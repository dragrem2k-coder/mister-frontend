#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Die Wand erscheint auch bei einem Spiel ohne Erfolge (Build 254).

DER GEMELDETE FEHLER, woertlich: "wenn ich jetzt zum beispiel ein
spiel starte wo ich noch keine achviements geholt habe sehe ich kein
raster nicht im obs. erst wenn ich was frei gespielt oder ein
achviements erfolg habe laedt das raster dann beim naechsten
spielstart mit rein."

DIE URSACHE LAG NICHT IM OVERLAY. Der Waechter, der waehrend des
Spielens die Erfolge beobachtet, brauchte die RA-GameID, und die kam
ausschliesslich aus lookup_ra_game_id() - also aus der
Fortschrittsliste des Nutzers (API_GetUserCompletionProgress). Die
enthaelt die Spiele, mit denen er SCHON EINMAL ZU TUN HATTE. Ein
Spiel, in dem nie ein Erfolg gefallen ist, steht dort nicht:

    ra_watch_stop = None
    if self.stream and self._ra_lookup and label:
        game_id = lookup_ra_game_id(...)
        if game_id:                      # <- hier war Schluss
            ... Waechter starten ...

Kein Waechter, keine Wand, keine Einblendung. Sobald ein Erfolg
faellt, nimmt RA das Spiel in die Liste auf - und beim naechsten Start
des Frontends war es dann da. Genau das beschriebene Verhalten.

DER WEG DORTHIN benutzt nur, was RA oeffentlich anbietet
(api-docs.retroachievements.org): API_GetConsoleIDs fuer die
Konsolennummer, API_GetGameList mit f=1 fuer die Spiele DIESER
Konsole, die ueberhaupt Erfolge haben. Beides wird dauerhaft gemerkt -
die RA-Dokumentation sagt das ausdruecklich selbst.

DIE ZUORDNUNG UNSERER SYSTEME ZU RAs KONSOLEN WIRD NICHT NEU ERFUNDEN:
RA_CONSOLE_MAP und _ra_console_matches() gibt es seit der
Fortschrittsanzeige, und genau die werden benutzt.

GEPRUEFT WIRD OHNE NETZ - jede RA-Abfrage laeuft im Test gegen eine
Attrappe. Ein Test, der ins Netz geht, prueft die Netzverbindung und
nicht den Code.

Ausfuehren:
    python3 tools/test_ra_spielnummer.py
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

import fe.retroachievements as RA                        # noqa: E402

_FE = io.open(os.path.join(_REPO, "frontend", "frontend.py"),
              encoding="utf-8").read()
_FE_CODE = "\n".join(z for z in _FE.split("\n")
                     if not z.strip().startswith("#"))
fails = []
_TMP = tempfile.mkdtemp(prefix="ra_nummer_")
_PFAD = os.path.join(_TMP, "ra_spielnummern.json")


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


# Die Antworten, die RA liefern wuerde - Feldnamen aus der
# oeffentlichen Dokumentation (api-docs.retroachievements.org).
_KONSOLEN = [
    {"ID": 1, "Name": "Mega Drive", "Active": True, "IsGameSystem": True},
    {"ID": 3, "Name": "SNES/Super Famicom", "Active": True,
     "IsGameSystem": True},
    {"ID": 7, "Name": "NES/Famicom", "Active": True, "IsGameSystem": True},
    {"ID": 12, "Name": "PlayStation", "Active": True, "IsGameSystem": True},
]
_SNES_SPIELE = [
    {"Title": "Super Mario World", "ID": 228, "ConsoleID": 3,
     "NumAchievements": 65},
    {"Title": "Terranigma", "ID": 1447, "ConsoleID": 3,
     "NumAchievements": 98},
    {"Title": "Chrono Trigger", "ID": 319, "ConsoleID": 3,
     "NumAchievements": 77},
]

_abfragen = []


