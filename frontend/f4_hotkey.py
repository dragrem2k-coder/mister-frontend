#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""F4-Schnellstart fuer das Frontend - kleiner Hintergrundwaechter.

NEUES FEATURE (Nutzerwunsch: "koennen wir das Script Frontend_Start.sh,
wenn einer kein Autostart eingerichtet hat, irgendwie auf F4 im OSD
einbinden? So dass man nur F4 druecken muss und es startet?").

WARUM UEBERHAUPT EIN EIGENER PROZESS
------------------------------------
Nachgesehen statt geraten: MiSTers eigene Menue-Verarbeitung
(menu.cpp) wertet in ihrem Tasten-Zweig F12, F1, F11, F10, F9, F7,
ESC, BACK, BACKSPACE und ENTER aus - F4 kommt dort NICHT vor, die
Taste ist also tatsaechlich frei. Eine Moeglichkeit, eine Taste per
MiSTer.ini auf ein Script zu legen, gibt es aber nicht (die komplette
Optionsliste in cfg.cpp wurde danach durchsucht: kein Eintrag fuer
Taste/Button/Script/Shortcut). Ohne Aenderung an MiSTer selbst bleibt
deshalb nur ein eigener kleiner Waechter, der die Eingabegeraete
mitliest - genau das ist diese Datei.

WAS SIE BEWUSST NICHT TUT
-------------------------
* Sie greift die Eingabegeraete NICHT exklusiv ab (kein EVIOCGRAB) -
  sie liest nur mit. MiSTers Menue bekommt jeden Tastendruck also
  weiterhin unveraendert; F4 selbst wertet es ohnehin nicht aus.
* Sie reagiert NUR, solange MiSTers Menue-Core aktiv ist
  (/tmp/CORENAME == "MENU"). Waehrend eines laufenden Spiels passiert
  auf F4 nichts - sonst wuerde ein versehentlicher Tastendruck mitten
  im Spiel das Frontend starten.
* Sie startet nichts, wenn das Frontend bereits laeuft (Sperrdatei
  /tmp/frontend.lock mit lebendem Prozess) - dann waere ein zweiter
  Start ohnehin sinnlos, und Frontend_Start.sh lehnt ihn selbst ab.
* Sie ist standardmaessig AUS. Ohne die Schalterdatei (siehe FLAG_FILE)
  beendet sie sich sofort wieder. Eingeschaltet wird ueber den
  Menuepunkt unter System -> Optionen.

Aufruf normalerweise ueber f4_hotkey.sh aus user-startup.sh.
Direkter Aufruf zum Ausprobieren:  python3 f4_hotkey.py --debug
"""
import fcntl
import glob
import os
import select
import struct
import subprocess
import sys
import time

FRONTEND_DIR = "/media/fat/frontend"
FLAG_FILE = os.path.join(FRONTEND_DIR, "f4_hotkey")
LOCK_FILE = "/tmp/f4_hotkey.lock"
FRONTEND_LOCK = "/tmp/frontend.lock"
CORENAME = "/tmp/CORENAME"
START_SCRIPT = "/media/fat/Scripts/Frontend_Start.sh"
LOGFILE = "/tmp/frontend.log"

# evdev-Grundlagen - bewusst hier wiederholt statt aus fe/input.py
# importiert: dieser Waechter laeuft beim Booten, moeglicherweise noch
# bevor irgendetwas anderes bereit ist. Ein Importfehler im grossen
# Frontend-Paket darf ihn nicht mitreissen, und er soll ohne dieses
# Paket lauffaehig bleiben.
EVENT_FMT = "llHHi"
EVENT_SIZE = struct.calcsize(EVENT_FMT)
EV_KEY = 1
KEY_F4 = 62
# Wert 1 = gedrueckt, 2 = Wiederholung (halten), 0 = losgelassen.
# Nur der echte Druck zaehlt - sonst wuerde Halten eine Salve ausloesen.
WERT_GEDRUECKT = 1

DEBUG = "--debug" in sys.argv
USER_STARTUP = "/media/fat/linux/user-startup.sh"


def log(text):
    zeile = "[f4_hotkey] %s\n" % text
    if DEBUG:
        sys.stdout.write(zeile)
        sys.stdout.flush()
    try:
        with open(LOGFILE, "a") as f:
            f.write(zeile)
    except OSError:
        pass


def eingeschaltet():
    return os.path.exists(FLAG_FILE)


def menue_aktiv():
    """True, wenn MiSTers eigener Menue-Core laeuft.

    Genauso robust gelesen wie in frontend_boot.sh und current_core()
    im Frontend selbst: manche Firmware haengt ein Leerzeichen oder ein
    CR an, ein blosser Vergleich auf "MENU" trifft dann nie."""
    try:
        with open(CORENAME, "rb") as f:
            roh = f.read(64)
    except OSError:
        return False
    return roh.decode("latin-1").strip("\x00\r\n\t ").upper() == "MENU"


def frontend_laeuft():
    try:
        with open(FRONTEND_LOCK) as f:
            pid = int(f.read().strip() or 0)
    except (OSError, ValueError):
        return False
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)          # Signal 0: nur pruefen, nicht senden
    except OSError:
        return False             # verwaiste Sperrdatei
    return True


class Geraete(object):
    """Offene Lese-Handles auf alle /dev/input/event*.

    Wird regelmaessig aufgefrischt: eine Tastatur, die erst nach dem
    Booten eingesteckt wird, soll genauso funktionieren."""

    def __init__(self):
        self.offen = {}          # Pfad -> Dateiobjekt
        self.letzte_pruefung = 0.0

    def aktualisieren(self, jetzt):
        if jetzt - self.letzte_pruefung < 3.0:
            return
        self.letzte_pruefung = jetzt
        vorhanden = set(glob.glob("/dev/input/event*"))
        for pfad in sorted(vorhanden - set(self.offen)):
            try:
                f = open(pfad, "rb", buffering=0)
                # Nicht blockierend: read() darf niemals haengen
                # bleiben, sonst reagiert der Waechter auf nichts mehr.
                flags = fcntl.fcntl(f, fcntl.F_GETFL)
                fcntl.fcntl(f, fcntl.F_SETFL, flags | os.O_NONBLOCK)
            except OSError:
                continue         # z.B. fehlende Rechte - einfach ueberspringen
            self.offen[pfad] = f
            log("Geraet dazu: %s" % pfad)
        for pfad in list(self.offen):
            if pfad not in vorhanden:
                self.schliessen(pfad)

    def schliessen(self, pfad):
        f = self.offen.pop(pfad, None)
        if f is not None:
            try:
                f.close()
            except OSError:
                pass
            log("Geraet weg: %s" % pfad)

    def f4_gedrueckt(self, timeout):
        """Wartet bis zu timeout Sekunden auf Eingaben. True, sobald
        auf irgendeinem Geraet F4 gedrueckt wurde."""
        if not self.offen:
            time.sleep(timeout)
            return False
        try:
            bereit, _, _ = select.select(list(self.offen.values()), [], [],
                                         timeout)
        except (OSError, ValueError):
            return False
        treffer = False
        for f in bereit:
            try:
                roh = f.read(EVENT_SIZE * 32)
            except (OSError, ValueError):
                # Geraet ist verschwunden (Kabel gezogen) - beim
                # naechsten Auffrischen faellt es sauber heraus.
                for pfad, g in list(self.offen.items()):
                    if g is f:
                        self.schliessen(pfad)
                continue
            if not roh:
                continue
            for i in range(0, len(roh) - EVENT_SIZE + 1, EVENT_SIZE):
                _s, _us, etype, code, wert = struct.unpack(
                    EVENT_FMT, roh[i:i + EVENT_SIZE])
                if etype == EV_KEY and wert == WERT_GEDRUECKT:
                    if DEBUG:
                        log("Taste gedrueckt: Code %d%s"
                            % (code, "  <-- das ist F4" if code == KEY_F4 else ""))
                    if code == KEY_F4:
                        treffer = True
        return treffer


def frontend_starten():
    if not os.path.exists(START_SCRIPT):
        log("Startscript fehlt: %s" % START_SCRIPT)
        return
    log("F4 im Menue erkannt - starte das Frontend.")
    try:
        # Vom Waechter ABKOPPELN (eigene Sitzung): der Waechter laeuft
        # weiter und soll den Start weder blockieren noch mit in den
        # Abgrund reissen, falls er selbst spaeter beendet wird.
        subprocess.Popen(["/bin/bash", START_SCRIPT],
                         stdin=subprocess.DEVNULL,
                         stdout=open(LOGFILE, "a"),
                         stderr=subprocess.STDOUT,
                         start_new_session=True)
    except OSError as e:
        log("Start fehlgeschlagen: %s" % e)


def sperre_inhaber():
    """PID des Waechters, der die Sperre gerade haelt - oder None."""
    try:
        with open(LOCK_FILE) as f:
            pid = int(f.read().strip() or 0)
    except (OSError, ValueError):
        return None
    if pid <= 0:
        return None
    try:
        os.kill(pid, 0)
    except OSError:
        return None
    return pid


def einmal_sicherstellen():
    """Verhindert, dass zwei Waechter gleichzeitig laufen (z.B. weil
    der Eintrag in user-startup.sh versehentlich doppelt steht).

    BUGFIX (beim Nachgehen der Meldung "laeuft bereits - dieser Start
    wird beendet" gefunden): die Datei wurde mit "w" geoeffnet, und das
    LEERT sie sofort - noch BEVOR ueberhaupt klar ist, ob die Sperre zu
    bekommen ist. Ein zweiter Startversuch loeschte damit die PID des
    tatsaechlich laufenden Waechters aus der Sperrdatei. Der Waechter
    lief zwar weiter (die Sperre selbst haengt am Dateizeiger, nicht am
    Inhalt), aber jede spaetere Frage "laeuft er, und unter welcher
    PID?" - Selbsttest wie Deinstallation - bekam eine leere Datei zu
    sehen und antwortete "nein". Also genau dann irrefuehrend, wenn man
    sich darauf verlassen wollte.

    Jetzt wird ohne Leeren geoeffnet, erst die Sperre geholt und
    ausschliesslich im Erfolgsfall geschrieben."""
    try:
        fd = os.open(LOCK_FILE, os.O_RDWR | os.O_CREAT, 0o644)
        f = os.fdopen(fd, "r+")
    except OSError:
        return None
    try:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (OSError, IOError):
        f.close()
        return None
    f.seek(0)
    f.truncate()
    f.write("%d\n" % os.getpid())
    f.flush()
    return f                     # offen halten, sonst faellt die Sperre


def geraete_info(f):
    """Name des Eingabegeraets und ob es ueberhaupt eine F4-Taste kennt.

    Beides direkt beim Kernel erfragt (dieselben ioctls, die auch evtest
    benutzt) - ohne das laesst sich nicht unterscheiden zwischen "die
    Taste kam nicht an" und "an diesem MiSTer haengt gar keine
    Tastatur". Genau diese Unterscheidung fehlte bei der Ferndiagnose.

    Schlaegt eines der ioctls fehl, wird das ehrlich als "unbekannt"
    gemeldet statt eine Vermutung auszugeben."""
    name = "?"
    try:
        puffer = bytearray(256)
        # EVIOCGNAME(len): _IOR('E', 0x06, len)
        fcntl.ioctl(f, 0x80000000 | (len(puffer) << 16) | (0x45 << 8) | 0x06,
                    puffer)
        name = puffer.split(b"\x00")[0].decode("latin-1") or "?"
    except (OSError, ValueError):
        pass
    kann_f4 = None
    try:
        # EVIOCGBIT(EV_KEY, len): _IOR('E', 0x20 + EV_KEY, len) - liefert
        # eine Bitmaske aller Tastencodes, die dieses Geraet melden kann.
        bits = bytearray((KEY_F4 // 8) + 1)
        fcntl.ioctl(f, 0x80000000 | (len(bits) << 16) | (0x45 << 8)
                    | (0x20 + EV_KEY), bits)
        kann_f4 = bool(bits[KEY_F4 // 8] & (1 << (KEY_F4 % 8)))
    except (OSError, ValueError, IndexError):
        kann_f4 = None
    return name[:34], kann_f4


def selbsttest():
    """Sagt in Klartext, was auf DIESEM Geraet tatsaechlich vorliegt.

    NEU (Nutzer-Rueckmeldung: "F4 funktioniert immer noch nicht"): nach
    zwei Fehlversuchen aus der Ferne wird hier nicht noch einmal
    geraten, sondern gemessen. Aufruf:

        python3 /media/fat/frontend/f4_hotkey.py --debug

    Danach F4 druecken - erscheint keine Zeile "Taste gedrueckt", kommt
    die Taste ueberhaupt nicht bei uns an (dann liegt es NICHT an dieser
    Datei). Erscheinen andere Tasten, aber F4 nie, meldet die Tastatur
    einen anderen Code als 62."""
    print("=== F4-Waechter: Selbsttest ===")
    print("Schalterdatei %s : %s"
          % (FLAG_FILE, "vorhanden (AN)" if eingeschaltet() else "FEHLT (aus)"))
    print("Startscript   %s : %s"
          % (START_SCRIPT, "vorhanden" if os.path.exists(START_SCRIPT) else "FEHLT"))
    try:
        with open(USER_STARTUP, "r", errors="replace") as f:
            zeilen = [z.strip() for z in f]
        treffer = [z for z in zeilen
                   if "f4_hotkey.sh" in z and not z.startswith("#")]
        print("Autostart-Zeile in %s : %s"
              % (USER_STARTUP, treffer[0] if treffer else "FEHLT"))
    except OSError as e:
        print("Autostart-Datei %s NICHT LESBAR: %s" % (USER_STARTUP, e))
    # NEU: die wichtigste Frage ueberhaupt - laeuft der Waechter als
    # Hintergrunddienst? Alles andere kann richtig eingerichtet sein und
    # F4 trotzdem nichts tun, wenn ihn seit dem Einschalten niemand
    # gestartet hat (die Zeile in user-startup.sh wirkt erst beim
    # naechsten Boot). Erkennbar an der Sperrdatei, die er beim Start
    # anlegt und mit flock() haelt.
    laeuft = "nein"
    try:
        with open(LOCK_FILE) as lf:
            lpid = int(lf.read().strip() or 0)
        if lpid > 0:
            try:
                os.kill(lpid, 0)
                laeuft = "ja (PID %d)" % lpid
            except OSError:
                laeuft = "nein (verwaiste Sperrdatei)"
    except (OSError, ValueError):
        pass
    print("Waechter laeuft im Hintergrund    : %s" % laeuft)
    if laeuft.startswith("nein") and eingeschaltet():
        print("   -> Schalter ist AN, aber niemand hat den Waechter gestartet.")
        print("      Beim naechsten Neustart passiert das von selbst.")
        print("      Sofort starten:  /media/fat/frontend/f4_hotkey.sh &")
    print("MiSTer-Menue aktiv (/tmp/CORENAME): %s" % ("ja" if menue_aktiv() else "nein"))
    print("Frontend laeuft gerade            : %s" % ("ja" if frontend_laeuft() else "nein"))
    gefunden = sorted(glob.glob("/dev/input/event*"))
    print("Eingabegeraete gefunden: %d" % len(gefunden))
    lesbar = 0
    mit_f4 = []
    for pfad in gefunden:
        try:
            f = open(pfad, "rb", buffering=0)
        except OSError as e:
            print("   %-20s NICHT lesbar (%s)" % (pfad, e))
            continue
        lesbar += 1
        name, kann_f4 = geraete_info(f)
        print("   %-20s %-34s %s"
              % (pfad, name, "kann F4" if kann_f4 else "kann KEIN F4"))
        if kann_f4:
            mit_f4.append(pfad)
        f.close()
    print("Davon lesbar: %d, davon mit F4-Taste: %d" % (lesbar, len(mit_f4)))
    if not lesbar:
        print("")
        print("KEIN Geraet lesbar - ohne Lesezugriff kann F4 nie ankommen.")
    elif not mit_f4:
        print("")
        print("WICHTIG: KEINES der angeschlossenen Geraete meldet eine")
        print("F4-Taste. Das sind vermutlich nur Gamepads. Dann kann dieser")
        print("Waechter prinzipiell nicht funktionieren - er braucht eine")
        print("echte Tastatur AM MISTER. Eine Tastatur im SSH-Fenster zaehlt")
        print("nicht: die Tastendruecke gehen an den PC, nie an den MiSTer.")
    print("")
    print("Jetzt F4 druecken. Kommt keine Zeile 'Taste gedrueckt', erreicht")
    print("uns die Taste nicht. Abbrechen mit Strg+C.")
    print("")


def main():
    if DEBUG:
        # Im Diagnosemodus bewusst OHNE Schalterdatei lauffaehig - sonst
        # koennte man genau den Fall "Schalter aus" nicht untersuchen.
        selbsttest()
        geraete = Geraete()
        while True:
            geraete.aktualisieren(time.monotonic())
            if geraete.f4_gedrueckt(1.0):
                print(">>> F4 erkannt. Menue aktiv: %s, Frontend laeuft: %s"
                      % (menue_aktiv(), frontend_laeuft()))
                print("    (im Diagnosemodus wird BEWUSST nichts gestartet -")
                print("     sonst laege das Frontend gleich ueber dieser Ausgabe)")
    if not eingeschaltet():
        # Kein Log-Eintrag: der Normalfall (Funktion ist aus), und die
        # Datei soll bei jedem Boot nicht unnoetig wachsen.
        return 0
    sperre = einmal_sicherstellen()
    if sperre is None:
        andere = sperre_inhaber()
        log("laeuft bereits%s - dieser Start wird beendet."
            % ((" (PID %d)" % andere) if andere else ""))
        return 0
    log("gestartet (F4 startet das Frontend, solange MiSTers Menue laeuft).")
    geraete = Geraete()
    while True:
        jetzt = time.monotonic()
        # Schalter zur Laufzeit ausgeschaltet -> sauber beenden, ohne
        # dass ein Neustart noetig waere.
        if not eingeschaltet():
            log("Schalter aus - beende mich.")
            return 0
        geraete.aktualisieren(jetzt)
        if not geraete.f4_gedrueckt(1.0):
            continue
        if not menue_aktiv():
            log("F4 erkannt, aber MiSTers Menue laeuft gerade nicht - ignoriert.")
            continue
        if frontend_laeuft():
            log("F4 erkannt, aber das Frontend laeuft bereits - ignoriert.")
            continue
        frontend_starten()
        # Kurze Sperrzeit: der Start braucht einen Moment, bis die
        # Sperrdatei des Frontends steht. Ohne diese Pause wuerde ein
        # zweiter Tastendruck in der Zwischenzeit einen zweiten Start
        # ausloesen.
        time.sleep(5.0)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:                      # noqa: BLE001
        # Ein Waechter darf den Bootvorgang unter keinen Umstaenden
        # stoeren - jeder unerwartete Fehler wird protokolliert und
        # fuehrt zu einem stillen, sauberen Ende.
        log("unerwarteter Fehler, beende mich: %r" % (e,))
        sys.exit(0)
