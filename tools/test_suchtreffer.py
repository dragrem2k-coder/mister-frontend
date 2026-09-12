#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft Positionsanzeige und Trefferwechsel (Build 114).

ZWEI AERGERNISSE AUS IDEEN_Bedienbarkeit, die zusammengehoeren, weil
beide dasselbe beantworten: wo bin ich gerade?

1. Die Kopfzeile nannte nur die Gesamtzahl. Bei 3500 Eintraegen sagte
   nichts, ob man bei 5 % oder 80 % steht. Jetzt steht "142/3500"
   rechts in der Fusszeile.

2. Im Suchmodus beendete JEDE Taste ausser Buchstaben die Suche
   stillschweigend - auch hoch/runter. Traf "mario" das falsche Mario,
   kam man nur weiter, indem man mehr tippte. Jetzt blaettern hoch und
   runter durch die Treffer, und der Suchbalken zaehlt sie mit.

DER TEIL, DER WIRKLICH SCHIEFGEHEN KANN, ist nicht die Anzeige,
sondern zweierlei:

- Die Trefferzaehlung muss die GANZE Liste normalisieren statt beim
  ersten Treffer aufzuhoeren. Ueber 12.605 Namen waren das 21,8 ms pro
  Tastendruck - auf der MiSTer-CPU unbenutzbar. Die Abkuerzung fuer
  reines ASCII bringt das auf 1,6 ms. Test 1 weist nach, dass sie
  wirklich dasselbe Ergebnis liefert, und zwar ueber alle 128
  ASCII-Zeichen, nicht nur ueber ein paar Beispiele.

- Der neue Sprung muss GENAU dasselbe treffen wie die alte Funktion,
  sonst verhaelt sich die Suche nach dem Umbau anders als vorher.
  Test 2 vergleicht beide ueber tausend Zufallsfaelle.

Ausfuehren:
    python3 tools/test_suchtreffer.py
