"""Select platform for Clivet ELFOFresh EVO."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DEHUM_MODE_ECO,
    DEHUM_MODE_LOW,
    DEHUM_MODE_STD,
    REG_DEHUM_MODE_SET,
    REG_SILENT_MODE_SET,
    REG_TARGET_FAN_SPEED,
    SILENT_MODE_NORMAL,
    SILENT_MODE_OFF,
    SILENT_MODE_SUPER,
)
from .coordinator import ClivetConfigEntry, ClivetDataUpdateCoordinator

SILENT_MODE_MAP = {
    SILENT_MODE_OFF: "off",
    SILENT_MODE_NORMAL: "silent",
    SILENT_MODE_SUPER: "super_silent",
}
REV_SILENT_MODE_MAP = {v: k for k, v in SILENT_MODE_MAP.items()}

DEHUM_MODE_MAP = {
    DEHUM_MODE_STD: "standard",
    DEHUM_MODE_LOW: "low",
    DEHUM_MODE_ECO: "eco",
}
REV_DEHUM_MODE_MAP = {v: k for k, v in DEHUM_MODE_MAP.items()}


@dataclass(frozen=True, kw_only=True)
class ClivetSelectEntityDescription(SelectEntityDescription):
    """Class describing Clivet select entities."""

    current_option_fn: Callable[[dict[str, Any]], str | None]
    set_option_fn: Callable[[ClivetDataUpdateCoordinator, str], Any]


SELECT_DESCRIPTIONS: tuple[ClivetSelectEntityDescription, ...] = (
    ClivetSelectEntityDescription(
        key="silent_mode",
        translation_key="silent_mode",
        icon="mdi:volume-mute",
        options=["off", "silent", "super_silent"],
        current_option_fn=lambda data: SILENT_MODE_MAP.get(data.get("silent_mode", 0)),
        set_option_fn=lambda coord, opt: coord.async_write_register(
            REG_SILENT_MODE_SET, REV_SILENT_MODE_MAP.get(opt, 0)
        ),
    ),
    ClivetSelectEntityDescription(
        key="dehumidification_mode",
        translation_key="dehumidification_mode",
        icon="mdi:water-percent",
        options=["standard", "low", "eco"],
        current_option_fn=lambda data: DEHUM_MODE_MAP.get(data.get("dehum_mode", 0)),
        set_option_fn=lambda coord, opt: coord.async_write_register(
            REG_DEHUM_MODE_SET, REV_DEHUM_MODE_MAP.get(opt, 0)
        ),
    ),
    ClivetSelectEntityDescription(
        key="target_fan_speed_select",
        translation_key="target_fan_speed_select",
        icon="mdi:fan-speed-1",
        options=["3", "4", "5", "6", "7"],
        current_option_fn=lambda data: str(data.get("target_fan_speed", "6")),
        set_option_fn=lambda coord, opt: coord.async_write_register(
            REG_TARGET_FAN_SPEED, int(opt)
        ),
    ),
)


class ClivetSelectEntity(CoordinatorEntity[ClivetDataUpdateCoordinator], SelectEntity):
    """Representation of a Clivet VMC select entity."""

    entity_description: ClivetSelectEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ClivetDataUpdateCoordinator,
        description: ClivetSelectEntityDescription,
    ) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.unique_id}_{description.key}"
        self._attr_device_info = coordinator.device_info

    @property
    def current_option(self) -> str | None:
        """Return the selected entity option."""
        if not self.coordinator.data:
            return None
        return self.entity_description.current_option_fn(self.coordinator.data)

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        await self.entity_description.set_option_fn(self.coordinator, option)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ClivetConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Clivet VMC select entities."""
    coordinator = entry.runtime_data
    async_add_entities(
        ClivetSelectEntity(coordinator, description)
        for description in SELECT_DESCRIPTIONS
    )
