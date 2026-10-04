#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""--demo: drei Minuten, die alles einmal zeigen (Build 233).

WUNSCH DES NUTZERS: "eventuell sollte man auf dem bildschirm auch dort
einmal die menuepunkte kategorien ect angezeigt bekommen, am besten als
so 3 min demo die alles einmal zeigt! fehlerfrei".

"Fehlerfrei" heisst bei einer Vorfuehrung vor allem DREI Dinge, und um
die ist dieser Test gebaut:

  1. SIE MUSS SICH ABBRECHEN LASSEN. Eine Vorfuehrung, die drei Minuten
     lang keine Taste annimmt, ist eine Zumutung - und auf einem Geraet
     ohne Tastatur am Ende ein Grund zum Stromziehen.
  2. SIE DARF NICHTS HINTERLASSEN. Sie stellt Seite, Kategorie und
     Ansicht um; danach muss alles stehen wie vorher. Sonst sitzt man
     hinterher in einer fremden Ansicht und weiss nicht, warum.
  3. SIE DARF DAS FRONTEND NICHT MITNEHMEN. Keine Kategorie, keine
     Ansicht, ein Zeichenfehler - nichts davon ist ein Grund fuer einen
     Absturz. Eine Vorfuehrung ist Zubehoer.

Und viertens, aus der Lehre von Build 231/232: es wird mit einem
Frontend geprueft, das dem echten GLEICHT - mit Kategorien, die drei
Felder haben. Ein Test gegen eine leere Liste prueft die Schleife
nicht, und genau so ist --show beim Nutzer abgestuerzt.

Ausfuehren:
    python3 tools/test_demo.py
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H          # noqa: E402

import fe.demo as DEMO        # noqa: E402
import fe.bench as BENCH      # noqa: E402
import fe.settings as S       # noqa: E402

fails = []
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def check(name, ok, info=""):
    print(("  OK   " if ok else "  FEHL ") + name
          + (("  " + str(info)) if info else ""))
    if not ok:
        fails.append(name)


class Schirm(object):
    def __init__(self, breite=1920, hoehe=1080):
        self.width, self.height = breite, hoehe
        self.bilder = 0
        self.texte = []

    def clear(self, farbe):
        pass

    def text(self, x, y, s, skala, farbe=None, *a, **k):
        self.texte.append(s)

    def flip(self, *a, **k):
        self.bilder += 1


class Taster(object):
    """Antwortet erst nach `nach` Abfragen mit einer Taste.

    UND DREHT DABEI DIE UHR WEITER. Der Pruefstand friert
    time.monotonic() ein (siehe tools/_harness.py) - ohne das hier
    liefe jede Wartezeit der Vorfuehrung endlos, und dieser Test
    pruefte nur noch die Notbremse statt der Zeiteinteilung."""

    def __init__(self, nach=10**9, antwort="ok", takt=0.05):
        self.nach, self.antwort, self.takt = nach, antwort, takt
        self.n = 0

    def read_action(self, timeout=None):
        self.n += 1
        H.NOW[0] += self.takt
        return self.antwort if self.n >= self.nach else None


class Attrappe(object):
    """Gerade so viel Frontend, wie die Vorfuehrung anfasst.

    MIT KATEGORIEN, DIE DREI FELDER HABEN - die Lehre aus Build 231:
    dort hatte der Test eine leere Liste, die Schleife lief nie, und
    beim Nutzer stuerzte es sofort ab."""

    def __init__(self):
        self.fb = Schirm()
        self.inp = Taster()
        self.page = 0
        self.cat_i = 0
        self.item_i = 0
        self.nav_path = []
        self.cats_visible = 12
        self.items_visible = 17
        self.cats = [
            ("Arcade", {"items": [("A%d" % i, "game", None)
                                  for i in range(300)],
                        "folders": {}}, None),
            ("SNES", {"items": [("S%d" % i, "game", None)
                                for i in range(50)], "folders": {}}, "snes"),
            ("System", {"items": [("Option %d" % i, "x", None)
                                  for i in range(20)], "folders": {}}, None),
        ]
        self.gezeichnet = 0
        self.gesetzt = []

    # --- was die Vorfuehrung benutzt ---------------------------------
    def _display_items(self):
        return self.cats[self.cat_i][1]["items"]

    def _draw_navigate_cats(self, alt):
        self.gezeichnet += 1
        return True

    def _draw_navigate_items(self, alt):
        self.gezeichnet += 1
        return True

    def draw(self, *a, **k):
        self.gezeichnet += 1

    def ansicht_setzen(self, wert, merken=False):
        self.gesetzt.append(("liste", wert))

    def ansicht_haupt_setzen(self, wert, merken=False):
        self.gesetzt.append(("haupt", wert))