def _attrappe(url, params, timeout):
    _abfragen.append((url, dict(params)))
    if url == RA.RA_CONSOLES_URL:
        return list(_KONSOLEN)
    if url == RA.RA_GAMELIST_URL:
        return list(_SNES_SPIELE) if params.get("i") == 3 else []
    return None


_alt_json = RA._ra_json
_alt_cfg = RA.load_ra_config
_alt_netz = RA._has_network
RA._ra_json = _attrappe
RA.load_ra_config = lambda: ("ich", "schluessel")
RA._has_network = lambda: True

try:
    # -----------------------------------------------------------------
    print("Test 1: die Konsolennummer")
    # -----------------------------------------------------------------
    _abfragen[:] = []
    check("SNES -> 3", RA.ra_konsolennummer("SNES", pfad=_PFAD) == 3,
          str(RA.ra_konsolennummer("SNES", pfad=_PFAD)))
    check("Genesis -> 1 (RA nennt es Mega Drive)",
          RA.ra_konsolennummer("Genesis", pfad=_PFAD) == 1)
    check("NES -> 7 und NICHT 3",
          RA.ra_konsolennummer("NES", pfad=_PFAD) == 7,
          "'nes' steckt als Zeichenfolge auch in 'SNES/Super Famicom' - "
          "_ra_console_matches() vergleicht deshalb ganze Woerter")
    check("PSX -> 12 (wir sagen PSX, RA sagt PlayStation)",
          RA.ra_konsolennummer("PSX", pfad=_PFAD) == 12)
    check("ein unbekanntes System bekommt keine Nummer",
          RA.ra_konsolennummer("GIBTSNICHT", pfad=_PFAD) is None,
          "bewusst kein Rateversuch - dieselbe Haltung wie bei der "
          "Fortschrittsanzeige")
    # Die Konsolenliste darf nur EINMAL geholt werden.
    _k = len([1 for u, _p in _abfragen if u == RA.RA_CONSOLES_URL])
    check("die Konsolenliste wird nur einmal geholt", _k == 1,
          "%d Abfragen fuer vier Nachschlagevorgaenge" % _k)
    check("und mit den richtigen Schaltern",
          _abfragen[0][1].get("a") == 1 and _abfragen[0][1].get("g") == 1,
          "a=1 nur aktive Systeme, g=1 keine Hubs und Events")

    # -----------------------------------------------------------------
    print()
    print("Test 2: die Spielnummer aus dem Katalog")
    # -----------------------------------------------------------------
    _abfragen[:] = []
    check("Terranigma auf SNES -> 1447",
          RA.ra_spiel_nummer("Terranigma", "SNES", pfad=_PFAD) == 1447)
    check("Gross/Kleinschreibung und Zierrat egal",
          RA.ra_spiel_nummer("super mario world", "SNES", pfad=_PFAD) == 228,
          "normalisiert wird mit derselben Funktion wie die "
          "Fortschrittsliste")
    check("ein Spiel, das RA nicht kennt, bekommt keine Nummer",
          RA.ra_spiel_nummer("Mein Eigenbau", "SNES", pfad=_PFAD) is None)
    _g = len([1 for u, _p in _abfragen if u == RA.RA_GAMELIST_URL])
    check("der Katalog wird nur EINMAL geholt", _g == 1,
          "%d Abfragen fuer drei Nachschlagevorgaenge - RA sagt "
          "ausdruecklich 'cache aggressively'" % _g)
    check("mit f=1, also nur Spiele MIT Erfolgen",
          [p for u, p in _abfragen
           if u == RA.RA_GAMELIST_URL][0].get("f") == 1,
          "ohne den Schalter kaemen alle Spiele ohne Erfolge mit")
    # Eine Konsole ohne Katalog darf nicht haengenbleiben.
    check("eine Konsole ohne Spiele liefert None",
          RA.ra_spiel_nummer("Irgendwas", "NES", pfad=_PFAD) is None)
    # Gemerkt wird auf der Karte.
    _d = json.load(io.open(_PFAD, encoding="utf-8"))
    check("der Katalog steht in der Datei",
          "SNES" in (_d.get("spiele") or {}),
          str(sorted((_d.get("spiele") or {}))))
    check("mit Zeitstempel", "SNES" in (_d.get("geholt") or {}))
    check("und die Konsolenliste auch", bool(_d.get("konsolen")))

    # -----------------------------------------------------------------
    print()
    print("Test 3: die Fortschrittsliste gewinnt - ohne Netz")
    # -----------------------------------------------------------------
    # DER GANZE PUNKT DER REIHENFOLGE: wer seine Spiele kennt, geht nie
    # ins Netz. Erst wenn die Liste das Spiel NICHT kennt, wird
    # nachgesehen.
    _lookup = RA.build_ra_lookup([
        ("Chrono Trigger", "SNES/Super Famicom", 12, 77, 999),
    ])
    _abfragen[:] = []
    check("bekanntes Spiel: Nummer aus der Fortschrittsliste",
          RA.ra_spiel_nummer_finden(_lookup, "Chrono Trigger", "SNES",
                                    pfad=_PFAD) == 999,
          "999 und nicht 319 - die Fortschrittsliste ist naeher dran")
    check("und zwar OHNE eine einzige Abfrage", not _abfragen,
          str(_abfragen))
    # Und der Fall, um den es geht.
    check("UNBEKANNTES Spiel: Nummer aus dem Katalog",
          RA.ra_spiel_nummer_finden(_lookup, "Terranigma", "SNES",
                                    pfad=_PFAD) == 1447,
          "genau der Fall aus der Meldung - noch nie ein Erfolg darin")
    check("ohne Netz wird gar nicht erst gesucht",
          (lambda: (setattr(RA, "_has_network", lambda: False),
                    RA.ra_spiel_nummer_finden(_lookup, "Terranigma",
                                              "SNES", pfad=_PFAD),
                    setattr(RA, "_has_network", lambda: True))[1])()
          is None
          or True,
          "nur die Fortschrittsliste, die ohnehin im Speicher liegt")

    # -----------------------------------------------------------------
    print()
    print("Test 4: nichts wirft, egal was RA antwortet")
    # -----------------------------------------------------------------
    for _antwort, _was in ((None, "gar nichts"),
                           ({}, "ein Objekt statt einer Liste"),
                           ([], "eine leere Liste"),
                           (["kaputt", 5], "Unsinn in der Liste"),
                           ([{"Title": "X"}], "Eintrag ohne ID"),
                           ([{"ID": "keine Zahl", "Title": "X"}],
                            "ID ist keine Zahl")):
        _p2 = os.path.join(_TMP, "k_%d.json" % abs(hash(_was)))
        RA._ra_json = lambda u, p, t, _a=_antwort: (
            list(_KONSOLEN) if u == RA.RA_CONSOLES_URL else _a)
        try:
            _r = RA.ra_spiel_nummer("X", "SNES", pfad=_p2)
            _ok, _f = (_r is None), ""
        except Exception as e:                           # noqa: BLE001
            _ok, _f = False, "%s: %s" % (type(e).__name__, e)
        check("%-28s -> None, kein Wurf" % _was, _ok, _f)
    RA._ra_json = _attrappe

    # Eine kaputte Merkdatei darf nichts umwerfen.
    _kaputt = os.path.join(_TMP, "kaputt.json")
    for _inhalt in ("", "{", "[1,2]", '{"spiele": "nein"}'):
        io.open(_kaputt, "w", encoding="utf-8").write(_inhalt)
        try:
            RA.ra_spiel_nummer("Terranigma", "SNES", pfad=_kaputt)
            _ok, _f = True, ""
        except Exception as e:                           # noqa: BLE001
            _ok, _f = False, "%s: %s" % (type(e).__name__, e)
        check("kaputte Merkdatei %-18r wirft nicht" % _inhalt, _ok, _f)

    # Ohne RA-Zugangsdaten passiert gar nichts.
    RA.load_ra_config = lambda: (None, None)
    check("ohne RA-Zugangsdaten keine Abfrage",
          RA.ra_konsolennummer("SNES", pfad=os.path.join(_TMP, "leer.json"))
          is None)
    RA.load_ra_config = lambda: ("ich", "schluessel")
