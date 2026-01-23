"""MQTT client for Azimut Energy integration."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import ssl
from collections.abc import Callable

import aiomqtt

from .const import (
    MQTT_KEEPALIVE,
    get_binary_sensor_discovery_topic,
    get_binary_sensor_state_topic,
    get_discovery_topic,
    get_republish_command_topic,
    get_state_topic,
)
from .types import BinarySensorDiscoveryPayload, DiscoveryPayload

_LOGGER = logging.getLogger(__name__)

# Reconnection settings
INITIAL_RECONNECT_DELAY = 1  # Start with 1 second
MAX_RECONNECT_DELAY = 30  # Max 30 seconds between retries
MESSAGE_TIMEOUT = 120  # Consider connection dead if no message for 2 minutes


class AzimutMQTTClient:
    """MQTT client for Azimut Energy System with automatic reconnection."""

    def __init__(
        self,
        host: str,
        port: int = 1883,
        serial: str = "",
        use_tls: bool = False,
    ) -> None:
        """Initialize the MQTT client."""
        self.host = host
        self.port = port
        self.serial = serial
        self.use_tls = use_tls

        self._client: aiomqtt.Client | None = None
        self._running = False
        self._connected = False
        self._reconnect_delay = INITIAL_RECONNECT_DELAY
        self._last_message_time: float = 0

        # Connection statistics
        self._connection_count = 0
        self._reconnect_count = 0
        self._last_connect_time: float | None = None
        self._last_disconnect_time: float | None = None
        self._total_messages_received = 0

        # Callbacks for discovery and state messages
        self._discovery_callback: Callable[[DiscoveryPayload], None] | None = None
        self._state_callback: Callable[[str, float], None] | None = None
        self._connection_callback: Callable[[bool], None] | None = None
        self._binary_sensor_discovery_callback: (
            Callable[[BinarySensorDiscoveryPayload], None] | None
        ) = None
        self._binary_sensor_state_callback: Callable[[str, bool], None] | None = None

        # TLS context - created lazily to avoid blocking in __init__
        self._tls_context: ssl.SSLContext | None = None

        # Topic patterns
        self._discovery_topic = get_discovery_topic(serial)
        self._state_topic = get_state_topic(serial)
        self._binary_sensor_discovery_topic = get_binary_sensor_discovery_topic(serial)
        self._binary_sensor_state_topic = get_binary_sensor_state_topic(serial)
        self._republish_command_topic = get_republish_command_topic(serial)

        # Regex patterns for parsing topics
        # Sensor discovery: homeassistant/sensor/azen_{serial}/{sensor_id}/config
        self._discovery_pattern = re.compile(
            rf"homeassistant/sensor/azen_{re.escape(serial)}/([^/]+)/config"
        )
        # Sensor state: azen/{serial}/sensor/{sensor_id}/state
        self._state_pattern = re.compile(
            rf"azen/{re.escape(serial)}/sensor/([^/]+)/state"
        )
        # Binary sensor discovery: homeassistant/binary_sensor/azen_{serial}/{sensor_id}/config
        self._binary_sensor_discovery_pattern = re.compile(
            rf"homeassistant/binary_sensor/azen_{re.escape(serial)}/([^/]+)/config"
        )
        # Binary sensor state: azen/{serial}/binary_sensor/{sensor_id}/state
        self._binary_sensor_state_pattern = re.compile(
            rf"azen/{re.escape(serial)}/binary_sensor/([^/]+)/state"
        )

    def set_discovery_callback(
        self, callback: Callable[[DiscoveryPayload], None]
    ) -> None:
        """Set callback for discovery messages."""
        self._discovery_callback = callback

    def set_state_callback(self, callback: Callable[[str, float], None]) -> None:
        """Set callback for state messages.

        Callback receives (state_topic, value).
        """
        self._state_callback = callback

    def set_connection_callback(self, callback: Callable[[bool], None]) -> None:
        """Set callback for connection state changes.

        Callback receives True when connected, False when disconnected.
        """
        self._connection_callback = callback

    def set_binary_sensor_discovery_callback(
        self, callback: Callable[[BinarySensorDiscoveryPayload], None]
    ) -> None:
        """Set callback for binary sensor discovery messages."""
        self._binary_sensor_discovery_callback = callback

    def set_binary_sensor_state_callback(
        self, callback: Callable[[str, bool], None]
    ) -> None:
        """Set callback for binary sensor state messages.

        Callback receives (state_topic, is_on).
        """
        self._binary_sensor_state_callback = callback

    def _create_tls_context(self) -> ssl.SSLContext | None:
        """Create TLS context if TLS is enabled (synchronous, for executor)."""
        if not self.use_tls:
            return None
        tls_context = ssl.create_default_context()
        tls_context.check_hostname = False
        tls_context.verify_mode = ssl.CERT_NONE
        return tls_context

    async def _get_tls_context(self) -> ssl.SSLContext | None:
        """Get or create TLS context asynchronously (non-blocking)."""
        if self._tls_context is None:
            # Run blocking SSL context creation in executor
            loop = asyncio.get_running_loop()
            self._tls_context = await loop.run_in_executor(
                None, self._create_tls_context
            )
        return self._tls_context

    def _notify_connected(self) -> None:
        """Notify that connection is established."""
        if not self._connected:
            import time

            self._connected = True
            self._reconnect_delay = INITIAL_RECONNECT_DELAY  # Reset on success
            self._last_connect_time = time.time()
            self._connection_count += 1
            if self._connection_count > 1:
                self._reconnect_count += 1
            if self._connection_callback:
                self._connection_callback(True)

    def _notify_disconnected(self) -> None:
        """Notify that connection is lost."""
        if self._connected:
            import time

            self._connected = False
            self._last_disconnect_time = time.time()
            if self._connection_callback:
                self._connection_callback(False)

    async def _request_republish(self) -> None:
        """Request republish of all sensor values.

        Publishes to the republish command topic to trigger the device to
        republish all sensor values. This is called on reconnect to ensure
        sensors get their initial values.
        """
        if not self._client:
            return

        try:
            await self._client.publish(self._republish_command_topic, payload="1")
            _LOGGER.debug(
                "Requested republish of sensor values on topic %s",
                self._republish_command_topic,
            )
        except Exception as err:
            _LOGGER.warning("Failed to request republish: %s", err)

    async def connect(self) -> bool:
        """Connect to MQTT broker (for initial validation only)."""
        try:
            # Get TLS context asynchronously (non-blocking)
            tls_context = await self._get_tls_context()

            client = aiomqtt.Client(
                hostname=self.host,
                port=self.port,
                tls_context=tls_context,
                identifier=f"ha_azimut_{self.serial}",
                keepalive=MQTT_KEEPALIVE,
            )

            await client.__aenter__()

            # Subscribe to test connection
            await client.subscribe(self._discovery_topic)
            await client.subscribe(self._state_topic)
            await client.subscribe(self._binary_sensor_discovery_topic)
            await client.subscribe(self._binary_sensor_state_topic)

            _LOGGER.info(
                "Connected to MQTT broker at %s:%s for device %s",
                self.host,
                self.port,
                self.serial,
            )

            # Disconnect - we'll reconnect in listen_with_reconnect
            await client.__aexit__(None, None, None)
            return True

        except Exception as err:
            _LOGGER.error("Failed to connect to MQTT broker: %s", err)
            return False

    async def disconnect(self) -> None:
        """Disconnect from MQTT broker."""
        self._running = False
        self._notify_disconnected()

        if self._client:
            try:
                await self._client.__aexit__(None, None, None)
            except Exception as err:
                _LOGGER.debug("Error during MQTT disconnect: %s", err)
            finally:
                self._client = None

    async def listen_with_reconnect(self) -> None:
        """Listen for MQTT messages with automatic reconnection."""
        self._running = True
        import time

        # Get TLS context once before loop (non-blocking)
        tls_context = await self._get_tls_context()

        while self._running:
            try:
                # Create new client for each connection attempt
                self._client = aiomqtt.Client(
                    hostname=self.host,
                    port=self.port,
                    tls_context=tls_context,
                    identifier=f"ha_azimut_{self.serial}",
                    keepalive=MQTT_KEEPALIVE,
                )

                async with self._client:
                    # Subscribe to topics
                    await self._client.subscribe(self._discovery_topic)
                    await self._client.subscribe(self._state_topic)
                    await self._client.subscribe(self._binary_sensor_discovery_topic)
                    await self._client.subscribe(self._binary_sensor_state_topic)

                    _LOGGER.info(
                        "MQTT connected to %s:%s for device %s",
                        self.host,
                        self.port,
                        self.serial,
                    )
                    _LOGGER.debug("Subscribed to: %s", self._discovery_topic)
                    _LOGGER.debug("Subscribed to: %s", self._state_topic)
                    _LOGGER.debug(
                        "Subscribed to: %s", self._binary_sensor_discovery_topic
                    )
                    _LOGGER.debug("Subscribed to: %s", self._binary_sensor_state_topic)

                    self._notify_connected()
                    self._last_message_time = time.monotonic()

                    # Request republish of all sensor values on reconnect
                    await self._request_republish()

                    # Listen for messages with timeout
                    await self._listen_loop_with_timeout()

            except aiomqtt.MqttError as err:
                self._notify_disconnected()
                _LOGGER.warning(
                    "MQTT connection error: %s. Reconnecting in %s seconds...",
                    err,
                    self._reconnect_delay,
                )

            except asyncio.CancelledError:
                _LOGGER.debug("MQTT listen task cancelled")
                self._notify_disconnected()
                return

            except Exception as err:
                self._notify_disconnected()
                _LOGGER.error(
                    "Unexpected MQTT error: %s. Reconnecting in %s seconds...",
                    err,
                    self._reconnect_delay,
                )

            finally:
                self._client = None

            # Wait before reconnecting (with early exit check)
            if self._running:
                await self._sleep_with_check(self._reconnect_delay)
                # Exponential backoff
                self._reconnect_delay = min(
                    self._reconnect_delay * 2, MAX_RECONNECT_DELAY
                )

    async def _sleep_with_check(self, seconds: float) -> None:
        """Sleep for specified seconds, but check _running periodically."""
        end_time = asyncio.get_event_loop().time() + seconds
        while asyncio.get_event_loop().time() < end_time and self._running:
            await asyncio.sleep(min(1.0, end_time - asyncio.get_event_loop().time()))

    async def _listen_loop_with_timeout(self) -> None:
        """Listen for messages with a timeout to detect dead connections."""
        import time

        if not self._client:
            return

        async for message in self._client.messages:
            if not self._running:
                break

            self._last_message_time = time.monotonic()

            topic = str(message.topic)
            self._total_messages_received += 1

            try:
                payload = message.payload.decode()
            except UnicodeDecodeError:
                _LOGGER.debug("Failed to decode payload on topic %s", topic)
                continue

            try:
                # Check if this is a sensor discovery message
                discovery_match = self._discovery_pattern.match(topic)
                if discovery_match:
                    self._handle_discovery_message(payload)
                    continue

                # Check if this is a sensor state message
                state_match = self._state_pattern.match(topic)
                if state_match:
                    self._handle_state_message(topic, payload)
                    continue

                # Check if this is a binary sensor discovery message
                binary_discovery_match = self._binary_sensor_discovery_pattern.match(
                    topic
                )
                if binary_discovery_match:
                    self._handle_binary_sensor_discovery_message(payload)
                    continue

                # Check if this is a binary sensor state message
                binary_state_match = self._binary_sensor_state_pattern.match(topic)
                if binary_state_match:
                    self._handle_binary_sensor_state_message(topic, payload)
                    continue

                _LOGGER.debug("Unhandled topic: %s", topic)

            except Exception as err:
                _LOGGER.debug("Error processing MQTT message on %s: %s", topic, err)

    def _handle_discovery_message(self, payload: str) -> None:
        """Handle a discovery message (JSON payload)."""
        try:
            data: object = json.loads(payload)

            # Handle double-encoded JSON (string inside JSON)
            if isinstance(data, str):
                data = json.loads(data)

            _LOGGER.debug("Received discovery message: %s", data)

            if self._discovery_callback and isinstance(data, dict):
                # Cast to DiscoveryPayload - the structure is validated by the device
                self._discovery_callback(data)  # type: ignore[arg-type]

        except json.JSONDecodeError as err:
            _LOGGER.debug("Failed to decode discovery JSON: %s", err)

    def _handle_state_message(self, topic: str, payload: str) -> None:
        """Handle a state message (numeric string, possibly JSON-encoded)."""
        try:
            # Try to parse as JSON first (in case it's a quoted string like "344.00")
            try:
                parsed = json.loads(payload)
                if isinstance(parsed, (int, float)):
                    value = float(parsed)
                elif isinstance(parsed, str):
                    value = float(parsed)
                else:
                    raise ValueError(f"Unexpected type: {type(parsed)}")
            except json.JSONDecodeError:
                # Not JSON, try direct float conversion
                value = float(payload)

            _LOGGER.debug("Received state update on %s: %s", topic, value)

            if self._state_callback:
                self._state_callback(topic, value)

        except ValueError as err:
            _LOGGER.debug("Failed to parse state value '%s': %s", payload, err)

    def _handle_binary_sensor_discovery_message(self, payload: str) -> None:
        """Handle a binary sensor discovery message (JSON payload)."""
        try:
            data: object = json.loads(payload)

            # Handle double-encoded JSON (string inside JSON)
            if isinstance(data, str):
                data = json.loads(data)

            _LOGGER.debug("Received binary sensor discovery message: %s", data)

            if self._binary_sensor_discovery_callback and isinstance(data, dict):
                self._binary_sensor_discovery_callback(data)  # type: ignore[arg-type]

        except json.JSONDecodeError as err:
            _LOGGER.debug("Failed to decode binary sensor discovery JSON: %s", err)

    def _handle_binary_sensor_state_message(self, topic: str, payload: str) -> None:
        """Handle a binary sensor state message (ON/OFF string)."""
        try:
            # Handle JSON-encoded string (e.g., "\"ON\"")
            try:
                parsed = json.loads(payload)
                if isinstance(parsed, str):
                    payload = parsed
            except json.JSONDecodeError:
                pass  # Use original payload

            # Convert ON/OFF to boolean
            payload_upper = payload.upper().strip()
            if payload_upper == "ON":
                is_on = True
            elif payload_upper == "OFF":
                is_on = False
            else:
                raise ValueError(f"Unexpected binary sensor payload: {payload}")

            _LOGGER.debug("Received binary sensor state update on %s: %s", topic, is_on)

            if self._binary_sensor_state_callback:
                self._binary_sensor_state_callback(topic, is_on)

        except ValueError as err:
            _LOGGER.debug(
                "Failed to parse binary sensor state value '%s': %s", payload, err
            )

    @property
    def is_connected(self) -> bool:
        """Return connection status."""
        return self._connected

    @property
    def connection_count(self) -> int:
        """Return total number of connections made."""
        return self._connection_count

    @property
    def reconnect_count(self) -> int:
        """Return number of reconnections."""
        return self._reconnect_count

    @property
    def last_connect_time(self) -> float | None:
        """Return timestamp of last connection."""
        return self._last_connect_time

    @property
    def last_disconnect_time(self) -> float | None:
        """Return timestamp of last disconnection."""
        return self._last_disconnect_time

    @property
    def last_message_time(self) -> float:
        """Return timestamp of last message received."""
        return self._last_message_time

    @property
    def total_messages_received(self) -> int:
        """Return total number of MQTT messages received."""
        return self._total_messages_received

    # Keep old method for backwards compatibility
    async def listen(self) -> None:
        """Listen for MQTT messages (legacy method, use listen_with_reconnect)."""
        await self.listen_with_reconnect()
