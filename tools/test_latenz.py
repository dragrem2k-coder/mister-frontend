#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Eingabe → fertiges Bild: die Zahl, die bisher fehlte (Build 192).

WORUM ES GEHT

Es gab zwei Messungen: wie lange ein Zeichenvorgang dauert (PERF) und
wie lange Verarbeitung plus Zeichnen zusammen brauchen (RUCKLER). Beide
sagen nichts darueber, was der Nutzer spuert:

    Taste gedrueckt  ->  Bild steht

Ohne diese Zahl laesst sich ueber "fuehlt sich traege an" nur reden,
nicht entscheiden. Und vor allem: ohne sie laesst sich nicht belegen,
ob eine Aenderung etwas gebracht hat.

BEI EINER GEHALTENEN TASTE zaehlt nicht der Augenblick der
Wiederholung, sondern ihr FAELLIGKEITStermin. Der Nutzer drueckt dort
nicht neu, er haelt - was er spuert, ist der Abstand zwischen zwei
Schritten auf dem Schirm. Mit "jetzt" als Startpunkt waere die
gemessene Latenz per Bauart immer nahe null, egal wie spaet der Schritt
kommt.

WAS DIESER TEST ABSICHERT

  - dass Unsinn nicht in die Statistik geraet (Uhrensprung, ein Spiel
    lief dazwischen, gar keine Eingabe),
  - dass eine Bilanz auch dann kommt, wenn nichts auffaellig war -
    genau daran ist Build 182 gescheitert,
  - dass die erste Bilanz nicht ueber eine einzige Aktion urteilt,
  - dass nach einer Bilanz von vorn gezaehlt wird,
  - und dass die Eingabezeit beim Halten vom Termin kommt, nicht von
    der Uhr.

Ausfuehren:
    python3 tools/test_latenz.py
