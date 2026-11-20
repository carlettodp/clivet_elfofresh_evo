"""DataUpdateCoordinator for Clivet ELFOFresh EVO."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from datetime import timedelta
import logging
from typing import Any

from pymodbus import FramerType
from pymodbus.client import AsyncModbusSerialClient, AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    BIT_124_DAMPER_OPEN,
    BIT_124_DEFROST,
    BIT_124_HUMIDIFIER_ON,
    BIT_124_OIL_RETURN,
    BIT_124_REMOTE_ON_OFF,
    BIT_124_SILENT,
    BIT_124_WATER_LEVEL_ALARM,
    BIT_125_4WAY_VALVE,
    BIT_125_DEFROST_INDEX,
    BIT_125_ELECTRICAL_FILTER,
    BIT_125_ELECTRICAL_HEATER,
    BIT_125_EXHAUST_FAN_POWER,
    BIT_125_HUMIDIFIER,
    BIT_125_SUPPLY_FAN_POWER,
    BIT_125_SYSTEM_ERROR,
    BIT_125_UNIT_ON_INDEX,
    BIT_125_WATER_PUMP,
    CONF_BAUDRATE,
    CONF_CONNECTION_TYPE,
    CONF_HOST,
    CONF_PORT,
    CONF_SERIAL_PORT,
    CONF_SLAVE_ID,
    CONN_TYPE_RTUOVERTCP,
    CONN_TYPE_SERIAL,
    CONN_TYPE_TCP,
    DEFAULT_BAUDRATE,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEFAULT_SLAVE_ID,
    DOMAIN,
    REG_COMPRESSOR_RPS,
    REG_COMPRESSOR_TIME,
    REG_CONDENSATION_TEMP,
    REG_CURRENT,
    REG_CURRENT_ERROR,
    REG_DEHUM_MODE_SET,
    REG_DISCHARGE_TEMP,
    REG_EHEATER_OUTPUT,
    REG_ENABLE_E_FILTER,
    REG_ENABLE_HUMIDIFIER,
    REG_EVAPORATION_TEMP,
    REG_EXHAUST_FAN_SPEED,
    REG_EXV_OPENING,
    REG_FUNCTIONS_SET,
    REG_HISTORY_ERROR_1,
    REG_HISTORY_ERROR_2,
    REG_HISTORY_ERROR_3,
    REG_HMI_SW_VERSION,
    REG_INDOOR_AIR_TEMP,
    REG_MAIN_SW_VERSION,
    REG_MODE_SET,
    REG_OP_MODE_BITMASK,
    REG_OPERATING_MODE,
    REG_OUTDOOR_AIR_TEMP,
    REG_OUTPUT_STATUS_BITMASK,
    REG_POWER,
    REG_SECOND_SUPPLY_TEMP,
    REG_SILENT_MODE_SET,
    REG_SUCTION_TEMP,
    REG_SUPPLY_AIR_HUMIDITY,
    REG_SUPPLY_AIR_TEMP,
    REG_SUPPLY_FAN_SPEED_RAW,
    REG_TARGET_FAN_SPEED,
    REG_TARGET_TEMP,
    REG_UNIT_SIZE,
    REG_VOLTAGE,
)

_LOGGER = logging.getLogger(__name__)


def to_signed16(val: int) -> int:
    """Convert 16-bit unsigned integer to signed integer."""
    return val if val < 32768 else val - 65536


def get_bit(value: int, bit_index: int) -> bool:
    """Check if a specific bit is set."""
    return bool((value >> bit_index) & 1)


type ClivetConfigEntry = ConfigEntry[ClivetDataUpdateCoordinator]
type ModbusClient = AsyncModbusSerialClient | AsyncModbusTcpClient


def create_client(config: Mapping[str, Any]) -> ModbusClient:
    """Build the same transport for setup and polling."""
    transport = config.get(CONF_CONNECTION_TYPE, CONN_TYPE_RTUOVERTCP)
    if transport == CONN_TYPE_SERIAL:
        return AsyncModbusSerialClient(
            port=config[CONF_SERIAL_PORT],
            baudrate=config.get(CONF_BAUDRATE, DEFAULT_BAUDRATE),
            bytesize=8, parity="N", stopbits=1, timeout=5,
        )
    return AsyncModbusTcpClient(
        host=config[CONF_HOST],
        port=config.get(CONF_PORT, DEFAULT_PORT),
        framer=FramerType.SOCKET if transport == CONN_TYPE_TCP else FramerType.RTU,
        timeout=5,
    )


class RegisterReadError(Exception):
    """The transport opened, but the required VMC registers could not be read."""


async def read_blocks(client: ModbusClient, slave_id: int) -> list[list[int]]:
    """Read and validate all three blocks used by the entities."""
    blocks = []
    for address, count in ((0, 4), (100, 29), (210, 16)):
        if blocks:
            await asyncio.sleep(0.05)
        try:
            result = await client.read_holding_registers(
                address, count=count, device_id=slave_id
            )
        except (OSError, ModbusException) as err:
            raise RegisterReadError(f"Failed reading block at {address}") from err
        if result is None or result.isError() or len(result.registers) != count:
            raise RegisterReadError(f"Invalid response for block at {address}: {result}")
        blocks.append(result.registers)
    return blocks


async def validate_connection(config: Mapping[str, Any]) -> None:
    """Probe a candidate connection without writing registers."""
    client = create_client(config)
    try:
        if not await client.connect():
            raise ConnectionError("Could not open Modbus connection")
        await read_blocks(client, config.get(CONF_SLAVE_ID, DEFAULT_SLAVE_ID))
    finally:
        client.close()


class ClivetDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Manage Modbus communication for one config entry."""

    def __init__(self, hass: HomeAssistant, entry: ClivetConfigEntry, scan_interval: int) -> None:
        super().__init__(
            hass, _LOGGER, name=DOMAIN, config_entry=entry,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.config = entry.data
        self.slave_id = entry.data.get(CONF_SLAVE_ID, DEFAULT_SLAVE_ID)
        self.unique_id = entry.entry_id
        self._lock = asyncio.Lock()
        self.client: ModbusClient | None = None

    async def async_validate_reconfiguration(self, config: Mapping[str, Any]) -> None:
        """Release the live transport while probing, including exclusive serial ports."""
        async with self._lock:
            await self.async_close()
            await validate_connection(config)

    async def _async_get_client(self) -> ModbusClient:
        if self.client is None:
            self.client = create_client(self.config)
        if not self.client.connected and not await self.client.connect():
            raise ConnectionError("Could not open Modbus connection")
        return self.client

    async def async_write_register(
        self, address: int, value: int, refresh: bool = True
    ) -> None:
        """Write a single holding register."""
        async with self._lock:
            client = await self._async_get_client()
            result = await client.write_register(address, value, device_id=self.slave_id)

            if result is None or result.isError():
                raise ModbusException(
                    f"Error writing register {address} with value {value}: {result}"
                )

            # Optimistically update cache so Home Assistant UI updates immediately
            if self.data is not None:
                if address == REG_POWER:
                    is_on = bool(value & 1)
                    self.data["power"] = is_on
                    if not is_on:
                        self.data["unit_on_index"] = False
                        self.data["operating_mode"] = 0
                elif address == REG_MODE_SET:
                    self.data["mode_set"] = value
                elif address == REG_TARGET_TEMP:
                    self.data["target_temp"] = value
                elif address == REG_TARGET_FAN_SPEED:
                    self.data["target_fan_speed"] = value
                elif address == REG_SILENT_MODE_SET:
                    self.data["silent_mode"] = value
                elif address == REG_DEHUM_MODE_SET:
                    self.data["dehum_mode"] = value
                elif address == REG_ENABLE_E_FILTER:
                    self.data["e_filter_enabled"] = bool(value & 1)
                elif address == REG_ENABLE_HUMIDIFIER:
                    self.data["humidifier_enabled"] = bool(value & 1)

                self.async_update_listeners()

            # Small inter-write gap for RS485 line
            await asyncio.sleep(0.05)

        # Trigger background hardware refresh OUTSIDE the lock
        if refresh:
            await asyncio.sleep(0.3)
            await self.async_request_refresh()

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch all data from Clivet VMC in 3 optimized block reads."""
        async with self._lock:
            try:
                client = await self._async_get_client()
                block_1, block_2, block_3 = await read_blocks(client, self.slave_id)
            except Exception as err:
                # Reset client on connection errors to force reconnect next time
                if self.client:
                    self.client.close()
                    self.client = None
                raise UpdateFailed(f"Error communicating with Clivet VMC: {err}") from err

        # Parse Block 1 (Addresses 0..3)
        reg_0 = block_1[0]  # REG_POWER
        reg_1 = block_1[1]  # REG_MODE_SET
        reg_2 = block_1[2]  # REG_TARGET_TEMP
        reg_3 = block_1[3]  # REG_FUNCTIONS_SET

        # Parse Block 2 (Addresses 100..128)
        reg_100 = block_2[0]   # REG_COMPRESSOR_RPS
        reg_101 = block_2[1]   # REG_OPERATING_MODE
        reg_102 = block_2[2]   # REG_SUPPLY_FAN_SPEED_RAW
        reg_103 = block_2[3]   # REG_EXHAUST_FAN_SPEED
        reg_104 = block_2[4]   # REG_EXV_OPENING
        reg_105 = block_2[5]   # REG_CONDENSATION_TEMP
        reg_106 = block_2[6]   # REG_SUPPLY_AIR_HUMIDITY
        reg_107 = block_2[7]   # REG_EVAPORATION_TEMP
        reg_108 = block_2[8]   # REG_OUTDOOR_AIR_TEMP
        reg_109 = block_2[9]   # REG_DISCHARGE_TEMP
        reg_110 = block_2[10]  # REG_SUCTION_TEMP
        reg_111 = block_2[11]  # REG_INDOOR_AIR_TEMP
        reg_112 = block_2[12]  # REG_SUPPLY_AIR_TEMP
        reg_113 = block_2[13]  # REG_SECOND_SUPPLY_TEMP
        reg_116 = block_2[16]  # REG_CURRENT
        reg_117 = block_2[17]  # REG_VOLTAGE
        reg_118 = block_2[18]  # REG_COMPRESSOR_TIME
        reg_119 = block_2[19]  # REG_CURRENT_ERROR
        reg_120 = block_2[20]  # REG_HISTORY_ERROR_1
        reg_121 = block_2[21]  # REG_HISTORY_ERROR_2
        reg_122 = block_2[22]  # REG_HISTORY_ERROR_3
        reg_123 = block_2[23]  # REG_UNIT_SIZE
        reg_124 = block_2[24]  # REG_OP_MODE_BITMASK
        reg_125 = block_2[25]  # REG_OUTPUT_STATUS_BITMASK
        reg_126 = block_2[26]  # REG_EHEATER_OUTPUT
        reg_127 = block_2[27]  # REG_MAIN_SW_VERSION
        reg_128 = block_2[28]  # REG_HMI_SW_VERSION

        # Parse Block 3 (Addresses 210..225)
        reg_210 = block_3[0]   # REG_TARGET_FAN_SPEED (210 - 210 = 0)
        reg_217 = block_3[7]   # REG_SILENT_MODE_SET (217 - 210 = 7)
        reg_222 = block_3[12]  # REG_DEHUM_MODE_SET (222 - 210 = 12)
        reg_224 = block_3[14]  # REG_ENABLE_E_FILTER (224 - 210 = 14)
        reg_225 = block_3[15]  # REG_ENABLE_HUMIDIFIER (225 - 210 = 15)

        data = {
            # Commands & Status
            "power": bool(reg_0 & 1),
            "mode_set": reg_1,
            "target_temp": reg_2,
            "functions_set": reg_3,
            "operating_mode": reg_101,

            # Temperatures (signed 16-bit)
            "indoor_air_temp": to_signed16(reg_111),
            "outdoor_air_temp": to_signed16(reg_108),
            "supply_air_temp": to_signed16(reg_112),
            "second_supply_temp": to_signed16(reg_113),
            "condensation_temp": to_signed16(reg_105),
            "evaporation_temp": to_signed16(reg_107),
            "discharge_temp": to_signed16(reg_109),
            "suction_temp": to_signed16(reg_110),

            # Humidity & Electrical
            "supply_air_humidity": reg_106,
            "current": round(reg_116 * 0.1, 1),
            "voltage": reg_117,

            # Operational parameters
            "compressor_rps": reg_100,
            "exv_opening": reg_104,
            "supply_fan_speed_raw": reg_102,
            "exhaust_fan_speed": reg_103,
            "compressor_time": reg_118,
            "eheater_output": reg_126,

            # Diagnostics & Errors
            "current_error": reg_119,
            "history_error_1": reg_120,
            "history_error_2": reg_121,
            "history_error_3": reg_122,
            "unit_size": reg_123,
            "op_mode_bitmask": reg_124,
            "output_status_bitmask": reg_125,
            "main_sw_version": reg_127,
            "hmi_sw_version": reg_128,

            # Settable parameters
            "target_fan_speed": reg_210,
            "silent_mode": reg_217,
            "dehum_mode": reg_222,
            "e_filter_enabled": bool(reg_224 & 1),
            "humidifier_enabled": bool(reg_225 & 1),

            # Decoded Bitmasks from Register 124 (Operating Mode)
            "defrost_active": get_bit(reg_124, BIT_124_DEFROST) or get_bit(reg_125, BIT_125_DEFROST_INDEX),
            "silent_active": get_bit(reg_124, BIT_124_SILENT),
            "oil_return": get_bit(reg_124, BIT_124_OIL_RETURN),
            "remote_on_off": get_bit(reg_124, BIT_124_REMOTE_ON_OFF),
            "water_level_alarm": get_bit(reg_124, BIT_124_WATER_LEVEL_ALARM),
            "damper_open": get_bit(reg_124, BIT_124_DAMPER_OPEN),
            "humidifier_on": get_bit(reg_124, BIT_124_HUMIDIFIER_ON),

            # Decoded Bitmasks from Register 125 (Output Status)
            "e_filter_active": get_bit(reg_125, BIT_125_ELECTRICAL_FILTER),
            "water_pump_active": get_bit(reg_125, BIT_125_WATER_PUMP),
            "humidifier_active": get_bit(reg_125, BIT_125_HUMIDIFIER),
            "valve_4way_active": get_bit(reg_125, BIT_125_4WAY_VALVE),
            "exhaust_fan_power": get_bit(reg_125, BIT_125_EXHAUST_FAN_POWER),
            "supply_fan_power": get_bit(reg_125, BIT_125_SUPPLY_FAN_POWER),
            "system_error": get_bit(reg_125, BIT_125_SYSTEM_ERROR),
            "unit_on_index": get_bit(reg_125, BIT_125_UNIT_ON_INDEX),
            "e_heater_active": get_bit(reg_125, BIT_125_ELECTRICAL_HEATER),
        }

        return data

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information about this Clivet VMC."""
        main_sw = self.data.get("main_sw_version") if self.data else None
        hmi_sw = self.data.get("hmi_sw_version") if self.data else None
        sw_version = f"Main: {main_sw} / HMI: {hmi_sw}" if (main_sw and hmi_sw) else None

        return DeviceInfo(
            identifiers={(DOMAIN, self.unique_id)},
            name=DEFAULT_NAME,
            manufacturer="Clivet",
            model="CPAN-YIN",
            sw_version=sw_version,
        )

    async def async_close(self) -> None:
        """Close the Modbus connection."""
        if self.client:
            self.client.close()
            self.client = None
