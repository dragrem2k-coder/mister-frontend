#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ordner, in denen genau EIN Spiel liegt, werden aufgeloest (Build 156).

AUSLOESER (Nutzer-Rueckmeldung): "meine psx roms liegen im ordner
games/PSX dort bekomme ich nur die listenansicht. und cover erscheint
nur wenn ich in denn ordner vom spiel reingehe. bei mega cd das gleiche
und saturn auch."

Das war keine Panne, sondern zwei richtige Entscheidungen, die sich
unguenstig treffen: hat_artspalte() blendet die Cover-Spalte aus, wenn
eine Liste NUR aus Ordnern besteht (Build 89), und eine reine
Ordnerauswahl faellt immer auf die Liste zurueck (Build 122). Bei
CD-Systemen liegt aber ueblicherweise jedes Spiel in einem eigenen
Ordner, weil eine .cue mehrere .bin mitbringt.

DIE DREI GRENZEN, DIE HIER ZAEHLEN - und warum sie so liegen:

  1. ZWEI Spiele im Ordner bleiben ein Ordner. Das ist eine echte
     Auswahl (Disc 1 / Disc 2), und die darf nicht verschwinden.
  2. Ein Spiel UND ein Unterordner bleibt ein Ordner. Sonst waere der
     Unterordner unerreichbar.
  3. Die .bin-Dateien zaehlen nicht mit. Kein System fuehrt ".bin" als
     ROM-Endung - fuer den Scanner war sie noch nie sichtbar. Genau
     deshalb greift die Regel im gemeldeten Fall ueberhaupt.

Ausfuehren:
    python3 tools/test_einzelordner.py
