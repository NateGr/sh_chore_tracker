"""Tests for chore tracker service handlers (Stories 2.2, 2.3, 2.6)."""

import re
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import unquote, urlsplit

import pytest
import pytest_asyncio
import yaml
from homeassistant.core import Context, HomeAssistant, SupportsResponse
from homeassistant.exceptions import ServiceValidationError, Unauthorized
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.selector import EntitySelector
from homeassistant.util import dt as dt_util
from homeassistant.util.yaml import load_yaml

from custom_components.sh_chore_tracker import (
    ChoreCoordinator,
    _complete_chore_handler,
    _find_chore_data,
    _handle_create_chore,
    _handle_list_my_chores,
    _handle_service_call,
    _reassign_chore_handler,
    _reset_next_due_date_handler,
    _restore_chore_handler,
    _skip_chore_handler,
    _snooze_chore_handler,
    _undo_complete_chore_handler,
    async_setup_services,
)
from custom_components.sh_chore_tracker.const import (
    CHORE_STATUS_COMPLETE,
    CHORE_STATUS_PENDING,
    CHORE_STATUS_SKIPPED,
    CHORE_STATUS_SNOOZED,
    DEFAULT_RESTORE_WINDOW_HOURS,
    DEFAULT_SNOOZE_DAYS,
    DOMAIN,
    EVENT_CHORE_COMPLETE_UNDONE,
    EVENT_CHORE_COMPLETED,
    EVENT_CHORE_REASSIGNED,
    EVENT_CHORE_RESTORED,
    EVENT_CHORE_SCHEDULE_RESET,
    EVENT_CHORE_SKIPPED,
    EVENT_CHORE_SNOOZED,
)


@pytest.mark.parametrize(
    "action",
    [
        "complete_chore",
        "undo_complete_chore",
        "snooze_chore",
        "skip_chore",
        "restore_chore",
        "reassign_chore",
        "reset_next_due_date",
    ],
)
def test_chore_action_selectors_filter_by_device_model(action: str) -> None:
    services = load_yaml(
        str(Path(__file__).parents[1] / "custom_components/sh_chore_tracker/services.yaml")
    )
    selector = EntitySelector(services[action]["fields"]["entity_id"]["selector"]["entity"])

    assert selector.config["filter"] == [
        {"domain": ["sensor"], "integration": DOMAIN, "device": {"model": "chore"}}
    ]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_coordinator(hass, initial_state=None):
    """Build a minimal ChoreCoordinator mock."""
    coordinator = MagicMock(spec=ChoreCoordinator)
    coordinator.async_request_refresh = AsyncMock()
    coordinator.async_save_state = AsyncMock()
    state = {
        "status": CHORE_STATUS_PENDING,
        "completion_count": 0,
        "snooze_count": 0,
        "last_completed_date": None,
        "snooze_until": None,
        "snooze_reason": None,
        "next_due_date": datetime(2024, 1, 10),
    }
    if initial_state:
        state.update(initial_state)
    coordinator._chore_data = {
        "config": {
            "recurrence_type": "interval",
            "pattern_interval": 7,
            "interval_unit": "days",
        },
        "state": state,
    }
    coordinator.chore_id_for_subentry.return_value = "chore_1"
    coordinator.get_chore_data.return_value = coordinator._chore_data
    return coordinator


def _make_chore_data(coordinator):
    return coordinator._chore_data


def _assert_same_instant(actual: datetime, expected: datetime) -> None:
    """Assert datetime equality while tolerating naive vs aware test inputs."""
    if actual.tzinfo is not None and expected.tzinfo is None:
        expected = expected.replace(tzinfo=actual.tzinfo)
    elif actual.tzinfo is None and expected.tzinfo is not None:
        actual = actual.replace(tzinfo=expected.tzinfo)
    assert actual == expected


@pytest_asyncio.fixture
async def registered_hass(tmp_path):
    hass = HomeAssistant(str(tmp_path))
    hass.config_entries = MagicMock()
    hass.auth = MagicMock()
    hass.auth.async_get_user = AsyncMock(return_value=MagicMock(is_admin=False))
    hass.states.async_set("person.alice", "home")
    coordinator = MagicMock(spec=ChoreCoordinator)
    coordinator.chore_data = {
        "chore_1": {
            "config": {"chore_name": "Test", "assigned_person": "person.alice"},
            "state": {"status": "pending", "next_due_date": datetime(2026, 11, 1)},
        }
    }
    coordinator.entity_id_for_chore.return_value = "sensor.renamed_task"
    hass.data[DOMAIN] = {"hub_1": coordinator}
    await async_setup_services(hass)
    yield hass
    await hass.async_block_till_done()


@pytest.mark.asyncio
async def test_registers_all_documented_services(registered_hass):
    services = load_yaml(
        str(Path(__file__).parents[1] / "custom_components/sh_chore_tracker/services.yaml")
    )
    assert set(registered_hass.services.async_services()[DOMAIN]) == set(services)
    assert len(services) == 9
    assert (
        registered_hass.services.supports_response(DOMAIN, "list_my_chores")
        == SupportsResponse.ONLY
    )
    await async_setup_services(registered_hass)
    assert len(registered_hass.services.async_services()[DOMAIN]) == 9


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "action",
    [
        "complete_chore",
        "undo_complete_chore",
        "snooze_chore",
        "skip_chore",
        "restore_chore",
        "reassign_chore",
        "reset_next_due_date",
    ],
)
async def test_registered_chore_actions_require_entity(registered_hass, action):
    with pytest.raises(cv.vol.Invalid):
        await registered_hass.services.async_call(DOMAIN, action, {}, blocking=True)


@pytest.mark.asyncio
@pytest.mark.parametrize("days", [0, 366, "invalid"])
async def test_registered_snooze_rejects_invalid_duration(registered_hass, days):
    with pytest.raises(cv.vol.Invalid):
        await registered_hass.services.async_call(
            DOMAIN, "snooze_chore", {"entity_id": "sensor.test", "days": days}, blocking=True
        )


@pytest.mark.asyncio
async def test_registered_reset_rejects_replacement_date(registered_hass):
    with pytest.raises(cv.vol.Invalid):
        await registered_hass.services.async_call(
            DOMAIN,
            "reset_next_due_date",
            {"entity_id": "sensor.test", "date": "2026-11-01"},
            blocking=True,
        )


