#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Das eigene Farbschema (Build 171).

WARUM AUSGERECHNET DIESER TEST WICHTIG IST

Die Bestandsaufnahme im Projekt (EINSCHAETZUNG_Theme_Editor.md) sagt
den entscheidenden Satz:

    "Die eigentliche Arbeit liegt nicht bei den Farbreglern."

Ein Theme wird an vier Stellen eingetragen, davon eine in
`fe/menu.py`. Dieses Modul haelt BEWUSST eine eigene, unabhaengige
Kopie der Themenamen, damit das Menue nicht am vollen Theme-System
haengt. Genau dort ist es schon einmal schiefgegangen: die Kopie
kannte die neun Konsolen-Geheim-Themes nicht, und die Menuezeile
behauptete "Farbschema: Dunkel", waehrend laengst ein anderes aktiv
war.

Dagegen helfen zwei Dinge, und dieser Test prueft beide:

  1. Das eigene Schema hat GENAU EINEN festen Namen ("eigen"). Nur
     die Farben kommen aus einer Datei. Damit kann die Kopie in
     fe/menu.py nicht mehr veralten - der Fehler ist nicht behoben,
     sondern unmoeglich gemacht.
  2. Test 1 vergleicht beide Namenstabellen vollstaendig gegen-
     einander. Das faengt auch KUENFTIGE Abweichungen ab, nicht nur
     diese eine.

Ausfuehren:
    python3 tools/test_theme_eigen.py
