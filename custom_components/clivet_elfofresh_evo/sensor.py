"""Sensor platform for Clivet ELFOFresh EVO."""

from __future__ import annotations

from dataclasses import dataclass
from time import monotonic
from typing import Any, Callable

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import ClivetConfigEntry, ClivetDataUpdateCoordinator

COMPRESSOR_POWER_SCALE = 1.36
FAN_POWER_MIN_SPEED_3 = 35.0
FAN_POWER_MAX_SPEED_7 = 90.0
FAN_POWER_STEP = (FAN_POWER_MAX_SPEED_7 - FAN_POWER_MIN_SPEED_3) / (7 - 3)  # 13.75 W per speed level
STANDBY_POWER = 5


def estimated_compressor_power(data: dict[str, Any] | None) -> int | None:
    """Estimate compressor input power in watts from one Modbus sample."""
    if not data:
        return None
    rps = data.get("compressor_rps", 0)
    current = data.get("current", 0)
    voltage = data.get("voltage")
    if voltage is None or current is None or rps <= 0 or current <= 0:
        return 0
    return round(voltage * current * COMPRESSOR_POWER_SCALE)


def estimated_vmc_power(data: dict[str, Any] | None) -> int | None:
    """Estimate total VMC input power in watts from fans, electronics, and compressor."""
    if not data:
        return None
    is_on = bool(data.get("power") or data.get("unit_on_index") or data.get("supply_fan_power"))
    if not is_on:
        return STANDBY_POWER

    fan_speed = data.get("target_fan_speed", 6)
    clamped_speed = max(3, min(7, fan_speed))
    fan_power = round(FAN_POWER_MIN_SPEED_3 + (clamped_speed - 3) * FAN_POWER_STEP)

    comp_power = estimated_compressor_power(data) or 0
    return fan_power + comp_power


@dataclass(frozen=True, kw_only=True)
class ClivetSensorEntityDescription(SensorEntityDescription):
    """Class describing Clivet sensor entities."""

    value_fn: Callable[[dict[str, Any]], Any]


SENSOR_DESCRIPTIONS: tuple[ClivetSensorEntityDescription, ...] = (
    # Temperatures
    ClivetSensorEntityDescription(
        key="indoor_air_temp",
        translation_key="indoor_air_temp",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("indoor_air_temp"),
    ),
    ClivetSensorEntityDescription(
        key="outdoor_air_temp",
        translation_key="outdoor_air_temp",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("outdoor_air_temp"),
    ),
    ClivetSensorEntityDescription(
        key="supply_air_temp",
        translation_key="supply_air_temp",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("supply_air_temp"),
    ),
    ClivetSensorEntityDescription(
        key="second_supply_temp",
        translation_key="second_supply_temp",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("second_supply_temp"),
    ),
    ClivetSensorEntityDescription(
        key="condensation_temp",
        translation_key="condensation_temp",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("condensation_temp"),
    ),
    ClivetSensorEntityDescription(
        key="evaporation_temp",
        translation_key="evaporation_temp",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("evaporation_temp"),
    ),
    ClivetSensorEntityDescription(
        key="discharge_temp",
        translation_key="discharge_temp",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("discharge_temp"),
    ),
    ClivetSensorEntityDescription(
        key="suction_temp",
        translation_key="suction_temp",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("suction_temp"),
    ),
    # Humidity
    ClivetSensorEntityDescription(
        key="supply_air_humidity",
        translation_key="supply_air_humidity",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("supply_air_humidity"),
    ),
    # Electrical
    ClivetSensorEntityDescription(
        key="current",
        translation_key="current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("current"),
    ),
    ClivetSensorEntityDescription(
        key="voltage",
        translation_key="voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("voltage"),
    ),
    ClivetSensorEntityDescription(
        key="estimated_power",
        translation_key="estimated_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=estimated_vmc_power,
    ),
    ClivetSensorEntityDescription(
        key="estimated_compressor_power",
        translation_key="estimated_compressor_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=estimated_compressor_power,
    ),
    # Operation
    ClivetSensorEntityDescription(
        key="compressor_rps",
        translation_key="compressor_rps",
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:engine",
        value_fn=lambda data: data.get("compressor_rps"),
    ),
    ClivetSensorEntityDescription(
        key="exv_opening",
        translation_key="exv_opening",
        icon="mdi:valve",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("exv_opening"),
    ),
    ClivetSensorEntityDescription(
        key="supply_fan_speed_raw",
        translation_key="supply_fan_speed_raw",
        icon="mdi:fan",
        value_fn=lambda data: data.get("supply_fan_speed_raw"),
    ),
    ClivetSensorEntityDescription(
        key="exhaust_fan_speed",
        translation_key="exhaust_fan_speed",
        icon="mdi:fan-chevron-up",
        value_fn=lambda data: data.get("exhaust_fan_speed"),
    ),
    ClivetSensorEntityDescription(
        key="compressor_time",
        translation_key="compressor_time",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:timer-outline",
        value_fn=lambda data: data.get("compressor_time"),
    ),
    ClivetSensorEntityDescription(
        key="eheater_output",
        translation_key="eheater_output",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:radiator",
        value_fn=lambda data: data.get("eheater_output"),
    ),
    # Diagnostics & Errors
    ClivetSensorEntityDescription(
        key="current_error",
        translation_key="current_error",
        icon="mdi:alert-circle-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("current_error"),
    ),
    ClivetSensorEntityDescription(
        key="history_error_1",
        translation_key="history_error_1",
        icon="mdi:history",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("history_error_1"),
    ),
    ClivetSensorEntityDescription(
        key="history_error_2",
        translation_key="history_error_2",
        icon="mdi:history",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("history_error_2"),
    ),
    ClivetSensorEntityDescription(
        key="history_error_3",
        translation_key="history_error_3",
        icon="mdi:history",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("history_error_3"),
    ),
    ClivetSensorEntityDescription(
        key="unit_size",
        translation_key="unit_size",
        icon="mdi:cube-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("unit_size"),
    ),
    ClivetSensorEntityDescription(
        key="main_sw_version",
        translation_key="main_sw_version",
        icon="mdi:chip",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("main_sw_version"),
    ),
    ClivetSensorEntityDescription(
        key="hmi_sw_version",
        translation_key="hmi_sw_version",
        icon="mdi:monitor-dashboard",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("hmi_sw_version"),
    ),
)


