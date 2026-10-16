#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ist der Prozessor auf Kernel 6.18 langsamer? - 20 Sekunden statt Bench.

WARUM ES DIESE PROBE GIBT

Nutzermeldung: "mit dem alten Kernel fluessig, mit dem neuen stockt es
immer wieder sehr doll." Die erste Vermutung war die Einblendung des
Bildspeichers. fb_tempo_probe.py hat sie erledigt: mmap auf /dev/fb0
ist auf diesem Geraet 1,65 ms/MB, /dev/mem 11,2 ms/MB - der Weg, den
das Frontend heute geht, ist der schnellste von drei.

DER VERGLEICH DER BENCH-LAEUFE ZEIGT ETWAS ANDERES. Abschnitt C des
Bench ist mit Absicht vom Bestand unabhaengig und war auf dem alten
Kernel ueber drei Laeufe auf 2 % stabil:

                              5.15.1 (alt)      6.18.38 (neu)
    Nearest     578x770           26,2 ms           33,8 ms   +29 %
    Flaechenm.  176x235           44,5 ms           57,1 ms   +28 %
    Nearest     176x235            3,9 ms            5,4 ms   +38 %
    Dasselbe in PYTHON           5520   ms         7338   ms   +33 %
    PNG lesen und dekodieren      258,6 ms          291,8 ms   +13 %
    Voller Flip ohne Vsync         12,6 ms           18,0 ms   +43 %

Die vierte Zeile ist die wichtigste: eine REINE PYTHON-SCHLEIFE, kein
Bildspeicher, keine SD-Karte, kein C-Modul, dieselbe Python-Version
(3.9.6). Wird die um ein Drittel langsamer, dann rechnet die Maschine
langsamer - und nicht das Frontend schlechter.

WAS DIESE PROBE DAZU BEITRAEGT

  1. Dieselben Messungen in 20 Sekunden statt in einem Bench-Lauf, so
     dass sich alter und neuer Kernel direkt vergleichen lassen: einmal
     hier laufen lassen, einmal nach dem Zurueckbauen.
  2. Die Auskuenfte, die die URSACHE benennen koennten - Taktfrequenz,
     cpufreq-Regler und was der Kernel ueber den L2-Cache und dessen
     Vorauslese (prefetch) sagt. Genau dort liegen bei dieser CPU
     (Cyclone V, Cortex-A9) die ueblichen 20-30 Prozent.

Es wird NICHTS geaendert und nichts auf die Karte geschrieben. Das
Frontend muss dafuer NICHT beendet werden - gemessen wird nur gerechnet
(am besten trotzdem ohne laufendes Spiel, damit die CPU frei ist).

BENUTZUNG

    python3 /media/fat/frontend/cpu_tempo_probe.py

