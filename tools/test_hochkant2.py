#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hochkant (TATE / 90 Grad) - zweiter Schritt (Build 176).

Der erste Schritt (Build 173, tools/test_hochkant.py) hat den
Vergroesserungsfaktor in Ordnung gebracht: hochkant zaehlt die
BREITE, nicht die Hoehe. Damit war das Frontend hochkant benutzbar.

Was danach offen blieb, stand so in der Doku zu Build 173: "Die
Spaltenaufteilung und die Boxart-Breite sind hochkant nicht
optimiert - sie funktionieren, aber das Verhaeltnis ist fuer 16:9
gedacht."

DREI ZAHLEN AUS DER MESSUNG, DIE DAS BELEGEN (vor Build 176):

  Kachelansicht     1080x1920   7x3 Kacheln zu 117x156 Punkten.
                    993 von 1497 Punkten Hoehe blieben LEER - zwei
                    Drittel der Flaeche, fuer die die Ansicht da ist.
                    Und die Kachel war so gross wie quer auf 720p.

  Galerie           Die Datenspalte rechts vom grossen Cover hatte
                    hochkant SIEBEN Zeichen (quer 52). Das grosse
                    Cover wurde aus der Hoehe gerechnet, und hochkant
                    ist die Hoehe riesig: 716 der 930 Punkte Breite
                    gingen an das Cover.

  Liste             Die Boxart-Karte war zu 68 % leer (quer 11 %),
                    weil sie sich die volle Hoehe nimmt, das Cover
                    darin aber 3:4 ist und damit an der BREITE haengt.
                    Danebe stand eine Liste mit 20 Zeichen je Zeile.

WAS DIESER TEST VOR ALLEM ABSICHERT, genau wie sein Vorgaenger:
dass QUER alles auf den Bildpunkt genau so bleibt, wie es war. Die
Zahlen dafuer stehen hier fest verdrahtet - sie stammen aus der
Messung VOR der Aenderung.

Ausfuehren:
    python3 tools/test_hochkant2.py
