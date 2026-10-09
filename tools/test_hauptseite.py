#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Die Hauptseite selbst bestimmen (Build 250).

Reihenfolge und Sichtbarkeit der Kategorien - Idee aus dem Vergleich
mit Degauss, das eine einrichtbare Startseite hat. Bei uns stand die
Reihenfolge an zehn verteilten insert()/append()-Stellen fest, und
ausblenden ging gar nicht.

WORAN DIESE AENDERUNG SCHEITERN KANN, und genau danach ist dieser Test
gebaut:

  1. "System" wird ausgeblendet oder vorgezogen. Dann sitzt man ohne
     Einstellungen da, und ohne Bildschirmtastatur kommt man an die
     Datei nicht heran. Muss auch bei einer VON HAND verstellten Datei
     unmoeglich sein.
  2. Der Schluessel haengt am Anzeigenamen. Die besonderen Kategorien
     sind uebersetzt ("Favoriten"/"Favorites"), mehrere tragen einen
     Zaehler ("Sammlungen (37)") - dann ist die Einstellung nach einem
     Sprachwechsel oder einem neuen Spiel weg.
  3. Ein gemerkter Filter und sein Quellsystem bekommen dasselbe
     Kuerzel. Ein Filter ueber SNES traegt syskey="SNES" (siehe
     _syskey_fuer_kat()) - wer den Filter ausblendet, verlore damit
     das System.
  4. Die Sync-Funktionen zerstoeren die Reihenfolge wieder.
     _sync_favorites_category() und _sync_recent_category() setzen
     Favoriten/Zuletzt/Weiterspielen mit einem harten insert(0, ...)
     zurueck an den Anfang - und zwar nach JEDEM Favoriten-Toggle und
     nach JEDEM Spiel.
  5. Eine kaputte Datei nimmt den Start mit.
  6. Eine neu hinzugekommene Kategorie ist unsichtbar, weil sie in der
     gespeicherten Reihenfolge nicht steht.

Ausfuehren:
    python3 tools/test_hauptseite.py
