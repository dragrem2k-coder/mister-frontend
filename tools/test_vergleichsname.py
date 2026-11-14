#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""vergleichsname() ohne Schleife in Python - und Zeichen fuer Zeichen gleich (Build 321).

DER ANLASS: "wenn ich denn mister anmache und das frontend startet hab
ich das gefuehl als wenn die ersten 10 sekunden das joypad manchmal wie
eingefroren ist". In diesen Sekunden werden die Namensverzeichnisse der
Cover gebaut, und vergleichsname() laeuft dabei fuer JEDE Datei - bis
Build 320 als Schleife ueber jedes einzelne Zeichen.

Die neue Fassung macht dasselbe mit regulaeren Ausdruecken und
str.translate. Eine schnellere Fassung, die auch nur bei einem Namen
etwas anderes liefert, waere ein Fehler, der nie auffaellt: ein Cover
wuerde schlicht nicht mehr gefunden. Deshalb prueft dieser Test gegen
die alte Fassung (fe/art.py: vergleichsname_zeichenweise), und zwar:

  1. an echten Schreibweisen (No-Intro, GoodTools, kuratierte Sets),
  2. an verschachtelten und unvollstaendigen Klammern - genau dort ist
     die Zaehler-Regel der alten Fassung nicht offensichtlich,
  3. an 400.000 Zufallsnamen aus einem Alphabet mit Klammern, Umlauten,
     ss, Ligaturen, Kombinationszeichen und Ziffern anderer Schriften,
  4. GEGENPROBE: eine absichtlich falsche Fassung (nur EIN Durchgang
     ueber die Klammerpaare) muss an diesem Material auffallen - sonst
     bewiese "gleich" nichts.

Ausfuehren:
    python3 tools/test_vergleichsname.py
