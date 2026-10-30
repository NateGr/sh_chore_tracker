"""Test the Chore Tracker config flow (multi-step device integration flow)."""

import json
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
import voluptuous as vol
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.util import dt as dt_util

from custom_components.sh_chore_tracker.config_flow import (
    ChoreTrackerChoreSubentryFlow,
    ChoreTrackerConfigFlow,
)
from custom_components.sh_chore_tracker.const import (
    CONF_ASSIGNED_PERSON,
    CONF_CHORE_DESCRIPTION,
    CONF_CHORE_NAME,
    CONF_FIRST_OCCURRENCE_DATE,
    CONF_HUB_ENTRY,
    CONF_INTERVAL_UNIT,
    CONF_MONTHLY_MODE,
    CONF_MONTHLY_ORDINAL,
    CONF_MONTHLY_WEEKDAY,
    CONF_PATTERN_INTERVAL,
    CONF_RECURRENCE_TYPE,
    CONF_WEEKLY_DAYS,
    INTERVAL_UNIT_DAYS,
    MONTHLY_MODE_DAY_OF_MONTH,
    MONTHLY_MODE_ORDINAL_WEEKDAY,
    RECURRENCE_TYPE_INTERVAL,
    RECURRENCE_TYPE_MONTHLY,
    RECURRENCE_TYPE_WEEKLY,
    RECURRENCE_TYPE_YEARLY,
    SUBENTRY_TYPE_CHORE,
)


@pytest.mark.parametrize("section", ["config", "config_subentries", "selector", "entity"])
def test_english_labels_match_translation_source(section: str) -> None:
    integration = Path(__file__).parents[1] / "custom_components/sh_chore_tracker"
    source = json.loads((integration / "strings.json").read_text())
    english = json.loads((integration / "translations/en.json").read_text())

    assert english[section] == source[section]


def test_subentry_translations_include_required_flow_sections() -> None:
    integration = Path(__file__).parents[1] / "custom_components/sh_chore_tracker"
    source = json.loads((integration / "strings.json").read_text())

    for translations in source["config_subentries"].values():
        assert translations["entry_type"]
        assert translations["initiate_flow"]["user"]
        assert isinstance(translations["step"], dict)

    # The automatic summary has labels but no user-facing configuration steps.
    assert source["config_subentries"]["summary"]["step"] == {}


@pytest.mark.parametrize("section", ["config", "chore"])
@pytest.mark.parametrize(
    ("step_id", "selector_fields"),
    [
        ("recurrence_type", ["recurrence_type"]),
        ("interval_config", ["interval_unit"]),
        ("weekly_config", ["weekly_days"]),
        ("monthly_config", ["monthly_mode"]),
        ("monthly_day_of_month", []),
        ("monthly_ordinal_weekday", ["monthly_ordinal", "monthly_weekday"]),
        ("yearly_config", ["yearly_month"]),
        ("first_occurrence", []),
    ],
)
@pytest.mark.asyncio
async def test_flow_fields_and_selector_options_are_translated(
    section: str, step_id: str, selector_fields: list[str]
) -> None:
    integration = Path(__file__).parents[1] / "custom_components/sh_chore_tracker"
    english = json.loads((integration / "translations/en.json").read_text())
    flow_class = {
        "config": ChoreTrackerConfigFlow,
        "chore": ChoreTrackerChoreSubentryFlow,
    }[section]
    flow = flow_class()
    flow.hass = _make_hass()
    result = await getattr(flow, f"async_step_{step_id}")()
    translations = {
        "config": english["config"],
        "chore": english["config_subentries"]["chore"],
    }[section]

    assert translations["step"][step_id]["title"]
    for field in result["data_schema"].schema:
        assert translations["step"][step_id]["data"][field.schema]

    fields = {field.schema: selector for field, selector in result["data_schema"].schema.items()}
    for field_name in selector_fields:
        selector = fields[field_name]
        options = english["selector"][selector.config["translation_key"]]["options"]
        assert set(options) == set(selector.config["options"])
        assert all(options.values())


def _schema_default(schema: vol.Schema, field_name: str):
    """Return default value configured for a schema field."""
    for key in schema.schema:
        if getattr(key, "schema", key) == field_name:
            return key.default()
    raise KeyError(field_name)


