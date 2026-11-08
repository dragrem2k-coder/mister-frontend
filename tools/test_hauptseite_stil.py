#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Die drei neuen Hauptseiten - seine Entwuerfe 7, 8 und 9 (Build 314).

NUTZERWUNSCH vom 08.11., woertlich: "alle drei machen unter menue mit
schalter zum hin und herwechseln, koenntest du bitte diese als
systemarts / boxarts dann verwenden? fuer das neue?" - dazu 18 Fotos
von Konsolen.

Also: Kachelwand, Dashboard und Karussell als Stile an EINEM Schalter,
nur auf HDMI, und die Geraetefotos als Kategoriebild mit Rueckfall auf
die vorhandenen Abzeichen.

WAS DIESER TEST SICHERT:
  1. die Vorgabe ist "klassisch", kaputte Werte fallen darauf zurueck,
     und der Schalter laeuft im Kreis,
  2. die drei Stile laufen NUR auf HDMI - auf der Roehre bleibt alles
     wie es war, auch wenn der Schalter steht,
  3. die Geometrien liegen im Bild und ueberlappen sich nicht,
  4. alle drei zeichnen auf allen HD-Groessen ohne Fehler, auch an den
     Raendern der Kategorienliste,
  5. DER SCHNELLE PFAD IST BITGENAU WIE EIN VOLLER AUFBAU - das ist
     der eigentliche Beweis, und derselbe wie in
     test_hauptseite_spuren.py,
  6. sie bauen KEINEN zweiten Bild-, Karten- oder Freiraeum-Weg,
     sondern benutzen die vorhandenen,
  7. das Bild wird VOR der Karte geholt (die Aussparung aus Build 305),
  8. der Fotosatz wird bevorzugt, UND es gibt den Rueckfall auf das
     Abzeichen,
  9. die Fotodateien selbst sind heil und einheitlich,
 10. Menuepunkt, Zweig und Texte sind da,
 11. und der klassische Weg bleibt unangetastet.

Ausfuehren:
    python3 tools/test_hauptseite_stil.py
