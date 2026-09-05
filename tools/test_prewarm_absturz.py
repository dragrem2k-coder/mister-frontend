#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft, dass "Miniaturen vorbereiten" das Frontend nicht mehr
umbringen kann (Build 82).

AUSLOESER (Nutzer-Rueckmeldung):

    "wenn er mit Miniaturen erstellen fertig ist, springt das Frontend
     ins OSD. Wenn ich dann das Frontend_Start.sh Script starte, geht er
     wieder ins Frontend rein, alles gut."

Das Frontend ist dort nicht ins OSD "gesprungen" - es ist ABGESTUERZT.
Der Aufraeum-Block in run() leert bei JEDEM Ende den Bildschirm und
injiziert F12, damit MiSTer sauber sein eigenes Menue zeigt. Von aussen
ist ein Absturz dadurch von einem gewollten Beenden nicht zu
unterscheiden - deshalb sah es nach einem Bedienfehler aus statt nach
einem Fehler.

DIE URSACHE, nachgestellt: ein Eintrag ohne Systemkey (Sonderkategorien
wie System oder Zufalls-Zock haben bewusst syskey=None) fuehrte in
fe/art.py zu

    os.path.join(ART_BASE, None)   ->   TypeError

Ein TypeError ist KEIN OSError - keiner der bestehenden except-Zweige
hat ihn gefangen, er flog bis aus run() heraus.

Ausfuehren:
    python3 tools/test_prewarm_absturz.py
