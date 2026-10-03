# -*- coding: utf-8 -*-
"""MiSTers eigene Shadow Masks - gelesen, nicht mitgeliefert (Build 226).

WUNSCH DES NUTZERS: "Masken vom Mister selbst benutzen, bitte mit eigener
Kategorie unter System, mit Auswahl und an und aus Schalter".

Dieselbe Haltung wie bei den Schriften aus Build 223 und bei der fremden
Artwork-Datenbank: die Dateien liegen auf SEINER Karte, wir lesen sie
nur. Dieses Paket enthaelt keine einzige Maskendatei.

WAS EINE MASKE IST. MiSTers Scaler legt ueber das Bild ein kleines, sich
wiederholendes Muster, das eine Lochmaske oder Streifenmaske nachahmt -
je Bildpunkt wird jeder Farbkanal entweder angehoben oder abgesenkt. Die
Muster stehen als Textdateien in /media/fat/Shadow_Masks, bis 16x16
Punkte gross.

DAS FORMAT (MiSTer-devel/ShadowMasks_MiSTer, Abschnitt "Specifications"):

    ####
    # Name: GRBG (Green)
    # Author: Tonurics
    ####

    Resolution=0
    v2
    4,4
    21d,42a,12a,21d
    ...

Jede Zelle sind DREI Hexziffern "FIO":

    F = welche Kanaele "an" sind, als Bitmaske
        1 = Blau, 2 = Gruen, 4 = Rot
        (0 = Grau, also keiner an; 7 = Weiss, alle an)
    I = Staerke fuer die ANGESCHALTETEN Kanaele:  (16 + I) / 16
        also 0 -> 100 %, f -> 193,75 %
    O = Staerke fuer die ABGESCHALTETEN Kanaele:  O / 16
        also 0 -> 0 %, f -> 93,75 %

"Resolution=0" heisst "fuer jede Hoehe gedacht"; eine andere Zahl nennt
die Bildhoehe, fuer die das Muster entworfen wurde. Wir lesen den Wert,
benutzen ihn aber nur als Hinweis in der Auswahl - abgelehnt wird
deswegen nichts, denn ob ein Muster gefaellt, entscheidet das Auge und
nicht eine Zahl in der Kopfzeile.

ALLES, WAS HIER SCHIEFGEHEN KANN, ENDET IN None. Eine Maskendatei ist
Zubehoer; eine kaputte darf das Frontend nicht aufhalten.
"""
import os

from fe.log import LOG

MASKEN_DIR = "/media/fat/Shadow_Masks"

# Groesser laesst MiSTer sie nicht zu, und wir auch nicht: das Muster
# wird je Bildpunkt ausgewertet und gehoert deshalb in den Cache des
# Prozessors.
MAX_KANTE = 16


def _zelle(text):
    """Eine Zelle "FIO" in drei Faktoren (Rot, Gruen, Blau) umrechnen.

    Rueckgabe in SECHZEHNTELN - also 16 = unveraendert, 32 = doppelt so
    hell, 0 = aus. Ganzzahlen, damit C ohne Fliesskomma auskommt."""
    text = text.strip().lower()
    if len(text) != 3:
        return None
    try:
        f = int(text[0], 16)
        i = int(text[1], 16)
        o = int(text[2], 16)
    except ValueError:
        return None
    if f > 7:
        return None
    an = 16 + i                      # 16/16 bis 31/16
    aus = o                          # 0/16 bis 15/16
    return (an if (f & 4) else aus,  # Rot
            an if (f & 2) else aus,  # Gruen
            an if (f & 1) else aus)  # Blau


