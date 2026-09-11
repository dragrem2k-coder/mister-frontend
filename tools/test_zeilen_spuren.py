#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft das gezielte Freiraeumen der Listenzeilen (Build 103).

WAS SICH GEAENDERT HAT: der schnelle Scroll-Pfad stellte bisher die
KOMPLETTE Listenspalte wieder her, bevor er die Zeilen neu zeichnete -
auf HDMI 859 mal 765 Bildpunkte, jede Bildzeile einzeln kopiert.
Gemessen war das mit 0.68 von 1.14 ms der groesste Einzelposten eines
Scrollschritts, groesser als alle siebzehn Zeilen zusammen.

Jetzt merkt sich jede Zeile, wie weit sie tatsaechlich gemalt hat, und
nur das wird beim naechsten Schritt freigeraeumt - in beiden Richtungen
weniger: ein mittlerer Titel belegt 45 % der Spaltenbreite, und der Text
ist 24 statt 45 Bildpunkte hoch.

WARUM DIESER TEST NICHT DIE GESCHWINDIGKEIT PRUEFT, SONDERN DAS BILD:
Wenn die gemerkte Ausdehnung auch nur einen Bildpunkt zu klein ist,
bleibt beim Scrollen ein Rest der alten Zeile stehen - und zwar
dauerhaft, weil jeder Schritt auf dem Ergebnis des vorigen aufsetzt.
Genau diese Sorte Fehler hat beim Scroll-Blitting (Build 96) zweimal
zugeschlagen und war beim Lesen des Codes nicht zu sehen. Verglichen
wird deshalb Bildpunkt fuer Bildpunkt gegen den vollen Neuaufbau -
einzeln und nach dreissig Schritten am Stueck.

Ausfuehren:
    python3 tools/test_zeilen_spuren.py
