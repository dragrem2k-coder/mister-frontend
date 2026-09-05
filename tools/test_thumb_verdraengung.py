#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft die Verdraengung im Miniaturen-Zwischenspeicher (Build 84).

AUSLOESER (Nutzer-Rueckmeldung mit Log vom Geraet): nach einem
Miniaturen-Durchlauf kostete jede Kategorie im Hauptmenue 1.4 bis 3.7
Sekunden - obwohl dieselben Logos Sekunden vorher noch Treffer waren:

    01:00:16  THUMB_CACHE Treffer: 6.3ms (ATARI2600.art, 304x792)
    12:48:33  PERF cover: 1732 ms (ATARI2600.art)

DER ENTSCHEIDENDE HINWEIS KAM VOM NUTZER SELBST: "wenn das an der Uhr
liegt, die aktualisiert sich ja immer erst nach ein paar Sekunden. Ich
starte das Frontend, dann steht da 1.00, dann nach ein paar Sekunden
springt sie auf die tatsaechliche Uhrzeit."

Die beiden Zeilen liegen also nicht zwoelf Stunden auseinander, sondern
Sekunden - der MiSTer hat keine gepufferte Uhr, und NTP stellt sie kurz
nach dem Start.

DER FEHLER: die Verdraengung benutzt die Aenderungszeit der Cache-Datei
als "zuletzt benutzt"-Marke, und ein Treffer setzte sie per os.utime auf
die AKTUELLE Systemzeit. Beim Start ist das 01:00. Springt die Uhr
danach auf 12:48, liegen ausgerechnet die eben gelesenen Dateien zwoelf
Stunden in der Vergangenheit - sie sind schlagartig die aeltesten im
ganzen Zwischenspeicher und fliegen als Erste raus.

Die Logos wurden also weggeworfen, WEIL sie gerade benutzt wurden.

Ausfuehren:
    python3 tools/test_thumb_verdraengung.py
