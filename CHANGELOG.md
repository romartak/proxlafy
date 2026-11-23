# Changelog

All notable changes to Proxlafy. · Cambios importantes de Proxlafy.

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
