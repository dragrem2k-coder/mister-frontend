#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DIAGNOSE (kein Pass/Fail): die Speicherspitze beim Rescan.

WOHER DIE FRAGE KOMMT. Die Messung vom 18.09. (FUND_Speicher_je_Eintrag)
hat die Posten aufgeteilt:

    Spielebaum                       383 B je Eintrag
    Anzeigenamen-Cache               123 B je Eintrag
    Pickle-Puffer beim Schreiben     144 B je Eintrag
    zweite Kopie beim Einlesen       439 B je Eintrag
    ------------------------------------------------
    Dauerlast (Baum + Namen)         506 B je Eintrag
    SPITZE                          1089 B je Eintrag

Der begrenzende Faktor ist also NICHT der Ruhezustand - 50.000 Spiele
sind im Betrieb 24 MB, auf einem Geraet mit 1 GB nichts. Der
begrenzende Faktor ist die SPITZE, und die entsteht, weil beim Scan
kurzzeitig zwei Baeume gleichzeitig im Speicher liegen.

WAS DIESES SKRIPT MISST, und zwar in Bytes und nicht in Vermutungen:
den Verlauf von VmRSS durch genau die Abfolge, die scan_games()
nimmt, wenn der Cache nicht mehr passt -

    1. alten Baum aus dem Cache lesen
    2. neuen Baum aufbauen (voller Scan)
    3. beide gleichzeitig im Speicher   <- die Spitze
    4. neuen Baum wegschreiben

und daneben dieselbe Abfolge, bei der der alte Baum VOR Schritt 2
freigegeben wird. Der Unterschied ist die Zahl, um die es geht.

Ausfuehren:
    python3 tools/diag_startspitze.py
    python3 tools/diag_startspitze.py 100000      # eigene Eintragszahl
