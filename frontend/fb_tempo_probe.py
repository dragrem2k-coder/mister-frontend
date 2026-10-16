#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Warum ist das Scrollen auf Kernel 6.18 langsamer? - Messen statt raten.

WAS DIESE PROBE BEANTWORTET

Nutzermeldung, mit dem neuen Kernel drauf: "ich habe sehr stark den
Eindruck, dass das Scrollen erheblich schlechter ist, mit dem alten
Kernel fluessig, mit dem neuen stockt es immer wieder sehr doll."

Der Eindruck ist durch Bench 9 belegt, und zwar an Zahlen, die
NICHTS mit dem Frontend zu tun haben, sondern nur mit dem
Hineinschreiben in den Bildspeicher:

    flip in Liste/liste        alter Kernel  9,17 ms  ->  neuer 12,11 ms
    karte_mit_schatten         alter Kernel  8,81 ms  ->  neuer 11,33 ms
    Start, je Spiel            alter Kernel 0,0877 ms -> neuer 0,1036 ms

Rund 30 Prozent auf allem, was in den Bildspeicher schreibt. Dazu
meldet der Kernel im dmesg:

    fb0: sys_fillrect: framebuffer is not in virtual address space

DIE VERMUTUNG, DIE HIER GEPRUEFT WIRD: nicht die Menge der Bytes hat
sich geaendert, sondern die ART, WIE der Bildspeicher eingeblendet
ist. Es gibt drei Wege, und sie unterscheiden sich darin, ob der
Prozessor die Schreibzugriffe puffern darf:

  1. mmap auf /dev/fb0            - das macht das Frontend heute. Seit
                                    dem Kernel-Fix vom 08.09.2026
                                    (Commit ea22122) geht es wieder.
  2. mmap auf /dev/mem, O_SYNC    - der Rueckfall aus Build 184, als
                                    Weg 1 nicht ging. O_SYNC heisst
                                    ausdruecklich "nicht puffern".
  3. mmap auf /dev/mem, OHNE O_SYNC - der Weg, den MiSTers eigenes
                                    Main-Binary benutzt (shmem_map auf
                                    die physische Adresse).

Ist Weg 3 deutlich schneller, liegt die Antwort dort - und dann ist
es eine Zeile im Frontend und kein Umbau. Ist er gleich schnell, war
die Vermutung falsch, und die naechste Messung muss woanders ansetzen.

EIN VORBEHALT, DER MITGEMESSEN WIRD: bei Weg 3 darf der Prozessor
Schreibzugriffe im Cache halten. Das FPGA liest den Bildspeicher
selbst - was im Cache liegt, sieht es moeglicherweise nicht. Deshalb
malt die Probe am Ende ein Muster und fragt nach, ob es zu sehen war.
Eine Zahl ohne diese Antwort ist hier wertlos.

BENUTZUNG

    Erst das Frontend beenden:

        kill $(cat /tmp/frontend.lock) ; sleep 2

    dann:

        python3 /media/fat/frontend/fb_tempo_probe.py

