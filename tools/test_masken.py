#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MiSTers Lochmasken im Frontend (Build 226).

WUNSCH DES NUTZERS: "Masken vom Mister selbst benutzen, bitte mit
eigener Kategorie unter System, mit Auswahl und an und aus Schalter".

Dieselbe Haltung wie bei den Schriften aus Build 223: die Dateien liegen
in /media/fat/Shadow_Masks auf SEINER Karte, wir lesen sie nur. Dieses
Paket enthaelt keine einzige Maskendatei - Test 6 geht das ganze Paket
durch und meldet jede, die sich einschleicht.

DIE DREI STELLEN, AN DENEN ES KIPPEN KANN, und jede hat hier ihren Test:

  1. Das FORMAT. Eine Datei kann MEHRERE Muster fuer verschiedene
     Bildhoehen enthalten - 106 von 1207 Dateien der echten Sammlung tun
     das. Ein Leser, der nur den ersten Block kennt, wirft ausgerechnet
     die aufwendigsten Masken weg (Sony PVM, Commodore 1084).
  2. Der PUFFER MUSS SAUBER BLEIBEN. Die Maske liegt auf dem Weg zum
     Bildspeicher, nicht im Puffer - sonst legte der naechste
     Teilaufbau sie ein zweites Mal darueber, und das Bild wuerde mit
     jedem Scrollschritt dunkler.
  3. Die BILDWAECHTER vergleichen byteweise gegen gemerkte Proben. Auf
     dem Schirm steht mit Maske "Puffer MAL Maske" - merken sie sich
     den Puffer, melden sie in JEDEM Bild "das ist nicht mehr unser
     Bild" und kopieren alles neu.

Ausfuehren:
    python3 tools/test_masken.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H          # noqa: E402

import fe.masken as M         # noqa: E402
import fe.art as A            # noqa: E402
import fe.settings as S       # noqa: E402

fails = []
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def check(name, ok, info=""):
    if ok:
        print("  OK   %s %s" % (name, info))
    else:
        print("  FEHL %s %s" % (name, info))
        fails.append(name)


EINFACH = """####
# Name: Test
####

Resolution=0
v2
2,2
700,007
007,700
"""

MEHRTEILIG = """####
# Name: Zweiteilig
####
v2
1,1
777

Resolution=1080
v2
2,1
000,7ff
"""


