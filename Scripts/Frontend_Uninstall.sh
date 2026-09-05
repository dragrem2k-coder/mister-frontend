#!/bin/bash
# ============================================================
# MiSTer Custom Frontend - Deinstallation
#
# Entfernt Autostart, Scripts und optional die Programmdateien
# wieder. Fragt nach, ob eigene Boxart/Musik/Einstellungen ebenfalls
# geloescht werden sollen, oder nur die Programmdateien selbst.
#
# Aufruf: ./Frontend_Uninstall.sh          (fragt nach)
#         ./Frontend_Uninstall.sh --yes    (entfernt alles ohne Rueckfrage)
#         ./Frontend_Uninstall.sh --keep-data  (Programmdateien weg, eigene
#                                       Daten bleiben, ohne Rueckfrage)
#
# NEU: diese Datei hiess bis einschliesslich Build 2026-08-24-5
# "uninstall.sh" - jetzt umbenannt, siehe Kopfkommentar in
# Frontend_Install.sh fuer die Begruendung.
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
# BEWUSST OHNE den Selbstmord-Schutz aus Frontend_Install.sh/
# Frontend_Install_Remote.sh/Frontend_Install_Offline.sh/
# Frontend_Update.sh: bei einer Deinstallation SOLL
# das Frontend danach nicht mehr laufen, egal ob dieses Skript aus
# MiSTers eigenem OSD oder aus dem Frontend-Menue selbst gestartet
# wurde - der Kill hier ist das gewuenschte Ergebnis, nicht ein
# Seiteneffekt, der vermieden werden muesste. Der Kind-Prozess (dieses
# Skript) laeuft dank setsid() in _ctty() ohnehin in einer eigenen
# Sitzung weiter und wird von einem sterbenden Elternprozess nicht
# beeintraechtigt - die restlichen Aufraeumschritte laufen also auch
# dann sauber zu Ende, wenn der Kill hier tatsaechlich das aufrufende
# Frontend selbst trifft.
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

# --- Reste des alten F4-Schnellstarts entfernen ---
# Den F4-Schnellstart gibt es seit Build 77 nicht mehr (siehe CHANGELOG).
# Wer ihn frueher installiert hatte, kann aber noch einen laufenden
# Waechter und einen Eintrag in user-startup.sh haben - beides muss weg,
# sonst bleibt nach der Deinstallation ein Prozess uebrig, der bei jedem
# Boot eine nicht mehr vorhandene Datei zu starten versucht.
if [ -f /tmp/f4_hotkey.lock ]; then
    F4_PID=$(cat /tmp/f4_hotkey.lock 2>/dev/null)
    if [ -n "$F4_PID" ] && kill -0 "$F4_PID" 2>/dev/null; then
        kill "$F4_PID" 2>/dev/null
        echo "F4-Waechter beendet (PID $F4_PID)."
    fi
    rm -f /tmp/f4_hotkey.lock
fi
if [ -f "$STARTUP_FILE" ] && grep -q "f4_hotkey.sh" "$STARTUP_FILE"; then
    grep -v "f4_hotkey.sh" "$STARTUP_FILE" > "$STARTUP_FILE.tmp" 2>/dev/null
    mv "$STARTUP_FILE.tmp" "$STARTUP_FILE"
    echo "F4-Schnellstart-Eintrag entfernt."
fi

# --- Video-Reste aus der MiSTer.ini entfernen ---
# NEU (Nutzerwunsch nach einem Fehlerbild bei einem Bekannten, dessen
# HDMI-Bild nach dem Start des Frontends wackelte): diese
# Deinstallation versprach bisher eine rueckstandsfreie Entfernung,
# fasste die MiSTer.ini aber ueberhaupt nicht an. Das Frontend kann
# darin genau zwei Dinge veraendern - den [Menu]-Block (CRT-Modus) und
# fb_size (Menue-Aufloesung). Beides sind Video-Einstellungen, die nach
# einer Deinstallation niemand mehr dem Frontend zuordnen wuerde.
#
# WICHTIG: der [Menu]-Block wird nur entfernt, wenn er auch wirklich vom
# Frontend stammt (Markierungsdatei oder wortgleicher Inhalt, siehe
# fe/settings.py) - ein selbst angelegter Block bleibt unangetastet.
#
# Muss VOR dem Loeschen der Programmdateien laufen, das Skript liegt
# selbst im Frontend-Ordner.
if [ -f "$FRONTEND_DIR/mister_ini_cleanup.py" ]; then
    python3 "$FRONTEND_DIR/mister_ini_cleanup.py" 2>/dev/null \
        || echo "MiSTer.ini: Aufraeumen uebersprungen."
else
    echo "MiSTer.ini: Aufraeumskript nicht gefunden - uebersprungen."
fi

# --- Scripts entfernen ---
# NEU: neue ("Frontend_"-Praefix, seit Build 2026-08-24-6) UND alte
# Dateinamen (falls hier noch von einer vor der Umbenennung installierten
# Fassung liegen geblieben) werden entfernt - so raeumt eine
# Deinstallation zuverlaessig auf, unabhaengig davon, wann zuletzt
# aktualisiert wurde.
for s in Frontend_Start.sh Frontend_Update.sh Frontend_Boxart_Download.sh \
         Frontend_Gameinfo_Download.sh Frontend_Stream_Toggle.sh \
         start_frontend.sh update_frontend.sh boxart_download.sh \
         gameinfo_download.sh stream_toggle.sh; do
    rm -f "$SCRIPTS_DIR/$s"
done
echo "Scripts aus $SCRIPTS_DIR entfernt."

# --- Eigene Daten behalten oder komplett loeschen? ---
if [ -z "$MODE" ]; then
    echo ""
    read -r -p "Auch eigene Boxart/Musik/Einstellungen loeschen? (j/N) " antwort
    # Wagenruecklauf entfernen: je nach Konsole liefert read "j\r"
    # statt "j", und der exakte Vergleich unten haette das
    # stillschweigend als "nein" gewertet. Siehe die ausfuehrliche
    # Begruendung in Frontend_Boxart_Download.sh - dort hat genau das
    # dazu gefuehrt, dass eine Auswahl wirkungslos blieb.
    antwort=$(printf '%s' "$antwort" | tr -d '\r\n\t ')
    case "$antwort" in
        j|J|ja|Ja|JA|y|Y|yes|Yes) MODE="all" ;;
        *)                        MODE="keep" ;;
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
