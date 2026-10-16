#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Nach einem Konsolenprogramm wird OHNE NACHSEHEN gewischt (Build 264).

NUTZER-RUECKMELDUNG zu Build 263: "wenn ich dann eine anleitung oeffne
bleib ich ab und zu im login prompt haengen und kann das frontend also
mister einmal neu starten." Geholfen hat **F10** - also ein voller
Neuaufbau.

DAS LOG DES GERAETS HAT DEN FALL ENTSCHIEDEN, und zwar gegen zwei
naheliegende Vermutungen:

    13:46:38  _auf_konsole: ... beendet, Ruecksprungwert=0
    13:46:39  enter_console_mode (F9) / grab(True)
    13:46:39  PERF draw_page_items: 59 ms
    13:46:40  aktion: right (Seite 1)

Der Betrachter endete also SAUBER, back_to_frontend() lief, das
Frontend ZEICHNETE, und die Tastendruecke kamen an. Es war weder
abgestuerzt noch blockiert - der Login-Gruss stand nur im Bild und
blieb dort.

WARUM DAS VORHANDENE NACHFASSEN IHN NICHT FAND: _konsole_aufraeumen()
vergleicht die OBERSTEN 40 BILDZEILEN und tut nichts, wenn dort nichts
Fremdes steht. Nach einem Konsolenprogramm steht der Cursor aber nicht
mehr oben links; der Gruss landet irgendwo in der Mitte. Diese enge
Pruefung ist seit Build 157 Absicht - ein Neuaufbau bei JEDEM Blick
waere das Flackern aus Build 151.

DIE ABWAEGUNG IST HIER EINE ANDERE, und genau das wird hier geprueft:
nach einem Konsolenprogramm WISSEN wir, dass geschrieben wurde. Dann
ist Nachsehen keine Vorsicht, sondern eine unvollstaendige Messung
anstelle einer sicheren Antwort.

Ausfuehren:
    python3 tools/test_konsole_nachfassen.py
