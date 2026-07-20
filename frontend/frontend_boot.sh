#!/bin/bash
# ============================================================
# MiSTer Frontend - Autostart-Wrapper
# Wird von /media/fat/linux/user-startup.sh beim Booten gerufen.
#
# Not-Aus: Datei /media/fat/frontend/disable anlegen,
# dann startet das Frontend beim naechsten Boot NICHT.
# (z.B. per SSH:  touch /media/fat/frontend/disable )
# ============================================================

# Deaktivierungs-Schalter pruefen
[ -e /media/fat/frontend/disable ] && exit 0

# Warten, bis MiSTer hochgefahren und im Menue ist (max. 60 s)
for i in $(seq 1 60); do
    CORE=$(tr -d '\0' < /tmp/CORENAME 2>/dev/null)
    [ "$CORE" = "MENU" ] && break
    sleep 1
done

# Dem MiSTer-Hauptprogramm noch einen Moment geben
sleep 2

exec /usr/bin/python3 /media/fat/frontend/frontend.py \
    >> /tmp/frontend.log 2>&1
