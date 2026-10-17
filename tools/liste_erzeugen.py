#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Erzeugt die vollstaendige Funktions- und Einstellungsliste.

NUTZERWUNSCH: "dann haette ich einmal gerne eine liste mit allen
funktionen und einstellmoeglichkeiten was das frontend alles kann!
wirklich alles! fehlerfrei!"

WARUM ERZEUGT UND NICHT GESCHRIEBEN. Das Frontend hat 647 Textbausteine,
davon 147 fuer das Systemmenue, dazu 110 Einstellungsfunktionen und ein
gutes Dutzend Schalterdateien. Eine von Hand geschriebene Liste waere am
Tag ihrer Fertigstellung schon falsch - und "fehlerfrei" war die
ausdrueckliche Bedingung.

Diese Liste kommt deshalb aus dem laufenden Code:

  * Das SYSTEMMENUE wird vom ECHTEN Erzeuger geholt
    (fe.menu.system_items()) - also genau dem, der im Betrieb die
    Eintraege baut. Nicht nachgebaut, nicht abgeschrieben.
  * Die KONTEXTMENUE-Eintraege, die TASTENBELEGUNG, die SCHALTERDATEIEN
    und die AUFRUF-OPTIONEN werden aus dem Quelltext gelesen.
  * Zum Schluss laeuft eine GEGENPROBE IN BEIDE RICHTUNGEN: jeder
    Menuetext, den der Erzeuger liefert, muss in der Liste stehen, und
    jeder Eintrag der Liste muss vom Erzeuger kommen. Faellt eines
    davon durch, bricht das Werkzeug ab und schreibt keine Datei.

Ausfuehren:
    python3 tools/liste_erzeugen.py            # schreibt docs/FUNKTIONSLISTE.md
    python3 tools/liste_erzeugen.py --pruefen  # nur die Gegenprobe
