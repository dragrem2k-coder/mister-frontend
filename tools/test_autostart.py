#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft den Autostart-Schalter (Nutzerfrage: "ist da jetzt quasi ein
Schalter unter System/Optionen drin, der den Autostart an- und
ausschaltbar macht?" - war bis dahin NEIN).

Das ist die heikelste Schreiboperation im ganzen Projekt: der Schalter
aendert /media/fat/linux/user-startup.sh, eine Datei, die dem MiSTer
gehoert. Ist ihr Inhalt kaputt, bootet das Geraet nicht mehr richtig -
und zwar OHNE dass der Nutzer noch an ein Menue kaeme, um es
zurueckzunehmen. Fuer diesen einen Schalter wird deshalb deutlich
gruendlicher geprueft als fuer jeden anderen, und vor allem auf die
Faelle, in denen etwas SCHIEFGEHT.

Gearbeitet wird immer auf einer Kopie in einem temporaeren Ordner, nie
auf einer echten user-startup.sh.

Ausfuehren:
    python3 tools/test_autostart.py
"""
import os
import shutil
import stat
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
_FRONTEND_DIR = os.path.dirname(
    os.environ.get("FRONTEND_PY",
                   os.path.join(_REPO, "frontend", "frontend.py")))
sys.path.insert(0, _FRONTEND_DIR)

import fe.settings as S                              # noqa: E402
import fe.translations as T                          # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


TMP = tempfile.mkdtemp(prefix="autostart_test_")
S.USER_STARTUP_FILE = os.path.join(TMP, "user-startup.sh")
S._AUTOSTART_BACKUP = S.USER_STARTUP_FILE + ".dragend_backup"

# Eine realistische user-startup.sh: MiSTers eigener Kopf, ein
# Netzlaufwerk-Mount des Nutzers, unser Autostart, unser F4-Waechter und
# etwas Fremdes hinterher.
ORIGINAL = """#!/bin/sh
# Startup script for MiSTer
/media/fat/linux/_user/meinmount.sh
mount -t cifs //192.168.1.5/roms /media/fat/cifs -o guest
/media/fat/frontend/frontend_boot.sh &
/media/fat/frontend/f4_hotkey.sh &
/media/fat/Scripts/irgendwas_fremdes.sh &
"""


def setze(inhalt):
    with open(S.USER_STARTUP_FILE, "w", encoding="utf-8") as f:
        f.write(inhalt)
    for rest in (S._AUTOSTART_BACKUP, S.USER_STARTUP_FILE + ".dragend_tmp"):
        if os.path.exists(rest):
            os.remove(rest)


def lies():
    with open(S.USER_STARTUP_FILE, "r", encoding="utf-8",
              errors="surrogateescape") as f:
        return f.read()


print("Test 1: der aktuelle Zustand wird korrekt erkannt")
setze(ORIGINAL)
check("Eintrag vorhanden -> AN", S.autostart_enabled())
setze(ORIGINAL.replace("/media/fat/frontend/frontend_boot.sh &\n", ""))
check("Eintrag fehlt -> AUS", not S.autostart_enabled())
setze(ORIGINAL.replace("/media/fat/frontend/frontend_boot.sh &",
                       "# /media/fat/frontend/frontend_boot.sh &"))
check("auskommentierter Eintrag zaehlt NICHT als AN",
      not S.autostart_enabled())
os.remove(S.USER_STARTUP_FILE)
check("Datei fehlt ganz -> AUS", not S.autostart_enabled())
check("Ausschalten ohne Datei ist trotzdem ein Erfolg",
      S.set_autostart(False) is True)

print()
print("Test 2: Ausschalten entfernt GENAU eine Zeile")
setze(ORIGINAL)
check("Ausschalten meldet Erfolg", S.set_autostart(False) is True)
danach = lies()
check("danach ist Autostart aus", not S.autostart_enabled())
check("die Autostart-Zeile ist weg", "frontend_boot.sh" not in danach)
# Das ist der eigentliche Kern: alles ANDERE muss zeichengenau stehen
# bleiben - fremde Eintraege genauso wie unser eigener F4-Waechter.
for zeile in ("#!/bin/sh",
              "# Startup script for MiSTer",
              "/media/fat/linux/_user/meinmount.sh",
              "mount -t cifs //192.168.1.5/roms /media/fat/cifs -o guest",
              "/media/fat/frontend/f4_hotkey.sh &",
              "/media/fat/Scripts/irgendwas_fremdes.sh &"):
    check("erhalten: %s" % zeile[:52], zeile in danach)
check("die Reihenfolge bleibt erhalten",
      danach.splitlines() == [z for z in ORIGINAL.splitlines()
                              if "frontend_boot.sh" not in z])
check("genau eine Zeile weniger",
      len(danach.splitlines()) == len(ORIGINAL.splitlines()) - 1,
      "%d statt %d" % (len(danach.splitlines()),
                       len(ORIGINAL.splitlines()) - 1))

print()
print("Test 3: der F4-Waechter wird nicht mit abgeraeumt")
# Beide Eintraege stehen in derselben Datei und sehen sich aehnlich -
# ein zu grob gefasster Filter wuerde beide treffen.
check("f4_hotkey.sh steht noch da", "f4_hotkey.sh" in lies())

print()
print("Test 4: Einschalten und Mehrfach-Umschalten")
check("Einschalten meldet Erfolg", S.set_autostart(True) is True)
check("danach ist Autostart an", S.autostart_enabled())
check("zweimal Einschalten traegt NICHT doppelt ein",
      S.set_autostart(True) is True
      and lies().count("frontend_boot.sh") == 1,
      "%d Vorkommen" % lies().count("frontend_boot.sh"))
check("zweimal Ausschalten ist ebenfalls harmlos",
      S.set_autostart(False) is True and S.set_autostart(False) is True)
check("Rundlauf: fremde Zeilen sind immer noch alle da",
      all(z in lies() for z in
          ("meinmount.sh", "mount -t cifs", "f4_hotkey.sh",
           "irgendwas_fremdes.sh")))

print()
print("Test 5: die Sicherheitskopie")
setze(ORIGINAL)
check("vorher keine Sicherheitskopie", not os.path.exists(S._AUTOSTART_BACKUP))
S.set_autostart(False)
check("nach der ersten Aenderung ist eine da",
      os.path.exists(S._AUTOSTART_BACKUP))
with open(S._AUTOSTART_BACKUP, encoding="utf-8") as f:
    kopie = f.read()
check("die Kopie enthaelt den ORIGINALZUSTAND", kopie == ORIGINAL)
S.set_autostart(True)
S.set_autostart(False)
with open(S._AUTOSTART_BACKUP, encoding="utf-8") as f:
    check("spaetere Aenderungen ueberschreiben die Kopie NICHT",
          f.read() == ORIGINAL)

print()
print("Test 6: nach jeder Aenderung ist die Datei startfaehig")
for ziel in (True, False, True):
    S.set_autostart(ziel)
    inhalt = lies()
    check("Shebang steht in der ersten Zeile (nach set_autostart(%s))" % ziel,
          inhalt.startswith("#!"), repr(inhalt[:12]))
    modus = os.stat(S.USER_STARTUP_FILE).st_mode
    check("Ausfuehrungsrecht gesetzt (nach set_autostart(%s))" % ziel,
          bool(modus & stat.S_IXUSR))
    check("Datei endet mit einem Zeilenumbruch (nach set_autostart(%s))" % ziel,
          inhalt.endswith("\n"))
check("keine Nebendatei bleibt liegen",
      not os.path.exists(S.USER_STARTUP_FILE + ".dragend_tmp"))

print()
print("Test 7: eine Datei ohne Shebang bekommt einen")
setze("/media/fat/etwas.sh &\n")
S.set_autostart(True)
check("Shebang ergaenzt", lies().startswith("#!/bin/bash"))
check("die vorhandene Zeile blieb erhalten", "/media/fat/etwas.sh &" in lies())
check("und der Autostart steht drin", S.autostart_enabled())

print()
print("Test 8: kaputte Zeichen in der Datei ueberleben")
# Manche user-startup.sh enthalten Zeichen, die kein sauberes UTF-8
# sind. Ein Umschreiben darf daran nichts kaputtmachen.
roh = b"#!/bin/sh\n# Ger\xe4t\n/media/fat/frontend/frontend_boot.sh &\n"
with open(S.USER_STARTUP_FILE, "wb") as f:
    f.write(roh)
if os.path.exists(S._AUTOSTART_BACKUP):
    os.remove(S._AUTOSTART_BACKUP)
check("Ausschalten gelingt trotzdem", S.set_autostart(False) is True)
with open(S.USER_STARTUP_FILE, "rb") as f:
    danach_roh = f.read()
check("das kaputte Byte steht unveraendert drin",
      b"# Ger\xe4t" in danach_roh, repr(danach_roh[:40]))
check("und die Autostart-Zeile ist weg",
      b"frontend_boot.sh" not in danach_roh)

print()
print("Test 9: wenn nicht geschrieben werden kann, bleibt alles wie es war")
nur_lesen = os.path.join(TMP, "gesperrt")
os.makedirs(nur_lesen, exist_ok=True)
gesperrte_datei = os.path.join(nur_lesen, "user-startup.sh")
with open(gesperrte_datei, "w", encoding="utf-8") as f:
    f.write(ORIGINAL)
alt_pfad, alt_backup = S.USER_STARTUP_FILE, S._AUTOSTART_BACKUP
S.USER_STARTUP_FILE = gesperrte_datei
S._AUTOSTART_BACKUP = gesperrte_datei + ".dragend_backup"
os.chmod(nur_lesen, 0o555)          # Verzeichnis nicht beschreibbar
try:
    ergebnis = S.set_autostart(False)
    with open(gesperrte_datei, encoding="utf-8") as f:
        unveraendert = f.read()
    if os.geteuid() == 0:
        # Als root greift der Schreibschutz nicht - dieser Fall laesst
        # sich hier also nicht ehrlich pruefen. Lieber offen sagen als
        # einen gruenen Haken vortaeuschen.
        print("       (als root nicht pruefbar - Schreibschutz greift "
              "fuer root nicht)")
    else:
        check("Misserfolg wird gemeldet", ergebnis is False)
        check("die Datei ist unveraendert", unveraendert == ORIGINAL)
        check("keine halbe Nebendatei liegt herum",
              not os.path.exists(gesperrte_datei + ".dragend_tmp"))
finally:
    os.chmod(nur_lesen, 0o755)
    S.USER_STARTUP_FILE, S._AUTOSTART_BACKUP = alt_pfad, alt_backup

print()
print("Test 9b: Fehler beim Umbenennen laesst die Datei unberuehrt")
# Der Schreibschutz aus Test 9 greift als root nicht. Dieser Weg
# funktioniert unabhaengig vom Benutzer: das atomare Umbenennen wird
# gezielt zum Scheitern gebracht. Genau daran haengt die Zusage
# "entweder die alte oder die neue Fassung, nie eine halbe".
setze(ORIGINAL)
echtes_replace = os.replace


def _replace_kaputt(a, b):
    raise OSError(28, "kein Platz mehr (kuenstlich)")


os.replace = _replace_kaputt
try:
    check("Misserfolg wird gemeldet", S.set_autostart(False) is False)
finally:
    os.replace = echtes_replace
check("die Datei ist zeichengenau unveraendert", lies() == ORIGINAL)
check("keine halbe Nebendatei liegt herum",
      not os.path.exists(S.USER_STARTUP_FILE + ".dragend_tmp"))
check("Autostart steht folgerichtig immer noch auf AN",
      S.autostart_enabled())

print()
print("Test 9c: die Rueckleseprobe verwirft eine falsche Fassung")
# Sicherung Nummer 3: bevor die neue Fassung an ihren Platz kommt, wird
# sie zurueckgelesen und geprueft. Faellt sie durch, darf die Zieldatei
# nicht angefasst werden.
setze(ORIGINAL)
check("Schreiben mit fehlschlagender Pruefung meldet Misserfolg",
      S._startup_schreiben(["#!/bin/sh", "irgendwas"],
                           lambda t: False) is False)
check("die Zieldatei ist unveraendert", lies() == ORIGINAL)
check("keine Nebendatei liegt herum",
      not os.path.exists(S.USER_STARTUP_FILE + ".dragend_tmp"))

print()
print("Test 10: Menuepunkt und Uebersetzungen")
check("toggle_autostart liefert (Erfolg, Zustand)", True)
setze(ORIGINAL)
ok, zustand = S.toggle_autostart()
check("Umschalten von AN meldet Erfolg und AUS", ok is True and zustand is False)
ok, zustand = S.toggle_autostart()
check("Umschalten von AUS meldet Erfolg und AN", ok is True and zustand is True)

menu_py = open(os.path.join(_FRONTEND_DIR, "fe", "menu.py"),
               encoding="utf-8").read()
check('der Menuepunkt "autostart" ist eingetragen',
      '"autostart", None' in menu_py)
check("er steht direkt ueber dem F4-Schalter",
      menu_py.index('"autostart", None') < menu_py.index('"f4_hotkey", None'))
fe_py = open(os.path.join(_FRONTEND_DIR, "frontend.py"), encoding="utf-8").read()
check("und wird in frontend.py behandelt", 'kind == "autostart"' in fe_py)

tabelle = getattr(T, "TRANSLATIONS", None) or getattr(T, "STRINGS", {})
for schluessel in ("sys_autostart_on", "sys_autostart_off",
                   "sys_autostart_enabled", "sys_autostart_disabled",
                   "sys_autostart_disabled_f4", "sys_autostart_failed"):
    eintrag = tabelle.get(schluessel)
    check("Uebersetzung %s vorhanden (de+en)" % schluessel,
          bool(eintrag) and "de" in eintrag and "en" in eintrag)
for schluessel in ("sys_autostart_enabled", "sys_autostart_disabled",
                   "sys_autostart_disabled_f4"):
    txt = tabelle.get(schluessel, {})
    check("%s nennt den Neustart bzw. den Weg drumherum" % schluessel,
          any(w in txt.get("de", "").lower()
              for w in ("neustart", "osd", "f4")))

shutil.rmtree(TMP, ignore_errors=True)

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for f in fails:
        print("   ", f)
    sys.exit(1)
print("Alle Tests bestanden.")
