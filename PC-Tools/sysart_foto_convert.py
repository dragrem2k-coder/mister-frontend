#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sysart_foto_convert.py - Geraetefotos fuer die neuen Hauptseiten (Build 314)
=============================================================================
Laeuft auf dem PC, NICHT auf dem MiSTer. Benoetigt Pillow.

NUTZERWUNSCH: "alle drei machen unter menue mit schalter zum hin und
herwechseln, koenntest du bitte diese als systemarts / boxarts dann
verwenden? fuer das neue?" - dazu 18 Fotos von Konsolen.

WOFUER DAS HIER DA IST
----------------------
Die drei neuen Hauptseiten-Stile (Kachelwand, Dashboard, Karussell)
holen ihr Kategoriebild zuerst aus frontend/sysart_foto und erst dann
aus frontend/sysart. Dieses Werkzeug fuellt den neuen Ordner.

WARUM EIN DRITTES WERKZEUG NEBEN sysart_convert.py UND
sysart_abzeichen.py - und das ist kein Geschmack, sondern die Vorlage:

  * sysart_convert.py bekommt LOGOS mit Transparenz oder auf
    einfarbigem Grund und schneidet sie randlos zu. Ein Foto hat
    keinen Alphakanal und soll gerade NICHT randlos sein.
  * sysart_abzeichen.py schneidet runde Abzeichen aus Kontaktbogen
    aus. Hier liegt jedes Foto einzeln vor.

Was ein Foto braucht, hat keines von beiden: den weissen
Studiohintergrund wegnehmen, das Geraet freistellen, und das Ergebnis
MITTIG in eine Kachel von immer derselben Groesse setzen.

DREI ENTSCHEIDUNGEN, DIE MAN SONST NACHTRAEGLICH BEREUT
--------------------------------------------------------
1. 420x320 - QUER, UND ZWAR WEIL DIE VORLAGEN QUER SIND.
   Die Abzeichen unter sysart/ sind hochkant 320x420, weil ein Kreis
   mit Text darunter hochkant ist. Von den 17 Fotos liegen 14 quer
   (Konsole mit Controller daneben) und nur drei hochkant (Game Boy,
   Game Boy Color, Automat). Nachgerechnet am Kachelfeld der
   Kachelwand bei 1920x1080 (260x182 Punkte): eine 4:3-Kachel fuellt
   davon 239 Punkte Breite, eine 3:4-Kachel nur 139. Das ist der
   Unterschied zwischen "Konsole" und "Briefmarke".

   Die drei hochkanten Fotos stehen dafuer mit Luft links und rechts -
   unsichtbar, weil die Luft C_PANEL ist und auf einer C_PANEL-Karte
   liegt. Genau dasselbe gilt umgekehrt fuer die Abzeichen, auf die
   zurueckgefallen wird, wenn es kein Foto gibt.

   Die drei klassischen Ansichten bleiben davon unberuehrt: sie lesen
   weiter aus sysart/, und kat_layout() rechnet dort unveraendert mit
   hochkant 3:4.

2. HINTERGRUND C_PANEL (28,32,44), NICHT TRANSPARENZ.
   Der Alphakanal in den .art-Dateien ist durchgehend 0 und wird vom
   Frontend gar nicht angesehen - es kopiert die Zeilen roh in den
   Bildspeicher. Durchsichtigkeit gibt es hier also nicht; was im
   Bild steht, steht auf dem Schirm. Genau denselben Weg geht
   sysart_abzeichen.py seit Build 99.

3. FLUTFUELLUNG VOM RAND, KEIN GLOBALER FARBTAUSCH.
   Weiss kommt auf den Geraeten selbst vor (Super Nintendo, NES,
   Game Boy). Ein globaler Tausch frisst Loecher hinein; die
   Flutfuellung kommt dort nicht hin, weil die Konturen sie
   einschliessen. Dieselbe Begruendung wie in sysart_convert.py.

Aufruf:

  # ein einzelnes Foto
  python3 PC-Tools/sysart_foto_convert.py nes.jpg \\
      --name NES --ziel frontend/sysart_foto

  # viele auf einmal, Name=Datei
  python3 PC-Tools/sysart_foto_convert.py \\
      NES=fotos/nes.jpg SNES=fotos/snes.jpg \\
      --ziel frontend/sysart_foto --vorschau /tmp/kontakt.png

