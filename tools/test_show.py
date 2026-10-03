#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""--show: der Bericht statt des Messgeraets (Build 231).

WUNSCH DES NUTZERS: "kann man ein zweites benchmark machen was die
funktionen einstellmoeglichkeiten design und so zeigt auch wie schnell
das scrollen mittlerweile ist? als vorfuehrung quasi?"

DIE EINE GEFAHR, UM DIE HERUM DIESER TEST GEBAUT IST: eine von Hand
gepflegte Funktionsliste. So eine Liste ist nach drei Builds falsch,
und zwar still - sie behauptet dann Dinge ueber ein Frontend, das
anders aussieht. Deshalb darf in fe/show.py keine stehen; alles muss
aus dem gelesen werden, was das Frontend ohnehin weiss. Test 2 sieht
genau danach.

DIE ZWEITE GEFAHR ist dieselbe wie bei Abschnitt J des Bench: zwei
Fassungen desselben Scrollschritts. Genau daran ist J in Build 218
gescheitert (gemessen wurde der volle Neuaufbau statt des leichten
Pfads, 132,87 ms statt des echten Schritts). --show misst deshalb mit
DERSELBEN Funktion - Test 3 prueft, dass es wirklich dieselbe ist.

Ausfuehren:
    python3 tools/test_show.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H          # noqa: E402

import fe.show as SHOW        # noqa: E402
import fe.bench as BENCH      # noqa: E402
import fe.menu as MENU        # noqa: E402
import fe.masken as MASKEN    # noqa: E402
import fe.schriften as SCHRIFTEN  # noqa: E402
import fe.settings as S       # noqa: E402

fails = []
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def check(name, ok, info=""):
    print(("  OK   " if ok else "  FEHL ") + name
          + (("  " + str(info)) if info else ""))
    if not ok:
        fails.append(name)


# ---------------------------------------------------------------------------
print("Test 1: der Bericht laeuft durch - ohne Framebuffer, ohne Absturz")
# ---------------------------------------------------------------------------
# Auf dem Pruefstand gibt es weder Bildspeicher noch Spiele. Genau das
# ist der Fall, in dem so ein Bericht gern mit einer Ausnahme endet -
# und ein Bericht, der abstuerzt, ist schlimmer als keiner.
class LeeresFrontend(object):
    fb = None
    cats = []
    page = 0
    cat_i = 0
    item_i = 0


class EchtesFrontend(LeeresFrontend):
    """Mit Kategorien, wie sie wirklich aussehen.

    DAS IST DIE LEHRE AUS BUILD 231. Dort stand in _abschnitt_bestand()
    "for name, node in kats" - ein Kategorieeintrag hat aber DREI
    Felder (Name, Baum, Systemkey). Auf dem Pruefstand war die Liste
    LEER, also lief die Schleife nie, und der Test meldete gruen. Beim
    Nutzer stuerzte --show in der zweiten Ueberschrift ab:

        ValueError: too many values to unpack (expected 2)

    Ein Test mit einer leeren Liste prueft die Schleife nicht. Seitdem
    steht hier eine, die der echten gleicht."""
    cats = [
        ("Arcade", {"items": [1] * 1041, "folders": {}}, None),
        ("SNES", {"items": [1] * 900,
                  "folders": {"Hacks": {"items": [1] * 20,
                                        "folders": {}}}}, "snes"),
        ("Leer", {"items": [], "folders": {}}, None),
    ]


zeilen = []
_echt_print = __builtins__["print"] if isinstance(__builtins__, dict) \
    else __builtins__.print


def _still(*a, **k):
    pass


import builtins                                          # noqa: E402
builtins.print = _still
try:
    text = SHOW.lauf(LeeresFrontend(), None, __import__("fe.art",
                                                        fromlist=["x"]),
                     S, MENU, MASKEN, SCHRIFTEN, BENCH, startdauer=1.5)
finally:
    builtins.print = _echt_print

check("er liefert Text zurueck", bool(text) and len(text) > 500,
      "%d Zeichen" % len(text))
