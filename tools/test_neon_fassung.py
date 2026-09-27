#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Die vektorisierte Fassung von libdragend - und warum sie bitgleich
rechnen MUSS.

WORUM ES GEHT

Der Cortex-A9 im DE10-Nano hat NEON. Gebaut wurde bisher mit blossem
-O2, also skalar. Aus dem Bench auf dem Geraet:

    Flaechenmittel 1200x1600 -> 578x770     112 ms

Das sind 58 Nanosekunden je Quellpunkt - fuer C auf 800 MHz viel. Die
Flaechenmittelung ist genau die Sorte Schleife, die ein Vektorbefehls-
satz mag, und GCC vektorisiert sie mit den passenden Flags auch
tatsaechlich.

Ob daraus auf dem Geraet ein Gewinn wird, sagt dieser Test NICHT - das
sagt nur eine Messung dort (siehe Kopf von frontend/c/bauen.sh).

WAS DIESER TEST ABSICHERT, UND WARUM ES DARAUF ANKOMMT

Dass beide Fassungen BITGLEICH rechnen.

Das ist keine Formsache. Der Schluessel des Miniaturen-Caches enthaelt
die Kastengroesse, nicht den Bildinhalt (siehe _thumb_cache_key() in
fe/art.py). Eine gespeicherte Miniatur und eine frisch gerechnete
muessen deshalb identisch sein - sonst haengt das Bild davon ab, ob es
gerade aus dem Cache kam oder nicht, und zwar unsichtbar.

Dieselbe Regel steht seit Build 116 im Modulkopf von fe/art.py.

DIE FALLE: -ffast-math und Verwandte. Die Zielbereiche werden in
dragend.c ueber DOUBLE gerechnet. Ein Compiler, der daran drehen darf,
verschiebt Kanten um einen Bildpunkt - und genau das faellt niemandem
auf, bis die Cover nach einem Neubau anders aussehen als vorher.

Ausfuehren (braucht libdragend_x86.so, also den Entwicklungsrechner):
    python3 tools/test_neon_fassung.py
