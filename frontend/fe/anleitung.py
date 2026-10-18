# -*- coding: utf-8 -*-
"""Die Spielanleitung zum markierten Eintrag (Build 263).

NUTZERWUNSCH: "Wenn ich ein Spiel ueber Frontend starte und es dann
spiele, habe ich ja die Moeglichkeit F12 zu druecken und dann im Menue
die Core-Einstellungen, wo ich auch auf Help gehen kann und mir die
Spieleanleitungen anzeigen lassen kann. Koennen wir das noch irgendwie
direkt einbinden? ... Dann waere es ja schoen, wenn man im Frontend
durch die Spiele scrollt und per Tastendruck sich die Anleitung dazu
ansehen koennte."

WAS NICHT GEHT, und warum das kein Versaeumnis ist: die Anleitung UEBER
das laufende Spiel legen. Waehrend ein Core laeuft, kommt das Bild vom
FPGA; der Linux-Framebuffer, in den wir zeichnen, ist dann gar nicht zu
sehen. Im MiSTer-Forum sagt ein Core-Entwickler zu genau dieser Idee,
das "would be a framework feature". Deshalb sitzt die Anleitung dort,
wo wir den Bildschirm haben: IM FRONTEND, am markierten Eintrag.

WIR BRINGEN KEINEN EIGENEN BETRACHTER MIT - und das ist der Kern der
Loesung. MiSTers Help-Funktion rendert PDFs nicht im Main-Binary,
sondern mit EIGENEN Programmen auf der Karte, und die zeichnen in
denselben Linux-Framebuffer wie wir:

    /media/fat/linux/pdfviewer   (jfbview 0.6.1, "jfbview [OPTIONS] FILE")
    /media/fat/linux/glow        (Markdown)

Beide kommen mit update_all ("linux"-Filter). AUF DEM GERAET GEPRUEFT,
bevor eine Zeile davon gebaut wurde: der Nutzer hat pdfviewer von Hand
gestartet, das Bild kam, und die Shell kehrte erst nach "q" zurueck -
der Betrachter kommt also mit seinem Kernel zurecht. Dass das Bild
zunaechst nach einer Sekunde wieder verschwand, war unser eigenes
Frontend, das darueber gezeichnet hat; genau dagegen gibt es
_auf_konsole() in frontend.py (derselbe Fehler wie seinerzeit bei
run_script()).

WO DIE DATEIEN LIEGEN - nachgesehen, nicht geraten. Auf dem Geraet des
Nutzers:

    /media/fat/docs/SMS/SMS Manuals/Ace of Aces.pdf   (206 Stueck)

Also: <DOCS_BASE>/<Core>/<irgendein Unterordner>/<Spielname>.pdf. Nicht
direkt im Core-Ordner - deshalb muss gesucht und nicht nur nachgesehen
werden. Dafuer gilt:

  * DER ARTWORK-ORDNER WIRD UEBERSPRUNGEN. Dort liegen bei einer
    gepflegten Sammlung Tausende Bilder; sie bei jeder Suche
    mitzulesen waere genau die Sorte Fehler, die in v1.32 den
    rekursiven Fingerabdruck gekostet hat.
  * EIN os.walk JE SYSTEM, danach gemerkt - wie _art_index() in
    fe/art.py.
  * BEGRENZT in Tiefe und Anzahl: wer sein halbes Archiv dorthin legt,
    soll das Frontend nicht zum Stehen bringen.

GESCHRIEBEN WIRD IN /media/fat/docs NICHTS. Der Ordner gehoert uns
nicht - dieselbe Linie wie bei den Covern seit Build 115.
"""
import os

from fe.art import DOCS_BASE, DOCS_UNTERORDNER, vergleichsname
import fe.systems as SYSTEMS

# Die beiden Betrachter, die MiSTers Help-Funktion selbst benutzt.
PDF_BETRACHTER = "/media/fat/linux/pdfviewer"
TEXT_BETRACHTER = "/media/fat/linux/glow"

