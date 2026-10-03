#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DIAGNOSE: woraus bestehen die 15,57 ms von `text`?

DIE FRAGE. Im Geraetebericht vom 02.10. steht `text` mit 15,57 ms je
Scrollschritt in der Spieleliste/Galerie - der groesste verbliebene
Posten nach Build 226. Bevor etwas umgebaut wird, muss klar sein, WOFUER
die Zeit draufgeht, denn es sind zwei voellig verschiedene Dinge:

    STREIFEN BAUEN   ein Fehltreffer im Textcache: acht b"".join() ueber
                     alle Zeichen, dazu die Glyphenzeilen. Teuer, aber
                     nur beim ersten Mal fuer diesen Text.
    BLITTEN          die Schleife am Ende von text(): 8*scale
                     Schnittzuweisungen in den Puffer. Billig je Zeile,
                     aber sie faellt bei JEDEM Aufruf an, auch bei einem
                     Treffer.

Nur das Blitten liesse sich nach C verschieben - und ob sich das lohnt,
haengt an Build 221: ein C-Aufruf kostet auf dem DE10-Nano rund EINE
Millisekunde. Ein Aufruf je Textzeile waere also teurer als die
Python-Schleife, die er ersetzen soll. Deshalb wird hier auch gezaehlt,
WIE VIELE Aufrufe je Schritt zusammenkommen.

Gemessen wird am Entwicklungsrechner; die Zeiten sind dort kleiner als
auf dem Geraet. Was uebertraegt, sind die ZAEHLUNGEN (Aufrufe, Treffer,
Zeilen, Breiten) und das Verhaeltnis der beiden Posten zueinander.

Diagnose, kein Test: der Rueckgabewert ist immer 0.

Ausfuehren:
    python3 tools/diag_textkosten.py
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H          # noqa: E402

ANSICHTEN = ("liste", "raster", "galerie")


class Zaehler(object):
    def __init__(self):
        self.aufrufe = 0
        self.fenster = 0
        self.treffer = 0
        self.fehl = 0
        self.t_bauen = 0.0
        self.t_blit = 0.0
        self.t_gesamt = 0.0
        self.zeilen = 0          # geschriebene Bildzeilen insgesamt
        self.bytes_ = 0
        self.breiten = {}        # scale -> groesste Streifenbreite

    def merken(self, scale, w4, zeilen):
        self.zeilen += zeilen
        self.bytes_ += w4 * zeilen
        if w4 > self.breiten.get(scale, 0):
            self.breiten[scale] = w4


def _haken(fb, z):
    """text(), text_window() und _text_strip() umlegen - die echten
    Fassungen laufen weiter, es wird nur die Zeit genommen."""
    echt_text = fb.text
    echt_fenster = fb.text_window
    echt_strip = fb._text_strip
    uhr = time.perf_counter

    def strip(s, scale, fg, bg, cachen=True):
        vorher = len(fb._textcache)
        t0 = uhr()
        erg = echt_strip(s, scale, fg, bg, cachen)
        dt = uhr() - t0
        # Treffer oder nicht? Der Cache-Zaehler des Framebuffers waere
        # genauer, aber er wird auch anderswo gelesen - hier reicht die
        # Zeit: ein Treffer ist ein Dictionary-Zugriff.
        if dt > 0.00005 or len(fb._textcache) != vorher:
            z.fehl += 1
            z.t_bauen += dt
        else:
            z.treffer += 1
            z.t_bauen += dt
        return erg

    def text(x, y, s, scale=2, fg=None, bg=None, cachen=True):
        z.aufrufe += 1
        t0 = uhr()
        erg = echt_text(x, y, s, scale, fg, bg, cachen)
        z.t_gesamt += uhr() - t0
        if s:
            z.merken(scale, len(s) * 8 * scale * 4, 8 * scale)
        return erg

    def fenster(x, y, full, off, maxc, scale=2, fg=None, bg=None):
        z.fenster += 1
        t0 = uhr()
        erg = echt_fenster(x, y, full, off, maxc, scale, fg, bg)
        z.t_gesamt += uhr() - t0
        z.merken(scale, maxc * 8 * scale * 4, 8 * scale)
        return erg

    fb.text = text
    fb.text_window = fenster
    fb._text_strip = strip
    return (echt_text, echt_fenster, echt_strip)


def _schritt(fe, seite):
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


def _messen(fn, runden=200):
    uhr = time.perf_counter
    fn()                                   # einmal warmlaufen
    t0 = uhr()
    for _ in range(runden):
        fn()
    return (uhr() - t0) * 1000.0 / runden


