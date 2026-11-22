#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Neuaufbau behaelt die Stelle, Coverflow und Computer beim Vorbereiten (Build 338).

NUTZER: "wenn ich ab und zu mal die musikquellen durchgehe oder aender
lande ich ab und zu mal auf einen bildschirm zufalls-zock / anzeige &
sound 0 eintraege" und "coverflow hab ich das gefuehl das die covers
nicht mit vorbereitet wurden einmal abklaeren genauso die neuen computer
kategorien beruecksichtigen".

GEPRUEFT WIRD:
  1. _position_wiederfinden(): kommt beim Neuaufbau eine Kategorie
     hinzu, bleibt die Auswahl auf "System" und im Ordner; fehlt ein
     Ordner, bleibt der gueltige Teil des Pfads; fehlt die Kategorie,
     geht es zur Hauptseite. build_categories() merkt und findet.
  2. Coverflow in "Miniaturen vorbereiten": ohne Benutzung nicht (wie
     bisher), nach einmaligem Einschalten auch nach einem Neustart
     (Merkdatei); auf der Roehre nie; die Merkdatei schreibt nur einmal.
  3. Die Computer-Kategorien (C64, Amiga, Amstrad, AO486): ihre Spiele
     stehen in der Vorbereitung, und fuer jedes Spiel mit Cover gibt es
     ein Ziel je Kastengroesse.
  4. Die Hilfe nennt Coverflow und den Pad-Ausstieg Start+Select+L+R.

Ausfuehren:
    python3 tools/test_neuaufbau_und_vorbereiten.py
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
import fe.settings as SE                                 # noqa: E402
import fe.translations as TR                             # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


def knoten(items=(), folders=None):
    return {"folders": dict(folders or {}), "items": list(items)}


def anlegen(pfad):
    os.makedirs(os.path.dirname(pfad), exist_ok=True)
    open(pfad, "wb").close()


print(__doc__.strip().split("\n")[0])
print()
TMP = tempfile.mkdtemp(prefix="neuaufbau_")
_lang = TR.CURRENT_LANG
_alt = (fm.ART_HD, fm.ART_BASE, A.fremdquellen_enabled,
        SE.ANSICHTEN_BENUTZT_FILE)
