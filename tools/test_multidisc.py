#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mehrteilige Spiele (Build 259).

NUTZERWUNSCH: "bei PSX, Sega CD oder Saturn bestehen viele Spiele aus
mehreren Discs. Wenn diese alle in einem Ordner liegen, blaeht das die
Spieleliste auf. Das Frontend soll sie zu einem Eintrag zusammenfassen
und beim Starten fragen, welche Disc."

WAS NICHT GEHT, und das steht hier, weil es sonst jemand erneut
vorschlaegt: **.m3u-Playlisten**. MiSTer unterstuetzt sie nicht - eine
MGL verweist immer auf GENAU EINE Datei. Nachgelesen im MiSTer-Forum,
wo ein Core-Entwickler selbst sagt, eine m3u-Umsetzung waere "fairly
awkward given how things work now", und Nutzer berichten, dass
m3u-Dateien beim Laden einer CD gar nicht auswaehlbar sind.
Zusammenfassen und beim Start fragen ist deshalb nicht der zweitbeste
Weg, sondern der einzige richtige.

WORAN ES SCHEITERN KANN - und darum haengt dieser Test daran:

  1. ZWEI FASSUNGEN WERDEN ZU EINER. "Spiel (USA) (Disc 1)" und
     "Spiel (Europe) (Disc 1)" sind zwei Fassungen, keine zwei Teile.
     Sie zusammenzuziehen liesse eine davon verschwinden - genau das
     Problem, das _dedupe_items() seinerzeit behoben hat.
  2. ZWEI SAMMLUNGEN WERDEN ZU EINER. Gleiche Namen in
     VERSCHIEDENEN Ordnern sind verschiedene Ablagen.
  3. EIN EINZELSTUECK WIRD UMBENANNT. Ein alleinstehendes
     "Spiel (Disc 1)" muss seinen Namen behalten - die Beschriftung
     entscheidet, welches Cover gefunden wird.
  4. DISC 10 STEHT VOR DISC 2. Ein sorted() ueber die Namen tut
     genau das.
  5. DER SCHALTER TUT NICHTS. Er formt den Baum beim EINLESEN - ohne
     Eintrag im Fingerabdruck wirkte er erst beim naechsten ohnehin
     faelligen Neuscan.
  6. DIE AUSWAHL SUCHT IM ARCHIV. Ein Pfad durch eine .zip hat kein
     Verzeichnis, das man auflisten koennte.

Ausfuehren:
    python3 tools/test_multidisc.py
