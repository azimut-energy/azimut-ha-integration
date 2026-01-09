"""Test the Azimut Energy binary sensor platform."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

from custom_components.azimut_energy.binary_sensor import AzimutConnectionSensor
from custom_components.azimut_energy.const import CONF_SERIAL, DOMAIN


@pytest.fixture
def mock_coordinator() -> MagicMock:
    """Mock coordinator."""
    coordinator = MagicMock()
    coordinator.is_connected = True
    coordinator.set_connection_callback = MagicMock()

    # Mock mqtt_client
    mqtt_client = MagicMock()
    mqtt_client.host = "192.168.1.100"
    mqtt_client.port = 8883
    mqtt_client.use_tls = True
    coordinator.mqtt_client = mqtt_client

    return coordinator


async def test_binary_sensor_setup(
    hass: HomeAssistant,
    mock_coordinator: MagicMock,
) -> None:
    """Test binary sensor setup."""
    from custom_components.azimut_energy.binary_sensor import async_setup_entry

    entry = MagicMock()
    entry.data = {CONF_SERIAL: "ABC123"}
    entry.entry_id = "test_entry"

    hass.data[DOMAIN] = {entry.entry_id: mock_coordinator}

    add_entities_mock = MagicMock()
    await async_setup_entry(hass, entry, add_entities_mock)

    # Verify connection sensor was created
    assert add_entities_mock.call_count == 1
    sensors = add_entities_mock.call_args[0][0]
    assert len(sensors) == 1
    assert isinstance(sensors[0], AzimutConnectionSensor)


async def test_connection_sensor_properties(
    hass: HomeAssistant,
    mock_coordinator: MagicMock,
) -> None:
    """Test connection sensor properties."""
    sensor = AzimutConnectionSensor(
        coordinator=mock_coordinator,
        serial="ABC123",
    )
    sensor.hass = hass

    # Check basic properties
    assert sensor.unique_id == "azen_ABC123_mqtt_connection"
    assert sensor.name == "MQTT Connection"
    assert sensor.device_class == BinarySensorDeviceClass.CONNECTIVITY
    assert sensor.entity_category == EntityCategory.DIAGNOSTIC
    assert sensor.available is True

    # Check device info
    assert sensor.device_info is not None
    assert (DOMAIN, "azen_ABC123") in sensor.device_info["identifiers"]


async def test_connection_sensor_state(
    hass: HomeAssistant,
    mock_coordinator: MagicMock,
) -> None:
    """Test connection sensor state reflects coordinator connection."""
    mock_coordinator.is_connected = True

    sensor = AzimutConnectionSensor(
        coordinator=mock_coordinator,
        serial="ABC123",
    )
    sensor.hass = hass

    # Should be connected initially
    assert sensor.is_on is True


async def test_connection_sensor_state_change(
    hass: HomeAssistant,
    mock_coordinator: MagicMock,
) -> None:
    """Test connection sensor state changes with connection."""
    sensor = AzimutConnectionSensor(
        coordinator=mock_coordinator,
        serial="ABC123",
    )
    sensor.hass = hass

    # Initially connected
    assert sensor.is_on is True

    # Simulate disconnection
    with patch.object(sensor, "async_write_ha_state"):
        sensor._handle_connection_change(False)

    assert sensor.is_on is False

    # Simulate reconnection
    with patch.object(sensor, "async_write_ha_state"):
        sensor._handle_connection_change(True)

    assert sensor.is_on is True


async def test_connection_sensor_attributes(
    hass: HomeAssistant,
    mock_coordinator: MagicMock,
) -> None:
    """Test connection sensor extra state attributes."""
    sensor = AzimutConnectionSensor(
        coordinator=mock_coordinator,
        serial="ABC123",
    )
    sensor.hass = hass

    attrs = sensor.extra_state_attributes
    assert attrs["broker"] == "192.168.1.100"
    assert attrs["port"] == 8883
    assert attrs["tls_enabled"] is True


async def test_connection_sensor_always_available(
    hass: HomeAssistant,
    mock_coordinator: MagicMock,
) -> None:
    """Test connection sensor is always available."""
    sensor = AzimutConnectionSensor(
        coordinator=mock_coordinator,
        serial="ABC123",
    )
    sensor.hass = hass

    # Should be available even when disconnected
    with patch.object(sensor, "async_write_ha_state"):
        sensor._handle_connection_change(False)

    assert sensor.available is True
