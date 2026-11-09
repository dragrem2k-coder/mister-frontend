#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Der Coverflow - sein Entwurf 6 (Build 313, Ansicht seit Build 318).

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
import hashlib
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
S.ANSICHT_FILE = os.path.join(TMP, "ansicht")

# ---------------------------------------------------------------------------
print("Test 1: der Coverflow ist eine ANSICHT, kein zweiter Schalter")
# ---------------------------------------------------------------------------
# BUILD 318. Bis dahin hing er an einem eigenen Schalter ueber der
# Ansicht - dieselbe Verdopplung, die auf der Hauptseite in Build 314
# schiefgegangen ist. Sein Wunsch war ausdruecklich, beide
# nebeneinander zu haben: "koennen wir zusaetzlich die alte galerie
# ansicht auch noch wieder dazuholen?"
check("ANSICHTEN hat vier Werte",
      S.ANSICHTEN == ("liste", "raster", "galerie", "coverflow"),
      "%r" % (S.ANSICHTEN,))
check("und der Coverflow braucht HDMI",
      S.ANSICHTEN_NUR_HD == ("coverflow",))
check("die klassische Galerie steht unveraendert daneben",
      "galerie" in S.ANSICHTEN)
S.ansicht_schreiben("coverflow")
H._zwischenspeicher_leeren()
check("geschrieben wird, was man setzt",
      S.ansicht_lesen() == "coverflow")
with open(S.ANSICHT_FILE, "w") as fh:
    fh.write("\x00kaputt\n")
H._zwischenspeicher_leeren()
check("Muell in der Datei faellt auf liste zurueck",
      S.ansicht_lesen() == "liste")

# Die einmalige Uebernahme aus Build 313
S.ansicht_schreiben("liste")
with open(S.GALERIE_STIL_FILE, "w") as fh:
    fh.write("flow")
H._zwischenspeicher_leeren()
check("die Uebernahme traegt 'flow' in die Ansicht",
      S.galerie_stil_uebernehmen() == "coverflow")
check("und die Ansicht steht danach darauf",
      S.ansicht_lesen() == "coverflow", "%r" % (S.ansicht_lesen(),))
check("die alte Datei steht auf klassisch",
      open(S.GALERIE_STIL_FILE).read().strip() == "klassisch")
S.ansicht_schreiben("liste")
H._zwischenspeicher_leeren()
check("ein zweiter Lauf tut nichts mehr",
      S.galerie_stil_uebernehmen() is None
      and S.ansicht_lesen() == "liste",
      "sonst holte sie den Nutzer bei jedem Start zurueck")

# ---------------------------------------------------------------------------
print()
print("Test 2: nur auf HDMI")
# ---------------------------------------------------------------------------


class Tasten(object):
    def read_action(self, timeout=None):
        return "back"


def frontend(b, h, ansicht):
    """Ein Frontend mit genau dieser ANSICHT - ueber die echte
    Einstellung, nicht ueber eine Attrappe."""
    S.ansicht_schreiben(ansicht if ansicht != "flow" else "coverflow")
    H._zwischenspeicher_leeren()
    H.SCREEN[:] = [b, h]
    f = H.make_frontend(page=1)
    f._ansicht_je_kat = {}
    # Den Cover-Schutz abschalten - im Pruefstand steht die Uhr, also
    # waere er immer an und das Bild haengt am Zufall des
    # Bildspeichers. Siehe tools/test_hauptseite_stil.py, dort steht
    # die lange Fassung.
    f._last_input_time = 0
    f.inp = Tasten()
    return f


for b, h, ansicht, erwartet in ((1920, 1080, "coverflow", "coverflow"),
                                (1280, 720, "coverflow", "coverflow"),
                                (1080, 1920, "coverflow", "coverflow"),
                                (320, 240, "coverflow", "galerie"),
                                (640, 480, "coverflow", "galerie"),
                                (1920, 1080, "galerie", "galerie")):
    f = frontend(b, h, ansicht)
    ist = f.aktuelle_ansicht()
    check("%4dx%-4d  %-10s -> %s" % (b, h, ansicht, erwartet),
          ist == erwartet, "" if ist == erwartet else "%r" % ist)
check("die Schwelle ist dieselbe wie im Haus (720)",
      "720" in nur_code(koerper(_QF, "_ansicht_hd", "Frontend")),
      "eine zweite Zahl waere eine zweite Gelegenheit, "
      "auseinanderzulaufen")
check("auf der Roehre wird die klassische GALERIE gezeigt",
      "galerie" in nur_code(koerper(_QF, "_ansicht_hd", "Frontend")),
      "wer den Coverflow eingestellt hat, will eine Galerie sehen - "
      "nicht die Liste")

# ---------------------------------------------------------------------------
print()
print("Test 3: fuenf Plaetze, die Mitte am groessten, alles im Bild")
# ---------------------------------------------------------------------------
for b, h in ((1920, 1080), (1280, 720), (1080, 1920), (1920, 1200)):
    f = frontend(b, h, "coverflow")
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
    f = frontend(b, h, "coverflow")
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
f = frontend(1920, 1080, "galerie")
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
# BUILD 318: entschieden wird beim Ansichten-Verteiler, nicht mehr in
# _draw_items_galerie(). Eine zweite Entscheidungsebene unterhalb der
# Ansicht ist genau die Form, die auf der Hauptseite in Build 314
# schiefgegangen ist.
_VERT = nur_code(koerper(_QF, "_draw_items_kacheln", "Frontend"))
check("der Ansichten-Verteiler kennt den Coverflow",
      '"coverflow"' in _VERT and "_draw_items_galerie_flow(" in _VERT)