@pytest.mark.asyncio
async def test_registered_create_requires_admin(registered_hass):
    with pytest.raises(Unauthorized):
        await registered_hass.services.async_call(
            DOMAIN,
            "create_chore",
            {"chore_name": "Test"},
            blocking=True,
            context=Context(user_id="non_admin"),
        )
    registered_hass.config_entries.async_add_subentry.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("assigned_person", ["none", "person.alice"])
async def test_registered_create_applies_defaults(registered_hass, assigned_person):
    await registered_hass.services.async_call(
        DOMAIN,
        "create_chore",
        {"chore_name": "Test", "assigned_person": assigned_person},
        blocking=True,
    )
    subentry = registered_hass.config_entries.async_add_subentry.call_args.args[1]
    assert subentry.data["recurrence_type"] == "interval"
    assert subentry.data["pattern_interval"] == 1
    assert subentry.data["interval_unit"] == "days"
    assert subentry.data["assigned_person"] == assigned_person
    assert date.fromisoformat(subentry.data["first_occurrence_date"]) == dt_util.now().date()


@pytest.mark.asyncio
async def test_registered_listing_returns_captured_response(registered_hass):
    response = await registered_hass.services.async_call(
        DOMAIN, "list_my_chores", {"person_id": "person.alice"}, blocking=True, return_response=True
    )
    assert set(response) == {"chores"}
    assert set(response["chores"][0]) == {
        "chore_id",
        "entity_id",
        "name",
        "status",
        "next_due_date",
        "days_until_due",
    }
    assert response["chores"][0]["entity_id"] == "sensor.renamed_task"
    with pytest.raises(ServiceValidationError, match="response"):
        await registered_hass.services.async_call(
            DOMAIN, "list_my_chores", {"person_id": "person.alice"}, blocking=True
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("action", "handler_name"),
    [
        ("complete_chore", "_complete_chore_handler"),
        ("undo_complete_chore", "_undo_complete_chore_handler"),
        ("snooze_chore", "_snooze_chore_handler"),
        ("skip_chore", "_skip_chore_handler"),
        ("restore_chore", "_restore_chore_handler"),
        ("reassign_chore", "_reassign_chore_handler"),
        ("reset_next_due_date", "_reset_next_due_date_handler"),
    ],
)
async def test_registered_actions_dispatch_validated_bulk_input(
    registered_hass, action, handler_name
):
    coordinator = _make_coordinator(registered_hass)
    data = {"entity_id": ["sensor.renamed_task", "sensor.other_task"]}
    if action == "reassign_chore":
        data["person_id"] = "person.alice"
    with (
        patch(
            "custom_components.sh_chore_tracker._find_chore_data",
            AsyncMock(return_value=(coordinator, coordinator._chore_data)),
        ),
        patch(f"custom_components.sh_chore_tracker.{handler_name}", AsyncMock()) as handler,
    ):
        await registered_hass.services.async_call(DOMAIN, action, data, blocking=True)
    assert handler.await_count == 2
    assert [call.args[3] for call in handler.await_args_list] == data["entity_id"]
    if action == "snooze_chore":
        assert handler.await_args.args[4]["days"] == 3


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "schedule",
    [
        {"recurrence_type": "weekly", "pattern_interval": 53},
        {"recurrence_type": "monthly", "pattern_interval": 61},
        {"recurrence_type": "yearly", "pattern_interval": 11},
        {"interval_unit": "weeks", "pattern_interval": 61},
        {"interval_unit": "years", "pattern_interval": 11},
    ],
)
async def test_registered_create_enforces_recurrence_limits(registered_hass, schedule):
    with pytest.raises(ServiceValidationError, match="recurrence"):
        await registered_hass.services.async_call(
            DOMAIN, "create_chore", {"chore_name": "Test", **schedule}, blocking=True
        )
    registered_hass.config_entries.async_add_subentry.assert_not_called()


def _documentation_yaml(relative):
    text = (Path(__file__).parents[1] / relative).read_text(encoding="utf-8")
    return [
        yaml.safe_load(block) for block in re.findall(r"^```yaml\n(.*?)^```", text, re.M | re.S)
    ]


