"""Read-only household calendar generated from chore schedules."""

from __future__ import annotations

import asyncio
import logging
from copy import deepcopy
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from . import ChoreCoordinator, InvalidProjectionConfig, RecurrenceEngine, _parse_state_datetime
from .const import (
    CONF_ASSIGNED_PERSON,
    CONF_CHORE_DESCRIPTION,
    CONF_CHORE_NAME,
    DOMAIN,
    HUB_UNIQUE_ID,
    SUBENTRY_TYPE_SUMMARY,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class ScheduledChore:
    """Snapshot of the configuration and actual current occurrence."""

    chore_id: str
    config: dict[str, Any]
    due_date: date
    valid_projection: bool


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Attach one calendar to the household's automatic summary group."""
    coordinator: ChoreCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    summary = config_entry.get_subentries_of_type(SUBENTRY_TYPE_SUMMARY)[0]
    calendar = ChoreCalendar(coordinator)
    await calendar.async_initialize(hass)
    async_add_entities(
        [calendar],
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
        self._event: CalendarEvent | None = None
        self._ready = False
        self._revision = 0
        self._refresh_task: asyncio.Task[None] | None = None
        self._invalid_schedules: set[str] = set()
        self._event_day: date | None = None
        self._event_chores: list[ScheduledChore] = []
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
        invalid: set[str] = set()
        for chore_id, chore_data in self.coordinator.chore_data.items():
            value = chore_data["state"].get("next_due_date")
            if value is None:
                continue
            due = _parse_state_datetime(value)
            if due is None:
                raise HomeAssistantError(f"Invalid due date for chore {chore_id}")
            config = deepcopy(chore_data["config"])
            try:
                self._engine.projection_config(config)
                valid_projection = True
            except InvalidProjectionConfig as err:
                invalid.add(chore_id)
                valid_projection = False
                if chore_id not in self._invalid_schedules:
                    _LOGGER.warning(
                        "Cannot project chore %s (%s): %s; its current due date remains visible",
                        config.get(CONF_CHORE_NAME, chore_id),
                        chore_id,
                        err,
                    )
            chores.append(ScheduledChore(chore_id, config, due.date(), valid_projection))
        self._invalid_schedules = invalid
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
        """Return the cached earliest active or upcoming occurrence."""
        return self._event if self._ready else None

    @property
    def available(self) -> bool:
        """Avoid presenting a stale event while recomputing."""
        return self._ready and super().available

    def _find_next_event(self, chores: list[ScheduledChore], today: date) -> CalendarEvent | None:
        """Calculate from a snapshot in an executor, never in an entity property."""
        candidates = []
        for chore in chores:
            if not chore.valid_projection:
                due = chore.due_date if chore.due_date >= today else None
            else:
                due = next(
                    (
                        due
                        for due in self._engine.iter_due_dates(
                            chore.config, chore.due_date, date.max
                        )
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

    async def async_initialize(self, hass: HomeAssistant) -> None:
        """Compute the initial event before registering the entity."""
        while True:
            today = dt_util.now().date()
            chores = self._scheduled_chores()
            event = await hass.async_add_executor_job(self._find_next_event, chores, today)
            if today == dt_util.now().date() and chores == self._scheduled_chores():
                self._event = event
                self._event_day = today
                self._event_chores = chores
                self._ready = True
                return

    async def async_added_to_hass(self) -> None:
        """Refresh cached events after local midnight and coordinator changes."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_track_time_change(self.hass, self._handle_midnight, hour=0, minute=0, second=0)
        )
        if (
            self._event_day != dt_util.now().date()
            or self._event_chores != self._scheduled_chores()
        ):
            self._schedule_refresh()

    @callback
    def _handle_midnight(self, _now: datetime) -> None:
        self._schedule_refresh()

    @callback
    def _handle_coordinator_update(self) -> None:
        self._schedule_refresh()

    @callback
    def _schedule_refresh(self) -> None:
        self._revision += 1
        self._ready = False
        self.async_write_ha_state()
        if self._refresh_task is None or self._refresh_task.done():
            self._refresh_task = self.hass.async_create_task(self._async_refresh_event())

    async def _async_refresh_event(self) -> None:
        """Coalesce updates; never publish an obsolete snapshot."""
        while True:
            revision = self._revision
            today = dt_util.now().date()
            try:
                chores = self._scheduled_chores()
                event = await self.hass.async_add_executor_job(self._find_next_event, chores, today)
                latest_chores = self._scheduled_chores()
            except HomeAssistantError:
                _LOGGER.exception("Failed to refresh the household chore calendar")
                return
            if (
                revision != self._revision
                or today != dt_util.now().date()
                or chores != latest_chores
            ):
                continue
            self._event = event
            self._event_day = today
            self._event_chores = chores
            self._ready = True
            self.async_write_ha_state()
            return

    async def async_will_remove_from_hass(self) -> None:
        """Prevent pending calculations from publishing after removal."""
        if self._refresh_task is not None:
            self._refresh_task.cancel()
        await super().async_will_remove_from_hass()

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

        return await hass.async_add_executor_job(
            self._events_in_range, self._scheduled_chores(), start_date, end_date, end_day
        )

    def _events_in_range(
        self,
        chores: list[ScheduledChore],
        start_date: datetime,
        end_date: datetime,
        end_day: date,
    ) -> list[CalendarEvent]:
        """Expand a snapshot away from the Home Assistant event loop."""
        events = []
        for chore in chores:
            dates = (
                self._engine.iter_due_dates(chore.config, chore.due_date, end_day)
                if chore.valid_projection
                else (chore.due_date,)
            )
            for due in dates:
                if due < start_date.date():
                    continue
                event = self._make_event(chore, due)
                if event.end_datetime_local > start_date and event.start_datetime_local < end_date:
                    events.append(event)
        return sorted(events, key=lambda event: (event.start, event.uid or ""))
