#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Eine Symlink-Schleife darf das Einlesen nicht aufhaengen (Build 200).

DER ANLASS

Degauss hat in v0.9.0 genau das reparieren muessen: "Arcade indexing now
excludes top-level cores support directory, preventing symlink loops from
aborting library rebuilds". Beim Nachsehen stand es bei uns SCHLECHTER,
und das ist der eigentliche Fund - nicht die Zeile aus den fremden
Release-Notes:

  - Die OBERE Ebene ist seit langem abgesichert (seen_roots mit realpath
    in _scan_system()).
  - Der rekursive Abstieg war es gar nicht. _scan_folder_tree() steigt in
    jeden Ordner, den os.path.isdir() bejaht - und isdir() FOLGT
    Symlinks.

Ein Link, der nach oben zeigt (games/SNES/alles -> /media/fat/games),
laesst das Einlesen also kreisen, bis Python mit RecursionError
abbricht. Beim Nutzer mit 97.000 Eintraegen trifft das den
unangenehmsten Moment ueberhaupt: den Neuaufbau der Bibliothek.

WAS DIESER TEST ABSICHERT - und zwar an einer ECHTEN Schleife auf der
Platte, nicht an einer Attrappe:

  - dass eine Schleife das Einlesen nicht aufhaengt und nicht abbricht,
  - dass die Spiele DIESSEITS der Schleife trotzdem alle gefunden werden
    (ein Schutz, der die halbe Sammlung verschluckt, waere schlimmer als
    das Problem),
  - dass ein Ordner, der voellig legitim ZWEIMAL auftaucht, weiterhin
    zweimal gelesen wird - deshalb wird gegen die VORFAHREN geprueft und
    nicht gegen "schon mal gesehen",
  - dass eine uferlose Verschachtelung bei SCAN_MAX_TIEFE endet,
  - dass jede uebersprungene Stelle EINMAL im Log steht,
  - und dass der Normalfall keine teuren realpath()-Aufrufe bezahlt.

Ausfuehren:
    python3 tools/test_scan_schleife.py
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
sys.path.insert(0, os.path.join(_REPO, "frontend"))
import fe.scan as SC                                     # noqa: E402

fails = []
meldungen = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


SC.LOG = lambda s: meldungen.append(s)

EXT = {".sfc": "SNES"}


def spiele(node):
    """Alle Spieltitel eines Knotens, ueber alle Ebenen."""
    raus = [i[0] for i in node.get("items", ())]
    for unter in node.get("folders", {}).values():
        raus.extend(spiele(unter))
    return raus


