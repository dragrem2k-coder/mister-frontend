#!/bin/bash
# ============================================================
# MiSTer Frontend - F4-Schnellstart (Autostart-Wrapper)
#
# Wird von /media/fat/linux/user-startup.sh beim Booten gerufen und
# startet den kleinen Waechter aus f4_hotkey.py im Hintergrund.
#
# BEWUSST IMMER EINGETRAGEN, ABER STANDARDMAESSIG WIRKUNGSLOS:
# ohne die Schalterdatei /media/fat/frontend/f4_hotkey beendet sich
# f4_hotkey.py sofort wieder. Der Eintrag in user-startup.sh muss
# deshalb nur EINMAL beim Installieren gesetzt werden - der Menuepunkt
# unter System -> Optionen legt danach nur noch die Schalterdatei an
# bzw. loescht sie. Das ist der springende Punkt: an user-startup.sh
# (einer Datei, die dem MiSTer gehoert und bei der ein Fehler das
# ganze Geraet lahmlegen kann) wird zur LAUFZEIT nie mehr geruehrt.
#
# Not-Aus wie beim Frontend selbst: Datei /media/fat/frontend/disable
# anlegen, dann startet hier gar nichts mehr.
# ============================================================

[ -e /media/fat/frontend/disable ] && exit 0
[ -e /media/fat/frontend/f4_hotkey ] || exit 0

exec /usr/bin/python3 /media/fat/frontend/f4_hotkey.py \
    >> /tmp/frontend.log 2>&1
