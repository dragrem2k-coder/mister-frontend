#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Schnelleres erstes Einlesen ueber ein NAS (Build 341).

RUECKMELDUNG eines NAS-Nutzers: die erste Einrichtung dauert sehr lange.
Das Einlesen lief System fuer System, und jeder Zugriff wartete auf das
Netz. Dazu: Zips wurden bei jedem Neu-Einlesen wieder geoeffnet.

GEPRUEFT WIRD:
  1. Mehrere Systeme gleichzeitig: dasselbe Ergebnis in derselben
     Reihenfolge wie nacheinander; die Fortschrittsanzeige laeuft nur im
     aufrufenden Faden, einmal je System.
  2. Mit kuenstlicher Netz-Wartezeit je Ordner ist es spuerbar schneller.
  3. Ein Fehler in einem System kostet nur dieses System.
  4. Wie viele Faeden: 6 mit Netzfreigabe, 2 ohne.
  5. Das Inhaltsverzeichnis eines Zips wird nur einmal gelesen; ein
     geaendertes Zip wird neu gelesen; ein kaputtes faellt weg; der
     Zwischenspeicher uebersteht einen Neustart und wird nach einem
     vollstaendigen Einlesen aufgeraeumt.
  6. Das Log nennt je System Eintraege und Dauer.

Ausfuehren:
    python3 tools/test_nas_einlesen.py
