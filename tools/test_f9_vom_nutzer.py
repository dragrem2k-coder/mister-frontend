#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Das F9 des NUTZERS wird bemerkt (Build 207).

DIE BEOBACHTUNG

    "mit f12 komme ich ins osd das klappt noch, druecke ich dann f9
     sollte das frontend ja wieder kommen, ich bleibe dann aber im
     login prompt haengen"

und, entscheidend nachgeliefert:

    "druecke ich im login prompt nochmal f12 bin ich wieder im
     frontend"

WAS DER EIGENE QUELLTEXT DAZU SEIT BUILD 150 SAGT, am Ende von
_konsole_sichern():

    "Das eingespeiste F9 erreicht nicht nur MiSTer, sondern auch den
     Login-Prozess auf tty1. Der wacht davon auf und schreibt
     'Welcome to MiSTer ... login:' mitten in unser Bild."

Fuer das EIGENE F9 wird deshalb hinterher aufgeraeumt. Beim F9 des
Nutzers passiert dasselbe - nur hat es bisher niemand mitbekommen,
weil KEY_F9 in der KEYMAP auf None liegt (MiSTer braucht die Taste)
und der Tastendruck das Frontend damit ueberhaupt nicht erreichte.

Im Log des Nutzers stehen waehrend der ganzen F12/F9-Folge NULL
Zeilen, weder von der Dauerwache noch vom Bildwaechter. Zwei
Erklaerungen, zwei verschiedene Abhilfen - siehe den Docstring von
_f9_nutzer_behandeln(). Dieser Build setzt das Aufraeumen an (Fall A)
und LOGGT die Zahl der gefundenen Bildpunkte, damit die naechste
Log-Zeile zwischen A und B entscheidet, statt dass noch einmal jemand
raet. In den Builds 146-149 bin ich bei genau dieser Fehlersuche
viermal falsch abgebogen, weil aus einer Beobachtung eine Ursache
wurde.

WAS DIESER TEST ABSICHERT

  - dass ein F9 auf der Tastatur im Frontend weiterhin KEINE Aktion
    ausloest (es muss fuer MiSTer frei bleiben),
  - dass es trotzdem vermerkt wird,
  - dass das Aufraeumen genau EINMAL je Tastendruck angesetzt wird -
    nicht in jeder Leerlaufrunde neu, das waere das Flackern aus
    Build 157,
  - dass bei unveraendertem Bild NICHT neu aufgebaut, aber die Zahl
    der Bildpunkte geloggt wird,
  - dass bei fremdem Text im Bild gewischt wird,
  - dass alles am Schalter konsole_mechanik() haengt (Build 167).
