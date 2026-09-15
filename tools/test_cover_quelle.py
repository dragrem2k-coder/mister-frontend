#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Woher ein Cover kommt - art/ oder art_hd/ (Build 130).

GEMELDETER FEHLER: "Wer die Menueaufloesung halbiert (z.B. gegen
Flackern bei 1080p) und NUR HD-Boxarts pflegt, sieht ploetzlich gar
keine Cover mehr."

Und das stimmte. Die Schwelle stand an ACHT Stellen als `if H >= 720`.
Bei halber Aufloesung ist H rund 540, also darunter - das Frontend
suchte nur noch in art/, und wer dort nichts liegen hat, bekam nichts.

DER VORSCHLAG WAR "IMMER ZUERST art_hd", UND DAS WAERE FALSCH GEWESEN.
Es haette den Fehler behoben und einen neuen gemacht: die Regel trifft
naemlich auch die ECHTE Roehre mit H=240. Wer dort sein art/ gepflegt
hat - kleine, fertig verkleinerte Bilder - bekaeme ab sofort jedes
Cover aus der grossen HD-Datei. Also eine 900x1200-Flaechenmittelung
statt eines fertigen 300x350-Bildes, auf der schwaechsten Hardware der
teuerste Weg.

GEPRUEFT WIRD DESHALB DIE ASYMMETRIE:

    H >= 720   nur art_hd/, KEIN Rueckfall (Build 89, ausdruecklicher
               Nutzerwunsch: ein hochskaliertes SD-Bild "sieht bloed
               aus", dann lieber gar keins)
    H <  720   erst art/, und nur wenn dort nichts liegt, art_hd/

Ausfuehren:
    python3 tools/test_cover_quelle.py
"""
import os
import shutil
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)

import _harness as H                                    # noqa: E402

fm = H.fm
sys.path.insert(0, os.path.join(_REPO, "frontend"))
import fe.art as A                                      # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


TMP = tempfile.mkdtemp(prefix="cover_quelle_")
SD = os.path.join(TMP, "art")
HD = os.path.join(TMP, "art_hd")
for d in (SD, HD):
    os.makedirs(os.path.join(d, "SNES"))

fm.ART_BASE, A.ART_BASE = SD, SD
fm.ART_HD, A.ART_HD = HD, HD


def legen(basis, name):
    with open(os.path.join(basis, "SNES", name + ".art"), "wb") as f:
        f.write(b"ART1")


def weg(basis, name):
    try:
        os.remove(os.path.join(basis, "SNES", name + ".art"))
    except OSError:
        pass


def quelle(f, name):
    A._art_index_cache.clear()
    p = f.cover_quelle("SNES", name)
    if not p:
        return "nichts"
    if p.startswith(HD):
        return "hd"
    if p.startswith(SD):
        return "sd"
    return p


# Vier Ausgangslagen, die es in echt alle gibt.
legen(SD, "NurSD")
legen(HD, "NurHD")
legen(SD, "Beide")
legen(HD, "Beide")
FAELLE = ["NurSD", "NurHD", "Beide", "Keins"]

# ---------------------------------------------------------------------
print("Test 1: volle Aufloesung - nur art_hd, kein Rueckfall")
# Das ist die Zusage aus Build 89 und sie bleibt unberuehrt: ein auf
# 1080p hochskaliertes SD-Bild ist sichtbar matschig, dann lieber gar
# keines.
H.set_screen(1920, 1080)
f = H.make_frontend(page=1)
erwartet = {"NurSD": "hd", "NurHD": "hd", "Beide": "hd", "Keins": "hd"}
for n in FAELLE:
    g = quelle(f, n)
    check("%-6s -> %s" % (n, erwartet[n]), g == erwartet[n], "ist %s" % g)
# Und die Probe darauf, dass "hd" bei NurSD wirklich ins Leere zeigt -
# sonst waere die Zeile darueber nur eine Pfadaussage ohne Bedeutung.
check("bei NurSD zeigt der HD-Pfad auf eine Datei, die es nicht gibt",
      not os.path.exists(f.cover_quelle("SNES", "NurSD")))

# ---------------------------------------------------------------------
print()
print("Test 2: halbe Aufloesung - erst art, dann art_hd")
# Der gemeldete Fall. 960x540 ist genau das, was "Menue-Aufloesung
# halb" aus 1080p macht.
H.set_screen(960, 540)
f = H.make_frontend(page=1)
erwartet = {"NurSD": "sd", "NurHD": "hd", "Beide": "sd", "Keins": "sd"}
for n in FAELLE:
    g = quelle(f, n)
    check("%-6s -> %s" % (n, erwartet[n]), g == erwartet[n], "ist %s" % g)
check("DER gemeldete Fall: nur art_hd gepflegt, und es kommt etwas an",
      os.path.exists(quelle(f, "NurHD") and f.cover_quelle("SNES", "NurHD")))

# ---------------------------------------------------------------------
print()
print("Test 3: echte Roehre - der billige Weg bleibt der billige")
# Die Stelle, an der der urspruengliche Vorschlag ("immer zuerst
# art_hd") einen neuen Fehler gemacht haette.
H.set_screen(320, 240)
f = H.make_frontend(page=1)
check("Beide vorhanden -> art/ gewinnt, NICHT art_hd",
      quelle(f, "Beide") == "sd", "ist %s" % quelle(f, "Beide"))
check("NurSD -> art/", quelle(f, "NurSD") == "sd")
# Aber ohne art/ ist ein HD-Cover besser als gar keines.
check("NurHD -> art_hd (besser etwas als nichts)",
      quelle(f, "NurHD") == "hd", "ist %s" % quelle(f, "NurHD"))

# ---------------------------------------------------------------------
print()
print("Test 4: die Wahl zwischen art/ und art_hd/ steht an EINER Stelle")
quelle_txt = open(os.path.join(_REPO, "frontend", "frontend.py"),
                  encoding="utf-8", errors="replace").read()
# Geprueft wird nicht die Zeichenfolge "720" - die steht auch in
# Kommentaren, Docstrings und bei thumb_cache_modus_setzen(), das
# voellig zu Recht dieselbe Schwelle benutzt (es waehlt den
# CACHE-ORDNER, nicht die Quelldatei). Geprueft wird, wer den
# HD-Pfad ZUSAMMENBAUT: das darf nur noch cover_quelle().
_ab = quelle_txt.index("def cover_quelle")
_bis = quelle_txt.index("def cover_pfad_und_kasten", _ab)
_drin = quelle_txt[_ab:_bis]
_draussen = quelle_txt[:_ab] + quelle_txt[_bis:]
_code_draussen = [z for z in _draussen.splitlines()
                  if not z.lstrip().startswith("#")]
_streu = [z.strip() for z in _code_draussen if "_art_path_in(ART_HD" in z]
check("ausserhalb von cover_quelle() greift niemand mehr auf art_hd zu",
      not _streu, repr(_streu[:3]))
check("und cover_quelle() selbst kennt beide Ordner",
      "_art_path_in(ART_HD" in _drin and "art_path(syskey, name)" in _drin)
check("alle Zeichenwege gehen darueber",
      quelle_txt.count("self.cover_quelle(") >= 8,
      "%d Aufrufe" % quelle_txt.count("self.cover_quelle("))

# ---------------------------------------------------------------------
print()
print("Test 5: Zeichenpfad und Vorauslader nehmen DIESELBE Datei")
# Der Fehler, der hier lauern wuerde: rechnet der Vorauslader aus der
# SD-Datei vor und zeichnet das Frontend aus der HD-Datei, tragen beide
# einen anderen Cache-Schluessel - das Vorbereiten liefe durch und es
# ruckelte trotzdem. Genau diese Klasse Fehler gab es in Build 122
# schon einmal mit der Kastengroesse.
H.set_screen(960, 540)
f = H.make_frontend(page=1)
_n, node, _k = f.cats[f.cat_i]
node["items"] = [("NurHD", "game", ("/f/x.sfc", ".sfc", "SNES", None, None))]
node.pop("_display_items_cache", None)
f.item_i = 0
geo = f._art_panel_geometrie(erzwingen=True)
ziel = f.cover_pfad_und_kasten(node["items"][0], "SNES", geo)
check("der Vorauslader nimmt die HD-Datei",
      ziel is not None and ziel[0].startswith(HD),
      os.path.basename(ziel[0]) if ziel else "None")
check("und es ist genau der Pfad aus cover_quelle()",
      ziel is not None and ziel[0] == f.cover_quelle("SNES", "NurHD"))

# ---------------------------------------------------------------------
print()
print("Test 6: alle drei Aufloesungen zeichnen noch")
for b, h, wie in ((1920, 1080, "voll"), (960, 540, "halb"), (320, 240, "CRT")):
    H.set_screen(b, h)
    ff = H.make_frontend(page=1)
    try:
        ff.draw()
        ok = True
    except Exception as e:                               # noqa: BLE001
        ok = False
        print("       %s" % e)
    check("%-4s zeichnet ohne Ausnahme" % wie, ok)

shutil.rmtree(TMP, ignore_errors=True)

print()
if fails:
    print("FEHLGESCHLAGEN (%d):" % len(fails))
    for f_ in fails:
        print("  -", f_)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
