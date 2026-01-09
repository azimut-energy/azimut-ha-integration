"""The Azimut Energy integration."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady

from .const import (
    CONF_SERIAL,
    DOMAIN,
    MQTT_PORT,
    MQTT_USE_TLS,
)
from .mqtt_client import AzimutMQTTClient

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "binary_sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Azimut Energy from a config entry."""
    host = entry.data[CONF_HOST]
    serial = entry.data.get(CONF_SERIAL, "")

    coordinator = AzimutMQTTCoordinator(
        hass,
        host=host,
        serial=serial,
    )

    # Connect to MQTT broker
    if not await coordinator.async_connect():
        raise ConfigEntryNotReady(
            f"Failed to connect to MQTT broker at {host}:{MQTT_PORT}"
        )

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Set up all platforms for this device/entry
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register update listener for config entry changes
    entry.async_on_unload(entry.add_update_listener(update_listener))

    # Start listening for MQTT messages (with auto-reconnect)
    coordinator.start_listening()

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_disconnect()

    return unload_ok


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


class AzimutMQTTCoordinator:
    """Coordinator for Azimut MQTT connection and message routing."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        serial: str,
    ) -> None:
        """Initialize the coordinator."""
        self.hass = hass
        self.serial = serial
        self.host = host

        self._mqtt_client = AzimutMQTTClient(
            host=host,
            port=MQTT_PORT,
            serial=serial,
            use_tls=MQTT_USE_TLS,
        )

        self._listen_task: asyncio.Task | None = None
        self._discovery_callback: Callable[[dict[str, Any]], None] | None = None
        self._state_callback: Callable[[str, float], None] | None = None
        self._connection_callback: Callable[[bool], None] | None = None

        # Set up MQTT client callbacks
        self._mqtt_client.set_discovery_callback(self._handle_discovery)
        self._mqtt_client.set_state_callback(self._handle_state)
        self._mqtt_client.set_connection_callback(self._handle_connection_change)

    def set_discovery_callback(
        self, callback_func: Callable[[dict[str, Any]], None]
    ) -> None:
        """Set callback for discovery messages from sensor platform."""
        self._discovery_callback = callback_func

    def set_state_callback(self, callback_func: Callable[[str, float], None]) -> None:
        """Set callback for state messages from sensor platform."""
        self._state_callback = callback_func

    def set_connection_callback(self, callback_func: Callable[[bool], None]) -> None:
        """Set callback for connection state changes."""
        self._connection_callback = callback_func

    @callback
    def _handle_discovery(self, payload: dict[str, Any]) -> None:
        """Handle discovery message from MQTT client."""
        if self._discovery_callback:
            self._discovery_callback(payload)

    @callback
    def _handle_state(self, state_topic: str, value: float) -> None:
        """Handle state message from MQTT client."""
        if self._state_callback:
            self._state_callback(state_topic, value)

    @callback
    def _handle_connection_change(self, connected: bool) -> None:
        """Handle connection state change from MQTT client."""
        if self._connection_callback:
            self._connection_callback(connected)

    async def async_connect(self) -> bool:
        """Connect to MQTT broker."""
        return await self._mqtt_client.connect()

    async def async_disconnect(self) -> None:
        """Disconnect from MQTT broker."""
        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
            self._listen_task = None

        await self._mqtt_client.disconnect()

    def start_listening(self) -> None:
        """Start listening for MQTT messages with auto-reconnect."""
        if self._listen_task is None:
            self._listen_task = asyncio.create_task(
                self._mqtt_client.listen_with_reconnect()
            )

    @property
    def is_connected(self) -> bool:
        """Return connection status."""
        return self._mqtt_client.is_connected

    @property
    def mqtt_client(self) -> AzimutMQTTClient:
        """Return the MQTT client for accessing statistics."""
        return self._mqtt_client
