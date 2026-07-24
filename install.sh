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
    TOOL=curl
elif command -v wget >/dev/null 2>&1; then
    TOOL=wget
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

download_ok=0
if [ "$TOOL" = "curl" ]; then
    curl -L --fail --show-error -o build.zip "$REPO_ZIP" 2>dl_err.txt \
        && download_ok=1
else
    wget -O build.zip "$REPO_ZIP" 2>dl_err.txt && download_ok=1
fi

if [ "$download_ok" != "1" ]; then
    echo ""
    echo "Erster Versuch fehlgeschlagen, genaue Fehlermeldung:"
    echo "----------------------------------------"
    cat dl_err.txt
    echo "----------------------------------------"
    echo ""
    echo "Versuche es erneut OHNE SSL-Zertifikatspruefung (auf manchen"
    echo "MiSTer-Installationen sind die mitgelieferten Zertifikate"
    echo "veraltet - das ist ein bekanntes, haeufiges Problem)..."
    if [ "$TOOL" = "curl" ]; then
        curl -L --fail --show-error -k -o build.zip "$REPO_ZIP" 2>dl_err2.txt \
            && download_ok=1
    else
        wget --no-check-certificate -O build.zip "$REPO_ZIP" 2>dl_err2.txt \
            && download_ok=1
    fi
fi

if [ "$download_ok" != "1" ]; then
    echo ""
    echo "FEHLER: Download auch im zweiten Versuch fehlgeschlagen."
    if [ -f dl_err2.txt ]; then
        echo "----------------------------------------"
        cat dl_err2.txt
        echo "----------------------------------------"
    fi
    echo ""
    echo "Naechste Schritte zum Selbst-Pruefen:"
    echo "  1. Internetzugang testen:   ping -c 2 github.com"
    echo "  2. Direkter Testaufruf:     $TOOL -v \"$REPO_ZIP\""
    echo "  3. Falls beides fehlschlaegt: Dateien stattdessen manuell"
    echo "     per WinSCP kopieren, siehe README.md Abschnitt 3."
    rm -rf "$TMP_DIR"
    exit 1
fi
echo "Download erfolgreich."

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
if [ -d "$SRC_DIR/frontend/sysart" ]; then
    # NUR fehlende Dateien ergaenzen (kein Ueberschreiben!) - sonst
    # wuerden eigene, per Hand ersetzte Logos bei jedem erneuten Lauf
    # (z.B. fuer ein Update) wieder auf die Standard-Bilder aus dem
    # Repo zurueckgesetzt.
    mkdir -p "$FRONTEND_DIR/sysart"
    cp -rn "$SRC_DIR/frontend/sysart/." "$FRONTEND_DIR/sysart/" 2>/dev/null || true
fi
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
