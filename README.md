<div align="center">

# Proxlafy

**A pocket RFID workbench — a Raspberry Pi Zero 2 W + a Proxmark3 (Iceman) + a power bank, driven from your phone.**

Read, catalogue, clone and emulate LF (125 kHz) and HF (13.56 MHz) cards from an offline web panel, with
an automatic WiFi hotspot and self-rollback updates.

[🇪🇸 Leer en español](README.es.md) · [Hardware](docs/hardware.md) · [Updating](docs/updating.md)

</div>

> [!IMPORTANT]
> **Authorized use only.** Proxlafy is built for a private lab: your own cards and readers, or engagements
> where you have explicit written permission (pentesting, research, training). Using it against access
> systems you do not own or are not authorized to test is illegal. You are responsible for how you use it.

---

## What it does

- **Read** a card on the antenna (LF, HF or auto) and identify it: HID Prox, EM410x, Indala, T55x7,
  MIFARE Classic/DESFire, iCLASS, NTAG/Ultralight…
- **Library** — save each read with a name and notes; everything is stored on the Pi and survives updates.
- **Emulate** — pick any saved card and the Proxmark emulates it; a banner shows what is live, one tap stops it.
- **Write** — clone a saved LF credential onto a blank **T5577** (and HF onto magic cards where supported).
- **From your phone** — the Pi serves an offline panel over its own WiFi hotspot; nothing leaves the device.

> [!NOTE]
> **No hardware yet?** Run the panel in demo mode on any computer:
> `PROXLAFY_DEMO=1 python3 files/proxlafy_server.py --port 8080` → http://localhost:8080

## Hardware

| Part | Notes |
|---|---|
| Raspberry Pi Zero 2 W | Onboard WiFi (used as the hotspot) |
| Proxmark3 (Iceman firmware) | Connected to the Pi's **USB/data** micro-USB via an OTG adapter |
| Power bank | To the Pi's **PWR** micro-USB (separate from the data port) |
| USB WiFi dongle | *Optional* — as the internet client, so the Pi can auto-update while the onboard WiFi stays the hotspot |
| Blank **T5577** cards | For writing LF clones |

See [docs/hardware.md](docs/hardware.md) for wiring and the firmware check.

## Installation

On the Pi, over SSH, one command:

```sh
curl -fsSL https://raw.githubusercontent.com/romartak/proxlafy/main/get.sh | sudo bash
```

It installs the dependencies, offers to build the Iceman `pm3` client, sets up the WiFi hotspot and the
services, and asks for a panel password. Then open **http://192.168.4.1** on the `Proxlafy` hotspot.

You can pre-fill answers by editing [`proxlafy.conf`](proxlafy.conf) first (also from your PC on the
microSD's `bootfs` partition).

## The `proxlafy` command

```sh
proxlafy status       # device and service state
proxlafy logs         # live journal
sudo proxlafy update  # update from GitHub (checks the new panel, auto-rolls-back if it fails)
sudo proxlafy rollback
sudo proxlafy hotspot # force the hotspot ("auto" releases it)
sudo proxlafy config  # edit proxlafy.conf
```
Spanish aliases work too (`actualizar`, `volver`, `estado`, `configurar`).

## Updates that cannot brick your kit

`sudo proxlafy update` fetches the latest commit, keeps your config and card library, installs it, then
polls `/api/status`. If the new panel does not answer within ~60 s it **restores the previous version
automatically**. Details in [docs/updating.md](docs/updating.md).

## How it works

- **Panel** — `files/proxlafy_server.py`: pure Python standard library (`http.server`), serves the offline
  web app in `files/web/` and a small JSON API. Light enough for the Zero 2 W.
- **Reader** — `files/pm3.py`: keeps one persistent Iceman `pm3` client session (via `pexpect`) and
  serializes every device command through it. A demo backend lets the UI run with no hardware.
- **Network** — `files/proxlafy-netwatch.sh`: at boot joins a known WiFi; otherwise raises its own hotspot,
  and keeps the Pi reachable either way (NetworkManager).
- **Updates** — `files/proxlafy-update.sh`: commit-based, with a health check and automatic rollback.

## Layout

```
proxlafy/
├── install.sh · get.sh · proxlafy.conf · VERSION
├── files/
│   ├── proxlafy_server.py   # web panel + JSON API
│   ├── pm3.py               # Proxmark3 (Iceman) wrapper, with demo mode
│   ├── proxlafy-lib.sh      # shared bash (config, language, hotspot)
│   ├── proxlafy-cli.sh      # the `proxlafy` command
│   ├── proxlafy-update.sh   # updater with auto-rollback
│   ├── proxlafy-netwatch.sh # known WiFi / automatic hotspot
│   ├── *.service            # systemd units
│   └── web/                 # offline panel (HTML/CSS/JS, EN+ES)
└── docs/
```

## License

MIT — see [LICENSE](LICENSE).
