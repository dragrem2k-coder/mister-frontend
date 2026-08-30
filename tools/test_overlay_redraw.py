#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft, dass eine eingeblendete Hinweisbox RESTLOS verschwindet.

Hintergrund (Nutzer-Rueckmeldung): "wenn ich von HDMI auf CRT umschalte
kommt das Popup mit der Info 'CRT aktiv' - sobald ich dann den Cursor
bewege, verschwindet die Infobox nicht ganz und ist teilweise noch zu
sehen."

Ursache war der schnelle Zeichenpfad: er baut den Hintergrund ausserhalb
der Listenspalte NICHT neu auf und liess deshalb den Teil der Box
stehen, der ueber die Liste hinausragte.

Der Test vergleicht BITGENAU mit einer Referenzinstanz, die dieselbe
Position ohne jemals eingeblendete Box zeichnet: bleibt auch nur ein
Pixel der Box uebrig, schlaegt er fehl.

Ausfuehren:
    python3 tools/test_overlay_redraw.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H          # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


MSG = "CRT-Modus ist aktiv - bitte bestaetigen"

for w, h in ((320, 240), (1920, 1080)):
    lbl = "CRT" if w == 320 else "HDMI"
    print("--- %s %dx%d ---" % (lbl, w, h))
    H.set_screen(w, h)

    # Referenzbild: Position 1, nie eine Box gesehen
    ref = H.make_frontend(1)
    ref.item_i = 1
    ref.draw()
    want = bytes(ref.fb.buf)

    fe = H.make_frontend(1)
    fe._prominent_message = MSG
    fe._prominent_message_until = H.NOW[0] + 30
    fe.item_i = 0
    fe.draw()
    check("%s: Box ist im Bild" % lbl, bytes(fe.fb.buf) != want)
    check("%s: _overlay_active() erkennt sie" % lbl, fe._overlay_active())

    old = fe.item_i
    fe.item_i = 1
    check("%s: leichter Pfad verweigert bei sichtbarer Box" % lbl,
          fe._draw_navigate_items(old) is False)

    # echter Ablauf: die Eingabe raeumt die Box ab, die Hauptschleife
    # zeichnet danach einmal voll
    fe._prominent_message = None
    fe._force_full_redraw = True
    check("%s: leichter Pfad verweigert einmalig danach" % lbl,
          fe._draw_navigate_items(0) is False)
    fe.draw()
    check("%s: KEIN Rest der Box mehr im Bild" % lbl,
          bytes(fe.fb.buf) == want)

    fe.item_i = 2
    check("%s: leichter Pfad danach wieder erlaubt" % lbl,
          fe._draw_navigate_items(1) is True)

    # zweiter Weg: die Box laeuft durch Zeitablauf aus (Leerlauf-Zweig)
    fe2 = H.make_frontend(1)
    fe2._prominent_message = MSG
    fe2._prominent_message_until = H.NOW[0] + 30
    fe2.item_i = 1
    fe2.draw()
    fe2._prominent_message = None
    fe2.draw()
    check("%s: auch nach Zeitablauf kein Rest" % lbl,
          bytes(fe2.fb.buf) == want)
    print()

if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for f in fails:
        print("   ", f)
    sys.exit(1)
print("Alle Tests bestanden.")
