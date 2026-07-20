#!/bin/bash
# ============================================================
# Startet das MiSTer-Frontend - erscheint im echten MiSTer-OSD
# unter dem Menuepunkt "Scripts", da MiSTer jedes .sh-Skript in
# /media/fat/Scripts/ automatisch dort auflistet.
#
# Nuetzlich, um das Frontend nach dem Beenden (Ja/Nein-Dialog)
# wieder zu starten, ohne SSH zu benoetigen.
# ============================================================

if [ -e /media/fat/frontend/disable ]; then
    echo "Frontend ist deaktiviert."
    echo "Aktivieren: Datei /media/fat/frontend/disable loeschen."
    exit 0
fi

# Pruefen, ob bereits eine Instanz laeuft (Lock-Datei)
if [ -f /tmp/frontend.lock ]; then
    OLD_PID=$(cat /tmp/frontend.lock 2>/dev/null)
    if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
        echo "Frontend laeuft bereits (PID $OLD_PID)."
        echo "Nichts zu tun."
        exit 0
    fi
    # verwaiste Lock-Datei (Prozess existiert nicht mehr) - aufraeumen
    rm -f /tmp/frontend.lock
fi

echo "Starte Frontend..."
exec /usr/bin/python3 /media/fat/frontend/frontend.py
