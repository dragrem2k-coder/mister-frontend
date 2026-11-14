#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Wenn der Kernel Ereignisse wegwirft: SYN_DROPPED, Abholen, Wartezeit (Build 321).

DER ANLASS, in seinen Worten: "wenn ich denn mister anmache und das
frontend startet hab ich das gefuehl als wenn die ersten 10 sekunden das
joypad manchmal wie eingefroren ist ! und eingaben uebersprungen oder
nicht wahrgenommen werden! danach wirds dann besser".

Jedes geoeffnete Eingabegeraet hat im Kernel eine Warteschlange fester
Groesse. Liest eine Weile niemand, laeuft sie ueber, und der Kernel
wirft ALLES Ungelesene weg und legt ein SYN_DROPPED hinein. Bis Build
320 wurde das wie ein gewoehnliches EV_SYN uebergangen.

GEPRUEFT WIRD UEBER ECHTE DATEIGRIFFE: das "Geraet" ist ein Pipe, in den
die Ereignisse genau so geschrieben werden, wie der Kernel sie liefert.
select() und os.read() laufen wie im Betrieb.

  1. Das LOSLASSEN einer Richtung geht verloren: ohne Abgleich ergibt
     der naechste Druck keine Aktion ("eingefroren") - GEGENPROBE mit
     abgeschaltetem Abgleich -, mit Abgleich wieder eine.
  2. Zwischen SYN_DROPPED und SYN_REPORT wird alles verworfen.
  3. Eine gehaltene Taste (Wiederholung), deren Loslassen verloren
     ging, laeuft nicht weiter - eine noch gedrueckte schon.
  4. Die Select-Taste wird zurueckgesetzt, wenn sie nicht mehr gedrueckt
     ist.
  5. Gezaehlt und gemeldet wird jedes SYN_DROPPED.
  6. abholen() holt alles in den eigenen Puffer, ohne auszuwerten, und
     read_action() liefert danach in derselben Reihenfolge.
  7. eingabe_anstehend(): Rauschen eines Sticks zaehlt NICHT, eine
     Taste, eine Richtungsaenderung, SYN_DROPPED und eine vorgelegte
     Aktion schon - und held/axis_state bleiben dabei unberuehrt.
  8. Die Wartezeit beim Kernel aus dem Zeitstempel - nur mit monotoner
     Uhr, sonst "jetzt".
  9. Die ioctl-Nummern, aus der Formel des Kernels nachgerechnet, und
     _richtung_aus_wert() an den Schwellen.

Ausfuehren:
    python3 tools/test_eingabe_ueberlauf.py
