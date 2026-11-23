# Changelog

All notable changes to Proxlafy. · Cambios importantes de Proxlafy.

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
