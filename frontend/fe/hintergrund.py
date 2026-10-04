# -*- coding: utf-8 -*-
"""Ein eigenes Hintergrundbild statt der einfarbigen Flaeche (Build 235).

WUNSCH DES NUTZERS: "wie aufwendig ist es ein background bild zu
integrieren? das benutzer ihr gewuenschtes background bild selbst in
einen ordner legen koennen und dieses statt jetzt schwarzen hintergrund
dann hier background bild an und ausschalten koennen ... die performence
soll dadurch aber nicht beeintraechtigt werden!"

DIE ANTWORT AUF DIE PERFORMANCE-FRAGE STEHT IM ZEICHENWEG SELBST, und
sie ist ueberraschend gut: fb.clear() kopiert SCHON HEUTE einen
Vollbildpuffer. Die einfarbige Flaeche ist naemlich gar nicht einfarbig
- sie traegt die Vignette (die dezente Randabdunkelung), und deshalb
liegt im _rowcache bereits ein fertiges Bild in Bildschirmgroesse, das
bei jedem clear() hineinkopiert wird. Dasselbe gilt fuer
_restore_row_bg() und _bg_fill(), die beim Scrollen Zeilen daraus
herausholen.

Was in diesem Puffer steht, ist dem Kopieren egal. Nachgemessen:

    clear mit Farbvorlage   0,680 ms
    clear mit Bildvorlage   0,667 ms

Also kein Unterschied - der Rest ist Rauschen. Ein Hintergrundbild
kostet im Zeichenweg NICHTS; es kostet einmal beim Laden.

WAS ES WIRKLICH KOSTET, und das wird hier auch nicht verschwiegen:
  - einmal Dekodieren und Skalieren beim Start oder beim Umschalten
  - keinen zusaetzlichen Speicher: der Vollbildpuffer existiert ohnehin

MITGELIEFERT WIRD KEIN BILD. Gelesen wird, was der Nutzer in seinen
Ordner legt - dieselbe Haltung wie bei Masken und Schriften.

LESBARKEIT: Text auf einem Foto ist schwer zu lesen. Deshalb gibt es
eine Abdunklung, und sie kostet ebenfalls nichts - sie wird EINMAL in
den Puffer gerechnet, nicht je Bild.
"""
import os

import fe.dateibaum as BAUM
from fe.log import LOG

HINTERGRUND_DIR = "/media/fat/frontend/backgrounds"

# Welche Formate der Bildleser kann - dieselben wie beim Artwork.
ENDUNGEN = (".png", ".jpg", ".jpeg")

# Abdunklung in Stufen. 0 = Bild unveraendert, 100 = schwarz. Vier
# Stufen statt eines Reglers: mehr Auswahl waere mehr Bedienung fuer
# dieselbe Frage ("kann ich den Text noch lesen?").
DIM_STUFEN = (0, 25, 40, 55, 70)


def hintergrund_eintraege(unterordner="", wurzel=None):
    """EINE Ebene des Bilderbaums - siehe fe/dateibaum.py.

    Gesucht wird nach .png; die uebrigen Endungen kommen dazu, weil
    fe/dateibaum.py je Aufruf genau eine kennt. Das ist eine Schleife
    und kein Sonderweg: zusammengefuehrt wird hier."""
    wurzel = wurzel or HINTERGRUND_DIR
    zusammen = {}
    for endung in ENDUNGEN:
        for e in BAUM.eintraege(wurzel, unterordner, endung):
            # Ordner kommen bei jeder Endung vor - ihre Anzahl ist je
            # Endung gezaehlt und muss addiert werden.
            vorher = zusammen.get(e[2])
            if vorher is None:
                zusammen[e[2]] = list(e)
            elif e[0]:
                vorher[3] += e[3]
    ordner = sorted((v for v in zusammen.values() if v[0]),
                    key=lambda v: v[1].lower())
    dateien = sorted((v for v in zusammen.values() if not v[0]),
                     key=lambda v: v[1].lower())
    return [tuple(v) for v in ordner + dateien if v[0] or v[3] == 0]


def oberordner(unterordner):
    return BAUM.oberordner(unterordner)


