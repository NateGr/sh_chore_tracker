"""SmartHass Chore Tracker integration for Home Assistant."""

import logging
from datetime import date, datetime, timedelta
from types import MappingProxyType
from typing import Any, Dict
from uuid import uuid4

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.const import ATTR_ENTITY_ID, Platform
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import (
    config_validation as cv,
)
from homeassistant.helpers import (
    device_registry as dr,
)
from homeassistant.helpers import (
    entity_registry as er,
)
from homeassistant.helpers.service import async_register_admin_service
from homeassistant.helpers.storage import Store
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    CHORE_STATUS_COMPLETE,
    CHORE_STATUS_DUE,
    CHORE_STATUS_OVERDUE,
    CHORE_STATUS_PENDING,
    CHORE_STATUS_SKIPPED,
    CHORE_STATUS_SNOOZED,
    CONF_ASSIGNED_PERSON,
    CONF_CHORE_DESCRIPTION,
    CONF_CHORE_NAME,
    CONF_FIRST_OCCURRENCE_DATE,
    CONF_HUB_ENTRY,
    CONF_INTERVAL_UNIT,
    CONF_MONTHLY_DAY,
    CONF_MONTHLY_MODE,
    CONF_MONTHLY_ORDINAL,
    CONF_MONTHLY_WEEKDAY,
    CONF_PATTERN_INTERVAL,
    CONF_RECURRENCE_TYPE,
    CONF_WEEKLY_DAYS,
    CONF_YEARLY_DAY,
    CONF_YEARLY_MONTH,
    CONFIG_ENTRY_VERSION,
    DEFAULT_RESTORE_WINDOW_HOURS,
    DEFAULT_SNOOZE_DAYS,
    DOMAIN,
    EVENT_CHORE_COMPLETE_UNDONE,
    EVENT_CHORE_COMPLETED,
    EVENT_CHORE_OVERDUE,
    EVENT_CHORE_REASSIGNED,
    EVENT_CHORE_RESTORED,
    EVENT_CHORE_SCHEDULE_RESET,
    EVENT_CHORE_SKIPPED,
    EVENT_CHORE_SNOOZED,
    HUB_UNIQUE_ID,
    INTERVAL_UNIT_DAYS,
    INTERVAL_UNIT_MONTHS,
    INTERVAL_UNIT_WEEKS,
    INTERVAL_UNIT_YEARS,
    MONTHLY_MODE_DAY_OF_MONTH,
    MONTHLY_MODE_ORDINAL_WEEKDAY,
    MONTHLY_ORDINALS,
    RECURRENCE_TYPE_INTERVAL,
    RECURRENCE_TYPE_MONTHLY,
    RECURRENCE_TYPE_WEEKLY,
    RECURRENCE_TYPE_YEARLY,
    SERVICE_COMPLETE_CHORE,
    SERVICE_CREATE_CHORE,
    SERVICE_LIST_MY_CHORES,
    SERVICE_REASSIGN_CHORE,
    SERVICE_RESET_NEXT_DUE_DATE,
    SERVICE_RESTORE_CHORE,
    SERVICE_SKIP_CHORE,
    SERVICE_SNOOZE_CHORE,
    SERVICE_UNDO_COMPLETE_CHORE,
    SUBENTRY_TYPE_CHORE,
    SUBENTRY_TYPE_SUMMARY,
    WEEKDAYS,
)

# Import date utilities
from .date_utils import (
    DateCalculator,
    coerce_date,
    normalize_first_occurrence_date,
    nth_weekday_of_month,
)


def _as_ha_datetime(value: datetime) -> datetime:
    """Normalize a datetime to Home Assistant local timezone awareness."""
    if value.tzinfo is not None:
        return value
    return value.replace(tzinfo=dt_util.now().tzinfo)


def _parse_state_datetime(value: datetime | str | None) -> datetime | None:
    """Parse state datetime values and normalize them for safe comparisons."""
    if value is None:
        return None
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return None
    if isinstance(value, datetime):
        return _as_ha_datetime(value)
    return None


def _resolve_open_status(next_due: datetime | None) -> str:
    """Resolve pending/due/overdue state from due date using date-only semantics."""
    if next_due is None:
        return CHORE_STATUS_PENDING

    today = dt_util.now().date()
    due_date = next_due.date()
    if due_date < today:
        return CHORE_STATUS_OVERDUE
    if due_date == today:
        return CHORE_STATUS_DUE
    return CHORE_STATUS_PENDING


def _calculate_first_occurrence_datetime(
    config: dict[str, Any],
    requested_value: date | datetime | str | None,
) -> datetime:
    """Calculate normalized first occurrence datetime from config and user input."""
    requested_date = coerce_date(requested_value) or dt_util.now().date()
    normalized_date, _adjusted = normalize_first_occurrence_date(config, requested_date)
    return _as_ha_datetime(datetime.combine(normalized_date, datetime.min.time()))