def _make_hass(persons=None):
    hass = MagicMock()
    hass.states.async_entity_ids.return_value = persons or [
        "person.alice",
        "person.bob",
    ]
    return hass


def _make_config_flow() -> ChoreTrackerConfigFlow:
    flow = ChoreTrackerConfigFlow()
    flow.hass = _make_hass()
    flow._async_current_entries = lambda: []
    flow.async_set_unique_id = AsyncMock()
    flow._abort_if_unique_id_configured = MagicMock()
    return flow


def _make_subentry_flow(monkeypatch, defaults: dict | None = None) -> ChoreTrackerChoreSubentryFlow:
    flow = ChoreTrackerChoreSubentryFlow()
    flow.hass = _make_hass()
    flow._editing = True
    monkeypatch.setattr(flow, "_defaults", lambda: dict(defaults or {}))
    return flow


class TestBasicInfoStep:
    """Step 1: chore_name, chore_description, assigned_person."""

    @pytest.mark.asyncio
    async def test_existing_hub_abort_has_english_message(self) -> None:
        flow = _make_config_flow()
        flow._async_current_entries = lambda: [MagicMock()]
        integration = Path(__file__).parents[1] / "custom_components/sh_chore_tracker"
        english = json.loads((integration / "translations/en.json").read_text())

        result = await flow.async_step_user()

        assert result["type"] == FlowResultType.ABORT
        assert result["reason"] == "single_instance_allowed"
        assert english["config"]["abort"][result["reason"]] == (
            "Only one Chore Tracker hub is allowed. Add new chores to your existing hub."
        )

    @pytest.mark.asyncio
    async def test_user_step_shows_form_with_person_options(self):
        flow = _make_config_flow()
        result = await flow.async_step_user()

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "user"
        assert CONF_CHORE_NAME in result["data_schema"].schema
        assert CONF_ASSIGNED_PERSON in result["data_schema"].schema

    def test_person_options_show_friendly_names_and_keep_entity_ids(self):
        flow = _make_config_flow()
        flow.hass.states.get.side_effect = [
            SimpleNamespace(attributes={"friendly_name": "Alice Smith"}),
            None,
        ]

        assert flow._person_options() == [
            {"value": "none", "label": "No assignment"},
            {"value": "person.alice", "label": "Alice Smith"},
            {"value": "person.bob", "label": "person.bob"},
        ]

    @pytest.mark.asyncio
    async def test_user_step_advances_to_recurrence_type(self):
        flow = _make_config_flow()
        result = await flow.async_step_user(
            {
                CONF_CHORE_NAME: "Take out trash",
                CONF_CHORE_DESCRIPTION: "",
                CONF_ASSIGNED_PERSON: "none",
            }
        )

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "recurrence_type"
        assert flow._data[CONF_CHORE_NAME] == "Take out trash"

    @pytest.mark.asyncio
    async def test_unrelated_input_redisplays_basic_info(self):
        """Unrelated input does not advance the chore setup flow."""
        flow = _make_config_flow()
        result = await flow.async_step_user({"entity_id": "sensor.chore_test"})

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "user"


class TestRecurrenceTypeBranching:
    """Step 2 routes to the recurrence-specific step for the chosen type."""

    @pytest.mark.asyncio
    async def test_interval_branch(self):
        flow = _make_config_flow()
        result = await flow.async_step_recurrence_type(
            {CONF_RECURRENCE_TYPE: RECURRENCE_TYPE_INTERVAL}
        )
        assert result["step_id"] == "interval_config"

    @pytest.mark.asyncio
    async def test_weekly_branch(self):
        flow = _make_config_flow()
        result = await flow.async_step_recurrence_type(
            {CONF_RECURRENCE_TYPE: RECURRENCE_TYPE_WEEKLY}
        )
        assert result["step_id"] == "weekly_config"

    @pytest.mark.asyncio
    async def test_monthly_branch(self):
        flow = _make_config_flow()
        result = await flow.async_step_recurrence_type(
            {CONF_RECURRENCE_TYPE: RECURRENCE_TYPE_MONTHLY}
        )
        assert result["step_id"] == "monthly_config"

    @pytest.mark.asyncio
    async def test_yearly_branch(self):
        flow = _make_config_flow()
        result = await flow.async_step_recurrence_type(
            {CONF_RECURRENCE_TYPE: RECURRENCE_TYPE_YEARLY}
        )
        assert result["step_id"] == "yearly_config"


