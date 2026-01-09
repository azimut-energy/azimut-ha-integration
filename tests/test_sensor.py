"""Test the Azimut Energy sensor platform."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.azimut_energy.const import CONF_SERIAL, DOMAIN  # noqa: I001
from custom_components.azimut_energy.sensor import (  # noqa: I001
    AzimutDiagnosticSensor,
    AzimutSensor,
)


@pytest.fixture
def mock_coordinator() -> MagicMock:
    """Mock coordinator."""
    coordinator = MagicMock()
    coordinator.set_discovery_callback = MagicMock()
    coordinator.set_state_callback = MagicMock()
    coordinator.set_connection_callback = MagicMock()
    return coordinator


@pytest.fixture
def sample_discovery_payload() -> dict:
    """Sample discovery payload."""
    return {
        "unique_id": "azen_ABC123_battery_soc",
        "name": "Battery State of Charge",
        "state_topic": "azen/ABC123/sensor/battery_soc/state",
        "unit_of_measurement": "%",
        "device_class": "battery",
        "state_class": "measurement",
        "icon": "mdi:battery",
        "expire_after": 300,
        "device": {
            "identifiers": ["azen_ABC123"],
            "name": "Azen ABC123",
            "manufacturer": "Azimut",
            "model": "Azen Energy System",
            "sw_version": "1.0.0",
        },
    }


async def test_sensor_creation_from_discovery(
    hass: HomeAssistant,
    mock_coordinator: MagicMock,
    sample_discovery_payload: dict,
) -> None:
    """Test sensor creation from discovery payload."""
    from custom_components.azimut_energy.sensor import async_setup_entry

    entry = MagicMock()
    entry.data = {CONF_SERIAL: "ABC123"}
    entry.entry_id = "test_entry"

    hass.data[DOMAIN] = {entry.entry_id: mock_coordinator}

    # Add mqtt_client to coordinator
    mqtt_client = MagicMock()
    mqtt_client.reconnect_count = 0
    mqtt_client.total_messages_received = 0
    mock_coordinator.mqtt_client = mqtt_client

    # Capture the callbacks
    callbacks = {}

    def capture_discovery_cb(cb):
        callbacks["discovery"] = cb

    def capture_state_cb(cb):
        callbacks["state"] = cb

    def capture_connection_cb(cb):
        callbacks["connection"] = cb

    mock_coordinator.set_discovery_callback.side_effect = capture_discovery_cb
    mock_coordinator.set_state_callback.side_effect = capture_state_cb
    mock_coordinator.set_connection_callback.side_effect = capture_connection_cb

    add_entities_mock = MagicMock()
    await async_setup_entry(hass, entry, add_entities_mock)

    # Simulate discovery message
    callbacks["discovery"](sample_discovery_payload)

    # Verify sensor was created (2 calls: 1 for diagnostic sensors, 1 for discovered sensor)
    assert add_entities_mock.call_count == 2
    # Second call contains the discovered sensor
    sensors = add_entities_mock.call_args_list[1][0][0]
    assert len(sensors) == 1

    sensor = sensors[0]
    assert sensor.unique_id == "azen_ABC123_battery_soc"
    assert (
        not hasattr(sensor, "_attr_name") or sensor._attr_name is None
    )  # Name not set when using translation_key
    assert (
        sensor.translation_key == "battery_soc"
    )  # Translation key provides the name (HA best practice)
    assert sensor.state_topic == "azen/ABC123/sensor/battery_soc/state"


async def test_sensor_state_update(
    hass: HomeAssistant,
    mock_coordinator: MagicMock,
    sample_discovery_payload: dict,
) -> None:
    """Test sensor state update."""
    sensor = AzimutSensor(
        coordinator=mock_coordinator,
        payload=sample_discovery_payload,
        serial="ABC123",
    )
    sensor.hass = hass

    # Initial state should be None and unavailable
    assert sensor.native_value is None
    assert not sensor.available

    # Update value
    with patch.object(sensor, "async_write_ha_state"):
        sensor.update_value(85.5)

    # Verify state
    assert sensor.native_value == 85.5
    assert sensor.available


async def test_sensor_duplicate_discovery(
    hass: HomeAssistant,
    mock_coordinator: MagicMock,
    sample_discovery_payload: dict,
) -> None:
    """Test that duplicate discovery messages don't create duplicate sensors."""
    from custom_components.azimut_energy.sensor import async_setup_entry

    entry = MagicMock()
    entry.data = {CONF_SERIAL: "ABC123"}
    entry.entry_id = "test_entry"

    hass.data[DOMAIN] = {entry.entry_id: mock_coordinator}

    # Add mqtt_client to coordinator
    mqtt_client = MagicMock()
    mqtt_client.reconnect_count = 0
    mqtt_client.total_messages_received = 0
    mock_coordinator.mqtt_client = mqtt_client

    callbacks = {}
    mock_coordinator.set_discovery_callback.side_effect = lambda cb: callbacks.update(
        {"discovery": cb}
    )
    mock_coordinator.set_state_callback.side_effect = lambda cb: None
    mock_coordinator.set_connection_callback.side_effect = lambda cb: None

    add_entities_mock = MagicMock()
    await async_setup_entry(hass, entry, add_entities_mock)

    # Call discovery callback twice with same payload
    callbacks["discovery"](sample_discovery_payload)
    callbacks["discovery"](sample_discovery_payload)

    # Should only create one discovered sensor (2 calls total: 1 for diagnostic, 1 for discovered)
    assert add_entities_mock.call_count == 2