"""
import io
import os
import sys

_HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HIER)
import _harness as H                                    # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


H.set_screen(1280, 720)
FE = H.make_frontend(page=1)

gewischt = []
FE._konsole_wischen = lambda grund: gewischt.append(grund)

# Beide Puffer gleich: die alte Pruefung findet oben NICHTS - genau die
# Lage, in der der Nutzer haengenblieb (der Gruss stand weiter unten).
FE.fb.mm[:] = FE.fb.buf[:]

# ---------------------------------------------------------------------------
print("Test 1: ohne Konsolenprogramm bleibt alles wie bisher")
# ---------------------------------------------------------------------------
FE._f9_blind = False
FE._f9_aufraeumen_ab = H.NOW[0] - 1.0
FE._konsole_aufraeumen()
check("oben nichts Fremdes -> es wird NICHT aufgebaut",
      not gewischt,
      "sonst kaeme das Flackern aus Build 151 zurueck")

# ---------------------------------------------------------------------------
print()
print("Test 2: nach einem Konsolenprogramm wird gewischt - ohne Nachsehen")
# ---------------------------------------------------------------------------
del gewischt[:]
FE._f9_blind = True
FE._f9_grund = "/media/fat/docs/SNES/Manuals/F-ZERO.pdf"
FE._f9_aufraeumen_ab = H.NOW[0] - 1.0
FE._konsole_aufraeumen()
check("es wird gewischt, obwohl oben nichts steht",
      len(gewischt) == 1, str(gewischt))
check("und der Grund steht im Protokoll",
      gewischt and "F-ZERO" in gewischt[0], str(gewischt))
check("danach ist der Blindflug wieder aus",
      FE._f9_blind is False,
      "sonst wischte jedes weitere Nachfassen ebenfalls blind")
check("und der Termin ist verbraucht",
      FE._f9_aufraeumen_ab is None)

# ---------------------------------------------------------------------------
print()
print("Test 3: vor dem Termin passiert nichts")
# ---------------------------------------------------------------------------
del gewischt[:]
FE._f9_blind = True
FE._f9_aufraeumen_ab = H.NOW[0] + 5.0
FE._konsole_aufraeumen()
check("zu frueh wird nicht gewischt", not gewischt,
      "erst muss der Gruss da sein, sonst wischt man vor ihm her")
check("und der Blindflug bleibt stehen", FE._f9_blind is True)

# ---------------------------------------------------------------------------
print()
print("Test 4: _auf_konsole() stellt den Termin")
# ---------------------------------------------------------------------------
_q = io.open(H.FRONTEND_PY, encoding="utf-8").read()
_ak = _q[_q.index("    def _auf_konsole(self, wrapped, raw, name="):]
_ak = _ak[:_ak.index("\n    def ", 10)]
check("es kehrt ueber back_to_frontend() zurueck",
      "self.back_to_frontend()" in _ak)
check("und setzt danach den Blindflug",
      "self._f9_blind = True" in _ak,
      "ohne ihn greift wieder die 40-Zeilen-Pruefung")
check("mit einem eigenen, laengeren Termin",
      "NACHFASSEN_KONSOLE" in _ak,
      "ein Skript endet in einer Shell, die weiterlaeuft; ein "
      "Betrachter gibt die Konsole zurueck, und erst DANACH meldet "
      "sich der Login-Prozess")
check("und der ist laenger als der normale",
      FE.NACHFASSEN_KONSOLE > FE.NACHFASSEN_SEK,
      "%.1f gegen %.1f s" % (FE.NACHFASSEN_KONSOLE, FE.NACHFASSEN_SEK))
check("der Blindflug wird NUR dort gesetzt",
      _q.count("self._f9_blind = True") == 1,
      "zwei Stellen waeren zwei Wege zum selben Ziel")

# ---------------------------------------------------------------------------
print()
print("Test 5: die alte Pruefung ist nicht verschwunden")
# ---------------------------------------------------------------------------
# Sie gilt weiterhin fuer das eingespeiste F9 beim Start und fuer das
# F9 des Nutzers - dort IST das Nachsehen richtig, weil dort gar nicht
# feststeht, ob jemand geschrieben hat.
_ka = _q[_q.index("    def _konsole_aufraeumen(self):"):]
_ka = _ka[:_ka.index("\n    def ", 10)]
check("die 40-Zeilen-Pruefung steht noch da",
      "hoehe = min(40, self.fb.height)" in _ka)
check("und der Blindflug steht DAVOR",
      _ka.index("if blind:") < _ka.index("hoehe = min(40"),
      "sonst kaeme er nie dran")

# ---------------------------------------------------------------------------
print()
print("Test 6: waehrend eines Bildprogramms schweigt die Textkonsole")
# ---------------------------------------------------------------------------
# NUTZER-RUECKMELDUNG, NACHDEM Build 264 drauf war: "nach ein paar
# Sekunden, wenn ich mir die Anleitung ansehe, kommt der Login-Prompt."
# Also WAEHREND des Lesens - und damit konnte das Nachfassen aus 264
# es gar nicht richten, das raeumt erst auf, wenn der Betrachter
# beendet ist.
check("es gibt den Grafikmodus-Schalter am Konsolenweg",
      "def _auf_konsole(self, wrapped, raw, name=\"\", grafik=False):" in _q)
check("er benutzt KDSETMODE/KD_GRAPHICS",
      "self.KDSETMODE, self.KD_GRAPHICS" in _ak,
      "dieselbe Mechanik, mit der X11 die Textkonsole stilllegt - der "
      "Kernel malt dann keinen Text mehr in den Bildspeicher")
check("und nimmt ihn im finally wieder zurueck",
      "self.KDSETMODE, self.KD_TEXT" in _ak
      and _ak.index("finally:") < _ak.index("self.KDSETMODE, self.KD_TEXT"),
      "eine Konsole, die im Grafikmodus haengenbleibt, waere "
      "schlimmer als das Problem")
check("die Anleitung ruft MIT Grafikmodus",
      "grafik=True" in _q[_q.index("    def anleitung_zeigen(self):"):]
      [:_q[_q.index("    def anleitung_zeigen(self):"):].index("\n    def ", 10)])
check("ein Skript dagegen NICHT",
      "grafik" not in _q[_q.index("    def run_script(self, path"):]
      [:_q[_q.index("    def run_script(self, path"):].index("\n    def ", 10)],
      "ein Skript SOLL seine Ausgabe zeigen - im Grafikmodus waere "
      "der Bildschirm schwarz")
check("und es gibt einen Notausgang",
      "GRAFIKMODUS_AUS_FLAG" in _q and "anleitung_textmodus" in _q,
      "dieselbe Linie wie beim Schalter fuer die Konsolen-Mechanik")

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
