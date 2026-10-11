#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Die Tastenlegende unten rechts (Build 257).

Nutzerwunsch: "neben der Uhrzeit und WLAN-Symbol die Tastenerklaerung
eingeblendet - nur bei HDMI, bei CRT wird der Platz nicht reichen. Also
A:Oeffnen B:Zurueck, das gleiche fuer X und Y."

WORAN ES SCHEITERN KANN, und darum haengt dieser Test an genau diesen
Punkten:

  1. SIE ERSCHEINT AUF CRT. Dort ist die Zeile 320 Punkte breit, davon
     gehen Uhr und Netzwerksymbol ab. Was bliebe, reicht fuer "A:Oe".
  2. SIE SCHREIBT IN EINE MELDUNG HINEIN. Die Statusmeldung laeuft
     mittig ueber dieselbe Zeile. Zwei Texte uebereinander sind zwei
     unlesbare Texte.
  3. SIE WIRD BEIM TEIL-NEUAUFBAU NICHT FREIGERAEUMT. Die Hauptseite
     raeumt beim schnellen Weg nur eine schmale Spur um Uhr und Symbol
     frei - steht die Legende daneben und nicht mit drin, bleibt ihr
     alter Text stehen.
  4. SIE BEHAUPTET ETWAS FALSCHES. "A:Oeffnen" gilt auf der
     Hauptseite. Stuende sie eines Tages in der Spieleliste, muesste
     dort "Starten" stehen - und genau deshalb steht im Quelltext,
     warum sie dort NICHT steht (die Zeile traegt bereits Laufschrift
     und Meldungen).

GEPRUEFT WIRD AM ECHTEN BILD, nicht am Text: der Test zeichnet die
Hauptseite in eine Framebuffer-Attrappe und sieht nach, ob in der
Fusszeile Bildpunkte stehen - bei 1920x1080 ja, bei 320x240 nein.

Ausfuehren:
    python3 tools/test_tastenlegende.py