check("und endet sauber", text.rstrip().endswith("="))
for ueberschrift in ("DEINE SAMMLUNG", "WIE ES AUSSEHEN KANN",
                     "WAS SICH EINSTELLEN LAESST", "WIE SCHNELL ES SCROLLT",
                     "WO WAS LIEGT"):
    check("Abschnitt '%s' ist da" % ueberschrift, ueberschrift in text)
check("ohne Framebuffer wird das Tempo uebersprungen, nicht gerechnet",
      "kein Framebuffer" in text,
      "ein Bericht, der abstuerzt, ist schlimmer als keiner")
check("die Startdauer steht drin", "1.5 s" in text, )
# DER ABSTURZ AUS BUILD 231 - mit Kategorien, wie sie wirklich sind.
builtins.print = _still
try:
    text2 = SHOW.lauf(EchtesFrontend(), None,
                      __import__("fe.art", fromlist=["x"]),
                      S, MENU, MASKEN, SCHRIFTEN, BENCH)
finally:
    builtins.print = _echt_print
check("mit ECHTEN Kategorien laeuft er auch durch", len(text2) > 500,
      "ein Eintrag hat DREI Felder, nicht zwei")
check("und zaehlt sie richtig", "1.961" in text2 or "1961" in text2,
      "1041 + 900 + 20 = 1961")
check("eine leere Kategorie wird nicht aufgezaehlt",
      "Leer" not in text2.split("WIE ES AUSSEHEN")[0],
      "sie steht in keiner Liste, die jemand liest")
check("und die Zahl der Kategorien zaehlt nur die vollen",
      "in 2 Kategorien" in text2, text2.splitlines()[14:16])

check("keine Zeile ist unangenehm lang",
      max(len(z) for z in text.splitlines()) <= 110,
      "max %d - das soll man vorlesen koennen"
      % max(len(z) for z in text.splitlines()))

# ---------------------------------------------------------------------------
print()
print("Test 2: KEINE von Hand gepflegte Funktionsliste")
# ---------------------------------------------------------------------------
# Das ist der eigentliche Inhalt dieses Tests. Eine Liste, die jemand
# per Hand fuehrt, ist nach drei Builds falsch - und sie behauptet dann
# Dinge ueber ein Frontend, das anders aussieht.
quelle = open(os.path.join(_REPO, "frontend", "fe", "show.py"),
              encoding="utf-8").read()
check("die Einstellungen kommen aus dem Systemmenue",
      "MENU.system_items()" in quelle,
      "also genau die Liste, die der Nutzer sieht")
check("die Ansichten aus den Einstellungen", "S.ANSICHTEN" in quelle)
check("die Farbschemata aus dem Menuemodul", "THEME_NAMES_DE" in quelle)
check("die Masken werden GEZAEHLT, nicht aufgezaehlt",
      "MASKEN.BAUM.zaehlen(" in quelle)
check("die Schriften ebenso", "SCHRIFTEN.BAUM.zaehlen(" in quelle)
check("der Bestand kommt aus dem laufenden Frontend",
      'getattr(fe, "cats"' in quelle)

# Die Probe aufs Exempel: der Bericht muss Eintraege nennen, die es im
# echten Systemmenue auch gibt.
baum = MENU.system_items()
namen = []


def _sammeln(knoten, tiefe=0):
    if tiefe > 4 or not isinstance(knoten, dict):
        return
    for _n, unter in (knoten.get("folders", {}) or {}).items():
        _sammeln(unter, tiefe + 1)
    for e in (knoten.get("items", ()) or ()):
        namen.append(str(e[0]).split(" -> ")[0])


_sammeln(baum)
check("das Systemmenue hat ueberhaupt Eintraege", len(namen) > 20,
      "%d" % len(namen))
fehlend = [n for n in namen[:25] if n[:30] not in text]
check("und sie stehen im Bericht", not fehlend,
      "%r fehlt" % (fehlend[:2],))