class FM(object):
    C_BG = (10, 10, 10)
    C_TITLE = (240, 240, 240)
    C_DIM = (140, 140, 140)


# ---------------------------------------------------------------------------
print("Test 1: die Vorfuehrung laeuft durch und zeigt WIRKLICH etwas")
# ---------------------------------------------------------------------------
fe = Attrappe()
ok = DEMO.lauf(fe, FM(), S, BENCH, sekunden=2.0)
check("sie laeuft durch", ok is True)
check("sie zeichnet Seiten", fe.fb.bilder > 0, "%d Bilder" % fe.fb.bilder)
check("und bewegt den Zeiger wirklich", fe.gezeichnet > 0,
      "%d Seitenaufbauten" % fe.gezeichnet)
check("jede Station bekommt eine Titelkarte",
      sum(1 for t in fe.fb.texte if t == "Dragend") >= 1)
titel = [st[1] for st in DEMO.STATIONEN]
fehlend = [t for t in titel if t not in fe.fb.texte]
check("und zwar jede", not fehlend, "%r fehlt" % (fehlend[:2],))
check("alle drei Ansichten kommen vor",
      {"liste", "raster", "galerie"} <= {w for _s, w in fe.gesetzt},
      "%r" % (sorted({w for _s, w in fe.gesetzt}),))
check("Hauptseite UND Spieleliste",
      {"haupt", "liste"} <= {s for s, _w in fe.gesetzt})
check("das Systemmenue ist dabei",
      any(st[0] == "system" for st in DEMO.STATIONEN)
      and "Systemmenue" in fe.fb.texte)

# ---------------------------------------------------------------------------
print()
print("Test 2: JEDE TASTE BRICHT AB")
# ---------------------------------------------------------------------------
# Drei Minuten ohne Ausweg waeren auf einem Geraet ohne Tastatur ein
# Grund zum Stromziehen.
fe2 = Attrappe()
fe2.inp = Taster(nach=1)          # gleich die erste Abfrage
ok2 = DEMO.lauf(fe2, FM(), S, BENCH, sekunden=120.0)
check("der Abbruch kommt an", ok2 is False)
check("und zwar sofort", fe2.fb.bilder <= 2,
      "%d Bilder - nicht die ganze Vorfuehrung" % fe2.fb.bilder)

fe3 = Attrappe()
fe3.inp = Taster(nach=25)         # mitten im Scrollen
ok3 = DEMO.lauf(fe3, FM(), S, BENCH, sekunden=120.0)
check("auch mitten im Scrollen", ok3 is False)

# ---------------------------------------------------------------------------
print()
print("Test 3: SIE HINTERLAESST NICHTS")
# ---------------------------------------------------------------------------
fe4 = Attrappe()
fe4.page = 1
fe4.cat_i = 1
fe4.item_i = 7
fe4.nav_path = ["Hacks"]
DEMO.lauf(fe4, FM(), S, BENCH, sekunden=2.0)
check("die Seite steht wieder wie vorher", fe4.page == 1, fe4.page)
check("die Kategorie auch", fe4.cat_i == 1, fe4.cat_i)
check("der Eintrag auch", fe4.item_i == 7, fe4.item_i)
check("und der Pfad im Ordner", fe4.nav_path == ["Hacks"], fe4.nav_path)
check("die Ansichten werden am Ende zurueckgestellt",
      fe4.gesetzt[-2:] and fe4.gesetzt[-1][0] == "liste",
      "%r" % (fe4.gesetzt[-2:],))

