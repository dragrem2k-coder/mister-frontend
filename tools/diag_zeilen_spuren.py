#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Was das gezielte Freiraeumen bringt (Diagnose, kein Test).

NUTZER-RUECKMELDUNG, aus der das entstanden ist: "HDMI-Modus laeuft
auch, aber das Scrollen ist mir da zu langsam, vor allem wenn Zeilen
nach unten neu ins Bild kommen."

Gemessen war der groesste Einzelposten eines Scrollschritts nicht das
Zeichnen der Zeilen, sondern das FREIRAEUMEN davor: der schnelle Pfad
stellte die komplette Listenspalte wieder her - auf HDMI 859 mal 765
Bildpunkte, jede Bildzeile einzeln kopiert, 0.68 von 1.14 ms.

Seit Build 103 merkt sich jede Zeile, wie weit sie tatsaechlich gemalt
hat, und nur das wird freigeraeumt. Dieses Skript stellt beide Wege
gegeneinander, indem es den neuen gezielt abschaltet (die Funktion
liefert dann None, und der Aufrufer nimmt wie frueher die ganze
Spalte).

Zweiter Posten im selben Aufwasch: _zeilen_platz() hiess frueher
_clear_row_glow_margin() und raeumte denselben Bereich frei, den
draw_list_row() unmittelbar danach noch einmal freiraeumt - ein
Ueberbleibsel des entfernten Leucht-Rands. Auch das wird hier
nachgestellt.

WIE GEMESSEN WIRD: ueber ein festes Zeitfenster von zwei Sekunden, von
drei Durchlaeufen zaehlt der mittlere. Eine feste Schrittzahl waere auf
CRT in wenigen Millisekunden durch und damit Rauschen.

Ausfuehren:
    python3 tools/diag_zeilen_spuren.py
"""
import os
import statistics
import sys
import tempfile
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)

import _harness as H                                    # noqa: E402

fm = H.fm
sys.path.insert(0, os.path.join(_REPO, "frontend"))
import fe.settings as S                                 # noqa: E402

# Schnelles Scrollen AN - sonst wird das Cover-Panel bei jedem Schritt
# mitgezeichnet und ueberdeckt den gemessenen Unterschied.
_TMP = tempfile.mkdtemp(prefix="diag_spuren_")
S.FAST_SCROLL_DISABLED_FLAG = os.path.join(_TMP, "aus")

MESSFENSTER = 2.0
DURCHLAEUFE = 3


def liste(w, h, anzahl=400):
    H.set_screen(w, h)
    f = H.make_frontend(page=1)
    nd = f._current_node()
    nd["items"] = [(H.TITLES[i % len(H.TITLES)] + " %d" % i, "game",
                    ("/f/%d.sfc" % i, ".sfc", "SNES", None, None))
                   for i in range(anzahl)]
    nd.pop("_display_items_cache", None)
    f.item_i = 0
    f.scroll = 0
    f.draw_page_items(flip=False)
    f.draw_page_items(flip=False)      # ab hier laeuft der schnelle Pfad
    return f


def messen(schritt, f):
    for _ in range(20):
        schritt(f)
    n = 0
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < MESSFENSTER:
        schritt(f)
        n += 1
    return (time.perf_counter() - t0) / n * 1000.0


def scroll_schritt(f):
    f._last_input_time = time.monotonic()
    f.item_i += 1
    f.scroll += 1
    if f.item_i > 380:
        f.item_i, f.scroll = 0, 0
    f.draw_page_items(flip=False)


def navi_schritt(f):
    f._last_input_time = time.monotonic()
    vis = f.items_visible
    alt = f.item_i
    f.item_i = f.scroll + ((f.item_i - f.scroll + 1) % max(2, vis - 1))
    f._draw_navigate_items(alt)


def median(schritt, w, h):
    return statistics.median([messen(schritt, liste(w, h))
                              for _ in range(DURCHLAEUFE)])


_echt_spuren = fm.Frontend._zeilen_spuren_holen
_echt_platz = fm.Frontend._zeilen_platz


def _spuren_aus(self, *a, **k):
    # Spuren trotzdem abholen und verwerfen (sonst wachsen sie an),
    # aber den alten Weg erzwingen.
    _echt_spuren(self, *a, **k)
    return None


def _platz_mit_doppelarbeit(self, item_i):
    """Den Zustand vor Build 103 nachstellen: erst hier freiraeumen,
    gleich danach in draw_list_row() noch einmal dasselbe."""
    y_top, max_p = _echt_platz(self, item_i)
    if y_top is not None:
        v = self.view
        s = v["s"]
        self._restore_row_bg(v["list_x"] - 4 * s, y_top,
                             max(4, v["list_right"] - v["list_x"] - 2 * s),
                             max(v["rowh"] - 2 * s, 11 * s))
    return y_top, max_p


print("Was das gezielte Freiraeumen bringt")
print("(%.0fs Messfenster, Mittlerer aus %d Durchlaeufen)"
      % (MESSFENSTER, DURCHLAEUFE))
print()
print("%-6s %-24s %10s %10s %8s"
      % ("Modus", "Fall", "bis 102", "ab 103", "Gewinn"))

for w, h, name in ((320, 240, "CRT"), (1920, 1080, "HDMI")):
    fm.Frontend._zeilen_spuren_holen = _spuren_aus
    alt = median(scroll_schritt, w, h)
    fm.Frontend._zeilen_spuren_holen = _echt_spuren
    neu = median(scroll_schritt, w, h)
    print("%-6s %-24s %8.3fms %8.3fms %7.0f%%"
          % (name, "Zeile kommt neu rein", alt, neu, (1 - neu / alt) * 100))

    fm.Frontend._zeilen_platz = _platz_mit_doppelarbeit
    alt = median(navi_schritt, w, h)
    fm.Frontend._zeilen_platz = _echt_platz
    neu = median(navi_schritt, w, h)
    print("%-6s %-24s %8.3fms %8.3fms %7.0f%%"
          % (name, "Markierung wandert", alt, neu, (1 - neu / alt) * 100))

# Wie viel Flaeche das ausmacht - die Zahl hinter dem Zeitgewinn.
print()
print("%-6s %14s %14s %8s" % ("Modus", "Spalte", "nur Spuren", "Anteil"))
for w, h, name in ((320, 240, "CRT"), (1920, 1080, "HDMI")):
    f = liste(w, h)
    f.draw_page_items(flip=False)
    v = f.view
    s, rowh = v["s"], v["rowh"]
    lm = 10 * s
    spalte = (((v["list_right"] - v["list_x"]) + 2 * lm)
              * (f.items_visible * rowh + 2 * lm))
    spuren = sum(sw * sh for _x, _y, sw, sh in f._zeilen_spur.values())
    print("%-6s %10d Pkt %10d Pkt %7.0f%%"
          % (name, spalte, spuren, spuren * 100.0 / spalte))

print()
print("Der Gewinn kommt aus BEIDEN Richtungen: ein mittlerer Titel")
print("belegt rund 45 % der Spaltenbreite (CRT: 80 %), und der Text ist")
print("8*s hoch statt der vollen Zeilenhoehe - auf HDMI 24 statt 45")
print("Bildpunkte. Deshalb faellt der Gewinn auf CRT deutlich kleiner")
print("aus: dort sind die Titel im Verhaeltnis breiter und die Zeilen")
print("ohnehin flach.")
sys.exit(0)