# ---------------------------------------------------------------------------
print()
print("Test 3: DERSELBE Scrollschritt wie im Bench")
# ---------------------------------------------------------------------------
# Zwei Fassungen desselben Schritts waeren zwei Gelegenheiten
# auseinanderzulaufen. Genau daran ist Abschnitt J in Build 218
# gescheitert: gemessen wurde der volle Neuaufbau statt des leichten
# Pfads - 132,87 ms statt des echten Schritts.
check("der Schritt steht EINMAL da", hasattr(BENCH, "schritt_funktion"))
check("und die Fensterspanne auch", hasattr(BENCH, "fenster_spanne"))
check("--show benutzt beide",
      "BENCH.schritt_funktion(fe, seite)" in quelle
      and "BENCH.fenster_spanne(fe, seite)" in quelle)
qb = open(os.path.join(_REPO, "frontend", "fe", "bench.py"),
          encoding="utf-8").read()
_j = qb.split("def _abschnitt_j")[1]
check("und Abschnitt J ebenfalls",
      "schritt_funktion(fe, seite)" in _j
      and "fenster_spanne(fe, seite)" in _j,
      "sonst misst der Bericht etwas anderes als das Messgeraet")
check("niemand baut den Schritt noch ein zweites Mal",
      "_draw_navigate_cats" not in quelle
      and "_draw_navigate_items" not in quelle,
      "fe/show.py darf ihn nur BENUTZEN")

# Der leichte Pfad muss wirklich zuerst versucht werden - das war der
# Fehler von Build 218.
_sf = qb.split("def schritt_funktion")[1].split("\ndef ")[0]
check("erst der leichte Pfad, dann der volle Aufbau",
      _sf.index("_draw_navigate_cats") < _sf.index("fe.draw()"),
      "sonst wird der volle Neuaufbau gemessen")
check("und die Fensterspanne haelt zwei Zeilen Rand",
      "max(2, min(fenster - 2, gesamt - 1))"
      in qb.split("def fenster_spanne")[1].split("\ndef ")[0],
      "der leichte Pfad verlangt ALTE und NEUE Zeile im Fenster")

# ---------------------------------------------------------------------------
print()
print("Test 4: der Aufruf ist verdrahtet und sagt sich an")
# ---------------------------------------------------------------------------
qf = open(H.FRONTEND_PY, encoding="utf-8", errors="replace").read()
check("--show steht in der Optionsliste", '"--show":' in qf)
check("und wird auch ausgefuehrt", 'if "--show" in sys.argv:' in qf)
check("der Bericht wird zusaetzlich geschrieben",
      "SHOW_AUSGABE" in qf and "/tmp/dragend_show.txt" in qf)
_zweig = qf.split('if "--show" in sys.argv:')[1].split("\n        _fe.run()")[0]
check("danach wird beendet, nicht weitergestartet",
      "_fe._beenden()" in _zweig and "sys.exit(0)" in _zweig,
      "ein Bericht soll berichten und dann aufhoeren")

# DIE OPTIONSPRUEFUNG GANZ VORN (Build 231, Nutzermeldung zu 230: die
# Meldung kam erst hinter "Keine andere Instanz aktiv - starte
# Framebuffer/Eingaben ..."). Fuer ein blosses --help wurde also die
# Einzelinstanz-Sperre geholt und der halbe Start durchlaufen.
check("die Optionspruefung steht VOR der ersten Startmeldung",
      qf.index("_unbekannt = [a for a in sys.argv")
      < qf.index('print("Frontend-Start: initialisiere ...")'),
      "sonst holt ein --help die Einzelinstanz-Sperre")

# ---------------------------------------------------------------------------
print()
print("Test 5: der Bericht steht auch AUF DEM FERNSEHER (Build 232)")
# ---------------------------------------------------------------------------
# NUTZERMELDUNG ZU BUILD 231: "ich dachte bei show sieht man was auf
# dem bildschirm, der ist schwarz". Er hat recht - wer vor dem
# Fernseher sitzt und "zeig mal, was du kannst" meint, will es dort
# sehen und nicht in einer SSH-Sitzung.
class Schirm(object):
    """Gerade so viel Framebuffer, wie auf_schirm() anfasst."""

    def __init__(self, breite=1920, hoehe=1080):
        self.width, self.height = breite, hoehe
        self.gemalt = []
        self.bilder = 0
        self.geleert = 0

    def clear(self, farbe):
        self.geleert += 1

    def text(self, x, y, s, skala, farbe=None, *a, **k):
        self.gemalt.append((x, y, s, skala))

    def flip(self, *a, **k):
        self.bilder += 1


