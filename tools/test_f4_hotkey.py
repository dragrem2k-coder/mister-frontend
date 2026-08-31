#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft den F4-Schnellstart (Nutzerwunsch: "koennen wir das Script
Frontend_Start.sh, wenn einer kein Autostart eingerichtet hat, irgendwie
auf F4 im OSD einbinden? So dass man nur F4 druecken muss und es
startet?").

MiSTer selbst wertet F4 nirgends aus (die Taste ist frei), bietet aber
auch keine Moeglichkeit, eine Taste per MiSTer.ini auf ein Script zu
legen. Deshalb ein eigener kleiner Waechter (frontend/f4_hotkey.py), der
die Eingabegeraete mitliest.

Ein Hintergrundprozess, der beim Booten startet und Tastendruecke
mitliest, ist die heikelste Art von Zusatz in diesem Projekt: er laeuft,
wenn niemand hinsieht, und ein Fehler faellt erst auf, wenn das Geraet
sich seltsam verhaelt. Entsprechend wird hier nicht nur der Gutfall
geprueft, sondern vor allem, dass er in allen anderen Lagen NICHTS tut.

Geprueft wird ohne echte Hardware ueber eine Pipe als Ersatz-
Eingabegeraet - die Ereignisse werden also mit demselben Byte-Format
gefuettert, das der Linux-Kernel liefert.

Ausfuehren:
    python3 tools/test_f4_hotkey.py
