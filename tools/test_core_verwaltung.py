#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Die Core-Auswahl zeigt jetzt alles (Build 312).

NUTZERWUNSCH vom 08.11., Prioritaet 1 seiner Liste - zwei Punkte, die
auf dieser Seite fehlten:

    "Fehlende oder inkompatible Cores erkennen."
    "RetroAchievements-, Unstable- und Turbo-Versionen beruecksichtigen."

BIS BUILD 311 STANDEN DORT NUR SYSTEME MIT MEHR ALS EINER FASSUNG, mit
der Begruendung "eine Liste mit fuenfzig Zeilen, bei denen ueberall
'automatisch' steht, waere keine Verwaltung, sondern eine Tapete". Das
war richtig fuer die WAHL - und es macht eine AUSKUNFT unmoeglich: was
fehlt, kann man nicht zeigen, indem man es weglaesst.

DIE TAPETE WIRD STATTDESSEN FILTERBAR: alle / mehrere Fassungen / ohne
Core, umgeschaltet mit der Filtertaste.

WAS DIESER TEST SICHERT:
  1. uebersicht() verhaelt sich ohne das neue Kennzeichen GENAU wie
     vorher - der alte Aufrufer merkt nichts,
  2. mit auch_ohne=True kommen die Luecken dazu, und zwar mit einer
     LEEREN Fassungsliste,
  3. ra_fassung() fragt fe/ra_core.py und baut dessen Namensliste
     nicht nach,
  4. bestand_cores() zaehlt richtig,
  5. die Seite zeichnet auf Roehre, HDMI und hochkant,
  6. die Filtertaste schaltet wirklich um,
  7. links/rechts auf einer Zeile OHNE Wahl aendert nichts - und
     speichert vor allem nichts,
  8. und jeder Text existiert in beiden Sprachen.

Ausfuehren:
    python3 tools/test_core_verwaltung.py
