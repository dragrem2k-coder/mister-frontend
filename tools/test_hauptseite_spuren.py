#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft den schnellen Zeichenweg der Hauptseite (Build 108).

NUTZER-RUECKMELDUNG: "Im Hauptmenue scrollt es noch etwas langsam,
wirkt etwas traege" - auf HDMI.

GEMESSEN: ein Kategorieschritt kostete 1.90 ms. Davon 0.64 ms allein
fb.clear(), also eine Kopie von 8,3 MB - bei JEDEM Schritt. Auf der
MiSTer-Hardware mit ihrer viel geringeren Speicherbandbreite ein
Vielfaches davon.

Seite 1 hat diesen Schritt seit Build 76 hinter sich; Seite 0 bekommt
ihn jetzt. Aendert sich an der Form der Seite nichts, bleibt der
Hintergrund stehen und es wird nur freigeraeumt, was im vorigen Bild
wirklich bemalt war.

WARUM DIESER TEST DAS BILD PRUEFT UND NICHT DIE ZEIT: wird auch nur ein
Bildpunkt zu wenig freigeraeumt, bleibt bei jedem Schritt ein Rest
stehen - und weil jeder Schritt auf dem vorigen aufsetzt, verschmiert
die Seite. Dieselbe Sorte Fehler hat beim Scroll-Blitting (Build 96)
zweimal zugeschlagen und war beim Lesen des Codes nicht zu sehen.

Ausfuehren:
    python3 tools/test_hauptseite_spuren.py
