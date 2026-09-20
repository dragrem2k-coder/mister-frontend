#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Der Farbschema-Editor (Build 172).

WAS HIER WIRKLICH SCHIEFGEHEN KANN

Nicht die Farbrechnung - die ist trivial. Gefaehrlich sind drei
andere Dinge, und der Test ist um sie herum gebaut:

  1. DER EDITOR DARF DAS LAUFENDE ERSCHEINUNGSBILD NICHT ANFASSEN,
     solange nicht gespeichert wurde. Die Vorschau zeichnet deshalb
     mit den Farben aus dem Editor, NICHT ueber die globalen
     C_*-Variablen. Waere es andersherum, muesste ein Abbruch alles
     zuruecknehmen - und genau das vergisst man irgendwann.
  2. ER MUSS AUF DER ROEHRE PASSEN. 320x240 mit Bildrand ist der
     enge Fall; eine abgeschnittene Vorschau waere irrefuehrender
     als gar keine.
  3. DIE WERTE MUESSEN IN 0..255 BLEIBEN. Ein Ueberlauf faellt
     nicht hier auf, sondern spaeter beim Zeichnen.

Getrieben wird der Editor mit einer Liste erfundener Tastendruecke -
so laeuft die echte Eingabeschleife, nicht eine Nachbildung davon.

Ausfuehren:
    python3 tools/test_theme_editor.py
