#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Was kosten die abgerundeten Cover-Ecken? (Build 243)

DIE BEDINGUNG DES NUTZERS gilt seit Build 236 unveraendert: "alles aber
nur wenn absolut keine Performance Verluste merkbar sind". Also wird
nicht geschaetzt, sondern gemessen - und zwar abwechselnd, mit Median
und mit der Streuung daneben. Die Lehre dazu steht in
tools/diag_feinheiten.py (dort stand beim ersten Entwurf -32 % fuer ein
Element, das in der Ansicht gar nicht gezeichnet wird) und in Abschnitt
E des Bench (dort hat ein scharfes Urteil zwischen zwei Laeufen des
Nutzers die Richtung gewechselt).

WAS HIER ANDERS IST ALS IN diag_feinheiten.py: die Ecken werden nur
gestempelt, wenn ueberhaupt ein Cover da ist - und der Pruefstand hat
keine Cover-Dateien. Ohne untergeschobenes Cover waere diese Messung so
blind wie die Kartenmessung vor Build 241. Also wird eines
untergeschoben, mit wechselndem Seitenverhaeltnis wie echte Boxarts.

ZUR EINORDNUNG, aus dem Bench des Nutzers:

    Abschnitt I.3   ein kleiner C-Fuellaufruf        ~0,39 ms Grundpreis
    Abschnitt H.2   ein weiteres Rechteck im Aufruf  ~0,02 ms
    Abschnitt J     ein Schritt in Liste/liste       38,92 ms

Ein einzelner Sammelaufruf mit rund 30 Rechtecken sollte auf dem Geraet
also grob 1 ms kosten. Ob das "merkbar" ist, entscheidet nicht diese
Datei - aber sie liefert die Zahl dafuer.

Ausfuehren:
    python3 tools/diag_eckenkosten.py
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H          # noqa: E402

import fe.art as ART          # noqa: E402
import fe.bench as BENCH      # noqa: E402

_uhr = time.perf_counter      # der Pruefstand friert monotonic() ein

SCHRITTE = 40
RUNDEN = 7

# Aus dem Bench des Nutzers - siehe Kopf.
MS_JE_AUFRUF = 0.39
MS_JE_RECHTECK = 0.02


