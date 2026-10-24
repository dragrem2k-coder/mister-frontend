#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft die Tastenwiederholung mit der ECHTEN InputManager-Logik.

Hintergrund (Nutzer-Rueckmeldungen, beide hier festgehalten):
  1. "wenn ich nach unten gedrueckt halte und dann wieder nach oben
     druecke bleibt der kurz haengen" - beim Richtungswechsel MITTEN im
     Scrollen lief die volle Anlaufsperre (REPEAT_DELAY) erneut an.
  2. "der Cursor bewegt sich nicht und dann kommt auf einmal die
     ploetzliche Bewegung" - nach 'Zurueck'/'OK' lief eine Geister-
     Wiederholung der vorher gehaltenen Richtungstaste weiter.

Getestet werden ausschliesslich die Zustandsuebergaenge der Wiederhol-
Steuerung (_hold/_release/_cancel_repeat und der Wiederhol-Zweig aus
read_action) - dafuer werden keine echten Eingabegeraete gebraucht.

Ausfuehren:
    python3 tools/test_input_repeat.py
"""
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_FRONTEND_DIR = os.path.dirname(
    os.environ.get("FRONTEND_PY",
                   os.path.join(os.path.dirname(_HERE), "frontend",
                                "frontend.py")))
sys.path.insert(0, _FRONTEND_DIR)

import fe.input as I          # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


im = I.InputManager.__new__(I.InputManager)   # ohne Geraete-Scan
im.devices = {}
im.want_grab = False
im.last_scan = 0.0
im.held = None
im._last_repeat_time = 0.0
im._last_repeat_act = None
im._last_repeat_iv = I.REPEAT_INTERVAL
im._last_input_mtime = None
# Build 93: ohne Messwerte gelten die festen Boeden - genau der
# Zustand, den dieser Test prueft.
im._zeichenzeit = {}

KID_DOWN = ("/dev/input/event0", "key", 108)
KID_UP = ("/dev/input/event0", "key", 103)
KID_RIGHT = ("/dev/input/event0", "key", 106)


def fire_repeat():
    """Bildet den Wiederhol-Zweig aus read_action() nach."""
    kid, act, _t, iv = im.held
    iv = max(I.REPEAT_FLOOR, iv * 0.85)
    im.held = (kid, act, time.monotonic() + iv, iv)
    im._last_repeat_time = time.monotonic()
    im._last_repeat_act = act
    im._last_repeat_iv = iv
    return act


print("Test 1: einzelner Tastendruck aus dem Stand -> volle Anlaufsperre")
im._last_repeat_act = None
t0 = time.monotonic()
im._hold(KID_DOWN, "down")
delay = im.held[2] - t0
check("Anlaufzeit betraegt %.0f ms (erwartet %.0f ms)"
      % (delay * 1000, I.REPEAT_DELAY * 1000),
      abs(delay - I.REPEAT_DELAY) < 0.02)

print()
print("Test 2: Richtungswechsel MITTEN im Scrollen -> kurze Anlaufzeit")
for _ in range(8):
    fire_repeat()
check("Dauergeschwindigkeit erreicht: %.0f ms" % (im._last_repeat_iv * 1000),
      abs(im._last_repeat_iv - I.REPEAT_FLOOR) < 1e-6)
t0 = time.monotonic()
im._hold(KID_UP, "up")            # Richtungswechsel
delay = im.held[2] - t0
check("Anlaufzeit nur noch %.0f ms (statt %.0f ms)"
      % (delay * 1000, I.REPEAT_DELAY * 1000),
      abs(delay - I.REPEAT_REVERSE_DELAY) < 0.02)
check("erreichtes Tempo bleibt erhalten (%.0f ms)" % (im.held[3] * 1000),
      abs(im.held[3] - I.REPEAT_FLOOR) < 1e-6)
check("Aktion ist jetzt 'up'", im.held[1] == "up")

print()
print("Test 3: Achswechsel (runter -> rechts) gilt NICHT als Richtungswechsel")
im._last_repeat_act = "down"
im._last_repeat_time = time.monotonic()
im._last_repeat_iv = I.REPEAT_FLOOR
t0 = time.monotonic()
im._hold(KID_RIGHT, "right")
delay = im.held[2] - t0
check("volle Anlaufsperre %.0f ms" % (delay * 1000),
      abs(delay - I.REPEAT_DELAY) < 0.02)

print()
print("Test 4: nach einer Scroll-Pause wieder volle Anlaufsperre")
im._last_repeat_act = "down"
im._last_repeat_time = time.monotonic() - (I.REPEAT_CONTINUE_WINDOW + 0.2)
t0 = time.monotonic()
im._hold(KID_UP, "up")
delay = im.held[2] - t0
check("volle Anlaufsperre %.0f ms" % (delay * 1000),
      abs(delay - I.REPEAT_DELAY) < 0.02)

print()
print("Test 5: Geister-Wiederholung nach 'Zurueck'/'OK' wird abgebrochen")
im._last_repeat_act = None
im._hold(KID_DOWN, "down")
for _ in range(5):
    fire_repeat()
check("Wiederholung laeuft (held gesetzt)", im.held is not None)
im._cancel_repeat()               # das macht jetzt jede nicht-wiederholbare Aktion
check("held ist danach geloescht", im.held is None)
check("Merker fuer Richtungswechsel ebenfalls zurueckgesetzt",
      im._last_repeat_act is None)
t0 = time.monotonic()
im._hold(KID_UP, "up")
delay = im.held[2] - t0
check("naechste Richtungstaste laeuft wieder normal an (%.0f ms)"
      % (delay * 1000),
      abs(delay - I.REPEAT_DELAY) < 0.02)

print()
print("Test 6: _release() verhaelt sich unveraendert")
im._last_repeat_act = None
im._hold(KID_DOWN, "down")
im._release(("/dev/input/event0", "key", 999))    # andere Taste
check("fremde Taste loest nichts aus", im.held is not None)
im._release(KID_DOWN)
check("eigene Taste loescht die Wiederholung", im.held is None)

print()
print("Test 7: Seiten-Spruenge (links/rechts) haben eine eigene, "
      "langsamere Untergrenze")
check("Seiten-Untergrenze (%.0f ms) ist groesser als die Zeilen-Untergrenze "
      "(%.0f ms)" % (I.REPEAT_FLOOR_PAGE * 1000, I.REPEAT_FLOOR * 1000),
      I.REPEAT_FLOOR_PAGE > I.REPEAT_FLOOR)
check("_repeat_floor('left') liefert die Seiten-Untergrenze",
      abs(im._repeat_floor("left") - I.REPEAT_FLOOR_PAGE) < 1e-9)
check("_repeat_floor('down') liefert die Zeilen-Untergrenze",
      abs(im._repeat_floor("down") - I.REPEAT_FLOOR) < 1e-9)
print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for f in fails:
        print("   ", f)
    sys.exit(1)
print("Alle Tests bestanden.")


# ---------------------------------------------------------------------
print()
print("Test 8: welche Richtungen 'Seite' bedeuten, ist umstellbar (Build 136)")
# Nutzer-Rueckmeldung: "das nach links und rechts scrollen kann trotzdem
# schneller passieren, wenn ich die Richtung gedrueckt halte."
#
# Der langsame Boden (0.25 s) ist richtig, wenn ein Druck eine ganze
# Seite blaettert. Bis Build 135 galt er FEST fuer links/rechts - auch
# im Raster, wo links/rechts nur eine Kachel weitergeht und damit die
# billigste Bewegung ueberhaupt ist. Vier Schritte je Sekunde fuer zwei
# neu gezeichnete Kacheln.
#
# Hier wird nur die EINGABESEITE geprueft: dass sich die Menge
# umstellen laesst und der Boden ihr folgt. Dass das Frontend je
# Ansicht die richtige Menge meldet, prueft tools/test_ansichten.py -
# dafuer braucht es den Pruefstand, den diese Datei bewusst nicht laedt.
im.seiten_aktionen_setzen(("up", "down"))
check("hoch/runter wird zur Seitenbewegung",
      im._repeat_floor("up") == I.REPEAT_FLOOR_PAGE,
      "%.2f" % im._repeat_floor("up"))
check("und links/rechts damit zur normalen",
      im._repeat_floor("left") == I.REPEAT_FLOOR,
      "%.2f" % im._repeat_floor("left"))
im.seiten_aktionen_setzen(())
check("ohne Seitenbewegung sind beide schnell",
      im._repeat_floor("left") == I.REPEAT_FLOOR
      and im._repeat_floor("up") == I.REPEAT_FLOOR)
im.seiten_aktionen_setzen(I.PAGE_ACTIONS)
check("und zurueck auf die Vorgabe",
      im._repeat_floor("left") == I.REPEAT_FLOOR_PAGE)

# Ein Objekt OHNE das Feld (aeltere Fassung, oder wie hier ueber
# __new__ gebaut) muss weiterhin rechnen koennen.
_roh = I.InputManager.__new__(I.InputManager)
_roh._zeichenzeit = {}
check("ohne das Feld gilt die Vorgabe",
      _roh._repeat_floor("left") == I.REPEAT_FLOOR_PAGE
      and _roh._repeat_floor("up") == I.REPEAT_FLOOR)


# ---------------------------------------------------------------------------
print()
print("Build 276: eine FAELLIGE Wiederholung wird nicht mehr ausgehungert")
# ---------------------------------------------------------------------------
# NUTZERMELDUNG: "das Scrollen bei gedrueckter Taste ist totaler Mist,
# lagt ohne Ende und stockt" - bei 291 ms Latenz im Mittel und KEINER
# einzigen RUCKLER-Zeile. Wir waren also nicht beschaeftigt, sondern
# nicht abrufbar.
#
# URSACHE: read_action() hat die Warteschlange bevorzugt ("erst leeren,
# dann Repeat"). Eine gehaltene Taste erzeugt aber dauernd Ereignisse,
# die GAR KEINE AKTION sind - die Auto-Wiederholung der Tastatur
# (value==2, in _translate() bewusst verworfen), dazu EV_MSC und
# EV_SYN, bei einem Pad die unveraenderten Achsen. Jedes davon schickte
# die Schleife zurueck an den Anfang, ohne den faelligen Schritt
# auszuliefern.
#
# GEPRUEFT WIRD MIT ECHTEN DATEIDESKRIPTOREN, nicht mit einer Attrappe
# von select(): die Frage ist ja genau, was die Schleife tut, wenn
# select() dauerhaft "da ist was" sagt. Eine Pipe voller EV_SYN ist
# dafuer der ehrlichste Pruefstand - sie liefert echte Bytes, und
# _translate() macht daraus zu Recht keine Aktion.
import struct as _struct                                     # noqa: E402


class _FakeDev(object):
    def __init__(self, fd, pfad):
        self.fd = fd
        self.path = pfad
        self.axis = {}
        self.axis_state = {}
        # Build 296: eine Attrappe soll aussehen wie das Echte. Dieses
        # Feld fehlte, und _rescan_takt() (Build 296) hat die Attrappe
        # damit mit einem AttributeError abgeschossen - mitten im
        # Eingabeweg. Die Funktion faengt das jetzt zwar ab, aber ein
        # unvollstaendiges Nachbau-Objekt bleibt eine Falle fuer die
        # naechste Erweiterung: dort stand der Fehler des Codes, hier
        # steht der Fehler des Tests.
        #
        # False, nicht True: dieses Geraet SPIELT ein Pad, deshalb
        # liegen im Test Tastenereignisse darin.
        self.is_kbd = False


def _bau_mit_stroem(anzahl):
    """InputManager mit einer Pipe, in der <anzahl> EV_SYN liegen."""
    r, w = os.pipe()
    roh = _struct.pack(I.EVENT_FMT, 0, 0, I.EV_SYN, 0, 0)
    os.write(w, roh * anzahl)
    os.close(w)                 # Leser sieht die Bytes, dann EOF
    m = I.InputManager.__new__(I.InputManager)
    m.devices = {"/dev/input/event9": _FakeDev(r, "/dev/input/event9")}
    m.want_grab = False
    m.last_scan = time.monotonic()      # kein rescan() in diesem Test
    m.held = None
    m._last_repeat_time = 0.0
    m._last_repeat_act = None
    m._last_repeat_iv = I.REPEAT_INTERVAL
    m._last_input_mtime = None
    m._zeichenzeit = {}
    m.seiten_aktionen = set()
    return m, r


# 400 aktionslose Ereignisse: so lange sagt select() ununterbrochen
# "da ist was". Die Wiederholung ist seit einer Zehntelsekunde faellig.
im2, _fd = _bau_mit_stroem(400)
im2.held = (KID_DOWN, "down", time.monotonic() - 0.10, I.REPEAT_FLOOR)
_t0 = time.perf_counter()
_act = im2.read_action(timeout=1.0)
_dauer = time.perf_counter() - _t0
os.close(_fd)
check("der faellige Schritt kommt, trotz Dauerstrom aus dem Geraet",
      _act == "down", repr(_act) + " nach %.0f ms" % (_dauer * 1000))
check("und er kommt sofort, nicht erst nach der Frist",
      _dauer < 0.5, "%.0f ms von 1000 ms Frist" % (_dauer * 1000))
check("gezaehlt wird, wie oft die alte Regel ihn aufgehalten haette",
      getattr(im2, "repeat_durchgelassen", 0) >= 1,
      "%d x - ohne diese Zahl liesse sich die Ursache nicht belegen"
      % getattr(im2, "repeat_durchgelassen", 0))

# Die Gegenprobe: ohne faellige Wiederholung bleibt es beim alten
# Verhalten - aktionslose Ereignisse werden geleert und liefern nichts.
im3, _fd3 = _bau_mit_stroem(50)
im3.held = None
check("ohne faelligen Schritt liefert ein Dauerstrom weiter nichts",
      im3.read_action(timeout=0.2) is None)
os.close(_fd3)

# UND DAS LOSLASSEN DARF NIE VERLOREN GEHEN - das war der Grund fuer
# die alte Regel, und daran aendert sich nichts: ein echtes Ereignis
# wird in derselben Runde uebersetzt und hat weiter Vorrang vor der
# Wiederholung.
_r4, _w4 = os.pipe()
os.write(_w4, _struct.pack(I.EVENT_FMT, 0, 0, I.EV_KEY, 103, 1))
os.close(_w4)
im4 = I.InputManager.__new__(I.InputManager)
im4.devices = {"/dev/input/event9": _FakeDev(_r4, "/dev/input/event9")}
im4.want_grab = False
im4.last_scan = time.monotonic()
im4.held = (KID_DOWN, "down", time.monotonic() - 0.10, I.REPEAT_FLOOR)
im4._last_repeat_time = 0.0
im4._last_repeat_act = None
im4._last_repeat_iv = I.REPEAT_INTERVAL
im4._last_input_mtime = None
im4._zeichenzeit = {}
im4.seiten_aktionen = set()
check("ein ECHTES Ereignis hat weiter Vorrang vor der Wiederholung",
      im4.read_action(timeout=0.5) == "up",
      "sonst koennte ein Loslassen hinter einem Schritt verschwinden")
os.close(_r4)

# ---------------------------------------------------------------------------
print()
print("Build 277: das Loslassen darf nicht hinter dem Buendel liegenbleiben")
# ---------------------------------------------------------------------------
# NUTZERMELDUNG ZU BUILD 276: "wenn ich nach unten gedrueckt halte und
# dann nach 2-3 Sekunden loslasse, scrollt er von alleine weiter, bis
# ich eine andere Richtung druecke."
#
# URSACHE: 276 hat den faelligen Schritt durchgelassen, SOBALD ein
# Ereignis gelesen war - und jede Runde liest nur EIN Ereignis je
# Geraet. Eine gehaltene Taste liefert aber Buendel (EV_MSC, EV_KEY mit
# value==2, EV_SYN), und das Loslassen steht hinten darin. Wer nach dem
# ersten Ereignis abbiegt, laesst den Rest liegen - und damit die
# Wiederholung ewig stehen.
#
# DAS IST DER TEST, DER IN 276 GEFEHLT HAT. Er haengt an der Zusage,
# nicht an der Mechanik: nach einer Abfrage, in deren Warteschlange ein
# Loslassen lag, darf nichts mehr gehalten sein.
_r5, _w5 = os.pipe()
for _ev in ((I.EV_SYN, 0, 0),              # Buendel der Auto-Wiederholung
            (I.EV_KEY, 108, 2),            # ... in _translate() verworfen
            (I.EV_SYN, 0, 0),
            (I.EV_KEY, 108, 0)):           # UND DANN DAS LOSLASSEN
    os.write(_w5, _struct.pack(I.EVENT_FMT, 0, 0, *_ev))
os.close(_w5)
im5 = I.InputManager.__new__(I.InputManager)
im5.devices = {"/dev/input/event9": _FakeDev(_r5, "/dev/input/event9")}
im5.want_grab = False
im5.last_scan = time.monotonic()
im5.held = (("/dev/input/event9", "key", 108), "down", time.monotonic() - 0.10, I.REPEAT_FLOOR)
im5._last_repeat_time = 0.0
im5._last_repeat_act = None
im5._last_repeat_iv = I.REPEAT_INTERVAL
im5._last_input_mtime = None
im5._zeichenzeit = {}
im5.seiten_aktionen = set()
_ergebnis = im5.read_action(timeout=0.2)
os.close(_r5)
check("nach dem Loslassen wird nichts mehr gehalten",
      im5.held is None,
      "sonst scrollt die Liste von alleine weiter - genau die "
      "Rueckmeldung zu Build 276")
check("und es kommt kein Schritt mehr aus der Wiederholung",
      _ergebnis is None, repr(_ergebnis))

# Die Gegenprobe zu beidem: liegt KEIN Loslassen im Buendel, kommt der
# faellige Schritt weiterhin sofort. Die Behebung darf die Behebung aus
# 276 nicht zuruecknehmen.
_r6, _w6 = os.pipe()
for _ev in ((I.EV_SYN, 0, 0), (I.EV_KEY, 108, 2), (I.EV_SYN, 0, 0)):
    os.write(_w6, _struct.pack(I.EVENT_FMT, 0, 0, *_ev))
os.close(_w6)
im6 = I.InputManager.__new__(I.InputManager)
im6.devices = {"/dev/input/event9": _FakeDev(_r6, "/dev/input/event9")}
im6.want_grab = False
im6.last_scan = time.monotonic()
im6.held = (("/dev/input/event9", "key", 108), "down", time.monotonic() - 0.10, I.REPEAT_FLOOR)
im6._last_repeat_time = 0.0
im6._last_repeat_act = None
im6._last_repeat_iv = I.REPEAT_INTERVAL
im6._last_input_mtime = None
im6._zeichenzeit = {}
im6.seiten_aktionen = set()
check("ohne Loslassen im Buendel kommt der Schritt weiter sofort",
      im6.read_action(timeout=0.5) == "down",
      "die Behebung aus Build 276 bleibt in Kraft")
os.close(_r6)

check("die Leer-Obergrenze steht als benannte Konstante da",
      I.InputManager.LEEREN_MAX >= 8,
      "%d Runden - weit mehr als jedes Buendel, und eine harte Grenze "
      "gegen einen Strom, der nie abreisst" % I.InputManager.LEEREN_MAX)

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for f_ in fails:
        print("  -", f_)
    sys.exit(1)
print("Alle Tests bestanden.")
