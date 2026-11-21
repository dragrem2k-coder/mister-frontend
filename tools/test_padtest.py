#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Der Controller-Test unter System -> Eingabe & Sprache (Build 335).

NUTZERWUNSCH (aus der Degauss-Einschaetzung, Punkt 3): ein Bildschirm,
der jede gedrueckte Taste anzeigt.

GEPRUEFT WIRD (mit nachgebauten Geraeten, ohne echtes Pad):
  1. Namen: Pad-Tasten, Steuerkreuz-Tasten, F-Tasten, Unbekanntes; in
     beiden Sprachen; dazu, was das Frontend aus der Taste macht.
  2. Achsen: Steuerkreuz und Stick in Richtungen, die Mitte ist keine.
  3. Mehrere Tasten zugleich und mehrere Geraete; ein abgezogenes Geraet
     bringt den Bildschirm nicht zum Absturz.
  4. Verlassen: zwei Sekunden halten, oder sofort mit Esc - B allein
     beendet NICHT (sonst liesse sich B nicht testen).
  5. Der Bildschirm: zeigt Tasten und Richtungen, leert danach die
     aufgelaufenen Ereignisse, steht im Menue und ist verdrahtet.

Ausfuehren:
    python3 tools/test_padtest.py
"""
import os
import sys

_HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HIER)

import _harness as H                                     # noqa: E402

fm = H.fm
import fe.padtest as PT                                  # noqa: E402
import fe.menu as M                                      # noqa: E402
import fe.translations as TR                             # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


class Geraet:
    def __init__(self, name, tasten=(), achsen=None, kaputt=False):
        self.name = name
        self.tasten = set(tasten)
        self.werte = dict(achsen or {})
        self.axis = {ax: (-32768, 32767) if ax in (0, 1) else (-1, 1)
                     for ax in (0, 1, 16, 17)}
        self.kaputt = kaputt

    def tasten_jetzt(self):
        if self.kaputt:
            raise OSError("abgezogen")
        return set(self.tasten)

    def achse_jetzt(self, ax):
        return self.werte.get(ax, 0)


print(__doc__.strip().split("\n")[0])
print()
_lang = TR.CURRENT_LANG
try:
    TR.CURRENT_LANG = "de"
    t = TR.t
    # -----------------------------------------------------------------------
    print("Test 1: Namen")
    # -----------------------------------------------------------------------
    check("Start/Select/L/R", [PT.taste_name(c) for c in (315, 314, 310, 311)]
          == ["Start", "Select", "L", "R"])
    check("Steuerkreuz-Taste auf Deutsch", PT.taste_name(544, t) == "Hoch")
    TR.CURRENT_LANG = "en"
    check("... und auf Englisch", PT.taste_name(544, t) == "Up")
    TR.CURRENT_LANG = "de"
    check("F-Tasten richtig (F1 = 59, F10 = 68, F11 = 87, F12 = 88)",
          [PT.taste_name(c) for c in (59, 68, 87, 88)]
          == ["F1", "F10", "F11", "F12"])
    check("GEGENPROBE: 69 ist NumLock, nicht F11",
          PT.taste_name(69) == "Code 69")
    check("Joystick-Taste", PT.taste_name(290, t) == "Taste 3")
    check("unbekannte Taste mit Code", PT.taste_name(999) == "Code 999")
    import fe.input as I
    a_code = [c for c, a in I.KEYMAP.items() if a == "ok"][0]
    check("was das Frontend daraus macht (KEYMAP)",
          PT.aktion(a_code) == "ok")
    check("GEGENPROBE: unbelegte Taste -> None", PT.aktion(999) is None)

    # -----------------------------------------------------------------------
    print()
    print("Test 2: Achsen")
    # -----------------------------------------------------------------------
    check("Stick ganz links", PT.richtung(-32768, (-32768, 32767),
                                          ("l", "r")) == "l")
    check("Stick ganz rechts", PT.richtung(32767, (-32768, 32767),
                                           ("l", "r")) == "r")
    check("GEGENPROBE: Mitte und leichtes Zittern -> nichts",
          PT.richtung(0, (-32768, 32767), ("l", "r")) is None
          and PT.richtung(-9000, (-32768, 32767), ("l", "r")) is None)
    check("Steuerkreuz -1/0/1", [PT.richtung(v, (-1, 1), ("h", "r"))
                                 for v in (-1, 0, 1)] == ["h", None, "r"])
    check("kaputte Grenzen -> nichts", PT.richtung(5, (3, 3), ("a", "b"))
          is None)

    # -----------------------------------------------------------------------
    print()
    print("Test 3: Zustand mehrerer Geraete")
    # -----------------------------------------------------------------------
    pad = Geraet("Pro Controller", (315, 314, 310, 311), {16: -1, 1: 32767})
    tast = Geraet("Tastatur")
    weg = Geraet("abgezogen", kaputt=True)
    st = PT.zustand([pad, tast, weg], t)
    check("abgezogenes Geraet fehlt, kein Absturz", len(st) == 2,
          [n for n, _t, _r in st])
    namen = [n for n, _a, _c in st[0][1]]
    check("vier Tasten zugleich (Start+Select+L+R)",
          sorted(namen) == ["L", "R", "Select", "Start"], namen)
    check("Richtungen: Kreuz links, Stick runter",
          st[0][2] == ["Steuerkreuz Links", "Stick Runter"], st[0][2])
    check("Tastatur ohne Druck: leer", st[1][1] == [] and st[1][2] == [])

    # -----------------------------------------------------------------------
    print()
    print("Test 4: Verlassen")
    # -----------------------------------------------------------------------
    h = PT.Halten(2.0)
    check("kurz gedrueckt: nicht fertig", h.melden([305], 0.0) is False)
    check("losgelassen: Uhr von vorn", h.melden([], 1.5) is False
          and h.melden([305], 1.6) is False and h.melden([305], 3.5) is False)
    check("zwei Sekunden am Stueck: fertig", h.melden([305], 3.7) is True)
    h = PT.Halten(2.0)
    check("Esc: sofort fertig", h.melden([1], 0.0) is True)
    h = PT.Halten(2.0)
    h.melden([304], 0.0)
    check("Rest der Haltezeit", abs(h.rest(0.5) - 1.5) < 1e-9)

    # -----------------------------------------------------------------------
    print()
    print("Test 5: der Bildschirm")
    # -----------------------------------------------------------------------
    for (w, hh) in ((1920, 1080), (320, 240)):
        H.set_screen(w, hh)
        f = H.make_frontend(page=0)
        texte = []
        echt = f.fb.text
        f.fb.text = lambda x, y, txt, *a, **k: (texte.append(txt),
                                                echt(x, y, txt, *a, **k))
        bilder = []
        f.fb.flip = lambda *a, **k: bilder.append(1)
        geleert = []
        f.inp.flush = lambda: geleert.append(1)
        f.inp.devices = {"/dev/input/event3": pad, "/dev/input/event0": tast}
        f.PADTEST_TAKT = 0
        runden = f.padtest_bildschirm(takte=5)
        check("%dx%d: Tasten stehen im Bild" % (w, hh),
              any("Start" in z for z in texte)
              and any("Pro Controller" in z for z in texte), texte[:6])
        check("%dx%d: gleiches Bild nur einmal gezeichnet" % (w, hh),
              len(bilder) == 1 and runden == 5, (len(bilder), runden))
        check("%dx%d: danach die aufgelaufenen Ereignisse geleert" % (w, hh),
              geleert == [1])
    esc = Geraet("Tastatur", (1,))
    f.inp.devices = {"k": esc}
    check("Esc beendet sofort (erste Runde)",
          f.padtest_bildschirm(takte=50) == 1)
    f.inp.devices = {}
    del texte[:]
    f.padtest_bildschirm(takte=1)
    check("ohne Geraete: eine Zeile statt eines leeren Bildes",
          fm.t("padtest_keine_geraete")[:20] in " ".join(texte))

    def kinds():
        offen, raus = [M.system_items()], []
        while offen:
            k = offen.pop()
            raus.extend(e[1] for e in k.get("items", ()) if len(e) > 1)
            offen.extend(k.get("folders", {}).values())
        return raus
    check("der Menuepunkt steht unter System", "padtest" in kinds())
    q = open(H.FRONTEND_PY, encoding="utf-8").read()
    check("und ist verdrahtet", 'elif kind == "padtest":' in q)
    for k in ("sys_padtest", "padtest_titel", "padtest_keine",
              "padtest_hinweis", "padtest_rest", "pt_kreuz", "pt_stick"):
        check("Text %s in beiden Sprachen" % k,
              set(TR.TRANSLATIONS.get(k, {})) >= {"de", "en"})
finally:
    TR.CURRENT_LANG = _lang

print()
if fails:
    print("ROT: %d Pruefung(en) fehlgeschlagen:" % len(fails))
    for f_ in fails:
        print("   - " + f_)
    sys.exit(1)
print("ALLES GRUEN")
