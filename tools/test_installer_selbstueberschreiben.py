#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Der Installer darf sich nicht selbst ueberschreiben (Build 187).

DER FALL, vom Bildschirm eines Nutzers abgelesen:

    Download erfolgreich.
    Entpacke...
    Installiere nach /media/fat/frontend und /media/fat/Scripts...
    /media/fat/Scripts/Frontend_Install.sh: line 302:
        syntax error near unexpected token `fi'

Unsere Fassung ist syntaktisch einwandfrei - "bash -n" sagt bei allen
Skripten nichts. Der Fehler entsteht erst beim LAUFEN:

In /media/fat/Scripts liegt das Skript, das gerade ausgefuehrt wird.
Bash liest ein Skript nicht auf einmal ein, sondern haeppchenweise, und
merkt sich dabei seine Byte-Position in der Datei. Ein "cp -f" schreibt
in DIESELBE Datei - derselbe Inode - und damit steht unter der
gemerkten Position ploetzlich anderer Inhalt. Bash liest mitten in
einen Befehl hinein und bricht ab; die gemeldete Zeilennummer bedeutet
nichts.

Dass es nur manchmal auftritt, passt genau dazu: es haengt daran, ob
sich die Datei an der gerade gelesenen Stelle ueberhaupt unterscheidet.

"mv" tauscht dagegen nur den Verzeichniseintrag. Der laufende Bash
behaelt seinen geoeffneten Inode und liest ihn unbeschadet zu Ende.

WAS DIESER TEST ABSICHERT

  - dass kein Installer mehr mit "cp" direkt in den Scripts-Ordner
    schreibt,
  - dass stattdessen ueber eine Nebendatei und "mv" gearbeitet wird,
  - dass die Nebendatei bei einem Fehlschlag wieder verschwindet,
  - und dass alle Skripte syntaktisch in Ordnung sind (das war hier
    NICHT die Ursache, aber es auszuschliessen kostet nichts).

Ausfuehren:
    python3 tools/test_installer_selbstueberschreiben.py
"""
import io
import os
import re
import subprocess
import sys

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
_SCRIPTS = os.path.join(_REPO, "Scripts")

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


namen = sorted(n for n in os.listdir(_SCRIPTS) if n.endswith(".sh"))
inhalt = {}
for n in namen:
    inhalt[n] = io.open(os.path.join(_SCRIPTS, n), encoding="utf-8",
                        errors="replace").read()

# ---------------------------------------------------------------------------
print("Test 1: alle Skripte sind syntaktisch in Ordnung")
# ---------------------------------------------------------------------------
# Nicht die Ursache des gemeldeten Fehlers - aber der erste Verdacht,
# und ihn auszuschliessen kostet eine Sekunde.
for n in namen:
    r = subprocess.run(["bash", "-n", os.path.join(_SCRIPTS, n)],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    check("bash -n %s" % n, r.returncode == 0,
          r.stderr.decode("utf-8", "replace").strip()[:120])

# ---------------------------------------------------------------------------
print()
print("Test 2: DER FEHLER - kein cp direkt in den Scripts-Ordner")
# ---------------------------------------------------------------------------
# Gesucht wird nach einem cp, dessen ZIEL der Scripts-Ordner ist. Genau
# das schreibt in den Inode der gerade laufenden Datei.
muster = re.compile(
    r'^\s*(?!#)\S*\bcp\b[^\n]*?(\$SCRIPTS_DIR/?"?|/media/fat/Scripts/?"?)\s*(2>|&&|\|\||$)')
for n in namen:
    treffer = [z.strip() for z in inhalt[n].splitlines()
               if muster.match(z)]
    check("%s schreibt nicht mit cp dorthin" % n, not treffer,
          "; ".join(treffer[:2]))

# ---------------------------------------------------------------------------
print()
print("Test 3: stattdessen Nebendatei und mv")
# ---------------------------------------------------------------------------
installer = [n for n in namen if n.startswith("Frontend_Install")]
check("es gibt die drei Installer", len(installer) >= 3,
      ", ".join(installer))
for n in installer:
    check("%s legt eine Nebendatei an" % n, "__neu__" in inhalt[n])
    check("   und benennt sie um", re.search(r'mv -f "[^"]*__neu__"',
                                             inhalt[n]) is not None)
    check("   und raeumt sie bei einem Fehlschlag weg",
          re.search(r'rm -f "[^"]*__neu__"', inhalt[n]) is not None,
          "sonst bleibt bei einem vollen Datentraeger Muell liegen")
    check("   und die Begruendung steht dabei",
          "derselbe Inode" in inhalt[n],
          "wer das in einem Jahr liest, soll nicht suchen muessen")

# ---------------------------------------------------------------------------
print()
print("Test 4: das Umbenennen ist wirklich ein Inode-Tausch")
# ---------------------------------------------------------------------------
# Die Behauptung des ganzen Umbaus, einmal nachgestellt: cp schreibt in
# denselben Inode, mv legt einen neuen an. Wer das anzweifelt, sieht es
# hier.
import tempfile                                          # noqa: E402

ordner = tempfile.mkdtemp(prefix="installer_test_")
try:
    ziel = os.path.join(ordner, "laeuft.sh")
    quelle = os.path.join(ordner, "neu.sh")
    io.open(ziel, "w").write("alt\n")
    io.open(quelle, "w").write("neu\n")
    inode_vorher = os.stat(ziel).st_ino

    subprocess.run(["cp", "-f", quelle, ziel], check=True)
    check("nach cp ist es DERSELBE Inode",
          os.stat(ziel).st_ino == inode_vorher,
          "genau das trifft die laufende Datei")

    io.open(ziel, "w").write("alt\n")
    inode_vorher = os.stat(ziel).st_ino
    subprocess.run(["cp", "-f", quelle, ziel + ".__neu__"], check=True)
    subprocess.run(["mv", "-f", ziel + ".__neu__", ziel], check=True)
    check("nach cp+mv ist es ein ANDERER Inode",
          os.stat(ziel).st_ino != inode_vorher,
          "die laufende Datei bleibt unberuehrt")
finally:
    import shutil
    shutil.rmtree(ordner, ignore_errors=True)

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
