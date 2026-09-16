#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Der schnelle Pfad der Kachelansichten bringt nur die geaenderten
Baender auf den Schirm (Build 133).

NUTZERWUNSCH: "ich haette gerne, dass das hin und her scrollen im neuen
Raster schneller laeuft."

BEIM NACHMESSEN GEFUNDEN. Der schnelle Pfad zeichnet seit Build 122 nur
ZWEI Kacheln neu - und lief danach trotzdem in ein volles fb.flip(),
also eine Kopie des KOMPLETTEN Bildspeichers. Auf 1080p sind das 8,3 MB
und auf dem Geraet des Nutzers rund 13 ms, gemessen in seinem eigenen
DRAGEND_PROFILE. Zwei Kacheln sparen und dann den ganzen Schirm
kopieren - das Sparen davor war damit zur Haelfte umsonst.

Die Liste macht es laengst richtig (flip_rows() in
_draw_navigate_items_impl()); den Kachelansichten hat es gefehlt.

Gemessen, wieviele Bildzeilen jetzt noch kopiert werden:

    links/rechts   253 + 132 = 385 von 1080   (36 %)
    hoch/runter    506 + 132 = 638 von 1080   (59 %)

WORAUF ES BEI DIESEM TEST ANKOMMT. Ein Vergleich des Zeichenpuffers
(fb.buf) wuerde hier NICHTS beweisen - der ist in beiden Faellen gleich,
egal wie viel davon anschliessend auf den Schirm wandert. Geprueft wird
deshalb fb.mm, also das, was wirklich angezeigt wird. Genau dort wuerde
ein zu knapp bemessenes Band als stehengebliebener Rest sichtbar - die
Sorte Fehler, die es in diesem Projekt schon viermal gab (Build 80, 122,
125, 128).

Ausfuehren:
    python3 tools/test_baender_flip.py
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

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


TMP = tempfile.mkdtemp(prefix="baender_")
BASIS = os.path.join(TMP, "art")
os.makedirs(os.path.join(BASIS, "SNES"))
TITEL = ["Spiel %02d" % i for i in range(60)]


def cover(pfad, w, h, nr):
    """Ein einfarbiges Cover je Eintrag - unterschiedliche Farben, damit
    eine stehengebliebene Kachel sofort auffaellt."""
    punkt = bytes(((nr * 37) % 256, (nr * 91) % 256, (nr * 53) % 256, 255))
    with open(pfad, "wb") as f:
        f.write(b"ART1" + struct.pack("<HH", w, h)
                + zlib.compress(punkt * (w * h), 1))


for i, t in enumerate(TITEL):
    cover(os.path.join(BASIS, "SNES", t + ".art"), 400, 533, i)

fm.ART_BASE = A.ART_BASE = BASIS
fm.ART_HD = A.ART_HD = BASIS
A._art_index_cache.clear()
A.THUMB_CACHE_DIR = os.path.join(TMP, "tc")
os.makedirs(A.THUMB_CACHE_DIR)
fm.SYSART_BASE = A.SYSART_BASE = os.path.join(_REPO, "frontend", "sysart")


def spieleliste(breite, hoehe):
    H.set_screen(breite, hoehe)
    f = H.make_frontend(page=1)
    fm.ART.auslagern = None
    f.lader.beenden()
    _n, node, _k = f.cats[f.cat_i]
    node["items"] = [(t, "game", ("/f/%d.sfc" % i, ".sfc", "SNES", None, None))
                     for i, t in enumerate(TITEL)]
    node.pop("_display_items_cache", None)
    return f


