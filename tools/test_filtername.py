#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Eigener Name fuer eine gemerkte Filter-Kategorie (Build 250).

WAS ES SCHON GAB, und das ist der Teil, der hier nicht doppelt gebaut
wird: Build 143 merkt eine Filterbedingung als eigene Kategorie. Der
Name entsteht dabei automatisch aus der Bedingung ("SNES / Platform /
1990-1994"), und im Kopf von fe/filter.py steht die Begruendung:

    "Absichtlich ohne Texteingabe ... und der Buchstabenwaehler fuer
    einen Namen waere drei Bildschirme fuer etwas, das sich von selbst
    ergibt."

Der erste Teil gilt weiter. Der zweite war falsch: der
Buchstabenwaehler existiert seit Build 88 fuer die Suche, samt
Zeichnen fuer Roehre UND HDMI. Herausgezogen statt neu gebaut
(name_abfragen()) sind es rund zwanzig Zeilen - und "Beste Jump n
Runs" sagt mehr als "SNES / Platform / 1990-1994".

WORAN ES SCHEITERN KANN

  1. Doppelte Namen. Der Name IST der Schluessel: vergessen() findet
     den Eintrag ueber ihn, der Hauptseiten-Editor bildet sein
     Kuerzel daraus. Zwei Kategorien gleichen Namens kann man nicht
     mehr auseinanderhalten.
  2. Umbenennen aendert die Bedingung mit. Dann zeigt die Kategorie
     danach andere Spiele, und niemand weiss, warum.
  3. Ein leerer Name wird uebernommen - eine Kategorie ohne
     Beschriftung findet man nicht wieder.
  4. Der Dialog laesst sich nicht verlassen, oder er frisst die
     Stelle des Suchwaehlers.
  5. Der gewohnte Weg wird laenger. Die Zeile aus Build 143 muss
     genau bleiben, was sie war: EIN Tastendruck, Name automatisch.

Ausfuehren:
    python3 tools/test_filtername.py
"""
import io
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H                                        # noqa: E402

import fe.filter as FILTER                                  # noqa: E402
import fe.translations as TR                                # noqa: E402
from fe.translations import t                              # noqa: E402

fm = H.fm
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_QF = io.open(os.path.join(_REPO, "frontend", "frontend.py"),
              encoding="utf-8").read()
fails = []
_TMP = tempfile.mkdtemp(prefix="filtername_")


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


_alt_datei = FILTER.KATEGORIEN_DATEI
FILTER.KATEGORIEN_DATEI = os.path.join(_TMP, "kategorien.json")

_F1 = {"genre": "Platform"}
_F2 = {"genre": "Shooter"}

# ---------------------------------------------------------------------------
print("Test 1: merken mit eigenem Namen")
# ---------------------------------------------------------------------------
_n = FILTER.merken_mit_namen("SNES", _F1, "Beste Jump n Runs")
check("der Name kommt zurueck", _n == "Beste Jump n Runs", repr(_n))
_liste = FILTER.gemerkte_laden()
check("und steht in der Datei", len(_liste) == 1
      and _liste[0]["name"] == "Beste Jump n Runs", str(_liste))
check("die Bedingung ist die uebergebene",
      _liste and _liste[0]["filter"] == _F1, str(_liste[0]["filter"]))
check("und die Quellkategorie auch",
      _liste and _liste[0]["kat"] == "SNES")
check("der automatische Weg funktioniert unveraendert daneben",
      FILTER.merken("SNES", _F2, t)
      == FILTER.name_fuer("SNES", _F2, t),
      "Build 143 bleibt, wie es war")

# ---------------------------------------------------------------------------
print()
print("Test 2: was abgewiesen werden MUSS")
# ---------------------------------------------------------------------------
check("ein schon vergebener Name",
      FILTER.merken_mit_namen("SNES", _F1, "Beste Jump n Runs") is None,
      "der Name ist der Schluessel - zwei gleiche waeren nicht mehr "
      "auseinanderzuhalten")
for _name, _was in ((None, "None"), ("", "leer"), ("   ", "nur Leerzeichen")):
    check("%-18s wird abgewiesen" % _was,
          FILTER.merken_mit_namen("SNES", _F1, _name) is None)
check("ein Filter, der nichts filtert",
      FILTER.merken_mit_namen("SNES", {}, "Leer") is None)
check("und eine fehlende Quellkategorie",
      FILTER.merken_mit_namen("", _F1, "Ohne Kategorie") is None)
check("Leerzeichen am Rand werden abgeschnitten",
      FILTER.merken_mit_namen("SNES", {"genre": "Puzzle"},
                              "  Knobelei  ") == "Knobelei")

# ---------------------------------------------------------------------------
print()
print("Test 3: umbenennen laesst die Bedingung in Ruhe")
# ---------------------------------------------------------------------------
# DAS IST DER PUNKT: wer umbenennt, will einen anderen NAMEN - nicht
# andere Spiele.
_vor = [e for e in FILTER.gemerkte_laden()
        if e["name"] == "Beste Jump n Runs"][0]
check("umbenennen gelingt",
      FILTER.umbenennen("Beste Jump n Runs", "Huepfspiele"))
_nach = [e for e in FILTER.gemerkte_laden()
         if e["name"] == "Huepfspiele"]
check("der neue Name steht da", len(_nach) == 1, str(_nach))
check("der alte ist weg",
      not [e for e in FILTER.gemerkte_laden()
           if e["name"] == "Beste Jump n Runs"])
check("die Bedingung ist unveraendert",
      _nach and _nach[0]["filter"] == _vor["filter"],
      "%s gegen %s" % (_nach[0]["filter"], _vor["filter"]))
check("die Quellkategorie auch",
      _nach and _nach[0]["kat"] == _vor["kat"])
check("die Zahl der Eintraege bleibt",
      len(FILTER.gemerkte_laden()) == 3,
      "%d" % len(FILTER.gemerkte_laden()))
check("auf einen vergebenen Namen umbenennen geht nicht",
      not FILTER.umbenennen("Knobelei", "Huepfspiele"),
      "sonst gaebe es zwei gleiche")
check("und der alte bleibt dann stehen",
      FILTER.ist_gemerkt("Knobelei"))
check("auf denselben Namen umbenennen ist kein Fehler",
      FILTER.umbenennen("Huepfspiele", "Huepfspiele"))
check("etwas Unbekanntes umzubenennen schlaegt fehl",
      not FILTER.umbenennen("gibt es nicht", "Neu"))
for _a, _b in ((None, "X"), ("Huepfspiele", ""), ("", "")):
    check("umbenennen(%r, %r) schlaegt fehl" % (_a, _b),
          not FILTER.umbenennen(_a, _b))
check("vergessen() findet den neuen Namen",
      FILTER.vergessen("Huepfspiele")
      and not FILTER.ist_gemerkt("Huepfspiele"),
      "der Name ist der Schluessel - nach dem Umbenennen muss er es "
      "weiterhin sein")

FILTER.KATEGORIEN_DATEI = _alt_datei

# ---------------------------------------------------------------------------
print()
print("Test 4: der Namensdialog")
# ---------------------------------------------------------------------------
H.set_screen(1920, 1080)
fe = H.make_frontend(page=1)
check("name_abfragen() gibt es", hasattr(fe, "name_abfragen"))


class _Tasten(object):
    """Eine Eingabe-Attrappe, die eine feste Folge abspielt.

    SIE WIRFT, WENN SIE LEER LAEUFT, und das ist Absicht: ein Dialog,
    der seine Abbruchtaste nicht kennt, wuerde sonst ewig drehen. Genau
    dieser Fehler hat in Build 246 die Ziehung zum Stillstand gebracht
    und den Test zehn Minuten laufen lassen."""

    def __init__(self, folge):
        self.folge = list(folge)
        self.gefragt = 0

    def read_action(self, timeout=None):
        self.gefragt += 1
        if not self.folge:
            raise AssertionError(
                "der Dialog hat %d Tasten verbraucht und kehrt nicht "
                "zurueck" % self.gefragt)
        return self.folge.pop(0)


def _felder_index(art, wert=None):
    for i, (a, w) in enumerate(fe.PICKER_FELDER):
        if a == art and (wert is None or w == wert):
            return i
    raise AssertionError("Feld %r/%r gibt es nicht" % (art, wert))


def _zu(ziel, von=0):
    """Tastenfolge, um von Feld `von` zu Feld `ziel` zu kommen.

    MIT STARTPOSITION, und das war im ersten Entwurf der Fehler: er
    rechnete immer von Feld 0 los. Nach einem Buchstabendruck steht
    der Waehler aber noch auf diesem Buchstaben - die zweite Folge
    zielte also ins Leere, und der Test lief in die Notbremse der
    Attrappe ("18 Tasten verbraucht und kehrt nicht zurueck"). Dass er
    dort gelandet ist und nicht in einer Endlosschleife, ist genau der
    Zweck dieser Notbremse.

    Nachgebildet wird die Bewegung von _picker_bewegen(): "down"
    klemmt die Spalte auf die Breite der neuen Zeile, "right" laeuft
    innerhalb der Zeile um. Die letzte Zeile ist kuerzer als die
    anderen (Leerzeichen, Loeschen, OK), deshalb reicht Rechnen mit
    einer festen Breite nicht."""
    zeilen = fe._picker_zeilen()
    n = fe.PICKER_SPALTEN
    z, sp = divmod(von, n)
    z_ziel, s_ziel = divmod(ziel, n)
    raus = []
    while z != z_ziel:
        if z < z_ziel:
            raus.append("down")
            z += 1
        else:
            raus.append("up")
            z -= 1
        sp = min(sp, len(zeilen[z]) - 1)
    while sp != s_ziel:
        raus.append("right")
        sp = (sp + 1) % len(zeilen[z])
    return raus


_ok = _felder_index("done")
_del = _felder_index("del")

# a) Vorschlag unveraendert uebernehmen - EIN Druck auf "OK".
fe.inp = _Tasten(_zu(_ok) + ["ok"])
check("der Vorschlag kommt unveraendert zurueck",
      fe.name_abfragen("Titel", "Mein Name") == "Mein Name")

# b) Abbrechen liefert None, und zwar bei jeder Abbruchtaste.
for _taste in ("back", "exit", "select"):
    fe.inp = _Tasten([_taste])
    check("%-8s bricht ab" % _taste,
          fe.name_abfragen("Titel", "Egal") is None)

# c) Buchstaben vom Raster.
_a = _felder_index("letter", "A")
fe.inp = _Tasten(_zu(_a) + ["ok"] + _zu(_ok, _a) + ["ok"])
check("ein Buchstabe aus dem Raster kommt an",
      fe.name_abfragen("Titel", "") == "A")

# d) Buchstaben von einer echten Tastatur.
fe.inp = _Tasten(["letter:H", "letter:I"] + _zu(_ok) + ["ok"])
check("Buchstabentasten wirken auch", fe.name_abfragen("Titel", "") == "HI")

# e) Loeschen, beide Wege.
fe.inp = _Tasten(_zu(_del) + ["ok"] + _zu(_ok, _del) + ["ok"])
check("das Loeschfeld nimmt ein Zeichen weg",
      fe.name_abfragen("Titel", "AB") == "A")
fe.inp = _Tasten(["search_backspace"] + _zu(_ok) + ["ok"])
check("und die Rueckschritt-Taste auch",
      fe.name_abfragen("Titel", "AB") == "A")

# f) Ein leerer Name ist ein Abbruch.
fe.inp = _Tasten(["search_backspace", "search_backspace"]
                 + _zu(_ok) + ["ok"])
check("ein leerer Name ist ein Abbruch",
      fe.name_abfragen("Titel", "AB") is None,
      "eine Kategorie ohne Beschriftung findet man nicht wieder")

# g) Die Laenge ist begrenzt - aber der Dialog kehrt trotzdem zurueck.
fe.inp = _Tasten(_zu(_a) + ["ok"] * 6 + _zu(_ok, _a) + ["ok"])
_lang = fe.name_abfragen("Titel", "X" * 4, maxlen=5)
check("die Grenze haelt", _lang is not None and len(_lang) == 5,
      repr(_lang))

# h) Die Stelle des Suchwaehlers darf der Dialog nicht verlieren.
fe._picker_i = 11
fe.inp = _Tasten(["back"])
fe.name_abfragen("Titel", "X")
check("die Stelle des Suchwaehlers bleibt", fe._picker_i == 11,
      "%d - sonst springt die Suche beim naechsten Oeffnen woanders hin"
      % fe._picker_i)

# ---------------------------------------------------------------------------
print()
print("Test 5: angeschlossen, und der gewohnte Weg bleibt kurz")
# ---------------------------------------------------------------------------
_code = "\n".join(z for z in _QF.split("\n")
                  if not z.strip().startswith("#"))
_blk = _code.split("def filter_bildschirm")[1].split("\n    def ")[0]
check("der Filter-Bildschirm hat jetzt zwei Aktionszeilen",
      "_zeilen = len(FILTER.FELDER) + 2" in _blk,
      "vier Felder, merken/vergessen, eigener Name")
check("die alte Zeile ist unveraendert EIN Tastendruck",
      'akt == "ok" and zeile == len(FILTER.FELDER):' in _blk
      and "FILTER.merken(" in _blk,
      "Build 143 bleibt, wie es war - der automatische Name kostet "
      "keinen Umweg")
check("die neue Zeile ruft den Dialog",
      'zeile == len(FILTER.FELDER) + 1' in _blk
      and "self.name_abfragen(" in _blk)
check("sie benutzt den automatischen Namen als Vorschlag",
      "FILTER.name_fuer(" in _blk,
      "wer ihn behalten will, drueckt zweimal")
check("umbenennen fuer eine schon gemerkte Kategorie",
      "FILTER.umbenennen(" in _blk)
check("und merken_mit_namen fuer eine neue",
      "FILTER.merken_mit_namen(" in _blk)
check("ein belegter Name wird gemeldet",
      "filter_name_belegt" in _blk,
      "sonst drueckt man dreimal und glaubt an einen Haenger")
_dlg = _code.split("def name_abfragen")[1].split("\n    def ")[0]
check("der Dialog baut den Waehler nicht nach",
      "self._draw_letter_picker(" in _dlg
      and "self._picker_bewegen(" in _dlg,
      "Build 88 hat ihn fuer Roehre UND HDMI gerechnet")
check("und stellt die Stelle des Suchwaehlers wieder her",
      "finally:" in _dlg and "self._picker_i = _alt_i" in _dlg)
for _schl in ("filter_merken_name", "filter_umbenennen",
              "filter_name_titel", "filter_umbenannt",
              "filter_name_belegt"):
    _e = TR.TRANSLATIONS.get(_schl)
    check("%-22s zweisprachig" % _schl,
          bool(_e) and bool(_e.get("de")) and bool(_e.get("en")))

shutil.rmtree(_TMP, ignore_errors=True)
print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
