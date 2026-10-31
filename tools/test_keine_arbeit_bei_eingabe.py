#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Keine Hintergrundarbeit waehrend aktiver Eingabe (Build 301).

WORUM ES GEHT. Dies ist **Punkt 1 der Prioritaetenliste des Nutzers**,
woertlich: "Keine Hintergrundaufgaben waehrend aktiver Eingabe, wenn sie
die Bedienung bremsen." Und es ist die Erklaerung fuer den Befund, den
er dreimal beschrieben hat:

    "fuehlt sich an als wuerde das frontend immer neu berechnen oder
     nachrechnen was auch immer"

Es rechnet auch - auf dem zweiten Kern. Aus seinem Bericht vom 31.10.
(Build 300):

    Abschnitt C:  Miniatur packen und schreiben     709,73 ms
    Abschnitt B:  "Miniaturen packen und schreiben  202,7 ms (21 x)"
    Abschnitt J:  "_schreib_arbeiter > _thumb_cache_put" MITTEN im
                  Scrollschritt, 0,13 bis 0,31 ms je Schritt
    Abschnitt L:  Raster  Mittel 22,67 ms, groesstes  68,08 ms
                  Galerie Mittel 36,10 ms, groesstes  72,94 ms

Das Mittel ist in Ordnung, die Ausreisser sind es nicht - zwei bis drei
Mal so gross. Genau so fuehlt sich das an: der Zeiger bewegt sich
ungleichmaessig, nicht langsam. Und das Geraet hat zwei Kerne, die sich
dieselbe Speicherbandbreite teilen (Abschnitt H.1: 2,69 ms je MB).

WARUM DAS PAUSIEREN NICHTS KOSTET: waehrend des Scrollens werden noch
nicht gerechnete Cover ohnehin uebersprungen (Build 244). Was der
Arbeiter schreibt, braucht das aktuelle Bild nicht - er arbeitet fuer
spaeter. Dann kann er auch spaeter arbeiten.

WAS DIESER TEST SICHERT:
  1. der Arbeiter pausiert, solange eine Taste gehalten wird,
  2. er nimmt nach dem Loslassen von selbst wieder auf,
  3. er VERHUNGERT NICHT - nach SCHREIB_PAUSE_MAX arbeitet er weiter,
     auch wenn noch gescrollt wird,
  4. eine leere Schlange nach der Pause ist kein Absturz,
  5. es ist DERSELBE Schalter wie bei Covern und Beschreibung,
  6. und der Boden der Wiederholrate liegt nie unter Schritt x Reserve.

Punkt 6 gehoert dazu, weil es derselbe Befund ist: beides fuehrt dazu,
dass mehr angefordert wird als lieferbar.

Ausfuehren:
    python3 tools/test_keine_arbeit_bei_eingabe.py
