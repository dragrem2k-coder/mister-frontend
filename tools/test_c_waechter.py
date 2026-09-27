#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bildwaechter in ganzen Zeilen und Fremdzaehler in C (Build 209).

WORUM ES GEHT

Der Nutzer hat ueber mehrere Builds dasselbe gemeldet: "login prompt
ploppt immer noch kurz zwischendurch auf". Der Bildwaechter aus Build
198 hat das nie gefunden, und der Grund ist keine Fehlfunktion, sondern
Wahrscheinlichkeit: er sah ACHT EINZELNE BILDPUNKTE an. Dass einer
davon genau auf einem Buchstaben des Login-Grusses liegt, ist
praktisch ausgeschlossen. Ein ganz weggeschaltetes Bild fand er sofort
(dort waren 15 von 15 Proben fremd) - einen hineingeschriebenen Text
nie.

Ganze Zeilen finden beides. In Python waren sie zu teuer, in C ist es
ein memcmp. Dasselbe fuer _fremdausgabe_zaehlen(), das seit Build 208
auch auf dem Aktions-Pfad laeuft: 48 Zeilen mal 512 Spalten sind 24576
Vergleiche in Python, mitten im Scrollen.

WAS DIESER TEST ABSICHERT

  - dass C und Python BITGENAU dasselbe zaehlen und dasselbe finden
    (beide Fassungen bleiben stehen, der Rueckfall muss stimmen),
  - dass der Zeilen-Waechter den Text findet, den acht Punkte
    verpassen - das ist der ganze Zweck des Umbaus,
  - dass er weiterhin KEINE Fehlalarme gibt, wenn der Puffer dem
    Schirm vorauslaeuft (das ist der Trick von Build 198 und darf
    nicht verloren gehen),
  - dass eine Probe, in die noch nie geschrieben wurde, uebersprungen
    wird,
  - dass ohne libdragend alles weiterhin funktioniert.
