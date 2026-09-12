#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft, WANN und WOHIN der Vorauslader angesetzt wird (Build 104).

NUTZER-RUECKMELDUNG: "Wenn ich beim Scrollen schnell die Richtung
wechsle, haengt es kurz, und wenn ich Ordner hin und her wechsle auch."

Beides zeigte auf dieselbe Stelle, und beides waren Ueberbleibsel aus
der Zeit, als das Vorrechnen noch im Hauptprozess lief:

  1. Der Vorauslader wartete eine volle Sekunde Ruhe (PREFETCH_SETTLE).
     Der Grund dafuer war richtig - solange das Vorrechnen dem Zeichnen
     Rechenzeit wegnahm, war jede Sekunde Wartezeit ein Schutz. Seit
     Build 102 rechnet er in einem eigenen Prozess auf dem zweiten Kern;
     der Schutz wurde zum Nachteil. Wer schnell scrollt und umdreht,
     kommt nie eine Sekunde zur Ruhe - es wurde also gar nichts
     vorgerechnet.
  2. Vorausgeschaut wird nur in EINE Richtung (20 Eintraege voraus, 6
     zurueck). Wer umdreht, hat die vorgerechneten Cover hinter sich -
     und neu gezielt wurde erst nach der naechsten vollstaendigen
     Ruhephase.
  3. _prefetch_neighbor_covers() dekodierte Cover im HAUPTTHREAD. Sie
     entstand, bevor es den Vorauslader gab, konnte nur roh dekodieren
     (die Zielgroesse haengt vom Titeltext ab) und lief ausgerechnet in
     der Ruhephase, in der als naechstes ein Tastendruck kommt.

Ausfuehren:
    python3 tools/test_vorladen_richtung.py
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)

import _harness as H                                    # noqa: E402

fm = H.fm
sys.path.insert(0, os.path.join(_REPO, "frontend"))
import fe.prewarm as P                                  # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


QUELLE = open(os.path.join(_REPO, "frontend", "frontend.py"),
              encoding="utf-8", errors="replace").read()

print("Test 1: die Wartezeit ist weg")
check("PREWARM_SETTLE existiert", hasattr(fm, "PREWARM_SETTLE"))
check("und liegt unter COVER_SETTLE",
      getattr(fm, "PREWARM_SETTLE", 99) < fm.COVER_SETTLE,
      "(%.2f gegen %.2f)" % (getattr(fm, "PREWARM_SETTLE", -1),
                             fm.COVER_SETTLE))
# Der Sinn der Reihenfolge: der Arbeitsprozess soll seine Auftraege
# schon haben, wenn der Hauptthread gleich darauf das Cover-Panel
# zeichnet - dann rechnet er die Nachbarn auf dem zweiten Kern,
# WAEHREND gezeichnet wird.
check("die alte Sekunde (PREFETCH_SETTLE) ist raus",
      "PREFETCH_SETTLE = " not in QUELLE)
_i_prewarm = QUELLE.find("self._prewarm_anstossen()")
_i_settle = QUELLE.find("ART._deferred_something = False")
check("der Vorauslader wird VOR dem Nachzeichnen angesetzt",
      0 < _i_prewarm < _i_settle,
      "(Positionen %d / %d)" % (_i_prewarm, _i_settle))

print("Test 2: _prefetch_neighbor_covers() ist raus")
check("keine Funktion mehr",
      "def _prefetch_neighbor_covers" not in QUELLE)
check("und kein Aufruf mehr",
      "self._prefetch_neighbor_covers()" not in QUELLE)
check("das Zeitbudget dafuer ebenfalls raus",
      "PREFETCH_BUDGET = " not in QUELLE)

print("Test 3: ein Richtungswechsel zielt neu")
# Der Kern der Beschwerde. auftraege_bauen() schaut in Scrollrichtung
# 20 Eintraege voraus und nur 6 zurueck - die Auftragsliste MUSS sich
# also sichtbar unterscheiden, je nachdem, wohin man gerade scrollt.
# Waere sie in beiden Richtungen gleich, brauchte man auch nicht neu zu
# zielen, und die ganze Aenderung waere wirkungslos.
eintraege = [("Spiel %d" % i, "game", ("/f/%d.sfc" % i,)) for i in range(200)]


