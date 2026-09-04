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
    # ==================================================================
    # ERWEITERUNG (Build 79, Nutzerwunsch: "eigentlich sollten alle
    # runtergeladen werden, wenn die Cores und die passenden ROMs im
    # Frontend mit verfuegbar sind ... falls jemand mal auf die Idee
    # kommt, dass er auf einmal Atari oder Jaguar oder 3DO mit nutzen
    # will. Quasi: falls vorhanden, dann auch mit bereitstellen.")
    #
    # Alle uebrigen Konsolen-Systeme der MiSTer-Distribution. Sie stehen
    # bewusst HIER bei den optionalen: jeder Eintrag erscheint nur, wenn
    # die Core-Datei WIRKLICH auf der Karte liegt UND ROMs dazu da sind.
    # Wer die Cores nicht hat, merkt von dieser Liste nichts.
    #
    # HERKUNFT DER STARTPARAMETER - und warum ich ihnen traue:
    # allesamt aus der mrext-Systemdatenbank (wizzomafizzo), derselben
    # Quelle wie die 13 Systeme oben. Zur Kontrolle habe ich die dort
    # hinterlegten Werte fuer unsere BESTEHENDEN Systeme abgerufen und
    # verglichen - NES (2,f,1), SNES (2,f,0), Mega Drive (1,f,1), PSX
    # (1,s,1), Master System (1,f,1), Game Gear (1,f,2), TurboGrafx
    # (1,f,0), SuperGrafx (1,f,1), MegaCD/Saturn (1,s,0), Neo Geo
    # (1,f,1): ALLE stimmen exakt mit unseren seit Langem
    # funktionierenden Werten ueberein. Die Quelle ist damit an 13
    # Punkten belegt, nicht angenommen.
    #
    # EHRLICH DAZU: geraten ist hier nichts, GETESTET aber auch nichts -
    # ich habe keinen MiSTer. Ob ein Core tatsaechlich startet und das
    # ROM laedt, zeigt erst der Einsatz. Sollte eines nicht laufen,
    # liegt der Fehler mit hoher Wahrscheinlichkeit in genau einer
    # Zahl (meist dem Index), und die steht hier direkt daneben.
    #
    # Reihenfolge: alphabetisch nach Anzeigename, damit die Liste bei
    # 30 Eintraegen ueberhaupt pflegbar bleibt.
    # ==================================================================

    ("3DO",             "3DO",          ["3DO"],            "_Console/3DO",
        {".cue": (1, "s", 1), ".chd": (1, "s", 1)},
        "/media/fat/_Console/3DO*.rbf"),
    ("Adventure Vision", "ADVENTUREVISION", ["AVision"],    "_Console/AdventureVision",
        {".bin": (1, "f", 1)},
        "/media/fat/_Console/AdventureVision*.rbf"),
    ("Arcadia 2001",    "ARCADIA",      ["Arcadia"],        "_Console/Arcadia",
        {".bin": (1, "f", 1)},
        "/media/fat/_Console/Arcadia*.rbf"),
    ("Astrocade",       "ASTROCADE",    ["Astrocade"],      "_Console/Astrocade",
        {".bin": (1, "f", 1)},
        "/media/fat/_Console/Astrocade*.rbf"),
    # Atari 2600 laeuft ueber den Atari7800-Core (kein eigener Core) -
    # deshalb derselbe rbf-Pfad und dieselbe Core-Pruefung wie beim 7800.
    # Die Endungen trennen die beiden sauber: .a26 hier, .a78/.bin dort.
    ("Atari 2600",      "ATARI2600",    ["Atari2600", "ATARI7800"], "_Console/Atari7800",
        {".a26": (1, "f", 1)},
        "/media/fat/_Console/Atari7800*.rbf"),
    ("Atari 5200",      "ATARI5200",    ["ATARI5200"],      "_Console/Atari5200",
        {".car": (1, "s", 1), ".a52": (1, "s", 1), ".bin": (1, "s", 1),
         ".rom": (1, "s", 1)},
        "/media/fat/_Console/Atari5200*.rbf"),
    ("Atari 7800",      "ATARI7800",    ["ATARI7800"],      "_Console/Atari7800",
        {".a78": (1, "f", 1), ".bin": (1, "f", 1)},
        "/media/fat/_Console/Atari7800*.rbf"),
    ("Atari Lynx",      "ATARILYNX",    ["AtariLynx"],      "_Console/AtariLynx",
        {".lnx": (1, "f", 1)},
        "/media/fat/_Console/AtariLynx*.rbf"),
    ("CD-i",            "CDI",          ["CD-i"],           "_Console/CDi",
        {".cue": (1, "s", 1), ".chd": (1, "s", 1)},
        "/media/fat/_Console/CDi*.rbf"),
    ("Casio PV-1000",   "CASIOPV1000",  ["Casio_PV-1000"],  "_Console/Casio_PV-1000",
        {".bin": (1, "f", 1)},
        "/media/fat/_Console/Casio_PV-1000*.rbf"),
    ("Channel F",       "CHANNELF",     ["ChannelF"],       "_Console/ChannelF",
        {".rom": (1, "f", 1), ".bin": (1, "f", 1)},
        "/media/fat/_Console/ChannelF*.rbf"),
    ("ColecoVision",    "COLECOVISION", ["Coleco"],         "_Console/ColecoVision",
        {".col": (1, "f", 1), ".bin": (1, "f", 1), ".rom": (1, "f", 1)},
        "/media/fat/_Console/ColecoVision*.rbf"),
    # Der BASIC-Steckplatz (.bas) hat einen ANDEREN Index (3) als die
    # Spielmodule - laut mrext ein eigener Slot desselben Cores.
    ("CreatiVision",    "CREATIVISION", ["CreatiVision"],   "_Console/CreatiVision",
        {".rom": (1, "f", 1), ".bin": (1, "f", 1), ".bas": (1, "f", 3)},
        "/media/fat/_Console/CreatiVision*.rbf"),
    # Famicom Disk System laeuft ueber den NES-Core. Ordner NES ist
    # bewusst mit drin (dort liegen .fds-Dateien haeufig) - eine
    # Doppelanzeige kann nicht entstehen, weil die NES-Kategorie
    # ausschliesslich .nes einliest.
    ("Famicom Disk System", "FDS",      ["FDS", "NES"],     "_Console/NES",
        {".fds": (2, "f", 1)},
        "/media/fat/_Console/NES*.rbf"),
    # Eigene Kategorie NUR fuer den Ordner games/GameGear. Game-Gear-
    # Dateien, die in games/SMS liegen, erscheinen wie bisher unter
    # "Master System" (die Kategorie liest .gg dort seit jeher mit) -
    # sonst waere das eine sichtbare Verhaltensaenderung fuer alle, die
    # ihre Sammlung so sortiert haben.
    ("Game Gear",       "GAMEGEAR",     ["GameGear"],       "_Console/SMS",
        {".gg": (1, "f", 2)},
        "/media/fat/_Console/SMS*.rbf"),
    ("Game & Watch",    "GAMENWATCH",   ["GameNWatch"],     "_Console/GnW",
        {".bin": (1, "f", 1)},
        "/media/fat/_Console/GnW*.rbf"),
    ("Gamate",          "GAMATE",       ["Gamate"],         "_Console/Gamate",
        {".bin": (1, "f", 1)},
        "/media/fat/_Console/Gamate*.rbf"),
    ("Intellivision",   "INTELLIVISION", ["Intellivision"], "_Console/Intellivision",
        {".int": (1, "f", 1), ".bin": (1, "f", 1)},
        "/media/fat/_Console/Intellivision*.rbf"),
    ("Jaguar",          "JAGUAR",       ["Jaguar"],         "_Console/Jaguar",
        {".jag": (1, "s", 1), ".j64": (1, "s", 1), ".rom": (1, "s", 1),
         ".bin": (1, "s", 1)},
        "/media/fat/_Console/Jaguar*.rbf"),
    # Bewusst NUR der eigene Ordner: mrext listet zusaetzlich GAMEBOY,
    # aber dort liegende .bin-Dateien sind fast nie Mega-Duck-Spiele -
    # die wuerden sonst als fremde Eintraege in dieser Kategorie
    # auftauchen.
    ("Mega Duck",       "MEGADUCK",     ["MegaDuck"],       "_Console/Gameboy",
        {".bin": (2, "f", 1)},
        "/media/fat/_Console/Gameboy*.rbf"),
    ("Neo Geo CD",      "NEOGEOCD",     ["NeoGeo-CD"],      "_Console/NeoGeo",
        {".cue": (1, "s", 1), ".chd": (1, "s", 1)},
        "/media/fat/_Console/NeoGeo*.rbf"),
    ("Odyssey 2",       "ODYSSEY2",     ["ODYSSEY2"],       "_Console/Odyssey2",
        {".bin": (1, "f", 1)},
        "/media/fat/_Console/Odyssey2*.rbf"),
    # Gleiche Ueberlegung wie bei Mega Duck - nur der eigene Ordner.
    ("Pocket Challenge V2", "POCKETCHALLENGEV2", ["PocketChallengeV2"],
        "_Console/WonderSwan",
        {".pc2": (1, "f", 1)},
        "/media/fat/_Console/WonderSwan*.rbf"),
    ("Pokemon Mini",    "POKEMONMINI",  ["PokemonMini"],    "_Console/PokemonMini",
        {".min": (1, "f", 1)},
        "/media/fat/_Console/PokemonMini*.rbf"),
    ("SG-1000",         "SG1000",       ["SG1000", "Coleco", "SMS"], "_Console/ColecoVision",
        {".sg": (1, "f", 0)},
        "/media/fat/_Console/ColecoVision*.rbf"),
    ("Sega 32X",        "S32X",         ["S32X"],           "_Console/S32X",
        {".32x": (1, "f", 1)},
        "/media/fat/_Console/S32X*.rbf"),
    ("Super Game Boy",  "SUPERGAMEBOY", ["SGB"],            "_Console/SGB",
        {".gb": (1, "f", 1), ".gbc": (1, "f", 1)},
        "/media/fat/_Console/SGB*.rbf"),
    ("TurboGrafx16 CD", "TGFX16CD",     ["TGFX16-CD"],      "_Console/TurboGrafx16",
        {".cue": (1, "s", 0), ".chd": (1, "s", 0)},
        "/media/fat/_Console/TurboGrafx16*.rbf"),
    ("VC 4000",         "VC4000",       ["VC4000"],         "_Console/VC4000",
        {".bin": (1, "f", 1)},
        "/media/fat/_Console/VC4000*.rbf"),
    ("Vectrex",         "VECTREX",      ["VECTREX"],        "_Console/Vectrex",
        {".vec": (1, "f", 1), ".bin": (1, "f", 1), ".rom": (1, "f", 1)},
        "/media/fat/_Console/Vectrex*.rbf"),
    ("WonderSwan",      "WONDERSWAN",   ["WonderSwan"],     "_Console/WonderSwan",
        {".ws": (1, "f", 1)},
        "/media/fat/_Console/WonderSwan*.rbf"),
    ("WonderSwan Color", "WONDERSWANCOLOR", ["WonderSwanColor", "WonderSwan"],
        "_Console/WonderSwan",
        {".wsc": (1, "f", 1)},
        "/media/fat/_Console/WonderSwan*.rbf"),
]



