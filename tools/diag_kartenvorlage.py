#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Die Kartenvorlage (Build 299) gegen den alten Weg - Byte fuer Byte.

WOZU. karte_mit_schatten() zeichnet die Karte bisher aus rund 47
Rechtecken je Aufruf (Bench-Abschnitt K, Galerie). Build 299 rechnet sie
EINMAL je Groesse vor und kopiert sie danach. Das ist nur dann eine
Verbesserung und keine Veraenderung, wenn dabei genau dasselbe Bild
entsteht.

Nachgewiesen wird das nicht durch Nachdenken, sondern durch Vergleich -
genau wie tools/diag_karte_aussparen.py es fuer Build 234 getan hat:
dieselbe Karte zweimal gezeichnet, einmal ueber die Vorlage und einmal
ueber den alten Weg, und dann jedes Byte verglichen.

WICHTIG ZUR REIHENFOLGE: dieses Werkzeug prueft die MECHANIK. Der
weiche Schatten aus demselben Build ist eine ausdrueckliche
Bildaenderung - er wird hier mit KARTE_SCHATTEN_WEICH = False
abgeschaltet, sonst prueefte der Vergleich zwei Dinge auf einmal und
koennte keines von beiden belegen.

Ausfuehren:
    python3 tools/diag_kartenvorlage.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H          # noqa: E402,F401  (setzt den Pfad)

from fe.framebuffer import Framebuffer                   # noqa: E402

fails = []


def check(name, ok, info=""):
    if ok:
        print("  OK   %s %s" % (name, info))
    else:
        print("  FEHL %s %s" % (name, info))
        fails.append(name)


# Die Farben des Betriebs. C_BG muss hier stehen und nicht weiter
# unten: leer() fuellt damit den Hintergrund, und genau aus dieser
# Vorlage holt die Kartenvorlage ihre Luecken.
C_BG = (18, 19, 24)
KARTE = (56, 58, 74)
SCHATTEN = Framebuffer._darken(C_BG, 0.55)


def leer(breite, hoehe, fuell=None):
    """Ein Framebuffer in Prueffassung, mit GEFUELLTEM Hintergrund.

    DAS FUELLEN IST DER PUNKT, nicht Beiwerk. Die erste Fassung dieses
    Helfers baute den Puffer selbst und liess ihn schwarz - und genau
    damit hat er den Fehler durchgelassen, den er finden sollte: die
    Vorlage schrieb Nullen in die Luecken der Karte (Eckenrundungen,
    der Versatz-Winkel), und weil der Vergleichspuffer ebenfalls
    schwarz war, stimmten beide zufaellig ueberein. Gefunden hat es
    tools/test_cover_panel.py, das vorher clear() ruft.

    Ein Vergleich gegen einen leeren Puffer prueft weniger, als er zu
    pruefen verspricht. Deshalb hier derselbe Weg wie im Betrieb:
    clear() legt die Hintergrundvorlage an (samt Vignette), und genau
    aus der holt die Kartenvorlage ihre Luecken."""
    H.set_screen(breite, hoehe)
    fb = Framebuffer()
    fb.clear(fuell if fuell is not None else C_BG)
    return fb


def erste_abweichung(a, b):
    """Index des ersten unterschiedlichen Bytes, oder None."""
    if a == b:
        return None
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return i
    return min(len(a), len(b))


# Der Zeilenkopierer wird normalerweise von frontend.py gesetzt.
try:
    from fe.art import zeilen_kopieren as _zk
except Exception as e:                                   # noqa: BLE001
    print("fe.art nicht ladbar: %s" % e)
    sys.exit(1)

if not Framebuffer.zeilen_kopierer:
    Framebuffer.zeilen_kopierer = staticmethod(_zk)

print(__doc__.strip().split("\n")[0])
print()

# Ohne libdragend gibt es keinen Zeilenkopierer, und dann faellt die
# Vorlage ohnehin aus. Das ist kein Fehler, nur nicht pruefbar.
_probe = leer(200, 200)
if _probe._karte_vorlage(5, 5, 32, 40, 4, KARTE, SCHATTEN, 4,
                         C_BG) is None:
    print("  -- uebersprungen: kein Zeilenkopierer (libdragend fehlt)")
    print()
    print("Alles in Ordnung (nichts zu pruefen).")
    sys.exit(0)

# Der weiche Schatten ist eine BILDAENDERUNG und gehoert nicht in
# diesen Vergleich - siehe Docstring.
_weich_vorher = getattr(Framebuffer, "KARTE_SCHATTEN_WEICH", None)
Framebuffer.KARTE_SCHATTEN_WEICH = False

# ---------------------------------------------------------------------------
# Die Faelle: die beiden echten Kartengroessen des Geraets (Bench K) und
# ein paar Randfaelle. Die Zahlen stammen aus dem Bericht des Nutzers,
# nicht aus der Luft: 769x945 Versatz 9 ist die Boxart-Spalte der Liste,
# 378x492 die Karte der Galerie.
# ---------------------------------------------------------------------------
FAELLE = [
    ("Liste 1080p",   769, 945, 9,  None),
    ("Galerie 1080p", 378, 492, 6,  None),
    ("kleiner Radius", 200, 160, 4, 3),
    ("Radius 0",       200, 160, 4, 0),
    ("quadratisch",    120, 120, 5, None),
    ("breit, flach",   400,  90, 3, None),
]


