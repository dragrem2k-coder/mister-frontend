#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DIAGNOSE: woraus besteht ein kaltes Cover eigentlich?

Laeuft sowohl hier als auch AUF DEM MISTER - dort ist die Messung, auf
die es ankommt:

    python3 /media/fat/frontend/../tools/diag_kaltes_cover.py
    (oder aus dem entpackten Update-Ordner heraus)

WARUM DAS SKRIPT EXISTIERT. Nach Build 115 lag die Vermutung nahe, die
Schutzschwellen aus den Builds 105 und 107 seien jetzt zu vorsichtig:
sie wurden fuer ein Cover gebaut, dessen Dekodierung 200-500 ms
dauerte, und die Dekodierung ist seither um ein Vielfaches schneller.

Die Messung hier hat das widerlegt. Ein kaltes Cover besteht aus ZWEI
Teilen, und nur einer davon ist schneller geworden:

    PNG dekodieren, alter Python-Weg   341,8 ms
    PNG dekodieren, libpng               3,9 ms
    auf HDMI-Kastengroesse verkleinern 102,0 ms   <- unveraendert

Das Verkleinern ist Flaechenmittelung in reinem Python (siehe
_verkleinern_flaechenmittel in fe/art.py) und war frueher der kleinere
Posten. Jetzt ist es fast der einzige. Die Schwellen bleiben also
noetig - aber der Hebel liegt woanders als gedacht.

