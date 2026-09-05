#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NTP-Zeitsynchronisierung beim Start (MiSTers eigene Uhr steht beim
Booten nahe Null) + Zeitzonen-Verschiebung fuer die Anzeige. Ausgelagert
aus frontend.py (Modularisierung, Git-Branch 'modular-refactor').

NTP_SYNC_OK wird von der noch nicht ausgelagerten Frontend-Klasse an
mehreren Stellen direkt gelesen (Uhrzeit-Anzeige, Retry-Logik) -
dieselbe Einfrier-Falle wie bei CURRENT_LANG/C_BG/VOLUME. Wie bei
current_lang()/get_volume() geloest: get_ntp_sync_ok() als Funktion,
die immer den aktuellen Wert liefert (unproblematisch, da nur
gelegentlich fuer die UI abgefragt, keine heisse Stelle).
"""
import os, socket, struct, time, threading, subprocess
from fe.log import LOG

def _has_network():
    """Prueft, ob irgendein Netzwerk-Interface eine Adresse hat - siehe
    ausfuehrlichen Kommentar in fe/scan.py (dort dieselbe Funktion,
    bewusst dupliziert statt importiert - frontend.py braucht die
    Original-Kopie ebenfalls, ein Ruecksfall-Import haette einen
    Zirkelbezug ausgeloest)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return bool(ip) and not ip.startswith("127.")
    except OSError:
        return False


# ----------------------------------------------------------------------------
# NTP-ZEITSYNCHRONISIERUNG BEIM START
#
# MiSTer hat keine batteriegepufferte Echtzeituhr - die Systemuhr startet
# beim Booten nahe Null (siehe v1.70: Log-Zeitstempel begannen bei
# "00:00:11") und wird sonst erst spaet (falls ueberhaupt) per NTP
# korrigiert, oft mitten in der Sitzung als ploetzlicher Sprung. Deshalb
# holt das Frontend die Uhrzeit selbst, EINMALIG und MOEGLICHST FRUEH
# beim Start (noch vor dem ersten Log-Eintrag), per einfacher SNTP-
# Abfrage (RFC 5905, reines socket/struct - keine externe Bibliothek).
NTP_SERVER = "pool.ntp.org"
NTP_EPOCH_OFFSET = 2208988800   # Sekunden zwischen 1.1.1900 (NTP) und 1.1.1970 (Unix)
TIMEZONE_OFFSET_FILE = "/media/fat/frontend/timezone_offset"

def load_timezone_offset():
    """Stunden-Versatz zur UTC-Zeit (z.B. 2.0 fuer UTC+2/deutsche
    Sommerzeit). MiSTer hat keine echte Zeitzonen-Datenbank und keine
    automatische Erkennung - NTP liefert grundsaetzlich nur UTC, ohne
    diesen manuell eingestellten Versatz wuerde die angezeigte Uhrzeit
    je nach Zeitzone des Nutzers falsch sein (Bugfix: genau das wurde
    gemeldet - Anzeige zeigte UTC statt der tatsaechlichen Ortszeit,
    zwei Stunden Differenz durch die deutsche Sommerzeit)."""
    try:
        with open(TIMEZONE_OFFSET_FILE) as f:
            return float(f.read().strip())
    except (OSError, ValueError):
        return 0.0

def save_timezone_offset(hours):
    try:
        os.makedirs(os.path.dirname(TIMEZONE_OFFSET_FILE), exist_ok=True)
        with open(TIMEZONE_OFFSET_FILE, "w") as f:
            f.write(str(hours))
    except OSError:
        pass

TIMEZONE_STEPS = [x * 0.5 for x in range(-24, 29)]   # -12.0 .. +14.0 in 0.5h-Schritten

def cycle_timezone_offset():
    """Naechsten Wert in TIMEZONE_STEPS waehlen (wrap-around). Liefert
    den neuen Versatz."""
    current = load_timezone_offset()
    try:
        idx = min(range(len(TIMEZONE_STEPS)),
                  key=lambda i: abs(TIMEZONE_STEPS[i] - current))
        new_idx = (idx + 1) % len(TIMEZONE_STEPS)
    except ValueError:
        new_idx = 0
    new_offset = TIMEZONE_STEPS[new_idx]
    save_timezone_offset(new_offset)
    return new_offset

