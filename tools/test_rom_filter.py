#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft, dass ROMs aus den Ordnern des Nutzers nicht mehr stillschweigend
verschwinden.

AUSLOESER (Nutzer-Rueckmeldung): "Die Datei heisst Tetris (Japan) (En).gb -
das ist die, die auch bei RetroAchievements genutzt werden soll. Diese
wurde bei mir weder mit kuratierter Liste noch ohne erkannt. Erst als ich
den Dateinamen auf Tetris.gb geaendert habe."

Zwei Ursachen, beide hier abgesichert:

1. Der Nur-Japan-Filter kannte die Ausnahme "(Japan, USA)" (mehrere
   Regionen in EINER Klammer), aber nicht "japanisches Release mit
   englischer Sprachfassung", wo die Sprache in einer ZWEITEN Klammer
   steht - in No-Intro-Sets die uebliche Schreibweise.

2. Beide Filter (_is_junk und _is_japan_only) liefen beim EINLESEN,
   immer, ohne Schalter und ohne Hinweis - und damit VOR der kuratierten
   Liste. Deshalb half deren Abschalten nicht: die Datei war da bereits
   verworfen. Jetzt gibt es einen Schalter, standardmaessig AUS.

Ausfuehren:
    python3 tools/test_rom_filter.py
