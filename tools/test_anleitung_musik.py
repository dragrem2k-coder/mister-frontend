#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Die Musik laeuft beim Anleitung-Lesen weiter (Build 354).

NUTZERFRAGE: "Warum laeuft die Musik im Frontend nicht weiter, wenn ich
mir Anleitungen anschaue?" - weil _auf_konsole() fuer JEDES fremde
Programm die Musik anhielt, auch fuer den stummen PDF-Betrachter.

GEPRUEFT WIRD am echten _auf_konsole() (Konsolenwechsel und Bildschirm
sind Attrappen, der Prozess ist echt):
  1. Anleitung (musik_weiter=True): kein Anhalten, kein Fortsetzen, die
     Musik wird im Puls weitergefuehrt (music.tick()), hoechstens einmal
     je MUSIK_TAKT.
  2. Ein Skript: weiter wie bisher - anhalten und danach fortsetzen.
  3. Ohne eigenen Puls (keine Tastatur zum Einspeisen) laeuft die Musik
     trotzdem weiter.
  4. Ein Fehler in der Musik stoert den Betrachter nicht.
  5. anleitung_zeigen() verlangt es, run_script() nicht.

Ausfuehren:
    python3 tools/test_anleitung_musik.py
"""
import os
import sys

_HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HIER)
import _harness as H                                     # noqa: E402

fm = H.fm
fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


class Musik(object):
    def __init__(self, kaputt=False):
        self.log = []
        self.enabled = True
        self.kaputt = kaputt

    def pause_for_core(self):
        self.log.append("pause")

    def resume_after_core(self):
        self.log.append("resume")

    def tick(self):
        self.log.append("tick")
        if self.kaputt:
            raise RuntimeError("Probe")

    def __getattr__(self, n):
        return lambda *a, **k: None


fe = H.make_frontend(page=1)
for _n in ("textkonsole_grafik_aus", "textkonsole_grafik_an",
           "enter_console_mode", "back_to_frontend"):
    setattr(fe, _n, lambda *a, **k: None)
fe.set_cursor_blink = lambda *a: None
fe._konsole_oeffnen = lambda e: (None, None)
fe._zurueck_auf_tty1 = lambda *a: None
# Eine Tastatur zum Einspeisen - sonst verwirft _auf_konsole() den Puls
# des Betrachters (das Pad bliebe bei MiSTer).
import types as _types                                   # noqa: E402
fe.inp.inject_ziel = lambda: _types.SimpleNamespace(
    name="Probe keyboard", path="/dev/null")
fe.inp.grab = lambda *a, **k: None
_echt_mono = fm.time.monotonic
_uhr = [1000.0]


def _mono():
    _uhr[0] += 0.25
    return _uhr[0]


def lauf(musik, **kw):
    fe.music = musik
    fm.time.monotonic = _mono
    try:
        fe._auf_konsole(["sleep", "0.6"], ["sleep", "0.6"], "probe", **kw)
    finally:
        fm.time.monotonic = _echt_mono
    return musik.log


# ---------------------------------------------------------------------------
print("Test 1: Anleitung - die Musik laeuft weiter")
# ---------------------------------------------------------------------------
pulse = []
log = lauf(Musik(), grafik=True, grenze=30, eigene_konsole=True,
           puls=lambda p: pulse.append(1) and False, musik_weiter=True)
check("weder angehalten noch neu gestartet",
      "pause" not in log and "resume" not in log, log[:5])
check("im Puls weitergefuehrt (der naechste Titel kommt)", "tick" in log,
      len(log))
check("der eigene Puls des Betrachters laeuft weiter mit", len(pulse) > 1,
      len(pulse))
# Der Takt, gemessen an einer Uhr, die je Puls 0,1 s weitergeht.
fe.music = Musik()
_t = [0.0]
fm.time.monotonic = lambda: _t[0]
try:
    _p = fe._puls_mit_musik(lambda proc: "weiter")
    _erg = []
    for _i in range(50):
        _erg.append(_p(None))
        _t[0] += 0.1
finally:
    fm.time.monotonic = _echt_mono
check("hoechstens einmal je MUSIK_TAKT (5 s, 50 Pulse: 5 ticks)",
      fe.music.log.count("tick") == 5 and fe.MUSIK_TAKT == 1.0,
      fe.music.log.count("tick"))
check("der Puls gibt die Antwort des Betrachters weiter",
      set(_erg) == {"weiter"})

# ---------------------------------------------------------------------------
print()
print("Test 2: ein Skript - wie bisher")
# ---------------------------------------------------------------------------
log = lauf(Musik(), eigene_konsole=True)
check("angehalten und danach fortgesetzt, kein Weiterfuehren",
      log == ["pause", "resume"], log)

# ---------------------------------------------------------------------------
print()
print("Test 3: ohne eigenen Puls")
# ---------------------------------------------------------------------------
log = lauf(Musik(), grafik=True, grenze=30, eigene_konsole=True,
           musik_weiter=True)
check("die Musik laeuft trotzdem weiter",
      "tick" in log and "pause" not in log, log[:3])

# ---------------------------------------------------------------------------
print()
print("Test 4: ein Fehler in der Musik")
# ---------------------------------------------------------------------------
pulse = []
log = lauf(Musik(kaputt=True), grafik=True, grenze=30, eigene_konsole=True,
           puls=lambda p: pulse.append(1) and False, musik_weiter=True)
check("der Betrachter laeuft weiter, sein Puls auch",
      "tick" in log and len(pulse) > 1, (log[:2], len(pulse)))

# ---------------------------------------------------------------------------
print()
print("Test 5: wer es verlangt")
# ---------------------------------------------------------------------------
fq = open(H.FRONTEND_PY, encoding="utf-8").read()
az = fq.split("    def anleitung_zeigen(self):")[1].split("\n    def ")[0]
rs = fq.split("    def run_script(")[1].split("\n    def ")[0]
check("anleitung_zeigen(): musik_weiter=True", "musik_weiter=True" in az)
check("run_script(): nicht", "musik_weiter" not in rs)

print()
if fails:
    print("ROT: %d Pruefung(en) fehlgeschlagen:" % len(fails))
    for f_ in fails:
        print("   - " + f_)
    sys.exit(1)
print("ALLES GRUEN")
