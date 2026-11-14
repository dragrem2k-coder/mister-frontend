#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Das grosse Cover wird vorausgelesen, nicht im Zeichenweg (Build 320).

DER ANLASS, in seinen Worten: "ab und an gibt es immer noch haenger
beim scrollen egal in welche richtung" und "was mich auch noch ein
wenig stoert ist das scrollen in der listen ansicht mit eingeschalteten
cover wechsel das das nicht schneller laeuft".

Sein Bench vom 13.11. sagt dazu drei Dinge:

    Spieleliste liste   je Schritt Karte 159,28 ms   warm 72,42 ms
    L.3  Boden Liste liste                227 ms
    L.4  69 Auftraege, 0 Pausen

Die ersten beiden sind EIN Befund: das Cover der Listenansicht
(733x909, 2,7 MB roh) wurde in jedem Schritt im Zeichenweg von der
Karte gelesen - 87 ms, in denen nichts auf Tasten reagiert. Der dritte
ist ein eigener: die zwei leichten Zeichenwege haben den Cover-Schutz
nie aufgefrischt, also hat der Schreibfaden nie erfahren, dass gerade
navigiert wird.

WAS DIESER TEST SICHERT:
  1. die leichten Zeichenwege bringen den Cover-Schutz auf den
     aktuellen Stand - in beide Richtungen, auf beiden Seiten, und
     mit Gegenprobe,
  2. eine GROSSE Miniatur wird waehrend der Navigation nicht gelesen:
     keine Datei wird geoeffnet - und jede der vier Bedingungen
     einzeln zurueckgenommen liest wieder sofort,
  3. die Marke "das Original passt" (acht Byte) wird NICHT
     aufgeschoben - das waere das Aufblitzen aus Build 92,
  4. der Vorausleser: nur mit "Cover sofort", in Scrollrichtung, mit
     wachsendem Vorgriff bei schnellen Schritten, ohne was schon im
     Speicher liegt und ohne was nicht auf der Karte ist,
  5. der Zeichenweg der Spieleliste ruft ihn - die Hauptseite nicht,
  6. was der Faden geholt hat, liegt VOR dem Zeichnen im Speicher,
  7. der Faden nennt, wie lange das letzte Lesen gedauert hat,
  8. das Auspacken kopiert die Datei nicht mehr, das Ergebnis ist
     bitgleich.

Ausfuehren:
    python3 tools/test_vorauslesen.py
