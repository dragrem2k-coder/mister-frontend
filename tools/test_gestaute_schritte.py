#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gestaute Navigationsschritte werden zusammengefasst (Build 307).

DER BEFUND, Nutzermeldung vom 08.11.:

    "wenn ich 10 mal kurz hintereinander hoch druecke und dann wieder
     nach unten druecke bleibt er auch ab und zu haengen !! fuehlt sich
     bloed an"

DAS IST EIN ANDERER FEHLER ALS DAS HALTEN, und die Messung sagt es
auch: Abschnitt L Teil 1b weist in seinem Bericht vom 07.11. fuer alle
drei Geraete **0 Ereignisse je Sekunde** aus - es gibt keinen
Dauerstrom, der Verdacht aus Build 306 ist ausgeraeumt. Was es gibt,
ist ein STAU.

Ein Listenschritt kostet laut Abschnitt J 46,57 ms. Zehn Druecker in
wenigen Zehntelsekunden kommen also schneller an, als sie gezeichnet
werden; sie sammeln sich im Puffer, und danach wurde jeder EINZELN
abgearbeitet - rund eine halbe Sekunde Nachlauf, in der die Liste von
selbst weiterwandert. Und drueckt er in dieser Zeit die andere
Richtung, lag die HINTER den restlichen neun.

ZUSAMMENFASSEN IST KEIN WEGWERFEN. Wer zehnmal drueckt, will zehn
Eintraege weiter - er bekommt sie, nur in EINEM Schritt statt in zehn.
Die Endposition ist dieselbe, gezeichnet wird einmal, und die andere
Richtung ist sofort dran.

WAS DIESER TEST SICHERT:
  1. zehn gestaute Schritte werden zu einem Sprung,
  2. eine ANDERE Aktion dahinter wird zurueckgelegt, nicht
     verschluckt - und kommt beim naechsten Aufruf als ERSTE,
  3. nicht-Navigation wird nie zusammengefasst (zwei OKs sind zwei
     Entscheidungen),
  4. ohne Stau kostet es nichts - kein select(), kein os.read(),
  5. die Obergrenze wird eingehalten,
  6. flush() raeumt die zurueckgelegte Aktion mit,
  7. die Endposition ist dieselbe wie bei Schritt fuer Schritt,
  8. und im Quelltext wird der Faden auch wirklich benutzt.

Ausfuehren:
    python3 tools/test_gestaute_schritte.py
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H          # noqa: E402,F401  (setzt den Pfad)

import fe.input as FI         # noqa: E402
from _quelle import koerper, nur_code                     # noqa: E402

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

fails = []


def check(name, ok, info=""):
    if ok:
        print("  OK   %s %s" % (name, info))
    else:
        print("  FEHL %s %s" % (name, info))
        fails.append(name)


print(__doc__.strip().split("\n")[0])
print()

EV_KEY = FI.EV_KEY
KEY_UP, KEY_DOWN, KEY_ENTER = FI.KEY_UP, FI.KEY_DOWN, FI.KEY_ENTER


def ev(etype, code, value):
    return struct.pack(FI.EVENT_FMT, 0, 0, etype, code, value)


def tipp(code):
    """Ein kurzer Druecker: druecken und loslassen."""
    return [ev(EV_KEY, code, 1), ev(EV_KEY, code, 0)]


class GeraeteAttrappe:
    def __init__(self):
        self.path = "/dev/input/event-test"
        self.name = "Attrappe"
        self.is_kbd = True
        self.fd = 4242
        self.axis = {}


def manager():
    inp = FI.InputManager.__new__(FI.InputManager)
    dev = GeraeteAttrappe()
    inp.devices = {dev.path: dev}
    inp.held = None
    inp.last_scan = 1e18
    inp._zeichenzeit = {}
    inp._zeichenproben = {}
    inp._ereignis_rest = FI.deque()
    inp._vorgelegt = None
    inp.seiten_aktionen = set()
    inp.eingabe_zeit = 0.0
    inp._select_down = {}
    inp._select_kombiniert = False
    inp._last_repeat_time = 0.0
    inp._last_repeat_act = None
    inp._last_repeat_iv = 0.0
    return inp, dev


def fuellen(inp, dev, ereignisse):
    """Den Puffer so fuellen, wie ein Buendel-Lesevorgang es tut."""
    for roh in ereignisse:
        inp._ereignis_rest.append((dev,) + struct.unpack(FI.EVENT_FMT, roh))


# ---------------------------------------------------------------------------
print("Test 1: zehn Druecker werden zu einem Sprung")
# ---------------------------------------------------------------------------
inp, dev = manager()
STROM = []
for _ in range(10):
    STROM += tipp(KEY_UP)
