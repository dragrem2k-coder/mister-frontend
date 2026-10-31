#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Die Scrollgeschwindigkeit wirkt wirklich, und der Takt ist ruhig
(Build 302).

WORUM ES GEHT. Der Nutzer hat viermal in Folge dasselbe gemeldet:

    "scrollt immer noch so scheisse !!!!! wie gesagt das war vor
     einigen builds viel besser !! echt mist gebaut wurde da!!"

Und sein Bericht (Bench 16, Abschnitt L, Build 301) sagt in zwei
Tabellen, was los ist. ER HAT RECHT, ABER NICHT AUS DEM GRUND, DEN DIE
LETZTEN BUILDS VERMUTET HABEN - gezeichnet wird nachweislich schneller
als je:

    Rasterschritt Build 216:  67,00 ms     jetzt: 20,32 ms
    Haupt galerie Build 237:  34,15 ms     jetzt: 28,78 ms

Es war also nie das Zeichnen. Es sind ZWEI Fehler in der Frage, WANN
ueberhaupt gefragt wird.

FEHLER 1 - DIE EINGESTELLTE GESCHWINDIGKEIT WAR TOT. Er hat
Scrollgeschwindigkeit 2.00 eingestellt. Aus Abschnitt L:

    Liste raster  (rechts)  Schritt 20,32 ms  noetig 23,37  Boden 40,00
    Haupt raster  (rechts)  Schritt 21,38 ms  noetig 24,59  Boden 40,00
    Haupt liste   (runter)  Schritt 21,81 ms  noetig 25,09  Boden 40,00

Dreimal "noetig" weit unter "Boden": das Geraet zeichnet in 20 ms,
gefragt wird alle 40. 25 Schritte je Sekunde, wo 43 lieferbar waeren.
Ursache ist die letzte Zeile von _tempo_anwenden(), die das Ergebnis
mit max(REPEAT_FLOOR_MIN, ...) wieder auf 40 ms hochzog - und zwar umso
wirksamer, je BILLIGER das Zeichnen wurde. Jede Verbesserung der Builds
296 bis 301 verschwand hinter dieser Zeile.

FEHLER 2 - UND DER BODEN PENDELTE. Massgeblich war ein gleitendes
Mittel mit zwei Fenstern (Build 297). Nachgerechnet mit seinen Zahlen
(Mittel 20,32 ms, groesstes 60,43 ms), bei Tempo 2.0:

    Ruhe 23,37 ms -> EIN Ausreisser -> 46,43 ms (+99 %)
    und 30 billige Schritte, bis es wieder bei 23,37 ms ist

Ein einzelner teurer Schritt verdoppelte also den Abfrageabstand fuer
eine halbe Sekunde. Genau so fuehlt sich "ungleichmaessig" an. Das war
vorher genauso da, nur von der starren 40-ms-Grenze verdeckt (bei
Tempo 1.0: 40,00 -> 46,43 ms). Haette Build 302 nur Fehler 1 behoben,
waere es dadurch SCHLECHTER geworden - deshalb gehoeren beide zusammen.

Seit Build 302 ist massgeblich der zweitgroesste der letzten acht
Messungen: ein hohes Quantil, also tatsaechlich eine Frist, statt eines
Mittelwerts, der per Definition in der Haelfte der Faelle zu knapp ist.

WAS DIESER TEST SICHERT:
  1. die Einstellung wirkt - bei einem billigen Schritt und Tempo 2.0
     liegt der Boden UNTER REPEAT_FLOOR_MIN,
  2. und sie wirkt nie zu weit: nie unter Frist x Reserve, nie unter
     eine Bildperiode, gerechnet an seinen echten Zahlen,
  3. links/rechts in der Liste bleibt unberuehrt - dort ist der Mensch
     die Grenze, nicht die Hardware,
  4. bei Tempo 1.0 aendert sich NICHTS gegenueber Build 301,
  5. hoeheres Tempo ist nie langsamer (kein Knick im Regler),
  6. ein Ausreisser bewegt den Boden gar nicht, zwei schon, und eine
     anhaltende Verlangsamung ist nach zwei Schritten erfasst,
  7. der Bench speist die ECHTEN Luecken ein, nicht den Mittelwert.

