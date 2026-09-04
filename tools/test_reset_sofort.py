#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft die beiden SOFORT ausloesenden Tasten waehrend eines Spiels:
F5 (Reset im Core, Build 75) und F1 (Ausstieg zum Frontend, Build 77).

NUTZERWUNSCH: "F5-Reset-Funktion haette ich gerne auf sofortigen
Tastendruck, wenn das geht."

Vorher lagen drei Verzoegerungen hintereinander:

  1. RESET_HOLD = 0,6 s Haltezeit
  2. bis zu 0,2 s, weil die Haltezeit erst am ANFANG der naechsten
     Schleifenrunde geprueft wurde - und die Schleife wartet in
     select(..., 0.2)
  3. 0,2 s beim Anlegen des virtuellen Tastatur-Geraets, das bei JEDEM
     Reset neu erzeugt wurde

Macht bis zu 1,0 s. Uebrig bleibt jetzt die Tastendruckdauer von 0,1 s,
die der Empfaenger braucht, um den Druck ueberhaupt zu sehen.

EHRLICH BENANNTES RISIKO, hier mitgeprueft: ohne Haltezeit ist ein
versehentlicher F5-Antipper waehrend des Spielens sofort ein Reset.
Was dagegen NICHT passieren darf, ist ein Dauerfeuer durch blosses
Halten - dafuer gibt es reset_gefeuert, und Test 3 nagelt das fest.

NUTZERWUNSCH ZU F1 (Build 77): "Esc-Funktion haette ich dann gerne auf
F1, und die soll so schnell ausloesen wie die F5-Reset-Funktion." Dazu:
"F10 kann auch komplett raus, funktioniert genauso wenig." Beim Umbau
kam heraus, WARUM F10 nie ausgeloest hat - die HID-Pruefung verglich
0x44, und das ist im HID-Standard F11, nicht F10 (0x43).

Ausfuehren:
    python3 tools/test_reset_sofort.py
