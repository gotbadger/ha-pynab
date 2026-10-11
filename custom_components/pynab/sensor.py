"""Sensor platform for the rabbit state."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.core import callback

from .const import DOMAIN, STATE_ASLEEP, STATE_IDLE, STATE_INTERACTIVE, STATE_PLAYING
from .entity import NabaztagEntity


async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([NabaztagStateSensor(data["client"], entry)])


class NabaztagStateSensor(NabaztagEntity, SensorEntity):
    """Rabbit state (idle, asleep, interactive, playing)."""

    _attr_name = "State"
    _attr_icon = "mdi:rabbit"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = [STATE_IDLE, STATE_ASLEEP, STATE_INTERACTIVE, STATE_PLAYING]

    def __init__(self, client, entry) -> None:
        super().__init__(client, entry)
        self._attr_unique_id = f"{entry.entry_id}_state"
        self._attr_native_value = client.last_state
        client.add_state_listener(self._on_state)

    @callback
    def _on_state(self, state):
        self._attr_native_value = state
        if self.hass is not None:
            self.async_write_ha_state()