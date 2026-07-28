#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
video_to_bootanim.py - Boot-Animation fuer das MiSTer-Frontend erzeugen
=========================================================================
Laeuft auf dem PC (nicht auf dem MiSTer). Benoetigt Python 3 + Pillow:
    pip install Pillow

Wandelt entweder ein Video (braucht zusaetzlich ffmpeg im PATH) oder
einen Ordner bereits extrahierter Einzelbilder in eine Sequenz von
.art-Dateien um, die das Frontend beim naechsten MiSTer-Boot einmalig
als kleine "Boot-Animation" abspielt, bevor das normale Menue erscheint.

Das .art-Format ist dasselbe wie bei Boxart/Hintergrundbildern:
4 Byte Kennung "ART1" + Breite/Hoehe (je 2 Byte) + zlib-komprimierte
BGRA-Rohpixel - das Frontend braucht dafuer keine Bildbibliothek.

WICHTIG - bewusst kurz halten:
  Jedes Frame wird auf dem MiSTer in reinem Python dekodiert und in
  den Framebuffer kopiert. Das ist fuer ein paar Sekunden Animation
  voellig ausreichend schnell, aber keine Videowiedergabe im
  eigentlichen Sinn. Empfehlung: 2-4 Sekunden, 8-12 Bilder/Sekunde,
  also insgesamt ca. 20-40 Einzelbilder. Laenger geht, dauert dann
  aber auch beim Hochfahren entsprechend laenger.

Aufruf-Beispiele (PowerShell):

  # Aus einem Video (braucht ffmpeg im PATH), 3 Sekunden bei 10 fps,
  # passend fuer den CRT-Menuemodus (320x240):
  python video_to_bootanim.py --video intro.mp4 --out bootanim_out ^
      --fps 10 --duration 3 --size 320x240

  # Aus einem Ordner mit bereits vorliegenden Einzelbildern
  # (z.B. frame001.png, frame002.png, ... - alphabetische Reihenfolge):
  python video_to_bootanim.py --frames-dir meine_frames --out bootanim_out ^
      --fps 12 --size 1920x1080

Ergebnis (den KOMPLETTEN Inhalt von bootanim_out) per WinSCP nach
/media/fat/frontend/bootanim/ kopieren.
"""

import argparse, glob, json, os, shutil, struct, subprocess, sys, tempfile, zlib

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow fehlt. Bitte installieren:  pip install Pillow")

IMG_EXT = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}


def convert_frame(img_path, out_path, box):
    """Ein Bild formatfuellend (letterboxed, keine Verzerrung) auf die
    Zielgroesse bringen und als .art speichern - identisch zum Format
    von art_convert.py, damit dieselbe Frontend-Logik es lesen kann."""
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


def extract_with_ffmpeg(video_path, tmp_dir, fps, duration):
    """Frames per ffmpeg aus dem Video ziehen (nur PC-seitig noetig -
    der MiSTer selbst braucht KEIN ffmpeg, nur die fertigen .art-Dateien)."""
    if shutil.which("ffmpeg") is None:
        sys.exit(
            "ffmpeg wurde nicht gefunden (im PATH gesucht).\n"
            "Entweder ffmpeg installieren (z.B. https://ffmpeg.org/download.html)\n"
            "oder stattdessen --frames-dir mit bereits extrahierten Bildern nutzen.")
    pattern = os.path.join(tmp_dir, "raw_%05d.png")
    cmd = ["ffmpeg", "-y", "-i", video_path, "-vf", "fps=%s" % fps]
    if duration:
        cmd += ["-t", str(duration)]
    cmd += [pattern]
    print("Extrahiere Frames per ffmpeg ...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit("ffmpeg-Fehler:\n" + result.stderr[-2000:])
    frames = sorted(glob.glob(os.path.join(tmp_dir, "raw_*.png")))
    if not frames:
        sys.exit("ffmpeg hat keine Frames erzeugt - Video-Pfad/Format pruefen.")
    return frames


def main():
    ap = argparse.ArgumentParser()
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--video", help="Video-Datei (braucht ffmpeg im PATH)")
    src.add_argument("--frames-dir",
                     help="Ordner mit bereits extrahierten Einzelbildern "
                          "(alphabetische Reihenfolge = Wiedergabereihenfolge)")
    ap.add_argument("--out", required=True, help="Zielordner fuer die .art-Sequenz")
    ap.add_argument("--size", default="320x240",
                    help="Zielaufloesung, z.B. 320x240 (CRT) oder 1920x1080 (HDMI)")
    ap.add_argument("--fps", type=float, default=10,
                    help="Bilder pro Sekunde beim Abspielen (Standard: 10)")
    ap.add_argument("--duration", type=float, default=None,
                    help="Nur bei --video: Laenge in Sekunden ab Videostart "
                         "(Standard: ganzes Video - fuer eine Boot-Animation "
                         "meist 2-4s empfohlen)")
    args = ap.parse_args()

    tw, th = (int(x) for x in args.size.lower().split("x"))
    os.makedirs(args.out, exist_ok=True)

    tmp_dir = None
    try:
        if args.video:
            tmp_dir = tempfile.mkdtemp(prefix="bootanim_")
            frames = extract_with_ffmpeg(args.video, tmp_dir,
                                        args.fps, args.duration)
        else:
            frames = sorted(
                p for p in glob.glob(os.path.join(args.frames_dir, "*"))
                if os.path.splitext(p)[1].lower() in IMG_EXT)
            if not frames:
                sys.exit("Keine Bilder in %s gefunden." % args.frames_dir)

        print("%d Frames werden konvertiert (Ziel: %dx%d) ..."
              % (len(frames), tw, th))
        total_bytes = 0
        for i, path in enumerate(frames, 1):
            out_path = os.path.join(args.out, "frame_%04d.art" % i)
            w, h, size = convert_frame(path, out_path, (tw, th))
            total_bytes += size
            if i % 10 == 0 or i == len(frames):
                print("  %d/%d konvertiert" % (i, len(frames)))

        with open(os.path.join(args.out, "bootanim.json"), "w") as f:
            json.dump({"fps": args.fps}, f)

        print("\nFertig: %d Frames, %.1f MB gesamt, %.1f Sekunden Laufzeit"
              % (len(frames), total_bytes / (1024 * 1024), len(frames) / args.fps))
        print("Naechster Schritt: kompletten Ordner '%s' per WinSCP nach"
              % args.out)
        print("/media/fat/frontend/bootanim/ auf den MiSTer kopieren.")
    finally:
        if tmp_dir:
            shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
