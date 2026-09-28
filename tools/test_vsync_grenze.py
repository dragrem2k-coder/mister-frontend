#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Die Vsync-Grenze und die Kachelbaender (Build 214).

NUTZER-RUECKMELDUNG, die das ausgeloest hat: "fast scroll enabled
bringt gefuehlt garnichts beim links und rechts scrollen im raster und
galerie."

DAS WAR KEIN GEFUEHL, SONDERN ARITHMETIK, und der Fehler war eine
einzelne Zahl. VSYNC_SKIP_MAX_ANTEIL stand seit Build 93 auf 0.25 -
also "ein Band bis zu einem Viertel der Bildhoehe darf das Warten auf
den Bildwechsel auslassen". Diese Zahl war fuer die DAMALIGEN Kacheln
gesetzt: 253 von 1080 Zeilen, 23,4 %, knapp darunter. Seit Build 211
sind die GROSSEN Kacheln der Standard, und damit misst dasselbe Band
379 Zeilen, also 35,1 % - darueber. Der Schalter war in der
Kachelansicht damit wirkungslos, ohne dass irgendwo etwas kaputt war.

WAS DIESER TEST FESTHAELT, und das ist der eigentliche Zweck: die
Zahlen in der Begruendung bei VSYNC_SKIP_MAX_ANTEIL sind MESSWERTE,
und Messwerte in Kommentaren veralten still. Hier stehen sie als
Pruefung. Wer die Kachelgroesse, die Abstaende oder die Fusszeile
aendert, erfaehrt in dieser Ausgabe, dass er die Grenze mitgeaendert
hat - und nicht erst der Nutzer, ein Build spaeter.

Geprueft wird in dieser Reihenfolge:

  1. die Bandhoehen aller acht Aufloesungen, gross und klein, gerechnet
     mit DERSELBEN Zusammenfassung wie _baender_flippen();
  2. dass jedes Kachelband der Standard-Ansicht unter der Grenze liegt;
  3. dass die Grenze nicht so hoch steht, dass halbe Bilder durchgehen;
  4. dass der volle Aufbau und fb.flip() weiterhin IMMER warten;
  5. dass ohne den Schalter nichts ausgelassen wird;
  6. und zum Schluss am echten Zeichenweg: kommt beim Schritt nach
     rechts wirklich skip_vsync=True beim Bildspeicher an?

Punkt 6 ist der einzige, der etwas beweist - 1 bis 5 rechnen, 6 sieht
nach. Beides, weil ein Rechenfehler in 1-5 sonst genau so aussieht wie
ein richtiges Ergebnis.

Ausfuehren:
    python3 tools/test_vsync_grenze.py
