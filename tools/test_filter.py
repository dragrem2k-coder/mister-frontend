#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft den Listenfilter (Build 142).

Nutzerwunsch, aus dem Vergleich mit einem anderen Frontend: nach
Genre, Jahr, Spielerzahl und Entwickler filtern koennen.

WARUM DAS BEI UNS NICHTS KOSTET: die vier Angaben stehen seit Build
115 ohnehin im Speicher (gameinfo.tsv der Artwork-Datenbank ueber
get_meta()). Der Filter ist deshalb eine Abfrage, kein neuer
Datenpfad - kein Kartenzugriff, kein Dekodieren.

Nachgemessen an der SNES-Tabelle des Nutzers: Jahr 99,2 %, Genre
98,3 %, Entwickler 99,7 %, Spieler 99,8 % belegt.

Geprueft wird:
  1. die drei Umrechnungen, die die Rohdaten NICHT hergeben
     (zusammengesetztes Genre, Spieler-Bereiche, Jahr mit Zusatz),
  2. das Filtern selbst, inklusive der Regel "Ordner bleiben drin",
  3. dass der Filter den Knoten-Cache des Baums nicht vergiftet,
  4. dass die Werte aus dem VOLLEN Bestand kommen, nicht aus dem
     schon gefilterten,
  5. Tasten, Texte und Verdrahtung.

Ausfuehren:
    python3 tools/test_filter.py
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)

import _harness as H                                    # noqa: E402

sys.path.insert(0, os.path.join(_REPO, "frontend"))
import fe.filter as F                                   # noqa: E402
import fe.translations as T                             # noqa: E402

t = T.t
fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


print("Test 1: Genre - aus 160 Werten werden bedienbare")
# So sieht es in der echten Datenbank aus.
check("zusammengesetzt wird auf die Gattung gekuerzt",
      F.genre_kurz("Action / Adventure/Action") == "Action")
check("auch bei drei Ebenen",
      F.genre_kurz("Adults/Mahjong/Asiatic board game")
      == "Asiatic board game")
check("einfache bleiben, wie sie sind",
      F.genre_kurz("Platform") == "Platform")
check("leer bleibt leer",
      F.genre_kurz("") == "" and F.genre_kurz(None) == "")

print()
print("Test 2: Spieler sind Bereiche, keine Zahlen")
for roh, erwartet in (("1", 1), ("2", 2), ("1-2", 2), ("1-4", 4),
                      ("1-10", 10), ("", 0), (None, 0), ("?", 0)):
    check("%-6r -> %d" % (roh, erwartet), F.spieler_max(roh) == erwartet)

print()
print("Test 3: Jahr")
for roh, erwartet in (("1994", 1994), ("1994 (Japan)", 1994),
                      ("", 0), ("?", 0), ("19", 0)):
    check("%-14r -> %d" % (roh, erwartet), F.jahr_zahl(roh) == erwartet)

print()
print("Test 4: die Jahres-Kette hat Einzeljahre UND Spannen")
kette = F.jahr_kette([1990, 1991, 1992, 1994, 1996, 1999])
check("neuestes Jahr steht vorn", kette[0] == 1999)
check("Spannen kommen danach",
      (1990, 1994) in kette and (1995, 1999) in kette)
check("eine leere Spanne entsteht gar nicht erst",
      all(not isinstance(k, tuple) or any(k[0] <= j <= k[1]
                                          for j in (1990, 1991, 1992,
                                                    1994, 1996, 1999))
          for k in kette))
check("ohne Jahre bleibt sie leer", F.jahr_kette([]) == [])

print()
print("Test 5: filtern")
META = {
    "Mario":  {"genre": "Action / Jump/Platform", "year": "1990",
               "players": "1", "developer": "Nintendo"},
    "Zelda":  {"genre": "Action/Adventure", "year": "1991",
               "players": "1", "developer": "Nintendo"},
    "Kart":   {"genre": "Racing, Driving", "year": "1992",
               "players": "1-2", "developer": "Nintendo"},
    "Bomber": {"genre": "Action/Platform", "year": "1994",
               "players": "1-4", "developer": "Hudson"},
    "Ohne":   {},
}
ITEMS = [("Unterordner/", "folder", "Unterordner")] + \
        [(n, "game", None) for n in META]


def meta(n):
    return META.get(n, {})


def namen(liste):
    return [e[0] for e in liste if e[1] == "game"]


check("ohne Filter bleibt alles",
      F.anwenden(ITEMS, meta, {}) is ITEMS)
check("Genre",
      namen(F.anwenden(ITEMS, meta, {"genre": "Platform"}))
      == ["Mario", "Bomber"])