"""
import io
import os
import sys
import traceback

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
sys.path.insert(0, _HIER)

import _harness as H                                     # noqa: E402

fm = H.fm
import fe.settings as S                                  # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


QUER = ((1920, 1080), (1280, 720), (640, 480), (320, 240))
HOCH = ((1080, 1920), (720, 1280), (480, 640), (240, 320))
ALLE = QUER + HOCH


def frontend(b, h, page=1):
    H.SCREEN[:] = [b, h]
    return H.make_frontend(page=page)


# Ein Eintrag mit Titel, wie ihn die Liste bekommt.
ITEM = ("Super Mario World (USA)", "rom", "Super Mario World (USA)",
        "/x/smw.sfc")

# ---------------------------------------------------------------------------
print("Test 1: QUER BLEIBT BITGENAU - Rasteraufteilung")
# ---------------------------------------------------------------------------
# Gemessen VOR Build 176. Diese Zahlen duerfen sich nie aendern.
QUER_RASTER = {(1920, 1080): (7, 3, 176, 235),
               (1280, 720): (7, 3, 117, 156),
               (640, 480): (7, 3, 73, 97),
               (320, 240): (5, 3, 32, 43)}
for (b, h), (sp, ze, cb, ch) in QUER_RASTER.items():
    f = frontend(b, h)
    g = f.raster_geometrie(f.layout_items(True))
    check("%4dx%-5d %dx%d Kacheln zu %dx%d" % (b, h, sp, ze, cb, ch),
          (g["spalten"], g["zeilen"], g["cov_b"], g["cov_h"])
          == (sp, ze, cb, ch),
          "ist %dx%d zu %dx%d" % (g["spalten"], g["zeilen"],
                                  g["cov_b"], g["cov_h"]))

# ---------------------------------------------------------------------------
print()
print("Test 2: QUER BLEIBT BITGENAU - Spaltenteilung und Galerie")
# ---------------------------------------------------------------------------
QUER_LISTE = {(1920, 1080): 859, (1280, 720): 573,
              (640, 480): 287, (320, 240): 160}
for (b, h), lw in QUER_LISTE.items():
    f = frontend(b, h)
    L = f.layout_items(True)
    check("%4dx%-5d Listenspalte %d breit" % (b, h, lw),
          L["list_right"] - L["list_x"] == lw,
          "ist %d" % (L["list_right"] - L["list_x"]))

QUER_GAL = {(1920, 1080): (342, 518), (1280, 720): (228, 345),
            (640, 480): (168, 226), (320, 240): (72, 108)}
for (b, h), (gb, tx) in QUER_GAL.items():
    f = frontend(b, h)
    G = f.galerie_geometrie(f.layout_items(True))
    check("%4dx%-5d grosses Cover %d breit, Text ab %d" % (b, h, gb, tx),
          (G["gross_b"], G["text_x"]) == (gb, tx),
          "ist %d / %d" % (G["gross_b"], G["text_x"]))
    check("%4dx%-5d der Text steht weiterhin NEBEN dem Cover" % (b, h),
          G["text_y"] == G["oben"] and G["gross_x"] == G["ox"])

QUER_KARTE = {(1920, 1080): 909, (1280, 720): 606,
              (640, 480): 411, (320, 240): 195}
for (b, h), ah in QUER_KARTE.items():
    f = frontend(b, h)
    L = f.layout_items(True)
    s, ox, oy = L["s"], L["ox"], L["oy"]
    x0 = fm.art_spalte_x0(L["list_right"], h, s)
    w = (b - ox) - x0
    check("%4dx%-5d Boxart-Karte %d hoch" % (b, h, ah),
          fm.art_spalte_h(w, oy, L["footer_y"], s, b, h) == ah,
          "ist %d" % fm.art_spalte_h(w, oy, L["footer_y"], s, b, h))

# ---------------------------------------------------------------------------
print()
print("Test 3: das Raster fuellt hochkant den Schirm")
# ---------------------------------------------------------------------------
# DER Punkt dieses Builds. Vorher blieben bei 1080x1920 993 von 1497
# Punkten Hoehe leer.
for b, h in HOCH:
    f = frontend(b, h)
    g = f.raster_geometrie(f.layout_items(True))
    hoehe = g["unten"] - g["oben"]
    genutzt = g["zeilen"] * g["kachel_h"] + (g["zeilen"] - 1) * g["abstand"]
    frei = hoehe - genutzt
    check("%4dx%-5d hoechstens 15 %% Hoehe ungenutzt" % (b, h),
          frei * 100 <= hoehe * 15,
          "%d von %d frei (%.0f %%)" % (frei, hoehe, 100.0 * frei / hoehe))
    # Und die Kachel darf nicht kleiner sein als quer bei derselben
    # schmalen Seite - das war der zweite Teil des Fehlers.
    check("%4dx%-5d Kachel mindestens so gross wie quer" % (b, h),
          g["cov_h"] * 1080 >= 150 * b,
          "%dx%d bei schmaler Seite %d" % (g["cov_b"], g["cov_h"], b))

# Das Raster darf nie ueber den Platz hinauslaufen.
for b, h in ALLE:
    f = frontend(b, h)
    g = f.raster_geometrie(f.layout_items(True))
    br = g["spalten"] * g["kachel_b"] + (g["spalten"] - 1) * g["abstand"]
    ho = g["zeilen"] * g["kachel_h"] + (g["zeilen"] - 1) * g["abstand"]
    check("%4dx%-5d Raster passt in seinen Platz" % (b, h),
          br <= b - 2 * g["rand_ox"] and ho <= g["unten"] - g["oben"],
          "%dx%d in %dx%d" % (br, ho, b - 2 * g["rand_ox"],
                              g["unten"] - g["oben"]))
    check("%4dx%-5d mindestens 2x2 Kacheln" % (b, h),
          g["spalten"] >= 2 and g["zeilen"] >= 2,
          "%dx%d" % (g["spalten"], g["zeilen"]))

# ---------------------------------------------------------------------------
print()
print("Test 4: die Galerie hat hochkant wieder eine lesbare Datenspalte")
# ---------------------------------------------------------------------------
# Vorher: SIEBEN Zeichen bei 1080x1920.
for b, h in HOCH:
    f = frontend(b, h)
    G = f.galerie_geometrie(f.layout_items(True))
    s = G["s"]
    zeichen = G["text_b"] // (8 * s)
    check("%4dx%-5d mindestens 24 Zeichen fuer die Daten" % (b, h),
          zeichen >= 24, "%d" % zeichen)
    check("%4dx%-5d der Text steht UNTER dem Cover" % (b, h),
          G["text_y"] >= G["oben"] + G["gross_h"],
          "text_y=%d, Cover endet bei %d" % (G["text_y"],
                                             G["oben"] + G["gross_h"]))
    check("%4dx%-5d und faengt nicht schon in der Karte an" % (b, h),
          G["text_y"] - 2 * s >= G["oben"] + G["gross_h"]
          + (fm.ART_CARD_PAD + 3) * s,
          "Karte endet bei %d" % (G["oben"] + G["gross_h"]
                                  + (fm.ART_CARD_PAD + 3) * s))

# Und das Wichtigste: alles muss uebereinander passen.
for b, h in ALLE:
    f = frontend(b, h)
    G = f.galerie_geometrie(f.layout_items(True))
    s = G["s"]
    karte_unten = G["oben"] + G["gross_h"] + (fm.ART_CARD_PAD + 3) * s
    check("%4dx%-5d Cover stoesst nicht in die Leiste" % (b, h),
          karte_unten <= G["leiste_y"],
          "Karte bis %d, Leiste ab %d" % (karte_unten, G["leiste_y"]))
    check("%4dx%-5d der Text hat Platz vor der Leiste" % (b, h),
          G["leiste_y"] - 4 * s - G["text_y"] >= 30 * s,
          "%d Punkte" % (G["leiste_y"] - 4 * s - G["text_y"]))
    check("%4dx%-5d das grosse Cover passt in die Breite" % (b, h),
          G["gross_x"] >= G["ox"]
          and G["gross_x"] + G["gross_b"] <= b - G["ox"],
          "x=%d b=%d" % (G["gross_x"], G["gross_b"]))
    # Es heisst GROSSES Cover - es muss groesser sein als die
    # Miniaturen in der Leiste darunter, sonst hat die Ansicht keinen
    # Sinn. Genau das war bei 240x320 der erste Anlauf.
    check("%4dx%-5d das grosse Cover ist groesser als die Nachbarn"
          % (b, h), G["gross_b"] >= G["klein_b"] * 5 // 4,
          "gross %d, klein %d" % (G["gross_b"], G["klein_b"]))

# ---------------------------------------------------------------------------
print()
print("Test 5: die Liste bekommt hochkant mehr Breite")
# ---------------------------------------------------------------------------
# Vorher 52 % wie quer - das ergab 20 Zeichen je Zeile.
for b, h, mindestens in ((1080, 1920, 24), (720, 1280, 24),
                         (480, 640, 30), (240, 320, 15)):
    f = frontend(b, h)
    L = f.layout_items(True)
    z = (L["list_right"] - L["list_x"]) // (8 * L["s"])
    check("%4dx%-5d mindestens %d Zeichen je Zeile" % (b, h, mindestens),
          z >= mindestens, "%d" % z)

# Das Cover in der Boxart-Spalte soll ANTEILIG nicht groesser sein
# als quer - genau daran hing die zu schmale Liste.
for b, h in HOCH:
    f = frontend(b, h)
    L = f.layout_items(True)
    s, ox = L["s"], L["ox"]
    x0 = fm.art_spalte_x0(L["list_right"], h, s)
    w = (b - ox) - x0
    check("%4dx%-5d Cover hoechstens 30 %% der Schirmbreite" % (b, h),
          (w - 2 * fm.ART_CARD_PAD * s) * 100 <= b * 30,
          "%d von %d" % (w - 2 * fm.ART_CARD_PAD * s, b))
# ... aber auch nicht verschwindend klein.
for b, h in HOCH:
    f = frontend(b, h)
    L = f.layout_items(True)
    s, ox = L["s"], L["ox"]
    x0 = fm.art_spalte_x0(L["list_right"], h, s)
    check("%4dx%-5d und mindestens 20 %%" % (b, h),
          ((b - ox) - x0) * 100 >= b * 20,
          "%d von %d" % ((b - ox) - x0, b))

# ---------------------------------------------------------------------------
print()
print("Test 6: die Boxart-Karte ist hochkant nicht mehr halb leer")
# ---------------------------------------------------------------------------
# Vorher 68 % leer bei 1080x1920, quer sind es 11 bis 30 %.
for b, h in ALLE:
    f = frontend(b, h)
    L = f.layout_items(True)
    s, ox, oy = L["s"], L["ox"], L["oy"]
    x0 = fm.art_spalte_x0(L["list_right"], h, s)
    w = (b - ox) - x0
    ah = fm.art_spalte_h(w, oy, L["footer_y"], s, b, h)
    aw, cover_h, tl, il, _ra = f.cover_box_size(w, ah, "snes", ITEM, s)
    ist_b = min(aw, cover_h * 3 // 4)
    ist_h = ist_b * 4 // 3
    text_h = (len(tl) + len(il)) * 12 * s + (4 * s if il else 0)
    leer = ah - ist_h - text_h
    check("%4dx%-5d hoechstens 40 %% der Karte leer" % (b, h),
          leer * 100 <= ah * 40,
          "%d von %d (%.0f %%)" % (leer, ah, 100.0 * leer / ah))
    check("%4dx%-5d Cover und Text passen in die Karte" % (b, h),
          ist_h + text_h + 8 * s <= ah,
          "%d + %d + %d > %d" % (ist_h, text_h, 8 * s, ah))

# Hochkant haengt die Kastenhoehe NUR noch an der Breite - das ist der
# Grund, warum die Stufen aus Build 86 dort entfallen duerfen. Prueft
# sich am besten daran, dass zwei Eintraege mit verschieden langem
# Text denselben Kasten bekommen (sonst legt der Vorauslader
# Miniaturen an, die der Zeichenweg nie findet - Build 73/86).
KURZ = ("Pong", "rom", "Pong", "/x/pong.sfc")
for b, h in HOCH:
    f = frontend(b, h)
    L = f.layout_items(True)
    s, ox, oy = L["s"], L["ox"], L["oy"]
    x0 = fm.art_spalte_x0(L["list_right"], h, s)
    w = (b - ox) - x0
    ah = fm.art_spalte_h(w, oy, L["footer_y"], s, b, h)
    a1 = f.cover_box_size(w, ah, "snes", ITEM, s)[:2]
    a2 = f.cover_box_size(w, ah, "snes", KURZ, s)[:2]
    check("%4dx%-5d kurzer und langer Titel, derselbe Kasten" % (b, h),
          a1 == a2, "%s vs %s" % (a1, a2))

# ---------------------------------------------------------------------------
print()
print("Test 7: alle drei Ansichten zeichnen weiterhin - hochkant UND quer")
# ---------------------------------------------------------------------------
# Gezeichnet wird in einen Puffer fester Groesse: schreibt etwas
# darueber hinaus, fliegt hier eine Ausnahme statt auf dem Geraet ein
# zerrissenes Bild. Quer ist bewusst mit dabei - die Aenderungen
# stecken in Funktionen, die beide Lagen benutzen.
for b, h in ALLE:
    for ansicht in S.ANSICHTEN:
        try:
            f = frontend(b, h)
            f.ansicht_setzen(ansicht)
            f.draw()
            gefaerbt = any(f.fb.buf[i] for i in range(0, f.fb.size, 997))
            ok, fehler = True, ""
        except Exception as e:                           # noqa: BLE001
            ok, gefaerbt, fehler = False, False, "%s: %s" % (
                type(e).__name__, e)
            traceback.print_exc(limit=3)
        check("%4dx%-5d %-8s zeichnet" % (b, h, ansicht), ok, fehler)
        check("%4dx%-5d %-8s faerbt den Schirm" % (b, h, ansicht),
              gefaerbt)
    for ansicht in S.ANSICHTEN:
        try:
            f = frontend(b, h, page=0)
            f.ansicht_haupt_setzen(ansicht)
            f.draw()
            ok, fehler = True, ""
        except Exception as e:                           # noqa: BLE001
            ok, fehler = False, "%s: %s" % (type(e).__name__, e)
            traceback.print_exc(limit=3)
        check("%4dx%-5d Hauptseite %-8s zeichnet" % (b, h, ansicht), ok,
              fehler)

# ---------------------------------------------------------------------------
print()
print("Test 8: die Rechnungen stehen an EINER Stelle")
# ---------------------------------------------------------------------------
# Dieselbe Regel wie bei _skala() in Build 173: eine Zahl, die an
# mehreren Stellen steht, laeuft irgendwann auseinander.
quelle = io.open(os.path.join(_REPO, "frontend", "frontend.py"),
                 encoding="utf-8").read()
check("die feste Rasteraufteilung steht nur noch in _raster_aufteilung",
      quelle.count("self.RASTER_CRT if") == 1,
      "%d Stellen" % quelle.count("self.RASTER_CRT if"))
check("es gibt genau eine Definition von _raster_aufteilung",
      quelle.count("def _raster_aufteilung(") == 1)
check("und beide Kachelrechnungen rufen sie",
      quelle.count("self._raster_aufteilung(") == 2,
      "%d Aufrufe" % quelle.count("self._raster_aufteilung("))
check("die Kartenhoehe wird nirgends mehr von Hand gerechnet",
      "art_h = footer_y - 8 * s - art_y0" not in quelle
      and 'art_h = L["footer_y"] - 8 * s - oy' not in quelle)
check("es gibt genau eine Definition von art_spalte_h",
      quelle.count("def art_spalte_h(") == 1)
check("und vier Aufrufe (die vier Zeichen- und Vorbereitungswege)",
      quelle.count("art_spalte_h(") == 5,
      "%d" % (quelle.count("art_spalte_h(") - 1))
check("die Galerie liest Text und Cover aus der Geometrie",
      quelle.count('geo["text_y"]') == 2
      and quelle.count('geo["gross_x"]') == 2,
      "text_y %d, gross_x %d" % (quelle.count('geo["text_y"]'),
                                 quelle.count('geo["gross_x"]')))

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