"""
import json
import os
import re
import shutil
import sys
import tempfile
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H          # noqa: E402

import fe.cores as C          # noqa: E402
import fe.ra_core as RAC      # noqa: E402
import fe.translations as TR  # noqa: E402
from _quelle import koerper, nur_code                     # noqa: E402

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_QF = open(os.path.join(_REPO, "frontend", "frontend.py"),
           encoding="utf-8", errors="replace").read()
_BS = nur_code(koerper(_QF, "cores_bildschirm", "Frontend"))

fails = []


def check(name, ok, info=""):
    if ok:
        print("  OK   %s %s" % (name, info))
    else:
        print("  FEHL %s %s" % (name, info))
        fails.append(name)


print(__doc__.strip().split("\n")[0])
print()

WURZEL = tempfile.mkdtemp(prefix="coreverw_")
os.makedirs(os.path.join(WURZEL, "_Console"))
os.makedirs(os.path.join(WURZEL, "_Computer"))
for _n in ("SNES_20260603.rbf", "SNES_20260914.rbf",   # zwei Fassungen
           "NES_20260801.rbf"):                        # genau eine
    open(os.path.join(WURZEL, "_Console", _n), "w").close()
_ALT = C.BASE
C.BASE = WURZEL

SYSTEME = [
    ("SNES", "SNES", ["SNES"], "_Console/SNES", {}),
    ("NES", "NES", ["NES"], "_Console/NES", {}),
    ("Nintendo 64", "N64", ["N64"], "_Console/N64", {}),   # fehlt
    ("Mega Drive", "Genesis", ["MegaDrive"], "_Console/MegaDrive", {}),
]

# ---------------------------------------------------------------------------
print("Test 1: ohne das neue Kennzeichen aendert sich GAR NICHTS")
# ---------------------------------------------------------------------------
# Die wichtigste Pruefung: uebersicht() hat einen zweiten Aufrufer
# (fe/show.py und der Bericht), und der soll die Luecken NICHT sehen.
_alt = C.uebersicht(SYSTEME)
check("nur Systeme mit Core", [e[0] for e in _alt] == ["SNES", "NES"],
      "%r" % ([e[0] for e in _alt],))
check("und jedes mit seinen Fassungen",
      len(_alt[0][3]) == 2 and len(_alt[1][3]) == 1,
      "%r" % ([len(e[3]) for e in _alt],))
check("die neueste Fassung steht vorn",
      _alt[0][3][0].endswith("20260914"), "%r" % (_alt[0][3][0],))

# ---------------------------------------------------------------------------
print()
print("Test 2: mit auch_ohne=True kommen die Luecken dazu")
# ---------------------------------------------------------------------------
_neu = C.uebersicht(SYSTEME, auch_ohne=True)
check("alle vier Systeme", len(_neu) == 4, "%d" % len(_neu))
check("und die Reihenfolge bleibt die der Systemtabelle",
      [e[0] for e in _neu] == [x[0] for x in SYSTEME],
      "%r" % ([e[0] for e in _neu],))
_luecken = [e for e in _neu if not e[3]]
check("zwei Luecken, mit LEERER Fassungsliste",
      [e[0] for e in _luecken] == ["Nintendo 64", "Mega Drive"],
      "%r" % ([e[0] for e in _luecken],))
check("und sie tragen trotzdem ihren Standardnamen",
      all(e[2] for e in _luecken),
      "sonst koennte die Seite nicht sagen, WELCHE Datei fehlt")

# ---------------------------------------------------------------------------
print()
print("Test 3: ra_fassung() fragt fe/ra_core.py")
# ---------------------------------------------------------------------------
_ra_alt = RAC.RA_CORES_DIR_ABS
_ra_ordner = os.path.join(WURZEL, "_RA_Cores", "Cores")
RAC.RA_CORES_DIR_ABS = _ra_ordner
check("ohne den Ordner gibt es keine RA-Fassung",
      C.ra_fassung("SNES") is None)
os.makedirs(_ra_ordner)
open(os.path.join(_ra_ordner, "SNES.rbf"), "w").close()
check("mit der Datei schon", C.ra_fassung("SNES") is not None,
      "%r" % (C.ra_fassung("SNES"),))
check("und es ist der Pfad aus fe/ra_core.py",
      str(C.ra_fassung("SNES")).startswith(RAC.RA_CORES_DIR_REL),
      "%r" % (C.ra_fassung("SNES"),))
check("ein System ohne RA-Core bleibt leer",
      C.ra_fassung("N64") is None)
check("und ein leerer Systemkey auch",
      C.ra_fassung(None) is None and C.ra_fassung("") is None)
# Die Namensliste darf NICHT nachgebaut sein - sonst muesste man sie
# beim naechsten neuen System an zwei Stellen pflegen.
_q = open(os.path.join(_REPO, "frontend", "fe", "cores.py"),
          encoding="utf-8").read()
_rf = nur_code(koerper(_q, "ra_fassung"))
check("fe/cores.py baut die Namensliste nicht nach",
      "RA_CORE_NAME_CANDIDATES" not in _rf and "find_ra_core(" in _rf)
check("und importiert ra_core erst in der Funktion",
      "import fe.ra_core" in _rf,
      "eine Abhaengigkeit, die nur eine Anzeige braucht, gehoert "
      "nicht in den Startweg")

# ---------------------------------------------------------------------------
print()
print("Test 4: bestand_cores() zaehlt")
# ---------------------------------------------------------------------------
B = C.bestand_cores(SYSTEME)
check("vier Systeme", B["systeme"] == 4, "%r" % (B,))
check("zwei mit Core", B["mit_core"] == 2)
check("eines mit mehreren Fassungen", B["mehrere"] == 1)
check("zwei ohne Core", B["ohne"] == 2,
      "das ist die Zahl, die seinen Wunsch beantwortet")
check("eines mit RA-Fassung", B["ra"] == 1)
check("ohne Systeme bleibt alles null",
      C.bestand_cores([])["systeme"] == 0)

# ---------------------------------------------------------------------------
print()
print("Test 5: die Seite zeichnet - und die Filtertaste schaltet um")
# ---------------------------------------------------------------------------
fm = H.fm
WAHL = os.path.join(WURZEL, "core_wahl.json")
C.WAHL_DATEI = WAHL
with open(WAHL, "w") as fh:
    json.dump({}, fh)
# Die Seite liest die ECHTE Systemtabelle, nicht unsere vier - also
# wird hier auch die echte gezeichnet. Das ist Absicht: so laeuft sie
# beim Nutzer auch, und ein Fehler in einer Zeile faellt hier auf.
fm.CORES.WAHL_DATEI = WAHL


class Tasten(object):
    def __init__(self, folge):
        self.folge = list(folge)

    def read_action(self, timeout=None):
        return self.folge.pop(0) if self.folge else "back"


def seite(folge, b=1920, h=1080):
    H.SCREEN[:] = [b, h]
    f = H.make_frontend(page=0)
    f.inp = Tasten(folge)
    f.draw = lambda *a, **k: None
    f.cores_bildschirm()
    return f


FOLGE = ["down", "filter", "down", "filter", "down", "filter",
         "down", "right", "left", "back"]
for name, b, h in (("CRT 320x240", 320, 240), ("CRT 640x480", 640, 480),
                   ("HDMI 1920x1080", 1920, 1080),
                   ("hochkant 1080x1920", 1080, 1920)):
    try:
        seite(list(FOLGE), b, h)
        ok, fehler = True, ""
    except Exception as e:                               # noqa: BLE001
        ok, fehler = False, "%s: %s" % (type(e).__name__, e)
        traceback.print_exc(limit=4)
    check("%-20s zeichnet mit Filterwechsel" % name, ok, fehler)

# Und einmal durch ALLE drei Filter und wieder zurueck - der Index
# darf dabei nie aus der Liste laufen (die drei Listen sind
# verschieden lang).
try:
    seite(["filter"] * 7 + ["down"] * 5 + ["filter", "up", "back"])
    ok = True
    fehler = ""
except Exception as e:                                   # noqa: BLE001
    ok, fehler = False, "%s: %s" % (type(e).__name__, e)
    traceback.print_exc(limit=4)
check("sieben Filterwechsel laufen nicht aus der Liste", ok, fehler)

# ---------------------------------------------------------------------------
print()
print("Test 6: links/rechts ohne Auswahl aendert NICHTS")
# ---------------------------------------------------------------------------
# DER GEFAEHRLICHE FALL. Eine Zeile ohne zweite Fassung hat nichts zu
# blaettern. Wuerde links/rechts dort trotzdem "geaendert" setzen,
# landete beim Verlassen eine Datei auf der Karte, die der Nutzer nie
# gewollt hat - und zwar fuer den Core-Start.
check("der Zweig steigt bei weniger als zwei Fassungen aus",
      "len(fassungen) < 2" in _BS and "continue" in _BS,
      "sonst wuerde eine Zeile ohne Wahl trotzdem als Aenderung "
      "gespeichert")
check("und die Pfeile werden dort gar nicht erst gezeigt",
      "markiert and len(fassungen) > 1" in _BS,
      "ein '< >' an einer Zeile, die sich nicht aendern laesst, ist "
      "ein Versprechen, das die Taste nicht haelt")
check("eine Luecke heisst 'kein Core' und nicht 'automatisch'",
      "cores_kein_core" in _BS,
      "'automatisch' waere die Zusage, dass schon irgendetwas startet")
check("die RA-Fassungen werden EINMAL nachgesehen, nicht je Bild",
      _BS.index("_ra[") < _BS.index("while True:"),
      "jeder Aufruf ist ein Dateizugriff - siehe Abschnitt G im Bench")

# ---------------------------------------------------------------------------
print()
print("Test 7: jeder benutzte Text existiert in beiden Sprachen")
# ---------------------------------------------------------------------------
_benutzt = sorted(set(re.findall(r'(?<![A-Za-z0-9_])t\(\s*"([a-z0-9_]+)"',
                                 _BS)))
check("die Seite benutzt ueberhaupt Texte", len(_benutzt) >= 6,
      "%d: %r" % (len(_benutzt), _benutzt))
# Die drei Filternamen werden zusammengesetzt ("cores_filter_" + art).
# Das ist derselbe Fall wie in Build 309 - dort wurde er aufgeloest,
# hier bleibt er, weil die drei Namen aus EINER Tabelle kommen. Also
# prueft der Test sie ausdruecklich mit.
_benutzt = sorted(set(_benutzt) - {"cores_filter_"}
                  | {"cores_filter_alle", "cores_filter_waehlbar",
                     "cores_filter_ohne"})
_fehlt = [k for k in _benutzt if k not in TR.TRANSLATIONS]
check("alle Schluessel sind eingetragen", not _fehlt, "fehlt: %r" % (_fehlt,))
_halb = [k for k in _benutzt if k in TR.TRANSLATIONS
         and not (TR.TRANSLATIONS[k].get("de")
                  and TR.TRANSLATIONS[k].get("en"))]
check("und in de UND en vorhanden", not _halb, "halb: %r" % (_halb,))
for _spr in ("de", "en"):
    _txt = TR.TRANSLATIONS["cores_fuss"][_spr]
    check("cores_fuss/%s hat fuenf Platzhalter" % _spr,
          len(re.findall(r"%[sd]", _txt)) == 5, "%r" % (_txt,))
check("der Hinweis nennt die Filtertaste",
      all("ilter" in TR.TRANSLATIONS["cores_hinweis"][sp]
          for sp in ("de", "en")),
      "eine Taste, die niemand kennt, gibt es nicht")

RAC.RA_CORES_DIR_ABS = _ra_alt
C.BASE = _ALT
shutil.rmtree(WURZEL, ignore_errors=True)

print()
if fails:
    print("ROT: %d Pruefung(en) fehlgeschlagen:" % len(fails))
    for f in fails:
        print("   - %s" % f)
    sys.exit(1)
print("ALLES GRUEN")
