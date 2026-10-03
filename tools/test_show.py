#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""--show: der Bericht statt des Messgeraets (Build 231).

WUNSCH DES NUTZERS: "kann man ein zweites benchmark machen was die
funktionen einstellmoeglichkeiten design und so zeigt auch wie schnell
das scrollen mittlerweile ist? als vorfuehrung quasi?"

DIE EINE GEFAHR, UM DIE HERUM DIESER TEST GEBAUT IST: eine von Hand
gepflegte Funktionsliste. So eine Liste ist nach drei Builds falsch,
und zwar still - sie behauptet dann Dinge ueber ein Frontend, das
anders aussieht. Deshalb darf in fe/show.py keine stehen; alles muss
aus dem gelesen werden, was das Frontend ohnehin weiss. Test 2 sieht
genau danach.

DIE ZWEITE GEFAHR ist dieselbe wie bei Abschnitt J des Bench: zwei
Fassungen desselben Scrollschritts. Genau daran ist J in Build 218
gescheitert (gemessen wurde der volle Neuaufbau statt des leichten
Pfads, 132,87 ms statt des echten Schritts). --show misst deshalb mit
DERSELBEN Funktion - Test 3 prueft, dass es wirklich dieselbe ist.

Ausfuehren:
    python3 tools/test_show.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H          # noqa: E402

import fe.show as SHOW        # noqa: E402
import fe.bench as BENCH      # noqa: E402
import fe.menu as MENU        # noqa: E402
import fe.masken as MASKEN    # noqa: E402
import fe.schriften as SCHRIFTEN  # noqa: E402
import fe.settings as S       # noqa: E402

fails = []
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def check(name, ok, info=""):
    print(("  OK   " if ok else "  FEHL ") + name
          + (("  " + str(info)) if info else ""))
    if not ok:
        fails.append(name)


# ---------------------------------------------------------------------------
print("Test 1: der Bericht laeuft durch - ohne Framebuffer, ohne Absturz")
# ---------------------------------------------------------------------------
# Auf dem Pruefstand gibt es weder Bildspeicher noch Spiele. Genau das
# ist der Fall, in dem so ein Bericht gern mit einer Ausnahme endet -
# und ein Bericht, der abstuerzt, ist schlimmer als keiner.
class LeeresFrontend(object):
    fb = None
    cats = []
    page = 0
    cat_i = 0
    item_i = 0


zeilen = []
_echt_print = __builtins__["print"] if isinstance(__builtins__, dict) \
    else __builtins__.print


def _still(*a, **k):
    pass


import builtins                                          # noqa: E402
builtins.print = _still
try:
    text = SHOW.lauf(LeeresFrontend(), None, __import__("fe.art",
                                                        fromlist=["x"]),
                     S, MENU, MASKEN, SCHRIFTEN, BENCH, startdauer=1.5)
finally:
    builtins.print = _echt_print

check("er liefert Text zurueck", bool(text) and len(text) > 500,
      "%d Zeichen" % len(text))
check("und endet sauber", text.rstrip().endswith("="))
for ueberschrift in ("DEINE SAMMLUNG", "WIE ES AUSSEHEN KANN",
                     "WAS SICH EINSTELLEN LAESST", "WIE SCHNELL ES SCROLLT",
                     "WO WAS LIEGT"):
    check("Abschnitt '%s' ist da" % ueberschrift, ueberschrift in text)
check("ohne Framebuffer wird das Tempo uebersprungen, nicht gerechnet",
      "kein Framebuffer" in text,
      "ein Bericht, der abstuerzt, ist schlimmer als keiner")
check("die Startdauer steht drin", "1.5 s" in text, )
check("keine Zeile ist unangenehm lang",
      max(len(z) for z in text.splitlines()) <= 110,
      "max %d - das soll man vorlesen koennen"
      % max(len(z) for z in text.splitlines()))

# ---------------------------------------------------------------------------
print()
print("Test 2: KEINE von Hand gepflegte Funktionsliste")
# ---------------------------------------------------------------------------
# Das ist der eigentliche Inhalt dieses Tests. Eine Liste, die jemand
# per Hand fuehrt, ist nach drei Builds falsch - und sie behauptet dann
# Dinge ueber ein Frontend, das anders aussieht.
quelle = open(os.path.join(_REPO, "frontend", "fe", "show.py"),
              encoding="utf-8").read()
check("die Einstellungen kommen aus dem Systemmenue",
      "MENU.system_items()" in quelle,
      "also genau die Liste, die der Nutzer sieht")
check("die Ansichten aus den Einstellungen", "S.ANSICHTEN" in quelle)
check("die Farbschemata aus dem Menuemodul", "THEME_NAMES_DE" in quelle)
check("die Masken werden GEZAEHLT, nicht aufgezaehlt",
      "MASKEN.BAUM.zaehlen(" in quelle)
