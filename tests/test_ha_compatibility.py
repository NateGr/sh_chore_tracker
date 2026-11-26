"""Tests for Home Assistant compatibility monitoring."""

import pytest

from scripts.check_ha_compatibility import check_installed, check_updates

REQUIREMENTS = "pytest-homeassistant-custom-component==0.13.375\n"


def test_minimum_requires_exact_homeassistant_version():
    check_installed("minimum", "2026.9.0", "2026.9.0")
    with pytest.raises(ValueError, match="expected 2026.9.0"):
        check_installed("minimum", "2026.9.0", "2026.10.4")


def test_latest_must_be_stable_and_not_older_than_minimum():
    check_installed("latest", "2026.9.0", "2026.10.4")
    with pytest.raises(ValueError, match="below"):
        check_installed("latest", "2026.9.0", "2026.8.0")
    with pytest.raises(ValueError, match="stable"):
        check_installed("latest", "2026.9.0", "2026.10.0b1")


def test_updates_match_latest_stable():
    check_updates(
        {"version": "2026.10.4"},
        {"version": "0.13.375", "requires_dist": ["homeassistant==2026.10.4"]},
        REQUIREMENTS,
    )


@pytest.mark.parametrize(
    ("homeassistant", "plugin", "requirements", "error"),
    [
        (
            {"version": "2026.11.3"},
            {"version": "0.13.375", "requires_dist": ["homeassistant==2026.10.4"]},
            REQUIREMENTS,
            "does not test the latest",
        ),
        (
            {"version": "2026.10.4"},
            {"version": "0.13.376", "requires_dist": ["homeassistant==2026.10.4"]},
            REQUIREMENTS,
            "not pinned",
        ),
        (
            {"version": "2026.10.4"},
            {"version": "0.13.375", "requires_dist": ["homeassistant==2026.11.0b1"]},
            REQUIREMENTS,
            "stable",
        ),
        (
            {"version": "2026.10.4"},
            {"version": "0.13.375", "requires_dist": []},
            REQUIREMENTS,
            "exactly one Home Assistant",
        ),
        (
            {"version": "2026.10.4"},
            {"version": "0.13.375", "requires_dist": ["homeassistant==2026.10.4"]},
            "",
            "pin exactly one fixture",
        ),
    ],
)
def test_updates_report_outdated_or_invalid_stacks(homeassistant, plugin, requirements, error):
    with pytest.raises(ValueError, match=error):
        check_updates(homeassistant, plugin, requirements)
