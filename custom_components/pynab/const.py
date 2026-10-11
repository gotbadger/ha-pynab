DOMAIN = "pynab"
DEFAULT_HOST = "nabaztag.local"
DEFAULT_PORT = 10543
EVENT_NABAZTAG = "nabaztag_event"
SERVICE_SAY = "say"
SERVICE_PLAY = "play"
SERVICE_SLEEP = "sleep"
SERVICE_WAKEUP = "wakeup"
SERVICE_SET_EARS = "set_ears"
SERVICE_SET_LEDS = "set_leds"
SERVICE_CANCEL = "cancel"
SERVICE_TRIGGER_SERVICE = "trigger"
TRIGGER_TARGETS = ["weather", "airquality", "taichi", "surprise"]
TRIGGER_PATHS = {
    "weather": "/nabweatherd/settings",
    "airquality": "/nabairqualityd/settings",
    "taichi": "/nabtaichid/settings",
    "surprise": "/nabsurprised/settings",
}
STATE_IDLE = "idle"
STATE_ASLEEP = "asleep"
STATE_INTERACTIVE = "interactive"
STATE_PLAYING = "playing"