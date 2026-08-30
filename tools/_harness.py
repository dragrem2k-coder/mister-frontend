#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gemeinsame Attrappe fuer die Zeichen-Tests in tools/.

Laedt frontend/frontend.py als Modul und ersetzt NUR den hardwarenahen
Teil des Framebuffers (Geraet oeffnen, mmap, Geometrie aus /sys lesen)
durch einen einfachen bytearray-Puffer. Alle echten Zeichenroutinen
(clear/rect/text/flip ...) bleiben unveraendert - genau darum geht es:
die Tests vergleichen tatsaechlich erzeugte Pixel.

Der Pfad zu frontend.py wird in dieser Reihenfolge bestimmt:
  1. Umgebungsvariable FRONTEND_PY (falls gesetzt)
  2. ../frontend/frontend.py relativ zu DIESER Datei

Damit laufen die Tests aus jedem Arbeitsverzeichnis und aus jeder
Kopie des Projektordners - frueher stand hier ein fester Pfad aus der
Entwicklungsumgebung, wodurch die Skripte nur auf genau einem Rechner
startbar waren.
"""
import os
import sys
import threading
import importlib.util

_HERE = os.path.dirname(os.path.abspath(__file__))
FRONTEND_PY = os.environ.get(
    "FRONTEND_PY",
    os.path.join(os.path.dirname(_HERE), "frontend", "frontend.py"))

if not os.path.exists(FRONTEND_PY):
    sys.stderr.write(
        "frontend.py nicht gefunden: %s\n"
        "Pfad per Umgebungsvariable setzen, z.B.:\n"
        "  FRONTEND_PY=/pfad/zu/frontend.py python3 %s\n"
        % (FRONTEND_PY, sys.argv[0]))
    sys.exit(2)

# Arbeitsverzeichnis auf den Projektordner setzen: einige Pfade im
# Frontend werden relativ aufgeloest, ausserdem findet der Modul-Loader
# so die Unterordner (art/, meta/ ...) genauso wie auf dem MiSTer.
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(FRONTEND_PY))))

_spec = importlib.util.spec_from_file_location("frontend_mod", FRONTEND_PY)
fm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fm)

# Aufloesung, die die naechste Framebuffer-Instanz melden soll.
SCREEN = [1920, 1080]

# Kuenstliche Uhr: alle Zeitvergleiche im Frontend (Puls, Laufschrift,
# Ruhe-Erkennung) laufen damit reproduzierbar statt in Echtzeit.
NOW = [1000.0]


def _fake_fb_init(self, bpp=32):
    w, h = SCREEN
    self.width, self.height, self.bpp = w, h, bpp
    self.stride = w * 4
    self.size = self.stride * h
    self.fd = -1
    self.mm = bytearray(self.size)
    self.buf = bytearray(self.size)
    self._rowcache = {}
    self._rectcache = {}
    self._glyphcache = {}
    self._textcache = {}
    self._textcache_order = []
    self._TEXTCACHE_LIMIT = 2000
    self._vsync_supported = False
    self.full_redraw_gen = 0
    self.flip_gen = 0
    self.flip_event = threading.Event()
    self._textcache_hits = 0
    self._textcache_misses = 0
    self._textcache_evictions = 0


fm.Framebuffer.__init__ = _fake_fb_init
fm.Framebuffer.refresh_geometry = lambda s: None
fm.Framebuffer.close = lambda s: None
fm.time.monotonic = lambda: NOW[0]


def set_screen(w, h):
    """Aufloesung fuer die NAECHSTE Frontend()-Instanz festlegen."""
    SCREEN[0], SCREEN[1] = w, h


# Beispiel-Titel mit Umlauten/scharfem s - deckt den erweiterten
# Zeichensatz (FONT_EXTRA) und lange, laufschrift-pflichtige Titel ab.
TITLES = [
    "Super Mario World",
    "The Legend of Zelda - A Link to the Past",
    "König der Löwen",
    "F-Zero",
    "Chrono Trigger",
    "Secret of Mana",
    "Super Metroid",
    "Grüße aus Straßburg",
    "Mega Man X",
    "Donkey Kong Country 2 - Diddy's Kong Quest",
    "Star Fox",
    "Earthbound",
    "Terranigma",
    "Pilotwings",
    "Actraiser",
    "Tetris Attack",
    "Yoshi's Island",
    "Final Fantasy VI",
    "Illusion of Time",
    "Soul Blazer",
]


def make_frontend(page=1, titles=None):
    """Echte Frontend()-Instanz mit einer festen, kuenstlichen
    Spieleliste - damit die Tests unabhaengig davon laufen, welche ROMs
    auf dem Testrechner liegen."""
    fe = fm.Frontend()
    fe._last_input_time = NOW[0] - 10.0
    if page == 1:
        fe.page = 1
        fe.cat_i = 0
        fe.nav_path = []
        _, node, _ = fe.cats[0]
        node["folders"] = {}
        node["items"] = [
            (t, "game", ("/f/%d.sfc" % i, ".sfc", "SNES", None, None))
            for i, t in enumerate(titles or TITLES)]
        node.pop("_display_items_cache", None)
        fe.item_i = 0
        fe.scroll = 0
    else:
        fe.page = 0
        fe.cat_i = 0
        fe.cat_scroll = 0
    return fe
