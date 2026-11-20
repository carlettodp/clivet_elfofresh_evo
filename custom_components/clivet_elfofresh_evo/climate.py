"""Climate platform for Clivet ELFOFresh EVO."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CLIVET_MODE_AUTO,
    CLIVET_MODE_COOL,
    CLIVET_MODE_FAN,
    CLIVET_MODE_HEAT,
    REG_MODE_SET,
    REG_POWER,
    REG_SILENT_MODE_SET,
    REG_TARGET_TEMP,
    SILENT_MODE_NORMAL,
    SILENT_MODE_OFF,
    SILENT_MODE_SUPER,
)
from .coordinator import ClivetConfigEntry, ClivetDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PRESET_NORMAL = "normal"
PRESET_SILENT = "silent"
PRESET_SUPER_SILENT = "super_silent"

HA_TO_CLIVET_MODE = {
    HVACMode.COOL: CLIVET_MODE_COOL,
    HVACMode.HEAT: CLIVET_MODE_HEAT,
    HVACMode.FAN_ONLY: CLIVET_MODE_FAN,
    HVACMode.AUTO: CLIVET_MODE_AUTO,
}

CLIVET_TO_HA_MODE = {
    CLIVET_MODE_COOL: HVACMode.COOL,
    CLIVET_MODE_HEAT: HVACMode.HEAT,
    CLIVET_MODE_FAN: HVACMode.FAN_ONLY,
    CLIVET_MODE_AUTO: HVACMode.AUTO,
}

PRESET_TO_CLIVET_SILENT = {
    PRESET_NORMAL: SILENT_MODE_OFF,
    PRESET_SILENT: SILENT_MODE_NORMAL,
    PRESET_SUPER_SILENT: SILENT_MODE_SUPER,
}

CLIVET_SILENT_TO_PRESET = {
    SILENT_MODE_OFF: PRESET_NORMAL,
    SILENT_MODE_NORMAL: PRESET_SILENT,
    SILENT_MODE_SUPER: PRESET_SUPER_SILENT,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ClivetConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Clivet VMC climate entity."""
    coordinator = entry.runtime_data
    async_add_entities([ClivetClimateEntity(coordinator)])


class ClivetClimateEntity(CoordinatorEntity[ClivetDataUpdateCoordinator], ClimateEntity):
    """Representation of the Clivet VMC Climate entity."""

    _attr_has_entity_name = True
    _attr_translation_key = "vmc"
    _attr_name = None  # Main entity of the device
    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_min_temp = 17.0
    _attr_max_temp = 28.0
    _attr_target_temperature_step = 1.0
    _attr_hvac_modes = [
        HVACMode.OFF,
        HVACMode.COOL,
        HVACMode.HEAT,
        HVACMode.FAN_ONLY,
        HVACMode.AUTO,
    ]
    _attr_preset_modes = [
        PRESET_NORMAL,
        PRESET_SILENT,
        PRESET_SUPER_SILENT,
    ]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.PRESET_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )

    def __init__(self, coordinator: ClivetDataUpdateCoordinator) -> None:
        """Initialize the climate entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.unique_id}_climate"
        self._attr_device_info = coordinator.device_info

    @property
    def native_current_temperature(self) -> float | None:
        """Return the current indoor temperature."""
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("indoor_air_temp")

    @property
    def native_target_temperature(self) -> float | None:
        """Return the target setpoint temperature."""
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("target_temp")

    @property
    def hvac_mode(self) -> HVACMode:
        """Return current HVAC mode."""
        if not self.coordinator.data:
            return HVACMode.OFF

        power = self.coordinator.data.get("power", False)
        unit_on = self.coordinator.data.get("unit_on_index", False)
        op_mode = self.coordinator.data.get("operating_mode", 0)

        # If everything indicates off, return OFF
        if not power and not unit_on and op_mode == 0:
            return HVACMode.OFF

        mode_set = self.coordinator.data.get("mode_set")
        mode = mode_set if (mode_set and mode_set in CLIVET_TO_HA_MODE) else op_mode
        return CLIVET_TO_HA_MODE.get(mode, HVACMode.AUTO)

    @property
    def hvac_action(self) -> HVACAction:
        """Return current HVAC action."""
        if not self.coordinator.data:
            return HVACAction.OFF

        power = self.coordinator.data.get("power", False)
        unit_on = self.coordinator.data.get("unit_on_index", False)
        op_mode = self.coordinator.data.get("operating_mode", 0)

        if not power and not unit_on and op_mode == 0:
            return HVACAction.OFF

        if self.coordinator.data.get("defrost_active", False):
            return HVACAction.DEFROSTING

        compressor_rps = self.coordinator.data.get("compressor_rps", 0)

        if compressor_rps > 0:
            if op_mode == CLIVET_MODE_COOL:
                return HVACAction.COOLING
            if op_mode == CLIVET_MODE_HEAT:
                return HVACAction.HEATING
            return HVACAction.FAN

        if op_mode == CLIVET_MODE_FAN:
            return HVACAction.FAN

        return HVACAction.IDLE

    @property
    def preset_mode(self) -> str:
        """Return current preset mode (silent mode)."""
        if not self.coordinator.data:
            return PRESET_NORMAL
        silent_mode = self.coordinator.data.get("silent_mode", SILENT_MODE_OFF)
        return CLIVET_SILENT_TO_PRESET.get(silent_mode, PRESET_NORMAL)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        if (temp := kwargs.get(ATTR_TEMPERATURE)) is not None:
            temp_int = int(round(temp))
            # Bound check: 17 to 28 °C
            temp_int = max(17, min(28, temp_int))
            await self.coordinator.async_write_register(REG_TARGET_TEMP, temp_int)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target HVAC mode."""
        if hvac_mode == HVACMode.OFF:
            await self.coordinator.async_write_register(REG_POWER, 0)
            return

        clivet_mode = HA_TO_CLIVET_MODE.get(hvac_mode)
        if clivet_mode is not None:
            # First ensure unit is powered on without intermediate poll
            is_powered = self.coordinator.data.get("power", False) if self.coordinator.data else False
            if not is_powered:
                await self.coordinator.async_write_register(REG_POWER, 1, refresh=False)
                await asyncio.sleep(0.1)
            # Then set mode and trigger refresh
            await self.coordinator.async_write_register(REG_MODE_SET, clivet_mode, refresh=True)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode (silent mode setting)."""
        clivet_silent = PRESET_TO_CLIVET_SILENT.get(preset_mode)
        if clivet_silent is not None:
            await self.coordinator.async_write_register(REG_SILENT_MODE_SET, clivet_silent)

    async def async_turn_on(self) -> None:
        """Turn on the unit."""
        await self.coordinator.async_write_register(REG_POWER, 1)

    async def async_turn_off(self) -> None:
        """Turn off the unit."""
        await self.coordinator.async_write_register(REG_POWER, 0)
