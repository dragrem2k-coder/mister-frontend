#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
art_convert.py - Boxart-Konverter fuer das MiSTer-Frontend
===========================================================
Laeuft auf dem PC (Windows/Linux), NICHT auf dem MiSTer.
Benoetigt Python 3 und Pillow:  pip install Pillow

Wandelt PNG/JPG-Boxart in das kompakte .art-Format um, das das
Frontend ohne Bildbibliothek direkt in den Framebuffer kopieren kann.
Die Bilder werden dabei passend zur Zielaufloesung vorskaliert.

Aufruf-Beispiele (PowerShell):

  # CRT-Profil (klein), SNES:
  python art_convert.py --images "D:\\boxart\\SNES" --roms "D:\\roms\\SNES" ^
      --out "out\\art\\SNES" --profile sd

  # HDMI-Profil (gross):
  python art_convert.py --images "D:\\boxart\\SNES" --roms "D:\\roms\\SNES" ^
      --out "out\\art\\SNES" --profile hd

Der Inhalt von out\\art\\ wird danach per WinSCP nach
/media/fat/frontend/art/ kopiert (Ordnername = Systemkey,
z.B. art/SNES/, art/NES/, art/PSX/ ...).

Zuordnung: Ein Bild passt zu einem ROM, wenn der Dateiname (ohne
Endung) uebereinstimmt - Gross-/Kleinschreibung egal. Ohne --roms
werden einfach alle Bilder im Ordner konvertiert.

