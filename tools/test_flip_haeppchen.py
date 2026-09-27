#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Der haeppchenweise Flip (Build 181) - ein Messgegenstand.

WORUM ES GEHT

Bei 1920x1080 blitzt achtmal je Minute MiSTers eigenes Menuebild durch
das Frontend, je ein bis zwei Bilder lang, jedes Mal dicht an einem
Scrollschritt. Bei halber Aufloesung nicht.

Nachgemessen (frontend/zuck_probe.py, zwei Abschnitte): MiSTer wacht
beim Scrollen NICHT oefter auf als im Leerlauf - 39 gegen 52
Aufwachmomente je Minute, bei 13 bzw. 26 Ereignissen also kein
Unterschied. Er zeichnet nicht dazwischen. UNSERE Ebene faellt kurz
aus.

DIE VERMUTUNG: ARM und FPGA teilen sich denselben Speicher. Ein
Vollbild sind 7,9 MB, in einem Zug geschrieben - gemessen 12,6 ms,
fast eine ganze Bildperiode. Bekommt der Scaler in dieser Zeit seine
Zeilen nicht, faellt unsere Ebene weg.

Geprueft wird sie, indem dasselbe Bild in Haeppchen geschrieben wird.
Verschwindet das Zucken, stimmt die Vermutung - und der Fix ist gleich
da. Verschwindet es nicht, ist es nicht der Speicherbus.

WAS DIESER TEST ABSICHERT

Vor allem eines: dass dabei GENAU DASSELBE BILD herauskommt. Ein
Umbau am Flip ist der denkbar heikelste Ort - hier geht jedes
einzelne Bild durch. Ein Fehler um ein paar Bytes waere ein
verschobenes Bild, und das sieht aus wie ein Grafikproblem und ist
keines (siehe die Warnung bei _map_ueber_dev_mem()).

Dazu: dass er STANDARDMAESSIG AUS ist. Niemand soll einen
Messgegenstand ungefragt bekommen.

Ausfuehren:
    python3 tools/test_flip_haeppchen.py
