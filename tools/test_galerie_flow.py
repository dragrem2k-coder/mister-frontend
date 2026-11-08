#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Die Galerie im Coverflow - sein Entwurf 6 (Build 313).

NUTZERWUNSCH vom 08.11.: nach drei Entwuerfen fuer Liste, Kachel und
Galerie hat er sich entschieden - "Entwurf 6". Das gewaehlte Cover
gross in der Mitte, die Nachbarn links und rechts kleiner, Titel und
Daten mittig darunter. Und ausdruecklich: "nur fuer hdmi modus".

WARUM ES EIN SCHALTER IST UND KEINE ABLOESUNG, und das ist eine
Messfrage. Die klassische Galerie hat seit Build 125 einen schnellen
Pfad, und der steht und faellt mit einem Satz aus ihrem Quelltext:

    "Seitenweise bleibt die Leiste die meiste Zeit STEHEN - dann ist
     nur das grosse Cover neu, also EIN Bild statt zwoelf."

Ein Coverflow kann das per Bauart nicht: dort rueckt bei jedem Schritt
JEDES Cover eine Stelle weiter und wechselt dabei die Groesse. Statt
einem Bild sind es fuenf. Was das auf SEINEM Geraet kostet, weiss
niemand - deshalb bleibt die Vorgabe "klassisch", bis der Bench es
gemessen hat.

WAS DIESER TEST SICHERT:
  1. die Vorgabe ist "klassisch", und kaputte Werte fallen darauf
     zurueck,
  2. der Coverflow laeuft NUR auf HDMI - auf der Roehre bleibt alles
     wie es war, auch wenn der Schalter steht,
  3. die Reihe hat fuenf Plaetze, die Mitte ist der groesste, und
     alles liegt im Bild,
  4. die Ansicht zeichnet auf allen HD-Groessen ohne Fehler,
  5. sie baut KEINEN zweiten Cover-, Beschreibungs- oder Textweg,
     sondern benutzt die vorhandenen,
  6. das Cover wird VOR der Karte geholt (die Aussparung aus Build
     305 gilt auch hier),
  7. und der klassische Weg bleibt unangetastet.

Ausfuehren:
    python3 tools/test_galerie_flow.py