# Reihenfolge = Rangfolge. Ein PDF ist die eingescannte Originalanleitung,
# eine Textdatei meist nur eine Notiz daneben.
ENDUNGEN = (".pdf", ".txt", ".md")

# Unterordner, die beim Suchen uebersprungen werden: dort liegt Artwork,
# keine Anleitung. Kleingeschrieben verglichen.
OHNE = frozenset(u.lower() for u in DOCS_UNTERORDNER if u)

# Grenzen. Beide sind da, damit eine ungewoehnlich bestueckte Karte das
# Frontend nicht aufhaelt - und beide stehen hier, statt irgendwo im
# Code zu verschwinden.
MAX_TIEFE = 3
MAX_DATEIEN = 4000

_index_speicher = {}         # syskey -> {vergleichsname: Pfad}


def _ist_anleitung(dateiname):
    endung = os.path.splitext(dateiname)[1].lower()
    return endung in ENDUNGEN


def _eine_wurzel(idx, wurzel, rest):
    """Einen Ordner durchsuchen und die Treffer in idx eintragen.

    HERAUSGELOEST (Build 289), weil es jetzt mehrere Wurzeln gibt -
    eine Schleife um eine Schleife mit try/except darin waere an
    dieser Stelle nur noch schwer zu lesen. Zurueck kommt, wie viele
    Anleitungen gezaehlt wurden; <rest> ist, wieviele noch erlaubt
    sind."""
    gezaehlt = 0
    try:
        for ordner, unterordner, dateien in os.walk(wurzel):
            tiefenrest = ordner[len(wurzel):].strip(os.sep)
            tiefe = len([t for t in tiefenrest.split(os.sep) if t])
            if tiefe >= MAX_TIEFE:
                del unterordner[:]
            # Artwork und seine Geschwister gar nicht erst betreten.
            unterordner[:] = [u for u in unterordner
                              if u.lower() not in OHNE]
            for fn in dateien:
                if not _ist_anleitung(fn):
                    continue
                gezaehlt += 1
                if gezaehlt > rest:
                    break
                # setdefault: der erste Treffer gewinnt, und die
                # Reihenfolge von ENDUNGEN entscheidet nur innerhalb
                # desselben Durchlaufs - deshalb spaeter noch einmal
                # ausdruecklich nach Rang sortiert.
                _eintragen(idx, os.path.splitext(fn)[0],
                           os.path.join(ordner, fn))
            if gezaehlt > rest:
                break
    except OSError:
        pass
    return gezaehlt


