#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Spielzeit-Tracking, Tagebuch, Jahresrueckblick, Meilensteine.
Ausgelagert aus frontend.py (Modularisierung, Git-Branch
'modular-refactor'). RetroAchievements-Integration bewusst NICHT mit
ausgelagert (eigener, spaeterer Schritt - deutlich groesser und
eigenstaendig genug fuer ein eigenes Modul).

PLAYTIME_FILE hierher verschoben (war vorher an einer frontend.py-
Stelle definiert, die ausschliesslich von diesem Bereich gebraucht
wurde - reine Verschiebung).
"""
import os, json, time, calendar
from fe.log import LOG
from fe.translations import current_lang, t
from fe.game_state import _load_completed_raw

PLAYTIME_FILE = "/media/fat/frontend/playtime.json"

def load_playtime():
    """Laedt die Spielzeit-/Start-Statistik. JEDER Eintrag wird auf das
    Format {"seconds": X, "launches": N, "syskey": S} normalisiert -
    frueher (v1.79/v1.80) fehlte "syskey" komplett bzw. war es nur
    eine reine Zahl ohne Start-Zaehler. Diese alten Eintraege werden
    beim Laden transparent umgewandelt (launches=0/syskey=None, da
    dafuer keine historischen Daten existieren), damit ein Update
    nicht die bisherige Spielzeit verwirft."""
    try:
        with open(PLAYTIME_FILE) as f:
            raw = json.load(f)
    except (OSError, ValueError):
        return {}
    data = {}
    for label, val in raw.items():
        if isinstance(val, dict):
            data[label] = {"seconds": val.get("seconds", 0),
                          "launches": val.get("launches", 0),
                          "syskey": val.get("syskey")}
        else:
            data[label] = {"seconds": val, "launches": 0, "syskey": None}
    return data

def record_playtime(label, seconds, syskey=None):
    """Addiert die gespielte Zeit (in Sekunden) UND zaehlt einen
    weiteren Start fuer dieses Spiel hoch (identifiziert ueber den
    Namen - gleiche Konvention wie record_recent()/Favoriten). Wird
    ganz am Ende von run_core() aufgerufen, NUR mit der Zeit vom
    bestaetigten Core-Start bis zur Rueckkehr ins Menue - Ladezeiten
    und fehlgeschlagene Starts zaehlen bewusst nicht mit (und werden
    dementsprechend auch nicht als Start gezaehlt - run_core() ruft
    diese Funktion nur bei einem TATSAECHLICH bestaetigten Start auf).
    syskey (optional, seit v1.89): fuers "Entdecker"-Achievement
    (verschiedene Systeme ausprobiert) - wird bei jedem Aufruf
    aktualisiert (falls mitgegeben), falls sich der Systemschluessel
    fuer denselben Namen mal aendern sollte."""
    if not label or seconds <= 0:
        return
    data = load_playtime()
    entry = data.get(label, {"seconds": 0, "launches": 0, "syskey": None})
    entry["seconds"] += seconds
    entry["launches"] += 1
    if syskey:
        entry["syskey"] = syskey
    data[label] = entry
    try:
        os.makedirs(os.path.dirname(PLAYTIME_FILE), exist_ok=True)
        with open(PLAYTIME_FILE, "w") as f:
            json.dump(data, f)
    except OSError:
        pass

# ----------------------------------------------------------------------------
# JAHRES-BUENDELUNG DER SPIELZEIT (Fundament fuer einen spaeteren
# echten Jahresrueckblick, Nutzerwunsch: "digitales Retro-Wohnzimmer").
# Unser bisheriges Tracking (record_playtime() oben) kennt nur
# KUMULIERTE Gesamtwerte pro Spiel, keine Kalenderjahr-Zuordnung - ein
# "Jahresrueckblick 2026" waere damit technisch gar kein echter
# Jahresrueckblick, sondern ein "seit Aufzeichnungsbeginn"-Rueckblick.
#
# Bewusst als KOMPLETT EIGENSTAENDIGE, separate Datei/Funktionen gebaut
# - aendert NICHTS an record_playtime()/load_playtime() selbst, kein
# Risiko fuer bestehende Funktionen, die auf die kumulierten
# Gesamtwerte angewiesen sind (Trophaeenraum, Top-10-Listen, eigene
# Erfolge usw. bleiben komplett unberuehrt). Wird IMMER ZUSAETZLICH zu
# record_playtime() aufgerufen, nie stattdessen.
PLAYTIME_YEARLY_FILE = "/media/fat/frontend/playtime_yearly.json"
FIRST_PLAYED_FILE = "/media/fat/frontend/first_played.json"

def _current_year():
    """Aktuelles Jahr als String - eigene kleine Funktion (statt
    ueberall einzeln time.localtime() aufzurufen), damit Tests den
    Jahreswechsel leicht simulieren koennen (siehe Tests: einfach
    ersetzen statt die Systemzeit zu verstellen)."""
    return str(time.localtime().tm_year)

def load_playtime_yearly():
    """Laedt die nach Kalenderjahr gebuendelte Spielzeit-Statistik.
    Struktur: {jahr_als_string: {"seconds": X, "launches": N,
    "games": {name: sekunden}, "systems": {syskey: sekunden}}}."""
    try:
        with open(PLAYTIME_YEARLY_FILE) as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}

def _load_first_played():
    """Jahr des allerersten Starts pro Spiel (als String) - fuer eine
    spaetere 'dieses Jahr entdeckt'-Sammlung. Eigene, winzige Datei
    statt Teil von playtime_yearly.json, damit ein einzelner
    fehlerhafter Schreibvorgang nicht die Jahres-Hauptstatistik
    gefaehrdet."""
    try:
        with open(FIRST_PLAYED_FILE) as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}

def _record_first_played(label, date_str):
    """Merkt sich das Datum des allerersten Starts eines Spiels - wird
    NUR beim allerersten Mal fuer dieses Spiel gesetzt, ein spaeterer
    Aufruf fuer dasselbe Spiel aendert nichts mehr (das reine
    Vorhandensein des Eintrags zaehlt als 'schon gesehen').

    date_str: seit dem "Auf diesen Tag vor X Jahren"-Feature das VOLLE
    Datum ("2026-03-15") statt nur des Jahres - siehe Aufrufer
    record_yearly_playtime()."""
    data = _load_first_played()
    if label in data:
        return
    data[label] = date_str
    try:
        os.makedirs(os.path.dirname(FIRST_PLAYED_FILE), exist_ok=True)
        with open(FIRST_PLAYED_FILE, "w") as f:
            json.dump(data, f)
    except OSError:
        pass

def find_on_this_day_hint():
    """Nutzerwunsch ('Auf diesen Tag vor X Jahren'): sucht in
    first_played.json ein Spiel, dessen allererster Start-TAG (Monat+
    Tag) auf HEUTE faellt, aber aus einem VERGANGENEN Jahr stammt.
    Liefert (spielname, jahre_her) oder None, wenn nichts passt (der
    haeufigste Fall - an den allermeisten Tagen wird hier nichts
    gefunden, das ist normal und kein Fehler).

    Rein lokale Dateiabfrage, KEIN Netzwerkzugriff - kann deshalb
    synchron und ohne Hintergrund-Thread aufgerufen werden, anders als
    z.B. der Update-Check.

    Alte Eintraege, die noch aus der Zeit VOR diesem Feature stammen
    und nur eine reine Jahreszahl enthalten (4 Zeichen, kein '-'),
    werden sauber uebersprungen - ohne Tag/Monat gibt es dafuer schlicht
    keine sinnvolle Antwort, kein Rateversuch."""
    first_played = _load_first_played()
    if not first_played:
        return None
    today = time.localtime()
    today_md = time.strftime("%m-%d", today)
    this_year = today.tm_year
    matches = []
    for label, date_str in first_played.items():
        if not isinstance(date_str, str) or len(date_str) != 10:
            continue   # kein volles YYYY-MM-DD (z.B. alte reine Jahreszahl)
        parts = date_str.split("-")
        if len(parts) != 3:
            continue
        y, m, d = parts
        try:
            y_int = int(y)
        except ValueError:
            continue
        if m + "-" + d == today_md and y_int < this_year:
            matches.append((label, this_year - y_int))
    if not matches:
        return None
    matches.sort(key=lambda mtch: -mtch[1])   # am laengsten zurueckliegend zuerst
    return matches[0]

def record_yearly_playtime(label, seconds, syskey=None):
    """Wie record_playtime(), aber zusaetzlich nach Kalenderjahr
    gebuendelt - siehe Modul-Kommentar oben fuer die Begruendung.
    Aktualisiert nebenbei _record_first_played().

    NEU (Nutzerwunsch: "Auf diesen Tag vor X Jahren"-Hinweis): uebergibt
    jetzt das VOLLE heutige Datum statt nur des Jahres - rueckwaerts-
    kompatibel, siehe _record_first_played()/find_on_this_day_hint()."""
    if not label or seconds <= 0:
        return
    year = _current_year()
    data = load_playtime_yearly()
    entry = data.get(year, {"seconds": 0, "launches": 0, "games": {}, "systems": {}})
    entry["seconds"] = entry.get("seconds", 0) + seconds
    entry["launches"] = entry.get("launches", 0) + 1
    games = entry.setdefault("games", {})
    games[label] = games.get(label, 0) + seconds
    if syskey:
        systems = entry.setdefault("systems", {})
        systems[syskey] = systems.get(syskey, 0) + seconds
    data[year] = entry
    try:
        os.makedirs(os.path.dirname(PLAYTIME_YEARLY_FILE), exist_ok=True)
        with open(PLAYTIME_YEARLY_FILE, "w") as f:
            json.dump(data, f)
    except OSError:
        pass
    _record_first_played(label, time.strftime("%Y-%m-%d", time.localtime()))

def compute_year_review_stats(year=None):
    """Berechnet die Kennzahlen fuer den Jahresrueckblick (Nutzerwunsch:
    "digitales Retro-Wohnzimmer") - baut auf load_playtime_yearly()/
    _load_first_played() auf (siehe v4.1-Fundament oben). year=None
    verwendet das aktuelle Kalenderjahr. Liefert None, wenn fuer das
    gewaehlte Jahr noch gar keine Daten vorliegen (z.B. frisch
    installiert oder der Jahreswechsel ist gerade erst passiert) -
    der Aufrufer zeigt dann eine freundliche "noch nichts hier"-
    Meldung statt leerer/falscher Werte."""
    year = year or _current_year()
    yearly = load_playtime_yearly()
    entry = yearly.get(year)
    if not entry or entry.get("seconds", 0) <= 0:
        return None

    games = entry.get("games", {})
    systems = entry.get("systems", {})
    top_game = max(games, key=games.get) if games else None
    favorite_system = max(systems, key=systems.get) if systems else None

    first_played = _load_first_played()
    discovered_this_year = sum(1 for g in games if first_played.get(g) == year)
    # BUGFIX/Kompatibilitaet: first_played.json speichert seit dem
    # "Auf diesen Tag"-Feature das VOLLE Datum ("2026-03-15") statt nur
    # des Jahres ("2026") - der Vergleich braucht deshalb jetzt die
    # ersten 4 Zeichen. Funktioniert unveraendert fuer alte, noch aus
    # reinen Jahreszahlen bestehende Eintraege (ein 4-Zeichen-String
    # liefert bei [:4] sich selbst zurueck) - keine Migration noetig.
    discovered_this_year = sum(1 for g in games if first_played.get(g, "")[:4] == year)

    return {
        "year": year,
        "total_seconds": entry.get("seconds", 0),
        "total_launches": entry.get("launches", 0),
        "distinct_games": len(games),
        "distinct_systems": len(systems),
        "top_game": top_game,
        "top_game_seconds": games.get(top_game, 0) if top_game else 0,
        "favorite_system": favorite_system,
        "discovered_this_year": discovered_this_year,
    }

# ----------------------------------------------------------------------------
# SPIELTAGEBUCH (Nutzerwunsch: "digitales Retro-Wohnzimmer" - kleine
# Version zunaechst, "schauen wie es ankommt", volle dauerhafte Version
# mit Archivierung bewusst zurueckgestellt). Rollierendes Protokoll der
# letzten DIARY_RETENTION_DAYS Tage - raeumt sich bei jedem Schreib-
# vorgang automatisch selbst auf, waechst dadurch NIE unbegrenzt (im
# Gegensatz zu playtime_yearly.json/first_played.json, die bewusst
# dauerhaft wachsen duerfen, weil sie nur wenige Bytes pro Spiel/Jahr
# kosten - ein taegliches Sitzungsprotokoll waere das nicht).
#
# Komplett EIGENSTAENDIG - aendert nichts an record_playtime()/
# record_yearly_playtime(), wird IMMER zusaetzlich zu beiden
# aufgerufen, nie stattdessen.
DIARY_FILE = "/media/fat/frontend/diary.json"
DIARY_RETENTION_DAYS = 30

def _current_date_str():
    """Heutiges Datum als 'YYYY-MM-DD' - eigene kleine Funktion (wie
    _current_year()), damit Tests einen Tageswechsel leicht simulieren
    koennen, statt die Systemzeit zu verstellen."""
    return time.strftime("%Y-%m-%d", time.localtime())

def load_diary():
    """Laedt das Spieltagebuch. Struktur: {datum_str: [{"name":...,
    "syskey":..., "seconds":...}, ...]} - ein Eintrag pro tatsaechlich
    beendeter Spielsitzung, mehrere Sitzungen desselben Spiels am
    selben Tag bleiben als SEPARATE Eintraege erhalten (anders als bei
    playtime_yearly.json, wo sie aufaddiert werden) - im Tagebuch soll
    ja der zeitliche Ablauf sichtbar bleiben, nicht nur die Summe."""
    try:
        with open(DIARY_FILE) as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}

def _prune_diary(data):
    """Entfernt Tage, die aelter als DIARY_RETENTION_DAYS sind - haelt
    die Datei dauerhaft klein. Vergleicht ueber epoch-Sekunden statt
    reinem String-Vergleich, damit Monats-/Jahresgrenzen (z.B. Ende
    Januar -> Anfang Februar) korrekt behandelt werden. Ungueltige
    Datumsschluessel (z.B. durch Handbearbeitung entstanden) werden
    still verworfen statt einen Absturz auszuloesen."""
    cutoff = time.time() - DIARY_RETENTION_DAYS * 86400
    kept = {}
    for date_str, entries in data.items():
        try:
            day_epoch = time.mktime(time.strptime(date_str, "%Y-%m-%d"))
        except ValueError:
            continue
        if day_epoch >= cutoff:
            kept[date_str] = entries
    return kept

def record_diary_entry(label, seconds, syskey=None):
    """Traegt eine beendete Spielsitzung ins Tagebuch ein - IMMER
    zusaetzlich zu record_playtime()/record_yearly_playtime()
    aufgerufen (gleicher Aufrufpunkt in run_core()), komplett
    eigenstaendig. Raeumt bei jedem Aufruf automatisch alte Eintraege
    auf (siehe _prune_diary())."""
    if not label or seconds <= 0:
        return
    date_str = _current_date_str()
    data = load_diary()
    data = _prune_diary(data)
    day_entries = data.setdefault(date_str, [])
    day_entries.append({"name": label, "syskey": syskey, "seconds": seconds})
    try:
        os.makedirs(os.path.dirname(DIARY_FILE), exist_ok=True)
        with open(DIARY_FILE, "w") as f:
            json.dump(data, f)
    except OSError:
        pass

# Eigene, sprachabhaengige Monatsnamen statt strftime("%B") - das
# haengt von der SYSTEM-Locale ab (typischerweise Englisch auf einem
# frischen MiSTer), nicht von unserem eigenen CURRENT_LANG-Umschalter.
MONTH_NAMES_DE = ["Januar", "Februar", "Maerz", "April", "Mai", "Juni",
                  "Juli", "August", "September", "Oktober", "November",
                  "Dezember"]
MONTH_NAMES_EN = ["January", "February", "March", "April", "May", "June",
                  "July", "August", "September", "October", "November",
                  "December"]

def _format_diary_date(date_str):
    """Formatiert ein 'YYYY-MM-DD'-Datum fuer die Anzeige im Tagebuch -
    "Heute"/"Gestern" fuer die letzten beiden Tage, sonst "Tag.
    Monatsname" (eigene, sprachabhaengige Monatsnamen, siehe oben)."""
    try:
        parsed = time.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return date_str
    today = _current_date_str()
    yesterday = time.strftime("%Y-%m-%d", time.localtime(time.time() - 86400))
    if date_str == today:
        return t("diary_today")
    if date_str == yesterday:
        return t("diary_yesterday")
    names = MONTH_NAMES_DE if current_lang() == "de" else MONTH_NAMES_EN
    return "%d. %s" % (parsed.tm_mday, names[parsed.tm_mon - 1])

