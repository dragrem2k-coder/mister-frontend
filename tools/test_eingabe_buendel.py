#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ereignisse werden buendelweise gelesen (Build 306).

DER BEFUND, Nutzermeldung vom 07.11.:

    "in jeder listenansicht wenn ich hoch und runter scrolle und dann
     mal eine richtung oben oder unten gedrueckt halte und dann nach
     oben gedrueckt halte reagiert manchmal die eingabe ueberhaupt
     nicht! oder sehr langsam und dauert lange"

read_action() las bisher GENAU EIN Ereignis je os.read(). Eine
gehaltene Taste liefert aber Buendel (EV_MSC, EV_KEY mit value==2,
EV_SYN), und ein Pad mit Lagesensoren sendet dauernd - der Kommentar
bei Build 280 nennt das Geraet, an dem es zuerst auffiel: "Die
Lagesensoren senden dauernd, und keines ihrer Ereignisse ist eine
Aktion."

Jedes dieser Ereignisse kostete einen eigenen Systemaufruf, UND ZWAR
AUF DEM FADEN, DER AUCH ZEICHNET. Bei einem Schritt von 55 ms liegt
beim naechsten Hinsehen ein ganzer Stapel vor.

WAS DABEI NICHT PASSIEREN DARF, und das ist der eigentliche Grund fuer
diesen Test: wird mitten im Buendel eine Aktion gefunden, muss der
REST aufgehoben werden. Sonst faellt ein Loslassen hinter einem
Tastendruck weg - genau der Fehler aus Build 276, den Build 277 mit
dem Leeren behoben hat, und den der Nutzer damals sofort gemeldet
hatte: "wenn ich nach unten gedrueckt halte und dann nach 2-3
Sekunden loslasse, scrollt er von alleine weiter".

WAS DIESER TEST SICHERT:
  1. ein Buendel kostet EINEN Systemaufruf, nicht N,
  2. die Reihenfolge bleibt die Ankunftsreihenfolge,
  3. der Rest hinter einer gefundenen Aktion geht NICHT verloren,
  4. ein Loslassen im Buendel raeumt self.held, auch wenn die
     zurueckgegebene Aktion dahinter steht,
  5. der aufgehobene Rest wird VOR einer faelligen Wiederholung
     angesehen,
  6. flush() leert ihn mit,
  7. und im Quelltext steht kein Einzel-Lesen mehr.

Ausfuehren:
    python3 tools/test_eingabe_buendel.py
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
KEY_UP, KEY_DOWN = FI.KEY_UP, FI.KEY_DOWN
EV_MSC, EV_SYN = 0x04, 0x00


def ev(etype, code, value):
    """Ein rohes evdev-Ereignis, genau wie der Kernel es liefert."""
    return struct.pack(FI.EVENT_FMT, 0, 0, etype, code, value)


class GeraeteAttrappe:
    """Nur die Felder, die _translate() anfasst."""
    def __init__(self):
        self.path = "/dev/input/event-test"
        self.name = "Attrappe"
        self.is_kbd = True
        self.fd = 4242
        self.axis = {}


def manager(strom):
    """Ein InputManager, dessen Geraet genau diesen Strom liefert.

    DER ZUSTAND WIRD HERGESTELLT, NICHT UMGANGEN: gelesen wird ueber
    os.read und select.select wie im Betrieb, nur die Quelle ist eine
    Attrappe. Gezaehlt wird dabei, wie oft gelesen wurde - das ist die
    Zahl, um die es in diesem Build geht."""
    inp = FI.InputManager.__new__(FI.InputManager)
    dev = GeraeteAttrappe()
    inp.devices = {dev.path: dev}
    inp.held = None
    inp.last_scan = 1e18          # nie rescannen
    inp._zeichenzeit = {}
    inp._zeichenproben = {}
    inp._ereignis_rest = FI.deque()
    inp.seiten_aktionen = set()
    inp.eingabe_zeit = 0.0
    inp._select_down = {}
    inp._select_kombiniert = False
    inp._last_repeat_time = 0.0
    inp._last_repeat_act = None
    inp._last_repeat_iv = 0.0
    zaehler = {"read": 0, "select": 0}
    puffer = {"daten": b"".join(strom)}

    def _read(fd, n):
        zaehler["read"] += 1
        d = puffer["daten"][:n]
        puffer["daten"] = puffer["daten"][len(d):]
        if not d:
            raise BlockingIOError("leer")
        return d

    def _select(rl, wl, xl, t):
        zaehler["select"] += 1
        return ([dev.fd] if puffer["daten"] else []), [], []

    return inp, dev, zaehler, puffer, _read, _select