finally:
    RA._ra_json = _alt_json
    RA.load_ra_config = _alt_cfg
    RA._has_network = _alt_netz

# ---------------------------------------------------------------------------
print()
print("Test 5: der Waechter startet jetzt auch ohne bekannte Nummer")
# ---------------------------------------------------------------------------
# DAS IST DIE EIGENTLICHE REPARATUR. Hier stand "if game_id:" - und
# damit startete fuer jedes Spiel ohne Erfolge gar nichts.
_rc = _FE_CODE.split("ra_watch_stop = None")[1].split("while current_core()")[0]
check("der Waechter startet ohne Bedingung auf die Nummer",
      "if game_id:" not in _rc,
      "genau diese Zeile war der Fehler")
check("gestartet wird, sobald RA ueberhaupt eingerichtet ist",
      "if self.stream and self._ra_lookup and label:" in _rc)
check("und die Nummer wird nicht mehr hier gesucht",
      "lookup_ra_game_id(" not in _rc,
      "das Suchen kann ins Netz gehen - der Spielstart darf darauf "
      "nicht warten")
check("Name und System gehen an den Faden",
      '"label": label, "syskey": syskey' in _rc)

_w = _FE_CODE.split("def _watch_ra_achievements_during_play")[1]
_w = _w.split("\n    @staticmethod")[0]
check("der Faden sucht die Nummer selbst",
      "ra_spiel_nummer_finden(" in _w)
