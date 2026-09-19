#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Die Installer muessen alles mitnehmen, was zum Programm gehoert -
und nichts, was dem Nutzer gehoert (Build 161).

DER VORFALL

Auf dem Geraet stand monatelang:

    "build_id": "2026-09-19-153"

waehrend laengst Build 159 lief. Die Kopierzeilen der Installer nehmen
*.py, *.sh und *.html - JSON war nie dabei. LATEST_BUILD.json kam
damit nie auf die Karte.

Funktional war das harmlos (der Update-Hinweis vergleicht gegen eine
eigene Zustandsdatei, nicht gegen diese). Trotzdem hat es Schaden
angerichtet: bei einer Fehlersuche sah die Datei aus wie eine Auskunft
ueber den installierten Stand, war aber keine - und die Messung, die
darauf aufbaute, ging ins Leere. Eine Datei, die falsche Auskunft
gibt, ist schlimmer als gar keine.

DIE ANDERE RICHTUNG IST GENAUSO WICHTIG

Im selben Ordner liegen zur Laufzeit erzeugte Dateien des Nutzers:

    games_cache.json      der Scan-Zwischenspeicher
    stream_config.json    Einstellungen des Stream-Overlays
    keymap_custom.json    die eigene Tastenbelegung

Ein pauschales "*.json" waere deshalb der falsche Fix: es wuerde diese
Dateien in dem Moment mit ueberschreiben, in dem jemand eine
gleichnamige ins Repo legt. Der Test prueft beide Richtungen.

Ausfuehren:
    python3 tools/test_installer_dateien.py
"""
import io
import os
import re
import sys

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


INSTALLER = [
    "Scripts/Frontend_Install.sh",
    "Scripts/Frontend_Install_Remote.sh",
    "Scripts/Frontend_Install_Offline.sh",
]

# Dateien, die das FRONTEND ausliefert und die deshalb mitmuessen.
GEHOERT_ZUM_PROGRAMM = ["LATEST_BUILD.json"]

# Dateien, die dem NUTZER gehoeren und die ein Installer niemals
# ueberschreiben darf.
GEHOERT_DEM_NUTZER = ["games_cache.json", "stream_config.json",
                      "keymap_custom.json"]

# ---------------------------------------------------------------------------
print("Test 1: jeder Installer nimmt LATEST_BUILD.json mit")
# ---------------------------------------------------------------------------
quellen = {}
for rel in INSTALLER:
    pfad = os.path.join(_REPO, rel)
    if not os.path.exists(pfad):
        check("%s existiert" % rel, False)
        continue
    quellen[rel] = io.open(pfad, encoding="utf-8").read()
    for datei in GEHOERT_ZUM_PROGRAMM:
        check("%-38s kopiert %s" % (os.path.basename(rel), datei),
              datei in quellen[rel])

# ---------------------------------------------------------------------------
print()
print("Test 2: kein pauschales *.json")
# ---------------------------------------------------------------------------
# Das waere der naheliegende, aber falsche Fix - siehe Kopf.
for rel, text in quellen.items():
    treffer = re.findall(r"frontend/\*\.json", text)
    check("%-38s benutzt kein Sammelmuster" % os.path.basename(rel),
          not treffer, str(treffer))

# ---------------------------------------------------------------------------
print()
print("Test 3: die Dateien des Nutzers werden nirgends angefasst")
# ---------------------------------------------------------------------------
for rel, text in quellen.items():
    for datei in GEHOERT_DEM_NUTZER:
        # Erwaehnen duerfen sie die Datei (z.B. zum Sichern oder
        # Aufraeumen) - kopieren nicht.
        kopiert = re.search(r"cp\b[^\n]*" + re.escape(datei), text)
        check("%-38s kopiert %s NICHT"
              % (os.path.basename(rel), datei), not kopiert,
              kopiert.group(0)[:60] if kopiert else "")

# ---------------------------------------------------------------------------
print()
print("Test 4: die Datei im Repo ist gueltig und aktuell benannt")
# ---------------------------------------------------------------------------
import json                                              # noqa: E402
lb = os.path.join(_REPO, "frontend", "LATEST_BUILD.json")
check("LATEST_BUILD.json liegt im Repo", os.path.exists(lb))
if os.path.exists(lb):
    daten = json.loads(io.open(lb, encoding="utf-8").read())
    check("hat build_id und summary",
          bool(daten.get("build_id")) and bool(daten.get("summary")))
    # Dieselbe Form, die check_for_build_update() erwartet.
    check("build_id sieht aus wie JJJJ-MM-TT-Nr",
          bool(re.match(r"^\d{4}-\d{2}-\d{2}-\d+$", daten.get("build_id", ""))),
          daten.get("build_id", ""))
    check("die Zusammenfassung ist keine leere Floskel",
          len(daten.get("summary", "")) > 40,
          "%d Zeichen" % len(daten.get("summary", "")))

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