"""
import os
import random
import string
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)

import _harness as H                                    # noqa: E402

fm = H.fm
sys.path.insert(0, os.path.join(_REPO, "frontend"))
import fe.search as S                                   # noqa: E402
import unicodedata                                      # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


def _alt_normalize(s):
    """Die Fassung VOR Build 114 - Massstab fuer die Abkuerzung."""
    nfkd = unicodedata.normalize("NFKD", s)
    stripped = "".join(c for c in nfkd if not unicodedata.combining(c))
    return stripped.lower()


def _alt_jump(names, cur_i, query):
    """jump_to_substring() nachgebaut, damit der Vergleich auch dann
    noch gilt, wenn die Originalfunktion irgendwann verschwindet."""
    n = len(names)
    if n == 0 or not query:
        return cur_i
    q = _alt_normalize(query)
    if q in _alt_normalize(names[cur_i]):
        return cur_i
    for step in range(1, n):
        idx = (cur_i + step) % n
        if q in _alt_normalize(names[idx]):
            return idx
    return cur_i


print("Test 1: die ASCII-Abkuerzung liefert dasselbe wie vorher")
# Erst erschoepfend ueber den ganzen Zeichenvorrat, dann ueber
# Zufallstexte - einzelne Beispiele wuerden genau die Zeichen
# uebersehen, bei denen es klemmt.
abweicher = [c for c in range(128)
             if S._normalize_for_search(chr(c)) != _alt_normalize(chr(c))]
check("alle 128 ASCII-Zeichen gleich", not abweicher,
      "abweichend: %r" % (abweicher,))

rnd = random.Random(114)
vorrat = string.printable + "äöüßÄÖÜéèêÇñÅøÆ日本語"
schlecht = None
for _ in range(3000):
    text = "".join(rnd.choice(vorrat) for _ in range(rnd.randint(0, 24)))
    if S._normalize_for_search(text) != _alt_normalize(text):
        schlecht = text
        break
check("3000 Zufallstexte, auch mit Umlauten und CJK, gleich",
      schlecht is None, repr(schlecht))
check("Akzente werden weiterhin entfernt",
      S._normalize_for_search("Pokémon") == "pokemon",
      S._normalize_for_search("Pokémon"))

print()
print("Test 2: der neue Sprung trifft dasselbe wie die alte Funktion")
namen_pool = ["Super Mario World", "Mario Kart", "Donkey Kong Country",
              "Pokémon Blaue Edition", "Zelda - A Link to the Past",
              "MARIO PAINT", "F-Zero", "mario is missing", "Tetris",
              "Super Metroid", "Chrono Trigger", "Earthbound"]
unterschiede = []
for _ in range(1000):
    namen = [rnd.choice(namen_pool) for _ in range(rnd.randint(1, 12))]
    anfrage = rnd.choice(["mario", "MARIO", "o", "zz", "", "pokemon",
                          "super", "kong", "e"])
    cur = rnd.randrange(len(namen))
    alt = _alt_jump(namen, cur, anfrage)
    treffer = S.treffer_suchen(namen, anfrage)
    neu = S.treffer_ab(treffer, cur)
    if neu < 0:
        neu = cur
    if alt != neu:
        unterschiede.append((namen, anfrage, cur, alt, neu))
check("1000 Zufallsfaelle, kein Unterschied", not unterschiede,
      "%d abweichend, z.B. %r" % (len(unterschiede),
                                  unterschiede[0] if unterschiede else None))

print()
print("Test 3: voriger/naechster Treffer, auch ueber den Rand")
namen = ["a1", "b", "a2", "c", "a3"]
treffer = S.treffer_suchen(namen, "a")
check("alle drei Treffer gefunden", treffer == [0, 2, 4], "%r" % (treffer,))
check("naechster ab 0 ist 2", S.treffer_ab(treffer, 1) == 2)
check("nach dem letzten geht es von vorn los",
      S.treffer_ab(treffer, 5) == 0, "%r" % S.treffer_ab(treffer, 5))
check("voriger vor 0 ist der letzte",
      S.treffer_davor(treffer, 0) == 4, "%r" % S.treffer_davor(treffer, 0))
check("voriger vor 4 ist 2", S.treffer_davor(treffer, 4) == 2)
check("Rang wird 1-basiert gezaehlt",
      (S.treffer_rang(treffer, 0), S.treffer_rang(treffer, 4)) == (1, 3))
check("ein Nicht-Treffer hat Rang 0", S.treffer_rang(treffer, 1) == 0)
check("ohne Treffer liefert der Sprung -1 statt zu raten",
      (S.treffer_ab([], 3), S.treffer_davor([], 3)) == (-1, -1))

print()
print("Test 4: hoch/runter beendet die Suche NICHT mehr")
quelle = open(os.path.join(_REPO, "frontend", "frontend.py"),
              encoding="utf-8", errors="replace").read()
check("hoch/runter werden im Suchmodus eigens behandelt",
      'elif act in ("up", "down") and self._such_treffer:' in quelle)
check("und der Suchbalken zeigt den Zaehler",
      'label += "  %d/%d" % (rang, anzahl)' in quelle)
check("die Trefferliste wird beim Oeffnen der Suche geleert",
      "self._such_treffer = []" in quelle)

print()
print("Test 5: die Positionsanzeige steht wirklich im Bild")
# Nicht die Zeichenkette pruefen, sondern das Bild: ein Aufbau MIT und
# einer OHNE Anzeige muessen sich in der Fusszeile unterscheiden - und
# zwar genau dort und nirgends sonst.
for w, h, name in ((320, 240, "CRT"), (1920, 1080, "HDMI")):
    H.set_screen(w, h)
    f = H.make_frontend(page=1)
    f.item_i = 3
    f.draw()
    L = f.layout_items(f.hat_artspalte(f.view["items"], f.view.get("syskey")))
    text = f._positionstext()
    check("%s: die Anzeige wird ueberhaupt gebildet" % name,
          text == "4/%d" % len(f.view["items"]), repr(text))

    feld_x, feld_w = f._positionsfeld(L["ox"], L["s"])
    check("%s: das Feld liegt im Bild" % name,
          0 < feld_x and feld_x + feld_w <= w,
          "x=%d w=%d W=%d" % (feld_x, feld_w, w))
    # Das Feld ist nach der GESAMTZAHL bemessen, nicht nach der gerade
    # angezeigten Zahl - sonst bliebe beim Wechsel von 1420 auf 999 die
    # letzte Ziffer stehen.
    check("%s: das Feld fasst die laengstmoegliche Zahl" % name,
          feld_w >= len("%d/%d" % (len(f.view["items"]),
                                   len(f.view["items"]))) * 8 * L["s"],
          "w=%d" % feld_w)

    vorher = bytes(f.fb.buf)
    f.item_i = 4
    f.draw()
    nachher = bytes(f.fb.buf)
    zeilen = set()
    for off in range(0, len(vorher), 4):
        if vorher[off:off + 4] != nachher[off:off + 4]:
            zeilen.add((off // 4) // w)
    check("%s: die Fusszeile aendert sich beim Schritt" % name,
          any(L["footer_y"] <= y < L["footer_y"] + 8 * L["s"]
              for y in zeilen),
          "geaenderte Zeilen: %d" % len(zeilen))

print()
print("Test 6: der leichte Pfad zeigt dieselbe Zahl wie der volle")
# Der eigentliche Knackpunkt. Die Zahl aendert sich bei GENAU dem
# Schritt, den der leichte Pfad bedient - stuende sie nur im vollen
# Aufbau, zeigte sie beim Durchblaettern dauerhaft etwas Veraltetes.
for w, h, name in ((320, 240, "CRT"), (1920, 1080, "HDMI")):
    H.set_screen(w, h)
    leicht = H.make_frontend(page=1)
    voll = H.make_frontend(page=1)
    voll._pulse_t0 = leicht._pulse_t0
    leicht.item_i = 3
    leicht.draw()
    schlecht = 0
    for ziel in (4, 5, 6, 5, 4):
        alt = leicht.item_i
        leicht.item_i = ziel
        if not leicht._draw_navigate_items(alt):
            leicht.draw()
        voll.item_i = ziel
        voll.draw()
        if bytes(leicht.fb.buf) != bytes(voll.fb.buf):
            schlecht += 1
    check("%s: fuenf Schritte, Bild jedesmal identisch" % name,
          schlecht == 0, "%d Schritte abweichend" % schlecht)

print()
print("Test 7: F3/F4 und Select+L/R springen an die Raender")
import fe.input as I                                    # noqa: E402
check("F3 belegt", I.KEYMAP.get(I.KEY_F3) == "list_start",
      repr(I.KEYMAP.get(I.KEY_F3)))
check("F4 belegt", I.KEYMAP.get(I.KEY_F4) == "list_end",
      repr(I.KEYMAP.get(I.KEY_F4)))
check("Select+L/R sind Kombinationen",
      (I.SELECT_COMBOS.get("left"), I.SELECT_COMBOS.get("right"))
      == ("list_start", "list_end"))
check("Select allein bleibt Zurueck", "select" not in I.SELECT_COMBOS)
check("die Aktionen werden verarbeitet",
      'elif act in ("list_start", "list_end"):' in quelle)
import fe.translations as T                             # noqa: E402
for key in ("help_nav_ends_key", "help_nav_ends_desc"):
    eintrag = T.TRANSLATIONS.get(key, {})
    check("%s in beiden Sprachen" % key,
          bool(eintrag.get("de")) and bool(eintrag.get("en")))
check("und die Hilfe fuehrt die Zeile auch auf",
      '("item", "help_nav_ends")' in quelle)

print()
print("Test 8: die Abkuerzung ist auch wirklich schneller")
# Ohne diese Messung waere Test 1 nur eine Gleichheitsaussage ueber
# zwei Funktionen, von denen eine grundlos existiert.
namen_gross = ["Game %d - Some Longer Title Here" % i for i in range(12605)]
t = time.perf_counter()
S.treffer_suchen(namen_gross, "titl")
neu_ms = (time.perf_counter() - t) * 1000
t = time.perf_counter()
[_alt_normalize(x) for x in namen_gross]
alt_ms = (time.perf_counter() - t) * 1000
check("Trefferzaehlung ueber 12.605 Namen mindestens 5x schneller",
      neu_ms * 5 < alt_ms, "neu %.1f ms, alt %.1f ms" % (neu_ms, alt_ms))

print()
if fails:
    print("FEHLGESCHLAGEN (%d):" % len(fails))
    for f_ in fails:
        print("  -", f_)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