# ---------------------------------------------------------------------------
# NAMEN DER LIBRETRO-DATENBANK je System
# ---------------------------------------------------------------------------
# NEU (Build 79). Vorher stand diese Zuordnung DREIMAL getrennt:
# in frontend/mister_boxart.py, frontend/mister_gameinfo.py und
# PC-Tools/boxart_fetch.py. Genau daran ist Virtual Boy gescheitert -
# das System kam ins Frontend, die drei Tabellen wurden uebersehen, und
# der Boxart-Download liess es stillschweigend aus (kein Fehler, nur
# keine Cover). Ab jetzt ist DAS HIER die einzige Quelle; die beiden
# Werkzeuge auf dem MiSTer lesen direkt von hier.
#
# PC-Tools/boxart_fetch.py behaelt bewusst eine eigene Kopie: es wird
# einzeln auf einen Windows-PC kopiert und kann nichts aus fe/
# importieren. Dass die Kopie nicht abdriftet, sichert
# tools/test_system_abdeckung.py ab.
#
# Die Namen sind ABGERUFEN, nicht angenommen: jeder hier eingetragene
# Name existiert als Verzeichnis unter thumbnails.libretro.com bzw. als
# .dat unter libretro-database/metadat.
#
# Systeme, die BEWUSST fehlen, weil es dort schlicht keine Datenbank
# gibt (ebenfalls geprueft, nicht vermutet): Astrocade, Gamate,
# Game & Watch, Mega Duck, Pocket Challenge V2, VC 4000 - sowie
# SMW Hacks und der ALTTP-Tracker, fuer die es naturgemaess keine
# offizielle Datenbank geben kann. Fuer diese Systeme laedt das
# Frontend keine Cover; eigene .art-Dateien lassen sich wie immer von
# Hand ablegen.
LIBRETRO_DB = {
    "NES":          "Nintendo - Nintendo Entertainment System",
    "SNES":         "Nintendo - Super Nintendo Entertainment System",
    "Genesis":      "Sega - Mega Drive - Genesis",
    "N64":          "Nintendo - Nintendo 64",
    "PSX":          "Sony - PlayStation",
    "GAMEBOY":      "Nintendo - Game Boy",
    "GBC":          "Nintendo - Game Boy Color",
    "GBA":          "Nintendo - Game Boy Advance",
    "SMS":          "Sega - Master System - Mark III",
    "TGFX16":       "NEC - PC Engine - TurboGrafx 16",
    "MegaCD":       "Sega - Mega-CD - Sega CD",
    "Saturn":       "Sega - Saturn",
    "NEOGEO":       "SNK - Neo Geo",
    "VIRTUALBOY":   "Nintendo - Virtual Boy",
    "3DO":              "The 3DO Company - 3DO",
    "ADVENTUREVISION":  "Entex - Adventure Vision",
    "ARCADIA":          "Emerson - Arcadia 2001",
    "ATARI2600":        "Atari - 2600",
    "ATARI5200":        "Atari - 5200",
    "ATARI7800":        "Atari - 7800",
    "ATARILYNX":        "Atari - Lynx",
    "CASIOPV1000":      "Casio - PV-1000",
    "CDI":              "Philips - CD-i",
    "CHANNELF":         "Fairchild - Channel F",
    "COLECOVISION":     "Coleco - ColecoVision",
    "CREATIVISION":     "VTech - CreatiVision",
    "FDS":              "Nintendo - Family Computer Disk System",
    "GAMEGEAR":         "Sega - Game Gear",
    "INTELLIVISION":    "Mattel - Intellivision",
    "JAGUAR":           "Atari - Jaguar",
    "NEOGEOCD":         "SNK - Neo Geo CD",
    "ODYSSEY2":         "Magnavox - Odyssey2",
    "POKEMONMINI":      "Nintendo - Pokemon Mini",
    "S32X":             "Sega - 32X",
    "SG1000":           "Sega - SG-1000",
    # Super Game Boy spielt ganz normale Game-Boy-ROMs (.gb/.gbc) - eine
    # eigene Datenbank gibt es dafuer nicht, die Game-Boy-Datenbank passt
    # aber inhaltlich exakt. Bewusst zugeordnet statt leer zu lassen.
    "SUPERGAMEBOY":     "Nintendo - Game Boy",
    "TGFX16CD":         "NEC - PC Engine CD - TurboGrafx-CD",
    "VECTREX":          "GCE - Vectrex",
    "WONDERSWAN":       "Bandai - WonderSwan",
    "WONDERSWANCOLOR":  "Bandai - WonderSwan Color",
}


