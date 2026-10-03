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

import fe.dateibaum as BAUM
from fe.log import LOG

MASKEN_DIR = "/media/fat/Shadow_Masks"

# MiSTers eigene Videovorlagen. Siehe preset_masken() - uns interessiert
# daran genau eine Zeile.
PRESETS_DIR = "/media/fat/Presets"

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


def masken_eintraege(unterordner="", wurzel=None):
    """EINE Ebene des Maskenbaums - siehe fe/dateibaum.py.

    NACHGEREICHT IN BUILD 227, auf Zuruf des Nutzers: "lochmasken in
    unterordner anzeigen sonst zuviel auswahl, die ordnerstruktur wie
    sie dort selbst angezeigt ist". MiSTers Sammlung ist selbst schon
    sortiert ("Complex (Multichromatic)/CRT Styles/..."), und diese
    Ordnung ist die Arbeit von jemandem, der die Masken kennt - wir
    bauen sie nicht nach, wir zeigen sie.

    SEIT BUILD 228 steht das Blaettern in fe/dateibaum.py, weil die
    Schriften es genauso machen."""
    return BAUM.eintraege(wurzel or MASKEN_DIR, unterordner, ".txt")


def preset_masken(presets=None, wurzel=None):
    """Welche Maske steckt in welchem MiSTer-PRESET? (Build 227)

    NACHGESCHAUT AUF ZURUF DES NUTZERS: "die sachen dafuer liegen in
    ordner /media/fat/Presets einmal nachschauen bitte".

    Und dort liegt tatsaechlich etwas fuer uns. Ein Preset ist eine
    winzige INI, die einen ganzen Satz Videoeinstellungen auf einmal
    setzt (MiSTer-devel/Presets_MiSTer):

        hfilter=Upscaling - Lanczos Bicubic etc/lanczos2_10.txt
        vfilter=same
        gamma=off
        mask=Complex (Multichromatic)/CRT Styles/Sony PVM.txt
        maskmode=1x

    Die Filterzeilen sind fuer MiSTers Scaler und fuer uns ohne Sinn -
    wir skalieren nichts, wir zeichnen gleich in der Groesse des
    Bildschirms. Die Zeile "mask=" dagegen nennt GENAU eine Datei aus
    /media/fat/Shadow_Masks, also genau das, was Build 226 lesen kann.

    DAS IST DER GEWINN: ein Preset ist eine von Hand zusammengestellte
    Empfehlung mit einem Namen, den jemand vergeben hat, der sich damit
    auskennt. Wer nicht durch 1207 Masken blaettern will, nimmt eine
    davon - und das ist dieselbe Antwort, die auch MiSTers eigenes OSD
    gibt.

    Rueckgabe: Liste von (presetname, relativer Maskenpfad), nach Namen
    sortiert. Presets ohne Maske ("off", "same", fehlende Zeile) und
    solche, deren Maske nicht auf der Karte liegt, fallen weg: ein
    Eintrag, der beim Druecken nichts tut, ist schlimmer als keiner."""
    presets = presets or PRESETS_DIR
    wurzel = wurzel or MASKEN_DIR
    gefunden = []
    try:
        namen = sorted(os.listdir(presets))
    except OSError:
        return []
    for name in namen:
        if not name.lower().endswith(".ini"):
            continue
        wert = _preset_maske(os.path.join(presets, name))
        if not wert:
            continue
        # Manche Presets schreiben den Ordner mit davor - beides gelten
        # lassen ist eine Zeile und erspart ein Raetsel.
        for kandidat in (wert, wert.split("Shadow_Masks/", 1)[-1]):
            voll = os.path.join(wurzel, kandidat)
            if os.path.isfile(voll):
                gefunden.append((os.path.splitext(name)[0], kandidat))
                break
    gefunden.sort(key=lambda e: e[0].lower())
    return gefunden


