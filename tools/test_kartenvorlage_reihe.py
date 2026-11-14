#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Eine Vorlage je Reihe, und die Tafel raeumt nur weg, was dasteht (Build 320).

DER ANLASS: "ab und an gibt es immer noch haenger beim scrollen egal
in welche richtung das muss besser laufen".

Sein Bench vom 13.11. zeigt fuer zwei Hauptseiten Zahlen, die nicht
zur Arbeit passen:

    Hauptseite kachelwand   voller Aufbau 243,56 ms  (Raster: 77,84)
    Haupt kachelwand        karten 13,07 ms, 1,2 Zeiger neu je Schritt
    Haupt dashboard         restore 12,49 ms  (3,43 MB je Schritt)

Die Kachelwand hat achtzehn Karten, der Vorlagenspeicher hatte vier
Plaetze und einen Schluessel mit der Position darin - sie hat ihre
Vorlagen also bei jedem Schritt verdraengt und neu gebaut. Und die
Tafel hat 3,43 MB Hintergrund geholt, nur um ein Rechteck fuer den
Flip in eine Liste zu bekommen.

WAS DIESER TEST SICHERT:
  1. der Hintergrund ohne eigenes Bild ist je Zeile einfarbig - DAS
     ist die Voraussetzung, und sie wird am Puffer geprueft, nicht
     am Quelltext,
  2. zwei Karten in derselben Reihe teilen sich EINE Vorlage, und das
     Bild ist bitgleich mit einer eigens fuer die Stelle gebauten,
  3. mit eigenem Hintergrundbild bleibt es bei einer Vorlage je
     Stelle - und die Gegenprobe zeigt, dass Teilen dort falsch waere,
  4. die Grenzen (48 Stueck, 24 MB) und dass beim Leeren auch die
     gemerkten Zeiger gehen,
  5. die Kachelwand baut im Schritt KEINE Vorlage und keinen Zeiger
     mehr neu - mit Gegenprobe,
  6. die Tafel holt im schnellen Weg keinen Hintergrund mehr und
     raeumt vom Bildfeld nur, was der vorige Schritt bemalt hat.

Dass der schnelle Weg dabei bitgenau dasselbe Bild liefert wie ein
voller Aufbau, prueft tools/test_hauptseite_stil.py (Test 7 und 8) -
mit denselben Ansichten und an echten Tastenschritten.

Ausfuehren:
    python3 tools/test_kartenvorlage_reihe.py
