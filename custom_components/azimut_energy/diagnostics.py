"""Diagnostics support for Azimut Energy."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import CONF_SERIAL, DOMAIN, MQTT_PORT


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = hass.data[DOMAIN].get(entry.entry_id)

    # Gather sensor information
    sensors_info = []
    if coordinator:
        # Get all entities for this config entry
        entity_registry = er.async_get(hass)
        entities = [
            entity
            for entity in entity_registry.entities.values()
            if entity.config_entry_id == entry.entry_id
        ]

        for entity in entities:
            state = hass.states.get(entity.entity_id)
            sensors_info.append(
                {
                    "entity_id": entity.entity_id,
                    "unique_id": entity.unique_id,
                    "name": entity.name or entity.original_name,
                    "state": state.state if state else "unknown",
                    "available": state.state != "unavailable" if state else False,
                }
            )

    # Get MQTT statistics if coordinator is available
    mqtt_stats = {}
    if coordinator:
        mqtt_client = coordinator.mqtt_client
        mqtt_stats = {
            "connection_count": mqtt_client.connection_count,
            "reconnect_count": mqtt_client.reconnect_count,
            "total_messages_received": mqtt_client.total_messages_received,
            "last_message_time": mqtt_client.last_message_time,
            "last_connect_time": mqtt_client.last_connect_time,
            "last_disconnect_time": mqtt_client.last_disconnect_time,
        }

    return {
        "config_entry": {
            "entry_id": entry.entry_id,
            "version": entry.version,
            "domain": entry.domain,
            "title": entry.title,
            "source": entry.source,
        },
        "connection": {
            "host": entry.data.get(CONF_HOST),
            "port": MQTT_PORT,
            "serial": entry.data.get(CONF_SERIAL),
            "connected": coordinator.is_connected if coordinator else False,
            "tls_enabled": True,
        },
        "mqtt_topics": {
            "discovery": f"homeassistant/sensor/azen_{entry.data.get(CONF_SERIAL)}/+/config",
            "state": f"azen/{entry.data.get(CONF_SERIAL)}/sensor/+/state",
        },
        "mqtt_statistics": mqtt_stats,
        "sensors": {
            "count": len(sensors_info),
            "entities": sensors_info,
        },
    }
