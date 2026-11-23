#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Proxlafy · Proxmark3 (Iceman) client wrapper · envoltorio del cliente Proxmark3 (Iceman)

Keeps ONE persistent `pm3` client session alive (over a pseudo-terminal, with pexpect) so commands
are fast — reconnecting the client for every command would add ~2 s each time. All device access goes
through this class, serialized by a lock. A demo mode lets the panel and the UI run with no hardware.

Mantiene UNA sesión del cliente `pm3` viva (con pexpect) para que los comandos sean rápidos. Todo el
acceso al lector pasa por esta clase, serializado con un lock. El modo demo deja usar el panel sin hardware.

Commands assume the Iceman firmware (lf hid, lf em, lf t55xx, hf mf, hf iclass, hw …). On official
firmware some syntaxes differ; set PM3_FIRMWARE="official" and adjust if needed.
"""

import os
import re
import sys
import time
import threading

try:
    import pexpect  # type: ignore
except Exception:  # pragma: no cover - pexpect optional for demo/tests
    pexpect = None

PROMPT = re.compile(r"pm3 -->\s*$")
# strip ANSI colour codes the client emits · quita los códigos de color ANSI del cliente
ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def _clean(text):
    return ANSI.sub("", text or "").replace("\r", "")


class PM3:
    def __init__(self, client="pm3", port="auto", firmware="iceman", demo=False):
        self.client = client or "pm3"
        self.port = port or "auto"
        self.firmware = firmware or "iceman"
        self.demo = bool(demo) or os.environ.get("PROXLAFY_DEMO") == "1"
        self._lock = threading.RLock()
        self._child = None
        self._online = False
        self._simulating = None   # card dict currently being emulated · tarjeta que se está emulando
        self._version = "Iceman (demo)" if self.demo else "?"
        self._last_err = ""
        self._demo_cards_seeded = False

    # ---------------------------------------------------------------- session
    def _spawn(self):
        """Start the pm3 client if it is not running. Returns True if a session exists."""
        if self.demo:
            self._online = True
            self._version = "Iceman (demo)"
            return True
        if pexpect is None:
            self._last_err = "pexpect no instalado · pexpect not installed"
            return False
        if self._child is not None and self._child.isalive():
            return True
        args = []
        if self.port and self.port != "auto":
            args = [self.port]
        try:
            self._child = pexpect.spawn(
                self.client, args, encoding="utf-8", codec_errors="replace",
                timeout=30, echo=False, dimensions=(50, 200),
            )
            # client prints a banner, then the prompt (usb = connected, offline = no device)
            self._child.expect(PROMPT, timeout=30)
            banner = _clean(self._child.before)
            self._online = "[offline]" not in banner.lower() and "offline" not in self._prompt_tag()
            self._version = self._parse_version(banner) or self._version
            return True
        except Exception as e:  # noqa: BLE001
            self._last_err = str(e)
            self._child = None
            self._online = False
            return False

    def _prompt_tag(self):
        try:
            return _clean(self._child.after or "")
        except Exception:  # noqa: BLE001
            return ""

    @staticmethod
    def _parse_version(text):
        m = re.search(r"Iceman[^\n]*", text or "")
        if m:
            return m.group(0).strip()
        m = re.search(r"os:\s*([^\n]+)", text or "")
        return m.group(1).strip() if m else None

    def close(self):
        with self._lock:
            if self._child is not None:
                try:
                    self._child.sendline("quit")
                    self._child.close(force=True)
                except Exception:  # noqa: BLE001
                    pass
                self._child = None

    # ---------------------------------------------------------------- raw command
    def run(self, command, timeout=25):
        """Send one client command and return its cleaned output. Raises RuntimeError if busy/offline."""
        with self._lock:
            if self._simulating is not None:
                raise RuntimeError("busy: emulando · emulating")
            if self.demo:
                return self._demo_run(command)
            if not self._spawn() or self._child is None:
                raise RuntimeError(self._last_err or "cliente no disponible · client unavailable")
            try:
                self._child.sendline(command)
                self._child.expect(PROMPT, timeout=timeout)
                return _clean(self._child.before)
            except pexpect.TIMEOUT:
                # try to regain the prompt without killing the session
                try:
                    self._child.sendintr()
                    self._child.expect(PROMPT, timeout=5)
                except Exception:  # noqa: BLE001
                    self.close()
                raise RuntimeError("tiempo agotado · timed out: %s" % command)
            except Exception as e:  # noqa: BLE001
                self.close()
                raise RuntimeError(str(e))

    # ---------------------------------------------------------------- status
    def status(self):
        with self._lock:
            if self._simulating is not None:
                return {"connected": True, "online": self._online, "firmware": self._version,
                        "simulating": self._simulating, "demo": self.demo}
            if self.demo:
                return {"connected": True, "online": True, "firmware": self._version,
                        "simulating": None, "demo": True}
            ok = self._spawn()
            connected = False
            if ok and self._child is not None:
                try:
                    out = self.run("hw status", timeout=10)
                    connected = "Proxmark3" in out or "USB" in out or "ARM" in out
                    if not self._version or self._version == "?":
                        v = self.run("hw version", timeout=10)
                        self._version = self._parse_version(v) or self._version
                except Exception:  # noqa: BLE001
                    connected = False
            return {"connected": connected, "online": self._online, "firmware": self._version,
                    "simulating": None, "demo": False, "error": self._last_err}

    # ---------------------------------------------------------------- read / search
    def read(self, band="auto"):
        """Search LF and/or HF and return a parsed card dict (not yet saved) or None."""
        if band in ("auto", "lf"):
            card = self._parse_lf(self.run("lf search", timeout=40))
            if card:
                return card
        if band in ("auto", "hf"):
            card = self._parse_hf(self.run("hf search", timeout=40))
            if card:
                return card
        return None

    # ---------------------------------------------------------------- emulate / sim
    def start_sim(self, card):
        """Begin emulating a saved card. The device stays busy until stop_sim()."""
        with self._lock:
            if self._simulating is not None:
                raise RuntimeError("ya está emulando · already emulating")
            cmd = self._sim_command(card)
            if not cmd:
                raise RuntimeError("tipo no soportado para emular · unsupported type: %s" % card.get("type"))
            if self.demo:
                self._simulating = card
                return cmd
            if not self._spawn() or self._child is None:
                raise RuntimeError(self._last_err or "cliente no disponible · client unavailable")
            # fire the blocking sim command but do NOT wait for the prompt: it runs until stop
            self._child.sendline(cmd)
            self._simulating = card
            return cmd

    def stop_sim(self):
        with self._lock:
            if self._simulating is None:
                return False
            if self.demo:
                self._simulating = None
                return True
            try:
                self._child.sendintr()            # Ctrl-C aborts the running sim
                self._child.sendline("")
                self._child.expect(PROMPT, timeout=8)
            except Exception:  # noqa: BLE001
                self.close()
            self._simulating = None
            return True

    def is_simulating(self):
        return self._simulating

    # ---------------------------------------------------------------- write to a blank card
    def write_card(self, card):
        """Write a saved card onto a writable blank (T5577 for LF, magic/gen1a for HF when supported)."""
        cmd = self._clone_command(card)
        if not cmd:
            raise RuntimeError("escritura no soportada para · write unsupported for: %s" % card.get("type"))
        out = self.run(cmd, timeout=40)
        ok = "done" in out.lower() or "written" in out.lower() or "verified" in out.lower() or self.demo
        return {"ok": bool(ok), "command": cmd, "output": out if not self.demo else "demo: escrito · written"}

    # ================================================================ command builders
    def _sim_command(self, card):
        t = (card.get("type") or "").lower()
        d = card.get("data", {})
        if "hid" in t:
            fmt = d.get("format", "H10301")
            if d.get("fc") is not None and d.get("cn") is not None:
                return "lf hid sim -w %s --fc %s --cn %s" % (fmt, d["fc"], d["cn"])
            if d.get("raw"):
                return "lf hid sim -r %s" % d["raw"]
        if "em" in t and "410" in t:
            if d.get("id"):
                return "lf em 410x sim --id %s" % d["id"]
        if "indala" in t and d.get("raw"):
            return "lf indala sim -r %s" % d["raw"]
        if "t55" in t and d.get("raw"):
            return "lf simask -d %s" % d["raw"]
        if "mifare" in t and "classic" in t and d.get("dump"):
            return "hf mf sim --1k -u %s" % (d.get("uid") or "")
        if "iclass" in t and d.get("dump"):
            return "hf iclass sim -t 3"
        return None

    def _clone_command(self, card):
        t = (card.get("type") or "").lower()
        d = card.get("data", {})
        if "hid" in t and d.get("fc") is not None and d.get("cn") is not None:
            return "lf hid clone -w %s --fc %s --cn %s" % (d.get("format", "H10301"), d["fc"], d["cn"])
        if "em" in t and "410" in t and d.get("id"):
            return "lf em 410x clone --id %s" % d["id"]
        if "indala" in t and d.get("raw"):
            return "lf indala clone -r %s" % d["raw"]
        return None

    # ================================================================ parsers
    def _parse_lf(self, out):
        out = out or ""
        # HID Prox · HID Proximity (match the banner line and/or the decoded line)
        if re.search(r"HID\b", out) and ("Prox" in out or "FC:" in out
                                         or re.search(r"HID\s+[A-Za-z0-9]+\s+\d+-bit", out)):
            fc = self._grab(out, r"FC:\s*(\d+)")
            cn = self._grab(out, r"CN:\s*(\d+)")
            raw = self._grab(out, r"raw:\s*([0-9A-Fa-f]+)") or self._grab(out, r"\(([0-9A-Fa-f]{10,})\)")
            fmt = self._grab(out, r"HID\s+([A-Za-z0-9]+)\s+\d+-bit") or "H10301"
            return self._card("lf", "HID Prox (%s)" % fmt,
                              {"format": fmt, "fc": _int(fc), "cn": _int(cn), "raw": raw}, out,
                              label=("FC %s · CN %s" % (fc, cn)) if fc else (raw or "HID"))
        # EM410x
        if re.search(r"EM\s*410x", out, re.I):
            eid = self._grab(out, r"EM\s*410x.*?ID[:\s]+([0-9A-Fa-f]+)") or self._grab(out, r"\bID[:\s]+([0-9A-Fa-f]{10})\b")
            return self._card("lf", "EM410x", {"id": eid}, out, label=eid or "EM410x")
        # Indala
        if re.search(r"Indala", out, re.I):
            raw = self._grab(out, r"Raw[:\s]+([0-9A-Fa-f]+)")
            return self._card("lf", "Indala", {"raw": raw}, out, label=raw or "Indala")
        # T55x7 generic
        if re.search(r"T55", out):
            raw = self._grab(out, r"([0-9A-Fa-f]{8,})")
            return self._card("lf", "T55x7", {"raw": raw}, out, label=raw or "T55x7")
        return None

    def _parse_hf(self, out):
        out = out or ""
        if re.search(r"MIFARE\s+Classic", out, re.I):
            uid = self._grab(out, r"UID[:\s]+([0-9A-Fa-f ]+)")
            size = "1k" if "1K" in out or "1k" in out else ("4k" if "4K" in out else "1k")
            return self._card("hf", "MIFARE Classic %s" % size.upper(),
                              {"uid": _hex(uid), "size": size}, out, label=_hex(uid) or "MIFARE")
        if re.search(r"MIFARE\s+DESFire", out, re.I):
            uid = self._grab(out, r"UID[:\s]+([0-9A-Fa-f ]+)")
            return self._card("hf", "MIFARE DESFire", {"uid": _hex(uid)}, out, label=_hex(uid) or "DESFire")
        if re.search(r"iCLASS", out, re.I):
            csn = self._grab(out, r"CSN[:\s]+([0-9A-Fa-f ]+)")
            return self._card("hf", "HID iCLASS", {"csn": _hex(csn)}, out, label=_hex(csn) or "iCLASS")
        if re.search(r"NTAG|Ultralight", out, re.I):
            uid = self._grab(out, r"UID[:\s]+([0-9A-Fa-f ]+)")
            return self._card("hf", "NTAG / Ultralight", {"uid": _hex(uid)}, out, label=_hex(uid) or "NTAG")
        return None

    @staticmethod
    def _grab(text, pattern):
        m = re.search(pattern, text or "", re.I)
        return m.group(1).strip() if m else None

    @staticmethod
    def _card(band, ctype, data, raw, label=""):
        return {"band": band, "type": ctype, "data": data,
                "label": label, "raw_output": (raw or "")[-4000:]}

    # ================================================================ demo backend
    def _demo_run(self, command):
        c = command.strip().lower()
        if c.startswith("hw status"):
            return "Proxmark3 RFID instrument (demo)\n ARM: fw 4.x\n"
        if c.startswith("hw version"):
            return "Iceman (demo) - compiled for proxlafy\n"
        if c == "lf search":
            return ("\n[+] Valid HID Prox ID found!\n"
                    "[+] HID H10301 26-bit; FC: 123 CN: 45678 (raw: 2004d1a35b)\n")
        if c == "hf search":
            return ("\n[+] MIFARE Classic 1K\n[+]  UID: 04 A3 2B 9C\n")
        return "demo: %s\n" % command


def _int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _hex(v):
    if not v:
        return None
    return re.sub(r"\s+", "", v).upper()


if __name__ == "__main__":  # quick manual check · prueba manual rápida
    pm = PM3(demo=("--demo" in sys.argv))
    print("status:", pm.status())
    print("read:", pm.read())
