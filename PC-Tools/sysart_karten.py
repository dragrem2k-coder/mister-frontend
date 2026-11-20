#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sysart_karten.py - Kategorie-Abzeichen aus einem Kartenblatt (Build 331)
=========================================================================
Laeuft auf dem PC, NICHT auf dem MiSTer. Benoetigt Pillow.

NUTZERWUNSCH: "die abzeichen fuer die andere ansicht bitte diese hier!
alle jeweils anpassen so wie die anderen auch sind" - dazu ein Blatt mit
vier Pixel-Karten: Amiga, Amstrad CPC ("HOME COMPUTER"), PC und
Commodore 64.

WARUM EIN VIERTES WERKZEUG
--------------------------
Die Vorlage ist anders gebaut als alles bisher:

  * sysart_abzeichen.py schneidet RUNDE beige Abzeichen mit Text darunter
    aus einem Blatt - das Abzeichen ist dort schon fertig.
  * Hier liegt jedes Geraet auf einer WEISSEN Karte mit farbigem Rand und
    einem dunkelblauen Schriftband. So, wie es ist, stuende auf der
    dunklen Hauptseite ein weisser Kasten zwischen lauter beigen Ovalen.

"So wie die anderen" heisst deshalb: das Geraet freistellen und in
dieselbe Form bringen, die alle 60 Abzeichen haben - beiges Oval mit
treppiger Pixelkante, Geraet oben drin, Name in dunkler, schmaler,
fetter Schrift darunter, Kachel 320x420 auf C_PANEL. Die Masse sind von
den vorhandenen Abzeichen abgenommen (siehe unten), nicht geschaetzt.

DIE BESCHRIFTUNG
----------------
Sie wird neu gesetzt und nicht aus dem Schriftband uebernommen: weisse
Schrift auf Dunkelblau passt nicht zu den anderen 60 (dunkle Schrift auf
Beige). Der Text je Kategorie steht in KARTEN. "HOME COMPUTER" vom Blatt
wird dabei zu "AMSTRAD CPC" - die Kategorie heisst so, und ein Abzeichen
soll sagen, welches System dahinter steckt.

Aufruf:
    python3 PC-Tools/sysart_karten.py blatt.png --ziel frontend/sysart \\
        --vorschau /tmp/karten.png
