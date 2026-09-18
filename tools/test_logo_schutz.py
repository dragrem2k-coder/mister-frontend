#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft, dass die Kategorie-Logos nicht aus dem Arbeitsspeicher
fliegen, wenn man lange durch Cover scrollt (Build 141).

Nutzer-Rueckmeldung: "wenn man durch die ROM-Listen/Galerie scrollt und
dann zurueck auf die Hauptseite geht, gibt es ab und zu einen kleinen
Haenger - nicht immer, ab und zu mal."

URSACHE. Der RAM-Bildspeicher (SCALED_BUDGET, 96 MB) verdraengte nach
reinem FIFO. Die Kategorie-Logos kommen als ERSTE herein - beim Start,
auf der Hauptseite - und sind mit bis zu 900 Bildpunkten Breite die
groessten Bilder im ganzen Frontend. Ein Galerie-Cover belegt auf HDMI
624 KB; nach rund 150 gescrollten Eintraegen ist das Budget voll, und
die Aeltesten, die fliegen, sind genau die Logos.

Beim Zurueckgehen muss das Logo dann neu von der Karte gelesen und
entpackt werden - fuer diesen Fall steht in fe/art.py eine Messung vom
Geraet: 722 ms fuer CONTINUE.art. Das "ab und zu" erklaert sich damit
von selbst: wer nur kurz scrollt, hat sein Logo noch.

Fuer den FESTPLATTEN-Cache gibt es diesen Schutz laengst
(_geschuetzte_cache_dateien) - fuer den Arbeitsspeicher fehlte er.

Ausfuehren:
    python3 tools/test_logo_schutz.py
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)

import _harness as H                                    # noqa: E402

sys.path.insert(0, os.path.join(_REPO, "frontend"))
import fe.art as A                                      # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


def frischer_cache():
    """Ein ArtCache ohne Dateien - hier geht es nur um die
    Verdraengung, nicht ums Lesen."""
    c = A.ArtCache()
    c.scaled = {}
    c.scaled_order = []
    c.scaled_bytes = 0
    return c


def ablegen(cache, pfad, bytes_gross):
    """Einen Eintrag einlagern, so wie der Zeichenweg es tut."""
    cache._scaled_cache_put((pfad, "box", 100, 100),
                            (100, 100, bytearray(bytes_gross)))


print("Test 1: die Regel selbst")
check("ein Bild unter sysart gilt als Logo",
      A._ist_kategorie_logo(A.SYSART_BASE + "/SNES.art"))
check("ein Spiel-Cover nicht",
      not A._ist_kategorie_logo("/media/fat/frontend/art_hd/SNES/Spiel.art"))
check("None und leer werfen nichts um",
      not A._ist_kategorie_logo(None) and not A._ist_kategorie_logo(""))
# SYSART_BASE wird bei jedem Aufruf frisch gelesen - Tests und der
# CRT/HDMI-Wechsel biegen die Konstante um.
_alt = A.SYSART_BASE
A.SYSART_BASE = "/woanders/sysart"
check("ein umgebogenes SYSART_BASE wirkt sofort",
      A._ist_kategorie_logo("/woanders/sysart/NES.art")
      and not A._ist_kategorie_logo(_alt + "/NES.art"))
A.SYSART_BASE = _alt

print()
print("Test 2: Cover verdraengen sich gegenseitig - wie bisher")
c = frischer_cache()
gross = c.SCALED_BUDGET // 10          # zehn Stueck sprengen das Budget
for i in range(25):
    ablegen(c, "/media/fat/frontend/art_hd/SNES/Cover%02d.art" % i, gross)
check("es bleiben nicht alle liegen", len(c.scaled) < 25,
      "%d von 25" % len(c.scaled))
check("das aelteste ist weg",
      ("/media/fat/frontend/art_hd/SNES/Cover00.art", "box", 100, 100)
      not in c.scaled)
check("das neueste ist da",
      ("/media/fat/frontend/art_hd/SNES/Cover24.art", "box", 100, 100)
      in c.scaled)

print()
print("Test 3: DAS war der Fehler - Logos ueberleben das Scrollen")
c = frischer_cache()
# Erst die Hauptseite: die Logos kommen zuerst herein.
logos = [A.SYSART_BASE + "/%s.art" % n
         for n in ("CONTINUE", "FAVORITES", "SNES", "NES")]
for p in logos:
    ablegen(c, p, gross)
# Dann eine lange Galerie-Fahrt.
for i in range(40):
    ablegen(c, "/media/fat/frontend/art_hd/SNES/Cover%02d.art" % i, gross)
fehlend = [p for p in logos
           if (p, "box", 100, 100) not in c.scaled]
check("alle vier Logos sind noch da", not fehlend,
      "fehlt: %s" % ", ".join(os.path.basename(p) for p in fehlend))
check("und die Cover haben trotzdem verdraengt",
      len([k for k in c.scaled if not A._ist_kategorie_logo(k[0])]) < 40,
      "%d Cover gehalten" % len([k for k in c.scaled
                                 if not A._ist_kategorie_logo(k[0])]))

print()
print("Test 4: nur Logos - die Schleife laeuft nicht endlos")
# Kann in der Praxis nicht vorkommen (zwei Dutzend Logos sprengen keine
# 96 MB), aber eine Verdraengungsschleife, die nichts mehr wegwerfen
# darf, muss trotzdem enden.
c = frischer_cache()
for i in range(30):
    ablegen(c, A.SYSART_BASE + "/Logo%02d.art" % i, gross)
check("alle Logos gehalten, kein Haenger", len(c.scaled) == 30,
      "%d" % len(c.scaled))

print()
print("Test 5: die Buchfuehrung bleibt heil")
# scaled_bytes muss zur Summe der tatsaechlich gehaltenen Eintraege
# passen - laeuft sie auseinander, verdraengt der Cache spaeter zu
# frueh oder gar nicht mehr.
c = frischer_cache()
for i in range(10):
    ablegen(c, A.SYSART_BASE + "/L%d.art" % i, gross)
for i in range(30):
    ablegen(c, "/media/fat/frontend/art_hd/SNES/C%02d.art" % i, gross)
summe = sum(len(v[2]) for v in c.scaled.values())
check("scaled_bytes stimmt mit dem Inhalt ueberein",
      c.scaled_bytes == summe, "%d gegen %d" % (c.scaled_bytes, summe))
check("Reihenfolge-Liste und Inhalt sind gleich lang",
      len(c.scaled_order) == len(c.scaled),
      "%d / %d" % (len(c.scaled_order), len(c.scaled)))

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Tests bestanden.")
