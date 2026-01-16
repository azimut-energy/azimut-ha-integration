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

from .const import CONF_SERIAL, DOMAIN, get_binary_sensor_definitions
from .types import BinarySensorDefinition

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

    entities: list[BinarySensorEntity] = []

    # Create connection status binary sensor
    entities.append(AzimutConnectionSensor(coordinator, serial))

    # Create binary sensors from definitions
    for definition in get_binary_sensor_definitions():
        entities.append(AzimutBinarySensor(coordinator, serial, definition))

    async_add_entities(entities)


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