"""
import hashlib
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import _harness as H                                    # noqa: E402

fm = H.fm

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


def gleich(a, b):
    return (hashlib.sha256(bytes(a)).hexdigest()
            == hashlib.sha256(bytes(b)).hexdigest())


def abweichung(a, b):
    ab, bb = bytes(a), bytes(b)
    stellen = [i // 4 for i in range(0, len(ab), 4)
               if ab[i:i + 3] != bb[i:i + 3]]
    return len(stellen), stellen[:3]


LANG = "The Legend of Zelda - A Link to the Past und noch viel mehr Text"


def liste(w, h, anzahl=400, titel=None, mit_art=True):
    """Eine Liste aufbauen und EINMAL zeichnen (voller Aufbau)."""
    H.set_screen(w, h)
    f = H.make_frontend(page=1)
    node = f._current_node()
    if titel is None:
        node["items"] = [(H.TITLES[i % len(H.TITLES)] + " %d" % i, "game",
                          ("/f/%d.sfc" % i, ".sfc", "SNES", None, None))
                         for i in range(anzahl)]
    else:
        node["items"] = list(titel)
    node.pop("_display_items_cache", None)
    f.item_i = 0
    f.scroll = 0
    f.draw_page_items(flip=False)
    return f


def voll_zeichnen(f):
    """Denselben Zustand als VOLLEN Neuaufbau zeichnen.

    mark_full_redraw() zaehlt die Generation hoch - damit passt die
    gemerkte Generation des schnellen Pfads nicht mehr, und
    draw_page_items() baut garantiert alles neu auf."""
    f.fb.mark_full_redraw()
    f.draw_page_items(flip=False)


def vergleich(w, h, schritte, richtung=1, titel=None, start=None,
              label=""):
    """schritte Scrollschritte ueber den schnellen Pfad, danach gegen
    den vollen Aufbau desselben Zustands vergleichen."""
    f = liste(w, h, titel=titel)
    n = len(f._current_node()["items"])
    if start is None:
        start = 0 if richtung > 0 else min(n - 1, 200)
    f.item_i = start
    f.scroll = max(0, min(start, n - f.items_visible))
    f.draw_page_items(flip=False)
    f.draw_page_items(flip=False)        # ab hier laeuft der schnelle Pfad
    check("%s: schneller Pfad aktiv" % label,
          getattr(f, "_pgi_fast_taken", False))
    for _ in range(schritte):
        f.item_i += richtung
        f.scroll += richtung
        f.draw_page_items(flip=False)
    schnell = bytes(f.fb.buf)

    # Referenz: gleiche Position, aber komplett neu aufgebaut.
    g = liste(w, h, titel=titel)
    g.item_i = f.item_i
    g.scroll = f.scroll
    voll_zeichnen(g)
    if gleich(schnell, g.fb.buf):
        check("%s: bitgenau wie voller Aufbau" % label, True)
    else:
        n_, wo = abweichung(schnell, g.fb.buf)
        check("%s: bitgenau wie voller Aufbau" % label, False,
              "%d Bildpunkte, z.B. %s" % (n_, wo))


print("Test 1: ein einzelner Scrollschritt")
for w, h, name in ((320, 240, "CRT"), (1920, 1080, "HDMI")):
    vergleich(w, h, 1, label="%s 1 Schritt runter" % name)
    vergleich(w, h, 1, richtung=-1, label="%s 1 Schritt hoch" % name)

print("Test 2: dreissig Schritte am Stueck")
# Der eigentliche Ernstfall. Ein zu klein gemerktes Rechteck laesst pro
# Schritt einen Rest stehen; nach dreissig Schritten ist die Liste
# verschmiert. Ein einzelner Schritt kann das noch verdecken.
for w, h, name in ((320, 240, "CRT"), (1920, 1080, "HDMI")):
    vergleich(w, h, 30, label="%s 30 runter" % name)
    vergleich(w, h, 30, richtung=-1, label="%s 30 hoch" % name)

print("Test 3: lange Titel (Laufschrift) und wechselnde Textbreiten")
# Der gefaehrlichste Fall fuer diese Aenderung: eine LANGE Zeile wandert
# auf einen Platz, auf dem vorher eine KURZE stand - und umgekehrt.
# Steht das Merken auf der falschen Seite, bleibt der Ueberhang stehen.
gemischt = []
for i in range(400):
    name = LANG if i % 3 == 0 else ("Kurz %d" % i)
    gemischt.append((name, "game",
                     ("/f/%d.sfc" % i, ".sfc", "SNES", None, None)))
for w, h, name in ((320, 240, "CRT"), (1920, 1080, "HDMI")):
    vergleich(w, h, 30, titel=gemischt, label="%s lang/kurz gemischt" % name)

print("Test 4: Ordner-Eintraege zwischen Spielen")
# Ordner werden ohne den abschliessenden "/" gezeichnet - die gemalte
# Breite weicht also von der Rohlaenge ab.
ordner = []
for i in range(400):
    if i % 4 == 0:
        ordner.append(("Ein Unterordner %d/" % i, "folder", None))
    else:
        ordner.append((H.TITLES[i % len(H.TITLES)] + " %d" % i, "game",
                       ("/f/%d.sfc" % i, ".sfc", "SNES", None, None)))
for w, h, name in ((320, 240, "CRT"), (1920, 1080, "HDMI")):
    vergleich(w, h, 30, titel=ordner, label="%s mit Ordnern" % name)

print("Test 5: kurze Liste - Plaetze ohne Zeile")
# Weniger Eintraege als sichtbare Plaetze: unten bleiben leere Plaetze.
# Die duerfen keine Spur behalten, die ewig weiter freigeraeumt wird -
# und ein Wechsel von langer zu kurzer Liste darf nichts stehenlassen.
for w, h, name in ((320, 240, "CRT"), (1920, 1080, "HDMI")):
    kurz = [(H.TITLES[i % len(H.TITLES)], "game",
             ("/f/%d.sfc" % i, ".sfc", "SNES", None, None))
            for i in range(4)]
    f = liste(w, h, titel=kurz)
    f.draw_page_items(flip=False)
    f.item_i = 1
    f.draw_page_items(flip=False)
    g = liste(w, h, titel=kurz)
    g.item_i = 1
    voll_zeichnen(g)
    if gleich(f.fb.buf, g.fb.buf):
        check("%s: kurze Liste bitgenau" % name, True)
    else:
        n_, wo = abweichung(f.fb.buf, g.fb.buf)
        check("%s: kurze Liste bitgenau" % name, False,
              "%d Bildpunkte, z.B. %s" % (n_, wo))

print("Test 6: ohne Spuren wird die ganze Spalte freigeraeumt")
# Der Rueckfall muss greifen, sonst bliebe beim ersten Schritt nach
# einem Wechsel etwas stehen. Geprueft an der Funktion selbst.
f = liste(1920, 1080)
f.draw_page_items(flip=False)
f._zeilen_spur = {}
check("leere Spuren -> None", f._zeilen_spuren_holen(f.items_visible) is None)
f.draw_page_items(flip=False)
f._zeilen_spur_sig = ("etwas", "anderes")
check("andere Geometrie -> None",
      f._zeilen_spuren_holen(f.items_visible) is None)
f.draw_page_items(flip=False)
f.draw_page_items(flip=False)
alle = dict(f._zeilen_spur)
if alle:
    f._zeilen_spur = dict(list(alle.items())[1:])     # eine Zeile fehlt
    check("fehlender Zeilenplatz -> None",
          f._zeilen_spuren_holen(f.items_visible) is None)

print("Test 7: es wird wirklich weniger freigeraeumt")
# Ohne diese Pruefung koennte die Aenderung unbemerkt wirkungslos sein -
# alle Bildvergleiche oben wuerden weiterhin bestehen.
for w, h, name in ((320, 240, "CRT"), (1920, 1080, "HDMI")):
    f = liste(w, h)
    f.draw_page_items(flip=False)
    f.draw_page_items(flip=False)
    v = f.view
    s, rowh = v["s"], v["rowh"]
    vis = f.items_visible
    lm = 10 * s
    frueher = ((v["list_right"] - v["list_x"]) + 2 * lm) * (vis * rowh + 2 * lm)
    spuren = list(f._zeilen_spur.values())
    jetzt = sum(sw * sh for _x, _y, sw, sh in spuren)
    check("%s: weniger Flaeche als vorher" % name, jetzt < frueher * 0.6,
          "%d statt %d Bildpunkte (%.0f%%)"
          % (jetzt, frueher, jetzt * 100.0 / frueher))

print()
if fails:
    print("FEHLGESCHLAGEN (%d):" % len(fails))
    for f_ in fails:
        print("  -", f_)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