"""
import io
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H                                        # noqa: E402

import fe.hauptseite as HS                                  # noqa: E402
import fe.translations as TR                                # noqa: E402

fm = H.fm
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_QF = io.open(os.path.join(_REPO, "frontend", "frontend.py"),
              encoding="utf-8").read()
fails = []
_TMP = tempfile.mkdtemp(prefix="hauptseite_")


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


def _cats(*namen):
    """Kategorienliste wie build_categories() sie baut: Tupel aus
    (Anzeigename, Knoten, syskey)."""
    raus = []
    for n in namen:
        if isinstance(n, tuple):
            raus.append((n[0], {"folders": {}, "items": []}, n[1]))
        else:
            raus.append((n, {"folders": {}, "items": []}, None))
    return raus


def _namen(cats):
    return [c[0] for c in cats]


def _datei(aus=(), folge=()):
    p = os.path.join(_TMP, "hs_%d.json" % len(os.listdir(_TMP)))
    with io.open(p, "w", encoding="utf-8") as fh:
        json.dump({"aus": list(aus), "reihenfolge": list(folge)}, fh)
    return p


# ---------------------------------------------------------------------------
print("Test 1: das Kuerzel ist von Sprache und Zaehler unabhaengig")
# ---------------------------------------------------------------------------
# GENAU HIER LAG DIE GEFAHR. "Favoriten" und "Favorites" sind dieselbe
# Kategorie, und "Sammlungen (37)" ist dieselbe wie "Sammlungen (38)",
# sobald ein Spiel dazukommt.
_fav_de = TR.TRANSLATIONS["favorites_cat"]["de"]
_fav_en = TR.TRANSLATIONS["favorites_cat"]["en"]
check("die beiden Sprachen liefern dasselbe Kuerzel",
      HS.schluessel(_fav_de) == HS.schluessel(_fav_en) == "favorites_cat",
      "%r / %r" % (HS.schluessel(_fav_de), HS.schluessel(_fav_en)))
check("und der Zaehler aendert es nicht",
      HS.schluessel("%s (37)" % _fav_de)
      == HS.schluessel("%s (912)" % _fav_de) == "favorites_cat")
check("ein Systemname mit Klammer bleibt ganz",
      HS.ohne_zaehler("Game Boy (Color)") == "Game Boy (Color)",
      "nur ein ZAEHLER am Ende wird abgeschnitten, keine Klammer")
check("System bekommt sein eigenes Kuerzel",
      HS.schluessel("System") == HS.SYSTEM)
check("ein Spiele-System haengt am syskey",
      HS.schluessel("SNES", "SNES") == "sys:SNES")
check("ein Core-Ordner am Namen",
      HS.schluessel("Arcade") == "name:Arcade")

# ---------------------------------------------------------------------------
print()
print("Test 2: gemerkter Filter und Quellsystem sind NICHT dasselbe")
# ---------------------------------------------------------------------------
# Ein gemerkter Filter traegt den syskey seiner Quellkategorie. Ohne
# eine eigene Unterscheidung waeren "SNES" (System) und ein Filter
# namens "SNES / Platform" ueber SNES dasselbe Kuerzel.
_k_sys = HS.schluessel("SNES", "SNES", gemerkte=("SNES / Platform",))
_k_flt = HS.schluessel("SNES / Platform (12)", "SNES",
                       gemerkte=("SNES / Platform",))
check("das System behaelt sein Kuerzel", _k_sys == "sys:SNES", _k_sys)
check("der Filter bekommt ein eigenes",
      _k_flt == "filter:SNES / Platform", _k_flt)
check("und sie sind verschieden", _k_sys != _k_flt)
# Der boeseste Fall: der Filter heisst genau wie sein System.
_k_gleich = HS.schluessel("SNES (12)", "SNES", gemerkte=("SNES",))
check("auch wenn der Filter genau wie das System heisst",
      _k_gleich == "filter:SNES" and _k_gleich != "sys:SNES", _k_gleich)

# ---------------------------------------------------------------------------
print()
print("Test 3: 'System' bleibt - immer, und immer zuletzt")
# ---------------------------------------------------------------------------
_c = _cats("Weiterspielen", ("SNES", "SNES"), "Arcade", "System")
# Der Versuch, es auszublenden, muss ins Leere laufen.
_p = _datei(aus=[HS.SYSTEM, "name:Arcade"], folge=[])
_raus = HS.anwenden(_c, pfad=_p)
check("System steht noch drin", "System" in _namen(_raus),
      str(_namen(_raus)))
check("und Arcade ist weg (die Datei wirkt also)",
      "Arcade" not in _namen(_raus), str(_namen(_raus)))
check("System steht zuletzt", _namen(_raus)[-1] == "System",
      str(_namen(_raus)))
# Der Versuch, es vorzuziehen, ebenso.
_p = _datei(aus=[], folge=[HS.SYSTEM, "name:Arcade", "sys:SNES"])
_raus = HS.anwenden(_c, pfad=_p)
check("auch mit System an erster Stelle der Reihenfolge",
      _namen(_raus)[-1] == "System", str(_namen(_raus)))
check("und der Rest folgt trotzdem der Reihenfolge",
      _namen(_raus)[:3] == ["Arcade", "SNES", "Weiterspielen"],
      str(_namen(_raus)))
# Und laden() raeumt es schon auf dem Weg heraus.
_aus, _f = HS.laden(_datei(aus=[HS.SYSTEM], folge=[]))
check("laden() nimmt System aus der Ausblendliste",
      HS.SYSTEM not in _aus, str(sorted(_aus)))
check("und speichern() schreibt es nie hinein",
      HS.speichern({HS.SYSTEM, "name:X"}, [], os.path.join(_TMP, "w.json"))
      and HS.SYSTEM not in json.load(
          io.open(os.path.join(_TMP, "w.json"), encoding="utf-8"))["aus"])

# ---------------------------------------------------------------------------
print()
print("Test 4: eine neue Kategorie bleibt sichtbar")
# ---------------------------------------------------------------------------
# Wer ein System dazustellt, soll es sehen und nicht suchen muessen.
_c = _cats("Weiterspielen", ("SNES", "SNES"), ("N64", "N64"), "System")
_p = _datei(aus=[], folge=["sys:SNES", "continue_cat"])
_raus = HS.anwenden(_c, pfad=_p)
check("N64 steht nicht in der Reihenfolge und ist trotzdem da",
      "N64" in _namen(_raus), str(_namen(_raus)))
check("die bekannten stehen in der gespeicherten Reihenfolge",
      _namen(_raus)[:2] == ["SNES", "Weiterspielen"], str(_namen(_raus)))
check("und die unbekannte dahinter, vor System",
      _namen(_raus) == ["SNES", "Weiterspielen", "N64", "System"],
      str(_namen(_raus)))
# Mehrere Unbekannte behalten ihre Reihenfolge untereinander - dafuer
# ist die Sortierung stabil.
_c2 = _cats(("A", "A"), ("B", "B"), ("C", "C"), "System")
_raus2 = HS.anwenden(_c2, pfad=_datei(aus=[], folge=["sys:C"]))
check("mehrere Unbekannte behalten ihre Reihenfolge",
      _namen(_raus2) == ["C", "A", "B", "System"], str(_namen(_raus2)))

# ---------------------------------------------------------------------------
print()
print("Test 5: eine kaputte Datei aendert nichts")
# ---------------------------------------------------------------------------
_c = _cats("Weiterspielen", ("SNES", "SNES"), "System")
for _inhalt, _was in (("", "leer"), ("{", "halb geschrieben"),
                      ("[1,2,3]", "falscher Typ"),
                      ('{"aus": "alles"}', "aus ist kein Array"),
                      ('{"reihenfolge": {"a": 1}}', "Reihenfolge ist Dict")):
    _p = os.path.join(_TMP, "kaputt.json")
    io.open(_p, "w", encoding="utf-8").write(_inhalt)
    try:
        _r = HS.anwenden(_c, pfad=_p)
        _ok = (_namen(_r) == _namen(_c))
        _fehler = ""
    except Exception as e:                               # noqa: BLE001
        _ok, _fehler = False, "%s: %s" % (type(e).__name__, e)
    check("%-22s -> Vorgabe bleibt" % _was, _ok, _fehler)
check("eine fehlende Datei ebenso",
      _namen(HS.anwenden(_c, pfad=os.path.join(_TMP, "gibtsnicht")))
      == _namen(_c))

# ---------------------------------------------------------------------------
print()
print("Test 6: reihenfolge_aus() liefert, was man sieht")
# ---------------------------------------------------------------------------
_c = _cats("Weiterspielen", ("SNES", "SNES"), "Arcade", "System")
_f = HS.reihenfolge_aus(_c)
check("ohne System", HS.SYSTEM not in _f, str(_f))
check("in der sichtbaren Reihenfolge",
      _f == ["continue_cat", "sys:SNES", "name:Arcade"], str(_f))
check("und einmal gespeichert kommt dieselbe Liste wieder heraus",
      _namen(HS.anwenden(_c, pfad=_datei(aus=[], folge=_f)))
      == _namen(_c), "eine Runde durch Speichern aendert nichts")

# ---------------------------------------------------------------------------
print()
print("Test 7: die Sync-Funktionen zerstoeren die Reihenfolge nicht")
# ---------------------------------------------------------------------------
# DAS IST DER PUNKT, AN DEM DIESES FEATURE STILL KAPUTT GEHT.
# _sync_favorites_category() und _sync_recent_category() setzen
# Favoriten/Zuletzt/Weiterspielen mit einem harten insert(0 bzw. 1,
# ...) zurueck an den Anfang - ausdruecklich, um nicht alles neu bauen
# zu muessen. Ohne einen Aufruf von _hauptseite_anwenden() stuende die
# Einstellung weiter in der Datei und waere auf dem Schirm nach dem
# ersten Favoriten-Toggle verschwunden.
_code = "\n".join(z for z in _QF.split("\n")
                  if not z.strip().startswith("#"))
for _fn in ("_sync_favorites_category", "_sync_recent_category",
            "build_categories"):
    _blk = _code.split("def %s" % _fn)[1].split("\n    def ")[0]
    check("%s() ruft _hauptseite_anwenden()" % _fn,
          "self._hauptseite_anwenden()" in _blk,
          "sonst zerfaellt die Reihenfolge still")
# Und in den Sync-Funktionen VOR dem Wiederfinden von cat_i, sonst
# zeigt die Auswahl auf die alte Position.
for _fn in ("_sync_favorites_category", "_sync_recent_category"):
    _blk = _code.split("def %s" % _fn)[1].split("\n    def ")[0]
    check("%s(): erst sortieren, dann cat_i suchen" % _fn,
          0 < _blk.find("self._hauptseite_anwenden()")
          < _blk.find("if current_ref is not None:"))
# Die Methode faellt nicht aus, wenn die Einstellung kaputt ist.
_blk = _code.split("def _hauptseite_anwenden")[1].split("\n    def ")[0]
check("_hauptseite_anwenden() faengt alles ab",
      "except Exception:" in _blk and "LOG(" in _blk,
      "eine kaputte Einstellung darf das Hauptmenue nicht kosten")

# ---------------------------------------------------------------------------
print()
print("Test 8: am echten Frontend")
# ---------------------------------------------------------------------------
# DER PRUEFSTAND HAT NUR ZWEI KATEGORIEN (Zufalls-Zock und System) -
# damit kann man eine Reihenfolge nicht pruefen, und der erste Entwurf
# dieses Tests hat deshalb versucht, "System" auszublenden. Es werden
# also Kategorien dazugestellt, so wie build_categories() sie baut, und
# "System" bleibt dabei, wo es hingehoert: zuletzt.
H.set_screen(1920, 1080)
fe = H.make_frontend(page=0)
_echte = list(fe.cats)
_system = [c for c in _echte if c[0] == "System"]
_rest = [c for c in _echte if c[0] != "System"]
fe.cats = (_rest
           + _cats(("SNES", "SNES"), ("N64", "N64"), "Arcade",
                   TR.TRANSLATIONS["favorites_cat"]["de"])
           + _system)
_vorher = _namen(fe.cats)
check("es gibt genug Kategorien zum Sortieren", len(_vorher) >= 5,
      "%d: %s" % (len(_vorher), _vorher))
check("System steht zuletzt", _vorher[-1] == "System", str(_vorher[-3:]))

_alt_datei = HS.DATEI
try:
    HS.DATEI = os.path.join(_TMP, "echt.json")
    # Favoriten ausblenden, Arcade nach vorne.
    HS.speichern(["favorites_cat"], ["name:Arcade"])
    fe._hauptseite_anwenden()
    _nachher = _namen(fe.cats)
    check("die ausgeblendete Kategorie ist weg",
          TR.TRANSLATIONS["favorites_cat"]["de"] not in _nachher,
          str(_nachher))
    check("die vorgezogene steht vorne", _nachher[0] == "Arcade",
          str(_nachher[:3]))
    check("System steht weiterhin zuletzt", _nachher[-1] == "System",
          str(_nachher[-3:]))
    check("und es ist genau eine Kategorie weniger",
          len(_nachher) == len(_vorher) - 1,
          "%d gegen %d" % (len(_nachher), len(_vorher)))
    # Zweimal anwenden darf nichts weiter aendern.
    fe._hauptseite_anwenden()
    check("zweimal anwenden aendert nichts mehr",
          _namen(fe.cats) == _nachher)
    # UND DER FALL, DER DAS FEATURE STILL KAPUTT MACHT: nach einem
    # Favoriten-Toggle setzt _sync_favorites_category() Favoriten mit
    # insert(0 oder 1, ...) zurueck an den Anfang.
    fe._sync_favorites_category()
    _danach = _namen(fe.cats)
    check("nach _sync_favorites_category() steht Arcade noch vorne",
          _danach and _danach[0] == "Arcade", str(_danach[:3]))
    check("und Favoriten ist weiterhin ausgeblendet",
          TR.TRANSLATIONS["favorites_cat"]["de"] not in _danach,
          str(_danach))
    check("System steht auch danach zuletzt",
          _danach[-1] == "System", str(_danach[-3:]))
finally:
    HS.DATEI = _alt_datei
    fe.cats = _echte

# ---------------------------------------------------------------------------
print()
print("Test 9: der Bildschirm ist angeschlossen")
# ---------------------------------------------------------------------------
import fe.menu as MENU                                    # noqa: E402
check("hauptseite_bildschirm() gibt es",
      hasattr(fe, "hauptseite_bildschirm"))
_sys = MENU.system_items(False, "lokal", "")
_alle = []
_rest = [_sys]
while _rest:
    _n = _rest.pop()
    if not isinstance(_n, dict):
        continue
    for _e in (_n.get("items") or ()):
        _alle.append(_e)
    for _u in (_n.get("folders") or {}).values():
        _rest.append(_u)
check("der Menuepunkt steht im Systemmenue",
      any(len(e) > 1 and e[1] == "hauptseite" for e in _alle),
      "%d Eintraege durchsucht" % len(_alle))
check("und die Aktion wird behandelt",
      'elif kind == "hauptseite":' in _QF
      and "self.hauptseite_bildschirm()" in _QF)
check("mit Netz gegen einen Absturz darin",
      "hauptseite_bildschirm CRASH" in _QF,
      "ein Fehler im Editor darf nicht das Frontend mitnehmen")
_blk = _code.split("def hauptseite_bildschirm")[1].split("\n    def ")[0]
check("System steht nicht in der Liste des Editors",
      "if _k == HS.SYSTEM:" in _blk and "continue" in _blk)
check("ausgeblendete Kategorien stehen trotzdem darin",
      "for _k in sorted(aus):" in _blk,
      "sonst kann man sie nie wieder einschalten")
check("nach dem Speichern wird neu gebaut",
      "self.build_categories()" in _blk,
      "eine wieder eingeschaltete Kategorie muss erst entstehen - ihr "
      "Knoten wurde beim letzten Bau gar nicht erzeugt")
check("der Griff laeuft beim Verschieben nicht um",
      "if 0 <= _ziel < len(zeilen):" in _blk,
      "ein Eintrag, der oben hinaus und unten wieder hereinkommt, "
      "sieht nach einem Fehler aus")
for _schl in ("sys_hauptseite", "hauptseite_titel", "hauptseite_an",
              "hauptseite_aus", "hauptseite_anzahl",
              "hauptseite_hinweis", "hauptseite_hinweis_griff",
              "hauptseite_gespeichert", "hauptseite_leer"):
    _e = TR.TRANSLATIONS.get(_schl)
    check("%-26s zweisprachig" % _schl,
          bool(_e) and bool(_e.get("de")) and bool(_e.get("en")))

shutil.rmtree(_TMP, ignore_errors=True)
print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
