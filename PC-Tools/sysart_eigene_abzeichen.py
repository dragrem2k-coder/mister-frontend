#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sysart_eigene_abzeichen.py - Abzeichen fuer Testarchiv und Zeitmaschine
=======================================================================
(Build 353) Laeuft auf dem PC, NICHT auf dem MiSTer. Benoetigt Pillow.

NUTZERWUNSCH: "wir braeuchten dann auch noch fuer die kategorien die neu
sind entsprechende abzeichen/bilder, die dann rechts daneben, wo die
anderen angezeigt werden ... dort steht jetzt ja nur der Name! also fuer
Testarchiv und Zeitmaschine!"

WOHER DAS MOTIV KOMMT
---------------------
Fuer diese beiden gibt es keine Vorlage - kein Geraet, kein Logo. Die
Motive sind deshalb HIER als Pixelgrafik gezeichnet, Punkt fuer Punkt
aus einfachen Formen: eine Taschenuhr mit einem Pfeil, der rueckwaerts
um sie herumlaeuft (Zeitmaschine), und ein Heftstapel mit Wertung
(Testarchiv). Eigene Arbeit, nichts uebernommen.

DIE FORM KOMMT VON sysart_karten.py: dasselbe beige Oval mit treppiger
Kante, dieselbe Schrift, dieselbe Kachel 320x420 auf C_PANEL - so sehen
die beiden aus wie die anderen 60. Das Werkzeug wird importiert, nicht
nachgebaut; aendert sich dort die Form, aendert sie sich hier mit.

Aufruf:
    python3 PC-Tools/sysart_eigene_abzeichen.py --ziel frontend/sysart \\
        --vorschau /tmp/eigene.png
