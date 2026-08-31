#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft das engere Layout auf CRT (Nutzerwunsch: "haben wir irgendwie
ne Moeglichkeit, das Frontend im CRT-Modus huebscher aussehen zu
lassen?").

WAS DER MANGEL WAR
------------------
Mehrere Abstaende standen als FESTE Pixelzahl im Layout (Kopfblock 46,
Zeilenhoehe 15, Abstand zur Boxart-Karte 20, Kategorie-Zeilenhoehe 22).
Sie skalieren zwar ueber s = H//360 mit - aber s ist sowohl bei 240 als
auch bei 480 Zeilen gleich 1. Bei 240 Zeilen belegten diese Abstaende
also den doppelten ANTEIL des Bildes. Gemessen an echten, in beiden
Aufloesungen gerenderten Bildern:

                       CRT 320x240   HDMI 1920x1080
    Zeichen pro Zeile       17            35
    sichtbare Spiele        10            17
    Kategorien im Menue      7            12
    Kopfzeilenblock         24 %          18 %

WAS HIER GEPRUEFT WIRD
----------------------
"Sieht huebscher aus" kann kein Test pruefen. Geprueft wird deshalb das
objektiv Nachrechenbare - und vor allem die zwei Dinge, die beim Bauen
tatsaechlich schiefgegangen sind:

1. Der Gewinn ist da (mehr Zeilen, mehr Zeichen).
2. HDMI und 640x480 bleiben BIT-genau unveraendert - die Aenderung
   sollte ausschliesslich CRT betreffen.
3. Der Kopfbereich kollidiert nicht mit der ersten Zeile. Genau das ist
   beim Bauen ZWEIMAL passiert (Auswahlbalken lief in die Eintragszahl)
   und faellt in reinen Zahlen nicht auf - deshalb wird die Freiraum-
   Rechnung hier ausdruecklich mitgeprueft.

Ausfuehren:
    python3 tools/test_crt_layout.py
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import _harness as H                                 # noqa: E402

fm = H.fm
fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


def layouts(w, h):
    H.set_screen(w, h)
    f = H.make_frontend(page=0)
    f._layout_items_cache = {}
    return f, f.layout_cats(), f.layout_items(True), f.layout_items(False)


def kennzahlen(w, h):
    _f, Lc, Li, Lv = layouts(w, h)
    s = Li["s"]
    breite = Li["list_right"] - Li["list_x"]
    return {
        "s": s,
        "zeichen": breite // (8 * s),
        "zeilen": Li["visible"],
        "kategorien": Lc["visible"],
        "kopf_anteil": 100.0 * Li["list_y"] / h,
        "art_anteil": 100.0 * Lc["art_w"] / w,
        "voll_breite": Lv["list_right"] - Lv["list_x"],
        "L_items": Li,
        "L_cats": Lc,
    }


print("Test 1: auf CRT kommt tatsaechlich mehr aufs Bild")
crt = kennzahlen(320, 240)
# Die Zahlen VOR der Aenderung, gemessen am selben Weg: 17 Zeichen,
# 10 Zeilen, 7 Kategorien, Kopfblock 24 %. Bewusst als Untergrenze
# festgehalten, nicht als exakter Wert - eine spaetere weitere
# Verbesserung soll diesen Test nicht rot faerben.
check("mindestens 20 Zeichen pro Zeile (vorher 17)",
      crt["zeichen"] >= 20, "jetzt %d" % crt["zeichen"])
check("mindestens 13 Spiele gleichzeitig sichtbar (vorher 10)",
      crt["zeilen"] >= 13, "jetzt %d" % crt["zeilen"])
check("mindestens 9 Kategorien im Hauptmenue (vorher 7)",
      crt["kategorien"] >= 9, "jetzt %d" % crt["kategorien"])
check("Kopfblock hoechstens 21 % der Hoehe (vorher 24 %)",
      crt["kopf_anteil"] <= 21.0, "jetzt %.0f %%" % crt["kopf_anteil"])
check("Logo-Spalte hoechstens 30 % der Breite (vorher 34 %)",
      crt["art_anteil"] <= 30.0, "jetzt %.0f %%" % crt["art_anteil"])

print()
print("Test 2: nichts davon faellt auf grosse Schirme durch")
# Der eigentliche Sinn des Tests: die Aenderung soll AUSSCHLIESSLICH
# kleine Schirme betreffen. Diese Werte sind die vor der Aenderung
# gemessenen - jede Abweichung waere ein ungewollter Nebeneffekt.
ERWARTET = {
    (1920, 1080): {"s": 3, "zeichen": 35, "zeilen": 17, "kategorien": 12,
                   "rowh": 45, "list_y_off": 46, "art_w": 340},
    (640, 480):   {"s": 1, "zeichen": 35, "zeilen": 24, "kategorien": 16,
                   "rowh": 15, "list_y_off": 46, "art_w": 217},
}
for (w, h), soll in ERWARTET.items():
    ist = kennzahlen(w, h)
    Li, Lc = ist["L_items"], ist["L_cats"]
    check("%dx%d: %d Zeichen unveraendert" % (w, h, soll["zeichen"]),
          ist["zeichen"] == soll["zeichen"], "jetzt %d" % ist["zeichen"])
    check("%dx%d: %d Zeilen unveraendert" % (w, h, soll["zeilen"]),
          ist["zeilen"] == soll["zeilen"], "jetzt %d" % ist["zeilen"])
    check("%dx%d: %d Kategorien unveraendert" % (w, h, soll["kategorien"]),
          ist["kategorien"] == soll["kategorien"],
          "jetzt %d" % ist["kategorien"])
    check("%dx%d: Zeilenhoehe unveraendert" % (w, h),
          Li["rowh"] == soll["rowh"], "jetzt %d" % Li["rowh"])
    check("%dx%d: Kopfblock unveraendert" % (w, h),
          Li["list_y"] - Li["oy"] == soll["list_y_off"] * soll["s"],
          "jetzt %d" % (Li["list_y"] - Li["oy"]))
    check("%dx%d: Logo-Spalte unveraendert" % (w, h),
          Lc["art_w"] == soll["art_w"], "jetzt %d" % Lc["art_w"])

