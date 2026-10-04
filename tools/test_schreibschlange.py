#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Die Schreib-Warteschlange fuer Miniaturen (Build 247).

DER BEFUND, auf den sie antwortet, steht im Bench vom 04.10.
(Abschnitt B, neu seit Build 245):

    Spieleliste liste    je Schritt kalt      294.61 ms
       davon dekodieren 94.4, verkleinern 43.3, Rest 156.9 ms
       DANEBEN (eigene Threads, nicht im Schritt enthalten):
         Miniaturen packen und schreiben 590.1 ms (44 x) - auf zwei Kernen

590 ms Hintergrundarbeit je Schritt bei einem Schritt von 294 ms, auf
einem Geraet mit ZWEI Kernen. Beide Kerne waren mit zlib und
SD-Schreiben belegt, waehrend daneben gezeichnet wurde - das war der
unbenannte Rest.

WORAN DIESE AENDERUNG SCHEITERN KANN, und genau das steht hier:

  1. Es laufen trotzdem mehrere Schreibvorgaenge gleichzeitig - dann
     ist nichts gewonnen.
  2. Die Schlange waechst unbegrenzt. Ein Cover der Boxart-Spalte sind
     1,78 MB; beim Schnellscrollen durch neues Gebiet waechst sie
     schneller, als die Karte schreiben kann.
  3. Beim Verwerfen fliegt der FALSCHE heraus (der neue statt des
     aeltesten) - dann wird immer das gerade Gebrauchte verworfen.
  4. Die Buchfuehrung driftet: der Byte-Zaehler passt nicht mehr zur
     Schlange, und die Grenze greift zu frueh oder nie.
  5. "Miniaturen vorbereiten" verliert Eintraege. Dort darf NICHTS
     verworfen werden - das ist der ganze Zweck des Durchlaufs.

Ausfuehren:
    python3 tools/test_schreibschlange.py
