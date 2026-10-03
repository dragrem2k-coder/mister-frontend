#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Der Textzeichner in C (Build 227).

WAS HIER AUF DEM SPIEL STEHT. Bis Build 226 ist JEDE Textzeile des
Frontends durch dieselbe Python-Schleife gegangen: acht Glyphenzeilen
bauen, zu einem Streifen fuegen, Zeile fuer Zeile in den Puffer
schneiden. Jetzt gibt es einen zweiten Weg, der dieselben Bildpunkte
erzeugen MUSS - und zwar bitgenau, denn sonst steht derselbe Text je
nach Weg zwei Punkte weiter rechts oder ein Zeichen kuerzer da, und
gefunden wird das erst auf dem Fernseher des Nutzers.

Deshalb ist der Kern dieses Tests ein stumpfer Vergleich: dieselbe
Zeile zweimal zeichnen, einmal ueber C und einmal ueber Python, und die
Puffer Byte fuer Byte gegeneinanderhalten. Ueber den ganzen ASCII- und
Latin-1-Bereich, ueber alle Schriftgroessen, ueber die Grenzfaelle am
rechten und unteren Rand.

DIE DREI STELLEN, AN DENEN SO ETWAS KIPPT, und jede hat ihren Abschnitt:

  1. DAS ABSCHNEIDEN. fb.text() kuerzt auf (Breite - x) // cw Zeichen.
     Rechnet C anders, steht am rechten Rand ein Zeichen zu viel oder zu
     wenig - und beim Vergleich faellt es sofort auf.
  2. DIE GRENZEN. In Python schuetzt der Puffer sich selbst; in C gibt
     es nur den Zeiger. Ein Auftrag, der nicht hineinpasst, darf nichts
     schreiben - geprueft mit einem Wachposten hinter dem Nutzbereich.
  3. DAS GEMERKTE "SCHON EINMAL DA". Der erste Auftritt geht nach C,
     der zweite baut den Streifen. Greift das nicht, kostet jeder
     wiederkehrende Menuepunkt dauerhaft einen C-Aufruf - auf dem
     Geraet eine Millisekunde fuer nichts.

Ausfuehren:
    python3 tools/test_text_in_c.py
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H          # noqa: E402

import fe.art as A            # noqa: E402
import fe.framebuffer as FM   # noqa: E402

fails = []
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def check(name, ok, info=""):
    if ok:
        print("  OK   %s %s" % (name, info))
    else:
        print("  FEHL %s %s" % (name, info))
        fails.append(name)


# ---------------------------------------------------------------------------
print("Test 1: die Funktion ist da")
# ---------------------------------------------------------------------------
check("libdragend geladen", A._LIB is not None,
      "ohne sie prueft dieser Test nichts")
check("texte_zeichnen ist angebunden", getattr(A, "_HAT_TEXT", False))
check("in einem EIGENEN try", "global _HAT_TEXT" in open(
    os.path.join(_REPO, "frontend", "fe", "art.py"),
    encoding="utf-8").read(),
    "eine 7er-Fassung darf die Bibliothek nicht mitnehmen")
check("die Fassung wurde hochgezaehlt", A.DRAGEND_LIB_VERSION == 8,
      str(A.DRAGEND_LIB_VERSION))
if A._LIB is None or not getattr(A, "_HAT_TEXT", False):
    print()
    print("Ohne libdragend ist hier Schluss - das ist auf einem Rechner")
    print("ohne passendes .so kein Fehler.")
    sys.exit(1 if fails else 0)


def neu(breite=1920, hoehe=1080):
    H.set_screen(breite, hoehe)
    fb = FM.Framebuffer()
    fb.text_zeichner = staticmethod(A.texte_zeichnen).__func__
    return fb


def py_text(fb, x, y, s, scale, fg, bg):
    """Der Python-Weg, unveraendert - das Vergleichsmass.

    Nachgebaut statt aufgerufen, weil fb.text() seit Build 227 selbst
    entscheidet, welchen Weg es nimmt. Die Zeilen stammen eins zu eins
    aus fe/framebuffer.py."""
    cw = 8 * scale
    if y + 8 * scale > fb.height or y < 0 or x < 0:
        return
    maxch = (fb.width - x) // cw
    if maxch <= 0:
        return
    if len(s) > maxch:
        s = s[:maxch]
    if not s:
        return
    strip = fb._text_strip(s, scale, fg, bg, False)
    w4 = len(strip[0])
    ziel = memoryview(fb.buf)
    for i, row in enumerate(strip):
        off = (y + i) * fb.stride + x * 4
        ziel[off:off + w4] = row


