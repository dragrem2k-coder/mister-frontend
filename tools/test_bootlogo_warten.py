#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Das Warten aufs eigene Bild vor der Boot-Animation (Build 185).

WORUM ES GEHT

Nach dem Wechsel auf Kernel 6.18 meldete der Nutzer: "ich sehe etwas
laenger das OSD, dann kommt kurz der Login-Prompt, dann das Frontend.
Das Bootlogo wird nicht mehr eingeblendet - das war beim alten Kernel
bei jedem Start zu sehen."

DER FEHLER war nicht das Logo, sondern die Reihenfolge. Seit Build 166
wartet play_boot_animation() darauf, dass MiSTer uebergibt, bevor es
zeichnet - ein Logo in einen Bildspeicher zu malen, der gar nicht
angezeigt wird, ist verlorene Zeit fuer alle. Ausgeloest wird diese
Uebergabe aber von den F9-Nachfassern in _konsole_sichern(), und die
laufen aus der HAUPTSCHLEIFE - die erst NACH der Boot-Animation
beginnt.

Wir haben also darauf gewartet, dass jemand klopft, und dabei selbst
die Hand stillgehalten. Auf 5.15 fiel das nicht auf, weil dort schon
das erste F9 aus enter_console_mode() sass.

WAS DIESER TEST ABSICHERT

  - dass die Warteschleife die Nachfasser SELBST ausloest,
  - dass sie sofort aufhoert, wenn MiSTer schlaeft (sonst kostet sie
    Zeit bei Leuten, die nie ein Problem hatten),
  - dass sie bei einer Eingabe aufhoert (wer drueckt, will weiter),
  - dass sie ohne Messmoeglichkeit nicht haengenbleibt,
  - dass sie NIE laenger als BOOTLOGO_WARTEN_MAX braucht,
  - und dass eine Ausnahme aus dem Nachfassen den Start nicht
    verhindert.

Dazu die Weitergabe der Messung: _mister_last() haelt seinen Messpunkt
und liefert bei zwei Abfragen dicht hintereinander beim zweiten Mal
None. Wer zweiter ist, ist blind - deshalb misst die Schleife einmal
und reicht das Ergebnis durch.

Ausfuehren:
    python3 tools/test_bootlogo_warten.py
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


NOW = H.NOW


class Lage(object):
    """Ein Frontend, das nur aus dem besteht, was die Warteschleife
    anfasst."""

    _NICHT_GEMESSEN = F._NICHT_GEMESSEN
    BOOTLOGO_WARTEN_MAX = F.BOOTLOGO_WARTEN_MAX
    MISTER_BESCHAEFTIGT = F.MISTER_BESCHAEFTIGT
    F9_WIEDERHOLUNGEN = F.F9_WIEDERHOLUNGEN
    _auf_eigenes_bild_warten = F._auf_eigenes_bild_warten

    def __init__(self, lasten, eingabe_nach=None, sichern_kracht=False):
        self.lasten = list(lasten)      # was _mister_last() liefert
        self.gemessen = []
        self.gesichert = []             # mit welchem Wert gerufen
        self.eingabe_nach = eingabe_nach
        self.sichern_kracht = sichern_kracht
        self.inp = self

    def _mister_last(self):
        wert = self.lasten.pop(0) if self.lasten else None
        self.gemessen.append(wert)
        return wert

    def _konsole_sichern(self, last=_NICHT_GEMESSEN):
        self.gesichert.append(last)
        if self.sichern_kracht:
            raise RuntimeError("Nachfassen kaputt")

    def read_action(self, timeout=0.0):
        NOW[0] += timeout or 0.25
        if self.eingabe_nach is not None \
                and len(self.gemessen) >= self.eingabe_nach:
            return "down"
        return None


def lauf(**kw):
    t0 = NOW[0]
    L = Lage(**kw)
    L._auf_eigenes_bild_warten()
    return L, NOW[0] - t0


# ---------------------------------------------------------------------------
print("Test 1: DER FEHLER - die Schleife loest die Nachfasser selbst aus")
# ---------------------------------------------------------------------------
L, dauer = lauf(lasten=[None, 99.0, 98.0, 97.0, 96.0, 1.0])
check("_konsole_sichern wurde gerufen", len(L.gesichert) > 0,
      "%d mal" % len(L.gesichert))