"""
import os
import sys
import traceback

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


# Alle Eintragsformen, die im Frontend tatsaechlich vorkommen - samt der
# schraegen. Genau diese Mischung steht in den Sonderkategorien.
EINTRAEGE = [
    ("Zufalls-Zock - Spiel ziehen", "wot_draw", None),
    ("Reboot", "reboot", None),
    ("Ein Script", "script", "/media/fat/Scripts/x.sh"),
    ("Ein Core", "core", "/media/fat/_Console/NES.rbf"),
    ("Unterordner/", "folder", "Unterordner"),
    ("Spiel", "game", ("/f/a.sfc", ".sfc", "SNES", None, (1, "f", 0))),
    ("Kaputt kurz", "game", ("/f/b.sfc",)),
    ("Kaputt None", "game", None),
    ("Kaputt Text", "game", "keintupel"),
    ("Ohne Arg", "menu"),
    ("Arcade-Spiel", "game", ("/f/c.mra", ".mra", "ARCADE", None, (1, "f", 0))),
    ("Leerer Name", "game", ("", ".sfc", "SNES", None, (1, "f", 0))),
]


def frontend_mit_eintraegen(w=320, h=240, eintraege=None):
    H.set_screen(w, h)
    f = H.make_frontend(page=0)
    items = list(eintraege if eintraege is not None else EINTRAEGE)
    node = {"items": items, "folders": {"sub": {"items": items,
                                                "folders": {}}}}
    # Eine Kategorie MIT und eine OHNE Systemkey - die ohne ist der Fall,
    # der abgestuerzt ist.
    f.cats = [("Mit Systemkey", node, "SNES"),
              ("Ohne Systemkey", node, None)]
    f.page = 0
    f.cat_i = 0
    f.inp.read_action = lambda timeout=None: None      # nie abbrechen
    f.inp.flush = lambda: None
    return f


print("Test 1: der eigentliche Absturz - Eintrag ohne Systemkey")
# Direkt an der Stelle, an der es geknallt hat. Der Test prueft die
# Zusage "liefert None", nicht bloss "stuerzt nicht ab" - eine Funktion,
# die stattdessen einen unbrauchbaren Pfad zurueckgibt, waere genauso
# falsch, nur leiser.
for beschreibung, syskey, name in (
        ("ohne Systemkey", None, "Irgendein Spiel"),
        ("ohne Namen", "SNES", None),
        ("beides fehlt", None, None)):
    try:
        pfad = A.art_path(syskey, name)
        ok, fehler = pfad is None, "lieferte %r" % (pfad,)
    except Exception as e:                             # noqa: BLE001
        ok, fehler = False, "%s: %s" % (type(e).__name__, e)
    check("art_path %s liefert None" % beschreibung, ok, fehler)

print()
print("Test 2: ein Bild ohne Pfad wird ruhig abgelehnt")
# Die andere Haelfte: die acht Aufrufstellen geben den Rueckgabewert
# ungeprueft an ART weiter.
check("ART.get(None) liefert None", A.ART.get(None) is None)
check("ART.get_scaled(None, ...) liefert None",
      A.ART.get_scaled(None, 100, 100) is None)

print()
print("Test 3: der komplette Durchlauf ueberlebt jede Eintragsform")
for w, h, name in ((320, 240, "CRT"), (1920, 1080, "HDMI")):
    f = frontend_mit_eintraegen(w, h)
    try:
        f.run_thumb_prewarm_all()
        ok, fehler = True, ""
    except BaseException:                              # noqa: BLE001
        ok = False
        fehler = traceback.format_exc().strip().splitlines()[-1]
    check("%s: laeuft durch, ohne das Frontend mitzunehmen" % name,
          ok, fehler)

print()
print("Test 4: auch ein unerwarteter Fehler beendet nur den Vorgang")
# Das Sicherheitsnetz selbst. "Miniaturen vorbereiten" ist eine reine
# Bequemlichkeitsfunktion - was darin schiefgeht, darf hoechstens diesen
# einen Vorgang kosten, niemals die laufende Sitzung.
f = frontend_mit_eintraegen()
echt = f.cover_pfad_und_kasten


def kaputt(item, cat_syskey, geo):
    if item[0] == "Spiel":
        raise RuntimeError("absichtlicher Testfehler")
    return echt(item, cat_syskey, geo)


f.cover_pfad_und_kasten = kaputt
try:
    f.run_thumb_prewarm_all()
    ok, fehler = True, ""
except BaseException:                                  # noqa: BLE001
    ok = False
    fehler = traceback.format_exc().strip().splitlines()[-1]
check("ein Fehler mitten im Durchlauf entkommt nicht", ok, fehler)

print()
print("Test 5: doppelte Eintraege werden nur EINMAL gerechnet")
# Nutzer-Rueckmeldung: "wenn ich Miniaturen starte, steht da dann 178
# von 52000, wobei die meisten ROMs kein Artwork besitzen". 52000 war
# die Zahl ALLER Eintraege aller Kategorien - dasselbe Spiel zaehlt dort
# unter Favoriten, Zuletzt gespielt und in jeder Sammlung erneut mit,
# dazu alle Nicht-Spiele.
spiel = ("Spiel", "game", ("/f/a.sfc", ".sfc", "SNES", None, (1, "f", 0)))
f = frontend_mit_eintraegen(eintraege=[spiel] * 25)
gesehen = []
_echt_has = fm.thumb_cache_has
fm.thumb_cache_has = lambda p, bw, bh: (gesehen.append((p, bw, bh))
                                        or True)
try:
    f.run_thumb_prewarm_all()
finally:
    fm.thumb_cache_has = _echt_has
# Die Kategorie-Logos laufen ueber denselben Aufruf (siehe
# kategorie_logo_auftraege()) - die gehoeren hier nicht dazu.
spiele = [g for g in gesehen if fm.SYSART_BASE not in g[0]]
# 25 Eintraege x 2 Ordner x 2 Kategorien = 100 Vorkommen desselben Spiels
check("100 gleiche Eintraege ergeben 1 Cover-Pruefung",
      len(spiele) == 1, "%d Pruefungen (%d davon Kategorie-Logos)"
      % (len(spiele), len(gesehen) - len(spiele)))

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for f_ in fails:
        print("  -", f_)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
