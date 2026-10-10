#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Die Ruckler-Zeile verliert ihre Posten nicht mehr (Build 251).

DER ANLASS, und er ist unangenehm, weil es MEIN Messwerkzeug war. Aus
dem Log des Nutzers vom 09.10. stehen diese zwei Zeilen zu DEMSELBEN
Zeichenschritt untereinander:

    PERF split: bg=0 restore=3 rows=9(17) art=107 flip=16 ms
    RUCKLER:   142 ms busy (... restore=0 rows=9 art=0 flip=16 ...)

107 gegen 0, und 3 gegen 0. draw_page_items() hat am Ende
self._perf_art und self._perf_restore auf null gesetzt - nachdem die
PERF-Zeile sie benutzt hatte, aber BEVOR die RUCKLER-Zeile in run() sie
liest. Der groesste Posten des Schritts stand damit als 0 da und
versteckte sich im "zeichnen=142".

WAS DAS GEKOSTET HAT: ich habe aus "art=0" geschlossen, die
Coverarbeit koenne es nicht sein, und bin ueber vier Vermutungen
gelaufen (Rueckkopplung beim Ueberspringen, falscher Cache-Schluessel,
fehlende JPEG-Miniaturen) - bis die Bilanzzeile 100 % Treffer meldete
und die PERF-Zeile daneben 107 ms Coverarbeit. Es war von Anfang an das
Cover.

UND ES IST EINE WIEDERHOLUNG. Build 193 hat genau diese Klasse Fehler
schon einmal behoben, damals andersherum: die Posten behielten einen
ALTEN Wert vom letzten Vollaufbau. Im Docstring von
_perf_zuruecksetzen() steht seitdem der Satz, der auch hier gilt:

    "Ein Messwerkzeug, das plausibel aussieht und nicht stimmt, ist
    schlimmer als keines."

DER ZWEITE FEHLER, aus denselben Zeilen:

    flip=16 (davon vsync=53)
    flip=27 (davon vsync=644)

"Davon" kann nicht groesser sein als das Ganze. Das Warten kommt als
SUMME ueber den Schritt (fb.vsync_ms_und_zuruecksetzen()), flip stand
dagegen auf dem letzten Aufruf. Jetzt summieren beide ueber denselben
Zeitraum.

GEPRUEFT WIRD DESHALB

  1. Es gibt genau EINE Stelle, die die Posten nullt.
  2. Nach einem Vollaufbau sind art und restore noch lesbar.
  3. Zwei Aufbauten in einem Schritt summieren sich, statt sich zu
     ueberschreiben.
  4. _perf_zuruecksetzen() nullt wirklich alle Posten.
  5. Die Summe der Posten uebersteigt "zeichnen" nicht.

Ausfuehren:
    python3 tools/test_ruckler_posten.py
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H                                        # noqa: E402

fm = H.fm

# DIE UHR MUSS LAUFEN, sonst misst dieser Test nichts.
#
# tools/_harness.py friert time.monotonic() auf NOW = [1000.0] ein, und
# das ist fuer die Zeichentests richtig: eine kuenstliche Uhr macht aus
# Zeitfenstern (COVER_SETTLE, Attract-Modus, Tastenwiederholung)
# vorhersagbare Faelle. Nur messen kann man damit nicht - jedes
# "time.monotonic() - _t0" ist exakt 0, und genau diese Nullen pruefen
# wir hier.
#
# Dasselbe macht tools/test_bench.py, aus demselben Grund. Gesetzt wird
# die echte Uhr direkt im Modul des Frontends, nicht global: andere
# Tests, die dieselbe Datei importieren, sollen ihre kuenstliche Uhr
# behalten.
import time as _zeit                                       # noqa: E402
fm.time.monotonic = _zeit.perf_counter

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_QF = io.open(os.path.join(_REPO, "frontend", "frontend.py"),
              encoding="utf-8").read()
_CODE = "\n".join(z for z in _QF.split("\n")
                  if not z.strip().startswith("#"))
fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


