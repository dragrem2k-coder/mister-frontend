#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft, dass die neuen Kategorie-Abzeichen wirklich auf der Karte
ankommen (Build 101).

NUTZERFRAGE, aus der das hier entstanden ist: "Muss ich die alten
haendisch loeschen auf GitHub? Oder werden die alten ueberschrieben?"

Auf GitHub: ja, ueberschrieben. Auf der SD-KARTE war die Antwort NEIN -
und genau das war der Fehler. Alle drei Installer kopieren sysart mit
"cp -rn" bzw. mit einer eigenen "nur wenn nicht vorhanden"-Schleife,
damit selbst gemaltes Artwork bei einem erneuten Lauf nicht
verlorengeht. Richtig gedacht fuer einzelne Bilder - aber mit Build
99/100 wurden ALLE 57 Kategorie-Logos umgestellt. 42 davon tragen
denselben Dateinamen wie ein altes Logo und waeren nie angekommen.
Dieselbe Falle wie damals bei WOT.art ("immer noch das alte
Zufalls-Zock-Bild, auch nach Update UND Install"), nur 42-fach.

Dieser Test fuehrt die ECHTEN Shell-Bloecke aus den Installern aus -
nicht eine Nachbildung davon. Der sysart-Block wird aus der jeweiligen
Datei herausgeschnitten und gegen einen kuenstlichen "SD-Karten"-Ordner
laufen gelassen. Faellt der Block auf "nur ergaenzen" zurueck, schlaegt
der Test fehl.

Geprueft werden vier Dinge, die alle vier halten muessen:
  1. Beim ersten Lauf wird ein gleichnamiges altes Logo ersetzt.
  2. Die vier toten Vollbild-Dateien verschwinden (ein Kopiervorgang
     allein wuerde sie nie entfernen).
  3. Beim ZWEITEN Lauf bleibt eigenes Artwork unangetastet - die
     Ersetzung ist einmalig, nicht dauerhaft.
  4. Das Henne-Ei-Problem: beim Update laeuft zuerst noch der ALTE
     Installer von der Karte. Frontend_Update.sh startet die
     Installation deshalb genau einmal nach.

Ausfuehren:
    python3 tools/test_abzeichen_verteilung.py
"""
import os
import shutil
import subprocess
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
SCRIPTS = os.path.join(_REPO, "Scripts")

TOTE_DATEIEN = [
    "SMW_HACKS_1920x1080.art",
    "SMW_HACKS_320x240.art",
    "SNES_ALTTP_TRACKER_1920x1080.art",
    "SNES_ALTTP_TRACKER_320x240.art",
]

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


def block_ausschneiden(pfad, start_pruefung):
    """Holt einen echten if-Block aus einem Shell-Skript heraus.

    Bewusst ueber die Einrueckung: der Block beginnt mit einem "if" am
    Zeilenanfang und endet beim ersten "fi", das ebenfalls ganz links
    steht. Alles dazwischen gehoert dazu, egal wie tief verschachtelt.
    """
    zeilen = open(pfad, encoding="utf-8").read().split("\n")
    anfang = None
    for i, z in enumerate(zeilen):
        if start_pruefung(z):
            anfang = i
            break
    if anfang is None:
        raise LookupError("Blockanfang nicht gefunden in %s" % pfad)
    for j in range(anfang + 1, len(zeilen)):
        if zeilen[j] == "fi":
            return "\n".join(zeilen[anfang:j + 1])
    raise LookupError("Blockende nicht gefunden in %s" % pfad)


def karte_bauen(wurzel):
    """Legt eine kuenstliche SD-Karte und ein Quell-Repo an."""
    quelle = os.path.join(wurzel, "quelle", "frontend", "sysart")
    ziel = os.path.join(wurzel, "karte", "sysart")
    os.makedirs(quelle)
    os.makedirs(ziel)

    # Im Repo: ein gleichnamiges Abzeichen (neu), ein zusaetzliches.
    open(os.path.join(quelle, "NES.art"), "w").write("NEUES-ABZEICHEN")
    open(os.path.join(quelle, "GAMATE.art"), "w").write("NEU-DAZU")
    open(os.path.join(quelle, "WOT.art"), "w").write("NEU-WOT")

    # Auf der Karte: das alte Logo, eigenes Artwork, die vier Leichen.
    open(os.path.join(ziel, "NES.art"), "w").write("ALTES-LOGO")
    open(os.path.join(ziel, "WOT.art"), "w").write("ALT-WOT")
    for t in TOTE_DATEIEN:
        open(os.path.join(ziel, t), "w").write("TOT")
    return os.path.join(wurzel, "quelle"), os.path.join(wurzel, "karte")


def block_laufen_lassen(block, quelle, karte):
    """Fuehrt den herausgeschnittenen Block wie im Installer aus."""
    kopf = (
        "set -u\n"
        "SRC_DIR=%s\n"
        "SRC=%s\n"
        "FRONTEND_DIR=%s\n"
        "say() { :; }\n"
        "step() { :; }\n"
    ) % (shquote(quelle), shquote(quelle), shquote(karte))
    p = subprocess.run(["bash", "-c", kopf + block],
                       capture_output=True, text=True)
    return p


def shquote(s):
    return "'" + s.replace("'", "'\\''") + "'"


def lies(pfad):
    try:
        return open(pfad, encoding="utf-8").read()
    except OSError:
        return None


INSTALLER = [
    ("Frontend_Install.sh", lambda z: z.startswith('if [ -d "$SRC_DIR/frontend/sysart" ]; then')),
    ("Frontend_Install_Remote.sh", lambda z: z.startswith('if [ -d "$SRC_DIR/frontend/sysart" ]; then')),
    ("Frontend_Install_Offline.sh", lambda z: z.startswith('if [ -d "$SRC/frontend/sysart" ]; then')),
]

print("Test 1: erster Lauf ersetzt die alten Logos und raeumt auf")
for name, pruef in INSTALLER:
    pfad = os.path.join(SCRIPTS, name)
    block = block_ausschneiden(pfad, pruef)
    tmp = tempfile.mkdtemp(prefix="abz_")
    try:
        quelle, karte = karte_bauen(tmp)
        p = block_laufen_lassen(block, quelle, karte)
        sysart = os.path.join(karte, "sysart")
        check("%-28s Block laeuft fehlerfrei" % name, p.returncode == 0,
              p.stderr.strip()[:200])
        check("%-28s gleichnamiges Logo ersetzt" % name,
              lies(os.path.join(sysart, "NES.art")) == "NEUES-ABZEICHEN",
              "ist: %r" % lies(os.path.join(sysart, "NES.art")))
        check("%-28s neues Abzeichen kam an" % name,
              lies(os.path.join(sysart, "GAMATE.art")) == "NEU-DAZU")
        uebrig = [t for t in TOTE_DATEIEN
                  if os.path.exists(os.path.join(sysart, t))]
        check("%-28s die vier toten Dateien sind weg" % name,
              not uebrig, "noch da: %s" % uebrig)
        check("%-28s Marke gesetzt" % name,
              os.path.isfile(os.path.join(sysart, ".abzeichen_v1")))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

print("Test 2: der zweite Lauf laesst eigenes Artwork in Ruhe")
# Die Ersetzung ist ausdruecklich EINMALIG. Wer sich nach der Umstellung
# ein eigenes Abzeichen malt, darf es beim naechsten Update nicht wieder
# verlieren - sonst haetten wir nur die alte Falle in die andere
# Richtung aufgestellt.
for name, pruef in INSTALLER:
    pfad = os.path.join(SCRIPTS, name)
    block = block_ausschneiden(pfad, pruef)
    tmp = tempfile.mkdtemp(prefix="abz2_")
    try:
        quelle, karte = karte_bauen(tmp)
        block_laufen_lassen(block, quelle, karte)          # 1. Lauf
        sysart = os.path.join(karte, "sysart")
        open(os.path.join(sysart, "NES.art"), "w").write("MEIN-EIGENES")
        block_laufen_lassen(block, quelle, karte)          # 2. Lauf
        check("%-28s eigenes Artwork bleibt" % name,
              lies(os.path.join(sysart, "NES.art")) == "MEIN-EIGENES",
              "ist: %r" % lies(os.path.join(sysart, "NES.art")))
        # WOT.art ist die eine namentlich gepflegte Ausnahme (siehe
        # Kommentar im Installer) - die wird bewusst IMMER ersetzt.
        check("%-28s WOT bleibt die gepflegte Ausnahme" % name,
              lies(os.path.join(sysart, "WOT.art")) == "NEU-WOT")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

print("Test 3: Henne-Ei - Frontend_Update.sh startet genau einmal nach")
# Beim Update laeuft zuerst der ALTE Installer von der Karte. Der legt
# den neuen Installer UND die neue Frontend_Update.sh ab und uebergibt
# dann per exec an letztere - ab da laeuft neuer Code, obwohl der
# Installer selbst noch der alte war. Genau dort greift der Nachlauf.
nach_block = block_ausschneiden(
    os.path.join(SCRIPTS, "Frontend_Update.sh"),
    lambda z: z.startswith('ABZEICHEN_MARKE='))


def nachlauf_lauf(wurzel, installer_text, marke, stempel):
    karte = os.path.join(wurzel, "karte")
    skripte = os.path.join(wurzel, "Scripts")
    os.makedirs(os.path.join(karte, "sysart"), exist_ok=True)
    os.makedirs(skripte, exist_ok=True)
    inst = os.path.join(skripte, "Frontend_Install.sh")
    open(inst, "w").write(installer_text)
    if marke:
        open(os.path.join(karte, "sysart", ".abzeichen_v1"), "w").write("")
    st = os.path.join(wurzel, "stempel")
    if stempel:
        open(st, "w").write("")
    kopf = (
        "set -u\n"
        "FRONTEND_DIR=%s\n"
        "SCRIPTS_DIR=%s\n"
    ) % (shquote(karte), shquote(skripte))
    # Der Stempel liegt im Original unter /tmp - hier umgebogen, damit
    # der Test nichts ausserhalb seines Ordners anfasst.
    block = nach_block.replace('ABZEICHEN_STEMPEL="/tmp/abzeichen_nachlauf"', "")
    kopf += "ABZEICHEN_STEMPEL=%s\n" % shquote(st)
    p = subprocess.run(["bash", "-c", kopf + block + "\necho KEIN-NACHLAUF"],
                       capture_output=True, text=True)
    return p.stdout + p.stderr


NEUER_INSTALLER = '#!/bin/bash\n# enthaelt .abzeichen_v1\necho NACHLAUF\n'
ALTER_INSTALLER = '#!/bin/bash\necho NACHLAUF\n'

faelle = [
    ("Marke fehlt, Installer ist neu  -> nachstarten",
     NEUER_INSTALLER, False, False, "NACHLAUF"),
    ("Marke vorhanden                 -> nichts tun",
     NEUER_INSTALLER, True, False, "KEIN-NACHLAUF"),
    ("Installer noch alt              -> nichts tun",
     ALTER_INSTALLER, False, False, "KEIN-NACHLAUF"),
    ("schon einmal nachgestartet      -> nichts tun",
     NEUER_INSTALLER, False, True, "KEIN-NACHLAUF"),
]
for label, inst, marke, stempel, erwartet in faelle:
    tmp = tempfile.mkdtemp(prefix="abz3_")
    try:
        aus = nachlauf_lauf(tmp, inst, marke, stempel)
        check(label, erwartet in aus, "Ausgabe: %r" % aus.strip()[-60:])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

print("Test 4: der Nachlauf-Block behaelt alle drei Bremsen")
# Faellt auch nur eine davon weg, kann aus dem einmaligen Nachlauf eine
# Schleife werden - deshalb hier namentlich festgehalten.
quelle = open(os.path.join(SCRIPTS, "Frontend_Update.sh"),
              encoding="utf-8").read()
check("Bremse 1: Stempel unter /tmp",
      '/tmp/abzeichen_nachlauf' in quelle)
check("Bremse 2: nur mit Installer, der die Marke kennt",
      'grep -qF ".abzeichen_v1"' in quelle)
check("Bremse 3: nur wenn sysart ueberhaupt existiert",
      'if [ -d "$FRONTEND_DIR/sysart" ]' in quelle)

print()
if fails:
    print("FEHLGESCHLAGEN (%d):" % len(fails))
    for f_ in fails:
        print("  -", f_)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
