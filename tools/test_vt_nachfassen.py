#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft, dass das Frontend die Anzeige zurueckholt, wenn der bootende
MiSTer sie ihm weggenommen hat (Build 146).

Nutzer-Rueckmeldung: "bin im OSD und hoere die Musik vom Frontend".

Das Frontend schaltet den MiSTer genau EINMAL per F9 in den
Konsolenmodus, ganz am Anfang. Danach baut es seine Kategorien auf.
Dauert das lange genug - beim Nutzer 44 Sekunden, weil der games-Ordner
geloescht war -, ist der MiSTer inzwischen fertig gebootet und holt
sich die Anzeige zurueck. Das Frontend zeichnet dann in einen
Framebuffer, den niemand sieht: Musik laeuft, Bild zeigt das OSD. Sieht
aus wie ein Absturz, ist ein verlorenes Wettrennen.

_boot_watch() hatte genau diese Signatur (VT=tty2) von Anfang an
protokolliert, aber bewusst nichts unternommen. Jetzt fasst es nach.

Geprueft wird vor allem, wann es NICHT nachfassen darf - ein Frontend,
das einen aus dem OSD zurueckzerrt, waere schlimmer als das Problem.

Ausfuehren:
    python3 tools/test_vt_nachfassen.py
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


_tmp = tempfile.mkdtemp(prefix="vt_test_")
_corename = os.path.join(_tmp, "CORENAME")
fm.CORENAME = _corename


def aufbau(vt="tty2", core="MENU", el=4.0, beruehrt=False):
    """Frontend mit nachgestelltem Anzeige-Zustand."""
    with open(_corename, "w") as fh:
        fh.write(core + "\x00")
    f = H.make_frontend(page=0)
    f._active_vt = lambda: vt
    f._boot_time = H.NOW[0] - el
    f._last_input_time = (H.NOW[0] if beruehrt else f._boot_time - 1.0)
    f._last_vt_check = 0.0
    f._last_bootstate = None
    f._last_snapshot = 0.0
    f._vt_nachgefasst = 0
    f._letztes_nachfassen = 0.0
    f._zaehler = {"konsole": 0, "gezeichnet": 0, "gegriffen": 0}

    def _konsole():
        f._zaehler["konsole"] += 1
    f.enter_console_mode = _konsole
    f.set_cursor_blink = lambda an: None
    f.inp.flush = lambda: None
    f.inp.grab = lambda an: f._zaehler.__setitem__(
        "gegriffen", f._zaehler["gegriffen"] + 1)
    f.draw = lambda *a, **k: f._zaehler.__setitem__(
        "gezeichnet", f._zaehler["gezeichnet"] + 1)
    return f


def laufen_lassen(f, runden=12, schritt=1.5):
    """Mehrere Durchlaeufe der Hauptschleife nachstellen."""
    start = H.NOW[0]
    for _ in range(runden):
        f._boot_watch()
        H.NOW[0] += schritt
    H.NOW[0] = start


# ---------------------------------------------------------------------------
print("Test 1: Anzeige weg -> F9 wird nachgeschickt")
# ---------------------------------------------------------------------------
f = aufbau(vt="tty2", core="MENU")
laufen_lassen(f)
check("F9 wurde nachgeschickt", f._zaehler["konsole"] > 0,
      "%d mal" % f._zaehler["konsole"])
check("hoechstens dreimal - kein Dauerfeuer",
      f._zaehler["konsole"] == fm.Frontend.VT_NACHFASSEN_MAX,
      "%d mal" % f._zaehler["konsole"])
check("danach wurde neu gezeichnet", f._zaehler["gezeichnet"] > 0,
      "%d mal" % f._zaehler["gezeichnet"])
check("die Tastatur wurde wieder uebernommen",
      f._zaehler["gegriffen"] > 0, "%d mal" % f._zaehler["gegriffen"])

# ---------------------------------------------------------------------------
print("Test 2: alles in Ordnung -> nichts passiert")
# ---------------------------------------------------------------------------
f = aufbau(vt="tty1", core="MENU")
laufen_lassen(f)
check("auf tty1 wird nicht nachgefasst", f._zaehler["konsole"] == 0,
      "%d mal" % f._zaehler["konsole"])

# ---------------------------------------------------------------------------
print("Test 3: ein Spiel laeuft -> Finger weg")
# ---------------------------------------------------------------------------
f = aufbau(vt="tty2", core="SNES")
laufen_lassen(f)
check("bei laufendem Core wird nicht nachgefasst",
      f._zaehler["konsole"] == 0, "%d mal" % f._zaehler["konsole"])

# ---------------------------------------------------------------------------
print("Test 4: der Nutzer ist selbst ins OSD gegangen -> Finger weg")
# ---------------------------------------------------------------------------
f = aufbau(vt="tty2", core="MENU", beruehrt=True)
laufen_lassen(f)
check("nach einer Eingabe wird nicht nachgefasst",
      f._zaehler["konsole"] == 0, "%d mal" % f._zaehler["konsole"])

# ---------------------------------------------------------------------------
print("Test 5: ausserhalb des Startfensters -> Finger weg")
# ---------------------------------------------------------------------------
f = aufbau(vt="tty2", core="MENU", el=fm.Frontend.BOOT_WATCH_FENSTER + 5.0)
laufen_lassen(f)
check("nach einer Minute wird nicht mehr nachgefasst",
      f._zaehler["konsole"] == 0, "%d mal" % f._zaehler["konsole"])

# ---------------------------------------------------------------------------
print("Test 6: der Abstand zwischen zwei Versuchen wird eingehalten")
# ---------------------------------------------------------------------------
f = aufbau(vt="tty2", core="MENU")
# Schritte kleiner als der geforderte Abstand: die Drossel in
# _boot_watch selbst laesst ohnehin nur jede Sekunde einen Durchlauf zu,
# der Abstand muss zusaetzlich greifen.
laufen_lassen(f, runden=4, schritt=1.1)
check("in 4.4s hoechstens zwei Versuche",
      f._zaehler["konsole"] <= 2, "%d mal" % f._zaehler["konsole"])

# ---------------------------------------------------------------------------
print("Test 7: unlesbare VT -> lieber nichts tun")
# ---------------------------------------------------------------------------
f = aufbau(vt="?", core="MENU")
laufen_lassen(f)
check("bei unbekannter VT wird nicht nachgefasst",
      f._zaehler["konsole"] == 0, "%d mal" % f._zaehler["konsole"])

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  - " + x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