def vergleich(fb, auftraege):
    """Einmal ueber C, einmal ueber Python - und die Zahl der
    abweichenden Bytes zurueck."""
    fb.buf[:] = bytearray(len(fb.buf))
    ok = fb.text_viele(auftraege)
    mit_c = bytes(fb.buf)
    fb.buf[:] = bytearray(len(fb.buf))
    for (x, y, s, scale, fg, bg) in auftraege:
        py_text(fb, x, y, s, scale, fg, bg)
    ohne = bytes(fb.buf)
    if not ok:
        return None, 0
    return True, sum(1 for a, b in zip(mit_c, ohne) if a != b)


FG = (220, 224, 232)
BG = (16, 18, 24)

# ---------------------------------------------------------------------------
print()
print("Test 2: JEDES Zeichen, JEDE Groesse - bitgenau")
# ---------------------------------------------------------------------------
fb = neu()
# Der ganze Bereich, den die Schrifttabellen abdecken, plus der
# "?"-Rueckfall darueber. In Haeppchen zu 24 Zeichen, damit eine Zeile
# auch bei Groesse 6 noch auf den Schirm passt.
alle = "".join(chr(c) for c in list(range(32, 128)) + list(range(0xA0, 0x100)))
alle += "€✓中"          # ausserhalb -> "?"
schief = 0
faelle = 0
for scale in (1, 2, 3, 4, 6):
    breite_max = 1920 // (8 * scale)
    schritt = min(24, breite_max)
    for i in range(0, len(alle), schritt):
        s = alle[i:i + schritt]
        faelle += 1
        ok, n = vergleich(fb, ((7, 13, s, scale, FG, BG),))
        if ok is None:
            schief += 1
            print("       C hat abgelehnt: Groesse %d, %r" % (scale, s[:12]))
        elif n:
            schief += 1
            print("       Groesse %d, %r: %d Bytes anders"
                  % (scale, s[:12], n))
check("%d Haeppchen ueber ASCII und Latin-1" % faelle, schief == 0,
      "%d weichen ab" % schief)

# Und mit anderen Farben - fg und bg gehen als 32-Bit-Wert nach C, und
# ein vertauschtes Byte faellt nur hier auf.
schief = 0
for fg, bg in (((255, 0, 0), (0, 0, 255)), ((0, 255, 0), (255, 255, 255)),
               ((1, 2, 3), (253, 254, 255)), ((0, 0, 0), (0, 0, 0))):
    ok, n = vergleich(fb, ((40, 40, "Farbe Pruefen 123", 3, fg, bg),))
    if ok is None or n:
        schief += 1
        print("       %r auf %r: %s" % (fg, bg, "abgelehnt" if ok is None
                                        else "%d Bytes" % n))
check("vier Farbkombinationen bitgenau", schief == 0)

# ---------------------------------------------------------------------------
print()
print("Test 3: DAS ABSCHNEIDEN am rechten und unteren Rand")
# ---------------------------------------------------------------------------
LANG = "Das ist ein ueberlanger Titel, der nicht mehr hineinpasst - " * 4
schief = []
for (w, h) in ((1920, 1080), (320, 240), (640, 480)):
    fb = neu(w, h)
    for scale in (1, 2, 3):
        for x in (0, 1, 7, w // 2, w - 8 * scale, w - 8 * scale - 1,
                  w - 1, w):
            ok, n = vergleich(fb, ((x, 20, LANG, scale, FG, BG),))
            if ok is None or n:
                schief.append("%dx%d Groesse %d bei x=%d (%s)"
                              % (w, h, scale, x,
                                 "abgelehnt" if ok is None
                                 else "%d Bytes" % n))
check("ueberlanger Text an jedem x bitgenau", not schief,
      "; ".join(schief[:3]))

fb = neu(640, 480)
schief = []
for y in (0, 1, 479 - 24, 480 - 24, 480 - 23, 479, 480, 1000):
    ok, n = vergleich(fb, ((10, y, "Unten", 3, FG, BG),))
    if ok is None or n:
        schief.append("y=%d (%s)" % (y, "abgelehnt" if ok is None
                                     else "%d Bytes" % n))
check("und an jedem y - auch jenseits des unteren Randes", not schief,
      "; ".join(schief[:3]))

