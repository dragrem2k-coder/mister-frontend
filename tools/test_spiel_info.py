#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Der Steckbrief eines Spiels (Build 311).

NUTZERWUNSCH vom 08.11., Prioritaet 4 seiner Liste - und sein
ausgewaehlter Entwurf 3 ("Hero") ist genau diese Seite:

    "Jedes Spiel sollte eine eigene Informationsseite bekommen: Cover,
     Spielbeschreibung und technische Daten, Erscheinungsjahr,
     Entwickler, Spielerzahl, Spielzeit und zuletzt gespielt,
     Anleitung."

JEDE EINZELNE ZUTAT WAR SCHON DA - das Cover liefert _ansicht_cover(),
die Daten get_meta() (Build 115/142), die Beschreibung docs_synopsis()
(Build 141), die Spielzeit load_playtime(), die Anleitung
_anleitung_zum_eintrag() (Build 263) und die startende Core-Fassung
aufloesen_spiel() (Build 310). Gefehlt hat NUR eine Seite, die sie
nebeneinander legt.

WAS DIESER TEST SICHERT:
  1. die Seite zeichnet auf Roehre, HDMI und hochkant ohne Fehler,
  2. auch dann, wenn es zu dem Spiel GAR NICHTS gibt - keine
     Metadaten, keine Beschreibung, keine Spielzeit,
  3. sie legt KEINE neue Quelle an: kein Netz, kein Schreiben,
  4. sie holt die Daten aus den vorhandenen Funktionen statt sie
     nachzubauen,
  5. der Menuepunkt steht ganz oben und nur bei Spielen,
  6. ein Ordner bekommt keine Infoseite,
  7. und jeder Text existiert in beiden Sprachen.

Ausfuehren:
    python3 tools/test_spiel_info.py
