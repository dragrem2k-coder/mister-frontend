#!/bin/bash
# ============================================================
# Stream-Overlay an-/ausschalten
#
# Legt /media/fat/frontend/stream_enabled an (=an) oder entfernt sie
# (=aus). Das Frontend startet den kleinen Web-Server nur, wenn diese
# Datei existiert. Wirkt beim naechsten Frontend-Start.
#
#   stream_toggle.sh        -> umschalten
#   stream_toggle.sh on|off -> gezielt setzen
#
# Danach in OBS eine Browser-Quelle auf  http://<MiSTer-IP>:8080/
# richten; Konfiguration unter  http://<MiSTer-IP>:8080/admin
# ============================================================

FRONTEND_DIR="/media/fat/frontend"
FLAG="$FRONTEND_DIR/stream_enabled"

want="$1"
if [ -z "$want" ]; then
    if [ -e "$FLAG" ]; then want="off"; else want="on"; fi
fi

case "$want" in
    on|ON|an|AN)
        mkdir -p "$FRONTEND_DIR"
        touch "$FLAG"
        echo "Stream-Overlay: AN (wirkt beim naechsten Frontend-Start)"
        echo "OBS-Quelle:  http://<MiSTer-IP>:8080/"
        echo "Backend:     http://<MiSTer-IP>:8080/admin"
        ;;
    off|OFF|aus|AUS)
        rm -f "$FLAG"
        echo "Stream-Overlay: AUS (wirkt beim naechsten Frontend-Start)"
        ;;
    *)
        echo "Nutzung: stream_toggle.sh [on|off]"; exit 1 ;;
esac

echo ""
echo "Aktueller Stand: $([ -e "$FLAG" ] && echo AN || echo AUS)"
