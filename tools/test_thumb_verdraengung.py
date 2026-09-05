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
A.THUMB_CACHE_BASE = os.path.join(TMP, "thumb_cache")
A.THUMB_CACHE_DIR = os.path.join(A.THUMB_CACHE_BASE, "hd")
os.makedirs(A.THUMB_CACHE_DIR, exist_ok=True)
QUELLE = os.path.join(TMP, "quelle")
os.makedirs(QUELLE, exist_ok=True)


def cache_datei(name, alter_sekunden=0.0):
    """Eine Datei im Cache anlegen, mit gewaehltem Alter - inklusive der
    Zwischenebene aus zwei Zeichen (siehe _thumb_cache_path)."""
    fp = os.path.join(A.THUMB_CACHE_DIR, name[:2], name + ".art")
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    with open(fp, "wb") as f:
        f.write(b"ART1" + b"\0" * 8)
    if alter_sekunden:
        t = time.time() - alter_sekunden
        os.utime(fp, (t, t))
    return fp


def zaehlen():
    n = 0
    for _d, _s, dateien in os.walk(A.THUMB_CACHE_DIR):
        n += len([f for f in dateien if f.endswith(".art")])
    return n


def zuruecksetzen(anzahl, grenze):
    shutil.rmtree(A.THUMB_CACHE_DIR, ignore_errors=True)
    os.makedirs(A.THUMB_CACHE_DIR, exist_ok=True)
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
    ordner = os.path.join(A.THUMB_CACHE_DIR, "re")
    os.makedirs(ordner, exist_ok=True)
    with open(os.path.join(ordner, "rest%d.art.tmp1234_5678" % i), "wb") as f:
        f.write(b"kaputt")
A._thumb_cache_evict_if_needed()
reste = [f for _d, _s, dateien in os.walk(A.THUMB_CACHE_DIR)
         for f in dateien if ".art.tmp" in f]
check("keine .tmp-Reste mehr im Ordner", not reste,
      "%d uebrig" % len(reste))

print()
print("Test 7: getrennte Zwischenspeicher fuer CRT und HDMI")
# Nutzerwunsch: "bitte fuer jeden Modus, also CRT und HDMI, einen
# eigenen Cache anlegen - quasi einmal SD-Variante fuer CRT-Modus und
# einmal HD-Variante fuer HDMI-Modus."
A.THUMB_CACHE_BASE = os.path.join(TMP, "modi")
hd = A.thumb_cache_modus_setzen(True)
check("HD-Modus landet in hd/", hd.endswith(os.sep + "hd"), hd)
sd = A.thumb_cache_modus_setzen(False)
check("SD-Modus landet in sd/", sd.endswith(os.sep + "sd"), sd)
check("die beiden Ordner sind verschieden", hd != sd)
# Und der mitgefuehrte Zaehler darf beim Wechsel NICHT stehenbleiben -
# sonst wuerde im neuen Ordner sofort falsch verdraengt.
A._thumb_cache_anzahl = 12345
A.thumb_cache_modus_setzen(True)
check("der Zaehler wird beim Moduswechsel verworfen",
      A._thumb_cache_anzahl is None, str(A._thumb_cache_anzahl))

print()
print("Test 8: derselbe Schluessel liegt je Modus an anderer Stelle")
A.thumb_cache_modus_setzen(True)
p_hd = A._thumb_cache_path("abcdef0123")
A.thumb_cache_modus_setzen(False)
p_sd = A._thumb_cache_path("abcdef0123")
check("HD- und SD-Pfad unterscheiden sich", p_hd != p_sd)
check("Zwischenebene aus zwei Zeichen vorhanden",
      os.path.basename(os.path.dirname(p_hd)) == "ab",
      os.path.dirname(p_hd))
# Der Sinn der Zwischenebene: /media/fat ist ueblicherweise exFAT, dort
# ist das Nachschlagen in einem Verzeichnis linear. 40000 Dateien in
# EINEM Ordner waeren doppelt so teuer wie die bisherigen 20000.
# ECHTE Schluessel benutzen, keine ausgedachten: _thumb_cache_key()
# liefert sha1-Hex, und nur dessen Gleichverteilung sorgt fuer die
# gleichmaessige Streuung ueber die 256 Unterordner. Ein Test mit
# hochgezaehlten Zahlen haette hier nichts bewiesen - die faengen alle
# mit denselben Zeichen an.
schluessel = [A._thumb_cache_key("/spiele/spiel%d.art" % i, 300, 400)
              for i in range(2000)]
ordner = {os.path.dirname(A._thumb_cache_path(k)) for k in schluessel}
check("2000 Schluessel verteilen sich auf viele Unterordner",
      len(ordner) >= 200, "%d Ordner" % len(ordner))

print()
print("Test 9: die alte, flache Ablage wird aufgeraeumt")
# Nach der Umstellung liegen die alten Dateien am falschen Ort und
# werden nie wieder gefunden - bei einer grossen Sammlung mehrere
# Gigabyte, die sonst fuer immer liegen blieben.
A.THUMB_CACHE_BASE = os.path.join(TMP, "alt")
os.makedirs(os.path.join(A.THUMB_CACHE_BASE, "hd", "ab"), exist_ok=True)
for i in range(12):
    open(os.path.join(A.THUMB_CACHE_BASE, "alt%02d.art" % i), "wb").close()
open(os.path.join(A.THUMB_CACHE_BASE, "rest.art.tmp1_2"), "wb").close()
neu_datei = os.path.join(A.THUMB_CACHE_BASE, "hd", "ab", "abcd.art")
open(neu_datei, "wb").close()
entfernt = A.alten_flachen_cache_aufraeumen()
check("die 13 losen Altdateien sind weg", entfernt == 13, "%d entfernt" % entfernt)
check("die neue Ablage bleibt unangetastet", os.path.exists(neu_datei))

print()
print("Test 10: die Obergrenze ist auf 40000 angehoben")
import importlib
A2 = importlib.reload(A)
check("THUMB_CACHE_MAX_FILES = 40000", A2.THUMB_CACHE_MAX_FILES == 40000,
      str(A2.THUMB_CACHE_MAX_FILES))
check("thumb_cache_stand() liefert auch die Belegung",
      len(A2.thumb_cache_stand()) == 3, str(A2.thumb_cache_stand()))

shutil.rmtree(TMP, ignore_errors=True)

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for f_ in fails:
        print("  -", f_)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
