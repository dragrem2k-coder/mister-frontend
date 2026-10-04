#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Woraus besteht ein Scrollschritt MIT Cover? (Build 241)

DER ANLASS ist die Frage vom Geraet: "wenn ich in arcade ordner gehe mit
cover wechsel anzeigen und nach unten gedrueckt scrolle, kann man da
noch was an anzeigezeit bzw geschwindigkeit rausholen?"

Dazu die Zahlen aus seinem Bench fuer genau diese Ansicht:

    Liste liste   ges 39.27 ms
      karten 13.81   flip 9.18 (3.5 MB)   panel 6.31   REST 3.61

WARUM ES DIESES WERKZEUG BRAUCHT, obwohl es diag_kartenkosten.py schon
gibt: der Pruefstand hat KEINE Cover-Dateien. art ist dort immer None,
und damit faellt genau der Teil weg, um den es geht - der Rahmen um das
Cover, der Schlagschatten darunter, die Aussparung in der Karte. Die
bisherige Messung war an dieser Stelle blind, und blind heisst hier:
sie zeigte vier rect()-Aufrufe nicht an, die es auf dem Geraet in JEDEM
Schritt gibt.

Hier wird deshalb ein Cover UNTERGESCHOBEN - ein erzeugtes Bild in der
Groesse, die das Panel anfragt. Damit laeuft derselbe Weg wie auf dem
Geraet.

WAS GEZAEHLT WIRD und warum die Zahl der AUFRUFE die wichtigere ist:
Abschnitt I.3 des Bench misst auf dem Geraet eine 60x40-Flaeche mit
0,489 ms in C und eine 697x3 mit 0,318 ms. Beides sind winzige
Flaechen - das ist nicht die Flaeche, das ist der AUFRUF. Wer die Zahl
der Aufrufe senkt, senkt die Zeit; wer nur die Flaeche senkt, oft nicht.

Ausfuehren:
    python3 tools/diag_cover_panel.py
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H          # noqa: E402

import fe.art as ART          # noqa: E402
import fe.bench as BENCH      # noqa: E402

_uhr = time.perf_counter      # der Pruefstand friert monotonic() ein

SCHRITTE = 12

# Was ein kleiner C-Fuellaufruf auf dem DE10-Nano kostet - gemessen,
# nicht geschaetzt: Abschnitt I.3 des Bench, 60x40 und 697x3.
MS_JE_AUFRUF = 0.40


def _cover_unterschieben():
    """ART.get_scaled() liefert ab jetzt ein erzeugtes Cover in genau
    der angefragten Groesse. Rueckgabe: die Funktion zum Aufraeumen.

    DIE GROESSE WECHSELT VON SCHRITT ZU SCHRITT, und das ist Absicht:
    auf dem Geraet hat jedes Spiel ein anders proportioniertes Cover,
    die Aussparung in der Karte ist also jeden Schritt eine andere.
    Ein immer gleiches Cover wuerde einen Fall messen, den es nicht
    gibt."""
    # ART ist die ArtCache-INSTANZ in fe/art.py, nicht das Modul -
    # frontend.py ruft ART.get_scaled() darauf.
    echt = ART.ART.get_scaled
    zaehler = [0]
    puffer = {}

    def _ersatz(quelle, breite, hoehe, **k):
        zaehler[0] += 1
        # Mal etwas schmaler, mal etwas kuerzer - wie echte Boxarts.
        aw = max(8, int(breite) - (zaehler[0] % 3) * 7)
        ah = max(8, int(hoehe) - (zaehler[0] % 4) * 5)
        pix = puffer.get((aw, ah))
        if pix is None:
            zeile = bytes(bytearray([40, 90, 160, 0])) * aw
            pix = zeile * ah
            puffer[(aw, ah)] = pix
        return (aw, ah, pix)

    ART.ART.get_scaled = _ersatz

    def _zurueck():
        ART.ART.get_scaled = echt

    return _zurueck


