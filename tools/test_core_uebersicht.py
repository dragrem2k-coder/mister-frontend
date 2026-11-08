#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Die Core-Uebersicht: was liegt drauf, wie alt ist es (Build 309).

NUTZERWUNSCH vom 08.11., aus einer Liste von sieben Punkten:
"Verbesserungen bei Core-Auswahl und Core-Verwaltung" und "Core
Updates mit Anzeige verfuegbarer Aktualisierungen".

DER ZWEITE WUNSCH IST NICHT EHRLICH ZU BAUEN, und das steht seit Build
250 im Kopf von fe/corestand.py - mit der Begruendung aus fe/cores.py:

    "dafuer muesste das Frontend die Datenbanken des MiSTer-Downloaders
     selbst auswerten und ihre Versionslogik nachbauen - genau die
     zweite Quelle der Wahrheit, die fe/cores.py ausschliesst."

WAS SEHR WOHL GEHT, ist die Frage dahinter: WELCHE MEINER CORES SIND
ALT? Die Antwort steht in den Dateinamen auf seiner eigenen Karte.

WAS DIESER TEST SICHERT:
  1. acht Ziffern sind nicht automatisch ein Datum - der Wert wird
     geprueft, und ein unlesbarer bekommt None,
  2. None heisst ueberall 'unbekannt' und nie 'sehr alt',
  3. die Praefix-Falle aus fe/cores.py gilt auch hier,
  4. 'nach Alter' stellt die aeltesten nach oben und die undatierten
     nach UNTEN,
  5. die Reihenfolge ist bei gleichen Werten stabil,
  6. der Bestand zaehlt richtig, auch ohne ein einziges Datum,
  7. die Seite ist verdrahtet: Menuepunkt, Zweig, Methode,
  8. sie schreibt NICHTS - eine Leseseite bleibt eine Leseseite,
  9. und jeder Text, den sie benutzt, existiert in beiden Sprachen.

Ausfuehren:
    python3 tools/test_core_uebersicht.py
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H          # noqa: E402

import fe.corestand as CS     # noqa: E402
import fe.translations as TR  # noqa: E402
from _quelle import koerper, nur_code                     # noqa: E402

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

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
print("Test 1: acht Ziffern sind nicht automatisch ein Datum")
# ---------------------------------------------------------------------------
check("ein normales Datum", CS.fassung_datum("20260603") == (2026, 6, 3),
      "%r" % (CS.fassung_datum("20260603"),))
check("mit sprechendem Zusatz dahinter",
      CS.fassung_datum("20260912_recording_adc_fix") == (2026, 9, 12),
      "%r" % (CS.fassung_datum("20260912_recording_adc_fix"),))
check("ein unmoegliches Jahr ist KEIN Datum",
      CS.fassung_datum("12345678") is None,
      "sonst stuende dieser Core mit Jahr 1234 ganz oben in der Liste "
      "'aelteste zuerst'")
check("ein unmoeglicher Monat ebenso",
      CS.fassung_datum("20261303") is None)
check("ein unmoeglicher Tag ebenso",
      CS.fassung_datum("20260632") is None)
check("zu kurz ist kein Datum", CS.fassung_datum("2026") is None)
check("leer ist kein Datum", CS.fassung_datum("") is None)
check("None ist kein Datum", CS.fassung_datum(None) is None)
check("Ziffern MITTENDRIN zaehlen nicht",
      CS.fassung_datum("v20260603") is None,
      "das Datum steht am Anfang der Fassung, sonst waere jeder Name "
      "mit Zahl ein Datum")

# ---------------------------------------------------------------------------
print()
print("Test 2: das Alter - und was None bedeutet")
# ---------------------------------------------------------------------------
# Fester Zeitpunkt, damit der Test nicht mit dem Kalender wandert:
# 2026-11-08, 12:00 Ortszeit.
import time as _t                                        # noqa: E402
JETZT = _t.mktime((2026, 11, 8, 12, 0, 0, 0, 1, -1))
check("heute ist 0 Tage alt",
      CS.alter_tage((2026, 11, 8), JETZT) == 0,
      "%r" % (CS.alter_tage((2026, 11, 8), JETZT),))
