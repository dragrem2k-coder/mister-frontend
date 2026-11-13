#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Wie oft baut ein Scrollschritt einen Zeiger nach C neu? (Build 319)

DAS WERKZEUG, DAS DEN BEFUND VON BUILD 319 GELIEFERT HAT.

Jeder Sprung nach libdragend braucht die Adresse des Puffers.
fe/art.py::_roh_zeiger() merkt sie sich - sechs Plaetze, und wenn der
siebte kommt, wird ALLES weggeworfen. Dieses Werkzeug haengt sich an
genau diese Funktion und zaehlt je Schritt:

    Zeiger    wie oft gefragt wurde
    Treffer   wie oft die Adresse schon da war
    NEU       wie oft sie neu gebaut werden musste
    bytes     Cover-Bilder (die gehen am Speicher vorbei)
    geleert   wie oft der Speicher ueberlief

VOR BUILD 319 (Obergrenze 6, vier Scheiben je Karte):

    Liste  liste       21,5   NEU  7,2   geleert 1,20
    Liste  galerie     27,1   NEU  7,5   geleert 1,25
    Haupt  kachelwand  29,0   NEU 13,5   geleert 2,25
    Liste  raster      15,0   NEU  0,0   geleert 0,00

Das Raster zeichnet keine Karte mit Schatten - und nur dort stand eine
Null. Seit Build 319 steht sie ueberall.

DIE ZAHLEN SIND GERAETEUNABHAENGIG. Es wird gezaehlt, nicht gestoppt;
auf dem DE10-Nano kommt dieselbe Tabelle heraus. Was dort ein neu
gebauter Zeiger KOSTET, sagt dieses Werkzeug nicht - das misst der
Bench (Abschnitt J: "Zeiger nach C", Abschnitt K: "im Kopierer
GEMESSEN").

DAS COVER WIRD UNTERGESCHOBEN, wie in Abschnitt K des Bench: ohne
Cover gibt es keine Aussparung, ohne Aussparung keine Scheiben, und
dann zaehlt man den Fall, den es am Geraet nicht gibt.

Ausfuehren:
    python3 tools/diag_zeiger.py
"""
import os
import sys
import time

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
sys.path.insert(0, _HIER)

if not os.environ.get("DRAGEND_LIB"):
    for _k in (os.path.join(_REPO, "frontend", "c", "libdragend_x86.so"),
               os.path.join(_REPO, "frontend", "libdragend_x86.so")):
        if os.path.exists(_k):
            os.environ["DRAGEND_LIB"] = _k
            break

_UHR = time.perf_counter

import _harness as H                                     # noqa: E402

import fe.art as A                                       # noqa: E402
import fe.bench as B                                     # noqa: E402
import fe.settings as S                                  # noqa: E402

SCHRITTE = 40


def main():
    H.set_screen(1920, 1080)
    f = H.make_frontend(page=0)
    # Eine Kategorie mit genug Eintraegen - der Pruefstand hat sonst
    # nur eine mit einem einzigen.
    _n, node, _sk = f.cats[0]
    node["items"] = [("Spiel Nummer %03d" % i, "game",
                      ("/f/%d.sfc" % i, ".sfc", "SNES", None, None))
                     for i in range(300)]
    node.pop("_display_items_cache", None)

    zaehler = [0]
    bilder = {}

    def _cover(quelle, breite, hoehe, **k):
        zaehler[0] += 1
        aw = max(8, int(breite) - (zaehler[0] % 3) * 7)
        ah = max(8, int(hoehe) - (zaehler[0] % 4) * 5)
        pix = bilder.get((aw, ah))
        if pix is None:
            pix = bytes(bytearray([40, 90, 160, 0])) * aw * ah
            bilder[(aw, ah)] = pix
        return (aw, ah, pix)

    echt_scaled = A.ART.get_scaled
    echt_zeiger = A._roh_zeiger
    st = {}

    def _haken(p):
        st["n"] += 1
        if isinstance(p, bytes):
            st["bytes"] += 1
            return echt_zeiger(p)
        e = A._ZEIGER.get(id(p))
        if e is not None and e[0] is p:
            st["treffer"] += 1
        return echt_zeiger(p)

    A.ART.get_scaled = _cover
    A._roh_zeiger = _haken
    try:
        print("%-6s %-11s %8s %8s %6s %6s %8s"
              % ("Seite", "Ansicht", "Zeiger", "Treffer", "NEU",
                 "bytes", "geleert"))
        for seite, name in ((0, "Haupt"), (1, "Liste")):
            f.page = seite
            if seite == 1:
                f.cat_i = 0
                f.nav_path = []
            for ansicht in B.ansichten_der_seite(S, seite):
                if B.ansicht_einstellen(f, seite, ansicht) != ansicht:
                    continue
                # Den Cover-Schutz abschalten - im Pruefstand steht
                # die Uhr, sonst waere er immer an.
                f._last_input_time = 0
                schritt = B.schritt_funktion(f, seite)
                for _r in range(2):
                    for i in range(10):
                        schritt(i)
                schritt(0)
                spanne = B.fenster_spanne(f, seite)
                for k in ("n", "treffer", "bytes"):
                    st[k] = 0
                vor = tuple(A.ZEIGER_STAND)
                for i in range(SCHRITTE):
                    schritt(i % spanne)
                nach = tuple(A.ZEIGER_STAND)
                je = float(SCHRITTE)
                print("%-6s %-11s %8.1f %8.1f %6.1f %6.1f %8.2f"
                      % (name, ansicht, st["n"] / je, st["treffer"] / je,
                         (nach[0] - vor[0]) / je, st["bytes"] / je,
                         (nach[1] - vor[1]) / je))
    finally:
        A.ART.get_scaled = echt_scaled
        A._roh_zeiger = echt_zeiger
    print()
    print("Obergrenze des Zeigerspeichers: %d, belegt: %d"
          % (A._ZEIGER_MAX, len(A._ZEIGER)))
    print("NEU und geleert muessen ueberall 0 sein. Die einzige")
    print("Ausnahme ist 'Haupt liste' MIT untergeschobenem Cover: dort")
    print("richtet sich die Karte nach der Bildgroesse, und dieses")
    print("Werkzeug wechselt sie mit Absicht bei jedem Schritt - es")
    print("entsteht also jedes Mal eine neue VORLAGE. Die echten")
    print("Abzeichen sind alle gleich gross (320x420).")


if __name__ == "__main__":
    main()