Der Name ist der sysart-Schluessel, also derselbe Dateiname wie unter
frontend/sysart (NES, SNES, Genesis, MegaCD, PSX, Saturn, TGFX16,
NEOGEO, ARCADE, GAMEBOY, GBC, GBA, N64, SMS, ATARI2600,
SUPERGAMEBOY, PHYSICAL_DISC_CORES ...). Gross-/Kleinschreibung zaehlt,
weil die Datei so gesucht wird.
"""

import argparse
import os
import struct
import sys
import zlib
from collections import deque

try:
    from PIL import Image
except ImportError:                                   # pragma: no cover
    sys.exit("Pillow fehlt. Bitte installieren:  pip install Pillow")

# Muss mit C_PANEL in frontend.py uebereinstimmen - das Bild wird direkt
# auf die Karte kopiert, jede Abweichung waere als Kasten sichtbar.
PANEL = (28, 32, 44)
# Quer, 4:3 - siehe oben, Punkt 1. Die Abzeichen unter frontend/sysart
# sind 320x420 und bleiben es.
KACHEL_B = 420
KACHEL_H = 320
# Luft zum Kachelrand, damit der Rahmen der markierten Kachel das
# Geraet nicht beruehrt.
RAND = 10


def grundfarbe(img):
    """Die Farbe des Studiohintergrunds - die haeufigste der vier Ecken.

    EINMAL AM ANFANG BESTIMMT UND DANN WEITERGEREICHT, und das ist
    nicht Stilfrage, sondern ein bereits gemachter Fehler: die
    Lochsuche hat sich diese Farbe zunaechst selbst aus den Ecken
    geholt - nur sind die Ecken da laengst durchsichtig, die Liste
    war leer, und die Funktion stieg wirkungslos wieder aus. Der
    Kontaktbogen sah danach aus wie vorher.

    Ein einzelner Ausreisser (JPEG-Artefakt) bestimmt nichts: es
    gewinnt die haeufigste Ecke, nicht die erste."""
    img = img.convert("RGBA")
    w, h = img.size
    px = img.load()
    ecken = [px[0, 0], px[w - 1, 0], px[0, h - 1], px[w - 1, h - 1]]
    ecken = [c for c in ecken if c[3] > 0]
    if not ecken:
        return None
    return max(set(ecken), key=ecken.count)


def hintergrund_fluten(img, toleranz=52, bg=None):
    """Vom Bildrand aus zusammenhaengende Flaechen gleicher Farbe
    durchsichtig machen.

    Toleranz hoeher als in sysart_convert.py (40): Studiofotos sind
    JPEG, und ein JPEG-Weiss ist nie zweimal derselbe Wert. Bei 40
    blieb an den Kanten ein Kranz heller Punkte stehen."""
    img = img.convert("RGBA")
    w, h = img.size
    px = img.load()
    if bg is None:
        bg = grundfarbe(img)
    if bg is None:
        return img

    def passt(c):
        return (c[3] > 0
                and abs(c[0] - bg[0]) + abs(c[1] - bg[1])
                + abs(c[2] - bg[2]) <= toleranz)

    gesehen = bytearray(w * h)
    q = deque()
    for x in range(w):
        for y in (0, h - 1):
            q.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            q.append((x, y))
    while q:
        x, y = q.popleft()
        if not (0 <= x < w and 0 <= y < h) or gesehen[y * w + x]:
            continue
        gesehen[y * w + x] = 1
        if not passt(px[x, y]):
            continue
        px[x, y] = (0, 0, 0, 0)
        q.append((x + 1, y))
        q.append((x - 1, y))
        q.append((x, y + 1))
        q.append((x, y - 1))
    return img


def loecher_schliessen(img, toleranz=52, mindest_anteil=0.0045, bg=None):
    """Eingeschlossene Reste des Studiohintergrunds entfernen.

    NOETIG, UND ZWAR NACHGEWIESEN AM ERSTEN KONTAKTBOGEN: bei Master
    System, Mega Drive und TurboGrafx liegt das Kabel des Controllers
    in einer Schleife auf dem Tisch. Das Weiss INNERHALB dieser
    Schleife ist vom Bildrand aus nicht erreichbar - die Flutfuellung
    kommt dort nie an, und auf der fertigen Kachel stand ein weisser
    Fleck neben dem Geraet.

    WARUM NICHT EINFACH ALLES WEISSE WEGNEHMEN: Lichter auf dem
    Gehaeuse sind auch fast weiss (die glaenzende Haube des Saturn,
    die Blende des Game Boy). Die sind aber KLEIN. Deshalb wird hier
    nach zusammenhaengenden Flaechen gefragt und nur entfernt, was
    gross genug ist, um Hintergrund zu sein - gemessen am Bild, nicht
    an einer festen Punktzahl, sonst haengt das Ergebnis an der
    Aufloesung der Vorlage.

    NACHGEMESSEN AN DEN 17 MITGELIEFERTEN FOTOS (Flaechenanteil der
    groessten eingeschlossenen hellen Flaeche je Bild):

        entfernen (Hintergrund)   behalten (Glanz/Kunststoff)
          SMS       5,80 %          Neo Geo   0,31 %
          Genesis   2,38 %          GBC       0,14 %
          TGFX16    2,27 %          Arcade    0,02 %
          PSX       1,23 %          SNES      0,02 %
          N64       1,21 %          alle uebrigen < 0,01 %
          Saturn    0,66 %

    Zwischen 0,31 % und 0,66 % liegt der Faktor zwei; die Vorgabe von
    0,45 % steht in der Mitte. Wer eigene Fotos nachliefert, bei denen
    das nicht passt, verstellt sie mit --loecher-anteil."""
    img = img.convert("RGBA")
    w, h = img.size
    px = img.load()
    if bg is None:
        bg = grundfarbe(img)
    if bg is None:
        return img
    mindest = max(16, int(w * h * mindest_anteil))

    def passt(c):
        return (c[3] > 0
                and abs(c[0] - bg[0]) + abs(c[1] - bg[1])
                + abs(c[2] - bg[2]) <= toleranz)

    gesehen = bytearray(w * h)
    for sy in range(h):
        for sx in range(w):
            if gesehen[sy * w + sx] or not passt(px[sx, sy]):
                continue
            # Eine Flaeche einsammeln, DANN entscheiden - wer beim
            # Laufen schon loescht, kann hinterher nicht mehr
            # zurueck.
            flaeche = []
            q = deque([(sx, sy)])
            gesehen[sy * w + sx] = 1
            while q:
                x, y = q.popleft()
                flaeche.append((x, y))
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1),
                               (x, y - 1)):
                    if not (0 <= nx < w and 0 <= ny < h):
                        continue
                    if gesehen[ny * w + nx]:
                        continue
                    if not passt(px[nx, ny]):
                        continue
                    gesehen[ny * w + nx] = 1
                    q.append((nx, ny))
            if len(flaeche) >= mindest:
                for x, y in flaeche:
                    px[x, y] = (0, 0, 0, 0)
    return img


def zuschneiden(img):
    """Den leeren Rand abschneiden - sonst bestimmt der Zufall des
    Studiofotos, wie gross das Geraet in der Kachel erscheint."""
    img = img.convert("RGBA")
    box = img.getchannel("A").getbbox()
    return img.crop(box) if box else img


def einpassen(img, breite=KACHEL_B, hoehe=KACHEL_H, rand=RAND):
    """Proportional in die Kachel setzen, mittig, Grund C_PANEL.

    MITTIG UND NICHT OBEN: bei den Abzeichen sitzt der Kreis oben und
    der Text darunter, das Bild ist also von sich aus ausgewogen. Ein
    freigestelltes Foto hat keine solche Struktur - haengt es oben,
    sieht die Kachel aus, als waere sie abgeschnitten."""
    img = img.convert("RGBA")
    nutz_b = max(1, breite - 2 * rand)
    nutz_h = max(1, hoehe - 2 * rand)
    f = min(nutz_b / float(img.width), nutz_h / float(img.height))
    zb = max(1, int(round(img.width * f)))
    zh = max(1, int(round(img.height * f)))
    img = img.resize((zb, zh), Image.LANCZOS)
    grund = Image.new("RGBA", (breite, hoehe), PANEL + (255,))
    grund.alpha_composite(img, ((breite - zb) // 2, (hoehe - zh) // 2))
    return grund


def schreiben(img, out_path):
    """Als ART1 ablegen: 'ART1', Breite und Hoehe als je 16 Bit, danach
    zlib-gepackte BGRX-Pixel - genau die Byte-Reihenfolge des
    Framebuffers, damit das Frontend die Zeilen ohne Umrechnung
    hineinkopieren kann. Dasselbe Format wie sysart_convert.py."""
    rgb = img.convert("RGB").tobytes()
    pix = bytearray(len(rgb) // 3 * 4)
    pix[0::4] = rgb[2::3]
    pix[1::4] = rgb[1::3]
    pix[2::4] = rgb[0::3]
    daten = (b"ART1" + struct.pack("<HH", img.width, img.height)
             + zlib.compress(bytes(pix), 9))
    tmp = out_path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(daten)
    os.replace(tmp, out_path)
    return img.width, img.height, len(daten)


ARBEITS_KANTE = 1000


def verkleinern(img, kante=ARBEITS_KANTE):
    """Vor der Maskenarbeit auf Arbeitsgroesse bringen.

    Die Vorlagen sind bis zu 2576 Punkte breit, die fertige Kachel ist
    320. Flutfuellung und Lochsuche laufen in Python Punkt fuer Punkt -
    auf dem vollen Bild sind das 3,6 Millionen Durchlaeufe je Foto und
    damit Minuten statt Sekunden, fuer eine Genauigkeit, die am Ende
    weggeworfen wird. 1000 Punkte lange Kante sind immer noch das
    Dreifache der Zielgroesse."""
    if max(img.size) <= kante:
        return img
    f = kante / float(max(img.size))
    return img.resize((max(1, int(img.width * f)),
                       max(1, int(img.height * f))), Image.LANCZOS)


def ein_foto(quelle, toleranz=52, rand=RAND, mindest_anteil=0.0045):
    bild = verkleinern(Image.open(quelle).convert("RGB")).convert("RGBA")
    # Die Grundfarbe VOR dem Fluten bestimmen - danach sind die Ecken
    # durchsichtig und geben sie nicht mehr her. Siehe grundfarbe().
    bg = grundfarbe(bild)
    bild = hintergrund_fluten(bild, toleranz, bg)
    bild = loecher_schliessen(bild, toleranz, mindest_anteil, bg)
    bild = zuschneiden(bild)
    return einpassen(bild, rand=rand)


def main(argv=None):
    p = argparse.ArgumentParser(
        description="Geraetefotos in .art-Kacheln fuer sysart_foto")
    p.add_argument("eingaben", nargs="+",
                   help="Dateien, wahlweise als NAME=datei.jpg")
    p.add_argument("--ziel", default="frontend/sysart_foto",
                   help="Zielordner (Vorgabe: frontend/sysart_foto)")
    p.add_argument("--name", default=None,
                   help="Name fuer EINE Eingabe ohne NAME=-Praefix")
    p.add_argument("--toleranz", type=int, default=52,
                   help="Farbabstand fuer die Flutfuellung (Vorgabe 52)")
    p.add_argument("--rand", type=int, default=RAND,
                   help="Luft zum Kachelrand in Bildpunkten")
    p.add_argument("--loecher-anteil", type=float, default=0.0045,
                   dest="loecher_anteil",
                   help="ab welchem Flaechenanteil ein eingeschlossener "
                        "heller Fleck als Hintergrund gilt (Vorgabe "
                        "0.0045 = 0,45 %%)")
    p.add_argument("--vorschau", default=None,
                   help="Kontaktbogen aller Ergebnisse als PNG ablegen")
    a = p.parse_args(argv)

    if not os.path.isdir(a.ziel):
        os.makedirs(a.ziel)

    fertig = []
    for eing in a.eingaben:
        if "=" in eing:
            name, pfad = eing.split("=", 1)
        elif a.name:
            name, pfad = a.name, eing
        else:
            name = os.path.splitext(os.path.basename(eing))[0]
            pfad = eing
        bild = ein_foto(pfad, a.toleranz, a.rand, a.loecher_anteil)
        ziel = os.path.join(a.ziel, "%s.art" % name)
        b, h, n = schreiben(bild, ziel)
        print("%-22s %dx%d  %6.1f KB" % (name + ".art", b, h, n / 1024.0))
        fertig.append((name, bild))

    if a.vorschau and fertig:
        sp = 6
        rows = (len(fertig) + sp - 1) // sp
        bogen = Image.new("RGB", (sp * KACHEL_B, rows * KACHEL_H),
                          (16, 18, 24))
        for i, (_n, b) in enumerate(fertig):
            bogen.paste(b.convert("RGB"),
                        ((i % sp) * KACHEL_B, (i // sp) * KACHEL_H))
        bogen.save(a.vorschau)
        print("Vorschau:", a.vorschau)
    return 0


if __name__ == "__main__":
    sys.exit(main())
