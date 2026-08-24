#!/bin/bash
# ============================================================
# MiSTer Custom Frontend - Installation direkt aus dem MiSTer-Menue
#
# Diese EINE Datei einmalig per WinSCP nach /media/fat/Scripts/
# kopieren. Danach im MiSTer-OSD: Scripts -> "Frontend_Install"
# antippen - der komplette Rest (Herunterladen, Einrichten,
# Autostart, NEUSTART) laeuft von selbst, ganz ohne SSH/Terminal.
#
# Kann jederzeit erneut ausgefuehrt werden (z.B. fuer ein Update) -
# vorhandene eigene Daten (Musik, heruntergeladene Boxart, Einstell-
# ungen) werden NICHT angetastet, nur die Programmdateien ersetzt.
#
# NEU (Nutzerwunsch: "Die Script-Benamungen sind nicht 'intuitiv' -
# entweder ein einheitliches Praefix oder einen eigenen Ordner, sonst
# sucht man sich nen Wolf" - Recherche ergab: MiSTers Scripts-Menue
# unterstuetzt zwar Unterordner, in der Community ist aber ein
# gemeinsames Namens-Praefix ueblicher und kostet keinen zusaetzlichen
# Menue-Klick): diese Datei hiess bis einschliesslich Build
# 2026-08-24-5 "install_frontend.sh" - jetzt "Frontend_Install.sh",
# zusammen mit allen anderen eigenen Scripts unter einem gemeinsamen
# "Frontend_"-Praefix (nur das externe MiSTer_RA.sh bleibt bewusst
# unveraendert). Wer diese Datei noch unter dem alten Namen im
# Scripts-Menue liegen hat: einfach ein letztes Mal antippen - das
# Ergebnis ist identisch, inklusive automatischem Neustart, und ab
# diesem Lauf steht die neu benannte Fassung bereit. Siehe
# Frontend_Update.sh fuer das automatische Aufraeumen der alten
# Dateinamen.
#
# NEU (Nutzer-Rueckmeldung: "Fixes wurden installiert, wirken aber
# nicht" - Ursache geklaert: dieses Skript kopierte bisher nur die
# Dateien auf die SD-Karte, der zu diesem Zeitpunkt BEREITS laufende
# Frontend-Prozess hatte seinen alten Code aber schon laengst in den
# Speicher geladen und liest ihn nie von selbst neu ein. Wurde dieses
# Skript aus dem Frontend-Menue selbst heraus gestartet (System ->
# Scripts -> Frontend_Install), kehrte man danach ueber
# back_to_frontend() einfach in genau diese ALTE, unveraenderte
# Instanz zurueck - ohne einen kompletten MiSTer-Neustart blieben die
# frisch installierten Fixes dadurch bis zum naechsten Booten
# unsichtbar, obwohl auf der SD-Karte laengst alles aktuell war): am
# Ende jetzt EXEC in Frontend_Update.sh statt nur "fertig" zu melden -
# das beendet den alten Frontend-Prozess zuverlaessig (dessen bereits
# bewaehrte, extra dafuer geschriebene Kill-Logik, siehe dortiger
# Kommentar, warum das dort - anders als am SKRIPTANFANG hier drueber -
# bewusst auch beim eigenen aufrufenden Elternprozess sicher
# funktioniert) und startet direkt danach selbst einen frischen
# Frontend-Prozess mit dem gerade installierten Code. Kein manueller
# Neustart mehr noetig, weder beim Erstinstall noch bei einem Update.
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
# BUGFIX (Nutzer-Rueckmeldung: "Skript startet nicht sichtbar, Frontend
# haengt danach fest" - per Log bestaetigt: subprocess.call() im
# Frontend kehrte NIE zurueck): dieses Skript funktioniert normal aus
# MiSTers eigenem OSD gestartet (dort ist die "laufende Instanz" ein
# GENUIN unabhaengiger Hintergrundprozess) - aber startet man es aus
# dem Frontend-Menue SELBST (System -> Scripts), ist die im Lockfile
# hinterlegte PID das EIGENE Elternprogramm, das gerade blockierend
# (subprocess.call()) auf genau dieses Skript wartet. Der bisherige
# Kill toetete es dabei mitten im Warten - Deadlock.
#
# KORREKTUR (per echtem "Signal 15 empfangen" im Frontend-Log bestaetigt,
# dass der erste Anlauf NICHT griff): run_script() im Frontend startet
# NICHT direkt dieses Skript, sondern eine "Wrapper-Bash" (druckt den
# Bildschirm-Reset, zeigt hinterher den Exit-Code + "Taste druecken"),
# die ERST DANACH per "bash \"\$0\" \"\$@\"" eine ZWEITE, innere Bash
# startet, die dieses Skript tatsaechlich ausfuehrt. $PPID zeigt hier
# deshalb auf die WRAPPER-Bash, nicht auf das Frontend selbst - der
# einfache Vergleich von vorhin griff nie. Der GROSSVATER-Prozess (der
# Elternteil der Wrapper-Bash) ist das eigentliche Frontend - ueber
# /proc/$PPID/stat ermittelt (Feld 4 = PPID jenes Prozesses), direkt
# mit der echten verschachtelten Struktur nachgebaut und bestaetigt.
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
cd "$TMP_DIR" || exit 1
echo "Lade aktuellen Build herunter..."
echo "(kann je nach Internetverbindung eine Weile dauern - bitte warten)"

