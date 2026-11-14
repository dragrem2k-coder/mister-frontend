#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ein Bewegungssensor ist kein Eingabegeraet (Build 320).

DER ANLASS: "ausserdem moechte ich das die joypad eingabe sofort
erkannt und angenommen wird".

Sein Bench vom 13.11. zeigt in Abschnitt L zwei offene Geraete: event3
mit 320 Meldungen je Sekunde und event4 mit 5150. Das zweite ist mit
grosser Wahrscheinlichkeit der Bewegungssensor des Pads (200 Messungen
je Sekunde, je Messung ein Buendel aus Achsen, Zeitstempel und
Abschluss) - und jede einzelne Meldung wurde gelesen, zerlegt und
uebersetzt, auf dem Faden, der auch zeichnet.

Seit Build 320 wird so ein Geraet gar nicht erst geoeffnet.

WAS DIESER TEST SICHERT:
  1. die Regel an echten Abschnitten aus /proc/bus/input/devices: das
     Pad bleibt, sein Sensor geht - ueber das PROP-Bit, ueber die
     fehlende KEY-Zeile und ueber den Namen, jedes fuer sich,
  2. EINE TASTATUR BLEIBT IMMER, egal was sonst im Abschnitt steht,
  3. scan_devices() wendet genau diese Regel an, fuehrt Buch ueber
     das Uebersprungene und vergisst es beim naechsten Blick wieder,
  4. der InputManager oeffnet den Sensor nicht - und meldet ihn
     einmal im Log, nicht bei jedem Blick,
  5. die Gegenprobe: ohne die Regel wird der Sensor geoeffnet,
  6. der Bench nennt den NAMEN jedes offenen Geraets und die Liste
     der uebersprungenen - damit aus dem Schluss eine Beobachtung
     wird.

Ausfuehren:
    python3 tools/test_eingabegeraete.py
