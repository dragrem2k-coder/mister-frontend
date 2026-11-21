#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Der Attract-Modus: nur Spiele mit Cover, OK startet, Links/Rechts wechselt (Build 334/335).

NUTZERWUNSCH: "ausserdem haette ich noch gerne das der attract modus nur
spiele anzeigt die auch ein cover haben!"

GEPRUEFT WIRD:
  1. cover_bekannt() (fe/art.py): ein Cover als .art, .png, .jpg und mit
     fuehrender Nummer zaehlt; ein Spiel ohne Datei nicht; und das ohne
     einen einzigen Plattenzugriff je Spiel (nur der Index je System).
  2. (Build 335) Der Attract-Modus zieht nur Spiele mit Cover - nach
     derselben Regel wie das Bild (ab 720 Zeilen nur art_hd) -, fragt
     dabei nur die gezogenen Spiele ab und merkt es sich. Der Pool selbst
     bleibt ALLE Spiele, und die Sammlungen fragen gar kein Cover ab
     (der Fehler aus Build 334: 15,5 s beim Start).
  3. Gibt es gar kein Spiel mit Cover, startet der Attract-Modus nicht.
  4. OK startet das gezeigte Spiel, Links/Rechts wechselt das System.

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
    print("Test 2: die Wahl des Attract-Modus (Build 335)")
    # -----------------------------------------------------------------------
    anlegen(os.path.join(SD, "SNES", "NurSD.art"))

    def spiel(n, sk="SNES"):
        return (n, "game", (n + ".x", ".x", sk, "_Console/" + sk,
                            (2, "f", 0)))
    namen = ["Alpha", "Beta", "Epsilon", "NurSD", "Delta"]
    knoten = {"folders": {"Unter": {"folders": {}, "items": [spiel("Gamma")]}},
              "items": [spiel(n) for n in namen]}

    def frontend_bei(w, h, cats=None):
        H.set_screen(w, h)
        f = H.make_frontend(page=0)
        f.draw = lambda *a, **k: None
        f.cats = cats or [("SNES", knoten, "SNES"), ("System", {
            "folders": {}, "items": [("x", "game", None)]}, None)]
        f._attract_pool = None
        return f

    def gezogen(f, n=300, **k):
        return {(f._attract_waehlen(**k) or ("-",))[0] for _ in range(n)}

    f = frontend_bei(1280, 720)
    check("HDMI: gezogen werden nur Spiele mit HD-Cover",
          gezogen(f) == {"Alpha", "Beta", "Delta", "Gamma"}, gezogen(f))
    f = frontend_bei(320, 240)
    check("Roehre: SD-Cover zaehlt, HD-Cover auch",
          gezogen(f) == {"Alpha", "Beta", "Delta", "Gamma", "NurSD"})
    pool = sorted(g[0] for g in f._attract_games_pool())
    check("GEGENPROBE: der Pool selbst bleibt ALLE Spiele (Sammlungen, "
          "Zufalls-Zock und F11 brauchen ihn so)",
          pool == sorted(namen + ["Gamma"]), pool)

    # Der Fehler aus Build 334: build_collections_category() bei jedem
    # Start - 15.570 ms in seinem Bench 24. Die Cover-Frage darf dort gar
    # nicht gestellt werden.
    f = frontend_bei(1280, 720)
    gefragt = []
    _echt_hat = f._hat_cover
    f._hat_cover = lambda sk, n: gefragt.append(n) or _echt_hat(sk, n)
    f.build_collections_category()
    check("Sammlungen bauen fragt KEIN Cover ab (Bench: 15,5 s)",
          not gefragt, len(gefragt))
    f._hat_cover = _echt_hat

    # gezaehlt: eine Wahl fragt nur, was sie zieht - und merkt es sich
    gross = {"folders": {}, "items": [spiel("Ohne%05d" % i)
                                      for i in range(20000)]
             + [spiel("Alpha")]}
    f = frontend_bei(1280, 720, [("SNES", gross, "SNES")])
    gefragt = []
    f._hat_cover = lambda sk, n: gefragt.append(n) or _echt_hat(sk, n)
    g = f._attract_waehlen()
    check("20.001 Spiele, eines mit Cover: hoechstens 400 Fragen je Wahl",
          len(gefragt) <= f.ATTRACT_SUCHE_ZUEGE, len(gefragt))
    vorher = len(gefragt)
    for _ in range(5):
        f._attract_waehlen()
    check("schon gefragte Spiele werden nicht nochmal gefragt",
          len(set(gefragt)) == len(gefragt), len(gefragt) - vorher)

    # -----------------------------------------------------------------------
    print()
    print("Test 3: Start des Attract-Modus")
    # -----------------------------------------------------------------------
    f = frontend_bei(1280, 720, [("SNES", {"folders": {}, "items": [
        spiel("Epsilon"), spiel("NurSD")]}, "SNES")])
    f.attract_mode = False
    f._enter_attract_mode()
    check("kein Spiel mit Cover: der Attract-Modus startet nicht",
          f.attract_mode is False)
    f = frontend_bei(1280, 720, [("SNES", {"folders": {}, "items": [
        spiel("Epsilon"), spiel("Alpha")]}, "SNES")])
    gesehen = set()
    for _ in range(20):
        f._enter_attract_mode()
        gesehen.add(f._attract_game[0])
        f._advance_attract()
        gesehen.add(f._attract_game[0])
    check("es werden nur Spiele mit Cover gezeigt", gesehen == {"Alpha"},
          gesehen)

    # -----------------------------------------------------------------------
    print()
    print("Test 4: OK startet, Links/Rechts wechselt das System (Build 335)")
    # -----------------------------------------------------------------------
    anlegen(os.path.join(HD, "NES", "Mario.png"))
    anlegen(os.path.join(HD, "GBA", "Zelda.png"))
    # Test 1 hat den NES-Ordner schon einmal (leer) angesehen - der Index
    # haelt das fest, wie auf dem Geraet bis zum naechsten Neuaufbau.
    A._art_index_cache.clear()
    cats = [("NES", {"folders": {}, "items": [spiel("Mario", "NES")]}, "NES"),
            ("SNES", {"folders": {}, "items": [spiel("Alpha"),
                                               spiel("Epsilon")]}, "SNES"),
            ("PSX", {"folders": {}, "items": [spiel("OhneCover", "PSX")]},
             "PSX"),
            ("GBA", {"folders": {}, "items": [spiel("Zelda", "GBA")]}, "GBA")]
    f = frontend_bei(1280, 720, cats)
    f._enter_attract_mode()
    f._attract_game = [g for g in f._attract_games_pool()
                       if g[0] == "Alpha"][0]
    check("rechts: naechstes System (NES -> SNES -> GBA, PSX hat kein Cover)",
          f._attract_system_wechseln(1) and f._attract_game[1] == "GBA",
          f._attract_game[:2])
    check("rechts am Ende: rundherum zu NES",
          f._attract_system_wechseln(1) and f._attract_game[1] == "NES")
    check("links: zurueck zu GBA",
          f._attract_system_wechseln(-1) and f._attract_game[1] == "GBA")

    # durch next_action(): die Tasten so, wie sie ankommen
    def tasten(f, liste):
        rest = list(liste)

        def lesen(timeout=None):
            if not rest:
                raise RuntimeError("keine Taste mehr")
            return rest.pop(0)
        f.inp.read_action = lesen
    f.attract_mode = True
    f._attract_game = [g for g in f._attract_games_pool()
                       if g[0] == "Alpha"][0]
    tasten(f, ["right", "down", "up"])
    act = f.next_action()
    check("next_action: rechts wechselt das System, die naechste Taste "
          "weckt nur, die dritte wirkt",
          act == "up" and f._attract_game[1] == "GBA"
          and f.attract_mode is False, (act, f._attract_game[:2]))
    f.attract_mode = True
    gezeigt = f._attract_game
    tasten(f, ["ok"])
    act = f.next_action()
    check("OK im Attract-Modus: 'random' mit genau dem gezeigten Spiel",
          act == "random" and f._attract_start_spiel == gezeigt
          and f.attract_mode is False, act)
    q = open(H.FRONTEND_PY, encoding="utf-8").read()
    i = q.find('_aus_attract = getattr(self, "_attract_start_spiel"')
    check("der Zufallsstart nimmt dann genau dieses Spiel",
          i > 0 and "pool = [_aus_attract]" in q[i:i + 400])
    check("der Hinweis nennt OK und Links/Rechts",
          "OK" in fm.t("attract_hint") and "</>" in fm.t("attract_hint")
          and len(fm.t("attract_hint")) <= 40)
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