"""
import os
import struct
import sys
import time

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
sys.path.insert(0, os.path.join(_REPO, "frontend"))

import fe.input as FI                                    # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


print(__doc__.strip().split("\n")[0])
print()

EV_SYN, EV_KEY, EV_ABS = FI.EV_SYN, FI.EV_KEY, FI.EV_ABS
SYN_REPORT, SYN_DROPPED = FI.SYN_REPORT, FI.SYN_DROPPED
HAT_Y, ABS_X = FI.ABS_HAT0Y, FI.ABS_X


def roh(etype, code, value, ts=0.0):
    sec = int(ts)
    usec = int(round((ts - sec) * 1000000))
    return struct.pack(FI.EVENT_FMT, sec, usec, etype, code, value)


class PadAttrappe:
    """Ein Pad mit Steuerkreuz als Achse (HAT0Y) und Stick (ABS_X).

    tasten_jetzt()/achse_jetzt() antworten mit dem, was der Test als
    "wirklichen Zustand" vorgibt - genau das, was EVIOCGKEY/EVIOCGABS
    auf dem Geraet liefern wuerden."""

    def __init__(self):
        self.lesen, self.schreiben = os.pipe()
        self.fd = self.lesen
        self.path = "/dev/input/event-pad"
        self.name = "Pad-Attrappe"
        self.is_kbd = False
        self.axis = {HAT_Y: (-1, 1), ABS_X: (0, 255)}
        self.axis_state = {HAT_Y: 0, ABS_X: 0}
        self.uhr_monoton = False
        self.nach_drop = False
        self.verworfen = 0
        self.tasten = set()
        self.achsen = {HAT_Y: 0, ABS_X: 128}

    def tasten_jetzt(self):
        return set(self.tasten)

    def achse_jetzt(self, axis):
        return self.achsen[axis]

    def senden(self, *ereignisse):
        os.write(self.schreiben, b"".join(ereignisse))

    def zu(self):
        os.close(self.lesen)
        os.close(self.schreiben)


def manager(*geraete):
    inp = FI.InputManager.__new__(FI.InputManager)
    inp.devices = {d.path: d for d in geraete}
    inp.held = None
    inp.last_scan = 1e18
    inp._last_input_mtime = None
    inp._zeichenzeit = {}
    inp._zeichenproben = {}
    inp._ereignis_rest = FI.deque()
    inp._vorgelegt = None
    inp.seiten_aktionen = set(FI.PAGE_ACTIONS)
    inp._select_down = {}
    inp._select_kombiniert = False
    inp._last_repeat_time = 0.0
    inp._last_repeat_act = None
    inp._last_repeat_iv = FI.REPEAT_INTERVAL
    inp._t_start = time.monotonic()
    inp.syn_dropped = {}
    inp.rescan = lambda force=False: None
    return inp


def lies(inp, n=1):
    raus = []
    for _ in range(n):
        raus.append(inp.read_action(timeout=0.05))
    return raus


DROP = (roh(EV_SYN, SYN_DROPPED, 0),)
REPORT = (roh(EV_SYN, SYN_REPORT, 0),)

# ---------------------------------------------------------------------------
print("Test 1: das Loslassen einer Richtung geht verloren")
# ---------------------------------------------------------------------------


def szenario_loslassen(mit_abgleich):
    pad = PadAttrappe()
    inp = manager(pad)
    if not mit_abgleich:
        inp._neu_abgleichen = lambda dev: None
    try:
        pad.senden(roh(EV_ABS, HAT_Y, 1), *REPORT)
        erstes = lies(inp)[0]
        # Das Loslassen kommt nie an - der Kernel hat es weggeworfen.
        # In Wirklichkeit steht das Steuerkreuz jetzt in der Mitte.
        pad.achsen[HAT_Y] = 0
        pad.senden(*(DROP + REPORT))
        zwischen = lies(inp)[0]
        held_danach = inp.held
        # Und jetzt drueckt er wieder runter.
        pad.senden(roh(EV_ABS, HAT_Y, 1), *REPORT)
        zweites = lies(inp)[0]
        return erstes, zwischen, held_danach, zweites, pad, inp
    finally:
        pad.zu()


e1, zw, h, e2, pad, inp = szenario_loslassen(False)
check("Gegenprobe ohne Abgleich: der zweite Druck ergibt KEINE Aktion",
      e1 == "down" and e2 is None,
      "erst %r, dann %r - genau das 'eingefroren'" % (e1, e2))
e1, zw, h, e2, pad, inp = szenario_loslassen(True)
check("mit Abgleich: der erste Druck wirkt", e1 == "down", repr(e1))
check("SYN_DROPPED selbst erzeugt keine Aktion", zw is None, repr(zw))
check("die Wiederholung ist nach dem Abgleich beendet", h is None,
      repr(h))
check("und der zweite Druck wirkt wieder", e2 == "down", repr(e2))

# ---------------------------------------------------------------------------
print()
print("Test 2: zwischen SYN_DROPPED und SYN_REPORT wird alles verworfen")
# ---------------------------------------------------------------------------
pad = PadAttrappe()
inp = manager(pad)
try:
    pad.senden(*DROP)
    pad.senden(roh(EV_KEY, FI.KEY_DOWN, 1), roh(EV_ABS, HAT_Y, -1))
    pad.senden(*REPORT)
    pad.senden(roh(EV_KEY, FI.KEY_UP, 1), *REPORT)
    raus = [a for a in lies(inp, 3) if a]
    check("nur der Druck NACH dem SYN_REPORT zaehlt", raus == ["up"],
          repr(raus))
    check("und das Geraet ist danach wieder verlaesslich",
          pad.nach_drop is False)
finally:
    pad.zu()

# ---------------------------------------------------------------------------
print()
print("Test 3: eine gehaltene Taste nach dem Ueberlauf")
# ---------------------------------------------------------------------------
for noch_gedrueckt in (False, True):
    pad = PadAttrappe()
    pad.is_kbd = True
    inp = manager(pad)
    try:
        pad.senden(roh(EV_KEY, FI.KEY_DOWN, 1), *REPORT)
        a = lies(inp)[0]
        held_vorher = inp.held is not None
        pad.tasten = {FI.KEY_DOWN} if noch_gedrueckt else set()
        pad.senden(*(DROP + REPORT))
        lies(inp)
        if noch_gedrueckt:
            check("noch gedrueckt: die Wiederholung bleibt",
                  a == "down" and held_vorher and inp.held is not None,
                  repr(inp.held))
        else:
            check("losgelassen: die Wiederholung endet",
                  a == "down" and held_vorher and inp.held is None,
                  repr(inp.held))
    finally:
        pad.zu()

# ---------------------------------------------------------------------------
print()
print("Test 4: die Select-Taste")
# ---------------------------------------------------------------------------
sel = [c for c, act in FI.KEYMAP.items() if act == "select" and c >= 0]
check("es gibt eine Select-Taste in der Belegung", bool(sel), repr(sel))
if sel:
    pad = PadAttrappe()
    inp = manager(pad)
    try:
        pad.senden(roh(EV_KEY, sel[0], 1), *REPORT)
        lies(inp)
        check("Select ist als gehalten vermerkt",
              pad.path in inp._select_down)
        pad.tasten = set()
        pad.senden(*(DROP + REPORT))
        lies(inp)
        check("nach dem Ueberlauf nicht mehr - sie ist ja los",
              pad.path not in inp._select_down)
    finally:
        pad.zu()

# ---------------------------------------------------------------------------
print()
print("Test 5: gezaehlt und gemeldet")
# ---------------------------------------------------------------------------
gemeldet = []
_echt_log = FI.LOG
FI.LOG = lambda m: gemeldet.append(m)
pad = PadAttrappe()
inp = manager(pad)
try:
    pad.senden(*(DROP + REPORT + DROP + REPORT))
    lies(inp, 2)
finally:
    FI.LOG = _echt_log
    pad.zu()
check("je Geraet gezaehlt", inp.syn_dropped.get(pad.path) == 2,
      repr(inp.syn_dropped))
check("auch am Geraet", pad.verworfen == 2, pad.verworfen)
check("und im Log, mit Sekunden seit dem Start",
      len(gemeldet) == 2 and "SYN_DROPPED" in gemeldet[0]
      and "nach dem Start" in gemeldet[0], gemeldet[:1])

# ---------------------------------------------------------------------------
print()
print("Test 6: abholen() - in den eigenen Puffer, ohne auszuwerten")
# ---------------------------------------------------------------------------
pad = PadAttrappe()
inp = manager(pad)
try:
    strom = []
    for v in (1, 0, -1, 0):
        strom += [roh(EV_ABS, HAT_Y, v), roh(EV_SYN, SYN_REPORT, 0)]
    pad.senden(*strom)
    n = inp.abholen()
    check("alle acht Ereignisse abgeholt", n == 8, n)
    check("im eigenen Puffer", len(inp._ereignis_rest) == 8,
          len(inp._ereignis_rest))
    import select as _sel
    check("und im Kernel (hier: im Pipe) liegt nichts mehr",
          not _sel.select([pad.fd], [], [], 0)[0])
    check("ausgewertet wurde nichts", inp.held is None
          and pad.axis_state[HAT_Y] == 0)
    raus = [a for a in lies(inp, 4) if a]
    check("read_action liefert danach in derselben Reihenfolge",
          raus == ["down", "up"], repr(raus))
finally:
    pad.zu()
leer = manager()
check("ohne Geraet: 0 und kein Fehler", leer.abholen() == 0)

# ---------------------------------------------------------------------------
print()
print("Test 7: eingabe_anstehend()")
# ---------------------------------------------------------------------------


def anstehend(*ereignisse, vorgelegt=None, vorher=None):
    pad = PadAttrappe()
    inp = manager(pad)
    if vorher:
        vorher(pad, inp)
    inp._vorgelegt = vorgelegt
    try:
        if ereignisse:
            pad.senden(*ereignisse)
        held0, st0 = inp.held, dict(pad.axis_state)
        r = inp.eingabe_anstehend()
        return r, inp, pad, (inp.held == held0 and pad.axis_state == st0)
    finally:
        pad.zu()


rauschen = []
for v in (120, 131, 126, 135, 122, 129):
    rauschen += [roh(EV_ABS, ABS_X, v), roh(EV_SYN, SYN_REPORT, 0)]
r, inp, pad, ruhig = anstehend(*rauschen)
check("Rauschen um die Mitte zaehlt NICHT", r is False)
check("es bleibt im Puffer fuer read_action",
      len(inp._ereignis_rest) == len(rauschen), len(inp._ereignis_rest))
check("held und axis_state unberuehrt", ruhig)
r, inp, pad, ruhig = anstehend(*(rauschen + [roh(EV_KEY, FI.KEY_ENTER, 1)]))
check("eine Taste hinter dem Rauschen zaehlt", r is True)
check("und auch dabei wird nichts ausgewertet", ruhig)
r, *_ = anstehend(roh(EV_ABS, ABS_X, 250))
check("der Stick ueber die Schwelle zaehlt", r is True)
r, *_ = anstehend(roh(EV_ABS, ABS_X, 250),
                  vorher=lambda p, i: p.axis_state.__setitem__(ABS_X, 1))
check("dieselbe Stellung wie axis_state zaehlt nicht", r is False)
r, *_ = anstehend(roh(EV_ABS, ABS_X, 128),
                  vorher=lambda p, i: p.axis_state.__setitem__(ABS_X, 1))
check("das LOSLASSEN des Sticks zaehlt", r is True)
r, *_ = anstehend(*DROP)
check("ein SYN_DROPPED zaehlt", r is True)
r, *_ = anstehend(vorgelegt="down")
check("eine vorgelegte Aktion zaehlt", r is True)
r, *_ = anstehend(roh(EV_KEY, FI.KEY_DOWN, 2))
check("die Tastatur-Wiederholung (value 2) zaehlt nicht", r is False)

# ---------------------------------------------------------------------------
print()
print("Test 8: wie lange lag der Druck beim Kernel?")
# ---------------------------------------------------------------------------
for monoton, ts_fn, erwartet in (
        (True, lambda: time.monotonic() - 0.4, "rund 400 ms"),
        (False, lambda: time.monotonic() - 0.4, "0 - keine monotone Uhr"),
        (True, lambda: 5.0, "0 - unplausibler Zeitstempel")):
    pad = PadAttrappe()
    pad.uhr_monoton = monoton
    inp = manager(pad)
    try:
        ts = ts_fn()
        pad.senden(roh(EV_KEY, FI.KEY_ENTER, 1, ts), roh(EV_SYN, 0, 0, ts))
        vor = time.monotonic()
        a = lies(inp)[0]
        nach = time.monotonic()
        w = inp.eingabe_wartezeit
        if erwartet.startswith("rund"):
            check("monoton: Wartezeit %s" % erwartet,
                  a == "ok" and 0.35 <= w <= 1.0, "%.3f s" % w)
            check("und eingabe_zeit ist der Zeitstempel des Kernels",
                  abs(inp.eingabe_zeit - ts) < 0.001,
                  "%.4f gegen %.4f" % (inp.eingabe_zeit, ts))
        else:
            check("Wartezeit %s" % erwartet, w == 0.0, "%.3f" % w)
            check("und eingabe_zeit ist 'jetzt'",
                  vor <= inp.eingabe_zeit <= nach)
    finally:
        pad.zu()

# ---------------------------------------------------------------------------
print()
print("Test 9: ioctl-Nummern und Schwellen")
# ---------------------------------------------------------------------------


def _ioc(richtung, typ, nr, groesse):
    return (richtung << 30) | (groesse << 16) | (ord(typ) << 8) | nr


check("EVIOCSCLOCKID = _IOW('E', 0xa0, int)",
      FI.EVIOCSCLOCKID == _ioc(1, "E", 0xa0, 4), hex(FI.EVIOCSCLOCKID))
check("EVIOCGKEY(96) = _IOR('E', 0x18, 96)",
      FI.EVIOCGKEY_96 == _ioc(2, "E", 0x18, 96), hex(FI.EVIOCGKEY_96))
check("EVIOCGABS wie in _absinfo (0x80184540 + Achse)",
      0x80184540 == _ioc(2, "E", 0x40, 24))
check("CLOCK_MONOTONIC = 1", FI.CLOCK_MONOTONIC == 1)
pad = PadAttrappe()
inp = manager(pad)
pad.axis[FI.ABS_Z] = (0, 255)
try:
    R = inp._richtung_aus_wert
    check("Steuerkreuz -1/0/1", [R(pad, HAT_Y, v) for v in (-1, 0, 1)]
          == [-1, 0, 1])
    check("Stick: unter 30 % links, ueber 70 % rechts",
          [R(pad, ABS_X, v) for v in (0, 76, 77, 128, 178, 179, 255)]
          == [-1, -1, 0, 0, 0, 1, 1],
          [R(pad, ABS_X, v) for v in (0, 76, 77, 128, 178, 179, 255)])
    check("Trigger: ueber der Haelfte gedrueckt",
          [R(pad, FI.ABS_Z, v) for v in (0, 127, 128, 255)] == [0, 0, 1, 1])
finally:
    pad.zu()
_q = open(os.path.join(_REPO, "frontend", "fe", "input.py"),
          encoding="utf-8").read()
check("Device stellt die Uhr um", "EVIOCSCLOCKID" in _q.split(
    "class Device")[1].split("class InputManager")[0])
# Vorher stand dieselbe Schwellenrechnung DREIMAL im Modul: in
# _translate() zweimal (Stick, Trigger) und in read_raw_key() (der
# Tastenbelegung) noch einmal. Jetzt nur noch in _richtung_aus_wert().
check("die Achsen-Schwellen stehen nur noch an EINER Stelle",
      _q.count("rel < 0.30") == 1 and _q.count("rel > 0.5") == 0
      and _q.count("/ span > 0.5") == 1,
      "%d / %d / %d" % (_q.count("rel < 0.30"), _q.count("rel > 0.5"),
                        _q.count("/ span > 0.5")))

print()
if fails:
    print("ROT: %d Pruefung(en) fehlgeschlagen:" % len(fails))
    for f_ in fails:
        print("   - " + f_)
    sys.exit(1)
print("ALLES GRUEN")
