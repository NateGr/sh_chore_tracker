"""Read-only household calendar generated from chore schedules."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from . import ChoreCoordinator, RecurrenceEngine, _parse_state_datetime
from .const import (
    CONF_ASSIGNED_PERSON,
    CONF_CHORE_DESCRIPTION,
    CONF_CHORE_NAME,
    DOMAIN,
    HUB_UNIQUE_ID,
    SUBENTRY_TYPE_SUMMARY,
)


@dataclass(frozen=True)
class ScheduledChore:
    """Snapshot of the configuration and actual current occurrence."""

    chore_id: str
    config: dict[str, Any]
    due_date: date


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Attach one calendar to the household's automatic summary group."""
    coordinator: ChoreCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    summary = config_entry.get_subentries_of_type(SUBENTRY_TYPE_SUMMARY)[0]
    async_add_entities(
        [ChoreCalendar(coordinator)],
        config_subentry_id=summary.subentry_id,
    )


class ChoreCalendar(CoordinatorEntity[ChoreCoordinator], CalendarEntity):
    """Expose actual and hypothetical due dates without storing calendar events."""

    _attr_has_entity_name = True
    _attr_translation_key = "schedule"
    _attr_supported_features = 0

    def __init__(self, coordinator: ChoreCoordinator) -> None:
        super().__init__(coordinator)
        self._engine = RecurrenceEngine()
        self._attr_unique_id = f"{HUB_UNIQUE_ID}_calendar"
        self.entity_id = "calendar.chores"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, HUB_UNIQUE_ID)},
            name="Chores",
            manufacturer="Chore Tracker",
            model="Summary",
        )

    def _scheduled_chores(self) -> list[ScheduledChore]:
        chores = []
        for chore_id, chore_data in self.coordinator.chore_data.items():
            value = chore_data["state"].get("next_due_date")
            if value is None:
                continue
            due = _parse_state_datetime(value)
            if due is None:
                raise HomeAssistantError(f"Invalid due date for chore {chore_id}")
            chores.append(ScheduledChore(chore_id, dict(chore_data["config"]), due.date()))
        return chores

    def _make_event(self, chore: ScheduledChore, due_date: date) -> CalendarEvent:
        projected = due_date != chore.due_date
        name = chore.config.get(CONF_CHORE_NAME, chore.chore_id)
        details = [chore.config.get(CONF_CHORE_DESCRIPTION) or "", f"Chore ID: {chore.chore_id}"]
        person = chore.config.get(CONF_ASSIGNED_PERSON)
        if person and person != "none":
            details.append(f"Assigned person: {person}")
        if projected:
            details.append(
                "Projected occurrence: assumes completion on every scheduled due date. "
                "This is not a recorded completion or a committed due date."
            )
        else:
            details.append("Current scheduled occurrence.")
        return CalendarEvent(
            start=due_date,
            end=due_date + timedelta(days=1),
            summary=f"{name} (projected)" if projected else name,
            description="\n".join(detail for detail in details if detail),
            uid=f"{chore.chore_id}_{due_date.isoformat()}",
        )

    @property
    def event(self) -> CalendarEvent | None:
        """Return the earliest active or upcoming actual/projected occurrence."""
        today = dt_util.now().date()
        candidates = []
        for chore in self._scheduled_chores():
            due = next(
                (
                    due
                    for due in self._engine.iter_due_dates(chore.config, chore.due_date, date.max)
                    if due >= today
                ),
                None,
            )
            if due is not None:
                candidates.append(self._make_event(chore, due))
        return (
            min(candidates, key=lambda event: (event.start, event.uid or ""))
            if candidates
            else None
        )

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Expand schedules and return events overlapping the requested range."""
        if end_date < start_date:
            raise HomeAssistantError("Calendar range end must not precede its start")
        if end_date == start_date:
            return []
        start_date = dt_util.as_local(start_date)
        end_date = dt_util.as_local(end_date)
        # Include the upper bound's day only when the request ends after midnight.
        end_day = end_date.date()
        if end_date > dt_util.start_of_local_day(end_date):
            end_day += timedelta(days=1)

        events = []
        iterations = 0
        for chore in self._scheduled_chores():
            for due in self._engine.iter_due_dates(chore.config, chore.due_date, end_day):
                iterations += 1
                if iterations % 256 == 0:
                    await asyncio.sleep(0)
                if due < start_date.date():
                    continue
                event = self._make_event(chore, due)
                if event.end_datetime_local > start_date and event.start_datetime_local < end_date:
                    events.append(event)
        return sorted(events, key=lambda event: (event.start, event.uid or ""))
