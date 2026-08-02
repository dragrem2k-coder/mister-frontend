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
import re
import struct
import threading
import time
import urllib.error
import urllib.request
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
    "show_ra_badges": True,      # Erfolgs-Einblendung mit Icon bei neuem Erfolg
    "show_favorite": True,       # Favoriten-Stern neben dem Titel
    "scale": 100,                # Prozent
    "corner": "bottom-left",     # bottom-left|bottom-right|top-left|top-right
}


class StreamServer:
    def __init__(self, art_base, port=8080, host="0.0.0.0",
                 config_path=None, art_hd=None, badge_cache_dir=None,
                 log=lambda *_: None):
        self.art_base = art_base
        self.port = port
        self.host = host
        self.config_path = config_path
        self.log = log
        # Erfolgs-Icons (RA-Badges) werden dauerhaft hier zwischen-
        # gespeichert - ohne Angabe direkt neben dem Cover-Ordner, damit
        # nichts zusaetzlich konfiguriert werden muss.
        self.badge_cache_dir = badge_cache_dir or os.path.join(
            os.path.dirname(art_base.rstrip("/")) or ".", "ra_badges")
        # Cover-Ordner in Suchreihenfolge - genau wie das Frontend: erst
        # HD, dann Standard. So findet das Overlay dieselben Cover.
        self._art_bases = [b for b in (art_hd, art_base) if b]
        self._art_idx_cache = {}

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

    def publish_achievement(self, achievement):
        """Pusht ein "gerade freigeschaltet"-Ereignis an alle
        verbundenen Overlays - eigener SSE-Event-Typ ("achievement"),
        unabhaengig vom normalen Auswahl-State (siehe publish()).
        achievement: dict mit title/description/points/badge (Badge-
        Name, wird im Overlay ueber /badge?name=... geladen)."""
        with self._lock:
            msg = ("event: achievement\ndata: " +
                   json.dumps(achievement) + "\n\n")
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
    def _art_dir_index(self, base, syskey):
        """Wie im Frontend: Name ohne "NNN "-Praefix -> Dateiname, damit
        Cover aus nummerierten Sets gefunden werden. Pro (Ordner, System)
        gecacht."""
        key = (base, syskey)
        idx = self._art_idx_cache.get(key)
        if idx is None:
            idx = {}
            try:
                for fn in os.listdir(os.path.join(base, syskey)):
                    if not fn.endswith(".art"):
                        continue
                    b = fn[:-4]
                    stripped = re.sub(r"^\d+\s+", "", b)
                    if stripped != b and stripped not in idx:
                        idx[stripped] = fn
            except OSError:
                pass
            self._art_idx_cache[key] = idx
        return idx

    def _find_art(self, syskey, name):
        """Cover-Datei suchen - genau wie das Frontend: erst der HD-Ordner
        (art_hd), dann der Standard (art); in jedem erst exakter Name,
        sonst tolerant (fuehrende "NNN "-Nummer ignoriert)."""
        for base in self._art_bases:
            exact = os.path.join(base, syskey, name + ".art")
            if os.path.exists(exact):
                return exact
            fn = self._art_dir_index(base, syskey).get(name)
            if fn:
                return os.path.join(base, syskey, fn)
        return None

    def _art_png(self, syskey, name):
        path = self._find_art(syskey, name)
        if not path:
            return None
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
        # .art ist BGRA -> RGBA; Alpha deckend setzen. Die von unseren
        # eigenen Werkzeugen (mister_boxart.py/art_convert.py) erzeugten
        # ART1-Pixel haben durchgehend Alpha=0 (der bytearray-Puffer wird
        # nie explizit gesetzt) - der MiSTer-Framebuffer ignoriert Alpha
        # sowieso, ein Browser aber nicht: ohne diese Zeile waere JEDES
        # Cover im Overlay komplett durchsichtig/schwarz erschienen.
        b = bytearray(pix)
        b[0::4], b[2::4] = b[2::4], b[0::4]
        b[3::4] = b"\xff" * (len(b) // 4)
        return _encode_png(w, h, bytes(b))

    RA_BADGE_URL = "https://media.retroachievements.org/Badge/%s.png"

    def _badge_png(self, badge_name):
        """Liefert das Erfolgs-Icon (PNG) zu einem RA-Badge-Namen - aus
        dem lokalen Cache, falls schon einmal geladen, sonst live von
        RA heruntergeladen und DAUERHAFT zwischengespeichert (Icons
        aendern sich nicht mehr, sobald ein Erfolg einmal
        veroeffentlicht ist - anders als Cover also kein "koennte sich
        aendern"-Fall). Anders als bei unseren eigenen .art-Dateien ist
        HIER keine Formatumwandlung noetig - RAs Badges sind schon PNG,
        wir reichen die Originalbytes 1:1 weiter."""
        if not badge_name or not re.match(r"^[A-Za-z0-9_-]+$", badge_name):
            return None   # nur unbedenkliche Namen - kein Pfad-Trick moeglich
        try:
            os.makedirs(self.badge_cache_dir, exist_ok=True)
        except OSError:
            pass
        path = os.path.join(self.badge_cache_dir, badge_name + ".png")
        try:
            with open(path, "rb") as f:
                return f.read()
        except OSError:
            pass
        try:
            req = urllib.request.Request(
                self.RA_BADGE_URL % badge_name,
                headers={"User-Agent": "MiSTerFrontend/1.0"})
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                if resp.status != 200:
                    return None
                data = resp.read()
        except (urllib.error.URLError, OSError, TimeoutError):
            return None
        try:
            with open(path, "wb") as f:
                f.write(data)
        except OSError:
            pass
        return data


    # -- HTTP handler -----------------------------------------------------
    def _make_handler(server):
        srv = server

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass  # keine Konsolen-Spam

            def _send(self, code, ctype, body, extra=None):
                extra = extra or {}
                self.send_response(code)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Access-Control-Allow-Origin", "*")
                if "Cache-Control" not in extra:
                    self.send_header("Cache-Control", "no-store")
                for k, v in extra.items():
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
                elif p == "/badge":
                    q = parse_qs(u.query)
                    badge_name = unquote((q.get("name") or [""])[0])
                    png = srv._badge_png(badge_name) if badge_name else None
                    if png:
                        # Badges aendern sich nie mehr - der Browser
                        # darf das lange cachen (anders als /art oder
                        # /state, die bewusst no-store sind).
                        self._send(200, "image/png", png,
                                  {"Cache-Control": "public, max-age=604800"})
                    else:
                        self._send(404, "text/plain", b"no badge")
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
