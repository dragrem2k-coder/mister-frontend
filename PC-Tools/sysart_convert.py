#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sysart_convert.py - Kategorie-Logos fuer das MiSTer-Frontend
=============================================================
Laeuft auf dem PC, NICHT auf dem MiSTer. Benoetigt Pillow.

Wandelt ein Logo-Bild (PNG/JPG/WEBP, gern mit Transparenz) in eine
.art-Datei um, wie sie unter frontend/sysart/ liegt - also das Bild,
das im Kategorie-Menue und ueber der Spieleliste erscheint.

WARUM EIN EIGENES WERKZEUG (und nicht art_convert.py):
art_convert.py ist fuer BOXART da. Es skaliert auf die kleinen
Zielkaesten (104x168 bzw. 300x350) und legt nichts unter transparente
Bereiche. Kategorie-Logos brauchen das Gegenteil:

  * 900 Pixel Breite (so liegen alle vorhandenen sysart-Dateien vor),
  * Hintergrund exakt C_PANEL = RGB(28, 32, 44), sonst hebt sich das
    Logo als heller oder schwarzer Kasten von der Karte ab,
  * einen sauber abgeschnittenen Rand, denn die vorhandenen Logos sind
    randlos auf das Motiv zugeschnitten (nachgemessen: bei allen ausser
    VIRTUALBOY liegt die Bounding-Box exakt auf den Bildkanten).

Die Doku dazu: docs/LOGOS_NACHLIEFERN.md

Beispiele:

  # Logo mit Transparenz - einfachster Fall:
  python sysart_convert.py wonderswan.png ../frontend/sysart/WONDERSWAN.art

  # Logo auf schwarzem/weissem Grund - Hintergrund wegfluten:
  python sysart_convert.py 3do.webp ../frontend/sysart/3DO.art --fluten

  # Schwarze Schrift auf hellem Grund - sonst unsichtbar auf der Karte:
  python sysart_convert.py gamate.webp ../frontend/sysart/GAMATE.art \\
      --fluten --aufhellen

  # Nur ansehen, nichts schreiben:
  python sysart_convert.py logo.png out.art --vorschau vorschau.png
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

# Muss mit C_PANEL in frontend.py uebereinstimmen - das Logo wird direkt
# auf die Karte kopiert, jede Abweichung waere als Kasten sichtbar.
PANEL = (28, 32, 44)
ZIEL_BREITE = 900
# Deckel fuer die Hoehe: die vorhandenen Logos reichen von 128 bis 403
# Zeilen - siehe schreiben() fuer die Begruendung.
MAX_HOEHE = 450


def _luma(r, g, b):
    return (r * 299 + g * 587 + b * 114) // 1000


def hintergrund_fluten(img, toleranz=40):
    """Vom Bildrand aus zusammenhaengende Flaechen gleicher Farbe
    transparent machen.

    Bewusst eine Flutfuellung und kein globaler Farbtausch: bei
    ColecoVision oder Famicom Disk System ist Schwarz AUCH Konturfarbe
    mitten im Logo. Ein globaler Tausch wuerde die Konturen mit
    wegnehmen; die Flutfuellung kommt dort gar nicht erst hin, weil die
    Konturen sie einschliessen."""
    img = img.convert("RGBA")
    w, h = img.size
    px = img.load()
    # Startfarbe aus den vier Ecken - die haeufigste gewinnt, damit ein
    # einzelnes Ausreisser-Pixel (JPEG-Artefakt) nicht das Ergebnis
    # bestimmt.
    ecken = [px[0, 0], px[w - 1, 0], px[0, h - 1], px[w - 1, h - 1]]
    ecken = [c for c in ecken if c[3] > 0]
    if not ecken:
        return img
    bg = max(set(ecken), key=ecken.count)

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


def karo_entfernen(img, luma_min=180, saettigung_max=45):
    """Helle, farblose Flaechen im GANZEN Bild entfernen - nicht nur vom
    Rand her.

    Fuer Vorlagen, bei denen das Schachbrettmuster fuer "durchsichtig"
    als echte Pixel im Bild steht (Atari 2600 und Famicom Disk System
    liegen so vor: das PNG ist vollstaendig deckend, das Karo ist
    hineingemalt). Eine Flutfuellung reicht dort nicht: die weissen und
    hellgrauen Karos INNERHALB der Buchstaben sind vom Rand aus nicht
    erreichbar und blieben als Schachbrett im Logo stehen."""
    img = img.convert("RGBA")
    px = img.load()
    w, h = img.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a == 0:
                continue
            if max(r, g, b) - min(r, g, b) > saettigung_max:
                continue
            if _luma(r, g, b) >= luma_min:
                px[x, y] = (0, 0, 0, 0)
    return img


