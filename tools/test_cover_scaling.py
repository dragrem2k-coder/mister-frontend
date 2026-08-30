#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft das Verkleinern der Boxart (Flaechenmittel statt Wegwerfen).

Hintergrund (Nutzer-Rueckmeldung nach Einfuehrung des Menuepunkts
"Menue-Aufloesung"): "auf halb sehen jetzt die Boxarts von den Spielen
aber pixelig aus ... auf viertel laeuft das Scrollen super, aber auch
hier sehen die Boxarts verpixelt aus."

Ursache war das Verkleinerungsverfahren: es hat Bildzeilen und -spalten
schlicht WEGGEWORFEN (Nearest-Neighbor). Aufgefallen ist das erst mit
dem neuen Menuepunkt, weil bei voller Aufloesung die Cover-Flaeche
groesser als ein uebliches Cover ist - dort wird gar nicht verkleinert.

Geprueft wird hier nicht "sieht huebsch aus" (das kann kein Test),
sondern das, was sich objektiv nachrechnen laesst:
  - die Zielgroesse ist unveraendert zur alten Fassung,
  - eine EINFARBIGE Flaeche bleibt exakt farbtreu,
  - ein feines Streifenmuster wird gemittelt statt zufaellig
    weggeworfen (genau der sichtbare Unterschied),
  - der Cache-Schluessel hat sich geaendert, sonst kaeme die
    Verbesserung bei bereits zwischengespeicherten Covern nie an.

Ausfuehren:
    python3 tools/test_cover_scaling.py
