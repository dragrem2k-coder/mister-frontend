#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_refresh_system_category() - nach JEDER Einstellungsaenderung
(Build 249).

WARUM GERADE DIESE FUNKTION. tools/diag_ungeprueft.py hat gemessen,
welche Funktionen die Suite WIRKLICH betritt - und oben auf der Liste
der ungeprueften stand:

    GEWICHT NAME                      DATEI                ZEILE
         35 _refresh_system_category  frontend/frontend.py  2799

35 Aufrufstellen im Programm, von keinem Test je betreten. Sie laeuft
nach praktisch jedem Umschalter im Systemmenue - Attract-Modus,
Musik, Theme, Feinheiten, Ziehung, Lautstaerke, Sprache. Haengt sie,
haengt jede Einstellung; baut sie die Kategorie falsch, zeigt das
Menue dauerhaft falsche Beschriftungen.

UND SIE HAT GENAU DAS SCHON EINMAL GETAN. Aus ihrem eigenen
Docstring: v1.73 suchte die Kategorie ueber syskey=None - das ist
aber nicht eindeutig ('Zuletzt gespielt', 'Favoriten' und 'Scripts'
haben alle syskey=None und stehen DAVOR). Ueberschrieben wurde
deshalb die falsche Kategorie, meist 'Zuletzt gespielt', und die
Beschriftung im Systemmenue blieb dauerhaft eingefroren.

Geprueft wird deshalb:

  1. Sie laeuft ueberhaupt durch (der Fall, der bei scan_games()
     monatelang niemandem aufgefallen ist).
  2. Sie trifft die Kategorie 'System' - und zwar DIE, nicht eine
     andere mit syskey=None.
  3. Die anderen Kategorien mit syskey=None bleiben unangetastet.
  4. Eine geaenderte Einstellung steht danach wirklich in der
     Beschriftung.
  5. Sie ruft NICHT build_categories() - das waere ein Scan aller
     Systeme fuer eine Beschriftung.
  6. Mehrfaches Aufrufen laesst die Kategorienzahl gleich.

Ausfuehren:
    python3 tools/test_systemkategorie_auffrischen.py
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H                                        # noqa: E402

fm = H.fm
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


def _system_index(fe):
    for i, (name, _node, sk) in enumerate(fe.cats):
        if sk is None and name == "System":
            return i
    return None


def _beschriftungen(node):
    """Alle Beschriftungen eines Kategorieknotens, flach.

    Der Knoten hat 'items' und 'folders'. Die Untermenues des
    Systemmenues liegen in 'folders' (RetroAchievements, Statistiken &
    Erfolge, Anzeige & Sound, Verhalten & Optionen, ...), und oben
    selbst stehen gar keine items.

    Der erste Entwurf dieses Tests suchte nach 'dirs' und fand
    deshalb null Beschriftungen - und meldete das als Fehler der
    Funktion, die er pruefen sollte. Ein Test, der die Struktur
    falsch annimmt, ist schlimmer als keiner: er beschuldigt den
    Richtigen."""
    raus = []
    rest = [node]
    while rest:
        n = rest.pop()
        if not isinstance(n, dict):
            continue
        for e in (n.get("items") or ()):
            if e and isinstance(e[0], str):
                raus.append(e[0])
        for u in (n.get("folders") or {}).values():
            rest.append(u)
    return raus


# ---------------------------------------------------------------------------
print("Test 1: sie laeuft ueberhaupt durch")
# ---------------------------------------------------------------------------
H.set_screen(1920, 1080)
fe = H.make_frontend(page=0)
try:
    fe._refresh_system_category()
    lief, fehler = True, ""
except Exception as e:                                       # noqa: BLE001
    lief, fehler = False, "%s: %s" % (type(e).__name__, e)
check("ein Aufruf ohne Ausnahme", lief, fehler)

idx = _system_index(fe)
check("es gibt genau eine Kategorie 'System'",
      idx is not None
      and len([1 for n, _x, sk in fe.cats if sk is None and n == "System"]) == 1,
      str(idx))

# ---------------------------------------------------------------------------
print()
print("Test 2: sie trifft 'System' und nicht eine andere mit syskey=None")
# ---------------------------------------------------------------------------
# GENAU HIER LAG DER FEHLER AUS v1.73: 'Zuletzt gespielt',
# 'Favoriten' und 'Scripts' haben ebenfalls syskey=None und stehen
# VOR 'System'.
_vorher = {}
for i, (name, node, sk) in enumerate(fe.cats):
    if sk is None:
        _vorher[i] = (name, id(node))
_andere = [i for i in _vorher if i != idx]
check("es gibt ueberhaupt andere Kategorien mit syskey=None",
      bool(_andere),
      "%d gefunden - sonst prueft der naechste Punkt nichts"
      % len(_andere))