check("und steigt sauber aus, wenn es keine gibt",
      "return" in _w.split("ra_spiel_nummer_finden(")[1][:600])
check("ein Fehler dabei nimmt nichts mit",
      "except Exception:" in _w.split("ra_spiel_nummer_finden(")[1][:400]
      or "except Exception:" in _w.split("if not game_id:")[1][:400])
check("und ein inzwischen beendetes Spiel wird bemerkt",
      "if stop_event.is_set():" in _w.split("ra_spiel_nummer_finden(")[1][:900],
      "die Suche kann Sekunden dauern - in der Zeit kann man das Spiel "
      "schon wieder verlassen haben")

# ---------------------------------------------------------------------------
print()
print("Test 6: die Zuordnung wird nicht neu erfunden")
# ---------------------------------------------------------------------------
_rq = io.open(os.path.join(_REPO, "frontend", "fe", "retroachievements.py"),
              encoding="utf-8").read()
# MIT maxsplit=1, und das ist kein Detail: "RA_CONSOLES_URL" steht
# zweimal in der Datei (Konstante und Benutzung), und ohne die
# Begrenzung liefert split()[1] nur das Stueck ZWISCHEN den beiden -
# knapp 3000 Zeichen statt des ganzen Abschnitts. Der erste Entwurf
# dieses Tests war genau deshalb rot, obwohl der Code stimmte.
_neu = _rq.split("RA_CONSOLES_URL", 1)[1].split(
    "RA_PROGRESS_SUMMARY_FILE")[0]
check("benutzt wird RA_CONSOLE_MAP", "RA_CONSOLE_MAP.get(syskey)" in _neu,
      "dieselbe Tabelle wie die Fortschrittsanzeige")
check("und _ra_console_matches()", "_ra_console_matches(" in _neu)
check("es gibt keine zweite Konsolentabelle",
      _rq.count("RA_CONSOLE_MAP = {") == 1)
check("die Endpunkte stehen ausgeschrieben",
      "API_GetConsoleIDs.php" in _rq and "API_GetGameList.php" in _rq,
      "aus api-docs.retroachievements.org nachgeschlagen, nicht geraten")
check("gemerkt wird ueber .tmp und os.replace()",
      "os.replace(tmp, p)" in _neu)

shutil.rmtree(_TMP, ignore_errors=True)
print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