"""
import os
import sys

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
sys.path.insert(0, _HIER)

if not os.environ.get("DRAGEND_LIB"):
    for _k in (os.path.join(_REPO, "frontend", "c", "libdragend_x86.so"),
               os.path.join(_REPO, "frontend", "libdragend_x86.so")):
        if os.path.exists(_k):
            os.environ["DRAGEND_LIB"] = _k
            break

import _harness as H                                     # noqa: E402

fm = H.fm
import fe.art as A                                       # noqa: E402
import fe.bench as B                                     # noqa: E402
import fe.framebuffer as FB                              # noqa: E402
import fe.settings as S                                  # noqa: E402
from _quelle import koerper, nur_code                    # noqa: E402

FBK = FB.Framebuffer

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


print(__doc__.strip().split("\n")[0])
print()

C_BG = (18, 19, 24)
C_PANEL = (56, 58, 74)
SCHATTEN = FBK._darken(C_BG, 0.55)
W, HH = 640, 480


def leer(bild=None):
    """Ein Framebuffer mit gefuelltem Hintergrund - mit oder ohne
    eigenes Bild."""
    H.set_screen(W, HH)
    fb = FBK()
    if bild is not None:
        fb.hintergrund_setzen(bild, "testbild")
    fb.clear(C_BG)
    return fb


def foto(fb_stride, hoehe):
    """Ein Hintergrund, der sich in BEIDEN Richtungen aendert."""
    b = bytearray(fb_stride * hoehe)
    for y in range(hoehe):
        zeile = bytearray()
        for x in range(fb_stride // 4):
            zeile += bytes(((x * 3) % 251, (y * 5) % 241,
                            (x + 2 * y) % 239, 0))
        b[y * fb_stride:(y + 1) * fb_stride] = zeile
    return b


def karte(fb, x, y, aus=None):
    fb.karte_mit_schatten(x, y, 120, 90, 4, C_PANEL, SCHATTEN, 6,
                          aussparen=aus, hintergrund_rgb=C_BG)


HAT_C = FBK.zeilen_kopierer is not None
# Als staticmethod aufheben - ueber FBK.zeilen_kopierer geholt und so
# zurueckgeschrieben, wuerde daraus eine gebundene Methode.
_ALT_KOPIERER = FBK.__dict__.get("zeilen_kopierer")
if not HAT_C:
    print("  -- kein Zeilenkopierer (libdragend fehlt): die Vorlage "
          "faellt aus, es gibt nichts zu pruefen")
    print()
    print("ALLES GRUEN")
    sys.exit(0)

# ---------------------------------------------------------------------------
print("Test 1: ohne eigenes Bild ist jede Hintergrundzeile einfarbig")
# ---------------------------------------------------------------------------
fb = leer()
hg = fb._rowcache.get(fb.bg_key(C_BG))
check("die Hintergrundvorlage liegt da", hg is not None
      and len(hg) == fb.stride * fb.height)
_bunt = 0
_farben = set()
for y in range(fb.height):
    z = bytes(hg[y * fb.stride:y * fb.stride + fb.width * 4])
    _farben.add(z[:4])
    if z != z[:4] * fb.width:
        _bunt += 1
check("alle %d Zeilen sind in sich einfarbig" % fb.height, _bunt == 0,
      "%d Zeilen mit mehr als einer Farbe" % _bunt)
check("und die Zeilen untereinander NICHT gleich (die Vignette) - "
      "sonst waere auch y ueberfluessig", len(_farben) > 1,
      "%d Stufen" % len(_farben))
fbf = leer(foto(fb.stride, fb.height))
hgf = fbf._rowcache.get(fbf.bg_key(C_BG))
_z = bytes(hgf[0:fbf.width * 4])
check("Gegenprobe: mit eigenem Bild ist eine Zeile NICHT einfarbig",
      _z != _z[:4] * fbf.width)

# ---------------------------------------------------------------------------
print()
print("Test 2: zwei Karten in einer Reihe, eine Vorlage, bitgleich")
# ---------------------------------------------------------------------------
AUS = (12, 14, 60, 40)                  # Aussparung, relativ zur Karte


def _aus(x, y):
    return (x + AUS[0], y + AUS[1], AUS[2], AUS[3])


for (titel, mit_aus) in (("ohne Aussparung", False),
                         ("mit Aussparung", True)):
    a = leer()
    karte(a, 30, 100, _aus(30, 100) if mit_aus else None)
    n1 = len(a._kartenvorlagen or {})
    karte(a, 330, 100, _aus(330, 100) if mit_aus else None)
    n2 = len(a._kartenvorlagen or {})
    check("%s: die zweite Karte der Reihe baut keine neue Vorlage"
          % titel, n1 == 1 and n2 == 1, "%d, dann %d" % (n1, n2))
    # Die Vergleichsseite baut ihre Vorlage AN DER ZWEITEN STELLE.
    b = leer()
    karte(b, 330, 100, _aus(330, 100) if mit_aus else None)
    karte(b, 30, 100, _aus(30, 100) if mit_aus else None)
    check("%s: beide Reihenfolgen geben bitgleich dasselbe Bild"
          % titel, bytes(a.buf) == bytes(b.buf))
    # Und gegen ganz ohne Vorlage (reines Rechnen). Der weiche
    # Schatten gehoert zur Vorlage und ist eine eigene Bildaenderung
    # (tools/test_kartenvorlage.py, Test 4) - fuer diesen Vergleich
    # also auf beiden Seiten aus.
    _alt_weich = FBK.KARTE_SCHATTEN_WEICH
    FBK.KARTE_SCHATTEN_WEICH = False
    try:
        a2 = leer()
        karte(a2, 30, 100, _aus(30, 100) if mit_aus else None)
        karte(a2, 330, 100, _aus(330, 100) if mit_aus else None)
        FBK.zeilen_kopierer = None
        try:
            c = leer()
            karte(c, 30, 100, _aus(30, 100) if mit_aus else None)
            karte(c, 330, 100, _aus(330, 100) if mit_aus else None)
        finally:
            FBK.zeilen_kopierer = _ALT_KOPIERER
    finally:
        FBK.KARTE_SCHATTEN_WEICH = _alt_weich
    check("%s: und dasselbe wie ganz ohne Vorlage gezeichnet" % titel,
          len(a2._kartenvorlagen or {}) == 1
          and not (c._kartenvorlagen or {})
          and bytes(a2.buf) == bytes(c.buf))

a = leer()
karte(a, 30, 20)
karte(a, 30, 300)
check("eine andere REIHE bekommt ihre eigene Vorlage (Vignette)",
      len(a._kartenvorlagen or {}) == 2, len(a._kartenvorlagen or {}))

# NUR GANZ IM BILD WIRD GETEILT. Rechts vom Bild kann der Puffer
# Fuellbytes haben, und eine Karte, die dort hineinragt, liegt nicht
# mehr auf einer einfarbigen Zeile. Gefragt wird die Funktion selbst,
# an drei Stellen derselben Reihe.
a = leer()
_v1 = a._karte_vorlage(30, 100, 120, 90, 4, C_PANEL, SCHATTEN, 6, C_BG)
_v2 = a._karte_vorlage(330, 100, 120, 90, 4, C_PANEL, SCHATTEN, 6, C_BG)
check("zwei Stellen ganz im Bild: DIESELBE Vorlage",
      _v1 is not None and _v1 is _v2)
_rand = W - 124                          # x + w + versatz == Bildbreite
_v3 = a._karte_vorlage(_rand, 100, 120, 90, 4, C_PANEL, SCHATTEN, 6, C_BG)
check("buendig am rechten Rand: immer noch dieselbe", _v3 is _v1)
_v4 = a._karte_vorlage(_rand + 1, 100, 120, 90, 4, C_PANEL, SCHATTEN, 6,
                       C_BG)
check("einen Bildpunkt darueber hinaus: NICHT mehr geteilt",
      _v4 is not _v1, "eigene Vorlage oder keine - beides ist richtig")
_v5 = a._karte_vorlage(-1, 100, 120, 90, 4, C_PANEL, SCHATTEN, 6, C_BG)
check("links aus dem Bild: ebenfalls nicht geteilt", _v5 is not _v1)

# ---------------------------------------------------------------------------
print()
print("Test 3: mit eigenem Hintergrundbild bleibt x im Schluessel")
# ---------------------------------------------------------------------------
bild = foto(fb.stride, fb.height)
a = leer(bild)
karte(a, 30, 100)
karte(a, 330, 100)
check("zwei Stellen, zwei Vorlagen", len(a._kartenvorlagen or {}) == 2,
      len(a._kartenvorlagen or {}))
_alt_weich = FBK.KARTE_SCHATTEN_WEICH
FBK.KARTE_SCHATTEN_WEICH = False
try:
    a2 = leer(bild)
    karte(a2, 30, 100)
    karte(a2, 330, 100)
    FBK.zeilen_kopierer = None
    try:
        c = leer(bild)
        karte(c, 30, 100)
        karte(c, 330, 100)
    finally:
        FBK.zeilen_kopierer = _ALT_KOPIERER
finally:
    FBK.KARTE_SCHATTEN_WEICH = _alt_weich
check("und das Bild ist bitgleich mit dem ohne Vorlage",
      len(a2._kartenvorlagen or {}) == 2 and bytes(a2.buf) == bytes(c.buf))
# Gegenprobe: so saehe es aus, wenn auch hier geteilt wuerde.
_alt_weich = FBK.KARTE_SCHATTEN_WEICH
FBK.KARTE_SCHATTEN_WEICH = False
g = leer(bild)
karte(g, 30, 100)
_einzige = list(g._kartenvorlagen.items())[0]


class _Alles(dict):
    """Gibt fuer JEDEN Schluessel dieselbe Vorlage zurueck."""

    def get(self, _schluessel, _vorgabe=None):
        return _einzige[1]


g._kartenvorlagen = _Alles()
try:
    karte(g, 330, 100)
finally:
    FBK.KARTE_SCHATTEN_WEICH = _alt_weich
check("Gegenprobe: geteilt waere das Bild FALSCH - der Vergleich kann "
      "rot werden", bytes(g.buf) != bytes(c.buf))

# ---------------------------------------------------------------------------
print()
print("Test 4: die Grenzen, und die Zeiger gehen mit")
# ---------------------------------------------------------------------------
check("48 Vorlagen, 24 MB", FBK.KARTE_VORLAGE_MAX == 48
      and FBK.KARTE_VORLAGE_BYTES == 24 * 1024 * 1024,
      "%d / %d" % (FBK.KARTE_VORLAGE_MAX, FBK.KARTE_VORLAGE_BYTES))
check("frontend.py hat den Zeiger-Leerer eingehaengt",
      FBK.zeiger_leerer is not None)
_geleert = [0]
_alt_leerer = FBK.__dict__["zeiger_leerer"]
FBK.zeiger_leerer = staticmethod(
    lambda: _geleert.__setitem__(0, _geleert[0] + 1))
try:
    a = leer(bild)
    # Achtzehn Stellen wie auf der Kachelwand, mit Hintergrundbild.
    for i in range(18):
        karte(a, 10 + (i % 6) * 100, 20 + (i // 6) * 120)
    check("achtzehn Karten mit Hintergrundbild: achtzehn Vorlagen, "
          "nichts verdraengt", len(a._kartenvorlagen) == 18
          and _geleert[0] == 0, "%d, %d mal geleert"
          % (len(a._kartenvorlagen), _geleert[0]))
    for i in range(18):
        karte(a, 10 + (i % 6) * 100, 20 + (i // 6) * 120)
    check("ein zweiter Durchgang baut keine einzige neu",
          len(a._kartenvorlagen) == 18 and _geleert[0] == 0)
    # Ueber die Grenze: es wird GANZ geleert, und die Zeiger gehen mit.
    alt_max = FBK.KARTE_VORLAGE_MAX
    FBK.KARTE_VORLAGE_MAX = 18
    try:
        karte(a, 500, 380)
    finally:
        FBK.KARTE_VORLAGE_MAX = alt_max
    check("ueber der Grenze wird geleert - danach liegt genau die neue da",
          len(a._kartenvorlagen) == 1, len(a._kartenvorlagen))
    check("und der Zeiger-Leerer wurde genau einmal gerufen",
          _geleert[0] == 1, _geleert[0])
    # Die Byte-Grenze.
    alt_b = FBK.KARTE_VORLAGE_BYTES
    FBK.KARTE_VORLAGE_BYTES = a._kartenvorlagen_bytes + 100
    try:
        karte(a, 30, 100)
    finally:
        FBK.KARTE_VORLAGE_BYTES = alt_b
    check("auch die Byte-Grenze leert, samt Zeigern",
          len(a._kartenvorlagen) == 1 and _geleert[0] == 2,
          (len(a._kartenvorlagen), _geleert[0]))
    # Ein Leerer, der wirft, darf das Zeichnen nicht stoeren.
    FBK.zeiger_leerer = staticmethod(lambda: 1 // 0)
    FBK.KARTE_VORLAGE_MAX = 1
    try:
        karte(a, 200, 200)
        _ok = True
    except Exception as e:                               # noqa: BLE001
        _ok = "%s: %s" % (type(e).__name__, e)
    finally:
        FBK.KARTE_VORLAGE_MAX = alt_max
    check("wirft der Leerer, wird trotzdem gezeichnet", _ok is True, _ok)
finally:
    FBK.zeiger_leerer = _alt_leerer

# Der echte Leerer.
_puf = bytearray(64)
A._roh_zeiger(_puf)
_vor = tuple(A.ZEIGER_STAND)
check("vor dem Leeren ist ein Zeiger gemerkt", len(A._ZEIGER) >= 1)
A.zeiger_leeren()
check("zeiger_leeren() wirft alle weg und zaehlt es",
      len(A._ZEIGER) == 0 and A.ZEIGER_STAND[1] == _vor[1] + 1)
check("der eingehaengte Leerer IST zeiger_leeren()",
      FBK.zeiger_leerer is A.zeiger_leeren)
check("der Zeigerspeicher fasst jetzt 64", A._ZEIGER_MAX == 64)

# ---------------------------------------------------------------------------
print()
print("Test 5: die Kachelwand baut im Schritt nichts mehr neu")
# ---------------------------------------------------------------------------


KEYS = ["FAVORITES", "CONTINUE", "RECENT", "COLLECTIONS", "NES", "SNES",
        "GAMEBOY", "GBC", "GBA", "N64", "Genesis", "SMS", "MegaCD", "PSX",
        "Saturn", "TGFX16", "NEOGEO", "ATARI2600", "ARCADE",
        "SUPERGAMEBOY", "S32X", "VIRTUALBOY", "COMPUTER", "GAMEGEAR",
        "ATARILYNX", "COLECOVISION", "SYSTEM", "SCRIPTS"]


def _viele_kategorien(f):
    """28 Kategorien wie auf seinem Geraet - der Pruefstand hat zwei,
    und zwei Kacheln beweisen ueber achtzehn nichts."""
    f.cats = [(k, {"items": [], "folders": {}}, k) for k in KEYS]
    f.cat_i = 0
    f.cat_scroll = 0


def wand_lauf(schritte=40):
    """(neue Vorlagen, Leerungen, neue Zeiger, Vorlagen gesamt,
        Kacheln) ueber <schritte> Schritte auf der Kachelwand."""
    H._zwischenspeicher_leeren()
    H.set_screen(1920, 1080)
    f = H.make_frontend(page=0)
    A.ART.auslagern = None
    f._last_input_time = 0
    _viele_kategorien(f)
    if B.ansicht_einstellen(f, 0, "kachelwand") != "kachelwand":
        return None
    schritt = B.schritt_funktion(f, 0)
    f.draw()
    for i in range(len(f.cats)):
        schritt(i)
    schritt(0)
    vl = f.fb._kartenvorlagen or {}
    vor_ids = set(id(e) for e in vl.values())
    vor_z = tuple(A.ZEIGER_STAND)
    for i in range(schritte):
        schritt(i % len(f.cats))
    f.fb.mark_full_redraw()
    f.draw()                              # und ein voller Aufbau dazu
    vl = f.fb._kartenvorlagen or {}
    neu = len(set(id(e) for e in vl.values()) - vor_ids)
    nach_z = tuple(A.ZEIGER_STAND)
    return (neu, nach_z[1] - vor_z[1], nach_z[0] - vor_z[0], len(vl),
            _karten[0], len(f.cats))


# Wie viele Karten zeichnet EIN voller Aufbau der Kachelwand? Gezaehlt
# am Framebuffer, nicht aus der Geometrie gerechnet.
_karten = [0]
_echt_kms = FBK.karte_mit_schatten


def _kms(self, *a, **k):
    _karten[0] += 1
    return _echt_kms(self, *a, **k)


def karten_je_aufbau():
    H._zwischenspeicher_leeren()
    H.set_screen(1920, 1080)
    f = H.make_frontend(page=0)
    A.ART.auslagern = None
    f._last_input_time = 0
    _viele_kategorien(f)
    if B.ansicht_einstellen(f, 0, "kachelwand") != "kachelwand":
        return 0
    f.draw()
    f.fb.mark_full_redraw()
    _karten[0] = 0
    FBK.karte_mit_schatten = _kms
    try:
        f.draw()
    finally:
        FBK.karte_mit_schatten = _echt_kms
    return _karten[0]


KARTEN = karten_je_aufbau()


erg = wand_lauf()
if erg is None:
    check("die Kachelwand ist auf 1920x1080 einstellbar", False)
else:
    neu, geleert, zeiger, gesamt, _k, n_kat = erg
    check("ein voller Aufbau der Kachelwand zeichnet mehr als zwoelf "
          "Karten (sonst prueft dieser Test die falsche Seite)",
          KARTEN > 12, "%d Karten" % KARTEN)
    check("40 Schritte und ein voller Aufbau: keine neue Vorlage",
          neu == 0, "%d neu" % neu)
    check("der Zeigerspeicher wurde nie geleert", geleert == 0, geleert)
    check("und kein Zeiger neu gebaut", zeiger == 0, zeiger)
    check("es liegen viel weniger Vorlagen da als Karten gezeichnet "
          "werden (eine je Reihe, nicht eine je Kachel)",
          0 < gesamt <= KARTEN // 3, "%d Vorlagen fuer %d Karten"
          % (gesamt, KARTEN))
    # Gegenprobe: mit zu wenig Platz wird verdraengt.
    alt_max = FBK.KARTE_VORLAGE_MAX
    FBK.KARTE_VORLAGE_MAX = max(1, gesamt - 1)
    try:
        erg2 = wand_lauf()
    finally:
        FBK.KARTE_VORLAGE_MAX = alt_max
    check("Gegenprobe: mit zu wenig Platz wird neu gebaut und geleert - "
          "die Pruefung kann rot werden",
          erg2 is not None and erg2[0] > 0 and erg2[1] > 0,
          "%s" % (erg2,))

# ---------------------------------------------------------------------------
print()
print("Test 6: die Tafel raeumt nur weg, was dasteht")
# ---------------------------------------------------------------------------
H._zwischenspeicher_leeren()
H.set_screen(1920, 1080)
f = H.make_frontend(page=0)
A.ART.auslagern = None
f._last_input_time = 0
_viele_kategorien(f)
if B.ansicht_einstellen(f, 0, "dashboard") != "dashboard":
    check("das Dashboard ist auf 1920x1080 einstellbar", False)
else:
    f.draw()
    f.draw()
    geo = f.dashboard_geometrie(f.kat_layout())
    bildfeld, textfeld = geo["felder"]
    C_P = fm.C_PANEL

    # Ein Bild unterschieben, das KLEINER ist als das Feld - auf dem
    # Geraet sind die Fotos hoechstens 420x320, das Feld 1079x517.
    BW, BH = 300, 200
    _pix = bytes(bytearray([90, 60, 30, 255])) * (BW * BH)
    f._kat_logo = lambda i, bb, bh, foto=False: ((BW, BH, _pix), False)

    drin = [False]
    restore = []
    flaechen = []
    _echt_tafel = f._dash_tafel_zeichnen
    _echt_restore = f._restore_row_bg
    _echt_rect = f.fb.rect
    schnell_gesehen = []

    spuren = []

    def _tafel(geo_, schnell):
        drin[0] = True
        schnell_gesehen.append(bool(schnell))
        try:
            return _echt_tafel(geo_, schnell)
        finally:
            drin[0] = False
            # Die Spuren gehoeren dem Aufbau, der gerade laeuft - nach
            # dem Flip sind sie weg. Also hier abgreifen.
            del spuren[:]
            spuren.extend(f._flip_spuren or ())

    def _restore(x, y, w, h):
        if drin[0]:
            restore.append((x, y, w, h))
        return _echt_restore(x, y, w, h)

    def _rect(x, y, w, h, rgb, *a, **k):
        if drin[0] and rgb == C_P:
            flaechen.append((x, y, w, h))
        return _echt_rect(x, y, w, h, rgb, *a, **k)

    f._dash_tafel_zeichnen = _tafel
    f._restore_row_bg = _restore
    f.fb.rect = _rect
    try:
        f.fb.mark_full_redraw()
        f.draw()                            # voller Aufbau, mit Bild
        n = len(f.cats)
        f.cat_i = (f.cat_i + 1) % n
        f.draw_page_cats(flip=False)        # der erste schnelle
        del restore[:]
        del flaechen[:]
        del schnell_gesehen[:]
        f.cat_i = (f.cat_i + 1) % n
        f.draw_page_cats(flip=False)
    finally:
        del f._dash_tafel_zeichnen
        del f._restore_row_bg
        del f.fb.rect
        del f._kat_logo

    check("der Schritt lief ueber den schnellen Weg",
          schnell_gesehen == [True], schnell_gesehen)
    check("im schnellen Weg wird KEIN Hintergrund mehr geholt",
          restore == [], restore)
    bx = geo["bild_x"] + max(0, (geo["bild_b"] - BW) // 2)
    by = geo["bild_y"] + max(0, (geo["bild_h"] - BH) // 2)
    check("weggeraeumt wird vom Bildfeld genau das Rechteck des alten "
          "Bildes", (bx, by, BW, BH) in flaechen
          and tuple(bildfeld) not in flaechen, flaechen[:3])
    check("und das Textfeld wie bisher ganz",
          tuple(textfeld) in flaechen)
    _alt_bytes = (bildfeld[2] * bildfeld[3] + textfeld[2] * textfeld[3]) * 4
    _neu_bytes = (BW * BH + textfeld[2] * textfeld[3]) * 4
    check("das sind deutlich weniger Bytes als das ganze Feld",
          _neu_bytes < _alt_bytes * 0.7,
          "%.2f statt %.2f MB" % (_neu_bytes / 1048576.0,
                                  _alt_bytes / 1048576.0))
    check("gemerkt ist das Rechteck des NEUEN Bildes",
          tuple(f._dash_bild_alt) == (bx, by, BW, BH), f._dash_bild_alt)

    def _deckt(r):
        return any(sx <= r[0] and sy <= r[1]
                   and sx + sw >= r[0] + r[2] and sy + sh >= r[1] + r[3]
                   for sx, sy, sw, sh in spuren)

    check("der Flip erfaehrt von Bild und Textfeld (von Hand "
          "eingetragen, weil kein restore es mehr tut)",
          _deckt((bx, by, BW, BH)) and _deckt(tuple(textfeld)),
          spuren[:4])
    _T = nur_code(koerper(open(os.path.join(_REPO, "frontend",
                                            "frontend.py"),
                               encoding="utf-8").read(),
                          "_dash_tafel_zeichnen", "Frontend"))
    check("im Quelltext der Tafel steht kein _restore_row_bg mehr",
          "_restore_row_bg" not in _T)

print()
if fails:
    print("ROT: %d Pruefung(en) fehlgeschlagen:" % len(fails))
    for f_ in fails:
        print("   - " + f_)
    sys.exit(1)
print("ALLES GRUEN")
