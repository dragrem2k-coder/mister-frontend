#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scrollgeschwindigkeit 3x und 4x: Zeilensprung beim Halten (Build 337).

NUTZERWUNSCH: "wir koennen ja die scrollgeschwindigkeit einstellen ...
und diese auf 2X stellen. koennen wir das noch schneller machen?"

Die Rate bleibt an die gemessene Zeichendauer gebunden (Build 93 - wer
schneller fragt, als gezeichnet wird, bekommt Stau und Nachlauf).
Schneller wird es auf 3x/4x durch die WEITE: ein Wiederholschritt im
Endtempo springt mehrere Zeilen.

GEPRUEFT WIRD:
  1. Die Stufen: 3x und 4x gibt es, umlaufend, mit Beschriftung.
  2. Die Weite: bis 2x immer 1; auf 3x/4x bei angeschlagener Rate 3/4
     Zeilen, bei billigem Zeichnen weniger; nie links/rechts, nie bei
     Seitenspruengen, nie ohne Messung; das Intervall unterschreitet
     auch auf 3x/4x nie die gemessene Zeit mit Reserve.
  3. read_action(): der erste Druck ist 1 weit, eine Wiederholung im
     Anlauf auch, erst im Endtempo springt sie; abgeholt wird einmal.
  4. nav_anwenden(): springt um die Weite, haelt am Listenende an,
     laeuft erst von dort wie bisher herum; ohne Weite wie bisher.

Ausfuehren:
    python3 tools/test_scrolltempo_sprung.py