# ---------------------------------------------------------------------------
print("Test 1: eine ECHTE Schleife haengt das Einlesen nicht auf")
# ---------------------------------------------------------------------------
basis = tempfile.mkdtemp(prefix="dragend_schleife_")
try:
    games = os.path.join(basis, "games")
    snes = os.path.join(games, "SNES")
    tief = os.path.join(snes, "Hacks")
    os.makedirs(tief)
    for p, n in ((snes, "Super Mario World"), (tief, "Kaizo")):
        io.open(os.path.join(p, n + ".sfc"), "w").write("x")
    # Der Link, um den es geht: er zeigt auf einen eigenen Vorfahren.
    os.symlink(games, os.path.join(snes, "alles"))

    del meldungen[:]
    try:
        node = SC._scan_folder_tree(snes, "SNES", "SNES", EXT)
        geplatzt = None
    except RecursionError as e:
        node, geplatzt = None, e
    except Exception as e:                               # noqa: BLE001
        node, geplatzt = None, e
    check("es bricht nicht ab", geplatzt is None, repr(geplatzt))
    if node is not None:
        gef = spiele(node)
        check("die Spiele diesseits der Schleife sind alle da",
              sorted(gef) == ["Kaizo", "Super Mario World"], sorted(gef))
        check("und die Schleife steht im Log",
              any("Symlink-Schleife" in m for m in meldungen), meldungen)

    # ---------------------------------------------------------------
    print()
    print("Test 2: ein legitimer Doppelgaenger wird NICHT verschluckt")
    # ---------------------------------------------------------------
    # Das ist der Grund, gegen die VORFAHREN zu pruefen und nicht gegen
    # "schon mal gesehen": ein zweiter Link auf dieselbe Sammlung ist
    # keine Schleife, sondern ein Wunsch. Eine globale Menge haette hier
    # still die Haelfte weggelassen.
    extra = os.path.join(basis, "Sammlung")
    os.makedirs(extra)
    io.open(os.path.join(extra, "Zelda.sfc"), "w").write("x")
    zwei = os.path.join(basis, "zwei")
    os.makedirs(zwei)
    os.symlink(extra, os.path.join(zwei, "A"))
    os.symlink(extra, os.path.join(zwei, "B"))
    del meldungen[:]
    node2 = SC._scan_folder_tree(zwei, "SNES", "SNES", EXT)
    check("beide Wege werden gelesen", spiele(node2) == ["Zelda", "Zelda"],
          spiele(node2))
    check("und es wird nichts als Schleife gemeldet",
          not [m for m in meldungen if "Schleife" in m], meldungen)

    # ---------------------------------------------------------------
    print()
    print("Test 3: uferlose Verschachtelung endet bei SCAN_MAX_TIEFE")
    # ---------------------------------------------------------------
    # Zweiter Guertel: auch ohne Symlink soll kein Baum den
    # Rekursionsdeckel von Python erreichen.
    tiefbau = os.path.join(basis, "tief")
    p = tiefbau
    for i in range(SC.SCAN_MAX_TIEFE + 6):
        p = os.path.join(p, "u%d" % i)
    os.makedirs(p)
    io.open(os.path.join(p, "Ganztief.sfc"), "w").write("x")
    del meldungen[:]
    node3 = SC._scan_folder_tree(tiefbau, "SNES", "SNES", EXT)
    check("es bricht nicht ab", node3 is not None)
    check("und die Begrenzung steht im Log",
          any("zu tief" in m for m in meldungen), meldungen[:3])
    check("der Deckel ist nicht zu knapp", SC.SCAN_MAX_TIEFE >= 16,
          "%d - echte Sammlungen sind verschachtelt" % SC.SCAN_MAX_TIEFE)

    # ---------------------------------------------------------------
    print()
    print("Test 4: jede Stelle wird nur EINMAL gemeldet")
    # ---------------------------------------------------------------
    del meldungen[:]
    SC._SCAN_GEMELDET.clear()
    for _ in range(3):
        SC._scan_folder_tree(snes, "SNES", "SNES", EXT)
    check("dreimal eingelesen, eine Meldung je Stelle",
          len([m for m in meldungen if "Symlink-Schleife" in m]) == 1,
          "%d Meldungen" % len([m for m in meldungen
                                if "Symlink-Schleife" in m]))

    # ---------------------------------------------------------------
    print()
    print("Test 5: der Normalfall bezahlt kein realpath()")
    # ---------------------------------------------------------------
    # realpath() kostet mehrere Systemaufrufe je Ordner. Gebraucht wird
    # es NUR fuer Symlinks - ein gewoehnlicher Unterordner kann keine
    # Schleife bauen, sein echter Pfad ist der des Vaters plus Name.
    # Ohne diese Unterscheidung waere der Schutz bei 97.000 Eintraegen
    # selbst der neue Bremsklotz.
    sauber = os.path.join(basis, "sauber")
    for i in range(12):
        u = os.path.join(sauber, "Ordner%d" % i)
        os.makedirs(u)
        io.open(os.path.join(u, "Spiel%d.sfc" % i), "w").write("x")
    _echt = os.path.realpath
    zaehler = [0]

    def _gezaehlt(p, *a, **k):
        zaehler[0] += 1
        return _echt(p, *a, **k)

    os.path.realpath = _gezaehlt
    try:
        node5 = SC._scan_folder_tree(sauber, "SNES", "SNES", EXT)
    finally:
        os.path.realpath = _echt
    check("alle Spiele gefunden", len(spiele(node5)) == 12,
          len(spiele(node5)))
    check("und realpath nur EINMAL gerufen (fuer den Startordner)",
          zaehler[0] <= 1,
          "%d Aufrufe bei 12 Unterordnern" % zaehler[0])
finally:
    shutil.rmtree(basis, ignore_errors=True)

# ---------------------------------------------------------------------------
print()
print("Test 6: die Begruendung steht im Quelltext")
# ---------------------------------------------------------------------------
quelle = io.open(os.path.join(_REPO, "frontend", "fe", "scan.py"),
                 encoding="utf-8").read()
check("warum gegen die Vorfahren geprueft wird, nicht gegen 'gesehen'",
      "VORFAHREN" in quelle and "schon mal gesehen" in quelle)
check("dass isdir() Symlinks folgt, ist festgehalten",
      "isdir() folgt Symlinks" in quelle
      or "isdir() FOLGT" in quelle)
check("und woher der Anlass kam", "Degauss" in quelle)

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
