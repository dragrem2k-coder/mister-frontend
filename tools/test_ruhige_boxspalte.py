#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft die vier Aenderungen an der Boxart-Spalte aus Build 89.

AUSLOESER (Nutzer-Rueckmeldung, vier Punkte in einer Nachricht):

  1. "Wenn ich durch die ROMs scrolle, etwas langsamer, ploppt immer
     erst 'kein Artwork' auf und dann wird das Cover nachgeladen."
  2. "Wenn ein ROM wirklich kein Artwork hat, die Box bitte so anpassen,
     dass das nicht immer auf die grosse blaue umspringt - das ist
     optisch nicht schoen und koennte auch Performance-Einbussen
     bedeuten."
  3. "Wenn ich in eine Kategorie reingehe und nur die Ordnerauswahl
     dort sehe, braucht daneben keine Artwork-Box stehen."
  4. "Die Kategorie vergisst, wo du warst - das bitte umsetzen."

ZU 1, DIE URSACHE: get_scaled() liefert None fuer ZWEI voellig
verschiedene Faelle - "es gibt kein Cover" und "ich habe es waehrend des
Scrollens bewusst uebersprungen, es kommt in ~150 ms" (COVER_SETTLE).
Der Zeichenpfad konnte die beiden nicht unterscheiden und malte auch im
zweiten Fall den Platzhalter, der Sekundenbruchteile spaeter vom Cover
ersetzt wurde. Ein Zaehler (ART._defer_count) trennt die Faelle jetzt.

ZU 2: der Platzhalter war eine VOLLFLAECHIG gefuellte Flaeche in der
Akzentfarbe, so gross wie das Cover geworden waere - auf HDMI rund
300x770 Bildpunkte. Jetzt ein duenner Rahmen.

Ausfuehren:
    python3 tools/test_ruhige_boxspalte.py
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import _harness as H                                  # noqa: E402

fm = H.fm
sys.path.insert(0, os.path.dirname(H.FRONTEND_PY))
import fe.art as A                                    # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


def panel_masse(f, h):
    """Die Masse der Boxart-Spalte, so wie der Zeichenpfad sie rechnet."""
    L = f.layout_items(True)
    s = L["s"]
    art_x0 = fm.art_spalte_x0(L["list_right"], h, s)
    return (art_x0, (f.fb.width - L["ox"]) - art_x0, L["oy"],
            L["footer_y"] - 8 * s - L["oy"], s)


SPIEL = ("Spiel ohne Cover", "game",
         ("/f/x.sfc", ".sfc", "SNES", None, (1, "f", 0)))


print("Test 1: ein nur VERZOEGERTES Cover zeichnet keinen Platzhalter")
# Der Kern der ersten Rueckmeldung. Unterschieden wird nicht ueber das
# Aussehen, sondern ueber den Aufruf selbst - eindeutiger.
for w, h, name in ((320, 240, "CRT"), (1920, 1080, "HDMI")):
    H.set_screen(w, h)
    f = H.make_frontend(page=1)
    x0, aw, y0, ah, s = panel_masse(f, h)
    fm.get_meta = lambda sk, n: {}
    fm.lookup_ra_progress = lambda *a, **k: None
    f._ra_lookup = None
    f._completed_set = set()
    f._playtime_cache = {}

    gerufen = []
    echt_platzhalter = f._zeichne_kein_artwork
    f._zeichne_kein_artwork = lambda *a, **k: gerufen.append(a)

    # a) wirklich kein Cover: get_scaled meldet None, OHNE zu zaehlen
    echt = A.ART.get_scaled
    A.ART.get_scaled = lambda *a, **k: None
    fm.ART.get_scaled = A.ART.get_scaled
    try:
        f.draw_art_panel(x0, aw, y0, ah, "SNES", SPIEL, s)
    finally:
        A.ART.get_scaled = echt
        fm.ART.get_scaled = echt
    check("%s: ohne Cover erscheint der Platzhalter" % name,
          len(gerufen) == 1, "%d Aufrufe" % len(gerufen))

    # b) nur verzoegert: get_scaled meldet None UND zaehlt hoch - genau
    #    so, wie es die drei Defer-Stellen in fe/art.py tun.
    gerufen[:] = []

    def verzoegernd(*a, **k):
        A.ART._defer_count += 1
        A.ART._deferred_something = True
        return None

    A.ART.get_scaled = verzoegernd
    fm.ART.get_scaled = verzoegernd
    try:
        f.draw_art_panel(x0, aw, y0, ah, "SNES", SPIEL, s)
    finally:
        A.ART.get_scaled = echt
        fm.ART.get_scaled = echt
        f._zeichne_kein_artwork = echt_platzhalter
    check("%s: beim Verzoegern erscheint KEIN Platzhalter" % name,
          not gerufen, "%d Aufrufe" % len(gerufen))

print()
print("Test 2: der Zaehler steht wirklich an allen Defer-Stellen")
# Sonst wuerde Test 1b eine Zusage pruefen, die der echte Code nicht
# einhaelt - der Test faelscht das Verzoegern ja nach.
quelle = open(os.path.join(os.path.dirname(H.FRONTEND_PY), "fe", "art.py"),
              encoding="utf-8").read()
check("jede '_deferred_something = True'-Stelle zaehlt mit",
      quelle.count("self._deferred_something = True\n            self._defer_count += 1")
      + quelle.count("self._deferred_something = True\n                self._defer_count += 1")
      == quelle.count("self._deferred_something = True"),
      "%d Defer-Stellen" % quelle.count("self._deferred_something = True"))

