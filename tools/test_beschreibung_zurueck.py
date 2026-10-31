#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Die Beschreibung bleibt beim Scrollen weg (Build 300).

WORUM ES GEHT. Befund des Nutzers: "irgendwie kommt es mir so vor als
wenn der zuviel nachladen oder berechnen muss komisch beim scrollen
nach rechts und links ist gefuehlt nicht viel besser geworden".

Er hat recht, und sein eigener Bericht sagt, warum. In der Galerie
kostet ein Seitwaertsschritt 48,69 ms (Abschnitt J), und die beiden
groessten Posten sind:

    restore  14,33 ms   ueber 1201 Bildzeilen
    flip      8,71 ms   ueber 2,6 MB

Von diesen 1201 Zeilen gehoeren rund 650 der TEXTSPALTE - und die muss
nur deshalb in dieser Hoehe freigeraeumt werden, weil die Beschreibung
bis dort hinunter reicht. Dazu kommt der Posten 'beschr' mit 3,08 ms
fuers Zeichnen. Zusammen rund ein Fuenftel des Schritts fuer einen
Text, den beim Durchfliegen niemand liest.

DASSELBE MUSTER WIE BEI DEN COVERN (Build 244): was waehrend der
Navigation zu teuer ist, wird uebersprungen und nach dem Loslassen
nachgeholt. Derselbe Schalter (ART._defer_uncached), derselbe
Nachlader (ART._deferred_something) - KEIN zweiter Mechanismus fuer
dieselbe Frage.

WAS DIESER TEST SICHERT:
  1. bei aktiver Navigation wird die Beschreibung NICHT gezeichnet,
  2. im Stillstand schon,
  3. das Auslassen meldet sich beim Nachlader - sonst sieht der
     Nutzer die Beschreibung erst beim naechsten Tastendruck,
  4. und der Restore der Textspalte schrumpft dadurch wirklich.

Punkt 4 ist der eigentliche Gewinn und nicht Punkt 1: das Zeichnen
allein waere 3 ms, der kleinere Restore bringt mehr.

Ausfuehren:
    python3 tools/test_beschreibung_zurueck.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H          # noqa: E402

import fe.art as A            # noqa: E402,F401
from _quelle import koerper, nur_code                     # noqa: E402

# DER MERKER SITZT AUF DER INSTANZ, NICHT AUF DEM MODUL.
#
# frontend.py hat ART = ArtCache(), und _defer_uncached wie
# _deferred_something sind Felder dieser Instanz (siehe __init__ in
# fe/art.py). "import fe.art as A" liefert das MODUL - A._defer_uncached
# ist also ein anderes Objekt als ART._defer_uncached.
#
# Genau dieser Verwechslung ist Build 294 schon einmal aufgesessen
# (dort stand ART.docs_bildart(), und das waere auf dem Geraet ein
# AttributeError gewesen). Die erste Fassung dieses Tests hat sie
# wiederholt: die Pruefung auf den Nachlader schlug an, obwohl der Code
# ihn setzt - nur eben an der Instanz.
ART = H.fm.ART


def navigiert(fe, ja):
    """Den Zustand "es wird gerade gescrollt" HERSTELLEN, nicht setzen.

    ART._defer_uncached von Hand zu setzen bringt hier nichts, und das
    ist kein Mangel des Tests, sondern eine Eigenschaft des Codes:
    draw_page_items() ruft _sync_cover_defer(), und das rechnet den
    Wert JEDES MAL neu aus self._last_input_time (Begruendung im
    Docstring dort - der Wert wurde vorher an einer Stelle gesetzt und
    war beim Zeichnen veraltet). Eine einzige Quelle also, und der
    Test muss sie bedienen statt sie zu umgehen.

    Genau an dieser Stelle hat die erste Fassung dieses Tests
    angeschlagen - zu Recht."""
    jetzt = H.NOW[0]
    fe._last_input_time = jetzt if ja else jetzt - 10.0

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

fails = []


def check(name, ok, info=""):
    if ok:
        print("  OK   %s %s" % (name, info))
    else:
        print("  FEHL %s %s" % (name, info))
        fails.append(name)


print(__doc__.strip().split("\n")[0])
print()

