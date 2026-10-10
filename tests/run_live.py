"""End-to-end test of the nabd client against a real rabbit.

Requires an SSH tunnel to the rabbit (its nabd is localhost-only plus firewall):
    ssh -N -L 10543:127.0.0.1:10543 pi@nabaztag.local &
    python3 tests/run_live.py

Uses asyncio.open_connection to 127.0.0.1:10543 (the tunnel).
"""

import asyncio
import json
import sys


async def main():
    reader, writer = await asyncio.open_connection("127.0.0.1", 10543)

    async def send(packet):
        writer.write((json.dumps(packet) + "\r\n").encode())
        await writer.drain()

    async def read_packet():
        while True:
            line = await reader.readline()
            if not line:
                raise RuntimeError("nabd closed connection")
            packet = json.loads(line.strip())
            if packet["type"] == "state":
                print("STATE:", packet["state"])
                continue
            return packet

    # initial state push
    initial = json.loads((await reader.readline()).strip())
    assert initial["type"] == "state", initial
    print("OK  initial state:", initial)

    # gestalt query
    await send({"type": "gestalt", "request_id": "g1"})
    resp = await read_packet()
    assert resp["type"] == "response" and resp.get("request_id") == "g1", resp
    print("OK  gestalt:", resp)

    # set LEDs via info packet
    await send(
        {
            "type": "info",
            "request_id": "i1",
            "info_id": "ha_test",
            "animation": {
                "tempo": 125,
                "colors": [{"left": "#00ff00", "center": "#0000ff", "right": "#ff0000"}],
            },
        }
    )
    resp = await read_packet()
    print("OK  info set:", resp)

    # wake the rabbit (commands queue while asleep)
    await send({"type": "wakeup", "request_id": "w1"})
    resp = await read_packet()
    print("OK  wakeup:", resp)

    # play a built-in sound
    await send(
        {
            "type": "command",
            "request_id": "c1",
            "sequence": [{"audio": ["nabtaichid/signature.mp3"]}],
        }
    )
    resp = await read_packet()
    print("OK  command play:", resp)

    # clear info
    await send({"type": "info", "request_id": "i2", "info_id": "ha_test"})
    resp = await read_packet()
    print("OK  info cleared:", resp)

    writer.close()
    print("\nLIVE TEST PASSED")


if __name__ == "__main__":
    asyncio.run(main())