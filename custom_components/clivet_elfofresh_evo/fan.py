"""Fan platform for Clivet ELFOFresh EVO."""

from __future__ import annotations

import logging
import math
from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    REG_POWER,
    REG_TARGET_FAN_SPEED,
)
from .coordinator import ClivetConfigEntry, ClivetDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Settable fan speed range for Clivet VMC (SupFanSet: 3..7)
MIN_FAN_SPEED = 3
MAX_FAN_SPEED = 7
SPEED_STEPS = MAX_FAN_SPEED - MIN_FAN_SPEED + 1  # 5 steps


class ClivetFanEntity(CoordinatorEntity[ClivetDataUpdateCoordinator], FanEntity):
    """Representation of the Clivet VMC ventilation fan."""

    _attr_has_entity_name = True
    _attr_translation_key = "ventilation"
    _attr_supported_features = (
        FanEntityFeature.SET_SPEED
        | FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
    )

    def __init__(self, coordinator: ClivetDataUpdateCoordinator) -> None:
        """Initialize the fan entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.unique_id}_fan"
        self._attr_device_info = coordinator.device_info

    @property
    def is_on(self) -> bool:
        """Return true if the fan/unit is running."""
        if not self.coordinator.data:
            return False
        return bool(
            self.coordinator.data.get("power", False)
            or self.coordinator.data.get("unit_on_index", False)
            or self.coordinator.data.get("supply_fan_power", False)
        )

    @property
    def speed_count(self) -> int:
        """Return the number of speeds the fan supports."""
        return SPEED_STEPS

    @property
    def percentage(self) -> int | None:
        """Return current speed percentage based on target fan speed (3..7)."""
        if not self.coordinator.data:
            return None
        target_speed = self.coordinator.data.get("target_fan_speed")
        if target_speed is None:
            return None

        # Clamp target speed
        speed = max(MIN_FAN_SPEED, min(MAX_FAN_SPEED, target_speed))
        # Convert step 3..7 into percentage 20..100
        step_index = speed - MIN_FAN_SPEED + 1  # 1..5
        return int(round((step_index / SPEED_STEPS) * 100))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional fan state attributes."""
        if not self.coordinator.data:
            return {}
        return {
            "target_speed_level": self.coordinator.data.get("target_fan_speed"),
            "supply_fan_speed_feedback": self.coordinator.data.get("supply_fan_speed_raw"),
            "exhaust_fan_speed_feedback": self.coordinator.data.get("exhaust_fan_speed"),
            "supply_fan_power": self.coordinator.data.get("supply_fan_power"),
            "exhaust_fan_power": self.coordinator.data.get("exhaust_fan_power"),
        }

    async def async_set_percentage(self, percentage: int) -> None:
        """Set fan speed percentage."""
        if percentage == 0:
            await self.async_turn_off()
            return

        # Ensure unit is on
        is_powered = self.coordinator.data.get("power", False) if self.coordinator.data else False
        if not is_powered:
            await self.coordinator.async_write_register(REG_POWER, 1)

        # Map 1..100% to 3..7
        step_index = math.ceil((percentage / 100.0) * SPEED_STEPS)
        step_index = max(1, min(SPEED_STEPS, step_index))
        target_speed = MIN_FAN_SPEED + step_index - 1

        await self.coordinator.async_write_register(REG_TARGET_FAN_SPEED, target_speed)

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Turn on the ventilation unit."""
        await self.coordinator.async_write_register(REG_POWER, 1)
        if percentage is not None:
            await self.async_set_percentage(percentage)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the ventilation unit."""
        await self.coordinator.async_write_register(REG_POWER, 0)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ClivetConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Clivet VMC fan entity."""
    coordinator = entry.runtime_data
    async_add_entities([ClivetFanEntity(coordinator)])