"""
import io
import os
import sys

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
sys.path.insert(0, _HIER)
sys.path.insert(0, os.path.join(_REPO, "frontend"))

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


_FE = io.open(os.path.join(_REPO, "frontend", "frontend.py"),
              encoding="utf-8").read()

# ---------------------------------------------------------------------------
print("Test 1: der Schalter und die Texte")
# ---------------------------------------------------------------------------
import fe.settings as S                                    # noqa: E402
import fe.translations as TR                               # noqa: E402

check("es gibt den Schalter", hasattr(S, "toggle_tastenlegende"))
check("und er ist von Haus aus AN", S.tastenlegende_an() is True,
      "sie ist genau fuer die da, die noch nicht wissen, welche Taste "
      "was tut")
for sch in ("legende_a", "legende_b", "legende_x", "legende_y",
            "legende_oeffnen", "legende_zurueck", "legende_menue",
            "legende_musik", "sys_tastenlegende_an",
            "sys_tastenlegende_aus"):
    e = TR.TRANSLATIONS.get(sch)
    check("Text '%s' gibt es in beiden Sprachen" % sch,
          bool(e and e.get("de") and e.get("en")), str(e))

from fe.menu import system_items                           # noqa: E402


def _finden(node, kind, pfad=""):
    for it in node.get("items", []):
        if it[1] == kind:
            return it[0], pfad
    for name, sub in node.get("folders", {}).items():
        tr = _finden(sub, kind, pfad + "/" + name)
        if tr:
            return tr
    return None


tr = _finden(system_items(), "tastenlegende")
check("es gibt einen Menuepunkt", tr is not None, str(tr))
if tr:
    check("und er steht bei den Anzeige-Einstellungen",
          "Anzeige" in tr[1] or "Display" in tr[1], tr[1])

# ---------------------------------------------------------------------------
print()
print("Test 2: die Legende selbst")
# ---------------------------------------------------------------------------
_q = _FE[_FE.index("    def _tastenlegende(self):"):]
_q = _q[:_q.index("\n    def ", 10)]
check("alle vier Tasten kommen vor",
      all(('t("legende_%s")' % k) in _q for k in "abxy"))
check("A heisst 'Oeffnen'", 'legende_oeffnen' in _q)
check("und es steht im Quelltext, warum sie in der Liste fehlt",
      "footer_y" in _q and "Laufschrift" in _q,
      "dort traegt dieselbe Zeile schon Laufschrift und Meldungen - "
      "das gehoert festgehalten, nicht nur entschieden")

# ---------------------------------------------------------------------------
print()
print("Test 3: am echten Bild - HDMI zeigt sie, CRT nicht")
# ---------------------------------------------------------------------------
# GEPRUEFT WIRD DURCH VERGLEICH ZWEIER BILDER, nicht durch Raten einer
# Farbe: einmal mit Legende, einmal ohne. Unterscheiden sie sich, war
# sie da. Das kommt ohne jede Annahme ueber Theme-Farben aus und ist
# genau die Technik, mit der in diesem Projekt schon die schnellen
# Zeichenwege geprueft werden.
import tempfile                                            # noqa: E402

import _harness as H                                       # noqa: E402
from fe.zwischenspeicher import vergessen as _vergessen    # noqa: E402

_TMP = tempfile.mkdtemp(prefix="legende_")
S.TASTENLEGENDE_AUS_FLAG = os.path.join(_TMP, "tastenlegende_aus")


def _bild(breite, hoehe, an, message=None):
    if an:
        try:
            os.remove(S.TASTENLEGENDE_AUS_FLAG)
        except OSError:
            pass
    else:
        open(S.TASTENLEGENDE_AUS_FLAG, "w").close()
    _vergessen()
    H.set_screen(breite, hoehe)
    fe = H.make_frontend(page=0)
    fe.draw(message=message)
    return bytes(fe.fb.buf)


def _unterschied(breite, hoehe, message=None):
    return _bild(breite, hoehe, True, message) != \
        _bild(breite, hoehe, False, message)


check("1920x1080: die Legende ist zu sehen", _unterschied(1920, 1080),
      "mit und ohne Schalter muesste sich das Bild unterscheiden")
check("320x240 (CRT): sie erscheint NICHT", not _unterschied(320, 240),
      "dort gehen Uhr und Symbol von 320 Punkten ab - was bliebe, "
      "reicht fuer 'A:Oe'")
check("eine lange Meldung verdraengt sie",
      not _unterschied(1920, 1080,
                       "Eine sehr lange Statusmeldung, die ueber die "
                       "halbe Zeile laeuft und links keinen Platz "
                       "mehr laesst"),
      "zwei Texte uebereinander sind zwei unlesbare Texte")
check("und danach ist sie wieder da", _unterschied(1920, 1080),
      "sie kommt von allein zurueck, sobald die Meldung weg ist")

# ---------------------------------------------------------------------------
print()
print("Test 4: der Teil-Neuaufbau raeumt sie mit frei")
# ---------------------------------------------------------------------------
# Die Hauptseite raeumt beim schnellen Weg nur eine schmale Spur um Uhr
# und Symbol frei ("__status__"). Steht die Legende daneben und nicht
# mit drin, bleibt ihr alter Text stehen, sobald sie sich aendert oder
# abgeschaltet wird.
_spur = _FE.split('_spuren["__status__"]')[0][-1200:]
check("die Spur rechnet die Legende mit ein",
      "_leg_w" in _spur and "tastenlegende_an()" in _spur,
      "sonst bleibt beim Abschalten der alte Text stehen")
check("und mit derselben Stufe wie beim Zeichnen",
      "max(1, s - 1)" in _spur,
      "eine andere Stufe hiesse eine andere Breite - und damit eine "
      "Spur, die daneben liegt")

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
