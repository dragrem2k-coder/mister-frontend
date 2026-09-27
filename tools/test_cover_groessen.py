#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Attract-Kasten und Galerie-Quelle (Build 207).

WORUM ES GEHT

Der Schluessel des Miniaturen-Caches enthaelt die KASTENGROESSE (siehe
_thumb_cache_key() in fe/art.py). Jede zusaetzliche Kastengroesse im
Programm ist deshalb eine zusaetzliche Datei je Spiel auf der Karte -
bei 30.270 Spielen keine Kleinigkeit. Gezaehlt wurden bei 1080p:

    Spieleliste, Cover-Spalte    697x771   (je Eintrag, haengt am Text)
    Hauptseite, Abzeichen        340x792
    Galerie gross                342x456
    Raster-Kachel                176x235
    Attract-Modus                960x777   <- nur er allein

Der Attract-Modus hatte damit fuer JEDES gezeigte Spiel eine eigene,
sonst von niemandem gebrauchte Miniatur. Er nimmt ab Build 207 den
Kasten der Cover-Spalte - fast dieselbe Hoehe (771 gegen 777, und die
begrenzt bei hochkantigen Covern ohnehin), also sichtbar kaum eine
Aenderung, aber kein eigener Eintrag mehr.

Galerie und Raster lagen ebenfalls nah beieinander, und Build 207 hat
probeweise die Galerie auf die hochskalierte Rasterkachel gestellt. Das
Urteil des Nutzers am Fernseher: "galerie sieht bloed aus lassen wir" -
der Schalter ist in Build 210 samt Hochskalierer wieder entfernt. Was
davon bleibt, ist der umgekehrte Weg: das RASTER kann jetzt grosse
Kacheln zeigen (raster_gross(), Standard aus), und DAS wollte er.

WAS DIESER TEST ABSICHERT

  - dass der Attract-Kasten BITGENAU der der Spieleliste ist, nicht
    "so aehnlich". Waere er nur aehnlich, waere er eine dritte Groesse
    und der Gewinn ins Gegenteil verkehrt.
  - dass der Rueckfall auf den alten Kasten greift, wenn die Geometrie
    nicht zu haben ist - ein Bildschirmschoner ohne Cover waere ein
    schlechter Tausch gegen eine gesparte Datei.
  - dass bei AUSGESCHALTETEM Schalter der Zeichenweg der Galerie
    Schritt fuer Schritt der von Build 206 ist.
  - dass bei EINGESCHALTETEM Schalter Zeichenweg UND Vorauslader
    denselben Kasten benutzen. Das ist die Falle aus Build 73: legt der
    Vorauslader unter einer Groesse ab, die der Zeichenweg nie
    abfragt, bereitet er ins Leere vor, und niemand sieht warum.
  - dass das Hochskalieren wirklich vergroessert und gemerkt wird.
