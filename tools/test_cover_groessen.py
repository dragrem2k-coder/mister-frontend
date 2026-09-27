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

Galerie und Raster liegen ebenfalls nah beieinander. Ob eine
hochskalierte Kachel dort gut genug aussieht, kann nur das Auge am
Fernseher entscheiden - deshalb ein SCHALTER
(galerie_kachelquelle()), Standard aus.

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
print("Test 4: der Schalter ist aus, solange die Flagdatei fehlt")
# ---------------------------------------------------------------------------
from fe import settings as S                              # noqa: E402

check("Flagdatei-Pfad liegt unter /media/fat/frontend",
      S.GALERIE_KACHELQUELLE_FLAG
      == "/media/fat/frontend/galerie_kachelquelle",
      S.GALERIE_KACHELQUELLE_FLAG)

L = fe.layout_items(True)
H._zwischenspeicher_leeren()
check("ohne Datei liefert galerie_quellkasten() None",
      fe.galerie_quellkasten(L) is None)

# ---------------------------------------------------------------------------
print()
print("Test 5: eingeschaltet nehmen Zeichenweg UND Vorauslader die Kachel")
# ---------------------------------------------------------------------------
_echt_flag = S.galerie_kachelquelle
try:
    S.galerie_kachelquelle = lambda: True
    kk = fe.galerie_quellkasten(L)
    raster = fe.raster_geometrie(L)
    check("der Quellkasten ist der Raster-Kasten, unveraendert",
          kk is not None and tuple(kk) == (raster["cov_b"], raster["cov_h"]),
          "%r gegen %r" % (kk, (raster["cov_b"], raster["cov_h"])))

    gal = fe.galerie_geometrie(L)
    check("und er ist KLEINER als der Galerie-Kasten - sonst waere hier "
          "nichts zu gewinnen",
          kk[0] < gal["gross_b"] and kk[1] < gal["gross_h"],
          "%r gegen %dx%d" % (kk, gal["gross_b"], gal["gross_h"]))
    print("    Kachel %dx%d, Galerie %dx%d, Faktor %.2f"
          % (kk[0], kk[1], gal["gross_b"], gal["gross_h"],
             gal["gross_b"] / float(kk[0])))

    fe.ansicht = "galerie"
    vorbereitet = fe._art_panel_geometrie("galerie", erzwingen=True)
    check("der Vorauslader bereitet GENAU diesen Kasten vor",
          vorbereitet is not None and len(vorbereitet) == 4
          and vorbereitet[0] == "fest"
          and (vorbereitet[1], vorbereitet[2]) == tuple(kk),
          repr(vorbereitet))
finally:
    S.galerie_kachelquelle = _echt_flag

# Und ausgeschaltet bereitet er wieder den Galerie-Kasten vor.
H._zwischenspeicher_leeren()
vorbereitet = fe._art_panel_geometrie("galerie", erzwingen=True)
gal = fe.galerie_geometrie(L)
check("ausgeschaltet wieder der Galerie-Kasten",
      vorbereitet is not None and len(vorbereitet) == 4
      and (vorbereitet[1], vorbereitet[2])
      == (gal["gross_b"], gal["gross_h"]),
      repr(vorbereitet))

# ---------------------------------------------------------------------------
print()
print("Test 6: get_scaled_aus_kachel() vergroessert und merkt sich das")
# ---------------------------------------------------------------------------
from fe import art as A                                   # noqa: E402

ART = A.ART
ruf = [0]
_echt_gs = ART.get_scaled


def _zaehl_gs(path, w, h, auslagern_ok=False):
    ruf[0] += 1
    # Ein kuenstliches, quadratisches Bild in der Kachelgroesse.
    return (w, h, bytes(bytearray(w * h * 4)))


try:
    ART.get_scaled = _zaehl_gs
    ART.scaled = {}
    ART.scaled_order = []
    erg = ART.get_scaled_aus_kachel("/x/y.art", 176, 235, 342, 456)
    check("liefert ein Bild", erg is not None)
    bw, bh = erg[0], erg[1]
    check("es ist groesser als die Kachel", bw > 176 and bh > 235,
          "%dx%d" % (bw, bh))
    check("und passt in den Galerie-Kasten", bw <= 342 and bh <= 456,
          "%dx%d" % (bw, bh))
    check("das Seitenverhaeltnis bleibt",
          abs(bw / float(bh) - 176 / 235.0) < 0.01,
          "%.4f gegen %.4f" % (bw / float(bh), 176 / 235.0))
    check("die Datenmenge passt zur Groesse", len(erg[2]) == bw * bh * 4)
    print("    176x235 -> %dx%d" % (bw, bh))

    vorher = ruf[0]
    erg2 = ART.get_scaled_aus_kachel("/x/y.art", 176, 235, 342, 456)
    check("der zweite Aufruf rechnet nicht neu", ruf[0] == vorher)
    check("und liefert dasselbe Bild", erg2 is erg)

    # Angefragt wird GENAU der Kachel-Kasten - nicht etwa der Ziel-
    # kasten. Sonst waere es eine dritte Groesse auf der Karte.
    gefragt = []
    ART.get_scaled = lambda p, w, h, auslagern_ok=False: (
        gefragt.append((w, h)) or (w, h, bytes(bytearray(w * h * 4))))
    ART.scaled = {}
    ART.scaled_order = []
    ART.get_scaled_aus_kachel("/x/z.art", 176, 235, 342, 456)
    check("geholt wird unter dem KACHEL-Kasten", gefragt == [(176, 235)],
          repr(gefragt))

    # Nichts zu vergroessern: dann das Original, nicht ein Zerrbild.
    ART.scaled = {}
    ART.scaled_order = []
    erg3 = ART.get_scaled_aus_kachel("/x/w.art", 400, 500, 342, 456)
    check("ist die Kachel schon gross genug, bleibt sie unangetastet",
          erg3 is not None and (erg3[0], erg3[1]) == (400, 500),
          repr(erg3[:2] if erg3 else None))

    # Kein Bild da (Vorauslader hat verzoegert): nichts merken.
    ART.get_scaled = lambda p, w, h, auslagern_ok=False: None
    ART.scaled = {}
    ART.scaled_order = []
    check("ohne Bild kommt None zurueck",
          ART.get_scaled_aus_kachel("/x/v.art", 176, 235, 342, 456) is None)
    check("und nichts wird gemerkt", not ART.scaled)
finally:
    ART.get_scaled = _echt_gs
    ART.scaled = {}
    ART.scaled_order = []

# ---------------------------------------------------------------------------
print()
print("Test 7: auf die Karte wird dabei NICHTS geschrieben")
# ---------------------------------------------------------------------------
q = inspect.getsource(A.ArtCache.get_scaled_aus_kachel)
check("kein _thumb_cache_put in get_scaled_aus_kachel",
      "_thumb_cache_put" not in q)
check("der Grund steht dabei",
      "abgeleitet" in q and "billig" in q)

# ---------------------------------------------------------------------------
print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
