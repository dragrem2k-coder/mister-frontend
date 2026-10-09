#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ein Testskript laufen lassen und aufschreiben, WELCHE Funktionen
dabei wirklich betreten wurden.

    python3 tools/_spur.py <ausgabedatei> tools/test_x.py [args...]

Benutzt von tools/diag_ungeprueft.py. Geschrieben wird je Zeile:

    <datei>\t<erste Zeile der Funktion>\t<name>

WARUM NICHT EINFACH DIE NAMEN IM TEXT SUCHEN, und das ist der ganze
Grund fuer diese Datei: der erste Entwurf von diag_ungeprueft.py hat
genau das getan - und die beiden Faelle, fuer die es gebaut wurde,
NICHT gefunden:

    scan_games     Programm   8, Tests  16
    read_action    Programm  41, Tests  33

Beide Namen stehen reichlich in tools/. Nur gerufen wurde die ECHTE
Funktion nie: scan_games() stand in einem Test, der sie beschreibt,
und read_action wurde durch eine Attrappe ERSETZT - der Name war da,
der Aufruf nicht. Eine Liste, die ihre eigenen Anlassfaelle durchlaesst,
ist keine Liste, sondern eine Beruhigung.

Gemessen wird deshalb mit sys.setprofile: es feuert bei jedem
EINTRITT in eine Python-Funktion. Kein Fremdpaket (coverage gibt es
hier nicht und soll es auch nicht geben), dafuer langsamer - der
komplette Lauf dauert ein Mehrfaches. Das ist in Ordnung: diese
Messung ist eine Durchsicht, kein Dauerlauf.

runpy statt exec(), damit __name__ == "__main__" und __file__ stimmen -
die Testdateien haengen beides an (sys.path.insert mit
dirname(__file__), und der Block unter if __name__)."""
import os
import runpy
import sys
import threading


def _schreiber(pfad):
    gesehen = set()
    lock = threading.Lock()

    def profil(rahmen, ereignis, _arg):
        if ereignis != "call":
            return
        code = rahmen.f_code
        with lock:
            schluessel = (code.co_filename, code.co_firstlineno,
                          code.co_name)
            gesehen.add(schluessel)

    def schreiben():
        try:
            with open(pfad, "a", encoding="utf-8") as f:
                for datei, zeile, name in sorted(gesehen):
                    f.write("%s\t%d\t%s\n" % (datei, zeile, name))
        except OSError:
            pass

    return profil, schreiben


def main():
    if len(sys.argv) < 3:
        print("Aufruf: _spur.py <ausgabe> <skript> [args...]")
        return 2
    ausgabe = sys.argv[1]
    ziel = sys.argv[2]
    sys.argv = [ziel] + sys.argv[3:]
    profil, schreiben = _schreiber(ausgabe)
    # AUCH IN NEUEN THREADS mitschreiben: der Vorauslader, der
    # Schreibfaden und die Sound-Faeden laufen nebenher, und was dort
    # laeuft, ist genauso geprueft wie der Hauptfaden.
    threading.setprofile(profil)
    sys.setprofile(profil)
    rc = 0
    try:
        runpy.run_path(ziel, run_name="__main__")
    except SystemExit as e:
        rc = e.code if isinstance(e.code, int) else (0 if not e.code else 1)
    except Exception:                                    # noqa: BLE001
        import traceback
        traceback.print_exc()
        rc = 1
    finally:
        sys.setprofile(None)
        threading.setprofile(None)
        schreiben()
    return rc


if __name__ == "__main__":
    sys.exit(main())
