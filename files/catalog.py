#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Proxlafy · RFID card catalog · catálogo de tarjetas RFID

A data-driven registry of the card families the Proxmark3 (Iceman) can work with. Each entry knows how to
be recognized in a `lf search` / `hf search` output, which fields to pull out, whether it can be emulated or
cloned and onto what blank, whether it is encrypted (needs key recovery / a decode step), and a plain-words
note in EN/ES. pm3.py uses this registry so adding a card type is just adding a dict here.

Registro data-driven de las familias de tarjetas que el Proxmark3 (Iceman) puede manejar. Cada entrada sabe
reconocerse en la salida de `lf search`/`hf search`, qué campos extraer, si se puede emular o clonar y sobre
qué tarjeta en blanco, si va cifrada (necesita recuperar claves / un paso de descifrado) y una nota en EN/ES.

Command syntax targets the Iceman/RRG client. Where a family's emulation or cloning is not practical, it is
marked so the panel can explain why instead of pretending.
"""

import re


def _hid_sim(f):
    if f.get("fc") and f.get("cn"):
        return "lf hid sim -w %s --fc %s --cn %s" % (f.get("format", "H10301"), f["fc"], f["cn"])
    if f.get("raw"):
        return "lf hid sim -r %s" % f["raw"]
    return None


def _hid_clone(f):
    if f.get("fc") and f.get("cn"):
        return "lf hid clone -w %s --fc %s --cn %s" % (f.get("format", "H10301"), f["fc"], f["cn"])
    if f.get("raw"):
        return "lf hid clone -r %s" % f["raw"]
    return None


# Each entry:
#   key, name, band ('lf'|'hf')
#   sig:    regex that identifies the family in a search output (case-insensitive)
#   fields: {name: regex-with-one-group} pulled from the search output
#   sim / clone: format string using {field} OR a callable(fields)->cmd OR None
#   target: the blank it clones onto (label) or None
#   secure: True if encrypted / needs keys before it can be read or cloned
#   decode: operation key pm3.py knows how to run (e.g. 'mf_autopwn') or None
#   notes_en / notes_es: one line of guidance
CATALOG = [
    # ================================ LF · 125 kHz ================================
    {
        "key": "hid_prox", "name": "HID Prox", "band": "lf",
        "sig": r"HID\s*Prox|HID\s+[A-Za-z0-9]+\s+\d+-bit|\bHID\b.*FC:",
        "fields": {"format": r"HID\s+([A-Za-z0-9]+)\s+\d+-bit", "fc": r"FC:\s*(\d+)",
                   "cn": r"CN:\s*(\d+)", "raw": r"raw:\s*([0-9A-Fa-f]+)"},
        "sim": _hid_sim, "clone": _hid_clone, "target": "T5577", "secure": False, "decode": None,
        "notes_en": "Open 125 kHz format. Fully clonable to a T5577 and emulable.",
        "notes_es": "Formato abierto de 125 kHz. Totalmente clonable a T5577 y emulable.",
    },
    {
        "key": "em410x", "name": "EM410x", "band": "lf",
        "sig": r"EM\s*410x|EM4100",
        "fields": {"id": r"EM\s*410x.*?ID[:\s]+([0-9A-Fa-f]+)|\bID[:\s]+([0-9A-Fa-f]{10})\b"},
        "sim": "lf em 410x sim --id {id}", "clone": "lf em 410x clone --id {id}",
        "target": "T5577 / EM4305", "secure": False, "decode": None,
        "notes_en": "The classic 125 kHz tag. Clone to T5577 or EM4305; emulable.",
        "notes_es": "El tag clásico de 125 kHz. Clónalo a T5577 o EM4305; emulable.",
    },
    {
        "key": "indala", "name": "Indala", "band": "lf",
        "sig": r"Indala",
        "fields": {"raw": r"Raw[:\s]+([0-9A-Fa-f]+)", "fc": r"FC:\s*(\d+)", "cn": r"(?:Card|CN):\s*(\d+)"},
        "sim": "lf indala sim -r {raw}", "clone": "lf indala clone -r {raw}",
        "target": "T5577", "secure": False, "decode": None,
        "notes_en": "Motorola/Indala 125 kHz. Clone the raw to a T5577.",
        "notes_es": "Indala/Motorola 125 kHz. Clona el 'raw' a una T5577.",
    },
    {
        "key": "awid", "name": "AWID", "band": "lf",
        "sig": r"\bAWID\b",
        "fields": {"fmt": r"AWID\s+(\d+)", "fc": r"FC:\s*(\d+)", "cn": r"(?:Card|CN):\s*(\d+)"},
        "sim": "lf awid sim --fmt {fmt} --fc {fc} --cn {cn}",
        "clone": "lf awid clone --fmt {fmt} --fc {fc} --cn {cn}",
        "target": "T5577", "secure": False, "decode": None,
        "notes_en": "AWID 125 kHz. Clonable to T5577 and emulable.",
        "notes_es": "AWID 125 kHz. Clonable a T5577 y emulable.",
    },
    {
        "key": "ioprox", "name": "ioProx (Kantech)", "band": "lf",
        "sig": r"ioProx|IO\s*Prox",
        "fields": {"vn": r"(?:XSF|version)[:\s(]*(\d+)", "fc": r"FC:\s*(\d+)", "cn": r"(?:Card|CN):\s*(\d+)"},
        "sim": "lf io sim --vn {vn} --fc {fc} --cn {cn}",
        "clone": "lf io clone --vn {vn} --fc {fc} --cn {cn}",
        "target": "T5577", "secure": False, "decode": None,
        "notes_en": "Kantech ioProx 125 kHz. Clonable to T5577.",
        "notes_es": "Kantech ioProx 125 kHz. Clonable a T5577.",
    },
    {
        "key": "paradox", "name": "Paradox", "band": "lf",
        "sig": r"Paradox",
        "fields": {"fc": r"FC:\s*(\d+)", "cn": r"(?:Card|CN):\s*(\d+)", "raw": r"Raw[:\s]+([0-9A-Fa-f]+)"},
        "sim": "lf paradox sim --raw {raw}", "clone": "lf paradox clone --raw {raw}",
        "target": "T5577", "secure": False, "decode": None,
        "notes_en": "Paradox 125 kHz. Clone the raw to a T5577.",
        "notes_es": "Paradox 125 kHz. Clona el 'raw' a una T5577.",
    },
    {
        "key": "pyramid", "name": "Pyramid (Farpointe)", "band": "lf",
        "sig": r"Pyramid",
        "fields": {"fc": r"FC:\s*(\d+)", "cn": r"(?:Card|CN):\s*(\d+)"},
        "sim": "lf pyramid sim --fc {fc} --cn {cn}", "clone": "lf pyramid clone --fc {fc} --cn {cn}",
        "target": "T5577", "secure": False, "decode": None,
        "notes_en": "Farpointe Pyramid 125 kHz. Clonable to T5577.",
        "notes_es": "Farpointe Pyramid 125 kHz. Clonable a T5577.",
    },
    {
        "key": "viking", "name": "Viking", "band": "lf",
        "sig": r"Viking",
        "fields": {"id": r"(?:ID|Card)[:\s]+([0-9A-Fa-f]+)"},
        "sim": "lf viking sim --cn {id}", "clone": "lf viking clone --cn {id}",
        "target": "T5577", "secure": False, "decode": None,
        "notes_en": "Viking 125 kHz. Clonable to T5577.",
        "notes_es": "Viking 125 kHz. Clonable a T5577.",
    },
    {
        "key": "noralsy", "name": "Noralsy", "band": "lf",
        "sig": r"Noralsy",
        "fields": {"id": r"Card[:\s]+([0-9A-Fa-f]+)", "year": r"year[:\s]+(\d+)"},
        "sim": "lf noralsy sim --cn {id}", "clone": "lf noralsy clone --cn {id}",
        "target": "T5577", "secure": False, "decode": None,
        "notes_en": "Noralsy 125 kHz. Clonable to T5577.",
        "notes_es": "Noralsy 125 kHz. Clonable a T5577.",
    },
    {
        "key": "jablotron", "name": "Jablotron", "band": "lf",
        "sig": r"Jablotron",
        "fields": {"id": r"(?:ID|Card)[:\s]+([0-9A-Fa-f]+)"},
        "sim": "lf jablotron sim --cn {id}", "clone": "lf jablotron clone --cn {id}",
        "target": "T5577", "secure": False, "decode": None,
        "notes_en": "Jablotron 125 kHz. Clonable to T5577.",
        "notes_es": "Jablotron 125 kHz. Clonable a T5577.",
    },
    {
        "key": "keri", "name": "Keri", "band": "lf",
        "sig": r"\bKeri\b",
        "fields": {"fc": r"FC:\s*(\d+)", "cn": r"(?:Card|CN):\s*(\d+)"},
        "sim": "lf keri sim --fc {fc} --cn {cn}", "clone": "lf keri clone --fc {fc} --cn {cn}",
        "target": "T5577", "secure": False, "decode": None,
        "notes_en": "Keri 125 kHz. Clonable to T5577.",
        "notes_es": "Keri 125 kHz. Clonable a T5577.",
    },
    {
        "key": "nexwatch", "name": "Nexwatch (Honeywell)", "band": "lf",
        "sig": r"Nexwatch|NexWatch|Quadrakey|Honeywell",
        "fields": {"id": r"(?:ID|Card)[:\s]+([0-9A-Fa-f]+)", "mode": r"mode[:\s]+(\d+)"},
        "sim": "lf nexwatch sim --raw {raw}", "clone": "lf nexwatch clone --cn {id} --nc {mode}",
        "target": "T5577", "secure": False, "decode": None,
        "notes_en": "Honeywell/Nexwatch 125 kHz. Clonable to T5577.",
        "notes_es": "Honeywell/Nexwatch 125 kHz. Clonable a T5577.",
    },
    {
        "key": "securakey", "name": "Securakey", "band": "lf",
        "sig": r"Securakey",
        "fields": {"raw": r"Raw[:\s]+([0-9A-Fa-f]+)"},
        "sim": "lf securakey sim --raw {raw}", "clone": "lf securakey clone --raw {raw}",
        "target": "T5577", "secure": False, "decode": None,
        "notes_en": "Securakey 125 kHz. Clonable to T5577.",
        "notes_es": "Securakey 125 kHz. Clonable a T5577.",
    },
    {
        "key": "gallagher", "name": "Gallagher", "band": "lf",
        "sig": r"Gallagher",
        "fields": {"rc": r"region[:\s]+(\d+)", "fc": r"FC:\s*(\d+)", "cn": r"(?:Card|CN):\s*(\d+)",
                   "il": r"issue[:\s]+(\d+)"},
        "sim": None, "clone": "lf gallagher clone --fc {fc} --cn {cn} --rc {rc} --il {il}",
        "target": "T5577", "secure": False, "decode": None,
        "notes_en": "Gallagher 125 kHz. Clonable to T5577 (sim limited).",
        "notes_es": "Gallagher 125 kHz. Clonable a T5577 (sim limitada).",
    },
    {
        "key": "presco", "name": "Presco", "band": "lf",
        "sig": r"Presco",
        "fields": {"id": r"Card[:\s]+([0-9A-Fa-f]+)"},
        "sim": "lf presco sim --cn {id}", "clone": "lf presco clone --cn {id}",
        "target": "T5577", "secure": False, "decode": None,
        "notes_en": "Presco 125 kHz. Clonable to T5577.",
        "notes_es": "Presco 125 kHz. Clonable a T5577.",
    },
    {
        "key": "fdxb", "name": "FDX-B (animal)", "band": "lf",
        "sig": r"FDX-?B|Animal",
        "fields": {"id": r"(?:Animal ID|National Code)[:\s]+([0-9A-Fa-f.]+)",
                   "country": r"Country(?: code)?[:\s]+(\d+)"},
        "sim": "lf fdxb sim --national {id} --country {country}",
        "clone": "lf fdxb clone --national {id} --country {country}",
        "target": "T5577", "secure": False, "decode": None,
        "notes_en": "Animal/pet microchip (FDX-B). Clonable to T5577.",
        "notes_es": "Microchip animal/mascota (FDX-B). Clonable a T5577.",
    },
    {
        "key": "visa2000", "name": "Visa2000", "band": "lf",
        "sig": r"Visa2000",
        "fields": {"id": r"Card[:\s]+([0-9A-Fa-f]+)"},
        "sim": "lf visa2000 sim --cn {id}", "clone": "lf visa2000 clone --cn {id}",
        "target": "T5577", "secure": False, "decode": None,
        "notes_en": "Visa2000 125 kHz. Clonable to T5577.",
        "notes_es": "Visa2000 125 kHz. Clonable a T5577.",
    },
    {
        "key": "em4x05", "name": "EM4x05 / EM4x50", "band": "lf",
        "sig": r"EM4x05|EM4205|EM4305|EM4x50|EM4450",
        "fields": {"raw": r"(?:word 0|block 0|UID)[:\s]+([0-9A-Fa-f]+)"},
        "sim": None, "clone": None, "target": "same chip (writable)", "secure": False, "decode": "em4x05_dump",
        "notes_en": "Writable EM chip. Read/write per-word; often the blank for EM410x clones.",
        "notes_es": "Chip EM regrabable. Lectura/escritura por palabra; suele ser el blanco de clones EM410x.",
    },
    {
        "key": "t55xx", "name": "T55x7 (blank/raw)", "band": "lf",
        "sig": r"T55[x0-9]{2}|Chipset.*T55",
        "fields": {"raw": r"(?:block 0|raw)[:\s]+([0-9A-Fa-f]+)"},
        "sim": None, "clone": None, "target": "same chip", "secure": False, "decode": "t55xx_dump",
        "notes_en": "The universal 125 kHz rewritable chip — the blank most LF clones are written to.",
        "notes_es": "El chip regrabable universal de 125 kHz — el blanco al que se escriben casi todos los clones LF.",
    },

    # ================================ HF · 13.56 MHz ================================
    {
        "key": "mifare_classic", "name": "MIFARE Classic", "band": "hf",
        "sig": r"MIFARE\s+Classic",
        "fields": {"uid": r"UID[:\s]+([0-9A-Fa-f ]+)", "size": r"(1K|4K|Mini)"},
        "sim": "hf mf sim --1k -u {uid}", "clone": "hf mf cload",
        "target": "magic gen1a / gen2", "secure": True, "decode": "mf_autopwn",
        "notes_en": "Encrypted sectors. Recover keys (autopwn) and dump first; then emulate or clone to a magic card.",
        "notes_es": "Sectores cifrados. Primero recupera claves (autopwn) y vuelca; luego emula o clona a una tarjeta magic.",
    },
    {
        "key": "mifare_ultralight", "name": "MIFARE Ultralight / NTAG", "band": "hf",
        "sig": r"MIFARE\s+Ultralight|NTAG\s*\d|Ultralight",
        "fields": {"uid": r"UID[:\s]+([0-9A-Fa-f ]+)", "type": r"(NTAG\s*\d+|Ultralight(?:\s*C| EV1)?)"},
        "sim": "hf mfu sim -t 7 -u {uid}", "clone": "hf mfu restore",
        "target": "magic Ultralight / NTAG", "secure": False, "decode": "mfu_dump",
        "notes_en": "Mostly open. Dump and clone to a magic UL/NTAG; emulable. Password-protected pages need the PWD.",
        "notes_es": "Casi abierta. Vuelca y clona a una UL/NTAG magic; emulable. Las páginas con contraseña necesitan el PWD.",
    },
    {
        "key": "mifare_desfire", "name": "MIFARE DESFire", "band": "hf",
        "sig": r"DESFire",
        "fields": {"uid": r"UID[:\s]+([0-9A-Fa-f ]+)", "ver": r"(EV1|EV2|EV3)"},
        "sim": None, "clone": None, "target": None, "secure": True, "decode": "mfdes_enum",
        "notes_en": "Strong crypto (AES/3DES). You can enumerate apps/UID but NOT clone it without the keys.",
        "notes_es": "Criptografía fuerte (AES/3DES). Puedes enumerar apps/UID pero NO clonarla sin las claves.",
    },
    {
        "key": "mifare_plus", "name": "MIFARE Plus", "band": "hf",
        "sig": r"MIFARE\s+Plus",
        "fields": {"uid": r"UID[:\s]+([0-9A-Fa-f ]+)", "sl": r"SL\s*(\d)"},
        "sim": None, "clone": None, "target": None, "secure": True, "decode": "mfp_info",
        "notes_en": "AES-secured. In SL3 it is not clonable; identify and read what is open.",
        "notes_es": "Protegida con AES. En SL3 no es clonable; identifica y lee lo abierto.",
    },
    {
        "key": "iclass", "name": "HID iCLASS", "band": "hf",
        "sig": r"iCLASS|PicoPass",
        "fields": {"csn": r"CSN[:\s]+([0-9A-Fa-f ]+)", "config": r"Config[:\s]+([0-9A-Fa-f ]+)"},
        "sim": "hf iclass sim -t 3", "clone": "hf iclass restore",
        "target": "writable iCLASS (2ks)", "secure": True, "decode": "iclass_dump",
        "notes_en": "13.56 MHz HID. Legacy/Elite need keys to read blocks; dump then clone to a writable iCLASS.",
        "notes_es": "HID de 13.56 MHz. Legacy/Elite necesitan claves para leer bloques; vuelca y clona a una iCLASS regrabable.",
    },
    {
        "key": "iso15693", "name": "ISO15693 / iCODE", "band": "hf",
        "sig": r"ISO\s*15693|iCODE|SLIX|Tag-it",
        "fields": {"uid": r"UID[:\s]+([0-9A-Fa-f ]+)"},
        "sim": "hf 15 sim -u {uid}", "clone": None, "target": "magic ISO15693", "secure": False, "decode": "iso15_dump",
        "notes_en": "Vicinity tag (iCODE SLIX). Readable/emulable; clone only to a magic 15693.",
        "notes_es": "Tag de vecindad (iCODE SLIX). Legible/emulable; clona solo a una 15693 magic.",
    },
    {
        "key": "felica", "name": "FeliCa", "band": "hf",
        "sig": r"FeliCa|Felica",
        "fields": {"idm": r"IDm[:\s]+([0-9A-Fa-f ]+)"},
        "sim": None, "clone": None, "target": None, "secure": True, "decode": "felica_info",
        "notes_en": "Sony FeliCa (transit/payment). Identify/read-only; not clonable.",
        "notes_es": "Sony FeliCa (transporte/pago). Identificar/solo lectura; no clonable.",
    },
    {
        "key": "topaz", "name": "Topaz (NFC Type 1)", "band": "hf",
        "sig": r"Topaz|Type\s*1",
        "fields": {"uid": r"UID[:\s]+([0-9A-Fa-f ]+)"},
        "sim": None, "clone": None, "target": None, "secure": False, "decode": "topaz_dump",
        "notes_en": "Topaz/Jewel NFC Type 1. Readable; limited cloning support.",
        "notes_es": "Topaz/Jewel NFC Tipo 1. Legible; clonado con soporte limitado.",
    },
    {
        "key": "legic", "name": "LEGIC Prime/Advant", "band": "hf",
        "sig": r"LEGIC|Legic",
        "fields": {"uid": r"(?:UID|MCD)[:\s]+([0-9A-Fa-f ]+)"},
        "sim": None, "clone": None, "target": None, "secure": True, "decode": "legic_info",
        "notes_en": "LEGIC 13.56 MHz. Prime is partly readable; Advant is secured. Identify/read.",
        "notes_es": "LEGIC 13.56 MHz. Prime es parcialmente legible; Advant va protegida. Identificar/leer.",
    },
    {
        "key": "iso14443b", "name": "ISO14443-B (SRx)", "band": "hf",
        "sig": r"14443-?B|SRI\d|SRT\d|ST25",
        "fields": {"uid": r"(?:UID|ChipID)[:\s]+([0-9A-Fa-f ]+)"},
        "sim": None, "clone": None, "target": None, "secure": False, "decode": "iso14b_info",
        "notes_en": "ISO14443-B (ST SRI). Read/identify.",
        "notes_es": "ISO14443-B (ST SRI). Leer/identificar.",
    },
]

CATALOG_BY_KEY = {c["key"]: c for c in CATALOG}


def _clean_hex(v):
    return re.sub(r"\s+", "", v).upper() if v else v


def classify(output, band):
    """Return (entry, fields) for the first catalog type that matches the search output, else (None, {})."""
    out = output or ""
    for entry in CATALOG:
        if entry["band"] != band:
            continue
        if not re.search(entry["sig"], out, re.I):
            continue
        fields = {}
        for name, pat in entry.get("fields", {}).items():
            m = re.search(pat, out, re.I)
            if m:
                val = next((g for g in m.groups() if g), None)
                if val is not None:
                    val = val.strip()
                    if name in ("uid", "csn", "idm", "raw"):
                        val = _clean_hex(val)
                    fields[name] = val
        return entry, fields
    return None, {}


def capabilities(entry, fields):
    """Describe what can be done with this card, for the panel."""
    if not entry:
        return {}
    emulable = entry["sim"] is not None
    clonable = entry["clone"] is not None
    return {
        "key": entry["key"], "band": entry["band"],
        "emulable": emulable, "clonable": clonable,
        "target": entry.get("target"), "secure": entry.get("secure", False),
        "decode": entry.get("decode"),
        "notes_en": entry.get("notes_en", ""), "notes_es": entry.get("notes_es", ""),
    }


def build_cmd(kind, entry, fields):
    """kind = 'sim' | 'clone'. Returns the Iceman command string or None."""
    tpl = entry.get(kind)
    if tpl is None:
        return None
    if callable(tpl):
        return tpl(fields)
    try:
        return tpl.format(**fields)
    except (KeyError, IndexError):
        return None  # missing field the command needs
