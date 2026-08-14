#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GAMES_BASES als eigenstaendiges Modul - vermeidet einen Zirkelbezug
zwischen frontend.py und fe/wot.py bzw. fe/scan.py (Modularisierung,
Git-Branch 'modular-refactor').

GAMES_BASES wird mehrfach NEU zugewiesen (nicht nur mutiert - siehe
_wait_for_network_ready() in fe/scan.py, wartet auf ein evtl. erst
spaeter erscheinendes NAS-Mount) - dieselbe Einfrier-Falle wie bei
CURRENT_LANG/C_BG/VOLUME. Alles, was GAMES_BASES braucht (fe/wot.py,
fe/scan.py), liest es modul-qualifiziert (import fe.paths;
fe.paths.GAMES_BASES) statt per "from fe.paths import GAMES_BASES",
um selbst keine eingefrorene Kopie zu erzeugen.

_discover_games_bases() lebt jetzt HIER (nicht mehr in frontend.py) -
zusammen mit dem Wert, den sie ermittelt, statt getrennt an zwei
Stellen. Modul initialisiert sich beim Import selbst.
"""
import os

def _discover_games_bases():
    """Alle Orte, an denen ROMs liegen koennen (SD + USB-Laufwerke).

    BUGFIX (Nutzer-Rueckmeldung: "Spiele ausser von /media/fat/games
    werden nicht angezeigt"): die feste Liste deckte nur usb0 bis
    usb5 ab - Speicherorte ausserhalb dieses festen Musters (z.B. ein
    Netzlaufwerk unter einem anderen Namen, oder ein USB-Geraet mit
    hoeherer Nummer) wurden dadurch nie gefunden, komplett unabhaengig
    davon, was tatsaechlich am MiSTer angeschlossen ist. Jetzt
    zusaetzlich dynamisch: alles, was tatsaechlich unter /media
    eingehaengt ist (ausser "fat" selbst, das schon feststeht), wird
    automatisch mit aufgenommen - deckt damit auch Faelle ab, die die
    feste Liste nicht vorgesehen hatte. Die urspruengliche feste Liste
    bleibt zusaetzlich bestehen (Vorhersagbarkeit/Ruecksichtigung auf
    den ueblichen Fall, auch wenn /media aus irgendeinem Grund gerade
    nicht lesbar sein sollte)."""
    bases = ["/media/fat/games"]
    bases += ["/media/usb%d/games" % i for i in range(6)]
    bases += ["/media/usb%d" % i for i in range(6)]
    try:
        for entry in sorted(os.listdir("/media")):
            if entry == "fat":
                continue   # schon oben abgedeckt
            path = "/media/" + entry
            if not os.path.isdir(path):
                continue
            games_sub = os.path.join(path, "games")
            if games_sub not in bases:
                bases.append(games_sub)
            if path not in bases:
                bases.append(path)
    except OSError:
        pass   # /media nicht lesbar - bei der festen Liste bleiben
    return bases

# Bewusst als Funktionsergebnis statt als literale Liste - siehe
# _discover_games_bases() oben fuer die Begruendung (dynamische
# Erkennung zusaetzlich zur festen Liste). Selbstinitialisierung beim
# Modul-Import, damit frontend.py hier nichts mehr extra tun muss.
GAMES_BASES = _discover_games_bases()
