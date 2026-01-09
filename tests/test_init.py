"""Test the Azimut Energy integration setup."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.azimut_energy.const import CONF_SERIAL, DOMAIN  # noqa: I001


async def test_setup_entry_success(
    hass: HomeAssistant,
    mock_mqtt_client: MagicMock,
    mock_config_entry: MagicMock,
) -> None:
    """Test successful setup of config entry."""
    with patch(
        "custom_components.azimut_energy.AzimutMQTTClient",
        return_value=mock_mqtt_client,
    ):
        from custom_components.azimut_energy import async_setup_entry

        # Mock the platform setup
        with patch.object(
            hass.config_entries, "async_forward_entry_setups", new_callable=AsyncMock
        ):
            result = await async_setup_entry(hass, mock_config_entry)

    assert result is True
    assert DOMAIN in hass.data
    assert mock_config_entry.entry_id in hass.data[DOMAIN]


async def test_setup_entry_connection_failure(
    hass: HomeAssistant,
    mock_mqtt_client_cannot_connect: MagicMock,
    mock_config_entry: MagicMock,
) -> None:
    """Test setup failure when MQTT connection fails."""
    with patch(
        "custom_components.azimut_energy.AzimutMQTTClient",
        return_value=mock_mqtt_client_cannot_connect,
    ):
        from custom_components.azimut_energy import async_setup_entry

        with pytest.raises(ConfigEntryNotReady):
            await async_setup_entry(hass, mock_config_entry)


async def test_unload_entry(
    hass: HomeAssistant,
    mock_mqtt_client: MagicMock,
    mock_config_entry: MagicMock,
) -> None:
    """Test unloading a config entry."""
    with patch(
        "custom_components.azimut_energy.AzimutMQTTClient",
        return_value=mock_mqtt_client,
    ):
        from custom_components.azimut_energy import (
            async_setup_entry,
            async_unload_entry,
        )

        # Setup first
        with patch.object(
            hass.config_entries, "async_forward_entry_setups", new_callable=AsyncMock
        ):
            await async_setup_entry(hass, mock_config_entry)

        # Now unload
        with patch.object(
            hass.config_entries,
            "async_unload_platforms",
            new_callable=AsyncMock,
            return_value=True,
        ):
            result = await async_unload_entry(hass, mock_config_entry)

    assert result is True
    assert mock_config_entry.entry_id not in hass.data[DOMAIN]


async def test_coordinator_callbacks(
    hass: HomeAssistant,
    mock_mqtt_client: MagicMock,
    mock_config_entry: MagicMock,
) -> None:
    """Test coordinator callback setup."""
    with patch(
        "custom_components.azimut_energy.AzimutMQTTClient",
        return_value=mock_mqtt_client,
    ):
        from custom_components.azimut_energy import async_setup_entry

        with patch.object(
            hass.config_entries, "async_forward_entry_setups", new_callable=AsyncMock
        ):
            await async_setup_entry(hass, mock_config_entry)

    # Verify MQTT client callbacks were set
    mock_mqtt_client.set_discovery_callback.assert_called_once()
    mock_mqtt_client.set_state_callback.assert_called_once()
    mock_mqtt_client.set_connection_callback.assert_called_once()


async def test_coordinator_connection_state(
    hass: HomeAssistant,
    mock_mqtt_client: MagicMock,
    mock_config_entry: MagicMock,
) -> None:
    """Test coordinator connection state property."""
    with patch(
        "custom_components.azimut_energy.AzimutMQTTClient",
        return_value=mock_mqtt_client,
    ):
        from custom_components.azimut_energy import async_setup_entry

        with patch.object(
            hass.config_entries, "async_forward_entry_setups", new_callable=AsyncMock
        ):
            await async_setup_entry(hass, mock_config_entry)

        coordinator = hass.data[DOMAIN][mock_config_entry.entry_id]
        assert coordinator.is_connected is True


async def test_coordinator_discovery_routing(
    hass: HomeAssistant,
    mock_mqtt_client: MagicMock,
    mock_config_entry: MagicMock,
) -> None:
    """Test coordinator routes discovery messages."""
    with patch(
        "custom_components.azimut_energy.AzimutMQTTClient",
        return_value=mock_mqtt_client,
    ):
        from custom_components.azimut_energy import async_setup_entry

        with patch.object(
            hass.config_entries, "async_forward_entry_setups", new_callable=AsyncMock
        ):
            await async_setup_entry(hass, mock_config_entry)

        coordinator = hass.data[DOMAIN][mock_config_entry.entry_id]

        # Set up a mock callback
        received = []
        coordinator.set_discovery_callback(lambda payload: received.append(payload))

        # Simulate discovery message from MQTT client
        # Get the callback that was registered with the MQTT client
        discovery_cb = mock_mqtt_client.set_discovery_callback.call_args[0][0]
        discovery_cb({"unique_id": "test", "name": "Test"})

        assert len(received) == 1
        assert received[0]["unique_id"] == "test"


async def test_coordinator_state_routing(
    hass: HomeAssistant,
    mock_mqtt_client: MagicMock,
    mock_config_entry: MagicMock,
) -> None:
    """Test coordinator routes state messages."""
    with patch(
        "custom_components.azimut_energy.AzimutMQTTClient",
        return_value=mock_mqtt_client,
    ):
        from custom_components.azimut_energy import async_setup_entry

        with patch.object(
            hass.config_entries, "async_forward_entry_setups", new_callable=AsyncMock
        ):
            await async_setup_entry(hass, mock_config_entry)

        coordinator = hass.data[DOMAIN][mock_config_entry.entry_id]

        # Set up a mock callback
        received = []
        coordinator.set_state_callback(
            lambda topic, value: received.append((topic, value))
        )

        # Simulate state message from MQTT client
        state_cb = mock_mqtt_client.set_state_callback.call_args[0][0]
        state_cb("test/topic", 42.0)

        assert len(received) == 1
        assert received[0] == ("test/topic", 42.0)