class RecurrenceEngine:
    """Engine for calculating chore recurrence patterns using all-day event model.

    This class implements a strategy pattern with functional composition to handle
    four types of recurrence patterns: interval, weekly, monthly, and yearly.
    All calculations operate on date objects only (no time components) following
    the all-day event model.

    The engine uses a DateCalculator utility for complex date arithmetic including
    leap year handling, month-end overflow, and weekday calculations.

    Attributes:
        _calculators: Dictionary mapping recurrence types to calculator functions
        date_calc: DateCalculator instance for date arithmetic operations
    """

    def __init__(self):
        """Initialize the RecurrenceEngine.

        Sets up the strategy pattern dictionary with calculator functions for each
        recurrence type and initializes the DateCalculator utility.
        """
        # Strategy pattern with functional composition
        self._calculators: Dict[str, Any] = {
            "interval": self._calculate_interval,
            "weekly": self._calculate_weekly,
            "monthly": self._calculate_monthly,
            "yearly": self._calculate_yearly,
        }

        # DateCalculator utility for complex date arithmetic
        self.date_calc = DateCalculator()

    def calculate_next_due_date(
        self, config: Dict[str, Any], completion_date: datetime
    ) -> datetime:
        """Calculate the next due date based on recurrence configuration.

        Args:
            config: Recurrence configuration dictionary
            completion_date: Date when chore was completed

        Returns:
            Next due date as datetime (time will be set to start of day)
        """
        recurrence_type = config.get("recurrence_type", "interval")

        # Get the appropriate calculator function
        calculator = self._calculators.get(recurrence_type, self._calculate_interval)

        # Convert completion_date to date for all-day event calculations
        completion_as_date = (
            completion_date.date() if isinstance(completion_date, datetime) else completion_date
        )

        # Calculate next due date (returns date object)
        next_due_date = calculator(config, completion_as_date)

        # Convert back to HA-aware datetime at start of day for backward compatibility
        return _as_ha_datetime(datetime.combine(next_due_date, datetime.min.time()))

    def _calculate_interval(self, config: Dict[str, Any], completion_date: date) -> date:
        """Calculate next due date for interval-based recurrence (completion-based).

        Examples:
            Every 3 days after completion
            Every 2 weeks after completion
            Every 6 months after completion
        """
        pattern_interval = config.get("pattern_interval", 1)
        interval_unit = config.get("interval_unit", "days")

        return self.date_calc.add_interval_units(completion_date, pattern_interval, interval_unit)

    def _calculate_weekly(self, config: Dict[str, Any], completion_date: date) -> date:
        """Calculate next due date for weekly recurrence (calendar-based).

        Examples:
            Every Monday (pattern_interval=1)
            Every 2 weeks on Tuesday and Friday (pattern_interval=2)
        """
        pattern_interval = config.get("pattern_interval", 1)
        weekly_days = config.get("weekly_days", ["monday"])

        # Import weekday mapping
        from .date_utils import WEEKDAY_MAP

        # Handle both string and list formats
        if isinstance(weekly_days, str):
            weekly_days = [day.strip() for day in weekly_days.split(",")]

        # Convert day names to weekday numbers
        target_weekdays = [
            WEEKDAY_MAP.get(day.lower(), 0) for day in weekly_days if day.lower() in WEEKDAY_MAP
        ]
        if not target_weekdays:
            target_weekdays = [0]  # Default to Monday

        # For pattern_interval > 1, we need to find the occurrence that's pattern_interval weeks from completion
        if pattern_interval > 1:
            # Start pattern_interval weeks after completion date
            target_week_start = completion_date + timedelta(weeks=pattern_interval)
            next_occurrence = self.date_calc.next_weekday_occurrence(
                target_week_start, target_weekdays
            )
        else:
            # Find next occurrence of target weekdays from completion date
            next_occurrence = self.date_calc.next_weekday_occurrence(
                completion_date, target_weekdays
            )

        return next_occurrence

    def _calculate_monthly(self, config: Dict[str, Any], completion_date: date) -> date:
        """Calculate next due date for monthly recurrence (calendar-based).

        Examples:
            Every 15th of the month (pattern_interval=1)
            Every 3 months on the 31st (pattern_interval=3, with smart last day)
        """
        pattern_interval = config.get("pattern_interval", 1)
        monthly_mode = config.get(CONF_MONTHLY_MODE, MONTHLY_MODE_DAY_OF_MONTH)

        if monthly_mode == MONTHLY_MODE_ORDINAL_WEEKDAY:
            target_month = date(completion_date.year, completion_date.month, 1)
            target_month = self.date_calc.add_interval_units(
                target_month, pattern_interval, "months"
            )
            monthly_ordinal = config.get(CONF_MONTHLY_ORDINAL, "first")
            monthly_weekday = config.get(CONF_MONTHLY_WEEKDAY, "monday")

            while True:
                candidate = nth_weekday_of_month(
                    target_month.year,
                    target_month.month,
                    monthly_weekday,
                    monthly_ordinal,
                )
                if candidate is not None:
                    return candidate
                target_month = self.date_calc.add_interval_units(
                    target_month, pattern_interval, "months"
                )

        monthly_day = int(config.get(CONF_MONTHLY_DAY, 1))
        monthly_day = max(1, min(31, monthly_day))

        return self.date_calc.add_months_with_smart_day(
            completion_date, pattern_interval, monthly_day
        )

    def _calculate_yearly(self, config: Dict[str, Any], completion_date: date) -> date:
        """Calculate next due date for yearly recurrence (calendar-based).

        Examples:
            Every March 15th (pattern_interval=1)
            Every 2 years on December 25th (pattern_interval=2)
        """
        pattern_interval = config.get("pattern_interval", 1)
        yearly_month = config.get("yearly_month", 1)
        yearly_day = config.get("yearly_day", 1)

        # Ensure valid values
        yearly_month = max(1, min(12, yearly_month))
        yearly_day = max(1, min(31, yearly_day))

        return self.date_calc.add_years_with_leap_day_logic(
            completion_date, pattern_interval, yearly_month, yearly_day
        )

    def get_recurrence_description(self, config: Dict[str, Any]) -> str:
        """Generate human-readable description of recurrence pattern.

        Args:
            config: Recurrence configuration dictionary containing pattern details

        Returns:
            Human-readable string describing the recurrence pattern
        """
        recurrence_type = config.get("recurrence_type", "interval")
        pattern_interval = config.get("pattern_interval", 1)

        if recurrence_type == "interval":
            interval_unit = config.get("interval_unit", "days")
            if pattern_interval == 1:
                return f"Every {interval_unit[:-1]}"  # Remove 's' from unit
            else:
                return f"Every {pattern_interval} {interval_unit}"

        elif recurrence_type == "weekly":
            weekly_days = config.get("weekly_days", ["monday"])

            # Handle both string and list formats
            if isinstance(weekly_days, str):
                weekly_days = [day.strip() for day in weekly_days.split(",")]

            # Format day list
            if len(weekly_days) == 1:
                day_str = weekly_days[0].title()
            else:
                day_list = ", ".join(day.title() for day in weekly_days[:-1])
                day_str = f"{day_list} and {weekly_days[-1].title()}"

            if pattern_interval == 1:
                return f"Every {day_str}"
            else:
                return f"Every {pattern_interval} weeks on {day_str}"

        elif recurrence_type == "monthly":
            monthly_mode = config.get(CONF_MONTHLY_MODE, MONTHLY_MODE_DAY_OF_MONTH)
            if monthly_mode == MONTHLY_MODE_ORDINAL_WEEKDAY:
                monthly_ordinal = str(config.get(CONF_MONTHLY_ORDINAL, "first")).title()
                monthly_weekday = str(config.get(CONF_MONTHLY_WEEKDAY, "monday")).title()
                phrase = f"the {monthly_ordinal} {monthly_weekday}"
                if pattern_interval == 1:
                    return f"Monthly on {phrase}"
                return f"Every {pattern_interval} months on {phrase}"

            monthly_day = int(config.get(CONF_MONTHLY_DAY, 1))

            suffix = "th"
            if monthly_day in [1, 21, 31]:
                suffix = "st"
            elif monthly_day in [2, 22]:
                suffix = "nd"
            elif monthly_day in [3, 23]:
                suffix = "rd"

            if pattern_interval == 1:
                return f"Monthly on the {monthly_day}{suffix}"
            return f"Every {pattern_interval} months on the {monthly_day}{suffix}"

        elif recurrence_type == "yearly":
            yearly_month = config.get("yearly_month", 1)
            yearly_day = config.get("yearly_day", 1)

            # Month names
            month_names = [
                "January",
                "February",
                "March",
                "April",
                "May",
                "June",
                "July",
                "August",
                "September",
                "October",
                "November",
                "December",
            ]
            month_name = month_names[yearly_month - 1] if 1 <= yearly_month <= 12 else "January"

            if pattern_interval == 1:
                return f"Every {month_name} {yearly_day}"
            else:
                return f"Every {pattern_interval} years on {month_name} {yearly_day}"

        return "Unknown recurrence pattern"

    def validate_recurrence_config(self, config: Dict[str, Any]) -> bool:
        """Validate recurrence configuration.

        Checks that the recurrence configuration contains valid values for the
        specified recurrence type, including pattern intervals, units, and
        pattern-specific parameters.

        Args:
            config: Recurrence configuration dictionary to validate

        Returns:
            True if configuration is valid, False otherwise
        """
        recurrence_type = config.get("recurrence_type", "interval")
        pattern_interval = config.get("pattern_interval", 1)

        # Validate pattern_interval is positive integer
        if not isinstance(pattern_interval, int) or pattern_interval < 1:
            return False

        if recurrence_type == "interval":
            interval_unit = config.get("interval_unit", "days")
            valid_units = {"days", "weeks", "months", "years"}

            if interval_unit not in valid_units:
                return False

            # Validate pattern_interval ranges
            if interval_unit == "days" and pattern_interval > 999:
                return False
            elif interval_unit in ["weeks", "months"] and pattern_interval > 60:
                return False
            elif interval_unit == "years" and pattern_interval > 10:
                return False

        elif recurrence_type == "weekly":
            weekly_days = config.get("weekly_days", [])
            valid_days = {
                "monday",
                "tuesday",
                "wednesday",
                "thursday",
                "friday",
                "saturday",
                "sunday",
            }

            # Handle both string and list formats
            if isinstance(weekly_days, str):
                weekly_days = [day.strip() for day in weekly_days.split(",")]

            if not isinstance(weekly_days, list) or not weekly_days:
                return False

            if not all(day.lower() in valid_days for day in weekly_days):
                return False

            # Validate pattern_interval range for weekly
            if pattern_interval > 52:
                return False

        elif recurrence_type == "monthly":
            monthly_mode = config.get(CONF_MONTHLY_MODE, MONTHLY_MODE_DAY_OF_MONTH)
            if monthly_mode == MONTHLY_MODE_ORDINAL_WEEKDAY:
                monthly_ordinal = config.get(CONF_MONTHLY_ORDINAL)
                monthly_weekday = str(config.get(CONF_MONTHLY_WEEKDAY, "")).lower()
                if monthly_ordinal not in MONTHLY_ORDINALS:
                    return False
                if monthly_weekday not in {
                    "monday",
                    "tuesday",
                    "wednesday",
                    "thursday",
                    "friday",
                    "saturday",
                    "sunday",
                }:
                    return False
            else:
                monthly_day = config.get(CONF_MONTHLY_DAY)
                if not isinstance(monthly_day, int) or not (1 <= monthly_day <= 31):
                    return False

            # Validate pattern_interval range for monthly
            if pattern_interval > 60:
                return False

        elif recurrence_type == "yearly":
            yearly_month = config.get("yearly_month")
            yearly_day = config.get("yearly_day")

            if not isinstance(yearly_month, int) or not (1 <= yearly_month <= 12):
                return False

            if not isinstance(yearly_day, int) or not (1 <= yearly_day <= 31):
                return False

            # Validate pattern_interval range for yearly
            if pattern_interval > 10:
                return False

        else:
            return False  # Unknown recurrence type

        return True


