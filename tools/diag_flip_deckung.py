#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DIAGNOSE: deckt der Rechteck-Flip wirklich alles ab, was sich geaendert
hat?

DIE FRAGE, AN DER BUILD 218 GESCHEITERT IST. Seit Build 215 geht nicht
mehr das ganze Bild auf den Schirm, sondern nur noch die Rechtecke, die
der Zeichenweg als veraendert gemeldet hat (_flip_spuren). Meldet eine
Stelle ihr Rechteck NICHT, bleibt dort der alte Inhalt auf dem Schirm
stehen - im Puffer sieht alles richtig aus, auf dem Bild nicht. In Build
218 waren das 210.600 Bildpunkte auf der Hauptseite, und gefunden wurden
sie durch Zufall.

Dieses Werkzeug fragt es mechanisch:

    1. einen leichten Schritt zeichnen, dabei den Puffer VORHER und
       NACHHER vergleichen  ->  welche Bildpunkte haben sich GEAENDERT?
    2. die gemeldeten Rechtecke einsammeln                ->  was WUERDE
       auf den Schirm gehen?
    3. Differenz bilden: geaendert, aber nicht gemeldet = ein Rest, der
       auf dem Schirm stehenbleibt

Ausgegeben wird je Ansicht die Zahl der ungedeckten Bildpunkte und ihr
umschliessendes Rechteck - damit man weiss, WO man suchen muss.

Diagnose, kein Test: der Rueckgabewert ist immer 0. Die Zahl soll bei
Aenderungen am Zeichenweg nicht STEIGEN.

Ausfuehren:
    python3 tools/diag_flip_deckung.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H          # noqa: E402

ANSICHTEN = ("liste", "raster", "galerie")


def _rechtecke_einsammeln(fe):
    """Was bei diesem Schritt tatsaechlich auf den Schirm ginge.

    GEHAKT WERDEN DIE DREI FLIP-WEGE SELBST und nicht
    _rechtecke_flippen(): die Listenansicht schickt ihre Rechtecke am
    Verteiler vorbei direkt an fb.flip_rechtecke(), und ein Haken eine
    Ebene zu hoch haette fuer sie "VOLLBILD" gemeldet - also genau das
    Gegenteil dessen, was auf dem Geraet passiert. Hier zaehlt, was den
    Bildspeicher erreicht, nichts darueber."""
    fb = fe.fb
    gesammelt = []
    echt = (fb.flip_rechtecke, fb.flip_rows, fb.flip)

    def h_rechtecke(rechtecke, skip_vsync=False):
        gesammelt.extend(list(rechtecke))
        return 0

    def h_rows(y, h, skip_vsync=False):
        gesammelt.append((0, y, fb.width, h))
        return 0

    def h_voll(skip_vsync=False):
        gesammelt.append((0, 0, fb.width, fb.height))
        return 0

    fb.flip_rechtecke = h_rechtecke
    fb.flip_rows = h_rows
    fb.flip = h_voll
    return gesammelt, echt


def _maske(breite, hoehe, rechtecke):
    """Welche Zeilen/Spalten sind gedeckt - als Menge von (x, y) waere
    es zu gross, deshalb je Zeile ein bytearray."""
    maske = [bytearray(breite) for _ in range(hoehe)]
    for r in rechtecke:
        try:
            x, y, w, h = r[0], r[1], r[2], r[3]
        except (TypeError, IndexError):
            continue
        x0 = max(0, x); y0 = max(0, y)
        x1 = min(breite, x + w); y1 = min(hoehe, y + h)
        if x1 <= x0 or y1 <= y0:
            continue
        eins = b"\x01" * (x1 - x0)
        for yy in range(y0, y1):
            maske[yy][x0:x1] = eins
    return maske


def _pruefen(name, fe, vorher, rechtecke):
    fb = fe.fb
    stride, breite, hoehe = fb.stride, fb.width, fb.height
    nachher = bytes(fb.buf)
    maske = _maske(breite, hoehe, rechtecke)
    offen = 0
    x_min = y_min = 10 ** 9
    x_max = y_max = -1
    for y in range(hoehe):
        a = y * stride
        zeile_alt = vorher[a:a + breite * 4]
        zeile_neu = nachher[a:a + breite * 4]
        if zeile_alt == zeile_neu:
            continue
        m = maske[y]
        for x in range(breite):
            o = x * 4
            if zeile_alt[o:o + 3] == zeile_neu[o:o + 3]:
                continue
            if m[x]:
                continue
            offen += 1
            if x < x_min:
                x_min = x
            if x > x_max:
                x_max = x
            if y < y_min:
                y_min = y
            if y > y_max:
                y_max = y
    flaeche = sum(r[2] * r[3] for r in rechtecke
                  if len(r) >= 4) if rechtecke else 0
    print("   %-26s %2d Rechtecke, %7.2f MB  ->  %d ungedeckte Punkte"
          % (name, len(rechtecke), flaeche * 4 / 1048576.0, offen))
    if offen:
        print("        %s  der Bereich: x %d..%d, y %d..%d"
              % ("!" * 3, x_min, x_max, y_min, y_max))
    return offen


