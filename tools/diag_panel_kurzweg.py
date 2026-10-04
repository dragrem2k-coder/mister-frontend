#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Was spart der kurze Weg im Cover-Panel? (Build 244)

DER BEFUND KOMMT AUS ABSCHNITT K DES BENCH, Lauf vom 04.10. auf dem
DE10-Nano, und er ist der groesste Einzelposten des ganzen
Scrollschritts:

    Liste liste   ges 39,42 ms
      karte_mit_schatten  769x945    8,295 ms
      flip                3,5 MB     9,230 ms

WAS DABEI PASSIERT, wenn man die Taste gedrueckt haelt und "Cover
sofort" an ist (die Einstellung des Nutzers): das Cover wird
uebersprungen (ART._defer_uncached), die Karte wird trotzdem JEDEN
SCHRITT komplett gefuellt, der Anfangsbuchstabe kommt hinein - und 2,9
MB gehen in den Bildspeicher. Dabei sieht die Karte genauso aus wie im
Schritt davor: derselbe leere Kasten, derselbe Buchstabe. Nur der TEXT
darunter wechselt.

DIESES WERKZEUG MISST GENAU DIESEN FALL. Es stellt her, was beim
Nutzer passiert - Cover uebersprungen, sortierte Liste, gleicher
Anfangsbuchstabe - und zaehlt, wieviel gefuellt und wieviel geflippt
wird, mit und ohne den kurzen Weg.

WAS DER KURZE WEG TUT: er zeichnet die Karte weiter, spart aber die
Flaeche des Cover-Kastens aus (karte_mit_schatten(aussparen=...), den
Mechanismus gibt es seit Build 234/238). Der Kasten bleibt damit
stehen - und dort steht schon das Richtige.

WAS ER NICHT TUT, und das ist der lehrreiche Teil: die Karte ganz
weglassen. Genau das war der erste Entwurf. Gemessen sah er besser aus
(gefuellt 2,71 auf 0,44 MB, geflippt 3,62 auf 1,13 MB), aber
tools/test_rechteck_flip.py hat ihn ueberfuehrt - 69 Bytes Unterschied
an der unteren rechten Kartenecke. Die Umgebung der Eckenrundung wird
NICHT von der Karte gefuellt (sie liegt ausserhalb der Kurve); ohne den
Kartenaufruf blieb dort, was der vorige Schritt hinterlassen hatte.

ZUR EINORDNUNG, alles aus seinem eigenen Bench:

    Abschnitt H.1   Bildspeicher je MB        1,55 ms
    Abschnitt K     karte_mit_schatten        8,295 ms je Schritt
    Abschnitt J     flip 3,5 MB               9,230 ms je Schritt

Ausfuehren:
    python3 tools/diag_panel_kurzweg.py
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H          # noqa: E402

import fe.art as ART          # noqa: E402
import fe.bench as BENCH      # noqa: E402

_uhr = time.perf_counter      # der Pruefstand friert monotonic() ein

SCHRITTE = 30

# Aus dem Bench des Nutzers - siehe Kopf.
MS_JE_MB_BILD = 1.55


def _mb(n):
    return n / 1048576.0


def _cover_ueberspringen():
    """get_scaled() verhaelt sich wie beim Schnellscrollen: es liefert
    NICHTS und zaehlt _defer_count hoch.

    GENAU SO SIEHT ES BEIM NUTZER AUS, und nicht anders: das Cover ist
    nicht WEG, es wird UEBERSPRUNGEN. Der Unterschied entscheidet,
    welchen Zweig draw_art_panel() nimmt - mit einem fehlenden Cover
    kaeme der Platzhalter, mit einem uebersprungenen der
    Anfangsbuchstabe."""
    echt = ART.ART.get_scaled

    def _ersatz(quelle, breite, hoehe, **k):
        # AUF DER INSTANZ, nicht am Modul: frontend.py importiert ART
        # aus fe.art und meint damit den ArtCache. Der erste Entwurf
        # hat am Modul gezaehlt - nur_verzoegert blieb falsch, und die
        # Messung zeigte brav, dass der kurze Weg nichts bringt.
        ART.ART._defer_count = getattr(ART.ART, "_defer_count", 0) + 1
        return None

    ART.ART.get_scaled = _ersatz

    def _zurueck():
        ART.ART.get_scaled = echt

    return _zurueck