# Auch beim ABBRUCH - gerade dann, denn da hoert jemand mittendrin auf.
fe5 = Attrappe()
fe5.page = 1
fe5.cat_i = 1
fe5.item_i = 3
fe5.inp = Taster(nach=20)
DEMO.lauf(fe5, FM(), S, BENCH, sekunden=120.0)
check("auch nach dem Abbruch steht alles wie vorher",
      (fe5.page, fe5.cat_i, fe5.item_i) == (1, 1, 3),
      "%r" % ((fe5.page, fe5.cat_i, fe5.item_i),))

# ---------------------------------------------------------------------------
print()
print("Test 4: SIE NIMMT NICHTS MIT")
# ---------------------------------------------------------------------------
# Eine Vorfuehrung ist Zubehoer. Kein fehlendes Stueck darf ein
# Frontend aufhalten, das eigentlich Spiele starten soll.
class OhneSchirm(Attrappe):
    def __init__(self):
        Attrappe.__init__(self)
        self.fb = None


check("ohne Bildspeicher passiert nichts",
      DEMO.lauf(OhneSchirm(), FM(), S, BENCH, sekunden=2.0) is False)


class LeeresFrontend(Attrappe):
    def __init__(self):
        Attrappe.__init__(self)
        self.cats = []

    def _display_items(self):
        return []


try:
    DEMO.lauf(LeeresFrontend(), FM(), S, BENCH, sekunden=2.0)
    geht = True
except Exception as e:                                   # noqa: BLE001
    geht = "%s: %s" % (type(e).__name__, e)
check("ohne Kategorien laeuft sie trotzdem", geht is True, str(geht))


class KaputtesZeichnen(Attrappe):
    def draw(self, *a, **k):
        raise RuntimeError("kaputt")

    def _draw_navigate_cats(self, alt):
        raise RuntimeError("kaputt")

    def _draw_navigate_items(self, alt):
        raise RuntimeError("kaputt")


try:
    DEMO.lauf(KaputtesZeichnen(), FM(), S, BENCH, sekunden=2.0)
    geht = True
except Exception as e:                                   # noqa: BLE001
    geht = "%s: %s" % (type(e).__name__, e)
check("ein Zeichenfehler bricht sie ab, statt abzustuerzen",
      geht is True, str(geht))


class KaputteEingabe(Attrappe):
    class Inp(object):
        def read_action(self, timeout=None):
            # Dreht die Uhr NICHT weiter - genau die Lage, fuer die
            # die Notbremse in fe/demo.py da ist.
            raise RuntimeError("kaputt")

    def __init__(self):
        Attrappe.__init__(self)
        self.inp = KaputteEingabe.Inp()


try:
    DEMO.lauf(KaputteEingabe(), FM(), S, BENCH, sekunden=2.0)
    geht = True
except Exception as e:                                   # noqa: BLE001
    geht = "%s: %s" % (type(e).__name__, e)
check("eine kaputte Eingabe ebenso", geht is True, str(geht))

# ---------------------------------------------------------------------------
print()
print("Test 5: KEIN zweiter Zeichenweg")
# ---------------------------------------------------------------------------
# Ein Demo-Modus, der sein eigenes Bild malt, zeigt am Ende etwas, das
# es gar nicht gibt. Gezeigt wird, was das Frontend ohnehin zeichnet -
# bewegt wird nur der Zeiger.
quelle = open(os.path.join(_REPO, "frontend", "fe", "demo.py"),
              encoding="utf-8").read()
check("der Schritt kommt aus dem Bench",
      "BENCH.schritt_funktion(fe, seite)" in quelle
      and "BENCH.fenster_spanne(fe, seite)" in quelle)
check("die Ansichten werden ueber das Frontend gesetzt",
      "fe.ansicht_setzen(" in quelle and "fe.ansicht_haupt_setzen(" in quelle)
check("gezeichnet wird nur die Titelkarte selbst",
      quelle.count("fbo.text(") <= 3,
      "alles andere malt das Frontend")

qf = open(H.FRONTEND_PY, encoding="utf-8", errors="replace").read()
check("--demo steht in der Optionsliste", '"--demo":' in qf)
check("und wird ausgefuehrt", 'if "--demo" in sys.argv:' in qf)
check("danach wird beendet",
      "_fe._beenden()" in qf.split('if "--demo" in sys.argv:')[1][:1400])
check("und ein Absturz nimmt das Frontend nicht mit",
      "--demo:" in qf and "Vorfuehrung abgebrochen" in qf)

