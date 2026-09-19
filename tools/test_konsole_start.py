#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft die Absicherung des Konsolenmodus (Build 150).

Nutzer-Rueckmeldung ueber mehrere Builds: "bin im OSD und hoere die
Musik vom Frontend". Kein Absturz - das Frontend laeuft, zeichnet und
spielt Musik, nur zeigt der Bildschirm MiSTers Menue.

Das Frontend schickt sein F9 rund eine Sekunde nach dem eigenen Start.
Mal sitzt es, mal nicht: MiSTer nimmt die Taste entgegen und macht den
Wechsel im Zuge seiner eigenen Initialisierung wieder zunichte. Ob das
passiert, haengt daran, wie lange MiSTer an diesem Tag zum Hochfahren
braucht.

DREI IRRWEGE, die dieser Test mit absichert:

  Build 146 fasste nach, sobald "VT != tty1" war. Beim Nutzer stand die
  VT durchgehend auf tty1 - die Bedingung konnte nie zutreffen. Die
  aktive Linux-Konsole sagt auf dem MiSTer nichts darueber aus, was auf
  dem Bildschirm landet.

  Build 147 wartete stattdessen, bis MiSTer ein Mindestalter erreicht
  hatte. Das liess den Bildschirm eine halbe Minute leer - und eine
  einzige Regung der Funkmaus strich den Termin ersatzlos.

