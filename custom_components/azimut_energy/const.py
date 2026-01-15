"""Constants for the Azimut Energy integration."""

from typing import Final

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
# Discovery topic: homeassistant/sensor/azen_{serial}/+/config
# State topic: azen/{serial}/sensor/+/state
DISCOVERY_TOPIC_PREFIX: Final[str] = "homeassistant/sensor"
STATE_TOPIC_PREFIX: Final[str] = "azen"


def get_discovery_topic(serial: str) -> str:
    """Get the discovery topic pattern for a device serial."""
    return f"{DISCOVERY_TOPIC_PREFIX}/azen_{serial}/+/config"


def get_state_topic(serial: str) -> str:
    """Get the state topic pattern for a device serial."""
    return f"{STATE_TOPIC_PREFIX}/{serial}/sensor/+/state"


def get_republish_command_topic(serial: str) -> str:
    """Get the republish command topic for a device serial.

    Publishing any message to this topic triggers the device to republish
    all sensor values. The payload content is ignored.
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