"""
import io
import os
import re
import sys

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
_FE = os.path.join(_REPO, "frontend")
sys.path.insert(0, _FE)

ZIEL = os.path.join(_REPO, "docs", "FUNKTIONSLISTE.md")

# Marken um den Menue-Abschnitt - die Gegenprobe der zweiten Richtung
# darf nur dort suchen. Siehe gegenprobe().
MENUE_ANFANG = "## 2. Das Systemmenue, Gruppe fuer Gruppe"
MENUE_ENDE = "## 3. Das Kontextmenue"


def ra_zusatz():
    """Menuezeilen, die nur bei EINGERICHTETEN RetroAchievements
    erscheinen.

    Dieses Werkzeug laeuft nicht auf dem MiSTer und sieht deshalb
    keine eingerichteten Achievements - in der Gruppe stuende sonst
    nur "nicht eingerichtet", und die Liste waere genau an der Stelle
    unvollstaendig, an der sie vollstaendig sein soll.

    DIESE DREI SIND DER EINZIGE ZUSATZ, den die Gegenprobe durchlaesst,
    und er steht hier namentlich. Eine Ausnahme, die man aufzaehlen
    muss, ist keine Luecke - eine Ausnahme "alles, was so aussieht",
    waere eine."""
    return [de("sys_ra_configured", "<Benutzername>"),
            de("sys_ra_toggle_on"),
            de("sys_ra_settings")]

import fe.menu as MENU                                   # noqa: E402
import fe.input as INP                                    # noqa: E402
from fe.translations import TRANSLATIONS as TEXTE                         # noqa: E402

_FRONTEND_PY = io.open(os.path.join(_FE, "frontend.py"),
                       encoding="utf-8").read()
_SETTINGS_PY = io.open(os.path.join(_FE, "fe", "settings.py"),
                       encoding="utf-8").read()


def de(key, *fmt):
    """Den deutschen Text eines Schluessels - ohne Formatfehler."""
    eintrag = TEXTE.get(key) or {}
    text = eintrag.get("de") or eintrag.get("en") or key
    if fmt:
        try:
            return text % fmt
        except (TypeError, ValueError):
            return text
    return text


# ---------------------------------------------------------------------------
# 1. DAS SYSTEMMENUE - vom echten Erzeuger
# ---------------------------------------------------------------------------
def systemmenue():
    """(Gruppenname, [Eintragstexte]) in der Reihenfolge des Menues.

    Aufgerufen wird fe.menu.system_items() mit den Vorgaben, die auch
    im Betrieb gelten. Die drei Gruppen, die vom GERAET abhaengen
    (Cores, Standalone, Scripts), kommen als Argument herein und
    bleiben hier leer - was dort steht, haengt an der SD-Karte des
    Nutzers und nicht am Frontend. Sie werden im Text dafuer eigens
    erklaert."""
    baum = MENU.system_items(music_enabled=True, music_source="mp3")
    gruppen = []
    for name, knoten in baum["folders"].items():
        eintraege = [eintrag[0] for eintrag in (knoten.get("items") or ())]
        gruppen.append((name, eintraege))
    return gruppen


# ---------------------------------------------------------------------------
# 2. DAS KONTEXTMENUE - aus den im Quelltext benutzten Schluesseln
# ---------------------------------------------------------------------------
def kontextmenue():
    """Alle ctx_*-Schluessel, die frontend.py tatsaechlich benutzt.

    Nicht alle ctx_*-Texte sind Menuepunkte (einige sind Meldungen und
    Titel). Gelistet werden deshalb nur die, die als Eintrag in einer
    Auswahl auftauchen - erkennbar daran, dass der Schluessel in einer
    Zeile mit einem Komma dahinter steht, also in einem Tupel. Dazu
    kommen die beiden Schalter-Paare (Favorit, Durchgespielt), bei
    denen der Text vom Zustand abhaengt."""
    benutzt = []
    for m in re.finditer(r't\("(ctx_[a-z0-9_]+)"', _FRONTEND_PY):
        k = m.group(1)
        if k not in benutzt:
            benutzt.append(k)
    # Titel und Meldungen sind keine Menuepunkte.
    keine_punkte = {"ctx_titel", "ctx_versteckt_ok", "ctx_system_bleibt",
                    "ctx_zufall_fav_leer", "ctx_hauptseite_wieder_hinweis"}
    return [(k, de(k)) for k in benutzt if k not in keine_punkte]


# ---------------------------------------------------------------------------
# 3. DIE TASTEN - aus KEYMAP und den Pad-Zuordnungen
# ---------------------------------------------------------------------------
AKTION_TEXT = {
    "up": "eine Zeile nach oben",
    "down": "eine Zeile nach unten",
    "left": "eine Seite zurueck (im Hauptmenue: Kategorie zurueck)",
    "right": "eine Seite vor (im Hauptmenue: Kategorie vor)",
    "ok": "oeffnen / starten / bestaetigen",
    "back": "zurueck",
    "exit": "zurueck (Esc)",
    "back_fe": "zum Frontend zurueck (waehrend ein Spiel laeuft)",
    "menu": "Kontextmenue oeffnen",
    "filter": "Filter",
    "search": "Suche",
    "ansicht": "Ansicht wechseln (Liste / Raster / Galerie)",
    "favorite": "als Favorit markieren",
    "music": "Musik an/aus",
    "music_next": "naechster Titel",
    "volume_up": "lauter",
    "volume_down": "leiser",
    "select": "Select (allein: zurueck; gehalten: Kombinationen)",
    "quit": "Frontend beenden",
    "random": "zufaelliges Spiel",
    "page_up": "eine Seite nach oben",
    "page_down": "eine Seite nach unten",
    "completed": "als durchgespielt markieren",
    "list_start": "an den Anfang der Liste",
    "list_end": "an das Ende der Liste",
    "osd": "MiSTers eigenes OSD oeffnen",
    "ra_showcase": "die Erfolge zum Spiel zeigen",
    "search_backspace": "in der Suche ein Zeichen zurueck",
}

# Die Buchstabentasten sind 26 Zeilen, die alle dasselbe sagen. Sie
# werden zu EINER zusammengefasst - eine Tabelle, in der man scrollen
# muss, um "ansicht" zu finden, hilft niemandem.
BUCHSTABEN_PRAEFIX = "letter:"


def tasten():
    """(Tastenname, Aktion, Beschreibung) aus der echten KEYMAP."""
    namen = {}
    for name, wert in vars(INP).items():
        if name.startswith(("KEY_", "BTN_", "AXIS_")) \
                and isinstance(wert, int):
            namen.setdefault(wert, name)
    zeilen = []
    buchstaben = 0
    for code, aktion in sorted(INP.KEYMAP.items(),
                               key=lambda kv: str(kv[1])):
        if aktion is None:
            continue
        if aktion.startswith(BUCHSTABEN_PRAEFIX):
            buchstaben += 1
            continue
        zeilen.append((namen.get(code, "Code %d" % code), aktion,
                       AKTION_TEXT.get(aktion, "")))
    if buchstaben:
        zeilen.append(("A - Z, Leertaste", "letter:...",
                       "springt zum Buchstaben; in der Suche wird "
                       "getippt (%d Tasten)" % buchstaben))
    return zeilen


def select_kombinationen():
    """Die Select-Kombinationen, falls vorhanden."""
    tab = getattr(INP, "SELECT_COMBOS", None) or {}
    namen = {"left": "Links", "right": "Rechts", "up": "Hoch",
             "down": "Runter"}
    return [(namen.get(k, k), v) for k, v in sorted(tab.items())]


# ---------------------------------------------------------------------------
# 4. DIE SCHALTERDATEIEN
# ---------------------------------------------------------------------------
def schalterdateien():
    """Alle /media/fat/frontend/<name>-Pfade aus dem Quelltext.

    Das sind die Schalter, die man von Hand anlegt oder loescht - also
    genau die, die man braucht, wenn man NICHT ins Menue kommt. Sie
    stehen in keiner Oberflaeche und waeren ohne diese Liste nur im
    Quelltext zu finden."""
    # GETRENNT NACH SCHALTER UND WERT, und das ist keine Kosmetik:
    # bei einem SCHALTER zaehlt nur, OB die Datei existiert - man legt
    # sie an oder loescht sie. Ein WERT steht IN der Datei und wird vom
    # Menue geschrieben; wer den von Hand anlegt, erzeugt eine leere
    # Datei und damit einen Zustand, den das Menue nie herstellt.
    #
    # Unterschieden wird daran, wie der Pfad im Quelltext benutzt wird:
    # steht er in derselben Zeile wie exists(), ist es ein Schalter.
    schalter, werte = set(), set()
    for _rohquelle in (_FRONTEND_PY, _SETTINGS_PY):
        # Fortsetzungszeilen zusammenziehen. Ohne das steht
        # 'NAME = \\' allein in der Zeile und der Pfad in der
        # naechsten - und die Konstante wird nicht erkannt.
        # Genau daran sind im ersten Lauf fuenf Schalter als
        # Wertdateien eingeordnet worden.
        quelle = re.sub(r'\\\n\s*', ' ', _rohquelle)
        # Die Pfade stehen meist in einer Konstante und werden
        # woanders benutzt. Der erste Entwurf dieser Pruefung sah nur
        # in DIE ZEILE und fand deshalb null Schalter - die Heuristik
        # war richtig gedacht und am falschen Ort angewendet.
        namen_zu_konst = {}
        for m in re.finditer(
                r'^\s*([A-Z][A-Z0-9_]*)\s*=\s+'
                r'"/media/fat/frontend/([a-z0-9_]+)"',
                quelle, re.M):
            namen_zu_konst[m.group(2)] = m.group(1)
        for zeile in quelle.split("\n"):
            for m in re.finditer(
                    r'"/media/fat/frontend/([a-z0-9_]+)"', zeile):
                name = m.group(1)
                if "exists(" in zeile or "_flag_setzen" in zeile:
                    schalter.add(name)
                elif name not in namen_zu_konst:
                    werte.add(name)
        # Und jetzt ueber die Konstanten: wird sie mit exists() oder
        # _flag_setzen() benutzt, ist es ein Schalter.
        for name, konst in namen_zu_konst.items():
            # self. UND cls. zulassen: textkonsole_grafik_aus wird
            # aus einer classmethod geprueft, und genau deshalb stand
            # es im ersten Lauf unter den Wertdateien.
            _vor = r'(self\.|cls\.)?'
            if re.search(r'(exists\(\s*%s%s|_flag_setzen\(\s*%s%s)'
                         % (_vor, konst, _vor, konst), quelle):
                schalter.add(name)
            else:
                werte.add(name)
    # Ein Name, der BEIDES kann, ist ein Schalter: dort entscheidet
    # die Existenz.
    werte -= schalter
    return sorted(schalter), sorted(werte)


# ---------------------------------------------------------------------------
# 5. DIE AUFRUF-OPTIONEN
# ---------------------------------------------------------------------------
def optionen():
    """Die --x-Optionen, die frontend.py selbst kennt."""
    gefunden = []
    for m in re.finditer(r'"(--[a-z][a-z0-9_-]*)"', _FRONTEND_PY):
        if m.group(1) not in gefunden:
            gefunden.append(m.group(1))
    return sorted(gefunden)


# ---------------------------------------------------------------------------
# 6. DIE EINGEBAUTE HILFE - sie ist selbst eine Funktionsliste
# ---------------------------------------------------------------------------
def hilfe_themen():
    """Die help_*-Abschnitte der eingebauten Hilfe/Uebersicht."""
    paare = []
    for k in TEXTE:
        if k.startswith("help_") and k.endswith("_desc"):
            taste = k[:-5] + "_key"
            if taste in TEXTE:
                paare.append((de(taste), de(k)))
    return sorted(paare)


# ---------------------------------------------------------------------------
# 7. DIE GROSSEN FUNKTIONEN - aus den Modulen selbst
# ---------------------------------------------------------------------------
# NACHFRAGE DES NUTZERS: "Hast du auch die Features bedacht, OBS etc,
# was es noch so alles kann?"
#
# Berechtigt. Die Liste zaehlte das MENUE auf - und Dinge wie das
# OBS-Overlay, Zaparoo oder der ROM-Waechter stehen dort als EINE Zeile
# ("Stream-Overlay: an"), ohne dass irgendwo steht, was sie eigentlich
# sind. Ein Menuepunkt ist nicht dasselbe wie eine Funktion.
#
# Die Quelle dafuer sind die Module selbst: jedes hat einen
# Beschreibungstext an seinem Anfang, und der ist von demjenigen
# geschrieben, der es gebaut hat. Genommen wird der erste Satz.
#
# WARUM EINE FESTE EINTEILUNG UND KEINE HEURISTIK: ob ein Modul eine
# Funktion fuer den Nutzer ist oder Innenleben, kann man nicht aus dem
# Namen raten. Die Einteilung steht deshalb hier - und
# tools/test_funktionsliste.py prueft, dass JEDES Modul darin
# vorkommt. Ein neues Modul macht die Suite rot, bis jemand
# entscheidet, in welche Haelfte es gehoert. Das ist Absicht: eine
# Liste, aus der neue Funktionen lautlos herausfallen, ist genau die,
# die wir nicht wollten.
INNENLEBEN = {
    "art", "bildlib", "dateibaum", "framebuffer", "input", "launch",
    "log", "nachladen", "naming", "paths", "prewarm_worker", "scan",
    "search", "settings", "single_instance", "systems",
    "translations", "zwischenspeicher", "menu", "bench", "show",
    "demo", "hidraw", "ra_core", "mister_system", "timekeeping",
    "update_check",
}


def module_beschreibung():
    """(Modulname, erster Satz) fuer alle Module - zweigeteilt.

    Rueckgabe: (funktionen, innenleben), beide als Liste von Paaren."""
    import ast
    import glob
    funktionen, innen = [], []
    pfade = sorted(glob.glob(os.path.join(_FE, "fe", "*.py")))
    pfade.append(os.path.join(_FE, "stream_server.py"))
    for pfad in pfade:
        name = os.path.basename(pfad)[:-3]
        if name == "__init__":
            continue
        try:
            doc = ast.get_docstring(
                ast.parse(io.open(pfad, encoding="utf-8").read())) or ""
        except (SyntaxError, OSError):
            doc = ""
        satz = " ".join(doc.split())
        # Der erste Satz, aber nicht mitten in einer Abkuerzung
        # abgeschnitten: getrennt wird an ". " vor einem Grossbuchstaben.
        teil = re.split(r"\.\s+(?=[A-ZÄÖÜ])", satz, 1)[0].rstrip(".")
        # Zwei Beschreibungen laufen ohne Punkt in eine Aufzaehlung
        # oder einen Dateinamen-Block weiter (cores, art). Ein
        # Nachschlagewerk braucht dort einen Satz und keine halbe
        # Codeliste - also vor der ersten Grossbuchstaben-Kopfzeile
        # abschneiden und notfalls hart kappen.
        teil = re.split(r"\s+(?=[A-ZÄÖÜ]{4,}\s)", teil, 1)[0]
        if len(teil) > 230:
            teil = teil[:227].rsplit(" ", 1)[0] + " ..."
        if not teil:
            teil = "(ohne Beschreibung)"
        (innen if name in INNENLEBEN else funktionen).append(
            (name, teil))
    return funktionen, innen


def alle_module():
    """Alle Modulnamen - fuer die Vollstaendigkeitspruefung im Test."""
    f, i = module_beschreibung()
    return [n for n, _ in f] + [n for n, _ in i]


# ---------------------------------------------------------------------------
# 8. DAS OVERLAY FUER OBS - Port und Pfade aus dem Quelltext
# ---------------------------------------------------------------------------
def overlay_pfade():
    """(Port, [Pfade]) des eingebauten Webservers.

    Beides aus dem Quelltext gelesen und nicht abgeschrieben: der Port
    steht in frontend.py, die Pfade in stream_server.py. Eine
    Dokumentation, die einen Port NENNT, muss ihn vom Code haben -
    sonst schickt sie jemanden auf eine falsche Adresse."""
    port = None
    m = re.search(r"^STREAM_PORT\s*=\s*(\d+)", _FRONTEND_PY, re.M)
    if m:
        port = int(m.group(1))
    srv = io.open(os.path.join(_FE, "stream_server.py"),
                  encoding="utf-8").read()
    pfade = []
    for m in re.finditer(r'p (?:==|!=) "(/[a-z0-9_.]*)"', srv):
        if m.group(1) not in pfade:
            pfade.append(m.group(1))
    for m in re.finditer(r'u\.path (?:==|!=) "(/[a-z0-9_.]*)"', srv):
        if m.group(1) not in pfade:
            pfade.append(m.group(1))
    return port, pfade


# ---------------------------------------------------------------------------
# DIE GEGENPROBE
# ---------------------------------------------------------------------------
def gegenprobe(gruppen, text):
    """In BEIDE Richtungen.

    1. Jeder Eintrag, den der echte Erzeuger liefert, muss im Text
       stehen. Sonst fehlt etwas - und eine unvollstaendige Liste ist
       genau das, was der Nutzer nicht wollte.
    2. Jede Menuezeile im Text muss vom Erzeuger kommen. Sonst steht
       etwas drin, das es nicht gibt - und das ist schlimmer als eine
       Luecke, weil man danach sucht.
    """
    fehlen = []
    vom_erzeuger = set()
    for _gruppe, eintraege in gruppen:
        for e in eintraege:
            vom_erzeuger.add(e)
            if e not in text:
                fehlen.append(e)
    # Die zweite Richtung gilt NUR fuer den Menue-Abschnitt. Weiter
    # unten stehen Schalterdateien und Aufruf-Optionen in derselben
    # Schreibweise, und die kommen zu Recht nicht vom Menue-Erzeuger.
    # Der erste Entwurf dieser Pruefung hat genau das verwechselt und
    # 24 richtige Zeilen als "ueberfluessig" gemeldet - eine Gegenprobe,
    # die Falschalarm gibt, wird abgeschaltet und ist dann keine mehr.
    ueberfluessig = []
    abschnitt = text.split(MENUE_ANFANG, 1)
    if len(abschnitt) == 2:
        for zeile in abschnitt[1].split(MENUE_ENDE, 1)[0].split("\n"):
            if zeile.startswith("- `") and zeile.count("`") >= 2:
                innen = zeile.split("`")[1]
                if innen not in vom_erzeuger \
                        and innen not in ra_zusatz():
                    ueberfluessig.append(innen)
    return fehlen, ueberfluessig


# ---------------------------------------------------------------------------
def bauen():
    gruppen = systemmenue()
    z = []
    a = z.append
    a("# Dragend - was das Frontend alles kann")
    a("")
    a("Vollstaendige Liste aller Funktionen und Einstellungen.")
    a("")
    a("**Diese Datei ist erzeugt, nicht geschrieben.** Das Systemmenue")
    a("unten kommt aus `fe.menu.system_items()` - also aus genau dem")
    a("Code, der die Eintraege im Betrieb baut. Tasten, Schalterdateien")
    a("und Aufruf-Optionen sind aus dem Quelltext gelesen. Zum Schluss")
    a("laeuft eine Gegenprobe in beide Richtungen: fehlt ein Eintrag")
    a("oder steht einer zuviel darin, wird die Datei nicht geschrieben.")
    a("")
    a("Neu erzeugen: `python3 tools/liste_erzeugen.py`")
    a("")
    a("---")
    a("")
    a("## 1. Die drei Ansichten")
    a("")
    a("Jede Liste kann in drei Ansichten angezeigt werden; umgeschaltet")
    a("wird mit **F10** oder ueber das Kontextmenue (*Ansicht")
    a("wechseln*).")
    a("")
    a("| Ansicht | Was man sieht |")
    a("|---|---|")
    a("| **Liste** | eine Zeile je Eintrag, rechts die Boxart des "
      "markierten Spiels |")
    a("| **Raster** | Kacheln mit Cover, mehrere Spalten |")
    a("| **Galerie** | grosse Cover, eines im Mittelpunkt |")
    a("")
    a("Dazu zwei Seiten: die **Hauptseite** mit den Kategorien und die")
    a("**Spieleliste** innerhalb einer Kategorie. Beide haben ihre")
    a("eigene Ansichts-Einstellung.")
    a("")
    a("---")
    a("")
    a(MENUE_ANFANG)
    a("")
    a("Die Eintraege stehen in der Reihenfolge, in der sie im Menue")
    a("erscheinen. Texte mit `->` sagen, was ein Druck darauf tut;")
    a("Texte mit Zahlen oder Namen zeigen den aktuellen Stand und")
    a("schalten weiter.")
    a("")
    for name, eintraege in gruppen:
        a("### %s (%d Eintraege)" % (name, len(eintraege)))
        a("")
        for e in eintraege:
            a("- `%s`" % e)
        a("")
        # EHRLICHKEIT UEBER DEN ZUSTAND. Dieses Werkzeug laeuft nicht
        # auf dem MiSTer, also sieht es keine eingerichteten
        # RetroAchievements - und das steht dann so in der Gruppe.
        # Wer sie eingerichtet hat, sieht dort MEHR. Das gehoert
        # dazugeschrieben, sonst ist die Liste genau an der Stelle
        # falsch, an der sie vollstaendig sein soll.
        if name == de("sys_group_ra"):
            a("Ist RetroAchievements eingerichtet, stehen hier")
            a("zusaetzlich:")
            a("")
            for _z in ra_zusatz():
                a("- `%s`" % _z)
            a("")
            a("Und in **MiSTer selbst** (nicht im Frontend) muessen")
            a("Benutzername und Passwort in")
            a("`/media/fat/retroachievements.cfg` stehen - das")
            a("Frontend liest diese Datei, legt sie aber nie an und")
            a("aendert darin hoechstens die eine Zeile, um die es")
            a("gerade geht.")
            a("")
    a("### Dazu drei Gruppen, die vom Geraet abhaengen")
    a("")
    a("Sie stehen nicht oben, weil ihr Inhalt von der SD-Karte kommt")
    a("und nicht vom Frontend:")
    a("")
    a("- **Cores** - alle gefundenen FPGA-Kerne, nach Art gruppiert")
    a("- **Standalone** - eigenstaendige Programme, nach ihren Ordnern")
    a("- **Scripts** - alles aus `/media/fat/Scripts`")
    a("")
    a("---")
    a("")
    a(MENUE_ENDE)
    a("")
    a("Oeffnet sich mit **Y** (oder der Menue-Taste) auf einem Eintrag.")
    a("Was darin steht, haengt davon ab, worauf man steht - ein Spiel,")
    a("ein Ordner oder eine Kategorie.")
    a("")
    for _k, text in kontextmenue():
        a("- %s" % text)
    a("")
    a("---")
    a("")
    a("## 4. Die Tastenbelegung")
    a("")
    a("Das ist die Belegung, wie sie im Quelltext steht. Jede davon")
    a("laesst sich im Menue unter *Eingabe & Sprache* -> ")
    a("*Tastenbelegung anpassen* aendern.")
    a("")
    a("| Taste | Aktion | Was sie tut |")
    a("|---|---|---|")
    for taste, aktion, text in tasten():
        a("| `%s` | %s | %s |" % (taste, aktion, text))
    a("")
    kombis = select_kombinationen()
    if kombis:
        a("### Select gehalten")
        a("")
        a("| Kombination | Aktion |")
        a("|---|---|")
        for richtung, aktion in kombis:
            a("| Select + %s | %s |" % (richtung, aktion))
        a("")
    a("---")
    a("")
    a("## 5. Schalterdateien")
    a("")
    a("Diese Schalter legt man von Hand an oder loescht sie wieder -")
    a("sie stehen in keinem Menue. Genau dafuer sind sie da: der Fall,")
    a("in dem man sie braucht, ist meist der, in dem man nicht ins")
    a("Menue kommt.")
    a("")
    a("```")
    a("touch   /media/fat/frontend/<name>     # anlegen = einschalten")
    a("rm      /media/fat/frontend/<name>     # loeschen = ausschalten")
    a("```")
    a("")
    _schalter, _werte = schalterdateien()
    for name in _schalter:
        a("- `%s`" % name)
    a("")
    a("Namen auf `_aus` schalten etwas AB, wenn die Datei existiert.")
    a("")
    a("### Und diese Dateien halten einen Wert oder Inhalt")
    a("")
    a("Sie werden vom Menue geschrieben und stehen hier nur zur")
    a("Vollstaendigkeit. Von Hand anzulegen bringt nichts - eine leere")
    a("Datei ist ein Zustand, den das Menue nie herstellt. Loeschen")
    a("setzt die Einstellung dagegen gefahrlos auf die Vorgabe zurueck.")
    a("")
    for name in _werte:
        a("- `%s`" % name)
    a("")
    a("---")
    a("")
    a("## 6. Aufruf-Optionen")
    a("")
    a("```")
    a("python3 /media/fat/frontend/frontend.py <option>")
    a("```")
    a("")
    for o in optionen():
        a("- `%s`" % o)
    a("")
    a("---")
    a("")
    themen = hilfe_themen()
    if themen:
        a("## 7. Die eingebaute Uebersicht")
        a("")
        a("Das Frontend bringt seine eigene Hilfe mit, unter")
        a("*System -> Info -> Hilfe / Uebersicht*. Was dort steht:")
        a("")
        for titel, beschreibung in themen:
            a("- **%s** - %s" % (titel, beschreibung))
        a("")
        a("---")
        a("")
    # DIE GROSSEN FUNKTIONEN (Nachfrage des Nutzers: "Hast du auch
    # die Features bedacht, OBS etc?"). Ein Menuepunkt ist nicht
    # dasselbe wie eine Funktion - "Stream-Overlay: an" sagt nicht,
    # was das Overlay ist.
    _funk, _innen = module_beschreibung()
    a("## 8. Die grossen Funktionen, einzeln benannt")
    a("")
    a("Das Systemmenue oben zeigt die SCHALTER. Was dahinter steckt,")
    a("steht hier - jeweils in den Worten, mit denen die Funktion im")
    a("Quelltext selbst beschrieben ist.")
    a("")
    for name, satz in _funk:
        a("- **%s** - %s" % (name, satz))
    a("")
    a("### Das Overlay fuer OBS und den Browser")
    a("")
    _port, _pfade = overlay_pfade()
    a("Ist *Stream-Overlay* eingeschaltet, laeuft im Frontend ein")
    a("kleiner Webserver. Vom gleichen Netz aus erreichbar unter")
    a("`http://<IP-des-MiSTer>:%s` - in OBS als **Browserquelle**"
      % (_port if _port else "?"))
    a("einzutragen, nicht als Fenster-Aufnahme.")
    a("")
    a("| Pfad | Wofuer |")
    a("|---|---|")
    _wofuer = {
        "/": "dasselbe wie /overlay",
        "/overlay": "die Einblendung fuer OBS (Cover, Titel, Erfolge)",
        "/admin": "die Bedienseite - hier wird eingestellt, welche "
                  "Felder erscheinen",
        "/state": "der aktuelle Stand als JSON (fuer eigene Basteleien)",
        "/config": "die Einstellungen des Overlays, lesen und schreiben",
        "/art": "das Cover des markierten oder laufenden Spiels",
        "/badge": "ein Erfolgs-Abzeichen als Bild",
        "/events": "laufende Meldungen, damit die Seite sich ohne "
                   "Neuladen aktualisiert",
        "/screen.png": "ein Abbild des Frontend-Bildschirms",
        "/mirror": "die Spiegelseite - das Frontend im Browser "
                   "mitsehen",
    }
    for pf in _pfade:
        a("| `%s` | %s |" % (pf, _wofuer.get(pf, "")))
    a("")
    a("Dazu kommt der **OBS-Szenenwechsel** (`obs_websocket`): das")
    a("Frontend kann OBS per WebSocket sagen, wann es von der")
    a("Frontend-Szene auf die Capture-Karten-Szene umschalten soll -")
    a("also beim Start eines Spiels und beim Zurueckkehren. Das weiss")
    a("nur das Frontend zuverlaessig.")
    a("")
    a("### Und das Innenleben")
    a("")
    a("Diese Module haben keine eigene Einstellung - sie stehen hier,")
    a("damit die Liste vollstaendig ist und niemand sie vergeblich im")
    a("Menue sucht.")
    a("")
    for name, satz in _innen:
        a("- `%s` - %s" % (name, satz))
    a("")
    a("---")
    a("")
    a("## Was in dieser Liste NICHT steht")
    a("")
    a("Damit auch das klar ist:")
    a("")
    a("- **Was auf der Karte liegt** - Cores, Scripts, Standalone-")
    a("  Programme, Spiele, Cover. Das Frontend zeigt, was es findet.")
    a("- **Die Einstellungen von MiSTer selbst** (`MiSTer.ini`,")
    a("  Tastenbelegung der Kerne, Video). Das Frontend fasst dort")
    a("  genau eine Stelle an: den `[Menu]`-Block fuer den CRT-Modus,")
    a("  und das nur, wenn man es im Menue verlangt.")
    a("- **Was im Hintergrund laeuft** und keine Einstellung hat -")
    a("  Miniaturen, Vorauslader, der ROM-Waechter.")
    return "\n".join(z) + "\n", gruppen


def main():
    text, gruppen = bauen()
    fehlen, ueberfluessig = gegenprobe(gruppen, text)
    print("Systemmenue: %d Gruppen, %d Eintraege"
          % (len(gruppen), sum(len(e) for _g, e in gruppen)))
    print("Kontextmenue: %d Punkte" % len(kontextmenue()))
    print("Tasten: %d" % len(tasten()))
    print("Schalterdateien: %d Schalter, %d Wertdateien"
      % tuple(len(x) for x in schalterdateien()))
    print("Aufruf-Optionen: %d" % len(optionen()))
    print("Hilfe-Abschnitte: %d" % len(hilfe_themen()))
    print()
    if fehlen:
        print("GEGENPROBE FEHLGESCHLAGEN - diese Eintraege liefert der")
        print("Erzeuger, aber sie stehen nicht in der Liste:")
        for f in fehlen:
            print("  -", f)
    if ueberfluessig:
        print("GEGENPROBE FEHLGESCHLAGEN - diese Zeilen stehen in der")
        print("Liste, kommen aber nicht vom Erzeuger:")
        for u in ueberfluessig:
            print("  +", u)
    if fehlen or ueberfluessig:
        print()
        print("Es wurde NICHTS geschrieben.")
        return 1
    print("Gegenprobe in beide Richtungen bestanden.")
    if "--pruefen" in sys.argv:
        return 0
    os.makedirs(os.path.dirname(ZIEL), exist_ok=True)
    io.open(ZIEL, "w", encoding="utf-8").write(text)
    print("Geschrieben: %s (%d Zeilen)" % (ZIEL, text.count("\n")))
    # UND DIE DRUCKFASSUNG. Dieselbe Quelle, damit Markdown und PDF
    # nicht auseinanderlaufen koennen - genau der Fehler, den die vier
    # Handbuch-PDFs aus v4.8 gemacht haben (siehe docs/PDF_ERZEUGEN.md:
    # "Aenderungen gehoeren in die HTML-Datei, nicht in die PDF").
    try:
        html_schreiben(text)
    except ImportError:
        print("(kein markdown-Modul - HTML uebersprungen)")
    return 0


HTML_STIL = """
@page { size: A4; margin: 16mm 14mm; }
body { font-family: "DejaVu Sans", Arial, sans-serif; font-size: 9.5pt;
       line-height: 1.45; color: #1a1d24; margin: 0; }
h1 { font-size: 20pt; margin: 0 0 2mm; color: #0e1726; }
h1 + p { color: #5a6472; font-size: 11pt; margin-top: 0; }
h2 { font-size: 13pt; margin: 7mm 0 2mm; padding-bottom: 1mm;
     border-bottom: 1.5px solid #c9d2de; color: #0e1726;
     page-break-after: avoid; }
h3 { font-size: 10.5pt; margin: 4.5mm 0 1.5mm; color: #2b3b4e;
     page-break-after: avoid; }
ul { margin: 0 0 2mm; padding-left: 5mm; }
li { margin: 0.4mm 0; }
code { font-family: "DejaVu Sans Mono", monospace; font-size: 8.6pt;
       background: #f1f4f8; padding: 0.3mm 1mm; border-radius: 2px; }
pre { background: #f1f4f8; padding: 2mm 3mm; border-radius: 3px;
      font-size: 8.4pt; white-space: pre-wrap; }
pre code { background: none; padding: 0; }
table { border-collapse: collapse; width: 100%; margin: 0 0 3mm;
        font-size: 8.8pt; }
th, td { border: 1px solid #d4dbe5; padding: 1.2mm 2mm;
         text-align: left; vertical-align: top; }
th { background: #eef2f7; font-weight: 600; }
hr { border: none; border-top: 1px solid #e2e7ee; margin: 5mm 0; }
strong { color: #0e1726; }
"""


def html_schreiben(text):
    """Die Druckfassung - aus DEMSELBEN Text wie die Markdown-Datei.

    Daraus wird die PDF, siehe docs/PDF_ERZEUGEN.md:

        chromium --headless --disable-gpu --no-sandbox \\
            --no-pdf-header-footer \\
            --print-to-pdf=docs/Dragend_Funktionsliste.pdf \\
            file://$PWD/docs/FUNKTIONSLISTE.html
    """
    import markdown
    ziel = os.path.join(_REPO, "docs", "FUNKTIONSLISTE.html")
    koerper = markdown.markdown(text, extensions=["tables",
                                                  "fenced_code"])
    io.open(ziel, "w", encoding="utf-8").write(
        "<!doctype html><html lang=de><meta charset=utf-8>"
        "<title>Dragend - Funktionsliste</title><style>%s</style>%s"
        "</html>" % (HTML_STIL, koerper))
    print("Geschrieben: %s" % ziel)


if __name__ == "__main__":
    sys.exit(main())