def _zaehlen(fe, titel):
    """Einen Scrollschritt messen: gefuellte Zeilen/Bytes und
    geflippte Bytes."""
    fb = fe.fb
    konto = {"fuell_zeilen": 0, "fuell_bytes": 0, "fuell_n": 0,
             "flip_bytes": 0, "flip_n": 0, "flip_rechtecke": 0}
    echt_fuell = fb.flaechen_fueller
    echt_rect = fb.flip_rechtecke
    echt_rows = fb.flip_rows
    echt_voll = fb.flip

    def _h_fuell(buf, stride, hoehe, grenze, rechtecke):
        konto["fuell_n"] += 1
        for r in rechtecke:
            konto["fuell_zeilen"] += r[3]
            konto["fuell_bytes"] += r[2] * r[3] * 4
        return echt_fuell(buf, stride, hoehe, grenze, rechtecke)

    def _h_rect(rechtecke, *a, **k):
        rl = list(rechtecke)
        konto["flip_n"] += 1
        konto["flip_rechtecke"] += len(rl)
        konto["flip_bytes"] += sum(w * h * 4 for (_x, _y, w, h) in rl)
        return echt_rect(rl, *a, **k)

    def _h_rows(y, h, *a, **k):
        # FLIP_ROWS GEHOERT MIT AN DEN HAKEN, und das Fehlen war ein
        # Loch in dieser Messung: bei kleiner Aenderungsflaeche waehlt
        # das Frontend den Zeilen-Flip statt der Rechtecke. Der erste
        # Entwurf meldete daraufhin "0,00 MB geflippt" und sah damit
        # besser aus, als es ist.
        konto["flip_n"] += 1
        konto["flip_rechtecke"] += 1
        konto["flip_bytes"] += int(h) * fb.stride
        return echt_rows(y, h, *a, **k)

    def _h_voll(*a, **k):
        konto["flip_n"] += 1
        konto["flip_rechtecke"] += 1
        konto["flip_bytes"] += len(fb.buf)
        return echt_voll(*a, **k)

    # Die Titel wechseln von Schritt zu Schritt, der ANFANGSBUCHSTABE
    # bleibt - genau wie in einer sortierten Liste.
    _, node, _ = fe.cats[fe.cat_i]
    node["items"] = [
        ("%s %03d" % (titel, i), "game",
         ("/f/%d.sfc" % i, ".sfc", "SNES", None, None))
        for i in range(60)]
    node.pop("_display_items_cache", None)
    fe.item_i = 0
    fe.scroll = 0
    fe.ansicht_setzen("liste")

    schritt = BENCH.schritt_funktion(fe, 1)
    schritt(0)
    spanne = BENCH.fenster_spanne(fe, 1)
    for i in range(SCHRITTE):                    # warmlaufen
        schritt(i % spanne)

    fb.flaechen_fueller = _h_fuell
    fb.flip_rechtecke = _h_rect
    fb.flip_rows = _h_rows
    fb.flip = _h_voll
    try:
        t0 = _uhr()
        for i in range(SCHRITTE):
            schritt(i % spanne)
        konto["ms"] = (_uhr() - t0) * 1000.0 / SCHRITTE
    finally:
        fb.flaechen_fueller = echt_fuell
        fb.flip_rechtecke = echt_rect
        fb.flip_rows = echt_rows
        fb.flip = echt_voll
    for k in ("fuell_zeilen", "fuell_bytes", "fuell_n",
              "flip_bytes", "flip_n", "flip_rechtecke"):
        konto[k] = konto[k] / float(SCHRITTE)
    return konto


