#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft, dass der Rechenkern des PC-Werkzeugs bitgenau dasselbe
liefert wie fe/art.py (Build 145).

WARUM DIESER TEST DER WICHTIGSTE DES PAKETS IST

pc_tools/dragend_kern.py enthaelt Kopien von zielmass(),
_verkleinern_flaechenmittel() und _hochskalieren(). Kopien laufen
auseinander - das ist keine Frage des Ob, sondern des Wann. Und hier
faellt es nicht auf: der PC legt Miniaturen ab, die anders aussehen als
die des MiSTer, aber beide fuer sich sehen richtig aus. Man haette
zweierlei Bilder im selben Zwischenspeicher, und niemand haette einen
Anhaltspunkt.

Deshalb wird hier mit Zufallsgroessen und Zufallsbildern gegen das
Original verglichen - Byte fuer Byte, nicht "sieht aehnlich aus".

Geprueft wird ausserdem das Dateiformat: Kennung, Masse, gepackter
Inhalt, und die Acht-Byte-Marke fuer "das Original passt schon".

Ausfuehren:
    python3 tools/test_pc_kern.py
"""
import os
import sys
import random
import struct
import zlib

_HIER = os.path.dirname(os.path.abspath(__file__))
_WURZEL = os.path.dirname(_HIER)
sys.path.insert(0, os.path.join(_WURZEL, "frontend"))
sys.path.insert(0, os.path.join(_WURZEL, "pc_tools"))

import fe.art as ART                                        # noqa: E402
import dragend_kern as KERN                                 # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


# ---------------------------------------------------------------------------
print("Test 1: die Verfahrensnummer stimmt ueberein")
# ---------------------------------------------------------------------------
check("THUMB_ALGO_VERSION identisch",
      KERN.THUMB_ALGO_VERSION == ART.THUMB_ALGO_VERSION,
      "PC %r / Frontend %r" % (KERN.THUMB_ALGO_VERSION,
                               ART.THUMB_ALGO_VERSION))

# ---------------------------------------------------------------------------
print("Test 2: zielmass() - 200 Zufallsfaelle")
# ---------------------------------------------------------------------------
random.seed(20260918)
abw = []
for _ in range(200):
    nw = random.randint(1, 2000)
    nh = random.randint(1, 2000)
    mw = random.randint(1, 900)
    mh = random.randint(1, 900)
    if ART.zielmass(nw, nh, mw, mh) != KERN.zielmass(nw, nh, mw, mh):
        abw.append((nw, nh, mw, mh))
check("alle 200 Faelle gleich", not abw, str(abw[:3]))

# ---------------------------------------------------------------------------
print("Test 3: Verkleinern - 40 Zufallsbilder, Byte fuer Byte")
# ---------------------------------------------------------------------------
abw = []
for nr in range(40):
    w = random.randint(8, 240)
    h = random.randint(8, 240)
    # Beide Wege abdecken: schwache Verkleinerung (der schnelle Weg mit
    # hoechstens zwei Quellspalten) und starke (der allgemeine Weg).
    if nr % 2:
        tw = max(1, int(w / random.uniform(1.1, 2.9)))
        th = max(1, int(h / random.uniform(1.1, 2.9)))
    else:
        tw = max(1, int(w / random.uniform(3.1, 9.0)))
        th = max(1, int(h / random.uniform(3.1, 9.0)))
    pix = bytes(random.getrandbits(8) for _ in range(w * h * 4))
    a = ART._verkleinern_flaechenmittel(pix, w, h, tw, th)
    b = KERN.verkleinern_flaechenmittel(pix, w, h, tw, th)
    if a != b:
        unterschiede = sum(1 for x, y in zip(a or b"", b or b"") if x != y)
        abw.append("%dx%d->%dx%d (%d Bytes)"
                   % (w, h, tw, th, unterschiede))
check("alle 40 Bilder bitgenau gleich", not abw, "; ".join(abw[:3]))

# ---------------------------------------------------------------------------
print("Test 4: Vergroessern - 20 Zufallsbilder, Byte fuer Byte")
# ---------------------------------------------------------------------------
abw = []
for _ in range(20):
    w = random.randint(4, 60)
    h = random.randint(4, 60)
    scale = random.randint(2, 6)
    pix = bytes(random.getrandbits(8) for _ in range(w * h * 4))
    aw, ah, a = ART._hochskalieren(pix, w, h, scale)
    bw_, bh_, b = KERN.hochskalieren(pix, w, h, scale)
    if (aw, ah) != (bw_, bh_) or bytes(a) != bytes(b):
        abw.append("%dx%d x%d" % (w, h, scale))
check("alle 20 Bilder bitgenau gleich", not abw, "; ".join(abw[:3]))

# ---------------------------------------------------------------------------
print("Test 5: Dateiformat")
# ---------------------------------------------------------------------------
pix = bytes(random.getrandbits(8) for _ in range(6 * 5 * 4))
roh = KERN.art_bytes(6, 5, pix)
check("Kennung ART1", roh[:4] == b"ART1", repr(roh[:4]))
tw, th = struct.unpack("<HH", roh[4:8])
check("Masse im Kopf", (tw, th) == (6, 5), "%dx%d" % (tw, th))
check("Inhalt entpackt sich zurueck", zlib.decompress(roh[8:]) == pix)

marke = KERN.MARKE_ORIGINAL_PASST
check("Marke ist acht Byte lang", len(marke) == 8, str(len(marke)))
check("Marke traegt die Kennung ARTO", marke[:4] == ART._MARKE,
      repr(marke[:4]))
check("Marke hat Masse 0x0", struct.unpack("<HH", marke[4:]) == (0, 0))

# ---------------------------------------------------------------------------
print("Test 6: Ablageort im Zwischenspeicher")
# ---------------------------------------------------------------------------
schluessel = ART._thumb_cache_key("/media/fat/frontend/art_hd/SNES/x.png",
                                  360, 420)
ART.thumb_cache_modus_setzen(True)
erwartet = ART._thumb_cache_path(schluessel)
bekommen = KERN.cache_pfad(ART.THUMB_CACHE_BASE, True, schluessel)
check("HD-Pfad identisch", erwartet == bekommen,
      "" if erwartet == bekommen else "%s gegen %s" % (erwartet, bekommen))
ART.thumb_cache_modus_setzen(False)
erwartet = ART._thumb_cache_path(schluessel)
bekommen = KERN.cache_pfad(ART.THUMB_CACHE_BASE, False, schluessel)
check("SD-Pfad identisch", erwartet == bekommen,
      "" if erwartet == bekommen else "%s gegen %s" % (erwartet, bekommen))
ART.thumb_cache_modus_setzen(True)

# ---------------------------------------------------------------------------
print("Test 7: miniatur_bauen() trifft dieselben Entscheidungen")
# ---------------------------------------------------------------------------
# a) Original passt exakt -> Marke
w, h = 100, 120
pix = bytes(random.getrandbits(8) for _ in range(w * h * 4))
check("passendes Original ergibt die Marke",
      KERN.miniatur_bauen(w, h, pix, 150, 150) == KERN.MARKE_ORIGINAL_PASST)

# b) Original klein genug fuer ganzzahliges Vergroessern
erg = KERN.miniatur_bauen(w, h, pix, 300, 300)
sw, sh = struct.unpack("<HH", erg[4:8])
scale = max(1, min(300 // w, 300 // h, 10))
check("Vergroessern nimmt denselben Faktor",
      (sw, sh) == (w * scale, h * scale),
      "%dx%d bei Faktor %d" % (sw, sh, scale))

# c) Original zu gross -> Verkleinern auf zielmass()
erg = KERN.miniatur_bauen(w, h, pix, 40, 40)
sw, sh = struct.unpack("<HH", erg[4:8])
check("Verkleinern trifft zielmass()",
      (sw, sh) == ART.zielmass(w, h, 40, 40),
      "%dx%d gegen %s" % (sw, sh, ART.zielmass(w, h, 40, 40)))
check("Inhalt entspricht der Flaechenmittelung",
      zlib.decompress(erg[8:])
      == ART._verkleinern_flaechenmittel(pix, w, h, sw, sh))

# ---------------------------------------------------------------------------
print("Test 8: Packstufen sind untereinander vertraeglich (Build 154)")
# ---------------------------------------------------------------------------
# Das Frontend schreibt seit Build 154 mit Stufe 1, das PC-Werkzeug
# weiterhin mit 6. Beide Dateien muessen von beiden Seiten lesbar sein -
# sonst waere der Zwischenspeicher zwischen MiSTer und PC gespalten.
pix = bytes(random.getrandbits(8) for _ in range(20 * 15 * 4))
vom_pc = KERN.art_bytes(20, 15, pix)
vom_mister = b"ART1" + struct.pack("<HH", 20, 15) + zlib.compress(pix, 1)
check("PC-Datei entpackt sich zu denselben Bildpunkten",
      zlib.decompress(vom_pc[8:]) == pix)
check("MiSTer-Datei entpackt sich zu denselben Bildpunkten",
      zlib.decompress(vom_mister[8:]) == pix)
check("Kopf ist in beiden gleich", vom_pc[:8] == vom_mister[:8])
check("nur die Packung unterscheidet sich", vom_pc[8:] != vom_mister[8:])

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  - " + x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
