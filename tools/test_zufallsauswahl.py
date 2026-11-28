#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Zufalls-Zock nur aus gewaehlten Systemen (Build 354).

NUTZERWUNSCH: "wenn jemand zum Beispiel nur SNES, Mega Drive, NES,
Game Boy Spiele haben will, sollte man das einstellen koennen - am
besten unter System".

GEPRUEFT WIRD:
  1. fe/zufallsauswahl.py: Vorgabe alle, speichern (ueber .tmp),
     wieder lesen, alle = Datei weg, kaputte Datei = alle, filtern,
     zaehlen.
  2. Systemmenue: Eintrag unter Optionen, mit "alle" bzw. der Zahl.
  3. Der Auswahl-Bildschirm: an/aus mit A und Links/Rechts, "Alle
     aus", "Alle an", B speichert; keines gewaehlt = wieder alle;
     ohne Aenderung wird nichts geschrieben; klemmende Eingabe.
  4. Der Zufalls-Zock zieht nur aus den gewaehlten Systemen; liegen
     dort keine Spiele, sagt er das, statt leer zu bleiben.
  5. Attract-Modus und Zufallsstart filtern NICHT mit.

Ausfuehren:
    python3 tools/test_zufallsauswahl.py
"""
import json
import os
import sys

_HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HIER)
import _harness as H                                     # noqa: E402
import fe.zufallsauswahl as ZA                           # noqa: E402
import fe.menu as MENU                                   # noqa: E402

fm = H.fm
fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


class Skript(object):
    def __init__(self, echt, tasten):
        self.echt = echt
        self.tasten = list(tasten)

    def __getattr__(self, n):
        return getattr(self.echt, n)

    def read_action(self, timeout=None):
        if self.tasten:
            return self.tasten.pop(0)
        return None


POOL = [("Mario %d" % i, "SNES", ("/s%d" % i,)) for i in range(4)] \
    + [("Sonic %d" % i, "MEGADRIVE", ("/m%d" % i,)) for i in range(3)] \
    + [("Zelda %d" % i, "NES", ("/n%d" % i,)) for i in range(2)]

# ---------------------------------------------------------------------------
print("Test 1: das Modul")
# ---------------------------------------------------------------------------
ZA.vergessen()
check("Vorgabe: alle (keine Datei)", ZA.laden() is None
      and not os.path.exists(ZA.DATEI))
check("speichern, ueber .tmp",
      ZA.speichern({"SNES", "NES"}) is True and os.path.exists(ZA.DATEI)
      and not os.path.exists(ZA.DATEI + ".tmp")
      and json.load(open(ZA.DATEI)) == {"nur": ["NES", "SNES"]})
ZA.vergessen()
check("wieder gelesen", ZA.laden() == {"SNES", "NES"})
check("filtern", [p[0] for p in ZA.filtern(POOL)]
      == ["Mario 0", "Mario 1", "Mario 2", "Mario 3", "Zelda 0", "Zelda 1"])
check("filtern mit nur=None und ohne Einstellung: alles",
      ZA.filtern(POOL, None) != POOL and ZA.filtern(POOL, set()) == POOL)
check("zaehlen", ZA.systeme(POOL) == {"SNES": 4, "MEGADRIVE": 3, "NES": 2})
check("alle: die Datei ist weg",
      ZA.speichern(None) is True and not os.path.exists(ZA.DATEI)
      and ZA.laden() is None)
for inhalt in ("{kaputt", "[1, 2]", '{"nur": "SNES"}', '{"nur": []}',
               '{"nur": [3, ""]}'):
    open(ZA.DATEI, "w").write(inhalt)
    ZA.vergessen()
    check("kaputte/fremde Datei %r: alle" % inhalt[:12], ZA.laden() is None)
os.remove(ZA.DATEI)
ZA.vergessen()


def optionen_items():
    sysm = MENU.system_items(False, "local", "")
    for _n, node in sysm["folders"].items():
        kinds = [k for _l, k, _a in node["items"]]
        if "ziehung_spannung" in kinds:
            return node["items"]
    return []


# ---------------------------------------------------------------------------
print()
print("Test 2: Systemmenue")
# ---------------------------------------------------------------------------
its = optionen_items()
kinds = [k for _l, k, _a in its]
check("unter Optionen, direkt nach der Ziehung",
      "zufall_systeme" in kinds and kinds.index("zufall_systeme")
      == kinds.index("ziehung_spannung") + 1)
label = [l for l, k, _a in its if k == "zufall_systeme"]
check("Beschriftung: alle", label == [fm.t("sys_zz_systeme",
                                           fm.t("zz_alle_kurz"))], label)
ZA.speichern({"SNES", "NES"})
label = [l for l, k, _a in optionen_items() if k == "zufall_systeme"]
check("Beschriftung: die Zahl", label == [fm.t("sys_zz_systeme", 2)], label)
ZA.speichern(None)
fq = open(H.FRONTEND_PY, encoding="utf-8").read()
check("verdrahtet", 'elif kind == "zufall_systeme":' in fq)
import fe.vorfuehrung as VF                              # noqa: E402
check("die Vorfuehrung kennt den Punkt",
      any("zufall_systeme" in g[3] for g in VF.GRUPPEN))

# ---------------------------------------------------------------------------
print()
print("Test 3: der Auswahl-Bildschirm")
# ---------------------------------------------------------------------------


def frontend():
    f = H.make_frontend(page=0)
    f.cats = [("SNES", {"folders": {}, "items": []}, "SNES"),
              ("Mega Drive (3)", {"folders": {}, "items": []}, "MEGADRIVE"),
              ("NES", {"folders": {}, "items": []}, "NES"),
              ("Arcade", {"folders": {}, "items": []}, "ARCADE")] + f.cats
    f._attract_pool = list(POOL)
    return f


fe = frontend()
echt = fe.inp


def bildschirm(tasten):
    fe.inp = Skript(echt, tasten)
    try:
        fe.zufall_systeme_bildschirm()
    finally:
        fe.inp = echt
    return ZA.laden()


# Zeilen: 0 Alle an, 1 Alle aus, 2 Mega Drive, 3 NES, 4 SNES
check("Mega Drive aus (Links), B speichert: SNES und NES",
      bildschirm(["down", "down", "left", "back"]) == {"SNES", "NES"})
check("NES aus mit A: nur noch SNES",
      bildschirm(["down", "down", "down", "ok", "back"]) == {"SNES"})
check("die Auswahl kommt beim naechsten Oeffnen wieder: NES an",
      bildschirm(["down", "down", "down", "right", "back"])
      == {"SNES", "NES"})
check("Alle an: wieder alle (auch kuenftige)",
      bildschirm(["ok", "back"]) is None and not os.path.exists(ZA.DATEI))
check("Alle aus, dann eines an: nur dieses",
      bildschirm(["down", "ok", "down", "ok", "back"]) == {"MEGADRIVE"})
check("Alle aus und so gespeichert: wieder alle, kein leerer Topf",
      bildschirm(["down", "ok", "back"]) is None)
ZA.speichern({"SNES"})
_mt = os.path.getmtime(ZA.DATEI)
os.utime(ZA.DATEI, (_mt - 100, _mt - 100))
check("ohne Aenderung wird nichts geschrieben",
      bildschirm(["down", "up", "back"]) == {"SNES"}
      and os.path.getmtime(ZA.DATEI) == _mt - 100)
check("Systeme ohne Spiele (Arcade) stehen nicht in der Liste",
      "ARCADE" not in ZA.systeme(fe._attract_pool))
fe.inp = Skript(echt, [])
try:
    fe.zufall_systeme_bildschirm()
    _ok = True
except Exception as e_:                                  # noqa: BLE001
    _ok = e_
fe.inp = echt
check("klemmende Eingabe: der Bildschirm gibt auf", _ok is True, _ok)
for b_, h_ in ((1280, 720), (320, 240)):
    H.set_screen(b_, h_)
    f2 = frontend()
    f2.inp = Skript(f2.inp, ["back"])
    try:
        f2.zufall_systeme_bildschirm()
        _ok = True
    except Exception as e_:                              # noqa: BLE001
        _ok = e_
    check("gezeichnet bei %dx%d" % (b_, h_), _ok is True, _ok)
H.set_screen(1280, 720)

# ---------------------------------------------------------------------------
print()
print("Test 4: der Zufalls-Zock zieht nur aus der Auswahl")
# ---------------------------------------------------------------------------
fe = frontend()
fe._play_ducked_sfx = lambda *a, **k: None
gezeigt = []
_sdn = fm.system_display_name
fm.system_display_name = lambda sk: gezeigt.append(sk) or str(sk)
class ImmerZurueck(Skript):
    """Der Zufalls-Zock wartet blockierend auf eine Taste - im Pruefstand
    heisst "keine Taste mehr" deshalb: zurueck."""
    def read_action(self, timeout=None):
        return self.tasten.pop(0) if self.tasten else "back"


fe.inp = ImmerZurueck(echt, [])
ZA.speichern({"NES"})
try:
    for _ in range(4):
        fe.draw_zufallszock_screen()
finally:
    fm.system_display_name = _sdn
    fe.inp = echt
check("nur NES gezogen", gezeigt and set(gezeigt) == {"NES"}, set(gezeigt))
ZA.speichern({"GAMEBOY"})
infos = []
fe._wizard_info = lambda titel, zeilen, **k: infos.append(zeilen)
fe.inp = ImmerZurueck(echt, [])
try:
    fe.draw_zufallszock_screen()
finally:
    fe.inp = echt
check("keine Spiele in der Auswahl: ein Satz, wo man es aendert",
      infos == [[fm.t("zz_keine_spiele")]], infos)
ZA.speichern(None)

# ---------------------------------------------------------------------------
print()
print("Test 5: nur der Zufalls-Zock filtert")
# ---------------------------------------------------------------------------
ZA.speichern({"NES"})
fe = frontend()
check("der gemeinsame Pool (Attract, F11, Sammlungen) bleibt ganz",
      len(fe._attract_games_pool()) == len(POOL))
zz = fq.split("    def draw_zufallszock_screen(self):")[1].split(
    "\n    def ")[0]
check("gefiltert wird im Zufalls-Zock", "ZA.filtern(pool)" in zz)
check("und nirgends sonst",
      fq.count("ZA.filtern(") == 1)
ZA.speichern(None)

print()
if fails:
    print("ROT: %d Pruefung(en) fehlgeschlagen:" % len(fails))
    for f_ in fails:
        print("   - " + f_)
    sys.exit(1)
print("ALLES GRUEN")