"""
import os
import re
import shutil
import sys
import tempfile
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H          # noqa: E402

import fe.settings as S       # noqa: E402
import fe.translations as TR  # noqa: E402
from _quelle import koerper, nur_code                     # noqa: E402

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_QF = open(os.path.join(_REPO, "frontend", "frontend.py"),
           encoding="utf-8", errors="replace").read()
_FLOW = nur_code(koerper(_QF, "_draw_items_galerie_flow", "Frontend"))
_GEO = nur_code(koerper(_QF, "galerie_flow_geometrie", "Frontend"))
_ALT = nur_code(koerper(_QF, "_draw_items_galerie", "Frontend"))

fails = []


def check(name, ok, info=""):
    if ok:
        print("  OK   %s %s" % (name, info))
    else:
        print("  FEHL %s %s" % (name, info))
        fails.append(name)


print(__doc__.strip().split("\n")[0])
print()

TMP = tempfile.mkdtemp(prefix="flow_")
S.GALERIE_STIL_FILE = os.path.join(TMP, "galerie_stil.txt")

# ---------------------------------------------------------------------------
print("Test 1: die Vorgabe ist 'klassisch'")
# ---------------------------------------------------------------------------
check("ohne Datei: klassisch", S.galerie_stil_lesen() == "klassisch",
      "%r - das ist der gemessene Stil" % (S.galerie_stil_lesen(),))
S.galerie_stil_schreiben("flow")
check("geschrieben wird, was man setzt",
      S.galerie_stil_lesen() == "flow")
S.galerie_stil_schreiben("quatsch")
check("ein unbekannter Wert faellt auf klassisch zurueck",
      S.galerie_stil_lesen() == "klassisch",
      "eine von Hand verstellte Datei darf das Frontend nicht in "
      "einen Zustand bringen, aus dem man ohne Texteditor nicht mehr "
      "herauskommt")
with open(S.GALERIE_STIL_FILE, "w") as fh:
    fh.write("\x00kaputt\n")
S._einstellungen_vergessen() if hasattr(S, "_einstellungen_vergessen") \
    else None
H._zwischenspeicher_leeren()
check("auch Muell in der Datei", S.galerie_stil_lesen() == "klassisch")
check("weiter() laeuft im Kreis",
      [S.galerie_stil_weiter() for _ in range(3)]
      == ["flow", "klassisch", "flow"])
S.galerie_stil_schreiben("klassisch")
H._zwischenspeicher_leeren()

# ---------------------------------------------------------------------------
print()
print("Test 2: nur auf HDMI")
# ---------------------------------------------------------------------------


class Tasten(object):
    def read_action(self, timeout=None):
        return "back"


def frontend(b, h, stil):
    S.galerie_stil_schreiben(stil)
    H._zwischenspeicher_leeren()
    H.SCREEN[:] = [b, h]
    f = H.make_frontend(page=1)
    f.inp = Tasten()
    return f


for b, h, stil, erwartet in ((1920, 1080, "flow", True),
                             (1280, 720, "flow", True),
                             (1080, 1920, "flow", True),
                             (320, 240, "flow", False),
                             (640, 480, "flow", False),
                             (1920, 1080, "klassisch", False)):
    f = frontend(b, h, stil)
    check("%4dx%-4d  %-9s -> %s" % (b, h, stil,
                                    "Coverflow" if erwartet else "klassisch"),
          f._galerie_flow() is erwartet,
          "" if f._galerie_flow() is erwartet else "%r" % f._galerie_flow())
check("die Schwelle ist dieselbe wie im Haus (720)",
      "720" in nur_code(koerper(_QF, "_galerie_flow", "Frontend")),
      "eine zweite Zahl waere eine zweite Gelegenheit, "
      "auseinanderzulaufen")

# ---------------------------------------------------------------------------
print()
print("Test 3: fuenf Plaetze, die Mitte am groessten, alles im Bild")
# ---------------------------------------------------------------------------
for b, h in ((1920, 1080), (1280, 720), (1080, 1920), (1920, 1200)):
    f = frontend(b, h, "flow")
    L = f.layout_items(True)
    geo = f.galerie_flow_geometrie(L)
    p = geo["plaetze"]
    ok_anzahl = len(p) == 5
    ok_mitte = ok_anzahl and p[2][0] == 0
    groessen = [e[3] for e in p]
    ok_gross = ok_anzahl and groessen[2] == max(groessen)
    ok_sym = ok_anzahl and groessen[0] == groessen[4] \
        and groessen[1] == groessen[3]
    ok_drin = all(e[1] >= 0 and e[1] + e[3] <= b
                  and e[2] >= 0 and e[2] + e[4] <= h for e in p)
    check("%4dx%-4d fuenf Plaetze" % (b, h), ok_anzahl, "%d" % len(p))
    check("%4dx%-4d die Mitte ist Platz 0 und am groessten" % (b, h),
          ok_mitte and ok_gross, "%r" % (groessen,))
    check("%4dx%-4d symmetrisch" % (b, h), ok_sym, "%r" % (groessen,))
    check("%4dx%-4d alles im Bild" % (b, h), ok_drin,
          "%r" % ([(e[1], e[2], e[3], e[4]) for e in p],))
    check("%4dx%-4d der Text beginnt unter der Reihe" % (b, h),
          geo["text_y"] > p[2][2] + p[2][4], "%r" % (geo["text_y"],))

# ---------------------------------------------------------------------------
print()
print("Test 4: die Ansicht zeichnet")
# ---------------------------------------------------------------------------
# DER EIGENTLICHE BEWEIS. Gezeichnet wird mit dem ECHTEN Weg, samt
# Kopfzeile, Karte, Fussleiste und Flip - nicht mit einer Nachbildung.
for b, h in ((1920, 1080), (1280, 720), (1080, 1920), (1920, 1200)):
    f = frontend(b, h, "flow")
    try:
        f.draw()
        # Und ein zweites Mal: beim zweiten Bild greift der schnelle
        # Pfad, und der raeumt frei statt zu loeschen. Genau dort
        # faellt eine negative Breite auf.
        f.item_i = 3
        f.draw()
        f.item_i = 0          # an den Rand - links fehlen Nachbarn
        f.draw()
        f.item_i = len(f._display_items()) - 1
        f.draw()
        ok, fehler = True, ""
    except Exception as e:                               # noqa: BLE001
        ok, fehler = False, "%s: %s" % (type(e).__name__, e)
        traceback.print_exc(limit=4)
    check("%4dx%-4d vier Schritte, auch an beiden Raendern" % (b, h),
          ok, fehler)

# Und die Gegenprobe: mit "klassisch" laeuft weiterhin der alte Weg.
f = frontend(1920, 1080, "klassisch")
try:
    f.draw()
    f.item_i = 3
    f.draw()
    ok, fehler = True, ""
except Exception as e:                                   # noqa: BLE001
    ok, fehler = False, "%s: %s" % (type(e).__name__, e)
check("klassisch zeichnet unveraendert weiter", ok, fehler)

# ---------------------------------------------------------------------------
print()
print("Test 5: kein zweiter Weg fuer etwas, das es schon gibt")
# ---------------------------------------------------------------------------
check("die Methode wurde gefunden", bool(_FLOW.strip()),
      "%d Zeichen" % len(_FLOW))
for ruf, wofuer in (("self._ansicht_cover(", "das Cover samt HD-Regel"),
                    ("self._beschreibung_zeichnen(", "die Beschreibung"),
                    ("self._spiel_infozeilen(", "die Datenzeilen"),
                    ("self._kachel_platzhalter(", "der leere Kasten"),
                    ("self._raster_kopf(", "die Kopfzeile"),
                    ("self._fusszeile_zeichnen(", "die Fusszeile"),
                    ("self._restore_row_bg(", "das Freiraeumen"),
                    ("self._rechtecke_flippen(", "der Rechteck-Flip")):
    check("%-30s -> %s" % (ruf, wofuer), ruf in _FLOW)
check("und der Uebersprung-Schalter ist derselbe",
      "ART._defer_uncached" in _FLOW and "ART._deferred_something" in _FLOW,
      "kein zweiter Mechanismus fuer dieselbe Frage (Build 244/300)")

# ---------------------------------------------------------------------------
print()
print("Test 6: erst das Cover, dann die Karte (Build 305)")
# ---------------------------------------------------------------------------
_i_cover = _FLOW.index("self._ansicht_cover(")
_i_karte = _FLOW.index("karte_mit_schatten(")
check("das Cover wird VOR der Karte geholt", _i_cover < _i_karte,
      "wer noch nicht weiss, wo das Cover hinkommt, kann seine "
      "Flaeche nicht aussparen")
check("und die Karte bekommt die Aussparung", "aussparen=" in _FLOW)
check("samt Hintergrundfarbe", "hintergrund_rgb=" in _FLOW)

# ---------------------------------------------------------------------------
print()
print("Test 7: der Verteiler steht an genau einer Stelle")
# ---------------------------------------------------------------------------
check("_draw_items_galerie() verteilt", "_galerie_flow()" in _ALT
      and "_draw_items_galerie_flow(" in _ALT)
check("und zwar GANZ oben",
      _ALT.index("_galerie_flow()") < _ALT.index("self.galerie_geometrie("),
      "sonst rechnet der klassische Weg erst und wirft es dann weg")
check("sonst entscheidet niemand ueber die Galerie",
      len(re.findall(r"_draw_items_galerie_flow\(", nur_code(_QF))) == 2,
      "einmal die Methode, einmal der Verteiler - mehr waere ein "
      "zweiter Weg hinein")

# ---------------------------------------------------------------------------
print()
print("Test 8: Menuepunkt, Zweig und Texte")
# ---------------------------------------------------------------------------
_qm = open(os.path.join(_REPO, "frontend", "fe", "menu.py"),
           encoding="utf-8").read()
check("der Menuepunkt steht im Systemmenue", '"galerie_stil"' in _qm)
check("und der Zweig behandelt ihn",
      'kind == "galerie_stil"' in _QF and "galerie_stil_weiter()" in _QF)
check("auf der Roehre sagt er, dass man nichts sehen wird",
      "galerie_stil_nur_hdmi" in _QF,
      "eine Einstellung, die stumm nichts tut, haelt man fuer kaputt")
for k in ("sys_galerie_stil", "galerie_stil_klassisch",
          "galerie_stil_flow", "galerie_stil_gesetzt",
          "galerie_stil_nur_hdmi"):
    e = TR.TRANSLATIONS.get(k)
    check("Text %-24s in beiden Sprachen" % k,
          bool(e) and bool(e.get("de")) and bool(e.get("en")),
          "" if e else "fehlt ganz")
for k in ("sys_galerie_stil", "galerie_stil_gesetzt"):
    for sp in ("de", "en"):
        check("%s/%s hat genau einen Platzhalter" % (k, sp),
              len(re.findall(r"%[sd]", TR.TRANSLATIONS[k][sp])) == 1)

shutil.rmtree(TMP, ignore_errors=True)

print()
if fails:
    print("ROT: %d Pruefung(en) fehlgeschlagen:" % len(fails))
    for f in fails:
        print("   - %s" % f)
    sys.exit(1)
print("ALLES GRUEN")
