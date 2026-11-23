#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Proxlafy · Proxmark3 standalone modes · modos standalone del Proxmark3

Standalone mode lets the Proxmark run WITHOUT a host (no Pi, no panel): you power it from anything —
a wall charger, a battery — and drive it with its own button. You flash a firmware image compiled with
one standalone mode; the normal client/USB keeps working too, and a long button-press enters the mode.

El modo standalone deja al Proxmark funcionar SIN host (sin Pi, sin panel): lo alimentas con cualquier
fuente — un cargador de pared, una batería — y lo manejas con su propio botón. Se graba una imagen de
firmware compilada con un modo; el cliente/USB normal sigue funcionando, y una pulsación larga entra al modo.

Mode list is from the Iceman firmware (armsrc/Standalone). `flash:true` modes store data in onboard flash,
present on the RDV4 — on a generic PM3 Easy (no flash) they run with reduced/no persistent storage.

Curated repos (asked for): list in REPOS below.
"""

# Curated subset of the 41 Iceman standalone modes — the ones that fit "read & replay in the field".
# rec = recommended for this kit · flash = needs onboard flash (RDV4); limited on a generic PM3 Easy.
MODES = [
    # ---- LF ----
    {"id": "LF_SAMYRUN", "band": "lf", "rec": True, "flash": False,
     "name_en": "HID read / clone / simulate (SamyRun)", "name_es": "HID leer / clonar / simular (SamyRun)",
     "desc_en": "Read an HID 26-bit card, then clone it to a T5577 or replay it — all with the button. The classic field mode.",
     "desc_es": "Lee una HID de 26 bits y luego la clona a una T5577 o la reemite, todo con el botón. El modo de campo clásico."},
    {"id": "LF_EM4100RWC", "band": "lf", "rec": True, "flash": True,
     "name_en": "EM4100 read / sim / clone (16 slots)", "name_es": "EM4100 leer / simular / clonar (16 ranuras)",
     "desc_en": "Read EM4100 tags into 16 slots, simulate or clone to T5577 with the button.",
     "desc_es": "Lee tags EM4100 en 16 ranuras, simula o clona a T5577 con el botón."},
    {"id": "LF_EM4100EMUL", "band": "lf", "rec": False, "flash": False,
     "name_en": "EM4100 simulate preset IDs", "name_es": "EM4100 simular IDs predefinidos",
     "desc_en": "Simulate a set of EM4100 IDs compiled into the firmware.",
     "desc_es": "Simula un conjunto de IDs EM4100 compilados en el firmware."},
    {"id": "LF_ICEHID", "band": "lf", "rec": False, "flash": True,
     "name_en": "HID credential collector", "name_es": "Recolector de credenciales HID",
     "desc_en": "Walk around collecting LF HID cards into flash to read back later.",
     "desc_es": "Recolecta tarjetas LF HID en la flash para leerlas luego."},
    {"id": "LF_HIDFCBRUTE", "band": "lf", "rec": False, "flash": True,
     "name_en": "HID facility-code bruteforce", "name_es": "Fuerza bruta de facility code HID",
     "desc_en": "Brute-force the HID facility code (0–255) against a reader.",
     "desc_es": "Fuerza bruta del facility code HID (0–255) contra un lector."},
    # ---- HF ----
    {"id": "HF_MATTYRUN", "band": "hf", "rec": True, "flash": False,
     "name_en": "MIFARE Classic check / dump / emulate", "name_es": "MIFARE Classic claves / volcar / emular",
     "desc_en": "Try a key dictionary on a MIFARE Classic, dump it and emulate it — button-driven.",
     "desc_es": "Prueba un diccionario de claves en una MIFARE Classic, la vuelca y la emula, con el botón."},
    {"id": "HF_MFCSIM", "band": "hf", "rec": False, "flash": True,
     "name_en": "MIFARE Classic 1K simulate (15 slots)", "name_es": "Simular MIFARE Classic 1K (15 ranuras)",
     "desc_en": "Simulate MIFARE Classic 1K dumps stored in flash, 15 slots.",
     "desc_es": "Simula volcados de MIFARE Classic 1K guardados en flash, 15 ranuras."},
    {"id": "HF_ICECLASS", "band": "hf", "rec": True, "flash": True,
     "name_en": "iCLASS simulate / dump / attack", "name_es": "iCLASS simular / volcar / atacar",
     "desc_en": "Multi-mode iCLASS: read, dump, simulate and key attacks from the button.",
     "desc_es": "iCLASS multimodo: leer, volcar, simular y ataques de clave desde el botón."},
    {"id": "HF_AVEFUL", "band": "hf", "rec": False, "flash": False,
     "name_en": "MIFARE Ultralight read / emulate", "name_es": "MIFARE Ultralight leer / emular",
     "desc_en": "Read a MIFARE Ultralight and emulate it.",
     "desc_es": "Lee una MIFARE Ultralight y la emula."},
    {"id": "HF_TMUDFORD", "band": "hf", "rec": False, "flash": False,
     "name_en": "ISO15693 read / emulate UID", "name_es": "ISO15693 leer / emular UID",
     "desc_en": "Read an ISO15693 tag UID and emulate it.",
     "desc_es": "Lee el UID de un tag ISO15693 y lo emula."},
    {"id": "HF_14ASNIFF", "band": "hf", "rec": False, "flash": True,
     "name_en": "ISO14443A sniffer", "name_es": "Sniffer ISO14443A",
     "desc_en": "Passively sniff 14A traffic to flash for later analysis.",
     "desc_es": "Esnifa pasivamente tráfico 14A a la flash para analizarlo luego."},
    # ---- Multi ----
    {"id": "DANKARMULTI", "band": "multi", "rec": False, "flash": True,
     "name_en": "Multi-mode loader", "name_es": "Cargador multi-modo",
     "desc_en": "Bundle several standalone modes in one image and switch with the button.",
     "desc_es": "Combina varios modos standalone en una imagen y cambia con el botón."},
]

MODES_BY_ID = {m["id"]: m for m in MODES}

# Related GitHub repositories (research) · Repositorios de GitHub relacionados (investigación)
REPOS = [
    {"name": "RfidResearchGroup/proxmark3", "stars": 6262,
     "what_en": "The Iceman firmware — all standalone modes live here (armsrc/Standalone).",
     "what_es": "El firmware Iceman — todos los modos standalone están aquí (armsrc/Standalone)."},
    {"name": "Proxmark/proxmark3", "stars": 3567,
     "what_en": "The original/official Proxmark3 firmware.",
     "what_es": "El firmware Proxmark3 original/oficial."},
    {"name": "wh201906/Proxmark3GUI", "stars": 1070,
     "what_en": "Cross-platform desktop GUI for the Proxmark3 client.",
     "what_es": "GUI de escritorio multiplataforma para el cliente Proxmark3."},
    {"name": "RfidResearchGroup/RFIDtools", "stars": 634,
     "what_en": "The official RRG Android app (the modular app you described).",
     "what_es": "La app oficial RRG para Android (la app por módulos que describiste)."},
    {"name": "TeamWalrus/Walrus", "stars": 491,
     "what_en": "Android app to use card-cloning devices in the field.",
     "what_es": "App Android para usar dispositivos de clonado de tarjetas en campo."},
    {"name": "AndProx/AndProx", "stars": 260,
     "what_en": "Native Android Proxmark3 client (no root).",
     "what_es": "Cliente Proxmark3 nativo para Android (sin root)."},
    {"name": "zaureliu/proxmark3-standalone-manager", "stars": 1,
     "what_en": "Windows manager for Proxmark3 standalone modules (Iceman + ProxSpace).",
     "what_es": "Gestor de Windows para módulos standalone del Proxmark3 (Iceman + ProxSpace)."},
    {"name": "akpotter/github-proxmark3-standalone-lf-emulator", "stars": 7,
     "what_en": "Pre-compiled LF standalone emulation/cloning firmware + easy flasher.",
     "what_es": "Firmware precompilado de emulación/clonado LF standalone + flasher fácil."},
    {"name": "Septimus4/PM3-Easy-standalone", "stars": 1,
     "what_en": "Portable standalone PM3 Easy build (NanoPi + touchscreen, Qt GUI).",
     "what_es": "Build portátil standalone para PM3 Easy (NanoPi + pantalla táctil, GUI Qt)."},
    {"name": "Dzmert/LF_T55COPY", "stars": 1,
     "what_en": "A standalone mode: read a T55xx UID and write it to a blank with the button.",
     "what_es": "Un modo standalone: lee el UID de un T55xx y lo escribe en un blanco con el botón."},
]


def catalog(lang="es"):
    """Modes + repos shaped for the panel in one language."""
    def mode(m):
        return {"id": m["id"], "band": m["band"], "rec": m["rec"], "flash": m["flash"],
                "name": m["name_es"] if lang == "es" else m["name_en"],
                "desc": m["desc_es"] if lang == "es" else m["desc_en"]}
    def repo(r):
        return {"name": r["name"], "stars": r["stars"], "what": r["what_es"] if lang == "es" else r["what_en"]}
    return {"modes": [mode(m) for m in MODES], "repos": [repo(r) for r in REPOS]}


def parse_current(hw_status_output):
    """Extract the standalone mode name the firmware reports in `hw status`, or None."""
    import re
    m = re.search(r"Standalone mode[.\s]*\.*\s*([A-Z0-9_]+)", hw_status_output or "", re.I)
    if m and m.group(1).upper() not in ("NONE", "NO"):
        return m.group(1).upper()
    return None
