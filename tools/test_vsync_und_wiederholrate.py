#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft die beiden Latenz-Aenderungen aus Build 93.

AUSLOESER (Nutzer, zwei Nachrichten):

  1. "Auf jeden Fall muss die Latenz deutlich besser werden und noch
     schneller von der Bedienung und Scrollen."
  2. "Ich habe schnelles Scrollen eigentlich standardmaessig an - und
     das fuehlt sich manchmal komisch an, bitte beruecksichtigen."

Punkt 2 hat die Richtung geaendert: der Schalter "Schnelles Scrollen"
war bei ihm die ganze Zeit AN. Alles, was ihm bisher als Beschleunigung
vorgeschlagen wurde, lief bei ihm also laengst - und was er spuerte,
war die Kehrseite: das Auslassen des Vsync-Wartens galt bis Build 92
pauschal fuer JEDE Kopie, auch fuer den kompletten Bildaufbau. Ein
Bildriss in einem zwei Zeilen hohen Streifen sieht niemand; derselbe
Riss quer durch ein 1080-Zeilen-Bild sieht jeder.

  AENDERUNG A (Item 2): das Auslassen haengt jetzt zusaetzlich an der
  GROESSE des kopierten Bandes - siehe VSYNC_SKIP_MAX_ANTEIL und
  Frontend._vsync_ueberspringen(). Vollbild = immer warten.

  AENDERUNG B (Item 3): die Wiederholrate der gehaltenen Richtungstaste
  war eine feste Zahl (12,5/s). Gemessen kostet ein Bildaufbau zwischen
  3 ms (CRT, leichter Pfad) und 110 ms (HDMI, voller Aufbau mit Cover) -
  die feste Zahl war also je nach Lage gleichzeitig zu langsam UND zu
  schnell. Zu schnell heisst: es kommen mehr Schritte herein als
  gezeichnet werden koennen, der Ueberschuss staut sich, und der Stau
  ist genau das, was man als Lag wahrnimmt. Der Boden richtet sich
  jetzt nach der tatsaechlich gemessenen Zeichendauer - siehe
  InputManager.zeichenzeit_melden()/_repeat_floor() in fe/input.py.

Ausfuehren:
    python3 tools/test_vsync_und_wiederholrate.py
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import _harness as H                                  # noqa: E402

fm = H.fm
sys.path.insert(0, os.path.dirname(H.FRONTEND_PY))
import fe.input as I                                  # noqa: E402
import fe.settings as S                               # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


def frontend_mit_schnellem_scrollen(w, h):
    """Frontend im Zustand des Nutzers: Schalter AN und gerade eben
    eine Eingabe gehabt (also innerhalb FAST_SCROLL_WINDOW)."""
    H.set_screen(w, h)
    f = H.make_frontend(page=1)
    fm.fast_scroll_enabled = lambda: True
    f._last_input_time = fm.time.monotonic()
    return f


print("Test 1: Vollbild wartet IMMER auf Vsync - auch bei schnellem"
      " Scrollen")
# Der eigentliche Kern der Rueckmeldung "fuehlt sich komisch an".
for w, h, name in ((320, 240, "CRT"), (1920, 1080, "HDMI")):
    f = frontend_mit_schnellem_scrollen(w, h)
    check("%s: _vsync_ueberspringen(None) ist False" % name,
          f._vsync_ueberspringen(None) is False)
    check("%s: _scroll_skip_vsync() meldet weiterhin True" % name,
          f._scroll_skip_vsync() is True,
          "(die Frage 'wird gerade gescrollt?' bleibt unveraendert)")

