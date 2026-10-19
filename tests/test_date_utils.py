"""Test the DateCalculator utility class."""

from datetime import date, datetime

import pytest

from custom_components.chore_tracker.date_utils import (
    WEEKDAY_MAP,
    DateCalculator,
    coerce_date,
    normalize_first_occurrence_date,
    nth_weekday_of_month,
)


class TestDateCalculator:
    """Test suite for DateCalculator utility class."""

    def setup_method(self):
        """Set up test instance."""
        self.calc = DateCalculator()

    # MONTH ADDITION TESTS
    def test_add_months_normal_case(self):
        """Test adding months with normal dates."""
        start_date = date(2024, 1, 15)
        result = self.calc.add_months_with_smart_day(start_date, 2, 15)
        expected = date(2024, 3, 15)
        assert result == expected

    def test_add_months_smart_day_february(self):
        """Test smart day handling when going to February."""
        # Jan 31 -> Feb 29 (leap year)
        start_date = date(2024, 1, 31)
        result = self.calc.add_months_with_smart_day(start_date, 1, 31)
        expected = date(2024, 2, 29)  # 2024 is leap year
        assert result == expected

        # Jan 31 -> Feb 28 (non-leap year)
        start_date = date(2023, 1, 31)
        result = self.calc.add_months_with_smart_day(start_date, 1, 31)
        expected = date(2023, 2, 28)  # 2023 is not leap year
        assert result == expected

    def test_add_months_smart_day_april(self):
        """Test smart day handling for months with 30 days."""
        # March 31 -> April 30
        start_date = date(2024, 3, 31)
        result = self.calc.add_months_with_smart_day(start_date, 1, 31)
        expected = date(2024, 4, 30)  # April only has 30 days
        assert result == expected

    def test_add_months_year_rollover(self):
        """Test adding months across year boundary."""
        start_date = date(2024, 11, 15)
        result = self.calc.add_months_with_smart_day(start_date, 3, 15)
        expected = date(2025, 2, 15)
        assert result == expected

    def test_add_months_multiple_years(self):
        """Test adding many months (multiple years)."""
        start_date = date(2024, 1, 15)
        result = self.calc.add_months_with_smart_day(start_date, 25, 15)  # 2 years + 1 month
        expected = date(2026, 2, 15)
        assert result == expected

    # WEEKDAY OCCURRENCE TESTS
    def test_next_weekday_occurrence_same_week(self):
        """Test finding next weekday in same week."""
        # Monday Jan 1, 2024, looking for Friday
        monday = date(2024, 1, 1)
        result = self.calc.next_weekday_occurrence(monday, [4])  # Friday
        expected = date(2024, 1, 5)  # Friday Jan 5
        assert result == expected

    def test_next_weekday_occurrence_next_week(self):
        """Test finding next weekday in following week."""
        # Friday Jan 5, 2024, looking for Monday
        friday = date(2024, 1, 5)
        result = self.calc.next_weekday_occurrence(friday, [0])  # Monday
        expected = date(2024, 1, 8)  # Monday Jan 8
        assert result == expected

    def test_next_weekday_occurrence_multiple_days(self):
        """Test finding next occurrence with multiple target days."""
        # Monday Jan 1, 2024, looking for Wednesday or Friday
        monday = date(2024, 1, 1)
        result = self.calc.next_weekday_occurrence(monday, [2, 4])  # Wed, Fri
        expected = date(2024, 1, 3)  # Wednesday Jan 3 (comes first)
        assert result == expected

        # Thursday Jan 4, looking for Wednesday or Friday
        thursday = date(2024, 1, 4)
        result = self.calc.next_weekday_occurrence(thursday, [2, 4])  # Wed, Fri
        expected = date(2024, 1, 5)  # Friday Jan 5 (next occurrence)
        assert result == expected

    def test_next_weekday_occurrence_empty_list(self):
        """Test handling of empty weekday list."""
        monday = date(2024, 1, 1)
        result = self.calc.next_weekday_occurrence(monday, [])
        expected = date(2024, 1, 2)  # Next day when no target weekdays
        assert result == expected

    # YEAR ADDITION TESTS
    def test_add_years_normal_case(self):
        """Test adding years with normal dates."""
        start_date = date(2024, 3, 15)
        result = self.calc.add_years_with_leap_day_logic(start_date, 2, 3, 15)
        expected = date(2026, 3, 15)
        assert result == expected

    def test_add_years_leap_day_to_leap_year(self):
        """Test leap day handling from leap year to leap year."""
        # Feb 29, 2024 -> Feb 29, 2028 (both leap years)
        start_date = date(2024, 2, 29)
        result = self.calc.add_years_with_leap_day_logic(start_date, 4, 2, 29)
        expected = date(2028, 2, 29)
        assert result == expected

    def test_add_years_leap_day_to_non_leap_year(self):
        """Test leap day handling from leap year to non-leap year."""
        # Feb 29, 2024 -> Feb 28, 2025 (leap to non-leap)
        start_date = date(2024, 2, 29)
        result = self.calc.add_years_with_leap_day_logic(start_date, 1, 2, 29)
        expected = date(2025, 2, 28)
        assert result == expected

    def test_add_years_different_target_date(self):
        """Test adding years with different target month/day."""
        # Jan 1, 2024 -> Dec 25, 2026
        start_date = date(2024, 1, 1)
        result = self.calc.add_years_with_leap_day_logic(start_date, 2, 12, 25)
        expected = date(2026, 12, 25)
        assert result == expected

    # INTERVAL UNIT TESTS
    def test_add_interval_units_days(self):
        """Test adding interval units - days."""
        start_date = date(2024, 1, 1)
        result = self.calc.add_interval_units(start_date, 10, "days")
        expected = date(2024, 1, 11)
        assert result == expected

    def test_add_interval_units_weeks(self):
        """Test adding interval units - weeks."""
        start_date = date(2024, 1, 1)
        result = self.calc.add_interval_units(start_date, 3, "weeks")
        expected = date(2024, 1, 22)
        assert result == expected

    def test_add_interval_units_months(self):
        """Test adding interval units - months."""
        start_date = date(2024, 1, 15)
        result = self.calc.add_interval_units(start_date, 6, "months")
        expected = date(2024, 7, 15)
        assert result == expected

    def test_add_interval_units_years(self):
        """Test adding interval units - years."""
        start_date = date(2024, 1, 1)
        result = self.calc.add_interval_units(start_date, 3, "years")
        expected = date(2027, 1, 1)
        assert result == expected

    def test_add_interval_units_invalid_unit(self):
        """Test handling of invalid interval unit."""
        start_date = date(2024, 1, 1)

        # Should raise ValueError for invalid unit
        with pytest.raises(ValueError, match="Invalid interval unit"):
            self.calc.add_interval_units(start_date, 5, "invalid")

    # EDGE CASE TESTS
    def test_month_edge_cases(self):
        """Test various month edge cases."""
        # Adding months across multiple years
        start_date = date(2024, 1, 31)
        result = self.calc.add_months_with_smart_day(start_date, 13, 31)  # 1 year + 1 month
        expected = date(2025, 2, 28)  # Feb 2025 (non-leap) -> 28th
        assert result == expected

        # Adding 0 months (should return next occurrence of target day)
        start_date = date(2024, 1, 15)
        result = self.calc.add_months_with_smart_day(start_date, 0, 20)
        expected = date(2024, 1, 20)  # Same month, day 20
        assert result == expected

    def test_weekday_map_completeness(self):
        """Test that WEEKDAY_MAP has all days."""
        expected_days = {
            "monday": 0,
            "tuesday": 1,
            "wednesday": 2,
            "thursday": 3,
            "friday": 4,
            "saturday": 5,
            "sunday": 6,
        }
        assert WEEKDAY_MAP == expected_days

    def test_leap_year_calculations(self):
        """Test leap year edge cases."""
        # Feb 29 -> March (no smart day needed)
        start_date = date(2024, 2, 29)
        result = self.calc.add_months_with_smart_day(start_date, 1, 15)
        expected = date(2024, 3, 15)
        assert result == expected

        # Leap year handling in year addition
        start_date = date(2020, 2, 29)  # Leap day
        result = self.calc.add_years_with_leap_day_logic(start_date, 8, 2, 29)  # 2028 is leap
        expected = date(2028, 2, 29)
        assert result == expected

    def test_year_boundary_edge_cases(self):
        """Test calculations across year boundaries."""
        # December to January
        start_date = date(2024, 12, 15)
        result = self.calc.add_months_with_smart_day(start_date, 2, 15)
        expected = date(2025, 2, 15)
        assert result == expected

        # Multiple year boundaries
        start_date = date(2024, 10, 31)
        result = self.calc.add_months_with_smart_day(start_date, 16, 31)  # 1 year 4 months
        expected = date(2026, 2, 28)  # Feb 2026 doesn't have 31st
        assert result == expected


