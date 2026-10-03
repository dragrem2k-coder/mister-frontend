#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Der gemeinsame Dateibaum von Masken und Schriften (Build 228).

WARUM ES DIESES MODUL UND DIESEN TEST GIBT. Build 227 hat die Lochmasken
in Ordnern gezeigt, statt 1207 Dateien in eine Liste zu kippen. Der
Nutzer hat daraufhin gesagt: "das was wir mit masken gemacht haben
sollte auch mit denn fonts also der schrift passieren."

Damit gibt es zwei Sammlungen mit derselben Aufgabe. Zwei Stellen, die
dasselbe tun, laufen auseinander - nicht sofort, aber beim dritten Mal,
wenn jemand die eine um eine Kleinigkeit erweitert und die andere
vergisst. Also steht das Blaettern EINMAL in fe/dateibaum.py.

WAS HIER GEPRUEFT WIRD, ist deshalb nicht nur "es listet Dateien",
sondern die vier Entscheidungen, die den Baum brauchbar machen:

  1. ORDNER VORN, und jeder sagt, wieviel darin liegt. Einen Ordner
     blind zu waehlen ist genau das Blaettern, das abgeschafft werden
     sollte.
  2. LEERE ORDNER FALLEN WEG. Beide Sammlungen haben welche (Vorlagen,
     Lesetexte, Bilder) - sie waeren Sackgassen.
  3. DER WEG ZURUECK endet an der Wurzel und laeuft nicht darueber
     hinaus. Wer in einen Ordner hineinkommt und nicht wieder heraus,
     ist schlechter dran als mit der langen Liste.
  4. EIN FEHLER ENDET IN EINER LEEREN LISTE. Ein Ordner, den es nicht
     gibt, ein Lesefehler - nichts davon darf ein Frontend aufhalten,
     das eigentlich Spiele starten soll.

Ausfuehren:
    python3 tools/test_dateibaum.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H          # noqa: E402,F401

import fe.dateibaum as B      # noqa: E402
import fe.masken as M         # noqa: E402
import fe.schriften as S      # noqa: E402

fails = []


def check(name, ok, info=""):
    print(("  OK   " if ok else "  FEHL ") + name
          + (("  " + info) if info else ""))
    if not ok:
        fails.append(name)


def baum_bauen(wurzel, pfade, inhalt="x"):
    for rel in pfade:
        voll = os.path.join(wurzel, rel)
        os.makedirs(os.path.dirname(voll), exist_ok=True)
        open(voll, "w").write(inhalt)


# ---------------------------------------------------------------------------
print("Test 1: eine Ebene - Ordner vorn, mit Anzahl")
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    baum_bauen(tmp, (
        "Complex/CRT Styles/Sony PVM.txt",
        "Complex/CRT Styles/Commodore 1084.txt",
        "Complex/Fein/Aperture.txt",
        "Simple/Scanlines.txt",
        "Direkt.txt",
        "Zweite.txt",
        "Nur Bilder/vorschau.png",
        "Lies mich.md",
    ))
    wurzel = B.eintraege(tmp, "", ".txt")
    check("Ordner stehen vorn, Dateien dahinter",
          [e[0] for e in wurzel] == [True, True, False, False],
          "%r" % ([(e[0], e[1]) for e in wurzel],))
    check("beides fuer sich alphabetisch",
          [e[1] for e in wurzel] == ["Complex", "Simple",
                                     "Direkt", "Zweite"],
          "%r" % ([e[1] for e in wurzel],))
    check("ein Ordner sagt, wieviel darin liegt - REKURSIV",
          wurzel[0][3] == 3, "Complex hat 3, gemeldet %r" % (wurzel[0][3],))
    check("ein Ordner OHNE passende Datei faellt weg",
          all(e[1] != "Nur Bilder" for e in wurzel),
          "sonst laeuft man in eine Sackgasse")
    check("und eine Datei mit falscher Endung ebenso",
          all(e[1] != "Lies mich" for e in wurzel))
    check("der Anzeigename traegt die Endung nicht",
          wurzel[2][1] == "Direkt", wurzel[2][1])
    check("der Pfad ist RELATIV zur Wurzel",
          wurzel[2][2] == "Direkt.txt", wurzel[2][2])

    tiefer = B.eintraege(tmp, "Complex", ".txt")
    check("eine Ebene tiefer stehen die Unterordner",
          [e[1] for e in tiefer] == ["CRT Styles", "Fein"],
          "%r" % ([e[1] for e in tiefer],))
    check("und ihr Pfad traegt den Weg mit",
          tiefer[0][2] == os.path.join("Complex", "CRT Styles"),
          tiefer[0][2])

    # ---------------------------------------------------------------
    print()
    print("Test 2: DIE ENDUNG entscheidet, und zwar ohne Gross/Klein")
    # ---------------------------------------------------------------
    baum_bauen(tmp, ("Gross/ARCADE.PF", "Gross/klein.pf"))
    pf = B.eintraege(tmp, "Gross", ".pf")
    check("beide Schreibweisen zaehlen",
          [e[1] for e in pf] == ["ARCADE", "klein"],
          "%r" % ([e[1] for e in pf],))
    check("und dieselbe Wurzel liefert mit .txt nichts davon",
          B.eintraege(tmp, "Gross", ".txt") == [])
    check("zaehlen() zaehlt dieselbe Endung",
          B.zaehlen(os.path.join(tmp, "Gross"), ".pf") == 2)

    # ---------------------------------------------------------------
    print()
    print("Test 3: DER WEG ZURUECK endet an der Wurzel")
    # ---------------------------------------------------------------
    check("zwei Ebenen -> eine",
          B.oberordner(os.path.join("Complex", "CRT Styles")) == "Complex")
    check("eine Ebene -> Wurzel", B.oberordner("Complex") == "")
    check("und ueber die Wurzel hinaus geht es nicht",
          B.oberordner("") == "")
    check("auch ein Schraegstrich am Ende aendert daran nichts",
          B.oberordner("Complex" + os.sep) == "")
    check("eine virtuelle Ebene fuehrt immer zur Wurzel",
          B.oberordner(B.VIRTUELL + "presets") == "")
    check("und ihr Name kann mit keinem Ordner kollidieren",
          B.VIRTUELL not in "".join(e[2] for e in wurzel),
          "ein Nullbyte steht in keinem Dateinamen")

    # ---------------------------------------------------------------
    print()
    print("Test 4: fertige Zeilen - mit Kopf nur auf der Wurzel")
    # ---------------------------------------------------------------
    TEXTE = {"zurueck": "zurueck"}
    KOPF = [("keine", "keine", "")]
    oben = B.zeilen(tmp, "", ".txt", TEXTE, KOPF)
    check("der Kopf steht ganz oben", oben[0][0] == "keine")
    check("und KEIN Weg nach oben, wo keiner hinfuehrt",
          all(e[0] != "hoch" for e in oben))
    unten = B.zeilen(tmp, "Complex", ".txt", TEXTE, KOPF)
    check("eine Ebene tiefer steht der Weg zurueck", unten[0][0] == "hoch")
    check("und der Kopf NICHT mehr",
          all(e[0] != "keine" for e in unten),
          "'keine' gehoert auf die Wurzel, nicht in jeden Ordner")
    check("ein Ordner zeigt seine Anzahl in der Beschriftung",
          "(2)" in [e[1] for e in unten if e[0] == "ordner"][0],
          "%r" % ([e[1] for e in unten],))
    check("eine Datei steht ohne Schmuck da",
          [e[1] for e in B.zeilen(tmp, "Complex/CRT Styles", ".txt",
                                  TEXTE, KOPF) if e[0] == "datei"]
          == ["Commodore 1084", "Sony PVM"])

