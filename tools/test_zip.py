#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft, dass ROMs IN ZIP-Archiven gefunden werden (Build 121).

WARUM DAS UEBERHAUPT GEHT: MiSTer behandelt ein Archiv im MGL-Pfad wie
einen Ordner - die offizielle Dokumentation schreibt es ausdruecklich
so:

    path="some/other.zip/path/dummy.gg"

Deshalb aendert sich am Startweg (write_mgl() in fe/launch.py) keine
einzige Zeile. Wir setzen den Pfad einfach durch das Archiv hindurch
zusammen. Genau das wird hier geprueft - und die Dinge, die dabei
schiefgehen koennten:

  - Entpackt werden darf NICHTS. Gelesen wird nur das Inhalts-
    verzeichnis am Ende der Datei. Wuerden wir entpacken, waere ein
    Scan ueber ein paar tausend Archive nicht mehr zu ertragen.
  - Ein kaputtes oder halb kopiertes Archiv darf den Scan nicht
    umwerfen. Es faellt still weg, so wie eine unlesbare Datei auch.
  - Ein Archiv ohne passende ROMs darf gar nicht erst auftauchen,
    sonst stehen ueberall leere Ordner herum.
  - Die bekannten Filter (Boot-Dateien, Beta/Proto/Hack) muessen im
    Archiv genauso greifen wie daneben.

Ausfuehren:
    python3 tools/test_zip.py