# ---------------------------------------------------------------------------
print("Test 1: genau eine Stelle nullt die Posten")
# ---------------------------------------------------------------------------
# DAS IST DIE EIGENTLICHE ZUSAGE. Zwei Stellen, die denselben Zaehler
# zuruecksetzen, sind eine zu viel - dieselbe Regel, die bei
# vsync_ms_und_zuruecksetzen() ausdruecklich im Docstring steht.
for _name in ("_perf_art", "_perf_restore", "_perf_bg", "_perf_rows",
              "_perf_flip"):
    _nullungen = (_CODE.count("self.%s = 0\n" % _name)
                  + _CODE.count("self.%s = 0.0\n" % _name))
    check("%s wird nirgends einzeln genullt" % _name, _nullungen == 0,
          "%d Stellen gefunden - genullt wird in _perf_zuruecksetzen()"
          % _nullungen)

_blk = _CODE.split("def _perf_zuruecksetzen")[1].split("\n    def ")[0]
check("_perf_zuruecksetzen() nullt ueber die Liste",
      "for name in self.PERF_POSTEN:" in _blk and "setattr(" in _blk,
      "eine Liste, keine Aufzaehlung - sonst fehlt der naechste Posten")

H.set_screen(1920, 1080)
fe = H.make_frontend(page=1)
_posten = list(fe.PERF_POSTEN)
for _name in ("_perf_art", "_perf_restore", "_perf_bg", "_perf_rows",
              "_perf_flip", "_perf_zeichnen"):
    check("%s steht in PERF_POSTEN" % _name, _name in _posten)

# ---------------------------------------------------------------------------
print()
print("Test 2: nach einem Vollaufbau sind die Posten noch lesbar")
# ---------------------------------------------------------------------------
# GENAU DER FALL AUS DEM LOG: erst zeichnen, dann (wie run() es tut) die
# Posten lesen. Standen sie da auf null, war die Ruckler-Zeile blind.
import fe.art as ART                                        # noqa: E402
import fe.bench as BENCH                                    # noqa: E402


def _liste(f, n=40):
    bi, _bn, _nm = BENCH._groesste_kategorie(f)
    f.page = 1
    f.cat_i = bi
    f.nav_path = []
    _, node, _ = f.cats[f.cat_i]
    node["items"] = [("Spiel %03d" % i, "game",
                      ("/f/%d.sfc" % i, ".sfc", "SNES", None, None))
                     for i in range(n)]
    node.pop("_display_items_cache", None)
    f.item_i = 0
    f.scroll = 0
    f.ansicht_setzen("liste")


def _cover_mit(breite=697, hoehe=729):
    echt = ART.ART.get_scaled
    pix = bytes(bytearray([40, 90, 160, 0])) * breite * hoehe

    def ersatz(quelle, b, h, **k):
        return (breite, hoehe, pix)

    ART.ART.get_scaled = ersatz
    return lambda: setattr(ART.ART, "get_scaled", echt)


_liste(fe)
_zurueck = _cover_mit()
try:
    fe._perf_zuruecksetzen()
    fe._force_full_redraw = True
    fe.draw()
    _art = getattr(fe, "_perf_art", 0)
    _res = getattr(fe, "_perf_restore", 0)
    _bg = getattr(fe, "_perf_bg", 0)
    _rows = getattr(fe, "_perf_rows", 0)
finally:
    _zurueck()

check("art ist nach dem Aufbau nicht null", _art > 0,
      "%.3f ms - genau das stand im Log als 0" % (_art * 1000))
check("und die uebrigen Posten auch nicht",
      _bg > 0 and _rows > 0,
      "bg %.3f, rows %.3f ms" % (_bg * 1000, _rows * 1000))
# restore laeuft nur, wenn es Spuren freizuraeumen gibt - beim
# Vollaufbau nicht zwingend. Geprueft wird deshalb nur, dass er nicht
# WEGGERAEUMT wird; die Zusage dazu steht in Test 1.
check("restore ist eine Zahl und keine Ausnahme",
      isinstance(_res, (int, float)), repr(_res))

