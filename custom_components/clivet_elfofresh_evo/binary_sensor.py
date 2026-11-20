"""Binary sensor platform for Clivet ELFOFresh EVO."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import ClivetConfigEntry, ClivetDataUpdateCoordinator


@dataclass(frozen=True, kw_only=True)
class ClivetBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Class describing Clivet binary sensor entities."""

    value_fn: Callable[[dict[str, Any]], bool | None]


BINARY_SENSOR_DESCRIPTIONS: tuple[ClivetBinarySensorEntityDescription, ...] = (
    # From Register 124 (Operating mode)
    ClivetBinarySensorEntityDescription(
        key="defrost_active",
        translation_key="defrost_active",
        icon="mdi:snowflake-melt",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("defrost_active"),
    ),
    ClivetBinarySensorEntityDescription(
        key="silent_active",
        translation_key="silent_active",
        icon="mdi:volume-mute",
        value_fn=lambda data: data.get("silent_active"),
    ),
    ClivetBinarySensorEntityDescription(
        key="oil_return",
        translation_key="oil_return",
        icon="mdi:oil",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("oil_return"),
    ),
    ClivetBinarySensorEntityDescription(
        key="remote_on_off",
        translation_key="remote_on_off",
        icon="mdi:remote",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("remote_on_off"),
    ),
    ClivetBinarySensorEntityDescription(
        key="water_level_alarm",
        translation_key="water_level_alarm",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:water-alert",
        value_fn=lambda data: data.get("water_level_alarm"),
    ),
    ClivetBinarySensorEntityDescription(
        key="damper_open",
        translation_key="damper_open",
        device_class=BinarySensorDeviceClass.OPENING,
        icon="mdi:valve-open",
        value_fn=lambda data: data.get("damper_open"),
    ),
    ClivetBinarySensorEntityDescription(
        key="humidifier_on",
        translation_key="humidifier_on",
        icon="mdi:air-humidifier",
        value_fn=lambda data: data.get("humidifier_on"),
    ),
    # From Register 125 (Output status)
    ClivetBinarySensorEntityDescription(
        key="e_filter_active",
        translation_key="e_filter_active",
        icon="mdi:air-filter",
        value_fn=lambda data: data.get("e_filter_active"),
    ),
    ClivetBinarySensorEntityDescription(
        key="water_pump_active",
        translation_key="water_pump_active",
        icon="mdi:pump",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("water_pump_active"),
    ),
    ClivetBinarySensorEntityDescription(
        key="humidifier_active",
        translation_key="humidifier_active",
        icon="mdi:air-humidifier",
        value_fn=lambda data: data.get("humidifier_active"),
    ),
    ClivetBinarySensorEntityDescription(
        key="valve_4way_active",
        translation_key="valve_4way_active",
        icon="mdi:swap-horizontal-bold",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("valve_4way_active"),
    ),
    ClivetBinarySensorEntityDescription(
        key="exhaust_fan_power",
        translation_key="exhaust_fan_power",
        device_class=BinarySensorDeviceClass.RUNNING,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("exhaust_fan_power"),
    ),
    ClivetBinarySensorEntityDescription(
        key="supply_fan_power",
        translation_key="supply_fan_power",
        device_class=BinarySensorDeviceClass.RUNNING,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("supply_fan_power"),
    ),
    ClivetBinarySensorEntityDescription(
        key="system_error",
        translation_key="system_error",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("system_error"),
    ),
    ClivetBinarySensorEntityDescription(
        key="unit_on_index",
        translation_key="unit_on_index",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda data: data.get("unit_on_index"),
    ),
    ClivetBinarySensorEntityDescription(
        key="e_heater_active",
        translation_key="e_heater_active",
        icon="mdi:radiator",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("e_heater_active"),
    ),
)


class ClivetBinarySensorEntity(
    CoordinatorEntity[ClivetDataUpdateCoordinator], BinarySensorEntity
):
    """Representation of a Clivet VMC binary sensor."""

    entity_description: ClivetBinarySensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ClivetDataUpdateCoordinator,
        description: ClivetBinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.unique_id}_{description.key}"
        self._attr_device_info = coordinator.device_info

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        if not self.coordinator.data:
            return None
        return self.entity_description.value_fn(self.coordinator.data)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ClivetConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Clivet VMC binary sensor entities."""
    coordinator = entry.runtime_data
    async_add_entities(
        ClivetBinarySensorEntity(coordinator, description)
        for description in BINARY_SENSOR_DESCRIPTIONS
    )