"""
import io
import json
import os
import shutil
import sys
import tempfile

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
sys.path.insert(0, _HIER)

import _harness as H                                     # noqa: E402

fm = H.fm
import fe.menu as menu                                   # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


# ---------------------------------------------------------------------------
print("Test 1: DIE ZWEI NAMENSTABELLEN MUESSEN DECKUNGSGLEICH SEIN")
# ---------------------------------------------------------------------------
# Der Fehler, der schon einmal passiert ist - und der Grund, warum es
# diesen Test gibt.
for sprache, a, b in (("DE", fm.THEME_NAMES_DE, menu.THEME_NAMES_DE),
                      ("EN", fm.THEME_NAMES_EN, menu.THEME_NAMES_EN)):
    fehlt_im_menue = set(a) - set(b)
    zuviel_im_menue = set(b) - set(a)
    check("%s: fe/menu.py kennt alle Themes aus frontend.py" % sprache,
          not fehlt_im_menue, str(sorted(fehlt_im_menue)))
    check("%s: und keine, die es dort nicht gibt" % sprache,
          not zuviel_im_menue, str(sorted(zuviel_im_menue)))
    unterschiedlich = sorted(k for k in set(a) & set(b) if a[k] != b[k])
    check("%s: und die Anzeigenamen sind identisch" % sprache,
          not unterschiedlich, str(unterschiedlich))

check("fe/menu.py haelt alle Namen fuer gueltig",
      not (set(fm.THEME_NAMES_DE) - menu._VALID_THEME_NAMES),
      str(sorted(set(fm.THEME_NAMES_DE) - menu._VALID_THEME_NAMES)))
check("beide Module meinen dieselbe Zustandsdatei",
      fm.THEME_FILE == menu.THEME_FILE)

# ---------------------------------------------------------------------------
print()
print("Test 2: es gibt genau EINEN Namen fuers eigene Schema")
# ---------------------------------------------------------------------------
check("der Name ist fest verdrahtet", fm.THEME_EIGEN_NAME == "eigen")
check("frontend.py kennt ihn", "eigen" in fm.THEME_NAMES_DE)
check("fe/menu.py auch", "eigen" in menu._VALID_THEME_NAMES)
check("die Farben stehen dagegen in einer Datei",
      fm.THEME_EIGEN_FILE.endswith(".json"))
check("sieben Eigenschaften, wie in der Bestandsaufnahme",
      len(fm.THEME_FARBFELDER) == 6, str(fm.THEME_FARBFELDER))

# ---------------------------------------------------------------------------
print()
print("Test 3: speichern und wieder laden")
# ---------------------------------------------------------------------------
tmp = tempfile.mkdtemp(prefix="test_theme_eigen_")
pfad = os.path.join(tmp, "theme_eigen.json")
# Auch die Zustandsdatei umlenken - ein Test hinterlaesst nichts
# ausserhalb seines eigenen Ordners (siehe test_theme_editor.py).
_ALTE_WAHL = fm.THEME_FILE
fm.THEME_FILE = os.path.join(tmp, "theme")

meins = {"C_BG": (10, 20, 30), "C_PANEL": (40, 50, 60),
         "C_TEXT": (200, 210, 220), "C_DIM": (90, 95, 100),
         "C_TITLE": (255, 250, 240), "C_ACCENT": (7, 200, 130),
         "monochrome": True}
fm.eigenes_theme_speichern(meins, pfad)
check("die Datei liegt da", os.path.exists(pfad))
check("und kein .tmp bleibt liegen", not os.path.exists(pfad + ".tmp"))

zurueck = fm.eigenes_theme_lesen(pfad)
check("alle sechs Farben kommen unveraendert zurueck",
      all(tuple(zurueck[f]) == tuple(meins[f])
          for f in fm.THEME_FARBFELDER))
check("der monochrome-Schalter auch", zurueck["monochrome"] is True)

# Und der Weg, den das Frontend geht: laden -> anwenden.
check("laden traegt es in THEMES ein", fm.eigenes_theme_laden(pfad))
check("es ist danach vorhanden", fm.eigenes_theme_vorhanden())
fm.apply_theme("eigen")
check("apply_theme setzt wirklich die eigenen Farben",
      fm.C_BG == (10, 20, 30) and fm.C_ACCENT == (7, 200, 130),
      "%r / %r" % (fm.C_BG, fm.C_ACCENT))
check("und den monochrome-Schalter", fm.CURRENT_THEME_MONOCHROME is True)
import fe.framebuffer as FB                              # noqa: E402
check("fe/framebuffer.py wird mitgezogen", FB.C_BG == (10, 20, 30),
      repr(FB.C_BG))

# ---------------------------------------------------------------------------
print()
print("Test 4: eine kaputte Datei darf den Start NICHT aufhalten")
# ---------------------------------------------------------------------------
# Sie liegt auf der SD-Karte und kann von einem abgebrochenen
# Schreibvorgang stammen. "Kein eigenes Theme" ist die richtige
# Antwort - nicht ein Absturz beim Hochfahren.
faelle = [
    ("gar kein JSON", "{das ist kaputt"),
    ("leere Datei", ""),
    ("eine Liste statt eines Objekts", "[1, 2, 3]"),
    ("eine Farbe fehlt", json.dumps({"C_BG": [1, 2, 3]})),
    ("Farbe mit zwei Werten", json.dumps(
        dict({f: [1, 2, 3] for f in fm.THEME_FARBFELDER},
             C_ACCENT=[1, 2]))),
    ("Wert ausserhalb 0-255", json.dumps(
        dict({f: [1, 2, 3] for f in fm.THEME_FARBFELDER},
             C_ACCENT=[1, 2, 300]))),
    ("Kommazahl statt ganzer Zahl", json.dumps(
        dict({f: [1, 2, 3] for f in fm.THEME_FARBFELDER},
             C_ACCENT=[1, 2, 3.5]))),
    ("Text statt Zahl", json.dumps(
        dict({f: [1, 2, 3] for f in fm.THEME_FARBFELDER},
             C_ACCENT=["rot", 2, 3]))),
]
for was, inhalt in faelle:
    io.open(pfad, "w", encoding="utf-8").write(inhalt)
    try:
        ergebnis = fm.eigenes_theme_lesen(pfad)
        ok = ergebnis is None
    except Exception as e:                               # noqa: BLE001
        ok = False
        print("    Ausnahme:", e)
    check("%-28s -> kein eigenes Theme" % was, ok)

# Auch eine fehlende Datei ist in Ordnung.
os.remove(pfad)
check("fehlende Datei                -> kein eigenes Theme",
      fm.eigenes_theme_lesen(pfad) is None)
check("und laden traegt nichts ein", not fm.eigenes_theme_laden(pfad))
check("danach ist es auch aus THEMES verschwunden",
      not fm.eigenes_theme_vorhanden())

# ---------------------------------------------------------------------------
print()
print("Test 5: Unsinn wird gar nicht erst geschrieben")
# ---------------------------------------------------------------------------
try:
    fm.eigenes_theme_speichern(dict(meins, C_ACCENT=(1, 2, 999)), pfad)
    check("eine ungueltige Farbe wird abgelehnt", False)
except ValueError as e:
    check("eine ungueltige Farbe wird abgelehnt", True)
    check("und die Meldung nennt das Feld", "C_ACCENT" in str(e), str(e))
check("dabei entsteht keine Datei", not os.path.exists(pfad))

# ---------------------------------------------------------------------------
print()
print("Test 6: ohne eigenes Schema aendert sich am Durchschalten nichts")
# ---------------------------------------------------------------------------
fm.THEMES.pop("eigen", None)
ohne = fm._available_theme_order()
check("'eigen' taucht nicht auf", "eigen" not in ohne, str(ohne))
check("die mitgelieferten sind unveraendert da",
      ohne[:3] == ["dark", "light", "green"], str(ohne[:3]))

fm.eigenes_theme_speichern(meins, pfad)
fm.eigenes_theme_laden(pfad)
mit = fm._available_theme_order()
check("mit eigenem Schema steht es in der Reihenfolge",
      "eigen" in mit, str(mit))
check("und zwar hinter den mitgelieferten",
      mit.index("eigen") >= 3, str(mit))

# ---------------------------------------------------------------------------
print()
print("Test 7: der Menuepunkt ist verdrahtet")
# ---------------------------------------------------------------------------
quelle = io.open(os.path.join(_REPO, "frontend", "frontend.py"),
                 encoding="utf-8").read();
mq = io.open(os.path.join(_REPO, "frontend", "fe", "menu.py"),
             encoding="utf-8").read()
check("es gibt einen Menueeintrag",
      '"theme_eigen_speichern"' in mq)
check("und einen Handler dafuer",
      'kind == "theme_eigen_speichern"' in quelle)
check("er merkt die Wahl in der Zustandsdatei",
      "_theme_datei_schreiben(THEME_EIGEN_NAME)" in quelle)
check("und wendet sie sofort an",
      "apply_theme(THEME_EIGEN_NAME)" in quelle)
check("ein Fehlschlag wird dem Nutzer gesagt",
      "sys_theme_eigen_fehler" in quelle)
# ECHT pruefen, nicht per hasattr-Ausrede: hier stand zuerst ein
# "... if hasattr(H, ...) else True", und das war gruen, weil es die
# Funktion gar nicht gibt. Ein Test, der immer besteht, ist kein Test.
import fe.translations as T                              # noqa: E402
for schluessel in ("sys_theme_eigen_speichern", "sys_theme_eigen_gespeichert",
                   "sys_theme_eigen_fehler"):
    eintrag = T.TRANSLATIONS.get(schluessel)
    check("Text %-30s in beiden Sprachen" % schluessel,
          bool(eintrag) and bool(eintrag.get("de"))
          and bool(eintrag.get("en")),
          "" if eintrag else "fehlt ganz")

# Und: das eigene Schema wird VOR apply_theme() geladen - sonst waere
# es nach jedem Neustart weg.
check("es wird beim Modulstart geladen, VOR apply_theme()",
      quelle.index("eigenes_theme_laden()")
      < quelle.index("apply_theme(current_theme_name())"))

shutil.rmtree(tmp, ignore_errors=True)
fm.THEME_FILE = _ALTE_WAHL

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