"""
import io
import os
import shutil
import sys
import tempfile

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
sys.path.insert(0, _HIER)

import _harness as H                                     # noqa: E402

fm = H.fm
fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


class Tasten(object):
    """Eine Liste erfundener Tastendruecke, danach 'back'.

    Das 'back' am Ende ist die Reissleine: kaeme der Editor aus
    irgendeinem Grund nicht heraus, liefe der Test sonst ewig statt
    fehlzuschlagen."""

    def __init__(self, folge):
        self.folge = list(folge)
        self.gelesen = []

    def read_action(self, timeout=None):
        if self.folge:
            akt = self.folge.pop(0)
        else:
            akt = "back"
        self.gelesen.append(akt)
        return akt


def editor_laufen_lassen(folge, hoehe=1080, breite=1920, datei=None):
    f = H.make_frontend(page=0)
    if (f.fb.width, f.fb.height) != (breite, hoehe):
        f.fb.width, f.fb.height = breite, hoehe
        f.fb.stride = breite * 4
        f.fb.size = f.fb.stride * hoehe
        f.fb.mm = bytearray(f.fb.size)
        f.fb.buf = bytearray(f.fb.size)
        f.fb._rowcache.clear()
    if datei is not None:
        fm.THEME_EIGEN_FILE = datei
    f.inp = Tasten(folge)
    f.draw = lambda *a, **k: None
    f._refresh_system_category = lambda *a, **k: None
    f.theme_editor()
    return f


tmp = tempfile.mkdtemp(prefix="test_theme_editor_")
DATEI = os.path.join(tmp, "theme_eigen.json")

# BEIDE Dateien umlenken, nicht nur die mit den Farben.
#
# Beim ersten Lauf hat dieser Test "eigen" in das ECHTE
# /media/fat/frontend/theme geschrieben - der Testrechner hatte danach
# ein Farbschema eingestellt, das es gar nicht gibt. Harmlos (es faellt
# beim naechsten Start auf "dark" zurueck), aber ein Test hat nichts
# ausserhalb seines eigenen Ordners zu hinterlassen. Selbst gefunden,
# bevor es jemandem aufgefallen waere.
_ALTE_DATEI = fm.THEME_EIGEN_FILE
_ALTE_WAHL = fm.THEME_FILE
fm.THEME_FILE = os.path.join(tmp, "theme")

# ---------------------------------------------------------------------------
print("Test 1: er laesst sich oeffnen und wieder verlassen")
# ---------------------------------------------------------------------------
fm.THEMES.pop("eigen", None)
vorher = (fm.C_BG, fm.C_PANEL, fm.C_TEXT, fm.C_DIM, fm.C_TITLE, fm.C_ACCENT)
f = editor_laufen_lassen(["back"], datei=DATEI)
check("er kehrt zurueck", True)
nachher = (fm.C_BG, fm.C_PANEL, fm.C_TEXT, fm.C_DIM, fm.C_TITLE, fm.C_ACCENT)
check("DAS LAUFENDE SCHEMA IST UNVERAENDERT", vorher == nachher,
      "%r -> %r" % (vorher[0], nachher[0]))
check("und es wurde nichts geschrieben", not os.path.exists(DATEI))

# ---------------------------------------------------------------------------
print()
print("Test 2: auch nach vielen Aenderungen ohne Speichern")
# ---------------------------------------------------------------------------
# Der eigentliche Punkt von Punkt 1 oben: erst drehen, dann abbrechen.
folge = ["right"] * 20 + ["down", "right", "right"] + ["ok", "right"] * 3
f = editor_laufen_lassen(folge + ["back"], datei=DATEI)
nachher = (fm.C_BG, fm.C_PANEL, fm.C_TEXT, fm.C_DIM, fm.C_TITLE, fm.C_ACCENT)
check("das laufende Schema ist immer noch unveraendert",
      vorher == nachher, "%r -> %r" % (vorher[0], nachher[0]))
check("und immer noch keine Datei", not os.path.exists(DATEI))

# ---------------------------------------------------------------------------
print()
print("Test 3: speichern - und zwar genau das, was eingestellt war")
# ---------------------------------------------------------------------------
# Von der ersten Zeile (C_BG) den Rotwert um 3 Schritte hochdrehen,
# dann ganz nach unten auf "Speichern" und bestaetigen.
schritt = fm.Frontend.THEME_EDIT_SCHRITT
start = fm.THEMES[fm.current_theme_name()]["C_BG"]
erwartet_r = min(255, start[0] + 3 * schritt)
runter = ["down"] * (len(fm.THEME_FARBFELDER) + 1)
f = editor_laufen_lassen(["right"] * 3 + runter + ["ok"], datei=DATEI)
check("die Datei liegt jetzt da", os.path.exists(DATEI))
gespeichert = fm.eigenes_theme_lesen(DATEI)
check("und enthaelt alle sechs Farben",
      gespeichert is not None
      and all(fx in gespeichert for fx in fm.THEME_FARBFELDER))
if gespeichert:
    check("der geaenderte Rotwert steht drin",
          gespeichert["C_BG"][0] == erwartet_r,
          "%d, erwartet %d" % (gespeichert["C_BG"][0], erwartet_r))
    check("Gruen und Blau blieben unberuehrt",
          gespeichert["C_BG"][1] == start[1]
          and gespeichert["C_BG"][2] == start[2])
check("und das Schema ist jetzt aktiv",
      fm.current_theme_name() == "eigen", fm.current_theme_name())

# ---------------------------------------------------------------------------
print()
print("Test 4: die Werte bleiben zwischen 0 und 255")
# ---------------------------------------------------------------------------
# Weit ueber das Ende hinaus drehen - in beide Richtungen.
f = editor_laufen_lassen(["right"] * 200 + runter + ["ok"], datei=DATEI)
oben = fm.eigenes_theme_lesen(DATEI)
check("nach oben ist bei 255 Schluss", oben["C_BG"][0] == 255,
      str(oben["C_BG"]))
f = editor_laufen_lassen(["left"] * 200 + runter + ["ok"], datei=DATEI)
unten = fm.eigenes_theme_lesen(DATEI)
check("nach unten bei 0", unten["C_BG"][0] == 0, str(unten["C_BG"]))
check("und die anderen Kanaele sind davon unberuehrt",
      unten["C_BG"][1] == oben["C_BG"][1])

# ---------------------------------------------------------------------------
print()
print("Test 5: Enter schaltet durch R/G/B")
# ---------------------------------------------------------------------------
# Einmal Enter, dann rechts -> Gruen muss sich aendern, Rot nicht.
f = editor_laufen_lassen(["ok", "right", "right"] + runter + ["ok"],
                         datei=DATEI)
nach = fm.eigenes_theme_lesen(DATEI)
basis = fm.THEMES["eigen"]
check("Gruen hat sich bewegt",
      nach["C_BG"][1] != unten["C_BG"][1],
      "%s -> %s" % (unten["C_BG"], nach["C_BG"]))
check("Rot blieb stehen", nach["C_BG"][0] == unten["C_BG"][0])

# ---------------------------------------------------------------------------
print()
print("Test 6: der monochrome-Schalter laesst sich umlegen")
# ---------------------------------------------------------------------------
vor_mono = bool(fm.eigenes_theme_lesen(DATEI)["monochrome"])
zu_mono = ["down"] * len(fm.THEME_FARBFELDER)
f = editor_laufen_lassen(zu_mono + ["right", "down", "ok"], datei=DATEI)
check("er steht danach andersherum",
      bool(fm.eigenes_theme_lesen(DATEI)["monochrome"]) != vor_mono)

# ---------------------------------------------------------------------------
print()
print("Test 7: er passt auf die Roehre UND auf HDMI")
# ---------------------------------------------------------------------------
# Gezeichnet wird in einen Puffer fester Groesse - schreibt der
# Editor darueber hinaus, fliegt hier eine Ausnahme statt auf dem
# Geraet ein zerrissenes Bild.
for name, b, h in (("CRT 320x240", 320, 240),
                   ("CRT 640x480", 640, 480),
                   ("HDMI 1920x1080", 1920, 1080)):
    try:
        editor_laufen_lassen(["down", "right", "down", "ok", "back"],
                             hoehe=h, breite=b, datei=DATEI)
        ok = True
    except Exception as e:                               # noqa: BLE001
        ok = False
        print("    Ausnahme:", type(e).__name__, e)
    check("%-16s zeichnet ohne Fehler" % name, ok)

# ---------------------------------------------------------------------------
print()
print("Test 8: die Vorschau benutzt NICHT die globalen Farben")
# ---------------------------------------------------------------------------
# Das ist die Zusage aus Punkt 1, hier am Quelltext festgehalten:
# _theme_vorschau() liest ausschliesslich aus stand.
quelle = io.open(os.path.join(_REPO, "frontend", "frontend.py"),
                 encoding="utf-8").read()
i = quelle.index("    def _theme_vorschau(self")
rumpf = quelle[i:]
rumpf = rumpf[:rumpf.index("\n    def ")]
code = "\n".join(z for z in rumpf.splitlines()
                 if not z.strip().startswith("#"))
for glob in ("C_BG", "C_PANEL", "C_TEXT", "C_DIM", "C_TITLE", "C_ACCENT"):
    check("die Vorschau nimmt %s aus stand, nicht global" % glob,
          ('stand["%s"]' % glob) in code
          and not any(z.strip().endswith(", %s)" % glob)
                      for z in code.splitlines()))
check("bei zu wenig Platz zeichnet sie gar nichts",
      "return" in code.split("if w <")[1][:120])

shutil.rmtree(tmp, ignore_errors=True)
fm.THEME_EIGEN_FILE = _ALTE_DATEI
fm.THEME_FILE = _ALTE_WAHL

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