Beide Umwege entstanden aus derselben falschen Annahme: F9 sei ein
UMSCHALTER, ein zweiter Druck nehme ein funktionierendes Bild wieder
weg. Der eigene Code beweist das Gegenteil - open_osd() und der
Exit-Pfad schalten mit F12 ins MiSTer-Menue, zurueck geht es mit F9.
Zwei Tasten, zwei Richtungen. Wiederholen ist also gefahrlos.

  Build 148 wiederholte deshalb - brach aber ab, sobald sich
  _last_input_time bewegt hatte ("dann bedient der Nutzer das Frontend,
  also sieht er es"). Die Funkmaus des Nutzers meldet Achsen; ein Zucken
  auf dem Tisch reichte, und die Absicherung schaltete sich ab, BEVOR
  der erste Schuss raus war. Im Log stand dann woertlich "Nutzer bedient
  das Frontend, es ist also sichtbar", waehrend er im OSD sass.

Build 149 betrachtet Eingaben gar nicht mehr. Der Griff war ohnehin
ueberfluessig: ein F9 bei bereits sichtbarer Konsole tut nichts.

Ausfuehren:
    python3 tools/test_konsole_start.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H                                        # noqa: E402

fm = H.fm
fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


_tmp = tempfile.mkdtemp(prefix="konsole_test_")
_corename = os.path.join(_tmp, "CORENAME")
fm.CORENAME = _corename


def aufbau(core="MENU", beruehrt=False):
    with open(_corename, "w") as fh:
        fh.write(core + "\x00")
    f = H.make_frontend(page=0)
    f._zaehler = {"f9": 0, "grab": 0}
    f.inp.inject = lambda code: f._zaehler.__setitem__(
        "f9", f._zaehler["f9"] + 1)
    f.inp.grab = lambda an: f._zaehler.__setitem__(
        "grab", f._zaehler["grab"] + 1)
    f._boot_time = H.NOW[0]
    f._last_input_time = (H.NOW[0] + 3.0 if beruehrt else H.NOW[0] - 1.0)
    f._f9_wiederholt = 0
    f._f9_aufraeumen_ab = None
    # Vorgabe: MiSTer rechnet (OSD sichtbar) - die Absicherung laeuft.
    f._mister_last = lambda: 100.0
    return f


def laufen(f, bis=70.0, schritt=1.0):
    start = H.NOW[0]
    while H.NOW[0] - start < bis:
        f._konsole_sichern()
        H.NOW[0] += schritt
    H.NOW[0] = start


PLAN = fm.Frontend.F9_WIEDERHOLUNGEN

# ---------------------------------------------------------------------------
print("Test 1: unbedienter Start -> F9 wird wiederholt")
# ---------------------------------------------------------------------------
f = aufbau()
laufen(f)
check("alle geplanten Wiederholungen geschickt",
      f._zaehler["f9"] == len(PLAN),
      "%d von %d" % (f._zaehler["f9"], len(PLAN)))
check("danach ist Schluss - kein Dauerfeuer",
      f._f9_wiederholt == len(PLAN))
check("KEIN Grab-Gefummel - die Absicherung muss billig sein",
      f._zaehler["grab"] == 0, "%d Aufrufe" % f._zaehler["grab"])

# ---------------------------------------------------------------------------
print("Test 2: nicht frueher als geplant")
# ---------------------------------------------------------------------------
f = aufbau()
H.NOW[0] += PLAN[0] - 0.5
f._konsole_sichern()
check("vor dem ersten Termin passiert nichts", f._zaehler["f9"] == 0,
      "%d mal" % f._zaehler["f9"])
H.NOW[0] += 1.0
f._konsole_sichern()
check("zum ersten Termin genau ein F9", f._zaehler["f9"] == 1,
      "%d mal" % f._zaehler["f9"])
f._konsole_sichern()
check("und im selben Moment kein zweites", f._zaehler["f9"] == 1,
      "%d mal" % f._zaehler["f9"])
H.NOW[0] = 1000.0

# ---------------------------------------------------------------------------
print("Test 3: Eingaben brechen NICHT mehr ab (die Korrektur aus Build 149)")
# ---------------------------------------------------------------------------
# Build 148 brach ab, sobald sich _last_input_time bewegt hatte. Beim
# Nutzer meldet die Funkmaus Achsen - ein Zucken auf dem Tisch reichte,
# und die Absicherung schaltete sich ab, BEVOR der erste Schuss raus
# war, waehrend er in Wahrheit im OSD sass.
f = aufbau(beruehrt=True)
laufen(f)
check("trotz Eingabe wird abgesichert", f._zaehler["f9"] == len(PLAN),
      "%d von %d" % (f._zaehler["f9"], len(PLAN)))

# auch wenn die Eingabe mittendrin kommt
f = aufbau()
H.NOW[0] += PLAN[1] + 0.5
f._konsole_sichern()
f._last_input_time = H.NOW[0] + 0.5
laufen(f)
check("Eingabe mittendrin stoppt nichts", f._zaehler["f9"] == len(PLAN),
      "%d von %d" % (f._zaehler["f9"], len(PLAN)))
H.NOW[0] = 1000.0

# ---------------------------------------------------------------------------
print("Test 4: ein Spiel laeuft -> Finger weg")
# ---------------------------------------------------------------------------
f = aufbau(core="SNES")
laufen(f)
check("kein F9 bei laufendem Core", f._zaehler["f9"] == 0,
      "%d mal" % f._zaehler["f9"])

# ---------------------------------------------------------------------------
print("Test 5: CORENAME unlesbar -> trotzdem absichern")
# ---------------------------------------------------------------------------
fm.CORENAME = os.path.join(_tmp, "gibtsnicht")
f = H.make_frontend(page=0)
f._zaehler = {"f9": 0, "grab": 0}
f.inp.inject = lambda code: f._zaehler.__setitem__(
    "f9", f._zaehler["f9"] + 1)
f._boot_time = H.NOW[0]
f._last_input_time = H.NOW[0] - 1.0
f._f9_wiederholt = 0
f._f9_aufraeumen_ab = None
f._mister_last = lambda: 100.0
laufen(f)
check("fehlende Datei blockiert die Absicherung nicht",
      f._zaehler["f9"] == len(PLAN),
      "%d von %d" % (f._zaehler["f9"], len(PLAN)))
fm.CORENAME = _corename

# ---------------------------------------------------------------------------
print("Test 6: F9 loest im Frontend selbst nichts aus")
# ---------------------------------------------------------------------------
# Das eingespeiste Ereignis wird von derselben Instanz wieder gelesen -
# waere F9 belegt, wuerde sich das Frontend bei jeder Absicherung selbst
# verstellen UND ueber _last_input_time die Absicherung abwuergen.
import fe.input as INP                                      # noqa: E402
check("KEY_F9 ist auf None gelegt",
      INP.KEYMAP.get(INP.KEY_F9) is None,
      repr(INP.KEYMAP.get(INP.KEY_F9)))
check("KEY_F12 dagegen oeffnet das OSD - zwei Tasten, zwei Richtungen",
      INP.KEYMAP.get(INP.KEY_F12) == "osd",
      repr(INP.KEYMAP.get(INP.KEY_F12)))

# ---------------------------------------------------------------------------
print("Test 7: nach jedem F9 wird die Konsolenausgabe weggewischt")
# ---------------------------------------------------------------------------
# Das eingespeiste F9 erreicht auch den Login-Prozess auf tty1. Der
# wacht davon auf und schreibt "Welcome to MiSTer ... login:" mitten in
# unser Bild - der Nutzer sah nach Build 149 genau das.
f = aufbau()
f._zaehler["gezeichnet"] = 0
f._zaehler["blink"] = 0
f.draw = lambda *a, **k: f._zaehler.__setitem__(
    "gezeichnet", f._zaehler["gezeichnet"] + 1)
f.set_cursor_blink = lambda an: f._zaehler.__setitem__(
    "blink", f._zaehler["blink"] + 1)
f._f9_aufraeumen_ab = None

H.NOW[0] += PLAN[0] + 0.1
f._konsole_sichern()
check("F9 ging raus", f._zaehler["f9"] == 1, "%d mal" % f._zaehler["f9"])
check("Aufraeumen ist vorgemerkt", f._f9_aufraeumen_ab is not None)
f._konsole_aufraeumen()
check("aber noch nicht sofort - erst muss der Prompt da sein",
      f._zaehler["gezeichnet"] == 0, "%d mal" % f._zaehler["gezeichnet"])

# Ohne Fremdausgabe bleibt alles ruhig - genau das verhindert das
# Flackern, das der Nutzer nach Build 150 gesehen hat.
H.NOW[0] += 1.0
f.fb.buf[:] = f.fb.mm[:]          # Bild und Puffer sind gleich
f._konsole_aufraeumen()
check("ohne Fremdausgabe wird NICHT neu gezeichnet",
      f._zaehler["gezeichnet"] == 0, "%d mal" % f._zaehler["gezeichnet"])

# Jetzt schreibt ein Fremder oben ins Bild.
f._f9_aufraeumen_ab = H.NOW[0] - 1.0
f.fb.mm[0:64] = b"\xff" * 64
vorher = f.fb.full_redraw_gen
f._konsole_aufraeumen()
check("mit Fremdausgabe wird neu gezeichnet", f._zaehler["gezeichnet"] == 1,
      "%d mal" % f._zaehler["gezeichnet"])
check("und zwar als VOLLER Aufbau", f.fb.full_redraw_gen > vorher,
      "%d -> %d" % (vorher, f.fb.full_redraw_gen))
check("der Cursor bleibt aus", f._zaehler["blink"] == 1,
      "%d mal" % f._zaehler["blink"])
check("Termin verbraucht", f._f9_aufraeumen_ab is None)

f._konsole_aufraeumen()
check("kein zweites Aufraeumen ohne neues F9",
      f._zaehler["gezeichnet"] == 1, "%d mal" % f._zaehler["gezeichnet"])
H.NOW[0] = 1000.0


# ---------------------------------------------------------------------------
print("Test 8: schlaefiger MiSTer beendet die Absicherung sofort")
# ---------------------------------------------------------------------------
# Das Signal, das zwei Tage lang gesucht wurde: MiSTer laeuft auf 100 %,
# solange er sein eigenes Menue zeichnet, und faellt auf ~1 %, sobald
# unser Framebuffer angezeigt wird. Gemessen ueber je fuenf Sekunden:
# 500 Ticks gegen 7.
f = aufbau()
f._mister_last = lambda: 1.4          # Konsole liegt oben
laufen(f)
check("kein einziges F9 noetig", f._zaehler["f9"] == 0,
      "%d mal" % f._zaehler["f9"])
check("und es wird auch nicht spaeter nochmal versucht",
      f._f9_wiederholt == len(PLAN))

# Mittendrin umschlagen: erst OSD, dann klappt es.
f = aufbau()
zustand = {"last": 100.0}
f._mister_last = lambda: zustand["last"]
H.NOW[0] += PLAN[0] + 0.1
f._konsole_sichern()
check("solange MiSTer rechnet, wird geschickt", f._zaehler["f9"] == 1,
      "%d mal" % f._zaehler["f9"])
zustand["last"] = 0.8                 # F9 hat gesessen
laufen(f)
check("danach ist sofort Schluss - kein Flackern mehr",
      f._zaehler["f9"] == 1, "%d mal" % f._zaehler["f9"])
H.NOW[0] = 1000.0

# Ohne Messwert (None) bleibt es beim reinen Zeitplan.
f = aufbau()
f._mister_last = lambda: None
laufen(f)
check("ohne Messwert zaehlt weiterhin der Zeitplan",
      f._zaehler["f9"] == len(PLAN),
      "%d von %d" % (f._zaehler["f9"], len(PLAN)))

# Die Schwelle liegt zwischen den beiden gemessenen Welten.
check("Schwelle liegt zwischen 1,4 % und 100 %",
      1.4 < fm.Frontend.MISTER_BESCHAEFTIGT < 100.0,
      "%.0f %%" % fm.Frontend.MISTER_BESCHAEFTIGT)


print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  - " + x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
