#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Der Rueckfall ueber /dev/mem (Build 168).

WORUM ES GEHT

Das MiSTer-Linux-Update vom 07.09.2026 hebt den Kernel von 5.15.1 auf
6.18.x. Der Treiber MiSTer_fb ist seither mit den System-Memory-
Helfern registriert, obwohl sein Speicher in einem iomem/CMA-Bereich
liegt, der nicht im virtuellen Adressraum des Kernels steht. Im Log
eines betroffenen Geraets steht:

    fb0: sys_fillrect: framebuffer is not in virtual address space.

Der Treiber bringt keine eigene mmap-Funktion mehr mit. Console Mode
meldet danach "Unable to memory map the video hardware", Degauss
startete gar nicht mehr und musste denselben Rueckfall einbauen: die
vom Treiber GEMELDETE physische Adresse ueber /dev/mem einblenden.

EHRLICH: auf dem Geraet, an dem unser Fehler gemeldet wurde, ging das
normale Einblenden weiterhin (das Frontend war sichtbar). Dieser
Rueckfall repariert also nicht den dort beobachteten Fehler, sondern
ist Vorsorge fuer Geraete, auf denen es hart scheitert.

WAS DIESER TEST PRUEFT

Weil sich hier kein echter Framebuffer nachbauen laesst, wird die
LOGIK geprueft - und zwar die Faelle, in denen der Rueckfall NICHT
losgehen darf. Das ist der gefaehrliche Teil: eine falsch berechnete
Adresse gaebe ein um ein paar Bytes verschobenes Bild, und das sieht
aus wie ein Grafikfehler, obwohl es keiner ist.

Ausfuehren:
    python3 tools/test_dev_mem_rueckfall.py
