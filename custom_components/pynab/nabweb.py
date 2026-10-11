"""aiohttp-based nabweb HTTP client for triggering service performances."""

import logging
import re

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import TRIGGER_PATHS

_LOGGER = logging.getLogger(__name__)

_CSRF_RE = re.compile(r"name='csrfmiddlewaretoken' value='([^']+)'")


class NabWebClient:
    """Client for the pynab web UI (nabweb) trigger endpoints."""

    def __init__(self, hass: HomeAssistant, base: str) -> None:
        self.hass = hass
        self.base = base.rstrip("/")

    async def async_trigger(self, target: str) -> None:
        """Trigger an immediate performance of a built-in service."""
        path = TRIGGER_PATHS[target]
        session = async_get_clientsession(self.hass)
        url = f"{self.base}{path}"

        # CSRF token from a prior GET, as the web UI does
        token = None
        async with session.get(url, timeout=10) as resp:
            resp.raise_for_status()
            body = await resp.text()
            match = _CSRF_RE.search(body)
            if match:
                token = match.group(1)
        _LOGGER.debug("csrf token for %s: %s", path, bool(token))

        # Only weather takes a body (type=today); others are empty PUTs
        data = {"type": "today"} if target == "weather" else None
        headers = {"X-CSRFToken": token, "Referer": url} if token else {}
        async with session.put(url, data=data, headers=headers, timeout=10) as resp:
            resp.raise_for_status()
            _LOGGER.debug("trigger %s -> %s", url, resp.status)