"""Config flow for Nabaztag (Pynab)."""

import socket

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback

from .const import CONF_HTTP_BASE, DEFAULT_HTTP_BASE, DEFAULT_PORT, DOMAIN

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST, default="nabaztag.local"): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Optional(CONF_HTTP_BASE, default=DEFAULT_HTTP_BASE): str,
    }
)


class NabaztagConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input[CONF_PORT]
            try:
                await self.hass.async_add_executor_job(_probe, host, port)
            except OSError:
                errors[CONF_HOST] = "cannot_connect"
            else:
                return self.async_create_entry(title=f"Nabaztag {host}", data=user_input)
        return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(entry):
        return NabaztagOptionsFlow(entry)


class NabaztagOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, entry):
        self.entry = entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_HOST, default=self.entry.data.get(CONF_HOST, "nabaztag.local")
                ): str,
                vol.Required(
                    CONF_PORT, default=self.entry.data.get(CONF_PORT, DEFAULT_PORT)
                ): int,
                vol.Optional(
                    CONF_HTTP_BASE,
                    default=self.entry.data.get(CONF_HTTP_BASE, DEFAULT_HTTP_BASE),
                ): str,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)


def _probe(host, port):
    sock = socket.create_connection((host, port), timeout=10)
    sock.close()