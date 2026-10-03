#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Die Zeilenkopie mit ZWEI Schrittweiten (Build 225).

WARUM ES SIE BRAUCHT. rechtecke_kopieren() aus Build 215 kann nur
Puffer mit DERSELBEN Schrittweite - Hintergrundkopie und Bildspeicher
sind gleich gerastert, dort stimmt das. Zwei Stellen im Zeichenweg sind
es nicht:

    blit()  - ein dekodiertes Cover liegt dicht gepackt (Breite * 4),
              das Ziel hat die Schrittweite des Bildschirms
    text()  - ein fertiger Textstreifen genauso

Beide hatten deshalb eine Python-Schleife ueber die Bildzeilen, und im
Bericht vom 02.10. stehen sie weit oben: blit mit 6 bis 12 ms je
Scrollschritt in jeder Ansicht.

DIE GRENZEN SIND DER EIGENTLICHE INHALT DIESES TESTS. Eine zu kurze
Quelle oder ein zu weit rechts liegendes Ziel darf NICHT ueber das Ende
schreiben - in C gibt es kein bytearray, das sich beschwert, sondern
einen Speicherfehler. Beide Grenzen werden mitgegeben, beide werden
geprueft, und im Zweifel werden WENIGER Zeilen kopiert, nie mehr.

Ausfuehren:
    python3 tools/test_zeilen_in_c.py
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H          # noqa: E402,F401

import fe.art as A            # noqa: E402

fails = []
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def check(name, ok, info=""):
    if ok:
        print("  OK   %s %s" % (name, info))
    else:
        print("  FEHL %s %s" % (name, info))
        fails.append(name)


def py_kopieren(dst, dst_stride, src, src_stride, x, y, breite, hoehe):
    """Der Python-Weg, Zeile fuer Zeile - das Vergleichsmass."""
    quelle = memoryview(src)
    ziel = memoryview(dst)
    for r in range(hoehe):
        s_off = r * src_stride
        d_off = (y + r) * dst_stride + x * 4
        if s_off + breite > len(src) or d_off + breite > len(dst):
            break
        ziel[d_off:d_off + breite] = quelle[s_off:s_off + breite]


# ---------------------------------------------------------------------------
print("Test 1: die Funktion ist da")
# ---------------------------------------------------------------------------
check("libdragend geladen", A._LIB is not None,
      "ohne sie prueft dieser Test nichts")
check("zeilen_kopieren ist angebunden", getattr(A, "_HAT_ZEILEN", False))
check("in einem EIGENEN try", "global _HAT_ZEILEN" in open(
    os.path.join(_REPO, "frontend", "fe", "art.py"),
    encoding="utf-8").read(),
    "eine 5er-Fassung darf die Bibliothek nicht mitnehmen")

# ---------------------------------------------------------------------------
print()
print("Test 2: C und Python schreiben BITGENAU dasselbe")
# ---------------------------------------------------------------------------
rng = random.Random(225)
DST_B, DST_H = 400, 300
FAELLE = [
    # (Quellbreite in Punkten, Quellhoehe, x, y)
    (100, 50, 0, 0),
    (100, 50, 10, 20),
    (1, 1, 399, 299),
    (400, 300, 0, 0),            # genau passend
    (50, 200, 350, 10),          # ragt rechts heraus
    (50, 200, 10, 250),          # ragt unten heraus
    (200, 1, 100, 150),          # eine einzige Zeile
    (1, 300, 0, 0),              # eine einzige Spalte
]
for _ in range(20):
    FAELLE.append((rng.randrange(1, 200), rng.randrange(1, 200),
                   rng.randrange(0, 380), rng.randrange(0, 280)))

