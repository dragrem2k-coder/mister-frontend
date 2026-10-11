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

# NEUES FEATURE (Nutzerwunsch: "es muesste noch fluessiger laufen" -
# gezielte Suche nach unnoetiger Doppelarbeit, inspiriert von Zaparoos
# Performance-Ansatz): display_name() ist eine REINE Funktion (gleicher
# Dateiname -> immer dasselbe Ergebnis, keine Seiteneffekte) - wurde
# bislang aber bei JEDEM Neuzeichnen einer Listenzeile neu berechnet
# (zwei Regex-Operationen), obwohl sich derselbe Dateiname zwischen
# zwei Scrollschritten typischerweise gar nicht aendert. Bei einer
# sichtbaren Liste von z.B. 8-10 Zeilen bleiben beim Scrollen um einen
# Schritt meist 7-9 davon unveraendert sichtbar - wurden bisher trotzdem
# jedes Mal neu durch beide Regexe geschickt. Einfacher Dict-Cache statt
# functools.lru_cache (bleibt im Stil des restlichen Projekts, kein
# zusaetzlicher Import) - Eingaberaum ist ohnehin begrenzt (nur echte
# Dateinamen der gescannten Sammlung, keine unbegrenzte/gegnerische
# Eingabe), daher bewusst OHNE Groessenlimit/Verdraengung.
_DISPLAY_NAME_CACHE = {}

def display_name(full):
    """Klammer-Zusaetze fuer die Anzeige entfernen - Disc-/CD-Marker
    bleiben aber stehen, sonst waeren mehrteilige Spiele in der Liste
    nicht auseinanderzuhalten."""
    if full in _DISPLAY_NAME_CACHE:
        return _DISPLAY_NAME_CACHE[full]
    short = _TAGS.sub("", full).strip()
    m = _DISC.search(full)
    if m and short:
        short += " " + m.group(0).strip()
    result = short if short else full
    _DISPLAY_NAME_CACHE[full] = result
    return result

# Region-Prioritaet fuer die Dedupe-Logik beim Scannen - dieselbe
# Reihenfolge wie in mister_boxart.py/mister_gameinfo.py bei der
# Boxart-/Info-Zuordnung, damit alles konsistent dieselbe Region
# bevorzugt.
# BUGFIX (Nutzer-Rueckmeldung: "Scrollen im HDMI-Modus fuehlt sich
# schlecht an" - bei der Fehlersuche in mister_boxart.py gefunden und
# hier konsistent mitkorrigiert, siehe dortige ausfuehrliche
# Begruendung): Germany/Europe/World standen bisher VOR USA - bei
# einer ueberwiegend USA-getaggten Sammlung mit doppelten Regions-
# ROMs desselben Spiels waere hier faelschlich die europaeische
# Variante als "die eine" angezeigte Version bevorzugt worden. USA/
# World jetzt vorne, deckt den weitaus haeufigeren Sammlungstyp ab.
REGION_PRIORITY = ["(usa)", "(world)", "(europe)", "(japan)", "(germany)"]

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

# BUGFIX, Runde 2 (Nutzer-Rueckmeldung ueber Bekannte - erst
# "Tetris (Japan) (En).gb", dann diese hier:
#
#     Seiken Densetsu 3 (Japan) (German).sfc
#     Magic Knight Rayearth (J) [T+Ger].sfc
#
# "Das sind wieder so Sonderlocken, das muesste nochmal erweitert
# werden.")
#
# Die erste Runde erkannte nur zweibuchstabige Sprachcodes und nur
# Englisch. Damit fielen zwei sehr verbreitete Schreibweisen durch:
#
#  * AUSGESCHRIEBENE Sprachnamen - "(German)", "(English)", "(Spanish)".
#  * UEBERSETZUNGS-Kennzeichen der GoodTools-Konvention - "[T+Ger]"
#    (neuere Uebersetzung), "[T-Eng]" (aeltere), oft mit Versions- und
#    Gruppenzusatz wie "[T+Ger1.01_Team]".
#
# Beides bedeutet dasselbe: das Spiel ist NICHT nur auf Japanisch
# nutzbar. Ein Fan-Uebersetzungspatch ist sogar der haeufigste Grund
# ueberhaupt, ein japanisches ROM zu behalten - ausgerechnet die
# auszublenden ist das Gegenteil des Gewollten.
#
# Regel jetzt: ein Japan-Kennzeichen blendet nur dann aus, wenn im
# Namen KEIN Hinweis auf eine andere Sprache steht. Ein
# Uebersetzungs-Kennzeichen zaehlt dabei IMMER als solcher Hinweis -
# unabhaengig davon, in welche Sprache uebersetzt wurde, denn eine
# Uebersetzung ins Japanische gibt es bei japanischen ROMs nicht.

# GoodTools-Uebersetzungskennzeichen: [T+Ger], [T-Eng], [T+Ger1.01],
# (T+Spa) ... - ein "T", dann + oder -, in runden ODER eckigen Klammern.
_UEBERSETZUNG = re.compile(r"[\(\[]\s*T[+-]", re.I)

