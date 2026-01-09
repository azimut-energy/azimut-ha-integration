# Azen Home Assistant Integration - MQTT Protocol Reference

This document describes the MQTT protocol used by the Azen energy system for integration with Home Assistant. Use this as a reference when developing the Python-based Home Assistant custom integration.

## MQTT Broker Connection

The Azen system publishes to an MQTT broker. Home Assistant should connect to this broker to receive sensor data.

**Default broker**: `externalmqttbroker:1883` (configurable)

## Auto-Discovery Protocol

The Azen system uses [Home Assistant MQTT Discovery](https://www.home-assistant.io/integrations/mqtt/#mqtt-discovery) to automatically register sensors.

### Discovery Topic Format

```
homeassistant/sensor/azen_{serial}/{sensor_id}/config
```

- `{serial}`: Device serial number (e.g., `ABC123`)
- `{sensor_id}`: Sensor identifier (e.g., `grid_power`, `battery_soc`)

### Discovery Payload Schema

```json
{
  "name": "string",
  "unique_id": "azen_{serial}_{sensor_id}",
  "state_topic": "azen/{serial}/sensor/{sensor_id}/state",
  "unit_of_measurement": "string",
  "device_class": "string",
  "state_class": "string",
  "icon": "string",
  "expire_after": 300,
  "device": {
    "identifiers": ["azen_{serial}"],
    "name": "Azen {serial}",
    "manufacturer": "Azimut",
    "model": "Azen Energy System",
    "sw_version": "string"
  }
}
```

### Discovery Payload Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Human-readable sensor name |
| `unique_id` | string | Yes | Unique identifier for the entity |
| `state_topic` | string | Yes | Topic where state values are published |
| `unit_of_measurement` | string | No | Unit (e.g., "W", "kWh", "%", "V") |
| `device_class` | string | No | HA device class (see below) |
| `state_class` | string | No | HA state class (see below) |
| `icon` | string | No | MDI icon (e.g., "mdi:battery") |
| `expire_after` | int | No | Seconds until sensor becomes unavailable (default: 300) |
| `device` | object | Yes | Device information for grouping |

### Device Classes Used

| Device Class | Description |
|--------------|-------------|
| `power` | Power in Watts |
| `energy` | Energy in kWh |
| `voltage` | Voltage in Volts |
| `battery` | Battery percentage |

### State Classes Used

| State Class | Description |
|-------------|-------------|
| `measurement` | Instantaneous value that can go up or down |
| `total_increasing` | Cumulative value that only increases (resets allowed) |

## State Topic Format

```
azen/{serial}/sensor/{sensor_id}/state
```

### State Payload

The payload is a **plain numeric string** with 2 decimal places:

```
1234.56
```

**Not JSON** - just the raw number as a string.

## Complete Sensor List

### Grid Sensors

| sensor_id | name | unit | device_class | state_class |
|-----------|------|------|--------------|-------------|
| `grid_power` | Grid Power | W | power | measurement |
| `grid_power_l1` | Grid Power L1 | W | power | measurement |
| `grid_power_l2` | Grid Power L2 | W | power | measurement |
| `grid_power_l3` | Grid Power L3 | W | power | measurement |
| `grid_voltage_l1` | Grid Voltage L1 | V | voltage | measurement |
| `grid_voltage_l2` | Grid Voltage L2 | V | voltage | measurement |
| `grid_voltage_l3` | Grid Voltage L3 | V | voltage | measurement |
| `grid_energy_import` | Grid Energy Import | kWh | energy | total_increasing |
| `grid_energy_export` | Grid Energy Export | kWh | energy | total_increasing |

### Battery Sensors

| sensor_id | name | unit | device_class | state_class |
|-----------|------|------|--------------|-------------|
| `battery_soc` | Battery State of Charge | % | battery | measurement |
| `battery_power` | Battery Power | W | power | measurement |
| `battery_voltage` | Battery Voltage | V | voltage | measurement |
| `battery_capacity` | Battery Capacity | Ah | *(none)* | measurement |

### Solar Sensors

| sensor_id | name | unit | device_class | state_class |
|-----------|------|------|--------------|-------------|
| `pv_power` | Solar Power | W | power | measurement |
| `pv_energy` | Solar Energy Today | kWh | energy | total_increasing |
| `mppt_power` | MPPT Power | W | power | measurement |

### Inverter Sensors

| sensor_id | name | unit | device_class | state_class |
|-----------|------|------|--------------|-------------|
| `inverter_power` | Inverter Power | W | power | measurement |

### Consumption Sensors

| sensor_id | name | unit | device_class | state_class |
|-----------|------|------|--------------|-------------|
| `consumption_power` | Total Consumption | W | power | measurement |

## Example MQTT Messages

### Discovery Message Example

**Topic**: `homeassistant/sensor/azen_ABC123/grid_power/config`

**Payload**:
```json
{
  "name": "Grid Power",
  "unique_id": "azen_ABC123_grid_power",
  "state_topic": "azen/ABC123/sensor/grid_power/state",
  "unit_of_measurement": "W",
  "device_class": "power",
  "state_class": "measurement",
  "icon": "mdi:transmission-tower",
  "expire_after": 300,
  "device": {
    "identifiers": ["azen_ABC123"],
    "name": "Azen ABC123",
    "manufacturer": "Azimut",
    "model": "Azen Energy System",
    "sw_version": "0.0.1"
  }
}
```

**Retained**: Yes

### State Message Example

**Topic**: `azen/ABC123/sensor/grid_power/state`

**Payload**: `1523.45`

**Retained**: No

## Python Integration Pseudocode

```python
import json
from homeassistant.components import mqtt
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import UnitOfPower, UnitOfEnergy, PERCENTAGE

DOMAIN = "azen"

# Subscribe to discovery topics
DISCOVERY_TOPIC = "homeassistant/sensor/azen_+/+/config"

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Azen sensors from discovery."""
    
    @callback
    def message_received(msg):
        """Handle discovery message."""
        payload = json.loads(msg.payload)
        
        # Extract sensor info
        unique_id = payload["unique_id"]
        name = payload["name"]
        state_topic = payload["state_topic"]
        unit = payload.get("unit_of_measurement")
        device_class = payload.get("device_class")
        state_class = payload.get("state_class")
        device_info = payload.get("device", {})
        
        # Create sensor entity
        sensor = AzenSensor(
            unique_id=unique_id,
            name=name,
            state_topic=state_topic,
            unit=unit,
            device_class=device_class,
            state_class=state_class,
            device_info=device_info,
        )
        async_add_entities([sensor])
    
    await mqtt.async_subscribe(hass, DISCOVERY_TOPIC, message_received)


class AzenSensor(SensorEntity):
    """Azen sensor entity."""
    
    def __init__(self, unique_id, name, state_topic, unit, device_class, state_class, device_info):
        self._attr_unique_id = unique_id
        self._attr_name = name
        self._state_topic = state_topic
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_device_info = {
            "identifiers": set(device_info.get("identifiers", [])),
            "name": device_info.get("name"),
            "manufacturer": device_info.get("manufacturer"),
            "model": device_info.get("model"),
            "sw_version": device_info.get("sw_version"),
        }
        self._attr_native_value = None
    
    async def async_added_to_hass(self):
        """Subscribe to state topic."""
        @callback
        def state_message_received(msg):
            try:
                self._attr_native_value = float(msg.payload)
                self.async_write_ha_state()
            except ValueError:
                pass
        
        await mqtt.async_subscribe(
            self.hass, 
            self._state_topic, 
            state_message_received
        )
```

## Topics to Subscribe

For a Python integration, subscribe to these topics:

| Purpose | Topic Pattern | Notes |
|---------|---------------|-------|
| Discovery | `homeassistant/sensor/azen_+/+/config` | Retained, JSON payload |
| All states | `azen/+/sensor/+/state` | Numeric string payload |
| Specific device | `azen/{serial}/sensor/+/state` | Filter by serial |

## Value Interpretation

### Power Values (W)

- **Positive**: Power flowing in expected direction
- **Negative**: Power flowing in reverse direction

| Sensor | Positive | Negative |
|--------|----------|----------|
| `grid_power` | Importing from grid | Exporting to grid |
| `battery_power` | Discharging | Charging |
| `pv_power` | Producing | N/A (always ≥ 0) |
| `consumption_power` | Consuming | N/A (always ≥ 0) |

### Energy Values (kWh)

- Always positive
- Monotonically increasing (resets at midnight or device restart)
- Use `state_class: total_increasing` for proper statistics

## Update Frequency

- State updates are debounced at **100ms** intervals
- Sensors expire after **300 seconds** (5 minutes) of no updates
- Typical update rate: **1-5 seconds** depending on the sensor

## Error Handling

1. **Sensor unavailable**: No message received within `expire_after` seconds
2. **Invalid payload**: Non-numeric state value (should be ignored)
3. **Device offline**: All sensors for a device become unavailable simultaneously