abw = 0
for (qb, qh, x, y) in FAELLE:
    src = bytes(rng.randrange(256) for _ in range(qb * qh * 4))
    breite = qb * 4
    # Soviel, wie beide Seiten vertragen - der Aufrufer rechnet das
    # ohnehin aus (siehe blit()).
    hoehe = min(qh, DST_H - y)
    if hoehe <= 0 or x + qb > DST_B:
        hoehe = min(hoehe, 0) if hoehe <= 0 else hoehe
    a = bytearray(DST_B * DST_H * 4)
    b = bytearray(DST_B * DST_H * 4)
    breite_eff = min(breite, (DST_B - x) * 4)
    if breite_eff <= 0 or hoehe <= 0:
        continue
    ok_c = A.zeilen_kopieren(a, DST_B * 4, src, breite, x, y,
                             breite_eff, hoehe)
    py_kopieren(b, DST_B * 4, src, breite, x, y, breite_eff, hoehe)
    if not ok_c:
        abw += 1
        print("       C hat abgelehnt: %dx%d an (%d,%d)" % (qb, qh, x, y))
    elif bytes(a) != bytes(b):
        abw += 1
        n = sum(1 for p, q in zip(a, b) if p != q)
        print("       %dx%d an (%d,%d): %d Bytes anders" % (qb, qh, x, y, n))
check("alle %d Faelle bitgenau gleich" % len(FAELLE), abw == 0,
      "%d weichen ab" % abw)

# ---------------------------------------------------------------------------
print()
print("Test 3: DIE GRENZEN - es wird nie ueber das Ende geschrieben")
# ---------------------------------------------------------------------------
# Hier wird C ABSICHTLICH mehr angeboten, als hineinpasst. Erwartet
# wird: weniger Zeilen oder eine Ablehnung - aber niemals ein Byte
# hinter dem Puffer. Geprueft wird das mit einem Wachposten hinter dem
# Nutzbereich.
NUTZ = 100 * 50 * 4
WACHE = b"\xA5" * 4096
for name, (dst_stride, src_stride, x, y, breite, hoehe) in (
        ("Hoehe weit zu gross", (400, 400, 0, 0, 400, 100000)),
        ("Quelle zu kurz", (400, 400, 0, 0, 400, 5000)),
        ("x hinter dem Rand", (400, 400, 10000, 0, 400, 10)),
        ("y hinter dem Rand", (400, 400, 0, 10000, 400, 10)),
        ("Breite groesser als die Zeile", (400, 400, 0, 0, 40000, 10)),
        ("negative Hoehe", (400, 400, 0, 0, 400, -5)),
        ("negative Breite", (400, 400, 0, 0, -8, 10)),
        ("Schrittweite null", (0, 400, 0, 0, 400, 10)),
):
    puffer = bytearray(NUTZ) + bytearray(WACHE)
    # Nur der vordere Teil gilt als Ziel - die Wache dahinter darf sich
    # NICHT veraendern.
    ziel = memoryview(puffer)[:NUTZ]
    quelle = bytes(NUTZ)
    try:
        A.zeilen_kopieren(bytearray(puffer[:NUTZ]), dst_stride, quelle,
                          src_stride, x, y, breite, hoehe)
        gestuerzt = False
    except Exception as e:                               # noqa: BLE001
        gestuerzt = "%s: %s" % (type(e).__name__, e)
    check("%-30s stuerzt nicht ab" % name, gestuerzt is False,
          str(gestuerzt))
    check("%-30s laesst die Wache stehen" % name,
          bytes(puffer[NUTZ:]) == WACHE)
    del ziel

# ---------------------------------------------------------------------------
print()
print("Test 4: blit() benutzt sie - und nur, wenn es sich lohnt")
# ---------------------------------------------------------------------------
quelle_f = open(H.FRONTEND_PY, encoding="utf-8", errors="replace").read()
check("blit ruft die C-Fassung", "_c_zeilen_kopieren(fb.buf, fb.stride"
      in quelle_f)
check("und zwar hinter derselben Schwelle wie das Fuellen",
      "fb._nach_c_viele(ch, cw * ch)" in quelle_f,
      "viele ZEILEN oder viel FLAECHE - ein 32x32-Abzeichen keines von beidem")
check("der Python-Weg steht weiterhin darunter",
      "ziel[dst_off:dst_off + need] = quelle[src_off:src_off + need]"
      in quelle_f,
      "ohne libdragend muss es trotzdem laufen")

print()
if fails:
    print("FEHLGESCHLAGEN (%d):" % len(fails))
    for f in fails:
        print("  - %s" % f)
    sys.exit(1)
print("Alles in Ordnung.")