"""
import io
import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H                                        # noqa: E402

import fe.art as A                                          # noqa: E402

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


class _Mitschrift(object):
    """Ersetzt _thumb_cache_put und zaehlt mit, wie viele Aufrufe
    GLEICHZEITIG laufen. Diese Zahl ist der ganze Unterschied zwischen
    vorher und jetzt - und sie haengt an keiner Uhr."""

    def __init__(self, dauer=0.03):
        self.dauer = dauer
        self.lock = threading.Lock()
        self.jetzt = 0
        self.hoechstens = 0
        self.reihenfolge = []
        self.marken = []

    def put(self, path, w, h, tw, th, pix):
        with self.lock:
            self.jetzt += 1
            self.hoechstens = max(self.hoechstens, self.jetzt)
        time.sleep(self.dauer)
        with self.lock:
            self.jetzt -= 1
            self.reihenfolge.append(path)

    def marke(self, path, w, h):
        with self.lock:
            self.marken.append(("marke", path))
            self.reihenfolge.append(("marke", path))


_echt_put = A._thumb_cache_put
_echt_marke = A._thumb_cache_put_marke


def _leeren():
    with A._schreib_lock:
        del A._schreib_queue[:]
        A._schreib_bytes = 0


def _bild(nr, kb):
    return ("/art/%03d.png" % nr, 578, 770, 578, 770, b"\x00" * (kb * 1024))


# ---------------------------------------------------------------------------
print("Test 1: EIN Schreibvorgang gleichzeitig, Reihenfolge erhalten")
# ---------------------------------------------------------------------------
m = _Mitschrift(0.03)
A._thumb_cache_put = m.put
A._thumb_cache_put_marke = m.marke
try:
    _leeren()
    for i in range(10):
        A._thumb_cache_put_async(*_bild(i, 32))
    fertig = A.thumb_schreib_abwarten(20.0)
    time.sleep(0.2)
finally:
    A._thumb_cache_put = _echt_put
    A._thumb_cache_put_marke = _echt_marke

check("die Schlange wird leer", fertig)
check("hoechstens EIN Schreibvorgang gleichzeitig", m.hoechstens == 1,
      "gemessen: %d - vorher war es einer JE COVER" % m.hoechstens)
check("alle zehn sind geschrieben", len(m.reihenfolge) == 10,
      "%d von 10" % len(m.reihenfolge))
check("und zwar in der Reihenfolge, in der sie kamen",
      m.reihenfolge == ["/art/%03d.png" % i for i in range(10)])

# ---------------------------------------------------------------------------
print()
print("Test 2: die Grenze greift, und der AELTESTE fliegt heraus")
# ---------------------------------------------------------------------------
# Der Arbeitsfaden wird mit einem langen Auftrag beschaeftigt, damit
# sich die Schlange ueberhaupt fuellen kann.
m2 = _Mitschrift(2.0)
A._thumb_cache_put = m2.put
A._thumb_cache_put_marke = m2.marke
try:
    _leeren()
    vor = A.thumb_schreib_stand()
    A._thumb_cache_put_async(*_bild(999, 1024))   # haelt den Faden fest
    time.sleep(0.15)
    stueck_kb = 2048
    anzahl = int(A.SCHREIB_QUEUE_MAX_BYTES / (stueck_kb * 1024)) + 8
    for i in range(anzahl):
        A._thumb_cache_put_async(*_bild(i, stueck_kb))
    stand = A.thumb_schreib_stand()
    with A._schreib_lock:
        drin = [a[1] for a in A._schreib_queue]
        summe = sum(A._auftrag_bytes(a) for a in A._schreib_queue)
finally:
    A._thumb_cache_put = _echt_put
    A._thumb_cache_put_marke = _echt_marke
    _leeren()

check("die Grenze wird nicht ueberschritten",
      stand[1] <= A.SCHREIB_QUEUE_MAX_BYTES,
      "%.1f von %.1f MB" % (stand[1] / 1048576.0,
                            A.SCHREIB_QUEUE_MAX_BYTES / 1048576.0))
check("es wurde ueberhaupt verworfen", stand[3] > vor[3],
      "%d Eintraege" % (stand[3] - vor[3]))
check("der Byte-Zaehler passt zur Schlange", summe == stand[1],
      "gezaehlt %d, wirklich %d" % (stand[1], summe))
check("herausgefallen ist der AELTESTE, nicht der neue",
      drin and drin[-1] == "/art/%03d.png" % (anzahl - 1),
      "juengster noch drin: %s" % (drin[-1] if drin else "-"))
check("und der aelteste ist weg", "/art/000.png" not in drin)

# ---------------------------------------------------------------------------
print()
print("Test 3: Marken und Bilder in EINER Schlange")
# ---------------------------------------------------------------------------
m3 = _Mitschrift(0.005)
A._thumb_cache_put = m3.put
A._thumb_cache_put_marke = m3.marke
try:
    _leeren()
    A._thumb_cache_put_async(*_bild(1, 8))
    A._thumb_cache_put_marke_async("/art/002.png", 578, 770)
    A._thumb_cache_put_async(*_bild(3, 8))
    A.thumb_schreib_abwarten(10.0)
    time.sleep(0.15)
finally:
    A._thumb_cache_put = _echt_put
    A._thumb_cache_put_marke = _echt_marke

check("die Reihenfolge von Marke und Bild bleibt",
      m3.reihenfolge == ["/art/001.png", ("marke", "/art/002.png"),
                         "/art/003.png"],
      str(m3.reihenfolge))
check("eine Marke zaehlt nicht gegen die Byte-Grenze",
      A._auftrag_bytes(("marke", "/x", 1, 2)) == 0)

# ---------------------------------------------------------------------------
print()
print("Test 4: 'Miniaturen vorbereiten' geht NICHT ueber die Schlange")
# ---------------------------------------------------------------------------
_q = io.open(os.path.join(_REPO, "frontend", "fe", "art.py"),
             encoding="utf-8").read()
# Nur Code, keine Kommentare/Docstrings - sonst springt die Pruefung
# auf der Begruendung an, die genau diesen Punkt erklaert.
_code = []
for _z in _q.split("\n"):
    _s = _z.strip()
    if _s.startswith("#"):
        continue
    _code.append(_z)
_code = "\n".join(_code)
_prewarm = _code.split("def _prewarm_aus_gelesenem")[-1].split("\ndef ")[0]
check("der Vorbereiter schreibt direkt und synchron",
      "_thumb_cache_put(" in _prewarm
      and "_thumb_cache_put_async(" not in _prewarm,
      "dort darf nichts verworfen werden - das ist der Zweck")
check("der Zeichenweg dagegen stellt ein",
      "_schreib_einstellen((\"bild\"" in _code)
check("es gibt genau EINEN Arbeitsfaden",
      _code.count("target=_schreib_arbeiter") == 1)
check("und er wird nur einmal gestartet",
      "if _schreib_faden is None:" in _code)
check("die Groesse wird an EINER Stelle gerechnet",
      _code.count("def _auftrag_bytes") == 1
      and _code.count("_auftrag_bytes(") >= 3,
      "dreimal gebraucht: einstellen, verwerfen, abarbeiten")

# ---------------------------------------------------------------------------
print()
print("Test 5: die Buchfuehrung ist abfragbar")
# ---------------------------------------------------------------------------
stand = A.thumb_schreib_stand()
check("thumb_schreib_stand() liefert vier Zahlen", len(stand) == 4,
      str(stand))
check("die Schlange ist nach den Tests leer", stand[0] == 0, str(stand[0]))
check("und der Byte-Zaehler steht auf null", stand[1] == 0, str(stand[1]))
check("erledigt wurde mitgezaehlt", stand[2] >= 13, str(stand[2]))
check("die Grenze ist eine benannte Zahl",
      isinstance(A.SCHREIB_QUEUE_MAX_BYTES, int)
      and A.SCHREIB_QUEUE_MAX_BYTES >= 8 * 1024 * 1024,
      "%.0f MB" % (A.SCHREIB_QUEUE_MAX_BYTES / 1048576.0))

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