"""
import os
import shutil
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
_FRONTEND_DIR = os.path.dirname(
    os.environ.get("FRONTEND_PY",
                   os.path.join(_REPO, "frontend", "frontend.py")))
sys.path.insert(0, _FRONTEND_DIR)

import fe.naming as N                                 # noqa: E402
import fe.settings as S                               # noqa: E402
import fe.scan as SC                                  # noqa: E402
import fe.translations as T                           # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


print("Test 1: der gemeldete Fall selbst")
check("'Tetris (Japan) (En)' wird NICHT als nur-japanisch verworfen",
      not N._is_japan_only("Tetris (Japan) (En)"))
check("'Tetris (Japan)' bleibt nur-japanisch",
      N._is_japan_only("Tetris (Japan)"))

print()
print("Test 2: uebliche Schreibweisen aus No-Intro/Redump")
FAELLE = [
    ("Tetris (Japan) (En)", False, "japanisches Release, englisch"),
    ("Puyo Puyo (Japan) (En,Ja)", False, "zweisprachig mit Englisch"),
    ("Spiel (Japan) (En,Fr,De)", False, "mehrsprachig mit Englisch"),
    ("Spiel [Japan] (En)", False, "eckige Klammern"),
    ("Spiel (Japan) (Ja)", True, "japanisch, nur japanische Sprache"),
    ("Spiel (Japan)", True, "japanisch, ohne Sprachangabe"),
    ("Spiel (J)", True, "alte Kurzform"),
    ("Spiel (Japan, USA)", False, "mehrere Regionen in EINER Klammer"),
    ("Spiel (USA)", False, "USA"),
    ("Spiel (Europe) (En,Fr,De)", False, "Europa"),
]
for name, soll, was in FAELLE:
    check("%-28s -> %s (%s)"
          % (name, "ausgeblendet" if soll else "sichtbar", was),
          N._is_japan_only(name) is soll)

print()
print("Test 3: der Schalter - Standard ist AUS (nichts wird gefiltert)")
TMP = tempfile.mkdtemp(prefix="romfilter_")
S.ROM_FILTER_FLAG = os.path.join(TMP, "rom_filter")
check("frisch: Filter aus", not S.rom_filter_enabled())
check("die Datei bedeutet AN, nicht 'abgeschaltet'",
      not S.ROM_FILTER_FLAG.endswith("disabled"))
check("einschalten meldet AN", S.toggle_rom_filter() is True)
check("danach an", S.rom_filter_enabled())
check("ausschalten meldet AUS", S.toggle_rom_filter() is False)
check("danach wieder aus", not S.rom_filter_enabled())

print()
print("Test 4: das Einlesen selbst - mit und ohne Filter")
ROMS = os.path.join(TMP, "GAMEBOY")
os.makedirs(ROMS)
DATEIEN = [
    "Tetris (Japan) (En).gb",          # der gemeldete Fall
    "Tetris (World).gb",
    "Spiel (Japan).gb",                # nur japanisch
    "Spiel (USA) (Beta).gb",           # unfertiger Dump
    "Spiel (USA) (Proto).gb",
    "Spiel (USA).gb",
    "Spiel (USA) [b].gb",              # als fehlerhaft markiert
]
for fn in DATEIEN:
    open(os.path.join(ROMS, fn), "w").close()


def eingelesen():
    node = SC._scan_folder_tree(ROMS, "GAMEBOY", "/x.rbf", {".gb": (1, "f", 1)})
    return sorted(e[0] for e in node["items"])


S.toggle_rom_filter()                  # AN
if not S.rom_filter_enabled():
    S.toggle_rom_filter()
mit = eingelesen()
S.toggle_rom_filter()                  # AUS
ohne = eingelesen()

check("OHNE Filter erscheint JEDE Datei aus dem Ordner",
      len(ohne) == len(DATEIEN), "%d von %d: %s" % (len(ohne), len(DATEIEN), ohne))
check("OHNE Filter ist der gemeldete Tetris-Titel dabei",
      "Tetris (Japan) (En)" in ohne)
check("OHNE Filter ist auch 'Spiel (Japan)' dabei", "Spiel (Japan)" in ohne)
check("OHNE Filter ist auch der Beta-Dump dabei", "Spiel (USA) (Beta)" in ohne)

check("MIT Filter faellt 'Spiel (Japan)' weg", "Spiel (Japan)" not in mit)
check("MIT Filter faellt der Beta-Dump weg", "Spiel (USA) (Beta)" not in mit)
check("MIT Filter faellt der Proto-Dump weg", "Spiel (USA) (Proto)" not in mit)
check("MIT Filter faellt der [b]-Dump weg", "Spiel (USA) [b]" not in mit)
# Das ist der Kern des gemeldeten Fehlers: dieser Titel muss AUCH mit
# eingeschaltetem Filter sichtbar bleiben - er ist auf Englisch spielbar.
check("MIT Filter bleibt 'Tetris (Japan) (En)' TROTZDEM sichtbar",
      "Tetris (Japan) (En)" in mit, str(mit))
check("MIT Filter bleiben die normalen Titel sichtbar",
      "Spiel (USA)" in mit and "Tetris (World)" in mit)

print()
print("Test 5: ein Umschalten laesst die Spieleliste neu einlesen")
# Die Filter wirken beim EINLESEN, nicht beim Anzeigen. Ohne den
# Schalterzustand im Fingerabdruck wuerde ein Umschalten erst beim
# naechsten ohnehin faelligen Neuscan sichtbar - der Menuepunkt wirkte
# dann kaputt.
import fe.paths                                        # noqa: E402
alt_bases = fe.paths.GAMES_BASES
try:
    fe.paths.GAMES_BASES = [TMP]
    S.toggle_rom_filter()
    sig_an, _ = SC._games_signature()
    S.toggle_rom_filter()
    sig_aus, _ = SC._games_signature()
finally:
    fe.paths.GAMES_BASES = alt_bases
check("der Fingerabdruck kennt den Schalter",
      any(e[0] == "__rom_filter__" for e in sig_an),
      str([e for e in sig_an if e[0].startswith("__")]))
check("und aendert sich beim Umschalten", sig_an != sig_aus)

print()
print("Test 6: Menuepunkt und Uebersetzungen")
menu_py = open(os.path.join(_FRONTEND_DIR, "fe", "menu.py"),
               encoding="utf-8").read()
check('der Menuepunkt "rom_filter" ist eingetragen',
      '"rom_filter", None' in menu_py)
fe_py = open(os.path.join(_FRONTEND_DIR, "frontend.py"), encoding="utf-8").read()
check("und wird in frontend.py behandelt", 'kind == "rom_filter"' in fe_py)
check("das Umschalten stoesst einen Neuscan an",
      'kind == "rom_filter"' in fe_py
      and "force_rescan=True" in fe_py.split('kind == "rom_filter"')[1][:1600])

tabelle = getattr(T, "TRANSLATIONS", None) or getattr(T, "STRINGS", {})
for schluessel in ("sys_rom_filter_on", "sys_rom_filter_off",
                   "sys_rom_filter_changed"):
    eintrag = tabelle.get(schluessel)
    check("Uebersetzung %s vorhanden (de+en)" % schluessel,
          bool(eintrag) and "de" in eintrag and "en" in eintrag)
# Die Zeile muss NENNEN, was gefiltert wird - "Filter an/aus" allein
# sagt niemandem, welche Dateien dann fehlen. Genau diese
# Unsichtbarkeit war das eigentliche Problem.
for schluessel in ("sys_rom_filter_on", "sys_rom_filter_off"):
    de = tabelle.get(schluessel, {}).get("de", "").lower()
    check("%s nennt konkret, was ausgeblendet wird" % schluessel,
          "beta" in de and "japan" in de, de[:60])

shutil.rmtree(TMP, ignore_errors=True)

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for f in fails:
        print("   ", f)
    sys.exit(1)
print("Alle Tests bestanden.")
