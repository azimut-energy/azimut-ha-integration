# CLAUDE.md - AI Assistant Guide for Azimut HA Integration

This document provides essential context for AI assistants working on this codebase.

## Project Overview

**Azimut HA Integration** is a Home Assistant custom integration for Azimut Energy Systems (Azen). It enables monitoring of energy systems including grid, battery, solar, and consumption data via MQTT.

- **Version**: 1.2.0
- **Python**: 3.11+
- **Home Assistant**: 2024.1.0+
- **Main Dependency**: `aiomqtt>=2.0.0`

## Repository Structure

```
azimut-ha-integration/
├── custom_components/azimut_energy/   # Main integration code
│   ├── __init__.py          # Entry point, AzimutMQTTCoordinator
│   ├── config_flow.py       # Configuration UI (manual + zeroconf discovery)
│   ├── const.py             # Constants, MQTT topics, icons
│   ├── mqtt_client.py       # MQTT client with auto-reconnect
│   ├── sensor.py            # Sensor entities (dynamic discovery)
│   ├── binary_sensor.py     # Connection status binary sensor
│   ├── diagnostics.py       # Diagnostics export for troubleshooting
│   ├── manifest.json        # HA integration manifest
│   ├── strings.json         # UI strings (English base)
│   └── translations/        # Localized UI strings (en, de, fr, nl)
├── tests/                   # Pytest test suite
│   ├── conftest.py          # Shared fixtures
│   ├── test_config_flow.py  # Config flow tests
│   ├── test_config_flow_serial.py
│   ├── test_init.py         # Integration setup tests
│   ├── test_mqtt_client.py  # MQTT client unit tests
│   ├── test_sensor.py       # Sensor entity tests
│   ├── test_binary_sensor.py
│   └── test_diagnostics.py
├── .github/workflows/       # CI/CD pipelines
│   ├── ci.yml               # Lint, test, validate, HACS check
│   ├── release.yml          # Release automation
│   └── hassfest.yaml        # Home Assistant manifest validation
├── .devcontainer/           # VS Code dev container setup
├── pyproject.toml           # Project config, tool settings
├── requirements_test.txt    # Test dependencies
└── .pre-commit-config.yaml  # Pre-commit hooks configuration
```

## Key Architecture Patterns

### MQTT Communication Flow

1. **Discovery**: Device publishes sensor configs to `homeassistant/sensor/azen_{serial}/+/config`
2. **State Updates**: Device publishes values to `azen/{serial}/sensor/+/state`
3. **Republish Command**: On reconnect, publishes to `azen/{serial}/command/republish` to request fresh values

### Component Hierarchy

```
ConfigEntry
    └── AzimutMQTTCoordinator (__init__.py)
            ├── AzimutMQTTClient (mqtt_client.py) - handles MQTT connection
            ├── AzimutSensor (sensor.py) - dynamically created from discovery
            ├── AzimutDiagnosticSensor (sensor.py) - stats sensors
            └── AzimutConnectionSensor (binary_sensor.py) - connection status
```

### Callback Pattern

The coordinator uses callbacks to decouple MQTT messages from entity updates:
- `set_discovery_callback()` - for new sensor discovery
- `set_state_callback()` - for value updates
- `set_connection_callback()` - for connection state changes

## Development Commands

### Running Tests

```bash
# Install dependencies
pip install -r requirements_test.txt

# Run all tests with coverage
pytest tests/ -v --cov=custom_components --cov-report=term-missing

# Run specific test file
pytest tests/test_mqtt_client.py -v

# Run tests quickly (no coverage)
pytest tests/ -q
```

### Linting & Formatting

```bash
# Check code style
ruff check .
black --check .
isort --check-only .

# Auto-fix issues
ruff check --fix .
black .
isort .
```

### Pre-commit Hooks

```bash
# Install pre-commit framework
pip install pre-commit
pre-commit install

# Run all checks manually
pre-commit run --all-files
```

