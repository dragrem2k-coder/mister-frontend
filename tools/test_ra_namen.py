#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Der RA-Namensabgleich muss nach der Beschleunigung BITGENAU dasselbe
liefern wie vorher (Build 160).

WARUM DAS GEPRUEFT WERDEN MUSS

_ra_normalize_name() entscheidet, ob ein Spiel unserer Sammlung einem
RA-Eintrag zugeordnet wird. Weicht die neue Fassung auch nur in einem
Zeichen ab, verschwindet fuer die betroffenen Spiele der
RA-Fortschritt - und zwar lautlos. Niemand sieht einen Fehler; es
steht nur nichts mehr da, wo vorher etwas stand. Genau die Sorte
Abweichung, die man ohne Test erst Monate spaeter bemerkt.

WAS BESCHLEUNIGT WURDE. Die Funktion lief einmal je Spiel der ganzen
Sammlung, bei jedem Bau der RA-Erfolgsjaeger-Kategorie. Auf dem Geraet
gemessen:

    START davon build_ra_hunter_category()   2229 ms (von 4970 ms)

Vier Regex-Durchlaeufe je Name. Zwei davon brauchen keine Regex
(str.translate, split/join), die beiden Klammer-Ausdruecke lassen sich
zu einem vorbereiteten Muster zusammenfassen.

Der Test haelt die ALTE Fassung als Vergleichsmass fest. Wer die neue
weiter anfasst, vergleicht automatisch gegen das urspruengliche
Verhalten - nicht gegen sich selbst.

Ausfuehren:
    python3 tools/test_ra_namen.py
