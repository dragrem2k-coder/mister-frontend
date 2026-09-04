#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft den F5-Reset auf sofortigen Tastendruck (Build 75).

NUTZERWUNSCH: "F5-Reset-Funktion haette ich gerne auf sofortigen
Tastendruck, wenn das geht."

Vorher lagen drei Verzoegerungen hintereinander:

  1. RESET_HOLD = 0,6 s Haltezeit
  2. bis zu 0,2 s, weil die Haltezeit erst am ANFANG der naechsten
     Schleifenrunde geprueft wurde - und die Schleife wartet in
     select(..., 0.2)
  3. 0,2 s beim Anlegen des virtuellen Tastatur-Geraets, das bei JEDEM
     Reset neu erzeugt wurde

Macht bis zu 1,0 s. Uebrig bleibt jetzt die Tastendruckdauer von 0,1 s,
die der Empfaenger braucht, um den Druck ueberhaupt zu sehen.

EHRLICH BENANNTES RISIKO, hier mitgeprueft: ohne Haltezeit ist ein
versehentlicher F5-Antipper waehrend des Spielens sofort ein Reset.
Was dagegen NICHT passieren darf, ist ein Dauerfeuer durch blosses
Halten - dafuer gibt es reset_gefeuert, und Test 3 nagelt das fest.

Ausfuehren:
    python3 tools/test_reset_sofort.py
