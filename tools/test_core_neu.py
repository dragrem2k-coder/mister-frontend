#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Was update_all geaendert hat (Build 250).

Seit Build 213 kann man update_all aus dem Menue starten. Danach stand
da nichts - das Skript schreibt Hunderte Zeilen auf die Konsole, und
wer nicht mitgelesen hat, weiss hinterher nicht, ob ueberhaupt etwas
passiert ist.

VERGLICHEN WIRD DIE KARTE MIT SICH SELBST, und das ist die
Entscheidung, um die es geht. Ein Leser fuer update_alls Protokoll
haengt am Format einer fremden Datei - dieselbe zweite Quelle der
Wahrheit, die fe/cores.py ausschliesst und die fe/mister_system.py
ausdruecklich ablehnt. Hier wird stattdessen vor dem Start
aufgeschrieben, welche .rbf-Dateien in den Core-Ordnern liegen, und
danach nachgesehen.

WORAN ES SCHEITERN KANN

  1. Der erste Lauf meldet jeden einzelnen Core als "neu". "Noch nie
     nachgesehen" ist etwas anderes als "damals lag dort nichts" -
     genau dieser Unterschied steckt in stand_lesen(), das (None,
     None) liefert und nicht (None, []).
  2. Die Praefix-Falle: "SNES" und "SNES_Tracker" sind zwei
     verschiedene Cores. fe/cores.py hat sie schon einmal abgefangen.
  3. Derselbe Dateiname in zwei Ordnern gilt als dieselbe Datei - ein
     verschobener Core saehe dann wie "weg und neu" aus.
  4. Der Stand wird NACH dem Lauf aufgeschrieben. Dann ist es zu spaet:
     es gibt nichts mehr, womit man vergleichen koennte.
  5. "Weg" wird nicht gemeldet. update_all raeumt alte Cores weg
     ("Removing /media/fat/_Console/SNES_20260603.rbf" - so stand es im
     Log des Nutzers, dutzendfach), und ein verschwundener Core ist
     genau das, was man wissen will, wenn ein Spiel nicht mehr startet.
  6. Eine kaputte Datei nimmt den Menueaufbau mit.

Ausfuehren:
    python3 tools/test_core_neu.py
