#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft das Auslagern eines kalten Covers (Build 105).

NUTZER-RUECKMELDUNG, die dahinter steht: "wenn ich beim Scrollen schnell
die Richtung wechsle, haengt es kurz, und beim Ordnerwechsel auch".

Bis Build 104 galt: waehrend des Scrollens werden noch nicht berechnete
Cover uebersprungen, im STILLSTAND werden sie gerechnet. Der Stillstand
ist aber genau der Moment, in dem jemand hinschaut - und eine
Erstberechnung kostet auf HDMI 200-500 ms, in denen die Bedienung steht.

Jetzt wandert diese Rechnung an den Arbeitsprozess auf dem zweiten Kern,
und der Cover-Platz bleibt eine Runde leer, bis die Miniatur da ist.

VIER ZUSAGEN, die alle vier halten muessen - die letzten drei sind die
eigentlich wichtigen, denn sie sagen, was passiert, wenn es NICHT
klappt:

  1. Liegt die Miniatur nicht auf der Karte, wird der Auftrag abgegeben
     und in dieser Runde nichts gezeichnet.
  2. Gibt es gar keine Quelldatei (Spiel ohne Cover - in einer frischen
     Sammlung der Normalfall), wird NICHT ausgelagert. Sonst wartete
     jedes coverlose Spiel zwei Sekunden auf einen Arbeiter, der nichts
     finden kann, statt sofort "kein Artwork" zu zeigen.
  3. Antwortet niemand, rechnet der Zeichen-Thread nach AUSLAGERN_MAX
     doch selbst. Ohne diese Notbremse verschwaende ein haengender
     Arbeitsprozess das Cover fuer immer - und zwar lautlos.
  4. Nur der ZEICHENPFAD darf auslagern. Alle uebrigen Aufrufer
     brauchen ein Ergebnis: das Vorwaermen beim Start wuerde sonst
     stillschweigend nichts waermen. Genau das ist beim ersten Anlauf
     passiert und von tools/test_cover_prewarm.py gefangen worden.

Ausfuehren:
    python3 tools/test_kaltes_cover.py
