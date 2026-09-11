#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Was der Vorauslader dem Zeichnen wegnimmt (Diagnose, kein Test).

DIE FRAGE, um die es geht: Build 102 hat den Cover-Vorauslader vom
Hintergrund-Thread auf einen eigenen PROZESS umgestellt, mit der
Begruendung, dass Pythons GIL immer nur einen Thread rechnen laesst -
ein vorrechnender Thread nimmt dem Zeichnen also echte Rechenzeit weg,
ein eigener Prozess nicht (der laeuft auf dem zweiten CPU-Kern).

Das ist eine Behauptung ueber Zahlen, also wird sie gemessen. Verglichen
werden drei Zustaende bei sonst identischem Zeichenweg:

    Leerlauf   Vorauslader hat nichts zu tun - die Untergrenze.
    Thread     Vorauslader rechnet, wie bis Build 101, im selben Prozess.
    Prozess    Vorauslader rechnet, wie ab Build 102, nebenan.

Ausgegeben wird beides, was zaehlt: was das Zeichnen KOSTET, und wie
viele Miniaturen der Vorauslader in derselben Zeit SCHAFFT. Die zweite
Zahl ist der Grund, warum der Nutzer den Unterschied ueberhaupt merkt -
je mehr Cover vorgerechnet sind, desto seltener muss der Zeichenpfad
selbst rechnen, wenn beim Scrollen neue Zeilen ins Bild kommen.

WIE GEMESSEN WIRD, und warum so umstaendlich: die erste Fassung dieses
Skripts mass 60 Scrollschritte - auf CRT keine 25 Millisekunden. In
diesem Fenster wird kein einziger Auftrag fertig, und das Ergebnis war
reines Rauschen (einmal -7 %, einmal +311 % bei identischer Last).
Gemessen wird deshalb ueber ein festes ZEITfenster von drei Sekunden,
und von drei Durchlaeufen zaehlt der mittlere.

EINORDNUNG, ehrlich: dieser Rechner hat wie der MiSTer zwei Kerne, ist
aber deutlich schneller. Der Abstand zwischen "Leerlauf" und "Thread"
uebertraegt sich deshalb NICHT eins zu eins - auf dem Geraet ist er
groesser, weil dort eine einzelne Miniatur 200-500 ms braucht statt
weniger Millisekunden. Was sich uebertraegt, ist die Richtung.

Ausfuehren:
    python3 tools/diag_vorauslader.py