"""

import argparse
import math
import os
import sys

_HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HIER)

try:
    from PIL import Image, ImageDraw
except ImportError:
    sys.exit("Pillow fehlt:  pip install Pillow")

import sysart_karten as K                                # noqa: E402

RASTER = 6               # jeder Bildpunkt der Pixelgrafik wird 6x6 gross

KONTUR = (30, 20, 14)
GOLD, GOLD_HELL, GOLD_DUNKEL = (232, 182, 52), (250, 222, 120), (176, 120, 30)
ZIFFERBLATT, ZIFFERBLATT_SCHATTEN = (246, 238, 214), (222, 208, 176)
BLAU, BLAU_HELL, BLAU_DUNKEL = (70, 90, 220), (130, 160, 255), (34, 34, 96)
VIOLETT, TUERKIS = (150, 60, 230), (80, 200, 240)
ROT, ROT_DUNKEL = (204, 44, 40), (130, 24, 24)
PAPIER, PAPIER_ALT = (246, 238, 214), (214, 202, 178)
HIMMEL, WIESE, SONNE = (96, 154, 232), (70, 168, 84), (250, 214, 70)
GRAU = (120, 112, 100)
WEISS = (255, 255, 255)


def _leer(b, h):
    return Image.new("RGBA", (b, h), (0, 0, 0, 0))


def _setzen(bild, x, y, farbe):
    if 0 <= x < bild.width and 0 <= y < bild.height:
        bild.putpixel((x, y), farbe + (255,))


def _kontur_drumherum(bild):
    """Jeder leere Punkt, der an einen gefuellten grenzt, wird Kontur -
    die dunkle Pixelkante, die alle Motive der anderen Abzeichen haben."""
    b, h = bild.size
    alt = bild.copy()
    for y in range(h):
        for x in range(b):
            if alt.getpixel((x, y))[3]:
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < b and 0 <= ny < h and alt.getpixel((nx, ny))[3]:
                    _setzen(bild, x, y, KONTUR)
                    break
    return bild


def _stern(bild, x, y, farbe):
    for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
        _setzen(bild, x + dx, y + dy, WEISS if (dx, dy) == (0, 0) else farbe)


# ----------------------------------------------------------------------
# ZEITMASCHINE: Taschenuhr, rueckwaerts umkreist
# ----------------------------------------------------------------------
def zeitmaschine():
    b, h = 42, 40
    bild = _leer(b, h)
    cx, cy = 21.0, 20.0
    # Der Pfeil: ein Ring, der rechts eine Luecke fuer die Spitze laesst.
    # Er laeuft GEGEN den Uhrzeigersinn - zurueck in der Zeit.
    for y in range(h):
        for x in range(b):
            dx, dy = x + 0.5 - cx, y + 0.5 - cy
            d = math.hypot(dx, dy)
            w = math.degrees(math.atan2(dy, dx)) % 360
            if 15.0 <= d < 18.0 and 40 <= w <= 330:
                innen = d < 16.0
                _setzen(bild, x, y, BLAU_HELL if innen and w > 180 else
                        (BLAU if d < 17.0 else VIOLETT))
    # Die Spitze am Ende (unten rechts, bei 40 Grad), in Laufrichtung.
    w0 = math.radians(40)
    px, py = cx + 16.5 * math.cos(w0), cy + 16.5 * math.sin(w0)
    tx, ty = math.sin(w0), -math.cos(w0)          # Laufrichtung
    nx, ny = math.cos(w0), math.sin(w0)           # nach aussen
    spitze = [(px + tx * 5.5, py + ty * 5.5),
              (px - tx * 0.5 + nx * 4.2, py - ty * 0.5 + ny * 4.2),
              (px - tx * 0.5 - nx * 4.2, py - ty * 0.5 - ny * 4.2)]
    ImageDraw.Draw(bild).polygon(spitze, fill=BLAU + (255,))
    # Die Uhr: Goldrand mit Licht oben links, Zifferblatt.
    for y in range(h):
        for x in range(b):
            dx, dy = x + 0.5 - cx, y + 0.5 - cy
            d = math.hypot(dx, dy)
            if d < 8.8:
                _setzen(bild, x, y, ZIFFERBLATT_SCHATTEN
                        if dx + dy > 8 else ZIFFERBLATT)
            elif d < 11.4:
                licht = -dx - dy
                _setzen(bild, x, y, GOLD_HELL if licht > 8 else
                        (GOLD_DUNKEL if licht < -8 else GOLD))
    # Striche bei 12, 3, 6, 9
    for ex, ey in ((0, -1), (1, 0), (0, 1), (-1, 0)):
        _setzen(bild, int(cx + ex * 7.0), int(cy + ey * 7.0), KONTUR)
    # Zeiger: Minute auf 12, Stunde auf 10
    for k in range(1, 6):
        _setzen(bild, int(cx), int(cy - k), KONTUR)
    for k in range(1, 5):
        _setzen(bild, int(cx - k * 0.87), int(cy - k * 0.5), KONTUR)
    _setzen(bild, int(cx), int(cy), ROT)
    _kontur_drumherum(bild)
    _stern(bild, 3, 3, TUERKIS)
    _stern(bild, 38, 3, VIOLETT)
    _stern(bild, 2, 36, VIOLETT)
    return bild


# ----------------------------------------------------------------------
# TESTARCHIV: Heftstapel mit Wertung
# ----------------------------------------------------------------------
_ZIFFERN = {
    "9": ("###", "#.#", "###", "..#", "###"),
    "1": (".#.", "##.", ".#.", ".#.", "###"),
    "%": ("#.#", "..#", ".#.", "#..", "#.#"),
}


def _heft(bild, x0, y0, b, h, papier, kopf):
    for y in range(y0, y0 + h):
        for x in range(x0, x0 + b):
            _setzen(bild, x, y, kopf if y < y0 + 4 else papier)


def testarchiv():
    b, h = 40, 36
    bild = _leer(b, h)
    # Zwei Hefte dahinter, versetzt
    _heft(bild, 14, 1, 21, 27, PAPIER_ALT, ROT_DUNKEL)
    _heft(bild, 10, 3, 21, 27, PAPIER_ALT, ROT_DUNKEL)
    bild = _kontur_drumherum(bild)
    # Das vordere Heft
    x0, y0, hb, hh = 4, 6, 22, 28
    for y in range(y0 - 1, y0 + hh + 1):
        for x in range(x0 - 1, x0 + hb + 1):
            _setzen(bild, x, y, KONTUR)
    _heft(bild, x0, y0, hb, hh, PAPIER, ROT)
    # Schriftzug im Kopf: helle Kloetzchen
    for x in range(x0 + 2, x0 + hb - 2):
        if (x - x0) % 4 != 1:
            _setzen(bild, x, y0 + 1, WEISS)
            _setzen(bild, x, y0 + 2, WEISS)
    # Titelbild: Himmel, Sonne, Huegel
    for y in range(y0 + 6, y0 + 16):
        for x in range(x0 + 2, x0 + hb - 2):
            huegel = y > y0 + 12 - int(2 * math.sin((x - x0) / 3.0))
            _setzen(bild, x, y, WIESE if huegel else HIMMEL)
    for y in range(y0 + 7, y0 + 10):
        for x in range(x0 + hb - 7, x0 + hb - 4):
            _setzen(bild, x, y, SONNE)
    # Textzeilen
    for y in (y0 + 18, y0 + 20, y0 + 22):
        for x in range(x0 + 2, x0 + 12 + (y % 3) * 2):
            _setzen(bild, x, y, GRAU)
    # Die Wertung: rotes Feld mit "91%", ueber der Ecke
    wx, wy, wb, wh = 21, 23, 17, 10
    for y in range(wy - 1, wy + wh + 1):
        for x in range(wx - 1, wx + wb + 1):
            ecke = (x in (wx - 1, wx + wb) and y in (wy - 1, wy + wh))
            if not ecke:
                _setzen(bild, x, y, KONTUR)
    for y in range(wy, wy + wh):
        for x in range(wx, wx + wb):
            _setzen(bild, x, y, ROT)
    tx = wx + 2
    for z in "91%":
        for zy, zeile in enumerate(_ZIFFERN[z]):
            for zx, c in enumerate(zeile):
                if c == "#":
                    _setzen(bild, tx + zx, wy + 3 + zy, WEISS)
        tx += 5
    _stern(bild, 36, 33, (250, 214, 70))
    return bild


ABZEICHEN = (("ZEITMASCHINE", zeitmaschine, "ZEITMASCHINE"),
             ("TESTARCHIV", testarchiv, "TESTARCHIV"))


def main(argv=None):
    p = argparse.ArgumentParser(
        description="Abzeichen fuer Testarchiv und Zeitmaschine")
    p.add_argument("--ziel", default="frontend/sysart")
    p.add_argument("--vorschau", default=None)
    a = p.parse_args(argv)
    if not os.path.isdir(a.ziel):
        sys.exit("Zielordner fehlt: %s" % a.ziel)
    fertig = []
    for schluessel, motiv, text in ABZEICHEN:
        pixel = motiv()
        gross = pixel.resize((pixel.width * RASTER, pixel.height * RASTER),
                             Image.NEAREST)
        kachel = K.abzeichen(gross, text)
        pfad = os.path.join(a.ziel, schluessel + ".art")
        n = K.schreiben(kachel, pfad)
        print("%-20s %dx%d  %.1f KB" % (os.path.basename(pfad), kachel.width,
                                         kachel.height, n / 1024.0))
        fertig.append(kachel)
    if a.vorschau:
        bogen = Image.new("RGB", (K.KACHEL_B * len(fertig), K.KACHEL_H),
                          K.C_PANEL)
        for i, k in enumerate(fertig):
            bogen.paste(k, (i * K.KACHEL_B, 0))
        bogen.save(a.vorschau)
        print("Vorschau: %s" % a.vorschau)


if __name__ == "__main__":
    main()
