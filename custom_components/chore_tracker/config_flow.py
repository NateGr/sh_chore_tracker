"""Configuration flow for SmartHass Chore Tracker."""

from types import MappingProxyType
from typing import Any, Self
from uuid import uuid4

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigSubentryFlow
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
from homeassistant.util import dt as dt_util

from .const import (
    CONF_ASSIGNED_PERSON,
    CONF_CHORE_DESCRIPTION,
    CONF_CHORE_NAME,
    CONF_FIRST_OCCURRENCE_DATE,
    CONF_HUB_ENTRY,
    # Legacy constants for migration
    CONF_INTERVAL_DAYS,
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
    DOMAIN,
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
    SUBENTRY_TYPE_CHORE,
    WEEKDAYS,
)
from .date_utils import coerce_date, normalize_first_occurrence_date

_MONTH_OPTIONS = [str(month) for month in range(1, 13)]


class ChoreFlowMixin:
    """Shared multi-step flow logic for creating and editing a chore.

    Both `ChoreTrackerConfigFlow` (hub bootstrap) and `ChoreTrackerChoreSubentryFlow` (chore)
    collect the same fields across the same branching steps; only how each flow
    resolves default values and finishes (create vs. update an entry) differs.
    """

    _data: dict[str, Any]
    hass: Any

    def _defaults(self) -> dict[str, Any]:
        """Return the values to prefill the flow with (empty for create flow)."""
        return {}

    def _is_create_flow(self) -> bool:
        """Return True if this is the initial creation flow (vs. editing)."""
        raise NotImplementedError

    async def _async_finish_flow(self) -> FlowResult:
        """Persist the collected chore data and finish the flow."""
        raise NotImplementedError

    def _person_options(self) -> list[dict[str, str]]:
        """Build the list of assignable person selector options."""
        options = [{"value": "none", "label": "No assignment"}]
        hass = getattr(self, "hass", None)
        if hass is not None:
            for entity_id in hass.states.async_entity_ids("person"):
                state = hass.states.get(entity_id)
                friendly_name = state.attributes.get("friendly_name") if state is not None else None
                label = friendly_name if isinstance(friendly_name, str) else entity_id
                options.append({"value": entity_id, "label": label})
        return options

    def _merge_defaults(self, field: str, fallback: Any) -> Any:
        """Look up a field's current value: in-progress data, then entry defaults."""
        if field in self._data:
            return self._data[field]
        defaults = self._defaults()
        if CONF_INTERVAL_DAYS in defaults and field == CONF_PATTERN_INTERVAL:
            return defaults[CONF_INTERVAL_DAYS]
        return defaults.get(field, fallback)

    async def _show_basic_info(
        self, step_id: str, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 1: chore name, description, and assigned person."""
        if user_input is not None and CONF_CHORE_NAME in user_input:
            self._data.update(user_input)
            return await self.async_step_recurrence_type()

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_CHORE_NAME,
                    default=self._merge_defaults(CONF_CHORE_NAME, ""),
                ): selector.TextSelector(),
                vol.Optional(
                    CONF_CHORE_DESCRIPTION,
                    default=self._merge_defaults(CONF_CHORE_DESCRIPTION, ""),
                ): selector.TextSelector(selector.TextSelectorConfig(multiline=True)),
                vol.Optional(
                    CONF_ASSIGNED_PERSON,
                    default=self._merge_defaults(CONF_ASSIGNED_PERSON, "none"),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=self._person_options())
                ),
            }
        )
        return self.async_show_form(step_id=step_id, data_schema=schema)

    async def async_step_recurrence_type(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 2: pick which recurrence pattern this chore follows."""
        if user_input is not None:
            self._data.update(user_input)
            recurrence_type = user_input[CONF_RECURRENCE_TYPE]
            if recurrence_type == RECURRENCE_TYPE_WEEKLY:
                return await self.async_step_weekly_config()
            if recurrence_type == RECURRENCE_TYPE_MONTHLY:
                return await self.async_step_monthly_config()
            if recurrence_type == RECURRENCE_TYPE_YEARLY:
                return await self.async_step_yearly_config()
            return await self.async_step_interval_config()

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_RECURRENCE_TYPE,
                    default=self._merge_defaults(CONF_RECURRENCE_TYPE, RECURRENCE_TYPE_INTERVAL),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            RECURRENCE_TYPE_INTERVAL,
                            RECURRENCE_TYPE_WEEKLY,
                            RECURRENCE_TYPE_MONTHLY,
                            RECURRENCE_TYPE_YEARLY,
                        ],
                        translation_key="recurrence_type",
                    )
                ),
            }
        )
        return self.async_show_form(step_id="recurrence_type", data_schema=schema)

    async def async_step_interval_config(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 3a: interval recurrence fields (only shown for interval type)."""
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_first_occurrence()

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_PATTERN_INTERVAL,
                    default=self._merge_defaults(CONF_PATTERN_INTERVAL, 1),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1, max=999, mode=selector.NumberSelectorMode.BOX
                    )
                ),
                vol.Optional(
                    CONF_INTERVAL_UNIT,
                    default=self._merge_defaults(CONF_INTERVAL_UNIT, INTERVAL_UNIT_DAYS),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            INTERVAL_UNIT_DAYS,
                            INTERVAL_UNIT_WEEKS,
                            INTERVAL_UNIT_MONTHS,
                            INTERVAL_UNIT_YEARS,
                        ],
                        translation_key="interval_unit",
                    )
                ),
            }
        )
        return self.async_show_form(step_id="interval_config", data_schema=schema)

    async def async_step_weekly_config(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 3b: weekly recurrence fields (only shown for weekly type)."""
        errors: dict[str, str] = {}
        if user_input is not None:
            if not user_input.get(CONF_WEEKLY_DAYS):
                errors["base"] = "weekly_days_required"
            else:
                self._data.update(user_input)
                return await self.async_step_first_occurrence()

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_WEEKLY_DAYS,
                    default=self._merge_defaults(CONF_WEEKLY_DAYS, ["monday"]),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=WEEKDAYS, multiple=True, translation_key="weekday"
                    )
                ),
            }
        )
        return self.async_show_form(step_id="weekly_config", data_schema=schema, errors=errors)

    async def async_step_monthly_config(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 3c: choose day-of-month vs. ordinal-weekday monthly mode."""
        if user_input is not None:
            self._data.update(user_input)
            if user_input[CONF_MONTHLY_MODE] == MONTHLY_MODE_ORDINAL_WEEKDAY:
                return await self.async_step_monthly_ordinal_weekday()
            return await self.async_step_monthly_day_of_month()

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_MONTHLY_MODE,
                    default=self._merge_defaults(CONF_MONTHLY_MODE, MONTHLY_MODE_DAY_OF_MONTH),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            MONTHLY_MODE_DAY_OF_MONTH,
                            MONTHLY_MODE_ORDINAL_WEEKDAY,
                        ],
                        translation_key="monthly_mode",
                    )
                ),
            }
        )
        return self.async_show_form(step_id="monthly_config", data_schema=schema)

    async def async_step_monthly_day_of_month(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 3c-i: specific day-of-month sub-branch."""
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_first_occurrence()

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_MONTHLY_DAY,
                    default=self._merge_defaults(CONF_MONTHLY_DAY, 1),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1, max=31, mode=selector.NumberSelectorMode.BOX
                    )
                ),
            }
        )
        return self.async_show_form(step_id="monthly_day_of_month", data_schema=schema)

    async def async_step_monthly_ordinal_weekday(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 3c-ii: ordinal weekday sub-branch (e.g. 'first Monday')."""
        errors: dict[str, str] = {}
        if user_input is not None:
            if user_input.get(CONF_MONTHLY_ORDINAL) not in MONTHLY_ORDINALS:
                errors["base"] = "invalid_monthly_ordinal"
            else:
                self._data.update(user_input)
                return await self.async_step_first_occurrence()

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_MONTHLY_ORDINAL,
                    default=self._merge_defaults(CONF_MONTHLY_ORDINAL, "first"),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            *MONTHLY_ORDINALS,
                        ],
                        translation_key="monthly_ordinal",
                    )
                ),
                vol.Required(
                    CONF_MONTHLY_WEEKDAY,
                    default=self._merge_defaults(CONF_MONTHLY_WEEKDAY, "monday"),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=WEEKDAYS, translation_key="weekday")
                ),
            }
        )
        return self.async_show_form(
            step_id="monthly_ordinal_weekday", data_schema=schema, errors=errors
        )

    async def async_step_yearly_config(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 3d: yearly recurrence fields (only shown for yearly type)."""
        if user_input is not None:
            user_input[CONF_YEARLY_MONTH] = int(user_input[CONF_YEARLY_MONTH])
            self._data.update(user_input)
            return await self.async_step_first_occurrence()

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_YEARLY_MONTH,
                    default=str(self._merge_defaults(CONF_YEARLY_MONTH, 1)),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=_MONTH_OPTIONS, translation_key="month")
                ),
                vol.Required(
                    CONF_YEARLY_DAY,
                    default=self._merge_defaults(CONF_YEARLY_DAY, 1),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1, max=31, mode=selector.NumberSelectorMode.BOX
                    )
                ),
            }
        )
        return self.async_show_form(step_id="yearly_config", data_schema=schema)

    async def async_step_first_occurrence(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Final step: pick and validate the first occurrence date, then finish."""
        errors: dict[str, str] = {}
        if user_input is not None:
            first_occurrence = coerce_date(user_input.get(CONF_FIRST_OCCURRENCE_DATE))
            if first_occurrence is None:
                errors["base"] = "invalid_date"
            elif self._is_create_flow() and first_occurrence < dt_util.now().date():
                errors["base"] = "date_in_past"
            else:
                normalized_date, _adjusted = normalize_first_occurrence_date(
                    self._data, first_occurrence
                )
                self._data[CONF_FIRST_OCCURRENCE_DATE] = normalized_date.isoformat()
                return await self._async_finish_flow()

        default_date = (
            coerce_date(self._merge_defaults(CONF_FIRST_OCCURRENCE_DATE, None))
            or dt_util.now().date()
        )

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_FIRST_OCCURRENCE_DATE, default=default_date
                ): selector.DateSelector(),
            }
        )
        return self.async_show_form(step_id="first_occurrence", data_schema=schema, errors=errors)


class ChoreTrackerConfigFlow(ChoreFlowMixin, ConfigFlow, domain=DOMAIN):
    """Create the Chore Tracker hub and its first chore."""

    VERSION = CONFIG_ENTRY_VERSION

    def is_matching(self, other_flow: Self) -> bool:
        """Only one household hub setup flow can be active at a time."""
        return isinstance(other_flow, ChoreTrackerConfigFlow)

    def __init__(self) -> None:
        """Initialize the flow's in-progress chore data."""
        self._data: dict[str, Any] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Set up the single household hub."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        await self.async_set_unique_id(HUB_UNIQUE_ID)
        self._abort_if_unique_id_configured()
        return await self._show_basic_info("user", user_input)

    def _is_create_flow(self) -> bool:
        return True

    async def _async_finish_flow(self) -> FlowResult:
        return self.async_create_entry(
            title="Chore Tracker",
            data={CONF_HUB_ENTRY: True},
            subentries=[
                {
                    "subentry_type": SUBENTRY_TYPE_CHORE,
                    "title": self._data[CONF_CHORE_NAME],
                    "data": self._data,
                    "unique_id": uuid4().hex,
                }
            ],
        )

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        """Return the chore subentry flow supported by the hub."""
        return {SUBENTRY_TYPE_CHORE: ChoreTrackerChoreSubentryFlow}


class ChoreTrackerChoreSubentryFlow(ChoreFlowMixin, ConfigSubentryFlow):
    """Add or edit a chore under the household hub."""

    def __init__(self) -> None:
        """Initialize the flow's in-progress chore data."""
        self._data: dict[str, Any] = {}
        self._editing = False

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Start adding a chore to the hub."""
        return await self._show_basic_info("user", user_input)

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Start editing an existing chore subentry."""
        self._editing = True
        self._data = dict(self._get_reconfigure_subentry().data)
        return await self._show_basic_info("user", user_input)

    def _defaults(self) -> dict[str, Any]:
        if self._editing:
            return dict(self._get_reconfigure_subentry().data)
        return {}

    def _is_create_flow(self) -> bool:
        return not self._editing

    async def _async_finish_flow(self) -> FlowResult:
        if self._editing:
            self.hass.config_entries.async_update_subentry(
                entry=self._get_entry(),
                subentry=self._get_reconfigure_subentry(),
                title=self._data[CONF_CHORE_NAME],
                data=MappingProxyType(self._data),
            )
            return self.async_abort(reason="reconfigure_successful")
        return self.async_create_entry(
            title=self._data[CONF_CHORE_NAME],
            data=self._data,
            unique_id=uuid4().hex,
        )
