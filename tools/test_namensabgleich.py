#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft den unscharfen Namensabgleich und das Nachzieh-Netz fuer
spaet anlaufende Laufwerke (Build 117).

BEIDES KAM AUS DERSELBEN URSACHE. Der Nutzer hat eine andere
USB-Festplatte angeschlossen, und daraufhin fiel zweierlei auf:

  1. "bei jedem Frontendstart wird versucht, die Spieleliste neu
     aufzubauen, ich muss immer erst unter Wartung von Hand neu
     einlesen" - die Platte laeuft langsamer an als die alte.
  2. "bei N64 und Sega 32X werden mir keine Boxarts mehr angezeigt".

Der zweite Punkt sah nach einem Fehler in einem der letzten Builds
aus, war aber keiner. Die ROMs auf der neuen Platte tragen die alte
GoodTools-Schreibweise:

    007 - The World is Not Enough (U) [!]

die heruntergeladenen Cover die No-Intro-Schreibweise:

    007 - The World Is Not Enough (USA).art

Zeichenweise passt davon nichts zusammen - nicht einmal das "is"
gegen "Is". Genau dafuer gibt es jetzt vergleichsname().

WORAUF ES BEI DEM ABGLEICH ANKOMMT: er darf nur einspringen, wenn der
exakte Name nichts gefunden hat, und er darf keine VERSCHIEDENEN
Spiele zusammenwerfen. Beides wird hier geprueft.

Ausfuehren:
    python3 tools/test_namensabgleich.py
