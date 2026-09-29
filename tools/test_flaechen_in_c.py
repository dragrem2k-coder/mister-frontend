#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Flaechen fuellen in C (Build 219).

WORAUF DAS ZURUECKGEHT: Abschnitt J des Benchs weist fb.rect(),
rect_rounded(), rect_rounded_schatten() und karte_mit_schatten()
gemeinsam als "karten" aus, und auf dem DE10-Nano war das der groesste
benannte Posten eines Scrollschritts - 47,0 ms in der Spieleliste (37 %
des Schritts), 35,2 in der Galerie, 28,7 auf der Hauptseite. Rund 4,7 ms
je Aufruf, und alles Python-Schleifen ueber Bildzeilen.

DIE EINE STELLE, DIE FAST ALLES DAVON ERWISCHT, ist fb.rect(): die
abgerundeten Fassungen zeichnen nur ihre Eckenzeilen selbst (zweimal
radius Stueck) und lassen den ganzen Mittelteil von dort fuellen. Bei der
Boxart-Karte sind das 876 von 900 Zeilen.

DIE SCHWELLE IST DER INTERESSANTE TEIL. Gemessen auf dem
Entwicklungsrechner:

    700x900   Python 0,523 ms   C 0,266 ms   ->  2,0x schneller
    400x300   Python 0,108 ms   C 0,140 ms   ->  0,8x LANGSAMER
     60x40    Python 0,020 ms   C 0,077 ms   ->  0,3x viel langsamer

Der Sprung nach C kostet also etwas, und unter etwa hundert Zeilen ist
das mehr als die gesparten Zuweisungen. Deshalb greift C erst ab
FLAECHEN_C_MIN_ZEILEN - und deshalb prueft dieser Test die Schwelle
genauso wie das Ergebnis.

WAS HIER GEPRUEFT WIRD

  1. C und Python schreiben BITGENAU dasselbe - viele Formen, Farben
     und Radien, auch die schiefen.
  2. Die Schwelle wirkt in beide Richtungen.
  3. Eine Bibliothek ohne die neue Funktion (Version 4) wird weiter
     VOLL genutzt - das war vorher nicht so und ist der eigentliche
     Fallstrick eines Teil-Updates.
  4. Der Schalter schaltet ab.

Ausfuehren:
    python3 tools/test_flaechen_in_c.py
