#!/bin/bash
# ============================================================
# Boxart-Download fuer das MiSTer-Frontend
# Erzeugt .art-Dateien unter /media/fat/frontend/art/ (bzw.
# art_hd/ fuer HD). Seit mister_boxart.py v4.0: zwei Quellen
# automatisch kombiniert - zuerst ein schneller Mirror mit
# bereits fertigen .art-Dateien (kein Dekodieren auf dem MiSTer
# noetig), fuer alles, was der Mirror nicht liefert, automatisch
# ein Rueckfall auf den bisherigen Weg (thumbnails.libretro.com,
# Fallback GitHub). Details siehe Kopfkommentar in mister_boxart.py.
#
# Startbar aus dem MiSTer-OSD (Scripts), aus der Scripts-
# Kategorie des Frontends oder per SSH.
#
# Profil-Auswahl:
#   sd  = fuer CRT (Standard)
#   hd  = fuer 1080p
#
# Aufruf mit Argument (z. B. per SSH):  Frontend_Boxart_Download.sh hd
# Ohne (gueltiges) Argument erscheint ein Auswahlmenue.
#
# NEU: diese Datei hiess bis einschliesslich Build 2026-08-24-5
# "boxart_download.sh" - jetzt umbenannt, siehe Kopfkommentar in
# Frontend_Install.sh fuer die Begruendung. frontend.py ruft sie
# passend dazu jetzt ebenfalls unter dem neuen Namen auf.
#
# Bleibt bewusst der EINZIGE Boxart-Launcher (sd/hd per Argument
# oder Menue) statt zwei getrennter Dateien - vermeidet die
# Skript-Namens-Unuebersichtlichkeit, die an anderer Stelle in
# diesem Projekt gerade erst aufgeraeumt wurde.
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