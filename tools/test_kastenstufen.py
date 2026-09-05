#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft die drei Stufen der Boxart-Kastenhoehe (Build 86).

AUSLOESER (Nutzer-Rueckmeldung): "Ich habe den Eindruck, dass das mit dem
Miniaturen vorbereiten nicht richtig klappt - wenn das durchgelaufen ist
und ich gehe in irgendein System und blaettere durch die ROMs, kommt es
mir so vor, als wuerde das Frontend immer noch nachjustieren."

DER ZUSAMMENHANG: die Kastenhoehe haengt am Text unter dem Cover, und der
aendert sich im Betrieb. Startet man ein Spiel zum ersten Mal, kommt
"Gespielt: 12min" als neue Zeile dazu - der Kasten wird um eine
Zeilenhoehe kleiner, der Cache-Schluessel ein anderer, und die beim
Vorbereiten berechnete Miniatur passt nicht mehr. Dasselbe bei
"Durchgespielt" und bei jeder Aenderung des RA-Fortschritts.

Nachgerechnet gab es bis zu ZWOELF verschiedene Kastenhoehen
(CRT 68..165, HDMI 513..772). Mit drei Stufen bleibt eine Textzeile mehr
oder weniger fast immer in derselben Stufe.

DIE ZWEI ZUSAGEN, die hier geprueft werden:
  1. Es gibt hoechstens drei Kastenhoehen je Aufloesung.
  2. Der Text passt IMMER noch vollstaendig in die Spalte - eine Stufe,
     die den Text hinausdruecken wuerde, wird nicht genommen.

Die zweite ist die wichtigere: eine Stufung, die Text abschneidet, waere
schlimmer als das Problem, das sie loest.

Ausfuehren:
    python3 tools/test_kastenstufen.py
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import _harness as H                                  # noqa: E402

fm = H.fm
fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


TITEL = [
    "A",
    "Super Mario World",
    "Ein etwas laengerer Spieltitel mit vielen Woertern",
    "Ein ausgesprochen langer Spieltitel der ueber mehrere Zeilen "
    "laeuft und einfach nicht aufhoert",
]
INFOS = [
    {},
    {"players": "1-2"},
    {"players": "1-2", "year": "1991"},
    {"players": "1-2", "year": "1991", "genre": "Action-Adventure"},
    {"players": "1-2", "year": "1991", "genre": "Action-Adventure",
     "manufacturer": "Nintendo"},
]


def alle_faelle(w, h):
    """Jede Kombination aus Titellaenge, Metadaten, Spielzeit,
    Durchgespielt und RA-Fortschritt - also der komplette Raum, in dem
    sich die Kastenhoehe bewegen kann."""
    H.set_screen(w, h)
    f = H.make_frontend(page=1)
    L = f.layout_items(True)
    s = L["s"]
    art_x0 = fm.art_spalte_x0(L["list_right"], h, s)
    art_w = (w - L["ox"]) - art_x0
    art_h = L["footer_y"] - 8 * s - L["oy"]
    ergebnisse = []
    for titel in TITEL:
        for meta in INFOS:
            for gespielt in (False, True):
                for fertig in (False, True):
                    for ra in (None, (12, 40)):
                        fm.get_meta = lambda sk, n, m=meta: m
                        f._playtime_cache = ({titel: {"seconds": 4500}}
                                             if gespielt else {})
                        f._completed_set = {titel} if fertig else set()
                        f._ra_lookup = {"x": 1} if ra else None
                        if ra:
                            fm.lookup_ra_progress = lambda *a, **k: ra
                        else:
                            fm.lookup_ra_progress = lambda *a, **k: None
                        it = (titel, "game",
                              ("/f/x.sfc", ".sfc", "SNES", None, (1, "f", 0)))
                        aw, ch, tl, il, _r = f.cover_box_size(
                            art_w, art_h, "SNES", it, s)
                        line_h = 12 * s
                        text_h = len(tl) * line_h
                        if il:
                            text_h += 4 * s + len(il) * line_h
                        ergebnisse.append((ch, text_h, art_h, s))
    return ergebnisse


for w, h, name in ((320, 240, "CRT"), (640, 480, "480p"),
                   (1920, 1080, "HDMI")):
    print("Test: %s (%dx%d)" % (name, w, h))
    faelle = alle_faelle(w, h)
    hoehen = sorted({c for c, _t, _a, _s in faelle})
    check("hoechstens 3 verschiedene Kastenhoehen",
          len(hoehen) <= 3, "%d: %s" % (len(hoehen), hoehen))
    # Die wichtigere Zusage.
    passt_nicht = [(c, t, a) for c, t, a, s in faelle
                   if c + t + 8 * s > a]
    check("der Text passt in JEDEM Fall noch vollstaendig",
          not passt_nicht,
          "%d Faelle zu eng, z.B. %s" % (len(passt_nicht),
                                         passt_nicht[:1]))
    check("die Kaesten sind alle brauchbar gross",
          min(hoehen) >= 20, "kleinster %d" % min(hoehen))
    print("       %d Faelle geprueft, Stufen: %s" % (len(faelle), hoehen))
    print()

print("Test: eine Textzeile mehr wechselt die Stufe nur selten")
# Das ist der eigentliche Zweck. Frueher hat JEDE zusaetzliche Zeile die
# Kastenhoehe um line_h veraendert und damit den Cache-Schluessel - beim
# ersten Start eines Spiels also garantiert.
for w, h, name in ((320, 240, "CRT"), (1920, 1080, "HDMI")):
    H.set_screen(w, h)
    f = H.make_frontend(page=1)
    L = f.layout_items(True)
    s = L["s"]
    art_x0 = fm.art_spalte_x0(L["list_right"], h, s)
    art_w = (w - L["ox"]) - art_x0
    art_h = L["footer_y"] - 8 * s - L["oy"]
    fm.get_meta = lambda sk, n: {"players": "1-2", "year": "1991"}
    fm.lookup_ra_progress = lambda *a, **k: None
    f._ra_lookup = None
    f._completed_set = set()
    it = ("Super Mario World", "game",
          ("/f/x.sfc", ".sfc", "SNES", None, (1, "f", 0)))
    f._playtime_cache = {}
    vorher = f.cover_box_size(art_w, art_h, "SNES", it, s)[1]
    # Genau das passiert beim ersten Start eines Spiels:
    f._playtime_cache = {"Super Mario World": {"seconds": 720}}
    nachher = f.cover_box_size(art_w, art_h, "SNES", it, s)[1]
    check("%s: 'Gespielt'-Zeile aendert die Kastenhoehe NICHT" % name,
          vorher == nachher, "%d -> %d" % (vorher, nachher))

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for f_ in fails:
        print("  -", f_)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
