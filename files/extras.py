#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Proxlafy · extras · utilidades

- wiegand_decode: break an HID credential into its Wiegand bits (facility, card, parity).
- parse_tune: read LF/HF antenna health from `hw tune`.
- standalone_for: which standalone mode would keep a given card emitting with no host (the
  "only the Proxmark is powered" case).
"""

import re

# ---------------------------------------------------------------- Wiegand (HID)
# Common formats: bit length -> (facility_bits, card_bits)
WIEGAND_FORMATS = {
    "H10301": (26, 8, 16),     # 26-bit standard
    "H10302": (37, 0, 35),
    "H10304": (37, 16, 19),
    "C1k35s": (35, 12, 20),    # Corporate 1000 35-bit
    "C1k48s": (48, 22, 23),    # Corporate 1000 48-bit
}


def _parity(bits):
    return bits.count("1") % 2


def wiegand_decode(card):
    """Return a human breakdown of an HID credential, or None if not applicable."""
    if (card.get("key") or "") != "hid_prox":
        return None
    d = card.get("data") or {}
    fmt = d.get("format") or "H10301"
    spec = WIEGAND_FORMATS.get(fmt)
    try:
        fc = int(d.get("fc")) if d.get("fc") is not None else None
        cn = int(d.get("cn")) if d.get("cn") is not None else None
    except (TypeError, ValueError):
        fc, cn = None, None
    out = {"format": fmt, "fc": fc, "cn": cn, "raw": d.get("raw")}
    if spec and fmt == "H10301" and fc is not None and cn is not None:
        fac = format(fc & 0xFF, "08b")
        card_b = format(cn & 0xFFFF, "016b")
        payload = fac + card_b                # 24 data bits
        ep = _parity(payload[:12])            # even parity over first 12
        op = 1 - _parity(payload[12:])        # odd parity over last 12
        full = "%d%s%d" % (ep, payload, op)   # 26 bits
        out.update({"bits": 26, "facility_bits": fac, "card_bits": card_b,
                    "even_parity": ep, "odd_parity": op, "binary": full})
    elif spec:
        out["bits"] = spec[0]
    return out


# ---------------------------------------------------------------- antenna / device
def parse_tune(output):
    """Parse `hw tune` into LF/HF antenna voltages and a simple health flag."""
    out = output or ""
    def v(pat):
        m = re.search(pat, out, re.I)
        return float(m.group(1)) if m else None
    lf = v(r"LF antenna:\s*([\d.]+)\s*V") or v(r"([\d.]+)\s*V.*125")
    lf_opt = v(r"([\d.]+)\s*V.*at\s*125\.?\d*\s*kHz") or lf
    hf = v(r"HF antenna:\s*([\d.]+)\s*V") or v(r"([\d.]+)\s*V.*13\.56")
    res = {"lf_v": lf, "hf_v": hf}
    # rough health: LF good if > 20 V peak, HF good if > 7 V (typical thresholds)
    res["lf_ok"] = (lf is not None and lf >= 18)
    res["hf_ok"] = (hf is not None and hf >= 6)
    return res


# ---------------------------------------------------------------- standalone bridge
# Which standalone mode keeps THIS card emitting when only the Proxmark has power.
STANDALONE_FOR = {
    "hid_prox": "LF_SAMYRUN",
    "em410x": "LF_EM4100RWC",
    "mifare_classic": "HF_MFCSIM",
    "mifare_ultralight": "HF_AVEFUL",
    "iclass": "HF_ICECLASS",
    "iso15693": "HF_TMUDFORD",
}


def standalone_for(card):
    """Suggest a standalone mode so the card keeps emitting with no host, or explain why not."""
    key = card.get("key")
    mode = STANDALONE_FOR.get(key)
    if mode:
        return {"ok": True, "mode": mode,
                "note_en": "Flash %s so the Proxmark keeps emitting this card on its own power, with no Pi." % mode,
                "note_es": "Graba %s para que el Proxmark siga emitiendo esta tarjeta con su propia energía, sin la Pi." % mode}
    return {"ok": False, "mode": None,
            "note_en": "This card type has no standalone emit mode; it needs the panel (Pi) running.",
            "note_es": "Este tipo de tarjeta no tiene modo standalone de emisión; necesita el panel (la Pi) encendido."}
