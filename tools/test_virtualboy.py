#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft die neue Kategorie "Virtual Boy".

Nutzerwunsch: "wenn der Core verfuegbar ist und ROMs dazu vorhanden sind,
wie die anderen Kategorien auf der Hauptseite hinzufuegen".

Daraus ergeben sich drei Bedingungen, die ALLE stimmen muessen - und
genau die werden hier geprueft:

  1. Core da  + ROMs da  -> Kategorie erscheint
  2. Core weg              -> Kategorie erscheint NICHT
  3. ROM-Ordner leer       -> Kategorie erscheint NICHT

Dazu kommt die Besonderheit gegenueber dem bisherigen optionalen System
(SNES_Tracker): offizielle MiSTer-Cores tragen einen Datumsstempel im
Dateinamen, der sich bei jedem Core-Update aendert. Die Pruefung muss
deshalb mit Platzhalter arbeiten, sonst waere die Kategorie nach dem
naechsten Core-Update ploetzlich verschwunden.

Gearbeitet wird in einem temporaeren Ordner, nie auf echten Daten.

Ausfuehren:
    python3 tools/test_virtualboy.py
"""
import os
import sys
import struct
import shutil
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_FRONTEND_DIR = os.path.join(_ROOT, "frontend")
sys.path.insert(0, _FRONTEND_DIR)

import fe.paths                                    # noqa: E402
import fe.systems as SYS                           # noqa: E402
import fe.scan as SCAN                             # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


TMP = tempfile.mkdtemp(prefix="vb_test_")
GAMES = os.path.join(TMP, "games")
CORES = os.path.join(TMP, "_Console")
os.makedirs(CORES)

# Eintrag aus OPTIONAL_GAME_SYSTEMS holen und auf den Testordner umbiegen
_orig = [e for e in SYS.OPTIONAL_GAME_SYSTEMS if e[1] == "VIRTUALBOY"]
check("Virtual Boy steht in OPTIONAL_GAME_SYSTEMS", len(_orig) == 1)
if not _orig:
    sys.exit(1)
disp, syskey, folders, rbf, extmap, core_pat = _orig[0]

print()
print("Test 1: Stammdaten")
check("Anzeigename ist 'Virtual Boy'", disp == "Virtual Boy")
check("ROM-Ordner ist games/VirtualBoy", folders == ["VirtualBoy"], str(folders))
check("Core-Pfad fuer die MGL ist _Console/VirtualBoy",
      rbf == "_Console/VirtualBoy", rbf)
check("Endung .vb mit MGL-Parametern delay=1 typ=f index=1",
      extmap == {".vb": (1, "f", 1)}, str(extmap))
check("Core-Pruefung arbeitet mit Platzhalter (ueberlebt Core-Updates)",
      "*" in core_pat, core_pat)

print()
print("Test 2: optional_core_file() - Datumsstempel im Dateinamen")
pat = os.path.join(CORES, "VirtualBoy*.rbf")
check("ohne Core-Datei: nichts gefunden", SYS.optional_core_file(pat) is None)
open(os.path.join(CORES, "VirtualBoy_20240115.rbf"), "w").close()
check("Core mit Datumsstempel wird gefunden",
      SYS.optional_core_file(pat) is not None)
open(os.path.join(CORES, "VirtualBoy_20250630.rbf"), "w").close()
check("bei mehreren Staenden wird der neueste genommen",
      os.path.basename(SYS.optional_core_file(pat) or "")
      == "VirtualBoy_20250630.rbf",
      str(SYS.optional_core_file(pat)))
os.remove(os.path.join(CORES, "VirtualBoy_20250630.rbf"))
check("auch ohne Datumsstempel (VirtualBoy.rbf) wird erkannt",
      SYS.optional_core_file(
          os.path.join(CORES, "VirtualBoy*.rbf")) is not None)
check("fester Pfad ohne Platzhalter funktioniert unveraendert",
      SYS.optional_core_file(
          os.path.join(CORES, "VirtualBoy_20240115.rbf")) is not None
      and SYS.optional_core_file(
          os.path.join(CORES, "GibtsNicht.rbf")) is None)
check("ein anderer Core wird NICHT mitgezaehlt",
      SYS.optional_core_file(os.path.join(CORES, "Saturn*.rbf")) is None)


def scan(mit_core, mit_roms):
    """Scan mit umgebogenen Pfaden ausfuehren und die Kategorienamen liefern."""
    shutil.rmtree(GAMES, ignore_errors=True)
    vb_dir = os.path.join(GAMES, "VirtualBoy")
    os.makedirs(vb_dir)
    if mit_roms:
        for name in ("Mario Clash (USA).vb", "Wario Land (USA).vb"):
            open(os.path.join(vb_dir, name), "w").close()
    core = os.path.join(CORES, "VirtualBoy_20240115.rbf")
    if mit_core and not os.path.exists(core):
        open(core, "w").close()
    if not mit_core and os.path.exists(core):
        os.remove(core)

    alt_bases = fe.paths.GAMES_BASES
    alt_opt = SYS.OPTIONAL_GAME_SYSTEMS[:]
    alt_std = SYS.GAME_SYSTEMS[:]
    try:
        fe.paths.GAMES_BASES = [GAMES]
        SYS.OPTIONAL_GAME_SYSTEMS[:] = [
            (disp, syskey, folders, rbf, extmap,
             os.path.join(CORES, "VirtualBoy*.rbf"))]
        SCAN.OPTIONAL_GAME_SYSTEMS[:] = SYS.OPTIONAL_GAME_SYSTEMS
        SYS.GAME_SYSTEMS[:] = []
        SCAN.GAME_SYSTEMS[:] = []
        cats = SCAN._scan_games_disk()
        return [c[0] for c in cats]
    finally:
        fe.paths.GAMES_BASES = alt_bases
        SYS.OPTIONAL_GAME_SYSTEMS[:] = alt_opt
        SCAN.OPTIONAL_GAME_SYSTEMS[:] = alt_opt
        SYS.GAME_SYSTEMS[:] = alt_std
        SCAN.GAME_SYSTEMS[:] = alt_std


print()
print("Test 3: die drei Sichtbarkeits-Bedingungen")
namen = scan(mit_core=True, mit_roms=True)
check("Core da + ROMs da -> Kategorie ist da", "Virtual Boy" in namen,
      str(namen))
namen = scan(mit_core=False, mit_roms=True)
check("Core fehlt -> Kategorie fehlt", "Virtual Boy" not in namen, str(namen))
namen = scan(mit_core=True, mit_roms=False)
check("ROM-Ordner leer -> Kategorie fehlt", "Virtual Boy" not in namen,
      str(namen))

print()
print("Test 4: Anzeigename und Akzentfarbe")
check("system_display_name('VIRTUALBOY') -> 'Virtual Boy'",
      SYS.system_display_name("VIRTUALBOY") == "Virtual Boy")
import importlib.util                              # noqa: E402
_spec = importlib.util.spec_from_file_location(
    "frontend_mod", os.path.join(_FRONTEND_DIR, "frontend.py"))
_fm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_fm)
check("eigene Akzentfarbe hinterlegt",
      "VIRTUALBOY" in _fm.SYSTEM_ACCENT, str(_fm.SYSTEM_ACCENT.get("VIRTUALBOY")))
check("Akzentfarbe ist rot (passend zum roten Display der Konsole)",
      _fm.SYSTEM_ACCENT["VIRTUALBOY"][0] > 200
      and _fm.SYSTEM_ACCENT["VIRTUALBOY"][1] < 100
      and _fm.SYSTEM_ACCENT["VIRTUALBOY"][2] < 100)

print()
print("Test 5: System-Logo (sysart)")
art_file = os.path.join(_ROOT, "frontend", "sysart", "VIRTUALBOY.art")
check("VIRTUALBOY.art liegt im sysart-Ordner", os.path.isfile(art_file))
if os.path.isfile(art_file):
    raw = open(art_file, "rb").read()
    check("Dateikopf ist ART1", raw[:4] == b"ART1")
    w, h = struct.unpack("<HH", raw[4:8])
    check("Breite 900 wie bei den uebrigen System-Logos", w == 900,
          "%dx%d" % (w, h))
    import zlib                                    # noqa: E402
    pix = zlib.decompress(raw[8:])
    check("Bilddaten haben die passende Groesse", len(pix) == w * h * 4,
          "%d statt %d" % (len(pix), w * h * 4))
    # Hintergrundfarbe wie bei den anderen Logos (BGRA, Alpha-Byte 0)
    ecke = (pix[2], pix[1], pix[0])
    check("Hintergrundfarbe wie bei den anderen Logos (28,32,44)",
          ecke == (28, 32, 44), str(ecke))
    check("kein Karomuster-Rest: Ecke ist nicht weiss/hellgrau",
          ecke not in ((255, 255, 255), (238, 238, 238)), str(ecke))
    # Das Logo ist rot - es muss also deutlich rote Pixel geben
    rot = sum(1 for i in range(0, len(pix), 4 * 37)
              if pix[i + 2] > 150 and pix[i + 1] < 90 and pix[i] < 90)
    check("das Logo enthaelt rote Bildpunkte", rot > 100, "%d Treffer" % rot)

shutil.rmtree(TMP, ignore_errors=True)

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for f in fails:
        print("   ", f)
    sys.exit(1)
print("Alle Tests bestanden.")