# Negative Werte und leere Texte: Python zeichnet nichts, C darf auch
# nichts zeichnen.
fb = neu(640, 480)
schief = []
for auftrag in ((-1, 10, "Links raus", 2, FG, BG),
                (10, -1, "Oben raus", 2, FG, BG),
                (10, 10, "", 2, FG, BG),
                (-5, -5, "Beides", 2, FG, BG)):
    ok, n = vergleich(fb, (auftrag,))
    if ok is None or n:
        schief.append("%r" % (auftrag[:3],))
check("Randfaelle aendern nichts", not schief, "; ".join(schief[:3]))

# ---------------------------------------------------------------------------
print()
print("Test 4: DER BUND - mehrere Zeilen in einem Aufruf")
# ---------------------------------------------------------------------------
fb = neu()
rng = random.Random(227)
WORTE = ["Super Mario World", "The Legend of Zelda", "Gruesse aus Strassburg",
         "Jahr: 1992", "Hersteller: Nintendo", "Spieler: 1-2", "Genre: Jump",
         "Koenig der Loewen", "Bewertung: 9/10", "x", ""]
schief = 0
for _ in range(40):
    n_jobs = rng.randrange(1, 9)
    jobs = []
    yy = 20
    for _j in range(n_jobs):
        jobs.append((rng.randrange(0, 1200), yy,
                     rng.choice(WORTE), rng.choice((1, 2, 3)), FG, BG))
        yy += 40
    ok, n = vergleich(fb, jobs)
    if ok is None or n:
        schief += 1
        print("       %d Auftraege: %s" % (n_jobs, "abgelehnt" if ok is None
                                           else "%d Bytes" % n))
check("40 zufaellige Buende bitgenau", schief == 0)

# Verschiedene Groessen UND Farben im selben Bund - in C haengt daran
# der Vorrat an fertigen Glyphenzeilen, und wenn der beim Wechsel nicht
# verworfen wird, steht die zweite Zeile in der Farbe der ersten.
ok, n = vergleich(fb, ((10, 10, "Erste Zeile", 3, (255, 0, 0), (0, 0, 0)),
                       (10, 60, "Zweite Zeile", 2, (0, 255, 0), (9, 9, 9)),
                       (10, 100, "Dritte Zeile", 3, (255, 0, 0), (0, 0, 0)),
                       (10, 140, "Vierte Zeile", 6, (0, 0, 255), (1, 1, 1))))
check("Groessen und Farben wechseln im selben Bund", ok and n == 0,
      "abgelehnt" if ok is None else "%d Bytes anders" % n)

# ---------------------------------------------------------------------------
print()
print("Test 5: DIE GRENZEN - C schreibt nie hinter den Puffer")
# ---------------------------------------------------------------------------
# Angeboten werden Auftraege, die NICHT hineinpassen. Erwartet wird:
# nichts geschrieben, kein Absturz, und der Wachposten hinter dem
# Nutzbereich steht unveraendert da.
WACHE = b"\xA5" * 8192
fb = neu(320, 240)
schief = []
for name, (x, y, s, scale) in (
        ("weit rechts", (100000, 0, "Weg", 2)),
        ("weit unten", (0, 100000, "Weg", 2)),
        ("negative Groesse", (0, 0, "Weg", -2)),
        ("Groesse null", (0, 0, "Weg", 0)),
        ("Groesse 99", (0, 0, "Weg", 99)),
        ("sehr langer Text", (0, 0, "A" * 100000, 1)),
):
    puffer = bytearray(fb.stride * fb.height) + bytearray(WACHE)
    merk = fb.buf
    fb.buf = puffer
    try:
        fb.text_viele(((x, y, s, scale, FG, BG),))
        gestuerzt = False
    except Exception as e:                               # noqa: BLE001
        gestuerzt = "%s: %s" % (type(e).__name__, e)
    fb.buf = merk
    if gestuerzt:
        schief.append("%s: %s" % (name, gestuerzt))
    elif bytes(puffer[fb.stride * fb.height:]) != WACHE:
        schief.append("%s: Wache ueberschrieben" % name)
check("sechs unsinnige Auftraege, Wache steht", not schief,
      "; ".join(schief[:3]))

# Eine unsinnige Groesse im Bund darf auch die GUTEN Auftraege nicht
# halb zeichnen - entweder alles oder nichts, sonst wuesste der
# Aufrufer nicht, was er noch nachholen muss.
fb = neu(640, 480)
fb.buf[:] = bytearray(len(fb.buf))
erg = fb.text_viele(((10, 10, "Gut", 2, FG, BG),
                     (10, 50, "Schlecht", 99, FG, BG)))
