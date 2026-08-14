#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Spielesystem-Definitionen: GAME_SYSTEMS/OPTIONAL_GAME_SYSTEMS (Anzeige-
name, Systemkey, ROM-Ordner, Core-RBF, Dateiendungen-Zuordnung) sowie
system_display_name(). Ausgelagert aus frontend.py (Modularisierung,
Git-Branch 'modular-refactor').

Komplett eigenstaendig - keine Abhaengigkeiten zu anderem Code, reine
Daten + eine kleine Nachschlage-Funktion. Bewusst als EIGENES,
kleines Modul (nicht zusammen mit scan_games() etc.) - der groessere
Scan-Cluster (scan_games/_scan_folder_tree/...) ist im Original stark
mit anderen Konzepten verflochten (Wonne oder Tonne, Theme-System,
RetroAchievements liegen dazwischen) und wird in einem spaeteren,
eigenen Schritt behandelt.
"""

# Spielesysteme: (Anzeigename, Systemkey, ROM-Ordner, Core-RBF,
#                  {Endung: (mgl_delay, mgl_type, mgl_index)})
# MGL-Parameter stammen aus der mrext-Systemdatenbank (wizzomafizzo).
GAME_SYSTEMS = [
    ("NES",           "NES",     ["NES"],                  "_Console/NES",
        {".nes": (2, "f", 1)}),
    ("SNES",          "SNES",    ["SNES"],                 "_Console/SNES",
        {".sfc": (2, "f", 0), ".smc": (2, "f", 0)}),
    ("Mega Drive",    "Genesis", ["MegaDrive", "Genesis"], "_Console/MegaDrive",
        {".md": (1, "f", 1), ".gen": (1, "f", 1), ".bin": (1, "f", 1)}),
    ("Nintendo 64",   "N64",     ["N64"],                  "_Console/N64",
        {".n64": (1, "f", 1), ".z64": (1, "f", 1)}),
    ("PlayStation",   "PSX",     ["PSX"],                  "_Console/PSX",
        {".chd": (1, "s", 1), ".cue": (1, "s", 1)}),
    ("Game Boy",      "GAMEBOY", ["GAMEBOY"],              "_Console/Gameboy",
        {".gb": (2, "f", 1)}),
    ("Game Boy Color","GBC",     ["GAMEBOY"],              "_Console/Gameboy",
        {".gbc": (2, "f", 1)}),
    ("GBA",           "GBA",     ["GBA"],                  "_Console/GBA",
        {".gba": (2, "f", 1)}),
    ("Master System", "SMS",     ["SMS"],                  "_Console/SMS",
        {".sms": (1, "f", 1), ".gg": (1, "f", 2)}),
    ("TurboGrafx16",  "TGFX16",  ["TGFX16"],               "_Console/TurboGrafx16",
        {".pce": (1, "f", 0), ".sgx": (1, "f", 1)}),
    ("Mega CD",       "MegaCD",  ["MegaCD"],               "_Console/MegaCD",
        {".chd": (1, "s", 0), ".cue": (1, "s", 0)}),
    ("Saturn",        "Saturn",  ["Saturn"],               "_Console/Saturn",
        {".chd": (1, "s", 0), ".cue": (1, "s", 0)}),
    ("Neo Geo",       "NEOGEO",  ["NEOGEO"],               "_Console/NeoGeo",
        {".neo": (1, "f", 1)}),
    # SMW Hacks (Nutzerwunsch): eigenes System im Hauptmenue, LAEUFT
    # ABER mit dem ganz normalen SNES-Core (rbf-Pfad identisch zu
    # "SNES" oben) - eigener Systemschluessel nur fuer eigene
    # Akzentfarbe/eigenes Sysart (siehe SYSTEM_ACCENT), NICHT weil ein
    # eigener Core noetig waere. ROMs liegen unter games/SNES/SMW_HACKS
    # (wird per claimed_subfolders aus der regulaeren SNES-Kategorie
    # ausgeschlossen, siehe _scan_games_disk() - sonst Doppel-Anzeige).
    ("SMW Hacks",     "SMW_HACKS", ["SNES/SMW_HACKS"],      "_Console/SNES",
        {".sfc": (2, "f", 0), ".smc": (2, "f", 0)}),
]

# OPTIONALE Systeme (Nutzerwunsch): wie GAME_SYSTEMS oben, aber
# zusaetzlich mit einer echten Core-Datei-Praesenzpruefung
# (core_check_path) - erscheinen NUR, wenn diese exakte Datei
# tatsaechlich auf der SD-Karte liegt, sonst komplett unsichtbar
# (nicht einmal ein leerer/deaktivierter Eintrag). Anders als die
# Standardsysteme oben, deren offizielle Cores praktisch immer
# vorhanden sind und deshalb nie geprueft wurden - hier handelt es
# sich um einen einzelnen, von Hand installierten Custom-Core
# (kein versionierter, datumsgestempelter Ordner wie bei den
# offiziellen Cores, sondern eine einzelne feste Datei direkt in
# _Console - vom Nutzer bestaetigt: "SNES_Tracker.rbf", Ordner
# "_Console").
#
# Feld-Reihenfolge identisch zu GAME_SYSTEMS (Anzeigename, Systemschluessel,
# ROM-Unterordner-Liste relativ zu GAMES_BASES, rbf-Pfad OHNE Endung fuer
# die .mgl-Datei, Dateiendungen-Map), plus fuenftes Feld core_check_path
# (absoluter Pfad zur tatsaechlichen .rbf-Datei fuer die Praesenzpruefung).
OPTIONAL_GAME_SYSTEMS = [
    ("SNES ALTTP Tracker", "SNES_ALTTP_TRACKER", ["SNES/ZELDA_MSU"],
        "_Console/SNES_Tracker",
        {".sfc": (2, "f", 0), ".smc": (2, "f", 0)},
        "/media/fat/_Console/SNES_Tracker.rbf"),
]

def system_display_name(syskey):
    """Anzeigename zu einem Systemschluessel (z.B. "Genesis" ->
    "Mega Drive") - fuer Stellen, die einen menschenlesbaren Namen
    statt des internen Schluessels brauchen (siehe Trophaeenraum).
    Prueft auch OPTIONAL_GAME_SYSTEMS mit."""
    for disp, sk, *_ in GAME_SYSTEMS:
        if sk == syskey:
            return disp
    for disp, sk, *_ in OPTIONAL_GAME_SYSTEMS:
        if sk == syskey:
            return disp
    return syskey or "?"