"""
import hashlib
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)

import _harness as H                                    # noqa: E402

fm = H.fm
sys.path.insert(0, os.path.join(_REPO, "frontend"))
import fe.art as A                                      # noqa: E402

SYSART = os.path.join(_REPO, "frontend", "sysart")
A.SYSART_BASE = SYSART
fm.SYSART_BASE = SYSART

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
    stellen = [i // 4 for i in range(0, len(ab), 4) if ab[i:i + 3] != bb[i:i + 3]]
    if not stellen:
        return 0, []
    return len(stellen), stellen[:3]


KEYS = [x[:-4] for x in sorted(os.listdir(SYSART)) if x.endswith(".art")]


def seite(w, h, anzahl=None):
    H.set_screen(w, h)
    f = H.make_frontend(page=0)
    namen = KEYS if anzahl is None else KEYS[:anzahl]
    f.cats = [(k, {"items": [], "folders": {}}, None) for k in namen]
    f.cat_i = 0
    f.cat_scroll = 0
    f.draw_page_cats(flip=False)
    return f


def voll(f, wie=None):
    """Denselben Zustand garantiert komplett neu aufbauen.

    'wie' ist die Seite, gegen die verglichen wird. Von ihr wird der
    Startzeitpunkt des Schimmer-Effekts uebernommen - _pulse_factor()
    rechnet gegen self._pulse_t0, und das ist ein Wert JE INSTANZ. Ohne
    diese Zeile vergleicht man zwei verschiedene Schimmer-Phasen und
    haelt den Farbunterschied faelschlich fuer einen Zeichenfehler.
    Genau darauf bin ich beim Absichern hereingefallen: 2022
    abweichende Bildpunkte auf CRT, die nichts mit dem Freiraeumen zu
    tun hatten (auf HDMI fiel es nicht auf, dort wird die Schimmerfarbe
    auf gröbere Stufen gerundet)."""
    if wie is not None:
        f._pulse_t0 = wie._pulse_t0
    f.fb.mark_full_redraw()
    f.draw_page_cats(flip=False)


def lauf(w, h, schritte, richtung=1, label=""):
    f = seite(w, h)
    n = len(f.cats)
    f.draw_page_cats(flip=False)          # ab hier greift der schnelle Weg
    # ... aber NUR oberhalb der Bildgroessen-Schwelle. Auf CRT ist
    # fb.clear() eine einzige Kopie von 307 KB und damit billiger als
    # ein Dutzend einzeln freigeraeumter Rechtecke - nachgemessen
    # -23 %. Dort bleibt es deshalb beim vollen Aufbau, und der
    # Bildvergleich unten prueft dann eben den.
    erwartet_schnell = h >= fm.KOMPAKT_H
    check("%s: schneller Weg %s" % (label, "aktiv" if erwartet_schnell
                                    else "bewusst AUS"),
          getattr(f, "_pgc_fast_taken", False) == erwartet_schnell)
    for _ in range(schritte):
        f.cat_i = (f.cat_i + richtung) % n
        # Mitscrollen wie die echte Navigation
        if f.cat_i < f.cat_scroll:
            f.cat_scroll = f.cat_i
        elif f.cat_i >= f.cat_scroll + f.cats_visible:
            f.cat_scroll = f.cat_i - f.cats_visible + 1
        f.draw_page_cats(flip=False)
    schnell = bytes(f.fb.buf)

    g = seite(w, h)
    g.cat_i = f.cat_i
    g.cat_scroll = f.cat_scroll
    voll(g, f)
    if gleich(schnell, g.fb.buf):
        check("%s: bitgenau wie voller Aufbau" % label, True)
    else:
        n_, wo = abweichung(schnell, g.fb.buf)
        check("%s: bitgenau wie voller Aufbau" % label, False,
              "%d Bildpunkte, z.B. %s" % (n_, wo))


print("Test 1: ein einzelner Kategorieschritt")
for w, h, name in ((320, 240, "CRT"), (1920, 1080, "HDMI")):
    lauf(w, h, 1, label="%s 1 Schritt" % name)
    lauf(w, h, 1, richtung=-1, label="%s 1 Schritt rueckwaerts" % name)

print("Test 2: dreissig Schritte am Stueck")
# Der Ernstfall: ein zu klein freigeraeumtes Rechteck laesst pro Schritt
# einen Rest stehen. Nach dreissig Schritten ist die Seite verschmiert,
# ein einzelner Schritt kann das noch verdecken.
for w, h, name in ((320, 240, "CRT"), (1920, 1080, "HDMI")):
    lauf(w, h, 30, label="%s 30 vorwaerts" % name)
    lauf(w, h, 30, richtung=-1, label="%s 30 rueckwaerts" % name)

print("Test 3: einmal ganz herum")
# Deckt den Uebergang ueber beide Listenenden ab und jede Kategorie
# mindestens einmal - damit auch jedes Abzeichen einmal auf jedem
# anderen liegt.
for w, h, name in ((320, 240, "CRT"), (1920, 1080, "HDMI")):
    lauf(w, h, len(KEYS) + 3, label="%s einmal rundum" % name)

print("Test 4: kurze Liste - weniger Kategorien als Plaetze")
for w, h, name in ((320, 240, "CRT"), (1920, 1080, "HDMI")):
    f = seite(w, h, anzahl=3)
    f.draw_page_cats(flip=False)
    f.cat_i = 2
    f.draw_page_cats(flip=False)
    g = seite(w, h, anzahl=3)
    g.cat_i = 2
    voll(g, f)
    if gleich(f.fb.buf, g.fb.buf):
        check("%s: kurze Liste bitgenau" % name, True)
    else:
        n_, wo = abweichung(f.fb.buf, g.fb.buf)
        check("%s: kurze Liste bitgenau" % name, False,
              "%d Bildpunkte, z.B. %s" % (n_, wo))

print("Test 5: nach einer anderen Bildschirmseite wird voll aufgebaut")
# Die Absicherung. Lief zwischendurch irgendetwas anderes ueber den
# Schirm, ist der Puffer nicht mehr unserer - dann MUSS wieder geleert
# werden, sonst bleiben Reste der fremden Seite stehen.
f = seite(1920, 1080)
f.draw_page_cats(flip=False)
check("vorher: schneller Weg", f._pgc_fast_taken)
check("auf CRT ist er aus (dort lohnt er nicht)",
      not seite(320, 240)._pgc_fast_taken)
f.fb.mark_full_redraw()
f.draw_page_cats(flip=False)
check("nach mark_full_redraw(): voller Aufbau", not f._pgc_fast_taken)
f.draw_page_cats(flip=False)
check("danach wieder schnell", f._pgc_fast_taken)

print("Test 6: Songtitel wird kuerzer - kein Rest in der Kopfzeile")
# Was die Vergleiche oben NICHT abdecken: sie laufen mit eingefrorener
# Uhr und ohne Musik. Genau die veraenderlichen Texte sind aber die
# Gefahr - der Zeichensatz malt seinen eigenen Hintergrund nur unter
# den Zeichen, die er setzt. Wird der neue Text kuerzer, bliebe der
# Schwanz des alten stehen, bis die Seite zufaellig einmal voll
# aufgebaut wird.
for w, h, name in ((320, 240, "CRT"), (1920, 1080, "HDMI")):
    f = seite(w, h)
    f._track_mq_name = "Ein sehr langer Songtitel der weit nach rechts reicht"
    f.draw_page_cats(flip=False)
    f.draw_page_cats(flip=False)
    f._track_mq_name = "Kurz"
    f.draw_page_cats(flip=False)
    g = seite(w, h)
    g._track_mq_name = "Kurz"
    g.cat_i, g.cat_scroll = f.cat_i, f.cat_scroll
    voll(g, f)
    if gleich(f.fb.buf, g.fb.buf):
        check("%s: kein Rest des langen Titels" % name, True)
    else:
        n_, wo = abweichung(f.fb.buf, g.fb.buf)
        check("%s: kein Rest des langen Titels" % name, False,
              "%d Bildpunkte, z.B. %s" % (n_, wo))

print("Test 7: Netzwerk faellt weg - kein Rest in der Statuszeile")
# Das Netzwerksymbol wird NUR gezeichnet, wenn eine Verbindung besteht.
# Faellt sie weg, entfernt es niemand - ausser dem Freiraeumen hier.
for w, h, name in ((320, 240, "CRT"), (1920, 1080, "HDMI")):
    f = seite(w, h)
    f._network_connected = lambda: True
    f.draw_page_cats(flip=False)
    f.draw_page_cats(flip=False)
    f._network_connected = lambda: False
    f.draw_page_cats(flip=False)
    g = seite(w, h)
    g._network_connected = lambda: False
    g.cat_i, g.cat_scroll = f.cat_i, f.cat_scroll
    voll(g, f)
    if gleich(f.fb.buf, g.fb.buf):
        check("%s: kein Rest des Netzwerksymbols" % name, True)
    else:
        n_, wo = abweichung(f.fb.buf, g.fb.buf)
        check("%s: kein Rest des Netzwerksymbols" % name, False,
              "%d Bildpunkte, z.B. %s" % (n_, wo))

print("Test 8: die ECHTE Navigationsmischung, Schritt fuer Schritt")
# DIESER TEST HAT GEFEHLT, und deshalb ist Build 108 mit einem sichtbaren
# Fehler ausgeliefert worden (Nutzer-Screenshot: zwei rote
# Markierungsbalken gleichzeitig, "wenn ich scrolle und das Bild
# verlasse nach oben oder unten").
#
# Die Vergleiche oben rufen immer nur draw_page_cats(). Im echten
# Ablauf wechseln sich aber DREI Wege ab: der leichte
# Navigationsschritt, der Puls-Takt und der volle Aufbau - und der
# Fehler entstand genau an der Naht. _draw_dynamic_cats() malt den
# Markierungsbalken selbst und trug sich nicht in die Spurbuchhaltung
# ein; die Spur dieser Zeile blieb auf "schmales Textfeld" stehen.
# Wanderte die Auswahl weiter, raeumte der schnelle Weg nur dieses
# schmale Feld frei - der Rest des Balkens blieb stehen.
#
# Zu sehen ist das erst NACH dem uebernaechsten Schritt. Verglichen
# wird deshalb nach JEDEM einzelnen.
for w, h, name in ((320, 240, "CRT"), (1920, 1080, "HDMI")):
    f = seite(w, h)
    f.draw_page_cats(flip=False)
    n = len(f.cats)
    schlecht = None
    for richtung in (1, -1):
        for schritt in range(1, 2 * n + 5):
            alt = f.cat_i
            f.cat_i = (f.cat_i + richtung) % n
            if not f._draw_navigate_cats(alt):
                f.draw_page_cats(flip=False)
            # Puls-Takt, wie ihn der Leerlauf-Zweig ausloest
            H.NOW[0] += 0.5
            f._draw_dynamic_cats(flip=False)
            g = seite(w, h)
            g.cat_i, g.cat_scroll = f.cat_i, f.cat_scroll
            voll(g, f)
            if not gleich(f.fb.buf, g.fb.buf):
                n_, wo = abweichung(f.fb.buf, g.fb.buf)
                schlecht = ("Richtung %+d, Schritt %d (cat_i=%d, scroll=%d): "
                            "%d Bildpunkte, z.B. %s"
                            % (richtung, schritt, f.cat_i, f.cat_scroll,
                               n_, wo))
                break
        if schlecht:
            break
    check("%s: leicht + Puls + voll gemischt bleibt sauber" % name,
          schlecht is None, schlecht or "")

print("Test 9: es wird wirklich weniger Flaeche angefasst")
# Ohne diese Pruefung koennte die Aenderung unbemerkt wirkungslos sein -
# alle Bildvergleiche oben wuerden weiterhin bestehen.
for w, h, name in ((320, 240, "CRT"), (1920, 1080, "HDMI")):
    f = seite(w, h)
    f.draw_page_cats(flip=False)
    f.draw_page_cats(flip=False)
    ganz = w * h
    spuren = sum(sw * sh for _x, _y, sw, sh in f._kat_spur.values())
    if h < fm.KOMPAKT_H:
        continue          # dort wird bewusst voll aufgebaut, siehe oben
    check("%s: Spuren viel kleiner als der ganze Schirm" % name,
          0 < spuren < ganz // 4,
          "%d von %d Bildpunkten (%.0f%%)"
          % (spuren, ganz, spuren * 100.0 / ganz))

print()
if fails:
    print("FEHLGESCHLAGEN (%d):" % len(fails))
    for f_ in fails:
        print("  -", f_)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