class TestFirstOccurrenceHelpers:
    """Test first occurrence parsing and normalization helpers."""

    def test_coerce_date_accepts_date_datetime_and_iso(self):
        assert coerce_date(date(2026, 5, 1)) == date(2026, 5, 1)
        assert coerce_date(datetime(2026, 5, 1, 8, 0)) == date(2026, 5, 1)
        assert coerce_date("2026-05-01") == date(2026, 5, 1)

    def test_coerce_date_rejects_invalid_values(self):
        assert coerce_date("not-a-date") is None
        assert coerce_date(None) is None

    def test_normalize_weekly_rolls_forward(self):
        config = {
            "recurrence_type": "weekly",
            "weekly_days": ["monday"],
        }
        normalized, adjusted = normalize_first_occurrence_date(config, date(2026, 5, 5))
        assert normalized == date(2026, 5, 11)
        assert adjusted is True

    def test_normalize_monthly_uses_smart_day(self):
        config = {
            "recurrence_type": "monthly",
            "monthly_day": 31,
        }
        normalized, adjusted = normalize_first_occurrence_date(config, date(2026, 4, 1))
        assert normalized == date(2026, 4, 30)
        assert adjusted is True

    def test_nth_weekday_of_month_supports_last_and_missing_fifth(self):
        assert nth_weekday_of_month(2026, 5, "monday", "first") == date(2026, 5, 4)
        assert nth_weekday_of_month(2026, 5, "friday", "last") == date(2026, 5, 29)
        assert nth_weekday_of_month(2026, 2, "monday", "fifth") is None

    def test_normalize_monthly_ordinal_rolls_forward(self):
        config = {
            "recurrence_type": "monthly",
            "monthly_mode": "ordinal_weekday",
            "monthly_ordinal": "first",
            "monthly_weekday": "monday",
        }
        normalized, adjusted = normalize_first_occurrence_date(config, date(2026, 5, 1))
        assert normalized == date(2026, 5, 4)
        assert adjusted is True

    def test_normalize_monthly_fifth_weekday_skips_missing_month(self):
        config = {
            "recurrence_type": "monthly",
            "monthly_mode": "ordinal_weekday",
            "monthly_ordinal": "fifth",
            "monthly_weekday": "monday",
        }
        normalized, adjusted = normalize_first_occurrence_date(config, date(2024, 2, 1))
        assert normalized == date(2024, 4, 29)
        assert adjusted is True

    def test_normalize_yearly_rolls_to_target_date(self):
        config = {
            "recurrence_type": "yearly",
            "yearly_month": 12,
            "yearly_day": 25,
        }
        normalized, adjusted = normalize_first_occurrence_date(config, date(2026, 7, 10))
        assert normalized == date(2026, 12, 25)
        assert adjusted is True

    def test_normalize_interval_keeps_date(self):
        config = {
            "recurrence_type": "interval",
            "pattern_interval": 3,
            "interval_unit": "days",
        }
        normalized, adjusted = normalize_first_occurrence_date(config, date(2026, 5, 1))
        assert normalized == date(2026, 5, 1)
        assert adjusted is False
