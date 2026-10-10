"""Tests for the NabdClient against a mock nabd server."""

import asyncio
import json

import pytest

from custom_components.pynab.nabd import NabdClient


class MockNabd:
    def __init__(self):
        self.server = None
        self.received = []

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
            self.received.append(json.loads(line.strip()))
            response = {"type": "response", "status": "ok", "request_id": json.loads(line)["request_id"]}
            writer.write((json.dumps(response) + "\r\n").encode())
            await writer.drain()

    async def stop(self):
        self.server.close()
        await self.server.wait_closed()


class HassStub:
    def async_create_background_task(self, coro, name):
        return asyncio.get_running_loop().create_task(coro)


@pytest.mark.asyncio
async def test_state_and_request():
    mock = MockNabd()
    host, port = await mock.start()
    try:
        client = NabdClient(HassStub(), host, port)
        await client.async_start(subscribe_events=True)
        for _ in range(50):
            if client.last_state == "idle":
                break
            await asyncio.sleep(0.05)
        assert client.last_state == "idle"
        response = await client.async_request({"type": "sleep"})
        assert response["status"] == "ok"
        assert any(p["type"] == "mode" for p in mock.received)
        assert any(p["type"] == "sleep" for p in mock.received)
        await client.async_stop()
    finally:
        await mock.stop()