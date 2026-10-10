#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Jeder Punkt im Systemmenue steht auch im Handbuch (Build 256).

DER ANLASS, und er ist derselbe wie bei test_version_einheitlich.py:
eine Ermahnung im Kommentar laesst niemanden stolpern, ein Werkzeug
schon.

Beim Aufraeumen fuer v4.8 kam heraus, dass das Handbuch NEUN Funktionen
ueberhaupt nicht erwaehnte - Theme-Editor, Hochkant, MiSTers Schriften,
die Lochmasken, die eigenen Hintergrundbilder, MiSTers Favoriten, die
Core-Wahl, den Speicher-Waechter und die Startoptionen. Dazu stand im
Inhaltsverzeichnis sechs Abschnitte lang nichts, die es laengst gab, und
in beiden READMEs wurde eine Funktion beworben, die in Build 250
ABSICHTLICH entfernt wurde (der Anfangsbuchstabe beim Schnellscrollen).

Eine Doku, die still hinter dem Programm zurueckbleibt, ist schlimmer
als eine kurze: sie behauptet Dinge, die nicht stimmen. Dieser Test
haengt deshalb am Menue selbst.

WIE GEPRUEFT WIRD: aus fe/menu.py werden die AKTIONSNAMEN gezogen - die
zweite Stelle jedes Menue-Eintrags, also "masken", "hauptseite",
"nachscan" und so weiter. Diese Namen sind stabil (sie aendern sich
nicht mit der Sprache, anders als die Beschriftungen), und genau
deshalb stehen sie im Handbuch in Abschnitt 16 als Code mit dabei: wer
etwas melden will, kann sagen "bei `masken` passiert ...".

Geprueft wird gegen die AKTIONSNAMEN und NICHT gegen die
Beschriftungen. Eine Pruefung auf den Beschriftungstext waere brittle:
die stecken voller "%s", "-> naechstes" und Umlaute, und sie aendern
sich bei jeder Formulierungspolitur. Dann passt man irgendwann den Test
an statt die Doku - und das ist genau die falsche Richtung.

Ausfuehren:
    python3 tools/test_doku_menue.py