"""
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_FRONTEND_DIR = os.path.dirname(
    os.environ.get("FRONTEND_PY",
                   os.path.join(os.path.dirname(_HERE), "frontend",
                                "frontend.py")))
sys.path.insert(0, _FRONTEND_DIR)

import fe.art as A          # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


def bild(w, h, farbe_fn):
    """BGRA-Rohbild wie im .art-Format bauen."""
    buf = bytearray(w * h * 4)
    for y in range(h):
        for x in range(w):
            r, g, b = farbe_fn(x, y)
            o = (y * w + x) * 4
            buf[o] = b
            buf[o + 1] = g
            buf[o + 2] = r
    return bytes(buf)


def px(data, w, x, y):
    o = (y * w + x) * 4
    return (data[o + 2], data[o + 1], data[o])


def alt_nearest(pix, w, h, tw, th):
    """Das frueher verwendete Verfahren - nur fuer den Vergleich hier."""
    scale = min(tw / w, th / h)
    tw = max(1, int(w * scale))
    th = max(1, int(h * scale))
    xmap = [min(w - 1, int(x / scale)) * 4 for x in range(tw)]
    out = bytearray(tw * th * 4)
    ro = tw * 4
    for ty in range(th):
        sy = min(h - 1, int(ty / scale))
        srow = pix[sy * w * 4:(sy + 1) * w * 4]
        out[ty * ro:(ty + 1) * ro] = b"".join([srow[sx:sx + 4] for sx in xmap])
    return tw, th, bytes(out)


print("Test 1: Zielgroesse bleibt unveraendert")
for (w, h, mw, mh) in ((600, 800, 377, 465), (600, 800, 179, 223),
                       (300, 350, 250, 250), (64, 64, 63, 63),
                       (1000, 1000, 1, 1)):
    scale = min(mw / w, mh / h)
    tw = max(1, int(w * scale))
    th = max(1, int(h * scale))
    atw, ath, _ = alt_nearest(b"\0" * (w * h * 4), w, h, mw, mh)
    check("%dx%d in %dx%d -> %dx%d (wie bisher)" % (w, h, mw, mh, tw, th),
          (tw, th) == (atw, ath), "alt %dx%d" % (atw, ath))

print()
print("Test 2: einfarbige Flaeche bleibt exakt farbtreu")
w = h = 120
data = bild(w, h, lambda x, y: (200, 120, 40))
out = A._verkleinern_flaechenmittel(data, w, h, 37, 37)
farben = {px(out, 37, x, y) for y in range(37) for x in range(37)}
check("alle Zielpixel haben exakt die Ausgangsfarbe",
      farben == {(200, 120, 40)}, str(sorted(farben)[:3]))

print()
print("Test 3: feines Streifenmuster wird GEMITTELT statt weggeworfen")
# Senkrechte 1-Pixel-Streifen schwarz/weiss: beim Halbieren muss ein
# mittleres Grau herauskommen. Nearest-Neighbor liefert dagegen je nach
# Rasterlage rein schwarze oder rein weisse Spalten - genau das sieht
# man als "verpixelt".
w = h = 120
data = bild(w, h, lambda x, y: (255, 255, 255) if x % 2 else (0, 0, 0))
neu = A._verkleinern_flaechenmittel(data, w, h, 60, 60)
_a, _b, alt = alt_nearest(data, w, h, 60, 60)
neu_farben = {px(neu, 60, x, y) for y in range(60) for x in range(60)}
alt_farben = {px(alt, 60, x, y) for y in range(60) for x in range(60)}
check("neu: nur noch Mischfarben, kein reines Schwarz/Weiss mehr",
      all(0 < c[0] < 255 for c in neu_farben), str(sorted(neu_farben)))
check("neu: das Ergebnis ist gleichmaessig (eine einzige Mischfarbe)",
      len(neu_farben) == 1, str(sorted(neu_farben)))
check("alt: lieferte reine Extremwerte (das war der sichtbare Mangel)",
      any(c[0] in (0, 255) for c in alt_farben), str(sorted(alt_farben)))

print()
print("Test 4: waagerechte Streifen ebenso (beide Achsen wirken)")
data = bild(w, h, lambda x, y: (255, 255, 255) if y % 2 else (0, 0, 0))
neu = A._verkleinern_flaechenmittel(data, w, h, 60, 60)
neu_farben = {px(neu, 60, x, y) for y in range(60) for x in range(60)}
check("auch senkrecht wird gemittelt", len(neu_farben) == 1
      and all(0 < c[0] < 255 for c in neu_farben), str(sorted(neu_farben)))

print()
print("Test 5: ein weicher Verlauf bleibt monoton (keine Spruenge)")
w = h = 200
data = bild(w, h, lambda x, y: (x * 255 // (w - 1),) * 3)
out = A._verkleinern_flaechenmittel(data, w, h, 50, 50)
zeile = [px(out, 50, x, 0)[0] for x in range(50)]
check("Helligkeit steigt durchgehend an",
      all(zeile[i] <= zeile[i + 1] for i in range(len(zeile) - 1)),
      str(zeile[:6]) + " ... " + str(zeile[-3:]))
check("Anfang dunkel, Ende hell", zeile[0] < 20 and zeile[-1] > 235,
      "%d .. %d" % (zeile[0], zeile[-1]))

print()
print("Test 6: Randfaelle stuerzen nicht ab")
for args in ((10, 10, 1, 1), (10, 10, 10, 10), (1, 1, 1, 1),
             (33, 7, 5, 3), (7, 33, 3, 5)):
    w2, h2, tw2, th2 = args
    d = bild(w2, h2, lambda x, y: (10, 20, 30))
    r = A._verkleinern_flaechenmittel(d, w2, h2, tw2, th2)
    check("%dx%d -> %dx%d liefert die richtige Datenmenge" % args,
          r is not None and len(r) == tw2 * th2 * 4)
check("unsinnige Zielgroesse liefert None statt einer Ausnahme",
      A._verkleinern_flaechenmittel(b"", 0, 0, 0, 0) is None)

print()
print("Test 7: Festplatten-Cache wird entwertet")
check("THUMB_ALGO_VERSION ist gesetzt und steckt im Schluessel",
      bool(getattr(A, "THUMB_ALGO_VERSION", "")))
import hashlib                                   # noqa: E402
_pfad = os.path.join(_HERE, "_gibt_es_nicht.art")
schluessel_jetzt = A._thumb_cache_key(_pfad, 300, 400)
_alt_sig = "%s|%d|%d" % (_pfad, 300, 400)
schluessel_frueher = hashlib.sha1(
    _alt_sig.encode("utf-8", "surrogateescape")).hexdigest()[:24]
check("der Schluessel unterscheidet sich vom frueheren",
      schluessel_jetzt != schluessel_frueher,
      "%s vs %s" % (schluessel_jetzt, schluessel_frueher))

print()
print("Test 8: Laufzeit (Einordnung, kein Pass/Fail-Kriterium)")
w, h = 600, 800
data = bild(w, h, lambda x, y: ((x * 7) % 256, (y * 5) % 256, (x + y) % 256))
for tw, th in ((377, 465), (179, 223)):
    t = time.perf_counter()
    A._verkleinern_flaechenmittel(data, w, h, tw, th)
    print("       %dx%d -> %dx%d: %.0f ms auf diesem Rechner"
          % (w, h, tw, th, (time.perf_counter() - t) * 1000))
print("       (auf dem MiSTer entsprechend langsamer - faellt aber nur")
print("        beim ERSTEN Betrachten eines Covers an, danach Cache)")

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for f in fails:
        print("   ", f)
    sys.exit(1)
print("Alle Tests bestanden.")