# ---------------------------------------------------------------------------
print("Test 1: das Format")
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    p = os.path.join(tmp, "Test.txt")
    open(p, "w").write(EINFACH)
    m = M.maske_lesen(p)
    check("eine einfache Datei wird gelesen", m is not None)
    check("Masse stimmen", m[:2] == (2, 2), "%r" % (m[:2],))
    # "700" = Farbe 7 (alle Kanaele an), An-Staerke 0 -> 16/16,
    # Aus-Staerke 0. Alle drei Kanaele sind an, also ueberall 16.
    check("'700' ergibt dreimal 16 (unveraendert)",
          m[2][:3] == [16, 16, 16], "%r" % (m[2][:3],))
    # "007" = Farbe 0 (Grau, kein Kanal an), Aus-Staerke 7 -> 7/16.
    check("'007' ergibt dreimal 7 (abgedunkelt)",
          m[2][3:6] == [7, 7, 7], "%r" % (m[2][3:6],))
    check("der Name kommt aus dem Dateinamen", m[4] == "Test", m[4])

    # Die Kanal-Bits: 1=Blau, 2=Gruen, 4=Rot
    for zelle, erwartet in (("400", [16, 0, 0]), ("200", [0, 16, 0]),
                            ("100", [0, 0, 16]), ("40f", [16, 15, 15])):
        check("Zelle %s -> %r" % (zelle, erwartet),
              list(M._zelle(zelle)) == erwartet, "%r" % (M._zelle(zelle),))

    # ---------------------------------------------------------------
    print()
    print("Test 2: eine Datei mit MEHREREN Mustern")
    # ---------------------------------------------------------------
    p2 = os.path.join(tmp, "Zwei.txt")
    open(p2, "w").write(MEHRTEILIG)
    m0 = M.maske_lesen(p2)
    m1 = M.maske_lesen(p2, 1080)
    check("ohne Hoehe kommt der Block ohne Resolution",
          m0 is not None and m0[:2] == (1, 1), "%r" % (m0 and m0[:2],))
    check("mit 1080 der passende", m1 is not None and m1[:2] == (2, 1),
          "%r" % (m1 and m1[:2],))
    check("und mit einer unbekannten Hoehe wieder der allgemeine",
          M.maske_lesen(p2, 999)[:2] == (1, 1))

    # ---------------------------------------------------------------
    print()
    print("Test 3: kaputte Dateien aendern nichts")
    # ---------------------------------------------------------------
    for name, inhalt in (("leer", ""),
                         ("ohne Masse", "v2\n700,007\n"),
                         ("zu gross", "v2\n99,99\n700\n"),
                         ("falsche Zellenzahl", "v2\n2,2\n700\n007,700\n"),
                         ("Unfug", "das ist keine Maske\n")):
        p3 = os.path.join(tmp, "Kaputt.txt")
        open(p3, "w").write(inhalt)
        check("%-20s liefert None" % name, M.maske_lesen(p3) is None)
    check("eine Datei, die es nicht gibt",
          M.maske_lesen(os.path.join(tmp, "weg.txt")) is None)

    # Eine Maske, die nichts tut, wird als neutral erkannt
    p4 = os.path.join(tmp, "Neutral.txt")
    open(p4, "w").write("v2\n1,1\n700\n")
    check("eine wirkungslose Maske wird erkannt",
          M.ist_neutral(M.maske_lesen(p4)),
          "sonst rechnet C je Bildpunkt fuer nichts")

# ---------------------------------------------------------------------------
print()
print("Test 4: C rechnet, was die Tabelle sagt")
# ---------------------------------------------------------------------------
check("libdragend kann es", getattr(A, "_HAT_MASKE", False))
B, HO = 4, 2
src = bytearray()
for _y in range(HO):
    for _x in range(B):
        src += bytes((100, 100, 100, 255))        # BGRA, ueberall 100
dst = bytearray(len(src))
# 2x1-Muster: links alles aus (0), rechts das Hoechste, was das Format
# kann - 31/16, also 193,75 %. Mehr gibt es nicht: die An-Staerke geht
# von 0 bis f und steht fuer (16+f)/16.
maske = (2, 1, [0, 0, 0, 31, 31, 31])
ok = A.rechtecke_maske(bytes(src), dst, B * 4, HO, len(dst),
                       ((0, 0, B, HO),), maske)
check("der Aufruf geht durch", ok)
werte = [dst[i * 4] for i in range(B)]
check("abwechselnd 0 und 193", werte == [0, 193, 0, 193], "%r" % werte)
check("und die Deckkraft bleibt",
      all(dst[i * 4 + 3] == 255 for i in range(B)))

# Ueberlauf wird geklemmt, nicht umgebrochen
src2 = bytes((200, 200, 200, 255)) * 4
dst2 = bytearray(len(src2))
A.rechtecke_maske(src2, dst2, 4 * 4, 1, len(dst2), ((0, 0, 4, 1),),
                  (1, 1, [31, 31, 31]))
check("200 mal 1,94 wird zu 255, nicht zu 131",
      all(dst2[i * 4] == 255 for i in range(4)),
      "%r" % [dst2[i * 4] for i in range(4)])

# DIE PHASE HAENGT AN DER BILDSCHIRMPOSITION, nicht am Rechteck - sonst
# saesse das Muster in jedem Teilstueck woanders und das Bild zerfiele
# in sichtbare Kacheln.
src3 = bytes((100, 100, 100, 255)) * 4
ganz = bytearray(len(src3))
A.rechtecke_maske(src3, ganz, 4 * 4, 1, len(ganz), ((0, 0, 4, 1),), maske)
stueck = bytearray(len(src3))
A.rechtecke_maske(src3, stueck, 4 * 4, 1, len(stueck),
                  ((0, 0, 2, 1), (2, 0, 2, 1)), maske)
