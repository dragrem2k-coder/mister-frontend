#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Video-Reste des Frontends aus der MiSTer.ini entfernen.

NEUES FEATURE (Nutzerwunsch nach einem Fehlerbild bei einem Bekannten,
dessen HDMI-Bild nach dem Start des Frontends wackelte: "falls das die
Ursache ist, sollten wir da Vorkehrungen treffen, das heisst bei
uninstall mit raus ... nicht dass es noch mehrere betrifft").

Die Deinstallation versprach bisher eine rueckstandsfreie Entfernung,
fasste die MiSTer.ini aber ueberhaupt nicht an. Das Frontend kann darin
genau zwei Dinge veraendern - den [Menu]-Block (CRT-Modus) und fb_size
(Menue-Aufloesung) - und beides sind Video-Einstellungen, die nach einer
Deinstallation niemand mehr dem Frontend zuordnen wuerde.

Wird von Scripts/Frontend_Uninstall.sh aufgerufen, BEVOR die
Programmdateien geloescht werden. Bewusst ein eigenes kleines Skript
statt einer Nachbildung derselben Logik in Shell: die Regeln, wann ein
[Menu]-Block entfernt werden DARF, stehen damit nur an einer Stelle
(fe/settings.py) und werden von tools/test_mister_ini.py mitgetestet.

Aufruf:
    python3 /media/fat/frontend/mister_ini_cleanup.py
    python3 /media/fat/frontend/mister_ini_cleanup.py --dry-run
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from fe.settings import (MISTER_INI, crt_menu_active, crt_menu_by_frontend,
                             remove_crt_menu_block, fb_size_value, set_fb_size,
                             mister_ini_video_zustand)
except Exception as e:                      # noqa: BLE001
    # Darf eine Deinstallation NIEMALS aufhalten - im Zweifel bleibt die
    # MiSTer.ini eben unveraendert, das ist die harmlose Richtung.
    print("MiSTer.ini: Aufraeumen uebersprungen (%s)" % e)
    sys.exit(0)

TROCKEN = "--dry-run" in sys.argv


def main():
    if not os.path.exists(MISTER_INI):
        print("MiSTer.ini: nicht vorhanden - nichts aufzuraeumen.")
        return 0

    print("MiSTer.ini vorher: %s" % mister_ini_video_zustand())

    # --- [Menu]-Block ---
    if not crt_menu_active():
        print("MiSTer.ini: kein [Menu]-Block vorhanden.")
    elif not crt_menu_by_frontend():
        # Der Block ist eine ganz normale MiSTer-Funktion und kann vom
        # Nutzer selbst stammen. Ein stehengebliebener eigener Block ist
        # deutlich harmloser als eine geloeschte Einstellung, die niemand
        # mehr zuordnen kann - deshalb hier bewusst NICHT anfassen.
        print("MiSTer.ini: [Menu]-Block bleibt stehen - er stammt nicht vom")
        print("            Frontend (eigene Einstellung des Nutzers).")
    elif TROCKEN:
        print("MiSTer.ini: [Menu]-Block WUERDE entfernt (Probelauf).")
    else:
        r = remove_crt_menu_block()
        if r:
            print("MiSTer.ini: [Menu]-Block entfernt (CRT-Modus zurueckgesetzt).")
        else:
            print("MiSTer.ini: [Menu]-Block konnte nicht entfernt werden.")

    # --- fb_size ---
    wert = fb_size_value()
    if not wert:
        print("MiSTer.ini: fb_size ist bereits auf dem MiSTer-Standard.")
    elif TROCKEN:
        print("MiSTer.ini: fb_size=%d WUERDE zurueckgesetzt (Probelauf)." % wert)
    else:
        if set_fb_size(0) == 0:
            print("MiSTer.ini: fb_size=%d zurueckgesetzt (Menue-Aufloesung)." % wert)
        else:
            print("MiSTer.ini: fb_size konnte nicht zurueckgesetzt werden.")

    print("MiSTer.ini nachher: %s" % mister_ini_video_zustand())
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:                  # noqa: BLE001
        print("MiSTer.ini: Aufraeumen abgebrochen (%s)" % e)
        sys.exit(0)
