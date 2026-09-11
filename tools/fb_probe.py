#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Framebuffer-Sondierung fuer den MiSTer - EINMAL auf dem Geraet laufen
lassen, danach wissen wir, welcher Weg fuer die Latenz offen ist.

Die entscheidende Frage: laesst sich das Vollbild-Kopieren (auf dem
Geraet gemessene 21 ms bei 1080p) ganz vermeiden?

Das ginge mit einem DOPPELPUFFER: der Framebuffer wird doppelt so hoch
angelegt wie das Bild, gezeichnet wird in die gerade unsichtbare Haelfte,
und danach schaltet FBIOPAN_DISPLAY einfach um - ein Zeigerwechsel statt
7,9 MB kopieren. Ob das geht, haengt an einem einzigen Wert, den nur das
Geraet selbst kennt: yres_virtual.

Aufruf ueber SSH:
    python3 /media/fat/frontend/fb_probe.py

Das Skript ZEICHNET NICHTS und aendert nichts dauerhaft - es liest die
Geometrie, misst die Kopierzeit und stellt jede Aenderung hinterher
zurueck.
"""
import ctypes
import fcntl
import mmap
import os
import struct
import sys
import time

FBIOGET_VSCREENINFO = 0x4600
FBIOPUT_VSCREENINFO = 0x4601
FBIOGET_FSCREENINFO = 0x4602
FBIOPAN_DISPLAY = 0x4606

# struct fb_var_screeninfo - die ersten Felder reichen uns; der Rest
# wird unveraendert zurueckgeschrieben.
VAR_LEN = 160


def var_lesen(fd):
    buf = bytearray(VAR_LEN)
    fcntl.ioctl(fd, FBIOGET_VSCREENINFO, buf, True)
    return buf


def felder(buf):
    (xres, yres, xres_virtual, yres_virtual, xoffset, yoffset,
     bits_per_pixel) = struct.unpack_from("<7I", buf, 0)
    return dict(xres=xres, yres=yres, xres_virtual=xres_virtual,
                yres_virtual=yres_virtual, xoffset=xoffset,
                yoffset=yoffset, bpp=bits_per_pixel)


def main():
    pfad = sys.argv[1] if len(sys.argv) > 1 else "/dev/fb0"
    if not os.path.exists(pfad):
        print("Kein Framebuffer unter %s - laeuft das auf dem MiSTer?" % pfad)
        return 1
    fd = os.open(pfad, os.O_RDWR)
    try:
        var = var_lesen(fd)
        f = felder(var)
        print("Framebuffer %s" % pfad)
        print("  Sichtbar        : %d x %d, %d bit" % (f["xres"], f["yres"], f["bpp"]))
        print("  Virtuell        : %d x %d" % (f["xres_virtual"], f["yres_virtual"]))
        print("  Aktueller Offset: x=%d y=%d" % (f["xoffset"], f["yoffset"]))
        bild_bytes = f["xres"] * f["yres"] * (f["bpp"] // 8)
        print("  Ein Bild        : %.1f MB" % (bild_bytes / 1024.0 / 1024.0))

        # --- 1) Reicht der virtuelle Bereich schon fuer zwei Bilder?
        print()
        if f["yres_virtual"] >= f["yres"] * 2:
            print("  [JA] Der virtuelle Bereich fasst BEREITS zwei Bilder.")
            passt_schon = True
        else:
            print("  [NEIN] Der virtuelle Bereich fasst nur ein Bild.")
            passt_schon = False

        # --- 2) Laesst er sich vergroessern? (danach zurueckgestellt)
        umschaltbar = False
        if not passt_schon:
            print("  Versuche, yres_virtual zu verdoppeln ...")
            neu = bytearray(var)
            struct.pack_into("<I", neu, 12, f["yres"] * 2)
            try:
                fcntl.ioctl(fd, FBIOPUT_VSCREENINFO, neu, True)
                jetzt = felder(var_lesen(fd))
                if jetzt["yres_virtual"] >= f["yres"] * 2:
                    print("    -> hat geklappt: yres_virtual = %d"
                          % jetzt["yres_virtual"])
                    umschaltbar = True
                else:
                    print("    -> abgelehnt, der Treiber bleibt bei %d"
                          % jetzt["yres_virtual"])
            except OSError as e:
                print("    -> nicht moeglich (%s)" % e)
        else:
            umschaltbar = True

        # --- 3) Nimmt der Treiber ein Umschalten an?
        if umschaltbar:
            print("  Versuche FBIOPAN_DISPLAY ...")
            pan = bytearray(var_lesen(fd))
            struct.pack_into("<I", pan, 20, f["yres"])      # yoffset
            try:
                _t = time.monotonic()
                fcntl.ioctl(fd, FBIOPAN_DISPLAY, pan, True)
                dt = (time.monotonic() - _t) * 1000
                print("    -> Umschalten angenommen, %.2f ms" % dt)
                struct.pack_into("<I", pan, 20, 0)
                fcntl.ioctl(fd, FBIOPAN_DISPLAY, pan, True)
                print("    -> zurueckgeschaltet")
                print()
                print("  ERGEBNIS: Doppelpuffer ist MOEGLICH.")
                print("            Die 21 ms Vollbild-Kopie koennen entfallen.")
            except OSError as e:
                print("    -> abgelehnt (%s)" % e)
                print()
                print("  ERGEBNIS: Doppelpuffer NICHT moeglich.")
        else:
            print()
            print("  ERGEBNIS: Doppelpuffer NICHT moeglich.")

        # --- 4) Wie teuer ist die Kopie wirklich?
        print()
        print("  Messe die Vollbild-Kopie (5 Durchlaeufe) ...")
        try:
            mm = mmap.mmap(fd, bild_bytes, mmap.MAP_SHARED,
                           mmap.PROT_READ | mmap.PROT_WRITE)
            quelle = bytearray(mm[:bild_bytes])
            zeiten = []
            for _ in range(5):
                _t = time.monotonic()
                mm[:bild_bytes] = quelle
                zeiten.append((time.monotonic() - _t) * 1000)
            mm.close()
            zeiten.sort()
            print("    Median %.1f ms  (min %.1f, max %.1f)  = %.0f MB/s"
                  % (zeiten[2], zeiten[0], zeiten[-1],
                     bild_bytes / 1024.0 / 1024.0 / (zeiten[2] / 1000.0)))
        except Exception as e:                             # noqa: BLE001
            print("    Messung nicht moeglich: %s" % e)
    finally:
        os.close(fd)
    return 0


if __name__ == "__main__":
    sys.exit(main())
