"""Sensor platform for the Azimut Energy integration."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util

from .const import CONF_SERIAL, DEFAULT_EXPIRE_AFTER, DOMAIN

if TYPE_CHECKING:
    from . import AzimutMQTTCoordinator

_LOGGER = logging.getLogger(__name__)

# Map string device classes to SensorDeviceClass enum
DEVICE_CLASS_MAP: dict[str, SensorDeviceClass] = {
    "power": SensorDeviceClass.POWER,
    "energy": SensorDeviceClass.ENERGY,
    "voltage": SensorDeviceClass.VOLTAGE,
    "battery": SensorDeviceClass.BATTERY,
    "current": SensorDeviceClass.CURRENT,
    "temperature": SensorDeviceClass.TEMPERATURE,
}

# Map string state classes to SensorStateClass enum
STATE_CLASS_MAP: dict[str, SensorStateClass] = {
    "measurement": SensorStateClass.MEASUREMENT,
    "total_increasing": SensorStateClass.TOTAL_INCREASING,
    "total": SensorStateClass.TOTAL,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Azimut sensors from config entry."""
    coordinator: AzimutMQTTCoordinator = hass.data[DOMAIN][entry.entry_id]
    serial = entry.data.get(CONF_SERIAL, "")

    # Track created sensors by unique_id to avoid duplicates
    created_sensors: dict[str, AzimutSensor] = {}

    # Create diagnostic sensors
    sensor_count_diag = AzimutDiagnosticSensor(
        coordinator=coordinator,
        serial=serial,
        sensor_type="sensor_count",
        name="Discovered Sensors",
        icon="mdi:counter",
    )
    diagnostic_sensors = [
        AzimutDiagnosticSensor(
            coordinator=coordinator,
            serial=serial,
            sensor_type="reconnect_count",
            name="MQTT Reconnect Count",
            icon="mdi:connection",
        ),
        AzimutDiagnosticSensor(
            coordinator=coordinator,
            serial=serial,
            sensor_type="total_messages",
            name="MQTT Messages Received",
            icon="mdi:message-processing",
        ),
        sensor_count_diag,
    ]
    async_add_entities(diagnostic_sensors)

    @callback
    def handle_discovery(payload: dict[str, Any]) -> None:
        """Handle discovery message and create sensor."""
        unique_id = payload.get("unique_id")
        if not unique_id:
            _LOGGER.warning("Discovery payload missing unique_id: %s", payload)
            return

        # Skip if sensor already exists
        if unique_id in created_sensors:
            _LOGGER.debug("Sensor %s already exists, skipping", unique_id)
            return

        # Create the sensor entity
        sensor = AzimutSensor(
            coordinator=coordinator,
            payload=payload,
            serial=serial,
        )
        created_sensors[unique_id] = sensor

        # Update sensor count
        sensor_count_diag.increment_sensor_count()

        # Add the entity
        async_add_entities([sensor])
        _LOGGER.info("Created sensor: %s", unique_id)

    @callback
    def handle_state_update(state_topic: str, value: float) -> None:
        """Handle state update and route to correct sensor."""
        for sensor in created_sensors.values():
            if sensor.state_topic == state_topic:
                sensor.update_value(value)
                return

        _LOGGER.debug("No sensor found for state topic: %s", state_topic)

    @callback
    def handle_connection_change(connected: bool) -> None:
        """Handle MQTT connection state change."""
        if not connected:
            # Mark all sensors as unavailable when connection is lost
            for sensor in created_sensors.values():
                sensor.set_connection_available(False)
        # When connected, sensors will become available when they receive data

    # Register callbacks with coordinator
    coordinator.set_discovery_callback(handle_discovery)
    coordinator.set_state_callback(handle_state_update)
    coordinator.set_connection_callback(handle_connection_change)


