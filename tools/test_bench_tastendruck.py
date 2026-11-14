#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tastendruecke im Bench - eine Roehre statt eines Schalters (Build 308).

DER AUFTRAG, Nutzermeldung vom 08.11.:

    "ich moechte das du in bench tastendruecke mit einbaust und damit
     die listen ansicht durchscrollst 5-8 mal runter 5-8 mal hoch im
     wechsel damit du merkst im bench wo die haenger her kommen"

WAS DER BENCH BIS BUILD 307 NICHT GEMESSEN HAT. Abschnitt J setzt den
Index selbst und zeichnet - er misst, was ein ZEICHENSCHRITT kostet.
Abschnitt L misst das Fenster zwischen zwei Blicken auf das Pad. Beide
ueberspringen genau die Stelle, an der sein Befund entsteht: was
passiert, wenn mehrere Druecker ankommen, waehrend noch gezeichnet
wird.

DIE GEFAHR BEI SO EINEM ABSCHNITT IST DIE ATTRAPPE. Wer dem Frontend
die Aktion "down" direkt in die Hand drueckt, misst seine eigene
Attrappe: select(), das Buendel-Lesen aus Build 306, _translate(), der
aufgehobene Rest und gestaute_schritte() aus Build 307 kommen dann gar
nicht vor. Genau diesen Fehler hat Build 300 mit einem von Hand
gesetzten Schalter schon einmal gemacht.

DESHALB EINE os.pipe(). Sie ist ein Dateideskriptor wie
/dev/input/eventN: select() wartet darauf, os.read() liest daraus, und
ganze input_event-Strukturen hineinzuschreiben ist genau das, was der
Kernel beim echten Pad tut. Ab fe/input.py aendert sich nichts.

UND DIESER TEST PRUEFT GENAU DAS - nicht mit einem vorgefuellten
Puffer (das tut test_gestaute_schritte.py), sondern durch die ECHTE
read_action() hindurch, mit echtem select() auf einem echten
Dateideskriptor:

  1. acht Druecker durch die Roehre ergeben EINE Aktion mit n=8,
  2. der Richtungswechsel im Stoss ergibt ZWEI Aktionen, nicht 13,
  3. die Gegenprobe ohne Zusammenfassen ergibt wirklich 13,
  4. nav_anwenden() rechnet richtig, und zusammen=False schaltet ab,
  5. n Einzelschritte und ein n-facher Schritt landen am gleichen Platz,
  6. run() benutzt nav_anwenden() - die Rechnung steht nur EINMAL,
  7. schritt_funktion() benutzt zeichen_funktion() - ebenso,
  8. Abschnitt M ist in lauf() eingetragen und M haengt den Zustand
     im finally wieder zurueck,
  9. die Attrappe packt mit EVENT_FMT, nicht mit einer eigenen Zahl.

Ausfuehren:
    python3 tools/test_bench_tastendruck.py