async def test_sensor_state_routing(
    hass: HomeAssistant,
    mock_coordinator: MagicMock,
    sample_discovery_payload: dict,
) -> None:
    """Test state updates are routed to correct sensor."""
    from custom_components.azimut_energy.sensor import async_setup_entry

    entry = MagicMock()
    entry.data = {CONF_SERIAL: "ABC123"}
    entry.entry_id = "test_entry"

    hass.data[DOMAIN] = {entry.entry_id: mock_coordinator}

    callbacks = {}
    mock_coordinator.set_discovery_callback.side_effect = lambda cb: callbacks.update(
        {"discovery": cb}
    )
    mock_coordinator.set_state_callback.side_effect = lambda cb: callbacks.update(
        {"state": cb}
    )
    mock_coordinator.set_connection_callback.side_effect = lambda cb: None

    add_entities_mock = MagicMock()
    await async_setup_entry(hass, entry, add_entities_mock)

    # Create sensor via discovery
    callbacks["discovery"](sample_discovery_payload)

    sensor = add_entities_mock.call_args[0][0][0]
    sensor.hass = hass

    # Mock async_write_ha_state
    with patch.object(sensor, "async_write_ha_state"):
        # Send state update
        callbacks["state"]("azen/ABC123/sensor/battery_soc/state", 92.0)

    assert sensor.native_value == 92.0


async def test_sensor_connection_availability(
    hass: HomeAssistant,
    mock_coordinator: MagicMock,
    sample_discovery_payload: dict,
) -> None:
    """Test sensor availability based on connection state."""
    sensor = AzimutSensor(
        coordinator=mock_coordinator,
        payload=sample_discovery_payload,
        serial="ABC123",
    )
    sensor.hass = hass

    # Set sensor as available
    with patch.object(sensor, "async_write_ha_state"):
        sensor.update_value(50.0)
    assert sensor.available

    # Simulate connection loss
    with patch.object(sensor, "async_write_ha_state"):
        sensor.set_connection_available(False)
    assert not sensor.available


async def test_sensor_expiration(
    hass: HomeAssistant,
    mock_coordinator: MagicMock,
    sample_discovery_payload: dict,
) -> None:
    """Test sensor expiration after no updates."""
    sensor = AzimutSensor(
        coordinator=mock_coordinator,
        payload=sample_discovery_payload,
        serial="ABC123",
    )
    sensor.hass = hass
    sensor._mqtt_connected = True

    # Set initial value
    with patch.object(sensor, "async_write_ha_state"):
        sensor.update_value(1000.0)
    assert sensor.available

    # Simulate time passing beyond expiration (300 seconds)
    sensor._last_update = dt_util.utcnow() - timedelta(seconds=301)

    with patch.object(sensor, "async_write_ha_state"):
        sensor._check_expiration(dt_util.utcnow())

    # Sensor should be unavailable
    assert not sensor.available