class AzimutSensor(SensorEntity):
    """Azimut sensor entity created from MQTT discovery."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AzimutMQTTCoordinator,
        payload: dict[str, Any],
        serial: str,
    ) -> None:
        """Initialize the sensor from discovery payload."""
        self._coordinator = coordinator
        self._serial = serial

        # Extract fields from discovery payload
        self._attr_unique_id = payload.get("unique_id", "")
        self._state_topic = payload.get("state_topic", "")

        # Extract translation key from unique_id (e.g., "azen_123_battery_soc" -> "battery_soc")
        # This allows entity names to be translated
        # Following HA best practices: with has_entity_name=True, use ONLY translation_key (no name)
        if self._attr_unique_id:
            # Format: azen_{serial}_{sensor_type}
            parts = self._attr_unique_id.split("_", 2)
            if len(parts) >= 3:
                self._attr_translation_key = parts[2]  # The sensor type part
            else:
                # Fallback: if unique_id doesn't match format, use name from payload
                self._attr_name = payload.get("name", "Unknown Sensor")
        else:
            # No unique_id, use name from payload
            self._attr_name = payload.get("name", "Unknown Sensor")
        self._attr_native_unit_of_measurement = payload.get("unit_of_measurement")
        self._attr_icon = payload.get("icon")

        # Map device class string to enum
        device_class_str = payload.get("device_class")
        if device_class_str and device_class_str in DEVICE_CLASS_MAP:
            self._attr_device_class = DEVICE_CLASS_MAP[device_class_str]

        # Map state class string to enum
        state_class_str = payload.get("state_class")
        if state_class_str and state_class_str in STATE_CLASS_MAP:
            self._attr_state_class = STATE_CLASS_MAP[state_class_str]

        # Entity category from discovery payload
        entity_category_str = payload.get("entity_category")
        if entity_category_str == "diagnostic":
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
        elif entity_category_str == "config":
            self._attr_entity_category = EntityCategory.CONFIG

        # Expiration for availability
        self._expire_after = payload.get("expire_after", DEFAULT_EXPIRE_AFTER)
        self._last_update: datetime | None = None
        self._unsub_expire_check: Any = None
        self._mqtt_connected = True

        # Device info from payload
        device_info = payload.get("device", {})
        identifiers = device_info.get("identifiers", [])
        if identifiers:
            # Convert list to set of tuples for HA
            identifier = (
                identifiers[0] if isinstance(identifiers[0], str) else identifiers[0]
            )
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, identifier)},
                name=device_info.get("name", f"Azen {serial}"),
                manufacturer=device_info.get("manufacturer", "Azimut"),
                model=device_info.get("model", "Azen Energy System"),
                sw_version=device_info.get("sw_version"),
            )

        # Initial state
        self._attr_native_value: float | None = None
        self._attr_available = False

    @property
    def state_topic(self) -> str:
        """Return the state topic for this sensor."""
        return self._state_topic

    @callback
    def update_value(self, value: float) -> None:
        """Update the sensor value from MQTT state message."""
        self._attr_native_value = value
        self._attr_available = True
        self._mqtt_connected = True
        self._last_update = dt_util.utcnow()
        self.async_write_ha_state()

    @callback
    def set_connection_available(self, connected: bool) -> None:
        """Set availability based on MQTT connection state."""
        self._mqtt_connected = connected
        if not connected and self._attr_available:
            self._attr_available = False
            self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Run when entity is added to hass."""
        await super().async_added_to_hass()

        # Set up periodic check for expiration
        if self._expire_after > 0:
            self._unsub_expire_check = async_track_time_interval(
                self.hass,
                self._check_expiration,
                timedelta(seconds=min(self._expire_after / 2, 60)),
            )

    async def async_will_remove_from_hass(self) -> None:
        """Run when entity is being removed."""
        await super().async_will_remove_from_hass()

        if self._unsub_expire_check:
            self._unsub_expire_check()
            self._unsub_expire_check = None

    @callback
    def _check_expiration(self, now: datetime) -> None:
        """Check if sensor has expired due to no updates."""
        if self._last_update is None:
            return

        # Only check expiration if MQTT is connected
        if not self._mqtt_connected:
            return

        if (now - self._last_update).total_seconds() > self._expire_after:
            if self._attr_available:
                self._attr_available = False
                self.async_write_ha_state()
                _LOGGER.debug(
                    "Sensor %s became unavailable (no update for %s seconds)",
                    self._attr_unique_id,
                    self._expire_after,
                )


class AzimutDiagnosticSensor(SensorEntity):
    """Diagnostic sensor for Azimut integration statistics."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_state_class = SensorStateClass.TOTAL

    def __init__(
        self,
        coordinator: AzimutMQTTCoordinator,
        serial: str,
        sensor_type: str,
        name: str,
        icon: str,
    ) -> None:
        """Initialize the diagnostic sensor."""
        self._coordinator = coordinator
        self._serial = serial
        self._sensor_type = sensor_type
        self._device_id = f"azen_{serial}"
        self._attr_unique_id = f"{self._device_id}_{sensor_type}"
        self._attr_translation_key = sensor_type  # Use sensor_type as translation key
        # Don't set name - let HA use translation_key following best practices
        self._attr_icon = icon

        # Device info
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=f"Azen {serial}",
            manufacturer="Azimut",
            model="Azen Energy System",
        )

        # Track sensor count for sensor_count type
        self._sensor_count = 0

    @property
    def available(self) -> bool:
        """Return True as diagnostic sensors should always be available."""
        return True

    @property
    def native_value(self) -> int:
        """Return the state of the sensor."""
        mqtt_client = self._coordinator.mqtt_client

        if self._sensor_type == "reconnect_count":
            return mqtt_client.reconnect_count
        elif self._sensor_type == "total_messages":
            return mqtt_client.total_messages_received
        elif self._sensor_type == "sensor_count":
            return self._sensor_count

        return 0

    def increment_sensor_count(self) -> None:
        """Increment the sensor count."""
        if self._sensor_type == "sensor_count":
            self._sensor_count += 1
            # Only write state if entity has been added to hass
            if self.hass is not None:
                self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Run when entity is added to hass."""
        await super().async_added_to_hass()

        # Set up periodic update for MQTT stats
        if self._sensor_type in ("reconnect_count", "total_messages"):
            async_track_time_interval(
                self.hass,
                self._async_update,
                timedelta(seconds=30),
            )

    @callback
    def _async_update(self, now: datetime) -> None:
        """Update the sensor value."""
        self.async_write_ha_state()
