"""Chore action buttons for the Chore Tracker integration."""

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import ChoreCoordinator
from .const import (
    DOMAIN,
    SERVICE_COMPLETE_CHORE,
    SERVICE_RESET_NEXT_DUE_DATE,
    SERVICE_SKIP_CHORE,
    SERVICE_SNOOZE_CHORE,
    SUBENTRY_TYPE_CHORE,
)

BUTTON_DESCRIPTIONS = (
    ButtonEntityDescription(
        key=SERVICE_COMPLETE_CHORE,
        translation_key="complete",
        icon="mdi:check",
    ),
    ButtonEntityDescription(
        key=SERVICE_SNOOZE_CHORE,
        translation_key="snooze",
        icon="mdi:sleep",
    ),
    ButtonEntityDescription(
        key=SERVICE_SKIP_CHORE,
        translation_key="skip",
        icon="mdi:skip-next",
    ),
    ButtonEntityDescription(
        key=SERVICE_RESET_NEXT_DUE_DATE,
        translation_key="reset",
        icon="mdi:calendar-refresh",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add action buttons to each chore device."""
    coordinator: ChoreCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    for subentry in config_entry.get_subentries_of_type(SUBENTRY_TYPE_CHORE):
        async_add_entities(
            [
                ChoreActionButton(coordinator, subentry, description)
                for description in BUTTON_DESCRIPTIONS
            ],
            config_subentry_id=subentry.subentry_id,
        )


class ChoreActionButton(CoordinatorEntity[ChoreCoordinator], ButtonEntity):
    """Run an existing action for one chore."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ChoreCoordinator,
        subentry: ConfigSubentry,
        description: ButtonEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._subentry = subentry
        self.chore_id = subentry.unique_id or subentry.subentry_id
        self._attr_unique_id = f"chore_{self.chore_id}_{description.key}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, self.chore_id)})

    async def async_press(self) -> None:
        """Run the action against the current registered chore sensor."""
        entity_id = self.coordinator.entity_id_for_chore(self.chore_id, dict(self._subentry.data))
        await self.hass.services.async_call(
            DOMAIN,
            self.entity_description.key,
            {ATTR_ENTITY_ID: entity_id},
            blocking=True,
            context=self._context,
        )
