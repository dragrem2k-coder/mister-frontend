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


# ---------------------------------------------------------------------------
# MEHRTEILIGE SPIELE (Build 259)
# ---------------------------------------------------------------------------
def disc_geschwister(rom_pfad):
    """Alle Teile eines mehrteiligen Spiels - [(Marker, Pfad), ...],
    nach Disc-Nummer sortiert. Leere Liste, wenn es nur einen gibt.

    GESUCHT WIRD ERST BEIM STARTEN und nicht beim Einlesen. Das ist
    Absicht und spart die groesste Klippe: der Scan-Cache muesste
    sonst eine zusaetzliche Struktur mittragen, und bei einem
    zwischengespeicherten System waere sie nicht da. So kostet es
    EINEN os.listdir() - und nur bei einem Spiel, dessen Name
    ueberhaupt einen Disc-Marker traegt.

    KEIN SONDERFALL FUER ARCHIVE, und das ist der Grund, warum hier
    kein einziges Mal "Archiv" steht: ein Pfad, der durch eine
    Archivdatei laeuft, hat kein Verzeichnis zum Auflisten - os.listdir
    scheitert, und der Griff unten liefert eine leere Liste. Derselbe
    Griff deckt auch den Ordner ab, den gerade jemand weggezogen hat.
    Der ganze Startweg kommt ohne Archiv-Sonderbehandlung aus (ein Test
    besteht darauf, dass in dieser Datei das Wort fuer die Archivendung
    nirgends vorkommt), und das soll so bleiben. Zusammengefasst werden
    Teile in einem Archiv ohnehin nicht - siehe _discs_buendeln() in
    fe/scan.py."""
    from fe.naming import disc_basis, disc_marker, disc_rang
    if not rom_pfad:
        return []
    name = os.path.basename(rom_pfad)
    stamm, endung = os.path.splitext(name)
    if not disc_marker(stamm):
        return []
    ordner = os.path.dirname(rom_pfad)
    basis = disc_basis(stamm).lower()
    try:
        eintraege = os.listdir(ordner)
    except OSError:
        return []
    raus = []
    for e in eintraege:
        st, en = os.path.splitext(e)
        if en.lower() != endung.lower():
            continue
        if not disc_marker(st) or disc_basis(st).lower() != basis:
            continue
        raus.append((disc_marker(st), os.path.join(ordner, e), st))
    if len(raus) < 2:
        return []
    raus.sort(key=lambda t: disc_rang(t[2]))
    return [(m, p) for m, p, _st in raus]
