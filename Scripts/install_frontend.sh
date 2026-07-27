#!/bin/bash
# ============================================================
# MiSTer Custom Frontend - Installation direkt aus dem MiSTer-Menue
#
# Diese EINE Datei einmalig per WinSCP nach /media/fat/Scripts/
# kopieren. Danach im MiSTer-OSD: Scripts -> "install frontend"
# antippen - der komplette Rest (Herunterladen, Einrichten,
# Autostart) laeuft von selbst, ganz ohne SSH/Terminal.
#
# Kann jederzeit erneut ausgefuehrt werden (z.B. fuer ein Update) -
# vorhandene eigene Daten (Musik, heruntergeladene Boxart, Einstell-
# ungen) werden NICHT angetastet, nur die Programmdateien ersetzt.
# ============================================================

REPO_ZIP="https://github.com/dragrem2k-coder/mister-frontend/archive/refs/heads/main.zip"
FRONTEND_DIR="/media/fat/frontend"
SCRIPTS_DIR="/media/fat/Scripts"
TMP_DIR="/tmp/frontend_install_$$"
LOCKFILE="/tmp/frontend.lock"

pause_before_exit() {
    # Im MiSTer-OSD verschwindet die Ausgabe sonst sofort wieder,
    # sobald das Skript endet - hier auf einen Tastendruck warten,
    # damit die Meldung tatsaechlich gelesen werden kann.
    echo ""
    read -n 1 -s -r -p "Taste druecken, um zurueck ins Menue zu gehen..."
    echo ""
}

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
    echo "siehe README.md, Abschnitt 3."
    pause_before_exit
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
cd "$TMP_DIR" || exit 1
echo "Lade aktuellen Build herunter..."
echo "(kann je nach Internetverbindung eine Weile dauern - bitte warten)"

download_ok=0
if [ "$TOOL" = "curl" ]; then
    curl -L --fail --show-error -o build.zip "$REPO_ZIP" 2>dl_err.txt \
        && download_ok=1
else
    wget -O build.zip "$REPO_ZIP" 2>dl_err.txt && download_ok=1
fi

if [ "$download_ok" != "1" ]; then
    echo ""
    echo "Erster Versuch fehlgeschlagen, versuche es erneut OHNE"
    echo "SSL-Zertifikatspruefung (auf manchen MiSTer-Installationen"
    echo "sind die mitgelieferten Zertifikate veraltet)..."
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
    echo "FEHLER: Download fehlgeschlagen. Pruefe, ob der MiSTer"
    echo "gerade Internetzugang hat (WLAN/LAN-Kabel), und versuch es"
    echo "danach nochmal. Falls es weiterhin nicht klappt: per SSH"
    echo "'ping -c 2 github.com' testen, oder die Dateien manuell per"
    echo "WinSCP kopieren (README.md, Abschnitt 3)."
    rm -rf "$TMP_DIR"
    pause_before_exit
    exit 1
fi
echo "Download erfolgreich."

echo "Entpacke..."
if command -v unzip >/dev/null 2>&1; then
    unzip -q build.zip
else
    echo "FEHLER: unzip nicht gefunden - kann das Archiv nicht entpacken."
    rm -rf "$TMP_DIR"
    pause_before_exit
    exit 1
fi

SRC_DIR=$(find . -maxdepth 1 -type d -name "mister-frontend-*" | head -1)
if [ -z "$SRC_DIR" ] || [ ! -d "$SRC_DIR/frontend" ]; then
    echo "FEHLER: Entpackte Struktur sieht nicht wie erwartet aus."
    rm -rf "$TMP_DIR"
    pause_before_exit
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
    # wieder auf die Standard-Bilder aus dem Repo zurueckgesetzt.
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
echo ""
echo "Boxart und Musik sind noch leer - sobald das Frontend laeuft,"
echo "im System-Menue \"Rescan\"/Boxart-Download nutzen, oder per SSH"
echo "siehe README.md auf GitHub (dragrem2k-coder/mister-frontend)."
pause_before_exit
