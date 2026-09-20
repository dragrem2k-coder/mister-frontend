#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scharf verkleinern statt weich (Build 175).

WORUM ES GEHT

Cover werden bisher mit dem Flaechenmittel verkleinert: jeder
Zielpunkt ist der Durchschnitt der Quellpunkte, die auf ihn fallen.
Das ist auf HDMI das bessere Bild und seit Build 118/155 sorgfaeltig
optimiert.

Auf einer Roehre ist es oft das schlechtere. Pixelkunst wird zu
weichem Brei, und das Weichzeichnen uebernimmt die Maske der Roehre
ohnehin selbst. Deshalb jetzt wahlweise Nearest-Neighbor: je
Zielpunkt genau EIN Quellpunkt, ohne zu mitteln.

DIE FALLE, DIE DIESE SACHE UNBRAUCHBAR MACHEN WUERDE

Der Miniaturen-Cache. Ohne den Modus im Cache-Schluessel wuerde nach
dem Umschalten weiterhin die ALTE Miniatur getroffen - das Bild
bliebe unveraendert, der Schalter schiene kaputt, und man wuerde
tagelang im Zeichenweg suchen. (Dieses Muster kennen wir aus dieser
Woche zur Genuege.)

Deshalb traegt der Schluessel ein Zeichen: "s" oder "f". Beide
Fassungen duerfen nebeneinander liegen - wer zurueckschaltet, hat
seine alten Miniaturen sofort wieder da.

Ausfuehren:
    python3 tools/test_scharf_verkleinern.py