async def test_sensor_device_class_mapping(
    hass: HomeAssistant,
    mock_coordinator: MagicMock,
) -> None:
    """Test device class string to enum mapping."""
    from homeassistant.components.sensor import SensorDeviceClass

    payload = {
        "unique_id": "test_power",
        "name": "Test Power",
        "state_topic": "test/state",
        "device_class": "power",
        "device": {"identifiers": ["test"]},
    }

    sensor = AzimutSensor(
        coordinator=mock_coordinator,
        payload=payload,
        serial="TEST",
    )

    assert sensor.device_class == SensorDeviceClass.POWER


async def test_sensor_state_class_mapping(
    hass: HomeAssistant,
    mock_coordinator: MagicMock,
) -> None:
    """Test state class string to enum mapping."""
    from homeassistant.components.sensor import SensorStateClass

    payload = {
        "unique_id": "test_energy",
        "name": "Test Energy",
        "state_topic": "test/state",
        "state_class": "total_increasing",
        "device": {"identifiers": ["test"]},
    }

    sensor = AzimutSensor(
        coordinator=mock_coordinator,
        payload=payload,
        serial="TEST",
    )

    assert sensor.state_class == SensorStateClass.TOTAL_INCREASING


async def test_sensor_missing_unique_id(
    hass: HomeAssistant,
    mock_coordinator: MagicMock,
) -> None:
    """Test discovery payload without unique_id is ignored."""
    from custom_components.azimut_energy.sensor import async_setup_entry

    entry = MagicMock()
    entry.data = {CONF_SERIAL: "ABC123"}
    entry.entry_id = "test_entry"

    hass.data[DOMAIN] = {entry.entry_id: mock_coordinator}

    callbacks = {}
    mock_coordinator.set_discovery_callback.side_effect = lambda cb: callbacks.update(
        {"discovery": cb}
    )
    mock_coordinator.set_state_callback.side_effect = lambda cb: None
    mock_coordinator.set_connection_callback.side_effect = lambda cb: None

    add_entities_mock = MagicMock()
    await async_setup_entry(hass, entry, add_entities_mock)

    # Discovery without unique_id (second call since first creates diagnostic sensors)
    callbacks["discovery"]({"name": "Test", "state_topic": "test"})

    # Should only have diagnostic sensors, not the invalid one
    assert add_entities_mock.call_count == 1


async def test_diagnostic_sensors_created(
    hass: HomeAssistant,
    mock_coordinator: MagicMock,
) -> None:
    """Test that diagnostic sensors are created on setup."""
    from custom_components.azimut_energy.sensor import async_setup_entry

    entry = MagicMock()
    entry.data = {CONF_SERIAL: "ABC123"}
    entry.entry_id = "test_entry"

    hass.data[DOMAIN] = {entry.entry_id: mock_coordinator}

    # Add mqtt_client to coordinator
    mqtt_client = MagicMock()
    mqtt_client.reconnect_count = 2
    mqtt_client.total_messages_received = 150
    mock_coordinator.mqtt_client = mqtt_client

    mock_coordinator.set_discovery_callback.side_effect = lambda cb: None
    mock_coordinator.set_state_callback.side_effect = lambda cb: None
    mock_coordinator.set_connection_callback.side_effect = lambda cb: None

    add_entities_mock = MagicMock()
    await async_setup_entry(hass, entry, add_entities_mock)

    # Verify diagnostic sensors were created
    assert add_entities_mock.call_count == 1
    sensors = add_entities_mock.call_args[0][0]
    assert len(sensors) == 3

    # Check sensor types
    sensor_types = [s._sensor_type for s in sensors]
    assert "reconnect_count" in sensor_types
    assert "total_messages" in sensor_types
    assert "sensor_count" in sensor_types