def _docs_ordner(syskey):
    """Alle Ordner unter DOCS_BASE, die zu diesem System gehoeren.

    WARUM MEHR ALS EINER (Build 289). Nutzermeldung: "bei den
    megadrive roms fehlen die anleitungen, kann es sein dass falsch in
    den docs ordner nachgeschaut wird? die liegen jetzt unter
    fat/docs/megadrive/Manuals, es gibt aber auch noch den ordner
    fat/docs/Genesis".

    Genau so ist es. Gesucht wurde nur in <DOCS_BASE>/<Systemschluessel>,
    und der heisst bei der Mega Drive "Genesis" (siehe
    fe/systems.py). Seine Anleitungen liegen aber in "megadrive" -
    benannt nach dem ROM-ORDNER, nicht nach unserem internen
    Schluessel. Beides ist vernuenftig; nur unsere Suche kannte den
    halben Namensraum.

    DIE NAMEN STEHEN SCHON IN DER SYSTEMTABELLE: jeder Eintrag bringt
    neben dem Schluessel die Liste seiner ROM-Ordner mit ("MegaDrive",
    "Genesis"). Die wird hier benutzt, statt eine zweite Liste zu
    pflegen - zwei Tabellen fuer dieselbe Zuordnung laufen
    auseinander (die Lehre aus Build 260).

    UND KLEINGESCHRIEBEN VERGLICHEN: sein Ordner heisst "megadrive",
    die Tabelle sagt "MegaDrive". Auf einer FAT-Karte ist das
    dasselbe, in os.path.join nicht.

    Zurueck kommen nur Ordner, die es WIRKLICH gibt, in fester
    Reihenfolge: der Systemschluessel zuerst (bisheriges Verhalten,
    damit sich fuer niemanden etwas verschlechtert), dann die
    ROM-Ordner.

    WAS DAS FUER DREISSIG SYSTEME HEISST: so viele haben mehr als
    einen Namen - meist nur gross/klein geschrieben ("VirtualBoy" neben
    "VIRTUALBOY"), bei einigen aber zwei echte Ordner. Vier TEILEN
    sich einen Ordner mit einem anderen System: FDS mit NES, SG-1000
    mit Coleco und SMS, Atari 2600 mit ATARI7800, WonderSwan Color mit
    WonderSwan. Dort kann ein Spiel mit demselben Namen theoretisch
    die Anleitung des Nachbarn bekommen.

    DAS IST BEWUSST IN KAUF GENOMMEN, und zwar aus einem Grund: wer
    seine FDS-ROMs in games/NES liegen hat, hat die Anleitung mit
    grosser Wahrscheinlichkeit daneben gelegt - und zwei Spiele
    verschiedener Systeme mit identischem Namen UND Anleitung sind
    selten. Ein Treffer am falschen Nachbarn ist ausserdem leichter zu
    bemerken und zu beheben als eine Anleitung, die gar nicht
    erscheint; der Ordner mit dem Systemschluessel behaelt den
    Vortritt, man kann es also jederzeit uebersteuern.

    Ein Name MIT Schraegstrich (z.B. "SNES/SMW_HACKS") taucht in
    os.listdir(DOCS_BASE) nie auf und faellt damit von selbst weg -
    das ist richtig so, denn gemeint ist dort ein Unterordner der
    ROM-Ablage und keine Doku-Wurzel."""
    if not syskey:
        return []
    namen = [syskey]
    try:
        for eintrag in SYSTEMS.alle_systeme():
            if eintrag[1] != syskey:
                continue
            for ordner in (eintrag[2] or ()):
                if ordner and ordner not in namen:
                    namen.append(ordner)
    except Exception:                                    # noqa: BLE001
        pass
    # Was liegt wirklich da? Einmal lesen, kleingeschrieben vergleichen.
    vorhanden = {}
    try:
        for name in os.listdir(DOCS_BASE):
            vorhanden.setdefault(name.lower(), name)
    except OSError:
        return []
    treffer = []
    for name in namen:
        echt = vorhanden.get(name.lower())
        if echt:
            pfad = os.path.join(DOCS_BASE, echt)
            if pfad not in treffer and os.path.isdir(pfad):
                treffer.append(pfad)
    return treffer


def _index(syskey):
    """{Vergleichsname: Pfad} fuer ein System - einmal gesucht, dann
    gemerkt.

    Gefunden wird unter EXAKTEM Namen und unter dem unscharfen
    Vergleichsnamen (siehe vergleichsname() in fe/art.py, Build 117):
    die Anleitung heisst "Ace of Aces.pdf", die ROM
    "Ace of Aces (Europe).sms". Ohne den unscharfen Vergleich faende
    man auf einer echten Karte fast nichts."""
    if not syskey:
        return {}
    fertig = _index_speicher.get(syskey)
    if fertig is not None:
        return fertig
    idx = {}
    # MEHRERE WURZELN (Build 289) - siehe _docs_ordner(). Die
    # Zaehlgrenze MAX_DATEIEN gilt weiter fuer ALLE zusammen: sie ist
    # da, damit eine ungewoehnlich bestueckte Karte das Frontend nicht
    # aufhaelt, und das aendert sich nicht dadurch, dass die Dateien
    # auf zwei Ordner verteilt sind.
    gezaehlt = 0
    for wurzel in _docs_ordner(syskey):
        gezaehlt += _eine_wurzel(idx, wurzel, MAX_DATEIEN - gezaehlt)
        if gezaehlt >= MAX_DATEIEN:
            break
    _index_speicher[syskey] = idx
    return idx


def _rang(pfad):
    endung = os.path.splitext(pfad)[1].lower()
    return ENDUNGEN.index(endung) if endung in ENDUNGEN else len(ENDUNGEN)