check("Entwickler",
      namen(F.anwenden(ITEMS, meta, {"developer": "x"}))
      == namen(ITEMS) and
      namen(F.anwenden(ITEMS, meta, {"entwickler": "Hudson"}))
      == ["Bomber"])
check("Spieler heisst MINDESTENS",
      namen(F.anwenden(ITEMS, meta, {"spieler": 2}))
      == ["Kart", "Bomber"])
check("Jahr einzeln",
      namen(F.anwenden(ITEMS, meta, {"jahr": 1991})) == ["Zelda"])
check("Jahr als Spanne",
      namen(F.anwenden(ITEMS, meta, {"jahr": (1990, 1992)}))
      == ["Mario", "Zelda", "Kart"])
check("mehrere Felder wirken zusammen",
      namen(F.anwenden(ITEMS, meta,
                       {"entwickler": "Nintendo", "spieler": 2}))
      == ["Kart"])
check("ein Spiel ohne Angabe faellt heraus",
      "Ohne" not in namen(F.anwenden(ITEMS, meta, {"jahr": 1990})))

print()
print("Test 6: Ordner bleiben IMMER drin")
# Ein Filter, der die Navigation wegfiltert, sperrt einen im
# Unterordner ein.
gefiltert = F.anwenden(ITEMS, meta, {"genre": "Platform"})
check("der Ordner ist noch da",
      any(e[1] == "folder" for e in gefiltert))

print()
print("Test 7: nur Werte anbieten, die auch vorkommen")
werte = F.werte_sammeln(ITEMS, meta)
check("Genres", werte["genre"] == ["Adventure", "Platform",
                                   "Racing, Driving"],
      "%r" % werte["genre"])
check("Jahre neueste zuerst", werte["jahr"] == [1994, 1992, 1991, 1990])
check("Spielerzahlen", werte["spieler"] == [1, 2, 4])
check("Entwickler", werte["entwickler"] == ["Hudson", "Nintendo"])

print()
print("Test 8: Blaettern - 'alle' ist immer erreichbar")
kette = ["A", "B", "C"]
check("von alle nach vorn", F.naechster_wert(kette, None, 1) == "A")
check("und weiter", F.naechster_wert(kette, "A", 1) == "B")
check("am Ende wieder auf alle",
      F.naechster_wert(kette, "C", 1) is None)
check("rueckwaerts von alle ans Ende",
      F.naechster_wert(kette, None, -1) == "C")
check("ein unbekannter Wert landet bei alle",
      F.naechster_wert(kette, "gibt es nicht", 1) == "A")

print()
print("Test 9: Beschriftung fuer die Kopfzeile")
check("leer, wenn nichts gesetzt ist",
      F.beschriftung({}, t) == "" and F.beschriftung({"genre": None}, t) == "")
check("aktiv ist aktiv",
      F.aktiv({"genre": "Platform"}) and not F.aktiv({"genre": None})
      and not F.aktiv({}))
T.CURRENT_LANG = "de"
check("Spielerzahl wird als 'ab N' geschrieben",
      F.wert_text("spieler", 2, t) == "ab 2", F.wert_text("spieler", 2, t))
check("Spanne mit Bindestrich",
      F.wert_text("jahr", (1992, 1995), t) == "1992-1995")

print()
print("Test 10: der Filter vergiftet den Knoten-Cache nicht")
# _display_items() cacht AM KNOTEN - der Baum ueberlebt
# Kategoriewechsel. Schriebe der Filter dort hinein, waere die
# Kategorie dauerhaft beschnitten, auch nach dem Zuruecksetzen.
H.set_screen(1920, 1080)
f = H.make_frontend(page=1)
voll = len(f._display_items())
f._filter = {"jahr": 1234}          # trifft garantiert nichts
f._filter_cache = None
leer = len([e for e in f._display_items() if e[1] == "game"])
check("mit unmoeglichem Filter bleibt kein Spiel", leer == 0, "%d" % leer)
f._filter = {}
f._filter_cache = None
check("ohne Filter ist alles wieder da",
      len(f._display_items()) == voll,
      "%d von %d" % (len(f._display_items()), voll))
knoten = f._current_node()
check("im Knoten liegt die UNGEFILTERTE Liste",
      len(knoten["_display_items_cache"]) == voll)

print()
print("Test 11: die Werte kommen aus dem vollen Bestand")
# Sonst schrumpft die Auswahl mit jedem gesetzten Filter und man
# kommt nie wieder heraus.
f._filter = {"jahr": 1234}
f._filter_cache = None
check("_display_items_ungefiltert() liefert alles",
      len(f._display_items_ungefiltert()) == voll)
check("und _display_items() daneben weiterhin gefiltert",
      len([e for e in f._display_items() if e[1] == "game"]) == 0)
f._filter = {}
f._filter_cache = None

