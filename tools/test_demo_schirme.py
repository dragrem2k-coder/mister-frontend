#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Die Vorfuehrung zeigt die ECHTEN Bildschirme (Build 262).

NUTZERWUNSCH: "kannst du eine erstellen die einmal durch das Frontend
scrollt, Ansichten zeigt und alle Features einmal zeigt? Nicht nur per
Text einblenden - einmal durch scrollen Optionen, System, Zufalls-Zock,
RA, alles einmal einblenden. Sollte so 4 Minuten gehen."

Bis Build 261 konnte die Vorfuehrung zwei Dinge: eine Titelkarte malen
und den Zeiger durch eine Liste laufen lassen. Zufalls-Zock,
Trophaeenraum, Meilensteine und die anderen Vollbild-Seiten kamen darin
nur als WORT auf einer Titelkarte vor - genau die Kritik.

DAS HINDERNIS: diese Bildschirme sind Warteschleifen. Sie zeichnen,
rufen inp.read_action() ohne Zeitgrenze und warten auf einen Menschen.
Die Loesung ist eine HAND AM PAD - ein Eingabe-Objekt, das die Tasten
liefert, die ein Vorfuehrender druecken wuerde. An den Bildschirmen
aendert sich dadurch KEINE ZEILE.

WAS HIER GEPRUEFT WIRD, und warum es ein eigener Test ist:
tools/test_demo.py arbeitet mit einer Attrappe, die nur das kann, was
die Vorfuehrung FRUEHER angefasst hat - die neuen Stationen wuerden
dort stillschweigend uebersprungen und der Test bliebe gruen. Ein Test,
der die neue Faehigkeit gar nicht erreicht, prueft sie auch nicht.

Hier stehen deshalb Attrappen, die die ECHTEN SCHLEIFENFORMEN
nachbilden - beide, die es in frontend.py gibt:

    scrollbar:   act = read_action()
                 if act in ("up","down") and max_scroll > 0: scrollen
                 if act is not None: break
    einfach:     act = read_action()
                 if act is not None: break

Der Unterschied ist der ganze Grund fuer die Tabelle in demo.py: bei
max_scroll == 0 ist "runter" fuer einen scrollbaren Bildschirm eine
BELIEBIGE Taste, und er geht zurueck. Auf HDMI passt aber oft alles auf
eine Seite.

Ausfuehren:
    python3 tools/test_demo_schirme.py