# BUGFIX (Nutzer-Rueckmeldung: "Skript aus dem Frontend-Menue gestartet,
# geht in den Konsolenmodus und dann passiert nichts weiter" - der
# Selbstmord-Deadlock beim Beenden der laufenden Instanz war die ERSTE
# gefundene Ursache und ist behoben, aber das Problem trat auch DANACH
# noch auf): keiner der vier Download-Versuche unten hatte bislang ein
# Zeitlimit - haengt die Verbindung zu GitHub (DNS-Problem, instabiles
# Netz, o.ae.), wartet das Skript UNBEGRENZT, exakt passend zum
# gemeldeten Symptom. --connect-timeout/--max-time (curl) bzw.
# --timeout/--tries (wget) sorgen jetzt dafuer, dass ein haengender
# Download nach spaetestens 3 Minuten mit einer klaren Fehlermeldung
# abbricht, statt fuer immer zu warten - 3 Minuten sind grosszuegig
# genug fuer eine echte, nur langsame Verbindung.
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
    echo "Erster Versuch fehlgeschlagen, versuche es erneut OHNE"
    echo "SSL-Zertifikatspruefung (auf manchen MiSTer-Installationen"
    echo "sind die mitgelieferten Zertifikate veraltet)..."
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
if [ -d "$SRC_DIR/frontend/sfx_source" ]; then
    mkdir -p "$FRONTEND_DIR/sfx_source"
    cp -rn "$SRC_DIR/frontend/sfx_source/." "$FRONTEND_DIR/sfx_source/" 2>/dev/null || true
fi
if [ -d "$SRC_DIR/frontend/sfx" ]; then
    # NEU (Nutzerwunsch: eigene MP3-Sounds je Geheimnis/Theme) - direkt
    # abspielbereite Klaenge fuer play_sfx()/_play_ducked_sfx(). Gleiches
    # "nicht ueberschreiben"-Prinzip wie bei sysart/sfx_source oben.
    mkdir -p "$FRONTEND_DIR/sfx"
    cp -rn "$SRC_DIR/frontend/sfx/." "$FRONTEND_DIR/sfx/" 2>/dev/null || true
fi
if [ -d "$SRC_DIR/frontend/boot_logo" ]; then
    mkdir -p "$FRONTEND_DIR/boot_logo"
    cp -rn "$SRC_DIR/frontend/boot_logo/." "$FRONTEND_DIR/boot_logo/" 2>/dev/null || true
fi
# fe/-Paket (modulare Logik, nur bei der modularen Variante vorhanden) -
# komplettes Verzeichnis, MIT Ueberschreiben (Code-Update). Fehlt es bei
# einer modularen Installation, bricht der Start mit "ModuleNotFoundError:
# No module named 'fe'" ab - genau das Problem, das ohne diesen Block
# hier entstehen wuerde.
if [ -d "$SRC_DIR/frontend/fe" ]; then
    mkdir -p "$FRONTEND_DIR/fe"
    cp -f "$SRC_DIR"/frontend/fe/*.py "$FRONTEND_DIR/fe/" 2>/dev/null || true
fi
cp -f "$SRC_DIR"/Scripts/*.sh "$SCRIPTS_DIR/" 2>/dev/null || true
chmod +x "$FRONTEND_DIR"/*.sh "$SCRIPTS_DIR"/*.sh 2>/dev/null || true
# Sicherheitsnetz gegen Windows-Zeilenenden (CRLF): kopierte Shell-Skripte
# auf Unix-LF normalisieren - sonst scheitert bash mit "syntax error near
# unexpected token" an den \r.
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
echo "=== Installation abgeschlossen ==="
echo ""
echo "Boxart und Musik sind noch leer - sobald das Frontend laeuft,"
echo "im System-Menue \"Rescan\"/Boxart-Download nutzen, oder per SSH"
echo "siehe README.md auf GitHub (dragrem2k-coder/mister-frontend)."
echo ""

UPDATE_SCRIPT="$SCRIPTS_DIR/Frontend_Update.sh"
if [ -x "$UPDATE_SCRIPT" ] || [ -f "$UPDATE_SCRIPT" ]; then
    # NEU (siehe ausfuehrliche Begruendung im Kopfkommentar): startet
    # den frisch installierten Code JETZT, ohne manuellen Neustart -
    # exec statt Aufruf, damit diese Shell durch Frontend_Update.sh
    # ERSETZT wird (nicht als Kindprozess daneben haengen bleibt), das
    # danach seinerseits per exec in den neuen Frontend-Prozess
    # uebergeht. pause_before_exit hier bewusst VOR dem exec, nicht
    # danach - Frontend_Update.sh startet das Frontend selbst sofort
    # neu, eine Wartemeldung DANACH wuerde nie mehr angezeigt.
    echo "Frontend wird jetzt automatisch neu gestartet..."
    pause_before_exit
    exec bash "$UPDATE_SCRIPT"
fi

# Fallback (sollte praktisch nie eintreten - Frontend_Update.sh gehoert
# seit Langem zum Repo und wurde oben gerade erst mit installiert):
# ohne diese Datei bleibt nur der bisherige Hinweis auf den naechsten
# manuellen Neustart, statt das Skript mit einem unklaren Fehler
# abbrechen zu lassen.
echo "Hinweis: Frontend_Update.sh wurde nicht gefunden - bitte den"
echo "MiSTer einmal manuell neu starten, damit die installierten"
echo "Aenderungen wirksam werden."
pause_before_exit
