#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gamelist.xml als Metadatenquelle (Build 188).

WOZU

Wer sein ROM-Verzeichnis mit Skraper oder ScreenScraper gepflegt hat,
hat dort eine gamelist.xml im EmulationStation-Format liegen - mit
Jahr, Genre, Spielerzahl, Hersteller und Beschreibung. Genau das, was
wir sonst ueber meta/<system>.json und die fremde Datenbank
zusammensuchen. Kein Werkzeug, kein Download: liegt sie da, wird sie
gelesen.

WAS DIESER TEST ABSICHERT

  - dass die Felder richtig ankommen, auch bei krummen Angaben,
  - die RANGFOLGE: eigene Daten schlagen die gamelist, die gamelist
    schlaegt die fremde Datenbank - und sie ERSETZT nie, sie fuellt,
  - dass eine kaputte oder halbe Datei nichts umwirft (sie liegt im
    Verzeichnis des Nutzers, dort kann alles stehen),
  - dass stromweise gelesen wird und der Baum dabei geleert wird -
    ohne das waere das Lesen nur dem Namen nach sparsam,
  - und dass sich die Quelle abschalten laesst.

Ausfuehren:
    python3 tools/test_gamelist.py
"""
import io
import os
import shutil
import sys
import tempfile

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
sys.path.insert(0, os.path.join(_REPO, "frontend"))

import fe.art as A                                       # noqa: E402
import fe.paths                                          # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


XML = """<?xml version="1.0"?>
<gameList>
  <game>
    <path>./Super Mario World.sfc</path>
    <name>Super Mario World</name>
    <desc>Mario rettet das Dinosaurier-Land.
    Mit Yoshi.</desc>
    <releasedate>19911121T000000</releasedate>
    <developer>Nintendo EAD</developer>
    <publisher>Nintendo</publisher>
    <genre>Jump and Run</genre>
    <players>1-2</players>
    <image>./media/images/Super Mario World.png</image>
    <thumbnail>./media/thumbs/Super Mario World.png</thumbnail>
  </game>
  <game>
    <path>./Nur Thumbnail.sfc</path>
    <genre>Test</genre>
    <thumbnail>./media/thumbs/Nur Thumbnail.png</thumbnail>
  </game>
  <game>
    <path>./Bild Weg.sfc</path>
    <genre>Test</genre>
    <image>./media/images/gibtesnicht.png</image>
  </game>
  <game>
    <path>./Nur Entwickler.sfc</path>
    <developer>Irgendwer</developer>
  </game>
  <game>
    <path>./Krummes Datum.sfc</path>
    <releasedate>0000</releasedate>
    <genre>Test</genre>
  </game>
  <game>
    <path>./Leer.sfc</path>
  </game>
