"""Sensor platform for SmartHass Chore Tracker."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from . import ChoreCoordinator
from .const import (
    CHORE_STATUS_COMPLETE,
    CHORE_STATUS_DUE,
    CHORE_STATUS_OVERDUE,
    CHORE_STATUS_PENDING,
    CHORE_STATUS_SNOOZED,
    CONF_ASSIGNED_PERSON,
    CONF_CHORE_DESCRIPTION,
    CONF_CHORE_NAME,
    DOMAIN,
    HUB_UNIQUE_ID,
    SUBENTRY_TYPE_CHORE,
    SUBENTRY_TYPE_SUMMARY,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class DueChore:
    """A chore and its next scheduled due date."""

    chore_id: str
    chore_data: dict[str, Any]
    due_date: datetime


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up chore sensors for the household hub."""

    try:
        coordinator: ChoreCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    except KeyError:
        _LOGGER.error("Coordinator not found for entry: %s", config_entry.entry_id)
        return

    summary = config_entry.get_subentries_of_type(SUBENTRY_TYPE_SUMMARY)[0]
    async_add_entities(
        [HubNextDueSensor(coordinator), HubOverdueCountSensor(coordinator)],
        config_subentry_id=summary.subentry_id,
    )
    for subentry in config_entry.get_subentries_of_type(SUBENTRY_TYPE_CHORE):
        async_add_entities(
            [ChoreEntity(coordinator, config_entry, subentry)],
            config_subentry_id=subentry.subentry_id,
        )


class HubSensor(CoordinatorEntity[ChoreCoordinator], SensorEntity):
    """Base class for sensors attached to the household hub device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: ChoreCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, HUB_UNIQUE_ID)},
            name="Chores",
            manufacturer="Chore Tracker",
            model="Summary",
        )

    def _chores(self) -> dict[str, dict[str, Any]]:
        return self.coordinator.chore_data


class HubNextDueSensor(HubSensor):
    """Signed days until the nearest chore occurrence."""

    _attr_native_unit_of_measurement = "d"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "next_due"

    def __init__(self, coordinator: ChoreCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{HUB_UNIQUE_ID}_next_due"
        self.entity_id = "sensor.chores_next_due"

    def _next_chore(self) -> DueChore | None:
        due_chores: list[DueChore] = []
        for chore_id, chore_data in self._chores().items():
            due_date = _parse_state_datetime(chore_data["state"].get("next_due_date"))
            if due_date is not None:
                due_chores.append(DueChore(chore_id, chore_data, due_date))
        return min(due_chores, key=lambda item: item.due_date) if due_chores else None

    @property
    def native_value(self) -> int | None:
        """Return signed days until the nearest chore is due."""
        next_chore = self._next_chore()
        if next_chore is None:
            return None
        return (next_chore.due_date.date() - dt_util.now().date()).days

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose which chore is next."""
        next_chore = self._next_chore()
        if next_chore is None:
            return {}
        chore_id = next_chore.chore_id
        chore_data = next_chore.chore_data
        due_date = next_chore.due_date
        return {
            "chore_id": chore_id,
            "chore_name": chore_data["config"].get(CONF_CHORE_NAME),
            "entity_id": self.coordinator.entity_id_for_chore(chore_id, chore_data["config"]),
            "next_due_date": due_date.isoformat(),
        }


class HubOverdueCountSensor(HubSensor):
    """Number of chores currently overdue."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "overdue_count"

    def __init__(self, coordinator: ChoreCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{HUB_UNIQUE_ID}_overdue_count"
        self.entity_id = "sensor.chores_overdue_count"

    @property
    def native_value(self) -> int:
        """Return the number of overdue chores."""
        return sum(
            chore_data["state"].get("status") == CHORE_STATUS_OVERDUE
            for chore_data in self._chores().values()
        )


def _parse_state_datetime(value: datetime | str | None) -> datetime | None:
    """Parse stored due-date values for aggregate calculations."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


