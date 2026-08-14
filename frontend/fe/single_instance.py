#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Single-Instance-Lock: verhindert, dass zwei Instanzen gleichzeitig
/dev/fb0 mappen und die Eingabegeraete grabben. Die Lock-Datei enthaelt
die PID, damit sie - wie in der README beschrieben - per
"kill $(cat /tmp/frontend.lock)" beendet werden kann (pkill/pgrep gibt
es auf dem MiSTer nicht). Ausgelagert aus frontend.py (Modularisierung,
Git-Branch 'modular-refactor').
"""
import os, sys
from fe.log import LOG

# ----------------------------------------------------------------------------
# SINGLE-INSTANCE-LOCK
# Verhindert, dass zwei Instanzen gleichzeitig /dev/fb0 mappen und die
# Eingabegeraete grabben. Die Lock-Datei enthaelt die PID, damit sie -
# wie in der README beschrieben - per "kill $(cat /tmp/frontend.lock)"
# beendet werden kann. pkill/pgrep gibt es auf dem MiSTer nicht.
# ----------------------------------------------------------------------------

LOCKFILE = "/tmp/frontend.lock"

def _pid_alive(pid):
    """True, wenn die PID existiert UND es sich nachweislich um unseren
    eigenen frontend.py-Prozess handelt - nicht nur irgendeinen
    Prozess, der zufaellig dieselbe Nummer hat.

    BUGFIX (Nutzer-Rueckmeldung: nach einem "Soft Reset" - vermutlich
    OHNE echten Linux-Kernel-Neustart, im Gegensatz zu einem echten
    Stromzyklus - kommt das Frontend manchmal nicht wieder, MiSTer
    bleibt im eigenen OSD haengen, OHNE jede Log-Zeile): reine "existiert
    die PID"-Pruefung (os.kill(pid, 0)) reicht nicht aus, wenn /tmp
    (und damit unsere Lock-Datei) einen Soft-Reset UEBERLEBT - Linux
    vergibt PID-Nummern nach einer Weile wieder neu, ein voellig
    unabhaengiger, neuer Prozess koennte zufaellig dieselbe Nummer wie
    der alte (laengst beendete) Frontend-Prozess bekommen haben. Die
    Sperrdatei-Pruefung haette das dann faelschlicherweise als "laeuft
    noch" gewertet und den Neustart stillschweigend verweigert - kein
    Absturz, keine Logzeile, einfach nichts (passt zum gemeldeten Bild).
    Fix: zusaetzlich pruefen, ob /proc/<pid>/cmdline tatsaechlich
    "frontend.py" enthaelt. Ist /proc nicht lesbar (sollte auf MiSTer
    nicht vorkommen), faellt die Funktion sicherheitshalber auf das
    alte Verhalten zurueck (PID existiert -> als lebendig werten),
    statt einen falschen Negativ-Befund zu riskieren."""
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    try:
        with open("/proc/%d/cmdline" % pid, "rb") as f:
            cmdline = f.read()
    except OSError:
        return True   # /proc nicht lesbar - alte, vorsichtige Annahme beibehalten
    return b"frontend.py" in cmdline

def acquire_single_instance():
    """True, wenn wir die einzige Instanz sind (Lock gesetzt). False,
    wenn bereits eine LEBENDE Instanz laeuft. Eine verwaiste Lock-Datei
    (Prozess existiert nicht mehr, z.B. nach Absturz) wird uebernommen."""
    try:
        with open(LOCKFILE) as f:
            old = f.read().strip()
        if old.isdigit() and _pid_alive(int(old)):
            LOG("Bereits aktive Instanz (PID %s) - Abbruch." % old)
            return False
    except OSError:
        pass
    try:
        with open(LOCKFILE, "w") as f:
            f.write(str(os.getpid()))
    except OSError as e:
        LOG("Lock-Datei nicht schreibbar: %s" % e)
    return True

def release_single_instance():
    try:
        with open(LOCKFILE) as f:
            mine = f.read().strip() == str(os.getpid())
        if mine:
            os.remove(LOCKFILE)
    except OSError:
        pass
