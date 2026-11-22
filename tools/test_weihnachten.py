#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Die Weihnachts-Deko (Build 342).

NUTZERWUNSCH: fallender Schnee, eine Muetze am "M", eine warmweisse
Lichterkette, Wichtel-Zock statt Zufalls-Zock - von selbst vom 1.12.
bis 6.1., und "wer es nicht will sollte es in system mit schalter an
und ausschalten koennen".

GEPRUEFT WIRD:
  1. Zeitraum und Schalter: auto/an/aus, Unbekanntes zaehlt als auto,
     der Schalter laeuft auto -> an -> aus -> auto; die Umgebung und
     ERZWUNGEN gehen vor.
  2. Das Mischen ueber grosse Ganzzahlen rechnet Punkt fuer Punkt
     dasselbe wie die Formel; das vierte Byte bleibt unberuehrt.
  3. malen() ist wiederholbar: zweimal gemalt = einmal gemalt, und nach
     einem neu geschriebenen Titel liegt die Muetze wieder genau so da
     (kein doppeltes Abdunkeln der weichen Raender). Am Schirmrand wird
     abgeschnitten statt abgestuerzt.
  4. Die Lichterkette endet samt Lichthof ueber dem Titel; bei zu
     schmalem Rand gibt es keine.
  5. Schnee raeumt sich selbst weg: nach wischen() ist der Puffer
     wieder das saubere Bild - auch wenn dazwischen jemand ueber einen
     Teil der Flocken gezeichnet hat.
  6. Im echten Frontend: Schnee faellt nur im Leerlauf, Puffer und
     Schirm bleiben dabei deckungsgleich, _schnee_weg() hinterlaesst
     beides sauber; kein Schnee bei Fenster, Navigation, Attract,
     anderer Seite oder ausgeschalteter Deko.
  7. Hauptseite: Muetze und Kette in allen sechs Ansichten; der
     schnelle Teil-Neuaufbau aendert daran keinen Bildpunkt.
  8. Wichtel-Zock: Uebersetzung, Wiedererkennen in fe/hauptseite.py und
     fe/art.py, Umbenennen an Ort und Stelle, und zurueck.
  9. Der Menuepunkt und seine Behandlung; Bench und Pruefstand
     schalten die Deko ab; die Bilder sind alle da.

Ausfuehren:
    python3 tools/test_weihnachten.py