</gameList>
"""


def aufbauen(text=XML, name="gamelist.xml", mit_bildern=True):
    """Eine gamelist.xml an genau der Stelle, an der das Frontend
    suchen wuerde - samt der Bilder, auf die sie zeigt."""
    basis = tempfile.mkdtemp(prefix="gamelist_test_")
    os.makedirs(os.path.join(basis, "SNES"))
    io.open(os.path.join(basis, "SNES", name), "w",
            encoding="utf-8").write(text)
    if mit_bildern:
        for unter, datei in (("images", "Super Mario World.png"),
                             ("thumbs", "Super Mario World.png"),
                             ("thumbs", "Nur Thumbnail.png")):
            ordner = os.path.join(basis, "SNES", "media", unter)
            os.makedirs(ordner, exist_ok=True)
            # "gibtesnicht.png" wird mit Absicht NICHT angelegt.
            open(os.path.join(ordner, datei), "wb").write(b"\x89PNG")
    return basis


_alte_bases = list(fe.paths.GAMES_BASES)


def mit_basis(basis):
    fe.paths.GAMES_BASES = [basis]
    A._gamelist_cache.clear()


def zurueck():
    fe.paths.GAMES_BASES = list(_alte_bases)
    A._gamelist_cache.clear()


# ---------------------------------------------------------------------------
print("Test 1: die Felder kommen an")
# ---------------------------------------------------------------------------
basis = aufbauen()
try:
    mit_basis(basis)
    m = A.gamelist_meta("SNES", "Super Mario World")
    check("Jahr aus releasedate", m.get("year") == "1991", m.get("year"))
    check("Genre", m.get("genre") == "Jump and Run", m.get("genre"))
    check("Spielerzahl", m.get("players") == "1-2", m.get("players"))
    check("Hersteller: publisher schlaegt developer",
          m.get("manufacturer") == "Nintendo", m.get("manufacturer"),)
    check("Beschreibung ohne Zeilenumbrueche",
          m.get("desc", "").startswith("Mario rettet")
          and "\n" not in m.get("desc", ""),
          repr(m.get("desc", ""))[:70])
    check("und sie kommt auch ueber gamelist_synopsis()",
          A.gamelist_synopsis("SNES", "Super Mario World") == m.get("desc"))

    m2 = A.gamelist_meta("SNES", "Nur Entwickler")
    check("ohne publisher gilt der developer",
          m2.get("manufacturer") == "Irgendwer", m2)

    m3 = A.gamelist_meta("SNES", "Krummes Datum")
    check("ein unbrauchbares Datum wird weggelassen",
          "year" not in m3,
          "ein falsch geratenes Jahr waere schlimmer als keines")
    check("der Rest des Eintrags bleibt aber",
          m3.get("genre") == "Test", m3)

    check("ein Eintrag ganz ohne Felder taucht nicht auf",
          A.gamelist_meta("SNES", "Leer") == {})
    check("und ein unbekannter Name liefert nichts",
          A.gamelist_meta("SNES", "Gibt es nicht") == {})
    check("Gross- und Kleinschreibung ist egal",
          A.gamelist_meta("SNES", "SUPER MARIO WORLD").get("year") == "1991")
finally:
    zurueck()
    shutil.rmtree(basis, ignore_errors=True)

# ---------------------------------------------------------------------------
print()
print("Test 2: DIE RANGFOLGE - fuellen, nicht ersetzen")
# ---------------------------------------------------------------------------
basis = aufbauen()
try:
    mit_basis(basis)
    A._meta_cache.clear()
    A._meta_cache["SNES"] = {"Super Mario World": {"year": "1990"}}
    m = A.get_meta("SNES", "Super Mario World")
    check("eigene Daten gewinnen", m.get("year") == "1990", m.get("year"))
    check("aber die Luecken fuellt die gamelist",
          m.get("genre") == "Jump and Run", m.get("genre"))

    A._meta_cache["SNES"] = {}
    m = A.get_meta("SNES", "Super Mario World")
    check("ohne eigene Daten gilt die gamelist",
          m.get("year") == "1991" and m.get("players") == "1-2", m)
finally:
    A._meta_cache.clear()
    zurueck()
    shutil.rmtree(basis, ignore_errors=True)

# ---------------------------------------------------------------------------
print()
print("Test 3: kaputte Dateien werfen nichts um")
# ---------------------------------------------------------------------------
# Sie liegt im Verzeichnis des Nutzers. Dort kann alles stehen - eine
# halb geschriebene Datei, eine leere, oder etwas ganz anderes.
for name, text in (("abgeschnitten", "<gameList><game><path>x</path>"),
                   ("leer", ""),
                   ("kein XML", "das ist kein XML"),
                   ("nur Wurzel", "<gameList></gameList>")):
    basis = aufbauen(text)
    try:
        mit_basis(basis)
        try:
            erg = A.gamelist_meta("SNES", "x")
            ok = isinstance(erg, dict)
        except Exception as e:                           # noqa: BLE001
            ok = False
            print("    ", type(e).__name__, e)
        check("%-14s -> kein Absturz" % name, ok)
    finally:
        zurueck()
        shutil.rmtree(basis, ignore_errors=True)

# ---------------------------------------------------------------------------
print()
print("Test 4: abschaltbar")
# ---------------------------------------------------------------------------
basis = aufbauen()
try:
    mit_basis(basis)
    _echt = os.path.exists
    os.path.exists = lambda p: (True if p == A.GAMELIST_AUS_FLAG
                                else _echt(p))
    A._gamelist_cache.clear()
    try:
        check("mit Schalterdatei kommt nichts mehr",
              A.gamelist_meta("SNES", "Super Mario World") == {})
    finally:
        os.path.exists = _echt
        A._gamelist_cache.clear()
    check("ohne sie wieder schon",
          A.gamelist_meta("SNES", "Super Mario World").get("year") == "1991")
finally:
    zurueck()
    shutil.rmtree(basis, ignore_errors=True)

# ---------------------------------------------------------------------------
print()
print("Test 5: stromweise gelesen, nicht am Stueck")
# ---------------------------------------------------------------------------
# Eine gamelist.xml mit 10.000 Eintraegen ist schnell 20 MB gross. Sie
# in einen DOM-Baum zu laden waere auf einem Geraet mit 1 GB RAM genau
# die Sorte stiller Kosten, gegen die die Builds 104-110 angegangen
# sind.
quelle = io.open(os.path.join(_REPO, "frontend", "fe", "art.py"),
                 encoding="utf-8").read()
_block = quelle[quelle.index("def _gamelist_lesen("):]
_block = _block[:_block.index("\ndef ", 10)]
check("iterparse statt parse", "iterparse" in _block
      and "ET.parse(" not in _block)
check("und der Baum wird geleert", "elem.clear()" in _block,
      "ohne das waechst er trotzdem weiter")
check("die Leerung steht in einem finally",
      "finally:" in _block,
      "sonst bleibt sie bei einem kaputten Eintrag aus")
check("es gibt eine Obergrenze fuer die Eintraege",
      "GAMELIST_MAX_EINTRAEGE" in quelle)

# ---------------------------------------------------------------------------
print()
print("Test 6: die Beschreibung erreicht die Galerie")
# ---------------------------------------------------------------------------
basis = aufbauen()
try:
    mit_basis(basis)
    text = A.docs_synopsis("SNES", "Super Mario World", "de")
    check("docs_synopsis nimmt die gamelist zuerst",
          text.startswith("Mario rettet"), repr(text)[:60])
    check("und das auch bei abgeschalteten fremden Quellen",
          "keine fremde Quelle" in quelle,
          "die gamelist gehoert dem Nutzer")
finally:
    zurueck()
    shutil.rmtree(basis, ignore_errors=True)

# ---------------------------------------------------------------------------
print()
print("Test 7: die BILDER aus der gamelist.xml (Build 191)")
# ---------------------------------------------------------------------------
# Der eigentliche Gewinn: Skraper ordnet ueber die PRUEFSUMME der
# ROM-Datei zu, nicht ueber den Namen. Fuer ein gepflegtes Verzeichnis
# entfaellt damit genau das Problem, an dem der unscharfe Vergleich aus
# Build 117 arbeitet.
basis = aufbauen()
try:
    mit_basis(basis)
    pfad = A.gamelist_cover("SNES", "Super Mario World")
    check("das Cover wird gefunden", bool(pfad), pfad)
    check("und es ist <image>, nicht <thumbnail>",
          bool(pfad) and os.sep + "images" + os.sep in pfad, pfad)
    check("der relative Pfad wurde gegen den gamelist-Ordner aufgeloest",
          bool(pfad) and os.path.isabs(pfad) and os.path.isfile(pfad))

    pfad = A.gamelist_cover("SNES", "Nur Thumbnail")
    check("ohne <image> tut es auch das <thumbnail>",
          bool(pfad) and os.sep + "thumbs" + os.sep in pfad, pfad)

    check("ein Pfad ins Leere liefert None",
          A.gamelist_cover("SNES", "Bild Weg") is None,
          "sonst haelt der Aufrufer ihn fuer ein Cover und sucht nicht weiter")
    check("und die Metadaten desselben Eintrags bleiben trotzdem",
          A.gamelist_meta("SNES", "Bild Weg").get("genre") == "Test")

    # Die eigentliche Einhaengestelle: _art_path_in() - eine Stelle,
    # acht Aufrufer.
    A._art_index_cache.clear()
    erg = A._art_path_in("/gibt/es/nicht", "SNES", "Super Mario World")
    check("die Cover-Suche benutzt es", bool(erg) and erg.endswith(".png"),
          erg)
finally:
    A._art_index_cache.clear()
    zurueck()
    shutil.rmtree(basis, ignore_errors=True)

# ---------------------------------------------------------------------------
print()
print("Nachtrag (Build 251): DOCTYPE/ENTITY wird abgewiesen")
# ---------------------------------------------------------------------------
# DIE EINZIGE FLANKE, die beim Nachsehen offen war. ElementTree aus der
# Standardbibliothek holt keine externen Dateien nachgeladen (kein
# XXE), expandiert aber INTERNE Entities - zehn verschachtelte, die
# sich je zehnmal aufeinander beziehen, werden beim Einlesen zu einem
# Gigabyte Text ("Billion Laughs"). Auf einem Geraet mit 1 GB RAM ist
# das Frontend dann weg, mitten im Start.
#
# Niemand baut so eine Datei versehentlich. Aber eine gamelist.xml
# kommt aus dem Verzeichnis des Nutzers, und der ganze Rest dieses
# Lesers ist genau darauf gebaut ("dort kann alles Moegliche stehen").
_bombe = tempfile.mkdtemp(prefix="gamelist_bombe_")
try:
    _p = os.path.join(_bombe, "gamelist.xml")
    io.open(_p, "w", encoding="utf-8").write(
        '<?xml version="1.0"?>\n'
        '<!DOCTYPE gameList [\n'
        '  <!ENTITY a "aaaaaaaaaa">\n'
        '  <!ENTITY b "&a;&a;&a;&a;&a;&a;&a;&a;&a;&a;">\n'
        ']>\n'
        '<gameList><game><path>./x.sfc</path>'
        '<genre>&b;</genre></game></gameList>\n')
    _raus = {}
    try:
        _n = A._gamelist_lesen(_p, _raus)
        _lief, _fehler = True, ""
    except Exception as e:                               # noqa: BLE001
        _n, _lief, _fehler = -1, False, "%s: %s" % (type(e).__name__, e)
    check("der Leser wirft nicht", _lief, _fehler)
    check("und liest NICHTS daraus", _n == 0 and not _raus,
          "%d Eintraege, %d Namen" % (_n, len(_raus)))

    # Die Gegenprobe: dieselbe Datei OHNE die Erklaerung wird gelesen.
    # Ohne sie wuerde dieser Test auch bei einem kaputten Leser gruen.
    _p2 = os.path.join(_bombe, "gut.xml")
    io.open(_p2, "w", encoding="utf-8").write(
        '<?xml version="1.0"?>\n'
        '<gameList><game><path>./x.sfc</path>'
        '<genre>Platform</genre></game></gameList>\n')
    _raus2 = {}
    _n2 = A._gamelist_lesen(_p2, _raus2)
    check("eine gewoehnliche Datei wird weiterhin gelesen",
          _n2 == 1 and _raus2.get("x", {}).get("genre") == "Platform",
          "%d Eintraege, %r" % (_n2, _raus2))

    # Eine Datei, die es nicht gibt, darf auch nichts werfen.
    check("eine fehlende Datei wirft nicht",
          A._gamelist_lesen(os.path.join(_bombe, "gibtsnicht.xml"), {}) == 0)
finally:
    shutil.rmtree(_bombe, ignore_errors=True)

# ---------------------------------------------------------------------------
print()
print("Nachtrag (Build 251): der Entwickler kommt im Filter an")
# ---------------------------------------------------------------------------
# EIN FEHLER, DER SEIT BUILD 188 DRIN WAR. Die Quellen benutzen zwei
# Schluessel fuer dieselbe Sache: gameinfo.tsv schreibt "developer",
# die gamelist.xml und die .mra-Dateien schreiben "manufacturer". Der
# Filter fragte nur nach "developer" - wer seine Metadaten aus einer
# gamelist bezieht, hatte den Entwickler-Filter dauerhaft leer, und in
# ARCADE ebenfalls. Angezeigt wurde der Hersteller die ganze Zeit.
#
# Das sieht nach "es gibt keine Daten" aus und nicht nach einem Fehler -
# genau deshalb ist es nie gemeldet worden.
import fe.filter as FILTER                                 # noqa: E402

for _meta, _erw, _was in (
        ({"developer": "Nintendo"}, "Nintendo", "gameinfo.tsv"),
        ({"manufacturer": "Capcom"}, "Capcom", "gamelist/Arcade"),
        ({"developer": "Rare", "manufacturer": "Nintendo"}, "Rare",
         "beides - developer gewinnt"),
        ({"developer": "  ", "manufacturer": "Sega"}, "Sega",
         "leer zaehlt nicht"),
        ({}, "", "nichts da")):
    check("%-24s -> %r" % (_was, _erw),
          FILTER.entwickler_von(_meta) == _erw,
          repr(FILTER.entwickler_von(_meta)))

_eintraege = [("A", "game", None), ("B", "game", None), ("C", "game", None)]
_metas = {"A": {"manufacturer": "Capcom"},
          "B": {"developer": "Konami"},
          "C": {}}
_werte = FILTER.werte_sammeln(_eintraege, lambda n: _metas.get(n, {}))
check("beide Schreibweisen stehen in der Auswahlliste",
      _werte["entwickler"] == ["Capcom", "Konami"],
      str(_werte["entwickler"]))
_treffer = FILTER.anwenden(_eintraege, lambda n: _metas.get(n, {}),
                           {"entwickler": "Capcom"})
check("und ein gamelist-Hersteller wird wirklich gefiltert",
      [e[0] for e in _treffer] == ["A"],
      str([e[0] for e in _treffer]))
check("die Rohfassung wuerde hier nichts finden",
      not [e for e in _eintraege
           if (_metas.get(e[0], {}).get("developer") or "") == "Capcom"],
      "so sah es vor Build 251 aus - leere Liste, kein Fehler")

quelle_art = io.open(os.path.join(_REPO, "frontend", "fe", "art.py"),
                     encoding="utf-8").read()
_block = quelle_art[quelle_art.index("def _art_path_in("):]
_block = _block[:_block.index("\ndef ", 10)]
check("eigenes Artwork kommt weiterhin ZUERST",
      _block.index("idx.get(rom_basename)") < _block.index("gamelist_cover("),
      "sonst ueberschreibt eine gamelist das, was der Nutzer selbst angelegt hat")
check("und die gamelist vor der fremden Datenbank",
      _block.index("gamelist_cover(") < _block.index("docs_cover("))

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
