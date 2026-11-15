#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Warten im Dialog ist keine Arbeit - und "vorige Aktion" misst richtig (Build 325).

DER ANLASS steht im Log vom 15.11., beim Betreten einer Kategorie:

    RUCKLER: 956 ms busy (stream=224 haus=3 zeichnen=53 rest=676
    | ... vorige Aktion=ok Seite=1 Ansicht=liste)
    EINGABE-STAU: down lag 542 ms ungelesen beim Kernel (...;
    vorige Aktion: ok 4 ms)

Zwei Fehler in zwei Zeilen:

  1. "vorige Aktion: ok 4 ms" neben 956 ms. Gemessen wurde seit Build
     322 die Zeit fuer das LOGGEN der vorigen Aktion (der Stempel
     _rt_prev wird gesetzt, BEVOR sie verarbeitet wird) - nicht ihre
     Verarbeitung.
  2. Wartet waehrend einer Aktion ein Dialog auf den Nutzer (die
     Core-Auswahl beim Betreten einer Kategorie), lag diese Zeit in
     busy, im Rest, in der Zeichenzeit fuer die Wiederholrate und in
     der Latenz. Wie viel von rest=676 die Maschine war, stand nirgends.

GEPRUEFT WIRD - an der ECHTEN Hauptschleife run(), mit kuenstlicher Uhr:
  1. read_action() und read_raw_key() buchen ihre Zeit auf
     wartezeit_summe, auch wenn sie mit einer Ausnahme enden; die
     Lesewege ohne Warten (abholen, eingabe_anstehend) tun es nicht.
  2. Eine Aktion mit 200 ms Arbeit und 600 ms Dialog: RUCKLER meldet
     200 ms busy und nennt die 600 ms getrennt; die Wiederholrate
     bekommt 200 ms, die Latenz 200 ms.
  3. GEGENPROBE: ohne Dialog meldet dieselbe Arbeit dieselben 200 ms
     (es wird nur das Warten abgezogen, nicht mehr).
  4. EINGABE-STAU nennt die Verarbeitung der vorigen Aktion mit ihrer
     echten Dauer - 120 ms Zeichnen stehen dort als 120 ms.

Ausfuehren:
    python3 tools/test_dialog_wartezeit.py
