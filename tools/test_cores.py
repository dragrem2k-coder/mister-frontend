#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Core-Verwaltung: welche Fassung startet ein System? (Build 174)

WAS HIER SCHIEFGEHEN KANN - UND WARUM ES SCHLIMM WAERE

Diese Sache fasst den START von Cores an. Das ist das Einzige, was
niemals kaputtgehen darf: wer nicht spielen kann, hat kein Frontend,
sondern ein Bild.

Zwei Fallen, und der Test ist um sie herum gebaut:

  1. DIE VERALTETE AUSWAHL. update_all loescht bei jedem Lauf alte
     Cores - im Log eines echten Nutzers dutzendfach ("Removing
     /media/fat/_Console/SNES_20260603.rbf"). Eine gemerkte Auswahl
     zeigt danach ins Leere. Wuerde sie trotzdem in die .mgl
     geschrieben, liesse sich das Spiel nicht mehr starten, und zwar
     still. Deshalb prueft aufloesen() bei JEDEM Start, ob die Datei
     noch da ist.

  2. DIE PRAEFIX-FALLE. MiSTer loest "_Console/SNES" als Praefix auf.
     Ein naives glob("SNES*") findet damit auch "SNES_Tracker" - und
     eine Auswahl fuer SNES wuerde stillschweigend den Tracker-Core
     starten. Nach dem Praefix muss deshalb ein Datum folgen
     (Unterstrich + Ziffer) oder gleich das Dateiende.

Ausfuehren:
    python3 tools/test_cores.py
"""
import io
import json
import os
import shutil
import sys
import tempfile

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
sys.path.insert(0, os.path.join(_REPO, "frontend"))

import fe.cores as C                                     # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


tmp = tempfile.mkdtemp(prefix="test_cores_")
C.BASE = tmp
WAHL = os.path.join(tmp, "core_wahl.json")
os.makedirs(os.path.join(tmp, "_Console"))
os.makedirs(os.path.join(tmp, "_Computer"))


def anlegen(ordner, *namen):
    for n in namen:
        open(os.path.join(tmp, ordner, n), "w").close()


anlegen("_Console",
        "SNES_20260603.rbf", "SNES_20260823.rbf",   # zwei Fassungen
        "SNES_Tracker_20260101.rbf",                # die Praefix-Falle
        "NES.rbf")                                  # ohne Datum
anlegen("_Computer",
        "NeXT_20260904a.rbf", "NeXT_20260908.rbf",
        "NeXT_20260911_scsi_dma_csr_fix.rbf",
        "NeXT_20260914_moves_fc.rbf")

# ---------------------------------------------------------------------------
print("Test 1: DIE PRAEFIX-FALLE")
# ---------------------------------------------------------------------------
snes = C.fassungen("_Console/SNES")
check("SNES findet seine zwei Fassungen", len(snes) == 2, str(snes))
check("und NICHT den Tracker-Core",
      not any("Tracker" in f for f in snes), str(snes))
check("die neueste steht vorn", snes[0].endswith("20260823"), str(snes))
tracker = C.fassungen("_Console/SNES_Tracker")
check("der Tracker findet sich selbst", tracker == ["_Console/SNES_Tracker_20260101"],
      str(tracker))
check("ein Core ohne Datum wird auch gefunden",
      C.fassungen("_Console/NES") == ["_Console/NES"])
check("NeXT hat vier Fassungen", len(C.fassungen("_Computer/NeXT")) == 4,
      str(len(C.fassungen("_Computer/NeXT"))))
check("auch die mit sprechendem Zusatz",
      any("scsi_dma" in f for f in C.fassungen("_Computer/NeXT")))

# ---------------------------------------------------------------------------
print()
print("Test 2: existiert dieser Core?")
# ---------------------------------------------------------------------------
check("Praefix mit Datum", C.core_existiert("_Console/SNES"))
check("genaue Datei", C.core_existiert("_Console/SNES_20260823"))
check("Datei ohne Datum", C.core_existiert("_Console/NES"))
check("etwas Erfundenes nicht", not C.core_existiert("_Console/GibtEsNicht"))
check("leerer Name nicht", not C.core_existiert(""))
check("None nicht", not C.core_existiert(None))
check("ein Ordner, den es nicht gibt, wirft nichts",
      not C.core_existiert("_Quatsch/Egal"))

# ---------------------------------------------------------------------------
print()
print("Test 3: DIE VERALTETE AUSWAHL - der wichtigste Test hier")
# ---------------------------------------------------------------------------
C.wahl_setzen("SNES", "_Console/SNES_20260603", WAHL)
check("die Auswahl gilt, solange die Datei da ist",
      C.aufloesen("SNES", "_Console/SNES", WAHL)
      == "_Console/SNES_20260603")

# Und jetzt das, was update_all bei jedem Lauf tut.
os.remove(os.path.join(tmp, "_Console", "SNES_20260603.rbf"))
check("nach dem Loeschen gilt wieder der Standard",
      C.aufloesen("SNES", "_Console/SNES", WAHL) == "_Console/SNES",
      C.aufloesen("SNES", "_Console/SNES", WAHL))
check("die Auswahl steht dabei noch in der Datei",
      C.wahl_laden(WAHL).get("SNES") == "_Console/SNES_20260603",
      "sie wird nur ignoriert, nicht geloescht - kommt der Core "
      "zurueck, gilt sie wieder")

# ---------------------------------------------------------------------------
print()
print("Test 4: aufloesen() liefert IMMER etwas Startbares")
# ---------------------------------------------------------------------------
check("ohne Auswahl der Standard",
      C.aufloesen("NES", "_Console/NES", WAHL) == "_Console/NES")
check("ohne Systemschluessel der Standard",
      C.aufloesen(None, "_Console/NES", WAHL) == "_Console/NES")
check("ohne Datei ueberhaupt der Standard",
      C.aufloesen("NES", "_Console/NES", os.path.join(tmp, "gibtesnicht"))
      == "_Console/NES")
# Auch eine Auswahl, die GENAU der Standard ist, aendert nichts.
C.wahl_setzen("NES", "_Console/NES", WAHL)
check("eine Auswahl gleich dem Standard aendert nichts",
      C.aufloesen("NES", "_Console/NES", WAHL) == "_Console/NES")

# ---------------------------------------------------------------------------
print()
print("Test 5: eine kaputte Auswahldatei darf nichts umwerfen")
# ---------------------------------------------------------------------------
for was, inhalt in (("gar kein JSON", "{kaputt"),
                    ("leer", ""),
                    ("eine Liste", "[1,2,3]"),
                    ("Werte sind keine Texte", json.dumps({"SNES": 42})),
                    ("leerer Wert", json.dumps({"SNES": ""}))):
    io.open(WAHL, "w", encoding="utf-8").write(inhalt)
    try:
        geladen = C.wahl_laden(WAHL)
        aufgeloest = C.aufloesen("SNES", "_Console/SNES", WAHL)
        ok = isinstance(geladen, dict) and aufgeloest == "_Console/SNES"
    except Exception as e:                               # noqa: BLE001
        ok = False
        print("    Ausnahme:", e)
    check("%-24s -> Standard, kein Absturz" % was, ok)

# ---------------------------------------------------------------------------
print()
print("Test 6: speichern ueber .tmp, loeschen per None")
# ---------------------------------------------------------------------------
C.wahl_speichern({"SNES": "_Console/SNES_20260823"}, WAHL)
check("die Datei liegt da", os.path.exists(WAHL))
check("und kein .tmp bleibt liegen", not os.path.exists(WAHL + ".tmp"))
C.wahl_setzen("SNES", None, WAHL)
check("None loescht den Eintrag", "SNES" not in C.wahl_laden(WAHL))

# ---------------------------------------------------------------------------
print()
print("Test 7: die Uebersicht zeigt nur, was wirklich da ist")
# ---------------------------------------------------------------------------
systeme = [("SNES", "SNES", ["SNES"], "_Console/SNES", {}),
           ("NES", "NES", ["NES"], "_Console/NES", {}),
           ("NeXT", "NEXT", ["NeXT"], "_Computer/NeXT", {}),
           ("Gibt es nicht", "NIX", ["NIX"], "_Console/Nix", {})]
ueb = C.uebersicht(systeme)
namen = [e[0] for e in ueb]
check("Systeme ohne Core fallen raus", "Gibt es nicht" not in namen,
      str(namen))
check("die anderen sind drin", set(namen) == {"SNES", "NES", "NeXT"},
      str(namen))
check("und jedes bringt seine Fassungen mit",
      all(len(e[3]) >= 1 for e in ueb))

# ---------------------------------------------------------------------------
print()
print("Test 8: der Startweg benutzt das auch wirklich")
# ---------------------------------------------------------------------------
quelle = io.open(os.path.join(_REPO, "frontend", "frontend.py"),
                 encoding="utf-8").read()
check("das Modul ist eingebunden", "import fe.cores as CORES" in quelle)
check("es gibt genau drei Aufloesungen im Startweg",
      quelle.count("CORES.aufloesen(") == 3,
      "%d" % quelle.count("CORES.aufloesen("))
# Der RA-Core muss Vorrang behalten - er ist ja gerade ausdruecklich
# gewaehlt worden.
for stelle in ("rbf, setname = ra_choice\n                        else:\n"
               "                            rbf = CORES.aufloesen(syskey, rbf)",
               "rbf, setname = ra_choice\n                            else:\n"
               "                                rbf = CORES.aufloesen(syskey, rbf)"):
    check("der RA-Core behaelt Vorrang", stelle in quelle)
check("es gibt einen Menuepunkt", '"cores"' in io.open(
    os.path.join(_REPO, "frontend", "fe", "menu.py"),
    encoding="utf-8").read())
check("und einen Handler", 'kind == "cores"' in quelle)
check("der Bildschirm faengt Fehler ab",
      "cores_bildschirm CRASH" in quelle)

import fe.translations as T                              # noqa: E402
for schluessel in ("sys_cores", "cores_titel", "cores_leer",
                   "cores_automatisch", "cores_fehlt", "cores_anzahl",
                   "cores_hinweis", "cores_gespeichert"):
    eintrag = T.TRANSLATIONS.get(schluessel)
    check("Text %-20s in beiden Sprachen" % schluessel,
          bool(eintrag) and bool(eintrag.get("de")) and bool(eintrag.get("en")),
          "" if eintrag else "fehlt ganz")

# ---------------------------------------------------------------------------
print()
print("Test 9: dieses Modul laedt und aktualisiert KEINE Cores")
# ---------------------------------------------------------------------------
# Das ist die Aufgabe von update_all. Es hier noch einmal zu bauen
# hiesse, eine zweite Quelle der Wahrheit fuer die wichtigsten
# Dateien auf der Karte zu schaffen.
modul = io.open(os.path.join(_REPO, "frontend", "fe", "cores.py"),
                encoding="utf-8").read()
for verboten in ("urllib", "requests", "subprocess", "os.remove",
                 "shutil", "os.unlink"):
    check("kein %s" % verboten, verboten not in modul)

# ---------------------------------------------------------------------------
print()
print("Test 10: der Auswahlbildschirm zeichnet - auf Roehre und HDMI")
# ---------------------------------------------------------------------------
# Getrieben wird die ECHTE Eingabeschleife mit erfundenen
# Tastendruecken, nicht eine Nachbildung davon.
sys.path.insert(0, _HIER)
import _harness as H                                     # noqa: E402

fm = H.fm
C.WAHL_DATEI = WAHL
# Test 3 hat eine der beiden SNES-Fassungen geloescht (das war ja
# gerade der Punkt dort). Fuer den Bildschirm braucht es wieder mehr
# als eine - sonst zeigt er voellig zu Recht "nichts zu waehlen" und
# dieser Test misst gar nichts. Selbst hineingelaufen.
anlegen("_Console", "SNES_20260603.rbf")


class Tasten(object):
    def __init__(self, folge):
        self.folge = list(folge)

    def read_action(self, timeout=None):
        return self.folge.pop(0) if self.folge else "back"


def bildschirm(folge, b=1920, h=1080):
    H.SCREEN[:] = [b, h]
    f = H.make_frontend(page=0)
    f.inp = Tasten(folge)
    f.draw = lambda *a, **k: None
    f.cores_bildschirm()
    return f


for name, b, h in (("CRT 320x240", 320, 240), ("CRT 640x480", 640, 480),
                   ("HDMI 1920x1080", 1920, 1080),
                   ("hochkant 1080x1920", 1080, 1920)):
    try:
        bildschirm(["down", "right", "right", "up", "left", "back"], b, h)
        ok, fehler = True, ""
    except Exception as e:                               # noqa: BLE001
        ok, fehler = False, "%s: %s" % (type(e).__name__, e)
        import traceback
        traceback.print_exc(limit=3)
    check("%-18s zeichnet ohne Fehler" % name, ok, fehler)

# Und: eine Auswahl, die dort getroffen wurde, landet in der Datei.
C.wahl_speichern({}, WAHL)
bildschirm(["right", "back"])
danach = C.wahl_laden(WAHL)
check("eine getroffene Auswahl wird gespeichert", bool(danach), str(danach))
check("und sie zeigt auf eine Datei, die es gibt",
      all(C.core_existiert(v) for v in danach.values()), str(danach))

shutil.rmtree(tmp, ignore_errors=True)

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
