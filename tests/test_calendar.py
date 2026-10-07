"""Test the Azimut Energy charge plan calendar."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.azimut_energy.calendar import (
    AzimutPlanningCalendar,
    build_events,
    normalize_intent,
)
from custom_components.azimut_energy.const import (
    CONF_SERIAL,
    DOMAIN,
    SMART_CHARGING_INTENTS,
)

BASE = datetime(2026, 10, 7, 0, 0, tzinfo=UTC)
QUARTER = timedelta(minutes=15)
LABELS = {"pre_charge": "Pre-charge", "anti_trip": "Anti-trip"}


def ms(offset: timedelta) -> int:
    """Epoch milliseconds of BASE + offset."""
    return int((BASE + offset).timestamp() * 1000)


def quarter(index: int, intent: str | None) -> dict:
    """One planning quarter, as the device mirrors it."""
    setpoint = {
        "start_time": ms(QUARTER * index),
        "end_time": ms(QUARTER * (index + 1)),
        "pilot_mode": "POWER_SETPOINT",
        "value": 0.0,
    }
    if intent is not None:
        setpoint["intent"] = intent
    return setpoint


def test_consecutive_quarters_with_the_same_intent_merge() -> None:
    """A run of the same intent is one event; a change of intent starts another."""
    setpoints = [
        quarter(0, "SELF_CONSUMPTION"),
        quarter(1, "PRE_CHARGE"),
        quarter(2, "PRE_CHARGE"),
        quarter(3, "PRE_CHARGE"),
        quarter(4, "ANTI_TRIP"),
    ]

    events = build_events(setpoints, LABELS)

    assert [(e.description, e.start, e.end) for e in events] == [
        ("self_consumption", BASE, BASE + QUARTER),
        ("pre_charge", BASE + QUARTER, BASE + 4 * QUARTER),
        ("anti_trip", BASE + 4 * QUARTER, BASE + 5 * QUARTER),
    ]
    assert events[1].summary == "Pre-charge"
    assert events[1].uid == f"pre_charge_{ms(QUARTER)}"


def test_gap_splits_a_run() -> None:
    """Two windows of the same intent separated by a gap stay two events."""
    events = build_events([quarter(0, "STANDBY"), quarter(2, "STANDBY")], LABELS)

    assert len(events) == 2


def test_quarters_are_sorted_before_merging() -> None:
    """The plan's order on the wire does not matter."""
    events = build_events(
        [quarter(2, "ABR"), quarter(0, "ABR"), quarter(1, "ABR")], LABELS
    )

    assert [(e.start, e.end) for e in events] == [(BASE, BASE + 3 * QUARTER)]


def test_quarters_without_intent_or_valid_times_are_skipped() -> None:
    """Plans computed before the cloud sent an intent produce no events."""
    broken = quarter(1, "PRE_CHARGE")
    broken["end_time"] = broken["start_time"]

    events = build_events([quarter(0, None), broken, quarter(2, "")], LABELS)

    assert events == []


def test_unknown_intent_is_shown_as_self_consumption() -> None:
    """An intent added to the cloud later degrades like on the device."""
    assert normalize_intent("PRE_CHARGE") == "pre_charge"
    assert normalize_intent("DSR") == "self_consumption"


def test_label_falls_back_to_the_intent() -> None:
    """Without a translation the event is named after the intent."""
    events = build_events([quarter(0, "BATTERY_CARE")], LABELS)

    assert events[0].summary == "battery_care"


async def test_event_is_the_current_window_then_the_next(
    hass: HomeAssistant,
) -> None:
    """The entity's event is the one in progress, or else the next one."""
    calendar = AzimutPlanningCalendar(serial="ABC123", labels=LABELS)
    calendar.update_planning(
        {"setpoints": [quarter(0, "PRE_CHARGE"), quarter(2, "ANTI_TRIP")]}
    )

    with patch(
        "custom_components.azimut_energy.calendar.dt_util.now",
        return_value=BASE + timedelta(minutes=5),
    ):
        assert calendar.event.description == "pre_charge"

    with patch(
        "custom_components.azimut_energy.calendar.dt_util.now",
        return_value=BASE + QUARTER + timedelta(minutes=5),
    ):
        assert calendar.event.description == "anti_trip"

    with patch(
        "custom_components.azimut_energy.calendar.dt_util.now",
        return_value=BASE + 4 * QUARTER,
    ):
        assert calendar.event is None


async def test_get_events_returns_the_overlapping_windows(
    hass: HomeAssistant,
) -> None:
    """calendar.get_events reads the planned future over any range."""
    calendar = AzimutPlanningCalendar(serial="ABC123", labels=LABELS)
    calendar.update_planning(
        {
            "setpoints": [
                quarter(0, "PRE_CHARGE"),
                quarter(4, "ANTI_TRIP"),
                quarter(8, "STANDBY"),
            ]
        }
    )

    events = await calendar.async_get_events(
        hass, BASE + timedelta(minutes=10), BASE + 5 * QUARTER
    )

    assert [e.description for e in events] == ["pre_charge", "anti_trip"]


async def test_new_planning_replaces_the_events_and_none_clears_them(
    hass: HomeAssistant,
) -> None:
    """Each planning replaces the whole calendar; a cleared one empties it."""
    calendar = AzimutPlanningCalendar(serial="ABC123", labels=LABELS)
    calendar.hass = hass

    with patch.object(calendar, "async_write_ha_state") as write:
        calendar.update_planning({"setpoints": [quarter(0, "PRE_CHARGE")]})
        calendar.update_planning({"setpoints": [quarter(1, "ANTI_TRIP")]})
        assert [e.description for e in calendar._events] == ["anti_trip"]

        calendar.update_planning(None)
        assert calendar._events == []

    assert write.call_count == 3


async def test_setup_wires_the_planning_callback(hass: HomeAssistant) -> None:
    """The platform creates one calendar fed by the coordinator."""
    from custom_components.azimut_energy.calendar import async_setup_entry

    entry = MagicMock()
    entry.data = {CONF_SERIAL: "ABC123"}
    entry.entry_id = "test_entry"
    coordinator = MagicMock()
    hass.data[DOMAIN] = {entry.entry_id: coordinator}

    add_entities = MagicMock()
    await async_setup_entry(hass, entry, add_entities)

    calendar = add_entities.call_args[0][0][0]
    assert isinstance(calendar, AzimutPlanningCalendar)
    assert calendar.unique_id == "azen_ABC123_smart_charging_plan"
    assert calendar.translation_key == "smart_charging_plan"
    # Event names come from the intent sensor's translated state labels
    assert calendar._labels["pre_charge"] == "Pre-charge"
    coordinator.set_planning_callback.assert_called_once_with(calendar.update_planning)


def test_calendar_name_is_translated() -> None:
    """The calendar has a name in every language."""
    base = Path(__file__).parent.parent / "custom_components" / "azimut_energy"
    files = [base / "strings.json", *sorted((base / "translations").glob("*.json"))]
    for path in files:
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["entity"]["calendar"]["smart_charging_plan"]["name"], path.name


@pytest.mark.parametrize("intent", SMART_CHARGING_INTENTS)
def test_every_intent_has_an_event_label(intent: str) -> None:
    """Event names come from the intent sensor's state labels."""
    base = Path(__file__).parent.parent / "custom_components" / "azimut_energy"
    for path in [base / "strings.json", *(base / "translations").glob("*.json")]:
        data = json.loads(path.read_text(encoding="utf-8"))
        states = data["entity"]["sensor"]["smart_charging_intent"]["state"]
        assert states[intent], path.name
