#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Zwei Namen kommen nirgends mehr vor (Build 340).

NUTZERWUNSCH: ein Mitwirkender "sollte noch komplett raus, genauso
sollte [der alte Name des Zufalls-Zocks] nirgends mehr auftauchen oder
durch Zufalls-Zock ersetzen".

Die Namen stehen hier bewusst nur zusammengesetzt - sonst stuende in
diesem Test genau das, was er verbietet.

GEPRUEFT WIRD:
  1. Keine Textdatei im Repository nennt einen der Namen (Quelltext,
     Doku, Changelogs, Tests, Skripte), und keine Datei heisst so.
  2. Auch die PDFs nicht (Text per pdftotext, wenn vorhanden).
  3. Die Spuren auf der Karte: die drei Installer entfernen die alten
     Dateien; die gespielt-Liste wird umbenannt statt verloren; eine
     alte Hauptseiten-Einstellung wird verstanden.

Ausfuehren:
    python3 tools/test_namen_entfernt.py
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
sys.path.insert(0, os.path.join(_REPO, "frontend"))

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


NAME_A = "denn" + "sen"
NAME_B = "won" + "ne"                    # mit "oder" und dem Reim dahinter
KURZ = "w" + "ot"
MUSTER = re.compile(r"%s|%s[- ]oder|%s%s|(?<![A-Za-z0-9])%s(?![A-Za-z0-9])"
                    % (NAME_A, NAME_B, NAME_B, "ton" + "ne", KURZ), re.I)
TEXT = (".py", ".sh", ".yml", ".md", ".html", ".json", ".c", ".h", ".txt",
        ".bat", ".spec", ".csv", ".css", ".js")

print(__doc__.strip().split("\n")[0])
print()
# ---------------------------------------------------------------------------
print("Test 1: Textdateien und Dateinamen")
# ---------------------------------------------------------------------------
dateien = subprocess.run(["git", "ls-files"], cwd=_REPO, capture_output=True,
                         text=True).stdout.split("\n")
dateien = [d for d in dateien if d and os.path.isfile(os.path.join(_REPO, d))]
treffer = []
for d in dateien:
    if MUSTER.search(os.path.basename(d)):
        treffer.append(("Dateiname", d))
    if not d.endswith(TEXT) or d.startswith(("pc_tools/build/",
                                             "pc_tools/dist/")):
        continue
    try:
        inhalt = open(os.path.join(_REPO, d), encoding="utf-8").read()
    except (UnicodeDecodeError, OSError):
        continue
    for nr, zeile in enumerate(inhalt.split("\n"), 1):
        if MUSTER.search(zeile):
            treffer.append((d, nr))
check("%d Dateien durchsucht - kein Treffer" % len(dateien), not treffer,
      treffer[:8])

# ---------------------------------------------------------------------------
print()
print("Test 2: die PDFs")
# ---------------------------------------------------------------------------
if shutil.which("pdftotext"):
    pdf_treffer = []
    for d in dateien:
        if d.endswith(".pdf"):
            t = subprocess.run(["pdftotext", os.path.join(_REPO, d), "-"],
                               capture_output=True, text=True).stdout
            if MUSTER.search(t):
                pdf_treffer.append(d)
    check("kein PDF nennt die Namen", not pdf_treffer, pdf_treffer)
else:
    print("  --   pdftotext fehlt, Test 2 uebersprungen")

# ---------------------------------------------------------------------------
print()
print("Test 3: die Spuren auf der Karte")
# ---------------------------------------------------------------------------
for skript in ("Frontend_Install.sh", "Frontend_Install_Offline.sh",
               "Frontend_Install_Remote.sh"):
    q = open(os.path.join(_REPO, "Scripts", skript), encoding="utf-8").read()
    block = q[q.find("# BUILD 340: Dateien unter alten Namen"):]
    block = block[:block.find('_logo.art" 2>/dev/null') + 24]
    tmp = tempfile.mkdtemp(prefix="karte_")
    try:
        for unter in ("sysart", "boot_logo", "__pycache__"):
            os.makedirs(os.path.join(tmp, unter))
        alte = ["sysart/%s.art" % KURZ.upper(), "mister_%s.py" % KURZ,
                "__pycache__/mister_%s.cpython-39.pyc" % KURZ,
                "%s_games_sample.csv" % KURZ, "%s_aliases_sample.json" % KURZ,
                "boot_logo/%s86_logo.art" % NAME_A]
        bleiben = ["boot_logo/cirdan_logo.art", "sysart/ZUFALLSZOCK.art",
                   "zufallszock_played.json"]
        for n in alte + bleiben:
            open(os.path.join(tmp, n), "w").close()
        subprocess.run(["bash", "-c", block], env=dict(os.environ,
                                                       FRONTEND_DIR=tmp))
        rest = sorted(os.path.relpath(os.path.join(w, f), tmp)
                      for w, _d, fs in os.walk(tmp) for f in fs)
        check("%s entfernt die alten Dateien und laesst den Rest" % skript,
              rest == sorted(bleiben), rest)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

import mister_zufallszock as Z                           # noqa: E402
tmp = tempfile.mkdtemp(prefix="umzug_")
_alt = (Z.ZUFALLSZOCK_PLAYED_FILE, Z.LOG)
try:
    Z.LOG = lambda s: None
    alt = os.path.join(tmp, "%s_played.json" % KURZ)
    json.dump({"played": [{"system": "NES", "title": "Spiel"}]},
              open(alt, "w"))
    Z.ZUFALLSZOCK_PLAYED_FILE = os.path.join(tmp, "zufallszock_played.json")
    paare = Z.alte_dateien_umziehen(tmp)
    check("die gespielt-Liste wird umbenannt, nicht verloren",
          not os.path.exists(alt) and json.load(open(
              Z.ZUFALLSZOCK_PLAYED_FILE))["played"][0]["title"] == "Spiel"
          and len(paare) == 1, paare)
    json.dump({"played": []}, open(alt, "w"))
    check("GEGENPROBE: gibt es die neue schon, wird nichts ueberschrieben",
          Z.alte_dateien_umziehen(tmp) == [] and os.path.exists(alt)
          and json.load(open(Z.ZUFALLSZOCK_PLAYED_FILE))["played"])
finally:
    Z.ZUFALLSZOCK_PLAYED_FILE, Z.LOG = _alt
    shutil.rmtree(tmp, ignore_errors=True)

import fe.hauptseite as HS                               # noqa: E402
tmp = tempfile.mkdtemp(prefix="haupt_")
try:
    p = os.path.join(tmp, "hauptseite.json")
    alt_k = "%s_title" % KURZ
    json.dump({"aus": [alt_k], "reihenfolge": ["recent_cat", alt_k]},
              open(p, "w"))
    aus, folge = HS.laden(p)
    check("eine alte Hauptseiten-Einstellung wird verstanden",
          aus == {"zufallszock_title"}
          and folge == ["recent_cat", "zufallszock_title"], (aus, folge))
    check("und das neue Kuerzel ist das der Kategorie",
          "zufallszock_title" in HS.BESONDERE)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print()
if fails:
    print("ROT: %d Pruefung(en) fehlgeschlagen:" % len(fails))
    for f_ in fails:
        print("   - " + f_)
    sys.exit(1)
print("ALLES GRUEN")