def masse(it):
    return ("/art/%s.art" % it[0], 300, 420)


runter = P.auftraege_bauen(eintraege, 100, masse, vorwaerts=True)
hoch = P.auftraege_bauen(eintraege, 100, masse, vorwaerts=False)
check("runter merkt sich mehr voraus als zurueck",
      sum(1 for p, _w, _h in runter if int(p.split()[-1].split(".")[0]) > 100)
      > len(runter) // 2)
check("hoch zielt in die andere Richtung",
      sum(1 for p, _w, _h in hoch if int(p.split()[-1].split(".")[0]) < 100)
      > len(hoch) // 2)
gemeinsam = set(runter) & set(hoch)
check("die beiden Listen sind grossteils verschieden",
      len(gemeinsam) < len(runter) // 2,
      "(%d von %d gemeinsam)" % (len(gemeinsam), len(runter)))

print("Test 4: der Wechsel loest das Neuzielen wirklich aus")
# Jetzt am echten Leerlauf-Zweig von next_action(), nicht am Quelltext:
# nach einem Richtungswechsel muss neu vorgemerkt werden, AUCH wenn fuer
# diese Ruhephase bereits einmal vorgemerkt wurde. Genau daran hing es -
# _prefetched_done blockierte den zweiten Anlauf.
H.set_screen(1920, 1080)
f = H.make_frontend(page=1)
node = f._current_node()
node["items"] = [(H.TITLES[i % len(H.TITLES)] + " %d" % i, "game",
                  ("/f/%d.sfc" % i, ".sfc", "SNES", None, None))
                 for i in range(200)]
node.pop("_display_items_cache", None)
f.item_i = 100
f.scroll = 90
f.draw_page_items(flip=False)

angesetzt = []
f._prewarm_anstossen = lambda: angesetzt.append(f._last_scroll_dir)
f.inp.flush = lambda: None


def leerlauf(runden=3):
    """Den Leerlauf-Zweig von next_action() laufen lassen und danach
    mit einer Eingabe wieder herauskommen."""
    rest = [None] * runden + ["down"]

    def lesen(timeout=None):
        H.NOW[0] += max(timeout or 0.05, 0.05)
        return rest.pop(0) if rest else "down"
    f.inp.read_action = lesen
    return f.next_action()


f._last_scroll_dir = 1
f._prewarm_dir = 1
f._prefetched_done = False
leerlauf()
check("in der Ruhe wird vorgemerkt", angesetzt == [1],
      "(%r)" % (angesetzt,))

# Jetzt der Fall aus der Beschwerde: fuer diese Ruhephase wurde schon
# vorgemerkt, und dann dreht der Nutzer um.
angesetzt[:] = []
f._prefetched_done = True
f._last_scroll_dir = 1
leerlauf()
check("ohne Wechsel wird NICHT erneut vorgemerkt", angesetzt == [],
      "(%r)" % (angesetzt,))

angesetzt[:] = []
f._last_scroll_dir = -1          # umgedreht
leerlauf()
check("nach dem Richtungswechsel wird neu gezielt", angesetzt == [-1],
      "(%r)" % (angesetzt,))
check("und die Richtung ist danach vermerkt", f._prewarm_dir == -1,
      "(%r)" % (f._prewarm_dir,))

angesetzt[:] = []
# Wieder "innerhalb derselben Ruhephase": leerlauf() endet mit einer
# Eingabe, und eine Eingabe setzt _prefetched_done zurueck - das ist
# richtig so (nach jedem Tastendruck darf neu vorgemerkt werden). Fuer
# diese Pruefung geht es um den Fall OHNE neue Eingabe: derselbe
# Ruhemoment, dieselbe Richtung, also nichts zu tun.
f._prefetched_done = True
leerlauf()
check("in derselben Ruhephase kein Dauerfeuer", angesetzt == [],
      "(%r)" % (angesetzt,))

print()
if fails:
    print("FEHLGESCHLAGEN (%d):" % len(fails))
    for f_ in fails:
        print("  -", f_)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
