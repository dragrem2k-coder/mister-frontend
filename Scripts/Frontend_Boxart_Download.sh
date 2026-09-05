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

# BUGFIX (Nutzer-Rueckmeldung: "egal ob ich Option 1 oder 2 auswaehle,
# der laedt immer nur Profil sd runter").
#
# Ursache: "read -r" entfernt den Zeilenumbruch, aber KEIN
# Wagenruecklauf-Zeichen. Liefert das Terminal die Zeile als "2\r" -
# was je nach Startweg (MiSTer-OSD, serielle Konsole, SSH-Client, das
# Frontend selbst) vorkommt - dann vergleicht das case unten "2\r"
# gegen "2". Das passt NICHT, der Zweig faellt auf "*" durch, und "*"
# bedeutete sd. Nachgestellt:
#
#     Eingabe "2"    -> hd     (richtig)
#     Eingabe "2 "   -> hd     (read entfernt Leerzeichen, die stehen in IFS)
#     Eingabe "2\r"  -> sd     <-- der gemeldete Fehler
#
# Zwei Aenderungen dagegen:
#
# 1. Die Eingabe wird von Wagenruecklauf und Leerraum befreit, bevor
#    sie verglichen wird.
# 2. Eine NICHT erkannte Eingabe faellt nicht mehr stillschweigend auf
#    sd, sondern wird als solche gemeldet. Genau dieses stille
#    Durchfallen hat den Fehler unsichtbar gemacht: das Skript tat
#    etwas anderes als verlangt und sagte kein Wort dazu.
_saeubern() {
    # tr statt Bash-Ersetzung: laeuft auch unter der sh, die MiSTer
    # mancherorts benutzt.
    printf '%s' "$1" | tr -d '\r\n\t '
}

# Kein oder ungueltiges Argument -> Auswahlmenue anzeigen
PROFIL=$(_saeubern "$PROFIL")
if [ "$PROFIL" != "sd" ] && [ "$PROFIL" != "hd" ]; then
    # Der Standard richtet sich nach dem tatsaechlich eingestellten
    # Menue-Modus (der [Menu]-Block in der MiSTer.ini, dieselbe Quelle
    # wie crt_menu_active() im Frontend) statt fest auf sd zu stehen.
    # Wer auf HDMI unterwegs ist, bekommt mit Enter jetzt auch hd.
    STANDARD=$(/usr/bin/python3 -c "import sys; sys.path.insert(0, '/media/fat/frontend'); from fe.settings import crt_menu_active; print('sd' if crt_menu_active() else 'hd')" 2>/dev/null)
    case "$STANDARD" in
        sd|hd) ;;
        *) STANDARD="sd" ;;
    esac
    if [ "$STANDARD" = "sd" ]; then
        STANDARD_NR=1
        STANDARD_TEXT="1 (SD) - dein Menue laeuft gerade auf CRT"
    else
        STANDARD_NR=2
        STANDARD_TEXT="2 (HD) - dein Menue laeuft gerade auf HDMI"
    fi

    echo "Boxart-Download - Profil waehlen:"
    echo ""
    echo "  1) SD  - fuer CRT   (Ordner art/)"
    echo "  2) HD  - fuer 1080p (Ordner art_hd/)"
    echo ""
    echo "Standard: $STANDARD_TEXT"
    echo ""
    printf "Auswahl [1/2, Enter = %s]: " "$STANDARD_NR"
    read -r AUSWAHL
    AUSWAHL=$(_saeubern "$AUSWAHL")

    case "$AUSWAHL" in
        2|hd|HD|Hd|hD|h|H) PROFIL="hd" ;;
        1|sd|SD|Sd|sD|s|S) PROFIL="sd" ;;
        "")                PROFIL="$STANDARD" ;;
        *)
            echo ""
            echo "'$AUSWAHL' ist weder 1 noch 2 - nehme den Standard ($STANDARD)."
            PROFIL="$STANDARD"
            ;;
    esac
fi

echo ""
if [ "$PROFIL" = "hd" ]; then
    echo "Boxart-Download startet - Profil HD -> /media/fat/frontend/art_hd/"
else
    echo "Boxart-Download startet - Profil SD -> /media/fat/frontend/art/"
fi
echo "Abbrechen jederzeit mit Strg+C - Fortschritt bleibt erhalten."
echo ""
exec /usr/bin/python3 /media/fat/frontend/mister_boxart.py "$PROFIL"