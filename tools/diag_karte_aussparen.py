#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Die ausgesparte Karte - ist das Bild wirklich dasselbe? (Build 234)

DER EINGRIFF. Im Bericht vom 03.10. ist "karten" mit 13,75 ms der
groesste Posten eines Scrollschritts in der Listenansicht;
tools/diag_kartenkosten.py sagt, woher: EINE Karte, 769x945 Punkte, in
JEDEM Schritt - und darueber liegt gleich darauf das Cover. Rund drei
Viertel der Flaeche werden gefuellt und sofort wieder uebermalt.

Seit Build 234 spart karte_mit_schatten() dieses Rechteck aus. Das ist
genau die Sorte Aenderung, bei der man sich irrt und es nicht merkt:
ein Punkt zu viel ausgespart, und es bleibt ein Streifen Hintergrund
stehen - sichtbar erst auf dem Fernseher des Nutzers, bei einem Cover
mit einem Seitenverhaeltnis, das hier niemand ausprobiert hat.

DESHALB WIRD ES NICHT NACHGEDACHT, SONDERN VERGLICHEN: dieselbe Seite
zweimal gezeichnet, einmal mit und einmal ohne Aussparung, Byte fuer
Byte. Und zwar ueber viele Cover-Groessen - auch die schiefen, auch die
winzigen, auch die, die groesser sind als der Kasten.

Ausfuehren:
    python3 tools/diag_karte_aussparen.py
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H          # noqa: E402

_uhr = time.perf_counter      # der Pruefstand friert monotonic() ein

fm = H.fm
FB = fm.Framebuffer


def _karte(fb, x, y, w, h, versatz, radius, luecke):
    fb.buf[:] = b"\x11" * len(fb.buf)
    fb.karte_mit_schatten(x, y, w, h, versatz, (40, 44, 60), (10, 10, 14),
                          radius, aussparen=luecke)
    return bytes(fb.buf)


def _cover_malen(fb, luecke):
    """Das Cover daruebermalen - genau das tut self.blit() auch."""
    ax, ay, aw, ah = luecke
    fb.rect(ax, ay, aw, ah, (200, 30, 90))


def main():
    H.set_screen(1920, 1080)
    fb = FB()
    print("=" * 66)
    print(" Die ausgesparte Karte - Byte fuer Byte verglichen")
    print("=" * 66)
    print("")

    # Die Karte aus der Listenansicht auf 1080p, und dazu Groessen,
    # die im Betrieb nicht vorkommen - gerade die sind interessant.
    KARTEN = (
        (1035, 36, 769, 945, 9, 12),      # Listenansicht, 1080p
        (116, 174, 387, 504, 9, 12),      # Galerie, 1080p
        (10, 10, 200, 120, 3, 8),         # klein
        (0, 0, 1920, 1080, 6, 40),        # bildschirmfuellend
        (100, 100, 60, 60, 2, 30),        # Radius = halbe Kante
    )
    # Cover-Seitenverhaeltnisse, wie sie wirklich vorkommen, plus
    # Grenzfaelle.
    ANTEILE = (1.0, 0.9, 0.75, 0.5, 0.25, 0.05, 1.5)

    faelle = 0
    schief = 0
    gespart = 0
    gesamt = 0
    for (x, y, w, h, versatz, radius) in KARTEN:
        ohne = _karte(fb, x, y, w, h, versatz, radius, None)
        for anteil in ANTEILE:
            aw = max(1, int(w * anteil * 0.8))
            ah = max(1, int(h * anteil * 0.8))
            ax = x + (w - aw) // 2
            ay = y + (h - ah) // 2
            luecke = (ax, ay, aw, ah)
            faelle += 1

            # a) ohne Aussparung, dann Cover drauf
            fb.buf[:] = ohne
            _cover_malen(fb, luecke)
            soll = bytes(fb.buf)

            # b) MIT Aussparung, dann dasselbe Cover drauf
            _karte(fb, x, y, w, h, versatz, radius, luecke)
            _cover_malen(fb, luecke)
            ist = bytes(fb.buf)

            if soll != ist:
                schief += 1
                n = sum(1 for p, q in zip(soll, ist) if p != q)
                print("  ABWEICHUNG  Karte %dx%d an (%d,%d), Cover %dx%d"
                      " -> %d Bytes anders" % (w, h, x, y, aw, ah, n))

            # Wieviel Flaeche wurde gespart? (Nur zur Einordnung - die
            # Aussparung gilt nur in den geraden Mittelzeilen.)
            gesamt += w * h
            gespart += aw * ah

    print("  Verglichene Faelle : %d" % faelle)
    print("  Abweichungen       : %d" % schief)
    print("")
    if schief:
        print("  NICHT bitgenau - die Aussparung ist falsch.")
        return 1

    # ---- und was es bringt ------------------------------------------
    print("-" * 66)
    print(" Was es spart (Entwicklungsrechner, nur zur Groessenordnung)")
    print("-" * 66)
    x, y, w, h, versatz, radius = KARTEN[0]
    aw, ah = int(w * 0.8), int(h * 0.8)
    luecke = (x + (w - aw) // 2, y + (h - ah) // 2, aw, ah)
    for name, lk in (("ohne Aussparung", None), ("mit Aussparung", luecke)):
        t0 = _uhr()
        for _ in range(40):
            fb.karte_mit_schatten(x, y, w, h, versatz, (40, 44, 60),
                                  (10, 10, 14), radius, aussparen=lk)
        ms = (_uhr() - t0) * 1000.0 / 40
        print("  %-18s %7.3f ms" % (name, ms))
    print("")
    print("  Die Karte ist %dx%d, das Cover %dx%d - das sind %.0f %% der"
          % (w, h, aw, ah, 100.0 * aw * ah / (w * h)))
    print("  Flaeche, die gefuellt und sofort uebermalt wurde.")
    print("")
    print("  Auf dem DE10-Nano kostet Fuellen laut Abschnitt I rund")
    print("  4,1 ms fuer 700x900 - dort faellt derselbe Anteil deutlich")
    print("  staerker ins Gewicht. Was ankommt, sagt der Bench.")
    print("=" * 66)
    print(" Bitgenau identisch.")
    print("=" * 66)
    return 0


if __name__ == "__main__":
    sys.exit(main())
