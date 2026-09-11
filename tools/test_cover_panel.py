#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft den verkuerzten Schlagschatten des Cover-Panels (Build 97).

AUSLOESER: die Messung aus Build 96 hat gezeigt, wo die Zeit beim
Scrollen auf HDMI wirklich hingeht - nicht in die Listenzeilen, sondern
ins Cover-Panel. Und dort war der groesste Einzelposten der
Schlagschatten.

DER BEFUND: der Schatten wurde als vollstaendiger abgerundeter Kasten
in Kartengroesse gemalt - und die Karte direkt danach darueber. Auf
1080p sind das 769x945 = 726.705 Bildpunkte, von denen nur 15.210
(2,1 %) jemals zu sehen sind. Gemessen 0,461 ms pro Panel-Aufbau, also
35 % des gesamten Panels, fuer Bildpunkte, die im selben Atemzug wieder
uebermalt werden.

DIE ANFORDERUNG IST HART: das Bild muss BITGENAU dasselbe bleiben. Der
Schatten ist ein rein optisches Detail - waere er hinterher auch nur an
einer Ecke anders, waere das eine Verschlechterung fuer einen
Geschwindigkeitsgewinn, den niemand sieht.

Deshalb wird hier nicht die Form nachgerechnet, sondern der ALTE Weg
gegen den NEUEN gestellt: derselbe Puffer, einmal mit vollem
Schatten-Rechteck plus Karte, einmal mit verkuerztem Schatten plus
Karte. Beide muessen Byte fuer Byte uebereinstimmen.

Ausfuehren:
    python3 tools/test_cover_panel.py
