#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft den einstellbaren Bildrand (Build 113).

UEBERNOMMEN VON DEGAUSS - dort laesst sich Randbreite und Bildlage im
Menue einstellen. Bei uns standen die beiden Werte als feste Zahlen im
Quelltext (OVERSCAN_X = 7, OVERSCAN_Y = 5). Auf HDMI ist das
unkritisch; auf einer Roehre nicht - jede sitzt anders, manche
schneiden rechts mehr ab als links, und wer das korrigieren wollte,
musste bisher Python editieren.

WORAUF ES BEI DIESER AENDERUNG ANKOMMT: die beiden Werte werden an
SECHSUNDZWANZIG Stellen als "W * OVERSCAN_X // 100" gelesen. Sie alle
auf ein Objektfeld umzustellen waeren sechsundzwanzig Gelegenheiten,
ein Layout zu verschieben. Stattdessen werden die Modul-Variablen
ueberschrieben - das erreicht dasselbe, ohne eine einzige dieser
Zeilen anzufassen. Dieser Test weist nach, dass das auch wirklich
ueberall ankommt und nicht nur an der einen Stelle, die man zufaellig
prueft.

Ausfuehren:
    python3 tools/test_bildrand.py
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
import fe.settings as S                                 # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


TMP = tempfile.mkdtemp(prefix="bildrand_")
S.OVERSCAN_FILE = os.path.join(TMP, "overscan")

print("Test 1: ohne gespeicherten Wert gelten die bisherigen Vorgaben")
# Das ist die wichtigste Zusage der Aenderung: wer nichts einstellt,
# bekommt exakt das Bild von vorher.
check("Vorgabe ist 7/5", S.overscan_lesen() == (7, 5),
      "(%r)" % (S.overscan_lesen(),))
check("und das sind dieselben Zahlen wie frueher im Quelltext",
      (S.OVERSCAN_X_STD, S.OVERSCAN_Y_STD) == (7, 5))

print("Test 2: speichern und wieder lesen")
S.overscan_schreiben(3, 9)
check("3/9 kommt zurueck", S.overscan_lesen() == (3, 9),
      "(%r)" % (S.overscan_lesen(),))

print("Test 3: eine von Hand verstellte Datei macht das Bild nicht kaputt")
# Ein Rand von 40 % liesse praktisch nichts uebrig - dann lieber die
# Vorgabe als ein unbedienbares Menue.
for inhalt, warum in (("40,40", "zu gross"), ("-5,3", "negativ"),
                      ("kaputt", "kein Zahlenpaar"), ("7", "unvollstaendig"),
                      ("", "leer")):
    with open(S.OVERSCAN_FILE, "w") as fh:
        fh.write(inhalt)
    check("%-14s -> Vorgabe" % warum, S.overscan_lesen() == (7, 5),
          "(%r bei %r)" % (S.overscan_lesen(), inhalt))

print("Test 4: Weiterschalten laeuft durch die Stufen und dreht um")
S.overscan_schreiben(0, 0)
gesehen = []
for _ in range(len(S.OVERSCAN_STUFEN) + 1):
    x, _y = S.overscan_weiter("x")
    gesehen.append(x)
check("alle Stufen kommen vor",
      set(gesehen) == set(S.OVERSCAN_STUFEN),
      "(%r)" % (gesehen,))
check("nach der letzten Stufe geht es von vorn los",
      gesehen[-1] == gesehen[0], "(%r ... %r)" % (gesehen[0], gesehen[-1]))
S.overscan_schreiben(4, 4)
_x, y = S.overscan_weiter("y")
check("y aendert sich, x bleibt", (S.overscan_lesen()[0], y) == (4, 5),
      "(%r)" % (S.overscan_lesen(),))

print("Test 5: der Wert kommt WIRKLICH im Layout an - an allen Stellen")
# Der eigentliche Sinn des Tests. Geprueft wird nicht die Einstellung,
# sondern das Bild: bei doppeltem Rand muss der Inhalt schmaler werden,
# und zwar auf BEIDEN Seiten.
for w, h, name in ((320, 240, "CRT"), (1920, 1080, "HDMI")):
    messungen = {}
    for rand in (2, 10):
        S.overscan_schreiben(rand, rand)
        H.set_screen(w, h)
        f = H.make_frontend(page=0)
        f._overscan_anwenden()
        f._layout_items_cache.clear()
        Lc = f.layout_cats()
        Li = f.layout_items(True)
        messungen[rand] = (Lc["ox"], Lc["oy"], Li["ox"], Li["list_right"])
    (ox2, oy2, iox2, ir2) = messungen[2]
    (ox10, oy10, iox10, ir10) = messungen[10]
    check("%s: Hauptseite-Rand waechst mit der Einstellung" % name,
          ox10 > ox2 and oy10 > oy2,
          "(2%%: %d/%d, 10%%: %d/%d)" % (ox2, oy2, ox10, oy10))
    check("%s: Rand ist genau die eingestellten Prozent" % name,
          ox10 == w * 10 // 100 and oy10 == h * 10 // 100,
          "(%d/%d erwartet %d/%d)" % (ox10, oy10, w * 10 // 100, h * 10 // 100))
    check("%s: auch die Spieleliste rueckt mit" % name,
          iox10 > iox2 and ir10 < ir2,
          "(links %d->%d, rechts %d->%d)" % (iox2, iox10, ir2, ir10))

print("Test 6: der Menuepunkt ist da und laeuft ueber denselben Weg")
quelle = open(os.path.join(_REPO, "frontend", "frontend.py"),
              encoding="utf-8", errors="replace").read()
menue = open(os.path.join(_REPO, "frontend", "fe", "menu.py"),
             encoding="utf-8", errors="replace").read()
check("zwei Menuepunkte unter Anzeige & Sound",
      '"overscan_x"' in menue and '"overscan_y"' in menue)
check("die Beschriftung zeigt den aktuellen Wert",
      't("sys_overscan_x", _ovx)' in menue)
check("der Schalter wird verarbeitet",
      'kind in ("overscan_x", "overscan_y")' in quelle)
check("beim Start werden die gespeicherten Werte angewendet",
      "self._overscan_anwenden()" in quelle)
# Ohne das Leeren bliebe die alte Aufteilung stehen und die Einstellung
# waere sichtbar wirkungslos - genau die Sorte Fehler, die man erst
# beim Ausprobieren auf dem Geraet merkt.
check("der Layout-Zwischenspeicher wird geleert",
      "self._layout_items_cache.clear()" in quelle)
check("und ein voller Neuaufbau erzwungen",
      "self.fb.mark_full_redraw()\n                            "
      "self._force_full_redraw = True" in quelle)

print("Test 7: beide Sprachen vorhanden")
import fe.translations as T                             # noqa: E402
for key in ("sys_overscan_x", "sys_overscan_y"):
    eintrag = T.TRANSLATIONS.get(key, {})
    check("%s hat deutsch und englisch" % key,
          bool(eintrag.get("de")) and bool(eintrag.get("en")))
    check("%s nennt einen Platzhalter fuer den Wert" % key,
          "%d" in eintrag.get("de", "") and "%d" in eintrag.get("en", ""))

shutil.rmtree(TMP, ignore_errors=True)

print()
if fails:
    print("FEHLGESCHLAGEN (%d):" % len(fails))
    for f_ in fails:
        print("  -", f_)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
