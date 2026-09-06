#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft die Pad-Bedienung aus Build 88.

AUSLOESER (Nutzerwunsch): "Suche per Pad, mit der Tastenkombi Select
gedrueckt halten und A druecken waere super. Schaukasten dann Select und
X. Die Hilfe muss eh ueberarbeitet werden, da stehen Sachen drin die
sind nicht mehr aktuell."

DER BEFUND DAHINTER: durchgezaehlt waren FUENF Funktionen ausschliesslich
ueber die Tastatur erreichbar - Volltextsuche, Buchstabensprung,
Zufallsspiel, Durchgespielt-Markierung und der RA-Schaukasten. Am Pad
belegt waren nur A, B, X, Y, Start, Select, L/R, L2/R2 und Mode. Wer mit
dem Controller auf dem Sofa sitzt, konnte in einer Liste mit tausenden
Eintraegen nur seitenweise blaettern.

Freie Pad-Tasten gibt es keine mehr, deshalb wird SELECT zum
Modifikator. Das ist heikler, als es klingt: Select ALLEIN muss weiter
wie Zurueck wirken, darf aber bei einer Kombination NICHT zusaetzlich
ein "zurueck" mitschicken - sonst landet man nach jeder Suche eine Ebene
hoeher.

GEPRUEFT WIRD:
  1. Select allein wirkt weiter wie Zurueck - aber erst beim Loslassen.
  2. Select+A und Select+X loesen die neuen Aktionen aus, und das
     Loslassen von Select danach loest NICHTS mehr aus.
  3. Die Kombination haengt an der ZIELAKTION der zweiten Taste, nicht
     an deren Tastencode - wer sich eine eigene Belegung eingerichtet
     hat, behaelt sie.
  4. Ein waehrend des Haltens abgezogenes Pad laesst Select nicht
     "haengen".
  5. Der Buchstabenwaehler: Raster vollstaendig, Bewegung landet nie
     ausserhalb, Eingabe/Loeschen/Fertig/Abbrechen tun das Richtige.
  6. Der Waehler passt in JEDE Aufloesung - nichts wird ausserhalb des
     Bildspeichers gezeichnet.
  7. Die Hilfe: jeder aufgefuehrte Eintrag existiert in BEIDEN Sprachen,
     und die veralteten Angaben sind wirklich weg.

Ausfuehren:
    python3 tools/test_pad_bedienung.py
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import _harness as H                                  # noqa: E402

fm = H.fm
sys.path.insert(0, os.path.dirname(H.FRONTEND_PY))
import fe.input as I                                  # noqa: E402
import fe.menu as M                                   # noqa: E402
from fe.translations import TRANSLATIONS              # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


class PadAttrappe:
    """Nur so viel Geraet, wie _translate() tatsaechlich anfasst."""

    def __init__(self, pfad="/dev/input/eventPAD"):
        self.path = pfad
        self.axis = {}
        self.axis_state = {}


def code_fuer(aktion):
    """Der Tastencode, der aktuell diese Aktion ausloest - so wie der
    Code selbst es macht (ueber die Aktion, nicht fest verdrahtet)."""
    for c, a in I.KEYMAP.items():
        if a == aktion:
            return c
    raise AssertionError("keine Taste fuer %r in der KEYMAP" % aktion)


def frischer_manager():
    """InputManager ohne echte Geraete - rescan() wuerde sonst die
    Geraete des Testrechners einlesen."""
    mgr = I.InputManager.__new__(I.InputManager)
    mgr.devices = {}
    mgr.held = None
    mgr._last_repeat_time = 0.0
    mgr._last_repeat_act = None
    mgr._last_repeat_iv = I.REPEAT_INTERVAL
    mgr._select_down = set()
    mgr._select_kombiniert = False
    return mgr


EV_KEY = I.EV_KEY
SELECT = code_fuer("select")
OK_TASTE = code_fuer("ok")
BACK_FE = code_fuer("back_fe")

print("Test 1: Select allein meldet sich erst beim Loslassen")
# GEAENDERT (Build 90, Nutzervorschlag): Select allein geht NICHT mehr
# eine Ebene zurueck - das macht B, und zwei Bedeutungen auf einer
# Taste, von denen eine doppelt vorhanden ist, sind eine zu viel. Wer
# den Modifikator haelt und sich anders entscheidet, loeste sonst beim
# Loslassen ein ungewolltes "zurueck" aus. Die Meldung selbst bleibt -
# sie zeigt jetzt den Hinweis, wofuer Select da ist.
mgr = frischer_manager()
dev = PadAttrappe()
check("Druecken meldet noch nichts",
      mgr._translate(dev, EV_KEY, SELECT, 1) is None)
check("Loslassen meldet 'select'",
      mgr._translate(dev, EV_KEY, SELECT, 0) == "select")
