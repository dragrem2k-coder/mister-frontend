#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Woraus bestehen "restore" und "flip"? (Build 237)

DER ANLASS steht im Geraetebericht vom 03.10.: in der Galerie der
Hauptseite ist "restore" mit 12,99 ms der groesste Einzelposten des
ganzen Berichts (5 Aufrufe ueber 1595 Zeilen), und "flip" liegt in
zwei Ansichten bei rund 10 ms (3,5 bis 3,9 MB).

Abschnitt J nennt die SUMME und die Zahl der Zeilen. WELCHE Flaeche
das ist, sagt er nicht - und ohne das waere jede Aenderung geraten.
Genau dieselbe Luecke gab es bei "karten", und diag_kartenkosten.py
hat sie geschlossen: eine Karte, 769x945, in jedem Schritt.

DIE FRAGE, UM DIE ES GEHT, ist dieselbe wie damals: wie viel von dem,
was freigeraeumt wird, wird gleich darauf ohnehin uebermalt? Und wie
viel von dem, was geflippt wird, hat sich ueberhaupt geaendert?

Die zweite Frage beantwortet dieses Werkzeug mit: es vergleicht den
Puffer vor und nach dem Schritt und sagt, welcher Anteil der
geflippten Flaeche sich wirklich unterscheidet.

Ausfuehren:
    python3 tools/diag_restore_flip.py
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H          # noqa: E402

import fe.bench as BENCH      # noqa: E402
import fe.settings as S       # noqa: E402

_uhr = time.perf_counter      # der Pruefstand friert monotonic() ein

SCHRITTE = 12


def _mb(n):
    return n / 1048576.0


def main():
    H.set_screen(1920, 1080)
    fe = H.make_frontend(page=1)
    fb = fe.fb
    K = type(fe)

    print("=" * 70)
    print(" Woraus bestehen 'restore' und 'flip'? - %dx%d, %d Schritte"
          % (fb.width, fb.height, SCHRITTE))
    print("=" * 70)
    print(" 'geaendert' ist der Anteil der geflippten Bytes, der sich")
    print(" zwischen zwei Schritten wirklich unterscheidet. Alles")
    print(" darunter ist Flaeche, die umsonst in den Bildspeicher geht.")
    print("")

    echt_restore = K._restore_row_bg
    echt_bgfill = K._bg_fill
    echt_rect = fb.flip_rechtecke
    echt_rows = fb.flip_rows
    echt_voll = fb.flip

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
            flip = {"n": 0, "bytes": 0, "ms": 0.0, "anders": 0,
                    "rechtecke": 0}
            vorher = [None]

            def _haken(name, original, selbst=True):
                def _ersatz(self_or_x, *a, **k):
                    if selbst:
                        x, y, w, h = (self_or_x,) + a[:3]
                    else:
                        x, y, w, h = self_or_x, a[0], a[1], a[2]
                    t0 = _uhr()
                    try:
                        return original(self_or_x, *a, **k)
                    finally:
                        ms = (_uhr() - t0) * 1000.0
                        e = konto.setdefault(
                            (name, int(x), int(y), int(w), int(h)),
                            [0, 0.0])
                        e[0] += 1
                        e[1] += ms
                return _ersatz

            def _r(selbst, x, y, w, h):
                t0 = _uhr()
                try:
                    return echt_restore(selbst, x, y, w, h)
                finally:
                    ms = (_uhr() - t0) * 1000.0
                    e = konto.setdefault(("restore", int(x), int(y),
                                          int(w), int(h)), [0, 0.0])
                    e[0] += 1
                    e[1] += ms

            def _b(selbst, x, y, w, h):
                t0 = _uhr()
                try:
                    return echt_bgfill(selbst, x, y, w, h)
                finally:
                    ms = (_uhr() - t0) * 1000.0
                    e = konto.setdefault(("bg_fill", int(x), int(y),
                                          int(w), int(h)), [0, 0.0])
                    e[0] += 1
                    e[1] += ms

            def _fr(rechtecke, *a, **k):
                rl = list(rechtecke)
                by = sum(w * h * 4 for (_x, _y, w, h) in rl)
                # Wieviel davon hat sich wirklich geaendert?
                anders = 0
                if vorher[0] is not None:
                    alt = vorher[0]
                    neu = fb.buf
                    for (x, y, w, h) in rl:
                        need = w * 4
                        for yy in range(y, y + h):
                            off = yy * fb.stride + x * 4
                            if alt[off:off + need] != neu[off:off + need]:
                                anders += need
                t0 = _uhr()
                try:
                    return echt_rect(rl, *a, **k)
                finally:
                    flip["ms"] += (_uhr() - t0) * 1000.0
                    flip["n"] += 1
                    flip["bytes"] += by
                    flip["anders"] += anders
                    flip["rechtecke"] += len(rl)

            def _fv(*a, **k):
                t0 = _uhr()
                try:
                    return echt_voll(*a, **k)
                finally:
                    flip["ms"] += (_uhr() - t0) * 1000.0
                    flip["n"] += 1
                    flip["bytes"] += len(fb.buf)
                    flip["rechtecke"] += 1

            K._restore_row_bg = _r
            K._bg_fill = _b
            fb.flip_rechtecke = _fr
            fb.flip = _fv
            try:
                t0 = _uhr()
                for i in range(SCHRITTE):
                    vorher[0] = bytes(fb.buf)
                    schritt(i % spanne)
                ges = (_uhr() - t0) * 1000.0 / SCHRITTE
            finally:
                K._restore_row_bg = echt_restore
                K._bg_fill = echt_bgfill
                fb.flip_rechtecke = echt_rect
                fb.flip_rows = echt_rows
                fb.flip = echt_voll

            summe = sum(e[1] for e in konto.values()) / SCHRITTE
            zeilen = sum(int(k[4]) * e[0] for k, e in konto.items())
            print("  %-16s Schritt %6.2f ms" % (sname + " " + ansicht, ges))
            print("     restore %5.2f ms in %d Aufrufen, %d Zeilen je Schritt"
                  % (summe, sum(e[0] for e in konto.values()) // SCHRITTE,
                     zeilen // SCHRITTE))
            posten = sorted(konto.items(), key=lambda e: -e[1][1])
            for (name, x, y, w, h), (n, ms) in posten[:4]:
                print("        %-9s %5dx%-5d an (%4d,%4d)  %6.3f ms  %s"
                      % (name, w, h, x, y, ms / SCHRITTE,
                         "JEDEN Schritt" if n >= SCHRITTE else "%dx" % n))
            if flip["n"]:
                anteil = (100.0 * flip["anders"] / flip["bytes"]
                          if flip["bytes"] else 0.0)
                print("     flip    %5.2f ms, %.2f MB in %.1f Rechtecken"
                      "  -> geaendert: %.0f %%"
                      % (flip["ms"] / SCHRITTE,
                         _mb(flip["bytes"]) / SCHRITTE,
                         float(flip["rechtecke"]) / SCHRITTE, anteil))
            print("")

    print("=" * 70)
    print(" Zu lesen als: steht bei 'geaendert' deutlich weniger als")
    print(" 100 Prozent, geht Flaeche umsonst in den Bildspeicher - und")
    print(" der Bildspeicher ist laut Abschnitt H das Teuerste, was es")
    print(" hier gibt. Bei 'restore' gilt dasselbe wie bei den Karten:")
    print(" was gleich darauf uebermalt wird, muss nicht freigeraeumt")
    print(" werden.")
    print("=" * 70)


if __name__ == "__main__":
    main()