"""
import os
import struct
import shutil
import sys
import tempfile
import time
import zlib

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_REPO, "frontend"))

import fe.art as A                                      # noqa: E402
import fe.prewarm as P                                  # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


TMP = tempfile.mkdtemp(prefix="kaltes_cover_")
A.THUMB_CACHE_BASE = os.path.join(TMP, "base")
A.THUMB_CACHE_DIR = os.path.join(TMP, "cache")


def art_datei(pfad, w, h):
    pix = bytearray()
    for y in range(h):
        for x in range(w):
            pix += bytes(((x * 3) % 256, (y * 5) % 256,
                          ((x + y) * 7) % 256, 0))
    with open(pfad, "wb") as f:
        f.write(b"ART1" + struct.pack("<HH", w, h)
                + zlib.compress(bytes(pix), 1))


BILD = os.path.join(TMP, "cover.art")
art_datei(BILD, 400, 560)
FEHLT = os.path.join(TMP, "gibt_es_nicht.art")

print("Test 1: kaltes Cover wird abgegeben, nicht gerechnet")
A.ART.cache = {}
A.ART.order = []
A.ART.scaled = {}
A.ART.scaled_order = []
A.ART._warte_start = {}
abgegeben = []
A.ART.auslagern = lambda p, w, h: (abgegeben.append((p, w, h)) or True)
vorher = A.ART._defer_count
r = A.ART.get_scaled(BILD, 200, 280, auslagern_ok=True)
check("liefert nichts zurueck", r is None)
check("der Auftrag wurde abgegeben", abgegeben == [(BILD, 200, 280)],
      "(%r)" % (abgegeben,))
check("als 'verzoegert' gezaehlt", A.ART._defer_count > vorher)
check("und es wird auf ihn gewartet", len(A.ART._warte_start) == 1)

print("Test 2: ohne auslagern_ok wird ganz normal gerechnet")
# Das Vorwaermen beim Start, der Trophaeenraum, der Attract-Modus - alle
# brauchen ein Ergebnis, kein Vielleicht.
A.ART.scaled = {}
A.ART.scaled_order = []
A.ART._warte_start = {}
abgegeben[:] = []
r = A.ART.get_scaled(BILD, 190, 266)
check("liefert ein Bild", r is not None and len(r) == 3)
check("nichts abgegeben", abgegeben == [], "(%r)" % (abgegeben,))

print("Test 3: ohne Quelldatei wird nicht ausgelagert")
A.ART.scaled = {}
A.ART.scaled_order = []
A.ART._warte_start = {}
abgegeben[:] = []
r = A.ART.get_scaled(FEHLT, 200, 280, auslagern_ok=True)
check("liefert nichts (kein Cover vorhanden)", r is None)
check("aber es wurde auch nichts abgegeben", abgegeben == [],
      "(%r)" % (abgegeben,))
check("und es wird auf nichts gewartet", not A.ART._warte_start)

print("Test 4: die Notbremse - antwortet niemand, rechnen wir selbst")
A.ART.scaled = {}
A.ART.scaled_order = []
A.ART._warte_start = {}
abgegeben[:] = []
A.ART.get_scaled(BILD, 210, 294, auslagern_ok=True)
check("erst wird abgegeben", len(abgegeben) == 1)
# Die Wartezeit kuenstlich ueberschreiten, statt zwei Sekunden zu warten.
for k in list(A.ART._warte_start):
    A.ART._warte_start[k] = time.monotonic() - A.ART.AUSLAGERN_MAX - 0.1
r = A.ART.get_scaled(BILD, 210, 294, auslagern_ok=True)
check("danach kommt ein Bild", r is not None and len(r) == 3)
check("der Warte-Eintrag ist weg", not A.ART._warte_start)

print("Test 5: warte_pruefen() meldet nur, wenn es etwas zu tun gibt")
A.ART._warte_start = {}
check("ohne Wartende: nichts zu tun", A.ART.warte_pruefen() is False)
A.ART.scaled = {}
A.ART.scaled_order = []
abgegeben[:] = []
A.ART.get_scaled(BILD, 220, 308, auslagern_ok=True)
check("waehrend gewartet wird: noch nichts", A.ART.warte_pruefen() is False)
# Jetzt die Miniatur tatsaechlich anlegen, wie es der Arbeitsprozess taete.
#
# ERGAENZT (Build 119): das Ergebnis von prewarm_thumb() und der
# Zustand der Warteliste wandern in die Meldung. Diese beiden
# Pruefungen sind in einem Sammellauf der ganzen Suite zweimal
# fehlgeschlagen und liessen sich danach weder einzeln noch unter
# kuenstlicher Last wiederholen - ohne diese Angaben bleibt beim
# naechsten Mal wieder nur Raten. Es kostet nichts: die Zeichenkette
# wird ohnehin nur bei einem Fehlschlag ausgegeben.
_vorbereitet = A.prewarm_thumb(BILD, 220, 308)
_liegt_da = A.thumb_cache_has(BILD, 220, 308)
check("sobald die Miniatur da ist: nachzeichnen",
      A.ART.warte_pruefen() is True,
      "prewarm_thumb=%r, Miniatur auf der Karte=%r, Warteliste=%r"
      % (_vorbereitet, _liegt_da, list(A.ART._warte_start)))
check("und der Warte-Eintrag ist abgeraeumt", not A.ART._warte_start,
      "%r" % (list(A.ART._warte_start),))

print("Test 6: der echte Weg - Arbeitsprozess rechnet, Cover kommt an")
# Kein Nachbau der Abgabe mehr, sondern PREWARMER.dringend() selbst.
A.THUMB_CACHE_DIR = os.path.join(TMP, "cache_echt")
A.ART.scaled = {}
A.ART.scaled_order = []
A.ART.cache = {}
A.ART.order = []
A.ART._warte_start = {}
pw = P.CoverPrewarmer()
pw.start()
if pw.betriebsart() != "prozess":
    print("       (kein Arbeitsprozess moeglich - Test uebersprungen)")
else:
    A.ART.auslagern = pw.dringend
    r = A.ART.get_scaled(BILD, 230, 322, auslagern_ok=True)
    check("Zeichenpfad bekommt erst einmal nichts", r is None)
    ende = time.monotonic() + 20.0
    while time.monotonic() < ende and not A.thumb_cache_has(BILD, 230, 322):
        time.sleep(0.05)
    check("der Arbeitsprozess liefert die Miniatur",
          A.thumb_cache_has(BILD, 230, 322))
    check("warte_pruefen() meldet das Nachzeichnen",
          A.ART.warte_pruefen() is True)
    r = A.ART.get_scaled(BILD, 230, 322, auslagern_ok=True)
    check("und der naechste Aufruf hat das Bild",
          r is not None and len(r) == 3)
pw.beenden()

print("Test 7: ohne Arbeitsprozess bleibt alles beim Alten")
# Die ehrliche Untergrenze: im Thread-Betrieb lehnt dringend() ab, denn
# ohne zweiten Kern nimmt das Rechnen dem Zeichnen dieselbe Zeit weg -
# nur eben spaeter und mit einem leeren Cover-Platz dazwischen.
A.THUMB_CACHE_DIR = os.path.join(TMP, "cache_thread")
A.ART.scaled = {}
A.ART.scaled_order = []
A.ART.cache = {}
A.ART.order = []
A.ART._warte_start = {}
echter_worker = P.WORKER
P.WORKER = os.path.join(TMP, "gibt_es_nicht.py")
pw2 = P.CoverPrewarmer()
pw2.start()
check("Betriebsart ist 'thread'", pw2.betriebsart() == "thread")
check("dringend() lehnt ab", pw2.dringend(BILD, 240, 336) is False)
A.ART.auslagern = pw2.dringend
r = A.ART.get_scaled(BILD, 240, 336, auslagern_ok=True)
check("der Zeichenpfad rechnet also selbst",
      r is not None and len(r) == 3)
pw2.beenden()
P.WORKER = echter_worker

print("Test 8: das Frontend zeichnet nach, solange gewartet wird")
quelle = open(os.path.join(_REPO, "frontend", "frontend.py"),
              encoding="utf-8", errors="replace").read()
check("der Nachlade-Takt ruft warte_pruefen()",
      "ART.warte_pruefen()" in quelle)
check("und setzt den Einmal-Schalter zurueck",
      "self._settled_redrawn = False" in quelle)
check("die Verbindung zum Vorauslader steht",
      "ART.auslagern = PREWARMER.dringend" in quelle)
check("nur der Cover-Zeichenpfad lagert aus",
      quelle.count("auslagern_ok=True") == 2,
      "(%d Fundstellen)" % quelle.count("auslagern_ok=True"))

shutil.rmtree(TMP, ignore_errors=True)

print()
if fails:
    print("FEHLGESCHLAGEN (%d):" % len(fails))
    for f_ in fails:
        print("  -", f_)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
