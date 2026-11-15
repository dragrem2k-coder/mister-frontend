#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Start + Select + L + R am Pad fuehrt aus dem Spiel ins Frontend (Build 326).

NUTZERWUNSCH: "warum wir mit f1 aus einem spiel wieder ins frontend
wechseln koennen aber per tastencombination am joypad nicht, ich haette
das aber gerne wenn man zum beispiel start, select, l, r gleichzeitig
drueckt das auch geschieht".

WARUM ES BISHER NICHT GING: waehrend ein Core laeuft, sperrt MiSTer die
evdev-Ebene - die alte Start+Select-Pruefung bekam nie ein Ereignis. F1
kommt ueber die rohe HID-Ebene. Der Pro Controller (Treiber hid-nintendo)
liefert seine Berichte dort ebenfalls - in einem bekannten Format.

GEPRUEFT WIRD:
  1. Das Lesen eines Berichts: echte Bytefolgen eines Pro Controllers
     (Bericht 0x30) ergeben genau die gedrueckten Tasten; ein fremdes
     Format ergibt None ("weiss nicht"), nicht "nichts gedrueckt".
  2. Die Erkennung des Geraets an Hersteller oder Name.
  3. wait_game_exit() Ende-zu-Ende mit einem nachgebauten hidraw-Geraet
     (Paket-Socket, wie hidraw je Bericht ein Paket liefert):
     a) alle vier gehalten -> "pad_combo"
     b) GEGENPROBE: drei von vier gehalten -> kein Ausstieg
     c) GEGENPROBE: dieselben Bytes von einem Nicht-Nintendo-Geraet ->
        kein Ausstieg (dort koennten die Bits etwas anderes heissen)
     d) zwei Joy-Con: Minus+L links, Plus+R rechts -> "pad_combo"
     e) nur kurz gestreift (kuerzer als PAD_COMBO_HOLD) -> kein Ausstieg
  4. run_core() behandelt "pad_combo" wie F1.

Ausfuehren:
    python3 tools/test_pad_ausstieg.py
