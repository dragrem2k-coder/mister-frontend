#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft, dass die Systemliste EINE Quelle hat und dass die
Startparameter der bestehenden Systeme sich nicht heimlich aendern.

AUSLOESER (Nutzerfrage, Build 78): "wir haben ja den Virtual Boy mit
reingenommen - muss ich das Skript Frontend_Boxart_Download.sh nochmal
starten, damit ich die dafuer bekomme?"

Die Antwort war nein: Virtual Boy stand in keinem der drei
Download-Werkzeuge. Es gab die Systemliste VIERMAL - einmal im Frontend
und dreimal in den Werkzeugen, alle von Hand gepflegt.

DAS TUECKISCHE DARAN IST DER FEHLENDE FEHLER: das Skript laeuft durch,
klappert die ihm bekannten Systeme ab, meldet Erfolg - und laesst das
fehlende einfach aus. Sichtbar ist nur, dass keine Cover kommen, und
gesucht wird der Fehler dann zwangslaeufig woanders.

Seit Build 79 ist fe/systems.py die einzige Quelle. Dieser Test sichert
beides ab: dass die Werkzeuge wirklich von dort lesen, UND - Test 3 -
dass beim Umbau kein bestehendes System stillschweigend andere
Startparameter bekommen hat.

Ausfuehren:
    python3 tools/test_system_abdeckung.py
