#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft, dass ein verlorenes Select-Loslassen nicht die Suche oeffnet
(Build 142).

Nutzer-Rueckmeldung: "ab und zu, wenn ich lange eine Richtung gedrueckt
habe und dann wieder ins Hauptmenue gehe und dann mit der Taste am
Joypad in eine Kategorie will, oeffnet sich auf einmal die
Volltextsuche."

Select+A ist die Suche (SELECT_COMBOS["ok"] = "search_pad"). Ob Select
gehalten wird, merkt sich fe/input.py in self._select_down - und das
wurde bisher NUR beim Loslass-Ereignis geleert. Faellt genau dieses
Ereignis weg, gilt Select fuer den Rest der Sitzung als gehalten, und
jedes A ist eine Suche.

Der Kommentar bei der Geraete-Aufraeumung in fe/input.py sagt das
woertlich voraus - nur war der Schutz ausschliesslich fuer den Fall
"Pad verschwindet" gebaut. Verlieren kann man das Ereignis aber auch,
wenn der Eingabepuffer ueberlaeuft, weil das Frontend gerade eine
Sekunde lang beschaeftigt war (im Profil des Nutzers standen Faelle mit
1089 ms und 722 ms).

Geprueft wird die echte Logik von InputManager - ohne Eingabegeraete,
indem die Zustandsuebergaenge direkt nachgestellt werden.

Ausfuehren:
    python3 tools/test_select_wachhund.py
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_FRONTEND_DIR = os.path.dirname(
    os.environ.get("FRONTEND_PY",
                   os.path.join(os.path.dirname(_HERE), "frontend",
                                "frontend.py")))
sys.path.insert(0, _FRONTEND_DIR)

import fe.input as I                                    # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


# Kuenstliche Uhr - sonst muesste der Test vier Sekunden warten.
NOW = [1000.0]
I.time.monotonic = lambda: NOW[0]

PAD = "/dev/input/event3"


def frischer_manager():
    im = I.InputManager.__new__(I.InputManager)
    im.devices = {}
    im._select_down = {}
    im._select_kombiniert = False
    im.held = None
    im._last_repeat_time = 0.0
    im._last_repeat_act = None
    im._last_repeat_iv = I.REPEAT_INTERVAL
    im._zeichenzeit = {}
    return im


print("Test 1: die Kombination funktioniert weiterhin")
im = frischer_manager()
im._select_down[PAD] = NOW[0]          # Select gedrueckt
check("Select gilt als gehalten", im._select_gehalten())
check("Select + A ist die Suche",
      I.SELECT_COMBOS.get("ok") == "search_pad")

print()
print("Test 2: DAS war der Fehler - Loslassen geht verloren")
im = frischer_manager()
im._select_down[PAD] = NOW[0]          # gedrueckt ...
# ... und das Loslass-Ereignis faellt weg. Der Nutzer geht ins
# Hauptmenue, schaut sich um, und drueckt irgendwann A.
NOW[0] += I.SELECT_MAX_HOLD + 0.5
check("nach %.0f Sekunden gilt Select als losgelassen"
      % I.SELECT_MAX_HOLD, not im._select_gehalten())
check("und der Merker ist mit aufgeraeumt",
      im._select_down == {} and im._select_kombiniert is False)

print()
print("Test 3: kurz gehalten bleibt kurz gehalten")
# Der Wachhund darf die normale Bedienung nicht kaputtmachen: wer
# Select haelt und gleich darauf A drueckt, will die Suche.
im = frischer_manager()
im._select_down[PAD] = NOW[0]
NOW[0] += I.SELECT_MAX_HOLD - 0.5
check("knapp unter der Grenze gilt Select noch", im._select_gehalten())
NOW[0] += 1.0
check("knapp darueber nicht mehr", not im._select_gehalten())

print()
print("Test 4: zwei Pads, eines haengt")
# Ein Pad mit verlorenem Loslassen darf ein zweites, tatsaechlich
# gehaltenes Select nicht entwerten - und umgekehrt.
im = frischer_manager()
im._select_down["/dev/input/event9"] = NOW[0] - I.SELECT_MAX_HOLD - 1
im._select_down[PAD] = NOW[0]
check("das frische Select zaehlt", im._select_gehalten())
check("das haengende ist weggeraeumt",
      "/dev/input/event9" not in im._select_down)

print()
print("Test 5: der Wachhund wird ueberhaupt gefragt")
# Regressionsschutz: steht in read_action() wieder die nackte Menge
# statt der Abfrage, ist der Fehler zurueck - und zwar unsichtbar.
quelle = open(os.path.join(_FRONTEND_DIR, "fe", "input.py"),
              encoding="utf-8").read()
check("read_action() fragt _select_gehalten()",
      "act in SELECT_COMBOS and self._select_gehalten()" in quelle)
check("und nicht mehr die nackte Menge",
      "self._select_down and act in SELECT_COMBOS" not in quelle)
check("_select_down traegt jetzt Zeitpunkte",
      "self._select_down[dev.path] = time.monotonic()" in quelle)

print()
print("Test 6: der bisherige Schutz ist noch da")
# Verschwindet ein Pad, waehrend Select gehalten wird, muss der
# Eintrag weiterhin sofort weg - darauf muss man nicht erst vier
# Sekunden warten.
check("beim Verschwinden eines Geraets wird aufgeraeumt",
      "self._select_down.pop(path, None)" in quelle)

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Tests bestanden.")
