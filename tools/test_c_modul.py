#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft libdragend gegen die Python-Fassungen - Byte fuer Byte.

WARUM DIESER TEST UNVERZICHTBAR IST

Der Miniaturen-Zwischenspeicher verlangt, dass eine gespeicherte
Miniatur bit-identisch zu einer frisch berechneten ist. Weicht die
C-Fassung auch nur in einem Byte ab, liegen zweierlei Bilder unter
demselben Schluessel - und das faellt niemandem auf, weil beide fuer
sich richtig aussehen.

Drei Fallstricke, an denen eine naive Uebersetzung scheitert und die
hier gezielt abgedeckt werden:

  1. Die Gruppengrenzen entstehen in Python ueber FLIESSKOMMA
     (int(x * w / tw)), nicht ueber Ganzzahldivision.
  2. Der schnelle Weg ("hoechstens zwei Quellspalten") zaehlt bei einer
     Ein-Pixel-Gruppe denselben Wert doppelt und verdoppelt den Teiler.
     Beide Wege werden deshalb getrennt angesteuert.
  3. Beim Verkleinern bleibt der Alphakanal 0, beim Vergroessern wird er
     mitkopiert.

Ohne Bibliothek meldet der Test das und endet erfolgreich - auf einem
Rechner ohne passendes .so ist das kein Fehler.

Ausfuehren (Bibliothek per Umgebungsvariable):
    DRAGEND_LIB=frontend/c/libdragend_x86.so python3 tools/test_c_modul.py
