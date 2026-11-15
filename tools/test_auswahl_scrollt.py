#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Eine lange Auswahl scrollt mit - das Kontextmenue zeigt jeden Eintrag (Build 327).

NUTZERMELDUNG: "wenn ich zum beispiel in der romsauswahl bin und dann x
druecke kommt ja das menue wo steht spiel-infos, anleitung und so weiter,
diese muesste mitscrollen weil man ein paar eintraege die unter 'zu
buchstaben springen' noch stehen man diese nicht sieht".

_wizard_choice() zeichnete alle Optionen untereinander, 36*s Punkte
auseinander - auf 1080p passen davon acht ueber die Bedienhilfe, das
Kontextmenue eines Spiels hat bis zu zwoelf.

GEPRUEFT WIRD, am echten _wizard_choice() mit nachgestellten Tasten:
  1. GEGENPROBE zuerst: zwoelf Optionen passen auf 1080p NICHT alle -
     sonst waere dieser Test keiner.
  2. In JEDEM Bild steht die markierte Option, und keine gezeichnete
     Option reicht in die Bedienhilfe.
  3. Jede Option war einmal markiert UND sichtbar - runter bis zum Ende,
     und ueber den Rand von oben nach unten (Umlauf).
  4. ^ und v stehen genau dann da, wenn oben bzw. unten etwas fehlt.
  5. Eine kurze Liste sieht aus wie vorher: alles sichtbar, kein ^/v.
  6. Dasselbe auf 320x240 (CRT).
  7. Das Kontextmenue benutzt _wizard_choice().

Ausfuehren:
    python3 tools/test_auswahl_scrollt.py