"""
import io
import os
import sys
import time

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
_FRONTEND_DIR = os.path.dirname(
    os.environ.get("FRONTEND_PY",
                   os.path.join(_REPO, "frontend", "frontend.py")))
sys.path.insert(0, _FRONTEND_DIR)

import fe.demo as DEMO                                   # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


class Uhr(object):
    """Eine Uhr, die nur dann weiterlaeuft, wenn jemand wartet - sonst
    dauert ein Test echte Minuten."""

    def __init__(self, takt=0.05):
        self.jetzt = 1000.0
        self.takt = takt

    def __call__(self):
        return self.jetzt

    def schlafen(self, d):
        self.jetzt += d


UHR = Uhr()
DEMO.time = type("t", (), {"monotonic": staticmethod(lambda: UHR.jetzt),
                           "sleep": staticmethod(UHR.schlafen)})()


class EchteHand(object):
    """Die echte Eingabe, die nie etwas meldet - aber die Uhr dreht,
    genau wie ein echtes read_action(timeout=...) es tut."""

    def __init__(self, antwort_nach=None):
        self.n = 0
        self.antwort_nach = antwort_nach
        self.gefragt = 0

    def read_action(self, timeout=None):
        self.gefragt += 1
        UHR.schlafen(timeout or 0.05)
        if self.antwort_nach and self.gefragt >= self.antwort_nach:
            return "ok"
        return None

    def flush(self):
        self.n += 1
        return "geflusht"


class Schirm(object):
    """Ein Bildschirm in einer der beiden echten Schleifenformen."""

    def __init__(self, inp_holen, scrollbar=True, max_scroll=3,
                 stur=False):
        self.inp_holen = inp_holen
        self.scrollbar = scrollbar
        self.max_scroll = max_scroll
        self.stur = stur
        self.scroll = 0
        self.runden = 0
        self.geschlossen = False

    def __call__(self):
        while True:
            self.runden += 1
            if self.runden > 10000:
                raise AssertionError("Schleife laeuft davon")
            act = self.inp_holen().read_action()
            if self.scrollbar and act in ("up", "down") \
                    and self.max_scroll > 0:
                self.scroll = min(self.max_scroll, self.scroll + 1)
                continue
            if act is not None:
                if self.stur:          # kommt NIE zurueck
                    continue
                self.geschlossen = True
                return


class Attrappe(object):
    def __init__(self, inp):
        self.inp = inp

    def draw(self):
        pass


# ---------------------------------------------------------------------------
print("Test 1: die Hand zeigt, hoert auf - und weicht")
# ---------------------------------------------------------------------------
echt = EchteHand()
fe = Attrappe(echt)
s1 = Schirm(lambda: fe.inp, scrollbar=True, max_scroll=5)
t0 = UHR.jetzt
weiter = DEMO._schirm(fe, s1, 10.0, ("down",), 1.0, "probe")
check("der Bildschirm kam von selbst zurueck", s1.geschlossen)
check("er hat dabei gescrollt", s1.scroll > 0, "Scroll %d" % s1.scroll)
check("die Station hat ihre Zeit gebraucht",
      9.0 <= UHR.jetzt - t0 <= 11.5, "%.1f s" % (UHR.jetzt - t0))
check("und die Vorfuehrung laeuft weiter", weiter is True)
check("die echte Eingabe wurde zurueckgegeben", fe.inp is echt,
      "sonst haengt die Hand bis zum Programmende am Frontend")

# ---------------------------------------------------------------------------
print()
print("Test 2: eine ECHTE Taste bricht alles ab")
# ---------------------------------------------------------------------------
# DAS IST DIE WICHTIGSTE ZUSAGE DES GANZEN MODULS: "jede Taste bricht
# ab". Sie darf nicht ausgerechnet dort aufhoeren zu gelten, wo eine
# gescriptete Hand am Pad liegt.
echt2 = EchteHand(antwort_nach=3)
fe2 = Attrappe(echt2)
s2 = Schirm(lambda: fe2.inp, scrollbar=True, max_scroll=5)
weiter = DEMO._schirm(fe2, s2, 60.0, ("down",), 5.0, "probe2")
check("die Vorfuehrung bricht ab", weiter is False)
check("und der Bildschirm ist trotzdem sauber zu",
      s2.geschlossen, "er bekommt 'zurueck', kein Abwuergen")
check("das ging lange vor dem Ende der Station",
      s2.scroll == 0, "drei Abfragen, kein Scrollschritt")

# ---------------------------------------------------------------------------
print()
print("Test 3: ein Bildschirm OHNE Scrollen schliesst sich nicht zu frueh")
# ---------------------------------------------------------------------------
# Der Fall, der die Tabelle in demo.py begruendet: Jahresrueckblick und
# Testbild kennen kein Scrollen. Wer denen ein "runter" schickt,
# beendet sie sofort - deshalb bekommen sie GAR KEINE Taste.
echt3 = EchteHand()
fe3 = Attrappe(echt3)
s3 = Schirm(lambda: fe3.inp, scrollbar=False)
t0 = UHR.jetzt
DEMO._schirm(fe3, s3, 8.0, (), 0, "ohne_scrollen")
check("er stand die volle Zeit", 7.0 <= UHR.jetzt - t0 <= 9.5,
      "%.1f s" % (UHR.jetzt - t0))
check("und wurde genau einmal geschlossen", s3.geschlossen)

# Und die Gegenprobe, die zeigt, dass die Sorge berechtigt ist:
echt3b = EchteHand()
fe3b = Attrappe(echt3b)
s3b = Schirm(lambda: fe3b.inp, scrollbar=False)
t0 = UHR.jetzt
DEMO._schirm(fe3b, s3b, 8.0, ("down",), 1.0, "mit_taste")
check("mit Taste waere er sofort weg - die Zeit haelt ihn trotzdem",
      7.0 <= UHR.jetzt - t0 <= 9.5,
      "%.1f s - _schirm() laesst das fertige Bild stehen, statt die "
      "Station zu verschlucken" % (UHR.jetzt - t0))

# ---------------------------------------------------------------------------
print()
print("Test 4: ein sturer Bildschirm haelt die Vorfuehrung nicht auf")
# ---------------------------------------------------------------------------
echt4 = EchteHand()
fe4 = Attrappe(echt4)
s4 = Schirm(lambda: fe4.inp, scrollbar=True, max_scroll=2, stur=True)
t0 = UHR.jetzt
weiter = DEMO._schirm(fe4, s4, 5.0, ("down",), 1.0, "stur")
check("die Vorfuehrung geht weiter", weiter is True)
check("der Bildschirm ist NICHT zurueckgekommen", not s4.geschlossen)
check("aber die Station endet trotzdem", UHR.jetzt - t0 < 8.0,
      "%.1f s - nach %d vergeblichen 'zurueck' wird abgebrochen"
      % (UHR.jetzt - t0, DEMO._GEDULD))

# ---------------------------------------------------------------------------
print()
print("Test 5: eine Zeitgrenze wird eingehalten")
# ---------------------------------------------------------------------------
# Ein Bildschirm, der mit Zeitgrenze fragt, zeichnet zwischendurch (die
# Ziehung beim Zufalls-Zock tut genau das). Wer ihm die Zeit stiehlt,
# macht aus einer Animation ein Standbild.
hand = DEMO._Hand(EchteHand(), ("down",), 10.0, UHR.jetzt + 100.0)
t0 = UHR.jetzt
antwort = hand.read_action(timeout=0.5)
check("sie liefert nichts, wenn nichts faellig ist", antwort is None)
check("und kommt puenktlich zurueck", UHR.jetzt - t0 <= 1.0,
      "%.2f s statt 10 s Pause" % (UHR.jetzt - t0))

# ---------------------------------------------------------------------------
print()
print("Test 6: alles andere geht ans echte Eingabe-Objekt")
# ---------------------------------------------------------------------------
echt6 = EchteHand()
hand6 = DEMO._Hand(echt6, (), 1.0, UHR.jetzt + 10.0)
check("flush() kommt beim echten an", hand6.flush() == "geflusht")
check("und wurde dort wirklich gezaehlt", echt6.n == 1,
      "eine zweite Fassung des Eingabe-Managers waere genau die Sorte "
      "Nachbau, die uns in Build 260 eingeholt hat")

# ---------------------------------------------------------------------------
print()
print("Test 7: die Bildschirme in der Tabelle GIBT es wirklich")
# ---------------------------------------------------------------------------
# Der stille Fehler, gegen den das hier steht: _schirm_station() holt
# die Methode mit getattr(..., None) und ueberspringt die Station, wenn
# es sie nicht gibt. Wird eine Methode umbenannt, faellt die Station
# fuer immer aus - und niemand merkt es, weil nichts rot wird.
_q = io.open(os.path.join(_FRONTEND_DIR, "frontend.py"),
             encoding="utf-8").read()
for st in DEMO.SCHIRME:
    name, methode = st[0], st[4]
    if methode is None:
        continue
    check("%s -> %s() gibt es" % (name, methode),
          ("    def %s(" % methode) in _q)

check("es sind zehn Bildschirme", len(DEMO.SCHIRME) == 10,
      str(len(DEMO.SCHIRME)))
check("jeder steht auch als Station in der Vorfuehrung",
      all(("schirm:" + st[0]) in [x[0] for x in DEMO.STATIONEN]
          for st in DEMO.SCHIRME))
check("die Vorgabe sind vier Minuten",
      "sekunden=240.0" in io.open(
          os.path.join(_FRONTEND_DIR, "fe", "demo.py"),
          encoding="utf-8").read())

# WAS JEDE STATION BEKOMMT - zur Auskunft, und damit auffaellt, wenn
# eine davon auf Sekundenbruchteile zusammenschrumpft.
_summe = DEMO._gewicht_summe()
print()
print("       Zeiteinteilung bei 240 s (%d Stationen, Gewicht %.1f):"
      % (len(DEMO.STATIONEN), _summe))
_kleinste = 999.0
for schluessel, titel, _e, gew in DEMO.STATIONEN:
    d = 240.0 * gew / _summe
    _kleinste = min(_kleinste, d)
    print("         %-22s %5.1f s" % (schluessel, d))
check("keine Station faellt unter vier Sekunden",
      _kleinste >= 4.0, "kuerzeste %.1f s" % _kleinste)

# ---------------------------------------------------------------------------
print()
print("Test 8: jede Station ruft WIRKLICH ihren Bildschirm auf")
# ---------------------------------------------------------------------------
# Die Naht, die sonst niemand prueft: _schirm_station() holt die
# Methode mit getattr() und ueberspringt still, wenn sie fehlt. Test 7
# sichert die NAMEN, hier wird gerufen.


class Voll(object):
    """Ein Frontend, das alle zehn Bildschirme hat und mitschreibt."""

    def __init__(self):
        self.inp = EchteHand()
        self.page = 1
        self.cat_i = 0
        self.item_i = 0
        self.nav_path = []
        self.gerufen = []
        for st in DEMO.SCHIRME:
            if st[4]:
                self._anlegen(st[4])

    def _anlegen(self, name):
        def fn(*a):
            self.gerufen.append((name, a))
            Schirm(lambda: self.inp, scrollbar=True, max_scroll=3)()
        setattr(self, name, fn)

    def draw(self):
        pass

    def ansicht_setzen(self, _a):
        pass

    def ansicht_haupt_setzen(self, _a):
        pass


voll = Voll()
for st in DEMO.SCHIRME:
    DEMO._schirm_station(voll, None, st[0], 2.0, 0, 1, None)

_namen = [n for n, _a in voll.gerufen]
for st in DEMO.SCHIRME:
    if st[4] is None:
        continue
    check("%s wurde aufgerufen" % st[0], st[4] in _namen, str(_namen))
check("die Top-10 bekommt ihren Parameter",
      ("draw_top10_screen", ("seconds",)) in voll.gerufen,
      str([x for x in voll.gerufen if x[0] == "draw_top10_screen"]))
check("die Suche braucht keine Methode am Frontend",
      "suche" not in _namen,
      "sie ist ein Zustand, den der normale Seitenaufbau zeichnet")

# Und der Fall, auf den es am meisten ankommt: fehlt der Bildschirm,
# wird uebersprungen - mit einer Zeile im Log, nicht stillschweigend.
class Leer(object):
    def __init__(self):
        self.inp = EchteHand()
        self.page = 1
        self.cat_i = 0
        self.item_i = 0
        self.nav_path = []

    def draw(self):
        pass

    def ansicht_setzen(self, _a):
        pass


_log = []
check("ein fehlender Bildschirm wirft nicht",
      DEMO._schirm_station(Leer(), None, "trophy", 1.0, 0, 1,
                           _log.append) is True)
check("und sagt im Log, dass er uebersprungen wurde",
      any("UEBERSPRUNGEN" in z for z in _log), str(_log))

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
