#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
arbeitskopien.py - JPEG-Arbeitskopien fuer vorhandene Cover (Build 129)
=======================================================================
Laeuft auf dem PC (Windows/Linux), NICHT auf dem MiSTer.
Benoetigt Python 3 und Pillow:  pip install Pillow

WOZU
----
"Miniaturen vorbereiten" verkleinert jedes Cover drei Mal (Liste,
Kachel, Galerie-Cover). Die Flaechenmittelung liest dabei JEDEN
Quellpunkt - es zaehlt also, wie gross die Datei ist, aus der gerechnet
wird, nicht wie klein die Kachel am Ende ist.

TurboJPEG kann verkleinert DEKODIEREN (1/2, 1/4, 1/8 direkt aus dem
Dekoder), libpng kann das nicht. Aus einem JPEG ist dieselbe Arbeit
deshalb deutlich billiger. Gemessen an einem 900x1200-Cover mit den
drei HDMI-Kaesten:

    aus dem PNG    689 ms
    aus dem JPEG   416 ms      (40 % weniger)

Seit Build 129 legt der Download diese Arbeitskopie selbst an. Fuer
Cover, die schon auf der Karte liegen, ist dieses Skript da - auf einem
PC dauert das Minuten, auf dem MiSTer Stunden.

WAS ES NICHT TUT
----------------
Es fasst kein Original an. Neben jedem "Spiel.png" entsteht ein
"Spiel.jpg"; das PNG bleibt liegen. Das Frontend bevorzugt ab Build 129
die .jpg (siehe _art_index() in fe/art.py). Wer das rueckgaengig machen
will, loescht die .jpg-Dateien wieder - mehr ist nicht noetig.

Sysart-Abzeichen werden UEBERSPRUNGEN: JPEG kennt keine Transparenz,
und die Abzeichen brauchen ihren durchsichtigen Rand. Dasselbe gilt
fuer jedes PNG, das tatsaechlich transparente Punkte enthaelt - das
wird geprueft, nicht geraten.

AUFRUF
------
  # Erst einmal nur schauen, was passieren wuerde:
  python arbeitskopien.py --ordner "D:\\MiSTer\\frontend\\art" --probe

  # Und dann wirklich:
  python arbeitskopien.py --ordner "D:\\MiSTer\\frontend\\art"

  # Mehrere Ordner, mit mehr Kernen:
  python arbeitskopien.py --ordner art art_hd --jobs 8