def dunkles_aufhellen(img, luma_schwelle=128, saettigung_max=45):
    """Dunkle, farblose Bildteile in ihre Helligkeit gespiegelt (v -> 255-v).

    Noetig bei Logos, die als schwarze Schrift auf hellem Grund
    vorliegen (Gamate, WonderSwan, Famicom Disk System): auf der dunklen
    Karte waere davon sonst schlicht nichts zu sehen. Farbige Teile
    (roter Schwan, gelbes Disk-Symbol) bleiben unangetastet, weil sie
    Saettigung haben; die weichen Kanten der Schrift werden mitgedreht
    und bleiben dadurch weich."""
    img = img.convert("RGBA")
    px = img.load()
    w, h = img.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a == 0:
                continue
            if max(r, g, b) - min(r, g, b) > saettigung_max:
                continue
            lu = _luma(r, g, b)
            if lu >= luma_schwelle:
                continue
            d = 255 - lu
            px[x, y] = (d, d, d, a)
    return img


def zuschneiden(img):
    """Rand ohne Motiv abschneiden - die vorhandenen Logos sind alle
    randlos zugeschnitten."""
    img = img.convert("RGBA")
    box = img.getchannel("A").getbbox()
    return img.crop(box) if box else img


def schreiben(img, out_path, breite=ZIEL_BREITE, max_hoehe=MAX_HOEHE):
    """Auf Zielbreite skalieren, auf C_PANEL legen und als ART1 ablegen.

    ART1 ist dasselbe Format wie bei art_convert.py: 'ART1', Breite und
    Hoehe als je 16 Bit, danach zlib-gepackte BGRX-Pixel - genau die
    Byte-Reihenfolge des Framebuffers, damit das Frontend die Zeilen
    ohne Umrechnung hineinkopieren kann."""
    # Breite ist die Vorgabe, die Hoehe die Notbremse: das Frontend passt
    # das Logo mit ART.get_scaled(pfad, art_w, box_h) proportional in
    # einen Kasten ein - ein hochkantes Bild wird dort ueber die Hoehe
    # begrenzt und bleibt schmal, waehrend die .art-Datei trotzdem in
    # voller Groesse gelesen und entpackt werden muesste. Beim
    # 3DO-Logo (Hochformat) waeren das bei 900 px Breite 1729 Zeilen und
    # 6 MB im Speicher, fuer ein Bild, das am Ende 234 px breit
    # erscheint. Deshalb die Deckelung - die vorhandenen Logos liegen
    # ohnehin alle unter 410 Zeilen.
    skala = breite / img.width
    if img.height * skala > max_hoehe:
        skala = max_hoehe / img.height
    zb = max(1, round(img.width * skala))
    zh = max(1, round(img.height * skala))
    if (zb, zh) != img.size:
        img = img.resize((zb, zh), Image.LANCZOS)
    grund = Image.new("RGBA", img.size, PANEL + (255,))
    grund.alpha_composite(img)
    rgb = grund.convert("RGB").tobytes()
    pix = bytearray(len(rgb) // 3 * 4)
    pix[0::4] = rgb[2::3]
    pix[1::4] = rgb[1::3]
    pix[2::4] = rgb[0::3]
    daten = (b"ART1" + struct.pack("<HH", grund.width, grund.height)
             + zlib.compress(bytes(pix), 9))
    with open(out_path, "wb") as f:
        f.write(daten)
    return grund.width, grund.height, len(daten)


def aufbereiten(pfad, fluten=False, aufhellen=False, toleranz=40,
                karo=False):
    img = Image.open(pfad).convert("RGBA")
    if fluten:
        img = hintergrund_fluten(img, toleranz)
    if karo:
        img = karo_entfernen(img)
    if aufhellen:
        img = dunkles_aufhellen(img)
    return zuschneiden(img)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("quelle", help="Logo-Bild (PNG/JPG/WEBP)")
    ap.add_argument("ziel", help="Ziel-.art (Dateiname = Systemschluessel)")
    ap.add_argument("--fluten", action="store_true",
                    help="einfarbigen Hintergrund vom Rand her entfernen")
    ap.add_argument("--aufhellen", action="store_true",
                    help="schwarze Schrift in Weiss drehen (sonst auf der "
                         "dunklen Karte unsichtbar)")
    ap.add_argument("--karo", action="store_true",
                    help="eingemaltes Transparenz-Schachbrett entfernen "
                         "(helle, farblose Flaechen im ganzen Bild)")
    ap.add_argument("--toleranz", type=int, default=40,
                    help="Farbtoleranz der Flutfuellung (Standard 40)")
    ap.add_argument("--breite", type=int, default=ZIEL_BREITE)
    ap.add_argument("--max-hoehe", type=int, default=MAX_HOEHE,
                    dest="max_hoehe")
    ap.add_argument("--vorschau", help="zusaetzlich als PNG zum Ansehen")
    args = ap.parse_args()

    img = aufbereiten(args.quelle, args.fluten, args.aufhellen,
                      args.toleranz, args.karo)
    w, h, n = schreiben(img, args.ziel, args.breite, args.max_hoehe)
    print("%s -> %s  (%dx%d, %d Bytes)"
          % (os.path.basename(args.quelle), args.ziel, w, h, n))
    if args.vorschau:
        vor = Image.new("RGBA", img.size, PANEL + (255,))
        vor.alpha_composite(img)
        vor.convert("RGB").save(args.vorschau)
        print("Vorschau: %s" % args.vorschau)


if __name__ == "__main__":
    main()
