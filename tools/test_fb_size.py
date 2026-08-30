#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft den Menuepunkt "Menue-Aufloesung" (fb_size in der MiSTer.ini).

Hintergrund (Nutzerwunsch): "eventuell unter System und dann unter
Optionen dafuer einen Schalter einbauen, der beim Neustart das an- und
ausschaltet."

Der Punkt schreibt in die MiSTer.ini - also in die zentrale
Konfigurationsdatei des MiSTers, die NICHT dem Frontend gehoert. Ein
Fehler dort trifft nicht nur das Frontend, sondern das ganze Geraet.
Deshalb prueft dieser Test besonders gruendlich, dass ausser der einen
Zeile NICHTS an der Datei veraendert wird - insbesondere nicht der
[Menu]-Block, den der CRT-Schalter verwaltet.

Es wird auf einer Kopie in einem temporaeren Ordner gearbeitet, nie auf
einer echten MiSTer.ini.

Ausfuehren:
    python3 tools/test_fb_size.py
"""
import os
import sys
import tempfile
import shutil

_HERE = os.path.dirname(os.path.abspath(__file__))
_FRONTEND_DIR = os.path.dirname(
    os.environ.get("FRONTEND_PY",
                   os.path.join(os.path.dirname(_HERE), "frontend",
                                "frontend.py")))
sys.path.insert(0, _FRONTEND_DIR)

import fe.settings as S          # noqa: E402
import fe.menu as M              # noqa: E402

# fe.menu hat crt_menu_active direkt importiert - damit beide auf
# dieselbe (umgebogene) MISTER_INI schauen, hier neu binden.
M.crt_menu_active = S.crt_menu_active

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


TMP = tempfile.mkdtemp(prefix="fbsize_test_")
S.MISTER_INI = os.path.join(TMP, "MiSTer.ini")

ORIG = """; MiSTer Konfiguration - Beispiel
[MiSTer]
video_mode=8
vga_scaler=0
bootcore=lastcore

