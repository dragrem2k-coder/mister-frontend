#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""blit(): halb so teuer, Byte fuer Byte dasselbe (Build 131).

GEFUNDEN in einem DRAGEND_PROFILE-Protokoll vom Geraet des Nutzers: ein
Galerie-Aufbau der Hauptseite kostete 144 ms, davon 75 ms in ZWOELF
blit()-Aufrufen. Groesster Einzelposten im ganzen Protokoll - und anders
als ein kalter Miniatur-Cache faellt er bei JEDEM Seitenaufbau an, auch
wenn alles vorbereitet ist.

Die Ursache stand in einer Zeile: `chunk = pix[src_off:src_off + need]`.
Ein Ausschnitt auf bytes/bytearray legt eine KOPIE an - bei einem
411x548-Cover also 548 Zwischenobjekte je Bild, die sofort wieder
weggeworfen werden. Mit memoryview ist derselbe Ausschnitt ein Verweis.

WAS DIESER TEST SICHERT, und das ist das Wichtigere: das Ergebnis muss
bitgenau dasselbe bleiben. blit() schreibt direkt in den Bildspeicher -
ein Fehler um eine Zeile oder ein Byte waere sofort sichtbar, und die
alten Laengenpruefungen (die einen zu kurzen Puffer abfangen, damit die
bytearray-Zuweisung den Speicher nicht VERSCHIEBT) stehen jetzt vor der
Schleife statt darin. Genau diese Randfaelle werden hier durchgespielt.

Ausfuehren:
    python3 tools/test_blit.py