def lauf(strom, rufe=1):
    """rufe-mal read_action(timeout=0.5) und die Ergebnisse sammeln."""
    inp, dev, zaehler, puffer, _read, _select = manager(strom)
    _echt_read, _echt_select = os.read, FI.select.select
    raus = []
    try:
        os.read = _read
        FI.select.select = _select
        FI.os.read = _read
        for _ in range(rufe):
            raus.append(inp.read_action(timeout=0.5))
    finally:
        os.read = _echt_read
        FI.os.read = _echt_read
        FI.select.select = _echt_select
    return inp, raus, zaehler, puffer


# ---------------------------------------------------------------------------
print("Test 1: ein Buendel kostet EINEN Systemaufruf")
# ---------------------------------------------------------------------------
# Elf Ereignisse, von denen nur das letzte eine Aktion ist - genau die
# Form, die eine gehaltene Taste und ein schwatzendes Pad erzeugen.
STROM = ([ev(EV_MSC, 4, 1), ev(EV_SYN, 0, 0)] * 5
         + [ev(EV_KEY, KEY_DOWN, 1)])
inp, raus, zaehler, puffer = lauf(STROM)
check("die Aktion kommt an", raus[0] == "down", "%r" % (raus,))
check("und zwar mit EINEM os.read", zaehler["read"] == 1,
      "%d Aufrufe fuer %d Ereignisse - vor Build 306 waren es %d"
      % (zaehler["read"], len(STROM), len(STROM)))

# ---------------------------------------------------------------------------
print()
print("Test 2: der Rest hinter der Aktion geht nicht verloren")
# ---------------------------------------------------------------------------
# DIE WICHTIGSTE PRUEFUNG. Im Buendel steht ERST der Tastendruck und
# DANN das Loslassen. Wer beim Tastendruck zurueckkehrt und den Rest
# wegwirft, laesst die Taste fuer immer gedrueckt - und das ist
# wortgleich der Fehler aus Build 276: "wenn ich nach unten gedrueckt
# halte und dann nach 2-3 Sekunden loslasse, scrollt er von alleine
# weiter".
STROM2 = [ev(EV_KEY, KEY_DOWN, 1),
          ev(EV_MSC, 4, 1),
          ev(EV_KEY, KEY_DOWN, 0),      # das Loslassen, HINTER der Aktion
          ev(EV_SYN, 0, 0)]
inp, raus, zaehler, puffer = lauf(STROM2, rufe=1)
check("der Tastendruck kommt zurueck", raus[0] == "down", "%r" % (raus,))
check("und das Loslassen liegt noch im Puffer",
      len(inp._ereignis_rest) == 3,
      "%d Ereignisse aufgehoben - weggeworfen waere der Fehler aus "
      "Build 276" % len(inp._ereignis_rest))
check("die Taste gilt noch als gehalten", inp.held is not None,
      "das Loslassen ist noch nicht abgearbeitet - das ist richtig, "
      "es steht ja hinten im Buendel")

# ---------------------------------------------------------------------------
print()
print("Test 3: der zweite Aufruf raeumt das Loslassen ab")
# ---------------------------------------------------------------------------
# UND ZWAR OHNE VORHER ZU LESEN: der Rest ist aelter als alles, was
# jetzt ankommen koennte.
#
# GEFORDERT IST NICHT "kein select()", und die erste Fassung dieses
# Tests hat genau das verlangt und war zu Recht rot. In diesem Buendel
# stehen nur EV_MSC, das Loslassen und EV_SYN - keine Aktion. Also
# muss read_action() danach weitersuchen, und dafuer gehoert ein
# select() hin. Die Zusage lautet: der Puffer wird abgearbeitet, BEVOR
# ein neues Ereignis geholt wird, und das Loslassen raeumt self.held,
# bevor eine Wiederholung geprueft wird.
_echt_read, _echt_select = os.read, FI.select.select
_gelesen = []
try:
    def _nicht_lesen(fd, n):
        _gelesen.append(n)
        raise BlockingIOError("im Test gibt es nichts mehr")
    os.read = FI.os.read = _nicht_lesen
    # Das echte select() kennt unsere erfundene Geraetenummer nicht
    # ("filedescriptor out of range") - also auch hier eine Attrappe,
    # die sagt: es liegt nichts an.
    FI.select.select = lambda *a: ([], [], [])
    _zweite = inp.read_action(timeout=0.0)
