#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Der Rechteck-Flip (Build 215).

NUTZER-RUECKMELDUNG: "das scrollen koennte echt ueberall ob nach links
rechts oben unten viel schneller sein."

WAS DAHINTER STECKTE, gemessen auf 1920x1080 je Scrollschritt:

    Kachelansicht links/rechts   3,74 MB   (zwei Baender)
    Kachelansicht hoch/runter    6,50 MB   (ein Band, 888 Zeilen)
    Galerie                      7,91 MB   (VOLLBILD, seit Build 125)

Geaendert haben sich dabei jeweils nur zwei Kacheln bzw. Cover, Text und
zwei Leistenkacheln - flip_rows() kennt aber nur Zeilen, und ein Band
geht immer ueber die volle Breite. Mit Rechtecken sind es 0,83 bzw.
1,02 MB, also der Faktor acht.

WORAUF ES BEI DIESEM TEST ANKOMMT

Ein Rechteck-Flip ist die riskanteste Art von Optimierung, die es in
diesem Frontend gibt: er kopiert WENIGER, und alles, was er zu wenig
kopiert, bleibt als Rest des vorigen Bildes stehen. Genau diese Sorte
Fehler gab es hier schon viermal (Build 80, 122, 125, 128), jedes Mal
weil ein Bereich zu knapp bemessen war.

Deshalb prueft dieser Test NICHT, ob die Rechtecke plausibel aussehen,
sondern vergleicht fb.mm - also das, was wirklich angezeigt wird -
gegen einen vollen Aufbau. Ein einziger vergessener Bildpunkt ist rot.

Die vier Fragen, in dieser Reihenfolge:

  1. Kommt auf dem SCHIRM dasselbe an wie bei einem vollen Aufbau? In
     allen Ansichten, quer und hochkant, mit und ohne Fussmeldung.
  2. Wird wirklich weniger kopiert - und zwar so viel weniger, wie
     oben behauptet?
  3. Liefert der Python-Rueckfall BITGENAU dasselbe wie der C-Weg?
  4. Meldet der Bildwaechter Fehlalarm? Das ist die subtilste Frage:
     seine Proben sind ganze ZEILEN, ein Rechteck schreibt eine Zeile
     nur zum Teil.

Ausfuehren:
    python3 tools/test_rechteck_flip.py