# ---------------------------------------------------------------------------
print()
print("Test 6: die Laenge laesst sich einstellen, ohne neun Zahlen")
# ---------------------------------------------------------------------------
check("die Stationen haben Gewichte",
      all(isinstance(st[3], (int, float)) and st[3] > 0
          for st in DEMO.STATIONEN))
check("und die Vorgabe sind drei Minuten",
      "sekunden=180.0" in quelle, "so hat der Nutzer es gewuenscht")
check("eine laengere Vorfuehrung braucht nur eine Zahl",
      "je = float(sekunden) / _gewicht_summe()" in quelle)

# ---------------------------------------------------------------------------
print()
print("Test 7: sie nutzt das GANZE Fenster, nicht die ersten drei Zeilen")
# ---------------------------------------------------------------------------
# NUTZERMELDUNG ZU BUILD 233: "der demo mode zuckt in der listen
# ansicht nur in denn ersten drei zeilen rum".
#
# Genau so war es. cats_visible und items_visible werden WAEHREND des
# Zeichnens gesetzt; wer sie vorher liest, bekommt den Startwert 5 -
# und fenster_spanne() macht daraus max(2, 5-2) = drei Zeilen. Der
# Zeiger pendelte zwischen Zeile 0, 1 und 2, die ganze Vorfuehrung
# lang. Dieser Test haelt die Lehre fest: ERST zeichnen, DANN die
# Fenstergroesse holen.
class ZeilenMerker(Attrappe):
    """Schreibt mit, auf welchen Zeilen der Zeiger wirklich war - und
    setzt die Fenstergroesse erst beim Zeichnen, wie das echte
    Frontend."""

    def __init__(self):
        Attrappe.__init__(self)
        self.cats_visible = 5         # der Startwert aus frontend.py
        self.items_visible = 5
        self.besucht = set()

    def _echtes_fenster(self):
        self.cats_visible = 14
        self.items_visible = 17

    def _draw_navigate_cats(self, alt):
        self._echtes_fenster()
        self.besucht.add(self.cat_i)
        self.gezeichnet += 1
        return True

    def _draw_navigate_items(self, alt):
        self._echtes_fenster()
        self.besucht.add(self.item_i)
        self.gezeichnet += 1
        return True

    def draw(self, *a, **k):
        self._echtes_fenster()
        self.gezeichnet += 1


fe6 = ZeilenMerker()
DEMO.lauf(fe6, FM(), S, BENCH, sekunden=6.0)
check("der Zeiger besucht mehr als drei Zeilen",
      len(fe6.besucht) > 3,
      "%d Zeilen: %r" % (len(fe6.besucht), sorted(fe6.besucht)[:20]))
check("und zwar deutlich mehr",
      len(fe6.besucht) >= 10,
      "%d - das Fenster ist 14 bis 17 Zeilen hoch" % len(fe6.besucht))

_q = open(os.path.join(_REPO, "frontend", "fe", "demo.py"),
          encoding="utf-8").read()
_scr = _q.split("def _scrollen")[1].split("\ndef ")[0]
# Gesucht wird der AUFRUF, nicht die Erwaehnung im Kommentar - der
# erklaert den Fehler ja gerade und nennt den Namen deshalb zuerst.
check("erst zeichnen, dann die Fenstergroesse holen",
      _scr.index("schritt(0)")
      < _scr.index("BENCH.fenster_spanne(fe, seite)"),
      "andersherum steht dort noch der Startwert 5")

# ---------------------------------------------------------------------------
print()
print("Test 8: das Systemmenue zeigt EINSTELLUNGEN, nicht Ordnernamen")
# ---------------------------------------------------------------------------
# NUTZERMELDUNG: "system menue und einstellung werden garnicht
# gezeigt". Die Wurzel der System-Kategorie besteht fast nur aus
# Ordnern - wer dort scrollt, sieht sechs Ordnernamen und keine
# einzige Einstellung.
class MitSystem(Attrappe):
    def __init__(self):
        Attrappe.__init__(self)
        self.cats = [
            ("Arcade", {"items": [("A%d" % i, "game", None)
                                  for i in range(300)],
                        "folders": {}}, None),
            ("System", {"items": [("Beenden", "x", None)],
                        "folders": {
                            "Anzeige & Sound": {
                                "items": [("Option %d" % i, "x", None)
                                          for i in range(25)],
                                "folders": {}},
                            "Info": {"items": [("Hilfe", "x", None)],
                                     "folders": {}}}}, None),
        ]