"""
import io
import os
import re
import sys

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)

fails = []


def check(name, ok, extra=""):
    print("  %s %s%s" % ("OK  " if ok else "FEHL", name,
                         ("  (%s)" % extra) if extra else ""))
    if not ok:
        fails.append(name + ((" - " + extra) if extra else ""))


def lies(*teile):
    return io.open(os.path.join(_REPO, *teile), encoding="utf-8").read()


MENU = lies("frontend", "fe", "menu.py")
HB = lies("docs", "HANDBUCH.md")
EN = lies("docs", "MANUAL_EN.md")

# Aktionen, die KEINE eigene Zeile im Handbuch brauchen, mit Grund.
# Bewusst eine kurze, begruendete Liste und kein Schalter zum Abschalten
# der Pruefung.
AUSGENOMMEN = {
    # Reine Zustands-Varianten derselben Zeile - im Handbuch steht die
    # Zeile einmal, nicht zweimal.
    "ra_settings_missing": "Variante von ra_settings (RA in MiSTer fehlt)",
    "ra_setup": "Variante von ra_status (noch nicht eingerichtet)",
}

# ---------------------------------------------------------------------------
print("Test 1: die Aktionen aus dem Menue")
# ---------------------------------------------------------------------------
# Der Bereich, in dem die Gruppen gebaut werden: von display_items bis
# zum Ende des groups-Literals. Davor stehen Hilfsfunktionen, danach die
# Bedienlogik - beide wuerden Namen beisteuern, die keine Menuepunkte
# sind.
_i = MENU.index("    ra_items")
_j = MENU.index("\n    }\n", MENU.index("    groups = {"))
_bereich = MENU[_i:_j]
aktionen = sorted(set(re.findall(r'"([a-z0-9_]+)",\s*None\)', _bereich)))
check("es wurden ueberhaupt Aktionen gefunden", len(aktionen) > 40,
      "%d gefunden" % len(aktionen))
print("    %d Aktionen: %s ..." % (len(aktionen), ", ".join(aktionen[:8])))

# ---------------------------------------------------------------------------
print()
print("Test 2: jede Aktion steht im Handbuch")
# ---------------------------------------------------------------------------
fehlend = []
for a in aktionen:
    if a in AUSGENOMMEN:
        continue
    if ("`%s`" % a) not in HB:
        fehlend.append(a)
check("keine Aktion fehlt in docs/HANDBUCH.md", not fehlend,
      "fehlt: " + ", ".join(fehlend) if fehlend
      else "%d geprueft" % (len(aktionen) - len(AUSGENOMMEN)))
# UND DASSELBE AUF ENGLISCH. Das englische Handbuch war beim Aufraeumen
# fuer v4.8 noch weiter zurueck als das deutsche (vierzehn fehlende
# Abschnitte) - genau deshalb steht es hier mit in der Pruefung und
# nicht in einer Absichtserklaerung.
fehlend_en = [a for a in aktionen
              if a not in AUSGENOMMEN and ("`%s`" % a) not in EN]
check("keine Aktion fehlt in docs/MANUAL_EN.md", not fehlend_en,
      "fehlt: " + ", ".join(fehlend_en) if fehlend_en
      else "%d geprueft" % (len(aktionen) - len(AUSGENOMMEN)))
for a, grund in sorted(AUSGENOMMEN.items()):
    print("    ausgenommen: %-22s %s" % (a, grund))

# ---------------------------------------------------------------------------
print()
print("Test 3: die Uebersicht ist als Abschnitt vorhanden")
# ---------------------------------------------------------------------------
check("Abschnitt 16 existiert", "## 16. Das Systemmenue" in HB
      or "## 16. Das Systemmenü" in HB)
check("und steht im Inhaltsverzeichnis",
      "16. Das Systemmenü von A bis Z" in HB.split("## 1. Paketinhalt")[0],
      "sonst findet ihn niemand")
check("die Startoptionen haben einen eigenen Abschnitt",
      "## 15. Startoptionen" in HB)
check("auch auf Englisch", "## 15. Start options" in EN)
check("und die Uebersicht auch", "## 16. The system menu from A to Z" in EN)
for opt in ("--show", "--bench", "--demo", "--help"):
    check("%-8s ist beschrieben" % opt, ("`%s`" % opt) in HB)

# ---------------------------------------------------------------------------
print()
print("Test 4: die Startoptionen im Handbuch sind die aus dem Programm")
# ---------------------------------------------------------------------------
# Umgekehrte Richtung: nicht nur "steht alles im Handbuch", sondern auch
# "das Handbuch erfindet nichts".
FE = lies("frontend", "frontend.py")
_opt = FE.split("    _OPTIONEN = {")[1].split("    }")[0]
echte = set(re.findall(r'"(--?[a-z]+)"', _opt))
check("das Programm kennt die vier", echte >= {"--show", "--bench",
                                               "--demo", "--help"},
      str(sorted(echte)))
_ab15 = HB.split("## 15. Startoptionen")[1].split("\n## ")[0]
erfunden = [o for o in re.findall(r'`(--[a-z]+)`', _ab15) if o not in echte]
check("und das Handbuch erfindet keine", not erfunden, str(erfunden))

# ---------------------------------------------------------------------------
print()
print("Test 5: keine entfernte Funktion wird noch beworben")
# ---------------------------------------------------------------------------
# Build 250 hat den Anfangsbuchstaben beim Schnellscrollen ABSICHTLICH
# entfernt (Nutzerwunsch). Beide READMEs haben ihn danach noch fuenf
# Builds lang angepriesen. Das ist die Sorte Fehler, die niemand
# bemerkt, weil niemand die Doku gegen den Code liest.
#
# ACHTUNG, EIGENER FEHLER BEIM SCHREIBEN: der erste Entwurf suchte den
# Namen im ganzen Quelltext und war rot - an einem KOMMENTAR, der
# erklaert, was Build 250 entfernt hat. Dieselbe Falle wie in Build 250
# (test_core_neu.py traf den eigenen Docstring) und 251
# (test_zaparoo.py ebenso). Geprueft wird deshalb nur der CODE, wie es
# nur_code() in test_beenden.py vormacht.
_code = "\n".join(z for z in FE.split("\n")
                  if not z.strip().startswith("#"))
for name, was in (("SCHNELLMARKE_ANTEIL",
                   "der Anfangsbuchstabe beim Schnellscrollen "
                   "(Build 250 entfernt)"),
                  ("def schnellmarke_text", "seine Textfunktion"),
                  ("_schnellmarke_zeichnen(", "sein Zeichner")):
    _raus = name not in _code
    check("%s ist wirklich aus dem Code raus" % was, _raus,
          "" if _raus else "%r steht noch im Code" % name)
for datei in ("README.md", "README_EN.md"):
    q = lies(datei).lower()
    check("%s bewirbt ihn nicht mehr" % datei,
          "anfangsbuchstabe beim schnellscroll" not in q
          and "initial letter while fast-scroll" not in q)

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