"""
import os
import random
import sys

_HIER = os.path.dirname(os.path.abspath(__file__))
_WURZEL = os.path.dirname(_HIER)
sys.path.insert(0, os.path.join(_WURZEL, "frontend"))

if not os.environ.get("DRAGEND_LIB"):
    _x86 = os.path.join(_WURZEL, "frontend", "c", "libdragend_x86.so")
    if os.path.exists(_x86):
        os.environ["DRAGEND_LIB"] = _x86

import fe.art as ART                                       # noqa: E402
from fe.framebuffer import Framebuffer                     # noqa: E402

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

print("libdragend Version %d" % ART._LIB.dragend_version())
check("die Fassung ist mindestens 4 (Build 209)",
      ART._LIB.dragend_version() >= 4)


class Attrappe(Framebuffer):
    """Ein Framebuffer ohne Geraet - mm und buf sind schlichte
    bytearrays, genau wie im Test-Harness."""

    def __init__(self, w=320, h=120):
        self.width, self.height, self.bpp = w, h, 32
        self.stride = w * 4
        self.size = self.stride * h
        self.fd = -1
        self.mm = bytearray(self.size)
        self.buf = bytearray(self.size)
        self._rowcache = {}
        self._waechter_einrichten()


def zaehlen_py(fb, hoehe, breite4):
    """Die Referenz - dieselbe Rechnung wie
    frontend.py::_fremdausgabe_zaehlen_py()."""
    treffer = 0
    for y in range(hoehe):
        off = y * fb.stride
        schirm = fb.mm[off:off + breite4]
        gemalt = fb.buf[off:off + breite4]
        if schirm == gemalt:
            continue
        treffer += sum(1 for a, b in zip(schirm[1::4], gemalt[1::4])
                       if a > 0x40 >= b)
    return treffer


# ---------------------------------------------------------------------------
print()
print("Test 1: fremd_zaehlen - C gegen Python, 60 Zufallsfaelle")
# ---------------------------------------------------------------------------
random.seed(20926)
gleich = 0
ungleich = []
nicht_null = 0
for fall in range(60):
    fb = Attrappe(64, 40)
    n = fb.size
    fb.mm[:] = bytes(random.randrange(256) for _ in range(n))
    fb.buf[:] = bytes(random.randrange(256) for _ in range(n))
    # In jedem dritten Fall die beiden streckenweise gleich machen -
    # dann greift die memcmp-Abkuerzung in C, und die muss dasselbe
    # Ergebnis liefern wie der Weg ohne sie.
    if fall % 3 == 0:
        fb.mm[: n // 2] = fb.buf[: n // 2]
    hoehe = random.randrange(1, fb.height + 1)
    breite4 = random.randrange(1, fb.width + 1) * 4
    c = ART.fremd_zaehlen(fb.mm, fb.buf, fb.stride, hoehe, breite4)
    p = zaehlen_py(fb, hoehe, breite4)
    if c == p:
        gleich += 1
    else:
        ungleich.append((fall, c, p))
    if p:
        nicht_null += 1
check("alle 60 Faelle gleich", not ungleich, repr(ungleich[:3]))
check("und es wurde wirklich etwas gezaehlt (nicht nur Nullen)",
      nicht_null >= 40, "%d von 60 mit Treffern" % nicht_null)

# Die Richtung ist der Kern: hell im Puffer, dunkel auf dem Schirm darf
# NICHT zaehlen - sonst waere jeder halbe Bildaufbau ein Fund
# (Build 151).
fb = Attrappe(64, 8)
for i in range(1, fb.size, 4):
    fb.buf[i] = 0xFF               # Puffer hell
    fb.mm[i] = 0x00                # Schirm dunkel
check("hell im Puffer, dunkel auf dem Schirm zaehlt NICHT",
      ART.fremd_zaehlen(fb.mm, fb.buf, fb.stride, 8, 64 * 4) == 0)
for i in range(1, fb.size, 4):
    fb.buf[i] = 0x00
    fb.mm[i] = 0xFF                # jetzt umgekehrt
check("umgekehrt zaehlt es sehr wohl",
      ART.fremd_zaehlen(fb.mm, fb.buf, fb.stride, 8, 64 * 4) == 8 * 64)

# ---------------------------------------------------------------------------
print()
print("Test 2: die Proben liegen eng genug fuer eine Konsolen-Textzeile")
# ---------------------------------------------------------------------------
fb = Attrappe(1920, 1080)
check("der Waechter ist an", fb._waechter_an)
zeilen = sorted(off // fb.stride for off in fb._waechter_offsets)
oben = [z for z in zeilen if z < Framebuffer.WAECHTER_OBEN_BIS]
print("    %d Proben, davon %d in den obersten %d Zeilen"
      % (len(zeilen), len(oben), Framebuffer.WAECHTER_OBEN_BIS))
luecken = [b - a for a, b in zip(oben, oben[1:])]
check("oben keine Luecke groesser als 16 Bildpunkte (eine Textzeile)",
      luecken and max(luecken) <= 16, "groesste Luecke %s" % (luecken or "-"))
check("eine Probe ist ganze Zeile breit",
      fb._waechter_zeile_bytes == 1920 * 4, str(fb._waechter_zeile_bytes))
check("und es gibt auch Proben tief im Bild (weggeschaltetes Bild)",
      max(zeilen) > fb.height // 2, str(max(zeilen)))

# ---------------------------------------------------------------------------
print()
print("Test 3: der Text, den acht Punkte verpassen")
# ---------------------------------------------------------------------------
fb = Attrappe(1920, 200)
# Unser Bild: dunkel. Geschrieben und gemerkt.
fb.buf[:] = b"\x10" * fb.size
fb.mm[:] = fb.buf
fb._waechter_merken()
check("frisch gemerkt findet der Waechter nichts",
      not fb._waechter_pruefen())

# Jetzt schreibt der Login-Prozess: drei Textzeilen, je 16 Bildpunkte
# hoch, ab Zeile 0 - aber nur 30 Zeichen breit, also die linken 240
# Bildpunkte. Genau so sieht "Welcome to MiSTer ... login:" aus.
for y in range(0, 48):
    if (y % 16) < 12:                       # Buchstabenkoerper
        off = y * fb.stride
        for x in range(0, 240 * 4, 8):      # jeder zweite Punkt hell
            fb.mm[off + x:off + x + 4] = b"\xff\xff\xff\xff"
check("DEN findet der Zeilen-Waechter", fb._waechter_pruefen())

# GEGENPROBE, und die musste ich zweimal schreiben. Beim ersten Versuch
# stand hier EIN synthetischer Text und die Behauptung "acht Punkte
# haetten ihn nicht gefunden" - der Test ist fehlgeschlagen, weil einer
# der acht Punkte zufaellig genau darauf lag. Und das war richtig so:
# bei EINEM Fall ist das ein Muenzwurf und kein Beweis. Die alten
# Probenzeilen 16 und 40 liegen ja absichtlich dort, wo der Prompt
# steht - sie treffen ihn nur in der Breite fast nie.
#
# Also gemessen statt behauptet: 200 Prompts an zufaelliger Stelle,
# jeder mit duennen Buchstabenstrichen wie echter Text, und gezaehlt,
# wie oft jede der beiden Fassungen ihn findet.
random.seed(4711)
alt_treffer = 0
neu_treffer = 0
for _ in range(200):
    pr = Attrappe(1920, 200)
    pr.buf[:] = b"\x10" * pr.size
    pr.mm[:] = pr.buf
    pr._waechter_merken()
    spalte = random.randrange(0, 40)          # Prompt beginnt links
    zeile0 = random.randrange(0, 3) * 16
    for ty in range(3):                       # drei Textzeilen
        for dy in range(2, 13):               # Buchstabenkoerper
            yy = zeile0 + ty * 16 + dy
            if yy >= pr.height:
                continue
            off = yy * pr.stride
            # 28 Zeichen, je 8 Punkte breit, davon 2 Punkte Strich -
            # so duenn ist echter Text wirklich.
            for zeichen in range(28):
                x = (spalte + zeichen * 8) * 4
                pr.mm[off + x:off + x + 8] = b"\xff" * 8
    if pr._waechter_pruefen():
        neu_treffer += 1
    # Die acht Punkte von Build 198, genau wie dort gerechnet.
    punkte = [min(pr.height - 1, 16), min(pr.height - 1, 40)]
    for i in range(6):
        punkte.append((pr.height * (2 * i + 1)) // 12)
    for k, z in enumerate(punkte):
        x = (pr.width * (2 * k + 1)) // (2 * len(punkte))
        off = z * pr.stride + x * 4
        if bytes(pr.mm[off:off + 4]) != b"\x10\x10\x10\x10":
            alt_treffer += 1
            break
print("    von 200 Prompts gefunden: Zeilen-Waechter %d, acht Punkte %d"
      % (neu_treffer, alt_treffer))
check("der Zeilen-Waechter findet jeden", neu_treffer == 200,
      "%d von 200" % neu_treffer)
check("acht Punkte finden fast keinen - das ist der Grund fuer den Umbau",
      alt_treffer <= 20, "%d von 200" % alt_treffer)

# Und die nackte Zahl dahinter, ohne Zufall: wie viel Bild die beiden
# Fassungen ueberhaupt ansehen.
alt_bytes = 8 * 4
neu_bytes = len(fb._waechter_offsets) * fb._waechter_zeile_bytes
print("    angesehene Bytes: vorher %d, jetzt %d (%dmal so viel)"
      % (alt_bytes, neu_bytes, neu_bytes // alt_bytes))
check("der Waechter sieht jetzt um Groessenordnungen mehr Bild an",
      neu_bytes > 1000 * alt_bytes)

# ---------------------------------------------------------------------------
print()
print("Test 4: kein Fehlalarm, wenn der Puffer vorauslaeuft")
# ---------------------------------------------------------------------------
fb = Attrappe(640, 120)
fb.buf[:] = b"\x20" * fb.size
fb.mm[:] = fb.buf
fb._waechter_merken()
# Jetzt malen wir ins buf, ohne zu flippen - genau der Normalfall
# zwischen zwei Teil-Flips.
fb.buf[:] = b"\xaa" * fb.size
check("der Waechter schlaegt NICHT an (er vergleicht gegen das zuletzt "
      "Geschriebene)", not fb._waechter_pruefen())

# Erst wenn wir das gemerkte Band auffrischen und danach jemand in mm
# schreibt, ist es ein Fund.
fb.mm[:] = fb.buf
fb._waechter_merken()
check("nach dem Auffrischen weiterhin still", not fb._waechter_pruefen())
fb.mm[7 * fb.stride + 100:7 * fb.stride + 104] = b"\x00\x00\x00\x00"
check("ein fremdes Byte in einer Probenzeile wird gefunden",
      fb._waechter_pruefen())

# ---------------------------------------------------------------------------
print()
print("Test 5: eine Probe ohne je geschriebenen Inhalt wird uebersprungen")
# ---------------------------------------------------------------------------
fb = Attrappe(640, 120)
fb.buf[:] = b"\x30" * fb.size
fb.mm[:] = b"\x99" * fb.size          # Schirm voellig anders
# NICHTS gemerkt - alle Gueltig-Marken stehen auf 0.
check("ohne jedes Merken kein Fund", not fb._waechter_pruefen())
# Nur das oberste Band merken, dann unten etwas veraendern.
#
# WICHTIG und beim ersten Schreiben falsch gemacht: veraendert werden
# muss eine ZEILE, AUF DER EINE PROBE LIEGT. Ich hatte hier Zeile 2
# genommen - dort liegt keine (die Proben liegen oben alle 8
# Bildzeilen), der Test schlug fehl und hatte recht damit. Deshalb
# werden die Zeilen jetzt aus _waechter_offsets geholt statt geraten.
probenzeilen = sorted(off // fb.stride for off in fb._waechter_offsets)
fb.mm[:] = fb.buf
fb._waechter_merken(0, 20)
gemerkt = [z for z in probenzeilen if z < 20]
nicht_gemerkt = [z for z in probenzeilen if z >= 20]
check("es gibt Proben in beiden Bereichen", gemerkt and nicht_gemerkt,
      "%r / %r" % (gemerkt[:3], nicht_gemerkt[:3]))
z = nicht_gemerkt[-1]
fb.mm[z * fb.stride:z * fb.stride + 4] = b"\x00\x00\x00\x00"
check("eine Aenderung in einer NICHT gemerkten Probenzeile bleibt still",
      not fb._waechter_pruefen(), "Zeile %d" % z)
z = gemerkt[-1]
fb.mm[z * fb.stride:z * fb.stride + 4] = b"\x00\x00\x00\x00"
check("in einer gemerkten Probenzeile nicht", fb._waechter_pruefen(),
      "Zeile %d" % z)

# ---------------------------------------------------------------------------
print()
print("Test 6: der Waechter braucht KEIN C - und das ist gemessen")
# ---------------------------------------------------------------------------
# Ich hatte den Waechter zuerst nach C geholt, in der Annahme, 20 Proben
# mal 7680 Byte seien in Python zu teuer. Die Messung hat das widerlegt
# (Python war sogar minimal schneller), und der C-Teil ist deshalb
# wieder rausgeflogen - siehe den Kommentarblock in c/dragend.c.
#
# Dieser Test haelt fest, WARUM: ein Schnittvergleich auf einem
# bytearray ist ein memcmp, der Python-Rahmen faellt je PROBE an, nicht
# je Byte. Damit das nicht irgendwann jemand wieder "optimiert", steht
# hier die Zahl.
import time                                                # noqa: E402

fb = Attrappe(1920, 1080)
fb.buf[:] = b"\x30" * fb.size
fb.mm[:] = fb.buf
fb._waechter_merken()
t0 = time.monotonic()
for _ in range(200):
    fb._waechter_pruefen()
dt = (time.monotonic() - t0) / 200 * 1000
gesehen = len(fb._waechter_offsets) * fb._waechter_zeile_bytes
print("    %d Proben, %d kB je Blick, %.4f ms" % (
    len(fb._waechter_offsets), gesehen // 1024, dt))
check("ein Blick kostet deutlich unter einer Millisekunde", dt < 1.0,
      "%.4f ms" % dt)
check("es gibt nur noch EINE Fassung (kein _waechter_pruefen_py mehr)",
      not hasattr(Framebuffer, "_waechter_pruefen_py"))
check("und keine C-Funktion dafuer",
      not hasattr(ART, "waechter_zeilen_pruefen"))

# ---------------------------------------------------------------------------
print()
print("Test 7: ohne libdragend laeuft alles weiter")
# ---------------------------------------------------------------------------
_echt = ART._LIB
try:
    ART._LIB = None
    fb = Attrappe(320, 80)
    fb.buf[:] = b"\x40" * fb.size
    fb.mm[:] = fb.buf
    fb._waechter_merken()
    check("der Waechter laeuft weiter (er braucht C ohnehin nicht)",
          not fb._waechter_pruefen())
    z = sorted(off // fb.stride for off in fb._waechter_offsets)[1]
    fb.mm[z * fb.stride:z * fb.stride + 4] = b"\x00\x00\x00\x00"
    check("und findet weiterhin", fb._waechter_pruefen(), "Zeile %d" % z)
    check("fremd_zaehlen meldet ehrlich None",
          ART.fremd_zaehlen(fb.mm, fb.buf, fb.stride, 8, 320 * 4) is None)
finally:
    ART._LIB = _echt

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