"""
import io
import os
import sys

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
sys.path.insert(0, _HIER)

import _harness as H                                     # noqa: E402

fm = H.fm
FB = fm.Framebuffer

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


def bild(n):
    """Ein Muster, in dem jede Position eindeutig ist - ein Versatz um
    auch nur ein Byte faellt damit sofort auf."""
    return bytearray((i * 7 + (i >> 11)) & 255 for i in range(n))


class Attrappe(object):
    """Nur so viel Framebuffer, wie _flip_haeppchenweise() anfasst."""

    def __init__(self, groesse, stuecke, pause_us=0):
        self.size = groesse
        self.mm = bytearray(groesse)
        self.buf = bild(groesse)
        self.haeppchen = stuecke
        self.haeppchen_pause = pause_us / 1000000.0
        self._mv_mm = memoryview(self.mm)
        self._mv_buf = memoryview(self.buf)
        self.schreibvorgaenge = 0

    flip_gen = 0

    def lauf(self):
        FB._flip_haeppchenweise(self)
        return bytes(self.mm)


# ---------------------------------------------------------------------------
print("Test 1: DASSELBE BILD - Haeppchen gegen einen Zug")
# ---------------------------------------------------------------------------
# Durchgespielt mit Groessen, die NICHT glatt aufgehen: krumme Reste
# sind genau die Stelle, an der so eine Schleife danebenliegt.
GROESSEN = (1920 * 1080 * 4, 320 * 240 * 4, 4, 7, 1000, 1024, 65537,
            1920 * 1080 * 4 - 1)
STUECKE = (2, 3, 7, 16, 64, 255, 1000)
schief = []
n = 0
for g in GROESSEN:
    erwartet = bytes(bild(g))
    for st in STUECKE:
        a = Attrappe(g, st)
        n += 1
        if a.lauf() != erwartet:
            schief.append("%d Bytes in %d Stuecken" % (g, st))
check("%d Kombinationen, alle bitgleich" % n, not schief,
      "; ".join(schief[:3]))

# Und mit Pause - die darf am Ergebnis natuerlich nichts aendern.
a = Attrappe(100000, 8, pause_us=50)
check("auch mit Pause dazwischen", a.lauf() == bytes(bild(100000)))

# ---------------------------------------------------------------------------
print()
print("Test 2: es wird wirklich in Stuecken geschrieben")
# ---------------------------------------------------------------------------
# Sonst waere der ganze Umbau wirkungslos und der Test oben gruen.
class Zaehlend(Attrappe):
    class Sicht(object):
        def __init__(self, ziel, zaehler):
            self.ziel, self.zaehler = ziel, zaehler

        def __setitem__(self, schluessel, wert):
            self.zaehler.append(schluessel)
            self.ziel[schluessel] = wert

        def __getitem__(self, schluessel):
            return self.ziel[schluessel]

    def __init__(self, groesse, stuecke):
        Attrappe.__init__(self, groesse, stuecke)
        self.zaehler = []
        self._mv_mm = Zaehlend.Sicht(memoryview(self.mm), self.zaehler)


z = Zaehlend(1920 * 1080 * 4, 16)
z.lauf()
check("16 angefragte Stuecke ergeben 16 Schreibvorgaenge",
      len(z.zaehler) == 16, "%d" % len(z.zaehler))
check("und sie decken das Bild luecken- und ueberschneidungsfrei ab",
      [s.start for s in z.zaehler] == [0] + [s.stop for s in z.zaehler[:-1]]
      and z.zaehler[-1].stop == z.size)
check("jedes Stueck faengt auf einer Bildpunktgrenze an",
      all(s.start % 4 == 0 for s in z.zaehler),
      "sonst waere ein Stueck mitten in einem Bildpunkt getrennt")

# ---------------------------------------------------------------------------
print()
print("Test 3: der Schalter - und dass er AUS ist")
# ---------------------------------------------------------------------------
check("die Klasse hat die Vorgabe 'ein Zug'", FB.haeppchen == 1,
      "%r" % FB.haeppchen)
check("und keine Pause", FB.haeppchen_pause == 0.0)

quelle = io.open(os.path.join(_REPO, "frontend", "fe", "framebuffer.py"),
                 encoding="utf-8").read()
check("flip() nimmt den alten Weg, solange der Schalter aus ist",
      "if self.haeppchen > 1:" in quelle)
check("der Schalter wird beim OEFFNEN gelesen, nicht je Bild",
      "_haeppchen_einrichten()" in quelle
      and quelle.count("flip_haeppchen\")") == 1,
      "eine Kartenabfrage je Bild war schon einmal ein Fehler")
check("memoryview statt Zwischenkopien",
      "memoryview(self.mm)" in quelle and "memoryview(self.buf)" in quelle,
      "self.mm[a:b] = self.buf[a:b] wuerde je Stueck eine Kopie erzeugen")

ein = io.open(os.path.join(_REPO, "frontend", "fe", "settings.py"),
              encoding="utf-8").read()
check("der Schalter ist in den Einstellungen dokumentiert",
      "FLIP_HAEPPCHEN_FLAG" in ein)
check("und als Messgegenstand gekennzeichnet, nicht als Funktion",
      "MESSGEGENSTAND" in ein)

# ---------------------------------------------------------------------------
print()
print("Test 4: kaputte Angaben bringen nichts durcheinander")
# ---------------------------------------------------------------------------
# Die Datei schreibt ein Mensch von Hand. Ein Tippfehler darf
# hoechstens dazu fuehren, dass der Schalter nicht greift.
class Leer(object):
    size = 4096
    mm = bytearray(4096)
    buf = bytearray(4096)


for wert, erwartet_an in (("", False), ("0", False), ("1", False),
                          ("aus", False), ("quatsch", True), ("16", True),
                          ("16:200", True), ("99999", True), ("-5", True),
                          ("8:99999999", True)):
    o = Leer()
    os.environ["DRAGEND_FLIP_HAEPPCHEN"] = wert
    try:
        FB._haeppchen_einrichten(o)
    finally:
        os.environ.pop("DRAGEND_FLIP_HAEPPCHEN", None)
    an = o.haeppchen > 1
    check("%-12s -> %s" % ("'" + wert + "'", "an" if an else "aus"),
          an == erwartet_an,
          "Stuecke %d, Pause %.6f s" % (o.haeppchen, o.haeppchen_pause))
    check("   Stuecke bleiben im sinnvollen Bereich",
          1 <= o.haeppchen <= 256, "%d" % o.haeppchen)
    check("   Pause bleibt unter 5 ms",
          0.0 <= o.haeppchen_pause <= 0.005,
          "%.6f s" % o.haeppchen_pause)

# Ohne Umgebungsvariable UND ohne Datei: aus.
o = Leer()
os.environ.pop("DRAGEND_FLIP_HAEPPCHEN", None)
FB._haeppchen_einrichten(o)
check("ohne Schalter bleibt es beim Flip in einem Zug", o.haeppchen == 1,
      "%d" % o.haeppchen)

# ---------------------------------------------------------------------------
print()
print("Test 5: das Frontend zeichnet damit unveraendert")
# ---------------------------------------------------------------------------
for b, h in ((1920, 1080), (320, 240)):
    H.SCREEN[:] = [b, h]
    f = H.make_frontend(page=1)
    f.draw()
    ohne = bytes(f.fb.buf)
    f2 = H.make_frontend(page=1)
    f2.fb.haeppchen = 16
    f2.fb._mv_mm = memoryview(f2.fb.mm) if hasattr(f2.fb, "mm") else None
    f2.fb._mv_buf = memoryview(f2.fb.buf)
    try:
        f2.draw()
        ok = True
    except Exception as e:                               # noqa: BLE001
        ok = False
        print("    ", type(e).__name__, e)
    check("%dx%-5d zeichnet mit Haeppchen ohne Fehler" % (b, h), ok)
    if ok:
        check("%dx%-5d und malt dasselbe" % (b, h),
              bytes(f2.fb.buf) == ohne)

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