## Code Style Guidelines

- **Formatter**: Black (88 char line length)
- **Import Sorting**: isort with black profile
- **Linter**: Ruff (pycodestyle, pyflakes, isort, bugbear, comprehensions, pyupgrade)
- **Type Hints**: Use where appropriate, especially in public APIs

### Import Order

```python
from __future__ import annotations

import asyncio  # stdlib
import logging

import aiomqtt  # third-party
from homeassistant.core import HomeAssistant

from .const import DOMAIN  # local
```

## Testing Conventions

### Fixture Usage

The test suite uses `pytest-homeassistant-custom-component` for HA testing infrastructure.

Key fixtures in `conftest.py`:
- `mock_mqtt_client` - mocked MQTT client that connects successfully
- `mock_mqtt_client_cannot_connect` - mocked client that fails to connect
- `mock_config_entry` - pre-configured config entry
- `auto_enable_custom_integrations` - auto-applied to enable custom components

### Test Patterns

```python
async def test_example(hass: HomeAssistant, mock_mqtt_client):
    """Test description."""
    # Arrange
    entry = MockConfigEntry(domain=DOMAIN, data={...})
    entry.add_to_hass(hass)

    # Act
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Assert
    assert hass.states.get("sensor.azen_504589_example")
```

## CI/CD Pipeline

### GitHub Actions Workflows

1. **CI (ci.yml)** - Runs on push/PR to main:
   - `lint`: ruff, black, isort checks
   - `test`: pytest with coverage
   - `validate`: manifest.json and translations validation
   - `hacs`: HACS integration validation

2. **Release (release.yml)** - Automated releases via release-please

3. **Hassfest (hassfest.yaml)** - Home Assistant manifest validation

### Required Checks

All PRs must pass:
- Linting (ruff, black, isort)
- Tests (pytest)
- HACS validation
- Manifest validation

## Key Constants

From `const.py`:
- `DOMAIN = "azimut_energy"`
- `MQTT_PORT = 8883` (MQTTS)
- `MQTT_USE_TLS = True`
- `MQTT_KEEPALIVE = 30` seconds
- `DEFAULT_EXPIRE_AFTER = 120` seconds (sensor unavailable timeout)

## Common Tasks

### Adding a New Sensor Type

1. Sensors are created dynamically from MQTT discovery messages
2. Device class mappings are in `sensor.py:DEVICE_CLASS_MAP`
3. State class mappings are in `sensor.py:STATE_CLASS_MAP`
4. Add translations in `translations/*.json` if needed

### Modifying Config Flow

1. Edit `config_flow.py`
2. Update `strings.json` for new UI text
3. Sync translations in `translations/en.json`
4. Add tests in `test_config_flow.py`

### Adding a New Platform

1. Add platform name to `PLATFORMS` list in `__init__.py`
2. Create `{platform}.py` with `async_setup_entry()` function
3. Add corresponding test file

## Debugging Tips

### Enable Debug Logging

Add to HA `configuration.yaml`:
```yaml
logger:
  logs:
    custom_components.azimut_energy: debug
    custom_components.azimut_energy.mqtt_client: debug
```

### Diagnostics

The integration supports HA's diagnostic download feature. See `diagnostics.py` for exported data structure.

## Important Notes

1. **MQTT Connection**: Uses TLS without certificate verification (`CERT_NONE`)
2. **Sensor Discovery**: Sensors appear only after device publishes discovery messages
3. **Reconnection**: Automatic with exponential backoff (1s to 30s)
4. **Availability**: Sensors become unavailable after 120s without updates
5. **Zeroconf**: Discovers devices via `_azimut-broker._tcp` mDNS service

## Version History

See `CHANGELOG.md` for detailed release notes. Key recent changes:
- **v1.2.0**: Added republish command topic support on reconnect
- **v1.1.0**: Added binary sensor support, translation keys, enhanced diagnostics