"""
import ctypes
import io
import os
import random
import subprocess
import sys
import tempfile

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
_C = os.path.join(_REPO, "frontend", "c")

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


# ---------------------------------------------------------------------------
print("Test 1: das Bauskript baut beide Fassungen, und zwar sauber")
# ---------------------------------------------------------------------------
_roh = io.open(os.path.join(_C, "bauen.sh"), encoding="utf-8").read()
# NUR die Befehlszeilen, ohne Kommentare. Sonst faellt die Pruefung
# unten ueber den Kommentar, der -ffast-math ausdruecklich ausschliesst
# - genau das ist beim ersten Lauf passiert.
skript = "\n".join(z for z in _roh.splitlines()
                   if not z.lstrip().startswith("#"))
check("libdragend.so wird weiterhin mit -O2 gebaut",
      "-O2 \\\n    -o libdragend.so" in skript or "-O2" in skript)
check("libdragend_neon.so wird zusaetzlich gebaut",
      "-o libdragend_neon.so" in skript)
check("mit -ftree-vectorize", "-ftree-vectorize" in skript)
check("und fuer den richtigen Kern", "-mcpu=cortex-a9" in skript)
# DAS hier ist die eigentliche Absicherung.
for gift in ("-ffast-math", "-funsafe-math-optimizations", "-Ofast",
             "-ffinite-math-only", "-fassociative-math"):
    check("KEIN %s" % gift, gift not in skript,
          "wuerde die Fliesskommarechnung veraendern")
check("   (und die Begruendung dafuer steht im Bauskript)",
      "-ffast-math" in _roh) if gift == "-ffast-math" else None
check("neon-vfpv3 statt blossem neon", "-mfpu=neon-vfpv3" in skript,
      "NEON rechnet einfache Genauigkeit nicht IEEE-treu")

# ---------------------------------------------------------------------------
print()
print("Test 2: beide ARM-Dateien liegen vor und sind fuer ARM gebaut")
# ---------------------------------------------------------------------------
for name in ("libdragend.so", "libdragend_neon.so"):
    for ort in ("frontend", os.path.join("frontend", "c")):
        p = os.path.join(_REPO, ort, name)
        da = os.path.exists(p)
        check("%s/%s liegt bereit" % (ort, name), da)
        if da:
            with open(p, "rb") as f:
                kopf = f.read(20)
            # ELF, 32 Bit, little endian, Maschine 40 = ARM
            check("   und ist ARM, 32 Bit",
                  kopf[:4] == b"\x7fELF" and kopf[4] == 1
                  and kopf[18] == 40, "Maschine %d" % kopf[18])

check("die beiden Fassungen sind NICHT dieselbe Datei",
      open(os.path.join(_REPO, "frontend", "libdragend.so"), "rb").read()
      != open(os.path.join(_REPO, "frontend", "libdragend_neon.so"),
              "rb").read(),
      "sonst waere nichts gewonnen und der Vergleich sinnlos")

# ---------------------------------------------------------------------------
print()
print("Test 3: DIE HAUPTSACHE - beide rechnen bitgleich")
# ---------------------------------------------------------------------------
# Auf dem Entwicklungsrechner laesst sich die ARM-Datei nicht
# ausfuehren. Geprueft wird deshalb dasselbe, was bei ARM den
# Unterschied macht: dieselbe Quelle, einmal mit -O2 und einmal mit
# -O3 samt Vektorisierung, hier fuer x86 gebaut. Bleibt das Ergebnis
# dort bitgleich, liegt es an der Quelle und nicht an der Zielmaschine.
def bauen(flags, ziel):
    r = subprocess.run(
        ["gcc", "-shared", "-fPIC"] + flags + ["-o", ziel,
                                               os.path.join(_C, "dragend.c")],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return r.returncode == 0, r.stderr.decode("utf-8", "replace")


def laden(p):
    lib = ctypes.CDLL(p)
    for n in ("skalieren_flaechenmittel", "skalieren_nearest"):
        f = getattr(lib, n)
        f.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_int,
                      ctypes.c_int, ctypes.c_int, ctypes.c_char_p]
        f.restype = ctypes.c_int
    lib.hochskalieren.argtypes = [ctypes.c_char_p, ctypes.c_int,
                                  ctypes.c_int, ctypes.c_int,
                                  ctypes.c_char_p]
    lib.hochskalieren.restype = ctypes.c_int
    return lib


ordner = tempfile.mkdtemp(prefix="neon_test_")
try:
    p_alt = os.path.join(ordner, "alt.so")
    p_neu = os.path.join(ordner, "neu.so")
    ok1, fehl1 = bauen(["-O2"], p_alt)
    ok2, fehl2 = bauen(["-O3", "-ftree-vectorize"], p_neu)
    check("die -O2-Fassung laesst sich bauen", ok1, fehl1[:120])
    check("die vektorisierte Fassung ebenso", ok2, fehl2[:120])
    if not (ok1 and ok2):
        print("  (ohne beide Fassungen kann Test 3 nichts pruefen)")
    else:
        a, b = laden(p_alt), laden(p_neu)
        rnd = random.Random(20260925)
        # Zufallsrauschen ist hier genau richtig: es hat keine Struktur,
        # an der sich ein Rundungsfehler verstecken koennte.
        def bild(w, h):
            return bytes(bytearray(rnd.randrange(256)
                                   for _ in range(w * h * 4)))
        vergleiche = 0
        abweichungen = []
        for _ in range(30):
            w, h = rnd.randint(8, 260), rnd.randint(8, 260)
            tw, th = rnd.randint(1, w), rnd.randint(1, h)
            q = bild(w, h)
            for fn in ("skalieren_flaechenmittel", "skalieren_nearest"):
                o1 = ctypes.create_string_buffer(tw * th * 4)
                o2 = ctypes.create_string_buffer(tw * th * 4)
                r1 = getattr(a, fn)(q, w, h, tw, th, o1)
                r2 = getattr(b, fn)(q, w, h, tw, th, o2)
                vergleiche += 1
                if r1 != r2 or o1.raw != o2.raw:
                    abweichungen.append("%s %dx%d->%dx%d" % (fn, w, h, tw, th))
            s = rnd.randint(2, 4)
            o1 = ctypes.create_string_buffer(w * s * h * s * 4)
            o2 = ctypes.create_string_buffer(w * s * h * s * 4)
            r1 = a.hochskalieren(q, w, h, s, o1)
            r2 = b.hochskalieren(q, w, h, s, o2)
            vergleiche += 1
            if r1 != r2 or o1.raw != o2.raw:
                abweichungen.append("hochskalieren %dx%d x%d" % (w, h, s))
        check("%d Vergleiche ohne eine einzige Abweichung" % vergleiche,
              not abweichungen, "; ".join(abweichungen[:3]))

        # Und die Groessen, die das Frontend wirklich anfragt.
        echt = [(1200, 1600, 578, 770), (1200, 1600, 176, 235),
                (900, 1200, 231, 420), (320, 420, 96, 128)]
        schief = []
        for w, h, tw, th in echt:
            q = bild(w, h)
            for fn in ("skalieren_flaechenmittel", "skalieren_nearest"):
                o1 = ctypes.create_string_buffer(tw * th * 4)
                o2 = ctypes.create_string_buffer(tw * th * 4)
                getattr(a, fn)(q, w, h, tw, th, o1)
                getattr(b, fn)(q, w, h, tw, th, o2)
                if o1.raw != o2.raw:
                    schief.append("%s %dx%d->%dx%d" % (fn, w, h, tw, th))
        check("auch bei den echten Kastengroessen des Frontends",
              not schief, "; ".join(schief))
finally:
    import shutil
    shutil.rmtree(ordner, ignore_errors=True)

# ---------------------------------------------------------------------------
print()
print("Test 4: die neue Fassung wird NICHT heimlich ausgeliefert")
# ---------------------------------------------------------------------------
# Sie ist ein Messgegenstand, keine Voreinstellung. Erst wenn auf dem
# Geraet nachgemessen ist, dass sie etwas bringt, gehoert sie in die
# Installer - und dann als Ersatz, nicht als zweite Datei daneben.
for skriptname in ("Frontend_Install.sh", "Frontend_Install_Remote.sh",
                   "Frontend_Install_Offline.sh"):
    p = os.path.join(_REPO, "Scripts", skriptname)
    if not os.path.exists(p):
        continue
    inhalt = io.open(p, encoding="utf-8", errors="replace").read()
    check("%s kopiert libdragend_neon.so (noch) nicht" % skriptname,
          "libdragend_neon" not in inhalt,
          "bis die Messung auf dem Geraet vorliegt")

quelle = io.open(os.path.join(_REPO, "frontend", "fe", "art.py"),
                 encoding="utf-8").read()
check("und das Frontend laedt weiterhin libdragend.so",
      "libdragend_neon" not in quelle,
      "der Vergleich laeuft ueber DRAGEND_LIB, nicht ueber den Code")
check("ueber DRAGEND_LIB laesst sich eine andere Datei waehlen",
      "DRAGEND_LIB" in quelle)

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