def ebene(ordner="", texte=None, wurzel=None):
    """Die sichtbare Liste EINER Ebene - fertig zum Hinmalen.

    Arten: "hoch", "keine", "ordner", "datei" - wie bei den Masken."""
    texte = texte or {}
    if ordner:
        liste = [("hoch", ".. %s" % texte.get("zurueck", "zurueck"), "")]
    else:
        liste = [("keine", texte.get("keine", "keiner"), "")]
    for ist_ordner, name, rel, n in hintergrund_eintraege(ordner, wurzel):
        if ist_ordner:
            liste.append(("ordner", "%s/   (%d)" % (name, n), rel))
        else:
            liste.append(("datei", name, rel))
    return liste


def zaehlen(wurzel=None):
    """Wieviele Bilder liegen insgesamt da?"""
    wurzel = wurzel or HINTERGRUND_DIR
    return sum(BAUM.zaehlen(wurzel, e) for e in ENDUNGEN)


def _fuellend(qb, qh, zb, zh):
    """Die Groesse, in der das Bild den Bildschirm FUELLT.

    Ein Hintergrund soll keine Balken haben - also wird so skaliert,
    dass beide Kanten mindestens die Bildschirmgroesse erreichen, und
    der Ueberstand wird mittig abgeschnitten. Das ist die Rechnung, die
    jeder Fernseher "Vollbild" nennt."""
    if qb <= 0 or qh <= 0:
        return zb, zh
    # Ganzzahlig aufrunden, damit nie eine Zeile oder Spalte fehlt.
    b1 = zb
    h1 = (qh * zb + qb - 1) // qb
    if h1 >= zh:
        return b1, h1
    h2 = zh
    b2 = (qb * zh + qh - 1) // qh
    return b2, h2