"""
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import _harness as H                                  # noqa: E402

fm = H.fm

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


def frontend(w, h):
    H.set_screen(w, h)
    f = H.make_frontend(page=1)
    f.draw_page_items(flip=False)
    return f


def alt_und_neu(fb, x, y, kw, kh, versatz, radius, dunkel, hell):
    """Beide Wege in denselben Puffer, jeweils auf leerem Grund."""
    fb.clear(fm.C_BG)
    fb.rect_rounded(x + versatz, y + versatz, kw, kh, dunkel, radius)
    fb.rect_rounded(x, y, kw, kh, hell, radius)
    alt = bytes(fb.buf)

    fb.clear(fm.C_BG)
    fb.rect_rounded_schatten(x, y, kw, kh, versatz, dunkel, radius)
    fb.rect_rounded(x, y, kw, kh, hell, radius)
    neu = bytes(fb.buf)
    return alt, neu


print("Test 1: verkuerzter Schatten ergibt bitgenau dasselbe Bild")
# Der Kern. Mehrere Groessen und Radien, damit nicht zufaellig genau die
# eine Kombination getroffen wird, bei der es klappt.
for w, h, name in ((320, 240, "CRT"), (1920, 1080, "HDMI")):
    f = frontend(w, h)
    fb = f.fb
    s = max(1, h // 360)
    dunkel = fb._darken(fm.C_BG, 0.55)
    hell = fm.C_PANEL
    faelle = [
        (40 * s, 20 * s, 120 * s, 180 * s, 3 * s, 4 * s, "Panel-Groesse"),
        (10, 10, 60, 40, 3, 4, "klein"),
        (10, 10, 60, 40, 1, 0, "ohne Rundung"),
        (10, 10, 40, 40, 6, 20, "Radius = halbe Kante"),
        (10, 10, 80, 30, 9, 4, "breit und flach"),
        (10, 10, 30, 80, 9, 4, "schmal und hoch"),
    ]
    for x, y, kw, kh, versatz, radius, label in faelle:
        if x + kw + versatz > w or y + kh + versatz > h:
            continue
        alt, neu = alt_und_neu(fb, x, y, kw, kh, versatz, radius,
                               dunkel, hell)
        d = sum(1 for a, b in zip(alt, neu) if a != b)
        check("%s/%s: bitgenau gleich" % (name, label), d == 0,
              "(%d abweichende Bytes)" % d)

print("Test 2: auch am Bildrand, wo abgeschnitten wird")
# Der Schatten ragt um 'versatz' nach rechts und unten ueber die Karte
# hinaus - steht die Karte am Rand, faellt er teilweise aus dem Bild.
f = frontend(1920, 1080)
fb = f.fb
dunkel = fb._darken(fm.C_BG, 0.55)
for x, y, kw, kh, label in ((1920 - 60, 100, 60, 200, "rechter Rand"),
                            (100, 1080 - 60, 200, 60, "unterer Rand"),
                            (1920 - 40, 1080 - 40, 40, 40, "untere Ecke")):
    alt, neu = alt_und_neu(fb, x, y, kw, kh, 9, 12, dunkel, fm.C_PANEL)
    d = sum(1 for a, b in zip(alt, neu) if a != b)
    check("%s: bitgenau gleich" % label, d == 0,
          "(%d abweichende Bytes)" % d)

print("Test 3: das komplette Cover-Panel sieht unveraendert aus")
# Nicht nur der Schatten fuer sich, sondern der echte Aufruf aus
# draw_art_panel() mit allem drum herum.
for w, h, name in ((320, 240, "CRT"), (1920, 1080, "HDMI")):
    f = frontend(w, h)
    L = f.layout_items(True)
    s, ox, oy = L["s"], L["ox"], L["oy"]
    art_x0 = fm.art_spalte_x0(L["list_right"], h, s)
    art_w = (w - ox) - art_x0
    art_h = L["footer_y"] - 8 * s - oy
    item = f.view["items"][f.item_i]
    sk = f._item_syskey(item, f.view.get("syskey"))

    f.draw_art_panel(art_x0, art_w, oy, art_h, sk, item, s)
    neu = bytes(f.fb.buf)

    # Denselben Aufbau mit dem ALTEN Schatten nachstellen: das Panel
    # noch einmal zeichnen, davor aber den vollen Schatten legen.
    echt = f.fb.rect_rounded_schatten

    def alter_weg(x, y, kw, kh, versatz, rgb, radius=None, _fb=f.fb):
        _fb.rect_rounded(x + versatz, y + versatz, kw, kh, rgb, radius)

    f.fb.rect_rounded_schatten = alter_weg
    f.draw_art_panel(art_x0, art_w, oy, art_h, sk, item, s)
    alt = bytes(f.fb.buf)
    f.fb.rect_rounded_schatten = echt
    d = sum(1 for a, b in zip(alt, neu) if a != b)
    check("%s: Panel bitgenau wie vorher" % name, d == 0,
          "(%d abweichende Bytes)" % d)

print("Test 4: und es ist wirklich schneller")
# Kein Selbstzweck: die Aenderung hat nur dann einen Sinn, wenn sie
# tatsaechlich Zeit spart. Grosszuegige Schwelle, damit der Test nicht
# an der Tagesform des Rechners scheitert - gemessen war der Gewinn
# rund Faktor 2,7.
f = frontend(1920, 1080)
fb = f.fb
s = 3
dunkel = fb._darken(fm.C_BG, 0.55)
kw, kh, versatz, radius = 769, 945, 3 * s, 4 * s


def zeit(fn, n=30):
    for _ in range(5):
        fn()
    t0 = time.perf_counter()
    for _ in range(n):
        fn()
    return (time.perf_counter() - t0) / n * 1000


t_alt = zeit(lambda: fb.rect_rounded(40 + versatz, 20 + versatz, kw, kh,
                                     dunkel, radius))
t_neu = zeit(lambda: fb.rect_rounded_schatten(40, 20, kw, kh, versatz,
                                              dunkel, radius))
check("verkuerzter Schatten ist schneller", t_neu < t_alt,
      "(alt %.3f ms, neu %.3f ms, Faktor %.1f)"
      % (t_alt, t_neu, t_alt / t_neu if t_neu else 0))
check("und zwar deutlich (mindestens Faktor 1,5)",
      t_neu * 1.5 < t_alt,
      "(Faktor %.1f)" % (t_alt / t_neu if t_neu else 0))

print("Test 5: kein vollflaechiges Schatten-Rechteck mehr im Zeichenpfad")
# Regressionsschutz: wer den Aufruf spaeter versehentlich zurueckbaut,
# holt sich die 0,461 ms wieder ins Haus.
src = open(H.FRONTEND_PY, encoding="utf-8", errors="replace").read()
check("draw_art_panel() benutzt rect_rounded_schatten()",
      "fb.rect_rounded_schatten(" in src)
check("und malt den Schatten nicht mehr als volles rect_rounded()",
      "shadow_off, y0 - pad + shadow_off" not in src)

print()
if fails:
    print("FEHLGESCHLAGEN (%d):" % len(fails))
    for f_ in fails:
        print("  -", f_)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
