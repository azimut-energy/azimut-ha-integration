"""Test the Azimut Energy binary sensor platform."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.util import dt as dt_util

from custom_components.azimut_energy.binary_sensor import (
    AzimutBinarySensor,
    AzimutConnectionSensor,
    BINARY_DEVICE_CLASS_MAP,
)
from custom_components.azimut_energy.const import (
    BINARY_DEVICE_CLASS_PROBLEM,
    CONF_SERIAL,
    DOMAIN,
    get_binary_sensor_definitions,
)


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


# Tests for binary sensor definitions


def test_get_binary_sensor_definitions() -> None:
    """Test get_binary_sensor_definitions returns expected definitions."""
    definitions = get_binary_sensor_definitions()

    assert isinstance(definitions, list)
    assert len(definitions) >= 1

    # Check the grid_lost_alarm definition exists
    grid_lost = next((d for d in definitions if d["id"] == "grid_lost_alarm"), None)
    assert grid_lost is not None
    assert grid_lost["name"] == "Grid Lost Alarm"
    assert grid_lost["device_class"] == BINARY_DEVICE_CLASS_PROBLEM
    assert grid_lost["icon"] == "mdi:transmission-tower-off"
    assert grid_lost["expire_after"] == 60 * 60  # 1 hour


def test_binary_device_class_map() -> None:
    """Test BINARY_DEVICE_CLASS_MAP contains expected mappings."""
    assert "problem" in BINARY_DEVICE_CLASS_MAP
    assert BINARY_DEVICE_CLASS_MAP["problem"] == BinarySensorDeviceClass.PROBLEM
    assert "connectivity" in BINARY_DEVICE_CLASS_MAP
    assert BINARY_DEVICE_CLASS_MAP["connectivity"] == BinarySensorDeviceClass.CONNECTIVITY


async def test_binary_sensor_from_definition(
    hass: HomeAssistant,
    mock_coordinator: MagicMock,
) -> None:
    """Test creating a binary sensor from a definition."""
    definition = {
        "id": "test_alarm",
        "name": "Test Alarm",
        "device_class": "problem",
        "icon": "mdi:alert",
        "expire_after": 3600,
    }

    sensor = AzimutBinarySensor(
        coordinator=mock_coordinator,
        serial="ABC123",
        definition=definition,
    )
    sensor.hass = hass

    # Check basic properties
    assert sensor.unique_id == "azen_ABC123_test_alarm"
    assert sensor.name == "Test Alarm"
    assert sensor.icon == "mdi:alert"
    assert sensor.device_class == BinarySensorDeviceClass.PROBLEM

    # Check device info
    assert sensor.device_info is not None
    assert (DOMAIN, "azen_ABC123") in sensor.device_info["identifiers"]

    # Should be unavailable initially
    assert sensor.available is False
    assert sensor.is_on is None


async def test_binary_sensor_update_state(
    hass: HomeAssistant,
    mock_coordinator: MagicMock,
) -> None:
    """Test binary sensor state update."""
    definition = {
        "id": "test_alarm",
        "name": "Test Alarm",
        "device_class": "problem",
        "icon": "mdi:alert",
        "expire_after": 3600,
    }

    sensor = AzimutBinarySensor(
        coordinator=mock_coordinator,
        serial="ABC123",
        definition=definition,
    )
    sensor.hass = hass

    # Initially unavailable
    assert sensor.available is False
    assert sensor.is_on is None

    # Update state to True (problem detected)
    with patch.object(sensor, "async_write_ha_state"):
        sensor.update_state(True)

    assert sensor.available is True
    assert sensor.is_on is True

    # Update state to False (problem resolved)
    with patch.object(sensor, "async_write_ha_state"):
        sensor.update_state(False)

    assert sensor.available is True
    assert sensor.is_on is False


async def test_binary_sensor_expiration(
    hass: HomeAssistant,
    mock_coordinator: MagicMock,
) -> None:
    """Test binary sensor expiration check."""
    definition = {
        "id": "test_alarm",
        "name": "Test Alarm",
        "device_class": "problem",
        "icon": "mdi:alert",
        "expire_after": 60,  # 60 seconds
    }

    sensor = AzimutBinarySensor(
        coordinator=mock_coordinator,
        serial="ABC123",
        definition=definition,
    )
    sensor.hass = hass

    # Set initial state
    with patch.object(sensor, "async_write_ha_state"):
        sensor.update_state(True)

    assert sensor.available is True

    # Simulate time passing beyond expiration
    with patch.object(sensor, "async_write_ha_state"):
        future_time = dt_util.utcnow() + timedelta(seconds=120)
        sensor._check_expiration(future_time)

    assert sensor.available is False


async def test_binary_sensor_setup_creates_sensors_from_definitions(
    hass: HomeAssistant,
    mock_coordinator: MagicMock,
) -> None:
    """Test binary sensor setup creates sensors from definitions."""
    from custom_components.azimut_energy.binary_sensor import async_setup_entry

    entry = MagicMock()
    entry.data = {CONF_SERIAL: "ABC123"}
    entry.entry_id = "test_entry"

    hass.data[DOMAIN] = {entry.entry_id: mock_coordinator}

    add_entities_mock = MagicMock()
    await async_setup_entry(hass, entry, add_entities_mock)

    # Verify sensors were created (connection sensor + defined sensors)
    assert add_entities_mock.call_count == 1
    sensors = add_entities_mock.call_args[0][0]

    # Should have at least 2 sensors (connection + grid_lost_alarm)
    assert len(sensors) >= 2

    # First should be connection sensor
    assert isinstance(sensors[0], AzimutConnectionSensor)

    # Second should be from definitions
    assert isinstance(sensors[1], AzimutBinarySensor)
    assert sensors[1].unique_id == "azen_ABC123_grid_lost_alarm"
