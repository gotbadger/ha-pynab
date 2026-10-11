"""Number platform for Nabaztag ear positions."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv

from .const import DEFAULT_PORT, DOMAIN
from .entity import NabaztagEntity
from .nabd import NabdClient


async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    client = data["client"]
    async_add_entities(
        [
            NabaztagEarNumber(client, entry, "left"),
            NabaztagEarNumber(client, entry, "right"),
        ]
    )


class NabaztagEarNumber(NabaztagEntity, NumberEntity):
    """Ear position control (0-16)."""

    _attr_native_min_value = 0
    _attr_native_max_value = 16
    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER

    def __init__(self, client: NabdClient, entry, ear: str) -> None:
        super().__init__(client, entry)
        self._ear = ear
        self._attr_name = f"{ear.capitalize()} ear"
        self._attr_unique_id = f"{entry.entry_id}_ear_{ear}"
        self._attr_icon = "mdi:ear"
        self._attr_native_value = None
        client.add_event_listener(self._on_ears_event)

    @callback
    def _on_ears_event(self, packet):
        if packet.get("nabaztag_type") == "ears_event" and self._ear in packet:
            self._attr_native_value = packet[self._ear]
            self.async_write_ha_state()

    async def async_set_native_value(self, value: float) -> None:
        """Move the ear to a position."""
        position = int(value)
        await self._client.async_request({"type": "ears", self._ear: position})
        self._attr_native_value = position