Boxart-Quelle-Tipp: https://thumbnails.libretro.com
("Named_Boxarts" pro System herunterladen - die Dateinamen folgen
der No-Intro-Konvention und passen damit zu ueblichen ROM-Sets).
"""

import argparse, os, struct, sys, zlib

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow fehlt. Bitte installieren:  pip install Pillow")

# NEU (siehe ausfuehrliche Begruendung in frontend/mister_boxart.py -
# per echter Hardware-Diagnose bestaetigt: kleinere Quelldateien lesen
# spuerbar schneller von der SD-Karte UND treffen bei typischen 1080p-
# Boxgroessen den Sprung auf Skalierungsfaktor 2x, was die Box sogar
# BESSER ausfuellt als die bisherigen 360x420 (die dort meist bei 1x
# blieben, kein tatsaechliches Hochskalieren).
# NEU (siehe ausfuehrliche Begruendung in frontend/mister_boxart.py -
# nachgerechnet statt "aggressiver" geraten: das CRT-Boxart-Panel ist
# rechnerisch nie groesser als ~101x165px, 104x168 deckt das mit kleiner
# Marge ab, ohne unnoetig ueber den Bildschirm hinaus aufzuloesen).
PROFILES = {
    "sd": (104, 168),   # max Breite x Hoehe fuer CRT-Modi (240 Zeilen)
    "hd": (300, 350),   # max Breite x Hoehe fuer 1080p
}

IMG_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}

def find_images(folder):
    out = {}
    for dirpath, _dirs, files in os.walk(folder):
        for fn in files:
            base, ext = os.path.splitext(fn)
            if ext.lower() in IMG_EXT:
                out.setdefault(base.lower(), os.path.join(dirpath, fn))
    return out

def find_rom_names(folder):
    names = set()
    for dirpath, _dirs, files in os.walk(folder):
        for fn in files:
            base, _ext = os.path.splitext(fn)
            names.add(base)
    return names

def convert(img_path, out_path, box):
    """Bild proportional in die Begrenzungsbox (max_w, max_h) einpassen."""
    max_w, max_h = box
    img = Image.open(img_path).convert("RGB")
    scale = min(max_w / img.width, max_h / img.height)
    w = max(1, round(img.width * scale))
    h = max(1, round(img.height * scale))
    img = img.resize((w, h), Image.LANCZOS)
    rgb = img.tobytes()
    pix = bytearray(len(rgb) // 3 * 4)
    pix[0::4] = rgb[2::3]
    pix[1::4] = rgb[1::3]
    pix[2::4] = rgb[0::3]
    data = (b"ART1" + struct.pack("<HH", w, h)
            + zlib.compress(bytes(pix), 9))
    with open(out_path, "wb") as f:
        f.write(data)
    return w, h, len(data)

def make_bg(img_path, out_path, size, darken):
    """Hintergrundbild: auf Zielaufloesung zuschneiden (cover),
    abdunkeln und als .art speichern."""
    tw, th = size
    img = Image.open(img_path).convert("RGB")
    scale = max(tw / img.width, th / img.height)
    w = max(1, round(img.width * scale))
    h = max(1, round(img.height * scale))
    img = img.resize((w, h), Image.LANCZOS)
    x0 = (w - tw) // 2
    y0 = (h - th) // 2
    img = img.crop((x0, y0, x0 + tw, y0 + th))
    img = img.point(lambda v: int(v * darken))
    rgb = img.tobytes()
    pix = bytearray(len(rgb) // 3 * 4)
    pix[0::4] = rgb[2::3]
    pix[1::4] = rgb[1::3]
    pix[2::4] = rgb[0::3]
    with open(out_path, "wb") as f:
        f.write(b"ART1" + struct.pack("<HH", tw, th)
                + zlib.compress(bytes(pix), 9))
    print("Hintergrund: %s -> %s (%dx%d, %d%% Helligkeit)"
          % (img_path, out_path, tw, th, int(darken * 100)))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", required=True,
                    help="Ordner mit Boxart - oder bei --bg EINE Bilddatei")
    ap.add_argument("--out", required=True, help="Zielordner fuer .art")
    ap.add_argument("--bg", action="store_true",
                    help="Hintergrundbild-Modus: EIN Bild -> EIN .art")
    ap.add_argument("--size", default="320x240",
                    help="Zielaufloesung fuer --bg, z.B. 320x240 oder 1920x1080")
    ap.add_argument("--darken", type=float, default=0.30,
                    help="Helligkeit des Hintergrunds 0..1 (Standard 0.30)")
    ap.add_argument("--roms", help="ROM-Ordner: nur passende Bilder wandeln")
    ap.add_argument("--profile", choices=PROFILES, default="sd",
                    help="sd = CRT (klein), hd = 1080p (gross)")
    ap.add_argument("--height", type=int,
                    help="max. Bildhoehe manuell (ueberschreibt --profile)")
    args = ap.parse_args()

    if args.bg:
        tw, th = (int(x) for x in args.size.lower().split("x"))
        make_bg(args.images, args.out, (tw, th), args.darken)
        return

    box = (args.height, args.height) if args.height else PROFILES[args.profile]
    os.makedirs(args.out, exist_ok=True)
    images = find_images(args.images)
    print("%d Bilder gefunden in %s" % (len(images), args.images))

    if args.roms:
        roms = find_rom_names(args.roms)
        print("%d ROMs gefunden in %s" % (len(roms), args.roms))
        todo = [(name, images[name.lower()])
                for name in sorted(roms) if name.lower() in images]
        missing = [name for name in sorted(roms)
                   if name.lower() not in images]
    else:
        todo = [(base, path) for base, path in sorted(images.items())]
        missing = []

    ok = err = 0
    for name, path in todo:
        out_path = os.path.join(args.out, name + ".art")
        try:
            w, h, size = convert(path, out_path, box)
            ok += 1
        except Exception as e:
            print("FEHLER bei %s: %s" % (name, e))
            err += 1
    print("Fertig: %d konvertiert, %d Fehler" % (ok, err))
    if missing:
        print("Ohne Artwork (%d):" % len(missing))
        for name in missing[:25]:
            print("  -", name)
        if len(missing) > 25:
            print("  ... und %d weitere" % (len(missing) - 25))

if __name__ == "__main__":
    main()
