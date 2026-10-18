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
        # Build 293: der Index gehoert mit zurueckgesetzt. Bliebe er
        # stehen, wuerde ein spaeterer gleichlautender Auftrag auf
        # einen Eintrag zeigen, der nicht mehr in der Liste steht -
        # abgefangen ist das im Quelltext, aber ein Testaufbau soll
        # keinen Zustand hinterlassen, den der naechste Test erst
        # aushalten muss.
        A._schreib_index.clear()


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
# UMGEDREHT IN BUILD 293, und das ist eine Verhaltensaenderung mit
# Grund, keine Abschwaechung. Hier stand:
#
#     check("und zwar in der Reihenfolge, in der sie kamen",
#           m.reihenfolge == ["/art/%03d.png" % i for i in range(10)])
#
# Build 247 hat die Grenze mit dem Satz gebaut, "was gerade auf dem
# Schirm war, ist wahrscheinlicher gleich wieder gebraucht als etwas
# von vor zwanzig Schritten" - und diesen Gedanken nur beim VERWERFEN
# angewandt. Abgearbeitet wurde weiter von vorn, also der aelteste
# zuerst. Beim Schnellscrollen packte der Faden damit mit Hunderten
# von Millisekunden ausgerechnet das Cover, das am wenigsten
# wahrscheinlich noch gebraucht wird, waehrend das vom letzten
# Schritt hinten wartete und selbst wieder hinausfiel.
#
# Im Bench des Nutzers (Build 292) sah das so aus:
#   Spieleliste galerie: 58 wartend (19.0 MB), 291 erledigt, 87 verworfen
#
# Jetzt nimmt der Faden den NEUESTEN. Die Zusage dieses Tests ist
# damit nicht "Ankunftsreihenfolge", sondern "Nuetzlichkeits-
# reihenfolge" - und die ist genauso pruefbar.
#
# HIER WIRD NUR NOCH GEPRUEFT, DASS ES NICHT DIE ANKUNFTSREIHENFOLGE
# IST - und das hat einen Grund, der selbst eine Lehre ist: in diesem
# Test laeuft der Faden MIT, waehrend eingestellt wird. Er nimmt den
# ersten Auftrag, sobald einer da ist, und was dann als Naechstes
# obenliegt, haengt davon ab, wie viele in der Zwischenzeit
# dazugekommen sind. Das ist ein Rennen, und eine exakte
# Reihenfolge daran festzuschreiben waere ein Test, der manchmal
# gruen ist. (Genau das ist mir beim Schreiben dieses Builds
# passiert: "genau umgekehrt" ging rot, und zwar zu Recht.)
#
# Die exakte Reihenfolge prueft deshalb Test 1b weiter unten, mit
# festgehaltenem Faden - dieselbe Technik, mit der Test 2 die
# Byte-Grenze prueft.
check("und NICHT in der Reihenfolge, in der sie kamen",
      m.reihenfolge != ["/art/%03d.png" % i for i in range(10)],
      str(m.reihenfolge))
# Und die Gegenprobe zur Befuerchtung, die dabei naheliegt: der
# aelteste verhungert NICHT. Hoert das Scrollen auf, kommt nichts
# mehr dazu, und die Schlange laeuft komplett leer.
check("niemand verhungert - es sind trotzdem alle zehn",
      sorted(m.reihenfolge) == sorted("/art/%03d.png" % i
                                      for i in range(10)))

# ---------------------------------------------------------------------------
print()
print("Test 1b: der NEUESTE ist zuerst dran - mit festgehaltenem Faden")
# ---------------------------------------------------------------------------
# Kein Rennen: der erste Auftrag haelt den Faden zwei Sekunden fest,
# in der Zeit werden fuenf weitere eingestellt, und erst danach darf
# er weiterarbeiten. Was dann herauskommt, ist die ECHTE Reihenfolge
# der Schlange und haengt an keiner Uhr.
m1b = _Mitschrift(0.0)
_halt = threading.Event()


def _put_mit_halt(path, w, h, tw, th, pix):
    if path == "/art/900.png":
        _halt.wait(5.0)      # der Haltegriff, nicht die Messung
    m1b.put(path, w, h, tw, th, pix)