# ---------------------------------------------------------------------------
print()
print("Test 3: zwei Aufbauten in einem Schritt summieren sich")
# ---------------------------------------------------------------------------
# DER FALL, DER DIE ZEILE FRUEHER VERFAELSCHT HAT: beim Cover-Nachladen
# wird in EINEM Schritt zweimal gezeichnet. Bisher stand nur der letzte
# Aufbau in der Zeile, und die Summe der Posten lag unter dem gemessenen
# "zeichnen".
_zurueck = _cover_mit()
try:
    fe._perf_zuruecksetzen()
    fe._force_full_redraw = True
    fe.draw()
    _art1 = getattr(fe, "_perf_art", 0)
    fe._force_full_redraw = True
    fe.draw()
    _art2 = getattr(fe, "_perf_art", 0)
finally:
    _zurueck()
check("art waechst beim zweiten Aufbau", _art2 > _art1,
      "%.3f -> %.3f ms" % (_art1 * 1000, _art2 * 1000))
check("und zwar etwa auf das Doppelte", _art2 > _art1 * 1.5,
      "Faktor %.1f - ueberschrieben waere er etwa gleich geblieben"
      % (_art2 / _art1 if _art1 else 0))
# Und nach dem Zuruecksetzen faengt er wieder bei null an.
fe._perf_zuruecksetzen()
check("_perf_zuruecksetzen() setzt ihn wieder auf null",
      getattr(fe, "_perf_art", 0) == 0)

# ---------------------------------------------------------------------------
print()
print("Test 4: flip summiert wie vsync")
# ---------------------------------------------------------------------------
# "flip=16 (davon vsync=53)" war unmoeglich: vsync kam als Summe ueber
# den Schritt, flip als letzter Aufruf.
check("flip wird summiert, nicht ueberschrieben",
      'self._perf_flip = getattr(self, "_perf_flip", 0) + _fdt' in _CODE,
      "sonst ist 'davon vsync' groesser als das Ganze")
check("und vsync wird beim Abholen zurueckgesetzt",
      "vsync_ms_und_zuruecksetzen()" in _CODE,
      "abholen und nullen in einem Schritt - damit beide denselben "
      "Zeitraum meinen")
_fb_q = io.open(os.path.join(_REPO, "frontend", "fe", "framebuffer.py"),
                encoding="utf-8").read()
_vq = _fb_q.split("def vsync_ms_und_zuruecksetzen")[1].split("\n    def ")[0]
check("der Abholer nullt wirklich", "self._vsync_summe = 0.0" in _vq)

# ---------------------------------------------------------------------------
print()
print("Test 5: die Posten uebersteigen 'zeichnen' nicht")
# ---------------------------------------------------------------------------
# Die Gegenprobe auf die Summierung: addiert man zu viel, steht in der
# Zeile ein negativer Rest - und das waere der naechste Messfehler.
_zurueck = _cover_mit()
try:
    fe._perf_zuruecksetzen()
    _t0 = _zeit.perf_counter()
    fe._force_full_redraw = True
    fe.draw()
    _echt = _zeit.perf_counter() - _t0
    _summe = sum(getattr(fe, n, 0) for n in
                 ("_perf_bg", "_perf_restore", "_perf_rows", "_perf_art",
                  "_perf_flip"))
finally:
    _zurueck()
check("die Summe der Posten passt in die gemessene Dauer",
      _summe <= _echt * 1.05,
      "%.1f von %.1f ms" % (_summe * 1000, _echt * 1000))
check("und sie ist nicht null", _summe > 0,
      "%.1f ms" % (_summe * 1000))

# ---------------------------------------------------------------------------
print()
print("Test 6: die Begruendung steht im Quelltext")
# ---------------------------------------------------------------------------
# Ein Fehler, der zweimal auftrat (Build 193 und Build 251), gehoert
# aufgeschrieben - sonst kommt er ein drittes Mal.
check("die beiden Zahlen aus dem Log stehen dabei",
      "art=107" in _QF and "restore=3" in _QF,
      "107 gegen 0 ist die ganze Geschichte")
check("und der Hinweis auf Build 193",
      "Build 193" in _QF.split("def _perf_zuruecksetzen")[1][:4000],
      "dieselbe Klasse Fehler, nur andersherum")

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
