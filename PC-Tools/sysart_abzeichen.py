#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sysart_abzeichen.py - die Abzeichen-Kategorie-Logos erzeugen (Build 99)
=======================================================================
Laeuft auf dem PC, NICHT auf dem MiSTer. Benoetigt Pillow.

NUTZERWUNSCH: "Ausserdem haette ich gerne auf der Hauptseite die alten
Sysarts durch diese hier ersetzt, damit es einheitlich aussieht. Alle
bitte auf eine Hoehe setzen, mittig rechts neben den Kategorien, und die
alten sollten dafuer raus. Soll alles die gleiche Groesse haben, ohne
dass ein Rahmen neu gezeichnet werden muss."

WARUM EIN EIGENES WERKZEUG NEBEN sysart_convert.py
---------------------------------------------------
sysart_convert.py schneidet ein Logo RANDLOS auf sein Motiv zu und legt
es in 900 Pixel Breite ab. Genau das ist hier falsch:

  * Randlos zugeschnitten hat jede Datei eine andere Groesse - und damit
    auf dem Schirm einen anderen Kasten. Der Nutzer will ausdruecklich
    das Gegenteil.
  * 900 Pixel sind Verschwendung: dargestellt werden rund 300.

Dieses Werkzeug erzeugt stattdessen KACHELN: jede Datei ist exakt
gleich gross, das Abzeichen sitzt immer an derselben Stelle. Dadurch
  - steht das Bild auf dem Schirm immer im selben Rechteck,
  - muss nichts freigeraeumt werden, bevor das naechste gezeichnet wird,
  - und alle Kategorien sehen gleich aus, egal wie lang ihr Text ist.

DIE FEINHEIT, DIE DEN UNTERSCHIED MACHT
----------------------------------------
Normiert wird auf den KREIS, nicht auf das ganze Bild. Die Vorlagen
sind unterschiedlich breit (239 bis 295 Bildpunkte) - aber nicht, weil
die Kreise verschieden gross waeren, sondern weil der Text darunter
verschieden lang ist ("N64" gegen "SEGA MASTER SYSTEM"). Wer auf die
Gesamtbreite normiert, macht ausgerechnet die Kreise mit kurzem Text zu
gross. Deshalb wird hier der beigefarbene Kreis gesucht und DER auf eine
feste Breite gebracht; der Text laeuft darunter mit.

Aufruf:
    python3 PC-Tools/sysart_abzeichen.py blatt1.png blatt2.jpg \\
        --ziel frontend/sysart --vorschau /tmp/kontakt.png

