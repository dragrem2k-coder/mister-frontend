#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MiSTers EIGENE Favoriten lesen (Build 213).

WORUM ES GEHT

MiSTer hat eine eingebaute Favoritenfunktion: im OSD markiert man ein
Spiel, und MiSTer legt dafuer eine .mgl-Startdatei in einem eigenen
Ordner ab. Das Frontend hat davon bisher nichts gewusst - es hatte nur
seine EIGENEN Favoriten (fe/game_state.py, load_favorites()). Wer in
MiSTer Favoriten gesetzt hatte, fand sie hier nicht wieder.

Dieses Modul liest sie und gibt sie in genau der Form zurueck, die eine
normale Spieleliste hat. Das ist die ganze Absicht: die Eintraege sollen
sich in nichts von anderen Spielen unterscheiden - Boxart,
Spielbeschreibung, Spielzeit, RetroAchievements, Startpfad, alles laeuft
ueber die vorhandenen Wege. Es kommt eine Kategorie dazu, kein zweiter
Spielbegriff.

WAS EINE .MGL ENTHAELT, und wir wissen es genau, weil wir selbst welche
schreiben (write_mgl() in fe/launch.py):

    <mistergamedescription>
        <rbf>_Console/SNES</rbf>
        <file delay="2" type="f" index="0"
              path="../../../../../media/fat/games/SNES/Spiel.sfc"/>
    </mistergamedescription>

ZWEI DINGE, DIE HIER NICHT GERATEN WERDEN

1. DER ORDNERNAME. Wie MiSTers Favoritenordner auf einem bestimmten
   Aufbau genau heisst, kann ich von hier aus nicht pruefen - je nach
   Fassung und Skript sind mehrere Schreibweisen im Umlauf. Deshalb
   wird eine LISTE von Kandidaten durchgesehen und der erste
   vorhandene genommen; welcher es war, steht danach im Log. Kein
   Kandidat da heisst: die Kategorie erscheint einfach nicht.

2. DIE PFADTIEFE. Unsere eigenen .mgl-Dateien tragen fuenf "../" vor
   dem absoluten Pfad, weil sie aus /tmp gestartet werden. Eine .mgl
   in einem Favoritenordner liegt anderswo und hat deshalb
   moeglicherweise eine andere Tiefe. Der Leser haengt sich daran
   nicht auf: er schneidet ALLE fuehrenden "../" ab und nimmt, was
   danach steht - beginnt es mit einem Schraegstrich, ist es der
   absolute Pfad; sonst wird es relativ zum Ordner der .mgl aufgeloest.
   Beides wird im Test durchgespielt.

WAS ES KOSTET: eine Verzeichnisdurchsicht beim Einlesen und ein paar
Dutzend winzige Dateien. Gegen die 30.000 Spiele einer echten Sammlung
ist das nichts, und es passiert genau einmal je Einlesevorgang - nicht
im Zeichenweg.
"""
import os
import re

from fe.log import LOG

BASE = "/media/fat"

# In dieser Reihenfolge gesucht. Der erste vorhandene Ordner gewinnt.
FAV_ORDNER_KANDIDATEN = (
    "_@Favorites",
    "_Favorites",
    "_@Favorite",
    "_Favorite",
)

# Bewusst nachsichtig: Anfuehrungszeichen einfach oder doppelt,
# Leerraum beliebig, Reihenfolge der Attribute egal. Eine .mgl ist
# kein strenges XML, und ein Parser aus der Standardbibliothek waere
# hier die schlechtere Wahl - er wuerde bei einer einzigen
# unsauberen Datei mit einer Ausnahme aussteigen, statt sie zu
# ueberspringen.
_RE_RBF = re.compile(r"<rbf>\s*([^<]+?)\s*</rbf>", re.I)
_RE_PATH = re.compile(r"""\bpath\s*=\s*["']([^"']+)["']""", re.I)
_RE_DELAY = re.compile(r"""\bdelay\s*=\s*["']?(\d+)""", re.I)
_RE_TYPE = re.compile(r"""\btype\s*=\s*["']([^"']+)["']""", re.I)
_RE_INDEX = re.compile(r"""\bindex\s*=\s*["']?(\d+)""", re.I)