def main():
    H.set_screen(1920, 1080)
    fe = H.make_frontend(page=1)
    fb = fe.fb
    K = type(fe)

    print("=" * 72)
    print(" Ein Scrollschritt MIT Cover - %dx%d, %d Schritte"
          % (fb.width, fb.height, SCHRITTE))
    print("=" * 72)
    print(" Das Cover ist erzeugt, nicht gelesen: es geht um den")
    print(" ZEICHENWEG, nicht um das Dekodieren. Die Millisekunden sind")
    print(" die dieses Rechners; uebertragbar ist die Zahl der AUFRUFE.")
    print(" Auf dem Geraet kostet ein kleiner C-Fuellaufruf rund %.2f ms"
          % MS_JE_AUFRUF)
    print(" (Abschnitt I.3: 60x40 -> 0,489 ms, 697x3 -> 0,318 ms).")
    print("")

    zurueck = _cover_unterschieben()
    try:
        kat_i, kat_n, kat_name = BENCH._groesste_kategorie(fe)
        if kat_i is None:
            print(" keine Kategorie mit Eintraegen - abgebrochen")
            return
        fe.page = 1
        fe.cat_i = kat_i
        fe.nav_path = []

        for ansicht in ("liste", "raster", "galerie"):
            try:
                fe.ansicht_setzen(ansicht)
            except Exception:                            # noqa: BLE001
                continue
            schritt = BENCH.schritt_funktion(fe, 1)
            schritt(0)                       # erst zeichnen (Build 239)
            spanne = BENCH.fenster_spanne(fe, 1)
            for i in range(SCHRITTE):
                schritt(i % spanne)

            konto = {}
            tiefe = [0]
            echte = []
            for name in ("karte_mit_schatten", "rect_rounded_schatten",
                         "rect_rounded", "rect", "rect_viele"):
                if hasattr(fb, name):
                    echte.append((name, getattr(fb, name)))

            def _haken(name, echt):
                def ersatz(*a, **k):
                    # NUR DER AEUSSERSTE AUFRUF - dieselbe Bauweise wie
                    # _h_karte() im Bench: karte_mit_schatten() ruft
                    # rect_rounded(), und die ruft rect(). Ohne das
                    # stuende dieselbe Zeit dreimal da.
                    if tiefe[0]:
                        return echt(*a, **k)
                    try:
                        if name == "rect_viele":
                            _n = len(list(a[0])) if a else 0
                            masse = "%d Rechtecke" % _n
                        else:
                            masse = "%dx%d" % (int(a[2]), int(a[3]))
                    except Exception:                    # noqa: BLE001
                        masse = "?"
                    t0 = _uhr()
                    tiefe[0] += 1
                    try:
                        return echt(*a, **k)
                    finally:
                        tiefe[0] -= 1
                        e = konto.setdefault((name, masse), [0, 0.0])
                        e[0] += 1
                        e[1] += (_uhr() - t0) * 1000.0
                return ersatz

            for name, echt in echte:
                setattr(fb, name, _haken(name, echt))
            try:
                t0 = _uhr()
                for i in range(SCHRITTE):
                    schritt(i % spanne)
                ges = (_uhr() - t0) * 1000.0 / SCHRITTE
            finally:
                for name, echt in echte:
                    setattr(fb, name, echt)

            aufrufe = sum(e[0] for e in konto.values()) / float(SCHRITTE)
            summe = sum(e[1] for e in konto.values()) / SCHRITTE
            print("  Liste %-8s Schritt %6.2f ms, davon Fuellen %5.2f ms"
                  % (ansicht, ges, summe))
            print("     %.1f Aufrufe je Schritt -> auf dem Geraet rund"
                  " %.1f ms NUR Aufruf-Overhead"
                  % (aufrufe, aufrufe * MS_JE_AUFRUF))
            for (name, masse), (n, ms) in sorted(
                    konto.items(), key=lambda e: -e[1][1])[:7]:
                print("        %-22s %-14s %5.2f x/Schritt  %6.3f ms"
                      % (name, masse, n / float(SCHRITTE), ms / SCHRITTE))
            print("")
    finally:
        zurueck()
        try:
            K._restore_row_bg = K._restore_row_bg
        except Exception:                                # noqa: BLE001
            pass

    print("=" * 72)
    print(" Zu lesen als: die Zahl der Aufrufe mal %.2f ms ist der Teil,"
          % MS_JE_AUFRUF)
    print(" den das Geraet allein fuer das Hinein und Heraus bezahlt -")
    print(" unabhaengig davon, wie gross die Flaechen sind. Steht dort")
    print(" ein nennenswerter Betrag, ist ZUSAMMENFASSEN die Abhilfe")
    print(" und nicht eine kleinere Flaeche.")
    print("=" * 72)


if __name__ == "__main__":
    main()
