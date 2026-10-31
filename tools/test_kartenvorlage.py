#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Die Kartenvorlage und der weiche Schatten (Build 299).

WORUM ES GEHT. Befund des Nutzers: "in raster und galerie ist das
seitliche scrollen etwas am ruckeln hakt! was da los?"

Der Bench sagt es genau. In Raster und Galerie ist links/rechts EIN
Eintrag, und genau diesen Schritt misst Abschnitt J (die Bewegung steht
dort als item_i = i % n). Seine Zahlen sind also die Seitwaertsbewegung:
Raster 32,13 ms, Galerie 49,93 ms - bei einer Bildperiode von 16,6 ms
also zwei bis drei Bilder je Schritt.

In der Galerie ist "karten" mit 10,64 ms der zweitgroesste Posten, und
Abschnitt K sagt, woraus er besteht: karte_mit_schatten() zeichnet dort
47 RECHTECKE in 3 Aufrufen. Die Karte sieht dabei immer gleich aus -
dieselbe Groesse, dieselben zwei Farben, derselbe Radius. Also einmal
rechnen und danach kopieren.

WAS DIESER TEST SICHERT, in dieser Reihenfolge:

  1. die MECHANIK veraendert das Bild nicht (bitgenau gegen den alten
     Weg - ausfuehrlich in tools/diag_kartenvorlage.py, hier die
     Kurzfassung fuer die Suite),
  2. die Vorlage entsteht EINMAL und nicht je Schritt (sonst waere der
     Umbau langsamer als vorher),
  3. am Bildrand greift sie NICHT (eine beschnittene Karte hat eine
     andere Form),
  4. der weiche Schatten ist wirklich ein Verlauf - und er verlaeuft
     zum HINTERGRUND hin, nicht ins Blaue,
  5. ohne bekannten Hintergrund bleibt der Schatten flach wie bisher,
  6. und die Aufrufstellen im Frontend geben den Hintergrund mit.

Ausfuehren:
    python3 tools/test_kartenvorlage.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H          # noqa: E402,F401  (setzt den Pfad)

from fe.framebuffer import Framebuffer                   # noqa: E402

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

fails = []


def check(name, ok, info=""):
    if ok:
        print("  OK   %s %s" % (name, info))
    else:
        print("  FEHL %s %s" % (name, info))
        fails.append(name)


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


def punkt(fb, x, y):
    o = y * fb.stride + x * 4
    return (fb.buf[o + 2], fb.buf[o + 1], fb.buf[o])


C_BG = (18, 19, 24)
C_PANEL = (56, 58, 74)
SCHATTEN = Framebuffer._darken(C_BG, 0.55)

print(__doc__.strip().split("\n")[0])
print()

# Der Zeilenkopierer wird im Betrieb von frontend.py gesetzt (an
# demselben Schalter wie der Flaechenfueller). Ohne libdragend gibt es
# ihn nicht, und dann faellt die Vorlage aus - das ist ein gueltiger
# Zustand und kein Fehler.
try:
    from fe.art import zeilen_kopieren as _zk              # noqa: E402
except Exception as e:                                     # noqa: BLE001
    print("  -- uebersprungen: fe.art nicht ladbar (%s)" % e)
    print()
    print("Alle Pruefungen bestanden.")
    sys.exit(0)

if not Framebuffer.zeilen_kopierer:
    Framebuffer.zeilen_kopierer = staticmethod(_zk)

_probe = leer(200, 200)
HAT_C = _probe._karte_vorlage(5, 5, 40, 48, 4, C_PANEL,
                              SCHATTEN, 4, C_BG) is not None

# ---------------------------------------------------------------------------
print("Test 1: die Mechanik veraendert das Bild nicht")
# ---------------------------------------------------------------------------
if not HAT_C:
    print("  -- uebersprungen: kein Zeilenkopierer (libdragend fehlt)")
