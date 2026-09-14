#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft die vier Beschleunigungen von "Miniaturen vorbereiten" (Build 128).

AUSLOESER, mit Zahlen vom Geraet des Nutzers:

    "Miniaturen vorbereiten laeuft im HDMI-Modus jetzt schon 6 Stunden,
     das ist viel zu lange, das geht garnicht und schreckt ab."

    28517 Cover  x  4 Kastengroessen  =  114068 Cache-Dateien
    Obergrenze bis Build 127:             40000

Das war kein Geschwindigkeitsproblem, sondern ein Durchlauf, der gar
nicht fertig werden KONNTE: ab 40000 Dateien verdraengt der
Zwischenspeicher das Aelteste - also das, was derselbe Durchlauf zwei
Stunden vorher gerechnet hat.

DIE MESSUNG, DIE DEN AUSSCHLAG GAB. Die Flaechenmittelung liest JEDEN
QUELLPUNKT, egal wie klein das Ziel ist. Bei einem 900x1200-PNG:

    Kasten 733x909 (Liste)    162 ms
    Kasten 411x548 (Galerie)  183 ms
    Kasten 128x171 (Raster)    68 ms
    Kasten 124x166 (Leiste)    68 ms   <- fast dieselbe Groesse!

Die winzige Kachel kostet also 40 % der grossen, nicht 3 %. In Build 123
hatte ich genau das Gegenteil behauptet ("die Rasterkacheln sind klein,
das Verkleinern kostet dort einen Bruchteil") und daraus geschlossen,
alle drei Ansichten vorzubereiten sei fast gratis. Das war falsch, und
dieser Test haelt fest, was daraus folgt.

GEPRUEFT WERDEN VIER DINGE:

  1. Es gibt nur noch DREI Kastengroessen, nicht vier - Raster und
     Galerie-Leiste teilen sich eine (kachel_cover_kasten()).
  2. prewarm_thumb_mehrfach() liefert BITGENAU dasselbe wie die
     Einzelaufrufe. Das ist die wichtigste Zusage des ganzen Builds:
     ein Cover wird einmal dekodiert und dann dreimal verkleinert -
     wenn dabei etwas anderes herauskaeme als vorher, waere die
     Beschleunigung wertlos.
  3. Der Passt-genau-Fall legt eine MARKE ab statt einer Kopie, und der
     Zeichenpfad kommt damit zum selben Bild wie vorher.
  4. Die Obergrenze des Zwischenspeichers reicht fuer die Sammlung des
     Nutzers.

Ausfuehren:
    python3 tools/test_vorbereiten_tempo.py
"""
import os
import shutil
import struct
import sys
import tempfile
import zlib

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)

import _harness as H                                    # noqa: E402

fm = H.fm
sys.path.insert(0, os.path.join(_REPO, "frontend"))
import fe.art as A                                      # noqa: E402
import fe.prewarm as P                                  # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


TMP = tempfile.mkdtemp(prefix="vorbereiten_")


def png_bauen(pfad, w, h):
    """Ein fotoartiges PNG von Hand - ohne Fremdbibliothek, damit der
    Test ueberall laeuft. Bewusst KEINE Flaeche: bei einfarbigen Bildern
    ist jede Verkleinerung dasselbe Ergebnis, und ein Vertauschen faellt
    nicht auf."""
    zeilen = []
    for y in range(h):
        r = bytearray([0])                       # Filter 0 je Zeile
        for x in range(w):
            r += bytes(((x * 7 + y * 3) % 256, (x * 3 + y * 11) % 256,
                        (x * 13 + y * 5) % 256))
        zeilen.append(bytes(r))

    def ch(typ, daten):
        return (struct.pack(">I", len(daten)) + typ + daten
                + struct.pack(">I", zlib.crc32(typ + daten) & 0xffffffff))

    with open(pfad, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n"
                + ch(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                + ch(b"IDAT", zlib.compress(b"".join(zeilen), 6))
                + ch(b"IEND", b""))
    return pfad


def cache_leeren():
    shutil.rmtree(A.THUMB_CACHE_DIR, ignore_errors=True)
    os.makedirs(A.THUMB_CACHE_DIR)


def cache_bytes():
    return sum(os.path.getsize(os.path.join(r, x))
               for r, _d, fs in os.walk(A.THUMB_CACHE_DIR) for x in fs)


A.THUMB_CACHE_DIR = os.path.join(TMP, "cache")
os.makedirs(A.THUMB_CACHE_DIR)

# ---------------------------------------------------------------------
print("Test 1: drei Kastengroessen statt vier")
# Das Raster und die Nachbarleiste der Galerie hatten bis Build 127
# eigene Kaesten, die sich um vier Bildpunkte unterschieden (HDMI
# 128x171 gegen 124x166). Vier Punkte, und dadurch eine komplette
# zweite Miniatur je Cover - die Kastengroesse steht im Schluessel.
for breite, hoehe, wie in ((1920, 1080, "HDMI"), (320, 240, "CRT")):
    H.set_screen(breite, hoehe)
    for seite, wo in ((1, "Spieleliste"), (0, "Hauptseite")):
        f = H.make_frontend(page=seite)
        geos = [f._art_panel_geometrie(erzwingen=True)]
        for a in fm.ANSICHTEN:
            if a == "liste":
                continue
            for g in f._ansicht_geometrien(a, erzwingen=True):
                if g not in geos:
                    geos.append(g)
        masse = [(g[1], g[2]) if g[0] == "fest" else (g[0], g[1])
                 for g in geos]
        check("%-4s %-12s drei Kaesten" % (wie, wo), len(geos) == 3,
              repr(masse))
        check("%-4s %-12s und keiner doppelt" % (wie, wo),
              len(set(masse)) == 3, repr(masse))

H.set_screen(1920, 1080)
f = H.make_frontend(page=1)
L = f.layout_items(True)
r = f.raster_geometrie(L)
g = f.galerie_geometrie(L)
check("Raster und Galerie-Leiste benutzen denselben Kasten",
      (r["cov_b"], r["cov_h"]) == (g["klein_b"], g["klein_h"]),
      "Raster %dx%d, Leiste %dx%d"
      % (r["cov_b"], r["cov_h"], g["klein_b"], g["klein_h"]))
# Die Richtung stimmt auch: genommen wird der KLEINERE. Ein Cover, das
# groesser ist als seine Kachel, wuerde darueber hinausragen.
natur_b, natur_h = f._raster_cover_natur(L)
check("und zwar der kleinere von beiden",
      r["cov_h"] <= natur_h and r["cov_h"] <= g["leiste_y"] and True,
      "Raster-Natur %d -> gemeinsam %d" % (natur_h, r["cov_h"]))
check("die Leiste ist weiterhin hoch genug fuer ihren Kasten",
      g["klein_h"] <= (g["unten"] - g["leiste_y"]),
      "Kasten %d, Leiste %d" % (g["klein_h"], g["unten"] - g["leiste_y"]))

# ---------------------------------------------------------------------
print()
print("Test 2: einmal dekodieren liefert BITGENAU dasselbe")
# Die wichtigste Zusage des Builds. prewarm_thumb_mehrfach() dekodiert
# das Original EINMAL und verkleinert daraus alle drei Kaesten - statt
# dreimal zu lesen, zu dekodieren und zu verkleinern.
#
# Was dabei ausdruecklich NICHT passiert: eine fertige Miniatur
# weiterverarbeiten. Jeder Kasten kommt aus demselben dekodierten
# ORIGINAL. Genau deshalb darf das Ergebnis bitgleich sein - und genau
# das wird hier nachgerechnet, statt es zu behaupten.
KAESTEN = [(733, 909), (124, 166), (411, 548)]
for qb, qh in ((600, 800), (900, 1200), (320, 420)):
    p = png_bauen(os.path.join(TMP, "q%dx%d.png" % (qb, qh)), qb, qh)

    cache_leeren()
    for k in KAESTEN:
        A.prewarm_thumb(p, *k)
    einzeln = [A._thumb_cache_get(p, *k) for k in KAESTEN]
    b_einzeln = cache_bytes()

    cache_leeren()
    erg = A.prewarm_thumb_mehrfach(p, KAESTEN)
    mehrfach = [A._thumb_cache_get(p, *k) for k in KAESTEN]

    check("Quelle %dx%-4d bitgenau gleich" % (qb, qh),
          einzeln == mehrfach,
          "" if einzeln == mehrfach else
          repr([(a is None, b is None) for a, b in zip(einzeln, mehrfach)]))
    check("Quelle %dx%-4d jeder Kasten gerechnet" % (qb, qh),
          all(e in ("fertig", "treffer") for e in erg), repr(erg))
    check("Quelle %dx%-4d und gleich viel auf der Karte" % (qb, qh),
          cache_bytes() == b_einzeln,
          "%d vs %d" % (cache_bytes(), b_einzeln))

# Ein zweiter Aufruf darf nichts mehr rechnen - sonst haekelt
# "Miniaturen vorbereiten" ein Cover nie ab.
erg2 = A.prewarm_thumb_mehrfach(p, KAESTEN)
check("beim zweiten Mal sind es lauter Treffer",
      all(e == "treffer" for e in erg2), repr(erg2))

# Eine kaputte Datei darf nicht durchschlagen.
kaputt = os.path.join(TMP, "kaputt.png")
with open(kaputt, "wb") as fh:
    fh.write(b"\x89PNG\r\n\x1a\nMuell")
check("eine kaputte Datei gibt Fehler statt einer Ausnahme",
      A.prewarm_thumb_mehrfach(kaputt, KAESTEN) == ["fehler"] * 3)
check("und eine leere Kastenliste kommt leer zurueck",
      A.prewarm_thumb_mehrfach(p, []) == [])

# ---------------------------------------------------------------------
print()
print("Test 3: der Passt-genau-Fall legt eine MARKE ab, keine Kopie")
# Gemessen bei einem 600x800-Cover im HDMI-Listenkasten (733x909):
#   Cache-Datei 548 KB - Lesen 5.9 ms - Original dekodieren 4.8 ms
# Die gespeicherte Kopie war also groesser als das Original UND
# langsamer, als es einfach neu zu dekodieren.
cache_leeren()
klein = png_bauen(os.path.join(TMP, "klein.png"), 600, 800)
check("prewarm_thumb meldet fertig", A.prewarm_thumb(klein, 733, 909)
      == "fertig")
gross = cache_bytes()
check("die Marke ist winzig statt einer halben Megabyte", gross < 100,
      "%d Byte" % gross)
check("thumb_cache_has sagt trotzdem 'da' - das war der ganze Zweck "
      "(Build 92)", A.thumb_cache_has(klein, 733, 909) is True)
check("_thumb_cache_get liefert die Marke",
      A._thumb_cache_get(klein, 733, 909) is A.ORIGINAL_PASST)
check("thumb_cache_lesen() macht daraus None - eine Marke ist kein Bild",
      A.thumb_cache_lesen(klein, 733, 909) is None)
check("und ein zweiter Durchlauf hakt es ab",
      A.prewarm_thumb(klein, 733, 909) == "treffer")

# Und jetzt die Probe aufs Exempel: der ZEICHENPFAD muss mit Marke
# dasselbe Bild liefern wie ohne. Das ist der Punkt, an dem sich
# entscheidet, ob die Marke eine Sparmassnahme oder ein Fehler ist.
A.ART.cache = {}
A.ART.order = []
A.ART.scaled = {}
A.ART.scaled_order = []
mit_marke = A.ART.get_scaled(klein, 733, 909)
cache_leeren()
A.ART.cache = {}
A.ART.order = []
A.ART.scaled = {}
A.ART.scaled_order = []
ohne_marke = A.ART.get_scaled(klein, 733, 909)
check("der Zeichenpfad liefert mit Marke dasselbe Bild wie ohne",
      mit_marke == ohne_marke,
      "" if mit_marke == ohne_marke else "%r vs %r"
      % (mit_marke[:2] if mit_marke else None,
         ohne_marke[:2] if ohne_marke else None))

quelle = open(os.path.join(_REPO, "frontend", "fe", "art.py"),
              encoding="utf-8", errors="replace").read()
# Der eine Punkt, an dem die Marke gefaehrlich waere: wenn sie in die
# Ueberspring-Pruefung liefe, waere der Fehler von Build 92 halb
# zurueck (Cover blitzen beim Scrollen auf und laden nach). Erlaubt ist
# das Uebergehen nur, weil die Messung sagt, dass Dekodieren billiger
# ist als die frueher dort gelesene Kopie.
check("eine Marke umgeht die Ueberspring-Pruefung",
      "if not marke and self._defer_uncached" in quelle)
check("und auch das Auslagern an den Vorauslader",
      "if (not marke and auslagern_ok" in quelle)

# ---------------------------------------------------------------------
print()
print("Test 4: die Obergrenze reicht fuer die Sammlung des Nutzers")
COVER = 28517                       # gezaehlt auf seinem Geraet
check("bis Build 127 passte nicht einmal die Haelfte hinein",
      COVER * 4 > 40000)
check("mit drei Kaesten und der neuen Grenze passt es",
      COVER * 3 < A.THUMB_CACHE_MAX_FILES,
      "%d noetig, %d erlaubt" % (COVER * 3, A.THUMB_CACHE_MAX_FILES))
# Das Nachzaehlen ist ein Verzeichnisdurchlauf. Bei der neuen Grenze
# darf es nicht mehr so oft laufen wie bei der alten, sonst tauscht man
# das eine Problem gegen ein anderes.
check("und das Nachzaehlen laeuft nicht haeufiger als aufgeraeumt wird",
      A._THUMB_CACHE_NACHZAEHLEN_ALLE
      >= A.THUMB_CACHE_MAX_FILES - int(A.THUMB_CACHE_MAX_FILES * 0.9),
      "nachzaehlen alle %d, Verdraengung raeumt %d"
      % (A._THUMB_CACHE_NACHZAEHLEN_ALLE,
         A.THUMB_CACHE_MAX_FILES - int(A.THUMB_CACHE_MAX_FILES * 0.9)))

# ---------------------------------------------------------------------
print()
print("Test 5: der zweite Kern")
# Geprueft wird der Ablauf mit einer Attrappe statt eines echten
# Prozesses - der Gewinn selbst laesst sich hier nicht messen (diese
# Maschine ist nicht der MiSTer), die REIHENFOLGE aber sehr wohl. Und
# auf die kommt es an: wird erst selbst gerechnet und dann
# hinuebergereicht, ist der zweite Kern genau so lange untaetig, wie
# das eigene Cover dauert - der ganze Gewinn waere weg.
fcode = open(os.path.join(_REPO, "frontend", "frontend.py"),
             encoding="utf-8", errors="replace").read()
ab = fcode.index("kern2 = Doppelkern()")
bis = fcode.index("kern2.beenden()", ab)
stelle = fcode[ab:bis]
check("erst senden, dann selbst rechnen",
      stelle.index("kern2.senden(") < stelle.index("prewarm_thumb_mehrfach("),
      "sonst laeuft der zweite Kern leer")
check("und erst danach die Antwort abholen",
      stelle.index("prewarm_thumb_mehrfach(") < stelle.index("kern2.abholen("))
check("hoechstens EIN Auftrag steht drueben - sonst greift Abbrechen "
      "nicht mehr", "if zwei_kerne and kern2.frei()" in stelle)
check("der Abbruch wird bei jedem Cover geprueft",
      "self.inp.read_action(timeout=0)" in stelle)
check("und der Prozess wird in jedem Fall abgeraeumt",
      "finally:" in fcode[ab:fcode.index("kern2.beenden()", ab) + 40])

d = P.Doppelkern()
check("ohne gestarteten Prozess ist nichts frei", d.frei() is False)
check("senden() lehnt dann ab", d.senden("/x.png", [(10, 10)]) is False)
check("abholen() gibt None", d.abholen() is None)
d.beenden()          # darf auch ungestartet nicht scheitern

# Der Arbeitsprozess muss die Mehrfach-Zeile verstehen - und die alte
# Einzelzeile weiterhin auch, denn der Leerlauf-Vorauslader benutzt sie.
wcode = open(os.path.join(_REPO, "frontend", "fe", "prewarm_worker.py"),
             encoding="utf-8", errors="replace").read()
check("der Arbeitsprozess kennt die Mehrfach-Zeile",
      'zeile.startswith("M\\t")' in wcode
      and "prewarm_thumb_mehrfach" in wcode)
check("und die alte Einzelzeile bleibt gueltig",
      "cachedir, bw, bh, pfad = teile" in wcode)

# Ende zu Ende: den Arbeitsprozess wirklich starten und eine
# Mehrfach-Zeile hindurchschicken. Das ist die einzige Pruefung, die
# das Protokoll auf BEIDEN Seiten gleichzeitig anfasst - ein Tippfehler
# im Trennzeichen faellt sonst erst auf dem Geraet auf.
import subprocess                                        # noqa: E402
cache_leeren()
worker = os.path.join(_REPO, "frontend", "fe", "prewarm_worker.py")
zeile = "M\t%s\t%s\t%s\n" % (A.THUMB_CACHE_DIR,
                             ",".join("%dx%d" % k for k in KAESTEN), klein)
try:
    fertig = subprocess.run(
        [sys.executable, worker], input=zeile.encode(),
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        cwd=os.path.join(_REPO, "frontend"), timeout=120)
    antwort = fertig.stdout.decode("ascii", "replace").strip()
except Exception as e:                                   # noqa: BLE001
    antwort = "<%s>" % e
check("der echte Arbeitsprozess beantwortet eine Mehrfach-Zeile",
      len(antwort) == len(KAESTEN) and set(antwort) <= set("ftu"),
      repr(antwort))
check("und hat dabei wirklich etwas auf die Karte gelegt",
      all(A.thumb_cache_has(klein, *k) for k in KAESTEN))

shutil.rmtree(TMP, ignore_errors=True)

print()
if fails:
    print("FEHLGESCHLAGEN (%d):" % len(fails))
    for f_ in fails:
        print("  -", f_)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
