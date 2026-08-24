#!/bin/bash
# ============================================================
# MiSTer Custom Frontend - Installation OHNE Internet
#
# Installiert aus dem bereits heruntergeladenen Paket heraus.
# Gegenstueck zu install.sh, das den Build frisch von GitHub laedt:
#
#   install.sh          braucht Internet auf dem MiSTer, holt immer
#                       die neueste Fassung von GitHub
#   install_offline.sh  braucht KEIN Internet, nimmt genau die
#                       Dateien aus diesem Paket (dieser Ordner)
#
# Sinnvoll, wenn der MiSTer nicht am Netz haengt, wenn eine
# bestimmte (z.B. getestete) Fassung installiert werden soll oder
# wenn der Download an alten SSL-Zertifikaten scheitert.
#
# Aufruf: das Paket per WinSCP auf den MiSTer kopieren, dann
# per SSH oder aus dem OSD unter "Scripts":
#
#     ./install_offline.sh
#
# Ohne Rueckfragen:
#     ./install_offline.sh --yes                # Autostart an, Overlay aus
#     ./install_offline.sh --yes --stream       # zusaetzlich Overlay an
#     ./install_offline.sh --yes --no-autostart # ohne Autostart
#
# Eine IP-Adresse wird NICHT gebraucht - das Skript laeuft auf dem
# MiSTer selbst und arbeitet nur mit lokalen Pfaden. Die IP fuer OBS
# zeigt es am Ende an.
#
# Erneutes Ausfuehren ist gefahrlos: eigene Boxart, Metadaten, Musik,
# selbst ersetzte System-Logos und Einstellungen bleiben unangetastet,
# die bisherigen Programmdateien werden vorher gesichert.
# ============================================================

set -u

# Zielpfade (fuer Tests ueberschreibbar)
: "${MISTER_ROOT:=/media/fat}"
FRONTEND_DIR="$MISTER_ROOT/frontend"
SCRIPTS_DIR="$MISTER_ROOT/Scripts"
STARTUP="$MISTER_ROOT/linux/user-startup.sh"
LOCKFILE="/tmp/frontend.lock"

SELF_DIR="$(cd "$(dirname "$0")" && pwd)"

# Ein Paket-Ordner enthaelt sowohl frontend/frontend.py als auch dieses
# install_offline.sh daneben - daran laesst er sich zuverlaessig vom
# bereits INSTALLIERTEN Frontend unterscheiden (/media/fat/frontend hat
# kein install_offline.sh daneben liegen, nur die Programmdateien selbst).
_is_pkg() { [ -f "$1/frontend/frontend.py" ] && [ -f "$1/install_offline.sh" ]; }