"""

import argparse
import os
import struct
import sys
import zlib
from collections import deque

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.exit("Pillow fehlt:  pip install Pillow")

# Muss C_PANEL in frontend.py entsprechen (tools/test_sysart_logos.py).
C_PANEL = (28, 32, 44)

# Abgenommen an den vorhandenen Abzeichen (COMPUTER.art: Oval x 42-276,
# y 14-301; Beige an sechs Stellen 190-197 / 163-176 / 130-136, also
# praktisch flach; Schrift fast schwarz). Das Geraet fuellt dort rund
# x 60-245, y 40-215, der Name sitzt bei y 235-270.
KACHEL_B, KACHEL_H = 320, 420
OVAL_B, OVAL_H, OVAL_Y = 236, 288, 14
BEIGE = (195, 173, 135)
SCHRIFT = (31, 30, 26)
TREPPE = 2                 # Kantenstufe der Pixelkante, wie beim Original

# Das Blatt: vier Karten im Raster 2x2, in Lesereihenfolge.
KARTEN = [("AMIGA", "AMIGA"), ("AMSTRAD", "AMSTRAD CPC"),
          ("AO486", "PC"), ("C64", "COMMODORE 64")]

SCHRIFTEN = [
    "/usr/share/fonts/truetype/google-fonts/ofl/roboto/Roboto[wdth,wght].ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf",
    "C:/Windows/Fonts/arialnb.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]


def _luecken(profil):
    raus, start = [], None
    for i, v in enumerate(profil):
        if v == 0 and start is None:
            start = i
        elif v and start is not None:
            raus.append((start, i - 1))
            start = None
    if start is not None:
        raus.append((start, len(profil) - 1))
    return raus


def karten_finden(blatt):
    """Die vier Karten als Rechtecke - an den weissen Fugen gemessen,
    nicht gerechnet (das Blatt ist nicht bildpunktgenau gerastert)."""
    b, h = blatt.size
    px = blatt.load()
    spalten = [sum(1 for y in range(0, h, 2) if min(px[x, y]) < 200)
               for x in range(b)]
    zeilen = [sum(1 for x in range(0, b, 2) if min(px[x, y]) < 200)
              for y in range(h)]

    def grenzen(profil, n):
        innen = [g for g in _luecken(profil)
                 if g[0] > 0 and g[1] < len(profil) - 1]
        innen.sort(key=lambda g: g[1] - g[0], reverse=True)
        mitte = sorted((g[0] + g[1]) // 2 for g in innen[:n - 1])
        return [0] + mitte + [len(profil)]
    xs, ys = grenzen(spalten, 2), grenzen(zeilen, 2)
    raus = []
    for r in range(2):
        for c in range(2):
            raus.append((xs[c], ys[r], xs[c + 1], ys[r + 1]))
    return raus


def _band_oben(karte):
    """Oberkante des dunkelblauen Schriftbands - die erste Zeile im
    unteren Drittel, die zu mehr als einem Viertel dunkelblau ist."""
    b, h = karte.size
    px = karte.load()
    for y in range(h * 2 // 3, h):
        n = sum(1 for x in range(0, b, 2)
                if px[x, y][2] > px[x, y][0] + 25 and sum(px[x, y]) < 250)
        if n > b * 0.25 / 2:
            return y
    return h


def geraet_freistellen(karte, rand=30, toleranz=45):
    """Das Geraet ohne Kartengrund: geflutet wird das Weiss vom Rand des
    Ausschnitts her (innerhalb des farbigen Kartenrands, oberhalb des
    Schriftbands). Verglichen wird mit Weiss, nicht mit dem Nachbarn -
    die Pixelgrafik hat harte Kanten, einen Verlauf gibt es nicht."""
    oben = _band_oben(karte)
    feld = karte.crop((rand, rand, karte.width - rand, oben - 4))
    feld = feld.convert("RGBA")
    b, h = feld.size
    px = feld.load()

    def weiss(c):
        return (255 - c[0]) + (255 - c[1]) + (255 - c[2]) <= toleranz
    q = deque()
    for x in range(b):
        q.append((x, 0))
        q.append((x, h - 1))
    for y in range(h):
        q.append((0, y))
        q.append((b - 1, y))
    while q:
        x, y = q.popleft()
        if not (0 <= x < b and 0 <= y < h):
            continue
        c = px[x, y]
        if c[3] == 0 or not weiss(c):
            continue
        px[x, y] = (0, 0, 0, 0)
        q.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))
    _inseln_weg(feld)
    box = feld.getchannel("A").getbbox()
    return feld.crop(box) if box else feld


def _inseln_weg(bild, anteil=0.03):
    """Was nicht mit dem Geraet zusammenhaengt und klein ist, kommt weg -
    Reste des farbigen Kartenrands an den abgerundeten Ecken (im ersten
    Versuch standen sie als duenne Linien links, rechts und oben)."""
    b, h = bild.size
    px = bild.load()
    gesehen = bytearray(b * h)
    flaechen = []
    for sy in range(h):
        for sx in range(b):
            if gesehen[sy * b + sx] or px[sx, sy][3] == 0:
                continue
            f, q = [], deque([(sx, sy)])
            gesehen[sy * b + sx] = 1
            while q:
                x, y = q.popleft()
                f.append((x, y))
                for nx in (x - 1, x, x + 1):
                    for ny in (y - 1, y, y + 1):
                        if (0 <= nx < b and 0 <= ny < h
                                and not gesehen[ny * b + nx]
                                and px[nx, ny][3] != 0):
                            gesehen[ny * b + nx] = 1
                            q.append((nx, ny))
            flaechen.append(f)
    if not flaechen:
        return
    groesste = max(len(f) for f in flaechen)
    for f in flaechen:
        if len(f) < groesste * anteil:
            for x, y in f:
                px[x, y] = (0, 0, 0, 0)


def _oval_maske():
    """Oval mit Treppenkante: klein gezeichnet, hart vergroessert."""
    kb, kh = OVAL_B // TREPPE, OVAL_H // TREPPE
    klein = Image.new("L", (kb, kh), 0)
    ImageDraw.Draw(klein).ellipse((0, 0, kb - 1, kh - 1), fill=255)
    return klein.resize((kb * TREPPE, kh * TREPPE), Image.NEAREST)


def _schrift(groesse):
    for pfad in SCHRIFTEN:
        if not os.path.isfile(pfad):
            continue
        try:
            f = ImageFont.truetype(pfad, groesse)
        except OSError:
            continue
        try:
            # Roboto ist eine variable Schrift; die Achsen stehen in der
            # Reihenfolge Gewicht, Breite (get_variation_axes()). Schwarz
            # (900) und schmal (75) - so nah an den Originalen wie
            # moeglich. Im ersten Versuch stand die Reihenfolge falsch
            # herum und die Schrift kam duenn heraus.
            f.set_variation_by_axes([900, 75])
        except Exception:                                # noqa: BLE001
            pass
        return f
    return ImageFont.load_default()


def _text_bild(text, max_b, max_h):
    """Der Name, so gross wie er in max_b x max_h passt - doppelt so
    gross gesetzt und verkleinert, damit die Kante so weich wird wie bei
    den Vorlagen (die sind gerasterte Pixelgrafik, nicht gestochen)."""
    for g in range(max_h * 2, 8, -1):
        f = _schrift(g)
        box = f.getbbox(text)
        tb, th = box[2] - box[0], box[3] - box[1]
        if tb <= max_b * 2 and th <= max_h * 2:
            bild = Image.new("L", (tb + 4, th + 4), 0)
            ImageDraw.Draw(bild).text((2 - box[0], 2 - box[1]), text,
                                      font=f, fill=255)
            return bild.resize(((tb + 4) // 2, (th + 4) // 2), Image.LANCZOS)
    return Image.new("L", (1, 1), 0)


def abzeichen(geraet, text):
    """Geraet + Name auf die einheitliche Kachel."""
    kachel = Image.new("RGB", (KACHEL_B, KACHEL_H), C_PANEL)
    maske = _oval_maske()
    ox = (KACHEL_B - maske.width) // 2
    kachel.paste(Image.new("RGB", maske.size, BEIGE), (ox, OVAL_Y), maske)
    # Das Geraet: in den oberen Teil des Ovals, so breit wie dort Platz
    # ist. Die Box ist so gewaehlt, dass auch die Ecken eines breiten
    # Geraets (Amiga mit Laufwerk und Maus) noch im Oval liegen.
    feld_b, feld_h, feld_y = 212, 172, OVAL_Y + 30
    f = min(feld_b / float(geraet.width), feld_h / float(geraet.height))
    gb = max(1, int(round(geraet.width * f)))
    gh = max(1, int(round(geraet.height * f)))
    g = geraet.resize((gb, gh), Image.LANCZOS)
    kachel.paste(g, ((KACHEL_B - gb) // 2, feld_y + (feld_h - gh)),
                 g.getchannel("A"))
    # Der Name: unter dem Geraet, in der Breite, die das Oval auf dieser
    # Hoehe noch hat (Ellipsengleichung, mit Luft zum Rand).
    ty = feld_y + feld_h + 18
    th = 32
    a, bb = OVAL_B / 2.0, OVAL_H / 2.0
    dy = abs((ty + th) - (OVAL_Y + bb))
    halb = a * max(0.0, 1 - (dy / bb) ** 2) ** 0.5
    tb_max = int(2 * halb - 20)
    tmaske = _text_bild(text, tb_max, th)
    tx = (KACHEL_B - tmaske.width) // 2
    kachel.paste(Image.new("RGB", tmaske.size, SCHRIFT), (tx, ty + (th - tmaske.height) // 2),
                 tmaske)
    return kachel


def schreiben(bild, pfad):
    """.art: b"ART1" + uint16 Breite + uint16 Hoehe + zlib(BGRX)."""
    rgb = bild.convert("RGB").tobytes()
    pix = bytearray(len(rgb) // 3 * 4)
    pix[0::4] = rgb[2::3]
    pix[1::4] = rgb[1::3]
    pix[2::4] = rgb[0::3]
    daten = (b"ART1" + struct.pack("<HH", bild.width, bild.height)
             + zlib.compress(bytes(pix), 9))
    tmp = pfad + ".tmp"
    with open(tmp, "wb") as f:
        f.write(daten)
    os.replace(tmp, pfad)
    return len(daten)


def main(argv=None):
    p = argparse.ArgumentParser(description="Kartenblatt -> Abzeichen")
    p.add_argument("blatt")
    p.add_argument("--ziel", default="frontend/sysart")
    p.add_argument("--vorschau", default=None)
    a = p.parse_args(argv)
    blatt = Image.open(a.blatt).convert("RGB")
    rechtecke = karten_finden(blatt)
    os.makedirs(a.ziel, exist_ok=True)
    fertig = []
    for (schluessel, text), r in zip(KARTEN, rechtecke):
        geraet = geraet_freistellen(blatt.crop(r))
        bild = abzeichen(geraet, text)
        n = schreiben(bild, os.path.join(a.ziel, schluessel + ".art"))
        print("%-10s %-14s %dx%d  %6.1f KB" % (schluessel, text, bild.width,
                                              bild.height, n / 1024.0))
        fertig.append(bild)
    if a.vorschau:
        bogen = Image.new("RGB", (len(fertig) * KACHEL_B, KACHEL_H),
                          (16, 18, 24))
        for i, b in enumerate(fertig):
            bogen.paste(b, (i * KACHEL_B, 0))
        bogen.save(a.vorschau)
        print("Vorschau:", a.vorschau)
    return 0


if __name__ == "__main__":
    sys.exit(main())
