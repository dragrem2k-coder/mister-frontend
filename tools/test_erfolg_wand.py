#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Die Erfolgs-Wand im OBS-Overlay (Build 253).

Alle Erfolge des laufenden Spiels als Raster, freigeschaltete in Farbe,
die uebrigen ausgegraut - nach einem Screenshot des Nutzers, darueber
"74 / 98" und ein Fortschrittsbalken.

DIE DATEN WAREN SCHON DA. fetch_ra_game_achievements() liefert die
KOMPLETTE Liste des laufenden Spiels mit Badge-Name und
freigeschaltet-ja/nein; der Abruf laeuft ohnehin alle 25 Sekunden, denn
genau er erkennt die neuen Erfolge. Hinzu kommt also eine Weitergabe,
kein zweiter Netzzugriff.

GEPRUEFT WIRD GEGEN DEN ECHTEN SERVER, nicht nur am Text: der Test
startet einen StreamServer auf einem freien Port, haengt sich als
SSE-Klient daran und liest mit, was wirklich ueber die Leitung geht.
Eine Textsuche haette drei der Fehler unten nicht gefunden.

WORAN ES SCHEITERN KANN

  1. Die Liste geht bei JEDEM Abruf raus, auch unveraendert - alle 25
     Sekunden hundert Eintraege ueber die Leitung, fuer nichts.
  2. Ein Overlay, das sich MITTEN im Spiel neu verbindet (OBS-Szene
     gewechselt, Browserquelle neu geladen), bekommt eine leere Wand
     und muss bis zum naechsten Abruf warten.
  3. Nach der Rueckkehr ins Menue bleibt die Wand des letzten Spiels
     stehen - das sieht nach einem haengengebliebenen Bild aus.
  4. Beim allerersten Mal werden ~98 Icons gleichzeitig von
     RetroAchievements geholt und blockieren den Abruf-Faden, der die
     neuen Erfolge erkennt.
  5. Das Raster wird bei jedem Abruf neu gebaut - dann sieht man die
     frisch freigeschaltete Kachel NICHT aufblitzen, sondern nur ein
     fertiges neues Raster.
  6. Beim ersten Anzeigen blitzen alle 74 schon freigeschalteten
     Kacheln nacheinander auf.

Ausfuehren:
    python3 tools/test_erfolg_wand.py
