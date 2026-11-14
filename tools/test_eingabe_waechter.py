#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Der Eingabe-Waechter und die Achsen-Maske (Build 322).

DER ANLASS ist sein Log vom 14.11. - der Schluss aus Build 321 hat sich
bestaetigt, sechsmal in 67 Sekunden:

    EINGABE: der Kernel hat ungelesene Ereignisse von /dev/input/event3
    'Nintendo Co., Ltd. Pro Controller' verworfen (SYN_DROPPED, 1. Mal,
    8.9 s nach dem Start)

Und die Wartezeiten daneben erklaert keine einzelne Leerlauf-Arbeit
("down lag 742 ms ... laengste Leerlauf-Arbeit davor: Warmlauf 55 ms").

GEPRUEFT WIRD UEBER ECHTE DATEIGRIFFE (Pipes), mit einem echten Faden:

  1. Haelt die Hauptschleife an, holt der Waechter das Pad in den
     Puffer - GEGENPROBE ohne Waechter: alles bleibt im Pipe liegen.
  2. Er wertet nichts aus (held, axis_state unberuehrt), und
     read_action() liefert danach in der richtigen Reihenfolge - auch
     wenn ein Teil vom Waechter und ein Teil von read_action() selbst
     gelesen wurde.
  3. Solange ein Lesender die Sperre haelt (read_action, wait_game_exit
     waehrend eines Spiels), liest der Waechter NICHT.
  4. Liest die Hauptschleife regelmaessig, tut er nichts.
  5. Alle sieben Lesewege laufen unter der Sperre; ohne Sperre
     (InputManager ueber __new__) laufen sie wie bisher.
  6. Starten, stoppen, und nur aus run() - nicht im Bench.
  7. EVIOCSMASK: die Nummer aus der Formel des Kernels, die Bitmaske
     mit genau den genutzten Achsen, und ein Kernel ohne Unterstuetzung
     aendert nichts.

Ausfuehren:
    python3 tools/test_eingabe_waechter.py