"""
import os
import socket
import sys
import threading
import time

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
sys.path.insert(0, os.path.join(_REPO, "frontend"))
sys.path.insert(0, _HIER)

import fe.hidraw as HR                                   # noqa: E402
import fe.input as I                                     # noqa: E402
from _quelle import koerper, nur_code                    # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


print(__doc__.strip().split("\n")[0])
print()


def bericht(rechts=0, mitte=0, links=0, art=0x30):
    """Ein Vollbericht wie vom Pro Controller: Kennung, Zeitgeber,
    Akku, drei Tastenbytes, dann Sticks und Bewegungsdaten."""
    roh = bytearray(49)
    roh[0] = art
    roh[1] = 0x5A
    roh[2] = 0x8E
    roh[3], roh[4], roh[5] = rechts, mitte, links
    roh[6:12] = bytes((0x00, 0x08, 0x80, 0x00, 0x08, 0x80))  # Sticks Mitte
    return bytes(roh)


R_ = 0x40          # Byte 3
PLUS, MINUS = 0x02, 0x01   # Byte 4
L_ = 0x40          # Byte 5
ALLE_VIER = bericht(rechts=R_, mitte=PLUS | MINUS, links=L_)
DREI = bericht(rechts=R_, mitte=PLUS | MINUS)
NICHTS = bericht()

# ---------------------------------------------------------------------------
print("Test 1: einen Bericht lesen")
# ---------------------------------------------------------------------------
check("alle vier", HR.nintendo_pad_tasten(ALLE_VIER) == HR.PAD_AUSSTIEG,
      HR.nintendo_pad_tasten(ALLE_VIER))
check("nichts gedrueckt ist ein LEERES Set",
      HR.nintendo_pad_tasten(NICHTS) == frozenset())
check("A allein", HR.nintendo_pad_tasten(bericht(rechts=0x08))
      == frozenset(["a"]))
check("ZL/ZR sind nicht L/R",
      HR.nintendo_pad_tasten(bericht(rechts=0x80, links=0x80))
      == frozenset(["zr", "zl"]))
check("die Antwort 0x21 traegt dieselben Bytes",
      HR.nintendo_pad_tasten(bericht(rechts=R_, mitte=PLUS | MINUS,
                                     links=L_, art=0x21))
      == HR.PAD_AUSSTIEG)
check("fremdes Format: None, nicht 'nichts gedrueckt'",
      HR.nintendo_pad_tasten(b"\x01\x80\x80\x80\x80\x08\x00\x00") is None)
check("zu kurz: None", HR.nintendo_pad_tasten(b"\x30\x00\x00") is None)
check("leer: None", HR.nintendo_pad_tasten(b"") is None)

# ---------------------------------------------------------------------------
print()
print("Test 2: das Geraet erkennen")
# ---------------------------------------------------------------------------
check("Pro Controller am Hersteller",
      HR.ist_nintendo_pad((0x057E, 0x2009, "irgendwas")))
check("Joy-Con am Namen", HR.ist_nintendo_pad((0x1234, 0x1, "Joy-Con (L)")))
check("Pro Controller am Namen",
      HR.ist_nintendo_pad((0, 0, "Nintendo Co., Ltd. Pro Controller")))
check("GEGENPROBE: ein Sony-Pad nicht",
      not HR.ist_nintendo_pad((0x054C, 0x09CC, "Wireless Controller")))
check("GEGENPROBE: eine Tastatur nicht",
      not HR.ist_nintendo_pad((0x046D, 0x4023, "Logitech Wireless Keyboard")))


# ---------------------------------------------------------------------------
# Ende-zu-Ende
# ---------------------------------------------------------------------------
def lauf(geraete, folge, frist=1.5):
    """wait_game_exit() mit nachgebauten hidraw-Geraeten.
    geraete: {pfad: kennung}; folge: [(Verzoegerung s, pfad, bericht)].
    Liefert das Ergebnis oder "frist" (nach frist Sekunden der Core
    'beendet', damit der Test nicht haengt)."""
    paare = {}
    for pfad in geraete:
        a, b = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        paare[pfad] = (a, b)
    echt = (I.glob.glob, I._find_keyboard_hidraws, I.os.open,
            I.hidraw_kennung, I.current_core)
    ende = [False]

    def _open(pfad, flags, *a):
        if pfad in paare:
            return os.dup(paare[pfad][1].fileno())
        return echt[2](pfad, flags, *a)

    I.glob.glob = lambda muster: (sorted(paare) if "hidraw" in muster
                                  else echt[0](muster))
    I._find_keyboard_hidraws = lambda: []
    I.os.open = _open
    I.hidraw_kennung = lambda pfad: geraete[pfad]
    I.current_core = lambda: "MENU" if ende[0] else "SNES"
    inp = I.InputManager.__new__(I.InputManager)
    inp.devices = {}
    inp.last_scan = time.monotonic() + 1e9

    stopp = threading.Event()

    def _senden():
        for warte, pfad, roh in folge:
            if stopp.wait(warte):
                return                    # der Lauf ist schon vorbei
            try:
                paare[pfad][0].send(roh)
            except OSError:
                return
        stopp.wait(frist)
        ende[0] = True
    t = threading.Thread(target=_senden, daemon=True)
    t.start()
    try:
        erg = inp.wait_game_exit()
    finally:
        stopp.set()
        t.join(2.0)
        (I.glob.glob, I._find_keyboard_hidraws, I.os.open,
         I.hidraw_kennung, I.current_core) = echt
        for a, b in paare.values():
            a.close()
            b.close()
    return "frist" if erg == "menu" else erg


PRO = {"/dev/hidraw7": (0x057E, 0x2009, "Pro Controller")}
P = "/dev/hidraw7"

print()
print("Test 3a: alle vier gehalten")
# Wie der Controller es tut: waehrend des Haltens kommt ein Bericht
# nach dem anderen (hier alle 15 ms).
t0 = time.monotonic()
erg = lauf(PRO, [(0.05, P, NICHTS)] + [(0.015, P, ALLE_VIER)] * 40)
dauer = time.monotonic() - t0
check("Ergebnis: pad_combo", erg == "pad_combo", erg)
check("nach der Haltezeit, nicht erst nach der Frist",
      dauer < 0.05 + I.InputManager.PAD_COMBO_HOLD + 0.5, "%.2f s" % dauer)

print()
print("Test 3b: GEGENPROBE - drei von vier")
erg = lauf(PRO, [(0.015, P, DREI)] * 40, frist=0.6)
check("kein Ausstieg", erg == "frist", erg)

print()
print("Test 3c: GEGENPROBE - dieselben Bytes von einem fremden Geraet")
erg = lauf({P: (0x054C, 0x09CC, "Wireless Controller")},
           [(0.015, P, ALLE_VIER)] * 40, frist=0.6)
check("kein Ausstieg", erg == "frist", erg)

print()
print("Test 3d: zwei Joy-Con")
JL, JR = "/dev/hidraw3", "/dev/hidraw4"
erg = lauf({JL: (0x057E, 0x2006, "Joy-Con (L)"),
            JR: (0x057E, 0x2007, "Joy-Con (R)")},
           [(0.015, JL, bericht(mitte=MINUS, links=L_)),
            (0.0, JR, bericht(rechts=R_, mitte=PLUS))] * 30)
check("links Minus+L, rechts Plus+R: pad_combo", erg == "pad_combo", erg)

print()
print("Test 3e: nur gestreift")
erg = lauf(PRO, [(0.015, P, ALLE_VIER)] * 3 + [(0.015, P, NICHTS)] * 30,
           frist=0.6)
check("kuerzer als die Haltezeit: kein Ausstieg", erg == "frist", erg)
check("die Haltezeit ist kurz", 0 < I.InputManager.PAD_COMBO_HOLD <= 0.5,
      I.InputManager.PAD_COMBO_HOLD)

# ---------------------------------------------------------------------------
print()
print("Test 4: run_core() behandelt es wie F1")
# ---------------------------------------------------------------------------
q = open(os.path.join(_REPO, "frontend", "frontend.py"),
         encoding="utf-8").read()
rc = nur_code(koerper(q, "run_core"))
check("pad_combo steht im selben Zweig wie hid_combo",
      '("combo", "hid_combo", "pad_combo")' in rc)

print()
if fails:
    print("ROT: %d Pruefung(en) fehlgeschlagen:" % len(fails))
    for f_ in fails:
        print("   - " + f_)
    sys.exit(1)
print("ALLES GRUEN")