def _abdunkeln(pix, prozent):
    """Das fertige Bild EINMAL abdunkeln - nicht je Bildaufbau.

    Ueber eine Tabelle mit 256 Werten, genau wie bei der Lochmaske.

    GEAENDERT (Build 240), auf Meldung vom Geraet: "wenn ich mehrere
    background bilder in denn ordner packe und diese dann durchklicke
    dauert das immer sehr lang bis es angezeigt wird."

    HIER STAND DIE URSACHE, und zwar als einzige von Bedeutung.
    tools/diag_hintergrundbild.py hat den Weg in seine Teile zerlegt:

        skalieren      0 bis 26 ms
        zuschneiden    2 bis  5 ms
        abdunkeln    214 bis 233 ms   <- 90 bis 98 Prozent

    DER GRUND WAR DIE SCHREIBWEISE, nicht die Idee. Hier stand dreimal
    "bytes(tab[b] for b in aus[k::4])" - ein Generator, also eine
    PYTHON-Schleife ueber jedes Byte. Bei 1920x1080 sind das 8,3
    Millionen Bytes, davon drei Viertel angefasst. Auf dem DE10-Nano
    ist Rechnen je Bildpunkt ein Vielfaches teurer; das waren die
    Sekunden, die gemeldet wurden.

    bytes.translate() macht genau dasselbe - eine Tabelle mit 256
    Werten auf jedes Byte anwenden - aber in C, in einer Schleife, die
    nie in den Interpreter zurueckkehrt. Gemessen 14,6-mal schneller
    (214 -> 15 ms), und das Ergebnis ist BITGENAU dasselbe.

    Der Schnitt [k::4] bleibt, damit die Deckkraft im vierten Byte
    unangetastet bleibt; Herausziehen, Uebersetzen und Zurueckschreiben
    sind alle drei C-Schritte.

    GLEICHWERTIGKEIT IST HIER NICHT VERHANDELBAR: ein Unterschied
    faellt nicht auf, das Bild sieht nur etwas anders aus.
    tools/test_hintergrund.py vergleicht deshalb gegen die alte
    Schreibweise, nicht gegen eine Erwartung - ueber alle Stufen und
    alle 256 Bytewerte."""
    if not prozent:
        return pix
    f = max(0, min(100, int(prozent)))
    tab = bytes(bytearray(((i * (100 - f)) // 100) for i in range(256)))
    aus = bytearray(pix)
    # Nur die drei Farbkanaele, nicht das vierte Byte - dort steht die
    # Deckkraft, und die bleibt.
    for k in range(3):
        aus[k::4] = bytes(aus[k::4]).translate(tab)
    return aus


def vorlage_bauen(pfad, breite, hoehe, dim=0, ART=None, stride=None):
    """Ein Bild zu einer fertigen Bildschirmvorlage machen.

    Rueckgabe: bytearray in der Form, die fb._rowcache erwartet -
    hoehe Zeilen zu je stride Byte (BGRA). Ohne stride dicht gepackt.

    Die Schrittweite gehoert hierher und nicht in den Aufrufer: die
    Vorlage wird am Stueck in den Puffer kopiert (fb.clear macht
    buf[:] = bg), und eine Vorlage mit falscher Schrittweite
    verschoebe das ganze Bild.

    ALLES, WAS SCHIEFGEHEN KANN, ENDET IN None. Ein Hintergrundbild ist
    Zubehoer; ein kaputtes darf das Frontend nicht aufhalten.

    DIE TEILZEITEN STEHEN IM LOG (Build 240), und das hat einen
    Grund. Nach der Aenderung an _abdunkeln() ist der groesste Posten
    das DEKODIEREN der Datei, und das ist der einzige, den dieses
    Modul nicht in der Hand hat - er haengt am Format, an der Groesse
    und an der Karte. Ohne Zahl vom Geraet waere jeder weitere Schritt
    geraten. Eine Zeile je Bildwechsel kostet nichts: sie laeuft genau
    dann, wenn ohnehin ein Bild geladen wird."""
    if not pfad or ART is None:
        return None
    import time as _t
    _t0 = _t.monotonic()
    try:
        gelesen = ART.original_lesen(pfad, breite, hoehe)
    except Exception as e:                               # noqa: BLE001
        LOG("Hintergrund %r nicht lesbar (%s)" % (pfad, e))
        return None
    if not gelesen:
        LOG("Hintergrund %r nicht lesbar" % pfad)
        return None
    _ms_lesen = (_t.monotonic() - _t0) * 1000.0
    qb, qh, pix = gelesen[0], gelesen[1], gelesen[2]
    zb, zh = _fuellend(qb, qh, breite, hoehe)
    _t1 = _t.monotonic()
    try:
        if (zb, zh) != (qb, qh):
            pix = ART._verkleinern(pix, qb, qh, zb, zh)
            qb, qh = zb, zh
    except Exception as e:                               # noqa: BLE001
        LOG("Hintergrund %r nicht skalierbar (%s)" % (pfad, e))
        return None
    if qb < breite or qh < hoehe:
        LOG("Hintergrund %r zu klein nach dem Skalieren (%dx%d)"
            % (pfad, qb, qh))
        return None

    _ms_skalieren = (_t.monotonic() - _t1) * 1000.0

    # Mittig zuschneiden - der Ueberstand faellt links/rechts bzw.
    # oben/unten gleichmaessig weg.
    _t2 = _t.monotonic()
    x0 = (qb - breite) // 2
    y0 = (qh - hoehe) // 2
    zeile = breite * 4
    schritt = int(stride or zeile)
    if schritt < zeile:
        schritt = zeile
    quelle = memoryview(pix)
    vorlage = bytearray(schritt * hoehe)
    ziel = memoryview(vorlage)
    for y in range(hoehe):
        s = ((y0 + y) * qb + x0) * 4
        d = y * schritt
        ziel[d:d + zeile] = quelle[s:s + zeile]
    del ziel, quelle
    _ms_schneiden = (_t.monotonic() - _t2) * 1000.0
    _t3 = _t.monotonic()
    vorlage = _abdunkeln(vorlage, dim)
    _ms_dunkel = (_t.monotonic() - _t3) * 1000.0
    LOG("Hintergrund geladen: %s (%dx%d, %d %% abgedunkelt) - "
        "%.0f ms gesamt: dekodieren %.0f, skalieren %.0f, "
        "zuschneiden %.0f, abdunkeln %.0f"
        % (os.path.basename(pfad), breite, hoehe, dim,
           (_t.monotonic() - _t0) * 1000.0, _ms_lesen, _ms_skalieren,
           _ms_schneiden, _ms_dunkel))
    return vorlage
