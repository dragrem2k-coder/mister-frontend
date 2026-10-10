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

from fe.obs_websocket import switch_scene as _obs_switch_scene
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, unquote

HERE = os.path.dirname(os.path.abspath(__file__))

DEFAULT_CONFIG = {
    "title": "",                 # optionaler Branding-Text oben
    "accent": "#e0b64a",         # Akzentfarbe
    "bg": "#0d0f14",             # Hintergrund (OBS kann per Chroma/Alpha)
    "transparent": True,         # Overlay-Hintergrund transparent lassen
    # Build 254: der Spieltitel selbst. Bisher stand er immer da -
    # wer den Titel schon im Bild hat (Capture-Karte) oder ihn
    # bewusst nicht verraten will, konnte ihn nicht abschalten.
    "show_name": True,
    "show_boxart": True,
    "show_system": True,
    "show_list": True,           # kleine Vorschau-Liste um die Auswahl
    "show_nowplaying": True,
    "show_genre": True,          # Genre/Jahr in der Fakten-Zeile
    "show_playtime": True,       # Spielzeit in der Fakten-Zeile
    "show_ra": True,             # RetroAchievements-Fortschritt (falls eingerichtet)
    "show_ra_badges": True,      # Erfolgs-Einblendung mit Icon bei neuem Erfolg
    # NEU (Build 253, Nutzerwunsch nach einem Screenshot): die
    # Erfolgs-Wand - alle Erfolge des laufenden Spiels als Raster,
    # freigeschaltete in Farbe, die uebrigen ausgegraut.
    "show_ra_wall": False,       # Vorgabe AUS - sie belegt Platz
    "ra_wall_corner": "top-right",   # wie corner, eigene Wahl
    "ra_wall_cols": 12,          # Kacheln je Zeile
    # Build 254: wie viele Zeilen sichtbar sind. 0 = alle (kein
    # Scrollen). Sonst wird das Raster auf diese Hoehe begrenzt
    # und laeuft langsam durch.
    "ra_wall_rows": 0,
    "show_favorite": True,       # Favoriten-Stern neben dem Titel
    "scale": 100,                # Prozent
    "corner": "bottom-left",     # bottom-left|bottom-right|top-left|top-right
    # NEUES FEATURE (Nutzerwunsch: "wenn ich ein Spiel starte, sollen
    # Zuschauer automatisch die Capture-Karten-Szene sehen statt des
    # eingefrorenen Frontend-Spiegels, und beim Zurueckkehren wieder
    # die Frontend-Szene") - OBS-WebSocket-Zugangsdaten UND die beiden
    # Szenennamen, die umgeschaltet werden sollen. Bewusst UEBER
    # dieselbe /config-Route wie die restlichen Overlay-Einstellungen
    # editierbar (Passwort/Hostname liessen sich ueber die Controller-
    # gesteuerte On-Screen-Menuefuehrung des Frontends kaum vernuenftig
    # eingeben) - kein zweites, paralleles Konfigurationssystem noetig.
    "obs_control_enabled": False,
    "obs_host": "",
    "obs_port": 4455,
    "obs_password": "",
    "obs_game_scene": "",
    "obs_frontend_scene": "",
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
        # Build 253: der zuletzt veroeffentlichte Stand der Erfolgs-Wand.
        #
        # GEMERKT, NICHT NUR DURCHGEREICHT, und das ist der Grund: ein
        # Overlay, das sich MITTEN im Spiel neu verbindet (OBS-Szene
        # gewechselt, Browserquelle neu geladen), bekaeme sonst eine
        # leere Wand und muesste bis zum naechsten Abruf warten - und
        # der kommt erst in RA_WATCH_POLL_INTERVAL Sekunden. Der
        # gemerkte Stand geht deshalb im Begruessungspaket mit, genau
        # wie config und state.
        self._erfolge = None
        self._badge_vorrat = set()       # schon geholte/versuchte Icons
        self._state = {"category": "", "name": "", "system": "",
                       "kind": "", "index": 0, "total": 0,
                       "nowplaying": None}
        self._config = dict(DEFAULT_CONFIG)
        self._load_config()

        # NEUES FEATURE (Nutzerwunsch: "CRT und HDMI koennen nicht
        # gleichzeitig laufen - waere es machbar, wenn man auf CRT
        # laeuft, es per Websocket als Stream-Overlay angezeigt werden
        # kann?"): recherchiert und bestaetigt (mehrere MiSTer-Forum-
        # Quellen uebereinstimmend) - der Linux-Framebuffer haengt fest
        # am einzigen vorhandenen Scaler, echte gleichzeitige Ausgabe in
        # JEWEILS nativer Aufloesung auf CRT UND HDMI ist auf dieser
        # Hardware nicht moeglich. Diese Funktion umgeht das Problem
        # NICHT technisch, sondern macht den aktuellen Bildschirminhalt
        # zusaetzlich als Bild ueber HTTP abrufbar - wer auf CRT laeuft,
        # kann so trotzdem auf einem Handy/zweiten Monitor/im Stream
        # sehen, was gerade im Frontend passiert.
        self._screen_png = None
        self._screen_lock = threading.Lock()

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

    def publish_screen(self, width, height, stride, buf):
        """Aktuellen Framebuffer-Inhalt als PNG zwischenspeichern, damit
        /screen.png ihn ausliefern kann - siehe Kommentar bei
        self._screen_png in __init__ zum Hintergrund dieser Funktion.

        Nimmt bewusst rohe Framebuffer-Werte entgegen (nicht schon
        fertig konvertiert) - die Umwandlung (Stride-Padding entfernen,
        BGRA->RGBA, siehe _art_png() fuer dasselbe Muster bei
        Cover-Bildern) bleibt komplett hier gekapselt, der Aufrufer
        (frontend.py) muss die Einzelheiten des PNG-Formats nicht
        kennen.

        Bewusst OHNE staendige Wiederholung/Threading HIER drin - der
        Aufrufer (frontend.py) entscheidet, wie oft das aufgerufen wird
        (siehe dortiger Kommentar zur Drosselung, gerade bei der
        deutlich groesseren HDMI-Aufloesung wichtig fuer die schwache
        MiSTer-CPU)."""
        row_bytes = width * 4
        if stride == row_bytes:
            rgba = bytearray(buf)
        else:
            # Stride-Padding vorhanden (Framebuffer-Zeilen sind auf eine
            # Grenze ausgerichtet, die nicht zwangsläufig width*4
            # entspricht) - Zeile fuer Zeile nur die tatsaechlichen
            # Pixel-Bytes uebernehmen, Auffuellung verwerfen. _encode_png()
            # erwartet lueckenlos gepackte Zeilen (stride = width*4 intern
            # angenommen), sonst waere das Ergebnis schief/verzerrt.
            rgba = bytearray(row_bytes * height)
            for y in range(height):
                so = y * stride
                do = y * row_bytes
                rgba[do:do + row_bytes] = buf[so:so + row_bytes]
        # Framebuffer ist BGRA (Projekt-Konvention), PNG/Browser
        # erwarten RGBA - B und R vertauschen, Alpha undeckend lassen
        # ist hier kein Problem (Browser zeigt volle Deckkraft nur bei
        # Alpha=255) - siehe _art_png() fuer dieselbe Notwendigkeit bei
        # Cover-Bildern und die dortige Begruendung.
        rgba[0::4], rgba[2::4] = rgba[2::4], rgba[0::4]
        rgba[3::4] = b"\xff" * (len(rgba) // 4)
        png = _encode_png(width, height, bytes(rgba))
        with self._screen_lock:
            self._screen_png = png

    def _obs_switch(self, scene_key):
        """Gemeinsame Grundlage fuer obs_switch_to_game()/
        obs_switch_to_frontend() - liest die aktuelle Konfiguration und
        wechselt per WebSocket zur passenden Szene (siehe
        fe/obs_websocket.py fuer das eigentliche Protokoll). scene_key
        ist "obs_game_scene" oder "obs_frontend_scene" - der jeweilige
        Konfigurationsschluessel, nicht der Szenenname selbst.

        Bewusst KOMPLETT still bei Fehlern/Deaktivierung (kein LOG-
        Aufruf hier) - dieselbe Begruendung wie in fe/obs_websocket.py:
        ein nicht konfiguriertes oder nicht erreichbares OBS darf den
        eigentlichen Spielstart/die Rueckkehr zum Menue niemals
        beeintraechtigen, und staendige Fehlermeldungen fuer ein
        bewusst NICHT genutztes Feature waeren nur Log-Rauschen."""
        with self._lock:
            cfg = dict(self._config)
        if not cfg.get("obs_control_enabled"):
            return
        host = cfg.get("obs_host") or ""
        scene = cfg.get(scene_key) or ""
        if not host or not scene:
            return
        _obs_switch_scene(host, int(cfg.get("obs_port") or 4455),
                          cfg.get("obs_password") or "", scene)

    def obs_switch_to_game(self):
        """Aufzurufen, sobald ein Core bestaetigt gestartet ist (siehe
        run_core() in frontend.py) - wechselt OBS zur Capture-Karten-
        Szene, falls konfiguriert."""
        self._obs_switch("obs_game_scene")

    def obs_switch_to_frontend(self):
        """Aufzurufen, sobald das Frontend wieder sichtbar ist (Core
        beendet/zurueck zum Menue, siehe run_core() in frontend.py) -
        wechselt OBS zurueck zur Frontend-Spiegel-Szene, falls
        konfiguriert."""
        self._obs_switch("obs_frontend_scene")

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

    # Wie viele Icons auf einmal im Hintergrund geholt werden, und wie
    # lange dazwischen Pause ist.
    #
    # DAS IST DER EINE ECHTE HAKEN DIESER WAND, und er gehoert
    # gedrosselt: ein Spiel mit 98 Erfolgen heisst beim allerersten Mal
    # 98 Icons von retroachievements.org. Danach liegen sie dauerhaft
    # auf der Karte (Icons aendern sich nicht mehr, siehe
    # _badge_png()), es ist also wirklich nur das erste Mal - aber in
    # genau diesem Moment laeuft ein Spiel, und der Abruf-Faden, der
    # die neuen Erfolge erkennt, darf dabei nicht haengen.
    #
    # Deshalb: ein EIGENER Faden, zwei Icons gleichzeitig, eine halbe
    # Sekunde Pause zwischen den Paketen. Bei 98 Icons sind das rund
    # 25 Sekunden im Hintergrund, und niemand merkt etwas davon.
    BADGE_VORRAT_GLEICHZEITIG = 2
    BADGE_VORRAT_PAUSE = 0.5

    def _badges_vorholen(self, namen):
        """Die Icons der Wand im Hintergrund in den Cache holen.

        WARUM UEBERHAUPT VORHOLEN, wo das Overlay sie doch selbst
        anfragt: der Browser fragt alle auf einmal an, und jede
        Anfrage, die nicht im Cache liegt, laedt sie dann im
        HTTP-Faden von RA nach - mit 5 Sekunden Zeitlimit. Bei einer
        frischen Karte stehen dann Dutzende Anfragen gleichzeitig an,
        und der Browser gibt einen Teil davon auf. Das Ergebnis waere
        eine Wand mit Loechern, die erst nach mehrmaligem Neuladen
        voll wird.

        Vorgeholt wird deshalb hier, langsam und im Hintergrund.
        Was schon da ist, kostet nichts - _badge_png() liest dann nur
        die Datei."""
        offen = []
        with self._lock:
            for n in namen:
                if n and n not in self._badge_vorrat:
                    self._badge_vorrat.add(n)
                    offen.append(n)
        if not offen:
            return

        def arbeiter():
            for i in range(0, len(offen), self.BADGE_VORRAT_GLEICHZEITIG):
                paket = offen[i:i + self.BADGE_VORRAT_GLEICHZEITIG]
                faeden = []
                for n in paket:
                    t = threading.Thread(target=self._badge_png, args=(n,),
                                         daemon=True)
                    t.start()
                    faeden.append(t)
                for t in faeden:
                    t.join(timeout=8.0)
                time.sleep(self.BADGE_VORRAT_PAUSE)
            self.log("Overlay: %d Erfolgs-Icons vorgeholt" % len(offen))

        threading.Thread(target=arbeiter, daemon=True).start()

    def publish_achievements(self, daten):
        """Die ganze Erfolgsliste des laufenden Spiels ans Overlay -
        die "Wand" (Build 253).

        daten: dict mit
            "items":  Liste aus {"badge": str, "an": bool, "titel": str,
                                 "punkte": int}
            "anzahl": (freigeschaltet, gesamt)
            "punkte": (erreicht, gesamt)

        EIGENER EREIGNISTYP, nicht an publish() angehaengt: der
        Auswahl-Zustand wird bei jeder Bewegung im Menue geschickt, die
        Erfolgsliste aber nur, wenn sie sich wirklich geaendert hat.
        Beides zusammen hiesse, bei jedem Scrollschritt hundert
        Eintraege ueber die Leitung zu schicken.

        GEMERKT WIRD SIE AUSSERDEM, damit ein Overlay, das sich mitten
        im Spiel neu verbindet, sofort die volle Wand hat."""
        with self._lock:
            self._erfolge = daten
            msg = ("event: achievements\ndata: " +
                   json.dumps(daten) + "\n\n")
            dead = []
            for q in self._clients:
                try:
                    q.put_nowait(msg)
                except queue.Full:
                    dead.append(q)
            for q in dead:
                self._clients.discard(q)
        try:
            self._badges_vorholen([e.get("badge") for e in
                                   (daten.get("items") or ())])
        except Exception:                                # noqa: BLE001
            pass      # Vorholen ist Beiwerk, nie kritisch

    def clear_achievements(self):
        """Die Wand leeren - wenn kein Spiel mehr laeuft.

        Ohne das stuende nach der Rueckkehr ins Menue die Wand des
        zuletzt gespielten Spiels weiter da, und zwar bis zum naechsten
        Spielstart. Das saehe nicht nach "fertig" aus, sondern nach
        einem haengengebliebenen Bild."""
        with self._lock:
            if self._erfolge is None:
                return
            self._erfolge = None
            msg = "event: achievements\ndata: null\n\n"
            for q in list(self._clients):
                try:
                    q.put_nowait(msg)
                except queue.Full:
                    pass

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
                elif p == "/screen.png":
                    with srv._screen_lock:
                        png = srv._screen_png
                    if png:
                        # bewusst no-store (Standard-Verhalten schon
                        # oben in _send()) - jedes Bild ist nur eine
                        # Momentaufnahme, der Browser soll IMMER neu
                        # abfragen, nie eine alte Version zwischenlagern
                        self._send(200, "image/png", png)
                    else:
                        self._send(404, "text/plain", b"noch kein Bild")
                elif p == "/mirror":
                    self._file("stream_mirror.html", "text/html; charset=utf-8")
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
                    # Build 253: die Erfolgs-Wand gehoert mit ins
                    # Begruessungspaket. Verbindet sich ein Overlay
                    # MITTEN im Spiel neu (OBS-Szene gewechselt,
                    # Browserquelle neu geladen), haette es sonst eine
                    # leere Wand bis zum naechsten Abruf - und der
                    # kommt erst Sekunden spaeter.
                    if srv._erfolge is not None:
                        initial += ("event: achievements\ndata: " +
                                    json.dumps(srv._erfolge) + "\n\n")
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