"""
import os
import random
import sys

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
sys.path.insert(0, _HIER)

if not os.environ.get("DRAGEND_LIB"):
    for _k in (os.path.join(_REPO, "frontend", "c", "libdragend_x86.so"),
               os.path.join(_REPO, "frontend", "libdragend_x86.so")):
        if os.path.exists(_k):
            os.environ["DRAGEND_LIB"] = _k
            break

import _harness as H                                     # noqa: E402

fm = H.fm
sys.path.insert(0, os.path.join(_REPO, "frontend"))
import fe.art as A                                       # noqa: E402
import fe.settings as S                                  # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


H.set_screen(1920, 1080)
fe = H.make_frontend(page=1)
fb = fe.fb
FUELLER = fm.Framebuffer.flaechen_fueller

# ---------------------------------------------------------------------------
print("Test 1: die Bibliothek ist da und kann es")
# ---------------------------------------------------------------------------
check("libdragend geladen", A._LIB is not None,
      "ohne sie prueft dieser Test nichts")
if A._LIB is not None:
    check("und meldet Version %d" % A.DRAGEND_LIB_VERSION,
          A._LIB.dragend_version() == A.DRAGEND_LIB_VERSION,
          "gefunden: %d - c/bauen.sh neu laufen lassen"
          % A._LIB.dragend_version())
check("rechtecke_farben ist angebunden", A._HAT_FARBEN)
check("und im Framebuffer eingehaengt", FUELLER is not None,
      "frontend.py setzt den Haken beim Laden")

# ---------------------------------------------------------------------------
print()
print("Test 2: C und Python schreiben BITGENAU dasselbe")
# ---------------------------------------------------------------------------
# Die Schwelle wird dafuer auf 1 gestellt - sonst prueft der Vergleich
# bei kleinen Formen zweimal den Python-Weg.
_alt_mz = fm.Framebuffer.FLAECHEN_C_MIN_PUNKTE
rng = random.Random(219)
FORMEN = [(0, 0, 1920, 1080), (0, 0, 1, 1), (1919, 1079, 1, 1),
          (0, 0, 1920, 1), (0, 0, 1, 1080), (1900, 1000, 100, 200),
          (-5, -5, 60, 60), (100, 100, 700, 900), (500, 500, 0, 10),
          (500, 500, 10, 0)]
for _ in range(25):
    FORMEN.append((rng.randrange(-10, 1930), rng.randrange(-10, 1090),
                   rng.randrange(0, 400), rng.randrange(0, 400)))
FARBEN = [(0, 0, 0), (255, 255, 255), (1, 2, 3), (255, 0, 0), (0, 255, 0),
          (0, 0, 255), (17, 34, 51)]
try:
    fm.Framebuffer.FLAECHEN_C_MIN_PUNKTE = 1
    abw = 0
    for (x, y, w, h) in FORMEN:
        rgb = FARBEN[(x + y + w + h) % len(FARBEN)]
        fb.buf[:] = bytearray(len(fb.buf))
        fb.rect(x, y, w, h, rgb)
        mit = bytes(fb.buf)
        fb.flaechen_fueller = None
        fb.buf[:] = bytearray(len(fb.buf))
        fb.rect(x, y, w, h, rgb)
        ohne = bytes(fb.buf)
        del fb.flaechen_fueller
        if mit != ohne:
            abw += 1
            d = sum(1 for a, b in zip(mit, ohne) if a != b)
            print("       %s %s: %d Bytes" % ((x, y, w, h), rgb, d))
    check("alle %d Formen gleich" % len(FORMEN), abw == 0,
          "%d weichen ab" % abw)

    # Die abgerundeten Fassungen und die Karte mit Schatten gehen
    # ebenfalls durch rect() bzw. durch den eigenen Band-Aufruf.
    abw = 0
    for (w, h, versatz, radius) in ((700, 900, 12, 24), (300, 400, 6, 8),
                                    (64, 64, 3, 4), (900, 300, 9, 0),
                                    (500, 500, 30, 60)):
        for name in ("rect_rounded", "rect_rounded_schatten",
                     "karte_mit_schatten"):
            def _zeichnen(_n=name, _w=w, _h=h, _v=versatz, _r=radius):
                if _n == "rect_rounded":
                    fb.rect_rounded(100, 80, _w, _h, (40, 60, 80), _r)
                elif _n == "rect_rounded_schatten":
                    fb.rect_rounded_schatten(100, 80, _w, _h, _v,
                                             (10, 10, 10), _r)
                else:
                    fb.karte_mit_schatten(100, 80, _w, _h, _v,
                                          (40, 60, 80), (10, 10, 10), _r)

            fb.buf[:] = bytearray(len(fb.buf))
            _zeichnen()
            mit = bytes(fb.buf)
            fb.flaechen_fueller = None
            fb.buf[:] = bytearray(len(fb.buf))
            _zeichnen()
            ohne = bytes(fb.buf)
            del fb.flaechen_fueller
            if mit != ohne:
                abw += 1
                d = sum(1 for a, b in zip(mit, ohne) if a != b)
                print("       %s %dx%d v=%d r=%d: %d Bytes"
                      % (name, w, h, versatz, radius, d))
    check("auch die abgerundeten Fassungen und die Karte", abw == 0,
          "%d Faelle weichen ab" % abw)

    # UND DER GEBUENDELTE RAHMEN (Build 220): ein rect_viele()-Aufruf
    # muss Byte fuer Byte dasselbe hinterlassen wie die einzelnen
    # rect()-Aufrufe, die dort vorher standen - auch dann, wenn die
    # Balken sich an den Ecken UEBERLAPPEN und wenn sie ueber den
    # Bildrand hinausragen.
    RAHMEN = [
        # Kachelrahmen der Rasteransicht (ueberlappende Ecken)
        ((10, 10, 288, 9), (10, 362, 288, 9), (10, 10, 9, 361),
         (289, 10, 9, 361)),
        # Platzhalterrahmen der Boxart-Spalte, sehr schmal und hoch
        ((100, 50, 697, 3), (100, 818, 697, 3), (100, 50, 3, 771),
         (794, 50, 3, 771)),
        # halb ausserhalb des Bildes, und ein leeres Rechteck dabei
        ((-20, -20, 200, 40), (1850, 1040, 200, 200), (0, 0, 0, 50),
         (500, 500, 50, 0)),
        # nur ein einziger Balken
        ((30, 30, 4, 900),),
    ]
    abw = 0
    for i, rahmen in enumerate(RAHMEN):
        rgb = FARBEN[i % len(FARBEN)]
        fb.buf[:] = bytearray(len(fb.buf))
        fb.rect_viele(rahmen, rgb)
        mit = bytes(fb.buf)
        fb.buf[:] = bytearray(len(fb.buf))
        for (x, y, w, h) in rahmen:
            fb.rect(x, y, w, h, rgb)
        einzeln = bytes(fb.buf)
        fb.flaechen_fueller = None
        fb.buf[:] = bytearray(len(fb.buf))
        fb.rect_viele(rahmen, rgb)
        ohne = bytes(fb.buf)
        del fb.flaechen_fueller
        if not (mit == einzeln == ohne):
            abw += 1
            print("       Rahmen %d: C=%s wie einzeln=%s wie Python=%s"
                  % (i, len(mit), len(einzeln), len(ohne)))
    check("rect_viele schreibt dasselbe wie einzelne rect()-Aufrufe, "
          "in C UND in Python", abw == 0, "%d Rahmen weichen ab" % abw)
finally:
    fm.Framebuffer.FLAECHEN_C_MIN_PUNKTE = _alt_mz

# ---------------------------------------------------------------------------
print()
print("Test 3: die Schwelle wirkt in BEIDE Richtungen")
# ---------------------------------------------------------------------------
# Ohne sie waere jede kleine Flaeche langsamer als vorher: 60x40 kostet
# in C 0,015 ms gegen 0,013 in Python - der Sprung selbst schlaegt dort
# schon durch. Eine Optimierung, die den haeufigen Fall verschlechtert,
# ist keine.
#
# UND DIE SCHWELLE ZAEHLT PUNKTE, NICHT ZEILEN, und das ist der Fund aus
# Build 220: 700x32 hat nur 32 Zeilen und lohnt trotzdem (1,3x), 60x40
# hat mehr Zeilen und lohnt nicht (0,8x). Die Zeilenzahl war das falsche
# Mass.
mz = fm.Framebuffer.FLAECHEN_C_MIN_PUNKTE
mzz = fm.Framebuffer.FLAECHEN_C_MIN_ZEILEN
check("die Flaechenschwelle ist gesetzt und plausibel",
      1024 <= mz <= 262144, "%r" % mz)
check("die Zeilenschwelle ist gesetzt und plausibel",
      32 <= mzz <= 512, "%r" % mzz)
gezaehlt = [0]
_echt = fb.flaechen_fueller


def _haken(*a, **k):
    gezaehlt[0] += 1
    return _echt(*a, **k)


fb.flaechen_fueller = _haken
try:
    # ERSTE SCHWELLE: die FLAECHE. Breit und flach zaehlt hier, und
    # genau diesen Fall haette eine Schwelle in Zeilen verpasst
    # (700x32 lohnt 1,3x).
    breit = max(1, -(-mz // (mzz - 1)))   # aufrunden, nicht ab
    gezaehlt[0] = 0
    fb.rect(0, 0, breit, mzz - 1, (1, 2, 3))
    check("breit und flach, genau auf der Flaechenschwelle: nach C",
          gezaehlt[0] == 1,
          "%d Aufrufe bei %dx%d = %d Punkten"
          % (gezaehlt[0], breit, mzz - 1, breit * (mzz - 1)))
    gezaehlt[0] = 0
    fb.rect(0, 0, breit // 4, mzz - 1, (1, 2, 3))
    check("dieselbe Hoehe, ein Viertel der Flaeche: bleibt in Python",
          gezaehlt[0] == 0,
          "%d Aufrufe bei %dx%d" % (gezaehlt[0], breit // 4, mzz - 1))
    # ZWEITE SCHWELLE: die ZEILEN. Ein 3x771-Balken hat nur 2314 Punkte
    # und kostet Python trotzdem 771 Zuweisungen - das ist der Fund aus
    # Build 220, und eine Schwelle allein in Punkten hat ihn verpasst.
    gezaehlt[0] = 0
    fb.rect(0, 0, 3, mzz, (1, 2, 3))
    check("schmal und hoch, genau auf der Zeilenschwelle: nach C",
          gezaehlt[0] == 1,
          "%d Aufrufe bei 3x%d = %d Punkten - weit unter der "
          "Flaechenschwelle" % (gezaehlt[0], mzz, 3 * mzz))
    gezaehlt[0] = 0
    fb.rect(0, 0, 3, mzz - 1, (1, 2, 3))
    check("eine Zeile darunter bleibt es in Python", gezaehlt[0] == 0,
          "%d Aufrufe" % gezaehlt[0])
    gezaehlt[0] = 0
    fb.rect(0, 0, 697, 3, (1, 2, 3))
    check("wenige Zeilen UND kleine Flaeche (697x3) bleibt in Python",
          gezaehlt[0] == 0,
          "%d Aufrufe - in C gemessen 0,3x, also dreimal langsamer"
          % gezaehlt[0])
    # DIE ZWEI FORMEN, DIE DEM GERAET NICHT GEFALLEN HABEN (Build 221).
    # Beide standen mit einer Schwelle aus PC-Messungen auf der
    # C-Seite. 60x40 stand im Bericht vom 29.09. mit "0,6x - genutzt:
    # ja", also schwarz auf weiss als Verschlechterung; 853x21 ist die
    # Zeilenmarkierung der Liste, zweimal je Scrollschritt, und kam
    # wegen ihrer 17919 Punkte durch.
    for (pw, ph, warum) in ((60, 40, "im Bericht vom 29.09. mit 0,6x"),
                            (853, 21, "die Zeilenmarkierung der Liste")):
        gezaehlt[0] = 0
        fb.rect(0, 0, pw, ph, (1, 2, 3))
        check("%dx%d bleibt in Python" % (pw, ph), gezaehlt[0] == 0,
              "%d Aufrufe - %s" % (gezaehlt[0], warum))
    gezaehlt[0] = 0
    fb.rect(0, 0, 100, 1000, (1, 2, 3), scanlines=True)
    check("mit Scanlines bleibt es in Python", gezaehlt[0] == 0,
          "dort wechselt die Farbe je Zeile")
    # Und die gebuendelten Eckenzeilen (Build 220): EIN Aufruf fuer die
    # ganze Rundung, nicht einer je Zeile.
    gezaehlt[0] = 0
    fb.rect_rounded(10, 10, 769, 945, (40, 60, 80), 96)
    check("die Rundung geht als EIN Bund nach C, plus der Mittelteil",
          gezaehlt[0] == 2,
          "%d Aufrufe - erwartet: Ecken gebuendelt und die Mitte"
          % gezaehlt[0])
    # UND DER RAHMEN (Build 220): vier Balken, von denen einzeln KEINER
    # die Schwelle erreicht - zusammen schon. Das ist der ganze Sinn von
    # rect_viele(), und der Kachelrahmen der Rasteransicht sieht genau so
    # aus.
    gezaehlt[0] = 0
    fb.rect_viele(((10, 10, 288, 9), (10, 362, 288, 9),
                   (10, 10, 9, 361), (289, 10, 9, 361)), (1, 2, 3))
    check("ein Rahmen aus vier Balken geht als EIN Aufruf nach C",
          gezaehlt[0] == 1,
          "%d Aufrufe - einzeln erreicht keiner der vier die Schwelle"
          % gezaehlt[0])
    gezaehlt[0] = 0
    fb.rect_viele(((10, 10, 40, 4), (10, 20, 40, 4)), (1, 2, 3))
    check("zwei winzige Balken bleiben zusammen in Python",
          gezaehlt[0] == 0, "%d Aufrufe" % gezaehlt[0])
finally:
    del fb.flaechen_fueller

# ---------------------------------------------------------------------------
print()
print("Test 4: eine ALTE Bibliothek bleibt voll nutzbar")
# ---------------------------------------------------------------------------
# DAS IST DER EIGENTLICHE FALLSTRICK dieses Builds. Bis Build 218 wurde
# jede Fassung verworfen, deren Nummer nicht genau passte - eine alte
# libdragend.so neben einer neuen frontend.py hiess also KEIN C mehr,
# auch nicht fuer das Verkleinern. Das ist auf dem Geraet der Faktor 124
# (Abschnitt C des Benchs). Deshalb gilt jetzt eine Spanne.
check("es gibt eine Untergrenze", hasattr(A, "DRAGEND_LIB_VERSION_MIN"))
check("und sie liegt unter der aktuellen Fassung",
      A.DRAGEND_LIB_VERSION_MIN < A.DRAGEND_LIB_VERSION,
      "%s / %s" % (A.DRAGEND_LIB_VERSION_MIN, A.DRAGEND_LIB_VERSION))
_q = open(os.path.join(_REPO, "frontend", "fe", "art.py")).read()
check("die Fassungspruefung ist eine Spanne, kein Vergleich",
      "DRAGEND_LIB_VERSION_MIN <= _v <= DRAGEND_LIB_VERSION" in _q)
check("rechtecke_farben wird in einem EIGENEN try angebunden",
      _q.count("_HAT_FARBEN = True") == 1
      and "except AttributeError:" in _q,
      "sonst nimmt eine fehlende Funktion die ganze Bibliothek mit")
check("und der Wrapper sagt nein, wenn sie fehlt",
      "if _LIB is None or not _HAT_FARBEN" in _q)
# Und die Probe aufs Exempel: ohne die Funktion muss alles andere laufen.
_alt_hat = A._HAT_FARBEN
try:
    A._HAT_FARBEN = False
    check("ohne rechtecke_farben liefert der Wrapper False",
          A.rechtecke_farben(bytearray(64), 16, 4, 64,
                             ((0, 0, 2, 2, 0),)) is False)
    check("aber rechtecke_kopieren laeuft weiter",
          A.rechtecke_kopieren(bytearray(64), bytearray(64), 16, 4, 64,
                               ((0, 0, 2, 2),)) is True,
          "das ist der ganze Sinn der Spanne")
finally:
    A._HAT_FARBEN = _alt_hat

# ---------------------------------------------------------------------------
print()
print("Test 5: der Schalter")
# ---------------------------------------------------------------------------
check("es gibt eine Schalterdatei", hasattr(S, "FLAECHEN_C_AUS_FLAG"))
check("und eine Abfrage", hasattr(S, "flaechen_c_enabled"))
check("Standard ist AN", S.flaechen_c_enabled() is True)
import tempfile                                          # noqa: E402

_f = os.path.join(tempfile.mkdtemp(prefix="flaechen_"), "aus")
_altf = S.FLAECHEN_C_AUS_FLAG
try:
    S.FLAECHEN_C_AUS_FLAG = _f
    open(_f, "w").close()
    check("mit der Datei aus", S.flaechen_c_enabled() is False)
finally:
    S.FLAECHEN_C_AUS_FLAG = _altf
_qf = open(os.path.join(_REPO, "frontend", "frontend.py")).read()
check("gefragt wird EINMAL beim Laden, nicht je Aufruf",
      "if flaechen_c_enabled():" in _qf
      and _qf.count("flaechen_c_enabled()") == 1,
      "fb.rect() laeuft einige hundert Mal je Seitenaufbau")

# ---------------------------------------------------------------------------
print()
print("Test 6: die Bauanleitung baut alle drei Fassungen")
# ---------------------------------------------------------------------------
# Die x86-Fassung wird von den Tests benutzt (DRAGEND_LIB). Blieb sie
# beim Bauen aussen vor, verglich "C gegen Python" irgendwann eine alte
# Fassung mit neuem Python - und meldete Gruen fuer etwas, das auf dem
# Geraet anders aussieht.
_qb = open(os.path.join(_REPO, "frontend", "c", "bauen.sh")).read()
for datei in ("libdragend.so", "libdragend_neon.so", "libdragend_x86.so"):
    check("bauen.sh baut %s" % datei, "-o %s" % datei in _qb)
_qc = open(os.path.join(_REPO, "frontend", "c", "dragend.c")).read()
check("die C-Fassung ist hochgezaehlt",
      "return 5; }" in _qc or "return 5;" in _qc)
check("und rechtecke_farben steht drin", "int rechtecke_farben(" in _qc)

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  - " + x)
    sys.exit(1)
print("Alles in Ordnung.")