_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BUTTON]

# Update interval for coordinator
UPDATE_INTERVAL = timedelta(minutes=15)


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate config entry metadata before the integration-level hub migration."""
    if config_entry.version < CONFIG_ENTRY_VERSION:
        hass.config_entries.async_update_entry(config_entry, version=CONFIG_ENTRY_VERSION)
        return True
    return config_entry.version == CONFIG_ENTRY_VERSION


async def async_setup(hass: HomeAssistant, _config: ConfigType) -> bool:
    """Consolidate legacy per-chore config entries into the household hub."""
    await _async_migrate_legacy_entries(hass)
    return True


async def _async_migrate_legacy_entries(hass: HomeAssistant) -> None:
    """Import legacy chore entries before their platforms are set up."""
    entries = hass.config_entries.async_entries(DOMAIN)
    hubs = [entry for entry in entries if entry.data.get(CONF_HUB_ENTRY)]
    legacy_entries = [entry for entry in entries if not entry.data.get(CONF_HUB_ENTRY)]
    if not legacy_entries:
        return
    if len(hubs) > 1:
        raise HomeAssistantError("Multiple Chore Tracker hubs are configured")

    hub_entry = hubs[0] if hubs else legacy_entries[0]
    legacy_configs = {
        entry.entry_id: {**dict(entry.data), **dict(entry.options)} for entry in legacy_entries
    }
    state_store = Store(hass, 1, f"sh_chore_tracker_hub_{hub_entry.entry_id}")
    stored = await state_store.async_load() or {}
    chore_states = dict(stored.get("chores", {}))
    entity_registry = er.async_get(hass)
    device_registry = dr.async_get(hass)

    for legacy_entry in legacy_entries:
        chore_id = legacy_entry.entry_id
        config = legacy_configs[chore_id]
        config.pop(CONF_HUB_ENTRY, None)
        if CONF_CHORE_NAME not in config and "name" in config:
            config[CONF_CHORE_NAME] = config.pop("name")
        if CONF_CHORE_DESCRIPTION not in config and "description" in config:
            config[CONF_CHORE_DESCRIPTION] = config.pop("description")
        if CONF_ASSIGNED_PERSON not in config and "assigned_to" in config:
            config[CONF_ASSIGNED_PERSON] = config.pop("assigned_to")
        if CONF_PATTERN_INTERVAL not in config and "interval_days" in config:
            config[CONF_PATTERN_INTERVAL] = config.pop("interval_days")
        if config.get(CONF_RECURRENCE_TYPE) == "fixed":
            config[CONF_RECURRENCE_TYPE] = RECURRENCE_TYPE_INTERVAL
        subentry = next(
            (
                item
                for item in hub_entry.subentries.values()
                if item.subentry_type == SUBENTRY_TYPE_CHORE and item.unique_id == chore_id
            ),
            None,
        )
        if subentry is None:
            subentry = ConfigSubentry(
                data=MappingProxyType(config),
                subentry_type=SUBENTRY_TYPE_CHORE,
                title=config.get("chore_name", legacy_entry.title),
                unique_id=chore_id,
            )
            hass.config_entries.async_add_subentry(hub_entry, subentry)

        if chore_id not in chore_states:
            old_store = Store(hass, 1, f"sh_chore_tracker_{chore_id}")
            old_state = await old_store.async_load()
            if old_state:
                if "last_completed_date" not in old_state and "last_completed" in old_state:
                    old_state["last_completed_date"] = old_state.pop("last_completed")
                if "completion_count" not in old_state and "completed_count" in old_state:
                    old_state["completion_count"] = old_state.pop("completed_count")
                chore_states[chore_id] = old_state

            await state_store.async_save({"chores": chore_states})

        for entity in er.async_entries_for_config_entry(entity_registry, legacy_entry.entry_id):
            disabled_by = entity.disabled_by
            if disabled_by is er.RegistryEntryDisabler.CONFIG_ENTRY and not hub_entry.disabled_by:
                disabled_by = er.RegistryEntryDisabler.USER
            entity_registry.async_update_entity(
                entity.entity_id,
                config_entry_id=hub_entry.entry_id,
                config_subentry_id=subentry.subentry_id,
                disabled_by=disabled_by,
            )

        device = device_registry.async_get_device_by_identifier(
            (DOMAIN, chore_id), legacy_entry.entry_id
        )
        if device is not None:
            disabled_by = device.disabled_by
            if disabled_by is dr.DeviceEntryDisabler.CONFIG_ENTRY and not hub_entry.disabled_by:
                disabled_by = dr.DeviceEntryDisabler.USER
            device_registry.async_update_device(
                device.id,
                new_config_entry_id=hub_entry.entry_id,
                new_config_subentry_id=subentry.subentry_id,
                disabled_by=disabled_by,
            )

    await state_store.async_save({"chores": chore_states})
    hass.config_entries.async_update_entry(
        hub_entry,
        data={CONF_HUB_ENTRY: True},
        options={},
        title="Chore Tracker",
        unique_id=HUB_UNIQUE_ID,
        version=CONFIG_ENTRY_VERSION,
    )

    for legacy_entry in legacy_entries:
        if legacy_entry.entry_id != hub_entry.entry_id:
            await hass.config_entries.async_remove(legacy_entry.entry_id)
        old_store = Store(hass, 1, f"sh_chore_tracker_{legacy_entry.entry_id}")
        await old_store.async_remove()


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the hub when chore subentries change."""
    await hass.config_entries.async_reload(entry.entry_id)


