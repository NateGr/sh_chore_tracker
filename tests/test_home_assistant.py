"""Exercise integration lifecycle through real Home Assistant fixtures."""

from datetime import timedelta

import pytest
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntryState
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from custom_components.sh_chore_tracker.const import (
    DOMAIN,
    SUBENTRY_TYPE_CHORE,
    SUBENTRY_TYPE_SUMMARY,
)

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")


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
