#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Der Rueckleser (Build 182) - ein Messgegenstand.

WORUM ES GEHT

Vier Erklaerungen fuer das Zucken bei 1080p sind durchgemessen und
tot: Eingabe-Leck, uebersprungenes Vsync, Speicherdurchsatz (Build 181:
ein dreifach entzerrter Flip aendert nichts) und der Cover-Weg (es
zuckt auch in Kategorien ohne ein einziges Cover). Uebrig bleiben zwei
Moeglichkeiten, die einander ausschliessen:

  A) Jemand SCHREIBT in den Bildspeicher hinein.
  B) Niemand schreibt, die Anzeige-Ebene wird WEGGESCHALTET.

fb_wacht.py entscheidet das ohne Frontend. Der Rueckleser stellt
dieselbe Frage im laufenden Betrieb: er merkt sich beim Schreiben ein
paar Zeilen und vergleicht sie beim naechsten Bild.

WAS DIESER TEST ABSICHERT

Vor allem den FEHLALARM. Ein Messgegenstand, der faelschlich anschlaegt,
ist schlimmer als keiner - er schickt uns auf eine Spur, die es nicht
gibt. Zwei Quellen dafuer gibt es:

  - die Laufschrift (flip_rows schreibt nur ein Band; die Proben
    ausserhalb muessen trotzdem stimmen, die darin muessen
    aufgefrischt werden),
  - der erste Durchgang, in dem noch gar nichts gemerkt wurde.

Dazu: dass er standardmaessig AUS ist, dass er nichts am Bild aendert,
und dass ein Tippfehler in der Schalterdatei hoechstens dazu fuehrt,
dass er nicht greift.

Ausfuehren:
    python3 tools/test_rueckleser.py
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
meldungen = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


# Das Log abfangen, damit die Treffermeldungen pruefbar sind. Gepatcht
# werden muss fe.framebuffer.LOG und NICHT frontend.LOG - das Modul
# holt sich seinen eigenen Namen beim Import. Beim ersten Anlauf lief
# der Test genau deswegen rot, und zwar mit "keine Meldung", was wie
# ein fehlendes Feature aussah und keines war.
import fe.framebuffer as FBM                             # noqa: E402
FBM.LOG = lambda s: meldungen.append(s)


class Attrappe(object):
    """Gerade so viel Framebuffer, wie der Rueckleser anfasst."""

    _rueckleser_einrichten = FB._rueckleser_einrichten
    _rueckleser_pruefen = FB._rueckleser_pruefen
    _rueckleser_merken = FB._rueckleser_merken
    _rueckleser_bilanz = FB._rueckleser_bilanz

    def __init__(self, breite=64, hoehe=32, proben="8"):
        self.width, self.height = breite, hoehe
        self.stride = breite * 4
        self.size = self.stride * hoehe
        self.mm = bytearray(self.size)
        self.buf = bytearray(
            bytearray((i * 7 + (i >> 11)) & 255 for i in range(self.size)))
        os.environ["DRAGEND_FLIP_RUECKLESER"] = proben
        try:
            self._rueckleser_einrichten()
        finally:
            os.environ.pop("DRAGEND_FLIP_RUECKLESER", None)

    def voll_schreiben(self):
        self._rueckleser_pruefen()
        self.mm[:] = self.buf
        self._rueckleser_merken()

    def band_schreiben(self, y0, y1):
        self._rueckleser_pruefen()
        a, b = y0 * self.stride, y1 * self.stride
        self.mm[a:b] = self.buf[a:b]
        self._rueckleser_merken(y0, y1)


# ---------------------------------------------------------------------------
print("Test 1: er ist aus, solange niemand ihn einschaltet")
# ---------------------------------------------------------------------------
check("die Klasse hat die Vorgabe 'aus'", FB.rueckleser == 0,
      "%r" % FB.rueckleser)
check("und keine Proben", FB._rueck_proben is None)

quelle = io.open(os.path.join(_REPO, "frontend", "fe", "framebuffer.py"),
                 encoding="utf-8").read()
check("flip() prueft nur, wenn Proben da sind",
      quelle.count("if self._rueck_proben is not None:") == 3,
      "je einmal vor und nach dem Vollbild, einmal nach dem Band")