Ausfuehren:
    python3 tools/test_scrolltempo_wirkt.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H          # noqa: E402,F401

import fe.input as FI         # noqa: E402
import fe.settings as SE      # noqa: E402
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

# SEINE SECHS ANSICHTEN, WORTGLEICH AUS ABSCHNITT L DES BERICHTS vom
# 31.10. (Bench 16, Build 301). Erfundene Zahlen hatten in diesem
# Projekt schon zweimal die falsche Entscheidung begruendet (Build 300:
# eine PC-Messung als Versprechen) - diese hier sind gemessen.
#   Name, Schritt in ms, Aktion, ist es eine Seitenaktion
ANSICHTEN = (
    ("Haupt liste",   21.81, "down",  False),
    ("Haupt raster",  21.38, "right", False),
    ("Haupt galerie", 30.77, "right", False),
    ("Liste liste",   39.57, "down",  False),
    ("Liste raster",  20.32, "right", False),
    ("Liste galerie", 35.82, "right", False),
)
STUFEN = SE.SCROLL_TEMPO_STUFEN            # (0.5, 0.75, 1.0, 1.5, 2.0)
BILD = 1000.0 / 60.0                       # eine Bildperiode in ms


def boden_ms(ms, act, seite, tempo):
    """Der Boden fuer eine gemessene Schrittdauer - ueber die ECHTE
    Rechnung, nicht ueber eine nachgebaute.

    Eine nachgebaute Formel prueft, ob ich zweimal dasselbe tippen kann.
    Dieses Projekt hat genau daran in Build 298 fuenf Testhelfer
    verloren."""
    inp = FI.InputManager.__new__(FI.InputManager)
    inp.seiten_aktionen = {"left", "right"} if seite else set()
    inp._zeichenzeit = {}
    inp._zeichenproben = {}
    _echt = SE.load_scroll_tempo
    try:
        SE.load_scroll_tempo = lambda: tempo
        for _ in range(FI.REPEAT_MESS_FENSTER):
            inp.zeichenzeit_melden(act, ms / 1000.0)
        return inp._repeat_floor(act) * 1000.0
    finally:
        SE.load_scroll_tempo = _echt


# ---------------------------------------------------------------------------
print("Test 1: die Einstellung wirkt ueberhaupt")
# ---------------------------------------------------------------------------
# DER KERN DES BUILDS. Bis Build 301 kam hier in ALLEN drei billigen
# Ansichten 40,00 ms heraus, bei jeder Stufe ueber 1.0.
wirkungslos = []
for name, ms, act, seite in ANSICHTEN:
    if ms * FI.REPEAT_MESS_RESERVE >= FI.REPEAT_FLOOR_MIN * 1000.0:
        continue              # dort bindet die Messung, nicht das Minimum
    b = boden_ms(ms, act, seite, 2.0)
    if b >= FI.REPEAT_FLOOR_MIN * 1000.0 - 1e-9:
        wirkungslos.append((name, b))
check("bei Tempo 2.0 faellt der Boden unter REPEAT_FLOOR_MIN",
      not wirkungslos,
      "%r" % (wirkungslos,) if wirkungslos else
      "geprueft in jeder Ansicht, deren Schritt billiger als %.0f ms ist"
      % (FI.REPEAT_FLOOR_MIN * 1000.0))

_vorher, _nachher = 40.00, boden_ms(20.32, "right", False, 2.0)
check("Liste raster: aus 40,00 ms werden %.2f ms" % _nachher,
      _nachher < _vorher * 0.65,
      "%.1f statt %.1f Schritte je Sekunde (+%.0f %%) - das ist die "
      "Zeile aus seinem Bericht"
      % (1000.0 / _nachher, 1000.0 / _vorher,
         (_vorher / _nachher - 1) * 100))

