#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Die Dauerwache gegen den Login-Prompt (Build 157).

NUTZER-RUECKMELDUNG MIT BILDSCHIRMFOTO: "wenn ich spiele liste neu
einlesen machen springt der manchmal um in denn welcome to mister ...
auch so manchmal macht das frontend das im menue". Auf dem Foto steht
oben links, ueber unserem Bild:

    Welcome to MiSTer (www.MiSTerFPGA.org)
    login: _

ZWEI DINGE GREIFEN INEINANDER:

  1. Der Login-Prozess auf tty1 schreibt in denselben Framebuffer wie
     wir. Seit Build 150 bekannt - aber nur im STARTFENSTER behandelt,
     weil es dort als Folge des eingespeisten F9 galt.
  2. flip() kopiert das ganze Bild und wischt den Prompt mit weg. Im
     Ruhezustand laeuft aber meistens nur flip_rows() (Laufschrift,
     Uhr, Equalizer), und das fasst die obersten Zeilen nicht an.
     Genau dort steht der Prompt. Er bleibt also stehen, bis zufaellig
     ein voller Aufbau kommt.

WAS DIESER TEST VOR ALLEM ABSICHERT, IST NICHT DAS ERKENNEN, SONDERN
DAS NICHT-ERKENNEN. Build 151 hat der Nutzer gemeldet: "es geht aber
es flakert jetzt alle paar sekunden". Ursache damals: die Pruefung
fragte nur, ob mm und buf ungleich sind - und das sind sie auch mitten
in einem eigenen Bildaufbau. Eine Wache, die jede Sekunde nachsieht,
darf diesen Fehler nicht wiederholen.

Deshalb zaehlt _fremdausgabe_zaehlen() gerichtet: hell auf dem SCHIRM,
dunkel im GEZEICHNETEN Bild. Ein eigener halbfertiger Aufbau hat es
genau andersherum.

Ausfuehren:
    python3 tools/test_konsole_wache.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H                                        # noqa: E402

fm = H.fm
fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


def aufbau():
    f = H.make_frontend(page=0)
    f.draw()
    f.fb.mm[:] = f.fb.buf          # Schirm und Zeichnung sind gleich
    f._wache_naechste = 0.0
    f._wache_verdacht = 0
    f._gewischt = []
    f._konsole_wischen = lambda grund: f._gewischt.append(grund)
    return f


def prompt_schreiben(f, text=b"Welcome to MiSTer (www.MiSTerFPGA.org)"):
    """Weissen Text oben links DIREKT in den Schirm malen - so, wie es
    der Login-Prozess tut: an uns vorbei, nur in mm, nicht in buf."""
    punkte = 0
    for zeile in range(2):
        y = 4 + zeile * 10
        for i in range(len(text)):
            for dx in range(5):        # fuenf helle Punkte je Zeichen
                x = 2 + i * 6 + dx
                if x >= f.fb.width:
                    break
                for dy in range(3):
                    off = (y + dy) * f.fb.stride + x * 4
                    f.fb.mm[off:off + 4] = b"\xff\xff\xff\x00"
                    punkte += 1
    return punkte


def takten(f, sekunden):
    """Die Wache n-mal im eigenen Takt laufen lassen."""
    for _ in range(sekunden):
        f._konsole_wache()
        H.NOW[0] += fm.Frontend.KONSOLE_WACHE_TAKT


# ---------------------------------------------------------------------------
print("Test 1: ein sauberes Bild loest nichts aus")
# ---------------------------------------------------------------------------
f = aufbau()
check("nichts Fremdes gefunden", f._fremdausgabe_zaehlen() == 0,
      "%d Punkte" % f._fremdausgabe_zaehlen())
takten(f, 10)
check("zehn Sekunden Ruhe, kein einziges Wischen", f._gewischt == [],
      str(f._gewischt))

# ---------------------------------------------------------------------------
print()
print("Test 2: der Login-Prompt wird gefunden und weggewischt")
# ---------------------------------------------------------------------------
f = aufbau()
gemalt = prompt_schreiben(f)
gefunden = f._fremdausgabe_zaehlen()
check("die Fremdpunkte werden gezaehlt",
      gefunden >= fm.Frontend.KONSOLE_WACHE_MINDEST,
      "%d von %d gemalten, Schwelle %d"
      % (gefunden, gemalt, fm.Frontend.KONSOLE_WACHE_MINDEST))
f._konsole_wache()
check("beim ERSTEN Blick passiert noch nichts", f._gewischt == [],
      "einmal koennte ein halber Bildaufbau sein")
H.NOW[0] += fm.Frontend.KONSOLE_WACHE_TAKT
f._konsole_wache()
check("beim zweiten wird gewischt", len(f._gewischt) == 1,
      str(f._gewischt))

