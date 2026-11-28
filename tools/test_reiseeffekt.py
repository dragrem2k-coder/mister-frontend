#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Der Reise-Effekt der Zeitmaschine (Build 352).

GEPRUEFT WIRD:
  1. Schalter (Vorgabe AN) und Systemmenue.
  2. Der Ablauf ohne Bildschirm: Blitz, Rattern, Halten, Blitz, Weiss;
     die Jahreszahl.
  3. Der Ringtunnel (ohne C): alles im Bild, gross nach klein, der
     erste Ring deckt den Schirm.
  4. Der Wirbel in C (frontend/libdragend_x86.so, dieselbe Quelle wie
     auf dem MiSTer): Fassung 9, Bild voll, Rand unberuehrt, weisser
     Blitz, ungerade Groessen, unsinnige Masse, Freigeben. Die ARM-
     Dateien enthalten die Funktion und liegen gleich in c/ und
     daneben.
  5. Der Effekt im Frontend: mit C (Wirbel), ohne C (Tunnel), C faellt
     mittendrin aus, Taste ueberspringt (aber nicht in den ersten
     0,3 s), stehende Uhr endet trotzdem, AUS heisst gar nichts, der
     Sound mit Griff, ein Fehler haelt die Reise nicht auf, von welchem
     Jahr gereist wird.
  6. Der Sound: die Datei, ihre Herkunft, der Ersatzklang.

Ausfuehren:
    python3 tools/test_reiseeffekt.py
