#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sysart_foto_eigene.py - HD-Kategoriebilder fuer die Sonderkategorien
=====================================================================
(Build 355) Laeuft auf dem PC, NICHT auf dem MiSTer. Benoetigt Pillow
und numpy.

NUTZERWUNSCH: "Beispiele fuer die Kategorien Weiterspielen, Zuletzt
gespielt, Custom Cores, Sammlung, Testarchiv, Zeitmaschine,
Zufalls-Zock, System fuer den HD-Modus ... dort werden ja noch die
alten angezeigt ... der Look passt nicht zu den HD-Bildern von den
Konsolen-Kategorien" - und nach den Entwuerfen: "Wir nehmen die, damit
es besser zusammenpasst."

WAS ENTSTEHT: je Kategorie eine Kachel 420x320 auf C_PANEL - dasselbe
Format wie die Geraetefotos in frontend/sysart_foto (siehe
sysart_foto_convert.py). Ein Gegenstand in Dreiviertelansicht, Licht
von oben links, weicher Schatten darunter, keine Schrift im Bild (bis
auf "FPGA" auf dem Chip und "91%" auf dem Sticker). Gezeichnet wird in
vierfacher Groesse und dann verkleinert, damit die Kanten weich werden
wie bei einem Foto.

ALLES SELBST GEZEICHNET: isometrische Koerper, Verlaeufe, Glanzlichter.
Keine Vorlage, kein fremdes Bild, kein Markenzeichen.

Die drei klassischen Ansichten (Liste, Raster, Galerie) behalten ihre
Abzeichen aus sysart/ - wie bei den Geraetefotos.

Aufruf:
    python3 PC-Tools/sysart_foto_eigene.py --ziel frontend/sysart_foto \
        --vorschau /tmp/eigene_fotos.png
