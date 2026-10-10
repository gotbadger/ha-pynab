# hacs-nabaztag

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

Persist the rules (e.g. `/etc/nftables.conf`). Re-run `pynab -public` after
each Pynab upgrade.

## Installation

HACS: add this repository as a custom repository (integration), then install
"Nabaztag (Pynab)". Or copy `custom_components/pynab` to
`<config>/custom_components/pynab` and restart.

## Configuration

Add via Settings -> Devices -> Add Integration -> Nabaztag (Pynab):

- Host (default `nabaztag.local`)
- nabd port (default 10543)
- Web UI base URL (default `http://nabaztag.local`), used for service triggers

## Entities

- Sensor `state`: rabbit state (`idle`, `asleep`, `interactive`, `playing`),
  pushed live over the nabd protocol.

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
- `ears_event` / `ear_event`
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

- TTS uses `tts.async_get_text_to_audio_url`; the rabbit must be able to reach
  your Home Assistant HTTP port on the LAN.
- The nabd protocol has no authentication. Keep the firewall rule in place;
  only the HA machine should be able to reach port 10543.