check("die Schalterdatei wird nur beim Start gelesen",
      quelle.count('flip_rueckleser") as f') == 1,
      "eine Kartenabfrage je Bild war schon einmal ein Fehler")

ein = io.open(os.path.join(_REPO, "frontend", "fe", "settings.py"),
              encoding="utf-8").read()
check("der Schalter ist dokumentiert", "RUECKLESER_FLAG" in ein)
check("und als Messgegenstand gekennzeichnet",
      "MESSGEGENSTAND (Build 182)" in ein)

# ---------------------------------------------------------------------------
print()
print("Test 2: ein fremder Schreibzugriff wird gefunden")
# ---------------------------------------------------------------------------
a = Attrappe(proben="8")
check("acht Proben-Zeilen eingerichtet", len(a._rueck_offsets) == 8,
      "%r" % (a._rueck_offsets,))
check("ueber das ganze Bild verteilt",
      a._rueck_offsets[0] == 0 and a._rueck_offsets[-1] >= a.height * 3 // 4,
      "%r" % (a._rueck_offsets,))

# Build 189: der obere Textbereich MUSS abgedeckt sein. Dort taucht
# fremde Ausgabe auf - der Konsolencursor sass auf dem Geraet des
# Nutzers in den Zeilen 32-47 (gemessen mit fb_wacht --wache, 116
# Treffer in 30 s), der Login-Gruss steht in denselben Zeilen. Mit
# rein gleichmaessigen Proben (0, 135, 270, ...) war der Rueckleser
# genau dafuer blind, wofuer man ihn am dringendsten braucht.
gross = Attrappe(breite=64, hoehe=1080, proben="8")
oben = [z for z in gross._rueck_offsets if z < 64]
check("mindestens zwei Proben im oberen Textbereich", len(oben) >= 2,
      "%r" % (gross._rueck_offsets,))
check("und eine davon dort, wo der Cursor sass (32-47)",
      any(32 <= z < 48 for z in gross._rueck_offsets),
      "%r" % (gross._rueck_offsets,))
check("der Rest deckt weiterhin das ganze Bild ab",
      max(gross._rueck_offsets) >= 810,
      "sonst faellt ein Vollbild-Ereignis unten durch")

a.voll_schreiben()
check("erster Durchgang meldet nichts", a._rueck_treffer == 0,
      "beim ersten Bild war noch nichts gemerkt")
a.voll_schreiben()
check("und der zweite auch nicht, wenn niemand dazwischenfunkt",
      a._rueck_treffer == 0)

# Jetzt schreibt jemand anders hinein - genau das, was wir suchen.
fremd = 12
ab = fremd * a.stride
a.mm[ab:ab + a.stride] = b"\xAA" * a.stride
a.voll_schreiben()
check("ein veraenderter Bildspeicher wird erkannt", a._rueck_treffer == 1,
      "%d Treffer" % a._rueck_treffer)
check("und die Zeile steht in der Meldung",
      any("RUECKLESER" in m and str(fremd) in m for m in meldungen),
      meldungen[-1] if meldungen else "keine Meldung")

# Danach ist der Bildspeicher wieder unser - kein Dauerfeuer.
vorher = a._rueck_treffer
a.voll_schreiben()
check("danach wieder Ruhe", a._rueck_treffer == vorher,
      "%d -> %d" % (vorher, a._rueck_treffer))

# ---------------------------------------------------------------------------
print()
print("Test 3: DER FEHLALARM - die Laufschrift darf nichts ausloesen")
# ---------------------------------------------------------------------------
# flip_rows() schreibt nur ein Band. Wuerden die Proben darin nicht
# aufgefrischt, meldete der Rueckleser jede Laufschrift als fremden
# Inhalt - und wir suchten monatelang etwas, das es nicht gibt.
b = Attrappe(proben="8")
b.voll_schreiben()
b.voll_schreiben()
start = b._rueck_treffer
for runde in range(20):
    # Die Laufschrift aendert ihren Inhalt und schreibt ihr Band neu.
    for y in range(10, 14):
        z = y * b.stride
        b.buf[z:z + b.stride] = bytes(
            bytearray((y * 31 + runde * 7 + i) & 255
                      for i in range(b.stride)))
    b.band_schreiben(10, 14)
check("20 Durchgaenge Laufschrift, kein einziger Fehlalarm",
      b._rueck_treffer == start, "%d Treffer" % (b._rueck_treffer - start))

