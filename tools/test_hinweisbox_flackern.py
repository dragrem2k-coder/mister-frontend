#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft, dass die Hinweisbox nicht mehr flackert (Build 94).

AUSLOESER (Nutzer-Rueckmeldung mit Video: "das Flackern muessen wir auch
beheben, das kommt bei einigen Einstellungen wenn man was veraendert").

DER BEFUND AUS DEM VIDEO (1920x1080, 60 Bilder/s, Bild fuer Bild
verglichen): nach dem Umschalten von "Autostart" erschien die
Hinweisbox - und verschwand danach 6 mal pro Sekunde fuer genau zwei
Bilder (33 ms). Der 6-Hz-Takt ist die Laufschrift (0.18 s), die wegen
_overlay_active() bewusst auf den vollen draw() faellt.

DIE URSACHE: draw() hat die Seite mit flip=True auf den Schirm gebracht
und ERST DANACH die Box gezeichnet (mit eigenem flip_rows nur ueber das
Box-Band). Zwischen beidem liegt das Rendern der Box - und genau so
lange zeigt der Bildschirm die fertige Seite OHNE Box.

Der Kommentar bei any_dialog in draw() beschrieb diesen Fehler schon
woertlich ("sonst blitzt fuer einen Frame der Hintergrund ohne Dialog
auf") - er war nur fuer die beiden Bestaetigungsdialoge behoben worden.
Die Hinweisbox kam spaeter dazu und fehlte in der Aufzaehlung.

Geprueft wird deshalb nicht "sieht gut aus", sondern die
Reihenfolge der Flips: waehrend die Box aktiv ist, darf es auf dem Weg
zum fertigen Bild NUR EINEN Flip geben, und der muss NACH dem Zeichnen
der Box kommen.

Ausfuehren:
    python3 tools/test_hinweisbox_flackern.py
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import _harness as H                                  # noqa: E402

fm = H.fm

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


def mit_protokoll(f):
    """Jeden Flip mitschreiben: ("voll", None) oder ("band", hoehe).
    Zusaetzlich wird vermerkt, wann die Box gezeichnet wurde."""
    log = []
    echt_flip = f.fb.flip
    echt_rows = f.fb.flip_rows
    echt_box = f._draw_prominent_message

    def flip(skip_vsync=False):
        log.append(("voll", None))
        return echt_flip(skip_vsync=skip_vsync)

    def flip_rows(y, h, skip_vsync=False):
        log.append(("band", h))
        return echt_rows(y, h, skip_vsync=skip_vsync)

    def box():
        log.append(("box", None))
        return echt_box()

    f.fb.flip = flip
    f.fb.flip_rows = flip_rows
    f._draw_prominent_message = box
    return log


SEITEN = ((0, "Hauptmenue"), (1, "Spieleliste"))


print("Test 1: mit Hinweisbox gibt es genau EINEN Flip - nach der Box")
# Der Kern. Zwei Flips (erst Seite, dann Box) sind exakt das Flackern.
for w, h, name in ((320, 240, "CRT"), (1920, 1080, "HDMI")):
    for page, pname in SEITEN:
        H.set_screen(w, h)
        f = H.make_frontend(page=page)
        log = mit_protokoll(f)
        f.draw(message="Autostart ist ab dem naechsten Start aus.",
               prominent=True)
        flips = [e for e in log if e[0] != "box"]
        box_i = [i for i, e in enumerate(log) if e[0] == "box"]
        check("%s/%s: genau ein Flip" % (name, pname), len(flips) == 1,
              "(%s)" % [e[0] for e in log])
        check("%s/%s: Box wurde gezeichnet" % (name, pname), len(box_i) == 1)
        if flips and box_i:
            letzter = max(i for i, e in enumerate(log) if e[0] != "box")
            check("%s/%s: der Flip kommt NACH der Box"
                  % (name, pname), letzter > box_i[0],
                  "(Reihenfolge %s)" % [e[0] for e in log])
            check("%s/%s: und er ist ein Vollbild-Flip" % (name, pname),
                  flips[0][0] == "voll",
                  "(sonst bliebe der Rest der Seite ungeflippt)")

print("Test 2: die Box haelt ueber mehrere Aufbauten durch")
# Das Video zeigte das Aufblitzen nicht einmalig, sondern bei jedem
# Laufschrift-Takt neu. Also mehrere Aufbauten hintereinander pruefen -
# jeder einzelne muss sauber sein.
H.set_screen(1920, 1080)
f = H.make_frontend(page=1)
f.draw(message="Autostart ist ab dem naechsten Start aus.", prominent=True)
log = mit_protokoll(f)
for _ in range(5):
    f.draw()                       # so kommt der Laufschrift-Takt herein
flips = [e for e in log if e[0] != "box"]
boxen = [e for e in log if e[0] == "box"]
check("5 weitere Aufbauten -> 5 Boxen", len(boxen) == 5,
      "(%d)" % len(boxen))
check("5 weitere Aufbauten -> genau 5 Flips", len(flips) == 5,
      "(%d Flips: %s)" % (len(flips), [e[0] for e in flips]))

print("Test 3: ohne Box bleibt alles wie bisher")
# Absicherung gegen das Gegenteil: der normale Aufbau darf nicht
# ploetzlich den Flip verlieren.
for w, h, name in ((320, 240, "CRT"), (1920, 1080, "HDMI")):
    for page, pname in SEITEN:
        H.set_screen(w, h)
        f = H.make_frontend(page=page)
        log = mit_protokoll(f)
        f.draw()
        check("%s/%s: normaler Aufbau flippt" % (name, pname),
              any(e[0] == "voll" for e in log),
              "(%s)" % [e[0] for e in log])
        check("%s/%s: keine Box ohne Meldung" % (name, pname),
              not any(e[0] == "box" for e in log))

print("Test 4: die kleine Fusszeilen-Meldung ist NICHT betroffen")
# prominent=False setzt nur die Fusszeile, keine Ueberlagerung - dort
# darf sich nichts aendern.
H.set_screen(1920, 1080)
f = H.make_frontend(page=1)
log = mit_protokoll(f)
f.draw(message="Favorit hinzugefuegt")
check("Fusszeilen-Meldung zeichnet keine Box",
      not any(e[0] == "box" for e in log))
check("Fusszeilen-Meldung flippt normal",
      any(e[0] == "voll" for e in log))

print("Test 5: die Entscheidung wird nur EINMAL getroffen")
# Feinheit, die beim Bauen aufgefallen ist: _overlay_active() prueft die
# Uhr. Wuerde draw() sie zweimal aufrufen (einmal fuer den Flip, einmal
# fuer das Zeichnen), koennte die Box genau dazwischen ablaufen - dann
# waere der Seiten-Flip unterdrueckt UND die Box nicht gezeichnet, das
# Bild bliebe komplett stehen. Am Quelltext geprueft, weil sich ein
# Zeitfenster von Mikrosekunden nicht zuverlaessig nachstellen laesst.
src = open(H.FRONTEND_PY, encoding="utf-8", errors="replace").read()
kopf = src[src.index("def draw(self"):]
kopf = kopf[:kopf.index("def _sync_cover_defer")]
check("_overlay_active() wird in draw() genau einmal aufgerufen",
      kopf.count("self._overlay_active()") == 1,
      "(%d mal)" % kopf.count("self._overlay_active()"))
check("und das Ergebnis wird wiederverwendet",
      "_box_aktiv" in kopf and kopf.count("_box_aktiv") >= 3,
      "(%d Vorkommen)" % kopf.count("_box_aktiv"))

print("Test 6: Regressionsschutz gegen den alten Band-Flip")
check("_draw_prominent_message() flippt nicht mehr nur das Band",
      "fb.flip_rows(box_y, box_h)" not in src)

print()
if fails:
    print("FEHLGESCHLAGEN (%d):" % len(fails))
    for f_ in fails:
        print("  -", f_)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