fuellen(inp, dev, STROM)
_erste = inp._aus_rest()
_n = inp.gestaute_schritte(_erste)
check("die erste Aktion ist 'up'", _erste == "up", "%r" % (_erste,))
check("und neun weitere liegen gestaut", _n == 9,
      "%d zusaetzliche Schritte - zusammen %d Eintraege in EINEM "
      "Zeichenschritt statt in zehn" % (_n, _n + 1))
check("der Puffer ist danach leer", not inp._ereignis_rest,
      "%d uebrig" % len(inp._ereignis_rest))
check("und nichts wurde zurueckgelegt", inp._vorgelegt is None,
      "%r" % (inp._vorgelegt,))

# ---------------------------------------------------------------------------
print()
print("Test 2: die andere Richtung wird ZURUECKGELEGT, nicht verschluckt")
# ---------------------------------------------------------------------------
# DIE WICHTIGSTE PRUEFUNG. Ein verschluckter Tastendruck waere ein
# schlimmerer Fehler als der, den dieser Build behebt - und genau das
# ist der Richtungswechsel, den der Nutzer beschreibt.
inp, dev = manager()
STROM2 = []
for _ in range(10):
    STROM2 += tipp(KEY_UP)
STROM2 += tipp(KEY_DOWN)
fuellen(inp, dev, STROM2)
_erste = inp._aus_rest()
_n = inp.gestaute_schritte(_erste)
check("zehn hoch, davon neun gestaut", (_erste, _n) == ("up", 9),
      "%r / %d" % (_erste, _n))
check("das 'down' liegt zurueckgelegt bereit", inp._vorgelegt == "down",
      "%r" % (inp._vorgelegt,))
# Und read_action() muss es als ERSTES liefern - vor jeder faelligen
# Wiederholung, denn es ist die aelteste Aktion, die es gibt.
_echt_select = FI.select.select
try:
    FI.select.select = lambda *a: ([], [], [])
    _danach = inp.read_action(timeout=0.0)
finally:
    FI.select.select = _echt_select
check("read_action() liefert es sofort", _danach == "down",
      "%r - zwei Zeichenschritte statt elf" % (_danach,))

# ---------------------------------------------------------------------------
print()
print("Test 3: nicht-Navigation wird nie zusammengefasst")
# ---------------------------------------------------------------------------
# Zwei OKs hintereinander sind ZWEI Entscheidungen. Wer die zu einer
# macht, verliert eine - und bei "ok" heisst das ein Spielstart, der
# nicht kommt, oder ein Dialog, der zweimal bestaetigt wird.
inp, dev = manager()
STROM3 = tipp(KEY_ENTER) + tipp(KEY_ENTER)
fuellen(inp, dev, STROM3)
_erste = inp._aus_rest()
# VORHER GEGEN NACHHER ist hier die richtige Messung, und die erste
# Fassung dieses Tests hat eine absolute Zahl erwartet und war zu
# Recht rot: _aus_rest() verbraucht oben selbst das Druck-Ereignis,
# es bleiben also drei (Loslassen, Druck, Loslassen) - nicht zwei.
# Geprueft gehoert, dass gestaute_schritte() NICHTS anfasst.
_vorher = len(inp._ereignis_rest)
_n = inp.gestaute_schritte(_erste)
check("'ok' wird nicht zusammengefasst", (_erste, _n) == ("ok", 0),
      "%r / %d" % (_erste, _n))
check("und der zweite Druck liegt unangetastet im Puffer",
      len(inp._ereignis_rest) == _vorher,
      "%d Ereignisse vorher, %d nachher - nichts verbraucht"
      % (_vorher, len(inp._ereignis_rest)))

# ---------------------------------------------------------------------------
print()
print("Test 4: ohne Stau kostet es nichts")
# ---------------------------------------------------------------------------
# DER NORMALFALL - ein Druck, ein Schritt. Hier darf kein select() und
# kein os.read() stattfinden, sonst haette dieser Build jeden
# gewoehnlichen Tastendruck teurer gemacht.
inp, dev = manager()
fuellen(inp, dev, tipp(KEY_UP))
_erste = inp._aus_rest()
_zugriffe = []
_echt_read, _echt_select = os.read, FI.select.select
try:
    os.read = FI.os.read = lambda *a: _zugriffe.append("read")
    FI.select.select = lambda *a: _zugriffe.append("select") or ([], [], [])
    _n = inp.gestaute_schritte(_erste)
finally:
    os.read = FI.os.read = _echt_read
    FI.select.select = _echt_select
