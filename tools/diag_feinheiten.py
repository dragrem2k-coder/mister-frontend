#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Was kosten die Feinheiten? (Build 236)

DIE BEDINGUNG DES NUTZERS war eindeutig: "alles aber nur wenn absolut
keine Performance Verluste merkbar sind". Also wird nicht geschaetzt,
sondern gemessen - und zwar jedes Element EINZELN, an und aus.

DREI ELEMENTE, und sie kosten aus verschiedenen Gruenden verschieden
viel:

  Scrollbalken   zwei Rechtecke, aber nur beim SEITENAUFBAU - er haengt
                 am Fenster (scroll), nicht am Zeiger (item_i). Im
                 leichten Navigationsschritt aendert sich das Fenster
                 per Definition nicht.
  Haarlinie      ein Rechteck, ebenfalls nur beim Seitenaufbau.
  Akzentbalken   ein Rechteck JE ZEILE - im leichten Pfad also zwei je
                 Schritt (alte und neue Zeile), beim vollen Aufbau so
                 viele wie sichtbare Zeilen. Das ist das einzige
                 Element, das im Scrollschritt ueberhaupt vorkommt.

Gemessen wird beides: der leichte Schritt (das, was beim Gedrueckt-
halten ankommt) und der volle Aufbau.

Ausfuehren:
    python3 tools/diag_feinheiten.py
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H          # noqa: E402

import fe.bench as BENCH      # noqa: E402
import fe.settings as S       # noqa: E402

# Der Pruefstand friert time.monotonic() ein - zum Messen taugt eine
# stehende Uhr nicht.
_uhr = time.perf_counter

SCHRITTE = 60
RUNDEN = 9


def _median(werte):
    w = sorted(werte)
    return w[len(w) // 2]


def _messen(fe, fm, seite, an):
    """Einen Scrollschritt messen - mit oder ohne Feinheiten."""
    fm.FEIN = an
    schritt = BENCH.schritt_funktion(fe, seite)
    spanne = BENCH.fenster_spanne(fe, seite)
    for i in range(SCHRITTE):            # warmlaufen
        schritt(i % spanne)
    laeufe = []
    for _ in range(RUNDEN):
        t0 = _uhr()
        for i in range(SCHRITTE):
            schritt(i % spanne)
        laeufe.append((_uhr() - t0) * 1000.0 / SCHRITTE)
    return _median(laeufe)


def _voll_messen(fe, fm, an):
    """Einen vollen Seitenaufbau messen."""
    fm.FEIN = an
    for _ in range(3):
        fe._force_full_redraw = True
        fe.draw()
    laeufe = []
    for _ in range(RUNDEN):
        t0 = _uhr()
        for _ in range(8):
            fe._force_full_redraw = True
            fe.draw()
        laeufe.append((_uhr() - t0) * 1000.0 / 8)
    return _median(laeufe)


def main():
    H.set_screen(1920, 1080)
    fe = H.make_frontend(page=1)
    fm = H.fm
    print("=" * 66)
    print(" Was kosten die Feinheiten? - %dx%d, %d Schritte, %d Runden"
          % (fe.fb.width, fe.fb.height, SCHRITTE, RUNDEN))
    print("=" * 66)
    print(" Genommen wird der MITTLERE Lauf, nicht der beste und nicht")
    print(" der Mittelwert - ein einzelner Ausreisser soll das Ergebnis")
    print(" weder schoenen noch verderben.")
    print("")

    alt = getattr(fm, "FEIN", True)
    kat_i, kat_n, kat_name = BENCH._groesste_kategorie(fe)
    try:
        print(" DER SCROLLSCHRITT (das, was beim Gedruecktthalten ankommt)")
        print(" %-22s %10s %10s %12s" % ("", "ohne", "mit", "Unterschied"))
        for seite, sname in ((0, "Haupt"), (1, "Liste")):
            fe.page = seite
            if seite == 1:
                if kat_i is None:
                    continue
                fe.cat_i = kat_i
                fe.nav_path = []
            for ansicht in S.ANSICHTEN:
                try:
                    if seite == 0:
                        fe.ansicht_haupt_setzen(ansicht)
                    else:
                        fe.ansicht_setzen(ansicht)
                except Exception:                        # noqa: BLE001
                    continue
                try:
                    # ABWECHSELND messen, nicht erst alles ohne und dann
                    # alles mit: sonst traegt jede Haelfte den Zustand
                    # des Rechners in genau diesem Moment, und der
                    # Unterschied misst den Zustand statt des Elements.
                    # Beim ersten Entwurf stand hier deshalb -32 % fuer
                    # ein Element, das in dieser Ansicht gar nicht
                    # gezeichnet wird.
                    ohne_l, mit_l = [], []
                    for _r in range(3):
                        ohne_l.append(_messen(fe, fm, seite, False))
                        mit_l.append(_messen(fe, fm, seite, True))
                    ohne, mit = _median(ohne_l), _median(mit_l)
                except Exception as e:                   # noqa: BLE001
                    print("   %-20s -- uebersprungen (%s)"
                          % (sname + " " + ansicht, type(e).__name__))
                    continue
                d = mit - ohne
                print("   %-20s %7.3f ms %7.3f ms  %+7.3f ms  (%+.1f %%)"
                      % (sname + " " + ansicht, ohne, mit, d,
                         100.0 * d / max(0.001, ohne)))
        print("")
        print(" DER VOLLE SEITENAUFBAU (nach dem Stillstand, beim Wechsel)")
        fe.page = 1
        if kat_i is not None:
            fe.cat_i = kat_i
            fe.nav_path = []
        for ansicht in S.ANSICHTEN:
            try:
                fe.ansicht_setzen(ansicht)
                ohne = _voll_messen(fe, fm, False)
                mit = _voll_messen(fe, fm, True)
            except Exception as e:                       # noqa: BLE001
                print("   %-20s -- uebersprungen (%s)"
                      % ("Liste " + ansicht, type(e).__name__))
                continue
            d = mit - ohne
            print("   %-20s %7.3f ms %7.3f ms  %+7.3f ms  (%+.1f %%)"
                  % ("Liste " + ansicht, ohne, mit, d,
                     100.0 * d / max(0.001, ohne)))
    finally:
        fm.FEIN = alt

    print("")
    print("=" * 66)
    print(" Zu lesen als: der Scrollschritt ist das, was zaehlt. Steht")
    print(" dort ein Plus, das groesser ist als das Rauschen zwischen")
    print(" zwei Laeufen derselben Messung, fliegt das Element raus -")
    print(" so hat der Nutzer es verlangt. Auf dem DE10-Nano ist alles")
    print(" rund dreissigmal teurer; was hier 0,05 ms kostet, kostet")
    print(" dort rund 1,5 ms. Dort messen.")
    print("=" * 66)


if __name__ == "__main__":
    main()
