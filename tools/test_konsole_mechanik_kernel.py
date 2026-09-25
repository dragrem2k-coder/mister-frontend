#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Die Konsolen-Mechanik entscheidet am Kernel (Build 184).

WORUM ES GEHT

Build 167 hat die Mechanik aus den Builds 146-166 stillgelegt, weil
Start und Beenden zusammen kaputtgegangen waren, und sie hinter eine
Datei gelegt:

    touch /media/fat/frontend/konsole_mechanik_an

Dort stand als moeglicher Ausgang des Versuchs woertlich: "Beenden
geht, aber 'bin im OSD und hoere die Musik' kommt zurueck - dann
haengen beide Probleme an derselben Stelle."

Genau das ist mit Kernel 6.18.38 eingetreten. Die Datei hat alle drei
Symptome beseitigt, und das Beenden mit F12 ging weiterhin. Damit ist
belegt: die Mechanik war nicht die Ursache des kaputten Beendens - der
Kernelwechsel war es.

WAS DIESER TEST ABSICHERT

Dass die Entscheidung in beide Richtungen stimmt und nicht auf halbem
Weg stehen bleibt:

  - auf 6.x und neuer AN, auf 5.15 weiterhin AUS (dort laeuft das
    Verhalten aus Build 145 seit Wochen auf zwei Geraeten),
  - beide Dateien schlagen die Kernelfrage, und zwar in BEIDE
    Richtungen - wer auf 6.18 zurueck will, braucht keinen Build,
  - eine unlesbare Versionszeile fuehrt zum ALTEN Verhalten und nicht
    zu einem Absturz,
  - die Entscheidung wird EINMAL getroffen und gemerkt (sie wird aus
    dem Zeichenweg gerufen - eine Dateiabfrage je Bild war schon
    einmal ein Fehler),
  - und der Grund steht im Log, damit bei der naechsten Rueckfrage
    niemand raten muss.

Ausfuehren:
    python3 tools/test_konsole_mechanik_kernel.py
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
meldungen = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


_echtes_exists = os.path.exists
_echtes_uname = os.uname


class Uname(object):
    def __init__(self, release):
        self.release = release
        self.sysname, self.nodename = "Linux", "MiSTer"
        self.version, self.machine = "#2 SMP", "armv7l"

    def __iter__(self):
        return iter((self.sysname, self.nodename, self.release,
                     self.version, self.machine))


def lage(release, an_da=False, aus_da=False):
    """Eine Entscheidung unter kuenstlichen Bedingungen treffen."""
    del meldungen[:]
    F._konsole_mechanik = None

    def exists(p):
        if p == F.KONSOLE_MECHANIK_FLAG:
            return an_da
        if p == F.KONSOLE_MECHANIK_AUS_FLAG:
            return aus_da
        return _echtes_exists(p)

    fm.os.path.exists = exists
    fm.os.uname = lambda: Uname(release)
    alt_log = fm.LOG
    fm.LOG = lambda s: meldungen.append(s)
    try:
        return F.konsole_mechanik()
    finally:
        fm.os.path.exists = _echtes_exists
        fm.os.uname = _echtes_uname
        fm.LOG = alt_log
        F._konsole_mechanik = None


# ---------------------------------------------------------------------------
print("Test 1: der Kernel entscheidet, wenn keine Datei da ist")
# ---------------------------------------------------------------------------
check("5.15.1-MiSTer  -> AUS (Verhalten wie Build 145)",
      lage("5.15.1-MiSTer") is False)
check("6.18.38-MiSTer -> AN  (der gemessene Fall)",
      lage("6.18.38-MiSTer") is True)
check("6.18.53-MiSTer -> AN", lage("6.18.53-MiSTer") is True)
check("7.0.0 spaeter  -> AN  (neuer heisst nicht wieder alt)",
      lage("7.0.0-MiSTer") is True)
check("4.14 aelter    -> AUS", lage("4.14.130") is False)