"""
import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H          # noqa: E402

import fe.art as A            # noqa: E402
import fe.input as FI         # noqa: E402
from _quelle import koerper, nur_code                     # noqa: E402

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

fails = []


def check(name, ok, info=""):
    if ok:
        print("  OK   %s %s" % (name, info))
    else:
        print("  FEHL %s %s" % (name, info))
        fails.append(name)


print(__doc__.strip().split("\n")[0])
print()


class Attrappe:
    """Eine ArtCache-aehnliche Huelle - nur das eine Feld zaehlt."""
    _defer_uncached = False


def navigation(ja):
    """Den Zustand "es wird gerade gescrollt" setzen.

    Gesetzt wird das Feld der registrierten Instanz - genau die Quelle,
    die _navigation_aktiv() liest. Kein zweites Flag."""
    A._aktive_instanz[0].\
        _defer_uncached = bool(ja)


# ---------------------------------------------------------------------------
print("Test 1: die Quelle ist DIESELBE wie bei Covern und Beschreibung")
# ---------------------------------------------------------------------------
quelle = open(os.path.join(_REPO, "frontend", "fe", "art.py"),
              encoding="utf-8").read()
nav = nur_code(koerper(quelle, "_navigation_aktiv"))
check("_navigation_aktiv liest _defer_uncached",
      "_defer_uncached" in nav,
      "ein eigener Merker waere einer, der irgendwann anders antwortet")
check("und holt es von der registrierten Instanz",
      "_aktive_instanz" in nav)
arbeiter = nur_code(koerper(quelle, "_schreib_arbeiter"))
check("der Arbeiter fragt danach", "_navigation_aktiv()" in arbeiter)
check("er wartet MIT Zeitschranke",
      "SCHREIB_PAUSE_TAKT" in arbeiter,
      "das Ende des Scrollens ist kein Ereignis, das hier ankommt - "
      "ein wait() ohne Timeout wuerde verschlafen")
check("und hat eine Obergrenze",
      "SCHREIB_PAUSE_MAX" in arbeiter,
      "wer eine Taste minutenlang haelt, darf das Schreiben nicht "
      "fuer immer aufhalten")
check("nach der Pause wird die Schlange erneut geprueft",
      "if not _schreib_queue:" in arbeiter,
      "sie kann waehrend der Pause geleert worden sein - sonst ein "
      "IndexError, der nur beim Scrollen auftritt")

# ---------------------------------------------------------------------------
print()
print("Test 2: er pausiert wirklich - und nimmt wieder auf")
# ---------------------------------------------------------------------------
# GEMESSEN WIRD AM VERHALTEN, nicht am Quelltext: ein Auftrag wird
# eingestellt, waehrend "gescrollt" wird, und es wird gezaehlt, ob er
# ausgefuehrt wurde. Dazu wird _thumb_cache_put durch einen Zaehler
# ersetzt - der Test schreibt nichts auf die Karte.
A._aktive_instanz[0] = Attrappe()

getan = []
echt_put = A._thumb_cache_put
echt_marke = A._thumb_cache_put_marke


def _put_haken(*a, **k):
    getan.append(time.monotonic())


A._thumb_cache_put = _put_haken
A._thumb_cache_put_marke = _put_haken

# Einen eigenen Arbeiter starten - der echte laeuft ggf. schon und
# haengt an derselben Schlange; ein zweiter wuerde das Ergebnis
# verfaelschen. Deshalb die Schlange vorher leeren.
with A._schreib_lock:
    del A._schreib_queue[:]
    A._schreib_index.clear()
    A._schreib_bytes = 0

faden = threading.Thread(target=A._schreib_arbeiter, daemon=True)
faden.start()
time.sleep(0.05)

try:
    # (a) WAEHREND DER NAVIGATION: der Auftrag muss liegenbleiben.
    navigation(True)
    del getan[:]
    with A._schreib_lock:
        A._schreib_queue.append(("marke", "/tmp/gibt_es_nicht_301", 10, 10))
        A._schreib_lock.notify()
    time.sleep(0.30)
    check("waehrend des Scrollens wird nichts geschrieben",
          len(getan) == 0,
          "%d Auftraege erledigt - jeder kostet auf dem Geraet laut "
          "Abschnitt C bis zu 709 ms" % len(getan))

    # (b) NACH DEM LOSLASSEN: er muss von selbst weitermachen, ohne
    # dass ein neuer Auftrag kommt. Das ist der Grund fuer den
    # Zeitschranken-wait.
    navigation(False)
    for _ in range(40):
        if getan:
            break
        time.sleep(0.02)
    check("nach dem Loslassen laeuft er von selbst weiter",
          len(getan) >= 1,
          "%d Auftraege - ohne Zeitschranke im wait() wuerde er bis "
          "zum naechsten Auftrag schlafen" % len(getan))

    # (c) ER VERHUNGERT NICHT. Wer eine Taste haelt, soll nicht dazu
    # fuehren, dass ueberhaupt nichts mehr geschrieben wird.
    #
    # DIE UHR DIESES PRUEFSTANDS STEHT (H.NOW, siehe _harness.py:
    # time.monotonic wird global ersetzt). Der Arbeiter liest dieselbe
    # Uhr, also laeuft seine Obergrenze hier NIE ab, solange niemand
    # sie weiterstellt - die erste Fassung dieses Tests hat deshalb
    # endlos gewartet. Das ist kein Fehler im Code, sondern eine
    # Eigenschaft des Pruefstands, und der Test muss sie bedienen.
    #
    # Gleichzeitig ist es die Gegenprobe darauf, dass die Obergrenze
    # ueberhaupt an der Uhr haengt: wird sie weitergestellt, muss der
    # Arbeiter weitermachen, OHNE dass das Scrollen endet.
    navigation(True)
    del getan[:]
    with A._schreib_lock:
        A._schreib_queue.append(("marke", "/tmp/gibt_es_nicht_301b", 10, 10))
        A._schreib_lock.notify()
    time.sleep(0.25)
    check("er pausiert weiter, solange die Uhr steht", len(getan) == 0,
          "%d Auftraege" % len(getan))
    # Uhr ueber die Obergrenze hinaus stellen - das Scrollen laeuft
    # ausdruecklich WEITER.
    H.NOW[0] += A.SCHREIB_PAUSE_MAX + 0.5
    with A._schreib_lock:
        A._schreib_lock.notify()
    for _ in range(60):
        if getan:
            break
        time.sleep(0.02)
    check("nach der Obergrenze arbeitet er trotz Scrollen weiter",
          len(getan) >= 1,
          "%d Auftraege - sonst verhungert das Schreiben, solange "
          "jemand eine Taste haelt" % len(getan))
    navigation(False)

    # (d) EINE LEERE SCHLANGE NACH DER PAUSE ist kein Absturz.
    navigation(True)
    with A._schreib_lock:
        A._schreib_queue.append(("marke", "/tmp/gibt_es_nicht_301c", 10, 10))
        A._schreib_lock.notify()
    time.sleep(0.10)
    with A._schreib_lock:
        del A._schreib_queue[:]          # waehrend er pausiert
        A._schreib_index.clear()
        A._schreib_lock.notify()
    navigation(False)
    time.sleep(0.20)
    check("der Faden lebt noch", faden.is_alive(),
          "eine leere Schlange nach der Pause darf ihn nicht umbringen")

    # (e) Der Zaehler ist abfragbar - eine Zahl, die man nicht
    # abfragen kann, ist eine Behauptung.
    anzahl, dauer = A.schreib_pausen_stand()
    check("die Pausen sind abfragbar", anzahl >= 1,
          "%d Pausen, %.2f s gezaehlt" % (anzahl, dauer))
    # Die Dauer haengt an derselben stehenden Uhr - gezaehlt wird hier
    # nur, was durch das Weiterstellen in (c) entstanden ist.
    check("und die Wartezeit wird mitgezaehlt", dauer > 0.0,
          "%.2f s" % dauer)
finally:
    A._thumb_cache_put = echt_put
    A._thumb_cache_put_marke = echt_marke
    navigation(False)
    with A._schreib_lock:
        del A._schreib_queue[:]
        A._schreib_index.clear()
        A._schreib_lock.notify_all()

# ---------------------------------------------------------------------------
print()
print("Test 3: der Boden liegt nie unter Schritt x Reserve")
# ---------------------------------------------------------------------------
# DERSELBE BEFUND, ANDERE STELLE. _tempo_anwenden() hatte als harte
# Grenze den NACKTEN Messwert, womit die Reserve aus Build 93 bei jeder
# Scrollgeschwindigkeit ueber 1,0 verschwand:
#
#   gemessen 39,75 ms -> Boden roh 45,71 ms -> ausgegeben 40,00
#   gemessen 46,32 ms -> Boden roh 53,27 ms -> ausgegeben 46,32
#
# Die zweite Zeile ist der Fehler: gefragt alle 46,32 ms, und genau so
# lange dauert ein Schritt IM MITTEL. Die Haelfte aller Schritte ist
# langsamer - jeder davon staut.
import fe.settings as SE                                 # noqa: E402

inp = FI.InputManager.__new__(FI.InputManager)
inp.seiten_aktionen = set()
_echt_tempo = SE.load_scroll_tempo
verstoesse = []
try:
    # Die Messwerte sind die aus seinem Bericht, nicht erfunden.
    for ms in (10.0, 22.67, 36.10, 39.75, 46.32, 68.08, 107.08):
        noetig = min(ms * FI.REPEAT_MESS_RESERVE,
                     FI.REPEAT_FLOOR_MAX * 1000.0)
        for faktor in (0.5, 1.0, 1.5, 2.0, 3.0):
            SE.load_scroll_tempo = lambda f=faktor: f
            inp._zeichenzeit = {"right": ms / 1000.0}
            boden = inp._repeat_floor("right") * 1000.0
            if boden + 1e-9 < noetig:
                verstoesse.append((ms, faktor, boden, noetig))
finally:
    SE.load_scroll_tempo = _echt_tempo

check("kein Tempo unterschreitet die Reserve", not verstoesse,
      "%r" % (verstoesse[:3],) if verstoesse else
      "7 Messwerte x 5 Tempo-Stufen geprueft")

# Und die Gegenprobe: LANGSAMER muss weiter gehen. Ein Regler, der nur
# noch in eine Richtung wirkt, waere ein toter Regler.
try:
    SE.load_scroll_tempo = lambda: 0.5
    inp._zeichenzeit = {"right": 0.02}
    langsam = inp._repeat_floor("right")
    SE.load_scroll_tempo = lambda: 1.0
    normal = inp._repeat_floor("right")
finally:
    SE.load_scroll_tempo = _echt_tempo
check("langsamer stellen wirkt weiterhin", langsam > normal,
      "%.1f ms gegen %.1f ms" % (langsam * 1000, normal * 1000))

_src = nur_code(koerper(open(os.path.join(_REPO, "frontend", "fe",
                                          "input.py"),
                             encoding="utf-8").read(), "_tempo_anwenden"))
check("die harte Grenze traegt die Reserve",
      "gemessen * REPEAT_MESS_RESERVE" in _src,
      "der nackte Messwert waere der Fehler von Build 300")

# ---------------------------------------------------------------------------
print()
print("Test 4: der Bench weist es aus")
# ---------------------------------------------------------------------------
import fe.bench as B                                      # noqa: E402
_bq = nur_code(koerper(open(os.path.join(_REPO, "frontend", "fe",
                                         "bench.py"),
                            encoding="utf-8").read(), "_abschnitt_l"))
check("Abschnitt L nennt die Pausen des Arbeiters",
      "schreib_pausen_stand" in _bq)
check("und rechnet den Boden nachvollziehbar vor",
      "noetig" in _bq and "REPEAT_MESS_RESERVE" in _bq,
      "ein Wert, den man nicht zurueckrechnen kann, ist keine Messung")
check("der Boden entsteht IN der Messschleife",
      _bq.index("seiten_aktionen") < _bq.index("Scrollgeschwindigkeit"),
      "spaeter nachgeholt stand dort der Zustand der zuletzt "
      "gesetzten Ansicht - 250 ms fuer hoch/runter in der Liste")
check("BENCH_VERSION ist mitgewachsen", B.BENCH_VERSION >= 16,
      "%d - Abschnitt L hat eine neue Spalte und einen Teil 4"
      % B.BENCH_VERSION)

print()
if fails:
    print("FEHLGESCHLAGEN (%d):" % len(fails))
    for f in fails:
        print("  - %s" % f)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
