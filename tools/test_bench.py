#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Der Bench-Modus (Build 177).

WORUM ES GEHT

Jede Messung in diesem Projekt seit Build 73 war Handarbeit:
DRAGEND_PROFILE setzen, scrollen, "grep PERF", abtippen. Das ergibt
Zahlen fuer GENAU dieses Geraet an GENAU diesem Tag - zwischen zwei
Geraeten laesst sich damit nichts vergleichen.

"--bench" macht daraus einen festen Ablauf. Der entscheidende Teil
des Entwurfs ist, dass die Kernzahlen NICHT vom Bestand abhaengen:
das Testbild wird erzeugt, die Bildgroessen stehen fest, die Zahl der
Schritte steht fest.

DIE ZWEI FALLEN, DIE DIESER TEST BEWACHT

1. DER BENCH DARF NICHTS AUF DER KARTE ANFASSEN. Er rechnet
   Miniaturen aus und schreibt sie - wenn das im echten Cache landet,
   ist der erste Bench-Lauf eines Nutzers ein stiller Eingriff in
   seinen Bestand. Test 4 legt eine Attrappe ueber /media/fat und
   prueft, dass dort nichts entsteht.

2. EIN BENCH, DER BEIM ERSTEN UNERWARTETEN DING ABBRICHT, IST
   NUTZLOS. Er laeuft auf fremden Geraeten, mit fremden Bestaenden,
   ohne Artwork, ohne C-Modul. Test 5 nimmt ihm nacheinander Teile
   weg und prueft, dass trotzdem ein vollstaendiger Bericht
   herauskommt.

Ausfuehren:
    python3 tools/test_bench.py
