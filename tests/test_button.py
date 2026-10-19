"""Tests for chore action buttons."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.components.button import ButtonEntityDescription
from homeassistant.core import Context
from homeassistant.exceptions import ServiceValidationError

from custom_components.chore_tracker.button import (
    BUTTON_DESCRIPTIONS,
    ChoreActionButton,
    async_setup_entry,
)
from custom_components.chore_tracker.const import DOMAIN, SUBENTRY_TYPE_CHORE


@pytest.fixture
def coordinator() -> MagicMock:
    """Provide a coordinator resolving a renamed sensor."""
    coordinator = MagicMock()
    coordinator.hass.services.async_call = AsyncMock()
    coordinator.entity_id_for_chore.return_value = "sensor.my_renamed_chore"
    return coordinator


@pytest.fixture
def subentry() -> MagicMock:
    """Provide a chore's stable identity and configuration."""
    return MagicMock(
        unique_id="chore_1",
        subentry_id="subentry_1",
        data={"chore_name": "Laundry"},
    )


@pytest.mark.parametrize("description", BUTTON_DESCRIPTIONS, ids=lambda item: item.key)
@pytest.mark.asyncio
async def test_button_calls_existing_action(
    coordinator: MagicMock,
    subentry: MagicMock,
    description: ButtonEntityDescription,
) -> None:
    button = ChoreActionButton(coordinator, subentry, description)
    button.hass = coordinator.hass
    context = Context()
    button.async_set_context(context)

    await button.async_press()

    coordinator.entity_id_for_chore.assert_called_once_with("chore_1", subentry.data)
    coordinator.hass.services.async_call.assert_awaited_once_with(
        DOMAIN,
        description.key,
        {"entity_id": "sensor.my_renamed_chore"},
        blocking=True,
        context=context,
    )
    assert button.unique_id == f"chore_chore_1_{description.key}"
    assert button.device_info["identifiers"] == {(DOMAIN, "chore_1")}


@pytest.mark.asyncio
async def test_setup_registers_buttons_only_for_chore_subentries(
    coordinator: MagicMock, subentry: MagicMock
) -> None:
    hass = coordinator.hass
    hass.data = {DOMAIN: {"hub_entry": coordinator}}
    entry = MagicMock(entry_id="hub_entry")
    second_chore = MagicMock(
        unique_id="chore_2", subentry_id="subentry_2", data={"chore_name": "Dishes"}
    )
    entry.get_subentries_of_type.return_value = [subentry, second_chore]
    add_entities = MagicMock()

    await async_setup_entry(hass, entry, add_entities)

    entry.get_subentries_of_type.assert_called_once_with(SUBENTRY_TYPE_CHORE)
    assert add_entities.call_count == 2
    first_call, second_call = add_entities.call_args_list
    assert first_call.kwargs["config_subentry_id"] == "subentry_1"
    assert second_call.kwargs["config_subentry_id"] == "subentry_2"
    assert len(first_call.args[0]) == 4
    assert len(second_call.args[0]) == 4
    assert {button.chore_id for button in first_call.args[0]} == {"chore_1"}
    assert {button.chore_id for button in second_call.args[0]} == {"chore_2"}
    assert len({button.unique_id for button in first_call.args[0] + second_call.args[0]}) == 8


@pytest.mark.asyncio
async def test_button_surfaces_action_failure(coordinator: MagicMock, subentry: MagicMock) -> None:
    button = ChoreActionButton(coordinator, subentry, BUTTON_DESCRIPTIONS[0])
    button.hass = coordinator.hass
    coordinator.hass.services.async_call.side_effect = ServiceValidationError("Chore action failed")

    with pytest.raises(ServiceValidationError, match="Chore action failed"):
        await button.async_press()


def test_button_is_unavailable_when_coordinator_update_fails(
    coordinator: MagicMock, subentry: MagicMock
) -> None:
    coordinator.last_update_success = False
    button = ChoreActionButton(coordinator, subentry, BUTTON_DESCRIPTIONS[0])

    assert button.available is False
