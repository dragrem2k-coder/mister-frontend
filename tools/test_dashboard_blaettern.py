#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Das Dashboard blaettert ohne Vollbild - Bildpunkt fuer Bildpunkt wie ein voller Aufbau (Build 324).

DER ANLASS: Bench 24, Abschnitt Q - beim Durchblaettern der Hauptseite
zeichnete das Dashboard in 24 von 58 Schritten ein VOLLBILD: jedes Mal,
wenn das Fenster der Liste mitwanderte (cat_scroll stand im fast_key).
Im Log vom 15.11. dazu 80 bis 147 ms je Schritt beim Halten der Taste,
"Ansicht=dashboard".

Seit Build 324 schreibt das Dashboard in diesem Fall nur die Zeilen der
Liste neu (jede raeumt ihren eigenen Streifen frei) und die Tafel ueber
ihren schnellen Weg.

GEPRUEFT WIRD:
  1. Durch ALLE Kategorien, zweimal, in beide Richtungen: nach jedem
     Schritt ist das Bild Bildpunkt fuer Bildpunkt dasselbe wie nach
     einem vollen Aufbau an derselben Stelle.
  2. Dabei laeuft kein einziges Vollbild - auch nicht in den Schritten,
     in denen das Fenster wandert (es gibt welche, das wird gezaehlt).
  3. GEGENPROBE: der Vergleich kann rot werden - eine Zeile, die beim
     Wandern NICHT neu geschrieben wird, faellt auf.
  4. Eine andere Aufloesung oder ein erzwungener Neuaufbau nimmt weiter
     den vollen Weg.

Ausfuehren:
    python3 tools/test_dashboard_blaettern.py
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

TMP = tempfile.mkdtemp(prefix="dash_blaettern_")
SYSART = os.path.join(_REPO, "frontend", "sysart")
FOTOS = os.path.join(_REPO, "frontend", "sysart_foto")
A.SYSART_BASE = fm.SYSART_BASE = SYSART
A.SYSART_FOTO_BASE = fm.SYSART_FOTO_BASE = FOTOS
# Die fuenf Verfaelscher eines Bildvergleichs (siehe
# tools/test_hauptseite_stil.py): kein Verdraengen, kein Schimmer, kein
# Auslagern, kein Cover-Schutz, eigener Zwischenspeicher.
A.ART.LIMIT = 100000
A.ART.ORIGINAL_MIN = 100000
A.ART.ORIGINAL_BUDGET = 8 * 1024 * 1024 * 1024
A.ART.SCALED_MIN = 100000
A.ART.SCALED_BUDGET = 8 * 1024 * 1024 * 1024
S.PULSE_EFFECT_DISABLED_FLAG = os.path.join(TMP, "kein_puls")
open(S.PULSE_EFFECT_DISABLED_FLAG, "w").close()
# Die Ansicht der Hauptseite steht in einer DATEI. In eine eigene, damit
# dieser Test keine Spur hinterlaesst - beim ersten Anlauf stand danach
# "dashboard" in /media/fat/frontend/ansicht_haupt, und
# tools/test_hauptseite_spuren.py (das die Liste erwartet) wurde rot.
_ALT_ANSICHT_DATEI = S.ANSICHT_HAUPT_FILE
S.ANSICHT_HAUPT_FILE = os.path.join(TMP, "ansicht_haupt")
A.THUMB_CACHE_BASE = os.path.join(TMP, "thumbs")
A.THUMB_CACHE_DIR = os.path.join(A.THUMB_CACHE_BASE, "hd")
os.makedirs(A.THUMB_CACHE_DIR, exist_ok=True)

KEYS = ["FAVORITES", "CONTINUE", "RECENT", "COLLECTIONS", "NES", "SNES",
        "GAMEBOY", "GBC", "GBA", "N64", "Genesis", "SMS", "MegaCD", "PSX",
        "Saturn", "TGFX16", "NEOGEO", "ATARI2600", "ARCADE",
        "SUPERGAMEBOY", "S32X", "VIRTUALBOY", "COMPUTER", "GAMEGEAR",
        "ATARILYNX", "COLECOVISION", "SYSTEM", "PHYSICAL_DISC_CORES"]


