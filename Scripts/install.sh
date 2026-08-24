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
#   curl -Ls https://raw.githubusercontent.com/dragrem2k-coder/mister-frontend/main/Scripts/install.sh | bash
#
# oder, falls curl nicht vorhanden ist:
#
#   wget -qO- https://raw.githubusercontent.com/dragrem2k-coder/mister-frontend/main/Scripts/install.sh | bash
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
# BUGFIX (siehe Scripts/install_frontend.sh fuer die ausfuehrliche
# Begruendung - identisches Problem, UND identische Korrektur noetig):
# run_script() im Frontend startet nicht direkt dieses Skript, sondern
# eine "Wrapper-Bash" (Bildschirm-Reset, danach Exit-Code-Anzeige +
# "Taste druecken"), die ERST DANACH per "bash \"\$0\" \"\$@\"" eine
# ZWEITE, innere Bash startet, die dieses Skript ausfuehrt. $PPID zeigt
# deshalb auf die WRAPPER-Bash, nicht auf das Frontend selbst - ein
# einfacher Vergleich gegen $PPID allein reicht nicht. Der GROSSVATER-
# Prozess (Elternteil der Wrapper-Bash) ist das eigentliche Frontend -
# ueber /proc/$PPID/stat ermittelt (Feld 4 = PPID jenes Prozesses).
if [ -f "$LOCKFILE" ]; then
    OLD_PID=$(cat "$LOCKFILE" 2>/dev/null)
    GRANDPARENT_PID=$(cut -d' ' -f4 /proc/$PPID/stat 2>/dev/null)
    if [ -n "$OLD_PID" ] && { [ "$OLD_PID" = "$PPID" ] || [ "$OLD_PID" = "$GRANDPARENT_PID" ]; }; then
        echo "Aus dem Frontend-Menue selbst gestartet - ueberspringe"
        echo "das Beenden der 'laufenden Instanz' (waere sie selbst)."
        echo "Das Frontend kehrt nach diesem Skript automatisch zurueck."
    elif [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
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

# BUGFIX (siehe Scripts/install_frontend.sh fuer die ausfuehrliche
# Begruendung - identisches Risiko: keiner der Download-Versuche hatte
# bislang ein Zeitlimit, ein haengendes Netzwerk wuerde das Skript
# unbegrenzt warten lassen)
download_ok=0
if [ "$TOOL" = "curl" ]; then
    curl -L --fail --show-error --connect-timeout 15 --max-time 180 \
        -o build.zip "$REPO_ZIP" 2>dl_err.txt \
        && download_ok=1
else
    wget --timeout=30 --tries=2 -O build.zip "$REPO_ZIP" 2>dl_err.txt \
        && download_ok=1
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
        curl -L --fail --show-error -k --connect-timeout 15 --max-time 180 \
            -o build.zip "$REPO_ZIP" 2>dl_err2.txt \
            && download_ok=1
    else
        wget --no-check-certificate --timeout=30 --tries=2 \
            -O build.zip "$REPO_ZIP" 2>dl_err2.txt \
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
if [ -d "$SRC_DIR/frontend/sfx_source" ]; then
    # Quelldatei(en) fuer echte (statt prozedural erzeugte) SFX-Klaenge
    # (z.B. achievement.wav) - gleiches "nicht ueberschreiben"-Prinzip
    # wie bei sysart oben, falls jemand eine eigene Datei eingesetzt hat.
    mkdir -p "$FRONTEND_DIR/sfx_source"
    cp -rn "$SRC_DIR/frontend/sfx_source/." "$FRONTEND_DIR/sfx_source/" 2>/dev/null || true
fi
if [ -d "$SRC_DIR/frontend/sfx" ]; then
    # NEU (Nutzerwunsch: eigene MP3-Sounds je Geheimnis/Theme statt der
    # prozedural erzeugten Ersatztoene) - direkt abspielbereite Klaenge
    # fuer play_sfx()/_play_ducked_sfx() (SFX_DIR = .../frontend/sfx).
    # Gleiches "nicht ueberschreiben"-Prinzip wie bei sysart/sfx_source
    # oben, falls jemand eine eigene Sound-Datei mit demselben Namen
    # hinterlegt hat.
    mkdir -p "$FRONTEND_DIR/sfx"
    cp -rn "$SRC_DIR/frontend/sfx/." "$FRONTEND_DIR/sfx/" 2>/dev/null || true
fi
if [ -d "$SRC_DIR/frontend/boot_logo" ]; then
    # Boot-Logo (dragend_logo.art) - gleiches Prinzip, eigene Datei
    # wird nicht ueberschrieben.
    mkdir -p "$FRONTEND_DIR/boot_logo"
    cp -rn "$SRC_DIR/frontend/boot_logo/." "$FRONTEND_DIR/boot_logo/" 2>/dev/null || true
fi
# fe/-Paket (modulare Logik, nur bei der modularen Variante vorhanden) -
# komplettes Verzeichnis, MIT Ueberschreiben (Code-Update, nicht
# nutzer-anpassbar wie sysart/). Fehlt es bei einer modularen
# Installation, bricht der Start mit "ModuleNotFoundError: No module
# named 'fe'" ab - genau das Problem, das ohne diesen Block hier
# entstehen wuerde.
if [ -d "$SRC_DIR/frontend/fe" ]; then
    mkdir -p "$FRONTEND_DIR/fe"
    cp -f "$SRC_DIR"/frontend/fe/*.py "$FRONTEND_DIR/fe/" 2>/dev/null || true
fi
cp -f "$SRC_DIR"/Scripts/*.sh "$SCRIPTS_DIR/" 2>/dev/null || true
chmod +x "$FRONTEND_DIR"/*.sh "$SCRIPTS_DIR"/*.sh 2>/dev/null || true
# Sicherheitsnetz gegen Windows-Zeilenenden (CRLF): kopierte Shell-Skripte
# auf Unix-LF normalisieren. Kommen die Dateien uebers Netz/Windows mit
# CR-Zeichen an, scheitert bash sonst mit "syntax error near unexpected
# token" an den \r. Bereinigt die bereits kopierten .sh im Zielordner.
for s in "$FRONTEND_DIR"/*.sh "$SCRIPTS_DIR"/*.sh; do
    [ -f "$s" ] || continue
    tr -d '\r' < "$s" > "$s.__nl__" 2>/dev/null && mv "$s.__nl__" "$s" 2>/dev/null || true
done

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
if command -v mpg123 >/dev/null 2>&1; then
    echo "mpg123 gefunden:  Hintergrundmusik ist nutzbar"
else
    echo "mpg123 fehlt:     Frontend laeuft normal, nur ohne Musik"
    echo "                  mpg123 gehoert eigentlich zur MiSTer-Firmware"
    echo "                  selbst (kein separates Paket) - falls es fehlt,"
    echo "                  hilft meist ein einmaliges 'Update All' im"
    echo "                  MiSTer-OSD (komplette Firmware auf den"
    echo "                  neuesten Stand bringen). Danach per SSH"
    echo "                  pruefen:  which mpg123"
fi

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
