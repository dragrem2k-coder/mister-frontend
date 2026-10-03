#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Woraus besteht der Posten "karten"? (Build 234)

DER ANLASS steht im Geraetebericht vom 03.10.: in der Listenansicht der
Spieleliste ist "karten" mit 13,75 ms der GROESSTE Posten eines
Scrollschritts - bei nur 5 Aufrufen plus 4 inneren. Der Nutzer hat dazu
gesagt: "wenn noch was zu holen ist in der listenansicht das man mit
eingeschalteten cover scrollen es noch schneller laeuft waere das noch
echt gut".

Abschnitt J nennt die SUMME. Welche Karte davon wie viel kostet, sagt
er nicht - und ohne das waere jede Aenderung geraten. Dieses Werkzeug
haengt sich deshalb an die vier Zeichenfunktionen und schreibt je
Aufruf mit, WIE GROSS die Flaeche war und WIE LANGE sie gedauert hat.

DIE FRAGE, UM DIE ES GEHT: wie viele dieser Flaechen aendern sich beim
Scrollen ueberhaupt? Eine Karte, die bei jedem Schritt in derselben
Groesse an derselben Stelle in derselben Farbe neu gefuellt wird, ist
Arbeit fuer nichts - der Puffer steht hinterher so da wie vorher.
Gezaehlt wird das hier als "unveraendert".

Ausfuehren:
    python3 tools/diag_kartenkosten.py
"""
import os
import sys
import time

# DER PRUEFSTAND FRIERT time.monotonic() EIN (siehe tools/_harness.py) -
# alle Zeitvergleiche des Frontends laufen damit reproduzierbar. Zum
# MESSEN taugt eine stehende Uhr nicht; perf_counter() ist nicht
# gepatcht und ist ohnehin die genauere Wahl.
_uhr = time.perf_counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H          # noqa: E402

import fe.bench as BENCH      # noqa: E402
import fe.settings as S       # noqa: E402

SCHRITTE = 12

NAMEN = ("karte_mit_schatten", "rect_rounded_schatten", "rect_rounded",
         "rect")


def _haken(fb, konto):
    """Die vier Zeichenfunktionen mitschreiben lassen.

    Rueckgabe: eine Funktion, die alle Haken wieder loest."""
    echt = []
    tiefe = [0]

    def _bauen(name, original):
        def _ersatz(x, y, w, h, *a, **k):
            # Nur die AEUSSEREN Aufrufe zaehlen: karte_mit_schatten()
            # ruft rect_rounded(), und beides zu zaehlen zaehlte die
            # Zeit doppelt.
            if tiefe[0]:
                return original(x, y, w, h, *a, **k)
            tiefe[0] += 1
            t0 = _uhr()
            try:
                return original(x, y, w, h, *a, **k)
            finally:
                tiefe[0] -= 1
                ms = (_uhr() - t0) * 1000.0
                schl = (name, int(x), int(y), int(w), int(h))
                e = konto.setdefault(schl, [0, 0.0])
                e[0] += 1
                e[1] += ms
        return _ersatz

    for name in NAMEN:
        o = getattr(fb, name, None)
        if o is None:
            continue
        echt.append((name, o))
        setattr(fb, name, _bauen(name, o))

    def _loesen():
        for name, o in echt:
            setattr(fb, name, o)
    return _loesen


def main():
    H.set_screen(1920, 1080)
    fe = H.make_frontend(page=1)
    fb = fe.fb
    print("=" * 66)
    print(" Woraus besteht 'karten'? - %dx%d, %d Schritte je Ansicht"
          % (fb.width, fb.height, SCHRITTE))
    print("=" * 66)
    print(" Gemessen wird JE AUFRUF: Groesse, Zahl der Aufrufe, Zeit.")
    print(" 'je Schritt' ist die Zeit, die diese eine Flaeche in JEDEM")
    print(" Scrollschritt kostet - und genau dort lohnt das Hinsehen.")
    print("")

    kat_i, kat_n, kat_name = BENCH._groesste_kategorie(fe)
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
            except Exception:                            # noqa: BLE001
                continue
            schritt = BENCH.schritt_funktion(fe, seite)
            spanne = BENCH.fenster_spanne(fe, seite)
            try:
                for i in range(SCHRITTE):
                    schritt(i % spanne)
            except Exception as e:                       # noqa: BLE001
                print("  %s %s -- uebersprungen (%s)"
                      % (sname, ansicht, type(e).__name__))
                continue

            konto = {}
            loesen = _haken(fb, konto)
            try:
                t0 = _uhr()
                for i in range(SCHRITTE):
                    schritt(i % spanne)
                ges = (_uhr() - t0) * 1000.0 / SCHRITTE
            finally:
                loesen()

            summe = sum(e[1] for e in konto.values()) / SCHRITTE
            print("  %-14s  Schritt %6.2f ms, davon karten %6.2f ms"
                  % (sname + " " + ansicht, ges, summe))
            # Nach Kosten je Schritt sortiert - der groesste Posten
            # sagt, wo die naechste Arbeit liegt, und nur er.
            posten = sorted(konto.items(), key=lambda e: -e[1][1])
            for (name, x, y, w, h), (n, ms) in posten[:6]:
                je = ms / SCHRITTE
                immer = "JEDEN Schritt" if n >= SCHRITTE else "%dx" % n
                print("      %-22s %5dx%-5d an (%4d,%4d)  %6.2f ms  %s"
                      % (name, w, h, x, y, je, immer))
            if len(posten) > 6:
                rest = sum(e[1][1] for e in posten[6:]) / SCHRITTE
                print("      %-22s %38s %6.2f ms"
                      % ("... %d weitere" % (len(posten) - 6), "", rest))
            print("")

    print("=" * 66)
    print(" Zu lesen als: eine Flaeche, die in JEDEM Schritt in")
    print(" derselben Groesse an derselben Stelle neu gefuellt wird,")
    print(" ist ein Kandidat - der Puffer steht hinterher so da wie")
    print(" vorher. Ob sie wirklich unveraendert ist, sagt diese")
    print(" Messung NICHT; sie sagt nur, wo es sich lohnt nachzusehen.")
    print("=" * 66)


if __name__ == "__main__":
    main()
