#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Die unskalierten Originale sind auch nach SPEICHER begrenzt
(Build 170).

DER FUND, DER DAZU GEFUEHRT HAT

Aus der 97.000-Spiele-Messung (siehe MESSUNG_Riesenbestand_97k.md):
`ArtCache.LIMIT = 60` ist eine STUECKZAHL. Seit Build 119 werden
Cover im ORIGINAL geladen statt auf Kastengroesse gestutzt - und
Originale sind unterschiedlich gross:

    600x800   Cover  ->  1,9 MB  ->  60 Stueck = 115 MB
    1200x1600 Scan   ->  7,7 MB  ->  60 Stueck = 460 MB

Auf einem Geraet mit rund 1 GB, das sich Linux mit dem FPGA-Kern
teilt, ist die zweite Zeile kein theoretischer Fall. Der skalierte
Cache hatte sein Budget seit Build 74; dieser hier nie - obwohl der
Kommentar bei SCALED_BUDGET ihn ausdruecklich erwaehnt.

WAS DIESER TEST PRUEFT

Vor allem, dass die Grenze HAELT, ohne dass der Cache sich selbst
leer macht. Beides kann man falsch bauen, und das zweite faellt erst
auf dem Geraet auf (jedes Cover wird bei jedem Schritt neu von der
Karte gelesen - genau der Haenger aus Build 120).

Ausfuehren:
    python3 tools/test_original_budget.py