"""
import io
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
sys.path.insert(0, os.path.join(_REPO, "frontend"))

from stream_server import StreamServer                   # noqa: E402

_OV = io.open(os.path.join(_REPO, "frontend", "stream_overlay.html"),
              encoding="utf-8").read()
_JS = _OV.split("<script>")[1].split("</script>")[0]
_CSS = _OV.split("<style>")[1].split("</style>")[0]
_AD = io.open(os.path.join(_REPO, "frontend", "stream_admin.html"),
              encoding="utf-8").read()
_FE = io.open(os.path.join(_REPO, "frontend", "frontend.py"),
              encoding="utf-8").read()
_FE_CODE = "\n".join(z for z in _FE.split("\n")
                     if not z.strip().startswith("#"))
fails = []
_TMP = tempfile.mkdtemp(prefix="erfolgwand_")


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


def _freier_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


# ---------------------------------------------------------------------------
print("Test 1: die Daten werden richtig geformt")
# ---------------------------------------------------------------------------
# _ra_wand_daten() ist bewusst eine eigene, statische Funktion - damit
# sie ohne Netz und ohne Overlay aufgerufen werden kann. Der Abruf-Faden
# daneben braucht beides.
import importlib.util                                      # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "_fe_wand", os.path.join(_REPO, "frontend", "frontend.py"))
# Das ganze Frontend zu importieren ist hier zu teuer und zu
# nebenwirkungsreich; die Funktion wird deshalb aus dem Quelltext
# herausgeschnitten und einzeln ausgefuehrt. Das ist haesslich, aber
# ehrlicher als die Logik im Test nachzubauen - dann prueft man die
# Kopie und nicht das Original.
_q = _FE.split("def _ra_wand_daten(achievements):")[1]
_q = _q.split("\n    def ")[0]
_src = "def _ra_wand_daten(achievements):" + _q
_ns = {}
exec(compile("\n".join(z[4:] if z.startswith("    ") else z
                       for z in _src.split("\n")),
             "<wand>", "exec"), _ns)
_wand = _ns["_ra_wand_daten"]

_liste = [
    ("Erster Schritt", "Besiege den ersten Gegner", 5, "11111", True,
     "2026-10-01", False),
    ("Tiefer hinab", "Erreiche Ebene 10", 10, "22222", False, None, False),
    ("Ohne Kratzer", "Volle Energie", 25, "33333", True, "2026-10-02", True),
    ("Sammler", "Alle Gegenstaende", 50, "44444", False, None, False),
]
_d = _wand(_liste)
check("vier Kacheln", len(_d["items"]) == 4, str(len(_d["items"])))
check("die Reihenfolge bleibt die von RetroAchievements",
      [e["badge"] for e in _d["items"]]
      == ["11111", "22222", "33333", "44444"],
      "nach freigeschaltet zu sortieren waere verlockend und falsch - "
      "dann springen beim Freischalten alle anderen Kacheln mit")
check("freigeschaltet richtig gesetzt",
      [e["an"] for e in _d["items"]] == [True, False, True, False])
check("die Anzahl stimmt", _d["anzahl"] == [2, 4], str(_d["anzahl"]))
check("die Punkte stimmen", _d["punkte"] == [30, 90], str(_d["punkte"]))
check("die Beschreibung ist NICHT dabei",
      all("desc" not in e and "beschreibung" not in e
          for e in _d["items"]),
      "sie steht in keiner Kachel und waere bei hundert Erfolgen der "
      "groesste Teil der Nachricht")
check("der Titel ist dabei (fuer den Mauszeiger)",
      _d["items"][0]["titel"] == "Erster Schritt")
# Kaputte Eintraege duerfen die Liste nicht abbrechen.
_kaputt = _wand([("A", "", "keine Zahl", "1", True, None, False),
                 ("B",),
                 None,
                 ("C", "", 7, None, False, None, False)])
check("ein unbrauchbarer Punktwert wird zu 0",
      _kaputt["items"][0]["punkte"] == 0, str(_kaputt["items"][:1]))
check("ein zu kurzer Eintrag wird uebersprungen",
      len(_kaputt["items"]) == 2, str(len(_kaputt["items"])))
check("ein Erfolg ohne Badge bekommt eine leere Kachel",
      _kaputt["items"][1]["badge"] == "")
check("eine leere Liste wirft nicht",
      _wand([])["anzahl"] == [0, 0] and _wand(None)["anzahl"] == [0, 0])

# ---------------------------------------------------------------------------
print()
print("Test 2: am echten Server - was wirklich ueber die Leitung geht")
# ---------------------------------------------------------------------------
_port = _freier_port()
_srv = StreamServer(os.path.join(_TMP, "art"), port=_port, host="127.0.0.1",
                    config_path=os.path.join(_TMP, "cfg.json"),
                    badge_cache_dir=os.path.join(_TMP, "badges"))
# Das Vorholen der Icons wuerde hier ins Netz gehen - abschalten.
_srv._badges_vorholen = lambda namen: None
_srv.start()
_ereignisse = []
_fertig = threading.Event()


def _lauschen():
    try:
        r = urllib.request.urlopen("http://127.0.0.1:%d/events" % _port,
                                   timeout=10)
        art, daten = None, None
        for roh in r:
            z = roh.decode("utf-8", "replace").rstrip("\n")
            if z.startswith("event: "):
                art = z[7:]
            elif z.startswith("data: "):
                daten = z[6:]
            elif z == "" and art:
                _ereignisse.append((art, daten))
                art, daten = None, None
                if len(_ereignisse) >= 12:
                    break
    except Exception:                                    # noqa: BLE001
        pass
    _fertig.set()


try:
    _th = threading.Thread(target=_lauschen, daemon=True)
    _th.start()
    time.sleep(0.6)
    _srv.publish_achievements(_wand(_liste))
    time.sleep(0.4)
    _srv.clear_achievements()
    time.sleep(0.4)

    _arten = [a for a, _d2 in _ereignisse]
    check("das Begruessungspaket kommt",
          _arten[:2] == ["config", "state"], str(_arten[:3]))
    check("die Wand kommt als eigener Ereignistyp",
          "achievements" in _arten, str(_arten))
    _wand_ereignisse = [d for a, d in _ereignisse if a == "achievements"]
    check("zwei davon - einmal Inhalt, einmal leer",
          len(_wand_ereignisse) == 2, str(len(_wand_ereignisse)))
    _erste = json.loads(_wand_ereignisse[0])
    check("der Inhalt kommt heil an",
          _erste["anzahl"] == [2, 4] and len(_erste["items"]) == 4,
          str(_erste["anzahl"]))
    check("und das Leeren schickt null",
          json.loads(_wand_ereignisse[1]) is None,
          "sonst bleibt die Wand des letzten Spiels stehen")

    # DER FALL, DER LEICHT VERGESSEN WIRD: ein Overlay, das sich MITTEN
    # im Spiel neu verbindet.
    _srv.publish_achievements(_wand(_liste))
    time.sleep(0.2)
    r2 = urllib.request.urlopen("http://127.0.0.1:%d/events" % _port,
                                timeout=10)
    _kopf = b""
    _t0 = time.time()
    while b"\n\n" not in _kopf[-4:] or _kopf.count(b"\n\n") < 3:
        if time.time() - _t0 > 5:
            break
        _kopf += r2.read(1)
    r2.close()
    _txt = _kopf.decode("utf-8", "replace")
    check("ein neu verbundenes Overlay bekommt die Wand sofort",
          "event: achievements" in _txt,
          "sonst steht sie leer, bis der naechste Abruf kommt - und "
          "der ist 25 Sekunden entfernt")
    check("und zwar mit Inhalt",
          '"anzahl"' in _txt, _txt[-160:].replace("\n", " "))
finally:
    try:
        _srv.stop()
    except Exception:                                    # noqa: BLE001
        pass

# ---------------------------------------------------------------------------
print()
print("Test 3: geschickt wird nur bei Aenderung")
# ---------------------------------------------------------------------------
_blk = _FE_CODE.split("def _ra_watch_loop")[1].split("\n    @staticmethod")[0] \
    if "def _ra_watch_loop" in _FE_CODE else _FE_CODE
_blk = _FE_CODE.split("wand_stand = None")[1].split("\n    @staticmethod")[0]
check("es gibt einen Vergleichsstand", "wand_stand" in _FE_CODE)
check("verglichen werden Badge und freigeschaltet",
      "(a[3] or a[0], bool(a[4]))" in _blk,
      "die Liste selbst zu vergleichen waere teuer und unnoetig - was "
      "sie aussehen laesst, sind die Badges und wer davon frei ist")
check("und nur dann geschickt",
      "if _stand != wand_stand:" in _blk
      and "publish_achievements(" in _blk)
# GENAU EIN ABRUF, nicht null: der erste Entwurf dieses Tests fragte
# nach null und war prompt rot - der Block beginnt bei "wand_stand =
# None" und enthaelt die Schleife mitsamt ihrem einen Abruf. Gemeint
# war "kein ZWEITER Netzzugriff", und genau das steht jetzt da.
check("die Wand kommt aus dem Abruf, der ohnehin laeuft",
      _blk.count("fetch_ra_game_achievements_bounded") == 1,
      "%d Abrufe - zwei waeren ein zweiter Netzzugriff fuer Daten, die "
      "schon da sind" % _blk.count("fetch_ra_game_achievements_bounded"))
check("ein Fehler beim Senden nimmt den Abruf nicht mit",
      "except Exception:" in _blk)
# Und beim Verlassen des Spiels wird geleert.
check("nach dem Spiel wird die Wand geleert",
      "self.stream.clear_achievements()" in _FE_CODE)
_ende = _FE_CODE.split("ra_watch_stop.set()")[1][:500]
check("und zwar direkt nachdem der Waechter gestoppt wurde",
      "clear_achievements()" in _ende, _ende[:120].replace("\n", " "))

# ---------------------------------------------------------------------------
print()
print("Test 4: die Icons werden gedrosselt vorgeholt")
# ---------------------------------------------------------------------------
# DER EINE ECHTE HAKEN: beim allerersten Mal sind es ~98 Icons von
# retroachievements.org, und in genau diesem Moment laeuft ein Spiel.
_sq = io.open(os.path.join(_REPO, "frontend", "stream_server.py"),
              encoding="utf-8").read()
_sc = "\n".join(z for z in _sq.split("\n")
                if not z.strip().startswith("#"))
check("es gibt ein Vorholen", "def _badges_vorholen" in _sq)
check("in einem EIGENEN Faden",
      "threading.Thread(target=arbeiter" in _sc,
      "nicht im Abruf-Faden - der erkennt die neuen Erfolge und darf "
      "nicht haengen")
check("paketweise", "BADGE_VORRAT_GLEICHZEITIG" in _sc)
check("mit Pause dazwischen",
      "BADGE_VORRAT_PAUSE" in _sc and "time.sleep(self.BADGE_VORRAT_PAUSE)" in _sc)
check("und jedes Icon nur einmal",
      "_badge_vorrat" in _sc and "self._badge_vorrat.add(n)" in _sc,
      "sonst laeuft bei jedem Abruf dasselbe Vorholen wieder los")
check("ein Fehler dabei nimmt das Senden nicht mit",
      "pass      # Vorholen ist Beiwerk" in _sq)
# Das Vorholen selbst, mit einer Attrappe statt Netz.
_srv2 = StreamServer(os.path.join(_TMP, "art2"), port=_freier_port(),
                     host="127.0.0.1",
                     config_path=os.path.join(_TMP, "cfg2.json"),
                     badge_cache_dir=os.path.join(_TMP, "badges2"))
_geholt = []
_srv2._badge_png = lambda n: _geholt.append(n)
_srv2._badges_vorholen(["a", "b", "c", "a", "", None])
time.sleep(2.5)
check("jedes Icon genau einmal geholt",
      sorted(_geholt) == ["a", "b", "c"], str(sorted(_geholt)))
_geholt2 = list(_geholt)
_srv2._badges_vorholen(["a", "b", "c"])
time.sleep(0.8)
check("ein zweiter Aufruf holt nichts noch einmal",
      _geholt == _geholt2, str(_geholt))

# ---------------------------------------------------------------------------
print()
print("Test 5: das Raster im Overlay")
# ---------------------------------------------------------------------------
_node = shutil.which("node") or shutil.which("nodejs")
if _node:
    _h = os.path.join(_HIER, "__wand_pruefung.js")
    try:
        io.open(_h, "w", encoding="utf-8").write(
            "const fs=require('fs');\n"
            "const s=fs.readFileSync(process.argv[2],'utf8');\n"
            "const js=s.split('<script>')[1].split('</script>')[0];\n"
            "new Function(js);\n")
        for _datei in ("stream_overlay.html", "stream_admin.html"):
            _p = subprocess.run(
                [_node, _h, os.path.join(_REPO, "frontend", _datei)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            check("%s: node liest das Skript" % _datei,
                  _p.returncode == 0,
                  _p.stderr.decode("utf-8", "replace").strip()[:200])
    finally:
        try:
            os.remove(_h)
        except OSError:
            pass
else:
    print("  --   node fehlt, Syntaxpruefung uebersprungen")

check("das Raster wird nur bei einem ANDEREN Spiel neu gebaut",
      "const neuesSpiel = (wandAufbau === null" in _JS,
      "sonst legt der Browser jedes <img> neu an, und die frisch "
      "freigeschaltete Kachel blitzt auf einem Element auf, das es "
      "vorher gar nicht gab")
check("beim ersten Mal blitzt nichts",
      "&& !erstesMal" in _JS,
      "wer mitten im Spiel neu laedt, hat vielleicht 74 Erfolge - die "
      "sollen da sein und nicht alle nacheinander aufleuchten")
check("nur was GERADE umgeschlagen ist, blitzt",
      "vorher === false" in _JS)
check("mit erzwungenem Neuberechnen",
      "void node.offsetWidth;" in _JS,
      "derselbe Grund wie beim Toast - sonst laeuft die Animation beim "
      "zweiten Mal nicht")
check("ein Icon, das nicht laedt, zeigt kein zerbrochenes Bild",
      "node.onerror" in _JS)
check("die Spaltenzahl wird begrenzt",
      "Math.min(40," in _JS,
      "eine von Hand verstellte Konfiguration darf das Raster nicht "
      "unbrauchbar machen")
check("null leert die Wand",
      "if(!daten || cfg.show_ra_wall !== true)" in _JS)
check("die Wand ist von Haus aus AUS",
      "cfg.show_ra_wall !== true" in _JS,
      "=== true und nicht !== false: sie belegt Platz")
check("sie haengt an der Konfiguration und wird dort neu gezeichnet",
      "renderWall(lastWall);" in _JS
      and _JS.count("renderWall(") >= 3,
      "sonst wirkt ein Schalter erst beim naechsten Abruf, also bis zu "
      "25 Sekunden spaeter")
check("der Ereignistyp heisst achievements",
      "es.addEventListener('achievements'" in _JS)

check("ausgegraut wird mit einem Filter, nicht mit zweiten Bildern",
      "filter:grayscale(1)" in _CSS,
      "RA hat zwar lock-Icons, aber derselbe Icon plus grayscale() "
      "gibt denselben Look - ohne zweite Download-Sorte")
check("es gibt die Aufblitz-Animation", "@keyframes kachel-an" in _CSS)
check("die Wand hat eine eigene Ecke",
      "#ra-wall.wall-top-right" in _CSS,
      "sonst liegt sie auf der Auswahl-Karte")
check("und der Toast weicht ihr aus",
      "#ra-wall.wall-top-right ~ #achievement-toast" in _CSS)
check("wer weniger Bewegung will, bekommt kein Aufblitzen",
      "prefers-reduced-motion" in _CSS
      and "#ra-wall-grid img.frisch{animation:none}" in _CSS)
check("die Wand faengt keine Klicks ab",
      "pointer-events:none" in _CSS.split("#ra-wall{")[1][:600])

# ---------------------------------------------------------------------------
print()
print("Test 6: die drei Schalter im Backend")
# ---------------------------------------------------------------------------
for _f in ("show_ra_wall", "ra_wall_corner", "ra_wall_cols"):
    check("%-16s steht in der Feldliste" % _f,
          ('"%s"' % _f) in _AD.split("const F = [")[1].split("]")[0])
    check("%-16s wird geladen" % _f, ('$("%s").' % _f) in _AD)
    # Auf "feld:" im Speicher-Block geprueft, nicht auf "feld:$(" -
    # ein Zahlenfeld geht durch parseInt() und steht dann als
    # "ra_wall_cols:parseInt($(...)" da. Der erste Entwurf suchte die
    # engere Form und war bei genau diesem einen Feld rot.
    _speicher = _AD.split("  return {")[1].split("};")[0]
    check("%-16s wird gespeichert" % _f, ("%s:" % _f) in _speicher)
check("die Vorgabe der Wand ist AUS",
      '$("show_ra_wall").checked = c.show_ra_wall===true;' in _AD)
check("der zweite Regler zeigt seinen Wert beim Ziehen",
      'if(id==="ra_wall_cols")' in _AD,
      "sonst steht die Zahl still, und man sieht nicht, wo man ist")
from stream_server import DEFAULT_CONFIG                  # noqa: E402
check("show_ra_wall ist auch im Server AUS vorgegeben",
      DEFAULT_CONFIG.get("show_ra_wall") is False,
      repr(DEFAULT_CONFIG.get("show_ra_wall")))
check("und die beiden anderen haben Vorgaben",
      DEFAULT_CONFIG.get("ra_wall_corner") == "top-right"
      and DEFAULT_CONFIG.get("ra_wall_cols") == 12)

shutil.rmtree(_TMP, ignore_errors=True)
print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
