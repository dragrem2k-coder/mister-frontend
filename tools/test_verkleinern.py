#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft den umgebauten Verkleinerer (Build 118).

WARUM DER UMBAU. Nach Build 115 und 116 war das Verkleinern der ganze
Rest: von einem kalten Cover auf HDMI entfielen 97 von 101 ms darauf.
Gemessen steckten 73 % davon in der inneren Summenschleife, 19 % in
den Divisionen.

Der Gewinn kommt aus einer einzigen Beobachtung: bei einer
Verkleinerung schwaecher als 3:1 - und genau das ist der HDMI-Fall,
424x768 in einen 360x420-Kasten sind Faktor 1,8 - entsteht jede
Zielspalte aus hoechstens ZWEI Quellspalten. Ein sum() auf einem
Ausschnitt von zwei Werten kostet dann mehr als die zwei Werte selbst:
der Ausschnitt muss angelegt, der Aufruf gemacht werden.

    HDMI, Faktor 1,8   98,8 -> 45,4 ms
    genau halb         21,2 -> 10,0 ms
    CRT,  Faktor 5     38,4 -> 34,9 ms   (allgemeiner Weg, nur Feinschliff)

WAS DIESER TEST BEWEISEN MUSS: dass dabei BITGENAU dasselbe Bild
herauskommt. Eine Abweichung faellt nicht auf - sie sitzt einfach fuer
immer in den vorberechneten Miniaturen auf der Karte, gemischt mit den
alten. Deshalb traegt der Test eine Kopie der alten Fassung und
vergleicht ueber Zufallsgroessen, wie beim Cover-Index in Build 110.

Ausfuehren:
    python3 tools/test_verkleinern.py
