#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_boot_watch() protokolliert und greift NICHT ein - und warum das so
ist (Build 146/147, festgeschrieben in Build 296).

WAS HIER FRUEHER STAND, UND WARUM ES WEG MUSSTE

Diese Datei hat bis Build 296 geprueft, dass _boot_watch() ein F9
nachschickt, sobald die aktive Linux-Konsole nicht tty1 ist. Dafuer
gab es eine Nutzer-Rueckmeldung ("bin im OSD und hoere die Musik vom
Frontend") und eine plausible Erklaerung: der bootende MiSTer holt sich
die Anzeige zurueck, das Frontend zeichnet in einen Framebuffer, den
niemand sieht.

GEBAUT WURDE DAS IN BUILD 146. ENTFERNT IN BUILD 147, weil es ein
IRRTUM war. Die Begruendung steht woertlich im Docstring von
_boot_watch():

    "beim Nutzer stand die VT durchgehend auf tty1, waehrend der
    Bildschirm trotzdem MiSTers Menue zeigte. Die aktive Linux-Konsole
    sagt also NICHT, was auf dem Bildschirm landet - das entscheidet
    MiSTer fuer sich, und er schreibt es nirgendwo hin (nachgemessen:
    beim Umschalten aendert sich weder unter /sys/class/graphics noch
    in /tmp ein einziger Wert). Die Bedingung konnte deshalb nie
    zutreffen, und der Fix lief ins Leere."

DER TEST IST ABER STEHENGEBLIEBEN. Er hat ein Verhalten verlangt, das
der Code seit Build 147 bewusst NICHT mehr hat, und war deshalb im
Repo rot - zuletzt ausgeliefert wurde er mit Build 275, aufgefallen ist
es erst in Build 296, als der Arbeitsstand neu aus dem Repo geklont
werden musste. Die Konstante, auf die er sich stuetzte
(VT_NACHFASSEN_MAX), existiert gar nicht mehr; der Test brach mit einem
AttributeError ab.

DAS IST DIESELBE LEHRE WIE IN BUILD 290, nur umgekehrt: dort hat eine
Pruefung ein Nicht-Verhalten festgeschrieben, das sich als zu eng
erwies. Hier hat eine Pruefung ein Verhalten festgeschrieben, das sich
als Irrtum erwies - und als der Code korrigiert wurde, blieb der Test
auf dem Irrtum sitzen.

WAS JETZT GEPRUEFT WIRD, und zwar in der Form, die dieses Projekt
dafuer schon benutzt (siehe "der 145er-Weg ist entfernt" in
test_beenden.py): dass das Eingreifen WEG ist, dass die Begruendung
dafuer im Quelltext steht, und wo die Loesung stattdessen sitzt.

Ausfuehren:
    python3 tools/test_vt_nachfassen.py
"""
import ast
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FE_PY = os.path.join(_REPO, "frontend", "frontend.py")
fe_src = open(FE_PY, encoding="utf-8").read()

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


def koerper(quelle, name):
    """Der Koerper genau einer Funktion - per ast, nicht per
    Zeichenfenster.

    In diesem Projekt sind Zeichenfenster vierfach danebengegangen
    (test_bench, test_konsole_wache, test_startweg, test_romwacht).
    Die Antwort ist nie eine groessere Zahl."""
    baum = ast.parse(quelle)
    zeilen = quelle.split("\n")
    for knoten in ast.walk(baum):
        if isinstance(knoten, ast.FunctionDef) and knoten.name == name:
            return "\n".join(zeilen[knoten.lineno - 1:knoten.end_lineno])
    return ""


print(__doc__.strip().split("\n")[0])
print()

# ---------------------------------------------------------------- 1
print("Test 1: _boot_watch() greift nicht ein")

bw = koerper(fe_src, "_boot_watch")
check("_boot_watch() ist da", bool(bw))
# DIE ZUSAGE: es protokolliert. Nichts weiter.
check("es schreibt ins Protokoll", "LOG(" in bw)
for was, nadel in (("kein F9 mehr", "inject"),
                   ("kein Konsolenwechsel", "enter_console_mode"),
                   ("kein Griff auf die Eingaben", "grab("),
                   ("und es zeichnet nicht", "self.draw(")):
    check("%s in _boot_watch()" % was, nadel not in bw,
          "Build 147 - die Bedingung konnte nie zutreffen")

print()

# ---------------------------------------------------------------- 2
print("Test 2: die Begruendung steht im Quelltext, nicht nur hier")

# EIN KOMMENTAR IST KEINE ABSICHERUNG - aber ein ENTFERNTER Fix ohne
# Begruendung ist eine Einladung, ihn wieder einzubauen. Genau das
# sichert diese Pruefung: wer die Zeilen loescht, muss sich mit dem
# Grund befassen.
check("der Irrtum ist benannt", "ein Irrtum" in bw)
check("und die Messung dazu steht dabei",
      "weder unter /sys/class/graphics noch" in bw,
      "beim Umschalten aendert sich kein einziger Wert - das ist die "
      "Messung, die den Fix widerlegt hat")
check("und wohin die Loesung gewandert ist",
      "_konsole_sichern()" in bw)
# Die Konstante von damals darf nicht wiederauftauchen, ohne dass
# dieser Test etwas dazu sagt.
check("VT_NACHFASSEN_MAX gibt es nicht mehr",
      "VT_NACHFASSEN_MAX" not in fe_src)

print()

# ---------------------------------------------------------------- 3
print("Test 3: wo das F9 heute wirklich nachgefasst wird")

sichern = koerper(fe_src, "_konsole_sichern")
check("_konsole_sichern() ist da", bool(sichern))
check("dort wird das F9 wiederholt",
      "F9_WIEDERHOLUNGEN" in sichern and "inject" in sichern)
# BEGRENZT, kein Dauerfeuer: das war schon die Sorge von Build 146,
# und sie gilt weiter - nur an der richtigen Stelle.
check("und zwar begrenzt, nicht im Dauerfeuer",
      "_f9_wiederholt >= len(self.F9_WIEDERHOLUNGEN)" in sichern,
      "ein Frontend, das einen aus dem OSD zurueckzerrt, waere "
      "schlimmer als das Problem")
_konst = [z for z in fe_src.split("\n")
          if z.strip().startswith("F9_WIEDERHOLUNGEN")]
check("die Wiederholungen stehen als benannte Liste da",
      bool(_konst), (_konst[0].strip() if _konst else "nicht gefunden"))
# Und die Zeitgrenze von _boot_watch bleibt eine Zeitgrenze - ohne
# sie liefe das Protokollieren fuer immer.
check("_boot_watch() hoert nach einem Fenster auf",
      "BOOT_WATCH_FENSTER" in bw)

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