"""
import os
import sys

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
sys.path.insert(0, os.path.join(_REPO, "frontend"))

import fe.art as art                                     # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


MB = 1024 * 1024


def leerer_cache():
    c = art.ArtCache()
    return c


def einfuegen(c, pfad, bytes_gross):
    """Direkt in den Cache legen - so, wie es _original_lesen() tut,
    nur ohne Datei. Geprueft wird die Verdraengung, nicht das Lesen."""
    bild = (10, 10, bytearray(bytes_gross))
    c._original_bytes = (getattr(c, "_original_bytes", 0)
                         - c._bildbytes(c.cache.get(pfad)))
    c.cache[pfad] = bild
    c._original_bytes += c._bildbytes(bild)
    c.order.append(pfad)
    c._originale_verdraengen()


def belegt(c):
    return sum(c._bildbytes(v) for v in c.cache.values())


# ---------------------------------------------------------------------------
print("Test 1: kleine Cover - die Stueckzahl greift wie bisher")
# ---------------------------------------------------------------------------
# 60 CRT-Cover zu je 60 KB sind 3,6 MB, weit unter dem Budget. Hier
# darf sich gegenueber vorher NICHTS aendern.
c = leerer_cache()
for i in range(200):
    einfuegen(c, "/crt/%d" % i, 60 * 1024)
check("es bleiben genau LIMIT Bilder", len(c.cache) == art.ArtCache.LIMIT,
      "%d von %d" % (len(c.cache), art.ArtCache.LIMIT))
check("das Budget wurde nie zum Thema",
      belegt(c) < art.ArtCache.ORIGINAL_BUDGET,
      "%.1f MB von %.0f MB" % (belegt(c) / MB,
                               art.ArtCache.ORIGINAL_BUDGET / MB))
check("der Zaehler stimmt mit dem echten Inhalt ueberein",
      c._original_bytes == belegt(c),
      "%d vs %d" % (c._original_bytes, belegt(c)))

# ---------------------------------------------------------------------------
print()
print("Test 2: DER FALL, UM DEN ES GEHT - grosse Originale")
# ---------------------------------------------------------------------------
# 60 Stueck a 7,7 MB waeren 460 MB gewesen.
c = leerer_cache()
for i in range(60):
    einfuegen(c, "/scan/%d" % i, int(7.7 * MB))
# Die Zusage ist "hoechstens das Groessere von Budget und
# ORIGINAL_MIN mal groesstem Bild" - die Mindestanzahl hat Vorrang,
# damit sich der Cache nicht selbst leert (siehe Test 3).
grenze = max(art.ArtCache.ORIGINAL_BUDGET,
             art.ArtCache.ORIGINAL_MIN * int(7.7 * MB))
check("die Grenze haelt", belegt(c) <= grenze,
      "%.0f MB (Grenze %.0f MB) statt frueher %.0f MB"
      % (belegt(c) / MB, grenze / MB, 60 * 7.7))
check("und es sind deutlich weniger als 60 Bilder",
      len(c.cache) < 60, "%d Bilder" % len(c.cache))
check("der Zaehler stimmt weiterhin",
      c._original_bytes == belegt(c),
      "%d vs %d" % (c._original_bytes, belegt(c)))

# ---------------------------------------------------------------------------
print()
print("Test 3: der Cache darf sich NICHT selbst leeren")
# ---------------------------------------------------------------------------
# Ein einzelnes Bild groesser als das ganze Budget waere der Fall, in
# dem eine naive Schleife alles hinauswirft - und dann bei jedem
# Schritt neu von der Karte liest. Genau der Haenger aus Build 120.
c = leerer_cache()
for i in range(5):
    einfuegen(c, "/riesig/%d" % i, art.ArtCache.ORIGINAL_BUDGET + MB)
check("auch bei uebergrossen Bildern bleiben Plaetze",
      len(c.cache) >= 1, "%d Bilder" % len(c.cache))
check("mindestens ORIGINAL_MIN, solange so viele da sind",
      len(c.cache) == min(5, art.ArtCache.ORIGINAL_MIN),
      "%d, erwartet %d" % (len(c.cache),
                           min(5, art.ArtCache.ORIGINAL_MIN)))

c = leerer_cache()
for i in range(40):
    einfuegen(c, "/riesig/%d" % i, art.ArtCache.ORIGINAL_BUDGET + MB)
check("und bei vielen davon genau ORIGINAL_MIN",
      len(c.cache) == art.ArtCache.ORIGINAL_MIN,
      "%d" % len(c.cache))

# ---------------------------------------------------------------------------
print()
print("Test 4: 'kein Cover' kostet nichts")
# ---------------------------------------------------------------------------
c = leerer_cache()
c.cache["/leer"] = None
check("ein None-Eintrag zaehlt als 0 Bytes", c._bildbytes(None) == 0)
# Ein String ist indizierbar und haette bei reinem try/except
# klaglos 1 geliefert - deshalb prueft _bildbytes() den Typ.
check("ein zu kurzes Tupel wirft nichts um", c._bildbytes((1, 2)) == 0)
check("und ein String zaehlt nicht als Bild",
      c._bildbytes("Unsinn") == 0, str(c._bildbytes("Unsinn")))

# ---------------------------------------------------------------------------
print()
print("Test 5: dasselbe Bild zweimal zaehlt nicht doppelt")
# ---------------------------------------------------------------------------
c = leerer_cache()
einfuegen(c, "/gleich", 5 * MB)
vorher = c._original_bytes
einfuegen(c, "/gleich", 5 * MB)
check("der Zaehler bleibt gleich", c._original_bytes == vorher,
      "%d vs %d" % (c._original_bytes, vorher))
check("und stimmt mit dem Inhalt ueberein",
      c._original_bytes == belegt(c))

# ---------------------------------------------------------------------------
print()
print("Test 6: die Werte sind plausibel gewaehlt")
# ---------------------------------------------------------------------------
check("es gibt ein Budget", hasattr(art.ArtCache, "ORIGINAL_BUDGET"))
check("und eine Mindestanzahl", hasattr(art.ArtCache, "ORIGINAL_MIN"))
check("zusammen mit dem skalierten Cache bleibt Luft auf 1 GB",
      (art.ArtCache.ORIGINAL_BUDGET + art.ArtCache.SCALED_BUDGET)
      < 256 * MB,
      "%.0f MB fuer Bilder"
      % ((art.ArtCache.ORIGINAL_BUDGET + art.ArtCache.SCALED_BUDGET) / MB))
check("die Mindestanzahl reicht fuer eine Bildschirmseite",
      art.ArtCache.ORIGINAL_MIN >= 4)
check("aber sie hebelt das Budget nicht aus",
      art.ArtCache.ORIGINAL_MIN < art.ArtCache.LIMIT)

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
