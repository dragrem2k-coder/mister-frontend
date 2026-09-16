#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Die drei heissen Kopierstellen - bitgenau, aber schneller (Build 131/132).

WO DAS HERKOMMT. Ein DRAGEND_PROFILE-Protokoll vom Geraet des Nutzers,
aufgenommen mit Build 130:

    0.144 s  _draw_cats_galerie
      0.075 s  blit             <- 12 Aufrufe
      0.021 s  clear
      0.016 s  flip

    0.066 s  _draw_page_items_impl
      0.031 s  _restore_row_bg  <- 2 Aufrufe
      0.013 s  text (tottime)   <- 21 Aufrufe

Drei verschiedene Funktionen, EIN Muster: alle drei kopieren Bildzeilen
ueber Ausschnitt-Zuweisungen auf ein bytearray.

    ziel[a:b] = quelle[c:d]

Zwei Kosten stecken darin, die man nicht sieht:

  1. Ein Ausschnitt auf bytes/bytearray legt eine KOPIE an. Bei einem
     411x548-Cover sind das 548 Zwischenobjekte je Bild - anfordern,
     kopieren, wegwerfen, 548 Mal.

  2. Eine Ausschnitt-ZUWEISUNG auf ein bytearray muss den allgemeinen
     Fall abdecken, in dem sich die Laenge aendert und der Puffer
     wachsen oder schrumpfen koennte. Auf einem memoryview ist die
     Groesse fest - es bleibt reines Kopieren.

WAS DIESER TEST SICHERT. Nicht die Geschwindigkeit - die schwankt und
ein Test, der gelegentlich grundlos rot wird, wird irgendwann ignoriert.
Gesichert wird, dass das Ergebnis BITGENAU dasselbe bleibt. Diese drei
Funktionen schreiben direkt in den Bildspeicher; ein Fehler um eine
Zeile oder ein Byte waere sofort sichtbar, und eine Zuweisung mit der
falschen Byte-Anzahl wuerde den Puffer sogar VERSCHIEBEN.

Ausfuehren:
    python3 tools/test_kopierpfade.py
