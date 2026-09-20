#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hochkant (TATE / 90 Grad) - erster Schritt (Build 173).

WAS GEMESSEN WURDE, BEVOR ETWAS GEBAUT WURDE

Das Frontend stuerzt hochkant NICHT ab - nachgeprueft bei 1080x1920,
720x1280, 480x640 und 240x320, alle drei Ansichten. Es war nur
unbrauchbar, und der Grund stand in einer einzigen Zeile:

    s = max(1, H // 360)

Der Vergroesserungsfaktor des ganzen Layouts haengt allein an der
HOEHE. Quer ist das richtig. Hochkant ist die Hoehe ploetzlich die
GROSSE Seite: s wird groesser, waehrend gleichzeitig weniger Breite
da ist. Beides zieht in dieselbe Richtung.

    1920x1080   68 Zeichen je Zeile      <- Auslegung
    1080x1920   23 Zeichen je Zeile      <- ein Drittel

Ein Spieltitel wird damit auf ein Drittel abgeschnitten.

DIE AENDERUNG ist _skala(w, h): quer wie bisher, hochkant zaehlt die
BREITE - sie ist die knappe Seite und entscheidet, wieviel Text in
eine Zeile passt. Danach 38 statt 23 Zeichen. Mehr geht nicht, ein
hochkantes Bild ist nun einmal schmaler.

WAS DIESER TEST VOR ALLEM ABSICHERT: dass sich QUER nichts geaendert
hat. Das ist die eigentliche Gefahr bei einer Zeile, die an 37
Stellen vorkommt.

Ausfuehren:
    python3 tools/test_hochkant.py
"""
import os
import sys
import traceback

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
sys.path.insert(0, _HIER)

import _harness as H                                     # noqa: E402

fm = H.fm
import fe.settings as S                                  # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


def zeichen_je_zeile(b, h):
    s = fm._skala(b, h)
    ox = b * fm.OVERSCAN_X // 100
    return (b - 2 * ox) // (8 * s)


QUER = ((1920, 1080), (1280, 720), (640, 480), (320, 240))
HOCH = ((1080, 1920), (720, 1280), (480, 640), (240, 320))

# ---------------------------------------------------------------------------
print("Test 1: QUER DARF SICH NICHTS GEAENDERT HABEN")
# ---------------------------------------------------------------------------
# Die Zeile kam an 37 Stellen vor. Das ist die eigentliche Gefahr.
for b, h in QUER:
    check("%4dx%-5d: Faktor weiterhin aus der Hoehe" % (b, h),
          fm._skala(b, h) == max(1, h // 360),
          "%d" % fm._skala(b, h))
check("und 16:9 fasst weiterhin 68 Zeichen",
      zeichen_je_zeile(1920, 1080) == 68, str(zeichen_je_zeile(1920, 1080)))
check("auch bei 720p", zeichen_je_zeile(1280, 720) == 68)

# ---------------------------------------------------------------------------
print()
print("Test 2: hochkant zaehlt die schmale Seite")
# ---------------------------------------------------------------------------
for b, h in HOCH:
    check("%4dx%-5d: Faktor aus der Breite" % (b, h),
          fm._skala(b, h) == max(1, b // 360),
          "%d" % fm._skala(b, h))

# Und das Ergebnis, um das es geht.
for b, h, mindestens in ((1080, 1920, 34), (720, 1280, 34)):
    z = zeichen_je_zeile(b, h)
    check("%4dx%-5d: mindestens %d Zeichen je Zeile" % (b, h, mindestens),
          z >= mindestens, "%d" % z)

check("1080x1920 ist deutlich besser als vorher (23)",
      zeichen_je_zeile(1080, 1920) > 30,
      "%d statt 23" % zeichen_je_zeile(1080, 1920))

# ---------------------------------------------------------------------------
print()
print("Test 3: der Faktor ist nie null und nie unsinnig gross")
# ---------------------------------------------------------------------------
for b, h in QUER + HOCH + ((1, 1), (7680, 4320), (100, 100)):
    s = fm._skala(b, h)
    check("%4dx%-5d: 1 <= s <= 12" % (b, h), 1 <= s <= 12, "s=%d" % s)
check("quadratisch zaehlt wie quer (keine Sonderfall-Falle)",
      fm._skala(800, 800) == max(1, 800 // 360))

# ---------------------------------------------------------------------------
print()
print("Test 4: alle drei Ansichten zeichnen hochkant")
# ---------------------------------------------------------------------------
# Gezeichnet wird in einen Puffer fester Groesse - schreibt etwas
# darueber hinaus, fliegt hier eine Ausnahme statt auf dem Geraet ein
# zerrissenes Bild.
for b, h in HOCH:
    H.SCREEN[:] = [b, h]
    for ansicht in S.ANSICHTEN:
        try:
            f = H.make_frontend(page=1)
            f.ansicht_setzen(ansicht)
            f.draw()
            gefaerbt = any(f.fb.buf[i] for i in range(0, f.fb.size, 997))
            ok, fehler = True, ""
        except Exception as e:                           # noqa: BLE001
            ok, gefaerbt, fehler = False, False, "%s: %s" % (
                type(e).__name__, e)
            traceback.print_exc(limit=2)
        check("%4dx%-5d %-8s zeichnet" % (b, h, ansicht), ok, fehler)
        check("%4dx%-5d %-8s faerbt den Schirm" % (b, h, ansicht),
              gefaerbt)
    # Und die Hauptseite.
    try:
        f = H.make_frontend(page=0)
        f.draw()
        ok = True
    except Exception as e:                               # noqa: BLE001
        ok = False
        print("    ", type(e).__name__, e)
    check("%4dx%-5d Hauptseite zeichnet" % (b, h), ok)

# ---------------------------------------------------------------------------
print()
print("Test 5: es gibt nur noch EINE Stelle, die den Faktor rechnet")
# ---------------------------------------------------------------------------
# Vorher stand "max(1, H // 360)" siebenunddreissig Mal da. Eine
# Aenderung an der Regel haette man an 36 davon vergessen koennen.
import io                                                # noqa: E402
quelle = io.open(os.path.join(_REPO, "frontend", "frontend.py"),
                 encoding="utf-8").read()
check("die alte Rechnung kommt nicht mehr vor",
      "max(1, H // 360)" not in quelle)
check("und auch nicht ueber fb.height",
      "max(1, fb.height // 360)" not in quelle)
check("es gibt genau eine Definition von _skala",
      quelle.count("def _skala(") == 1)
check("und sie wird auch benutzt", quelle.count("_skala(") > 30,
      "%d Aufrufe" % (quelle.count("_skala(") - 1))

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
