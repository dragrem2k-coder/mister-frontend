#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Die RUCKLER-Aufschlüsselung muss aufgehen (Build 193).

DER ANLASS, aus dem Log des Nutzers - vierzehnmal hintereinander
waehrend eines gehaltenen Scrollens:

    RUCKLER: 202 ms busy (stream=1 haus=0 bg=20 restore=6 rows=36
             art=0 flip=22 | vorige Aktion=down Seite=1)

Zwei Dinge stimmen daran nicht.

ERSTENS ergeben die Posten zusammen 85 ms, gemessen waren 202. Ueber
die Haelfte stand nirgends.

ZWEITENS sind bg, rows und flip in allen vierzehn Zeilen
BUCHSTABENGLEICH (20, 36, 22), waehrend die gemessene Zeit zwischen
202 und 240 ms schwankte. Echte Messungen schwanken. Diese drei wurden
nur beim VOLLAUFBAU gesetzt; auf dem schnellen Navigationspfad -
genau dem, der beim Scrollen laeuft - behielten sie ihren alten Wert
und wurden trotzdem geloggt. restore wiederum addierte sich auf und
wuchs im Log sichtbar von 6 auf 36.

Die Folge war keine Kleinigkeit: die Zeile sah plausibel aus, und sie
hat mich prompt an die falsche Stelle geschickt - ich habe die
Coverarbeit verdaechtigt, obwohl "art=0" danebenstand.

WAS DIESER TEST ABSICHERT

  - dass alle Posten vor jeder Aktion auf null gehen,
  - dass die Aufzaehlung der Posten an EINER Stelle steht, damit ein
    neuer nicht vergessen werden kann,
  - dass ein Rest ausgewiesen wird - ist er gross, sagt das Werkzeug
    es selbst,
  - dass der Rest nie negativ wird,
  - und dass der schnelle Pfad seine eigenen Posten eintraegt.

Ausfuehren:
    python3 tools/test_perf_aufschluesselung.py
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

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


quelle = io.open(os.path.join(_REPO, "frontend", "frontend.py"),
                 encoding="utf-8").read()

# ---------------------------------------------------------------------------
print("Test 1: alle Posten gehen vor jeder Aktion auf null")
# ---------------------------------------------------------------------------
class Lage(object):
    PERF_POSTEN = F.PERF_POSTEN
    _perf_zuruecksetzen = F._perf_zuruecksetzen


L = Lage()
for name in F.PERF_POSTEN:
    setattr(L, name, 0.123)
L._perf_zuruecksetzen()
for name in F.PERF_POSTEN:
    check("%-16s auf null" % name, getattr(L, name) == 0,
          getattr(L, name))

check("und sie wird in der Hauptschleife gerufen",
      "self._perf_zuruecksetzen()" in quelle)
_i = quelle.index("self._perf_zuruecksetzen()")
check("und zwar NACH dem Buchen der vorigen Aktion",
      quelle.index("self._latenz_buchen(") < _i,
      "sonst waeren die Posten schon weg, bevor sie geloggt wurden")

# ---------------------------------------------------------------------------
print()
print("Test 2: die Aufzaehlung steht an EINER Stelle")
# ---------------------------------------------------------------------------
# Sonst wird beim naechsten neuen Posten genau einer von zwei Orten
# vergessen - und dann fehlt er still in der Statistik.
for name in ("_perf_bg", "_perf_restore", "_perf_rows", "_perf_art",
             "_perf_flip", "_perf_house"):
    check("%s steht in PERF_POSTEN" % name, name in F.PERF_POSTEN)

# ---------------------------------------------------------------------------
print()
print("Test 3: DER REST - die Zeile muss aufgehen")
# ---------------------------------------------------------------------------
check("die Zeile weist einen Rest aus", "rest=%.0f" in quelle,
      "ohne ihn sieht eine luecken­hafte Aufschluesselung vollstaendig aus")
# Von der Sammelliste bis zum Ende des Log-Aufrufs. Beim ersten
# Anlauf setzte dieser Schnitt bei LOG("RUCKLER: an - die Liste _p
# steht aber DAVOR, und der Test meldete einen Fehler, den es nicht
# gab. Schon wieder nach dem Wort geschnitten statt nach der Struktur.
_z = quelle[quelle.index("_oben = [(_rt1 - _rt0)"):]
_z = _z[:_z.index("self.page]))") + 20]
check("der Rest wird aus busy minus den Oberposten gerechnet",
      "_busy - sum(_oben)" in _z, _z[-200:])
check("und nie negativ", "max(0.0, _busy - sum(_oben))" in _z,
      "eine negative Zahl dort wuerde niemand mehr einordnen")
check("die Oberposten stehen als Liste, nicht doppelt aufgezaehlt",
      _z.count("_oben = [") == 1)