"""
import os
import sys
import tempfile
import time

_HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HIER)
import _harness as H                                     # noqa: E402

import fe.settings as SE                                 # noqa: E402
import fe.translations as TR                             # noqa: E402
import fe.weihnachten as WN                              # noqa: E402
import fe.hauptseite as HS                               # noqa: E402
import fe.art as ART                                     # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


def lt(m, d):
    return time.struct_time((2026, m, d, 12, 0, 0, 0, 1, 0))


print(__doc__.strip().split("\n")[0])
print()
TMP = tempfile.mkdtemp(prefix="weihnacht_")
_alt_datei = SE.WEIHNACHTEN_FILE
SE.WEIHNACHTEN_FILE = os.path.join(TMP, "weihnachten")

# ---------------------------------------------------------------------------
print("Test 1: Zeitraum und Schalter")
# ---------------------------------------------------------------------------
WN.ERZWUNGEN = None
os.environ.pop("DRAGEND_WEIHNACHTEN", None)
H._zwischenspeicher_leeren()
check("ohne Datei: auto", SE.load_weihnachten() == "auto")
tage = [((11, 30), False), ((12, 1), True), ((12, 24), True),
        ((12, 31), True), ((1, 1), True), ((1, 6), True), ((1, 7), False),
        ((7, 15), False)]
check("auto: genau 1.12. bis 6.1.",
      all(WN.aktiv(lt(m, d)) == soll for (m, d), soll in tage),
      [(m, d, WN.aktiv(lt(m, d))) for (m, d), _s in tage])
stufen = [SE.cycle_weihnachten() for _ in range(3)]
check("Schalter: auto -> an -> aus -> auto", stufen == ["an", "aus", "auto"],
      stufen)
with open(SE.WEIHNACHTEN_FILE, "w") as f:
    f.write("an\n")
H._zwischenspeicher_leeren()
check("an: auch im Juli", WN.aktiv(lt(7, 15)) is True)
with open(SE.WEIHNACHTEN_FILE, "w") as f:
    f.write("aus")
H._zwischenspeicher_leeren()
check("aus: auch an Heiligabend", WN.aktiv(lt(12, 24)) is False)
with open(SE.WEIHNACHTEN_FILE, "w") as f:
    f.write("Quatsch")
H._zwischenspeicher_leeren()
check("Unbekanntes zaehlt als auto", SE.load_weihnachten() == "auto")
os.environ["DRAGEND_WEIHNACHTEN"] = "an"
check("Umgebung geht vor dem Datum", WN.aktiv(lt(7, 15)) is True)
os.environ.pop("DRAGEND_WEIHNACHTEN")
WN.ERZWUNGEN = False
check("ERZWUNGEN geht vor allem", WN.aktiv(lt(12, 24)) is False)

# ---------------------------------------------------------------------------
print()
print("Test 2: das Mischen rechnet richtig")
# ---------------------------------------------------------------------------
import random                                            # noqa: E402
rnd = random.Random(7)


def referenz(b, unter):
    out = bytearray(len(unter))
    for p in range(b.w * b.h):
        q = WN._STUFE[b.roh[p * 4 + 3]]
        for c in range(3):
            out[p * 4 + c] = (unter[p * 4 + c] * (15 - q) // 15
                              + b.roh[p * 4 + c] * q // 15)
        out[p * 4 + 3] = unter[p * 4 + 3]
    return bytes(out)


for name in ("muetze_2", "birne_3a", "birne_1b"):
    b = WN.bild(name)
    unter = bytes(rnd.randrange(256) for _ in range(b.laenge))
    check("%s: Punkt fuer Punkt wie die Formel" % name,
          b.mischen(unter) == referenz(b, unter))
b = WN.bild("muetze_3")
check("die Muetze hat weiche Raender (mehrere Zwischenstufen)",
      len(b.stufen) >= 8, len(b.stufen))

# ---------------------------------------------------------------------------
print()
print("Test 3: malen() ist wiederholbar")
# ---------------------------------------------------------------------------


class FB(object):
    def __init__(self, w, h, farbe=(11, 13, 19)):
        self.width, self.height, self.stride = w, h, w * 4
        self.buf = bytearray(bytes((farbe[2], farbe[1], farbe[0], 0))
                             * (w * h))

    @staticmethod
    def px(rgb):
        return bytes((rgb[2], rgb[1], rgb[0], 0))

    def block(self, x, y, w, h, rgb):
        for yy in range(y, y + h):
            o = yy * self.stride + x * 4
            self.buf[o:o + w * 4] = self.px(rgb) * w


WN._STAND.clear()
fb = FB(200, 120)
fb.block(40, 40, 60, 30, (250, 250, 250))       # "Titel"
sauber = bytes(fb.buf)
b = WN.bild("muetze_2")
WN.malen(fb, b, 30, 10)
einmal = bytes(fb.buf)
check("die Muetze ist zu sehen", einmal != sauber)
WN.malen(fb, b, 30, 10)
check("zweimal gemalt = einmal gemalt", bytes(fb.buf) == einmal)
fb.block(40, 40, 60, 30, (250, 250, 250))       # Titel neu geschrieben
WN.malen(fb, b, 30, 10)
check("nach neu geschriebenem Titel genau wie vorher", bytes(fb.buf) == einmal)
for _ in range(5):
    fb.block(40, 40, 60, 30, (250, 250, 250))
    WN.malen(fb, b, 30, 10)
check("auch nach fuenf Runden kein Abdunkeln", bytes(fb.buf) == einmal)
fb.block(40, 40, 60, 30, (20, 200, 20))         # Titel in anderer Farbe
WN.malen(fb, b, 30, 10)
fb2 = FB(200, 120)
fb2.block(40, 40, 60, 30, (20, 200, 20))
WN._STAND.clear()
WN.malen(fb2, b, 30, 10)
check("neuer Untergrund: wie frisch gemalt", bytes(fb.buf) == bytes(fb2.buf))
fb3 = FB(60, 40)
try:
    r = WN.malen(fb3, b, -20, -30)
    ok = r is not None and r[0] == 0 and r[1] == 0
except Exception as e:                                   # noqa: BLE001
    ok = False
    r = e
check("am Schirmrand abgeschnitten statt abgestuerzt", ok, r)
check("ganz ausserhalb: nichts", WN.malen(fb3, b, 500, 500) is None)

# ---------------------------------------------------------------------------
print()
print("Test 4: die Lichterkette")
# ---------------------------------------------------------------------------
gut = True
info = []
for W, oy, s in ((1920, 54, 3), (1280, 36, 2), (640, 24, 1), (320, 12, 1),
                 (1920, 20, 3), (1920, 100, 3)):
    plan = WN.kette_plan(W, oy, s)
    if plan is None:
        gut = False
        info.append((W, oy, "keine"))
        continue
    stuecke, birnen = plan
    for (x, y, w, d) in stuecke:
        if x < 0 or x + w > W or y < 0 or y + d > oy:
            gut = False
            info.append(("Draht", W, oy, x, y, w, d))
    for name, bx, by in birnen:
        bb = WN.bild(name)
        if bb is None or by - bb.ay + bb.h > oy or not 0 <= bx < W:
            gut = False
            info.append(("Birne", W, oy, name, by))
    if len(birnen) < 8:
        gut = False
        info.append((W, oy, len(birnen)))
check("Draht und Birnen samt Lichthof enden ueber dem Titel", gut, info)
check("zu schmaler Rand: keine Kette",
      WN.kette_plan(1920, 6, 3) is None and WN.kette_plan(1920, 0, 3) is None)

# ---------------------------------------------------------------------------
print()
print("Test 5: Schnee raeumt sich selbst weg")
# ---------------------------------------------------------------------------
fb = FB(320, 200)
fb.block(10, 10, 100, 50, (200, 40, 40))
sauber = bytes(fb.buf)
sn = WN.Schnee(320, 200, 3, seed=1)
sn.zeichnen(fb)
check("Flocken liegen", bytes(fb.buf) != sauber and len(sn.gezeichnet) > 20,
      len(sn.gezeichnet))
sn.wischen(fb)
check("nach wischen() wieder das saubere Bild", bytes(fb.buf) == sauber)
for _ in range(30):
    sn.schritt(0.05)
    sn.wischen(fb)
    sn.zeichnen(fb)
sn.wischen(fb)
check("nach 30 Schritten sauber", bytes(fb.buf) == sauber)
sn.zeichnen(fb)
fb.block(0, 80, 320, 30, (30, 90, 200))          # Laufschrift o.ae.
soll = FB(320, 200)
soll.block(10, 10, 100, 50, (200, 40, 40))
soll.block(0, 80, 320, 30, (30, 90, 200))
sn.wischen(fb)
check("dazwischen uebermalt: das Neue bleibt, der Rest wird sauber",
      bytes(fb.buf) == bytes(soll.buf))
roehre = WN.Schnee(320, 240, 1, seed=2)
check("Roehre: weniger und kleinere Flocken",
      len(roehre.flocken) == WN.SCHNEE_ZAHL_ROEHRE
      and max(len(f) for f in roehre.formen) <= 2,
      (len(roehre.flocken), [len(f) for f in roehre.formen]))

# ---------------------------------------------------------------------------
print()
print("Test 6: Schnee im echten Frontend")
# ---------------------------------------------------------------------------
WN.ERZWUNGEN = True
H.set_screen(1920, 1080)
fe = H.make_frontend(page=0)
check("aktiv beim Start erkannt", fe._weihnacht_an is True)
fe.draw()
sauber = bytes(fe.fb.buf)
check("Schirm = Puffer nach draw()", bytes(fe.fb.mm) == sauber)
fe._last_input_time = H.NOW[0] - 5.0


def ticks(n, dialog=False, nav=False):
    for _ in range(n):
        H.NOW[0] += 0.06
        fe._schnee_tick(dialog, nav)


ticks(5)
check("im Leerlauf faellt Schnee",
      fe._schnee is not None and len(fe._schnee.gezeichnet) > 20
      and bytes(fe.fb.buf) != sauber)
check("Puffer und Schirm bleiben deckungsgleich",
      bytes(fe.fb.mm) == bytes(fe.fb.buf))
fe._schnee_weg()
check("_schnee_weg(): Puffer wieder sauber", bytes(fe.fb.buf) == sauber)
check("_schnee_weg(): Schirm wieder sauber", bytes(fe.fb.mm) == sauber)
ticks(3)
fe.draw()
check("draw() raeumt den Schnee vorher weg (Bild = sauberes Bild)",
      bytes(fe.fb.buf) == sauber and not fe._schnee.gezeichnet)
for label, kw, vorher in (("kein Schnee bei offenem Fenster", {"dialog": True}, None),
                          ("kein Schnee beim Navigieren", {"nav": True}, None),
                          ("kein Schnee gleich nach einer Taste", {},
                           lambda: setattr(fe, "_last_input_time", H.NOW[0])),
                          ("kein Schnee auf anderer Seite", {},
                           lambda: setattr(fe, "page", 2)),
                          ("kein Schnee im Attract-Modus", {},
                           lambda: setattr(fe, "attract_mode", True))):
    fe.page = 0
    fe.attract_mode = False
    fe._last_input_time = H.NOW[0] - 5.0
    ticks(2)
    if vorher:
        vorher()
    ticks(2, **kw)
    check(label, not fe._schnee.gezeichnet
          and bytes(fe.fb.mm) == bytes(fe.fb.buf))
fe.page = 0
fe.attract_mode = False
fe._last_input_time = H.NOW[0] - 5.0
fe.draw()
fe._weihnacht_an = False
ticks(3)
check("Deko aus: kein Schnee", not fe._schnee.gezeichnet)
fe._weihnacht_an = True
quelle = H.nur_code(H.koerper(open(H.FRONTEND_PY, encoding="utf-8").read(),
                              "next_action"))
import re                                                # noqa: E402
check("next_action: vor 'return act' wird der Schnee weggeraeumt",
      re.search(r"self\._schnee_weg\(\)\n\s*return act\n", quelle))
check("next_action: vorgemerkte Aktion ebenso",
      re.search(r"self\._schnee_weg\(\)\n\s*return vorgemerkt\n", quelle))
check("next_action: vor dem Nachzeichnen und dem Attract-Modus",
      quelle.count("self._schnee_weg()") >= 6, quelle.count("self._schnee_weg()"))
check("next_action: der Schnee kommt als letztes in der Leerlaufrunde",
      quelle.rfind("self._schnee_tick(") > quelle.rfind("_draw_dynamic_track_marquee"))

# ---------------------------------------------------------------------------
print()
print("Test 7: Muetze und Kette auf der Hauptseite")
# ---------------------------------------------------------------------------


def band(fe):
    L = fe.layout_cats()
    zl = fe.fb.stride
    unten = L["oy"] + 24 * L["s"]
    return bytes(fe.fb.buf[0:unten * zl])


for ansicht in ("liste", "raster", "galerie", "kachelwand", "dashboard",
                "karussell"):
    WN.ERZWUNGEN = True
    fe = H.make_frontend(page=0)
    fe.ansicht_haupt_setzen(ansicht)
    fe._force_full_redraw = True
    fe.draw()
    mit = band(fe)
    WN.ERZWUNGEN = False
    fe._force_full_redraw = True
    fe.fb.full_redraw_gen += 1
    fe.draw()
    ohne = band(fe)
    check("%s: Muetze und Kette sind zu sehen" % ansicht, mit != ohne)
    WN.ERZWUNGEN = True
    fe._force_full_redraw = True
    fe.fb.full_redraw_gen += 1
    fe.draw()
    check("%s: wieder eingeschaltet genau wie vorher" % ansicht,
          band(fe) == mit)
    for schritt in (1, 1, 1, -1):
        fe.cat_i = (fe.cat_i + schritt) % len(fe.cats)
        fe.draw()
    check("%s: nach vier Schritten kein Bildpunkt anders" % ansicht,
          band(fe) == mit)
WN.ERZWUNGEN = True
fe = H.make_frontend(page=0)
fe.ansicht_haupt_setzen("liste")
fe._force_full_redraw = True
fe.draw()
fe.cat_i = (fe.cat_i + 1) % len(fe.cats)
fe.draw()
check("liste: der schnelle Weg wurde dabei wirklich genommen",
      getattr(fe, "_pgc_fast_taken", False) is True)

# ---------------------------------------------------------------------------
print()
print("Test 8: Wichtel-Zock")
# ---------------------------------------------------------------------------
WN.umleitung_setzen(True)
check("Titel heisst WICHTEL-ZOCK", TR.t("zufallszock_title") == "WICHTEL-ZOCK")
check("die Aktion darunter auch",
      TR.t("sys_zufallszock_action").startswith("Wichtel-Zock"))
check("fe/hauptseite.py erkennt beide Namen",
      HS.schluessel("WICHTEL-ZOCK") == "zufallszock_title"
      and HS.schluessel("ZUFALLS-ZOCK") == "zufallszock_title")
check("fe/art.py: dieselbe Sysart in beiden Jahreszeiten",
      "alle_fassungen(\"zufallszock_title\")" in open(ART.__file__,
                                                     encoding="utf-8").read())
WN.ERZWUNGEN = False
fe = H.make_frontend(page=0)
namen = [c[0] for c in fe.cats]
check("ohne Deko: ZUFALLS-ZOCK in der Liste", "ZUFALLS-ZOCK" in namen
      and TR.t("zufallszock_title") == "ZUFALLS-ZOCK")
WN.ERZWUNGEN = True
check("Umschalten erkannt", fe._weihnacht_pruefen(sofort=True) is True)
namen = [c[0] for c in fe.cats]
check("an Ort und Stelle umbenannt", "WICHTEL-ZOCK" in namen
      and "ZUFALLS-ZOCK" not in namen, namen)
i = namen.index("WICHTEL-ZOCK")
check("die Aktion darin heisst mit",
      fe.cats[i][1]["items"][0][0].startswith("Wichtel-Zock")
      and fe.cats[i][1]["items"][0][1] == "zufallszock_draw")
WN.ERZWUNGEN = False
fe._weihnacht_pruefen(sofort=True)
namen = [c[0] for c in fe.cats]
check("und zurueck", "ZUFALLS-ZOCK" in namen and "WICHTEL-ZOCK" not in namen
      and TR.t("zufallszock_title") == "ZUFALLS-ZOCK")
check("ohne Aenderung: nichts zu tun", fe._weihnacht_pruefen(sofort=True)
      is False)

# ---------------------------------------------------------------------------
print()
print("Test 9: Menue, Bench, Pruefstand, Bilder")
# ---------------------------------------------------------------------------
menu = open(os.path.join(os.path.dirname(H.FRONTEND_PY), "fe", "menu.py"),
            encoding="utf-8").read()
check("Menuepunkt steht in fe/menu.py", '"weihnachten", None)' in menu)
code = open(H.FRONTEND_PY, encoding="utf-8").read()
check("Behandlung: umschalten, sofort pruefen, Menue auffrischen",
      'elif kind == "weihnachten":\n' in code
      and "cycle_weihnachten()\n                            "
          "self._weihnacht_pruefen(sofort=True)" in code)
for stufe in ("auto", "an", "aus"):
    check("Beschriftung fuer %s in beiden Sprachen" % stufe,
          all(TR.TRANSLATIONS["weihnachten_" + stufe].get(l)
              for l in ("de", "en")))
check("--bench schaltet die Deko ab",
      'if sys.argv.count("--bench"):\n        WEIHNACHT.ERZWUNGEN = False' in code)
check("der Pruefstand schaltet sie ab",
      "_WEIHNACHT.ERZWUNGEN = False" in open(os.path.join(_HIER, "_harness.py"),
                                             encoding="utf-8").read())
from fe.weihnacht_bilder import BILDER                   # noqa: E402
fehlt = [n for n in ["muetze_%d" % s for s in (1, 2, 3, 4)]
         + ["birne_%d%s" % (r, v) for r in range(1, 9) for v in "ab"]
         if n not in BILDER or WN.bild(n) is None]
check("alle Bilder da und lesbar", not fehlt, fehlt)

SE.WEIHNACHTEN_FILE = _alt_datei
WN.ERZWUNGEN = False
WN.umleitung_setzen(False)
print()
if fails:
    print("ROT: %d Pruefung(en) fehlgeschlagen:" % len(fails))
    for f_ in fails:
        print("   - " + f_)
    sys.exit(1)
print("ALLES GRUEN")
