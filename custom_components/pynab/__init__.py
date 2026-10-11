import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady
import homeassistant.helpers.config_validation as cv

from .const import (
    DEFAULT_PORT,
    DOMAIN,
    EVENT_NABAZTAG,
    SERVICE_CANCEL,
    SERVICE_PLAY,
    SERVICE_SAY,
    SERVICE_SET_EARS,
    SERVICE_SET_LEDS,
    SERVICE_SLEEP,
    SERVICE_TRIGGER_SERVICE,
    SERVICE_WAKEUP,
    TRIGGER_TARGETS,
)
from .nabd import NabdClient
from .nabweb import NabWebClient

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.NUMBER,
    Platform.BUTTON,
    Platform.EVENT,
]

SAY_SCHEMA = vol.Schema(
    {
        vol.Required("message"): cv.string,
        vol.Optional("engine"): cv.string,
        vol.Optional("choreography"): cv.string,
    }
)
PLAY_SCHEMA = vol.Schema(
    {
        vol.Required("url"): cv.string,
        vol.Optional("choreography"): cv.string,
    }
)
SET_EARS_SCHEMA = vol.Schema(
    {
        vol.Optional("left"): vol.All(vol.Coerce(int), vol.Range(0, 16)),
        vol.Optional("right"): vol.All(vol.Coerce(int), vol.Range(0, 16)),
    }
)
SET_LEDS_SCHEMA = vol.Schema(
    {
        vol.Required("info_id"): cv.string,
        vol.Required("tempo", default=125): vol.All(vol.Coerce(int), vol.Range(50, 60000)),
        vol.Optional("left"): cv.string,
        vol.Optional("center"): cv.string,
        vol.Optional("right"): cv.string,
    }
)
CANCEL_SCHEMA = vol.Schema({vol.Required("request_id"): cv.string})
TRIGGER_SCHEMA = vol.Schema({vol.Required("target"): vol.In(TRIGGER_TARGETS)})


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})
    client = NabdClient(
        hass, entry.data[CONF_HOST], entry.data.get(CONF_PORT, DEFAULT_PORT)
    )
    try:
        await _probe(entry.data[CONF_HOST], entry.data.get(CONF_PORT, DEFAULT_PORT))
    except OSError as err:
        raise ConfigEntryNotReady(f"cannot reach nabd: {err}") from err
    await client.async_start(subscribe_events=True)

    async def handle_event(event_packet):
        hass.bus.async_fire(EVENT_NABAZTAG, event_packet)

    client.add_event_listener(handle_event)

    http_base = f"http://{entry.data[CONF_HOST]}"
    web = NabWebClient(hass, http_base)

    async def get_client() -> NabdClient:
        return client

    async def say(call: ServiceCall):
        message = call.data["message"]
        engine = call.data.get("engine")
        choreography = call.data.get("choreography")
        url = await _resolve_tts_url(hass, message, engine)
        await _play(client, url, choreography)

    async def play(call: ServiceCall):
        await _play(client, call.data["url"], call.data.get("choreography"))

    async def sleep(call: ServiceCall):
        await client.async_send({"type": "sleep"})

    async def wakeup(call: ServiceCall):
        await client.async_send({"type": "wakeup"})

    async def set_ears(call: ServiceCall):
        packet = {"type": "ears"}
        if "left" in call.data:
            packet["left"] = call.data["left"]
        if "right" in call.data:
            packet["right"] = call.data["right"]
        await client.async_request(packet)

    async def set_leds(call: ServiceCall):
        animation = {
            "tempo": call.data["tempo"],
            "colors": [
                {
                    key: call.data[key]
                    for key in ("left", "center", "right")
                    if key in call.data
                }
            ],
        }
        await client.async_request(
            {"type": "info", "info_id": call.data["info_id"], "animation": animation}
        )

    async def cancel(call: ServiceCall):
        await client.async_send(
            {"type": "cancel", "request_id": call.data["request_id"]}
        )

    async def trigger(call: ServiceCall):
        target = call.data["target"]
        await web.async_trigger(target)

    hass.services.async_register(DOMAIN, SERVICE_SAY, say, schema=SAY_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_PLAY, play, schema=PLAY_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_SLEEP, sleep)
    hass.services.async_register(DOMAIN, SERVICE_WAKEUP, wakeup)
    hass.services.async_register(DOMAIN, SERVICE_SET_EARS, set_ears, schema=SET_EARS_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_SET_LEDS, set_leds, schema=SET_LEDS_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_CANCEL, cancel, schema=CANCEL_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_TRIGGER_SERVICE, trigger, schema=TRIGGER_SCHEMA)

    hass.data[DOMAIN][entry.entry_id] = {"client": client, "web": web}
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _probe(host: str, port: int) -> None:
    import asyncio

    reader, writer = await asyncio.open_connection(host, port)
    writer.close()


async def _play(client: NabdClient, url: str, choreography=None) -> None:
    element = {"audio": [url]}
    if choreography:
        element["choreography"] = choreography
    await client.async_send({"type": "command", "sequence": [element]})


async def _resolve_tts_url(hass, message: str, engine) -> str:
    try:
        from homeassistant.components import tts
    except ImportError as err:
        raise ValueError("tts integration not available") from err
    if engine:
        url = await tts.async_get_text_to_audio_url(hass, message, engine)
    else:
        url = await tts.async_get_text_to_audio_url(hass, message)
    if url is None:
        raise ValueError("no tts engine available for message")
    return url


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    data = hass.data[DOMAIN].get(entry.entry_id)
    if data is not None:
        await data["client"].async_stop()
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        if not hass.data[DOMAIN]:
            for service in (
                SERVICE_SAY,
                SERVICE_PLAY,
                SERVICE_SLEEP,
                SERVICE_WAKEUP,
                SERVICE_SET_EARS,
                SERVICE_SET_LEDS,
                SERVICE_CANCEL,
                SERVICE_TRIGGER_SERVICE,
            ):
                hass.services.async_remove(DOMAIN, service)
    return unloaded