"""
import io
import os
import sys
import tempfile
import time
import zlib

# VOR dem Pruefstand merken: tools/_harness.py friert time.monotonic()
# auf einen festen Wert ein, damit Puls und Laufschrift in den
# Zeichentests reproduzierbar sind. Fuer ein BENCH ist das toedlich -
# jede Messung waere 0.00 ms, und der Test wuerde nur pruefen, dass
# Nullen an der richtigen Stelle stehen. Waehrend der Bench-Laeufe
# unten wird deshalb kurz die echte Uhr eingesetzt.
_ECHTE_UHR = time.monotonic

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
sys.path.insert(0, _HIER)

# Wie tools/test_c_modul.py: ohne die x86-Fassung wuerde der Vergleich
# "C gegen Python" nichts pruefen.
if not os.environ.get("DRAGEND_LIB"):
    for _k in (os.path.join(_REPO, "frontend", "c", "libdragend_x86.so"),
               os.path.join(_REPO, "frontend", "libdragend_x86.so")):
        if os.path.exists(_k):
            os.environ["DRAGEND_LIB"] = _k
            break

import _harness as H                                     # noqa: E402

fm = H.fm
import fe.art as A                                       # noqa: E402
import fe.settings as S                                  # noqa: E402
import fe.bench as B                                     # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


# Klein rechnen - dieser Test prueft den ABLAUF, nicht die
# Geschwindigkeit. Mit den echten Massen (1200x1600, 60 Schritte,
# neun Wiederholungen) liefe er Minuten.
B.QUELL_B, B.QUELL_H = 60, 80
B.ZIEL_B, B.ZIEL_H = 29, 38
B.KLEIN_B, B.KLEIN_H = 9, 12
B.WDH_BILLIG, B.WDH_TEUER = 2, 1
B.SCHRITTE = 3

H.SCREEN[:] = [1920, 1080]


def lauf(fe=None):
    gefroren = fm.time.monotonic
    fm.time.monotonic = _ECHTE_UHR
    try:
        return B.lauf(fe or H.make_frontend(page=0), fm, A, S,
                      startdauer=1.234, log=None)
    finally:
        fm.time.monotonic = gefroren


# ---------------------------------------------------------------------------
print("Test 1: der Bericht entsteht und ist vollstaendig")
# ---------------------------------------------------------------------------
text = lauf()
for marke in ("Dragend Bench", "A  START", "B  ZEICHNEN", "C  BILDKETTE",
              "D  ECHTE DATEI", "Nichts auf der Karte wurde veraendert"):
    check("Abschnitt %-24s steht im Bericht" % ("'" + marke + "'"),
          marke in text)
check("kein Abschnitt ist abgebrochen",
      "ABGEBROCHEN" not in text,
      [z for z in text.splitlines() if "ABGEBROCHEN" in z][:2])
check("keine FEHLER-Zeile im Bericht",
      "FEHLER" not in text,
      [z for z in text.splitlines() if "FEHLER" in z][:2])

# ---------------------------------------------------------------------------
print()
print("Test 2: die Kopfdaten sagen, WORAUF gemessen wurde")
# ---------------------------------------------------------------------------
# Ohne die ist eine Zahl wertlos - genau das war das Problem an den
# bisher von Hand abgetippten Messwerten.
for feld in ("Build", "System", "Python", "Anzeige", "C-Modul",
             "Verkleinern", "Bestand"):
    check("Kopfzeile %-12s vorhanden" % feld,
          any(z.startswith(feld) for z in text.splitlines()))
check("die Aufloesung steht wirklich drin", "1920x1080" in text)
check("und der Hinweis auf die Vergleichbarkeit",
      "VERGLEICHBAR" in text and "NICHT vergleichbar" in text)

# ---------------------------------------------------------------------------
print()
print("Test 3: die bestandsabhaengigen Zahlen sind JE SPIEL normiert")
# ---------------------------------------------------------------------------
# Das ist der Punkt, an dem 2000 und 97000 Spiele vergleichbar werden.
check("der Startwert wird je Spiel ausgewiesen",
      "je Spiel" in text or "kein Bestand erkannt" in text)
check("die Startdauer selbst steht da",
      "1234.00 ms" in text, [z for z in text.splitlines()
                             if "Start bis" in z][:1])

# ---------------------------------------------------------------------------
print()
print("Test 4: DER BENCH FASST DIE KARTE NICHT AN")
# ---------------------------------------------------------------------------
# Die Attrappe sandboxt /media/fat NICHT (siehe tools/_harness.py) -
# hier wird deshalb von Hand ein Ersatzordner untergeschoben und
# danach nachgesehen, ob etwas darin gelandet ist.
sandbox = tempfile.mkdtemp(prefix="bench_karte_")
alt_thumb = A.THUMB_CACHE_BASE
alt_art = A.ART_BASE
try:
    A.THUMB_CACHE_BASE = os.path.join(sandbox, "thumbs")
    A.ART_BASE = os.path.join(sandbox, "art")
    vorher = set()
    for wurzel, _d, dateien in os.walk(sandbox):
        for d in dateien:
            vorher.add(os.path.join(wurzel, d))
    lauf()
    nachher = set()
    for wurzel, _d, dateien in os.walk(sandbox):
        for d in dateien:
            nachher.add(os.path.join(wurzel, d))
    neu = nachher - vorher
    check("keine einzige Datei im Cache-Ordner entstanden",
          not neu, "%d neue: %s" % (len(neu), sorted(neu)[:3]))
finally:
    A.THUMB_CACHE_BASE = alt_thumb
    A.ART_BASE = alt_art

# Und der temporaere Ordner, in dem der Bench WIRKLICH schreibt, muss
# hinterher weg sein - sonst sammelt sich bei jedem Lauf Muell in /tmp.
vor_tmp = set(p for p in os.listdir(tempfile.gettempdir())
              if p.startswith("dragend_bench_"))
lauf()
nach_tmp = set(p for p in os.listdir(tempfile.gettempdir())
               if p.startswith("dragend_bench_"))
check("der temporaere Arbeitsordner wird wieder aufgeraeumt",
      nach_tmp <= vor_tmp, "uebrig: %s" % sorted(nach_tmp - vor_tmp)[:3])

# ---------------------------------------------------------------------------
print()
print("Test 5: er laeuft auch durch, wenn etwas FEHLT")
# ---------------------------------------------------------------------------
# Der Bench landet auf fremden Geraeten. Dort fehlt mal das C-Modul,
# mal das Artwork, mal sieht der Kategoriebaum anders aus als hier.
alt_lib = A._LIB
try:
    A._LIB = None
    t2 = lauf()
    check("ohne C-Modul laeuft er durch",
          "ABGEBROCHEN" not in t2 and "C  BILDKETTE" in t2)
    check("und sagt ehrlich, dass Python rechnet",
          "NICHT geladen" in t2)
finally:
    A._LIB = alt_lib

alt_pfad = A.art_path
try:
    A.art_path = lambda *a, **k: None
    t3 = lauf()
    check("ohne jedes Cover laeuft er durch",
          "ABGEBROCHEN" not in t3)
    check("und sagt, dass Abschnitt D uebersprungen wurde",
          "uebersprungen" in t3)
finally:
    A.art_path = alt_pfad


class KaputterBaum(object):
    """Ein Kategoriebaum, der auf jede Frage mit einer Ausnahme
    antwortet - das Schlimmste, was _zaehlen() passieren kann."""

    def __iter__(self):
        raise RuntimeError("kaputt")

    def values(self):
        raise RuntimeError("kaputt")


fe = H.make_frontend(page=0)
fe.cats = [("Kaputt", KaputterBaum(), "snes")]
t4 = lauf(fe)
check("ein unlesbarer Kategoriebaum bringt ihn nicht um",
      "ABGEBROCHEN" not in t4 and "Ende." in t4)

# ---------------------------------------------------------------------------
print()
print("Test 6: das erzeugte Testbild taugt als Messgrundlage")
# ---------------------------------------------------------------------------
# Wenn das Bild aus einer einzigen Farbe bestuende, waere die
# Cache-Messung eine Messung von "zlib komprimiert Nullen".
pix = B.testbild(64, 48)
check("es hat die richtige Groesse", len(pix) == 64 * 48 * 4,
      "%d" % len(pix))
check("es ist bei jedem Lauf dasselbe", pix == B.testbild(64, 48))
farben = set(bytes(pix[i:i + 4]) for i in range(0, len(pix), 4))
check("es hat viele verschiedene Farbwerte", len(farben) > 200,
      "%d" % len(farben))
gepackt = len(zlib.compress(pix, 6))
check("es laesst sich nicht unrealistisch gut packen",
      gepackt * 20 > len(pix),
      "%d von %d Bytes (%.0f %%)"
      % (gepackt, len(pix), 100.0 * gepackt / len(pix)))

# Und das erzeugte PNG muss ein PNG sein, das unser eigener Leseweg
# auch wirklich versteht - sonst misst Abschnitt C einen Fehlschlag.
png = B.testbild_png(pix, 64, 48)
check("das erzeugte PNG hat die richtige Signatur",
      png.startswith(b"\x89PNG\r\n\x1a\n"))
ordner = tempfile.mkdtemp(prefix="bench_png_")
try:
    p = os.path.join(ordner, "x.png")
    io.open(p, "wb").write(png)
    gelesen = A.original_lesen(p, 32, 24)
    check("und original_lesen() kann es lesen", gelesen is not None,
          "sonst misst Abschnitt C einen Fehlschlag statt eine Dauer")
    if gelesen:
        check("mit den richtigen Massen", gelesen[3] == (64, 48),
              str(gelesen[3]))
finally:
    import shutil
    shutil.rmtree(ordner, ignore_errors=True)

# Das eigene Format ebenso.
art1 = B.testbild_art1(pix, 64, 48)
check("das erzeugte ART1 faengt mit der Kennung an",
      art1.startswith(b"ART1"))

# ---------------------------------------------------------------------------
print()
print("Test 7: der Median, nicht der Mittelwert")
# ---------------------------------------------------------------------------
# Auf einem Geraet, auf dem nebenher etwas laeuft, verschiebt EIN
# Ausreisser den Mittelwert und macht die Zahl unbrauchbar.
check("gerade Anzahl", abs(B._median([1, 2, 3, 4]) - 2.5) < 1e-9)
check("ungerade Anzahl", B._median([5, 1, 3]) == 3)
check("ein Ausreisser zieht ihn nicht mit",
      B._median([1, 1, 1, 1, 1000]) == 1)
check("leere Liste ergibt 0", B._median([]) == 0.0)

zaehler = [0]


def _zaehl():
    zaehler[0] += 1


ms, best = B.messen(_zaehl, 5)
check("messen() ruft genau so oft auf, wie verlangt", zaehler[0] == 5,
      "%d" % zaehler[0])
check("und liefert zwei Zahlen", ms >= 0 and best >= 0 and best <= ms)
import gc                                                # noqa: E402
check("die Muellabfuhr laeuft danach wieder", gc.isenabled(),
      "sonst waechst der Speicher bis zum Ende des Laufs")

# ---------------------------------------------------------------------------
print()
print("Test 8: der Schalter haengt am Einstieg")
# ---------------------------------------------------------------------------
quelle = io.open(os.path.join(_REPO, "frontend", "frontend.py"),
                 encoding="utf-8").read()
check('"--bench" wird in sys.argv gesucht', '"--bench" in sys.argv' in quelle)
check("das Bench-Modul wird dort geladen", "import fe.bench as BENCH" in quelle)
check("es bekommt das MODUL fe.art, nicht den ArtCache",
      'sys.modules["fe.art"]' in quelle,
      "ART ist eine Instanz - original_lesen() gaebe es dort nicht")
check("der Bericht wird zusaetzlich in eine Datei geschrieben",
      "BENCH_AUSGABE" in quelle)
check("und die liegt in /tmp, nicht auf der Karte",
      'BENCH_AUSGABE = "/tmp/' in quelle)
# Ohne das bliebe nach dem Bench ein schwarzer Schirm mit Cursor
# stehen, statt zurueck ins MiSTer-Menue zu gehen - genau der
# Fehler aus Build 163/165/166, nur an einer neuen Stelle.
_nach_bench = quelle.split('"--bench" in sys.argv')[1][:2500]
check("danach wird sauber beendet (Bildschirm zurueck an MiSTer)",
      "_fe._beenden()" in _nach_bench)
check("und der Prozess endet dort, statt in run() weiterzulaufen",
      "sys.exit(0)" in _nach_bench)

bq = io.open(os.path.join(_REPO, "frontend", "fe", "bench.py"),
             encoding="utf-8").read()
check("fe/bench.py importiert das Frontend NICHT",
      "import frontend" not in bq,
      "sonst gaebe es zwei Ladewege fuer dieselbe Datei")

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