# Notbremse: eine .mgl ist ein paar hundert Byte. Was deutlich groesser
# ist, ist keine, und dann wird sie auch nicht eingelesen.
MGL_MAX_BYTES = 64 * 1024


def fav_ordner():
    """Der vorhandene Favoritenordner von MiSTer - oder None."""
    for name in FAV_ORDNER_KANDIDATEN:
        pfad = os.path.join(BASE, name)
        if os.path.isdir(pfad):
            return pfad
    return None


def pfad_aus_mgl(roh, mgl_ordner):
    """Den ROM-Pfad aus dem path-Attribut einer .mgl herausloesen.

    Siehe Punkt 2 im Modulkopf: alle fuehrenden "../" weg, danach
    entscheidet der erste Buchstabe."""
    if not roh:
        return None
    teile = roh.replace("\\", "/").split("/")
    # Fuehrende ".."-Glieder abtragen und dabei ZAEHLEN.
    hoch = 0
    while teile and teile[0] in ("..", "", "."):
        if teile[0] == "..":
            hoch += 1
        teile.pop(0)
    if not teile:
        return None
    rest = "/".join(teile)

    # DIE ENTSCHEIDUNG, und sie hat einen Fehler gekostet, den der
    # erste Rauchtest gefunden hat.
    #
    # write_mgl() setzt fuenf ".." vor einen ABSOLUTEN Pfad:
    #
    #     "../../../../.." + "/media/fat/games/SNES/Spiel.sfc"
    #     = ../../../../../media/fat/games/SNES/Spiel.sfc
    #
    # Zaehlt man die "../" als Zeichenketten weg, frisst das fuenfte
    # den Schraegstrich des absoluten Pfads mit - uebrig bleibt
    # "media/fat/..." OHNE fuehrenden Schraegstrich, und das wurde
    # dann relativ zum Favoritenordner aufgeloest. Der Pfad zeigte
    # ins Nichts, und zwar still: der Favorit waere einfach
    # verschwunden, ohne Fehlermeldung.
    #
    # Die Regel, die beide Faelle richtig trifft: waren ".."-Glieder
    # dabei, war ein absoluter Pfad gemeint (so macht es die
    # mrext-Konvention, und so schreiben wir selbst). War keines
    # dabei, ist es wirklich relativ zum Ordner der .mgl.
    if hoch:
        return os.path.normpath("/" + rest)
    return os.path.normpath(os.path.join(mgl_ordner, rest))


def mgl_lesen(pfad):
    """(rbf, rom_pfad, delay, ftype, index) aus einer .mgl - oder None.

    Nachsichtig: fehlt etwas, wird der uebliche Standard genommen
    (delay 2, type "f", index 0) - dieselben Werte, die auch
    write_mgl() als Rueckfall benutzt."""
    try:
        if os.path.getsize(pfad) > MGL_MAX_BYTES:
            return None
        with open(pfad, "r", errors="replace") as f:
            inhalt = f.read()
    except OSError:
        return None
    m_rbf = _RE_RBF.search(inhalt)
    m_path = _RE_PATH.search(inhalt)
    if not m_rbf or not m_path:
        return None
    rom = pfad_aus_mgl(m_path.group(1), os.path.dirname(pfad))
    if not rom:
        return None
    m_d = _RE_DELAY.search(inhalt)
    m_t = _RE_TYPE.search(inhalt)
    m_i = _RE_INDEX.search(inhalt)
    return (m_rbf.group(1).strip(),
            rom,
            int(m_d.group(1)) if m_d else 2,
            (m_t.group(1) if m_t else "f"),
            int(m_i.group(1)) if m_i else 0)


