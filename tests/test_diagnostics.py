"""Test the Azimut Energy diagnostics."""

from __future__ import annotations

from unittest.mock import MagicMock

from homeassistant.core import HomeAssistant

from custom_components.azimut_energy.const import DOMAIN


async def test_diagnostics(hass: HomeAssistant, mock_config_entry: MagicMock) -> None:
    """Test diagnostics."""
    from homeassistant.helpers import entity_registry as er

    from custom_components.azimut_energy.diagnostics import (
        async_get_config_entry_diagnostics,
    )

    # Initialize entity registry
    er.async_get(hass)

    mock_config_entry.add_to_hass(hass)

    # Set up coordinator in hass.data
    mock_coordinator = MagicMock()
    mock_coordinator.is_connected = True
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][mock_config_entry.entry_id] = mock_coordinator

    # Get diagnostics
    diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry)

    # Verify diagnostics structure
    assert "config_entry" in diagnostics
    assert diagnostics["config_entry"]["entry_id"] == mock_config_entry.entry_id
    assert diagnostics["config_entry"]["domain"] == DOMAIN
    assert diagnostics["config_entry"]["title"] == "Azimut Battery 504589"

    assert "connection" in diagnostics
    assert diagnostics["connection"]["host"] == "192.168.1.100"
    assert diagnostics["connection"]["port"] == 8883
    assert diagnostics["connection"]["serial"] == "504589"
    assert diagnostics["connection"]["connected"] is True

    assert "mqtt_topics" in diagnostics
    assert "homeassistant/sensor/azen_504589" in diagnostics["mqtt_topics"]["discovery"]
    assert "azen/504589/sensor" in diagnostics["mqtt_topics"]["state"]

    assert "sensors" in diagnostics
    assert diagnostics["sensors"]["count"] == 0
    assert diagnostics["sensors"]["entities"] == []


async def test_diagnostics_no_coordinator(
    hass: HomeAssistant, mock_config_entry: MagicMock
) -> None:
    """Test diagnostics when coordinator is not available."""
    from custom_components.azimut_energy.diagnostics import (
        async_get_config_entry_diagnostics,
    )

    mock_config_entry.add_to_hass(hass)

    # Don't set up coordinator - simulate it not being available
    hass.data.setdefault(DOMAIN, {})

    # Get diagnostics
    diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry)

    # Verify connection shows disconnected
    assert diagnostics["connection"]["connected"] is False
    assert diagnostics["sensors"]["count"] == 0


async def test_diagnostics_with_entities(
    hass: HomeAssistant, mock_config_entry: MagicMock
) -> None:
    """Test diagnostics with registered entities."""
    from homeassistant.helpers import entity_registry as er

    from custom_components.azimut_energy.diagnostics import (
        async_get_config_entry_diagnostics,
    )

    mock_config_entry.add_to_hass(hass)

    # Set up coordinator
    mock_coordinator = MagicMock()
    mock_coordinator.is_connected = True
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][mock_config_entry.entry_id] = mock_coordinator

    # Register a test entity
    entity_registry = er.async_get(hass)
    entity = entity_registry.async_get_or_create(
        "sensor",
        DOMAIN,
        "504589_battery_voltage",
        config_entry=mock_config_entry,
        original_name="Battery Voltage",
    )

    # Set state for the entity using the actual entity_id
    hass.states.async_set(entity.entity_id, "48.5", {"unit": "V"})

    # Get diagnostics
    diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry)

    # Verify sensor information is included
    assert diagnostics["sensors"]["count"] == 1
    assert len(diagnostics["sensors"]["entities"]) == 1

    sensor = diagnostics["sensors"]["entities"][0]
    assert sensor["unique_id"] == "504589_battery_voltage"
    assert sensor["state"] == "48.5"
    assert sensor["available"] is True


async def test_diagnostics_with_unavailable_entity(
    hass: HomeAssistant, mock_config_entry: MagicMock
) -> None:
    """Test diagnostics with an unavailable entity."""
    from homeassistant.helpers import entity_registry as er

    from custom_components.azimut_energy.diagnostics import (
        async_get_config_entry_diagnostics,
    )

    mock_config_entry.add_to_hass(hass)

    # Set up coordinator
    mock_coordinator = MagicMock()
    mock_coordinator.is_connected = False
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][mock_config_entry.entry_id] = mock_coordinator

    # Register a test entity
    entity_registry = er.async_get(hass)
    entity = entity_registry.async_get_or_create(
        "sensor",
        DOMAIN,
        "504589_battery_voltage",
        config_entry=mock_config_entry,
        original_name="Battery Voltage",
    )

    # Set state as unavailable using the actual entity_id
    hass.states.async_set(entity.entity_id, "unavailable")

    # Get diagnostics
    diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry)

    # Verify sensor is marked as unavailable
    sensor = diagnostics["sensors"]["entities"][0]
    assert sensor["state"] == "unavailable"
    assert sensor["available"] is False
