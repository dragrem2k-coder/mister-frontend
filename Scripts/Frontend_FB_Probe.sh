#!/bin/bash
# ============================================================
# Framebuffer-Sondierung - erscheint im MiSTer-OSD unter "Scripts".
#
# Startet tools/fb_probe.py, zeigt das Ergebnis auf dem Bildschirm
# UND schreibt es nach /media/fat/frontend/fb_probe.txt - diese Datei
# ist das, was zurueckgeschickt werden soll.
#
# Das Skript zeichnet nichts und aendert nichts dauerhaft: es liest die
# Framebuffer-Geometrie, probiert einmal das Umschalten und stellt es
# sofort zurueck.
# ============================================================

PY=""
for KANDIDAT in \
    /media/fat/frontend/fb_probe.py \
    /media/fat/frontend/tools/fb_probe.py \
    /media/fat/Scripts/fb_probe.py
do
    [ -f "$KANDIDAT" ] && PY="$KANDIDAT" && break
done

if [ -z "$PY" ]; then
    echo "fb_probe.py nicht gefunden."
    echo "Bitte nach /media/fat/frontend/fb_probe.py kopieren."
    echo
    echo "Beliebige Taste zum Beenden ..."
    read -r -n 1
    exit 1
fi

AUS=/media/fat/frontend/fb_probe.txt

echo "============================================"
echo " Framebuffer-Sondierung"
echo "============================================"
echo

# Beides gleichzeitig: auf den Bildschirm und in die Datei.
python3 "$PY" 2>&1 | tee "$AUS"

echo
echo "--------------------------------------------"
echo "Ergebnis gespeichert unter:"
echo "  $AUS"
echo
echo "Diese Datei bitte zurueckschicken."
echo
echo "Beliebige Taste zum Beenden ..."
read -r -n 1