"""
import ctypes
import os
import select
import struct
import sys
import threading
import time

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
sys.path.insert(0, os.path.join(_REPO, "frontend"))
sys.path.insert(0, _HIER)

import fe.input as FI                                    # noqa: E402
from _quelle import koerper, nur_code                    # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


print(__doc__.strip().split("\n")[0])
print()

EV_SYN, EV_KEY, EV_ABS = FI.EV_SYN, FI.EV_KEY, FI.EV_ABS
HAT_Y = FI.ABS_HAT0Y


def roh(etype, code, value):
    return struct.pack(FI.EVENT_FMT, 0, 0, etype, code, value)


class PadAttrappe:
    def __init__(self):
        self.lesen, self.schreiben = os.pipe()
        self.fd = self.lesen
        self.path = "/dev/input/event-pad"
        self.name = "Pad-Attrappe"
        self.is_kbd = False
        self.axis = {HAT_Y: (-1, 1)}
        self.axis_state = {HAT_Y: 0}
        self.uhr_monoton = False
        self.nach_drop = False

    def senden(self, *ereignisse):
        os.write(self.schreiben, b"".join(ereignisse))

    def liegt_noch(self):
        return bool(select.select([self.fd], [], [], 0)[0])

    def zu(self):
        os.close(self.lesen)
        os.close(self.schreiben)


def manager(pad, mit_sperre=True):
    inp = FI.InputManager.__new__(FI.InputManager)
    inp.devices = {pad.path: pad}
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
    if mit_sperre:
        inp._lese_lock = threading.RLock()
        inp._zuletzt_gelesen = time.monotonic()
        inp._wache_faden = None
        inp._wache_ende = threading.Event()
        inp.wache_laeufe = 0
        inp.wache_geholt = 0
    return inp


def druck(v):
    return (roh(EV_ABS, HAT_Y, v), roh(EV_SYN, 0, 0))


# ---------------------------------------------------------------------------
print("Test 1: haelt die Hauptschleife an, holt der Waechter ab")
# ---------------------------------------------------------------------------
for mit_waechter in (False, True):
    pad = PadAttrappe()
    inp = manager(pad)
    try:
        if mit_waechter:
            inp.wache_starten(takt=0.02)
        inp._zuletzt_gelesen = time.monotonic() - 1.0
        pad.senden(*(druck(1) + druck(0) + druck(-1) + druck(0)))
        time.sleep(0.3)               # "die Hauptschleife zeichnet"
        im_puffer = len(inp._ereignis_rest)
        noch_da = pad.liegt_noch()
        if mit_waechter:
            check("mit Waechter: alles im eigenen Puffer",
                  im_puffer == 8 and not noch_da,
                  "%d im Puffer, Pipe %s" % (im_puffer,
                                              "voll" if noch_da else "leer"))
            check("und mitgezaehlt", inp.wache_geholt == 8
                  and inp.wache_laeufe >= 1,
                  "%d / %d" % (inp.wache_geholt, inp.wache_laeufe))
            check("ausgewertet hat er nichts",
                  inp.held is None and pad.axis_state[HAT_Y] == 0)
            raus = [a for a in (inp.read_action(timeout=0.05)
                                for _ in range(4)) if a]
            check("read_action liefert danach in der Reihenfolge",
                  raus == ["down", "up"], repr(raus))
        else:
            check("GEGENPROBE ohne Waechter: alles liegt noch im Pipe",
                  im_puffer == 0 and noch_da, im_puffer)
    finally:
        inp.wache_stoppen()
        pad.zu()

# ---------------------------------------------------------------------------
print()
print("Test 2: ein Teil vom Waechter, ein Teil von read_action")
# ---------------------------------------------------------------------------
pad = PadAttrappe()
inp = manager(pad)
try:
    inp.wache_starten(takt=0.02)
    inp._zuletzt_gelesen = time.monotonic() - 1.0
    pad.senden(*druck(1))          # runter ...
    time.sleep(0.15)                # ... vom Waechter geholt
    vom_waechter = len(inp._ereignis_rest)
    inp.wache_stoppen()
    pad.senden(*druck(0))           # loslassen ...
    pad.senden(*druck(-1))          # ... hoch - das liest read_action
    raus = [a for a in (inp.read_action(timeout=0.05) for _ in range(4))
            if a]
    check("der Waechter hatte den ersten Druck", vom_waechter == 2,
          vom_waechter)
    check("und die Reihenfolge stimmt trotzdem", raus == ["down", "up"],
          repr(raus))
finally:
    inp.wache_stoppen()
    pad.zu()

# ---------------------------------------------------------------------------
print()
print("Test 3: haelt jemand die Sperre, liest der Waechter nicht")
# ---------------------------------------------------------------------------
pad = PadAttrappe()
inp = manager(pad)
try:
    inp.wache_starten(takt=0.02)
    inp._zuletzt_gelesen = time.monotonic() - 1.0
    frei = threading.Event()
    gestartet = threading.Event()

    def spiel_laeuft():
        # So haelt wait_game_exit() die Sperre - waehrend eines Spiels.
        with inp._lese_lock:
            gestartet.set()
            frei.wait(1.0)

    t = threading.Thread(target=spiel_laeuft)
    t.start()
    gestartet.wait(1.0)
    pad.senden(*druck(1))
    time.sleep(0.25)
    waehrend = len(inp._ereignis_rest)
    noch_da = pad.liegt_noch()
    frei.set()
    t.join()
    check("waehrend die Sperre gehalten wird: nichts geholt",
          waehrend == 0 and noch_da, waehrend)
    time.sleep(0.25)
    check("danach holt er ab", len(inp._ereignis_rest) == 2
          and not pad.liegt_noch(), len(inp._ereignis_rest))
finally:
    inp.wache_stoppen()
    pad.zu()
check("wait_game_exit laeuft unter der Sperre",
      hasattr(FI.InputManager.wait_game_exit, "__wrapped__"))

# ---------------------------------------------------------------------------
print()
print("Test 4: liest die Hauptschleife regelmaessig, tut er nichts")
# ---------------------------------------------------------------------------
pad = PadAttrappe()
inp = manager(pad)
try:
    inp.wache_starten(takt=0.05)
    ende = time.monotonic() + 0.5
    while time.monotonic() < ende:
        pad.senden(roh(EV_ABS, HAT_Y, 0), roh(EV_SYN, 0, 0))
        inp.read_action(timeout=0.01)
    check("kein einziges Mal abgeholt", inp.wache_laeufe == 0,
          inp.wache_laeufe)
finally:
    inp.wache_stoppen()
    pad.zu()

# ---------------------------------------------------------------------------
print()
print("Test 5: alle Lesewege unter der Sperre")
# ---------------------------------------------------------------------------
for name in ("read_action", "abholen", "eingabe_anstehend", "rescan",
             "read_raw_key", "wait_game_exit", "flush"):
    fn = getattr(FI.InputManager, name)
    check("%s laeuft unter der Sperre" % name, hasattr(fn, "__wrapped__")
          and fn.__name__ == name)
pad = PadAttrappe()
inp = manager(pad, mit_sperre=False)
try:
    pad.senden(*druck(1))
    check("ohne Sperre (ueber __new__ gebaut) wie bisher",
          inp.read_action(timeout=0.05) == "down")
finally:
    pad.zu()

# ---------------------------------------------------------------------------
print()
print("Test 6: starten, stoppen - und nur aus run()")
# ---------------------------------------------------------------------------
pad = PadAttrappe()
inp = manager(pad)
try:
    inp.wache_starten(takt=0.05)
    faden = inp._wache_faden
    inp.wache_starten(takt=0.05)
    check("ein zweiter Start startet keinen zweiten Faden",
          inp._wache_faden is faden)
    inp.wache_stoppen()
    check("gestoppt ist er weg", inp._wache_faden is None
          and not faden.is_alive())
finally:
    pad.zu()
_quelle_fm = open(os.path.join(_REPO, "frontend", "frontend.py"),
                  encoding="utf-8").read()
_run = nur_code(koerper(_quelle_fm, "run", "Frontend"))
check("run() startet ihn vor der Schleife",
      "self.inp.wache_starten()" in _run
      and _run.index("self.inp.wache_starten()")
      < _run.index("while True:"))
check("und stoppt ihn im finally", "self.inp.wache_stoppen()"
      in _run.split("finally:")[-1] or "self.inp.wache_stoppen()"
      in _run[_run.rindex("finally:"):])
_init = nur_code(koerper(_quelle_fm, "__init__", "Frontend"))
check("der Konstruktor startet ihn NICHT (der Bench liest selbst)",
      "wache_starten" not in _init)

# ---------------------------------------------------------------------------
print()
print("Test 7: EVIOCSMASK - nur die genutzten Achsen")
# ---------------------------------------------------------------------------
check("EVIOCSMASK = _IOW('E', 0x93, 16 Byte)",
      FI.EVIOCSMASK == (1 << 30) | (16 << 16) | (ord("E") << 8) | 0x93,
      hex(FI.EVIOCSMASK))
gesehen = {}
_echt_ioctl = FI.fcntl.ioctl


def _fang(fd, nr, arg):
    if nr == FI.EVIOCSMASK:
        typ, groesse, adresse = struct.unpack("IIQ", arg)
        gesehen["typ"], gesehen["groesse"] = typ, groesse
        gesehen["bits"] = ctypes.string_at(adresse, groesse)
        return 0
    return _echt_ioctl(fd, nr, arg)


FI.fcntl.ioctl = _fang
try:
    achsen = {FI.ABS_X: (0, 255), FI.ABS_Y: (0, 255), FI.ABS_HAT0X: (-1, 1),
              FI.ABS_HAT0Y: (-1, 1), FI.ABS_Z: (0, 255),
              FI.ABS_RZ: (0, 255)}
    ok = FI._achsen_maske_setzen(99, achsen)
finally:
    FI.fcntl.ioctl = _echt_ioctl
bits = gesehen.get("bits", b"")
erlaubt = {i * 8 + b for i, byte in enumerate(bits) for b in range(8)
           if byte & (1 << b)}
check("angenommen", ok is True)
check("fuer EV_ABS, 8 Byte (64 Achsen)",
      gesehen.get("typ") == FI.EV_ABS and gesehen.get("groesse") == 8,
      gesehen.get("typ"))
check("genau die sechs genutzten Achsen",
      erlaubt == {0, 1, 2, 5, 16, 17}, sorted(erlaubt))
check("RX (3) und RY (4) - der rechte Stick - sind NICHT dabei",
      3 not in erlaubt and 4 not in erlaubt)
lesen, schreiben = os.pipe()
try:
    check("ein Dateigriff ohne Unterstuetzung: False, kein Fehler",
          FI._achsen_maske_setzen(lesen, achsen) is False)
finally:
    os.close(lesen)
    os.close(schreiben)
_dev = koerper(open(os.path.join(_REPO, "frontend", "fe", "input.py"),
                    encoding="utf-8").read(), "__init__", "Device")
check("Device setzt die Maske mit seinen eigenen Achsen",
      "_achsen_maske_setzen(self.fd, self.axis)" in _dev)

print()
if fails:
    print("ROT: %d Pruefung(en) fehlgeschlagen:" % len(fails))
    for f_ in fails:
        print("   - " + f_)
    sys.exit(1)
print("ALLES GRUEN")