"""
import io
import os
import sys

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
sys.path.insert(0, _HIER)

import _harness as H                                     # noqa: E402

fm = H.fm
F = fm.Frontend
NOW = H.NOW

fails = []
meldungen = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


fm.LOG = lambda s: meldungen.append(s)


class Lage(object):
    LATENZ_SCHWELLE = F.LATENZ_SCHWELLE
    LATENZ_BILANZ_TAKT = F.LATENZ_BILANZ_TAKT
    _latenz_buchen = F._latenz_buchen
    page = 0


def frisch():
    del meldungen[:]
    return Lage()


# ---------------------------------------------------------------------------
print("Test 1: eine normale Aktion wird gebucht, aber nicht beschwatzt")
# ---------------------------------------------------------------------------
L = frisch()
L._latenz_buchen("down", 100.0, 100.05)          # 50 ms
check("gezaehlt", L._latenz_n == 1, L._latenz_n)
check("summiert", abs(L._latenz_summe - 0.05) < 1e-9)
check("keine Log-Zeile unterhalb der Schwelle",
      not [m for m in meldungen if m.startswith("LATENZ:")],
      "sonst stuende bei jedem Schritt eine Zeile")

L = frisch()
L._latenz_buchen("down", 100.0, 100.30)          # 300 ms
check("oberhalb der Schwelle steht eine Zeile",
      any(m.startswith("LATENZ: down") and "300 ms" in m
          for m in meldungen), meldungen[:1])

# ---------------------------------------------------------------------------
print()
print("Test 2: Unsinn kommt nicht in die Statistik")
# ---------------------------------------------------------------------------
for name, args in (("ohne Aktion", (None, 100.0, 100.05)),
                   ("ohne Eingabezeit", ("down", 0.0, 100.05)),
                   ("Uhr rueckwaerts", ("down", 100.0, 99.9)),
                   ("ein Spiel lief dazwischen", ("down", 100.0, 160.0))):
    L = frisch()
    L._latenz_buchen(*args)
    check("%-26s -> nicht gezaehlt" % name,
          getattr(L, "_latenz_n", 0) == 0)

# ---------------------------------------------------------------------------
print()
print("Test 3: DIE BILANZ KOMMT AUCH, WENN NICHTS WAR")
# ---------------------------------------------------------------------------
# Das ist der Kern. Ein Messwerkzeug, das nur bei Ausreissern redet,
# kann eine Verbesserung nicht belegen - es kann eine Vermutung nur
# bestaetigen, nie widerlegen. Genau daran ist Build 182 gescheitert.
L = frisch()
L._latenz_buchen("down", 100.0, 100.05)          # stellt den Takt
check("die erste Bilanz urteilt nicht ueber eine einzige Aktion",
      not [m for m in meldungen if "BILANZ" in m])
# Die Bilanz faellt beim NAECHSTEN Buchen nach Ablauf des Takts - also
# hier, beim zweiten Wert. Beim ersten Anlauf hatte dieser Test neun
# weitere Buchungen davorgesetzt und dann eine Bilanz ueber alle zehn
# erwartet; gezaehlt wurden aber nur die zwei bis zur Bilanz, die
# restlichen acht landeten schon im naechsten Abschnitt. Der Code war
# richtig, meine Erwartung falsch.
NOW[0] += F.LATENZ_BILANZ_TAKT + 1.0
L._latenz_buchen("down", 200.0, 200.03)          # 30 ms
bilanz = [m for m in meldungen if "LATENZ-BILANZ" in m]
check("nach dem Takt kommt eine Bilanz", len(bilanz) == 1, bilanz)
check("sie nennt die Zahl der Schritte",
      bilanz and "2 Schritte" in bilanz[0], bilanz[:1])
check("das Mittel stimmt",
      bilanz and "Mittel 40 ms" in bilanz[0],
      "50 und 30 ms ergeben 40")
check("und der schlechteste wird genannt, mit Aktion",
      bilanz and "schlechtester 50 ms (down)" in bilanz[0], bilanz[:1])

# ---------------------------------------------------------------------------
print()
print("Test 4: nach einer Bilanz wird von vorn gezaehlt")
# ---------------------------------------------------------------------------
check("Zaehler zurueckgesetzt", L._latenz_n == 0, L._latenz_n)
check("Summe zurueckgesetzt", L._latenz_summe == 0.0)
check("und der Hoechstwert auch", L._latenz_max == 0.0,
      "sonst bliebe ein einmaliger Ausreisser fuer immer stehen")
L._latenz_buchen("up", 300.0, 300.02)
check("danach wird wieder gezaehlt", L._latenz_n == 1, L._latenz_n)
check("und es kommt nicht sofort die naechste Bilanz",
      len([m for m in meldungen if "LATENZ-BILANZ" in m]) == 1,
      "sonst stuende bei jedem Schritt eine")

# ---------------------------------------------------------------------------
print()
print("Test 5: beim Halten zaehlt der Termin, nicht die Uhr")
# ---------------------------------------------------------------------------
quelle_in = io.open(os.path.join(_REPO, "frontend", "fe", "input.py"),
                    encoding="utf-8").read()
check("es gibt das Feld", "eingabe_zeit = 0.0" in quelle_in,
      "als Klassenvorgabe, damit jede Attrappe es hat")
check("beim Geraete-Ereignis kommt es von der Uhr",
      "self.eingabe_zeit = time.monotonic()" in quelle_in)
check("bei der Wiederholung vom Faelligkeitstermin",
      "self.eingabe_zeit = _faellig" in quelle_in,
      "sonst waere die gemessene Latenz per Bauart immer nahe null")
check("und die Begruendung steht dabei",
      "CLOCK_REALTIME" in quelle_in,
      "warum nicht der Zeitstempel aus dem evdev-Ereignis")

quelle = io.open(os.path.join(_REPO, "frontend", "frontend.py"),
                 encoding="utf-8").read()
check("die Hauptschleife merkt sich die Eingabezeit der vorigen Aktion",
      "_eingabe_prev = getattr(self.inp, \"eingabe_zeit\", 0.0)" in quelle)
check("und bucht sie gegen den Zeitpunkt, an dem das Bild stand",
      "self._latenz_buchen(_act_prev, _eingabe_prev, _rt0)" in quelle)
check("ohne eine zusaetzliche Zeitabfrage",
      "_rt0 = time.monotonic()" in quelle,
      "beide Zeitstempel lagen ohnehin vor")

# ---------------------------------------------------------------------------
print()
print("Test 6: JE AKTION UND SEITE (Build 197)")
# ---------------------------------------------------------------------------
# DER ANLASS, drei Bilanzen in Folge aus dem Log des Nutzers:
#
#   LATENZ-BILANZ: 349 Schritte, Mittel  59 ms, schlechtester 1179 ms (ok)
#   LATENZ-BILANZ: 215 Schritte, Mittel 112 ms, schlechtester  357 ms (ansicht)
#   LATENZ-BILANZ: 125 Schritte, Mittel 126 ms, schlechtester  205 ms (right)
#
# An diesen Zeilen liess sich NICHT ablesen, ob Build 196 gegriffen hat.
# Ein aufgeschobener Scrollschritt kostet 6 ms und verschwindet im
# Mittel hinter einem Ansichtswechsel, der eine ganze Seite neu baut.
# Ein Mittel ueber alles beantwortet keine Frage - es verdeckt beide
# Antworten gleichzeitig.
L = frisch()
L._latenz_buchen("down", 100.0, 100.006)         # Hauptseite: billig
NOW[0] += F.LATENZ_BILANZ_TAKT + 1.0             # Takt stellen
L._latenz_buchen("down", 200.0, 200.006)
del meldungen[:]

for _ in range(20):                              # Seite 0, gehalten: 6 ms
    L._latenz_buchen("down", 300.0, 300.006)
L.page = 1
for _ in range(4):                               # Seite 1: teuer
    L._latenz_buchen("right", 300.0, 300.150)
L._latenz_buchen("ok", 300.0, 300.400)           # einmalig, sehr teuer

NOW[0] += F.LATENZ_BILANZ_TAKT + 1.0
# Zurueck auf die Hauptseite, BEVOR der letzte Schritt die Bilanz
# auslaest: die ausloesende Buchung wird selbst noch mitgezaehlt, und
# beim ersten Anlauf stand self.page hier noch auf 1 - dadurch erschien
# ein Posten "down/S1", den es im Testaufbau nie gab, und die
# Hauptseite zaehlte 20 statt 21 Schritte. Der Code war richtig, meine
# Vorbereitung falsch; heute zum fuenften Mal dieselbe Sorte Fehler.
L.page = 0
L._latenz_buchen("down", 400.0, 400.006)

zeile = [m for m in meldungen if m.startswith("LATENZ-JE-AKTION:")]
check("es gibt die Aufschluesselung", len(zeile) == 1, zeile)
z = zeile[0] if zeile else ""
check("der billige Scrollschritt der Hauptseite steht eigen da",
      "down/S0" in z, z)
check("und ist als billig erkennbar - DAS ist die Frage, die die "
      "Gesamtbilanz nicht beantworten konnte",
      "down/S0 21x Mittel 6" in z, z)
check("die teure Aktion der Spieleliste steht daneben",
      "right/S1 4x Mittel 150" in z, z)
check("dieselbe Taste auf verschiedenen Seiten bleibt getrennt",
      "down/S0" in z and "right/S1" in z,
      "sonst mischte sich wieder, was man einzeln braucht")
check("sortiert nach dem MITTEL, teuerstes zuerst",
      z.index("ok/S1") < z.index("right/S1") < z.index("down/S0"), z)
check("die Zahl der Schritte steht dabei", "21x" in z and "4x" in z,
      "ein Mittel ueber zwei Schritte ist keine Aussage")
check("und der Hoechstwert je Posten", "max 6" in z and "max 150" in z, z)
check("hoechstens %d Posten je Zeile" % fm.LATENZ_POSTEN_ZEILE,
      z.count(" | ") <= fm.LATENZ_POSTEN_ZEILE - 1,
      "%d Trenner - die Zeile soll in ein Terminal passen"
      % z.count(" | "))

# ---------------------------------------------------------------------------
print()
print("Test 7: nach der Bilanz wird auch hier von vorn gezaehlt")
# ---------------------------------------------------------------------------
# Der ausloesende Schritt wird noch in DIE Zeile mitgezaehlt, die er
# ausloest (deshalb 21 und nicht 20 oben) - und danach wird restlos
# geleert, genau wie _latenz_n. Meine erste Erwartung hier war, er
# stuende noch als erster Posten der naechsten Runde drin. Falsch, und
# zwar zum sechsten Mal heute dieselbe Sorte: ich habe geprueft, was
# ich vermutet habe, statt erst zu lesen, was dasteht.
check("die Posten sind restlos geleert", L._latenz_posten == {},
      list(L._latenz_posten))
del meldungen[:]
L.page = 0
for _ in range(3):
    L._latenz_buchen("up", 500.0, 500.010)
check("und es kommt nicht sofort die naechste Aufschluesselung",
      not [m for m in meldungen if m.startswith("LATENZ-JE-AKTION:")],
      "sonst stuende bei jedem Schritt eine")

# ---------------------------------------------------------------------------
print()
print("Test 8: die Buchfuehrung waechst nicht unbegrenzt")
# ---------------------------------------------------------------------------
L = frisch()
L._latenz_buchen("a", 100.0, 100.01)
NOW[0] += F.LATENZ_BILANZ_TAKT + 1.0
L._latenz_buchen("a", 100.0, 100.01)
for i in range(200):
    L.page = i                                   # 200 verschiedene Schluessel
    L._latenz_buchen("x%d" % i, 100.0, 100.01)
check("gedeckelt", len(L._latenz_posten) <= 40,
      "%d Eintraege" % len(L._latenz_posten))

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