def _preset_maske(pfad):
    """Die Zeile "mask=" einer Preset-INI - oder None."""
    try:
        with open(pfad, encoding="utf-8", errors="replace") as f:
            for roh in f:
                z = roh.strip()
                if not z or z[0] in "#;[":
                    continue
                if "=" not in z:
                    continue
                schluessel, wert = z.split("=", 1)
                if schluessel.strip().lower() != "mask":
                    continue
                wert = wert.strip().strip('"')
                if not wert or wert.lower() in ("off", "same", "none"):
                    return None
                return wert
    except OSError:
        return None
    return None


def oberordner(unterordner):
    """Eine Ebene hoeher - "" ist die Wurzel und das Ende des Weges."""
    return BAUM.oberordner(unterordner)


# Die Presets sind eine Ebene, die es als Ordner nicht gibt.
PRESET_EBENE = BAUM.VIRTUELL + "presets"


def ebene(ordner="", texte=None, wurzel=None, presets=None):
    """Die sichtbare Liste EINER Ebene - fertig zum Hinmalen.

    HIER UND NICHT IM BILDSCHIRM, weil das die Logik ist, die man
    pruefen will: was steht oben, was ist ein Weg nach unten, was ist
    der Weg zurueck. Der Bildschirm soll nur noch zeichnen.

    texte: {"zurueck": .., "keine": .., "presets": .., "modus": ..} -
    die uebersetzten Beschriftungen. Uebersetzen tut dieses Modul nicht.

    Rueckgabe: Liste von (art, anzeige, rel). Zu den Arten aus
    fe/dateibaum.py ("hoch", "ordner", "datei") kommen hier drei eigene:

        "keine"   - keine Maske (steht nur AUF der Wurzel)
        "modus"   - 1x / 2x / gedreht (dito)
        "presets" - MiSTers Empfehlungen (nur, wenn es welche gibt)
    """
    texte = texte or {}
    if ordner == PRESET_EBENE:
        liste = [("hoch", ".. %s" % texte.get("zurueck", "zurueck"), "")]
        for name, rel in preset_masken(presets, wurzel):
            liste.append(("datei", name, rel))
        return liste

    kopf = [("keine", texte.get("keine", "keine"), "")]
    # NEU (Build 228): der Modus. Eigene Zeile und nicht eine weitere
    # Taste, weil die Seite schon vier Tasten belegt - und weil man den
    # Unterschied zwischen 1x und 2x nur SIEHT, also beim Drehen an der
    # Zeile die Vorschau danebenhaben will.
    if texte.get("modus"):
        kopf.append(("modus", texte["modus"], ""))
    # GANZ OBEN, weil es die kuerzeste Antwort auf "zuviel Auswahl"
    # ist: ein Preset ist eine fertige Empfehlung mit Namen,
    # zusammengestellt von jemandem, der die Masken kennt. Liegt nichts
    # in /media/fat/Presets, steht die Zeile auch nicht da.
    anzahl = len(preset_masken(presets, wurzel))
    if anzahl:
        kopf.append(("presets", "%s   (%d)"
                     % (texte.get("presets", "Presets"), anzahl),
                     PRESET_EBENE))
    return BAUM.zeilen(wurzel or MASKEN_DIR, ordner, ".txt", texte, kopf)


# ===========================================================================
# DIE VIER MODI (Build 228)
# ===========================================================================
#
# ZURUF DES NUTZERS: "bei denn masken ist mir noch aufgefallen das man
# mehrere optionen hat shadow mask 1x, shadow mask 2x, shadow mask 1x
# rotated und shadow mask 2x rotated, kriegen wir das auch noch mit
# eingebracht?"
#
# Das sind MiSTers eigene vier Einstellungen (in einer Preset-INI steht
# dasselbe als "maskmode="), und beide sind reine UMFORMUNGEN des
# Musters:
#
#   2x       - jede Zelle deckt 2x2 Bildpunkte statt einem. Auf 1080p
#              ist eine 1x-Maske so fein, dass man sie kaum sieht; 2x
#              ist das, was auf einem grossen Bild nach Lochmaske
#              aussieht.
#   gedreht  - das Muster um 90 Grad gekippt. Gedacht fuer hochkant
#              stehende Bildschirme, aber auch sonst ein anderer Look:
#              aus senkrechten Streifen werden waagerechte.
#
# WARUM DAS NICHTS KOSTET: beides passiert EINMAL beim Laden der Maske,
# nicht je Bildpunkt. Danach liegt wieder nur eine Tabelle da, und C
# rechnet genau wie vorher. Eine 16x16-Maske wird in 2x zu 32x32 - die
# C-Fassung nimmt bis 64x64, da ist Luft.
MODI = ("1x", "2x", "1x_gedreht", "2x_gedreht")
MODUS_FILE = "/media/fat/frontend/maske_modus"