Das Skript misst genau diese Aufteilung an ECHTEN Covern der jeweiligen
Karte, damit die naechste Entscheidung nicht wieder auf einer
Hochrechnung steht.
"""
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
for p in (os.path.join(_REPO, "frontend"), "/media/fat/frontend"):
    if os.path.isdir(p) and p not in sys.path:
        sys.path.insert(0, p)

import fe.art as A                                      # noqa: E402
try:
    import fe.bildlib as B
except ImportError:
    B = None

# Kastengroessen, wie sie das Frontend tatsaechlich benutzt - grob die
# Werte aus layout_items() fuer die beiden Faelle.
KAESTEN = (("CRT   ", 110, 150), ("HDMI  ", 360, 420))

SUCHORTE = (
    "/media/fat/frontend/art_hd",
    "/media/fat/frontend/art",
    "/media/fat/docs",
)


def bestes(fn, n=3, runden=3):
    """Bestwert statt Mittelwert - Stoerungen koennen nur bremsen."""
    b = None
    for _ in range(runden):
        t0 = time.perf_counter()
        for _ in range(n):
            fn()
        d = (time.perf_counter() - t0) / n * 1000
        b = d if b is None or d < b else b
    return b


def bilder_finden(grenze=6):
    """Ein paar echte Cover von dieser Karte - .art, PNG und JPG
    gemischt, damit alle drei Wege vorkommen."""
    gefunden = []
    for ort in SUCHORTE:
        if not os.path.isdir(ort):
            continue
        for wurzel, _dirs, dateien in os.walk(ort):
            for fn in dateien:
                if fn.lower().endswith((".art", ".png", ".jpg", ".jpeg")):
                    gefunden.append(os.path.join(wurzel, fn))
                    if len(gefunden) >= grenze * 4:
                        break
            if len(gefunden) >= grenze * 4:
                break
        if len(gefunden) >= grenze * 4:
            break
    # Moeglichst gemischt: je Endung ein paar.
    nach_art = {}
    for p in gefunden:
        nach_art.setdefault(os.path.splitext(p)[1].lower(), []).append(p)
    auswahl = []
    for endung in (".art", ".png", ".jpg", ".jpeg"):
        auswahl.extend(nach_art.get(endung, [])[:2])
    return auswahl[:grenze]


print("Bibliotheken:",
      "libpng " + ("ja" if B and B.png_verfuegbar() else "NEIN") + ",",
      "TurboJPEG " + ("ja" if B and B.verfuegbar() else "NEIN") + ",",
      "in fe/art.py aktiv " + ("ja" if A._BILDLIB is not None else "NEIN"))
print()

bilder = bilder_finden()
ersatz_ordner = None
if not bilder:
    # Auf einem Entwicklungsrechner gibt es diese Ordner nicht. Statt
    # gar nichts zu messen, werden Cover in typischer Groesse erzeugt -
    # die Aufteilung zwischen Dekodieren und Verkleinern ist genau so
    # aussagekraeftig, nur eben nicht an echten Dateien.
    print("Keine Cover auf dieser Maschine gefunden - es werden welche")
    print("in typischer Groesse (424x768) erzeugt.")
    print()
    try:
        import struct
        import tempfile
        import zlib
        from PIL import Image
    except ImportError:
        print("Dafuer fehlt Pillow. Gesucht wurde in:")
        for o in SUCHORTE:
            print("   ", o)
        sys.exit(0)
    ersatz_ordner = tempfile.mkdtemp(prefix="kaltes_cover_")
    im = Image.new("RGB", (424, 768))
    q = im.load()
    for y in range(768):
        for x in range(424):
            q[x, y] = ((x * 3) % 256, (y * 2) % 256, (x + y) % 256)
    p_png = os.path.join(ersatz_ordner, "muster.png")
    im.save(p_png)
    p_jpg = os.path.join(ersatz_ordner, "muster.jpg")
    im.save(p_jpg, quality=90)
    p_art = os.path.join(ersatz_ordner, "muster.art")
    roh = im.convert("RGBA").tobytes()
    # RGBA -> BGRA, wie unser Format es erwartet.
    b = bytearray(roh)
    b[0::4], b[2::4] = bytes(roh[2::4]), bytes(roh[0::4])
    with open(p_art, "wb") as fh:
        fh.write(b"ART1" + struct.pack("<HH", 424, 768)
                 + zlib.compress(bytes(b)))
    bilder = [p_art, p_png, p_jpg]

print("%-34s %9s %9s %9s %9s" % ("Datei", "lesen", "dekod.", "verklein.",
                                 "gesamt"))
print("-" * 74)

summe = {}
for pfad in bilder:
    try:
        roh = open(pfad, "rb").read()
    except OSError as e:
        print("%-34s  %s" % (os.path.basename(pfad)[:34], e))
        continue

    t_lesen = bestes(lambda: open(pfad, "rb").read(), 3)

    for name, bw, bh in KAESTEN:
        # Genau der Weg, den der Zeichenpfad geht - einschliesslich des
        # verkleinerten Dekodierens aus Build 116. Eine Messung an
        # zusammengebastelten Einzelschritten haette genau das
        # uebersehen.
        cache = A.ArtCache()
        t_dek = bestes(lambda: A.ArtCache().get(pfad, bw, bh), 3, 2)
        basis = cache.get(pfad, bw, bh)
        if not basis:
            print("%-34s  nicht lesbar" % os.path.basename(pfad)[:34])
            break
        w, h, pix = basis
        nw, nh = cache.nativ.get(pfad, (w, h))
        if nw <= bw and nh <= bh:
            faktor = max(1, min(bw // nw, bh // nh, 10))
            if faktor == 1:
                t_skal = 0.0
            else:
                t_skal = bestes(
                    lambda: A._hochskalieren(pix, w, h, faktor), 3, 2)
        else:
            sc = min(bw / nw, bh / nh)
            tw, th = max(1, int(nw * sc)), max(1, int(nh * sc))
            t_skal = bestes(
                lambda: A._verkleinern_flaechenmittel(pix, w, h, tw, th),
                3, 2)
        gesamt = t_lesen + t_dek + t_skal
        print("%-28s %s %7.1f %9.1f %9.1f %9.1f"
              % (os.path.basename(pfad)[:28], name,
                 t_lesen, t_dek, t_skal, gesamt))
        eintrag = summe.setdefault(name, [0.0, 0.0, 0.0, 0])
        eintrag[0] += t_lesen
        eintrag[1] += t_dek
        eintrag[2] += t_skal
        eintrag[3] += 1

print("-" * 74)
for name, (le, de, sk, n) in summe.items():
    if not n:
        continue
    g = (le + de + sk) / n
    print("Mittel %s  lesen %.1f ms, dekodieren %.1f ms, "
          "verkleinern %.1f ms  = %.1f ms"
          % (name, le / n, de / n, sk / n, g))
    if g > 0:
        print("        Anteil: lesen %2.0f %%, dekodieren %2.0f %%, "
              "verkleinern %2.0f %%"
              % (le / n / g * 100, de / n / g * 100, sk / n / g * 100))

print()
print("WORAUF ES ANKOMMT: steht 'verkleinern' bei ueber der Haelfte,")
print("bringt ein Lockern der Schutzschwellen nichts - dann muss das")
print("Verkleinern billiger werden, nicht die Schwelle groesser.")