Es wird NICHTS dauerhaft geaendert: nichts auf die SD-Karte
geschrieben, keine Einstellung angefasst. Nur in den Bildspeicher
gemalt - das raeumt das Frontend beim naechsten Bild selbst auf.
"""
import fcntl
import mmap
import os
import struct
import sys
import time

FBIOGET_VSCREENINFO = 0x4600
FBIOGET_FSCREENINFO = 0x4602

# Wie oft jede Messung wiederholt wird. Berichtet werden Mittel UND
# bester Wert: der beste sagt, was die Maschine kann, das Mittel, was
# sie im Alltag tut.
RUNDEN = 5


def kopf(text):
    print()
    print("=" * 68)
    print(text)
    print("=" * 68)


def geometrie(fd):
    """Breite, Hoehe, Bytes je Zeile, physische Adresse, Laenge."""
    roh = bytearray(160)
    fcntl.ioctl(fd, FBIOGET_VSCREENINFO, roh, True)
    width, height = struct.unpack_from("<II", roh, 0)
    bpp = struct.unpack_from("<I", roh, 24)[0]
    fix = bytearray(160)
    fcntl.ioctl(fd, FBIOGET_FSCREENINFO, fix, True)
    smem_start, smem_len = struct.unpack_from("<II", fix, 16)
    stride = struct.unpack_from("<I", fix, 40)[0]
    if not stride:
        stride = width * (bpp // 8)
    return width, height, stride, bpp, smem_start, smem_len


def messen(fn):
    """Beste und mittlere Dauer in Millisekunden."""
    zeiten = []
    for _ in range(RUNDEN):
        t0 = time.perf_counter()
        fn()
        zeiten.append((time.perf_counter() - t0) * 1000.0)
    return min(zeiten), sum(zeiten) / len(zeiten)


def pruefen(mm, groesse, stride, hoehe):
    """Die drei Schreibmuster, die im Frontend wirklich vorkommen."""
    ergebnis = {}
    voll = b"\x20" * groesse

    def _voll():
        mm[0:groesse] = voll

    ergebnis["voll"] = messen(_voll)

    # Lange Zeilen: ein Band, wie es _baender_flippen() kopiert.
    zeilen_lang = min(136, hoehe)
    band = b"\x30" * (zeilen_lang * stride)

    def _band():
        mm[0:zeilen_lang * stride] = band

    ergebnis["band"] = messen(_band)

    # Kurze Zeilen: der Rechteck-Flip aus Build 215 (952 Zeilen a
    # 1096 Byte). Genau hier entscheidet sich, ob die Einblendung
    # jeden einzelnen Zugriff teurer macht oder nur die Menge.
    kurz_breite = 1096
    kurz_zeilen = min(952, hoehe)
    stueck = b"\x40" * kurz_breite

    def _kurz():
        for y in range(kurz_zeilen):
            a = y * stride
            mm[a:a + kurz_breite] = stueck

    ergebnis["kurz"] = messen(_kurz)

    # Und das Lesen - der Blick des Bildwaechters (20 Zeilen a 30 kB).
    def _lesen():
        for y in range(0, min(20 * 50, hoehe), 50):
            a = y * stride
            _ = bytes(mm[a:a + 1536])

    ergebnis["lesen"] = messen(_lesen)
    return ergebnis


def bericht(name, e, groesse):
    mb = groesse / (1024.0 * 1024.0)
    print("  %-34s %8.2f ms  (best %6.2f)  %5.2f ms/MB"
          % ("Vollbild (%.1f MB)" % mb, e["voll"][1], e["voll"][0],
             e["voll"][1] / mb))
    print("  %-34s %8.2f ms  (best %6.2f)"
          % ("Band, 136 lange Zeilen", e["band"][1], e["band"][0]))
    print("  %-34s %8.2f ms  (best %6.2f)"
          % ("952 kurze Zeilen a 1096 Byte", e["kurz"][1], e["kurz"][0]))
    print("  %-34s %8.2f ms  (best %6.2f)"
          % ("20 Proben lesen (30 kB)", e["lesen"][1], e["lesen"][0]))


def main():
    if os.path.exists("/tmp/frontend.lock"):
        print("ACHTUNG: /tmp/frontend.lock liegt da - das Frontend laeuft")
        print("vermutlich noch und zeichnet gleichzeitig in denselben")
        print("Bildspeicher. Die Messung waere wertlos. Bitte erst:")
        print()
        print("    kill $(cat /tmp/frontend.lock) ; sleep 2")
        print()
        return 1

    try:
        fd = os.open("/dev/fb0", os.O_RDWR)
    except OSError as e:
        print("/dev/fb0 laesst sich nicht oeffnen: %s" % e)
        return 1

    w, h, stride, bpp, smem_start, smem_len = geometrie(fd)
    groesse = stride * h
    kopf("1. Was fuer ein Bildspeicher ist das?")
    print("Kernel     : %s" % os.uname().release)
    print("Geometrie  : %dx%d, %d bpp, %d Byte je Zeile" % (w, h, bpp, stride))
    print("smem_start = 0x%08X, smem_len = %d (gebraucht: %d)"
          % (smem_start, smem_len, groesse))

    ergebnisse = {}

    kopf("2. Weg 1: mmap auf /dev/fb0 (das macht das Frontend heute)")
    try:
        mm = mmap.mmap(fd, groesse, mmap.MAP_SHARED,
                       mmap.PROT_READ | mmap.PROT_WRITE)
    except (OSError, ValueError) as e:
        print("GEHT NICHT: %s" % e)
    else:
        ergebnisse["fb0"] = pruefen(mm, groesse, stride, h)
        bericht("fb0", ergebnisse["fb0"], groesse)
        mm.close()

    for schluessel, sync, titel in (
            ("mem_sync", True,
             "3. Weg 2: mmap auf /dev/mem MIT O_SYNC (Rueckfall aus "
             "Build 184)"),
            ("mem", False,
             "4. Weg 3: mmap auf /dev/mem OHNE O_SYNC (so macht es "
             "MiSTers Main)")):
        kopf(titel)
        if not smem_start:
            print("Der Treiber meldet keine physische Adresse - nicht "
                  "messbar.")
            continue
        if smem_start % mmap.PAGESIZE:
            print("smem_start ist nicht seitenausgerichtet - nicht "
                  "messbar.")
            continue
        flags = os.O_RDWR | (os.O_SYNC if sync else 0)
        try:
            mem_fd = os.open("/dev/mem", flags)
        except OSError as e:
            print("/dev/mem laesst sich nicht oeffnen: %s" % e)
            continue
        try:
            mm = mmap.mmap(mem_fd, groesse, mmap.MAP_SHARED,
                           mmap.PROT_READ | mmap.PROT_WRITE,
                           offset=smem_start)
        except (OSError, ValueError) as e:
            print("GEHT NICHT: %s" % e)
            os.close(mem_fd)
            continue
        ergebnisse[schluessel] = pruefen(mm, groesse, stride, h)
        bericht(schluessel, ergebnisse[schluessel], groesse)
        if not sync:
            # DIE SICHTPRUEFUNG. Ohne sie ist die Zahl wertlos: was im
            # Cache des Prozessors liegt, sieht das FPGA
            # moeglicherweise nicht - und dann waere der schnellere
            # Weg ein unsichtbarer.
            print()
            print("  SICHTPRUEFUNG - bitte auf den Bildschirm sehen:")
            print("  drei breite Streifen werden gemalt (oben, Mitte, "
                  "unten).")
            for i, (y0, y1) in enumerate(((0, h // 3),
                                          (h // 3, 2 * h // 3),
                                          (2 * h // 3, h))):
                farbe = (b"\xff\x00\x00\x00", b"\x00\xff\x00\x00",
                         b"\x00\x00\xff\x00")[i]
                zeile = farbe * (stride // 4)
                for y in range(y0, y1):
                    a = y * stride
                    mm[a:a + stride] = zeile
            print("  Gemalt. Zehn Sekunden Zeit.")
            time.sleep(10)
            print("  WAREN DIE DREI STREIFEN ZU SEHEN - vollstaendig und")
            print("  sofort? Diese Antwort bitte mitschicken, sie")
            print("  entscheidet ueber den Weg.")
        mm.close()
        os.close(mem_fd)

    os.close(fd)

    kopf("BEFUND")
    if "fb0" not in ergebnisse:
        print("Weg 1 war nicht messbar - ohne ihn gibt es keinen "
              "Vergleich.")
        return 0
    basis = ergebnisse["fb0"]
    namen = {"fb0": "mmap /dev/fb0 (heute)",
             "mem_sync": "mmap /dev/mem, O_SYNC",
             "mem": "mmap /dev/mem, ohne O_SYNC"}
    print("%-30s %10s %10s %10s" % ("Weg", "Vollbild", "Band", "kurz"))
    for schluessel in ("fb0", "mem_sync", "mem"):
        e = ergebnisse.get(schluessel)
        if not e:
            continue
        print("%-30s %9.2f %10.2f %10.2f"
              % (namen[schluessel], e["voll"][1], e["band"][1],
                 e["kurz"][1]))
    print()
    for schluessel in ("mem_sync", "mem"):
        e = ergebnisse.get(schluessel)
        if not e:
            continue
        v = basis["voll"][1] / e["voll"][1] if e["voll"][1] else 0.0
        print("%-30s Vollbild %4.2fx %s als heute"
              % (namen[schluessel], v,
                 "schneller" if v > 1 else "langsamer"))
    print()
    print("ZU LESEN ALS: lohnt sich ein Wechsel, muss der Unterschied")
    print("deutlich ueber dem Rauschen liegen (Mittel gegen besten Wert")
    print("vergleichen) UND die Sichtpruefung muss gestimmt haben.")
    print("Sind alle drei Wege gleich schnell, war die Vermutung falsch")
    print("und die Einblendung ist es nicht - das ist auch ein Ergebnis.")
    print()
    print("Diese Ausgabe bitte komplett zurueckschicken.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