def vergleich(f, setzen, ziele, label):
    """Schneller Pfad gegen vollen Aufbau - am SCHIRM, nicht am Puffer."""
    for ziel in ziele:
        setzen(f, 0)
        f._force_full_redraw = True
        f.draw()
        setzen(f, ziel)
        f.draw()                       # schneller Pfad -> nur Baender
        schnell = bytes(f.fb.mm)
        f._force_full_redraw = True
        f.draw()                       # voller Aufbau -> alles
        voll = bytes(f.fb.mm)
        d = sum(1 for a, b in zip(schnell, voll) if a != b)
        check("%s Schritt auf %-3d" % (label, ziel), d == 0,
              "" if d == 0 else "%d abweichende Bytes auf dem Schirm" % d)


# ---------------------------------------------------------------------
print("Test 1: Raster der Spieleliste - was ankommt, ist identisch")
f = spieleliste(1920, 1080)
f.ansicht_setzen("raster")
for i in range(25):
    f.item_i = i
    f.draw()


def _setz_item(f_, i):
    f_.item_i = i


# Bewusst gemischt: ein Nachbar (gleiche Reihe), ein Reihenwechsel, und
# einer, der die Seite wechselt (dort greift der schnelle Pfad gar
# nicht - auch das muss stimmen).
vergleich(f, _setz_item, (1, 2, 6, 7, 8, 14, 20, 21, 25), "HDMI")

print()
print("Test 2: dasselbe auf CRT")
f2 = spieleliste(320, 240)
f2.ansicht_setzen("raster")
for i in range(20):
    f2.item_i = i
    f2.draw()
vergleich(f2, _setz_item, (1, 2, 5, 6, 15), "CRT ")

# ---------------------------------------------------------------------
print()
print("Test 3: Raster der Hauptseite")
H.set_screen(1920, 1080)
f3 = H.make_frontend(page=0)
fm.ART.auslagern = None
f3.lader.beenden()
sp = [("S %d" % i, "game", ("/f/%d.sfc" % i, ".sfc", "SNES", None, None))
      for i in range(8)]
KAT = [("Favoriten", "FAVORITES"), ("Arcade", "ARCADE"), ("NES", "NES"),
       ("SNES", "SNES"), ("Game Boy", "GAMEBOY"), ("GBC", "GBC"),
       ("GBA", "GBA"), ("N64", "N64"), ("Mega Drive", "Genesis"),
       ("SMS", "SMS"), ("PSX", "PSX"), ("Neo Geo", "NEOGEO")]
f3.cats = [(n, {"folders": {}, "items": list(sp)}, k) for n, k in KAT]
f3.ansicht_haupt_setzen("raster")
for i in range(len(f3.cats)):
    f3.cat_i = i
    f3.draw()


def _setz_cat(f_, i):
    f_.cat_i = i


vergleich(f3, _setz_cat, (1, 2, 3, 5, 8, 10), "Haupt")

# ---------------------------------------------------------------------
print()
print("Test 4: es wird wirklich weniger kopiert")
# Ohne diese Pruefung koennte _baender_flippen() heimlich den ganzen
# Schirm nehmen und Test 1-3 waeren trotzdem gruen.
f4 = spieleliste(1920, 1080)
f4.ansicht_setzen("raster")
for i in range(25):
    f4.item_i = i
    f4.draw()
gezaehlt = []
echt = f4.fb.flip_rows


def _haken(y, h, skip_vsync=False):
    gezaehlt.append(h)
    return echt(y, h, skip_vsync)


f4.fb.flip_rows = _haken
f4.item_i = 0
f4._force_full_redraw = True
f4.draw()

gezaehlt[:] = []
f4.item_i = 1
f4.draw()
check("links/rechts kopiert deutlich weniger als den Schirm",
      gezaehlt and sum(gezaehlt) < 1080 // 2,
      "%s = %d von 1080 Zeilen" % ("+".join(map(str, gezaehlt)),
                                   sum(gezaehlt)))

gezaehlt[:] = []
f4.item_i = 8
f4.draw()
check("hoch/runter ebenfalls weniger",
      gezaehlt and sum(gezaehlt) < 1080,
      "%s = %d von 1080 Zeilen" % ("+".join(map(str, gezaehlt)),
                                   sum(gezaehlt)))

