"""Test the Chore Tracker integration initialization and RecurrenceEngine."""

from datetime import date, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.sh_chore_tracker import (
    PLATFORMS,
    ChoreCoordinator,
    RecurrenceEngine,
    _async_ensure_summary_subentry,
    _async_update_hub_entities,
    async_migrate_entry,
    async_setup,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.sh_chore_tracker.const import (
    CHORE_STATUS_COMPLETE,
    CHORE_STATUS_DUE,
    CHORE_STATUS_OVERDUE,
    CHORE_STATUS_PENDING,
    CHORE_STATUS_SKIPPED,
    CHORE_STATUS_SNOOZED,
    DOMAIN,
    EVENT_CHORE_OVERDUE,
    HUB_UNIQUE_ID,
    MONTHLY_MODE_ORDINAL_WEEKDAY,
    SUBENTRY_TYPE_SUMMARY,
)


def _assert_same_instant(actual: datetime, expected: datetime) -> None:
    """Assert datetime equality while tolerating naive vs aware test inputs."""
    if actual.tzinfo is not None and expected.tzinfo is None:
        expected = expected.replace(tzinfo=actual.tzinfo)
    elif actual.tzinfo is None and expected.tzinfo is not None:
        actual = actual.replace(tzinfo=expected.tzinfo)
    assert actual == expected


@pytest.mark.asyncio
async def test_setup_entry():
    """Test successful setup of integration."""
    hass = Mock()
    hass.data = {}

    entry = Mock()
    entry.entry_id = "test_entry"
    entry.version = 3
    entry.data = {"is_hub_entry": True}
    summary = Mock(subentry_id="summary_subentry")
    entry.get_subentries_of_type.return_value = [summary]

    with patch("custom_components.sh_chore_tracker.ChoreCoordinator") as mock_coordinator:
        mock_coordinator_instance = Mock()
        mock_coordinator_instance.async_load_persisted_state = AsyncMock()
        mock_coordinator_instance.async_config_entry_first_refresh = AsyncMock()
        mock_coordinator.return_value = mock_coordinator_instance

        with patch.object(
            hass.config_entries, "async_forward_entry_setups", new_callable=AsyncMock
        ) as mock_forward:
            mock_forward.return_value = True

            with (
                patch("custom_components.sh_chore_tracker.dr.async_get") as get_devices,
                patch(
                    "custom_components.sh_chore_tracker._async_update_hub_entities"
                ) as update_entities,
            ):
                get_devices.return_value.async_get_or_create = Mock()
                result = await async_setup_entry(hass, entry)
            update_entities.assert_called_once_with(hass, entry, "summary_subentry")
            get_devices.return_value.async_update_device.assert_called_once_with(
                get_devices.return_value.async_get_or_create.return_value.id,
                new_config_subentry_id="summary_subentry",
            )
            assert PLATFORMS == ["sensor", "button"]
            assert result is True
            assert DOMAIN in hass.data
            assert entry.entry_id in hass.data[DOMAIN]


def test_chore_entity_lookup_ignores_buttons() -> None:
    coordinator = Mock()
    coordinator._subentry_to_chore = {"subentry_1": "chore_1"}
    coordinator.entry.entry_id = "hub_entry"
    button = Mock(
        config_subentry_id="subentry_1",
        domain="button",
        unique_id="chore_chore_1_complete_chore",
        entity_id="button.laundry_complete",
    )
    sensor = Mock(
        config_subentry_id="subentry_1",
        domain="sensor",
        unique_id="chore_chore_1",
        entity_id="sensor.my_renamed_laundry",
    )
    with (
        patch("custom_components.sh_chore_tracker.er.async_get"),
        patch(
            "custom_components.sh_chore_tracker.er.async_entries_for_config_entry",
            return_value=[button, sensor],
        ),
    ):
        entity_id = ChoreCoordinator.entity_id_for_chore(
            coordinator, "chore_1", {"chore_name": "Laundry"}
        )
    assert entity_id == "sensor.my_renamed_laundry"


def test_summary_subentry_is_created_for_existing_hub() -> None:
    hass = Mock()
    entry = Mock()
    entry.get_subentries_of_type.return_value = []

    summary = _async_ensure_summary_subentry(hass, entry)

    assert summary.title == "Overall summary"
    assert summary.subentry_type == SUBENTRY_TYPE_SUMMARY
    assert summary.unique_id == f"{HUB_UNIQUE_ID}_summary"
    assert summary.data == {}
    hass.config_entries.async_add_subentry.assert_called_once_with(entry, summary)


def test_summary_subentry_is_reused_without_changing_its_title() -> None:
    hass = Mock()
    summary = Mock(title="My household overview")
    entry = Mock()
    entry.get_subentries_of_type.return_value = [summary]

    assert _async_ensure_summary_subentry(hass, entry) is summary
    hass.config_entries.async_add_subentry.assert_not_called()


def test_existing_summary_sensor_moves_to_summary_group() -> None:
    registry = Mock()
    entity = Mock(
        platform=DOMAIN,
        domain="sensor",
        unique_id=f"{HUB_UNIQUE_ID}_next_due",
        entity_id="sensor.my_next_chore",
        config_subentry_id=None,
    )
    with (
        patch("custom_components.sh_chore_tracker.er.async_get", return_value=registry),
        patch(
            "custom_components.sh_chore_tracker.er.async_entries_for_config_entry",
            return_value=[entity],
        ),
    ):
        _async_update_hub_entities(Mock(), Mock(entry_id="hub_entry"), "summary_subentry")
    registry.async_update_entity.assert_called_once_with(
        "sensor.my_next_chore", config_subentry_id="summary_subentry"
    )
    registry.async_get_available_entity_id.assert_not_called()


@pytest.mark.parametrize(
    ("unique_id", "entity_id", "object_id"),
    [
        pytest.param(
            "household_next_due",
            "sensor.chore_tracker",
            "chores_next_due",
            id="next-due",
        ),
        pytest.param(
            "household_overdue_count",
            "sensor.chore_tracker_2",
            "chores_overdue_count",
            id="overdue-count",
        ),
        pytest.param(
            "household_next_due",
            "sensor.chore_tracker_2",
            "chores_next_due",
            id="reversed-order",
        ),
    ],
)
def test_update_hub_entities_renames_generic_ids(
    unique_id: str, entity_id: str, object_id: str
) -> None:
    hass = Mock()
    entry = Mock(entry_id="hub_entry")
    entity = Mock(platform=DOMAIN, domain="sensor", unique_id=unique_id, entity_id=entity_id)
    registry = Mock()
    registry.async_get_available_entity_id.return_value = f"sensor.{object_id}_2"
    with (
        patch("custom_components.sh_chore_tracker.er.async_get", return_value=registry),
        patch(
            "custom_components.sh_chore_tracker.er.async_entries_for_config_entry",
            return_value=[entity],
        ),
    ):
        _async_update_hub_entities(hass, entry)
    registry.async_get_available_entity_id.assert_called_once_with("sensor", object_id)
    registry.async_update_entity.assert_called_once_with(
        entity_id, new_entity_id=f"sensor.{object_id}_2"
    )
    registry.async_remove.assert_not_called()


@pytest.mark.parametrize(
    ("platform", "domain", "unique_id", "entity_id"),
    [
        pytest.param(
            DOMAIN,
            "sensor",
            "household_next_due",
            "sensor.my_next_chore",
            id="custom-id",
        ),
        pytest.param(
            DOMAIN,
            "sensor",
            "household_overdue_count",
            "sensor.chores_overdue_count",
            id="already-migrated",
        ),
        pytest.param(
            DOMAIN,
            "sensor",
            "chore_laundry",
            "sensor.chore_tracker",
            id="individual-chore",
        ),
        pytest.param(
            "other",
            "sensor",
            "household_next_due",
            "sensor.chore_tracker",
            id="other-platform",
        ),
    ],
)
def test_update_hub_entities_preserves_other_ids(
    platform: str, domain: str, unique_id: str, entity_id: str
) -> None:
    registry = Mock()
    entity = Mock(platform=platform, domain=domain, unique_id=unique_id, entity_id=entity_id)
    with (
        patch("custom_components.sh_chore_tracker.er.async_get", return_value=registry),
        patch(
            "custom_components.sh_chore_tracker.er.async_entries_for_config_entry",
            return_value=[entity],
        ),
    ):
        _async_update_hub_entities(Mock(), Mock(entry_id="hub_entry"))
    registry.async_update_entity.assert_not_called()
    registry.async_remove.assert_not_called()


def test_update_hub_entities_removes_overdue_indicator() -> None:
    registry = Mock()
    entity = Mock(
        platform=DOMAIN,
        domain="binary_sensor",
        unique_id=f"{HUB_UNIQUE_ID}_any_overdue",
        entity_id="binary_sensor.my_overdue_indicator",
    )
    with (
        patch("custom_components.sh_chore_tracker.er.async_get", return_value=registry),
        patch(
            "custom_components.sh_chore_tracker.er.async_entries_for_config_entry",
            return_value=[entity],
        ),
    ):
        _async_update_hub_entities(Mock(), Mock(entry_id="hub_entry"))
    registry.async_remove.assert_called_once_with(entity.entity_id)
    registry.async_update_entity.assert_not_called()


@pytest.mark.asyncio
async def test_unload_entry():
    """Test successful unload of integration."""
    hass = Mock()
    hass.data = {DOMAIN: {"test_entry": Mock()}}

    entry = Mock()
    entry.entry_id = "test_entry"

    with patch.object(
        hass.config_entries, "async_unload_platforms", new_callable=AsyncMock
    ) as mock_unload:
        mock_unload.return_value = True

        result = await async_unload_entry(hass, entry)

        assert result is True
        assert entry.entry_id not in hass.data[DOMAIN]


@pytest.mark.asyncio
@pytest.mark.parametrize("existing_hub", [False, True])
async def test_setup_accepts_fresh_or_current_hub_without_modification(existing_hub):
    hass = Mock()
    entry = Mock(version=3, data={"is_hub_entry": True})
    hass.config_entries.async_entries.return_value = [entry] if existing_hub else []
    with patch("custom_components.sh_chore_tracker.Store") as store:
        assert await async_setup(hass, {}) is True
    store.assert_not_called()
    hass.config_entries.async_update_entry.assert_not_called()
    hass.config_entries.async_add_subentry.assert_not_called()
    hass.config_entries.async_remove.assert_not_called()


@pytest.mark.asyncio
async def test_setup_rejects_multiple_hubs_without_modification():
    hass = Mock()
    hass.config_entries.async_entries.return_value = [
        Mock(version=3, data={"is_hub_entry": True}),
        Mock(version=3, data={"is_hub_entry": True}),
    ]
    with pytest.raises(HomeAssistantError, match="Multiple"):
        await async_setup(hass, {})
    hass.config_entries.async_remove.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("data", [{}, {"is_hub_entry": False}, {"is_hub_entry": "true"}])
async def test_per_chore_layout_is_rejected_without_state_access(data):
    hass = Mock()
    entry = Mock(version=3, data=data)
    hass.config_entries.async_entries.return_value = [entry]
    with (
        patch("custom_components.sh_chore_tracker.Store") as store,
        patch("custom_components.sh_chore_tracker.ChoreCoordinator") as coordinator,
    ):
        assert await async_migrate_entry(hass, entry) is False
        with pytest.raises(HomeAssistantError, match="version-3"):
            await async_setup(hass, {})
        with pytest.raises(HomeAssistantError, match="version-3"):
            await async_setup_entry(hass, entry)
    store.assert_not_called()
    coordinator.assert_not_called()
    hass.config_entries.async_update_entry.assert_not_called()
    hass.config_entries.async_add_subentry.assert_not_called()
    hass.config_entries.async_remove.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("version", [1, 2, 4])
async def test_setup_rejects_unsupported_versions_without_modification(version):
    hass = Mock()
    entry = Mock(version=version, data={"is_hub_entry": True})
    hass.config_entries.async_entries.return_value = [entry]
    with patch("custom_components.sh_chore_tracker.Store") as store:
        with pytest.raises(HomeAssistantError, match="version-3"):
            await async_setup(hass, {})
    store.assert_not_called()
    hass.config_entries.async_update_entry.assert_not_called()
    hass.config_entries.async_add_subentry.assert_not_called()
    hass.config_entries.async_remove.assert_not_called()


@pytest.mark.asyncio
async def test_async_migrate_entry_rejects_v1_without_mutation():
    """An unsupported version is not silently relabeled as a current hub."""
    hass = Mock()
    entry = Mock()
    entry.version = 1
    entry.entry_id = "test_entry"

    with patch.object(hass.config_entries, "async_update_entry") as mock_update:
        result = await async_migrate_entry(hass, entry)

    assert result is False
    mock_update.assert_not_called()


@pytest.mark.asyncio
async def test_async_migrate_entry_already_v3_is_noop():
    """An entry already at the hub schema version does not get updated again."""
    hass = Mock()
    entry = Mock()
    entry.version = 3
    entry.entry_id = "test_entry"
    entry.data = {"is_hub_entry": True}

    with patch.object(hass.config_entries, "async_update_entry") as mock_update:
        result = await async_migrate_entry(hass, entry)

    assert result is True
    mock_update.assert_not_called()


@pytest.mark.asyncio
async def test_hub_coordinator_initializes_all_chore_subentries():
    hass = Mock()
    hass.data = {}
    entry = Mock()
    entry.entry_id = "hub_entry"
    subentries = [
        Mock(
            subentry_id="subentry_1",
            unique_id="chore_1",
            data={"chore_name": "Laundry", "first_occurrence_date": "2026-10-10"},
        ),
        Mock(
            subentry_id="subentry_2",
            unique_id="chore_2",
            data={"chore_name": "Dishes", "first_occurrence_date": "2026-10-11"},
        ),
    ]
    entry.get_subentries_of_type.return_value = subentries

    with patch("custom_components.sh_chore_tracker.Store"):
        coordinator = ChoreCoordinator(hass, entry)

    assert set(coordinator._chores) == {"chore_1", "chore_2"}
    assert coordinator.chore_id_for_subentry("subentry_1") == "chore_1"
    assert coordinator._chores["chore_1"]["config"]["chore_name"] == "Laundry"


@pytest.mark.asyncio
async def test_existing_v3_hub_preserves_identity_and_state_across_reload():
    hass = Mock()
    entry = Mock(entry_id="existing_hub", version=3, data={"is_hub_entry": True})
    subentry = Mock(
        subentry_id="existing_subentry",
        unique_id="existing_chore",
        data={
            "chore_name": "Laundry",
            "assigned_person": "person.alice",
            "first_occurrence_date": "2026-10-01",
        },
    )
    entry.get_subentries_of_type.return_value = [subentry]
    hass.config_entries.async_entries.return_value = [entry]
    stored = {
        "chores": {
            "existing_chore": {
                "status": CHORE_STATUS_PENDING,
                "next_due_date": "2026-11-05T00:00:00+00:00",
                "last_completed_date": "2026-10-29T12:00:00+00:00",
                "completion_count": 9,
            }
        }
    }
    store = Mock(async_load=AsyncMock(return_value=stored), async_save=AsyncMock())
    with patch("custom_components.sh_chore_tracker.Store", return_value=store) as make_store:
        for _attempt in range(2):
            assert await async_setup(hass, {}) is True
            assert await async_migrate_entry(hass, entry) is True
            coordinator = ChoreCoordinator(hass, entry)
            await coordinator.async_load_persisted_state()
            state = coordinator._chores["existing_chore"]["state"]
            assert state["next_due_date"].isoformat() == "2026-11-05T00:00:00+00:00"
            assert state["last_completed_date"].isoformat() == "2026-10-29T12:00:00+00:00"
            assert state["completion_count"] == 9
            assert coordinator.chore_id_for_subentry("existing_subentry") == "existing_chore"
            assert (
                coordinator._chores["existing_chore"]["config"]["assigned_person"] == "person.alice"
            )
            await coordinator.async_save_state()
            store.async_load.return_value = store.async_save.call_args.args[0]
    make_store.assert_called_with(hass, 1, "sh_chore_tracker_hub_existing_hub")
    hass.config_entries.async_update_entry.assert_not_called()
    hass.config_entries.async_add_subentry.assert_not_called()
    hass.config_entries.async_remove.assert_not_called()


def _make_coordinator_for_update(state: dict) -> ChoreCoordinator:
    """Build a minimal coordinator instance for lifecycle update tests."""
    coordinator = ChoreCoordinator.__new__(ChoreCoordinator)
    coordinator.hass = Mock()
    coordinator.hass.bus.async_fire = Mock()
    coordinator.entry = Mock()
    coordinator.entry.entry_id = "test_entry"
    coordinator._hub_mode = True
    coordinator._chores = {
        "test_chore": {
            "state": state,
            "config": {"chore_name": "Test Chore"},
        }
    }
    coordinator._subentry_to_chore = {}
    coordinator.async_save_state = AsyncMock()
    return coordinator


class TestCoordinatorLifecycleDateOnly:
    """Test date-only lifecycle transitions in ChoreCoordinator._async_update_data."""

    @pytest.mark.asyncio
    async def test_pending_due_today_transitions_to_due(self):
        coordinator = _make_coordinator_for_update(
            {
                "status": CHORE_STATUS_PENDING,
                "next_due_date": datetime(2026, 5, 27, 0, 0),
            }
        )

        with patch(
            "custom_components.sh_chore_tracker.dt_util.now",
            return_value=datetime(2026, 5, 27, 12, 0, tzinfo=datetime.now().astimezone().tzinfo),
        ):
            await coordinator._async_update_data()

        assert coordinator._chores["test_chore"]["state"]["status"] == CHORE_STATUS_DUE
        coordinator.async_save_state.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_pending_past_due_transitions_to_overdue(self):
        coordinator = _make_coordinator_for_update(
            {
                "status": CHORE_STATUS_PENDING,
                "next_due_date": datetime(2026, 5, 26, 0, 0),
            }
        )

        with patch(
            "custom_components.sh_chore_tracker.dt_util.now",
            return_value=datetime(2026, 5, 27, 9, 0, tzinfo=datetime.now().astimezone().tzinfo),
        ):
            await coordinator._async_update_data()

        assert coordinator._chores["test_chore"]["state"]["status"] == CHORE_STATUS_OVERDUE
        coordinator.async_save_state.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_complete_transitions_to_due_when_date_reached(self):
        coordinator = _make_coordinator_for_update(
            {
                "status": CHORE_STATUS_COMPLETE,
                "next_due_date": datetime(2026, 5, 27, 0, 0),
                "last_completed_date": datetime(2026, 5, 26, 19, 0),
            }
        )

        with patch(
            "custom_components.sh_chore_tracker.dt_util.now",
            return_value=datetime(2026, 5, 27, 8, 30, tzinfo=datetime.now().astimezone().tzinfo),
        ):
            await coordinator._async_update_data()

        assert coordinator._chores["test_chore"]["state"]["status"] == CHORE_STATUS_DUE
        coordinator.async_save_state.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_complete_transitions_to_pending_after_rollover_with_future_due(self):
        coordinator = _make_coordinator_for_update(
            {
                "status": CHORE_STATUS_COMPLETE,
                "next_due_date": datetime(2026, 5, 30, 0, 0),
                "last_completed_date": datetime(2026, 5, 27, 20, 0),
            }
        )

        with patch(
            "custom_components.sh_chore_tracker.dt_util.now",
            return_value=datetime(2026, 5, 28, 8, 0, tzinfo=datetime.now().astimezone().tzinfo),
        ):
            await coordinator._async_update_data()

        assert coordinator._chores["test_chore"]["state"]["status"] == CHORE_STATUS_PENDING
        coordinator.async_save_state.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_complete_stays_complete_same_day_with_future_due(self):
        coordinator = _make_coordinator_for_update(
            {
                "status": CHORE_STATUS_COMPLETE,
                "next_due_date": datetime(2026, 5, 30, 0, 0),
                "last_completed_date": datetime(2026, 5, 27, 8, 0),
            }
        )

        with patch(
            "custom_components.sh_chore_tracker.dt_util.now",
            return_value=datetime(2026, 5, 27, 20, 0, tzinfo=datetime.now().astimezone().tzinfo),
        ):
            await coordinator._async_update_data()

        assert coordinator._chores["test_chore"]["state"]["status"] == CHORE_STATUS_COMPLETE
        coordinator.async_save_state.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_snoozed_transitions_to_due_on_snooze_date(self):
        coordinator = _make_coordinator_for_update(
            {
                "status": CHORE_STATUS_SNOOZED,
                "next_due_date": datetime(2026, 5, 27, 0, 0),
                "snooze_until": datetime(2026, 5, 27, 0, 0),
                "snooze_reason": "test",
            }
        )

        with patch(
            "custom_components.sh_chore_tracker.dt_util.now",
            return_value=datetime(2026, 5, 27, 0, 5, tzinfo=datetime.now().astimezone().tzinfo),
        ):
            await coordinator._async_update_data()

        state = coordinator._chores["test_chore"]["state"]
        assert state["status"] == CHORE_STATUS_DUE
        assert state["snooze_until"] is None
        assert state["snooze_reason"] is None
        coordinator.async_save_state.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_skipped_transitions_to_due_when_next_date_reached(self):
        coordinator = _make_coordinator_for_update(
            {
                "status": CHORE_STATUS_SKIPPED,
                "next_due_date": datetime(2026, 5, 27, 0, 0),
                "last_skip_date": datetime(2026, 5, 26, 12, 0),
            }
        )

        with patch(
            "custom_components.sh_chore_tracker.dt_util.now",
            return_value=datetime(2026, 5, 27, 10, 0, tzinfo=datetime.now().astimezone().tzinfo),
        ):
            await coordinator._async_update_data()

        assert coordinator._chores["test_chore"]["state"]["status"] == CHORE_STATUS_DUE
        coordinator.async_save_state.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_skipped_transitions_to_pending_after_rollover_with_future_due(self):
        coordinator = _make_coordinator_for_update(
            {
                "status": CHORE_STATUS_SKIPPED,
                "next_due_date": datetime(2026, 5, 30, 0, 0),
                "last_skip_date": datetime(2026, 5, 27, 18, 0),
            }
        )

        with patch(
            "custom_components.sh_chore_tracker.dt_util.now",
            return_value=datetime(2026, 5, 28, 7, 0, tzinfo=datetime.now().astimezone().tzinfo),
        ):
            await coordinator._async_update_data()

        assert coordinator._chores["test_chore"]["state"]["status"] == CHORE_STATUS_PENDING
        coordinator.async_save_state.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_overdue_transition_fires_event_once(self):
        coordinator = _make_coordinator_for_update(
            {
                "status": CHORE_STATUS_PENDING,
                "next_due_date": datetime(2026, 5, 26, 0, 0),
            }
        )

        with patch(
            "custom_components.sh_chore_tracker.dt_util.now",
            return_value=datetime(2026, 5, 27, 10, 0, tzinfo=datetime.now().astimezone().tzinfo),
        ):
            await coordinator._async_update_data()

        assert coordinator._chores["test_chore"]["state"]["status"] == CHORE_STATUS_OVERDUE
        coordinator.hass.bus.async_fire.assert_called_once()
        event_name, payload = coordinator.hass.bus.async_fire.call_args[0]
        assert event_name == EVENT_CHORE_OVERDUE
        assert payload["from_status"] == CHORE_STATUS_PENDING
        assert payload["to_status"] == CHORE_STATUS_OVERDUE

    @pytest.mark.asyncio
    async def test_overdue_event_not_fired_when_already_overdue(self):
        coordinator = _make_coordinator_for_update(
            {
                "status": CHORE_STATUS_OVERDUE,
                "next_due_date": datetime(2026, 5, 26, 0, 0),
            }
        )

        with patch(
            "custom_components.sh_chore_tracker.dt_util.now",
            return_value=datetime(2026, 5, 27, 10, 0, tzinfo=datetime.now().astimezone().tzinfo),
        ):
            await coordinator._async_update_data()

        coordinator.hass.bus.async_fire.assert_not_called()

    @pytest.mark.asyncio
    async def test_first_occurrence_unchanged_keeps_existing_state(self):
        # applied_first_occurrence_date matches config → no reset
        coordinator = _make_coordinator_for_update(
            {
                "status": CHORE_STATUS_SNOOZED,
                "next_due_date": datetime(2026, 5, 19, 0, 0),  # advanced past seed
                "snooze_until": datetime(2026, 5, 19, 0, 0),
                "snooze_reason": "delay",
                "applied_first_occurrence_date": "2026-05-12",  # seed was already applied
            }
        )
        coordinator._chores["test_chore"]["config"] = {
            "chore_name": "Test Chore",
            "recurrence_type": "weekly",
            "weekly_days": ["monday"],
            "first_occurrence_date": "2026-05-12",
        }

        with patch(
            "custom_components.sh_chore_tracker.dt_util.now",
            return_value=datetime(2026, 5, 14, 9, 0, tzinfo=datetime.now().astimezone().tzinfo),
        ):
            changed = coordinator._apply_chore_first_occurrence_update(
                coordinator._chores["test_chore"]
            )

        assert changed is False
        state = coordinator._chores["test_chore"]["state"]
        assert state["status"] == CHORE_STATUS_SNOOZED
        assert state["snooze_until"] is not None

    @pytest.mark.asyncio
    async def test_first_occurrence_changed_reanchors_and_clears_transient_state(self):
        # applied_first_occurrence_date differs from config → re-anchor
        coordinator = _make_coordinator_for_update(
            {
                "status": CHORE_STATUS_SNOOZED,
                "next_due_date": datetime(2026, 5, 12, 0, 0),
                "snooze_until": datetime(2026, 5, 12, 0, 0),
                "snooze_reason": "delay",
                "last_skip_date": datetime(2026, 5, 1, 0, 0),
                "skip_reason": "vacation",
                "original_due_date": datetime(2026, 5, 2, 0, 0),
                "skip_restored": True,
                "applied_first_occurrence_date": "2026-05-12",  # old applied value
            }
        )
        coordinator._chores["test_chore"]["config"] = {
            "chore_name": "Test Chore",
            "recurrence_type": "weekly",
            "weekly_days": ["monday"],
            "first_occurrence_date": "2026-05-14",  # user changed it
        }

        with patch(
            "custom_components.sh_chore_tracker.dt_util.now",
            return_value=datetime(2026, 5, 14, 9, 0, tzinfo=datetime.now().astimezone().tzinfo),
        ):
            changed = coordinator._apply_chore_first_occurrence_update(
                coordinator._chores["test_chore"]
            )

        assert changed is True
        state = coordinator._chores["test_chore"]["state"]
        assert state["next_due_date"].date() == datetime(2026, 5, 18).date()
        assert state["status"] == CHORE_STATUS_PENDING
        assert state["snooze_until"] is None
        assert state["snooze_reason"] is None
        assert state["last_skip_date"] is None
        assert state["skip_reason"] is None
        assert state["original_due_date"] is None
        assert state["skip_restored"] is False
        from datetime import date

        assert state["applied_first_occurrence_date"] == date(2026, 5, 14)

    @pytest.mark.asyncio
    async def test_restart_after_completion_does_not_reset_state(self):
        """Regression: completing a chore and restarting HA must not revert to overdue.

        Before the fix, _apply_first_occurrence_update_if_changed compared
        next_due_date (advanced by completion) against first_occurrence_date
        (the original seed). They never matched after the first completion, so
        the function always reset next_due_date back to the seed date — which
        was now in the past — making every chore appear overdue after a restart.
        """
        # Simulate state as it would be loaded from storage after a completion:
        # the chore was completed yesterday, next due in 6 days, status=complete.
        coordinator = _make_coordinator_for_update(
            {
                "status": CHORE_STATUS_COMPLETE,
                "next_due_date": datetime(2026, 9, 5, 0, 0),  # future next due
                "last_completed_date": datetime(2026, 8, 29, 0, 0),
                "completion_count": 2,
                # applied_first_occurrence_date absent (pre-fix storage)
            }
        )
        coordinator._chores["test_chore"]["config"] = {
            "chore_name": "Tooth Brush - Change Head",
            "recurrence_type": "interval",
            "pattern_interval": 7,
            "interval_unit": "days",
            "first_occurrence_date": "2026-05-28",  # original seed, months ago
        }

        # Mimic what async_load_persisted_state does: stamp applied_first_occurrence_date
        # on first load when it is absent (migration path).
        from custom_components.sh_chore_tracker.const import CONF_FIRST_OCCURRENCE_DATE
        from custom_components.sh_chore_tracker.date_utils import coerce_date

        state = coordinator._chores["test_chore"]["state"]
        config = coordinator._chores["test_chore"]["config"]
        if state.get("next_due_date") and not state.get("applied_first_occurrence_date"):
            seed = coerce_date(config.get(CONF_FIRST_OCCURRENCE_DATE))
            if seed is not None:
                state["applied_first_occurrence_date"] = seed

        with patch(
            "custom_components.sh_chore_tracker.dt_util.now",
            return_value=datetime(2026, 8, 30, 9, 0, tzinfo=datetime.now().astimezone().tzinfo),
        ):
            changed = coordinator._apply_chore_first_occurrence_update(
                coordinator._chores["test_chore"]
            )

        assert changed is False, "State must not be reset on restart after completion"
        state = coordinator._chores["test_chore"]["state"]
        assert state["status"] == CHORE_STATUS_COMPLETE
        assert state["next_due_date"] == datetime(2026, 9, 5, 0, 0)


class TestRecurrenceEngine:
    """Test suite for RecurrenceEngine with all-day event model."""

    def setup_method(self):
        """Set up test instance."""
        self.engine = RecurrenceEngine()
        self.test_date = datetime(2024, 1, 1)  # Monday, Jan 1, 2024

    # INTERVAL RECURRENCE TESTS
    def test_interval_days(self):
        """Test interval recurrence with days."""
        config = {
            "recurrence_type": "interval",
            "pattern_interval": 7,
            "interval_unit": "days",
        }

        result = self.engine.calculate_next_due_date(config, self.test_date)
        expected = datetime(2024, 1, 8)

        _assert_same_instant(result, expected)
        assert result.time() == datetime.min.time()  # Should be start of day

    def test_interval_weeks(self):
        """Test interval recurrence with weeks."""
        config = {
            "recurrence_type": "interval",
            "pattern_interval": 2,
            "interval_unit": "weeks",
        }

        result = self.engine.calculate_next_due_date(config, self.test_date)
        expected = datetime(2024, 1, 15)

        _assert_same_instant(result, expected)

    def test_interval_months(self):
        """Test interval recurrence with months."""
        config = {
            "recurrence_type": "interval",
            "pattern_interval": 3,
            "interval_unit": "months",
        }

        result = self.engine.calculate_next_due_date(config, self.test_date)
        expected = datetime(2024, 4, 1)

        _assert_same_instant(result, expected)

    def test_interval_months_smart_day(self):
        """Test interval months with smart day handling (Jan 31 -> Feb 29)."""
        config = {
            "recurrence_type": "interval",
            "pattern_interval": 1,
            "interval_unit": "months",
        }

        test_date = datetime(2024, 1, 31)  # Jan 31, 2024
        result = self.engine.calculate_next_due_date(config, test_date)
        expected = datetime(2024, 2, 29)  # Feb 29 (2024 is leap year)

        _assert_same_instant(result, expected)

    def test_interval_years(self):
        """Test interval recurrence with years."""
        config = {
            "recurrence_type": "interval",
            "pattern_interval": 2,
            "interval_unit": "years",
        }

        result = self.engine.calculate_next_due_date(config, self.test_date)
        expected = datetime(2026, 1, 1)

        _assert_same_instant(result, expected)

    # WEEKLY RECURRENCE TESTS
    def test_weekly_single_day(self):
        """Test weekly recurrence on single day."""
        config = {
            "recurrence_type": "weekly",
            "pattern_interval": 1,
            "weekly_days": ["monday"],
        }

        result = self.engine.calculate_next_due_date(config, self.test_date)
        expected = datetime(2024, 1, 8)  # Next Monday

        _assert_same_instant(result, expected)

    def test_weekly_multiple_days(self):
        """Test weekly recurrence on multiple days."""
        config = {
            "recurrence_type": "weekly",
            "pattern_interval": 1,
            "weekly_days": ["monday", "friday"],
        }

        # Complete on Monday, next should be Friday of same week
        result = self.engine.calculate_next_due_date(config, self.test_date)
        expected = datetime(2024, 1, 5)  # Friday Jan 5

        _assert_same_instant(result, expected)

    def test_weekly_bi_weekly(self):
        """Test bi-weekly recurrence."""
        config = {
            "recurrence_type": "weekly",
            "pattern_interval": 2,
            "weekly_days": ["wednesday"],
        }

        result = self.engine.calculate_next_due_date(config, self.test_date)
        expected = datetime(2024, 1, 17)  # Wednesday 2 weeks later

        _assert_same_instant(result, expected)

    def test_weekly_string_format(self):
        """Test weekly days as string format."""
        config = {
            "recurrence_type": "weekly",
            "pattern_interval": 1,
            "weekly_days": "monday,friday",  # String format
        }

        result = self.engine.calculate_next_due_date(config, self.test_date)
        expected = datetime(2024, 1, 5)  # Friday Jan 5

        _assert_same_instant(result, expected)

    # MONTHLY RECURRENCE TESTS
    def test_monthly_normal_day(self):
        """Test monthly recurrence on normal day."""
        config = {
            "recurrence_type": "monthly",
            "pattern_interval": 1,
            "monthly_day": 15,
        }

        result = self.engine.calculate_next_due_date(config, self.test_date)
        expected = datetime(2024, 2, 15)  # Feb 15

        _assert_same_instant(result, expected)

    def test_monthly_last_day_smart_handling(self):
        """Test monthly recurrence with smart day handling (31st -> last day of month)."""
        config = {
            "recurrence_type": "monthly",
            "pattern_interval": 1,
            "monthly_day": 31,
        }

        test_date = datetime(2024, 1, 31)
        result = self.engine.calculate_next_due_date(config, test_date)
        expected = datetime(2024, 2, 29)  # Feb 29 (2024 is leap year)

        _assert_same_instant(result, expected)

    def test_monthly_quarterly(self):
        """Test quarterly (every 3 months) recurrence."""
        config = {"recurrence_type": "monthly", "pattern_interval": 3, "monthly_day": 1}

        result = self.engine.calculate_next_due_date(config, self.test_date)
        expected = datetime(2024, 4, 1)  # April 1

        _assert_same_instant(result, expected)

    def test_monthly_ordinal_weekday(self):
        """Test monthly recurrence using ordinal weekday rules."""
        config = {
            "recurrence_type": "monthly",
            "pattern_interval": 1,
            "monthly_mode": MONTHLY_MODE_ORDINAL_WEEKDAY,
            "monthly_ordinal": "first",
            "monthly_weekday": "monday",
        }

        result = self.engine.calculate_next_due_date(config, datetime(2024, 1, 1))
        expected = datetime(2024, 2, 5)

        _assert_same_instant(result, expected)

    def test_monthly_ordinal_skips_missing_fifth_weekday(self):
        """Test monthly recurrence skips months without the requested 5th weekday."""
        config = {
            "recurrence_type": "monthly",
            "pattern_interval": 1,
            "monthly_mode": MONTHLY_MODE_ORDINAL_WEEKDAY,
            "monthly_ordinal": "fifth",
            "monthly_weekday": "monday",
        }

        result = self.engine.calculate_next_due_date(config, datetime(2024, 1, 1))
        expected = datetime(2024, 4, 29)

        _assert_same_instant(result, expected)

    def test_monthly_ordinal_every_two_months(self):
        """Test monthly ordinal recurrence supports pattern_interval greater than one."""
        config = {
            "recurrence_type": "monthly",
            "pattern_interval": 2,
            "monthly_mode": MONTHLY_MODE_ORDINAL_WEEKDAY,
            "monthly_ordinal": "second",
            "monthly_weekday": "friday",
        }

        result = self.engine.calculate_next_due_date(config, datetime(2026, 6, 12))
        expected = datetime(2026, 8, 14)

        _assert_same_instant(result, expected)

    # YEARLY RECURRENCE TESTS
    def test_yearly_normal_date(self):
        """Test yearly recurrence on normal date."""
        config = {
            "recurrence_type": "yearly",
            "pattern_interval": 1,
            "yearly_month": 3,
            "yearly_day": 15,
        }

        result = self.engine.calculate_next_due_date(config, self.test_date)
        expected = datetime(2025, 3, 15)  # March 15, 2025

        _assert_same_instant(result, expected)

    def test_yearly_leap_day_handling(self):
        """Test yearly recurrence with leap day handling."""
        config = {
            "recurrence_type": "yearly",
            "pattern_interval": 1,
            "yearly_month": 2,
            "yearly_day": 29,
        }

        test_date = datetime(2024, 2, 29)  # Leap day 2024
        result = self.engine.calculate_next_due_date(config, test_date)
        expected = datetime(2025, 2, 28)  # Feb 28, 2025 (non-leap year)

        _assert_same_instant(result, expected)

    def test_yearly_bi_annual(self):
        """Test bi-annual (every 2 years) recurrence."""
        config = {
            "recurrence_type": "yearly",
            "pattern_interval": 2,
            "yearly_month": 12,
            "yearly_day": 25,
        }

        result = self.engine.calculate_next_due_date(config, self.test_date)
        expected = datetime(2026, 12, 25)  # Dec 25, 2026

        _assert_same_instant(result, expected)

    # VALIDATION TESTS
    def test_validate_interval_config(self):
        """Test validation for interval recurrence."""
        # Valid config
        valid_config = {
            "recurrence_type": "interval",
            "pattern_interval": 7,
            "interval_unit": "days",
        }
        assert self.engine.validate_recurrence_config(valid_config) is True

        # Invalid interval unit
        invalid_config = {
            "recurrence_type": "interval",
            "pattern_interval": 7,
            "interval_unit": "invalid",
        }
        assert self.engine.validate_recurrence_config(invalid_config) is False

        # Invalid pattern_interval (negative)
        invalid_config = {
            "recurrence_type": "interval",
            "pattern_interval": -1,
            "interval_unit": "days",
        }
        assert self.engine.validate_recurrence_config(invalid_config) is False

        # Invalid pattern_interval (too large for days)
        invalid_config = {
            "recurrence_type": "interval",
            "pattern_interval": 1000,
            "interval_unit": "days",
        }
        assert self.engine.validate_recurrence_config(invalid_config) is False

    def test_validate_weekly_config(self):
        """Test validation for weekly recurrence."""
        # Valid config
        valid_config = {
            "recurrence_type": "weekly",
            "pattern_interval": 2,
            "weekly_days": ["monday", "friday"],
        }
        assert self.engine.validate_recurrence_config(valid_config) is True

        # Invalid day name
        invalid_config = {
            "recurrence_type": "weekly",
            "pattern_interval": 1,
            "weekly_days": ["invalid_day"],
        }
        assert self.engine.validate_recurrence_config(invalid_config) is False

        # Empty weekly_days
        invalid_config = {
            "recurrence_type": "weekly",
            "pattern_interval": 1,
            "weekly_days": [],
        }
        assert self.engine.validate_recurrence_config(invalid_config) is False

        # Invalid pattern_interval (too large)
        invalid_config = {
            "recurrence_type": "weekly",
            "pattern_interval": 100,
            "weekly_days": ["monday"],
        }
        assert self.engine.validate_recurrence_config(invalid_config) is False

    def test_validate_monthly_config(self):
        """Test validation for monthly recurrence."""
        # Valid config
        valid_config = {
            "recurrence_type": "monthly",
            "pattern_interval": 3,
            "monthly_day": 15,
        }
        assert self.engine.validate_recurrence_config(valid_config) is True

        ordinal_config = {
            "recurrence_type": "monthly",
            "pattern_interval": 1,
            "monthly_mode": MONTHLY_MODE_ORDINAL_WEEKDAY,
            "monthly_ordinal": "last",
            "monthly_weekday": "friday",
        }
        assert self.engine.validate_recurrence_config(ordinal_config) is True

        # Invalid monthly_day (too low)
        invalid_config = {
            "recurrence_type": "monthly",
            "pattern_interval": 1,
            "monthly_day": 0,
        }
        assert self.engine.validate_recurrence_config(invalid_config) is False

        # Invalid monthly_day (too high)
        invalid_config = {
            "recurrence_type": "monthly",
            "pattern_interval": 1,
            "monthly_day": 32,
        }
        assert self.engine.validate_recurrence_config(invalid_config) is False

        invalid_ordinal_config = {
            "recurrence_type": "monthly",
            "pattern_interval": 1,
            "monthly_mode": MONTHLY_MODE_ORDINAL_WEEKDAY,
            "monthly_ordinal": "invalid",
            "monthly_weekday": "friday",
        }
        assert self.engine.validate_recurrence_config(invalid_ordinal_config) is False

    def test_validate_yearly_config(self):
        """Test validation for yearly recurrence."""
        # Valid config
        valid_config = {
            "recurrence_type": "yearly",
            "pattern_interval": 2,
            "yearly_month": 6,
            "yearly_day": 15,
        }
        assert self.engine.validate_recurrence_config(valid_config) is True

        # Invalid yearly_month
        invalid_config = {
            "recurrence_type": "yearly",
            "pattern_interval": 1,
            "yearly_month": 13,
            "yearly_day": 15,
        }
        assert self.engine.validate_recurrence_config(invalid_config) is False

        # Invalid yearly_day
        invalid_config = {
            "recurrence_type": "yearly",
            "pattern_interval": 1,
            "yearly_month": 6,
            "yearly_day": 32,
        }
        assert self.engine.validate_recurrence_config(invalid_config) is False

    # DESCRIPTION TESTS
    def test_get_description_interval(self):
        """Test description generation for interval recurrence."""
        config = {
            "recurrence_type": "interval",
            "pattern_interval": 1,
            "interval_unit": "days",
        }
        description = self.engine.get_recurrence_description(config)
        assert description == "Every day"

        config["pattern_interval"] = 7
        description = self.engine.get_recurrence_description(config)
        assert description == "Every 7 days"

        config["interval_unit"] = "weeks"
        config["pattern_interval"] = 2
        description = self.engine.get_recurrence_description(config)
        assert description == "Every 2 weeks"

    def test_get_description_weekly(self):
        """Test description generation for weekly recurrence."""
        config = {
            "recurrence_type": "weekly",
            "pattern_interval": 1,
            "weekly_days": ["monday"],
        }
        description = self.engine.get_recurrence_description(config)
        assert description == "Every Monday"

        config["weekly_days"] = ["monday", "friday"]
        description = self.engine.get_recurrence_description(config)
        assert description == "Every Monday and Friday"

        config["pattern_interval"] = 2
        description = self.engine.get_recurrence_description(config)
        assert description == "Every 2 weeks on Monday and Friday"

    def test_get_description_monthly(self):
        """Test description generation for monthly recurrence."""
        config = {"recurrence_type": "monthly", "pattern_interval": 1, "monthly_day": 1}
        description = self.engine.get_recurrence_description(config)
        assert description == "Monthly on the 1st"

        config["monthly_day"] = 2
        description = self.engine.get_recurrence_description(config)
        assert description == "Monthly on the 2nd"

        config["monthly_day"] = 3
        description = self.engine.get_recurrence_description(config)
        assert description == "Monthly on the 3rd"

        config["monthly_day"] = 15
        description = self.engine.get_recurrence_description(config)
        assert description == "Monthly on the 15th"

        config["pattern_interval"] = 3
        description = self.engine.get_recurrence_description(config)
        assert description == "Every 3 months on the 15th"

        config = {
            "recurrence_type": "monthly",
            "pattern_interval": 1,
            "monthly_mode": MONTHLY_MODE_ORDINAL_WEEKDAY,
            "monthly_ordinal": "last",
            "monthly_weekday": "friday",
        }
        description = self.engine.get_recurrence_description(config)
        assert description == "Monthly on the Last Friday"

    def test_get_description_yearly(self):
        """Test description generation for yearly recurrence."""
        config = {
            "recurrence_type": "yearly",
            "pattern_interval": 1,
            "yearly_month": 3,
            "yearly_day": 15,
        }
        description = self.engine.get_recurrence_description(config)
        assert description == "Every March 15"

        config["pattern_interval"] = 2
        description = self.engine.get_recurrence_description(config)
        assert description == "Every 2 years on March 15"

    # EDGE CASE TESTS
    def test_date_input_handling(self):
        """Test handling of date vs datetime input."""
        config = {
            "recurrence_type": "interval",
            "pattern_interval": 7,
            "interval_unit": "days",
        }

        # Test with date object
        test_date_obj = date(2024, 1, 1)
        result = self.engine.calculate_next_due_date(config, test_date_obj)
        expected = datetime(2024, 1, 8)
        _assert_same_instant(result, expected)

    def test_february_29_edge_cases(self):
        """Test edge cases around February 29th."""
        config = {
            "recurrence_type": "monthly",
            "pattern_interval": 1,
            "monthly_day": 29,
        }

        # From Feb 29 in leap year
        test_date = datetime(2024, 2, 29)
        result = self.engine.calculate_next_due_date(config, test_date)
        expected = datetime(2024, 3, 29)  # March has 29th
        _assert_same_instant(result, expected)

        # From Jan 29 going to February in leap year
        test_date = datetime(2024, 1, 29)
        result = self.engine.calculate_next_due_date(config, test_date)
        expected = datetime(2024, 2, 29)  # Feb 29 exists in 2024
        _assert_same_instant(result, expected)

        # From Jan 29 going to February in non-leap year
        test_date = datetime(2023, 1, 29)
        result = self.engine.calculate_next_due_date(config, test_date)
        expected = datetime(2023, 2, 28)  # Feb 28 in non-leap year
        _assert_same_instant(result, expected)

    def test_monthly_31st_rolls_to_month_end_then_recovers(self):
        """Test 31st-of-month rules roll to month end and continue with 31st when available."""
        config = {
            "recurrence_type": "monthly",
            "pattern_interval": 1,
            "monthly_day": 31,
        }

        # March 31 -> April 30 (smart month-end fallback)
        result = self.engine.calculate_next_due_date(config, datetime(2026, 3, 31))
        expected = datetime(2026, 4, 30)
        _assert_same_instant(result, expected)

        # April 30 -> May 31 (returns to configured day when it exists)
        result = self.engine.calculate_next_due_date(config, datetime(2026, 4, 30))
        expected = datetime(2026, 5, 31)
        _assert_same_instant(result, expected)
