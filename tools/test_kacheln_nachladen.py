#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kacheln laden nach (Build 180) - SuTes Video bei 1080p.

WAS IM VIDEO ZU SEHEN WAR

Raster, Mega Drive / Europe, 249 Eintraege, 1080p. Das Raster bleibt
fast leer. Ein Cover erscheint nur auf der Kachel, auf der man stehen
bleibt, und das nach einer halben bis zwei Sekunden. Nach einem
Seitenwechsel ist wieder alles leer. In der Galerie bleibt das grosse
Cover oft leer. Bei halber Aufloesung: nichts davon.

SuTes Bench sagte dazu: sein Geraet ist nicht langsamer. Die
Bildkette liegt auf 1-2 % bei Dragrems Werten. Es war also kein
Durchsatzproblem, sondern eines im Ablauf.

DREI FEHLER, ALLE IM CODE NACHGELESEN

1. DAS NACHZEICHNEN IM LEERLAUF ging durch den schnellen Pfad - und
   der zeichnet im Raster nur ZWEI Kacheln. Ein fertiges Cover fuer
   eine andere Kachel lag auf der Karte, wurde aber nie gemalt.

2. EINE TASTE BRACH DIE AUFTRAEGE AB, NICHT ABER DIE WARTEVERMERKE.
   Die 19 Kacheln, die der schnelle Pfad nicht neu zeichnet, fragten
   nie wieder nach. Ihre Vermerke veralteten, und warte_pruefen()
   meldete ab da dauerhaft "nachzeichnen" - die Hauptschleife
   zeichnete im Leerlauf immer wieder, ohne dass je etwas kam.

3. DIE NOTBREMSE ZOG ZU FRUEH. Sie mass zwei Sekunden ab dem
   Auftrag. Im Raster warten 21 auf einmal, die letzten sind nach
   rund fuenf Sekunden dran - die Notbremse hielt den fleissigen
   Arbeitsprozess fuer haengend und liess den ZEICHENWEG selbst
   rechnen. 100-500 ms je Kachel, in denen nichts auf Tasten
   reagiert: das Zucken.

Ausfuehren:
    python3 tools/test_kacheln_nachladen.py
