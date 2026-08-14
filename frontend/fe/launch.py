#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Core-Start-Hilfsfunktionen: MGL-Startdatei erzeugen (write_mgl),
Scripts-Ordner auflisten (scan_scripts), aktuell laufenden Core
abfragen/wechseln (current_core/launch_core). Ausgelagert aus
frontend.py (Modularisierung, Git-Branch 'modular-refactor').

SCRIPTS_DIR hier bewusst noch einmal definiert (nicht importiert) -
wird auch von der Frontend-Klasse selbst gebraucht (run_script()-
Aufrufe), ein Ruecksfall-Import haette einen Zirkelbezug ausgeloest
(frontend.py laeuft als Hauptskript, nicht als benanntes,
importierbares Modul). Fester Pfad, kein Synchronisierungsrisiko.
"""
import os, glob

SCRIPTS_DIR = "/media/fat/Scripts"
MGL_TMP     = "/tmp/frontend_launch.mgl"
CORENAME    = "/tmp/CORENAME"
MISTER_CMD  = "/dev/MiSTer_cmd"

def write_mgl(rbf, rom_path, delay, ftype, index, setname=None):
    """MGL-Startdatei erzeugen (Pfad-Konvention wie in mrext).
    setname (optional): fuer RA-Cores noetig (siehe find_ra_core()) -
    <setname same_dir="1">...</setname> zwischen <rbf> und <file>,
    exakt wie in einer echten .mgl-Datei von sage2050s Werkzeug
    verifiziert."""
    setname_xml = ('\t<setname same_dir="1">%s</setname>\n' % setname) \
        if setname else ""
    xml = ('<mistergamedescription>\n'
           '\t<rbf>%s</rbf>\n'
           '%s'
           '\t<file delay="%d" type="%s" index="%d" '
           'path="../../../../..%s"/>\n'
           '</mistergamedescription>\n'
           % (rbf, setname_xml, delay, ftype, index, rom_path))
    with open(MGL_TMP, "w") as f:
        f.write(xml)
    return MGL_TMP

def scan_scripts():
    items = []
    for f in sorted(glob.glob(os.path.join(SCRIPTS_DIR, "*.sh"))):
        name = os.path.splitext(os.path.basename(f))[0].replace("_", " ")
        items.append((name, "script", f))
    return items

def current_core():
    try:
        return open(CORENAME).read().strip("\x00 \n\r\t")
    except OSError:
        return ""

def launch_core(path):
    with open(MISTER_CMD, "w") as f:
        f.write("load_core " + path)