# ---------------------------------------------------------------------------
print()
print("Test 5: ein Fehler endet in einer leeren Liste, nie in einem Absturz")
# ---------------------------------------------------------------------------
check("ein Ordner, den es nicht gibt",
      B.eintraege("/gibt/es/ganz/sicher/nicht", "", ".txt") == [])
check("ein Unterordner, den es nicht gibt",
      B.eintraege("/tmp", "gibt/es/nicht", ".txt") == [])
check("zaehlen() auf nichts", B.zaehlen("/gibt/es/nicht", ".txt") == 0)
check("und zeilen() liefert dann nur den Kopf",
      B.zeilen("/gibt/es/nicht", "", ".txt", {}, [("keine", "keine", "")])
      == [("keine", "keine", "")])
with tempfile.TemporaryDirectory() as tmp:
    # Eine DATEI dort, wo ein Ordner erwartet wird.
    datei = os.path.join(tmp, "keinordner.txt")
    open(datei, "w").write("x")
    check("eine Datei als Wurzel", B.eintraege(datei, "", ".txt") == [])

# ---------------------------------------------------------------------------
print()
print("Test 6: BEIDE Sammlungen benutzen wirklich diesen Baum")
# ---------------------------------------------------------------------------
# Der eigentliche Zweck des Moduls. Gaebe es daneben noch eine zweite,
# eigene Implementierung, waere nichts gewonnen - deshalb wird hier
# nachgesehen, dass beide Module es importieren UND keine eigene
# os.listdir-Schleife mehr haben.
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for modul in ("masken", "schriften"):
    quelle = open(os.path.join(_REPO, "frontend", "fe", modul + ".py"),
                  encoding="utf-8").read()
    check("fe/%s.py benutzt den Baum" % modul,
          "import fe.dateibaum as BAUM" in quelle)
    check("und hat keine eigene Ordnerschleife mehr" + " " * len(modul),
          "os.listdir" not in quelle.split("def preset_masken")[0],
          "zwei Wege in dieselbe Sammlung sind einer zuviel")

check("die Masken nehmen .txt", M.masken_eintraege("", "/gibt/es/nicht") == [])
check("die Schriften nehmen .pf", S.ENDUNG == ".pf")
check("und jede ihren eigenen Ordner",
      M.MASKEN_DIR == "/media/fat/Shadow_Masks"
      and S.SCHRIFTEN_DIR == "/media/fat/font")

print()
if fails:
    print("FEHLGESCHLAGEN (%d):" % len(fails))
    for f in fails:
        print("  - %s" % f)
    sys.exit(1)
print("Alles in Ordnung.")