def format_timezone_offset(hours):
    """z.B. 'UTC+2', 'UTC-3.5', 'UTC' fuer 0."""
    if hours == 0:
        return "UTC"
    sign = "+" if hours > 0 else "-"
    h = abs(hours)
    if h == int(h):
        return "UTC%s%d" % (sign, int(h))
    return "UTC%s%.1f" % (sign, h)

def _ntp_time(server=NTP_SERVER, timeout=2.0):
    """Fragt die aktuelle Unix-Zeit per SNTP ab. Liefert None bei jedem
    Fehler (kein Internet, Zeitueberschreitung, unplausible Antwort) -
    wird NIE eine Ausnahme nach aussen weiterreichen, damit ein
    Zeitserver-Problem den Start niemals blockieren oder zum Absturz
    fuehren kann."""
    s = None
    try:
        packet = bytearray(48)
        packet[0] = 0x1B   # LI=0, VN=3 (NTPv3), Mode=3 (Client)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(timeout)
        s.sendto(bytes(packet), (server, 123))
        data, _ = s.recvfrom(48)
        if len(data) < 48:
            return None
        secs = struct.unpack("!I", data[40:44])[0]
        frac = struct.unpack("!I", data[44:48])[0]
        unix_time = secs - NTP_EPOCH_OFFSET + frac / 2**32
        # Grobe Plausibilitaetspruefung (nach 2020, vor 2100) - schuetzt
        # vor einer kaputten Antwort, die die Uhr auf einen abwegigen
        # Wert setzen wuerde.
        if unix_time < 1577836800 or unix_time > 4102444800:
            return None
        return unix_time
    except (OSError, struct.error, socket.gaierror):
        return None
    finally:
        if s is not None:
            try:
                s.close()
            except OSError:
                pass

NTP_SYNC_OK = False   # von sync_system_clock_from_ntp() bei jedem Aufruf
                      # aktuell gehalten - ermoeglicht spaeteren Code (z.B.
                      # dem RA-Neuversuch) zu pruefen, ob die Systemuhr
                      # zum jetzigen Zeitpunkt als verlaesslich gilt.

def _apply_ntp_result(unix_time):
    """Setzt die Systemuhr anhand eines per NTP ermittelten UTC-
    Zeitstempels (oder None bei Fehlschlag) und haelt NTP_SYNC_OK
    aktuell. Ausgelagert, damit sowohl der blockierende als auch der
    nicht-blockierende Modus von sync_system_clock_from_ntp() dieselbe
    Logik nutzen (siehe dort).

    NACHGEBESSERT (Nutzer-Rueckmeldung: Uhrzeit trotz korrekt
    eingestelltem UTC+2-Versatz falsch, aber im Log stand dazu
    RUEBERHAUPT NICHTS - weder Erfolg noch Fehlschlag): die komplette
    NTP-Kette war bisher vollstaendig stumm, dadurch nicht
    diagnostizierbar, ob ueberhaupt versucht wurde zu synchronisieren."""
    global NTP_SYNC_OK
    if unix_time is None:
        NTP_SYNC_OK = False
        LOG("NTP-Sync fehlgeschlagen (kein Zeitserver erreichbar/Zeitueberschreitung)")
        return False
    try:
        # BUGFIX (Nutzer-Rueckmeldung: Uhr zeigte 2 Stunden zu wenig,
        # deutsche Sommerzeit): NTP liefert grundsaetzlich UTC. Die alte
        # Fassung nutzte time.localtime(), das sich auf die System-
        # Zeitzone verlaesst - MiSTer hat aber vermutlich gar keine
        # echte Zeitzone konfiguriert (Standard UTC), wodurch die
        # angezeigte Uhrzeit der reinen UTC-Zeit entsprach statt der
        # tatsaechlichen Ortszeit. Jetzt wird der manuell eingestellte
        # Versatz (siehe load_timezone_offset()) selbst angewendet und
        # mit time.gmtime() formatiert - unabhaengig davon, was die
        # Systemzeitzone gerade zu sein glaubt.
        offset_h = load_timezone_offset()
        local_unix_time = unix_time + offset_h * 3600
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(local_unix_time))
        subprocess.run(["date", "-s", ts], capture_output=True, timeout=2.0)
        NTP_SYNC_OK = True
        LOG("NTP-Sync erfolgreich: Systemuhr auf %s gesetzt (UTC%+d)" % (ts, offset_h))
        # NEU (Build 84): dem Miniaturen-Zwischenspeicher Bescheid sagen.
        # Er benutzt die Aenderungszeit der Dateien als "zuletzt
        # benutzt"-Marke - und genau JETZT ist die Uhr gerade um Stunden
        # gesprungen. Ohne diesen Anruf haetten alle beim Start
        # gelesenen Eintraege eine Marke aus der Zeit VOR dem Sprung und
        # waeren dadurch die ersten Verdraengungsopfer. Die
        # ausfuehrliche Herleitung steht bei uhr_ist_gestellt() in
        # fe/art.py. Bewusst spaet importiert: fe/art.py importiert
        # dieses Modul nicht, ein Import auf Modulebene waere trotzdem
        # eine unnoetige Kopplung fuer eine einzige Zeile.
        try:
            from fe.art import uhr_ist_gestellt
            uhr_ist_gestellt()
        except Exception:                            # noqa: BLE001
            pass   # Uhrstellen darf an dieser Nebensache nie scheitern
        return True
    except (OSError, subprocess.SubprocessError) as e:
        NTP_SYNC_OK = False
        LOG("NTP-Sync: Systemuhr setzen fehlgeschlagen: %s" % e)
        return False

