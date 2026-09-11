#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft die einheitlichen Kategorie-Abzeichen (Build 99).

NUTZERWUNSCH: "Ausserdem haette ich gerne auf der Hauptseite die alten
Sysarts durch diese hier ersetzt, damit es einheitlich aussieht. Alle
bitte auf eine Hoehe setzen, mittig rechts neben den Kategorien, und die
alten sollten dafuer raus. Soll alles die gleiche Groesse haben, ohne
dass ein Rahmen neu gezeichnet werden muss."

WORAUF ES ANKOMMT: "die gleiche Groesse" ist hier keine Kosmetik. Weil
alle Kacheln gleich gross sind, deckt das neue Abzeichen beim
Kategoriewechsel das alte IMMER vollstaendig ab - es muss nichts
freigeraeumt werden, und es gibt nichts, was je nach Bild anders
aussieht. Sobald auch nur EINE Datei aus der Reihe faellt, gilt das
nicht mehr, und es bleiben Reste stehen.

Ausfuehren:
    python3 tools/test_kategorie_abzeichen.py
"""
import glob
import os
import struct
import sys
import zlib

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_REPO, "frontend"))

SYSART = os.path.join(_REPO, "frontend", "sysart")
C_PANEL_BGRA = (44, 32, 28, 0)      # C_PANEL = RGB(28,32,44), siehe frontend.py
KACHEL = (320, 420)

# ALLE Kategorien, die es im Frontend gibt - namentlich festgehalten,
# damit ein versehentliches Loeschen oder ein neu dazugekommenes System
# ohne Abzeichen auffaellt. Seit Build 100 ist die Liste vollstaendig:
# 48 Spielesysteme plus neun Sonderkategorien.
ABZEICHEN = [
    "3DO", "ADVENTUREVISION", "ARCADE", "ARCADIA", "ASTROCADE",
    "ATARI2600", "ATARI5200", "ATARI7800", "ATARILYNX", "CASIOPV1000",
    "CDI", "CHANNELF", "COLECOVISION", "COLLECTIONS", "COMPUTER",
    "CONTINUE", "CREATIVISION", "FAVORITES", "FDS", "GAMATE", "GAMEBOY",
    "GAMEGEAR", "GAMENWATCH", "GBA", "GBC", "Genesis", "INTELLIVISION",
    "JAGUAR", "MEGADUCK", "MegaCD", "N64", "NEOGEO", "NEOGEOCD", "NES",
    "ODYSSEY2", "POCKETCHALLENGEV2", "POKEMONMINI", "PSX", "RA_HUNTER",
    "RECENT", "S32X", "SG1000", "SMS", "SMW_HACKS", "SNES",
    "SNES_ALTTP_TRACKER", "SUPERGAMEBOY", "SYSTEM", "Saturn", "TGFX16",
    "TGFX16CD", "VC4000", "VECTREX", "VIRTUALBOY", "WONDERSWAN",
    "WONDERSWANCOLOR", "WOT",
]

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


def lesen(pfad):
    d = open(pfad, "rb").read()
    if d[:4] != b"ART1":
        raise ValueError("kein ART1")
    w, h = struct.unpack("<HH", d[4:8])
    return w, h, zlib.decompress(d[8:]), len(d)


print("Test 1: jedes Abzeichen liegt vor und hat die Kachelgroesse")
for key in ABZEICHEN:
    pfad = os.path.join(SYSART, "%s.art" % key)
    if not os.path.isfile(pfad):
        check("%s.art vorhanden" % key, False)
        continue
    w, h, pix, groesse = lesen(pfad)
    check("%-20s %dx%d" % (key, w, h), (w, h) == KACHEL,
          "erwartet %dx%d" % KACHEL)
    check("%-20s Bilddaten passen" % key, len(pix) == w * h * 4)

print("Test 2: Hintergrund ist C_PANEL - sonst steht ein heller Kasten "
      "auf der Karte")
for key in ABZEICHEN:
    pfad = os.path.join(SYSART, "%s.art" % key)
    if not os.path.isfile(pfad):
        continue
    w, h, pix, _g = lesen(pfad)
    ecken = [tuple(pix[i:i + 4]) for i in
             (0, (w - 1) * 4, (h - 1) * w * 4, (h * w - 1) * 4)]
    check("%-20s alle vier Ecken C_PANEL" % key,
          all(e == C_PANEL_BGRA for e in ecken), "%s" % (ecken,))

print("Test 3: die Dateien sind nicht unnoetig gross")
# Die alten Logos lagen bei 900 Punkten Breite - SYSTEM.art war dadurch
# 379 KB gross, um am Ende 300 Punkte breit gezeigt zu werden. Jede
# Kachel wird beim Anzeigen komplett entpackt; das kostet Zeit und
# Speicher auf der schwachen MiSTer-CPU.
groessen = []
for key in ABZEICHEN:
    pfad = os.path.join(SYSART, "%s.art" % key)
    if os.path.isfile(pfad):
        groessen.append((os.path.getsize(pfad), key))
groessen.sort(reverse=True)
if groessen:
    check("groesste Kachel unter 200 KB", groessen[0][0] < 200_000,
          "%s: %d B" % (groessen[0][1], groessen[0][0]))
    schnitt = sum(g for g, _k in groessen) / len(groessen)
    print("       Durchschnitt %d B ueber %d Kacheln"
          % (schnitt, len(groessen)))

print("Test 4: der Zeichenpfad malt keinen Rahmen mehr")
# Der Rahmen in Systemfarbe war der einzige Grund, warum sich beim
# Kategoriewechsel etwas AUSSERHALB des Bildes aendern konnte. Faellt
# er weg und sind alle Kacheln gleich gross, deckt das neue Abzeichen
# das alte restlos ab.
src = open(os.path.join(_REPO, "frontend", "frontend.py"),
           encoding="utf-8", errors="replace").read()
block = src[src.index("def _draw_cat_artbox"):]
block = block[:block.index("def draw_page_items")]
check("kein Rahmen in Akzentfarbe mehr",
      "aw + 4 * s, 2 * s, accent" not in block)
check("kein Schattenstreifen unter dem Bild mehr",
      "blend_rect_fast" not in block)
check("die Karte kommt aus dem zusammengefassten Aufruf (Build 98)",
      "karte_mit_schatten(" in block)

print("Test 5: alle Kategorien landen an derselben Stelle")
# Der eigentliche Nutzerwunsch: "alle bitte auf eine Hoehe setzen,
# mittig rechts neben den Kategorien". Gleich grosse Kacheln allein
# genuegen dafuer nicht - der Zeichenpfad muss sie auch mittig setzen.
sys.path.insert(0, _HERE)
import _harness as H                                   # noqa: E402
fm = H.fm
import fe.art as A                                     # noqa: E402
A.SYSART_BASE = SYSART
fm.SYSART_BASE = SYSART

for w, h, name in ((320, 240, "CRT"), (1920, 1080, "HDMI")):
    H.set_screen(w, h)
    f = H.make_frontend(page=0)
    stellen = set()
    echt_blit = f.blit

    def merken(x, y, bw, bh, pix, _s=stellen):
        _s.add((x, y, bw, bh))
        return echt_blit(x, y, bw, bh, pix)

    f.blit = merken
    for i in range(len(f.cats)):
        f.cat_i = i
        f.cat_scroll = 0
        f.draw_page_cats(flip=False)
    check("%s: alle Abzeichen im selben Rechteck" % name,
          len(stellen) <= 1, "(%d verschiedene: %s)"
          % (len(stellen), sorted(stellen)[:3]))

print()
if fails:
    print("FEHLGESCHLAGEN (%d):" % len(fails))
    for f_ in fails:
        print("  -", f_)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
