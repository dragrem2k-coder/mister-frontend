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

# DIE PASSENDE C-BIBLIOTHEK FUER DIESEN RECHNER (Build 239).
#
# MUSS VOR DEM LADEN DES FRONTENDS STEHEN: fe/art.py laedt die
# Bibliothek beim Import, ein spaeter gesetztes DRAGEND_LIB kommt zu
# spaet.
#
# WARUM DAS HIER STEHT UND NICHT IN EINZELNEN TESTS: frontend/
# libdragend.so ist die ARM-Fassung fuer das Geraet und laedt auf einem
# PC gar nicht ("wrong ELF class: ELFCLASS32"). Ohne diesen Griff lief
# die GANZE Suite ohne C - also auf einem Weg, den das Geraet nie geht.
# Vier Tests sind daran gescheitert, ohne dass am Frontend etwas falsch
# war (test_masken, test_text_in_c, test_zeilen_in_c,
# test_beschreibung), und sie haben es sogar gesagt: "libdragend geladen
# - ohne sie prueft dieser Test nichts". Gefunden beim Bau von Build
# 239; rot waren sie schon vorher, und Build 238 ist damit rausgegangen.
#
# EINIGE TESTS SETZEN DIE VARIABLE SELBST (test_c_modul.py und
# Geschwister) - genau deshalb wird ein vorhandener Wert hier NIE
# ueberschrieben. Wer die Python-Fassung pruefen will, setzt
# DRAGEND_LIB auf einen Pfad, der nicht existiert.
if not os.environ.get("DRAGEND_LIB"):
    import platform as _plat
    _m = _plat.machine().lower()
    _kandidaten = []
    if _m in ("x86_64", "amd64", "i386", "i686"):
        _kandidaten = ["libdragend_x86.so"]
    elif _m.startswith("arm") or _m.startswith("aarch"):
        _kandidaten = ["libdragend_neon.so", "libdragend.so"]
    _wurzel = os.path.dirname(_HERE)
    for _name in _kandidaten:
        for _ort in (os.path.join(_wurzel, "frontend", "c", _name),
                     os.path.join(_wurzel, "frontend", _name)):
            if os.path.exists(_ort):
                os.environ["DRAGEND_LIB"] = _ort
                break
        if os.environ.get("DRAGEND_LIB"):
            break

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
    # Build 227: das gemerkte "schon einmal da" des Textzeichners.
    self._text_einmal = set()
    self._TEXTCACHE_LIMIT = 2000
    self._vsync_supported = False
    self.full_redraw_gen = 0
    self.flip_gen = 0
    self.flip_event = threading.Event()
    self._textcache_hits = 0
    self._textcache_misses = 0
    self._textcache_evictions = 0


_echt_strftime = fm.time.strftime      # fuer alle anderen Formate, siehe unten

fm.Framebuffer.__init__ = _fake_fb_init
fm.Framebuffer.refresh_geometry = lambda s: None
fm.Framebuffer.close = lambda s: None
fm.time.monotonic = lambda: NOW[0]

# BUGFIX (Build 94, beim Pruefen des Flacker-Fixes aufgefallen): die
# kuenstliche Uhr oben ersetzte nur monotonic(), NICHT strftime(). Die
# Statuszeile im Hauptmenue zeigt aber die Uhrzeit (%H:%M, siehe
# _draw_status_bar()) - und die kommt weiterhin von der echten Uhr.
#
# Folge: faellt in einem Test oder in diag_lightpath.py ein
# Minutenwechsel zwischen den Referenz-Aufbau und den Vergleichs-Aufbau,
# unterscheiden sich die beiden Bilder in den Ziffern der Uhrzeit - und
# der Vergleich meldet eine Abweichung, die es gar nicht gibt. Genau das
# ist einmal passiert (diag_lightpath.py sprang von 22 auf 23 Faelle und
# war beim naechsten Lauf wieder bei 22) und hat eine Viertelstunde
# Fehlersuche an der voellig falschen Stelle gekostet.
#
# Feste Uhrzeit fuer ALLE Vergleiche. Dass die Statuszeile damit immer
# dieselbe Zeit zeigt, ist fuer Pixelvergleiche genau richtig.
fm.time.strftime = lambda fmt, *a: (
    "13:37" if fmt == "%H:%M" else _echt_strftime(fmt, *a))


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


def _zwischenspeicher_leeren():
    """Den Einstellungs-Zwischenspeicher (Build 135) verwerfen.

    WICHTIG fuer jeden Test: dieser Pruefstand friert time.monotonic()
    ein (siehe NOW oben). Der Zwischenspeicher wird aber ueber genau
    diese Uhr ungueltig - bei stehender Uhr also NIE. Wer in einem Test
    eine Einstellungsdatei direkt anlegt oder loescht, statt die
    zugehoerige toggle-Funktion zu benutzen, muss deshalb hier
    aufraeumen. Genau darueber ist tools/test_cover_prewarm.py beim Bau
    von Build 135 gestolpert."""
    try:
        import fe.zwischenspeicher as _zs
        _zs.vergessen()
    except Exception:                                    # noqa: BLE001
        pass


def make_frontend(page=1, titles=None):
    """Echte Frontend()-Instanz mit einer festen, kuenstlichen
    Spieleliste - damit die Tests unabhaengig davon laufen, welche ROMs
    auf dem Testrechner liegen."""
    _zwischenspeicher_leeren()
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