Die Ausgabe landet zusaetzlich in /tmp/dragend_cpu_probe.txt.
"""
import gc
import os
import sys
import time
import zlib

RUNDEN = 3

# Nur die Beschriftung. Bezugswerte stehen hier ABSICHTLICH nicht: die
# Zahlen gelten je Geraet, und eine einbetonierte Vergleichszahl waere
# beim naechsten Geraet eine Falle. Verglichen wird mit dem eigenen
# zweiten Lauf auf dem anderen Kernel.
NAMEN = {
    "schleife": "reine Python-Schleife",
    "float": "Gleitkomma-Schleife",
    "translate": "bytes.translate auf 1 MB",
    "memcpy1": "1 MB in RAM kopieren",
    "memcpy8": "7,9 MB in RAM kopieren",
    "zlib": "1 MB packen, Stufe 1",
}

_zeilen = []


def sag(text=""):
    print(text)
    _zeilen.append(text)


def kopf(text):
    sag()
    sag("=" * 68)
    sag(text)
    sag("=" * 68)


def messen(fn):
    gc.collect()
    gc.disable()
    try:
        zeiten = []
        for _ in range(RUNDEN):
            t0 = time.perf_counter()
            fn()
            zeiten.append((time.perf_counter() - t0) * 1000.0)
    finally:
        gc.enable()
    return min(zeiten), sum(zeiten) / len(zeiten)


def datei(pfad, zeilen=1):
    try:
        with open(pfad) as f:
            return "".join([f.readline() for _ in range(zeilen)]).strip()
    except OSError:
        return None


def rechnen():
    """Fuenf Messungen, die nichts mit Bildschirm oder Karte zu tun haben."""
    ergebnis = {}

    # 1. Reine Ganzzahl-Schleife. Keine Bibliothek, kein Speicher,
    #    nichts, was sich zwischen zwei Kerneln anders uebersetzen
    #    laesst. Das ist die Zahl, auf die es ankommt.
    def _schleife():
        s = 0
        for i in range(400000):
            s += i * 3 % 7
        return s

    ergebnis["schleife"] = messen(_schleife)

    # 2. Gleitkomma - haengt an einer anderen Einheit der CPU als 1.
    def _float():
        s = 0.0
        for i in range(200000):
            s += (i * 1.5) / 3.25
        return s

    ergebnis["float"] = messen(_float)

    # 3. bytes.translate auf 1 MB - genau das, was der Bench benutzt,
    #    um sein Testbild zu bauen. Reiner Speicherdurchsatz in C,
    #    ohne jeden Bildspeicher.
    eins = bytes(range(256)) * 4096
    tabelle = bytes((255 - b) for b in range(256))

    def _translate():
        eins.translate(tabelle)

    ergebnis["translate"] = messen(_translate)

    # 4. Kopieren im RAM - einmal 1 MB, einmal so viel wie ein ganzes
    #    Bild. Der Vergleich mit fb_tempo_probe.py sagt, ob der
    #    Unterschied am Bildspeicher haengt oder am Speicher ueberhaupt.
    ziel1 = bytearray(1024 * 1024)
    quelle1 = bytes(1024 * 1024)

    def _memcpy1():
        ziel1[:] = quelle1

    ergebnis["memcpy1"] = messen(_memcpy1)

    gross = 1920 * 1080 * 4
    ziel8 = bytearray(gross)
    quelle8 = bytes(gross)

    def _memcpy8():
        ziel8[:] = quelle8

    ergebnis["memcpy8"] = messen(_memcpy8)

    # 5. zlib, Stufe 1 - so packt das Frontend seine Miniaturen.
    packbar = (bytes(range(64)) * 64 + os.urandom(4096)) * 240

    def _zlib():
        zlib.compress(packbar[:1024 * 1024], 1)

    ergebnis["zlib"] = messen(_zlib)
    return ergebnis


def main():
    kopf("1. Was fuer eine Maschine ist das?")
    u = os.uname()
    sag("Kernel     : %s (%s)" % (u.release, u.machine))
    sag("Python     : %s" % sys.version.split()[0])
    sag("Zeit       : %s" % time.strftime("%Y-%m-%d %H:%M:%S"))

    kopf("2. Rechnen - nichts davon beruehrt Bildschirm oder Karte")
    e = rechnen()
    for schluessel in ("schleife", "float", "translate", "memcpy1",
                       "memcpy8", "zlib"):
        wert = e.get(schluessel)
        if not wert:
            continue
        sag("  %-32s %9.2f ms  (best %8.2f)"
            % (NAMEN[schluessel], wert[1], wert[0]))
    sag()
    sag("  Zum Einordnen: 7,9 MB in den BILDSPEICHER schreiben kostet")
    sag("  auf diesem Geraet laut fb_tempo_probe.py rund 13 ms. Steht")
    sag("  '7,9 MB in RAM kopieren' deutlich darueber, ist nicht der")
    sag("  Bildspeicher das Problem, sondern der Speicher ueberhaupt.")

    kopf("3. Taktfrequenz und Regler")
    cpufreq = "/sys/devices/system/cpu/cpu0/cpufreq"
    if os.path.isdir(cpufreq):
        for name in ("scaling_governor", "scaling_cur_freq",
                     "scaling_min_freq", "scaling_max_freq",
                     "cpuinfo_cur_freq", "cpuinfo_min_freq",
                     "cpuinfo_max_freq", "scaling_driver",
                     "scaling_available_governors"):
            wert = datei(os.path.join(cpufreq, name))
            if wert is not None:
                sag("  %-28s %s" % (name, wert))
    else:
        sag("  Kein cpufreq vorhanden - der Takt kommt dann vom")
        sag("  Preloader/u-boot und ist zur Laufzeit nicht einstellbar.")
        sag("  Dann entscheidet der Vergleich der Zahlen oben.")
    sag()
    for feld in ("BogoMIPS", "model name", "Processor", "CPU implementer",
                 "CPU part", "CPU revision"):
        try:
            with open("/proc/cpuinfo") as f:
                for zeile in f:
                    if zeile.lower().startswith(feld.lower()):
                        sag("  /proc/cpuinfo: %s" % zeile.strip())
                        break
        except OSError:
            break
    sag("  Kerne       : %s" % (os.cpu_count() or "?"))
    last = datei("/proc/loadavg")
    if last:
        sag("  loadavg     : %s" % last)

    kopf("4. Was sagt der Kernel ueber den L2-Cache?")
    # HIER LIEGT DER WAHRSCHEINLICHSTE GRUND. Beim Cortex-A9 haengt
    # der Speicherdurchsatz an der Einstellung des L2-Caches (PL310):
    # Vorauslese (prefetch), doppelte Zeilenfuellung, Write-Allocate.
    # Die stehen im Devicetree, und ein neuer Kernel bringt einen
    # neuen Devicetree mit. Genau diese Zeilen sind der Vergleich
    # zwischen altem und neuem Kernel.
    gefunden = False
    try:
        import subprocess
        aus = subprocess.run(["dmesg"], stdout=subprocess.PIPE,
                             stderr=subprocess.DEVNULL)
        for zeile in aus.stdout.decode("utf-8", "replace").splitlines():
            k = zeile.lower()
            if ("l2c" in k or "l2x0" in k or "prefetch" in k
                    or "cache poli" in k or "write alloc" in k
                    or "cpufreq" in k or "opp" in k):
                sag("  " + zeile.strip())
                gefunden = True
    except Exception as ex:                              # noqa: BLE001
        sag("  dmesg nicht lesbar (%s)" % ex)
    if not gefunden:
        sag("  Keine Zeile zu L2/prefetch im dmesg - moeglicherweise ist")
        sag("  der Puffer schon ueberschrieben. Dann hilft nach einem")
        sag("  Neustart: dmesg | grep -i -E 'l2|prefetch|cache'")

    kopf("SO IST DIE PROBE ZU BENUTZEN")
    sag("Diese Zahlen sagen allein noch nichts - sie brauchen den")
    sag("VERGLEICH. Einmal hier (neuer Kernel), einmal nach dem")
    sag("Zurueckbauen auf den alten. Dieselbe Datei, dieselbe Maschine,")
    sag("nichts anderes dazwischen.")
    sag()
    sag("Ist die REINE PYTHON-SCHLEIFE auf dem neuen Kernel deutlich")
    sag("langsamer, rechnet die Maschine langsamer, und dann ist am")
    sag("Frontend nichts zu holen - dann gehoert der Befund ins")
    sag("MiSTer-Forum, mit diesen Zahlen.")
    sag()
    sag("Sind die Schleifen gleich und nur die Speicher-Zeilen langsamer,")
    sag("ist es der L2-Cache bzw. seine Vorauslese - dann sagt Abschnitt")
    sag("4 im Vergleich, welche Einstellung sich geaendert hat.")
    sag()
    sag("Diese Ausgabe bitte komplett zurueckschicken.")

    try:
        with open("/tmp/dragend_cpu_probe.txt", "w") as f:
            f.write("\n".join(_zeilen) + "\n")
        print()
        print("Auch gespeichert in: /tmp/dragend_cpu_probe.txt")
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
