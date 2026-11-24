#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Proxlafy · web panel server · servidor del panel web

Pure Python standard library (no framework) so it runs light on a Raspberry Pi Zero 2 W.
Serves the offline web panel from ./web and a small JSON API that drives the Proxmark3 through pm3.PM3.

Python puro de la biblioteca estándar (sin framework) para correr ligero en la Pi Zero 2 W.
Sirve el panel web offline desde ./web y una pequeña API JSON que maneja el Proxmark3 vía pm3.PM3.

Run (demo, no hardware) · Ejecutar (demo, sin hardware):
    PROXLAFY_DEMO=1 python3 files/proxlafy_server.py --port 8080
"""

import os
import re
import io
import sys
import json
import time
import uuid
import html
import shutil
import secrets
import argparse
import threading
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from http import HTTPStatus
from urllib.parse import urlparse, parse_qs

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(HERE, "web")
sys.path.insert(0, HERE)
from pm3 import PM3  # noqa: E402
import feasibility  # noqa: E402
import standalone as standalone_mod  # noqa: E402

CONF_PATH = os.environ.get("PROXLAFY_CONF", "/etc/proxlafy/proxlafy.conf")


def read_version():
    for p in (os.path.join(HERE, "VERSION"), os.path.join(HERE, "..", "VERSION"), "/opt/proxlafy/VERSION"):
        try:
            with open(p, "r", encoding="utf-8") as f:
                v = f.read().strip()
                if v:
                    return v
        except OSError:
            continue
    return "?"


VERSION = None  # filled in main()/App

MIME = {
    ".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8", ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml", ".png": "image/png", ".ico": "image/x-icon",
    ".webmanifest": "application/manifest+json", ".woff2": "font/woff2",
}


def load_conf(path):
    conf = {}
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                m = re.match(r'^\s*(?:export\s+)?([A-Z_][A-Z0-9_]*)=(.*)$', line.rstrip("\n"))
                if not m:
                    continue
                key, val = m.group(1), m.group(2).strip()
                mq = re.match(r'^"([^"]*)"', val) or re.match(r"^'([^']*)'", val)
                if mq:
                    val = mq.group(1)
                else:
                    val = val.split("#", 1)[0].strip()
                conf[key] = val
    except FileNotFoundError:
        pass
    return conf


def cint(v, default):
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return default


class Log:
    """Small in-memory ring buffer the panel polls with /api/log?since=cursor."""
    def __init__(self, size=400):
        self._lock = threading.Lock()
        self._items = []
        self._seq = 0
        self._size = size

    def add(self, text, level="info"):
        with self._lock:
            self._seq += 1
            self._items.append({"seq": self._seq, "t": time.time(), "level": level, "text": text})
            if len(self._items) > self._size:
                self._items = self._items[-self._size:]

    def since(self, cursor):
        with self._lock:
            return [i for i in self._items if i["seq"] > cursor], self._seq


class Library:
    """Saved cards as one JSON file each, under CARDS_DIR."""
    def __init__(self, directory):
        self.dir = directory
        os.makedirs(self.dir, exist_ok=True)
        self._lock = threading.Lock()

    def list(self):
        out = []
        for name in os.listdir(self.dir):
            if name.endswith(".json"):
                try:
                    with open(os.path.join(self.dir, name), "r", encoding="utf-8") as f:
                        out.append(json.load(f))
                except Exception:  # noqa: BLE001
                    continue
        out.sort(key=lambda c: c.get("created", 0), reverse=True)
        return out

    def get(self, cid):
        path = os.path.join(self.dir, "%s.json" % _safe_id(cid))
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def save(self, card):
        with self._lock:
            cid = card.get("id") or uuid.uuid4().hex[:12]
            card["id"] = cid
            card.setdefault("created", time.time())
            card["updated"] = time.time()
            with open(os.path.join(self.dir, "%s.json" % _safe_id(cid)), "w", encoding="utf-8") as f:
                json.dump(card, f, ensure_ascii=False, indent=2)
            return card

    def delete(self, cid):
        path = os.path.join(self.dir, "%s.json" % _safe_id(cid))
        if os.path.exists(path):
            os.remove(path)
            return True
        return False


def _safe_id(cid):
    return re.sub(r"[^A-Za-z0-9_-]", "", str(cid))[:40] or "x"


class App:
    def __init__(self, conf):
        self.conf = conf
        self.admin_pw = conf.get("ADMIN_PASSWORD", "") or ""
        self.viewer_pw = conf.get("VIEWER_PASSWORD", "") or ""
        self.log = Log()
        state_dir = "/var/lib/proxlafy"
        cards_dir = conf.get("CARDS_DIR") or os.path.join(state_dir, "cards")
        if os.environ.get("PROXLAFY_DEMO") == "1" and not os.path.isdir(state_dir):
            state_dir = os.environ.get("PROXLAFY_STATE_DIR", os.path.abspath(os.path.join(HERE, "..", "data")))
            cards_dir = os.environ.get("PROXLAFY_CARDS_DIR", os.path.join(state_dir, "cards"))
        self.state_dir = os.path.abspath(state_dir)
        self.lib = Library(os.path.abspath(cards_dir))
        self.pm = PM3(
            client=conf.get("PM3_CLIENT", "pm3"),
            port=conf.get("PM3_PORT", "auto"),
            firmware=conf.get("PM3_FIRMWARE", "iceman"),
            demo=os.environ.get("PROXLAFY_DEMO") == "1",
            state_dir=self.state_dir,
        )
        self._sessions = {}   # token -> role
        self.history = []     # last reads (not saved), newest first
        self.log.add("Proxlafy iniciado · started", "ok")
        if self.pm.active():
            self.log.add("Emulación pendiente de reanudar · emulation pending resume: %s"
                         % (self.pm.active().get("name") or self.pm.active().get("label")), "warn")
        self._mon = threading.Thread(target=self._monitor, daemon=True)
        self._mon.start()

    def _monitor(self):
        """Resume a persisted emulation after a power cycle, and log when it goes live."""
        was_running = False
        while True:
            try:
                self.pm.resume_if_needed()
                st = self.pm.status()
                running = st.get("simulating") is not None
                if running and not was_running:
                    self.log.add("Emulación activa · emulation live: %s"
                                 % (st["simulating"].get("name") or st["simulating"].get("label")), "ok")
                was_running = running
            except Exception:  # noqa: BLE001
                pass
            time.sleep(4)

    # -------------------------------------------------- auth
    def auth_open(self):
        return not self.admin_pw

    def role_for(self, token):
        if self.auth_open():
            return "admin"
        return self._sessions.get(token)

    def login(self, password):
        if self.admin_pw and password == self.admin_pw:
            tok = secrets.token_urlsafe(24)
            self._sessions[tok] = "admin"
            return tok, "admin"
        if self.viewer_pw and password == self.viewer_pw:
            tok = secrets.token_urlsafe(24)
            self._sessions[tok] = "viewer"
            return tok, "viewer"
        return None, None

    def logout(self, token):
        self._sessions.pop(token, None)

    # -------------------------------------------------- lab switch (Proxlafy <-> SDR-Kit)
    LABSWITCH = "/usr/local/sbin/labswitch"

    def switch_state(self):
        """State of the other RF-lab project, via `labswitch json`. {enabled:False} if unavailable."""
        if not os.path.exists(self.LABSWITCH):
            return {"enabled": False}
        try:
            out = subprocess.check_output([self.LABSWITCH, "json"], timeout=6).decode("utf-8", "replace")
            data = json.loads(out.strip().splitlines()[-1])
            data["enabled"] = True
            return data
        except Exception:  # noqa: BLE001
            return {"enabled": False}

    def start_switch(self, target, do_install=False):
        """Launch the switch detached, so it survives this service being stopped. Returns the resolved state."""
        state = self.switch_state()
        if not state.get("enabled"):
            return None
        if target not in ("other", "proxlafy", "sdrkit"):
            target = "other"
        tgt = state.get("other") if target == "other" else target
        arg = ("install %s" % tgt) if do_install else tgt
        cmd = "sleep 2; exec %s %s" % (self.LABSWITCH, arg)
        self.log.add("Cambiando de proyecto · switching lab project → %s%s"
                     % (tgt, " (install)" if do_install else ""), "warn")
        if shutil.which("systemd-run"):
            subprocess.Popen(["systemd-run", "--collect", "--unit=proxlafy-switch",
                              "/bin/bash", "-c", cmd])
        else:
            subprocess.Popen(["setsid", "/bin/bash", "-c", cmd], start_new_session=True)
        return state

    # -------------------------------------------------- self-update from the panel
    UPDATER = "/opt/proxlafy/proxlafy-update.sh"
    UPDATE_LOG = "/var/log/proxlafy-update.log"

    def update_check(self):
        """Ask the updater (git fetch) whether a newer version is on GitHub."""
        if self.pm.demo or not os.path.exists(self.UPDATER):
            return {"ok": True, "demo": True, "behind": 0, "current": read_version(), "changes": []}
        try:
            out = subprocess.check_output(["bash", self.UPDATER, "--check", "--json"],
                                          timeout=50, stderr=subprocess.STDOUT).decode("utf-8", "replace")
            return json.loads(out.strip().splitlines()[-1])
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "error": str(e)}

    def update_log(self, maxlen=8000):
        try:
            with open(self.UPDATE_LOG, "r", encoding="utf-8", errors="replace") as f:
                return f.read()[-maxlen:]
        except Exception:  # noqa: BLE001
            return ""

    def start_update(self):
        """Launch the updater detached (survives this panel restarting) with auto-rollback."""
        if not os.path.exists(self.UPDATER):
            return False
        self.log.add("Actualizando desde el panel · updating from the panel…", "warn")
        cmd = "sleep 1; exec bash %s --yes" % self.UPDATER
        if shutil.which("systemd-run"):
            subprocess.Popen(["systemd-run", "--collect", "--unit=proxlafy-update",
                              "/bin/bash", "-c", cmd])
        else:
            subprocess.Popen(["setsid", "/bin/bash", "-c", cmd], start_new_session=True)
        return True


class Handler(BaseHTTPRequestHandler):
    server_version = "Proxlafy"
    protocol_version = "HTTP/1.1"

    @property
    def app(self):
        return self.server.app

    def log_message(self, fmt, *args):
        pass  # keep stdout clean; real logging goes through App.log

    # -------------------------------------------------- helpers
    def _token(self):
        cookie = self.headers.get("Cookie", "") or ""
        m = re.search(r"proxlafy_session=([A-Za-z0-9_\-]+)", cookie)
        return m.group(1) if m else ""

    def _role(self):
        return self.app.role_for(self._token())

    def _send_json(self, obj, status=200, headers=None):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        length = cint(self.headers.get("Content-Length"), 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:  # noqa: BLE001
            return {}

    def _require(self, role="admin"):
        r = self._role()
        if r is None:
            self._send_json({"ok": False, "error": "login"}, 401)
            return False
        if role == "admin" and r != "admin":
            self._send_json({"ok": False, "error": "read-only · solo lectura"}, 403)
            return False
        return True

    # -------------------------------------------------- GET
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path.startswith("/api/"):
            return self._api_get(path, parse_qs(parsed.query))
        return self._serve_static(path)

    def _serve_static(self, path):
        if path in ("/", ""):
            path = "/index.html"
        rel = path.lstrip("/")
        full = os.path.normpath(os.path.join(WEB, rel))
        if not full.startswith(WEB) or not os.path.isfile(full):
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        ext = os.path.splitext(full)[1].lower()
        with open(full, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", MIME.get(ext, "application/octet-stream"))
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _api_get(self, path, qs):
        if path == "/api/status":
            try:
                st = self.app.pm.status()
            except Exception as e:  # noqa: BLE001
                st = {"connected": False, "error": str(e)}
            st["role"] = self._role()
            st["auth_open"] = self.app.auth_open()
            st["count"] = len(self.app.lib.list())
            st["version"] = read_version()
            return self._send_json({"ok": True, "status": st})
        if path == "/api/cards":
            if not self._require("viewer" if self.app.viewer_pw else "admin") and not self.app.auth_open():
                if self._role() is None:
                    return
            return self._send_json({"ok": True, "cards": [feasibility.enrich(c) for c in self.app.lib.list()]})
        if path == "/api/log":
            since = cint(qs.get("since", ["0"])[0], 0)
            items, cur = self.app.log.since(since)
            return self._send_json({"ok": True, "items": items, "cursor": cur})
        if path == "/api/standalone":
            lang = "en" if (qs.get("lang", ["es"])[0] == "en") else "es"
            return self._send_json({"ok": True, "catalog": standalone_mod.catalog(lang),
                                    "status": self.app.pm.standalone_status()})
        if path == "/api/device":
            try:
                dev = self.app.pm.device_status()
            except Exception as e:  # noqa: BLE001
                dev = {"error": str(e)}
            return self._send_json({"ok": True, "device": dev})
        if path == "/api/history":
            return self._send_json({"ok": True, "history": self.app.history})
        if path == "/api/switch":
            return self._send_json({"ok": True, "switch": self.app.switch_state()})
        if path == "/api/update":
            return self._send_json({"ok": True, "update": self.app.update_check()})
        if path == "/api/update/log":
            return self._send_json({"ok": True, "log": self.app.update_log()})
        m = re.match(r"^/api/cards/([^/]+)$", path)
        if m:
            card = self.app.lib.get(m.group(1))
            if not card:
                return self._send_json({"ok": False, "error": "not found"}, 404)
            return self._send_json({"ok": True, "card": feasibility.enrich(card)})
        return self._send_json({"ok": False, "error": "unknown"}, 404)

    # -------------------------------------------------- POST / etc
    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        body = self._read_body()

        if path == "/api/login":
            tok, role = self.app.login(str(body.get("password", "")))
            if not tok:
                self.app.log.add("Intento de acceso fallido · failed login", "warn")
                return self._send_json({"ok": False, "error": "clave incorrecta · wrong password"}, 401)
            cookie = "proxlafy_session=%s; Path=/; HttpOnly; SameSite=Lax" % tok
            return self._send_json({"ok": True, "role": role}, headers={"Set-Cookie": cookie})

        if path == "/api/logout":
            self.app.logout(self._token())
            return self._send_json({"ok": True})

        if path == "/api/read":
            if not self._require("admin"):
                return
            band = str(body.get("band", "auto"))
            self.app.log.add("Buscando tarjeta (%s)… · reading (%s)…" % (band, band))
            try:
                card = self.app.pm.read(band)
            except Exception as e:  # noqa: BLE001
                self.app.log.add("Error al leer · read error: %s" % e, "err")
                return self._send_json({"ok": False, "error": str(e)}, 500)
            if not card:
                self.app.log.add("No se detectó ninguna tarjeta · no card detected", "warn")
                return self._send_json({"ok": True, "card": None})
            self.app.log.add("Detectada · detected: %s (%s)" % (card.get("type"), card.get("label")), "ok")
            entry = {"type": card.get("type"), "label": card.get("label"), "band": card.get("band"),
                     "key": card.get("key"), "t": time.time()}
            self.app.history.insert(0, entry)
            self.app.history[:] = self.app.history[:25]
            return self._send_json({"ok": True, "card": card})

        if path == "/api/cards":
            if not self._require("admin"):
                return
            card = body.get("card") or {}
            if body.get("name"):
                card["name"] = str(body["name"])[:80]
            if not card.get("type"):
                return self._send_json({"ok": False, "error": "sin datos · no card data"}, 400)
            saved = self.app.lib.save(card)
            self.app.log.add("Guardada · saved: %s" % (saved.get("name") or saved.get("label")), "ok")
            return self._send_json({"ok": True, "card": saved})

        if path == "/api/emulate":
            # Emulate a saved card (by id) OR an unsaved one (the last read, sent in the body).
            if not self._require("admin"):
                return
            card = self.app.lib.get(body["id"]) if body.get("id") else (body.get("card") or {})
            if not card or not card.get("key"):
                return self._send_json({"ok": False, "error": "sin datos · no card data"}, 400)
            seconds = cint(body.get("seconds"), 0)
            try:
                cmd = self.app.pm.start_sim(card, seconds=seconds)
            except Exception as e:  # noqa: BLE001
                self.app.log.add("No se pudo emular · emulate failed: %s" % e, "err")
                return self._send_json({"ok": False, "error": str(e)}, 500)
            self.app.log.add("Emulando · emulating: %s [%s]" % (card.get("name") or card.get("label"), cmd), "ok")
            return self._send_json({"ok": True, "command": cmd})

        if path == "/api/decode":
            if not self._require("admin"):
                return
            card = body.get("card") or {}
            if not card.get("key"):
                return self._send_json({"ok": False, "error": "sin datos · no card data"}, 400)
            self.app.log.add("Decodificando · decoding: %s…" % card.get("type"))
            try:
                card, res = self.app.pm.decode(card)
            except Exception as e:  # noqa: BLE001
                return self._send_json({"ok": False, "error": str(e)}, 500)
            self.app.log.add("Decodificación · decode: %s" % ("OK" if res.get("ok") else "falló · failed"),
                             "ok" if res.get("ok") else "err")
            return self._send_json({"ok": res.get("ok", False), "card": card, "result": res})

        m = re.match(r"^/api/cards/([^/]+)/decode$", path)
        if m:
            if not self._require("admin"):
                return
            card = self.app.lib.get(m.group(1))
            if not card:
                return self._send_json({"ok": False, "error": "not found"}, 404)
            self.app.log.add("Decodificando · decoding: %s…" % card.get("type"))
            try:
                card, res = self.app.pm.decode(card)
                self.app.lib.save(card)
            except Exception as e:  # noqa: BLE001
                return self._send_json({"ok": False, "error": str(e)}, 500)
            return self._send_json({"ok": res.get("ok", False), "card": card, "result": res})

        m = re.match(r"^/api/cards/([^/]+)/emulate$", path)
        if m:
            if not self._require("admin"):
                return
            card = self.app.lib.get(m.group(1))
            if not card:
                return self._send_json({"ok": False, "error": "not found"}, 404)
            try:
                cmd = self.app.pm.start_sim(card)
            except Exception as e:  # noqa: BLE001
                self.app.log.add("No se pudo emular · emulate failed: %s" % e, "err")
                return self._send_json({"ok": False, "error": str(e)}, 500)
            self.app.log.add("Emulando · emulating: %s [%s]" % (card.get("name") or card.get("label"), cmd), "ok")
            return self._send_json({"ok": True, "command": cmd})

        m = re.match(r"^/api/cards/([^/]+)/write$", path)
        if m:
            if not self._require("admin"):
                return
            card = self.app.lib.get(m.group(1))
            if not card:
                return self._send_json({"ok": False, "error": "not found"}, 404)
            self.app.log.add("Escribiendo a tarjeta física · writing to blank: %s" % card.get("label"))
            try:
                res = self.app.pm.write_card(card)
            except Exception as e:  # noqa: BLE001
                return self._send_json({"ok": False, "error": str(e)}, 500)
            self.app.log.add("Escritura · write: %s" % ("OK" if res["ok"] else "falló · failed"),
                             "ok" if res["ok"] else "err")
            return self._send_json({"ok": res["ok"], "result": res})

        if path == "/api/standalone/flash":
            if not self._require("admin"):
                return
            mode = str(body.get("mode", ""))
            app = self.app

            def _run():
                app.log.add("Programando standalone · programming standalone: %s" % mode, "warn")
                res = app.pm.program_standalone(mode, log=lambda ln: app.log.add(ln))
                app.log.add("Standalone: %s" % ("OK ✓" if res.get("ok") else "falló · failed"),
                            "ok" if res.get("ok") else "err")
            threading.Thread(target=_run, daemon=True).start()
            return self._send_json({"ok": True, "started": True})

        if path == "/api/emulate/stop":
            if not self._require("admin"):
                return
            self.app.pm.stop_sim()
            self.app.log.add("Emulación detenida · emulation stopped")
            return self._send_json({"ok": True})

        if path == "/api/update":
            if not self._require("admin"):
                return
            started = self.app.start_update()
            if not started:
                return self._send_json({"ok": False, "error": "actualizador no disponible · updater not available"}, 400)
            return self._send_json({"ok": True, "started": True})

        if path == "/api/switch":
            if not self._require("admin"):
                return
            target = str(body.get("target", "other")) or "other"
            do_install = bool(body.get("install"))
            state = self.app.start_switch(target, do_install)
            if state is None:
                return self._send_json({"ok": False, "error": "labswitch no disponible · not available"}, 400)
            return self._send_json({"ok": True, "target": state.get("other"),
                                    "label": state.get("other_label"), "ssid": state.get("other_ssid"),
                                    "ip": state.get("other_ip"), "install": do_install})

        return self._send_json({"ok": False, "error": "unknown"}, 404)

    def do_DELETE(self):
        m = re.match(r"^/api/cards/([^/]+)$", urlparse(self.path).path)
        if m:
            if not self._require("admin"):
                return
            ok = self.app.lib.delete(m.group(1))
            if ok:
                self.app.log.add("Tarjeta borrada · card deleted")
            return self._send_json({"ok": ok})
        return self._send_json({"ok": False, "error": "unknown"}, 404)

    def do_PATCH(self):
        m = re.match(r"^/api/cards/([^/]+)$", urlparse(self.path).path)
        if m:
            if not self._require("admin"):
                return
            card = self.app.lib.get(m.group(1))
            if not card:
                return self._send_json({"ok": False, "error": "not found"}, 404)
            body = self._read_body()
            if "name" in body:
                card["name"] = str(body["name"])[:80]
            if "notes" in body:
                card["notes"] = str(body["notes"])[:500]
            saved = self.app.lib.save(card)
            return self._send_json({"ok": True, "card": saved})
        return self._send_json({"ok": False, "error": "unknown"}, 404)


class Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, addr, app):
        self.app = app
        super().__init__(addr, Handler)


def main():
    ap = argparse.ArgumentParser(description="Proxlafy web panel")
    ap.add_argument("--port", type=int, default=0)
    ap.add_argument("--demo", action="store_true")
    args = ap.parse_args()
    if args.demo:
        os.environ["PROXLAFY_DEMO"] = "1"
    conf = load_conf(CONF_PATH)
    port = args.port or cint(conf.get("PANEL_PORT"), 80)
    app = App(conf)
    httpd = Server(("0.0.0.0", port), app)
    mode = "DEMO" if os.environ.get("PROXLAFY_DEMO") == "1" else "live"
    print("Proxlafy panel [%s] → http://0.0.0.0:%d" % (mode, port))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
