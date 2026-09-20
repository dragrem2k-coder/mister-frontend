#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Was hat sich mit Kernel 6.18 geaendert? - Messen statt raten.

WARUM ES DIESES WERKZEUG GIBT

Das MiSTer-Linux-Update vom 07.09.2026 hebt den Kernel von 5.15.1 auf
6.18.x. Danach kam ein Nutzer beim Beenden des Frontends nicht mehr
ins MiSTer-OSD zurueck, und das Boot-Logo war nicht mehr zu sehen -
obwohl das Log bewies, dass es vollstaendig gezeichnet wurde.

Ich habe daraufhin vier Builds lang im Frontend gesucht. Falsch: der
Rueckbau auf Kernel 5.15.1 hat alles sofort repariert, ohne eine
einzige Zeile am Frontend. Es lag nie an uns.

Das ist kein Einzelfall. Im MiSTer-Forum steht zu diesem Update
woertlich "Front Ends have to be patched due to framebuffer changes";
Degauss, das Zaparoo-Frontend und Console Mode mussten alle gepatcht
werden.

DAMIT DAS NICHT NOCH EINMAL PASSIERT

Dieses Skript laeuft OHNE das Frontend und beantwortet in zwei
Minuten die Fragen, fuer die ich sonst wieder raten muesste:

  1. Laesst sich der Bildspeicher noch wie bisher einblenden
     (mmap auf /dev/fb0)? Wenn nein - geht es ueber /dev/mem?
  2. Erreicht eine eingespeiste Taste MiSTer ueberhaupt noch?
     Das Frontend schreibt sie in das Geraet einer vorhandenen
     Tastatur zurueck. Ob der Kernel das noch weiterreicht, ist
     eine Kernel-Eigenschaft, keine Frontend-Eigenschaft.
  3. Falls nicht: kommt sie ueber ein EIGENES Eingabegeraet an
     (uinput) - der uebliche, unterstuetzte Weg?

GEMESSEN WIRD AN MISTERS CPU-LAST. Das ist das Signal aus Build 152:
zeichnet MiSTer sein eigenes Menue, laeuft er auf Anschlag (gemessen
100 %); liegt der Linux-Bildspeicher oben, schlaeft er (1,4 %).
Dazwischen ist eine Luecke, in die jede Schwelle passt.

    F9  soll die Last SENKEN  (Konsole/unser Bild kommt nach vorn)
    F12 soll die Last HEBEN   (MiSTers OSD kommt nach vorn)

Passiert beides nicht, ist die Taste nicht angekommen.

BENUTZUNG

    Frontend beenden (oder: touch /media/fat/frontend/disable
    und neu starten), dann per SSH:

        python3 /media/fat/frontend/kernel_probe.py

    Das Skript laesst den MiSTer am Ende im OSD zurueck.