check("kein Stau -> 0 zusaetzliche Schritte", _n == 0, "%d" % _n)
check("und kein einziger Zugriff auf das Geraet", not _zugriffe,
      "%r" % (_zugriffe,))

# ---------------------------------------------------------------------------
print()
print("Test 5: die Obergrenze wird eingehalten")
# ---------------------------------------------------------------------------
inp, dev = manager()
STROM5 = []
for _ in range(200):
    STROM5 += tipp(KEY_DOWN)
fuellen(inp, dev, STROM5)
_erste = inp._aus_rest()
_n = inp.gestaute_schritte(_erste)
check("nicht mehr als NAV_ZUSAMMEN_MAX", _n <= FI.NAV_ZUSAMMEN_MAX,
      "%d von hoechstens %d" % (_n, FI.NAV_ZUSAMMEN_MAX))
check("aber auch nicht weniger als die Grenze", _n == FI.NAV_ZUSAMMEN_MAX,
      "%d - bei 200 anliegenden muss die Grenze greifen" % _n)

# ---------------------------------------------------------------------------
print()
print("Test 6: flush() raeumt die zurueckgelegte Aktion mit")
# ---------------------------------------------------------------------------
inp, dev = manager()
inp._vorgelegt = "down"
inp.devices = {}
inp.flush()
check("nach flush ist nichts zurueckgelegt", inp._vorgelegt is None,
      "sonst waere es ein Tastendruck aus der Zeit VOR dem Spiel")

# ---------------------------------------------------------------------------
print()
print("Test 7: die Endposition ist dieselbe wie Schritt fuer Schritt")
# ---------------------------------------------------------------------------
# DIE ZUSAGE, auf die es ankommt: zusammengefasst heisst NICHT anders.
# Geprueft an der Rechnung selbst, ueber viele Faelle - Rundum-
# Navigation per Modulo macht aus n Einzelschritten genau einen
# Schritt der n-fachen Weite.
_abweichung = []
for laenge in (1, 2, 7, 13, 60, 1100, 31199):
    for weite in (1, 3, 6, 12):
        for n in (1, 2, 9, 32):
            for start in (0, 1, laenge - 1, laenge // 3):
                for richtung in (-1, 1):
                    _einzeln = start
                    for _ in range(n):
                        _einzeln = (_einzeln + weite * richtung) % laenge
                    _zusammen = (start + weite * n * richtung) % laenge
                    if _einzeln != _zusammen:
                        _abweichung.append(
                            (laenge, weite, n, start, richtung,
                             _einzeln, _zusammen))
check("ein Sprung der n-fachen Weite trifft denselben Eintrag",
      not _abweichung,
      "%r" % (_abweichung[:3],) if _abweichung else
      "geprueft fuer Listen bis 31.199 Eintraege, alle Weiten, "
      "beide Richtungen")

# ---------------------------------------------------------------------------
print()
print("Test 8: am Quelltext")
# ---------------------------------------------------------------------------
_inp_src = open(os.path.join(_REPO, "frontend", "fe", "input.py"),
                encoding="utf-8").read()
_gs = nur_code(koerper(_inp_src, "gestaute_schritte"))
check("gestaute_schritte() liest nur aus dem Puffer",
      "_aus_rest()" in _gs and "os.read" not in _gs
      and "select" not in _gs,
      "ein Geraetezugriff hier wuerde jeden Tastendruck teurer machen")
check("und legt Fremdes zurueck", "_vorgelegt" in _gs,
      "verschlucken waere schlimmer als der behobene Fehler")
check("nur die vier Richtungen", "REPEAT_AXIS" in _gs,
      "zwei OKs sind zwei Entscheidungen")

_ra = nur_code(koerper(_inp_src, "read_action"))
check("read_action() bedient das Zurueckgelegte als Erstes",
      "_vorgelegt" in _ra
      and _ra.index("_vorgelegt") < _ra.index("deadline ="),
      "es ist die aelteste Aktion, die es gibt")

_fe = open(H.FRONTEND_PY, encoding="utf-8", errors="replace").read()
check("die Hauptschleife benutzt den Zaehler",
      "gestaute_schritte(act)" in _fe,
      "sonst waere die ganze Mechanik toter Code - der Fehler aus "
      "Build 305")
check("und die vier Richtungen stehen in EINEM Zweig",
      'elif act in ("up", "down", "left", "right"):' in _fe,
      "vier Kopien des Faktors waeren die Dopplung, aus der in "
      "Build 293 ein halb angewandter Fix wurde")

# ---------------------------------------------------------------------------
print()
if fails:
    print("FEHLGESCHLAGEN (%d):" % len(fails))
    for f in fails:
        print("  - %s" % f)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