# Quellpaket robust finden - egal ob dieses Skript aus dem Paketordner
# selbst, aus dessen Scripts/-Unterordner oder als Kopie in
# /media/fat/Scripts/ (OSD-Aufruf) gestartet wurde:
_find_src() {
    local d
    for d in "$SELF_DIR" "$SELF_DIR/.." \
             "$MISTER_ROOT"/MiSTer_Frontend* \
             "$MISTER_ROOT"/mister-frontend* \
             "$MISTER_ROOT"/*[Ff]rontend*; do
        [ -d "$d" ] || continue
        if _is_pkg "$d"; then (cd "$d" && pwd); return 0; fi
    done
    return 1
}
SRC="$(_find_src)" || SRC=""

WANT_AUTOSTART=1
WANT_STREAM=0
ASSUME_YES=0

for arg in "$@"; do
    case "$arg" in
        --yes|-y)        ASSUME_YES=1 ;;
        --stream)        WANT_STREAM=1 ;;
        --no-stream)     WANT_STREAM=0 ;;
        --autostart)     WANT_AUTOSTART=1 ;;
        --no-autostart)  WANT_AUTOSTART=0 ;;
        --help|-h)
            sed -n '2,36p' "$0" | sed 's/^# \{0,1\}//'
            exit 0 ;;
        *) echo "Unbekannte Option: $arg (--help fuer Hilfe)"; exit 1 ;;
    esac
done

say()  { echo "$*"; }
step() { echo; echo "--- $* ---"; }

# ------------------------------------------------------------
# 0. Vorpruefungen
# ------------------------------------------------------------
say "============================================"
say " MiSTer Custom Frontend - Installation"
say " (offline, aus diesem Paket)"
say "============================================"

if [ -z "$SRC" ]; then
    echo "FEHLER: Das Frontend-Paket wurde nicht gefunden (gesucht wird ein"
    echo "Ordner mit 'frontend/frontend.py' UND 'install_offline.sh' darin)."
    echo
    echo "Bitte den ENTPACKTEN Paketordner als Ganzes auf die SD-Karte"
    echo "kopieren - z.B. nach /media/fat/MiSTer_Frontend/ - und dieses"
    echo "Skript daraus starten (per SSH oder aus dem OSD unter Scripts)."
    exit 1
fi

if [ ! -d "$MISTER_ROOT" ]; then
    echo "FEHLER: '$MISTER_ROOT' existiert nicht."
    echo "Laeuft dieses Skript wirklich auf dem MiSTer?"
    exit 1
fi

PYBIN=""
for c in /usr/bin/python3 python3; do
    if command -v "$c" >/dev/null 2>&1; then PYBIN="$c"; break; fi
done
if [ -z "$PYBIN" ]; then
    echo "FEHLER: python3 nicht gefunden - das Frontend braucht es."
    exit 1
fi
say "Python gefunden:  $($PYBIN --version 2>&1)"

if command -v mpg123 >/dev/null 2>&1; then
    say "mpg123 gefunden:  Hintergrundmusik ist nutzbar"
else
    say "mpg123 fehlt:     Frontend laeuft normal, nur ohne Musik"
    say "                  mpg123 gehoert eigentlich zur MiSTer-Firmware"
    say "                  selbst (kein separates Paket) - falls es fehlt,"
    say "                  hilft meist ein einmaliges 'Update All' im"
    say "                  MiSTer-OSD (komplette Firmware auf den"
    say "                  neuesten Stand bringen). Danach per SSH"
    say "                  pruefen:  which mpg123"
fi

MODE="Neuinstallation"
[ -f "$FRONTEND_DIR/frontend.py" ] && MODE="Aktualisierung"
say "Modus:            $MODE"

# ------------------------------------------------------------
# 1. Rueckfragen (nur wenn eine Eingabe moeglich ist)
# ------------------------------------------------------------
if [ "$ASSUME_YES" -eq 0 ] && [ -t 0 ]; then
    echo
    read -r -p "Frontend automatisch beim Booten starten? [J/n] " a
    case "$a" in [nN]*) WANT_AUTOSTART=0 ;; esac
    read -r -p "Stream-Overlay fuer OBS mitinstallieren? [j/N] " b
    case "$b" in [jJyY]*) WANT_STREAM=1 ;; esac
fi

# ------------------------------------------------------------
# 2. Laufende Instanz beenden
# BUGFIX (siehe install_frontend.sh fuer die ausfuehrliche Begruendung):
# run_script() im Frontend startet nicht direkt dieses Skript, sondern
# eine "Wrapper-Bash", die ERST DANACH eine ZWEITE, innere Bash startet,
# die dieses Skript ausfuehrt. $PPID zeigt deshalb auf die WRAPPER-Bash,
# nicht auf das Frontend selbst - der GROSSVATER-Prozess (Elternteil
# der Wrapper-Bash) ist das eigentliche Frontend.
# ------------------------------------------------------------
if [ -f "$LOCKFILE" ]; then
    step "Laufende Instanz"
    OLD_PID="$(cat "$LOCKFILE" 2>/dev/null)"
    GRANDPARENT_PID=$(cut -d' ' -f4 /proc/$PPID/stat 2>/dev/null)
    if [ -n "$OLD_PID" ] && { [ "$OLD_PID" = "$PPID" ] || [ "$OLD_PID" = "$GRANDPARENT_PID" ]; }; then
        say "  Aus dem Frontend-Menue selbst gestartet - ueberspringe"
        say "  das Beenden der 'laufenden Instanz' (waere sie selbst)."
    elif [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
        say "  Beende laufende Instanz (PID $OLD_PID)..."
        kill "$OLD_PID" 2>/dev/null
        i=0
        while [ "$i" -lt 5 ]; do
            kill -0 "$OLD_PID" 2>/dev/null || break
            sleep 1
            i=$((i + 1))
        done
        kill -9 "$OLD_PID" 2>/dev/null
    fi
    rm -f "$LOCKFILE"
fi

# ------------------------------------------------------------
# 3. Sicherung der bisherigen Programmdateien
# ------------------------------------------------------------
if [ "$MODE" = "Aktualisierung" ]; then
    step "Sicherung der bisherigen Version"
    BACKUP="$FRONTEND_DIR/backup_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP"
    for f in "$FRONTEND_DIR"/*.py "$FRONTEND_DIR"/*.sh "$FRONTEND_DIR"/*.html; do
        [ -e "$f" ] && cp -p "$f" "$BACKUP/" 2>/dev/null
    done
    [ -d "$FRONTEND_DIR/fe" ] && cp -rp "$FRONTEND_DIR/fe" "$BACKUP/" 2>/dev/null
    say "Gesichert nach: $BACKUP"
fi

# ------------------------------------------------------------
# 4. Programmdateien kopieren
# ------------------------------------------------------------
step "Programmdateien nach $FRONTEND_DIR"
mkdir -p "$FRONTEND_DIR" || { echo "FEHLER: kann $FRONTEND_DIR nicht anlegen"; exit 1; }

COPIED=0
for f in "$SRC"/frontend/*.py "$SRC"/frontend/*.sh "$SRC"/frontend/*.html; do
    [ -e "$f" ] || continue
    cp -f "$f" "$FRONTEND_DIR/" && COPIED=$((COPIED+1))
    say "  kopiert: $(basename "$f")"
done
say "$COPIED Datei(en) kopiert."

# System-Logos: nur fehlende ergaenzen, selbst ersetzte behalten
if [ -d "$SRC/frontend/sysart" ]; then
    step "System-Logos (sysart)"
    mkdir -p "$FRONTEND_DIR/sysart"
    NEW=0; KEPT=0
    for f in "$SRC/frontend/sysart/"*.art; do
        [ -e "$f" ] || continue
        base="$(basename "$f")"
        if [ -f "$FRONTEND_DIR/sysart/$base" ]; then
            KEPT=$((KEPT+1))
        else
            cp -f "$f" "$FRONTEND_DIR/sysart/" && NEW=$((NEW+1))
        fi
    done
    extra="$SRC/frontend/sysart/_weitere_systeme_noch_nicht_unterstuetzt"
    if [ -d "$extra" ]; then
        mkdir -p "$FRONTEND_DIR/sysart/_weitere_systeme_noch_nicht_unterstuetzt"
        cp -f "$extra/"*.art \
              "$FRONTEND_DIR/sysart/_weitere_systeme_noch_nicht_unterstuetzt/" \
              2>/dev/null
    fi
    say "  $NEW neu, $KEPT vorhandene behalten"
fi

# SFX-Quelldateien (echte Klaenge statt prozedural erzeugter Toene,
# z.B. achievement.wav): gleiches "nur fehlende ergaenzen"-Prinzip.
if [ -d "$SRC/frontend/sfx_source" ]; then
    step "SFX-Quelldateien (sfx_source)"
    mkdir -p "$FRONTEND_DIR/sfx_source"
    NEW=0; KEPT=0
    for f in "$SRC/frontend/sfx_source/"*.wav; do
        [ -e "$f" ] || continue
        base="$(basename "$f")"
        if [ -f "$FRONTEND_DIR/sfx_source/$base" ]; then
            KEPT=$((KEPT+1))
        else
            cp -f "$f" "$FRONTEND_DIR/sfx_source/" && NEW=$((NEW+1))
        fi
    done
    say "  $NEW neu, $KEPT vorhandene behalten"
fi

# NEU (Nutzerwunsch: eigene MP3-Sounds je Geheimnis/Theme statt der
# prozedural erzeugten Ersatztoene) - direkt abspielbereite Klaenge fuer
# play_sfx()/_play_ducked_sfx() (SFX_DIR = .../frontend/sfx). Gleiches
# "nur fehlende ergaenzen"-Prinzip wie bei sysart/sfx_source oben, damit
# eine eigene, per Hand ersetzte Sound-Datei nicht wieder ueberschrieben
# wird.
if [ -d "$SRC/frontend/sfx" ]; then
    step "SFX-Klaenge (sfx)"
    mkdir -p "$FRONTEND_DIR/sfx"
    NEW=0; KEPT=0
    for f in "$SRC/frontend/sfx/"*.mp3; do
        [ -e "$f" ] || continue
        base="$(basename "$f")"
        if [ -f "$FRONTEND_DIR/sfx/$base" ]; then
            KEPT=$((KEPT+1))
        else
            cp -f "$f" "$FRONTEND_DIR/sfx/" && NEW=$((NEW+1))
        fi
    done
    say "  $NEW neu, $KEPT vorhandene behalten"
fi

# Boot-Logo (dragend_logo.art): gleiches Prinzip.
if [ -d "$SRC/frontend/boot_logo" ]; then
    step "Boot-Logo (boot_logo)"
    mkdir -p "$FRONTEND_DIR/boot_logo"
    NEW=0; KEPT=0
    for f in "$SRC/frontend/boot_logo/"*.art; do
        [ -e "$f" ] || continue
        base="$(basename "$f")"
        if [ -f "$FRONTEND_DIR/boot_logo/$base" ]; then
            KEPT=$((KEPT+1))
        else
            cp -f "$f" "$FRONTEND_DIR/boot_logo/" && NEW=$((NEW+1))
        fi
    done
    say "  $NEW neu, $KEPT vorhandene behalten"
fi

# fe/-Paket (modulare Logik, nur bei der modularen Variante vorhanden) -
# komplettes Verzeichnis, MIT Ueberschreiben (Code-Update, nicht
# nutzer-anpassbar wie sysart/). Fehlt es bei einer modularen
# Installation, bricht der Start mit "ModuleNotFoundError: No module
# named 'fe'" ab - genau das Problem, das ohne diesen Block hier
# entstehen wuerde.
if [ -d "$SRC/frontend/fe" ]; then
    step "Modul-Paket (fe/)"
    mkdir -p "$FRONTEND_DIR/fe"
    FE=0
    for f in "$SRC/frontend/fe/"*.py; do
        [ -e "$f" ] || continue
        cp -f "$f" "$FRONTEND_DIR/fe/" && FE=$((FE+1))
    done
    say "  $FE Modul(e) kopiert."
fi
# ------------------------------------------------------------
step "Hilfsskripte nach $SCRIPTS_DIR"
mkdir -p "$SCRIPTS_DIR"
for f in "$SRC/Scripts/"*.sh; do
    [ -e "$f" ] || continue
    cp -f "$f" "$SCRIPTS_DIR/" && say "  kopiert: $(basename "$f")"
done

# ------------------------------------------------------------
# 6. Ordner fuer eigene Inhalte (nur anlegen, nie leeren)
# ------------------------------------------------------------
step "Ordner fuer eigene Inhalte"
for d in art art_hd meta music bootanim; do
    if [ -d "$FRONTEND_DIR/$d" ]; then
        say "  vorhanden (unveraendert): $d/"
    else
        mkdir -p "$FRONTEND_DIR/$d" && say "  angelegt: $d/"
    fi
done
# Hinweistext fuer den Musikordner mitliefern, falls vorhanden
[ -f "$SRC/music/LIESMICH.txt" ] && \
    cp -f "$SRC/music/LIESMICH.txt" "$FRONTEND_DIR/music/" 2>/dev/null

# Ausfuehrbar setzen - auf exFAT/FAT32 ohne Wirkung, das ist ok
chmod +x "$FRONTEND_DIR"/*.sh 2>/dev/null
chmod +x "$SCRIPTS_DIR"/*.sh 2>/dev/null

# Sicherheitsnetz gegen Windows-Zeilenenden (CRLF): kopierte Shell-Skripte
# auf Unix-LF normalisieren. Kommen die Dateien uebers Netz/Windows mit
# CR-Zeichen an, scheitert bash sonst mit "syntax error near unexpected
# token" an den \r. Bereinigt die bereits kopierten .sh im Zielordner.
for s in "$FRONTEND_DIR"/*.sh "$SCRIPTS_DIR"/*.sh; do
    [ -f "$s" ] || continue
    tr -d '\r' < "$s" > "$s.__nl__" 2>/dev/null && mv "$s.__nl__" "$s" 2>/dev/null || true
done

# ------------------------------------------------------------
# 7. Autostart
# ------------------------------------------------------------
step "Autostart"
BOOTLINE="$FRONTEND_DIR/frontend_boot.sh &"
if [ "$WANT_AUTOSTART" -eq 1 ]; then
    mkdir -p "$(dirname "$STARTUP")"
    if [ ! -f "$STARTUP" ]; then
        printf '#!/bin/bash\n' > "$STARTUP"
        chmod +x "$STARTUP" 2>/dev/null
        say "  $STARTUP neu angelegt."
    fi
    if grep -qF "frontend_boot.sh" "$STARTUP" 2>/dev/null; then
        say "  Eintrag ist bereits vorhanden - nichts geaendert."
    else
        printf '%s\n' "$BOOTLINE" >> "$STARTUP"
        say "  Eintrag ergaenzt in $STARTUP"
    fi
    rm -f "$FRONTEND_DIR/disable"
    say "  Frontend startet ab dem naechsten Boot automatisch."
else
    say "  Uebersprungen (kein Autostart gewuenscht)."
    say "  Manuell starten: OSD -> Scripts -> start_frontend"
fi

# ------------------------------------------------------------
# 8. Stream-Overlay
# ------------------------------------------------------------
step "Stream-Overlay fuer OBS"
if [ "$WANT_STREAM" -eq 1 ]; then
    touch "$FRONTEND_DIR/stream_enabled"
    say "  Aktiviert (wirkt ab dem naechsten Frontend-Start)."
else
    say "  Nicht aktiviert."
    say "  Spaeter einschalten: OSD -> Scripts -> stream_toggle"
fi

# ------------------------------------------------------------
# 9. Abschluss
# ------------------------------------------------------------
IP="$(ip -4 addr show scope global 2>/dev/null \
      | awk '/inet /{sub(/\/.*/,"",$2); print $2; exit}')"
[ -z "$IP" ] && IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
[ -z "$IP" ] && IP="$(ifconfig 2>/dev/null \
      | awk '/inet /{print $2}' | sed 's/addr://' \
      | grep -v '^127\.' | head -1)"
[ -z "$IP" ] && IP="<MiSTer-IP>"

echo
say "============================================"
say " Fertig."
say "============================================"
say "Installiert nach: $FRONTEND_DIR"
if [ "$WANT_AUTOSTART" -eq 1 ]; then
    say "Naechster Schritt: MiSTer neu starten."
else
    say "Naechster Schritt: OSD -> Scripts -> start_frontend"
fi
say "Sofort testen ohne Neustart:  $PYBIN $FRONTEND_DIR/frontend.py"
if [ "$WANT_STREAM" -eq 1 ]; then
    echo
    say "Fuer OBS (sobald das Frontend laeuft):"
    say "  Browser-Quelle:  http://$IP:8080/"
    say "  Einstellungen:   http://$IP:8080/admin"
    say "  IP des MiSTers:  $IP"
fi
echo
say "Log bei Problemen:  /tmp/frontend.log"
