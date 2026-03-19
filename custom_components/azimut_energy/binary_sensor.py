"""Binary sensor platform for the Azimut Energy integration."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util

from .const import CONF_SERIAL, DEFAULT_EXPIRE_AFTER, DOMAIN, get_binary_sensor_definitions
from .types import BinarySensorDefinition, BinarySensorDiscoveryPayload

if TYPE_CHECKING:
    from . import AzimutMQTTCoordinator

_LOGGER = logging.getLogger(__name__)

# Map string device classes to BinarySensorDeviceClass enum
BINARY_DEVICE_CLASS_MAP: dict[str, BinarySensorDeviceClass] = {
    "battery": BinarySensorDeviceClass.BATTERY,
    "battery_charging": BinarySensorDeviceClass.BATTERY_CHARGING,
    "connectivity": BinarySensorDeviceClass.CONNECTIVITY,
    "door": BinarySensorDeviceClass.DOOR,
    "garage_door": BinarySensorDeviceClass.GARAGE_DOOR,
    "gas": BinarySensorDeviceClass.GAS,
    "heat": BinarySensorDeviceClass.HEAT,
    "lock": BinarySensorDeviceClass.LOCK,
    "moisture": BinarySensorDeviceClass.MOISTURE,
    "motion": BinarySensorDeviceClass.MOTION,
    "moving": BinarySensorDeviceClass.MOVING,
    "occupancy": BinarySensorDeviceClass.OCCUPANCY,
    "opening": BinarySensorDeviceClass.OPENING,
    "plug": BinarySensorDeviceClass.PLUG,
    "power": BinarySensorDeviceClass.POWER,
    "presence": BinarySensorDeviceClass.PRESENCE,
    "problem": BinarySensorDeviceClass.PROBLEM,
    "running": BinarySensorDeviceClass.RUNNING,
    "safety": BinarySensorDeviceClass.SAFETY,
    "smoke": BinarySensorDeviceClass.SMOKE,
    "sound": BinarySensorDeviceClass.SOUND,
    "tamper": BinarySensorDeviceClass.TAMPER,
    "update": BinarySensorDeviceClass.UPDATE,
    "vibration": BinarySensorDeviceClass.VIBRATION,
    "window": BinarySensorDeviceClass.WINDOW,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Azimut binary sensors from config entry."""
    coordinator: AzimutMQTTCoordinator = hass.data[DOMAIN][entry.entry_id]
    serial = entry.data.get(CONF_SERIAL, "")

    # Track created binary sensors by state_topic
    created_binary_sensors: dict[str, AzimutBinarySensor] = {}

    entities: list[BinarySensorEntity] = []

    # Create connection status binary sensor
    entities.append(AzimutConnectionSensor(coordinator, serial))

    # Create binary sensors from definitions
    for definition in get_binary_sensor_definitions():
        sensor = AzimutBinarySensor(coordinator, serial, definition)
        entities.append(sensor)
        # Track by state topic for routing state updates
        created_binary_sensors[sensor.state_topic] = sensor

    async_add_entities(entities)

    # Track dynamically discovered binary sensors by unique_id
    created_discovered: dict[str, AzimutDiscoveredBinarySensor] = {}

    @callback
    def handle_binary_sensor_discovery(payload: BinarySensorDiscoveryPayload) -> None:
        """Handle binary sensor discovery message and create sensor."""
        unique_id = payload.get("unique_id")
        if not unique_id:
            _LOGGER.warning(
                "Binary sensor discovery payload missing unique_id: %s", payload
            )
            return

        if unique_id in created_discovered:
            _LOGGER.debug("Binary sensor %s already exists, skipping", unique_id)
            return

        sensor = AzimutDiscoveredBinarySensor(
            coordinator=coordinator,
            payload=payload,
            serial=serial,
        )
        created_discovered[unique_id] = sensor
        # Also track by state topic for routing state updates
        created_binary_sensors[sensor.state_topic] = sensor
        async_add_entities([sensor])
        _LOGGER.info("Created discovered binary sensor: %s", unique_id)

    @callback
    def handle_binary_sensor_state_update(state_topic: str, is_on: bool) -> None:
        """Handle binary sensor state update and route to correct sensor."""
        if state_topic in created_binary_sensors:
            created_binary_sensors[state_topic].update_state(is_on)
            return

        _LOGGER.debug("No binary sensor found for state topic: %s", state_topic)

    # Register callbacks with coordinator
    coordinator.set_binary_sensor_discovery_callback(handle_binary_sensor_discovery)
    coordinator.set_binary_sensor_state_callback(handle_binary_sensor_state_update)