"""
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)

import _harness as H                                    # noqa: E402

fm = H.fm

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


def alt_blit(fb, x, y, w, h, pix):
    """Die Fassung aus Build 130 - Massstab fuer den Vergleich."""
    if x < 0 or y < 0 or x >= fb.width or y >= fb.height:
        return
    cw = min(w, fb.width - x)
    ch = min(h, fb.height - y)
    need = cw * 4
    buflen = len(fb.buf)
    for row in range(ch):
        src_off = row * w * 4
        dst_off = (y + row) * fb.stride + x * 4
        if dst_off + need > buflen:
            continue
        chunk = pix[src_off:src_off + need]
        if len(chunk) != need:
            continue
        fb.buf[dst_off:dst_off + need] = chunk


def muster(w, h, versatz=0):
    """Ein Bild, in dem JEDER Punkt anders aussieht - bei einer
    einfarbigen Flaeche faellt ein Versatz um eine Zeile nicht auf."""
    b = bytearray()
    for y in range(h):
        for x in range(w):
            b += bytes(((x + versatz) % 256, y % 256,
                        (x * 3 + y * 7) % 256, 255))
    return bytes(b)


H.set_screen(1920, 1080)
f = H.make_frontend(page=1)
fb = f.fb

# ---------------------------------------------------------------------
print("Test 1: bitgenau dasselbe wie die alte Fassung")
FAELLE = [
    (100, 100, 411, 548, "Galerie-Cover"),
    (50, 40, 733, 909, "Listen-Cover HDMI"),
    (0, 0, 124, 166, "Leisten-Kachel"),
    (0, 0, 1, 1, "ein einziger Punkt"),
    (1919, 1079, 10, 10, "ragt rechts UND unten hinaus"),
    (1900, 500, 100, 50, "ragt nur rechts hinaus"),
    (300, 1050, 80, 80, "ragt nur unten hinaus"),
    (0, 0, 1920, 1080, "genau der ganze Schirm"),
]
for x, y, w, h, name in FAELLE:
    pix = muster(w, h)
    laenge = len(fb.buf)

    fb.clear((0, 0, 0))
    alt_blit(fb, x, y, w, h, pix)
    erwartet = bytes(fb.buf)

    fb.clear((0, 0, 0))
    f.blit(x, y, w, h, pix)
    bekommen = bytes(fb.buf)

    gleich = erwartet == bekommen
    check("%-26s bitgenau" % name, gleich,
          "" if gleich else "%d abweichende Bytes"
          % sum(1 for a, b in zip(erwartet, bekommen) if a != b))
    check("%-26s Puffer unveraendert lang" % name, len(fb.buf) == laenge)

# ---------------------------------------------------------------------
print()
print("Test 2: die Randfaelle, die den Puffer zerstoeren koennten")
# Das ist der Grund, warum die alte Fassung ueberhaupt Laengenpruefungen
# hatte: eine Zuweisung mit der falschen Anzahl Bytes VERKUERZT ein
# bytearray und verschiebt alles dahinter. Auf dem Schirm sieht das aus,
# als waere das halbe Bild diagonal verrutscht.
laenge = len(fb.buf)
fb.clear((0, 0, 0))
f.blit(100, 100, 50, 50, b"")                      # gar keine Punkte
check("leere Quelle laesst den Puffer in Ruhe", len(fb.buf) == laenge)
f.blit(100, 100, 50, 50, muster(50, 10))           # zu kurz: 10 statt 50 Zeilen
check("zu kurze Quelle laesst den Puffer in Ruhe", len(fb.buf) == laenge)
f.blit(100, 100, 50, 50, muster(50, 50)[:-7])      # angebrochene letzte Zeile
check("angebrochene letzte Zeile ebenfalls", len(fb.buf) == laenge)
f.blit(-5, 10, 20, 20, muster(20, 20))
f.blit(10, -5, 20, 20, muster(20, 20))
f.blit(5000, 10, 20, 20, muster(20, 20))
check("Punkte ausserhalb des Schirms werden abgewiesen",
      len(fb.buf) == laenge)

# Und die Probe, dass eine zu kurze Quelle nicht einfach ALLES
# verwirft: was hineinpasst, soll auch ankommen.
fb.clear((0, 0, 0))
teil = muster(50, 50)[:50 * 20 * 4]                # nur 20 volle Zeilen
f.blit(100, 100, 50, 50, teil)
o = 100 * fb.stride + 100 * 4
check("von einer zu kurzen Quelle kommt an, was da ist",
      bytes(fb.buf[o:o + 4]) == teil[:4],
      "%r vs %r" % (bytes(fb.buf[o:o + 4]), teil[:4]))

# ---------------------------------------------------------------------
print()
print("Test 3: und es ist wirklich schneller")
# perf_counter(), NICHT monotonic(): der Pruefstand ersetzt monotonic()
# durch eine STEHENDE Uhr (siehe NOW in tools/_harness.py), damit Tests
# nicht von der echten Zeit abhaengen. Beim ersten Anlauf massen beide
# Fassungen dadurch 0.00 ms und der Test schlug fehl - die Messung lief
# gegen eine Uhr, die sich nie bewegt.
def _bestes(fn, laeufe=5, je=10):
    """Der BESTE von mehreren Durchgaengen, nicht der erste.

    GEAENDERT (Build 191). Vorher wurde einmal gemessen, und genau das
    ist an einem Abend zweimal grundlos rot geworden ("alt 0.35 ms,
    neu 0.35 ms"), weil nebenher die uebrige Testreihe lief. Der beste
    Lauf ist der, in dem die Maschine am wenigsten dazwischenkam - und
    fuer die Frage "ist der neue Weg schneller als der alte" ist genau
    das die ehrliche Zahl.

    Ein Test, der bei Last rot wird, ist schlimmer als keiner: man
    gewoehnt sich an rote Zeilen und sieht die echte nicht mehr."""
    beste = None
    for _ in range(laeufe):
        t0 = time.perf_counter()
        for _ in range(je):
            fn()
        dt = (time.perf_counter() - t0) / je * 1000
        beste = dt if beste is None else min(beste, dt)
    return beste


for w, h, name in ((411, 548, "Galerie-Cover"), (733, 909, "Listen-Cover")):
    pix = muster(w, h)
    a = _bestes(lambda: alt_blit(fb, 100, 100, w, h, pix))
    b = _bestes(lambda: f.blit(100, 100, w, h, pix))
    # Bewusst nur "schneller", nicht "mindestens Faktor X": unter
    # paralleler Last schwanken solche Messungen, und ein Test, der
    # gelegentlich grundlos rot wird, wird irgendwann ignoriert.
    check("%-14s schneller als vorher" % name, b < a,
          "alt %.2f ms, neu %.2f ms (Faktor %.1f)" % (a, b, a / b if b else 0))

print()
if fails:
    print("FEHLGESCHLAGEN (%d):" % len(fails))
    for f_ in fails:
        print("  -", f_)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
