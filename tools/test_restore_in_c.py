#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Das Freiraeumen des Hintergrunds laeuft in C (Build 216).

NUTZERWUNSCH: "das scrollen kann noch schneller gehen bitte bei
gedrueckten tasten oben, unten, links, rechts."

WORAN ES LAG, und es ist eine alte Baustelle mit einer vergessenen
Haelfte. `_bg_fill()` und `_restore_row_bg()` sind Zwillinge - beide
kopieren einen Ausschnitt der Hintergrund-Vorlage in den Puffer, Zeile
fuer Zeile. Build 209 hat den einen nach C geholt
(`rechtecke_kopieren()` in c/dragend.c) und den anderen stehen gelassen.
Ausgerechnet der andere laeuft in JEDEM Scrollschritt.

DIE ZWEI MESSUNGEN, DIE DEN UMBAU BEGRUENDEN - getrennt, weil sie von
verschiedenen Rechnern kommen und nur zusammen eine Aussage sind:

  1. ANTEIL am Schritt, Entwicklungsrechner, Wanduhr, 40 Schritte je
     Ansicht: Kachelansicht 29 %, Galerie 34 %, Liste 1 %. Ein Anteil
     ist uebertragbar, die Millisekunden dahinter nicht.
  2. PREIS JE ZEILE auf dem Geraet, aus Bench-Abschnitt I (Build 215,
     DE10-Nano): 952 kurze Zeilen kosten ueber memoryview 8,34 ms,
     ueber rechtecke_kopieren in C 3,22 ms. Also 2,6x.

Je Schritt sind das 1541 freigeraeumte Bildzeilen in der Galerie (516
Cover-Karte, 495 Textspalte, zweimal 253 Leistenkacheln, 24 Fusszeile)
und 815 in der Kachelansicht. Nicht die Bytes zaehlen, sondern die ZAHL
DER ZEILEN - genau das hat Abschnitt I gemessen.

WAS DIESER TEST PRUEFT

  1. Dass C und Python BITGENAU dasselbe schreiben - an vielen Formen,
     auch an den schiefen (Rand, Ueberhang, negative Ecken).
  2. Dass der Zeichenweg wirklich durch C geht und nicht heimlich
     weiter in Python schleift.
  3. Dass die Zahl der Python-Zeilenoperationen je Scrollschritt
     gesunken ist - eine ZAEHLUNG, also auf jedem Rechner dieselbe
     Aussage.
  4. Dass ohne libdragend nichts kaputt ist, sondern nur langsamer.

Ausfuehren:
    python3 tools/test_restore_in_c.py
