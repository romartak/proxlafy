# Standalone mode · Modo standalone

## EN

Standalone mode lets the Proxmark3 run **without a host** — no Raspberry Pi, no panel, no computer. You power
it from anything (a wall charger, a battery) and drive it with its own button. You flash a firmware image
compiled with one standalone mode; the normal client/USB still works, and a **long button-press** enters the
mode. Only one mode is compiled in at a time (except `DANKARMULTI`, which bundles several).

**From the panel:** *System → Standalone mode*. Pick a mode and tap **Program**. It recompiles the Iceman
firmware with that mode and flashes it (~15–30 min on a Zero 2 W — don't unplug the Proxmark). The current
mode shows at the top (and in `pm3 -c "hw status"`).

### Recommended modes for this kit
| Mode | Band | What it does |
|---|---|---|
| **LF_SAMYRUN** | LF | Read an HID 26-bit card, then clone to a T5577 or replay it — all with the button. The classic field mode. |
| **LF_EM4100RWC** | LF | Read EM4100 into 16 slots, simulate or clone to T5577 (needs RDV4 flash). |
| **HF_MATTYRUN** | HF | MIFARE Classic: key-dictionary check, dump and emulate, button-driven. |
| **HF_ICECLASS** | HF | iCLASS read / dump / simulate / key attacks (needs RDV4 flash). |

> **Generic PM3 Easy vs RDV4:** modes marked *needs RDV4* use the onboard flash for storage. On a generic
> PM3 Easy (no flash) they run with reduced or no persistent storage; the "Generic" modes (LF_SAMYRUN,
> HF_MATTYRUN, HF_AVEFUL…) are the safe bet.

### How it's built (what the panel runs)
```sh
cd /opt/proxmark3-src
# set STANDALONE=<mode> in Makefile.platform
make clean && make -j
./pm3-flash-all            # flashes bootloader + fullimage
```

### Related GitHub repositories
- **RfidResearchGroup/proxmark3** (★6.3k) — the Iceman firmware; all standalone modes live in `armsrc/Standalone`.
- **Proxmark/proxmark3** (★3.6k) — the original/official firmware.
- **wh201906/Proxmark3GUI** (★1.1k) — cross-platform desktop GUI for the client.
- **RfidResearchGroup/RFIDtools** (★634) — the official RRG **Android** app (the modular app, by sections).
- **TeamWalrus/Walrus** (★491) — Android app to use card-cloning devices in the field.
- **AndProx/AndProx** (★260) — native Android Proxmark3 client (no root).
- **zaureliu/proxmark3-standalone-manager** (★1) — Windows manager for standalone modules (Iceman + ProxSpace).
- **akpotter/github-proxmark3-standalone-lf-emulator** (★7) — pre-compiled LF standalone firmware + easy flasher.
- **Septimus4/PM3-Easy-standalone** (★1) — portable standalone PM3 Easy build (NanoPi + touchscreen, Qt GUI).
- **Dzmert/LF_T55COPY** (★1) — a standalone mode: read a T55xx UID and write it to a blank with the button.

The full list of 41 Iceman standalone modes is in `armsrc/Standalone/readme.md` in the firmware repo.

---

## ES

El modo standalone deja al Proxmark3 funcionar **sin host** — sin Raspberry Pi, sin panel, sin computadora.
Lo alimentas con cualquier cosa (un cargador de pared, una batería) y lo manejas con su propio botón. Se graba
una imagen de firmware compilada con un modo standalone; el cliente/USB normal sigue funcionando, y una
**pulsación larga** entra al modo. Solo se compila un modo a la vez (salvo `DANKARMULTI`, que combina varios).

**Desde el panel:** *Sistema → Modo standalone*. Elige un modo y pulsa **Programar**. Recompila el firmware
Iceman con ese modo y lo graba (~15–30 min en una Zero 2 W — no desconectes el Proxmark). El modo actual se
muestra arriba (y en `pm3 -c "hw status"`).

### Modos recomendados para este kit
| Modo | Banda | Qué hace |
|---|---|---|
| **LF_SAMYRUN** | LF | Lee una HID de 26 bits y luego la clona a una T5577 o la reemite — todo con el botón. El modo de campo clásico. |
| **LF_EM4100RWC** | LF | Lee EM4100 en 16 ranuras, simula o clona a T5577 (necesita flash RDV4). |
| **HF_MATTYRUN** | HF | MIFARE Classic: prueba diccionario de claves, vuelca y emula, con el botón. |
| **HF_ICECLASS** | HF | iCLASS leer / volcar / simular / ataques de clave (necesita flash RDV4). |

> **PM3 Easy genérico vs RDV4:** los modos marcados *necesita RDV4* usan la flash interna para guardar datos.
> En un PM3 Easy genérico (sin flash) corren con almacenamiento reducido o nulo; los modos "Generic"
> (LF_SAMYRUN, HF_MATTYRUN, HF_AVEFUL…) son la apuesta segura.

### Cómo se compila (lo que ejecuta el panel)
```sh
cd /opt/proxmark3-src
# pon STANDALONE=<modo> en Makefile.platform
make clean && make -j
./pm3-flash-all            # graba bootloader + fullimage
```

### Repositorios de GitHub relacionados
(ver la tabla en la sección EN de arriba — los mismos repos, con su descripción).

La lista completa de los 41 modos standalone de Iceman está en `armsrc/Standalone/readme.md` del repo del firmware.
