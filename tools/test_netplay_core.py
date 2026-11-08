#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Die Netplay-Fassung als dritte Core-Moeglichkeit (Build 315).

NUTZERWUNSCH, woertlich: "ausserdem haette ich gerne das core die mit
_netplay.rbf auf dem mister sind mit im core auswahlmenue mit
angezeigt werden! als dritte option!" - und auf die Rueckfrage, WO:
"da wo ich zwischen standard core oder Retroachievements core
auswaehle". Zur Benennung: "Bau es tolerant, ich pruefe danach".

WARUM SIE BISHER NIRGENDS AUFTAUCHTEN, und das ist kein Versehen:
fassungen() in fe/cores.py verlangt, dass auf den Core-Namen ein
Unterstrich und dann eine ZIFFER folgt. Diese Regel haelt die
Praefix-Falle zu - ohne sie wuerde eine Auswahl fuer "_Console/SNES"
stillschweigend den SNES_Tracker-Core einsammeln. Die Regel bleibt;
die Netplay-Fassung wird stattdessen ausdruecklich gesucht.

WAS DIESER TEST SICHERT:
  1. netplay_fassungen() findet alle plausiblen Schreibweisen, im
     eigenen Ordner UND in einem Ordner mit "netplay" im Namen (auch
     eine Ebene tiefer),
  2. die Praefix-Falle bleibt zu: weder SNES_Tracker noch SNESNetplay
     werden eingesammelt,
  3. finde_netplay() liefert die NEUESTE,
  4. fassungen() ist unveraendert - die Gegenprobe, dass die alte
     Regel noch greift,
  5. find_netplay_core() liefert (name, None): KEIN erfundener
     setname,
  6. draw_core_choice_screen() liefert einen NAMEN und keinen
     Wahrheitswert mehr, zeigt genau die Optionen, die es wirklich
     gibt, und laeuft umlaufend,
  7. alle drei Aufrufer fragen bei RA ODER Netplay und bilden die
     Antwort ueber EINE gemeinsame Stelle ab,
  8. der Text existiert in beiden Sprachen,
  9. und ohne Netplay-Datei aendert sich gar nichts.

Ausfuehren:
    python3 tools/test_netplay_core.py
