"""Test the Azimut Energy config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant import config_entries
from homeassistant.components import zeroconf
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.azimut_energy.const import CONF_SERIAL, DOMAIN


async def test_form(hass: HomeAssistant, mock_setup_entry: AsyncMock) -> None:
    """Test we get the form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {}

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
                CONF_SERIAL: "504589",
            },
        )
        await hass.async_block_till_done()

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Azimut Battery 504589"
    assert result2["data"] == {
        CONF_HOST: "192.168.1.100",
        CONF_SERIAL: "504589",
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_cannot_connect(hass: HomeAssistant) -> None:
    """Test we handle cannot connect error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.azimut_energy.config_flow.AzimutMQTTClient"
    ) as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.connect = AsyncMock(return_value=False)
        mock_client.disconnect = AsyncMock()

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "192.168.1.100",
                CONF_SERIAL: "504589",
            },
        )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_form_already_configured(
    hass: HomeAssistant, mock_setup_entry: AsyncMock
) -> None:
    """Test we abort if already configured."""
    # Create an existing entry
    entry = MockConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Azimut Battery 504589",
        data={
            CONF_HOST: "192.168.1.100",
            CONF_SERIAL: "504589",
        },
        source=config_entries.SOURCE_USER,
        unique_id="azimut_energy_504589",
    )
    entry.add_to_hass(hass)

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
                CONF_HOST: "192.168.1.200",
                CONF_SERIAL: "504589",
            },
        )

    assert result2["type"] == FlowResultType.ABORT
    assert result2["reason"] == "already_configured"


async def test_zeroconf_discovery(
    hass: HomeAssistant, mock_setup_entry: AsyncMock
) -> None:
    """Test zeroconf discovery."""
    discovery_info = zeroconf.ZeroconfServiceInfo(
        ip_address="192.168.1.100",
        ip_addresses=["192.168.1.100"],
        hostname="azen-504589.local.",
        name="Zephyr Azimut Broker on azen-504589._azimut-broker._tcp.local.",
        port=8883,
        properties={},
        type="_azimut-broker._tcp.local.",
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=discovery_info,
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "zeroconf_confirm"

    with patch(
        "custom_components.azimut_energy.config_flow.AzimutMQTTClient"
    ) as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.connect = AsyncMock(return_value=True)
        mock_client.disconnect = AsyncMock()

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {},
        )
        await hass.async_block_till_done()

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Azimut Battery 504589"
    assert result2["data"] == {
        CONF_HOST: "192.168.1.100",
        CONF_SERIAL: "504589",
    }


async def test_zeroconf_already_configured(hass: HomeAssistant) -> None:
    """Test zeroconf discovery when already configured."""
    # Create an existing entry
    entry = MockConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Azimut Battery 504589",
        data={
            CONF_HOST: "192.168.1.100",
            CONF_SERIAL: "504589",
        },
        source=config_entries.SOURCE_USER,
        unique_id="azimut_energy_504589",
    )
    entry.add_to_hass(hass)

    discovery_info = zeroconf.ZeroconfServiceInfo(
        ip_address="192.168.1.200",
        ip_addresses=["192.168.1.200"],
        hostname="azen-504589.local.",
        name="Zephyr Azimut Broker on azen-504589._azimut-broker._tcp.local.",
        port=8883,
        properties={},
        type="_azimut-broker._tcp.local.",
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=discovery_info,
    )

    # Should abort because already configured
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_options_flow(hass: HomeAssistant) -> None:
    """Test options flow."""
    entry = MockConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Azimut Battery 504589",
        data={
            CONF_HOST: "192.168.1.100",
            CONF_SERIAL: "504589",
        },
        source=config_entries.SOURCE_USER,
        unique_id="azimut_energy_504589",
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"

    with patch(
        "custom_components.azimut_energy.config_flow.AzimutMQTTClient"
    ) as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.connect = AsyncMock(return_value=True)
        mock_client.disconnect = AsyncMock()

        result2 = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "192.168.1.200",
            },
        )

    assert result2["type"] == FlowResultType.CREATE_ENTRY

    # Verify entry was updated
    assert entry.data[CONF_HOST] == "192.168.1.200"


async def test_options_flow_cannot_connect(hass: HomeAssistant) -> None:
    """Test options flow with connection failure."""
    entry = MockConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Azimut Battery 504589",
        data={
            CONF_HOST: "192.168.1.100",
            CONF_SERIAL: "504589",
        },
        source=config_entries.SOURCE_USER,
        unique_id="azimut_energy_504589",
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    with patch(
        "custom_components.azimut_energy.config_flow.AzimutMQTTClient"
    ) as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.connect = AsyncMock(return_value=False)
        mock_client.disconnect = AsyncMock()

        result2 = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "invalid.host",
            },
        )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_reconfigure_flow(hass: HomeAssistant) -> None:
    """Test reconfigure flow."""
    entry = MockConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Azimut Battery 504589",
        data={
            CONF_HOST: "192.168.1.100",
            CONF_SERIAL: "504589",
        },
        source=config_entries.SOURCE_USER,
        unique_id="azimut_energy_504589",
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": entry.entry_id,
        },
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    with patch(
        "custom_components.azimut_energy.config_flow.AzimutMQTTClient"
    ) as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.connect = AsyncMock(return_value=True)
        mock_client.disconnect = AsyncMock()

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "192.168.1.200",
            },
        )

    assert result2["type"] == FlowResultType.ABORT
    assert result2["reason"] == "reconfigure_successful"


async def test_zeroconf_no_serial_in_name(hass: HomeAssistant) -> None:
    """Test zeroconf discovery without serial in name."""
    discovery_info = zeroconf.ZeroconfServiceInfo(
        ip_address="192.168.1.100",
        ip_addresses=["192.168.1.100"],
        hostname="unknown.local.",
        name="Some Unknown Device._azimut-broker._tcp.local.",
        port=8883,
        properties={},
        type="_azimut-broker._tcp.local.",
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=discovery_info,
    )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "no_serial"


async def test_zeroconf_serial_from_properties(
    hass: HomeAssistant, mock_setup_entry: AsyncMock
) -> None:
    """Test zeroconf discovery with serial in properties."""
    discovery_info = zeroconf.ZeroconfServiceInfo(
        ip_address="192.168.1.100",
        ip_addresses=["192.168.1.100"],
        hostname="device.local.",
        name="Device._azimut-broker._tcp.local.",
        port=8883,
        properties={"serial": "504589"},
        type="_azimut-broker._tcp.local.",
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=discovery_info,
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "zeroconf_confirm"

    with patch(
        "custom_components.azimut_energy.config_flow.AzimutMQTTClient"
    ) as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.connect = AsyncMock(return_value=True)
        mock_client.disconnect = AsyncMock()

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {},
        )

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["data"][CONF_SERIAL] == "504589"


async def test_reconfigure_flow_connection_failure(hass: HomeAssistant) -> None:
    """Test reconfigure flow with connection failure."""
    entry = MockConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Azimut Battery 504589",
        data={
            CONF_HOST: "192.168.1.100",
            CONF_SERIAL: "504589",
        },
        source=config_entries.SOURCE_USER,
        unique_id="azimut_energy_504589",
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": entry.entry_id,
        },
    )

    with patch(
        "custom_components.azimut_energy.config_flow.AzimutMQTTClient"
    ) as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.connect = AsyncMock(return_value=False)
        mock_client.disconnect = AsyncMock()

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "192.168.1.200",
            },
        )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_form_exception_handling(hass: HomeAssistant) -> None:
    """Test exception handling in user form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.azimut_energy.config_flow.AzimutMQTTClient"
    ) as mock_client_class:
        mock_client = mock_client_class.return_value
        # Raise exception during connect
        mock_client.connect = AsyncMock(side_effect=Exception("Test exception"))
        mock_client.disconnect = AsyncMock()

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "192.168.1.100",
                CONF_SERIAL: "504589",
            },
        )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_zeroconf_confirm_connection_failure(hass: HomeAssistant) -> None:
    """Test connection failure (returns False) in zeroconf confirm."""
    discovery_info = zeroconf.ZeroconfServiceInfo(
        ip_address="192.168.1.100",
        ip_addresses=["192.168.1.100"],
        hostname="azen-504589.local.",
        name="Zephyr Azimut Broker on azen-504589._azimut-broker._tcp.local.",
        port=8883,
        properties={},
        type="_azimut-broker._tcp.local.",
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=discovery_info,
    )

    with patch(
        "custom_components.azimut_energy.config_flow.AzimutMQTTClient"
    ) as mock_client_class:
        mock_client = mock_client_class.return_value
        # Connection fails (returns False, not exception)
        mock_client.connect = AsyncMock(return_value=False)
        mock_client.disconnect = AsyncMock()

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {},
        )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_zeroconf_confirm_exception_handling(hass: HomeAssistant) -> None:
    """Test exception handling in zeroconf confirm."""
    discovery_info = zeroconf.ZeroconfServiceInfo(
        ip_address="192.168.1.100",
        ip_addresses=["192.168.1.100"],
        hostname="azen-504589.local.",
        name="Zephyr Azimut Broker on azen-504589._azimut-broker._tcp.local.",
        port=8883,
        properties={},
        type="_azimut-broker._tcp.local.",
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=discovery_info,
    )

    with patch(
        "custom_components.azimut_energy.config_flow.AzimutMQTTClient"
    ) as mock_client_class:
        mock_client = mock_client_class.return_value
        # Raise exception during connect
        mock_client.connect = AsyncMock(side_effect=Exception("Test exception"))
        mock_client.disconnect = AsyncMock()

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {},
        )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_reconfigure_missing_entry(hass: HomeAssistant) -> None:
    """Test reconfigure flow with missing entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": "nonexistent_entry_id",
        },
    )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reconfigure_failed"


async def test_reconfigure_exception_handling(hass: HomeAssistant) -> None:
    """Test exception handling in reconfigure flow."""
    entry = MockConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Azimut Battery 504589",
        data={
            CONF_HOST: "192.168.1.100",
            CONF_SERIAL: "504589",
        },
        source=config_entries.SOURCE_USER,
        unique_id="azimut_energy_504589",
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": entry.entry_id,
        },
    )

    with patch(
        "custom_components.azimut_energy.config_flow.AzimutMQTTClient"
    ) as mock_client_class:
        mock_client = mock_client_class.return_value
        # Raise exception during connect
        mock_client.connect = AsyncMock(side_effect=Exception("Test exception"))
        mock_client.disconnect = AsyncMock()

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "192.168.1.200",
            },
        )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_options_flow_exception_handling(hass: HomeAssistant) -> None:
    """Test exception handling in options flow."""
    entry = MockConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Azimut Battery 504589",
        data={
            CONF_HOST: "192.168.1.100",
            CONF_SERIAL: "504589",
        },
        source=config_entries.SOURCE_USER,
        unique_id="azimut_energy_504589",
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    with patch(
        "custom_components.azimut_energy.config_flow.AzimutMQTTClient"
    ) as mock_client_class:
        mock_client = mock_client_class.return_value
        # Raise exception during connect
        mock_client.connect = AsyncMock(side_effect=Exception("Test exception"))
        mock_client.disconnect = AsyncMock()

        result2 = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "192.168.1.200",
            },
        )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}
