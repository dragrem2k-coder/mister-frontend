#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft den Abbruch und die Fortschrittsanzeige von "Miniaturen
vorbereiten" (Build 81).

AUSLOESER (Nutzer-Rueckmeldung, CRT-Modus):

    "wenn ich die Option Miniaturen erstellen starte, dann kommt der
     Fortschritts-Screen auf CRT und dieser ist nicht ganz lesbar, da
     steht nur 'Miniaturen werden' und 'jede taste bricht ab -
     gerechnetes bl'. Ausserdem kann ich durch Tastendruck nicht
     abbrechen, oder er reagiert gar nicht."

ZWEI FEHLER, EINE MELDUNG:

1. read_action(timeout=0) hat NIE etwas gelesen. Bei timeout=0 ist die
   Deadline sofort erreicht, und die Pruefung stand ganz am Anfang der
   Schleife - select() wurde also gar nicht erst aufgerufen. Der Abbruch
   konnte damit nicht funktionieren, und zwar lautlos, weil None auch
   der normale Rueckgabewert fuer "keine Taste" ist. Das ist der Test,
   der hier am meisten wert ist: er prueft die Zusage "kehrt sofort
   zurueck, sieht aber wirklich nach" statt nur "stuerzt nicht ab".

2. Die Fortschrittsanzeige zeichnete Titel und Abbruch-Hinweis mit
   fester Schriftgroesse. fb.text() schneidet still ab, was nicht passt
   - auf 320x240 waren das 18 bzw. 37 Zeichen bei 29 bzw. 51 Zeichen
   Text. Genau die vom Nutzer zitierten Bruchstuecke.

Ausfuehren:
    python3 tools/test_prewarm_abbruch.py
"""
import os
import struct
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import _harness as H                                  # noqa: E402

fm = H.fm
sys.path.insert(0, os.path.dirname(H.FRONTEND_PY))
import fe.input as I                                  # noqa: E402
import fe.translations as T                           # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


class FakeDev(object):
    """Gerade genug Geraet fuer read_action(): ein Dateideskriptor, aus
    dem sich lesen laesst, plus die beiden Felder, die _translate()
    anfasst."""

    def __init__(self, fd, path="/dev/input/fake"):
        self.fd = fd
        self.path = path
        self.name = "Testgeraet"
        self.is_kbd = True
        self.axis = {}
        self.axis_state = {}


def ereignis(code, value):
    return struct.pack(I.EVENT_FMT, 0, 0, I.EV_KEY, code, value)


def manager_mit_ereignis(code, value=1):
    """InputManager mit genau EINEM bereitliegenden Tastendruck."""
    inp = I.InputManager()
    inp.rescan = lambda: None            # keine echte Hardware suchen
    inp.last_scan = 1e18                 # und auch nicht danach fragen
    r, w = os.pipe()
    os.write(w, ereignis(code, value))
    inp.devices = {"/dev/input/fake": FakeDev(r)}
    return inp, r, w


# Irgendeine Taste, die im KEYMAP wirklich eine Aktion ausloest - der
# Test soll an einer belegten Taste haengen, nicht an einer geratenen.
TASTE = next(c for c, a in I.KEYMAP.items() if a in ("ok", "back", "up"))

print("Test 1: read_action(timeout=0) sieht wirklich nach")
inp, r, w = manager_mit_ereignis(TASTE)
try:
    act = inp.read_action(timeout=0)
    check("ein bereitliegender Tastendruck wird gemeldet",
          act is not None, "geliefert: %r" % (act,))
finally:
    os.close(r)
    os.close(w)

print()
print("Test 2: ohne Tastendruck kehrt der Poll trotzdem sofort zurueck")
# Die andere Haelfte der Zusage - haette der Fix stattdessen blockiert,
# wuerde "Miniaturen vorbereiten" bei jedem Eintrag haengen.
inp = I.InputManager()
inp.rescan = lambda: None
inp.last_scan = 1e18
r, w = os.pipe()
inp.devices = {"/dev/input/fake": FakeDev(r)}
try:
    import time
    t0 = time.monotonic()
    act = inp.read_action(timeout=0)
    dauer = time.monotonic() - t0
    check("liefert None", act is None, "geliefert: %r" % (act,))
    check("und braucht dafuer unter 50 ms", dauer < 0.05,
          "%.1f ms" % (dauer * 1000))
finally:
    os.close(r)
    os.close(w)

print()
print("Test 3: kein Text auf dem Fortschrittsbild wird abgeschnitten")
# Deutsch ist die laengere der beiden Sprachen - wenn es hier passt,
# passt Englisch erst recht.
for sprache in ("de", "en"):
    T.set_language(sprache)
    for w_, h_, name in ((320, 240, "CRT"), (640, 480, "480p"),
                         (1920, 1080, "HDMI")):
        H.set_screen(w_, h_)
        f = H.make_frontend(page=1)
        breite = w_ - 2 * (w_ * fm.OVERSCAN_X // 100)
        s = max(1, h_ // 360)

        titel = T.t("thumb_prewarm")
        titel_s = f._fit_scale(titel, breite, 2 * s)
        check("%s/%s: Titel passt (%d Zeichen)"
              % (name, sprache, len(titel)),
              len(titel) * 8 * titel_s <= breite,
              "%d von %d Pixeln" % (len(titel) * 8 * titel_s, breite))

        maxc = max(4, breite // (8 * s))
        zeilen = f._wrap_text(T.t("thumb_prewarm_cancel"), maxc)
        check("%s/%s: Abbruch-Hinweis passt in hoechstens 2 Zeilen"
              % (name, sprache),
              len(zeilen) <= 2 and all(len(z) <= maxc for z in zeilen),
              "%d Zeilen, laengste %d von %d Zeichen"
              % (len(zeilen), max(len(z) for z in zeilen), maxc))

print()
print("Test 4: das Fortschrittsbild laesst sich in beiden Aufloesungen "
      "zeichnen")
T.set_language("de")
for w_, h_, name in ((320, 240, "CRT"), (1920, 1080, "HDMI")):
    H.set_screen(w_, h_)
    f = H.make_frontend(page=1)
    try:
        # Mit und ohne Restzeit-Schaetzung - die verschiebt die Zeilen
        # darunter, und genau dort lag frueher der feste Abstand.
        f._draw_prewarm_progress(0, 2400, 0, H.NOW[0])
        f._draw_prewarm_progress(137, 2400, 42, H.NOW[0] - 90)
        f._draw_prewarm_progress(2399, 2400, 900, H.NOW[0] - 900)
        ok = True
        fehler = ""
    except Exception as e:                             # noqa: BLE001
        ok, fehler = False, repr(e)
    check("%s: zeichnet ohne Ausnahme" % name, ok, fehler)
    # Der letzte gezeichnete Text darf nicht unter den Bildrand rutschen.
    letzte_zeile = (h_ * fm.OVERSCAN_Y // 100) + 8 * 1 + 24 * max(1, h_ // 360) \
        + 10 * max(1, h_ // 360) + 66 * max(1, h_ // 360)
    check("%s: letzte Zeile bleibt im Bild" % name, letzte_zeile < h_,
          "y=%d von %d" % (letzte_zeile, h_))

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for f_ in fails:
        print("  -", f_)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
