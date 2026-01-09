"""Fixtures for Azimut Energy integration tests."""

from __future__ import annotations

import sys
from collections.abc import Generator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.const import CONF_HOST

# Add the workspace root to Python path for imports
workspace_root = Path(__file__).parent.parent
if str(workspace_root) not in sys.path:
    sys.path.insert(0, str(workspace_root))

# Import after module setup
from custom_components.azimut_energy.const import (  # noqa: E402, I001
    CONF_SERIAL,
    DOMAIN,
)

# Import pytest_homeassistant_custom_component fixtures
pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for all tests."""
    yield


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock, None, None]:
    """Override async_setup_entry."""
    with patch(
        "custom_components.azimut_energy.async_setup_entry",
        return_value=True,
    ) as mock_setup:
        yield mock_setup


@pytest.fixture
def mock_mqtt_client() -> Generator[MagicMock, None, None]:
    """Mock the AzimutMQTTClient."""
    with patch(
        "custom_components.azimut_energy.mqtt_client.AzimutMQTTClient",
        autospec=True,
    ) as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.connect = AsyncMock(return_value=True)
        mock_client.disconnect = AsyncMock()
        mock_client.listen = AsyncMock()
        mock_client.listen_with_reconnect = AsyncMock()
        mock_client.is_connected = True
        mock_client.set_discovery_callback = MagicMock()
        mock_client.set_state_callback = MagicMock()
        mock_client.set_connection_callback = MagicMock()
        # Statistics properties
        mock_client.connection_count = 1
        mock_client.reconnect_count = 0
        mock_client.total_messages_received = 0
        mock_client.last_message_time = 0.0
        mock_client.last_connect_time = 1234567890.0
        mock_client.last_disconnect_time = None
        mock_client.host = "192.168.1.100"
        mock_client.port = 8883
        mock_client.use_tls = True
        yield mock_client


@pytest.fixture
def mock_mqtt_client_cannot_connect() -> Generator[MagicMock, None, None]:
    """Mock the AzimutMQTTClient that cannot connect."""
    with patch(
        "custom_components.azimut_energy.mqtt_client.AzimutMQTTClient",
        autospec=True,
    ) as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.connect = AsyncMock(return_value=False)
        mock_client.disconnect = AsyncMock()
        mock_client.is_connected = False
        yield mock_client


@pytest.fixture
def mock_config_entry() -> MagicMock:
    """Create a mock config entry."""
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.domain = DOMAIN
    entry.data = {
        CONF_HOST: "192.168.1.100",
        CONF_SERIAL: "504589",
    }
    entry.options = {}
    entry.unique_id = "azimut_energy_504589"
    entry.title = "Azimut Battery 504589"
    return entry
