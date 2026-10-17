#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Die gemerkte Form zeichnet BITGENAU dasselbe (Build 271).

WORAUF DAS ZURUECKGEHT - und es ist diesmal eine Zahl, kein Verdacht.
Bench 10 (Abschnitt K, Liste/liste mit Cover) teilt den groessten
Fuellposten erstmals auf:

    karte_mit_schatten  gemessen                13,04 ms
                        im C-Fueller selbst      5,83 ms  (49,5 Rechtecke)
                        davor in Python          7,21 ms

Die 7,21 ms sind die Zeilenschleifen ueber die Eckenzeilen (bei Radius
96 rund 300 Durchlaeufe je Karte, und zwar zweimal - Schatten und
Karte), das Buendeln und der Bau des Tupels fuer C. Dieselbe Karte, an
derselben Stelle, in JEDEM Scrollschritt neu gerechnet.

DIE FORM HAENGT ABER NICHT AN DER POSITION. Sie haengt an Breite,
Hoehe, Radius, Versatz und der ausgesparten Spanne - und das sind beim
Scrollen immer dieselben. Gemerkt wird deshalb die gebuendelte
Streifenliste RELATIV zur linken oberen Ecke; der Aufrufer rechnet
seine Position dazu (eine Listenkomprehension ueber rund 50 Tupel).

WAS DARAN GEFAEHRLICH IST, und genau das prueft diese Datei: am
BILDRAND darf die Form nicht anders aussehen als in der Mitte, sonst
waere sie unter demselben Schluessel falsch gemerkt. Beide Aufrufer
stellen das vorher her - rect_rounded() beschneidet x, y, w und h gleich
am Anfang, rect_rounded_schatten() tut dasselbe in gestalt() fuer beide
Kaesten. Der Beweis dafuer ist aber keine Ueberlegung, sondern der
bitgenaue Vergleich hier: jede Form wird zweimal gezeichnet, einmal mit
Cache und einmal ohne, und die Bildspeicher muessen Byte fuer Byte
gleich sein - an jedem Rand, mit und ohne C.

Ausfuehren:
    python3 tools/test_form_cache.py