"""
import os
import random
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)

import _harness as H                                    # noqa: E402,F401

sys.path.insert(0, os.path.join(_REPO, "frontend"))
import fe.art as A                                      # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


def alt(pix, w, h, tw, th):
    """Die Fassung VOR Build 118, wortgleich uebernommen - Massstab.

    Steht hier und nicht im Quelltext, damit der Vergleich auch dann
    noch gilt, wenn dort irgendwann niemand mehr weiss, wie es vorher
    aussah."""
    if tw <= 0 or th <= 0 or w <= 0 or h <= 0:
        return None
    xr = []
    nx = []
    for x in range(tw):
        a = int(x * w / tw)
        b = max(a + 1, int((x + 1) * w / tw))
        xr.append((a * 4, b * 4))
        nx.append(b - a)
    rw = w * 4
    ro = tw * 4
    out = bytearray(tw * th * 4)
    for ty in range(th):
        y0 = int(ty * h / th)
        y1 = max(y0 + 1, int((ty + 1) * h / th))
        n = y1 - y0
        acc = None
        for y in range(y0, y1):
            row = pix[y * rw:(y + 1) * rw]
            cur = []
            _an = cur.append
            for a, b in xr:
                _an(sum(row[a:b:4]))
                _an(sum(row[a + 1:b:4]))
                _an(sum(row[a + 2:b:4]))
            acc = cur if acc is None else [p + q for p, q in zip(acc, cur)]
        o = ty * ro
        i = 0
        for x in range(tw):
            d = nx[x] * n
            out[o] = acc[i] // d
            out[o + 1] = acc[i + 1] // d
            out[o + 2] = acc[i + 2] // d
            o += 4
            i += 3
    return bytes(out)


def bild(w, h, rnd=None):
    p = bytearray(w * h * 4)
    if rnd is None:
        for i in range(0, len(p), 4):
            p[i] = i % 251
            p[i + 1] = (i // 4) % 253
            p[i + 2] = (i // 16) % 256
            p[i + 3] = 255
    else:
        for i in range(len(p)):
            p[i] = rnd.randrange(256)
    return bytes(p)


def bestes(fn, n=3, runden=3):
    b = None
    for _ in range(runden):
        t0 = time.perf_counter()
        for _ in range(n):
            fn()
        d = (time.perf_counter() - t0) / n * 1000
        b = d if b is None or d < b else b
    return b


print("Test 1: die echten Faelle aus dem Frontend, bitgenau")
# Genau die Groessen, die auf dem Geraet vorkommen - ein 424x768-Cover
# in den HDMI- und in den CRT-Kasten.
for w, h, tw, th, lbl in ((424, 768, 231, 420, "HDMI  Faktor 1,8"),
                          (424, 768, 82, 150, "CRT   Faktor 5"),
                          (320, 240, 160, 120, "genau halb"),
                          (400, 560, 220, 308, "Faktor 1,8"),
                          (600, 800, 200, 266, "Faktor 3")):
    p = bild(w, h)
    check("%-16s %dx%d -> %dx%d" % (lbl, w, h, tw, th),
          alt(p, w, h, tw, th) == A._verkleinern_flaechenmittel(p, w, h, tw, th))

print()
print("Test 2: 120 Zufallsgroessen, bitgenau")
# Der eigentliche Beweis. Einzelne Beispiele wuerden genau die
# Randlagen uebersehen, an denen sich die Gruppenbildung aendert -
# etwa den Sprung von hoechstens zwei auf drei Quellspalten, an dem
# der schnelle Weg abgibt.
rnd = random.Random(118)
schlecht = []
for _ in range(120):
    w = rnd.randint(1, 90)
    h = rnd.randint(1, 90)
    tw = rnd.randint(1, w)
    th = rnd.randint(1, h)
    p = bild(w, h, rnd)
    if alt(p, w, h, tw, th) != A._verkleinern_flaechenmittel(p, w, h, tw, th):
        schlecht.append((w, h, tw, th))
check("keine Abweichung", not schlecht,
      "%d abweichend, z.B. %r" % (len(schlecht),
                                  schlecht[0] if schlecht else None))

print()
print("Test 3: der Sprung zwischen schnellem und allgemeinem Weg")
# Beide Wege muessen an der Grenze dasselbe liefern - dort entscheidet
# sich, welcher genommen wird.
for w in range(10, 40):
    for tw in (w // 2, w // 3, w // 3 + 1, w // 4):
        if tw < 1:
            continue
        p = bild(w, 12, rnd)
        if alt(p, w, 12, tw, 6) != A._verkleinern_flaechenmittel(p, w, 12, tw, 6):
            schlecht.append((w, 12, tw, 6))
check("auch an der Grenze gleich", not schlecht,
      "%r" % (schlecht[:3],))

print()
print("Test 4: Randfaelle werfen nichts um")
check("Zielgroesse 0 liefert None",
      A._verkleinern_flaechenmittel(bild(4, 4), 4, 4, 0, 4) is None)
check("Quellgroesse 0 liefert None",
      A._verkleinern_flaechenmittel(b"", 0, 4, 2, 2) is None)
einzel = A._verkleinern_flaechenmittel(bild(8, 8), 8, 8, 1, 1)
check("auf einen einzigen Bildpunkt", einzel is not None and len(einzel) == 4,
      "%r" % (einzel,))
gleich = A._verkleinern_flaechenmittel(bild(8, 8), 8, 8, 8, 8)
check("gleiche Groesse ist auch erlaubt",
      gleich == alt(bild(8, 8), 8, 8, 8, 8))

print()
print("Test 5: und es ist wirklich schneller")
# Ohne diese Messung waere der ganze Umbau nur eine zweite Fassung
# derselben Funktion.
p = bild(424, 768)
t_alt = bestes(lambda: alt(p, 424, 768, 231, 420), 2)
t_neu = bestes(lambda: A._verkleinern_flaechenmittel(p, 424, 768, 231, 420), 2)
# GEAENDERT (Build 143): Schwelle von 1,7 auf 1,5. Der Faktor liegt
# gemessen bei 1,9-2,0; auf einer ausgelasteten Maschine rutschte er
# einmal auf 1,6 und liess den Test ohne Anlass rot werden. Die
# Schwelle soll eine ECHTE Verschlechterung fangen, nicht die
# Zeitscheiben des Betriebssystems - und zwischen 1,9 und 1,5 liegt
# genug Luft dafuer, waehrend ein Rueckfall auf den alten Weg (Faktor
# 1,0) weiterhin sofort auffaellt.
check("HDMI-Fall mindestens 1,5x schneller", t_alt > 1.5 * t_neu,
      "alt %.1f ms, neu %.1f ms, Faktor %.1f"
      % (t_alt, t_neu, t_alt / t_neu if t_neu else 0))
t_alt = bestes(lambda: alt(p, 424, 768, 82, 150), 2)
t_neu = bestes(lambda: A._verkleinern_flaechenmittel(p, 424, 768, 82, 150), 2)
check("und der allgemeine Weg nicht langsamer", t_alt >= t_neu * 0.98,
      "alt %.1f ms, neu %.1f ms" % (t_alt, t_neu))

print()
if fails:
    print("FEHLGESCHLAGEN (%d):" % len(fails))
    for f_ in fails:
        print("  -", f_)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