def modus_lesen():
    """Der eingestellte Modus - immer einer aus MODI."""
    try:
        wert = open(MODUS_FILE).read().strip()
    except OSError:
        return MODI[0]
    return wert if wert in MODI else MODI[0]


def modus_schreiben(wert):
    if wert not in MODI:
        wert = MODI[0]
    try:
        d = os.path.dirname(MODUS_FILE)
        if d:
            os.makedirs(d, exist_ok=True)
        with open(MODUS_FILE, "w") as f:
            f.write(wert)
    except OSError as e:
        LOG("modus_schreiben: %s" % e)
    return wert


def modus_weiter(jetzt, rueckwaerts=False):
    """Einen Modus weiterschalten (rundum)."""
    try:
        i = MODI.index(jetzt)
    except ValueError:
        i = 0
    return MODI[(i - 1 if rueckwaerts else i + 1) % len(MODI)]


def _gedreht(maske):
    """Das Muster um 90 Grad kippen - aus (b,h) wird (h,b).

    neu[y][x] = alt[x][y]. Die Kanalreihenfolge bleibt: gedreht wird
    das MUSTER, nicht die Farbe."""
    b, h, werte = maske[0], maske[1], maske[2]
    neu = []
    for x in range(b):                       # neue Zeilen = alte Spalten
        for y in range(h):                   # neue Spalten = alte Zeilen
            i = (y * b + x) * 3
            neu.extend(werte[i:i + 3])
    return (h, b, neu) + tuple(maske[3:])


def _verdoppelt(maske):
    """Jede Zelle auf 2x2 aufblasen - aus (b,h) wird (2b,2h)."""
    b, h, werte = maske[0], maske[1], maske[2]
    neu = []
    for y in range(h):
        zeile = []
        for x in range(b):
            i = (y * b + x) * 3
            zelle = werte[i:i + 3]
            zeile.extend(zelle)
            zeile.extend(zelle)
        neu.extend(zeile)
        neu.extend(zeile)                    # dieselbe Zeile zweimal
    return (b * 2, h * 2, neu) + tuple(maske[3:])


def modus_anwenden(maske, modus):
    """Die Umformung auf eine gelesene Maske anwenden.

    Reihenfolge: erst drehen, dann verdoppeln. Andersherum kaeme
    dasselbe heraus - gedreht wird ein Quadrat aus vier gleichen Zellen
    zu einem Quadrat aus vier gleichen Zellen -, aber eine feste
    Reihenfolge erspart die Frage."""
    if not maske or modus == MODI[0]:
        return maske
    if "gedreht" in modus:
        maske = _gedreht(maske)
    if modus.startswith("2x"):
        maske = _verdoppelt(maske)
    return maske


def maske_fuer(pfad, bildhoehe=None, modus=None):
    """Lesen mit Protokollzeile - der Weg, den das Frontend nimmt.

    modus: einer aus MODI, oder None fuer den eingestellten."""
    if not pfad:
        return None
    m = maske_lesen(pfad, bildhoehe)
    if m is None:
        LOG("Maske %r nicht lesbar - zeichne ohne" % pfad)
        return None
    if ist_neutral(m):
        LOG("Maske %r veraendert nichts - zeichne ohne" % pfad)
        return None
    if modus is None:
        modus = modus_lesen()
    roh = (m[0], m[1])
    m = modus_anwenden(m, modus)
    if roh == (m[0], m[1]):
        LOG("Maske geladen: %s (%dx%d)" % (m[4], m[0], m[1]))
    else:
        LOG("Maske geladen: %s (%dx%d aus %dx%d, %s)"
            % (m[4], m[0], m[1], roh[0], roh[1], modus))
    return m
