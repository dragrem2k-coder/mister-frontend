#!/bin/bash
# ============================================================
# Boxart-Download fuer das MiSTer-Frontend
# Laedt Cover von thumbnails.libretro.com und erzeugt
# .art-Dateien unter /media/fat/frontend/art/
#
# Startbar aus dem MiSTer-OSD (Scripts), aus der Scripts-
# Kategorie des Frontends oder per SSH.
#
# Profil-Auswahl:
#   sd  = fuer CRT (Standard)
#   hd  = fuer 1080p
#
# Aufruf mit Argument (z. B. per SSH):  boxart_download.sh hd
# Ohne (gueltiges) Argument erscheint ein Auswahlmenue.
# ============================================================

PROFIL="$1"

# Kein oder ungueltiges Argument -> Auswahlmenue anzeigen
if [ "$PROFIL" != "sd" ] && [ "$PROFIL" != "hd" ]; then
    echo "Boxart-Download - Profil waehlen:"
    echo ""
    echo "  1) SD  - fuer CRT (Standard)"
    echo "  2) HD  - fuer 1080p"
    echo ""
    printf "Auswahl [1/2, Standard 1]: "
    read -r AUSWAHL

    case "$AUSWAHL" in
        2|hd|HD) PROFIL="hd" ;;
        *)       PROFIL="sd" ;;
    esac
fi

echo ""
echo "Boxart-Download startet (Profil: $PROFIL) ..."
echo "Abbrechen jederzeit mit Strg+C - Fortschritt bleibt erhalten."
echo ""
exec /usr/bin/python3 /media/fat/frontend/mister_boxart.py "$PROFIL"