def frontend():
    S.ansicht_haupt_schreiben("dashboard")
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
    """Die Schritte gehen; nach jedem das Bild mit einem vollen Aufbau
    an derselben Stelle vergleichen."""
    n = len(f.cats)
    abw = []
    gewandert = 0
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
            gewandert += 1
        schritt_bild = bytes(f.fb.buf)
        if voll(f) != schritt_bild:
            abw.append(k % n)
    return abw, gewandert, vollbilder


try:
    if "dashboard" not in S.ANSICHTEN_HAUPT:
        print("  -- keine Dashboard-Ansicht in diesem Stand")
        sys.exit(0)
    # -----------------------------------------------------------------------
    print("Test 1 und 2: durch alle Kategorien, beide Richtungen")
    # -----------------------------------------------------------------------
    f = frontend()
    n = len(f.cats)
    check("die Ansicht ist das Dashboard",
          f.aktuelle_ansicht_haupt() == "dashboard",
          f.aktuelle_ansicht_haupt())
    runter = list(range(1, 2 * n + 1))
    abw, gewandert, vollbilder = gang(f, runter)
    check("runter: in jedem Schritt wie ein voller Aufbau", not abw,
          "abweichend bei %s" % abw[:6])
    check("runter: das Fenster ist dabei gewandert", gewandert >= 10,
          "%d mal" % gewandert)
    check("runter: kein einziges Vollbild", vollbilder == 0,
          "%d von %d" % (vollbilder, len(runter)))
    f = frontend()
    f.cat_i = n - 1
    voll(f)
    hoch = list(range(n - 2, -n - 1, -1))
    abw, gewandert, vollbilder = gang(f, hoch)
    check("hoch: in jedem Schritt wie ein voller Aufbau", not abw,
          "abweichend bei %s" % abw[:6])
    check("hoch: das Fenster ist dabei gewandert", gewandert >= 10,
          "%d mal" % gewandert)
    check("hoch: kein einziges Vollbild", vollbilder == 0,
          "%d von %d" % (vollbilder, len(hoch)))

    # -----------------------------------------------------------------------
    print()
    print("Test 3: GEGENPROBE - eine vergessene Zeile faellt auf")
    # -----------------------------------------------------------------------
    f = frontend()
    echt = f._dash_zeile_zeichnen

    def _vergesslich(geo, platz, i, markiert, freiraeumen):
        if platz == 2 and freiraeumen and not markiert:
            return                    # beim Wandern NICHT neu geschrieben
        return echt(geo, platz, i, markiert, freiraeumen)

    f._dash_zeile_zeichnen = _vergesslich
    abw, gewandert, _v = gang(f, list(range(1, 2 * n + 1)))
    check("der Vergleich wird rot, wenn eine Zeile stehenbleibt",
          len(abw) > 0, "%d abweichende Schritte" % len(abw))

    # -----------------------------------------------------------------------
    print()
    print("Test 4: ein erzwungener Neuaufbau nimmt weiter den vollen Weg")
    # -----------------------------------------------------------------------
    f = frontend()
    f.cat_i = n - 1
    gen = f.fb.full_redraw_gen
    f._force_full_redraw = True
    f.draw()
    check("erzwungen: Vollbild", f.fb.full_redraw_gen != gen)
    # Ein fremdes Vollbild dazwischen (z.B. ein Dialog war offen): dann
    # stimmt der Puffer nicht mehr, und das Wandern darf NICHT den
    # kurzen Weg nehmen.
    f.fb.mark_full_redraw()
    gen_vor = f.fb.full_redraw_gen
    f.cat_i = 0                         # das Fenster wandert ganz nach oben
    f.draw()
    check("nach einem fremden Vollbild: wieder ein voller Aufbau",
          f.fb.full_redraw_gen > gen_vor,
          "%d -> %d" % (gen_vor, f.fb.full_redraw_gen))
finally:
    S.ANSICHT_HAUPT_FILE = _ALT_ANSICHT_DATEI
    H._zwischenspeicher_leeren()
    shutil.rmtree(TMP, ignore_errors=True)

print()
if fails:
    print("ROT: %d Pruefung(en) fehlgeschlagen:" % len(fails))
    for f_ in fails:
        print("   - " + f_)
    sys.exit(1)
print("ALLES GRUEN")