print("Test 2: schmale Baender ueberspringen das Warten weiterhin")
# Die Ersparnis, die Build 76-80 gebracht haben, muss erhalten bleiben -
# sonst waere die Korrektur ein reiner Rueckschritt.
for w, h, name in ((320, 240, "CRT"), (1920, 1080, "HDMI")):
    f = frontend_mit_schnellem_scrollen(w, h)
    grenze = h * fm.VSYNC_SKIP_MAX_ANTEIL
    check("%s: Band von 2 Zeilen wird uebersprungen" % name,
          f._vsync_ueberspringen(2) is True)
    check("%s: Band genau auf der Grenze (%d Zeilen) wird uebersprungen"
          % (name, int(grenze)),
          f._vsync_ueberspringen(int(grenze)) is True)
    check("%s: Band knapp ueber der Grenze wartet" % name,
          f._vsync_ueberspringen(int(grenze) + 2) is False)
    check("%s: volle Bildhoehe wartet" % name,
          f._vsync_ueberspringen(h) is False)

print("Test 3: die gemessenen ECHTEN Bandhoehen liegen nicht am Rand")
# Wichtig gegen einen Grenzfall, der zufaellig kippt: der leichte
# Navigations-Pfad muss klar UNTER der Schwelle liegen, der volle
# Aufbau klar darueber. Gemessen (fruehere Profiling-Runde):
#   HDMI  114 von 1080 Zeilen (leicht)  /  909 (voll)
#   CRT    32 von  240 Zeilen (leicht)  /  195 (voll)
for h, leicht, voll, name in ((240, 32, 195, "CRT"),
                              (1080, 114, 909, "HDMI")):
    grenze = h * fm.VSYNC_SKIP_MAX_ANTEIL
    check("%s: leichtes Band %d Zeilen liegt deutlich unter %d"
          % (name, leicht, int(grenze)), leicht < grenze * 0.7,
          "(%.0f%% der Bildhoehe)" % (100.0 * leicht / h))
    check("%s: volles Band %d Zeilen liegt deutlich ueber %d"
          % (name, voll, int(grenze)), voll > grenze * 1.5,
          "(%.0f%% der Bildhoehe)" % (100.0 * voll / h))

print("Test 4: bei ausgeschaltetem Schalter aendert sich gar nichts")
# Wer "Schnelles Scrollen" aus hat, bekommt weiterhin ueberall Vsync -
# die neue Bandgroessen-Regel darf daran nicht ruetteln.
H.set_screen(1920, 1080)
f = H.make_frontend(page=1)
fm.fast_scroll_enabled = lambda: False
f._last_input_time = fm.time.monotonic()
check("Schalter aus: schmales Band wartet trotzdem",
      f._vsync_ueberspringen(2) is False)
check("Schalter aus: Vollbild wartet",
      f._vsync_ueberspringen(None) is False)

print("Test 5: im Ruhezustand wird nie uebersprungen")
# Unveraendertes Verhalten seit Build 61 - beim blossen Betrachten gibt
# es kein Tearing-Risiko, weil gar nicht ausgelassen wird.
f = frontend_mit_schnellem_scrollen(1920, 1080)
f._last_input_time = fm.time.monotonic() - 10.0
check("10 s ohne Eingabe: schmales Band wartet",
      f._vsync_ueberspringen(2) is False)

# ----------------------------------------------------------------------
print("Test 6: ohne Messwerte gelten die bisherigen festen Boeden")
# Wichtig fuer den allerersten Tastendruck nach dem Start: da gibt es
# noch nichts Gemessenes, und dann muss sich das Frontend exakt so
# verhalten wie bisher.
im = I.InputManager.__new__(I.InputManager)
im._zeichenzeit = {}
check("hoch/runter -> REPEAT_FLOOR",
      abs(im._repeat_floor("down") - I.REPEAT_FLOOR) < 1e-9)
check("links/rechts -> REPEAT_FLOOR_PAGE",
      abs(im._repeat_floor("left") - I.REPEAT_FLOOR_PAGE) < 1e-9)

print("Test 7: langsames Zeichnen bremst die Anforderung")
# Der Stau-Fall, den der Nutzer als Lag spuert: ein voller Aufbau mit
# Cover dauert auf HDMI gemessen 45-110 ms. Bei festen 0.08 s wurden
# 12,5 Schritte/s angefordert - lieferbar waren 9 bis 22.
im = I.InputManager.__new__(I.InputManager)
im._zeichenzeit = {}
for _ in range(40):
    im.zeichenzeit_melden("down", 0.110)