def _async_ensure_summary_subentry(hass: HomeAssistant, entry: ConfigEntry) -> ConfigSubentry:
    """Create the hub's automatic summary group once."""
    if summaries := entry.get_subentries_of_type(SUBENTRY_TYPE_SUMMARY):
        return summaries[0]
    summary = ConfigSubentry(
        data=MappingProxyType({}),
        subentry_type=SUBENTRY_TYPE_SUMMARY,
        title="Overall summary",
        unique_id=f"{HUB_UNIQUE_ID}_summary",
    )
    hass.config_entries.async_add_subentry(entry, summary)
    return summary


def _async_update_hub_entities(
    hass: HomeAssistant, entry: ConfigEntry, summary_subentry_id: str | None = None
) -> None:
    """Remove the redundant indicator and replace generic summary IDs."""
    registry = er.async_get(hass)
    summary_ids = {
        f"{HUB_UNIQUE_ID}_next_due": "chores_next_due",
        f"{HUB_UNIQUE_ID}_overdue_count": "chores_overdue_count",
    }
    for entity in er.async_entries_for_config_entry(registry, entry.entry_id):
        if entity.platform != DOMAIN:
            continue
        if entity.domain == "binary_sensor" and entity.unique_id == f"{HUB_UNIQUE_ID}_any_overdue":
            registry.async_remove(entity.entity_id)
            continue
        if entity.domain != "sensor" or entity.unique_id not in summary_ids:
            continue
        updates: dict[str, Any] = {}
        if summary_subentry_id is not None and entity.config_subentry_id != summary_subentry_id:
            updates["config_subentry_id"] = summary_subentry_id
        object_id = entity.entity_id.split(".", 1)[1]
        if object_id == "chore_tracker" or (
            object_id.startswith("chore_tracker_")
            and object_id.removeprefix("chore_tracker_").isdigit()
        ):
            updates["new_entity_id"] = registry.async_get_available_entity_id(
                "sensor", summary_ids[entity.unique_id]
            )
        if updates:
            registry.async_update_entity(entity.entity_id, **updates)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the Chore Tracker household hub."""
    coordinator = ChoreCoordinator(hass, entry)

    # Restore persisted runtime state before first refresh so the entity
    # comes up with the correct status, next_due_date, and completion history.
    await coordinator.async_load_persisted_state()

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator
    summary = _async_ensure_summary_subentry(hass, entry)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    devices = dr.async_get(hass)
    device = devices.async_get_or_create(
        config_entry_id=entry.entry_id,
        config_subentry_id=summary.subentry_id,
        identifiers={(DOMAIN, HUB_UNIQUE_ID)},
        name="Chores",
        manufacturer="Chore Tracker",
        model="Summary",
    )
    devices.async_update_device(device.id, new_config_subentry_id=summary.subentry_id)

    _async_update_hub_entities(hass, entry, summary.subentry_id)

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    await async_setup_services(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading SmartHass Chore Tracker integration")

    # Unload platforms
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

        await async_unload_services(hass)

    return unload_ok


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unload chore tracker services."""
    _LOGGER.info("🔧 DEBUG: Unregistering chore tracker services")

    services_to_remove = [
        SERVICE_COMPLETE_CHORE,
        SERVICE_UNDO_COMPLETE_CHORE,
        SERVICE_SNOOZE_CHORE,
        SERVICE_SKIP_CHORE,
        SERVICE_RESTORE_CHORE,
        SERVICE_REASSIGN_CHORE,
        SERVICE_RESET_NEXT_DUE_DATE,
        SERVICE_CREATE_CHORE,
        SERVICE_LIST_MY_CHORES,
    ]

    for service in services_to_remove:
        if hass.services.has_service(DOMAIN, service):
            hass.services.async_remove(DOMAIN, service)

    _LOGGER.info("🔧 DEBUG: All chore tracker services unregistered")