"""
import os
import random
import sys

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

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


H.set_screen(1920, 1080)
fe = H.make_frontend(page=1)
fb = fe.fb

KARTE = (210, 220, 230)
SCHATTEN = (8, 8, 10)

# ---------------------------------------------------------------------------
print("Test 0: ein frisch gebauter Bildspeicher merkt sich Formen auch")
# ---------------------------------------------------------------------------
# DIESE PRUEFUNG KOMMT ZUERST, weil sie als einzige nicht zu
# beschaedigen ist, indem man sie besteht: alle folgenden Tests setzen
# fb._formcache selbst, und genau deshalb koennten sie gruen sein,
# waehrend auf dem Geraet nichts gemerkt wird.
#
# Beim Suite-Lauf von Build 271 war es genau so herum kaputt: die
# Vorgabe liegt auf Klassenebene bei None ("nicht merken", damit ein
# ueber __new__ gebautes Objekt nicht mitten im Zeichnen mit einem
# AttributeError aussteigt), und die Attrappe in tools/_harness.py
# bildet die Feldliste des echten __init__ nach. Fehlt das Feld dort,
# laeuft die GANZE Suite mit abgeschaltetem Cache.
check("das Feld ist ein Wortverzeichnis, kein None",
      isinstance(fb._formcache, dict),
      "Vorgabe ist None - dann merkt sich nichts etwas. Entweder im "
      "echten __init__ (fe/framebuffer.py) oder in _fake_fb_init "
      "(tools/_harness.py) fehlt die Zeile")

# Die Masse der echten Aufrufer stehen zuerst: die Boxart-Karte der
# Listenansicht (769x945, Versatz 9, Radius 12 - siehe den Kommentar in
# karte_mit_schatten), die Galeriekarte (378x492) und die
# Zeilenhervorhebung (853x39).
FORMEN = [
    (1035, 36, 769, 945, 9, 12),
    (120, 80, 378, 492, 6, 8),
    (40, 500, 853, 39, 0, 6),
    (0, 0, 300, 300, 9, 96),
    (0, 0, 1920, 1080, 12, 96),
    (1920 - 300, 1080 - 300, 300, 300, 9, 24),
    (-40, -40, 300, 300, 9, 24),
    (1850, 1000, 300, 300, 9, 24),
    (-40, 500, 300, 300, 0, 24),
    (500, -40, 300, 300, 0, 24),
    (100, 100, 64, 64, 3, 0),
    (100, 100, 64, 64, 3, 1),
    (100, 100, 2, 2, 1, 1),
    (300, 300, 500, 500, 60, 200),
]
rng = random.Random(271)
for _ in range(30):
    FORMEN.append((rng.randrange(-60, 1950), rng.randrange(-60, 1100),
                   rng.randrange(1, 500), rng.randrange(1, 500),
                   rng.choice((0, 1, 6, 9, 30)),
                   rng.choice((0, 1, 4, 12, 48, 96))))


def _leeren():
    fb.buf[:] = bytearray(len(fb.buf))


def _zeichnen(x, y, w, h, versatz, radius, ohne, aussparen):
    """Alle drei Wege einmal - sie bauen aufeinander auf."""
    fb.rect_rounded(x, y, w, h, KARTE, radius, ohne=ohne)
    fb.rect_rounded_schatten(x, y, w, h, versatz, SCHATTEN, radius,
                             ohne=ohne)
    fb.karte_mit_schatten(x, y, w, h, versatz, KARTE, SCHATTEN, radius,
                          aussparen=aussparen)


def _bild(x, y, w, h, versatz, radius, ohne, aussparen, cache):
    """Einmal zeichnen und den Bildspeicher zurueckgeben."""
    fb._formcache = {} if cache else None
    _leeren()
    if cache:
        # ZWEIMAL, damit der zweite Durchgang wirklich ein TREFFER ist -
        # ein Cache, der nur beim Fuellen geprueft wird, prueft nichts.
        _zeichnen(x, y, w, h, versatz, radius, ohne, aussparen)
        _leeren()
    _zeichnen(x, y, w, h, versatz, radius, ohne, aussparen)
    return bytes(fb.buf)


def _vergleich(titel, mit_c):
    abw = 0
    erste = None
    if not mit_c:
        fb.flaechen_fueller = None
    try:
        for (x, y, w, h, versatz, radius) in FORMEN:
            for ohne, aussparen in ((None, None),
                                    ((y + 40, y + 300), None),
                                    (None, (x + 20, y + 20, 100, 100))):
                a = _bild(x, y, w, h, versatz, radius, ohne, aussparen,
                          True)
                b = _bild(x, y, w, h, versatz, radius, ohne, aussparen,
                          False)
                if a != b:
                    abw += 1
                    if erste is None:
                        erste = "%s r=%d v=%d ohne=%s aus=%s: %d Bytes" % (
                            (x, y, w, h), radius, versatz, ohne, aussparen,
                            sum(1 for p, q in zip(a, b) if p != q))
    finally:
        if not mit_c:
            del fb.flaechen_fueller
        fb._formcache = {}
    check(titel, abw == 0, erste or "")


# ---------------------------------------------------------------------------
print("Test 1: mit Cache und ohne Cache ist dasselbe Bild - MIT C")
# ---------------------------------------------------------------------------
_vergleich("%d Formen x 3 Varianten bitgenau gleich" % len(FORMEN), True)

# ---------------------------------------------------------------------------
print()
print("Test 2: dasselbe OHNE C (der Rueckfallweg)")
# ---------------------------------------------------------------------------
# Die relative Liste wird in BEIDE Wege eingespeist - in den C-Aufruf
# und in die Python-Schleife darunter. Ein Fehler im Umrechnen traefe
# beide, ein Fehler in der Reihenfolge nur einen.
_vergleich("auch ohne libdragend bitgenau gleich", False)

# ---------------------------------------------------------------------------
print()
print("Test 3: die Form wird WIRKLICH nur einmal gebaut")
# ---------------------------------------------------------------------------
# Gezaehlt, nicht gestoppt (die Lehre aus Build 267/269): der Aufbau
# einer Form endet immer in _zeilen_buendeln(). Wer den zaehlt, zaehlt
# die Aufbauten.
_echt_buendeln = fb._zeilen_buendeln
_zaehler = [0]


def _zaehl_buendeln(zeilen):
    _zaehler[0] += 1
    return _echt_buendeln(zeilen)


fb._zeilen_buendeln = _zaehl_buendeln
try:
    fb._formcache = {}
    _leeren()
    for _ in range(20):
        fb.karte_mit_schatten(1035, 36, 769, 945, 9, KARTE, SCHATTEN, 12)
    mit = _zaehler[0]
    _zaehler[0] = 0
    fb._formcache = None
    for _ in range(20):
        fb.karte_mit_schatten(1035, 36, 769, 945, 9, KARTE, SCHATTEN, 12)
    ohne = _zaehler[0]
finally:
    del fb._zeilen_buendeln
    fb._formcache = {}
check("zwanzig Karten kosten nur den ersten Aufbau", mit <= 2,
      "%d Aufbauten mit Cache, %d ohne" % (mit, ohne))
check("ohne Cache wird jedes Mal neu gebaut", ohne >= 20,
      "%d" % ohne)

# ---------------------------------------------------------------------------
print()
print("Test 4: dieselbe Form an einer ANDEREN Stelle")
# ---------------------------------------------------------------------------
# DER EIGENTLICHE FALLSTRICK. Wird die Position mitgemerkt, zeichnet
# die zweite Karte an der Stelle der ersten - und das faellt bei einem
# Vergleich, der jede Form einzeln prueft, nicht auf.
fb._formcache = {}
_leeren()
fb.karte_mit_schatten(100, 100, 300, 300, 9, KARTE, SCHATTEN, 24)
_a = bytes(fb.buf)
_leeren()
fb.karte_mit_schatten(700, 400, 300, 300, 9, KARTE, SCHATTEN, 24)
_b = bytes(fb.buf)
fb._formcache = None
_leeren()
fb.karte_mit_schatten(700, 400, 300, 300, 9, KARTE, SCHATTEN, 24)
_c = bytes(fb.buf)
check("die zweite Karte steht an ihrer eigenen Stelle", _b == _c,
      "%d Bytes Unterschied" % sum(1 for p, q in zip(_b, _c) if p != q))
check("und nicht an der der ersten", _a != _b,
      "beide Bilder gleich - dann hat der Test nichts geprueft")

# ---------------------------------------------------------------------------
print()
print("Test 5: der Schluessel enthaelt alles, was die Form aendert")
# ---------------------------------------------------------------------------
# Jede dieser Groessen aendert die Form. Wuerde eine im Schluessel
# fehlen, kaeme die zweite Zeichnung mit der Form der ersten.
VARIANTEN = (
    ("Breite", (300, 300, 9, 24), (320, 300, 9, 24)),
    ("Hoehe", (300, 300, 9, 24), (300, 340, 9, 24)),
    ("Radius", (300, 300, 9, 24), (300, 300, 9, 40)),
    ("Versatz", (300, 300, 9, 24), (300, 300, 20, 24)),
)
for name, (w1, h1, v1, r1), (w2, h2, v2, r2) in VARIANTEN:
    fb._formcache = {}
    _leeren()
    fb.karte_mit_schatten(400, 300, w1, h1, v1, KARTE, SCHATTEN, r1)
    _leeren()
    fb.karte_mit_schatten(400, 300, w2, h2, v2, KARTE, SCHATTEN, r2)
    _nach = bytes(fb.buf)
    fb._formcache = None
    _leeren()
    fb.karte_mit_schatten(400, 300, w2, h2, v2, KARTE, SCHATTEN, r2)
    check("%s im Schluessel" % name, _nach == bytes(fb.buf),
          "%d Bytes" % sum(1 for p, q in zip(_nach, bytes(fb.buf))
                           if p != q))
fb._formcache = {}

# ---------------------------------------------------------------------------
print()
print("Test 6: der Cache laeuft nicht ueber")
# ---------------------------------------------------------------------------
fb._formcache = {}
for i in range(fb.ROWCACHE_MAX_ENTRIES + 50
               if hasattr(fb, "ROWCACHE_MAX_ENTRIES") else 250):
    fb.rect_rounded(10, 10, 100 + (i % 200), 60, KARTE, 8)
check("die Zahl der Eintraege bleibt begrenzt",
      len(fb._formcache) <= 400, "%d Eintraege" % len(fb._formcache))

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