# ---------------------------------------------------------------------------
print("Test 1: gezeichnet wird sie nur im Stillstand")
# ---------------------------------------------------------------------------
H.set_screen(1920, 1080)
fe = H.make_frontend()
fe.page = 1
# Eine Kategorie mit genug Eintraegen suchen - ohne Eintraege gibt es
# keine Galerie, und dann prueefte der Test nichts.
kat = None
for i, c in enumerate(fe.cats):
    try:
        fe.cat_i = i
        fe.nav_path = []
        if len(fe._display_items()) >= 5:
            kat = i
            break
    except Exception:                                    # noqa: BLE001
        continue


def navigiert(ja):
    """Den Zustand "es wird gerade gescrollt" HERSTELLEN.

    ART._defer_uncached von Hand zu setzen bringt nichts, und das ist
    kein Mangel des Tests, sondern eine Eigenschaft des Codes:
    draw_page_items() ruft _sync_cover_defer(), und das rechnet den
    Wert JEDES MAL neu aus self._last_input_time (die Begruendung steht
    im Docstring dort - der Wert wurde frueher an einer Stelle gesetzt
    und war beim Zeichnen veraltet). Eine einzige Quelle also, und der
    Test bedient sie statt sie zu umgehen."""
    fe._last_input_time = H.NOW[0] if ja else H.NOW[0] - 10.0


if kat is None:
    print("  -- uebersprungen: keine Kategorie mit genug Eintraegen")
else:
    fe.cat_i = kat
    fe.ansicht_setzen("galerie")
    n = max(1, len(fe._display_items()))

    # EINE BESCHREIBUNG WIRD GESETZT, NICHT ERHOFFT.
    #
    # Der Pruefstand hat keine Spieldaten, also liefert
    # _beschreibung_zeichnen() dort nichts und es gaebe nichts zu
    # beobachten. Die erste Fassung dieses Tests hat das uebersehen und
    # stattdessen zwei Spiele mit verschieden vielen Infozeilen
    # verglichen - herausgekommen waren "12 % weniger", und das war
    # Rauschen, kein Befund. Also hier eine Attrappe mit festem
    # Unterrand: so ist der Unterschied zwischen "Beschreibung da" und
    # "Beschreibung weg" eindeutig und haengt an keinen Metadaten.
    UNTEN = [0]
    rufe = []
    echt_beschr = fe._beschreibung_zeichnen

    def _beschr_attrappe(tx, oben, unten, breite, item, syskey, s):
        rufe.append(1)
        UNTEN[0] = unten - 2 * s
        return UNTEN[0]

    hoehen = []
    echt_restore = fe._restore_row_bg

    def _restore_haken(x, y, w, h, _e=echt_restore):
        hoehen.append((x, y, w, h))
        return _e(x, y, w, h)

    fe._beschreibung_zeichnen = _beschr_attrappe
    fe._restore_row_bg = _restore_haken
    try:
        # ---- Stillstand: gezeichnet ----------------------------------
        navigiert(False)
        del rufe[:]
        fe.item_i = (fe.item_i + 1) % n
        fe.draw_page_items()
        check("im Stillstand wird sie gezeichnet", len(rufe) >= 1,
              "%d Aufrufe" % len(rufe))
        _unten_mit = getattr(fe, "_galerie_text_unten", None)
        check("und die Textspalte reicht bis zu ihrem Unterrand",
              _unten_mit == UNTEN[0],
              "%r gegen %r" % (_unten_mit, UNTEN[0]))

        # ---- Navigation: ausgelassen ---------------------------------
        navigiert(True)
        ART._deferred_something = False
        del rufe[:]
        fe.item_i = (fe.item_i + 1) % n
        fe.draw_page_items()
        check("bei aktiver Navigation nicht", len(rufe) == 0,
              "%d Aufrufe - jeder kostet laut Bericht 3,08 ms"
              % len(rufe))
        check("und der Nachlader wird angefordert",
              getattr(ART, "_deferred_something", False) is True,
              "sonst erscheint sie erst beim naechsten Tastendruck")
        _unten_ohne = getattr(fe, "_galerie_text_unten", None)
        check("die Textspalte endet damit hoeher",
              _unten_ohne is not None and _unten_mit is not None
              and _unten_ohne < _unten_mit,
              "mit %r, ohne %r" % (_unten_mit, _unten_ohne))

        # ---- und der NAECHSTE Schritt raeumt weniger frei ------------
        # Das ist der eigentliche Gewinn: nicht die gesparten 3 ms
        # fuers Zeichnen, sondern der kleinere Restore. Oben wird nur
        # bis _galerie_text_unten freigeraeumt.
        print()
        print("Test 2: der Restore der Textspalte schrumpft dadurch")
        navigiert(True)
        del hoehen[:]
        fe.item_i = (fe.item_i + 1) % n
        fe.draw_page_items()
        punkte_ohne = sum(w * h for (_x, _y, w, h) in hoehen)

        # Gegenprobe: dieselbe Stelle MIT Beschreibung im vorigen
        # Schritt - dann steht der grosse Unterrand und der Restore
        # faellt entsprechend groesser aus.
        navigiert(False)
        fe.item_i = (fe.item_i + 1) % n
        fe.draw_page_items()            # zeichnet die Beschreibung
        navigiert(True)
        del hoehen[:]
        fe.item_i = (fe.item_i + 1) % n
        fe.draw_page_items()            # raeumt die GROSSE Spalte frei
        punkte_mit = sum(w * h for (_x, _y, w, h) in hoehen)

        check("der naechste Schritt raeumt weniger frei",
              punkte_ohne < punkte_mit,
              "%d gegen %d Punkte (%.0f %% weniger)"
              % (punkte_ohne, punkte_mit,
                 100.0 * (1 - punkte_ohne / float(punkte_mit or 1))))
        check("und es ist keine Kleinigkeit",
              punkte_mit - punkte_ohne > 50000,
              "%d Punkte Unterschied - bei 4 Byte je Punkt sind das "
              "%.2f MB je Schritt"
              % (punkte_mit - punkte_ohne,
                 (punkte_mit - punkte_ohne) * 4 / 1048576.0))
    finally:
        fe._beschreibung_zeichnen = echt_beschr
        fe._restore_row_bg = echt_restore
        navigiert(False)
        ART._deferred_something = False