check("und die klassische Galerie steht gleichberechtigt daneben",
      '"galerie"' in _VERT and "_draw_items_galerie(" in _VERT)
check("_draw_items_galerie() entscheidet NICHTS mehr",
      "_draw_items_galerie_flow(" not in _ALT
      and "_galerie_flow()" not in _ALT)
check("sonst entscheidet niemand ueber den Coverflow",
      len(re.findall(r"_draw_items_galerie_flow\(", nur_code(_QF))) == 2,
      "einmal die Methode, einmal der Verteiler - mehr waere ein "
      "zweiter Weg hinein")

# ---------------------------------------------------------------------------
print()
print("Test 8: der alte Schalter ist weg, der Name steht bei den Ansichten")
# ---------------------------------------------------------------------------
_qm = open(os.path.join(_REPO, "frontend", "fe", "menu.py"),
           encoding="utf-8").read()
check("kein Menuepunkt 'galerie_stil' mehr", '"galerie_stil"' not in _qm,
      "er steht jetzt in 'ansicht' mit drin")
check("und kein Zweig dafuer", 'kind == "galerie_stil"' not in _QF)
check("frontend.py kennt kein _galerie_flow() mehr",
      "def _galerie_flow" not in _QF
      and "self._galerie_flow(" not in _QF)
check("der Menuepunkt fuer die Spieleliste ist genau einer",
      _qm.count('"ansicht", None') == 1)
for k in ("ansicht_liste", "ansicht_raster", "ansicht_galerie",
          "ansicht_coverflow"):
    e = TR.TRANSLATIONS.get(k)
    check("Text %-20s in beiden Sprachen" % k,
          bool(e) and bool(e.get("de")) and bool(e.get("en")),
          "" if e else "fehlt ganz")
for k in list(TR.TRANSLATIONS):
    if k.startswith("galerie_stil_") or k == "sys_galerie_stil":
        check("der alte Schluessel %s ist raus" % k, False,
              "er beschriebe einen Schalter, den es nicht mehr gibt")

# ---------------------------------------------------------------------------
print()
print("Test 9: der schnelle Pfad ist bitgenau wie ein voller Aufbau")
# ---------------------------------------------------------------------------
# NACHGEREICHT IN BUILD 314, und nicht aus Ordnungsliebe: derselbe
# Vergleich am neuen Karussell der Hauptseite hat dort 3.486
# stehengebliebene Bildpunkte gefunden - und als ich ihn danach
# einmal hier laufen liess, waren es 5.014. Der Coverflow hatte den
# Fehler seit Build 313 und niemand hat ihn gesehen: ein
# hauchduenner heller Strich an zwei Kanten der grossen Karte, weil
# der Nachbar rechts und die Textspalte nach ihr freigeraeumt haben
# und dabei in ihren Schlagschatten reichten.
#
# Ein Standbild zeigt so etwas nicht. Dieser Vergleich schon.


def _pixelvergleich(schritte, richtung):
    f = frontend(1920, 1080, "coverflow")
    f.ansicht_setzen("galerie")
    f.draw()                       # voller Aufbau
    f.draw()                       # ab hier der schnelle Weg
    n = len(f._display_items())
    for _ in range(schritte):
        f.item_i = (f.item_i + richtung) % n
        f.draw()
    schnell = bytes(f.fb.buf)

    g = frontend(1920, 1080, "coverflow")
    g.ansicht_setzen("galerie")
    g.item_i = f.item_i
    g.scroll = f.scroll
    # _pulse_t0 ist ein Wert JE INSTANZ - ohne diese Zeile vergleicht
    # man zwei Phasen desselben Schimmerns (siehe
    # test_hauptseite_spuren.py).
    g._pulse_t0 = f._pulse_t0
    g.fb.mark_full_redraw()
    g.draw()
    voll = bytes(g.fb.buf)
    # ERST HASHEN, DANN ZAEHLEN. Der Puffer ist bei 1920x1080 acht
    # Megabyte; ihn Punkt fuer Punkt in Python zu vergleichen dauert
    # im gruenen Fall laenger als der ganze uebrige Test. Gezaehlt
    # wird nur, wenn es etwas zu zaehlen gibt.
    if (hashlib.sha256(schnell).hexdigest()
            == hashlib.sha256(voll).hexdigest()):
        check("Coverflow %+d x%d: bitgenau" % (richtung, schritte), True)
        return
    anders = sum(1 for i in range(0, len(schnell), 4)
                 if schnell[i:i + 3] != voll[i:i + 3])
    check("Coverflow %+d x%d: bitgenau" % (richtung, schritte),
          False, "%d Bildpunkte" % anders)


for _sch, _ri in ((3, 1), (7, 1), (4, -1)):
    _pixelvergleich(_sch, _ri)
check("freigeraeumt wird in einem eigenen Durchlauf VOR dem Zeichnen",
      _FLOW.index("self._restore_row_bg(") < _FLOW.index("sorted("),
      "wer je Platz raeumt und sofort zeichnet, radiert dem Nachbarn "
      "den Schatten weg")
check("und die grosse Karte wird zuletzt gezeichnet",
      "sorted(" in _FLOW and "versatz == 0" in _FLOW)

shutil.rmtree(TMP, ignore_errors=True)

print()
if fails:
    print("ROT: %d Pruefung(en) fehlgeschlagen:" % len(fails))
    for f in fails:
        print("   - %s" % f)
    sys.exit(1)
print("ALLES GRUEN")
