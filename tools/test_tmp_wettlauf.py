#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Das Aufraeumen darf keine Zwischendatei loeschen, in die gerade
geschrieben wird (Build 156).

DIE GESCHICHTE DIESES FEHLERS

_thumb_cache_put() schreibt nach "<name>.art.tmp<PID>_<TID>" und
benennt danach um - atomar, damit ein Absturz mitten im Schreiben
keine halbe Datei hinterlaesst. Bricht der Vorgang doch ab, bleibt die
Zwischendatei liegen; deshalb raeumt _thumb_cache_evict_if_needed()
solche Reste mit weg.

Nur hat es JEDEN Rest weggeraeumt - auch den eines Threads, der gerade
mittendrin war. Der fand danach seine eigene Datei nicht mehr:

    THUMB_CACHE Schreibfehler: [Errno 2] No such file or directory:
    '.../41edf9fc.art.tmp4408_140600438023872' -> '.../41edf9fc.art'

Die Miniatur war weg. Nach aussen sah das so aus: "Miniaturen
vorbereiten" meldet fertig, und das Cover laedt beim Scrollen trotzdem
nach.

WARUM ES SO LANGE GEDAUERT HAT. tools/test_kaltes_cover.py hat genau
das zweimal in einem Sammellauf gemeldet - und liess sich danach weder
einzeln noch unter kuenstlicher Last wiederholen. Im Kommentar dort
steht seit Build 119 die Bitte, beim naechsten Mal mehr Angaben
mitzuliefern. Sichtbar wurde der Wettlauf erst, als libdragend (Build
153) das Rechnen so stark beschleunigt hat, dass sich Vordergrund und
Hintergrund-Schreiber zuverlaessig ueberholen.

Die Lehre, und sie ist im Projekt nicht neu: ein Test, der "manchmal"
fehlschlaegt, meldet keinen Testfehler. Er meldet einen Wettlauf.

Ausfuehren:
    python3 tools/test_tmp_wettlauf.py
"""
import os
import struct
import shutil
import sys
import tempfile
import threading
import time
import zlib

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
sys.path.insert(0, os.path.join(_REPO, "frontend"))

import fe.art as A                                      # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


TMP = tempfile.mkdtemp(prefix="tmpwettlauf_")
A.THUMB_CACHE_BASE = os.path.join(TMP, "base")
A.THUMB_CACHE_DIR = os.path.join(TMP, "cache")
os.makedirs(os.path.join(A.THUMB_CACHE_DIR, "ab"), exist_ok=True)

# Die Verdraengung soll bei jedem Aufruf wirklich durchlaufen.
A._thumb_cache_anzahl = None
A._thumb_cache_seit_zaehlung = 0

# ---------------------------------------------------------------------------
print("Test 1: eine frische Zwischendatei ueberlebt das Aufraeumen")
# ---------------------------------------------------------------------------
frisch = os.path.join(A.THUMB_CACHE_DIR, "ab",
                      "abcdef01.art.tmp%d_%d" % (os.getpid(),
                                                 threading.get_ident()))
open(frisch, "wb").write(b"halb geschrieben")
A._thumb_cache_anzahl = None
A._thumb_cache_evict_if_needed()
check("die frische Zwischendatei liegt noch da", os.path.exists(frisch))

# ---------------------------------------------------------------------------
print()
print("Test 2: eine alte Zwischendatei wird weggeraeumt")
# ---------------------------------------------------------------------------
# Beim Nutzer standen 20008 Dateien im Ordner bei einer Obergrenze von
# 20000 - Reste von Abstuerzen. Die muessen weiterhin verschwinden,
# sonst hat der Bugfix oben nur ein Leck gegen ein anderes getauscht.
alt = os.path.join(A.THUMB_CACHE_DIR, "ab", "beef0002.art.tmp999_1")
open(alt, "wb").write(b"vom letzten Absturz")
uralt = time.time() - A.TMP_REST_MINDESTALTER - 30
os.utime(alt, (uralt, uralt))
A._thumb_cache_anzahl = None
A._thumb_cache_evict_if_needed()
check("die alte Zwischendatei ist weg", not os.path.exists(alt))
check("die frische immer noch nicht", os.path.exists(frisch))

# ---------------------------------------------------------------------------
print()
print("Test 3: der echte Wettlauf - schreiben, waehrend aufgeraeumt wird")
# ---------------------------------------------------------------------------
# Das ist der Fall, der im Sammellauf zugeschlagen hat: waehrend
# _thumb_cache_put() zwischen "geschrieben" und "umbenannt" steht,
# laeuft in einem anderen Thread die Verdraengung.
BILD = os.path.join(TMP, "cover.art")
w, h = 200, 280
pix = bytes(bytearray([(i * 11) % 256 for i in range(w * h * 4)]))
open(BILD, "wb").write(b"ART1" + struct.pack("<HH", w, h)
                       + zlib.compress(pix, 1))

echt_replace = os.replace
laeuft = threading.Event()
weiter = threading.Event()


def replace_mit_pause(a, b):
    """Genau im gefaehrlichen Moment anhalten: Zwischendatei liegt
    fertig auf der Karte, das Umbenennen hat noch nicht stattgefunden."""
    if ".art.tmp" in str(a):
        laeuft.set()
        weiter.wait(5.0)
    return echt_replace(a, b)


os.replace = replace_mit_pause
ergebnis = []


def schreiber():
    ergebnis.append(A.prewarm_thumb(BILD, 100, 140))


t = threading.Thread(target=schreiber)
t.start()
check("der Schreiber steht im kritischen Moment", laeuft.wait(5.0))
A._thumb_cache_anzahl = None
A._thumb_cache_evict_if_needed()          # <- hier wurde vorher geloescht
weiter.set()
t.join(10.0)
os.replace = echt_replace

check("der Schreiber meldet Erfolg", ergebnis == ["fertig"], str(ergebnis))
check("und die Miniatur liegt wirklich auf der Karte",
      A.thumb_cache_has(BILD, 100, 140))

shutil.rmtree(TMP, ignore_errors=True)

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for f in fails:
        print("  -", f)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