print()
print("Test 3: der Kopfbereich kollidiert nicht mit der ersten Zeile")
# BUGFIX-ABSICHERUNG: beim Bauen lief der Auswahlbalken zweimal in die
# Kopfzeile hinein, weil nur die Zeilenzahl nachgerechnet, aber nicht
# die Hoehe des Kopfes beruecksichtigt wurde. Beide Seiten werden hier
# nachgerechnet - die Zahlen stammen direkt aus dem Zeichencode:
#   Hauptmenue: "MiSTer" mit 3*s ab oy, Kategorienzahl 8*s hoch bei
#               oy+28*s; die Markierung beginnt 4*s OBERHALB von y0
#               (siehe _draw_cat_row()).
#   Spieleliste: Titel bis 2*s hoch ab oy, Eintragszahl 8*s hoch bei
#               oy+22*s; die Zeilen beginnen bei list_y.
for w, h in ((320, 240), (640, 480), (1920, 1080)):
    ist = kennzahlen(w, h)
    Li, Lc = ist["L_items"], ist["L_cats"]
    s = Li["s"]
    kopf_unterkante = Lc["oy"] + 28 * s + 8 * s
    balken_oberkante = Lc["y0"] - 4 * s
    check("%dx%d Hauptmenue: Balken beginnt unter der Kategorienzahl"
          % (w, h), balken_oberkante >= kopf_unterkante,
          "Balken %d, Text endet %d" % (balken_oberkante, kopf_unterkante))
    liste_kopf_unterkante = Li["oy"] + 22 * s + 8 * s
    check("%dx%d Spieleliste: erste Zeile beginnt unter der Eintragszahl"
          % (w, h), Li["list_y"] >= liste_kopf_unterkante,
          "Zeile %d, Text endet %d" % (Li["list_y"], liste_kopf_unterkante))

print()
print("Test 4: der Overscan-Rand bleibt unangetastet")
# Auf einem echten CRT wird der Bildrand abgeschnitten - genau dafuer
# gibt es OVERSCAN_X/Y. Beim Enger-Machen war die Versuchung gross,
# sich dort ein paar Pixel zu holen; das waere genau der falsche Ort.
for w, h in ((320, 240), (1920, 1080)):
    ist = kennzahlen(w, h)
    Li = ist["L_items"]
    s = Li["s"]
    check("%dx%d: Fusszeile haelt den vollen Sicherheitsrand ein"
          % (w, h), Li["footer_y"] == h - Li["oy"] - 13 * s,
          "footer_y %d" % Li["footer_y"])
    check("%dx%d: Fusszeilentext bleibt innerhalb des Rands" % (w, h),
          Li["footer_y"] + 8 * s <= h - Li["oy"] + 13 * s)
    check("%dx%d: linker Rand unveraendert bei %d %%"
          % (w, h, fm.OVERSCAN_X), Li["ox"] == w * fm.OVERSCAN_X // 100)

print()
print("Test 5: die Boxart-Spalte bleibt brauchbar breit")
# Der breitere Listenanteil auf CRT geht zu Lasten der Cover-Spalte.
# Das ist gewollt, darf aber nicht so weit gehen, dass das Cover
# unbrauchbar klein wird: die mitgelieferten CRT-Cover sind laut
# PC-Tools/art_convert.py (Profil "sd") bis zu 104 px breit.
for w, h in ((320, 240), (1920, 1080)):
    ist = kennzahlen(w, h)
    Li = ist["L_items"]
    s = Li["s"]
    luecke = (8 if h < fm.KOMPAKT_H else 20) * s
    art_x0 = Li["list_right"] + luecke
    art_w = (w - Li["ox"]) - art_x0
    nutzbar = art_w - 2 * (6 * s)          # pad in draw_art_panel()
    check("%dx%d: Cover-Spalte mindestens 90 px nutzbar" % (w, h),
          nutzbar >= 90, "jetzt %d px" % nutzbar)

print()
print("Test 6: ohne Boxart nutzt die Liste weiterhin die volle Breite")
for w, h in ((320, 240), (640, 480), (1920, 1080)):
    ist = kennzahlen(w, h)
    check("%dx%d: volle Breite = Bild minus beide Raender" % (w, h),
          ist["voll_breite"] == w - 2 * ist["L_items"]["ox"],
          "jetzt %d" % ist["voll_breite"])

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for f in fails:
        print("   ", f)
    sys.exit(1)
print("Alle Tests bestanden.")
