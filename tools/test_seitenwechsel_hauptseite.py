#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Raster und Kachelwand wechseln die Seite ohne Vollbild - Bildpunkt fuer Bildpunkt wie ein voller Aufbau (Build 328).

DER ANLASS: Bench 24, Abschnitt Q - beim Durchblaettern der Hauptseite
zeichnete das Raster in 6 und die Kachelwand in 4 von 58 Schritten ein
VOLLBILD, die langsamsten Schritte lagen bei 217 und 260 ms. Das sind
die Seitenwechsel: der ganze Schirm wurde geloescht, Kopf und
Fusszeile neu gezeichnet und 7,9 MB hinausgeschickt, obwohl sich nur
die Kacheln aendern. Nutzerwunsch: "2 noch machen".

Seit Build 328 raeumt ein Seitenwechsel nur die Kachelfelder frei,
zeichnet die Kacheln der neuen Seite und schickt nur diese Rechtecke
(plus Name und Fusszeile) hinaus.

GEPRUEFT WIRD, je Ansicht:
  1. Durch ALLE Kategorien, zweimal, in beide Richtungen: nach jedem
     Schritt ist das Bild Bildpunkt fuer Bildpunkt dasselbe wie nach
     einem vollen Aufbau an derselben Stelle.
  2. Dabei laeuft kein einziges Vollbild - auch nicht beim
     Seitenwechsel (es gibt welche, das wird gezaehlt).
  3. GEGENPROBE: der Vergleich kann rot werden - ein leerer Platz, der
     beim Wechsel auf die (nicht volle) letzte Seite NICHT geraeumt
     wird, faellt auf.
  4. Ein erzwungener Neuaufbau und ein fremdes Vollbild dazwischen
     nehmen weiter den vollen Weg.
  5. Auf dem Schirm (nicht nur im Puffer) steht nach dem Wechsel das
     neue Bild - die gesammelten Rechtecke reichen.

Ausfuehren:
    python3 tools/test_seitenwechsel_hauptseite.py
