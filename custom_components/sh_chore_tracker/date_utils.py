"""Date calculation utilities for SmartHass Chore Tracker."""

import calendar
from datetime import date, datetime, timedelta
from typing import Any, List, Mapping

from dateutil.relativedelta import relativedelta

from .const import (
    CONF_MONTHLY_DAY,
    CONF_MONTHLY_MODE,
    CONF_MONTHLY_ORDINAL,
    CONF_MONTHLY_WEEKDAY,
    MONTHLY_MODE_DAY_OF_MONTH,
    MONTHLY_MODE_ORDINAL_WEEKDAY,
    MONTHLY_ORDINAL_FIFTH,
    MONTHLY_ORDINAL_FIRST,
    MONTHLY_ORDINAL_FOURTH,
    MONTHLY_ORDINAL_LAST,
    MONTHLY_ORDINAL_SECOND,
    MONTHLY_ORDINAL_THIRD,
)


class DateCalculator:
    """Utility class for complex date arithmetic in chore recurrence patterns.

    Provides static methods for handling edge cases in date calculations,
    including month-end overflow, leap year logic, and weekday calculations.
    All methods operate on date objects only (no time components).
    """

    @staticmethod
    def add_months_with_smart_day(base_date: date, months: int, target_day: int) -> date:
        """Add months with smart last-day logic for monthly/yearly patterns.

        Args:
            base_date: Starting date
            months: Number of months to add
            target_day: Desired day of month (1-31)

        Returns:
            New date with smart day logic applied

        Example:
            add_months_with_smart_day(date(2025, 1, 31), 1, 31) -> date(2025, 2, 28)
        """
        # Calculate target month/year
        new_date = base_date + relativedelta(months=months)
        year, month = new_date.year, new_date.month

        # Handle monthly overflow (31st -> Feb 28th, etc.)
        last_day_of_month = calendar.monthrange(year, month)[1]
        actual_day = min(target_day, last_day_of_month)

        return date(year, month, actual_day)

    @staticmethod
    def next_weekday_occurrence(base_date: date, target_weekdays: List[int]) -> date:
        """Find next occurrence of target weekdays.

        Args:
            base_date: Starting date
            target_weekdays: List of weekday numbers (0=Monday, 6=Sunday)

        Returns:
            Next date that matches one of the target weekdays

        Example:
            next_weekday_occurrence(date(2025, 10, 13), [0, 4]) -> next Monday or Friday
        """
        if not target_weekdays:
            return base_date + timedelta(days=1)

        current_weekday = base_date.weekday()
        days_ahead = []

        # Calculate days until each target weekday
        for target_day in sorted(target_weekdays):
            days_until = (target_day - current_weekday) % 7
            if days_until == 0:
                days_until = 7  # Next week if today matches
            days_ahead.append(days_until)

        # Get the nearest future occurrence
        min_days = min(days_ahead)
        return base_date + timedelta(days=min_days)

    @staticmethod
    def add_years_with_leap_day_logic(
        base_date: date, years: int, target_month: int, target_day: int
    ) -> date:
        """Add years with leap day logic for yearly patterns.

        Args:
            base_date: Starting date
            years: Number of years to add
            target_month: Target month (1-12)
            target_day: Target day (1-31)

        Returns:
            New date with leap day logic applied

        Example:
            add_years_with_leap_day_logic(date(2024, 2, 29), 1, 2, 29) -> date(2025, 2, 28)
        """
        target_year = base_date.year + years

        # Handle leap day edge case
        if target_month == 2 and target_day == 29:
            # If target is Feb 29th but target year isn't leap year, use Feb 28th
            if not calendar.isleap(target_year):
                return date(target_year, 2, 28)

        # Handle other month overflow cases
        try:
            return date(target_year, target_month, target_day)
        except ValueError:
            # Day doesn't exist in target month, use last day of month
            last_day = calendar.monthrange(target_year, target_month)[1]
            return date(target_year, target_month, min(target_day, last_day))

    @staticmethod
    def add_interval_units(base_date: date, interval_value: int, interval_unit: str) -> date:
        """Add interval units (days/weeks/months/years) to a base date.

        Args:
            base_date: Starting date
            interval_value: Number of units to add
            interval_unit: Unit type ("days", "weeks", "months", "years")

        Returns:
            New date with interval added
        """
        if interval_unit == "days":
            return base_date + timedelta(days=interval_value)
        elif interval_unit == "weeks":
            return base_date + timedelta(weeks=interval_value)
        elif interval_unit == "months":
            return base_date + relativedelta(months=interval_value)
        elif interval_unit == "years":
            return base_date + relativedelta(years=interval_value)
        else:
            raise ValueError(f"Invalid interval unit: {interval_unit}")