"""
import os
import sys
import tempfile
import zipfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)

import _harness as H                                    # noqa: E402,F401

sys.path.insert(0, os.path.join(_REPO, "frontend"))
import fe.scan as S                                     # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


EXTMAP = {".gg": 1, ".sms": 1, ".bin": 0}


def _namen(node, praefix=""):
    """Alle Eintraege im Baum als (Anzeigename, Pfad)."""
    raus = []
    for name, art, daten in node["items"]:
        if art == "game":
            raus.append((praefix + name, daten[0]))
    for ordner in sorted(node["folders"]):
        raus.extend(_namen(node["folders"][ordner], praefix + ordner + "/"))
    return raus


tmp = tempfile.mkdtemp(prefix="dragend_zip_")
roms = os.path.join(tmp, "GameGear")
os.makedirs(roms)

# Ein Archiv mit Unterordner, einer fremden Datei und einer Boot-Datei.
with zipfile.ZipFile(os.path.join(roms, "Sammlung.zip"), "w") as z:
    z.writestr("Sonic the Hedgehog (USA).gg", b"x")
    z.writestr("Puzzle/Columns (USA, Europe).gg", b"x")
    z.writestr("Puzzle/liesmich.txt", b"kein ROM")
    z.writestr("boot.rom", b"x")
    z.writestr("Shinobi (Beta).gg", b"x")

# Ein Archiv ohne passende ROMs.
with zipfile.ZipFile(os.path.join(roms, "Handbuecher.zip"), "w") as z:
    z.writestr("Sonic.pdf", b"%PDF")

# Ein kaputtes Archiv.
with open(os.path.join(roms, "Abgebrochen.zip"), "wb") as f:
    f.write(b"PK\x03\x04 hier bricht die Kopie ab")

# Eine ganz normale Datei daneben - die darf davon nichts abbekommen.
open(os.path.join(roms, "Wonder Boy (USA).gg"), "wb").write(b"x")

_alt_filter = S.rom_filter_enabled
_alt_einzeln = S.einzelordner_aufloesen

# Build 156 loest Ordner mit genau EINEM Spiel auf - auch im Archiv.
# Die Tests 1 bis 6 pruefen den Aufbau des Archivbaums und wollen ihn
# deshalb unveraendert sehen; der Schalter wird hier ausgeschaltet und
# in Test 7 gezielt eingeschaltet. Sein eigener Test ist
# tools/test_einzelordner.py.
S.einzelordner_aufloesen = lambda: False

print("Test 1: ohne Filter - alles im Archiv taucht auf")
S.rom_filter_enabled = lambda: False
node = S._scan_folder_tree(roms, "GAMEGEAR", "_Console/SMS", EXTMAP)
gefunden = dict(_namen(node))
for erwartet in ("Sonic the Hedgehog (USA)",
                 "Sammlung.zip/Puzzle/Columns (USA, Europe)",
                 "Shinobi (Beta)"):
    # Der Anzeigepfad im Baum beginnt mit dem Archivnamen als Ordner.
    treffer = [k for k in gefunden if k.endswith(erwartet.split("/")[-1])]
    check("gefunden: " + erwartet.split("/")[-1], bool(treffer),
          str(sorted(gefunden)[:3]))

check("die Datei neben dem Archiv bleibt unberuehrt",
      "Wonder Boy (USA)" in gefunden)
check("das Archiv wird als Ordner gefuehrt, nicht als Spiel",
      "Sammlung.zip" in node["folders"],
      str(sorted(node["folders"])))
check("der Unterordner im Archiv wird zum Unterordner",
      "Puzzle" in node["folders"]["Sammlung.zip"]["folders"])

print()
print("Test 2: der Pfad laeuft DURCH das Archiv (MGL-Schreibweise)")
pfad = dict(_namen(node)).get("Sammlung.zip/Puzzle/Columns (USA, Europe)")
check("Pfad zeigt durch Archiv und Unterordner",
      pfad == os.path.join(roms, "Sammlung.zip")
      + "/Puzzle/Columns (USA, Europe).gg",
      str(pfad))
check("und write_mgl() braucht dafuer keine Sonderbehandlung",
      "zip" not in open(os.path.join(_REPO, "frontend", "fe", "launch.py"),
                        encoding="utf-8", errors="replace").read().lower())

print()
print("Test 3: was NICHT auftauchen darf")
check("keine Nicht-ROM-Datei aus dem Archiv",
      not any("liesmich" in k for k in gefunden))
check("keine bekannte Boot-Datei",
      not any(k.endswith("boot") for k in gefunden))
check("ein Archiv ohne ROMs erscheint gar nicht",
      "Handbuecher.zip" not in node["folders"])
check("ein kaputtes Archiv faellt still weg",
      "Abgebrochen.zip" not in node["folders"])

print()
print("Test 4: mit eingeschaltetem Filter greift er auch im Archiv")
S.rom_filter_enabled = lambda: True
node2 = S._scan_folder_tree(roms, "GAMEGEAR", "_Console/SMS", EXTMAP)
gefunden2 = dict(_namen(node2))
check("Beta-Titel ist raus", not any("Beta" in k for k in gefunden2))
check("der echte Titel ist weiter da",
      any(k.endswith("Sonic the Hedgehog (USA)") for k in gefunden2))
S.rom_filter_enabled = _alt_filter

print()
print("Test 5: es wird wirklich nichts entpackt")
# Das Archiv wird nur lesend geoeffnet; im Zielordner darf nach dem
# Scan keine einzige Datei dazugekommen sein.
vorher = sorted(os.listdir(roms))
S._scan_folder_tree(roms, "GAMEGEAR", "_Console/SMS", EXTMAP)
check("der ROM-Ordner sieht danach genauso aus",
      sorted(os.listdir(roms)) == vorher, str(vorher))
quelle = open(os.path.join(_REPO, "frontend", "fe", "scan.py"),
              encoding="utf-8", errors="replace").read()
check("und im Code steht kein extract/read auf dem Archiv",
      "archiv.extract" not in quelle and ".read(" not in
      quelle.split("def _zip_baum")[1].split("def _scan_folder_tree")[0])

print()
print("Test 6: ein leerer Ordner IM Archiv bleibt nicht stehen")
with zipfile.ZipFile(os.path.join(roms, "Leer.zip"), "w") as z:
    z.writestr("Doku/handbuch.txt", b"x")
    z.writestr("Spiele/Alex Kidd (USA).gg", b"x")
node3 = S._scan_folder_tree(roms, "GAMEGEAR", "_Console/SMS", EXTMAP)
leer = node3["folders"].get("Leer.zip", {"folders": {}})
check("der Ordner ohne ROMs ist weg", "Doku" not in leer["folders"],
      str(sorted(leer["folders"])))
check("der Ordner mit ROM ist da", "Spiele" in leer["folders"])

print()
print("Test 7: mit Build 156 loesen sich Ordner mit einem Spiel auf")
# "Leer.zip" enthaelt genau ein ROM, und das steckt noch in einem
# Unterordner. Aufgeloest wird von unten nach oben: erst faellt
# "Spiele" weg, danach ist das Archiv selbst nur noch ein Spiel und
# faellt ebenfalls weg. Das Spiel steht am Ende direkt im ROM-Ordner.
S.einzelordner_aufloesen = lambda: True
node4 = S._scan_folder_tree(roms, "GAMEGEAR", "_Console/SMS", EXTMAP)
flach = dict(_namen(node4))
check("das Archiv erscheint nicht mehr als Ordner",
      "Leer.zip" not in node4["folders"], str(sorted(node4["folders"])))
check("sein einziges Spiel steht direkt in der Liste",
      "Alex Kidd (USA)" in flach, str(sorted(flach)[:5]))
check("und der Pfad laeuft weiter durch Archiv und Unterordner",
      flach.get("Alex Kidd (USA)", "").endswith(
          "Leer.zip/Spiele/Alex Kidd (USA).gg"),
      str(flach.get("Alex Kidd (USA)")))
# Das Archiv mit mehreren Spielen bleibt dagegen ein Ordner.
check("ein Archiv mit mehreren Spielen bleibt Ordner",
      "Sammlung.zip" in node4["folders"], str(sorted(node4["folders"])))
S.einzelordner_aufloesen = _alt_einzeln

import shutil                                            # noqa: E402
shutil.rmtree(tmp, ignore_errors=True)

print()
if fails:
    print("FEHLGESCHLAGEN (%d):" % len(fails))
    for f_ in fails:
        print("  -", f_)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