# ----------------------------------------------------------------------------
# EIGENES, LOKALES ACHIEVEMENT-SYSTEM
#
# Komplett unabhaengig von RetroAchievements - basiert nur auf unseren
# eigenen, laengst vorhandenen Daten (Spielzeit-Tracker, Start-Zaehler,
# Durchgespielt-Markierung). Schwellenwerte werden bei jedem Aufruf
# LIVE aus den aktuellen Daten berechnet (kein separater "erreicht am
# ..."-Zustand, der aus dem Ruder laufen koennte) - simpler und
# robuster als ein eigenes Fortschritts-Tracking zu pflegen.
MILESTONE_DEFS = [
    ("playtime_seconds", 3600,   "milestone_playtime_1h"),
    ("playtime_seconds", 36000,  "milestone_playtime_10h"),
    ("playtime_seconds", 180000, "milestone_playtime_50h"),
    ("playtime_seconds", 360000, "milestone_playtime_100h"),
    ("launches", 10,  "milestone_launches_10"),
    ("launches", 50,  "milestone_launches_50"),
    ("launches", 100, "milestone_launches_100"),
    ("launches", 500, "milestone_launches_500"),
    ("systems", 3,  "milestone_systems_3"),
    ("systems", 5,  "milestone_systems_5"),
    ("systems", 10, "milestone_systems_10"),
    ("completed", 1,  "milestone_completed_1"),
    ("completed", 5,  "milestone_completed_5"),
    ("completed", 10, "milestone_completed_10"),
    ("completed", 25, "milestone_completed_25"),
]

