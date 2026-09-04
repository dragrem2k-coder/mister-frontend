#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft, dass jedes Spiele-System, das das Frontend anzeigt, auch von
den Download-Werkzeugen fuer Boxart und Spiele-Infos bedient wird.

AUSLOESER (Nutzerfrage, Build 78): "wir haben ja den Virtual Boy mit
reingenommen - muss ich das Skript Frontend_Boxart_Download.sh nochmal
starten, damit ich die dafuer bekomme?"

Die ehrliche Antwort war: nein, das haette nichts gebracht. Virtual Boy
stand in keinem der drei Werkzeuge in der Systemtabelle. Die Kategorie
kam mit einem frueheren Build dazu, die Tabellen wurden dabei
uebersehen - drei getrennte Listen, die niemand miteinander verglichen
hat.

DAS TUECKISCHE DARAN, und der Grund fuer diesen Test: es gibt keine
Fehlermeldung. Das Skript laeuft durch, klappert die ihm bekannten
Systeme ab, meldet Erfolg - und laesst das fehlende einfach aus. Der
Nutzer sieht nur, dass keine Cover kommen, und sucht den Fehler
zwangslaeufig woanders (kaputte ROM-Namen, Netzwerk, Rechte).

Ausfuehren:
    python3 tools/test_system_abdeckung.py
"""
import ast
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
_FRONTEND_DIR = os.path.dirname(
    os.environ.get("FRONTEND_PY",
                   os.path.join(_REPO, "frontend", "frontend.py")))
sys.path.insert(0, _FRONTEND_DIR)

import fe.systems as SYS                              # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


# Systeme, die BEWUSST in keinem Download-Werkzeug stehen - mit dem
# Grund, warum das richtig ist. Wer hier etwas eintraegt, sollte einen
# echten Grund haben; die Liste ist kurz zu halten.
OHNE_DATENBANK = {
    "SMW_HACKS": "ROM-Hacks von Fans - es gibt dafuer keine offizielle "
                 "Boxart-/Metadatenbank, die Cover legt man selbst ab",
    "SNES_ALTTP_TRACKER": "kein Spielesystem, sondern eine Tracker-"
                          "Ansicht - dort gibt es nichts herunterzuladen",
}

WERKZEUGE = [
    ("frontend/mister_boxart.py", "Boxart-Download auf dem MiSTer"),
    ("frontend/mister_gameinfo.py", "Spiele-Infos auf dem MiSTer"),
    ("PC-Tools/boxart_fetch.py", "Boxart-Download am PC"),
]


def systemtabelle(pfad):
    """Die SYSTEMS-Tabelle einer Werkzeug-Datei als echtes dict.

    Bewusst ueber den Syntaxbaum (ast) statt per Textsuche: die drei
    Werkzeuge schreiben ihre Tabellen unterschiedlich (einmal
    {Endung: Datenbankname}, zweimal {Endungen} + Name), und ein
    Muster, das auf alle passt, waere genau die Sorte Halbwissen, die
    hier gerade zum Fehler gefuehrt hat. Ausgefuehrt wird nichts -
    literal_eval nimmt nur Literale."""
    quelle = open(os.path.join(_REPO, pfad), encoding="utf-8").read()
    baum = ast.parse(quelle)
    for knoten in baum.body:
        if not isinstance(knoten, ast.Assign):
            continue
        for ziel in knoten.targets:
            if isinstance(ziel, ast.Name) and ziel.id == "SYSTEMS":
                return ast.literal_eval(knoten.value)
    raise AssertionError("keine SYSTEMS-Tabelle in %s gefunden" % pfad)


frontend_systeme = [(e[0], e[1]) for e in
                    (list(SYS.GAME_SYSTEMS)
                     + list(getattr(SYS, "OPTIONAL_GAME_SYSTEMS", [])))]

print("Test 1: jedes Spiele-System ist in allen Werkzeugen bekannt")
print("        (Frontend kennt %d Systeme)" % len(frontend_systeme))
for pfad, was in WERKZEUGE:
    keys = set(systemtabelle(pfad))
    fehlend = [(name, key) for name, key in frontend_systeme
               if key not in keys and key not in OHNE_DATENBANK]
    check("%s kennt alle" % was, not fehlend,
          "fehlt: %s" % ", ".join("%s (%s)" % (n, k) for n, k in fehlend)
          if fehlend else "")

print()
print("Test 1b: der gemeldete Fall selbst - Virtual Boy")
for pfad, was in WERKZEUGE:
    check("%s kennt VIRTUALBOY" % was,
          "VIRTUALBOY" in systemtabelle(pfad))

print()
print("Test 2: die Ausnahmen sind wirklich Ausnahmen")
# Verhindert, dass die Ausnahmeliste zur Muellhalde wird: was hier
# steht, muss es im Frontend ueberhaupt geben.
frontend_keys = {key for _n, key in frontend_systeme}
for key in OHNE_DATENBANK:
    check("%s gibt es im Frontend" % key, key in frontend_keys)

print()
print("Test 3: Ordnername und Dateiendung stimmen zwischen Frontend "
      "und Werkzeugen ueberein")
# Zweite Falle derselben Art: das System steht zwar in der Tabelle, aber
# mit einem anderen ROM-Ordner oder einer anderen Endung - dann findet
# das Werkzeug schlicht keine Dateien und meldet trotzdem Erfolg.
for pfad, was in WERKZEUGE:
    tabelle = systemtabelle(pfad)
    for eintrag in (list(SYS.GAME_SYSTEMS)
                    + list(getattr(SYS, "OPTIONAL_GAME_SYSTEMS", []))):
        name, key, ordner, _corepfad, endungen = eintrag[:5]
        if key in OHNE_DATENBANK or key not in tabelle:
            continue
        wert = tabelle[key]
        werkzeug_ordner = set(wert[0])
        # Endungen stehen je nach Werkzeug an Stelle 1 als dict
        # {Endung: Datenbankname} oder als Menge {Endung, ...}.
        werkzeug_ext = set(wert[1])
        check("%s / %s: ROM-Ordner passt" % (was, name),
              set(ordner) <= werkzeug_ordner,
              "Frontend %s, Werkzeug %s" % (sorted(ordner),
                                            sorted(werkzeug_ordner)))
        check("%s / %s: Endungen passen" % (was, name),
              set(endungen) <= werkzeug_ext,
              "Frontend %s, Werkzeug %s" % (sorted(endungen),
                                            sorted(werkzeug_ext)))

print()
print("Test 4: alle Werkzeuge nutzen denselben Datenbanknamen")
# Alle drei fragen dieselbe libretro-Datenbank ab. Weicht ein Name
# zwischen ihnen ab, laedt eines der drei nichts - wieder lautlos.
def datenbanknamen(pfad):
    raus = {}
    for key, wert in systemtabelle(pfad).items():
        if isinstance(wert[1], dict):          # {Endung: Datenbankname}
            raus[key] = set(wert[1].values())
        elif len(wert) > 2:                    # {Endungen}, Datenbankname
            raus[key] = {wert[2]}
    return raus


ref = datenbanknamen("frontend/mister_boxart.py")
for pfad, was in WERKZEUGE[1:]:
    for key, namen in datenbanknamen(pfad).items():
        if key in ref:
            check("%s: %s nutzt denselben Datenbanknamen" % (was, key),
                  namen <= ref[key],
                  "%s vs %s" % (sorted(namen), sorted(ref[key])))

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for f in fails:
        print("   ", f)
    sys.exit(1)
print("Alle Tests bestanden.")
