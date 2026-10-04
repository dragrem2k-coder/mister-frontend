#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DIAGNOSE (kein Pass/Fail): die Schreib-Warteschlange fuer Miniaturen.

DER BEFUND, auf den sie antwortet, steht im Bench vom 04.10. auf dem
DE10-Nano (Abschnitt B, neu seit Build 245):

    Spieleliste liste    je Schritt kalt      294.61 ms
       davon dekodieren 94.4, verkleinern 43.3, Rest 156.9 ms
       DANEBEN (eigene Threads, nicht im Schritt enthalten):
         Miniaturen packen und schreiben 590.1 ms (44 x) - auf zwei Kernen

590 ms Hintergrundarbeit je Schritt bei einem Schritt von 294 ms. Ueber
60 Schritte: 35 Sekunden Packen und Schreiben in knapp 18 Sekunden
Messzeit - auf einem Geraet mit ZWEI Kernen. Beide Kerne waren also
durchgehend belegt, waehrend daneben gezeichnet wurde.

Was dieses Skript zeigt, und zwar in Zahlen, die auf JEDEM Rechner
gelten (nicht in Millisekunden, die nur fuer diesen hier stimmen):

  1. wie viele Schreibvorgaenge GLEICHZEITIG laufen - vorher so viele
     wie Cover, jetzt genau einer
  2. dass kein Auftrag verlorengeht, solange die Schlange reicht
  3. dass die Grenze greift und der AELTESTE herausfaellt
  4. was das Einstellen den Zeichenweg kostet

Ausfuehren:
    python3 tools/diag_schreibschlange.py
