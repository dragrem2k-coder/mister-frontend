#!/bin/bash
# ============================================================
# Frontend nach einem Datei-Update sauber neu starten
#
# Ablauf fuer ein Update:
#   1. Neue Dateien (frontend.py usw.) per WinSCP nach
#      /media/fat/frontend/ kopieren (alte ueberschreiben)
#   2. DANACH dieses Skript ausfuehren - per SSH oder aus dem
#      MiSTer-OSD (Hauptmenue -> Scripts -> Frontend_Update)
#
# Ersetzt den bisherigen manuellen Ablauf
# (kill $(cat /tmp/frontend.lock); rm -f ...; python3 frontend.py)
# durch einen einzigen Befehl.
#
# NEU: diese Datei hiess bis einschliesslich Build 2026-08-24-5
# "update_frontend.sh" - jetzt umbenannt, siehe Kopfkommentar in
# Frontend_Install.sh fuer die Begruendung. Ein duenner Kompatibilitaets-
# Platzhalter unter dem ALTEN Namen ("Scripts/update_frontend.sh", nur
# noch ein exec auf diese Datei hier) bleibt vorerst zusaetzlich im
# Repo, DAMIT eine bereits auf der SD-Karte liegende, noch nicht
# aktualisierte Fassung von Frontend_Install.sh (die unter ihrem alten
# Namen "install_frontend.sh" noch fest auf "update_frontend.sh"
# verweist) beim naechsten Ausfuehren trotzdem sauber hierher
# durchreicht, statt mit einer Fehlermeldung abzubrechen.
# ============================================================

FRONTEND_DIR="/media/fat/frontend"
SCRIPTS_DIR="/media/fat/Scripts"
LOCKFILE="/tmp/frontend.lock"

echo "Frontend-Update wird angewendet..."

# NEU: alte, vor dem "Frontend_"-Praefix-Umzug benannte Script-Kopien
# aufraeumen, falls noch vorhanden - dieser Punkt hier ist der
# gemeinsame Endpunkt JEDES Install-/Update-Wegs (egal ob ueber den
# neuen Frontend_Install.sh oder - via Kompatibilitaets-Platzhalter -
# eine bereits installierte, noch alte Fassung), deshalb der
# zuverlaessigste Ort fuer dieses einmalige Aufraeumen. Nur echte
# Karteileichen (jede neu benannte Datei existiert zu diesem Zeitpunkt
# schon, da der jeweilige Install-Schritt bereits gelaufen ist, bevor
# hierher verzweigt wird) - eine eigene, per Hand angelegte Datei mit
# einem dieser Namen gaebe es nicht, das waeren ausschliesslich vom
# Installer selbst kopierte Programmdateien.
for old in start_frontend.sh update_frontend.sh boxart_download.sh \
           gameinfo_download.sh stream_toggle.sh install.sh \
           install_frontend.sh install_offline.sh uninstall.sh; do
    [ -f "$SCRIPTS_DIR/$old" ] && rm -f "$SCRIPTS_DIR/$old"
done

# BEWUSST OHNE den Selbstmord-Schutz aus Frontend_Install.sh/
# Frontend_Install_Remote.sh/Frontend_Install_Offline.sh: hier ist der
# Kill tatsaechlich beabsichtigt UND
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
