#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Passen frontend.py und das fe-Paket zusammen? (Build 186)

DER ANLASS, wörtlich aus dem Log eines Nutzers:

    AttributeError: 'ArtCache' object has no attribute 'warten_vergessen'

Seine frontend.py war Build 184, sein fe/art.py aelter als Build 180 -
die Methode kam mit 180 dazu. Er hatte ein Teil-ZIP von Hand
eingespielt, das nur frontend.py enthielt.

Der Absturz kam nicht beim Start, sondern beim ersten Druck auf eine
Pfeiltaste, weil erst dort die Vorauslader-Aufraeumung laeuft. Auf dem
Bildschirm sah das aus wie "das Frontend beendet sich und ich lande im
OSD" - also wie ein Kernel- oder Anzeigeproblem. Die Fehlersuche lief
eine Stunde lang an der voellig falschen Stelle, samt zweier
verworfener Verdaechtigungen gegen den eigenen letzten Build.

WAS DIESER TEST ABSICHERT

  - dass genau dieser Fall gefunden wird (fe/art.py ohne
    warten_vergessen),
  - dass die Meldung SAGT, was zu tun ist, statt nur zu jammern,
  - dass ein vollstaendiges Paket KEINE Meldung erzeugt (ein Werkzeug,
    das immer meckert, wird ignoriert),
  - dass die Pruefung den Start NICHT verhindert - vielleicht fehlt
    etwas, das dieser Nutzer nie anfasst,
  - und dass sie selbst nicht abstuerzen kann, egal was sie vorfindet.

Ausfuehren:
    python3 tools/test_fe_paket_pruefung.py
