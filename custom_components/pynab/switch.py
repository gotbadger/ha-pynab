"""Switch platform for Nabaztag sleep/wake."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback

from .const import DEFAULT_PORT, DOMAIN
from .entity import NabaztagEntity
from .nabd import NabdClient


async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([NabaztagSleepSwitch(data["client"], entry)])


class NabaztagSleepSwitch(NabaztagEntity, SwitchEntity):
    """Sleep/wake switch for the rabbit."""

    _attr_name = "Sleep"
    _attr_icon = "mdi:sleep"

    def __init__(self, client: NabdClient, entry) -> None:
        super().__init__(client, entry)
        self._attr_unique_id = f"{entry.entry_id}_sleep"
        client.add_state_listener(self._on_state)

    @callback
    def _on_state(self, state):
        if self.hass is not None:
            self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        return self._client.last_state != "asleep"

    async def async_turn_on(self, **kwargs) -> None:
        """Wake the rabbit."""
        await self._client.async_send({"type": "wakeup"})

    async def async_turn_off(self, **kwargs) -> None:
        """Put the rabbit to sleep."""
        await self._client.async_send({"type": "sleep"})