class ChoreEntity(CoordinatorEntity[ChoreCoordinator], SensorEntity):
    """Representation of a Chore sensor.

    A Home Assistant sensor entity that represents a single chore with
    comprehensive state and attribute information for automation and UI display.
    Supports all-day event model with flexible recurrence patterns.
    """

    _attr_has_entity_name = True
    _attr_device_class = None
    _attr_native_unit_of_measurement = "d"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: ChoreCoordinator,
        config_entry: ConfigEntry,
        subentry: ConfigSubentry,
    ) -> None:
        """Initialize the sensor.

        Sets up the chore entity with proper naming, unique ID, and
        coordinator integration for state management.

        Args:
            coordinator: ChoreCoordinator instance for this chore
            config_entry: ConfigEntry containing chore configuration
        """
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._subentry = subentry
        self.chore_id = subentry.unique_id or subentry.subentry_id

        chore_name = subentry.data.get(CONF_CHORE_NAME, subentry.title)

        # Create safe entity ID from chore name
        safe_chore_name = chore_name.lower().replace(" ", "_").replace("-", "_")
        # Remove any non-alphanumeric characters except underscores
        safe_chore_name = "".join(c for c in safe_chore_name if c.isalnum() or c == "_")

        # Create unique ID with chore prefix
        self._attr_unique_id = f"chore_{self.chore_id}"

        # Set entity_id directly instead of using suggested_object_id
        self.entity_id = f"sensor.chore_{safe_chore_name}"

        self._attr_suggested_object_id = f"chore_{safe_chore_name}"
        self._attr_name = None
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.chore_id)},
            via_device_id=dr.async_get_device_id_by_identifier(
                coordinator.hass,
                (DOMAIN, HUB_UNIQUE_ID),
                config_entry_id=config_entry.entry_id,
            ),
            name=chore_name,
            manufacturer="SmartHass",
            model="chore",
        )

    def _chore_data(self) -> dict[str, Any] | None:
        """Return this entity's state from the hub coordinator."""
        return self.coordinator.get_chore_data(self.chore_id)

    def _compute_days_until_due(self) -> int:
        """Compute the signed integer days-until-due from coordinator data.

        Returns:
            Signed integer: negative = overdue, 0 = due today, positive = days remaining.
        """
        try:
            chore_data = self._chore_data()
            if not chore_data:
                return 0
            state = chore_data.get("state", {})
            next_due = state.get("next_due_date")
            if not next_due:
                return 0
            if isinstance(next_due, str):
                try:
                    next_due = datetime.fromisoformat(next_due.replace("Z", "+00:00"))
                except ValueError:
                    return 0
            if isinstance(next_due, datetime) and next_due.tzinfo is None:
                next_due = next_due.replace(tzinfo=dt_util.now().tzinfo)
            return (next_due.date() - dt_util.now().date()).days
        except Exception as ex:
            _LOGGER.warning(
                "Error computing days_until_due for chore %s: %s",
                self.chore_id,
                ex,
            )
            return 0

    def _get_status(self) -> str:
        """Return the current status string from coordinator data."""
        try:
            chore_data = self._chore_data()
            if chore_data and "state" in chore_data:
                return chore_data["state"].get("status", CHORE_STATUS_PENDING)
        except Exception as ex:
            _LOGGER.warning(
                "Error getting status for chore %s: %s", self._config_entry.entry_id, ex
            )
        return CHORE_STATUS_PENDING

    @property
    def native_value(self) -> int:
        """Return the sensor state as days until due (signed integer).

        Negative values indicate overdue chores, 0 means due today,
        positive values indicate days remaining.

        Returns:
            Signed integer days until due date.
        """
        return self._compute_days_until_due()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes.

        Provides comprehensive chore information for automation and UI display,
        including due dates, completion history, recurrence details, and
        snooze/skip metadata.

        Returns:
            Dictionary of chore attributes for Home Assistant
        """
        try:
            chore_data = self._chore_data()
            if not chore_data:
                return {}

            state = chore_data.get("state", {})
            config = chore_data.get("config", {})

            # Resolve next_due_date for attribute output
            next_due = state.get("next_due_date")
            if next_due and isinstance(next_due, str):
                try:
                    next_due = datetime.fromisoformat(next_due.replace("Z", "+00:00"))
                except ValueError:
                    next_due = None
            if isinstance(next_due, datetime) and next_due.tzinfo is None:
                next_due = next_due.replace(tzinfo=dt_util.now().tzinfo)

            attributes = {
                "status": self._get_status(),
                "integration_domain": DOMAIN,
                "days_until_due": self._compute_days_until_due(),
                "next_due_date": next_due.isoformat() if next_due else None,
                "completion_count": state.get("completion_count", state.get("completed_count", 0)),
                "last_completed_date": self._format_datetime_attr(
                    state.get("last_completed_date", state.get("last_completed"))
                ),
                "assigned_person": config.get(CONF_ASSIGNED_PERSON),
                "description": config.get(CONF_CHORE_DESCRIPTION, ""),
                "recurrence_type": config.get("recurrence_type", "interval"),
                "pattern_interval": config.get("pattern_interval", 1),
                "created_at": self._format_datetime_attr(state.get("created_date")),
            }

            # Get recurrence description safely
            try:
                from . import RecurrenceEngine

                recurrence_engine = RecurrenceEngine()
                attributes["recurrence_description"] = recurrence_engine.get_recurrence_description(
                    config
                )
            except Exception as ex:
                _LOGGER.warning("Error getting recurrence description: %s", ex)
                attributes["recurrence_description"] = "Unknown"

            # Add snooze information if applicable
            if state.get("snooze_until"):
                attributes["snooze_until"] = self._format_datetime_attr(state["snooze_until"])
                attributes["snooze_reason"] = state.get("snooze_reason", "")

            # Add skip information if applicable
            if state.get("last_skip_date"):
                attributes["last_skip_date"] = self._format_datetime_attr(state["last_skip_date"])
                attributes["skip_reason"] = state.get("skip_reason", "")
                attributes["skip_restored"] = state.get("skip_restored", False)

            return attributes

        except Exception as ex:
            _LOGGER.warning(
                "Error getting extra_state_attributes for chore %s: %s",
                self.chore_id,
                ex,
            )
            return {}

    def _format_datetime_attr(self, dt_value: datetime | str | None) -> str | None:
        """Format datetime attribute safely.

        Converts datetime objects to ISO format strings for Home Assistant
        compatibility, handles string inputs, and safely handles None values.

        Args:
            dt_value: Datetime value to format (datetime, string, or None)

        Returns:
            ISO formatted datetime string or None
        """
        if not dt_value:
            return None

        if isinstance(dt_value, str):
            return dt_value

        if isinstance(dt_value, datetime):
            return dt_value.isoformat()

        return None

    @property
    def icon(self) -> str:
        """Return the icon for the sensor.

        Provides status-appropriate icons for the chore entity in the UI.

        Returns:
            Material Design icon name based on chore status
        """
        status = self._get_status()
        if status == CHORE_STATUS_COMPLETE:
            return "mdi:check-circle"
        elif status == CHORE_STATUS_DUE:
            return "mdi:calendar-today"
        elif status == CHORE_STATUS_OVERDUE:
            return "mdi:alert-circle"
        elif status == CHORE_STATUS_SNOOZED:
            return "mdi:sleep"
        else:
            return "mdi:clipboard-list"

    async def async_update(self) -> None:
        """Trigger coordinator refresh.

        State transitions (snooze expiry, overdue detection, complete→pending)
        are handled centrally in ChoreCoordinator._async_update_data.
        """
        await self.coordinator.async_request_refresh()
