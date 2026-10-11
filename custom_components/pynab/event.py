"""Event platform exposing rabbit events as UI-selectable triggers."""

from __future__ import annotations

from homeassistant.components.event import EventEntity
from homeassistant.core import callback

from .const import DOMAIN
from .entity import NabaztagEntity
from .nabd import NabdClient

BUTTON_EVENT_TYPES = [
    "down",
    "up",
    "click",
    "double_click",
    "triple_click",
    "hold",
    "click_and_hold",
]


async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    client = data["client"]
    async_add_entities(
        [
            NabaztagEventEntity(client, entry, "Button", "button_event", ["down", "up", "click", "double_click", "triple_click", "hold", "click_and_hold"], "mdi:gesture-tap"),
            NabaztagEventEntity(client, entry, "RFID tag", "rfid_event", ["detected", "removed"], "mdi:nfc-variant"),
            NabaztagEventEntity(client, entry, "Ears", "ears_event", ["moved"], "mdi:ear"),
            NabaztagEventEntity(client, entry, "Voice", "asr_event", ["intent"], "mdi:microphone"),
        ]
    )


class NabaztagEventEntity(NabaztagEntity, EventEntity):
    """Event entity for one class of rabbit events."""

    _attr_has_entity_name = True

    def __init__(
        self,
        client: NabdClient,
        entry,
        name: str,
        event_type: str,
        event_types: list,
        icon: str,
    ) -> None:
        super().__init__(client, entry)
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_event_{event_type}"
        self._attr_icon = icon
        self._attr_event_types = event_types
        self._event_type = event_type
        client.add_event_listener(self._on_event)

    @callback
    def _on_event(self, packet):
        if packet.get("nabaztag_type") != self._event_type:
            return
        properties = {
            k: v for k, v in packet.items() if k not in ("type", "nabaztag_type")
        }
        if self._event_type == "button_event":
            event_type = packet.get("event", "click")
        elif self._event_type == "rfid_event":
            event_type = packet.get("event", "detected")
        elif self._event_type == "asr_event":
            event_type = "intent"
        else:
            event_type = "moved"
        self._trigger_event(event_type, properties)