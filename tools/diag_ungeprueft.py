#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DIAGNOSE (kein Pass/Fail): welche Funktionen betritt KEIN Test?

    python3 tools/diag_ungeprueft.py sammeln      # Suite mit Spur, dauert
    python3 tools/diag_ungeprueft.py              # auswerten
    python3 tools/diag_ungeprueft.py 50           # auswerten, Top 50

WARUM ES DAS GIBT, und der Anlass ist unangenehm. Zweimal in zwei Tagen
hat dieselbe Luecke zugeschlagen:

  * Build 248: scan_games() - die Funktion, die die KOMPLETTE
    Spieleliste baut - war halb umgebaut und warf einen NameError.
    Kein einziger Test hatte sie je aufgerufen.
  * Build 247: die Ziehung in Zufalls-Zock rief read_action() ohne
    Zeitangabe und blieb damit stehen. Der Test hatte read_action
    durch eine Attrappe ersetzt - der echte Aufruf wurde nie gegangen.

DER ERSTE ENTWURF DIESES SKRIPTS HAT BEIDE DURCHGELASSEN, und das ist
der Grund, warum es jetzt anders gebaut ist. Er suchte die Namen im
Text von tools/ und fand:

    scan_games     Programm   8, Tests  16
    read_action    Programm  41, Tests  33

Beide Namen stehen reichlich in den Tests. Nur gerufen wurde die ECHTE
Funktion nie - einmal nur beschrieben, einmal durch eine Attrappe
ersetzt. Eine Liste, die ihre eigenen Anlassfaelle durchlaesst, ist
keine Liste, sondern eine Beruhigung.

GEMESSEN WIRD DESHALB, WAS WIRKLICH LAEUFT: jede Testdatei laeuft
unter sys.setprofile (siehe tools/_spur.py), und aufgeschrieben wird
jede Funktion, die dabei BETRETEN wurde - auch in Nebenfaeden. Kein
Fremdpaket; dafuer dauert der Sammellauf ein Mehrfaches der Suite.

GEWICHT ist die Zahl der Nennungen im Programmtext (ohne die
Definition selbst): je hoeher, desto zentraler die Funktion, und desto
unangenehmer, dass kein Test sie betritt.

WAS DIE LISTE NICHT IST: ein Urteil. Manches gehoert mit Recht nicht
in einen Test (Abschalten des Geraets, Neustart, der Installer).
Manches ist nur ueber echte Hardware erreichbar. Die Liste nennt
Kandidaten; welche davon einen Test bekommen, bleibt eine
Entscheidung.
"""
import io
import os
import re
import subprocess
import sys
import time

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_FRONTEND = os.path.join(_REPO, "frontend")
_TOOLS = os.path.join(_REPO, "tools")
SPUR = os.environ.get("DRAGEND_SPUR",
                      os.path.join(_TOOLS, "__spur_ungeprueft.txt"))

# Namen, bei denen die Zaehlung nichts aussagt: zu kurz, oder so
# allgemein, dass das Gewicht nur Rauschen ist.
UNINTERESSANT = {"main", "run", "get", "put", "key", "name", "path"}

# Was mit Absicht ungeprueft bleibt - und WARUM. Ohne diese Liste
# steht derselbe Posten bei jedem Lauf wieder oben, und man liest
# darueber hinweg; mit ihr steht die Begruendung dabei.
MIT_ABSICHT = {
    "reboot": "faehrt das Geraet neu - in einem Test nicht lustig",
    "shutdown_mister": "schaltet das Geraet ab",
    "_mister_ini_schreiben": "schreibt in MiSTer.ini, fremde Datei",
    "ra_settings_schreiben": "fremde Datei mit Passwort darin",
}

_DEF = re.compile(r"^(\s*)def\s+([A-Za-z_][A-Za-z_0-9]*)\s*\(")


def _dateien(wurzel):
    for ordner, _unter, namen in os.walk(wurzel):
        if "__pycache__" in ordner:
            continue
        for n in sorted(namen):
            if n.endswith(".py"):
                yield os.path.join(ordner, n)


def _ohne_kommentare(text):
    """Kommentare und Docstrings heraus - sonst zaehlt die
    Begruendung, warum eine Funktion wichtig ist, als Nennung. Genau
    dieser Fehler hat in diesem Projekt schon dreimal eine
    Strukturpruefung falsch gruen gemacht (Build 244)."""
    raus = []
    in_doc = None
    for zeile in text.split("\n"):
        s = zeile.strip()
        if in_doc:
            if in_doc in s:
                in_doc = None
            continue
        if s.startswith("#"):
            continue
        marke = None
        for m in ('"""', "'''"):
            if s.startswith(m) or s.startswith("r" + m):
                marke = m
                break
        if marke is not None:
            rest = s.split(marke, 1)[1]
            if marke not in rest:
                in_doc = marke
            continue
        raus.append(zeile.split("#", 1)[0])
    return "\n".join(raus)


