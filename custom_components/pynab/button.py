"""Button platform to trigger built-in Pynab service performances."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity

from .const import DOMAIN
from .entity import NabaztagEntity
from .nabweb import NabWebClient


async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        NabaztagTriggerButton(data["client"], data["web"], entry, target)
        for target in ("weather", "airquality", "taichi", "surprise")
    )


class NabaztagTriggerButton(NabaztagEntity, ButtonEntity):
    """Trigger an immediate performance of a built-in service."""

    _attr_icon = "mdi:play"

    def __init__(self, client, web: NabWebClient, entry, target: str) -> None:
        super().__init__(client, entry)
        self._web = web
        self._target = target
        self._attr_name = f"Trigger {target}"
        self._attr_unique_id = f"{entry.entry_id}_trigger_{target}"

    async def async_press(self) -> None:
        await self._web.async_trigger(self._target)