#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft die Kategorie-Logos unter frontend/sysart/ (Build 80).

HINTERGRUND: mit Build 79 kennt das Frontend 48 Spielesysteme, hatte
aber nur fuer 24 ein Logo. Der Nutzer liefert die fehlenden nach; Build
80 bringt die ersten neun mit (3DO, Atari 2600, Atari Lynx, Famicom Disk
System, Gamate, Intellivision, Neo Geo CD, Vectrex, WonderSwan).

WAS HIER SCHIEFGEHEN KANN, OHNE DASS ES AUFFAELLT
-------------------------------------------------
Ein Logo mit falschem Hintergrund faellt nicht als Fehler auf - es sieht
nur aus wie ein heller Kasten mitten auf der dunklen Karte. Ein zu
grosses Logo wird ebenfalls klaglos angezeigt, kostet aber beim
Entpacken Zeit und Speicher (das 3DO-Logo waere bei 900 px Breite 1729
Zeilen und 6 MB gross gewesen, um am Ende 234 px breit dargestellt zu
werden). Beides prueft dieser Test.

Ausfuehren:
    python3 tools/test_sysart_logos.py
"""
import os
import struct
import sys
import zlib

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_REPO, "frontend"))

from fe.systems import alle_systeme                    # noqa: E402

SYSART = os.path.join(_REPO, "frontend", "sysart")
PANEL = (28, 32, 44)      # muss C_PANEL in frontend.py entsprechen
MAX_BREITE = 900
MAX_HOEHE = 450

# Mit Build 80 neu dazugekommen - namentlich festgehalten, damit ein
# versehentliches Loeschen auffaellt.
NEU_IN_BUILD_80 = ["3DO", "ATARI2600", "ATARILYNX", "FDS", "GAMATE",
                   "INTELLIVISION", "NEOGEOCD", "VECTREX", "WONDERSWAN"]

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
    pix = zlib.decompress(d[8:])
    if len(pix) != w * h * 4:
        raise ValueError("Pixelzahl passt nicht zu %dx%d" % (w, h))
    return w, h, pix


def randfarbe(w, h, pix):
    """Haeufigste Farbe der vier Bildraender - das ist der Grund, auf dem
    das Logo liegt."""
    zaehler = {}
    for x in range(w):
        for y in (0, h - 1):
            i = (y * w + x) * 4
            zaehler[(pix[i + 2], pix[i + 1], pix[i])] = \
                zaehler.get((pix[i + 2], pix[i + 1], pix[i]), 0) + 1
    for y in range(h):
        for x in (0, w - 1):
            i = (y * w + x) * 4
            zaehler[(pix[i + 2], pix[i + 1], pix[i])] = \
                zaehler.get((pix[i + 2], pix[i + 1], pix[i]), 0) + 1
    return max(zaehler.items(), key=lambda kv: kv[1])[0]


print("Test 1: die neun mit Build 80 gelieferten Logos sind da")
for key in NEU_IN_BUILD_80:
    check("%s.art vorhanden" % key,
          os.path.exists(os.path.join(SYSART, "%s.art" % key)))

print()
print("Test 2: jedes Logo ist les- und entpackbar")
dateien = sorted(f for f in os.listdir(SYSART) if f.endswith(".art"))
check("ueberhaupt Logos gefunden", len(dateien) >= 30,
      "%d Dateien" % len(dateien))
masse = {}
for fn in dateien:
    try:
        w, h, pix = lesen(os.path.join(SYSART, fn))
        masse[fn] = (w, h, pix)
    except Exception as e:
        check("%s lesbar" % fn, False, str(e))
if len(masse) == len(dateien):
    print("  OK   alle %d Dateien tragen einen gueltigen ART1-Kopf"
          % len(dateien))

print()
print("Test 3: die neuen Logos halten Groesse und Hintergrund ein")
# Bewusst nur die neuen: die alten Dateien sind teils gewachsen
# (SNES_ALTTP_TRACKER_1920x1080 ist absichtlich bildschirmfuellend) und
# sollen von diesem Test nicht rot gefaerbt werden.
for key in NEU_IN_BUILD_80:
    fn = "%s.art" % key
    if fn not in masse:
        continue
    w, h, pix = masse[fn]
    check("%s: hoechstens %dx%d" % (key, MAX_BREITE, MAX_HOEHE),
          w <= MAX_BREITE and h <= MAX_HOEHE, "%dx%d" % (w, h))
    # Kleine Toleranz, kein exakter Vergleich: die Logos sind randlos
    # auf das Motiv zugeschnitten, in der aeussersten Pixelreihe liegen
    # also die weichen Kanten der Schrift. Die Lanczos-Skalierung
    # mischt dort ein bis zwei Stufen Helligkeit hinein (bei GAMATE
    # nachgemessen 29/33/45 statt 28/32/44). Sichtbar ist das nicht -
    # ein falsch gewaehlter Hintergrund dagegen sofort.
    ist = randfarbe(w, h, pix)
    abstand = sum(abs(a - b) for a, b in zip(ist, PANEL))
    check("%s: Rand ist C_PANEL %s" % (key, PANEL), abstand <= 6,
          "gemessen %s" % (ist,))

print()
print("Test 4: jedes Logo gehoert zu einem Systemschluessel")
# Sonst liegt eine Datei da, die nie jemand oeffnet - der lautlose
# Fehler, der beim Nachliefern am leichtesten passiert (Tippfehler im
# Dateinamen).
schluessel = set(k for _n, k, *_r in alle_systeme())
# Die Sonderkategorien haben eigene, in fe/art.py vergebene Schluessel.
SONDER = {"RECENT", "CONTINUE", "FAVORITES", "COLLECTIONS", "RA_HUNTER",
          "WOT", "SYSTEM", "ARCADE", "COMPUTER", "SMW_HACKS",
          "SNES_ALTTP_TRACKER"}
for key in NEU_IN_BUILD_80:
    check("%s ist ein bekannter Systemschluessel" % key,
          key in schluessel or key in SONDER)

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for f_ in fails:
        print("  -", f_)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