Das Raster der Blaetter steht unten in BLAETTER und muss zu den
uebergebenen Dateien passen (Reihenfolge der Argumente = Reihenfolge
dort).
"""

import argparse
import os
import struct
import sys
import zlib

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow fehlt:  pip install Pillow")

# Muss C_PANEL in frontend.py entsprechen - siehe tools/test_sysart_logos.py,
# der genau das prueft. Ein anderer Hintergrund faellt nicht als Fehler
# auf, sondern nur als heller Kasten auf der Karte.
C_PANEL = (28, 32, 44)

# Kachelgroesse. 320x400 nimmt die groesste Vorlage (295x386) ohne
# Verkleinern auf und liegt nah an der tatsaechlichen Anzeigegroesse
# (rund 300 Bildpunkte breit) - also weder Qualitaetsverlust noch
# Verschwendung. Die alten Dateien lagen bei 900 Bildpunkten Breite;
# SYSTEM.art war dadurch 379 KB gross, um am Ende 300 Punkte breit
# gezeigt zu werden.
KACHEL_B, KACHEL_H = 320, 420
KREIS_B = 235            # darauf wird jeder Kreis gebracht
KREIS_Y = 14             # Abstand des Kreises vom oberen Kachelrand
RAND_U = 8               # Mindestluft unter der laengsten Beschriftung

# Wie viel Prozent einer Zellhoehe/-breite mindestens leer sein muss,
# damit eine Luecke als Trennung zwischen zwei Abzeichen zaehlt.
LUECKE_MIN = 0.04

# Helligkeit, ab der ein Bildpunkt sicher zum Abzeichen gehoert und
# nicht mehr zum Hintergrund - siehe _grund_maske(). Gemessen: der
# beige Kreis liegt bei rund 209, die hellste Hintergrundstelle des
# dritten Blattes bei 143.
HELL_GRENZE = 175

# Die Blaetter, die der Nutzer geschickt hat - Zeile fuer Zeile, in
# Lesereihenfolge. Weitere Blaetter einfach anhaengen.
#
# Eine Zelle ist entweder
#   "SCHLUESSEL"              ein Abzeichen fuer genau eine Kategorie,
#   ["A", "B", "C"]           EIN Abzeichen fuer mehrere Kategorien
#                             (das Atari-Abzeichen traegt "2600/5200/
#                             7800" und gilt damit fuer alle drei), oder
#   None                      eine Zelle, die uebersprungen wird.
BLAETTER = [
    [["GAMEBOY", "GBC", "NES", "SNES"],
     ["SMS", "GBA", "Genesis", "PSX"],
     ["Saturn", "MegaCD", "VIRTUALBOY", "N64"]],
    [["CONTINUE", "RECENT", "TGFX16", "NEOGEO", "SMW_HACKS",
      "SNES_ALTTP_TRACKER"],
     ["ARCADE", "COMPUTER", "COLLECTIONS", "RA_HUNTER", "WOT", "SYSTEM"]],
    [["3DO", ["ATARI2600", "ATARI5200", "ATARI7800"], "ATARILYNX", "CDI",
      "COLECOVISION", "FAVORITES", "FDS", "GAMATE"],
     ["INTELLIVISION", "JAGUAR", "NEOGEOCD", "S32X", "SUPERGAMEBOY",
      "TGFX16CD", "VECTREX", "WONDERSWAN"],
     ["ADVENTUREVISION", "ARCADIA", "ASTROCADE", "CASIOPV1000", "CHANNELF",
      "CREATIVISION", "GAMEGEAR", "GAMENWATCH"],
     # Die vorletzte Zelle traegt keine Beschriftung und zeigt eine
     # zweite, blaue WonderSwan - eine Farbvariante, fuer die es keine
     # eigene Kategorie gibt. Bewusst uebersprungen statt sie
     # irgendwohin zu zwingen.
     ["MEGADUCK", "ODYSSEY2", "POCKETCHALLENGEV2", "POKEMONMINI",
      "SG1000", "VC4000", None, "WONDERSWANCOLOR"]],
    # Viertes Blatt (Build 112): zwei Nachzuegler fuer Kategorien, die
    # als ORDNER auf der SD-Karte liegen - "Custom Cores" und "Physical
    # Disc Cores". Eine Zeile, zwei Zellen; das Blatt ist deutlich
    # kleiner als die vorherigen, das Raster kommt damit von selbst
    # zurecht (die Trennlinien werden gemessen, nicht gerechnet).
    [["CUSTOM_CORES", "PHYSICAL_DISC_CORES"]],
]


def _trennlinien(projektion, anzahl, laenge, schwelle=None):
    """Aus einem Helligkeitsprofil die Grenzen zwischen `anzahl`
    Abzeichen bestimmen.

    WARUM NICHT EINFACH GLEICHMAESSIG TEILEN: die Blaetter sind nicht
    bildpunktgenau gerastert. Teilt man stur in gleiche Zellen, ragt mal
    der Kreis des Nachbarn mit herein (im ersten Versuch als
    beigefarbener Klecks zu sehen), und rueckt man dagegen pauschal ein,
    schneidet man bei den zweizeiligen Beschriftungen die untere Zeile
    ab (im zweiten Versuch zu sehen: "WEITER-SPIELEN" endete nach
    "WEITER-").

    Deshalb werden die echten Luecken gesucht: Bildzeilen bzw. -spalten,
    in denen NICHTS steht. Zwischen zwei Abzeichen gibt es immer eine -
    sonst waeren sie nicht als getrennte Motive zu erkennen."""
    # Die Schwelle ist RELATIV, nicht absolut: auf dem dritten Blatt
    # beruehren sich die Abzeichen fast, zwischen zwei Reihen steht die
    # Beschriftung der oberen und gleich darunter der Kreis der unteren.
    # Voellig leere Bildzeilen gibt es dort nicht - wohl aber ein klares
    # Minimum. Mit der starren Bedingung "ganz leer" wurde deshalb gar
    # kein Raster erkannt und stur gleichmaessig geteilt; die Folge
    # waren abgeschnittene Beschriftungen und hereinragende Nachbarn.
    if schwelle is None:
        schwelle = max(1, int(max(projektion) * 0.03))
    leer = [i for i, v in enumerate(projektion) if v <= schwelle]
    # aufeinanderfolgende leere Linien zu Baendern zusammenfassen
    baender = []
    for i in leer:
        if baender and i == baender[-1][1] + 1:
            baender[-1][1] = i
        else:
            baender.append([i, i])
    mindest = max(1, int(laenge / float(anzahl) * LUECKE_MIN))
    innen = [b for b in baender
             if b[1] - b[0] + 1 >= mindest and b[0] > 0 and b[1] < laenge - 1]
    if len(innen) < anzahl - 1:
        return None
    # die `anzahl-1` breitesten Luecken sind die Trennungen
    innen.sort(key=lambda b: b[1] - b[0], reverse=True)
    trenner = sorted((b[0] + b[1]) // 2 for b in innen[:anzahl - 1])
    return [0] + trenner + [laenge]


def _grund_maske(bild, toleranz=14):
    """bytearray mit 1 fuer jeden Bildpunkt, der zum Blattgrund gehoert.

    Geflutet wird vom Bildrand aus, und verglichen wird jeder neue Punkt
    mit dem NACHBARN, von dem aus er erreicht wurde - nicht mit einer
    festen Grundfarbe.

    WARUM LOKAL UND NICHT GEGEN DIE ECKFARBE: das dritte Blatt hat einen
    Farbverlauf im Hintergrund - Ecke (102,94,68), Mitte (160,143,106),
    also rund 58 Stufen Unterschied. Gegen die Eckfarbe verglichen
    bliebe entweder die halbe Bildmitte als "Motiv" stehen (kleine
    Toleranz) oder die Abzeichen wuerden mitgefressen (grosse). Ein
    Verlauf aendert sich von Punkt zu Punkt aber nur minimal, waehrend
    die dunkle Umrandung eines Abzeichens ein harter Sprung ist - genau
    darauf reagiert der lokale Vergleich richtig.

    Einfach "alles Dunkle" oder "alles Beige" waere ebenfalls falsch:
    die Abzeichen sind teils fast schwarz (Mega Drive, N64), teils fast
    beige (der Kreis selbst).

    ZUSAETZLICH eine Helligkeitsgrenze (HELL_GRENZE): der lokale
    Vergleich allein reicht nicht, weil die Kante des Abzeichens
    stellenweise weich genug ist, dass sich das Fluten Punkt fuer Punkt
    hineinschleichen kann - im Versuch davor war bei den meisten
    Abzeichen der beige Kreis weggefressen und nur die Umrandung uebrig.
    Der Kreis ist aber IMMER deutlich heller als jeder Hintergrund
    (Kreis rund 209 Helligkeit, hellste Hintergrundstelle 143), und
    diese Grenze kann kein Verlauf ueberschreiten."""
    rgb = bild.convert("RGB")
    b, h = rgb.size
    px = rgb.load()
    maske = bytearray(b * h)
    stapel = []
    for x in range(b):
        stapel.append((x, 0, px[x, 0]))
        stapel.append((x, h - 1, px[x, h - 1]))
    for y in range(h):
        stapel.append((0, y, px[0, y]))
        stapel.append((b - 1, y, px[b - 1, y]))
    while stapel:
        x, y, vor = stapel.pop()
        if x < 0 or y < 0 or x >= b or y >= h:
            continue
        i = y * b + x
        if maske[i]:
            continue
        c = px[x, y]
        if (abs(c[0] - vor[0]) > toleranz or abs(c[1] - vor[1]) > toleranz
                or abs(c[2] - vor[2]) > toleranz):
            continue
        if (c[0] * 299 + c[1] * 587 + c[2] * 114) // 1000 > HELL_GRENZE:
            continue
        maske[i] = 1
        stapel += [(x + 1, y, c), (x - 1, y, c), (x, y + 1, c), (x, y - 1, c)]
    return maske, rgb


def _grund_fluten(bild):
    """Den Blattgrund durch C_PANEL ersetzen (siehe _grund_maske)."""
    maske, rgb = _grund_maske(bild)
    b, h = rgb.size
    px = rgb.load()
    for y in range(h):
        z = y * b
        for x in range(b):
            if maske[z + x]:
                px[x, y] = C_PANEL
    return rgb


def _hell_bbox(bild):
    """Umriss alles dessen, was NICHT Blattgrund ist."""
    maske, rgb = _grund_maske(bild)
    b, h = rgb.size
    xs, ys = [], []
    for y in range(h):
        z = y * b
        for x in range(b):
            if not maske[z + x]:
                xs.append(x)
                ys.append(y)
    if not xs:
        return None
    return (min(xs), min(ys), max(xs) + 1, max(ys) + 1)


def _profil_maske(bild, achse):
    """Wie viele Nicht-Grund-Punkte je Bildzeile bzw. -spalte."""
    maske, rgb = _grund_maske(bild)
    b, h = rgb.size
    if achse == "y":
        return [sum(1 for x in range(b) if not maske[y * b + x])
                for y in range(h)]
    return [sum(1 for y in range(h) if not maske[y * b + x])
            for x in range(b)]


def _kreis_bbox(bild):
    """Umriss NUR des beigefarbenen Kreises (ohne den Text darunter).

    Der Kreis ist die einzige grosse, zusammenhaengende helle Flaeche im
    Bild; der Text ist weiss auf dunklem Grund und damit deutlich
    dunkler UND gesaettigter. Gesucht werden also Bildpunkte nahe der
    Beigefarbe."""
    rgb = bild.convert("RGB")
    b, h = rgb.size
    px = rgb.load()
    xs, ys = [], []
    for y in range(h):
        for x in range(b):
            r, g, bl = px[x, y]
            # beige: hell, warm, wenig blau
            if r > 150 and g > 140 and bl > 100 and r >= bl + 25:
                xs.append(x)
                ys.append(y)
    if not xs:
        return None
    return (min(xs), min(ys), max(xs) + 1, max(ys) + 1)


def kachel(icon):
    """Ein ausgeschnittenes Abzeichen auf die einheitliche Kachel
    setzen: Kreis auf feste Breite, mittig, immer an derselben Stelle."""
    kb = _kreis_bbox(icon)
    if kb is None:
        faktor = KREIS_B / float(icon.size[0])
    else:
        faktor = KREIS_B / float(kb[2] - kb[0])
    # Nicht ueber die Kachel hinauslaufen: die Abzeichen mit
    # zweizeiliger Beschriftung ("SEGA MASTER SYSTEM", "RA-
    # ERFOLGSJAEGER") sind deutlich hoeher als die einzeiligen und
    # wurden im ersten Versuch unten abgeschnitten. Lieber der Kreis
    # ein paar Punkte kleiner als der Text ab.
    passt_h = (KACHEL_H - KREIS_Y - RAND_U) / float(icon.size[1])
    passt_b = (KACHEL_B - 4) / float(icon.size[0])
    faktor = min(faktor, passt_h, passt_b)
    neu_b = max(1, int(round(icon.size[0] * faktor)))
    neu_h = max(1, int(round(icon.size[1] * faktor)))
    # LANCZOS statt NEAREST: der Faktor liegt nahe bei 1, und die
    # Vorlagen sind bereits gerasterte Pixelgrafik - hartes Nearest
    # wuerde bei krummen Faktoren einzelne Pixelreihen verdoppeln oder
    # verschlucken und die Kanten ausfransen lassen.
    ic = icon.resize((neu_b, neu_h), Image.LANCZOS)

    kachel_bild = Image.new("RGB", (KACHEL_B, KACHEL_H), C_PANEL)
    x = (KACHEL_B - neu_b) // 2
    if kb is not None:
        y = KREIS_Y - int(round(kb[1] * faktor))
    else:
        y = (KACHEL_H - neu_h) // 2
    y = max(0, min(y, KACHEL_H - neu_h)) if neu_h <= KACHEL_H else 0
    kachel_bild.paste(ic, (x, y))
    return kachel_bild


def schreiben(bild, pfad):
    """.art-Format: b"ART1" + uint16 Breite + uint16 Hoehe +
    zlib(BGRA-Rohpixel) - siehe Kopf von fe/art.py."""
    b, h = bild.size
    roh = bytearray()
    for r, g, bl in bild.convert("RGB").getdata():
        roh += bytes((bl, g, r, 0))
    daten = b"ART1" + struct.pack("<HH", b, h) + zlib.compress(bytes(roh), 9)
    with open(pfad, "wb") as f:
        f.write(daten)
    return len(daten)


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("blaetter", nargs="+", help="Bildblaetter in der "
                   "Reihenfolge von BLAETTER")
    p.add_argument("--ziel", default="frontend/sysart",
                   help="Zielordner fuer die .art-Dateien")
    p.add_argument("--vorschau", help="Kontaktbogen als PNG hierhin")
    p.add_argument("--trocken", action="store_true",
                   help="nichts schreiben, nur berichten")
    # NEU (Build 112): die Blaetter kommen nach und nach dazu, und die
    # alten liegen nicht im Repo. Ohne diese Angabe muesste man zum
    # Nachtragen von zwei Abzeichen alle vier Blaetter zur Hand haben.
    p.add_argument("--nur", type=int, metavar="N",
                   help="nur Blatt N aus BLAETTER verarbeiten (1-basiert)")
    a = p.parse_args()

    blaetter = BLAETTER
    if a.nur:
        if not 1 <= a.nur <= len(BLAETTER):
            sys.exit("--nur %d: es gibt %d Blaetter" % (a.nur, len(BLAETTER)))
        blaetter = [BLAETTER[a.nur - 1]]
    if len(a.blaetter) != len(blaetter):
        sys.exit("%d Blaetter uebergeben, %d erwartet"
                 % (len(a.blaetter), len(blaetter)))

    if not a.trocken:
        os.makedirs(a.ziel, exist_ok=True)

    fertig = []
    for pfad, raster in zip(a.blaetter, blaetter):
        blatt = Image.open(pfad).convert("RGB")
        B, H = blatt.size
        reihen, spalten = len(raster), len(raster[0])
        ygrenzen = _trennlinien(_profil_maske(blatt, "y"), reihen, H)
        xgrenzen = _trennlinien(_profil_maske(blatt, "x"), spalten, B)
        if ygrenzen is None or xgrenzen is None:
            print("  !! %s: kein Raster erkannt, teile gleichmaessig"
                  % os.path.basename(pfad))
            ygrenzen = [int(i * H / reihen) for i in range(reihen + 1)]
            xgrenzen = [int(i * B / spalten) for i in range(spalten + 1)]
        for r, zeile in enumerate(raster):
            for c, schluessel in enumerate(zeile):
                if schluessel is None:
                    continue
                zelle = blatt.crop((xgrenzen[c], ygrenzen[r],
                                    xgrenzen[c + 1], ygrenzen[r + 1]))
                bb = _hell_bbox(zelle)
                if bb is None:
                    print("  !! %-20s leere Zelle" % schluessel)
                    continue
                # Erst zuschneiden, DANN fluten: so beginnt das Fluten
                # direkt am Motivrand und laeuft nicht durch halbe
                # Nachbarzellen.
                icon = _grund_fluten(zelle.crop(bb))
                bild = kachel(icon)
                for k in ([schluessel] if isinstance(schluessel, str)
                          else schluessel):
                    fertig.append((k, bild))

    for schluessel, bild in fertig:
        if a.trocken:
            print("  %-22s %dx%d (trocken)" % (schluessel, *bild.size))
            continue
        ziel = os.path.join(a.ziel, "%s.art" % schluessel)
        n = schreiben(bild, ziel)
        print("  %-22s %dx%d  %6d B  -> %s"
              % (schluessel, bild.size[0], bild.size[1], n, ziel))

    if a.vorschau:
        sp = 6
        reihen = (len(fertig) + sp - 1) // sp
        bogen = Image.new("RGB", (sp * KACHEL_B, reihen * KACHEL_H), (0, 0, 0))
        for i, (_k, bild) in enumerate(fertig):
            bogen.paste(bild, ((i % sp) * KACHEL_B, (i // sp) * KACHEL_H))
        bogen.save(a.vorschau)
        print("Vorschau:", a.vorschau)

    print("%d Abzeichen" % len(fertig))


if __name__ == "__main__":
    main()