[Menu]
vga_scaler=1
fb_terminal=1
video_mode=320,8,32,24,240,4,3,16,6048
"""


def write_ini(text):
    with open(S.MISTER_INI, "w") as f:
        f.write(text)


def read_ini():
    with open(S.MISTER_INI) as f:
        return f.read()


def menu_entries():
    """Alle (Beschriftung, Art)-Paare des System-Menues."""
    out = []

    def walk(node):
        for item in node.get("items", []):
            out.append((item[0], item[1]))
        for sub in node.get("folders", {}).values():
            walk(sub)

    walk(M.system_items())
    return out


print("Test 1: Lesen und Schreiben des Werts")
write_ini(ORIG)
check("ohne Eintrag ist der Wert 0 (MiSTer-Standard)", S.fb_size_value() == 0)
check("auf halbe Groesse stellen", S.set_fb_size(2) == 2 and S.fb_size_value() == 2)
check("Zeile steht INNERHALB der [MiSTer]-Sektion",
      read_ini().index("[MiSTer]") < read_ini().index("fb_size=2")
      < read_ini().index("[Menu]"), read_ini().replace("\n", " | "))
check("weiterschalten -> viertel", S.cycle_fb_size() == 4 and S.fb_size_value() == 4)
check("weiterschalten -> wieder voll", S.cycle_fb_size() == 0
      and S.fb_size_value() == 0)

print()
print("Test 2: die uebrige MiSTer.ini bleibt unangetastet")
write_ini(ORIG)
S.set_fb_size(2)
now = read_ini()
check("[Menu]-Block unveraendert",
      "video_mode=320,8,32,24,240,4,3,16,6048" in now
      and "fb_terminal=1" in now)
check("[MiSTer]-Block unveraendert",
      "video_mode=8" in now and "vga_scaler=0" in now
      and "bootcore=lastcore" in now)
check("Kommentarzeile am Dateianfang erhalten",
      now.startswith("; MiSTer Konfiguration - Beispiel"))
S.set_fb_size(0)
check("nach dem Zurueckstellen ist die Datei WORTGLEICH wie vorher",
      read_ini() == ORIG, "" if read_ini() == ORIG else repr(read_ini()))

print()
print("Test 3: Randfaelle")
write_ini("[MiSTer]\nfb_size=2\nfb_size=4\nx=1\n")
S.set_fb_size(2)
check("mehrfach vorhandener Schluessel wird zu genau einem",
      read_ini().count("fb_size=") == 1, read_ini().replace("\n", " | "))

# BUGFIX-ABSICHERUNG (Nutzer-Rueckmeldung "ich merke keinen Unterschied"):
# der MiSTer-ini-Parser wertet NUR Zeilen INNERHALB einer Sektion aus.
# Ein Schluessel vor der ersten Sektionszeile wird stillschweigend
# verworfen - genau das war der Fehler der ersten Fassung.
write_ini("fb_size=2\n[MiSTer]\nx=1\n")
check("Schluessel VOR der ersten Sektion zaehlt nicht (MiSTer ignoriert ihn)",
      S.fb_size_value() == 0)
S.set_fb_size(4)
_pos_sec = read_ini().index("[MiSTer]")
_pos_key = read_ini().rindex("fb_size=4")
check("Schreiben legt den Wert in die [MiSTer]-Sektion", _pos_key > _pos_sec,
      read_ini().replace("\n", " | "))

write_ini("[Menu]\nvga_scaler=1\n")
check("ohne [MiSTer]-Sektion ist der Wert 0", S.fb_size_value() == 0)
S.set_fb_size(2)
check("fehlende [MiSTer]-Sektion wird angelegt",
      "[MiSTer]" in read_ini() and S.fb_size_value() == 2,
      read_ini().replace("\n", " | "))
check("der vorhandene [Menu]-Block bleibt dabei erhalten",
      "vga_scaler=1" in read_ini())

write_ini("[Menu]\nvga_scaler=1\n")
check("ohne Sektion und mit Wert 0 wird NICHTS angelegt",
      S.set_fb_size(0) == 0 and "[MiSTer]" not in read_ini())

write_ini("[MiSTer]\nfb_size=9\n")
check("unbekannter Wert wird als 0 gemeldet statt zu stoeren",
      S.fb_size_value() == 0)

_saved = S.MISTER_INI
S.MISTER_INI = os.path.join(TMP, "gibt_es_nicht.ini")
check("fehlende Datei: Lesen liefert 0", S.fb_size_value() == 0)
check("fehlende Datei: Schreiben liefert None statt einer Ausnahme",
      S.set_fb_size(2) is None)
check("fehlende Datei: es wird auch keine angelegt",
      not os.path.exists(S.MISTER_INI))
S.MISTER_INI = _saved

print()
print("Test 4: Menuezeile")
write_ini(ORIG.replace("\n[Menu]\nvga_scaler=1\nfb_terminal=1\n"
                       "video_mode=320,8,32,24,240,4,3,16,6048\n", ""))
check("HDMI-Modus: der Punkt ist im System-Menue vorhanden",
      any(k == "fb_size" for _l, k in menu_entries()))
labels = {}
for val in (0, 2, 4):
    S.set_fb_size(val)
    labels[val] = [l for l, k in menu_entries() if k == "fb_size"][0]
check("jede Stufe hat eine eigene Beschriftung",
      len(set(labels.values())) == 3)
check("die Beschriftung nennt jeweils den Neustart-Hinweis",
      all(("Neustart" in v) or ("restart" in v) for v in labels.values()),
      " / ".join(labels.values()))
S.set_fb_size(0)

write_ini(ORIG)          # enthaelt [Menu] -> CRT-Modus aktiv
check("CRT-Modus erkannt", S.crt_menu_active())
check("CRT-Modus: der Punkt ist AUSGEBLENDET",
      not any(k == "fb_size" for _l, k in menu_entries()))

print()
print("Test 5: Uebersetzungen vollstaendig")
from fe.translations import TRANSLATIONS      # noqa: E402
for key in ("sys_fb_size_full", "sys_fb_size_half", "sys_fb_size_quarter",
            "sys_fb_size_changed", "sys_fb_size_failed"):
    entry = TRANSLATIONS.get(key)
    check("%s hat deutsch und englisch" % key,
          bool(entry) and bool(entry.get("de")) and bool(entry.get("en")))

shutil.rmtree(TMP, ignore_errors=True)

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for f in fails:
        print("   ", f)
    sys.exit(1)
print("Alle Tests bestanden.")
