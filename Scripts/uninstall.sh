#!/bin/bash
# AUTOMATISCH ERZEUGTE KOPIE - NICHT DIREKT BEARBEITEN.
# Diese Datei ist eine 1:1-Kopie von /uninstall.sh (Hauptverzeichnis),
# hier abgelegt, damit sie im MiSTer-OSD unter "Scripts"
# erscheint und direkt startbar ist. Aenderungen bitte NUR
# an der Hauptdatei vornehmen - diese Kopie wird beim naechsten
# Paket-Build automatisch neu erzeugt. Eine GitHub Action prueft
# bei jedem Push, ob beide Dateien noch uebereinstimmen (siehe
# .github/workflows/sync-check.yml) - laeuft sonst auseinander,
# wie es hier zuvor bereits passiert war (fehlender fe/-Fix in
# dieser Kopie, urspruengliche Ursache fuer Dennsens Installations-
# problem).
#
# ============================================================
# MiSTer Custom Frontend - Deinstallation
#
# Entfernt Autostart, Scripts und optional die Programmdateien
# wieder. Fragt nach, ob eigene Boxart/Musik/Einstellungen ebenfalls
# geloescht werden sollen, oder nur die Programmdateien selbst.
#
# Aufruf: ./uninstall.sh          (fragt nach)
#         ./uninstall.sh --yes    (entfernt alles ohne Rueckfrage)
#         ./uninstall.sh --keep-data  (Programmdateien weg, eigene
#                                       Daten bleiben, ohne Rueckfrage)
# ============================================================

FRONTEND_DIR="/media/fat/frontend"
SCRIPTS_DIR="/media/fat/Scripts"
STARTUP_FILE="/media/fat/linux/user-startup.sh"
LOCKFILE="/tmp/frontend.lock"

MODE=""
for arg in "$@"; do
    case "$arg" in
        --yes) MODE="all" ;;
        --keep-data) MODE="keep" ;;
    esac
done

echo "=== MiSTer Custom Frontend - Deinstallation ==="
echo ""

# --- Laufende Instanz sauber beenden ---
if [ -f "$LOCKFILE" ]; then
    OLD_PID=$(cat "$LOCKFILE" 2>/dev/null)
    if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
        echo "Beende laufende Instanz (PID $OLD_PID)..."
        kill "$OLD_PID" 2>/dev/null
        i=0
        while [ "$i" -lt 5 ]; do
            kill -0 "$OLD_PID" 2>/dev/null || break
            sleep 1
            i=$((i + 1))
        done
        kill -9 "$OLD_PID" 2>/dev/null || true
    fi
    rm -f "$LOCKFILE"
fi
rm -f /tmp/frontend.log

# --- Autostart-Eintrag entfernen (nur die eine Zeile, Rest bleibt) ---
if [ -f "$STARTUP_FILE" ] && grep -q "frontend_boot.sh" "$STARTUP_FILE"; then
    grep -v "frontend_boot.sh" "$STARTUP_FILE" > "$STARTUP_FILE.tmp" 2>/dev/null
    mv "$STARTUP_FILE.tmp" "$STARTUP_FILE"
    echo "Autostart-Eintrag entfernt."
else
    echo "Kein Autostart-Eintrag gefunden (schon entfernt oder nie eingerichtet)."
fi

# --- Scripts entfernen ---
for s in start_frontend.sh update_frontend.sh boxart_download.sh \
         gameinfo_download.sh stream_toggle.sh; do
    rm -f "$SCRIPTS_DIR/$s"
done
echo "Scripts aus $SCRIPTS_DIR entfernt."

# --- Eigene Daten behalten oder komplett loeschen? ---
if [ -z "$MODE" ]; then
    echo ""
    read -p "Auch eigene Boxart/Musik/Einstellungen loeschen? (j/N) " antwort
    case "$antwort" in
        j|J) MODE="all" ;;
        *)   MODE="keep" ;;
    esac
fi

if [ "$MODE" = "all" ]; then
    rm -rf "$FRONTEND_DIR"
    echo "Kompletter Ordner $FRONTEND_DIR entfernt."
else
    rm -f "$FRONTEND_DIR"/*.py "$FRONTEND_DIR"/*.sh "$FRONTEND_DIR"/*.html
    echo "Programmdateien entfernt - eigene Boxart/Musik/Einstellungen"
    echo "bleiben in $FRONTEND_DIR erhalten (fuer eine spaetere Neuinstallation)."
fi

echo ""
echo "Fertig. MiSTer zeigt beim naechsten Neustart wieder das normale Menue."