"""
import hashlib
import os
import re
import shutil
import struct
import sys
import tempfile
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H          # noqa: E402

import fe.art as A            # noqa: E402
import fe.settings as S       # noqa: E402
import fe.translations as TR  # noqa: E402
from _quelle import koerper, nur_code                     # noqa: E402

fm = H.fm

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYSART = os.path.join(_REPO, "frontend", "sysart")
FOTOS = os.path.join(_REPO, "frontend", "sysart_foto")
A.SYSART_BASE = fm.SYSART_BASE = SYSART
A.SYSART_FOTO_BASE = fm.SYSART_FOTO_BASE = FOTOS

_QF = open(os.path.join(_REPO, "frontend", "frontend.py"),
           encoding="utf-8", errors="replace").read()
_WAND = nur_code(koerper(_QF, "_draw_cats_kachelwand", "Frontend"))
_WKACHEL = nur_code(koerper(_QF, "_wand_kachel_zeichnen", "Frontend"))
_DASH = nur_code(koerper(_QF, "_draw_cats_dashboard", "Frontend"))
_TAFEL = nur_code(koerper(_QF, "_dash_tafel_zeichnen", "Frontend"))
_ZEILE = nur_code(koerper(_QF, "_dash_zeile_zeichnen", "Frontend"))
_KAR = nur_code(koerper(_QF, "_draw_cats_karussell", "Frontend"))
_IMPL = nur_code(koerper(_QF, "_draw_page_cats_impl", "Frontend"))
_STIL = nur_code(koerper(_QF, "_haupt_stil", "Frontend"))
_LOGO = nur_code(koerper(_QF, "_kat_logo", "Frontend"))

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


def gleich(a, b):
    return (hashlib.sha256(bytes(a)).hexdigest()
            == hashlib.sha256(bytes(b)).hexdigest())


def abweichung(a, b):
    ab, bb = bytes(a), bytes(b)
    stellen = [i // 4 for i in range(0, len(ab), 4)
               if ab[i:i + 3] != bb[i:i + 3]]
    if not stellen:
        return 0, []
    return len(stellen), stellen[:3]


print(__doc__.strip().split("\n")[0])
print()

TMP = tempfile.mkdtemp(prefix="hauptstil_")
S.HAUPT_STIL_FILE = os.path.join(TMP, "haupt_stil.txt")

# Die Kategorien fuer die Bilder: eine Mischung aus Namen MIT Foto und
# Namen OHNE - genau der Fall, der auf seinem Geraet eintritt (17
# Fotos, 60 Abzeichen). Ein Test nur mit Fotos haette den Rueckfall nie
# angefasst.
MIT_FOTO = ["NES", "SNES", "GAMEBOY", "GBC", "GBA", "N64", "Genesis",
            "SMS", "MegaCD", "PSX", "Saturn", "TGFX16", "NEOGEO",
            "ATARI2600", "ARCADE", "SUPERGAMEBOY", "PHYSICAL_DISC_CORES"]
OHNE_FOTO = ["FAVORITES", "CONTINUE", "RECENT", "COLLECTIONS",
             "GAMEGEAR", "ATARILYNX", "COLECOVISION", "SYSTEM"]
KEYS = OHNE_FOTO[:4] + MIT_FOTO + OHNE_FOTO[4:]


def seite(w, h, stil, anzahl=None):
    S.haupt_stil_schreiben(stil)
    H._zwischenspeicher_leeren()
    H.set_screen(w, h)
    f = H.make_frontend(page=0)
    namen = KEYS if anzahl is None else KEYS[:anzahl]
    # Der Systemkey MUSS gesetzt sein - sonst liefert
    # _category_art_key() None und geprueft wuerde der Platzhalter
    # statt der Karte mit dem Bild. Derselbe Stolperstein wie in
    # test_hauptseite_spuren.py.
    f.cats = [(k, {"items": [], "folders": {}}, k) for k in namen]
    f.cat_i = 0
    f.cat_scroll = 0
    return f


# ---------------------------------------------------------------------------
print("Test 1: der Schalter")
# ---------------------------------------------------------------------------
check("ohne Datei: klassisch", S.haupt_stil_lesen() == "klassisch",
      "%r - das ist der gemessene Zustand" % (S.haupt_stil_lesen(),))
for wert in ("kachelwand", "dashboard", "karussell"):
    S.haupt_stil_schreiben(wert)
    H._zwischenspeicher_leeren()
    check("geschrieben wird, was man setzt (%s)" % wert,
          S.haupt_stil_lesen() == wert)
S.haupt_stil_schreiben("quatsch")
H._zwischenspeicher_leeren()
check("ein unbekannter Wert faellt auf klassisch zurueck",
      S.haupt_stil_lesen() == "klassisch",
      "eine von Hand verstellte Datei darf das Frontend nicht in einen "
      "Zustand bringen, aus dem man ohne Texteditor nicht herauskommt")
with open(S.HAUPT_STIL_FILE, "w") as fh:
    fh.write("\x00kaputt\n")
H._zwischenspeicher_leeren()
check("auch Muell in der Datei", S.haupt_stil_lesen() == "klassisch")
_runde = [S.haupt_stil_weiter() for _ in range(5)]
check("weiter() laeuft im Kreis durch alle vier",
      _runde == ["kachelwand", "dashboard", "karussell", "klassisch",
                 "kachelwand"],
      "%r" % (_runde,))
check("und die Liste hat genau diese vier",
      S.HAUPT_STILE == ("klassisch", "kachelwand", "dashboard",
                        "karussell"),
      "%r" % (S.HAUPT_STILE,))

# ---------------------------------------------------------------------------
print()
print("Test 2: nur auf HDMI")
# ---------------------------------------------------------------------------
for b, h, stil, erwartet in ((1920, 1080, "kachelwand", "kachelwand"),
                             (1920, 1080, "dashboard", "dashboard"),
                             (1920, 1080, "karussell", "karussell"),
                             (1280, 720, "kachelwand", "kachelwand"),
                             (1080, 1920, "dashboard", "dashboard"),
                             (320, 240, "kachelwand", "klassisch"),
                             (640, 480, "dashboard", "klassisch"),
                             (640, 480, "karussell", "klassisch"),
                             (1920, 1080, "klassisch", "klassisch")):
    f = seite(b, h, stil)
    ist = f._haupt_stil()
    check("%4dx%-4d  %-10s -> %s" % (b, h, stil, erwartet),
          ist == erwartet, "" if ist == erwartet else "%r" % ist)
check("die Schwelle ist dieselbe wie im Haus (720)", "720" in _STIL,
      "eine zweite Zahl waere eine zweite Gelegenheit, "
      "auseinanderzulaufen")
check("auf der Roehre wird der Wert trotzdem GESCHRIEBEN",
      "haupt_stil_weiter()" in nur_code(_QF)
      and "haupt_stil_nur_hdmi" in _QF,
      "er gilt ja fuers naechste Mal am Fernseher")

# ---------------------------------------------------------------------------
print()
print("Test 3: die Geometrien liegen im Bild")
# ---------------------------------------------------------------------------
for b, h in ((1920, 1080), (1280, 720), (1080, 1920), (1920, 1200),
             (2560, 1440)):
    f = seite(b, h, "kachelwand")
    KL = f.kat_layout()
    g = f.kachelwand_geometrie(KL)
    letzte = g["spalten"] * g["zeilen"] - 1
    fx, fy, fw, fh = f._kachel_feld(g, letzte)
    check("%4dx%-4d Kachelwand: letzte Kachel im Bild" % (b, h),
          fx >= 0 and fy >= 0 and fx + fw <= b and fy + fh <= h,
          "%r" % ((fx, fy, fw, fh),))
    check("%4dx%-4d Kachelwand: Bild und Text passen in die Kachel"
          % (b, h),
          g["bild_h"] + g["text_h"] + 2 * g["pad"] <= g["kachel_h"],
          "Bild %d + Text %d + Polster %d > Kachel %d"
          % (g["bild_h"], g["text_h"], 2 * g["pad"], g["kachel_h"]))
    check("%4dx%-4d Kachelwand: mindestens 2x1" % (b, h),
          g["spalten"] >= 2 and g["zeilen"] >= 1,
          "%dx%d" % (g["spalten"], g["zeilen"]))

    f = seite(b, h, "dashboard")
    g = f.dashboard_geometrie(f.kat_layout())
    check("%4dx%-4d Dashboard: Liste und Tafel ueberlappen nicht" % (b, h),
          g["ox"] + g["lw"] <= g["px"],
          "Liste bis %d, Tafel ab %d" % (g["ox"] + g["lw"], g["px"]))
    check("%4dx%-4d Dashboard: Tafel im Bild" % (b, h),
          g["px"] + g["pw"] <= b and g["py"] + g["ph"] <= h,
          "%r" % ((g["px"], g["py"], g["pw"], g["ph"]),))
    for fx, fy, fw, fh in g["felder"]:
        check("%4dx%-4d Dashboard: Feld liegt in der Tafel" % (b, h),
              fx >= g["px"] and fy >= g["py"]
              and fx + fw <= g["px"] + g["pw"]
              and fy + fh <= g["py"] + g["ph"],
              "%r" % ((fx, fy, fw, fh),))
    check("%4dx%-4d Dashboard: der Text steht unter dem Bild" % (b, h),
          g["text_y"] >= g["bild_y"] + g["bild_h"])

    f = seite(b, h, "karussell")
    g = f.karussell_geometrie(f.kat_layout())
    p = g["plaetze"]
    groessen = [e[3] for e in p]
    check("%4dx%-4d Karussell: fuenf Plaetze" % (b, h), len(p) == 5,
          "%d" % len(p))
    check("%4dx%-4d Karussell: die Mitte ist Platz 0 und am groessten"
          % (b, h), p[2][0] == 0 and groessen[2] == max(groessen),
          "%r" % (groessen,))
    check("%4dx%-4d Karussell: symmetrisch" % (b, h),
          groessen[0] == groessen[4] and groessen[1] == groessen[3],
          "%r" % (groessen,))
    check("%4dx%-4d Karussell: alles im Bild" % (b, h),
          all(e[1] >= 0 and e[1] + e[3] <= b
              and e[2] >= 0 and e[2] + e[4] <= h for e in p),
          "%r" % ([(e[1], e[2], e[3], e[4]) for e in p],))
    check("%4dx%-4d Karussell: der Text beginnt unter der Reihe" % (b, h),
          g["text_y"] > p[2][2] + p[2][4])
    check("%4dx%-4d Karussell: die Karten liegen quer" % (b, h),
          g["mitte_b"] > g["mitte_h"],
          "%dx%d - ein Geraetefoto liegt quer, ein Spielcover steht "
          "hochkant" % (g["mitte_b"], g["mitte_h"]))

# ---------------------------------------------------------------------------
print()
print("Test 4: alle drei zeichnen")
# ---------------------------------------------------------------------------
# DER ECHTE WEG, nicht eine Nachbildung: draw_page_cats() samt
# Kopfzeile, Karten, Fussleiste und Verteiler.
for stil in ("kachelwand", "dashboard", "karussell"):
    for b, h in ((1920, 1080), (1280, 720), (1080, 1920), (2560, 1440)):
        f = seite(b, h, stil)
        try:
            f.draw_page_cats(flip=False)
            f.cat_i = 1
            f.draw_page_cats(flip=False)       # ab hier der schnelle Weg
            f.cat_i = len(f.cats) - 1          # ans Ende
            f.draw_page_cats(flip=False)
            f.cat_i = 0                        # und zurueck an den Anfang
            f.draw_page_cats(flip=False)
            ok, fehler = True, ""
        except Exception as e:                           # noqa: BLE001
            ok, fehler = False, "%s: %s" % (type(e).__name__, e)
            traceback.print_exc(limit=4)
        check("%-10s %4dx%-4d vier Schritte, auch an beiden Raendern"
              % (stil, b, h), ok, fehler)
    # Und mit EINER einzigen Kategorie - der Fall, in dem im Karussell
    # alle fuenf Plaetze auf denselben Eintrag zeigen und im Raster
    # die Seite nicht voll wird.
    f = seite(1920, 1080, stil, anzahl=1)
    try:
        f.draw_page_cats(flip=False)
        f.draw_page_cats(flip=False)
        ok, fehler = True, ""
    except Exception as e:                               # noqa: BLE001
        ok, fehler = False, "%s: %s" % (type(e).__name__, e)
        traceback.print_exc(limit=4)
    check("%-10s eine einzige Kategorie" % stil, ok, fehler)

# Gegenprobe: mit "klassisch" laeuft weiterhin der alte Weg.
f = seite(1920, 1080, "klassisch")
try:
    f.draw_page_cats(flip=False)
    f.cat_i = 2
    f.draw_page_cats(flip=False)
    ok, fehler = True, ""
except Exception as e:                                   # noqa: BLE001
    ok, fehler = False, "%s: %s" % (type(e).__name__, e)
check("klassisch zeichnet unveraendert weiter", ok, fehler)

# ---------------------------------------------------------------------------
print()
print("Test 5: der schnelle Pfad ist bitgenau wie ein voller Aufbau")
# ---------------------------------------------------------------------------
# DER EIGENTLICHE BEWEIS. Alles andere in dieser Datei prueft, dass
# etwas aufgerufen wird; das hier prueft, dass hinterher dasselbe Bild
# dasteht. Vier der letzten fuenf Zeichenfehler im Projekt (Build
# 80/122/125/128) waren stehengebliebene Reste, und keiner davon waere
# ohne diesen Vergleich aufgefallen.


def lauf(stil, w, h, schritte, richtung=1):
    f = seite(stil=stil, w=w, h=h)
    f.draw_page_cats(flip=False)          # voller Aufbau
    f.draw_page_cats(flip=False)          # ab hier der schnelle Weg
    n = len(f.cats)
    for _ in range(schritte):
        f.cat_i = (f.cat_i + richtung) % n
        f.draw_page_cats(flip=False)
    schnell = bytes(f.fb.buf)

    g = seite(stil=stil, w=w, h=h)
    g.cat_i = f.cat_i
    g.cat_scroll = f.cat_scroll
    # _pulse_t0 ist ein Wert JE INSTANZ - ohne diese Zeile vergleicht
    # man zwei Phasen desselben Schimmerns und haelt den
    # Farbunterschied fuer einen Zeichenfehler (siehe
    # test_hauptseite_spuren.py).
    g._pulse_t0 = f._pulse_t0
    g.fb.mark_full_redraw()
    g.draw_page_cats(flip=False)
    label = "%-10s %4dx%-4d %+d x%d" % (stil, w, h, richtung, schritte)
    if gleich(schnell, g.fb.buf):
        check(label + ": bitgenau", True)
    else:
        n_, wo = abweichung(schnell, g.fb.buf)
        check(label + ": bitgenau", False,
              "%d Bildpunkte, z.B. %s" % (n_, wo))


for stil in ("kachelwand", "dashboard", "karussell"):
    for w, h in ((1920, 1080), (1280, 720)):
        lauf(stil, w, h, 3, 1)
        lauf(stil, w, h, 7, 1)
        lauf(stil, w, h, 4, -1)

# ---------------------------------------------------------------------------
print()
print("Test 6: kein zweiter Weg fuer etwas, das es schon gibt")
# ---------------------------------------------------------------------------
for name, quelle in (("Kachelwand", _WAND + _WKACHEL),
                     ("Dashboard", _DASH + _TAFEL + _ZEILE),
                     ("Karussell", _KAR)):
    check("%s: Quelltext gefunden" % name, bool(quelle.strip()),
          "%d Zeichen" % len(quelle))
    for ruf, wofuer in (("self._kat_logo(", "das Kategoriebild"),
                        ("self._kachel_platzhalter(", "der leere Kasten"),
                        ("self._restore_row_bg(", "das Freiraeumen")):
        check("%-11s %-28s -> %s" % (name, ruf, wofuer), ruf in quelle)
    # DIE ZAHLEN KOMMEN AUS EINEM DER BEIDEN VORHANDENEN HELFER -
    # welcher, ist Sache des Stils: die Kachelwand und das Dashboard
    # brauchen die Einzelwerte (_kat_zahlen), das Karussell die
    # fertigen Zeilen (_kat_infozeilen). Was KEINER darf, ist selbst
    # durch die Eintraege laufen; genau das waere der zweite Weg.
    check("%s: die Zahlen kommen aus einem vorhandenen Helfer" % name,
          "self._kat_zahlen(" in quelle
          or "self._kat_infozeilen(" in quelle)
    check("%s: und zaehlt NICHT selbst" % name,
          'node.get("items"' not in quelle
          and '.get("items", ())' not in quelle,
          "ein Durchlauf ueber die Eintraege je Kachel und Schritt "
          "waere genau die Sorte Aufwand, die wir uns abgewoehnt haben")
for name, quelle in (("Kachelwand", _WAND), ("Dashboard", _DASH),
                     ("Karussell", _KAR)):
    for ruf in ("self._kat_kopf(", "self._kat_fusszeile(",
                "self._rechtecke_flippen(", "self._overlay_active()",
                "fb.full_redraw_gen"):
        check("%-11s %s" % (name, ruf), ruf in quelle)
check("die Kachelwand benutzt das Kachelfeld der Hauptseite",
      "self._kachel_feld(" in _WKACHEL,
      "keine zweite Rechnung fuer dieselbe Kachelposition")
check("das Karussell rechnet umlaufend",
      "% gesamt" in _KAR,
      "in einem Karussell gibt es kein 'da ist nichts mehr'")
check("die Aussparung wird an EINER Stelle gerechnet",
      len(re.findall(r"def _kat_bild_luecke", nur_code(_QF))) == 1
      and "_kat_bild_luecke(" in _WKACHEL
      and "_kat_bild_luecke(" in _TAFEL
      and "_kat_bild_luecke(" in _KAR)

# ---------------------------------------------------------------------------
print()
print("Test 7: erst das Bild, dann die Karte (Build 305)")
# ---------------------------------------------------------------------------
for name, quelle in (("Kachelwand", _WKACHEL), ("Dashboard", _TAFEL),
                     ("Karussell", _KAR)):
    check("%s: das Bild wird VOR der Karte geholt" % name,
          quelle.index("self._kat_logo(")
          < quelle.index("karte_mit_schatten("),
          "wer noch nicht weiss, wo das Bild hinkommt, kann seine "
          "Flaeche nicht aussparen")
    check("%s: und die Karte bekommt die Aussparung" % name,
          "aussparen=" in quelle and "hintergrund_rgb=" in quelle)

# ---------------------------------------------------------------------------
print()
print("Test 8: der Fotosatz - Vorrang UND Rueckfall")
# ---------------------------------------------------------------------------
check("_kat_logo kennt den Fotosatz",
      "SYSART_FOTO_BASE" in _LOGO and "foto" in _LOGO)
check("gefragt wird ueber die gemerkte Liste, nicht ueber einen "
      "zweiten get_scaled-Versuch",
      "_sysart_foto_namen()" in _LOGO,
      "ein fehlendes Bild und ein uebersprungenes liefern beide None")

f = seite(1920, 1080, "kachelwand")
namen = f._sysart_foto_namen()
check("der Fotosatz wird gefunden", len(namen) >= 17,
      "%d Dateien in %s" % (len(namen), os.path.basename(FOTOS)))

_gefragt = []
_echt = A.ART.get_scaled


def _mitschreiben(pfad, *a, **k):
    _gefragt.append(pfad)
    return _echt(pfad, *a, **k)


A.ART.get_scaled = _mitschreiben
try:
    for idx, key in enumerate(KEYS):
        _gefragt[:] = []
        f._kat_logo(idx, 120, 90, foto=True)
        aus_foto = any(p.startswith(FOTOS) for p in _gefragt)
        soll = key in MIT_FOTO
        check("%-20s -> %s" % (key, "Foto" if soll else "Abzeichen"),
              aus_foto is soll, "%r" % (_gefragt,))
    # Und die Gegenprobe: OHNE foto=True kommt IMMER das Abzeichen -
    # sonst haetten die drei klassischen Ansichten heimlich ein neues
    # Aussehen bekommen, und davon war nie die Rede.
    _gefragt[:] = []
    f._kat_logo(KEYS.index("NES"), 120, 90)
    check("ohne foto=True bleibt es beim Abzeichen",
          _gefragt and all(p.startswith(SYSART)
                           and not p.startswith(FOTOS) for p in _gefragt),
          "%r" % (_gefragt,))
finally:
    A.ART.get_scaled = _echt

check("die drei klassischen Ansichten fragen NICHT nach Fotos",
      "foto=True" not in nur_code(
          koerper(_QF, "_kat_kachel_zeichnen", "Frontend")),
      "sein Wunsch war ausdruecklich 'fuer das neue'")

# ---------------------------------------------------------------------------
print()
print("Test 9: die Fotodateien sind heil und einheitlich")
# ---------------------------------------------------------------------------
PANEL = (28, 32, 44)
dateien = sorted(n for n in os.listdir(FOTOS) if n.endswith(".art"))
check("es liegen Dateien da", len(dateien) >= 17, "%d" % len(dateien))
masse = set()
for n in dateien:
    roh = open(os.path.join(FOTOS, n), "rb").read()
    kopf_ok = roh[:4] == b"ART1"
    if not kopf_ok:
        check("%-24s ART1-Kopf" % n, False)
        continue
    b, h = struct.unpack("<HH", roh[4:8])
    masse.add((b, h))
    import zlib
    try:
        pix = zlib.decompress(roh[8:])
    except zlib.error as e:                              # noqa: BLE001
        check("%-24s entpackbar" % n, False, str(e))
        continue
    laenge_ok = len(pix) == b * h * 4
    # Die Ecke MUSS C_PANEL sein (BGRA) - das Frontend blittet die
    # Datei undurchsichtig und sieht den Alphakanal gar nicht an. Eine
    # andere Eckfarbe waere auf der Karte ein sichtbarer Kasten.
    ecke = (pix[2], pix[1], pix[0])
    check("%-24s %dx%d, %d Bytes, Ecke %r"
          % (n, b, h, len(pix), ecke),
          laenge_ok and ecke == PANEL)
check("alle Fotos haben dasselbe Mass", len(masse) == 1, "%r" % (masse,))
check("und zwar quer", bool(masse) and list(masse)[0][0]
      > list(masse)[0][1], "%r" % (masse,))
check("die Abzeichen sind unangetastet geblieben",
      os.path.exists(os.path.join(SYSART, "NES.art"))
      and struct.unpack(
          "<HH", open(os.path.join(SYSART, "NES.art"), "rb").read()[4:8])
      == (320, 420),
      "sysart/ bleibt hochkant 320x420, der Fotosatz liegt daneben")
check("das Werkzeug zum Nachliefern liegt bei",
      os.path.exists(os.path.join(_REPO, "PC-Tools",
                                  "sysart_foto_convert.py")))

# ---------------------------------------------------------------------------
print()
print("Test 10: der Verteiler steht an genau einer Stelle")
# ---------------------------------------------------------------------------
check("_draw_page_cats_impl() verteilt", "_haupt_stil()" in _IMPL
      and "_draw_cats_stil(" in _IMPL)
check("und zwar VOR der Ansicht",
      _IMPL.index("_draw_cats_stil(") < _IMPL.index("_draw_cats_kacheln("),
      "ein Stil ist eine ganze Hauptseite, keine Anordnung in einer")
check("sonst entscheidet niemand ueber die Hauptseite",
      len(re.findall(r"_draw_cats_stil\(", nur_code(_QF))) == 2,
      "einmal die Methode, einmal der Verteiler - mehr waere ein "
      "zweiter Weg hinein")
_VERT = nur_code(koerper(_QF, "_draw_cats_stil", "Frontend"))
for stil in ("kachelwand", "dashboard", "karussell"):
    check("der Verteiler kennt %s" % stil,
          '"%s"' % stil in _VERT and "_draw_cats_%s(" % stil in _VERT)
check("und ein unbekannter Stil faellt durch",
      "return False" in _VERT,
      "sonst zeichnet gar nichts, statt klassisch zu zeichnen")

# ---------------------------------------------------------------------------
print()
print("Test 11: Menuepunkt, Zweig und Texte")
# ---------------------------------------------------------------------------
_qm = open(os.path.join(_REPO, "frontend", "fe", "menu.py"),
           encoding="utf-8").read()
check("der Menuepunkt steht im Systemmenue", '"haupt_stil"' in _qm)
check("er steht direkt unter der Ansicht der Hauptseite",
      _qm.index('"ansicht_haupt"') < _qm.index('"haupt_stil"'),
      "dieselbe Seite, nur eine Stufe tiefer")
check("und der Zweig behandelt ihn",
      'kind == "haupt_stil"' in _QF and "haupt_stil_weiter()" in _QF)
check("auf der Roehre sagt er, dass man nichts sehen wird",
      "haupt_stil_nur_hdmi" in _QF,
      "eine Einstellung, die stumm nichts tut, haelt man fuer kaputt")
for k in ("sys_haupt_stil", "haupt_stil_klassisch",
          "haupt_stil_kachelwand", "haupt_stil_dashboard",
          "haupt_stil_karussell", "haupt_stil_gesetzt",
          "haupt_stil_nur_hdmi", "dash_eintraege", "dash_ordner",
          "dash_favoriten", "dash_anteil"):
    e = TR.TRANSLATIONS.get(k)
    check("Text %-24s in beiden Sprachen" % k,
          bool(e) and bool(e.get("de")) and bool(e.get("en")),
          "" if e else "fehlt ganz")
for k in ("sys_haupt_stil", "haupt_stil_gesetzt"):
    for sp in ("de", "en"):
        check("%s/%s hat genau einen Platzhalter" % (k, sp),
              len(re.findall(r"%[sd]", TR.TRANSLATIONS[k][sp])) == 1)
# Die Stilnamen werden WOERTLICH nachgeschlagen - zusammengesetzte
# Schluessel ("haupt_stil_" + wert) sieht die Vollstaendigkeitspruefung
# nicht, und genau daran ist Build 309 einmal haengengeblieben. Hier
# ist das Zusammensetzen in Ordnung, WEIL dieser Test jeden der vier
# Schluessel einzeln nennt - die Liste oben ist der Ersatz.
for wert in S.HAUPT_STILE:
    check("Stilname haupt_stil_%s existiert" % wert,
          ("haupt_stil_" + wert) in TR.TRANSLATIONS)

# ---------------------------------------------------------------------------
print()
print("Test 12: ECHTE Tastenschritte, einmal rundherum")
# ---------------------------------------------------------------------------
# NACHGEREICHT IN BUILD 315, und zwar wegen eines Fehlers, den Test 5
# NICHT gefunden hat: er ruft draw_page_cats() direkt, die Taste aber
# geht zuerst durch _draw_navigate_cats(). Und dieser leichte Pfad
# fragte nur nach der ANSICHT, nicht nach dem STIL - bei Ansicht
# "liste" und Stil "kachelwand" hielt er sich fuer zustaendig, malte
# zwei klassische Listenzeilen mitten in die Kachelwand und meldete
# "erledigt".
#
# Gemeldet wurde das so: "wenn ich die ansicht wechsel baut sich die
# alte dahinter auf und es gibt ein durcheinander, beide ansichten
# ueberschneiden sich" - und praeziser: "wenn ich quasi in der listen
# ansicht auf der hauptseiten nach unten durchscrolle und es oben
# wieder anfaengt".
#
# Deshalb hier der ganze Weg, so wie die Taste ihn nimmt, einmal
# komplett rundherum samt Umlauf von der letzten auf die erste
# Kategorie.


def rundherum(stil, w=1920, h=1080):
    f = seite(w, h, stil)
    f.draw_page_cats(flip=False)
    n = len(f.cats)
    schlecht = []
    for _ in range(n + 2):
        alt = f.cat_i
        f.cat_i = (f.cat_i + 1) % n       # genau das tut nav_anwenden()
        if not f._draw_navigate_cats(alt):
            f.draw_page_cats(flip=False)
        ist = bytes(f.fb.buf)
        g = seite(w, h, stil)
        g.cat_i = f.cat_i
        g.cat_scroll = f.cat_scroll
        g._pulse_t0 = f._pulse_t0
        g.fb.mark_full_redraw()
        g.draw_page_cats(flip=False)
        if not gleich(ist, g.fb.buf):
            schlecht.append((f.cat_i, abweichung(ist, g.fb.buf)[0]))
    check("%-11s %d Tastenschritte bitgenau" % (stil, n + 2),
          not schlecht,
          "" if not schlecht else "%d Schritte daneben, erster bei "
          "cat_i=%d mit %d Bildpunkten"
          % (len(schlecht), schlecht[0][0], schlecht[0][1]))


for _stil in ("klassisch", "kachelwand", "dashboard", "karussell"):
    rundherum(_stil)

check("der leichte Pfad fragt nach dem STIL, nicht nur nach der Ansicht",
      "_haupt_stil()" in nur_code(
          koerper(_QF, "_draw_navigate_cats_impl", "Frontend")),
      "wer eine neue Entscheidungsebene einzieht, muss JEDE Stelle "
      "nachziehen, die die alte abfragt (Build 284)")

shutil.rmtree(TMP, ignore_errors=True)

print()
if fails:
    print("ROT: %d Pruefung(en) fehlgeschlagen:" % len(fails))
    for f in fails:
        print("   - %s" % f)
    sys.exit(1)
print("ALLES GRUEN")
