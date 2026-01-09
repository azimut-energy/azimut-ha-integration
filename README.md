# Azimut Energy

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![CI](https://github.com/azimut-energy/azimut-ha-integration/actions/workflows/ci.yml/badge.svg)](https://github.com/azimut-energy/azimut-ha-integration/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/badge/coverage-88%25-brightgreen)](https://github.com/azimut-energy/azimut-ha-integration)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Home Assistant integration for Azimut Energy Systems (Azen). Monitor your energy system including grid, battery, solar, and consumption data in real-time.

> **⚠️ Important Notice**
> This integration requires firmware with MQTT support, which is **not yet available** in the current production firmware.
> The firmware update with MQTT support is **planned for early January 2026**.
> This integration will not work until your Azimut Energy System is updated to the new firmware.

> **ℹ️ Support Notice**
> This integration is provided by Azimut Energy to enable sensor monitoring in Home Assistant.
> However, **Azimut Energy does not provide support for Home Assistant configurations or setup**.
> This integration solely exposes sensor data to Home Assistant - any questions about Home Assistant usage, automations, or dashboards should be directed to the [Home Assistant Community](https://community.home-assistant.io/).
> For integration-specific issues, use [GitHub Issues](https://github.com/azimut-energy/azimut-ha-integration/issues).

## Features

- **Automatic device discovery** - Devices are discovered via mDNS (Zeroconf) on your local network
- **Dynamic sensor discovery** - Sensors are automatically created based on your device configuration
- **Real-time updates** - Data pushed via MQTT for instant updates
- **Automatic reconnection** - Seamlessly recovers from network interruptions
- **Reconfigurable** - Change connection settings without removing the integration
- **Diagnostics support** - Download diagnostic information for troubleshooting
- **Grid monitoring** - Track power import/export and per-phase voltage
- **Battery status** - State of charge, power, voltage, and capacity
- **Solar production** - PV power and energy generation
- **Consumption tracking** - Monitor your total power consumption

## Requirements

- Home Assistant 2024.1.0 or newer
- Azimut Energy System with MQTT enabled
- Network access to the MQTT broker

## Installation

### HACS (Recommended)

1. Make sure you have [HACS](https://hacs.xyz/) installed
2. Add this repository as a custom repository in HACS:
   - Go to HACS → Integrations → ⋮ (menu) → Custom repositories
   - Add URL: `https://github.com/azimut-energy/azimut-ha-integration`
   - Category: Integration
3. Search for "Azimut Energy" in HACS
4. Click Install
5. Restart Home Assistant

### Manual Installation

1. Download the latest release from GitHub
2. Extract the `azimut_energy` folder into your `custom_components` directory:
   ```
   custom_components/
   └── azimut_energy/
       ├── __init__.py
       ├── config_flow.py
       ├── const.py
       ├── diagnostics.py
       ├── manifest.json
       ├── mqtt_client.py
       ├── sensor.py
       ├── strings.json
       └── translations/
           └── en.json
   ```
3. Restart Home Assistant

## Configuration

### Automatic Discovery (Recommended)

Azimut devices advertise themselves on your local network using mDNS (Zeroconf). Home Assistant will automatically detect your device:

1. In Home Assistant, go to **Settings** → **Devices & Services**
2. If a device is discovered, you'll see a notification: "Azimut Battery {serial} discovered"
3. Click **Configure** to add it
4. Confirm the device details and click **Submit**

The integration uses the `_azimut-broker._tcp` mDNS service type to discover devices.

### Manual Configuration

If automatic discovery doesn't work, you can manually add the integration:

#### Step 1: Add the Integration

1. In Home Assistant, go to **Settings** → **Devices & Services**
2. Click the **+ Add Integration** button
3. Search for **"Azimut Energy"**
4. Click to add it

#### Step 2: Enter Connection Details

You will be prompted to enter:

| Field | Description | Example |
|-------|-------------|---------|
| **IP Address** | IP address of your Azimut device | `192.168.1.100` |
| **Device Serial Number** | Your Azen device serial number | `504589` |

> **Note:** The port is always 8883 (MQTTS) and is not configurable.

#### Step 3: Complete Setup

Click **Submit**. The integration will:
1. Connect to the MQTT broker (using TLS without certificate verification)
2. Subscribe to discovery topics for your device
3. Automatically create sensors as they are discovered

### Reconfiguring the Integration

To change the IP address after setup:
1. Go to **Settings** → **Devices & Services**
2. Find the Azimut Energy integration
3. Click **Configure** to update the IP address

## Available Sensors

Sensors are dynamically created based on your device configuration. Common sensors include:

### Grid Sensors

| Sensor | Unit | Description |
|--------|------|-------------|
| Grid Power | W | Total grid power (positive = import, negative = export) |
| Grid Power L1/L2/L3 | W | Per-phase grid power |
| Grid Voltage L1/L2/L3 | V | Per-phase grid voltage |
| Grid Energy Import | kWh | Total energy imported from grid |
| Grid Energy Export | kWh | Total energy exported to grid |

### Battery Sensors

| Sensor | Unit | Description |
|--------|------|-------------|
| Battery State of Charge | % | Current battery level |
| Battery Power | W | Battery power (positive = discharging, negative = charging) |
| Battery Voltage | V | Battery voltage |
| Battery Capacity | Ah | Battery capacity |

### Solar Sensors

| Sensor | Unit | Description |
|--------|------|-------------|
| PV Power | W | Current solar production |
| PV Energy | kWh | Total solar energy produced today |
| MPPT Power | W | MPPT controller power |

### Other Sensors

| Sensor | Unit | Description |
|--------|------|-------------|
| Inverter Power | W | Inverter output power |
| Consumption Power | W | Total home consumption |

## Energy Dashboard Integration

The Azimut Energy sensors are fully compatible with Home Assistant's Energy Dashboard. To set it up:

1. Go to **Settings** → **Dashboards** → **Energy**
2. Configure the following:

### Grid Configuration
- **Grid consumption**: Select `Grid Energy Import`
- **Return to grid**: Select `Grid Energy Export`

### Solar Configuration
- **Solar production**: Select `PV Energy`

### Battery Configuration
- **Battery energy in**: Use a helper to track energy charged
- **Battery energy out**: Use a helper to track energy discharged

## Example Automations

### Low Battery Alert

```yaml
automation:
  - alias: "Low Battery Alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.azen_504589_battery_soc
        below: 20
    action:
      - service: notify.mobile_app
        data:
          title: "Battery Low"
          message: "Battery is at {{ states('sensor.azen_504589_battery_soc') }}%"
```

### High Solar Production Notification

```yaml
automation:
  - alias: "High Solar Production"
    trigger:
      - platform: numeric_state
        entity_id: sensor.azen_504589_pv_power
        above: 5000
    action:
      - service: notify.mobile_app
        data:
          title: "High Solar Production"
          message: "Solar panels producing {{ states('sensor.azen_504589_pv_power') }}W!"
```

### Grid Export Alert

```yaml
automation:
  - alias: "Exporting to Grid"
    trigger:
      - platform: numeric_state
        entity_id: sensor.azen_504589_grid_power
        below: -1000
    action:
      - service: notify.mobile_app
        data:
          title: "Exporting Power"
          message: "Exporting {{ (states('sensor.azen_504589_grid_power') | float | abs) | round(0) }}W to the grid"
```

### Battery Charging from Solar Only

```yaml
automation:
  - alias: "Battery Charging from Solar"
    trigger:
      - platform: numeric_state
        entity_id: sensor.azen_504589_battery_power
        below: -500
    condition:
      - condition: numeric_state
        entity_id: sensor.azen_504589_pv_power
        above: 1000
    action:
      - service: logbook.log
        data:
          name: "Battery"
          message: "Charging at {{ (states('sensor.azen_504589_battery_power') | float | abs) | round(0) }}W from solar"
```

## Dashboard Examples

### Energy Flow Card

Create a visual energy flow using the `power-flow-card`:

```yaml
type: custom:power-flow-card
entities:
  battery:
    entity: sensor.azen_504589_battery_power
    state_of_charge: sensor.azen_504589_battery_soc
  grid:
    entity: sensor.azen_504589_grid_power
  solar:
    entity: sensor.azen_504589_pv_power
  home:
    entity: sensor.azen_504589_consumption_power
```

### Simple Gauge Cards

```yaml
type: vertical-stack
cards:
  - type: gauge
    entity: sensor.azen_504589_battery_soc
    name: Battery
    min: 0
    max: 100
    severity:
      green: 50
      yellow: 20
      red: 10
  - type: gauge
    entity: sensor.azen_504589_pv_power
    name: Solar Production
    min: 0
    max: 10000
    unit: W
```

## Troubleshooting

### Integration won't connect

**Symptoms:** Setup fails with "Failed to connect to the MQTT broker"

**Solutions:**
1. **Check network connectivity**
   - Ensure Home Assistant can reach the MQTT broker IP address
   - Try pinging the broker from the HA host: `ping 192.168.1.100`

2. **Verify port configuration**
   - Default port is 8883 (MQTTS with TLS)
   - Check your Azen device configuration for the correct port

3. **Check firewall rules**
   - Ensure port 8883 is open between Home Assistant and the broker

4. **View detailed logs**
   - Go to Settings → System → Logs
   - Filter by "azimut_energy" to see connection errors

### Sensors not appearing

**Symptoms:** Integration connects but no sensors are created

**Solutions:**
1. **Wait for discovery messages**
   - Sensors are created when the device publishes discovery messages
   - This may take up to 60 seconds after connection

2. **Verify device serial number**
   - Check that the serial number matches your device exactly
   - Serial is case-sensitive

3. **Check MQTT topics**
   - Discovery topic format: `homeassistant/sensor/azen_{serial}/+/config`
   - Use an MQTT client (like MQTT Explorer) to verify messages

4. **Enable debug logging**
   Add to `configuration.yaml`:
   ```yaml
   logger:
     logs:
       custom_components.azimut_energy: debug
   ```

### Sensors become unavailable

**Symptoms:** Sensors show "Unavailable" after working

**Causes:**
1. **Device offline** - The Azen device is not sending data
2. **Network issues** - Connection between device and broker interrupted
3. **Broker issues** - MQTT broker is down or overloaded

**What happens:**
- Sensors become unavailable after 5 minutes without updates
- The integration automatically reconnects (every 30 seconds)
- Sensors become available again when data is received

**Solutions:**
1. Check the Azen device is powered on and connected
2. Verify the MQTT broker is running
3. Check network connectivity between all components

### Connection keeps dropping

**Symptoms:** Frequent disconnection/reconnection in logs

**Solutions:**
1. **Check network stability**
   - Look for packet loss or high latency
   - Consider using a wired connection

2. **Adjust keepalive settings**
   - Default keepalive is 60 seconds
   - Some networks may require shorter intervals

3. **Check broker capacity**
   - Ensure the MQTT broker isn't overloaded
   - Check broker logs for errors

## Diagnostics

To download diagnostic information for troubleshooting:

1. Go to **Settings** → **Devices & Services**
2. Find the Azimut Energy integration
3. Click the three dots menu (⋮)
4. Select **Download diagnostics**

The diagnostics file includes:
- Connection status
- MQTT topic subscriptions
- List of discovered sensors
- Current sensor states

## Debug Logging

To enable detailed debug logging, add this to your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.azimut_energy: debug
    custom_components.azimut_energy.mqtt_client: debug
```

After restarting, check the logs at Settings → System → Logs.

## Development

### Running Tests

This project has comprehensive test coverage (86%). To run tests:

```bash
# Install test dependencies
pip install -r requirements_test.txt

# Run tests with coverage
pytest tests/ -v --cov=custom_components --cov-report=term-missing

# Run tests quickly (no coverage)
pytest tests/ -q
```

### Pre-commit Hook

A pre-commit hook is automatically installed that runs tests before each commit. This ensures all tests pass before code is committed.

To manually run the pre-commit checks:

```bash
.git/hooks/pre-commit
```

### Using pre-commit Framework (Optional)

For additional code quality checks, you can use the pre-commit framework:

```bash
# Install pre-commit
pip install pre-commit

# Install the git hooks
pre-commit install

# Run manually on all files
pre-commit run --all-files
```

This will automatically run:
- Black (code formatting)
- isort (import sorting)
- Ruff (linting)
- pytest (tests)

### Code Style

This project follows:
- **Black** for code formatting (88 character line length)
- **isort** for import sorting
- **Ruff** for linting
- **Type hints** where appropriate

## Support

For support, please:
1. Check the troubleshooting section above
2. Download diagnostics and enable debug logging
3. Open an issue in the [GitHub repository](https://github.com/azimut-energy/azimut-ha-integration) with:
   - Home Assistant version
   - Integration version
   - Diagnostics file
   - Relevant log entries
   - Steps to reproduce the issue

## License

This project is licensed under the MIT License - see the LICENSE file for details.
