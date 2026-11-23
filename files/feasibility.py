#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Proxlafy · feasibility engine + module workflow · motor de viabilidad + flujo por módulos

Given a classified card, this answers the questions the user actually cares about before they try:
can it be emulated? can it be cloned, and onto what? how likely is it to WORK against a real reader,
what do you need, and why might it fail? It also lays out the work as sections/modules (like the
Android Proxmark apps): Identify → Dump → Recover keys → Feasibility → Emulate/Clone → Verify.

Dado una tarjeta clasificada, responde lo que de verdad importa antes de intentar: ¿se puede emular?,
¿clonar y a qué?, ¿qué probabilidad hay de que funcione en un lector real?, ¿qué necesitas y por qué
podría fallar? Y organiza el trabajo en secciones/módulos, como las apps de Android para Proxmark.

Scores are heuristics for authorized lab testing — the panel is honest, not a guarantee.
"""


def _R(en, es, level="info"):
    """A requirement or risk line, bilingual, with a level for colouring (info|low|med|high)."""
    return {"en": en, "es": es, "level": level}


# Per-card-type feasibility data. base = score 0-100 assuming the card is fully read/decoded.
# req = what you need to pull it off. risk = why it might still fail against a real reader.
FEAS = {
    # ---------------- LF (clone target is almost always a T5577; no challenge-response) ----------------
    "hid_prox": {
        "emulate": {"base": 96, "req": [], "risk": [_R("Very reliable; the full Wiegand (FC+CN) is captured.",
                                                       "Muy fiable; se captura el Wiegand completo (FC+CN).", "low")]},
        "clone": {"base": 95, "req": [_R("A blank T5577 card/fob.", "Una tarjeta/llavero T5577 en blanco.")],
                  "risk": [_R("A few sites log card UIDs centrally and flag duplicates.",
                              "Algunos sitios registran UIDs y detectan duplicados.", "low")]},
    },
    "em410x": {
        "emulate": {"base": 97, "req": [], "risk": []},
        "clone": {"base": 96, "req": [_R("A blank T5577 or EM4305.", "Una T5577 o EM4305 en blanco.")], "risk": []},
    },
    "indala": {
        "emulate": {"base": 90, "req": [], "risk": [_R("Some Indala carry PACS data beyond the raw ID.",
                                                       "Algunas Indala llevan datos PACS más allá del ID crudo.", "low")]},
        "clone": {"base": 90, "req": [_R("A blank T5577.", "Una T5577 en blanco.")], "risk": []},
    },
    "awid": {"emulate": {"base": 90, "req": [], "risk": []},
             "clone": {"base": 92, "req": [_R("A blank T5577.", "Una T5577 en blanco.")], "risk": []}},
    "ioprox": {"emulate": {"base": 88, "req": [], "risk": []},
               "clone": {"base": 90, "req": [_R("A blank T5577.", "Una T5577 en blanco.")], "risk": []}},
    "paradox": {"emulate": {"base": 68, "req": [], "risk": [_R("Paradox emulation support is partial in firmware.",
                                                              "El soporte de emulación de Paradox es parcial en el firmware.", "med")]},
                "clone": {"base": 85, "req": [_R("A blank T5577.", "Una T5577 en blanco.")], "risk": []}},
    "pyramid": {"emulate": {"base": 82, "req": [], "risk": []},
                "clone": {"base": 88, "req": [_R("A blank T5577.", "Una T5577 en blanco.")], "risk": []}},
    "viking": {"emulate": {"base": 86, "req": [], "risk": []}, "clone": {"base": 90, "req": [_R("A blank T5577.", "Una T5577 en blanco.")], "risk": []}},
    "noralsy": {"emulate": {"base": 85, "req": [], "risk": []}, "clone": {"base": 88, "req": [_R("A blank T5577.", "Una T5577 en blanco.")], "risk": []}},
    "jablotron": {"emulate": {"base": 85, "req": [], "risk": []}, "clone": {"base": 88, "req": [_R("A blank T5577.", "Una T5577 en blanco.")], "risk": []}},
    "keri": {"emulate": {"base": 84, "req": [], "risk": []}, "clone": {"base": 88, "req": [_R("A blank T5577.", "Una T5577 en blanco.")], "risk": []}},
    "nexwatch": {"emulate": {"base": 70, "req": [], "risk": [_R("Mode byte must match the reader.", "El byte de modo debe coincidir con el lector.", "low")]},
                 "clone": {"base": 84, "req": [_R("A blank T5577.", "Una T5577 en blanco.")], "risk": []}},
    "securakey": {"emulate": {"base": 82, "req": [], "risk": []}, "clone": {"base": 88, "req": [_R("A blank T5577.", "Una T5577 en blanco.")], "risk": []}},
    "gallagher": {"emulate": {"base": 0, "req": [], "risk": [_R("No LF Gallagher sim in firmware; clone instead.", "El firmware no simula Gallagher LF; clónala.", "med")]},
                  "clone": {"base": 80, "req": [_R("A blank T5577.", "Una T5577 en blanco.")],
                            "risk": [_R("Gallagher obfuscates the card data; region/FC/CN must decode cleanly.",
                                        "Gallagher ofusca los datos; región/FC/CN deben decodificar bien.", "med")]}},
    "presco": {"emulate": {"base": 84, "req": [], "risk": []}, "clone": {"base": 88, "req": [_R("A blank T5577.", "Una T5577 en blanco.")], "risk": []}},
    "fdxb": {"emulate": {"base": 90, "req": [], "risk": []}, "clone": {"base": 90, "req": [_R("A blank T5577.", "Una T5577 en blanco.")], "risk": []}},
    "visa2000": {"emulate": {"base": 85, "req": [], "risk": []}, "clone": {"base": 88, "req": [_R("A blank T5577.", "Una T5577 en blanco.")], "risk": []}},
    "em4x05": {"emulate": {"base": 0, "req": [], "risk": [_R("This is a writable chip, not a credential to emulate.", "Es un chip regrabable, no una credencial a emular.", "info")]},
               "clone": {"base": 0, "req": [], "risk": [_R("Write to it directly (it is the blank for LF clones).", "Escríbelo directamente (es el blanco de los clones LF).", "info")]}},
    "t55xx": {"emulate": {"base": 0, "req": [], "risk": [_R("This is the blank itself; write a credential onto it.", "Es el blanco en sí; escríbele una credencial encima.", "info")]},
              "clone": {"base": 0, "req": [], "risk": []}},

    # ---------------- HF (challenge-response / crypto — more caveats) ----------------
    "mifare_classic": {
        "emulate": {"base": 85, "req": [_R("Keys recovered and the sectors dumped.", "Claves recuperadas y sectores volcados.")],
                    "risk": [_R("Readers that read data sectors (not just the UID) need the full dump, which you have once decoded.",
                                "Los lectores que leen sectores (no solo el UID) necesitan el volcado completo, que tienes al decodificar.", "low"),
                             _R("Hardened MIFARE (EV1) resists the nested attack; key recovery can be slow or need a known key.",
                                "La MIFARE endurecida (EV1) resiste el ataque nested; recuperar claves puede ser lento o requerir una clave conocida.", "med")]},
        "clone": {"base": 82, "req": [_R("Keys recovered, plus a magic card (gen1a/gen2) that allows a writable UID.",
                                         "Claves recuperadas y una tarjeta magic (gen1a/gen2) con UID escribible.")],
                  "risk": [_R("Some access systems detect the gen1a backdoor and reject magic cards — use gen2 or emulate instead.",
                              "Algunos sistemas detectan la puerta trasera gen1a y rechazan las magic — usa gen2 o emula.", "med")]},
    },
    "mifare_ultralight": {
        "emulate": {"base": 86, "req": [_R("The pages dumped.", "Las páginas volcadas.")],
                    "risk": [_R("Password-protected pages need the PWD/PACK to read.", "Las páginas con contraseña necesitan el PWD/PACK.", "low")]},
        "clone": {"base": 70, "req": [_R("A magic Ultralight/NTAG with a writable UID.", "Una Ultralight/NTAG magic con UID escribible.")],
                  "risk": [_R("Genuine NTAG has a locked ECC signature tied to the UID that can't be copied; systems that verify it reject clones.",
                              "La NTAG genuina tiene una firma ECC bloqueada ligada al UID que no se copia; los sistemas que la verifican rechazan clones.", "high")]},
    },
    "mifare_desfire": {
        "emulate": {"base": 0, "req": [], "risk": [_R("AES/3DES with unknown keys — cannot be emulated as a working credential.",
                                                      "AES/3DES con claves desconocidas — no se puede emular como credencial válida.", "high")]},
        "clone": {"base": 0, "req": [], "risk": [_R("Not clonable without the application keys. You can only read the UID and app list.",
                                                    "No clonable sin las claves de la aplicación. Solo puedes leer el UID y la lista de apps.", "high")]},
    },
    "mifare_plus": {
        "emulate": {"base": 0, "req": [], "risk": [_R("In SL3 it is AES-secured; identify/read only.", "En SL3 va con AES; solo identificar/leer.", "high")]},
        "clone": {"base": 0, "req": [], "risk": [_R("Not clonable in SL3.", "No clonable en SL3.", "high")]},
    },
    "iclass": {
        "emulate": {"base": 60, "req": [_R("Block dump (legacy uses the known key; Elite needs the custom/elite key).",
                                           "Volcado de bloques (legacy usa la clave conocida; Elite necesita la clave custom/elite).")],
                    "risk": [_R("iCLASS SE/SEOS use diversified keys + SIO — not emulable without those keys.",
                                "iCLASS SE/SEOS usan claves diversificadas + SIO — no emulable sin esas claves.", "high")]},
        "clone": {"base": 55, "req": [_R("A writable iCLASS card (2KS) and the block dump.", "Una iCLASS regrabable (2KS) y el volcado de bloques.")],
                  "risk": [_R("Legacy iCLASS (standard key) clones well; SE/Elite usually do not.",
                              "La iCLASS legacy (clave estándar) clona bien; SE/Elite normalmente no.", "high")]},
    },
    "iso15693": {
        "emulate": {"base": 72, "req": [_R("The tag read.", "El tag leído.")], "risk": [_R("Some iCODE use passwords/AFI.", "Algunas iCODE usan contraseñas/AFI.", "low")]},
        "clone": {"base": 45, "req": [_R("A magic ISO15693 tag with a writable UID (uncommon).", "Un tag ISO15693 magic con UID escribible (poco común).")],
                  "risk": [_R("Writable-UID 15693 blanks are rare; emulation is usually the better route.",
                              "Los blancos 15693 con UID escribible son raros; emular suele ser mejor.", "med")]},
    },
    "felica": {
        "emulate": {"base": 0, "req": [], "risk": [_R("Sony FeliCa (transit/pay) uses mutual auth; not emulable here.", "Sony FeliCa (transporte/pago) usa autenticación mutua; no emulable aquí.", "high")]},
        "clone": {"base": 0, "req": [], "risk": [_R("Not clonable.", "No clonable.", "high")]},
    },
    "topaz": {
        "emulate": {"base": 40, "req": [], "risk": [_R("Limited Topaz emulation support.", "Soporte de emulación de Topaz limitado.", "med")]},
        "clone": {"base": 50, "req": [_R("A compatible NFC Type-1 blank.", "Un blanco NFC Tipo 1 compatible.")], "risk": []},
    },
    "legic": {
        "emulate": {"base": 0, "req": [], "risk": [_R("LEGIC Advant is secured; Prime is only partly readable.", "LEGIC Advant va protegida; Prime solo es parcialmente legible.", "high")]},
        "clone": {"base": 0, "req": [], "risk": [_R("Not clonable with standard tooling.", "No clonable con herramientas estándar.", "high")]},
    },
    "iso14443b": {
        "emulate": {"base": 0, "req": [], "risk": [_R("Identify/read only.", "Solo identificar/leer.", "info")]},
        "clone": {"base": 0, "req": [], "risk": []},
    },
}


def _verdict(score):
    if score >= 80:
        return "high"
    if score >= 55:
        return "medium"
    if score >= 30:
        return "low"
    return "no"


def _assess_one(kind, card):
    caps = card.get("caps") or {}
    key = card.get("key")
    data = card.get("data") or {}
    decoded = bool(card.get("decoded"))
    capable = caps.get("emulable") if kind == "emulate" else caps.get("clonable")
    info = (FEAS.get(key) or {}).get(kind) or {"base": 0, "req": [], "risk": []}
    req = list(info.get("req", []))
    risk = list(info.get("risk", []))

    if not capable:
        return {"verdict": "no", "score": 0, "capable": False,
                "requirements": req, "risks": risk,
                "summary_en": "Not possible with this card type.",
                "summary_es": "No es posible con este tipo de tarjeta."}

    score = info.get("base", 0)
    # encrypted cards must be decoded first; until then, cap the score and add the requirement
    if caps.get("secure") and caps.get("decode") and not decoded:
        score = min(score, 45)
        req = [_R("Run key recovery / dump first (this card is encrypted).",
                  "Primero recupera claves / vuelca (esta tarjeta va cifrada).", "med")] + req

    verdict = _verdict(score)
    tgt = caps.get("target")
    if kind == "clone" and tgt:
        req = [_R("A blank: %s." % tgt, "Un blanco: %s." % tgt)] + [r for r in req if "T5577" not in r["en"] or tgt == "T5577"]

    labels = {
        "high": ("Likely to work", "Probable que funcione"),
        "medium": ("May work — depends on the reader", "Puede funcionar — depende del lector"),
        "low": ("Unlikely without more work", "Poco probable sin más trabajo"),
    }
    en, es = labels.get(verdict, ("", ""))
    return {"verdict": verdict, "score": score, "capable": True,
            "requirements": req, "risks": risk,
            "summary_en": en, "summary_es": es}


def assess(card):
    return {"emulate": _assess_one("emulate", card), "clone": _assess_one("clone", card)}


def modules(card):
    """The section-by-section workflow for this card (like the Android apps). Each module has a status."""
    caps = card.get("caps") or {}
    decoded = bool(card.get("decoded"))
    out = []
    out.append({"key": "identify", "action": None, "status": "done",
                "title_en": "Identify", "title_es": "Identificar",
                "desc_en": "Card type and raw read.", "desc_es": "Tipo de tarjeta y lectura cruda."})

    if caps.get("decode"):
        secure = caps.get("secure")
        out.append({"key": "decode", "action": "decode", "status": "done" if decoded else "ready",
                    "title_en": "Recover keys & dump" if secure else "Read & dump",
                    "title_es": "Recuperar claves y volcar" if secure else "Leer y volcar",
                    "desc_en": "Needed before emulate/clone." if secure else "Full contents.",
                    "desc_es": "Necesario antes de emular/clonar." if secure else "Contenido completo."})

    out.append({"key": "feasibility", "action": None, "status": "done",
                "title_en": "Feasibility", "title_es": "Viabilidad",
                "desc_en": "Chances, requirements and risks.", "desc_es": "Probabilidades, requisitos y riesgos."})

    needs_decode = caps.get("secure") and caps.get("decode") and not decoded
    if caps.get("emulable"):
        out.append({"key": "emulate", "action": "emit", "status": "blocked" if needs_decode else "ready",
                    "title_en": "Emulate", "title_es": "Emular",
                    "desc_en": "Broadcast it from the Proxmark.", "desc_es": "Emítela desde el Proxmark."})
    if caps.get("clonable"):
        out.append({"key": "clone", "action": "write", "status": "blocked" if needs_decode else "ready",
                    "title_en": "Clone to blank", "title_es": "Clonar a blanco",
                    "desc_en": "Write onto %s." % (caps.get("target") or "a blank"),
                    "desc_es": "Escribir en %s." % (caps.get("target") or "un blanco")})

    out.append({"key": "verify", "action": None, "status": "pending",
                "title_en": "Verify", "title_es": "Verificar",
                "desc_en": "Re-read the clone / confirm the sim.", "desc_es": "Re-leer el clon / confirmar la emulación."})
    return out


# Writable blanks you can clone ONTO, and what they accept · Blancos regrabables y qué aceptan
BLANKS = {
    "t55xx": {"en": "Blank T5577 — accepts most LF credentials (HID, EM410x, Indala, AWID…).",
              "es": "T5577 en blanco — acepta casi cualquier credencial LF (HID, EM410x, Indala, AWID…)."},
    "em4x05": {"en": "EM4x05/4305 — a writable LF chip, good for EM410x clones.",
               "es": "EM4x05/4305 — chip LF regrabable, ideal para clones EM410x."},
}


def candidate(card):
    """Is this card a writable blank you could clone onto? Returns a dict or None."""
    b = BLANKS.get(card.get("key"))
    if b:
        return {"blank": True, "note_en": b["en"], "note_es": b["es"]}
    return None


def enrich(card):
    """Attach feasibility + modules (+ blank candidacy) to a card dict (idempotent)."""
    if not card or not card.get("key"):
        return card
    card["feasibility"] = assess(card)
    card["modules"] = modules(card)
    card["candidate"] = candidate(card)
    return card