"""
import os
import shutil
import struct
import sys
import tempfile
import time
import zlib

_ECHTE_UHR = time.monotonic

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
import fe.nachladen as N                                 # noqa: E402
from _quelle import koerper                              # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


print(__doc__.strip().split("\n")[0])
print()

TMP = tempfile.mkdtemp(prefix="vorauslesen_")
_ALT_BASE, _ALT_DIR = A.THUMB_CACHE_BASE, A.THUMB_CACHE_DIR
A.THUMB_CACHE_BASE = os.path.join(TMP, "base")
A.THUMB_CACHE_DIR = os.path.join(TMP, "cache")

_Q = open(os.path.join(_REPO, "frontend", "frontend.py"),
          encoding="utf-8").read()


def _mit_spielen(f, n=300):
    _nm, node, _sk = f.cats[0]
    node["items"] = [("Spiel Nummer %03d" % i, "game",
                      ("/f/%d.sfc" % i, ".sfc", "SNES", None, None))
                     for i in range(n)]
    node.pop("_display_items_cache", None)


def _liste(n=300):
    H.set_screen(1920, 1080)
    f = H.make_frontend(page=0)
    A.ART.auslagern = None
    _mit_spielen(f, n)
    f.page = 1
    f.cat_i = 0
    f.nav_path = []
    f.ansicht_setzen("liste")
    f.item_i = 5
    f.draw()
    # Der erste leichte Schritt nach einem Ansichtswechsel wird mit
    # Absicht abgelehnt (_force_full_redraw) - den hier verbrauchen.
    if not f._draw_navigate_items(5):
        f.draw()
    return f


# ---------------------------------------------------------------------------
print("Test 1: die leichten Zeichenwege frischen den Cover-Schutz auf")
# ---------------------------------------------------------------------------
f = _liste()
H.NOW[0] = 500.0

# Spieleliste, es wird navigiert, der Wert ist veraltet (False).
f._last_input_time = H.NOW[0]
A.ART._defer_uncached = False
alt = f.item_i
f.item_i = alt + 1
leicht = f._draw_navigate_items(alt)
check("der leichte Pfad der Spieleliste hat gezeichnet", bool(leicht))
check("Spieleliste: waehrend der Navigation steht der Schutz danach",
      A.ART._defer_uncached is True)
check("und _navigation_aktiv() sagt es dem Schreibfaden",
      A._navigation_aktiv() is True)

# Umgekehrt: Stillstand, der Wert ist veraltet (True).
f._last_input_time = 0
A.ART._defer_uncached = True
alt = f.item_i
f.item_i = alt + 1
f._draw_navigate_items(alt)
check("Spieleliste: im Stillstand ist er danach aus",
      A.ART._defer_uncached is False)

# Gegenprobe: ohne die Auffrischung bleibt der veraltete Wert stehen.
f._last_input_time = H.NOW[0]
A.ART._defer_uncached = False
f._sync_cover_defer = lambda: None
alt = f.item_i
f.item_i = alt + 1
f._draw_navigate_items(alt)
check("Gegenprobe: ohne _sync_cover_defer() bleibt er veraltet",
      A.ART._defer_uncached is False)
del f._sync_cover_defer

# Hauptseite.
H.set_screen(1920, 1080)
f = H.make_frontend(page=0)
A.ART.auslagern = None
f.ansicht_haupt_setzen("liste")
f.draw()
if not f._draw_navigate_cats(f.cat_i):
    f.draw()
H.NOW[0] = 600.0
f._last_input_time = H.NOW[0]
A.ART._defer_uncached = False
alt = f.cat_i
f.cat_i = (alt + 1) % len(f.cats)
leicht = f._draw_navigate_cats(alt)
check("der leichte Pfad der Hauptseite hat gezeichnet", bool(leicht))
check("Hauptseite: waehrend der Navigation steht der Schutz danach",
      A.ART._defer_uncached is True)
f._last_input_time = 0
alt = f.cat_i
f.cat_i = (alt + 1) % len(f.cats)
f._draw_navigate_cats(alt)
check("Hauptseite: im Stillstand ist er danach aus",
      A.ART._defer_uncached is False)
for _name in ("_draw_navigate_cats_impl", "_draw_navigate_items_impl"):
    check("%s ruft _sync_cover_defer()" % _name,
          "self._sync_cover_defer()" in koerper(_Q, _name, "Frontend"))

# ---------------------------------------------------------------------------
print()
print("Test 2: eine grosse Miniatur wird beim Navigieren nicht gelesen")
# ---------------------------------------------------------------------------
GROSS = (733, 909)            # das Cover der Listenansicht, 2,7 MB
KLEIN = (426, 569)            # das grosse Bild der Galerie, 0,97 MB


def _miniatur(pfad, w, h):
    """Eine echte Miniatur auf die (temporaere) Karte legen."""
    pix = bytes(bytearray([10, 20, 30, 255])) * (w * h)
    A._thumb_cache_put(pfad, w, h, w, h, pix)
    return pix


PIX_GROSS = _miniatur("/c/gross.png", *GROSS)
PIX_KLEIN = _miniatur("/c/klein.png", *KLEIN)
check("die Miniaturen liegen auf der Karte, groesser als die Marke",
      A.thumb_cache_groesse("/c/gross.png", *GROSS)
      > A.GROSSE_MINIATUR_DATEI_MIN
      and A.thumb_cache_groesse("/c/klein.png", *KLEIN)
      > A.GROSSE_MINIATUR_DATEI_MIN)
check("thumb_cache_groesse() ohne Datei ist -1",
      A.thumb_cache_groesse("/c/gibt_es_nicht.png", *GROSS) == -1)
check("die Schwelle ist ein Megabyte: Liste darueber, Galerie darunter",
      GROSS[0] * GROSS[1] * 4 >= A.GROSSE_MINIATUR_BYTES
      > KLEIN[0] * KLEIN[1] * 4)

_gelesen = []
_echt_get = A._thumb_cache_get


def _get(path, *a, **k):
    _gelesen.append(path)
    return _echt_get(path, *a, **k)


A._thumb_cache_get = _get


def _frage(pfad, kasten, defer=True, ok=True):
    """Ein frischer Cache, eine Anfrage. Rueckgabe: (Ergebnis, wie oft
    die Datei gelesen wurde, wie oft 'gross aufgeschoben')."""
    c = A.ArtCache()
    c.auslagern = None
    c._defer_uncached = defer
    del _gelesen[:]
    r = c.get_scaled(pfad, kasten[0], kasten[1], auslagern_ok=ok)
    return r, len(_gelesen), getattr(c, "gross_aufgeschoben", 0), c


try:
    r, n, g, c = _frage("/c/gross.png", GROSS)
    check("navigiert + gross + auf der Karte: es kommt None", r is None)
    check("und die Datei wurde NICHT geoeffnet", n == 0, "%d mal" % n)
    check("gezaehlt als 'gross aufgeschoben'", g == 1, g)
    check("und zum Nachholen vorgemerkt",
          c._deferred_something is True and c._defer_count >= 1)

    # Jede der vier Bedingungen einzeln zurueckgenommen.
    r, n, g, _c = _frage("/c/gross.png", GROSS, defer=False)
    check("im Stillstand wird sofort gelesen",
          r is not None and r[2] == PIX_GROSS and n == 1 and g == 0,
          (n, g))
    r, n, g, _c = _frage("/c/gross.png", GROSS, ok=False)
    check("ohne auslagern_ok wird sofort gelesen (der Aufrufer kann "
          "mit 'kommt gleich' nicht umgehen)",
          r is not None and r[2] == PIX_GROSS and n == 1 and g == 0,
          (n, g))
    r, n, g, _c = _frage("/c/klein.png", KLEIN)
    check("ein Kasten unter einem Megabyte wird sofort gelesen",
          r is not None and r[2] == PIX_KLEIN and n == 1 and g == 0,
          (n, g))
    r, n, g, _c = _frage("/c/gibt_es_nicht.png", GROSS)
    check("ohne Miniatur auf der Karte greift die neue Regel nicht",
          r is None and g == 0, g)

    # Im Speicher: sofort da, auch beim Navigieren.
    c = A.ArtCache()
    c.auslagern = None
    c._defer_uncached = True
    check("nachgeladen_eintragen() nimmt das Bild an",
          c.nachgeladen_eintragen("/c/gross.png", GROSS[0], GROSS[1],
                                  (GROSS[0], GROSS[1], PIX_GROSS)))
    check("im_ram() sieht es", c.im_ram("/c/gross.png", *GROSS)
          and not c.im_ram("/c/klein.png", *KLEIN))
    del _gelesen[:]
    r = c.get_scaled("/c/gross.png", GROSS[0], GROSS[1], auslagern_ok=True)
    check("liegt es im Speicher, kommt es auch beim Navigieren sofort",
          r is not None and r[2] == PIX_GROSS and not _gelesen)

    # Gegenprobe: mit der Schwelle ausser Reichweite ist es der alte Weg.
    _alt_schwelle = A.GROSSE_MINIATUR_BYTES
    A.GROSSE_MINIATUR_BYTES = 1 << 40
    try:
        r, n, g, _c = _frage("/c/gross.png", GROSS)
    finally:
        A.GROSSE_MINIATUR_BYTES = _alt_schwelle
    check("Gegenprobe: ohne die Regel wird im Zeichenweg gelesen",
          r is not None and n == 1 and g == 0, (n, g))

    # -----------------------------------------------------------------------
    print()
    print("Test 3: die Marke 'das Original passt' wird nicht aufgeschoben")
    # -----------------------------------------------------------------------
    A._thumb_cache_put_marke("/c/marke.png", *GROSS)
    check("die Marke ist genau acht Byte gross",
          A.thumb_cache_groesse("/c/marke.png", *GROSS) == 8
          == A.GROSSE_MINIATUR_DATEI_MIN)
    r, n, g, c = _frage("/c/marke.png", GROSS)
    check("sie zaehlt nicht als 'gross aufgeschoben'", g == 0, g)
    check("sondern geht den bisherigen Weg (die Datei wird gelesen)",
          n == 1, n)
finally:
    A._thumb_cache_get = _echt_get

# ---------------------------------------------------------------------------
print()
print("Test 4: der Vorausleser")
# ---------------------------------------------------------------------------


class _Lader(object):
    """Steht fuer fe.nachladen.MiniaturLader."""

    def __init__(self):
        self.listen = []
        self.gestartet = 0
        self.letzte_dauer = 0.0
        self.fertig = []
        self.in_arbeit = None

    def start(self):
        self.gestartet += 1

    def uebergeben(self, auftraege):
        self.listen.append(list(auftraege))

    def abholen(self, hoechstens=8):
        raus, self.fertig = self.fertig[:hoechstens], self.fertig[hoechstens:]
        return raus

    def abbrechen(self):
        pass

    def beenden(self):
        pass


f = _liste()
ITEMS = [("Spiel %03d" % i, "game", ("/f/%d.sfc" % i, ".sfc", "SNES",
                                     None, None)) for i in range(40)]
AUF_KARTE = set(range(40))
_gefragt = []


def _pk(item, _sk, _geo):
    i = int(item[0].split()[1])
    _gefragt.append(i)
    return ("/c/%03d.png" % i, GROSS[0], GROSS[1])


def _nr(auftraege):
    return [int(os.path.basename(a[0])[:3]) for a in auftraege]


_alt_sofort = fm.cover_sofort_enabled
_alt_has = fm.thumb_cache_has
_alt_lader = f.lader
f.cover_pfad_und_kasten = _pk
fm.thumb_cache_has = lambda p, w, h: int(os.path.basename(p)[:3]) in AUF_KARTE
_sofort = [True]
fm.cover_sofort_enabled = lambda: _sofort[0]
A.ART.scaled = {}
A.ART.scaled_order = []
A.ART.scaled_bytes = 0


def _vl(item_i, richtung=1, abstand=None, dauer=0.0, v=None):
    """Ein Aufruf mit gestellter Uhr. Rueckgabe: (Nummern, Lader, v)."""
    lader = _Lader()
    lader.letzte_dauer = dauer
    f.lader = lader
    f._last_scroll_dir = richtung
    if abstand is None:
        f._vl_zeit = 0.0              # "lange her"
    else:
        f._vl_zeit = H.NOW[0] - abstand
    if v is None:
        v = {"items": ITEMS}
    aus = f._vorauslesen(v, "SNES", item_i, 800, 1000, 3)
    return _nr(aus), lader, v


try:
    H.NOW[0] = 1000.0
    _sofort[0] = False
    nr, lader, _v = _vl(10)
    check("ohne 'Cover sofort' wird nichts angemeldet",
          nr == [] and lader.listen == [] and lader.gestartet == 0, nr)
    _sofort[0] = True

    nr, lader, _v = _vl(10)
    check("langsames Tippen: die naechsten drei - und der Eintrag "
          "unter dem Zeiger ZULETZT", nr == [11, 12, 13, 10], nr)
    check("der Faden wird gestartet und bekommt genau diese Liste",
          lader.gestartet == 1 and len(lader.listen) == 1
          and _nr(lader.listen[0]) == nr)
    check("angemeldet wird das Tripel, das der Zeichenweg anfragt",
          lader.listen[0][0] == ("/c/011.png", GROSS[0], GROSS[1]))

    nr, _l, _v = _vl(10, richtung=-1)
    check("rueckwaerts geht es in die andere Richtung",
          nr == [9, 8, 7, 10], nr)

    # DIE RECHNUNG: angemeldet wird am Ende des Zeichnens von Eintrag
    # i, und i+1 wird gleich danach gezeichnet. Fuer i+ab hat der Faden
    # (ab - 1) Schrittabstaende Zeit - also ab = 1 + aufgerundet(Lade-
    # zeit / Abstand). Dahinter die naeheren Eintraege, zuletzt der
    # unter dem Zeiger.
    nr, _l, _v = _vl(10, abstand=0.05, dauer=0.10)
    check("50 ms je Schritt bei 100 ms je Bild: drei voraus (2 Abstaende "
          "Zeit = 100 ms)", nr == [13, 14, 15, 12, 11, 10], nr)
    nr, _l, _v = _vl(10, abstand=0.20, dauer=0.10)
    check("200 ms je Schritt: zwei voraus, dann der naechste, dann der "
          "unter dem Zeiger", nr == [12, 13, 14, 11, 10], nr)
    nr, _l, _v = _vl(10, abstand=0.16, dauer=0.087)
    check("die Zahlen seines Bench (87 ms je Bild, 160 ms je Schritt): "
          "zwei voraus", nr[:3] == [12, 13, 14], nr)
    nr, _l, _v = _vl(10, abstand=0.01, dauer=0.50)
    check("der Vorgriff ist begrenzt (VORAUS_WEITESTER)",
          nr[:3] == list(range(10 + f.VORAUS_WEITESTER,
                               10 + f.VORAUS_WEITESTER + f.VORAUS_ZAHL))
          and nr[-1] == 10 and len(nr) == 3 + f.VORAUS_WEITESTER, nr)
    nr, _l, _v = _vl(10, abstand=0.05, dauer=0.0)
    check("kennt der Faden noch keine Dauer, gilt ein Zehntel",
          nr == [13, 14, 15, 12, 11, 10], nr)
    # Liest der Faden gerade, braucht er laenger: erst fertig werden.
    lader = _Lader()
    lader.letzte_dauer = 0.10
    lader.in_arbeit = ("/c/099.png", GROSS[0], GROSS[1])
    f.lader = lader
    f._last_scroll_dir = 1
    f._vl_zeit = H.NOW[0] - 0.05
    nr = _nr(f._vorauslesen({"items": list(ITEMS)}, "SNES", 10, 800,
                            1000, 3))
    check("liest der Faden gerade, wird einen Eintrag weiter gegriffen",
          nr[:3] == [14, 15, 16], nr)
    # Gegenprobe zur Rechnung: der alte Vorgriff (Ladezeit / Abstand
    # + 1, ohne den Schritt, der sofort folgt) haette bei 160 ms und
    # 87 ms den NAECHSTEN Eintrag als Ziel genommen - fuer den bleibt
    # dem Faden keine Zeit.
    check("Gegenprobe: die alte Formel haette hier Eintrag 11 als Ziel",
          int(0.087 / 0.16) + 1 == 1)

    # Raender.
    nr, _l, _v = _vl(38)
    check("am Listenende wird nicht ueber das Ende hinaus gefragt",
          nr == [39, 38], nr)
    nr, _l, _v = _vl(1, richtung=-1)
    check("am Listenanfang nicht vor den Anfang", nr == [0, 1], nr)
    nr, lader, _v = _vl(0, v={"items": ITEMS[:1]})
    check("eine Liste mit einem Eintrag: nichts", nr == []
          and lader.listen == [])

    # Was schon im Speicher liegt oder nicht auf der Karte ist.
    A.ART.nachgeladen_eintragen("/c/011.png", GROSS[0], GROSS[1],
                                (2, 2, b"\0" * 16))
    AUF_KARTE.discard(12)
    nr, _l, _v = _vl(10)
    check("im Speicher (11) und nicht auf der Karte (12) fallen heraus",
          nr == [13, 10], nr)
    AUF_KARTE.add(12)
    A.ART.scaled = {}
    A.ART.scaled_order = []
    A.ART.scaled_bytes = 0

    # Der Merker: beim Halten fragen Schritte fast dieselben Eintraege.
    del _gefragt[:]
    nr, _l, v = _vl(10)
    erste = list(_gefragt)
    del _gefragt[:]
    _vl(11, abstand=0.5, v=v)
    check("der zweite Schritt rechnet nur die NEUEN Eintraege aus",
          erste == [11, 12, 13, 10] and _gefragt == [14, 15], _gefragt)
    # Beim Halten in einer langen Liste ist jeder Schritt ein voller
    # Aufbau, und der legt self.view NEU an. Die Liste bleibt dieselbe.
    del _gefragt[:]
    _vl(12, abstand=0.5, v={"items": ITEMS})
    check("auch mit neu angelegter Ansicht, solange es DIESELBE Liste "
          "ist", _gefragt == [16], _gefragt)
    check("der Merker haengt also an der Liste, nicht an der Ansicht",
          "_vl_merk" not in v and f._vl_merk[0] is ITEMS)
    del _gefragt[:]
    _vl(12, abstand=0.5, v={"items": list(ITEMS)})
    check("eine ANDERE Liste (gleicher Inhalt) wirft ihn weg",
          _gefragt == [14, 15, 16, 13, 12], _gefragt)
    del _gefragt[:]
    f.lader = _Lader()
    f._vl_zeit = H.NOW[0] - 0.5
    f._vorauslesen({"items": f._vl_merk[0]}, "SNES", 12, 640, 1000, 3)
    check("eine andere Kastengroesse ebenso",
          _gefragt == [14, 15, 16, 13, 12], _gefragt)
    del _gefragt[:]
    _vl(12, v={"items": f._vl_merk[0]})
    check("und eine Pause auch - danach kann sich der Kasten geaendert "
          "haben", _gefragt == [13, 14, 15, 12], _gefragt)
    # Ein Nein von der Karte wird NICHT gemerkt: der Arbeitsprozess
    # schreibt waehrenddessen.
    eigene = list(ITEMS)
    AUF_KARTE.discard(21)
    nr1, _l, _v = _vl(20, v={"items": eigene})
    AUF_KARTE.add(21)
    nr2, _l, _v = _vl(20, abstand=0.5, v={"items": eigene})
    check("ein Cover, das eben noch fehlte, wird im selben Lauf "
          "gefunden", nr1 == [22, 23, 20]
          and nr2 == [22, 23, 24, 21, 20], (nr1, nr2))

    # Was der Faden GERADE liest, wird nicht noch einmal angemeldet -
    # eine neue Liste bricht nur ab, was noch nicht begonnen wurde.
    lader = _Lader()
    lader.in_arbeit = ("/c/031.png", GROSS[0], GROSS[1])
    f.lader = lader
    f._vl_zeit = 0.0
    f._last_scroll_dir = 1
    aus = f._vorauslesen({"items": list(ITEMS)}, "SNES", 30, 800, 1000, 3)
    check("der laufende Auftrag (31) faellt heraus", _nr(aus)
          == [32, 33, 30], _nr(aus))
    # Und was er eben fertig hat, wird vorher eingetragen statt neu
    # angemeldet.
    lader = _Lader()
    lader.fertig = [("/c/032.png", GROSS[0], GROSS[1], (2, 2, b"\0" * 16))]
    f.lader = lader
    f._vl_zeit = 0.0
    aus = f._vorauslesen({"items": list(ITEMS)}, "SNES", 30, 800, 1000, 3)
    check("der eben fertige (32) ist schon eingetragen und faellt heraus",
          _nr(aus) == [31, 33, 30]
          and A.ART.im_ram("/c/032.png", *GROSS), _nr(aus))
    A.ART.scaled = {}
    A.ART.scaled_order = []
    A.ART.scaled_bytes = 0
    # Die Pause des Fadens zwischen zwei Bildern zaehlt zur Dauer.
    lader = _Lader()
    lader.PAUSE = 0.06
    lader.letzte_dauer = 0.05
    f.lader = lader
    f._vl_zeit = H.NOW[0] - 0.05
    aus = f._vorauslesen({"items": list(ITEMS)}, "SNES", 10, 800, 1000, 3)
    check("50 ms Lesen + 60 ms Pause bei 50 ms je Schritt: vier voraus",
          _nr(aus)[:3] == [14, 15, 16], _nr(aus))

    # Ohne Faden: kein Absturz, nichts zu tun.
    f.lader = None
    f._vl_zeit = 0.0
    check("ohne Nachlade-Faden kommt eine leere Liste",
          f._vorauslesen({"items": ITEMS}, "SNES", 10, 800, 1000, 3) == [])

    # -----------------------------------------------------------------------
    print()
    print("Test 5: der Zeichenweg der Spieleliste ruft ihn")
    # -----------------------------------------------------------------------
    f.lader = lader = _Lader()
    _rufe = []
    _echt_vl = type(f)._vorauslesen

    def _vl_haken(v, syskey, item_i, art_w, art_h, s):
        _rufe.append((f.page, item_i))
        return _echt_vl(f, v, syskey, item_i, art_w, art_h, s)

    f._vorauslesen = _vl_haken
    f._last_input_time = 0
    alt = f.item_i
    f.item_i = alt + 1
    leicht = f._draw_navigate_items(alt)
    check("ein leichter Schritt in der Spieleliste ruft den Vorausleser "
          "genau einmal, fuer den neuen Eintrag",
          bool(leicht) and _rufe == [(1, alt + 1)], _rufe)
    del _rufe[:]
    f.draw()
    check("der VOLLE Aufbau ruft ihn auch - beim Halten wandert das "
          "Fenster, und dann ist jeder Schritt ein voller Aufbau",
          _rufe == [(1, alt + 1)], _rufe)
    del f._vorauslesen

    # VON DER ANDEREN SEITE: was der Zeichenweg fuer den NAECHSTEN
    # Eintrag anfragt, muss genau das sein, was einen Schritt vorher
    # angemeldet wurde - sonst landet das Bild unter einem Schluessel,
    # den nie jemand abfragt. Hier laeuft die ECHTE
    # cover_pfad_und_kasten().
    f.__dict__.pop("cover_pfad_und_kasten", None)
    f.cover_quelle = lambda syskey, name: "/art/%s/%s.png" % (syskey, name)
    fm.thumb_cache_has = lambda p, w, h: True
    _angefragt = []
    _echt_scaled = A.ART.get_scaled

    def _scaled(path, w, h, **k):
        _angefragt.append((path, w, h))
        return None

    A.ART.get_scaled = _scaled
    try:
        for _weg in ("leicht", "voll"):
            f.lader = lader = _Lader()
            f._vl_zeit = 0.0
            f._last_scroll_dir = 1
            alt = f.item_i
            f.item_i = alt + 1
            if _weg == "voll" or not f._draw_navigate_items(alt):
                f.draw()
            angemeldet = lader.listen[-1] if lader.listen else []
            del _angefragt[:]
            alt = f.item_i
            f.item_i = alt + 1
            if _weg == "voll" or not f._draw_navigate_items(alt):
                f.draw()
            _spalte = [a for a in _angefragt if a[0].startswith("/art/")]
            check("%s: der naechste Schritt fragt genau das Tripel an, "
                  "das vorher als ERSTES angemeldet war" % _weg,
                  len(_spalte) >= 1 and len(angemeldet) == 4
                  and _spalte[0] == angemeldet[0],
                  "%s in %s" % (_spalte[:1], angemeldet))
    finally:
        A.ART.get_scaled = _echt_scaled
        del f.cover_quelle
    f.cover_pfad_und_kasten = _pk
    fm.thumb_cache_has = lambda p, w, h: (
        int(os.path.basename(p)[:3]) in AUF_KARTE)
    check("_art_panel_aktualisieren() ruft ihn nur auf Seite 1",
          "if self.page == 1:\n            self._vorauslesen("
          in koerper(_Q, "_art_panel_aktualisieren", "Frontend"))

    # -----------------------------------------------------------------------
    print()
    print("Test 6: geholt wird VOR dem Zeichnen eingetragen")
    # -----------------------------------------------------------------------
    A.ART.scaled = {}
    A.ART.scaled_order = []
    A.ART.scaled_bytes = 0
    f.lader = lader = _Lader()
    lader.fertig = [("/c/777.png", GROSS[0], GROSS[1],
                     (4, 4, b"\x01" * 64))]
    check("_lader_einsammeln() traegt ein und zaehlt",
          f._lader_einsammeln() == 1
          and A.ART.im_ram("/c/777.png", *GROSS))
    check("ein zweites Mal gibt es nichts mehr",
          f._lader_einsammeln() == 0)
    f.lader = None
    check("ohne Faden: 0, kein Absturz", f._lader_einsammeln() == 0)

    f.lader = lader = _Lader()
    lader.fertig = [("/c/778.png", GROSS[0], GROSS[1],
                     (4, 4, b"\x02" * 64))]
    _beim_zeichnen = []
    _echt_panel = f.draw_art_panel

    def _panel(*a, **k):
        _beim_zeichnen.append(A.ART.im_ram("/c/778.png", *GROSS))
        return _echt_panel(*a, **k)

    f.draw_art_panel = _panel
    alt = f.item_i
    f.item_i = alt + 1
    f._draw_navigate_items(alt)
    del f.draw_art_panel
    check("der leichte Pfad sammelt ein, BEVOR die Boxart-Spalte "
          "gezeichnet wird", _beim_zeichnen == [True], _beim_zeichnen)
    _nx = koerper(_Q, "next_action", "Frontend")
    check("im Leerlauf wird vor dem Nachzeichnen eingesammelt",
          0 < _nx.find("self._lader_einsammeln()")
          < _nx.find("self._nachzeichnen_vorbereiten()"))
finally:
    fm.cover_sofort_enabled = _alt_sofort
    fm.thumb_cache_has = _alt_has
    f.lader = _alt_lader
    f.__dict__.pop("cover_pfad_und_kasten", None)

# ---------------------------------------------------------------------------
print()
print("Test 7: der Faden nennt die Dauer des letzten Lesens")
# ---------------------------------------------------------------------------


_waehrend = []


def _langsam(pfad, w, h):
    _waehrend.append(ml.in_arbeit)
    if pfad == "/fehlt":
        return None
    time.sleep(0.03)
    return (w, h, b"\0" * 4)


# Der Pruefstand haelt die Uhr an - der Faden braucht die echte.
_gefroren = time.monotonic
time.monotonic = _ECHTE_UHR
ml = N.MiniaturLader(_langsam)
check("vor dem ersten Bild ist die Dauer 0", ml.letzte_dauer == 0.0)
ml.start()
ml.uebergeben([("/a", 1, 1)])
_ende = _ECHTE_UHR() + 3.0
while ml.geholt < 1 and _ECHTE_UHR() < _ende:
    time.sleep(0.005)
d1 = ml.letzte_dauer
check("nach einem Bild steht sie da, in Sekunden",
      ml.geholt == 1 and 0.02 <= d1 < 1.0, "%.3f s" % d1)
ml.uebergeben([("/fehlt", 1, 1)])
_ende = _ECHTE_UHR() + 3.0
while ml.nicht_da < 1 and _ECHTE_UHR() < _ende:
    time.sleep(0.005)
check("ein Fehlgriff aendert sie nicht (er sagt nichts ueber das Lesen)",
      ml.nicht_da == 1 and ml.letzte_dauer == d1)
check("waehrend des Lesens nennt der Faden seinen Auftrag",
      _waehrend == [("/a", 1, 1), ("/fehlt", 1, 1)], _waehrend)
time.sleep(0.05)
check("und danach nichts mehr", ml.in_arbeit is None, ml.in_arbeit)
ml.beenden()
time.monotonic = _gefroren

# ---------------------------------------------------------------------------
print()
print("Test 8: das Auspacken kopiert die Datei nicht mehr")
# ---------------------------------------------------------------------------
_w, _h = 64, 48
_pix = bytes(bytearray((i * 7) % 256 for i in range(_w * _h * 4)))
_cp = A._thumb_cache_path(A._thumb_cache_key("/c/art1.png", _w, _h))
os.makedirs(os.path.dirname(_cp), exist_ok=True)
with open(_cp, "wb") as _f:
    _f.write(b"ART1" + struct.pack("<HH", _w, _h) + zlib.compress(_pix, 1))
A._thumb_fehlt.discard(_cp)
r = A._thumb_cache_get("/c/art1.png", _w, _h)
check("eine ART1-Miniatur kommt bitgleich zurueck",
      r is not None and r[0] == _w and r[1] == _h and r[2] == _pix
      and type(r[2]) is bytes)
_tg = koerper(open(os.path.join(_REPO, "frontend", "fe", "art.py"),
                   encoding="utf-8").read(), "_thumb_cache_get")
check("die Nutzlast ist dort ein Blick (memoryview), keine Kopie",
      "memoryview(rohdaten)[8:]" in _tg)
with open(_cp, "wb") as _f:
    _f.write(b"ART1" + struct.pack("<HH", _w, _h) + b"kaputt")
check("eine kaputte Datei gibt None, keinen Absturz",
      A._thumb_cache_get("/c/art1.png", _w, _h) is None)

A.THUMB_CACHE_BASE, A.THUMB_CACHE_DIR = _ALT_BASE, _ALT_DIR
time.sleep(0.3)
shutil.rmtree(TMP, ignore_errors=True)

print()
if fails:
    print("ROT: %d Pruefung(en) fehlgeschlagen:" % len(fails))
    for f_ in fails:
        print("   - " + f_)
    sys.exit(1)
print("ALLES GRUEN")
