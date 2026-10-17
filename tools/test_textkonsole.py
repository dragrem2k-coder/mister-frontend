#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Der Grafikmodus der Textkonsole (Build 279).

NUTZERMELDUNG, zum vierten Mal zu derselben Sache: "was mir immer noch
auffaellt das nach ein paar sekunden mit dem neuen kernel immer nochmal
der login prompt aufblitzt."

Alle bisherigen Mittel sind BITTEN: nicht abdunkeln (Build 160), kein
Cursor (158), kein VESA-Abschalten, und hinterher der Rueckleser, der
nachsieht, ob sich die Konsole daran gehalten hat. Der Grafikmodus ist
keine Bitte - er nimmt der Textkonsole die Moeglichkeit, auf tty1
ueberhaupt zu zeichnen.

WAS DIESER TEST VOR ALLEM SICHERT, ist nicht das Anschalten, sondern
das ZURUECKSTELLEN. Bleibt der Grafikmodus stehen, zeigt tty1 keinen
Text mehr, und ein Script aus MiSTers OSD laeuft unsichtbar - also
genau der Fehler, den Build 278 behoben hat, nur eine Ebene tiefer.
Deshalb gibt es drei Rueckstellungen und einen Schalter, und deshalb
steht hier zu jeder eine Pruefung.

Ausfuehren:
    python3 tools/test_textkonsole.py