"""
import ast
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H          # noqa: E402

import fe.input as FI         # noqa: E402
import fe.bench as FB         # noqa: E402
from _quelle import koerper, nur_code                     # noqa: E402

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BENCH_PY = os.path.join(_REPO, "frontend", "fe", "bench.py")

fails = []


def check(name, ok, info=""):
    if ok:
        print("  OK   %s %s" % (name, info))
    else:
        print("  FEHL %s %s" % (name, info))
        fails.append(name)


print(__doc__.strip().split("\n")[0])
print()

KEY_UP, KEY_DOWN, KEY_ENTER = FI.KEY_UP, FI.KEY_DOWN, FI.KEY_ENTER


def manager(pad):
    """Ein InputManager, dessen einziges Geraet die Roehre ist.

    __new__ statt __init__, weil __init__ echte Geraete oeffnen wuerde -
    dieselbe Bauart wie in test_gestaute_schritte.py. last_scan steht
    absichtlich in ferner Zukunft: rescan() wuerde die Roehre aus
    inp.devices werfen."""
    inp = FI.InputManager.__new__(FI.InputManager)
    inp.devices = {pad.path: pad}
    inp.held = None
    inp.last_scan = 1e18
    inp._zeichenzeit = {}
    inp._zeichenproben = {}
    inp._ereignis_rest = FI.deque()
    inp._vorgelegt = None
    inp.seiten_aktionen = set()
    inp.eingabe_zeit = 0.0
    inp._select_down = {}
    inp._select_kombiniert = False
    inp._last_repeat_time = 0.0
    inp._last_repeat_act = None
    inp._last_repeat_iv = 0.0
    inp.f9_gesehen = 0.0
    return inp


def neu():
    pad = FB._PadAttrappe(FI.EVENT_FMT)
    return pad, manager(pad)


# ---------------------------------------------------------------------------
print("Test 1: acht Druecker durch die ECHTE read_action()")
# ---------------------------------------------------------------------------
pad, inp = neu()
for _ in range(8):
    pad.druck(KEY_DOWN)
_act = inp.read_action(timeout=0.0)
check("die Roehre wird von select()/os.read() wirklich gelesen",
      _act == "down",
      "%r - das ist der Beweis, dass der Weg aus fe/input.py laeuft "
      "und nicht eine Attrappe" % (_act,))
_n = 1 + inp.gestaute_schritte(_act)
check("und alle acht Druecker stecken in EINEM Schritt", _n == 8,
      "n=%d" % _n)
check("der Puffer ist danach leer", not inp._ereignis_rest,
      "%d uebrig" % len(inp._ereignis_rest))
check("keine Wiederholung laeuft nach (Loslassen kam mit)",
      inp.held is None, "%r" % (inp.held,))
check("naechster Blick findet nichts mehr",
      inp.read_action(timeout=0.0) is None)
pad.close()

# ---------------------------------------------------------------------------
print()
print("Test 2: 8x runter + 5x hoch in EINEM Stoss - zwei Aktionen")
# ---------------------------------------------------------------------------
# DAS IST DER GEMELDETE FALL. Alles liegt vor dem ersten Blick in der
# Roehre, so wie es bei ihm ankommt, wenn er schneller drueckt als ein
# Schritt dauert (46,57 ms laut Abschnitt J).
pad, inp = neu()
for _ in range(8):
    pad.druck(KEY_DOWN)
for _ in range(5):
    pad.druck(KEY_UP)
_folge = []
while True:
    a = inp.read_action(timeout=0.0)
    if a is None:
        break
    _folge.append((a, 1 + inp.gestaute_schritte(a)))
check("genau zwei Aktionen fuer 13 Druecker", len(_folge) == 2,
      "%r" % (_folge,))
check("die erste ist runter mit n=8", _folge[0] == ("down", 8),
      "%r" % (_folge[0],) if _folge else "-")
check("die zweite ist hoch mit n=5",
      len(_folge) > 1 and _folge[1] == ("up", 5),
      "%r" % (_folge[1],) if len(_folge) > 1 else "-")
check("alle 13 Druecker sind gezaehlt",
      sum(n for _a, n in _folge) == 13,
      "%d" % sum(n for _a, n in _folge))
check("nichts liegt mehr vorgelegt", inp._vorgelegt is None,
      "%r" % (inp._vorgelegt,))
pad.close()

# ---------------------------------------------------------------------------
print()
print("Test 3: GEGENPROBE - ohne Zusammenfassen sind es 13 Aktionen")
# ---------------------------------------------------------------------------
# Ohne diese Gegenprobe wuerde Test 2 auch dann gruen, wenn die Roehre
# nur zwei Druecker uebertraegt. Derselbe Stoss, nur ohne
# gestaute_schritte() - es muessen 13 einzelne Aktionen herauskommen.
pad, inp = neu()
for _ in range(8):
    pad.druck(KEY_DOWN)
for _ in range(5):
    pad.druck(KEY_UP)
_einzeln = []
while True:
    a = inp.read_action(timeout=0.0)
    if a is None:
        break
    _einzeln.append(a)
check("13 einzelne Aktionen", len(_einzeln) == 13, "%d" % len(_einzeln))
check("davon 8x runter", _einzeln.count("down") == 8,
      "%d" % _einzeln.count("down"))
check("davon 5x hoch", _einzeln.count("up") == 5,
      "%d" % _einzeln.count("up"))
check("und die Reihenfolge stimmt",
      _einzeln == ["down"] * 8 + ["up"] * 5)
pad.close()

# ---------------------------------------------------------------------------
print()
print("Test 4: nav_anwenden() - und der Schalter zusammen=False")
# ---------------------------------------------------------------------------
NAV = getattr(H.fm.Frontend, "nav_anwenden", None)
check("Frontend.nav_anwenden() existiert", NAV is not None)


class FeAttrappe:
    """Nur die Felder, die nav_anwenden() anfasst.

    Eine Attrappe ist hier zulaessig, weil nav_anwenden() als UNGEBUNDENE
    Funktion gerufen wird - der Code, der geprueft wird, ist der echte
    aus frontend.py."""

    def __init__(self, inp, n_items, page=1):
        self.inp = inp
        self.page = page
        self.item_i = 0
        self.cat_i = 0
        self.cats = list(range(12))
        self._last_scroll_dir = 1
        self.marquees = 0

    def marquee_reset(self):
        self.marquees += 1


if NAV is not None:
    ITEMS = list(range(1085))
    # a) mit Zusammenfassen
    pad, inp = neu()
    for _ in range(7):
        pad.druck(KEY_DOWN)
    fe = FeAttrappe(inp, len(ITEMS))
    fe.item_i = 100
    _a = inp.read_action(timeout=0.0)
    _n = NAV(fe, _a, ITEMS, 1)
    check("sieben Druecker -> ein Schritt ueber sieben Eintraege",
          _n == 7 and fe.item_i == 107, "n=%d, item_i=%d" % (_n, fe.item_i))
    check("Richtungsmerker zeigt nach unten", fe._last_scroll_dir == 1)
    check("marquee_reset() genau einmal", fe.marquees == 1,
          "%d" % fe.marquees)
    pad.close()

    # b) OHNE Zusammenfassen - der A/B-Schalter des Bench
    pad, inp = neu()
    for _ in range(7):
        pad.druck(KEY_DOWN)
    fe = FeAttrappe(inp, len(ITEMS))
    fe.item_i = 100
    _a = inp.read_action(timeout=0.0)
    _n = NAV(fe, _a, ITEMS, 1, zusammen=False)
    check("zusammen=False fasst nicht zusammen",
          _n == 1 and fe.item_i == 101, "n=%d, item_i=%d" % (_n, fe.item_i))
    check("und der Puffer bleibt dabei voll",
          len(inp._ereignis_rest) > 0,
          "%d Ereignisse liegen noch - sie werden zu den naechsten "
          "sechs Aktionen" % len(inp._ereignis_rest))
    pad.close()

    # c) hoch zieht zurueck, und die Weite wird multipliziert
    pad, inp = neu()
    fe = FeAttrappe(inp, len(ITEMS))
    fe.item_i = 100
    _n = NAV(fe, "up", ITEMS, 1)
    check("hoch zieht zurueck", fe.item_i == 99, "%d" % fe.item_i)
    check("Richtungsmerker zeigt nach oben", fe._last_scroll_dir == -1)
    fe.item_i = 100
    NAV(fe, "right", ITEMS, 17)
    check("rechts nimmt die Seitenweite", fe.item_i == 117,
          "%d" % fe.item_i)
    pad.close()

    # d) Rundum, und zwar in beide Richtungen
    pad, inp = neu()
    fe = FeAttrappe(inp, len(ITEMS))
    fe.item_i = 3
    NAV(fe, "up", ITEMS, 1)
    check("vom Anfang nach hinten", fe.item_i == 2, "%d" % fe.item_i)
    fe.item_i = 0
    NAV(fe, "up", ITEMS, 1)
    check("und vom ersten Eintrag ans Ende", fe.item_i == 1084,
          "%d" % fe.item_i)
    pad.close()

    # e) Seite 0: Kategorien, und die neue Schranke
    pad, inp = neu()
    fe = FeAttrappe(inp, 12, page=0)
    fe.cat_i = 11
    NAV(fe, "down", [], 1)
    check("Kategorien laufen rundum", fe.cat_i == 0, "%d" % fe.cat_i)
    fe.cats = []
    try:
        NAV(fe, "down", [], 1)
        _ok = True
    except ZeroDivisionError:
        _ok = False
    check("ohne Kategorien kein Absturz", _ok,
          "vorher war das ein ZeroDivisionError mitten in run()")
    pad.close()

# ---------------------------------------------------------------------------
print()
print("Test 5: n Einzelschritte und EIN n-facher Schritt - gleicher Platz")
# ---------------------------------------------------------------------------
# Dieselbe Zusage wie test_gestaute_schritte.py Test 7, hier aber durch
# nav_anwenden() hindurch - also durch den Code, der im Betrieb laeuft.
if NAV is not None:
    _schief = []
    for gesamt in (20, 137, 1085, 31199):
        ITEMS = list(range(gesamt))
        for weite in (1, 3, 17, 25):
            for n in (1, 2, 5, 8, 13, 32):
                for act in ("up", "down"):
                    for start in (0, 1, gesamt // 2, gesamt - 1):
                        a = FeAttrappe(None, gesamt)
                        a.item_i = start
                        for _ in range(n):
                            NAV(a, act, ITEMS, weite, zusammen=False)
                        c = FeAttrappe(None, gesamt)
                        c.item_i = start
                        # Ein Schritt, der n Druecker abdeckt: genau das
                        # tut nav_anwenden(), wenn gestaute_schritte()
                        # n-1 meldet. Hier von Hand, weil kein Puffer
                        # beteiligt sein soll.
                        c.item_i = (start + weite * n
                                    * (-1 if act == "up" else 1)) % gesamt
                        if a.item_i != c.item_i:
                            _schief.append((gesamt, weite, n, act, start,
                                            a.item_i, c.item_i))
    check("in allen geprueften Faellen derselbe Eintrag", not _schief,
          "%d Abweichungen" % len(_schief) if _schief
          else "Listen bis 31.199 Eintraege, Weiten 1/3/17/25, "
               "n bis 32, beide Richtungen")

# ---------------------------------------------------------------------------
print()
print("Test 6: die Rechnung steht nur EINMAL")
# ---------------------------------------------------------------------------
_fp = os.path.join(_REPO, "frontend", "frontend.py")
_run = nur_code(koerper(open(_fp).read(), "run", "Frontend"))
check("run() ruft nav_anwenden()", "nav_anwenden(" in _run)
check("run() rechnet den Index nicht mehr selbst",
      "gestaute_schritte(" not in _run,
      "sonst stuende der Faktor an zwei Stellen - genau die Dopplung, "
      "aus der in Build 293 ein halb angewandter Fix wurde")
_nav = nur_code(koerper(open(_fp).read(), "nav_anwenden", "Frontend"))
check("nav_anwenden() ruft gestaute_schritte()",
      "gestaute_schritte(" in _nav)
check("und nur, wenn zusammengefasst werden soll",
      "if zusammen" in _nav)
check("nav_anwenden() gibt die Zahl der Druecker zurueck",
      "return n" in _nav)

# ---------------------------------------------------------------------------
print()
print("Test 7: der Zeichenschritt steht auch nur einmal")
# ---------------------------------------------------------------------------
_quelle = open(_BENCH_PY).read()
_sf = nur_code(koerper(_quelle, "schritt_funktion"))
check("schritt_funktion() benutzt zeichen_funktion()",
      "zeichen_funktion(" in _sf)
check("und zeichnet nicht mehr selbst",
      "_draw_navigate_items(" not in _sf and "_draw_navigate_cats(" not in _sf,
      "sonst waere es die dritte Fassung desselben Schritts")
_zf = nur_code(koerper(_quelle, "zeichen_funktion"))
check("zeichen_funktion() kennt den leichten Pfad",
      "_draw_navigate_items(" in _zf and "_draw_navigate_cats(" in _zf)
check("und faellt auf den vollen Aufbau zurueck", "fe.draw()" in _zf)
_m = nur_code(koerper(_quelle, "_abschnitt_m"))
# DIE ZUSAGE IST ENG, UND SIE MUSS ES SEIN: im MESSENDEN Teil darf der
# Bench den Index nicht selbst setzen, sonst misst er wieder nur das
# Zeichnen (so wie Abschnitt J). Das Warmlaufen davor darf ihn setzen -
# dort wird nichts gemessen. Ein Text-Vergleich kann das nicht
# unterscheiden, eine Baumsuche schon: gesucht wird die Abarbeitungs-
# Schleife, und IN ihr darf keine Zuweisung an item_i stehen.
_mfun0 = None
for _node in ast.walk(ast.parse(_quelle)):
    if isinstance(_node, ast.FunctionDef) and _node.name == "_abschnitt_m":
        _mfun0 = _node
_in_schleife = []
_schleifen = 0
for _node in ast.walk(_mfun0) if _mfun0 else ():
    if not isinstance(_node, ast.While):
        continue
    _schleifen += 1
    for _st in ast.walk(_node):
        if (isinstance(_st, ast.Attribute) and _st.attr == "item_i"
                and isinstance(_st.ctx, ast.Store)):
            _in_schleife.append(_st.lineno)
check("die Abarbeitungs-Schleife existiert", _schleifen >= 1,
      "%d" % _schleifen)
check("und setzt den Index NICHT selbst", not _in_schleife,
      "Zeilen %r" % (_in_schleife,) if _in_schleife
      else "sie laesst nav_anwenden() rechnen - das ist der ganze Zweck")
check("Abschnitt M ruft nav_anwenden()", "nav_anwenden(" in _m)
check("und faehrt beide Faelle (A/B)",
      "zusammen=zusammen" in _m and "(False," in _m and "(True," in _m)

# ---------------------------------------------------------------------------
print()
print("Test 8: Abschnitt M ist eingetragen und raeumt wieder auf")
# ---------------------------------------------------------------------------
_lauf = nur_code(koerper(_quelle, "lauf"))
check("lauf() ruft _abschnitt_m()", "_abschnitt_m(" in _lauf)
check("mit eigenem Fangnetz", "ABSCHNITT M ABGEBROCHEN" in _lauf)
# Build 321: "mindestens" statt "genau" - eine Gleichheit hier muss bei
# jeder neuen Bench-Fassung von Hand nachgezogen werden, und eine Zahl,
# die man jedes Mal hochsetzt, setzt man irgendwann ohne Nachdenken
# hoch. Was dieser Test sichern will, ist, dass die Nummer mit Abschnitt
# M mitgewachsen ist (Fassung 15 und spaeter).
check("BENCH_VERSION ist mindestens 22", FB.BENCH_VERSION >= 22,
      "%d" % FB.BENCH_VERSION)
# Der Zustand MUSS im finally zurueckgehen, nicht am Ende des
# Erfolgswegs: bricht ein Durchgang ab, liefe das Frontend sonst mit
# einer Roehre als einzigem Eingabegeraet weiter - also ohne Bedienung.
_baum = ast.parse(_quelle)
_mfun = None
for _node in ast.walk(_baum):
    if isinstance(_node, ast.FunctionDef) and _node.name == "_abschnitt_m":
        _mfun = _node
_zurueck = set()
for _node in ast.walk(_mfun) if _mfun else ():
    if isinstance(_node, ast.Try) and _node.finalbody:
        for _st in ast.walk(ast.Module(body=_node.finalbody,
                                       type_ignores=[])):
            if isinstance(_st, ast.Attribute) and isinstance(_st.ctx,
                                                             ast.Store):
                _zurueck.add(_st.attr)
for _feld in ("devices", "rescan", "held", "_vorgelegt", "_zeichenzeit",
              "last_scan"):
    check("finally stellt %s zurueck" % _feld, _feld in _zurueck,
          "" if _feld in _zurueck else "gefunden: %s" % sorted(_zurueck))
check("und schliesst die Roehre", "pad.close()" in _m)
check("Abschnitt M greift KEIN Eingabegeraet",
      "inp.grab(" not in _m and ".grab(True)" not in _m,
      "ein grab auf seinen echten Pads haette der Bench nicht zu "
      "vergeben")

# ---------------------------------------------------------------------------
print()
print("Test 9: die Attrappe packt mit EVENT_FMT")
# ---------------------------------------------------------------------------
# koerper() ist namensgenau und findet FUNKTIONEN, keine Klassen - bei
# einem Klassennamen liefert es "". Genau daran ist die erste Fassung
# dieses Tests gruen geworden, ohne etwas zu pruefen ("keine eigene
# Byte-Zahl" in einer leeren Zeichenkette ist immer wahr). Also die
# beiden Methoden einzeln, mit klasse= - und der Test prueft zuerst,
# dass ueberhaupt Quelltext da ist.
_roh_src = nur_code(koerper(_quelle, "_roh", "_PadAttrappe"))
_druck_src = nur_code(koerper(_quelle, "druck", "_PadAttrappe"))
check("der Quelltext der Attrappe wurde gefunden",
      bool(_roh_src.strip()) and bool(_druck_src.strip()),
      "_roh %d Zeichen, druck %d Zeichen"
      % (len(_roh_src), len(_druck_src)))
_pad_src = _roh_src + "\n" + _druck_src
check("struct.pack mit dem uebergebenen Format",
      "struct.pack(self._fmt" in _pad_src)
check("keine eigene Byte-Zahl im Pack-Weg",
      " 24" not in _pad_src and " 16)" not in _pad_src,
      "eine zweite Formatangabe waere eine zweite Gelegenheit "
      "auseinanderzulaufen - und zwar lautlos")
check("ein Druecker ist Druecken UND Loslassen",
      _druck_src.count("self._roh(") == 4,
      "ohne Loslassen liefe nach dem Stoss eine Wiederholung weiter")
# Und die Gegenprobe am Objekt: das Format kommt wirklich von input.py.
_pad = FB._PadAttrappe(FI.EVENT_FMT)
try:
    _pad.druck(KEY_ENTER)
    _roh = os.read(_pad.fd, FI.EVENT_SIZE * 8)
    check("vier Ereignisse je Druecker, in EVENT_SIZE-Schritten",
          len(_roh) == 4 * FI.EVENT_SIZE,
          "%d Byte bei EVENT_SIZE=%d" % (len(_roh), FI.EVENT_SIZE))
    import struct as _st2
    _e0 = _st2.unpack_from(FI.EVENT_FMT, _roh, 0)
    check("und input.py packt sie richtig aus",
          _e0[2] == FI.EV_KEY and _e0[3] == KEY_ENTER and _e0[4] == 1,
          "%r" % (_e0,))
finally:
    _pad.close()

# ---------------------------------------------------------------------------
print()
if fails:
    print("ROT: %d Pruefung(en) fehlgeschlagen:" % len(fails))
    for f in fails:
        print("   - %s" % f)
    sys.exit(1)
print("ALLES GRUEN")