"""
import io
import os
import sys

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
sys.path.insert(0, _HIER)

import _harness as H                                     # noqa: E402

fm = H.fm
import fe.art as A                                       # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


# Die Uhr steuert der Test selbst - ueber die Attrappe des Pruefstands.
def uhr(t):
    H.NOW[0] = t


def cache_mit_wartenden(n, t0):
    """Ein ArtCache, auf dem n Kacheln seit t0 auf den Arbeitsprozess
    warten - so wie nach dem Betreten einer Rasterseite."""
    c = A.ArtCache()
    for i in range(n):
        c._warte_start[("/k/%02d.jpg" % i, "", 176, 235)] = t0
    return c


# thumb_cache_has() fragt die Karte. Hier entscheidet eine Menge,
# welche Miniaturen "schon geliefert" sind.
GELIEFERT = set()
_alt_has = A.thumb_cache_has
A.thumb_cache_has = lambda p, w, h: p in GELIEFERT

try:
    # -----------------------------------------------------------------------
    print("Test 1: die Notbremse misst ab der LETZTEN LIEFERUNG")
    # -----------------------------------------------------------------------
    GELIEFERT.clear()
    uhr(100.0)
    c = cache_mit_wartenden(21, 100.0)
    check("mit nur einem Wartenden ist alles wie vorher",
          not cache_mit_wartenden(1, 100.0)._geduld_am_ende(100.0, 101.9)
          and cache_mit_wartenden(1, 100.0)._geduld_am_ende(100.0, 102.1),
          "2 s ab dem Auftrag, solange nichts geliefert wurde")

    # Der Arbeitsprozess liefert bei 101.9 die erste Kachel.
    GELIEFERT.add("/k/00.jpg")
    uhr(101.9)
    check("die Lieferung wird bemerkt", c.warte_pruefen() is True)
    check("und vermerkt", c._letzte_lieferung == 101.9,
          "%r" % c._letzte_lieferung)

    # Bei 102.5 sind die anderen 2,5 s alt - VORHER hiess das Notbremse.
    check("2,5 s nach dem Auftrag, 0,6 s nach der letzten Lieferung: "
          "noch KEINE Notbremse",
          not c._geduld_am_ende(100.0, 102.5),
          "vorher zog sie hier, und der Zeichenweg rechnete selbst")
    uhr(102.5)
    check("warte_pruefen meldet deshalb nichts", c.warte_pruefen() is False)

    # Liefert der Prozess zwei Sekunden lang GAR NICHTS, greift sie.
    check("zwei Sekunden ohne jede Lieferung: jetzt schon",
          c._geduld_am_ende(100.0, 104.0))
    uhr(104.0)
    check("und warte_pruefen meldet es", c.warte_pruefen() is True)

    # -----------------------------------------------------------------------
    print()
    print("Test 2: eine Taste vergisst die Wartevermerke")
    # -----------------------------------------------------------------------
    # Nachgestellt, was im Raster passierte: Seite betreten (21
    # Vermerke), Taste (Auftraege weg), schneller Pfad zeichnet zwei
    # Kacheln - die anderen 19 fragen nie wieder nach.
    GELIEFERT.clear()
    uhr(200.0)
    c = cache_mit_wartenden(21, 200.0)
    uhr(203.0)
    # SO WAR ES: ohne Vergessen meldet warte_pruefen() bei jeder
    # Abfrage "nachzeichnen", fuer immer - die 19 werden nie abgeraeumt.
    dauerhaft = [c.warte_pruefen() for _ in range(5)]
    check("vorher: veraltete Vermerke melden DAUERHAFT 'nachzeichnen'",
          all(dauerhaft) and len(c._warte_start) == 21,
          "%s, %d Vermerke" % (dauerhaft, len(c._warte_start)))

    c.warten_vergessen()
    check("warten_vergessen() raeumt alle ab", not c._warte_start)
    check("danach gibt es nichts mehr nachzuzeichnen",
          c.warte_pruefen() is False)

    # Und was nach der Taste sichtbar ist, fragt frisch an.
    c._warte_start[("/k/05.jpg", "", 176, 235)] = 203.0
    uhr(204.0)
    check("die neu angefragte Kachel hat einen FRISCHEN Vermerk",
          not c._geduld_am_ende(203.0, 204.0))
finally:
    A.thumb_cache_has = _alt_has

# ---------------------------------------------------------------------------
print()
print("Test 3: Nachzeichnen im Leerlauf zeichnet in Raster und Galerie VOLL")
# ---------------------------------------------------------------------------
# Gezaehlt wird, wie viele Kacheln tatsaechlich neu gezeichnet werden.
H.SCREEN[:] = [1920, 1080]
f = H.make_frontend(page=1)
f.ansicht_setzen("raster")
gezaehlt = []
_orig = f._kachel_zeichnen


def _zaehl(*a, **k):
    gezaehlt.append(1)
    return _orig(*a, **k)


f._kachel_zeichnen = _zaehl

f._force_full_redraw = True
f.draw()
voll = len(gezaehlt)
check("das Raster hat mehr als zwei Kacheln (sonst prueft der Test nichts)",
      voll > 2, "%d" % voll)

del gezaehlt[:]
f.item_i = min(f.item_i + 1, voll - 1)
f.draw()
schritt = len(gezaehlt)
check("ein Schritt zeichnet wie gehabt nur zwei", schritt <= 2,
      "%d" % schritt)

# SO WAR ES: das Nachzeichnen im Leerlauf war derselbe schnelle Pfad.
del gezaehlt[:]
f.draw()
check("vorher: Nachzeichnen ohne Vorbereitung = hoechstens zwei Kacheln",
      len(gezaehlt) <= 2, "%d - die anderen bekamen ihr Cover nie"
      % len(gezaehlt))

del gezaehlt[:]
ans = f._nachzeichnen_vorbereiten()
f.draw()
check("jetzt: Nachzeichnen zeichnet ALLE Kacheln der Seite",
      len(gezaehlt) == voll, "%d von %d" % (len(gezaehlt), voll))
check("und meldet die Ansicht", ans == "raster")

# Galerie: auch dort muss es voll sein (Nachbarleiste).
f.ansicht_setzen("galerie")
f._force_full_redraw = False
check("in der Galerie setzt es ebenfalls den vollen Aufbau",
      f._nachzeichnen_vorbereiten() == "galerie" and f._force_full_redraw)

# Liste: bleibt beim schnellen Pfad - dort ist nur EIN Cover zu sehen.
f.ansicht_setzen("liste")
f._force_full_redraw = False
check("in der Liste bleibt der schnelle Pfad",
      f._nachzeichnen_vorbereiten() == "liste"
      and not f._force_full_redraw)

# Hauptseite ebenso.
g = H.make_frontend(page=0)
g.ansicht_haupt_setzen("raster")
g._force_full_redraw = False
check("auf der Hauptseite im Raster ebenfalls voll",
      g._nachzeichnen_vorbereiten() == "raster" and g._force_full_redraw)
g.ansicht_haupt_setzen("liste")
g._force_full_redraw = False
check("und in ihrer Liste nicht",
      g._nachzeichnen_vorbereiten() == "liste" and not g._force_full_redraw)

# ---------------------------------------------------------------------------
print()
print("Test 4: die beiden Stellen im Code")
# ---------------------------------------------------------------------------
quelle = io.open(os.path.join(_REPO, "frontend", "frontend.py"),
                 encoding="utf-8").read()
code = "\n".join(z for z in quelle.splitlines()
                 if not z.strip().startswith("#"))
i = code.index("PREWARMER.abbrechen()\n                self.lader.abbrechen()")
check("die Eingabe vergisst die Wartevermerke direkt nach dem Abbrechen",
      "ART.warten_vergessen()" in code[i:i + 200])
j = code.index("ART._deferred_something = False\n")
check("das Nachzeichnen im Leerlauf bereitet vorher den vollen Aufbau vor",
      "self._nachzeichnen_vorbereiten()" in code[j:j + 200])
check("es gibt genau eine Definition",
      quelle.count("def _nachzeichnen_vorbereiten(") == 1)

art_q = io.open(os.path.join(_REPO, "frontend", "fe", "art.py"),
                encoding="utf-8").read()
check("beide Notbremsen-Pruefungen gehen ueber _geduld_am_ende()",
      art_q.count("self._geduld_am_ende(") == 2,
      "%d" % art_q.count("self._geduld_am_ende("))
check("und nirgends mehr die alte Rechnung ab dem Auftrag",
      "- t0 > self.AUSLAGERN_MAX" not in art_q)

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