finally:
    os.read = FI.os.read = _echt_read
    FI.select.select = _echt_select
check("der Puffer wird abgearbeitet, ohne vorher zu lesen",
      not _gelesen,
      "%d Leseversuche - vor dem Puffer darf keiner stehen"
      % len(_gelesen))
check("danach gilt die Taste als losgelassen", inp.held is None,
      "self.held = %r" % (inp.held,))
check("und der Puffer ist leer", not inp._ereignis_rest,
      "%d uebrig" % len(inp._ereignis_rest))

# ---------------------------------------------------------------------------
print()
print("Test 4: die Reihenfolge ist die Ankunftsreihenfolge")
# ---------------------------------------------------------------------------
# Zwei Aktionen in EINEM Buendel: runter, dann hoch. Sie muessen in
# dieser Reihenfolge herauskommen - beim Richtungswechsel haengt genau
# daran, ob die neue Richtung gilt oder die alte nachzieht.
STROM4 = [ev(EV_KEY, KEY_DOWN, 1), ev(EV_KEY, KEY_DOWN, 0),
          ev(EV_KEY, KEY_UP, 1), ev(EV_KEY, KEY_UP, 0)]
inp, raus, zaehler, puffer = lauf(STROM4, rufe=2)
check("erst runter, dann hoch", raus == ["down", "up"], "%r" % (raus,))
check("und alles aus einem einzigen Lesevorgang", zaehler["read"] == 1,
      "%d Aufrufe" % zaehler["read"])

# ---------------------------------------------------------------------------
print()
print("Test 5: flush() leert den aufgehobenen Rest mit")
# ---------------------------------------------------------------------------
# Ein Buendelrest, der ein flush() ueberlebt, waere ein Tastendruck
# aus der Zeit VOR dem Spiel, der danach ploetzlich wirkt.
inp, raus, zaehler, puffer = lauf(STROM2, rufe=1)
check("vor flush liegt etwas im Puffer", len(inp._ereignis_rest) > 0,
      "%d" % len(inp._ereignis_rest))
inp.devices = {}            # flush() laeuft dann ueber keine Geraete
inp.flush()
check("nach flush ist er leer", not inp._ereignis_rest,
      "%d uebrig" % len(inp._ereignis_rest))

# ---------------------------------------------------------------------------
print()
print("Test 6: am Quelltext")
# ---------------------------------------------------------------------------
_src = open(os.path.join(_REPO, "frontend", "fe", "input.py"),
            encoding="utf-8").read()
_ra = nur_code(koerper(_src, "read_action"))
check("read_action liest buendelweise",
      "EREIGNIS_BUENDEL" in _ra,
      "os.read(fd, EVENT_SIZE * EREIGNIS_BUENDEL)")
check("und nicht mehr genau ein Ereignis",
      "os.read(fd, EVENT_SIZE)" not in _ra,
      "das war der Zustand bis Build 305")
check("der Puffer wird VOR dem Warten angesehen",
      _ra.index("_aus_rest()") < _ra.index("select.select"),
      "sonst verdreht er die Reihenfolge")
_fl = nur_code(koerper(_src, "flush"))
check("flush() leert ihn", "_ereignis_rest" in _fl)
_ar = nur_code(koerper(_src, "_aus_rest"))
check("_aus_rest() haelt den Rest, statt ihn zu verwerfen",
      "popleft()" in _ar and "clear" not in _ar,
      "verwerfen waere der Fehler aus Build 276")

# ---------------------------------------------------------------------------
print()
if fails:
    print("FEHLGESCHLAGEN (%d):" % len(fails))
    for f in fails:
        print("  - %s" % f)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
