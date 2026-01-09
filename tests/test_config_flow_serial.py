"""Test the Azimut Energy config flow with various serial number formats."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.azimut_energy.const import CONF_SERIAL, DOMAIN


async def test_form_with_leading_zero_serial(
    hass: HomeAssistant, mock_setup_entry: AsyncMock
) -> None:
    """Test that serial numbers with leading zeros are preserved as strings."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.azimut_energy.config_flow.AzimutMQTTClient"
    ) as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.connect = AsyncMock(return_value=True)
        mock_client.disconnect = AsyncMock()

        # Serial with leading zero
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "192.168.1.100",
                CONF_SERIAL: "012345",
            },
        )
        await hass.async_block_till_done()

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Azimut Battery 012345"
    # Verify leading zero is preserved
    assert result2["data"][CONF_SERIAL] == "012345"
    assert result2["data"][CONF_SERIAL].startswith("0")
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_with_all_zero_serial(
    hass: HomeAssistant, mock_setup_entry: AsyncMock
) -> None:
    """Test that serial numbers with all zeros are preserved."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.azimut_energy.config_flow.AzimutMQTTClient"
    ) as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.connect = AsyncMock(return_value=True)
        mock_client.disconnect = AsyncMock()

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "192.168.1.100",
                CONF_SERIAL: "000000",
            },
        )
        await hass.async_block_till_done()

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    # Verify zeros are preserved
    assert result2["data"][CONF_SERIAL] == "000000"
    assert len(mock_setup_entry.mock_calls) == 1


async def test_serial_number_string_preservation(hass: HomeAssistant) -> None:
    """Test that serial numbers are always treated as strings, not integers."""
    from custom_components.azimut_energy.const import (
        get_discovery_topic,
        get_state_topic,
    )

    # Serial with leading zeros
    serial_with_zeros = "007890"
    discovery_topic = get_discovery_topic(serial_with_zeros)
    state_topic = get_state_topic(serial_with_zeros)

    # Verify the serial is preserved in topics (not converted to 7890)
    assert "007890" in discovery_topic
    assert "007890" in state_topic
    assert discovery_topic == "homeassistant/sensor/azen_007890/+/config"
    assert state_topic == "azen/007890/sensor/+/state"
