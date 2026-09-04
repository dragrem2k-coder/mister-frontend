#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft, dass das Frontend keine Video-Reste in der MiSTer.ini
hinterlaesst - und dass es dabei nichts anfasst, was ihm nicht gehoert.

AUSLOESER (Nutzer-Rueckmeldung nach einem Fehlerbild bei einem
Bekannten, dessen HDMI-Bild nach dem Start des Frontends wackelte):
"falls das die Ursache ist, sollten wir da Vorkehrungen treffen, das
heisst bei uninstall mit raus ... nicht dass es noch mehrere betrifft."

Das Frontend setzt selbst KEINEN Videomodus - es liest die Geometrie aus
/sys/class/graphics/fb0/ und schreibt Pixel. Die einzigen beiden
Stellen, an denen es das Bild ueberhaupt beeinflussen kann, sind der
[Menu]-Block (CRT-Modus) und fb_size (Menue-Aufloesung). Genau die
muessen bei einer Deinstallation verschwinden - und genau die duerfen
NICHT verschwinden, wenn sie vom Nutzer selbst stammen.

Ausfuehren:
    python3 tools/test_mister_ini.py
"""
import os
import shutil
import subprocess
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
_FRONTEND_DIR = os.path.dirname(
    os.environ.get("FRONTEND_PY",
                   os.path.join(_REPO, "frontend", "frontend.py")))
sys.path.insert(0, _FRONTEND_DIR)

import fe.settings as S                                # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


TMP = tempfile.mkdtemp(prefix="misterini_")
S.MISTER_INI = os.path.join(TMP, "MiSTer.ini")
S.CRT_MENU_OWNED_FLAG = os.path.join(TMP, "crt_menu_by_frontend")


def write_ini(text):
    with open(S.MISTER_INI, "w") as f:
        f.write(text)
    # Sicherung/Temp aus einem frueheren Testblock wegraeumen, damit jeder
    # Block mit demselben Ausgangszustand startet.
    for rest in (S.MISTER_INI + ".dragend_backup", S.MISTER_INI + ".tmp"):
        try:
            os.remove(rest)
        except OSError:
            pass


def read_ini():
    with open(S.MISTER_INI) as f:
        return f.read()


def flag_weg():
    try:
        os.remove(S.CRT_MENU_OWNED_FLAG)
    except OSError:
        pass


BASIS = "[MiSTer]\nbootcore=lastcore\nvideo_mode=0\n"

print("Test 1: Einschalten setzt die Markierung, Ausschalten nimmt sie weg")
write_ini(BASIS)
flag_weg()
check("frisch: kein CRT-Modus", not S.crt_menu_active())
check("frisch: gehoert nicht dem Frontend", not S.crt_menu_by_frontend())
check("einschalten meldet AN", S.toggle_crt_menu() is True)
check("danach ist der CRT-Modus aktiv", S.crt_menu_active())
check("die Markierungsdatei liegt jetzt da",
      os.path.exists(S.CRT_MENU_OWNED_FLAG))
check("und der Block gilt als vom Frontend erzeugt", S.crt_menu_by_frontend())
check("die bestehenden Zeilen bleiben unangetastet",
      "bootcore=lastcore" in read_ini())
check("ausschalten meldet AUS", S.toggle_crt_menu() is False)
check("danach ist kein [Menu] mehr da", not S.crt_menu_active())
check("und die Markierungsdatei ist weg",
      not os.path.exists(S.CRT_MENU_OWNED_FLAG))
check("die bestehenden Zeilen sind immer noch da",
      "bootcore=lastcore" in read_ini(), read_ini().replace("\n", " | "))

print()
print("Test 2: Deinstallation entfernt einen selbst gesetzten Block")
write_ini(BASIS)
flag_weg()
S.toggle_crt_menu()
check("vorher: Block da", S.crt_menu_active())
check("entfernen meldet Erfolg", S.remove_crt_menu_block() is True)
check("nachher: Block weg", not S.crt_menu_active())
check("Markierung mit weggeraeumt", not os.path.exists(S.CRT_MENU_OWNED_FLAG))
check("der Rest der Datei steht noch", "bootcore=lastcore" in read_ini())
check("nochmal entfernen meldet 'nichts zu tun'",
      S.remove_crt_menu_block() is False)

print()
print("Test 3: ein FREMDER [Menu]-Block wird NICHT angefasst")
# Der wichtigste Test dieser Datei. [Menu] ist eine ganz normale
# MiSTer-Funktion; wer dort eigene Werte stehen hat, darf sie durch eine
# Deinstallation des Frontends nicht verlieren.
FREMD = BASIS + "\n[Menu]\nvideo_mode=1280,720,60\nvga_scaler=0\n"
write_ini(FREMD)
flag_weg()
check("Block ist da", S.crt_menu_active())
check("gilt NICHT als vom Frontend erzeugt", not S.crt_menu_by_frontend())
check("entfernen lehnt ab", S.remove_crt_menu_block() is False)
check("die Datei ist unveraendert", read_ini() == FREMD,
      read_ini().replace("\n", " | "))
check("der Log-Text sagt, dass er nicht vom Frontend stammt",
      "NICHT vom Frontend" in S.mister_ini_video_zustand(),
      S.mister_ini_video_zustand())

print()
print("Test 3b: --force entfernt auch einen fremden Block")
# Nur fuer den Fall, dass jemand bewusst aufraeumen will - der normale
# Weg (ohne force) muss die Finger davon lassen, siehe Test 3.
write_ini(FREMD)
flag_weg()
check("mit force wird auch der fremde Block entfernt",
      S.remove_crt_menu_block(force=True) is True)
check("danach ist er weg", not S.crt_menu_active())

print()
print("Test 4: Rueckfall fuer alte Installationen ohne Markierungsdatei")
# Wer den CRT-Modus mit einer Fassung VOR Build 72 eingeschaltet hat,
# besitzt die Markierungsdatei nicht - genau diese Installationen sind
# aber der Grund fuer die ganze Aufraeumfunktion. Deshalb zaehlt auch der
# wortgleiche Blockinhalt als Beweis.
write_ini(BASIS.rstrip() + "\n" + S.CRT_MENU_BLOCK)
flag_weg()
check("Markierung fehlt", not os.path.exists(S.CRT_MENU_OWNED_FLAG))
check("wird am Inhalt trotzdem erkannt", S.crt_menu_by_frontend())
check("und darf entfernt werden", S.remove_crt_menu_block() is True)
check("danach weg", not S.crt_menu_active())

print()
print("Test 4b: eine EINZELNE geaenderte Zeile macht den Block fremd")
GEAENDERT = BASIS.rstrip() + "\n" + S.CRT_MENU_BLOCK.replace(
    "vga_scaler=1", "vga_scaler=0")
write_ini(GEAENDERT)
flag_weg()
check("gilt nicht mehr als unserer", not S.crt_menu_by_frontend())
check("und bleibt stehen", S.remove_crt_menu_block() is False)
check("Datei unveraendert", read_ini() == GEAENDERT)

print()
print("Test 5: Umschalten auf HDMI setzt fb_size mit zurueck")
# BISHER passierte das nur in die andere Richtung (beim Wechsel IN den
# CRT-Modus). Ein im CRT-Modus vorgefundener fb_size-Wert kann keine
# bewusste Entscheidung sein - der Menuepunkt dafuer ist dort
# ausgeblendet (fe/menu.py). Ihn beim Rueckweg stehenzulassen hiesse,
# jemanden mit einem halb aufgeloesten Bild sitzen zu lassen.
write_ini(BASIS)
flag_weg()
S.toggle_crt_menu()                        # -> CRT
S.set_fb_size(2)                           # Rest aus einer alten Fassung
check("Ausgangslage: CRT an und fb_size=2",
      S.crt_menu_active() and S.fb_size_value() == 2)
check("zurueck auf HDMI meldet AUS", S.toggle_crt_menu() is False)
check("fb_size ist dabei zurueckgesetzt", S.fb_size_value() == 0,
      read_ini().replace("\n", " | "))

print()
print("Test 5b: Umschalten IN den CRT-Modus setzt fb_size ebenfalls zurueck")
write_ini(BASIS)
flag_weg()
S.set_fb_size(4)
check("Ausgangslage: fb_size=4", S.fb_size_value() == 4)
check("einschalten meldet AN", S.toggle_crt_menu() is True)
check("fb_size zurueckgesetzt", S.fb_size_value() == 0)

print()
print("Test 6: sicheres Schreiben - Sicherung, Rueck-Lesen, atomar")
write_ini(BASIS)
flag_weg()
S.toggle_crt_menu()
check("eine einmalige Sicherungskopie wurde angelegt",
      os.path.exists(S.MISTER_INI + ".dragend_backup"))
check("die Sicherung enthaelt den Zustand VOR der Aenderung",
      "[Menu]" not in open(S.MISTER_INI + ".dragend_backup").read())
check("keine Temp-Datei bleibt liegen",
      not os.path.exists(S.MISTER_INI + ".tmp"))
_inhalt_vorher = read_ini()
S.toggle_crt_menu()
check("die Sicherung wird NICHT bei jedem Schreiben ueberschrieben",
      "[Menu]" not in open(S.MISTER_INI + ".dragend_backup").read())

print()
print("Test 6b: schlaegt das Schreiben fehl, bleibt die Datei unveraendert")
write_ini(BASIS)
flag_weg()
_echtes_replace = os.replace


def _kaputtes_replace(a, b):
    raise OSError("Test: Schreiben schlaegt fehl")


os.replace = _kaputtes_replace
try:
    ergebnis = S.toggle_crt_menu()
finally:
    os.replace = _echtes_replace
check("das Umschalten meldet den Fehlschlag (None)", ergebnis is None)
check("die MiSTer.ini ist unveraendert", read_ini() == BASIS,
      read_ini().replace("\n", " | "))
check("keine Markierung gesetzt", not os.path.exists(S.CRT_MENU_OWNED_FLAG))
check("keine Temp-Datei bleibt liegen",
      not os.path.exists(S.MISTER_INI + ".tmp"))

print()
print("Test 7: fehlende MiSTer.ini bricht nichts ab")
_gespeichert = S.MISTER_INI
S.MISTER_INI = os.path.join(TMP, "gibt_es_nicht.ini")
check("crt_menu_active meldet einfach AUS", not S.crt_menu_active())
check("toggle meldet Fehlschlag", S.toggle_crt_menu() is None)
check("entfernen meldet Fehlschlag", S.remove_crt_menu_block() is None)
check("der Log-Text sagt es klar",
      "nicht lesbar" in S.mister_ini_video_zustand())
check("es wurde nichts angelegt", not os.path.exists(S.MISTER_INI))
S.MISTER_INI = _gespeichert

print()
print("Test 8: die Log-Zeile beim Start nennt beide Einstellungen")
write_ini(BASIS)
flag_weg()
zustand = S.mister_ini_video_zustand()
check("ohne alles: [Menu] nicht vorhanden, fb_size=0",
      "nicht vorhanden" in zustand and "fb_size=0" in zustand, zustand)
S.toggle_crt_menu()
S.set_fb_size(2)
zustand = S.mister_ini_video_zustand()
check("mit CRT-Modus: als vom Frontend gesetzt erkannt",
      "vom Frontend gesetzt" in zustand, zustand)
check("und fb_size wird genannt", "fb_size=2" in zustand, zustand)
fe_py = open(os.path.join(_FRONTEND_DIR, "frontend.py"), encoding="utf-8").read()
check("frontend.py schreibt die Zeile beim Start ins Log",
      "mister_ini_video_zustand()" in fe_py)

print()
print("Test 9: das Aufraeumskript der Deinstallation")
CLEANUP = os.path.join(_FRONTEND_DIR, "mister_ini_cleanup.py")
check("mister_ini_cleanup.py liegt im Frontend-Ordner",
      os.path.exists(CLEANUP))
uninst = open(os.path.join(_REPO, "Scripts", "Frontend_Uninstall.sh"),
              encoding="utf-8").read()
check("Frontend_Uninstall.sh ruft es auf",
      "mister_ini_cleanup.py" in uninst)
# Es MUSS vor dem Loeschen der Programmdateien laufen - das Skript liegt
# selbst im Frontend-Ordner und waere sonst schon weg.
check("und zwar VOR dem Loeschen der Programmdateien",
      uninst.index("mister_ini_cleanup.py") < uninst.index('rm -rf "$FRONTEND_DIR"'))

# Das Skript einmal echt laufen lassen, gegen eine Wegwerf-MiSTer.ini.
LAUF = os.path.join(TMP, "lauf")
os.makedirs(LAUF, exist_ok=True)
shutil.copytree(os.path.join(_FRONTEND_DIR, "fe"), os.path.join(LAUF, "fe"),
                dirs_exist_ok=True)
shutil.copy(CLEANUP, LAUF)
ini_pfad = os.path.join(TMP, "lauf_MiSTer.ini")
with open(ini_pfad, "w") as f:
    f.write(BASIS.rstrip() + "\n" + S.CRT_MENU_BLOCK + "\n")
# Pfade des Skripts auf die Wegwerf-Datei umbiegen: dafuer eine winzige
# Startdatei, die fe.settings VOR dem Import des Aufraeumskripts umstellt
# (das holt sich seine Namen beim Import aus fe.settings).
starter = os.path.join(LAUF, "starter.py")
with open(starter, "w") as f:
    f.write(
        "import sys, os\n"
        "sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))\n"
        "import fe.settings as S\n"
        "S.MISTER_INI = %r\n"
        "S.CRT_MENU_OWNED_FLAG = %r\n"
        "import mister_ini_cleanup as C\n"
        "sys.exit(C.main())\n" % (ini_pfad, os.path.join(TMP, "lauf_flag")))
p = subprocess.run([sys.executable, starter], capture_output=True, text=True,
                   cwd=LAUF)
ausgabe = (p.stdout or "") + (p.stderr or "")
check("das Aufraeumskript laeuft fehlerfrei durch", p.returncode == 0,
      ausgabe.strip()[-200:])
with open(ini_pfad) as f:
    danach = f.read()
check("es hat den [Menu]-Block entfernt", "[Menu]" not in danach,
      danach.replace("\n", " | "))
check("und den Rest der Datei stehen gelassen", "bootcore=lastcore" in danach)
check("es sagt im Klartext, was es getan hat",
      "[Menu]-Block entfernt" in ausgabe, ausgabe.strip()[-200:])

print()
print("Test 9b: das Aufraeumskript laesst einen fremden Block stehen")
with open(ini_pfad, "w") as f:
    f.write(FREMD)
try:
    os.remove(os.path.join(TMP, "lauf_flag"))
except OSError:
    pass
p = subprocess.run([sys.executable, starter], capture_output=True, text=True,
                   cwd=LAUF)
ausgabe = (p.stdout or "") + (p.stderr or "")
with open(ini_pfad) as f:
    danach = f.read()
check("die fremde Datei ist unveraendert", danach == FREMD,
      danach.replace("\n", " | "))
check("und das Skript sagt auch warum",
      "bleibt stehen" in ausgabe, ausgabe.strip()[-200:])

shutil.rmtree(TMP, ignore_errors=True)

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for f in fails:
        print("   ", f)
    sys.exit(1)
print("Alle Tests bestanden.")