boden = im._repeat_floor("down")
check("110 ms Aufbau -> Boden mindestens 110 ms", boden >= 0.110,
      "(Boden %.0f ms = %.1f Schritte/s)" % (boden * 1000, 1.0 / boden))
check("110 ms Aufbau -> Boden hoeher als der alte Festwert",
      boden > I.REPEAT_FLOOR)

print("Test 8: schnelles Zeichnen erlaubt mehr Schritte (nur hoch/runter)")
# Die andere Haelfte: auf CRT kostet ein Einzelschritt ~3 ms. Dort waren
# 12,5/s unnoetig traege.
im = I.InputManager.__new__(I.InputManager)
im._zeichenzeit = {}
for _ in range(40):
    im.zeichenzeit_melden("down", 0.003)
boden = im._repeat_floor("down")
check("3 ms Aufbau -> Boden faellt unter den alten Festwert",
      boden < I.REPEAT_FLOOR,
      "(Boden %.0f ms = %.0f Schritte/s)" % (boden * 1000, 1.0 / boden))
check("3 ms Aufbau -> Boden nicht unter REPEAT_FLOOR_MIN",
      boden >= I.REPEAT_FLOOR_MIN - 1e-9)

print("Test 9: links/rechts wird NIE schneller - der Mensch ist die Grenze")
# Bewusste Asymmetrie: bei einem Seitensprung ist nicht die Rechenzeit
# die Grenze, sondern das Lesen. Schnellere Hardware aendert daran
# nichts, deshalb darf die Messung hier nur bremsen.
im = I.InputManager.__new__(I.InputManager)
im._zeichenzeit = {}
for _ in range(40):
    im.zeichenzeit_melden("left", 0.005)
check("5 ms Seitenaufbau -> Boden bleibt REPEAT_FLOOR_PAGE",
      abs(im._repeat_floor("left") - I.REPEAT_FLOOR_PAGE) < 1e-9)
im = I.InputManager.__new__(I.InputManager)
im._zeichenzeit = {}
for _ in range(40):
    im.zeichenzeit_melden("left", 0.400)
check("400 ms Seitenaufbau -> Boden wird groesser",
      im._repeat_floor("left") > I.REPEAT_FLOOR_PAGE)

print("Test 10: Notbremse nach oben")
# Eine einzelne sehr langsame Phase darf die Bedienung nicht auf
# Kriechtempo festnageln.
im = I.InputManager.__new__(I.InputManager)
# GEAENDERT IN BUILD 297: geschluesselt wird mit der AKTION, nicht
# mehr mit der Achse - "up" und "down" hatten sich einen Messwert
# geteilt, obwohl sie um Faktor 4 verschieden teuer sind (siehe
# zeichenzeit_melden()). Hier stand {"y": 5.0}.
im._zeichenzeit = {"down": 5.0}    # absurd, von Hand gesetzt
check("Boden gedeckelt auf REPEAT_FLOOR_MAX",
      abs(im._repeat_floor("down") - I.REPEAT_FLOOR_MAX) < 1e-9)

print("Test 11: unsinnige Messungen werden verworfen")
# Uhrensprung (negativ), Nullwert, und der Fall "zwischendurch lief ein
# Spiel" (Sekunden statt Millisekunden) duerfen das Mittel nicht
# vergiften.
im = I.InputManager.__new__(I.InputManager)
im._zeichenzeit = {}
for wert in (-1.0, 0.0, 900.0, None, "schnell"):
    im.zeichenzeit_melden("down", wert)
check("nach nur unsinnigen Meldungen gilt weiter der Festwert",
      abs(im._repeat_floor("down") - I.REPEAT_FLOOR) < 1e-9,
      "(nichts gespeichert: %r)" % (im._zeichenzeit,))