check("ein schlechter Auftrag verwirft den ganzen Bund",
      erg is False and bytes(fb.buf) == bytes(len(fb.buf)),
      "sonst steht die Haelfte da und Python zeichnet sie noch einmal")

# ---------------------------------------------------------------------------
print()
print("Test 6: wann C und wann Python")
# ---------------------------------------------------------------------------
fb = neu()
check("die Schwelle steht in Punkten", fb.TEXT_C_MIN_PUNKTE == 6000,
      str(fb.TEXT_C_MIN_PUNKTE))
check("40 Zeichen in Groesse 3 gehen nach C", fb._text_nach_c(40, 3),
      "960 x 24 = 23040 Punkte")
check("10 Zeichen in Groesse 3 bleiben in Python",
      not fb._text_nach_c(10, 3), "5760 Punkte")
check("30 Zeichen in Groesse 1 bleiben in Python",
      not fb._text_nach_c(30, 1), "die ganze Roehre rechnet in Python")
fb.text_zeichner = None
check("ohne Zeichner geht gar nichts nach C", not fb._text_nach_c(400, 6))

# ---------------------------------------------------------------------------
print()
print("Test 7: der zweite Auftritt bekommt seinen Streifen")
# ---------------------------------------------------------------------------
fb = neu()
TITEL = "Ein Titel, lang genug fuer den Weg nach C"
fb.text(10, 10, TITEL, 3, FG, BG)
check("beim ersten Mal entsteht KEIN Cache-Eintrag",
      (TITEL, 3, FG, BG) not in fb._textcache,
      "beim Scrollen kommt jeder Titel genau einmal vor")
check("aber er ist gemerkt", (TITEL, 3, FG, BG) in fb._text_einmal)
fb.text(10, 10, TITEL, 3, FG, BG)
check("beim zweiten Mal schon", (TITEL, 3, FG, BG) in fb._textcache,
      "Menuepunkte und Kopfzeilen kommen bei jedem Bild wieder")

# Und das Bild ist in allen drei Faellen dasselbe.
fb2 = neu()
fb.buf[:] = bytearray(len(fb.buf))
fb.text(10, 10, TITEL, 3, FG, BG)          # dritter Aufruf: aus dem Cache
fb2.buf[:] = bytearray(len(fb2.buf))
py_text(fb2, 10, 10, TITEL, 3, FG, BG)
check("und das Bild bleibt dasselbe", bytes(fb.buf) == bytes(fb2.buf))

# cachen=False darf NIE in den Cache - sonst verdraengt die
# Beschreibung genau die Eintraege, fuer die er da ist.
fb = neu()
fb.text(10, 10, "Eine Beschreibungszeile von ausreichender Laenge", 3,
        FG, BG, cachen=False)
fb.text(10, 10, "Eine Beschreibungszeile von ausreichender Laenge", 3,
        FG, BG, cachen=False)
check("cachen=False bleibt draussen", not fb._textcache and not fb._text_einmal,
      "%d Eintraege" % (len(fb._textcache) + len(fb._text_einmal)))

# Und der Vorrat wird mit der Schrift geleert - sonst stuenden die
# haeufigen Texte weiter in der alten Schrift da.
fb = neu()
fb.text(10, 10, TITEL, 3, FG, BG)
hatte = bool(fb._text_einmal)
fb.schrift_setzen(bytes(1024))
check("die Schrift zu wechseln leert beide Vorraete",
      hatte and not fb._text_einmal and not FM._GLYPHBYTES,
      "sonst bleibt der haeufige Text in der alten Schrift stehen")
fb.schrift_setzen(None)

# ---------------------------------------------------------------------------
print()
print("Test 8: die Aufrufer buendeln")
# ---------------------------------------------------------------------------
quelle = open(H.FRONTEND_PY, encoding="utf-8", errors="replace").read()
check("die Datenzeilen unter dem Cover kommen als Bund",
      "fb.text_viele(auftraege)" in quelle)
check("die Beschreibung ebenfalls",
      "self.fb.text_viele(auftraege)" in quelle)
check("und beide nur ueber die Schwelle",
      quelle.count("_text_nach_c(zeichen,") == 2,
      "ein kleiner Bund ist in Python billiger")
check("der Zeichner haengt am selben Schalter wie der Fueller",
      "Framebuffer.text_zeichner = staticmethod(_c_texte_zeichnen)" in quelle)

print()
if fails:
    print("FEHLGESCHLAGEN (%d):" % len(fails))
    for f in fails:
        print("  - %s" % f)
    sys.exit(1)
print("Alles in Ordnung.")
