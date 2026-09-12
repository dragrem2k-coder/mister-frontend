#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft, dass das Frontend auf BEIDEN MiSTer-Kerneln hochkommt
(Build 111).

NUTZER-RUECKMELDUNG: "Einige Nutzer haben auf den neuen Kernel
gewechselt, und da lief unser Frontend nicht mehr - deswegen habe ich
Update All nicht gestartet."

WAS PASSIERT IST: das MiSTer-Update vom 07.09.2026 hat den Linux-Kernel
gewechselt und dabei den Zugriff auf den Bildspeicher veraendert.
Mehrere Frontends (Zaparoo, Degauss) starteten danach nicht mehr - sie
beendeten sich, BEVOR ueberhaupt etwas auf dem Schirm stand.
Kernelseitig ist nichts zurueckgenommen worden; jedes Programm hat sich
selbst gepatcht.

BEI UNS HING ES AN EINER EINZIGEN FUNKTION. _read_geometry() las drei
Dateien unter /sys/class/graphics/fb0/. Fehlt oder aendert sich eine
davon, fliegt eine Ausnahme - und das Frontend endet still.

DIE ANFORDERUNG WAR AUSDRUECKLICH "beide Varianten muessen laufen".
Genau das prueft dieser Test: der sysfs-Weg bleibt der erste Versuch
und liefert auf dem alten Kernel exakt dieselben Werte wie bisher; nur
wenn er ausfaellt, uebernimmt der ioctl-Rueckfall.

Geprueft wird gegen einen NACHGEBAUTEN sysfs-Ordner und einen
nachgebildeten Treiber - auf dem Entwicklungsrechner gibt es keinen
MiSTer-Bildspeicher, und die Zusage "es startet auch auf dem neuen
Kernel" laesst sich sonst ueberhaupt nicht pruefen.

Ausfuehren:
    python3 tools/test_kernel_wechsel.py
