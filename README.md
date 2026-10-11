# ha-pynab

Home Assistant custom integration for Nabaztag (v1/Tag:Tag) rabbits running
[Pynab](https://github.com/nabaztag2018/pynab) (nabaztag2018).

## Prerequisites

The integration talks to the rabbit's `nabd` daemon (JSON-lines TCP protocol,
default port 10543). On a stock Pynab image `nabd` only listens on localhost.
Expose it to your LAN on the rabbit:

```
sudo pynab -public
```

Then restrict port 10543 to the Home Assistant machine only (nftables):

```
sudo nft add rule inet filter input ip saddr <HA_IP> tcp dport 10543 accept
sudo nft add rule inet filter input tcp dport 10543 drop
```

Persist the rules (e.g. `/etc/nftables.conf`).

**Caveats:**
- Pynab upgrades regenerate the systemd units, which reverts `pynab -public`.
  Either re-run it after each upgrade, or make the change persistent with a
  systemd drop-in: create `/etc/systemd/system/nabd.socket.d/override.conf`
  containing
  `[Socket]\nListenStream=0.0.0.0:10543`
  (and comment out the stock `ListenStream` via `systemctl edit nabd.socket`).
- The nftables rules above assume the `inet filter input` chain already
  exists. On a stock Raspberry Pi OS, start from `/etc/nftables.conf`
  (create the table/chain there) rather than `nft add rule` on a fresh boot.
- The rabbit's **web UI on port 80 is also unauthenticated** and is used by
  the `trigger` service. If your LAN is not fully trusted, firewall port 80
  the same way (e.g. allow only Home Assistant and your usual admin host).

## Installation

1. In Home Assistant, open **HACS → (⋮) Custom repositories**.
2. Paste `https://github.com/gotbadger/ha-pynab`, set category to
   **Integration**, and add it.
3. Search HACS for **Nabaztag (Pynab)** and install it.
4. Restart Home Assistant.

Or manually: copy `custom_components/pynab` to
`<config>/custom_components/pynab` and restart.

## Configuration

Add via Settings -> Devices & Services -> Add Integration -> Nabaztag (Pynab):

- Host (default `nabaztag.local`; a static IP is the most reliable choice if
  mDNS is flaky in your setup)
- nabd port (default 10543)

The web UI URL for service triggers is derived from the host. The flow tests
the connection before accepting it.

## Entities

- Sensor `state`: rabbit state (`idle`, `asleep`, `interactive`, `playing`),
  pushed live over the nabd protocol.
- Switch `sleep`: wake the rabbit / put it to sleep.
- Number `left ear` / `right ear`: ear positions, 0-16.
- Buttons `trigger weather/airquality/taichi/surprise`: run a built-in
  performance immediately.
- Event entities `button`, `rfid tag`, `ears`, `voice`: UI-selectable
  automation triggers for rabbit events.

## Services (domain `pynab`)

| Service | Description |
|---|---|
| `say` | Speak text using Home Assistant TTS. The rabbit fetches the MP3 itself. |
| `play` | Play an MP3 URL (or absolute path on the rabbit). |
| `sleep` / `wakeup` | Put the rabbit to sleep / wake it. |
| `set_ears` | Move ears to positions (0-16). |
| `set_leds` | Set an idle LED animation by `info_id`. |
| `cancel` | Cancel a running command by request id. |
| `trigger` | Trigger a built-in performance: `weather`, `airquality`, `taichi`, `surprise`. |

## Events

The integration subscribes to rabbit events and fires them on the Home
Assistant event bus as `nabaztag_event`:

- `button_event` (`down`, `up`, `click`, `double_click`, `click_and_hold`)
- `rfid_event` (`detected`/`removed`, with tag `uid`, `support`, `picture`, `app`, `data`)
- `ears_event` (normalised: covers both the protocol's idle and interactive
  ear events)
- `asr_event` (voice intents)

Example automation trigger:

```yaml
trigger:
  - platform: event
    event_type: nabaztag_event
    event_data:
      nabaztag_type: rfid_event
```

## Notes

- TTS uses HA's `tts.async_get_text_to_audio_url`; the rabbit must be able to
  reach your Home Assistant's **internal** HTTP URL on the LAN (it fetches the
  MP3 itself). Make sure the TTS engine's base URL is reachable from the
  rabbit, not just from your browser.
- The nabd protocol has no authentication. Keep the firewall rule in place;
  only the HA machine should be able to reach port 10543.

## Example calls

```yaml
# Speak a message (uses your default TTS engine)
service: pynab.say
data:
  message: "The front door is open"

# Move ears
service: pynab.set_ears
data:
  left: 5
  right: 10
```

## Troubleshooting

- **"Name does not resolve"**: use the rabbit's IP as the host. `.local`
  (mDNS) and custom `.lan` names can be flaky inside container-based HA
  setups; an IP or a DHCP reservation is the most reliable option.
- **"cannot connect"**: check on the rabbit that `sudo pynab -status` shows
  nabd listening publicly (`0.0.0.0:10543`) and that your firewall allows
  the HA machine's IP.
- **Entities unavailable**: the client reconnects automatically with a
  backoff; entities show as unavailable while disconnected.
- Tested against Pynab v1.0.2 (`2019_TAGTAG` hardware).