check("gestern ist 1 Tag alt",
      CS.alter_tage((2026, 11, 7), JETZT) == 1,
      "%r" % (CS.alter_tage((2026, 11, 7), JETZT),))
_fuenf = CS.alter_tage((2021, 11, 8), JETZT)
check("fuenf Jahre sind rund 1826 Tage",
      1824 <= _fuenf <= 1828, "%r" % (_fuenf,))
check("ohne Datum kein Alter", CS.alter_tage(None, JETZT) is None)
_zukunft = CS.alter_tage((2026, 12, 1), JETZT)
check("ein Datum aus der Zukunft gibt ein NEGATIVES Alter",
      _zukunft is not None and _zukunft < 0,
      "%r - der MiSTer hat ohne Netz keine richtige Uhr; das auf 0 zu "
      "klemmen hiesse, eine falsche Uhr als richtig auszugeben"
      % (_zukunft,))

# ---------------------------------------------------------------------------
print()
print("Test 3: die Uebersicht an einem gebauten Kartenbaum")
# ---------------------------------------------------------------------------
import tempfile                                          # noqa: E402

WURZEL = tempfile.mkdtemp(prefix="coreueb_")
BAUM = {
    "_Console": ["SNES_20260603.rbf", "SNES_Tracker_20260101.rbf",
                 "NES_20210204.rbf", "Genesis.rbf"],
    "_Computer": ["NeXT_20260912_scsi_dma_csr_fix.rbf",
                  "C64_20260815.rbf"],
    "_Arcade": ["Galaga_12345678.rbf"],
}
for _o, _dateien in BAUM.items():
    os.makedirs(os.path.join(WURZEL, _o))
    for _d in _dateien:
        open(os.path.join(WURZEL, _o, _d), "w").close()
    # Eine Datei, die KEIN Core ist - sie darf nicht mitzaehlen.
    open(os.path.join(WURZEL, _o, "liesmich.txt"), "w").close()

UEB = CS.uebersicht(wurzel=WURZEL, jetzt=JETZT)
check("alle sieben .rbf gefunden, und nur die", len(UEB) == 7,
      "%d: %r" % (len(UEB), sorted(e["rel"] for e in UEB)))
_nach_kopf = {e["kopf"]: e for e in UEB}
check("die Praefix-Falle haelt",
      "SNES" in _nach_kopf and "SNES_Tracker" in _nach_kopf,
      "SNES und SNES_Tracker sind zwei Cores - sonst waehlt eine "
      "Auswahl fuer SNES stillschweigend den Tracker")
check("der Ordner steht dabei",
      _nach_kopf["SNES"]["ordner"] == "_Console"
      and _nach_kopf["C64"]["ordner"] == "_Computer",
      "dieselbe Datei in zwei Ordnern waere sonst dasselbe")
check("der sprechende Zusatz bleibt in der Fassung",
      _nach_kopf["NeXT"]["fassung"] == "20260912_scsi_dma_csr_fix",
      "%r" % (_nach_kopf["NeXT"]["fassung"],))
check("und wird trotzdem richtig datiert",
      _nach_kopf["NeXT"]["datum"] == (2026, 9, 12))
check("ein Core ohne Datum hat keins",
      _nach_kopf["Genesis"]["datum"] is None
      and _nach_kopf["Genesis"]["alter"] is None)
check("ein Core mit Unsinn im Namen ebenso",
      _nach_kopf["Galaga"]["datum"] is None,
      "12345678 ist kein Datum")
check("der alte NES-Core ist ueber vier Jahre alt",
      _nach_kopf["NES"]["alter"] > 1700,
      "%r Tage" % (_nach_kopf["NES"]["alter"],))

# ---------------------------------------------------------------------------
print()
print("Test 4: sortieren - und wo die Undatierten landen")
# ---------------------------------------------------------------------------
_alter = CS.sortiert(UEB, "alter")
check("der aelteste steht oben", _alter[0]["kopf"] == "NES",
      "%r" % ([e["kopf"] for e in _alter],))