# Aber ein fremder Zugriff AUSSERHALB des Bandes muss weiterhin auffallen.
z = 24 * b.stride
b.mm[z:z + b.stride] = b"\x5A" * b.stride
b.band_schreiben(10, 14)
check("ein fremder Zugriff ausserhalb des Bandes faellt trotzdem auf",
      b._rueck_treffer == start + 1,
      "%d Treffer" % (b._rueck_treffer - start))

# ---------------------------------------------------------------------------
print()
print("Test 3b: DAS SCHWEIGEN MUSS AUSWERTBAR SEIN (Build 183)")
# ---------------------------------------------------------------------------
# Build 182 schrieb nur bei einem TREFFER ins Log. Bleibt der
# Rueckleser stumm, laesst sich daraus nicht unterscheiden, ob er
# nichts gefunden hat oder ob er gar nicht lief - und genau daran ist
# die erste Messung bei SuTe haengengeblieben. Ein Messgegenstand, der
# nur bei Erfolg redet, kann eine Vermutung nur bestaetigen und nie
# widerlegen.
d = Attrappe(proben="8")
d._rueck_letzte_bilanz = d._rueck_start - 31.0    # 30 s sind vorbei
del meldungen[:]
d.voll_schreiben()
d.voll_schreiben()
bilanz = [m for m in meldungen if "RUECKLESER-BILANZ" in m]
check("ohne einen einzigen Treffer kommt trotzdem eine Zeile",
      len(bilanz) == 1, "%d Zeilen" % len(bilanz))
check("und sie nennt Bilder UND Treffer",
      bilanz and "Bilder geprueft" in bilanz[0]
      and "0 Treffer" in bilanz[0],
      bilanz[0] if bilanz else "")
del meldungen[:]
for _ in range(50):
    d.voll_schreiben()
check("danach 30 Sekunden Ruhe, kein Dauerfeuer",
      not [m for m in meldungen if "BILANZ" in m],
      "%d Zeilen in 50 Bildern" % len(meldungen))

# ---------------------------------------------------------------------------
print()
print("Test 4: kaputte Angaben bringen nichts durcheinander")
# ---------------------------------------------------------------------------
for wert, erwartet_an in (("", False), ("0", False), ("aus", False),
                          ("off", False), ("quatsch", True), ("8", True),
                          ("1", True), ("9999", True), ("-5", True)):
    c = Attrappe(proben=wert)
    an = c._rueck_proben is not None
    check("%-10s -> %s" % ("'" + wert + "'", "an" if an else "aus"),
          an == erwartet_an, "%d Proben" % len(c._rueck_offsets))
    if an:
        check("   Anzahl bleibt im sinnvollen Bereich",
              1 <= len(c._rueck_offsets) <= 64,
              "%d" % len(c._rueck_offsets))
        check("   und keine Probe liegt ausserhalb des Bildes",
              all(0 <= z < c.height for z in c._rueck_offsets))

# Ohne Umgebungsvariable UND ohne Datei: aus.
class Leer(object):
    height = 1080
    stride = 7680


o = Leer()
os.environ.pop("DRAGEND_FLIP_RUECKLESER", None)
FB._rueckleser_einrichten(o)
check("ohne Schalter bleibt er aus", o._rueck_proben is None)

# ---------------------------------------------------------------------------
print()
print("Test 5: das Frontend zeichnet damit unveraendert")
# ---------------------------------------------------------------------------
for br, ho in ((1920, 1080), (320, 240)):
    H.SCREEN[:] = [br, ho]
    f = H.make_frontend(page=1)
    f.draw()
    ohne = bytes(f.fb.buf)

    f2 = H.make_frontend(page=1)
    os.environ["DRAGEND_FLIP_RUECKLESER"] = "8"
    try:
        FB._rueckleser_einrichten(f2.fb)
    finally:
        os.environ.pop("DRAGEND_FLIP_RUECKLESER", None)
    try:
        f2.draw()
        ok = True
    except Exception as e:                               # noqa: BLE001
        ok = False
        print("    ", type(e).__name__, e)
    check("%dx%-5d zeichnet mit Rueckleser ohne Fehler" % (br, ho), ok)
    if ok:
        check("%dx%-5d und malt dasselbe" % (br, ho),
              bytes(f2.fb.buf) == ohne)

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