fe7 = MitSystem()
seite, ansicht = DEMO._station_einstellen(fe7, S, "system",
                                          0, DEMO._system_kategorie(fe7))
check("die System-Kategorie wird gefunden",
      DEMO._system_kategorie(fe7) == 1)
check("und es geht eine Ebene tiefer",
      fe7.nav_path == ["Anzeige & Sound"],
      "%r - sonst sieht man nur Ordnernamen" % (fe7.nav_path,))
check("in den Ordner mit dem meisten Inhalt",
      "_station_einstellen" in _q and "key=lambda e: -len(" in _q)

# Ohne genug Inhalt bleibt es bei der Wurzel - eine Vorfuehrung darf
# daran nicht scheitern.
fe8 = MitSystem()
fe8.cats[1][1]["folders"]["Anzeige & Sound"]["items"] = [("A", "x", None)]
fe8.cats[1][1]["folders"]["Info"]["items"] = []
DEMO._station_einstellen(fe8, S, "system", 0, 1)
check("ohne genug Inhalt bleibt es bei der Wurzel",
      fe8.nav_path == [], "%r" % (fe8.nav_path,))

# ---------------------------------------------------------------------------
print()
print("Test 9: nach der Vorfuehrung startet nicht sofort Zufalls-Zock")
# ---------------------------------------------------------------------------
# DIE DRITTE HAELFTE DER MELDUNG ZU BUILD 233: "dann oeffnet er nur
# zufalls zock und bleibt dort stehen".
#
# Das war kein Fehler der Vorfuehrung, sondern ihre Folge. Der
# Attract-Modus (im Menue "Zufalls-Zock - Spiel ziehen") startet nach
# ATTRACT_DELAY Sekunden ohne Eingabe, voreingestellt 90. Die
# Vorfuehrung laeuft 180 Sekunden mit eigener Schleife -
# _last_input_time stand danach drei Minuten in der Vergangenheit, und
# der erste Leerlauf-Tick danach erfuellte die Bedingung sofort.
#
# Geprueft wird die EIGENSCHAFT, nicht die Zeile: nach dem Lauf darf
# die Eingabe-Uhr nicht aelter sein als ein Wimpernschlag.
import fe.settings as _S9                                  # noqa: E402
print("   ATTRACT_DELAY_STEPS beginnt bei %d s, die Vorfuehrung laeuft"
      " %d s" % (min(_S9.ATTRACT_DELAY_STEPS), 180))


class UhrFrontend(Attrappe):
    """Wie die Attrappe, aber mit einer Eingabe-Uhr, die alt ist -
    genau wie sie nach 180 Sekunden Vorfuehrung dasteht."""

    def __init__(self, nach=10**9):
        Attrappe.__init__(self)
        self.inp = Taster(nach=nach)
        self._last_input_time = time.monotonic() - 500.0


for nach, was in ((10**9, "nach dem vollen Lauf"),
                  (3, "und auch nach dem Abbruch durch eine Taste")):
    fe9 = UhrFrontend(nach=nach)
    vorher9 = time.monotonic() - fe9._last_input_time
    try:
        DEMO.lauf(fe9, FM(), S, BENCH, sekunden=2.0)
    except Exception as e:                                 # noqa: BLE001
        print("       %s: %s" % (type(e).__name__, e))
    jung = time.monotonic() - fe9._last_input_time
    check("%s ist die Eingabe-Uhr frisch" % was, jung < 5.0,
          "%.1f s alt (vorher %.1f s)" % (jung, vorher9))

check("die Uhr wird im finally nachgestellt, nicht an mehreren Stellen",
      open(os.path.join(_REPO, "frontend", "fe", "demo.py"),
           encoding="utf-8").read().count("_last_input_time = time.monotonic()")
      == 1,
      "jeder zweite Ort waere einer, der beim Abbruch nicht laeuft")

print()
if fails:
    print("FEHLGESCHLAGEN (%d):" % len(fails))
    for f in fails:
        print("  - %s" % f)
    sys.exit(1)
print("Alles in Ordnung.")
