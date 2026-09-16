#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ein Scrollschritt darf die SD-Karte nicht anfassen (Build 135).

WAS GEMESSEN WURDE. Ein einzelner Schritt im Raster fasste die Karte
FUENFMAL an:

    open    /media/fat/frontend/retroachievements.cfg
    open    /media/fat/frontend/ansicht
    exists  /media/fat/frontend/profile
    exists  /media/fat/frontend/thumb_cache/hd
    exists  /media/fat/frontend/fast_scroll_enabled

Bei jedem Tastendruck, fuer Werte, die sich nur aendern, wenn der
Nutzer im Menue etwas umstellt.

WARUM DAS AUF DER ENTWICKLUNGSMASCHINE UNSICHTBAR IST. Dort liegen die
Dateien im Dateisystem-Cache und ein Zugriff kostet Mikrosekunden. Auf
dem MiSTer ist es exFAT auf einer SD-Karte: open() plus read() kostet
1-5 ms, und deutlich mehr, wenn die Karte gerade beschaeftigt ist -
Vorauslader, Nachlader, Musik lesen alle von derselben Karte.

Das ist die Erklaerung fuer "meistens fluessig, manchmal ein Haenger":
nicht der Durchschnitt, sondern der Ausreisser.

DIESER TEST MISST DESHALB NICHT DIE ZEIT, sondern die ZUGRIFFE. Zeit
schwankt und wuerde hier nichts aussagen; die Anzahl der Kartenzugriffe
ist eine harte Zahl, die sich auf jeder Maschine gleich verhaelt.

Ausfuehren:
    python3 tools/test_kartenzugriffe.py
