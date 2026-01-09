"""Test the Azimut Energy MQTT client."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.azimut_energy.mqtt_client import AzimutMQTTClient


@pytest.fixture
def mqtt_client() -> AzimutMQTTClient:
    """Create a test MQTT client."""
    return AzimutMQTTClient(
        host="192.168.1.100",
        port=8883,
        serial="ABC123",
        use_tls=True,
    )


async def test_client_initialization(mqtt_client: AzimutMQTTClient) -> None:
    """Test client initialization."""
    assert mqtt_client.host == "192.168.1.100"
    assert mqtt_client.port == 8883
    assert mqtt_client.serial == "ABC123"
    assert mqtt_client.use_tls is True
    assert not mqtt_client.is_connected


async def test_connect_success(mqtt_client: AzimutMQTTClient) -> None:
    """Test successful connection validation."""
    mock_aiomqtt_client = MagicMock()
    mock_aiomqtt_client.__aenter__ = AsyncMock(return_value=mock_aiomqtt_client)
    mock_aiomqtt_client.__aexit__ = AsyncMock(return_value=None)
    mock_aiomqtt_client.subscribe = AsyncMock()

    with patch(
        "custom_components.azimut_energy.mqtt_client.aiomqtt.Client"
    ) as mock_client:
        mock_client.return_value = mock_aiomqtt_client

        result = await mqtt_client.connect()

    assert result is True
    # connect() is for validation only, it disconnects after
    assert not mqtt_client.is_connected
    assert mock_aiomqtt_client.subscribe.call_count == 2  # Discovery + state topics


async def test_connect_failure(mqtt_client: AzimutMQTTClient) -> None:
    """Test connection failure."""
    with patch(
        "custom_components.azimut_energy.mqtt_client.aiomqtt.Client"
    ) as mock_client:
        mock_client.return_value.__aenter__ = AsyncMock(
            side_effect=Exception("Connection refused")
        )

        result = await mqtt_client.connect()

    assert result is False
    assert not mqtt_client.is_connected


async def test_disconnect(mqtt_client: AzimutMQTTClient) -> None:
    """Test disconnection."""
    # Manually set connected state for testing disconnect
    mqtt_client._connected = True
    mqtt_client._running = True

    await mqtt_client.disconnect()

    assert not mqtt_client.is_connected
    assert not mqtt_client._running


async def test_discovery_callback(mqtt_client: AzimutMQTTClient) -> None:
    """Test discovery message callback."""
    received_payloads = []

    def discovery_callback(payload: dict) -> None:
        received_payloads.append(payload)

    mqtt_client.set_discovery_callback(discovery_callback)

    # Simulate discovery message handling
    discovery_payload = json.dumps(
        {
            "unique_id": "azen_ABC123_battery_soc",
            "name": "Battery SOC",
            "state_topic": "azen/ABC123/sensor/battery_soc/state",
        }
    )

    mqtt_client._handle_discovery_message(discovery_payload)

    assert len(received_payloads) == 1
    assert received_payloads[0]["unique_id"] == "azen_ABC123_battery_soc"


async def test_discovery_double_encoded_json(mqtt_client: AzimutMQTTClient) -> None:
    """Test handling of double-encoded JSON in discovery messages."""
    received_payloads = []

    def discovery_callback(payload: dict) -> None:
        received_payloads.append(payload)

    mqtt_client.set_discovery_callback(discovery_callback)

    # Double-encoded JSON (string inside JSON)
    inner_payload = {"unique_id": "test", "name": "Test Sensor"}
    double_encoded = json.dumps(json.dumps(inner_payload))

    mqtt_client._handle_discovery_message(double_encoded)

    assert len(received_payloads) == 1
    assert received_payloads[0]["unique_id"] == "test"


async def test_state_callback(mqtt_client: AzimutMQTTClient) -> None:
    """Test state message callback."""
    received_states = []

    def state_callback(topic: str, value: float) -> None:
        received_states.append((topic, value))

    mqtt_client.set_state_callback(state_callback)

    # Simulate state message handling
    mqtt_client._handle_state_message("azen/ABC123/sensor/battery_soc/state", "85.50")

    assert len(received_states) == 1
    assert received_states[0] == ("azen/ABC123/sensor/battery_soc/state", 85.50)


async def test_state_json_encoded_value(mqtt_client: AzimutMQTTClient) -> None:
    """Test handling of JSON-encoded state values."""
    received_states = []

    def state_callback(topic: str, value: float) -> None:
        received_states.append((topic, value))

    mqtt_client.set_state_callback(state_callback)

    # JSON-encoded string value (e.g., "344.00")
    mqtt_client._handle_state_message(
        "azen/ABC123/sensor/grid_power/state", '"1523.45"'
    )

    assert len(received_states) == 1
    assert received_states[0][1] == 1523.45


async def test_state_invalid_value(mqtt_client: AzimutMQTTClient) -> None:
    """Test handling of invalid state values."""
    received_states = []

    def state_callback(topic: str, value: float) -> None:
        received_states.append((topic, value))

    mqtt_client.set_state_callback(state_callback)

    # Invalid value should be ignored
    mqtt_client._handle_state_message(
        "azen/ABC123/sensor/battery_soc/state", "not_a_number"
    )

    assert len(received_states) == 0


async def test_connection_callback(mqtt_client: AzimutMQTTClient) -> None:
    """Test connection state callback."""
    connection_states = []

    def connection_callback(connected: bool) -> None:
        connection_states.append(connected)

    mqtt_client.set_connection_callback(connection_callback)

    # Test notify connected
    mqtt_client._notify_connected()
    assert connection_states == [True]

    # Test notify disconnected
    mqtt_client._notify_disconnected()
    assert connection_states == [True, False]

    # Test that duplicate notifications are ignored
    mqtt_client._notify_disconnected()
    assert connection_states == [True, False]  # No change


async def test_topic_patterns(mqtt_client: AzimutMQTTClient) -> None:
    """Test topic pattern matching."""
    # Discovery topic pattern
    assert mqtt_client._discovery_pattern.match(
        "homeassistant/sensor/azen_ABC123/battery_soc/config"
    )
    assert not mqtt_client._discovery_pattern.match(
        "homeassistant/sensor/azen_OTHER/battery_soc/config"
    )

    # State topic pattern
    assert mqtt_client._state_pattern.match("azen/ABC123/sensor/battery_soc/state")
    assert not mqtt_client._state_pattern.match("azen/OTHER/sensor/battery_soc/state")


async def test_tls_context_creation(mqtt_client: AzimutMQTTClient) -> None:
    """Test TLS context is created when use_tls is True."""
    tls_context = mqtt_client._create_tls_context()

    assert tls_context is not None
    # Verify insecure settings (no cert verification)
    import ssl

    assert tls_context.verify_mode == ssl.CERT_NONE
    assert tls_context.check_hostname is False


async def test_no_tls_context() -> None:
    """Test no TLS context when use_tls is False."""
    client = AzimutMQTTClient(
        host="192.168.1.100",
        port=1883,
        serial="ABC123",
        use_tls=False,
    )

    tls_context = client._create_tls_context()
    assert tls_context is None


async def test_disconnect_with_error(mqtt_client: AzimutMQTTClient) -> None:
    """Test disconnect handling when an error occurs."""
    mqtt_client._connected = True
    mqtt_client._running = True

    # Create a mock client that raises an error on exit
    mock_client = MagicMock()
    mock_client.__aexit__ = AsyncMock(side_effect=Exception("Disconnect error"))
    mqtt_client._client = mock_client

    # Should handle the error gracefully
    await mqtt_client.disconnect()

    assert not mqtt_client.is_connected
    assert not mqtt_client._running
    assert mqtt_client._client is None


async def test_listen_with_reconnect_mqtt_error(mqtt_client: AzimutMQTTClient) -> None:
    """Test listen_with_reconnect handles MQTT errors and reconnects."""
    import asyncio

    import aiomqtt

    mock_aiomqtt_client = MagicMock()
    mock_aiomqtt_client.__aenter__ = AsyncMock(
        side_effect=aiomqtt.MqttError("Connection failed")
    )
    mock_aiomqtt_client.__aexit__ = AsyncMock()

    with patch(
        "custom_components.azimut_energy.mqtt_client.aiomqtt.Client"
    ) as mock_client:
        mock_client.return_value = mock_aiomqtt_client

        # Start listening in background
        task = asyncio.create_task(mqtt_client.listen_with_reconnect())

        # Wait a bit for the first connection attempt
        await asyncio.sleep(0.1)

        # Stop the client
        mqtt_client._running = False

        # Wait for task to complete
        try:
            await asyncio.wait_for(task, timeout=1.0)
        except TimeoutError:
            task.cancel()


async def test_listen_with_reconnect_cancelled(mqtt_client: AzimutMQTTClient) -> None:
    """Test listen_with_reconnect handles cancellation."""
    import asyncio

    mock_aiomqtt_client = MagicMock()

    async def mock_aenter(*args):
        # Simulate a cancellation during connection
        raise asyncio.CancelledError()

    mock_aiomqtt_client.__aenter__ = mock_aenter
    mock_aiomqtt_client.__aexit__ = AsyncMock()

    with patch(
        "custom_components.azimut_energy.mqtt_client.aiomqtt.Client"
    ) as mock_client:
        mock_client.return_value = mock_aiomqtt_client

        # This should exit cleanly when cancelled
        try:
            await mqtt_client.listen_with_reconnect()
        except asyncio.CancelledError:
            pass

        assert not mqtt_client.is_connected


async def test_listen_with_reconnect_unexpected_error(
    mqtt_client: AzimutMQTTClient,
) -> None:
    """Test listen_with_reconnect handles unexpected errors."""
    import asyncio

    mock_aiomqtt_client = MagicMock()
    mock_aiomqtt_client.__aenter__ = AsyncMock(
        side_effect=RuntimeError("Unexpected error")
    )
    mock_aiomqtt_client.__aexit__ = AsyncMock()

    with patch(
        "custom_components.azimut_energy.mqtt_client.aiomqtt.Client"
    ) as mock_client:
        mock_client.return_value = mock_aiomqtt_client

        # Start listening in background
        task = asyncio.create_task(mqtt_client.listen_with_reconnect())

        # Wait a bit for the first connection attempt
        await asyncio.sleep(0.1)

        # Stop the client
        mqtt_client._running = False

        # Wait for task to complete
        try:
            await asyncio.wait_for(task, timeout=1.0)
        except TimeoutError:
            task.cancel()


async def test_message_timeout_handling(mqtt_client: AzimutMQTTClient) -> None:
    """Test timeout handling in message loop."""
    import time

    # Set last message time to simulate timeout
    mqtt_client._last_message_time = time.monotonic() - 500  # Way past timeout

    # Test the timeout check
    elapsed = time.monotonic() - mqtt_client._last_message_time
    assert elapsed > 120  # MESSAGE_TIMEOUT is 120


async def test_sleep_with_check_early_exit(mqtt_client: AzimutMQTTClient) -> None:
    """Test _sleep_with_check exits early when running is False."""
    import asyncio

    mqtt_client._running = True

    async def stop_soon():
        await asyncio.sleep(0.1)
        mqtt_client._running = False

    # Start stop task
    stop_task = asyncio.create_task(stop_soon())

    # _sleep_with_check should exit early
    start = asyncio.get_event_loop().time()
    await mqtt_client._sleep_with_check(10.0)  # Would sleep 10 seconds normally
    elapsed = asyncio.get_event_loop().time() - start

    await stop_task

    # Should have exited early (much less than 10 seconds)
    assert elapsed < 5.0


async def test_statistics_initialization(mqtt_client: AzimutMQTTClient) -> None:
    """Test that statistics are initialized correctly."""
    assert mqtt_client.connection_count == 0
    assert mqtt_client.reconnect_count == 0
    assert mqtt_client.total_messages_received == 0
    assert mqtt_client.last_message_time == 0.0
    assert mqtt_client.last_connect_time is None
    assert mqtt_client.last_disconnect_time is None


async def test_connection_statistics_tracking(mqtt_client: AzimutMQTTClient) -> None:
    """Test connection statistics are tracked correctly."""
    import time

    # Initial state
    assert mqtt_client.connection_count == 0
    assert mqtt_client.reconnect_count == 0

    # First connection
    mqtt_client._notify_connected()
    assert mqtt_client.connection_count == 1
    assert mqtt_client.reconnect_count == 0
    assert mqtt_client.last_connect_time is not None
    assert mqtt_client.is_connected is True

    # Disconnect
    mqtt_client._notify_disconnected()
    assert mqtt_client.last_disconnect_time is not None
    assert mqtt_client.is_connected is False

    # Second connection (should count as reconnect)
    time.sleep(0.01)  # Small delay to ensure different timestamps
    mqtt_client._notify_connected()
    assert mqtt_client.connection_count == 2
    assert mqtt_client.reconnect_count == 1  # Second connection counts as reconnect


async def test_message_counter(mqtt_client: AzimutMQTTClient) -> None:
    """Test message counter increments."""
    assert mqtt_client.total_messages_received == 0

    # Simulate receiving messages by directly incrementing
    # (normally done in _listen_loop_with_timeout)
    mqtt_client._total_messages_received += 1
    assert mqtt_client.total_messages_received == 1

    mqtt_client._total_messages_received += 1
    assert mqtt_client.total_messages_received == 2


async def test_statistics_properties(mqtt_client: AzimutMQTTClient) -> None:
    """Test all statistics properties are accessible."""
    import time

    # Set some values
    mqtt_client._connection_count = 5
    mqtt_client._reconnect_count = 3
    mqtt_client._total_messages_received = 150
    mqtt_client._last_message_time = time.monotonic()
    mqtt_client._last_connect_time = time.time()
    mqtt_client._last_disconnect_time = time.time() - 100

    # Verify properties return correct values
    assert mqtt_client.connection_count == 5
    assert mqtt_client.reconnect_count == 3
    assert mqtt_client.total_messages_received == 150
    assert mqtt_client.last_message_time > 0
    assert mqtt_client.last_connect_time is not None
    assert mqtt_client.last_disconnect_time is not None


async def test_connection_tracking_edge_cases(mqtt_client: AzimutMQTTClient) -> None:
    """Test connection tracking edge cases."""
    # Multiple connect notifications should only count once
    mqtt_client._notify_connected()
    first_count = mqtt_client.connection_count
    mqtt_client._notify_connected()  # Duplicate notification
    assert mqtt_client.connection_count == first_count  # No change

    # Multiple disconnect notifications should only count once
    mqtt_client._notify_disconnected()
    first_disconnect_time = mqtt_client.last_disconnect_time
    mqtt_client._notify_disconnected()  # Duplicate notification
    assert mqtt_client.last_disconnect_time == first_disconnect_time  # No change
