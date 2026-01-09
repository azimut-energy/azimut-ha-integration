"""Constants for the Azimut Energy integration."""

DOMAIN = "azimut_energy"

# MQTT Configuration
MQTT_PORT = 8883
MQTT_USE_TLS = True
MQTT_KEEPALIVE = 30  # Reduced from 60 for faster dead connection detection

# Default expiration for sensors (seconds)
# Sensors become unavailable if no update received within this time
DEFAULT_EXPIRE_AFTER = 120  # Reduced from 300 to 2 minutes

# Configuration keys
CONF_SERIAL = "serial"

# MQTT Topic patterns
# Discovery topic: homeassistant/sensor/azen_{serial}/+/config
# State topic: azen/{serial}/sensor/+/state
DISCOVERY_TOPIC_PREFIX = "homeassistant/sensor"
STATE_TOPIC_PREFIX = "azen"


def get_discovery_topic(serial: str) -> str:
    """Get the discovery topic pattern for a device serial."""
    return f"{DISCOVERY_TOPIC_PREFIX}/azen_{serial}/+/config"


def get_state_topic(serial: str) -> str:
    """Get the state topic pattern for a device serial."""
    return f"{STATE_TOPIC_PREFIX}/{serial}/sensor/+/state"


# Icon mapping
ICON_GRID = "mdi:transmission-tower"
ICON_BATTERY = "mdi:battery"
ICON_SOLAR = "mdi:solar-power"
ICON_INVERTER = "mdi:power-plug"
ICON_CONSUMPTION = "mdi:home-lightning-bolt"
ICON_VOLTAGE = "mdi:flash"
ICON_ENERGY = "mdi:lightning-bolt"