im.zeichenzeit_melden("ok", 0.02)          # keine Wiederhol-Aktion
check("nicht wiederholbare Aktionen werden ignoriert",
      im._zeichenzeit == {})

print("Test 12: das Mittel ist traege, ein Ausreisser kippt es nicht")
# REPEAT_MESS_FENSTER: ein einzelnes langsam geladenes Cover darf die
# Wiederholrate nicht sofort halbieren.
im = I.InputManager.__new__(I.InputManager)
im._zeichenzeit = {}
for _ in range(40):
    im.zeichenzeit_melden("down", 0.010)
vorher = im._repeat_floor("down")
im.zeichenzeit_melden("down", 0.300)       # ein einzelner Ausreisser
nachher = im._repeat_floor("down")
# NEU GEFASST IN BUILD 297, und das ist eine echte Verhaltensaenderung
# mit Grund - keine Abschwaechung, aber auch kein Gratis-Gewinn.
#
# HIER STAND: "ein Ausreisser aendert den Boden um weniger als 50 %"
# (nachher < vorher * 1.5). Die Sorge dahinter ist richtig und war der
# Grund fuer das traege Fenster: ein einzelnes langsam geladenes Cover
# darf die Wiederholrate nicht festnageln.
#
# NUR WAR DIESELBE TRAEGHEIT AUCH DIE URSACHE DES FEHLERS, den der
# Nutzer gemeldet hat: eine ANHALTENDE Verlangsamung (rauf 69 ms ->
# runter 284 ms) brauchte acht Schritte, bis der Boden sie bemerkte -
# acht Schritte, in denen viermal mehr angefordert wurde als lieferbar.
# "hackt oder reagiert nicht und zieht dann nach".
#
# Build 297 reagiert auf Verlangsamung deshalb mit Fenster 2 statt 8
# (siehe REPEAT_MESS_FENSTER_HOCH). Damit bewegt EIN Ausreisser den
# Boden um die halbe Strecke statt um ein Achtel - die alte Grenze von
# 50 % ist nicht mehr zu halten.
#
# DIE ZUSAGE WIRD DESHALB NEU FORMULIERT, in zwei Teilen, und
# zusammen sind sie strenger als vorher: der Ausreisser darf den Boden
# NICHT auf seinen eigenen Wert ziehen, UND er muss nach wenigen
# billigen Schritten wieder eingesammelt sein. Das Zweite hat die alte
# Fassung ueberhaupt nicht geprueft - sie war in BEIDE Richtungen
# traege, ein Ausreisser wirkte also lange nach.
check("ein Ausreisser zieht den Boden NICHT auf seinen eigenen Wert",
      nachher < 0.300 * I.REPEAT_MESS_RESERVE * 0.75,
      "(%.0f ms -> %.0f ms; der Ausreisser selbst waere %.0f ms)"
      % (vorher * 1000, nachher * 1000,
         0.300 * I.REPEAT_MESS_RESERVE * 1000))
# UND DIE ERHOLUNG, und zwar als STRUKTUR statt als Einzelwert
# gemessen: jeder billige Schritt muss den Boden senken. Das ist die
# Zusage, die wirklich zaehlt - sie schliesst eine Ratsche aus, bei der
# ein Ausreisser dauerhaft nachwirkt. Eine einzelne Zahl ("nach vier
# Schritten unter X") haette ich hier beim ersten Versuch zu streng
# angesetzt (gemessen sind es 178 -> 109 ms nach vier Schritten, nicht
# 80), und dann prueft der Test meine Schaetzung statt der Mechanik.
_lauf = [im._repeat_floor("down")]
for _ in range(8):
    im.zeichenzeit_melden("down", 0.010)
    _lauf.append(im._repeat_floor("down"))
check("jeder billige Schritt senkt den Boden wieder",
      all(b < a for a, b in zip(_lauf, _lauf[1:])),
      " -> ".join("%.0f" % (b * 1000) for b in _lauf) + " ms")