_ohne = [e["kopf"] for e in _alter if e["datum"] is None]
_letzte = [e["kopf"] for e in _alter[-len(_ohne):]]
check("die Undatierten stehen UNTEN", sorted(_ohne) == sorted(_letzte),
      "%r - unbekannt ist nicht alt" % (_letzte,))
_mit = [e["datum"] for e in _alter if e["datum"]]
check("und die Datierten steigen an", _mit == sorted(_mit),
      "%r" % (_mit,))

_name = CS.sortiert(UEB, "name")
check("nach Name ist alphabetisch",
      [e["kopf"] for e in _name]
      == sorted((e["kopf"] for e in UEB), key=str.lower),
      "%r" % ([e["kopf"] for e in _name],))
_ordner = CS.sortiert(UEB, "ordner")
check("nach Ordner stehen die Ordner beisammen",
      [e["ordner"] for e in _ordner]
      == sorted(e["ordner"] for e in UEB),
      "%r" % ([e["ordner"] for e in _ordner],))

# GEGENPROBE: eine Sortierung, die sich bei gleichen Werten nicht
# entscheidet, laesst den Zeiger beim naechsten Zeichnen woanders
# stehen. Zwei Cores mit demselben Datum und derselbe Aufruf zweimal.
_gleich = [
    {"rel": "_Console/B_20260101.rbf", "ordner": "_Console", "kopf": "B",
     "fassung": "20260101", "datum": (2026, 1, 1), "alter": 311},
    {"rel": "_Console/A_20260101.rbf", "ordner": "_Console", "kopf": "A",
     "fassung": "20260101", "datum": (2026, 1, 1), "alter": 311},
]
_s1 = [e["rel"] for e in CS.sortiert(list(_gleich), "alter")]
_s2 = [e["rel"] for e in CS.sortiert(list(reversed(_gleich)), "alter")]
check("bei gleichem Datum ist die Reihenfolge stabil", _s1 == _s2,
      "%r gegen %r" % (_s1, _s2))
check("eine unbekannte Sortierart faellt auf 'alter' zurueck",
      [e["kopf"] for e in CS.sortiert(UEB, "quatsch")]
      == [e["kopf"] for e in _alter],
      "lieber eine sinnvolle Liste als eine leere")

# ---------------------------------------------------------------------------
print()
print("Test 5: der Bestand")
# ---------------------------------------------------------------------------
B = CS.bestand(UEB)
check("gesamt stimmt", B["gesamt"] == 7, "%r" % (B["gesamt"],))
check("mit Datum sind es fuenf", B["mit_datum"] == 5,
      "%r - Genesis und Galaga haben keins" % (B["mit_datum"],))
check("je Ordner stimmt",
      B["ordner"] == {"_Console": 4, "_Computer": 2, "_Arcade": 1},
      "%r" % (B["ordner"],))
check("das aelteste Datum", B["aeltestes"] == (2021, 2, 4),
      "%r" % (B["aeltestes"],))
check("das neueste Datum", B["neuestes"] == (2026, 9, 12),
      "%r" % (B["neuestes"],))
_leer = CS.bestand([{"rel": "x/y.rbf", "ordner": "x", "kopf": "y",
                     "fassung": "", "datum": None, "alter": None}])
check("ohne ein einziges Datum bleibt es None",
      _leer["aeltestes"] is None and _leer["neuestes"] is None
      and _leer["gesamt"] == 1,
      "'kein lesbares Datum' ist nicht 'keine Cores'")
check("und ganz ohne Eintraege auch",
      CS.bestand([])["gesamt"] == 0 and CS.bestand(None)["gesamt"] == 0)

# ---------------------------------------------------------------------------
print()
print("Test 6: die Seite ist verdrahtet")
# ---------------------------------------------------------------------------
_FP = os.path.join(_REPO, "frontend", "frontend.py")
_qf = open(_FP, encoding="utf-8", errors="replace").read()
_qm = open(os.path.join(_REPO, "frontend", "fe", "menu.py"),
           encoding="utf-8").read()
check("die Methode gibt es",
      hasattr(H.fm.Frontend, "core_uebersicht_bildschirm"))
check("der Menuepunkt steht im Systemmenue",
      '"core_uebersicht"' in _qm)