"""
import ctypes
import os
import sys

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
_X86 = os.path.join(_REPO, "frontend", "libdragend_x86.so")
# Die Fassung fuer den Entwicklungsrechner - dieselbe Quelle wie auf dem
# Geraet. VOR dem Geruest setzen, sonst laedt fe/art.py die ARM-Datei
# (und damit gar keine).
if os.path.exists(_X86):
    os.environ["DRAGEND_LIB"] = _X86
sys.path.insert(0, _HIER)
import _harness as H                                     # noqa: E402
import fe.reiseeffekt as RE                              # noqa: E402
import fe.zeitmaschine as ZM                             # noqa: E402
import fe.menu as MENU                                   # noqa: E402
import fe.art as A                                       # noqa: E402
import fe.audio as AU                                    # noqa: E402

fm = H.fm
fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


class Skript(object):
    def __init__(self, echt, tasten):
        self.echt = echt
        self.tasten = list(tasten)

    def __getattr__(self, n):
        return getattr(self.echt, n)

    def read_action(self, timeout=None):
        if self.tasten:
            return self.tasten.pop(0)
        return None


# ---------------------------------------------------------------------------
print("Test 1: Schalter und Menue")
# ---------------------------------------------------------------------------
check("Vorgabe AN", RE.an() is True and not os.path.exists(RE.AUS_FLAG))


def stats_items():
    sysm = MENU.system_items(False, "local", "")
    for _n, node in sysm["folders"].items():
        kinds = [k for _l, k, _a in node["items"]]
        if "diary" in kinds:
            return node["items"]
    return []


its = stats_items()
kinds = [k for _l, k, _a in its]
check("Schalter im Systemmenue, direkt nach der Zeitmaschine",
      "zeitreise_effekt_an" in kinds
      and kinds.index("zeitreise_effekt_an")
      == kinds.index("zeitmaschine_an") + 1
      and fm.t("sys_zm_effekt_an") in [l for l, _k, _a in its])
check("ausschalten", RE.toggle_an() is False and os.path.exists(RE.AUS_FLAG))
check("AUS steht im Menue",
      fm.t("sys_zm_effekt_aus") in [l for l, _k, _a in stats_items()])
check("einschalten", RE.toggle_an() is True
      and not os.path.exists(RE.AUS_FLAG))
fq = open(H.FRONTEND_PY, encoding="utf-8").read()
check("Menueschalter verdrahtet",
      'elif kind == "zeitreise_effekt_an":' in fq)
import fe.vorfuehrung as VF                              # noqa: E402
check("die Vorfuehrung kennt den Schalter",
      any("zeitreise_effekt_an" in g[3] for g in VF.GRUPPEN))

# ---------------------------------------------------------------------------
print()
print("Test 2: der Ablauf")
# ---------------------------------------------------------------------------
check("Beginn: ganz weiss, noch nichts gerattert",
      RE.phase(0.0) == (256, 0.0, False))
b_, r_, f_ = RE.phase(RE.BLITZ_EIN / 2)
check("der erste Blitz klingt ab", 100 < b_ < 156 and r_ == 0.0 and not f_,
      b_)
b_, r_, f_ = RE.phase(RE.BLITZ_EIN + RE.RATTERN / 2)
check("Rattern: ohne Blitz, halb", b_ == 0 and abs(r_ - 0.5) < 1e-9)
check("Halten: das Ziel steht",
      RE.phase(RE.BLITZ_EIN + RE.RATTERN + RE.HALTEN / 2) == (0, 1.0, False))
b_, r_, f_ = RE.phase(RE.BLITZ_EIN + RE.RATTERN + RE.HALTEN
                      + RE.BLITZ_AUS / 2)
check("der zweite Blitz kommt", 100 < b_ < 156 and r_ == 1.0 and not f_, b_)
check("dann ganz weiss",
      RE.phase(RE.GESAMT - RE.WEISS / 2) == (256, 1.0, False))
check("danach fertig", RE.phase(RE.GESAMT)[2] is True
      and RE.phase(99)[2] is True)
check("negative Zeit wie Beginn", RE.phase(-1) == RE.phase(0))
# Build 353: "kann ruhig laenger dauern, quasi so lange wie der
# Soundeffekt". Die MP3 hat 192 kbit/s fest - ihre Laenge steht damit in
# der Dateigroesse.
_mp3 = os.path.join(_REPO, "frontend", "sfx", "zeitreise.mp3")
_sound_s = os.path.getsize(_mp3) * 8 / 192000.0
check("so lang wie der Sound (bis zu 1 s Ausklingen ueber der Liste)",
      _sound_s - 1.0 <= RE.GESAMT <= _sound_s and RE.GESAMT > 5.5,
      "%.2f s Effekt, %.2f s Sound" % (RE.GESAMT, _sound_s))
check("Jahreszahl: Anfang, Ende, geklemmt",
      RE.jahr_bei(2026, 1991, 0) == 2026 and RE.jahr_bei(2026, 1991, 1)
      == 1991 and RE.jahr_bei(2026, 1991, 7) == 1991
      and RE.jahr_bei(2026, 1991, -1) == 2026)
check("Jahreszahl: schnell los, langsam ins Ziel",
      RE.jahr_bei(2026, 1991, 0.5) < 1997 and RE.jahr_bei(1980, 1990, 0.5)
      > 1987)
check("Aufhellen: 0 nichts, 256 weiss",
      RE.aufhellen((10, 20, 30), 0) == (10, 20, 30)
      and RE.aufhellen((10, 20, 30), 256) == (255, 255, 255)
      and RE.aufhellen((10, 20, 30), 999) == (255, 255, 255))

# ---------------------------------------------------------------------------
print()
print("Test 3: der Ringtunnel (ohne C)")
# ---------------------------------------------------------------------------
for b_, h_ in ((1280, 720), (320, 240), (641, 359)):
    alle_ok = True
    for t_ in (0.0, 0.07, 0.5, 1.33, 2.9):
        rr = RE.ringe(b_, h_, t_)
        for x, y, w, h, farbe in rr:
            if not (0 <= x and 0 <= y and w > 0 and h > 0 and x + w <= b_
                    and y + h <= h_ and all(0 <= c <= 255 for c in farbe)
                    and all(isinstance(v, int) for v in (x, y, w, h))):
                alle_ok = False
        tunnel = rr[:-2]
        flaechen = [w * h for _x, _y, w, h, _f in tunnel]
        if flaechen != sorted(flaechen, reverse=True):
            alle_ok = False
        if tunnel[0][:4] != (0, 0, b_, h_):
            alle_ok = False
        if len(rr) > RE.RINGE + 2:
            alle_ok = False
    check("%dx%d: im Bild, gross nach klein, der erste deckt alles"
          % (b_, h_), alle_ok)
check("der Tunnel bewegt sich",
      RE.ringe(1280, 720, 0.3) != RE.ringe(1280, 720, 0.35))
check("und ist zur selben Zeit derselbe",
      RE.ringe(1280, 720, 0.3) == RE.ringe(1280, 720, 0.3))

# ---------------------------------------------------------------------------
print()
print("Test 4: der Wirbel in C")
# ---------------------------------------------------------------------------
lib = ctypes.CDLL(_X86)
lib.dragend_version.restype = ctypes.c_int
lib.wirbel_zeichnen.restype = ctypes.c_int
lib.wirbel_zeichnen.argtypes = [ctypes.c_void_p] + [ctypes.c_int] * 6
lib.wirbel_freigeben.restype = None
check("Fassung 9", lib.dragend_version() == 9 == A.DRAGEND_LIB_VERSION)
check("fe/art.py hat sie geladen und kennt den Wirbel", A.wirbel_da())


def puffer(w, h, rand=16, fuell=0x11):
    stride = w * 4 + rand
    return (ctypes.c_ubyte * (stride * h)).from_buffer(
        bytearray([fuell]) * (stride * h)), stride


def sichtbar(buf, stride, w, h):
    roh = bytes(buf)
    return [roh[y * stride:y * stride + w * 4] for y in range(h)]


for w_, h_ in ((320, 240), (321, 181), (1, 1), (2, 3)):
    buf, stride = puffer(w_, h_)
    r = lib.wirbel_zeichnen(buf, stride, len(buf), w_, h_, 700, 0)
    zeilen = sichtbar(buf, stride, w_, h_)
    voll = all(z[3::4] == bytes(w_) for z in zeilen)
    roh = bytes(buf)
    rand_ok = all(roh[y * stride + w_ * 4:(y + 1) * stride]
                  == b"\x11" * (stride - w_ * 4) for y in range(h_))
    check("%dx%d: jeder Bildpunkt gesetzt, Rand unberuehrt" % (w_, h_),
          r == 0 and voll and rand_ok, r)
buf, stride = puffer(320, 240)
lib.wirbel_zeichnen(buf, stride, len(buf), 320, 240, 700, 0)
z = sichtbar(buf, stride, 320, 240)
farben = set(z[y][x * 4:x * 4 + 3] for y in range(0, 240, 7)
             for x in range(0, 320, 7))
check("ein Muster, keine Flaeche", len(farben) > 200, len(farben))
mitte = z[120][160 * 4:160 * 4 + 3]
check("Licht in der Mitte", min(mitte) > 200, tuple(mitte))
bild_a = bytes(buf)
lib.wirbel_zeichnen(buf, stride, len(buf), 320, 240, 700, 0)
check("dieselbe Zeit, dasselbe Bild", bytes(buf) == bild_a)
lib.wirbel_zeichnen(buf, stride, len(buf), 320, 240, 740, 0)
check("40 ms spaeter ein anderes", bytes(buf) != bild_a)
lib.wirbel_zeichnen(buf, stride, len(buf), 320, 240, 700, 256)
check("Blitz 256: alles weiss",
      all(zl == b"\xff\xff\xff\x00" * 320
          for zl in sichtbar(buf, stride, 320, 240)))
lib.wirbel_zeichnen(buf, stride, len(buf), 320, 240, 700, 999)
check("Blitz ueber 256 wird geklemmt",
      sichtbar(buf, stride, 320, 240)[5] == b"\xff\xff\xff\x00" * 320)
lib.wirbel_zeichnen(buf, stride, len(buf), 320, 240, 700, 128)
check("Blitz 128: aufgehellt, nicht weiss",
      bytes(buf) != bild_a and sichtbar(buf, stride, 320, 240)[5]
      != b"\xff\xff\xff\x00" * 320)
vorher = bytes(buf)
schlecht = (
    ("stride zu klein", (buf, 320 * 4 - 4, len(buf), 320, 240, 0, 0)),
    ("Puffer zu klein", (buf, stride, len(buf) - 1 - 16, 320, 240, 0, 0)),
    ("Breite 0", (buf, stride, len(buf), 0, 240, 0, 0)),
    ("Hoehe negativ", (buf, stride, len(buf), 320, -1, 0, 0)),
    ("zu gross", (buf, 5000 * 4, 5000 * 4 * 240, 5000, 240, 0, 0)),
    ("kein Puffer", (None, stride, len(buf), 320, 240, 0, 0)))
for name, args in schlecht:
    check("unsinnig (%s): -1, nichts geschrieben" % name,
          lib.wirbel_zeichnen(*args) == -1 and bytes(buf) == vorher)
check("Puffer genau gross genug (letzte Zeile ohne Rand): geht",
      lib.wirbel_zeichnen(buf, stride, 239 * stride + 320 * 4, 320, 240,
                          0, 0) == 0)
lib.wirbel_freigeben()
lib.wirbel_freigeben()
check("zweimal freigeben, danach wieder zeichnen",
      lib.wirbel_zeichnen(buf, stride, len(buf), 320, 240, 700, 0) == 0
      and bytes(buf)[:stride] == bild_a[:stride])
# Andere Groesse OHNE Freigeben dazwischen: es muss genau das Bild
# herauskommen, das eine frische Tabelle dieser Groesse liefert.
lib.wirbel_freigeben()
buf2, stride2 = puffer(640, 360, rand=0)
lib.wirbel_zeichnen(buf2, stride2, len(buf2), 640, 360, 700, 0)
frisch = bytes(buf2)
lib.wirbel_freigeben()
lib.wirbel_zeichnen(buf, stride, len(buf), 320, 240, 700, 0)
buf2, stride2 = puffer(640, 360, rand=0)
check("andere Groesse: neue Tabelle (wie frisch gebaut)",
      lib.wirbel_zeichnen(buf2, stride2, len(buf2), 640, 360, 700, 0) == 0
      and bytes(buf2) == frisch
      and min(sichtbar(buf2, stride2, 640, 360)[180][320 * 4:320 * 4 + 3])
      > 200)
lib.wirbel_freigeben()
fr = os.path.join(_REPO, "frontend")
for name in ("libdragend.so", "libdragend_neon.so", "libdragend_x86.so"):
    a_ = open(os.path.join(fr, name), "rb").read()
    c_ = open(os.path.join(fr, "c", name), "rb").read()
    check("%s: Wirbel drin, gleich in c/ und daneben" % name,
          b"wirbel_zeichnen" in a_ and b"wirbel_freigeben" in a_
          and a_ == c_)
cq = open(os.path.join(fr, "c", "dragend.c"), encoding="utf-8").read()
check("die Quelle nennt Fassung 9 und braucht keine libm",
      "int dragend_version(void) { return 9; }" in cq
      and "#include <math.h>" not in cq)

# ---------------------------------------------------------------------------
print()
print("Test 5: der Effekt im Frontend")
# ---------------------------------------------------------------------------


class Uhr(object):
    def __init__(self, schritt=0.05, start=100.0):
        self.t = start
        self.schritt = schritt

    def __call__(self):
        jetzt = self.t
        self.t += self.schritt
        return jetzt


def lauf(tasten=(), uhr=None, c_da=None, c_zeichnen=None,
         seiten=None, b_h=(1280, 720), merken=True):
    H.set_screen(*b_h)
    fe = H.make_frontend(page=0)
    fe._zm_uhr = uhr or Uhr()
    toene = []
    FOLGE[:] = []
    fe._play_ducked_sfx = lambda name, griff=None: (
        toene.append((name, griff)), FOLGE.append("ton"))
    bilder = []
    echt_flip = fe.fb.flip

    def _flip(*a, **k):
        bilder.append(bytes(fe.fb.buf) if merken else None)
        FOLGE.append("bild")
        return echt_flip(*a, **k)
    fe.fb.flip = _flip
    frei = []
    alt = (fm._c_wirbel_da, fm._c_wirbel_zeichnen, fm._c_wirbel_freigeben)
    if c_da is not None:
        fm._c_wirbel_da = c_da
    if c_zeichnen is not None:
        fm._c_wirbel_zeichnen = c_zeichnen
    fm._c_wirbel_freigeben = lambda: frei.append(1) or alt[2]()
    fe.inp = Skript(fe.inp, list(tasten))
    try:
        erg = fe._zm_effekt(2026, 1991)
    finally:
        fm._c_wirbel_da, fm._c_wirbel_zeichnen, fm._c_wirbel_freigeben = alt
        H.set_screen(1280, 720)
    return fe, erg, bilder, toene, frei


FOLGE = []


def bunt(roh, w, h):
    stride = len(roh) // h
    return len(set(roh[y * stride + x * 4:y * stride + x * 4 + 3]
                   for y in range(0, h, 9) for x in range(0, w, 9)))


fe, erg, bilder, toene, frei = lauf()
n_soll = int(RE.GESAMT / 0.05)
check("mit C: ganz gelaufen, Bilder nach der Uhr (plus das weisse "
      "Vorbild)", erg is True and abs(len(bilder) - 1 - n_soll) <= 2,
      len(bilder))
check("mit C: erst das weisse Bild (Tabelle gebaut), DANN der Sound",
      FOLGE[:2] == ["bild", "ton"]
      and all(z == b"\xff\xff\xff\x00" * 1280
              for z in (bilder[0][:1280 * 4],)), FOLGE[:3])
check("der Sound 'zeitreise' mit Griff, nicht abgebrochen",
      len(toene) == 1 and toene[0][0] == "zeitreise"
      and toene[0][1] is not None and not toene[0][1].abgebrochen())
check("der Wirbel (viele Farben) in der Mitte des Effekts",
      bunt(bilder[len(bilder) // 2], 1280, 720) > 300,
      bunt(bilder[len(bilder) // 2], 1280, 720))
_st = len(bilder[0]) // 720
check("zweites Bild hell (der Blitz klingt ab), letztes ganz weiss",
      sum(bilder[1][::97]) / len(bilder[1][::97]) > 150
      and all(bilder[-1][y * _st:y * _st + 1280 * 4]
              == b"\xff\xff\xff\x00" * 1280 for y in (0, 360, 719)))
check("die Tabelle wird freigegeben", frei == [1])
check("danach wird voll neu gezeichnet", fe._force_full_redraw is True)
mitte = bilder[len(bilder) // 2]
stride = len(mitte) // 720
y_k = int(720 * 0.80)
zeile = mitte[y_k * stride:y_k * stride + 1280 * 4]
check("die Jahreszahl steht im Kasten (weisse Schrift auf Dunkel)",
      b"\xff\xff\xff\x00" in zeile and b"\x14\x08\x08\x00" in zeile)

fe, erg, bilder, toene, frei = lauf(c_da=lambda: False)
check("ohne C: der Ringtunnel, ganz gelaufen, Sound sofort",
      erg is True and abs(len(bilder) - n_soll) <= 2 and FOLGE[0] == "ton"
      and 5 < bunt(bilder[len(bilder) // 2], 1280, 720) < 200,
      bunt(bilder[len(bilder) // 2], 1280, 720))

aufrufe = []


def _faellt_aus(*a):
    aufrufe.append(1)
    return len(aufrufe) < 5 and A.wirbel_zeichnen(*a)


fe, erg, bilder, toene, frei = lauf(c_zeichnen=_faellt_aus)
check("C faellt mittendrin aus: weiter mit dem Tunnel, C nicht mehr "
      "gefragt", erg is True and len(aufrufe) == 5
      and abs(len(bilder) - 1 - n_soll) <= 2)
aufrufe2 = []
fe, erg, bilder, toene, frei = lauf(
    c_zeichnen=lambda *a: aufrufe2.append(1) and False)
check("C scheitert schon am Vorbild: gleich der Tunnel, kein weisses "
      "Vorbild", erg is True and len(aufrufe2) == 1
      and FOLGE[0] == "ton" and abs(len(bilder) - n_soll) <= 2)

fe, erg, bilder, toene, frei = lauf(tasten=["ok", "ok", "ok", "ok", "ok",
                                            None, None, "back"])
check("Taste in den ersten 0,3 s zaehlt nicht, danach ueberspringt sie",
      erg is False and len(bilder) == 1 + 8, len(bilder))
check("uebersprungen: der Sound wird beendet, die Tabelle freigegeben",
      toene[0][1].abgebrochen() and frei == [1])

fe, erg, bilder, toene, frei = lauf(uhr=Uhr(schritt=0.0), merken=False)
check("stehende Uhr: endet trotzdem (MAX_BILDER, Vorbild mitgezaehlt)",
      len(bilder) == RE.MAX_BILDER, len(bilder))
fe, erg, bilder, toene, frei = lauf(uhr=Uhr(schritt=-0.1), merken=False)
check("rueckwaerts laufende Uhr: endet trotzdem",
      len(bilder) == RE.MAX_BILDER)
check("MAX_BILDER reicht fuer den ganzen Effekt bei 60 Bildern je Sekunde",
      RE.MAX_BILDER >= RE.GESAMT * 60 * 1.2, RE.MAX_BILDER)

fe, erg, bilder, toene, frei = lauf(b_h=(320, 240))
check("Roehre 320x240: Wirbel, ganz gelaufen",
      erg is True and bunt(bilder[len(bilder) // 2], 320, 240) > 100)
fe, erg, bilder, toene, frei = lauf(b_h=(320, 240), c_da=lambda: False)
check("Roehre 320x240: Tunnel, ganz gelaufen", erg is True)

RE.toggle_an()
fe, erg, bilder, toene, frei = lauf()
check("AUS: kein Bild, kein Ton", erg is False and not bilder and not toene)
RE.toggle_an()

# Die Reise selbst: mit Effekt, mit kaputtem Effekt, von welchem Jahr.
JAHRE = {"A": "1990", "B": "1991", "C": "1994"}
fm.get_meta = lambda sk, l: {"year": JAHRE.get(l, "")}
fe = H.make_frontend(page=0)
fe.cats = [("SNES", {"folders": {}, "items": [
    (n, "game", ("/f/" + n, ".sfc", "SNES", None, None)) for n in JAHRE]},
    "SNES")] + fe.cats
fe._zm_sync_kategorie()
fe.cat_i = fe._zm_index()
fe.page = 1
gerufen = []
fe._zm_effekt = lambda von, nach: gerufen.append((von, nach))
echt_inp = fe.inp
fe.inp = Skript(echt_inp, ["ok"])
fe._zm_reisen()
import time as _time                                     # noqa: E402
heute = int(_time.strftime("%Y"))
check("erste Reise: vom heutigen Jahr ins Ziel",
      gerufen == [(heute, 1990)] and fe._zm_jahr == 1990, gerufen)
fe.inp = Skript(echt_inp, ["right", "ok"])
fe._zm_reisen()
check("zweite Reise: vom letzten Reiseziel",
      gerufen[-1] == (1990, 1991) and fe._zm_jahr == 1991, gerufen)
fe.inp = Skript(echt_inp, ["back"])
fe._zm_reisen()
check("im Rad abgebrochen: kein Effekt", len(gerufen) == 2)


def _kaputt(von, nach):
    raise RuntimeError("Probe")


fe._zm_effekt = _kaputt
fe.inp = Skript(echt_inp, ["left", "ok"])
fe._zm_reisen()
fe.inp = echt_inp
check("Fehler im Effekt: die Reise findet trotzdem statt",
      fe._zm_jahr == 1990 and fe.cats[fe._zm_index()][0].endswith("1990"))

# ---------------------------------------------------------------------------
print()
print("Test 6: der Sound")
# ---------------------------------------------------------------------------
sfx = os.path.join(_REPO, "frontend", "sfx")
mp3 = os.path.join(sfx, "zeitreise.mp3")
roh = open(mp3, "rb").read() if os.path.exists(mp3) else b""
check("sfx/zeitreise.mp3 da, klein, MP3 ohne Tags",
      20000 < len(roh) < 250000 and roh[:3] != b"ID3"
      and roh[0] == 0xFF and (roh[1] & 0xE0) == 0xE0, len(roh))
q = open(os.path.join(sfx, "QUELLEN.txt"), encoding="utf-8").read()
check("Herkunft vermerkt: Pixabay, Nummer, Urheber, nicht GPL",
      "zeitreise.mp3" in q and "pixabay.com" in q and "305473" in q
      and "AudioPapkin" in q and "NICHT unter der GPL" in q)
check("Ersatzklang, falls die MP3 fehlt",
      "zeitreise" in AU.SFX_CHIME_DEFS and RE.SOUND == "zeitreise")
check("der Effekt spielt ihn wie der Zufalls-Zock (gedaempft, mit Griff)",
      "self._play_ducked_sfx(RE.SOUND, griff=griff)" in fq)

print()
if fails:
    print("ROT: %d Pruefung(en) fehlgeschlagen:" % len(fails))
    for f_ in fails:
        print("   - " + f_)
    sys.exit(1)
print("ALLES GRUEN")