def teil2():
    """C gegen Python, Streifen fuer Streifen - und als Bund.

    Das Modell des Geraets (Abschnitt I/3 des Benchs, Build 221):
        C      = 1,00 ms + 0,0000057 * Punkte
    Der Sprung allein kostet dort also eine Millisekunde. Hier steht
    deshalb nicht nur das Verhaeltnis, sondern auch die Zahl der
    Aufrufe - sie ist auf dem Geraet der teure Teil."""
    import fe.art as A
    import fe.framebuffer as FM
    H.set_screen(1920, 1080)
    fb = FM.Framebuffer()
    fb.text_zeichner = staticmethod(A.texte_zeichnen).__func__
    fg, bg = (220, 224, 232), (16, 18, 24)
    print("== Ein einzelner Streifen (Entwicklungsrechner)")
    print("   %-22s %10s %10s %8s" % ("Fall", "Python", "C", ""))
    for zeichen, scale in ((40, 3), (24, 3), (78, 2), (10, 3), (30, 1),
                           (20, 6)):
        s = ("Dragend " * 20)[:zeichen]

        def py():
            fb._textcache.clear()
            del fb._textcache_order[:]
            fb._text_einmal.clear()
            fb._glyphcache.clear()
            strip = fb._text_strip(s, scale, fg, bg, False)
            w4 = len(strip[0])
            ziel = memoryview(fb.buf)
            for i, row in enumerate(strip):
                off = (20 + i) * fb.stride + 40
                ziel[off:off + w4] = row

        def c():
            fb.text_viele(((10, 20, s, scale, fg, bg),))

        tp, tc = _messen(py), _messen(c)
        punkte = zeichen * 8 * scale * 8 * scale
        print("   %-22s %8.3fms %8.3fms %6.1fx  (%d Punkte, Schwelle %s)"
              % ("%d Zeichen, Groesse %d" % (zeichen, scale), tp, tc,
                 tp / tc if tc else 0, punkte,
                 "ja" if fb._text_nach_c(zeichen, scale) else "nein"))

    print()
    print("== Acht Zeilen (Titel und Datenzeilen unter dem Cover)")
    zeilen = ["The Legend of Zelda - A Link to the Past",
              "Jahr: 1991", "Hersteller: Nintendo", "Spieler: 1",
              "Genre: Action-Adventure", "Bewertung: 9,4 / 10",
              "Dateigroesse: 1,0 MB", "Region: Europa"]
    jobs = [(10, 20 + i * 40, z, 3, fg, bg) for i, z in enumerate(zeilen)]

    def py8():
        fb._textcache.clear()
        del fb._textcache_order[:]
        fb._text_einmal.clear()
        for (x, y, z, sc, f, b) in jobs:
            strip = fb._text_strip(z, sc, f, b, False)
            w4 = len(strip[0])
            ziel = memoryview(fb.buf)
            for i, row in enumerate(strip):
                off = (y + i) * fb.stride + x * 4
                ziel[off:off + w4] = row

    def c8():
        fb.text_viele(jobs)

    tp, tc = _messen(py8, 100), _messen(c8, 100)
    punkte = sum(len(z) for z in zeilen) * 8 * 3 * 8 * 3
    print("   %-22s %8.3fms %8.3fms %6.1fx  (%d Zeichen, %d Punkte)"
          % ("acht Zeilen", tp, tc, tp / tc if tc else 0,
             sum(len(z) for z in zeilen), punkte))
    print("   AUFRUFE NACH C: 8 einzeln gegen 1 gebuendelt - auf dem")
    print("   DE10-Nano sind das 8 ms gegen 1 ms allein an Uebergaengen.")
    print()


def main():
    SCHRITTE = 12
    for res_label, w, h in (("CRT 320x240", 320, 240),
                            ("HDMI 1920x1080", 1920, 1080)):
        H.set_screen(w, h)
        print("== %s" % res_label)
        print("   %-24s %6s %6s %6s %6s %8s %8s %8s"
              % ("Ansicht", "Aufr", "Fens", "Tref", "Fehl",
                 "bauen", "blit", "Zeilen"))
        for seite, seitenname in ((0, "Haupt"), (1, "Liste")):
            for ansicht in ANSICHTEN:
                try:
                    fe = H.make_frontend(seite)
                    if seite == 0:
                        fe.ansicht_haupt_setzen(ansicht)
                    else:
                        fe.ansicht_setzen(ansicht)
                    fe.draw()
                    for _ in range(4):           # warmlaufen
                        _schritt(fe, seite)
                except Exception as e:           # noqa: BLE001
                    print("   %-24s uebersprungen (%s)"
                          % ("%s %s" % (seitenname, ansicht),
                             type(e).__name__))
                    continue
                z = Zaehler()
                echt = _haken(fe.fb, z)
                try:
                    for _ in range(SCHRITTE):
                        _schritt(fe, seite)
                finally:
                    (fe.fb.text, fe.fb.text_window,
                     fe.fb._text_strip) = echt
                n = float(SCHRITTE)
                print("   %-24s %6.1f %6.1f %6.1f %6.1f %7.2fms %7.2fms "
                      "%7.0f"
                      % ("%s %s" % (seitenname, ansicht),
                         z.aufrufe / n, z.fenster / n, z.treffer / n,
                         z.fehl / n, z.t_bauen * 1000 / n,
                         (z.t_gesamt - z.t_bauen) * 1000 / n,
                         z.zeilen / n))
                if z.breiten:
                    print("        Streifen je Groesse: %s"
                          % ", ".join("scale %d bis %d Punkte breit"
                                      % (s, b // 4)
                                      for s, b in sorted(z.breiten.items())))
        print()
    print("Zu lesen als: 'bauen' ist der Textcache (Fehltreffer), 'blit'")
    print("die Schleife in text(). NUR 'blit' liesse sich nach C schieben,")
    print("und nur, wenn die Zahl der AUFRUFE klein genug ist - auf dem")
    print("DE10-Nano kostet ein C-Aufruf rund eine Millisekunde (Build 221).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
