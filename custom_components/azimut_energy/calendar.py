"""Calendar platform for the Azimut Energy integration.

Exposes the cloud charge plan as a calendar: one event per run of consecutive
quarters with the same smart charging intent. Home Assistant can then show the
planned future, trigger automations on an event's start or end (with an
offset), and read upcoming windows with calendar.get_events.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.translation import async_get_translations
from homeassistant.util import dt as dt_util

from .const import (
    CONF_SERIAL,
    DEFAULT_SMART_CHARGING_INTENT,
    DOMAIN,
    SMART_CHARGING_INTENTS,
)
from .types import PlanningPayload, PlanningSetpoint

if TYPE_CHECKING:
    from . import AzimutMQTTCoordinator

_LOGGER = logging.getLogger(__name__)

# Two quarters belong to the same event when the second starts at most this
# long after the first ends (the plan's quarters are contiguous to the
# millisecond; the margin only absorbs rounding).
_CONTIGUITY_MS = 1000

# The event names are the smart_charging_intent sensor's state labels
_INTENT_LABEL_KEY = (
    "component." + DOMAIN + ".entity.sensor.smart_charging_intent.state.{}"
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the charge plan calendar from a config entry."""
    coordinator: AzimutMQTTCoordinator = hass.data[DOMAIN][entry.entry_id]
    serial = entry.data.get(CONF_SERIAL, "")

    translations = await async_get_translations(
        hass, hass.config.language, "entity", {DOMAIN}
    )
    labels = {
        intent: translations.get(_INTENT_LABEL_KEY.format(intent), intent)
        for intent in SMART_CHARGING_INTENTS
    }

    calendar = AzimutPlanningCalendar(serial=serial, labels=labels)
    async_add_entities([calendar])

    coordinator.set_planning_callback(calendar.update_planning)


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def normalize_intent(intent: str) -> str:
    """Return the intent as the device names it, unknown ones as the default."""
    key = intent.strip().lower()
    return key if key in SMART_CHARGING_INTENTS else DEFAULT_SMART_CHARGING_INTENT


def build_events(
    setpoints: list[PlanningSetpoint], labels: dict[str, str]
) -> list[CalendarEvent]:
    """Merge the plan's quarters into one event per run of the same intent.

    Quarters without an intent (plans computed before the cloud sent one) or
    with unusable times are skipped. The result is sorted by start time.
    """
    quarters: list[tuple[int, int, str]] = []
    for setpoint in setpoints:
        intent = setpoint.get("intent")
        start = setpoint.get("start_time")
        end = setpoint.get("end_time")
        if not isinstance(intent, str) or not intent.strip():
            continue
        if not _is_number(start) or not _is_number(end) or end <= start:
            continue
        quarters.append((int(start), int(end), normalize_intent(intent)))
    quarters.sort()

    runs: list[list[Any]] = []
    for start, end, intent in quarters:
        last = runs[-1] if runs else None
        if last and last[2] == intent and start - last[1] <= _CONTIGUITY_MS:
            last[1] = max(last[1], end)
        else:
            runs.append([start, end, intent])

    return [
        CalendarEvent(
            start=dt_util.utc_from_timestamp(start / 1000),
            end=dt_util.utc_from_timestamp(end / 1000),
            summary=labels.get(intent, intent),
            description=intent,
            uid=f"{intent}_{start}",
        )
        for start, end, intent in runs
    ]


class AzimutPlanningCalendar(CalendarEntity):
    """The cloud charge plan, one event per smart charging intent window."""

    _attr_has_entity_name = True
    _attr_translation_key = "smart_charging_plan"
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, serial: str, labels: dict[str, str]) -> None:
        """Initialize the calendar."""
        self._labels = labels
        self._events: list[CalendarEvent] = []
        self._device_id = f"azen_{serial}"
        self._attr_unique_id = f"azen_{serial}_smart_charging_plan"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=f"Azen {serial}",
            manufacturer="Azimut",
            model="Azen Energy System",
        )

    @property
    def event(self) -> CalendarEvent | None:
        """Return the current event, or the next one."""
        now = dt_util.now()
        for event in self._events:
            if event.end_datetime_local > now:
                return event
        return None

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return the events overlapping a time range."""
        return [
            event
            for event in self._events
            if event.end_datetime_local > start_date
            and event.start_datetime_local < end_date
        ]

    @callback
    def update_planning(self, payload: PlanningPayload | None) -> None:
        """Replace the events with a new plan; None clears them."""
        setpoints = (payload or {}).get("setpoints") or []
        self._events = build_events(setpoints, self._labels)
        _LOGGER.debug(
            "Charge plan updated: %d quarters, %d events",
            len(setpoints),
            len(self._events),
        )
        if self.hass is not None:
            self.async_write_ha_state()