"""
import os
import sys

_HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HIER)

import _harness as H                                     # noqa: E402

fm = H.fm
fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


print(__doc__.strip().split("\n")[0])
print()

OPTIONEN = ["Eintrag %02d" % i for i in range(1, 13)]


def lauf(w, h, optionen, tasten):
    """_wizard_choice() mit diesen Tasten; liefert (Ergebnis, Bilder,
    Grenze, s). Ein Bild ist die Liste (y, Text) der Optionen, wie sie
    bis zum flip() gezeichnet wurden; Grenze ist die Oberkante der
    Bedienhilfe."""
    H.set_screen(w, h)
    f = H.make_frontend(page=1)
    s = fm._skala(f.fb.width, f.fb.height)
    bilder = []
    aktuell = []
    echt_text = f.fb.text

    def _text(x, y, txt, *a, **k):
        aktuell.append((x, y, txt))
        return echt_text(x, y, txt, *a, **k)

    def _flip(*a, **k):
        bilder.append(list(aktuell))
        del aktuell[:]
    f.fb.text = _text
    f.fb.flip = _flip
    rest = list(tasten)
    f.inp.read_action = lambda timeout=None: rest.pop(0) if rest else "ok"
    erg = f._wizard_choice("Titel", optionen,
                           hint_key="choice_hint_plain")
    hint = fm.t("choice_hint_plain")
    sc = s - 1 if s > 1 else 1
    oy = f.fb.height * fm.OVERSCAN_Y // 100
    grenze = f.fb.height - oy - f._hinweis_hoehe(hint, sc)
    return erg, bilder, grenze, s, f


def optionen_im_bild(bild, optionen):
    """[(Index, y, markiert)] fuer jede gezeichnete Option."""
    raus = []
    for _x, y, txt in bild:
        for i, o in enumerate(optionen):
            if txt in ("> " + o, "  " + o):
                raus.append((i, y, txt.startswith("> ")))
    return raus


def zeichen_im_bild(bild, z):
    return any(txt == z for _x, _y, txt in bild)


for (w, h) in ((1920, 1080), (320, 240)):
    print("--- %dx%d ---" % (w, h))
    # -----------------------------------------------------------------------
    # Runter bis ans Ende, dann einmal ueber den Rand, dann hoch.
    tasten = ["down"] * 11 + ["down"] + ["up"] * 3 + ["back"]
    erg, bilder, grenze, s, f = lauf(w, h, OPTIONEN, tasten)
    sichtbar = f._wahl_sichtbar((h * fm.OVERSCAN_Y // 100) + 70 * s,
                                fm.t("choice_hint_plain"),
                                s - 1 if s > 1 else 1, s, 999)
    check("GEGENPROBE: zwoelf passen hier nicht alle", sichtbar < 12,
          "%d sichtbar" % sichtbar)
    check("ESC liefert None wie bisher", erg is None, erg)
    check("ein Bild je Taste (und eins am Anfang)",
          len(bilder) == len(tasten), "%d Bilder" % len(bilder))
    erwartet = [0]
    c = 0
    for t_ in tasten[:-1]:
        c = (c + (1 if t_ == "down" else -1)) % len(OPTIONEN)
        erwartet.append(c)
    alle_gut = True
    gesehen_markiert = set()
    zu_tief = []
    for k, bild in enumerate(bilder):
        im = optionen_im_bild(bild, OPTIONEN)
        markiert = [i for i, _y, m in im if m]
        if markiert != [erwartet[k]]:
            alle_gut = False
        gesehen_markiert.update(markiert)
        for i, y, _m in im:
            if y + 8 * s > grenze:
                zu_tief.append((k, i, y))
        # ^ / v genau dann, wenn oben / unten etwas fehlt
        idx = [i for i, _y, _m in im]
        if idx:
            oben_fehlt = min(idx) > 0
            unten_fehlt = max(idx) < len(OPTIONEN) - 1
            if (zeichen_im_bild(bild, "^") != oben_fehlt
                    or zeichen_im_bild(bild, "v") != unten_fehlt):
                alle_gut = False
                print("     Bild %d: Anzeiger falsch (%s..%s)"
                      % (k, min(idx), max(idx)))
    check("in jedem Bild genau die richtige Option markiert und sichtbar, "
          "^/v stimmen", alle_gut)
    check("keine Option reicht in die Bedienhilfe", not zu_tief, zu_tief[:3])
    check("jede der zwoelf war einmal markiert und sichtbar",
          gesehen_markiert == set(range(12)), sorted(gesehen_markiert))
    check("je Bild nie mehr Zeilen als Platz ist",
          max(len(optionen_im_bild(b, OPTIONEN)) for b in bilder)
          == sichtbar)
    # Auswahl am Ende wirklich die gezeigte
    erg2, _b, _g, _s, _f = lauf(w, h, OPTIONEN, ["down"] * 10 + ["ok"])
    check("OK liefert die markierte (Index 10)", erg2 == 10, erg2)

    # -----------------------------------------------------------------------
    kurz = OPTIONEN[:3]
    erg3, bilder3, grenze3, s3, _f = lauf(w, h, kurz, ["down", "ok"])
    im = optionen_im_bild(bilder3[0], kurz)
    check("kurze Liste: alles sichtbar", sorted(i for i, _y, _m in im)
          == [0, 1, 2])
    check("kurze Liste: kein ^ und kein v",
          not zeichen_im_bild(bilder3[0], "^")
          and not zeichen_im_bild(bilder3[0], "v"))
    check("kurze Liste: Abstand wie bisher (36*s)",
          [y for _i, y, _m in sorted(im)][1]
          - [y for _i, y, _m in sorted(im)][0] == 36 * s3)
    print()

print("Test 7: das Kontextmenue benutzt _wizard_choice()")
q = open(H.FRONTEND_PY, encoding="utf-8").read()
check("ja", "self._wizard_choice(t(\"ctx_titel\")"
      in H.nur_code(H.koerper(q, "kontextmenue")))

print()
if fails:
    print("ROT: %d Pruefung(en) fehlgeschlagen:" % len(fails))
    for f_ in fails:
        print("   - " + f_)
    sys.exit(1)
print("ALLES GRUEN")
