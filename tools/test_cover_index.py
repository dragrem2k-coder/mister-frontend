#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft den Cover-Index nach dem Ausbau des regulaeren Ausdrucks
(Build 107).

NUTZER-RUECKMELDUNG: "Warum ist nach einem Neustart das Hauptmenue so
traege? Das Scrollen ist total langsam, wird erst nach ein paar
Sekunden besser - vor allem im HDMI-Modus."

GEFUNDEN: _art_index() baut beim Start fuer jedes System ein
Verzeichnis "Spielname -> Coverdatei" auf, in ART_BASE UND ART_HD. Je
Datei lief dabei ein re.sub(r"^\\d+\\s+", ...), um eine fuehrende
Sortiernummer zu entfernen. Bei einer grossen Sammlung sind das
sechsstellig viele Aufrufe - reines Python, also GIL-haltend, genau
waehrend jemand das frisch gestartete Hauptmenue bedient.

Nachgemessen an 48 Systemen zu je 1500 Covern: der regulaere Ausdruck
allein war 69 % des gesamten Index-Aufbaus, die Ersatzfassung ist
viermal schneller.

WARUM DIESER TEST SO GRUENDLICH IST: eine Abweichung faellt nicht auf.
Sie stuerzt nicht ab und malt nichts falsch - sie zeigt irgendwann bei
irgendeinem Spiel das falsche Cover oder gar keines, und niemand bringt
das je mit dieser Funktion in Verbindung. Deshalb wird die
Gleichwertigkeit hier nicht an ein paar Beispielen geprueft, sondern
ueber ALLE 65536 Zeichen der Basic Multilingual Plane in vier
Stellungen.

Ausfuehren:
    python3 tools/test_cover_index.py
