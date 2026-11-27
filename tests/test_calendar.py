"""Test on-demand chore calendar expansion without changing chore state."""

import asyncio
import threading
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util

from custom_components.sh_chore_tracker import RecurrenceEngine
from custom_components.sh_chore_tracker.calendar import ChoreCalendar, async_setup_entry
from custom_components.sh_chore_tracker.const import DOMAIN, SUBENTRY_TYPE_SUMMARY


@pytest.fixture(autouse=True)
async def use_utc(hass):
    await hass.config.async_set_time_zone("UTC")


def make_calendar(due="2026-11-02T00:00:00+00:00", **config):
    coordinator = MagicMock()
    coordinator.chore_data = {
        "dishes": {
            "config": {
                "chore_name": "Dishes",
                "chore_description": "Wash the dishes",
                "assigned_person": "person.test",
                "recurrence_type": "interval",
                "pattern_interval": 2,
                "interval_unit": "days",
                **config,
            },
            "state": {
                "next_due_date": due,
                "status": "pending",
                "completion_count": 0,
            },
        }
    }
    return ChoreCalendar(coordinator)


def utc(year, month, day, hour=0):
    return datetime(year, month, day, hour, tzinfo=timezone.utc)


async def test_setup_attaches_one_calendar_to_summary(hass):
    calendar = make_calendar()
    entry = MagicMock(entry_id="hub")
    summary = MagicMock(subentry_id="summary")
    entry.get_subentries_of_type.return_value = [summary]
    hass.data[DOMAIN] = {"hub": calendar.coordinator}
    add_entities = MagicMock()

    await async_setup_entry(hass, entry, add_entities)

    entry.get_subentries_of_type.assert_called_once_with(SUBENTRY_TYPE_SUMMARY)
    entities = add_entities.call_args.args[0]
    assert len(entities) == 1
    assert isinstance(entities[0], ChoreCalendar)
    assert add_entities.call_args.kwargs == {"config_subentry_id": "summary"}


@pytest.mark.parametrize(
    ("config", "first_due", "end_date", "expected"),
    [
        (
            {"recurrence_type": "interval", "pattern_interval": 3.0, "interval_unit": "days"},
            date(2026, 11, 1),
            date(2026, 11, 11),
            [date(2026, 11, day) for day in (1, 4, 7, 10)],
        ),
        (
            {"recurrence_type": "interval", "pattern_interval": 2, "interval_unit": "weeks"},
            date(2026, 11, 1),
            date(2026, 12, 1),
            [date(2026, 11, day) for day in (1, 15, 29)],
        ),
        (
            {"recurrence_type": "interval", "pattern_interval": 1, "interval_unit": "months"},
            date(2026, 1, 31),
            date(2026, 5, 1),
            [date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 28), date(2026, 4, 28)],
        ),
        (
            {"recurrence_type": "interval", "pattern_interval": 1, "interval_unit": "years"},
            date(2024, 2, 29),
            date(2027, 1, 1),
            [date(2024, 2, 29), date(2025, 2, 28), date(2026, 2, 28)],
        ),
        (
            {"recurrence_type": "weekly", "weekly_days": ["monday", "thursday"]},
            date(2026, 11, 2),
            date(2026, 11, 13),
            [date(2026, 11, day) for day in (2, 5, 9, 12)],
        ),
        (
            {"recurrence_type": "weekly", "weekly_days": "monday", "pattern_interval": 2},
            date(2026, 11, 2),
            date(2026, 12, 15),
            [date(2026, 11, 2), date(2026, 11, 23), date(2026, 12, 14)],
        ),
        (
            {"recurrence_type": "monthly", "monthly_day": 31.0},
            date(2026, 1, 31),
            date(2026, 5, 1),
            [date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31), date(2026, 4, 30)],
        ),
        (
            {
                "recurrence_type": "monthly",
                "monthly_mode": "ordinal_weekday",
                "monthly_ordinal": "fifth",
                "monthly_weekday": "monday",
            },
            date(2026, 3, 30),
            date(2026, 9, 1),
            [date(2026, 3, 30), date(2026, 6, 29), date(2026, 8, 31)],
        ),
        (
            {
                "recurrence_type": "monthly",
                "monthly_mode": "ordinal_weekday",
                "monthly_ordinal": "last",
                "monthly_weekday": "friday",
            },
            date(2026, 1, 30),
            date(2026, 4, 1),
            [date(2026, 1, 30), date(2026, 2, 27), date(2026, 3, 27)],
        ),
        (
            {"recurrence_type": "yearly", "yearly_month": 2.0, "yearly_day": 29.0},
            date(2024, 2, 29),
            date(2029, 1, 1),
            [
                date(2024, 2, 29),
                date(2025, 2, 28),
                date(2026, 2, 28),
                date(2027, 2, 28),
                date(2028, 2, 29),
            ],
        ),
    ],
)
def test_expansion_preserves_existing_recurrence(config, first_due, end_date, expected):
    assert list(RecurrenceEngine().iter_due_dates(config, first_due, end_date)) == expected


