#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Proxlafy · Proxmark3 (Iceman) client wrapper · envoltorio del cliente Proxmark3 (Iceman)

Keeps ONE persistent `pm3` client session alive (over a pseudo-terminal, with pexpect) so commands are
fast. All device access goes through this class, serialized by a lock. A demo mode lets the panel and the
UI run with no hardware. Card knowledge lives in catalog.py.

Persistent emulation · Emulación persistente:
  start_sim() writes the chosen card to a state file and begins emulating. If the Proxmark (or the whole
  kit) loses power, the intent survives: on the next boot a monitor calls resume_if_needed() and the kit
  starts emulating that same card again as soon as the device is back — until you cancel it in the panel.

Commands assume the Iceman firmware. On official firmware some syntaxes differ (PM3_FIRMWARE="official").
"""

import os
import re
import sys
import json
import time
import threading

try:
    import pexpect  # type: ignore
except Exception:  # pragma: no cover
    pexpect = None

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import catalog  # noqa: E402
import feasibility  # noqa: E402
import standalone as standalone_mod  # noqa: E402
import extras  # noqa: E402

PROMPT = re.compile(r"pm3 -->\s*$")
ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def _clean(text):
    return ANSI.sub("", text or "").replace("\r", "")


def _label(entry, fields):
    if not entry:
        return ""
    f = fields
    if entry["key"] == "hid_prox" and f.get("fc"):
        return "FC %s · CN %s" % (f.get("fc"), f.get("cn"))
    for k in ("id", "uid", "csn", "idm", "raw"):
        if f.get(k):
            return f[k]
    if f.get("fc") and f.get("cn"):
        return "FC %s · CN %s" % (f["fc"], f["cn"])
    return entry["name"]


class PM3:
    def __init__(self, client="pm3", port="auto", firmware="iceman", demo=False, state_dir=None):
        self.client = client or "pm3"
        self.port = port or "auto"
        self.firmware = firmware or "iceman"
        self.demo = bool(demo) or os.environ.get("PROXLAFY_DEMO") == "1"
        self.state_dir = state_dir or "/var/lib/proxlafy"
        self._lock = threading.RLock()
        self._child = None
        self._online = False
        self._active = None       # card we INTEND to emulate (persisted) · tarjeta que se quiere emular
        self._sim_running = False  # whether the sim command is actually running now
        self._version = "Iceman (demo)" if self.demo else "?"
        self._last_err = ""
        self._demo_i = 0
        self._demo_standalone = None   # demo: pretend a mode is flashed
        self._flashing = False
        self._load_active()

    # ================================================================ session
    def _spawn(self):
        if self.demo:
            self._online = True
            return True
        if pexpect is None:
            self._last_err = "pexpect no instalado · pexpect not installed"
            return False
        if self._child is not None and self._child.isalive():
            return True
        args = [] if (not self.port or self.port == "auto") else [self.port]
        try:
            self._child = pexpect.spawn(self.client, args, encoding="utf-8", codec_errors="replace",
                                        timeout=30, echo=False, dimensions=(60, 220))
            self._child.expect(PROMPT, timeout=30)
            banner = _clean(self._child.before)
            self._online = "offline" not in banner.lower()
            self._version = self._parse_version(banner) or self._version
            return True
        except Exception as e:  # noqa: BLE001
            self._last_err = str(e)
            self._child = None
            self._online = False
            return False

    @staticmethod
    def _parse_version(text):
        m = re.search(r"Iceman[^\n]*", text or "")
        if m:
            return m.group(0).strip()
        m = re.search(r"os:\s*([^\n]+)", text or "")
        return m.group(1).strip() if m else None

    def _device_ready(self):
        if self.demo:
            return True
        if not self._spawn() or self._child is None:
            return False
        try:
            out = self._raw("hw status", timeout=8)
            return "Proxmark3" in out or "ARM" in out or "USB" in out
        except Exception:  # noqa: BLE001
            return False

    def close(self):
        with self._lock:
            if self._child is not None:
                try:
                    self._child.sendline("quit")
                    self._child.close(force=True)
                except Exception:  # noqa: BLE001
                    pass
                self._child = None

    # ================================================================ raw command
    def _raw(self, command, timeout=25):
        if self.demo:
            return self._demo_run(command)
        if not self._spawn() or self._child is None:
            raise RuntimeError(self._last_err or "cliente no disponible · client unavailable")
        try:
            self._child.sendline(command)
            self._child.expect(PROMPT, timeout=timeout)
            return _clean(self._child.before)
        except pexpect.TIMEOUT:
            try:
                self._child.sendintr(); self._child.expect(PROMPT, timeout=5)
            except Exception:  # noqa: BLE001
                self.close()
            raise RuntimeError("tiempo agotado · timed out: %s" % command)
        except Exception as e:  # noqa: BLE001
            self.close()
            raise RuntimeError(str(e))

    def run(self, command, timeout=25):
        with self._lock:
            if self._sim_running:
                raise RuntimeError("busy: emulando · emulating")
            return self._raw(command, timeout)

    # ================================================================ status
    def status(self):
        with self._lock:
            connected = self._device_ready() if not self._sim_running else True
            return {
                "connected": connected, "online": self._online or self.demo,
                "firmware": self._version, "demo": self.demo,
                "simulating": self._active if self._sim_running else None,
                "pending_sim": self._active if (self._active and not self._sim_running) else None,
                "error": self._last_err,
            }

    # ================================================================ read / classify
    def read(self, band="auto"):
        outputs = []
        if band in ("auto", "lf"):
            out = self.run("lf search", timeout=40)
            outputs.append(("lf", out))
            card = self._classify("lf", out)
            if card:
                return card
        if band in ("auto", "hf"):
            out = self.run("hf search", timeout=40)
            outputs.append(("hf", out))
            card = self._classify("hf", out)
            if card:
                return card
        return None

    def _classify(self, band, out):
        entry, fields = catalog.classify(out, band)
        if not entry:
            return None
        caps = catalog.capabilities(entry, fields)
        card = {
            "band": band, "type": entry["name"], "key": entry["key"],
            "label": _label(entry, fields), "data": fields, "caps": caps,
            "raw_output": (out or "")[-4000:],
        }
        return feasibility.enrich(card)

    # ================================================================ decode / deep read
    def decode(self, card):
        """Run the card's decode step (key recovery / dump) and enrich the card. Returns (card, result)."""
        key = (card.get("caps") or {}).get("decode") or card.get("key")
        op = (card.get("caps") or {}).get("decode")
        if not op:
            return card, {"ok": True, "message": "nada que decodificar · nothing to decode"}
        out = ""
        try:
            if op == "mf_autopwn":
                out = self.run("hf mf autopwn", timeout=600)
                keys = re.findall(r"([0-9A-Fa-f]{12})", out)
                card.setdefault("data", {})["keys_found"] = len(set(keys))
                card["data"]["dump"] = True
                card["decoded"] = True
            elif op in ("iclass_dump", "mfu_dump", "iso15_dump", "topaz_dump", "t55xx_dump", "em4x05_dump"):
                cmd = {
                    "iclass_dump": "hf iclass dump", "mfu_dump": "hf mfu dump",
                    "iso15_dump": "hf 15 dump", "topaz_dump": "hf topaz dump",
                    "t55xx_dump": "lf t55xx dump", "em4x05_dump": "lf em 4x05 dump",
                }[op]
                out = self.run(cmd, timeout=120)
                card.setdefault("data", {})["dump"] = True
                card["decoded"] = True
            else:  # info/enum ops (desfire, felica, legic, plus, 14b)
                cmd = {
                    "mfdes_enum": "hf mfdes enum", "felica_info": "hf felica info",
                    "legic_info": "hf legic info", "mfp_info": "hf mf info", "iso14b_info": "hf 14b info",
                }.get(op, "hw status")
                out = self.run(cmd, timeout=60)
                card["decoded"] = True
            feasibility.enrich(card)
            return card, {"ok": True, "output": out[-2000:]}
        except Exception as e:  # noqa: BLE001
            return card, {"ok": False, "error": str(e), "output": out[-2000:]}

    # ================================================================ emulate (persistent)
    def build_sim(self, card):
        entry = catalog.CATALOG_BY_KEY.get(card.get("key"))
        if not entry:
            return None
        return catalog.build_cmd("sim", entry, card.get("data", {}))

    def build_clone(self, card):
        entry = catalog.CATALOG_BY_KEY.get(card.get("key"))
        if not entry:
            return None
        return catalog.build_cmd("clone", entry, card.get("data", {}))

    def start_sim(self, card, seconds=0):
        """Set the card as the active emulation (persisted) and begin emulating.
        seconds > 0 auto-stops after that long (timed emission)."""
        with self._lock:
            cmd = self.build_sim(card)
            if not cmd:
                raise RuntimeError("tipo no soportado para emular · unsupported for emulation: %s" % card.get("type"))
            self._active = {"id": card.get("id"), "name": card.get("name"), "label": card.get("label"),
                            "type": card.get("type"), "key": card.get("key"), "band": card.get("band"),
                            "data": card.get("data", {})}
            self._save_active(cmd)
            self._ensure_sim(cmd)
            if seconds and seconds > 0:
                t = threading.Timer(float(seconds), self.stop_sim)
                t.daemon = True
                t.start()
            return cmd

    def _ensure_sim(self, cmd=None):
        """Make sure the active card is actually being emulated right now (if the device is available)."""
        if self._active is None or self._sim_running:
            return
        cmd = cmd or self._active.get("_cmd") or self.build_sim(self._active)
        if not cmd:
            return
        if self.demo:
            self._sim_running = True
            return
        if not self._device_ready():
            return  # will retry on the next resume_if_needed()
        try:
            self._child.sendline(cmd)   # blocking sim; we do not wait for the prompt
            self._sim_running = True
        except Exception:  # noqa: BLE001
            self.close()
            self._sim_running = False

    def resume_if_needed(self):
        """Called periodically by the server monitor. Re-starts a persisted emulation after a power cycle."""
        with self._lock:
            if self._active is None:
                return
            if self._sim_running and not self.demo and (self._child is None or not self._child.isalive()):
                self._sim_running = False   # the device went away; the sim is not really running
            if not self._sim_running:
                self._ensure_sim()

    def stop_sim(self):
        with self._lock:
            was = self._active is not None
            self._active = None
            self._clear_active()
            if self._sim_running and not self.demo and self._child is not None:
                try:
                    self._child.sendintr(); self._child.sendline(""); self._child.expect(PROMPT, timeout=8)
                except Exception:  # noqa: BLE001
                    self.close()
            self._sim_running = False
            return was

    def active(self):
        return self._active

    # ================================================================ write / clone to blank
    def write_card(self, card, verify=True):
        cmd = self.build_clone(card)
        if not cmd:
            raise RuntimeError("escritura no soportada para · write unsupported for: %s" % card.get("type"))
        out = self.run(cmd, timeout=60)
        ok = self.demo or any(w in out.lower() for w in ("done", "written", "verified", "ok"))
        result = {"ok": bool(ok), "command": cmd,
                  "output": "demo: escrito · written" if self.demo else out[-2000:]}
        if ok and verify:
            if self.demo:
                result["verified"] = True
                result["verify_label"] = card.get("label")
            else:
                try:
                    check = self.read(card.get("band", "auto"))
                    orig = card.get("data", {})
                    chk = (check or {}).get("data", {})
                    match = bool(check) and (
                        (check.get("label") and check.get("label") == card.get("label")) or
                        (orig.get("uid") and orig.get("uid") == chk.get("uid")) or
                        (orig.get("id") and orig.get("id") == chk.get("id")))
                    result["verified"] = bool(match)
                    result["verify_label"] = (check or {}).get("label")
                except Exception:  # noqa: BLE001
                    result["verified"] = None
        return result

    # ================================================================ device / antenna
    def device_status(self):
        """Antenna health (LF/HF voltages) from `hw tune`, plus connection + standalone."""
        base = {"standalone": self.standalone_status().get("current")}
        if self.demo:
            base.update({"lf_v": 32.4, "hf_v": 8.1, "lf_ok": True, "hf_ok": True, "demo": True})
            return base
        try:
            out = self.run("hw tune", timeout=20)
            base.update(extras.parse_tune(out))
        except Exception as e:  # noqa: BLE001
            base["error"] = str(e)
        return base

    # ================================================================ standalone modes
    def standalone_status(self):
        """Which standalone mode the firmware currently reports (or None)."""
        if self.demo:
            return {"ok": True, "current": self._demo_standalone, "flashing": self._flashing}
        try:
            out = self.run("hw status", timeout=10)
            return {"ok": True, "current": standalone_mod.parse_current(out), "flashing": self._flashing}
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "current": None, "flashing": self._flashing, "error": str(e)}

    def program_standalone(self, mode, log=None):
        """Build + flash a standalone mode. Long and irreversible-ish; the server runs it in a thread.
        `log` is an optional callable(line) for live progress."""
        log = log or (lambda *_a: None)
        if mode not in standalone_mod.MODES_BY_ID:
            return {"ok": False, "error": "modo desconocido · unknown mode: %s" % mode}
        if self._flashing:
            return {"ok": False, "error": "ya se está grabando · already flashing"}
        self._flashing = True
        try:
            if self.demo:
                for step in ("Seleccionando modo en Makefile.platform",
                             "make clean && make -j (compilando firmware)…",
                             "Grabando imagen (no desconectes)…",
                             "✔ Listo (demo): modo %s grabado" % mode):
                    log(step)
                    time.sleep(0.4)
                self._demo_standalone = mode
                return {"ok": True, "mode": mode}
            # live: run the helper script and stream its output
            import subprocess
            here = os.path.dirname(os.path.abspath(__file__))
            script = os.path.join(here, "proxlafy-standalone.sh")
            proc = subprocess.Popen(["bash", script, mode], stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, text=True)
            for line in iter(proc.stdout.readline, ""):
                line = line.rstrip("\n")
                if line:
                    log(line)
            proc.wait()
            return {"ok": proc.returncode == 0, "mode": mode, "rc": proc.returncode}
        finally:
            self._flashing = False

    # ================================================================ persistence
    @property
    def _active_path(self):
        return os.path.join(self.state_dir, "active_sim.json")

    def _save_active(self, cmd):
        try:
            os.makedirs(self.state_dir, exist_ok=True)
            data = dict(self._active); data["_cmd"] = cmd; data["started"] = time.time()
            with open(self._active_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
        except OSError:
            pass

    def _clear_active(self):
        try:
            os.remove(self._active_path)
        except OSError:
            pass

    def _load_active(self):
        try:
            with open(self._active_path, "r", encoding="utf-8") as f:
                self._active = json.load(f)
        except (OSError, ValueError):
            self._active = None

    # ================================================================ demo backend
    _DEMO_CARDS = [
        "\n[+] Valid HID Prox ID found!\n[+] HID H10301 26-bit; FC: 123 CN: 45678 (raw: 2004d1a35b)\n",
        "\n[+] EM 410x ID 1A2B3C4D5E\n[=]  Format: Unique\n",
        "\n[+] Indala (len 64)  Raw: a0000000c2f3e4b1  FC: 42  Card: 1337\n",
        "\n[+] AWID 26 FC: 200 Card: 31337\n",
        "\n[+] Chipset detection: T55xx\n[=]  block 0: 000880E0\n[=]  (blank / writable)\n",
        "\n[+] EM4x05/4x69\n[=]  word 0: 00008040\n[=]  (writable)\n",
        "\n[+] MIFARE Classic 1K\n[=]  UID: 04 A3 2B 9C\n[=]  ATQA: 00 04  SAK: 08\n",
        "\n[+] MIFARE Ultralight EV1\n[=]  UID: 04 51 7A B2 C1 33 80\n[=]  NTAG 215\n",
        "\n[+] iCLASS / PicoPass\n[=]  CSN: 00 0B 0F FF F7 FF 12 E0\n[=]  Config: 12 FF FF FF 7F 1F FF 3C\n",
        "\n[+] MIFARE DESFire EV2\n[=]  UID: 04 7A 11 92 33 55 80\n",
        "\n[+] ISO15693 / iCODE SLIX\n[=]  UID: E0 04 01 50 12 34 56 78\n",
    ]

    def _demo_run(self, command):
        c = command.strip().lower()
        if c.startswith("hw status"):
            return "Proxmark3 RFID instrument (demo)\n ARM: fw 4.x\n"
        if c.startswith("hw version"):
            return "Iceman (demo) - compiled for proxlafy\n"
        if c == "lf search":
            lf = [x for x in self._DEMO_CARDS if "MIFARE" not in x and "iCLASS" not in x
                  and "DESFire" not in x and "ISO15693" not in x]
            out = lf[self._demo_i % len(lf)]; self._demo_i += 1
            return out
        if c == "hf search":
            hf = [x for x in self._DEMO_CARDS if any(t in x for t in ("MIFARE", "iCLASS", "ISO15693"))]
            out = hf[self._demo_i % len(hf)]; self._demo_i += 1
            return out
        if c == "hf mf autopwn":
            return ("[+] found keys:\n[+] Sector 0 key A ffffffffffff\n[+] Sector 1 key A a0a1a2a3a4a5\n"
                    "[+] all keys found\n[+] dumped 1024 bytes\n")
        return "demo: %s\n" % command


if __name__ == "__main__":
    pm = PM3(demo=True, state_dir="/tmp/proxlafy-demo")
    print("status:", pm.status())
    for _ in range(3):
        print("read:", (pm.read() or {}).get("type"))