"""
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_REPO, "frontend"))

import fe.art as A                                      # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


ALT = re.compile(r"^\d+\s+")
NEU = A._ohne_fuehrende_nummer

print("Test 1: die Faelle, um die es fachlich geht")
for roh, erwartet in (
        ("007 Super Mario Kart (USA)", "Super Mario Kart (USA)"),
        ("1 Zelda", "Zelda"),
        ("0123  Doppelt Leerzeichen", "Doppelt Leerzeichen"),
        ("42\tTabulator", "Tabulator"),
        ("Super Mario World", "Super Mario World"),
        ("1234KeinAbstand", "1234KeinAbstand"),
        ("Spiel 12", "Spiel 12"),
        ("", ""),
        ("99 ", ""),
        ("2 Fast 2 Furious", "Fast 2 Furious")):
    check("%-28r -> %r" % (roh, erwartet), NEU(roh) == erwartet,
          "ist: %r" % NEU(roh))

print("Test 2: gleichwertig zum bisherigen regulaeren Ausdruck")
# Das ist die eigentliche Zusage. Vier Stellungen je Zeichen: ganz
# vorne, hinter einer Ziffer, hinter zwei Ziffern, und allein.
schlecht = []
for cp in range(0x0000, 0x10000):
    c = chr(cp)
    for probe in (c + " Titel", "1" + c + "Titel", "12" + c + " Titel", c):
        if ALT.sub("", probe) != NEU(probe):
            schlecht.append((hex(cp), probe))
            if len(schlecht) > 5:
                break
    if len(schlecht) > 5:
        break
check("65536 Zeichen x 4 Stellungen ohne Abweichung", not schlecht,
      "%r" % (schlecht[:5],))

print("Test 3: der regulaere Ausdruck ist wirklich raus")
quelle = open(os.path.join(_REPO, "frontend", "fe", "art.py"),
              encoding="utf-8", errors="replace").read()
# GEAENDERT (Build 117): der Block faengt jetzt bei _index_ergaenzen()
# an. Das Nachtragen der Ausweich-Schreibweisen ist von dort aus
# _art_index() UND _docs_index() gemeinsam - der Aufruf von
# _ohne_fuehrende_nummer() steht seither in dieser Hilfsfunktion und
# nicht mehr im Rumpf von _art_index(). Geprueft wird weiterhin
# dasselbe: kein regulaerer Ausdruck, und die eigene Fassung wird
# tatsaechlich benutzt.
block = quelle[quelle.index("def _index_ergaenzen("):]
block = block[:block.index("def _art_path_in(")]
check("kein re.sub mehr im Index-Aufbau", "re.sub" not in block)
check("stattdessen die eigene Fassung",
      "_ohne_fuehrende_nummer(base)" in block)
# isdecimal() statt isdigit() ist kein Geschmack, sondern der Grund,
# warum Test 2 durchgeht. Geprueft wird der CODE, nicht der Text
# darueber - die Erklaerung im Docstring nennt isdigit() ja gerade
# deshalb, weil es das Falsche waere.
_fn = quelle[quelle.index("def _ohne_fuehrende_nummer"):
             quelle.index("def _art_index(")]
_rumpf = _fn.split('"""')[2] if _fn.count('"""') >= 2 else _fn
check("der Rumpf benutzt isdecimal()", "isdecimal()" in _rumpf)
check("und nirgends isdigit()", "isdigit()" not in _rumpf)

print("Test 4: der Index selbst liefert unveraendert dasselbe")
# Nicht nur die Hilfsfunktion, sondern das Ergebnis: exakte Namen haben
# Vorrang, nummerierte fuellen nur Luecken.
dateien = ["007 Super Mario Kart (USA).art",
           "Super Mario Kart (USA).art",
           "012 Zelda.art",
           "Irgendwas.art",
           "keine.txt"]
echte_listdir = A.os.listdir
A.os.listdir = lambda p: list(dateien)
A._art_index_cache.clear()
try:
    idx = A._art_index("/base", "SNES")
finally:
    A.os.listdir = echte_listdir
    A._art_index_cache.clear()
check("exakter Name gewinnt gegen die nummerierte Fassung",
      idx.get("Super Mario Kart (USA)") == "Super Mario Kart (USA).art",
      "ist: %r" % idx.get("Super Mario Kart (USA)"))
check("nummerierte Fassung fuellt eine Luecke",
      idx.get("Zelda") == "012 Zelda.art", "ist: %r" % idx.get("Zelda"))
check("der volle Dateiname steht ebenfalls drin",
      idx.get("007 Super Mario Kart (USA)")
      == "007 Super Mario Kart (USA).art")
check("Nicht-.art-Dateien bleiben draussen", "keine" not in idx)

print("Test 5: der Start-Thread steckt zurueck, solange bedient wird")
# Die zweite Haelfte der Meldung. Auch viermal schneller ist auf der
# schwachen CPU noch spuerbar, wenn es am Stueck durchlaeuft - also
# laeuft es nicht am Stueck durch.
quelle_f = open(os.path.join(_REPO, "frontend", "frontend.py"),
                encoding="utf-8", errors="replace").read()
block = quelle_f[quelle_f.index("def _prewarm_art_dirs"):]
block = block[:block.index("threading.Thread(target=_prewarm_art_dirs")]
check("wartet auf eine Ruhephase",
      "self._last_input_time" in block and "PREWARM_SETTLE" in block)
# Die Obergrenze ist kein Beiwerk: ohne sie bleibt das Vorwaermen bei
# gehaltener Taste DAUERHAFT stehen (Tastenwiederholung 0.08 s gegen
# eine Ruhe-Schwelle von 0.10 s - es kommt nie eine Ruhephase). Genau
# das ist beim Nachmessen passiert: null eingelesene Systeme.
check("mit Obergrenze, damit es nicht dauerhaft stehenbleibt",
      "PREWARM_MAX_WARTEN" in block)
check("die Obergrenze ist auch definiert",
      "PREWARM_MAX_WARTEN = " in quelle_f)
check("und zwar VOR dem Einlesen",
      block.index("time.sleep(0.05)") < block.index("_art_index(ART_BASE"))
# Der Thread liest _last_input_time in seiner ersten Zeile - gibt es das
# Feld dann noch nicht, stirbt er still und das Vorwaermen faellt
# lautlos aus.
vor_thread = quelle_f[:quelle_f.index(
    "threading.Thread(target=_prewarm_art_dirs")]
check("_last_input_time existiert, bevor der Thread startet",
      "self._last_input_time = time.monotonic()" in vor_thread)

print()
if fails:
    print("FEHLGESCHLAGEN (%d):" % len(fails))
    for f_ in fails:
        print("  -", f_)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