A._thumb_cache_put = _put_mit_halt
A._thumb_cache_put_marke = m1b.marke
try:
    _leeren()
    A._thumb_cache_put_async("/art/900.png", 578, 770, 578, 770,
                             b"\x00" * 1024)
    time.sleep(0.2)          # dem Faden Zeit, den Haltegriff zu nehmen
    for i in range(1, 6):
        A._thumb_cache_put_async(*_bild(i, 16))
    with A._schreib_lock:
        wartend = [a[1] for a in A._schreib_queue]
    _halt.set()
    A.thumb_schreib_abwarten(20.0)
    time.sleep(0.3)
finally:
    _halt.set()
    A._thumb_cache_put = _echt_put
    A._thumb_cache_put_marke = _echt_marke

check("alle fuenf standen wirklich gleichzeitig in der Schlange",
      wartend == ["/art/%03d.png" % i for i in range(1, 6)],
      str(wartend))
check("abgearbeitet wird von hinten - der NEUESTE zuerst",
      m1b.reihenfolge[1:] == ["/art/%03d.png" % i
                              for i in range(5, 0, -1)],
      str(m1b.reihenfolge))
check("und der Haltegriff war der erste, wie bestellt",
      m1b.reihenfolge[:1] == ["/art/900.png"], str(m1b.reihenfolge[:1]))

# ---------------------------------------------------------------------------
print()
print("Test 1c: derselbe Auftrag zweimal wird EINMAL gepackt")
# ---------------------------------------------------------------------------
# Wer hin- und herscrollt, sieht dasselbe Cover zweimal. Bei 833 ms je
# Packvorgang (Abschnitt C des Benchs) ist doppeltes Packen keine
# Kleinigkeit.
m1c = _Mitschrift(0.0)
_halt2 = threading.Event()


def _put_mit_halt2(path, w, h, tw, th, pix):
    if path == "/art/900.png":
        _halt2.wait(5.0)
    m1c.put(path, w, h, tw, th, pix)


A._thumb_cache_put = _put_mit_halt2
A._thumb_cache_put_marke = m1c.marke
try:
    _leeren()
    with A._schreib_lock:
        A._schreib_index.clear()
        A._schreib_doppelt = 0
    A._thumb_cache_put_async("/art/900.png", 578, 770, 578, 770,
                             b"\x00" * 1024)
    time.sleep(0.2)
    A._thumb_cache_put_async(*_bild(7, 16))
    A._thumb_cache_put_async(*_bild(8, 16))
    A._thumb_cache_put_async(*_bild(7, 16))    # derselbe noch einmal
    with A._schreib_lock:
        drin1c = [a[1] for a in A._schreib_queue]
        doppelt = A._schreib_doppelt
    _halt2.set()
    A.thumb_schreib_abwarten(20.0)
    time.sleep(0.3)
finally:
    _halt2.set()
    A._thumb_cache_put = _echt_put
    A._thumb_cache_put_marke = _echt_marke

check("der doppelte steht nur EINMAL in der Schlange",
      drin1c.count("/art/007.png") == 1, str(drin1c))
check("und zwar an der NEUEN Stelle, hinten",
      drin1c == ["/art/008.png", "/art/007.png"], str(drin1c))
check("das Zusammenfassen wird gezaehlt", doppelt == 1, str(doppelt))
check("gepackt wurde er auch nur einmal",
      m1c.reihenfolge.count("/art/007.png") == 1, str(m1c.reihenfolge))
check("und die Zahl ist abfragbar, getrennt von 'verworfen'",
      isinstance(A.thumb_schreib_zusatz(), tuple)
      and len(A.thumb_schreib_zusatz()) >= 1,
      str(A.thumb_schreib_zusatz()))

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

# EBENFALLS UMGEDREHT IN BUILD 293 (siehe Test 1). Die Zusage dieses
# Tests war und bleibt: Marken und Bilder liegen in EINER Schlange und
# werden von EINEM Faden abgearbeitet, ohne sich zu ueberholen. Dass
# die Reihenfolge jetzt die umgekehrte ist, aendert daran nichts - und
# gerade weil hier beide Arten gemischt sind, ist dies die Stelle, an
# der auffiele, wenn eine Art anders behandelt wuerde als die andere.
check("Marke und Bild in EINER Schlange, neueste zuerst",
      m3.reihenfolge == ["/art/003.png", ("marke", "/art/002.png"),
                         "/art/001.png"],
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
