#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft die beiden Sackgassen des Zufalls-Zock-Bildschirms (Build 144).

Bis Build 143 endete draw_wot_screen() in genau EINER Meldung, sobald
nichts mehr ziehbar war: "alles durchgespielt". Dahinter steckten aber
zwei voellig verschiedene Lagen:

  a) Der Bestand ist leer (noch nie gescannt, oder keine Spiele-Systeme).
     Dann ist "durchgespielt" schlicht falsch - faellig ist ein Scan.
  b) Der Bestand ist da, aber jedes Spiel steht schon in wot_played.json.
     Dann stimmte die Meldung zwar, war aber eine Sackgasse: die
     gespielt-Liste liess sich nirgends im Frontend zuruecksetzen, man
     musste wot_played.json von Hand loeschen.

Getestet wird deshalb:
  1. leerer Bestand  -> Hinweis auf den Scan, KEINE Auswahl
  2. alles gespielt  -> Auswahl mit Erklaertext, "Zurueck" beendet sauber
  3. alles gespielt  -> "Zuruecksetzen" leert die Datei und macht weiter
  4. _wizard_choice(lines=...) verdraengt auf 320x240 weder die Optionen
     noch die Hinweiszeile

Ausfuehren:
    python3 tools/test_zufallszock.py
"""
import os
import sys
import json
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H                                        # noqa: E402

fm = H.fm
fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


# ---------------------------------------------------------------------------
# Attrappen: die beiden Dialoge protokollieren statt zu zeichnen, damit der
# Test die ENTSCHEIDUNG prueft und nicht die Pixel (die deckt Test 4 ab).
# ---------------------------------------------------------------------------
def _rueste(f, wahl):
    """wahl = Index, den _wizard_choice liefern soll (None = ESC)."""
    f._protokoll = []

    def _info(title, lines, skippable=True):
        f._protokoll.append(("info", list(lines)))
        return True

    def _choice(title, options, initial=0, hint_key=None, lines=None):
        f._protokoll.append(("choice", list(options), list(lines or [])))
        return wahl

    f._wizard_info = _info
    f._wizard_choice = _choice
    # Nach dem Zuruecksetzen laeuft die echte Funktion weiter und will
    # ziehen/zeichnen. So weit soll der Test nicht - eine Abbruch-Marke
    # direkt hinter der Ruecksetz-Stelle reicht.
    f._wot_start_screen = lambda pick: None


class _Abbruch(Exception):
    pass


def _pool_setzen(f, spiele):
    """Attract-Pool fest vorgeben: [(label, syskey, arg), ...]."""
    f._attract_pool = [
        (titel, "SNES", ("/f/%d.sfc" % i, ".sfc", "SNES", None, None))
        for i, titel in enumerate(spiele)]


def _played_datei(tmpdir, eintraege):
    """wot_played.json im Testordner anlegen und mister_wot darauf
    umbiegen. Liefert den Pfad."""
    pfad = os.path.join(tmpdir, "wot_played.json")
    if eintraege is None:
        if os.path.exists(pfad):
            os.remove(pfad)
    else:
        with open(pfad, "w", encoding="utf-8") as fh:
            json.dump({"version": 1, "played": eintraege}, fh)
    fm.mister_wot.WOT_PLAYED_FILE = pfad
    return pfad


tmp = tempfile.mkdtemp(prefix="wot_test_")

# ---------------------------------------------------------------------------
print("Test 1: leerer Bestand -> Hinweis auf den Scan")
# ---------------------------------------------------------------------------
f = H.make_frontend(page=1)
_pool_setzen(f, [])
_played_datei(tmp, None)
_rueste(f, wahl=0)
f.draw_wot_screen()

arten = [e[0] for e in f._protokoll]
check("genau eine Meldung, keine Auswahl", arten == ["info"], str(arten))
if arten[:1] == ["info"]:
    text = " ".join(f._protokoll[0][1])
    check("Text nennt den Scan, nicht 'durchgespielt'",
          "einlesen" in text.lower() or "scan" in text.lower(),
          repr(text))
    check("Text behauptet NICHT 'durchgespielt'",
          "durchgespielt" not in text.lower() and "dran" not in text.lower(),
          repr(text))

# ---------------------------------------------------------------------------
print("Test 2: alles gespielt -> Auswahl, 'Zurueck' beendet sauber")
# ---------------------------------------------------------------------------
SPIELE = ["Super Mario World", "F-Zero", "Chrono Trigger"]
f = H.make_frontend(page=1)
_pool_setzen(f, SPIELE)
pfad = _played_datei(tmp, [{"system": "SNES", "title": s,
                            "norm": fm.wot_normalize_title(s)}
                           for s in SPIELE])
_rueste(f, wahl=1)                       # 1 = "Zurueck"
f.draw_wot_screen()

arten = [e[0] for e in f._protokoll]
check("Auswahl statt Sackgasse", arten == ["choice"], str(arten))
if arten[:1] == ["choice"]:
    _, optionen, zeilen = f._protokoll[0]
    check("zwei Optionen (zuruecksetzen / zurueck)", len(optionen) == 2,
          str(optionen))
    check("Erklaertext mit der Anzahl",
          bool(zeilen) and "3" in zeilen[0], str(zeilen))
with open(pfad, encoding="utf-8") as fh:
    noch_da = json.load(fh)["played"]
check("'Zurueck' laesst die gespielt-Liste unangetastet",
      len(noch_da) == 3, "%d Eintraege" % len(noch_da))

# ---------------------------------------------------------------------------
print("Test 3: alles gespielt -> 'Zuruecksetzen' leert die Datei")
# ---------------------------------------------------------------------------
f = H.make_frontend(page=1)
_pool_setzen(f, SPIELE)
pfad = _played_datei(tmp, [{"system": "SNES", "title": s,
                            "norm": fm.wot_normalize_title(s)}
                           for s in SPIELE])
_rueste(f, wahl=0)                       # 0 = "Liste zuruecksetzen"
# Nach dem Zuruecksetzen zieht die Funktion weiter; der Ziehvorgang
# selbst ist hier egal, deshalb direkt hinter der Bestaetigung raus.
_echtes_info = f._wizard_info


def _info_mit_stopp(title, lines, skippable=True):
    _echtes_info(title, lines, skippable)
    if any("zurückgesetzt" in x.lower() or "reset" in x.lower()
           for x in lines):
        raise _Abbruch()
    return True


f._wizard_info = _info_mit_stopp
try:
    f.draw_wot_screen()
except _Abbruch:
    pass

arten = [e[0] for e in f._protokoll]
check("erst Auswahl, dann Bestaetigung",
      arten[:2] == ["choice", "info"], str(arten))
with open(pfad, encoding="utf-8") as fh:
    daten = json.load(fh)
check("gespielt-Liste ist leer", daten.get("played") == [], str(daten))
check("Datei bleibt gueltiges JSON mit Version",
      daten.get("version") == 1, str(daten))
check("keine .tmp-Leiche neben der Datei",
      not os.path.exists(pfad + ".tmp"))
if arten[:2] == ["choice", "info"]:
    check("Bestaetigung nennt die Anzahl wieder",
          "3" in " ".join(f._protokoll[1][1]), str(f._protokoll[1][1]))

# ---------------------------------------------------------------------------
print("Test 4: _wizard_choice(lines=...) verdraengt nichts auf 320x240")
# ---------------------------------------------------------------------------
H.set_screen(320, 240)
f = H.make_frontend(page=1)
fb = f.fb
LANG = ("Alle 1234 Spiele waren schon einmal dran - die Liste merkt sich "
        "jeden Start, damit sich nichts wiederholt und man wirklich einmal "
        "durch den ganzen Bestand kommt, bevor sich etwas wiederholt.")


def _zeilen_mit_inhalt(fb):
    """Indizes aller Bildzeilen, in denen TEXT steht.

    Auf reine Hintergrund-Gleichheit zu pruefen geht hier nicht: der
    Hintergrund ist ein ganz flacher Verlauf (Zeilenwerte 0x07..0x0a),
    damit unterscheidet sich fast jede Zeile von jeder anderen. Text
    ist dagegen um ein Vielfaches heller - eine Helligkeitsschwelle
    trennt beides sauber."""
    return [y for y in range(fb.height)
            if max(fb.mm[y * fb.stride:(y + 1) * fb.stride]) > 0x40]


eingaben = ["ok"]
f.inp.read_action = lambda: eingaben.pop(0) if eingaben else "ok"
ergebnis = f._wizard_choice("ZUFALLS-ZOCK",
                            ["Liste zurücksetzen - wieder alles ziehbar",
                             "Zurück"],
                            lines=[LANG])
check("OK liefert den gewaehlten Index", ergebnis == 0, str(ergebnis))

zeilen = _zeilen_mit_inhalt(fb)
check("ueberhaupt etwas gezeichnet", bool(zeilen))
if zeilen:
    oy = fb.height * fm.OVERSCAN_Y // 100
    unten = fb.height - oy
    check("nichts unterhalb des Overscan-Randes", max(zeilen) < unten,
          "letzte Zeile %d, Grenze %d" % (max(zeilen), unten))
    # Die Hinweiszeile sitzt bei H - oy - 8*sc; es muss also im untersten
    # Viertel noch Inhalt stehen, sonst wurde sie ueberschrieben/verdraengt.
    check("Hinweiszeile noch vorhanden",
          any(y > fb.height * 3 // 4 for y in zeilen),
          "letzte Zeile %d" % max(zeilen))

# Gegenprobe: derselbe Bildschirm ohne Erklaertext. Bewusst eine FRISCHE
# Instanz - flip() uebertraegt nur geaenderte Zeilen, ein von Hand
# genullter mm-Puffer wuerde die Zaehlung also verfaelschen.
f2 = H.make_frontend(page=1)
fb2 = f2.fb
eingaben = ["ok"]
f2.inp.read_action = lambda: eingaben.pop(0) if eingaben else "ok"
f2._wizard_choice("ZUFALLS-ZOCK",
                  ["Liste zurücksetzen - wieder alles ziehbar", "Zurück"])
ohne = _zeilen_mit_inhalt(fb2)
check("ohne lines wird spuerbar weniger gezeichnet",
      bool(ohne) and len(ohne) < len(zeilen),
      "ohne %d Zeilen / mit %d" % (len(ohne), len(zeilen)))
check("auch ohne lines endet das Bild vor dem Rand",
      bool(ohne) and max(ohne) < fb2.height - fb2.height * fm.OVERSCAN_Y // 100,
      "letzte Zeile %d" % max(ohne or [0]))

H.set_screen(1920, 1080)

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  - " + x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
