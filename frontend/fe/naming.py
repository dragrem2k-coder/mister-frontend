#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Namens-/Anzeige-Hilfsfunktionen fuer den Scan: Klammer-Tags entfernen
(display_name), Regions-/Dedupe-Schluessel (region_rank/canonical_key),
Junk-/Japan-only-/Boot-Datei-Erkennung, freundliche Ordnernamen.
Ausgelagert aus frontend.py (Modularisierung, Git-Branch
'modular-refactor').

Zwei ehemals GETRENNTE Bloecke aus dem Original zusammengefuehrt
(NICE_NAMES lag deutlich frueher im Code als der Rest) - gehoeren
inhaltlich klar zusammen (reine String-/Namens-Verarbeitung, keine
Dateisystem-Zugriffe).
"""
import re

# Freundliche Anzeigenamen fuer bekannte Ordner
NICE_NAMES = {
    "Arcade": "Arcade", "Console": "Consoles", "Computer": "Computer",
    "Other": "Other", "Utility": "Utilities", "RA_Cores": "RA Cores",
}

_TAGS = re.compile(r"\s*[\(\[][^\)\]]*[\)\]]")

# Datentraeger-Marker (Disc 1/2, CD 2, Side B, Part 3 ...). Diese Klammer-
# Zusaetze duerfen NICHT wie Regions-Tags behandelt werden: sie
# unterscheiden echte, eigenstaendige Eintraege desselben Spiels. Ohne
# diese Ausnahme faenden "Spiel (Disc 1)" und "Spiel (Disc 2)" auf
# demselben Dedupe-Schluessel zusammen - Disc 2+ waere aus der Liste
# verschwunden und nicht mehr startbar.
_DISC = re.compile(r"[\(\[]\s*(?:disc|disk|cd|side|part|tape|track)\s*"
                   r"[0-9a-z]+\s*[\)\]]", re.I)

def display_name(full):
    """Klammer-Zusaetze fuer die Anzeige entfernen - Disc-/CD-Marker
    bleiben aber stehen, sonst waeren mehrteilige Spiele in der Liste
    nicht auseinanderzuhalten."""
    short = _TAGS.sub("", full).strip()
    m = _DISC.search(full)
    if m and short:
        short += " " + m.group(0).strip()
    return short if short else full

# Region-Prioritaet fuer die Dedupe-Logik beim Scannen - dieselbe
# Reihenfolge wie in mister_boxart.py/mister_gameinfo.py bei der
# Boxart-/Info-Zuordnung, damit alles konsistent dieselbe Region
# bevorzugt.
REGION_PRIORITY = ["(germany)", "(europe)", "(world)", "(usa)", "(japan)"]

def _region_rank(name):
    low = name.lower()
    for i, tag in enumerate(REGION_PRIORITY):
        if tag in low:
            return i
    return len(REGION_PRIORITY)

def _canonical_key(name):
    """Name ohne Klammer-Zusaetze, kleingeschrieben - fuer die Erkennung
    von Mehrfach-Regionen desselben Spiels ("Spiel (USA)" und
    "Spiel (Europe)" landen auf demselben Schluessel).

    Ausnahme: ein Disc-/CD-/Side-Marker bleibt Teil des Schluessels,
    damit mehrteilige Spiele (Disc 1/2/3) NICHT zusammengefasst und
    dadurch unerreichbar werden."""
    key = _TAGS.sub("", name).strip().lower()
    m = _DISC.search(name)
    if m:
        key += " " + re.sub(r"\s+", "", m.group(0).lower())
    return key

# Tags, die ein ROM als Beta/Prototyp/Demo/defekten Dump o.ae.
# kennzeichnen - werden beim Scannen ausgefiltert.
JUNK_TAGS = ("(beta", "(proto", "(demo", "(sample", "[b]",
            "(program", "(test", "(kiosk")
# BUGFIX/AENDERUNG (Nutzerwunsch: "Was ist mit ROM Hacks und Zelda
# Randomizer" - Spielhacks und Randomizer-Ausgaben wurden bisher
# GAR NICHT angezeigt): "(hack" stand bisher in dieser Liste und
# wurde damit komplett ausgefiltert, genau wie unfertige Beta-/Proto-
# Dumps. Anders als diese sind Hacks (und Randomizer-Ausgaben, die
# haeufig aehnlich getaggt werden) aber vollstaendige, spielbare
# Inhalte, die viele Nutzer bewusst suchen - keine unfertigen/
# kaputten Dumps. Deshalb aus der Ausschlussliste entfernt.
#
# BUGFIX Runde 2 (Nutzer-Rueckmeldung anhand eines echten Datei-
# Screenshots: "NES-Ordner zeigt nur 2 ROMs an, sind aber viel mehr"):
# "(unl)" und "(pirate" standen ebenfalls noch in dieser Liste - die
# Screenshot-Dateiliste zeigte, dass ein GROSSER TEIL einer typischen
# NES-Sammlung aus genau diesen Tags besteht (unzaehlige beliebte,
# VOLLSTAENDIGE Mehrfach-Cartridges/unlizenzierte Spiele, gerade im
# asiatischen Raum sehr verbreitet und kommerziell verkauft) - wurden
# bisher komplett wie kaputte Dumps behandelt und ausgeblendet, obwohl
# es sich um voll spielbare, oft gesuchte Inhalte handelt. Aus der
# Ausschlussliste entfernt, gleiche Begruendung wie bei "(hack" oben.
# "[b]" (explizit als fehlerhafter Dump markiert) bleibt bewusst
# bestehen - das ist ein echter Qualitaetsmangel, kein blosser
# Lizenzstatus.

def _is_junk(name):
    low = name.lower()
    return any(tag in low for tag in JUNK_TAGS)

# Rein japanische ROMs ausblenden (auf Wunsch - EU/USA reicht den
# meisten). Erkennt "(Japan)"/"[Japan]" und die abgekuerzte Variante
# "(J)" aus aelteren ROM-Sets. WICHTIG: Mehrfach-Region-Tags wie
# "(Japan, USA)" oder "(USA, Japan)" bleiben erhalten, da diese Version
# auch USA/Europa abdeckt - das Muster verlangt eine direkt schliessende
# Klammer OHNE weiteren Text/Komma dazwischen.
_JAPAN_ONLY = re.compile(r"[\(\[]\s*(?:japan|j)\s*[\)\]]", re.I)

def _is_japan_only(name):
    return bool(_JAPAN_ONLY.search(name))

# Bekannte Boot-/Test-/Demo-Dateien, die manche MiSTer-Verteilungen
# direkt in die ROM-Ordner legen (fuer den Hardware-Selbsttest). Haben
# zufaellig die richtige Endung (z.B. .chd/.gb/.gba) und wuerden sonst
# faelschlich als "Spiel" in der Liste auftauchen.
IGNORE_ROM_BASENAMES = {"boot", "boot1", "boot2", "mister-boot", "mister-demo"}

def nice_name(dirname):
    raw = dirname.lstrip("_")
    return NICE_NAMES.get(raw, raw.replace("_", " "))
