#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Der ROM-Waechter (Build 258).

NUTZERWUNSCH: "wenn ich im laufenden Betrieb mit WinSCP oder MiSTer
Companion ROMs entferne oder neue hinzufuege, erkennt das Frontend
diese nicht, ohne die Spieleliste neu einzulesen."

WORAN ES SCHEITERN KANN - und genau daran haengt dieser Test:

  1. ER LIEST VON SELBST NACH. Das dauert bei einer grossen Sammlung
     Sekunden bis Minuten; mitten im Scrollen waere es ein sichtbarer
     Haenger, und es ist eine Entscheidung des Nutzers. Dieselbe Linie
     wie beim Speicher-Waechter seit Build 213.
  2. ER MELDET DASSELBE IMMER WIEDER. Der Ruhemoment laeuft staendig
     durch - ohne Sperre stuende die Meldung bei jedem Durchgang
     wieder da.
  3. ER VERGISST DIE MELDUNG ZU FRUEH. Uebernimmt er den neuen Stand
     schon beim Melden, ist die Meldung nach einmal Wegklicken weg -
     und wer sie verpasst hat, sitzt wieder vor einer Liste, die nicht
     stimmt. Genau das hat Build 251 beim Speicher-Waechter behoben.
  4. ER GREIFT IM ZEICHENWEG AUF DIE KARTE ZU. Ein Fingerabdruck ist
     ein Dutzend Dateisystemzugriffe.
  5. ER LEGT EINEN ZWEITEN WEG ZUM NACHLESEN AN. Es gibt seit Build
     251 einen, und zwei Wege zum selben Ziel laufen auseinander.
  6. EIN ORDNERWECHSEL GILT ALS AENDERUNG. Der beobachtete Ordner
     wechselt staendig - beim ersten Blick darf er nicht melden.

GEZAEHLT, NICHT GESTOPPT: wie teuer ein Blick ist, haengt an der
Karte und gehoert auf das Geraet gemessen. Was dieser Test
stattdessen festhaelt, ist die ZAHL der Blicke - und die ist auf jedem
Geraet dieselbe.

Ausfuehren:
    python3 tools/test_romwacht.py