def sync_system_clock_from_ntp(timeout=2.5, blocking=True):
    """Setzt die Systemuhr per NTP, FALLS ein lokales Netzwerk vorhanden
    ist - in einem separaten Thread mit hartem Zeitlimit, damit eine
    haengende DNS-Aufloesung (die von socket.settimeout() NICHT
    zuverlaessig erfasst wird) den Start niemals um mehr als `timeout`
    Sekunden verzoegert. Der Thread laeuft im schlimmsten Fall im
    Hintergrund weiter, blockiert dabei aber nichts mehr (Daemon-Thread) -
    sein Ergebnis wird dann einfach verworfen. Ohne lokales Netzwerk wird
    gar nicht erst versucht (spart die Wartezeit komplett).

    blocking=False (Nutzerwunsch: schnellerer Programmstart): startet
    die Synchronisierung nur im Hintergrund und kehrt SOFORT zurueck
    (Rueckgabewert dann None - das Ergebnis steht ja noch nicht fest),
    ohne auf das Ergebnis zu warten. Der Hintergrund-Thread setzt die
    Uhr trotzdem zuverlaessig, sobald er fertig ist - der bestehende
    RA-Neuversuch-Mechanismus (Frontend._maybe_retry_ra()) faengt den
    Fall "Uhr war beim allerersten RA-Abruf noch nicht fertig" schon
    ab, dafuer aendert sich durch blocking=False nichts.

    Haelt NTP_SYNC_OK bei jedem Aufruf aktuell (auch bei spaeteren
    Neuversuchen) - andere Code-Stellen koennen darueber pruefen, ob
    die Systemuhr aktuell als verlaesslich gilt, ohne selbst NTP
    abfragen zu muessen."""
    if not _has_network():
        LOG("NTP-Sync uebersprungen: kein Netzwerk erkannt")
        return False
    result = {"t": None}
    def worker():
        result["t"] = _ntp_time(timeout=timeout)
        if not blocking:
            # Niemand wartet auf dieses Ergebnis - der Hintergrund-
            # Thread muss die Uhr deshalb selbst setzen.
            _apply_ntp_result(result["t"])
    th = threading.Thread(target=worker, daemon=True)
    th.start()
    if not blocking:
        return None   # Ergebnis noch nicht bekannt, laeuft im Hintergrund weiter
    th.join(timeout=timeout + 0.5)
    return _apply_ntp_result(result["t"])

def get_ntp_sync_ok():
    """Liefert IMMER den aktuellen Stand - siehe Modul-Kommentar oben,
    warum ein direktes 'from fe.timekeeping import NTP_SYNC_OK' an
    anderer Stelle gefaehrlich waere (eingefrorene Kopie)."""
    return NTP_SYNC_OK