for (name, w, h, versatz, radius) in FAELLE:
    breite = w + versatz + 60
    hoehe = h + versatz + 60
    x, y = 20, 20

    # Weg A: die Vorlage.
    fb_a = leer(breite, hoehe)
    fb_a.karte_mit_schatten(x, y, w, h, versatz, KARTE, SCHATTEN, radius,
                            hintergrund_rgb=C_BG)

    # Weg B: der alte Weg. Abgeschaltet wird er, indem der
    # Zeilenkopierer fehlt - genau der Zustand ohne libdragend, also
    # kein Sonderpfad nur fuer den Test.
    fb_b = leer(breite, hoehe)
    fb_b.zeilen_kopierer = None
    fb_b.karte_mit_schatten(x, y, w, h, versatz, KARTE, SCHATTEN, radius,
                            hintergrund_rgb=C_BG)

    stelle = erste_abweichung(fb_a.buf, fb_b.buf)
    if stelle is None:
        check("%-15s ohne Aussparung" % name, True,
              "%dx%d Versatz %d" % (w, h, versatz))
    else:
        zeile, spalte = divmod(stelle, fb_a.stride)
        check("%-15s ohne Aussparung" % name, False,
              "erste Abweichung bei Byte %d (Zeile %d, Spalte %d)"
              % (stelle, zeile, spalte // 4))

    # Und mit Aussparung - das Rechteck, das das Cover gleich
    # uebermalt. Die Masse sind die aus der Listenansicht: das Cover
    # sitzt mit kleinem Rand in der Karte.
    rand = max(2, min(w, h) // 20)
    aus = (x + rand, y + rand, w - 2 * rand, h - 2 * rand)

    fb_c = leer(breite, hoehe)
    fb_c.karte_mit_schatten(x, y, w, h, versatz, KARTE, SCHATTEN, radius,
                            aussparen=aus, hintergrund_rgb=C_BG)
    fb_d = leer(breite, hoehe)
    fb_d.zeilen_kopierer = None
    fb_d.karte_mit_schatten(x, y, w, h, versatz, KARTE, SCHATTEN, radius,
                            aussparen=aus, hintergrund_rgb=C_BG)
    stelle = erste_abweichung(fb_c.buf, fb_d.buf)
    if stelle is None:
        check("%-15s mit Aussparung" % name, True)
    else:
        zeile, spalte = divmod(stelle, fb_c.stride)
        check("%-15s mit Aussparung" % name, False,
              "erste Abweichung bei Byte %d (Zeile %d, Spalte %d)"
              % (stelle, zeile, spalte // 4))

# ---------------------------------------------------------------------------
print()
print("Am Bildrand beschnitten: die Vorlage darf NICHT greifen")
# ---------------------------------------------------------------------------
# Eine beschnittene Karte hat eine andere Form (gestalt() beschneidet
# vor dem Runden). Die Vorlage kennt nur die freistehende Form - also
# muss der alte Weg laufen, und das Bild muss gleich bleiben.
for (name, x, y) in (("rechts raus", 300, 20),
                     ("unten raus", 20, 300),
                     ("x negativ", -10, 20)):
    w, h, versatz = 200, 160, 5
    fb_a = leer(420, 420)
    fb_a.karte_mit_schatten(x, y, w, h, versatz, KARTE, SCHATTEN,
                            hintergrund_rgb=C_BG)
    fb_b = leer(420, 420)
    fb_b.zeilen_kopierer = None
    fb_b.karte_mit_schatten(x, y, w, h, versatz, KARTE, SCHATTEN,
                            hintergrund_rgb=C_BG)
    stelle = erste_abweichung(fb_a.buf, fb_b.buf)
    check("%-12s bleibt gleich" % name, stelle is None,
          "" if stelle is None else "Abweichung bei Byte %d" % stelle)
    check("%-12s hat keine Vorlage angelegt" % name,
          not (fb_a._kartenvorlagen or {}),
          "%d Eintraege" % len(fb_a._kartenvorlagen or {}))

# ---------------------------------------------------------------------------
print()
print("Die Vorlage entsteht EINMAL, nicht je Aufruf")
# ---------------------------------------------------------------------------
fb = leer(900, 1100)
w, h, versatz = 769, 945, 9
fb.karte_mit_schatten(20, 20, w, h, versatz, KARTE, SCHATTEN,
                      hintergrund_rgb=C_BG)
check("eine Vorlage liegt da", len(fb._kartenvorlagen or {}) == 1,
      "%d" % len(fb._kartenvorlagen or {}))
erste = list((fb._kartenvorlagen or {}).values())[0]["puffer"]
for _ in range(20):
    fb.karte_mit_schatten(20, 20, w, h, versatz, KARTE, SCHATTEN,
                      hintergrund_rgb=C_BG)
check("nach zwanzig weiteren Aufrufen immer noch eine",
      len(fb._kartenvorlagen or {}) == 1, "%d" % len(fb._kartenvorlagen or {}))
check("und es ist derselbe Puffer",
      list((fb._kartenvorlagen or {}).values())[0]["puffer"] is erste,
      "sonst wird je Schritt neu gerechnet, und das waere langsamer "
      "als vorher")

# Die Obergrenze muss greifen - eine Vorlage ist mehrere Megabyte.
for i in range(fb.KARTE_VORLAGE_MAX + 3):
    fb.karte_mit_schatten(20, 20, 100 + i, 90, 4, KARTE, SCHATTEN,
                          hintergrund_rgb=C_BG)
check("die Obergrenze greift",
      len(fb._kartenvorlagen or {}) <= fb.KARTE_VORLAGE_MAX,
      "%d von hoechstens %d"
      % (len(fb._kartenvorlagen or {}), fb.KARTE_VORLAGE_MAX))

if _weich_vorher is None:
    del Framebuffer.KARTE_SCHATTEN_WEICH
else:
    Framebuffer.KARTE_SCHATTEN_WEICH = _weich_vorher

print()
if fails:
    print("FEHLGESCHLAGEN (%d):" % len(fails))
    for f in fails:
        print("  - %s" % f)
    sys.exit(1)
print("Alles in Ordnung.")