class TestMonthlySubBranch:
    """Step 3c splits further into day-of-month vs. ordinal-weekday."""

    @pytest.mark.asyncio
    async def test_day_of_month_sub_branch(self):
        flow = _make_config_flow()
        result = await flow.async_step_monthly_config(
            {CONF_MONTHLY_MODE: MONTHLY_MODE_DAY_OF_MONTH}
        )
        assert result["step_id"] == "monthly_day_of_month"

    @pytest.mark.asyncio
    async def test_ordinal_weekday_sub_branch(self):
        flow = _make_config_flow()
        result = await flow.async_step_monthly_config(
            {CONF_MONTHLY_MODE: MONTHLY_MODE_ORDINAL_WEEKDAY}
        )
        assert result["step_id"] == "monthly_ordinal_weekday"

    @pytest.mark.asyncio
    async def test_ordinal_weekday_invalid_ordinal_shows_error(self):
        flow = _make_config_flow()
        result = await flow.async_step_monthly_ordinal_weekday(
            {CONF_MONTHLY_ORDINAL: "invalid", CONF_MONTHLY_WEEKDAY: "monday"}
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "monthly_ordinal_weekday"
        assert result["errors"]["base"] == "invalid_monthly_ordinal"

    @pytest.mark.asyncio
    async def test_ordinal_weekday_valid_advances_to_first_occurrence(self):
        flow = _make_config_flow()
        result = await flow.async_step_monthly_ordinal_weekday(
            {CONF_MONTHLY_ORDINAL: "first", CONF_MONTHLY_WEEKDAY: "monday"}
        )
        assert result["step_id"] == "first_occurrence"


class TestWeeklyValidation:
    @pytest.mark.asyncio
    async def test_weekly_requires_at_least_one_day(self):
        flow = _make_config_flow()
        result = await flow.async_step_weekly_config({CONF_WEEKLY_DAYS: []})

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "weekly_config"
        assert result["errors"]["base"] == "weekly_days_required"

    @pytest.mark.asyncio
    async def test_weekly_valid_days_advances(self):
        flow = _make_config_flow()
        result = await flow.async_step_weekly_config({CONF_WEEKLY_DAYS: ["monday", "friday"]})
        assert result["step_id"] == "first_occurrence"


class TestFirstOccurrenceStep:
    """Final step: validate and normalize the first occurrence date, then finish."""

    @pytest.mark.asyncio
    async def test_rejects_past_date_on_create(self):
        flow = _make_config_flow()
        flow._data.update(
            {
                CONF_CHORE_NAME: "Test",
                CONF_RECURRENCE_TYPE: RECURRENCE_TYPE_INTERVAL,
                CONF_PATTERN_INTERVAL: 1,
                CONF_INTERVAL_UNIT: INTERVAL_UNIT_DAYS,
            }
        )
        result = await flow.async_step_first_occurrence({CONF_FIRST_OCCURRENCE_DATE: "2000-01-01"})

        assert result["type"] == FlowResultType.FORM
        assert result["errors"]["base"] == "date_in_past"

    @pytest.mark.asyncio
    async def test_rejects_invalid_date(self):
        flow = _make_config_flow()
        flow._data.update(
            {
                CONF_CHORE_NAME: "Test",
                CONF_RECURRENCE_TYPE: RECURRENCE_TYPE_INTERVAL,
            }
        )
        result = await flow.async_step_first_occurrence({CONF_FIRST_OCCURRENCE_DATE: "not-a-date"})

        assert result["errors"]["base"] == "invalid_date"

    @pytest.mark.asyncio
    async def test_valid_date_creates_entry(self):
        flow = _make_config_flow()
        flow._data.update(
            {
                CONF_CHORE_NAME: "Test",
                CONF_RECURRENCE_TYPE: RECURRENCE_TYPE_INTERVAL,
                CONF_PATTERN_INTERVAL: 1,
                CONF_INTERVAL_UNIT: INTERVAL_UNIT_DAYS,
            }
        )
        today = dt_util.now().date().isoformat()
        result = await flow.async_step_first_occurrence({CONF_FIRST_OCCURRENCE_DATE: today})

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["title"] == "Chore Tracker"
        assert result["data"][CONF_HUB_ENTRY] is True
        assert result["subentries"][0]["subentry_type"] == SUBENTRY_TYPE_CHORE
        assert result["subentries"][0]["data"][CONF_FIRST_OCCURRENCE_DATE] == today

    @pytest.mark.asyncio
    async def test_weekly_date_is_normalized_to_target_weekday(self):
        flow = _make_config_flow()
        flow._data.update(
            {
                CONF_CHORE_NAME: "Test",
                CONF_RECURRENCE_TYPE: RECURRENCE_TYPE_WEEKLY,
                CONF_WEEKLY_DAYS: ["friday"],
            }
        )
        # Pick a date that is not a Friday; the flow should roll it forward.
        monday = dt_util.now().date()
        while monday.weekday() != 0:  # Monday
            monday += timedelta(days=1)

        result = await flow.async_step_first_occurrence(
            {CONF_FIRST_OCCURRENCE_DATE: monday.isoformat()}
        )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        normalized = date.fromisoformat(result["subentries"][0]["data"][CONF_FIRST_OCCURRENCE_DATE])
        assert normalized.weekday() == 4  # Friday
        assert normalized >= monday


class TestChoreTrackerConfigFlowClass:
    def test_version_is_3(self):
        assert ChoreTrackerConfigFlow.VERSION == 3

    def test_registers_chore_subentry_flow(self):
        entry = MagicMock()
        subentry_types = ChoreTrackerConfigFlow.async_get_supported_subentry_types(entry)
        assert subentry_types == {SUBENTRY_TYPE_CHORE: ChoreTrackerChoreSubentryFlow}


class TestChoreSubentryFlow:
    """Editing an existing chore mirrors the hub's create flow."""

    @pytest.mark.asyncio
    async def test_edit_flow_prefills_from_existing_options(self, monkeypatch):
        flow = _make_subentry_flow(
            monkeypatch,
            defaults={
                CONF_CHORE_NAME: "Existing Chore",
                CONF_ASSIGNED_PERSON: "person.alice",
            },
        )
        result = await flow._show_basic_info("user")

        assert result["step_id"] == "user"
        assert _schema_default(result["data_schema"], CONF_CHORE_NAME) == "Existing Chore"
        assert _schema_default(result["data_schema"], CONF_ASSIGNED_PERSON) == "person.alice"

    @pytest.mark.asyncio
    async def test_edit_flow_allows_past_first_occurrence(self, monkeypatch):
        flow = _make_subentry_flow(monkeypatch, defaults={})
        flow._data.update(
            {
                CONF_CHORE_NAME: "Test",
                CONF_RECURRENCE_TYPE: RECURRENCE_TYPE_INTERVAL,
                CONF_PATTERN_INTERVAL: 1,
                CONF_INTERVAL_UNIT: INTERVAL_UNIT_DAYS,
            }
        )
        flow._async_finish_flow = AsyncMock(return_value={"type": FlowResultType.CREATE_ENTRY})
        result = await flow.async_step_first_occurrence({CONF_FIRST_OCCURRENCE_DATE: "2000-01-01"})

        assert result["type"] == FlowResultType.CREATE_ENTRY

    @pytest.mark.asyncio
    async def test_edit_flow_updates_subentry_and_aborts(self, monkeypatch):
        flow = _make_subentry_flow(monkeypatch, defaults={})
        flow._data.update({CONF_CHORE_NAME: "Test"})
        entry = MagicMock()
        subentry = MagicMock()
        flow._get_entry = MagicMock(return_value=entry)
        flow._get_reconfigure_subentry = MagicMock(return_value=subentry)
        flow.async_abort = MagicMock(return_value={"type": FlowResultType.ABORT})
        result = await flow._async_finish_flow()

        assert result["type"] == FlowResultType.ABORT
        flow.hass.config_entries.async_update_subentry.assert_called_once_with(
            entry=entry,
            subentry=subentry,
            title="Test",
            data=flow._data,
        )
        flow.async_abort.assert_called_once_with(reason="reconfigure_successful")