def _eintragen(idx, stamm, pfad):
    for schluessel in (stamm, vergleichsname(stamm)):
        if not schluessel:
            continue
        vorher = idx.get(schluessel)
        if vorher is None or _rang(pfad) < _rang(vorher):
            idx[schluessel] = pfad


def vergessen(syskey=None):
    """Den gemerkten Stand verwerfen - nach einem Neueinlesen, oder
    wenn jemand Anleitungen dazugelegt hat."""
    if syskey is None:
        _index_speicher.clear()
    else:
        _index_speicher.pop(syskey, None)


def anleitung_finden(syskey, rom_basename):
    """Der Pfad zur Anleitung dieses Spiels - oder None.

    Erst der exakte Name, dann der unscharfe Vergleich. Dieselbe
    Rangfolge wie bei den Covern, und aus demselben Grund: was genau
    passt, soll gewinnen."""
    if not syskey or not rom_basename:
        return None
    idx = _index(syskey)
    if not idx:
        return None
    treffer = idx.get(rom_basename)
    if treffer is None:
        treffer = idx.get(vergleichsname(rom_basename))
    if treffer and os.path.exists(treffer):
        return treffer
    return None


def betrachter_fuer(pfad):
    """Das Programm, das diese Datei anzeigen kann - oder None, wenn
    es auf diesem Geraet nicht installiert ist."""
    if not pfad:
        return None
    endung = os.path.splitext(pfad)[1].lower()
    prog = PDF_BETRACHTER if endung == ".pdf" else TEXT_BETRACHTER
    return prog if os.path.exists(prog) else None


def befehl(pfad):
    """Die vollstaendige Befehlszeile - oder None.

    ZWEI EINSTELLUNGEN, und beide haben einen Grund.

    "--zoom_to_width": eine Anleitungsseite ist hochkant, der
    Bildschirm quer. Ohne sie startet jfbview in Originalgroesse, und
    man sieht die obere linke Ecke einer Seite.

    "--cache_size=1" (Build 267): NUTZERMELDUNG "wenn ich jetzt durch
    eine Anleitung blaettere, haengt sich das Frontend nach ein paar
    Seiten auf". Das Protokoll zeigt den Betrachter gestartet und
    danach NICHTS mehr - kein Rueckgabewert, also kein Absturz,
    sondern ein Prozess, der nicht mehr fertig wird.

    "Nach ein paar Seiten" ist dabei der entscheidende Hinweis: das
    Einzige, was mit jeder Seite WAECHST, ist der Seitenspeicher.
    jfbviews eigene Hilfe schreibt dazu woertlich: "Cache at most N
    pages. If you have an older machine with limited RAM, or if you
    are loading huge documents ... you might want to set this to a
    smaller number." Ein DE10-Nano mit 1 GB und eingescannten
    Anleitungen auf 1920x1080 ist genau diese Maschine. Mit 1 bleibt
    der Verbrauch flach; der Preis ist, dass eine zurueckgeblaetterte
    Seite neu gezeichnet wird.

    GERATEN IST DARAN NICHTS AUSSER DER URSACHE: dass es der Speicher
    IST, ist noch nicht gemessen (dafuer braucht es dmesg/free vom
    Geraet). Die Einstellung ist aber unabhaengig davon richtig - sie
    steht so in der Hilfe des Programms."""
    prog = betrachter_fuer(pfad)
    if not prog:
        return None
    if prog == PDF_BETRACHTER:
        return [prog, "--zoom_to_width", "--cache_size=1", pfad]
    return [prog, "-p", pfad]


def hat_anleitung(syskey, rom_basename):
    """Gibt es etwas zu zeigen UND etwas, womit man es zeigen kann?

    Beides zusammen, weil der Menuepunkt sonst erscheint und dann
    nichts tut - ein toter Eintrag ist schlimmer als keiner."""
    pfad = anleitung_finden(syskey, rom_basename)
    return bool(pfad) and betrachter_fuer(pfad) is not None