def _bloecke(zeilen):
    """Eine Maskendatei in ihre BLOECKE zerlegen.

    EINE DATEI KANN MEHRERE MUSTER ENTHALTEN, und das war beim Bauen die
    Ueberraschung: 106 von 1207 Dateien der MiSTer-Sammlung haben
    mehrere, jeweils mit eigener Zeile "Resolution=". Ein Leser, der nur
    den ersten Block kennt, stolpert ueber den zweiten und wirft die
    ganze Datei weg - genau das ist passiert, und zwar ausgerechnet bei
    den aufwendigsten Masken (Sony PVM, Commodore 1084, Mitsubishi).

    Die Zeile "Resolution=" steht VOR ihrem Block; ein Block ohne sie
    gilt fuer jede Hoehe (0).

    Rueckgabe: Liste von (aufloesung, breite, hoehe, flache Faktoren).
    """
    bloecke = []
    naechste_aufloesung = 0
    masse = None
    daten = []
    aktuelle_aufloesung = 0

    def _abschliessen():
        if masse is not None and len(daten) == masse[1]:
            flach = []
            for reihe in daten:
                flach.extend(reihe)
            bloecke.append((aktuelle_aufloesung, masse[0], masse[1], flach))

    for roh in zeilen:
        z = roh.strip()
        if not z or z.startswith("#"):
            continue
        if z.lower().startswith("resolution="):
            _abschliessen()
            masse, daten = None, []
            try:
                naechste_aufloesung = int(z.split("=", 1)[1].strip())
            except ValueError:
                naechste_aufloesung = 0
            continue
        if z.lower() in ("v1", "v2"):
            # Ein "v2" OHNE vorangehendes Resolution= beginnt ebenfalls
            # einen neuen Block (so sehen die mehrteiligen Dateien aus).
            if masse is not None:
                _abschliessen()
                masse, daten = None, []
            aktuelle_aufloesung = naechste_aufloesung
            naechste_aufloesung = 0
            continue
        if masse is None and len(z.split(",")) == 2:
            try:
                b, h = (int(t.strip()) for t in z.split(","))
            except ValueError:
                return []
            if not (1 <= b <= MAX_KANTE and 1 <= h <= MAX_KANTE):
                return []
            masse = (b, h)
            continue
        if masse is None:
            continue
        reihe = []
        for t in (x for x in z.split(",") if x.strip()):
            w = _zelle(t)
            if w is None:
                return []
            reihe.extend(w)
        if len(reihe) != masse[0] * 3:
            return []
        daten.append(reihe)
    _abschliessen()
    return bloecke


def maske_lesen(pfad, bildhoehe=None):
    """Eine .txt-Maske lesen.

    bildhoehe waehlt unter mehreren Bloecken aus: zuerst der, dessen
    "Resolution=" genau passt, sonst der mit 0 ("fuer jede Hoehe"),
    sonst der erste. Mehr Auswahl waere geraten - welche Aufloesung ein
    Muster meint, steht nur in dieser Zahl.

    Rueckgabe: (breite, hoehe, faktoren, aufloesung, name) - faktoren ist
    eine flache Liste aus breite*hoehe*3 Ganzzahlen in Sechzehnteln,
    zeilenweise, je Zelle Rot/Gruen/Blau. None bei jedem Fehler."""
    try:
        with open(pfad, encoding="utf-8", errors="replace") as f:
            zeilen = f.read().splitlines()
    except OSError:
        return None
    bloecke = _bloecke(zeilen)
    if not bloecke:
        return None
    gewaehlt = None
    if bildhoehe:
        for b in bloecke:
            if b[0] == bildhoehe:
                gewaehlt = b
                break
    if gewaehlt is None:
        for b in bloecke:
            if b[0] == 0:
                gewaehlt = b
                break
    if gewaehlt is None:
        gewaehlt = bloecke[0]
    name = os.path.splitext(os.path.basename(pfad))[0]
    return (gewaehlt[1], gewaehlt[2], gewaehlt[3], gewaehlt[0], name)


def ist_neutral(maske):
    """Aendert diese Maske ueberhaupt etwas?

    Eine Maske, in der jede Zelle auf 16/16 steht, laesst das Bild wie es
    ist - dann lohnt der Aufwand nicht und wir lassen sie weg. Kommt in
    der Sammlung nicht vor, kostet aber eine Zeile und erspart im
    Zweifel eine ganze Rechnung je Bildpunkt."""
    if not maske:
        return True
    return all(w == 16 for w in maske[2])


def masken_dateien(wurzel=None):
    """Alle .txt-Masken unter MASKEN_DIR, sortiert.

    Rueckgabe: Liste von (anzeigename, vollpfad). MiSTers Sammlung legt
    sie in Unterordnern ab ("Complex (Multichromatic)/CRT Styles/..."),
    deshalb wird der Baum durchlaufen und der Unterordner in den Namen
    aufgenommen - sonst stuenden drei gleichnamige Eintraege
    nebeneinander."""
    wurzel = wurzel or MASKEN_DIR
    gefunden = []
    try:
        for ordner, _unter, dateien in os.walk(wurzel):
            for d in dateien:
                if not d.lower().endswith(".txt"):
                    continue
                voll = os.path.join(ordner, d)
                rel = os.path.relpath(voll, wurzel)
                anzeige = os.path.splitext(rel)[0].replace(os.sep, " / ")
                gefunden.append((anzeige, voll))
    except OSError:
        return []
    gefunden.sort(key=lambda e: e[0].lower())
    return gefunden


def maske_fuer(pfad, bildhoehe=None):
    """Lesen mit Protokollzeile - der Weg, den das Frontend nimmt."""
    if not pfad:
        return None
    m = maske_lesen(pfad, bildhoehe)
    if m is None:
        LOG("Maske %r nicht lesbar - zeichne ohne" % pfad)
        return None
    if ist_neutral(m):
        LOG("Maske %r veraendert nichts - zeichne ohne" % pfad)
        return None
    LOG("Maske geladen: %s (%dx%d)" % (m[4], m[0], m[1]))
    return m
