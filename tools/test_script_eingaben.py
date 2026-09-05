#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft die Abfragen in den Shell-Skripten gegen Wagenruecklauf
(Build 83).

AUSLOESER (Nutzer-Rueckmeldung):

    "wenn ich Frontend_Boxart_Download.sh starte, egal ob ich Option 1
     oder 2 auswaehle, der laedt immer nur Profil sd runter. 1 sollte ja
     fuer sd sein und 2 fuer hd."

URSACHE: "read -r" entfernt den Zeilenumbruch, aber KEIN
Wagenruecklauf-Zeichen. Je nach Startweg (MiSTer-OSD, serielle Konsole,
SSH-Client) kommt die Zeile als "2\\r" an, und

    case "2\\r" in 2|hd|HD) ... ;; *) ... ;; esac

trifft den *-Zweig. Der bedeutete "sd". Die Auswahl war damit
wirkungslos - und zwar lautlos, weil das Skript weiterlief, als waere
alles in Ordnung.

WARUM DAS HIER GEPRUEFT WIRD UND NICHT PER HAND: die Skripte werden von
Hand nur mit einer normalen Tastatur getestet, und die liefert kein \\r.
Genau der Fall, der beim Nutzer auftritt, ist der, den man beim Testen
nie erwischt. Deshalb faehrt dieser Test die Skripte mit BEIDEN
Eingabeformen und vergleicht.

Ausfuehren:
    python3 tools/test_script_eingaben.py
"""
import os
import re
import subprocess
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
SCRIPTS = os.path.join(_REPO, "Scripts")

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


def boxart_lauf(eingabe):
    """Das echte Auswahlmenue aus Frontend_Boxart_Download.sh laufen
    lassen - ohne den Download selbst.

    Statt das Skript nachzubauen (was den Fehler mitnehmen wuerde, ohne
    ihn zu zeigen) wird die ECHTE Datei genommen und nur die letzte
    Zeile ersetzt, die python3 startet. Aendert jemand die Auswahl-
    logik, prueft dieser Test also weiterhin die Wahrheit."""
    quelle = open(os.path.join(SCRIPTS, "Frontend_Boxart_Download.sh"),
                  encoding="utf-8").read()
    quelle = re.sub(r"^exec /usr/bin/python3 .*$",
                    'echo "ERGEBNIS=$PROFIL"',
                    quelle, flags=re.M)
    # Die Standard-Ermittlung fragt das Frontend auf dem MiSTer - hier
    # gibt es das nicht, das Skript faellt dann selbst auf sd zurueck.
    with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False,
                                     encoding="utf-8") as f:
        f.write(quelle)
        pfad = f.name
    try:
        p = subprocess.run(["bash", pfad], input=eingabe,
                           capture_output=True, text=True, timeout=30)
        m = re.search(r"ERGEBNIS=(\w+)", p.stdout)
        return m.group(1) if m else "(nichts)"
    finally:
        os.unlink(pfad)


print("Test 1: die Profil-Auswahl - mit und ohne Wagenruecklauf")
FAELLE = [
    ("1\n",     "sd", "Ziffer 1"),
    ("2\n",     "hd", "Ziffer 2"),
    ("1\r\n",   "sd", "Ziffer 1 mit Wagenruecklauf"),
    ("2\r\n",   "hd", "Ziffer 2 mit Wagenruecklauf"),   # der gemeldete Fehler
    ("hd\n",    "hd", "Wort hd"),
    ("HD\r\n",  "hd", "Wort HD mit Wagenruecklauf"),
    ("sd\n",    "sd", "Wort sd"),
    (" 2 \n",   "hd", "Ziffer 2 mit Leerzeichen"),
]
for eingabe, soll, beschreibung in FAELLE:
    ist = boxart_lauf(eingabe)
    check("%s -> %s" % (beschreibung, soll), ist == soll,
          "geliefert: %s" % ist)

print()
print("Test 2: ein Argument wirkt weiterhin direkt")
# So ruft der Ersteinrichtungs-Assistent das Skript auf
# (frontend.py: run_script(..., args=[profile])).
for arg, soll in (("hd", "hd"), ("sd", "sd")):
    quelle = open(os.path.join(SCRIPTS, "Frontend_Boxart_Download.sh"),
                  encoding="utf-8").read()
    quelle = re.sub(r"^exec /usr/bin/python3 .*$",
                    'echo "ERGEBNIS=$PROFIL"', quelle, flags=re.M)
    with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False,
                                     encoding="utf-8") as f:
        f.write(quelle)
        pfad = f.name
    try:
        p = subprocess.run(["bash", pfad, arg], input="",
                           capture_output=True, text=True, timeout=30)
        m = re.search(r"ERGEBNIS=(\w+)", p.stdout)
        ist = m.group(1) if m else "(nichts)"
    finally:
        os.unlink(pfad)
    check("Argument '%s' -> %s" % (arg, soll), ist == soll,
          "geliefert: %s" % ist)
    check("Argument '%s' fragt nicht nach" % arg,
          "Profil waehlen" not in p.stdout)

print()
print("Test 3: keine Abfrage vergleicht mehr ungefiltert auf Gleichheit")
# Die Vorbeugung: ein exaktes [ "$x" = "y" ] bzw. ein case ohne
# *-Muster direkt nach einem read ist genau die Konstruktion, die
# hier schiefgegangen ist. Sie ist erlaubt - aber nur, wenn die
# Eingabe vorher gesaeubert wurde.
VERDAECHTIG = []
LESEN = re.compile(r'^\s*read\s+(?:-\w+\s+)*(?:-p\s+"[^"]*"\s+)?(\w+)\s*$')
for fn in sorted(os.listdir(SCRIPTS)):
    if not fn.endswith(".sh"):
        continue
    zeilen = open(os.path.join(SCRIPTS, fn),
                  encoding="utf-8").read().split("\n")
    for i, z in enumerate(zeilen):
        m = LESEN.match(z)
        if not m:
            continue
        name = m.group(1)
        folgende = "\n".join(zeilen[i + 1:i + 14])
        # Entweder die Eingabe wird gesaeubert ...
        gesaeubert = (("tr -d" in folgende or "_saeubern" in folgende)
                      and name in folgende)
        # ... oder es wird ohnehin nur auf ein Praefix verglichen
        # (z.B. [nN]*), dann stoert ein angehaengtes \r nicht.
        nur_praefix = bool(re.search(r"\[[A-Za-z]+\]\*\)", folgende))
        if not gesaeubert and not nur_praefix:
            VERDAECHTIG.append("%s:%d  read %s" % (fn, i + 1, name))
check("jede Abfrage ist entweder gesaeubert oder praefix-tolerant",
      not VERDAECHTIG, "; ".join(VERDAECHTIG))

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for f_ in fails:
        print("  -", f_)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