check("nach acht billigen Schritten wieder in der Naehe von vorher",
      _lauf[-1] < vorher * 2.0,
      "(%.0f ms, vorher waren es %.0f ms)"
      % (_lauf[-1] * 1000, vorher * 1000))

print("Test 12b: eine ANHALTENDE Verlangsamung wird schnell erfasst")
# DAS IST DER FEHLER AUS BUILD 297, und er ist die Gegenseite von
# Test 12: was ein Ausreisser nicht duerfen soll, muss ein echter
# Trend sofort koennen.
#
# Seine Zahlen, aus dem LATENZ-Protokoll: rauf 69 ms, runter 284 ms.
im = I.InputManager.__new__(I.InputManager)
im._zeichenzeit = {}
for _ in range(12):
    im.zeichenzeit_melden("up", 0.069)
check("nach schnellem Hochscrollen ist der Boden niedrig",
      im._repeat_floor("up") < 0.090,
      "%.0f ms" % (im._repeat_floor("up") * 1000))
# ERSTER Schritt nach unten: noch kein eigener Messwert, also die
# Schaetzung ueber den Achsenpartner - genau einmal zu optimistisch.
im.zeichenzeit_melden("down", 0.284)
_noetig = 0.284 * I.REPEAT_MESS_RESERVE
check("nach EINEM Schritt nach unten stimmt der Boden",
      im._repeat_floor("down") >= _noetig * 0.95,
      "%.0f ms (noetig %.0f ms) - vorher brauchte das acht Schritte"
      % (im._repeat_floor("down") * 1000, _noetig * 1000))
check("und hoch bleibt unberuehrt schnell",
      im._repeat_floor("up") < 0.090,
      "%.0f ms - getrennte Messung je Richtung ist der Kern von "
      "Build 297" % (im._repeat_floor("up") * 1000))

print("Test 13: das Frontend meldet die Zeit auch wirklich")
# Ohne diesen Aufruf waere die ganze Mechanik totes Holz. Geprueft am
# Quelltext von run(), da die Schleife selbst nicht isoliert laufen kann.
src = open(H.FRONTEND_PY, encoding="utf-8", errors="replace").read()
check("run() ruft zeichenzeit_melden() auf",
      "self.inp.zeichenzeit_melden(" in src)
check("gemeldet wird die Zeichenzeit, nicht die Wartezeit",
      "_rt0 - _rt_prev" in src,
      "(_rt2 waere die Wartezeit in next_action())")

print("Test 14: kein Zeichenpfad benutzt mehr den alten Vollbild-Skip")
# Regressionsschutz: taucht irgendwo wieder flip(skip_vsync=
# self._scroll_skip_vsync()) auf, ist Aenderung A wieder ausgehebelt.
check("kein flip(skip_vsync=self._scroll_skip_vsync())",
      "flip(skip_vsync=self._scroll_skip_vsync())" not in src)
check("kein flip_rows(..., skip_vsync=self._scroll_skip_vsync())",
      "skip_vsync=self._scroll_skip_vsync())" not in src)
# _scroll_skip_vsync() selbst bleibt aber in Gebrauch - fuer die beiden
# Entscheidungen, die gar nichts kopieren (defer_panel und
# _spalte_auslassen). Wuerde es verschwinden, waere das Auslassen der
# Boxart-Spalte mit weggefallen.
# GEAENDERT (Build 138): die Bedingung hat einen zweiten Teil bekommen -
# den Schalter "Cover beim Scrollen" (siehe tools/test_cover_sofort.py).
# Geprueft wird deshalb weiter, dass _scroll_skip_vsync() hier ueberhaupt
# noch vorkommt, nicht mehr der genaue Wortlaut der Zeile.
check("_scroll_skip_vsync() weiterhin fuer defer_panel benutzt",
      "defer_panel = (has_art and self._scroll_skip_vsync()" in src)

print()
if fails:
    print("FEHLGESCHLAGEN (%d):" % len(fails))
    for f_ in fails:
        print("  -", f_)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