# Weekday mapping for consistent weekday handling
WEEKDAY_MAP = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}

ORDINAL_INDEX_MAP = {
    MONTHLY_ORDINAL_FIRST: 1,
    MONTHLY_ORDINAL_SECOND: 2,
    MONTHLY_ORDINAL_THIRD: 3,
    MONTHLY_ORDINAL_FOURTH: 4,
    MONTHLY_ORDINAL_FIFTH: 5,
}


def nth_weekday_of_month(year: int, month: int, weekday_name: str, ordinal: str) -> date | None:
    """Return the nth weekday date in a month, or None if it does not exist."""
    weekday = WEEKDAY_MAP.get(str(weekday_name).lower())
    if weekday is None:
        return None

    matching_days = [
        day
        for day in calendar.Calendar(firstweekday=0).itermonthdates(year, month)
        if day.month == month and day.weekday() == weekday
    ]

    ordinal = str(ordinal).lower()
    if ordinal == MONTHLY_ORDINAL_LAST:
        return matching_days[-1] if matching_days else None

    index = ORDINAL_INDEX_MAP.get(ordinal)
    if index is None or len(matching_days) < index:
        return None

    return matching_days[index - 1]


def next_monthly_ordinal_occurrence(
    requested: date,
    weekday_name: str,
    ordinal: str,
) -> tuple[date, bool]:
    """Return the next date on or after requested matching a monthly ordinal rule."""
    candidate_year = requested.year
    candidate_month = requested.month

    while True:
        candidate = nth_weekday_of_month(candidate_year, candidate_month, weekday_name, ordinal)
        if candidate is not None and candidate >= requested:
            return candidate, candidate != requested

        next_month = date(candidate_year, candidate_month, 1) + relativedelta(months=1)
        candidate_year = next_month.year
        candidate_month = next_month.month


def coerce_date(value: date | datetime | str | None) -> date | None:
    """Parse date-like values from config flow/service input.

    Accepts date, datetime, or ISO strings and returns a date object.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None


def normalize_first_occurrence_date(
    config: Mapping[str, Any],
    requested: date,
) -> tuple[date, bool]:
    """Normalize first occurrence date to the next valid date for the recurrence rule.

    Returns the normalized date and whether an adjustment was applied.
    """
    recurrence_type = config.get("recurrence_type", "interval")

    if recurrence_type == "interval":
        return requested, False

    if recurrence_type == "weekly":
        weekly_days = config.get("weekly_days", ["monday"])
        if isinstance(weekly_days, str):
            weekly_days = [day.strip() for day in weekly_days.split(",")]

        target_weekdays = {
            WEEKDAY_MAP[day.lower()]
            for day in weekly_days
            if isinstance(day, str) and day.lower() in WEEKDAY_MAP
        }
        if not target_weekdays:
            target_weekdays = {0}

        if requested.weekday() in target_weekdays:
            return requested, False

        candidate = requested
        while candidate.weekday() not in target_weekdays:
            candidate += timedelta(days=1)
        return candidate, True

    if recurrence_type == "monthly":
        monthly_mode = config.get(CONF_MONTHLY_MODE, MONTHLY_MODE_DAY_OF_MONTH)
        if monthly_mode == MONTHLY_MODE_ORDINAL_WEEKDAY:
            monthly_ordinal = config.get(CONF_MONTHLY_ORDINAL, MONTHLY_ORDINAL_FIRST)
            monthly_weekday = config.get(CONF_MONTHLY_WEEKDAY, "monday")
            return next_monthly_ordinal_occurrence(requested, monthly_weekday, monthly_ordinal)

        monthly_day = int(config.get(CONF_MONTHLY_DAY, 1))
        monthly_day = max(1, min(31, monthly_day))

        candidate = requested
        calc = DateCalculator()
        while True:
            last_day = calendar.monthrange(candidate.year, candidate.month)[1]
            valid_day = min(monthly_day, last_day)
            current_month_candidate = date(candidate.year, candidate.month, valid_day)
            if current_month_candidate >= requested:
                return current_month_candidate, current_month_candidate != requested
            candidate = calc.add_months_with_smart_day(candidate, 1, monthly_day)

    if recurrence_type == "yearly":
        yearly_month = int(config.get("yearly_month", 1))
        yearly_day = int(config.get("yearly_day", 1))
        yearly_month = max(1, min(12, yearly_month))
        yearly_day = max(1, min(31, yearly_day))

        year = requested.year
        while True:
            last_day = calendar.monthrange(year, yearly_month)[1]
            valid_day = min(yearly_day, last_day)
            candidate = date(year, yearly_month, valid_day)
            if candidate >= requested:
                return candidate, candidate != requested
            year += 1

    return requested, False