class ClivetSensorEntity(CoordinatorEntity[ClivetDataUpdateCoordinator], SensorEntity):
    """Representation of a Clivet VMC sensor."""

    entity_description: ClivetSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ClivetDataUpdateCoordinator,
        description: ClivetSensorEntityDescription,
    ) -> None:
        """Initialize the sensor entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.unique_id}_{description.key}"
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> Any:
        """Return the native sensor value."""
        if not self.coordinator.data:
            return None
        return self.entity_description.value_fn(self.coordinator.data)


class ClivetVmcEnergySensor(CoordinatorEntity[ClivetDataUpdateCoordinator], RestoreSensor):
    """Accumulate total estimated VMC energy (fans, electronics, compressor) in kWh."""

    _attr_has_entity_name = True
    _attr_translation_key = "estimated_energy"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_suggested_display_precision = 3

    def __init__(self, coordinator: ClivetDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.unique_id}_estimated_energy"
        self._attr_device_info = coordinator.device_info
        self._attr_native_value = 0.0
        self._previous_sample: tuple[float, int] | None = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        previous = await self.async_get_last_sensor_data()
        if previous is not None and previous.native_value is not None:
            self._attr_native_value = float(previous.native_value)
        self._previous_sample = None
        self._record_sample()

    def _record_sample(self) -> None:
        power = estimated_vmc_power(self.coordinator.data) if self.coordinator.last_update_success else None
        if power is None:
            self._previous_sample = None
            return

        now = monotonic()
        if self._previous_sample is not None:
            previous_time, previous_watts = self._previous_sample
            self._attr_native_value += previous_watts * (now - previous_time) / 3_600_000
        self._previous_sample = (now, power)

    @callback
    def _handle_coordinator_update(self) -> None:
        self._record_sample()
        super()._handle_coordinator_update()


class ClivetCompressorEnergySensor(CoordinatorEntity[ClivetDataUpdateCoordinator], RestoreSensor):
    """Accumulate estimated compressor input energy between Modbus samples."""

    _attr_has_entity_name = True
    _attr_translation_key = "estimated_compressor_energy"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_suggested_display_precision = 3

    def __init__(self, coordinator: ClivetDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.unique_id}_estimated_compressor_energy"
        self._attr_device_info = coordinator.device_info
        self._attr_native_value = 0.0
        self._previous_sample: tuple[float, int] | None = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        previous = await self.async_get_last_sensor_data()
        if previous is not None and previous.native_value is not None:
            self._attr_native_value = float(previous.native_value)
        self._previous_sample = None
        self._record_sample()

    def _record_sample(self) -> None:
        power = estimated_compressor_power(self.coordinator.data) if self.coordinator.last_update_success else None
        if power is None:
            self._previous_sample = None
            return

        now = monotonic()
        if self._previous_sample is not None:
            previous_time, previous_watts = self._previous_sample
            self._attr_native_value += previous_watts * (now - previous_time) / 3_600_000
        self._previous_sample = (now, power)

    @callback
    def _handle_coordinator_update(self) -> None:
        self._record_sample()
        super()._handle_coordinator_update()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ClivetConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Clivet VMC sensor entities."""
    coordinator = entry.runtime_data
    entities = [
        ClivetSensorEntity(coordinator, description)
        for description in SENSOR_DESCRIPTIONS
    ]
    async_add_entities([
        *entities,
        ClivetVmcEnergySensor(coordinator),
        ClivetCompressorEnergySensor(coordinator),
    ])
