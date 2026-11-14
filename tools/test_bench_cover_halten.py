#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cover bei gehaltener Taste - durch den ganzen Weg (Build 320).

DER ANLASS: "was mich auch noch ein wenig stoert ist das scrollen in
der listen ansicht mit eingeschalteten cover wechsel das das nicht
schneller laeuft".

tools/test_vorauslesen.py prueft die Teile einzeln, mit einer Attrappe
anstelle des Nachlade-Fadens. Das beweist, dass jedes Teil tut, was es
soll - aber nicht, dass am Ende ein Cover auf dem Schirm steht. Genau
diese Luecke hat in diesem Projekt schon mehrfach einen Fehler
durchgelassen ("ein Test, der den Zeichenweg von unten anstoesst,
prueft nie, ob ihn ueberhaupt jemand erreicht").

HIER LAEUFT ALLES ECHT: echte Cover-Dateien, echte Miniaturen auf der
(temporaeren) Karte, der echte Faden, der echte Zeichenweg - gefahren
vom Bench-Abschnitt O, also von demselben Code, der auf seinem Geraet
misst. Nur zwei Dinge werden gestellt, und zwar um das GERAET
nachzubilden: das Lesen von der Karte und das Zeichnen der Spalte
bekommen je 30 ms Aufschlag. Ohne das waere der Entwicklungsrechner
so schnell, dass die Pause des Fadens (10 ms) alles bestimmt.

WAS DIESER TEST SICHERT:
  1. "wie bisher" zeigt jedes Cover - und zahlt je Schritt das Lesen,
  2. "jetzt" ist um das Lesen schneller,
  3. im alten Tempo kommt (bis auf den ersten Schritt) JEDES Cover
     rechtzeitig an - nichts geht verloren, was vorher zu sehen war,
  4. die Gegenprobe: liefert der Faden nichts, steht in derselben
     Zeile "alle ohne Cover" - die Zahl kann also schlecht werden,
  5. der Abschnitt hinterlaesst alles, wie er es vorgefunden hat,
  6. ohne Cover sagt er das, statt Zahlen zu erfinden,
  7. lauf() faehrt ihn mit eigenem Fangnetz.

Ausfuehren:
    python3 tools/test_bench_cover_halten.py
"""
import contextlib
import io
import os
import re
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
import fe.bench as B                                     # noqa: E402
import fe.settings as S                                  # noqa: E402
from _quelle import koerper, nur_code                    # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


print(__doc__.strip().split("\n")[0])
print()

TMP = tempfile.mkdtemp(prefix="cover_halten_")
_ALT_BASE, _ALT_DIR = A.THUMB_CACHE_BASE, A.THUMB_CACHE_DIR
A.THUMB_CACHE_BASE = os.path.join(TMP, "thumbs")

# Cover, die GROESSER sind als der Kasten der Listenansicht - sonst
# entsteht nur die Marke "das Original passt" und keine Miniatur.
CB, CH = 800, 1000
ANZAHL = 24
_zeile = bytearray()
for _x in range(CB):
    _zeile += bytes(((_x * 3) % 256, (_x * 5) % 256, (_x * 7) % 256, 255))
COVER = []
for _i in range(ANZAHL):
    _pix = bytearray()
    _kopf = bytes(((_i * 9) % 256, 40, 200 - _i, 255)) * CB
    for _y in range(CH):
        _pix += _kopf if _y % 50 < 10 else _zeile
    _p = os.path.join(TMP, "cover_%02d.art" % _i)
    with open(_p, "wb") as _f:
        _f.write(b"ART1" + struct.pack("<HH", CB, CH)
                 + zlib.compress(bytes(_pix), 1))
    COVER.append(_p)

AUFSCHLAG = 0.03              # je Lesen und je Spalte, siehe oben


def _mit_spielen(fe, n=300):
    _nm, node, _sk = fe.cats[0]
    node["items"] = [("Spiel Nummer %03d" % i, "game",
                      ("/f/%d.sfc" % i, ".sfc", "SNES", None, None))
                     for i in range(n)]
    node.pop("_display_items_cache", None)


def _quelle(_syskey, name):
    try:
        return COVER[int(str(name).split()[-1]) % ANZAHL]
    except (ValueError, IndexError):
        return None


_echt_get = A._thumb_cache_get


def _langsame_karte(*a, **k):
    time.sleep(AUFSCHLAG)
    return _echt_get(*a, **k)


def abschnitt_o(mit_cover=True, faden_liefert=True):
    """Abschnitt O gegen ein echtes Frontend. Rueckgabe: (Text, fe)."""
    H._zwischenspeicher_leeren()
    H.set_screen(1920, 1080)
    fe = H.make_frontend(page=0)
    A.thumb_cache_modus_setzen(True)
    A.ART.auslagern = None
    A.ART.ram_leeren()
    _mit_spielen(fe)
    if mit_cover:
        fe.cover_quelle = _quelle
    fe.page, fe.cat_i, fe.item_i = 0, 0, 0
    _echt_panel = fe.draw_art_panel

    def _panel(*a, **k):
        time.sleep(AUFSCHLAG)
        return _echt_panel(*a, **k)

    fe.draw_art_panel = _panel
    _echt_lesen = fe.lader._lesen
    if not faden_liefert:
        fe.lader._lesen = lambda *_a: None
    A._thumb_cache_get = _langsame_karte
    ber = B.Bericht()
    gefroren = time.monotonic
    time.monotonic = _ECHTE_UHR
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            B._abschnitt_o(ber, fe, S, A, fm)
    finally:
        time.monotonic = gefroren
        A._thumb_cache_get = _echt_get
        fe.lader._lesen = _echt_lesen
        del fe.draw_art_panel
    return ber.text(), fe


_Z = re.compile(r"^\s+(wie bisher|jetzt, im alten Tempo|jetzt)\s+"
                r"([\d.]+) ms/Schritt\s+([\d.]+) Schritte/s\s+"
                r"ohne Cover\s+(\d+) von (\d+)\s*$", re.M)


def zahlen(text):
    return dict((m.group(1), (float(m.group(2)), int(m.group(4)),
                              int(m.group(5))))
                for m in _Z.finditer(text))


_s_sofort = fm.cover_sofort_enabled
_s_schwelle = A.GROSSE_MINIATUR_BYTES

try:
    # -----------------------------------------------------------------------
    print("Test 1-3: echte Cover, echter Faden")
    # -----------------------------------------------------------------------
    text, fe = abschnitt_o()
    z = zahlen(text)
    check("die Ueberschrift steht da",
          " O  Listenansicht mit Cover, Taste gehalten" in text)
    check("alle 24 Eintraege haben eine grosse Miniatur auf der Karte",
          "davon mit grosser Miniatur auf der Karte   24" in text,
          [x for x in text.splitlines() if "Miniatur" in x][:1])
    check("drei Laeufe stehen im Bericht", sorted(z)
          == ["jetzt", "jetzt, im alten Tempo", "wie bisher"], sorted(z))
    if len(z) == 3:
        alt, neu, takt = (z["wie bisher"], z["jetzt"],
                          z["jetzt, im alten Tempo"])
        check("wie bisher: jedes Cover wird gezeigt",
              alt[1] == 0 and alt[2] == 23, alt)
        check("wie bisher zahlt je Schritt das Lesen UND die Spalte",
              alt[0] >= 2 * AUFSCHLAG * 1000.0, "%.1f ms" % alt[0])
        check("jetzt ist um (fast) das Lesen schneller",
              neu[0] <= alt[0] - AUFSCHLAG * 1000.0 * 0.6,
              "%.1f statt %.1f ms je Schritt" % (neu[0], alt[0]))
        check("im alten Tempo kommt jedes Cover an - hoechstens die "
              "ersten beiden Schritte nicht", takt[1] <= 2,
              "%d von %d ohne Cover" % (takt[1], takt[2]))
        check("und das alte Tempo wurde wirklich gehalten",
              abs(takt[0] - alt[0]) <= alt[0] * 0.25,
              "%.1f gegen %.1f ms" % (takt[0], alt[0]))
    check("der Faden nennt seine Lesedauer",
          re.search(r"Letztes Lesen im Faden\s+[\d.]+ ms", text) is not None)

    # -----------------------------------------------------------------------
    print()
    print("Test 5: der Abschnitt raeumt auf")
    # -----------------------------------------------------------------------
    check("'Cover sofort' ist wieder die echte Abfrage",
          fm.cover_sofort_enabled is _s_sofort)
    check("die Schwelle steht wieder", A.GROSSE_MINIATUR_BYTES
          == _s_schwelle)
    check("der Vorausleser ist wieder der echte",
          "_vorauslesen" not in fe.__dict__)
    check("Seite, Kategorie und Zeiger stehen wie vorher",
          (fe.page, fe.cat_i, fe.item_i) == (0, 0, 0)
          and list(fe.nav_path) == [])
    fe.lader.beenden()

    # -----------------------------------------------------------------------
    print()
    print("Test 4: Gegenprobe - der Faden liefert nichts")
    # -----------------------------------------------------------------------
    text2, fe2 = abschnitt_o(faden_liefert=False)
    z2 = zahlen(text2)
    check("drei Laeufe stehen im Bericht", len(z2) == 3, sorted(z2))
    if len(z2) == 3:
        check("wie bisher bleibt davon unberuehrt",
              z2["wie bisher"][1] == 0, z2["wie bisher"])
        check("im alten Tempo steht jetzt JEDER Schritt ohne Cover da - "
              "die Zahl kann schlecht werden",
              z2["jetzt, im alten Tempo"][1] == 23,
              z2["jetzt, im alten Tempo"])
    fe2.lader.beenden()

    # -----------------------------------------------------------------------
    print()
    print("Test 6: ohne Cover")
    # -----------------------------------------------------------------------
    text3, fe3 = abschnitt_o(mit_cover=False)
    check("eine ehrliche Zeile statt Zahlen",
          "-- nichts zu messen" in text3 and not zahlen(text3),
          [x for x in text3.splitlines() if "--" in x][:1])
    check("auch dann wird aufgeraeumt",
          fm.cover_sofort_enabled is _s_sofort
          and A.GROSSE_MINIATUR_BYTES == _s_schwelle)
    fe3.lader.beenden()
finally:
    fm.cover_sofort_enabled = _s_sofort
    A.GROSSE_MINIATUR_BYTES = _s_schwelle
    A.THUMB_CACHE_BASE, A.THUMB_CACHE_DIR = _ALT_BASE, _ALT_DIR
    time.sleep(0.5)
    shutil.rmtree(TMP, ignore_errors=True)

# ---------------------------------------------------------------------------
print()
print("Test 7: eingetragen im Lauf")
# ---------------------------------------------------------------------------
_QB = open(os.path.join(_REPO, "frontend", "fe", "bench.py"),
           encoding="utf-8").read()
_lauf = nur_code(koerper(_QB, "lauf"))
check("lauf() ruft _abschnitt_o()", "_abschnitt_o(" in _lauf)
check("nach Abschnitt N", 0 < _lauf.find("_abschnitt_n(")
      < _lauf.find("_abschnitt_o("))
check("mit eigenem Fangnetz", "ABSCHNITT O ABGEBROCHEN" in _lauf)
_o = koerper(_QB, "_abschnitt_o")
check("der Abschnitt stellt im finally zurueck",
      "fm.cover_sofort_enabled = _s_sofort" in _o.split("finally:")[-1]
      and "A.GROSSE_MINIATUR_BYTES = _s_schwelle" in _o.split("finally:")[-1])

print()
if fails:
    print("ROT: %d Pruefung(en) fehlgeschlagen:" % len(fails))
    for f_ in fails:
        print("   - " + f_)
    sys.exit(1)
print("ALLES GRUEN")