"""
import io
import os
import sys
import time

_HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HIER)

import _harness as H                                     # noqa: E402

fm = H.fm
import fe.input as FI                                    # noqa: E402
import fe.settings as SE                                 # noqa: E402
import fe.translations as TR                             # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


def eingabe():
    inp = FI.InputManager.__new__(FI.InputManager)
    inp.seiten_aktionen = set()
    inp._zeichenzeit = {}
    return inp


print(__doc__.strip().split("\n")[0])
print()
_echt_tempo = SE.load_scroll_tempo
_lang = TR.CURRENT_LANG
try:
    TR.CURRENT_LANG = "de"
    # -----------------------------------------------------------------------
    print("Test 1: die Stufen")
    # -----------------------------------------------------------------------
    check("3x und 4x sind da, 2x bleibt",
          {2.0, 3.0, 4.0} <= set(SE.SCROLL_TEMPO_STUFEN)
          and SE.SCROLL_TEMPO_STUFEN[-1] == 4.0, SE.SCROLL_TEMPO_STUFEN)
    check("aufsteigend sortiert (Umlauf im Menue)",
          list(SE.SCROLL_TEMPO_STUFEN) == sorted(SE.SCROLL_TEMPO_STUFEN))
    check("Beschriftung", fm.t("sys_scroll_tempo", "4x")
          == "Scrollgeschwindigkeit: 4x -> nächste")

    # -----------------------------------------------------------------------
    print()
    print("Test 2: die Weite")
    # -----------------------------------------------------------------------
    def weite(faktor, ms, act="down", seite=False):
        inp = eingabe()
        if seite:
            inp.seiten_aktionen = {act}
        if ms is not None:
            inp._zeichenzeit = {act: ms / 1000.0}
        SE.load_scroll_tempo = lambda f=faktor: f
        iv = inp._repeat_floor(act)
        return inp._sprung_je_akt.get(act), iv

    for f in (0.5, 1.0, 1.5, 2.0):
        check("Stufe %gx: immer 1 Zeile" % f,
              all(weite(f, ms)[0] == 1 for ms in (5, 20, 40, 100)))
    check("3x, Rate angeschlagen (40 ms je Schritt): 3 Zeilen",
          weite(3.0, 40)[0] == 3, weite(3.0, 40))
    check("4x, Rate angeschlagen: 4 Zeilen", weite(4.0, 40)[0] == 4)
    check("3x, billiges Zeichnen (5 ms): die Rate reicht, 1 Zeile",
          weite(3.0, 5)[0] == 1, weite(3.0, 5))
    check("4x, billiges Zeichnen: 2 Zeilen", weite(4.0, 5)[0] == 2,
          weite(4.0, 5))
    check("hoechstens SPRUNG_MAX",
          all(weite(4.0, ms)[0] <= FI.SPRUNG_MAX for ms in (1, 40, 400)))
    check("GEGENPROBE: links/rechts springt nie",
          weite(4.0, 40, "right")[0] == 1 and weite(4.0, 40, "left")[0] == 1)
    check("GEGENPROBE: Seitensprung (Galerie hoch/runter) springt nie",
          weite(4.0, 40, "down", seite=True)[0] == 1)
    check("GEGENPROBE: ohne Messung springt nichts",
          weite(4.0, None)[0] == 1)
    verstoss = []
    for ms in (5.0, 20.32, 39.75, 46.32, 107.08):
        for f in (3.0, 4.0):
            iv = weite(f, ms)[1]
            noetig = min(ms * FI.REPEAT_MESS_RESERVE,
                         FI.REPEAT_FLOOR_MAX * 1000.0) / 1000.0
            if iv + 1e-9 < noetig:
                verstoss.append((ms, f, iv))
    check("das Intervall unterschreitet nie die Messung mit Reserve "
          "(Build 93/301)", not verstoss, verstoss)
    _, iv2 = weite(2.0, 40)
    _, iv4 = weite(4.0, 40)
    check("bei angeschlagener Rate: 4x fragt nicht oefter als 2x, "
          "springt aber weiter", abs(iv2 - iv4) < 1e-9, (iv2, iv4))

    # -----------------------------------------------------------------------
    print()
    print("Test 3: read_action() - erst im Endtempo")
    # -----------------------------------------------------------------------
    SE.load_scroll_tempo = lambda: 4.0
    inp = eingabe()
    inp.devices = {}
    inp.last_scan = time.monotonic() + 3600
    inp._zeichenzeit = {"down": 0.040}
    inp._last_repeat_act = None
    inp._last_repeat_time = 0.0
    inp._last_repeat_iv = FI.REPEAT_INTERVAL
    inp._hold(("p", "k", 1), "down")
    weiten = []
    for _ in range(12):
        kid, act, _f, iv = inp.held
        inp.held = (kid, act, time.monotonic() - 0.001, iv)
        a = inp.read_action(timeout=0.5)
        weiten.append((a, inp.sprung_abholen()))
    check("alle Wiederholungen sind 'down'",
          all(a == "down" for a, _k in weiten), weiten)
    ks = [k for _a, k in weiten]
    check("im Anlauf 1 Zeile, danach 4", ks[0] == 1 and ks[-1] == 4
          and ks == sorted(ks), ks)
    check("abgeholt wird einmal (danach 1)", inp.sprung_abholen() == 1)
    q = open(os.path.join(os.path.dirname(H.FRONTEND_PY), "fe",
                          "input.py"), encoding="utf-8").read()
    i = q.find("def read_action(self, timeout=None):")
    k = q[i:i + 6000]
    check("jede Aktion beginnt mit Weite 1 (vor allem anderen)",
          k.find("self.wiederhol_sprung = 1")
          < k.find('_vor = getattr(self, "_vorgelegt", None)'))

    # -----------------------------------------------------------------------
    print()
    print("Test 4: nav_anwenden()")
    # -----------------------------------------------------------------------
    H.set_screen(1280, 720)
    f = H.make_frontend(page=1)

    class Inp:
        def __init__(self, k):
            self.k = k

        def sprung_abholen(self):
            k, self.k = self.k, 1
            return k

        def gestaute_schritte(self, act, maximal=None):
            return 0
    f.marquee_reset = lambda: None
    items = list(range(20))
    f.page = 1
    f.item_i = 5
    f.inp = Inp(3)
    f.nav_anwenden("down", items, 1)
    check("Weite 3: von 5 auf 8", f.item_i == 8, f.item_i)
    f.nav_anwenden("down", items, 1)
    check("abgeholt: der naechste Schritt ist wieder 1", f.item_i == 9,
          f.item_i)
    f.item_i = 18
    f.inp = Inp(4)
    f.nav_anwenden("down", items, 1)
    check("am Ende: haelt auf dem letzten Eintrag", f.item_i == 19, f.item_i)
    f.inp = Inp(4)
    f.nav_anwenden("down", items, 1)
    check("vom letzten aus: herum auf den ersten (wie bisher)",
          f.item_i == 0, f.item_i)
    f.item_i = 2
    f.inp = Inp(4)
    f.nav_anwenden("up", items, 1)
    check("nach oben: haelt auf dem ersten", f.item_i == 0, f.item_i)
    f.item_i = 4
    f.inp = Inp(1)
    f.nav_anwenden("down", items, 5)
    check("GEGENPROBE: ohne Weite wie bisher (Raster, 5 Spalten)",
          f.item_i == 9, f.item_i)
    f.item_i = 17
    f.nav_anwenden("down", items, 5)
    check("GEGENPROBE: ohne Weite laeuft es herum wie bisher",
          f.item_i == 2, f.item_i)
    class Alt:
        def gestaute_schritte(self, act, maximal=None):
            return 0
    f.inp = Alt()
    f.item_i = 3
    f.nav_anwenden("down", items, 1)
    check("Eingabe ohne sprung_abholen(): 1 Schritt, kein Absturz",
          f.item_i == 4, f.item_i)
finally:
    SE.load_scroll_tempo = _echt_tempo
    TR.CURRENT_LANG = _lang

print()
if fails:
    print("ROT: %d Pruefung(en) fehlgeschlagen:" % len(fails))
    for f_ in fails:
        print("   - " + f_)
    sys.exit(1)
print("ALLES GRUEN")
