#!/bin/bash
# ============================================================
# Startet das MiSTer-Frontend - erscheint im echten MiSTer-OSD
# unter dem Menuepunkt "Scripts", da MiSTer jedes .sh-Skript in
# /media/fat/Scripts/ automatisch dort auflistet.
#
# Nuetzlich, um das Frontend nach dem Beenden (Ja/Nein-Dialog)
# wieder zu starten, ohne SSH zu benoetigen.
#
# NEU: diese Datei hiess bis einschliesslich Build 2026-08-24-5
# "start_frontend.sh" - jetzt umbenannt, siehe Kopfkommentar in
# Frontend_Install.sh fuer die Begruendung.
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
# BUGFIX: gleiches Sicherheitsnetz wie in Frontend_Update.sh (siehe
# dortiger ausfuehrlicher Kommentar) - kein "exec" mehr, damit ein
# sofortiger Absturz nicht zu einer stillen, leeren Konsole ohne jeden
# Hinweis fuehrt, sondern zu einem automatischen Neuversuch samt
# sichtbarer Fehlermeldung, falls selbst der scheitert.
FRONTEND_DIR="/media/fat/frontend"
attempt=1
while [ "$attempt" -le 2 ]; do
    START_TS=$(date +%s 2>/dev/null || echo 0)
    /usr/bin/python3 "$FRONTEND_DIR/frontend.py"
    RC=$?
    END_TS=$(date +%s 2>/dev/null || echo 0)
    RUNTIME=$((END_TS - START_TS))
    if [ "$RUNTIME" -ge 3 ]; then
        exit "$RC"
    fi
    if [ "$attempt" -eq 1 ]; then
        echo ""
        echo "Frontend hat sich sofort wieder beendet (Code $RC, nach ${RUNTIME}s)"
        echo "- vermutlich eine kurze Race direkt nach dem Start."
        echo "Neuer Versuch in 2 Sekunden..."
        sleep 2
    fi
    attempt=$((attempt + 1))
done
echo ""
echo "FEHLER: Frontend startet auch im zweiten Versuch sofort wieder ab."
echo "Details:  cat /tmp/frontend.log"
echo "Manuell erneut versuchen:  python3 $FRONTEND_DIR/frontend.py"
echo ""
read -rsn1 -p "Taste druecken zum Beenden..." 2>/dev/null
echo ""
exit 1
