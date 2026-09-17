#!/usr/bin/env bash
# ============================================================
# Prueft, dass Frontend_Install_Offline.sh sein Paket findet -
# von JEDEM der drei moeglichen Startorte aus (Build 140).
#
# Gemeldet von SuTe: startet man den Offline-Installer dort, wo er im
# Paket liegt (MiSTer_Frontend/Scripts/), bricht er ab mit
#   "FEHLER: Das Frontend-Paket wurde nicht gefunden"
# und man muss ihn erst eine Ebene hoeher kopieren.
#
# Der naheliegende Fix - den Marker auch in Scripts/ gelten lassen -
# ist allein NICHT richtig: sobald der Installer wie vorgesehen nach
# /media/fat/Scripts/ kopiert ist (OSD-Aufruf), traegt MISTER_ROOT
# selbst beide Merkmale (frontend/frontend.py von der Installation,
# Scripts/Frontend_Install_Offline.sh von der Kopie). Dann installiert
# das Skript die vorhandene Installation ueber sich selbst, meldet
# "Fertig." und aktualisiert NICHTS. Genau das prueft Test 4 - ein
# stiller Fehlschlag ist schlimmer als eine Fehlermeldung.
#
# Der Test baut sich dafuer jedes Mal einen vollstaendigen, aber
# winzigen MiSTer nach: ein Paketordner mit einer neuen Fassung, eine
# alte Installation daneben. Danach steht in der Datei entweder
# "NEUES PAKET" (richtig) oder noch "ALTE INSTALLATION" (falsch).
#
# Ausfuehren:
#     bash tools/test_offline_installer.sh
# ============================================================
set -u

HIER="$(cd "$(dirname "$0")" && pwd)"
REPO="$(dirname "$HIER")"
INSTALLER="$REPO/Scripts/Frontend_Install_Offline.sh"

fehler=0

pruefe() {
    if [ "$2" = "$3" ]; then
        printf "  OK   %s\n" "$1"
    else
        printf "  FEHL %s\n         erwartet: %s\n         bekommen: %s\n" \
               "$1" "$3" "$2"
        fehler=$((fehler + 1))
    fi
}

# Baut einen Mini-MiSTer auf und liefert dessen Wurzel.
#
#   $1 = 1: der Installer liegt AUCH oben im Paketordner. So sah ein
#           von Hand zusammengestelltes Paket frueher aus - und genau
#           deshalb ist der Fehler so lange niemandem aufgefallen.
#           Im ausgelieferten Paket liegt er NUR in Scripts/ (0).
#   $2 = 1: der Installer liegt zusaetzlich in /media/fat/Scripts -
#           so macht man es fuer den Aufruf ueber das OSD.
mini_mister() {
    local wurzel
    wurzel="$(mktemp -d)"
    mkdir -p "$wurzel/MiSTer_Frontend/frontend" \
             "$wurzel/MiSTer_Frontend/Scripts" \
             "$wurzel/Scripts" "$wurzel/frontend" "$wurzel/linux"
    cp "$INSTALLER" "$wurzel/MiSTer_Frontend/Scripts/"
    echo "NEUES PAKET" > "$wurzel/MiSTer_Frontend/frontend/frontend.py"
    echo "ALTE INSTALLATION" > "$wurzel/frontend/frontend.py"
    [ "${1:-0}" = "1" ] && cp "$INSTALLER" "$wurzel/MiSTer_Frontend/"
    [ "${2:-0}" = "1" ] && cp "$INSTALLER" "$wurzel/Scripts/"
    echo "$wurzel"
}

# Startet den Installer und liefert, was danach installiert ist.
starte() {
    local wurzel="$1" von="$2"
    MISTER_ROOT="$wurzel" bash "$wurzel/$von/Frontend_Install_Offline.sh" \
        --yes >/dev/null 2>&1
    cat "$wurzel/frontend/frontend.py" 2>/dev/null | tr -d '\n'
}

echo "Test 1: Start aus dem Paketordner selbst"
# Dafuer muss der Installer dort auch liegen - also die alte
# Paketform. Genau so lautet auch der bisherige Behelf: Skript eine
# Ebene hoeher kopieren und von dort starten.
W="$(mini_mister 1 0)"
pruefe "MiSTer_Frontend/" "$(starte "$W" "MiSTer_Frontend")" "NEUES PAKET"
rm -rf "$W"

echo
echo "Test 2: Start aus Scripts/ IM Paket - das war der gemeldete Fehler"
# So liegt der Installer im ausgelieferten Paket: NUR in Scripts/.
W="$(mini_mister 0 0)"
pruefe "MiSTer_Frontend/Scripts/" \
       "$(starte "$W" "MiSTer_Frontend/Scripts")" "NEUES PAKET"
rm -rf "$W"

echo
echo "Test 3: Start ueber das OSD (Kopie in /media/fat/Scripts)"
W="$(mini_mister 0 1)"
pruefe "Scripts/ neben der Installation" \
       "$(starte "$W" "Scripts")" "NEUES PAKET"
rm -rf "$W"

echo
echo "Test 4: der Zielort selbst darf NIE als Paket gelten"
# Ohne diese Ausnahme findet der OSD-Aufruf /media/fat als "Paket",
# kopiert die alte Installation ueber sich selbst und meldet "Fertig.".
W="$(mini_mister 0 1)"
ergebnis="$(starte "$W" "Scripts")"
pruefe "es wird nicht die alte Installation ueber sich selbst gelegt" \
       "$ergebnis" "NEUES PAKET"
rm -rf "$W"

echo
echo "Test 5: die alte Paketform bleibt in jeder Lage benutzbar"
# Aeltere, von Hand zusammengestellte Pakete haben den Installer oben
# UND in Scripts/. Sie haben immer funktioniert und muessen das weiter
# tun - auch neben einer vorhandenen Installation und einer OSD-Kopie.
W="$(mini_mister 1 1)"
pruefe "alte Paketform, Start aus Scripts/ im Paket" \
       "$(starte "$W" "MiSTer_Frontend/Scripts")" "NEUES PAKET"
rm -rf "$W"
W="$(mini_mister 1 1)"
pruefe "alte Paketform, Start ueber das OSD" \
       "$(starte "$W" "Scripts")" "NEUES PAKET"
rm -rf "$W"

echo
echo "Test 6: ohne Paket kommt weiterhin eine ehrliche Fehlermeldung"
# Der Schutz aus Test 4 darf nicht dazu fuehren, dass irgendein Ordner
# durchrutscht - wo wirklich kein Paket liegt, muss es das auch sagen.
W="$(mktemp -d)"
mkdir -p "$W/Scripts" "$W/frontend" "$W/linux"
cp "$INSTALLER" "$W/Scripts/"
echo "ALTE INSTALLATION" > "$W/frontend/frontend.py"
ausgabe="$(MISTER_ROOT="$W" bash "$W/Scripts/Frontend_Install_Offline.sh" \
           --yes 2>&1)"
case "$ausgabe" in
    *"nicht gefunden"*)
        printf "  OK   %s\n" "kein Paket da -> Fehlermeldung" ;;
    *)
        printf "  FEHL %s\n" "kein Paket da, aber keine Fehlermeldung"
        fehler=$((fehler + 1)) ;;
esac
pruefe "und die Installation bleibt unangetastet" \
       "$(tr -d '\n' < "$W/frontend/frontend.py")" "ALTE INSTALLATION"
rm -rf "$W"

echo
if [ "$fehler" -gt 0 ]; then
    echo "FEHLGESCHLAGEN: $fehler"
    exit 1
fi
echo "Alle Tests bestanden."