print()
print("Test 3: der Platzhalter ist ein Rahmen, keine gefuellte Flaeche")
# Gezaehlt werden Bildpunkte in der Akzentfarbe innerhalb des Kastens.
# Vorher war das die komplette Flaeche.
for w, h, name in ((320, 240, "CRT"), (1920, 1080, "HDMI")):
    H.set_screen(w, h)
    f = H.make_frontend(page=1)
    x0, aw, y0, ah, s = panel_masse(f, h)
    fm.get_meta = lambda sk, n: {}
    fm.lookup_ra_progress = lambda *a, **k: None
    f._ra_lookup = None
    f._completed_set = set()
    f._playtime_cache = {}
    cover_h = f.cover_box_size(aw, ah, "SNES", SPIEL, s)[1]
    avail_w = aw - 2 * (6 * s)
    f.fb.clear(fm.C_BG)
    f._zeichne_kein_artwork(x0, y0, avail_w, cover_h, s)
    ziel = fm.Framebuffer.px(fm.C_ACCENT2)
    treffer = 0
    for yy in range(y0, y0 + cover_h):
        zeile = f.fb.buf[yy * f.fb.stride:yy * f.fb.stride + f.fb.width * 4]
        for xx in range(x0, x0 + avail_w):
            if bytes(zeile[xx * 4:xx * 4 + 4]) == ziel:
                treffer += 1
    flaeche = avail_w * cover_h
    # Ein Rahmen ist der Umfang mal Strichstaerke - grosszuegig mit
    # Faktor 3 abgesichert, aber weit unter der vollen Flaeche.
    grenze = 3 * max(1, s) * 2 * (avail_w + cover_h)
    check("%s: gefaerbte Flaeche ist ein Rahmen" % name,
          treffer <= grenze,
          "%d von %d Bildpunkten (Grenze %d)" % (treffer, flaeche, grenze))
    check("%s: der Rahmen ist ueberhaupt sichtbar" % name, treffer > 0)

print()
print("Test 4: nur Ordner -> keine Boxart-Spalte")
H.set_screen(1920, 1080)
f = H.make_frontend(page=1)
nur_ordner = [("Hacks/", "folder", "Hacks"),
              ("Homebrew/", "folder", "Homebrew")]
gemischt = nur_ordner + [SPIEL]
check("nur Ordner: keine Spalte",
      f.hat_artspalte(nur_ordner, "SNES") is False)
check("Ordner UND Spiele: Spalte bleibt",
      f.hat_artspalte(gemischt, "SNES") is True)
check("nur Spiele: Spalte",
      f.hat_artspalte([SPIEL], "SNES") is True)
check("leere Liste: keine Spalte", f.hat_artspalte([], "SNES") is False)
# "Zuletzt gespielt" mischt Systeme und hat deshalb syskey=None - die
# Spalte muss dort trotzdem erscheinen.
check("gemischte Kategorie ohne Systemkey: Spalte",
      f.hat_artspalte([SPIEL], None) is True)
check("Menuepunkte ohne Systemkey: keine Spalte",
      f.hat_artspalte([("Reboot", "reboot", None)], None) is False)

# Und: die Bedingung darf nur noch an EINER Stelle stehen. Laufen die
# Aufrufer auseinander, berechnet der Vorauslader Miniaturen unter einer
# Kastengroesse, die der Zeichenpfad nie abfragt.
fquelle = open(H.FRONTEND_PY, encoding="utf-8").read()
code = "\n".join(z for z in fquelle.splitlines()
                 if not z.lstrip().startswith("#"))
check("keine zweite, handgeschriebene Bedingung mehr im Code",
      'has_art = len(' not in code and 'has_art = total' not in code)
check("alle drei Aufrufer benutzen hat_artspalte()",
      code.count("self.hat_artspalte(") >= 4,
      "%d Aufrufe" % code.count("self.hat_artspalte("))

print()
print("Test 5: die Kategorie merkt sich, wo man war")
H.set_screen(1920, 1080)
f = H.make_frontend(page=0)
# Die erste Kategorie der Attrappe hat nur einen Eintrag - fuer diesen
# Test braucht es eine, in der man ueberhaupt scrollen kann.
f.cat_i = 0
for i in range(len(f.cats)):
    f.cat_i = i
    if len(f._display_items()) > 4:
        break
f._enter_category()
check("Betreten startet oben", f.item_i == 0)
eintraege = len(f._display_items())
if eintraege > 4:
    f.item_i, f.scroll = 4, 2
    f._go_back_or_confirm_quit()          # zurueck zu den Kategorien
    check("zurueck auf der Kategorienseite", f.page == 0)
    f._enter_category()
    check("die Position ist wieder da",
          (f.item_i, f.scroll) == (4, 2), "%d/%d" % (f.item_i, f.scroll))
else:
    check("Testliste hat genug Eintraege", False,
          "%d Eintraege" % eintraege)

# Eine kuerzer gewordene Liste darf nicht ins Leere zeigen.
f._kategorie_position[f.cat_i] = (9999, 9999)
f._enter_category()
check("ein zu grosser gemerkter Index faellt auf 0 zurueck",
      (f.item_i, f.scroll) == (0, 0), "%d/%d" % (f.item_i, f.scroll))

# Nach einem Neu-Einlesen koennen sich Reihenfolge UND Kategorie-
# Nummerierung verschieben - dann ist ein gemerkter Index schlimmer als
# keiner.
f._kategorie_position[0] = (3, 1)
f.build_categories(force_rescan=False)
check("Neu-Einlesen verwirft die gemerkten Positionen",
      f._kategorie_position == {}, "%r" % (f._kategorie_position,))

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for f_ in fails:
        print("  -", f_)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