"""
import argparse
import os
import math
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

_HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HIER)
SS = 4
W, H = 420 * SS, 320 * SS
BG = (28, 32, 44)
C30, S30 = math.cos(math.radians(30)), math.sin(math.radians(30))
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def leinwand():
    return Image.new("RGBA", (W, H), BG + (255,))


def mischen(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def heller(c, f):
    return mischen(c, (255, 255, 255), f) if f > 0 else mischen(c, (0, 0, 0), -f)


def verlauf(size, c1, c2, richtung=(0, 1)):
    w, h = size
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    dx, dy = richtung
    t = (xx / max(1, w - 1)) * dx + (yy / max(1, h - 1)) * dy
    t = (t - t.min()) / max(1e-6, t.max() - t.min())
    a = np.array(c1, np.float32)[None, None, :]
    b = np.array(c2, np.float32)[None, None, :]
    rgb = a + (b - a) * t[..., None]
    return Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), "RGB")


def flaeche(bild, punkte, c1, c2=None, richtung=(0, 1)):
    """Polygon mit Verlauf ueber seine Bounding-Box."""
    xs = [p[0] for p in punkte]
    ys = [p[1] for p in punkte]
    x0, y0, x1, y1 = int(min(xs)), int(min(ys)), int(max(xs)) + 1, int(max(ys)) + 1
    maske = Image.new("L", (x1 - x0, y1 - y0), 0)
    ImageDraw.Draw(maske).polygon([(x - x0, y - y0) for x, y in punkte], fill=255)
    farbe = verlauf(maske.size, c1, c2 or c1, richtung)
    bild.paste(farbe, (x0, y0), maske)


def schatten(bild, punkte, versatz=(0, 0), weich=40, staerke=150):
    maske = Image.new("L", (W, H), 0)
    ImageDraw.Draw(maske).polygon([(x + versatz[0], y + versatz[1]) for x, y in punkte], fill=staerke)
    maske = maske.filter(ImageFilter.GaussianBlur(weich))
    dunkel = Image.new("RGBA", (W, H), (8, 10, 16, 255))
    bild.paste(dunkel, (0, 0), maske)


def ellipse_schatten(bild, box, weich=50, staerke=160):
    maske = Image.new("L", (W, H), 0)
    ImageDraw.Draw(maske).ellipse(box, fill=staerke)
    maske = maske.filter(ImageFilter.GaussianBlur(weich))
    bild.paste(Image.new("RGBA", (W, H), (8, 10, 16, 255)), (0, 0), maske)


def glanz(bild, box, staerke=70, weich=20):
    maske = Image.new("L", (W, H), 0)
    ImageDraw.Draw(maske).ellipse(box, fill=staerke)
    maske = maske.filter(ImageFilter.GaussianBlur(weich))
    bild.paste(Image.new("RGBA", (W, H), (255, 255, 255, 255)), (0, 0), maske)


class Iso(object):
    def __init__(self, cx, cy, s):
        self.cx, self.cy, self.s = cx, cy, s

    def p(self, x, y, z):
        return (self.cx + (x - y) * C30 * self.s,
                self.cy + (x + y) * S30 * self.s - z * self.s)


def quader(bild, iso, x, y, z, w, d, h, farbe, oben=None, links=None, rechts=None,
           kante=None):
    P = iso.p
    top = [P(x, y, z + h), P(x + w, y, z + h), P(x + w, y + d, z + h), P(x, y + d, z + h)]
    li = [P(x, y + d, z + h), P(x + w, y + d, z + h), P(x + w, y + d, z), P(x, y + d, z)]
    re = [P(x + w, y, z + h), P(x + w, y + d, z + h), P(x + w, y + d, z), P(x + w, y, z)]
    flaeche(bild, top, heller(oben or farbe, 0.18), heller(oben or farbe, 0.02), (1, 1))
    flaeche(bild, li, heller(links or farbe, -0.05), heller(links or farbe, -0.28))
    flaeche(bild, re, heller(rechts or farbe, -0.30), heller(rechts or farbe, -0.48))
    if kante:
        d_ = ImageDraw.Draw(bild)
        d_.line([top[1], top[2], top[3]], fill=kante, width=max(2, SS))
        d_.line([top[2], li[2]], fill=kante, width=max(2, SS))
    return top, li, re


def textur(bild, tex, o, u, v):
    """tex (RGBA) auf das Parallelogramm o + a*u + b*v legen."""
    tw, th = tex.size
    a, b = u[0] / tw, v[0] / th
    c, d = u[1] / tw, v[1] / th
    det = a * d - b * c
    ia, ib, ic, id_ = d / det, -b / det, -c / det, a / det
    xs = [o[0], o[0] + u[0], o[0] + v[0], o[0] + u[0] + v[0]]
    ys = [o[1], o[1] + u[1], o[1] + v[1], o[1] + u[1] + v[1]]
    x0, y0 = int(min(xs)), int(min(ys))
    x1, y1 = int(max(xs)) + 1, int(max(ys)) + 1
    ox, oy = o[0] - x0, o[1] - y0
    daten = (ia, ib, -(ia * ox + ib * oy), ic, id_, -(ic * ox + id_ * oy))
    t2 = tex.transform((x1 - x0, y1 - y0), Image.AFFINE, daten, Image.BICUBIC)
    bild.alpha_composite(t2, (x0, y0))


def fertig(bild, name):
    klein = bild.convert("RGB").resize((420, 320), Image.LANCZOS)
    # Die Ecken MUESSEN genau C_PANEL sein (das Frontend blittet die
    # Kachel undurchsichtig) - nach dem Verkleinern einmal nachsehen.
    for xy in ((0, 0), (419, 0), (0, 319), (419, 319)):
        if klein.getpixel(xy) != BG:
            raise SystemExit("%s: Ecke %r ist %r statt %r"
                             % (name, xy, klein.getpixel(xy), BG))
    return klein


# ----------------------------------------------------------------------
def weiterspielen():
    b = leinwand()
    iso = Iso(W * 0.47, H * 0.54, 2.45 * SS)
    ellipse_schatten(b, (W * 0.18, H * 0.62, W * 0.80, H * 0.86))
    # Modul, schraeg im Schacht einer flachen Konsole
    quader(b, iso, -40, -26, -12, 80, 52, 12, (70, 74, 84), kante=(40, 42, 50))
    P = iso.p
    flaeche(b, [P(-18, -26, 0), P(18, -26, 0), P(18, -18, 0), P(-18, -18, 0)], (20, 22, 28))
    top, li, re = quader(b, iso, -16, -24, 0, 32, 5, 34, (150, 152, 160))
    lab = verlauf((320, 220), (255, 120, 60), (120, 60, 220), (1, 1)).convert("RGBA")
    ImageDraw.Draw(lab).rectangle((0, 0, 319, 219), outline=(240, 240, 245, 255), width=8)
    textur(b, lab, P(-12, -19, 30), (P(12, -19, 30)[0] - P(-12, -19, 30)[0], P(12, -19, 30)[1] - P(-12, -19, 30)[1]),
           (P(-12, -19, 10)[0] - P(-12, -19, 30)[0], P(-12, -19, 10)[1] - P(-12, -19, 30)[1]))
    # Play-Knopf, glaenzend
    cx, cy, r = W * 0.70, H * 0.64, 46 * SS
    ellipse_schatten(b, (cx - r, cy - r * 0.4 + r * 0.9, cx + r, cy + r * 1.3), weich=30)
    kreis = Image.new("L", (W, H), 0)
    ImageDraw.Draw(kreis).ellipse((cx - r, cy - r, cx + r, cy + r), fill=255)
    b.paste(verlauf((W, H), (90, 230, 120), (20, 140, 60)), (0, 0), kreis)
    d = ImageDraw.Draw(b)
    d.polygon([(cx - r * 0.32, cy - r * 0.45), (cx - r * 0.32, cy + r * 0.45), (cx + r * 0.48, cy)],
              fill=(255, 255, 255, 255))
    glanz(b, (cx - r * 0.8, cy - r * 0.9, cx + r * 0.5, cy - r * 0.2), 90, 12 * SS)
    return fertig(b, "weiterspielen")


def zuletzt():
    b = leinwand()
    ellipse_schatten(b, (W * 0.12, H * 0.66, W * 0.84, H * 0.92))
    farben = [(200, 60, 60), (60, 110, 210), (240, 180, 40)]
    for i, f in enumerate(farben):
        iso = Iso(W * (0.32 + i * 0.10), H * (0.74 - i * 0.03), 2.05 * SS)
        top, li, re = quader(b, iso, -24, -4, 0, 48, 8, 62, f)
        P = iso.p
        o = P(-24, 4, 60)
        u = (P(24, 4, 60)[0] - o[0], P(24, 4, 60)[1] - o[1])
        v = (P(-24, 4, 2)[0] - o[0], P(-24, 4, 2)[1] - o[1])
        cover = verlauf((300, 380), heller(f, 0.25), heller(f, -0.35), (0.3, 1)).convert("RGBA")
        dc = ImageDraw.Draw(cover)
        dc.rectangle((0, 0, 299, 50), fill=(250, 250, 252, 255))
        dc.ellipse((70, 140, 230, 300), fill=heller(f, 0.6) + (255,))
        textur(b, cover, o, u, v)
    # Uhr davor
    cx, cy, r = W * 0.70, H * 0.70, 46 * SS
    ellipse_schatten(b, (cx - r, cy + r * 0.6, cx + r * 1.1, cy + r * 1.3), weich=30)
    d = ImageDraw.Draw(b)
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(40, 120, 230, 255))
    d.ellipse((cx - r * 0.84, cy - r * 0.84, cx + r * 0.84, cy + r * 0.84), fill=(250, 250, 252, 255))
    for k in range(12):
        a = math.radians(k * 30)
        r1, r2 = r * (0.62 if k % 3 else 0.55), r * 0.72
        d.line([(cx + math.cos(a) * r1, cy + math.sin(a) * r1), (cx + math.cos(a) * r2, cy + math.sin(a) * r2)],
               fill=(60, 64, 76, 255), width=3 * SS if k % 3 == 0 else 2 * SS)
    d.line([(cx, cy), (cx, cy - r * 0.55)], fill=(30, 32, 40, 255), width=4 * SS)
    d.line([(cx, cy), (cx - r * 0.38, cy + r * 0.12)], fill=(30, 32, 40, 255), width=5 * SS)
    d.ellipse((cx - 5 * SS, cy - 5 * SS, cx + 5 * SS, cy + 5 * SS), fill=(230, 60, 60, 255))
    # Pfeil zurueck um die Uhr
    d.arc((cx - r * 1.18, cy - r * 1.18, cx + r * 1.18, cy + r * 1.18), 200, 330, fill=(120, 190, 255, 255), width=6 * SS)
    a = math.radians(200)
    px, py = cx + math.cos(a) * r * 1.18, cy + math.sin(a) * r * 1.18
    d.polygon([(px - 14 * SS, py - 2 * SS), (px + 10 * SS, py - 4 * SS), (px - 4 * SS, py + 16 * SS)], fill=(120, 190, 255, 255))
    glanz(b, (cx - r * 0.8, cy - r * 0.9, cx + r * 0.3, cy - r * 0.3), 80, 10 * SS)
    return fertig(b, "zuletzt")


def custom_cores():
    b = leinwand()
    iso = Iso(W * 0.50, H * 0.48, 2.0 * SS)
    ellipse_schatten(b, (W * 0.14, H * 0.60, W * 0.86, H * 0.88))
    top, li, re = quader(b, iso, -46, -46, -6, 92, 92, 6, (24, 110, 60))
    P = iso.p
    d = ImageDraw.Draw(b)
    # Leiterbahnen
    for k in range(-40, 41, 10):
        for (a1, a2) in (((k, -44), (k, -26)), ((k, 26), (k, 44)), ((-44, k), (-26, k)), ((26, k), (44, k))):
            d.line([P(a1[0], a1[1], 0), P(a2[0], a2[1], 0)], fill=(210, 180, 70, 255), width=2 * SS)
    # Chip
    quader(b, iso, -24, -24, 0, 48, 48, 6, (32, 34, 40))
    for k in range(-20, 21, 5):
        for pts in ((P(k, 24, 3), P(k, 28, 1)), (P(24, k, 3), P(28, k, 1))):
            d.line(pts, fill=(225, 200, 110, 255), width=2 * SS)
    o = P(-20, -20, 6)
    tex = Image.new("RGBA", (400, 400), (0, 0, 0, 0))
    dt = ImageDraw.Draw(tex)
    f = ImageFont.truetype(FONT_B, 110)
    dt.text((200, 200), "FPGA", font=f, fill=(150, 154, 166, 255), anchor="mm")
    dt.ellipse((40, 40, 80, 80), fill=(90, 94, 104, 255))
    textur(b, tex, o, (P(20, -20, 6)[0] - o[0], P(20, -20, 6)[1] - o[1]),
           (P(-20, 20, 6)[0] - o[0], P(-20, 20, 6)[1] - o[1]))
    # Leuchten
    gl = Image.new("L", (W, H), 0)
    ImageDraw.Draw(gl).polygon([P(-24, -24, 6), P(24, -24, 6), P(24, 24, 6), P(-24, 24, 6)], fill=90)
    gl = gl.filter(ImageFilter.GaussianBlur(30 * SS))
    b.paste(Image.new("RGBA", (W, H), (60, 220, 255, 255)), (0, 0), gl)
    return fertig(b, "custom_cores")


def sammlung():
    b = leinwand()
    iso = Iso(W * 0.50, H * 0.60, 1.9 * SS)
    ellipse_schatten(b, (W * 0.10, H * 0.62, W * 0.90, H * 0.92))
    quader(b, iso, -60, -14, -6, 124, 30, 6, (120, 84, 52))
    farben = [(210, 50, 50), (40, 90, 200), (240, 190, 40), (40, 160, 90), (150, 60, 200), (230, 120, 40), (60, 60, 70)]
    x = -58
    for i, f in enumerate(farben):
        h = 54 + (i * 7) % 12
        dicke = 14 if i % 3 else 18
        quader(b, iso, x, -12, 0, dicke, 26, h, f, links=f, rechts=heller(f, -0.1))
        P = iso.p
        d = ImageDraw.Draw(b)
        d.line([P(x + 2, 14, h - 8), P(x + dicke - 2, 14, h - 8)], fill=(255, 255, 255, 200), width=3 * SS)
        x += dicke + 2
    return fertig(b, "sammlung")


def testarchiv():
    b = leinwand()
    ellipse_schatten(b, (W * 0.12, H * 0.62, W * 0.88, H * 0.92))
    farben = [(200, 50, 50), (40, 100, 200), (240, 170, 40)]
    for i, f in enumerate(farben):
        iso = Iso(W * 0.48 + i * 7 * SS, H * 0.56 - i * 14 * SS, 2.7 * SS)
        quader(b, iso, -30, -40, 0, 60, 80, 4, (240, 238, 232))
        P = iso.p
        o = P(-30, -40, 4)
        tex = Image.new("RGBA", (300, 400), (246, 244, 238, 255))
        dt = ImageDraw.Draw(tex)
        dt.rectangle((0, 0, 299, 70), fill=f + (255,))
        dt.rectangle((20, 90, 280, 260), fill=heller(f, 0.45) + (255,))
        dt.ellipse((150, 120, 250, 220), fill=heller(f, -0.3) + (255,))
        for y in range(280, 380, 22):
            dt.rectangle((20, y, 200 + (y % 3) * 25, y + 8), fill=(150, 150, 160, 255))
        textur(b, tex, o, (P(30, -40, 4)[0] - o[0], P(30, -40, 4)[1] - o[1]),
               (P(-30, 40, 4)[0] - o[0], P(-30, 40, 4)[1] - o[1]))
    # Wertungs-Sticker
    cx, cy, r = W * 0.68, H * 0.34, 44 * SS
    d = ImageDraw.Draw(b)
    zacken = []
    for k in range(32):
        a = math.radians(k * 360 / 32)
        rr = r if k % 2 == 0 else r * 0.86
        zacken.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
    ellipse_schatten(b, (cx - r, cy - r + 14 * SS, cx + r, cy + r + 14 * SS), weich=18, staerke=120)
    d.polygon(zacken, fill=(220, 40, 40, 255))
    f = ImageFont.truetype(FONT_B, 30 * SS)
    d.text((cx, cy), "91%", font=f, fill=(255, 255, 255, 255), anchor="mm")
    glanz(b, (cx - r * 0.7, cy - r * 0.85, cx + r * 0.2, cy - r * 0.35), 60, 8 * SS)
    return fertig(b, "testarchiv")


def zeitmaschine():
    b = leinwand()
    cx, cy = W * 0.50, H * 0.50
    # Wirbel dahinter
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    dx, dy = (xx - cx) / (W * 0.5), (yy - cy) / (W * 0.5)
    rr = np.sqrt(dx * dx + dy * dy) + 1e-3
    a = np.arctan2(dy, dx)
    band = np.sin(a * 3 + 6.0 / (rr * 6 + 0.5)) * 0.5 + 0.5
    hell = np.clip(1.05 - rr * 1.75, 0, 1) * (0.45 + 0.55 * band)
    farbe = np.stack([60 + 120 * band, 70 + 60 * band, 200 + 50 * band], -1)
    rgb = np.array(BG, np.float32) * (1 - hell[..., None]) + farbe * hell[..., None]
    b = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
    # Taschenuhr, leicht gekippt
    r = 100 * SS
    ellipse_schatten(b, (cx - r * 0.9, cy + r * 0.7, cx + r * 1.1, cy + r * 1.2), weich=30)
    d = ImageDraw.Draw(b)
    box = (cx - r, cy - r * 0.92, cx + r, cy + r * 0.92)
    rand = Image.new("L", (W, H), 0)
    ImageDraw.Draw(rand).ellipse(box, fill=255)
    b.paste(verlauf((W, H), (255, 225, 120), (170, 110, 20), (1, 1)), (0, 0), rand)
    innen = (cx - r * 0.82, cy - r * 0.75, cx + r * 0.82, cy + r * 0.75)
    d.ellipse(innen, fill=(250, 246, 234, 255))
    d.ellipse((cx - r * 0.20, cy - r * 1.08, cx + r * 0.20, cy - r * 0.90), outline=(220, 180, 70, 255), width=6 * SS)
    d.rectangle((cx - r * 0.10, cy - r * 0.98, cx + r * 0.10, cy - r * 0.88), fill=(230, 190, 80, 255))
    f = ImageFont.truetype(FONT_B, 16 * SS)
    for k in range(12):
        a_ = math.radians(k * 30 - 90)
        px, py = cx + math.cos(a_) * r * 0.64, cy + math.sin(a_) * r * 0.58
        d.text((px, py), str(12 if k == 0 else k), font=f, fill=(60, 50, 40, 255), anchor="mm")
    d.line([(cx, cy), (cx, cy - r * 0.48)], fill=(40, 34, 28, 255), width=4 * SS)
    d.line([(cx, cy), (cx - r * 0.33, cy - r * 0.18)], fill=(40, 34, 28, 255), width=6 * SS)
    d.ellipse((cx - 6 * SS, cy - 6 * SS, cx + 6 * SS, cy + 6 * SS), fill=(200, 60, 60, 255))
    glanz(b, (cx - r * 0.8, cy - r * 0.8, cx + r * 0.1, cy - r * 0.3), 90, 14 * SS)
    return fertig(b, "zeitmaschine")


def zufallszock():
    b = leinwand()
    ellipse_schatten(b, (W * 0.14, H * 0.62, W * 0.86, H * 0.90))

    def wuerfel(iso, s, farbe, augen_oben, augen_li, augen_re):
        top, li, re = quader(b, iso, -s, -s, 0, 2 * s, 2 * s, 2 * s, farbe)
        P = iso.p
        def aug(face, n):
            tex = Image.new("RGBA", (300, 300), (0, 0, 0, 0))
            dt = ImageDraw.Draw(tex)
            pos = {1: [(150, 150)], 2: [(80, 80), (220, 220)], 3: [(75, 75), (150, 150), (225, 225)],
                   4: [(80, 80), (220, 80), (80, 220), (220, 220)],
                   5: [(80, 80), (220, 80), (150, 150), (80, 220), (220, 220)],
                   6: [(80, 70), (220, 70), (80, 150), (220, 150), (80, 230), (220, 230)]}[n]
            for (x, y) in pos:
                dt.ellipse((x - 30, y - 30, x + 30, y + 30), fill=(255, 255, 255, 255) if farbe != (245, 245, 248) else (200, 30, 40, 255))
            o, u, v = face
            textur(b, tex, o, u, v)
        def fv(a, bb, c):
            return (a, (bb[0] - a[0], bb[1] - a[1]), (c[0] - a[0], c[1] - a[1]))
        aug(fv(P(-s, -s, 2 * s), P(s, -s, 2 * s), P(-s, s, 2 * s)), augen_oben)
        aug(fv(P(-s, s, 2 * s), P(s, s, 2 * s), P(-s, s, 0)), augen_li)
        aug(fv(P(s, -s, 2 * s), P(s, s, 2 * s), P(s, -s, 0)), augen_re)
    wuerfel(Iso(W * 0.40, H * 0.58, 2.4 * SS), 18, (210, 30, 40), 5, 3, 2)
    wuerfel(Iso(W * 0.62, H * 0.68, 2.2 * SS), 16, (245, 245, 248), 6, 1, 4)
    return fertig(b, "zufallszock")


def system():
    b = leinwand()
    ellipse_schatten(b, (W * 0.14, H * 0.66, W * 0.86, H * 0.92))

    def zahnrad(cx, cy, r, zaehne, c1, c2, loch=0.35):
        pts = []
        n = zaehne * 4
        for k in range(n):
            a = 2 * math.pi * k / n
            rr = r if (k % 4) in (1, 2) else r * 0.80
            pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr * 0.80))
        m = Image.new("L", (W, H), 0)
        dm = ImageDraw.Draw(m)
        dm.polygon(pts, fill=255)
        dm.ellipse((cx - r * loch, cy - r * loch * 0.8, cx + r * loch, cy + r * loch * 0.8), fill=0)
        # Dicke: dunkler Unterbau
        m2 = Image.new("L", (W, H), 0)
        ImageDraw.Draw(m2).polygon([(x, y + 14 * SS) for x, y in pts], fill=255)
        b.paste(Image.new("RGBA", (W, H), heller(c2, -0.35) + (255,)), (0, 0), m2)
        b.paste(verlauf((W, H), c1, c2, (1, 1)), (0, 0), m)
        ring = Image.new("L", (W, H), 0)
        ImageDraw.Draw(ring).ellipse((cx - r * 0.62, cy - r * 0.5, cx + r * 0.62, cy + r * 0.5), outline=90, width=5 * SS)
        b.paste(Image.new("RGBA", (W, H), (255, 255, 255, 255)), (0, 0), ring.filter(ImageFilter.GaussianBlur(2 * SS)))
    zahnrad(W * 0.40, H * 0.46, 105 * SS, 10, (220, 224, 232), (110, 116, 130))
    zahnrad(W * 0.68, H * 0.62, 62 * SS, 8, (120, 190, 255), (40, 90, 190))
    glanz(b, (W * 0.24, H * 0.18, W * 0.44, H * 0.30), 60, 12 * SS)
    return fertig(b, "system")


# Kategorie-Schluessel (fe/art._category_art_key) -> Motiv
MOTIVE = (("CONTINUE", weiterspielen), ("RECENT", zuletzt),
          ("CUSTOM_CORES", custom_cores), ("COLLECTIONS", sammlung),
          ("TESTARCHIV", testarchiv), ("ZEITMASCHINE", zeitmaschine),
          ("ZUFALLSZOCK", zufallszock), ("SYSTEM", system))


def main(argv=None):
    p = argparse.ArgumentParser(
        description="HD-Kategoriebilder fuer die Sonderkategorien")
    p.add_argument("--ziel", default="frontend/sysart_foto")
    p.add_argument("--vorschau", default=None)
    a = p.parse_args(argv)
    if not os.path.isdir(a.ziel):
        sys.exit("Zielordner fehlt: %s" % a.ziel)
    import sysart_karten as K
    fertig_ = []
    for schluessel, motiv in MOTIVE:
        bild = motiv()
        n = K.schreiben(bild, os.path.join(a.ziel, schluessel + ".art"))
        print("%-18s 420x320  %.1f KB" % (schluessel + ".art", n / 1024.0))
        fertig_.append(bild)
    if a.vorschau:
        bogen = Image.new("RGB", (420 * 4, 320 * 2), BG)
        for i, im in enumerate(fertig_):
            bogen.paste(im, ((i % 4) * 420, (i // 4) * 320))
        bogen.save(a.vorschau)
        print("Vorschau: %s" % a.vorschau)


if __name__ == "__main__":
    main()