fe._refresh_system_category()
_geaendert = [i for i in _vorher
              if id(fe.cats[i][1]) != _vorher[i][1]]
check("die Kategorie 'System' wurde ersetzt", idx in _geaendert,
      str(_geaendert))
check("und KEINE andere mit syskey=None",
      [i for i in _geaendert if i != idx] == [],
      "ersetzt wurden: %s"
      % [_vorher[i][0] for i in _geaendert if i != idx])
check("die Namen aller Kategorien stehen unveraendert",
      [n for n, _x, _s in fe.cats][:len(_vorher)]
      == [n for n, _x, _s in fe.cats][:len(_vorher)])

# ---------------------------------------------------------------------------
print()
print("Test 3: eine geaenderte Einstellung steht danach in der Beschriftung")
# ---------------------------------------------------------------------------
# Die Ziehung aus Build 246 ist dafuer der klarste Fall: ihre
# Beschriftung nennt den Wert, und der laesst sich ohne Hardware
# umstellen.
import fe.settings as SET                                   # noqa: E402
import tempfile                                             # noqa: E402

_tmp = tempfile.mkdtemp(prefix="syskat_")
_alt_datei = SET.ZIEHUNG_SPANNUNG_FILE
SET.ZIEHUNG_SPANNUNG_FILE = os.path.join(_tmp, "ziehung_spannung")
try:
    SET.save_ziehung_spannung(0)
    fe._refresh_system_category()
    _aus = _beschriftungen(fe.cats[_system_index(fe)][1])
    SET.save_ziehung_spannung(3000)
    fe._refresh_system_category()
    _an = _beschriftungen(fe.cats[_system_index(fe)][1])
finally:
    SET.ZIEHUNG_SPANNUNG_FILE = _alt_datei

_z_aus = [b for b in _aus if "Ziehung" in b]
_z_an = [b for b in _an if "Ziehung" in b]
check("die Ziehungs-Beschriftung ist ueberhaupt dabei",
      bool(_z_aus) and bool(_z_an),
      str(_z_aus[:1] + _z_an[:1]))
check("und sie aendert sich mit der Einstellung", _z_aus != _z_an,
      "%s -> %s" % (_z_aus[:1], _z_an[:1]))
check("3,0s steht danach darin",
      any("3.0s" in b or "3,0s" in b for b in _z_an), str(_z_an[:1]))

# ---------------------------------------------------------------------------
print()
print("Test 4: sie ruft NICHT build_categories()")
# ---------------------------------------------------------------------------
_gerufen = {"n": 0}
_echt = type(fe).build_categories


def _zaehl(selbst, *a, **k):
    _gerufen["n"] += 1
    return _echt(selbst, *a, **k)


type(fe).build_categories = _zaehl
try:
    fe._refresh_system_category()
finally:
    type(fe).build_categories = _echt
check("kein kompletter Neuaufbau", _gerufen["n"] == 0,
      "%d Aufrufe - das waere ein Scan aller Systeme fuer eine "
      "Beschriftung" % _gerufen["n"])

# ---------------------------------------------------------------------------
print()
print("Test 5: mehrfaches Aufrufen aendert die Struktur nicht")
# ---------------------------------------------------------------------------
_n_vorher = len(fe.cats)
_namen_vorher = [n for n, _x, _s in fe.cats]
for _ in range(5):
    fe._refresh_system_category()
check("die Zahl der Kategorien bleibt", len(fe.cats) == _n_vorher,
      "%d gegen %d" % (len(fe.cats), _n_vorher))
check("und ihre Namen auch",
      [n for n, _x, _s in fe.cats] == _namen_vorher)
check("'System' hat danach noch Einträge",
      len(_beschriftungen(fe.cats[_system_index(fe)][1])) > 10,
      "%d" % len(_beschriftungen(fe.cats[_system_index(fe)][1])))

# ---------------------------------------------------------------------------
print()
print("Test 6: der Fehler aus v1.73 ist im Quelltext festgehalten")
# ---------------------------------------------------------------------------
_q = io.open(os.path.join(_REPO, "frontend", "frontend.py"),
             encoding="utf-8").read()
_block = _q.split("def _refresh_system_category")[1].split("\n    def ")[0]
check("die Suche laeuft ueber den Namen, nicht nur ueber syskey",
      'name == "System"' in _block,
      "syskey=None ist nicht eindeutig - 'Zuletzt gespielt', "
      "'Favoriten' und 'Scripts' haben es auch")
check("und die Begruendung steht dabei",
      "NICHT eindeutig" in _block or "nicht eindeutig" in _block,
      "ein Fehler, der einmal gefunden wurde, gehoert aufgeschrieben")

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