# ---------------------------------------------------------------------------
print()
print("Test 2: aber nie schneller, als das Geraet liefert")
# ---------------------------------------------------------------------------
# DIE LEHRE AUS BUILD 93, und die Gegenseite von Test 1. Wer mehr
# anfordert, als gezeichnet werden kann, bekommt keine schnellere
# Liste - der Ueberschuss staut sich, und das ist das gemeldete
# "hakt und zieht nach".
zu_schnell, unter_bild = [], []
for name, ms, act, seite in ANSICHTEN:
    noetig = min(ms * FI.REPEAT_MESS_RESERVE, FI.REPEAT_FLOOR_MAX * 1000.0)
    for tempo in STUFEN:
        b = boden_ms(ms, act, seite, tempo)
        if b + 1e-9 < noetig:
            zu_schnell.append((name, tempo, round(b, 2), round(noetig, 2)))
        if b + 1e-9 < BILD:
            unter_bild.append((name, tempo, round(b, 2)))
check("keine Ansicht x Stufe unterschreitet Frist x Reserve",
      not zu_schnell,
      "%r" % (zu_schnell[:3],) if zu_schnell else
      "%d Ansichten x %d Stufen geprueft, alle mit seinen Messwerten"
      % (len(ANSICHTEN), len(STUFEN)))
check("und keine unterschreitet eine Bildperiode (%.1f ms)" % BILD,
      not unter_bild,
      "%r" % (unter_bild[:3],) if unter_bild else
      "mehr als ein Schritt je Bild ist nicht darstellbar")

# ---------------------------------------------------------------------------
print()
print("Test 3: links/rechts in der Liste bleibt unberuehrt")
# ---------------------------------------------------------------------------
# BEWUSSTE ASYMMETRIE, und sie ist KEIN Versehen: bei einem Seitensprung
# ist nicht die Rechenzeit die Grenze, sondern das Lesen. Wer mehr als
# vier ganze Seiten je Sekunde springt, kann nicht mehr sehen, wo er
# gelandet ist - schnellere Hardware aendert daran nichts. Build 302
# senkt deshalb NUR das Minimum fuer den Einzelschritt.
seitenfehler = []
for tempo in STUFEN:
    for ms in (5.0, 20.0, 48.0):
        b = boden_ms(ms, "right", True, tempo)
        if b + 1e-9 < FI.REPEAT_FLOOR_PAGE * 1000.0:
            seitenfehler.append((tempo, ms, round(b, 2)))
check("eine Seitenaktion faellt nie unter REPEAT_FLOOR_PAGE",
      not seitenfehler,
      "%r" % (seitenfehler[:3],) if seitenfehler else
      "%.0f ms bleiben die harte Grenze, bei jeder Stufe"
      % (FI.REPEAT_FLOOR_PAGE * 1000.0))
check("und langsamer stellen bremst auch die Seite",
      boden_ms(48.0, "right", True, 0.5)
      > boden_ms(48.0, "right", True, 1.0) + 1e-9,
      "%.0f ms gegen %.0f ms"
      % (boden_ms(48.0, "right", True, 0.5),
         boden_ms(48.0, "right", True, 1.0)))

# ---------------------------------------------------------------------------
print()
print("Test 4: bei Tempo 1.0 aendert sich NICHTS")
# ---------------------------------------------------------------------------
# WER NICHTS EINSTELLT, DARF NICHTS MERKEN. Das ist die Zusage, die
# tools/test_listen_kleinzeug.py seit Build 256 festhaelt, und sie
# begrenzt Build 302 auf genau den Fall, fuer den die Einstellung
# gebaut wurde.
abweichung = []
for name, ms, act, seite in ANSICHTEN:
    b = boden_ms(ms, act, seite, 1.0)
    # Die Formel aus Build 301, unveraendert hingeschrieben - hier ist
    # das Nachbauen ausdruecklich der Zweck: es ist die ALTE Fassung,
    # gegen die verglichen wird.
    alt = min(FI.REPEAT_FLOOR_MAX * 1000.0,
              max(FI.REPEAT_FLOOR_MIN * 1000.0,
                  ms * FI.REPEAT_MESS_RESERVE))
    if abs(b - alt) > 1e-9:
        abweichung.append((name, round(b, 2), round(alt, 2)))