@pytest.mark.parametrize(
    ("interval", "unit", "expected"),
    [
        (2.5, "days", date(2026, 11, 3)),
        (61.0, "months", date(2031, 12, 1)),
        (11.0, "years", date(2037, 11, 1)),
    ],
)
def test_existing_ui_intervals_are_not_restricted_by_creation_service_limits(
    interval, unit, expected
):
    config = {"pattern_interval": interval, "interval_unit": unit}
    dates = RecurrenceEngine().iter_due_dates(config, date(2026, 11, 1), date(2040, 1, 1))
    assert next(dates) == date(2026, 11, 1)
    assert next(dates) == expected
    assert config["pattern_interval"] == interval


@pytest.mark.parametrize(
    "config",
    [
        {"recurrence_type": "interval", "interval_unit": "months", "pattern_interval": 2.5},
        {"recurrence_type": "interval", "interval_unit": "years", "pattern_interval": 2.5},
        {"recurrence_type": "monthly", "monthly_day": 1, "pattern_interval": 2.5},
        {"recurrence_type": "yearly", "yearly_month": 1, "yearly_day": 1, "pattern_interval": 2.5},
    ],
)
def test_fractional_month_and_year_intervals_fail_explicitly(config):
    with pytest.raises(HomeAssistantError, match="whole numbers"):
        list(RecurrenceEngine().iter_due_dates(config, date(2026, 1, 1), date(2027, 1, 1)))


async def test_invalid_chore_retains_actual_event_and_warns_once(hass, caplog):
    calendar = make_calendar(
        due=utc(2026, 11, 2),
        recurrence_type="yearly",
        pattern_interval=2.5,
        yearly_month=11,
        yearly_day=2,
    )
    calendar.coordinator.chore_data["valid"] = {
        "config": {
            "chore_name": "Laundry",
            "recurrence_type": "interval",
            "pattern_interval": 2,
            "interval_unit": "days",
        },
        "state": {"next_due_date": utc(2026, 11, 2)},
    }
    before = deepcopy(calendar.coordinator.chore_data)
    with patch(
        "custom_components.sh_chore_tracker.calendar.dt_util.now",
        return_value=utc(2026, 11, 1),
    ):
        await calendar.async_initialize(hass)
        assert calendar.event is not None
        events = await calendar.async_get_events(hass, utc(2026, 11, 1), utc(2026, 11, 8))
        await calendar.async_get_events(hass, utc(2026, 11, 1), utc(2026, 11, 8))
    assert [event.summary for event in events].count("Dishes") == 1
    assert "Dishes (projected)" not in [event.summary for event in events]
    assert [event.summary for event in events].count("Laundry (projected)") == 2
    assert caplog.text.count("Cannot project chore Dishes (dishes)") == 1
    assert "edit the chore schedule" in caplog.text
    assert calendar.coordinator.chore_data == before


async def test_fifth_weekday_search_stops_at_range_and_cycle(hass):
    calendar = make_calendar(
        due=utc(2029, 2, 1),
        recurrence_type="monthly",
        pattern_interval=48,
        monthly_mode="ordinal_weekday",
        monthly_ordinal="fifth",
        monthly_weekday="monday",
    )
    events = await calendar.async_get_events(hass, utc(2029, 2, 1), utc(2029, 3, 1))
    assert [(event.start, event.summary) for event in events] == [(date(2029, 2, 1), "Dishes")]
    assert await calendar.async_get_events(hass, utc(2030, 1, 1), utc(2400, 1, 1)) == []
    with patch(
        "custom_components.sh_chore_tracker.calendar.dt_util.now",
        return_value=utc(2030, 1, 1),
    ):
        await calendar.async_initialize(hass)
        assert calendar.event is None


def test_ordinal_fifth_weekday_respects_exclusive_end_and_date_limit():
    engine = RecurrenceEngine()
    config = {
        "recurrence_type": "monthly",
        "pattern_interval": 1,
        "monthly_mode": "ordinal_weekday",
        "monthly_ordinal": "fifth",
        "monthly_weekday": "monday",
    }
    assert list(engine.iter_due_dates(config, date(2026, 3, 30), date(2026, 6, 29))) == [
        date(2026, 3, 30)
    ]
    assert list(engine.iter_due_dates(config, date(2026, 3, 30), date(2026, 6, 30))) == [
        date(2026, 3, 30),
        date(2026, 6, 29),
    ]
    assert list(engine.iter_due_dates(config, date(9999, 11, 30), date.max)) == [date(9999, 11, 30)]


