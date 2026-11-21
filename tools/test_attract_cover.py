#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Der Attract-Modus zeigt nur Spiele mit Cover (Build 334).

NUTZERWUNSCH: "ausserdem haette ich noch gerne das der attract modus nur
spiele anzeigt die auch ein cover haben!"

GEPRUEFT WIRD:
  1. cover_bekannt() (fe/art.py): ein Cover als .art, .png, .jpg und mit
     fuehrender Nummer zaehlt; ein Spiel ohne Datei nicht; und das ohne
     einen einzigen Plattenzugriff je Spiel (nur der Index je System).
  2. Der Attract-Pool enthaelt nur Spiele mit Cover - nach derselben
     Regel wie das Bild selbst (cover_quelle()): ab 720 Zeilen nur
     art_hd, darunter art und art_hd.
  3. Gibt es gar kein Spiel mit Cover, startet der Attract-Modus nicht.
  4. Der Attract-Modus waehlt aus genau diesem Pool.

Ausfuehren:
    python3 tools/test_attract_cover.py
"""
import os
import shutil
import sys
import tempfile

_HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HIER)

import _harness as H                                     # noqa: E402

fm = H.fm
import fe.art as A                                       # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


def anlegen(pfad):
    os.makedirs(os.path.dirname(pfad), exist_ok=True)
    open(pfad, "wb").close()


print(__doc__.strip().split("\n")[0])
print()

TMP = tempfile.mkdtemp(prefix="attract_")
_alt = (fm.ART_HD, fm.ART_BASE, A.fremdquellen_enabled)
try:
    SD = os.path.join(TMP, "art")
    HD = os.path.join(TMP, "art_hd")
    fm.ART_HD, fm.ART_BASE = HD, SD
    # Die fremde Datenbank aus dem Spiel lassen - sie liegt in diesem
    # Container nicht, auf dem Geraet vielleicht schon.
    A.fremdquellen_enabled = lambda: False
    A._art_index_cache.clear()

    # -----------------------------------------------------------------------
    print("Test 1: cover_bekannt()")
    # -----------------------------------------------------------------------
    anlegen(os.path.join(HD, "SNES", "Alpha.art"))
    anlegen(os.path.join(HD, "SNES", "Beta.png"))
    anlegen(os.path.join(HD, "SNES", "Gamma.jpg"))
    anlegen(os.path.join(HD, "SNES", "007 Delta.art"))
    for name in ("Alpha", "Beta", "Gamma"):
        check("%s: Cover erkannt" % name, A.cover_bekannt(HD, "SNES", name))
    check("mit fuehrender Nummer im Dateinamen erkannt",
          A.cover_bekannt(HD, "SNES", "Delta"))
    check("GEGENPROBE: ohne Datei kein Cover",
          not A.cover_bekannt(HD, "SNES", "Epsilon"))
    check("GEGENPROBE: anderes System, kein Ordner",
          not A.cover_bekannt(HD, "NES", "Alpha"))
    check("ohne Systemkey: nein, kein Absturz",
          not A.cover_bekannt(HD, None, "Alpha")
          and not A.cover_bekannt(HD, "SNES", ""))
    gezaehlt = []
    _ex, _st = os.path.exists, os.stat
    try:
        os.path.exists = lambda p: gezaehlt.append(p) or _ex(p)
        for i in range(200):
            A.cover_bekannt(HD, "SNES", "Alpha" if i % 2 else "Epsilon")
    finally:
        os.path.exists = _ex
    check("200 Abfragen ohne einen einzigen exists() (nur der Index)",
          not gezaehlt, len(gezaehlt))

    # -----------------------------------------------------------------------
    print()
    print("Test 2: der Attract-Pool")
    # -----------------------------------------------------------------------
    anlegen(os.path.join(SD, "SNES", "NurSD.art"))

    def spiel(n):
        return (n, "game", (n + ".sfc", ".sfc", "SNES", "_Console/SNES",
                            (2, "f", 0)))
    namen = ["Alpha", "Beta", "Epsilon", "NurSD", "Delta"]
    knoten = {"folders": {"Unter": {"folders": {}, "items": [spiel("Gamma")]}},
              "items": [spiel(n) for n in namen]}

    def pool_bei(w, h):
        H.set_screen(w, h)
        f = H.make_frontend(page=0)
        f.cats = [("SNES", knoten, "SNES"), ("System", {"folders": {},
                  "items": [("x", "game", None)]}, None)]
        f._attract_pool = None
        return f, sorted(g[0] for g in f._attract_games_pool())

    f, pool = pool_bei(1280, 720)
    check("HDMI: nur Spiele mit HD-Cover (auch im Unterordner)",
          pool == ["Alpha", "Beta", "Delta", "Gamma"], pool)
    check("GEGENPROBE HDMI: ein reines SD-Cover zaehlt nicht (das Bild "
          "zeigt es ab 720 Zeilen auch nicht)", "NurSD" not in pool)
    check("GEGENPROBE: ohne Cover nicht dabei", "Epsilon" not in pool)
    f, pool = pool_bei(320, 240)
    check("Roehre: SD-Cover zaehlt, HD-Cover auch",
          pool == ["Alpha", "Beta", "Delta", "Gamma", "NurSD"], pool)

    # -----------------------------------------------------------------------
    print()
    print("Test 3/4: Start des Attract-Modus")
    # -----------------------------------------------------------------------
    H.set_screen(1280, 720)
    f = H.make_frontend(page=0)
    f.draw = lambda *a, **k: None
    f.cats = [("SNES", {"folders": {}, "items": [spiel("Epsilon"),
                                                 spiel("NurSD")]}, "SNES")]
    f._attract_pool = None
    f.attract_mode = False
    f._enter_attract_mode()
    check("kein Spiel mit Cover: der Attract-Modus startet nicht",
          f.attract_mode is False)
    f.cats = [("SNES", {"folders": {}, "items": [spiel("Epsilon"),
                                                 spiel("Alpha")]}, "SNES")]
    f._attract_pool = None
    gesehen = set()
    for _ in range(20):
        f._enter_attract_mode()
        gesehen.add(f._attract_game[0])
        f._advance_attract()
        gesehen.add(f._attract_game[0])
    check("es werden nur Spiele mit Cover gezeigt", gesehen == {"Alpha"},
          gesehen)
finally:
    fm.ART_HD, fm.ART_BASE, A.fremdquellen_enabled = _alt
    A._art_index_cache.clear()
    shutil.rmtree(TMP, ignore_errors=True)

print()
if fails:
    print("ROT: %d Pruefung(en) fehlgeschlagen:" % len(fails))
    for f_ in fails:
        print("   - " + f_)
    sys.exit(1)
print("ALLES GRUEN")