def main():
    gesamt = 0
    for res_label, w, h in (("CRT 320x240", 320, 240),
                            ("HDMI 1920x1080", 1920, 1080)):
        H.set_screen(w, h)
        print("== %s" % res_label)
        for seite, seitenname in ((0, "Hauptseite"), (1, "Spieleliste")):
            for ansicht in ANSICHTEN:
                try:
                    fe = H.make_frontend(seite)
                    fb = fe.fb
                    if seite == 0:
                        fe.ansicht_haupt_setzen(ansicht)
                    else:
                        fe.ansicht_setzen(ansicht)
                    # WARMLAUFEN MIT ECHTEN SCHRITTEN, nicht mit zwei
                    # draw(): _force_full_redraw ist ein Einmal-Schalter,
                    # den der Listenpfad von draw() NICHT loescht (der
                    # Fund aus Build 218). Wer nur zweimal zeichnet, misst
                    # deshalb zweimal den vollen Aufbau und haelt die
                    # Ansicht faelschlich fuer einen Vollbild-Flipper.
                    fe.draw()
                    for _i in range(4):
                        if seite == 0:
                            _alt = fe.cat_i
                            fe.cat_i = (fe.cat_i + 1) % max(1, len(fe.cats))
                            if not fe._draw_navigate_cats(_alt):
                                fe.draw()
                        else:
                            _n = max(1, len(fe._display_items()))
                            _alt = fe.item_i
                            fe.item_i = (fe.item_i + 1) % _n
                            if not fe._draw_navigate_items(_alt):
                                fe.draw()
                except Exception as e:                   # noqa: BLE001
                    print("   %-26s uebersprungen (%s)"
                          % ("%s %s" % (seitenname, ansicht),
                             type(e).__name__))
                    continue
                rechtecke, echt = _rechtecke_einsammeln(fe)
                vorher = bytes(fb.buf)
                try:
                    # GENAU DIE REIHENFOLGE AUS run() - erst der leichte
                    # Pfad, und nur wenn der ablehnt, der volle Aufbau.
                    # Die Listenansicht hat ihren leichten Weg in
                    # _draw_navigate_items(); draw() ruft ihn NIE (siehe
                    # Abschnitt J des Benchs, Build 219). Ohne das hier
                    # stuende fuer die Liste "VOLLBILD", obwohl sie auf
                    # dem Geraet laengst Rechtecke schickt.
                    if seite == 0:
                        alt = fe.cat_i
                        fe.cat_i = (fe.cat_i + 1) % max(1, len(fe.cats))
                        if not fe._draw_navigate_cats(alt):
                            fe.draw()
                    else:
                        n = max(1, len(fe._display_items()))
                        alt = fe.item_i
                        fe.item_i = (fe.item_i + 1) % n
                        if not fe._draw_navigate_items(alt):
                            fe.draw()
                finally:
                    (fb.flip_rechtecke, fb.flip_rows, fb.flip) = echt
                if not rechtecke:
                    print("   %-26s NICHTS geflippt"
                          % ("%s %s" % (seitenname, ansicht)))
                    continue
                if (len(rechtecke) == 1
                        and tuple(rechtecke[0][:4])
                        == (0, 0, fb.width, fb.height)):
                    print("   %-26s VOLLBILD (%.2f MB) - diese Ansicht "
                          "benutzt den Rechteck-Flip nicht"
                          % ("%s %s" % (seitenname, ansicht),
                             fb.width * fb.height * 4 / 1048576.0))
                    continue
                gesamt += _pruefen("%s %s" % (seitenname, ansicht),
                                   fe, vorher, rechtecke)
        print("")
    print("Ungedeckte Bildpunkte insgesamt: %d" % gesamt)
    print("")
    print("Zu lesen als: jeder ungedeckte Punkt bleibt auf dem SCHIRM")
    print("als Rest des vorigen Bildes stehen, obwohl er im Puffer")
    print("richtig ist. Null ist der einzige gute Wert; 'VOLLBILD'")
    print("heisst, dass diese Ansicht den Rechteck-Flip gar nicht")
    print("benutzt - langsam, aber nicht falsch.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