# BUILD 195: die Aufteilung darf NICHT in den Rest eingerechnet
# werden - sie liegt INNERHALB von zeichnen=. Sonst zaehlte man sie
# doppelt, und der Rest waere dauerhaft null, egal was fehlt.
# Gezaehlt werden die EINTRAEGE, nicht die Kommas: in
# getattr(self, "_perf_house", 0) stecken selbst welche. Diese Sorte
# Fehlzaehlung ist mir in dieser Testdatei heute schon dreimal
# passiert - nach dem Zeichen gesucht statt nach der Struktur.
_ob = _z[:_z.index("]") + 1]
_eintraege = _ob.count("getattr(") + _ob.count("(_rt1 - _rt0)")
check("nur drei Oberposten: stream, haus, zeichnen",
      _eintraege == 3, "%d Eintraege: %s" % (_eintraege, _ob))
check("bg/restore/rows/art/flip stehen als 'davon'", "davon bg=" in _z,
      "sie sind die Aufteilung von zeichnen, kein eigener Posten")

# ---------------------------------------------------------------------------
print()
print("Test 4: der schnelle Pfad traegt seine Posten selbst ein")
# ---------------------------------------------------------------------------
_nav = quelle[quelle.index("def _draw_navigate_items_impl("):]
_nav = _nav[:_nav.index("\n    def ", 10)]
check("er misst die Boxart-Spalte", "self._perf_art = " in _nav)
check("er misst den Flip", "self._perf_flip = " in _nav)
check("und den Rest seiner eigenen Arbeit als rows",
      "self._perf_rows = " in _nav,
      "sonst landete alles davon im Rest und saehe aus wie ein "
      "unbekannter Verbraucher")
check("die Zeilenzeit zieht Boxart und Flip ab",
      "- getattr(self, \"_perf_art\", 0)" in _nav
      and "- getattr(self, \"_perf_flip\", 0)" in _nav,
      "sonst waeren sie doppelt gezaehlt und der Rest negativ")
check("und wird nicht negativ", "max(0.0," in _nav)

# ---------------------------------------------------------------------------
print()
print("Test 5: die Vorgeschichte steht im Quelltext")
# ---------------------------------------------------------------------------
# Wer in einem Jahr diese Zahlen liest, soll wissen, warum sie einmal
# gelogen haben - und woran man es gemerkt hat.
check("das Zahlenbeispiel aus dem Log ist festgehalten",
      "202 ms busy" in quelle and "85 ms" in quelle)
check("und dass es an die falsche Stelle gefuehrt hat",
      "falsche Stelle" in quelle)

# ---------------------------------------------------------------------------
print()
print("Test 6: Seite 0 wird jetzt auch vermessen (Build 194)")
# ---------------------------------------------------------------------------
# Nach Build 193 stand im Log des Nutzers elfmal hintereinander
# "rest=82" bei 82 ms Gesamtzeit - die Hauptseite war als einzige
# ueberhaupt nicht vermessen. Genau dafuer ist der Rest-Posten da: er
# hat die Luecke selbst gemeldet, statt sie hinter plausiblen Zahlen
# zu verstecken.
_cat = quelle[quelle.index("def _draw_navigate_cats_impl("):]
_cat = _cat[:_cat.index("\n    def ", 10)]
check("der leichte Pfad misst den Hintergrund", "self._perf_bg = " in _cat)
check("die Artbox", "self._perf_art = " in _cat)
check("den Flip", "self._perf_flip = " in _cat)
check("und den Rest seiner Arbeit als rows", "self._perf_rows = " in _cat)
check("die Zeilenzeit zieht die anderen Posten ab",
      _cat.count("- getattr(self, ") >= 3,
      "sonst waeren sie doppelt gezaehlt und der Rest negativ")
check("der Zeitnehmer steht am Anfang der Funktion",
      _cat.index("_tnav = time.monotonic()") < _cat.index("if self.page != 0"),
      "sonst fehlt genau der Teil, der frueh aussteigt")

check("und der VOLLE Aufbau der Hauptseite zaehlt auch mit",
      "_perf_rows" in quelle[quelle.index("def draw_page_cats("):
                            quelle.index("def draw_page_cats(") + 900],
      "er laeuft beim Scrollen und war ebenso unvermessen")

# ---------------------------------------------------------------------------
print()
print("Test 7: EIN TRICHTER statt vieler Pfade (Build 195)")
# ---------------------------------------------------------------------------
# Das Nachruesten einzelner Zeichenwege war eine Tretmuehle: erst
# fehlte Seite 0, dann Raster und Galerie - jedes Mal stand "rest" auf
# der vollen Zeit, und jedes Mal kam ein weiterer instrumentierter Pfad
# dazu. _perf_profiled_call() ist die Stelle, durch die ALLE laufen,
# und dort wurde ohnehin schon gemessen.
_pc = quelle[quelle.index("def _perf_profiled_call("):]
_pc = _pc[:_pc.index("\n    def ", 10)]
check("der Trichter traegt zeichnen ein", "_perf_zeichnen" in _pc)
# Auch hier die Zuweisungs-ZEILEN zaehlen, nicht das Wort: in
# "self._perf_zeichnen = (getattr(self, \"_perf_zeichnen\", 0) + _dt)"
# steht es zweimal.
_zuw = [z for z in _pc.splitlines()
        if z.strip().startswith("self._perf_zeichnen =")]