# ---------------------------------------------------------------------------
print("Test 3: es ist DERSELBE Schalter wie bei den Covern")
# ---------------------------------------------------------------------------
# Ein zweiter Mechanismus fuer dieselbe Frage waere einer, der
# irgendwann anders antwortet. Geprueft wird deshalb, dass im
# Galerie-Zeichner genau die beiden bekannten Namen stehen - und kein
# eigener Merker daneben.
quelle = open(H.FRONTEND_PY, encoding="utf-8", errors="replace").read()
galerie = nur_code(koerper(quelle, "_draw_items_galerie"))
check("der Zeichner fragt ART._defer_uncached",
      "ART._defer_uncached" in galerie)
check("und meldet ART._deferred_something",
      "ART._deferred_something = True" in galerie)
check("die Beschreibung haengt wirklich an dieser Abfrage",
      "_beschreibung_zeichnen" in galerie
      and galerie.index("ART._defer_uncached")
      < galerie.index("_beschreibung_zeichnen"),
      "sonst wird erst gezeichnet und dann gefragt")

# ---------------------------------------------------------------------------
print()
print("Test 4: der Bench sieht es (Abschnitt L und die Nummer)")
# ---------------------------------------------------------------------------
import fe.bench as B                                      # noqa: E402
check("BENCH_VERSION ist mitgewachsen", B.BENCH_VERSION >= 15,
      "%d - ein neuer Abschnitt ohne neue Nummer macht zwei Berichte "
      "unvergleichbar" % B.BENCH_VERSION)
check("es gibt einen Abschnitt L", hasattr(B, "_abschnitt_l"))
_bq = nur_code(koerper(open(os.path.join(_REPO, "frontend", "fe",
                                         "bench.py"),
                            encoding="utf-8").read(), "_abschnitt_l"))
check("er misst das Fenster zwischen zwei Blicken",
      "read_action" in _bq,
      "ohne diese Zahl ist jeder Eingriff am Eingabeweg geraten")
check("und stellt read_action danach zurueck",
      "inp.read_action = echt_read" in _bq,
      "ein Messgeraet, das etwas stehen laesst, ist kaputt")
check("die Schattenstufen sind begrenzt",
      __import__("fe.framebuffer", fromlist=["x"]
                 ).Framebuffer.KARTE_SCHATTEN_STUFEN_MAX <= 4,
      "jede Stufe ist ein voller Schatten-Aufruf beim Bau der Vorlage")

print()
if fails:
    print("FEHLGESCHLAGEN (%d):" % len(fails))
    for f in fails:
        print("  - %s" % f)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
