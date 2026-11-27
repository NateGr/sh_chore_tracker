"""Tests for logbook event descriptions."""

from unittest.mock import MagicMock

from custom_components.sh_chore_tracker.const import (
    DOMAIN,
    EVENT_CHORE_COMPLETED,
    EVENT_CHORE_CONFIG_CHANGED,
)
from custom_components.sh_chore_tracker.logbook import async_describe_events


def _describers() -> dict:
    registered = {}
    async_describe_events(
        MagicMock(), lambda domain, event, fn: registered.update({(domain, event): fn})
    )
    return registered


def test_config_changed_is_described_with_old_and_new_values() -> None:
    describe = _describers()[(DOMAIN, EVENT_CHORE_CONFIG_CHANGED)]
    event = MagicMock(
        data={
            "entity_id": "sensor.chore_dishes",
            "changed": {"pattern_interval": {"old": 7, "new": 14}},
        }
    )

    result = describe(event)

    assert result["message"] == "config changed: pattern_interval 7 -> 14"
    assert result["entity_id"] == "sensor.chore_dishes"


def test_completed_is_described() -> None:
    describe = _describers()[(DOMAIN, EVENT_CHORE_COMPLETED)]
    event = MagicMock(
        data={
            "entity_id": "sensor.chore_dishes",
            "completion_count": 5,
            "next_due_date": "2026-10-13T00:00:00+00:00",
        }
    )

    assert describe(event)["message"] == "completed (total 5), next due 2026-10-13"