def compute_milestone_progress():
    """Aktuelle Werte fuer alle Meilenstein-Kategorien, aus den
    bereits vorhandenen Daten berechnet (kein zusaetzlicher Scan)."""
    playtime = load_playtime()
    total_seconds = sum(e.get("seconds", 0) for e in playtime.values())
    total_launches = sum(e.get("launches", 0) for e in playtime.values())
    distinct_systems = len(set(
        e["syskey"] for e in playtime.values() if e.get("syskey")))
    completed_count = len(_load_completed_raw())
    return {
        "playtime_seconds": total_seconds,
        "launches": total_launches,
        "systems": distinct_systems,
        "completed": completed_count,
    }

def _format_seconds_short(seconds):
    """Wie format_playtime(), liefert aber IMMER einen Text (auch unter
    einer Minute) - fuer die Meilenstein-Anzeige, wo bei jedem
    Fortschrittswert etwas Lesbares stehen soll, nicht nur ab einer
    bestimmten Groessenordnung.

    BUGFIX (Nutzer-Rueckmeldung anhand eines CRT-Fotos: Fortschritts-
    anzeige zeigte z.B. "14min/100h" - Aktuell- und Zielwert in
    UNTERSCHIEDLICHEN Einheiten nebeneinander, schwer auf einen Blick
    vergleichbar): zeigt jetzt IMMER konsequent "Stunden dann Minuten"
    (auch "0h"), damit beide Seiten des Bruchs im selben Format stehen -
    z.B. "0h 14min/100h 0min" statt des vorherigen Mix aus "14min" und
    "100h"."""
    seconds = max(0, int(seconds))
    mins = seconds // 60
    h, m = divmod(mins, 60)
    return "%dh %dmin" % (h, m)

def get_milestones():
    """Liste aller Meilensteine als (label_key, erreicht, aktueller_wert,
    schwellenwert, kind)-Tupel, in der definierten Reihenfolge. kind
    wird fuer die richtige Anzeige-Formatierung gebraucht (Sekunden
    lesbar als "3min"/"2h 15min" statt roher Zahl, siehe
    draw_milestones_screen())."""
    progress = compute_milestone_progress()
    out = []
    for kind, threshold, label_key in MILESTONE_DEFS:
        current = progress.get(kind, 0)
        out.append((label_key, current >= threshold, current, threshold, kind))
    return out