"""
import io
import os
import sys

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
sys.path.insert(0, os.path.join(_REPO, "frontend"))

# Auf dem Entwicklungsrechner liegt neben der ARM-Bibliothek eine
# x86-Fassung - dieselbe Quelle, nur fuer diesen Rechner uebersetzt.
# Ohne sie waere Test 2 ("C und Python rechnen dasselbe") ein Test,
# der nichts prueft. Genauso macht es tools/test_c_modul.py.
if not os.environ.get("DRAGEND_LIB"):
    for _kandidat in (os.path.join(_REPO, "frontend", "c",
                                   "libdragend_x86.so"),
                      os.path.join(_REPO, "frontend", "libdragend_x86.so")):
        if os.path.exists(_kandidat):
            os.environ["DRAGEND_LIB"] = _kandidat
            break

import fe.art as A                                       # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


def bild(w, h):
    """Ein Muster mit harten Kanten - gerade daran sieht man den
    Unterschied zwischen mitteln und auswaehlen."""
    raus = bytearray(w * h * 4)
    for y in range(h):
        for x in range(w):
            i = (y * w + x) * 4
            hell = 255 if ((x // 3) + (y // 3)) % 2 else 0
            raus[i] = hell
            raus[i + 1] = (x * 5) % 256
            raus[i + 2] = (y * 7) % 256
            raus[i + 3] = 0
    return bytes(raus)


W, H, TW, TH = 120, 160, 37, 49
QUELLE = bild(W, H)

# ---------------------------------------------------------------------------
print("Test 1: beide Verfahren liefern ein vollstaendiges Bild")
# ---------------------------------------------------------------------------
weich = A._verkleinern_flaechenmittel(QUELLE, W, H, TW, TH)
scharf = A._verkleinern_nearest(QUELLE, W, H, TW, TH)
check("weich hat die richtige Groesse", len(weich) == TW * TH * 4,
      "%d" % len(weich))
check("scharf auch", len(scharf) == TW * TH * 4, "%d" % len(scharf))
check("und sie sind NICHT gleich", bytes(weich) != bytes(scharf))

# ---------------------------------------------------------------------------
print()
print("Test 2: C und Python rechnen dasselbe")
# ---------------------------------------------------------------------------
# Sonst haengt das Bild davon ab, ob libdragend geladen ist - und ein
# Unterschied faellt erst auf, wenn jemand ohne die Bibliothek
# unterwegs ist.
py = A._verkleinern_nearest_py(QUELLE, W, H, TW, TH)
check("libdragend ist fuer diesen Lauf geladen", A._LIB is not None,
      "sonst prueft Test 2 nichts - DRAGEND_LIB setzen")
check("C und Python sind bitgleich", bytes(scharf) == bytes(py))

# Und ueber viele Groessen, nicht nur eine.
import random                                            # noqa: E402
rnd = random.Random(7)
unterschiede = 0
for _ in range(25):
    w = rnd.randint(8, 90)
    h = rnd.randint(8, 90)
    tw = rnd.randint(1, w)
    th = rnd.randint(1, h)
    q = bild(w, h)
    if bytes(A._verkleinern_nearest(q, w, h, tw, th)) != \
            bytes(A._verkleinern_nearest_py(q, w, h, tw, th)):
        unterschiede += 1
        print("    Abweichung bei %dx%d -> %dx%d" % (w, h, tw, th))
check("auch bei 25 Zufallsgroessen", unterschiede == 0,
      "%d Abweichungen" % unterschiede)

# ---------------------------------------------------------------------------
print()
print("Test 3: scharf nimmt ECHTE Quellpunkte, weich mittelt")
# ---------------------------------------------------------------------------
# Das ist der inhaltliche Unterschied, nicht nur "die Bytes sind
# anders": jeder Punkt im scharfen Bild muss so im Original vorkommen.
quellpunkte = set()
for y in range(H):
    for x in range(W):
        i = (y * W + x) * 4
        quellpunkte.add(bytes(QUELLE[i:i + 4]))
fremd_scharf = sum(1 for i in range(0, len(scharf), 4)
                   if bytes(scharf[i:i + 4]) not in quellpunkte)
fremd_weich = sum(1 for i in range(0, len(weich), 4)
                  if bytes(weich[i:i + 4]) not in quellpunkte)
check("scharf erfindet keinen einzigen Farbwert", fremd_scharf == 0,
      "%d erfundene" % fremd_scharf)
check("weich dagegen schon (es mittelt ja)", fremd_weich > 0,
      "%d gemittelte" % fremd_weich)

# ---------------------------------------------------------------------------
print()
print("Test 4: derselbe Ausschnitt, nur andere Schaerfe")
# ---------------------------------------------------------------------------
# Beide muessen auf demselben Raster liegen - sonst waere der
# Umschalter ein Bildversatz, und das sieht aus wie ein Fehler.
quelle = io.open(os.path.join(_REPO, "frontend", "c", "dragend.c"),
                 encoding="utf-8").read()
i = quelle.index("int skalieren_nearest(")
rumpf = quelle[i:]
check("die C-Fassung rechnet die Spalte wie das Flaechenmittel",
      "(int)((double)(x * w) / (double)tw)" in rumpf)
check("und die Zeile ebenso",
      "(int)((double)(ty * h) / (double)th)" in rumpf)
# Die Ecken muessen uebereinstimmen: oben links ist in beiden
# Verfahren derselbe Quellbereich.
check("oben links stammt aus derselben Ecke",
      scharf[0:4] == QUELLE[0:4])

# ---------------------------------------------------------------------------
print()
print("Test 5: DER CACHE-SCHLUESSEL - die eigentliche Falle")
# ---------------------------------------------------------------------------
pfad = os.path.join(_REPO, "frontend", "frontend.py")   # irgendeine Datei
A._scharf_an = False
k_weich = A._thumb_cache_key(pfad, 231, 420)
A._scharf_an = True
k_scharf = A._thumb_cache_key(pfad, 231, 420)
check("der Schluessel unterscheidet sich je Modus", k_weich != k_scharf,
      "%s vs %s" % (k_weich[:10], k_scharf[:10]))
A._scharf_an = False
check("und ist beim Zurueckschalten wieder derselbe",
      A._thumb_cache_key(pfad, 231, 420) == k_weich,
      "beide Fassungen duerfen nebeneinander liegen")
check("das Kuerzel ist f bzw. s",
      A.verkleinern_modus_kuerzel() == "f")
A._scharf_an = True
check("", A.verkleinern_modus_kuerzel() == "s")

# Auch fuer eine Datei, die es gar nicht gibt (der except-Zweig).
A._scharf_an = False
a = A._thumb_cache_key("/gibt/es/nicht", 100, 100)
A._scharf_an = True
b = A._thumb_cache_key("/gibt/es/nicht", 100, 100)
check("auch ohne Datei unterscheiden sich die Schluessel", a != b)

# ---------------------------------------------------------------------------
print()
print("Test 6: der Merker wird beim Umschalten verworfen")
# ---------------------------------------------------------------------------
# Ohne das zeichnet das Frontend bis zum Neustart im alten Modus
# weiter - der Schalter taete scheinbar nichts.
A._scharf_an = True
A.verkleinern_modus_vergessen()
check("nach dem Vergessen wird neu nachgesehen", A._scharf_an is None)

quelle_fm = io.open(pfad, encoding="utf-8").read()
check("der Menuepunkt verwirft ihn auch",
      "verkleinern_modus_vergessen()" in quelle_fm)
check("und leert die Bildspeicher im RAM",
      "ART.cache.clear()" in quelle_fm)
check("aber NICHT den Cache auf der Karte",
      "thumb_cache_leeren()" not in quelle_fm.split(
          'kind == "scharf_verkleinern"')[1][:900],
      "die alten Miniaturen sollen liegen bleiben")

# ---------------------------------------------------------------------------
print()
print("Test 7: EIN Einstieg, nicht zwei")
# ---------------------------------------------------------------------------
art_quelle = io.open(os.path.join(_REPO, "frontend", "fe", "art.py"),
                     encoding="utf-8").read()
code = "\n".join(z for z in art_quelle.splitlines()
                 if not z.strip().startswith("#"))
check("der Zeichenweg ruft _verkleinern(), nicht direkt ein Verfahren",
      code.count("data = _verkleinern(pix, w, h, tw, th)") == 2,
      "%d" % code.count("data = _verkleinern(pix, w, h, tw, th)"))
check("und niemand ruft das Flaechenmittel mehr direkt",
      "data = _verkleinern_flaechenmittel(" not in code)

# ---------------------------------------------------------------------------
print()
print("Test 8: die Bibliothek passt zur Erwartung")
# ---------------------------------------------------------------------------
check("die Version wurde hochgezaehlt", A.DRAGEND_LIB_VERSION == 3,
      str(A.DRAGEND_LIB_VERSION))
check("die C-Datei meldet dieselbe",
      "int dragend_version(void) { return 3; }" in quelle)
for datei in ("libdragend.so", "libdragend_x86.so"):
    p = os.path.join(_REPO, "frontend", datei)
    check("%s liegt neu gebaut bereit" % datei, os.path.exists(p))

import fe.translations as T                              # noqa: E402
for schluessel in ("sys_scharf_on", "sys_scharf_off", "sys_scharf_changed"):
    e = T.TRANSLATIONS.get(schluessel)
    check("Text %-20s in beiden Sprachen" % schluessel,
          bool(e) and bool(e.get("de")) and bool(e.get("en")),
          "" if e else "fehlt ganz")

A._scharf_an = None

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