"""
import os
import random
import re
import sys
import time

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
sys.path.insert(0, os.path.join(_REPO, "frontend"))

import fe.art as A                                       # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


print(__doc__.strip().split("\n")[0])
print()

ALT = A.vergleichsname_zeichenweise
NEU = A.vergleichsname

# ---------------------------------------------------------------------------
print("Test 1: echte Schreibweisen")
# ---------------------------------------------------------------------------
ECHT = [
    "007 - The World is Not Enough (U) [!]",
    "007 - The World Is Not Enough (USA)",
    "Super Mario World (USA)",
    "Legend of Zelda, The - A Link to the Past (Europe) (En,Fr,De)",
    "Donkey Kong Country 2 - Diddy's Kong Quest (USA) (En,Fr) (Rev 1)",
    "042 Super Mario Kart (USA)",
    "Pokémon - Blaue Edition (Germany) (SGB Enhanced)",
    "Street Fighter II' Turbo - Hyper Fighting (World 920313)",
    "F-Zero",
    "Ys I & II (Japan) [T-En by DeJap v1.0]",
    "Tetris & Dr. Mario (USA) {Hack}",
    "Mega Man X² (Japan)",
    "Final Fantasy VI (Japan) (Rev 1) [T+Eng1.1_RPGOne]",
    "Grüße aus Straßburg",
    "",
    "(Nur Klammer)",
    "Ohne Ende (Europe",
    "Zu viele) Klammern] zu",
]
for n in ECHT:
    check("%-50s -> %s" % (repr(n)[:50], NEU(n)), ALT(n) == NEU(n),
          "" if ALT(n) == NEU(n) else "alt %r" % ALT(n))

# ---------------------------------------------------------------------------
print()
print("Test 2: verschachtelt, gemischt, unvollstaendig")
# ---------------------------------------------------------------------------
# Die Regel der alten Fassung: jede oeffnende Klammer zaehlt hoch, jede
# schliessende (gleich welcher Art) zaehlt runter, aber nie unter null.
# Daraus folgen Faelle, die man der neuen Fassung nicht ansieht.
SONDER = [
    "a(b[c]d)e",          # verschachtelt -> AE
    "a(b]c",              # ( mit ] geschlossen -> AC
    "a)b(c)d",            # schliessende vorn wird ignoriert -> ABD
    "a(b(c)d",            # eine bleibt offen -> A
    "a((b)c)d)e",         # danach eine ueberzaehlige -> ADE
    "a{b(c}d)e",          # ueber Kreuz -> A...?
    "]]]x[[[y",
    "x(((((y)))))z",
    "((((((",
    ")))))",
    "a(b)c(d",
    "Name (A) [B] {C} Rest",
]
for n in SONDER:
    check("%-24s alt %-8s neu %-8s" % (repr(n), ALT(n), NEU(n)),
          ALT(n) == NEU(n))

# ---------------------------------------------------------------------------
print()
print("Test 3: 400.000 Zufallsnamen")
# ---------------------------------------------------------------------------
random.seed(321)
ALPHABETE = [
    list("abcXYZ019 -_.,'!&()[]{}"),
    list("abcXYZ019 -_.,'!&ßéÆøİıﬁ²½٣()[]{}")
    + ["́", "Ⅰ", "あ", " ", "İ"],
]
abw = 0
erste = None
for alphabet in ALPHABETE:
    for _ in range(200000):
        n = "".join(random.choice(alphabet)
                    for _ in range(random.randint(0, 30)))
        if ALT(n) != NEU(n):
            abw += 1
            if erste is None:
                erste = (n, ALT(n), NEU(n))
check("keine einzige Abweichung", abw == 0,
      "%d, z.B. %r" % (abw, erste) if abw else "")

# ---------------------------------------------------------------------------
print()
print("Test 4: Gegenprobe - eine falsche Fassung faellt auf")
# ---------------------------------------------------------------------------
_PAAR = re.compile(r"[(\[{][^(\[{)\]}]*[)\]}]")


def falsch(base):
    """Nur EIN Durchgang ueber die Klammerpaare, und offene Klammern
    bleiben stehen - beides plausible Abkuerzungen."""
    s = _PAAR.sub("", base)
    return "".join(filter(str.isalnum, s)).upper()


abw_falsch = sum(1 for n in ECHT + SONDER if ALT(n) != falsch(n))
check("die falsche Fassung weicht an den Testnamen ab",
      abw_falsch >= 3, "%d Abweichungen" % abw_falsch)

# ---------------------------------------------------------------------------
print()
print("Test 5: der Betrieb ruft die neue Fassung, nicht die alte")
# ---------------------------------------------------------------------------
sys.path.insert(0, _HIER)
from _quelle import nur_code                             # noqa: E402
# nur_code: ohne Kommentare und Zeichenketten - die Kommentare nennen
# die alte Fassung ausdruecklich, und genau das soll hier nicht zaehlen.
_q = nur_code(open(os.path.join(_REPO, "frontend", "fe", "art.py"),
                   encoding="utf-8").read())
_ohne_def = _q.replace("def vergleichsname_zeichenweise(", "")
check("vergleichsname_zeichenweise wird nirgends gerufen",
      "vergleichsname_zeichenweise(" not in _ohne_def)
check("vergleichsname_gemerkt geht ueber die neue Fassung",
      "v = _VN_MERK[base] = vergleichsname(base)" in _q)
_namen = ["%03d Spiel Nummer %d (USA) [!]" % (i % 50, i)
          for i in range(2000)]
for fn in (ALT, NEU):
    fn("aufwaermen (x)")


def _zeit(fn):
    best = None
    for _ in range(3):
        t0 = time.perf_counter()
        for n in _namen:
            fn(n)
        d = time.perf_counter() - t0
        best = d if best is None else min(best, d)
    return best


_ta, _tn = _zeit(ALT), _zeit(NEU)
print("  (Entwicklungsrechner: alt %.2f us, neu %.2f us je Aufruf - was "
      "es auf dem Geraet ist, misst der Bench in Abschnitt P)"
      % (_ta / len(_namen) * 1e6, _tn / len(_namen) * 1e6))

print()
if fails:
    print("ROT: %d Pruefung(en) fehlgeschlagen:" % len(fails))
    for f_ in fails:
        print("   - " + f_)
    sys.exit(1)
print("ALLES GRUEN")
