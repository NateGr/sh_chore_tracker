"""Exercise integration lifecycle through real Home Assistant fixtures."""

from datetime import timedelta
from unittest.mock import Mock

import pytest
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntryState
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.sh_chore_tracker.calendar import ChoreCalendar
from custom_components.sh_chore_tracker.const import (
    DOMAIN,
    SUBENTRY_TYPE_CHORE,
    SUBENTRY_TYPE_SUMMARY,
)

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")


@pytest.fixture(autouse=True)
async def use_utc(hass):
    await hass.config.async_set_time_zone("UTC")


async def finish_interval_flow(manager, result, name):
    """Complete the shared chore creation or reconfiguration steps."""
    for data in (
        {"chore_name": name, "chore_description": "", "assigned_person": "none"},
        {"recurrence_type": "interval"},
        {"pattern_interval": 2, "interval_unit": "days"},
        {"first_occurrence_date": (dt_util.now().date() + timedelta(days=1)).isoformat()},
    ):
        assert result["type"] == FlowResultType.FORM
        result = await manager.async_configure(result["flow_id"], data)
    return result


async def create_hub(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await finish_interval_flow(hass.config_entries.flow, result, "Dishes")
    assert result["type"] == FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    assert entry.state is ConfigEntryState.LOADED
    return entry


async def get_calendar_events(hass, start, end):
    response = await hass.services.async_call(
        "calendar",
        "get_events",
        {
            "entity_id": "calendar.chores",
            "start_date_time": start,
            "end_date_time": end,
        },
        blocking=True,
        return_response=True,
    )
    return response["calendar.chores"]["events"]


async def test_setup_entities_service_storage_and_reload(hass):
    entry = await create_hub(hass)
    chore = entry.get_subentries_of_type(SUBENTRY_TYPE_CHORE)[0]
    assert len(entry.get_subentries_of_type(SUBENTRY_TYPE_SUMMARY)) == 1
    registry = er.async_get(hass)
    entities = er.async_entries_for_config_entry(registry, entry.entry_id)
    chore_entities = [
        entity for entity in entities if entity.config_subentry_id == chore.subentry_id
    ]
    sensor = next(entity for entity in chore_entities if entity.domain == "sensor")
    assert any(entity.domain == "button" for entity in chore_entities)
    assert hass.states.get(sensor.entity_id) is not None
    assert hass.services.has_service(DOMAIN, "complete_chore")
    calendar_entry = next(entity for entity in entities if entity.domain == "calendar")
    assert (
        calendar_entry.config_subentry_id
        == entry.get_subentries_of_type(SUBENTRY_TYPE_SUMMARY)[0].subentry_id
    )
    assert hass.states.get(calendar_entry.entity_id) is not None

    await hass.services.async_call(
        DOMAIN, "complete_chore", {"entity_id": sensor.entity_id}, blocking=True
    )
    await hass.async_block_till_done()
    state = hass.states.get(sensor.entity_id)
    assert state.attributes["completion_count"] == 1
    stored = await Store(hass, 1, f"sh_chore_tracker_hub_{entry.entry_id}").async_load()
    assert stored["chores"][chore.unique_id]["completion_count"] == 1

    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    assert len(entry.get_subentries_of_type(SUBENTRY_TYPE_SUMMARY)) == 1
    assert hass.states.get(sensor.entity_id).attributes["completion_count"] == 1
    assert registry.async_get(sensor.entity_id).config_subentry_id == chore.subentry_id
    assert registry.async_get(calendar_entry.entity_id).unique_id == calendar_entry.unique_id
    assert (
        len(
            [
                entity
                for entity in er.async_entries_for_config_entry(registry, entry.entry_id)
                if entity.domain == "calendar"
            ]
        )
        == 1
    )
    registry.async_update_entity(calendar_entry.entity_id, new_entity_id="calendar.household")
    await hass.async_block_till_done()
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get("calendar.household") is not None
    assert registry.async_get("calendar.household").unique_id == calendar_entry.unique_id


async def test_add_and_reconfigure_subentry(hass):
    entry = await create_hub(hass)
    manager = hass.config_entries.subentries
    result = await manager.async_init(
        (entry.entry_id, SUBENTRY_TYPE_CHORE), context={"source": config_entries.SOURCE_USER}
    )
    result = await finish_interval_flow(manager, result, "Laundry")
    assert result["type"] == FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    laundry = next(
        chore
        for chore in entry.get_subentries_of_type(SUBENTRY_TYPE_CHORE)
        if chore.title == "Laundry"
    )
    result = await manager.async_init(
        (entry.entry_id, SUBENTRY_TYPE_CHORE),
        context={"source": config_entries.SOURCE_RECONFIGURE, "subentry_id": laundry.subentry_id},
    )
    result = await finish_interval_flow(manager, result, "Wash clothes")
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    await hass.async_block_till_done()
    assert entry.subentries[laundry.subentry_id].title == "Wash clothes"
    assert entry.state is ConfigEntryState.LOADED
    start = dt_util.start_of_local_day()
    end = start + timedelta(days=8)
    events = await get_calendar_events(hass, start, end)
    assert {event["summary"] for event in events} == {
        "Dishes",
        "Dishes (projected)",
        "Wash clothes",
        "Wash clothes (projected)",
    }
    new_due = (start + timedelta(days=3)).date()
    hass.config_entries.async_update_subentry(
        entry,
        entry.subentries[laundry.subentry_id],
        data={
            **entry.subentries[laundry.subentry_id].data,
            "first_occurrence_date": new_due.isoformat(),
        },
    )
    await hass.async_block_till_done()
    events = await get_calendar_events(hass, start, end)
    assert (
        next(event for event in events if event["summary"] == "Wash clothes")["start"]
        == new_due.isoformat()
    )
    assert hass.config_entries.async_remove_subentry(entry, laundry.subentry_id)
    await hass.async_block_till_done()
    events = await get_calendar_events(hass, start, end)
    assert {event["summary"] for event in events} == {"Dishes", "Dishes (projected)"}


@pytest.mark.parametrize(
    ("actions", "expected_days"),
    [
        ([("complete_chore", {})], 2),
        ([("complete_chore", {"completion_date": "2026-11-03T12:00:00+00:00"})], 4),
        ([("snooze_chore", {"days": 3})], 4),
        ([("skip_chore", {})], 3),
        ([("skip_chore", {}), ("restore_chore", {})], 1),
        ([("complete_chore", {}), ("undo_complete_chore", {})], 1),
        ([("snooze_chore", {"days": 3}), ("reset_next_due_date", {})], 1),
        ([("snooze_chore", {"days": 3}), ("skip_chore", {}), ("restore_chore", {})], 4),
        ([("reassign_chore", {"person_id": "person.test"})], 1),
    ],
)
async def test_calendar_recalculates_after_chore_actions(hass, freezer, actions, expected_days):
    freezer.move_to("2026-11-01T12:00:00+00:00")
    entry = await create_hub(hass)
    hass.states.async_set("person.test", "home", {"friendly_name": "Test person"})
    start = dt_util.start_of_local_day()
    end = start + timedelta(days=15)
    for action, data in actions:
        await hass.services.async_call(
            DOMAIN, action, {"entity_id": "sensor.chore_dishes", **data}, blocking=True
        )
        await hass.async_block_till_done()
    coordinator = hass.data[DOMAIN][entry.entry_id]
    chore = next(iter(coordinator.chore_data.values()))
    due = (start + timedelta(days=expected_days)).date()
    assert chore["state"]["next_due_date"].date() == due
    events = await get_calendar_events(hass, start, end)
    assert events[0]["start"] == due.isoformat()
    assert events[0]["summary"] == "Dishes"
    assert events[1]["start"] == (due + timedelta(days=2)).isoformat()
    assert events[1]["summary"] == "Dishes (projected)"
    if actions[-1][0] == "reassign_chore":
        assert "person.test" in events[0]["description"]
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert await get_calendar_events(hass, start, end) == events


async def test_calendar_subscription_updates_for_non_earliest_chore_and_unloads(hass, freezer):
    freezer.move_to("2026-11-01T12:00:00+00:00")
    entry = await create_hub(hass)
    manager = hass.config_entries.subentries
    result = await manager.async_init(
        (entry.entry_id, SUBENTRY_TYPE_CHORE), context={"source": config_entries.SOURCE_USER}
    )
    await finish_interval_flow(manager, result, "Laundry")
    await hass.async_block_till_done()
    await hass.services.async_call(
        DOMAIN, "snooze_chore", {"entity_id": "sensor.chore_laundry", "days": 1}, blocking=True
    )
    await hass.async_block_till_done()
    component = hass.data["calendar"]
    calendar = component.get_entity("calendar.chores")
    assert isinstance(calendar, ChoreCalendar)
    start = dt_util.start_of_local_day()
    end = start + timedelta(days=10)
    listener = Mock()
    unsubscribe = calendar.async_subscribe_events(start, end, listener)
    calendar.async_update_event_listeners()
    await hass.async_block_till_done()
    before = listener.call_args.args[0]
    current_event = calendar.event

    await hass.services.async_call(
        DOMAIN, "snooze_chore", {"entity_id": "sensor.chore_laundry", "days": 3}, blocking=True
    )
    await hass.async_block_till_done()
    freezer.tick(timedelta(seconds=10))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    after = listener.call_args.args[0]
    assert calendar.event == current_event
    assert before != after
    assert next(event for event in after if event["summary"] == "Laundry")["start"] == "2026-11-06"
    unsubscribe()
    calendar_entity_id = calendar.entity_id
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(calendar_entity_id).state == "unavailable"
    assert component.get_entity(calendar_entity_id) is None
    assert not calendar._alarm_unsubs
    assert calendar._event_listener_debouncer is None
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(calendar_entity_id) is not None
    assert await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(calendar_entity_id) is None
    assert er.async_get(hass).async_get(calendar_entity_id) is None


async def test_calendar_state_rolls_at_local_midnight(hass, freezer):
    freezer.move_to("2026-11-01T12:00:00+00:00")
    await create_hub(hass)
    assert hass.states.get("calendar.chores").state == "off"
    freezer.move_to("2026-11-02T00:00:00+00:00")
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get("calendar.chores").state == "on"
    freezer.move_to("2026-11-03T00:00:00+00:00")
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    state = hass.states.get("calendar.chores")
    assert state.state == "off"
    assert state.attributes["message"] == "Dishes (projected)"
    assert state.attributes["start_time"] == "2026-11-04 00:00:00"