class ChoreCoordinator(DataUpdateCoordinator):
    """Own lifecycle state and persistence for all chores in one hub."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator.

        Sets up the DataUpdateCoordinator with appropriate update interval,
        initializes chore data from the config entry, and prepares for
        state management operations.

        Args:
            hass: Home Assistant instance
            entry: ConfigEntry containing chore configuration
        """
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=UPDATE_INTERVAL,
        )
        self.entry = entry
        self._chores: dict[str, dict[str, Any]] = {}
        self._subentry_to_chore: dict[str, str] = {}
        self._store = Store(hass, 1, f"sh_chore_tracker_hub_{entry.entry_id}")
        self._initialize_chore_data()

    def _initialize_chore_data(self):
        """Initialize one config/state record for each chore subentry."""
        for subentry in self.entry.get_subentries_of_type(SUBENTRY_TYPE_CHORE):
            chore_id = subentry.unique_id or subentry.subentry_id
            config = dict(subentry.data)
            self._subentry_to_chore[subentry.subentry_id] = chore_id
            self._chores[chore_id] = {
                "config": config,
                "state": {
                    "status": CHORE_STATUS_PENDING,
                    "completion_count": 0,
                    "last_completed_date": None,
                    "next_due_date": self._calculate_initial_due_date(config),
                    "snooze_until": None,
                    "snooze_reason": None,
                    "snooze_count": 0,
                    "created_date": dt_util.now(),
                },
            }

    def _calculate_initial_due_date(self, config: dict) -> datetime:
        """Calculate the initial due date for a new chore.

        For new chores, determines the first due date based on the recurrence
        pattern. Uses current time as the reference point for calculation.

        Args:
            config: Chore configuration dictionary

        Returns:
            Initial due date as datetime
        """
        return _calculate_first_occurrence_datetime(
            config,
            config.get(CONF_FIRST_OCCURRENCE_DATE),
        )

    async def _async_update_data(self):
        """Update lifecycle state for every chore under the hub."""
        return await self._async_update_hub_data()

    async def _async_update_hub_data(self) -> dict[str, dict[str, Any]]:
        """Update lifecycle states for all chores and save once per refresh."""
        today = dt_util.now().date()
        state_changed = False

        for chore_id, chore_data in self._chores.items():
            state = chore_data["state"]
            config = chore_data["config"]
            status = state.get("status")
            snooze_until = _parse_state_datetime(state.get("snooze_until"))
            next_due = _parse_state_datetime(state.get("next_due_date"))

            def resolve_open_status(due_date: datetime | None) -> str:
                if due_date is None:
                    return CHORE_STATUS_PENDING
                if due_date.date() < today:
                    return CHORE_STATUS_OVERDUE
                if due_date.date() == today:
                    return CHORE_STATUS_DUE
                return CHORE_STATUS_PENDING

            def rolled_over_since(value: datetime | str | None) -> bool:
                parsed = _parse_state_datetime(value)
                return parsed is not None and today > parsed.date()

            resolved = status
            if status == CHORE_STATUS_SNOOZED and snooze_until and today >= snooze_until.date():
                resolved = resolve_open_status(next_due)
                state["snooze_until"] = None
                state["snooze_reason"] = None
            elif status == CHORE_STATUS_SKIPPED and next_due:
                if today >= next_due.date():
                    resolved = resolve_open_status(next_due)
                elif rolled_over_since(state.get("last_skip_date")):
                    resolved = CHORE_STATUS_PENDING
            elif status == CHORE_STATUS_COMPLETE and next_due:
                if today >= next_due.date():
                    resolved = resolve_open_status(next_due)
                elif rolled_over_since(state.get("last_completed_date")):
                    resolved = CHORE_STATUS_PENDING
            elif status in (
                CHORE_STATUS_PENDING,
                CHORE_STATUS_DUE,
                CHORE_STATUS_OVERDUE,
            ):
                resolved = resolve_open_status(next_due)

            if resolved != status:
                state["status"] = resolved
                state_changed = True
                if resolved == CHORE_STATUS_OVERDUE and status != CHORE_STATUS_OVERDUE:
                    self.hass.bus.async_fire(
                        EVENT_CHORE_OVERDUE,
                        {
                            "entity_id": self.entity_id_for_chore(chore_id, config),
                            "entry_id": self.entry.entry_id,
                            "chore_id": chore_id,
                            "from_status": status,
                            "to_status": resolved,
                            "effective_date": today.isoformat(),
                            "next_due_date": next_due.isoformat() if next_due else None,
                        },
                    )

        if state_changed:
            await self.async_save_state()
        return self._chores

    def entity_id_for_chore(self, chore_id: str, config: dict[str, Any]) -> str:
        """Return a registered entity ID, falling back to a name-derived ID."""
        subentry_id = next(
            (
                subentry_id
                for subentry_id, mapped_chore_id in self._subentry_to_chore.items()
                if mapped_chore_id == chore_id
            ),
            None,
        )
        if subentry_id:
            for entity in er.async_entries_for_config_entry(
                er.async_get(self.hass), self.entry.entry_id
            ):
                if (
                    entity.config_subentry_id == subentry_id
                    and entity.domain == "sensor"
                    and entity.unique_id == f"chore_{chore_id}"
                ):
                    return entity.entity_id

        name = config.get("chore_name", chore_id)
        object_id = "".join(
            char
            for char in name.lower().replace(" ", "_").replace("-", "_")
            if char.isalnum() or char == "_"
        )
        return f"sensor.chore_{object_id}"

    def get_chore_data(self, chore_id: str) -> dict[str, Any] | None:
        """Return one chore's current config and lifecycle state."""
        chores = self.data if self.data is not None else self._chores
        return chores.get(chore_id)

    def chore_id_for_subentry(self, subentry_id: str) -> str | None:
        """Resolve the stable chore ID for a Home Assistant subentry ID."""
        return self._subentry_to_chore.get(subentry_id)

    @property
    def chore_data(self) -> dict[str, dict[str, Any]]:
        """Return the current chore map."""
        return self.data if self.data is not None else self._chores

    async def async_load_persisted_state(self) -> None:
        """Load the persisted runtime state map for all chore subentries."""
        await self._async_load_hub_state()

    async def _async_load_hub_state(self) -> None:
        """Restore the hub's versioned per-chore state map."""
        stored = await self._store.async_load() or {}
        stored_chores = stored.get("chores", {})
        datetime_keys = {
            "next_due_date",
            "snooze_until",
            "last_completed_date",
            "last_skip_date",
            "original_due_date",
            "created_date",
            "_undo_completed_at",
        }
        changed = False

        for chore_id, chore_data in self._chores.items():
            state = chore_data["state"]
            saved_state = stored_chores.get(chore_id)
            if saved_state:
                for key, value in saved_state.items():
                    if key in datetime_keys and value:
                        try:
                            state[key] = datetime.fromisoformat(value)
                        except (ValueError, TypeError):
                            continue
                    else:
                        state[key] = value
                if state.get("next_due_date") and not state.get("applied_first_occurrence_date"):
                    seed = coerce_date(chore_data["config"].get(CONF_FIRST_OCCURRENCE_DATE))
                    if seed is not None:
                        state["applied_first_occurrence_date"] = seed
            changed |= self._apply_chore_first_occurrence_update(chore_data)

        if changed:
            await self.async_save_state()

    def _apply_chore_first_occurrence_update(self, chore_data: dict[str, Any]) -> bool:
        """Apply an explicitly changed first occurrence to one chore."""
        config = chore_data["config"]
        state = chore_data["state"]
        configured_date = coerce_date(config.get(CONF_FIRST_OCCURRENCE_DATE))
        if configured_date is None:
            return False
        applied_date = coerce_date(state.get("applied_first_occurrence_date"))
        if applied_date == configured_date:
            return False

        due_date = _calculate_first_occurrence_datetime(config, configured_date)
        state["next_due_date"] = due_date
        state["status"] = _resolve_open_status(due_date)
        state["applied_first_occurrence_date"] = configured_date
        for key in (
            "_undo_previous_state",
            "_undo_completed_at",
            "_undo_used",
        ):
            state.pop(key, None)
        for key in (
            "snooze_until",
            "snooze_reason",
            "skip_reason",
            "last_skip_date",
            "original_due_date",
        ):
            state[key] = None
        state["skip_restored"] = False
        return True

    async def async_save_state(self) -> None:
        """Persist the hub's mutable chore state map."""
        await self._async_save_hub_state()

    async def _async_save_hub_state(self) -> None:
        """Persist every chore's mutable state in one hub store record."""
        if not self._chores:
            return
        serialized_chores: dict[str, dict[str, Any]] = {}
        for chore_id, chore_data in self._chores.items():
            serialized_state: dict[str, Any] = {}
            for key, value in chore_data["state"].items():
                if isinstance(value, (datetime, date)):
                    serialized_state[key] = value.isoformat()
                elif key == "_undo_previous_state" and isinstance(value, dict):
                    serialized_state[key] = {
                        nested_key: nested_value.isoformat()
                        if isinstance(nested_value, (datetime, date))
                        else nested_value
                        for nested_key, nested_value in value.items()
                    }
                else:
                    serialized_state[key] = value
            serialized_chores[chore_id] = serialized_state
        await self._store.async_save({"chores": serialized_chores})


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up the chore tracker services.

    Registers all service handlers for chore management operations:
    - complete_chore: Mark chore as completed
    - undo_complete_chore: Undo a recent completion
    - snooze_chore: Postpone chore for specified days
    - skip_chore: Skip current occurrence
    - restore_chore: Restore skipped chore
    - reassign_chore: Transfer chore to different person
    - reset_next_due_date: Recalculate the next occurrence from completion history

    Args:
        hass: Home Assistant instance for service registration
    """
    if hass.services.has_service(DOMAIN, SERVICE_COMPLETE_CHORE):
        _LOGGER.debug("Services already registered, skipping setup")
        return

    _LOGGER.info("🔧 DEBUG: Setting up chore tracker services")

    # Service schemas
    COMPLETE_CHORE_SCHEMA = vol.Schema(
        {
            vol.Required(ATTR_ENTITY_ID): cv.entity_ids,
            vol.Optional("completion_date"): cv.datetime,
        }
    )

    UNDO_COMPLETE_CHORE_SCHEMA = vol.Schema(
        {
            vol.Required(ATTR_ENTITY_ID): cv.entity_ids,
        }
    )

    SNOOZE_CHORE_SCHEMA = vol.Schema(
        {
            vol.Required(ATTR_ENTITY_ID): cv.entity_ids,
            vol.Optional("days", default=DEFAULT_SNOOZE_DAYS): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=365)
            ),
            vol.Optional("reason"): cv.string,
        }
    )

    SKIP_CHORE_SCHEMA = vol.Schema(
        {
            vol.Required(ATTR_ENTITY_ID): cv.entity_ids,
            vol.Optional("reason"): cv.string,
        }
    )

    RESTORE_CHORE_SCHEMA = vol.Schema(
        {
            vol.Required(ATTR_ENTITY_ID): cv.entity_ids,
        }
    )

    REASSIGN_CHORE_SCHEMA = vol.Schema(
        {
            vol.Required(ATTR_ENTITY_ID): cv.entity_ids,
            vol.Required("person_id"): cv.entity_id,
        }
    )

    RESET_NEXT_DUE_DATE_SCHEMA = vol.Schema({vol.Required(ATTR_ENTITY_ID): cv.entity_ids})
    CREATE_CHORE_SCHEMA = vol.Schema(
        {
            vol.Required(CONF_CHORE_NAME): cv.string,
            vol.Optional(CONF_CHORE_DESCRIPTION, default=""): cv.string,
            vol.Required(CONF_RECURRENCE_TYPE, default=RECURRENCE_TYPE_INTERVAL): vol.In(
                {
                    RECURRENCE_TYPE_INTERVAL,
                    RECURRENCE_TYPE_WEEKLY,
                    RECURRENCE_TYPE_MONTHLY,
                    RECURRENCE_TYPE_YEARLY,
                }
            ),
            vol.Optional(CONF_PATTERN_INTERVAL, default=1): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=999)
            ),
            vol.Optional(CONF_INTERVAL_UNIT, default=INTERVAL_UNIT_DAYS): vol.In(
                {
                    INTERVAL_UNIT_DAYS,
                    INTERVAL_UNIT_WEEKS,
                    INTERVAL_UNIT_MONTHS,
                    INTERVAL_UNIT_YEARS,
                }
            ),
            vol.Optional(CONF_ASSIGNED_PERSON, default="none"): cv.string,
            vol.Optional(CONF_WEEKLY_DAYS, default=["monday"]): [vol.In(WEEKDAYS)],
            vol.Optional(CONF_MONTHLY_MODE, default=MONTHLY_MODE_DAY_OF_MONTH): cv.string,
            vol.Optional(CONF_MONTHLY_DAY, default=1): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=31)
            ),
            vol.Optional(CONF_MONTHLY_ORDINAL, default="first"): cv.string,
            vol.Optional(CONF_MONTHLY_WEEKDAY, default="monday"): vol.In(WEEKDAYS),
            vol.Optional(CONF_YEARLY_MONTH, default=1): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=12)
            ),
            vol.Optional(CONF_YEARLY_DAY, default=1): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=31)
            ),
            vol.Optional(CONF_FIRST_OCCURRENCE_DATE): cv.date,
        }
    )
    LIST_MY_CHORES_SCHEMA = vol.Schema({vol.Required("person_id"): cv.entity_id})

    async def handle_complete_chore(call: ServiceCall) -> None:
        """Handle complete chore service call.

        Processes the complete_chore service call by delegating to the
        common service handler with the complete chore handler function.

        Args:
            call: Service call data containing entity_id and optional completion_date
        """
        await _handle_service_call(hass, call, _complete_chore_handler)

    async def handle_undo_complete_chore(call: ServiceCall) -> None:
        """Handle undo complete chore service call."""
        await _handle_service_call(hass, call, _undo_complete_chore_handler)

    async def handle_snooze_chore(call: ServiceCall) -> None:
        """Handle snooze chore service call."""
        await _handle_service_call(hass, call, _snooze_chore_handler)

    async def handle_skip_chore(call: ServiceCall) -> None:
        """Handle skip chore service call."""
        await _handle_service_call(hass, call, _skip_chore_handler)

    async def handle_restore_chore(call: ServiceCall) -> None:
        """Handle restore chore service call."""
        await _handle_service_call(hass, call, _restore_chore_handler)

    async def handle_reassign_chore(call: ServiceCall) -> None:
        """Handle reassign chore service call."""
        await _handle_service_call(hass, call, _reassign_chore_handler)

    async def handle_reset_next_due_date(call: ServiceCall) -> None:
        """Handle reset next due date service call."""
        await _handle_service_call(hass, call, _reset_next_due_date_handler)

    async def handle_create_chore(call: ServiceCall) -> None:
        """Create a chore under the household hub."""
        await _handle_create_chore(hass, call)

    async def handle_list_my_chores(call: ServiceCall) -> dict[str, Any]:
        """Return chores assigned to the requested person."""
        return _handle_list_my_chores(hass, call)

    # Register services
    hass.services.async_register(
        DOMAIN,
        SERVICE_COMPLETE_CHORE,
        handle_complete_chore,
        schema=COMPLETE_CHORE_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_UNDO_COMPLETE_CHORE,
        handle_undo_complete_chore,
        schema=UNDO_COMPLETE_CHORE_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN, SERVICE_SNOOZE_CHORE, handle_snooze_chore, schema=SNOOZE_CHORE_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_SKIP_CHORE, handle_skip_chore, schema=SKIP_CHORE_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_RESTORE_CHORE, handle_restore_chore, schema=RESTORE_CHORE_SCHEMA
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_REASSIGN_CHORE,
        handle_reassign_chore,
        schema=REASSIGN_CHORE_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_RESET_NEXT_DUE_DATE,
        handle_reset_next_due_date,
        schema=RESET_NEXT_DUE_DATE_SCHEMA,
    )

    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_CREATE_CHORE,
        handle_create_chore,
        schema=CREATE_CHORE_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_LIST_MY_CHORES,
        handle_list_my_chores,
        schema=LIST_MY_CHORES_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )

    _LOGGER.info("🔧 DEBUG: All chore tracker services registered successfully")


async def _handle_service_call(hass: HomeAssistant, call: ServiceCall, handler) -> None:
    """Common service call handler."""
    entity_ids = call.data[ATTR_ENTITY_ID]

    if isinstance(entity_ids, str):
        entity_ids = [entity_ids]

    for entity_id in entity_ids:
        # Find the coordinator and chore data; validation happens inside _find_chore_data
        coordinator, chore_data = await _find_chore_data(hass, entity_id)
        if not coordinator or not chore_data:
            raise ServiceValidationError(f"Chore entity {entity_id} not found")

        # Call the specific handler
        await handler(hass, coordinator, chore_data, entity_id, call.data)


async def _find_chore_data(hass: HomeAssistant, entity_id: str):
    """Find coordinator and chore data for an entity ID.

    Uses the HASS entity registry to validate that the entity belongs to this
    integration (entry.platform == DOMAIN) and to map entity_id → config_entry_id,
    then looks up the coordinator from hass.data[DOMAIN].

    This is the same mechanism used by auto-entities when filtering by 'integration':
    the entity registry 'platform' field is the authoritative source for which
    integration owns an entity, regardless of entity naming conventions.
    """
    registry = er.async_get(hass)
    entry = registry.async_get(entity_id)
    if not entry or not entry.config_entry_id:
        return None, None

    # Validate ownership via the integration platform field — the same field
    # that the auto-entities card exposes as the 'integration' filter.
    if entry.platform != DOMAIN:
        return None, None

    coordinator = hass.data.get(DOMAIN, {}).get(entry.config_entry_id)
    if not coordinator:
        return None, None

    if not entry.config_subentry_id:
        return None, None
    chore_id = coordinator.chore_id_for_subentry(entry.config_subentry_id)
    if chore_id is None:
        return None, None
    return coordinator, coordinator.get_chore_data(chore_id)


async def _complete_chore_handler(
    hass: HomeAssistant,
    coordinator: ChoreCoordinator,
    chore_data: dict,
    entity_id: str,
    service_data: dict,
) -> None:
    """Handle completing a chore."""
    _LOGGER.info("🔧 DEBUG: Completing chore %s", entity_id)

    completion_date = _parse_state_datetime(service_data.get("completion_date"))
    if completion_date is None:
        completion_date = dt_util.now()

    state = chore_data["state"]
    config = chore_data["config"]
    next_due = _parse_state_datetime(state.get("next_due_date"))

    # Ignore duplicate complete calls until the chore is due again.
    if (
        state.get("status") == CHORE_STATUS_COMPLETE
        and next_due is not None
        and completion_date.date() < next_due.date()
    ):
        _LOGGER.info(
            "Ignoring duplicate complete for %s; already complete until %s",
            entity_id,
            next_due,
        )
        return

    # Keep a snapshot so accidental double-complete can be undone.
    state["_undo_previous_state"] = {
        key: value for key, value in state.items() if not key.startswith("_undo_")
    }
    state["_undo_completed_at"] = completion_date
    state["_undo_used"] = False

    # Update state
    state["status"] = CHORE_STATUS_COMPLETE
    state["last_completed_date"] = completion_date
    state["completion_count"] = state.get("completion_count", 0) + 1
    state["snooze_until"] = None  # Clear any snooze
    state["snooze_count"] = 0  # Reset snooze counter on completion

    # Calculate next due date using recurrence engine
    recurrence_engine = RecurrenceEngine()
    state["next_due_date"] = recurrence_engine.calculate_next_due_date(config, completion_date)

    # Persist state before triggering refresh
    await coordinator.async_save_state()

    # Trigger entity refresh
    await coordinator.async_request_refresh()

    # Fire event
    hass.bus.async_fire(
        EVENT_CHORE_COMPLETED,
        {
            "entity_id": entity_id,
            "completed_at": completion_date.isoformat(),
            "next_due_date": state["next_due_date"].isoformat(),
            "completion_count": state["completion_count"],
        },
    )

    _LOGGER.info("Chore %s completed, next due: %s", entity_id, state["next_due_date"])


async def _undo_complete_chore_handler(
    hass: HomeAssistant,
    coordinator: ChoreCoordinator,
    chore_data: dict,
    entity_id: str,
    _service_data: dict,
) -> None:
    """Undo a recent chore completion within the restore window."""
    _LOGGER.info("🔧 DEBUG: Undoing completion for chore %s", entity_id)

    state = chore_data["state"]
    snapshot = state.get("_undo_previous_state")
    undo_completed_at = _parse_state_datetime(state.get("_undo_completed_at"))

    if not snapshot or not undo_completed_at:
        raise ServiceValidationError(f"Chore {entity_id} has no recent completion to undo")

    if state.get("_undo_used", False):
        raise ServiceValidationError(f"Chore {entity_id} completion has already been undone")

    if (dt_util.now() - undo_completed_at).total_seconds() > DEFAULT_RESTORE_WINDOW_HOURS * 3600:
        raise ServiceValidationError(f"Chore {entity_id} completion was too long ago to undo")

    # Restore the exact pre-complete state snapshot.
    state.clear()
    state.update(snapshot)

    await coordinator.async_save_state()
    await coordinator.async_request_refresh()

    hass.bus.async_fire(
        EVENT_CHORE_COMPLETE_UNDONE,
        {
            "entity_id": entity_id,
            "undo_date": dt_util.now().isoformat(),
            "undone_completion_date": undo_completed_at.isoformat(),
            "status": state.get("status"),
            "next_due_date": state.get("next_due_date").isoformat()
            if isinstance(state.get("next_due_date"), datetime)
            else state.get("next_due_date"),
            "completion_count": state.get("completion_count"),
        },
    )

    _LOGGER.info("Chore %s completion undone", entity_id)


async def _snooze_chore_handler(
    hass: HomeAssistant,
    coordinator: ChoreCoordinator,
    chore_data: dict,
    entity_id: str,
    service_data: dict,
) -> None:
    """Handle snoozing a chore."""
    _LOGGER.info("🔧 DEBUG: Snoozing chore %s", entity_id)

    days = service_data.get("days", DEFAULT_SNOOZE_DAYS)
    reason = service_data.get("reason", "")

    state = chore_data["state"]

    # Push next_due_date forward by the snooze period (primary due-date shift)
    current_due = _parse_state_datetime(state.get("next_due_date")) or dt_util.now()
    state["next_due_date"] = current_due + timedelta(days=days)

    # Set snooze tracking fields
    state["status"] = CHORE_STATUS_SNOOZED
    state["snooze_until"] = state["next_due_date"]
    state["snooze_reason"] = reason
    state["snooze_count"] = state.get("snooze_count", 0) + 1

    # Persist state before triggering refresh
    await coordinator.async_save_state()

    # Trigger entity refresh
    await coordinator.async_request_refresh()

    # Fire event
    hass.bus.async_fire(
        EVENT_CHORE_SNOOZED,
        {
            "entity_id": entity_id,
            "snoozed_for_days": days,
            "new_due_date": state["next_due_date"].isoformat(),
            "snooze_count": state["snooze_count"],
            "reason": reason,
        },
    )

    _LOGGER.info("Chore %s snoozed %d days, new due: %s", entity_id, days, state["next_due_date"])


async def _skip_chore_handler(
    hass: HomeAssistant,
    coordinator: ChoreCoordinator,
    chore_data: dict,
    entity_id: str,
    service_data: dict,
) -> None:
    """Handle skipping a chore."""
    _LOGGER.info("🔧 DEBUG: Skipping chore %s", entity_id)

    reason = service_data.get("reason", "")

    state = chore_data["state"]
    config = chore_data["config"]

    # Skip semantics decision: advance from the current due date (pattern-forward),
    # not from "now".
    current_due = _parse_state_datetime(state.get("next_due_date")) or dt_util.now()

    # Store original due date for potential restore
    if not state.get("original_due_date"):
        state["original_due_date"] = current_due

    # Store skip information for potential restore
    state["last_skip_date"] = dt_util.now()
    state["skip_reason"] = reason
    state["skip_restored"] = False

    # Update state
    state["status"] = CHORE_STATUS_SKIPPED

    # Calculate next due date from the current due date (not from now)
    recurrence_engine = RecurrenceEngine()
    state["next_due_date"] = recurrence_engine.calculate_next_due_date(config, current_due)

    # Update coordinator and trigger refresh
    await coordinator.async_save_state()
    await coordinator.async_request_refresh()

    # Fire event
    hass.bus.async_fire(
        EVENT_CHORE_SKIPPED,
        {
            "entity_id": entity_id,
            "skip_date": state["last_skip_date"].isoformat(),
            "next_due_date": state["next_due_date"].isoformat(),
            "reason": reason,
        },
    )

    _LOGGER.info("Chore %s skipped, next due: %s", entity_id, state["next_due_date"])


async def _restore_chore_handler(
    hass: HomeAssistant,
    coordinator: ChoreCoordinator,
    chore_data: dict,
    entity_id: str,
    _service_data: dict,
) -> None:
    """Handle restoring a skipped chore."""
    _LOGGER.info("🔧 DEBUG: Restoring chore %s", entity_id)

    state = chore_data["state"]

    # Validate chore was recently skipped
    if state.get("status") != CHORE_STATUS_SKIPPED:
        raise ServiceValidationError(f"Chore {entity_id} is not in skipped state")

    if state.get("skip_restored", False):
        raise ServiceValidationError(f"Chore {entity_id} has already been restored")

    # Restore to previous state (typically pending or overdue)
    last_skip_date = _parse_state_datetime(state.get("last_skip_date"))
    if (
        last_skip_date
        and (dt_util.now() - last_skip_date).total_seconds() > DEFAULT_RESTORE_WINDOW_HOURS * 3600
    ):
        raise ServiceValidationError(f"Chore {entity_id} was skipped too long ago to restore")

    # Restore the chore
    state["status"] = CHORE_STATUS_PENDING
    state["skip_restored"] = True
    # Restore original due date (before skip moved it forward)
    if "original_due_date" in state:
        state["next_due_date"] = state["original_due_date"]

    # Persist state before triggering refresh
    await coordinator.async_save_state()

    # Trigger entity refresh
    await coordinator.async_request_refresh()

    # Fire event
    hass.bus.async_fire(
        EVENT_CHORE_RESTORED,
        {
            "entity_id": entity_id,
            "restore_date": dt_util.now().isoformat(),
            "original_skip_date": last_skip_date.isoformat() if last_skip_date else None,
        },
    )

    _LOGGER.info("Chore %s restored from skip", entity_id)


async def _reassign_chore_handler(
    hass: HomeAssistant,
    coordinator: ChoreCoordinator,
    chore_data: dict,
    entity_id: str,
    service_data: dict,
) -> None:
    """Handle reassigning a chore."""
    _LOGGER.info("🔧 DEBUG: Reassigning chore %s", entity_id)

    person_id = service_data["person_id"]

    # Validate person entity exists
    person_state = hass.states.get(person_id)
    if not person_state:
        raise ServiceValidationError(f"Person entity {person_id} not found")

    config = chore_data["config"]
    old_person = config.get("assigned_person")

    entity_entry = er.async_get(hass).async_get(entity_id)
    if entity_entry is None or entity_entry.config_subentry_id is None:
        raise ServiceValidationError(f"Chore entity {entity_id} has no chore subentry")
    subentry = coordinator.entry.subentries[entity_entry.config_subentry_id]
    updated_config = {**dict(subentry.data), "assigned_person": person_id}
    hass.config_entries.async_update_subentry(
        coordinator.entry,
        subentry,
        data=MappingProxyType(updated_config),
    )
    chore_data["config"] = updated_config

    # Update coordinator and trigger refresh
    await coordinator.async_request_refresh()

    # Fire event
    hass.bus.async_fire(
        EVENT_CHORE_REASSIGNED,
        {
            "entity_id": entity_id,
            "old_person": old_person,
            "new_person": person_id,
            "reassign_date": dt_util.now().isoformat(),
        },
    )

    _LOGGER.info("Chore %s reassigned from %s to %s", entity_id, old_person, person_id)


async def _reset_next_due_date_handler(
    hass: HomeAssistant,
    coordinator: ChoreCoordinator,
    chore_data: dict,
    entity_id: str,
    _service_data: dict,
) -> None:
    """Reset a chore schedule anchor and clear conflicting transient state."""
    _LOGGER.info("🔧 DEBUG: Resetting next due date for chore %s", entity_id)

    state = chore_data["state"]
    config = chore_data["config"]

    last_completed = _parse_state_datetime(state.get("last_completed_date"))
    if last_completed is not None:
        new_next_due = RecurrenceEngine().calculate_next_due_date(config, last_completed)
    else:
        new_next_due = _calculate_first_occurrence_datetime(
            config, config.get(CONF_FIRST_OCCURRENCE_DATE)
        )

    # Reset schedule anchor and clear transient lifecycle state that conflicts
    # with a manual reset operation.
    state["next_due_date"] = new_next_due
    state["snooze_until"] = None
    state["snooze_reason"] = None
    state["skip_reason"] = None
    state["last_skip_date"] = None
    state["original_due_date"] = None
    state["skip_restored"] = False
    state.pop("_undo_previous_state", None)
    state.pop("_undo_completed_at", None)
    state.pop("_undo_used", None)

    state["status"] = _resolve_open_status(new_next_due)

    await coordinator.async_save_state()
    await coordinator.async_request_refresh()

    hass.bus.async_fire(
        EVENT_CHORE_SCHEDULE_RESET,
        {
            "entity_id": entity_id,
            "anchor_date": last_completed.date().isoformat()
            if last_completed
            else config.get(CONF_FIRST_OCCURRENCE_DATE),
            "next_due_date": new_next_due.isoformat(),
            "status": state["status"],
        },
    )

    _LOGGER.info("Chore %s schedule reset, next due: %s", entity_id, new_next_due)


async def _handle_create_chore(hass: HomeAssistant, call: ServiceCall) -> None:
    """Validate and add a chore subentry to the hub."""
    hub_entry_id = next(iter(hass.data.get(DOMAIN, {})), None)
    hub_entry = hass.config_entries.async_get_entry(hub_entry_id) if hub_entry_id else None
    if hub_entry is None:
        raise ServiceValidationError("Chore Tracker hub is not loaded")

    config = dict(call.data)
    person_id = config[CONF_ASSIGNED_PERSON]
    if person_id != "none" and hass.states.get(person_id) is None:
        raise ServiceValidationError(f"Person entity {person_id} not found")
    if config[CONF_RECURRENCE_TYPE] == RECURRENCE_TYPE_YEARLY:
        config[CONF_YEARLY_MONTH] = int(config[CONF_YEARLY_MONTH])
    if config[CONF_RECURRENCE_TYPE] == RECURRENCE_TYPE_MONTHLY and config.get(
        CONF_MONTHLY_MODE, MONTHLY_MODE_DAY_OF_MONTH
    ) not in {MONTHLY_MODE_DAY_OF_MONTH, MONTHLY_MODE_ORDINAL_WEEKDAY}:
        raise ServiceValidationError("Invalid monthly recurrence mode")

    if not RecurrenceEngine().validate_recurrence_config(config):
        raise ServiceValidationError("Invalid recurrence configuration")

    requested_date = coerce_date(config.get(CONF_FIRST_OCCURRENCE_DATE))
    if requested_date is None:
        requested_date = dt_util.now().date()
    if requested_date < dt_util.now().date():
        raise ServiceValidationError("The first due date cannot be in the past")
    normalized_date, _adjusted = normalize_first_occurrence_date(config, requested_date)
    config[CONF_FIRST_OCCURRENCE_DATE] = normalized_date.isoformat()

    hass.config_entries.async_add_subentry(
        hub_entry,
        ConfigSubentry(
            data=MappingProxyType(config),
            subentry_type=SUBENTRY_TYPE_CHORE,
            title=config[CONF_CHORE_NAME],
            unique_id=uuid4().hex,
        ),
    )


def _handle_list_my_chores(hass: HomeAssistant, call: ServiceCall) -> dict[str, Any]:
    """Return a stable, template-friendly list of chores assigned to a person."""
    coordinator = next(iter(hass.data.get(DOMAIN, {}).values()), None)
    if coordinator is None:
        raise ServiceValidationError("Chore Tracker hub is not loaded")

    person_id = call.data["person_id"]
    if not person_id.startswith("person."):
        raise ServiceValidationError("person_id must identify a Person entity")
    if hass.states.get(person_id) is None:
        raise ServiceValidationError(f"Person entity {person_id} not found")
    chores = coordinator.chore_data
    assigned = []
    for chore_id, chore_data in chores.items():
        config = chore_data["config"]
        if config.get(CONF_ASSIGNED_PERSON) != person_id:
            continue
        state = chore_data["state"]
        due_date = _parse_state_datetime(state.get("next_due_date"))
        assigned.append(
            {
                "chore_id": chore_id,
                "entity_id": coordinator.entity_id_for_chore(chore_id, config),
                "name": config[CONF_CHORE_NAME],
                "status": state.get("status"),
                "next_due_date": due_date.isoformat() if due_date else None,
                "days_until_due": (due_date.date() - dt_util.now().date()).days
                if due_date
                else None,
            }
        )
    return {"chores": assigned}