"""
import io
import os
import sys

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
sys.path.insert(0, _HIER)

import _harness as H                                     # noqa: E402

fm = H.fm

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


def pruefen():
    """Die Pruefung laufen lassen und alles einsammeln, was sie sagt."""
    gesagt = []
    alt_print = fm.print if hasattr(fm, "print") else None
    import builtins
    echt_print = builtins.print
    builtins.print = lambda *a, **k: gesagt.append(" ".join(str(x) for x in a))
    alt_log = fm.LOG
    fm.LOG = lambda s: None
    try:
        fm._fe_paket_pruefen()
    finally:
        builtins.print = echt_print
        fm.LOG = alt_log
        if alt_print is not None:
            fm.print = alt_print
    return "\n".join(gesagt)


# ---------------------------------------------------------------------------
print("Test 1: ein vollstaendiges Paket wird NICHT bemaengelt")
# ---------------------------------------------------------------------------
# Ein Werkzeug, das auch im Normalfall meckert, wird nach zwei Tagen
# ignoriert - und dann nuetzt es beim dritten nichts mehr.
ausgabe = pruefen()
check("kein Wort, wenn alles da ist", ausgabe.strip() == "",
      repr(ausgabe[:120]))

# ---------------------------------------------------------------------------
print()
print("Test 2: DER FALL DES NUTZERS wird gefunden")
# ---------------------------------------------------------------------------
import fe.art                                            # noqa: E402

gesichert = fe.art.ArtCache.warten_vergessen
del fe.art.ArtCache.warten_vergessen
try:
    ausgabe = pruefen()
finally:
    fe.art.ArtCache.warten_vergessen = gesichert

check("fehlendes warten_vergessen faellt auf",
      "warten_vergessen" in ausgabe, repr(ausgabe[:200]))
check("und der Build wird genannt, mit dem es dazukam",
      "Build 180" in ausgabe)
check("die Meldung sagt, WAS zu tun ist",
      "Frontend_Update.sh" in ausgabe,
      "eine Fehlermeldung ohne Ausweg ist nur halb so viel wert")
check("und warum es passiert ist",
      "nur ein Teil der Dateien" in ausgabe)
check("sie warnt davor, dass es spaeter knallt",
      "Tastendruck" in ausgabe,
      "genau so hat es sich beim Nutzer gezeigt")

# ---------------------------------------------------------------------------
print()
print("Test 3: eine zu alte Paket-Version faellt auf")
# ---------------------------------------------------------------------------
import fe                                                # noqa: E402

gesichert = fe.PAKET_VERSION
try:
    fe.PAKET_VERSION = 0
    ausgabe = pruefen()
finally:
    fe.PAKET_VERSION = gesichert
check("Paket-Version 0 wird bemaengelt", "Paket-Version" in ausgabe,
      repr(ausgabe[:160]))

del fe.PAKET_VERSION
try:
    ausgabe = pruefen()
finally:
    fe.PAKET_VERSION = gesichert
check("und ein Paket ganz ohne Versionsangabe ebenso",
      "gar keine" in ausgabe, repr(ausgabe[:160]))

# ---------------------------------------------------------------------------
print()
print("Test 4: die Pruefung verhindert den Start NICHT")
# ---------------------------------------------------------------------------
# Vielleicht fehlt etwas, das dieser Nutzer nie anfasst. Ein Frontend,
# das deswegen gar nicht mehr startet, waere schlimmer als das Problem.
gesichert = fe.art.ArtCache.warten_vergessen
del fe.art.ArtCache.warten_vergessen
try:
    pruefen()
    ok = True
except SystemExit:
    ok = False
except Exception as e:                                   # noqa: BLE001
    ok = False
    print("    ", type(e).__name__, e)
finally:
    fe.art.ArtCache.warten_vergessen = gesichert
check("kein sys.exit, keine Ausnahme", ok)

quelle = io.open(os.path.join(_REPO, "frontend", "frontend.py"),
                 encoding="utf-8").read()
_block = quelle.split("def _fe_paket_pruefen(")[1]
# Bis zum naechsten def ODER bis zum __main__-Block - die Funktion
# steht am Dateiende, und ohne die zweite Grenze wuerde hier der
# ganze Startblock mitgelesen (samt seiner sys.exit-Aufrufe).
for _grenze in ("\ndef ", '\nif __name__ == "__main__":'):
    _block = _block.split(_grenze)[0]
check("und im Quelltext steht kein sys.exit in dieser Funktion",
      "sys.exit" not in _block,
      "Abbrechen waere schlimmer als das Problem")
# Ein "raise" steht sehr wohl drin - AttributeError als Signal an das
# except zwei Zeilen weiter. Das war beim ersten Anlauf ein Fehlalarm
# dieses Tests: er hat nach dem WORT gesucht statt nach der Wirkung.
# Geprueft wird deshalb, dass jedes raise in einem try steht.
_zeilen = _block.splitlines()
_offen = 0
_frei = []
for _z in _zeilen:
    _k = _z.strip()
    if _k.startswith("try:"):
        _offen += 1
    elif _k.startswith("except"):
        _offen = max(0, _offen - 1)
    elif _k.startswith("raise") and _offen == 0:
        _frei.append(_k)
check("jedes raise steht in einem try", not _frei, "; ".join(_frei))

# ---------------------------------------------------------------------------
print()
print("Test 5: sie kann selbst nicht abstuerzen")
# ---------------------------------------------------------------------------
# Sie laeuft vor allem anderen. Was sie vorfindet, ist nicht ihre Sache.
class Boesartig(object):
    def __getattr__(self, name):
        raise RuntimeError("nicht mit mir")


gesichert = sys.modules.get("fe.art")
sys.modules["fe.art"] = Boesartig()
try:
    ausgabe = pruefen()
    ok = True
except Exception as e:                                   # noqa: BLE001
    ok = False
    print("    ", type(e).__name__, e)
finally:
    if gesichert is not None:
        sys.modules["fe.art"] = gesichert
check("ein Modul, das bei jedem Zugriff wirft, bringt sie nicht um", ok)

# ---------------------------------------------------------------------------
print()
print("Test 6: sie laeuft frueh genug")
# ---------------------------------------------------------------------------
check("gerufen wird sie vor dem Framebuffer",
      quelle.index("_fe_paket_pruefen()")
      < quelle.index("_t_boot = time.monotonic()"),
      "spaeter zu meckern hilft niemandem")
check("die Liste nennt zu jedem Stueck den Build",
      quelle.count("\"Build 1") >= 3
      or quelle.count("'Build 1") >= 3,
      "ohne die Jahreszahl ist 'fehlt' eine Sackgasse")

init = io.open(os.path.join(_REPO, "frontend", "fe", "__init__.py"),
               encoding="utf-8").read()
check("und die Regel zum Hochzaehlen steht im Paket selbst",
      "REGEL:" in init and "PAKET_VERSION" in init)

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