"""
import os
import sys

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
sys.path.insert(0, _HIER)
import _harness as H                                     # noqa: E402

fm = H.fm
NOW = H.NOW

fails = []


def check(name, ok, extra=""):
    print("  %s %s%s" % ("OK  " if ok else "FEHL", name,
                         ("  (%s)" % extra) if extra and not ok else ""))
    if not ok:
        fails.append(name + ((" - " + extra) if extra else ""))


# ---------------------------------------------------------------------------
print("Test 1: der Attract-Kasten ist der der Spieleliste")
# ---------------------------------------------------------------------------
H.set_screen(1920, 1080)
fe = H.make_frontend(page=1)
items = fe._display_items()
name = items[0][0]
syskey = fe._item_syskey(items[0], fe.cats[fe.cat_i][2])

geo = fe._art_panel_geometrie("liste", erzwingen=True)
check("die Listen-Geometrie ist die Drei-Form", geo is not None
      and len(geo) == 3, repr(geo))
art_w, art_h, s = geo
soll = fe.cover_box_size(art_w, art_h, syskey, items[0], s)[:2]
ist = fe.attract_cover_kasten(name, syskey)
check("Attract-Kasten == Kasten der Cover-Spalte", tuple(ist) == tuple(soll),
      "Attract %r, Liste %r" % (ist, soll))

alt = (int(1920 * 0.5), int(1080 * 0.72))
check("und NICHT mehr der eigene Kasten von Build 206",
      tuple(ist) != alt, "beide %r" % (alt,))
print("    Liste %dx%d, alter Attract-Kasten %dx%d"
      % (soll[0], soll[1], alt[0], alt[1]))

# ---------------------------------------------------------------------------
print()
print("Test 2: die Attrappe liest nur, was ein Spiel-Eintrag hergibt")
# ---------------------------------------------------------------------------
# Das ist die Stelle, an der die Gleichheit aus Test 1 stehen oder
# fallen wuerde: cover_box_size() und _spiel_infozeilen() duerfen aus
# dem Eintrag NUR item[0], item[1] und item[2] lesen. Griffen sie auf
# item[3] zu, waere die Attrappe (Name, "game", Name) nicht dasselbe
# wie der echte Eintrag - und der Kasten waere still ein anderer.
import inspect                                           # noqa: E402

for fn_name in ("cover_box_size", "_spiel_infozeilen"):
    q = inspect.getsource(getattr(fm.Frontend, fn_name))
    hoch = [z for z in ("item[3]", "item[4]", "item[5]") if z in q]
    check("%s liest kein item[3+]" % fn_name, not hoch, ", ".join(hoch))

# Und derselbe Kasten muss herauskommen, wenn man ihn mit der Attrappe
# statt mit dem echten Eintrag rechnet - gepruefte Gleichheit, nicht
# nur die Abwesenheit von Zugriffen.
attrappe = (name, "game", name)
mit_attrappe = fe.cover_box_size(art_w, art_h, syskey, attrappe, s)[:2]
check("Attrappe und echter Eintrag ergeben denselben Kasten",
      tuple(mit_attrappe) == tuple(soll),
      "%r gegen %r" % (mit_attrappe, soll))

# ---------------------------------------------------------------------------
print()
print("Test 3: Rueckfall auf den Kasten von Build 206")
# ---------------------------------------------------------------------------
_echt = fm.Frontend._art_panel_geometrie
try:
    fm.Frontend._art_panel_geometrie = lambda self, a=None, erzwingen=False: None
    check("keine Geometrie -> alter Kasten",
          tuple(fe.attract_cover_kasten(name, syskey)) == alt,
          repr(fe.attract_cover_kasten(name, syskey)))

    def _wirft(self, a=None, erzwingen=False):
        raise RuntimeError("kaputt")
    fm.Frontend._art_panel_geometrie = _wirft
    check("Ausnahme -> alter Kasten",
          tuple(fe.attract_cover_kasten(name, syskey)) == alt)
finally:
    fm.Frontend._art_panel_geometrie = _echt

check("der Anteil von Build 206 steht als Vorgabe im Quelltext",
      fm.Frontend.ATTRACT_KASTEN_ANTEIL == (0.5, 0.72),
      repr(fm.Frontend.ATTRACT_KASTEN_ANTEIL))

# ---------------------------------------------------------------------------
print()
print("Test 4: grosse Rasterkacheln - der Schalter ist aus ohne Flagdatei")
# ---------------------------------------------------------------------------
from fe import settings as S                              # noqa: E402

check("Flagdatei-Pfad liegt unter /media/fat/frontend",
      S.RASTER_GROSS_FLAG == "/media/fat/frontend/raster_gross",
      S.RASTER_GROSS_FLAG)
H._zwischenspeicher_leeren()
check("ohne Datei ist der Grossmodus aus", not fe._raster_gross_an())

_echt_flag = S.raster_gross


def mit_schalter(an):
    """Frontend mit gesetztem/geloeschtem Schalter, frisch gerechnet."""
    S.raster_gross = (lambda: an)
    H._zwischenspeicher_leeren()
    f = H.make_frontend(page=1)
    L = f.layout_items(True)
    return f, L


# ---------------------------------------------------------------------------
print()
print("Test 5: die Kacheln werden groesser, und zwar in JEDER Aufloesung")
# ---------------------------------------------------------------------------
try:
    for w, h, name in ((1920, 1080, "HDMI 1080p"), (1280, 720, "720p"),
                       (320, 240, "CRT"), (1080, 1920, "Hochkant")):
        H.set_screen(w, h)
        f0, L0 = mit_schalter(False)
        g0 = f0.raster_geometrie(L0)
        f1, L1 = mit_schalter(True)
        g1 = f1.raster_geometrie(L1)
        gal = f1.galerie_geometrie(L1)
        anteil = 100 * g1["cov_h"] // max(1, gal["gross_h"])
        print("    %-11s klein %dx%d=%2d a %3dx%3d  ->  gross %dx%d=%2d "
              "a %3dx%3d  (%d%% der Galerie)"
              % (name, g0["spalten"], g0["zeilen"],
                 g0["spalten"] * g0["zeilen"], g0["cov_b"], g0["cov_h"],
                 g1["spalten"], g1["zeilen"],
                 g1["spalten"] * g1["zeilen"], g1["cov_b"], g1["cov_h"],
                 anteil))
        check("%s: Kachel wird groesser" % name,
              g1["cov_h"] > g0["cov_h"],
              "%d gegen %d" % (g1["cov_h"], g0["cov_h"]))
        check("%s: und es sind weniger" % name,
              g1["spalten"] * g1["zeilen"] < g0["spalten"] * g0["zeilen"])
        # Der Deckel aus Build 176 in neuem Anzug: hochkant lieferte
        # ohne ihn 1x2 - zwei Kacheln auf einem 1080 breiten Schirm.
        check("%s: mindestens %d Spalten" % (name,
                                             fm.Frontend.RASTER_GROSS_SPALTEN),
              g1["spalten"] >= fm.Frontend.RASTER_GROSS_SPALTEN,
              str(g1["spalten"]))
        check("%s: die Kachel passt noch ins Bild" % name,
              g1["cov_b"] * g1["spalten"] <= w
              and g1["cov_h"] <= gal["gross_h"],
              "%dx%d" % (g1["cov_b"], g1["cov_h"]))

    # ---------------------------------------------------------------------
    print()
    print("Test 6: die GALERIE bleibt unberuehrt - in jeder Aufloesung")
    # ---------------------------------------------------------------------
    # Das ist der Punkt, an dem der Bau beim ersten Anlauf falsch war:
    # kachel_cover_kasten() nimmt seit Build 128 den kleineren von Raster
    # und Galerie-Nachbarleiste, und dadurch hat der Raster-Schalter die
    # LEISTE mitverschoben (bei 1080p 176x235 -> 193x258). Eine
    # zusaetzliche Miniatur je Spiel fuer eine Ansicht, an der sich
    # nichts aendern sollte. Deshalb hier fuer jede Aufloesung geprueft.
    for w, h, name in ((1920, 1080, "HDMI 1080p"), (1280, 720, "720p"),
                       (320, 240, "CRT"), (1080, 1920, "Hochkant")):
        H.set_screen(w, h)
        f0, L0 = mit_schalter(False)
        leiste0 = f0.kachel_cover_kasten(L0)
        gal0 = f0.galerie_geometrie(L0)
        f1, L1 = mit_schalter(True)
        leiste1 = f1.kachel_cover_kasten(L1)
        gal1 = f1.galerie_geometrie(L1)
        check("%s: Nachbarleiste unveraendert" % name,
              tuple(leiste0) == tuple(leiste1),
              "%r -> %r" % (leiste0, leiste1))
        check("%s: grosses Galeriebild unveraendert" % name,
              (gal0["gross_b"], gal0["gross_h"])
              == (gal1["gross_b"], gal1["gross_h"]),
              "%r -> %r" % ((gal0["gross_b"], gal0["gross_h"]),
                            (gal1["gross_b"], gal1["gross_h"])))

    # ---------------------------------------------------------------------
    print()
    print("Test 7: Zeichenweg und Vorauslader nehmen denselben Kasten")
    # ---------------------------------------------------------------------
    # Die Falle aus Build 73: legt der Vorauslader unter einer Groesse
    # ab, die der Zeichenweg nie abfragt, bereitet er ins Leere vor.
    H.set_screen(1920, 1080)
    f1, L1 = mit_schalter(True)
    g1 = f1.raster_geometrie(L1)
    f1.ansicht = "raster"
    vor = f1._art_panel_geometrie("raster", erzwingen=True)
    check("der Vorauslader bereitet GENAU den Kachelkasten vor",
          vor is not None and len(vor) == 4 and vor[0] == "fest"
          and (vor[1], vor[2]) == (g1["cov_b"], g1["cov_h"]),
          "%r gegen %r" % (vor, (g1["cov_b"], g1["cov_h"])))

    # Und die Ansicht laesst sich wirklich zeichnen.
    f1.draw()
    check("die Rasteransicht zeichnet mit grossen Kacheln", True)
finally:
    S.raster_gross = _echt_flag
    H.set_screen(1920, 1080)
    H._zwischenspeicher_leeren()

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
