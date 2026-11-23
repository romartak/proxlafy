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
import secrets
import argparse
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from http import HTTPStatus
from urllib.parse import urlparse, parse_qs

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(HERE, "web")
sys.path.insert(0, HERE)
from pm3 import PM3  # noqa: E402

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
        cards_dir = conf.get("CARDS_DIR") or "/var/lib/proxlafy/cards"
        if os.environ.get("PROXLAFY_DEMO") == "1" and not os.path.isdir("/var/lib/proxlafy"):
            cards_dir = os.environ.get("PROXLAFY_CARDS_DIR", os.path.join(HERE, "..", "data", "cards"))
        self.lib = Library(os.path.abspath(cards_dir))
        self.pm = PM3(
            client=conf.get("PM3_CLIENT", "pm3"),
            port=conf.get("PM3_PORT", "auto"),
            firmware=conf.get("PM3_FIRMWARE", "iceman"),
            demo=os.environ.get("PROXLAFY_DEMO") == "1",
        )
        self._sessions = {}   # token -> role
        self.log.add("Proxlafy iniciado · started", "ok")

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
            return self._send_json({"ok": True, "cards": self.app.lib.list()})
        if path == "/api/log":
            since = cint(qs.get("since", ["0"])[0], 0)
            items, cur = self.app.log.since(since)
            return self._send_json({"ok": True, "items": items, "cursor": cur})
        m = re.match(r"^/api/cards/([^/]+)$", path)
        if m:
            card = self.app.lib.get(m.group(1))
            if not card:
                return self._send_json({"ok": False, "error": "not found"}, 404)
            return self._send_json({"ok": True, "card": card})
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

        if path == "/api/emulate/stop":
            if not self._require("admin"):
                return
            self.app.pm.stop_sim()
            self.app.log.add("Emulación detenida · emulation stopped")
            return self._send_json({"ok": True})

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
