"""Constants for the Chore Tracker integration."""

DOMAIN = "sh_chore_tracker"
SUBENTRY_TYPE_CHORE = "chore"
SUBENTRY_TYPE_SUMMARY = "summary"
CONF_HUB_ENTRY = "is_hub_entry"
HUB_UNIQUE_ID = "household"
CONFIG_ENTRY_VERSION = 3

# Configuration constants
CONF_CHORE_NAME = "chore_name"
CONF_CHORE_DESCRIPTION = "chore_description"
CONF_RECURRENCE_TYPE = "recurrence_type"
CONF_PATTERN_INTERVAL = "pattern_interval"  # Unified frequency field
CONF_INTERVAL_UNIT = "interval_unit"  # For interval recurrence: days/weeks/months/years
CONF_ASSIGNED_PERSON = "assigned_person"

# Legacy constants (for migration compatibility)
CONF_INTERVAL_DAYS = "interval_days"

# Chore status values
CHORE_STATUS_PENDING = "pending"
CHORE_STATUS_DUE = "due"
CHORE_STATUS_COMPLETE = "complete"
CHORE_STATUS_OVERDUE = "overdue"
CHORE_STATUS_SNOOZED = "snoozed"
CHORE_STATUS_SKIPPED = "skipped"

# Recurrence types
RECURRENCE_TYPE_INTERVAL = "interval"
RECURRENCE_TYPE_WEEKLY = "weekly"
RECURRENCE_TYPE_MONTHLY = "monthly"
RECURRENCE_TYPE_YEARLY = "yearly"

# All-day event recurrence constants
CONF_WEEKLY_DAYS = "weekly_days"
CONF_MONTHLY_DAY = "monthly_day"
CONF_MONTHLY_MODE = "monthly_mode"
CONF_MONTHLY_ORDINAL = "monthly_ordinal"
CONF_MONTHLY_WEEKDAY = "monthly_weekday"
CONF_YEARLY_MONTH = "yearly_month"
CONF_YEARLY_DAY = "yearly_day"
CONF_FIRST_OCCURRENCE_DATE = "first_occurrence_date"

MONTHLY_MODE_DAY_OF_MONTH = "day_of_month"
MONTHLY_MODE_ORDINAL_WEEKDAY = "ordinal_weekday"

MONTHLY_ORDINAL_FIRST = "first"
MONTHLY_ORDINAL_SECOND = "second"
MONTHLY_ORDINAL_THIRD = "third"
MONTHLY_ORDINAL_FOURTH = "fourth"
MONTHLY_ORDINAL_FIFTH = "fifth"
MONTHLY_ORDINAL_LAST = "last"

MONTHLY_ORDINALS = [
    MONTHLY_ORDINAL_FIRST,
    MONTHLY_ORDINAL_SECOND,
    MONTHLY_ORDINAL_THIRD,
    MONTHLY_ORDINAL_FOURTH,
    MONTHLY_ORDINAL_FIFTH,
    MONTHLY_ORDINAL_LAST,
]

# Interval unit options
INTERVAL_UNIT_DAYS = "days"
INTERVAL_UNIT_WEEKS = "weeks"
INTERVAL_UNIT_MONTHS = "months"
INTERVAL_UNIT_YEARS = "years"

# Legacy constants (for migration compatibility)
RECURRENCE_TYPE_FIXED = "fixed"
CONF_FIXED_TIME = "fixed_time"

# Weekday constants (for weekly recurrence)
WEEKDAYS = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]

# Service names
SERVICE_COMPLETE_CHORE = "complete_chore"
SERVICE_UNDO_COMPLETE_CHORE = "undo_complete_chore"
SERVICE_SNOOZE_CHORE = "snooze_chore"
SERVICE_SKIP_CHORE = "skip_chore"
SERVICE_RESTORE_CHORE = "restore_chore"
SERVICE_REASSIGN_CHORE = "reassign_chore"
SERVICE_RESET_NEXT_DUE_DATE = "reset_next_due_date"
SERVICE_CREATE_CHORE = "create_chore"
SERVICE_LIST_MY_CHORES = "list_my_chores"

# Event names
EVENT_CHORE_COMPLETED = "sh_chore_tracker_chore_completed"
EVENT_CHORE_COMPLETE_UNDONE = "sh_chore_tracker_chore_complete_undone"
EVENT_CHORE_SNOOZED = "sh_chore_tracker_chore_snoozed"
EVENT_CHORE_SKIPPED = "sh_chore_tracker_chore_skipped"
EVENT_CHORE_RESTORED = "sh_chore_tracker_chore_restored"
EVENT_CHORE_REASSIGNED = "sh_chore_tracker_chore_reassigned"
EVENT_CHORE_OVERDUE = "sh_chore_tracker_chore_overdue"
EVENT_CHORE_SCHEDULE_RESET = "sh_chore_tracker_chore_schedule_reset"

# Default values
DEFAULT_SNOOZE_DAYS = 3
DEFAULT_RESTORE_WINDOW_HOURS = 24
