#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Die Hausarbeit faellt aus, solange eine Taste gehalten wird (Build 273).

WORAUF DAS ZURUECKGEHT - und es ist diesmal das Protokoll des Geraets,
keine Vermutung. NUTZERFRAGE:

    "wenn ich beim neuen kernel schnell hintereinander hoch oder runter
     druecke geht das mit dem scrollen eigentlich. wenn ich aber nach
     oben gedrueckt halte oder nach unten, dann scrollt der ganz laggig
     und stockend. warum ist das so?"

Die Antwort stand in zwei Zeilen seines Logs:

    RUCKLER: 1646 ms busy (stream=1 haus=1572 zeichnen=71 rest=3)
    LATENZ-JE-AKTION: down/S0 133x Mittel 166 (max 2889)

**1572 von 1646 Millisekunden in der HAUSARBEIT**, bei 71 ms Zeichnen.
Der Kommentar in draw() hatte den Verdacht schon 2024 notiert ("lange
billig, dann einmal teuer") und den Zaehler dafuer eingebaut - jetzt
ist er eingeloest.

UND DAMIT IST AUCH DIE FRAGE "warum nur beim HALTEN?" beantwortet: die
Hausarbeit laeuft vor JEDEM Bild. Drueckt man einzeln, faellt sie in
die Pause zwischen zwei Tastendruecken, und niemand wartet auf sie.
Haelt man die Taste, sitzt sie zwischen je zwei Schritten.

WAS HIER GEPRUEFT WIRD

  1. Bei gehaltener Taste laufen die fuenf Aufgaben NICHT.
  2. Ohne gehaltene Taste laufen sie.
  3. Die Obergrenze greift: nach HAUSARBEIT_PAUSE_MAX laufen sie auch
     bei gehaltener Taste - sie fallen aus, sie verschwinden nicht.
  4. Die LAUFSCHRIFT laeuft immer - sie ist das einzige Sichtbare an
     der Hausarbeit, und ein Musiktitel, der beim Scrollen
     stehenbleibt, waere ein neuer Fehler anstelle des alten.
  5. Jeder Posten wird EINZELN gemessen, und eine teure Runde schreibt
     ihre Aufteilung ins Protokoll - "haus=1572" sagte bisher nicht,
     WELCHE der fuenf.

Ausfuehren:
    python3 tools/test_hausarbeit.py
"""
import os
import sys

_HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HIER)
import _harness as H                                     # noqa: E402

fm = H.fm
fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


H.set_screen(1920, 1080)
FE = H.make_frontend(page=0)

RUFE = []
AUFGABEN = ("_maybe_apply_pending_ra_data", "_maybe_retry_ra",
            "_maybe_retry_clock", "_maybe_rebuild_ra_categories",
            "_maybe_rescan_for_late_mount")
MARQUEE = "_sync_track_marquee"


def _haken(name, dauer=0.0):
    def ersatz(*a, **k):
        RUFE.append(name)
        if dauer:
            H.NOW[0] += dauer        # kuenstliche Uhr, siehe _harness
    return ersatz


for _n in AUFGABEN + (MARQUEE,):
    setattr(FE, _n, _haken(_n))


def _runde():
    del RUFE[:]
    FE.draw()
    return list(RUFE)


# ---------------------------------------------------------------------------
print("Test 1: ohne gehaltene Taste laeuft alles wie bisher")
# ---------------------------------------------------------------------------
FE.inp.held = None
FE._haus_letzte = 0.0
gerufen = _runde()
check("alle fuenf Aufgaben laufen",
      all(n in gerufen for n in AUFGABEN),
      str([n for n in AUFGABEN if n not in gerufen]))
check("und die Laufschrift auch", MARQUEE in gerufen)

# ---------------------------------------------------------------------------
print()
print("Test 2: bei GEHALTENER Taste fallen sie aus")
# ---------------------------------------------------------------------------
# So sieht ein gehaltener Tastendruck im InputManager aus:
# (key_id, aktion, naechste_zeit, intervall) - siehe _hold().
FE.inp.held = (("/dev/input/event0", 108), "down", H.NOW[0] + 0.1, 0.1)
FE._haus_letzte = H.NOW[0]
gerufen = _runde()
check("keine der fuenf Aufgaben laeuft",
      not any(n in gerufen for n in AUFGABEN),
      str([n for n in AUFGABEN if n in gerufen]))
check("die Laufschrift laeuft TROTZDEM", MARQUEE in gerufen,
      "sie ist das einzige Sichtbare - ein Titel, der beim Scrollen "
      "stehenbleibt, waere ein neuer Fehler anstelle des alten")
check("und es wird mitgezaehlt", FE._haus_ausgelassen >= 1,
      "%d" % FE._haus_ausgelassen)
check("die gemessene Hausarbeit ist dann (fast) null",
      FE._perf_house < 0.01, "%.4f s" % FE._perf_house)

# ---------------------------------------------------------------------------
print()
print("Test 3: die Obergrenze - sie fallen aus, sie verschwinden nicht")
# ---------------------------------------------------------------------------
# DAS IST DIE WICHTIGE ZUSAGE. Alle fuenf Aufgaben haben einen Grund
# (RA-Daten einarbeiten, Netzabfrage wiederholen, Uhr abgleichen,
# Kategorien neu bauen, spaet eingehaengte Laufwerke finden). Wer sie
# bei gehaltener Taste dauerhaft abschaltet, baut aus einem Ruckler
# einen Ausfall.
H.NOW[0] += FE.HAUSARBEIT_PAUSE_MAX + 0.1
gerufen = _runde()
check("nach der Obergrenze laufen sie auch bei gehaltener Taste",
      all(n in gerufen for n in AUFGABEN),
      "Grenze ist %.1f s" % FE.HAUSARBEIT_PAUSE_MAX)
check("und die Grenze ist kuerzer als die Wartezeit der Aufgaben selbst",
      0.5 <= FE.HAUSARBEIT_PAUSE_MAX <= 5.0,
      "%.1f s" % FE.HAUSARBEIT_PAUSE_MAX)

# ---------------------------------------------------------------------------
print()
print("Test 4: eine teure Runde sagt, WELCHE Aufgabe teuer war")
# ---------------------------------------------------------------------------
# "haus=1572" war die Zahl, die der Nutzer geschickt hat - und sie sagt
# nicht, ob es die Netzabfrage, die Uhr, der Kategorie-Neubau oder die
# Laufwerkssuche war. Vier sehr verschiedene Verdaechtige.
zeilen = []
_echt_log = fm.LOG
fm.LOG = lambda s: zeilen.append(s)
try:
    FE.inp.held = None
    FE._haus_letzte = 0.0
    # Eine der fuenf dauert kuenstlich 300 ms (ueber die kuenstliche
    # Uhr des Pruefstands - kein echtes Warten).
    FE._maybe_retry_clock = _haken("_maybe_retry_clock", dauer=0.3)
    _runde()
finally:
    fm.LOG = _echt_log
    FE._maybe_retry_clock = _haken("_maybe_retry_clock")
haus = [z for z in zeilen if z.startswith("HAUSARBEIT:")]
check("die Runde wird protokolliert", len(haus) == 1, str(zeilen[-3:]))
check("mit der Gesamtzeit", haus and " ms - " in haus[0], str(haus))
check("und mit dem NAMEN des teuren Postens",
      haus and "uhr=300" in haus[0], str(haus))
check("die Schwelle steht als benannte Konstante da",
      hasattr(FE, "HAUSARBEIT_LOG_MS") and FE.HAUSARBEIT_LOG_MS > 0,
      "sonst stuende die Zahl mitten im Code")

# ---------------------------------------------------------------------------
print()
print("Test 5: eine billige Runde schweigt")
# ---------------------------------------------------------------------------
# Eine Zeile je Bild waere ein Protokoll, in dem man nichts mehr
# findet - und das Schreiben selbst kostet (siehe die LOG-Posten in
# Abschnitt J des Benchs).
zeilen = []
fm.LOG = lambda s: zeilen.append(s)
try:
    FE.inp.held = None
    FE._haus_letzte = 0.0
    _runde()
finally:
    fm.LOG = _echt_log
check("ohne teuren Posten steht keine HAUSARBEIT-Zeile im Log",
      not [z for z in zeilen if z.startswith("HAUSARBEIT:")],
      str([z for z in zeilen if z.startswith("HAUSARBEIT:")]))

# ---------------------------------------------------------------------------
print()
print("Test 6: die Entscheidung haengt an EINER Stelle")
# ---------------------------------------------------------------------------
import io                                                # noqa: E402
_q = io.open(H.FRONTEND_PY, encoding="utf-8").read()
check("es gibt genau eine Pruefung _hausarbeit_jetzt()",
      _q.count("def _hausarbeit_jetzt(") == 1
      and _q.count("self._hausarbeit_jetzt(") == 1,
      "zwei Stellen waeren zwei Regeln fuer dieselbe Frage")
check("ein fehlendes 'held' schaltet die Hausarbeit NICHT ab",
      'getattr(self.inp, "held", None)' in _q,
      "ein InputManager ohne dieses Feld (aeltere Fassung, Pruefstand "
      "ohne __init__) wuerde sonst dafuer sorgen, dass die Hausarbeit "
      "gar nicht mehr laeuft")

# ---------------------------------------------------------------------------
print()
print("Test 7: der teure Posten selbst - Kategorien nur bei RUHE neu bauen")
# ---------------------------------------------------------------------------
# DIE ZEILE AUS BUILD 273 HAT GELIEFERT, vom Geraet:
#
#   HAUSARBEIT: 1630 ms - ra_kategorien=1627, mount=3
#
# 1627 von 1630 ms sind der Neubau der Kategorien ueber 31.000 Spiele -
# und der lief mitten im Zeichenweg. Ab Build 274 verlangt er RUHE.
# Geprueft wird hier die ECHTE Methode, nicht die Attrappe von oben.
for _n in AUFGABEN:
    try:
        delattr(FE, _n)          # Haken weg, echte Methode zurueck
    except AttributeError:
        pass
neubauten = []
FE._rebuild_categories_preserving_selection = (
    lambda *a, **k: neubauten.append(1))
FE.inp.held = None
FE.page = 0
FE._ra_categories_dirty = True
FE._last_input_time = H.NOW[0]          # gerade eben gedrueckt
FE._maybe_rebuild_ra_categories()
check("waehrend gescrollt wird: KEIN Neubau", not neubauten,
      "1,6 Sekunden Stillstand mitten im Zeichenweg")
check("und das Flag bleibt stehen - verloren geht nichts",
      FE._ra_categories_dirty is True)

H.NOW[0] += FE.RA_NEUBAU_RUHE + 0.1
FE._maybe_rebuild_ra_categories()
check("nach der Ruhe wird nachgeholt", len(neubauten) == 1,
      "%d" % len(neubauten))
check("und das Flag ist verbraucht",
      FE._ra_categories_dirty is False)

del neubauten[:]
FE._ra_categories_dirty = True
FE.page = 1
FE._last_input_time = H.NOW[0] - 10.0   # lange Ruhe
FE._maybe_rebuild_ra_categories()
check("in einer Kategorie (Seite 1) weiterhin nicht", not neubauten,
      "die Zusage von vorher gilt unveraendert - ein Neubau mitten in "
      "einer Kategorie passt nicht zu Ordnerpfad und Scrollstand")
FE.page = 0
del neubauten[:]
FE._ra_categories_dirty = False
FE._maybe_rebuild_ra_categories()
check("ohne frische Daten passiert gar nichts", not neubauten)
check("die Ruhezeit steht als benannte Konstante da",
      0.3 <= FE.RA_NEUBAU_RUHE <= 3.0,
      "%.1f s - laenger als jede Scroll-Wiederholung, kurz genug, dass "
      "die Daten gleich nach dem Loslassen stehen" % FE.RA_NEUBAU_RUHE)

# ---------------------------------------------------------------------------
print()
print("Build 276: eine gehaltene Taste ist kein Stillstand")
import time as _t276                                       # noqa: E402
time = _t276
# ---------------------------------------------------------------------------
# NUTZERMELDUNG: "das Scrollen bei gedrueckter Taste ist totaler Mist,
# lagt ohne Ende und stockt" - und dazu, aus demselben Protokoll, 291 ms
# Latenz im Mittel bei NULL Ruckler-Zeilen.
#
# URSACHE: "wird gerade navigiert?" hing allein an der Uhr (letzte
# Eingabe < 150 ms her). Kommen die Schritte selbst langsamer als
# 150 ms, gilt jeder Zwischenraum als Stillstand - und dann laufen
# Nachlader, Warmlauf, Laufschrift und Puls GENAU ZWISCHEN zwei
# Schritten. Der naechste Schritt kommt dadurch noch spaeter, der
# Zwischenraum wird groesser, und die Sache treibt sich selbst.
#
# Deshalb steht hier KEINE Zeitmessung, sondern die eine Zusage, auf
# die es ankommt: solange die Taste gehalten wird, ist kein Stillstand.
f276 = H.make_frontend(page=1)


class _InpGehalten(object):
    held = (("/dev/input/event0", "key", 108), "down", 0.0, 0.08)
    _last_repeat_time = 0.0


class _InpLos(object):
    held = None
    _last_repeat_time = 0.0


# Der letzte Schritt liegt deutlich laenger zurueck als das Fenster -
# nach der alten Regel waere das ein Stillstand.
f276._last_input_time = time.monotonic() - 1.0

f276.inp = _InpLos()
check("ohne gehaltene Taste gilt ein alter Schritt als Stillstand",
      f276._nav_active() is False,
      "sonst liefen Nachlader und Laufschrift nie - der Schutz darf "
      "nicht zum Dauerzustand werden")

f276.inp = _InpGehalten()
check("mit gehaltener Taste NICHT",
      f276._nav_active() is True,
      "das ist die Rueckkopplung: Schritt spaet -> 'Stillstand' -> "
      "Nachlader -> Schritt noch spaeter")

# Und der frische Schritt zaehlt weiter wie bisher, ganz ohne Taste.
f276.inp = _InpLos()
f276._last_input_time = time.monotonic()
check("ein frischer Schritt zaehlt weiter allein ueber die Uhr",
      f276._nav_active() is True)

# Eine Attrappe OHNE das Feld darf nicht darueber fallen - in den
# uebrigen Tests dieser Datei ist self.inp genau so eine.
class _InpRoh(object):
    pass


f276.inp = _InpRoh()
f276._last_input_time = time.monotonic() - 1.0
check("eine Eingabe-Attrappe ohne das Feld stuerzt nicht ab",
      f276._nav_active() is False,
      "dieselbe Vorsicht wie bei _hausarbeit_jetzt()")

# DER COVER-AUFSCHUB HAENGT AN DERSELBEN RUECKKOPPLUNG, und genau ihn
# hat der Nutzer SEHEN koennen: "wenn ich dort nach links oder rechts
# gedrueckt halte, ziehen die Sysart nach, als wenn die nachgeladen
# werden."
f276.inp = _InpGehalten()
f276.inp._last_repeat_time = time.monotonic() - 1.0
check("die Scroll-Serie gilt weiter, solange gehalten wird",
      f276._scroll_serie_aktiv() is True,
      "sonst wird mitten im Halten wieder in voller Groesse gerechnet")
f276.inp = _InpLos()
f276.inp._last_repeat_time = time.monotonic() - 1.0
check("und geht nach dem Loslassen aus",
      f276._scroll_serie_aktiv() is False,
      "was aufgeschoben wurde, holt der Nachlader im Leerlauf nach - "
      "der Aufschub darf nicht haengen bleiben")
f276.inp = _InpGehalten()
f276.inp._last_repeat_time = 0.0
check("ohne laufenden Scrollvorgang bleibt er aus",
      f276._scroll_serie_aktiv() is False,
      "ein einzelner bedachter Tastendruck soll das Cover sofort "
      "bekommen, auch wenn die Taste noch unten ist")

# EINE STELLE, EINE ANTWORT: der Leerlaufzweig rechnete das Fenster
# bisher ein zweites Mal selbst nach. Zwei Kopien derselben Regel sind
# genau der Grund, warum diese eine Stelle jahrelang uebersehen wurde.
check("der Leerlaufzweig fragt dieselbe Stelle",
      "nav_active = self._nav_active()" in _q,
      "vorher stand dort eine zweite Kopie der Zeitrechnung")

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