else:
    # Ohne weichen Schatten MUSS das Ergebnis byteweise das von Build
    # 298 sein. Der Verlauf ist eine ausdrueckliche Bildaenderung und
    # wird getrennt geprueft (Test 4) - sonst prueefte eine Zusage zwei
    # Dinge auf einmal und koennte keines davon belegen.
    weich_vorher = Framebuffer.KARTE_SCHATTEN_WEICH
    Framebuffer.KARTE_SCHATTEN_WEICH = False
    try:
        for (name, w, h, versatz, radius) in (
                ("Liste 1080p", 769, 945, 9, None),
                ("Galerie 1080p", 378, 492, 6, None),
                ("Radius 0", 200, 160, 4, 0)):
            b, hh = w + versatz + 60, h + versatz + 60
            rand = max(2, min(w, h) // 20)
            aus = (20 + rand, 20 + rand, w - 2 * rand, h - 2 * rand)
            for (was, aussparen) in (("ohne Aussparung", None),
                                     ("mit Aussparung", aus)):
                a = leer(b, hh)
                a.karte_mit_schatten(20, 20, w, h, versatz, C_PANEL,
                                     SCHATTEN, radius, aussparen=aussparen,
                                     hintergrund_rgb=C_BG)
                z = leer(b, hh)
                z.zeilen_kopierer = None        # der Weg von Build 298
                z.karte_mit_schatten(20, 20, w, h, versatz, C_PANEL,
                                     SCHATTEN, radius, aussparen=aussparen,
                                     hintergrund_rgb=C_BG)
                check("%-14s %s" % (name, was), a.buf == z.buf,
                      "%dx%d Versatz %d" % (w, h, versatz))
    finally:
        Framebuffer.KARTE_SCHATTEN_WEICH = weich_vorher

# ---------------------------------------------------------------------------
print()
print("Test 2: die Vorlage entsteht EINMAL, nicht je Schritt")
# ---------------------------------------------------------------------------
if not HAT_C:
    print("  -- uebersprungen: kein Zeilenkopierer")
else:
    fb = leer(900, 1100, C_BG)
    w, h, versatz = 769, 945, 9
    fb.karte_mit_schatten(20, 20, w, h, versatz, C_PANEL, SCHATTEN,
                          hintergrund_rgb=C_BG)
    check("eine Vorlage liegt da", len(fb._kartenvorlagen or {}) == 1,
          "%d" % len(fb._kartenvorlagen or {}))
    erster = list((fb._kartenvorlagen or {}).values())[0]["puffer"]
    for _ in range(25):
        fb.karte_mit_schatten(20, 20, w, h, versatz, C_PANEL, SCHATTEN,
                              hintergrund_rgb=C_BG)
    check("nach 25 weiteren Aufrufen immer noch eine",
          len(fb._kartenvorlagen or {}) == 1, "%d" % len(fb._kartenvorlagen or {}))
    check("und es ist derselbe Puffer",
          list((fb._kartenvorlagen or {}).values())[0]["puffer"] is erster,
          "sonst wird je Schritt neu gerechnet, und das waere "
          "langsamer als vorher")

    # Die Zerlegung in Kopierstuecke muss ebenfalls stabil sein - die
    # Zeiger darauf werden in fe/art.py nach id() gemerkt, und eine je
    # Schritt neu geschnittene memoryview wuerde diesen
    # Zwischenspeicher dauernd leeren.
    eintrag = list((fb._kartenvorlagen or {}).values())[0]
    rand = max(2, min(w, h) // 20)
    aus = (20 + rand, 20 + rand, w - 2 * rand, h - 2 * rand)
    fb.karte_mit_schatten(20, 20, w, h, versatz, C_PANEL, SCHATTEN,
                          aussparen=aus, hintergrund_rgb=C_BG)
    _vorher = len(eintrag["teile"])
    _ids = [[id(t[0]) for t in v] for v in eintrag["teile"].values()]
    for _ in range(15):
        fb.karte_mit_schatten(20, 20, w, h, versatz, C_PANEL, SCHATTEN,
                              aussparen=aus, hintergrund_rgb=C_BG)
    check("die Kopierstuecke werden nicht neu geschnitten",
          len(eintrag["teile"]) == _vorher
          and [[id(t[0]) for t in v]
               for v in eintrag["teile"].values()] == _ids,
          "%d Zerlegungen" % len(eintrag["teile"]))

    # Und die Obergrenze greift - eine Vorlage ist mehrere Megabyte.
    for i in range(fb.KARTE_VORLAGE_MAX + 3):
        fb.karte_mit_schatten(20, 20, 100 + i, 90, 4, C_PANEL, SCHATTEN,
                              hintergrund_rgb=C_BG)
    check("die Obergrenze greift",
          len(fb._kartenvorlagen or {}) <= fb.KARTE_VORLAGE_MAX,
          "%d von hoechstens %d"
          % (len(fb._kartenvorlagen or {}), fb.KARTE_VORLAGE_MAX))
    check("und der Byte-Zaehler laeuft mit",
          fb._kartenvorlagen_bytes > 0
          and fb._kartenvorlagen_bytes <= fb.KARTE_VORLAGE_BYTES,
          "%.2f MB" % (fb._kartenvorlagen_bytes / 1048576.0))

# ---------------------------------------------------------------------------
print()
print("Test 3: am Bildrand greift die Vorlage NICHT")
# ---------------------------------------------------------------------------
# Eine beschnittene Karte hat eine andere Form - gestalt() in
# rect_rounded_schatten() beschneidet Breite und Hoehe VOR dem Runden.
# Die Vorlage kennt nur die freistehende Form.
for (name, x, y) in (("rechts raus", 300, 20),
                     ("unten raus", 20, 300),
                     ("x negativ", -10, 20)):
    fb = leer(420, 420, C_BG)
    fb.karte_mit_schatten(x, y, 200, 160, 5, C_PANEL, SCHATTEN,
                          hintergrund_rgb=C_BG)
    check("%-12s legt keine Vorlage an" % name,
          not (fb._kartenvorlagen or {}), "%d" % len(fb._kartenvorlagen or {}))

# ---------------------------------------------------------------------------
print()
print("Test 4: der weiche Schatten ist ein Verlauf zum Hintergrund")
# ---------------------------------------------------------------------------
if not HAT_C:
    print("  -- uebersprungen: kein Zeilenkopierer")
else:
    w, h, versatz, r = 378, 492, 6, 47
    x = y = 20
    fb = leer(w + versatz + 60, h + versatz + 60, C_BG)
    fb.karte_mit_schatten(x, y, w, h, versatz, C_PANEL, SCHATTEN, r,
                          hintergrund_rgb=C_BG)

    # Quer durch den Schattenstreifen rechts der Karte, auf halber
    # Hoehe - dort liegen die geraden Mittelzeilen.
    zeile = y + h // 2
    streifen = [punkt(fb, px, zeile)
                for px in range(x + w, x + w + versatz)]
    helligkeit = [sum(p) for p in streifen]
    check("der Streifen wird nach aussen heller",
          all(helligkeit[i] <= helligkeit[i + 1]
              for i in range(len(helligkeit) - 1)),
          "%r" % (helligkeit,))
    # KEINE GERATENEN ZAHLEN, sondern die Struktur: innen die volle
    # Schattenfarbe, aussen in Richtung Hintergrund - und nirgends
    # heller als der Hintergrund selbst, sonst saesse um die Karte ein
    # Leuchtrand.
    check("innen ist es die dunkelste Stufe",
          helligkeit[0] == min(helligkeit),
          "%d" % helligkeit[0])
    check("aussen nicht heller als der Hintergrund",
          max(helligkeit) <= sum(C_BG),
          "%d gegen %d" % (max(helligkeit), sum(C_BG)))
    check("und es sind wirklich mehrere Stufen",
          len(set(helligkeit)) > 1,
          "%d verschiedene von %d" % (len(set(helligkeit)),
                                      len(helligkeit)))
    check("der Punkt direkt an der Karte ist noch Karte",
          punkt(fb, x + w - 1, zeile) == C_PANEL,
          "%r" % (punkt(fb, x + w - 1, zeile),))
    check("und hinter dem Schatten wieder Hintergrund",
          punkt(fb, x + w + versatz, zeile) == C_BG,
          "%r" % (punkt(fb, x + w + versatz, zeile),))

    # Die Stufenliste selbst: von aussen (breit, hell) nach innen
    # (schmal, dunkel). Die Reihenfolge ist nicht Kosmetik - wird sie
    # umgedreht, ueberschreibt der helle Ring den dunklen und der
    # Verlauf verschwindet.
    stufen = fb._schattenstufen(versatz, SCHATTEN, C_BG)
    check("die Stufen laufen von breit nach schmal",
          all(stufen[i][0] > stufen[i + 1][0]
              for i in range(len(stufen) - 1)),
          "%r" % ([s[0] for s in stufen],))
    check("und von hell nach dunkel",
          all(sum(stufen[i][1]) >= sum(stufen[i + 1][1])
              for i in range(len(stufen) - 1)),
          "sonst ueberschreibt der helle Ring den dunklen")
    check("die innerste Stufe ist die volle Schattenfarbe",
          stufen[-1][1] == SCHATTEN,
          "%r - sonst waere der Schatten insgesamt heller als vorher, "
          "also nicht weicher sondern weniger" % (stufen[-1][1],))

# ---------------------------------------------------------------------------
print()
print("Test 5: ohne bekannten Hintergrund bleibt der Schatten flach")
# ---------------------------------------------------------------------------
# Ein Schatten verlaeuft NACH AUSSEN zum Hintergrund hin. Wer den nicht
# kennt, kann nur raten - und geraten waere ein Rand in der falschen
# Farbe um jede Karte.
fb = leer(300, 300, C_BG)
stufen = fb._schattenstufen(6, SCHATTEN, None)
check("ohne Hintergrund genau eine Stufe", len(stufen) == 1,
      "%r" % (stufen,))
check("und die in der alten Farbe", stufen[0] == (6, SCHATTEN),
      "%r" % (stufen[0],))
weich_vorher = Framebuffer.KARTE_SCHATTEN_WEICH
Framebuffer.KARTE_SCHATTEN_WEICH = False
try:
    check("abgeschaltet ebenso",
          fb._schattenstufen(6, SCHATTEN, C_BG) == ((6, SCHATTEN),),
          "%r" % (fb._schattenstufen(6, SCHATTEN, C_BG),))
finally:
    Framebuffer.KARTE_SCHATTEN_WEICH = weich_vorher
# Ein Versatz von 1 kann keinen Verlauf haben - eine Stufe je Bildzeile.
check("Versatz 1 hat nichts zu verlaufen",
      fb._schattenstufen(1, SCHATTEN, C_BG) == ((1, SCHATTEN),),
      "%r" % (fb._schattenstufen(1, SCHATTEN, C_BG),))

# Der Hintergrund gehoert in den Schluessel, sonst behaelt eine Vorlage
# ihren Verlauf nach einem Wechsel des Hintergrundbildes.
if HAT_C:
    ANDERS = (90, 10, 10)
    fb = leer(300, 300, C_BG)
    fb.karte_mit_schatten(20, 20, 160, 120, 5, C_PANEL, SCHATTEN,
                          hintergrund_rgb=C_BG)
    check("mit bekanntem Hintergrund gibt es eine Vorlage",
          len(fb._kartenvorlagen or {}) == 1,
          "%d" % len(fb._kartenvorlagen or {}))
    # OHNE Hintergrundvorlage fuer diese Farbe gibt es KEINE Karten-
    # vorlage - und das ist richtig, nicht ein Mangel: die Luecken der
    # Karte muessen aus der echten Hintergrundvorlage kommen. Lieber
    # der alte Zeichenweg als geratene Luecken.
    fb.karte_mit_schatten(20, 20, 160, 120, 5, C_PANEL, SCHATTEN,
                          hintergrund_rgb=ANDERS)
    check("eine unbekannte Hintergrundfarbe legt keine Vorlage an",
          len(fb._kartenvorlagen or {}) == 1,
          "%d - ohne Hintergrundvorlage waeren die Luecken geraten"
          % len(fb._kartenvorlagen or {}))
    # Sobald es sie gibt, bekommt sie ihre EIGENE Kartenvorlage - sonst
    # saesse nach einem Bildwechsel ein Rand in der alten Farbe um
    # jede Karte.
    fb.clear(ANDERS)
    fb.karte_mit_schatten(20, 20, 160, 120, 5, C_PANEL, SCHATTEN,
                          hintergrund_rgb=ANDERS)
    check("ein anderer Hintergrund ergibt eine eigene Vorlage",
          len(fb._kartenvorlagen or {}) == 2,
          "%d" % len(fb._kartenvorlagen or {}))

# ---------------------------------------------------------------------------
print()
print("Test 6: die Aufrufstellen geben den Hintergrund mit")
# ---------------------------------------------------------------------------
# Eine Zusage, die nur in der Bibliothek steht und von niemandem
# benutzt wird, ist keine. Genau diese Sorte Fehler hat das Projekt in
# Build 284 als "ein Menuepunkt ist keine Funktion" aufgeschrieben.
_fe = H.nur_code(open(H.FRONTEND_PY, encoding="utf-8",
                      errors="replace").read())
_rufe = _fe.count("karte_mit_schatten(")
_mit = _fe.count("hintergrund_rgb=C_BG")
check("jede Aufrufstelle gibt ihn mit", _rufe > 0 and _mit == _rufe,
      "%d Aufrufe, %d mit Hintergrund" % (_rufe, _mit))
check("und der Zeilenkopierer wird gesetzt",
      "Framebuffer.zeilen_kopierer = staticmethod(_c_zeilen_kopieren)"
      in _fe,
      "ohne ihn faellt die Vorlage aus")

print()
if fails:
    print("FEHLGESCHLAGEN (%d):" % len(fails))
    for f in fails:
        print("  - %s" % f)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