async def test_diagnostic_sensor_values(
    hass: HomeAssistant,
    mock_coordinator: MagicMock,
) -> None:
    """Test diagnostic sensor values."""
    from custom_components.azimut_energy.sensor import AzimutDiagnosticSensor

    # Setup mqtt_client
    mqtt_client = MagicMock()
    mqtt_client.reconnect_count = 3
    mqtt_client.total_messages_received = 250
    mock_coordinator.mqtt_client = mqtt_client

    # Test reconnect count sensor
    reconnect_sensor = AzimutDiagnosticSensor(
        coordinator=mock_coordinator,
        serial="ABC123",
        sensor_type="reconnect_count",
        name="MQTT Reconnect Count",
        icon="mdi:connection",
    )
    assert reconnect_sensor.native_value == 3

    # Test total messages sensor
    messages_sensor = AzimutDiagnosticSensor(
        coordinator=mock_coordinator,
        serial="ABC123",
        sensor_type="total_messages",
        name="MQTT Messages Received",
        icon="mdi:message-processing",
    )
    assert messages_sensor.native_value == 250

    # Test sensor count sensor
    count_sensor = AzimutDiagnosticSensor(
        coordinator=mock_coordinator,
        serial="ABC123",
        sensor_type="sensor_count",
        name="Discovered Sensors",
        icon="mdi:counter",
    )
    assert count_sensor.native_value == 0

    # Increment sensor count
    count_sensor.increment_sensor_count()
    assert count_sensor.native_value == 1


async def test_diagnostic_sensor_properties(
    hass: HomeAssistant,
    mock_coordinator: MagicMock,
) -> None:
    """Test diagnostic sensor properties."""
    from homeassistant.helpers.entity import EntityCategory

    from custom_components.azimut_energy.sensor import AzimutDiagnosticSensor

    mqtt_client = MagicMock()
    mqtt_client.reconnect_count = 0
    mock_coordinator.mqtt_client = mqtt_client

    sensor = AzimutDiagnosticSensor(
        coordinator=mock_coordinator,
        serial="ABC123",
        sensor_type="reconnect_count",
        name="MQTT Reconnect Count",
        icon="mdi:connection",
    )
    sensor.hass = hass

    # Check properties
    assert sensor.unique_id == "azen_ABC123_reconnect_count"
    assert (
        not hasattr(sensor, "_attr_name") or sensor._attr_name is None
    )  # Name not set when using translation_key
    assert (
        sensor.translation_key == "reconnect_count"
    )  # Translation key provides the name (HA best practice)
    assert sensor.icon == "mdi:connection"
    assert sensor.entity_category == EntityCategory.DIAGNOSTIC
    assert sensor.available is True

    # Check device info
    assert sensor.device_info is not None
    assert (DOMAIN, "azen_ABC123") in sensor.device_info["identifiers"]
    assert sensor.device_info["name"] == "Azen ABC123"


async def test_sensor_count_increments_on_discovery(
    hass: HomeAssistant,
    mock_coordinator: MagicMock,
    sample_discovery_payload: dict,
) -> None:
    """Test sensor count increments when new sensors are discovered."""
    from custom_components.azimut_energy.sensor import async_setup_entry

    entry = MagicMock()
    entry.data = {CONF_SERIAL: "ABC123"}
    entry.entry_id = "test_entry"

    hass.data[DOMAIN] = {entry.entry_id: mock_coordinator}

    # Add mqtt_client
    mqtt_client = MagicMock()
    mqtt_client.reconnect_count = 0
    mqtt_client.total_messages_received = 0
    mock_coordinator.mqtt_client = mqtt_client

    callbacks = {}
    mock_coordinator.set_discovery_callback.side_effect = lambda cb: callbacks.update(
        {"discovery": cb}
    )
    mock_coordinator.set_state_callback.side_effect = lambda cb: None
    mock_coordinator.set_connection_callback.side_effect = lambda cb: None

    add_entities_mock = MagicMock()
    await async_setup_entry(hass, entry, add_entities_mock)

    # Get the sensor count diagnostic sensor
    diagnostic_sensors = add_entities_mock.call_args[0][0]
    sensor_count_diag = next(
        s for s in diagnostic_sensors if s._sensor_type == "sensor_count"
    )

    # Initial count should be 0
    assert sensor_count_diag.native_value == 0

    # Discover a sensor
    callbacks["discovery"](sample_discovery_payload)

    # Count should increment
    assert sensor_count_diag.native_value == 1

    # Discover another sensor
    payload2 = sample_discovery_payload.copy()
    payload2["unique_id"] = "azen_ABC123_battery_voltage"
    callbacks["discovery"](payload2)

    # Count should increment again
    assert sensor_count_diag.native_value == 2