"""
import os
import random
import re
import sys
import time

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
sys.path.insert(0, os.path.join(_REPO, "frontend"))

import fe.retroachievements as RA                       # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


def alte_fassung(name):
    """Die Fassung vor Build 160, woertlich. NICHT anfassen - sie ist
    hier das Vergleichsmass, nicht Code, der gepflegt werden will."""
    n = name.lower()
    n = re.sub(r"\([^)]*\)", " ", n)
    n = re.sub(r"\[[^\]]*\]", " ", n)
    n = re.sub(r"[^a-z0-9 ]", " ", n)
    n = re.sub(r"\s+", " ", n).strip()
    return n


# ---------------------------------------------------------------------------
print("Test 1: die Faelle, um die es wirklich geht")
# ---------------------------------------------------------------------------
ECHTE = [
    "Super Mario World (USA)",
    "Super Mario World (Europe) (Rev 1)",
    "The Legend of Zelda - A Link to the Past (USA) [!]",
    "Tetris (Japan) (En)",
    "007 - The World is Not Enough (U) [!]",
    "Sonic & Knuckles (World)",
    "Mega Man X3 (USA) [T+Ger1.0_Star-trans]",
    "Final Fantasy VII (USA) (Disc 1)",
    "Pokémon - Rote Edition (Germany)",
    "R-Type III - The Third Lightning (USA)",
    "Jumping Flash! (NTSC-U)",
    "Castlevania - Symphony of the Night (USA)",
    "Densetsu no Stafy (Japan)",
    "F-Zero (USA)",
    "Street Fighter II' - Special Champion Edition (USA, Europe)",
]
abw = []
for n in ECHTE:
    if RA._ra_normalize_name(n) != alte_fassung(n):
        abw.append("%r: %r statt %r"
                   % (n, RA._ra_normalize_name(n), alte_fassung(n)))
check("alle %d echten Namen gleich" % len(ECHTE), not abw, "; ".join(abw[:2]))

# ---------------------------------------------------------------------------
print()
print("Test 2: 5000 Zufallsnamen, Zeichen fuer Zeichen")
# ---------------------------------------------------------------------------
random.seed(20260919)
# WICHTIG: die Zeichenmenge muss auch ueber Latin-1 hinausgehen.
# Beim ersten Anlauf stand hier nur Latin-1 - und genau deshalb ist
# durchgerutscht, dass str.translate() Zeichen oberhalb von 255
# UNVERAENDERT stehen laesst, waehrend die alte Regex sie durch ein
# Leerzeichen ersetzt hat. "Ys \u2014 The Oath" waere damit auf einen
# anderen Schluessel gefallen und haette seinen RA-Fortschritt lautlos
# verloren.
ZEICHEN = (" abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
           "0123456789()[]-_.,!'&+~#\u00e4\u00f6\u00fc\u00c4\u00d6\u00dc\u00df"
           "\u00e9\u00e8\u00ea\u00e0\u00f1:;/\\\"*?<>|\t\n"
           "\u2014\u2013\u2605\u3042\u30c9\u4e2d\u00a0\u20ac\u2026\uff1a")
zufall = []
for _ in range(5000):
    laenge = random.randint(0, 40)
    zufall.append("".join(random.choice(ZEICHEN) for _ in range(laenge)))
abw = []
for n in zufall:
    if RA._ra_normalize_name(n) != alte_fassung(n):
        abw.append("%r: %r statt %r"
                   % (n[:30], RA._ra_normalize_name(n), alte_fassung(n)))
check("alle 5000 gleich", not abw, "; ".join(abw[:2]))

# ---------------------------------------------------------------------------
print()
print("Test 3: die Randfaelle, an denen so etwas scheitert")
# ---------------------------------------------------------------------------
RAND = [
    # Zeichen oberhalb von Latin-1 - siehe Kommentar bei ZEICHEN oben.
    "Ys \u2014 The Oath", "\u30c9\u30e9\u30b4\u30f3", "Game \u2605 Star",
    "\u00dcber\u2013Spiel", "Caf\u00e9 \u2026 Zeit", "Preis \u20ac 10",
    "", " ", "   ", "()", "[]", "(", ")", "[", "]",
    "(unvollstaendig", "abc(def", "a(b)c(d)e", "a[b]c[d]e",
    "(nur Klammern)", "[nur eckige]", "ÄÖÜ", "123", "---",
    "\t\n ", "a\tb\nc", "(a[b)c]d",
]
abw = []
for n in RAND:
    if RA._ra_normalize_name(n) != alte_fassung(n):
        abw.append("%r: %r statt %r"
                   % (n, RA._ra_normalize_name(n), alte_fassung(n)))
check("alle Randfaelle gleich", not abw, "; ".join(abw[:3]))
check("leerer Name bleibt leer", RA._ra_normalize_name("") == "")

# ---------------------------------------------------------------------------
print()
print("Test 4: der Merker liefert dasselbe wie der erste Durchlauf")
# ---------------------------------------------------------------------------
# Ein Merker, der beim zweiten Aufruf etwas anderes liefert, waere
# schlimmer als gar keiner.
probe = "Super Mario World (USA) [!]"
erst = RA._ra_normalize_name(probe)
nochmal = RA._ra_normalize_name(probe)
check("zweiter Aufruf identisch", erst == nochmal and erst == alte_fassung(probe),
      "%r / %r" % (erst, nochmal))
check("der Name steht im Merker", probe in RA._RA_NAME_CACHE)

# ---------------------------------------------------------------------------
print()
print("Test 5: es ist wirklich schneller geworden")
# ---------------------------------------------------------------------------
# Ohne diese Pruefung koennte die Beschleunigung spaeter unbemerkt
# wieder verschwinden - und der Kommentar in der Quelle behauptete
# weiterhin etwas, das nicht mehr stimmt.
namen = ["%s Spiel %d (USA) [!]" % (w, i)
         for i, w in enumerate(["Super", "Mega", "Turbo", "Ultra"] * 1250)]
RA._RA_NAME_CACHE.clear()


def messen(fn, daten):
    t = time.perf_counter()
    for x in daten:
        fn(x)
    return time.perf_counter() - t


t_alt = messen(alte_fassung, namen)
RA._RA_NAME_CACHE.clear()
t_neu = messen(RA._ra_normalize_name, namen)
check("die neue Fassung ist schneller", t_neu < t_alt,
      "alt %.0f ms / neu %.0f ms  (%.1fx)"
      % (t_alt * 1000, t_neu * 1000, t_alt / max(t_neu, 1e-9)))
# Der Merker: derselbe Durchlauf noch einmal, jetzt aus dem Merker.
t_gemerkt = messen(RA._ra_normalize_name, namen)
check("mit gefuelltem Merker noch einmal deutlich schneller",
      t_gemerkt < t_neu,
      "%.0f ms statt %.0f ms" % (t_gemerkt * 1000, t_neu * 1000))

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