"""
import importlib.util
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
_FRONTEND_DIR = os.path.dirname(
    os.environ.get("FRONTEND_PY",
                   os.path.join(_REPO, "frontend", "frontend.py")))
sys.path.insert(0, _FRONTEND_DIR)

import fe.systems as SYS                              # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


def lade(pfad, name):
    """Ein Werkzeug-Skript als Modul laden, ohne es auszufuehren
    (die Skripte tun beim Import nichts ausser Definitionen)."""
    spec = importlib.util.spec_from_file_location(
        name, os.path.join(_REPO, pfad))
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


QUELLE = SYS.download_systeme()

print("Test 1: alle Werkzeuge benutzen dieselbe Systemliste")
print("        (Quelle fe/systems.py: %d Systeme mit Datenbank)" % len(QUELLE))
for pfad, name, was in (
        ("frontend/mister_boxart.py", "mb", "Boxart-Download auf dem MiSTer"),
        ("frontend/mister_gameinfo.py", "mg", "Spiele-Infos auf dem MiSTer"),
        ("PC-Tools/boxart_fetch.py", "bf", "Boxart-Download am PC")):
    modul = lade(pfad, name)
    check("%s: identisch zur Quelle" % was,
          modul.SYSTEMS == QUELLE,
          "%d statt %d Systeme" % (len(modul.SYSTEMS), len(QUELLE))
          if len(modul.SYSTEMS) != len(QUELLE) else
          "Inhalt weicht ab: %s" % sorted(
              k for k in set(modul.SYSTEMS) | set(QUELLE)
              if modul.SYSTEMS.get(k) != QUELLE.get(k))[:4])

print()
print("Test 1b: der gemeldete Fall selbst - Virtual Boy")
check("VIRTUALBOY hat eine Datenbank", "VIRTUALBOY" in QUELLE)
check("und zwar die gepruefte",
      QUELLE.get("VIRTUALBOY", (None, {}))[1].get(".vb")
      == "Nintendo - Virtual Boy",
      str(QUELLE.get("VIRTUALBOY")))

print()
print("Test 2: jedes Frontend-System hat eine Datenbank ODER einen Grund")
# Systeme, fuer die es NACHWEISLICH keine Datenbank gibt (bei
# thumbnails.libretro.com nachgesehen, nicht vermutet) bzw. geben kann.
OHNE_DATENBANK = {
    "ASTROCADE": "keine libretro-Datenbank vorhanden",
    "GAMATE": "keine libretro-Datenbank vorhanden",
    "GAMENWATCH": "keine libretro-Datenbank vorhanden",
    "MEGADUCK": "keine libretro-Datenbank vorhanden",
    "POCKETCHALLENGEV2": "keine libretro-Datenbank vorhanden",
    "VC4000": "keine libretro-Datenbank vorhanden",
    "SMW_HACKS": "Fan-Hacks - eine offizielle Datenbank kann es nicht geben",
    "SNES_ALTTP_TRACKER": "kein Spielesystem, sondern eine Tracker-Ansicht",
}
alle = [(e[0], e[1]) for e in
        (list(SYS.GAME_SYSTEMS) + list(SYS.OPTIONAL_GAME_SYSTEMS))]
fehlend = [(n, k) for n, k in alle
           if k not in QUELLE and k not in OHNE_DATENBANK]
check("kein System faellt unbemerkt durch", not fehlend,
      "ohne Datenbank UND ohne Begruendung: %s" % fehlend)
for key in OHNE_DATENBANK:
    check("Ausnahme %s gibt es im Frontend" % key,
          key in {k for _n, k in alle})

print()
print("Test 3: die Startparameter der BESTEHENDEN Systeme sind unveraendert")
# Der wichtigste Block dieser Datei. Build 79 hat fe/systems.py von 16
# auf 48 Systeme erweitert - dabei darf sich an den bereits laufenden
# nichts verschoben haben. Ein falscher Index heisst: Core startet, ROM
# laedt nicht, und zwar ohne Fehlermeldung.
#
# Die Werte hier sind der Stand VOR der Erweiterung, von Hand
# festgehalten. Sie stimmen ausserdem mit der mrext-Datenbank ueberein
# (abgerufen und verglichen) - zwei unabhaengige Belege.
BESTAND = {
    "NES":        {".nes": (2, "f", 1)},
    "SNES":       {".sfc": (2, "f", 0), ".smc": (2, "f", 0)},
    "Genesis":    {".md": (1, "f", 1), ".gen": (1, "f", 1), ".bin": (1, "f", 1)},
    "N64":        {".n64": (1, "f", 1), ".z64": (1, "f", 1)},
    "PSX":        {".chd": (1, "s", 1), ".cue": (1, "s", 1)},
    "GAMEBOY":    {".gb": (2, "f", 1)},
    "GBC":        {".gbc": (2, "f", 1)},
    "GBA":        {".gba": (2, "f", 1)},
    "SMS":        {".sms": (1, "f", 1), ".gg": (1, "f", 2)},
    "TGFX16":     {".pce": (1, "f", 0), ".sgx": (1, "f", 1)},
    "MegaCD":     {".chd": (1, "s", 0), ".cue": (1, "s", 0)},
    "Saturn":     {".chd": (1, "s", 0), ".cue": (1, "s", 0)},
    "NEOGEO":     {".neo": (1, "f", 1)},
    "SMW_HACKS":  {".sfc": (2, "f", 0), ".smc": (2, "f", 0)},
    "SNES_ALTTP_TRACKER": {".sfc": (2, "f", 0), ".smc": (2, "f", 0)},
    "VIRTUALBOY": {".vb": (1, "f", 1)},
}
BESTAND_ORDNER = {
    "NES": ["NES"], "SNES": ["SNES"], "Genesis": ["MegaDrive", "Genesis"],
    "N64": ["N64"], "PSX": ["PSX"], "GAMEBOY": ["GAMEBOY"], "GBC": ["GAMEBOY"],
    "GBA": ["GBA"], "SMS": ["SMS"], "TGFX16": ["TGFX16"], "MegaCD": ["MegaCD"],
    "Saturn": ["Saturn"], "NEOGEO": ["NEOGEO"], "SMW_HACKS": ["SNES/SMW_HACKS"],
    "SNES_ALTTP_TRACKER": ["SNES/ZELDA_MSU"], "VIRTUALBOY": ["VirtualBoy"],
}
nach_key = {e[1]: e for e in
            (list(SYS.GAME_SYSTEMS) + list(SYS.OPTIONAL_GAME_SYSTEMS))}
for key, erwartet in BESTAND.items():
    eintrag = nach_key.get(key)
    if not eintrag:
        check("%s gibt es noch" % key, False)
        continue
    check("%s: Startparameter unveraendert" % key,
          eintrag[4] == erwartet,
          "jetzt %s, erwartet %s" % (eintrag[4], erwartet))
    check("%s: ROM-Ordner unveraendert" % key,
          list(eintrag[2]) == BESTAND_ORDNER[key],
          "jetzt %s" % list(eintrag[2]))

print()
print("Test 3b: die Datenbank-Zuordnung der bestehenden Systeme "
      "ist unveraendert")
# Gleiche Ueberlegung fuer die Download-Seite. Besonders Game Gear:
# der Master-System-Core spielt auch .gg, und deren Cover liegen bei
# libretro unter einem EIGENEN Namen. Ginge diese Ausnahme beim Umbau
# verloren, wuerden Game-Gear-Spiele in der Master-System-Datenbank
# gesucht und nicht mehr gefunden - lautlos.
BESTAND_DB = {
    "NES": {".nes": "Nintendo - Nintendo Entertainment System"},
    "SNES": {".sfc": "Nintendo - Super Nintendo Entertainment System",
             ".smc": "Nintendo - Super Nintendo Entertainment System"},
    "Genesis": {".md": "Sega - Mega Drive - Genesis",
                ".gen": "Sega - Mega Drive - Genesis",
                ".bin": "Sega - Mega Drive - Genesis"},
    "GAMEBOY": {".gb": "Nintendo - Game Boy"},
    "GBC": {".gbc": "Nintendo - Game Boy Color"},
    "SMS": {".sms": "Sega - Master System - Mark III",
            ".gg": "Sega - Game Gear"},
    "TGFX16": {".pce": "NEC - PC Engine - TurboGrafx 16",
               ".sgx": "NEC - PC Engine - TurboGrafx 16"},
    "NEOGEO": {".neo": "SNK - Neo Geo"},
}
for key, erwartet in BESTAND_DB.items():
    check("%s: Datenbank-Zuordnung unveraendert" % key,
          QUELLE.get(key, (None, None))[1] == erwartet,
          "jetzt %s" % (QUELLE.get(key, (None, None))[1],))

print()
print("Test 4: die neuen Systeme sind plausibel definiert")
# Kein Ersatz fuer einen echten Test auf Hardware - aber die Sorte
# Fehler, die beim Abtippen von 30 Eintraegen entsteht, faengt das ab.
for disp, key, ordner, rbf, extmap, corepfad in SYS.OPTIONAL_GAME_SYSTEMS:
    check("%s: Core-Pruefpfad ist absolut" % disp,
          corepfad.startswith("/media/fat/"), corepfad)
    check("%s: rbf-Pfad ohne .rbf-Endung" % disp,
          not rbf.endswith(".rbf"), rbf)
    check("%s: mindestens eine Endung" % disp, bool(extmap))
    for ext, werte in extmap.items():
        check("%s: %s hat drei Startwerte" % (disp, ext),
              isinstance(werte, tuple) and len(werte) == 3, str(werte))
        check("%s: %s Methode ist f oder s" % (disp, ext),
              werte[1] in ("f", "s"), str(werte))
        check("%s: %s beginnt mit einem Punkt" % (disp, ext),
              ext.startswith("."), ext)
    check("%s: ROM-Ordner angegeben" % disp, bool(ordner))

print()
print("Test 4b: keine doppelten Systemschluessel")
keys = [e[1] for e in (list(SYS.GAME_SYSTEMS) + list(SYS.OPTIONAL_GAME_SYSTEMS))]
doppelt = sorted({k for k in keys if keys.count(k) > 1})
check("jeder Schluessel kommt genau einmal vor", not doppelt, str(doppelt))

print()
print("Test 4c: gleiche Endung im gleichen Ordner nur einmal")
# Sonst erschiene dieselbe Datei in zwei Kategorien. Beispiel, das
# bewusst KEIN Konflikt ist: das Famicom Disk System liest .fds aus dem
# Ordner NES, die NES-Kategorie liest dort nur .nes.
belegt = {}
for eintrag in (list(SYS.GAME_SYSTEMS) + list(SYS.OPTIONAL_GAME_SYSTEMS)):
    disp, _key, ordner, _rbf, extmap = eintrag[:5]
    for f in ordner:
        for ext in extmap:
            belegt.setdefault((f.lower(), ext), []).append(disp)
check("es wurden ueberhaupt Kombinationen geprueft", len(belegt) > 40,
      "%d Ordner/Endung-Kombinationen" % len(belegt))
konflikte = {k: v for k, v in belegt.items() if len(v) > 1}
check("keine Datei kann in zwei Kategorien landen", not konflikte,
      "; ".join("%s%s -> %s" % (f, e, v) for (f, e), v in
                sorted(konflikte.items())[:5]))

print()
print("Test 5: Akzentfarben")
farben = open(os.path.join(_FRONTEND_DIR, "frontend.py"),
              encoding="utf-8").read()
i = farben.index("SYSTEM_ACCENT = {")
block = farben[i:farben.index("\n}", i)]
for _disp, key in alle:
    check("%s hat eine eigene Akzentfarbe" % key, '"%s":' % key in block)

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for f in fails:
        print("   ", f)
    sys.exit(1)
print("Alle Tests bestanden.")
