#!/usr/bin/env python3
# ----------------------------------------------------------------------------
# stream_server.py  -  Web-Overlay + Config-Backend fuer OBS
# ----------------------------------------------------------------------------
# Zweck: Waehrend Dennsen am CRT im Frontend navigiert, zeigt ein
# Browser-Overlay (OBS Browser Source) in Echtzeit, was gerade
# ausgewaehlt ist - Cover, Titel, System, Now-Playing. Das umgeht die
# Scaler-Grenze komplett: die "Menue-Ansicht" fuer den Stream kommt
# nicht mehr aus dem Videoausgang des MiSTers, sondern wird im Browser
# gerendert und von OBS ins Bild gesetzt.
#
# Reines Standard-Python (http.server + SSE), keine externen Pakete -
# passend zum Rest des Frontends. Laeuft als Daemon-Thread neben der
# Hauptschleife; publish() wird bei jeder Auswahl-Aenderung gerufen.
#
# Endpunkte:
#   GET  /            -> Overlay-Seite (fuer OBS Browser Source)
#   GET  /admin       -> Backend/Konfiguration (fuer Dennsen)
#   GET  /events      -> Server-Sent-Events: State- und Config-Push
#   GET  /state       -> aktueller State als JSON (Initial-Load)
#   GET  /config      -> aktuelle Config als JSON
#   POST /config      -> Config speichern (JSON-Body)
#   GET  /art?sys=..&name=..  -> Cover als PNG (aus lokaler .art)
# ----------------------------------------------------------------------------

import json
import os
import queue
import struct
import threading
import time
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, unquote

HERE = os.path.dirname(os.path.abspath(__file__))

DEFAULT_CONFIG = {
    "title": "",                 # optionaler Branding-Text oben
    "accent": "#e0b64a",         # Akzentfarbe
    "bg": "#0d0f14",             # Hintergrund (OBS kann per Chroma/Alpha)
    "transparent": True,         # Overlay-Hintergrund transparent lassen
    "show_boxart": True,
    "show_system": True,
    "show_list": True,           # kleine Vorschau-Liste um die Auswahl
    "show_nowplaying": True,
    "show_genre": True,          # Genre/Jahr in der Fakten-Zeile
    "show_playtime": True,       # Spielzeit in der Fakten-Zeile
    "show_ra": True,             # RetroAchievements-Fortschritt (falls eingerichtet)
    "show_favorite": True,       # Favoriten-Stern neben dem Titel
    "scale": 100,                # Prozent
    "corner": "bottom-left",     # bottom-left|bottom-right|top-left|top-right
}