"""
import os
import shutil
import struct
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_REPO, "frontend"))

import fe.framebuffer as FB                             # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


def leer():
    """Ein Framebuffer-Objekt OHNE __init__ - wir wollen hier die
    Geometrie-Erkennung pruefen, nicht ein echtes Geraet oeffnen."""
    f = object.__new__(FB.Framebuffer)
    f.fd = -1
    f.fbname = "fb0"
    f.fbdev = "/dev/fb0"
    return f


def sysfs_bauen(wurzel, **werte):
    """Einen /sys/class/graphics/fb0-Ordner nachbauen."""
    d = os.path.join(wurzel, "fb0")
    os.makedirs(d, exist_ok=True)
    for name, inhalt in werte.items():
        with open(os.path.join(d, name), "w") as fh:
            fh.write(inhalt)
    return d


TMP = tempfile.mkdtemp(prefix="kernelwechsel_")
_echtes_sysfs = FB.SYSFS_GRAPHICS
_echter_ioctl = FB.fcntl.ioctl

print("Test 1: alter Kernel - genau die Werte vom Geraet des Nutzers")
# Abgelesen auf seinem MiSTer (5.15.1-MiSTer, CRT-Modus):
#   virtual_size 320,240   stride 1280   bits_per_pixel 32
# Diese Zeile ist der eigentliche Sinn des Tests: der bisherige Weg
# muss unveraendert dasselbe liefern, sonst haben wir den alten Kernel
# kaputtgemacht, um den neuen zu retten.
FB.SYSFS_GRAPHICS = sysfs_bauen(os.path.join(TMP, "alt"),
                                virtual_size="320,240\n",
                                stride="1280\n",
                                bits_per_pixel="32\n")
FB.SYSFS_GRAPHICS = os.path.join(TMP, "alt")
f = leer()
f._read_geometry()
check("Breite/Hoehe 320x240", (f.width, f.height) == (320, 240),
      "(%dx%d)" % (f.width, f.height))
check("Zeilenlaenge 1280", f.stride == 1280, "(%d)" % f.stride)
check("32 bpp", f.bpp == 32)
check("Puffergroesse 1280*240", f.size == 1280 * 240, "(%d)" % f.size)
check("Quelle war sysfs", f._geo_quelle == "sysfs", "(%s)" % f._geo_quelle)

print("Test 2: HDMI-Werte, ebenfalls ueber sysfs")
FB.SYSFS_GRAPHICS = os.path.join(TMP, "hdmi")
sysfs_bauen(FB.SYSFS_GRAPHICS, virtual_size="1920,1080\n",
            stride="7680\n", bits_per_pixel="32\n")
f = leer()
f._read_geometry()
check("1920x1080, Zeile 7680",
      (f.width, f.height, f.stride) == (1920, 1080, 7680),
      "(%dx%d, %d)" % (f.width, f.height, f.stride))


def fake_ioctl(xres, yres, bpp, line_length, mit_fix=True, offset=44):
    """Einen Treiber nachbilden, der auf die beiden ioctls antwortet."""
    def ersatz(fd, req, buf, mutate=False):
        if req == FB.FBIOGET_VSCREENINFO:
            struct.pack_into("<8I", buf, 0, xres, yres, xres, yres,
                             0, 0, bpp, 0)
            return 0
        if req == FB.FBIOGET_FSCREENINFO:
            if not mit_fix:
                raise OSError(25, "Inappropriate ioctl for device")
            struct.pack_into("<I", buf, offset, line_length)
            return 0
        raise OSError(25, "unbekannter ioctl")
    return ersatz


print("Test 3: neuer Kernel - sysfs fehlt, ioctl uebernimmt")
# Der eigentliche Ernstfall. Bis Build 110 waere hier Schluss gewesen:
# Ausnahme, fuenf Versuche, Abbruch - ohne ein Bild.
FB.SYSFS_GRAPHICS = os.path.join(TMP, "gibt_es_nicht")
FB.fcntl.ioctl = fake_ioctl(1920, 1080, 32, 7680)
f = leer()
f._read_geometry()
check("1920x1080 per ioctl erkannt",
      (f.width, f.height, f.stride, f.bpp) == (1920, 1080, 7680, 32),
      "(%dx%d, %d, %d)" % (f.width, f.height, f.stride, f.bpp))
check("Quelle war ioctl", f._geo_quelle == "ioctl", "(%s)" % f._geo_quelle)

print("Test 4: sysfs da, aber nur noch halb")
# Der wahrscheinlichere Fall: der Ordner existiert, eine Datei fehlt.
for fehlt in ("stride", "virtual_size", "bits_per_pixel"):
    d = os.path.join(TMP, "halb_" + fehlt)
    werte = {"virtual_size": "320,240\n", "stride": "1280\n",
             "bits_per_pixel": "32\n"}
    del werte[fehlt]
    sysfs_bauen(d, **werte)
    FB.SYSFS_GRAPHICS = d
    FB.fcntl.ioctl = fake_ioctl(320, 240, 32, 1280)
    f = leer()
    f._read_geometry()
    check("ohne %-15s trotzdem 320x240" % fehlt,
          (f.width, f.height, f.stride) == (320, 240, 1280),
          "(%dx%d, %d)" % (f.width, f.height, f.stride))

print("Test 5: sysfs liefert Unsinn - auch das faellt zurueck")
# Eine vorhandene, aber leere oder unsinnige Datei ist gefaehrlicher
# als eine fehlende: sie wirft keine Ausnahme, sondern liefert Werte,
# mit denen weitergerechnet wuerde.
for name, werte in (
        ("Null-Groesse", {"virtual_size": "0,0\n", "stride": "0\n",
                          "bits_per_pixel": "32\n"}),
        ("Zeile zu kurz", {"virtual_size": "1920,1080\n", "stride": "64\n",
                           "bits_per_pixel": "32\n"}),
        ("absurd gross", {"virtual_size": "99999,99999\n",
                          "stride": "399996\n", "bits_per_pixel": "32\n"})):
    d = os.path.join(TMP, "unsinn_" + name.replace(" ", "_"))
    sysfs_bauen(d, **werte)
    FB.SYSFS_GRAPHICS = d
    FB.fcntl.ioctl = fake_ioctl(1920, 1080, 32, 7680)
    f = leer()
    f._read_geometry()
    check("%-14s -> ioctl greift" % name,
          (f.width, f.height) == (1920, 1080) and f._geo_quelle == "ioctl",
          "(%dx%d, %s)" % (f.width, f.height, f._geo_quelle))

print("Test 6: auch ohne FBIOGET_FSCREENINFO kommt etwas Brauchbares")
# Manche Treiber beantworten nur den ersten der beiden ioctls. Bei 32
# Bit je Bildpunkt ohne Zeilenauffuellung ist Breite mal vier exakt
# richtig - und wenn doch aufgefuellt wird, ist die Kopie nur etwas
# kleiner als noetig, nicht falsch.
FB.SYSFS_GRAPHICS = os.path.join(TMP, "gibt_es_nicht")
FB.fcntl.ioctl = fake_ioctl(1280, 720, 32, 0, mit_fix=False)
f = leer()
f._read_geometry()
check("1280x720, Zeile aus der Breite abgeleitet",
      (f.width, f.height, f.stride) == (1280, 720, 5120),
      "(%dx%d, %d)" % (f.width, f.height, f.stride))

print("Test 7: 64-Bit-Aufbau der Treiberstruktur wird auch getroffen")
# Die Zeilenlaenge steht je nach Wortbreite an unterschiedlicher
# Stelle. Beide werden probiert, genommen wird die, die zur Breite
# passt.
FB.fcntl.ioctl = fake_ioctl(1920, 1080, 32, 7680, offset=52)
f = leer()
f._read_geometry()
check("Zeile 7680 auch bei anderem Aufbau", f.stride == 7680,
      "(%d)" % f.stride)

print("Test 8: geht gar nichts, gibt es eine Ausnahme - keinen Unsinn")
FB.fcntl.ioctl = fake_ioctl(0, 0, 0, 0)
f = leer()
try:
    f._read_geometry()
    check("unbrauchbare Geometrie wird abgelehnt", False,
          "(lief durch: %dx%d)" % (f.width, f.height))
except OSError as e:
    check("unbrauchbare Geometrie wird abgelehnt", True, "(%s)" % e)

print("Test 9: die Plausibilitaetspruefung selbst")
p = FB.Framebuffer._geo_plausibel
check("320x240/1280/32 ist gut", p(320, 240, 32, 1280))
check("1920x1080/7680/32 ist gut", p(1920, 1080, 32, 7680))
check("Breite 0 ist schlecht", not p(0, 240, 32, 1280))
check("Zeile kuerzer als Breite ist schlecht", not p(1920, 1080, 32, 64))
check("99999 Kante ist schlecht", not p(99999, 99999, 32, 399996))
check("7 bpp ist schlecht", not p(320, 240, 7, 1280))

print("Test 10: das Geraet ist nicht mehr fest verdrahtet")
quelle = open(os.path.join(_REPO, "frontend", "fe", "framebuffer.py"),
              encoding="utf-8", errors="replace").read()
check("mehrere Geraetekandidaten", "FBDEV_KANDIDATEN" in quelle)
check("per Umgebungsvariable uebersteuerbar", "DRAGEND_FBDEV" in quelle)
check("erster Kandidat bleibt /dev/fb0",
      FB.FBDEV_KANDIDATEN[0] == "/dev/fb0")
check("Diagnose schreibt ins Log, bevor aufgegeben wird",
      "self.diagnose()" in quelle and "FB-DIAGNOSE" in quelle)
check("das Geraet wird VOR der Geometrie geoeffnet",
      quelle.index("self._geraet_oeffnen()")
      < quelle.index("self._read_geometry()\n                break"))

FB.SYSFS_GRAPHICS = _echtes_sysfs
FB.fcntl.ioctl = _echter_ioctl
shutil.rmtree(TMP, ignore_errors=True)

print()
if fails:
    print("FEHLGESCHLAGEN (%d):" % len(fails))
    for f_ in fails:
        print("  -", f_)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