"""
import io
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H                                        # noqa: E402

import fe.corestand as CSTAND                               # noqa: E402
import fe.cores as CORES                                    # noqa: E402
import fe.translations as TR                                # noqa: E402

fm = H.fm
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_QF = io.open(os.path.join(_REPO, "frontend", "frontend.py"),
              encoding="utf-8").read()
fails = []
_TMP = tempfile.mkdtemp(prefix="coreneu_")


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


def _karte(dateien, name="karte"):
    """Eine Karte mit Core-Ordnern anlegen. dateien ist eine Liste
    "_Console/SNES_20260603.rbf"."""
    wurzel = os.path.join(_TMP, name)
    for o in CORES.CORE_ORDNER:
        os.makedirs(os.path.join(wurzel, o), exist_ok=True)
    for d in dateien:
        p = os.path.join(wurzel, d)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        io.open(p, "w").write("x")
    return wurzel


# ---------------------------------------------------------------------------
print("Test 1: Kopf und Fassung aus dem Dateinamen")
# ---------------------------------------------------------------------------
for _name, _erw in (("SNES_20260603.rbf", ("SNES", "20260603")),
                    ("SNES.rbf", ("SNES", "")),
                    ("MegaCD_20251231.rbf", ("MegaCD", "20251231")),
                    ("NES_20260101_beta.rbf", ("NES", "20260101_beta")),
                    ("", ("", ""))):
    check("%-24r -> %r" % (_name, _erw),
          CSTAND.kopf_und_fassung(_name) == _erw,
          str(CSTAND.kopf_und_fassung(_name)))
# DIE PRAEFIX-FALLE, die fe/cores.py schon einmal erwischt hat.
check("SNES_Tracker.rbf ist NICHT SNES",
      CSTAND.kopf_und_fassung("SNES_Tracker.rbf") == ("SNES_Tracker", ""),
      str(CSTAND.kopf_und_fassung("SNES_Tracker.rbf")))
check("und SNES_Tracker_20260603.rbf auch nicht",
      CSTAND.kopf_und_fassung("SNES_Tracker_20260603.rbf")
      == ("SNES_Tracker", "20260603"),
      "nach dem Unterstrich muss eine ZIFFER kommen")

# ---------------------------------------------------------------------------
print()
print("Test 2: der erste Lauf meldet nichts")
# ---------------------------------------------------------------------------
# "Noch nie nachgesehen" ist etwas anderes als "damals lag dort
# nichts". Wer das verwechselt, meldet beim ersten Mal mehrere Hundert
# Cores als neu.
_w = _karte(["_Console/SNES_20260603.rbf", "_Console/NES_20260101.rbf"],
            "erst")
_sp = os.path.join(_TMP, "stand1.json")
_bp = os.path.join(_TMP, "bericht1.json")
_ber = CSTAND.nachsehen(_w, _sp, _bp)
check("der Bericht ist leer", CSTAND.leer(_ber), str(_ber))
check("aber der Stand ist jetzt da", os.path.exists(_sp))
_zeit, _liste = CSTAND.stand_lesen(_sp)
check("und enthaelt beide Cores", len(_liste or ()) == 2, str(_liste))
check("mit Ordner davor",
      all("/" in x for x in (_liste or ())), str(_liste))
check("es wurde kein Bericht geschrieben", not os.path.exists(_bp),
      "beim ersten Mal gibt es nichts zu berichten")
check("stand_lesen() unterscheidet 'nie' von 'leer'",
      CSTAND.stand_lesen(os.path.join(_TMP, "gibtsnicht"))
      == (None, None))
check("und vergleich(None, ...) meldet nichts",
      CSTAND.leer(CSTAND.vergleich(None, ["_Console/X_1.rbf"])))

# ---------------------------------------------------------------------------
print()
print("Test 3: neu, aktualisiert, weg")
# ---------------------------------------------------------------------------
_vorher = ["_Console/SNES_20260603.rbf", "_Console/NES_20260101.rbf",
           "_Console/MegaCD_20250101.rbf", "_Arcade/Pacman.rbf"]
_jetzt = ["_Console/SNES_20260915.rbf",       # aktualisiert
          "_Console/NES_20260101.rbf",        # unveraendert
          "_Console/N64_20260901.rbf",        # neu
          "_Arcade/Pacman.rbf"]               # unveraendert
# MegaCD fehlt jetzt -> weg
_v = CSTAND.vergleich(_vorher, _jetzt)
check("N64 ist neu", _v["neu"] == ["_Console/N64"], str(_v["neu"]))
check("MegaCD ist weg", _v["weg"] == ["_Console/MegaCD"], str(_v["weg"]))
check("SNES ist aktualisiert",
      [x[0] for x in _v["aktualisiert"]] == ["_Console/SNES"],
      str(_v["aktualisiert"]))
check("mit alter und neuer Fassung",
      _v["aktualisiert"]
      and _v["aktualisiert"][0][1] == "20260603"
      and _v["aktualisiert"][0][2] == "20260915",
      str(_v["aktualisiert"][:1]))
# AUF DEN GENAUEN NAMEN GEPRUEFT, nicht auf "enthaelt". Der erste
# Entwurf fragte 'if "NES" in x' - und "_Console/SNES" enthaelt "NES".
# Der Test wurde dadurch rot, obwohl der Vergleich stimmte: eine
# Teilstring-Pruefung auf Core-Namen ist dieselbe Praefix-Falle, die
# fe/cores.py im Programm schon abgefangen hat.
_unberuehrt = ("_Console/NES", "_Arcade/Pacman")
check("NES und Pacman stehen nirgends",
      not [x for x in _v["neu"] + _v["weg"] if x in _unberuehrt]
      and not [x for x in _v["aktualisiert"] if x[0] in _unberuehrt],
      "unveraendert heisst: kein Posten")
check("und die Zahl stimmt", CSTAND.anzahl(_v) == 3,
      "%d" % CSTAND.anzahl(_v))

# DERSELBE NAME IN ZWEI ORDNERN ist nicht dieselbe Datei.
# MIT ECHTEM DATUM, vierstellig: "Doppelt_1" waere nach den Regeln von
# kopf_und_fassung() gar kein Datum, und der Kopf hiesse "Doppelt_1".
# Genau richtig so - aber dann prueft dieser Fall nicht, was er soll.
_v2 = CSTAND.vergleich(["_Console/Doppelt_20260101.rbf"],
                       ["_Arcade/Doppelt_20260101.rbf"])
check("ein verschobener Core ist weg UND neu",
      _v2["neu"] == ["_Arcade/Doppelt"]
      and _v2["weg"] == ["_Console/Doppelt"],
      "%s / %s" % (_v2["neu"], _v2["weg"]))

# Ein Core ohne Datum im Namen: nur da oder nicht da.
_v3 = CSTAND.vergleich(["_Console/Ohne.rbf"], ["_Console/Ohne.rbf"])
check("ohne Datum gibt es kein 'aktualisiert'",
      CSTAND.leer(_v3), str(_v3))

# ---------------------------------------------------------------------------
print()
print("Test 4: der ganze Weg - vor und nach dem Lauf")
# ---------------------------------------------------------------------------
_sp = os.path.join(_TMP, "stand2.json")
_bp = os.path.join(_TMP, "bericht2.json")
_w1 = _karte(_vorher, "vor")
CSTAND.stand_schreiben(CSTAND.cores_jetzt(_w1), _sp)
_w2 = _karte(_jetzt, "nach")
_ber = CSTAND.nachsehen(_w2, _sp, _bp)
check("der Bericht ist nicht leer", not CSTAND.leer(_ber))
check("drei Posten", CSTAND.anzahl(_ber) == 3,
      "%d: %s" % (CSTAND.anzahl(_ber), _ber))
check("und er liegt auf der Karte", os.path.exists(_bp))
_gelesen = CSTAND.bericht_lesen(_bp)
check("gelesen kommt dasselbe wieder heraus",
      _gelesen and _gelesen["neu"] == _ber["neu"]
      and _gelesen["weg"] == _ber["weg"],
      str(_gelesen))
check("die Tripel sind nach dem Lesen wieder Tripel",
      _gelesen and _gelesen["aktualisiert"]
      and isinstance(_gelesen["aktualisiert"][0], tuple)
      and len(_gelesen["aktualisiert"][0]) == 3,
      "in JSON sind sie Listen - genau dieser Fehler steckt in "
      "gemerkte_laden() als Kommentar")
check("der Stand ist jetzt der neue",
      CSTAND.stand_lesen(_sp)[1] == CSTAND.cores_jetzt(_w2))
# Zweimal nachsehen ohne Aenderung meldet nichts mehr.
check("zweimal nachsehen meldet nichts mehr",
      CSTAND.leer(CSTAND.nachsehen(_w2, _sp,
                                   os.path.join(_TMP, "b3.json"))))

# ---------------------------------------------------------------------------
print()
print("Test 5: kaputte und fehlende Dateien")
# ---------------------------------------------------------------------------
for _inhalt, _was in (("", "leer"), ("{", "halb geschrieben"),
                      ("[1,2]", "falscher Typ"),
                      ('{"cores": "alles"}', "cores ist kein Array"),
                      ('{"zeit": "gestern"}', "ohne cores")):
    _p = os.path.join(_TMP, "kaputt.json")
    io.open(_p, "w", encoding="utf-8").write(_inhalt)
    try:
        _r = CSTAND.stand_lesen(_p)
        _ok, _f = (_r == (None, None)), ""
    except Exception as e:                               # noqa: BLE001
        _ok, _f = False, "%s: %s" % (type(e).__name__, e)
    check("Stand %-22s -> (None, None)" % _was, _ok, _f)
    try:
        _ok2, _f2 = (CSTAND.bericht_lesen(_p) is None), ""
    except Exception as e:                               # noqa: BLE001
        _ok2, _f2 = False, "%s: %s" % (type(e).__name__, e)
    check("Bericht %-20s -> None" % _was, _ok2, _f2)
check("eine Karte ohne Core-Ordner wirft nicht",
      CSTAND.cores_jetzt(os.path.join(_TMP, "gibtsnicht")) == [],
      "nicht jede Karte hat _Utility")
check("ein Bericht mit nur einer Gruppe ist nicht leer",
      not CSTAND.leer({"neu": ["_Console/X"], "aktualisiert": [],
                       "weg": []}))
check("und leer(None) ist wahr", CSTAND.leer(None))
check("anzahl(None) ist 0", CSTAND.anzahl(None) == 0)

# ---------------------------------------------------------------------------
print()
print("Test 6: angeschlossen - und zwar in der richtigen Reihenfolge")
# ---------------------------------------------------------------------------
_code = "\n".join(z for z in _QF.split("\n")
                  if not z.strip().startswith("#"))
_blk = _code.split('elif kind == "update_all":')[1].split("elif kind ==")[0]
_i_stand = _blk.find("CSTAND.stand_schreiben(")
_i_start = _blk.find("self.run_script(_ua)")
_i_nach = _blk.find("CSTAND.nachsehen(")
check("der Stand wird VOR dem Start geschrieben",
      0 < _i_stand < _i_start,
      "danach ist es zu spaet - dann liegt schon der neue Stand da")
check("und nachgesehen wird NACH dem Lauf",
      _i_start < _i_nach,
      "run_script() kehrt erst zurueck, wenn das Skript durch ist")
check("ein Fehler dabei nimmt update_all nicht mit",
      _blk.count("except Exception:") >= 2
      and "traceback.format_exc()" in _blk)
check("auch 'nichts geaendert' wird gesagt",
      "core_neu_nichts" in _blk,
      "sonst steht man vor dem alten Bild und weiss nicht, ob "
      "update_all gelaufen ist")
check("das Systemmenue wird aufgefrischt",
      "self._refresh_system_category()" in _blk,
      "sonst erscheint der neue Menuepunkt erst beim naechsten Start")

H.set_screen(1920, 1080)
fe = H.make_frontend(page=0)
check("core_neu_bildschirm() gibt es",
      hasattr(fe, "core_neu_bildschirm"))
check("und die Aktion wird behandelt",
      'elif kind == "core_neu":' in _QF)
check("mit Netz gegen einen Absturz darin",
      "core_neu_bildschirm CRASH" in _QF)
_scr = _code.split("def core_neu_bildschirm")[1].split("\n    def ")[0]
check("'weg' steht nicht am Ende",
      _scr.find('"weg"') < _scr.find('"aktualisiert"'),
      "ein verschwundener Core ist das, was man wissen will, wenn ein "
      "Spiel nicht mehr startet")
check("jede andere Taste geht zurueck",
      "else:\n                break" in _scr,
      "es gibt hier nichts einzustellen")

import fe.menu as MENU                                     # noqa: E402
_alt_ber = CSTAND.BERICHT_DATEI
try:
    # Ohne Bericht KEIN Menuepunkt - ein Punkt, der "nichts da" sagt,
    # ist einer zu viel.
    CSTAND.BERICHT_DATEI = os.path.join(_TMP, "gibtsnicht.json")
    _sys = MENU.system_items(False, "lokal", "")
    _alle = []
    _rest = [_sys]
    while _rest:
        _n = _rest.pop()
        if not isinstance(_n, dict):
            continue
        _alle.extend(_n.get("items") or ())
        _rest.extend((_n.get("folders") or {}).values())
    check("ohne Bericht steht der Punkt nicht im Menue",
          not [e for e in _alle if len(e) > 1 and e[1] == "core_neu"],
          "%d Eintraege durchsucht" % len(_alle))
    # Mit Bericht schon.
    CSTAND.BERICHT_DATEI = os.path.join(_TMP, "menue.json")
    CSTAND.bericht_schreiben({"neu": ["_Console/N64"], "aktualisiert": [],
                              "weg": []})
    _sys = MENU.system_items(False, "lokal", "")
    _alle = []
    _rest = [_sys]
    while _rest:
        _n = _rest.pop()
        if not isinstance(_n, dict):
            continue
        _alle.extend(_n.get("items") or ())
        _rest.extend((_n.get("folders") or {}).values())
    _treffer = [e for e in _alle if len(e) > 1 and e[1] == "core_neu"]
    check("mit Bericht steht er drin", len(_treffer) == 1, str(_treffer))
    check("und nennt die Zahl",
          _treffer and "1" in _treffer[0][0], str(_treffer[:1]))
    # Eine kaputte Berichtsdatei darf das Menue nicht kosten.
    io.open(CSTAND.BERICHT_DATEI, "w", encoding="utf-8").write("{")
    try:
        MENU.system_items(False, "lokal", "")
        _ok = True
        _f = ""
    except Exception as e:                               # noqa: BLE001
        _ok, _f = False, "%s: %s" % (type(e).__name__, e)
    check("eine kaputte Berichtsdatei nimmt das Menue nicht mit", _ok, _f)
finally:
    CSTAND.BERICHT_DATEI = _alt_ber

for _schl in ("sys_core_neu", "core_neu_titel", "core_neu_gruppe_neu",
              "core_neu_gruppe_weg", "core_neu_gruppe_aktualisiert",
              "core_neu_von", "core_neu_hinweis", "core_neu_nichts"):
    _e = TR.TRANSLATIONS.get(_schl)
    check("%-30s zweisprachig" % _schl,
          bool(_e) and bool(_e.get("de")) and bool(_e.get("en")))

# ---------------------------------------------------------------------------
print()
print("Test 7: kein Protokoll von update_all wird gelesen")
# ---------------------------------------------------------------------------
# DAS IST DIE ENTSCHEIDUNG DIESES BUILDS, und sie gehoert festgehalten:
# fe/mister_system.py liest aus update_alls Spuren NUR den Zeitstempel
# (os.path.getmtime), nie den Inhalt. Wer das aendert, haengt uns an
# das Zeilenformat einer fremden Datei.
_cs = io.open(os.path.join(_REPO, "frontend", "fe", "corestand.py"),
              encoding="utf-8").read()
_cs_code = "\n".join(z for z in _cs.split("\n")
                     if not z.strip().startswith("#"))
# AUF DIE PFADE GEPRUEFT, nicht auf das Wort. Der erste Entwurf
# suchte "update_all" im Quelltext und wurde rot am eigenen Docstring,
# der erklaert, WARUM update_alls Protokoll nicht gelesen wird. Ein
# Test, der die Begruendung als Verstoss zaehlt, ist kein Test.
for _verboten in ("/media/fat/Scripts", "UPDATE_ALL_SPUREN", ".log",
                  "downloader"):
    check("corestand.py benutzt %-22s nicht" % _verboten,
          _verboten not in _cs_code,
          "verglichen wird die Karte mit sich selbst, nicht ein "
          "fremdes Protokoll gelesen")
check("gelesen werden nur .rbf-Dateinamen",
      '.rbf' in _cs_code and "os.listdir" in _cs_code)
_ms = io.open(os.path.join(_REPO, "frontend", "fe", "mister_system.py"),
              encoding="utf-8").read()
_ms_code = "\n".join(z for z in _ms.split("\n")
                     if not z.strip().startswith("#"))
check("mister_system.py liest weiterhin nur den Zeitstempel",
      "getmtime" in _ms_code
      and "UPDATE_ALL_SPUREN" in _ms_code
      and _ms_code.count("open(pfad") == 0,
      "der Inhalt des Protokolls bleibt unangetastet")

shutil.rmtree(_TMP, ignore_errors=True)
print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