def _system_zu_pfad(rom, systeme):
    """Welches System gehoert zu diesem ROM-Pfad? (anzeige, syskey,
    rbf, extmap) oder None.

    ZWEI MERKMALE MUESSEN ZUSAMMENPASSEN, und das ist Absicht: der
    Ordnername im Pfad UND die Dateiendung. Nur der Ordner waere zu
    wenig (in /games/SNES kann eine .zip oder ein Bild liegen), nur
    die Endung ebenfalls (.bin gehoert zu einem halben Dutzend
    Systemen). Passt nichts zusammen, wird der Eintrag ausgelassen -
    lieber ein Favorit weniger als einer, der den falschen Core
    startet."""
    endung = os.path.splitext(rom)[1].lower()
    teile = set(p.upper() for p in rom.replace("\\", "/").split("/") if p)
    treffer = None
    for anzeige, syskey, ordner, rbf, extmap in systeme:
        if endung not in extmap:
            continue
        if not any(o.upper() in teile for o in ordner):
            continue
        # Der genauere Treffer gewinnt: ein System, dessen Ordnername
        # weiter hinten im Pfad steht, ist der naeherliegende.
        if treffer is None:
            treffer = (anzeige, syskey, rbf, extmap)
    return treffer


# GEPRUEFT UND WIEDER ENTFERNT (Build 214): hier standen ein Satz
# _labels und eine Funktion labels(), die die Namen der gelesenen
# Favoriten fuer die kleine Markierung in der Liste bereithalten
# sollten. Gebraucht werden sie nicht: die zurueckgegebenen Eintraege
# TRAGEN ihren Namen an erster Stelle, und _favoriten_vereinen() in
# frontend.py liest ihn genau dort ab. Ein zweiter Weg zur selben
# Auskunft ist kein Komfort, sondern eine Stelle, die spaeter
# auseinanderlaufen kann - und eine Funktion, die niemand ruft, liest
# beim naechsten Mal wie ein Hinweis, dass es sie braucht.


def favoriten_lesen(systeme, hoechstens=500):
    """MiSTers Favoriten als Spieleliste: [(name, "game", arg), ...].

    arg hat GENAU die Form, die der Rest des Programms erwartet
    (siehe load_recent() in fe/game_state.py und den Startpfad in
    frontend.py):

        (rom_pfad, endung, syskey, rbf, (delay, ftype, index))

    Dadurch funktioniert an diesen Eintraegen alles Uebrige von
    selbst - Boxart, Beschreibung, Spielzeit, RA, Start.

    Der rbf aus der .mgl wird BEWUSST NICHT uebernommen, sondern der
    des Systems genommen: nur so greifen die Core-Wahl aus
    fe/cores.py (aufloesen(), prueft ob die Datei noch existiert) und
    die RA-Core-Erkennung. Eine .mgl von MiSTer kann einen Core
    nennen, den update_all inzwischen geloescht hat - der Weg ueber
    das System ist der geprueftere.

    hoechstens: Notbremse gegen einen Ordner, in dem aus irgendeinem
    Grund Tausende Dateien liegen."""
    ordner = fav_ordner()
    if not ordner:
        return []
    try:
        dateien = sorted(f for f in os.listdir(ordner)
                         if f.lower().endswith(".mgl"))
    except OSError as e:
        LOG("MiSTer-Favoriten: %s nicht lesbar (%s)" % (ordner, e))
        return []
    if not dateien:
        return []
    items = []
    ausgelassen = 0
    for name in dateien[:hoechstens]:
        gelesen = mgl_lesen(os.path.join(ordner, name))
        if not gelesen:
            ausgelassen += 1
            continue
        _rbf_aus_mgl, rom, dl, ftype, idx = gelesen
        sys_treffer = _system_zu_pfad(rom, systeme)
        if not sys_treffer:
            ausgelassen += 1
            continue
        _anzeige, syskey, rbf, extmap = sys_treffer
        endung = os.path.splitext(rom)[1].lower()
        # Die Werte des SYSTEMS haben Vorrang vor denen der .mgl: sie
        # sind gepflegt und getestet, die .mgl kann von einem
        # beliebigen Werkzeug stammen.
        dl, ftype, idx = extmap.get(endung, (dl, ftype, idx))
        titel = os.path.splitext(os.path.basename(rom))[0]
        items.append((titel, "game",
                      (rom, endung, syskey, rbf, (dl, ftype, idx))))
    LOG("MiSTer-Favoriten: %d aus %s%s"
        % (len(items), ordner,
           (", %d ausgelassen" % ausgelassen) if ausgelassen else ""))
    return items