"""
import os
import random
import shutil
import struct
import sys
import tempfile
import zlib

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
sys.path.insert(0, _HIER)

if not os.environ.get("DRAGEND_LIB"):
    for _k in (os.path.join(_REPO, "frontend", "c", "libdragend_x86.so"),
               os.path.join(_REPO, "frontend", "libdragend_x86.so")):
        if os.path.exists(_k):
            os.environ["DRAGEND_LIB"] = _k
            break

import _harness as H                                     # noqa: E402

fm = H.fm
sys.path.insert(0, os.path.join(_REPO, "frontend"))
import fe.art as A                                       # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


TMP = tempfile.mkdtemp(prefix="restore_c_")
BASIS = os.path.join(TMP, "art")
os.makedirs(os.path.join(BASIS, "SNES"))
TITEL = (["Spiel %02d" % i for i in range(20)]
         + ["Ein deutlich laengerer Titel Nummer %02d" % i
            for i in range(20, 40)])
for _i, _t in enumerate(TITEL):
    _pk = bytes(((_i * 37) % 256, (_i * 91) % 256, (_i * 53) % 256, 255))
    with open(os.path.join(BASIS, "SNES", _t + ".art"), "wb") as _f:
        _f.write(b"ART1" + struct.pack("<HH", 400, 533)
                 + zlib.compress(_pk * (400 * 533), 1))
fm.ART_BASE = A.ART_BASE = BASIS
fm.ART_HD = A.ART_HD = BASIS
A._art_index_cache.clear()
A.THUMB_CACHE_DIR = os.path.join(TMP, "tc")
os.makedirs(A.THUMB_CACHE_DIR)
fm.SYSART_BASE = A.SYSART_BASE = os.path.join(_REPO, "frontend", "sysart")


def spieleliste(breite, hoehe, ansicht):
    H.set_screen(breite, hoehe)
    f = H.make_frontend(page=1)
    fm.ART.auslagern = None
    f.lader.beenden()
    _n, node, _k = f.cats[f.cat_i]
    node["items"] = [(t, "game", ("/f/%d.sfc" % i, ".sfc", "SNES", None, None))
                     for i, t in enumerate(TITEL)]
    node.pop("_display_items_cache", None)
    f.ansicht_setzen(ansicht)
    for i in range(len(TITEL)):
        f.item_i = i
        f.draw()
    return f


# ---------------------------------------------------------------------------
print("Test 1: C und Python schreiben BITGENAU dasselbe")
# ---------------------------------------------------------------------------
# Die Formen sind bewusst auch schief: genau an den Raendern rechnet die
# C-Fassung selbst (abrunden_div, max_rows), und dort koennte sie um eine
# Zeile abweichen, ohne dass es in einer Ansicht auffiele.
f = spieleliste(1920, 1080, "raster")
fb = f.fb
FORMEN = [(0, 0, 1920, 1080),            # ganzes Bild
          (0, 0, 1920, 1),               # eine volle Zeile
          (134, 210, 402, 516),          # Cover-Karte der Galerie
          (518, 204, 1268, 495),         # Textspalte der Galerie
          (134, 987, 1652, 24),          # Fusszeile
          (1, 1, 1, 1),                  # ein Punkt
          (1919, 1079, 1, 1),            # der letzte Punkt
          (1900, 1000, 100, 200),        # Ueberhang rechts UND unten
          (-10, -10, 50, 50),            # negative Ecke
          (0, 1079, 1920, 5),            # Ueberhang nur unten
          (1919, 0, 5, 1080)]            # Ueberhang nur rechts
rng = random.Random(215216)
for _ in range(20):
    x = rng.randrange(-20, 1930)
    y = rng.randrange(-20, 1090)
    FORMEN.append((x, y, rng.randrange(1, 300), rng.randrange(1, 300)))

cur_bg = fb._rowcache.get(fb.bg_key(fm.C_BG))
check("die Hintergrund-Vorlage liegt vor", cur_bg is not None,
      "ohne sie prueft dieser Test nichts")
muster = bytearray(((i * 7 + 3) % 256) for i in range(256)) * 64
abweichungen = 0
for (x, y, w, h) in FORMEN:
    # Beide Wege auf DENSELBEN Ausgangszustand ansetzen, damit der
    # Vergleich nur das Kopieren betrifft.
    for i in range(0, len(fb.buf), len(muster)):
        fb.buf[i:i + len(muster)] = muster[:len(fb.buf) - i]
    vorher = bytes(fb.buf)
    f._restore_row_bg(x, y, w, h)
    mit_c = bytes(fb.buf)
    fb.buf[:] = vorher
    # Die Python-Fassung mit denselben Grenzen wie die Methode sie
    # rechnet - sonst vergleicht man zwei verschiedene Bereiche.
    need = w * 4
    y0 = max(0, y)
    y1 = min(fb.height, y + h)
    if x >= 0 and need > 0 and y1 > y0:
        limit = min(len(fb.buf), len(cur_bg))
        max_rows = (limit - (x * 4) - need) // fb.stride + 1
        if max_rows < y1:
            y1 = max(y0, max_rows)
        if y1 > y0:
            f._restore_row_bg_py(cur_bg, fb.buf, fb.stride, x, y0, need,
                                 y1 - y0)
    ohne_c = bytes(fb.buf)
    if mit_c != ohne_c:
        abweichungen += 1
        d = sum(1 for a, b in zip(mit_c, ohne_c) if a != b)
        print("       Form %s: %d abweichende Bytes" % ((x, y, w, h), d))
check("alle %d Formen gleich" % len(FORMEN), abweichungen == 0,
      "%d Formen weichen ab" % abweichungen)

# ---------------------------------------------------------------------------
print()
print("Test 2: der Zeichenweg geht wirklich durch C")
# ---------------------------------------------------------------------------
# Ohne diese Pruefung koennte der C-Aufruf still fehlschlagen (falsche
# Grenzen, fehlende Bibliothek) und alles liefe weiter in Python -
# richtig, aber ohne den Gewinn, und Test 1 saehe es nicht.
gezaehlt = [0]
_echt_c = fm._c_rechtecke_kopieren


def _haken_c(*a, **k):
    gezaehlt[0] += 1
    return _echt_c(*a, **k)


fm._c_rechtecke_kopieren = _haken_c
try:
    f.item_i = 1
    f._force_full_redraw = True
    f.draw()
    gezaehlt[0] = 0
    f.item_i = 2
    f.draw()
    check("ein Rasterschritt ruft C mehrfach", gezaehlt[0] >= 3,
          "%d Aufrufe - erwartet sind zwei Kacheln, Namenszeile, "
          "Fusszeile" % gezaehlt[0])
    g = spieleliste(1920, 1080, "galerie")
    g.item_i = 1
    g._force_full_redraw = True
    g.draw()
    gezaehlt[0] = 0
    g.item_i = 2
    g.draw()
    check("ein Galerieschritt ebenso", gezaehlt[0] >= 3,
          "%d Aufrufe" % gezaehlt[0])
finally:
    fm._c_rechtecke_kopieren = _echt_c

# ---------------------------------------------------------------------------
print()
print("Test 3: die Zahl der Python-Zeilen je Schritt ist gesunken")
# ---------------------------------------------------------------------------
# DIE EINZIGE ZAHL IN DIESEM TEST, DIE ETWAS UEBER TEMPO SAGT - und sie
# ist eine ZAEHLUNG, kein Zeitwert. Damit gilt sie auf jedem Rechner,
# waehrend Millisekunden von hier nach dem DE10-Nano nichts bedeuten
# (Faktor 39 bei reinem Python, gemessen an Abschnitt C).
#
# Gezaehlt werden die Durchlaeufe der Python-Schleife in
# _restore_row_bg_py(). Vor Build 216 war das die Zahl der
# freigeraeumten Bildzeilen: Kachelansicht 815, Galerie 1541. Jetzt
# muessen es NULL sein, solange libdragend da ist.
_zeilen = [0]
_echt_py = type(f)._restore_row_bg_py


def _haken_py(self, cur_bg, buf, stride, x, y0, need, zeilen):
    _zeilen[0] += zeilen
    return _echt_py(self, cur_bg, buf, stride, x, y0, need, zeilen)


type(f)._restore_row_bg_py = _haken_py
try:
    for ansicht, tag in (("raster", "Kachelansicht"), ("galerie", "Galerie"),
                         ("liste", "Liste       ")):
        fx = spieleliste(1920, 1080, ansicht)
        fx.item_i = 1
        fx._force_full_redraw = True
        fx.draw()
        _zeilen[0] = 0
        fx.item_i = 2
        fx.draw()
        check("%s: keine Python-Zeile mehr" % tag, _zeilen[0] == 0,
              "%d Zeilen liefen noch in Python" % _zeilen[0])
finally:
    type(f)._restore_row_bg_py = _echt_py

# ---------------------------------------------------------------------------
print()
print("Test 4: ohne libdragend ist nichts kaputt, nur langsamer")
# ---------------------------------------------------------------------------
# Der Rueckfall laeuft auf jedem Geraet, auf dem die Bibliothek fehlt
# oder nicht passt - also dort, wo niemand hinsieht.
_alt = fm._c_rechtecke_kopieren
try:
    fm._c_rechtecke_kopieren = lambda *a, **k: False
    for ansicht in ("raster", "galerie"):
        fp = spieleliste(1920, 1080, ansicht)
        fp.item_i = 1
        fp._force_full_redraw = True
        fp.draw()
        fp.item_i = 2
        fp.draw()
        schnell = bytes(fp.fb.mm)
        fp._force_full_redraw = True
        fp.draw()
        voll = bytes(fp.fb.mm)
        d = sum(1 for a, b in zip(schnell, voll) if a != b)
        check("ohne C bleibt %s bitgenau" % ansicht, d == 0,
              "%d abweichende Bytes" % d)
    # Und der Rueckfall muss dann auch wirklich laufen.
    _zeilen[0] = 0
    type(f)._restore_row_bg_py = _haken_py
    try:
        fq = spieleliste(1920, 1080, "raster")
        fq.item_i = 1
        fq._force_full_redraw = True
        fq.draw()
        _zeilen[0] = 0
        fq.item_i = 2
        fq.draw()
        check("und zwar in Python", _zeilen[0] > 100,
              "%d Zeilen - erwartet rund 815" % _zeilen[0])
    finally:
        type(f)._restore_row_bg_py = _echt_py
finally:
    fm._c_rechtecke_kopieren = _alt

# ---------------------------------------------------------------------------
print()
print("Test 5: der volle-Breite-Fall bleibt die Abkuerzung")
# ---------------------------------------------------------------------------
# Deckt der Bereich die ganze Breite ab, ist er EIN zusammenhaengender
# Block - eine Zuweisung, kein C-Aufruf und keine Schleife. Das steht
# seit Build 132 da und war schon damals gemessen; ein C-Aufruf waere
# hier teurer als die Zuweisung selbst.
gezaehlt[0] = 0
fm._c_rechtecke_kopieren = _haken_c
try:
    f._restore_row_bg(0, 100, 1920, 50)
    check("volle Breite ruft C NICHT", gezaehlt[0] == 0,
          "%d Aufrufe" % gezaehlt[0])
    f._restore_row_bg(10, 100, 500, 50)
    check("ein schmaler Bereich schon", gezaehlt[0] == 1,
          "%d Aufrufe" % gezaehlt[0])
finally:
    fm._c_rechtecke_kopieren = _echt_c

shutil.rmtree(TMP, ignore_errors=True)

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  - " + x)
    sys.exit(1)
print("Alles in Ordnung.")
