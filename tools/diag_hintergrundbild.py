#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Warum dauert das Durchklicken der Hintergrundbilder so lange?
(Build 240)

DER ANLASS ist eine Meldung vom Geraet:

    "wenn ich mehrere background bilder in denn ordner packe und diese
     dann durchklicke dauert das immer sehr lang bis es angezeigt wird.
     werden diese noch vorbereitet? und jedesmal neu?"

Die zweite Frage beantwortet der Quelltext mit ja: hintergrund_bauen()
geht bei JEDEM Klick den ganzen Weg - Datei lesen, dekodieren,
skalieren, mittig zuschneiden, abdunkeln. Es gibt keinen Ort, an dem
das Ergebnis liegenbleibt.

DIESES WERKZEUG ZERLEGT DIESEN WEG in seine vier Teile, damit die
Abhilfe an der richtigen Stelle ansetzt und nicht an der, die man
zuerst vermutet. Die Teile sind sehr verschieden teuer, und einer
davon ist eine Python-Schleife ueber JEDES BYTE des fertigen Bildes -
bei 1920x1080 sind das 8,3 Millionen.

Gemessen wird auf diesem Rechner. Auf dem DE10-Nano ist alles
Rechnen je Bildpunkt ein Vielfaches teurer (Abschnitt C des Bench
nennt fuer dieselbe Arbeit in Python Faktor 126 gegenueber C).

Ausfuehren:
    python3 tools/diag_hintergrundbild.py
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H          # noqa: E402

import fe.art as ART          # noqa: E402
import fe.hintergrund as HG   # noqa: E402

_uhr = time.perf_counter      # der Pruefstand friert monotonic() ein

BREITE, HOEHE = 1920, 1080
RUNDEN = 3

# So gross sind Hintergrundbilder, die Leute wirklich ablegen: ein
# Wallpaper in Full HD, und eines in 4K (das kommt von jeder
# Bildersuche).
QUELLEN = ((1920, 1080, "Full HD, passt genau"),
           (3840, 2160, "4K, muss verkleinert werden"),
           (1280, 800, "kleiner als der Schirm"))