# ---------------------------------------------------------------------------
print()
print("Test 2: eine kaputte Versionszeile fuehrt zum ALTEN Verhalten")
# ---------------------------------------------------------------------------
# Nicht zum Absturz, und nicht zum neuen Verhalten: wer sich nicht
# sicher ist, aendert nichts.
for komisch in ("", "keine-zahl", "MiSTer", "..", "v6.18"):
    check("%-12r -> AUS" % komisch, lage(komisch) is False)

# ---------------------------------------------------------------------------
print()
print("Test 3: die Dateien schlagen den Kernel - in BEIDE Richtungen")
# ---------------------------------------------------------------------------
check("5.15 + konsole_mechanik_an   -> AN",
      lage("5.15.1-MiSTer", an_da=True) is True)
check("6.18 + konsole_mechanik_aus  -> AUS",
      lage("6.18.38-MiSTer", aus_da=True) is False)
check("beide Dateien -> AUS gewinnt",
      lage("6.18.38-MiSTer", an_da=True, aus_da=True) is False,
      "im Zweifel das Verhalten, das seit Build 145 bekannt ist")

# ---------------------------------------------------------------------------
print()
print("Test 4: der Grund steht im Log")
# ---------------------------------------------------------------------------
lage("6.18.38-MiSTer")
check("bei der Kernelentscheidung steht die Version da",
      any("6.18.38" in m for m in meldungen),
      meldungen[0] if meldungen else "keine Meldung")
lage("5.15.1-MiSTer", an_da=True)
check("bei der Datei steht, dass sie es war",
      any("Datei erzwingt AN" in m for m in meldungen),
      meldungen[0] if meldungen else "keine Meldung")
lage("6.18.38-MiSTer", aus_da=True)
check("und bei der Gegen-Datei ebenso",
      any("Datei erzwingt AUS" in m for m in meldungen),
      meldungen[0] if meldungen else "keine Meldung")

# ---------------------------------------------------------------------------
print()
print("Test 5: einmal entschieden, dann gemerkt")
# ---------------------------------------------------------------------------
# konsole_mechanik() wird aus dem Zeichenweg gerufen. Eine
# Kartenabfrage je Bild war in diesem Projekt schon einmal ein Fehler.
F._konsole_mechanik = None
zaehler = [0]


def zaehlend(p):
    if p in (F.KONSOLE_MECHANIK_FLAG, F.KONSOLE_MECHANIK_AUS_FLAG):
        zaehler[0] += 1
        return False
    return _echtes_exists(p)


fm.os.path.exists = zaehlend
fm.os.uname = lambda: Uname("6.18.38-MiSTer")
alt_log = fm.LOG
fm.LOG = lambda s: None
try:
    for _ in range(500):
        F.konsole_mechanik()
finally:
    fm.os.path.exists = _echtes_exists
    fm.os.uname = _echtes_uname
    fm.LOG = alt_log
    F._konsole_mechanik = None
check("500 Abfragen, hoechstens zwei Dateizugriffe", zaehler[0] <= 2,
      "%d Zugriffe" % zaehler[0])

# ---------------------------------------------------------------------------
print()
print("Test 6: die Doku sagt es auch")
# ---------------------------------------------------------------------------
quelle = io.open(os.path.join(_REPO, "frontend", "frontend.py"),
                 encoding="utf-8").read()
check("die Gegen-Datei ist im Quelltext benannt",
      "konsole_mechanik_aus" in quelle)
check("und der Grund fuer die Umstellung steht dabei",
      "6.18" in quelle and "haenge im OSD" in quelle,
      "wer das in einem Jahr liest, soll nicht suchen muessen")

for name in ("README.md", "README_EN.md"):
    p = os.path.join(_REPO, name)
    if os.path.exists(p):
        inhalt = io.open(p, encoding="utf-8", errors="replace").read()
        check("%s nennt den Kernel 6.18" % name, "6.18" in inhalt)

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