"""
import os
import shutil
import sys
import tempfile
import zipfile

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
_FRONTEND_DIR = os.path.dirname(
    os.environ.get("FRONTEND_PY",
                   os.path.join(_REPO, "frontend", "frontend.py")))
sys.path.insert(0, _FRONTEND_DIR)

import fe.settings as S                                # noqa: E402
import fe.scan as SC                                   # noqa: E402
import fe.translations as T                            # noqa: E402
import fe.naming as N                                  # noqa: E402
import fe.art as A                                     # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


TMP = tempfile.mkdtemp(prefix="einzelordner_")
S.EINZELORDNER_AUS_FLAG = os.path.join(TMP, "einzelordner_aus")

# Eine PSX-Sammlung, genau so aufgebaut wie die des Nutzers.
PSX = os.path.join(TMP, "PSX")
EXTMAP = {".cue": (1, "s", 1), ".chd": (1, "s", 1)}


def anlegen(*pfade):
    for p in pfade:
        voll = os.path.join(PSX, p)
        os.makedirs(os.path.dirname(voll), exist_ok=True)
        open(voll, "w").close()


anlegen(
    # Der gemeldete Fall: Ordner heisst (USA), die .cue heisst (NTSC-U),
    # und daneben liegt eine .bin, die der Scanner nicht kennt.
    "Jumping Flash! (USA)/Jumping Flash! (USA).bin",
    "Jumping Flash! (USA)/Jumping Flash! (NTSC-U).cue",
    # Ein zweiter, gleich gebauter Ordner.
    "Tekken 3 (USA)/Tekken 3 (USA).bin",
    "Tekken 3 (USA)/Tekken 3 (USA).cue",
    # Mehrteilig: zwei .cue - muss Ordner BLEIBEN.
    "Final Fantasy VII (USA)/Final Fantasy VII (USA) (Disc 1).cue",
    "Final Fantasy VII (USA)/Final Fantasy VII (USA) (Disc 2).cue",
    "Final Fantasy VII (USA)/Final Fantasy VII (USA) (Disc 1).bin",
    # Ein Spiel UND ein Unterordner - muss Ordner BLEIBEN.
    "Sammlung/Ein Spiel (USA).cue",
    "Sammlung/Extra/Noch eins (USA).cue",
    # Zwei Ebenen, unten genau ein Spiel: beide muessen wegfallen.
    "Tief/Tiefer/Verstecktes Spiel (USA).cue",
    # Ein Spiel, das schon flach liegt.
    "Wipeout (USA).chd",
)


def baum(einzeln):
    if einzeln:
        try:
            os.remove(S.EINZELORDNER_AUS_FLAG)
        except OSError:
            pass
    else:
        open(S.EINZELORDNER_AUS_FLAG, "w").close()
    return SC._scan_folder_tree(PSX, "PSX", "PSX", EXTMAP)


def namen(node):
    return sorted(i[0] for i in node["items"])


def ordner(node):
    return sorted(node["folders"].keys())


# ---------------------------------------------------------------------------
print("Test 1: Standard ist AN")
# ---------------------------------------------------------------------------
try:
    os.remove(S.EINZELORDNER_AUS_FLAG)
except OSError:
    pass
check("ohne Datei ist der Schalter an", S.einzelordner_aufloesen())
open(S.EINZELORDNER_AUS_FLAG, "w").close()
check("die Datei bedeutet AUS", not S.einzelordner_aufloesen())
check("die Datei heisst nach dem Abschalten, nicht nach dem Einschalten",
      S.EINZELORDNER_AUS_FLAG.endswith("_aus"))

# ---------------------------------------------------------------------------
print()
print("Test 2: ohne den Schalter bleibt alles beim Alten")
# ---------------------------------------------------------------------------
alt = baum(False)
check("die erste Ebene zeigt die Ordner",
      ordner(alt) == ["Final Fantasy VII (USA)", "Jumping Flash! (USA)",
                      "Sammlung", "Tekken 3 (USA)", "Tief"],
      str(ordner(alt)))
check("und nur das flach liegende Spiel", namen(alt) == ["Wipeout (USA)"],
      str(namen(alt)))

# ---------------------------------------------------------------------------
print()
print("Test 3: mit Schalter loesen sich die Einzelspiel-Ordner auf")
# ---------------------------------------------------------------------------
neu = baum(True)
check("Jumping Flash! steht jetzt direkt in der Liste",
      "Jumping Flash! (NTSC-U)" in namen(neu), str(namen(neu)))
check("Tekken 3 ebenso", "Tekken 3 (USA)" in namen(neu))
check("das flache Spiel ist unveraendert dabei",
      "Wipeout (USA)" in namen(neu))
check("die aufgeloesten Ordner sind weg",
      "Jumping Flash! (USA)" not in ordner(neu)
      and "Tekken 3 (USA)" not in ordner(neu), str(ordner(neu)))

# ---------------------------------------------------------------------------
print()
print("Test 4: die drei Grenzen halten")
# ---------------------------------------------------------------------------
check("zwei Discs bleiben ein Ordner",
      "Final Fantasy VII (USA)" in ordner(neu), str(ordner(neu)))
check("ein Spiel PLUS Unterordner bleibt ein Ordner",
      "Sammlung" in ordner(neu))
# Aufgeloest wird von UNTEN nach oben: der Unterordner "Extra" enthaelt
# selbst genau ein Spiel und faellt zuerst weg. "Sammlung" hat danach
# zwei Spiele - und bleibt deshalb voellig richtig ein Ordner. Beim
# Schreiben dieses Tests hatte ich hier zuerst "Sammlung enthaelt EIN
# Spiel" stehen und damit die Reihenfolge falsch im Kopf.
check("der Unterordner darin wurde selbst aufgeloest",
      namen(neu["folders"]["Sammlung"])
      == ["Ein Spiel (USA)", "Noch eins (USA)"],
      str(namen(neu["folders"]["Sammlung"])))
check("und ist danach kein Ordner mehr",
      not ordner(neu["folders"]["Sammlung"]),
      str(ordner(neu["folders"]["Sammlung"])))
check("das Spiel aus dem Unterordner behaelt seinen echten Pfad",
      any(i[2][0].endswith("Sammlung/Extra/Noch eins (USA).cue")
          for i in neu["folders"]["Sammlung"]["items"]),
      str([i[2][0] for i in neu["folders"]["Sammlung"]["items"]]))
check("zwei leere Ebenen fallen zusammen weg",
      "Verstecktes Spiel (USA)" in namen(neu) and "Tief" not in ordner(neu),
      str(namen(neu)))

# ---------------------------------------------------------------------------
print()
print("Test 5: die .bin-Dateien zaehlen nicht mit")
# ---------------------------------------------------------------------------
# Das ist der Kern des gemeldeten Falls. Waere ".bin" eine bekannte
# Endung, haette der Ordner ZWEI Spiele und bliebe stehen.
check(".bin ist keine bekannte Endung", ".bin" not in EXTMAP)
check("und taucht nirgends als Eintrag auf",
      not any(n.endswith(".bin") for n in namen(neu)))

# ---------------------------------------------------------------------------
print()
print("Test 6: der Name aendert weder Anzeige noch Cover-Abgleich")
# ---------------------------------------------------------------------------
# Der Ordner heisst "(USA)", die Datei "(NTSC-U)". Beides faellt bei der
# Anzeige weg und beim unscharfen Cover-Abgleich (Build 117) ebenso -
# sonst haette das Aufloesen ein funktionierendes Cover kaputtgemacht.
check("Anzeigename ist in beiden Faellen gleich",
      N.display_name("Jumping Flash! (USA)")
      == N.display_name("Jumping Flash! (NTSC-U)") == "Jumping Flash!",
      N.display_name("Jumping Flash! (NTSC-U)"))
check("Cover-Abgleich ist in beiden Faellen gleich",
      A.vergleichsname("Jumping Flash! (USA)")
      == A.vergleichsname("Jumping Flash! (NTSC-U)"),
      A.vergleichsname("Jumping Flash! (NTSC-U)"))
check("Disc-Marker bleiben dagegen stehen",
      "Disc 1" in N.display_name("Final Fantasy VII (USA) (Disc 1)"),
      N.display_name("Final Fantasy VII (USA) (Disc 1)"))

# ---------------------------------------------------------------------------
print()
print("Test 7: die Startpfade bleiben unveraendert")
# ---------------------------------------------------------------------------
# Das Aufloesen verschiebt einen Eintrag, es baut ihn NICHT neu. Zeigte
# der Pfad danach auf den Elternordner statt auf die Datei, liesse sich
# kein einziges Spiel mehr starten - und in der Liste saehe alles
# richtig aus.
eintrag = [i for i in neu["items"] if i[0] == "Jumping Flash! (NTSC-U)"][0]
pfad = eintrag[2][0]
check("der Pfad zeigt auf die echte Datei", os.path.isfile(pfad), pfad)
check("und fuehrt durch den Ordner hindurch",
      pfad.endswith("Jumping Flash! (USA)/Jumping Flash! (NTSC-U).cue"),
      pfad)
check("Art und Endung stimmen", eintrag[1] == "game" and eintrag[2][1] == ".cue")

# ---------------------------------------------------------------------------
print()
print("Test 8: dasselbe in ZIP-Archiven")
# ---------------------------------------------------------------------------
ZIP = os.path.join(TMP, "ZIP")
os.makedirs(ZIP, exist_ok=True)
with zipfile.ZipFile(os.path.join(ZIP, "Eins.zip"), "w") as z:
    z.writestr("Spiel im Archiv (USA).cue", "x")
with zipfile.ZipFile(os.path.join(ZIP, "Zwei.zip"), "w") as z:
    z.writestr("Unterordner/Nur eins (USA).cue", "x")
with zipfile.ZipFile(os.path.join(ZIP, "Drei.zip"), "w") as z:
    z.writestr("A (USA).cue", "x")
    z.writestr("B (USA).cue", "x")

try:
    os.remove(S.EINZELORDNER_AUS_FLAG)
except OSError:
    pass
zb = SC._scan_folder_tree(ZIP, "PSX", "PSX", EXTMAP)
check("ein Archiv mit genau einem Spiel wird aufgeloest",
      "Spiel im Archiv (USA)" in namen(zb), str(namen(zb)))
check("auch ueber einen Ordner IM Archiv hinweg",
      "Nur eins (USA)" in namen(zb), str(namen(zb)))
check("ein Archiv mit zwei Spielen bleibt Ordner",
      "Drei.zip" in ordner(zb), str(ordner(zb)))
check("und enthaelt beide", namen(zb["folders"]["Drei.zip"])
      == ["A (USA)", "B (USA)"], str(namen(zb["folders"]["Drei.zip"])))

# ---------------------------------------------------------------------------
print()
print("Test 9: ein Umschalten laesst neu einlesen")
# ---------------------------------------------------------------------------
import fe.paths                                        # noqa: E402
alt_bases = fe.paths.GAMES_BASES
try:
    fe.paths.GAMES_BASES = [TMP]
    S.toggle_einzelordner()
    sig_a, _ = SC._games_signature()
    S.toggle_einzelordner()
    sig_b, _ = SC._games_signature()
finally:
    fe.paths.GAMES_BASES = alt_bases
check("der Fingerabdruck kennt den Schalter",
      any(e[0] == "__einzelordner__" for e in sig_a),
      str([e for e in sig_a if e[0].startswith("__")]))
check("und aendert sich beim Umschalten", sig_a != sig_b)
check("die Logik-Version wurde hochgezaehlt",
      SC.SCAN_LOGIC_VERSION >= 5, str(SC.SCAN_LOGIC_VERSION))

# ---------------------------------------------------------------------------
print()
print("Test 10: Menuepunkt und Uebersetzungen")
# ---------------------------------------------------------------------------
menu_py = open(os.path.join(_FRONTEND_DIR, "fe", "menu.py"),
               encoding="utf-8").read()
check('der Menuepunkt "einzelordner" ist eingetragen',
      '"einzelordner", None' in menu_py)
fe_py = open(os.path.join(_FRONTEND_DIR, "frontend.py"),
             encoding="utf-8").read()
check("und wird in frontend.py behandelt", 'kind == "einzelordner"' in fe_py)
check("das Umschalten stoesst einen Neuscan an",
      'kind == "einzelordner"' in fe_py
      and "force_rescan=True"
      in fe_py.split('kind == "einzelordner"')[1][:1800])

tabelle = getattr(T, "TRANSLATIONS", None) or getattr(T, "STRINGS", {})
for schluessel in ("sys_einzelordner_on", "sys_einzelordner_off",
                   "sys_einzelordner_changed"):
    eintrag = tabelle.get(schluessel)
    check("Uebersetzung %s vorhanden (de+en)" % schluessel,
          bool(eintrag) and "de" in eintrag and "en" in eintrag)
# Die Zeile muss sagen, WAS sie bewirkt - "Einzelordner auflösen" allein
# sagt niemandem, warum er das wollen sollte.
de_aus = tabelle.get("sys_einzelordner_off", {}).get("de", "").lower()
check("der Text nennt den Gewinn (Cover/Raster/Galerie)",
      "cover" in de_aus and ("raster" in de_aus or "galerie" in de_aus),
      de_aus[:70])

shutil.rmtree(TMP, ignore_errors=True)

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for f in fails:
        print("   ", f)
    sys.exit(1)
print("Alle Tests bestanden.")