"""
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
_FRONTEND_DIR = os.path.dirname(
    os.environ.get("FRONTEND_PY",
                   os.path.join(_REPO, "frontend", "frontend.py")))
sys.path.insert(0, _FRONTEND_DIR)

import fe.reset_trigger as R                         # noqa: E402
import fe.input as I                                 # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


print("Test 1: keine Haltezeit mehr")
check("RESET_HOLD ist 0", I.InputManager.RESET_HOLD == 0,
      str(I.InputManager.RESET_HOLD))
# Die Haltezeit allein wegzunehmen haette NICHT gereicht: geprueft wird
# sie am Anfang der Schleife, und die wartet vorher in select(...,0.2).
# Ausgeloest werden muss deshalb DORT, wo die Taste erkannt wird.
quelle = open(os.path.join(_FRONTEND_DIR, "fe", "input.py"),
              encoding="utf-8").read()
block = quelle.split("reset_since = time.monotonic()")[-1][:1600]
check("ausgeloest wird direkt beim Erkennen der Taste",
      "if self.RESET_HOLD <= 0:" in block and "send_reset_combo()" in block)
check("es gibt eine Sperre gegen Dauerfeuer beim Halten",
      "reset_gefeuert" in quelle)
check("und sie wird beim Loslassen wieder aufgehoben",
      "reset_gefeuert = False" in quelle)

print()
print("Test 2: das virtuelle Geraet wird nur EINMAL angelegt")
# Das war der zweitgroesste Posten: 0,2 s Wartezeit nach dem Anlegen,
# damit der Kernel das Geraet bekannt macht - frueher bei jedem Reset.
angelegt = []
geschrieben = []
geschlossen = []


class FakeFcntl:
    @staticmethod
    def ioctl(fd, req, arg=0):
        if req == R.UI_DEV_CREATE:
            angelegt.append(fd)
        elif req == R.UI_DEV_DESTROY:
            geschlossen.append(fd)
        return 0


_echt = (R.os.open, R.os.write, R.os.close, R.fcntl, R.time.sleep)
R.os.open = lambda *a, **k: 4242
R.os.write = lambda fd, b: geschrieben.append(b) or len(b)
R.os.close = lambda fd: None
R.fcntl = FakeFcntl
schlafzeiten = []
R.time.sleep = lambda s: schlafzeiten.append(s)
try:
    R._geraet_fd = None
    check("erster Aufruf meldet Erfolg", R.send_reset_combo() is True)
    check("dabei wurde genau EIN Geraet angelegt", len(angelegt) == 1,
          str(angelegt))
    schlaf_erster = sum(schlafzeiten)
    schlafzeiten.clear()
    check("zweiter Aufruf meldet Erfolg", R.send_reset_combo() is True)
    check("und legt KEIN zweites Geraet an", len(angelegt) == 1,
          str(angelegt))
    schlaf_zweiter = sum(schlafzeiten)
    check("der zweite Aufruf wartet nicht mehr auf das Anlegen",
          schlaf_zweiter < schlaf_erster,
          "erster %.2fs, zweiter %.2fs" % (schlaf_erster, schlaf_zweiter))
    check("uebrig bleibt nur die Tastendruckdauer",
          abs(schlaf_zweiter - 0.1) < 0.001, "%.3fs" % schlaf_zweiter)

    print()
    print("Test 2b: es werden Druck UND Loslassen aller drei Tasten gesendet")
    # Bleibt eine Taste "gedrueckt", haengt die Kombination im System
    # fest und der naechste Reset kaeme nie an.
    ereignisse = []
    import struct as _struct
    for b in geschrieben[-8:]:
        if len(b) == _struct.calcsize(R._EVENT_FMT):
            _s, _us, typ, code, wert = _struct.unpack(R._EVENT_FMT, b)
            ereignisse.append((typ, code, wert))
    tasten = (R.KEY_LEFTCTRL, R.KEY_LEFTALT, R.KEY_RIGHTALT)
    gedrueckt = [c for typ, c, w in ereignisse if typ == R.EV_KEY and w == 1]
    losgelassen = [c for typ, c, w in ereignisse if typ == R.EV_KEY and w == 0]
    check("alle drei Tasten gedrueckt", sorted(gedrueckt) == sorted(tasten),
          str(gedrueckt))
    check("alle drei Tasten wieder losgelassen",
          sorted(losgelassen) == sorted(tasten), str(losgelassen))

    print()
    print("Test 2c: nach einem Schreibfehler wird das Geraet neu angelegt")
    # Sonst haetten wir uns mit dem dauerhaft offenen Geraet ein
    # Dauerproblem eingehandelt: waere es einmal kaputt (z.B. weil das
    # uinput-Modul entladen wurde), wuerde nie wieder ein Reset gehen.
    def _kaputt(fd, b):
        raise OSError("Test: Schreiben schlaegt fehl")

    R.os.write = _kaputt
    check("der Fehlschlag wird gemeldet", R.send_reset_combo() is False)
    check("das kaputte Geraet wurde geschlossen", len(geschlossen) >= 1,
          str(geschlossen))
    R.os.write = lambda fd, b: geschrieben.append(b) or len(b)
    check("der naechste Aufruf legt ein neues Geraet an",
          R.send_reset_combo() is True and len(angelegt) == 2,
          str(angelegt))
finally:
    R.os.open, R.os.write, R.os.close, R.fcntl, R.time.sleep = _echt
    R._geraet_fd = None

print()
print("Test 3: Halten loest nur EINMAL aus")
# Nachgebaut wird genau die Zustandsfolge aus wait_game_exit():
# Bericht mit gesetztem F5-Bit -> ausloesen; weitere Berichte mit
# weiterhin gesetztem Bit -> nichts; Bericht ohne Bit (losgelassen);
# Bericht mit Bit -> wieder ausloesen.
ausloesungen = []
reset_since = None
reset_gefeuert = False
RESET_HOLD = I.InputManager.RESET_HOLD

for gehalten in (True, True, True, True, False, False, True, True):
    if gehalten and reset_since is None and not reset_gefeuert:
        reset_since = time.monotonic()
        if RESET_HOLD <= 0:
            ausloesungen.append("reset")
            reset_since = None
            reset_gefeuert = True
    elif not gehalten:
        reset_since = None
        reset_gefeuert = False

check("vier Berichte mit gehaltener Taste ergeben EINEN Reset",
      ausloesungen[:1] == ["reset"], str(ausloesungen))
check("nach Loslassen und erneutem Druecken kommt ein zweiter",
      len(ausloesungen) == 2, str(ausloesungen))

print()
print("Test 4: F1 steigt SOFORT aus dem laufenden Core aus")
import fe.hidraw as HR                                # noqa: E402

# HID-Usages: F1 = 0x3A, F5 = 0x3E, Esc = 0x29, F10 = 0x43, F11 = 0x44.
def bericht(*usages):
    """Ein einfacher 8-Byte-Tastaturbericht (Boot-Protokoll)."""
    b = bytearray(8)
    for i, u in enumerate(usages[:6]):
        b[2 + i] = u
    return bytes(b)


check("F1 wird erkannt", HR._hid_report_has_f1_key(bericht(0x3A)))
check("eine andere Taste nicht", not HR._hid_report_has_f1_key(bericht(0x3E)))
check("ein leerer Bericht nicht", not HR._hid_report_has_f1_key(bericht()))
check("F1 zaehlt NICHT als Esc-Ausstieg (getrennte Wege)",
      not HR._hid_report_has_exit_key(bericht(0x3A)))
check("Esc weiterhin als Esc-Ausstieg", HR._hid_report_has_exit_key(bericht(0x29)))

print()
print("Test 4b: NKRO-Bitmap - dieselbe Formel wie bei Esc und F5")
# Bitmap-Byte = Usage // 8, Report-Byte = Bitmap-Byte + 2, Bit = Usage % 8.
# F5 (0x3E) landet danach in Byte 9, Bit 6 - genau das hat der Nutzer auf
# echter Hardware bestaetigt. F1 (0x3A) liegt im SELBEN Byte, Bit 2.
def nkro(usage):
    b = bytearray(12)
    b[0] = 0x06
    b[2 + usage // 8] |= 1 << (usage % 8)
    return bytes(b)


check("F1 im NKRO-Bericht erkannt", HR._hid_report_has_f1_key(nkro(0x3A)))
check("F5 im NKRO-Bericht erkannt", HR._hid_report_has_reset_key(nkro(0x3E)))
check("Esc im NKRO-Bericht erkannt", HR._hid_report_has_exit_key(nkro(0x29)))
check("F1 und F5 liegen im selben Byte, aber auf verschiedenen Bits",
      not HR._hid_report_has_f1_key(nkro(0x3E))
      and not HR._hid_report_has_reset_key(nkro(0x3A)))

print()
print("Test 5: F10 ist ueberall raus - und war ohnehin die falsche Taste")
# 0x44 ist F11, nicht F10 (0x43). Die alte Pruefung haette also bei
# einem F11-Druck im Spiel den Ausstieg ausgeloest und bei F10 nie.
check("F10 (0x43) loest keinen Ausstieg mehr aus",
      not HR._hid_report_has_exit_key(bericht(0x43)))
check("F11 (0x44) ebenfalls nicht - genau der alte Fehlgriff",
      not HR._hid_report_has_exit_key(bericht(0x44)))
# Bewusst die TATSAECHLICHE Tabelle pruefen, nicht den Dateitext - der
# enthaelt die alte Belegung noch als Kommentar, und genau so soll es
# sein (dort steht, warum sie weg ist).
check("F10 ist nicht mehr in der KEYMAP",
      I.KEY_F10 not in I.KEYMAP, str(I.KEYMAP.get(I.KEY_F10)))
# F1 taucht bewusst NICHT in der KEYMAP auf: die evdev-Ebene ist
# waehrend eines laufenden Cores gesperrt (genau der Grund, warum F10
# dort nie ankam). F1 laeuft ausschliesslich ueber die HID-Ebene.
check("F1 (evdev 59) steht bewusst NICHT in der KEYMAP",
      59 not in I.KEYMAP, str(I.KEYMAP.get(59)))
input_py = open(os.path.join(_FRONTEND_DIR, "fe", "input.py"),
                encoding="utf-8").read()
check("und die evdev-Abfrage ist weg",
      "if etype == EV_KEY and code == KEY_F10" not in input_py)
fe_py = open(os.path.join(_FRONTEND_DIR, "frontend.py"), encoding="utf-8").read()
check('das Ergebnis "f10" wird nicht mehr behandelt',
      'res in ("combo", "hid_combo")' in fe_py)

print()
print("Test 6: der F4-Schnellstart ist restlos entfernt")
# NUTZERWUNSCH (Build 77): "F4 kann raus komplett, auch der Schalter
# unter System, weil die Funktion ja nicht geht."
import fe.settings as S4                              # noqa: E402
for name in ("toggle_f4_hotkey", "f4_hotkey_enabled", "f4_selbstheilung",
             "f4_boot_entry_ok", "F4_HOTKEY_FLAG"):
    check("fe.settings hat kein %s mehr" % name, not hasattr(S4, name))
for datei in ("f4_hotkey.py", "f4_hotkey.sh"):
    check("%s ist geloescht" % datei,
          not os.path.exists(os.path.join(_FRONTEND_DIR, datei)))
menu_py = open(os.path.join(_FRONTEND_DIR, "fe", "menu.py"),
               encoding="utf-8").read()
check("der Menuepunkt ist raus", '"f4_hotkey"' not in menu_py)
check("und der Handler in frontend.py auch",
      'kind == "f4_hotkey"' not in fe_py)
import fe.translations as T4                          # noqa: E402
tab4 = getattr(T4, "TRANSLATIONS", {})
check("keine F4-Uebersetzungen mehr uebrig",
      not [k for k in tab4 if "f4" in k.lower()],
      str([k for k in tab4 if "f4" in k.lower()]))

print()
print("Test 6b: die Skripte raeumen alte Installationen aktiv auf")
# Das ist der Teil, der leicht vergessen wird: wer den Schnellstart je
# installiert hatte, hat eine Startzeile in user-startup.sh. Bleibt sie
# stehen, versucht der MiSTer bei JEDEM Boot eine geloeschte Datei zu
# starten. Bestehende Installationen laufen nur ueber Frontend_Update.sh.
_SCRIPTS = os.path.join(_REPO, "Scripts")
for skript in ("Frontend_Update.sh", "Frontend_Install.sh",
               "Frontend_Install_Remote.sh", "Frontend_Install_Offline.sh"):
    txt = open(os.path.join(_SCRIPTS, skript), encoding="utf-8").read()
    check("%s traegt NICHTS mehr ein" % skript,
          "printf '%s\\n' \"$F4_LINE\"" not in txt
          and '/media/fat/frontend/f4_hotkey.sh &" >>' not in txt)
    check("%s entfernt die alte Zeile" % skript,
          'grep -v "f4_hotkey.sh"' in txt)
    check("%s loescht die alten Dateien" % skript,
          "f4_hotkey.py" in txt and "rm -f" in txt)

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for f in fails:
        print("   ", f)
    sys.exit(1)
print("Alle Tests bestanden.")