"""
import builtins
import io
import os
import sys

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
sys.path.insert(0, _HIER)

import _harness as H                                     # noqa: E402

import fe.input as I                                     # noqa: E402
from _quelle import koerper                              # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


print(__doc__.strip().split("\n")[0])
print()

# Abschnitte, wie sie der Kernel schreibt. Die ersten beiden sind das
# Paar, das hid-nintendo fuer EIN Pad anlegt.
PAD = """I: Bus=0005 Vendor=057e Product=2009 Version=8001
N: Name="Nintendo Switch Pro Controller"
P: Phys=aa:bb:cc:dd:ee:ff
S: Sysfs=/devices/virtual/misc/uhid/0005:057E:2009.0003/input/input7
U: Uniq=11:22:33:44:55:66
H: Handlers=event3 js0
B: PROP=0
B: EV=20001b
B: KEY=ffff0000 0 0 0 0 0 0 0 0 0
B: ABS=3001b
B: MSC=10
B: FF=1 7030000 0 0"""

SENSOR = """I: Bus=0005 Vendor=057e Product=2009 Version=8001
N: Name="Nintendo Switch Pro Controller IMU"
P: Phys=aa:bb:cc:dd:ee:ff
S: Sysfs=/devices/virtual/misc/uhid/0005:057E:2009.0003/input/input8
U: Uniq=11:22:33:44:55:66
H: Handlers=event4
B: PROP=40
B: EV=19
B: ABS=3f
B: MSC=20"""

# Aelterer Treiber: kein PROP-Bit, aber auch keine Tasten.
SENSOR_OHNE_PROP = """I: Bus=0003 Vendor=054c Product=09cc Version=8111
N: Name="Sony Interactive Entertainment Wireless Controller Motion Sensors"
H: Handlers=event6
B: PROP=0
B: EV=19
B: ABS=3f
B: MSC=20"""

# Ein Treiber, der dem Sensor versehentlich eine Taste mitgibt und
# das PROP-Bit vergisst: dann haelt nur noch der Name.
SENSOR_MIT_TASTE = """I: Bus=0003 Vendor=1234 Product=5678 Version=0111
N: Name="Irgendein Pad Gyro"
H: Handlers=event9
B: PROP=0
B: EV=1b
B: KEY=1 0 0 0 0 0
B: ABS=3f"""

TASTATUR = """I: Bus=0003 Vendor=046d Product=c31c Version=0110
N: Name="Logitech USB Keyboard"
H: Handlers=sysrq kbd event0 leds
B: PROP=0
B: EV=120013
B: KEY=1000000000007 ff9f207ac14057ff febeffdfffefffff fffffffffffffffe
B: MSC=10
B: LED=7"""

# Die boeseste Tastatur, die man sich ausdenken kann: PROP-Bit
# gesetzt, keine KEY-Zeile, "Gyro" im Namen. Sie muss trotzdem bleiben.
TASTATUR_SCHRAEG = """I: Bus=0003 Vendor=1111 Product=2222 Version=0110
N: Name="Gyro Accelerometer IMU Keyboard"
H: Handlers=sysrq kbd event1
B: PROP=40
B: EV=120013"""

ACHTBITDO = """I: Bus=0003 Vendor=2dc8 Product=3106 Version=0114
N: Name="8BitDo Ultimate 2C Wireless Controller"
H: Handlers=event5 js1
B: PROP=0
B: EV=20000b
B: KEY=7cdb000000000000 0 0 0 0
B: ABS=3003f
B: FF=107030000 0"""

# "Gyro" als Teil eines Wortes ist kein Sensor.
GYROTECH = """I: Bus=0003 Vendor=9999 Product=0001 Version=0110
N: Name="Gyrotech Arcade Stick"
H: Handlers=event7 js2
B: PROP=0
B: EV=1b
B: KEY=fff 0 0 0 0
B: ABS=3"""

VIRTUELL = """I: Bus=0000 Vendor=0000 Product=0000 Version=0000
N: Name="MiSTer virtual input"
H: Handlers=sysrq kbd event2
B: PROP=0
B: EV=3
B: KEY=ffffffff"""

g = I.geraet_grund_zum_ueberspringen

# ---------------------------------------------------------------------------
print("Test 1: die Regel an echten Abschnitten")
# ---------------------------------------------------------------------------
check("das Pad bleibt", g(PAD) is None, g(PAD))
check("der Sensor geht - PROP-Bit 6", g(SENSOR) == "Bewegungssensor",
      g(SENSOR))
check("ohne PROP-Bit: keine Tasten", g(SENSOR_OHNE_PROP) == "keine Tasten",
      g(SENSOR_OHNE_PROP))
check("mit Taste und ohne PROP-Bit: der Name",
      g(SENSOR_MIT_TASTE) == "Bewegungssensor (Name)", g(SENSOR_MIT_TASTE))
check("ein 8BitDo bleibt", g(ACHTBITDO) is None, g(ACHTBITDO))
check("'Gyrotech' ist kein Sensor (ganzes Wort verlangt)",
      g(GYROTECH) is None, g(GYROTECH))
check("das PROP-Bit ist das sechste (INPUT_PROP_ACCELEROMETER)",
      I.INPUT_PROP_ACCELEROMETER == 6)
# Mehrere Woerter: das niederwertigste steht hinten.
check("PROP mit zwei Woertern: das hintere zaehlt",
      g(PAD.replace("B: PROP=0", "B: PROP=0 40")) == "Bewegungssensor"
      and g(PAD.replace("B: PROP=0", "B: PROP=40 0")) is None)
# Ein Zeigegeraet (Touchpad am Pad, PROP=5) ist kein Sensor.
check("PROP=5 (Zeigegeraet) wird nicht verwechselt",
      g(PAD.replace("B: PROP=0", "B: PROP=5")) is None)

# ---------------------------------------------------------------------------
print()
print("Test 2: eine Tastatur bleibt immer")
# ---------------------------------------------------------------------------
check("die gewoehnliche Tastatur bleibt", g(TASTATUR) is None)
check("auch eine mit PROP-Bit, ohne KEY-Zeile und 'Gyro' im Namen",
      g(TASTATUR_SCHRAEG) is None, g(TASTATUR_SCHRAEG))
_k = koerper(open(os.path.join(_REPO, "frontend", "fe", "input.py"),
                  encoding="utf-8").read(),
             "geraet_grund_zum_ueberspringen")
check("die Tastatur wird ZUERST geprueft, vor jedem Ausschluss",
      0 < _k.find('"kbd" in block') < _k.find("PROP="))

# ---------------------------------------------------------------------------
print()
print("Test 3: scan_devices() wendet die Regel an")
# ---------------------------------------------------------------------------
_echt_open = builtins.open
_inhalt = [""]


def _open(pfad, *a, **k):
    if pfad == "/proc/bus/input/devices":
        return io.StringIO(_inhalt[0])
    return _echt_open(pfad, *a, **k)


ALLE = "\n\n".join((TASTATUR, VIRTUELL, PAD, SENSOR, ACHTBITDO,
                    SENSOR_OHNE_PROP, SENSOR_MIT_TASTE, TASTATUR_SCHRAEG))
builtins.open = _open
try:
    _inhalt[0] = ALLE + "\n"
    devs = I.scan_devices()
    weg = list(I.UEBERSPRUNGEN)
    _inhalt[0] = "\n\n".join((TASTATUR, PAD)) + "\n"
    devs2 = I.scan_devices()
    weg2 = list(I.UEBERSPRUNGEN)
finally:
    builtins.open = _echt_open

pfade = [d[0] for d in devs]
check("geoeffnet werden Tastatur, Pad, 8BitDo und die schraege Tastatur",
      pfade == ["/dev/input/event0", "/dev/input/event3",
                "/dev/input/event5", "/dev/input/event1"], pfade)
check("die Tastaturen sind als Tastatur markiert, die Pads nicht",
      [d[2] for d in devs] == [True, False, False, True])
check("uebersprungen: die drei Sensoren, mit Pfad, Name und Grund",
      [(w[0], w[2]) for w in weg]
      == [("/dev/input/event4", "Bewegungssensor"),
          ("/dev/input/event6", "keine Tasten"),
          ("/dev/input/event9", "Bewegungssensor (Name)")], weg)
check("der Name steht dabei",
      weg and weg[0][1] == "Nintendo Switch Pro Controller IMU")
check("MiSTers virtuelles Geraet steht in KEINER der beiden Listen",
      "/dev/input/event2" not in pfade
      and all(w[0] != "/dev/input/event2" for w in weg))
check("beim naechsten Blick ist die Liste neu, nicht verlaengert",
      weg2 == [] and [d[0] for d in devs2]
      == ["/dev/input/event0", "/dev/input/event3"], weg2)

# ---------------------------------------------------------------------------
print()
print("Test 4: der InputManager oeffnet den Sensor nicht")
# ---------------------------------------------------------------------------


class _Geraet(object):
    geoeffnet = []

    def __init__(self, path, name, is_kbd):
        self.path, self.name, self.is_kbd = path, name, is_kbd
        self.fd = -1
        self.axis = {}
        _Geraet.geoeffnet.append(path)

    def grab(self, _an):
        pass

    def close(self):
        pass


def _manager_blick(inhalt, mgr=None, regel=None):
    """Einen rescan() gegen einen gestellten Geraetebestand fahren.
    Rueckgabe: (Manager, geoeffnete Pfade, Logzeilen)."""
    zeilen = []
    echt_dev, echt_log = I.Device, I.LOG
    echt_stat, echt_regel = I.os.stat, I.geraet_grund_zum_ueberspringen
    _Geraet.geoeffnet = []
    I.Device = _Geraet
    I.LOG = zeilen.append
    if regel is not None:
        I.geraet_grund_zum_ueberspringen = regel
    builtins.open = _open
    _inhalt[0] = inhalt
    try:
        if mgr is None:
            mgr = I.InputManager.__new__(I.InputManager)
            mgr.devices = {}
            mgr.want_grab = False
            mgr._last_input_mtime = -1.0
            mgr.last_scan = 0.0
            mgr._select_down = {}
            mgr._select_kombiniert = False
        mgr.rescan(force=True)
    finally:
        builtins.open = _echt_open
        I.Device, I.LOG = echt_dev, echt_log
        I.os.stat = echt_stat
        I.geraet_grund_zum_ueberspringen = echt_regel
    return mgr, list(_Geraet.geoeffnet), zeilen


BESTAND = "\n\n".join((TASTATUR, PAD, SENSOR)) + "\n"
try:
    m, auf, log = _manager_blick(BESTAND)
    fehler = None
except Exception as e:                                   # noqa: BLE001
    m, auf, log, fehler = None, [], [], "%s: %s" % (type(e).__name__, e)
check("rescan() laeuft durch", fehler is None, fehler)
check("geoeffnet: Tastatur und Pad", sorted(auf)
      == ["/dev/input/event0", "/dev/input/event3"], auf)
check("der Sensor ist NICHT unter den offenen Geraeten",
      m is not None and "/dev/input/event4" not in m.devices)
_meld = [z for z in log if "uebersprungen" in z]
check("im Log steht er einmal, mit Name und Grund",
      len(_meld) == 1 and "event4" in _meld[0] and "IMU" in _meld[0]
      and "Bewegungssensor" in _meld[0], _meld)
if m is not None:
    _m2, auf2, log2 = _manager_blick(BESTAND, mgr=m)
    check("beim zweiten Blick wird nichts noch einmal geoeffnet",
          auf2 == [], auf2)
    check("und der Sensor NICHT noch einmal gemeldet",
          not [z for z in log2 if "uebersprungen" in z], log2)

# ---------------------------------------------------------------------------
print()
print("Test 5: Gegenprobe - ohne die Regel wird der Sensor geoeffnet")
# ---------------------------------------------------------------------------
_m3, auf3, _l3 = _manager_blick(BESTAND, regel=lambda _b: None)
check("mit abgeschalteter Regel ist event4 dabei - der Test kann rot "
      "werden", "/dev/input/event4" in auf3, auf3)

# ---------------------------------------------------------------------------
print()
print("Test 6: der Bench nennt Namen und Uebersprungenes")
# ---------------------------------------------------------------------------
_QB = open(os.path.join(_REPO, "frontend", "fe", "bench.py"),
           encoding="utf-8").read()
_kl = koerper(_QB, "_abschnitt_l")
check("Abschnitt L schreibt den Namen jedes offenen Geraets",
      'getattr(d, "name", "?")' in _kl)
check("Abschnitt L liest die Liste der uebersprungenen aus fe.input",
      "UEBERSPRUNGEN" in _kl and "Uebersprungene Geraete" in _kl)
check("die Bench-Nummer ist mitgewachsen", __import__(
    "fe.bench", fromlist=["x"]).BENCH_VERSION >= 21)

print()
if fails:
    print("ROT: %d Pruefung(en) fehlgeschlagen:" % len(fails))
    for f_ in fails:
        print("   - " + f_)
    sys.exit(1)
print("ALLES GRUEN")