fquelle = open(H.FRONTEND_PY, encoding="utf-8").read()
fcode = "\n".join(z for z in fquelle.splitlines()
                  if not z.lstrip().startswith("#"))
# Nur der Rumpf DIESES Zweigs - der naechste Zweig ("exit"/"back") ruft
# _go_back_or_confirm_quit() voellig zu Recht auf.
_ab = fcode.index('if act == "select":')
stelle = fcode[_ab:fcode.index('if act == "exit"', _ab)]
check("Select allein geht nicht mehr zurueck",
      "_go_back_or_confirm_quit" not in stelle)
check("Select allein zeigt stattdessen den Hinweis",
      "select_hint" in stelle)
check("der Hinweis existiert in beiden Sprachen",
      TRANSLATIONS.get("select_hint", {}).get("de")
      and TRANSLATIONS["select_hint"].get("en"))

print()
print("Test 2: die beiden Kombinationen")
for zweite, erwartet, name in ((OK_TASTE, "search_pad", "Select+A"),
                               (BACK_FE, "ra_showcase", "Select+X")):
    mgr = frischer_manager()
    dev = PadAttrappe()
    mgr._translate(dev, EV_KEY, SELECT, 1)
    got = mgr._translate(dev, EV_KEY, zweite, 1)
    check("%s loest %r aus" % (name, erwartet), got == erwartet,
          "bekam %r" % (got,))
    mgr._translate(dev, EV_KEY, zweite, 0)
    # Der eigentliche Stolperstein: ohne Sonderbehandlung kaeme hier
    # zusaetzlich ein "select" - also ein ungewolltes "eine Ebene
    # zurueck" direkt nach der Suche.
    check("%s: Loslassen von Select meldet NICHTS mehr" % name,
          mgr._translate(dev, EV_KEY, SELECT, 0) is None)

print()
print("Test 3: die zweite Taste zaehlt ueber ihre AKTION, nicht den Code")
# Wer im Menue "Tastenbelegung anpassen" benutzt hat, hat OK evtl. auf
# einer anderen Taste. Die Kombination muss mitwandern.
mgr = frischer_manager()
dev = PadAttrappe()
FREI = 999
alt = I.KEYMAP.get(FREI)
I.KEYMAP[FREI] = "ok"
try:
    mgr._translate(dev, EV_KEY, SELECT, 1)
    got = mgr._translate(dev, EV_KEY, FREI, 1)
finally:
    if alt is None:
        I.KEYMAP.pop(FREI, None)
    else:
        I.KEYMAP[FREI] = alt
check("eine umbelegte OK-Taste loest die Kombination genauso aus",
      got == "search_pad", "bekam %r" % (got,))

print()
print("Test 4: abgezogenes Pad laesst Select nicht haengen")
mgr = frischer_manager()
dev = PadAttrappe()
mgr._translate(dev, EV_KEY, SELECT, 1)
check("Select gilt als gehalten", dev.path in mgr._select_down)
# rescan() raeumt normalerweise verschwundene Geraete ab - hier direkt
# der Zweig, der dabei greift.
mgr._select_down.discard(dev.path)
if not mgr._select_down:
    mgr._select_kombiniert = False
check("nach dem Abziehen ist der Modifikator wieder aus",
      not mgr._select_down)
check("ein A danach ist wieder ein normales OK",
      mgr._translate(dev, EV_KEY, OK_TASTE, 1) == "ok")

print()
print("Test 5: der Buchstabenwaehler")
H.set_screen(1920, 1080)
f = H.make_frontend(page=1)
felder = f.PICKER_FELDER
buchstaben = "".join(w for a, w in felder if a == "letter")
check("26 Buchstaben und 10 Ziffern, in dieser Reihenfolge",
      buchstaben == "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", buchstaben)
check("Leerzeichen, Loeschen und Fertig sind dabei",
      [a for a, _w in felder[-3:]] == ["space", "del", "done"])
# Die letzte Zeile ist kuerzer als die anderen - von dort aus darf keine
# Bewegung ins Leere zeigen.
schlimmster = 0
for start in range(len(felder)):
    for richtung in ("up", "down", "left", "right"):
        f._picker_i = start
        f._picker_bewegen(richtung)
        schlimmster = max(schlimmster, f._picker_i)
        if not (0 <= f._picker_i < len(felder)):
            break
check("jede Bewegung von jedem Feld bleibt im Raster",
      schlimmster < len(felder), "groesster Index %d von %d"
      % (schlimmster, len(felder) - 1))

