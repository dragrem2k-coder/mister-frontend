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

# Warten, bis MiSTer hochgefahren und im Menue ist (max. 120 s).
# Alle 0.2s statt jede volle Sekunde pruefen, damit wir nicht bis zu
# fast einer ganzen Sekunde unnoetig verlieren, sobald MENU bereit ist.
#
# BUGFIX (Nutzer-Rueckmeldung: "1 von 10 Faellen startet nicht richtig,
# bleibt im OSD"): die Obergrenze war bisher 60s (300 Schritte). Auf
# Systemen, deren Boot-Zeit knapp UM diese Marke schwankt (langsamere
# SD-Karte, grosse ROM-Sammlung, die MiSTer's eigenes Menue laenger
# indizieren laesst), lief das Warten manchmal in den Timeout, WORAUFHIN
# das Skript trotzdem blind weitermachte - ohne zu wissen, ob MiSTer
# tatsaechlich fertig war. Startete dann der Framebuffer, waehrend
# MiSTer selbst noch mitten im Uebergang vom OSD steckte, stuerzte das
# Frontend beim Start ab (sauber geloggt, aber eben abgestuerzt) - das
# alte OSD blieb einfach stehen, siehe Frontend._draw_scan_progress()-
# Kopfkommentar/CRASH-Log-Eintrag fuer die Absturz-Seite dieses Bugs.
#
# Fix, Teil 1 (dieser hier): Obergrenze auf 120s verdoppelt. WICHTIG:
# das verlangsamt den Start fuer NIEMANDEN, der schon vorher zuverlaessig
# funktioniert hat - die Schleife bricht IMMER sofort ab, sobald CORE
# tatsaechlich "MENU" meldet (siehe break unten), unabhaengig von der
# Obergrenze. Die Obergrenze wird nur in genau dem Ausnahmefall
# ausgeschoepft, den wir hier beheben wollen - und selbst dann ist ein
# spaeterer, aber ZUVERLAESSIGER Start besser als ein schneller, aber
# unzuverlaessiger. Fix, Teil 2: siehe frontend.py (Neuversuch beim
# Framebuffer-Oeffnen, falls MiSTer trotzdem noch nicht ganz bereit ist).
i=0
while [ "$i" -lt 600 ]; do
    # Genauso robust lesen wie current_core() im Frontend selbst
    # (strip \x00, Leerzeichen, \n, \r, \t) - sonst matcht "MENU" bei
    # Firmware, die zusaetzlich ein Leerzeichen/CR anhaengt, NIE, und es
    # wird sinnlos bis zum Limit gewartet.
    CORE=$(tr -d '\000\r\n\t ' < /tmp/CORENAME 2>/dev/null)
    [ "$CORE" = "MENU" ] && break
    sleep 0.2
    i=$((i + 1))
done
if [ "$i" -ge 600 ]; then
    # Diagnose-Hinweis fuer genau diesen Bug - falls jemand nach einem
    # fehlgeschlagenen Start /tmp/frontend.log ansieht, soll sofort
    # erkennbar sein, dass MiSTer laenger als 120s zum Booten brauchte,
    # statt raetseln zu muessen.
    echo "WARNUNG: MiSTer-Menue nach 120s immer noch nicht bereit (letzter CORENAME-Wert: '$CORE') - starte trotzdem." \
        >> /tmp/frontend.log
fi

# Kurzer Puffer, damit MiSTer's Hauptprogramm den Menue-Wechsel wirklich
# abgeschlossen hat (vorher pauschal 2s - 1s reicht in der Praxis und
# spart eine Sekunde beim Start).
sleep 1

exec /usr/bin/python3 /media/fat/frontend/frontend.py \
    >> /tmp/frontend.log 2>&1
