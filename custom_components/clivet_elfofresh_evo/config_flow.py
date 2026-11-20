"""Config flow for Clivet ELFOFresh EVO."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

import probatio as vol
from pymodbus.exceptions import ModbusException

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.core import callback

from .const import (
    CONF_BAUDRATE,
    CONF_CONNECTION_TYPE,
    CONF_HOST,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_SERIAL_PORT,
    CONF_SLAVE_ID,
    CONN_TYPE_RTUOVERTCP,
    CONN_TYPE_SERIAL,
    CONN_TYPE_TCP,
    DEFAULT_BAUDRATE,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SLAVE_ID,
    DOMAIN,
)
from .coordinator import ClivetConfigEntry, RegisterReadError, validate_connection

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL_VALIDATOR = vol.All(vol.Coerce(int), vol.Range(min=5, max=300))
NONEMPTY_TEXT = vol.All(str, vol.Length(min=1))


def endpoint(config: Mapping[str, Any]) -> tuple:
    """Identify a bus address for duplicate checks, independent of registry IDs."""
    slave = config.get(CONF_SLAVE_ID, DEFAULT_SLAVE_ID)
    if config.get(CONF_CONNECTION_TYPE) == CONN_TYPE_SERIAL:
        return ("serial", config[CONF_SERIAL_PORT], slave)
    return ("network", config[CONF_HOST].casefold(), config.get(CONF_PORT, DEFAULT_PORT), slave)


class ClivetConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Set up a VMC or edit the connection of an existing one."""

    VERSION = 1

    def __init__(self) -> None:
        self._entry: ClivetConfigEntry | None = None
        self._transport = CONN_TYPE_RTUOVERTCP

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        self._entry = self._get_reconfigure_entry()
        self._transport = self._entry.data.get(CONF_CONNECTION_TYPE, CONN_TYPE_RTUOVERTCP)
        return await self.async_step_user(user_input)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            self._transport = user_input[CONF_CONNECTION_TYPE]
            if self._transport == CONN_TYPE_SERIAL:
                return await self.async_step_serial()
            return await self.async_step_network()
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_CONNECTION_TYPE, default=self._transport): vol.In({
                    CONN_TYPE_RTUOVERTCP: "Modbus RTU over TCP",
                    CONN_TYPE_TCP: "Modbus TCP",
                    CONN_TYPE_SERIAL: "Modbus RTU (RS-485 / USB)",
                }),
            }),
        )

    async def async_step_network(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        return await self._connection_step("network", user_input)

    async def async_step_serial(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        return await self._connection_step("serial", user_input)

    def _already_configured(self, data: Mapping[str, Any]) -> bool:
        return any(
            entry is not self._entry and endpoint(entry.data) == endpoint(data)
            for entry in self._async_current_entries()
        )

    async def _connection_step(
        self, step: str, user_input: dict[str, Any] | None
    ) -> ConfigFlowResult:
        errors = {}
        defaults = dict(self._entry.data) if self._entry else {}
        if user_input is not None:
            defaults.update(user_input)
            data = {CONF_CONNECTION_TYPE: self._transport, **user_input}
            if self._already_configured(data):
                return self.async_abort(reason="already_configured")
            try:
                if self._entry and self._entry.state is config_entries.ConfigEntryState.LOADED:
                    await self._entry.runtime_data.async_validate_reconfiguration(data)
                else:
                    await validate_connection(data)
            except RegisterReadError:
                errors["base"] = "cannot_read_registers"
            except (OSError, ModbusException):
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error validating Clivet VMC connection")
                errors["base"] = "unknown"
            else:
                # Another flow may have finished while this one was probing the bus.
                if self._already_configured(data):
                    return self.async_abort(reason="already_configured")
                address = data[CONF_SERIAL_PORT] if step == "serial" else data[CONF_HOST]
                title = f"{DEFAULT_NAME} ({address})"
                if self._entry:
                    data[CONF_SCAN_INTERVAL] = defaults.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
                    old_address = self._entry.data.get(CONF_SERIAL_PORT) or self._entry.data.get(CONF_HOST)
                    if self._entry.title not in (f"{DEFAULT_NAME} ({old_address})", f"Clivet VMC ({old_address})"):
                        title = self._entry.title
                    return self.async_update_reload_and_abort(self._entry, data=data, title=title)
                return self.async_create_entry(title=title, data=data)

        if step == "serial":
            fields = {
                vol.Required(CONF_SERIAL_PORT, default=defaults.get(CONF_SERIAL_PORT, "/dev/ttyUSB0")): NONEMPTY_TEXT,
                vol.Required(CONF_BAUDRATE, default=defaults.get(CONF_BAUDRATE, DEFAULT_BAUDRATE)):
                    vol.All(vol.Coerce(int), vol.Range(min=1)),
            }
        else:
            fields = {
                vol.Required(CONF_HOST): NONEMPTY_TEXT,
                vol.Required(CONF_PORT, default=defaults.get(CONF_PORT, DEFAULT_PORT)):
                    vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
            }
        # Native TCP carries an 8-bit unit identifier; RTU uses unicast addresses.
        slave_range = vol.Range(min=0, max=255) if self._transport == CONN_TYPE_TCP else vol.Range(min=1, max=247)
        fields[vol.Required(CONF_SLAVE_ID, default=defaults.get(CONF_SLAVE_ID, DEFAULT_SLAVE_ID))] = (
            vol.All(vol.Coerce(int), slave_range)
        )
        if self._entry is None:
            fields[vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL)] = SCAN_INTERVAL_VALIDATOR
        return self.async_show_form(
            step_id=step,
            data_schema=self.add_suggested_values_to_schema(vol.Schema(fields), defaults),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        return ClivetOptionsFlow()


class ClivetOptionsFlow(config_entries.OptionsFlowWithReload):
    """Manage polling frequency."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        current_interval = self.config_entry.options.get(
            CONF_SCAN_INTERVAL, self.config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(CONF_SCAN_INTERVAL, default=current_interval): SCAN_INTERVAL_VALIDATOR,
            }),
        )