"""
import os
import shutil
import sys
import tempfile
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_REPO, "frontend"))

import fe.art as A                                    # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


TMP = tempfile.mkdtemp(prefix="verdraengung_")
A.THUMB_CACHE_DIR = os.path.join(TMP, "thumb_cache")
os.makedirs(A.THUMB_CACHE_DIR, exist_ok=True)
QUELLE = os.path.join(TMP, "quelle")
os.makedirs(QUELLE, exist_ok=True)


def cache_datei(name, alter_sekunden=0.0):
    """Eine Datei direkt im Cache-Ordner anlegen, mit gewaehltem Alter."""
    fp = os.path.join(A.THUMB_CACHE_DIR, name + ".art")
    with open(fp, "wb") as f:
        f.write(b"ART1" + b"\0" * 8)
    if alter_sekunden:
        t = time.time() - alter_sekunden
        os.utime(fp, (t, t))
    return fp


def zaehlen():
    return len([f for f in os.listdir(A.THUMB_CACHE_DIR)
                if f.endswith(".art")])


def zuruecksetzen(anzahl, grenze):
    for f in os.listdir(A.THUMB_CACHE_DIR):
        os.remove(os.path.join(A.THUMB_CACHE_DIR, f))
    A.THUMB_CACHE_MAX_FILES = grenze
    A._thumb_cache_anzahl = None
    A._thumb_cache_seit_zaehlung = 0
    A._geschuetzte_cache_dateien = set()
    A._uhr_verlaesslich = False
    A._vor_uhrstellung_beruehrt = []
    # Aelteste zuerst, damit die Reihenfolge eindeutig ist
    return [cache_datei("d%05d" % i, alter_sekunden=(anzahl - i) * 10)
            for i in range(anzahl)]


print("Test 1: die Verdraengung raeumt auf Vorrat statt Eintrag fuer "
      "Eintrag")
# Frueher wurde exakt auf die Obergrenze heruntergeraeumt: bei vollem
# Cache genau EIN Eintrag je Schreibvorgang - und dafuer jedes Mal der
# volle Verzeichnisdurchgang mit einem getmtime JE DATEI. Aus den
# Messungen des Nutzers herausgerechnet: 1030 ms Grundkosten pro
# Fehltreffer, unabhaengig von der Bildgroesse.
zuruecksetzen(105, grenze=100)
A._thumb_cache_evict_if_needed()
nach = zaehlen()
check("raeumt deutlich unter die Obergrenze", nach <= 92,
      "%d Dateien uebrig (Grenze 100)" % nach)
check("wirft aber nicht zu viel weg", nach >= 85, "%d uebrig" % nach)

print()
print("Test 2: danach laeuft der teure Durchgang lange nicht mehr")
# Genau das ist der Gewinn: nach dem Aufraeumen liegt der Zaehler unter
# der Grenze, der billige Weg greift wieder.
durchgaenge = []
echt = os.listdir


def gezaehlt(pfad):
    if pfad == A.THUMB_CACHE_DIR:
        durchgaenge.append(1)
    return echt(pfad)


os.listdir = gezaehlt
try:
    for i in range(50):
        cache_datei("neu%05d" % i)
        A._thumb_cache_evict_if_needed()
finally:
    os.listdir = echt
# Der teure Durchgang darf hoechstens einmal je "Luft bis zur Grenze"
# laufen. Hier sind das 10 Schreibvorgaenge (Grenze 100, Zielfuellung
# 90) - auf dem Geraet mit 20000 Dateien entsprechend alle 2000.
luft = A.THUMB_CACHE_MAX_FILES - int(A.THUMB_CACHE_MAX_FILES * 0.9)
erlaubt = 50 // luft + 1
check("Verzeichnisdurchgang hoechstens 1x je %d Schreibvorgaenge" % luft,
      len(durchgaenge) <= erlaubt,
      "%d Durchgaenge bei 50 Schreibvorgaengen (erlaubt %d)"
      % (len(durchgaenge), erlaubt))
# Zum Vergleich, was frueher passiert waere: bei vollem Cache lief er
# bei JEDEM Schreibvorgang, also 50 Mal - jeder mit einem getmtime je
# Datei. Genau das waren die 1030 ms Grundkosten im Log des Nutzers.
check("das sind deutlich weniger als die frueheren 50",
      len(durchgaenge) * 5 <= 50, "%d statt 50" % len(durchgaenge))

print()
print("Test 3: geschuetzte Eintraege werden nie verdraengt")
dateien = zuruecksetzen(105, grenze=100)
# Die zehn AELTESTEN schuetzen - genau die, die sonst als Erste
# rausfliegen wuerden.
geschuetzt = dateien[:10]
A._geschuetzte_cache_dateien = set(geschuetzt)
A._thumb_cache_evict_if_needed()
fehlend = [f for f in geschuetzt if not os.path.exists(f)]
check("alle 10 geschuetzten Dateien sind noch da", not fehlend,
      "%d fehlen" % len(fehlend))
check("trotzdem wurde aufgeraeumt", zaehlen() <= 95,
      "%d Dateien uebrig" % zaehlen())

print()
print("Test 4: der Uhrensprung - der eigentliche Fehler")
# Nachgestellt: Frontend startet mit falscher Uhr, liest eine Datei aus
# dem Cache, danach springt die Uhr um zwoelf Stunden nach vorn.
zuruecksetzen(0, grenze=100)
A._uhr_verlaesslich = False
gelesen = cache_datei("beim_start_gelesen", alter_sekunden=60)
vorher = os.path.getmtime(gelesen)
A._benutzt_vermerken(gelesen)          # das macht ein Cache-Treffer
check("vor dem Uhrstellen wird die Marke NICHT angefasst",
      abs(os.path.getmtime(gelesen) - vorher) < 0.001,
      "Marke um %.1f s verschoben"
      % abs(os.path.getmtime(gelesen) - vorher))
check("die Datei ist aber vorgemerkt",
      gelesen in A._vor_uhrstellung_beruehrt)

A.uhr_ist_gestellt()                   # NTP meldet: Uhr steht jetzt
check("nach dem Uhrstellen ist die Marke nachgeholt",
      os.path.getmtime(gelesen) > vorher + 30,
      "%.0f s juenger" % (os.path.getmtime(gelesen) - vorher))
check("die Vormerkliste ist danach leer",
      not A._vor_uhrstellung_beruehrt)

# Und ab jetzt ganz normal sofort
zweite = cache_datei("spaeter_gelesen", alter_sekunden=60)
vorher2 = os.path.getmtime(zweite)
A._benutzt_vermerken(zweite)
check("bei stehender Uhr wird sofort gestempelt",
      os.path.getmtime(zweite) > vorher2 + 30)

print()
print("Test 5: die Vormerkliste kann nicht unbegrenzt wachsen")
# Falls die Uhr NIE gestellt wird (kein Netzwerk), darf sich hier
# nichts aufstauen.
A._uhr_verlaesslich = False
A._vor_uhrstellung_beruehrt = []
for i in range(A._VOR_UHRSTELLUNG_MAX + 200):
    A._benutzt_vermerken(os.path.join(A.THUMB_CACHE_DIR, "x%d.art" % i))
check("Vormerkliste bleibt gedeckelt",
      len(A._vor_uhrstellung_beruehrt) <= A._VOR_UHRSTELLUNG_MAX,
      "%d Eintraege" % len(A._vor_uhrstellung_beruehrt))

print()
print("Test 6: liegengebliebene Zwischendateien werden aufgeraeumt")
# Beim Nutzer standen 20008 Dateien im Ordner bei einer Obergrenze von
# 20000 - die acht ueberzaehligen sind abgebrochene Schreibvorgaenge.
zuruecksetzen(105, grenze=100)
for i in range(8):
    with open(os.path.join(A.THUMB_CACHE_DIR,
                           "rest%d.art.tmp1234_5678" % i), "wb") as f:
        f.write(b"kaputt")
A._thumb_cache_evict_if_needed()
reste = [f for f in os.listdir(A.THUMB_CACHE_DIR) if ".art.tmp" in f]
check("keine .tmp-Reste mehr im Ordner", not reste,
      "%d uebrig" % len(reste))

shutil.rmtree(TMP, ignore_errors=True)

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for f_ in fails:
        print("  -", f_)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
