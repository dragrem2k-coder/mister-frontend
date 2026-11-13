#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Vorbereitet wird, was gezeichnet wird - in JEDER Ansicht (Build 319).

DER BEFUND, und er ist dreimal derselbe:

  * Der COVERFLOW (Build 313) fragt jedes Cover in DREI Groessen an -
    Mitte, naher Nachbar, ferner Nachbar. Keine davon stand je in
    einer Vorbereitungsliste: _art_panel_geometrie() kannte die
    Ansicht nicht und gab ihr den Kasten der LISTE. Vorbereitet wurden
    also Miniaturen in einer Groesse, nach der dort nie jemand fragt.
  * KACHELWAND, DASHBOARD und KARUSSELL (Build 314) kamen im
    Vorauslader der Hauptseite gar nicht vor. Dessen Schleife lief
    ueber ANSICHTEN - die Liste der Spieleliste.
  * Die LEISTE der Galerie auf der Hauptseite steht seit Build 124 in
    keiner Liste. Genau den Fehler hat Build 125 in der Spieleliste
    behoben ("die Boxarts sind trotz Miniaturen vorbereiten nicht
    sofort sichtbar, das stoert") - auf der Hauptseite blieb er.

Jedes Mal dieselbe Form: der Zeichenweg bekommt eine neue Groesse, und
der Vorauslader erfaehrt nichts davon. Ein kaltes Bild kostet auf dem
Geraet 11,2 ms Lesen und 1,3 ms Entpacken (gemessen in Build 74, steht
in fe/art.py), im Karussell bis zu dreimal je Schritt.

WARUM DIESER TEST DAS GEFUNDEN HAETTE, UND DIE VORHANDENEN NICHT. Die
bisherigen Tests pruefen, dass der Vorauslader tut, was er soll - mit
den Kaesten, die er kennt. Dieser hier fragt von der ANDEREN Seite:
er zeichnet jede Ansicht mit dem Zeiger auf jedem Eintrag, schreibt
mit, was der Bildspeicher gefragt wird, und haelt das gegen die
Vorbereitungsliste. Wer eine neue Groesse einbaut und den Vorauslader
vergisst, macht diesen Test rot, ohne dass ihn jemand anpassen muss.

WAS DIESER TEST SICHERT:
  1. Hauptseite, alle sechs Ansichten: jede Anfrage des Zeichenwegs
     steht in kategorie_logo_alle() - und dort steht nichts, wonach
     nie gefragt wird,
  2. Spieleliste, alle vier Ansichten: dasselbe gegen
     _ansicht_geometrien(),
  3. der Pfad kommt aus EINER Regel (Foto oder Abzeichen),
  4. beim Start und in der Ruhepause werden die drei klassischen
     Ansichten vorbereitet UND die, in der man steht - nicht mehr,
  5. der Menuepunkt nimmt den Coverflow nur mit, wenn er die Vorgabe
     ist (sieben Miniaturen je Cover sprengen sonst den
     Zwischenspeicher),
  6. auf der Roehre gibt es keine Kaesten fuer HD-Ansichten.

Ausfuehren:
    python3 tools/test_vorwaermen_alle_ansichten.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H          # noqa: E402

import fe.art as A            # noqa: E402
import fe.settings as S       # noqa: E402
from _quelle import koerper, nur_code                     # noqa: E402

fm = H.fm

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYSART = os.path.join(_REPO, "frontend", "sysart")
FOTOS = os.path.join(_REPO, "frontend", "sysart_foto")
A.SYSART_BASE = fm.SYSART_BASE = SYSART
A.SYSART_FOTO_BASE = fm.SYSART_FOTO_BASE = FOTOS

_QF = open(os.path.join(_REPO, "frontend", "frontend.py"),
           encoding="utf-8", errors="replace").read()

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


print(__doc__.strip().split("\n")[0])
print()

TMP = tempfile.mkdtemp(prefix="vorwaermen_")
S.ANSICHT_HAUPT_FILE = os.path.join(TMP, "ansicht_haupt.txt")
S.HAUPT_STIL_FILE = os.path.join(TMP, "haupt_stil.txt")
S.ANSICHT_FILE = os.path.join(TMP, "ansicht")
S.GALERIE_STIL_FILE = os.path.join(TMP, "galerie_stil.txt")
H._zwischenspeicher_leeren()

# Kategorien MIT Foto und OHNE - der Fall, der auf dem Geraet eintritt
# (20 Fotos, 60 Abzeichen). Nur mit Fotos haette der Test die Regel
# "sonst das Abzeichen" nie angefasst.
MIT_FOTO = ["NES", "SNES", "GAMEBOY", "GBC", "GBA", "N64", "Genesis",
            "SMS", "MegaCD", "PSX", "Saturn", "TGFX16", "NEOGEO",
            "ATARI2600", "ARCADE", "SUPERGAMEBOY", "PHYSICAL_DISC_CORES",
            "S32X", "VIRTUALBOY", "COMPUTER"]
OHNE_FOTO = ["FAVORITES", "CONTINUE", "RECENT", "COLLECTIONS",
             "GAMEGEAR", "ATARILYNX", "COLECOVISION", "SYSTEM"]
KEYS = OHNE_FOTO[:4] + MIT_FOTO + OHNE_FOTO[4:]


def mitschreiben():
    """get_scaled() abhoeren. Rueckgabe (menge, zuruecksetzen)."""
    gefragt = set()
    echt = A.ART.get_scaled

    def _hoeren(pfad, breite, hoehe, **k):
        if pfad:
            gefragt.add((pfad, int(breite), int(hoehe)))
        return None

    A.ART.get_scaled = _hoeren

    def zurueck():
        A.ART.get_scaled = echt

    return gefragt, zurueck


def haupt(w, h, ansicht):
    S.ansicht_haupt_schreiben(ansicht)
    H._zwischenspeicher_leeren()
    H.set_screen(w, h)
    f = H.make_frontend(page=0)
    f._ansicht_haupt = None
    f._last_input_time = 0
    f.cats = [(k, {"items": [], "folders": {}}, k) for k in KEYS]
    f.cat_i = 0
    f.cat_scroll = 0
    return f


def liste(w, h, ansicht, n=40):
    S.ansicht_schreiben(ansicht)
    H._zwischenspeicher_leeren()
    H.set_screen(w, h)
    f = H.make_frontend(page=1)
    f._ansicht_je_kat = {}
    f._last_input_time = 0
    f.cat_i = 0
    f.nav_path = []
    _n, node, _sk = f.cats[0]
    # Verschieden lange Titel: in der Listenansicht haengt die Hoehe
    # des Cover-Kastens am Text (cover_box_size).
    node["items"] = [
        (("Spiel %03d" % i) if i % 3 else
         ("Ein deutlich laengerer Spieltitel Nummer %03d (USA)" % i),
         "game", ("/f/%d.sfc" % i, ".sfc", "SNES", None, None))
        for i in range(n)]
    node.pop("_display_items_cache", None)
    f.item_i = 0
    f.scroll = 0
    return f


# ---------------------------------------------------------------------------
print("Test 1: Hauptseite - gezeichnet gegen vorbereitet")
# ---------------------------------------------------------------------------
for (w, h) in ((1920, 1080), (1280, 720)):
    for ansicht in S.ANSICHTEN_HAUPT:
        f = haupt(w, h, ansicht)
        check("%4dx%-4d %-10s ist die gezeichnete Ansicht"
              % (w, h, ansicht), f.aktuelle_ansicht_haupt() == ansicht)
        vorbereitet = set(f.kategorie_logo_alle())
        gefragt, zurueck = mitschreiben()
        try:
            for i in range(len(f.cats)):
                f.cat_i = i
                f._force_full_redraw = True
                f.fb.mark_full_redraw()
                f.draw_page_cats(flip=False)
        finally:
            zurueck()
        fehlt = gefragt - vorbereitet
        zuviel = vorbereitet - gefragt
        check("%4dx%-4d %-10s jede Anfrage ist vorbereitet (%d)"
              % (w, h, ansicht, len(gefragt)),
              bool(gefragt) and not fehlt,
              "" if not fehlt else "%d fehlen, z.B. %s"
              % (len(fehlt), sorted(fehlt)[:2]))
        check("%4dx%-4d %-10s und nichts wird vorbereitet, wonach "
              "niemand fragt" % (w, h, ansicht), not zuviel,
              "" if not zuviel else "%d zuviel, z.B. %s"
              % (len(zuviel), sorted(zuviel)[:2]))

f = haupt(1920, 1080, "karussell")
kaesten = f._kat_logo_kaesten("karussell")
check("das Karussell hat DREI Kaesten", len(kaesten) == 3,
      "%r" % (kaesten,))
check("die Mitte steht vorn", kaesten[0][0] == max(k[0] for k in kaesten))
check("die Galerie hat ZWEI - das grosse Bild und die Leiste",
      len(f._kat_logo_kaesten("galerie")) == 2,
      "die Leiste fehlte seit Build 124")
check("Kachelwand und Dashboard je einen, mit Foto",
      [k[2] for k in f._kat_logo_kaesten("kachelwand")] == [True]
      and [k[2] for k in f._kat_logo_kaesten("dashboard")] == [True])
check("Liste und Raster je einen, mit Abzeichen",
      [k[2] for k in f._kat_logo_kaesten("liste")] == [False]
      and [k[2] for k in f._kat_logo_kaesten("raster")] == [False])

# ---------------------------------------------------------------------------
print()
print("Test 2: Spieleliste - gezeichnet gegen vorbereitet")
# ---------------------------------------------------------------------------
for (w, h) in ((1920, 1080), (1280, 720)):
    for ansicht in S.ANSICHTEN:
        f = liste(w, h, ansicht)
        check("%4dx%-4d %-10s ist die gezeichnete Ansicht"
              % (w, h, ansicht), f.aktuelle_ansicht() == ansicht)
        items = f._display_items()
        _n, _r, syskey = f.cats[f.cat_i]
        geos = f._ansicht_geometrien(ansicht)
        vorbereitet = set()
        for g in geos:
            for it in items:
                e = f.cover_pfad_und_kasten(it, syskey, g)
                if e:
                    vorbereitet.add((e[0], int(e[1]), int(e[2])))
        gefragt, zurueck = mitschreiben()
        try:
            for i in range(len(items)):
                f.item_i = i
                f._force_full_redraw = True
                f.fb.mark_full_redraw()
                f.draw()
        finally:
            zurueck()
        fehlt = gefragt - vorbereitet
        zuviel = vorbereitet - gefragt
        check("%4dx%-4d %-10s jede Anfrage ist vorbereitet (%d)"
              % (w, h, ansicht, len(gefragt)),
              len(gefragt) >= len(items) and not fehlt,
              "" if not fehlt else "%d fehlen, z.B. %s"
              % (len(fehlt), sorted(fehlt)[:2]))
        check("%4dx%-4d %-10s und nichts wird vorbereitet, wonach "
              "niemand fragt" % (w, h, ansicht), not zuviel,
              "" if not zuviel else "%d zuviel, z.B. %s"
              % (len(zuviel), sorted(zuviel)[:2]))

f = liste(1920, 1080, "coverflow")
geos = f._ansicht_geometrien("coverflow")
check("der Coverflow hat DREI Groessen", len(geos) == 3, "%r" % (geos,))
check("alle drei sind feste Kaesten",
      all(len(g) == 4 and g[0] == "fest" for g in geos))
check("die Mitte steht vorn", geos[0][1] == max(g[1] for g in geos),
      "der Vorauslader nimmt die erste als Hauptgroesse")
check("und keine ist der Kasten der LISTE",
      f._art_panel_geometrie("liste") not in geos,
      "genau den hat der Coverflow bis Build 318 bekommen")
check("die Galerie behaelt ihre zwei",
      len(liste(1920, 1080, "galerie")._ansicht_geometrien("galerie")) == 2)

# ---------------------------------------------------------------------------
print()
print("Test 3: der Pfad kommt aus EINER Regel")
# ---------------------------------------------------------------------------
f = haupt(1920, 1080, "kachelwand")
check("mit Foto und foto=True: aus dem Fotosatz",
      f._kat_logo_pfad("SNES", "SNES", True)
      == os.path.join(FOTOS, "SNES.art"))
check("mit Foto und foto=False: das Abzeichen",
      f._kat_logo_pfad("SNES", "SNES", False)
      == os.path.join(SYSART, "SNES.art"))
check("ohne Foto: immer das Abzeichen",
      f._kat_logo_pfad("GAMEGEAR", "GAMEGEAR", True)
      == os.path.join(SYSART, "GAMEGEAR.art"))
_logo = nur_code(koerper(_QF, "_kat_logo", "Frontend"))
check("_kat_logo() fragt _kat_logo_pfad() und baut nicht selbst",
      "_kat_logo_pfad(" in _logo and "SYSART_FOTO_BASE" not in _logo
      and "SYSART_BASE" not in _logo)
for fn in ("kategorie_logo_auftraege", "kategorie_logo_alle",
           "_kat_logo_eintraege"):
    kc = nur_code(koerper(_QF, fn, "Frontend"))
    check("%-26s baut keinen eigenen Pfad" % fn,
          "SYSART_BASE" not in kc and "SYSART_FOTO_BASE" not in kc,
          "vorbereitet wurde sonst das Abzeichen, gezeichnet das Foto")
check("kategorie_logo_auftraege() laeuft nicht mehr ueber ANSICHTEN",
      "in ANSICHTEN:" not in nur_code(
          koerper(_QF, "kategorie_logo_auftraege", "Frontend")),
      "das ist die Liste der SPIELELISTE")

# ---------------------------------------------------------------------------
print()
print("Test 4: beim Start die drei klassischen UND die aktuelle")
# ---------------------------------------------------------------------------
# thumb_cache_has() sagt, was schon auf der Karte liegt - hier soll
# ALLES als fehlend gelten, sonst haengt der Test am Zustand eines
# Ordners.
_echt_has = fm.thumb_cache_has
fm.thumb_cache_has = lambda *a, **k: False
try:
    def auftraege(ansicht, w=1920, h=1080):
        f_ = haupt(w, h, ansicht)
        return f_, set(f_.kategorie_logo_auftraege())

    f, a_liste = auftraege("liste")
    klassisch = set()
    for a in ("liste", "raster", "galerie"):
        klassisch |= set(f._kat_logo_eintraege(a))
    check("in der Liste: genau die drei klassischen",
          a_liste == klassisch, "%d gegen %d" % (len(a_liste),
                                                 len(klassisch)))
    for neu in ("kachelwand", "dashboard", "karussell"):
        f, a_neu = auftraege(neu)
        eigene = set(f._kat_logo_eintraege(neu))
        check("in %-10s: die klassischen plus die eigenen (%d)"
              % (neu, len(eigene)),
              a_neu == klassisch | eigene and bool(eigene - klassisch))
        fremde = set()
        for anderer in ("kachelwand", "dashboard", "karussell"):
            if anderer != neu:
                fremde |= set(f._kat_logo_eintraege(anderer))
        check("in %-10s: NICHT die der anderen neuen Ansichten" % neu,
              not ((fremde - eigene - klassisch) & a_neu),
              "wer das Karussell nie benutzt, soll dafuer nichts "
              "rechnen")
    f, a_kar = auftraege("karussell")
    check("das Karussell bringt drei Groessen je Kategorie mit Bild",
          len(a_kar - klassisch) == 3 * len(KEYS),
          "%d bei %d Kategorien" % (len(a_kar - klassisch), len(KEYS)))
    check("und davon %d aus dem Fotosatz" % (3 * len(MIT_FOTO)),
          len([e for e in a_kar if e[0].startswith(FOTOS)])
          == 3 * len(MIT_FOTO))
finally:
    fm.thumb_cache_has = _echt_has

# ---------------------------------------------------------------------------
print()
print("Test 5: der Menuepunkt und der Coverflow")
# ---------------------------------------------------------------------------
_menue = nur_code(koerper(_QF, "vorbereitungs_kaesten", "Frontend"))
check("der Menuepunkt fragt vorbereitungs_kaesten()",
      "geos = self.vorbereitungs_kaesten(geo)" in nur_code(
          koerper(_QF, "_thumb_prewarm_durchlauf", "Frontend")))
check("der Coverflow kommt nur mit, wenn er die Vorgabe ist",
      "_a in ANSICHTEN_NUR_HD and _a != _vorgabe" in _menue,
      "sieben Miniaturen je Cover laegen bei 21.000 Covern an der "
      "Grenze von 150.000 Dateien")
check("und nie auf einem Bild, das ihn nicht zeigen kann",
      "self._ansicht_hd(_a) != _a" in _menue)
check("und holt sich vorn ausdruecklich den Kasten der LISTE",
      'geo = self._art_panel_geometrie("liste")' in nur_code(
          koerper(_QF, "_thumb_prewarm_durchlauf", "Frontend"))
      or "geo = self._art_panel_geometrie('liste')" in nur_code(
          koerper(_QF, "_thumb_prewarm_durchlauf", "Frontend")),
      "ohne Angabe waere es die Ansicht der Kategorie unter dem "
      "Zeiger - und die Listenansicht fehlte im ganzen Durchlauf")
# Und dasselbe als Verhalten: steht der Zeiger auf einer Kategorie
# mit Raster als Ansicht, muss vorn trotzdem der Listenkasten stehen.
f = liste(1920, 1080, "raster")
check("vorbereitungs_kaesten() beginnt auch im Raster mit der Liste",
      f.vorbereitungs_kaesten()[0]
      == f._art_panel_geometrie("liste", erzwingen=True)
      and f.vorbereitungs_kaesten()[0][0] != "fest")
for vorgabe, w_, h_, soll in (("liste", 1920, 1080, 4),
                              ("coverflow", 1920, 1080, 7),
                              ("coverflow", 320, 240, 4)):
    f = liste(w_, h_, vorgabe)
    n = len(f.vorbereitungs_kaesten())
    check("%4dx%-4d Vorgabe %-9s -> %d Kaesten" % (w_, h_, vorgabe, soll),
          n == soll, "%d" % n)
check("die Grenze, mit der gerechnet wurde, steht noch so da",
      A.THUMB_CACHE_MAX_FILES == 150000,
      "aendert sie sich, gehoert die Entscheidung neu gerechnet")

# ---------------------------------------------------------------------------
print()
print("Test 6: auf der Roehre")
# ---------------------------------------------------------------------------
f = haupt(320, 240, "karussell")
check("das Karussell faellt auf die Liste zurueck",
      f.aktuelle_ansicht_haupt() == "liste")
check("und vorbereitet wird dann der Kasten der Liste",
      set(f.kategorie_logo_alle())
      == set(f._kat_logo_eintraege("liste")))
check("ohne ein einziges Foto",
      not [e for e in f.kategorie_logo_alle() if e[0].startswith(FOTOS)])
f = liste(320, 240, "coverflow")
check("der Coverflow faellt auf die Galerie zurueck",
      f.aktuelle_ansicht() == "galerie")
gefragt, zurueck = mitschreiben()
try:
    f.draw()
finally:
    zurueck()
_n, _r, syskey = f.cats[f.cat_i]
vorbereitet = set()
for g in f._ansicht_geometrien(f.aktuelle_ansicht()):
    for it in f._display_items():
        e = f.cover_pfad_und_kasten(it, syskey, g)
        if e:
            vorbereitet.add((e[0], int(e[1]), int(e[2])))
check("und was sie zeichnet, ist vorbereitet",
      bool(gefragt) and not (gefragt - vorbereitet),
      "%d gefragt" % len(gefragt))

print()
if fails:
    print("ROT: %d Pruefung(en) fehlgeschlagen:" % len(fails))
    for f_ in fails:
        print("   - " + f_)
    sys.exit(1)
print("ALLES GRUEN")