check("und zwar in BEIDEN Zweigen", len(_zuw) == 2,
      "%d Zuweisungen - mit DRAGEND_PROFILE=1 laeuft der andere"
      % len(_zuw))
check("zeichnen steht in PERF_POSTEN", "_perf_zeichnen" in F.PERF_POSTEN,
      "sonst bliebe es ueber Aktionen hinweg stehen")

# Alle vier zentralen Wege gehen wirklich durch den Trichter.
for name in ("draw_page_cats", "draw_page_items",
             "_draw_navigate_cats", "_draw_navigate_items"):
    _blk = quelle[quelle.index("def %s(self" % name):]
    _blk = _blk[:_blk.index("\n    def ", 10)]
    check("%s laeuft durch den Trichter" % name,
          "_perf_profiled_call" in _blk)

# ---------------------------------------------------------------------------
print()
print("Test 8: vsync= in der Zeile (Build 214)")
# ---------------------------------------------------------------------------
# WARUM DAS DAZUKOMMT. "flip=50" ist zweierlei in einer Zahl: die Kopie
# in den Bildspeicher UND das Warten auf den naechsten Bildwechsel. Das
# hat in diesem Projekt schon zweimal zu einer falschen Schlussfolgerung
# gefuehrt - man sieht eine grosse Zahl und verdaechtigt die Kopie,
# waehrend die Haelfte davon Stillstand ist. Mit dem Ausweis daneben ist
# die Frage "kopieren oder warten?" in der Zeile beantwortet.
check("die Zeile nennt das Warten getrennt", "(davon vsync=%.0f)" in quelle,
      "sonst stecken Kopie und Warten in einer Zahl")
check("und es steht INNERHALB von flip, nicht daneben",
      quelle.index("flip=%.0f") < quelle.index("(davon vsync=%.0f)"),
      "'davon' sagt genau das - kein eigener Posten, kein doppeltes Zaehlen")

_z8 = quelle[quelle.index("_oben = [(_rt1 - _rt0)"):]
_z8 = _z8[:_z8.index("self.page]))") + 20]
check("der Wert kommt vom Framebuffer, nicht aus einer eigenen Uhr",
      "vsync_ms_und_zuruecksetzen()" in _z8,
      "nur dort steht das Warten - hier waere es geschaetzt")
check("er wird beim Abholen zurueckgesetzt",
      "_vsync_ms = self.fb.vsync_ms_und_zuruecksetzen()" in _z8,
      "sonst zaehlte die naechste Zeile das Warten dieser mit")
check("und das Abholen steht VOR dem Logaufruf, nicht darin",
      _z8.index("_vsync_ms = self.fb") < _z8.index("_vsync_ms,"),
      "in der Format-Zeile wuerde es nur beim Loggen zurueckgesetzt - der "
      "Zaehler wuechse zwischen zwei Rucklern unbemerkt an")
check("ein fehlendes Attribut bringt die Zeile nicht um",
      "except AttributeError:" in _z8,
      "die Attrappen der Tests ersetzen den Framebuffer komplett")

# Und die andere Haelfte: der Framebuffer muss das ueberhaupt zaehlen.
fbq = io.open(os.path.join(_REPO, "frontend", "fe", "framebuffer.py"),
              encoding="utf-8").read()
check("_wait_vsync() summiert die Wartezeit auf", "_vsync_summe" in fbq)
check("und es gibt genau einen Abholer",
      fbq.count("def vsync_ms_und_zuruecksetzen") == 1)

_fb = H.make_frontend(page=1).fb
check("frisch ist der Zaehler null", _fb.vsync_ms_und_zuruecksetzen() == 0.0)
_fb._vsync_summe = 0.012
check("er rechnet in Millisekunden",
      abs(_fb.vsync_ms_und_zuruecksetzen() - 12.0) < 1e-9)
check("und ist danach wieder leer", _fb.vsync_ms_und_zuruecksetzen() == 0.0,
      "zweimal abholen darf nicht zweimal dieselbe Zahl geben")
# Auf einem Geraet OHNE Vsync (und in diesem Pruefstand) darf nichts
# dazukommen - sonst stuende in der Zeile eine Wartezeit, die es nie gab.
_fb._wait_vsync()
check("ohne Vsync-Unterstuetzung bleibt er bei null",
      _fb.vsync_ms_und_zuruecksetzen() == 0.0,
      "hier schlaegt der ioctl fehl, also gibt es auch kein Warten")

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