"""
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)

import _harness as H                                    # noqa: E402

fm = H.fm

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


H.set_screen(1920, 1080)
f = H.make_frontend(page=1)
fb = f.fb

# ---------------------------------------------------------------------
print("Test 1: _restore_row_bg stellt denselben Hintergrund wieder her")
# Der Massstab ist nicht eine fruehere Fassung, sondern das, was die
# Funktion VERSPRICHT: genau die Vorlage, die fb.clear() benutzt. Ein
# Test gegen den alten Code wuerde denselben Fehler zweimal machen.
fb.clear(fm.C_BG)
vorlage = bytes(fb.buf)
FAELLE = [
    (100, 100, 700, 880, "Listenspalte"),
    (0, 0, 1920, 880, "volle Breite - der neue Sonderfall"),
    (100, 900, 700, 40, "Fusszeile"),
    (0, 0, 1920, 1080, "der ganze Schirm"),
    (0, 0, 1, 1, "ein einziger Punkt"),
    (0, 1079, 1920, 1, "die allerletzte Bildzeile"),
]
for x, y, w, h, name in FAELLE:
    # JEDER Fall faengt sauber an. Ohne das schleppt ein Fall die
    # Reste des vorherigen mit, und der zweite Fehlschlag ist nur
    # der erste in neuer Verkleidung - genau so beim Schreiben
    # dieses Tests passiert.
    fb.clear(fm.C_BG)
    fb.rect(max(0, x), max(0, y), min(w, 1920 - x), min(h, 1080 - y),
            (255, 0, 255))
    f._restore_row_bg(x, y, w, h)
    jetzt = bytes(fb.buf)
    gleich = jetzt == vorlage
    check("%-32s wiederhergestellt" % name, gleich,
          "" if gleich else "%d abweichende Bytes"
          % sum(1 for a, b in zip(vorlage, jetzt) if a != b))
    check("%-32s Puffer gleich lang" % name, len(fb.buf) == len(vorlage))

# UND DER FALL, DER NICHT VOLLSTAENDIG GEHT - bewusst als eigene
# Aussage, statt ihn zu den obigen zu zaehlen.
#
# Ein Bereich, der ueber den rechten Rand hinausragt, kann seine
# unterste Zeile nicht wiederherstellen: sie wuerde hinter dem
# Pufferende landen (bei 1900x1070 mit Breite 100 sind es 320 Byte
# zuviel). Die Funktion laesst sie deshalb aus - schon immer, das ist
# kein neues Verhalten. Zugesagt wird hier nur, was zugesagt werden
# kann: sie stuerzt nicht ab und sie verschiebt den Puffer nicht.
fb.clear(fm.C_BG)
fb.rect(1900, 1070, 20, 10, (255, 0, 255))
f._restore_row_bg(1900, 1070, 100, 100)
check("ueber den Rand hinaus: kein Absturz, Puffer unveraendert lang",
      len(fb.buf) == len(vorlage))
# Was hineinpasst, wird aber sehr wohl wiederhergestellt.
o = 1070 * fb.stride + 1900 * 4
check("und was hineinpasst, ist wieder da",
      bytes(fb.buf[o:o + 4]) == vorlage[o:o + 4],
      "%r vs %r" % (bytes(fb.buf[o:o + 4]), vorlage[o:o + 4]))

# Der Sonderfall "volle Breite" nimmt einen anderen Weg als die
# Schleife. Beide muessen dasselbe liefern - sonst ist die Abkuerzung
# eine Falle.
quelle = open(os.path.join(_REPO, "frontend", "frontend.py"),
              encoding="utf-8", errors="replace").read()
check("es gibt eine Abkuerzung fuer den zusammenhaengenden Fall",
      "if x == 0 and need == stride:" in quelle)

# ---------------------------------------------------------------------
print()
print("Test 2: text() zeichnet unveraendert")
# Gegen eine nachgebaute alte Fassung - hier gibt es kein unabhaengiges
# Versprechen wie oben, also wird gegen das frueher Erzeugte geprueft.
def text_alt(x, y, s, scale, fg, bg):
    strip = fb._text_strip(s, scale, fg, bg)
    w4 = len(strip[0])
    xo = x * 4
    for i, row in enumerate(strip):
        off = (y + i) * fb.stride + xo
        fb.buf[off:off + w4] = row

PROBEN = [
    ("Super Mario World", 3),
    ("Grüße aus Straßburg", 2),
    ("The Legend of Zelda - A Link to the Past", 1),
    ("X", 4),
    ("", 2),
]
for txt, scale in PROBEN:
    fb.clear(fm.C_BG)
    if txt:
        text_alt(50, 50, txt, scale, fm.C_TEXT, fm.C_BG)
    erwartet = bytes(fb.buf)
    fb.clear(fm.C_BG)
    fb.text(50, 50, txt, scale, fm.C_TEXT, fm.C_BG)
    gleich = bytes(fb.buf) == erwartet
    check("%-42s bitgenau" % ("%r (Groesse %d)" % (txt[:28], scale)), gleich)

# Text, der ueber den Rand hinausragt, muss abgeschnitten werden - und
# zwar an genau derselben Stelle wie vorher.
fb.clear(fm.C_BG)
fb.text(1850, 50, "Das passt hier nicht mehr hin", 3, fm.C_TEXT, fm.C_BG)
check("ueberlanger Text sprengt den Puffer nicht",
      len(fb.buf) == 1920 * 1080 * 4)

# ---------------------------------------------------------------------
print()
print("Test 3: die Kachelansichten sind groesser geworden (Build 132)")
# Nutzerwunsch mit Bildentwurf: "hier haette ich gerne groessere
# Bilder, von der Anzahl passt es aber - aber auch hier sollte nichts
# neues vorbereitet werden muessen, was Zeit oder Performance kostet".
#
# Der zweite Teil ist nur zur Haelfte erfuellbar, und das haelt dieser
# Test fest: die Kastengroesse IST der Schluessel des
# Miniatur-Zwischenspeichers, eine andere Kachelgroesse bedeutet also
# zwingend EINEN neuen Durchlauf. Was sich vermeiden liess, ist der
# DAUERHAFTE Aufpreis - und genau das wird hier geprueft.
H.set_screen(1920, 1080)
f2 = H.make_frontend(page=1)
L = f2.layout_items(True)
r = f2.raster_geometrie(L)
g = f2.galerie_geometrie(L)
check("Raster HDMI ist 7x3, nicht mehr 7x4",
      f2.RASTER_HDMI == (7, 3), repr(f2.RASTER_HDMI))
check("die Kachel ist deutlich groesser als die alten 124x166",
      r["cov_b"] >= 160 and r["cov_h"] >= 220,
      "%dx%d" % (r["cov_b"], r["cov_h"]))
check("und die Galerie-Leiste traegt denselben Kasten",
      (r["cov_b"], r["cov_h"]) == (g["klein_b"], g["klein_h"]),
      "Raster %dx%d, Leiste %dx%d"
      % (r["cov_b"], r["cov_h"], g["klein_b"], g["klein_h"]))

# DAS ist die eigentliche Zusage: es bleibt bei DREI Kastengroessen.
# Waere die Leiste stehen geblieben, waeren es wieder vier - und damit
# dauerhaft 25 % mehr Vorbereitungszeit und 25 % mehr Dateien.
for breite, hoehe, wie in ((1920, 1080, "HDMI"), (320, 240, "CRT")):
    H.set_screen(breite, hoehe)
    ff = H.make_frontend(page=1)
    geos = [ff._art_panel_geometrie(erzwingen=True)]
    for a in fm.ANSICHTEN:
        if a == "liste":
            continue
        for gg in ff._ansicht_geometrien(a, erzwingen=True):
            if gg not in geos:
                geos.append(gg)
    masse = [(x[1], x[2]) if x[0] == "fest" else (x[0], x[1]) for x in geos]
    check("%-4s weiterhin nur drei Kastengroessen" % wie, len(geos) == 3,
          repr(masse))

# CRT bleibt unangetastet - dort sind die Kacheln ohnehin winzig, und
# 5x3 war nie das Problem.
H.set_screen(320, 240)
fc = H.make_frontend(page=1)
check("CRT-Raster unveraendert 5x3", fc.RASTER_CRT == (5, 3),
      repr(fc.RASTER_CRT))

# ---------------------------------------------------------------------
print()
print("Test 4: und alle drei Ansichten zeichnen noch, in beiden Modi")
for breite, hoehe, wie in ((1920, 1080, "HDMI"), (320, 240, "CRT")):
    for seite, wo in ((1, "Spieleliste"), (0, "Hauptseite")):
        H.set_screen(breite, hoehe)
        ff = H.make_frontend(page=seite)
        for a in fm.ANSICHTEN:
            if seite == 1:
                ff.ansicht_setzen(a)
            else:
                ff.ansicht_haupt_setzen(a)
            try:
                ff.draw()
                ok = True
            except Exception as e:                       # noqa: BLE001
                ok = False
                print("       %s" % e)
            check("%-4s %-11s %-8s zeichnet" % (wie, wo, a), ok)

print()
if fails:
    print("FEHLGESCHLAGEN (%d):" % len(fails))
    for f_ in fails:
        print("  -", f_)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
