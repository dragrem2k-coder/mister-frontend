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
import glob
import os

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
#
# ERWEITERUNG (Nutzerwunsch Virtual Boy): core_check_path darf jetzt auch
# ein MUSTER mit Platzhalter sein (siehe optional_core_file() unten). Fuer
# von Hand installierte Einzel-Cores wie den SNES_Tracker bleibt der feste
# Pfad richtig; offizielle Cores dagegen liegen mit Datumsstempel im
# Dateinamen auf der Karte ("VirtualBoy_20240115.rbf"), der sich bei jedem
# Update aendert - ein fester Pfad wuerde dort nach dem naechsten
# Core-Update nicht mehr passen und die Kategorie waere ploetzlich weg.
OPTIONAL_GAME_SYSTEMS = [
    ("SNES ALTTP Tracker", "SNES_ALTTP_TRACKER", ["SNES/ZELDA_MSU"],
        "_Console/SNES_Tracker",
        {".sfc": (2, "f", 0), ".smc": (2, "f", 0)},
        "/media/fat/_Console/SNES_Tracker.rbf"),
    # NEUES SYSTEM (Nutzerwunsch: "wenn der Core verfuegbar ist und ROMs
    # dazu vorhanden sind, wie die anderen Kategorien auf der Hauptseite
    # hinzufuegen"). Bewusst als OPTIONALES System: der Virtual-Boy-Core
    # gehoert nicht zur Standardausstattung eines MiSTers, er muss ueber
    # den Downloader nachinstalliert werden. Ohne Core (oder ohne ROMs im
    # Ordner games/VirtualBoy) taucht die Kategorie gar nicht erst auf.
    #
    # MGL-Parameter (delay 1, Typ "f", Index 1) und Endung ".vb" stammen
    # aus derselben gepflegten Systemdatenbank, aus der auch die uebrigen
    # Systeme hier kommen (Zaparoo, Nachfolger von mrext) - dort gegen die
    # bekannten Werte der bereits laufenden Systeme abgeglichen: SNES
    # (2/f/0), NES (2/f/1), Game Boy (2/f/1) und Mega Drive (1/f/1)
    # stimmen dort exakt mit unseren seit Langem funktionierenden Werten
    # ueberein, die Quelle ist fuer Virtual Boy also belastbar. Passt zur
    # Core-Beschreibung selbst ("FS1,VB ,Load ROM;" in VirtualBoy.sv).
    ("Virtual Boy",       "VIRTUALBOY",        ["VirtualBoy"],
        "_Console/VirtualBoy",
        {".vb": (1, "f", 1)},
        "/media/fat/_Console/VirtualBoy*.rbf"),
]


def optional_core_file(pattern):
    """Tatsaechlich vorhandene Core-Datei zu einem core_check_path.

    Der Eintrag darf ein fester Pfad ODER ein Muster mit Platzhalter
    sein. Grund fuer den Platzhalter: offizielle MiSTer-Cores tragen den
    Build-Stempel im Dateinamen ("VirtualBoy_20240115.rbf") und heissen
    nach jedem Core-Update anders. Ein fester Pfad wuerde nur zufaellig
    genau einmal passen.

    Rueckgabe: der Pfad der gefundenen Datei (bei mehreren Treffern der
    alphabetisch letzte - das ist bei Datumsstempeln automatisch der
    neueste), sonst None.
    """
    if "*" not in pattern and "?" not in pattern and "[" not in pattern:
        return pattern if os.path.isfile(pattern) else None
    treffer = sorted(p for p in glob.glob(pattern) if os.path.isfile(p))
    return treffer[-1] if treffer else None

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