@pytest.mark.parametrize(
    ("config", "first_due"),
    [
        (
            {"recurrence_type": "interval", "interval_unit": "days", "pattern_interval": 2.5},
            date(2026, 1, 1),
        ),
        (
            {"recurrence_type": "interval", "interval_unit": "weeks", "pattern_interval": 1.5},
            date(2026, 1, 1),
        ),
        (
            {"recurrence_type": "interval", "interval_unit": "months", "pattern_interval": 1},
            date(2026, 1, 31),
        ),
        ({"recurrence_type": "weekly", "weekly_days": ["monday", "thursday"]}, date(2026, 1, 1)),
        (
            {
                "recurrence_type": "monthly",
                "monthly_mode": "ordinal_weekday",
                "monthly_ordinal": "fifth",
                "monthly_weekday": "monday",
            },
            date(2026, 3, 30),
        ),
        ({"recurrence_type": "yearly", "yearly_month": 2, "yearly_day": 29}, date(2024, 2, 29)),
    ],
)
def test_range_projection_matches_chained_completion_semantics(config, first_due):
    engine = RecurrenceEngine()
    end = date(2030, 1, 1)
    expected = []
    due = first_due
    while due < end:
        expected.append(due)
        due = engine.calculate_next_due_date(config, due).date()
    assert list(engine.iter_due_dates(config, first_due, end)) == expected


async def test_event_property_never_replays_old_schedules(hass):
    calendar = make_calendar(due=utc(2000, 1, 1), pattern_interval=1)
    with patch(
        "custom_components.sh_chore_tracker.calendar.dt_util.now",
        return_value=utc(2026, 11, 3),
    ):
        await calendar.async_initialize(hass)
        with patch.object(calendar._engine, "iter_due_dates", side_effect=AssertionError("replay")):
            for _ in range(10):
                assert calendar.event.start == date(2026, 11, 3)


async def test_range_queries_are_complete_read_only_and_label_projections(hass):
    calendar = make_calendar()
    before = deepcopy(calendar.coordinator.chore_data)

    events = await calendar.async_get_events(hass, utc(2026, 11, 1), utc(2026, 12, 1))
    later = await calendar.async_get_events(hass, utc(2027, 1, 1), utc(2027, 2, 1))

    assert [event.start for event in events] == [date(2026, 11, day) for day in range(2, 31, 2)]
    assert [event.start for event in later] == [date(2027, 1, day) for day in range(1, 32, 2)]
    assert all(event.all_day and event.end == event.start + timedelta(days=1) for event in events)
    assert events[0].summary == "Dishes"
    assert all(event.summary == "Dishes (projected)" for event in events[1:] + later)
    assert "person.test" in events[0].description
    assert "Wash the dishes" in events[0].description
    assert "assumes completion" in events[1].description
    assert len({event.uid for event in events}) == len(events)
    repeated = await calendar.async_get_events(hass, utc(2026, 11, 1), utc(2026, 11, 5))
    assert repeated[1].uid == events[1].uid
    assert calendar.coordinator.chore_data == before
    calendar.coordinator.async_save_state.assert_not_called()
    calendar.coordinator.async_request_refresh.assert_not_called()


async def test_range_boundaries_and_invalid_ranges(hass):
    calendar = make_calendar()
    assert await calendar.async_get_events(hass, utc(2026, 11, 1), utc(2026, 11, 2)) == []
    assert await calendar.async_get_events(hass, utc(2026, 11, 3), utc(2026, 11, 4)) == []
    partial = await calendar.async_get_events(hass, utc(2026, 11, 2, 12), utc(2026, 11, 4, 12))
    assert [event.start for event in partial] == [date(2026, 11, 2), date(2026, 11, 4)]
    assert await calendar.async_get_events(hass, utc(2026, 11, 2), utc(2026, 11, 2)) == []
    with pytest.raises(HomeAssistantError, match="range end"):
        await calendar.async_get_events(hass, utc(2026, 11, 3), utc(2026, 11, 2))


@pytest.mark.parametrize(("month", "day", "hours"), [(3, 8, 23), (11, 1, 25)])
async def test_local_all_day_boundaries_across_dst(hass, month, day, hours):
    await hass.config.async_set_time_zone("America/New_York")
    zone = dt_util.DEFAULT_TIME_ZONE
    due = datetime(2026, month, day, tzinfo=zone)
    following = datetime.combine(due.date() + timedelta(days=1), datetime.min.time(), zone)
    calendar = make_calendar(due=due)
    events = await calendar.async_get_events(
        hass, due.astimezone(timezone.utc), following.astimezone(timezone.utc)
    )
    assert len(events) == 1
    assert events[0].start == due.date()
    assert (
        events[0].end_datetime_local.astimezone(timezone.utc)
        - events[0].start_datetime_local.astimezone(timezone.utc)
    ).total_seconds() == hours * 3600
    assert await calendar.async_get_events(hass, following, following + timedelta(hours=1)) == []