def _median(w):
    return sorted(w)[len(w) // 2]


def _cover_unterschieben():
    echt = ART.ART.get_scaled
    zaehler = [0]
    puffer = {}

    def _ersatz(quelle, breite, hoehe, **k):
        zaehler[0] += 1
        aw = max(8, int(breite) - (zaehler[0] % 3) * 7)
        ah = max(8, int(hoehe) - (zaehler[0] % 4) * 5)
        pix = puffer.get((aw, ah))
        if pix is None:
            pix = bytes(bytearray([40, 90, 160, 0])) * aw * ah
            puffer[(aw, ah)] = pix
        return (aw, ah, pix)

    ART.ART.get_scaled = _ersatz

    def _zurueck():
        ART.ART.get_scaled = echt

    return _zurueck


def _messen(fe, fm, seite, an):
    fm.FEIN = an
    schritt = BENCH.schritt_funktion(fe, seite)
    schritt(0)
    spanne = BENCH.fenster_spanne(fe, seite)
    for i in range(SCHRITTE):
        schritt(i % spanne)
    t0 = _uhr()
    for i in range(SCHRITTE):
        schritt(i % spanne)
    return (_uhr() - t0) * 1000.0 / SCHRITTE


def _rechtecke_zaehlen(fe, fm):
    """Wieviele Rechtecke gehen in den EINEN Sammelaufruf?"""
    fb = fe.fb
    echt = fb.flaechen_fueller
    zaehler = {"aufrufe": 0, "rechtecke": 0}
    echt_stempeln = fb.ecken_stempeln

    def _haken(buf, stride, hoehe, grenze, rechtecke):
        zaehler["aufrufe"] += 1
        zaehler["rechtecke"] += len(rechtecke)
        return echt(buf, stride, hoehe, grenze, rechtecke)

    def _stempel_haken(*a, **k):
        _vor = (zaehler["aufrufe"], zaehler["rechtecke"])
        fb.flaechen_fueller = _haken
        try:
            return echt_stempeln(*a, **k)
        finally:
            fb.flaechen_fueller = echt
            zaehler["letzte"] = (zaehler["aufrufe"] - _vor[0],
                                 zaehler["rechtecke"] - _vor[1])

    fb.ecken_stempeln = _stempel_haken
    try:
        fm.FEIN = True
        fe._force_full_redraw = True
        fe.draw()
    finally:
        fb.ecken_stempeln = echt_stempeln
        fb.flaechen_fueller = echt
    return zaehler.get("letzte", (0, 0))


def main():
    H.set_screen(1920, 1080)
    fe = H.make_frontend(page=1)
    fm = H.fm
    print("=" * 70)
    print(" Was kosten die abgerundeten Cover-Ecken? - %dx%d, %d Schritte,"
          " %d Runden" % (fe.fb.width, fe.fb.height, SCHRITTE, RUNDEN))
    print("=" * 70)
    print(" ABWECHSELND gemessen, Median genommen, Streuung daneben.")
    print(" Ein Unterschied, der nicht groesser ist als die Streuung,")
    print(" ist keine Aussage - das ist die Lehre aus Abschnitt E.")
    print("")

    alt = getattr(fm, "FEIN", True)
    zurueck = _cover_unterschieben()
    try:
        kat_i, kat_n, kat_name = BENCH._groesste_kategorie(fe)
        if kat_i is None:
            print(" keine Kategorie mit Eintraegen - abgebrochen")
            return
        fe.page = 1
        fe.cat_i = kat_i
        fe.nav_path = []

        try:
            fe.ansicht_setzen("liste")
            n_auf, n_rech = _rechtecke_zaehlen(fe, fm)
            print(" DER STEMPEL SELBST: %d Aufruf(e), %d Rechtecke"
                  % (n_auf, n_rech))
            print(" -> auf dem Geraet rund %.2f ms"
                  " (%d x %.2f + %d x %.2f)"
                  % (n_auf * MS_JE_AUFRUF + n_rech * MS_JE_RECHTECK,
                     n_auf, MS_JE_AUFRUF, n_rech, MS_JE_RECHTECK))
            print("")
        except Exception as e:                           # noqa: BLE001
            print(" Zaehlen uebersprungen (%s)" % type(e).__name__)

        print(" DER SCROLLSCHRITT")
        print(" %-20s %10s %10s %12s" % ("", "ohne", "mit", "Unterschied"))
        for ansicht in ("liste", "raster", "galerie"):
            try:
                fe.ansicht_setzen(ansicht)
                ohne_l, mit_l = [], []
                for _r in range(RUNDEN):
                    ohne_l.append(_messen(fe, fm, 1, False))
                    mit_l.append(_messen(fe, fm, 1, True))
            except Exception as e:                       # noqa: BLE001
                print("   %-18s -- uebersprungen (%s)"
                      % (ansicht, type(e).__name__))
                continue
            ohne, mit = _median(ohne_l), _median(mit_l)
            streu = max(max(ohne_l) - min(ohne_l), max(mit_l) - min(mit_l))
            d = mit - ohne
            urteil = "im Rauschen" if abs(d) <= streu else "AUSSERHALB"
            print("   %-18s %7.3f ms %7.3f ms  %+7.3f ms  (Streuung"
                  " %.3f, %s)" % (ansicht, ohne, mit, d, streu, urteil))
    finally:
        fm.FEIN = alt
        zurueck()

    print("")
    print("=" * 70)
    print(" Zu lesen als: steht 'AUSSERHALB', kostet der Stempel mehr als")
    print(" das Rauschen - dann entscheidet die Zahl 'auf dem Geraet'")
    print(" oben, ob er bleiben darf. Er steht ohnehin unter dem")
    print(" Feinheiten-Schalter; wer ihn nicht will, schaltet ihn aus.")
    print(" Und beachte: die Ecken werden nur gestempelt, wenn ein Cover")
    print(" da ist - beim schnellen Scrollen laesst das Frontend die")
    print(" Boxart-Spalte aus, dort kostet der Stempel also gar nichts.")
    print("=" * 70)


if __name__ == "__main__":
    main()