Danach den Ordner wie gewohnt per WinSCP auf die Karte kopieren -
oder, wenn er schon dort liegt, direkt auf der gemounteten Karte
laufen lassen.
"""

import argparse
import io
import os
import sys
from concurrent.futures import ThreadPoolExecutor

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow fehlt. Bitte installieren:  pip install Pillow")

# Dieselben Werte wie auf dem Geraet (siehe ARBEITSKOPIE_GUETE und
# TJSAMP_444 in frontend/mister_boxart.py bzw. fe/bildlib.py).
#
# subsampling=0 heisst KEINE Farbunterabtastung. Der uebliche Wert
# waere 4:2:0 - kleinere Dateien, bei Fotos kaum sichtbar. Auf Boxart
# steht aber der Spieltitel, oft farbig auf farbigem Grund, und genau
# dort macht 4:2:0 sichtbare Farbsaeume.
GUETE = 90
SUBSAMPLING = 0

# KEINE Groessenbremse - und das ist eine bewusste Entscheidung, die
# ich zweimal falsch getroffen habe, bevor die Messung sie geklaert hat.
#
# Erster Versuch: "nur schreiben, wenn das JPEG kleiner ist als das
# PNG". Zweiter Versuch: "nur, wenn es hoechstens doppelt so gross ist".
# Beide gehen von der Annahme aus, die Arbeitskopie solle Platz sparen.
# Das tut sie nicht. Sie spart RECHENZEIT, und die haengt an der
# BILDPUNKTZAHL, nicht an der Dateigroesse.
#
# Ein PNG, das sich gut komprimieren laesst, ist klein auf der Karte
# und beim Verkleinern trotzdem genauso teuer wie jedes andere Bild
# derselben Masse. Gerade dort haette eine Groessenbremse die
# Arbeitskopie verhindert - also genau in dem Fall, in dem sie am
# meisten bringt.
#
# Was der Platz kostet, steht stattdessen ehrlich in der Zusammen-
# fassung, und "--probe" sagt es vorher. Wer es nicht will, loescht die
# .jpg-Dateien wieder.


def transparent(bild):
    """Hat dieses Bild wirklich durchsichtige Punkte? Nicht: hat es
    einen Alphakanal.

    Der Unterschied ist wichtig - sehr viele Cover liegen als RGBA vor,
    obwohl jeder Punkt undurchsichtig ist. Wer nur auf den Modus sieht,
    ueberspringt die Haelfte der Sammlung ohne Grund."""
    if bild.mode not in ("RGBA", "LA", "PA") and "transparency" not in bild.info:
        return False
    try:
        alpha = bild.convert("RGBA").getchannel("A")
        return alpha.getextrema()[0] < 255
    except Exception:                                    # noqa: BLE001
        # Im Zweifel als transparent behandeln: lieber eine
        # Arbeitskopie zu wenig als ein Cover mit schwarzem Rand.
        return True


def eine_datei(pfad, probe=False):
    """Rueckgabe: ("neu"|"da"|"transparent"|"fehler", bytes)"""
    ziel = pfad[:-4] + ".jpg"
    if os.path.exists(ziel):
        return ("da", 0)
    try:
        with Image.open(pfad) as bild:
            bild.load()
            if transparent(bild):
                return ("transparent", 0)
            rgb = bild.convert("RGB")
            puffer = io.BytesIO()
            rgb.save(puffer, "JPEG", quality=GUETE, subsampling=SUBSAMPLING,
                     optimize=True)
        daten = puffer.getvalue()
        if probe:
            return ("neu", len(daten))
        # Ueber eine Zwischendatei: ein Abbruch mitten im Schreiben
        # darf keine halbe .jpg hinterlassen, die das Frontend dann
        # bevorzugt und nicht lesen kann.
        tmp = ziel + ".tmp%d" % os.getpid()
        with open(tmp, "wb") as f:
            f.write(daten)
        os.replace(tmp, ziel)
        return ("neu", len(daten))
    except Exception as e:                               # noqa: BLE001
        print("  uebersprungen (%s): %s" % (os.path.basename(pfad), e))
        return ("fehler", 0)


def sammeln(ordner):
    raus = []
    for wurzel, _dirs, dateien in os.walk(ordner):
        # Die Kategorie-Abzeichen bleiben aussen vor - siehe Kopf.
        if os.path.basename(wurzel).lower() == "sysart":
            continue
        for fn in dateien:
            if fn.lower().endswith(".png"):
                raus.append(os.path.join(wurzel, fn))
    return raus


def main():
    p = argparse.ArgumentParser(
        description="JPEG-Arbeitskopien neben vorhandene PNG-Cover legen")
    p.add_argument("--ordner", nargs="+", required=True,
                   help="ein oder mehrere Cover-Ordner (wird durchsucht)")
    p.add_argument("--jobs", type=int, default=4,
                   help="wie viele gleichzeitig (Vorgabe 4)")
    p.add_argument("--probe", action="store_true",
                   help="nur zeigen, was passieren wuerde - nichts schreiben")
    a = p.parse_args()

    dateien = []
    for o in a.ordner:
        if not os.path.isdir(o):
            print("Ordner nicht gefunden: %s" % o)
            continue
        dateien += sammeln(o)
    if not dateien:
        print("Keine PNG-Cover gefunden.")
        return 1

    print("%d PNG-Cover gefunden%s." % (len(dateien),
                                        " (Probelauf)" if a.probe else ""))
    zaehler = {}
    zusatz = 0
    fertig = 0
    with ThreadPoolExecutor(max_workers=max(1, a.jobs)) as pool:
        for art, groesse in pool.map(lambda f: eine_datei(f, a.probe),
                                     dateien):
            zaehler[art] = zaehler.get(art, 0) + 1
            zusatz += groesse
            fertig += 1
            if fertig % 250 == 0 or fertig == len(dateien):
                sys.stdout.write("\r  %d / %d" % (fertig, len(dateien)))
                sys.stdout.flush()
    sys.stdout.write("\n")

    print("")
    print("  neu angelegt : %d" % zaehler.get("neu", 0))
    print("  lagen schon  : %d" % zaehler.get("da", 0))
    print("  transparent  : %d  (bleiben PNG - JPEG kann das nicht)"
          % zaehler.get("transparent", 0))
    print("  Fehler       : %d" % zaehler.get("fehler", 0))
    if zaehler.get("neu"):
        print("")
        print("  zusaetzlich belegt: %.1f MB  (die Originale bleiben liegen)"
              % (zusatz / 1024.0 / 1024.0))
    if a.probe:
        print("")
        print("  (Probelauf - es wurde nichts geschrieben.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
