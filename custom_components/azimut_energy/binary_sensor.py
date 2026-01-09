"""Binary sensor platform for the Azimut Energy integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_SERIAL, DOMAIN

if TYPE_CHECKING:
    from . import AzimutMQTTCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Azimut binary sensors from config entry."""
    coordinator: AzimutMQTTCoordinator = hass.data[DOMAIN][entry.entry_id]
    serial = entry.data.get(CONF_SERIAL, "")

    # Create connection status binary sensor
    async_add_entities([AzimutConnectionSensor(coordinator, serial)])


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
    def extra_state_attributes(self) -> dict[str, str]:
        """Return extra state attributes."""
        mqtt_client = self._coordinator.mqtt_client
        return {
            "broker": mqtt_client.host,
            "port": mqtt_client.port,
            "tls_enabled": mqtt_client.use_tls,
        }