def _document_nodes(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _document_nodes(child)
    elif isinstance(value, list):
        for child in value:
            yield from _document_nodes(child)


@pytest.mark.parametrize(
    "relative", ["README.md", "docs/configuration-reference.md", "docs/service-reference.md"]
)
def test_active_yaml_examples_parse_and_use_current_state_contract(relative):
    examples = _documentation_yaml(relative)
    assert examples
    for example in examples:
        for node in _document_nodes(example):
            if isinstance(node.get("entity_id"), str) and node.get("condition") == "state":
                if node["entity_id"].startswith("sensor.chore_"):
                    assert node.get("attribute") == "status" or node.get("state") not in {
                        "pending",
                        "due",
                        "overdue",
                        "complete",
                        "snoozed",
                        "skipped",
                    }
            if node.get("type") == "custom:auto-entities":
                assert "sort" in node
                assert "sort" not in node["filter"]
                for include in node["filter"]["include"]:
                    assert "attribute" not in include
                    assert include["attributes"]["integration_domain"] == DOMAIN


@pytest.mark.asyncio
async def test_documented_service_data_matches_registered_schemas(registered_hass):
    registrations = registered_hass.services.async_services()[DOMAIN]
    for relative in ("README.md", "docs/service-reference.md"):
        for example in _documentation_yaml(relative):
            for node in _document_nodes(example):
                action = node.get("service", node.get("action"))
                if not isinstance(action, str) or not action.startswith(f"{DOMAIN}."):
                    continue
                service = action.split(".", 1)[1]
                data = node.get("data", {})
                if "{{" not in str(data):
                    registrations[service].schema(data)
                if service == "list_my_chores":
                    assert node.get("response_variable")


@pytest.mark.parametrize(
    "relative",
    [
        "README.md",
        "CONTRIBUTING.md",
        "docs/configuration-reference.md",
        "docs/service-reference.md",
        "docs/maintainer.md",
        ".github/SECURITY.md",
        ".github/pull_request_template.md",
    ],
)
def test_active_documentation_local_links_exist(relative):
    document = Path(__file__).parents[1] / relative
    for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", document.read_text(encoding="utf-8")):
        url = urlsplit(target)
        if not url.scheme and url.path:
            assert (document.parent / unquote(url.path)).exists(), target


# ---------------------------------------------------------------------------
# Story 2.2 — Mark Complete
# ---------------------------------------------------------------------------


class TestCompleteChoreHandler:
    """Tests for _complete_chore_handler (Story 2.2)."""

    @pytest.mark.asyncio
    async def test_status_transitions_to_complete(self):
        hass = MagicMock()
        hass.bus.async_fire = MagicMock()
        coordinator = _make_coordinator(hass)
        chore_data = _make_chore_data(coordinator)

        await _complete_chore_handler(hass, coordinator, chore_data, "sensor.test", {})

        assert chore_data["state"]["status"] == CHORE_STATUS_COMPLETE

    @pytest.mark.asyncio
    async def test_completion_count_increments(self):
        hass = MagicMock()
        hass.bus.async_fire = MagicMock()
        coordinator = _make_coordinator(hass, {"completion_count": 3})
        chore_data = _make_chore_data(coordinator)

        await _complete_chore_handler(hass, coordinator, chore_data, "sensor.test", {})

        assert chore_data["state"]["completion_count"] == 4

    @pytest.mark.asyncio
    async def test_next_due_date_advanced(self):
        """Completing a 7-day-interval chore should advance next_due_date by 7 days."""
        hass = MagicMock()
        hass.bus.async_fire = MagicMock()
        completion_date = datetime(2024, 1, 5)
        coordinator = _make_coordinator(hass)
        chore_data = _make_chore_data(coordinator)

        await _complete_chore_handler(
            hass,
            coordinator,
            chore_data,
            "sensor.test",
            {"completion_date": completion_date},
        )

        expected = datetime(2024, 1, 12)  # 7 days after completion_date
        _assert_same_instant(chore_data["state"]["next_due_date"], expected)

    @pytest.mark.asyncio
    async def test_last_completed_date_recorded(self):
        hass = MagicMock()
        hass.bus.async_fire = MagicMock()
        completion_date = datetime(2024, 1, 5)
        coordinator = _make_coordinator(hass)
        chore_data = _make_chore_data(coordinator)

        await _complete_chore_handler(
            hass,
            coordinator,
            chore_data,
            "sensor.test",
            {"completion_date": completion_date},
        )

        _assert_same_instant(chore_data["state"]["last_completed_date"], completion_date)

    @pytest.mark.asyncio
    async def test_snooze_cleared_on_completion(self):
        hass = MagicMock()
        hass.bus.async_fire = MagicMock()
        coordinator = _make_coordinator(
            hass,
            {
                "snooze_until": datetime(2024, 1, 8),
                "snooze_count": 2,
            },
        )
        chore_data = _make_chore_data(coordinator)

        await _complete_chore_handler(hass, coordinator, chore_data, "sensor.test", {})

        assert chore_data["state"]["snooze_until"] is None
        assert chore_data["state"]["snooze_count"] == 0

    @pytest.mark.asyncio
    async def test_state_persisted_before_refresh(self):
        """async_save_state must be called before async_request_refresh."""
        call_order = []
        hass = MagicMock()
        hass.bus.async_fire = MagicMock()
        coordinator = _make_coordinator(hass)

        async def record_save():
            call_order.append("save")

        async def record_refresh():
            call_order.append("refresh")

        coordinator.async_save_state = record_save
        coordinator.async_request_refresh = record_refresh

        chore_data = _make_chore_data(coordinator)
        await _complete_chore_handler(hass, coordinator, chore_data, "sensor.test", {})

        assert call_order == ["save", "refresh"]

    @pytest.mark.asyncio
    async def test_event_fired_with_correct_key(self):
        """Event must use 'completed_at' not 'completion_date'."""
        hass = MagicMock()
        hass.bus.async_fire = MagicMock()
        coordinator = _make_coordinator(hass)
        chore_data = _make_chore_data(coordinator)

        await _complete_chore_handler(hass, coordinator, chore_data, "sensor.test", {})

        hass.bus.async_fire.assert_called_once()
        event_name, payload = hass.bus.async_fire.call_args[0]
        assert event_name == EVENT_CHORE_COMPLETED
        assert "completed_at" in payload
        assert "completion_date" not in payload
        assert "next_due_date" in payload
        assert "completion_count" in payload

    @pytest.mark.asyncio
    async def test_already_complete_is_no_op_until_due_again(self):
        hass = MagicMock()
        hass.bus.async_fire = MagicMock()
        next_due = datetime(2024, 1, 10)
        coordinator = _make_coordinator(
            hass,
            {
                "status": CHORE_STATUS_COMPLETE,
                "completion_count": 3,
                "last_completed_date": datetime(2024, 1, 3),
                "next_due_date": next_due,
            },
        )
        chore_data = _make_chore_data(coordinator)

        await _complete_chore_handler(
            hass,
            coordinator,
            chore_data,
            "sensor.test",
            {"completion_date": datetime(2024, 1, 5)},
        )

        state = chore_data["state"]
        assert state["status"] == CHORE_STATUS_COMPLETE
        assert state["completion_count"] == 3
        _assert_same_instant(state["last_completed_date"], datetime(2024, 1, 3))
        _assert_same_instant(state["next_due_date"], next_due)
        coordinator.async_save_state.assert_not_awaited()
        coordinator.async_request_refresh.assert_not_awaited()
        hass.bus.async_fire.assert_not_called()

    @pytest.mark.asyncio
    async def test_undo_restores_previous_state_snapshot(self):
        hass = MagicMock()
        hass.bus.async_fire = MagicMock()
        prior_due = datetime(2024, 1, 10)
        coordinator = _make_coordinator(
            hass,
            {
                "status": CHORE_STATUS_PENDING,
                "completion_count": 2,
                "next_due_date": prior_due,
            },
        )
        chore_data = _make_chore_data(coordinator)

        await _complete_chore_handler(
            hass,
            coordinator,
            chore_data,
            "sensor.test",
            {"completion_date": datetime.now()},
        )

        await _undo_complete_chore_handler(
            hass,
            coordinator,
            chore_data,
            "sensor.test",
            {},
        )

        state = chore_data["state"]
        assert state["status"] == CHORE_STATUS_PENDING
        assert state["completion_count"] == 2
        _assert_same_instant(state["next_due_date"], prior_due)

        event_name, payload = hass.bus.async_fire.call_args[0]
        assert event_name == EVENT_CHORE_COMPLETE_UNDONE
        assert payload["entity_id"] == "sensor.test"

    @pytest.mark.asyncio
    async def test_undo_rejects_when_completion_too_old(self):
        hass = MagicMock()
        hass.bus.async_fire = MagicMock()
        coordinator = _make_coordinator(hass)
        chore_data = _make_chore_data(coordinator)

        chore_data["state"]["_undo_previous_state"] = {
            "status": CHORE_STATUS_PENDING,
            "completion_count": 0,
            "next_due_date": datetime(2024, 1, 10),
        }
        chore_data["state"]["_undo_completed_at"] = datetime.now() - timedelta(
            hours=DEFAULT_RESTORE_WINDOW_HOURS + 1
        )
        chore_data["state"]["_undo_used"] = False

        with pytest.raises(ServiceValidationError, match="too long ago"):
            await _undo_complete_chore_handler(
                hass,
                coordinator,
                chore_data,
                "sensor.test",
                {},
            )

    @pytest.mark.asyncio
    async def test_undo_rejects_without_snapshot(self):
        hass = MagicMock()
        hass.bus.async_fire = MagicMock()
        coordinator = _make_coordinator(hass)
        chore_data = _make_chore_data(coordinator)

        with pytest.raises(ServiceValidationError, match="no recent completion"):
            await _undo_complete_chore_handler(
                hass,
                coordinator,
                chore_data,
                "sensor.test",
                {},
            )


# ---------------------------------------------------------------------------
# Story 2.3 — Snooze
# ---------------------------------------------------------------------------


class TestSnoozeChoreHandler:
    """Tests for _snooze_chore_handler (Story 2.3)."""

    @pytest.mark.asyncio
    async def test_status_transitions_to_snoozed(self):
        hass = MagicMock()
        hass.bus.async_fire = MagicMock()
        coordinator = _make_coordinator(hass)
        chore_data = _make_chore_data(coordinator)

        await _snooze_chore_handler(hass, coordinator, chore_data, "sensor.test", {"days": 3})

        assert chore_data["state"]["status"] == CHORE_STATUS_SNOOZED

    @pytest.mark.asyncio
    async def test_next_due_date_pushed_forward(self):
        """next_due_date must shift forward by the snooze days."""
        hass = MagicMock()
        hass.bus.async_fire = MagicMock()
        original_due = datetime(2024, 1, 10)
        coordinator = _make_coordinator(hass, {"next_due_date": original_due})
        chore_data = _make_chore_data(coordinator)

        await _snooze_chore_handler(hass, coordinator, chore_data, "sensor.test", {"days": 3})

        _assert_same_instant(
            chore_data["state"]["next_due_date"],
            original_due + timedelta(days=3),
        )

    @pytest.mark.asyncio
    async def test_snooze_until_equals_next_due_date(self):
        hass = MagicMock()
        hass.bus.async_fire = MagicMock()
        coordinator = _make_coordinator(hass)
        chore_data = _make_chore_data(coordinator)

        await _snooze_chore_handler(hass, coordinator, chore_data, "sensor.test", {"days": 5})

        assert chore_data["state"]["snooze_until"] == chore_data["state"]["next_due_date"]

    @pytest.mark.asyncio
    async def test_snooze_count_increments(self):
        hass = MagicMock()
        hass.bus.async_fire = MagicMock()
        coordinator = _make_coordinator(hass, {"snooze_count": 1})
        chore_data = _make_chore_data(coordinator)

        await _snooze_chore_handler(hass, coordinator, chore_data, "sensor.test", {"days": 3})

        assert chore_data["state"]["snooze_count"] == 2

    @pytest.mark.asyncio
    async def test_default_snooze_days_used(self):
        """When no days specified, DEFAULT_SNOOZE_DAYS should be used."""
        hass = MagicMock()
        hass.bus.async_fire = MagicMock()
        original_due = datetime(2024, 1, 10)
        coordinator = _make_coordinator(hass, {"next_due_date": original_due})
        chore_data = _make_chore_data(coordinator)

        await _snooze_chore_handler(hass, coordinator, chore_data, "sensor.test", {})

        _assert_same_instant(
            chore_data["state"]["next_due_date"],
            original_due + timedelta(days=DEFAULT_SNOOZE_DAYS),
        )

    @pytest.mark.asyncio
    async def test_reason_stored(self):
        hass = MagicMock()
        hass.bus.async_fire = MagicMock()
        coordinator = _make_coordinator(hass)
        chore_data = _make_chore_data(coordinator)

        await _snooze_chore_handler(
            hass,
            coordinator,
            chore_data,
            "sensor.test",
            {"days": 3, "reason": "busy week"},
        )

        assert chore_data["state"]["snooze_reason"] == "busy week"

    @pytest.mark.asyncio
    async def test_state_persisted_before_refresh(self):
        call_order = []
        hass = MagicMock()
        hass.bus.async_fire = MagicMock()
        coordinator = _make_coordinator(hass)

        async def record_save():
            call_order.append("save")

        async def record_refresh():
            call_order.append("refresh")

        coordinator.async_save_state = record_save
        coordinator.async_request_refresh = record_refresh

        chore_data = _make_chore_data(coordinator)
        await _snooze_chore_handler(hass, coordinator, chore_data, "sensor.test", {"days": 3})

        assert call_order == ["save", "refresh"]

    @pytest.mark.asyncio
    async def test_event_payload_fields(self):
        hass = MagicMock()
        hass.bus.async_fire = MagicMock()
        coordinator = _make_coordinator(hass)
        chore_data = _make_chore_data(coordinator)

        await _snooze_chore_handler(
            hass,
            coordinator,
            chore_data,
            "sensor.test",
            {"days": 4, "reason": "holiday"},
        )

        hass.bus.async_fire.assert_called_once()
        event_name, payload = hass.bus.async_fire.call_args[0]
        assert event_name == EVENT_CHORE_SNOOZED
        assert payload["snoozed_for_days"] == 4
        assert "new_due_date" in payload
        assert "snooze_count" in payload
        assert payload["reason"] == "holiday"


# ---------------------------------------------------------------------------
# Story 2.4 — Restore
# ---------------------------------------------------------------------------


class TestRestoreChoreHandler:
    """Tests for _restore_chore_handler (Story 2.4)."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("reload_state", [False, True])
    async def test_restore_survives_midnight_refresh(self, reload_state):
        skipped_at = datetime.fromisoformat("2026-10-28T23:55:00+00:00")
        restored_at = datetime.fromisoformat("2026-10-29T00:05:00+00:00")
        original_due = skipped_at.replace(hour=0, minute=0)
        coordinator = ChoreCoordinator.__new__(ChoreCoordinator)
        coordinator.hass = MagicMock()
        coordinator.entry = MagicMock(entry_id="hub_1")
        coordinator._chores = {
            "chore_1": {
                "config": {"chore_name": "Test Chore"},
                "state": {
                    "status": CHORE_STATUS_SKIPPED,
                    "last_skip_date": skipped_at,
                    "original_due_date": original_due,
                    "next_due_date": original_due + timedelta(days=7),
                    "completion_count": 4,
                },
            }
        }
        coordinator._subentry_to_chore = {}
        coordinator.async_save_state = AsyncMock()
        coordinator.async_request_refresh = AsyncMock(
            side_effect=coordinator._async_update_hub_data
        )
        chore_data = coordinator._chores["chore_1"]

        if reload_state:
            coordinator._store = MagicMock()
            coordinator._store.async_save = AsyncMock()
            await coordinator._async_save_hub_state()
            stored = coordinator._store.async_save.call_args.args[0]
            coordinator._store.async_load = AsyncMock(return_value=stored)
            chore_data["state"] = {}
            await coordinator._async_load_hub_state()

        with patch("custom_components.sh_chore_tracker.dt_util.now", return_value=restored_at):
            await coordinator._async_update_hub_data()
            assert chore_data["state"]["status"] == CHORE_STATUS_PENDING
            await _restore_chore_handler(
                coordinator.hass, coordinator, chore_data, "sensor.test", {}
            )

        assert chore_data["state"]["next_due_date"] == original_due
        assert chore_data["state"]["status"] == "overdue"
        assert chore_data["state"]["completion_count"] == 4
        assert chore_data["state"]["skip_restored"] is True

    @pytest.mark.asyncio
    async def test_restore_resolves_status_and_persists(self):
        hass = MagicMock()
        hass.bus.async_fire = MagicMock()
        coordinator = _make_coordinator(
            hass,
            {
                "status": CHORE_STATUS_SKIPPED,
                "skip_restored": False,
                "last_skip_date": datetime.now() - timedelta(hours=1),
                "original_due_date": datetime(2024, 1, 10),
                "next_due_date": datetime(2024, 1, 20),
            },
        )
        chore_data = _make_chore_data(coordinator)

        await _restore_chore_handler(hass, coordinator, chore_data, "sensor.test", {})

        state = chore_data["state"]
        assert state["status"] == "overdue"
        assert state["skip_restored"] is True
        _assert_same_instant(state["next_due_date"], state["original_due_date"])
        coordinator.async_save_state.assert_awaited_once()
        coordinator.async_request_refresh.assert_awaited_once()

        hass.bus.async_fire.assert_called_once()
        event_name, payload = hass.bus.async_fire.call_args[0]
        assert event_name == EVENT_CHORE_RESTORED
        assert payload["entity_id"] == "sensor.test"
        assert payload["original_skip_date"] is not None

    @pytest.mark.asyncio
    async def test_restore_rejects_when_skip_too_old(self):
        hass = MagicMock()
        hass.bus.async_fire = MagicMock()
        coordinator = _make_coordinator(
            hass,
            {
                "status": CHORE_STATUS_SKIPPED,
                "skip_restored": False,
                "last_skip_date": datetime.now()
                - timedelta(hours=DEFAULT_RESTORE_WINDOW_HOURS + 1),
            },
        )
        chore_data = _make_chore_data(coordinator)

        with pytest.raises(ServiceValidationError, match="too long ago"):
            await _restore_chore_handler(hass, coordinator, chore_data, "sensor.test", {})

        coordinator.async_save_state.assert_not_awaited()
        coordinator.async_request_refresh.assert_not_awaited()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("elapsed_minutes", [0, 10, 1439, 1440, 1441])
    async def test_restore_window_boundary(self, elapsed_minutes):
        now = datetime.fromisoformat("2026-10-29T12:00:00+00:00")
        hass = MagicMock()
        coordinator = _make_coordinator(
            hass,
            {
                "status": CHORE_STATUS_PENDING,
                "last_skip_date": now - timedelta(minutes=elapsed_minutes),
                "original_due_date": now - timedelta(days=2),
            },
        )
        chore_data = _make_chore_data(coordinator)
        with patch("custom_components.sh_chore_tracker.dt_util.now", return_value=now):
            if elapsed_minutes > 1440:
                with pytest.raises(ServiceValidationError, match="too long ago"):
                    await _restore_chore_handler(hass, coordinator, chore_data, "sensor.test", {})
                coordinator.async_save_state.assert_not_awaited()
            else:
                await _restore_chore_handler(hass, coordinator, chore_data, "sensor.test", {})
                with pytest.raises(ServiceValidationError, match="already been restored"):
                    await _restore_chore_handler(hass, coordinator, chore_data, "sensor.test", {})

    @pytest.mark.asyncio
    @pytest.mark.parametrize("action", ["complete", "snooze", "reset", "reanchor"])
    async def test_later_actions_invalidate_restore(self, action):
        now = datetime.fromisoformat("2026-10-29T12:00:00+00:00")
        hass = MagicMock()
        coordinator = _make_coordinator(hass, {"next_due_date": now})
        chore_data = _make_chore_data(coordinator)
        with patch("custom_components.sh_chore_tracker.dt_util.now", return_value=now):
            await _skip_chore_handler(hass, coordinator, chore_data, "sensor.test", {})
            if action == "reanchor":
                chore_data["config"]["first_occurrence_date"] = "2026-11-01"
                ChoreCoordinator._apply_chore_first_occurrence_update(coordinator, chore_data)
            else:
                handler = {
                    "complete": _complete_chore_handler,
                    "snooze": _snooze_chore_handler,
                    "reset": _reset_next_due_date_handler,
                }[action]
                await handler(hass, coordinator, chore_data, "sensor.test", {})
            with pytest.raises(ServiceValidationError, match="no skipped occurrence"):
                await _restore_chore_handler(hass, coordinator, chore_data, "sensor.test", {})

    @pytest.mark.asyncio
    async def test_restore_undoes_only_the_latest_skip(self):
        now = datetime.fromisoformat("2026-10-29T12:00:00+00:00")
        hass = MagicMock()
        coordinator = _make_coordinator(hass, {"next_due_date": now})
        chore_data = _make_chore_data(coordinator)
        with patch("custom_components.sh_chore_tracker.dt_util.now", return_value=now):
            await _skip_chore_handler(hass, coordinator, chore_data, "sensor.test", {})
            after_first_skip = chore_data["state"]["next_due_date"]
            await _skip_chore_handler(hass, coordinator, chore_data, "sensor.test", {})
            await _restore_chore_handler(hass, coordinator, chore_data, "sensor.test", {})
        assert chore_data["state"]["next_due_date"] == after_first_skip


# ---------------------------------------------------------------------------
# Story 2.4 — Skip
# ---------------------------------------------------------------------------


class TestSkipChoreHandler:
    """Tests for _skip_chore_handler (Story 2.4)."""

    @pytest.mark.asyncio
    async def test_skip_advances_from_current_due_date(self):
        hass = MagicMock()
        hass.bus.async_fire = MagicMock()
        current_due = datetime(2024, 1, 10)
        coordinator = _make_coordinator(hass, {"next_due_date": current_due})
        chore_data = _make_chore_data(coordinator)

        await _skip_chore_handler(
            hass, coordinator, chore_data, "sensor.test", {"reason": "vacation"}
        )

        state = chore_data["state"]
        assert state["status"] == CHORE_STATUS_SKIPPED
        _assert_same_instant(state["original_due_date"], current_due)
        _assert_same_instant(state["next_due_date"], datetime(2024, 1, 17))

    @pytest.mark.asyncio
    async def test_skip_persists_refreshes_and_emits_event(self):
        hass = MagicMock()
        hass.bus.async_fire = MagicMock()
        coordinator = _make_coordinator(hass, {"next_due_date": datetime(2024, 1, 10)})
        chore_data = _make_chore_data(coordinator)

        await _skip_chore_handler(
            hass, coordinator, chore_data, "sensor.test", {"reason": "weather"}
        )

        coordinator.async_save_state.assert_awaited_once()
        coordinator.async_request_refresh.assert_awaited_once()
        hass.bus.async_fire.assert_called_once()
        event_name, payload = hass.bus.async_fire.call_args[0]
        assert event_name == EVENT_CHORE_SKIPPED
        assert payload["entity_id"] == "sensor.test"
        assert payload["reason"] == "weather"
        assert "next_due_date" in payload


# ---------------------------------------------------------------------------
# Story 3.2 — Reassign
# ---------------------------------------------------------------------------


class TestReassignChoreHandler:
    """Tests for _reassign_chore_handler (Story 3.2)."""

    @pytest.mark.asyncio
    async def test_reassign_rejects_existing_non_person_without_mutation(self):
        hass = MagicMock()
        coordinator = _make_coordinator(hass)
        chore_data = _make_chore_data(coordinator)
        chore_data["config"]["assigned_person"] = "person.alice"
        with pytest.raises(ServiceValidationError, match="Person entity"):
            await _reassign_chore_handler(
                hass, coordinator, chore_data, "sensor.test", {"person_id": "light.kitchen"}
            )
        assert chore_data["config"]["assigned_person"] == "person.alice"
        hass.config_entries.async_update_subentry.assert_not_called()
        coordinator.async_request_refresh.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_reassign_updates_assignment_and_emits_event(self):
        hass = MagicMock()
        hass.bus.async_fire = MagicMock()
        hass.states.get = MagicMock(return_value=MagicMock())
        coordinator = _make_coordinator(hass)
        coordinator.entry = MagicMock()
        subentry = MagicMock()
        subentry.data = dict(coordinator._chore_data["config"])
        coordinator.entry.subentries = {"subentry_1": subentry}
        chore_data = _make_chore_data(coordinator)
        chore_data["config"]["assigned_person"] = "person.alice"
        entity_registry_entry = MagicMock(config_subentry_id="subentry_1")
        with patch("custom_components.sh_chore_tracker.er.async_get") as get_registry:
            get_registry.return_value.async_get.return_value = entity_registry_entry

            await _reassign_chore_handler(
                hass,
                coordinator,
                chore_data,
                "sensor.test",
                {"person_id": "person.bob"},
            )

        assert chore_data["config"]["assigned_person"] == "person.bob"
        hass.config_entries.async_update_subentry.assert_called_once()
        coordinator.async_request_refresh.assert_awaited_once()
        hass.bus.async_fire.assert_called_once()
        event_name, payload = hass.bus.async_fire.call_args[0]
        assert event_name == EVENT_CHORE_REASSIGNED
        assert payload["old_person"] == "person.alice"
        assert payload["new_person"] == "person.bob"

    @pytest.mark.asyncio
    async def test_reassign_rejects_unknown_person(self):
        hass = MagicMock()
        hass.bus.async_fire = MagicMock()
        hass.states.get = MagicMock(return_value=None)
        coordinator = _make_coordinator(hass)
        chore_data = _make_chore_data(coordinator)

        with pytest.raises(ServiceValidationError, match="Person entity"):
            await _reassign_chore_handler(
                hass,
                coordinator,
                chore_data,
                "sensor.test",
                {"person_id": "person.unknown"},
            )

        coordinator.async_request_refresh.assert_not_awaited()
        hass.bus.async_fire.assert_not_called()


class TestResetNextDueDateHandler:
    """Tests for _reset_next_due_date_handler."""

    @pytest.mark.asyncio
    async def test_reset_sets_normalized_next_due_and_clears_transient_state(self):
        hass = MagicMock()
        hass.bus.async_fire = MagicMock()
        coordinator = _make_coordinator(
            hass,
            {
                "status": CHORE_STATUS_SNOOZED,
                "snooze_until": datetime(2026, 5, 12),
                "snooze_reason": "delay",
                "skip_reason": "vacation",
                "last_skip_date": datetime(2026, 5, 1),
                "original_due_date": datetime(2026, 5, 3),
                "skip_restored": True,
                "last_completed_date": datetime(2026, 5, 5),
            },
        )
        chore_data = _make_chore_data(coordinator)
        chore_data["config"].update(
            {
                "recurrence_type": "weekly",
                "pattern_interval": 1,
                "weekly_days": ["monday"],
            }
        )

        await _reset_next_due_date_handler(
            hass,
            coordinator,
            chore_data,
            "sensor.test",
            {},
        )

        state = chore_data["state"]
        assert state["next_due_date"].date() == date(2026, 5, 11)
        assert state["snooze_until"] is None
        assert state["snooze_reason"] is None
        assert state["skip_reason"] is None
        assert state["last_skip_date"] is None
        assert state["original_due_date"] is None
        assert state["skip_restored"] is False

        coordinator.async_save_state.assert_awaited_once()
        coordinator.async_request_refresh.assert_awaited_once()

        event_name, payload = hass.bus.async_fire.call_args[0]
        assert event_name == EVENT_CHORE_SCHEDULE_RESET
        assert payload["entity_id"] == "sensor.test"
        assert payload["next_due_date"].startswith("2026-05-11")

    @pytest.mark.asyncio
    async def test_reset_without_completion_uses_first_occurrence(self):
        hass = MagicMock()
        hass.bus.async_fire = MagicMock()
        coordinator = _make_coordinator(hass)
        chore_data = _make_chore_data(coordinator)
        chore_data["config"]["first_occurrence_date"] = "2026-05-20"

        await _reset_next_due_date_handler(
            hass,
            coordinator,
            chore_data,
            "sensor.test",
            {},
        )

        assert chore_data["state"]["next_due_date"].date() == date(2026, 5, 20)


# ---------------------------------------------------------------------------
# Story 2.6 — Data Persistence
# ---------------------------------------------------------------------------


class TestDataPersistence:
    """Tests for async_load_persisted_state / async_save_state (Story 2.6)."""

    def _make_real_coordinator(self, hass):
        """Construct a ChoreCoordinator with mocked Store and entry."""
        entry = MagicMock()
        entry.entry_id = "test_entry_id"
        entry.data = {"is_hub_entry": True}
        chore_config = {
            "chore_name": "Test Chore",
            "recurrence_type": "interval",
            "pattern_interval": 7,
            "interval_unit": "days",
        }
        subentry = MagicMock()
        subentry.subentry_id = "subentry_1"
        subentry.unique_id = "chore_1"
        subentry.data = chore_config
        entry.get_subentries_of_type.return_value = [subentry]

        with patch("custom_components.sh_chore_tracker.Store") as MockStore:
            store_instance = MagicMock()
            store_instance.async_load = AsyncMock(return_value=None)
            store_instance.async_save = AsyncMock()
            MockStore.return_value = store_instance

            coordinator = ChoreCoordinator(hass, entry)
            coordinator._store = store_instance
            return coordinator, store_instance

    @pytest.mark.asyncio
    async def test_load_state_no_stored_data(self):
        """If store returns None, in-memory state is unchanged."""
        hass = MagicMock()
        coordinator, store = self._make_real_coordinator(hass)
        store.async_load = AsyncMock(return_value=None)

        original_status = coordinator._chores["chore_1"]["state"]["status"]
        await coordinator.async_load_persisted_state()

        assert coordinator._chores["chore_1"]["state"]["status"] == original_status

    @pytest.mark.asyncio
    async def test_load_state_deserializes_datetime_fields(self):
        """ISO datetime strings in stored data are deserialized to datetime objects."""
        hass = MagicMock()
        coordinator, store = self._make_real_coordinator(hass)
        iso_date = "2024-03-15T10:30:00"
        store.async_load = AsyncMock(
            return_value={
                "chores": {
                    "chore_1": {
                        "status": "complete",
                        "next_due_date": iso_date,
                        "completion_count": 5,
                    }
                }
            }
        )

        await coordinator.async_load_persisted_state()

        state = coordinator._chores["chore_1"]["state"]
        assert state["status"] == "complete"
        assert state["completion_count"] == 5
        assert isinstance(state["next_due_date"], datetime)
        assert state["next_due_date"] == datetime.fromisoformat(iso_date)

    @pytest.mark.asyncio
    async def test_save_state_serializes_datetime_fields(self):
        """datetime values in state are serialized to ISO strings before saving."""
        hass = MagicMock()
        coordinator, store = self._make_real_coordinator(hass)
        dt = datetime(2024, 3, 15, 10, 30, 0)
        state = coordinator._chores["chore_1"]["state"]
        state["next_due_date"] = dt
        state["completion_count"] = 3

        await coordinator.async_save_state()

        store.async_save.assert_called_once()
        saved = store.async_save.call_args[0][0]
        assert saved["chores"]["chore_1"]["next_due_date"] == dt.isoformat()
        assert saved["chores"]["chore_1"]["completion_count"] == 3

    @pytest.mark.asyncio
    async def test_round_trip_preserves_state(self):
        """Save then load should yield identical state values."""
        hass = MagicMock()
        coordinator, store = self._make_real_coordinator(hass)

        original = {
            "status": "snoozed",
            "next_due_date": datetime(2024, 4, 1, 0, 0, 0),
            "snooze_until": datetime(2024, 4, 1, 0, 0, 0),
            "completion_count": 7,
            "snooze_count": 2,
        }
        coordinator._chores["chore_1"]["state"].update(original)

        await coordinator.async_save_state()

        saved_payload = store.async_save.call_args[0][0]
        store.async_load = AsyncMock(return_value=saved_payload)

        await coordinator.async_load_persisted_state()

        state = coordinator._chores["chore_1"]["state"]
        assert state["status"] == "snoozed"
        assert state["next_due_date"] == original["next_due_date"]
        assert state["snooze_until"] == original["snooze_until"]
        assert state["completion_count"] == 7
        assert state["snooze_count"] == 2

    @pytest.mark.asyncio
    async def test_save_state_no_op_when_no_data(self):
        """async_save_state should not crash when _chore_data is empty."""
        hass = MagicMock()
        coordinator, store = self._make_real_coordinator(hass)
        coordinator._chores = {}

        await coordinator.async_save_state()  # Should not raise

        store.async_save.assert_not_called()


# ---------------------------------------------------------------------------
# Integration-based entity validation
# ---------------------------------------------------------------------------


class TestFindChoreData:
    """Tests for _find_chore_data integration-field validation."""

    @pytest.mark.asyncio
    async def test_returns_coordinator_when_platform_matches(self):
        """Entity registered under sh_chore_tracker platform returns coordinator."""
        hass = MagicMock()
        coordinator = _make_coordinator(hass)
        hass.data = {DOMAIN: {"entry_1": coordinator}}

        entry = MagicMock()
        entry.config_entry_id = "entry_1"
        entry.config_subentry_id = "subentry_1"
        entry.platform = DOMAIN

        with patch(
            "custom_components.sh_chore_tracker.er.async_get",
        ) as mock_registry:
            mock_registry.return_value.async_get.return_value = entry
            result_coordinator, result_data = await _find_chore_data(
                hass, "sensor.my_custom_chore_name"
            )

        assert result_coordinator is coordinator
        assert result_data is coordinator._chore_data

    @pytest.mark.asyncio
    async def test_returns_none_when_platform_is_different_integration(self):
        """Entity from another integration is rejected even with a matching entry_id."""
        hass = MagicMock()
        coordinator = _make_coordinator(hass)
        hass.data = {DOMAIN: {"entry_1": coordinator}}

        entry = MagicMock()
        entry.config_entry_id = "entry_1"
        entry.platform = "some_other_integration"

        with patch(
            "custom_components.sh_chore_tracker.er.async_get",
        ) as mock_registry:
            mock_registry.return_value.async_get.return_value = entry
            result_coordinator, result_data = await _find_chore_data(hass, "sensor.chore_lookalike")

        assert result_coordinator is None
        assert result_data is None

    @pytest.mark.asyncio
    async def test_returns_none_when_entity_not_in_registry(self):
        """Entity absent from the registry returns None."""
        hass = MagicMock()
        hass.data = {DOMAIN: {}}

        with patch(
            "custom_components.sh_chore_tracker.er.async_get",
        ) as mock_registry:
            mock_registry.return_value.async_get.return_value = None
            result_coordinator, result_data = await _find_chore_data(hass, "sensor.chore_unknown")

        assert result_coordinator is None
        assert result_data is None


class TestHandleServiceCallIntegrationValidation:
    """Tests that _handle_service_call uses integration-field validation."""

    @pytest.mark.asyncio
    async def test_accepts_entity_with_non_standard_name_from_our_integration(self):
        """An entity without 'sensor.chore_' prefix is accepted if it belongs to us."""
        hass = MagicMock()
        coordinator = _make_coordinator(hass)
        hass.data = {DOMAIN: {"entry_1": coordinator}}

        call = MagicMock()
        call.data = {"entity_id": "sensor.my_renamed_chore"}

        handler = AsyncMock()

        with patch(
            "custom_components.sh_chore_tracker._find_chore_data",
            AsyncMock(return_value=(coordinator, coordinator._chore_data)),
        ):
            await _handle_service_call(hass, call, handler)

        handler.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_rejects_entity_from_different_integration(self):
        """An entity from a different integration raises ServiceValidationError."""
        hass = MagicMock()
        hass.data = {DOMAIN: {}}

        call = MagicMock()
        # Entity ID matches old prefix pattern but belongs to another integration
        call.data = {"entity_id": "sensor.chore_lookalike"}

        handler = AsyncMock()

        with patch(
            "custom_components.sh_chore_tracker._find_chore_data",
            AsyncMock(return_value=(None, None)),
        ):
            with pytest.raises(ServiceValidationError, match="not found"):
                await _handle_service_call(hass, call, handler)

        handler.assert_not_called()


class TestHubServices:
    """Tests for hub-level chore creation and person-filtered listing."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("person_id", ["light.kitchen", "person.missing"])
    async def test_create_rejects_invalid_person_without_mutation(self, person_id):
        hass = MagicMock()
        hass.data = {DOMAIN: {"hub_1": MagicMock()}}
        hass.states.get.return_value = None if person_id == "person.missing" else MagicMock()
        call = MagicMock(data={"chore_name": "Test", "assigned_person": person_id})
        with pytest.raises(ServiceValidationError, match="Person entity"):
            await _handle_create_chore(hass, call)
        hass.config_entries.async_add_subentry.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_chore_adds_a_validated_subentry(self):
        hass = MagicMock()
        hub_entry = MagicMock()
        hub_entry.entry_id = "hub_entry"
        coordinator = MagicMock(spec=ChoreCoordinator)
        hass.data = {DOMAIN: {hub_entry.entry_id: coordinator}}
        hass.config_entries.async_get_entry.return_value = hub_entry
        call = MagicMock()
        call.data = {
            "chore_name": "Water plants",
            "recurrence_type": "interval",
            "pattern_interval": 7,
            "interval_unit": "days",
            "assigned_person": "none",
            "first_occurrence_date": date.today() + timedelta(days=7),
        }

        await _handle_create_chore(hass, call)

        subentry = hass.config_entries.async_add_subentry.call_args.args[1]
        assert subentry.subentry_type == "chore"
        assert subentry.title == "Water plants"
        assert subentry.data["pattern_interval"] == 7
        assert (
            subentry.data["first_occurrence_date"] == call.data["first_occurrence_date"].isoformat()
        )
        assert subentry.unique_id

    def test_list_my_chores_filters_by_person(self):
        coordinator = MagicMock(spec=ChoreCoordinator)
        coordinator.chore_data = {
            "laundry": {
                "config": {"chore_name": "Laundry", "assigned_person": "person.alice"},
                "state": {"status": "pending", "next_due_date": datetime(2026, 10, 10)},
            },
            "dishes": {
                "config": {"chore_name": "Dishes", "assigned_person": "person.bob"},
                "state": {"status": "overdue", "next_due_date": datetime(2026, 10, 1)},
            },
        }
        coordinator.entity_id_for_chore.side_effect = lambda chore_id, _config: (
            f"sensor.chore_{chore_id}"
        )
        hass = MagicMock()
        hass.data = {DOMAIN: {"hub_entry": coordinator}}
        call = MagicMock()
        call.data = {"person_id": "person.alice"}

        response = _handle_list_my_chores(hass, call)

        assert [chore["name"] for chore in response["chores"]] == ["Laundry"]
        assert response["chores"][0]["entity_id"] == "sensor.chore_laundry"

    def test_list_my_chores_rejects_non_person_entity(self):
        coordinator = MagicMock(spec=ChoreCoordinator)
        hass = MagicMock()
        hass.data = {DOMAIN: {"hub_entry": coordinator}}
        call = MagicMock()
        call.data = {"person_id": "light.kitchen"}

        with pytest.raises(ServiceValidationError, match="Person entity"):
            _handle_list_my_chores(hass, call)