"""
import inspect
import os
import sys

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
sys.path.insert(0, _HIER)
import _harness as H                                     # noqa: E402

fm = H.fm
NOW = H.NOW

fails = []


def check(name, ok, extra=""):
    print("  %s %s%s" % ("OK  " if ok else "FEHL", name,
                         ("  (%s)" % extra) if extra and not ok else ""))
    if not ok:
        fails.append(name + ((" - " + extra) if extra else ""))


# ---------------------------------------------------------------------------
print("Test 1: F9 bleibt fuer das Frontend wirkungslos")
# ---------------------------------------------------------------------------
from fe import input as I                                 # noqa: E402

check("KEY_F9 ist in der KEYMAP auf None", I.KEYMAP.get(I.KEY_F9) is None,
      repr(I.KEYMAP.get(I.KEY_F9)))
check("und der Grund steht im Quelltext",
      "F9 ist bei MiSTer" in inspect.getsource(I))

# ---------------------------------------------------------------------------
print()
print("Test 2: _translate() vermerkt das F9 trotzdem")
# ---------------------------------------------------------------------------


class Geraet(object):
    path = "/dev/input/event0"


class Mgr(object):
    """Nur die Felder, die _translate() im F9-Zweig anfasst."""
    f9_gesehen = 0.0
    held = None
    _select_down = {}
    _select_kombiniert = False

    def _hold(self, *a):
        pass

    def _release(self, *a):
        pass


m = Mgr()
NOW[0] = 5000.0
act = I.InputManager._translate(m, Geraet(), I.EV_KEY, I.KEY_F9, 1)
check("gibt keine Aktion zurueck", act is None, repr(act))
check("hat den Zeitpunkt vermerkt", m.f9_gesehen == 5000.0,
      repr(m.f9_gesehen))

m2 = Mgr()
I.InputManager._translate(m2, Geraet(), I.EV_KEY, I.KEY_F9, 0)
check("das Loslassen vermerkt nichts", m2.f9_gesehen == 0.0,
      repr(m2.f9_gesehen))

check("f9_gesehen ist eine Klassenvorgabe (Attrappen fallen nicht "
      "darueber)", I.InputManager.f9_gesehen == 0.0)

# ---------------------------------------------------------------------------
print()
print("Test 3: genau EINMAL je Tastendruck angesetzt")
# ---------------------------------------------------------------------------
NOW[0] = 6000.0
fe = H.make_frontend(page=1)
fe.inp = Mgr()

fe._f9_aufraeumen_ab = None
fe._f9_nutzer_letzte = 0.0
fe._f9_nutzer_behandeln()
check("ohne Tastendruck wird nichts angesetzt", fe._f9_aufraeumen_ab is None)

fe.inp.f9_gesehen = 6000.0
fe._f9_nutzer_behandeln()
check("nach dem Tastendruck steht ein Zeitpunkt",
      fe._f9_aufraeumen_ab == 6000.0 + fm.Frontend.F9_NUTZER_WARTEN,
      repr(fe._f9_aufraeumen_ab))
check("und der Grund ist vermerkt", fe._f9_grund == "Nutzer", fe._f9_grund)
check("dieselben 0,4 s wie beim eigenen F9",
      fm.Frontend.F9_NUTZER_WARTEN == 0.4)

# Zweite, dritte, vierte Leerlaufrunde: derselbe Tastendruck darf nicht
# wieder und wieder ansetzen - genau das waere das Flackern aus 157.
fe._f9_aufraeumen_ab = None
for _ in range(3):
    fe._f9_nutzer_behandeln()
check("derselbe Tastendruck setzt NICHT erneut an",
      fe._f9_aufraeumen_ab is None, repr(fe._f9_aufraeumen_ab))

# Ein neuer Tastendruck aber schon.
fe.inp.f9_gesehen = 6001.5
fe._f9_nutzer_behandeln()
check("ein neuer Tastendruck setzt wieder an",
      fe._f9_aufraeumen_ab == 6001.5 + 0.4, repr(fe._f9_aufraeumen_ab))

# Eine Attrappe ohne das Feld darf nichts zerlegen.
class Ohne(object):
    pass


fe.inp = Ohne()
fe._f9_aufraeumen_ab = None
fe._f9_nutzer_behandeln()
check("eine Eingabe-Attrappe ohne f9_gesehen stoert nicht",
      fe._f9_aufraeumen_ab is None)

# ---------------------------------------------------------------------------
print()
print("Test 4: unveraendertes Bild -> kein Aufbau, aber eine Log-Zeile")
# ---------------------------------------------------------------------------
zeilen = []
_echt_log = fm.LOG
_echt_wischen = fm.Frontend._konsole_wischen
gewischt = []
try:
    fm.LOG = lambda *a: zeilen.append(a[0] % a[1:] if len(a) > 1 else a[0])
    fm.Frontend._konsole_wischen = lambda self, grund: gewischt.append(grund)

    fe = H.make_frontend(page=1)
    fe.inp = Mgr()
    fe.draw()                       # mm und buf gleichziehen
    fe.fb.mm[:] = fe.fb.buf[:]
    NOW[0] = 7000.0
    fe.inp.f9_gesehen = 7000.0
    fe._f9_nutzer_letzte = 0.0
    fe._f9_nutzer_behandeln()
    NOW[0] = 7000.0 + 0.5
    zeilen[:] = []
    gewischt[:] = []
    fe._konsole_aufraeumen()
    check("es wird NICHT neu aufgebaut", not gewischt, repr(gewischt))
    befund = [z for z in zeilen if "F9 vom Nutzer" in z]
    check("aber die Zahl der Bildpunkte steht im Log", len(befund) == 1,
          repr(zeilen))
    if befund:
        print("    " + befund[0])
        check("die Schwelle wird mitgenannt",
              str(fm.Frontend.KONSOLE_WACHE_MINDEST) in befund[0])

    # ---- und jetzt mit fremdem Text im Bild ----
    fe.fb.mm[:] = fe.fb.buf[:]
    breite = fe.fb.stride
    for y in range(6):
        for x in range(0, 900, 4):
            off = y * breite + x
            fe.fb.mm[off:off + 4] = b"\xff\xff\xff\xff"
    NOW[0] = 7100.0
    fe.inp.f9_gesehen = 7100.0
    fe._f9_nutzer_behandeln()
    NOW[0] = 7100.0 + 0.5
    zeilen[:] = []
    gewischt[:] = []
    fe._konsole_aufraeumen()
    check("fremder Text -> es wird gewischt", len(gewischt) == 1,
          repr(gewischt))
    check("und der Grund steht dabei",
          bool(gewischt) and "Nutzer" in gewischt[0],
          repr(gewischt))

    # Der Grund faellt danach auf "eingespeist" zurueck, sonst wuerde
    # das naechste eigene F9 als Nutzer-F9 geloggt.
    check("der Grund ist danach zurueckgesetzt",
          fe._f9_grund == "eingespeist", fe._f9_grund)
finally:
    fm.LOG = _echt_log
    fm.Frontend._konsole_wischen = _echt_wischen

# ---------------------------------------------------------------------------
print()
print("Test 5: alles haengt am Schalter konsole_mechanik() (Build 167)")
# ---------------------------------------------------------------------------
q = inspect.getsource(fm.Frontend.next_action)
i_schalter = q.find("if self.konsole_mechanik():")
i_f9 = q.find("self._f9_nutzer_behandeln()")
i_auf = q.find("self._konsole_aufraeumen()")
check("der Aufruf steht im Quelltext", i_f9 > 0)
check("hinter dem Schalter", 0 < i_schalter < i_f9)
check("und VOR dem Aufraeumen - sonst greift es erst eine Runde "
      "spaeter", 0 < i_f9 < i_auf, "%d / %d" % (i_f9, i_auf))
# Wirklich im selben Block, nicht nur irgendwo dahinter: gleiche
# Einrueckung wie _konsole_aufraeumen().
zl = q[:i_f9].split("\n")[-1]
zl2 = q[:i_auf].split("\n")[-1]
check("in genau demselben Block", zl == zl2, "%r gegen %r" % (zl, zl2))

# ---------------------------------------------------------------------------
print()
print("Test 6: die Nutzer-Beobachtung ist festgehalten")
# ---------------------------------------------------------------------------
qd = inspect.getsource(fm.Frontend._f9_nutzer_behandeln)
check("das F12 aus dem Login-Prompt steht dabei",
      "nochmal\n        f12" in qd or "nochmal f12" in qd
      or "nochmal\n         f12" in qd, "der entscheidende Hinweis fehlt")
check("beide Erklaerungen stehen da, A und B",
      "A)" in qd and "B)" in qd)
check("und dass hier NICHT geraten wird",
      "146-149" in qd)

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
