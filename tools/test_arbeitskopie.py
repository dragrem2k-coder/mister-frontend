#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Die JPEG-Arbeitskopie und was daran haengt (Build 129).

WOZU DAS GANZE. "Miniaturen vorbereiten" verkleinert jedes Cover drei
Mal. Die Flaechenmittelung liest dabei JEDEN Quellpunkt - es zaehlt
also, wie gross das Bild ist, aus dem gerechnet wird. TurboJPEG kann
verkleinert DEKODIEREN (1/2, 1/4, 1/8 direkt aus dem Dekoder), libpng
kann das nicht. Gemessen an einem 900x1200-Cover mit den drei
HDMI-Kaesten: 689 ms aus dem PNG, 416 ms aus dem JPEG.

DER FEHLER, DEN DIESER TEST ALS ERSTES FESTHAELT (Test 1). Build 128
hat in prewarm_thumb_mehrfach() EINMAL auf das groesste Ziel dekodiert
und alle Kaesten daraus gerechnet. Bei PNG ist das richtig. Bei JPEG
war es falsch, und zwar nicht nur langsamer:

Der ZEICHENPFAD fragt sein Bild je Kasten an (ArtCache.get(path,
max_w, max_h)) und bekommt fuer eine kleine Kachel ein 1/8 dekodiertes
Bild. Die Vorbereitung rechnete dieselbe Kachel aus dem grossen Bild -
andere Bildpunkte. Die gespeicherte Miniatur war damit NICHT mehr
bit-identisch zu einer frisch berechneten, und genau das verlangt der
Modul-Kommentar in fe/art.py.

Aufgefallen ist es nicht, weil tools/test_vorbereiten_tempo.py in
Build 128 nur PNG-Quellen benutzt hat. Die Bitgleichheit war dort
geprueft - aber nur fuer das Format, bei dem sie ohnehin galt.

Ausfuehren:
    python3 tools/test_arbeitskopie.py