"""
import io
import mmap
import os
import struct
import sys

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
sys.path.insert(0, os.path.join(_REPO, "frontend"))

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


import fe.framebuffer as FB                              # noqa: E402

FBK = FB.Framebuffer


class Attrappe(object):
    """Gerade so viel Framebuffer, wie _map_ueber_dev_mem() anfasst."""

    def __init__(self, smem_start, smem_len, size, ioctl_geht=True):
        self.fd = -1
        self.fbdev = "/dev/fb0"
        self.size = size
        self._smem = (smem_start, smem_len)
        self._ioctl_geht = ioctl_geht
        self._mem_fd = None
        self.geoeffnet = []

    # Die beiden Methoden, um die es geht - unveraendert aus der
    # echten Klasse geholt.
    _map = FBK._map
    _map_ueber_dev_mem = FBK._map_ueber_dev_mem


def mit_attrappe(fn):
    """fcntl.ioctl und os.open fuer die Dauer eines Aufrufs ersetzen."""
    def lauf(att):
        echt_ioctl, echt_open, echt_mmap = FB.fcntl.ioctl, FB.os.open, FB.mmap.mmap

        def fake_ioctl(fd, req, buf, mutate=False):
            if not att._ioctl_geht:
                raise OSError(25, "Inappropriate ioctl")
            struct.pack_into("<II", buf, 16, *att._smem)
            return 0

        def fake_open(pfad, flags):
            att.geoeffnet.append(pfad)
            return 4242

        def fake_mmap(fd, laenge, flags, prot, offset=0):
            att.mmap_args = (fd, laenge, offset)
            return "EINGEBLENDET"

        FB.fcntl.ioctl, FB.os.open, FB.mmap.mmap = (fake_ioctl, fake_open,
                                                    fake_mmap)
        try:
            return fn(att)
        finally:
            FB.fcntl.ioctl, FB.os.open, FB.mmap.mmap = (echt_ioctl, echt_open,
                                                        echt_mmap)
    return lauf


SEITE = mmap.PAGESIZE
GROESSE = 1920 * 4 * 1080

# ---------------------------------------------------------------------------
print("Test 1: der gute Fall - ausgerichtete Adresse, genug Platz")
# ---------------------------------------------------------------------------
att = Attrappe(0x22000000, GROESSE, GROESSE)
ergebnis = mit_attrappe(lambda a: a._map_ueber_dev_mem())(att)
check("es wird eingeblendet", ergebnis == "EINGEBLENDET")
check("und zwar ueber /dev/mem", att.geoeffnet == ["/dev/mem"],
      str(att.geoeffnet))
check("mit der gemeldeten Adresse als Versatz",
      att.mmap_args[2] == 0x22000000, hex(att.mmap_args[2]))
check("und der gebrauchten Laenge", att.mmap_args[1] == GROESSE)
check("der Dateizeiger wird gemerkt (zum Schliessen)",
      att._mem_fd == 4242)

# ---------------------------------------------------------------------------
print()
print("Test 2: DIE WICHTIGEN FAELLE - wann NICHT eingeblendet wird")
# ---------------------------------------------------------------------------
# Eine nicht seitenausgerichtete Adresse waere ein um Bytes
# verschobenes Bild. Lieber laut abbrechen als leise falsch zeichnen.
att = Attrappe(0x22000000 + 17, GROESSE, GROESSE)
try:
    mit_attrappe(lambda a: a._map_ueber_dev_mem())(att)
    check("nicht ausgerichtete Adresse wird abgelehnt", False)
except OSError as e:
    check("nicht ausgerichtete Adresse wird abgelehnt", True)
    check("und die Begruendung nennt den Grund",
          "ausgerichtet" in str(e), str(e))
check("dabei wurde /dev/mem gar nicht erst geoeffnet",
      att.geoeffnet == [], str(att.geoeffnet))

# Keine Adresse -> kein Rueckfall moeglich.
att = Attrappe(0, GROESSE, GROESSE)
try:
    mit_attrappe(lambda a: a._map_ueber_dev_mem())(att)
    check("fehlende Adresse wird abgelehnt", False)
except OSError as e:
    check("fehlende Adresse wird abgelehnt", "physische Adresse" in str(e),
          str(e))

# Zu kleiner Bereich -> wir wuerden ueber das Ende hinausschreiben.
att = Attrappe(0x22000000, GROESSE // 2, GROESSE)
try:
    mit_attrappe(lambda a: a._map_ueber_dev_mem())(att)
    check("zu kleiner gemeldeter Bereich wird abgelehnt", False)
except OSError as e:
    check("zu kleiner gemeldeter Bereich wird abgelehnt",
          "gebraucht" in str(e), str(e))

# smem_len = 0 heisst "keine Angabe", nicht "null Bytes".
att = Attrappe(0x22000000, 0, GROESSE)
ergebnis = mit_attrappe(lambda a: a._map_ueber_dev_mem())(att)
check("smem_len 0 gilt als 'keine Angabe', nicht als Fehler",
      ergebnis == "EINGEBLENDET")

# Kein FBIOGET_FSCREENINFO -> sauberer Fehler, kein Absturz.
att = Attrappe(0x22000000, GROESSE, GROESSE, ioctl_geht=False)
try:
    mit_attrappe(lambda a: a._map_ueber_dev_mem())(att)
    check("fehlendes ioctl wird abgefangen", False)
except OSError as e:
    check("fehlendes ioctl wird abgefangen",
          "FBIOGET_FSCREENINFO" in str(e), str(e))

# ---------------------------------------------------------------------------
print()
print("Test 3: der normale Weg hat Vorrang - auf dem alten Kernel "
      "aendert sich NICHTS")
# ---------------------------------------------------------------------------
att = Attrappe(0x22000000, GROESSE, GROESSE)
echt_mmap = FB.mmap.mmap
versuche = []


def mmap_geht(fd, laenge, flags, prot, offset=0):
    versuche.append(("fb", offset))
    return "NORMAL"


FB.mmap.mmap = mmap_geht
try:
    att._map()
finally:
    FB.mmap.mmap = echt_mmap
check("bei funktionierendem mmap wird /dev/mem nie angefasst",
      att.geoeffnet == [] and att.mm == "NORMAL", str(att.geoeffnet))
check("der Zeichenpuffer wird trotzdem angelegt",
      isinstance(att.buf, bytearray) and len(att.buf) == GROESSE)
check("und kein /dev/mem-Zeiger bleibt zurueck", att._mem_fd is None)

# ---------------------------------------------------------------------------
print()
print("Test 4: bei einem Fehlschlag wird umgeschaltet")
# ---------------------------------------------------------------------------
att = Attrappe(0x22000000, GROESSE, GROESSE)
zaehler = {"n": 0}


def mmap_erst_fehler(fd, laenge, flags, prot, offset=0):
    zaehler["n"] += 1
    if zaehler["n"] == 1:
        raise OSError(19, "No such device")     # ENODEV
    att.mmap_args = (fd, laenge, offset)
    return "UEBER_MEM"


echt_ioctl, echt_open = FB.fcntl.ioctl, FB.os.open


def fake_ioctl(fd, req, buf, mutate=False):
    struct.pack_into("<II", buf, 16, 0x22000000, GROESSE)
    return 0


FB.mmap.mmap, FB.fcntl.ioctl, FB.os.open = (
    mmap_erst_fehler, fake_ioctl, lambda p, f: att.geoeffnet.append(p) or 7)
try:
    att._map()
finally:
    FB.mmap.mmap, FB.fcntl.ioctl, FB.os.open = echt_mmap, echt_ioctl, echt_open
check("nach ENODEV wird ueber /dev/mem eingeblendet",
      att.mm == "UEBER_MEM")
check("und /dev/mem wurde genau einmal geoeffnet",
      att.geoeffnet == ["/dev/mem"], str(att.geoeffnet))

# ---------------------------------------------------------------------------
print()
print("Test 5: das Sondierungswerkzeug ist vollstaendig")
# ---------------------------------------------------------------------------
# Das Werkzeug liegt unter frontend/, nicht unter tools/:
# nur von dort nehmen die Installer es mit (sie kopieren
# frontend/*.py), und genau dort braucht es der Nutzer -
# auf dem Geraet, nicht im Arbeitsverzeichnis.
probe = os.path.join(_REPO, "frontend", "kernel_probe.py")
check("frontend/kernel_probe.py liegt im Repo", os.path.exists(probe))
check("und wird von den Installern mitgenommen (frontend/*.py)",
      "frontend/*.py" in io.open(
          os.path.join(_REPO, "Scripts", "Frontend_Install.sh"),
          encoding="utf-8").read())
if os.path.exists(probe):
    text = io.open(probe, encoding="utf-8").read()
    for was, muster in (("prueft mmap auf /dev/fb0", "mmap auf /dev/fb0"),
                        ("prueft den /dev/mem-Weg", "/dev/mem"),
                        ("prueft das Einspeisen wie heute", "per_evdev"),
                        ("prueft uinput als Alternative", "UI_DEV_CREATE"),
                        ("misst MiSTers Last als Signal", "MISTER_PFAD"),
                        ("laesst den MiSTer im OSD zurueck", "aufraeumen")):
        check(was, muster in text)
    # Es darf messen und Tasten schicken, aber nichts hinterlassen.
    # Geprueft wird das an den Werkzeugen, mit denen man etwas
    # hinterlaesst - nicht an Pfaden im Fliesstext.
    import re as _re
    schreibend = _re.findall(r'open\([^)]*["\'](?:w|a|r\+|w\+)b?["\']', text)
    check("es oeffnet keine Datei zum Schreiben", not schreibend,
          str(schreibend))
    for gefaehrlich in ("os.remove", "os.unlink", "shutil.",
                        "os.makedirs", "os.rename"):
        check("es benutzt kein %s" % gefaehrlich, gefaehrlich not in text)
    import py_compile
    try:
        py_compile.compile(probe, doraise=True)
        check("es laesst sich uebersetzen", True)
    except Exception as e:                               # noqa: BLE001
        check("es laesst sich uebersetzen", False, str(e))

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