Es aendert NICHTS dauerhaft: kein Schreiben auf die SD-Karte, keine
Einstellung, keine Datei. Nur lesen, messen und ein paar Tasten.
"""
import errno
import fcntl
import mmap
import os
import struct
import sys
import time

# --------------------------------------------------------------------
# Konstanten - dieselben wie im Frontend, hier bewusst noch einmal
# ausgeschrieben. Das Skript soll auch dann laufen, wenn vom Frontend
# gar nichts (mehr) installiert ist.
# --------------------------------------------------------------------
FBIOGET_VSCREENINFO = 0x4600
FBIOGET_FSCREENINFO = 0x4602

EV_SYN, EV_KEY = 0x00, 0x01
KEY_F9, KEY_F12 = 67, 88
EVENT_FMT = "llHHi"
EVENT_SIZE = struct.calcsize(EVENT_FMT)

UI_SET_EVBIT = 0x40045564
UI_SET_KEYBIT = 0x40045565
UI_DEV_CREATE = 0x5501
UI_DEV_DESTROY = 0x5502

MISTER_PFAD = "/media/fat/MiSTer"
MESSFENSTER = 1.2          # Sekunden je Lastmessung
NACH_TASTE = 1.0           # so lange wirken lassen, bevor gemessen wird
SCHWELLE = 25.0            # ab hier gilt MiSTer als "zeichnet sein OSD"

befunde = []


def sagen(text=""):
    print(text)
    sys.stdout.flush()


def titel(text):
    sagen()
    sagen("=" * 68)
    sagen(text)
    sagen("=" * 68)


# --------------------------------------------------------------------
# Teil 1: Umgebung
# --------------------------------------------------------------------
def umgebung():
    titel("1. Was fuer ein System ist das?")
    try:
        sagen("Kernel:  " + open("/proc/version").read().strip())
    except OSError as e:
        sagen("Kernel:  nicht lesbar (%s)" % e)
    try:
        fbs = sorted(n for n in os.listdir("/dev") if n.startswith("fb"))
        sagen("/dev/fb*: %s" % (fbs or "KEINE"))
    except OSError as e:
        sagen("/dev/fb*: nicht lesbar (%s)" % e)
    sagen("/dev/uinput vorhanden: %s" % os.path.exists("/dev/uinput"))
    # Die Kernel-Meldung, an der man dieses Update erkennt.
    try:
        import subprocess
        roh = subprocess.run(["dmesg"], capture_output=True, text=True,
                             timeout=10).stdout
        treffer = [z for z in roh.splitlines()
                   if "fb" in z.lower() and ("virtual address" in z
                                             or "MiSTer_fb" in z)]
        for z in treffer[-6:]:
            sagen("dmesg:   " + z.strip())
        if any("not in virtual address space" in z for z in treffer):
            befunde.append("Der Kernel meldet 'framebuffer is not in "
                           "virtual address space' - das ist die Signatur "
                           "des Updates vom 07.09.2026.")
    except Exception as e:                               # noqa: BLE001
        sagen("dmesg:   nicht lesbar (%s)" % e)


# --------------------------------------------------------------------
# Teil 2: Bildspeicher
# --------------------------------------------------------------------
def framebuffer():
    titel("2. Laesst sich der Bildspeicher noch einblenden?")
    try:
        fd = os.open("/dev/fb0", os.O_RDWR)
    except OSError as e:
        sagen("/dev/fb0 laesst sich nicht oeffnen: %s" % e)
        befunde.append("/dev/fb0 ist nicht zu oeffnen - ohne das geht "
                       "gar nichts.")
        return
    try:
        roh = bytearray(160)
        fcntl.ioctl(fd, FBIOGET_VSCREENINFO, roh, True)
        xres, yres, _xv, _yv, _xo, _yo, bpp, _g = struct.unpack_from("<8I", roh)
        sagen("Geometrie per ioctl: %dx%d, %d bpp" % (xres, yres, bpp))

        fix = bytearray(160)
        smem_start = smem_len = stride = 0
        try:
            fcntl.ioctl(fd, FBIOGET_FSCREENINFO, fix, True)
            # fb_fix_screeninfo: char id[16]; unsigned long smem_start;
            # __u32 smem_len; ... Auf 32-Bit-ARM ist unsigned long
            # vier Bytes gross.
            smem_start, smem_len = struct.unpack_from("<II", fix, 16)
            for off in (44, 52):
                k = struct.unpack_from("<I", fix, off)[0]
                if xres * (bpp // 8) <= k <= 8192 * 4:
                    stride = k
                    break
            sagen("smem_start = 0x%08X, smem_len = %d, stride = %d"
                  % (smem_start, smem_len, stride))
        except OSError as e:
            sagen("FBIOGET_FSCREENINFO nicht verfuegbar: %s" % e)

        groesse = (stride or xres * 4) * yres
        # --- Weg 1: wie bisher ---
        try:
            mm = mmap.mmap(fd, groesse, mmap.MAP_SHARED,
                           mmap.PROT_READ | mmap.PROT_WRITE)
            mm[0:4] = mm[0:4]          # ein echter Schreibzugriff
            mm.close()
            sagen("mmap auf /dev/fb0:        GEHT")
        except Exception as e:                           # noqa: BLE001
            nummer = getattr(e, "errno", None)
            sagen("mmap auf /dev/fb0:        GEHT NICHT (%s%s)"
                  % (e, " / ENODEV" if nummer == errno.ENODEV else ""))
            befunde.append("mmap auf /dev/fb0 schlaegt fehl (%s) - das "
                           "Frontend braucht den /dev/mem-Rueckfall." % e)
            # --- Weg 2: der Rueckfall, den Degauss gebaut hat ---
            if smem_start:
                try:
                    mfd = os.open("/dev/mem", os.O_RDWR | os.O_SYNC)
                    seite = mmap.PAGESIZE
                    basis = smem_start - (smem_start % seite)
                    versatz = smem_start - basis
                    mm = mmap.mmap(mfd, groesse + versatz, mmap.MAP_SHARED,
                                   mmap.PROT_READ | mmap.PROT_WRITE,
                                   offset=basis)
                    mm.close()
                    os.close(mfd)
                    sagen("mmap ueber /dev/mem:      GEHT")
                    befunde.append("Der /dev/mem-Rueckfall funktioniert - "
                                   "genau dieser Weg gehoert ins Frontend.")
                except Exception as e2:                  # noqa: BLE001
                    sagen("mmap ueber /dev/mem:      GEHT AUCH NICHT (%s)" % e2)
                    befunde.append("Auch /dev/mem geht nicht (%s) - hier "
                                   "hilft nur der alte Kernel." % e2)
            else:
                sagen("mmap ueber /dev/mem:      nicht versucht "
                      "(kein smem_start)")
    finally:
        os.close(fd)


# --------------------------------------------------------------------
# Teil 3: MiSTers Last als Anzeige-Signal
# --------------------------------------------------------------------
class Last(object):
    """MiSTers CPU-Last in Prozent - das Anzeige-Signal aus Build 152."""

    def __init__(self):
        self.pid = None
        try:
            self.tck = os.sysconf("SC_CLK_TCK") or 100
        except (ValueError, OSError):
            self.tck = 100
        self._suchen()

    def _suchen(self):
        try:
            eintraege = os.listdir("/proc")
        except OSError:
            return
        for d in eintraege:
            if not d.isdigit():
                continue
            try:
                with open("/proc/%s/cmdline" % d, "rb") as f:
                    roh = f.read().decode("utf-8", "replace")
            except OSError:
                continue
            if roh.split("\0")[0] == MISTER_PFAD:
                self.pid = d
                return

    def _zeit(self):
        with open("/proc/%s/stat" % self.pid) as f:
            felder = f.read().rsplit(")", 1)[1].split()
        return (float(felder[11]) + float(felder[12])) / self.tck

    def messen(self, fenster=MESSFENSTER):
        if self.pid is None:
            return None
        try:
            t0, z0 = time.monotonic(), self._zeit()
            time.sleep(fenster)
            t1, z1 = time.monotonic(), self._zeit()
        except (OSError, IndexError, ValueError):
            return None
        return (z1 - z0) / (t1 - t0) * 100.0


# --------------------------------------------------------------------
# Teil 4: die zwei Einspeise-Wege
# --------------------------------------------------------------------
def tastaturen():
    """Eingabegeraete, die nach Tastatur aussehen - so wie das
    Frontend sie sucht (Name zuerst, dann der Kernel-Handler)."""
    treffer, sonstige = [], []
    try:
        text = open("/proc/bus/input/devices").read()
    except OSError:
        return []
    for block in text.split("\n\n"):
        name = ""
        pfad = ""
        for zeile in block.splitlines():
            if zeile.startswith("N: Name="):
                name = zeile.split("=", 1)[1].strip().strip('"')
            if zeile.startswith("H: Handlers="):
                for h in zeile.split("=", 1)[1].split():
                    if h.startswith("event"):
                        pfad = "/dev/input/" + h
                if "kbd" in zeile:
                    sonstige.append((name, pfad))
        if name and pfad and "keyboard" in name.lower():
            treffer.append((name, pfad))
    return treffer + [e for e in sonstige if e not in treffer]


def per_evdev(pfad, keycode):
    """Der Weg, den das Frontend heute geht: das Ereignis in das
    Geraet einer vorhandenen Tastatur zurueckschreiben."""
    fd = os.open(pfad, os.O_RDWR)
    try:
        for wert in (1, 0):
            ev = struct.pack(EVENT_FMT, 0, 0, EV_KEY, keycode, wert)
            syn = struct.pack(EVENT_FMT, 0, 0, EV_SYN, 0, 0)
            os.write(fd, ev + syn)
            time.sleep(0.05)
    finally:
        os.close(fd)


class Uinput(object):
    """Ein EIGENES Eingabegeraet - der uebliche, unterstuetzte Weg.

    Das Frontend benutzt ihn bis heute nicht. Falls der neue Kernel
    das Zurueckschreiben in fremde Geraete nicht mehr weiterreicht,
    ist das hier die Antwort."""

    def __init__(self):
        self.fd = os.open("/dev/uinput", os.O_WRONLY | os.O_NONBLOCK)
        fcntl.ioctl(self.fd, UI_SET_EVBIT, EV_KEY)
        for code in (KEY_F9, KEY_F12):
            fcntl.ioctl(self.fd, UI_SET_KEYBIT, code)
        # struct uinput_user_dev: char name[80]; struct input_id
        # (4x u16); u32 ff_effects_max; s32 absmax/min/fuzz/flat[64]
        name = b"Dragend Kernel Probe".ljust(80, b"\0")
        dev = name + struct.pack("<HHHHI", 3, 0x1234, 0x5678, 1, 0)
        dev += b"\0" * (4 * 64 * 4)
        os.write(self.fd, dev)
        fcntl.ioctl(self.fd, UI_DEV_CREATE)
        # MiSTer muss das neue Geraet erst bemerken.
        time.sleep(1.0)

    def taste(self, keycode):
        for wert in (1, 0):
            ev = struct.pack(EVENT_FMT, 0, 0, EV_KEY, keycode, wert)
            syn = struct.pack(EVENT_FMT, 0, 0, EV_SYN, 0, 0)
            os.write(self.fd, ev + syn)
            time.sleep(0.05)

    def close(self):
        try:
            fcntl.ioctl(self.fd, UI_DEV_DESTROY)
        except OSError:
            pass
        os.close(self.fd)


def umschalten(last, senden, name):
    """Ein Umschaltversuch: F9 soll die Last senken, F12 sie heben."""
    vorher = last.messen()
    if vorher is None:
        sagen("  %s: keine Lastmessung moeglich - MiSTer-Prozess nicht "
              "gefunden" % name)
        return None
    sagen("  Ausgangslast: %5.1f %%" % vorher)

    senden(KEY_F9)
    time.sleep(NACH_TASTE)
    nach_f9 = last.messen()
    sagen("  nach F9:      %5.1f %%   %s"
          % (nach_f9, "gesunken - angekommen"
             if nach_f9 is not None and nach_f9 < SCHWELLE
             else "unveraendert hoch - NICHT angekommen"))

    senden(KEY_F12)
    time.sleep(NACH_TASTE)
    nach_f12 = last.messen()
    sagen("  nach F12:     %5.1f %%   %s"
          % (nach_f12, "gestiegen - angekommen"
             if nach_f12 is not None and nach_f12 >= SCHWELLE
             else "unveraendert niedrig - NICHT angekommen"))

    ok = (nach_f9 is not None and nach_f9 < SCHWELLE
          and nach_f12 is not None and nach_f12 >= SCHWELLE)
    sagen("  ERGEBNIS %s: %s" % (name, "GEHT" if ok else "GEHT NICHT"))
    return ok


def eingaben():
    titel("3. Kommt eine eingespeiste Taste bei MiSTer noch an?")
    last = Last()
    if last.pid is None:
        sagen("MiSTers Prozess (%s) laeuft nicht - ohne ihn gibt es kein "
              "Messsignal. Abbruch dieses Teils." % MISTER_PFAD)
        befunde.append("MiSTer-Prozess nicht gefunden - Teil 3 konnte "
                       "nicht gemessen werden.")
        return
    sagen("MiSTer laeuft als PID %s." % last.pid)

    tasten = tastaturen()
    sagen("Gefundene Tastaturen: %s"
          % ([n for n, _p in tasten] or "KEINE"))

    sagen()
    sagen("Weg A - zurueckschreiben in eine vorhandene Tastatur "
          "(das macht das Frontend heute):")
    ok_a = None
    if not tasten:
        sagen("  keine Tastatur gefunden - nicht pruefbar")
    else:
        pfad = tasten[0][1]
        sagen("  benutze %s" % pfad)
        try:
            ok_a = umschalten(last, lambda c: per_evdev(pfad, c), "Weg A")
        except OSError as e:
            sagen("  Einspeisen schlug fehl: %s" % e)
            ok_a = False

    sagen()
    sagen("Weg B - eigenes Eingabegeraet ueber uinput:")
    ok_b = None
    try:
        ui = Uinput()
    except OSError as e:
        sagen("  /dev/uinput nicht nutzbar: %s" % e)
    else:
        try:
            ok_b = umschalten(last, ui.taste, "Weg B")
        finally:
            ui.close()

    if ok_a is False and ok_b:
        befunde.append("Der heutige Weg (Zurueckschreiben in eine fremde "
                       "Tastatur) kommt NICHT mehr an, uinput dagegen "
                       "schon. Das Frontend muss auf uinput umgestellt "
                       "werden.")
    elif ok_a:
        befunde.append("Das Einspeisen funktioniert weiterhin - die "
                       "Ursache liegt NICHT bei den Tasten.")
    elif ok_a is False and ok_b is False:
        befunde.append("Weder der heutige Weg noch uinput kommt an - "
                       "MiSTer schaltet auf diesem Kernel die Anzeige "
                       "nicht mehr per Taste um.")


def aufraeumen():
    """Den MiSTer im OSD zuruecklassen, nicht auf der Konsole."""
    tasten = tastaturen()
    if tasten:
        try:
            per_evdev(tasten[0][1], KEY_F12)
        except OSError:
            pass


def main():
    if os.geteuid() != 0:
        sagen("Bitte als root ausfuehren (per SSH als root).")
        return 1
    if os.path.exists("/tmp/frontend.lock"):
        sagen("ACHTUNG: /tmp/frontend.lock liegt da - das Frontend laeuft "
              "vermutlich noch.")
        sagen("Es haelt die Eingabegeraete exklusiv und verfaelscht die "
              "Messung. Bitte erst beenden.")
        sagen()
    umgebung()
    framebuffer()
    eingaben()
    aufraeumen()

    titel("BEFUND")
    if not befunde:
        sagen("Nichts Auffaelliges gefunden.")
    for i, b in enumerate(befunde, 1):
        sagen("%d. %s" % (i, b))
    sagen()
    sagen("Diese Ausgabe bitte komplett zurueckschicken.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