class AzimutConnectionSensor(BinarySensorEntity):
    """Binary sensor representing MQTT connection status."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: AzimutMQTTCoordinator,
        serial: str,
    ) -> None:
        """Initialize the connection sensor."""
        self._coordinator = coordinator
        self._serial = serial
        self._device_id = f"azen_{serial}"
        self._attr_unique_id = f"{self._device_id}_mqtt_connection"
        self._attr_name = "MQTT Connection"

        # Device info
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=f"Azen {serial}",
            manufacturer="Azimut",
            model="Azen Energy System",
        )

        # Initial state
        self._attr_is_on = coordinator.is_connected

        # Register callback for connection changes
        coordinator.set_connection_callback(self._handle_connection_change)

    @callback
    def _handle_connection_change(self, connected: bool) -> None:
        """Handle connection state change."""
        self._attr_is_on = connected
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return True as this sensor should always be available."""
        return True

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        mqtt_client = self._coordinator.mqtt_client
        return {
            "broker": mqtt_client.host,
            "port": mqtt_client.port,
            "tls_enabled": mqtt_client.use_tls,
        }


class AzimutBinarySensor(BinarySensorEntity):
    """Binary sensor entity created from a definition."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AzimutMQTTCoordinator,
        serial: str,
        definition: BinarySensorDefinition,
    ) -> None:
        """Initialize the binary sensor from definition."""
        self._coordinator = coordinator
        self._serial = serial
        self._definition = definition
        self._device_id = f"azen_{serial}"

        # Set attributes from definition
        self._attr_unique_id = f"{self._device_id}_{definition['id']}"
        self._attr_name = definition["name"]
        self._attr_icon = definition["icon"]

        # State topic for receiving MQTT updates
        # Format: azen/{serial}/binary_sensor/{sensor_id}/state
        self._state_topic = f"azen/{serial}/binary_sensor/{definition['id']}/state"

        # Map device class string to enum
        device_class_str = definition["device_class"]
        if device_class_str in BINARY_DEVICE_CLASS_MAP:
            self._attr_device_class = BINARY_DEVICE_CLASS_MAP[device_class_str]

        # Expiration for availability
        self._expire_after = definition["expire_after"]
        self._last_update: datetime | None = None
        self._unsub_expire_check: Any = None

        # Device info
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=f"Azen {serial}",
            manufacturer="Azimut",
            model="Azen Energy System",
        )

        # Initial state - unavailable until we receive data
        self._attr_is_on: bool | None = None
        self._attr_available = False

    @property
    def state_topic(self) -> str:
        """Return the state topic for this binary sensor."""
        return self._state_topic

    @callback
    def update_state(self, is_on: bool) -> None:
        """Update the sensor state from MQTT message."""
        self._attr_is_on = is_on
        self._attr_available = True
        self._last_update = dt_util.utcnow()
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

        if (now - self._last_update).total_seconds() > self._expire_after:
            if self._attr_available:
                self._attr_available = False
                self.async_write_ha_state()
                _LOGGER.debug(
                    "Binary sensor %s became unavailable (no update for %s seconds)",
                    self._attr_unique_id,
                    self._expire_after,
                )


class AzimutDiscoveredBinarySensor(BinarySensorEntity):
    """Binary sensor entity created from MQTT discovery."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AzimutMQTTCoordinator,
        payload: BinarySensorDiscoveryPayload,
        serial: str,
    ) -> None:
        """Initialize the binary sensor from discovery payload."""
        self._coordinator = coordinator
        self._serial = serial

        # Extract fields from discovery payload
        self._attr_unique_id = payload.get("unique_id", "")
        self._state_topic = payload.get("state_topic", "")

        # Extract translation key from unique_id (e.g., "azen_123_arbitrage_active")
        if self._attr_unique_id:
            parts = self._attr_unique_id.split("_", 2)
            if len(parts) >= 3:
                self._attr_translation_key = parts[2]
            else:
                self._attr_name = payload.get("name", "Unknown Binary Sensor")
        else:
            self._attr_name = payload.get("name", "Unknown Binary Sensor")

        self._attr_icon = payload.get("icon")

        # Map device class string to enum
        device_class_str = payload.get("device_class")
        if device_class_str and device_class_str in BINARY_DEVICE_CLASS_MAP:
            self._attr_device_class = BINARY_DEVICE_CLASS_MAP[device_class_str]

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

        # Device info from payload
        device_info = payload.get("device", {})
        identifiers = device_info.get("identifiers", [])
        if identifiers:
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
        self._attr_is_on: bool | None = None
        self._attr_available = False

    @property
    def state_topic(self) -> str:
        """Return the state topic for this binary sensor."""
        return self._state_topic

    @callback
    def update_state(self, is_on: bool) -> None:
        """Update the sensor state from MQTT message."""
        self._attr_is_on = is_on
        self._attr_available = True
        self._last_update = dt_util.utcnow()
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Run when entity is added to hass."""
        await super().async_added_to_hass()

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

        if (now - self._last_update).total_seconds() > self._expire_after:
            if self._attr_available:
                self._attr_available = False
                self.async_write_ha_state()
                _LOGGER.debug(
                    "Binary sensor %s became unavailable (no update for %s seconds)",
                    self._attr_unique_id,
                    self._expire_after,
                )