"""
import os
import re
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H          # noqa: E402

import fe.cores as CORES      # noqa: E402
import fe.translations as TR  # noqa: E402
from _quelle import koerper, nur_code                     # noqa: E402

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_QF = open(os.path.join(_REPO, "frontend", "frontend.py"),
           encoding="utf-8", errors="replace").read()
_SCHIRM = nur_code(koerper(_QF, "draw_core_choice_screen", "Frontend"))
_ENTER = nur_code(koerper(_QF, "_enter_category", "Frontend"))
_FIND = nur_code(koerper(_QF, "find_netplay_core", "Frontend"))
_TUPEL = nur_code(koerper(_QF, "_core_wahl_tupel", "Frontend"))

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


print(__doc__.strip().split("\n")[0])
print()

TMP = tempfile.mkdtemp(prefix="netplay_")
_ALT_BASE = CORES.BASE
CORES.BASE = TMP


def lege(*teile):
    pfad = os.path.join(TMP, *teile)
    os.makedirs(os.path.dirname(pfad), exist_ok=True)
    with open(pfad, "wb") as fh:
        fh.write(b"\x00")


# Ein nachgebautes /media/fat. Die Dateinamen sind absichtlich die
# verschiedenen Schreibweisen, die es geben KANN - welche es auf
# seinem Geraet wirklich sind, pruefen wir dort.
lege("_Console", "SNES_20260101.rbf")          # normale Fassung
lege("_Console", "SNES_20260305.rbf")          # neuere normale Fassung
lege("_Console", "SNES_netplay.rbf")           # ohne Datum
lege("_Console", "SNES_Netplay_20260220.rbf")  # gross, mit Datum
lege("_Console", "SNES_20260110_netplay.rbf")  # Datum vor der Marke
lege("_Console", "SNES_Tracker_20260101.rbf")  # die Praefix-Falle
lege("_Console", "SNESNetplay.rbf")            # ohne Unterstrich
lege("_Console", "NES_20260101.rbf")           # ein anderes System
lege("_Netplay", "Cores", "N64_netplay_20260401.rbf")
lege("_Console", "N64_20260101.rbf")
lege("_Console", "GBA_20260101.rbf")           # ganz ohne Netplay
# DER FALL AUS SEINER RUECKMELDUNG ("warum wird der gameboy_netplay
# core nicht mit aufgelistet, die anderen gehen"): in der
# Systemtabelle heisst der Core "_Console/Gameboy", die Datei auf der
# Karte "gameboy_netplay" - andere Schreibweise. Bei NES oder SNES
# faellt das nicht auf, weil beide dort zufaellig uebereinstimmen.
lege("_Console", "Gameboy_20260101.rbf")
lege("_Console", "gameboy_netplay.rbf")

# ---------------------------------------------------------------------------
print("Test 1: gefunden wird, was Netplay ist")
# ---------------------------------------------------------------------------
snes = CORES.netplay_fassungen("_Console/SNES")
check("drei Schreibweisen gefunden", len(snes) == 3,
      "%r" % (snes,))
for erwartet in ("_Console/SNES_netplay",
                 "_Console/SNES_Netplay_20260220",
                 "_Console/SNES_20260110_netplay"):
    check("dabei: %s" % erwartet, erwartet in snes)
n64 = CORES.netplay_fassungen("_Console/N64")
check("auch aus einem eigenen Netplay-Ordner, eine Ebene tief",
      n64 == ["_Netplay/Cores/N64_netplay_20260401"], "%r" % (n64,))
check("ohne Netplay-Datei kommt eine leere Liste",
      CORES.netplay_fassungen("_Console/GBA") == [],
      "%r" % (CORES.netplay_fassungen("_Console/GBA"),))
check("und ohne Namen auch", CORES.netplay_fassungen("") == [])

# ---------------------------------------------------------------------------
print()
print("Test 2: die Praefix-Falle bleibt zu")
# ---------------------------------------------------------------------------
check("der Tracker wird NICHT eingesammelt",
      not any("Tracker" in n for n in snes),
      "sonst waehlt eine Auswahl fuer SNES stillschweigend einen "
      "ganz anderen Core")
check("und 'SNESNetplay' ohne Unterstrich auch nicht",
      not any(n.endswith("SNESNetplay") for n in snes),
      "ohne Trennzeichen koennte das ein voellig anderer Core sein")
check("ein anderes System faengt nichts davon ab",
      CORES.netplay_fassungen("_Console/NES") == [],
      "%r" % (CORES.netplay_fassungen("_Console/NES"),))

# ---------------------------------------------------------------------------
print()
print("Test 2b: Gross- und Kleinschreibung zaehlt nicht")
# ---------------------------------------------------------------------------
# SEINE RUECKMELDUNG ZU BUILD 315: "warum wird der gameboy_netplay
# core nicht mit aufgelistet die anderen gehen". Der Core heisst in
# der Systemtabelle "_Console/Gameboy", die Datei auf der Karte
# "gameboy_netplay" - buchstabengenau verglichen faellt sie durch.
# Dass es bei NES, SNES und N64 ging, machte den Fehler erst recht
# schwer zu sehen: dort stimmen beide Schreibweisen zufaellig
# ueberein.
gb = CORES.netplay_fassungen("_Console/Gameboy")
check("gameboy_netplay wird zu _Console/Gameboy gefunden",
      gb == ["_Console/gameboy_netplay"], "%r" % (gb,))
check("und der NAME bleibt, wie die Datei heisst",
      gb and gb[0].endswith("gameboy_netplay"),
      "in die .mgl gehoert der echte Dateiname, nicht eine "
      "zurechtgebogene Schreibweise")
check("die Praefix-Falle bleibt trotzdem zu",
      not any("Tracker" in n for n in snes),
      "kleiner geschrieben ist 'SNES_Tracker' immer noch nicht "
      "'SNES_netplay'")

# ---------------------------------------------------------------------------
print()
print("Test 3: die neueste gewinnt")
# ---------------------------------------------------------------------------
check("finde_netplay liefert die neueste",
      CORES.finde_netplay("_Console/SNES")
      == "_Console/SNES_netplay",
      "%r - absteigend alphabetisch, und das Datum steckt im Namen"
      % (CORES.finde_netplay("_Console/SNES"),))
check("ohne Treffer: None",
      CORES.finde_netplay("_Console/GBA") is None)

# ---------------------------------------------------------------------------
print()
print("Test 4: Gegenprobe - fassungen() ist unveraendert")
# ---------------------------------------------------------------------------
# WICHTIG, sonst beweist der Rest nichts: haette ich die alte Regel
# aufgeweicht, statt eine zweite Frage danebenzustellen, waere der
# Tracker jetzt eine Fassung von SNES.
alt = CORES.fassungen("_Console/SNES")
check("nur die Fassungen mit Datum", sorted(alt) == sorted(
    ["_Console/SNES_20260101", "_Console/SNES_20260305",
     "_Console/SNES_20260110_netplay"]), "%r" % (alt,))
check("der Tracker ist auch dort draussen",
      not any("Tracker" in n for n in alt))
check("'SNES_netplay' ohne Datum ist KEINE normale Fassung",
      "_Console/SNES_netplay" not in alt,
      "die alte Regel verlangt nach dem Unterstrich eine Ziffer - "
      "genau deshalb gibt es die zweite Frage")

# ---------------------------------------------------------------------------
print()
print("Test 5: find_netplay_core() erfindet keinen setname")
# ---------------------------------------------------------------------------
H.set_screen(1920, 1080)
f = H.make_frontend(page=0)
treffer = f.find_netplay_core("SNES", "_Console/SNES")
check("liefert ein Paar", isinstance(treffer, tuple) and len(treffer) == 2,
      "%r" % (treffer,))
check("der Name ist der gefundene Core",
      treffer and treffer[0] == "_Console/SNES_netplay", "%r" % (treffer,))
check("und der setname ist None", treffer and treffer[1] is None,
      "fuer den RA-Core ist er an einer echten Installation "
      "verifiziert - fuer Netplay nicht, und raten wuerde hier an "
      "der Stelle geraten, an der ein Spiel startet oder eben nicht")
check("ohne Netplay-Datei: None",
      f.find_netplay_core("GBA", "_Console/GBA") is None)
check("ohne Standard-Core: None",
      f.find_netplay_core("GIBTESNICHT", None) is None)
check("der Standard-Core wird sonst aus der Systemtabelle geholt",
      f._system_rbf("SNES") == "_Console/SNES",
      "%r" % (f._system_rbf("SNES"),))
check("und das Nachschlagen wird gemerkt",
      isinstance(getattr(f, "_syskey_rbf_cache", None), dict),
      "gefragt wird bei JEDEM Betreten einer Kategorie")

# ---------------------------------------------------------------------------
print()
print("Test 6: der Auswahlbildschirm")
# ---------------------------------------------------------------------------


class Tasten(object):
    def __init__(self, folge):
        self.folge = list(folge)

    def read_action(self, timeout=None):
        return self.folge.pop(0) if self.folge else "back"


def waehle(folge, ra=None, netplay=None):
    f.inp = Tasten(folge)
    return f.draw_core_choice_screen("SNES", "Testspiel", ra_core=ra,
                                     netplay_core=netplay)


RA = ("_RA_Cores/Cores/SNES", "RA_SNES")
NP = ("_Console/SNES_netplay", None)

check("ohne alles: nur 'normal', OK liefert den NAMEN",
      waehle(["ok"]) == "normal",
      "ein Wahrheitswert reicht bei drei Moeglichkeiten nicht mehr")
check("mit RA: runter einmal -> ra", waehle(["down", "ok"], ra=RA) == "ra")
check("mit Netplay: runter einmal -> netplay",
      waehle(["down", "ok"], netplay=NP) == "netplay")
check("mit beiden: zweimal runter -> netplay",
      waehle(["down", "down", "ok"], ra=RA, netplay=NP) == "netplay")
check("mit beiden: dreimal runter laeuft um auf normal",
      waehle(["down", "down", "down", "ok"], ra=RA, netplay=NP) == "normal",
      "umlaufend wie ueberall sonst im Haus")
check("hoch geht wirklich hoch",
      waehle(["up", "ok"], ra=RA, netplay=NP) == "netplay",
      "mit drei Eintraegen ist '1 - choice' keine Umschaltung mehr, "
      "sondern ein Sprung an den Anfang")
f.inp = Tasten(["ok"])
_vw = f.draw_core_choice_screen("SNES", "T", ra_core=RA, netplay_core=NP,
                                vorwahl="netplay")
check("Vorwahl netplay startet dort", _vw == "netplay", "%r" % (_vw,))
f.inp = Tasten(["ok"])
_vw = f.draw_core_choice_screen("SNES", "T", ra_core=RA, netplay_core=NP,
                                vorwahl="normal")
check("und Vorwahl normal ebenso", _vw == "normal", "%r" % (_vw,))
f.inp = Tasten(["back"])
check("back liefert None und NICHT 'normal'",
      f.draw_core_choice_screen("SNES", "T", ra_core=RA,
                                netplay_core=NP) is None,
      "nur None bricht das Betreten der Kategorie ab")
f.inp = Tasten(["ok"])
check("default_ra=True waehlt weiterhin den RA-Core vor",
      f.draw_core_choice_screen("SNES", "T", default_ra=True,
                                ra_core=RA, netplay_core=NP) == "ra")

# ---------------------------------------------------------------------------
print()
print("Test 7: alle drei Aufrufer fragen bei RA ODER Netplay")
# ---------------------------------------------------------------------------
_roh = nur_code(_QF)
check("der Bildschirm wird dreimal gerufen",
      len(re.findall(r"self\.draw_core_choice_screen\(", _roh)) == 3,
      "Kategorie betreten, Zufallsstart, Spielstart")
check("und es wird dreimal nach Netplay gesucht",
      len(re.findall(r"self\.find_netplay_core\(", _roh)) == 3,
      "%d" % len(re.findall(r"self\.find_netplay_core\(", _roh)))
check("die Bedingung fragt bei RA ODER Netplay",
      len(re.findall(r"ra_core or netplay_core", _roh)) >= 3,
      "%d Stellen" % len(re.findall(r"ra_core or netplay_core", _roh)))
check("die Antwort wird an EINER Stelle abgebildet",
      len(re.findall(r"def _core_wahl_tupel", _roh)) == 1
      and len(re.findall(r"self\._core_wahl_tupel\(", _roh)) == 3,
      "dieselbe Zuordnung dreimal zu tippen ist genau die Sorte "
      "Verdopplung, die hier schon viermal auseinandergelaufen ist")
check("und niemand behandelt das Ergebnis mehr als Wahrheitswert",
      "ra_core if use_ra else None" not in _roh
      and "ra_core if wahl else None" not in _roh,
      "'normal' ist wahr - ein uebriggebliebenes 'if use_ra:' waere "
      "stillschweigend falsch geworden")
check("_enter_category fragt auch ohne RA-Core",
      "netplay_core" in _ENTER and "ra_core or netplay_core" in _ENTER)
check("das Protokoll unterscheidet die Fassungen",
      "_core_wahl_log(" in _roh and "[Netplay-Core]" in _QF,
      "ein Netplay-Start als RA-Start im Protokoll fuehrt bei der "
      "naechsten Fehlersuche in die Irre")
check("kein zweiter Startweg: write_mgl bleibt dasselbe",
      len(re.findall(r"def write_mgl", open(
          os.path.join(_REPO, "frontend", "fe", "launch.py"),
          encoding="utf-8").read())) == 1)

# ---------------------------------------------------------------------------
print()
print("Test 8: der Text")
# ---------------------------------------------------------------------------
for k in ("core_choice_normal", "core_choice_ra", "core_choice_netplay"):
    e = TR.TRANSLATIONS.get(k)
    check("Text %-22s in beiden Sprachen" % k,
          bool(e) and bool(e.get("de")) and bool(e.get("en")),
          "" if e else "fehlt ganz")
check("der Bildschirm schlaegt die Namen WOERTLICH nach",
      't("core_choice_netplay")' in _SCHIRM
      and 't("core_choice_ra")' in _SCHIRM,
      "zusammengesetzte Schluessel sieht die "
      "Vollstaendigkeitspruefung nicht - die Falle aus Build 309")

# ---------------------------------------------------------------------------
print()
print("Test 9: Gegenprobe - ohne Netplay-Datei aendert sich nichts")
# ---------------------------------------------------------------------------
leer = tempfile.mkdtemp(prefix="netplay_leer_")
os.makedirs(os.path.join(leer, "_Console"))
with open(os.path.join(leer, "_Console", "SNES_20260101.rbf"), "wb") as fh:
    fh.write(b"\x00")
CORES.BASE = leer
check("keine Netplay-Fassung", CORES.netplay_fassungen("_Console/SNES") == [])
check("find_netplay_core liefert None",
      f.find_netplay_core("SNES", "_Console/SNES") is None)
f.inp = Tasten(["ok"])
check("und der Bildschirm zeigt dann auch keinen dritten Eintrag",
      f.draw_core_choice_screen("SNES", "T", ra_core=RA,
                                netplay_core=None) == "normal",
      "ein Menuepunkt fuer eine Datei, die es nicht gibt, ist eine "
      "Falle (Build 284)")
shutil.rmtree(leer, ignore_errors=True)

CORES.BASE = _ALT_BASE
shutil.rmtree(TMP, ignore_errors=True)

print()
if fails:
    print("ROT: %d Pruefung(en) fehlgeschlagen:" % len(fails))
    for x in fails:
        print("   - %s" % x)
    sys.exit(1)
print("ALLES GRUEN")
