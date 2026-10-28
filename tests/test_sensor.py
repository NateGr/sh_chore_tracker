"""Tests for chore tracker sensor attributes."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from custom_components.chore_tracker.const import (
    DOMAIN,
    SUBENTRY_TYPE_CHORE,
    SUBENTRY_TYPE_SUMMARY,
)
from custom_components.chore_tracker.sensor import (
    ChoreEntity,
    HubNextDueSensor,
    HubOverdueCountSensor,
    async_setup_entry,
)


def _make_entity(next_due_date: datetime, status: str = "pending") -> ChoreEntity:
    """Build a chore entity with controlled coordinator data."""
    coordinator = MagicMock()
    chore_data = {
        "state": {
            "status": status,
            "next_due_date": next_due_date,
            "completion_count": 0,
            "last_completed_date": None,
            "created_date": datetime(2026, 5, 26, 19, 31, 27),
        },
        "config": {
            "chore_name": "Test Chore",
            "chore_description": "Desc",
            "recurrence_type": "interval",
            "pattern_interval": 1,
            "interval_unit": "days",
            "assigned_person": "none",
        },
    }

    config_entry = MagicMock()
    config_entry.entry_id = "entry_1"
    config_entry.title = "Chore: Test Chore"
    coordinator.get_chore_data.return_value = chore_data
    coordinator.chore_data = {"entry_1": chore_data}
    subentry = MagicMock()
    subentry.unique_id = "entry_1"
    subentry.subentry_id = "subentry_1"
    subentry.title = "Test Chore"
    subentry.data = chore_data["config"]

    with patch(
        "custom_components.chore_tracker.sensor.dr.async_get_device_id_by_identifier",
        return_value="hub_device",
    ):
        return ChoreEntity(coordinator, config_entry, subentry)


def test_native_value_is_integer_days_until_due() -> None:
    """native_value should return signed integer days until due, not a string."""
    entity = _make_entity(datetime(2026, 5, 27, 0, 0))

    with patch(
        "custom_components.chore_tracker.sensor.dt_util.now",
        return_value=datetime(2026, 5, 26, 19, 31, 27),
    ):
        value = entity.native_value

    assert isinstance(value, int)
    assert value == 1


def test_device_info_groups_chore_under_hub_device() -> None:
    """Each chore device is linked beneath the household hub."""
    entity = _make_entity(datetime(2026, 5, 27, 0, 0))

    device_info = entity.device_info

    assert device_info["identifiers"] == {(DOMAIN, "entry_1")}
    assert device_info["via_device_id"] == "hub_device"
    assert device_info["name"] == "Test Chore"
    assert device_info["manufacturer"] == "SmartHass"
    assert device_info["model"] == "chore"
    assert entity.name is None


@pytest.mark.parametrize(
    ("next_due", "status", "days_until_due"),
    [
        pytest.param(datetime(2026, 10, 6, tzinfo=timezone.utc), "due", 0, id="today"),
        pytest.param(datetime(2026, 10, 7, tzinfo=timezone.utc), "pending", 1, id="tomorrow"),
    ],
)
def test_attributes_read_the_individual_chore_record(
    next_due: datetime, status: str, days_until_due: int
) -> None:
    entity = _make_entity(next_due, status)
    with patch(
        "custom_components.chore_tracker.sensor.dt_util.now",
        return_value=datetime(2026, 10, 6, 12, tzinfo=timezone.utc),
    ):
        attributes = entity.extra_state_attributes

    assert attributes["next_due_date"] == next_due.isoformat()
    assert attributes["status"] == status
    assert attributes["days_until_due"] == days_until_due
    assert attributes["created_at"] == "2026-05-26T19:31:27"
    assert attributes["assigned_person"] == "none"
    assert attributes["description"] == "Desc"
    assert attributes["recurrence_description"] == "Every day"


def test_native_value_tomorrow_is_one() -> None:
    """native_value should be 1 when due date is tomorrow."""
    entity = _make_entity(datetime(2026, 5, 27, 0, 0))

    with patch(
        "custom_components.chore_tracker.sensor.dt_util.now",
        return_value=datetime(2026, 5, 26, 19, 31, 27),
    ):
        value = entity.native_value

    assert value == 1


def test_native_value_day_after_tomorrow_is_two() -> None:
    """native_value should be 2 when due date is day-after-tomorrow."""
    entity = _make_entity(datetime(2026, 5, 28, 0, 0))

    with patch(
        "custom_components.chore_tracker.sensor.dt_util.now",
        return_value=datetime(2026, 5, 26, 19, 31, 27),
    ):
        value = entity.native_value

    assert value == 2


def test_status_attribute_returns_status_string() -> None:
    """extra_state_attributes['status'] should return the status string."""
    entity = _make_entity(datetime(2026, 5, 27, 0, 0), status="pending")

    with patch(
        "custom_components.chore_tracker.sensor.dt_util.now",
        return_value=datetime(2026, 5, 26, 19, 31, 27),
    ):
        attrs = entity.extra_state_attributes

    assert attrs["status"] == "pending"


def test_integration_domain_attribute() -> None:
    """extra_state_attributes['integration_domain'] should always match the integration domain."""
    entity = _make_entity(datetime(2026, 5, 27, 0, 0))

    with patch(
        "custom_components.chore_tracker.sensor.dt_util.now",
        return_value=datetime(2026, 5, 26, 19, 31, 27),
    ):
        attrs = entity.extra_state_attributes

    assert attrs["integration_domain"] == "chore_tracker"


def test_days_until_due_also_present_as_attribute() -> None:
    """days_until_due should appear as an attribute as well as being the sensor state."""
    entity = _make_entity(datetime(2026, 5, 27, 0, 0))

    with patch(
        "custom_components.chore_tracker.sensor.dt_util.now",
        return_value=datetime(2026, 5, 26, 19, 31, 27),
    ):
        attrs = entity.extra_state_attributes
        value = entity.native_value

    assert "days_until_due" in attrs
    assert attrs["days_until_due"] == 1
    assert value == attrs["days_until_due"]


def test_hub_aggregate_sensors_report_next_due_and_overdue_count() -> None:
    coordinator = MagicMock()
    coordinator.data = {
        "laundry": {
            "config": {"chore_name": "Laundry"},
            "state": {
                "status": "pending",
                "next_due_date": datetime(2026, 5, 28),
            },
        },
        "dishes": {
            "config": {"chore_name": "Dishes"},
            "state": {
                "status": "overdue",
                "next_due_date": datetime(2026, 5, 25),
            },
        },
    }
    coordinator.chore_data = coordinator.data
    coordinator.entity_id_for_chore.side_effect = lambda chore_id, _config: (
        f"sensor.chore_{chore_id}"
    )

    next_due = HubNextDueSensor(coordinator)
    overdue_count = HubOverdueCountSensor(coordinator)

    assert next_due.entity_id == "sensor.chores_next_due"
    assert overdue_count.entity_id == "sensor.chores_overdue_count"
    assert next_due.device_info["model"] == "Summary"
    assert overdue_count.device_info["model"] == "Summary"

    with patch(
        "custom_components.chore_tracker.sensor.dt_util.now",
        return_value=datetime(2026, 5, 26, 12, 0),
    ):
        assert next_due.native_value == -1
        assert next_due.extra_state_attributes["entity_id"] == "sensor.chore_dishes"
    assert overdue_count.native_value == 1


@pytest.mark.asyncio
async def test_setup_registers_each_chore_entity_with_its_subentry() -> None:
    coordinator = MagicMock()
    hass = MagicMock()
    hass.data = {DOMAIN: {"hub_entry": coordinator}}
    entry = MagicMock()
    entry.entry_id = "hub_entry"
    subentry = MagicMock()
    subentry.subentry_id = "subentry_1"
    subentry.unique_id = "chore_1"
    subentry.title = "Laundry"
    subentry.data = {"chore_name": "Laundry"}
    summary = MagicMock()
    summary.subentry_id = "summary_subentry"
    entry.get_subentries_of_type.side_effect = {
        SUBENTRY_TYPE_CHORE: [subentry],
        SUBENTRY_TYPE_SUMMARY: [summary],
    }.__getitem__
    add_entities = MagicMock()

    await async_setup_entry(hass, entry, add_entities)

    assert len(add_entities.call_args_list) == 2
    summary_call = add_entities.call_args_list[0]
    assert summary_call.kwargs["config_subentry_id"] == "summary_subentry"
    assert len(summary_call.args[0]) == 2
    chore_call = add_entities.call_args_list[1]
    assert chore_call.kwargs["config_subentry_id"] == "subentry_1"
    assert chore_call.args[0][0].chore_id == "chore_1"