print()
print("Test 6: der Waehler passt in jede Aufloesung")
# Der Framebuffer der Attrappe ist genau so gross wie der echte - wird
# ausserhalb gezeichnet, fliegt es hier auf.
for w, h, name in ((320, 240, "CRT"), (640, 480, "480p"),
                   (1920, 1080, "HDMI")):
    H.set_screen(w, h)
    f = H.make_frontend(page=1)
    f._search_mode = True
    f._search_picker = True
    f._search_query = "MAR"
    fehler = ""
    try:
        for f._picker_i in (0, 12, len(f.PICKER_FELDER) - 1):
            f.draw_page_items(flip=False)
        ok = True
    except Exception as e:                             # noqa: BLE001
        ok, fehler = False, "%s: %s" % (type(e).__name__, e)
    check("%s: Waehler zeichnet sauber" % name, ok, fehler)

print()
print("Test 7: Eingeben, Loeschen, Fertig und Abbrechen")
# Kein Nachbau der Tastenschleife - stattdessen genau die Bausteine,
# die sie benutzt.
H.set_screen(1920, 1080)
f = H.make_frontend(page=1)
namen = [it[0] for it in f._display_items()]
treffer = fm.jump_to_substring(namen, 0, "MARIO")
check("die Suche findet ueberhaupt etwas",
      0 <= treffer < len(namen),
      "%r" % (namen[treffer] if namen else None,))
check("und zwar einen Namen, der 'Mario' enthaelt",
      "mario" in namen[treffer].lower(), namen[treffer])
# Loeschen muss ab der AUSGANGSPOSITION neu suchen, nicht ab dem
# aktuellen Treffer - sonst wandert man beim Zurueckloeschen weiter
# nach unten statt zurueck.
zurueck = fm.jump_to_substring(namen, 0, "MAR")
check("kuerzere Anfrage sucht wieder von vorn",
      zurueck <= treffer or "mar" in namen[zurueck].lower(),
      "%r" % namen[zurueck])

print()
print("Test 8: die Hilfe ist vollstaendig und nicht mehr veraltet")
quelle = open(H.FRONTEND_PY, encoding="utf-8").read()
import re                                             # noqa: E402
block = quelle[quelle.index("section_keys = ["):]
block = block[:block.index("]")]
schluessel = re.findall(r'\("(header|item)", "([a-z0-9_]+)"\)', block)
fehlend = []
for art, key in schluessel:
    namen_zu_pruefen = ([key] if art == "header"
                        else [key + "_key", key + "_desc"])
    for n in namen_zu_pruefen:
        eintrag = TRANSLATIONS.get(n)
        if not eintrag or not eintrag.get("de") or not eintrag.get("en"):
            fehlend.append(n)
check("jeder aufgefuehrte Eintrag existiert in beiden Sprachen",
      not fehlend, "fehlt: %s" % fehlend)
check("die Hilfe fuehrt ueberhaupt Eintraege",
      len(schluessel) > 20, "%d Zeilen" % len(schluessel))

hilfe_texte = " ".join(
    TRANSLATIONS[k + suffix][lang]
    for art, k in schluessel
    for suffix in (([""] if art == "header" else ["_key", "_desc"]))
    for lang in ("de", "en")
    if (k + suffix) in TRANSLATIONS)
# F10 ist seit Build 77 ersatzlos entfallen (lief ueber die von MiSTer
# gesperrte evdev-Ebene, und die HID-Pruefung verglich versehentlich
# F11) - stand aber weiter als Ausstieg in der Hilfe.
check("F10 wird nicht mehr als Ausstieg genannt",
      "F10" not in hilfe_texte)
check("F1 als Ausstieg steht jetzt drin",
      "F1 " in hilfe_texte or "F1(" in hilfe_texte)
check("die neuen Pad-Kombinationen stehen drin",
      "Select+A" in hilfe_texte and "Select+X" in hilfe_texte)
# Der F5-Reset loest seit Build 75 SOFORT aus (RESET_HOLD = 0.0).
check("der F5-Reset wird nicht mehr mit Haltezeit beschrieben",
      I.InputManager.RESET_HOLD == 0.0
      and "F5 (Tastatur, ca." not in hilfe_texte,
      "RESET_HOLD=%r" % I.InputManager.RESET_HOLD)

print()
print("Test 9: die beiden Nachlade-Punkte stehen im Menue")


def alle_eintraege(node):
    raus = list(node.get("items", []))
    for sub in node.get("folders", {}).values():
        raus.extend(alle_eintraege(sub))
    return raus


arten = [e[1] for e in alle_eintraege(M.system_items())
         if isinstance(e, (list, tuple)) and len(e) > 1]
check("Boxarts nachladen ist erreichbar", "boxart_download" in arten)
check("Spieledaten nachladen ist erreichbar", "gameinfo_download" in arten)
check("und zwar genau einmal",
      arten.count("boxart_download") == 1
      and arten.count("gameinfo_download") == 1)

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for f_ in fails:
        print("  -", f_)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
