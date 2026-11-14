#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Die Speicherbereinigung: eingefroren und endlich gemessen (Build 320).

DER ANLASS: "ab und an gibt es immer noch haenger beim scrollen egal
in welche richtung".

Abschnitt J seines Bench vom 13.11. zeigt Ausreisser OHNE Vollbild -
einzelne Schritte, die ein Vielfaches dauern, obwohl der Zeichenweg
derselbe war. Dann liegt es an etwas neben dem Zeichnen, das auf
demselben Faden laeuft. Pythons Speicherbereinigung ist so etwas, und
das Frontend hat sie bis hierher weder angefasst noch gemessen.

Build 320 friert den stehenden Bestand ein (gc.freeze()) - und sagt
dazu, dass NICHT gemessen ist, ob die Haenger daher kommen. Deshalb
gehoert zu der Aenderung die Messung: Abschnitt N im Bench und eine
Zeile im Log.

WAS DIESER TEST SICHERT:
  1. speicherbereinigung_einfrieren() nimmt den Bestand wirklich aus
     der Betrachtung - gezaehlt an den Objekten, nicht gestoppt,
  2. speicherbereinigung_stand() zaehlt die Sammlungen je Stufe,
  3. eingefroren wird nach JEDEM Aufbau des Spielebaums, im Leerlauf,
     genau einmal,
  4. gc_lauf() sieht jede Sammlung, mit Stufe und Dauer, und nimmt
     seinen Haken wieder ab - auch wenn die Arbeit wirft,
  5. Abschnitt N laeuft durch, nennt beide Faelle und hinterlaesst
     die Speicherbereinigung, wie er sie vorgefunden hat,
  6. lauf() faehrt Abschnitt N mit eigenem Fangnetz, und die
     RUCKLER-Zeile im Log nennt die Sammlungen.

Ausfuehren:
    python3 tools/test_gc_messung.py