try:
    TR.CURRENT_LANG = "de"
    # -----------------------------------------------------------------------
    print("Test 1: der Neuaufbau behaelt die Stelle")
    # -----------------------------------------------------------------------
    H.set_screen(1280, 720)
    f = H.make_frontend(page=1)
    system = knoten(folders={
        "Anzeige & Sound": knoten([("Musik-Quelle: MP3", "music_source",
                                    None), ("Lautstaerke", "volume", None)]),
        "Info": knoten([("Hilfe", "help", None)])})
    vorher = [("SNES", knoten([("Mario", "game", None)]), "SNES"),
              ("Zufalls-Zock", knoten([("Ziehen", "zufallszock_draw", None)]), None),
              ("System", system, None)]
    f.cats = vorher
    f.cat_i = 2
    f.page = 1
    f.nav_path = ["Anzeige & Sound"]
    f._nav_position_stack = [(0, 0)]
    f.item_i = 1
    gemerkt = f._position_merken()
    check("gemerkt wird Name und Systemkey", gemerkt == ("System", None))
    # Der Neuaufbau bringt eine Kategorie mehr (z.B. den Erfolgsjaeger)
    f.cats = [vorher[0], ("RA-Erfolgsjaeger", knoten([("x", "game", None)]),
                          None)] + vorher[1:]
    f._position_wiederfinden(gemerkt)
    check("eine Kategorie mehr: weiter auf System (nicht Zufalls-Zock)",
          f.cats[f.cat_i][0] == "System", f.cats[f.cat_i][0])
    check("... im selben Ordner, an derselben Stelle",
          f.nav_path == ["Anzeige & Sound"] and f.item_i == 1
          and f.page == 1, (f.nav_path, f.item_i))
    check("... mit Eintraegen (nicht '0 Eintraege')",
          len(f._display_items()) == 2)
    # Ordner fehlt (z.B. nach dem Sprachwechsel anders benannt)
    f.cats = [vorher[0], ("System", knoten(folders={
        "Display & Sound": knoten([("x", "volume", None)])}), None)]
    f._position_wiederfinden(("System", None))
    check("Ordner gibt es nicht mehr: zurueck auf die oberste Ebene",
          f.nav_path == [] and f._nav_position_stack == []
          and f.item_i == 0, (f.nav_path, f._nav_position_stack))
    # Kategorie fehlt
    f.cats = [vorher[0]]
    f.cat_i = 0
    f.page = 1
    f.nav_path = ["X"]
    f._position_wiederfinden(("Weg", None))
    check("Kategorie gibt es nicht mehr: zur Hauptseite",
          f.page == 0 and f.nav_path == [] and f.cat_i == 0)
    check("erster Aufbau (nichts gemerkt): kein Absturz",
          f._position_wiederfinden(None) is None)
    q = open(H.FRONTEND_PY, encoding="utf-8").read()
    k = q[q.find("    def build_categories("):]
    k = k[:k.find("\n    def ", 10)]
    check("build_categories() merkt am Anfang und findet am Ende",
          k.find("_vorher = self._position_merken()")
          < k.find("self._position_wiederfinden(_vorher)")
          and k.rstrip().endswith("self._position_wiederfinden(_vorher)"))

    # -----------------------------------------------------------------------
    print()
    print("Test 2: der Coverflow beim Vorbereiten")
    # -----------------------------------------------------------------------
    SE.ANSICHTEN_BENUTZT_FILE = os.path.join(TMP, "ansichten_benutzt")
    flow = None
    for (w, hh) in ((1920, 1080), (320, 240)):
        H.set_screen(w, hh)
        f = H.make_frontend(page=1)
        f._ansicht_je_kat = {}
        if os.path.exists(SE.ANSICHTEN_BENUTZT_FILE):
            os.remove(SE.ANSICHTEN_BENUTZT_FILE)
        flow = set(f._ansicht_geometrien("coverflow", erzwingen=True))
        ohne = f.vorbereitungs_kaesten()
        if w == 1920:
            check("HDMI, nie benutzt: kein Coverflow (wie bisher)",
                  not flow & set(ohne) or SE.ansicht_lesen() == "coverflow",
                  ohne)
        f.ansicht_setzen("coverflow")
        f2 = H.make_frontend(page=1)          # "nach dem Neustart"
        f2._ansicht_je_kat = {}
        mit = f2.vorbereitungs_kaesten()
        if w == 1920:
            check("HDMI, einmal benutzt: nach dem Neustart alle drei "
                  "Coverflow-Kaesten dabei", len(flow) == 3
                  and flow <= set(mit), mit)
        else:
            check("Roehre: der Coverflow wird nie vorbereitet (dort ist er "
                  "die Galerie)", not (set(mit) - set(ohne)), mit)
    check("die Merkdatei hat genau einen Eintrag",
          open(SE.ANSICHTEN_BENUTZT_FILE).read() == "coverflow\n")
    check("ein zweites Einschalten schreibt nichts mehr",
          SE.ansicht_benutzt_merken("coverflow") is False)
    check("nur HD-Ansichten werden gemerkt",
          SE.ansicht_benutzt_merken("raster") is False)
    SE.ANSICHTEN_BENUTZT_FILE = os.path.join(TMP, "fehlt", "x", "y")
    check("ohne Datei: leere Menge, kein Absturz",
          SE.ansichten_benutzt() == set())

    # -----------------------------------------------------------------------
    print()
    print("Test 3: die Computer-Kategorien beim Vorbereiten")
    # -----------------------------------------------------------------------
    HD = os.path.join(TMP, "art_hd")
    fm.ART_HD = HD
    fm.ART_BASE = os.path.join(TMP, "art")
    A.fremdquellen_enabled = lambda: False
    A._art_index_cache.clear()
    computer = {"C64": "Commodore 64", "AMIGA": "Amiga 500",
                "AMSTRAD": "Amstrad CPC", "AO486": "PC (486)"}
    for sk in computer:
        anlegen(os.path.join(HD, sk, "Spiel %s.png" % sk))
    H.set_screen(1920, 1080)
    f = H.make_frontend(page=1)

    def spiel(name, sk):
        return (name, "game", (name + ".x", ".x", sk, "_Computer/" + sk,
                               (2, "f", 0)))
    f.cats = [(titel, knoten([spiel("Spiel %s" % sk, sk),
                              spiel("Ohne Cover", sk)],
                             {"Unter": knoten([spiel("Spiel %s" % sk, sk)])}),
               sk) for sk, titel in computer.items()]
    alle = f._alle_spiel_eintraege()
    je_sys = {}
    for item, sk in alle:
        if item[1] == "game":
            je_sys[sk] = je_sys.get(sk, 0) + 1
    check("alle vier Computer stehen in der Vorbereitung, auch Unterordner",
          je_sys == {sk: 3 for sk in computer}, je_sys)
    geos = f.vorbereitungs_kaesten()
    for sk in computer:
        ziele = {f.cover_pfad_und_kasten(spiel("Spiel %s" % sk, sk), sk, g)
                 for g in geos}
        check("%s: ein Ziel je Kastengroesse (%d)" % (sk, len(geos)),
              None not in ziele and len(ziele) == len(geos)
              and all(z[0].endswith("Spiel %s.png" % sk) for z in ziele))
        # Ohne Cover liefert cover_quelle() den Rueckfall-Pfad (siehe
        # cover_bekannt() in fe/art.py) - das Vorbereiten ueberspringt
        # ihn dann, weil es die Datei nicht gibt.
        check("%s: ohne Cover kein vorhandenes Bild als Ziel" % sk,
              all(z is None or not os.path.exists(z[0]) for z in
                  (f.cover_pfad_und_kasten(spiel("Ohne Cover", sk), sk, g)
                   for g in geos)))

    # -----------------------------------------------------------------------
    print()
    print("Test 4: die Hilfe")
    # -----------------------------------------------------------------------
    check("Ansicht wechseln nennt den Coverflow",
          "Coverflow" in fm.t("help_list_ansicht_desc"))
    check("der Pad-Ausstieg heisst Start+Select+L+R wie seit Build 326",
          "L+R" in fm.t("help_playing_exit_pad_key")
          and "Start+Select" in fm.t("help_playing_exit_pad_desc"))
    TR.CURRENT_LANG = "en"
    check("... auch auf Englisch", "L+R" in fm.t("help_playing_exit_pad_key")
          and "coverflow" in fm.t("help_list_ansicht_desc"))
finally:
    TR.CURRENT_LANG = _lang
    (fm.ART_HD, fm.ART_BASE, A.fremdquellen_enabled,
     SE.ANSICHTEN_BENUTZT_FILE) = _alt
    A._art_index_cache.clear()
    shutil.rmtree(TMP, ignore_errors=True)

print()
if fails:
    print("ROT: %d Pruefung(en) fehlgeschlagen:" % len(fails))
    for f_ in fails:
        print("   - " + f_)
    sys.exit(1)
print("ALLES GRUEN")