class Taster(object):
    """Gibt nach n Abfragen eine Taste - sonst liefe der Test sieben
    Sekunden je Seite."""

    def __init__(self, antwort="ok"):
        self.antwort = antwort
        self.gefragt = 0

    def read_action(self, timeout=None):
        self.gefragt += 1
        return self.antwort


class SchirmFrontend(EchtesFrontend):
    pass


_fe = SchirmFrontend()
_fe.fb = Schirm()
_fe.inp = Taster("ok")
ok = SHOW.auf_schirm(_fe, text2, sekunden=5.0)
check("er malt etwas", ok and _fe.fb.bilder > 0,
      "%d Seiten" % _fe.fb.bilder)
check("und zwar mehrere Seiten", _fe.fb.bilder > 1,
      "ein Bericht passt nicht auf eine Seite")
check("jede Seite wird vorher geleert",
      _fe.fb.geleert == _fe.fb.bilder,
      "%d geleert, %d Bilder - sonst steht die alte Seite darunter"
      % (_fe.fb.geleert, _fe.fb.bilder))
check("keine Zeile ragt ueber den Rand",
      all(x + len(s) * 8 * sk <= _fe.fb.width + 8 * sk
          for (x, y, s, sk) in _fe.fb.gemalt),
      "lange Zeilen werden umgebrochen, nicht abgeschnitten")
check("und keine unter den unteren Rand",
      all(y + 9 * sk <= _fe.fb.height for (x, y, s, sk) in _fe.fb.gemalt),
      "max y %d von %d"
      % (max(y for (x, y, s, sk) in _fe.fb.gemalt), _fe.fb.height))
check("die Seitenzahl steht dabei",
      any("Seite " in s for (x, y, s, sk) in _fe.fb.gemalt),
      "sonst weiss man nicht, wie lange es noch dauert")

# ZURUECK BRICHT AB - eine Vorfuehrung, die sich nicht abbrechen
# laesst, ist eine Zumutung.
_fe2 = SchirmFrontend()
_fe2.fb = Schirm()
_fe2.inp = Taster("back")
SHOW.auf_schirm(_fe2, text2, sekunden=5.0)
check("Zurueck bricht ab", _fe2.fb.bilder == 1,
      "%d Seiten - nach der ersten muss Schluss sein" % _fe2.fb.bilder)

# OHNE Bildspeicher passiert nichts, und zwar ohne Absturz.
check("ohne Bildspeicher passiert nichts",
      SHOW.auf_schirm(LeeresFrontend(), text2) is False)

# Und ein Fehler beim Zeichnen beendet die Vorfuehrung, statt das
# Frontend mitzunehmen.
class Kaputt(Schirm):
    def text(self, *a, **k):
        raise RuntimeError("kaputt")


_fe3 = SchirmFrontend()
_fe3.fb = Kaputt()
_fe3.inp = Taster("ok")
check("ein Zeichenfehler nimmt nichts mit",
      SHOW.auf_schirm(_fe3, text2, sekunden=0.1) is False,
      "der Bericht auf der Konsole steht da schon")

check("der Aufruf steht in frontend.py",
      "SHOW.auf_schirm(_fe, _text, sys.modules[__name__]" in qf)
check("und ist gegen Abstuerze gesichert",
      "--show auf dem Schirm" in qf,
      "eine Vorfuehrung darf das Frontend nicht mitnehmen")

print()
if fails:
    print("FEHLGESCHLAGEN (%d):" % len(fails))
    for f in fails:
        print("  - %s" % f)
    sys.exit(1)
print("Alles in Ordnung.")