@pytest.mark.parametrize("status", ["pending", "overdue", "snoozed", "complete", "skipped"])
async def test_actual_due_date_is_authoritative_for_every_status(hass, status):
    calendar = make_calendar()
    calendar.coordinator.chore_data["dishes"]["state"]["status"] = status
    events = await calendar.async_get_events(hass, utc(2026, 11, 2), utc(2026, 11, 5))
    assert [(event.start, event.summary) for event in events] == [
        (date(2026, 11, 2), "Dishes"),
        (date(2026, 11, 4), "Dishes (projected)"),
    ]


async def test_overdue_seed_stays_anchored_and_current_event_rolls_forward(hass):
    calendar = make_calendar(due=utc(2026, 11, 1))
    calendar.coordinator.chore_data["dishes"]["state"]["status"] = "overdue"
    with patch(
        "custom_components.sh_chore_tracker.calendar.dt_util.now",
        return_value=utc(2026, 11, 3, 12),
    ):
        await calendar.async_initialize(hass)
        assert calendar.event.start == date(2026, 11, 3)
        assert calendar.event.summary == "Dishes (projected)"
        assert calendar.state == "on"
    with patch(
        "custom_components.sh_chore_tracker.calendar.dt_util.now",
        return_value=utc(2026, 11, 4),
    ):
        await calendar.async_initialize(hass)
        assert calendar.event.start == date(2026, 11, 5)
        assert calendar.state == "off"
    events = await calendar.async_get_events(hass, utc(2026, 11, 1), utc(2026, 11, 8))
    assert events[0].start == date(2026, 11, 1)
    assert events[0].summary == "Dishes"
    assert calendar.coordinator.chore_data["dishes"]["state"]["next_due_date"] == utc(2026, 11, 1)


async def test_simultaneous_chores_empty_hub_and_invalid_due_date(hass):
    calendar = make_calendar()
    calendar.coordinator.chore_data["another"] = deepcopy(calendar.coordinator.chore_data["dishes"])
    events = await calendar.async_get_events(hass, utc(2026, 11, 2), utc(2026, 11, 3))
    assert [event.uid for event in events] == ["another_2026-11-02", "dishes_2026-11-02"]
    calendar.coordinator.chore_data.clear()
    assert calendar.event is None
    assert await calendar.async_get_events(hass, utc(2026, 11, 1), utc(2026, 12, 1)) == []
    calendar = make_calendar(due=None)
    assert calendar.event is None
    calendar = make_calendar(due="not-a-date")
    with pytest.raises(HomeAssistantError, match="Invalid due date"):
        await calendar.async_get_events(hass, utc(2026, 11, 1), utc(2026, 12, 1))


def test_invalid_nonadvancing_and_overflowing_recurrence_errors_are_explicit():
    engine = RecurrenceEngine()
    with pytest.raises(HomeAssistantError, match="invalid recurrence"):
        list(engine.iter_due_dates({"pattern_interval": 0}, date(2026, 11, 1), date(2026, 12, 1)))
    with (
        patch.object(engine, "calculate_next_due_date", return_value=utc(2026, 11, 1)),
        pytest.raises(HomeAssistantError, match="must advance"),
    ):
        list(engine.iter_due_dates({}, date(2026, 11, 1), date(2026, 12, 1)))
    with pytest.raises(HomeAssistantError, match="supported date range"):
        list(
            engine.iter_due_dates(
                {"interval_unit": "years", "pattern_interval": 10},
                date(9998, 1, 1),
                date.max,
            )
        )


async def test_long_range_yields_without_truncating_or_using_live_mutations(hass):
    calendar = make_calendar(due=utc(2020, 1, 1), pattern_interval=1)
    original = calendar._events_in_range
    loop = asyncio.get_running_loop()
    entered = asyncio.Event()
    release = threading.Event()

    def blocked(*args):
        loop.call_soon_threadsafe(entered.set)
        if not release.wait(5):
            raise RuntimeError("Test did not release executor")
        return original(*args)

    with patch.object(calendar, "_events_in_range", new=blocked):
        task = asyncio.create_task(
            calendar.async_get_events(hass, utc(2026, 1, 1), utc(2027, 1, 1))
        )
        await asyncio.wait_for(entered.wait(), 5)
        calendar.coordinator.chore_data.clear()
        release.set()
        events = await task
    assert len(events) == 365
    assert events[-1].start == date(2026, 12, 31)