"""
import io
import os
import sys

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
sys.path.insert(0, os.path.join(_REPO, "frontend"))

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


import fe.romwacht as RW                                   # noqa: E402

_FE = io.open(os.path.join(_REPO, "frontend", "frontend.py"),
              encoding="utf-8").read()

# ---------------------------------------------------------------------------
print("Test 1: er meldet eine Aenderung - und zwar genau einmal")
# ---------------------------------------------------------------------------
stand = {"SNES": [("fat:SNES", 100)], "NES": [("fat:NES", 50)]}
w = RW.RomWaechter(signatur_fn=lambda: dict(stand))
w.merken()
T = [1000.0]


def tick():
    T[0] += RW.ROMWACHT_TAKT
    return T[0]


check("ohne Aenderung meldet er nichts", w.pruefen(jetzt=tick()) is None)
stand["SNES"] = [("fat:SNES", 101)]
check("eine Aenderung wird gemeldet", w.pruefen(jetzt=tick()) == "SNES")
check("und beim zweiten Mal nicht noch einmal",
      w.pruefen(jetzt=tick()) is None,
      "sonst stuende die Meldung bei jedem Durchgang durch den "
      "Ruhemoment wieder da")
check("der Stand bleibt aber ALT, bis nachgelesen wurde",
      w.stand["SNES"] == [("fat:SNES", 100)],
      "sonst ist die Meldung nach einmal Wegklicken endgueltig weg - "
      "genau das Problem, das Build 251 behoben hat")

# Eine ZWEITE, andere Aenderung muss wieder durchkommen.
stand["NES"] = [("fat:NES", 51)]
check("eine weitere Aenderung kommt durch",
      w.pruefen(jetzt=tick()) == "NES, SNES",
      "sie ist eine andere Nachricht, keine Wiederholung")

w.merken()
check("nach dem Nachlesen ist Ruhe", w.pruefen(jetzt=tick()) is None)

# ---------------------------------------------------------------------------
print()
print("Test 2: die eigene Uhr")
# ---------------------------------------------------------------------------
w2 = RW.RomWaechter(signatur_fn=lambda: dict(stand))
w2.merken()
t = 5000.0
w2.pruefen(jetzt=t)
vorher = w2.blicke
for _ in range(20):
    t += RW.ROMWACHT_TAKT / 10.0
    w2.pruefen(jetzt=t)
check("zwischen zwei Takten wird nicht nachgesehen",
      w2.blicke - vorher <= 2,
      "%d Blicke in zwei Takten - ein Fingerabdruck ist ein Dutzend "
      "Zugriffe auf die Karte" % (w2.blicke - vorher))
check("und der Takt ist traege genug", RW.ROMWACHT_TAKT >= 10.0,
      "%.0f s" % RW.ROMWACHT_TAKT)

# ---------------------------------------------------------------------------
print()
print("Test 2b: ein Blick bleibt flach - GEZAEHLT")
# ---------------------------------------------------------------------------
# DAS IST DIE WICHTIGSTE ZAHL DIESES BUILDS, und sie ist eine
# Obergrenze gegen einen Fehler, der in diesem Projekt schon einmal
# passiert ist: v1.32 hat den Fingerabdruck REKURSIV gebaut und musste
# zurueckgerollt werden, weil bei einer grossen Sammlung ueber USB
# jeder Start minutenlang dauerte. Wuerde jemand das wieder einbauen,
# waere der Waechter das erste, was es merkt - er fragt alle 20
# Sekunden.
#
# Gezaehlt wird die Zahl der Zugriffe, NICHT die Dauer: die Zahl ist
# auf jedem Geraet dieselbe, die Dauer gehoert auf den MiSTer
# gemessen. Dieselbe Regel wie seit Build 249.
import fe.scan as _SC                                      # noqa: E402

_zaehler = {"n": 0}
_echt = os.path.getmtime


def _gezaehlt(pfad):
    _zaehler["n"] += 1
    return _echt(pfad)


os.path.getmtime = _gezaehlt
try:
    _sig, _per = _SC._games_signature()
    _n_erst = _zaehler["n"]
    _zaehler["n"] = 0
    _w = RW.RomWaechter()
    _w.merken()
    _n_merken = _zaehler["n"]
    _zaehler["n"] = 0
    _w.pruefen(jetzt=99999.0)
    _n_blick = _zaehler["n"]
finally:
    os.path.getmtime = _echt

_systeme = max(1, len(_per))
print("    %d Systeme im Fingerabdruck, %d Zugriffe je Blick"
      % (_systeme, _n_blick))
check("ein Blick kostet hoechstens zwei Zugriffe je System",
      _n_blick <= _systeme * 2 + 8,
      "%d Zugriffe bei %d Systemen - mehr hiesse, dass jemand wieder "
      "rekursiv zaehlt (siehe v1.32)" % (_n_blick, _systeme))
check("und merken() kostet nicht mehr als ein Blick",
      _n_merken <= _n_blick + 2, "%d gegen %d" % (_n_merken, _n_blick))

# ---------------------------------------------------------------------------
print()
print("Test 3: der beobachtete Ordner")
# ---------------------------------------------------------------------------
import tempfile                                            # noqa: E402

_TMP = tempfile.mkdtemp(prefix="romwacht_")
ordner = os.path.join(_TMP, "Hacks")
os.makedirs(ordner)

fest = {"SNES": [("fat:SNES", 1)]}
w3 = RW.RomWaechter(signatur_fn=lambda: dict(fest))
w3.merken()
t = 9000.0


def tick3():
    global t
    t += RW.ROMWACHT_TAKT
    return t


check("ein neu beobachteter Ordner meldet beim ERSTEN Blick nichts",
      w3.pruefen([ordner], jetzt=tick3()) is None,
      "ein Ordnerwechsel ist keine Aenderung am Dateisystem")
# Eine Datei anlegen aendert die mtime des Ordners.
io.open(os.path.join(ordner, "neu.sfc"), "w").write("x")
os.utime(ordner, (10 ** 9, 10 ** 9))
check("eine Aenderung IM Ordner wird gemeldet",
      w3.pruefen([ordner], jetzt=tick3()) == "Hacks",
      "das ist der Ausgleich dafuer, dass der Fingerabdruck nur die "
      "oberste Ebene sieht")
check("und auch hier nur einmal",
      w3.pruefen([ordner], jetzt=tick3()) is None)
check("die Zahl der beobachteten Ordner ist begrenzt",
      len(RW.RomWaechter._begrenzt(["/a"] * 50)) <= RW.MAX_EXTRA,
      "sonst waere eine tiefe Navigation ein wachsender Posten je Blick")

import shutil                                              # noqa: E402

shutil.rmtree(_TMP, ignore_errors=True)

# ---------------------------------------------------------------------------
print()
print("Test 4: die Anbindung im Frontend")
# ---------------------------------------------------------------------------
check("der Waechter wird neben dem Speicher-Waechter angelegt",
      "self._romwacht = ROMWACHT.RomWaechter()" in _FE)
check("und nach JEDEM Einlesen auf den neuen Stand gesetzt",
      _FE.count("self._romwacht.merken(") == _FE.count("self._speicher.merken()"),
      "%d gegen %d - sonst meldet er die gerade eingelesene Aenderung "
      "gleich noch einmal"
      % (_FE.count("self._romwacht.merken("),
         _FE.count("self._speicher.merken()")))

# Gefragt wird NUR im Ruhemoment - also in demselben Block wie der
# Speicher-Waechter.
_ruhe = _FE.split("self._speicher.pruefen()")[1][:3000]
check("gefragt wird im selben Ruhemoment wie beim Speicher-Waechter",
      "self._romwacht.pruefen(" in _ruhe,
      "ein Fingerabdruck hat im Zeichenweg nichts verloren")
check("und nur, wenn der Schalter an ist", "romwacht_an()" in _ruhe)

_zweig = _FE.split("self._romwacht.pruefen(")[1][:900]
check("es wird NICHT von selbst nachgelesen",
      "build_categories" not in _zweig and "scan_games" not in _zweig,
      "das dauert bei einer grossen Sammlung Minuten und ist eine "
      "Entscheidung des Nutzers")
check("gesetzt wird derselbe Grund wie beim Speicher-Waechter",
      "_nachscan_grund" in _zweig,
      "der Menuepunkt aus Build 251 erledigt den Rest - es gibt also "
      "keinen zweiten Weg zum Nachlesen")
check("und die Quelle wird vermerkt", "_nachscan_rom = True" in _zweig,
      "sonst macht medium_art() aus 'SNES' ein 'unbekanntes Medium'")

check("es gibt weiterhin genau EINEN Nachlese-Zweig",
      _FE.count('elif kind == "nachscan":') == 1)

# ---------------------------------------------------------------------------
print()
print("Test 5: der beobachtete Ordner kommt aus einem Eintrag")
# ---------------------------------------------------------------------------
_b = _FE[_FE.index("    def _beobachtete_ordner(self):"):]
_b = _b[:_b.index("\n    def ", 10)]
_b_code = "\n".join(z for z in _b.split("\n")
                    if not z.strip().startswith("#"))
check("nur auf der Spieleseite", "self.page != 1" in _b_code)
check("und nur bei einer echten Systemkategorie",
      "self.cats[self.cat_i][2]" in _b_code,
      "'Favoriten' mischt Systeme - der Ordner des ersten Eintrags "
      "waere dort ein zufaelliger")
check("der Pfad kommt aus einem Eintrag, nicht aus dem Knoten",
      "os.path.dirname(" in _b_code,
      "die Baumknoten tragen ihren Pfad nicht mit sich")
check("ein Fehler darf die Anzeige nicht kosten",
      "except Exception" in _b_code and "return ()" in _b_code)

# ---------------------------------------------------------------------------
print()
print("Test 6: der Schalter")
# ---------------------------------------------------------------------------
import fe.settings as S                                    # noqa: E402
import fe.translations as TR                               # noqa: E402

check("es gibt ihn", hasattr(S, "toggle_romwacht"))
check("und er ist von Haus aus AN", S.romwacht_an() is True)
for sch in ("rom_geaendert", "sys_romwacht_an", "sys_romwacht_aus",
            "sys_nachscan_rom"):
    e = TR.TRANSLATIONS.get(sch)
    check("Text '%s' gibt es in beiden Sprachen" % sch,
          bool(e and e.get("de") and e.get("en")), str(e))

from fe.menu import system_items                           # noqa: E402


def _finden(node, kind, pfad=""):
    for it in node.get("items", []):
        if it[1] == kind:
            return it[0], pfad
    for name, sub in node.get("folders", {}).items():
        tr = _finden(sub, kind, pfad + "/" + name)
        if tr:
            return tr
    return None


check("es gibt einen Menuepunkt", _finden(system_items(), "romwacht")
      is not None)
# Und der Nachlese-Punkt nennt bei einem ROM-Grund KEIN Medium.
_mit = _finden(system_items(nachscan_grund="SNES", nachscan_rom=True),
               "nachscan")
check("der Nachlese-Punkt nennt bei ROMs kein Medium",
      _mit is not None and "SNES" in _mit[0]
      and TR.t("medium_unbekannt") not in _mit[0],
      str(_mit))

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