"""
import os
import shutil
import statistics
import struct
import sys
import tempfile
import time
import zlib

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)

import _harness as H                                    # noqa: E402

fm = H.fm
sys.path.insert(0, os.path.join(_REPO, "frontend"))
import fe.art as art                                    # noqa: E402
import fe.prewarm as P                                  # noqa: E402

MESSFENSTER = 3.0      # Sekunden je Durchlauf
DURCHLAEUFE = 3        # davon zaehlt der mittlere

TMP = tempfile.mkdtemp(prefix="diag_vorauslader_")
QUELLE = os.path.join(TMP, "quelle")
os.makedirs(QUELLE)


def art_datei(pfad, w, h):
    pix = bytearray()
    for y in range(h):
        for x in range(w):
            pix += bytes(((x * 3) % 256, (y * 5) % 256,
                          ((x + y) * 7) % 256, 0))
    with open(pfad, "wb") as f:
        f.write(b"ART1" + struct.pack("<HH", w, h)
                + zlib.compress(bytes(pix), 1))


# Ein Original, viele Kopien: gleicher Rechenaufwand je Auftrag, aber
# jede Kopie hat ihren eigenen Schluessel im Zwischenspeicher und muss
# deshalb wirklich gerechnet werden. Genug davon, dass dem Vorauslader
# in keinem Durchlauf die Arbeit ausgeht.
MASTER = os.path.join(QUELLE, "master.art")
art_datei(MASTER, 240, 336)
BILDER = []
for i in range(2000):
    b = os.path.join(QUELLE, "k%04d.art" % i)
    shutil.copyfile(MASTER, b)
    BILDER.append(b)


def liste(w, h, anzahl=400):
    H.set_screen(w, h)
    f = H.make_frontend(page=1)
    nd = f._current_node()
    nd["items"] = [(H.TITLES[i % len(H.TITLES)] + " %d" % i, "game",
                    ("/f/%d.sfc" % i, ".sfc", "SNES", None, None))
                   for i in range(anzahl)]
    nd.pop("_display_items_cache", None)
    f.item_i = 0
    f.scroll = 0
    f.draw_page_items(flip=False)
    return f


def messen(f):
    """Drei Sekunden lang scrollen, mittlere Dauer je Schritt liefern."""
    def schritt():
        f._last_input_time = time.monotonic()
        f.item_i += 1
        f.scroll += 1
        if f.item_i > 380:
            f.item_i, f.scroll = 0, 0
        f.draw_page_items(flip=False)

    for _ in range(20):
        schritt()
    n = 0
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < MESSFENSTER:
        schritt()
        n += 1
    return (time.perf_counter() - t0) / n * 1000.0


def mit_vorauslader(f, betriebsart):
    """Den Vorauslader dauerhaft beschaeftigen und dabei messen."""
    art.THUMB_CACHE_DIR = os.path.join(
        TMP, "cache_%s_%d" % (betriebsart, time.time() * 1000))
    echter = P.WORKER
    if betriebsart == "thread":
        P.WORKER = os.path.join(TMP, "gibt_es_nicht.py")
    pw = P.CoverPrewarmer()
    pw.start()
    if pw.betriebsart() != betriebsart:
        P.WORKER = echter
        pw.beenden()
        return None, 0
    pw.uebergeben([(b, 150, 210) for b in BILDER])
    try:
        return messen(f), pw.gerechnet
    finally:
        pw.beenden()
        P.WORKER = echter


def median_lauf(f, betriebsart):
    ergebnisse = [mit_vorauslader(f, betriebsart)
                  for _ in range(DURCHLAEUFE)]
    if any(t is None for t, _g in ergebnisse):
        return None, 0
    return (statistics.median([t for t, _g in ergebnisse]),
            max(g for _t, g in ergebnisse))


print("Was der Vorauslader dem Zeichnen wegnimmt")
print("(%.0fs Messfenster, Mittlerer aus %d Durchlaeufen - siehe Kopf)"
      % (MESSFENSTER, DURCHLAEUFE))
print()
print("%-6s %-12s %10s %22s %22s"
      % ("Modus", "Aufloesung", "Leerlauf", "Thread (bis 101)",
         "Prozess (ab 102)"))

for w, h, name in ((320, 240, "CRT"), (1920, 1080, "HDMI")):
    f = liste(w, h)
    t_leer = statistics.median([messen(f) for _ in range(DURCHLAEUFE)])
    t_th, g_th = median_lauf(f, "thread")
    t_pr, g_pr = median_lauf(f, "prozess")
    if t_th is None or t_pr is None:
        print("%-6s %-12s  Betriebsart nicht herstellbar - uebersprungen"
              % (name, "%dx%d" % (w, h)))
        continue
    print("%-6s %-12s %9.3fms %9.3fms %+5.0f%% %5d %9.3fms %+5.0f%% %5d"
          % (name, "%dx%d" % (w, h), t_leer,
             t_th, (t_th / t_leer - 1) * 100, g_th,
             t_pr, (t_pr / t_leer - 1) * 100, g_pr))

shutil.rmtree(TMP, ignore_errors=True)
print()
print("Je Betriebsart: Dauer eines Scrollschritts, Aufschlag gegenueber")
print("Leerlauf, und wie viele Miniaturen in derselben Zeit fertig")
print("wurden. Der Thread teilt sich die Rechenzeit mit dem Zeichnen -")
print("er bremst es UND kommt dabei selbst langsamer voran.")
sys.exit(0)