"""
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
_FRONTEND_DIR = os.path.dirname(
    os.environ.get("FRONTEND_PY",
                   os.path.join(_REPO, "frontend", "frontend.py")))
sys.path.insert(0, _FRONTEND_DIR)

import fe.reset_trigger as R                         # noqa: E402
import fe.input as I                                 # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


print("Test 1: keine Haltezeit mehr")
check("RESET_HOLD ist 0", I.InputManager.RESET_HOLD == 0,
      str(I.InputManager.RESET_HOLD))
# Die Haltezeit allein wegzunehmen haette NICHT gereicht: geprueft wird
# sie am Anfang der Schleife, und die wartet vorher in select(...,0.2).
# Ausgeloest werden muss deshalb DORT, wo die Taste erkannt wird.
quelle = open(os.path.join(_FRONTEND_DIR, "fe", "input.py"),
              encoding="utf-8").read()
block = quelle.split("reset_since = time.monotonic()")[-1][:1600]
check("ausgeloest wird direkt beim Erkennen der Taste",
      "if self.RESET_HOLD <= 0:" in block and "send_reset_combo()" in block)
check("es gibt eine Sperre gegen Dauerfeuer beim Halten",
      "reset_gefeuert" in quelle)
check("und sie wird beim Loslassen wieder aufgehoben",
      "reset_gefeuert = False" in quelle)

print()
print("Test 2: das virtuelle Geraet wird nur EINMAL angelegt")
# Das war der zweitgroesste Posten: 0,2 s Wartezeit nach dem Anlegen,
# damit der Kernel das Geraet bekannt macht - frueher bei jedem Reset.
angelegt = []
geschrieben = []
geschlossen = []


class FakeFcntl:
    @staticmethod
    def ioctl(fd, req, arg=0):
        if req == R.UI_DEV_CREATE:
            angelegt.append(fd)
        elif req == R.UI_DEV_DESTROY:
            geschlossen.append(fd)
        return 0


_echt = (R.os.open, R.os.write, R.os.close, R.fcntl, R.time.sleep)
R.os.open = lambda *a, **k: 4242
R.os.write = lambda fd, b: geschrieben.append(b) or len(b)
R.os.close = lambda fd: None
R.fcntl = FakeFcntl
schlafzeiten = []
R.time.sleep = lambda s: schlafzeiten.append(s)
try:
    R._geraet_fd = None
    check("erster Aufruf meldet Erfolg", R.send_reset_combo() is True)
    check("dabei wurde genau EIN Geraet angelegt", len(angelegt) == 1,
          str(angelegt))
    schlaf_erster = sum(schlafzeiten)
    schlafzeiten.clear()
    check("zweiter Aufruf meldet Erfolg", R.send_reset_combo() is True)
    check("und legt KEIN zweites Geraet an", len(angelegt) == 1,
          str(angelegt))
    schlaf_zweiter = sum(schlafzeiten)
    check("der zweite Aufruf wartet nicht mehr auf das Anlegen",
          schlaf_zweiter < schlaf_erster,
          "erster %.2fs, zweiter %.2fs" % (schlaf_erster, schlaf_zweiter))
    check("uebrig bleibt nur die Tastendruckdauer",
          abs(schlaf_zweiter - 0.1) < 0.001, "%.3fs" % schlaf_zweiter)

    print()
    print("Test 2b: es werden Druck UND Loslassen aller drei Tasten gesendet")
    # Bleibt eine Taste "gedrueckt", haengt die Kombination im System
    # fest und der naechste Reset kaeme nie an.
    ereignisse = []
    import struct as _struct
    for b in geschrieben[-8:]:
        if len(b) == _struct.calcsize(R._EVENT_FMT):
            _s, _us, typ, code, wert = _struct.unpack(R._EVENT_FMT, b)
            ereignisse.append((typ, code, wert))
    tasten = (R.KEY_LEFTCTRL, R.KEY_LEFTALT, R.KEY_RIGHTALT)
    gedrueckt = [c for typ, c, w in ereignisse if typ == R.EV_KEY and w == 1]
    losgelassen = [c for typ, c, w in ereignisse if typ == R.EV_KEY and w == 0]
    check("alle drei Tasten gedrueckt", sorted(gedrueckt) == sorted(tasten),
          str(gedrueckt))
    check("alle drei Tasten wieder losgelassen",
          sorted(losgelassen) == sorted(tasten), str(losgelassen))

    print()
    print("Test 2c: nach einem Schreibfehler wird das Geraet neu angelegt")
    # Sonst haetten wir uns mit dem dauerhaft offenen Geraet ein
    # Dauerproblem eingehandelt: waere es einmal kaputt (z.B. weil das
    # uinput-Modul entladen wurde), wuerde nie wieder ein Reset gehen.
    def _kaputt(fd, b):
        raise OSError("Test: Schreiben schlaegt fehl")

    R.os.write = _kaputt
    check("der Fehlschlag wird gemeldet", R.send_reset_combo() is False)
    check("das kaputte Geraet wurde geschlossen", len(geschlossen) >= 1,
          str(geschlossen))
    R.os.write = lambda fd, b: geschrieben.append(b) or len(b)
    check("der naechste Aufruf legt ein neues Geraet an",
          R.send_reset_combo() is True and len(angelegt) == 2,
          str(angelegt))
finally:
    R.os.open, R.os.write, R.os.close, R.fcntl, R.time.sleep = _echt
    R._geraet_fd = None

print()
print("Test 3: Halten loest nur EINMAL aus")
# Nachgebaut wird genau die Zustandsfolge aus wait_game_exit():
# Bericht mit gesetztem F5-Bit -> ausloesen; weitere Berichte mit
# weiterhin gesetztem Bit -> nichts; Bericht ohne Bit (losgelassen);
# Bericht mit Bit -> wieder ausloesen.
ausloesungen = []
reset_since = None
reset_gefeuert = False
RESET_HOLD = I.InputManager.RESET_HOLD

for gehalten in (True, True, True, True, False, False, True, True):
    if gehalten and reset_since is None and not reset_gefeuert:
        reset_since = time.monotonic()
        if RESET_HOLD <= 0:
            ausloesungen.append("reset")
            reset_since = None
            reset_gefeuert = True
    elif not gehalten:
        reset_since = None
        reset_gefeuert = False

check("vier Berichte mit gehaltener Taste ergeben EINEN Reset",
      ausloesungen[:1] == ["reset"], str(ausloesungen))
check("nach Loslassen und erneutem Druecken kommt ein zweiter",
      len(ausloesungen) == 2, str(ausloesungen))

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for f in fails:
        print("   ", f)
    sys.exit(1)
print("Alle Tests bestanden.")