def _median(w):
    return sorted(w)[len(w) // 2]


def _testbild(breite, hoehe):
    """Ein Bild mit Struktur - kein einfarbiges, das sich zu gut
    packen laesst."""
    pix = bytearray(breite * hoehe * 4)
    for y in range(hoehe):
        z = y * breite * 4
        for x in range(0, breite * 4, 4):
            pix[z + x] = (x + y) & 0xFF
            pix[z + x + 1] = (x * 3 + y * 7) & 0xFF
            pix[z + x + 2] = (x // 4 + y * 2) & 0xFF
            pix[z + x + 3] = 255
    return bytes(pix)


def _teile_messen(qb, qh, pix):
    """Den Weg von vorlage_bauen() in seine vier Teile zerlegen."""
    zeiten = {}

    # 1) Skalieren auf Bildschirmfuellung
    zb, zh = HG._fuellend(qb, qh, BREITE, HOEHE)
    laeufe = []
    skaliert = pix
    for _ in range(RUNDEN):
        t0 = _uhr()
        if (zb, zh) != (qb, qh):
            skaliert = ART._verkleinern(pix, qb, qh, zb, zh)
        laeufe.append((_uhr() - t0) * 1000.0)
    zeiten["skalieren"] = _median(laeufe)

    # 2) Mittig zuschneiden (die Zeilenschleife)
    x0 = (zb - BREITE) // 2
    y0 = (zh - HOEHE) // 2
    zeile = BREITE * 4
    laeufe = []
    vorlage = None
    for _ in range(RUNDEN):
        t0 = _uhr()
        quelle = memoryview(skaliert)
        vorlage = bytearray(zeile * HOEHE)
        ziel = memoryview(vorlage)
        for y in range(HOEHE):
            s = ((y0 + y) * zb + x0) * 4
            ziel[y * zeile:y * zeile + zeile] = quelle[s:s + zeile]
        del ziel, quelle
        laeufe.append((_uhr() - t0) * 1000.0)
    zeiten["zuschneiden"] = _median(laeufe)

    # 3) Abdunkeln
    laeufe = []
    for _ in range(RUNDEN):
        t0 = _uhr()
        HG._abdunkeln(vorlage, 40)
        laeufe.append((_uhr() - t0) * 1000.0)
    zeiten["abdunkeln"] = _median(laeufe)
    return zeiten, len(vorlage)


def _ganzer_weg():
    """Der ganze Weg, wie ihn ein Klick geht - einmal kalt, einmal mit
    abgelegter Vorlage. DAS ist die Zahl, die der Nutzer merkt."""
    import tempfile
    import fe.bench as B

    print(" EIN KLICK, GANZER WEG (das, was der Nutzer merkt)")
    alt = HG.VORLAGEN_DIR
    with tempfile.TemporaryDirectory() as tmp:
        HG.VORLAGEN_DIR = os.path.join(tmp, "cache")
        bild = os.path.join(tmp, "wallpaper.png")
        # Ein echtes PNG in Full HD - so gross, wie Leute sie ablegen.
        pix = _testbild(1920, 1080)
        try:
            with open(bild, "wb") as f:
                f.write(B.testbild_png(pix, 1920, 1080))
        except Exception as e:                           # noqa: BLE001
            print("    uebersprungen (%s)" % type(e).__name__)
            HG.VORLAGEN_DIR = alt
            return
        kb = os.path.getsize(bild) // 1024
        print("    Quelle: %d KB PNG, 1920x1080" % kb)
        try:
            t0 = _uhr()
            erst = HG.vorlage_bauen(bild, BREITE, HOEHE, 40, ART=ART,
                                    stride=BREITE * 4)
            kalt = (_uhr() - t0) * 1000.0
            HG.vorlagen_fertig_abwarten(60.0)
            laeufe = []
            for _ in range(RUNDEN):
                t0 = _uhr()
                HG.vorlage_bauen(bild, BREITE, HOEHE, 40, ART=ART,
                                 stride=BREITE * 4)
                laeufe.append((_uhr() - t0) * 1000.0)
            warm = _median(laeufe)
            dateien = [n for n in os.listdir(HG.VORLAGEN_DIR)
                       if n.endswith(".bgv")]
            vkb = (os.path.getsize(os.path.join(HG.VORLAGEN_DIR,
                                                dateien[0])) // 1024
                   if dateien else 0)
            print("    erster Klick (nichts liegt da)     %8.1f ms"
                  % kalt)
            print("    jeder weitere (Vorlage liegt da)   %8.1f ms"
                  "   -> %.1fx" % (warm, kalt / max(0.001, warm)))
            print("    abgelegte Vorlage: %d KB (%s)"
                  % (vkb, "JPEG" if dateien else "keine"))
            print("    (die Vorlage ist %.1f MB roh)"
                  % ((len(erst) if erst else 0) / 1048576.0))
        except Exception as e:                           # noqa: BLE001
            print("    uebersprungen (%s: %s)" % (type(e).__name__, e))
    HG.VORLAGEN_DIR = alt
    print("")


def main():
    print("=" * 70)
    print(" Warum dauert das Durchklicken der Hintergrundbilder?"
          " - Ziel %dx%d" % (BREITE, HOEHE))
    print("=" * 70)
    print(" Gezeigt wird der Weg, den JEDER Klick heute komplett geht.")
    print(" Das Dekodieren der Datei steht nicht dabei - es haengt am")
    print(" Format und ist in Abschnitt C/D des Bench gemessen (PNG")
    print(" lesen und dekodieren: 258 ms auf dem Geraet).")
    print("")

    for qb, qh, was in QUELLEN:
        print(" QUELLE %dx%d - %s" % (qb, qh, was))
        t0 = _uhr()
        pix = _testbild(qb, qh)
        bau = (_uhr() - t0) * 1000.0
        try:
            zeiten, groesse = _teile_messen(qb, qh, pix)
        except Exception as e:                           # noqa: BLE001
            print("    uebersprungen (%s: %s)" % (type(e).__name__, e))
            print("")
            continue
        summe = sum(zeiten.values())
        for name in ("skalieren", "zuschneiden", "abdunkeln"):
            ms = zeiten[name]
            print("    %-14s %8.1f ms  (%4.1f %% des Wegs)"
                  % (name, ms, 100.0 * ms / max(0.001, summe)))
        print("    %-14s %8.1f ms  fertige Vorlage %.1f MB"
              % ("zusammen", summe, groesse / 1048576.0))
        print("    (Testbild erzeugt in %.0f ms - nicht Teil des Wegs)"
              % bau)
        print("")

    _ganzer_weg()

    print("=" * 70)
    print(" Zu lesen als: steht EIN Teil fuer den Grossteil der Zeit,")
    print(" ist dort anzusetzen. Und die zweite Frage des Nutzers")
    print(" ('jedesmal neu?') ist die wichtigere: was einmal gerechnet")
    print(" ist, muss beim zweiten Klick nicht wieder gerechnet werden.")
    print("=" * 70)


if __name__ == "__main__":
    main()
