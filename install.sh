#!/bin/bash
# ============================================================
# MiSTer Custom Frontend - automatische Installation
#
# Fuer Leute ohne Vorkenntnisse: laedt den kompletten Build direkt
# von GitHub, kopiert alles an die richtige Stelle und richtet den
# Autostart ein - EIN Befehl statt vieler manueller WinSCP-Schritte.
#
# Aufruf (per SSH auf dem MiSTer):
#
#   curl -Ls https://raw.githubusercontent.com/dragrem2k-coder/mister-frontend/main/install.sh | bash
#
# oder, falls curl nicht vorhanden ist:
#
#   wget -qO- https://raw.githubusercontent.com/dragrem2k-coder/mister-frontend/main/install.sh | bash
#
# Kann jederzeit erneut ausgefuehrt werden (z.B. fuer ein Update) -
# vorhandene eigene Daten (Musik, heruntergeladene Boxart, Einstell-
# ungen) werden NICHT angetastet, nur die Programmdateien ersetzt.
# ============================================================

set -e

REPO_ZIP="https://github.com/dragrem2k-coder/mister-frontend/archive/refs/heads/main.zip"
FRONTEND_DIR="/media/fat/frontend"
SCRIPTS_DIR="/media/fat/Scripts"
TMP_DIR="/tmp/frontend_install_$$"
LOCKFILE="/tmp/frontend.lock"

echo "=== MiSTer Custom Frontend - Installation ==="
echo ""

# --- Download-Werkzeug pruefen ---
if command -v curl >/dev/null 2>&1; then
    DL="curl -Ls -o"
elif command -v wget >/dev/null 2>&1; then
    DL="wget -q -O"
else
    echo "FEHLER: Weder curl noch wget gefunden."
    echo "Bitte die Dateien stattdessen manuell per WinSCP kopieren -"
    echo "siehe README.md, Abschnitt 3 (Installation Schritt fuer Schritt)."
    exit 1
fi

# --- Laufende Instanz sauber beenden (falls vorhanden) ---
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

# --- Herunterladen ---
mkdir -p "$TMP_DIR"
cd "$TMP_DIR"
echo "Lade aktuellen Build herunter..."
if ! $DL build.zip "$REPO_ZIP"; then
    echo "FEHLER: Download fehlgeschlagen. Hat der MiSTer Internetzugang?"
    echo "Test: ping -c 2 github.com"
    rm -rf "$TMP_DIR"
    exit 1
fi

echo "Entpacke..."
if command -v unzip >/dev/null 2>&1; then
    unzip -q build.zip
else
    echo "FEHLER: unzip nicht gefunden - kann das Archiv nicht entpacken."
    rm -rf "$TMP_DIR"
    exit 1
fi

SRC_DIR=$(find . -maxdepth 1 -type d -name "mister-frontend-*" | head -1)
if [ -z "$SRC_DIR" ] || [ ! -d "$SRC_DIR/frontend" ]; then
    echo "FEHLER: Entpackte Struktur sieht nicht wie erwartet aus."
    rm -rf "$TMP_DIR"
    exit 1
fi

# --- Installieren ---
echo "Installiere nach $FRONTEND_DIR und $SCRIPTS_DIR..."
mkdir -p "$FRONTEND_DIR" "$SCRIPTS_DIR" "$FRONTEND_DIR/music"

cp -f "$SRC_DIR"/frontend/*.py "$FRONTEND_DIR/" 2>/dev/null || true
cp -f "$SRC_DIR"/frontend/*.sh "$FRONTEND_DIR/" 2>/dev/null || true
cp -f "$SRC_DIR"/frontend/*.html "$FRONTEND_DIR/" 2>/dev/null || true
[ -d "$SRC_DIR/frontend/sysart" ] && cp -rf "$SRC_DIR/frontend/sysart" "$FRONTEND_DIR/"
cp -f "$SRC_DIR"/Scripts/*.sh "$SCRIPTS_DIR/" 2>/dev/null || true
chmod +x "$FRONTEND_DIR"/*.sh "$SCRIPTS_DIR"/*.sh 2>/dev/null || true

# --- Autostart einrichten (nur falls noch nicht vorhanden) ---
STARTUP_FILE="/media/fat/linux/user-startup.sh"
STARTUP_LINE="$FRONTEND_DIR/frontend_boot.sh &"
if [ -f "$STARTUP_FILE" ] && grep -qF "frontend_boot.sh" "$STARTUP_FILE"; then
    echo "Autostart bereits eingerichtet, wird nicht doppelt eingetragen."
else
    echo "$STARTUP_LINE" >> "$STARTUP_FILE"
    echo "Autostart eingerichtet."
fi

rm -rf "$TMP_DIR"

echo ""
echo "=== Fertig! ==="
echo ""
echo "Das Frontend startet automatisch beim naechsten MiSTer-Neustart."
echo "Jetzt sofort testen, ohne neu zu starten:"
echo "  python3 $FRONTEND_DIR/frontend.py"
echo ""
echo "Boxart und Musik sind noch leer - siehe README.md auf"
echo "https://github.com/dragrem2k-coder/mister-frontend fuer die"
echo "naechsten Schritte (Boxart laden, Musik hinzufuegen usw.)."
