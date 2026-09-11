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

# ============================================================
# NEU (Build 101): Henne-Ei-Problem beim Abzeichen-Umstieg
# ============================================================
# Mit Build 99/100 wurden alle 57 Kategorie-Logos auf einen neuen,
# einheitlichen Abzeichen-Stil umgestellt. Die Installer kopieren
# sysart bewusst OHNE Ueberschreiben (sonst waere eigenes Artwork bei
# jedem Lauf weg), deshalb bekamen sie in Build 101 eine einmalige,
# per Marke gesteuerte Komplett-Ersetzung.
#
# DAS PROBLEM DABEI: auf der SD-Karte liegt zum Zeitpunkt eines
# Updates noch der ALTE Installer. Der laedt zwar das neue Repo und
# legt dabei auch den neuen Installer ab - aber sein eigener
# sysart-Schritt ist in genau diesem Lauf noch der alte. Ergebnis:
# die 15 neuen Abzeichen kaemen an, die 42 gleichnamigen nicht. Der
# Nutzer saehe eine halb umgestellte Hauptseite - das sieht nach
# kaputt aus, und er haette keinen Grund, das Update ein zweites Mal
# zu starten.
#
# DIESE STELLE LOEST DAS: Frontend_Install.sh uebergibt ganz am Ende
# per "exec bash" an dieses Skript - und zwar an die Fassung, die
# wenige Zeilen vorher frisch mitinstalliert wurde. Hier laeuft also
# schon NEUER Code, obwohl der Installer selbst noch der alte war.
# Fehlt die Marke, wird der (jetzt neue) Installer genau einmal
# nachgestartet; der ersetzt die Abzeichen, setzt die Marke und
# landet danach wieder hier - dann greift dieser Block nicht mehr und
# es geht normal mit dem Neustart weiter.
#
# DREI BREMSEN GEGEN EINE ENDLOSSCHLEIFE, alle drei muessen halten:
#   1. Der Stempel unter /tmp erlaubt hoechstens EINEN Nachlauf pro
#      Systemstart - selbst wenn die Marke aus irgendeinem Grund nie
#      gesetzt wuerde.
#   2. Nachgestartet wird nur, wenn der Installer auf der Karte die
#      Ersetzung ueberhaupt kennt (grep auf die Marke). Ein alter
#      Installer wuerde die Marke nie setzen - ihn nachzustarten
#      waere genau die Schleife, die wir verhindern wollen.
#   3. Ohne sysart-Ordner (z.B. Frontend gar nicht installiert)
#      passiert hier nichts.
ABZEICHEN_MARKE="$FRONTEND_DIR/sysart/.abzeichen_v1"
ABZEICHEN_STEMPEL="/tmp/abzeichen_nachlauf"
ABZEICHEN_INSTALLER="$SCRIPTS_DIR/Frontend_Install.sh"
if [ -d "$FRONTEND_DIR/sysart" ] \
   && [ ! -f "$ABZEICHEN_MARKE" ] \
   && [ ! -f "$ABZEICHEN_STEMPEL" ] \
   && [ -f "$ABZEICHEN_INSTALLER" ] \
   && grep -qF ".abzeichen_v1" "$ABZEICHEN_INSTALLER" 2>/dev/null; then
    : > "$ABZEICHEN_STEMPEL" 2>/dev/null || true
    echo ""
    echo "Die neuen Kategorie-Abzeichen fehlen noch auf der Karte."
    echo "Dafuer laeuft die Installation einmal nach (das ist normal"
    echo "und passiert nur dieses eine Mal)..."
    echo ""
    exec bash "$ABZEICHEN_INSTALLER"
fi

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

# AUFRAEUMEN (Build 77, Nutzerwunsch: "F4 kann raus komplett, auch der
# Schalter unter System, weil die Funktion ja nicht geht"). Hier wurde
# frueher der Autostart-Eintrag des F4-Waechters NACHGETRAGEN. Jetzt
# passiert das Gegenteil - und genau hier ist es am wichtigsten:
# bestehende Installationen laufen nur ueber dieses Update-Skript und
# nie wieder durch einen Installer. Ohne diesen Block bliebe bei allen,
# die den Schnellstart je installiert hatten, eine Startzeile stehen,
# die bei jedem Boot eine geloeschte Datei aufrufen will.
F4_STARTUP="/media/fat/linux/user-startup.sh"
if [ -f /tmp/f4_hotkey.lock ]; then
    F4_PID=$(cat /tmp/f4_hotkey.lock 2>/dev/null)
    if [ -n "$F4_PID" ] && kill -0 "$F4_PID" 2>/dev/null; then
        kill "$F4_PID" 2>/dev/null
        echo "Alten F4-Waechter beendet (PID $F4_PID)."
    fi
    rm -f /tmp/f4_hotkey.lock
fi
if [ -f "$F4_STARTUP" ] && grep -qF "f4_hotkey.sh" "$F4_STARTUP"; then
    grep -v "f4_hotkey.sh" "$F4_STARTUP" > "$F4_STARTUP.tmp" 2>/dev/null \
        && mv "$F4_STARTUP.tmp" "$F4_STARTUP"
    echo "Alten F4-Eintrag aus user-startup.sh entfernt."
