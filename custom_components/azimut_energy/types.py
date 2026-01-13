"""Type definitions for the Azimut Energy integration."""

from __future__ import annotations

from typing import TypedDict


class DeviceInfoPayload(TypedDict, total=False):
    """Device info from MQTT discovery payload."""

    identifiers: list[str]
    name: str
    manufacturer: str
    model: str
    sw_version: str | None


class DiscoveryPayload(TypedDict, total=False):
    """MQTT discovery payload structure."""

    unique_id: str
    state_topic: str
    name: str
    unit_of_measurement: str | None
    icon: str | None
    device_class: str | None
    state_class: str | None
    entity_category: str | None
    expire_after: int
    device: DeviceInfoPayload


class MQTTStatistics(TypedDict):
    """MQTT connection statistics."""

    connection_count: int
    reconnect_count: int
    total_messages_received: int
    last_message_time: float
    last_connect_time: float | None
    last_disconnect_time: float | None


class SensorInfo(TypedDict):
    """Sensor information for diagnostics."""

    entity_id: str
    unique_id: str | None
    name: str | None
    state: str
    available: bool


class ConfigEntryInfo(TypedDict):
    """Config entry information for diagnostics."""

    entry_id: str
    version: int
    domain: str
    title: str
    source: str


class ConnectionInfo(TypedDict):
    """Connection information for diagnostics."""

    host: str | None
    port: int
    serial: str | None
    connected: bool
    tls_enabled: bool


class MQTTTopicsInfo(TypedDict):
    """MQTT topics information for diagnostics."""

    discovery: str
    state: str


class SensorsInfo(TypedDict):
    """Sensors summary for diagnostics."""

    count: int
    entities: list[SensorInfo]


class DiagnosticsData(TypedDict):
    """Complete diagnostics data structure."""

    config_entry: ConfigEntryInfo
    connection: ConnectionInfo
    mqtt_topics: MQTTTopicsInfo
    mqtt_statistics: MQTTStatistics
    sensors: SensorsInfo