"""
import builtins
import os
import shutil
import struct
import sys
import tempfile
import zlib

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)

import _harness as H                                    # noqa: E402

fm = H.fm
sys.path.insert(0, os.path.join(_REPO, "frontend"))
import fe.art as A                                      # noqa: E402
import fe.zwischenspeicher as ZS                        # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


TMP = tempfile.mkdtemp(prefix="kartenzugriffe_")
B = os.path.join(TMP, "art")
os.makedirs(os.path.join(B, "SNES"))
TITEL = ["Spiel %02d" % i for i in range(40)]
for i, t in enumerate(TITEL):
    with open(os.path.join(B, "SNES", t + ".art"), "wb") as f:
        f.write(b"ART1" + struct.pack("<HH", 400, 533)
                + zlib.compress(bytes((i % 256, 99, 50, 255)) * (400 * 533), 1))
fm.ART_BASE = A.ART_BASE = B
fm.ART_HD = A.ART_HD = B
A._art_index_cache.clear()
A.THUMB_CACHE_DIR = os.path.join(TMP, "tc")
os.makedirs(A.THUMB_CACHE_DIR)


def frontend_mit_covern(ansicht):
    H.set_screen(1920, 1080)
    f = H.make_frontend(page=1)
    fm.ART.auslagern = None
    f.lader.beenden()
    _n, node, _k = f.cats[f.cat_i]
    node["items"] = [(t, "game", ("/f/%d.sfc" % i, ".sfc", "SNES", None, None))
                     for i, t in enumerate(TITEL)]
    node.pop("_display_items_cache", None)
    f.ansicht_setzen(ansicht)
    for i in range(22):                  # alles warm rechnen
        f.item_i = i
        f.draw()
    return f


def zugriffe(f, schritte):
    """Wie oft fasst eine Folge von Schritten /media/fat an?"""
    geoeffnet = []
    geprueft = []
    echt_open, echt_exists = builtins.open, os.path.exists
    builtins.open = lambda p, *a, **k: (geoeffnet.append(str(p)),
                                        echt_open(p, *a, **k))[1]
    os.path.exists = lambda p: (geprueft.append(str(p)), echt_exists(p))[1]
    try:
        for k in range(schritte):
            f.item_i = 1 + (k % 6)       # bewusst INNERHALB einer Seite
            f.draw()
    finally:
        builtins.open = echt_open
        os.path.exists = echt_exists
    auf_karte = [p for p in geoeffnet + geprueft if p.startswith("/media/fat")]
    # Der Miniatur-Zwischenspeicher wird hier ausgeklammert, und das ist
    # keine Bequemlichkeit: er SCHREIBT im Hintergrund frisch gerechnete
    # Miniaturen (die ".art.tmp..."-Dateien), und genau dafuer ist er da.
    # Das ist Arbeit, die anfaellt, weil ein Cover neu war - nicht ein
    # Nachschlagen einer Einstellung bei jedem Tastendruck. Nur um
    # letzteres geht es hier.
    return [p for p in auf_karte if "/thumb_cache/" not in p]


# ---------------------------------------------------------------------
print("Test 1: zehn Rasterschritte fassen die Karte kaum noch an")
f = frontend_mit_covern("raster")
f._last_input_time = fm.time.monotonic() - 0.05      # schnelle Folge
treffer = zugriffe(f, 10)
check("kein Einstellungs-Zugriff auf zehn Schritte", not treffer,
      "%d Zugriffe: %s" % (len(treffer), sorted(set(treffer))))
# Die Einstellungsdateien duerfen ueberhaupt nicht mehr vorkommen.
for name in ("retroachievements.cfg", "/ansicht", "/profile",
             "fast_scroll_enabled"):
    check("%-22s wird nicht mehr je Schritt gelesen" % name.strip("/"),
          not any(name in p for p in treffer),
          repr([p for p in treffer if name in p]))

print()
print("Test 2: dasselbe in Liste und Galerie")
for ansicht in ("liste", "galerie"):
    f2 = frontend_mit_covern(ansicht)
    f2._last_input_time = fm.time.monotonic() - 0.05
    t2 = zugriffe(f2, 10)
    check("%-8s kein Einstellungs-Zugriff auf zehn Schritte" % ansicht,
          not t2, "%d: %s" % (len(t2), sorted(set(t2))))

# ---------------------------------------------------------------------
print()
print("Test 3: eine Aenderung im Menue wirkt trotzdem SOFORT")
# Das ist die Gegenprobe. Ein Zwischenspeicher, der eine Umstellung
# verschluckt, waere schlimmer als die Kartenzugriffe - man wuerde eine
# halbe Sekunde lang glauben, der Schalter sei kaputt.
import fe.settings as S                                 # noqa: E402

_alt_datei = S.ANSICHT_FILE
S.ANSICHT_FILE = os.path.join(TMP, "ansicht")
try:
    ZS.vergessen()
    S.ansicht_schreiben("raster")
    check("nach ansicht_schreiben() gilt der neue Wert sofort",
          S.ansicht_lesen() == "raster", S.ansicht_lesen())
    S.ansicht_schreiben("galerie")
    check("und beim naechsten Wechsel wieder", S.ansicht_lesen() == "galerie",
          S.ansicht_lesen())
finally:
    S.ANSICHT_FILE = _alt_datei
    ZS.vergessen()

_alt_flag = S.FAST_SCROLL_ENABLED_FLAG
S.FAST_SCROLL_ENABLED_FLAG = os.path.join(TMP, "fast_scroll")
try:
    ZS.vergessen()
    vorher = S.fast_scroll_enabled()
    S.toggle_fast_scroll()
    check("toggle_fast_scroll() wirkt sofort",
          S.fast_scroll_enabled() != vorher)
    S.toggle_fast_scroll()
    check("und wieder zurueck", S.fast_scroll_enabled() == vorher)
finally:
    S.FAST_SCROLL_ENABLED_FLAG = _alt_flag
    ZS.vergessen()

# ---------------------------------------------------------------------
print()
print("Test 4: der Schluessel haengt am PFAD, nicht nur am Namen")
# Darueber ist tools/test_cover_prewarm.py beim Bauen gestolpert: es
# biegt FAST_SCROLL_ENABLED_FLAG auf einen Testpfad um. Haette der
# Zwischenspeicher nur unter "fast_scroll" gemerkt, gaebe er danach den
# Wert der ECHTEN Datei zurueck.
a = os.path.join(TMP, "flag_a")
b = os.path.join(TMP, "flag_b")
open(a, "w").close()
ZS.vergessen()
S.FAST_SCROLL_ENABLED_FLAG = a
erst = S.fast_scroll_enabled()
S.FAST_SCROLL_ENABLED_FLAG = b            # existiert NICHT
dann = S.fast_scroll_enabled()
S.FAST_SCROLL_ENABLED_FLAG = _alt_flag
ZS.vergessen()
check("ein anderer Pfad liefert einen anderen Wert",
      erst is True and dann is False, "%r / %r" % (erst, dann))

# ---------------------------------------------------------------------
print()
print("Test 5: die Zeitspanne ist kurz genug fuer Aenderungen von aussen")
# Wer per SSH eine Einstellungsdatei aendert, soll nicht minutenlang
# warten. Eine halbe Sekunde merkt niemand.
check("hoechstens eine Sekunde", ZS.GUELTIG_MS <= 1.0, str(ZS.GUELTIG_MS))
check("und nicht null - sonst waere der ganze Zweck weg",
      ZS.GUELTIG_MS > 0)

shutil.rmtree(TMP, ignore_errors=True)

print()
if fails:
    print("FEHLGESCHLAGEN (%d):" % len(fails))
    for f_ in fails:
        print("  -", f_)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
