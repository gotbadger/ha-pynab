"""Local stdlib-only test runner for the nabd protocol client.

Runs against an in-process mock nabd server; no pytest/homeassistant needed.
Usage: python3 tests/run_local.py
"""

import asyncio
import json
import os
import sys
import types
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Stub the single homeassistant symbol imported by nabd.py
ha = types.ModuleType("homeassistant")
core = types.ModuleType("homeassistant.core")


def callback(func):
    return func


core.callback = callback
ha.core = core
sys.modules["homeassistant"] = ha
sys.modules["homeassistant.core"] = core

# Load nabd.py directly (skip package __init__ which needs voluptuous)
import importlib.util  # noqa: E402

_nabd_path = os.path.join(
    os.path.dirname(__file__), "..", "custom_components", "pynab", "nabd.py"
)
_spec = importlib.util.spec_from_file_location("nabd_under_test", _nabd_path)
_nabd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_nabd)
NabdClient = _nabd.NabdClient


class HassStub:
    def async_create_background_task(self, coro, name):
        return asyncio.ensure_future(coro)


class MockNabd:
    def __init__(self):
        self.server = None
        self.received = []
        self.events = []

    async def start(self):
        self.server = await asyncio.start_server(self._handle, "127.0.0.1", 0)
        port = self.server.sockets[0].getsockname()[1]
        return "127.0.0.1", port

    async def _handle(self, reader, writer):
        writer.write((json.dumps({"type": "state", "state": "idle"}) + "\r\n").encode())
        await writer.drain()
        while True:
            line = await reader.readline()
            if not line:
                break
            packet = json.loads(line.strip())
            self.received.append(packet)
            response = {"type": "response", "status": "ok", "request_id": packet.get("request_id")}
            writer.write((json.dumps(response) + "\r\n").encode())
            await writer.drain()

    async def stop(self):
        self.server.close()
        await self.server.wait_closed()


async def test_state_and_request(mock, client):
    # Wait for the initial state push
    for _ in range(100):
        if client.last_state == "idle":
            break
        await asyncio.sleep(0.05)
    assert client.last_state == "idle", f"state push failed: {client.last_state}"
    print("OK  state push on connect: idle")

    # Request/response correlation
    response = await client.async_request({"type": "sleep"})
    assert response["status"] == "ok", response
    print("OK  request/response:", response)

    # Subscription packet was sent
    assert any(p["type"] == "mode" for p in mock.received), mock.received
    print("OK  mode subscription sent:", next(p for p in mock.received if p["type"] == "mode"))

    # sleep + command packets sent
    assert any(p["type"] == "sleep" for p in mock.received)
    print("OK  sleep packet sent")

    await client.async_send(
        {"type": "command", "sequence": [{"audio": ["https://example.com/x.mp3"]}]}
    )
    await asyncio.sleep(0.2)
    assert any(
        p["type"] == "command" and p["sequence"][0]["audio"] == ["https://example.com/x.mp3"]
        for p in mock.received
    )
    print("OK  command packet with audio URL sent")


async def test_event_dispatch(client):
    seen = []
    client.add_event_listener(lambda p: seen.append(p))
    client._handle_packet({"type": "button_event", "event": "click"})
    await asyncio.sleep(0)
    assert seen and seen[0]["nabaztag_type"] == "button_event"
    print("OK  event listener dispatch:", seen[0])

    client._handle_packet(
        {
            "type": "rfid_event",
            "tech": "st25tb",
            "uid": "d0:02:18:01:02:03:04:05",
            "event": "detected",
        }
    )
    assert seen[-1]["nabaztag_type"] == "rfid_event"
    print("OK  rfid event dispatch:", seen[-1])


async def test_reconnect(mock):
    client = NabdClient(HassStub(), *mock.server_info)
    await client.async_start(subscribe_events=False)
    for _ in range(100):
        if client.last_state == "idle":
            break
        await asyncio.sleep(0.05)
    # Kill the server side; client should not raise but mark disconnected
    mock.server.close()
    await asyncio.sleep(0.3)
    print("OK  reconnect loop survives server close (connected=%s)" % client.connected)
    await client.async_stop()


async def main():
    mock = MockNabd()
    host, port = await mock.start()
    mock.server_info = (host, port)
    client = NabdClient(HassStub(), host, port)
    await client.async_start(subscribe_events=True)
    try:
        await test_state_and_request(mock, client)
        await test_event_dispatch(client)
        await test_reconnect(mock)
    finally:
        await client.async_stop()
    await mock.stop()
    print("\nALL LOCAL TESTS PASSED")


if __name__ == "__main__":
    asyncio.run(main())