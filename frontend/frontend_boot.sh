#!/bin/bash
# ============================================================
# MiSTer Frontend - Autostart-Wrapper
# Wird von /media/fat/linux/user-startup.sh beim Booten gerufen.
#
# Not-Aus: Datei /media/fat/frontend/disable anlegen,
# dann startet das Frontend beim naechsten Boot NICHT.
# (z.B. per SSH:  touch /media/fat/frontend/disable )
# ============================================================

# Deaktivierungs-Schalter pruefen
[ -e /media/fat/frontend/disable ] && exit 0

# Sicherheitsnetz: falls die Log-Datei durch rohe Fehlerausgaben
# (Python-Tracebacks ueber stderr, ausserhalb der eigenen LOG()-
# Kuerzung) trotzdem zu gross geworden ist, hier zusaetzlich kappen.
# LOG() selbst kuerzt waehrend des Betriebs bereits automatisch -
# das hier faengt nur den Fall ab, dass der Prozess vorher abgestuerzt
# ist und dabei viel rohen Text ueber stderr geschrieben hat.
LOGFILE="/tmp/frontend.log"
if [ -f "$LOGFILE" ]; then
    SIZE=$(wc -c < "$LOGFILE" 2>/dev/null || echo 0)
    if [ "$SIZE" -gt 1048576 ]; then
        tail -c 262144 "$LOGFILE" > "$LOGFILE.tmp" 2>/dev/null \
            && mv "$LOGFILE.tmp" "$LOGFILE"
    fi
fi

# Warten, bis MiSTer hochgefahren und im Menue ist (max. 60 s)
for i in $(seq 1 60); do
    CORE=$(tr -d '\0' < /tmp/CORENAME 2>/dev/null)
    [ "$CORE" = "MENU" ] && break
    sleep 1
done

# Dem MiSTer-Hauptprogramm noch einen Moment geben
sleep 2

exec /usr/bin/python3 /media/fat/frontend/frontend.py \
    >> /tmp/frontend.log 2>&1
