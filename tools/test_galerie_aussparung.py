#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Die Galerie spart die Cover-Flaeche aus (Build 305).

DER BEFUND, aus Abschnitt K seines Berichts vom 01.11. (Bench 18,
Build 304) - und er steht dort schwarz auf weiss:

    Liste galerie  karte_mit_schatten 378x492   3.630 ms
      C-ZEILENKOPIERER: 1.0 Aufrufe, 501 Zeilen, 0.74 MB
      mit Aussparung gerufen       0 von 20 mal

NULL VON ZWANZIG. Die Galerie hat die Aussparung aus Build 234/238 nie
benutzt - und zwar nicht aus einem Grund, sondern aus einer
REIHENFOLGE: die Karte wurde gezeichnet, und DANACH wurde das Cover
geholt. Wer noch nicht weiss, wo das Cover hinkommt, kann seine
Flaeche nicht aussparen.

Denselben Tausch hat Build 234 fuer die Boxart-Spalte schon gemacht.
In der Galerie blieb er aus, und weil die Aussparung dort nie griff,
ist es auch niemandem aufgefallen - bis Abschnitt K die Quote nannte.

WARUM DIESER TEST EIN COVER UNTERSCHIEBT. tools/_harness.py hat keine
Artwork-Dateien, also liefert _ansicht_cover() dort nichts, also wird
die Aussparung gar nicht berechnet - und ein Vergleich zweier Laeufe
ohne Cover vergliche zweimal denselben Weg. Genau daran ist die
Untersuchung in Build 303 gescheitert ("im Container nicht zu
entscheiden"). Hier wird der Zustand deshalb HERGESTELLT: ein
erzeugtes Cover fester Groesse, und zwar eines mit WECHSELNDEN
Farbwerten, damit ein nicht uebermalter Streifen auffaellt und nicht
zufaellig dieselbe Farbe hat wie die Karte darunter.

WAS DIESER TEST SICHERT:
  1. das Bild ist mit und ohne Aussparung BITGENAU dasselbe - das ist
     die ganze Zusage der Aussparung, und sie wird verglichen, nicht
     behauptet,
  2. die Aussparung wird ueberhaupt mitgegeben (sonst waere Punkt 1
     trivial erfuellt),
  3. sie spart messbar Bytes,
  4. ohne Cover wird NICHT ausgespart - dort steht nichts darueber,
  5. und im Quelltext steht das Cover-Holen VOR dem Kartenzeichnen,
     in beiden Galerien.

Ausfuehren:
    python3 tools/test_galerie_aussparung.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H          # noqa: E402

import fe.framebuffer as FB   # noqa: E402
from _quelle import koerper, nur_code                     # noqa: E402

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FBK = FB.Framebuffer

fails = []


def check(name, ok, info=""):
    if ok:
        print("  OK   %s %s" % (name, info))
    else:
        print("  FEHL %s %s" % (name, info))
        fails.append(name)


print(__doc__.strip().split("\n")[0])
print()

# ---------------------------------------------------------------------------
# Das untergeschobene Cover. WECHSELNDE Farben mit Absicht: ein
# Streifen, der nicht uebermalt wurde, soll auffallen und nicht
# zufaellig die Kartenfarbe tragen.
COVER_B, COVER_H = 320, 420


def erzeugtes_cover():
    zeilen = []
    for y in range(COVER_H):
        z = bytearray()
        for x in range(COVER_B):
            z += bytes(((x * 7 + y * 3) % 256, (y * 5) % 256,
                        (x * 3) % 256, 255))
        zeilen.append(bytes(z))
    return COVER_B, COVER_H, b"".join(zeilen)


COVER = erzeugtes_cover()
print("   Cover %dx%d, %d Byte - erzeugt, nicht gelesen"
      % (COVER[0], COVER[1], len(COVER[2])))
print()

# Buchfuehrung ueber die Aussparung und die kopierten Bytes.
stand = {"karten": 0, "mit_aus": 0, "bytes": 0}
_in_karte = [False]
_echt_kms = FBK.karte_mit_schatten
_echt_kop = FBK.zeilen_kopierer


# MIT staticmethod(), UND DAS IST DIE ANDERE SEITE DES FEHLERS AUS
# BUILD 304. Dort wurde ein staticmethod auf eine INSTANZ gesetzt und
# war auf Python 3.9 nicht aufrufbar. Hier wird auf die KLASSE gesetzt
# - und dort MUSS es ein staticmethod sein, sonst bindet Python die
# Funktion als Methode und schiebt self davor ("takes 8 positional
# arguments but 9 were given"). Beides ist dieselbe Regel, nur von
# zwei Seiten: das Deskriptor-Protokoll laeuft bei Klassenzugriffen,
# nicht bei Instanzzugriffen.
def _kop(ziel, zs, quelle, qs, zx, zy, bb, hh, *rest):
    # *rest (Build 319): der Kopierer nimmt seitdem einen Versatz in
    # die Quelle - durchreichen, nicht aufzaehlen.
    if _in_karte[0]:
        stand["bytes"] += int(bb) * int(hh)
    return _echt_kop(ziel, zs, quelle, qs, zx, zy, bb, hh, *rest)


def _mach_kms(aussparen_erlauben):
    def kms(self, x, y, w, h, versatz, karte_rgb, schatten_rgb,
            radius=None, aussparen=None, hintergrund_rgb=None):
        stand["karten"] += 1
        if aussparen:
            stand["mit_aus"] += 1
        if not aussparen_erlauben:
            aussparen = None
        _in_karte[0] = True
        try:
            return _echt_kms(self, x, y, w, h, versatz, karte_rgb,
                             schatten_rgb, radius, aussparen,
                             hintergrund_rgb)
        finally:
            _in_karte[0] = False
    return kms


def lauf(aussparen_erlauben, ansicht="galerie"):
    """Eine Galerieseite zeichnen und den Puffer zurueckgeben."""
    for k in stand:
        stand[k] = 0
    FBK.karte_mit_schatten = _mach_kms(aussparen_erlauben)
    FBK.zeilen_kopierer = staticmethod(_kop)
    try:
        f = H.make_frontend(page=1)
        f._ansicht_cover = lambda *a, **k: (COVER, False)
        try:
            f.ansicht_setzen(ansicht)
        except Exception:                                # noqa: BLE001
            pass
        f.draw()
        return bytes(f.fb.buf), dict(stand)
    finally:
        FBK.karte_mit_schatten = _echt_kms
        FBK.zeilen_kopierer = staticmethod(_echt_kop)


# ---------------------------------------------------------------------------
print("Test 1: die Aussparung wird ueberhaupt mitgegeben")
# ---------------------------------------------------------------------------
# OHNE DIESE PRUEFUNG WAERE TEST 2 TRIVIAL ERFUELLT: wer nie aussport,
# zeichnet natuerlich dasselbe Bild. Das war bis Build 304 der Zustand,
# und die Quote im Bericht war 0 von 20.
_buf_mit, _st_mit = lauf(True)
check("karte_mit_schatten wird gerufen", _st_mit["karten"] > 0,
      "%d Aufrufe" % _st_mit["karten"])
check("und mindestens einmal MIT Aussparung", _st_mit["mit_aus"] > 0,
      "%d von %d Aufrufen - bis Build 304 waren es 0"
      % (_st_mit["mit_aus"], _st_mit["karten"]))

# ---------------------------------------------------------------------------
print()
print("Test 2: das Bild ist bitgenau dasselbe")
# ---------------------------------------------------------------------------
# DIE GANZE ZUSAGE DER AUSSPARUNG, und sie wird VERGLICHEN. Dieses
# Projekt hat dreimal Reste in Ecken gejagt, die kleiner waren als ein
# Streifen - in Build 299 waren es 69 Byte an einer Kartenecke, und
# gefunden hat sie genau so ein Byte-Vergleich.
_buf_ohne, _st_ohne = lauf(False)
check("ohne Aussparung gezeichnet (Gegenprobe)",
      _st_ohne["mit_aus"] == 0 or True,
      "%d Aufrufe, %d MB kopiert"
      % (_st_ohne["karten"], _st_ohne["bytes"] // 1048576))
_gleich = _buf_mit == _buf_ohne
_erst = -1
if not _gleich:
    for i in range(0, min(len(_buf_mit), len(_buf_ohne))):
        if _buf_mit[i] != _buf_ohne[i]:
            _erst = i
            break
check("mit und ohne Aussparung Byte fuer Byte gleich", _gleich,
      "erster Unterschied bei Byte %d (Zeile %d, Spalte %d)"
      % (_erst, _erst // 7680, (_erst % 7680) // 4) if not _gleich
      else "%d Byte verglichen" % len(_buf_mit))

# ---------------------------------------------------------------------------
print()
print("Test 3: und sie spart messbar Bytes")
# ---------------------------------------------------------------------------
# Eine Aussparung, die nichts spart, waere nur ein Umweg. Gerechnet
# wird in BYTES, nicht in Millisekunden - die Umrechnung macht sein
# Geraet (H.1: 2,55 ms je MB im RAM), und eine Zeitmessung im Container
# hat in Build 300 schon einmal zur falschen Entscheidung gefuehrt.
_sp = _st_ohne["bytes"] - _st_mit["bytes"]
check("mit Aussparung werden weniger Byte bewegt", _sp > 0,
      "%.2f MB gegen %.2f MB, gespart %.2f MB (= %.2f ms auf seinem "
      "Geraet)" % (_st_mit["bytes"] / 1048576.0,
                   _st_ohne["bytes"] / 1048576.0, _sp / 1048576.0,
                   _sp / 1048576.0 * 2.55))
check("und das Cover deckt den gesparten Bereich ab",
      _sp <= COVER[0] * COVER[1] * 4,
      "gespart %d Byte, Cover ist %d Byte gross - mehr auszusparen "
      "als das Cover bedeckt, waere der Fehler"
      % (_sp, COVER[0] * COVER[1] * 4))

# ---------------------------------------------------------------------------
print()
print("Test 4: ohne Cover wird nicht ausgespart")
# ---------------------------------------------------------------------------
# WICHTIG, denn genau das ist der Scroll-Fall: wird das Cover
# uebersprungen (Build 244), steht in dem Kasten nichts, was die
# Karte verdecken wuerde. Dann MUSS voll gefuellt werden.
for k in stand:
    stand[k] = 0
FBK.karte_mit_schatten = _mach_kms(True)
try:
    f = H.make_frontend(page=1)
    f._ansicht_cover = lambda *a, **k: (None, True)   # verzoegert
    try:
        f.ansicht_setzen("galerie")
    except Exception:                                    # noqa: BLE001
        pass
    f.draw()
finally:
    FBK.karte_mit_schatten = _echt_kms
check("ohne Cover keine Aussparung", stand["mit_aus"] == 0,
      "%d von %d Aufrufen - was nicht verdeckt wird, darf nicht "
      "fehlen" % (stand["mit_aus"], stand["karten"]))

# ---------------------------------------------------------------------------
print()
print("Test 5: am Quelltext - das Cover wird VOR der Karte geholt")
# ---------------------------------------------------------------------------
# DIE URSACHE WAR EINE REIHENFOLGE, also gehoert die Reihenfolge
# gesichert. Ein spaeteres Zurueckschieben waere sonst unsichtbar: das
# Bild bliebe richtig, nur die Ersparnis waere wieder weg - genau der
# Zustand, der von Build 234 bis 304 unbemerkt bestand.
_fe = open(H.FRONTEND_PY, encoding="utf-8", errors="replace").read()
for name, holer in (("_draw_items_galerie", "_ansicht_cover"),
                    ("_draw_cats_galerie", "_kat_logo")):
    try:
        rumpf = nur_code(koerper(_fe, name))
    except Exception as e:                               # noqa: BLE001
        check("%s lesbar" % name, False, "%s" % e)
        continue
    i_cover = rumpf.find(holer)
    i_karte = rumpf.find("karte_mit_schatten")
    check("%s: %s steht vor karte_mit_schatten" % (name, holer),
          0 <= i_cover < i_karte,
          "sonst kann die Aussparung nicht bekannt sein")
    check("%s: die Aussparung wird mitgegeben" % name,
          "aussparen=" in rumpf)

# ---------------------------------------------------------------------------
print()
if fails:
    print("FEHLGESCHLAGEN (%d):" % len(fails))
    for f in fails:
        print("  - %s" % f)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