"""
import os
import shutil
import struct
import sys
import tempfile
import zlib

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
sys.path.insert(0, _HIER)

# Wie tools/test_c_modul.py: ohne die x86-Fassung liefe Frage 3 gegen
# sich selbst - zweimal der Python-Weg, und der Vergleich wuerde nichts
# beweisen.
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


TMP = tempfile.mkdtemp(prefix="rechteck_")
BASIS = os.path.join(TMP, "art")
os.makedirs(os.path.join(BASIS, "SNES"))
# Lange Titel mit dabei: die Namenszeile unter dem Raster und die
# Textspalte der Galerie werden dadurch je Schritt unterschiedlich
# lang - genau die Stelle, an der ein zu knapper Bereich einen Rest
# stehen laesst.
TITEL = (["Spiel %02d" % i for i in range(20)]
         + ["Ein ausgesprochen langer Spieltitel Nummer %02d mit Anhang" % i
            for i in range(20, 40)]
         + ["S%d" % i for i in range(40, 60)])


def cover(pfad, w, h, nr):
    punkt = bytes(((nr * 37) % 256, (nr * 91) % 256, (nr * 53) % 256, 255))
    with open(pfad, "wb") as f:
        f.write(b"ART1" + struct.pack("<HH", w, h)
                + zlib.compress(punkt * (w * h), 1))


for i, t in enumerate(TITEL):
    cover(os.path.join(BASIS, "SNES", t + ".art"), 400, 533, i)

fm.ART_BASE = A.ART_BASE = BASIS
fm.ART_HD = A.ART_HD = BASIS
A._art_index_cache.clear()
A.THUMB_CACHE_DIR = os.path.join(TMP, "tc")
os.makedirs(A.THUMB_CACHE_DIR)
fm.SYSART_BASE = A.SYSART_BASE = os.path.join(_REPO, "frontend", "sysart")


def spieleliste(breite, hoehe, ansicht):
    H.set_screen(breite, hoehe)
    f = H.make_frontend(page=1)
    fm.ART.auslagern = None
    f.lader.beenden()
    _n, node, _k = f.cats[f.cat_i]
    node["items"] = [(t, "game", ("/f/%d.sfc" % i, ".sfc", "SNES", None, None))
                     for i, t in enumerate(TITEL)]
    node.pop("_display_items_cache", None)
    f.ansicht_setzen(ansicht)
    # Warmlaufen: alle Miniaturen in den RAM, damit kein Schritt an
    # einem nachgeladenen Cover haengt und der Vergleich wirklich nur
    # den Kopierweg prueft.
    for i in range(min(30, len(TITEL))):
        f.item_i = i
        f.draw()
    return f


def hauptseite(breite, hoehe, ansicht):
    H.set_screen(breite, hoehe)
    f = H.make_frontend(page=0)
    fm.ART.auslagern = None
    f.lader.beenden()
    sp = [("S %d" % i, "game", ("/f/%d.sfc" % i, ".sfc", "SNES", None, None))
          for i in range(8)]
    KAT = [("Favoriten", "FAVORITES"), ("Arcade", "ARCADE"), ("NES", "NES"),
           ("SNES", "SNES"), ("Game Boy", "GAMEBOY"), ("GBC", "GBC"),
           ("GBA", "GBA"), ("N64", "N64"), ("Mega Drive", "Genesis"),
           ("SMS", "SMS"), ("PSX", "PSX"), ("Neo Geo", "NEOGEO")]
    f.cats = [(n, {"folders": {}, "items": list(sp)}, k) for n, k in KAT]
    f.ansicht_haupt_setzen(ansicht)
    for i in range(len(f.cats)):
        f.cat_i = i
        f.draw()
    return f


def vergleich(f, setzen, ziele, label, message=None):
    """Schneller Pfad gegen vollen Aufbau - am SCHIRM, nicht am Puffer.

    Dasselbe Verfahren wie in tools/test_baender_flip.py: der Puffer
    ist in beiden Faellen gleich, egal wie viel davon anschliessend auf
    den Schirm wandert. Nur fb.mm beweist etwas."""
    for ziel in ziele:
        setzen(f, 0)
        f._force_full_redraw = True
        f.draw(message=message)
        setzen(f, ziel)
        f.draw(message=message)                # schnell -> Rechtecke
        schnell = bytes(f.fb.mm)
        f._force_full_redraw = True
        f.draw(message=message)                # voll -> alles
        voll = bytes(f.fb.mm)
        d = sum(1 for a, b in zip(schnell, voll) if a != b)
        check("%s Schritt auf %-3d" % (label, ziel), d == 0,
              "" if d == 0 else "%d abweichende Bytes auf dem Schirm" % d)


def _setz_item(f_, i):
    f_.item_i = i


def _setz_cat(f_, i):
    f_.cat_i = i


# ---------------------------------------------------------------------------
print("Test 1: der Schalter ist AN, ohne dass jemand etwas anlegt")
# ---------------------------------------------------------------------------
# Anders als "schnelles Scrollen": dort geht es um einen Kompromiss
# (Bildriss gegen Zeit), hier um dasselbe Bild mit weniger Bytes.
H._zwischenspeicher_leeren()
check("rechteck_flip_enabled() ist ohne Datei an",
      S.rechteck_flip_enabled() is True)
_flag = os.path.join(TMP, "rechteck_flip_aus")
_alt_flag = S.RECHTECK_FLIP_AUS_FLAG
try:
    S.RECHTECK_FLIP_AUS_FLAG = _flag
    open(_flag, "w").close()
    H._zwischenspeicher_leeren()
    check("und mit der Datei aus", S.rechteck_flip_enabled() is False)
    os.unlink(_flag)
    H._zwischenspeicher_leeren()
    check("und danach wieder an", S.rechteck_flip_enabled() is True)
finally:
    S.RECHTECK_FLIP_AUS_FLAG = _alt_flag
    H._zwischenspeicher_leeren()

# ---------------------------------------------------------------------------
print()
print("Test 2: AM SCHIRM identisch - Kachelansicht der Spieleliste")
# ---------------------------------------------------------------------------
f = spieleliste(1920, 1080, "raster")
# Gemischt: Nachbar in derselben Reihe, Reihenwechsel, Seitenwechsel
# (dort greift der schnelle Pfad gar nicht - auch das muss stimmen),
# und Schritte mit kurzem auf langen Titel.
vergleich(f, _setz_item, (1, 2, 6, 7, 8, 14, 19, 20, 21, 25), "HDMI ")

print()
print("  -- mit einer Fussmeldung (sie aendert die Fusszeile mit)")
vergleich(f, _setz_item, (1, 6, 21), "HDMI ", message="Lade ...")

# ---------------------------------------------------------------------------
print()
print("Test 3: AM SCHIRM identisch - Galerie (war bisher Vollbild)")
# ---------------------------------------------------------------------------
g = spieleliste(1920, 1080, "galerie")
vergleich(g, _setz_item, (1, 2, 3, 19, 20, 21, 25), "Galerie")
print()
print("  -- mit einer Fussmeldung")
vergleich(g, _setz_item, (1, 21), "Galerie", message="Lade ...")

# ---------------------------------------------------------------------------
print()
print("Test 4: AM SCHIRM identisch - CRT und hochkant")
# ---------------------------------------------------------------------------
for b, h, ansicht, tag in ((320, 240, "raster", "CRT Raster "),
                           (320, 240, "galerie", "CRT Galerie"),
                           (1080, 1920, "raster", "TATE Raster"),
                           (1080, 1920, "galerie", "TATE Galer."),
                           (1280, 720, "raster", "720p Raster")):
    fx = spieleliste(b, h, ansicht)
    vergleich(fx, _setz_item, (1, 2, 5, 15), tag)

# ---------------------------------------------------------------------------
print()
print("Test 5: AM SCHIRM identisch - die Hauptseite")
# ---------------------------------------------------------------------------
for ansicht, tag in (("raster", "Haupt Raster "), ("galerie", "Haupt Galerie")):
    fh = hauptseite(1920, 1080, ansicht)
    vergleich(fh, _setz_cat, (1, 2, 3, 5, 8, 10), tag)

# ---------------------------------------------------------------------------
print()
print("Test 6: es wird WIRKLICH weniger kopiert")
# ---------------------------------------------------------------------------
# Ohne diese Pruefung koennten die Tests 2-5 gruen sein, waehrend
# heimlich weiterhin das Vollbild kopiert wird.
def kopierbilanz(f_, setzen, von, nach, message=None):
    """(Bytes, Aufrufe) fuer EINEN Schritt, ueber alle drei Wege."""
    setzen(f_, von)
    f_._force_full_redraw = True
    f_.draw(message=message)
    fb = f_.fb
    zahl = {"rect": 0, "rows": 0, "voll": 0}
    bytes_ = [0]
    e_rect = fb.flip_rechtecke
    e_rows = fb.flip_rows
    e_voll = fb.flip

    def h_rect(rechtecke, skip_vsync=False):
        rechtecke = list(rechtecke)
        zahl["rect"] += 1
        n = e_rect(rechtecke, skip_vsync=skip_vsync)
        bytes_[0] += n
        return n

    def h_rows(y, hh, skip_vsync=False):
        zahl["rows"] += 1
        bytes_[0] += max(0, min(fb.height, y + hh) - max(0, y)) * fb.stride
        return e_rows(y, hh, skip_vsync)

    def h_voll(skip_vsync=False):
        zahl["voll"] += 1
        bytes_[0] += fb.size
        return e_voll(skip_vsync)

    fb.flip_rechtecke = h_rect
    fb.flip_rows = h_rows
    fb.flip = h_voll
    try:
        setzen(f_, nach)
        f_.draw(message=message)
    finally:
        fb.flip_rechtecke = e_rect
        fb.flip_rows = e_rows
        fb.flip = e_voll
    return bytes_[0], zahl


VOLL_1080 = 1920 * 1080 * 4
# DIE GRENZEN SIND GEMESSEN, NICHT GEWUENSCHT, und beim ersten Lauf hat
# dieser Test genau deshalb eine falsche Zahl im Quelltext ueberfuehrt:
# dort stand die Galerie mit 1,02 MB: der Wert der wirklich GEAENDERTEN
# Bildpunkte. Kopiert werden aber die freigeraeumten RECHTECKE, und die
# sind ein Obermenge davon - die Textspalte der Galerie wird auf ihrer
# ganzen Hoehe freigeraeumt, weil der Titel mal kuerzer, mal laenger
# ist, auch wenn dabei Hintergrund auf Hintergrund faellt. Gemessen:
#
#   Raster links/rechts   3,74 MB  ->  1,19 MB   (Faktor 3,1)
#   Raster hoch/runter    6,50 MB  ->  1,19 MB   (Faktor 5,5)
#   Galerie (Vollbild)    7,91 MB  ->  3,71 MB   (Faktor 2,1)
#
# Die Kachelbaender bestehen zu zwei Dritteln aus den zwei Kacheln, der
# Rest ist Namenszeile und Fusszeile - die gehen ueber die volle Breite
# und lassen sich nicht schmaler machen.
for ansicht, ziel, grenze, tag in (("raster", 2, 1.3, "Raster links/rechts"),
                                   ("raster", 6, 1.3, "Raster hoch/runter "),
                                   ("galerie", 2, 3.9, "Galerie            ")):
    fk = spieleliste(1920, 1080, ansicht)
    n, zahl = kopierbilanz(fk, _setz_item, 1, ziel)
    mb = n / 1048576.0
    check("%s %5.2f MB statt %4.2f MB" % (tag, mb, VOLL_1080 / 1048576.0),
          mb <= grenze and zahl["voll"] == 0,
          "Rechteck-Aufrufe %d, Baender %d, Vollbilder %d"
          % (zahl["rect"], zahl["rows"], zahl["voll"]))
    check("%s nimmt den Rechteck-Weg" % tag, zahl["rect"] >= 1,
          "%s" % zahl)

# Und die Gegenprobe: mit ausgeschaltetem Schalter MUSS es der alte Weg
# sein - Baender im Raster, Vollbild in der Galerie. Sonst waere der
# Schalter eine Beruhigung ohne Wirkung.
_alt_flag = S.RECHTECK_FLIP_AUS_FLAG
try:
    S.RECHTECK_FLIP_AUS_FLAG = _flag
    open(_flag, "w").close()
    H._zwischenspeicher_leeren()
    fk = spieleliste(1920, 1080, "raster")
    n, zahl = kopierbilanz(fk, _setz_item, 1, 2)
    check("Schalter aus: das Raster nimmt wieder Baender",
          zahl["rows"] >= 1 and zahl["rect"] == 0, "%s" % zahl)
    gk = spieleliste(1920, 1080, "galerie")
    n2, zahl2 = kopierbilanz(gk, _setz_item, 1, 2)
    check("Schalter aus: die Galerie nimmt wieder das Vollbild",
          zahl2["voll"] == 1 and zahl2["rect"] == 0, "%s" % zahl2)
    # Und auch DANN muss das Bild stimmen.
    vergleich(gk, _setz_item, (1, 21), "Schalter aus Galerie")
finally:
    S.RECHTECK_FLIP_AUS_FLAG = _alt_flag
    if os.path.exists(_flag):
        os.unlink(_flag)
    H._zwischenspeicher_leeren()

# ---------------------------------------------------------------------------
print()
print("Test 6b: wer darf das Warten auslassen - und wer nicht")
# ---------------------------------------------------------------------------
# Der Punkt, an dem im Quelltext eine falsche Zahl stand. Die
# Entscheidung faellt ueber die BYTES, in volle Bildzeilen umgerechnet,
# gegen dieselbe eine Grenze VSYNC_SKIP_MAX_ANTEIL:
#
#   Raster   1,19 MB = 162 von 1080 Zeilen = 15 %  ->  laesst aus
#   Galerie  3,71 MB = 506 von 1080 Zeilen = 47 %  ->  wartet
#
# Die Galerie wartet also WEITERHIN, und das ist Absicht (Abwaegung aus
# Build 93: ein Riss quer durch Cover und Textspalte ist sichtbar). Wer
# das aendern will, raeumt die Textspalte kleiner frei - er hebt nicht
# die Grenze an.
_echt_fs = S.fast_scroll_enabled
try:
    S.fast_scroll_enabled = (lambda: True)
    fm.fast_scroll_enabled = (lambda: True)
    for ansicht, erwartet, tag in (("raster", True, "Raster "),
                                   ("galerie", False, "Galerie")):
        fv = spieleliste(1920, 1080, ansicht)
        fv.item_i = 1
        fv._force_full_redraw = True
        fv._last_input_time = H.NOW[0]
        fv.draw()
        gesehen = []
        _e = fv.fb.flip_rechtecke

        def _h(r, skip_vsync=False, _e=_e):
            gesehen.append(bool(skip_vsync))
            return _e(r, skip_vsync=skip_vsync)

        fv.fb.flip_rechtecke = _h
        fv.item_i = 2
        fv._last_input_time = H.NOW[0]
        fv.draw()
        check("%s skip_vsync=%s, wie gerechnet" % (tag, erwartet),
              gesehen == [erwartet], "gesehen: %s" % gesehen)
    # Und ohne den Schalter wartet BEIDES - die Grenze ist nur die
    # zweite Bedingung, der Schalter bleibt die erste.
    S.fast_scroll_enabled = (lambda: False)
    fm.fast_scroll_enabled = (lambda: False)
    fv = spieleliste(1920, 1080, "raster")
    fv.item_i = 1
    fv._force_full_redraw = True
    fv.draw()
    gesehen = []
    _e = fv.fb.flip_rechtecke
    fv.fb.flip_rechtecke = (lambda r, skip_vsync=False, _e=_e:
                            (gesehen.append(bool(skip_vsync)),
                             _e(r, skip_vsync=skip_vsync))[1])
    fv.item_i = 2
    fv._last_input_time = H.NOW[0]
    fv.draw()
    check("ohne den Schalter wartet auch das Raster",
          gesehen == [False], "gesehen: %s" % gesehen)
finally:
    S.fast_scroll_enabled = _echt_fs
    fm.fast_scroll_enabled = _echt_fs

# ---------------------------------------------------------------------------
print()
print("Test 7: der Python-Rueckfall liefert BITGENAU dasselbe wie C")
# ---------------------------------------------------------------------------
# Ohne diese Pruefung waere der Rueckfall (kein libdragend auf dem
# Geraet) ungetestet - und er laeuft dort, wo niemand hinsieht.
fc = spieleliste(1920, 1080, "raster")
_kop = fm.Framebuffer.rechteck_kopierer
check("der C-Kopierer ist ueberhaupt eingehaengt", _kop is not None,
      "sonst prueft dieser Test zweimal denselben Weg")
try:
    fc.item_i = 1
    fc._force_full_redraw = True
    fc.draw()
    fc.item_i = 2
    fc.draw()
    mit_c = bytes(fc.fb.mm)
    fc.fb.rechteck_kopierer = None
    fc.item_i = 1
    fc._force_full_redraw = True
    fc.draw()
    fc.item_i = 2
    fc.draw()
    ohne_c = bytes(fc.fb.mm)
    d = sum(1 for a, b in zip(mit_c, ohne_c) if a != b)
    check("C und Python schreiben dasselbe", d == 0,
          "" if d == 0 else "%d abweichende Bytes" % d)
finally:
    fc.fb.rechteck_kopierer = _kop

# Und der Python-Weg allein muss auch gegen den VOLLEN Aufbau stimmen -
# sonst waeren beide Wege gleich falsch.
fp = spieleliste(1920, 1080, "raster")
fp.fb.rechteck_kopierer = None
vergleich(fp, _setz_item, (1, 2, 6, 21), "ohne C")

# ---------------------------------------------------------------------------
print()
print("Test 8: der Bildwaechter schlaegt keinen Fehlalarm")
# ---------------------------------------------------------------------------
# DIE SUBTILSTE FRAGE des ganzen Builds, und sie steht im Quelltext von
# flip_rechtecke() ausdruecklich als Bedingung: die Proben des Waechters
# sind GANZE Zeilen, ein Rechteck schreibt eine Zeile nur zum Teil. Der
# Sollwert wird trotzdem aus dem PUFFER aufgefrischt - das ist nur dann
# richtig, wenn der Puffer ausserhalb der Rechtecke schon vorher dem
# Schirm entsprach.
#
# Waere es nicht so, meldete der Waechter das eben selbst Geschriebene
# als fremdes Bild und kopierte zur "Reparatur" das Vollbild - bei jedem
# Schritt. Das Bild bliebe richtig, der ganze Gewinn waere weg, und die
# Tests 2-7 saehen es nicht.
os.environ["DRAGEND_BILDWAECHTER"] = "8"
try:
    for ansicht, tag in (("raster", "Raster "), ("galerie", "Galerie")):
        fw = spieleliste(1920, 1080, ansicht)
        fw.fb._waechter_einrichten()
        check("%s der Waechter ist eingerichtet" % tag, fw.fb._waechter_an)
        fw.item_i = 0
        fw._force_full_redraw = True
        fw.draw()
        fw.fb._waechter_repariert = 0
        # Vierzig Schritte, wie bei gehaltener Taste. Die kuenstliche Uhr
        # steht, WAECHTER_TAKT kann also nicht bremsen - jeder Schritt
        # sieht wirklich nach.
        for i in range(1, 41):
            fw.item_i = i % len(TITEL)
            fw.draw()
        check("%s 40 Schritte ohne eine einzige Reparatur" % tag,
              fw.fb._waechter_repariert == 0,
              "%d Reparaturen - jede kopiert das Vollbild"
              % fw.fb._waechter_repariert)
        # Und er darf dabei nicht blind geworden sein: ein echter
        # Fremdschreiber MUSS weiterhin auffallen.
        #
        # EINMAL FALSCH GEBAUT (und der Fehler war meiner): hier stand
        # ein einzelner Aufruf von _waechter_pruefen(). Der sieht aber
        # seit Build 210 nur WAECHTER_PRO_BLICK Proben je Blick im
        # Ringverfahren an (4 von 20) - die manipulierte Zeile war
        # schlicht nicht dran, und der Test meldete einen Fehler, den es
        # nicht gab. Jetzt so viele Blicke wie der Ring braucht.
        off = fw.fb._waechter_offsets[len(fw.fb._waechter_offsets) // 2]
        zb = fw.fb._waechter_zeile_bytes
        fw.fb.mm[off:off + zb] = b"\xff" * zb
        _proben = len(fw.fb._waechter_offsets)
        _pro = max(1, int(getattr(fw.fb, "WAECHTER_PRO_BLICK", _proben)))
        _blicke = _proben // _pro + 2
        _gefunden = any(fw.fb._waechter_pruefen() for _ in range(_blicke))
        check("%s ein echter Fremdschreiber faellt weiterhin auf" % tag,
              _gefunden,
              "%d Blicke fuer %d Proben - sonst waere der Waechter durch "
              "Build 215 blind geworden" % (_blicke, _proben))
finally:
    del os.environ["DRAGEND_BILDWAECHTER"]

# ---------------------------------------------------------------------------
print()
print("Test 9: flip_rechtecke() selbst - Zuschnitt und Buchfuehrung")
# ---------------------------------------------------------------------------
H.set_screen(320, 240)
fb = fm.Framebuffer()
fb.buf[:] = bytearray([0xAB]) * len(fb.buf)
check("nichts zu tun ergibt 0 Bytes", fb.flip_rechtecke([]) == 0)
check("ein leeres Rechteck ebenso",
      fb.flip_rechtecke([(10, 10, 0, 5)]) == 0)
check("eines ausserhalb des Bildes ebenso",
      fb.flip_rechtecke([(400, 300, 10, 10)]) == 0)
n = fb.flip_rechtecke([(0, 0, 10, 4)])
check("10x4 sind 160 Bytes", n == 160, "%d" % n)
check("und sie stehen auf dem Schirm",
      bytes(fb.mm[0:40]) == b"\xab" * 40)
check("der Rest aber nicht", bytes(fb.mm[40:80]) == b"\x00" * 40,
      "sonst kopiert es mehr als verlangt")
# Negativ und ueber den Rand hinaus: zugeschnitten, nicht abgestuerzt.
n = fb.flip_rechtecke([(-5, -5, 10, 10)])
check("negative Ecken werden zugeschnitten", n == 5 * 4 * 5, "%d" % n)
n = fb.flip_rechtecke([(315, 235, 20, 20)])
check("und der Ueberhang rechts unten auch", n == 5 * 4 * 5, "%d" % n)
_gen = fb.flip_gen
fb.flip_rechtecke([(0, 0, 4, 4)])
check("jeder Flip zaehlt die Bildnummer hoch", fb.flip_gen == _gen + 1,
      "der Vorauslader haengt daran")

# ---------------------------------------------------------------------------
print()
print("Test 10: die Sammelstelle laeuft nicht aus")
# ---------------------------------------------------------------------------
# Bliebe _flip_spuren nach einem Schritt stehen, wuechse die Liste ueber
# den naechsten hinaus - und der wuerde Flaechen mitkopieren, die
# laengst auf dem Schirm stehen. Wachsende Kosten je Schritt, und die
# Tests 2-7 blieben gruen.
fs = spieleliste(1920, 1080, "raster")
check("nach einem vollen Aufbau ist sie leer",
      fs._flip_spuren is None, repr(fs._flip_spuren))
fs.item_i = 2
fs.draw()
check("nach einem schnellen Schritt auch",
      fs._flip_spuren is None, repr(fs._flip_spuren))
fs.item_i = 3
fs.draw(message="Hinweis")
check("mit Fussmeldung ebenfalls", fs._flip_spuren is None)
# Der Weg OHNE flip (Attract-Modus, Vorauslader) muss sie genauso
# loswerden - er kommt gar nicht am Flip vorbei, wo man es beilaeufig
# erledigen koennte.
fs.item_i = 4
fs.draw_page_items(flip=False)
check("und auch der Aufruf mit flip=False",
      fs._flip_spuren is None, repr(fs._flip_spuren))
gs = spieleliste(1920, 1080, "galerie")
gs.item_i = 2
gs.draw()
check("die Galerie raeumt sie ebenso auf", gs._flip_spuren is None)
gs.item_i = 3
gs.draw_page_items(flip=False)
check("auch dort mit flip=False", gs._flip_spuren is None)

# ---------------------------------------------------------------------------
print()
print("Test 11: die Suche nimmt weiterhin den alten Weg")
# ---------------------------------------------------------------------------
# Der Suchbalken liegt ueber dem Bild und wird NICHT ueber
# _restore_row_bg() freigeraeumt - fuer ihn gibt es also keine Spur, und
# ein Rechteck-Flip liesse ihn halb stehen. Derselbe Grund, aus dem der
# Bandweg ihn seit Build 133 ausnimmt.
fq = spieleliste(1920, 1080, "raster")
fq.item_i = 1
fq._force_full_redraw = True
fq.draw()
fq._search_mode = True
try:
    n, zahl = kopierbilanz(fq, _setz_item, 1, 2)
    check("in der Suche kein Rechteck-Flip", zahl["rect"] == 0, "%s" % zahl)
finally:
    fq._search_mode = False

shutil.rmtree(TMP, ignore_errors=True)

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  - " + x)
    sys.exit(1)
print("Alles in Ordnung.")