def alle_systeme():
    """Alle Spielesysteme als (Anzeigename, Systemschluessel, Ordner,
    rbf, Endungen-Map) - Standard- UND optionale zusammen.

    Fuer die Download-Werkzeuge (Boxart, Spiele-Infos), die nicht
    zwischen beiden unterscheiden muessen: was das Frontend anzeigen
    kann, soll auch bedient werden."""
    return ([tuple(e[:5]) for e in GAME_SYSTEMS]
            + [tuple(e[:5]) for e in OPTIONAL_GAME_SYSTEMS])


# Ausnahmen: EINE Endung eines Systems gehoert in eine ANDERE
# Datenbank als der Rest.
#
# Der Master-System-Core spielt auch Game-Gear-Module (.gg), und deren
# Cover liegen bei libretro unter einem eigenen Namen. Das war in den
# alten, handgepflegten Tabellen bereits so eingetragen - ohne diese
# Ausnahme wuerden Game-Gear-Spiele, die im Ordner games/SMS liegen,
# ploetzlich in der Master-System-Datenbank gesucht und nicht mehr
# gefunden. Genau so eine stille Verschlechterung soll der Umbau auf
# eine einzige Quelle NICHT einfuehren; tools/test_system_abdeckung.py
# vergleicht das Ergebnis deshalb mit der alten Zuordnung.
LIBRETRO_DB_ENDUNG = {
    ("SMS", ".gg"): "Sega - Game Gear",
}


def download_systeme():
    """{Systemschluessel: (Ordnerliste, {Endung: Datenbankname})} fuer
    die Boxart-/Gameinfo-Werkzeuge - nur Systeme MIT Datenbank."""
    raus = {}
    for _disp, syskey, folders, _rbf, extmap in alle_systeme():
        db = LIBRETRO_DB.get(syskey)
        zuordnung = {}
        for ext in extmap:
            name = LIBRETRO_DB_ENDUNG.get((syskey, ext), db)
            if name:
                zuordnung[ext] = name
        if not zuordnung:
            continue
        raus[syskey] = (list(folders), zuordnung)
    return raus


def optional_core_file(pattern):
    """Tatsaechlich vorhandene Core-Datei zu einem core_check_path.

    KOSTEN, nachgemessen statt vermutet (Build 79, als die Liste von 2
    auf 34 optionale Systeme wuchs): 34 Muster kosten zusammen rund
    2 ms, und pro Start laufen zwei Durchgaenge (Signatur + Scan). Ein
    Zwischenspeicher waere also Aufwand ohne Gegenwert - und haette den
    Preis, dass ein frisch installierter Core erst verzoegert auffaellt.
    Bewusst nicht eingebaut.

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
