#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Eine Core-Fassung fuer GENAU EIN Spiel (Build 310).

NUTZERWUNSCH vom 08.11., in seiner Prioritaetenliste als der
wichtigste Punkt des wichtigsten Bereichs markiert:

    "Besonders wichtig: Core-Auswahl pro Spiel, damit beispielsweise
     ein bestimmtes Spiel mit einer anderen Core-Version gestartet
     werden kann."

WARUM DAS NICHT DASSELBE IST WIE DIE WAHL JE SYSTEM. Der Kopf von
fe/cores.py nennt den Fall, aus dem das Modul entstanden ist: beim
NeXT-Core liegen vier Fassungen nebeneinander, mit sprechenden Namen
wie "scsi_dma_csr_fix". Wer die eine braucht, die SEINEN Fehler
behebt, musste bisher das ganze System darauf umstellen.

WAS DIESER TEST SICHERT:
  1. die Wahl je Spiel schlaegt die Wahl je System,
  2. die Sicherheitsregel gilt auch hier: eine gemerkte Fassung gilt
     nur, solange ihre DATEI da ist,
  3. ohne Wahl je Spiel aendert sich GAR NICHTS - aufloesen_spiel()
     liefert dann genau das, was aufloesen() liefert,
  4. die Regel steht nur EINMAL da (aufloesen_spiel ruft aufloesen),
  5. der Schluessel ist der ROM-Pfad, nicht der Anzeigename,
  6. geschrieben wird ueber .tmp + os.replace(),
  7. alle drei Startwege benutzen die neue Funktion,
  8. der Menuepunkt erscheint nur, wenn es mehr als eine Fassung
     gibt,
  9. und jeder Text existiert in beiden Sprachen.

Ausfuehren:
    python3 tools/test_core_wahl_spiel.py