"""
import os
import re
import sys

_HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HIER)

import _harness as H                                     # noqa: E402

fm = H.fm
import fe.input as FI                                    # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


print(__doc__.strip().split("\n")[0])
print()

# ---------------------------------------------------------------------------
print("Test 1: die Wartezeit wird gebucht - und nur dort, wo gewartet wird")
# ---------------------------------------------------------------------------


class Leser(object):
    pass


def _drei_zehntel(self, timeout=None):
    H.NOW[0] += 0.3
    return "ok"


def _und_kaputt(self, timeout=None):
    H.NOW[0] += 0.2
    raise OSError("Geraet weg")


L = Leser()
gebucht = FI._wartezeit_zaehlen(_drei_zehntel)
check("ein Aufruf: 0,3 s gebucht", gebucht(L) == "ok"
      and abs(L.wartezeit_summe - 0.3) < 1e-9, L.wartezeit_summe)
gebucht(L)
check("ein zweiter: es wird aufsummiert",
      abs(L.wartezeit_summe - 0.6) < 1e-9, L.wartezeit_summe)
try:
    FI._wartezeit_zaehlen(_und_kaputt)(L)
except OSError:
    pass
check("auch ein Ende mit Ausnahme wird gebucht",
      abs(L.wartezeit_summe - 0.8) < 1e-9, L.wartezeit_summe)
L2 = Leser()
_drei_zehntel(L2)
check("GEGENPROBE: ohne den Zaehler bucht nichts",
      getattr(L2, "wartezeit_summe", 0.0) == 0.0)

# Welche Lesewege gezaehlt werden - am Code-Objekt erkannt, nicht am
# Namen: jeder Wrapper aus _wartezeit_zaehlen() teilt dasselbe.
_code = FI._wartezeit_zaehlen(_drei_zehntel).__code__
for name in ("read_action", "read_raw_key"):
    fn = getattr(FI.InputManager, name)
    check("%s wird gezaehlt" % name, fn.__code__ is _code
          and fn.__name__ == name)
    check("%s laeuft weiterhin unter der Lesesperre" % name,
          hasattr(fn.__wrapped__, "__wrapped__"),
          "der Zaehler sitzt AUSSEN um die Sperre")
for name in ("abholen", "eingabe_anstehend", "flush", "rescan"):
    fn = getattr(FI.InputManager, name)
    check("%s wird NICHT gezaehlt (dort wartet niemand)" % name,
          fn.__code__ is not _code)
check("der Stand beginnt bei null", FI.InputManager.wartezeit_summe == 0.0)


# ---------------------------------------------------------------------------
# Die echte Hauptschleife, mit Drehbuch.
# ---------------------------------------------------------------------------
class _Ende(BaseException):
    """Beendet run() - BaseException, damit kein 'except Exception' in
    der Schleife es verschluckt."""


def hauptschleife(drehbuch, arbeit_beim_betreten, dialog_beim_betreten,
                  zeichnen_bei_down=0.0, leerlauf_zeichnen=0.0,
                  leerlauf_vsync=0.0):
    """run() mit einem Drehbuch laufen lassen. Jeder Eintrag ist
    (aktion, Leerlauf davor in s, eingabe_wartezeit in s). Liefert die
    Logzeilen, die Meldungen an die Wiederholrate und das Frontend."""
    H.set_screen(1280, 720)
    f = H.make_frontend(page=0)
    zeilen = []
    gemeldet = []
    f.play_boot_animation = lambda *a, **k: None
    f._show_max_level_boot_effect = lambda *a, **k: None
    # Der Ausstieg beendet den Prozess (os._exit) - hier nicht.
    f._beenden = lambda *a, **k: None
    f.inp.wache_starten = lambda *a, **k: None
    f.inp.zeichenzeit_melden = lambda act, dt: gemeldet.append((act, dt))

    def _dialog(self, timeout=None):
        H.NOW[0] += dialog_beim_betreten
        return "ok"
    # Der echte Zaehler um eine Attrappe des Lesens: so wartet ein
    # Dialog, ohne dass ein Geraet da sein muss.
    f.inp.read_action = FI._wartezeit_zaehlen(_dialog).__get__(f.inp)
    _echt_betreten = f._enter_category

    def _betreten():
        H.NOW[0] += arbeit_beim_betreten            # Maschinenarbeit
        if dialog_beim_betreten:
            f.inp.read_action()                     # die Core-Auswahl
        return _echt_betreten()
    f._enter_category = _betreten

    if zeichnen_bei_down:
        _echt_nav = f._draw_navigate_cats

        def _nav(*a, **k):
            H.NOW[0] += zeichnen_bei_down
            return _echt_nav(*a, **k)
        f._draw_navigate_cats = _nav

    rest = list(drehbuch)

    def _naechste():
        if not rest:
            raise _Ende()
        act, leerlauf, liegezeit = rest.pop(0)
        H.NOW[0] += leerlauf
        # Build 326: der Leerlauf zeichnet selbst (Nachzeichnen, Puls) -
        # das darf NICHT in der Zeile der vorigen Aktion landen.
        if leerlauf_zeichnen:
            f._perf_zeichnen = (getattr(f, "_perf_zeichnen", 0)
                                + leerlauf_zeichnen)
            f._perf_flip = getattr(f, "_perf_flip", 0) + leerlauf_zeichnen
        if leerlauf_vsync:
            f.fb._vsync_summe = (getattr(f.fb, "_vsync_summe", 0.0)
                                 + leerlauf_vsync)
        f.inp.eingabe_zeit = H.NOW[0]
        f.inp.eingabe_wartezeit = liegezeit
        return act
    f.next_action = _naechste

    alt_log = fm.LOG
    alt_wizard = fm.setup_wizard_done
    alt_update = fm.update_check_enabled
    alt_crt = fm.crt_pending_confirm
    fm.LOG = lambda msg, *a, **k: zeilen.append(str(msg))
    fm.setup_wizard_done = lambda: True
    fm.update_check_enabled = lambda: False
    fm.crt_pending_confirm = lambda: False
    try:
        f.run()
    except _Ende:
        pass
    finally:
        fm.LOG = alt_log
        fm.setup_wizard_done = alt_wizard
        fm.update_check_enabled = alt_update
        fm.crt_pending_confirm = alt_crt
    return zeilen, gemeldet, f


def zahl(muster, zeile):
    m = re.search(muster, zeile)
    return float(m.group(1)) if m else None


try:
    # -----------------------------------------------------------------------
    print()
    print("Test 2: 200 ms Arbeit und 600 ms Dialog beim Betreten")
    # -----------------------------------------------------------------------
    zeilen, gemeldet, f = hauptschleife(
        [("ok", 1.0, 0.0), ("down", 0.5, 0.0)],
        arbeit_beim_betreten=0.2, dialog_beim_betreten=0.6)
    ruckler = [z for z in zeilen if z.startswith("RUCKLER: ")]
    check("die Kategorie wurde betreten", f.page == 1, f.page)
    check("genau eine RUCKLER-Zeile", len(ruckler) == 1, ruckler)
    z = ruckler[0] if ruckler else ""
    check("busy sind die 200 ms Arbeit",
          zahl(r"RUCKLER: (\d+) ms busy", z) == 200, z[:70])
    check("das Warten steht getrennt daneben",
          zahl(r"im Dialog gewartet=(\d+)", z) == 600, z[-60:])
    check("und nicht im Rest", zahl(r"rest=(\d+)", z) == 200, z[:90])
    ok_meldung = [dt for act, dt in gemeldet if act == "ok"]
    check("die Wiederholrate bekommt die Arbeit, nicht das Warten",
          ok_meldung and abs(ok_meldung[0] - 0.2) < 1e-6, ok_meldung)
    check("die Latenz ebenso", abs(f._latenz_max - 0.2) < 1e-6,
          f._latenz_max)

    # -----------------------------------------------------------------------
    print()
    print("Test 3: GEGENPROBE - dieselbe Arbeit ohne Dialog")
    # -----------------------------------------------------------------------
    zeilen, gemeldet, f = hauptschleife(
        [("ok", 1.0, 0.0), ("down", 0.5, 0.0)],
        arbeit_beim_betreten=0.2, dialog_beim_betreten=0.0)
    ruckler = [z for z in zeilen if z.startswith("RUCKLER: ")]
    z = ruckler[0] if ruckler else ""
    check("auch hier 200 ms busy", zahl(r"RUCKLER: (\d+) ms busy", z) == 200,
          z[:70])
    check("und kein Warten", zahl(r"im Dialog gewartet=(\d+)", z) == 0,
          z[-60:])
    # Und die Probe, dass die Zahl ueberhaupt etwas abzieht: mit Dialog
    # waeren es ohne den Abzug 800 ms gewesen - sichtbar an der Latenz,
    # wenn man den Abzug weglaesst.
    f2 = H.make_frontend(page=0)
    f2._latenz_max = 0.0
    f2._latenz_buchen("ok", 100.0, 100.8, begonnen=100.0)
    check("GEGENPROBE Latenz: ohne Abzug stuenden 800 ms da",
          abs(f2._latenz_max - 0.8) < 1e-6, f2._latenz_max)
    f2._latenz_max = 0.0
    f2._latenz_buchen("ok", 100.0, 100.8, begonnen=100.0, gewartet=0.6)
    check("mit Abzug 200 ms", abs(f2._latenz_max - 0.2) < 1e-6,
          f2._latenz_max)

    # -----------------------------------------------------------------------
    print()
    print("Test 3b: Zeichnen im Leerlauf gehoert nicht zur vorigen Aktion "
          "(Build 326)")
    # -----------------------------------------------------------------------
    # Im Log vom 15.11.: "flip=20 (davon vsync=138)", "flip=0 (davon
    # vsync=423)", "zeichnen=230" bei 206 ms busy.
    zeilen, gemeldet, f = hauptschleife(
        [("ok", 1.0, 0.0), ("down", 0.5, 0.0)],
        arbeit_beim_betreten=0.2, dialog_beim_betreten=0.0,
        leerlauf_zeichnen=0.3, leerlauf_vsync=0.4)
    ruckler = [z for z in zeilen if z.startswith("RUCKLER: ")]
    z = ruckler[0] if ruckler else ""
    check("zeichnen enthaelt nicht die 300 ms aus dem Leerlauf",
          (zahl(r"zeichnen=(\d+)", z) or 0) < 300, z[:90])
    check("flip ebenso", (zahl(r"flip=(\d+)", z) or 0) < 300, z)
    check("vsync enthaelt nicht die 400 ms aus dem Leerlauf",
          (zahl(r"vsync=(\d+)", z) or 0) < 400, z)
    check("busy bleibt bei der Arbeit",
          zahl(r"RUCKLER: (\d+) ms busy", z) == 200, z[:60])
    check("und der Rest geht auf (busy - zeichnen)",
          zahl(r"rest=(\d+)", z) == 200 - (zahl(r"zeichnen=(\d+)", z) or 0)
          - (zahl(r"haus=(\d+)", z) or 0), z[:90])

    # -----------------------------------------------------------------------
    print()
    print("Test 4: EINGABE-STAU nennt die echte Dauer der vorigen Aktion")
    # -----------------------------------------------------------------------
    zeilen, gemeldet, f = hauptschleife(
        [("down", 1.0, 0.0), ("down", 0.0, 0.3)],
        arbeit_beim_betreten=0.0, dialog_beim_betreten=0.0,
        zeichnen_bei_down=0.12)
    stau = [z for z in zeilen if z.startswith("EINGABE-STAU: ")]
    check("eine Stau-Zeile", len(stau) == 1, stau)
    z = stau[0] if stau else ""
    check("die vorige Aktion stand 120 ms an",
          zahl(r"vorige Aktion: down (\d+) ms", z) == 120, z)
    check("ohne Dialog kein Zusatz", "im Dialog" not in z, z)

    zeilen, gemeldet, f = hauptschleife(
        [("ok", 1.0, 0.0), ("down", 0.0, 0.3)],
        arbeit_beim_betreten=0.2, dialog_beim_betreten=0.6)
    stau = [z for z in zeilen if z.startswith("EINGABE-STAU: ")]
    z = stau[0] if stau else ""
    check("nach dem Dialog: die Arbeit", zahl(r"vorige Aktion: ok (\d+) ms",
                                              z) == 200, z)
    check("und das Warten getrennt",
          zahl(r"dazu (\d+) ms im Dialog gewartet", z) == 600, z)
    check("der alte Merker ist weg",
          not hasattr(f, "_verarbeitung_vorher"),
          "er mass das Loggen statt der Verarbeitung")
finally:
    H._zwischenspeicher_leeren()

print()
if fails:
    print("ROT: %d Pruefung(en) fehlgeschlagen:" % len(fails))
    for f_ in fails:
        print("   - " + f_)
    sys.exit(1)
print("ALLES GRUEN")
