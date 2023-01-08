from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant import config_entries, core, exceptions
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType
import voluptuous as vol

from .const import (  # pylint:disable=unused-import
    CONF_NAME,
    CONF_SERIAL,
    DOMAIN,
)
from homeassistant.components import zeroconf
from homeassistant.data_entry_flow import FlowResult

_LOGGER = logging.getLogger(__name__)

import platform    # For getting the operating system name
import subprocess  # For executing a shell command

def ping(host):
    """
    Returns True if host (str) responds to a ping request.
    Remember that a host may not respond to a ping (ICMP) request even if the host name is valid.
    """

    # Option for the number of packets as a function of
    param = '-n' if platform.system().lower()=='windows' else '-c'

    # Building the command. Ex: "ping -c 1 google.com"
    command = ['ping', param, '1', host]

    return subprocess.call(command) == 0


class SmartEVSEConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SmartEVSE."""

    VERSION = 1

    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self) -> None:
        self._serial = None

    async def async_step_zeroconf(
        self, discovery_info: zeroconf.ZeroconfServiceInfo
    ) -> FlowResult:
        """Handle zeroconf discovery."""
        errors: dict[str, str] = {}

        if not discovery_info.hostname.startswith("SmartEVSE"):
            return self.async_abort(reason="invalid_mdns")

        serial_number = discovery_info.hostname.replace(".local.", "").replace(
            "SmartEVSE-", ""
        )

        print("DEBUG: hostname:%s." % (discovery_info.hostname))
        print("DEBUG: serial number:%s." % (serial_number))

        await self.async_set_unique_id(serial_number)
        self._abort_if_unique_id_configured()
        print("DEBUG: ip adres:%s" % (discovery_info.host))


        # Attempt to make a connection to the local device and abort if not possible
        try:
            await self.validate_smartevse_connection(serial_number)
        except CannotConnect:
            errors["base"] = "cannot_connect"
        if not errors:
            self._serial = serial_number
            #print("DEBUG: user_input[CONF_SERIAL]=%s,CONF_SERIAL=%s,user_input=%s." % (user_input[CONF_SERIAL], CONF_SERIAL, user_input))
            return await self.async_step_options()

    async def validate_smartevse_connection(self, serial:Str ):
        host = "smartevse-" + serial + ".lan"
        ok = ping(host)
        if (not ok): #TODO disabled for debug purposes
            raise CannotConnect("Ping cannot find %s." % (host))

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step when user initializes an integration."""
        errors: dict[str, str] = {}
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_SERIAL])
            self._abort_if_unique_id_configured()

            try:
                await self.validate_smartevse_connection(user_input[CONF_SERIAL])
            except CannotConnect:
                errors["base"] = "cannot_connect"

            if not errors:
                self._serial = user_input[CONF_SERIAL]
                print("DEBUG: user_input[CONF_SERIAL]=%s,CONF_SERIAL=%s,user_input=%s." % (user_input[CONF_SERIAL], CONF_SERIAL, user_input))
                return await self.async_step_options()

        schema = vol.Schema(
            {
                vol.Required(CONF_SERIAL): cv.string,
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_options(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step to set options."""
        errors: dict[str, str] = {}
        data = {
            CONF_SERIAL: self._serial,
            CONF_NAME: "SmartEVSE",
        }

        return self.async_create_entry(title=f"{self._serial}", data=data)


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""