"""
import json
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
_FP = os.path.join(_REPO, "frontend", "frontend.py")

fails = []


def check(name, ok, info=""):
    if ok:
        print("  OK   %s %s" % (name, info))
    else:
        print("  FEHL %s %s" % (name, info))
        fails.append(name)


print(__doc__.strip().split("\n")[0])
print()

# ---------------------------------------------------------------------------
# Ein Kartenbaum mit vier NeXT-Fassungen - genau der Fall aus dem Kopf
# von fe/cores.py, und zwar mit seinen echten Dateinamen.
# ---------------------------------------------------------------------------
WURZEL = tempfile.mkdtemp(prefix="corewahl_")
os.makedirs(os.path.join(WURZEL, "_Computer"))
os.makedirs(os.path.join(WURZEL, "_Console"))
NEXT = ["NeXT_20260908.rbf",
        "NeXT_20260911_scsi_dma_csr_fix.rbf",
        "NeXT_20260912_recording_adc_fix.rbf",
        "NeXT_20260914_moves_fc.rbf"]
for n in NEXT:
    open(os.path.join(WURZEL, "_Computer", n), "w").close()
open(os.path.join(WURZEL, "_Console", "SNES_20260603.rbf"), "w").close()
_ALT_BASE = CORES.BASE
CORES.BASE = WURZEL

SYS_WAHL = os.path.join(WURZEL, "core_wahl.json")
SPIEL_WAHL = os.path.join(WURZEL, "core_wahl_spiel.json")
ROM_A = "/media/fat/games/NeXT/Spiel A.hdd"
ROM_B = "/media/fat/games/NeXT/Spiel B.hdd"
STANDARD = "_Computer/NeXT"
NEU = "_Computer/NeXT_20260914_moves_fc"
FIX = "_Computer/NeXT_20260911_scsi_dma_csr_fix"

# ---------------------------------------------------------------------------
print("Test 1: vier Fassungen, und die neueste steht vorn")
# ---------------------------------------------------------------------------
_f = CORES.fassungen(STANDARD)
check("alle vier gefunden", len(_f) == 4, "%r" % (_f,))
check("die neueste zuerst", _f[0] == NEU, "%r" % (_f[0],))
check("SNES ist nicht dabei",
      all("SNES" not in x for x in _f),
      "die Praefix-Falle aus fe/cores.py")

# ---------------------------------------------------------------------------
print()
print("Test 2: ohne Wahl je Spiel aendert sich GAR NICHTS")
# ---------------------------------------------------------------------------
# Die wichtigste Pruefung des Builds: ein neuer Weg, der im Normalfall
# etwas anderes tut als der alte, waere eine Verschlechterung fuer
# alle, die ihn nie benutzen.
for _syswahl in ({}, {"next": FIX}):
    with open(SYS_WAHL, "w") as fh:
        json.dump(_syswahl, fh)
    _alt = CORES.aufloesen("next", STANDARD, SYS_WAHL)
    _neu = CORES.aufloesen_spiel(ROM_A, "next", STANDARD, SYS_WAHL,
                                 SPIEL_WAHL)
    check("gleiches Ergebnis bei Systemwahl %r"
          % (list(_syswahl.values()) or "keine",),
          _alt == _neu, "%r gegen %r" % (_alt, _neu))
_leer = CORES.aufloesen_spiel(None, "next", STANDARD, SYS_WAHL, SPIEL_WAHL)
check("auch ohne ROM-Pfad", _leer == CORES.aufloesen("next", STANDARD,
                                                     SYS_WAHL),
      "%r" % (_leer,))

# ---------------------------------------------------------------------------
print()
print("Test 3: die Wahl je Spiel schlaegt die Wahl je System")
# ---------------------------------------------------------------------------
with open(SYS_WAHL, "w") as fh:
    json.dump({"next": FIX}, fh)
CORES.spiel_wahl_setzen(ROM_A, NEU, SPIEL_WAHL)
check("Spiel A nimmt seine eigene Fassung",
      CORES.aufloesen_spiel(ROM_A, "next", STANDARD, SYS_WAHL,
                            SPIEL_WAHL) == NEU,
      "%r" % (CORES.aufloesen_spiel(ROM_A, "next", STANDARD, SYS_WAHL,
                                    SPIEL_WAHL),))
check("Spiel B bleibt bei der Systemwahl",
      CORES.aufloesen_spiel(ROM_B, "next", STANDARD, SYS_WAHL,
                            SPIEL_WAHL) == FIX,
      "%r - genau darum geht es: EIN Spiel abweichen lassen, nicht "
      "alle" % (CORES.aufloesen_spiel(ROM_B, "next", STANDARD, SYS_WAHL,
                                      SPIEL_WAHL),))
CORES.spiel_wahl_setzen(ROM_A, None, SPIEL_WAHL)
check("und zuruecknehmen geht auch",
      CORES.aufloesen_spiel(ROM_A, "next", STANDARD, SYS_WAHL,
                            SPIEL_WAHL) == FIX)
check("die Datei haelt den Pfad als Schluessel",
      CORES.spiel_wahl_holen(ROM_A, SPIEL_WAHL) is None
      and CORES.spiel_wahl_setzen(ROM_A, NEU, SPIEL_WAHL).get(ROM_A) == NEU,
      "zwei Spiele koennen gleich HEISSEN, aber nicht am gleichen Pfad "
      "liegen")

# ---------------------------------------------------------------------------
print()
print("Test 4: die Sicherheitsregel gilt auch je Spiel")
# ---------------------------------------------------------------------------
# update_all loescht bei jedem Lauf alte Cores. Eine gemerkte Wahl
# zeigt danach ins Leere - und ohne diese Pruefung liesse sich das
# Spiel nicht mehr starten, und zwar still.
CORES.spiel_wahl_setzen(ROM_A, FIX, SPIEL_WAHL)
check("solange die Datei da ist, gilt sie",
      CORES.aufloesen_spiel(ROM_A, "next", STANDARD, SYS_WAHL,
                            SPIEL_WAHL) == FIX)
os.remove(os.path.join(WURZEL, "_Computer",
                       "NeXT_20260911_scsi_dma_csr_fix.rbf"))
with open(SYS_WAHL, "w") as fh:
    json.dump({}, fh)
_nach = CORES.aufloesen_spiel(ROM_A, "next", STANDARD, SYS_WAHL, SPIEL_WAHL)
check("ist sie weg, faellt es sauber zurueck", _nach == STANDARD,
      "%r - lieber der Core, den MiSTer selbst waehlt, als gar keiner"
      % (_nach,))
check("die Wahl bleibt dabei GEMERKT",
      CORES.spiel_wahl_holen(ROM_A, SPIEL_WAHL) == FIX,
      "sonst waere sie nach einem update_all-Lauf endgueltig weg - "
      "kommt die Datei wieder, soll sie wieder gelten")
# Und die Gegenprobe: zurueck ist sie, sobald die Datei wieder da ist.
open(os.path.join(WURZEL, "_Computer",
                  "NeXT_20260911_scsi_dma_csr_fix.rbf"), "w").close()
check("und greift wieder, sobald die Datei zurueck ist",
      CORES.aufloesen_spiel(ROM_A, "next", STANDARD, SYS_WAHL,
                            SPIEL_WAHL) == FIX)

# ---------------------------------------------------------------------------
print()
print("Test 5: eine kaputte Datei ist 'keine Wahl', kein Absturz")
# ---------------------------------------------------------------------------
with open(SPIEL_WAHL, "w") as fh:
    fh.write("{das ist kein json")
check("kaputtes JSON gibt ein leeres Dict",
      CORES.spiel_wahl_laden(SPIEL_WAHL) == {})
check("und aufloesen_spiel faellt zurueck",
      CORES.aufloesen_spiel(ROM_A, "next", STANDARD, SYS_WAHL,
                            SPIEL_WAHL) == STANDARD)
with open(SPIEL_WAHL, "w") as fh:
    json.dump(["eine Liste"], fh)
check("eine Liste statt eines Dicts ebenso",
      CORES.spiel_wahl_laden(SPIEL_WAHL) == {})
with open(SPIEL_WAHL, "w") as fh:
    json.dump({"a": 5, "b": "", "c": "_Computer/NeXT_20260908"}, fh)
check("Werte, die keine Namen sind, fliegen raus",
      CORES.spiel_wahl_laden(SPIEL_WAHL)
      == {"c": "_Computer/NeXT_20260908"},
      "%r" % (CORES.spiel_wahl_laden(SPIEL_WAHL),))
os.remove(SPIEL_WAHL)
check("eine fehlende Datei auch",
      CORES.spiel_wahl_laden(SPIEL_WAHL) == {}
      and CORES.spiel_wahl_holen(ROM_A, SPIEL_WAHL) is None)

# ---------------------------------------------------------------------------
print()
print("Test 6: geschrieben wird ueber .tmp und os.replace()")
# ---------------------------------------------------------------------------
_q = open(os.path.join(_REPO, "frontend", "fe", "cores.py"),
          encoding="utf-8").read()
_sp = nur_code(koerper(_q, "spiel_wahl_speichern"))
check("die Funktion wurde gefunden", bool(_sp.strip()))
check("erst .tmp", '".tmp"' in _sp or "'.tmp'" in _sp)
check("dann os.replace()", "os.replace(" in _sp,
      "eine halb geschriebene Datei betrifft hier den Core-Start")
check("und niemals direkt auf die Zieldatei",
      _sp.count("open(") == 1 and "open(tmp" in _sp,
      "%d open()" % _sp.count("open("))
# Gegenprobe am echten Dateisystem: nach dem Schreiben darf kein .tmp
# uebrig sein.
CORES.spiel_wahl_setzen(ROM_B, NEU, SPIEL_WAHL)
check("kein .tmp bleibt liegen", not os.path.exists(SPIEL_WAHL + ".tmp"))
with open(SPIEL_WAHL) as fh:
    check("und die Datei ist gueltiges JSON",
          json.load(fh) == {ROM_B: NEU})

# ---------------------------------------------------------------------------
print()
print("Test 7: die Regel steht nur EINMAL da")
# ---------------------------------------------------------------------------
_as = nur_code(koerper(_q, "aufloesen_spiel"))
check("aufloesen_spiel() ruft aufloesen()", "aufloesen(" in _as
      and "return aufloesen(" in _as)
check("und baut core_existiert nur fuer den eigenen Fall nach",
      _as.count("core_existiert(") == 1,
      "%d - die Pruefung fuer die SYSTEMwahl gehoert in aufloesen(), "
      "sonst stuende sie zweimal da" % _as.count("core_existiert("))

# ---------------------------------------------------------------------------
print()
print("Test 8: alle drei Startwege benutzen die neue Funktion")
# ---------------------------------------------------------------------------
_qf = open(_FP, encoding="utf-8", errors="replace").read()
# GEZAEHLT WIRD IM CODE, NICHT IM TEXT. Die erste Fassung dieses Tests
# zaehlte am rohen Quelltext - und fand einen zweiten Aufruf, der gar
# keiner war: in run() steht "CORES.aufloesen()" in einem KOMMENTAR.
# Der Kommentar war ueberdies veraltet und wurde mitkorrigiert, aber
# der Test darf sich davon gar nicht erst beeindrucken lassen.
_code = nur_code(_qf)
_mit = len(re.findall(r"CORES\.aufloesen_spiel\(", _code))
_ohne = len(re.findall(r"CORES\.aufloesen\(", _code))
check("drei Aufrufe von aufloesen_spiel()", _mit == 3, "%d" % _mit)
check("und genau einer von aufloesen() - der Auswahlbildschirm",
      _ohne == 1,
      "%d. Bliebe im STARTWEG noch ein alter Aufruf stehen, wuerde die "
      "Wahl je Spiel dort stillschweigend nicht gelten - genau der "
      "halb angewandte Fix aus Build 293" % _ohne)
_bs = nur_code(koerper(_qf, "core_spiel_bildschirm", "Frontend"))
check("der Auswahlbildschirm ist der eine Aufrufer",
      "CORES.aufloesen(" in _bs,
      "er zeigt, was 'automatisch' bedeutet - und fragt dafuer "
      "dieselbe Funktion wie der Startweg")

# ---------------------------------------------------------------------------
print()
print("Test 9: der Menuepunkt erscheint nur, wenn es etwas zu waehlen gibt")
# ---------------------------------------------------------------------------
_pruef = H.fm.Frontend._core_fassungen_zum_eintrag


class FeStub:
    pass


_stub = FeStub()
_spiel = ("Spiel A", "game", (ROM_A, ".hdd", "next", STANDARD, (2, "f", 0)))
check("vier Fassungen -> der Punkt erscheint",
      len(_pruef(_stub, _spiel)) == 4,
      "%r" % (len(_pruef(_stub, _spiel)),))
_eine = ("Super Mario", "game",
         ("/media/fat/games/SNES/smw.sfc", ".sfc", "snes",
          "_Console/SNES", (2, "f", 0)))
check("nur eine Fassung -> der Punkt erscheint NICHT",
      _pruef(_stub, _eine) == [],
      "ein Punkt, der einen leeren Bildschirm oeffnet, ist einer zu "
      "viel")
check("ein Ordner ist kein Spiel",
      _pruef(_stub, ("Ordner", "dir", "/irgendwo")) == [])
check("None faellt nicht um", _pruef(_stub, None) == [])
check("ein zu kurzer Eintrag auch nicht",
      _pruef(_stub, ("x", "game")) == [])
check("und ein Eintrag ohne rbf ebenso",
      _pruef(_stub, ("x", "game", ("rom", ".bin", "sys", "", (2, "f", 0))))
      == [])
_km = nur_code(koerper(_qf, "kontextmenue", "Frontend"))
check("das Kontextmenue fragt vorher nach",
      "_core_fassungen_zum_eintrag(" in _km and '"core_spiel"' in _km)
check("und der Zweig behandelt die Wahl",
      'gewaehlt == "core_spiel"' in _qf
      and "core_spiel_bildschirm CRASH" in _qf)

# ---------------------------------------------------------------------------
print()
print("Test 10: jeder benutzte Text existiert in beiden Sprachen")
# ---------------------------------------------------------------------------
_benutzt = sorted(set(re.findall(r't\(\s*"([a-z0-9_]+)"', _bs))
                  | {"ctx_core_spiel"})
check("die Seite benutzt ueberhaupt Texte", len(_benutzt) >= 5,
      "%d: %r" % (len(_benutzt), _benutzt))
_fehlt = [k for k in _benutzt if k not in TR.TRANSLATIONS]
check("alle Schluessel sind eingetragen", not _fehlt, "fehlt: %r" % (_fehlt,))
_halb = [k for k in _benutzt if k in TR.TRANSLATIONS
         and not (TR.TRANSLATIONS[k].get("de")
                  and TR.TRANSLATIONS[k].get("en"))]
check("und in de UND en vorhanden", not _halb, "halb: %r" % (_halb,))
for _k in ("corespiel_titel", "corespiel_auto", "corespiel_gesetzt"):
    for _spr in ("de", "en"):
        _txt = TR.TRANSLATIONS[_k][_spr]
        check("%s/%s hat genau einen Platzhalter" % (_k, _spr),
              len(re.findall(r"%[sd]", _txt)) == 1, "%r" % (_txt,))

CORES.BASE = _ALT_BASE
shutil.rmtree(WURZEL, ignore_errors=True)

# ---------------------------------------------------------------------------
print()
if fails:
    print("ROT: %d Pruefung(en) fehlgeschlagen:" % len(fails))
    for f in fails:
        print("   - %s" % f)
    sys.exit(1)
print("ALLES GRUEN")