# Beim Seitenwechsel MUSS es der ganze Schirm sein - dort aendert sich
# alles. Ein Band waere dort ein Fehler, kein Gewinn.
gezaehlt[:] = []
f4.item_i = 21
f4.draw()
check("beim Seitenwechsel bleibt es beim vollen Bild",
      not gezaehlt, repr(gezaehlt))

# Und der Suchbalken liegt OBEN - da darf kein Band greifen.
f4.item_i = 0
f4._force_full_redraw = True
f4.draw()
f4._search_mode = True
gezaehlt[:] = []
f4.item_i = 1
f4.draw()
check("bei aktiver Suche ebenfalls volles Bild", not gezaehlt,
      repr(gezaehlt))
f4._search_mode = False

# ---------------------------------------------------------------------
print()
print("Test 5: das Vsync-Warten faellt je BAND, nicht pauschal")
# KORRIGIERT (Build 134). In Build 133 berechneten die Aufrufer das
# Ueberspringen mit _vsync_ueberspringen(None) - und None heisst dort
# ausdruecklich "Vollbild", wofuer IMMER gewartet wird. Die neuen,
# kleinen Baender haben dadurch trotzdem jedes Mal auf den Bildwechsel
# gewartet, also genau die 8-17 ms, die Build 93 sparen wollte.
#
# Aufgefallen an einer Nutzerbeobachtung: "wenn ich schnell
# hintereinander nach links oder rechts druecke, geht es schneller".
# Genau so sieht es aus, wenn eine Kopie auf den Bildwechsel wartet.
import fe.settings as S                                  # noqa: E402

f5 = spieleliste(1920, 1080)
f5.ansicht_setzen("raster")
for i in range(25):
    f5.item_i = i
    f5.draw()
notiert = []
_echt5 = f5.fb.flip_rows


def _haken5(y, h, skip_vsync=False):
    notiert.append((h, skip_vsync))
    return _echt5(y, h, skip_vsync)


f5.fb.flip_rows = _haken5

if not S.fast_scroll_enabled():
    print("       ('Schnelles Scrollen' ist aus - uebersprungen)")
else:
    # Schnelle Folge: die letzte Eingabe liegt Millisekunden zurueck.
    f5.item_i = 0
    f5._force_full_redraw = True
    f5.draw()
    f5._last_input_time = fm.time.monotonic() - 0.05
    notiert[:] = []
    f5.item_i = 1
    f5.draw()
    check("bei schneller Folge wird nicht mehr gewartet",
          notiert and all(skip for _h, skip in notiert),
          repr(notiert))

    # Einzelner Druck: die letzte Eingabe liegt lange zurueck. Hier MUSS
    # gewartet werden - ein einzelner Schritt ist kein Scrollen, und der
    # Bildriss waere ohne Not sichtbar.
    f5.item_i = 0
    f5._force_full_redraw = True
    f5.draw()
    f5._last_input_time = fm.time.monotonic() - 10.0
    notiert[:] = []
    f5.item_i = 1
    f5.draw()
    check("bei einem einzelnen Druck wird weiterhin gewartet",
          notiert and not any(skip for _h, skip in notiert),
          repr(notiert))

# Und die Grenze selbst: ein Band ueber einem Viertel der Bildhoehe
# darf NIE ueberspringen, egal wie schnell gescrollt wird - dort waere
# der Riss sichtbar (siehe VSYNC_SKIP_MAX_ANTEIL).
check("ein zu grosses Band ueberspringt nie",
      f5._vsync_ueberspringen(1080) is False
      and f5._vsync_ueberspringen(None) is False)

shutil.rmtree(TMP, ignore_errors=True)

print()
if fails:
    print("FEHLGESCHLAGEN (%d):" % len(fails))
    for f_ in fails:
        print("  -", f_)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