# ---------------------------------------------------------------------------
print()
print("Test 3: DAS FLACKERN VON BUILD 151 DARF NICHT WIEDERKEHREN")
# ---------------------------------------------------------------------------
# Ein halbfertiger eigener Aufbau: buf ist schon hell, mm noch alt.
# Genau diese Lage hat die alte Pruefung ("mm != buf") jedes Mal als
# Fremdausgabe gewertet - und der Nutzer sah alle paar Sekunden ein
# Zucken.
f = aufbau()
for y in range(20):
    off = y * f.fb.stride
    f.fb.buf[off:off + 400 * 4] = b"\xff\xff\xff\x00" * 400
check("mm und buf sind jetzt ungleich",
      bytes(f.fb.mm[:20 * f.fb.stride]) != bytes(f.fb.buf[:20 * f.fb.stride]))
check("die Wache wertet das NICHT als Fremdausgabe",
      f._fremdausgabe_zaehlen() == 0,
      "%d Punkte" % f._fremdausgabe_zaehlen())
takten(f, 10)
check("und wischt auch nach zehn Takten nicht", f._gewischt == [],
      str(f._gewischt))

# ---------------------------------------------------------------------------
print()
print("Test 4: ein paar helle Punkte reichen nicht")
# ---------------------------------------------------------------------------
# Ein einzelner verirrter Bildpunkt - etwa vom Mauszeiger des Kernels -
# darf keinen vollen Neuaufbau ausloesen.
f = aufbau()
for i in range(10):
    off = 5 * f.fb.stride + (20 + i) * 4
    f.fb.mm[off:off + 4] = b"\xff\xff\xff\x00"
check("zehn Punkte liegen unter der Schwelle",
      f._fremdausgabe_zaehlen() < fm.Frontend.KONSOLE_WACHE_MINDEST,
      "%d Punkte" % f._fremdausgabe_zaehlen())
takten(f, 6)
check("also wird nicht gewischt", f._gewischt == [], str(f._gewischt))

# ---------------------------------------------------------------------------
print()
print("Test 5: der Verdacht verfaellt, wenn er sich nicht bestaetigt")
# ---------------------------------------------------------------------------
# Ein Aufblitzen darf keinen Zaehler fuellen, der irgendwann spaeter
# zusammen mit einem zweiten Aufblitzen ausloest.
f = aufbau()
prompt_schreiben(f)
f._konsole_wache()                       # Verdacht 1
check("Verdacht ist vermerkt", f._wache_verdacht == 1)
f.fb.mm[:] = f.fb.buf                    # Prompt weg (voller flip)
H.NOW[0] += fm.Frontend.KONSOLE_WACHE_TAKT
f._konsole_wache()
check("sauberes Bild setzt den Verdacht zurueck", f._wache_verdacht == 0)
check("und es wurde nie gewischt", f._gewischt == [], str(f._gewischt))

# ---------------------------------------------------------------------------
print()
print("Test 6: die Wache haelt ihren Takt ein")
# ---------------------------------------------------------------------------
f = aufbau()
prompt_schreiben(f)
for _ in range(20):                      # zwanzig Schleifendurchlaeufe,
    f._konsole_wache()                   # aber keine Zeit vergeht
check("ohne vergehende Zeit bleibt es bei einem Blick",
      f._wache_verdacht == 1 and f._gewischt == [],
      "Verdacht %d, gewischt %s" % (f._wache_verdacht, f._gewischt))

# ---------------------------------------------------------------------------
print()
print("Test 7: die Wache haengt nicht mehr am Startfenster")
# ---------------------------------------------------------------------------
# Das war der eigentliche Fehler: _konsole_aufraeumen() steigt sofort
# aus, wenn _f9_aufraeumen_ab None ist - und das wird nur von
# _konsole_sichern() im Startfenster gesetzt. Danach raeumte niemand
# mehr auf, und genau das hat der Nutzer gemeldet.
f = aufbau()
f._f9_aufraeumen_ab = None               # Startfenster laengst vorbei
H.NOW[0] += 3600.0                       # eine Stunde spaeter
f._wache_naechste = 0.0
prompt_schreiben(f)
f._konsole_aufraeumen()
check("die alte Funktion allein tut nichts mehr", f._gewischt == [],
      str(f._gewischt))
f._konsole_wache()
H.NOW[0] += fm.Frontend.KONSOLE_WACHE_TAKT
f._konsole_wache()
check("die Wache raeumt trotzdem auf", len(f._gewischt) == 1,
      str(f._gewischt))
check("und nennt den Grund im Log", "Dauerwache" in (f._gewischt or [""])[0],
      str(f._gewischt))

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
