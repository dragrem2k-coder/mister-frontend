#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Der RA-Abruf beim Start laeuft genau einmal, und im Hintergrund.

WORUM ES GEHT (Build 187)

Im Quelltext stand ein langer Kommentar, der erklaert, warum der
RetroAchievements-Abruf aus dem Start herausgenommen und in einen
Hintergrund-Thread verlegt wurde: er blockierte bis zu 3,5 Sekunden,
und der Bildschirm blieb in dieser Zeit dunkel.

Nur: die alte, synchrone Fassung stand vierzig Zeilen darueber
weiterhin da. Beide liefen. Die Verbesserung, die der Kommentar
beschreibt, hat nie stattgefunden - der Start wartete weiter, und
derselbe Abruf lief anschliessend ein zweites Mal im Thread.

Aufgefallen ist das nicht beim Lesen, sondern beim Vermessen: in der
Startmarke "Musik, RA-Abruf angestossen" standen 797 ms auf einem
Geraet OHNE Netz - dort scheitert der Abruf sofort. Mit Netz sind es
bis zu 3,5 Sekunden.

Ein Kommentar ist keine Absicherung. Dieser Test ist eine.

Ausfuehren:
    python3 tools/test_start_ra_einmal.py
"""
import io
import os
import sys

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
sys.path.insert(0, _HIER)

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


quelle = io.open(os.path.join(_REPO, "frontend", "frontend.py"),
                 encoding="utf-8").read()

# Nur der Rumpf von Frontend.__init__ - anderswo (Menuepunkt "RA-Daten
# neu holen", Trophaeenraum) ist ein synchroner Abruf voellig richtig.
_i = quelle.index("class Frontend")
_init = quelle[quelle.index("    def __init__(self", _i):]
_init = _init[:_init.index("\n    def ", 10)]

# ---------------------------------------------------------------------------
print("Test 1: im Start steht der Abruf genau einmal")
# ---------------------------------------------------------------------------
# Kommentarzeilen zaehlen nicht mit - die Begruendung, warum die alte
# Fassung entfernt wurde, zitiert den Aufruf absichtlich.
_code = "\n".join(z for z in _init.splitlines()
                  if not z.lstrip().startswith("#"))
n = _code.count("fetch_ra_progress_bounded(")
check("genau ein Aufruf im Startpfad", n == 1, "%d gefunden" % n)

# ---------------------------------------------------------------------------
print()
print("Test 2: und er steht im Hintergrund-Thread")
# ---------------------------------------------------------------------------
check("es gibt die Thread-Fassung", "_initial_ra_fetch" in _code)
_thread = _code[_code.index("def _initial_ra_fetch"):]
_thread = _thread[:_thread.index("threading.Thread")]
check("der eine Aufruf liegt darin",
      "fetch_ra_progress_bounded(" in _thread,
      "sonst blockiert er den Start wieder")
check("der Thread wird auch gestartet",
      "threading.Thread(target=_initial_ra_fetch" in _code)
check("und als daemon, damit er das Beenden nicht aufhaelt",
      "daemon=True" in _code[_code.index("_initial_ra_fetch"):
                             _code.index("_initial_ra_fetch") + 900])

# ---------------------------------------------------------------------------
print()
print("Test 3: die Ergebnisse werden nachgetragen")
# ---------------------------------------------------------------------------
# Ohne das waere der Abruf zwar schnell, aber wirkungslos - die
# Erfolgsjaeger-Kategorie taucht dann nie auf.
check("es gibt das Ablagefach fuer das Ergebnis",
      "_ra_pending_result" in _code)
check("und jemanden, der es abholt",
      "_maybe_apply_pending_ra_data" in quelle)

# ---------------------------------------------------------------------------
print()
print("Test 4: die entfernte Fassung ist erklaert, nicht nur weg")
# ---------------------------------------------------------------------------
# Ein stilles Loeschen waere hier das Schlechteste: der naechste, der
# den langen Kommentar darunter liest, wuerde sich fragen, wo der
# synchrone Abruf geblieben ist - und ihn womoeglich wieder einbauen.
check("im Quelltext steht, was dort stand und warum es weg ist",
      "BIS BUILD 187" in _init and "3,5 Sekunden" in _init)

# ---------------------------------------------------------------------------
print()
print("Test 5: der Start misst sich feiner als vorher")
# ---------------------------------------------------------------------------
# Die 797 ms standen in EINER Marke, die vier verschiedene Dinge
# zusammenfasste. Ohne Aufteilung faengt die naechste Suche wieder bei
# null an.
check("der Metadaten-Vorwaermer hat eine eigene Marke",
      "davon Metadaten-Vorwaermer angestossen" in quelle)

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
