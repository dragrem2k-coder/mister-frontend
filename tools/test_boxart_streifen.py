#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft, dass das Restore-Band die Boxart-Karte nicht anknabbert
(Build 80).

AUSLOESER (Nutzer-Rueckmeldung, CRT-Modus):

    "wenn ich jetzt nach unten gedrueckt halte und die roms
     durchsuche und die liste weiter nach unten laeuft ... wird ein
     teil der boxart und der gameinfo mit einen schwarzen block nicht
     mehr sichtbar. sobald ich loslasse sieht man wieder alles."

URSACHE: der schnelle Seitenpfad stellt vor dem Neuzeichnen der Zeilen
den Hintergrund der Listenspalte wieder her - mit 10*s Rand nach jeder
Seite. Die Boxart-Karte beginnt aber auf CRT schon 2*s rechts von der
Liste (auf HDMI erst 14*s). Das Band wischte also 8 Pixel WEIT IN DIE
KARTE hinein.

Sichtbar wurde das erst mit Build 76, seit dem die Karte waehrend des
Scrollens nicht mehr bei jedem Schritt darueber gemalt wird. Der Fehler
selbst ist aelter - genau deshalb dieser Test: er prueft die
Ueberlappung DIREKT, nicht ueber den Umweg "faellt es gerade auf".

Ausfuehren:
    python3 tools/test_boxart_streifen.py
"""
import os
import sys

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


def aufbauen(w, h):
    H.set_screen(w, h)
    f = H.make_frontend(page=1, titles=H.TITLES * 6)
    f.draw_page_items()          # erster Aufbau: legt den schnellen
    f.draw_page_items()          # Schluessel an, zweiter nimmt ihn
    return f


def geometrie(f):
    L = f.layout_items(True)
    s = L["s"]
    list_right = L["list_right"]
    karte = fm.art_karte_x0(list_right, f.fb.height, s)
    spalte = fm.art_spalte_x0(list_right, f.fb.height, s)
    return L, s, list_right, karte, spalte


def spalte_lesen(fb, x, y0, y1):
    """Eine senkrechte Pixelspalte als Bytes - damit laesst sich
    vergleichen, ob dort noch dasselbe steht wie vorher."""
    out = bytearray()
    for y in range(y0, y1):
        i = y * fb.stride + x * 4
        out += fb.buf[i:i + 3]
    return bytes(out)


print("Test 1: warum ein fester Rand von 10*s falsch sein MUSSTE")
# Kein Test der Loesung, sondern der Nachweis der Voraussetzung: der
# Abstand zwischen Liste und Karte ist NICHT konstant. Genau das hat
# der feste Rand stillschweigend angenommen. Bleibt dieser Test gruen,
# ist klar, dass jede kuenftige feste Pixelzahl an dieser Stelle
# denselben Fehler wieder erzeugen wuerde.
ERWARTET_UEBERLAPPUNG = {(320, 240): True,     # CRT: Karte ab +2*s
                         (640, 480): False,    # 480p: ab +14*s
                         (1920, 1080): False}  # HDMI: ab +42
for (w, h), ueberlappt in ERWARTET_UEBERLAPPUNG.items():
    H.set_screen(w, h)
    f = fm.Frontend()
    L = f.layout_items(True)
    s, list_right = L["s"], L["list_right"]
    abstand = fm.art_karte_x0(list_right, h, s) - list_right
    check("%dx%d: fester Rand 10*s wuerde %s" % (
              w, h, "in die Karte greifen" if ueberlappt else "passen"),
          (10 * s > abstand) == ueberlappt,
          "Karte ab +%d, Rand waere +%d" % (abstand, 10 * s))
    # Und das ist die Absicherung: der TATSAECHLICH benutzte Rand haelt
    # sich in jedem Fall links der Karte.
    rand = min(10 * s, max(0, abstand))
    check("%dx%d: benutzter Rand bleibt links der Karte" % (w, h),
          rand <= abstand, "Band bis +%d" % rand)

print()
print("Test 2: die Karte bleibt stehen, auch wenn das Panel ausgelassen "
      "wird")
# Der eigentliche Beweis - auf Pixelebene, nicht ueber die Rechnung:
# Panel-Zeichnen abklemmen (so verhaelt sich Build 76 beim schnellen
# Scrollen), dann eine Seite weiterscrollen und nachsehen, ob die
# Karte noch da ist, wo sie war.
for w, h, name in ((320, 240, "CRT"), (1920, 1080, "HDMI")):
    f = aufbauen(w, h)
    L, s, list_right, karte, _spalte = geometrie(f)
    y0 = L["list_y"] + 2 * s
    y1 = y0 + L["visible"] * L["rowh"] - 2 * s
    # Genau die Spalte, die frueher weggewischt wurde: das erste Pixel
    # der Karte.
    vorher = spalte_lesen(f.fb, karte, y0, y1)

    echt = f.draw_art_panel
    f.draw_art_panel = lambda *a, **k: None
    try:
        f.item_i = min(len(f._display_items()) - 1,
                       f.item_i + L["visible"])
        f.scroll = f.item_i - L["visible"] + 1
        f.draw_page_items()
    finally:
        f.draw_art_panel = echt
    nachher = spalte_lesen(f.fb, karte, y0, y1)
    check("%s: Kartenkante unveraendert nach dem Scrollen" % name,
          vorher == nachher,
          "%d von %d Pixeln veraendert"
          % (sum(1 for a, b in zip(vorher, nachher) if a != b) // 3,
             len(vorher) // 3))

print()
print("Test 3: das Panel-Auslassen greift nur dort, wo es nachgemessen "
      "hilft")
# Build 76 spart auf HDMI ueber 100 ms pro Scroll-Schritt (Cover
# 697x729). Auf CRT ist dasselbe Cover 96x99 - dort steht der kleinen
# Ersparnis ein voller Seitenaufbau nach jedem Stillstand gegenueber
# (COVER_SETTLE), weil jedes Auslassen ART._deferred_something setzt.
# Nutzer-Rueckmeldung dazu: "hdmi modus scrollt jetzt gut ... ausserdem
# habe ich den leichten Eindruck, dass das Scrollen etwas schlechter
# laeuft beim CRT".
for w, h, name, soll_gezeichnet in ((320, 240, "CRT", True),
                                    (1920, 1080, "HDMI", False)):
    f = aufbauen(w, h)
    L = f.layout_items(True)
    aufrufe = []
    echt = f.draw_art_panel
    f.draw_art_panel = lambda *a, **k: aufrufe.append(1)
    # Schnelles Scrollen: Einstellung an UND Eingabe gerade eben.
    f._scroll_skip_vsync = lambda: True
    try:
        f.item_i = min(len(f._display_items()) - 1,
                       f.item_i + L["visible"])
        f.scroll = f.item_i - L["visible"] + 1
        f.draw_page_items()
    finally:
        f.draw_art_panel = echt
    check("%s: Boxart-Spalte wird %s" % (name, "gezeichnet"
                                         if soll_gezeichnet
                                         else "ausgelassen"),
          bool(aufrufe) == soll_gezeichnet,
          "%d Aufrufe" % len(aufrufe))

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for f_ in fails:
        print("  -", f_)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