"""
import os
import re
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H          # noqa: E402

import fe.translations as TR  # noqa: E402
from _quelle import koerper, nur_code                     # noqa: E402

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_FP = os.path.join(_REPO, "frontend", "frontend.py")
_QF = open(_FP, encoding="utf-8", errors="replace").read()
_BS = nur_code(koerper(_QF, "spiel_info_bildschirm", "Frontend"))

fails = []


def check(name, ok, info=""):
    if ok:
        print("  OK   %s %s" % (name, info))
    else:
        print("  FEHL %s %s" % (name, info))
        fails.append(name)


print(__doc__.strip().split("\n")[0])
print()


class Tasten(object):
    """Eine Taste, und die Seite geht wieder zu."""

    def __init__(self, folge=("back",)):
        self.folge = list(folge)

    def read_action(self, timeout=None):
        return self.folge.pop(0) if self.folge else "back"


def seite(b=1920, h=1080, titles=None, page=1):
    H.SCREEN[:] = [b, h]
    f = H.make_frontend(page=page, titles=titles)
    f.inp = Tasten()
    f.draw = lambda *a, **k: None
    f.spiel_info_bildschirm()
    return f


# ---------------------------------------------------------------------------
print("Test 1: die Seite zeichnet - auf Roehre, HDMI und hochkant")
# ---------------------------------------------------------------------------
# DER EIGENTLICHE BEWEIS DIESES BUILDS. Eine Seite, die nur auf 1080p
# gerechnet wurde, faellt auf der Roehre ueber eine negative Breite -
# und zwar erst bei ihm. Dieselbe Bauart wie Test 10 in test_cores.py.
for name, b, h in (("CRT 320x240", 320, 240), ("CRT 640x480", 640, 480),
                   ("HDMI 1920x1080", 1920, 1080),
                   ("hochkant 1080x1920", 1080, 1920),
                   ("sehr schmal 256x224", 256, 224)):
    try:
        seite(b, h)
        ok, fehler = True, ""
    except Exception as e:                               # noqa: BLE001
        ok, fehler = False, "%s: %s" % (type(e).__name__, e)
        traceback.print_exc(limit=4)
    check("%-20s zeichnet ohne Fehler" % name, ok, fehler)

# ---------------------------------------------------------------------------
print()
print("Test 2: auch ein Spiel, zu dem es GAR NICHTS gibt")
# ---------------------------------------------------------------------------
# Der Normalfall auf einer frischen Karte: keine Metadaten, keine
# Beschreibung, nie gespielt, kein Cover. Die Seite darf dann nicht
# leer AUSSEHEN wollen und dabei umfallen - sie zeigt eben weniger.
try:
    seite(1920, 1080, titles=["Ein Spiel ohne alles"])
    ok, fehler = True, ""
except Exception as e:                                   # noqa: BLE001
    ok, fehler = False, "%s: %s" % (type(e).__name__, e)
    traceback.print_exc(limit=4)
check("ohne Metadaten, Cover und Spielzeit", ok, fehler)
try:
    seite(1920, 1080,
          titles=["Donkey Kong Country 2 - Diddy's Kong Quest "
                  "(Europe) (Rev 1) (Beta)"])
    ok2, fehler2 = True, ""
except Exception as e:                                   # noqa: BLE001
    ok2, fehler2 = False, "%s: %s" % (type(e).__name__, e)
check("und ein sehr langer Titel", ok2, fehler2)

# ---------------------------------------------------------------------------
print()
print("Test 3: ein Ordner bekommt keine Infoseite")
# ---------------------------------------------------------------------------
H.SCREEN[:] = [1920, 1080]
f = H.make_frontend(page=1)
_, node, _ = f.cats[0]
node["items"] = [("Hacks/", "folder", "Hacks")]
node.pop("_display_items_cache", None)
f.item_i = 0
f.inp = Tasten()
_meldungen = []
f.draw = lambda *a, **k: _meldungen.append(k.get("message"))
f.spiel_info_bildschirm()
check("es kommt eine Meldung statt einer leeren Seite",
      TR.t("info_kein_spiel") in _meldungen, "%r" % (_meldungen,))

# ---------------------------------------------------------------------------
print()
print("Test 4: keine neue Quelle - kein Netz, kein Schreiben")
# ---------------------------------------------------------------------------
# Eine Infoseite, die etwas nachlaedt, waere eine Seite, die beim
# Oeffnen haengt. Und eine, die schreibt, waere eine, die beim
# Ansehen etwas aendert. Beides verbietet dieser Test am Quelltext -
# dieselbe Bauart wie test_anleitung.py.
check("die Methode wurde gefunden", bool(_BS.strip()),
      "%d Zeichen" % len(_BS))
for _verboten in ("open(", "urllib", "requests", "socket", "os.remove",
                  "os.rename", "os.replace", "os.makedirs", "shutil.",
                  "fetch_", "subprocess"):
    check("kein %s" % _verboten, _verboten not in _BS,
          "eine Infoseite laedt nichts nach und aendert nichts")

# ---------------------------------------------------------------------------
print()
print("Test 5: die Daten kommen aus den vorhandenen Funktionen")
# ---------------------------------------------------------------------------
# Nichts davon wird nachgebaut - jede Zeile dieser Seite hat eine
# Quelle, die es laengst gibt.
for _quelle_name, _wofuer in (
        ("get_meta(", "Jahr, Genre, Entwickler, Spieler (Build 115/142)"),
        ("docs_synopsis(", "die Beschreibung (Build 141)"),
        ("load_playtime(", "Spielzeit und Starts"),
        ("_ansicht_cover(", "das Cover - samt der Regel fuer HD"),
        ("_anleitung_zum_eintrag(", "ob es eine Anleitung gibt (Build 263)"),
        ("aufloesen_spiel(", "welcher Core starten wuerde (Build 310)"),
        ("FILTER.entwickler_von(", "developer ODER manufacturer (Build 251)"),
        ("FILTER.genre_kurz(", "die grobe Gattung statt des Rohwerts"),
        ("_format_seconds_short(", "die Spielzeit lesbar")):
    check("%-26s -> %s" % (_quelle_name, _wofuer),
          _quelle_name in _BS)
check("und der Systemname kommt aus der Systemtabelle",
      "system_display_name(" in _BS)

# ---------------------------------------------------------------------------
print()
print("Test 6: der Menuepunkt steht ganz oben und nur bei Spielen")
# ---------------------------------------------------------------------------
_km = nur_code(koerper(_QF, "kontextmenue", "Frontend"))
check("das Kontextmenue kennt den Punkt", '"spiel_info"' in _km)
check("und zeigt ihn nur bei einem Spiel",
      'kind == "game"' in _km.split('"spiel_info"')[0].rsplit("\n", 3)[-3:][0]
      or 'kind == "game"' in "\n".join(
          _km.split('"spiel_info"')[0].split("\n")[-4:]),
      "sonst stuende er auch auf einem Ordner")
# GANZ OBEN heisst: vor der Anleitung und vor dem Favoriten.
_vor_info = _km.index('"spiel_info"')
for _spaeter in ('"anleitung"', '"favorite"', '"completed"',
                 '"verstecken"'):
    check("steht vor %s" % _spaeter,
          _spaeter in _km and _vor_info < _km.index(_spaeter),
          "der Steckbrief ist das, was man zu einem Spiel zuerst "
          "wissen will")
check("der Zweig behandelt die Wahl",
      'gewaehlt == "spiel_info"' in _QF
      and "spiel_info_bildschirm CRASH" in _QF,
      "eine Seite darf das Frontend nicht mitnehmen")

# ---------------------------------------------------------------------------
print()
print("Test 7: jeder benutzte Text existiert in beiden Sprachen")
# ---------------------------------------------------------------------------
# DIE VORSCHAU IM MUSTER IST NICHT SCHMUCK. Die erste Fassung suchte
# nach 't("..."' - und fand damit auch jedes meta.get("genre"),
# zeit.get("seconds") und get("launches"), weil "get(" auf "t(" endet.
# Der Test verlangte danach Uebersetzungen fuer "genre" und "seconds"
# und war rot, obwohl nichts fehlte. Ein Muster ohne Wortgrenze prueft
# etwas anderes, als es zu pruefen vorgibt.
_benutzt = sorted(set(re.findall(r'(?<![A-Za-z0-9_])t\(\s*"([a-z0-9_]+)"', _BS))
                  | {"ctx_spiel_info"})
check("die Seite benutzt ueberhaupt Texte", len(_benutzt) >= 10,
      "%d: %r" % (len(_benutzt), _benutzt))
_fehlt = [k for k in _benutzt if k not in TR.TRANSLATIONS]
check("alle Schluessel sind eingetragen", not _fehlt, "fehlt: %r" % (_fehlt,))
_halb = [k for k in _benutzt if k in TR.TRANSLATIONS
         and not (TR.TRANSLATIONS[k].get("de")
                  and TR.TRANSLATIONS[k].get("en"))]
check("und in de UND en vorhanden", not _halb, "halb: %r" % (_halb,))
# Genau ein Platzhalter dort, wo einer eingesetzt wird - und KEINER
# bei den Beschriftungen. Ein uebriges %s waere auf dem Fernseher ein
# Absturz mitten im Zeichnen.
for _k in ("info_spieler_kurz",):
    for _spr in ("de", "en"):
        check("%s/%s hat genau einen Platzhalter" % (_k, _spr),
              len(re.findall(r"%[sd]", TR.TRANSLATIONS[_k][_spr])) == 1)
_mit_platzhalter = [k for k in _benutzt
                    if k != "info_spieler_kurz"
                    and any(re.search(r"%[sd]", TR.TRANSLATIONS[k][sp] or "")
                            for sp in ("de", "en"))]
check("und sonst keiner einen", not _mit_platzhalter,
      "%r" % (_mit_platzhalter,))

# ---------------------------------------------------------------------------
print()
if fails:
    print("ROT: %d Pruefung(en) fehlgeschlagen:" % len(fails))
    for f in fails:
        print("   - %s" % f)
    sys.exit(1)
print("ALLES GRUEN")
