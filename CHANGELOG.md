# Changelog

All notable changes to Proxlafy. · Cambios importantes de Proxlafy.

## 0.5.2

**Fix: connect to the Proxmark with `-p <port>`**
- The client was launched with the port as a bare argument (`pm3 /dev/pm3-0`), which made it print usage and
  exit (EOF). Now it uses the canonical `pm3 -p <port>`, so it connects to the reader properly.
- El cliente se lanzaba con el puerto “suelto” y el programa imprimía su ayuda y salía. Ahora usa
  `pm3 -p <puerto>` y se conecta bien al lector.

## 0.5.1

**Fix: the panel no longer hangs when no Proxmark is connected**
- With the `pm3` client installed but no reader plugged in, the client's auto-detect scanned Bluetooth and
  blocked, piling up processes and making the panel unresponsive. Now the server resolves the serial port
  first (`/dev/ttyACM*`, `/dev/ttyUSB*`, `/dev/pm3-*`): if there's no device it reports *disconnected*
  instantly, and when a device is present it launches `pm3 <port>` directly (no Bluetooth scan).
- Con el cliente `pm3` instalado pero sin lector conectado, el autodetección escaneaba Bluetooth y se
  colgaba. Ahora resuelve el puerto serie primero y, si no hay lector, responde *desconectado* al instante.

## 0.5.0

**Lab switch · Conmutador de laboratorio (Proxlafy ⇄ SDR-Kit)**
- Both projects can live on the same microSD; a new `labswitch` tool flips which one is active —
  **instantly, offline, with no reinstall** (they share the WiFi hotspot and port 80, so only one runs).
  Los dos proyectos pueden convivir en la misma microSD; `labswitch` cambia cuál está activo **al
  instante, sin internet y sin reinstalar** (comparten el hotspot y el puerto 80, solo corre uno).
- **Secret button in the panel**: long-press (≈1 s) or triple-tap the Proxlafy logo → a sheet to hand
  control to SDR-Kit, warning that the WiFi will change (SSID + address to reconnect to). Admin only.
  **Botón secreto en el panel**: mantén pulsado (≈1 s) o toca tres veces el logo → una hoja para pasar
  el control a SDR-Kit, avisando que la WiFi cambiará (SSID + dirección para reconectarte). Solo admin.
- If the other project isn't installed yet, the button offers to **install it from GitHub** (needs internet).
  Si el otro proyecto aún no está instalado, el botón ofrece **instalarlo desde GitHub** (necesita internet).
- CLI: `sudo proxlafy switch` (cambiar) and `proxlafy labs` (list installed projects).
- The installer pauses the other project automatically so there's no port/hotspot clash. See `docs/conmutador.md`.
- New API: `GET/POST /api/switch`. The switch runs detached (systemd-run) so it survives this panel stopping.

## 0.4.0

**Emit hub · Centro de emisión** (new tab)
- A dedicated **Emitir** tab: a big live-emission hero (with an animated wave) + Stop, a duration selector
  (no limit / 10s / 30s / 60s) and one-tap emit from the library.
- **Keep going without the Pi**: when a card is active, the hub shows the standalone mode that would keep the
  Proxmark emitting it from its own power with no host (the "only the Proxmark is powered" case), with a
  Prepare button. (idea 12 + the power-bank scenario)

**Smarter reads**
- **Wiegand decoder** for HID: shows the 26-bit frame with facility / card / parity highlighted. (17)
- **Continuous scan** toggle and a **read history** in the Scan tab. (1, 4)
- **Auto-verify after cloning**: re-reads the written card and reports match/mismatch. (13)

**Device & UX**
- **Antenna health** (LF/HF voltages) in System. (21)
- **Manual theme** toggle (system / dark / light) and a **Beginner/Expert** mode that hides the raw console
  and commands for newcomers. (26, 27)
- Timed emission auto-stops; the whole thing stays phone-first, bilingual and offline.

## 0.3.0

**Feasibility engine · Motor de viabilidad** (`files/feasibility.py`)
- When you read a card the panel now shows, for **emulate** and **clone** separately: a verdict
  (High/Medium/Low/No), a **success-chance meter (0–100%)**, the **requirements** (a T5577 blank, keys
  recovered, a magic card…) and the **risks / why it might fail** (reader checks data sectors, NTAG ECC
  signature, gen1a detection, encrypted…). Honest, not a guarantee.

**Module workflow · Flujo por módulos**
- Each card lays out its work as sections like the Android Proxmark apps: Identify → Read/Dump → Recover
  keys → Feasibility → Emulate/Clone → Verify, each with a status (done/ready/blocked) and a **Run** button,
  plus **Run workflow** to chain them.

**Scan / Identify tab · Pestaña Escanear**
- Read a card only to classify it (no save). Marks **rewritable blanks as clone candidates** and says what
  they accept — made for sorting a pile of unknown white cards.

**Standalone mode section · Sección de modo standalone**
- Program the Proxmark to run with no host (no Pi, no panel) from any power source and its own button.
  Curated list of Iceman standalone modes (LF_SAMYRUN, HF_MATTYRUN, HF_ICECLASS…), one-tap **Program**
  (build + flash), and a list of the related GitHub repositories. See `docs/standalone.md`.

**Panel · UX**
- In-panel **quick guide** (the `?` button): a bilingual glossary explaining read vs emit, dump, recover
  keys, emulate, clone, blank/candidate, modules, feasibility, LF vs HF and standalone — so the panel
  teaches the terms where you use them.

## 0.2.0

**Card catalog · Catálogo de tarjetas**
- Data-driven registry (`files/catalog.py`) with **29 families** — 19 LF + 10 HF.
- Per-card **capabilities**: emulable, clonable and onto which blank, encrypted/needs-keys, plain-words note.
- **Decode / key recovery**: MIFARE Classic `autopwn`, iCLASS / Ultralight / ISO15693 dumps, DESFire/FeliCa/
  LEGIC enumeration. The panel says when a card must be decoded before it can be emulated or cloned.

**Persistent emulation · Emulación persistente**
- Emitting a card is now remembered on disk (`/var/lib/proxlafy/active_sim.json`). After a power cycle a
  background monitor **resumes emulating the same card automatically** once the Proxmark is back — until you
  cancel it in the panel. The banner shows *EMULATING* (live) or *RESUMING ON CONNECT* (waiting for device).

**Panel / UX**
- Rebuilt GUI: segmented navigation (Read / Library / System) with a gliding pill, a per-card **bottom sheet**
  with all actions, capability chips, data table, decoded data and raw Proxmark output.
- Library search + LF/HF filter; emulation marker on the active card.
- Motion system (entrances, reveals, honest loaders, press feedback) with full `prefers-reduced-motion` support.
- Phone-first layout, EN/ES everywhere, still 100% offline.

**Docs**
- New `docs/installation.md`: flash-to-first-read, bilingual, with troubleshooting.

## 0.1.0
- First version: offline web panel, Proxmark3 (Iceman) wrapper with demo mode, card library, read/emulate/
  write, one-command install, automatic WiFi hotspot, `proxlafy` command, updates with auto-rollback.