"""
import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H          # noqa: E402

import fe.art as ART          # noqa: E402

_uhr = time.perf_counter


def _balken(titel):
    print()
    print("=" * 70)
    print(" " + titel)
    print("=" * 70)


def _mb(n):
    return n / 1048576.0


# ---------------------------------------------------------------------
# Haken: _thumb_cache_put() durch einen langsamen Platzhalter ersetzen,
# der mitzaehlt, wie viele Aufrufe GLEICHZEITIG laufen. Genau diese
# Zahl ist der Unterschied zwischen vorher und jetzt - und sie haengt
# an keiner Uhr.
# ---------------------------------------------------------------------
class _Zaehler(object):
    def __init__(self, dauer=0.05):
        self.dauer = dauer
        self.lock = threading.Lock()
        self.jetzt = 0
        self.hoechstens = 0
        self.erledigt = []
        self.marken = []

    def put(self, path, w, h, tw, th, pix):
        with self.lock:
            self.jetzt += 1
            self.hoechstens = max(self.hoechstens, self.jetzt)
        time.sleep(self.dauer)       # steht fuer zlib + SD-Schreiben
        with self.lock:
            self.jetzt -= 1
            self.erledigt.append(path)

    def marke(self, path, w, h):
        with self.lock:
            self.marken.append(path)


def _mit_haken(dauer=0.05):
    z = _Zaehler(dauer)
    ART._thumb_cache_put = z.put
    ART._thumb_cache_put_marke = z.marke
    return z


_echt_put = ART._thumb_cache_put
_echt_marke = ART._thumb_cache_put_marke


def _bild(nr, kb=64):
    return ("/art/%03d.png" % nr, 578, 770, 578, 770,
            b"\x00" * (kb * 1024))


def main():
    _balken("Die Schreib-Warteschlange - 1920x1080, Cover der Listenspalte")
    print(" Grenze der Schlange: %.0f MB" % _mb(ART.SCHREIB_QUEUE_MAX_BYTES))

    # --- 1) Wie viele Schreibvorgaenge laufen gleichzeitig? ----------
    z = _mit_haken(0.05)
    try:
        vor = ART.thumb_schreib_stand()
        t0 = _uhr()
        for i in range(12):
            ART._thumb_cache_put_async(*_bild(i, 64))
        einstell_ms = (_uhr() - t0) * 1000.0 / 12.0
        ART.thumb_schreib_abwarten(20.0)
        time.sleep(0.2)
        nach = ART.thumb_schreib_stand()
    finally:
        ART._thumb_cache_put = _echt_put
        ART._thumb_cache_put_marke = _echt_marke

    print()
    print(" 1) GLEICHZEITIGE SCHREIBVORGAENGE  (12 Cover, je 50 ms)")
    print("    hoechstens gleichzeitig : %d" % z.hoechstens)
    print("    erledigt                : %d von 12" % len(z.erledigt))
    print("    verworfen               : %d"
          % (nach[3] - vor[3]))
    print("    Reihenfolge eingehalten : %s"
          % ("ja" if z.erledigt == ["/art/%03d.png" % i
                                    for i in range(12)] else "NEIN"))
    print()
    print("    Zu lesen als: VORHER war diese Zahl so hoch wie die Zahl")
    print("    der Cover - ein Thread je Aufruf. Auf einem Geraet mit")
    print("    zwei Kernen heisst das: beide Kerne packen, und das")
    print("    Zeichnen bekommt den Rest. JETZT ist sie 1.")

    # --- 2) Was kostet das Einstellen den Zeichenweg? ---------------
    print()
    print(" 2) WAS DER ZEICHENWEG BEZAHLT")
    print("    Einstellen je Auftrag   : %.4f ms" % einstell_ms)
    print("    (vorher: ein Thread-Start je Auftrag - teurer, und auf")
    print("     diesem Rechner trotzdem beides unter einer Millisekunde.")
    print("     Die Zahl, auf die es ankommt, steht unter 1.)")

    # --- 3) Greift die Grenze, und faellt der AELTESTE heraus? ------
    # Der Arbeitsfaden wird kuenstlich blockiert, damit sich die
    # Schlange ueberhaupt fuellen kann.
    z2 = _mit_haken(1.5)
    try:
        vor2 = ART.thumb_schreib_stand()
        # Ein Auftrag blockiert den Arbeitsfaden, danach wird die
        # Schlange gezielt ueberfuellt: 24 MB Grenze, 2 MB je Bild.
        ART._thumb_cache_put_async(*_bild(900, 2048))
        time.sleep(0.1)
        for i in range(20):
            ART._thumb_cache_put_async(*_bild(i, 2048))
        stand = ART.thumb_schreib_stand()
        print()
        print(" 3) DIE GRENZE  (20 Cover a 2 MB gegen eine Grenze von %.0f MB)"
              % _mb(ART.SCHREIB_QUEUE_MAX_BYTES))
        print("    wartende Auftraege      : %d" % stand[0])
        print("    wartende Bytes          : %.1f MB" % _mb(stand[1]))
        print("    verworfen               : %d" % (stand[3] - vor2[3]))
        print("    ueber der Grenze?       : %s"
              % ("JA - Fehler" if stand[1] > ART.SCHREIB_QUEUE_MAX_BYTES
                 else "nein"))
        # Welche sind noch drin? Es muessen die JUENGSTEN sein.
        with ART._schreib_lock:
            drin = [a[1] for a in ART._schreib_queue]
        if drin:
            print("    aeltester noch wartend  : %s" % drin[0])
            print("    juengster noch wartend  : %s" % drin[-1])
            print("    (herausfallen muss der AELTESTE - was gerade auf")
            print("     dem Schirm war, ist wahrscheinlicher gleich")
            print("     wieder gebraucht)")
        with ART._schreib_lock:
            del ART._schreib_queue[:]
            ART._schreib_bytes = 0
    finally:
        ART._thumb_cache_put = _echt_put
        ART._thumb_cache_put_marke = _echt_marke
        time.sleep(1.6)      # den blockierenden Auftrag auslaufen lassen

    # --- 4) Marken und Bilder in EINER Reihenfolge ------------------
    z3 = _mit_haken(0.01)
    try:
        ART._thumb_cache_put_async(*_bild(1, 16))
        ART._thumb_cache_put_marke_async("/art/002.png", 578, 770)
        ART._thumb_cache_put_async(*_bild(3, 16))
        ART.thumb_schreib_abwarten(10.0)
        time.sleep(0.1)
        print()
        print(" 4) MARKEN UND BILDER IN EINER SCHLANGE")
        print("    Bilder geschrieben      : %s" % z3.erledigt)
        print("    Marken geschrieben      : %s" % z3.marken)
        print("    (zwei getrennte Wege haetten die Reihenfolge von")
        print("     Marke und Bild desselben Covers nicht garantiert)")
    finally:
        ART._thumb_cache_put = _echt_put
        ART._thumb_cache_put_marke = _echt_marke

    print()
    print("=" * 70)
    print(" Zu lesen als: die uebertragbare Zahl ist 1 unter Punkt 1.")
    print(" Alles andere haengt an diesem Rechner. Was das auf dem")
    print(" Geraet bringt, sagt Abschnitt B des Bench: dort stand")
    print(" 'Miniaturen packen und schreiben 590,1 ms (44 x)' bei")
    print(" einem Schritt von 294 ms.")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
