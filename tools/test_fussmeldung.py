#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft, dass eine Fusszeilen-Meldung (Erfolgs-Popup, "Favorit
hinzugefuegt", Geheimcode ...) lange genug stehen bleibt - in ALLEN
Ansichten.

Hintergrund (Nutzer-Rueckmeldung, Build 137): "die Popups fuer
geschaffte Erfolge kommen nicht im Raster und Galerie."

Sie kamen schon - nur nicht lange genug, um sie zu sehen. Gezeichnet
wurden sie korrekt (das prueft Test 1 hier), aber ~150ms spaeter lief
der COVER_SETTLE-Nachlader aus next_action() und baute die Seite per
draw_page_items() KOMPLETT neu auf - ohne Meldung, denn die kennt nur
der eine draw()-Aufruf, der sie ausgeloest hat.

Warum ausgerechnet Raster und Galerie: der Nachlader laeuft nur, wenn
beim Zeichnen Cover uebersprungen wurden. Die Liste zeigt EIN Cover
(das Panel rechts), die Kachelansichten bis zu 21 gleichzeitig - dort
ist praktisch immer eines dabei. In der Liste war der Fehler also
vorhanden, aber selten sichtbar.

Das bereits vorhandene Schutzfenster (self._popup_message_until) half
hier nicht: es bremst nur die beiden LEICHTEN Fusszeilen-Ticks, nicht
einen vollen Seitenaufbau.

Ausfuehren:
    python3 tools/test_fussmeldung.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H                                        # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


MSG = "Erfolg freigeschaltet: Sammler"


def _band(fb, y0, h):
    """Der Bildschirminhalt (mm, nicht der Puffer) eines Zeilenbandes."""
    return bytes(fb.mm[y0 * fb.stride:(y0 + h) * fb.stride])


def _fussband(f):
    """(y, hoehe) der Zeile, in der die Meldung steht - je Seite
    verschieden."""
    fb = f.fb
    if f.page == 1:
        has_art = f.hat_artspalte(f._display_items(), f.cats[f.cat_i][2])
        L = f.layout_items(has_art)
        return L["footer_y"], 8 * L["s"]
    L = f.layout_cats()
    s, oy = L["s"], L["oy"]
    return fb.height - oy - 13 * s, 8 * s


def _zuruecksetzen(f):
    """Meldungsgedaechtnis leeren - noetig, weil der Pruefstand die Uhr
    einfriert und das Schutzfenster damit von selbst nie ablaeuft."""
    f._popup_message = None
    f._popup_message_until = 0.0


def _messen(f, ansicht, seite):
    """Zeichnet dreimal und liefert (sichtbar, ueberlebt) in Bytes."""
    if seite == 1:
        f.ansicht_setzen(ansicht)
    else:
        f.ansicht_haupt_setzen(ansicht)
    _zuruecksetzen(f)
    f._force_full_redraw = True
    f.draw()                         # Ausgangsbild ohne Meldung
    y, h = _fussband(f)
    ohne = _band(f.fb, y, h)
    f.draw(message=MSG)              # wie _notify_new_achievements()
    sichtbar = sum(1 for a, b in zip(ohne, _band(f.fb, y, h)) if a != b)
    # Und jetzt genau der Aufruf, der die Meldung bisher weggeputzt hat:
    # der COVER_SETTLE-Nachlader aus next_action().
    if seite == 1:
        f.draw_page_items()
    else:
        f.draw_page_cats()
    ueberlebt = sum(1 for a, b in zip(ohne, _band(f.fb, y, h)) if a != b)
    return sichtbar, ueberlebt


print("Test 1: die Meldung wird ueberhaupt gezeichnet (alle Ansichten)")
H.set_screen(1920, 1080)
f = H.make_frontend(page=1)
ergebnisse = {}
for ansicht in ("liste", "raster", "galerie"):
    sichtbar, ueberlebt = _messen(f, ansicht, 1)
    ergebnisse[ansicht] = (sichtbar, ueberlebt)
    check("Seite 1 / %-8s zeichnet die Meldung" % ansicht, sichtbar > 0,
          "%d Bytes" % sichtbar)

print()
print("Test 2: sie ueberlebt den Nachlader (das war der Fehler)")
for ansicht in ("liste", "raster", "galerie"):
    sichtbar, ueberlebt = ergebnisse[ansicht]
    check("Seite 1 / %-8s: Meldung steht noch" % ansicht,
          ueberlebt == sichtbar and ueberlebt > 0,
          "%d von %d Bytes" % (ueberlebt, sichtbar))

print()
print("Test 3: dasselbe im Hauptmenue (Seite 0, alle drei Ansichten)")
f0 = H.make_frontend(page=0)
for ansicht in ("liste", "raster", "galerie"):
    sichtbar, ueberlebt = _messen(f0, ansicht, 0)
    check("Seite 0 / %-8s zeichnet und behaelt die Meldung" % ansicht,
          sichtbar > 0 and ueberlebt == sichtbar,
          "%d / %d Bytes" % (sichtbar, ueberlebt))

print()
print("Test 4: nach Ablauf des Schutzfensters ist sie wieder weg")
f.ansicht_setzen("raster")
_zuruecksetzen(f)
f._force_full_redraw = True
f.draw()
y, h = _fussband(f)
ohne = _band(f.fb, y, h)
f.draw(message=MSG)
check("waehrend des Fensters sichtbar",
      _band(f.fb, y, h) != ohne)
H.NOW[0] += 5.0                      # Fenster (2 s) ist damit vorbei
f.draw_page_items()
check("danach wieder die normale Fusszeile",
      _band(f.fb, y, h) == ohne)
H.NOW[0] -= 5.0

print()
print("Test 5: eine neue Meldung ersetzt die alte sofort")
_zuruecksetzen(f)
f._force_full_redraw = True
f.draw(message=MSG)
alt = _band(f.fb, y, h)
f.draw(message="Favorit hinzugefuegt")
neu = _band(f.fb, y, h)
check("die zweite Meldung steht da, nicht mehr die erste", alt != neu)
check("und sie wird gemerkt", f._popup_message == "Favorit hinzugefuegt")

print()
print("Test 6: ohne Meldung bleibt die Fusszeile unveraendert")
# Sicherheitsnetz gegen den naheliegenden Fehler, das Gedaechtnis nie
# zu leeren: ein ganz normaler Aufbau ohne Meldung darf keine alte
# Meldung hervorzaubern.
_zuruecksetzen(f)
f._force_full_redraw = True
f.draw()
check("_fussmeldung(None) liefert nichts", f._fussmeldung(None) is None)
check("_fussmeldung(eigene) liefert die eigene",
      f._fussmeldung("Test") == "Test")

print()
print("Test 7: der Aufraeum-Zweig im Leerlauf ist vorhanden")
# Ohne ihn bliebe die Meldung stehen, bis zufaellig etwas anderes die
# Zeile anfasst - in einer stillen Kachelansicht (kein Songtitel, kein
# Puls) kann das beliebig lange dauern.
quelle = open(H.FRONTEND_PY, encoding="utf-8").read()
check("next_action() leert _popup_message nach Ablauf",
      "if (self._popup_message\n"
      "                        and time.monotonic() >= self._popup_message_until):"
      in quelle)

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Tests bestanden.")
