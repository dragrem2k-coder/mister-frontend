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

# Warten, bis MiSTer hochgefahren und im Menue ist (max. 60 s).
# Alle 0.2s statt jede volle Sekunde pruefen, damit wir nicht bis zu
# fast einer ganzen Sekunde unnoetig verlieren, sobald MENU bereit ist.
i=0
while [ "$i" -lt 300 ]; do
    # Genauso robust lesen wie current_core() im Frontend selbst
    # (strip \x00, Leerzeichen, \n, \r, \t) - sonst matcht "MENU" bei
    # Firmware, die zusaetzlich ein Leerzeichen/CR anhaengt, NIE, und es
    # wird sinnlos bis zum 60s-Limit gewartet.
    CORE=$(tr -d '\000\r\n\t ' < /tmp/CORENAME 2>/dev/null)
    [ "$CORE" = "MENU" ] && break
    sleep 0.2
    i=$((i + 1))
done

# Kurzer Puffer, damit MiSTer's Hauptprogramm den Menue-Wechsel wirklich
# abgeschlossen hat (vorher pauschal 2s - 1s reicht in der Praxis und
# spart eine Sekunde beim Start).
sleep 1

exec /usr/bin/python3 /media/fat/frontend/frontend.py \
    >> /tmp/frontend.log 2>&1