check("ein Faktor ausserhalb 0..31 wird ABGEWIESEN",
      A.rechtecke_maske(src3, bytearray(len(src3)), 4 * 4, 1,
                        len(src3), ((0, 0, 4, 1),),
                        (1, 1, [99, 16, 16])) is False,
      "das waere ein Lesefehler in fe/masken.py - lieber nichts tun")
check("in zwei Stuecken kommt dasselbe heraus wie am Stueck",
      bytes(ganz) == bytes(stueck),
      "sonst zerfaellt das Bild beim Teilaufbau in Kacheln")

# ---------------------------------------------------------------------------
print()
print("Test 5: der Puffer bleibt sauber, die Waechter lernen mit")
# ---------------------------------------------------------------------------
quelle = open(os.path.join(_REPO, "frontend", "fe", "framebuffer.py"),
              encoding="utf-8").read()
check("die Maske wird NICHT in den Puffer gerechnet",
      "self.buf, self.mm, self.stride" in quelle,
      "Quelle ist der Puffer, Ziel der Bildspeicher")
check("beide Waechter merken sich mit Maske den SCHIRM",
      quelle.count("self.mm if self.maske is not None") == 2,
      "sonst meldet der Waechter in jedem Bild fremden Inhalt")
check("auch das Vollbild geht ueber die Maske",
      "_maske_kopieren(((0, 0, self.width, self.height),))" in quelle)
check("und das Band ebenfalls",
      "_maske_kopieren(((0, y0, self.width, y1 - y0),))" in quelle)
check("faellt C aus, wird ohne Maske kopiert",
      "return False" in quelle.split("def _maske_kopieren")[1][:900],
      "lieber ein Bild ohne Effekt als gar keines")

# ---------------------------------------------------------------------------
print()
print("Test 6: Auswahl UND Schalter - und keine mitgelieferte Datei")
# ---------------------------------------------------------------------------
check("es gibt eine Auswahl", hasattr(S, "maske_lesen"))
check("und einen eigenen Schalter", hasattr(S, "toggle_maske"))
check("beide sind getrennt", S.MASKE_FILE != S.MASKE_AUS_FLAG,
      "wer kurz abschaltet, soll seine Auswahl behalten")
check("der Ordner ist MiSTers eigener",
      M.MASKEN_DIR == "/media/fat/Shadow_Masks")

gefunden = []
for wurzel, _dirs, dateien in os.walk(_REPO):
    if ".git" in wurzel or "node_modules" in wurzel:
        continue
    if os.path.basename(wurzel).lower() in ("shadow_masks", "filters"):
        gefunden.extend(os.path.join(wurzel, d) for d in dateien)
check("keine Maskendatei im Paket", not gefunden,
      "%s" % (gefunden[:2] if gefunden else ""))

quelle_f = open(H.FRONTEND_PY, encoding="utf-8", errors="replace").read()
check("es gibt eine eigene Seite dafuer",
      "def masken_bildschirm" in quelle_f,
      "ueber tausend Masken lassen sich nicht mit links/rechts durchblaettern")
check("sie wird beim Start angewandt",
      "maske_anwenden(self.fb, maske_pfad_oder_leer())" in quelle_f)
check("und ein Absturz dort schaltet sie ab",
      "self.fb.maske = None" in quelle_f.split("masken_bildschirm CRASH")[1]
      [:300] if "masken_bildschirm CRASH" in quelle_f else False)

print()
if fails:
    print("FEHLGESCHLAGEN (%d):" % len(fails))
    for f in fails:
        print("  - %s" % f)
    sys.exit(1)
print("Alles in Ordnung.")
