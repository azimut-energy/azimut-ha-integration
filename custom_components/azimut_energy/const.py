"""Constants for the Azimut Energy integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from .types import BinarySensorDefinition

DOMAIN: Final[str] = "azimut_energy"

# MQTT Configuration
MQTT_PORT: Final[int] = 8883
MQTT_USE_TLS: Final[bool] = True
MQTT_KEEPALIVE: Final[int] = 30  # Reduced from 60 for faster dead connection detection

# Default expiration for sensors (seconds)
# Sensors become unavailable if no update received within this time
DEFAULT_EXPIRE_AFTER: Final[int] = 120  # Reduced from 300 to 2 minutes

# Configuration keys
CONF_SERIAL: Final[str] = "serial"

# MQTT Topic patterns
# Sensor discovery topic: homeassistant/sensor/azen_{serial}/+/config
# Sensor state topic: azen/{serial}/sensor/+/state
# Binary sensor discovery topic: homeassistant/binary_sensor/azen_{serial}/+/config
# Binary sensor state topic: azen/{serial}/binary_sensor/+/state
SENSOR_DISCOVERY_TOPIC_PREFIX: Final[str] = "homeassistant/sensor"
BINARY_SENSOR_DISCOVERY_TOPIC_PREFIX: Final[str] = "homeassistant/binary_sensor"
STATE_TOPIC_PREFIX: Final[str] = "azen"


def get_discovery_topic(serial: str) -> str:
    """Get the sensor discovery topic pattern for a device serial."""
    return f"{SENSOR_DISCOVERY_TOPIC_PREFIX}/azen_{serial}/+/config"


def get_binary_sensor_discovery_topic(serial: str) -> str:
    """Get the binary sensor discovery topic pattern for a device serial."""
    return f"{BINARY_SENSOR_DISCOVERY_TOPIC_PREFIX}/azen_{serial}/+/config"


def get_state_topic(serial: str) -> str:
    """Get the sensor state topic pattern for a device serial."""
    return f"{STATE_TOPIC_PREFIX}/{serial}/sensor/+/state"


def get_binary_sensor_state_topic(serial: str) -> str:
    """Get the binary sensor state topic pattern for a device serial."""
    return f"{STATE_TOPIC_PREFIX}/{serial}/binary_sensor/+/state"


def get_republish_command_topic(serial: str) -> str:
    """Get the republish command topic for a device serial.

    Publishing to this topic triggers the device to republish all sensor values.
    """
    return f"{STATE_TOPIC_PREFIX}/{serial}/command/republish"


# Icon mapping
ICON_GRID: Final[str] = "mdi:transmission-tower"
ICON_BATTERY: Final[str] = "mdi:battery"
ICON_SOLAR: Final[str] = "mdi:solar-power"
ICON_INVERTER: Final[str] = "mdi:power-plug"
ICON_CONSUMPTION: Final[str] = "mdi:home-lightning-bolt"
ICON_VOLTAGE: Final[str] = "mdi:flash"
ICON_ENERGY: Final[str] = "mdi:lightning-bolt"


# Binary sensor device classes
BINARY_DEVICE_CLASS_PROBLEM: Final[str] = "problem"


def get_binary_sensor_definitions() -> list[BinarySensorDefinition]:
    """Get the list of binary sensor definitions.

    Returns a list of binary sensor definitions that should be created
    for each Azimut device.
    """
    return [
        {
            "id": "grid_lost_alarm",
            "name": "Grid Lost Alarm",
            "device_class": BINARY_DEVICE_CLASS_PROBLEM,
            "icon": "mdi:transmission-tower-off",
            "expire_after": 60 * 60,  # 1 hour
        },
    ]