"""
import gc
import os
import pickle
import sys
import tempfile

EINTRAEGE = int(sys.argv[1]) if len(sys.argv) > 1 else 50000

# Realistische Laengen - genau wie in der Messung vom 18.09.: Titel
# rund 40, Pfad rund 69 Zeichen. Mit kuerzeren Zeichenketten faellt
# die Messung zu guenstig aus, und das waere die unangenehmere Sorte
# Fehler.
TITEL = "Super Mario Bros 3 (USA) [Hack by Someone]"
PFAD = ("/media/fat/games/NES/USA/Platformer/"
        "Super Mario Bros 3 (USA) [Hack by Someone].nes")


def vmrss():
    """VmRSS in Bytes - was der Prozess WIRKLICH belegt.

    Nicht sys.getsizeof(): das zaehlt nur das aeussere Objekt und
    verschweigt die Zeichenketten darin, also genau das, worum es hier
    geht."""
    try:
        with open("/proc/self/status") as f:
            for zeile in f:
                if zeile.startswith("VmRSS:"):
                    return int(zeile.split()[1]) * 1024
    except OSError:
        pass
    return 0


def mb(n):
    return n / 1048576.0


def baum_bauen(n, marke=""):
    """Ein Spielebaum in genau der Form, die fe/scan.py erzeugt:
    cats -> (Anzeigename, Knoten, Systemkuerzel), Knoten["items"] ->
    (Titel, "game", (Pfad, Endung, Systemkuerzel, RBF, Ladeart))."""
    cats = []
    je_system = max(1, n // 24)
    rest = n
    for s in range(24):
        wieviel = min(je_system, rest)
        rest -= wieviel
        items = [("%s%s %05d" % (TITEL, marke, i), "game",
                  ("%s%s%05d" % (PFAD, marke, i), ".nes", "NES",
                   "/media/fat/_Console/NES.rbf", None))
                 for i in range(wieviel)]
        cats.append(("System %02d" % s, {"items": items}, "SYS%02d" % s))
        if rest <= 0:
            break
    return cats


def messen(freigeben, je_system=False):
    """Die Abfolge von scan_games() einmal durchspielen und die
    Spitze mitschreiben. freigeben=True gibt den alten Baum vor dem
    Aufbau des neuen frei."""
    gc.collect()
    basis = vmrss()
    verlauf = []

    # --- 1. alten Baum "aus dem Cache lesen" --------------------
    fd, cache = tempfile.mkstemp(suffix=".pkl")
    os.close(fd)
    try:
        alt = baum_bauen(EINTRAEGE, "a")
        with open(cache, "wb") as f:
            pickle.dump({"sig": "x", "per_syskey": {}, "cats": alt},
                        f, protocol=pickle.HIGHEST_PROTOCOL)
        del alt
        gc.collect()
        with open(cache, "rb") as f:
            data = pickle.load(f)
        gc.collect()
        verlauf.append(("alter Baum gelesen", vmrss() - basis))

        # --- 2./3. neuer Baum, beide gleichzeitig ---------------
        # GENAU HIER LIEGT DER UNTERSCHIED: scan_games() haelt 'data'
        # ueber den ganzen Aufruf. Im inkrementellen Fall MUSS es das
        # (die unveraenderten Systeme werden daraus uebernommen), im
        # vollen Scan nicht.
        if freigeben:
            data = None
            gc.collect()
            verlauf.append(("alter Baum freigegeben", vmrss() - basis))
        cats = baum_bauen(EINTRAEGE, "n")
        gc.collect()
        verlauf.append(("neuer Baum aufgebaut", vmrss() - basis))

        # --- 4. wegschreiben ------------------------------------
        #
        # WARUM DAS SCHREIBEN UEBERHAUPT NOCH EINE SPITZE MACHT:
        # pickle fuehrt eine Memo-Tabelle mit JEDEM Objekt, das es
        # schon geschrieben hat - bei 50.000 Eintraegen sind das rund
        # eine Viertelmillion Einträge. Die Tabelle lebt bis zum Ende
        # des EINEN dump()-Aufrufs. Schreibt man je System einen
        # eigenen dump() in dieselbe Datei, ist die Tabelle immer nur
        # so gross wie ein System.
        if je_system:
            with open(cache, "wb") as f:
                pickle.dump({"sig": "y", "per_syskey": {},
                             "systeme": len(cats)}, f,
                            protocol=pickle.HIGHEST_PROTOCOL)
                for eintrag in cats:
                    pickle.dump(eintrag, f,
                                protocol=pickle.HIGHEST_PROTOCOL)
        else:
            with open(cache, "wb") as f:
                pickle.dump({"sig": "y", "per_syskey": {}, "cats": cats},
                            f, protocol=pickle.HIGHEST_PROTOCOL)
        verlauf.append(("neuer Baum geschrieben", vmrss() - basis))
        spitze = max(v for _n, v in verlauf)
        del cats, data
        gc.collect()
        verlauf.append(("danach (Dauerlast 0)", vmrss() - basis))
    finally:
        try:
            os.remove(cache)
        except OSError:
            pass
    return verlauf, spitze


def _teil(schalter):
    """EIN Durchlauf, und der Prozess ist danach fertig.

    JE VARIANTE EIN EIGENER PROZESS - das ist nicht Umstaendlichkeit,
    sondern der Unterschied zwischen einer Zahl und einer Behauptung.
    Der erste Entwurf hat beide Varianten hintereinander im selben
    Prozess gemessen, und die zweite startete damit auf einer
    verschmutzten Grundlinie: freigegebener Speicher geht nicht
    zwangslaeufig an das Betriebssystem zurueck, die Arena bleibt
    liegen. In der Ausgabe stand dann "danach (Dauerlast 0): 17,2 MB",
    was fuer sich schon die Warnung war. Jetzt faengt jede Variante
    bei null an."""
    verlauf, spitze = messen(schalter in ("mit", "je_system"),
                             je_system=(schalter == "je_system"))
    for name, wert in verlauf:
        print("ZEILE\t%s\t%d" % (name, wert))
    print("SPITZE\t%d" % spitze)
    return 0


def main():
    if len(sys.argv) > 2 and sys.argv[2] in ("mit", "ohne", "je_system"):
        return _teil(sys.argv[2])

    print("=" * 70)
    print(" Die Speicherspitze beim Rescan - %d Eintraege" % EINTRAEGE)
    print("=" * 70)
    print(" Gemessen wird VmRSS, nicht sys.getsizeof(): gesucht ist,")
    print(" was der Prozess WIRKLICH belegt - samt der Zeichenketten.")
    print(" Je Variante ein EIGENER Prozess, damit beide bei null")
    print(" anfangen (siehe _teil()).")
    print("")

    import subprocess
    ergebnis = {}
    for titel, schalter in (
            ("WIE BISHER: alter Baum bleibt liegen", "ohne"),
            ("MIT FREIGABE vor dem neuen Baum", "mit"),
            ("FREIGABE + je System geschrieben", "je_system")):
        roh = subprocess.check_output(
            [sys.executable, os.path.abspath(__file__),
             str(EINTRAEGE), schalter]).decode("utf-8", "replace")
        print(" %s" % titel)
        spitze = 0
        for zeile in roh.strip().split("\n"):
            teile = zeile.split("\t")
            if teile[0] == "ZEILE":
                wert = int(teile[2])
                print("   %-26s %8.1f MB   %6.0f B je Eintrag"
                      % (teile[1], mb(wert), wert / float(EINTRAEGE)))
            elif teile[0] == "SPITZE":
                spitze = int(teile[1])
        print("   %-26s %8.1f MB   %6.0f B je Eintrag"
              % ("SPITZE", mb(spitze), spitze / float(EINTRAEGE)))
        print("")
        ergebnis[schalter] = spitze

    ohne = ergebnis["ohne"]
    mit = ergebnis["mit"]
    js = ergebnis["je_system"]
    print(" UNTERSCHIED")
    for name, wert in (("ohne Freigabe", ohne), ("mit Freigabe", mit),
                       ("+ je System", js)):
        print("   Spitze %-16s %8.1f MB   %6.0f B je Eintrag  %s"
              % (name, mb(wert), wert / float(EINTRAEGE),
                 "" if wert == ohne
                 else ("-%.0f %%" % (100.0 * (ohne - wert) / max(1, ohne)))))
    print("")
    print("   Hochgerechnet (Spitze beim Rescan):")
    print("     %9s %10s %10s %10s" % ("Spiele", "bisher", "Freigabe",
                                       "+je System"))
    for n in (30000, 50000, 100000, 250000):
        print("     %9d %7.0f MB %7.0f MB %7.0f MB"
              % (n, mb(ohne / float(EINTRAEGE) * n),
                 mb(mit / float(EINTRAEGE) * n),
                 mb(js / float(EINTRAEGE) * n)))
    print("")

    print("=" * 70)
    print(" Zu lesen als: 'je Eintrag' ist die uebertragbare Zahl -")
    print(" damit laesst sich jede Bestandsgroesse hochrechnen. Die")
    print(" Dauerlast war nie das Problem (50.000 Spiele sind rund")
    print(" 24 MB); die Spitze beim Rescan ist es. Und sie entsteht")
    print(" nicht durch Pickle, sondern dadurch, dass der alte Baum")
    print(" noch referenziert ist, waehrend der neue entsteht.")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
