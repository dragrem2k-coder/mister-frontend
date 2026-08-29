#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RA-Core-Erkennung (sage2050s "MiSTer_RetroAchievements"-Werkzeug -
legt RA-faehige Core-Varianten in einen separaten Ordner an).
Ausgelagert aus frontend.py (Modularisierung, Git-Branch
'modular-refactor').

Komplett eigenstaendig - nur os aus der Standardbibliothek, keine
Abhaengigkeiten zu anderem Code (reine Daten + eine kleine
Nachschlage-Funktion).
"""
import os

# ----------------------------------------------------------------------------
# RA-CORE-ERKENNUNG (sage2050s "MiSTer_RetroAchievements"-Werkzeug -
# legt RA-faehige Core-Varianten in einen separaten Ordner, getrennt
# von den Standard-Cores)
#
# EHRLICHER HINWEIS: die exakte Dateibenennung dieses Werkzeugs wurde
# inzwischen per echter Nutzer-Installation verifiziert (siehe die
# .mgl-Struktur unten bei write_mgl()/setname). Fuer Systeme ohne
# bestaetigte Namensliste werden trotzdem mehrere plausible Varianten
# durchprobiert - der erste tatsaechlich EXISTIERENDE Treffer gewinnt,
# findet sich keiner, wird fuer dieses System einfach KEINE Auswahl
# angezeigt (nie ein nicht-existierender Pfad referenziert). Arcade
# ist bei diesem RA-Core-Set nicht enthalten - taucht deshalb hier
# bewusst nicht auf.
RA_CORES_DIR_ABS = "/media/fat/_RA_Cores/Cores"
RA_CORES_DIR_REL = "_RA_Cores/Cores"

RA_CORE_NAME_CANDIDATES = {
    "NES":     ["NES"],
    "SNES":    ["SNES"],
    "Genesis": ["Genesis", "MegaDrive"],
    # NEU (Nutzerwunsch: "N64_ALSA.rbf"/"PSX_ALSA.rbf" bevorzugt starten,
    # wenn im _RA_Cores-Ordner vorhanden - sonst ganz normal auf den
    # bisherigen RA-Core zurueckfallen): die ALSA-Variante steht jeweils
    # VOR dem bisherigen Namen in der Liste - find_ra_core() unten nimmt
    # ja ohnehin schon "die erste tatsaechlich EXISTIERENDE Datei" (siehe
    # Docstring), das genuegt hier also bereits vollstaendig, ohne
    # find_ra_core() selbst aendern zu muessen. Ist NUR die normale
    # N64.rbf/PSX.rbf vorhanden (keine ALSA-Datei), aendert sich nichts
    # am bisherigen Verhalten - der zweite Listeneintrag greift dann wie
    # gehabt.
    "N64":     ["N64_ALSA", "N64"],
    "PSX":     ["PSX_ALSA", "PSX", "PlayStation"],
    "GAMEBOY": ["Gameboy", "GAMEBOY", "GB"],
    "GBC":     ["Gameboy", "GAMEBOY", "GBC"],
    "GBA":     ["GBA"],
    "SMS":     ["SMS", "MasterSystem"],
    "TGFX16":  ["TGFX16", "TurboGrafx16"],
    "MegaCD":  ["MegaCD", "SegaCD"],
    "NEOGEO":  ["NeoGeo", "NEOGEO"],
    "Saturn":  ["Saturn"],
    "SMW_HACKS": ["SNES"],   # laeuft mit dem normalen SNES-(RA-)Core, siehe GAME_SYSTEMS-Kommentar
}

def find_ra_core(syskey):
    """Sucht die RA-faehige Core-Datei fuer ein System. Liefert
    (mgl_rbf_pfad, setname) bei einem tatsaechlichen Treffer, sonst
    None. setname entspricht exakt dem Format, das sage2050s eigene
    .mgl-Dateien verwenden (per echter Nutzer-Installation
    verifiziert: <rbf>_RA_Cores/Cores/NES</rbf> +
    <setname same_dir="1">RA_NES</setname>) - ohne dieses Element
    wird der RA-Core von MiSTer offenbar nicht korrekt als eigene,
    von der Standard-Konfiguration getrennte Core-Variante behandelt."""
    for name in RA_CORE_NAME_CANDIDATES.get(syskey, []):
        if os.path.exists(os.path.join(RA_CORES_DIR_ABS, name + ".rbf")):
            return (RA_CORES_DIR_REL + "/" + name, "RA_" + name)
    return None