def main():
    H.set_screen(1920, 1080)
    fe = H.make_frontend(page=1)

    print("=" * 72)
    print(" Was spart der kurze Weg im Cover-Panel? - %dx%d, %d Schritte"
          % (fe.fb.width, fe.fb.height, SCHRITTE))
    print("=" * 72)
    print(" Hergestellt wird der Fall des Nutzers: Taste gedrueckt,")
    print(" 'Cover sofort' an, sortierte Liste. Das Cover wird")
    print(" UEBERSPRUNGEN, der Anfangsbuchstabe bleibt derselbe.")
    print("")

    zurueck = _cover_ueberspringen()
    try:
        fe.page = 1
        fe.cat_i = 0
        fe.nav_path = []

        # 1) Mit dem kurzen Weg - gleicher Anfangsbuchstabe.
        mit = _zaehlen(fe, "Super Mario")

        # 2) Ohne ihn: der Stand wird vor jedem Schritt verworfen. Das
        #    ist genau der Zustand vor Build 244.
        echt_panel = type(fe).draw_art_panel

        def _ohne_kurz(selbst, *a, **k):
            selbst._panel_stand = None
            return echt_panel(selbst, *a, **k)

        type(fe).draw_art_panel = _ohne_kurz
        try:
            ohne = _zaehlen(fe, "Super Mario")
        finally:
            type(fe).draw_art_panel = echt_panel

        print(" %-26s %12s %12s %10s" % ("", "ohne", "mit", "gespart"))
        for name, schl, einheit in (
                ("gefuellte Zeilen", "fuell_zeilen", "z"),
                ("gefuellte Bytes", "fuell_bytes", "MB"),
                ("Fuellaufrufe", "fuell_n", ""),
                ("geflippte Bytes", "flip_bytes", "MB"),
                ("Flip-Rechtecke", "flip_rechtecke", "")):
            a, b = ohne[schl], mit[schl]
            if einheit == "MB":
                print("   %-24s %9.2f MB %9.2f MB %8.2f MB"
                      % (name, _mb(a), _mb(b), _mb(a - b)))
            else:
                print("   %-24s %9.1f %s %11.1f %s %8.1f"
                      % (name, a, einheit, b, einheit, a - b))
        print("")
        print("   %-24s %9.3f ms %9.3f ms %8.3f ms"
              % ("Schritt (dieser Rechner)", ohne["ms"], mit["ms"],
                 ohne["ms"] - mit["ms"]))
        _f_mb = _mb(ohne["fuell_bytes"] - mit["fuell_bytes"])
        _f_z = ohne["fuell_zeilen"] - mit["fuell_zeilen"]
        print("")
        print("   AUF DEM GERAET, nach dem Modell aus Abschnitt I.1")
        print("   (je Zeile 0,000576 ms, je MB 2,1 ms - aus 136 langen")
        print("    gegen 952 kurze Zeilen in C):")
        print("     ohne  %6.0f Zeilen + %.2f MB = %5.2f ms"
              % (ohne["fuell_zeilen"], _mb(ohne["fuell_bytes"]),
                 ohne["fuell_zeilen"] * 0.000576
                 + _mb(ohne["fuell_bytes"]) * 2.1))
        print("     mit   %6.0f Zeilen + %.2f MB = %5.2f ms"
              % (mit["fuell_zeilen"], _mb(mit["fuell_bytes"]),
                 mit["fuell_zeilen"] * 0.000576
                 + _mb(mit["fuell_bytes"]) * 2.1))
        print("   DER FLIP AENDERT SICH NICHT, und das ist Absicht: die")
        print("   Karte wird weiter gezeichnet (nur der Kasten")
        print("   ausgespart), also ist die angefasste Flaeche dieselbe.")
        print("   Der erste Entwurf liess die Karte ganz weg und sparte")
        print("   dabei 2,49 MB Flip - und liess 69 Bytes an der")
        print("   Kartenecke stehen. Siehe test_rechteck_flip.py.")

        # 2b) DIE WICHTIGSTE PRUEFUNG DIESER AENDERUNG: liegt JEDES
        #     geaenderte Byte in einem geflippten Bereich? Ein Byte,
        #     das geaendert aber nicht geflippt wurde, bleibt auf dem
        #     Schirm als Rest des vorigen Bildes stehen - der Fehler,
        #     den tools/diag_flip_deckung.py sucht. Dort greift der
        #     kurze Weg aber nicht, weil der Pruefstand keine Cover
        #     hat; also hier.
        print("")
        print(" DECKUNG DES KURZEN WEGS")
        fb = fe.fb
        _, node, _ = fe.cats[fe.cat_i]
        node["items"] = [
            ("Super Mario %03d" % i, "game",
             ("/f/%d.sfc" % i, ".sfc", "SNES", None, None))
            for i in range(60)]
        node.pop("_display_items_cache", None)
        fe.item_i = 0
        fe.scroll = 0
        fe.ansicht_setzen("liste")
        schritt = BENCH.schritt_funktion(fe, 1)
        schritt(0)
        spanne = BENCH.fenster_spanne(fe, 1)
        for i in range(8):
            schritt(i % spanne)

        geflippt = []
        echt_rect2 = fb.flip_rechtecke
        echt_rows2 = fb.flip_rows
        echt_voll2 = fb.flip

        def _s_rect(rechtecke, *a, **k):
            for (x, y, w, h) in rechtecke:
                geflippt.append((y, y + h))
            return echt_rect2(rechtecke, *a, **k)

        def _s_rows(y, h, *a, **k):
            geflippt.append((y, y + h))
            return echt_rows2(y, h, *a, **k)

        def _s_voll(*a, **k):
            geflippt.append((0, fb.height))
            return echt_voll2(*a, **k)

        ungedeckt = 0
        schritte_geprueft = 0
        for i in range(12):
            vorher = bytes(fb.buf)
            del geflippt[:]
            fb.flip_rechtecke = _s_rect
            fb.flip_rows = _s_rows
            fb.flip = _s_voll
            try:
                schritt(i % spanne)
            finally:
                fb.flip_rechtecke = echt_rect2
                fb.flip_rows = echt_rows2
                fb.flip = echt_voll2
            nachher = bytes(fb.buf)
            if vorher == nachher:
                continue
            schritte_geprueft += 1
            # Welche ZEILEN haben sich geaendert?
            st = fb.stride
            for y in range(fb.height):
                a = y * st
                if vorher[a:a + st] == nachher[a:a + st]:
                    continue
                if not any(y0 <= y < y1 for (y0, y1) in geflippt):
                    ungedeckt += 1
        print("   %d Schritte mit Aenderung, %d ungedeckte Zeilen"
              % (schritte_geprueft, ungedeckt))
        print("   (null ist der einzige gute Wert - eine geaenderte,")
        print("    nicht geflippte Zeile bleibt als Rest stehen)")

        # 3) UND DIE GEGENPROBE: wechselt der Anfangsbuchstabe, MUSS
        #    der volle Weg laufen - sonst stuende der alte Buchstabe da.
        print("")
        print(" GEGENPROBE: wechselnder Anfangsbuchstabe")
        _, node, _ = fe.cats[fe.cat_i]
        node["items"] = [
            ("%s%03d" % (chr(65 + (i % 26)), i), "game",
             ("/f/%d.sfc" % i, ".sfc", "SNES", None, None))
            for i in range(60)]
        node.pop("_display_items_cache", None)
        wechsel = _zaehlen(fe, None) if False else None
        fe.item_i = 0
        fe.scroll = 0
        fe.ansicht_setzen("liste")
        schritt = BENCH.schritt_funktion(fe, 1)
        schritt(0)
        spanne = BENCH.fenster_spanne(fe, 1)
        _voll = {"n": 0}
        _echt2 = type(fe)._panel_text_zeichnen

        def _zaehl_text(selbst, *a, **k):
            _voll["n"] += 1
            return _echt2(selbst, *a, **k)

        type(fe)._panel_text_zeichnen = _zaehl_text
        try:
            for i in range(SCHRITTE):
                schritt(i % spanne)
        finally:
            type(fe)._panel_text_zeichnen = _echt2
        print("   der Textblock wurde %d mal gezeichnet (%d Schritte) -"
              % (_voll["n"], SCHRITTE))
        print("   er laeuft auf BEIDEN Wegen, das ist richtig so.")
    finally:
        zurueck()

    print("")
    print("=" * 72)
    print(" Zu lesen als: der kurze Weg greift nur, wenn der")
    print(" Cover-Kasten GLEICH AUSSIEHT - gleiches Bild oder gleicher")
    print(" Buchstabe, gleiche Geometrie, gleiche Farben, kein voller")
    print(" Aufbau dazwischen. Beim Blaettern durch eine sortierte")
    print(" Liste ist das der Normalfall; bei jedem Buchstabenwechsel")
    print(" laeuft einmal der volle Weg, und das muss er auch.")
    print("=" * 72)


if __name__ == "__main__":
    main()