check("Tempo 1.0 liefert genau den Wert von Build 301",
      not abweichung,
      "%r" % (abweichung,) if abweichung else
      "alle sechs Ansichten bitgenau wie vorher")

# ---------------------------------------------------------------------------
print()
print("Test 5: der Regler hat keinen Knick")
# ---------------------------------------------------------------------------
# Hoeheres Tempo darf nie LANGSAMER sein als niedrigeres. Eine Grenze,
# die man an einer Stelle einzieht, kann so etwas versehentlich
# erzeugen - und ein Regler, der auf Stufe 2.0 schlechter ist als auf
# 1.5, waere ein Regler, den man besser nicht gebaut haette.
knicke = []
for name, ms, act, seite in ANSICHTEN:
    werte = [boden_ms(ms, act, seite, t) for t in STUFEN]
    for a, b in zip(werte, werte[1:]):
        if b > a + 1e-9:
            knicke.append((name, [round(w, 2) for w in werte]))
            break
check("ueber alle Stufen monoton fallend", not knicke,
      "%r" % (knicke,) if knicke else
      " / ".join("%.2f" % w for w in
                 [boden_ms(20.32, "right", False, t) for t in STUFEN])
      + " ms (Liste raster)")

# ---------------------------------------------------------------------------
print()
print("Test 6: der Takt ist ruhig - ein Ausreisser bewegt nichts")
# ---------------------------------------------------------------------------
# DER ZWEITE HALBE BUILD, und ohne ihn waere der erste ein Rueckschritt:
# je naeher der Boden an der Lieferzeit liegt, desto mehr faellt ein
# Pendeln auf. Seine Zahlen: Mittel 20,32 ms, groesstes 60,43 ms.
MITTEL, AUSREISSER = 0.02032, 0.06043


def _lauf(tempo):
    inp = FI.InputManager.__new__(FI.InputManager)
    inp.seiten_aktionen = set()
    inp._zeichenzeit = {}
    inp._zeichenproben = {}
    _echt = SE.load_scroll_tempo
    try:
        SE.load_scroll_tempo = lambda: tempo
        for _ in range(12):
            inp.zeichenzeit_melden("right", MITTEL)
        ruhe = inp._repeat_floor("right")
        inp.zeichenzeit_melden("right", AUSREISSER)
        spitze = inp._repeat_floor("right")
        return ruhe, spitze
    finally:
        SE.load_scroll_tempo = _echt


for tempo in (1.0, 2.0):
    ruhe, spitze = _lauf(tempo)
    check("Tempo %.1f: ein Ausreisser laesst den Boden unberuehrt" % tempo,
          abs(spitze - ruhe) < 1e-9,
          "%.2f ms -> %.2f ms (bis Build 301: %.2f ms, also %+.0f %%)"
          % (ruhe * 1000, spitze * 1000,
             (MITTEL + (AUSREISSER - MITTEL)
              / FI.REPEAT_MESS_FENSTER_HOCH) * FI.REPEAT_MESS_RESERVE * 1000,
             ((MITTEL + (AUSREISSER - MITTEL) / FI.REPEAT_MESS_FENSTER_HOCH)
              * FI.REPEAT_MESS_RESERVE / ruhe - 1) * 100))

# UND DIE BEIDEN GEGENPROBEN, ohne die "bewegt nichts" auch durch eine
# Mechanik zu bestehen waere, die Messungen einfach ignoriert.
inp = FI.InputManager.__new__(FI.InputManager)
inp.seiten_aktionen = set()
inp._zeichenzeit = {}
inp._zeichenproben = {}
for i in range(16):
    inp.zeichenzeit_melden("right", AUSREISSER if i % 4 == 0 else MITTEL)
check("jeder vierte Schritt teuer -> der Boden steigt",
      inp._repeat_floor("right") > MITTEL * FI.REPEAT_MESS_RESERVE * 2.0,
      "%.2f ms - 25 %% teure Schritte sind ein Zustand, kein Ausreisser"
      % (inp._repeat_floor("right") * 1000))

