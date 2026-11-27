"""Describe SmartHass Chore Tracker events in the Home Assistant logbook."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from homeassistant.components.logbook import LOGBOOK_ENTRY_ENTITY_ID, LOGBOOK_ENTRY_MESSAGE
from homeassistant.core import Event, HomeAssistant, callback

from .const import (
    DOMAIN,
    EVENT_CHORE_COMPLETE_UNDONE,
    EVENT_CHORE_COMPLETED,
    EVENT_CHORE_CONFIG_CHANGED,
    EVENT_CHORE_SKIPPED,
    EVENT_CHORE_SNOOZED,
)


def _describe_completed(data: dict[str, Any]) -> str:
    return f"completed (total {data.get('completion_count', '?')}), next due {_date(data.get('next_due_date'))}"


def _describe_undone(data: dict[str, Any]) -> str:
    return f"completion undone (total {data.get('completion_count', '?')})"


def _describe_snoozed(data: dict[str, Any]) -> str:
    message = f"snoozed {data.get('snoozed_for_days', '?')} day(s) until {_date(data.get('new_due_date'))}"
    return f"{message}: {data['reason']}" if data.get("reason") else message


def _describe_skipped(data: dict[str, Any]) -> str:
    message = f"skipped, next due {_date(data.get('next_due_date'))}"
    return f"{message}: {data['reason']}" if data.get("reason") else message


def _describe_config_changed(data: dict[str, Any]) -> str:
    changes = ", ".join(
        f"{field} {change.get('old')} -> {change.get('new')}"
        for field, change in (data.get("changed") or {}).items()
    )
    return f"config changed: {changes}"


def _date(value: str | None) -> str:
    """Trim an ISO datetime to its date part."""
    return value[:10] if isinstance(value, str) else "unknown"


_DESCRIBERS: dict[str, Callable[[dict[str, Any]], str]] = {
    EVENT_CHORE_COMPLETED: _describe_completed,
    EVENT_CHORE_COMPLETE_UNDONE: _describe_undone,
    EVENT_CHORE_SNOOZED: _describe_snoozed,
    EVENT_CHORE_SKIPPED: _describe_skipped,
    EVENT_CHORE_CONFIG_CHANGED: _describe_config_changed,
}


@callback
def async_describe_events(
    hass: HomeAssistant,
    async_describe_event: Callable[[str, str, Callable[[Event], dict[str, Any]]], None],
) -> None:
    """Register logbook descriptions for chore events."""

    def make_describer(describe: Callable[[dict[str, Any]], str]):
        @callback
        def async_describe(event: Event) -> dict[str, Any]:
            return {
                LOGBOOK_ENTRY_MESSAGE: describe(event.data),
                LOGBOOK_ENTRY_ENTITY_ID: event.data.get("entity_id"),
            }

        return async_describe

    for event_type, describe in _DESCRIBERS.items():
        async_describe_event(DOMAIN, event_type, make_describer(describe))
