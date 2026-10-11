from homeassistant.components.sensor import SensorEntity
from homeassistant.core import callback

from .const import DOMAIN, STATE_ASLEEP, STATE_IDLE, STATE_INTERACTIVE, STATE_PLAYING
from .nabd import NabdClient


async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([NabaztagStateSensor(data["client"], entry)])


class NabaztagStateSensor(SensorEntity):
    _attr_has_entity_name = True
    _attr_name = "State"
    _attr_icon = "mdi:rabbit"

    def __init__(self, client: NabdClient, entry) -> None:
        self._client = client
        self._attr_unique_id = f"{entry.entry_id}_state"
        self._attr_native_value = None
        client.add_state_listener(self._on_state)

    @callback
    def _on_state(self, state):
        self._attr_native_value = state
        self.async_write_ha_state()

    @property
    def native_value(self):
        return self._attr_native_value

    @property
    def options(self):
        return [STATE_IDLE, STATE_ASLEEP, STATE_INTERACTIVE, STATE_PLAYING]