inp = FI.InputManager.__new__(FI.InputManager)
inp.seiten_aktionen = set()
inp._zeichenzeit = {}
inp._zeichenproben = {}
for _ in range(12):
    inp.zeichenzeit_melden("down", 0.069)      # seine Zahlen aus 297
_schritte = None
for n in range(1, 9):
    inp.zeichenzeit_melden("down", 0.284)
    if inp._repeat_floor("down") >= 0.284 * FI.REPEAT_MESS_RESERVE * 0.95:
        _schritte = n
        break
check("eine anhaltende Verlangsamung ist nach 2 Schritten erfasst",
      _schritte == 2,
      "nach %r Schritten (Build 297 brauchte 3, Build 93 acht)"
      % (_schritte,))

# ---------------------------------------------------------------------------
print()
print("Test 7: am Quelltext - die Grenzen stehen da, wo sie wirken")
# ---------------------------------------------------------------------------
_inp_py = os.path.join(_REPO, "frontend", "fe", "input.py")
_src = open(_inp_py, encoding="utf-8").read()
_tempo_src = nur_code(koerper(_src, "_tempo_anwenden"))
check("_tempo_anwenden() kennt REPEAT_FLOOR_BILD",
      "REPEAT_FLOOR_BILD" in _tempo_src,
      "sonst zieht REPEAT_FLOOR_MIN das Ergebnis wieder hoch")
check("und senkt das Minimum nur bei hoeherem Tempo",
      "faktor > 1.0" in _tempo_src,
      "bei 1.0 darf sich nichts aendern")
check("und nur fuer den Einzelschritt, nicht fuer die Seite",
      "not seite" in _tempo_src,
      "die Seitengrenze ist eine menschliche, keine technische")
check("die harte Grenze traegt weiter die Reserve",
      "gemessen * REPEAT_MESS_RESERVE" in _tempo_src,
      "der nackte Messwert war der Fehler von Build 300")

_melden = nur_code(koerper(_src, "zeichenzeit_melden"))
check("zeichenzeit_melden() rechnet kein gleitendes Mittel mehr",
      "REPEAT_MESS_FENSTER_HOCH" not in _melden
      and "_zeit_aus_proben" in _melden,
      "die beiden Fenster sind durch ein Quantil ersetzt")

_quantil = nur_code(koerper(_src, "_zeit_aus_proben"))
check("und das Quantil nimmt bei zu wenigen Proben den groessten Wert",
      "max(proben)" in _quantil,
      "zu langsam fragen merkt niemand, zu schnell ist der Fehler")

# ---------------------------------------------------------------------------
print()
print("Test 8: der Bench misst die neue Groesse auch")
# ---------------------------------------------------------------------------
# EIN ACHTMAL WIEDERHOLTER MITTELWERT HAT KEINE STREUUNG. Solange der
# Boden an einem Mittel hing, war das gleichgueltig; seit Build 302
# wuerde der Bericht damit genau die Groesse verschweigen, um die es
# geht. Das ist dieselbe Sorte Fehler wie der in Build 301 behobene:
# ein Wert, den man nicht zurueckrechnen kann, ist keine Messung.
_bench_py = os.path.join(_REPO, "frontend", "fe", "bench.py")
_bsrc = open(_bench_py, encoding="utf-8").read()
_l = nur_code(koerper(_bsrc, "_abschnitt_l"))
check("Abschnitt L speist die echten Luecken ein",
      "for _l in luecken[-_fenster:]" in _l,
      "nicht mehr den Mittelwert, so oft wie das Fenster lang ist")
check("und sichert die Proben beim Umhaengen",
      "_vorher_zp" in _l and "inp._zeichenproben = {}" in _l,
      "sonst zaehlen die Werte der vorigen Ansicht mit")
check("und berichtet die Frist neben dem Mittel",
      "frist" in _l and '"Frist"' in _l,
      "Frist gegen Mittel ist das Mass fuer die Gleichmaessigkeit")

# ---------------------------------------------------------------------------
print()
if fails:
    print("FEHLGESCHLAGEN (%d):" % len(fails))
    for f in fails:
        print("  - %s" % f)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
