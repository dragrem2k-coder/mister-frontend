#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft den Schalter "Cover beim Scrollen" (Build 138).

Nutzerwunsch: "ich haette gerne mal ausprobiert, ob wir in der
Listenansicht das Cover sofort anzeigen lassen - dieses wird dort ja
erst angezeigt, sobald man stehen bleibt. In der Galerie klappt das ja
mittlerweile sehr gut."

Der Unterschied liegt NICHT im Cover-Cache, sondern in einer
Entscheidung davor: die Liste laesst waehrend des Scrollens die GANZE
Cover-Spalte aus (defer_panel / _spalte_auslassen), egal ob das Cover
laengst fertig im Speicher liegt. Die Galerie zeichnet immer und
ueberspringt nur das EINZELNE noch nicht gerechnete Bild.

Der Schalter nimmt der Liste genau diese pauschale Auslassung. Getestet
wird deshalb dreierlei:
  1. AUS verhaelt sich exakt wie bisher (die Spalte wird ausgelassen),
  2. AN zeichnet sie auch waehrend des Scrollens,
  3. BEIDE Auslass-Stellen kennen den Schalter - der leichte
     Navigationsschritt UND der volle Seitenaufbau. Kennt ihn nur eine,
     haengt es vom Zeichenweg ab, ob das Cover erscheint.

Ausfuehren:
    python3 tools/test_cover_sofort.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H                                        # noqa: E402

import fe.settings as S                                     # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


# Die echten Schalterpfade liegen unter /media/fat - hier umbiegen,
# damit der Test nichts auf einem echten Geraet anfasst.
_tmp = tempfile.mkdtemp(prefix="dragend_cover_sofort_")
S.COVER_SOFORT_FLAG = os.path.join(_tmp, "cover_sofort_enabled")
S.FAST_SCROLL_ENABLED_FLAG = os.path.join(_tmp, "fast_scroll_enabled")
open(S.FAST_SCROLL_ENABLED_FLAG, "w").close()   # Schnelles Scrollen AN


def _sofort(an):
    """Schalter setzen - ueber die echte Umschaltfunktion, damit auch
    der Zwischenspeicher aus Build 135 mitbekommt, dass sich etwas
    geaendert hat."""
    if S.cover_sofort_enabled() != an:
        S.toggle_cover_sofort()
    H._zwischenspeicher_leeren()


H.set_screen(1920, 1080)
f = H.make_frontend(page=1)
f.ansicht_setzen("liste")
f._force_full_redraw = True
f.draw()
# "Gerade am Scrollen": _scroll_skip_vsync() prueft den Schalter UND
# das 150-ms-Fenster seit der letzten Eingabe.
f._last_input_time = H.NOW[0]

print("Test 1: der Schalter selbst")
_sofort(False)
check("Vorgabe ist AUS", not S.cover_sofort_enabled())
_sofort(True)
check("einschalten wirkt sofort", S.cover_sofort_enabled())
_sofort(False)
check("und ausschalten auch", not S.cover_sofort_enabled())

print()
print("Test 2: waehrend des Scrollens - AUS laesst die Spalte aus")
_sofort(False)
check("schnelles Scrollen ist aktiv", f._scroll_skip_vsync())
y0, y1 = f._art_panel_aktualisieren(f.view, f.cats[f.cat_i][2], f.item_i)
check("die Cover-Spalte wird ausgelassen", y0 is None and y1 is None)

print()
print("Test 3: waehrend des Scrollens - AN zeichnet sie")
_sofort(True)
y0, y1 = f._art_panel_aktualisieren(f.view, f.cats[f.cat_i][2], f.item_i)
check("die Cover-Spalte wird gezeichnet",
      y0 is not None and y1 is not None and y1 > y0,
      "Band %s..%s" % (y0, y1))

print()
print("Test 4: im Stillstand aendert der Schalter gar nichts")
# Das ist der wichtigste Nicht-Effekt: wer den Schalter auslaesst, soll
# genau das bisherige Verhalten behalten, und wer ihn anschaltet, darf
# im Stillstand nichts Neues erleben.
f._last_input_time = H.NOW[0] - 10.0
for an in (False, True):
    _sofort(an)
    y0, y1 = f._art_panel_aktualisieren(f.view, f.cats[f.cat_i][2], f.item_i)
    check("Schalter %s: Spalte wird gezeichnet" % ("AN " if an else "AUS"),
          y0 is not None)
f._last_input_time = H.NOW[0]

print()
print("Test 5: das Cover erscheint waehrend des Scrollens auch wirklich")
# Pixelbeweis statt Rueckgabewert: der Bereich der Cover-Spalte muss
# sich bei eingeschaltetem Schalter zwischen zwei Eintraegen
# unterscheiden, bei ausgeschaltetem nicht.
import fe.art as ART                                        # noqa: E402


def _spaltenband(f):
    """Der Bildinhalt der Cover-Spalte als Bytes."""
    has_art = f.hat_artspalte(f.view["items"], f.cats[f.cat_i][2])
    L = f.layout_items(has_art)
    y0 = L["oy"]
    y1 = L["footer_y"] - 8 * L["s"]
    fb = f.fb
    return bytes(fb.buf[y0 * fb.stride:y1 * fb.stride])


for an, erwartet in ((False, False), (True, True)):
    _sofort(an)
    f._force_full_redraw = True
    f.item_i, f.scroll = 0, 0
    f.draw()
    f._last_input_time = H.NOW[0]
    vorher = _spaltenband(f)
    f.item_i = 5
    ART._deferred_something = False
    f._art_panel_aktualisieren(f.view, f.cats[f.cat_i][2], f.item_i)
    geaendert = _spaltenband(f) != vorher
    check("Schalter %s: Spalte aendert sich beim Scrollen: %s"
          % ("AN " if an else "AUS", "ja" if geaendert else "nein"),
          geaendert == erwartet)

print()
print("Test 6: BEIDE Auslass-Stellen kennen den Schalter")
# Der leichte Navigationsschritt und der volle Seitenaufbau haben je
# eine eigene Bedingung. Kennt nur eine den Schalter, haengt es vom
# Zeichenweg ab, ob das Cover erscheint - und das faellt erst auf dem
# Geraet auf.
quelle = open(H.FRONTEND_PY, encoding="utf-8").read()
check("defer_panel (leichter Navigationsschritt)",
      "defer_panel = (has_art and self._scroll_skip_vsync()\n"
      "                       and not cover_sofort_enabled())" in quelle)
check("_spalte_auslassen (voller Seitenaufbau)",
      "and not cover_sofort_enabled()"
      in quelle.split("_spalte_auslassen = (self.fb.height")[1][:400])

print()
print("Test 7: der Menuepunkt ist verdrahtet")
menu_quelle = open(os.path.join(os.path.dirname(H.FRONTEND_PY), "fe", "menu.py"),
                   encoding="utf-8").read()
check('der Punkt steht im System-Menue',
      '"cover_sofort", None)' in menu_quelle)
check("und das Frontend behandelt ihn",
      'elif kind == "cover_sofort":' in quelle)
import fe.translations as T                                 # noqa: E402
for key in ("sys_cover_sofort_on", "sys_cover_sofort_off"):
    eintrag = T.TRANSLATIONS.get(key)
    check("Beschriftung %s in beiden Sprachen" % key,
          bool(eintrag) and "de" in eintrag and "en" in eintrag)

_sofort(False)

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Tests bestanden.")