async def test_entity_category_from_discovery(
    hass: HomeAssistant,
    mock_coordinator: MagicMock,
    sample_discovery_payload: dict,
) -> None:
    """Test entity category is properly set from discovery payload."""
    from homeassistant.helpers.entity import EntityCategory

    # Test diagnostic entity category
    diagnostic_payload = sample_discovery_payload.copy()
    diagnostic_payload["entity_category"] = "diagnostic"
    diagnostic_payload["unique_id"] = "azen_ABC123_uptime"
    diagnostic_payload["name"] = "Uptime"

    sensor = AzimutSensor(mock_coordinator, diagnostic_payload, "ABC123")
    assert sensor.entity_category == EntityCategory.DIAGNOSTIC

    # Test config entity category
    config_payload = sample_discovery_payload.copy()
    config_payload["entity_category"] = "config"
    config_payload["unique_id"] = "azen_ABC123_poll_interval"
    config_payload["name"] = "Poll Interval"

    sensor = AzimutSensor(mock_coordinator, config_payload, "ABC123")
    assert sensor.entity_category == EntityCategory.CONFIG

    # Test no entity category (regular sensor)
    regular_payload = sample_discovery_payload.copy()
    sensor = AzimutSensor(mock_coordinator, regular_payload, "ABC123")
    assert sensor.entity_category is None


async def test_translation_key_from_unique_id(
    hass: HomeAssistant,
    mock_coordinator: MagicMock,
    sample_discovery_payload: dict,
) -> None:
    """Test translation_key is extracted from unique_id."""
    # Test battery_soc translation key
    payload = sample_discovery_payload.copy()
    payload["unique_id"] = "azen_365102_battery_soc"
    sensor = AzimutSensor(mock_coordinator, payload, "365102")
    assert sensor.translation_key == "battery_soc"

    # Test grid_power_l1 translation key
    payload["unique_id"] = "azen_365102_grid_power_l1"
    sensor = AzimutSensor(mock_coordinator, payload, "365102")
    assert sensor.translation_key == "grid_power_l1"

    # Test pv_energy translation key
    payload["unique_id"] = "azen_504589_pv_energy"
    sensor = AzimutSensor(mock_coordinator, payload, "504589")
    assert sensor.translation_key == "pv_energy"

    # Test with serial containing leading zeros
    payload["unique_id"] = "azen_007890_battery_power"
    sensor = AzimutSensor(mock_coordinator, payload, "007890")
    assert sensor.translation_key == "battery_power"

    # Test diagnostic sensor translation key
    payload["unique_id"] = "azen_365102_reconnect_count"
    sensor = AzimutSensor(mock_coordinator, payload, "365102")
    assert sensor.translation_key == "reconnect_count"

    # Test no translation key for invalid unique_id format
    payload["unique_id"] = "invalid_format"
    sensor = AzimutSensor(mock_coordinator, payload, "365102")
    assert not hasattr(sensor, "translation_key") or sensor.translation_key is None


async def test_sensor_no_unique_id(
    hass: HomeAssistant,
    mock_coordinator: MagicMock,
    sample_discovery_payload: dict,
) -> None:
    """Test sensor creation without unique_id uses name from payload."""
    payload = sample_discovery_payload.copy()
    del payload["unique_id"]

    sensor = AzimutSensor(mock_coordinator, payload, "365102")
    assert sensor.name == "Battery State of Charge"
    assert (
        not hasattr(sensor, "_attr_translation_key") or sensor.translation_key is None
    )


async def test_diagnostic_sensor_default_value(
    hass: HomeAssistant,
    mock_coordinator: MagicMock,
) -> None:
    """Test diagnostic sensor returns 0 by default."""
    sensor = AzimutDiagnosticSensor(
        coordinator=mock_coordinator,
        serial="365102",
        sensor_type="sensor_count",
        name="Sensor Count",
        icon="mdi:counter",
    )
    assert sensor.native_value == 0
