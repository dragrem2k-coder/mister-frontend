#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Der Controller-Test unter System -> Eingabe & Sprache (Build 335).

NUTZERWUNSCH (aus der Degauss-Einschaetzung): "3 auch" - ein Bildschirm,
der jede gedrueckte Taste anzeigt. Hilfreich beim Einrichten (welche
Taste ist bei diesem Pad "Start"?) und beim Pruefen der Pad-Kombination
Start+Select+L+R aus Build 326.

GELESEN WIRD DER ZUSTAND, NICHT DER EREIGNISSTROM: je Geraet die gerade
gedrueckten Tasten (EVIOCGKEY, Device.tasten_jetzt()) und die Achsen
(EVIOCGABS, Device.achse_jetzt()). So zeigt der Bildschirm, was JETZT
gedrueckt ist - auch drei Tasten gleichzeitig -, und nicht nur das
letzte Ereignis. Dazu je Taste, was das Frontend daraus macht (KEYMAP).

VERLASSEN: eine Taste zwei Sekunden halten, oder Esc auf der Tastatur.
B allein darf den Test nicht beenden - sonst liesse sich B nicht testen.
"""
import time

from fe.input import (KEYMAP, ABS_X, ABS_Y, ABS_HAT0X, ABS_HAT0Y, ABS_Z,
                      ABS_RZ, KEY_ESC)

HALTEN_ZUM_VERLASSEN = 2.0      # Sekunden

# Die Namen der ueblichen Pad-Tasten (linux/input-event-codes.h). Ein
# Eintrag, der mit "pt_" beginnt, ist ein Uebersetzungsschluessel
# (fe/translations.py) - Woerter gibt es in zwei Sprachen, "Start" nicht.
TASTEN_NAMEN = {
    304: "A", 305: "B", 306: "C", 307: "X", 308: "Y", 309: "Z",
    310: "L", 311: "R", 312: "L2", 313: "R2",
    314: "Select", 315: "Start", 316: "Home", 317: "L3", 318: "R3",
    544: "pt_hoch", 545: "pt_runter", 546: "pt_links", 547: "pt_rechts",
    1: "Esc", 28: "Enter", 57: "pt_leer", 14: "pt_rueck",
    103: "pt_pfeil_hoch", 108: "pt_pfeil_runter", 105: "pt_pfeil_links",
    106: "pt_pfeil_rechts", 87: "F11", 88: "F12",
}
for _i in range(12):
    TASTEN_NAMEN[288 + _i] = "pt_taste%d" % (_i + 1)   # BTN_TRIGGER...
for _i in range(10):
    TASTEN_NAMEN[59 + _i] = "F%d" % (_i + 1)          # KEY_F1..KEY_F10

ACHSEN = ((ABS_HAT0X, "pt_kreuz", ("pt_links", "pt_rechts")),
          (ABS_HAT0Y, "pt_kreuz", ("pt_hoch", "pt_runter")),
          (ABS_X, "pt_stick", ("pt_links", "pt_rechts")),
          (ABS_Y, "pt_stick", ("pt_hoch", "pt_runter")),
          (ABS_Z, "L2", (None, "pt_gedrueckt")),
          (ABS_RZ, "R2", (None, "pt_gedrueckt")))


def _wort(name, t=None):
    if name.startswith("pt_") and t is not None:
        if name.startswith("pt_taste"):
            return t("pt_taste", int(name[8:]))
        return t(name)
    return name


def taste_name(code, t=None):
    """Der Name einer Taste; t (die Uebersetzungsfunktion) macht aus den
    "pt_"-Schluesseln Woerter. Unbekannte Tasten heissen "Code <n>"."""
    return _wort(TASTEN_NAMEN.get(code, "Code %d" % code), t)


def aktion(code):
    """Was das Frontend aus dieser Taste macht - oder None."""
    a = KEYMAP.get(code)
    if a is None:
        return None
    return str(a)


def richtung(wert, grenzen, namen):
    """-1/1-Ausschlag einer Achse als Wort, oder None in der Mitte.

    Ein Viertel des Weges zur Seite zaehlt - dieselbe Groessenordnung wie
    die Totzone, mit der das Frontend Achsen in Richtungen uebersetzt."""
    lo, hi = grenzen
    if hi <= lo:
        return None
    anteil = (wert - lo) / float(hi - lo)
    if anteil < 0.25:
        return namen[0]
    if anteil > 0.75:
        return namen[1]
    return None


def zustand(geraete, t=None):
    """[(Geraetename, [(Tastenname, Aktion oder None, Code)],
    [Richtungstext])] fuer jedes Geraet. Geraete, die beim Lesen einen
    Fehler werfen (abgezogen), fehlen einfach."""
    raus = []
    for g in geraete:
        try:
            codes = sorted(g.tasten_jetzt())
        except OSError:
            continue
        tasten = [(taste_name(c, t), aktion(c), c) for c in codes]
        richtungen = []
        for ax, wort, namen in ACHSEN:
            grenzen = getattr(g, "axis", {}).get(ax)
            if not grenzen:
                continue
            try:
                r = richtung(g.achse_jetzt(ax), grenzen, namen)
            except OSError:
                continue
            if r:
                richtungen.append("%s %s" % (_wort(wort, t), _wort(r, t)))
        raus.append((getattr(g, "name", "?") or "?", tasten, richtungen))
    return raus


class Halten:
    """Merkt, seit wann eine Taste ununterbrochen gedrueckt ist.
    fertig() wird wahr, sobald irgendeine Taste HALTEN_ZUM_VERLASSEN
    Sekunden lang gehalten wurde - oder sofort bei Esc."""

    def __init__(self, dauer=HALTEN_ZUM_VERLASSEN):
        self.dauer = dauer
        self.seit = {}

    def melden(self, codes, jetzt=None):
        jetzt = time.monotonic() if jetzt is None else jetzt
        codes = set(codes)
        for c in list(self.seit):
            if c not in codes:
                del self.seit[c]
        for c in codes:
            self.seit.setdefault(c, jetzt)
        return self.fertig(jetzt)

    def fertig(self, jetzt=None):
        jetzt = time.monotonic() if jetzt is None else jetzt
        if KEY_ESC in self.seit:
            return True
        return any(jetzt - t >= self.dauer for t in self.seit.values())

    def rest(self, jetzt=None):
        """Wie lange die am laengsten gehaltene Taste noch braucht."""
        jetzt = time.monotonic() if jetzt is None else jetzt
        if not self.seit:
            return None
        return max(0.0, self.dauer - (jetzt - min(self.seit.values())))
