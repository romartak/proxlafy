# Changelog

All notable changes to Proxlafy. · Cambios importantes de Proxlafy.

## 0.8.0

**Design & UX polish (web-ui-motion) · Pulido de diseño y UX**
- **Keyboard focus rings** on every control (accessibility), consistent **press feedback** on chips and tabs,
  **bottom-sheet content now arrives in reading order**, and **skeleton loaders** — all honouring reduced-motion.
- Anillos de **foco de teclado** en cada control, **feedback al pulsar** uniforme, contenido de la hoja que
  entra en orden de lectura y **loaders tipo skeleton**; todo respeta "reduce motion".

**Compare two cards · Comparar dos tarjetas**
- In the Library, **Compare** mode: pick two cards and see them side by side (type, band, UID, FC, CN,
  feasibility, tags) with the differences highlighted.
- En la Biblioteca, modo **Comparar**: elige dos tarjetas y las ves lado a lado con las diferencias resaltadas.

**More robust updates · Actualizaciones más robustas**
- The updater now **prefers IPv4**, so a home router that hands out broken IPv6 no longer makes it say
  "no internet". · El actualizador **prefiere IPv4**: un router con IPv6 roto ya no lo bloquea.

**Tested**
- Automated click-through of every button in every view (no console errors). · Prueba automática de todos los
  botones de todas las vistas (sin errores de consola).

## 0.7.0

**Wipe a blank and re-clone · Limpiar un blanco y reclonar** (your request)
- New **Wipe a physical card** tool (Emit tab): erases a rewritable/magic card back to blank
  (T5577, EM4305, magic MIFARE gen1a). Then pick any saved card in the Library → **Clone to physical card**
  to write it on top. `POST /api/wipe`, `GET /api/wipe`.
- Nueva herramienta **Limpiar tarjeta física**: deja en blanco una regrabable/magic; luego eliges una de la
  biblioteca y la **clonas** encima.

**Library power-ups · Biblioteca con superpoderes**
- **Search by name, UID, FC, CN or tag.** · Búsqueda por nombre, UID, FC, CN o etiqueta.
- **Tags** per card (add in the card sheet; shown as chips). · **Etiquetas** por tarjeta.
- **Export / Import** the whole library as a JSON file (backup or move between Pis). `GET /api/library/export`,
  `POST /api/library/import`. · **Exportar / Importar** toda la biblioteca como archivo JSON.

**GUI & motion · Interfaz y animaciones**
- View entrance transitions, tag-chip pop-in, card press feedback, a pulsing "connected" dot — all respecting
  reduced-motion. · Transiciones de entrada, feedback al pulsar y punto de "conectado" con pulso.

**Fixes**
- Reader detection is robust across RDV4 and Easy/generic boards (shown in 0.6.0, kept here).

## 0.6.0

**Update from the panel · Actualizar desde el panel**
- New **Updates** controls in System: **Check for updates** (shows current → latest and the list of changes)
  and **Update now** — it pulls from GitHub, shows the live log, restarts, and **reloads the page by itself**
  when the panel comes back. Auto-rollback still protects a bad update. No SSH needed. (`GET`/`POST /api/update`,
  `GET /api/update/log`.)
- Nueva sección **Actualizaciones** en Sistema: **Buscar actualizaciones** y **Actualizar ahora**, con registro
  en vivo y recarga automática del panel al terminar. Sin necesidad de SSH. Mantiene el auto-rollback.

**Fix: the reader now shows as connected when it works**
- Device detection no longer depends on exact wording of `hw status` (which varies between RDV4 and
  Easy/generic boards). If the Proxmark answers `hw status` at all, the panel shows it **connected**.
- La detección ya no depende del texto exacto de `hw status`; si el Proxmark responde, el panel lo marca
  **conectado** (antes podía leer tarjetas y aun así decir "no detectado").

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