"""
import io
import os
import shutil
import sys
import tempfile

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
sys.path.insert(0, os.path.join(_REPO, "frontend"))

fails = []
_TMP = tempfile.mkdtemp(prefix="multidisc_")


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


# ---------------------------------------------------------------------------
print("Test 1: die Namenshilfen")
# ---------------------------------------------------------------------------
from fe.naming import disc_basis, disc_marker, disc_rang   # noqa: E402

check("der Marker wird gefunden",
      disc_marker("Final Fantasy VII (USA) (Disc 2)") == "(Disc 2)")
check("und bei einem normalen Namen nicht",
      disc_marker("Tekken 3 (USA)") == "")
check("die Basis laesst die Region STEHEN",
      disc_basis("Final Fantasy VII (USA) (Disc 2)")
      == "Final Fantasy VII (USA)",
      "sonst faenden USA- und Europe-Fassung zusammen")
check("Disc 2 kommt vor Disc 10",
      sorted(["A (Disc 10)", "A (Disc 2)", "A (Disc 1)"], key=disc_rang)
      == ["A (Disc 1)", "A (Disc 2)", "A (Disc 10)"],
      "ein sorted() ueber die Namen setzte die 10 nach vorn")
check("Buchstaben-Marker funktionieren auch",
      disc_rang("Spiel (Side B)")[0] == 1
      and disc_rang("Spiel (Side A)") < disc_rang("Spiel (Side B)"))

# ---------------------------------------------------------------------------
print()
print("Test 2: das Buendeln beim Einlesen")
# ---------------------------------------------------------------------------
import fe.scan as SC                                       # noqa: E402


def g(label, pfad):
    return (label, "game", (pfad, ".chd", "PSX", None, (0, 0, 0)))


ROH = [
    g("Final Fantasy VII (USA) (Disc 1)", "/g/PSX/FF7 D1.chd"),
    g("Final Fantasy VII (USA) (Disc 10)", "/g/PSX/FF7 D10.chd"),
    g("Final Fantasy VII (USA) (Disc 2)", "/g/PSX/FF7 D2.chd"),
    g("Final Fantasy VII (Europe) (Disc 1)", "/g/PSX/FF7E D1.chd"),
    g("Final Fantasy VII (Europe) (Disc 2)", "/g/PSX/FF7E D2.chd"),
    g("Tekken 3 (USA)", "/g/PSX/Tekken.chd"),
    g("Einzelstueck (Disc 1)", "/g/PSX/Einzel.chd"),
    g("Anderswo (Disc 1)", "/g/PSX/A/x1.chd"),
    g("Anderswo (Disc 2)", "/g/PSX/B/x2.chd"),
    # Im Archiv: muss getrennt bleiben, siehe Bedingung 4.
    g("Im Archiv (Disc 1)", "/g/PSX/Sammlung.zip/Im Archiv (Disc 1).chd"),
    g("Im Archiv (Disc 2)", "/g/PSX/Sammlung.zip/Im Archiv (Disc 2).chd"),
]
raus = SC._dedupe_items(list(ROH))
namen = [it[0] for it in raus]
check("die drei USA-Discs werden eine Zeile",
      namen.count("Final Fantasy VII (USA)") == 1, str(namen))
check("und zwar mit Disc 1 dahinter",
      dict((it[0], it[2][0]) for it in raus)["Final Fantasy VII (USA)"]
      == "/g/PSX/FF7 D1.chd",
      "Disc 1, nicht Disc 10 - disc_rang() statt sorted()")
check("die Europe-Fassung bleibt eine EIGENE Zeile",
      "Final Fantasy VII (Europe)" in namen,
      "zwei Fassungen sind keine zwei Teile")
check("ein Spiel ohne Marker bleibt unberuehrt",
      "Tekken 3 (USA)" in namen)
check("ein alleinstehender Teil behaelt seinen Namen",
      "Einzelstueck (Disc 1)" in namen,
      "die Beschriftung entscheidet, welches Cover gefunden wird")
check("Teile aus VERSCHIEDENEN Ordnern bleiben getrennt",
      "Anderswo (Disc 1)" in namen and "Anderswo (Disc 2)" in namen,
      str(namen))
check("Teile IN EINEM ARCHIV bleiben getrennt",
      "Im Archiv (Disc 1)" in namen and "Im Archiv (Disc 2)" in namen,
      "beim Starten wird mit os.listdir() nach den Geschwistern "
      "gesucht - durch ein Archiv geht das nicht, die Frage kaeme nie, "
      "und die uebrigen Teile waeren weg UND nicht startbar")
check("aus elf Zeilen werden acht", len(raus) == 8, str(len(raus)))

# Abgeschaltet bleibt alles, wie es war.
import fe.settings as S                                    # noqa: E402
from fe.zwischenspeicher import vergessen as _vergessen    # noqa: E402

S.MULTIDISC_AUS_FLAG = os.path.join(_TMP, "multidisc_aus")
open(S.MULTIDISC_AUS_FLAG, "w").close()
_vergessen()
check("abgeschaltet bleiben alle neun Zeilen",
      len(SC._dedupe_items(list(ROH))) == len(ROH))
os.remove(S.MULTIDISC_AUS_FLAG)
_vergessen()

# ---------------------------------------------------------------------------
print()
print("Test 3: der Schalter steckt im Fingerabdruck")
# ---------------------------------------------------------------------------
_q = io.open(os.path.join(_REPO, "frontend", "fe", "scan.py"),
             encoding="utf-8").read()
check("__multidisc__ geht in die Signatur ein",
      '"__multidisc__"' in _q,
      "ohne das taete der Schalter bis zum naechsten ohnehin "
      "faelligen Neuscan nichts")
check("und die Logik-Fassung wurde hochgezaehlt",
      "SCAN_LOGIC_VERSION = 6" in _q,
      "sonst liest ein vorhandener Cache die alte, ungebuendelte "
      "Liste weiter aus")

# ---------------------------------------------------------------------------
print()
print("Test 4: die Auswahl beim Starten")
# ---------------------------------------------------------------------------
from fe.launch import disc_geschwister                     # noqa: E402

spiele = os.path.join(_TMP, "PSX")
os.makedirs(spiele)
for n in ("FF7 (USA) (Disc 1).chd", "FF7 (USA) (Disc 2).chd",
          "FF7 (USA) (Disc 10).chd", "FF7 (USA) (Disc 1).cue",
          "FF7 (Europe) (Disc 1).chd", "Tekken (USA).chd"):
    io.open(os.path.join(spiele, n), "w").close()

teile = disc_geschwister(os.path.join(spiele, "FF7 (USA) (Disc 1).chd"))
check("alle drei Teile werden gefunden", len(teile) == 3, str(teile))
check("in der richtigen Reihenfolge",
      [m for m, _p in teile] == ["(Disc 1)", "(Disc 2)", "(Disc 10)"],
      str([m for m, _p in teile]))
check("eine andere Endung zaehlt nicht mit",
      all(p.endswith(".chd") for _m, p in teile),
      "die .cue daneben ist dieselbe Disc, kein weiterer Teil")
check("eine andere Fassung zaehlt nicht mit",
      all("Europe" not in p for _m, p in teile))
check("ein Spiel ohne Marker liefert nichts",
      disc_geschwister(os.path.join(spiele, "Tekken (USA).chd")) == [])
check("ein alleinstehender Teil liefert nichts",
      disc_geschwister(os.path.join(spiele, "FF7 (Europe) (Disc 1).chd"))
      == [],
      "unter zwei Teilen gibt es nichts zu fragen")
check("im Archiv wird nicht gesucht",
      disc_geschwister("/g/x.zip/FF7 (Disc 1).chd") == [],
      "ein Pfad durch eine .zip hat kein Verzeichnis")
check("ein nicht vorhandener Ordner stuerzt nicht ab",
      disc_geschwister("/gibt/es/nicht/FF7 (Disc 1).chd") == [])

# ---------------------------------------------------------------------------
print()
print("Test 5: die Anbindung im Startweg")
# ---------------------------------------------------------------------------
_FE = io.open(os.path.join(_REPO, "frontend", "frontend.py"),
              encoding="utf-8").read()
_spiel = _FE.split('elif kind == "game":')[1][:2500]
_code = "\n".join(z for z in _spiel.split("\n")
                  if not z.strip().startswith("#"))
check("gefragt wird im Spielstart", "disc_geschwister(rom)" in _code)
check("und VOR der Core-Frage",
      _code.index("disc_geschwister(rom)") < _code.index("find_ra_core("),
      "wer die Auswahl abbricht, soll nicht erst noch den Core "
      "gewaehlt haben")
check("ein Abbruch startet nichts",
      "if _w is None:" in _code and "continue" in _code)
check("die Wahl ersetzt den Pfad", "rom = _discs[_w][1]" in _code)
check("es gibt weiterhin genau einen Startweg fuer Spiele",
      _FE.count('elif kind == "game":') == 1)

# ---------------------------------------------------------------------------
print()
print("Test 6: Schalter, Texte, Menuepunkt")
# ---------------------------------------------------------------------------
import fe.translations as TR                               # noqa: E402

check("die Vorgabe ist AN", S.multidisc_buendeln() is True,
      "dieselbe Sorte Aufraeumen wie das Zusammenfassen doppelter "
      "Regionen - niemand sucht ein Spiel unter 'Disc 2'")
for sch in ("disc_titel", "sys_multidisc_an", "sys_multidisc_aus",
            "multidisc_hinweis"):
    e = TR.TRANSLATIONS.get(sch)
    check("Text '%s' gibt es in beiden Sprachen" % sch,
          bool(e and e.get("de") and e.get("en")), str(e))

from fe.menu import system_items                           # noqa: E402


def _finden(node, kind):
    for it in node.get("items", []):
        if it[1] == kind:
            return it[0]
    for _n, sub in node.get("folders", {}).items():
        tr = _finden(sub, kind)
        if tr:
            return tr
    return None


check("es gibt einen Menuepunkt",
      _finden(system_items(), "multidisc") is not None)
check("und einen Hinweis, dass er erst beim Einlesen wirkt",
      "multidisc_hinweis" in _FE,
      "sonst sieht es aus, als taete der Schalter nichts")

shutil.rmtree(_TMP, ignore_errors=True)
print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