print()
print("Test 12: Tasten, Texte, Verdrahtung")
import fe.input as I                                    # noqa: E402
check("Tab oeffnet den Filter", I.KEYMAP.get(I.KEY_TAB) == "filter")
check("Select + L2/R2 ebenfalls",
      I.SELECT_COMBOS.get("favorite") == "filter")
quelle = open(H.FRONTEND_PY, encoding="utf-8").read()
check("das Frontend behandelt die Aktion",
      'elif act == "filter":' in quelle)
check("und nur auf Seite 1",
      'elif act == "filter":' in quelle
      and "if self.page == 1:\n                        self.filter_bildschirm()"
      in quelle)
for key in ("filter_titel", "filter_genre", "filter_jahr", "filter_spieler",
            "filter_entwickler", "filter_alle", "filter_treffer",
            "filter_hinweis", "filter_keine_daten"):
    eintrag = T.TRANSLATIONS.get(key)
    check("Text %-22s in beiden Sprachen" % key,
          bool(eintrag) and "de" in eintrag and "en" in eintrag)

print()
print("Test 13: Filter als Kategorie merken (Build 143)")
import tempfile                                          # noqa: E402
F.KATEGORIEN_DATEI = os.path.join(tempfile.mkdtemp(prefix="dragend_filt_"),
                                  "filter_kategorien.json")
check("am Anfang ist nichts gemerkt", F.gemerkte_laden() == [])
name = F.merken("SNES", {"genre": "Platform", "jahr": (1990, 1994)}, t)
check("der Name entsteht aus der Bedingung",
      name == "SNES / Platform / 1990-1994", str(name))
check("und steht danach in der Datei",
      [e["name"] for e in F.gemerkte_laden()] == [name])
check("ist_gemerkt() findet ihn", F.ist_gemerkt(name))
check("zweimal dasselbe merken geht nicht",
      F.merken("SNES", {"genre": "Platform", "jahr": (1990, 1994)}, t)
      is None)
check("ohne Bedingung gibt es nichts zu merken",
      F.merken("SNES", {}, t) is None)

# Der Stolperstein: JSON kennt keine Tupel. Eine Jahres-Spanne kaeme
# als Liste zurueck, und passt() vergliche danach gegen etwas anderes
# als beim Speichern - der Filter traefe stillschweigend nichts mehr.
geladen = F.gemerkte_laden()[0]["filter"]
check("die Jahres-Spanne ist nach dem Laden wieder ein Tupel",
      isinstance(geladen.get("jahr"), tuple), repr(geladen.get("jahr")))
check("und sie filtert auch wirklich noch",
      namen(F.anwenden(ITEMS, meta, geladen)) == ["Mario", "Bomber"],
      "%r" % namen(F.anwenden(ITEMS, meta, geladen)))

check("vergessen entfernt ihn", F.vergessen(name)
      and not F.ist_gemerkt(name))
check("etwas Unbekanntes zu vergessen ist kein Fehler",
      F.vergessen("gibt es nicht") is False)

# Eine kaputte Datei darf den Start nicht umwerfen.
with open(F.KATEGORIEN_DATEI, "w", encoding="utf-8") as fh:
    fh.write("{kaputt")
check("eine kaputte Datei liefert eine leere Liste",
      F.gemerkte_laden() == [])

print()
print("Test 14: die Kategorie wird auch gebaut")
check("das Frontend kennt den Bauweg",
      "def _gemerkte_kategorie(self, eintrag):" in quelle)
# GEAENDERT (Build 164): hier stand die woertliche Zeile
# "for _eintrag in FILTER.gemerkte_laden():". Der Test wurde rot, als
# die Schleife einen Messpunkt bekam und der Aufruf in eine eigene
# Variable wanderte - obwohl sich am Verhalten nichts geaendert hat.
# Ein Test, der an einer Formulierung haengt statt an dem, was sie
# bewirkt, meldet Umbauten als Fehler und echte Fehler gar nicht.
_bau = quelle.split("def build_categories")[1].split("\n    def ")[0]
check("und haengt sie beim Kategorienbau an",
      "FILTER.gemerkte_laden()" in _bau
      and "self._gemerkte_kategorie(" in _bau
      and "self.cats.append(" in _bau)
check("die Kategorie wird ueber ihren NAMEN wiedergefunden",
      "def _syskey_fuer_kat(self, kat_name):" in quelle
      and "merkname = self.cats[self.cat_i][0]" in quelle)
for key in ("filter_merken", "filter_vergessen", "filter_gemerkt"):
    eintrag = T.TRANSLATIONS.get(key)
    check("Text %-18s in beiden Sprachen" % key,
          bool(eintrag) and "de" in eintrag and "en" in eintrag)

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Tests bestanden.")