check("die Schriften ebenso", "SCHRIFTEN.BAUM.zaehlen(" in quelle)
check("der Bestand kommt aus dem laufenden Frontend",
      'getattr(fe, "cats"' in quelle)

# Die Probe aufs Exempel: der Bericht muss Eintraege nennen, die es im
# echten Systemmenue auch gibt.
baum = MENU.system_items()
namen = []


def _sammeln(knoten, tiefe=0):
    if tiefe > 4 or not isinstance(knoten, dict):
        return
    for _n, unter in (knoten.get("folders", {}) or {}).items():
        _sammeln(unter, tiefe + 1)
    for e in (knoten.get("items", ()) or ()):
        namen.append(str(e[0]).split(" -> ")[0])


_sammeln(baum)
check("das Systemmenue hat ueberhaupt Eintraege", len(namen) > 20,
      "%d" % len(namen))
fehlend = [n for n in namen[:25] if n[:30] not in text]
check("und sie stehen im Bericht", not fehlend,
      "%r fehlt" % (fehlend[:2],))

# ---------------------------------------------------------------------------
print()
print("Test 3: DERSELBE Scrollschritt wie im Bench")
# ---------------------------------------------------------------------------
# Zwei Fassungen desselben Schritts waeren zwei Gelegenheiten
# auseinanderzulaufen. Genau daran ist Abschnitt J in Build 218
# gescheitert: gemessen wurde der volle Neuaufbau statt des leichten
# Pfads - 132,87 ms statt des echten Schritts.
check("der Schritt steht EINMAL da", hasattr(BENCH, "schritt_funktion"))
check("und die Fensterspanne auch", hasattr(BENCH, "fenster_spanne"))
check("--show benutzt beide",
      "BENCH.schritt_funktion(fe, seite)" in quelle
      and "BENCH.fenster_spanne(fe, seite)" in quelle)
qb = open(os.path.join(_REPO, "frontend", "fe", "bench.py"),
          encoding="utf-8").read()
_j = qb.split("def _abschnitt_j")[1]
check("und Abschnitt J ebenfalls",
      "schritt_funktion(fe, seite)" in _j
      and "fenster_spanne(fe, seite)" in _j,
      "sonst misst der Bericht etwas anderes als das Messgeraet")
check("niemand baut den Schritt noch ein zweites Mal",
      "_draw_navigate_cats" not in quelle
      and "_draw_navigate_items" not in quelle,
      "fe/show.py darf ihn nur BENUTZEN")

# Der leichte Pfad muss wirklich zuerst versucht werden - das war der
# Fehler von Build 218.
_sf = qb.split("def schritt_funktion")[1].split("\ndef ")[0]
check("erst der leichte Pfad, dann der volle Aufbau",
      _sf.index("_draw_navigate_cats") < _sf.index("fe.draw()"),
      "sonst wird der volle Neuaufbau gemessen")
check("und die Fensterspanne haelt zwei Zeilen Rand",
      "max(2, min(fenster - 2, gesamt - 1))"
      in qb.split("def fenster_spanne")[1].split("\ndef ")[0],
      "der leichte Pfad verlangt ALTE und NEUE Zeile im Fenster")

# ---------------------------------------------------------------------------
print()
print("Test 4: der Aufruf ist verdrahtet und sagt sich an")
# ---------------------------------------------------------------------------
qf = open(H.FRONTEND_PY, encoding="utf-8", errors="replace").read()
check("--show steht in der Optionsliste", '"--show":' in qf)
check("und wird auch ausgefuehrt", 'if "--show" in sys.argv:' in qf)
check("der Bericht wird zusaetzlich geschrieben",
      "SHOW_AUSGABE" in qf and "/tmp/dragend_show.txt" in qf)
_zweig = qf.split('if "--show" in sys.argv:')[1].split("\n        _fe.run()")[0]
check("danach wird beendet, nicht weitergestartet",
      "_fe._beenden()" in _zweig and "sys.exit(0)" in _zweig,
      "ein Bericht soll berichten und dann aufhoeren")

# DIE OPTIONSPRUEFUNG GANZ VORN (Build 231, Nutzermeldung zu 230: die
# Meldung kam erst hinter "Keine andere Instanz aktiv - starte
# Framebuffer/Eingaben ..."). Fuer ein blosses --help wurde also die
# Einzelinstanz-Sperre geholt und der halbe Start durchlaufen.
check("die Optionspruefung steht VOR der ersten Startmeldung",
      qf.index("_unbekannt = [a for a in sys.argv")
      < qf.index('print("Frontend-Start: initialisiere ...")'),
      "sonst holt ein --help die Einzelinstanz-Sperre")

print()
if fails:
    print("FEHLGESCHLAGEN (%d):" % len(fails))
    for f in fails:
        print("  - %s" % f)
    sys.exit(1)
print("Alles in Ordnung.")
