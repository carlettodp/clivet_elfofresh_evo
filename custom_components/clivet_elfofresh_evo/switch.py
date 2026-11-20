"""Switch platform for Clivet ELFOFresh EVO."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.switch import (
    SwitchDeviceClass,
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    REG_ENABLE_E_FILTER,
    REG_ENABLE_HUMIDIFIER,
    REG_POWER,
)
from .coordinator import ClivetConfigEntry, ClivetDataUpdateCoordinator


@dataclass(frozen=True, kw_only=True)
class ClivetSwitchEntityDescription(SwitchEntityDescription):
    """Class describing Clivet switch entities."""

    is_on_fn: Callable[[dict[str, Any]], bool | None]
    turn_on_fn: Callable[[ClivetDataUpdateCoordinator], Any]
    turn_off_fn: Callable[[ClivetDataUpdateCoordinator], Any]


SWITCH_DESCRIPTIONS: tuple[ClivetSwitchEntityDescription, ...] = (
    ClivetSwitchEntityDescription(
        key="power",
        translation_key="power",
        device_class=SwitchDeviceClass.SWITCH,
        icon="mdi:power",
        is_on_fn=lambda data: bool(data.get("power") or data.get("unit_on_index")),
        turn_on_fn=lambda coord: coord.async_write_register(REG_POWER, 1),
        turn_off_fn=lambda coord: coord.async_write_register(REG_POWER, 0),
    ),
    ClivetSwitchEntityDescription(
        key="enable_e_filter",
        translation_key="enable_e_filter",
        entity_category=EntityCategory.CONFIG,
        icon="mdi:air-filter",
        is_on_fn=lambda data: data.get("e_filter_enabled"),
        turn_on_fn=lambda coord: coord.async_write_register(REG_ENABLE_E_FILTER, 1),
        turn_off_fn=lambda coord: coord.async_write_register(REG_ENABLE_E_FILTER, 0),
    ),
    ClivetSwitchEntityDescription(
        key="enable_humidifier",
        translation_key="enable_humidifier",
        entity_category=EntityCategory.CONFIG,
        icon="mdi:air-humidifier",
        is_on_fn=lambda data: data.get("humidifier_enabled"),
        turn_on_fn=lambda coord: coord.async_write_register(REG_ENABLE_HUMIDIFIER, 1),
        turn_off_fn=lambda coord: coord.async_write_register(REG_ENABLE_HUMIDIFIER, 0),
    ),
)


class ClivetSwitchEntity(CoordinatorEntity[ClivetDataUpdateCoordinator], SwitchEntity):
    """Representation of a Clivet VMC switch."""

    entity_description: ClivetSwitchEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ClivetDataUpdateCoordinator,
        description: ClivetSwitchEntityDescription,
    ) -> None:
        """Initialize the switch entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.unique_id}_{description.key}"
        self._attr_device_info = coordinator.device_info

    @property
    def is_on(self) -> bool | None:
        """Return true if switch is on."""
        if not self.coordinator.data:
            return None
        return self.entity_description.is_on_fn(self.coordinator.data)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the switch."""
        await self.entity_description.turn_on_fn(self.coordinator)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the switch."""
        await self.entity_description.turn_off_fn(self.coordinator)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ClivetConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Clivet VMC switch entities."""
    coordinator = entry.runtime_data
    async_add_entities(
        ClivetSwitchEntity(coordinator, description)
        for description in SWITCH_DESCRIPTIONS
    )