"""
import importlib.util
import os
import struct
import subprocess
import sys
import tempfile
import shutil

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
_FRONTEND_DIR = os.path.dirname(
    os.environ.get("FRONTEND_PY",
                   os.path.join(_REPO, "frontend", "frontend.py")))
sys.path.insert(0, _FRONTEND_DIR)

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


def lade(name, pfad):
    spec = importlib.util.spec_from_file_location(name, pfad)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


HOTKEY_PY = os.path.join(_FRONTEND_DIR, "f4_hotkey.py")
HOTKEY_SH = os.path.join(_FRONTEND_DIR, "f4_hotkey.sh")
F = lade("f4_hotkey", HOTKEY_PY)

TMP = tempfile.mkdtemp(prefix="f4_test_")
F.FLAG_FILE = os.path.join(TMP, "f4_hotkey")
F.CORENAME = os.path.join(TMP, "CORENAME")
F.FRONTEND_LOCK = os.path.join(TMP, "frontend.lock")
F.LOGFILE = os.path.join(TMP, "frontend.log")


def schreibe(pfad, inhalt):
    with open(pfad, "wb") as f:
        f.write(inhalt if isinstance(inhalt, bytes) else inhalt.encode())


print("Test 1: der Tastencode stimmt mit dem Linux-Standard ueberein")
# KEY_F4 ist ein Kernel-Konstantenwert - ein Zahlendreher hier waere im
# Betrieb nicht zu bemerken (es passierte einfach nie etwas), deshalb
# wird er gegen die Systemkopfdatei geprueft, wo vorhanden.
kopf = "/usr/include/linux/input-event-codes.h"
echt = None
if os.path.exists(kopf):
    for zeile in open(kopf, encoding="utf-8", errors="replace"):
        teile = zeile.split()
        if len(teile) >= 3 and teile[0] == "#define" and teile[1] == "KEY_F4":
            echt = int(teile[2], 0)
            break
if echt is None:
    print("       (input-event-codes.h nicht vorhanden - fester Vergleich)")
    echt = 62
check("KEY_F4 == %d" % echt, F.KEY_F4 == echt, "im Waechter: %d" % F.KEY_F4)
check("nur der echte Druck zaehlt (Wert 1, nicht 2=halten/0=los)",
      F.WERT_GEDRUECKT == 1)
check("Ereignisgroesse passt zum Kernel-Format",
      F.EVENT_SIZE == struct.calcsize("llHHi"))

print()
print("Test 2: ohne Schalterdatei passiert gar nichts")
check("ausgeschaltet erkannt", not F.eingeschaltet())
check("main() beendet sich sofort mit 0", F.main() == 0)
schreibe(F.FLAG_FILE, "")
check("mit Schalterdatei eingeschaltet", F.eingeschaltet())

print()
print("Test 3: 'laeuft MiSTers Menue?' vertraegt unsaubere Dateiinhalte")
# Genau hier ist schon einmal etwas schiefgegangen (siehe Kommentar in
# frontend_boot.sh): manche Firmware haengt \0, CR oder ein Leerzeichen
# an, ein blosser Vergleich auf "MENU" trifft dann NIE.
for roh, erwartet, was in (
        (b"MENU", True, "blank"),
        (b"MENU\n", True, "mit Zeilenumbruch"),
        (b"MENU\x00\x00\x00", True, "mit Nullbytes"),
        (b"MENU \r\n", True, "mit Leerzeichen und CR"),
        (b"menu", True, "kleingeschrieben"),
        (b"SNES", False, "ein Spiele-Core"),
        (b"", False, "leer")):
    schreibe(F.CORENAME, roh)
    check("CORENAME %s -> %s" % (was, "Menue" if erwartet else "kein Menue"),
          F.menue_aktiv() is erwartet)
os.remove(F.CORENAME)
check("CORENAME fehlt ganz -> kein Menue", not F.menue_aktiv())
schreibe(F.CORENAME, b"MENU")

print()
print("Test 4: ein bereits laufendes Frontend wird erkannt")
check("keine Sperrdatei -> laeuft nicht", not F.frontend_laeuft())
schreibe(F.FRONTEND_LOCK, "%d\n" % os.getpid())
check("Sperrdatei mit lebendem Prozess -> laeuft", F.frontend_laeuft())
schreibe(F.FRONTEND_LOCK, "999999\n")
check("verwaiste Sperrdatei (toter Prozess) -> laeuft nicht",
      not F.frontend_laeuft())
schreibe(F.FRONTEND_LOCK, "kaputt\n")
check("unlesbare Sperrdatei -> laeuft nicht", not F.frontend_laeuft())
os.remove(F.FRONTEND_LOCK)

print()
print("Test 5: das Erkennen von F4 im echten Ereignisstrom")


def ereignis(etype, code, wert):
    return struct.pack(F.EVENT_FMT, 0, 0, etype, code, wert)


def durchlauf(*rohdaten):
    """Fuettert Bytes ueber eine Pipe - dieselben Bytes, die der Kernel
    auf /dev/input/event* liefert - und liefert das Urteil des
    Waechters."""
    r, w = os.pipe()
    os.write(w, b"".join(rohdaten))
    os.close(w)
    g = F.Geraete()
    g.offen = {"/dev/input/event-test": os.fdopen(r, "rb", buffering=0)}
    try:
        return g.f4_gedrueckt(0.2)
    finally:
        g.schliessen("/dev/input/event-test")


check("F4 gedrueckt wird erkannt",
      durchlauf(ereignis(F.EV_KEY, F.KEY_F4, 1)))
check("F4 losgelassen loest NICHT aus",
      not durchlauf(ereignis(F.EV_KEY, F.KEY_F4, 0)))
check("F4 gehalten (Wiederholung) loest NICHT aus",
      not durchlauf(ereignis(F.EV_KEY, F.KEY_F4, 2)))
check("eine andere Taste loest NICHT aus",
      not durchlauf(ereignis(F.EV_KEY, 63, 1)))          # F5
check("dieselbe Codezahl auf einem anderen Ereignistyp loest NICHT aus",
      not durchlauf(ereignis(3, F.KEY_F4, 1)))           # EV_ABS
check("F4 mitten in einer Salve anderer Ereignisse wird gefunden",
      durchlauf(ereignis(F.EV_KEY, 30, 1), ereignis(0, 0, 0),
                ereignis(F.EV_KEY, F.KEY_F4, 1), ereignis(F.EV_KEY, 30, 0)))
check("ein abgeschnittenes Ereignis stuerzt nicht ab",
      not durchlauf(ereignis(F.EV_KEY, F.KEY_F4, 1)[:-3]))
check("ohne jedes Geraet wartet er nur, statt abzustuerzen",
      not F.Geraete().f4_gedrueckt(0.05))

print()
print("Test 6: der Menuepunkt und seine Uebersetzungen")
import fe.settings as S                              # noqa: E402
import fe.translations as T                          # noqa: E402

check("Schalter-Abfrage vorhanden", hasattr(S, "f4_hotkey_enabled"))
check("Umschalter vorhanden", hasattr(S, "toggle_f4_hotkey"))
check("Standard ist AUS (Datei bedeutet AN, nicht 'abgeschaltet')",
      "f4_hotkey" in S.F4_HOTKEY_FLAG and not S.F4_HOTKEY_FLAG.endswith("disabled"))
S.F4_HOTKEY_FLAG = os.path.join(TMP, "schalter")
S.F4_HOTKEY_SCRIPT = os.path.join(TMP, "gibtsnicht.sh")   # Start unterbinden
check("frisch: aus", not S.f4_hotkey_enabled())
check("einschalten meldet AN", S.toggle_f4_hotkey() is True)
check("danach eingeschaltet", S.f4_hotkey_enabled())
check("ausschalten meldet AUS", S.toggle_f4_hotkey() is False)
check("danach ausgeschaltet", not S.f4_hotkey_enabled())

for schluessel in ("sys_f4_hotkey_on", "sys_f4_hotkey_off",
                   "sys_f4_hotkey_enabled", "sys_f4_hotkey_disabled"):
    eintrag = T.TRANSLATIONS.get(schluessel) if hasattr(T, "TRANSLATIONS") \
        else getattr(T, "STRINGS", {}).get(schluessel)
    check("Uebersetzung %s vorhanden (de+en)" % schluessel,
          bool(eintrag) and "de" in eintrag and "en" in eintrag)

print()
print("Test 7: die Skripte selbst")
sh = open(HOTKEY_SH, encoding="utf-8").read()
check("f4_hotkey.sh prueft die Schalterdatei", "f4_hotkey" in sh)
check("f4_hotkey.sh achtet auf den Not-Aus", "disable" in sh)
r = subprocess.run(["bash", "-n", HOTKEY_SH], capture_output=True)
check("f4_hotkey.sh ist syntaktisch in Ordnung", r.returncode == 0,
      r.stderr.decode()[:120])
# Ohne Schalterdatei muss der Wrapper sofort und sauber aussteigen -
# geprueft mit umgebogenen Pfaden ueber eine Kopie.
kopie = os.path.join(TMP, "wrapper.sh")
with open(kopie, "w", encoding="utf-8") as f:
    f.write(sh.replace("/media/fat/frontend", TMP)
              .replace("exec /usr/bin/python3", "echo GESTARTET; exit 0 #"))
# Test 2 hat die Schalterdatei angelegt - fuer den Aus-Fall wieder weg
# damit, sonst prueft dieser Durchlauf gar nicht das, was er behauptet.
if os.path.exists(os.path.join(TMP, "f4_hotkey")):
    os.remove(os.path.join(TMP, "f4_hotkey"))
r = subprocess.run(["bash", kopie], capture_output=True)
check("ohne Schalterdatei startet der Wrapper nichts",
      r.returncode == 0 and b"GESTARTET" not in r.stdout,
      r.stdout.decode()[:60])
schreibe(os.path.join(TMP, "f4_hotkey"), "")
r = subprocess.run(["bash", kopie], capture_output=True)
check("mit Schalterdatei startet der Wrapper den Waechter",
      b"GESTARTET" in r.stdout)
schreibe(os.path.join(TMP, "disable"), "")
r = subprocess.run(["bash", kopie], capture_output=True)
check("Not-Aus schlaegt den Schalter", b"GESTARTET" not in r.stdout)
os.remove(os.path.join(TMP, "disable"))

print()
print("Test 8: Installation, Update und Deinstallation greifen ineinander")
# Der Eintrag in user-startup.sh ist der gefaehrlichste Teil: die Datei
# gehoert dem MiSTer, ein Fehler darin legt den naechsten Boot lahm.
for name, muss in (("Frontend_Install.sh", True),
                   ("Frontend_Install_Remote.sh", True),
                   ("Frontend_Install_Offline.sh", True),
                   ("Frontend_Update.sh", True),
                   ("Frontend_Uninstall.sh", True)):
    pfad = os.path.join(_REPO, "Scripts", name)
    inhalt = open(pfad, encoding="utf-8").read()
    check("%s kennt f4_hotkey.sh" % name,
          ("f4_hotkey.sh" in inhalt) is muss)
    r = subprocess.run(["bash", "-n", pfad], capture_output=True)
    check("%s ist syntaktisch in Ordnung" % name, r.returncode == 0,
          r.stderr.decode()[:120])

fuer_install = open(os.path.join(_REPO, "Scripts", "Frontend_Install.sh"),
                    encoding="utf-8").read()
check("Installation traegt nicht doppelt ein (grep-Pruefung davor)",
      'grep -qF "f4_hotkey.sh"' in fuer_install)
fuer_deinst = open(os.path.join(_REPO, "Scripts", "Frontend_Uninstall.sh"),
                   encoding="utf-8").read()
check("Deinstallation entfernt den Eintrag wieder",
      'grep -v "f4_hotkey.sh"' in fuer_deinst)
check("Deinstallation beendet auch einen laufenden Waechter",
      "f4_hotkey.lock" in fuer_deinst)

shutil.rmtree(TMP, ignore_errors=True)

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for f in fails:
        print("   ", f)
    sys.exit(1)
print("Alle Tests bestanden.")