"""
import contextlib
import gc
import io
import os
import sys
import time

_ECHTE_UHR = time.monotonic

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
sys.path.insert(0, _HIER)

if not os.environ.get("DRAGEND_LIB"):
    for _k in (os.path.join(_REPO, "frontend", "c", "libdragend_x86.so"),
               os.path.join(_REPO, "frontend", "libdragend_x86.so")):
        if os.path.exists(_k):
            os.environ["DRAGEND_LIB"] = _k
            break

import _harness as H                                     # noqa: E402

fm = H.fm
import fe.art as A                                       # noqa: E402
import fe.bench as B                                     # noqa: E402
import fe.settings as S                                  # noqa: E402
from _quelle import koerper, nur_code                    # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


print(__doc__.strip().split("\n")[0])
print()

_Q = open(os.path.join(_REPO, "frontend", "frontend.py"),
          encoding="utf-8").read()
_QB = open(os.path.join(_REPO, "frontend", "fe", "bench.py"),
           encoding="utf-8").read()

# ---------------------------------------------------------------------------
print("Test 1: Einfrieren nimmt den Bestand aus der Betrachtung")
# ---------------------------------------------------------------------------
gc.unfreeze()
gc.collect()
# Ein Bestand, den die Bereinigung verwalten MUSS: Listen sind immer
# verwaltet (anders als Tupel aus Zeichenketten).
bestand = [[i, [i]] for i in range(20000)]
vor = len(gc.get_objects())
check("vor dem Einfrieren ist nichts eingefroren",
      gc.get_freeze_count() == 0)
n = fm.speicherbereinigung_einfrieren()
nach = len(gc.get_objects())
check("die Rueckgabe ist die Zahl der eingefrorenen Objekte",
      n == gc.get_freeze_count() and n >= 40000, n)
check("im Blick der Bereinigung bleibt fast nichts",
      nach < vor // 20, "%d statt %d" % (nach, vor))
check("der Bestand selbst ist unberuehrt",
      len(bestand) == 20000 and bestand[19999] == [19999, [19999]])
# Was eingefroren ist, wird trotzdem freigegeben, sobald niemand mehr
# darauf zeigt - das macht die Referenzzaehlung.
import weakref                                           # noqa: E402


class _Ding(object):
    pass


d = _Ding()
ref = weakref.ref(d)
fm.speicherbereinigung_einfrieren()
del d
check("ein eingefrorenes Objekt ohne Verweis wird weiter freigegeben",
      ref() is None)
del bestand
gc.unfreeze()
check("Gegenprobe: nach unfreeze() ist nichts mehr eingefroren",
      gc.get_freeze_count() == 0)
_alt_freeze = gc.freeze
gc.freeze = lambda: 1 // 0
try:
    check("kann nicht eingefroren werden, kommt -1 und keine Ausnahme",
          fm.speicherbereinigung_einfrieren() == -1)
finally:
    gc.freeze = _alt_freeze

# ---------------------------------------------------------------------------
print()
print("Test 2: der Stand zaehlt die Sammlungen je Stufe")
# ---------------------------------------------------------------------------
a = fm.speicherbereinigung_stand()
gc.collect(0)
gc.collect(2)
gc.collect(2)
b_ = fm.speicherbereinigung_stand()
check("drei Zahlen", len(a) == 3 and all(isinstance(x, int) for x in a), a)
check("eine Sammlung der Stufe 0 und zwei der Stufe 2 sind gezaehlt",
      b_[0] - a[0] >= 1 and b_[2] - a[2] == 2, (a, b_))

# ---------------------------------------------------------------------------
print()
print("Test 3: eingefroren wird nach jedem Aufbau, im Leerlauf, einmal")
# ---------------------------------------------------------------------------
_bc = koerper(_Q, "build_categories", "Frontend")
_erste = [z.strip() for z in nur_code(_bc).splitlines()[1:] if z.strip()]
check("build_categories() vermerkt es als ERSTES (die Methode hat "
      "mehrere Ausgaenge)",
      _erste and _erste[0] == "self._gc_einfrieren_faellig = True",
      _erste[:1])
_na = nur_code(koerper(_Q, "next_action", "Frontend"))
_i = _na.find('getattr(self, "_gc_einfrieren_faellig", False)')
check("der Leerlauf-Zweig fragt den Vermerk ab", _i > 0)
_stueck = _na[_i:_i + 400]
check("setzt ihn VOR dem Einfrieren zurueck - also genau einmal je "
      "Aufbau", 0 < _stueck.find("self._gc_einfrieren_faellig = False")
      < _stueck.find("speicherbereinigung_einfrieren()"))
check("und schreibt die Zahl ins Log",
      'LOG("GC: %d Objekte eingefroren"' in _stueck)
# Der Vermerk liegt im Leerlauf - hinter derselben Frage wie alle
# andere Hintergrundarbeit, nicht im Zeichenweg.
for _name in ("_draw_page_items_impl", "_draw_page_cats_impl",
              "_draw_navigate_items_impl", "_draw_navigate_cats_impl"):
    check("%s friert nicht ein" % _name,
          "speicherbereinigung_einfrieren" not in koerper(_Q, _name,
                                                          "Frontend"))
# Und am Objekt: ein frisches Frontend hat den Vermerk gesetzt.
H.set_screen(1920, 1080)
f = H.make_frontend(page=0)
A.ART.auslagern = None
f._gc_einfrieren_faellig = False
try:
    f.build_categories()
    _gebaut = True
except Exception as e:                                   # noqa: BLE001
    _gebaut = "%s: %s" % (type(e).__name__, e)
check("nach build_categories() steht der Vermerk",
      f._gc_einfrieren_faellig is True, _gebaut)

# ---------------------------------------------------------------------------
print()
print("Test 4: gc_lauf() sieht jede Sammlung")
# ---------------------------------------------------------------------------
vorher = list(gc.callbacks)


def _arbeit():
    gc.collect(0)
    gc.collect(1)
    gc.collect(2)
    gc.collect(2)


war_an = gc.isenabled()
gc.disable()                 # keine zufaellige Sammlung dazwischen
try:
    erg = B.gc_lauf(_arbeit)
    leer = B.gc_lauf(lambda: None)
finally:
    if war_an:
        gc.enable()
check("je Stufe die richtige Zahl", erg["laeufe"] == [1, 1, 2],
      erg["laeufe"])
check("je Stufe eine Dauer, zusammen nicht laenger als die Arbeit",
      all(x >= 0.0 for x in erg["gc_ms"])
      and 0.0 < sum(erg["gc_ms"]) <= erg["ms"] + 0.5,
      "%s in %.3f ms" % (["%.3f" % x for x in erg["gc_ms"]], erg["ms"]))
check("die laengste Sammlung ist benannt, mit Stufe",
      erg["laengste"] is not None and erg["laengste"][1] in (0, 1, 2)
      and erg["laengste"][0] <= sum(erg["gc_ms"]) + 1e-9, erg["laengste"])
check("ohne Sammlung: Nullen und keine laengste",
      leer["laeufe"] == [0, 0, 0] and leer["laengste"] is None, leer)
check("der Haken ist wieder abgenommen", gc.callbacks == vorher,
      len(gc.callbacks))


def _wirft():
    raise RuntimeError("mitten in der Arbeit")


try:
    B.gc_lauf(_wirft)
    _geworfen = False
except RuntimeError:
    _geworfen = True
check("wirft die Arbeit, kommt die Ausnahme durch - und der Haken ist "
      "trotzdem weg", _geworfen and gc.callbacks == vorher)

# ---------------------------------------------------------------------------
print()
print("Test 5: Abschnitt N laeuft durch und raeumt auf")
# ---------------------------------------------------------------------------


def _mit_spielen(fe, n=300):
    _nm, node, _sk = fe.cats[0]
    node["items"] = [("Spiel Nummer %03d" % i, "game",
                      ("/f/%d.sfc" % i, ".sfc", "SNES", None, None))
                     for i in range(n)]
    node.pop("_display_items_cache", None)


def abschnitt_n(vorher_eis):
    H.set_screen(1920, 1080)
    fe = H.make_frontend(page=0)
    A.ART.auslagern = None
    _mit_spielen(fe)
    fe.page, fe.cat_i, fe.item_i = 0, 0, 0
    gc.unfreeze()
    if vorher_eis:
        gc.freeze()
    eis = gc.get_freeze_count()
    ber = B.Bericht()
    gefroren = fm.time.monotonic
    fm.time.monotonic = _ECHTE_UHR
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            B._abschnitt_n(ber, fe, S, A, fm)
    finally:
        fm.time.monotonic = gefroren
    return ber.text(), fe, eis


text, fe, _eis = abschnitt_n(False)
check("die Ueberschrift steht da",
      " N  Speicherbereinigung - ohne und mit Einfrieren" in text)
check("kein Abbruch, keine Ausrede", "--" not in text.replace(
    "-" * 62, ""), [z for z in text.splitlines() if "--" in z
                    and set(z.strip()) != {"-"}][:2])
for marke in ("Schwellen (Stufe 0/1/2)", "Eingefroren beim Eintritt",
              "Verwaltete Objekte", "davon nach dem Einfrieren noch im Blick",
              "Eine VOLLE Sammlung", "120 Scrollschritte, Liste liste",
              "ZU LESEN ALS"):
    check("im Bericht: %s" % marke, marke in text)
_ohne = [z for z in text.splitlines() if z.strip().startswith("ohne ")]
_mit = [z for z in text.splitlines() if z.strip().startswith("mit ")]
check("beide Faelle stehen je zweimal da (volle Sammlung, Scroll-Lauf)",
      len(_ohne) == 2 and len(_mit) == 2, (len(_ohne), len(_mit)))
check("der Scroll-Lauf nennt Schritte, Sammlungen und ihre Zeit",
      any("ms/Schritt" in z and "Sammlungen" in z and "darin" in z
          for z in _ohne) and any("ms/Schritt" in z for z in _mit))
import re                                                # noqa: E402
_m = re.search(r"im Blick\s+(\d+)\s+\((\d+) im Eis\)", text)
_v = re.search(r"Verwaltete Objekte\s+(\d+)", text)
check("eingefroren ist fast alles: im Blick bleibt ein Bruchteil",
      _m and _v and int(_m.group(1)) < int(_v.group(1)) // 10
      and int(_m.group(2)) >= int(_v.group(1)) * 9 // 10,
      (_v.group(1) if _v else None, _m.groups() if _m else None))
check("war vorher nichts eingefroren, ist es danach auch nichts",
      gc.get_freeze_count() == 0, gc.get_freeze_count())
check("die Speicherbereinigung laeuft danach wie vorher",
      gc.isenabled())
check("Seite, Kategorie und Zeiger stehen wieder wie vorher",
      (fe.page, fe.cat_i, fe.item_i) == (0, 0, 0)
      and list(fe.nav_path) == [], (fe.page, fe.cat_i, fe.item_i))
check("kein Haken bleibt haengen", gc.callbacks == vorher)

text2, _fe2, eis2 = abschnitt_n(True)
check("war vorher eingefroren, bleibt es das",
      eis2 > 0 and gc.get_freeze_count() > 0,
      "%d vorher, %d danach" % (eis2, gc.get_freeze_count()))
check("und der Bericht nennt den Stand beim Eintritt",
      ("Eingefroren beim Eintritt                  %d Objekte" % eis2)
      in text2)
gc.unfreeze()

# Ohne Kategorie mit Eintraegen: eine Zeile, kein Absturz.
H.set_screen(1920, 1080)
fe3 = H.make_frontend(page=0)
for _c in fe3.cats:
    _c[1]["items"] = []
    _c[1]["folders"] = {}
    _c[1].pop("_display_items_cache", None)
ber3 = B.Bericht()
with contextlib.redirect_stdout(io.StringIO()):
    B._abschnitt_n(ber3, fe3, S, A, fm)
check("ohne Eintraege: eine ehrliche Zeile statt einer Zahl",
      "-- keine Kategorie mit Eintraegen" in ber3.text())

# ---------------------------------------------------------------------------
print()
print("Test 6: eingetragen im Lauf und im Log")
# ---------------------------------------------------------------------------
_lauf = nur_code(koerper(_QB, "lauf"))
check("lauf() ruft _abschnitt_n()", "_abschnitt_n(" in _lauf)
check("nach Abschnitt M", 0 < _lauf.find("_abschnitt_m(")
      < _lauf.find("_abschnitt_n("))
check("mit eigenem Fangnetz", "ABSCHNITT N ABGEBROCHEN" in _lauf)
check("die Bench-Nummer ist mitgewachsen", B.BENCH_VERSION >= 21,
      B.BENCH_VERSION)
_n = koerper(_QB, "_abschnitt_n")
check("Abschnitt N stellt den Zustand im finally zurueck",
      "finally:" in _n and "gc.unfreeze()" in _n.split("finally:")[-1])
check("die RUCKLER-Zeile nennt die Sammlungen seit der vorigen",
      "RUCKLER-GC: Sammlungen seit der vorigen" in _Q
      and "speicherbereinigung_stand()" in _Q)

print()
if fails:
    print("ROT: %d Pruefung(en) fehlgeschlagen:" % len(fails))
    for f_ in fails:
        print("   - " + f_)
    sys.exit(1)
print("ALLES GRUEN")