"""
import os
import sys
import random

_HIER = os.path.dirname(os.path.abspath(__file__))
_WURZEL = os.path.dirname(_HIER)
sys.path.insert(0, os.path.join(_WURZEL, "frontend"))

if not os.environ.get("DRAGEND_LIB"):
    # Bequemlichkeit: die hier gebaute Fassung fuer diesen Rechner
    # nehmen, falls vorhanden.
    _x86 = os.path.join(_WURZEL, "frontend", "c", "libdragend_x86.so")
    if os.path.exists(_x86):
        os.environ["DRAGEND_LIB"] = _x86

import fe.art as ART                                       # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


if ART._LIB is None:
    print("Keine libdragend geladen - nichts zu vergleichen.")
    print("(Das ist auf einem Rechner ohne passendes .so kein Fehler.)")
    sys.exit(0)

print("Bibliothek geladen, Version %d" % ART._LIB.dragend_version())

# ---------------------------------------------------------------------------
print("Test 1: Verkleinern - 150 Zufallsbilder, beide Rechenwege")
# ---------------------------------------------------------------------------
random.seed(20260919)
abw = []
schmal = allgemein = 0
for nr in range(150):
    w = random.randint(4, 260)
    h = random.randint(4, 260)
    if nr % 3 == 0:
        f = random.uniform(1.02, 2.95)     # schneller Weg
    elif nr % 3 == 1:
        f = random.uniform(3.05, 12.0)     # allgemeiner Weg
    else:
        f = random.uniform(1.0, 1.3)       # Grenzbereich
    tw = max(1, int(w / f))
    th = max(1, int(h / f))
    if tw > w or th > h:
        continue
    # Welcher Weg greift? (dieselbe Bedingung wie im Code)
    breit = max(max(1, int((x+1)*w/tw)) - int(x*w/tw) for x in range(tw))
    if breit <= 2:
        schmal += 1
    else:
        allgemein += 1
    pix = bytes(random.getrandbits(8) for _ in range(w * h * 4))
    soll = ART._verkleinern_flaechenmittel_py(pix, w, h, tw, th)
    ist = ART._verkleinern_flaechenmittel(pix, w, h, tw, th)
    if ist != soll:
        d = sum(1 for a, b in zip(soll or b"", ist or b"") if a != b)
        abw.append("%dx%d->%dx%d (%d Byte)" % (w, h, tw, th, d))
check("alle bitgenau gleich", not abw, "; ".join(abw[:3]))
check("beide Rechenwege kamen dran", schmal > 10 and allgemein > 10,
      "schmal %d / allgemein %d" % (schmal, allgemein))

# ---------------------------------------------------------------------------
print("Test 2: Alphakanal bleibt beim Verkleinern 0")
# ---------------------------------------------------------------------------
pix = bytes([9, 9, 9, 255]) * (40 * 40)
erg = ART._verkleinern_flaechenmittel(pix, 40, 40, 10, 10)
check("Alpha ist ueberall 0", set(erg[3::4]) == {0},
      str(sorted(set(erg[3::4]))[:4]))
check("Farbkanaele stimmen", set(erg[0::4]) == {9})

# ---------------------------------------------------------------------------
print("Test 3: Vergroessern - 40 Zufallsbilder")
# ---------------------------------------------------------------------------
abw = []
for _ in range(40):
    w = random.randint(3, 50)
    h = random.randint(3, 50)
    sc = random.randint(2, 7)
    pix = bytes(random.getrandbits(8) for _ in range(w * h * 4))
    aw, ah, soll = ART._hochskalieren_py(pix, w, h, sc)
    bw_, bh_, ist = ART._hochskalieren(pix, w, h, sc)
    if (aw, ah) != (bw_, bh_) or bytes(soll) != bytes(ist):
        abw.append("%dx%d x%d" % (w, h, sc))
check("alle bitgenau gleich", not abw, "; ".join(abw[:3]))
check("Alpha wird hier MITkopiert",
      bytes(ART._hochskalieren(bytes([1, 2, 3, 77]) * 9, 3, 3, 2)[2])[3::4]
      == bytes([77]) * 36)

# ---------------------------------------------------------------------------
print("Test 4: unsinnige Masse werden abgefangen")
# ---------------------------------------------------------------------------
for (w, h, tw, th) in ((0, 10, 5, 5), (10, 0, 5, 5),
                       (10, 10, 0, 5), (10, 10, 5, 0)):
    pix = bytes(max(1, w * h * 4))
    check("(%d,%d)->(%d,%d) liefert None" % (w, h, tw, th),
          ART._verkleinern_flaechenmittel(pix, w, h, tw, th) is None)

# ---------------------------------------------------------------------------
print("Test 5: eine kaputte Bibliothek darf nichts umbringen")
# ---------------------------------------------------------------------------
echt = ART._LIB


class _Kaputt(object):
    def dragend_version(self):
        return 1

    def skalieren_flaechenmittel(self, *a):
        raise OSError("absichtlich kaputt")

    def hochskalieren(self, *a):
        raise OSError("absichtlich kaputt")

    def rechtecke_kopieren(self, *a):
        raise OSError("absichtlich kaputt")


ART._LIB = _Kaputt()
pix = bytes(random.getrandbits(8) for _ in range(30 * 30 * 4))
soll = ART._verkleinern_flaechenmittel_py(pix, 30, 30, 10, 10)
check("Verkleinern faellt auf Python zurueck",
      ART._verkleinern_flaechenmittel(pix, 30, 30, 10, 10) == soll)
sw, sh, soll2 = ART._hochskalieren_py(pix, 30, 30, 2)
check("Vergroessern faellt auf Python zurueck",
      bytes(ART._hochskalieren(pix, 30, 30, 2)[2]) == bytes(soll2))
ziel = bytearray(40 * 16)
check("Rechtecke melden ehrlich False statt halb zu kopieren",
      ART.rechtecke_kopieren(bytes(40 * 16), ziel, 40, 16, 40 * 16,
                             [(0, 0, 10, 16)]) is False)
ART._LIB = echt

# ---------------------------------------------------------------------------
print("Test 6: Rechtecke kopieren - 200 Zufallsfaelle, Byte fuer Byte")
# ---------------------------------------------------------------------------
# Die Python-Fassung aus frontend.py::_restore_spuren_py(), hier
# nachgebildet. Sie wird bewusst NICHT importiert: frontend.py zieht den
# halben Bildschirmapparat mit, und der Rumpf ist kurz genug, um ihn
# nebeneinander zu legen. Wer dort etwas aendert, muss es hier auch tun -
# dafuer steht in frontend.py ein Verweis auf diesen Test.


def kopieren_py(src, dst, stride, hoehe, grenze, spuren):
    quelle = memoryview(bytes(src))
    for x, y, w, h in spuren:
        need = w * 4
        if x < 0 or need <= 0:
            continue
        y0 = max(0, y)
        y1 = min(hoehe, y + h)
        if y1 <= y0:
            continue
        max_rows = (grenze - (x * 4) - need) // stride + 1
        if max_rows < y1:
            y1 = max(y0, max_rows)
        off = y0 * stride + x * 4
        for _ in range(y1 - y0):
            dst[off:off + need] = quelle[off:off + need]
            off += stride


abw = []
rand_getroffen = 0
for nr in range(200):
    breite = random.randint(8, 120)
    hoehe = random.randint(4, 40)
    stride = breite * 4 + (4 * random.randint(0, 3))     # auch mit Rand
    gross = stride * hoehe
    vorlage = bytes(random.getrandbits(8) for _ in range(gross))
    start = bytes(random.getrandbits(8) for _ in range(gross))
    # grenze absichtlich manchmal kuerzen - genau dann greift die
    # max_rows-Klemme, und genau dort weicht C ohne abrunden_div() ab.
    grenze = gross if nr % 3 else random.randint(0, gross)
    spuren = []
    for _ in range(random.randint(1, 8)):
        x = random.randint(-2, breite)                   # auch negativ
        w = random.randint(0, breite - max(0, x) + 2)    # auch 0 und zu breit
        y = random.randint(-3, hoehe)                    # auch negativ
        h = random.randint(0, hoehe + 2)
        if x * 4 + w * 4 > stride:                       # nie ueber die Zeile
            w = max(0, (stride - max(0, x) * 4) // 4)
        spuren.append((x, y, w, h))
        if x * 4 + w * 4 + (hoehe - 1) * stride > grenze:
            rand_getroffen += 1

    soll = bytearray(start)
    kopieren_py(vorlage, soll, stride, hoehe, grenze, spuren)

    ist = bytearray(start)
    if not ART.rechtecke_kopieren(vorlage, ist, stride, hoehe, grenze,
                                  spuren):
        abw.append("Nr %d: C hat abgelehnt" % nr)
        continue
    if bytes(ist) != bytes(soll):
        d = sum(1 for a, b in zip(soll, ist) if a != b)
        abw.append("Nr %d: %d Byte (%d Rechtecke, grenze %d/%d)"
                   % (nr, d, len(spuren), grenze, gross))

check("alle 200 Faelle bitgenau gleich", not abw, "; ".join(abw[:3]))
check("die max_rows-Klemme kam dran", rand_getroffen > 20,
      "%d mal" % rand_getroffen)

# Auch mit bytearray als Quelle (Vignette legt den Hintergrund so ab).
vorlage = bytearray(random.getrandbits(8) for _ in range(40 * 16))
soll = bytearray(40 * 16)
ist = bytearray(40 * 16)
spuren = [(0, 0, 10, 16), (2, 3, 5, 4)]
kopieren_py(vorlage, soll, 40, 16, 40 * 16, spuren)
check("Quelle darf ein bytearray sein",
      ART.rechtecke_kopieren(vorlage, ist, 40, 16, 40 * 16, spuren)
      and bytes(ist) == bytes(soll))

# Leere Liste: nichts tun, und das ehrlich melden.
ist = bytearray(40 * 16)
check("leere Liste wird abgelehnt (Aufrufer macht nichts)",
      ART.rechtecke_kopieren(vorlage, ist, 40, 16, 40 * 16, []) is False)
check("dabei blieb der Puffer unberuehrt", set(ist) == {0})

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  - " + x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
