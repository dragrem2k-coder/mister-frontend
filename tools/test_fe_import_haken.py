#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ein zu altes fe/-Paket darf keinen Traceback werfen (Build 204).

DER VORFALL, woertlich vom Bildschirm eines Freundes des Nutzers,
nachdem er Frontend_Install.sh zum Aktualisieren laufen liess:

    Starte Frontend...
    Traceback (most recent call last):
      File "/media/fat/frontend/frontend.py", line 218, in <module>
        from fe.settings import (
    ImportError: cannot import name 'artbox_aufschub_aus' from
    'fe.settings' (/media/fat/frontend/fe/settings.py)
    FEHLER: Frontend startet auch im zweiten Versuch sofort wieder ab.

Seine frontend.py kannte den Namen, seine fe/settings.py nicht - die
beiden kamen aus verschiedenen Staenden. Der Name kam in Build 197 in
BEIDE Dateien gleichzeitig; wer nur eine davon bekommt, hat genau
diesen Absturz. Und das Gerät steht dann, es ist kein Schoenheitsfehler.

WARUM DIE VORHANDENE VORSORGE NICHT REICHTE

Seit Build 186 vergleicht _fe_paket_pruefen() namentlich, ob fe/ zu
dieser frontend.py passt, und druckt eine Anleitung statt eines
Absturzes. Die Mechanik ist richtig - sie kommt nur nie zum Zug: ein
fehlender Name in einem "from fe.x import y" fliegt beim IMPORT, also
bevor auch nur eine Zeile eigener Code laeuft.

WAS DIESER TEST ABSICHERT

  - dass der Haken VOR dem ersten fe-Import steht (danach waere er
    wertlos),
  - dass ein fehlender Name in einem fe-Modul eine lesbare Anleitung
    ergibt statt eines Tracebacks - geprueft an einem echten,
    nachgebauten Mischstand auf der Platte,
  - dass die Anleitung den Weg nennt, der wirklich hilft,
  - dass ALLES ANDERE unveraendert durchgereicht wird: ein echter
    Programmfehler muss weiterhin wie einer aussehen, sonst hat man
    sich den naechsten Fehler nur unsichtbar gemacht,
  - und dass der Name, an dem es gescheitert ist, in FE_PAKET_BRAUCHT
    steht.

Ausfuehren:
    python3 tools/test_fe_import_haken.py
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


quelle = io.open(os.path.join(_REPO, "frontend", "frontend.py"),
                 encoding="utf-8").read()

# ---------------------------------------------------------------------------
print("Test 1: der Haken steht VOR dem ersten fe-Import")
# ---------------------------------------------------------------------------
# Sonst ist er wertlos - genau der Import, der stirbt, waere schon
# gelaufen.
_haken = quelle.index("sys.excepthook = _fe_import_haken")
_erster = quelle.index("\nfrom fe.")
check("der Haken wird vor dem ersten 'from fe.' gesetzt",
      _haken < _erster,
      "Haken bei %d, erster fe-Import bei %d" % (_haken, _erster))
check("und nach dem Import von sys",
      quelle.index("import os, sys,") < _haken)

# ---------------------------------------------------------------------------
print()
print("Test 2: DER ECHTE MISCHSTAND - nachgebaut auf der Platte")
# ---------------------------------------------------------------------------
# Nicht die Funktion isoliert aufgerufen, sondern frontend.py wirklich
# gestartet, mit einem fe/settings.py, dem der Name fehlt. Nur so wird
# geprueft, was der Nutzer sieht.
basis = tempfile.mkdtemp(prefix="dragend_mischstand_")
try:
    ziel = os.path.join(basis, "frontend")
    shutil.copytree(os.path.join(_REPO, "frontend"), ziel)
    sp = os.path.join(ziel, "fe", "settings.py")
    s = io.open(sp, encoding="utf-8").read()
    check("der Name steht ueberhaupt in fe/settings.py",
          "def artbox_aufschub_aus():" in s,
          "sonst prueft dieser Test nichts")
    io.open(sp, "w", encoding="utf-8").write(
        s.replace("def artbox_aufschub_aus():",
                  "def _alt_ohne_diesen_namen():", 1))

    erg = subprocess.run([sys.executable, "frontend.py"], cwd=ziel,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         timeout=120)
    text = erg.stdout.decode("utf-8", "replace")
    check("kein Traceback auf dem Bildschirm",
          "Traceback (most recent call last)" not in text,
          text.strip().splitlines()[:2])
    check("stattdessen die Ansage, worum es geht",
          "passen nicht" in text and "zusammen" in text)
    check("der fehlende Name wird genannt",
          "artbox_aufschub_aus" in text)
    check("die betroffene Datei auch",
          "fe/settings.py" in text)
    check("und der Weg, der wirklich hilft",
          "Frontend_Update.sh" in text)
    check("Rueckgabewert 1, damit das Start-Script es merkt",
          erg.returncode == 1, erg.returncode)
finally:
    shutil.rmtree(basis, ignore_errors=True)

# ---------------------------------------------------------------------------
print()
print("Test 3: alles ANDERE wird unveraendert durchgereicht")
# ---------------------------------------------------------------------------
# Das ist die wichtigere Haelfte. Ein Haken, der zu viel abfaengt,
# macht aus jedem kuenftigen Programmfehler eine irrefuehrende
# Update-Anleitung - und dann sucht man tagelang an der falschen Stelle.
_a = quelle.index("def _fe_import_haken")
_e = quelle.index("sys.excepthook = _fe_import_haken")
ns = {"sys": sys}
exec(quelle[_a:_e], ns)                                  # noqa: S102
haken = ns["_fe_import_haken"]

gereicht = []
_echt = sys.__excepthook__
try:
    sys.__excepthook__ = lambda t, w, s: gereicht.append(t)
    for name, ausnahme in (
            ("ValueError", ValueError("irgendein Fehler")),
            ("AttributeError", AttributeError("kein Import")),
            ("ImportError eines FREMDEN Moduls",
             ImportError("cannot import name 'x' from 'json'")),
    ):
        if isinstance(ausnahme, ImportError) and "json" in str(ausnahme):
            ausnahme.name = "json"
        del gereicht[:]
        haken(type(ausnahme), ausnahme, None)
        check("%-34s -> durchgereicht" % name, len(gereicht) == 1)
finally:
    sys.__excepthook__ = _echt

# Und der fe-Fall wird eben NICHT durchgereicht, sondern beendet.
_f = ImportError("cannot import name 'y' from 'fe.art'")
_f.name = "fe.art"
gereicht2 = []
try:
    sys.__excepthook__ = lambda t, w, s: gereicht2.append(t)
    try:
        haken(ImportError, _f, None)
        beendet = False
    except SystemExit as se:
        beendet = (se.code == 1)
finally:
    sys.__excepthook__ = _echt
check("ein fe-Import dagegen beendet sauber mit 1", beendet)
check("und wird nicht zusaetzlich durchgereicht", not gereicht2)

# ---------------------------------------------------------------------------
print()
print("Test 4: der Name steht auch in der Paketpruefung")
# ---------------------------------------------------------------------------
# Der Haken faengt den Absturz ab - aber BENANNT wird ein gemischter
# Stand in FE_PAKET_BRAUCHT, und dort gehoert er hin.
_blk = quelle[quelle.index("FE_PAKET_BRAUCHT = ("):]
_blk = _blk[:_blk.index(")\n")]
check("artbox_aufschub_aus ist aufgenommen",
      "artbox_aufschub_aus" in _blk and "Build 197" in _blk)
check("mit Modul und Build-Nummer",
      "fe.settings" in _blk)

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
