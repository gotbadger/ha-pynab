"""Async client for the nabd TCP protocol (JSON lines, CRLF, port 10543)."""

import asyncio
import json
import logging
import uuid

from homeassistant.core import callback

_LOGGER = logging.getLogger(__name__)

RECV_TIMEOUT = 30
RECONNECT_DELAY = 5


class NabdError(Exception):
    pass


class NabdClient:
    def __init__(self, hass, host: str, port: int) -> None:
        self.hass = hass
        self.host = host
        self.port = port
        self._reader = None
        self._writer = None
        self._pending = {}
        self._state_listeners = []
        self._event_listeners = []
        self._task = None
        self._lock = asyncio.Lock()
        self.connected = False
        self.last_state = None

    @callback
    def add_state_listener(self, listener):
        self._state_listeners.append(listener)
        if self.last_state is not None:
            listener(self.last_state)

    @callback
    def add_event_listener(self, listener):
        self._event_listeners.append(listener)

    async def async_start(self, subscribe_events: bool = True) -> None:
        self._task = self.hass.async_create_background_task(
            self._run(subscribe_events), "pynab-nabd"
        )

    async def _run(self, subscribe_events: bool) -> None:
        while True:
            try:
                await self._connect(subscribe_events)
            except (OSError, asyncio.TimeoutError) as err:
                _LOGGER.warning("nabd connection to %s:%s failed: %s", self.host, self.port, err)
                self.connected = False
                await asyncio.sleep(RECONNECT_DELAY)
            except Exception:  # noqa: BLE001
                _LOGGER.exception("unexpected nabd client error")
                self.connected = False
                await asyncio.sleep(RECONNECT_DELAY)

    async def _connect(self, subscribe_events: bool) -> None:
        self._reader, self._writer = await asyncio.open_connection(self.host, self.port)
        self.connected = True
        _LOGGER.info("connected to nabd at %s:%s", self.host, self.port)
        if subscribe_events:
            packet = {
                "type": "mode",
                "request_id": uuid.uuid4().hex,
                "mode": "idle",
                "events": ["button", "ears", "rfid/*", "asr/*"],
            }
            await self._send_line(packet)
        while True:
            try:
                data = await asyncio.wait_for(self._reader.readline(), timeout=RECV_TIMEOUT * 20)
            except asyncio.TimeoutError:
                raise OSError("nabd read timeout")
            if not data:
                raise OSError("nabd connection closed")
            line = data.strip()
            if not line:
                continue
            try:
                packet = json.loads(line)
            except ValueError:
                _LOGGER.warning("invalid JSON line from nabd: %r", line)
                continue
            self._handle_packet(packet)

    def _handle_packet(self, packet: dict) -> None:
        ptype = packet.get("type")
        if ptype == "state":
            self.last_state = packet.get("state")
            for listener in self._state_listeners:
                listener(self.last_state)
            return
        if ptype == "response":
            request_id = packet.get("request_id")
            future = self._pending.pop(request_id, None)
            if future is not None and not future.done():
                future.set_result(packet)
            else:
                _LOGGER.debug("unmatched response: %s", packet)
            return
        if ptype in (
            "button_event",
            "rfid_event",
            "ears_event",
            "ear_event",
            "asr_event",
        ):
            packet["nabaztag_type"] = ptype
            for listener in self._event_listeners:
                listener(packet)
            return
        _LOGGER.debug("unhandled packet type: %s", ptype)

    async def _send_line(self, packet: dict) -> None:
        if self._writer is None:
            raise NabdError("not connected to nabd")
        self._writer.write((json.dumps(packet) + "\r\n").encode("utf-8"))
        await self._writer.drain()

    async def async_request(self, packet: dict, timeout: float = 10.0) -> dict:
        request_id = packet.setdefault("request_id", uuid.uuid4().hex)
        future = asyncio.get_running_loop().create_future()
        self._pending[request_id] = future
        await self._send_line(packet)
        try:
            return await asyncio.wait_for(future, timeout)
        except asyncio.TimeoutError:
            self._pending.pop(request_id, None)
            raise NabdError(f"timeout waiting for response to {request_id}") from None

    async def async_send(self, packet: dict) -> None:
        packet.setdefault("request_id", uuid.uuid4().hex)
        await self._send_line(packet)

    async def async_stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            self._task = None
        if self._writer is not None:
            self._writer.close()
            self._writer = None
        self.connected = False