"""
import io
import os
import sys
import tempfile
import shutil

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
sys.path.insert(0, _HIER)

import _harness as H                                      # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


_q = io.open(H.FRONTEND_PY, encoding="utf-8").read()

# ---------------------------------------------------------------------------
print("Teil 1: die Zusagen im Quelltext")
# ---------------------------------------------------------------------------
check("der Grafikmodus wird beim Start gesetzt",
      "self.textkonsole_grafik_an()" in _q
      and "self.konsole_ruhig_stellen()" in _q,
      "neben die bisherigen Mittel, nicht an ihre Stelle")

# DIE DREI RUECKSTELLUNGEN. Jede deckt einen anderen Fall ab, und keine
# davon deckt die der anderen mit ab.
_beenden = _q.split("def _beenden")[1].split("\n    def ")[0]
check("1. der normale Ausstieg stellt zurueck",
      "self.textkonsole_grafik_aus()" in _beenden)
check("   und zwar bevor der Bildschirm MiSTer gehoert",
      _beenden.index("textkonsole_grafik_aus")
      < _beenden.index("self.fb.close()"),
      "danach wird die Konsole nicht mehr angefasst (Build 165/166)")
_wache = _q.split("def _notausgang_stellen")[1].split("\n    def ")[0]
check("2. der harte Abbruch stellt zurueck",
      "Frontend.textkonsole_grafik_aus()" in _wache,
      "hier endet der Prozess per os._exit() - _beenden() laeuft dann "
      "nie")
check("3. und das finally in main, fuer den Absturz mitten im Betrieb",
      "Frontend.textkonsole_grafik_aus()" in
      _q.split("release_single_instance()")[-2][-900:],
      "dort, wo weder _beenden() noch der Wachhund greift")

# DIE UEBERGABE. Ein Script, dessen Ausgabe niemand sehen kann, ist
# nutzlos - und genau diese Konsole uebergeben wir.
_konsole = _q.split("def _auf_konsole")[1].split("\n    def ")[0]
check("bei der Uebergabe an ein fremdes Programm geht er aus",
      "self.textkonsole_grafik_aus()" in _konsole,
      "sonst laeuft ein Script unsichtbar - der Fehler aus Build 278 "
      "eine Ebene tiefer")
check("und danach wieder an",
      "self.textkonsole_grafik_an()" in _konsole
      and "_grafik_war" in _konsole,
      "nur wenn er vorher an war - ein Schalter-Nein bleibt ein Nein")
check("das Wiederherstellen kommt NACH dem Konsolenwechsel",
      _konsole.index("self._zurueck_auf_tty1")
      < _konsole.rindex("self.textkonsole_grafik_an()"),
      "erst gehoert tty1 wieder uns, dann legen wir sie still")

check("es gibt einen Schalter dagegen",
      "TEXTKONSOLE_GRAFIK_AUS_FLAG" in _q,
      "eine Datei und kein Menuepunkt: der Fall, in dem man ihn "
      "braucht, ist der, in dem der Bildschirm schwarz bleibt")
check("und misslingt das Zurueckstellen, nennt das Protokoll die Folge",
      "unsichtbar laufen" in _q,
      "ein stilles Scheitern hat denselben Fehler in Build 278 "
      "wochenlang verdeckt")

# ---------------------------------------------------------------------------
print()
print("Teil 2: das Verhalten")
# ---------------------------------------------------------------------------
F = H.fm.Frontend
_tmp = tempfile.mkdtemp(prefix="tk_")
_echt_setmode = F._kdsetmode
try:
    _gesetzt = []
    F._kdsetmode = classmethod(lambda cls, modus: _gesetzt.append(modus))
    F.TEXTKONSOLE_GRAFIK_AUS_FLAG = os.path.join(_tmp, "kein_schalter")
    F._tty1_grafik = False

    F.textkonsole_grafik_an()
    check("an: setzt den Grafikmodus",
          _gesetzt == [F.KD_GRAPHICS] and F._tty1_grafik is True,
          repr(_gesetzt))

    F.textkonsole_grafik_an()
    check("zweimal an setzt ihn nicht zweimal",
          _gesetzt == [F.KD_GRAPHICS],
          "ein ioctl je Zustandswechsel, nicht je Aufruf")

    F.textkonsole_grafik_aus()
    check("aus: setzt den Textmodus",
          _gesetzt == [F.KD_GRAPHICS, F.KD_TEXT]
          and F._tty1_grafik is False)

    _gesetzt[:] = []
    F.textkonsole_grafik_aus()
    check("aus ohne vorheriges an tut NICHTS",
          _gesetzt == [],
          "wer nichts gesetzt hat, stellt nichts zurueck - sonst "
          "legte ein Absturz die Konsole eines fremden Programms um")

    # DER SCHALTER
    _flag = os.path.join(_tmp, "textkonsole_grafik_aus")
    io.open(_flag, "w").write("")
    F.TEXTKONSOLE_GRAFIK_AUS_FLAG = _flag
    _gesetzt[:] = []
    F.textkonsole_grafik_an()
    check("mit Schalter passiert gar nichts",
          _gesetzt == [] and F._tty1_grafik is False,
          "das ist die Notbremse fuer einen schwarzen Bildschirm")

    # DER FEHLERFALL. Scheitert der ioctl, darf NICHT behauptet werden,
    # der Modus sei gesetzt - sonst stellte der Ausstieg etwas zurueck,
    # was nie an war.
    F.TEXTKONSOLE_GRAFIK_AUS_FLAG = os.path.join(_tmp, "kein_schalter")

    def _wirft(cls, modus):
        raise OSError(25, "Inappropriate ioctl for device")

    F._kdsetmode = classmethod(_wirft)
    F._tty1_grafik = False
    F.textkonsole_grafik_an()
    check("scheitert der ioctl, gilt der Modus als AUS",
          F._tty1_grafik is False,
          "eine Behauptung ueber einen Zustand, den wir nicht "
          "herstellen konnten, waere schlimmer als kein Versuch")

    # Umgekehrt: scheitert das ZURUECKstellen, bleibt der Merker
    # stehen, damit ein spaeterer Versuch es noch einmal probiert.
    F._tty1_grafik = True
    F.textkonsole_grafik_aus()
    check("scheitert das Zurueckstellen, bleibt der Merker stehen",
          F._tty1_grafik is True,
          "lieber zweimal zurueckstellen als einmal zu wenig")

    # Und der echte Weg scheitert auf einer gewoehnlichen Datei - das
    # ist die Gegenprobe, dass _kdsetmode wirklich ein ioctl macht und
    # nicht nur ein Merker ist.
    F._kdsetmode = _echt_setmode
    F.TTY1_PFAD = os.path.join(_tmp, "keine_konsole")
    io.open(F.TTY1_PFAD, "w").write("")
    F._tty1_grafik = False
    F.textkonsole_grafik_an()
    check("auf einer gewoehnlichen Datei schlaegt der echte Weg fehl",
          F._tty1_grafik is False,
          "also macht _kdsetmode tatsaechlich einen ioctl")
finally:
    F._kdsetmode = _echt_setmode
    F.TTY1_PFAD = "/dev/tty1"
    F._tty1_grafik = False
    shutil.rmtree(_tmp, ignore_errors=True)

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