def sammeln():
    """Jede Testdatei unter der Spur laufen lassen."""
    tests = sorted(n for n in os.listdir(_TOOLS)
                   if n.startswith("test_") and n.endswith(".py"))
    try:
        os.remove(SPUR)
    except OSError:
        pass
    print("Sammellauf: %d Testdateien, Spur nach %s"
          % (len(tests), SPUR))
    print("Das dauert ein Mehrfaches der normalen Suite.")
    t0 = time.time()
    gruen = rot = 0
    for i, n in enumerate(tests, 1):
        pfad = os.path.join(_TOOLS, n)
        rc = subprocess.call(
            [sys.executable, os.path.join(_TOOLS, "_spur.py"), SPUR, pfad],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            cwd=_REPO)
        if rc == 0:
            gruen += 1
        else:
            rot += 1
        sys.stdout.write("\r  %3d/%d  %-34s  gruen %d, rot %d"
                         % (i, len(tests), n[:34], gruen, rot))
        sys.stdout.flush()
    print("")
    print("Fertig in %.0f s. %d gruen, %d rot."
          % (time.time() - t0, gruen, rot))
    print("Jetzt auswerten:  python3 tools/diag_ungeprueft.py")
    return 0


def auswerten(top):
    if not os.path.exists(SPUR):
        print("Keine Spur gefunden (%s)." % SPUR)
        print("Erst sammeln:  python3 tools/diag_ungeprueft.py sammeln")
        return 1
    # 1) Was wurde betreten?
    betreten = set()
    for zeile in io.open(SPUR, encoding="utf-8", errors="replace"):
        teile = zeile.rstrip("\n").split("\t")
        if len(teile) != 3:
            continue
        datei, nr, _name = teile
        try:
            betreten.add((os.path.realpath(datei), int(nr)))
        except ValueError:
            continue

    # 2) Alle Definitionen in frontend/ - mit Zeilennummer, damit
    #    gleichnamige Methoden in verschiedenen Klassen nicht
    #    zusammenfallen.
    defs = []
    fe_text = []
    for pfad in _dateien(_FRONTEND):
        roh = io.open(pfad, encoding="utf-8", errors="replace").read()
        code = _ohne_kommentare(roh)
        fe_text.append(code)
        echt = os.path.realpath(pfad)
        kurz = os.path.relpath(pfad, _REPO)
        for nr, zeile in enumerate(roh.split("\n"), 1):
            m = _DEF.match(zeile)
            if m:
                defs.append((echt, nr, m.group(2), kurz))
    fe_code = "\n".join(fe_text)

    # 3) Gewicht JE DATEI zaehlen, nicht ueber das ganze Programm.
    #
    # DER ERSTE ENTWURF HAT GLOBAL GEZAEHLT, und dann stand oben:
    #
    #     96  sagen   frontend/kernel_probe.py
    #     78  close   frontend/fe/input.py
    #
    # Beides sind Hilfsfunktionen mit haeufigen Namen - 'sagen' kommt
    # 96 mal vor, aber nur innerhalb von kernel_probe.py, und 'close'
    # gibt es in vier Dateien unabhaengig voneinander. Global gezaehlt
    # bekommt jede von ihnen die Summe aller anderen mit, und die
    # Liste fuellt sich mit Namen statt mit Funktionen.
    #
    # Je Datei gezaehlt steht dort, was diese eine Datei wirklich oft
    # benutzt - und genau das ist gemeint.
    gewicht = {}
    for pfad in _dateien(_FRONTEND):
        roh = io.open(pfad, encoding="utf-8", errors="replace").read()
        code = _ohne_kommentare(roh)
        echt = os.path.realpath(pfad)
        namen = set(d[2] for d in defs if d[0] == echt)
        for name in namen:
            muster = re.compile(r"\b" + re.escape(name) + r"\b")
            gewicht[(echt, name)] = len(muster.findall(code))

    offen = []
    for echt, nr, name, kurz in defs:
        if (echt, nr) in betreten:
            continue
        if name in UNINTERESSANT or len(name) < 4:
            continue
        if name.startswith("__") and name.endswith("__"):
            continue
        offen.append((gewicht.get((echt, name), 0), name, kurz, nr))
    offen.sort(key=lambda z: (-z[0], z[2], z[3]))

    insgesamt = len([d for d in defs if len(d[2]) >= 4])
    gelaufen = len([d for d in defs
                    if (d[0], d[1]) in betreten and len(d[2]) >= 4])
    print("=" * 72)
    print(" Welche Funktionen betritt KEIN Test?")
    print("=" * 72)
    print(" %d Definitionen in frontend/, davon %d von der Suite"
          " betreten (%.0f %%)"
          % (insgesamt, gelaufen, 100.0 * gelaufen / max(1, insgesamt)))
    print("")
    print(" GEWICHT = Nennungen im Programmtext. Je hoeher, desto")
    print(" zentraler - und desto unangenehmer, dass kein Test die")
    print(" Funktion betritt. Gemessen mit sys.setprofile, nicht")
    print(" ueber Namen im Testtext: der erste Entwurf dieses Skripts")
    print(" hat genau dadurch seine beiden Anlassfaelle durchgelassen.")
    print("")
    print(" %-7s %-32s %-24s %s"
          % ("GEWICHT", "NAME", "DATEI", "ZEILE"))
    gezeigt = 0
    for g, name, kurz, nr in offen:
        if name in MIT_ABSICHT:
            continue
        print(" %7d %-32s %-24s %d" % (g, name[:32], kurz[-24:], nr))
        gezeigt += 1
        if gezeigt >= top:
            break
    print("")
    print(" (%d ungeprueft insgesamt, %d angezeigt)"
          % (len(offen), gezeigt))

    print("")
    print(" MIT ABSICHT UNGEPRUEFT")
    for name, grund in sorted(MIT_ABSICHT.items()):
        da = [z for z in offen if z[1] == name]
        print("   %-28s %s%s" % (name, grund,
                                 "" if da else "   (laeuft inzwischen)"))

    print("")
    print("=" * 72)
    print(" Die Gegenprobe - die zwei Faelle, fuer die es gebaut wurde:")
    for name in ("scan_games", "read_action"):
        tr = [d for d in defs if d[2] == name]
        for echt, nr, _n, kurz in tr:
            print("   %-14s %-24s Zeile %-6d %s"
                  % (name, kurz[-24:], nr,
                     "BETRETEN" if (echt, nr) in betreten
                     else "von keinem Test betreten"))
    print("=" * 72)
    return 0


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    if arg == "sammeln":
        return sammeln()
    try:
        top = int(arg) if arg else 30
    except ValueError:
        top = 30
    return auswerten(top)


if __name__ == "__main__":
    sys.exit(main())
