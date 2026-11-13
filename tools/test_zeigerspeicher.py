#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Der Zeigerspeicher haelt, und der Bench misst jede Ansicht (Build 319).

DER ANLASS: "Ich moechte dass es das beste Frontend wird fuer den
MiSTer! Schnell und lagfrei!"

Bevor irgendetwas beschleunigt wurde, wurde gezaehlt - und drei Dinge
kamen heraus, die alle nicht dort lagen, wo sie vermutet wurden:

  1. "Rest in Python 5,25 ms" in karte_mit_schatten war ein NAME und
     keine Messung. Die Zeit im Kopierer hat nie jemand genommen.
  2. Der Zeigerspeicher in fe/art.py (sechs Plaetze) wurde in JEDEM
     Scrollschritt mindestens einmal geleert, in jeder Ansicht mit
     einer Karte: sieben bis dreizehn neu gebaute Zeiger je Schritt.
  3. Der Bench hat seit Build 316 die drei neuen Hauptseiten nie
     gemessen, haette seit Build 318 die Liste unter dem Namen
     "Haupt coverflow" ein zweites Mal gemessen, und hat seit Build
     219 in jeder Zeile der Spieleliste einen vollen Aufbau im
     Mittelwert mitgeschleppt.

WAS DIESER TEST SICHERT:
  1. bytes gehen ohne ctypes-Objekt durch, alles andere bekommt eine
     ZAHL als Adresse und wird gemerkt,
  2. zeilen_kopieren(quell_off=...) schreibt bitgenau dasselbe wie
     der alte Weg ueber eine geschnittene memoryview - und schreibt
     nie ueber das Ende der Quelle hinaus,
  3. die Karte mit Aussparung ist bitgenau dieselbe wie mit einem
     Kopierer in reinem Python,
  4. DIE ZUSAGE: in jeder Ansicht beider Seiten wird je Scrollschritt
     KEIN Zeiger neu gebaut und der Speicher nie geleert - und die
     Gegenprobe, dass diese Pruefung auch rot werden kann,
  5. die Scheiben der Kartenvorlage sind Zahlen, keine Objekte,
  6. vergleichsname_gemerkt() ist gleichwertig, begrenzt, und steht
     nur auf der Nachschlage-Seite,
  7. der Bench fragt EINE Stelle nach den Ansichten einer Seite und
     misst nichts unter falschem Namen - auch nicht auf der Roehre,
  8. Abschnitt J nennt Verteilung, Vollbild-Flips und Zeiger; in
     einem Fenster, in dem nur der Zeiger pendelt, laeuft KEIN voller
     Aufbau,
  9. Abschnitt K misst die Zeit im Kopierer und zaehlt, WARUM der
     kurze Weg nicht greift.

Ausfuehren:
    python3 tools/test_zeigerspeicher.py