"""
import os
import shutil
import sys
import tempfile

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
sys.path.insert(0, _HIER)

import _harness as H                                     # noqa: E402

fm = H.fm
import fe.art as A                                       # noqa: E402
import fe.settings as S                                  # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


print(__doc__.strip().split("\n")[0])
print()

TMP = tempfile.mkdtemp(prefix="seitenwechsel_")
SYSART = os.path.join(_REPO, "frontend", "sysart")
FOTOS = os.path.join(_REPO, "frontend", "sysart_foto")
A.SYSART_BASE = fm.SYSART_BASE = SYSART
A.SYSART_FOTO_BASE = fm.SYSART_FOTO_BASE = FOTOS
# Die fuenf Verfaelscher eines Bildvergleichs (siehe
# tools/test_hauptseite_stil.py).
A.ART.LIMIT = 100000
A.ART.ORIGINAL_MIN = 100000
A.ART.ORIGINAL_BUDGET = 8 * 1024 * 1024 * 1024
A.ART.SCALED_MIN = 100000
A.ART.SCALED_BUDGET = 8 * 1024 * 1024 * 1024
S.PULSE_EFFECT_DISABLED_FLAG = os.path.join(TMP, "kein_puls")
open(S.PULSE_EFFECT_DISABLED_FLAG, "w").close()
# Die Ansicht der Hauptseite steht in einer DATEI - in eine eigene, damit
# dieser Test keine Spur hinterlaesst (siehe test_dashboard_blaettern.py).
_ALT_ANSICHT_DATEI = S.ANSICHT_HAUPT_FILE
S.ANSICHT_HAUPT_FILE = os.path.join(TMP, "ansicht_haupt")
A.THUMB_CACHE_BASE = os.path.join(TMP, "thumbs")
A.THUMB_CACHE_DIR = os.path.join(A.THUMB_CACHE_BASE, "hd")
os.makedirs(A.THUMB_CACHE_DIR, exist_ok=True)

KEYS = ["FAVORITES", "CONTINUE", "RECENT", "COLLECTIONS", "NES", "SNES",
        "GAMEBOY", "GBC", "GBA", "N64", "Genesis", "SMS", "MegaCD", "PSX",
        "Saturn", "TGFX16", "NEOGEO", "ATARI2600", "ARCADE",
        "SUPERGAMEBOY", "S32X", "VIRTUALBOY", "COMPUTER", "GAMEGEAR",
        "ATARILYNX", "COLECOVISION", "SYSTEM", "PHYSICAL_DISC_CORES",
        "FDS"]


def frontend(ansicht):
    S.ansicht_haupt_schreiben(ansicht)
    H._zwischenspeicher_leeren()
    H.set_screen(1920, 1080)
    f = H.make_frontend(page=0)
    f._ansicht_haupt = None
    f._last_input_time = 0
    A.ART.auslagern = None
    f.cats = [(k, {"items": [], "folders": {}}, k) for k in KEYS]
    f.cat_i = 0
    f.cat_scroll = 0
    f._force_full_redraw = True
    f.draw()
    return f


def voll(f):
    f._force_full_redraw = True
    f.draw()
    return bytes(f.fb.buf)


def gang(f, schritte):
    n = len(f.cats)
    abw = []
    gewechselt = 0
    vollbilder = 0
    for k in schritte:
        alt_scroll = f.cat_scroll
        alt = f.cat_i
        f.cat_i = k % n
        gen = f.fb.full_redraw_gen
        if not f._draw_navigate_cats(alt):
            f.draw()
        if f.fb.full_redraw_gen != gen:
            vollbilder += 1
        if f.cat_scroll != alt_scroll:
            gewechselt += 1
        schritt_bild = bytes(f.fb.buf)
        if voll(f) != schritt_bild:
            abw.append(k % n)
    return abw, gewechselt, vollbilder


try:
    for ansicht, zeichner in (("raster", "_kat_kachel_zeichnen"),
                              ("kachelwand", "_wand_kachel_zeichnen")):
        if ansicht not in S.ANSICHTEN_HAUPT:
            print("  -- keine Ansicht %s in diesem Stand" % ansicht)
            continue
        print("=== %s ===" % ansicht)
        # -------------------------------------------------------------------
        print("Test 1 und 2: durch alle Kategorien, beide Richtungen")
        # -------------------------------------------------------------------
        f = frontend(ansicht)
        n = len(f.cats)
        check("die Ansicht ist %s" % ansicht,
              f.aktuelle_ansicht_haupt() == ansicht,
              f.aktuelle_ansicht_haupt())
        check("es gibt mehr als eine Seite", f.cats_visible < n,
              "%d je Seite, %d Kategorien" % (f.cats_visible, n))
        runter = list(range(1, 2 * n + 1))
        abw, gew, vb = gang(f, runter)
        check("runter: in jedem Schritt wie ein voller Aufbau", not abw,
              "abweichend bei %s" % abw[:6])
        check("runter: die Seite hat gewechselt", gew >= 2, "%d mal" % gew)
        check("runter: kein einziges Vollbild", vb == 0,
              "%d von %d" % (vb, len(runter)))
        f = frontend(ansicht)
        f.cat_i = n - 1
        voll(f)
        hoch = list(range(n - 2, -n - 1, -1))
        abw, gew, vb = gang(f, hoch)
        check("hoch: in jedem Schritt wie ein voller Aufbau", not abw,
              "abweichend bei %s" % abw[:6])
        check("hoch: die Seite hat gewechselt", gew >= 2, "%d mal" % gew)
        check("hoch: kein einziges Vollbild", vb == 0,
              "%d von %d" % (vb, len(hoch)))

        # -------------------------------------------------------------------
        print("Test 3: GEGENPROBE - ein ungeraeumter leerer Platz faellt auf")
        # -------------------------------------------------------------------
        f = frontend(ansicht)
        echt_restore = f._restore_row_bg
        proseite = f.cats_visible
        letzter = f._kachel_feld(f.raster_geometrie(f.kat_layout())
                                 if ansicht == "raster"
                                 else f.kachelwand_geometrie(f.kat_layout()),
                                 proseite - 1)

        def _vergesslich(x, y, w, h):
            if (x, y, w, h) == letzter:
                return                      # der letzte Platz bleibt stehen
            return echt_restore(x, y, w, h)
        f._restore_row_bg = _vergesslich
        abw, gew, _v = gang(f, list(range(1, n + 1)))
        f._restore_row_bg = echt_restore
        check("der Vergleich wird rot", len(abw) > 0,
              "%d abweichende Schritte" % len(abw))

        # -------------------------------------------------------------------
        print("Test 4: erzwungen und nach fremdem Vollbild: voller Weg")
        # -------------------------------------------------------------------
        f = frontend(ansicht)
        gen = f.fb.full_redraw_gen
        f._force_full_redraw = True
        f.draw()
        check("erzwungen: Vollbild", f.fb.full_redraw_gen != gen)
        f.fb.mark_full_redraw()
        gen_vor = f.fb.full_redraw_gen
        f.cat_i = n - 1                     # andere Seite
        f.draw()
        check("nach einem fremden Vollbild: wieder ein voller Aufbau",
              f.fb.full_redraw_gen > gen_vor,
              "%d -> %d" % (gen_vor, f.fb.full_redraw_gen))

        # -------------------------------------------------------------------
        print("Test 5: auf dem Schirm steht das neue Bild")
        # -------------------------------------------------------------------
        f = frontend(ansicht)
        mm = getattr(f.fb, "mm", None)
        if mm is None:
            print("  -- die Attrappe hat keinen Schirm")
        else:
            f.cat_i = proseite - 1
            if not f._draw_navigate_cats(0):
                f.draw()
            gen = f.fb.full_redraw_gen
            alt = f.cat_i
            f.cat_i = proseite              # erste Kachel der naechsten Seite
            if not f._draw_navigate_cats(alt):
                f.draw()
            check("es war ein Seitenwechsel ohne Vollbild",
                  f.cat_scroll == proseite and f.fb.full_redraw_gen == gen)
            check("Schirm gleich Puffer", bytes(mm) == bytes(f.fb.buf))
        print()
finally:
    S.ANSICHT_HAUPT_FILE = _ALT_ANSICHT_DATEI
    H._zwischenspeicher_leeren()
    shutil.rmtree(TMP, ignore_errors=True)

if fails:
    print("ROT: %d Pruefung(en) fehlgeschlagen:" % len(fails))
    for f_ in fails:
        print("   - " + f_)
    sys.exit(1)
print("ALLES GRUEN")