fi
rm -f /media/fat/frontend/f4_hotkey.py /media/fat/frontend/f4_hotkey.sh \
      /media/fat/frontend/f4_hotkey

# AUFRAEUMEN (Build 102): das Scroll-Blitting aus Build 96 ist raus - es
# hat in jeder Aufloesung gekostet und in keiner etwas gebracht. Seine
# Schalter-Datei liest kein Codepfad mehr; sie liegt aber bei allen auf
# der Karte, die den Punkt im System-Menue einmal eingeschaltet hatten.
# Hier ist der eine Ort, durch den JEDE bestehende Installation kommt.
rm -f /media/fat/frontend/scroll_blit_enabled

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
# GEAENDERT (Nutzer-Rueckmeldung: "dann kam die Update-Benachrichtigung
# und ich wollte das mit Jetzt bestaetigen, danach stuerzt das Frontend
# ab und ich konnte den MiSTer neu starten"). Die Ursache liess sich
# NICHT nachweisen - und zwar aus einem hausgemachten Grund: das Log
# liegt unter /tmp (also im RAM, weg bei jedem Neustart) UND wurde hier
# zusaetzlich geloescht. Ausgerechnet in dem einen Ablauf, der mit einem
# Neustart endet, war die Spur damit garantiert vernichtet.
#
# Jetzt wird das Log VOR dem Loeschen auf die SD-Karte gerettet. Es
# bleibt genau eine Datei (wird beim naechsten Update ueberschrieben),
# kostet also dauerhaft ein paar hundert Kilobyte - der Preis dafuer,
# dass ein Absturz an dieser Stelle beim naechsten Mal nachweisbar ist
# statt nur spuerbar.
if [ -f /tmp/frontend.log ]; then
    cp -f /tmp/frontend.log "$FRONTEND_DIR/last_update.log" 2>/dev/null || true
    echo "Log des alten Frontends gesichert:"
    echo "  $FRONTEND_DIR/last_update.log"
fi
rm -f /tmp/frontend.log

if [ -e "$FRONTEND_DIR/disable" ]; then
    echo "Hinweis: Frontend ist deaktiviert (disable-Datei vorhanden)."
    echo "Aktivieren: rm $FRONTEND_DIR/disable"
    exit 0
fi

# GEAENDERT (Nutzer-Rueckmeldung: "wenn Update verfuegbar ist und man
# waehlt jetzt installieren, sollten wir nach der Installation einen
# Hardreset/kompletten Neustart machen lassen, damit die Aenderungen
# auch definitiv uebernommen sind?" - Einschaetzung geteilt und
# bestaetigt): bis hierher startete dieses Skript nur den Frontend-
# PROZESS neu (siehe Historie direkt unten, jetzt ersetzt) - das laedt
# zuverlaessig neuen PYTHON-Code, fasst aber zwei Dinge NICHT an, die
# nur bei einem echten Boot neu geladen werden: frontend_boot.sh selbst
# (das Skript, das den Frontend-Prozess beim Hochfahren ueberhaupt
# erst startet) und die Autostart-Zeile in
# /media/fat/linux/user-startup.sh. Aendert ein Update genau daran
# etwas (kam in diesem Projekt schon vor, siehe z.B. die Skript-
# Umbenennungen weiter oben in dieser Datei), wuerde der reine
# Prozess-Neustart das STILLSCHWEIGEND nicht uebernehmen - erst der
# naechste ECHTE Neustart haette gegriffen. Deshalb jetzt stattdessen
# ein kompletter MiSTer-Neustart: dauert spuerbar laenger als der
# vorherige Weg, garantiert dafuer aber wirklich JEDE installierte
# Aenderung, nicht nur den Python-Code - fuer "ich habe gerade ein
# Update installiert" ist Verlaesslichkeit wichtiger als die paar
# gesparten Sekunden. Gilt bewusst fuer BEIDE Aufrufwege gleichermassen
# (manuell ueber das Scripts-Menue UND automatisch ueber den "Update
# jetzt installieren?"-Dialog im Frontend selbst, siehe frontend.py) -
# kein Sonderfall im Code, ein einziges, konsistentes Verhalten.
#
# HISTORIE (fuer den Kontext, warum es hier vorher eine eigene
# Ueberwachungs-/Neuversuch-Logik gab): frueher startete dieses Skript
# per "exec python3 frontend.py" direkt den neuen Prozess, mit einem
# extra gebauten Sicherheitsnetz fuer den seltenen Fall, dass der
# sofort wieder abstuerzte (Nutzer-Rueckmeldung: "bleibt das Frontend
# haengen [an der rohen Linux-Konsole], passiert nicht oft aber ab und
# zu"). Bei einem echten Neustart durchlaeuft der neue Prozess ohnehin
# denselben Weg wie jeder normale Boot, inklusive des dort bereits
# LANGE bewaehrten eigenen Sicherheitsnetzes (frontend_boot.sh, siehe
# dortiger Kommentar zum "1 von 10 startet nicht richtig"-Bug) - eine
# zweite, separate Ueberwachung genau dafuer hier ist dadurch
# ueberfluessig geworden.
echo "MiSTer wird jetzt komplett neu gestartet, damit wirklich alle"
echo "installierten Aenderungen greifen (kann einen Moment dauern)..."
sync
reboot