check("und direkt bei der Core-Wahl",
      _qm.index('"core_uebersicht"') - _qm.index('"cores", None') < 400,
      "zwei Seiten derselben Frage gehoeren nebeneinander")
check("der Zweig faengt den Aufruf ab",
      'elif kind == "core_uebersicht":' in _qf
      and "core_uebersicht_bildschirm CRASH" in _qf,
      "eine Seite darf das Frontend nicht mitnehmen")

_meth = nur_code(koerper(_qf, "core_uebersicht_bildschirm", "Frontend"))
check("die Methode wurde gefunden", bool(_meth.strip()),
      "%d Zeichen" % len(_meth))
check("sie liest aus fe/corestand.py",
      "CSTAND.uebersicht(" in _meth and "CSTAND.sortiert(" in _meth
      and "CSTAND.bestand(" in _meth,
      "und baut die Rechnung nicht ein zweites Mal nach")
check("OK wechselt die Sortierung",
      'akt == "ok"' in _meth and "art_i" in _meth)
check("und springt dabei nach oben",
      "erste = 0" in _meth,
      "nach dem Wechsel stuende an derselben Stelle ein anderer Core")

# ---------------------------------------------------------------------------
print()
print("Test 7: eine Leseseite schreibt NICHTS")
# ---------------------------------------------------------------------------
# Dieselbe Bauart wie test_anleitung.py: nicht 'wir haben nicht vor zu
# schreiben', sondern 'es steht kein Schreibbefehl drin'.
for _verboten in ("open(", "os.remove", "os.rename", "os.replace",
                  "os.makedirs", "shutil.", "os.unlink", "os.rmdir"):
    check("kein %s" % _verboten, _verboten not in _meth,
          "eine Uebersicht veraendert die Karte nicht")
check("und kein Core wird gestartet",
      "launch" not in _meth and ".mgl" not in _meth)

# ---------------------------------------------------------------------------
print()
print("Test 8: jeder benutzte Text existiert in beiden Sprachen")
# ---------------------------------------------------------------------------
# Eine fehlende Uebersetzung faellt sonst erst auf dem Fernseher auf -
# und dort steht dann der Schluessel selbst.
_benutzt = sorted(set(re.findall(r'(?<![A-Za-z0-9_])t\(\s*"([a-z0-9_]+)"', _meth)))
check("die Seite benutzt ueberhaupt Texte", len(_benutzt) >= 6,
      "%d: %r" % (len(_benutzt), _benutzt))
_fehlt = [k for k in _benutzt if k not in TR.TRANSLATIONS]
check("alle Schluessel sind eingetragen", not _fehlt, "fehlt: %r" % (_fehlt,))
_halb = [k for k in _benutzt if k in TR.TRANSLATIONS
         and not (TR.TRANSLATIONS[k].get("de")
                  and TR.TRANSLATIONS[k].get("en"))]
check("und in de UND en vorhanden", not _halb, "halb: %r" % (_halb,))
_fehlt_m = [k for k in ("sys_core_uebersicht",) if k not in TR.TRANSLATIONS]
check("der Menuepunkt hat auch einen Text", not _fehlt_m,
      "fehlt: %r" % (_fehlt_m,))
# Die Platzhalter muessen zur Zahl der Werte passen - ein %d zu viel
# ist ein Absturz mitten im Zeichnen.
for _k, _n in (("coreueb_bestand", 1), ("coreueb_fuss", 4),
               ("vor_tagen", 1)):
    for _spr in ("de", "en"):
        _txt = TR.TRANSLATIONS[_k][_spr]
        check("%s/%s hat %d Platzhalter" % (_k, _spr, _n),
              len(re.findall(r"%[sd]", _txt)) == _n,
              "%r" % (_txt,))

import shutil as _sh                                     # noqa: E402
_sh.rmtree(WURZEL, ignore_errors=True)

# ---------------------------------------------------------------------------
print()
if fails:
    print("ROT: %d Pruefung(en) fehlgeschlagen:" % len(fails))
    for f in fails:
        print("   - %s" % f)
    sys.exit(1)
print("ALLES GRUEN")