"""
import os
import shutil
import sys
import tempfile
import threading
import time
import zipfile

_HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_HIER), "frontend"))

import fe.paths                                          # noqa: E402
import fe.scan as SC                                     # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


def anlegen(pfad, inhalt=b"x"):
    os.makedirs(os.path.dirname(pfad), exist_ok=True)
    with open(pfad, "wb") as f:
        f.write(inhalt)


print(__doc__.strip().split("\n")[0])
print()
TMP = tempfile.mkdtemp(prefix="nas_")
_alt = (fe.paths.GAMES_BASES, SC._scan_faeden, SC.LOG, SC.ZIP_INDEX_FILE,
        SC._ordner_eintraege, SC.GAME_SYSTEMS, SC.OPTIONAL_GAME_SYSTEMS)
meldungen = []
try:
    SC.LOG = lambda s: meldungen.append(s)
    SC.ZIP_INDEX_FILE = os.path.join(TMP, "zip_index_cache.pkl")
    SC._zip_index = None
    games = os.path.join(TMP, "games")
    fe.paths.GAMES_BASES = [games]
    # Acht einfache Systeme mit einer festen Endung - eigene Tabelle,
    # damit der Test nicht an der echten Systemliste haengt.
    systeme = []
    for i in range(8):
        sk = "SYS%d" % i
        systeme.append(("System %d" % i, sk, [sk], "_Console/" + sk,
                        {".rom": (1, "f", 1)}))
        for o in range(5):
            for s in range(6):
                anlegen(os.path.join(games, sk, "Ordner %d" % o,
                                     "Spiel %d-%d.rom" % (o, s)))
    SC.GAME_SYSTEMS = systeme
    SC.OPTIONAL_GAME_SYSTEMS = []

    # -----------------------------------------------------------------------
    print("Test 1: gleichzeitig wie nacheinander")
    # -----------------------------------------------------------------------
    def einlesen(faeden):
        SC._scan_faeden = lambda: faeden
        aufrufe = []

        def cb(i, total, name):
            aufrufe.append((threading.current_thread() is
                            threading.main_thread(), total, name))
        return SC._scan_games_disk(progress_cb=cb), aufrufe
    seriell, a1 = einlesen(1)
    parallel, a6 = einlesen(6)

    def form(cats):
        def k(n):
            return (sorted(i[0] for i in n["items"]),
                    sorted((f, k(s)) for f, s in n["folders"].items()))
        return [(d, sk, k(n)) for d, n, sk in cats]
    check("dasselbe Ergebnis in derselben Reihenfolge",
          form(seriell) == form(parallel) and len(parallel) == 8,
          [c[2] for c in parallel])
    check("Fortschritt nur im aufrufenden Faden, einmal je System",
          len(a6) == 8 and all(m for m, _t, _n in a6)
          and {n for _m, _t, n in a6} == {"System %d" % i for i in range(8)},
          a6[:2])

    # -----------------------------------------------------------------------
    print()
    print("Test 2: mit Netz-Wartezeit")
    # -----------------------------------------------------------------------
    _echt = SC._ordner_eintraege

    def langsam(pfad):
        time.sleep(0.02)                 # eine Rueckfrage beim NAS
        return _echt(pfad)
    SC._ordner_eintraege = langsam
    t0 = time.monotonic()
    einlesen(1)
    t_seriell = time.monotonic() - t0
    t0 = time.monotonic()
    einlesen(6)
    t_parallel = time.monotonic() - t0
    SC._ordner_eintraege = _echt
    check("6 Faeden mindestens 2,5-mal so schnell wie einer",
          t_seriell / max(t_parallel, 1e-6) >= 2.5,
          "%.0f ms gegen %.0f ms" % (t_seriell * 1000, t_parallel * 1000))

    # -----------------------------------------------------------------------
    print()
    print("Test 3: ein Fehler kostet nur ein System")
    # -----------------------------------------------------------------------
    _echt_tree = SC._scan_folder_tree

    def kaputt(root, syskey, *a, **k):
        if syskey == "SYS3":
            raise RuntimeError("Laufwerk weg")
        return _echt_tree(root, syskey, *a, **k)
    SC._scan_folder_tree = kaputt
    del meldungen[:]
    try:
        cats, _a = einlesen(6)
    finally:
        SC._scan_folder_tree = _echt_tree
    check("die anderen sieben sind da", [c[2] for c in cats]
          == ["SYS%d" % i for i in range(8) if i != 3])
    check("und der Fehler steht im Log",
          any("Einlesen: System 3 fehlgeschlagen" in m for m in meldungen))

    # -----------------------------------------------------------------------
    print()
    print("Test 4: wie viele Faeden")
    # -----------------------------------------------------------------------
    SC._scan_faeden = _alt[1]
    _echt_netz = SC._has_network_mount
    try:
        SC._has_network_mount = lambda: True
        mit = SC._scan_faeden()
        SC._has_network_mount = lambda: False
        ohne = SC._scan_faeden()
    finally:
        SC._has_network_mount = _echt_netz
    check("mit Netzfreigabe 6, ohne 2", (mit, ohne) == (6, 2), (mit, ohne))

    # -----------------------------------------------------------------------
    print()
    print("Test 5: Zips nur einmal oeffnen")
    # -----------------------------------------------------------------------
    zdir = os.path.join(TMP, "zips")
    os.makedirs(zdir)
    zips = []
    for i in range(5):
        p = os.path.join(zdir, "Spiel %d.zip" % i)
        with zipfile.ZipFile(p, "w") as z:
            z.writestr("Spiel %d.rom" % i, b"x")
        zips.append(p)
    kaputt_zip = os.path.join(zdir, "kaputt.zip")
    anlegen(kaputt_zip, b"kein zip")
    geoeffnet = []
    _echt_zf = zipfile.ZipFile

    class Zaehler(_echt_zf):
        def __init__(self, f, *a, **k):
            geoeffnet.append(f)
            _echt_zf.__init__(self, f, *a, **k)
    zipfile.ZipFile = Zaehler
    try:
        SC._zip_index = None
        erst = [SC._zip_namen(p) for p in zips]
        n1 = len(geoeffnet)
        zweit = [SC._zip_namen(p) for p in zips]
        n2 = len(geoeffnet) - n1
        check("erstes Lesen oeffnet jedes Zip", n1 == 5, n1)
        check("zweites Lesen oeffnet keines, gleiche Namen",
              n2 == 0 and erst == zweit, n2)
        time.sleep(0.01)
        with _echt_zf(zips[0], "w") as z:
            z.writestr("Neu.rom", b"xyz")
        check("ein geaendertes Zip wird neu gelesen",
              SC._zip_namen(zips[0]) == ["Neu.rom"])
        check("ein kaputtes Zip faellt weg", SC._zip_namen(kaputt_zip) is None)
        check("gespeichert", SC.zip_index_speichern() is True
              and os.path.exists(SC.ZIP_INDEX_FILE))
        SC._zip_index = None             # "Neustart"
        del geoeffnet[:]
        nach = [SC._zip_namen(p) for p in zips]
        check("nach dem Neustart aus der Datei, ohne ein Zip zu oeffnen",
              not geoeffnet and nach[1:] == erst[1:], len(geoeffnet))
        SC._zip_index_gesehen.clear()
        SC._zip_namen(zips[1])
        SC.zip_index_speichern(alle_gesehen=True)
        SC._zip_index = None
        check("nach einem vollstaendigen Einlesen nur noch Gesehenes",
              sorted(SC._zip_index_laden()) == [zips[1]],
              sorted(SC._zip_index_laden()))
    finally:
        zipfile.ZipFile = _echt_zf

    # -----------------------------------------------------------------------
    print()
    print("Test 6: das Log")
    # -----------------------------------------------------------------------
    del meldungen[:]
    einlesen(6)
    check("je System eine Zeile mit Eintraegen und Dauer",
          sum(1 for m in meldungen if m.startswith("Einlesen: SYS")
              and "30 Eintraege" in m and m.endswith(" ms")) == 8,
          [m for m in meldungen if m.startswith("Einlesen: SYS")][:2])
    check("und eine Summenzeile mit der Zahl der Faeden",
          any(m.startswith("Einlesen: 8 Systeme in") and "(6 Faeden)" in m
              for m in meldungen))
finally:
    (fe.paths.GAMES_BASES, SC._scan_faeden, SC.LOG, SC.ZIP_INDEX_FILE,
     SC._ordner_eintraege, SC.GAME_SYSTEMS, SC.OPTIONAL_GAME_SYSTEMS) = _alt
    SC._zip_index = None
    shutil.rmtree(TMP, ignore_errors=True)

print()
if fails:
    print("ROT: %d Pruefung(en) fehlgeschlagen:" % len(fails))
    for f_ in fails:
        print("   - " + f_)
    sys.exit(1)
print("ALLES GRUEN")