"""
import contextlib
import ctypes
import io
import os
import re
import sys
import time

_ECHTE_UHR = time.monotonic

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
import fe.art as A                                       # noqa: E402
import fe.bench as B                                     # noqa: E402
import fe.framebuffer as FB                              # noqa: E402
import fe.settings as S                                  # noqa: E402
from _quelle import koerper, nur_code                    # noqa: E402

FBK = FB.Framebuffer

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


print(__doc__.strip().split("\n")[0])
print()

_QA = open(os.path.join(_REPO, "frontend", "fe", "art.py"),
           encoding="utf-8").read()
_QF = open(os.path.join(_REPO, "frontend", "fe", "framebuffer.py"),
           encoding="utf-8").read()
_QB = open(os.path.join(_REPO, "frontend", "fe", "bench.py"),
           encoding="utf-8").read()
_QS = open(os.path.join(_REPO, "frontend", "fe", "show.py"),
           encoding="utf-8").read()
_QN = open(os.path.join(_REPO, "frontend", "fe", "anleitung.py"),
           encoding="utf-8").read()

HAT_C = A._LIB is not None and getattr(A, "_HAT_ZEILEN", False)
if not HAT_C:
    print("  -- libdragend nicht geladen: die Teile, die C brauchen,")
    print("     werden uebersprungen. Die Zusage gilt dann auch nicht -")
    print("     ohne C gibt es keine Zeiger.")
    print()

# ---------------------------------------------------------------------------
print("Test 1: was _roh_zeiger() zurueckgibt")
# ---------------------------------------------------------------------------
_b = bytes(range(64))
_h, _z = A._roh_zeiger(_b)
check("bytes: der Zeiger IST das Objekt", _z is _b and _h is _b,
      "c_void_p nimmt bytes selbst an - vorher c_char_p() plus cast() "
      "bei jedem blit")
_ba = bytearray(256)
A._ZEIGER.clear()
_vor = tuple(A.ZEIGER_STAND)
_h1, _z1 = A._roh_zeiger(_ba)
check("bytearray: der Zeiger ist eine ZAHL", isinstance(_z1, int)
      and _z1 > 0, "%r" % (type(_z1),))
check("und zwar die Adresse des Puffers",
      _z1 == ctypes.addressof(_h1))
check("gezaehlt wurde EIN neuer Zeiger",
      A.ZEIGER_STAND[0] - _vor[0] == 1)
_h2, _z2 = A._roh_zeiger(_ba)
check("beim zweiten Mal kommt derselbe - nichts wird neu gebaut",
      _h2 is _h1 and _z2 == _z1 and A.ZEIGER_STAND[0] - _vor[0] == 1)
check("der Eintrag HAELT den Puffer am Leben",
      A._ZEIGER[id(_ba)][0] is _ba,
      "sonst koennte seine id() neu vergeben werden und der Zeiger "
      "zeigte auf fremden Speicher")
check("kein ctypes.cast() mehr in _roh_zeiger()",
      "cast(" not in nur_code(koerper(_QA, "_roh_zeiger")),
      "der Umweg war der teure Teil: 1,81 gegen 0,46 Mikrosekunden")
# Die Obergrenze: voll heisst GANZ leeren, und das wird gezaehlt.
A._ZEIGER.clear()
_vor = tuple(A.ZEIGER_STAND)
_halten = [bytearray(8) for _ in range(A._ZEIGER_MAX + 1)]
for _p in _halten:
    A._roh_zeiger(_p)
check("ueber der Obergrenze wird einmal geleert, und das zaehlt mit",
      A.ZEIGER_STAND[1] - _vor[1] == 1
      and len(A._ZEIGER) == 1,
      "geleert %d, belegt %d" % (A.ZEIGER_STAND[1] - _vor[1],
                                 len(A._ZEIGER)))
check("die Obergrenze laesst Platz fuer mehr als eine Ansicht",
      A._ZEIGER_MAX >= 12, "%d" % A._ZEIGER_MAX)
A._ZEIGER.clear()

# ---------------------------------------------------------------------------
print()
print("Test 2: zeilen_kopieren() mit einem Versatz in die Quelle")
# ---------------------------------------------------------------------------
if HAT_C:
    QB, QH = 40, 30                       # Quelle, dicht gepackt
    qstride = QB * 4
    quelle = bytearray((i * 7 + 3) % 251 for i in range(qstride * QH))
    ZB, ZH = 64, 48
    zstride = ZB * 4

    def _ziel():
        return bytearray(b"\xEE" * (zstride * ZH))

    for (tx, ty, tw, th, zx, zy) in ((0, 0, 40, 30, 5, 4),
                                     (7, 3, 20, 11, 0, 0),
                                     (39, 29, 1, 1, 63, 47),
                                     (0, 12, 40, 5, 24, 40)):
        off = ty * qstride + tx * 4
        a = _ziel()
        b_ = _ziel()
        ok_a = A.zeilen_kopieren(a, zstride, memoryview(quelle)[off:],
                                 qstride, zx, zy, tw * 4, th)
        ok_b = A.zeilen_kopieren(b_, zstride, quelle, qstride, zx, zy,
                                 tw * 4, th, off)
        check("Ausschnitt (%d,%d %dx%d) nach (%d,%d): bitgenau wie die "
              "geschnittene memoryview" % (tx, ty, tw, th, zx, zy),
              ok_a and ok_b and a == b_)
    # bytes mit Versatz - der seltene Weg
    qb = bytes(quelle)
    a = _ziel()
    b_ = _ziel()
    A.zeilen_kopieren(a, zstride, memoryview(quelle)[qstride * 2:],
                      qstride, 1, 1, 80, 6)
    A.zeilen_kopieren(b_, zstride, qb, qstride, 1, 1, 80, 6,
                      qstride * 2)
    check("auch aus bytes mit Versatz", a == b_)
    # Grenzen
    a = _ziel()
    check("negativer Versatz wird abgelehnt, nichts geschrieben",
          not A.zeilen_kopieren(a, zstride, quelle, qstride, 0, 0, 16,
                                4, -4) and a == _ziel())
    check("Versatz hinter dem Ende wird abgelehnt",
          not A.zeilen_kopieren(a, zstride, quelle, qstride, 0, 0, 16,
                                4, len(quelle)) and a == _ziel())
    # ZU KURZE QUELLE: C kuerzt die Zeilenzahl, nie die Laenge. Mit
    # Versatz muss die GEKUERZTE Grenze gelten - sonst liest C ueber
    # das Ende des Puffers hinaus.
    off = qstride * (QH - 3)              # nur noch 3 Zeilen da
    a = _ziel()
    A.zeilen_kopieren(a, zstride, quelle, qstride, 0, 0, qstride, 10,
                      off)
    geschrieben = len([y for y in range(ZH)
                       if a[y * zstride:y * zstride + 4] != b"\xEE" * 4])
    check("eine zu kurze Quelle kuerzt die Zeilen (3 statt 10)",
          geschrieben == 3, "%d Zeilen geschrieben" % geschrieben)
    check("und der Inhalt stimmt",
          a[:qstride] == quelle[off:off + qstride])
else:
    print("  -- uebersprungen (kein C)")

# ---------------------------------------------------------------------------
print()
print("Test 3: die Karte mit Aussparung, C gegen reines Python")
# ---------------------------------------------------------------------------


def _py_kopierer(ziel, zstride, quelle, qstride, zx, zy, bb, hh,
                 quell_off=0):
    """Derselbe Vertrag wie zeilen_kopieren(), ohne C - als
    unabhaengige Gegenrechnung fuer die Versatzrechnung."""
    for r in range(hh):
        q = quell_off + r * qstride
        z = (zy + r) * zstride + zx * 4
        ziel[z:z + bb] = quelle[q:q + bb]
    return True


def _karte(kopierer, aussparen):
    H.set_screen(1920, 1080)
    f = H.make_frontend(page=1)
    fb = f.fb
    fb.clear(fm.C_BG)
    # Auf die KLASSE, mit staticmethod - und ueber einen Namen mit
    # grossem Anfangsbuchstaben: genau daran erkennt
    # tools/test_python39.py eine Klasse (siehe dort, Build 303).
    alt = FBK.__dict__.get("zeilen_kopierer")
    FBK.zeilen_kopierer = staticmethod(kopierer)
    try:
        fb.karte_mit_schatten(1035, 36, 769, 945, 9, fm.C_PANEL,
                              fb._darken(fm.C_BG, 0.55), 12,
                              aussparen=aussparen,
                              hintergrund_rgb=fm.C_BG)
        if aussparen:
            # Was der Aufrufer zusagt: er malt die Luecke selbst zu.
            ax, ay, aw, ah = aussparen
            fb.rect(ax, ay, aw, ah, (200, 10, 10))
        vorlagen = len(getattr(fb, "_kartenvorlagen", None) or ())
        return bytes(fb.buf), vorlagen
    finally:
        FBK.zeilen_kopierer = alt


if HAT_C:
    for asp in (None, (1100, 80, 640, 800), (1035, 60, 769, 100),
                (1200, 300, 37, 41)):
        c_bild, c_vorl = _karte(A.zeilen_kopieren, asp)
        p_bild, p_vorl = _karte(_py_kopierer, asp)
        check("Aussparung %-22s bitgenau" % (asp,),
              c_bild == p_bild and c_vorl >= 1 and p_vorl >= 1,
              "Vorlagen %d/%d" % (c_vorl, p_vorl))
else:
    print("  -- uebersprungen (kein C)")

# ---------------------------------------------------------------------------
print()
print("Test 4: DIE ZUSAGE - kein neuer Zeiger je Scrollschritt")
# ---------------------------------------------------------------------------


def _mit_spielen(f, n=300):
    _nm, node, _sk = f.cats[0]
    node["items"] = [("Spiel Nummer %03d" % i, "game",
                      ("/f/%d.sfc" % i, ".sfc", "SNES", None, None))
                     for i in range(n)]
    node.pop("_display_items_cache", None)


_zaehler = [0]
_bilder = {}


def _cover(quelle, breite, hoehe, **k):
    # WECHSELNDE Groessen, wie in Abschnitt K des Bench - sonst ist
    # die Aussparung immer dieselbe, und das ist der Fall, den es am
    # Geraet nicht gibt.
    _zaehler[0] += 1
    aw = max(8, int(breite) - (_zaehler[0] % 3) * 7)
    ah = max(8, int(hoehe) - (_zaehler[0] % 4) * 5)
    pix = _bilder.get((aw, ah))
    if pix is None:
        pix = bytes(bytearray([40, 90, 160, 0])) * aw * ah
        _bilder[(aw, ah)] = pix
    return (aw, ah, pix)


def zeiger_je_schritt(schritte=24, nur=None):
    """{(seite, ansicht): (neu, geleert, karten)} je Schritt."""
    H.set_screen(1920, 1080)
    f = H.make_frontend(page=0)
    _mit_spielen(f)
    echt = A.ART.get_scaled
    echt_kms = FBK.karte_mit_schatten
    karten = [0]

    def _kms(self, *a, **k):
        karten[0] += 1
        return echt_kms(self, *a, **k)

    A.ART.get_scaled = _cover
    FBK.karte_mit_schatten = _kms
    erg = {}
    try:
        for seite in (0, 1):
            f.page = seite
            if seite == 1:
                f.cat_i = 0
                f.nav_path = []
            for ansicht in B.ansichten_der_seite(S, seite):
                if nur and (seite, ansicht) not in nur:
                    continue
                if B.ansicht_einstellen(f, seite, ansicht) != ansicht:
                    continue
                f._last_input_time = 0
                schritt = B.schritt_funktion(f, seite)
                for _r in range(2):
                    for i in range(10):
                        schritt(i)
                schritt(0)
                spanne = B.fenster_spanne(f, seite)
                vor = tuple(A.ZEIGER_STAND)
                karten[0] = 0
                for i in range(schritte):
                    schritt(i % spanne)
                nach = tuple(A.ZEIGER_STAND)
                erg[(seite, ansicht)] = (
                    (nach[0] - vor[0]) / float(schritte),
                    (nach[1] - vor[1]) / float(schritte),
                    karten[0] / float(schritte))
    finally:
        A.ART.get_scaled = echt
        FBK.karte_mit_schatten = echt_kms
    return erg


if HAT_C:
    erg = zeiger_je_schritt()
    check("alle zehn Ansichten wurden gemessen", len(erg) == 10,
          "%d" % len(erg))
    for (seite, ansicht), (neu, geleert, karten) in sorted(erg.items()):
        name = ("Haupt" if seite == 0 else "Liste") + " " + ansicht
        if (seite, ansicht) == (0, "liste"):
            # DIE EINE AUSNAHME, und sie ist eine Eigenheit dieses
            # Tests, nicht des Frontends: auf der Hauptseite richtet
            # sich die Karte nach der Groesse des Abzeichens, und
            # _cover() oben wechselt sie mit Absicht bei jedem Aufruf.
            # Jede neue Groesse ist eine neue VORLAGE, also auch ein
            # neuer Puffer. Die echten Abzeichen sind alle 320x420.
            # Geprueft wird hier deshalb nur, dass nicht MEHR als eine
            # Vorlage je Schritt entsteht - vor Build 319 waren es
            # sechs Zeiger.
            check("%-18s hoechstens die eine neue Vorlage je Schritt"
                  % name, neu <= 2.0, "%.1f neu" % neu)
            continue
        check("%-18s 0 neu, 0 geleert" % name,
              neu == 0.0 and geleert == 0.0,
              "%.1f neu, %.2f geleert, %.1f Karten je Schritt"
              % (neu, geleert, karten))
    check("und die Pruefung trifft Ansichten, die wirklich Karten "
          "zeichnen",
          erg[(1, "liste")][2] >= 1.0 and erg[(1, "galerie")][2] >= 1.0
          and erg[(1, "coverflow")][2] >= 1.0,
          "sonst waere die Null billig zu haben")

    # DIE GEGENPROBE. Eine Pruefung, die nicht rot werden kann,
    # beweist nichts: mit einer zu kleinen Obergrenze MUSS der
    # Zaehler anschlagen.
    _merk = A._ZEIGER_MAX
    A._ZEIGER_MAX = 2
    try:
        klein = zeiger_je_schritt(nur={(1, "liste")})
    finally:
        A._ZEIGER_MAX = _merk
        A._ZEIGER.clear()
    check("Gegenprobe: mit zwei Plaetzen schlaegt der Zaehler an",
          klein[(1, "liste")][0] >= 1.0 and klein[(1, "liste")][1] > 0.0,
          "%.1f neu, %.2f geleert" % klein[(1, "liste")][:2])
else:
    print("  -- uebersprungen (kein C)")

# ---------------------------------------------------------------------------
print()
print("Test 5: die Scheiben der Kartenvorlage sind Zahlen")
# ---------------------------------------------------------------------------
_teile = nur_code(koerper(_QF, "_karte_teile", "Framebuffer"))
check("_karte_teile() schneidet keine memoryview mehr",
      "memoryview" not in _teile,
      "jede davon war ein eigener Platz im Zeigerspeicher")
_aus = nur_code(koerper(_QF, "_karte_aus_vorlage", "Framebuffer"))
check("_karte_aus_vorlage() reicht den Versatz als neunten Wert durch",
      len(re.findall(r"hoehe, off\)|h2, off2\)", _aus)) == 2)
_vorl = nur_code(koerper(_QF, "_karte_vorlage", "Framebuffer"))
check("auch der Bau der Vorlage schneidet nicht mehr",
      "memoryview" not in _vorl and "quell_off)" in _vorl)
if HAT_C:
    H.set_screen(1920, 1080)
    f = H.make_frontend(page=1)
    f.fb.clear(fm.C_BG)
    f.fb.karte_mit_schatten(100, 100, 400, 500, 9, fm.C_PANEL,
                            (5, 5, 5), 12,
                            aussparen=(150, 160, 300, 380),
                            hintergrund_rgb=fm.C_BG)
    eintraege = list((f.fb._kartenvorlagen or {}).values())
    alle = [t for e in eintraege for tl in e["teile"].values()
            for t in tl]
    check("die Vorlage hat vier Scheiben um die Aussparung",
          len(alle) == 4, "%d" % len(alle))
    check("jede Scheibe beginnt mit einer ganzen Zahl",
          all(isinstance(t[0], int) for t in alle))

# ---------------------------------------------------------------------------
print()
print("Test 6: vergleichsname_gemerkt()")
# ---------------------------------------------------------------------------
A._VN_MERK.clear()
for name in ("007 - The World is Not Enough (U) [!]",
             "007 - The World Is Not Enough (USA)", "", "(nur Klammer)",
             "Zelda [T+Ger] {x} (v1.1)", "Öäü ß 123", "A)B(C"):
    check("gleichwertig: %r" % name,
          A.vergleichsname_gemerkt(name) == A.vergleichsname(name)
          and A.vergleichsname_gemerkt(name) == A.vergleichsname(name))
check("auch der LEERE Vergleichsname wird gemerkt",
      A._VN_MERK.get("(nur Klammer)") == "",
      "sonst rechnete ein Name ohne Buchstaben jedes Mal neu")
_echt_vn = A.vergleichsname
_gezaehlt = [0]


def _vn_zaehlen(base):
    _gezaehlt[0] += 1
    return _echt_vn(base)


A.vergleichsname = _vn_zaehlen
try:
    A._VN_MERK.clear()
    for _ in range(8):
        A.vergleichsname_gemerkt("Chrono Trigger (USA)")
    check("achtmal gefragt, einmal gerechnet", _gezaehlt[0] == 1,
          "%d" % _gezaehlt[0])
    for i in range(A._VN_MERK_MAX + 10):
        A.vergleichsname_gemerkt("Spiel %d" % i)
    check("der Merker bleibt begrenzt",
          len(A._VN_MERK) <= A._VN_MERK_MAX,
          "%d von %d" % (len(A._VN_MERK), A._VN_MERK_MAX))
finally:
    A.vergleichsname = _echt_vn
    A._VN_MERK.clear()
for fn in ("_art_path_in", "docs_cover", "docs_bildart"):
    kc = nur_code(koerper(_QA, fn))
    check("%-14s schlaegt ueber den Merker nach" % fn,
          "vergleichsname_gemerkt(" in kc
          and not re.search(r"(?<![\w_])vergleichsname\(", kc))
check("die Anleitung ebenso",
      "idx.get(vergleichsname_gemerkt(rom_basename))" in nur_code(_QN))
# DIE ANDERE SEITE: der Index-Aufbau darf NICHT merken - dort kommt
# jeder Name genau einmal, und ein Merker waere nur Speicher.
check("der Index-Aufbau rechnet weiter direkt",
      "vergleichsname_gemerkt(" not in nur_code(
          koerper(_QA, "_index_ergaenzen")),
      "zehntausende VERSCHIEDENE Namen, jeder einmal")

# ---------------------------------------------------------------------------
print()
print("Test 7: der Bench fragt EINE Stelle nach den Ansichten")
# ---------------------------------------------------------------------------
check("Seite 0 bekommt die sechs der Hauptseite",
      B.ansichten_der_seite(S, 0) == tuple(S.ANSICHTEN_HAUPT))
check("Seite 1 die vier der Spieleliste",
      B.ansichten_der_seite(S, 1) == tuple(S.ANSICHTEN))
_bcode = nur_code(_QB)
check("in fe/bench.py laeuft keine Schleife mehr ueber S.ANSICHTEN",
      "in S.ANSICHTEN" not in _bcode,
      "genau diese Schleifen haben die Hauptseite unter falschem "
      "Namen gemessen")
check("und in fe/show.py auch nicht",
      "in S.ANSICHTEN" not in nur_code(_QS))
check("alle fuenf Schleifen fragen dieselbe Funktion",
      _bcode.count("in ansichten_der_seite(") == 4
      and nur_code(_QS).count("in BENCH.ansichten_der_seite(") == 1,
      "bench %d, show %d"
      % (_bcode.count("in ansichten_der_seite("),
         nur_code(_QS).count("in BENCH.ansichten_der_seite(")))
check("gesetzt wird nur noch ueber ansicht_einstellen()",
      _bcode.count("fe.ansicht_haupt_setzen(ansicht)") == 1
      and _bcode.count("fe.ansicht_setzen(ansicht)") == 1,
      "naemlich IN ansicht_einstellen() - jede zweite Stelle waere "
      "eine, die das Nachfragen vergisst")

for b_, h_, seite, ansicht, erwartet in (
        (1920, 1080, 0, "kachelwand", "kachelwand"),
        (1920, 1080, 1, "coverflow", "coverflow"),
        (320, 240, 0, "kachelwand", "liste"),
        (320, 240, 0, "karussell", "liste"),
        (320, 240, 1, "coverflow", "galerie"),
        (320, 240, 1, "raster", "raster"),
        (1920, 1080, 0, "coverflow", "liste")):
    H.set_screen(b_, h_)
    f = H.make_frontend(page=seite)
    f._ansicht_haupt = None
    f._ansicht_je_kat = {}
    ist = B.ansicht_einstellen(f, seite, ansicht)
    check("%4dx%-4d Seite %d %-10s -> %s"
          % (b_, h_, seite, ansicht, erwartet), ist == erwartet,
          "" if ist == erwartet else "%r" % ist)

# ---------------------------------------------------------------------------
print()
print("Test 8: Abschnitt J - jede Ansicht, mit Verteilung")
# ---------------------------------------------------------------------------
B.SCHRITTE = 20


def bericht(abschnitt, w, h, vorbereiten=None):
    H.set_screen(w, h)
    f = H.make_frontend(page=0)
    _mit_spielen(f)
    if vorbereiten:
        vorbereiten(f)
    b_ = B.Bericht()
    gefroren = fm.time.monotonic
    fm.time.monotonic = _ECHTE_UHR
    # Der Bericht schreibt jede Zeile auch auf stdout (so will man ihn
    # per SSH sehen). Hier interessiert nur der Text.
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            if abschnitt == "j":
                B._abschnitt_j(b_, f, S, A, fm)
            else:
                B._abschnitt_k(b_, f, S, A)
    finally:
        fm.time.monotonic = gefroren
    return b_.text()


def zeilen_nach(text, kopf):
    """Die Zeilen eines Ansichtsblocks in Abschnitt J."""
    aus, drin = [], False
    for z in text.splitlines():
        if z.startswith("   ") and not z.startswith("    ") \
                and " ges " in z:
            drin = z.strip().startswith(kopf)
        if drin:
            aus.append(z)
    return aus


tj = bericht("j", 1920, 1080)
check("Abschnitt J ist durchgelaufen",
      "ABGEBROCHEN" not in tj and "uebersprungen (" not in tj,
      [z for z in tj.splitlines()
       if "ABGEBROCHEN" in z or "uebersprungen (" in z][:2])
for kopf in ("Haupt liste", "Haupt raster", "Haupt galerie",
             "Haupt kachelwand", "Haupt dashboard", "Haupt karussell",
             "Liste liste", "Liste raster", "Liste galerie",
             "Liste coverflow"):
    block = zeilen_nach(tj, kopf)
    hat = " ".join(block)
    check("%-18s gemessen, mit Verteilung, Vollbild und Zeigern" % kopf,
          bool(block) and "VERTEILUNG: Median" in hat
          and "Vollbild-Flips:" in hat
          and ("Zeiger nach C:" in hat or not HAT_C))
    m = re.search(r"Vollbild-Flips: (\d+) von (\d+)", hat)
    check("%-18s KEIN voller Aufbau im Fenster" % kopf,
          bool(m) and m.group(1) == "0",
          m.group(0) if m else "Zeile fehlt")
    if HAT_C:
        m = re.search(r"Zeiger nach C: ([\d.]+) neu gebaut, ([\d.]+) mal",
                      hat)
        check("%-18s 0.0 Zeiger neu gebaut" % kopf,
              bool(m) and float(m.group(1)) == 0.0
              and float(m.group(2)) == 0.0,
              m.group(0) if m else "Zeile fehlt")
check("es gibt KEINE Zeile 'Haupt coverflow'",
      "Haupt coverflow" not in tj,
      "die Hauptseite kennt keinen Coverflow - gemessen wuerde die "
      "Liste unter falschem Namen")
check("der erste gemessene Schritt beginnt am Anfang",
      "_schritt(0)" in nur_code(koerper(_QB, "_abschnitt_j")),
      "sonst springt er von Eintrag 29 auf 0 und ist ein voller "
      "Aufbau - einer von dreissig, in jedem Bericht seit Build 219")

# Auf der Roehre: die HD-Ansichten duerfen nicht gemessen werden.
tr = bericht("j", 320, 240)
for kopf in ("Haupt kachelwand", "Haupt dashboard", "Haupt karussell",
             "Liste coverflow"):
    zl = [z for z in tr.splitlines() if z.strip().startswith(kopf)]
    check("Roehre: %-18s steht da, aber als 'nicht zu haben'" % kopf,
          len(zl) == 1 and "nicht zu haben" in zl[0]
          and " ges " not in zl[0], zl[:1])
for kopf in ("Haupt liste", "Haupt raster", "Haupt galerie",
             "Liste liste", "Liste raster", "Liste galerie"):
    check("Roehre: %-18s wird gemessen" % kopf,
          bool(zeilen_nach(tr, kopf)))

# ---------------------------------------------------------------------------
print()
print("Test 9: Abschnitt K - die Zeit im Kopierer, und das WARUM")
# ---------------------------------------------------------------------------
if HAT_C:
    tk = bericht("k", 1920, 1080)
    check("Abschnitt K ist durchgelaufen", "ABGEBROCHEN" not in tk,
          [z for z in tk.splitlines() if "ABGEBROCHEN" in z][:2])
    check("die Zeit im Kopierer wird GEMESSEN",
          "im Kopierer GEMESSEN" in tk
          and "Rest in Python (jetzt wirklich)" in tk,
          "vorher stand dort eine Differenz gegen das Modell unter "
          "dem Namen 'Rest in Python'")
    check("der Coverflow hat einen eigenen Durchgang",
          "Liste coverflow" in tk)
    m = re.findall(r"Rest in Python \(jetzt wirklich\)\s+(-?[\d.]+) ms",
                   tk)
    check("der Rest ist klein gegen den Kopierer - wie gezaehlt",
          bool(m) and all(abs(float(x)) < 1.0 for x in m), m[:4])
    check("der Haken am Kopierer nimmt die Uhr",
          "e[3] += time.monotonic() - _t" in nur_code(
              koerper(_QB, "_abschnitt_k")))
    check("beide Kopierer-Haken reichen neue Parameter durch",
          nur_code(_QB).count("bb, hh, *rest)") >= 3,
          "ein Haken, der die Parameter seines Originals aufzaehlt, "
          "bricht bei jedem neuen")

    # DAS WARUM. Auf dem Pruefstand hat kein Spiel Metadaten, der
    # Cover-Kasten wechselt die Stufe also nie und der kurze Weg
    # greift zwanzigmal von zwanzig. Am Geraet sind es sechzehn. Hier
    # wird der Zustand HERGESTELLT: jedes fuenfte Spiel bekommt einen
    # niedrigeren Kasten.
    def _stufen(f):
        K = type(f)
        echt = K.cover_box_size

        def _cbs(self, w, h, syskey, item, s):
            r = list(echt(self, w, h, syskey, item, s))
            try:
                nr = int(item[0].rsplit(" ", 1)[1])
            except Exception:                            # noqa: BLE001
                nr = 0
            if nr % 5 == 0:
                r[1] = max(20, r[1] - 60)
            return tuple(r)

        K.cover_box_size = _cbs
        _stufen.zurueck = (K, echt)

    try:
        tk2 = bericht("k", 1920, 1080, _stufen)
    finally:
        _K, _e = _stufen.zurueck
        _K.cover_box_size = _e
    teil = tk2[tk2.index("Liste liste    Taste gedrueckt"):]
    teil = teil[:teil.index("Liste raster")]
    m = re.search(r"mit Aussparung gerufen\s+(\d+) von (\d+) mal", teil)
    check("mit wechselndem Kasten greift der kurze Weg nur teilweise",
          bool(m) and 0 < int(m.group(1)) < int(m.group(2)),
          m.group(0) if m else "Zeile fehlt")
    mw = re.search(r"Cover-Kasten hat die Groesse gewechselt\s+(\d+) mal",
                   teil)
    mg = re.search(r"Puffer fuer ungueltig erklaert\s+(\d+) mal", teil)
    check("und der Bericht nennt den Grund: der Kasten",
          bool(mw) and int(mw.group(1)) > 0, mw.group(0) if mw else
          "Zeile fehlt")
    check("und NICHT den anderen: kein voller Aufbau",
          bool(mg) and int(mg.group(1)) == 0, mg.group(0) if mg else
          "Zeile fehlt")
    check("die Zahl der Wechsel erklaert die fehlenden Schritte",
          bool(m and mw)
          and int(mw.group(1)) >= int(m.group(2)) - int(m.group(1)),
          "jeder Wechsel kostet genau einen kurzen Weg")
    check("der Haken wird wieder abgenommen",
          type(H.make_frontend(page=1)).cover_box_size is _e)
else:
    print("  -- uebersprungen (kein C)")

print()
if fails:
    print("ROT: %d Pruefung(en) fehlgeschlagen:" % len(fails))
    for f_ in fails:
        print("   - " + f_)
    sys.exit(1)
print("ALLES GRUEN")