check("und zwar in JEDEM Durchgang",
      len(L.gesichert) == len(L.gemessen),
      "%d Nachfasser bei %d Messungen"
      % (len(L.gesichert), len(L.gemessen)))

# ---------------------------------------------------------------------------
print()
print("Test 2: die Messung wird durchgereicht, nicht zweimal genommen")
# ---------------------------------------------------------------------------
# Zweimal dicht hintereinander messen liefert beim zweiten Mal None -
# wer zweiter ist, ist blind.
check("kein Aufruf ohne Argument",
      all(w is not Lage._NICHT_GEMESSEN for w in L.gesichert),
      "sonst wuerde _konsole_sichern() selbst messen")
check("durchgereicht wird genau das, was gemessen wurde",
      L.gesichert == L.gemessen,
      "%r gegen %r" % (L.gesichert[:4], L.gemessen[:4]))

# ---------------------------------------------------------------------------
print()
print("Test 3: sie hoert auf, sobald MiSTer schlaeft")
# ---------------------------------------------------------------------------
L, dauer = lauf(lasten=[1.0])
check("sofort fertig, wenn die erste Messung niedrig ist",
      dauer < 1.0, "%.2f s" % dauer)
check("und ohne zu warten", len(L.gemessen) == 1,
      "%d Messungen" % len(L.gemessen))

L, dauer = lauf(lasten=[99.0, 99.0, 2.0])
check("nach zwei hohen Werten beim dritten Schluss",
      len(L.gemessen) == 3, "%d Messungen" % len(L.gemessen))

# ---------------------------------------------------------------------------
print()
print("Test 4: eine Eingabe beendet das Warten")
# ---------------------------------------------------------------------------
L, dauer = lauf(lasten=[99.0] * 60, eingabe_nach=3)
check("wer drueckt, wartet nicht", dauer < F.BOOTLOGO_WARTEN_MAX,
      "%.2f s" % dauer)

# ---------------------------------------------------------------------------
print()
print("Test 5: ohne Messmoeglichkeit bleibt nichts haengen")
# ---------------------------------------------------------------------------
L, dauer = lauf(lasten=[])
check("gibt nach hoechstens 3 s auf", dauer <= 3.5, "%.2f s" % dauer)

# ---------------------------------------------------------------------------
print()
print("Test 6: die Obergrenze haelt")
# ---------------------------------------------------------------------------
L, dauer = lauf(lasten=[99.0] * 500)
check("nie laenger als BOOTLOGO_WARTEN_MAX",
      dauer <= F.BOOTLOGO_WARTEN_MAX + 0.5,
      "%.2f s bei Grenze %.1f" % (dauer, F.BOOTLOGO_WARTEN_MAX))
check("die Grenze deckt die Nachfasser bei 2, 5 und 9 s ab",
      F.BOOTLOGO_WARTEN_MAX > F.F9_WIEDERHOLUNGEN[2],
      "%.1f s gegen %.1f s" % (F.BOOTLOGO_WARTEN_MAX,
                               F.F9_WIEDERHOLUNGEN[2]))

# ---------------------------------------------------------------------------
print()
print("Test 7: ein kaputtes Nachfassen verhindert den Start nicht")
# ---------------------------------------------------------------------------
# Das Logo ist Beiwerk. Es darf niemals der Grund sein, warum jemand
# gar nicht erst ins Menue kommt.
try:
    L, dauer = lauf(lasten=[99.0, 1.0], sichern_kracht=True)
    ok = True
except Exception as e:                                   # noqa: BLE001
    ok = False
    print("    ", type(e).__name__, e)
check("eine Ausnahme wird geschluckt", ok)

# ---------------------------------------------------------------------------
print()
print("Test 8: der Grund steht im Quelltext")
# ---------------------------------------------------------------------------
quelle = io.open(os.path.join(_REPO, "frontend", "frontend.py"),
                 encoding="utf-8").read()
check("das Warten laeuft nur mit eingeschalteter Mechanik",
      "self._auf_eigenes_bild_warten()" in quelle
      and "if self.konsole_mechanik():" in quelle)
check("und warum die Grenze angehoben wurde, steht dabei",
      "ANGEHOBEN VON 6 AUF 12 SEKUNDEN" in quelle)
check("ebenso, warum die Schleife selbst nachfasst",
      "die Hand stillgehalten" in quelle,
      "wer das in einem Jahr liest, soll nicht suchen muessen")

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