"""
import os
import shutil
import struct
import sys
import tempfile
import zlib

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)

import _harness as H                                    # noqa: E402

fm = H.fm
sys.path.insert(0, os.path.join(_REPO, "frontend"))
import fe.art as A                                      # noqa: E402
import fe.bildlib as BL                                 # noqa: E402
import mister_boxart as MB                              # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


TMP = tempfile.mkdtemp(prefix="arbeitskopie_")
A.THUMB_CACHE_DIR = os.path.join(TMP, "cache")
os.makedirs(A.THUMB_CACHE_DIR)

KAESTEN = [(733, 909), (124, 166), (411, 548)]


def png_bauen(pfad, w, h):
    """Ein fotoartiges PNG von Hand. Bewusst KEINE Flaeche: bei
    einfarbigen Bildern ist jede Verkleinerung dasselbe Ergebnis, und
    ein Unterschied zwischen zwei Wegen faellt gar nicht auf."""
    zeilen = []
    for y in range(h):
        r = bytearray([0])
        for x in range(w):
            r += bytes(((x * 7 + y * 3) % 256, (x * 3 + y * 11) % 256,
                        (x * 13 + y * 5) % 256))
        zeilen.append(bytes(r))

    def ch(typ, daten):
        return (struct.pack(">I", len(daten)) + typ + daten
                + struct.pack(">I", zlib.crc32(typ + daten) & 0xffffffff))

    with open(pfad, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n"
                + ch(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                + ch(b"IDAT", zlib.compress(b"".join(zeilen), 6))
                + ch(b"IEND", b""))
    return pfad


def cache_leeren():
    shutil.rmtree(A.THUMB_CACHE_DIR, ignore_errors=True)
    os.makedirs(A.THUMB_CACHE_DIR)


# ---------------------------------------------------------------------
print("Test 1: bei JPEG muss je Kasten EINZELN dekodiert werden")
if not BL.verfuegbar():
    print("       (TurboJPEG nicht vorhanden - Test 1-3 uebersprungen)")
else:
    p_png = png_bauen(os.path.join(TMP, "q.png"), 600, 800)
    roh = open(p_png, "rb").read()
    w, h, pix = BL.decode_png_lib(roh)

    if not BL.schreiben_verfuegbar():
        print("       (kein JPEG-Schreiber - Test 1 uebersprungen)")
        p_jpg = None
    else:
        p_jpg = os.path.join(TMP, "q.jpg")
        with open(p_jpg, "wb") as fh:
            fh.write(BL.encode_jpeg(w, h, pix, 90))

    if p_jpg:
        check("die Datei wird als verkleinert dekodierbar erkannt",
              A._skaliert_dekodierbar(p_jpg) is True)
        check("und ein PNG ausdruecklich nicht",
              A._skaliert_dekodierbar(p_png) is False)

        # DER KERN. Was die Vorbereitung ablegt, muss dasselbe sein wie
        # das, was der Zeichenpfad rechnen wuerde. Der Zeichenpfad geht
        # ueber prewarm_thumb() je Kasten - also muss die
        # Mehrfach-Fassung dort genauso herauskommen.
        cache_leeren()
        A.prewarm_thumb_mehrfach(p_jpg, KAESTEN)
        ueber_mehrfach = [A._thumb_cache_get(p_jpg, *k) for k in KAESTEN]
        cache_leeren()
        for k in KAESTEN:
            A.prewarm_thumb(p_jpg, *k)
        einzeln = [A._thumb_cache_get(p_jpg, *k) for k in KAESTEN]
        check("JPEG: Mehrfach-Fassung == Einzelaufrufe, bitgenau",
              ueber_mehrfach == einzeln,
              "" if ueber_mehrfach == einzeln else "unterschiedlich")

        # Und die Gegenprobe, die den Build-128-Fehler beschreibt:
        # gemeinsames Dekodieren ergaebe ETWAS ANDERES. Waeren beide
        # gleich, wuerde dieser Test nichts aussagen.
        cache_leeren()
        gelesen = A.original_lesen(p_jpg, 733, 909)
        anders = A._prewarm_aus_gelesenem(p_jpg, 124, 166, gelesen)
        gemeinsam = A._thumb_cache_get(p_jpg, 124, 166)
        cache_leeren()
        A.prewarm_thumb(p_jpg, 124, 166)
        richtig = A._thumb_cache_get(p_jpg, 124, 166)
        check("und der gemeinsame Weg waere bei JPEG wirklich anders "
              "(sonst pruefte die Zeile darueber nichts)",
              anders == "fertig" and gemeinsam != richtig)

        # PNG bleibt beim gemeinsamen Dekodieren - dort ist es richtig
        # UND schneller.
        cache_leeren()
        A.prewarm_thumb_mehrfach(p_png, KAESTEN)
        m_png = [A._thumb_cache_get(p_png, *k) for k in KAESTEN]
        cache_leeren()
        for k in KAESTEN:
            A.prewarm_thumb(p_png, *k)
        e_png = [A._thumb_cache_get(p_png, *k) for k in KAESTEN]
        check("PNG: beide Wege weiterhin bitgenau gleich", m_png == e_png)

# ---------------------------------------------------------------------
print()
print("Test 2: der JPEG-Schreiber")
if not BL.schreiben_verfuegbar():
    print("       (kein JPEG-Schreiber vorhanden - uebersprungen)")
else:
    # Drei Farben, an denen eine Kanalvertauschung sofort auffiele -
    # derselbe Massstab wie in tools/test_farbkanaele.py. Ein Encoder,
    # der BGRA als RGBA liest, wuerde hier Rot und Blau tauschen, und
    # niemand haette es an der Dateigroesse gemerkt.
    b, ho = 60, 40
    roh = bytearray()
    for _y in range(ho):
        for x in range(b):
            if x < 20:
                roh += bytes((0, 0, 255, 255))       # BGRA: Rot
            elif x < 40:
                roh += bytes((0, 255, 0, 255))       # Gruen
            else:
                roh += bytes((255, 0, 0, 255))       # Blau
    daten = BL.encode_jpeg(b, ho, bytes(roh), 92)
    check("es kommen JPEG-Bytes heraus",
          bool(daten) and daten[:3] == b"\xff\xd8\xff",
          "%d Byte" % (len(daten) if daten else 0))
    zurueck = BL.decode_jpeg(daten, 0, 0)
    check("und sie lassen sich wieder lesen",
          zurueck is not None and zurueck[0] == b and zurueck[1] == ho,
          repr(zurueck[:2]) if zurueck else "None")
    if zurueck:
        bw, _bh, pix = zurueck
        proben = [tuple(pix[(5 * bw + x) * 4:(5 * bw + x) * 4 + 3])
                  for x in (5, 25, 45)]
        # JPEG ist verlustbehaftet - ein paar Stufen sind normal, eine
        # Vertauschung waere 255.
        soll = [(0, 0, 255), (0, 255, 0), (255, 0, 0)]
        nah = all(abs(a - c) <= 6 for p, s in zip(proben, soll)
                  for a, c in zip(p, s))
        check("die Farbkanaele bleiben BGRA", nah, repr(proben))
    check("eine unsinnige Groesse wird abgewiesen",
          BL.encode_jpeg(0, 10, b"x" * 40) is None
          and BL.encode_jpeg(10, 10, b"zu kurz") is None)

# ---------------------------------------------------------------------
print()
print("Test 3: der Download legt Original UND Arbeitskopie hin")
ziel = os.path.join(TMP, "SNES")
os.makedirs(ziel)
p2 = png_bauen(os.path.join(TMP, "vorlage.png"), 200, 260)
inhalt = open(p2, "rb").read()
pfad = MB.original_ablegen(ziel, "Spiel (USA)", inhalt)
check("das Original liegt da", pfad and os.path.exists(pfad)
      and pfad.endswith(".png"))
check("und ist Byte fuer Byte unveraendert",
      open(pfad, "rb").read() == inhalt)
if MB._bildlib is not None and MB._bildlib.schreiben_verfuegbar():
    kopie = os.path.join(ziel, "Spiel (USA).jpg")
    check("die Arbeitskopie liegt daneben", os.path.exists(kopie),
          repr(sorted(os.listdir(ziel))))
    check("und ist ein JPEG",
          open(kopie, "rb").read(3) == b"\xff\xd8\xff")
    check("es bleibt keine Zwischendatei liegen",
          not any(".tmp" in f for f in os.listdir(ziel)),
          repr(sorted(os.listdir(ziel))))
else:
    print("       (kein JPEG-Schreiber - Arbeitskopie uebersprungen)")

# Ein JPEG vom Server bekommt KEINE zweite Kopie - es ist ja schon eine.
jpg_roh = b"\xff\xd8\xff" + b"\x00" * 100
MB.original_ablegen(ziel, "Zweites", jpg_roh)
check("ein JPEG vom Server bekommt keine zweite Kopie",
      os.path.exists(os.path.join(ziel, "Zweites.jpg"))
      and not os.path.exists(os.path.join(ziel, "Zweites.png")))
check("und etwas, das kein Bild ist, wird gar nicht abgelegt",
      MB.original_ablegen(ziel, "Muell", b"kein bild hier") is None)

# ---------------------------------------------------------------------
print()
print("Test 4: liegt beides, gewinnt die Arbeitskopie - und zwar immer")
# Bis Build 128 entschied die Reihenfolge von os.listdir(), also das
# Dateisystem. Auf zwei Karten mit demselben Inhalt konnte dasselbe
# Frontend unterschiedlich schnell sein, ohne dass irgendetwas darauf
# hingedeutet haette.
basis = os.path.join(TMP, "index")
os.makedirs(os.path.join(basis, "SNES"))
for endung in (".png", ".jpg"):
    with open(os.path.join(basis, "SNES", "Doppelt" + endung), "wb") as fh:
        fh.write(b"x")
A._art_index_cache.clear()
p = A._art_path_in(basis, "SNES", "Doppelt")
check("JPEG vor PNG", p.endswith(".jpg"), os.path.basename(p))

# Und .art schlaegt weiterhin beide - es ist bereits fertig verkleinert.
with open(os.path.join(basis, "SNES", "Doppelt.art"), "wb") as fh:
    fh.write(b"ART1")
A._art_index_cache.clear()
p = A._art_path_in(basis, "SNES", "Doppelt")
check("aber .art schlaegt beide", p.endswith(".art"), os.path.basename(p))

# Die Reihenfolge muss auch bei vielen Dateien stabil sein, nicht nur
# zufaellig richtig herum.
viele = os.path.join(TMP, "viele")
os.makedirs(os.path.join(viele, "SNES"))
for i in range(40):
    for endung in (".png", ".jpg"):
        with open(os.path.join(viele, "SNES", "S%02d%s" % (i, endung)),
                  "wb") as fh:
            fh.write(b"x")
A._art_index_cache.clear()
falsch = [i for i in range(40)
          if not A._art_path_in(viele, "SNES", "S%02d" % i).endswith(".jpg")]
check("und das gilt fuer alle 40, nicht nur fuer das erste",
      not falsch, "falsch bei %r" % falsch[:5])

# ---------------------------------------------------------------------
print()
print("Test 5: das PC-Werkzeug fasst kein Original an")
quelle = open(os.path.join(_REPO, "PC-Tools", "arbeitskopien.py"),
              encoding="utf-8", errors="replace").read()
check("es schreibt nur nach .jpg",
      'ziel = pfad[:-4] + ".jpg"' in quelle)
check("es ueberspringt die Kategorie-Abzeichen (JPEG kann kein Alpha)",
      'os.path.basename(wurzel).lower() == "sysart"' in quelle)
check("es prueft Transparenz wirklich, statt nur auf den Modus zu sehen",
      "getextrema()[0] < 255" in quelle)
check("es schreibt ueber eine Zwischendatei",
      "os.replace(tmp, ziel)" in quelle)
check("und es hat einen Probelauf",
      '"--probe"' in quelle and "nichts geschrieben" in quelle)
# Die Groessenbremse ist bewusst NICHT drin - zweimal falsch angesetzt,
# siehe den Kommentarblock dort. Ein Test, der sie wieder einfuehrt,
# waere ein Rueckschritt, deshalb steht die Abwesenheit hier fest.
check("keine Groessenbremse (sie haette den Gewinn verhindert)",
      "MAX_FAKTOR" not in quelle)

shutil.rmtree(TMP, ignore_errors=True)

print()
if fails:
    print("FEHLGESCHLAGEN (%d):" % len(fails))
    for f_ in fails:
        print("  -", f_)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
