#!/bin/bash
# ============================================================
# Frontend nach einem Datei-Update sauber neu starten
#
# Ablauf fuer ein Update:
#   1. Neue Dateien (frontend.py usw.) per WinSCP nach
#      /media/fat/frontend/ kopieren (alte ueberschreiben)
#   2. DANACH dieses Skript ausfuehren - per SSH oder aus dem
#      MiSTer-OSD (Hauptmenue -> Scripts -> update_frontend)
#
# Ersetzt den bisherigen manuellen Ablauf
# (kill $(cat /tmp/frontend.lock); rm -f ...; python3 frontend.py)
# durch einen einzigen Befehl.
# ============================================================

FRONTEND_DIR="/media/fat/frontend"
LOCKFILE="/tmp/frontend.lock"

echo "Frontend-Update wird angewendet..."

# BEWUSST OHNE den Selbstmord-Schutz aus install_frontend.sh/install.sh/
# install_offline.sh: hier ist der Kill tatsaechlich beabsichtigt UND
# funktioniert korrekt selbst dann, wenn er das aufrufende Frontend
# selbst trifft - anders als bei den Install-Skripten (die auf das
# ORIGINAL-Frontend angewiesen sind, das nach diesem Script normal ueber
# back_to_frontend() zurueckkehrt) startet DIESES Script am Ende selbst
# einen frischen Frontend-Prozess (exec python3 frontend.py, siehe
# unten) - der Kill hier toetet also bewusst die ALTE Instanz, bevor
# gleich die NEUE (mit aktualisiertem Code) an ihrer Stelle startet.
# Wuerde der Kill hier uebersprungen, liefen am Ende ZWEI
# Frontend-Prozesse gleichzeitig - ein anderes, neues Problem.
if [ -f "$LOCKFILE" ]; then
    OLD_PID=$(cat "$LOCKFILE" 2>/dev/null)
    if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
        echo "Beende laufende Instanz (PID $OLD_PID)..."
        kill "$OLD_PID" 2>/dev/null
        # Bis zu 5 Sekunden auf sauberes Beenden warten (ganze
        # Sekunden statt Sekundenbruchteile - maximale Kompatibilitaet
        # mit unterschiedlichen MiSTer-Shell-Umgebungen)
        i=0
        while [ "$i" -lt 5 ]; do
            kill -0 "$OLD_PID" 2>/dev/null || break
            sleep 1
            i=$((i + 1))
        done
        if kill -0 "$OLD_PID" 2>/dev/null; then
            echo "Reagiert nicht - erzwinge Beenden..."
            kill -9 "$OLD_PID" 2>/dev/null
            sleep 1
        fi
    fi
    rm -f "$LOCKFILE"
fi
rm -f /tmp/frontend.log

if [ -e "$FRONTEND_DIR/disable" ]; then
    echo "Hinweis: Frontend ist deaktiviert (disable-Datei vorhanden)."
    echo "Aktivieren: rm $FRONTEND_DIR/disable"
    exit 0
fi

echo "Starte aktualisiertes Frontend..."
exec /usr/bin/python3 "$FRONTEND_DIR/frontend.py"