# Ausgeschriebene Sprachnamen, wie sie in Sammlungen vorkommen.
# Japanisch bewusst NICHT in dieser Liste - "(Japanese)" ist kein
# Hinweis auf eine andere Sprache.
_SPRACHNAMEN = (
    "english", "german", "deutsch", "french", "francais", "spanish",
    "espanol", "italian", "italiano", "portuguese", "dutch", "swedish",
    "danish", "norwegian", "finnish", "polish", "russian", "korean",
    "chinese", "czech", "hungarian", "greek", "turkish", "catalan",
)
_SPRACHNAME = re.compile(
    r"[\(\[]\s*(?:%s)(?:\s*,\s*[A-Za-z]+)*\s*[\)\]]" % "|".join(_SPRACHNAMEN),
    re.I)

# Zweibuchstabige Sprachcodes als Klammergruppe: (En), (En,Ja),
# (En,Fr,De) - so schreiben No-Intro und Redump das durchgaengig.
# "Ja" allein ist KEIN Hinweis auf eine andere Sprache.
_SPRACHCODES = re.compile(r"[\(\[]\s*[A-Z][a-z](?:\s*,\s*[A-Z][a-z])*\s*[\)\]]")


def _hat_fremdsprache(name):
    """True, wenn der Name irgendeinen Hinweis darauf traegt, dass das
    Spiel in einer ANDEREN Sprache als Japanisch spielbar ist."""
    if _UEBERSETZUNG.search(name):
        return True
    if _SPRACHNAME.search(name):
        return True
    for treffer in _SPRACHCODES.finditer(name):
        teile = [t.strip().lower()
                 for t in treffer.group(0).strip("()[]").split(",")]
        if any(t and t != "ja" for t in teile):
            return True
    return False


def _is_japan_only(name):
    if not _JAPAN_ONLY.search(name):
        return False
    # Japanisches Release, aber mit Hinweis auf eine andere Sprache
    # (Sprachcode, ausgeschriebener Sprachname oder Uebersetzungspatch)
    # -> kein "nur japanisch".
    return not _hat_fremdsprache(name)

# Bekannte Boot-/Test-/Demo-Dateien, die manche MiSTer-Verteilungen
# direkt in die ROM-Ordner legen (fuer den Hardware-Selbsttest). Haben
# zufaellig die richtige Endung (z.B. .chd/.gb/.gba) und wuerden sonst
# faelschlich als "Spiel" in der Liste auftauchen.
IGNORE_ROM_BASENAMES = {"boot", "boot1", "boot2", "mister-boot", "mister-demo"}

def nice_name(dirname):
    raw = dirname.lstrip("_")
    return NICE_NAMES.get(raw, raw.replace("_", " "))


# ---------------------------------------------------------------------------
# MEHRTEILIGE SPIELE (Build 259)
#
# NUTZERWUNSCH: "bei PSX, Sega CD oder Saturn bestehen viele Spiele aus
# mehreren Discs. Wenn diese alle in einem Ordner liegen, blaeht das die
# Spieleliste auf. Das Frontend soll sie zu einem Eintrag
# zusammenfassen und beim Starten fragen, welche Disc."
#
# WAS NICHT GEHT, und das gehoert an den Anfang: .m3u-Playlisten.
# MiSTer unterstuetzt sie nicht - nachgelesen im MiSTer-Forum, dort
# sagt es ein Core-Entwickler selbst ("trying to implement m3us would
# be fairly awkward given how things work now"), und Nutzer berichten,
# dass m3u-Dateien beim Laden einer CD gar nicht erst auswaehlbar sind.
# Eine MGL verweist immer auf GENAU EINE Datei. Zusammenfassen und beim
# Start fragen ist deshalb nicht der zweitbeste Weg, sondern der
# einzige richtige.
#
# DER MARKER IST DERSELBE wie oben (_DISC) - es gibt keine zweite
# Erkennung fuer dieselbe Sache.

def disc_marker(name):
    """Der Datentraeger-Marker eines Namens ("(Disc 2)") oder ""."""
    m = _DISC.search(name or "")
    return m.group(0).strip() if m else ""


def disc_basis(name):
    """Der Name OHNE den Datentraeger-Marker - der gemeinsame Nenner
    aller Teile eines Spiels.

    Nur der Marker faellt weg, sonst nichts: Regions- und
    Versions-Tags bleiben stehen. "Spiel (USA) (Disc 1)" und
    "Spiel (Europe) (Disc 1)" sind zwei verschiedene Fassungen und
    duerfen NICHT zusammenfallen - genau diese Unterscheidung hat
    _dedupe_items() seinerzeit absichtlich wiederhergestellt."""
    if not name:
        return name
    ohne = _DISC.sub(" ", name)
    return re.sub(r"\s{2,}", " ", ohne).strip()


# Reihenfolge fuer die Auswahl: Zahlen zuerst nach Wert, Buchstaben
# danach alphabetisch ("Side A" vor "Side B", "Disc 2" vor "Disc 10").
# Ein reines sorted() ueber die Namen setzte "Disc 10" vor "Disc 2".
_DISC_NUM = re.compile(r"([0-9]+)")


def disc_rang(name):
    """Sortierschluessel eines Teils - (0, Zahl) oder (1, Text)."""
    marker = disc_marker(name)
    if not marker:
        return (2, "")
    m = _DISC_NUM.search(marker)
    if m:
        return (0, int(m.group(1)))
    return (1, marker.lower())