class StreamServer:
    def __init__(self, art_base, port=8080, host="0.0.0.0",
                 config_path=None, log=lambda *_: None):
        self.art_base = art_base
        self.port = port
        self.host = host
        self.config_path = config_path
        self.log = log

        self._lock = threading.Lock()
        self._clients = set()            # set[queue.Queue]
        self._state = {"category": "", "name": "", "system": "",
                       "kind": "", "index": 0, "total": 0,
                       "nowplaying": None}
        self._config = dict(DEFAULT_CONFIG)
        self._load_config()

        self._httpd = None
        self._thread = None

    # -- Config -----------------------------------------------------------
    def _load_config(self):
        if not self.config_path:
            return
        try:
            with open(self.config_path) as f:
                self._config.update(json.load(f))
        except (OSError, ValueError):
            pass

    def _save_config(self):
        if not self.config_path:
            return
        try:
            dirname = os.path.dirname(self.config_path)
            if dirname:
                os.makedirs(dirname, exist_ok=True)
            tmp = self.config_path + ".tmp"
            with open(tmp, "w") as f:
                json.dump(self._config, f)
            os.replace(tmp, self.config_path)
        except OSError:
            pass

    # -- Public API -------------------------------------------------------
    def start(self):
        try:
            self._httpd = ThreadingHTTPServer((self.host, self.port),
                                              self._make_handler())
        except OSError as e:
            self.log("StreamServer: Port %d nicht verfuegbar: %s"
                     % (self.port, e))
            return False
        self._thread = threading.Thread(target=self._httpd.serve_forever,
                                        daemon=True)
        self._thread.start()
        self.log("StreamServer laeuft auf http://%s:%d/" %
                 (self.host, self.port))
        return True

    def stop(self):
        if self._httpd:
            try:
                self._httpd.shutdown()
            except Exception:
                pass

    def publish(self, state):
        """Neuen Auswahl-State an alle verbundenen Overlays pushen."""
        with self._lock:
            self._state = dict(state)
            msg = ("event: state\ndata: " +
                   json.dumps(self._state) + "\n\n")
            dead = []
            for q in self._clients:
                try:
                    q.put_nowait(msg)
                except queue.Full:
                    dead.append(q)
            for q in dead:
                self._clients.discard(q)

    def _push_config(self):
        with self._lock:
            msg = ("event: config\ndata: " +
                   json.dumps(self._config) + "\n\n")
            for q in list(self._clients):
                try:
                    q.put_nowait(msg)
                except queue.Full:
                    pass

    # -- .art -> PNG ------------------------------------------------------
    def _art_png(self, syskey, name):
        path = os.path.join(self.art_base, syskey, name + ".art")
        try:
            with open(path, "rb") as f:
                if f.read(4) != b"ART1":
                    return None
                w, h = struct.unpack("<HH", f.read(4))
                pix = zlib.decompress(f.read())
        except (OSError, zlib.error):
            return None
        if len(pix) != w * h * 4:
            return None
        # .art ist BGRA -> RGBA
        b = bytearray(pix)
        b[0::4], b[2::4] = b[2::4], b[0::4]
        return _encode_png(w, h, bytes(b))

    # -- HTTP handler -----------------------------------------------------
    def _make_handler(server):
        srv = server

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass  # keine Konsolen-Spam

            def _send(self, code, ctype, body, extra=None):
                self.send_response(code)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Cache-Control", "no-store")
                for k, v in (extra or {}).items():
                    self.send_header(k, v)
                self.end_headers()
                self.wfile.write(body)

            def _file(self, fname, ctype):
                try:
                    with open(os.path.join(HERE, fname), "rb") as f:
                        self._send(200, ctype, f.read())
                except OSError:
                    self._send(404, "text/plain", b"not found")

            def do_GET(self):
                u = urlparse(self.path)
                p = u.path
                if p == "/" or p == "/overlay":
                    self._file("stream_overlay.html", "text/html; charset=utf-8")
                elif p == "/admin":
                    self._file("stream_admin.html", "text/html; charset=utf-8")
                elif p == "/state":
                    with srv._lock:
                        body = json.dumps(srv._state).encode()
                    self._send(200, "application/json", body)
                elif p == "/config":
                    with srv._lock:
                        body = json.dumps(srv._config).encode()
                    self._send(200, "application/json", body)
                elif p == "/art":
                    q = parse_qs(u.query)
                    sysk = unquote((q.get("sys") or [""])[0])
                    name = unquote((q.get("name") or [""])[0])
                    png = srv._art_png(sysk, name) if sysk and name else None
                    if png:
                        self._send(200, "image/png", png)
                    else:
                        self._send(404, "text/plain", b"no art")
                elif p == "/events":
                    self._events()
                else:
                    self._send(404, "text/plain", b"not found")

            def do_POST(self):
                u = urlparse(self.path)
                if u.path != "/config":
                    self._send(404, "text/plain", b"not found")
                    return
                try:
                    n = int(self.headers.get("Content-Length", 0))
                    data = json.loads(self.rfile.read(n) or b"{}")
                except (ValueError, TypeError):
                    self._send(400, "text/plain", b"bad json")
                    return
                with srv._lock:
                    for k, v in data.items():
                        if k in DEFAULT_CONFIG:
                            srv._config[k] = v
                    srv._save_config()
                    body = json.dumps(srv._config).encode()
                srv._push_config()
                self._send(200, "application/json", body)

            def _events(self):
                q = queue.Queue(maxsize=32)
                with srv._lock:
                    srv._clients.add(q)
                    initial = ("event: config\ndata: " +
                               json.dumps(srv._config) + "\n\n" +
                               "event: state\ndata: " +
                               json.dumps(srv._state) + "\n\n")
                try:
                    self.send_response(200)
                    self.send_header("Content-Type", "text/event-stream")
                    self.send_header("Cache-Control", "no-store")
                    self.send_header("Connection", "keep-alive")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(initial.encode())
                    self.wfile.flush()
                    while True:
                        try:
                            msg = q.get(timeout=15)
                        except queue.Empty:
                            msg = ": keep-alive\n\n"   # SSE-Kommentar
                        self.wfile.write(msg.encode())
                        self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError, OSError):
                    pass
                finally:
                    with srv._lock:
                        srv._clients.discard(q)

        return H


# -- minimaler PNG-Encoder (stdlib zlib) ---------------------------------
def _encode_png(w, h, rgba):
    def chunk(typ, data):
        return (struct.pack(">I", len(data)) + typ + data +
                struct.pack(">I", zlib.crc32(typ + data) & 0xffffffff))
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)  # RGBA, 8-bit
    stride = w * 4
    raw = bytearray()
    for y in range(h):
        raw.append(0)                       # Filter 0 (None)
        raw += rgba[y * stride:(y + 1) * stride]
    idat = zlib.compress(bytes(raw), 6)
    return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")
