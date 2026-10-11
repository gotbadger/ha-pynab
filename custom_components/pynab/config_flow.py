"""Config flow for Nabaztag (Pynab)."""

import socket

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import DOMAIN


class NabaztagConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Nabaztag (Pynab)."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input[CONF_PORT]
            await self.async_set_unique_id(f"{DOMAIN}-{host}:{port}")
            self._abort_if_unique_id_configured()
            try:
                await self.hass.async_add_executor_job(_probe, host, port)
            except OSError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(title=f"Nabaztag {host}", data=user_input)
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_HOST, default=(user_input or {}).get(CONF_HOST, "nabaztag.local")
                    ): selector.TextSelector(),
                    vol.Required(
                        CONF_PORT, default=(user_input or {}).get(CONF_PORT, 10543)
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(min=1, max=65535, mode=selector.NumberSelectorMode.BOX)
                    ),
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(entry):
        return NabaztagOptionsFlow(entry)


class NabaztagOptionsFlow(config_entries.OptionsFlow):
    """Options flow for Nabaztag (Pynab)."""

    def __init__(self, entry):
        self.entry = entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_HOST, default=self.entry.data.get(CONF_HOST, "nabaztag.local")
                ): selector.TextSelector(),
                vol.Required(
                    CONF_PORT, default=self.entry.data.get(CONF_PORT, 10543)
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1, max=65535, mode=selector.NumberSelectorMode.BOX
                    )
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)


def _probe(host, port):
    sock = socket.create_connection((host, port), timeout=10)
    sock.close()