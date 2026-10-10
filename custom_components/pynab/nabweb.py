"""Minimal nabweb HTTP client for triggering service performances."""

import asyncio
import logging
import re
import urllib.parse

from homeassistant.core import HomeAssistant

from .const import TRIGGER_PATHS

_LOGGER = logging.getLogger(__name__)

_CSRF_RE = re.compile(r"name='csrfmiddlewaretoken' value='([^']+)'")


class NabWebClient:
    def __init__(self, hass: HomeAssistant, base: str) -> None:
        self.hass = hass
        self.base = base.rstrip("/")

    async def async_trigger(self, target: str) -> None:
        path = TRIGGER_PATHS[target]
        token = await self.hass.async_add_executor_job(self._fetch_csrf, path)
        await self.hass.async_add_executor_job(self._put, path, token, target)

    def _fetch_csrf(self, path: str):
        import urllib.request

        url = f"{self.base}{path}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8", errors="replace")
        match = _CSRF_RE.search(body)
        token = match.group(1) if match else None
        _LOGGER.debug("csrf token for %s: %s", path, bool(token))
        return token

    def _put(self, path: str, token, target: str) -> None:
        import urllib.request

        url = f"{self.base}{path}"
        if target == "weather":
            data = urllib.parse.urlencode({"type": "today"}).encode()
        else:
            data = b""
        headers = {"X-CSRFToken": token} if token else {}
        if token:
            headers["Referer"] = url
        req = urllib.request.Request(url, data=data, headers=headers, method="PUT")
        with urllib.request.urlopen(req, timeout=10) as resp:
            _LOGGER.debug("trigger %s -> %s", url, resp.status)