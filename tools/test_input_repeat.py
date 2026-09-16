#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft die Tastenwiederholung mit der ECHTEN InputManager-Logik.

Hintergrund (Nutzer-Rueckmeldungen, beide hier festgehalten):
  1. "wenn ich nach unten gedrueckt halte und dann wieder nach oben
     druecke bleibt der kurz haengen" - beim Richtungswechsel MITTEN im
     Scrollen lief die volle Anlaufsperre (REPEAT_DELAY) erneut an.
  2. "der Cursor bewegt sich nicht und dann kommt auf einmal die
     ploetzliche Bewegung" - nach 'Zurueck'/'OK' lief eine Geister-
     Wiederholung der vorher gehaltenen Richtungstaste weiter.

Getestet werden ausschliesslich die Zustandsuebergaenge der Wiederhol-
Steuerung (_hold/_release/_cancel_repeat und der Wiederhol-Zweig aus
read_action) - dafuer werden keine echten Eingabegeraete gebraucht.

Ausfuehren:
    python3 tools/test_input_repeat.py
"""
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_FRONTEND_DIR = os.path.dirname(
    os.environ.get("FRONTEND_PY",
                   os.path.join(os.path.dirname(_HERE), "frontend",
                                "frontend.py")))
sys.path.insert(0, _FRONTEND_DIR)

import fe.input as I          # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


im = I.InputManager.__new__(I.InputManager)   # ohne Geraete-Scan
im.devices = {}
im.want_grab = False
im.last_scan = 0.0
im.held = None
im._last_repeat_time = 0.0
im._last_repeat_act = None
im._last_repeat_iv = I.REPEAT_INTERVAL
im._last_input_mtime = None
# Build 93: ohne Messwerte gelten die festen Boeden - genau der
# Zustand, den dieser Test prueft.
im._zeichenzeit = {}

KID_DOWN = ("/dev/input/event0", "key", 108)
KID_UP = ("/dev/input/event0", "key", 103)
KID_RIGHT = ("/dev/input/event0", "key", 106)


def fire_repeat():
    """Bildet den Wiederhol-Zweig aus read_action() nach."""
    kid, act, _t, iv = im.held
    iv = max(I.REPEAT_FLOOR, iv * 0.85)
    im.held = (kid, act, time.monotonic() + iv, iv)
    im._last_repeat_time = time.monotonic()
    im._last_repeat_act = act
    im._last_repeat_iv = iv
    return act


print("Test 1: einzelner Tastendruck aus dem Stand -> volle Anlaufsperre")
im._last_repeat_act = None
t0 = time.monotonic()
im._hold(KID_DOWN, "down")
delay = im.held[2] - t0
check("Anlaufzeit betraegt %.0f ms (erwartet %.0f ms)"
      % (delay * 1000, I.REPEAT_DELAY * 1000),
      abs(delay - I.REPEAT_DELAY) < 0.02)

print()
print("Test 2: Richtungswechsel MITTEN im Scrollen -> kurze Anlaufzeit")
for _ in range(8):
    fire_repeat()
check("Dauergeschwindigkeit erreicht: %.0f ms" % (im._last_repeat_iv * 1000),
      abs(im._last_repeat_iv - I.REPEAT_FLOOR) < 1e-6)
t0 = time.monotonic()
im._hold(KID_UP, "up")            # Richtungswechsel
delay = im.held[2] - t0
check("Anlaufzeit nur noch %.0f ms (statt %.0f ms)"
      % (delay * 1000, I.REPEAT_DELAY * 1000),
      abs(delay - I.REPEAT_REVERSE_DELAY) < 0.02)
check("erreichtes Tempo bleibt erhalten (%.0f ms)" % (im.held[3] * 1000),
      abs(im.held[3] - I.REPEAT_FLOOR) < 1e-6)
check("Aktion ist jetzt 'up'", im.held[1] == "up")

print()
print("Test 3: Achswechsel (runter -> rechts) gilt NICHT als Richtungswechsel")
im._last_repeat_act = "down"
im._last_repeat_time = time.monotonic()
im._last_repeat_iv = I.REPEAT_FLOOR
t0 = time.monotonic()
im._hold(KID_RIGHT, "right")
delay = im.held[2] - t0
check("volle Anlaufsperre %.0f ms" % (delay * 1000),
      abs(delay - I.REPEAT_DELAY) < 0.02)

print()
print("Test 4: nach einer Scroll-Pause wieder volle Anlaufsperre")
im._last_repeat_act = "down"
im._last_repeat_time = time.monotonic() - (I.REPEAT_CONTINUE_WINDOW + 0.2)
t0 = time.monotonic()
im._hold(KID_UP, "up")
delay = im.held[2] - t0
check("volle Anlaufsperre %.0f ms" % (delay * 1000),
      abs(delay - I.REPEAT_DELAY) < 0.02)

print()
print("Test 5: Geister-Wiederholung nach 'Zurueck'/'OK' wird abgebrochen")
im._last_repeat_act = None
im._hold(KID_DOWN, "down")
for _ in range(5):
    fire_repeat()
check("Wiederholung laeuft (held gesetzt)", im.held is not None)
im._cancel_repeat()               # das macht jetzt jede nicht-wiederholbare Aktion
check("held ist danach geloescht", im.held is None)
check("Merker fuer Richtungswechsel ebenfalls zurueckgesetzt",
      im._last_repeat_act is None)
t0 = time.monotonic()
im._hold(KID_UP, "up")
delay = im.held[2] - t0
check("naechste Richtungstaste laeuft wieder normal an (%.0f ms)"
      % (delay * 1000),
      abs(delay - I.REPEAT_DELAY) < 0.02)

print()
print("Test 6: _release() verhaelt sich unveraendert")
im._last_repeat_act = None
im._hold(KID_DOWN, "down")
im._release(("/dev/input/event0", "key", 999))    # andere Taste
check("fremde Taste loest nichts aus", im.held is not None)
im._release(KID_DOWN)
check("eigene Taste loescht die Wiederholung", im.held is None)

print()
print("Test 7: Seiten-Spruenge (links/rechts) haben eine eigene, "
      "langsamere Untergrenze")
check("Seiten-Untergrenze (%.0f ms) ist groesser als die Zeilen-Untergrenze "
      "(%.0f ms)" % (I.REPEAT_FLOOR_PAGE * 1000, I.REPEAT_FLOOR * 1000),
      I.REPEAT_FLOOR_PAGE > I.REPEAT_FLOOR)
check("_repeat_floor('left') liefert die Seiten-Untergrenze",
      abs(im._repeat_floor("left") - I.REPEAT_FLOOR_PAGE) < 1e-9)
check("_repeat_floor('down') liefert die Zeilen-Untergrenze",
      abs(im._repeat_floor("down") - I.REPEAT_FLOOR) < 1e-9)

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for f in fails:
        print("   ", f)
    sys.exit(1)
print("Alle Tests bestanden.")


# ---------------------------------------------------------------------
print()
print("Test 8: welche Richtungen 'Seite' bedeuten, ist umstellbar (Build 136)")
# Nutzer-Rueckmeldung: "das nach links und rechts scrollen kann trotzdem
# schneller passieren, wenn ich die Richtung gedrueckt halte."
#
# Der langsame Boden (0.25 s) ist richtig, wenn ein Druck eine ganze
# Seite blaettert. Bis Build 135 galt er FEST fuer links/rechts - auch
# im Raster, wo links/rechts nur eine Kachel weitergeht und damit die
# billigste Bewegung ueberhaupt ist. Vier Schritte je Sekunde fuer zwei
# neu gezeichnete Kacheln.
#
# Hier wird nur die EINGABESEITE geprueft: dass sich die Menge
# umstellen laesst und der Boden ihr folgt. Dass das Frontend je
# Ansicht die richtige Menge meldet, prueft tools/test_ansichten.py -
# dafuer braucht es den Pruefstand, den diese Datei bewusst nicht laedt.
im.seiten_aktionen_setzen(("up", "down"))
check("hoch/runter wird zur Seitenbewegung",
      im._repeat_floor("up") == I.REPEAT_FLOOR_PAGE,
      "%.2f" % im._repeat_floor("up"))
check("und links/rechts damit zur normalen",
      im._repeat_floor("left") == I.REPEAT_FLOOR,
      "%.2f" % im._repeat_floor("left"))
im.seiten_aktionen_setzen(())
check("ohne Seitenbewegung sind beide schnell",
      im._repeat_floor("left") == I.REPEAT_FLOOR
      and im._repeat_floor("up") == I.REPEAT_FLOOR)
im.seiten_aktionen_setzen(I.PAGE_ACTIONS)
check("und zurueck auf die Vorgabe",
      im._repeat_floor("left") == I.REPEAT_FLOOR_PAGE)

# Ein Objekt OHNE das Feld (aeltere Fassung, oder wie hier ueber
# __new__ gebaut) muss weiterhin rechnen koennen.
_roh = I.InputManager.__new__(I.InputManager)
_roh._zeichenzeit = {}
check("ohne das Feld gilt die Vorgabe",
      _roh._repeat_floor("left") == I.REPEAT_FLOOR_PAGE
      and _roh._repeat_floor("up") == I.REPEAT_FLOOR)

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for f_ in fails:
        print("  -", f_)
    sys.exit(1)
print("Alle Tests bestanden.")