"""
import os
import shutil
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)

import _harness as H                                    # noqa: E402,F401

sys.path.insert(0, os.path.join(_REPO, "frontend"))
import fe.art as A                                      # noqa: E402
import fe.scan as S                                     # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


print("Test 1: die echten Namenspaare vom Geraet finden zusammen")
paare = [
    ("007 - The World is Not Enough (U) [!]",
     "007 - The World Is Not Enough (USA)"),
    ("AeroFighters Assault (U) [!]", "AeroFighters Assault (USA)"),
    ("1080 Snowboarding (JU) (M2) [!]", "1080 Snowboarding (USA)"),
    ("Mortal Kombat II 32X (JUE) (Dec 1994) [!]",
     "Mortal Kombat II 32X (JUE)"),
    ("Knuckles Chaotix 32X (5) [!]", "Knuckles Chaotix 32X (USA)"),
]
for rom, cover in paare:
    check("%-40s = %s" % (rom[:40], cover[:34]),
          A.vergleichsname(rom) == A.vergleichsname(cover),
          "%r vs %r" % (A.vergleichsname(rom), A.vergleichsname(cover)))

print()
print("Test 2: verschiedene Spiele bleiben verschieden")
# Der eigentliche Preis des unscharfen Vergleichs waere, wenn er zu
# viel zusammenwirft. Diese Paare MUESSEN auseinanderbleiben.
getrennt = [
    ("Super Mario 64 (U) [!]", "Super Mario World (USA)"),
    ("Mortal Kombat (USA)", "Mortal Kombat II (USA)"),
    ("Zelda - Ocarina of Time (USA)", "Zelda - Majora's Mask (USA)"),
    ("F-Zero X (USA)", "F-Zero (USA)"),
]
for a, b in getrennt:
    check("%-32s != %s" % (a[:32], b[:30]),
          A.vergleichsname(a) != A.vergleichsname(b),
          A.vergleichsname(a))

print()
print("Test 3: Sonderfaelle des Vergleichsnamens")
check("Klammern verschwinden mitsamt Inhalt",
      A.vergleichsname("Spiel (USA) (Rev A) [!]") == "SPIEL",
      A.vergleichsname("Spiel (USA) (Rev A) [!]"))
check("Satzzeichen verschwinden",
      A.vergleichsname("Knuckles' Chaotix - 32X!") == "KNUCKLESCHAOTIX32X",
      A.vergleichsname("Knuckles' Chaotix - 32X!"))
check("verschachtelte Klammern",
      A.vergleichsname("Spiel (USA (Rev)) Extra") == "SPIELEXTRA",
      A.vergleichsname("Spiel (USA (Rev)) Extra"))
check("eine Klammer ohne Ende frisst nicht den Rest",
      A.vergleichsname("Spiel )USA( Extra") == "SPIELUSA",
      A.vergleichsname("Spiel )USA( Extra"))
check("ein Name, der nur aus Klammern besteht, ergibt nichts",
      A.vergleichsname("(USA)") == "", A.vergleichsname("(USA)"))
check("Umlaute bleiben erhalten",
      A.vergleichsname("Grün (D)") == "GRÜN", A.vergleichsname("Grün (D)"))

print()
print("Test 4: der exakte Name gewinnt IMMER")
tmp = tempfile.mkdtemp(prefix="namen_")
_alt_docs = A.DOCS_BASE
try:
    A.DOCS_BASE = os.path.join(tmp, "keine_docs")
    eigen = os.path.join(tmp, "art_hd")
    os.makedirs(os.path.join(eigen, "N64"))
    # Zwei Dateien, die denselben Vergleichsnamen ergeben, und eine
    # davon heisst exakt wie das ROM.
    for f in ("Spiel (U) [!].art", "Spiel (USA).art",
              "007 - The World Is Not Enough (USA).art"):
        open(os.path.join(eigen, "N64", f), "wb").write(b"ART1")
    A.docs_caches_leeren()
    A._art_index_cache.clear()
    p = A._art_path_in(eigen, "N64", "Spiel (U) [!]")
    check("exakter Treffer wird genommen",
          os.path.basename(p) == "Spiel (U) [!].art", p)
    p = A._art_path_in(eigen, "N64", "007 - The World is Not Enough (U) [!]")
    check("sonst der unscharfe Treffer",
          os.path.basename(p) == "007 - The World Is Not Enough (USA).art", p)
    p = A._art_path_in(eigen, "N64", "Voellig Anderes Spiel (U)")
    check("und ohne jeden Treffer der bisherige Rueckfall",
          p.endswith("Voellig Anderes Spiel (U).art"), p)
    # Bei zwei gleichwertigen Kandidaten muss die Wahl STABIL sein -
    # os.listdir() liefert keine verlaessliche Reihenfolge.
    erste = A._art_path_in(eigen, "N64", "Spiel [!]")
    for _ in range(5):
        A._art_index_cache.clear()
        check2 = A._art_path_in(eigen, "N64", "Spiel [!]")
        if check2 != erste:
            erste = None
            break
    check("bei mehreren Kandidaten immer derselbe", erste is not None,
          "%s" % (os.path.basename(erste) if erste else "wechselt!"))

    print()
    print("Test 5: auch die fremde Datenbank findet anders benannte ROMs")
    docs = os.path.join(tmp, "docs")
    os.makedirs(os.path.join(docs, "N64", "Artwork"))
    open(os.path.join(docs, "N64", "Artwork",
                      "Blast Corps (USA).jpg"), "wb").write(b"x")
    with open(os.path.join(docs, "N64", "Artwork", "gameinfo.tsv"),
              "w", encoding="utf-8") as fh:
        fh.write("#key\tname\tyear\tgenre\tdeveloper\tplayers\n")
        fh.write("Blast Corps (USA)\tBlast Corps\t1997\tAction\tRare\t1\n")
    A.DOCS_BASE = docs
    A.docs_caches_leeren()
    check("Cover trotz GoodTools-Namen gefunden",
          A.docs_cover("N64", "Blast Corps (U) [!]") is not None)
    check("und die Spieledaten ebenso",
          A.docs_meta("N64", "Blast Corps (U) [!]").get("year") == "1997",
          "%r" % (A.docs_meta("N64", "Blast Corps (U) [!]"),))
    check("was es nicht gibt, gibt es weiterhin nicht",
          A.docs_cover("N64", "Gibt Es Nicht (U)") is None)
finally:
    A.DOCS_BASE = _alt_docs
    A.docs_caches_leeren()
    A._art_index_cache.clear()
    shutil.rmtree(tmp, ignore_errors=True)

print()
print("Test 6: spaet angelaufenes Laufwerk wird bemerkt")
# Ohne vorheriges Einlesen darf NICHTS ausgeloest werden - sonst
# zoege das Frontend beim allerersten Start sofort nach.
S._LETZTE_ORDNER = set()
check("ohne vorheriges Einlesen passiert nichts",
      S.ordner_sind_dazugekommen() is False)

S.ordner_merken([("usb:SNES", 111), ("fat:NES", 222),
                 ("__scan_logic_version__", 3)])
check("die Sondereintraege stehen nicht im Merker",
      all(":" in k for k in S._LETZTE_ORDNER), "%r" % (S._LETZTE_ORDNER,))
check("aber die echten Ordner schon",
      S._LETZTE_ORDNER == {"usb:SNES", "fat:NES"}, "%r" % (S._LETZTE_ORDNER,))

echt = S._games_signature
try:
    S._games_signature = lambda: ([("usb:SNES", 999), ("fat:NES", 222)], {})
    check("ein NEUER Zeitstempel allein loest nichts aus",
          S.ordner_sind_dazugekommen() is False)
    S._games_signature = lambda: ([("usb:SNES", 111)], {})
    check("ein WEGGEFALLENER Ordner loest auch nichts aus",
          S.ordner_sind_dazugekommen() is False)
    S._games_signature = lambda: ([("usb:SNES", 111), ("fat:NES", 222),
                                   ("usb:N64", 333)], {})
    check("ein DAZUGEKOMMENER Ordner loest aus",
          S.ordner_sind_dazugekommen() is True)
    # Die Abfrage darf den NAS-Merker nicht ueberschreiben - er
    # beschreibt das letzte echte Einlesen, nicht diese Zwischenfrage.
    S._LETZTE_SIGNATUR_MIT_NAS = True
    S._games_signature = lambda: ([("usb:SNES", 111)], {})
    S.ordner_sind_dazugekommen()
    check("der NAS-Merker bleibt unangetastet",
          S.letzter_scan_hatte_nas() is True)
    S._LETZTE_SIGNATUR_MIT_NAS = False
    # Und ein Fehler beim Nachsehen darf nichts umwerfen.
    def _kaputt():
        raise OSError("Laufwerk weg")
    S._games_signature = _kaputt
    check("ein Fehler beim Nachsehen wirft nichts um",
          S.ordner_sind_dazugekommen() is False)
finally:
    S._games_signature = echt
    S._LETZTE_ORDNER = set()

print()
print("Test 7: das Sicherheitsnetz benutzt es auch")
quelle = open(os.path.join(_REPO, "frontend", "frontend.py"),
              encoding="utf-8", errors="replace").read()
check("die Abfrage ist verdrahtet",
      "elif ordner_sind_dazugekommen():" in quelle)
check("der Netzlaufwerk-Weg bleibt bestehen",
      "if _has_network_mount():" in quelle
      and "letzter_scan_hatte_nas():" in quelle)
check("und beide muenden in denselben einmaligen Nachzug",
      quelle.count("self._late_mount_rescan_pending = True") >= 2
      and "self._late_mount_rescan_done = True\n        self."
          "_rebuild_categories_preserving_selection(force_rescan=True)"
          in quelle)
skript = open(os.path.join(_REPO, "frontend", "fe", "scan.py"),
              encoding="utf-8", errors="replace").read()
check("und der Merker wird beim Einlesen gesetzt",
      skript.count("ordner_merken(sig)") >= 3,
      "%d Stellen" % skript.count("ordner_merken(sig)"))

print()
if fails:
    print("FEHLGESCHLAGEN (%d):" % len(fails))
    for f_ in fails:
        print("  -", f_)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
