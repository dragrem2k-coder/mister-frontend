#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
weihnacht_bilder.py - Muetze und Lichterketten-Birnen fuer die
Weihnachts-Deko erzeugen (Build 342)
=====================================================================
Laeuft auf dem PC, NICHT auf dem MiSTer. Benoetigt Pillow.

NUTZERWUNSCH: "schnee sieht ok aus, weihnachtsmuetze sollte am M oben
links haengen und etwas besser gezeichnet aussehen, lichterkette nicht
bunt eher ein weiss gelblicher farbton" - und zur zweiten Runde der
Beispiele: "das ist gut bitte so machen".

WARUM DIE BILDER FERTIG GERECHNET MITKOMMEN
-------------------------------------------
Auf dem MiSTer gibt es kein Pillow, und eine Muetze mit Verlauf,
Glanz, Falte und Pelzrand Punkt fuer Punkt in Python zu zeichnen
kostete dort bei jedem Start eine spuerbare Zeit. Gezeichnet wird
deshalb hier, vierfach ueberabgetastet und verkleinert - genau wie in
den Beispielbildern, die der Nutzer freigegeben hat -, und zwar fuer
jede Skalenstufe des Layouts einmal.

WARUM ALS PYTHON-MODUL UND NICHT ALS .art-DATEIEN
-------------------------------------------------
Die Installations- und Update-Skripte kopieren jeden Bildordner einzeln
(boot_logo, sysart, ...). Ein neuer Ordner hiesse vier Skripte und den
eingebauten Updater anzufassen - und wer ein Skript auslaesst, hat im
Dezember eine Deko ohne Muetze. fe/*.py dagegen kommt auf JEDEM Weg mit.
Das Modul ist rund 120 kB gross und wird nur geladen, wenn die Deko
tatsaechlich gezeichnet wird.

Ausgabe: frontend/fe/weihnacht_bilder.py

Aufruf (im Repo-Hauptordner):
    python PC-Tools/weihnacht_bilder.py
"""
import base64
import math
import os
import random
import zlib

from PIL import Image, ImageChops, ImageDraw, ImageFilter

HIER = os.path.dirname(os.path.abspath(__file__))
ZIEL = os.path.join(os.path.dirname(HIER), "frontend", "fe",
                    "weihnacht_bilder.py")

# Muss zu fe/weihnachten.py passen: Hoehe der hellen Titelschrift
# "MiSTer" (Groesse 3*s) - nachgemessen 20 Punkte bei s=1, 41 bei s=2,
# 62 bei s=3.
SKALEN = (1, 2, 3, 4)
BIRNEN_RADIEN = (1, 2, 3, 4, 5, 6, 7, 8)


def titel_hoehe(s):
    return (62 * s + 1) // 3


def muetze_masse(s):
    """(faktor, winkel) - auf der Roehre (s=1) etwas kleiner, wie im
    freigegebenen Beispiel C."""
    return (1.3, 12) if s <= 1 else (1.55, 12)


# ---------------------------------------------------------------- Muetze
def bezier(p0, p1, p2, n=40):
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1])
            for t in (i / float(n) for i in range(n + 1))]


def muetze_bild(breite):
    """Eine Weihnachtsmuetze als RGBA, 4-fach gezeichnet und verkleinert:
    Koerper mit Verlauf und Glanz, die Spitze kippt nach rechts und haengt
    herunter, Pelzrand und Bommel aus vielen kleinen Kreisen. Dieselbe
    Zeichnung wie im freigegebenen Beispiel (zweite Runde)."""
    S = 4
    W, H = 420 * S, 380 * S
    rnd = random.Random(11)

    def P(x, y):
        return (x * S, y * S)
    umriss = (bezier(P(70, 300), P(85, 140), P(205, 72))
              + bezier(P(205, 72), P(330, 30), P(352, 178))[1:]
              + bezier(P(332, 186), P(300, 120), P(322, 300))[1:])
    maske = Image.new("L", (W, H), 0)
    ImageDraw.Draw(maske).polygon(umriss, fill=255)
    verlauf = Image.new("RGB", (W, H))
    vd = ImageDraw.Draw(verlauf)
    for x in range(W):
        t = x / float(W)
        vd.line((x, 0, x, H), fill=(int(225 - 85 * t), int(38 - 18 * t),
                                    int(48 - 20 * t)))
    koerper = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    koerper.paste(verlauf, (0, 0), maske)
    glanz = Image.new("L", (W, H), 0)
    gd = ImageDraw.Draw(glanz)
    gd.line(bezier(P(120, 285), P(130, 170), P(200, 100)), fill=110,
            width=10 * S)
    glanz = ImageChops.multiply(glanz.filter(ImageFilter.GaussianBlur(9 * S)),
                                maske)
    weiss = Image.new("RGBA", (W, H), (255, 220, 220, 255))
    koerper = Image.composite(weiss, koerper, glanz.point(lambda v: v // 2))
    falte = Image.new("L", (W, H), 0)
    ImageDraw.Draw(falte).line(bezier(P(255, 295), P(262, 190), P(312, 118)),
                               fill=150, width=6 * S)
    falte = ImageChops.multiply(falte.filter(ImageFilter.GaussianBlur(4 * S)),
                                maske)
    dunkel = Image.new("RGBA", (W, H), (110, 12, 22, 255))
    koerper = Image.composite(dunkel, koerper, falte.point(lambda v: v // 2))
    koerper.putalpha(maske)

    bild = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    schatten = Image.new("L", (W, H), 0)
    ImageDraw.Draw(schatten).rounded_rectangle(
        (P(55, 300) + P(360, 352)), radius=26 * S, fill=110)
    schatten = schatten.filter(ImageFilter.GaussianBlur(10 * S))
    bild.paste((0, 0, 0, 255), (0, 0), schatten)
    bild.alpha_composite(koerper)

    def pelz(cx, cy, rx, ry, n, rmin, rmax):
        d = ImageDraw.Draw(bild)
        for _ in range(n):
            a = rnd.uniform(0, 2 * math.pi)
            r = math.sqrt(rnd.uniform(0, 1))
            x = cx + math.cos(a) * rx * r
            y = cy + math.sin(a) * ry * r
            rr = rnd.uniform(rmin, rmax)
            hell = 255 - int(40 * max(0.0, (y - cy) / float(ry)))
            d.ellipse((x - rr, y - rr, x + rr, y + rr),
                      fill=(hell, hell, min(255, hell + 6), 255))
    for i in range(14):
        t = i / 13.0
        cx = (52 + 316 * t) * S
        cy = (302 - 10 * math.sin(math.pi * t)) * S
        pelz(cx, cy, 30 * S, 26 * S, 26, 9 * S, 16 * S)
    pelz(352 * S, 186 * S, 30 * S, 30 * S, 70, 8 * S, 15 * S)
    hoehe = int(breite * H / float(W))
    return bild.resize((breite, hoehe), Image.LANCZOS)


def muetze_fuer(s):
    faktor, winkel = muetze_masse(s)
    breite = int(titel_hoehe(s) * faktor)
    return muetze_bild(breite).rotate(winkel, resample=Image.BICUBIC,
                                      expand=True)


# ---------------------------------------------------------------- Birne
def birne_masse(r):
    """(links, oben, rechts, unten) - wie weit das Bild um den
    Aufhaengepunkt reicht. Seitlich bewusst knapp (6,2 r): der Abstand
    zweier Birnen ist rund 1,5 Bandhoehen, und so ueberlappen sich die
    Lichthoefe nie. Nach unten nur 4 r: der Lichthof laeuft dort sanft
    aus (siehe birne_bild()), und kette_plan() in fe/weihnachten.py
    haengt die Birnen so, dass diese 4 r ueber dem Titel enden - der
    Teil-Neuaufbau der Kopfzeile darf den Lichthof nicht anschneiden."""
    seite = int(math.ceil(6.2 * r))
    return seite, int(math.ceil(4.7 * r)), seite, int(math.ceil(4.0 * r))


def birne_bild(r, hell):
    links, oben, rechts, unten = birne_masse(r)
    S = 4
    w, h = links + rechts + 1, oben + unten + 1
    x, y = (links + 0.5) * S, (oben + 0.5) * S
    rs = r * S
    leuchten = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
    ImageDraw.Draw(leuchten).ellipse(
        (x - rs * 3, y - rs * 1.5, x + rs * 3, y + rs * 4.5),
        fill=(255, 210, 120, int(130 * hell)))
    leuchten = leuchten.filter(ImageFilter.GaussianBlur(rs * 1.6))
    # unten sanft auslaufen lassen: voll bis zum Ende der Birne (2,7 r),
    # null am unteren Bildrand (4 r)
    rampe = Image.new("L", leuchten.size, 255)
    rd = ImageDraw.Draw(rampe)
    voll, null = y + rs * 2.7, h * S
    for yy in range(int(voll), h * S):
        rd.line((0, yy, w * S, yy),
                fill=max(0, int(255 * (null - yy) / float(null - voll))))
    leuchten.putalpha(ImageChops.multiply(leuchten.getchannel("A"), rampe))
    ebene = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(ebene)
    kern = (255, int(232 + 18 * hell), int(178 + 40 * hell))
    # Fassung: ein kleines dunkles Stueck direkt am Draht
    d.rectangle((x - rs * 0.45, y - rs * 0.1, x + rs * 0.45, y + rs * 0.5),
                fill=(70, 64, 52, 255))
    d.ellipse((x - rs, y + rs * 0.3, x + rs, y + rs * 2.7), fill=kern + (255,))
    d.ellipse((x - rs * 0.35, y + rs * 0.6, x + rs * 0.15, y + rs * 1.3),
              fill=(255, 255, 255, 230))
    leuchten.alpha_composite(ebene)
    return leuchten.resize((w, h), Image.LANCZOS), links, oben


# ------------------------------------------------------------ Ausgabe
def kodieren(bild):
    """BGRA mit gerader (nicht vormultiplizierter) Deckkraft. Sehr
    schwache Deckkraft (< 8) wird zu 0 - auf dem Schirm unsichtbar,
    spart aber Rechenarbeit."""
    roh = bytearray(bild.convert("RGBA").tobytes("raw", "BGRA"))
    for i in range(3, len(roh), 4):
        if roh[i] < 8:
            roh[i - 3:i + 1] = b"\x00\x00\x00\x00"
    return base64.b64encode(zlib.compress(bytes(roh), 9)).decode("ascii")


def main():
    eintraege = []
    for s in SKALEN:
        b = muetze_fuer(s)
        eintraege.append(("muetze_%d" % s, b.size[0], b.size[1], 0, 0,
                          kodieren(b)))
    for r in BIRNEN_RADIEN:
        for name, hell in (("a", 1.0), ("b", 0.72)):
            b, ax, ay = birne_bild(r, hell)
            eintraege.append(("birne_%d%s" % (r, name), b.size[0],
                              b.size[1], ax, ay, kodieren(b)))
    zeilen = [
        "# -*- coding: utf-8 -*-",
        '"""Bilder der Weihnachts-Deko (Build 342) - ERZEUGT, nicht von Hand',
        "bearbeiten. Quelle: PC-Tools/weihnacht_bilder.py.",
        "",
        "Je Eintrag: (Breite, Hoehe, Ankerpunkt x, Ankerpunkt y, Daten).",
        "Daten = base64(zlib(BGRA)), Deckkraft gerade im vierten Byte.",
        '"""',
        "",
        "BILDER = {",
    ]
    for name, w, h, ax, ay, daten in eintraege:
        zeilen.append("    %r: (%d, %d, %d, %d, (" % (name, w, h, ax, ay))
        for i in range(0, len(daten), 68):
            zeilen.append("        %r" % daten[i:i + 68])
        zeilen.append("    )),")
    zeilen.append("}")
    with open(ZIEL, "w", newline="\n") as f:
        f.write("\n".join(zeilen) + "\n")
    print("geschrieben: %s (%d Bilder, %d kB)"
          % (ZIEL, len(eintraege), os.path.getsize(ZIEL) // 1024))


if __name__ == "__main__":
    main()