"""
import os
import struct
import sys
import tempfile
import zlib

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
sys.path.insert(0, _HIER)

import _harness as H                                     # noqa: E402

fm = H.fm
sys.path.insert(0, os.path.join(_REPO, "frontend"))
import fe.art as A                                       # noqa: E402
from fe import settings as S                             # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


QUER = ((1920, 1080), (1280, 720), (640, 480), (320, 240))
HOCH = ((1080, 1920), (720, 1280), (480, 640), (240, 320))

# GEMESSEN mit diesem Test selbst, Build 214. Fest verdrahtet, damit
# eine Aenderung an der Kachelrechnung hier auffaellt und nicht erst
# beim Nutzer. Anteil in Prozent der Bildhoehe, auf eine Stelle.
GROSS_SOLL = {(1920, 1080): 35.1, (1280, 720): 35.1,
              (640, 480): 37.5, (320, 240): 32.1,
              (1080, 1920): 19.7, (720, 1280): 19.7,
              (480, 640): 26.2, (240, 320): 23.4}
KLEIN_SOLL = {(1920, 1080): 23.4, (1280, 720): 23.3,
              (640, 480): 21.5, (320, 240): 20.4,
              (1080, 1920): 15.8, (720, 1280): 13.1,
              (480, 640): 17.2, (240, 320): 16.9}

TITEL = ["Spiel %02d" % i for i in range(60)]
TMP = tempfile.mkdtemp(prefix="vsyncgrenze_")
BASIS = os.path.join(TMP, "art")
os.makedirs(os.path.join(BASIS, "SNES"))


def cover(pfad, w, h, nr):
    punkt = bytes(((nr * 37) % 256, (nr * 91) % 256, (nr * 53) % 256, 255))
    with open(pfad, "wb") as f:
        f.write(b"ART1" + struct.pack("<HH", w, h)
                + zlib.compress(punkt * (w * h), 1))


for i, t in enumerate(TITEL):
    cover(os.path.join(BASIS, "SNES", t + ".art"), 400, 533, i)

fm.ART_BASE = A.ART_BASE = BASIS
fm.ART_HD = A.ART_HD = BASIS
A._art_index_cache.clear()
A.THUMB_CACHE_DIR = os.path.join(TMP, "tc")
os.makedirs(A.THUMB_CACHE_DIR)
fm.SYSART_BASE = A.SYSART_BASE = os.path.join(_REPO, "frontend", "sysart")


def spieleliste(breite, hoehe):
    H.set_screen(breite, hoehe)
    f = H.make_frontend(page=1)
    fm.ART.auslagern = None
    f.lader.beenden()
    _n, node, _k = f.cats[f.cat_i]
    node["items"] = [(t, "game", ("/f/%d.sfc" % i, ".sfc", "SNES", None, None))
                     for i, t in enumerate(TITEL)]
    node.pop("_display_items_cache", None)
    return f


def baender(f, hoehe):
    """DIESELBE Zusammenfassung wie _baender_flippen() - sortieren und
    ueberlappende Spannen verschmelzen -, angewandt auf zwei Kacheln
    derselben Reihe plus den unteren Streifen. Absichtlich hier
    nachgebaut und nicht die Methode gerufen: die schreibt in den
    Bildspeicher, und hier soll nur gerechnet werden."""
    L = f.layout_items(True)
    geo = f.raster_geometrie(L)
    felder = [f._kachel_feld(geo, 0), f._kachel_feld(geo, 1)]
    spannen = [(max(0, y), min(hoehe, y + h)) for (_x, y, _b, h) in felder]
    unten_ab = max(0, min(geo["name_y"] - geo["s"], L["footer_y"] - geo["s"]))
    if unten_ab < hoehe:
        spannen.append((unten_ab, hoehe))
    spannen.sort()
    zus = []
    for a, b in spannen:
        if b <= a:
            continue
        if zus and a <= zus[-1][1]:
            zus[-1][1] = max(zus[-1][1], b)
        else:
            zus.append([a, b])
    return geo, [b - a for a, b in zus]


# ---------------------------------------------------------------------------
print("Test 1: die Bandhoehen, gross und klein, alle acht Aufloesungen")
# ---------------------------------------------------------------------------
_echt = S.raster_gross
gemessen = {True: {}, False: {}}
try:
    for gross, soll, tag in ((True, GROSS_SOLL, "gross"),
                             (False, KLEIN_SOLL, "klein")):
        S.raster_gross = (lambda v=gross: v)
        print("  -- %s" % tag)
        for (b, h) in QUER + HOCH:
            f = spieleliste(b, h)
            f.ansicht_setzen("raster")
            geo, hoehen = baender(f, h)
            # Das ERSTE Band ist das der Kacheln, das zweite der untere
            # Streifen - nach der Sortierung in dieser Reihenfolge.
            kachelband = hoehen[0]
            anteil = 100.0 * kachelband / h
            gemessen[gross][(b, h)] = (kachelband, anteil)
            check("%4dx%-5d %dx%d  Band %4d von %4d = %4.1f %%"
                  % (b, h, geo["spalten"], geo["zeilen"], kachelband, h,
                     anteil),
                  abs(anteil - soll[(b, h)]) < 0.1,
                  "erwartet %.1f %%" % soll[(b, h)])
finally:
    S.raster_gross = _echt

# ---------------------------------------------------------------------------
print()
print("Test 2: jedes Kachelband der STANDARD-Ansicht liegt unter der Grenze")
# ---------------------------------------------------------------------------
# Das ist der Punkt des ganzen Builds. Mit der alten Grenze von 0.25
# fallen hier FUENF der acht Faelle durch (nachgerechnet, indem die
# Konstante zurueckgedreht wurde): alle vier QUER-Aufloesungen und
# 480x640. Die drei anderen Hochkant-Faelle waren auch vorher schon
# drunter - hochkant ist die Bildhoehe gross und das Band im Verhaeltnis
# klein. Der Schalter war also nicht ueberall wirkungslos, sondern genau
# da, wo die Leute sitzen.
grenze = fm.VSYNC_SKIP_MAX_ANTEIL
print("  VSYNC_SKIP_MAX_ANTEIL = %.2f" % grenze)
schlimmster = max(a for (_z, a) in gemessen[True].values())
for (b, h), (zeilen, anteil) in sorted(gemessen[True].items()):
    check("%4dx%-5d %4.1f %% <= %.0f %%" % (b, h, anteil, grenze * 100),
          anteil <= grenze * 100.0 + 1e-9,
          "Band %d von %d" % (zeilen, h))
check("der schlimmste Fall (%.1f %%) passt noch" % schlimmster,
      schlimmster <= grenze * 100.0)
# Und die kleinen Kacheln duerfen dadurch nicht schlechter werden - sie
# waren schon vorher drunter.
for (b, h), (_z, anteil) in sorted(gemessen[False].items()):
    check("klein %4dx%-5d %4.1f %% weiterhin drunter" % (b, h, anteil),
          anteil <= grenze * 100.0)

# ---------------------------------------------------------------------------
print()
print("Test 3: die Grenze steht nicht zu hoch")
# ---------------------------------------------------------------------------
# Eine Grenze, die alles durchlaesst, waere keine. Die Abwaegung aus
# Build 93 gilt weiter: je mehr Bild eine Kopie anfasst, desto
# sichtbarer der Riss. Ein halbes Bild ist zu viel.
check("die Grenze bleibt unter der Haelfte des Bildes", grenze < 0.5,
      "ist %.2f" % grenze)
check("und laesst dem schlimmsten Fall Luft (mind. 2 Punkte)",
      grenze * 100.0 - schlimmster >= 2.0,
      "Luft %.1f Punkte" % (grenze * 100.0 - schlimmster))

# ---------------------------------------------------------------------------
print()
print("Test 4: Vollbild wartet IMMER, egal wie der Schalter steht")
# ---------------------------------------------------------------------------
f = spieleliste(1920, 1080)
f.ansicht_setzen("raster")
# WICHTIG: der Pruefstand friert time.monotonic() auf H.NOW ein (siehe
# _harness.py). "gerade eben getippt" heisst hier also H.NOW[0] und
# nicht time.monotonic() - mit der echten Uhr laege der Zeitpunkt in
# ferner Zukunft und _scroll_skip_vsync() saehe eine NEGATIVE Spanne.
_echt_fs = S.fast_scroll_enabled
try:
    S.fast_scroll_enabled = (lambda: True)
    fm.fast_scroll_enabled = (lambda: True)
    f._last_input_time = H.NOW[0]
    check("_vsync_ueberspringen(None) bleibt False",
          f._vsync_ueberspringen(None) is False)
    # Das Band der Boxart-Spalte auf der Hauptseite: rund 1000 von 1080
    # Zeilen, 92 %. Dafuer ist die Grenze da.
    check("ein 1000-Zeilen-Band wartet weiterhin",
          f._vsync_ueberspringen(1000) is False)
    check("ein Kachelband (379) darf auslassen",
          f._vsync_ueberspringen(379) is True)
    check("genau auf der Grenze (432) darf noch auslassen",
          f._vsync_ueberspringen(int(1080 * grenze)) is True)
    check("eine Zeile darueber (433) nicht mehr",
          f._vsync_ueberspringen(int(1080 * grenze) + 1) is False)

    # ------------------------------------------------------------------
    print()
    print("Test 5: ohne den Schalter wird NICHTS ausgelassen")
    # ------------------------------------------------------------------
    S.fast_scroll_enabled = (lambda: False)
    fm.fast_scroll_enabled = (lambda: False)
    for hoehe in (1, 10, 100, 379, 1000, None):
        check("Schalter aus: %s wartet" % ("Vollbild" if hoehe is None
                                           else "%d Zeilen" % hoehe),
              f._vsync_ueberspringen(hoehe) is False)

    # ------------------------------------------------------------------
    print()
    print("Test 6: am echten Zeichenweg - was kommt bei flip_rows an?")
    # ------------------------------------------------------------------
    # Die Rechnung oben kann stimmen und der Zeichenweg sie trotzdem
    # nicht benutzen (genau das war der Fehler aus Build 133, behoben in
    # 134: die Aufrufer rechneten mit None, also "Vollbild"). Deshalb
    # hier nachgesehen, nicht gerechnet.
    S.fast_scroll_enabled = (lambda: True)
    fm.fast_scroll_enabled = (lambda: True)
    f2 = spieleliste(1920, 1080)
    f2.ansicht_setzen("raster")
    for i in range(12):
        f2.item_i = i
        f2._last_input_time = H.NOW[0]
        f2.draw()
    gesehen = []
    echt_fr = f2.fb.flip_rows

    def _haken(y, h, skip_vsync=False):
        gesehen.append((h, bool(skip_vsync)))
        return echt_fr(y, h, skip_vsync)

    f2.fb.flip_rows = _haken
    f2.item_i = 0
    f2._force_full_redraw = True
    f2._last_input_time = H.NOW[0]
    f2.draw()
    gesehen[:] = []
    f2.item_i = 1                      # ein Schritt nach rechts
    f2._last_input_time = H.NOW[0]
    f2.draw()
    check("es wurden ueberhaupt Baender kopiert", bool(gesehen),
          repr(gesehen))
    check("ALLE Baender dieses Schritts lassen das Warten aus",
          bool(gesehen) and all(sk for (_h, sk) in gesehen),
          ", ".join("%d:%s" % (h, sk) for (h, sk) in gesehen))
    check("und das groesste davon ist das Kachelband",
          bool(gesehen) and max(h for (h, _s) in gesehen) >= 300,
          ", ".join(str(h) for (h, _s) in gesehen))

    # Dieselbe Bewegung mit ausgeschaltetem Schalter: dieselben Baender,
    # aber jedes mit Warten. Ohne diese Gegenprobe koennte im Zeichenweg
    # ein festes True stehen und Test 6 waere trotzdem gruen.
    S.fast_scroll_enabled = (lambda: False)
    fm.fast_scroll_enabled = (lambda: False)
    f2.item_i = 0
    f2._force_full_redraw = True
    f2.draw()
    gesehen[:] = []
    f2.item_i = 1
    f2._last_input_time = H.NOW[0]
    f2.draw()
    check("Gegenprobe: mit ausgeschaltetem Schalter wartet jedes Band",
          bool(gesehen) and not any(sk for (_h, sk) in gesehen),
          ", ".join("%d:%s" % (h, sk) for (h, sk) in gesehen))
finally:
    S.fast_scroll_enabled = _echt_fs
    fm.fast_scroll_enabled = _echt_fs

# ---------------------------------------------------------------------------
print()
print("Test 7: die GALERIE kopiert weiterhin das Vollbild")
# ---------------------------------------------------------------------------
# Kein Wunsch, sondern eine Feststellung mit Absicht: der Nutzer hat
# Raster UND Galerie in einem Satz genannt, und diese Grenze hilft nur
# dem Raster. Solange das so ist, soll es hier stehen - damit niemand
# (auch ich nicht) spaeter glaubt, Build 214 haette die Galerie
# mitbehoben.
import inspect                                           # noqa: E402

quelle = inspect.getsource(fm.Frontend._draw_items_galerie)
check("_draw_items_galerie ruft fb.flip(), nicht flip_rows()",
      "fb.flip(" in quelle and "flip_rows" not in quelle,
      "flip_rows kommt vor" if "flip_rows" in quelle else "")
check("und zwar mit _vsync_ueberspringen(None), also immer wartend",
      "_vsync_ueberspringen(None)" in quelle)

# ---------------------------------------------------------------------------
print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  - " + x)
    sys.exit(1)
print("Alles in Ordnung.")
