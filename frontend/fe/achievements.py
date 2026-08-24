#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Eigenes Erfolgssystem ("Easter Egg System"): versteckte, ereignis-
basierte Erfolge (Nachteule, Marathon, Wochenend-Krieger, Comeback,
Vielseitig), Profil-Statistiken, Frontend-Level, geheime Codes
(Konami-artige Tastenfolgen fuer Entwicklerraum/Regenbogen-Cursor
usw.), Top-Spiele-Liste, Spielzeit-Formatierung. Ausgelagert aus
frontend.py (Modularisierung, Git-Branch 'modular-refactor').

_has_network()/_load_json_dict()/_save_json_dict() bewusst dupliziert
(gleiches Muster wie in fe/scan.py/fe/timekeeping.py/
fe/retroachievements.py) - werden auch von frontend.py selbst
gebraucht, ein Ruecksfall-Import haette einen Zirkelbezug ausgeloest.
"""
import os, json, time, random
from fe.log import LOG
from fe.playtime import load_playtime, _current_year, compute_milestone_progress, get_milestones
from fe.retroachievements import RA_PROGRESS_SUMMARY_FILE
from fe.game_state import _load_favorites_raw

HIDDEN_UNLOCKED_FILE = "/media/fat/frontend/hidden_achievements.json"

def _load_hidden_unlocked():
    """Menge der IDs bereits freigeschalteter, EREIGNIS-basierter
    versteckter Erfolge."""
    try:
        with open(HIDDEN_UNLOCKED_FILE) as f:
            data = json.load(f)
            return set(data) if isinstance(data, list) else set()
    except (OSError, ValueError):
        return set()

def _unlock_hidden(achievement_id):
    """Schaltet einen ereignis-basierten versteckten Erfolg frei
    (dauerhaft gespeichert). Rueckgabe: True, wenn er JETZT neu
    freigeschaltet wurde, False, wenn er es schon vorher war."""
    data = _load_hidden_unlocked()
    if achievement_id in data:
        return False
    data.add(achievement_id)
    try:
        os.makedirs(os.path.dirname(HIDDEN_UNLOCKED_FILE), exist_ok=True)
        with open(HIDDEN_UNLOCKED_FILE, "w") as f:
            json.dump(sorted(data), f)
    except OSError:
        pass
    return True

# NEU (Nutzerwunsch: weitere versteckte Erfolge): drei zusaetzliche
# kleine Tracker-Dateien, alle nach demselben Muster wie
# HIDDEN_UNLOCKED_FILE - defensiv (fehlende/kaputte Datei = leerer
# Anfangszustand, nie ein Absturz).
WEEKEND_TRACKER_FILE = "/media/fat/frontend/weekend_tracker.json"
LAST_PLAYED_FILE = "/media/fat/frontend/last_played.json"
DAILY_SYSTEMS_FILE = "/media/fat/frontend/daily_systems.json"

def _load_json_dict(path):
    try:
        with open(path) as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}

def _save_json_dict(path, data):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f)
    except OSError:
        pass

def _check_weekend_warrior(session_start_walltime, local_time):
    """'Wochenend-Krieger': an Samstag UND Sonntag DERSELBEN ISO-Woche
    gespielt. tm_wday: Montag=0 ... Sonntag=6, Samstag=5. Nur ein
    winziger Eintrag pro Woche (max. ~52/Jahr) - kein Aufraeumen
    noetig, das waechst ueber Jahre hinweg vernachlaessigbar."""
    wday = local_time.tm_wday
    if wday not in (5, 6):
        return
    week_key = time.strftime("%G-W%V", local_time)
    tracker = _load_json_dict(WEEKEND_TRACKER_FILE)
    days = set(tracker.get(week_key, []))
    days.add(wday)
    tracker[week_key] = sorted(days)
    _save_json_dict(WEEKEND_TRACKER_FILE, tracker)
    if 5 in days and 6 in days:
        _unlock_hidden("weekend_warrior")

def _check_comeback(label, session_start_walltime):
    """'Comeback': dasselbe Spiel nach 6+ Monaten Pause wieder
    gestartet. Vergleicht den ZULETZT gespeicherten Zeitstempel GEGEN
    JETZT, BEVOR er mit dem neuen Wert ueberschrieben wird - Pruefung
    und Aktualisierung bewusst in EINER Funktion, damit die Reihenfolge
    nie versehentlich vertauscht werden kann."""
    if not label:
        return
    data = _load_json_dict(LAST_PLAYED_FILE)
    old_ts = data.get(label)
    if old_ts is not None:
        try:
            if session_start_walltime - float(old_ts) >= 180 * 24 * 3600:
                _unlock_hidden("comeback")
        except (TypeError, ValueError):
            pass
    data[label] = session_start_walltime
    _save_json_dict(LAST_PLAYED_FILE, data)

def _check_versatile(syskey, session_start_walltime, local_time):
    """'Vielseitig': an einem Tag Spiele aus 4+ verschiedenen Systemen
    gestartet. Taeglich zurueckgesetzt (Datumsvergleich)."""
    if not syskey:
        return
    today = time.strftime("%Y-%m-%d", local_time)
    data = _load_json_dict(DAILY_SYSTEMS_FILE)
    if data.get("date") != today:
        data = {"date": today, "systems": []}
    systems = set(data.get("systems", []))
    systems.add(syskey)
    data["systems"] = sorted(systems)
    _save_json_dict(DAILY_SYSTEMS_FILE, data)
    if len(systems) >= 4:
        _unlock_hidden("versatile")

def check_hidden_session_achievements(session_start_walltime, elapsed_seconds,
                                      label=None, syskey=None):
    """Nach einer gespielten Sitzung (siehe run_core()) pruefen, ob
    dadurch ein ereignis-basierter versteckter Erfolg freigeschaltet
    wird. session_start_walltime: echte Wanduhrzeit (time.time()) beim
    Sitzungsbeginn - NICHT die monotone Zeit, die fuer die
    Dauer-Berechnung genutzt wird (die ist unempfindlich gegen
    Uhr-Korrekturen, sagt aber nichts ueber die Tageszeit aus).

    label/syskey (neu, optional - Rueckwaertskompatibel, bislang
    einziger Aufrufer ist run_core()): fuer 'Comeback' (dasselbe Spiel
    nach langer Pause) und 'Vielseitig' (mehrere Systeme an einem Tag)
    zusaetzlich zu den bereits bestehenden Nachteule/Marathon-Pruefungen
    noetig. Alles einzeln try/except-abgesichert - ein Problem bei
    einer Pruefung darf niemals eine andere verhindern."""
    try:
        lt = time.localtime(session_start_walltime)
        hour = lt.tm_hour
        if 0 <= hour < 5:
            _unlock_hidden("night_owl")
        elif 5 <= hour < 7:
            _unlock_hidden("early_bird")
        _check_weekend_warrior(session_start_walltime, lt)
    except Exception:
        pass
    if elapsed_seconds >= 3 * 3600:
        _unlock_hidden("marathon")
    try:
        _check_comeback(label, session_start_walltime)
    except Exception:
        pass
    try:
        _check_versatile(syskey, session_start_walltime,
                         time.localtime(session_start_walltime))
    except Exception:
        pass

def _ra_100pct_achieved():
    """'Perfektionist': mindestens ein Spiel zu 100% bei RetroAchievements
    abgeschlossen. Liest eine kleine, separat gepflegte Zusammenfassung
    (siehe build_ra_lookup()) statt selbst RA abzufragen - diese Funktion
    ist eine reine, synchrone Anzeige-Hilfsfunktion (wird u.a. beim
    Zeichnen des Trophaeenraums aufgerufen) und darf niemals selbst
    Netzwerkzugriffe ausloesen."""
    data = _load_json_dict(RA_PROGRESS_SUMMARY_FILE)
    return bool(data.get("any_100pct"))

def get_hidden_achievements():
    """Liste (id, label_key, freigeschaltet)-Tupel fuer alle
    versteckten Erfolge."""
    unlocked_events = _load_hidden_unlocked()
    favorites_count = len(_load_favorites_raw())
    playtime = load_playtime()
    max_launches = max((e.get("launches", 0) for e in playtime.values()),
                       default=0)
    progress = compute_milestone_progress()
    legend_unlocked = (progress["playtime_seconds"] >= 360000 and
                       progress["launches"] >= 500 and
                       progress["systems"] >= 10 and
                       progress["completed"] >= 25)
    return [
        ("night_owl", "hidden_night_owl", "night_owl" in unlocked_events),
        ("marathon", "hidden_marathon", "marathon" in unlocked_events),
        ("collector", "hidden_collector", favorites_count >= 10),
        ("completionist", "hidden_completionist", max_launches >= 20),
        ("legend", "hidden_legend", legend_unlocked),
        ("early_bird", "hidden_early_bird", "early_bird" in unlocked_events),
        ("weekend_warrior", "hidden_weekend_warrior", "weekend_warrior" in unlocked_events),
        ("comeback", "hidden_comeback", "comeback" in unlocked_events),
        ("versatile", "hidden_versatile", "versatile" in unlocked_events),
        ("perfectionist", "hidden_perfectionist", _ra_100pct_achieved()),
    ]

# ----------------------------------------------------------------------------
# POP-UP BEI NEU ERREICHTEN ERFOLGEN - vergleicht den aktuellen Stand
# (normale Meilensteine UND versteckte Erfolge, jeweils live berechnet)
# gegen eine dauerhafte Liste "das wurde dem Nutzer schon gezeigt", damit
# nach einem Neustart nicht ploetzlich alle laengst erreichten Erfolge
# erneut aufploppen - nur ECHT NEUE loesen ein Pop-up aus.
ACHIEVEMENTS_SEEN_FILE = "/media/fat/frontend/achievements_seen.json"

def _load_achievements_seen():
    try:
        with open(ACHIEVEMENTS_SEEN_FILE) as f:
            data = json.load(f)
            return set(data) if isinstance(data, list) else set()
    except (OSError, ValueError):
        return set()

def _save_achievements_seen(seen):
    try:
        os.makedirs(os.path.dirname(ACHIEVEMENTS_SEEN_FILE), exist_ok=True)
        with open(ACHIEVEMENTS_SEEN_FILE, "w") as f:
            json.dump(sorted(seen), f)
    except OSError:
        pass

def _ensure_achievements_seen_initialized():
    """Initialisiert ACHIEVEMENTS_SEEN_FILE einmalig GLEICH BEIM START
    (Frontend.__init__()), falls sie noch nicht existiert - markiert
    alle zu DIESEM Zeitpunkt bereits erreichten Erfolge als "gezeigt",
    OHNE dafuer ein Pop-up auszuloesen (sonst gaebe es bei jemandem mit
    laengerer Spielhistorie eine Flut von Meldungen fuer laengst
    Erreichtes).

    BUGFIX (Nutzer-Rueckmeldung): 3 verschiedene Systeme gestartet,
    "Entdecker"-Erfolg korrekt in "Meine Erfolge" als erreicht
    angezeigt - aber KEIN Pop-up/Ton beim Zurueckkehren aus dem Spiel.
    Ursache: die Erstlauf-Sonderbehandlung sass bisher direkt IN
    check_new_achievements() und griff beim ALLERERSTEN Aufruf dieser
    Funktion ueberhaupt - der aber zufaellig GENAU in dem Moment
    passieren konnte, in dem der Erfolg WIRKLICH neu erreicht wurde
    (z.B. die erste jemals gespielte Sitzung, bei der zugleich das
    dritte System erreicht wird). Der Erfolg wurde dadurch faelschlich
    als "schon vorher da gewesen" behandelt und sein Pop-up
    unterdrueckt. Fix: die Baseline wird jetzt explizit VOR jeder
    moeglichen Nutzeraktion initialisiert (siehe Frontend.__init__()),
    dadurch ist die Datei bei JEDEM tatsaechlichen Ereignis-Aufruf
    (Sitzungsende, Favorit/Durchgespielt umschalten) bereits vorhanden
    - check_new_achievements() selbst braucht dadurch keine Erstlauf-
    Sonderbehandlung mehr und meldet zuverlaessig jeden Erfolg, der
    NACH dem Start neu erreicht wird."""
    if os.path.exists(ACHIEVEMENTS_SEEN_FILE):
        return
    seen = set()
    for label_key, achieved, _current, _threshold, _kind in get_milestones():
        if achieved:
            seen.add(label_key)
    for hid, _label_key, unlocked in get_hidden_achievements():
        if unlocked:
            seen.add(hid)
    _save_achievements_seen(seen)

def check_new_achievements():
    """Vergleicht den aktuellen Erfolgs-Stand gegen die bereits gezeigten
    - liefert eine Liste der NEU erreichten label_keys (in der
    Reihenfolge: normale Meilensteine, dann versteckte Erfolge) und
    merkt sie SOFORT als gezeigt, damit derselbe Erfolg nicht ein
    zweites Mal ein Pop-up ausloest. Leere Liste, wenn nichts Neues
    dazugekommen ist - der haeufigste Fall, entsprechend guenstig
    (nur Mengen-Operationen, kein Datei-Schreiben ohne Aenderung).

    Setzt voraus, dass _ensure_achievements_seen_initialized() bereits
    beim Start gelaufen ist (siehe Frontend.__init__()) - deshalb hier
    KEINE eigene Erstlauf-Sonderbehandlung mehr noetig (siehe dort fuer
    die Begruendung/den Bugfix)."""
    seen = _load_achievements_seen()
    newly = []
    for label_key, achieved, _current, _threshold, _kind in get_milestones():
        if achieved and label_key not in seen:
            newly.append(label_key)
            seen.add(label_key)
    for hid, label_key, unlocked in get_hidden_achievements():
        if unlocked and hid not in seen:
            newly.append(label_key)
            seen.add(hid)
    if newly:
        _save_achievements_seen(seen)
    return newly


# ----------------------------------------------------------------------------
# TROPHAEENRAUM - persoenlicher Profil-Bildschirm: meistgespieltes Spiel,
# Lieblingssystem, Erfolgs-Zaehler, kurze Zusammenfassung. Baut komplett
# auf Daten auf, die wir ohnehin schon sammeln (Spielzeit-Tracker,
# Meilensteine) - reine Zusammenfassung, keine neue Datenquelle.
def compute_profile_stats():
    """Sammelt die Kennzahlen fuer den Trophaeenraum-Bildschirm.
    Liefert ein dict - alle Werte auch bei komplett leerer Historie
    sicher (0/None statt eines Fehlers), damit der Bildschirm auch
    fuer jemanden ohne jede Spielzeit sinnvoll etwas anzeigen kann."""
    playtime = load_playtime()
    total_seconds = sum(e.get("seconds", 0) for e in playtime.values())
    total_launches = sum(e.get("launches", 0) for e in playtime.values())

    top = top_played_games(by="seconds", n=1)
    top_game = top[0] if top else None   # (label, seconds, launches)

    # Lieblingssystem: Summe der Spielzeit pro System (nur Eintraege mit
    # bekanntem syskey - siehe record_playtime()/v1.92).
    system_seconds = {}
    for e in playtime.values():
        sk = e.get("syskey")
        if sk:
            system_seconds[sk] = system_seconds.get(sk, 0) + e.get("seconds", 0)
    favorite_system = (max(system_seconds, key=system_seconds.get)
                       if system_seconds else None)

    milestones = get_milestones()
    hidden = get_hidden_achievements()
    unlocked = (sum(1 for m in milestones if m[1])
               + sum(1 for h in hidden if h[2]))
    total_achievements = len(milestones) + len(hidden)

    return {
        "total_seconds": total_seconds,
        "total_launches": total_launches,
        "top_game": top_game,
        "favorite_system": favorite_system,
        "distinct_systems": len(system_seconds),
        "unlocked": unlocked,
        "total_achievements": total_achievements,
    }

# ----------------------------------------------------------------------------
# FRONTEND-LEVEL (Nutzerwunsch: "das Menue sammelt Erfahrungspunkte,
# nicht der Spieler") - rein abgeleitet aus Werten, die wir ohnehin
# schon dauerhaft speichern (Spielzeit, Starts, versteckte Erfolge).
# Kein zusaetzlicher Speicherbedarf, kann bei jedem Aufruf frisch
# berechnet werden - und ist von Natur aus monoton (kann nie sinken,
# da die zugrunde liegenden Werte nur wachsen koennen).
FRONTEND_LEVEL_MAX = 5

def compute_frontend_level():
    """Liefert das aktuelle Frontend-Level (1-5). Stufen bewusst grosszuegig
    UND ueber mehrere Wege erreichbar (Spielzeit ODER Starts ODER
    versteckte Erfolge) - niemand soll sich durch eine einzelne, enge
    Anforderung ausgeschlossen fuehlen."""
    stats = compute_profile_stats()
    hours = stats["total_seconds"] / 3600.0
    launches = stats["total_launches"]
    hidden = get_hidden_achievements()
    hidden_count = sum(1 for h in hidden if h[2])
    legend_unlocked = any(h[0] == "legend" and h[2] for h in hidden)

    if legend_unlocked:
        return 5
    if hours >= 50 or hidden_count >= 3:
        return 4
    if hours >= 20 or launches >= 50:
        return 3
    if hours >= 5 or launches >= 20:
        return 2
    return 1

# ----------------------------------------------------------------------------
# GEHEIME CODES (Nutzerwunsch: "Easter Egg System" - ein paar
# Cheat-Code-Sequenzen, jede schaltet ein anderes Geheimnis frei). Auf
# unser Aktions-Vokabular uebertragen. Absichtlich KEINE ausfuehrliche
# Erklaerung hier im Kommentar, welche Codes das sind oder woher sie
# stammen - das darf sich jede/r selbst erspielen, siehe
# draw_secrets_screen().
#
# WICHTIG (Nutzer-Nachfrage, Design zweimal korrigiert):
#   1. Versuch: "ok"/"back" fuer die Bestaetigungs-Positionen - FALSCH,
#      beide loesen im Hauptmenue IMMER eine echte Wirkung aus
#      (Kategorie betreten bzw. Beenden-Bestaetigung, siehe
#      _go_back_or_confirm_quit()), auch waehrend einer laufenden
#      Code-Eingabe. Einer der Codes haette dadurch NIE vollstaendig
#      eingegeben werden koennen.
#   2. Versuch: "favorite"/"completed" (F7/F8) statt ok/back - beide
#      nachweislich wirkungslos, ABER: "completed" hat GAR KEINE
#      Joypad-Taste (nur Tastatur F7), und "favorite" liegt auf L2/R2 -
#      auf SNES-Nachbau-Pads (bei MiSTer-Nutzern verbreitet) oft gar
#      nicht vorhanden. Auf einem einfachen Pad war praktisch KEINE
#      Taste mehr frei, die garantiert wirkungslos ist.
#   FINALE LOESUNG (auf Nutzerwunsch): Codes werden bewusst NUR per
#   TASTATUR eingegeben - Pfeiltasten fuer die Richtungen, echte
#   Buchstabentasten fuer die Bestaetigungs-Positionen. Buchstabentasten
#   loesen im Hauptmenue nur einen harmlosen Buchstaben-Sprung in der
#   Kategorienliste aus (siehe LETTER_KEYS/"letter:"-Aktion,
#   jump_to_letter()) - GENAUSO sicher wie hoch/runter/links/rechts,
#   kein Seitenwechsel, kein Dialog. Per Joypad sind diese Codes damit
#   bewusst NICHT eingebbar - siehe Hinweistext auf dem Geheimnisse-
#   Bildschirm.
SECRETS_FILE = "/media/fat/frontend/secrets_unlocked.json"

SECRET_CODES = {
    # Schaltet das erste geheime Theme frei. Nur per Tastatur eingebbar.
    "secret_theme_1": ["up", "up", "down", "down", "left", "right",
                       "left", "right", "letter:B", "letter:A"],
    # Schaltet den Entwicklerraum frei. Nur per Tastatur eingebbar.
    #
    # BUGFIX (Nutzer-Rueckmeldung: "der Code fuer den Entwicklerraum
    # funktioniert nicht", dann auf Nachfrage: "geh davon aus, dass
    # jeder eine deutsche Tastatur hat"): der Bug lag nicht am "Y"
    # selbst, sondern daran, dass LETTER_KEYS in fe/input.py Y/Z bisher
    # nach der reinen US-QWERTY-Scancode-Bedeutung benannt hatte, obwohl
    # das Frontend rohe Scancodes ohne Tastaturlayout-Umrechnung liest -
    # auf einer deutschen QWERTZ-Tastatur loeste die bedruckte "Y"-Taste
    # dadurch "letter:Z" aus statt "letter:Y". Der eigentliche Fix sitzt
    # jetzt direkt in LETTER_KEYS (siehe dortiger Kommentar) - die
    # Zuordnung ist dort bewusst an die deutsche Tastatur angepasst,
    # nicht layoutneutral. "letter:Y" hier ist also wieder das Original.
    "entwicklerraum": ["down", "letter:R", "up", "letter:L",
                      "letter:Y", "letter:B"],
    # Schaltet einen geheimen Sound frei. Nur per Tastatur eingebbar.
    "secret_sound": ["letter:A", "letter:B", "letter:B", "letter:A"],
    # NEU (Nutzerwunsch, Easter Egg): faerbt den Auswahl-Cursor im
    # Hauptmenue fuer eine Weile in Regenbogenfarben. Nur per Tastatur
    # eingebbar, wie alle anderen Codes.
    "rainbow_cursor": ["letter:R", "letter:A", "letter:I", "letter:N",
                       "letter:B", "letter:O", "letter:W"],
    # NEU (Nutzerwunsch, Easter Egg): spielt einen kurzen 8-Bit-Chiptune-
    # Jingle ab (ueber denselben gedaempften Weg wie der geheime Sound/
    # die Erfolgs-Jingles - siehe _play_ducked_sfx()). Nur per Tastatur.
    "chiptune_sound": ["letter:C", "letter:H", "letter:I", "letter:P"],

    # NEU (Nutzerwunsch: "Secret-Sammlung" mit einem eigenen Theme pro
    # klassischem System, angelehnt an bekannte Cheat-/Level-Select-Codes
    # dieser Systeme). WICHTIG: unsere Codes koennen NUR aus Pfeiltasten
    # und Buchstaben bestehen (siehe Design-Erklaerung ganz oben in
    # diesem Kommentarblock - ok/back/select loesen im Hauptmenue immer
    # eine echte Wirkung aus). Die Original-Vorlagen benutzen teils
    # Gesichtstasten (A/B/X/Y - lassen sich 1:1 als Buchstaben
    # uebernehmen, genau wie beim bestehenden Konami-Code oben), teils
    # aber auch Select/Start, Zahlen oder System-spezifische Tasten ohne
    # Tastatur-Aequivalent (PS1-Symbole, Mega-Drive-Sound-Test-Ziffern) -
    # diese wurden durch thematisch passende Buchstaben ERSETZT statt
    # weggelassen, um trotzdem auf die volle, eindeutige Laenge des
    # Originals zu kommen. Jeder Code unten wurde einzeln gegen ALLE
    # anderen (auch die vier oben) auf Eindeutigkeit UND auf verfrühtes
    # Ausloesen als Teilsequenz geprueft (siehe tools/regression_test.py
    # bzw. das Diagnose-Skript aus der Entwicklung).
    #
    # Original: Batman Forever (SNES) - Stage-/Waffen-Auswahl.
    "theme_snes": ["left", "up", "left", "left",
                  "letter:A", "letter:B", "letter:Y"],
    # Original: Game Genie/"Message 2" (Game Boy). Select durch die
    # Buchstaben G,B (fuer "Game Boy") ersetzt.
    "theme_gb": ["letter:B", "letter:A", "left", "right",
                "letter:G", "letter:B"],
    # Original: Cheat-Menu-Code aus Space Invaders (Game Boy Color).
    # Die beiden Select-Druecke durch "NEON" (Theme-Name) ersetzt.
    "theme_gbc": ["down", "down", "letter:N", "letter:E",
                 "letter:O", "letter:N"],
    # Original: Robotron 64 (N64) - C-Oben-Taste durch "T" (Turbo)
    # ersetzt, siehe der zugehoerige Turbo-Scroll-Effekt in
    # _on_secret_triggered().
    "theme_n64": ["left", "left", "right", "right", "letter:T"],
    # Original: Aladdin (PS1) - die Dreieck/Quadrat/Kreis-Symbole haben
    # kein Tastatur-Aequivalent, ersetzt durch "PSX".
    "theme_ps1": ["right", "right", "letter:P", "letter:S", "letter:X"],
    # Original: Sonic 2 (Mega Drive) - der beruehmte Sound-Test-Code ist
    # eine elfstellige Ziffernfolge (kein "digit:"-Aktionstyp vorhanden,
    # siehe fe/input.py), ersetzt durch "RING" (Sonics Ringe).
    "theme_megadrive": ["down", "down", "letter:R", "letter:I",
                        "letter:N", "letter:G"],
    # Original: Sonic Chaos (Master System) - eigener Sound-Test-Code,
    # NICHT identisch mit dem Mega-Drive-Code oben (bewusst getrennt
    # gehalten, wie in der urspruenglichen Recherche gefordert).
    "theme_sms": ["up", "up", "down", "down",
                 "letter:S", "letter:M", "letter:S"],
    # Original: Sonic Chaos (Game Gear) - hier fast 1:1 uebernehmbar,
    # nur das abschliessende "Start" entfaellt (nicht codetauglich).
    "theme_gamegear": ["up", "up", "down", "down",
                       "right", "left", "right", "left"],
    # Original: Sonic Jam/Sonic 2 Level-Select (Saturn) - "A+Start" am
    # Ende durch "SAT" ersetzt.
    "theme_saturn": ["down", "up", "letter:S", "letter:A", "letter:T"],

    # Dreamcast BEWUSST NICHT dabei: es gibt zwar Sonic-Adventure-
    # Geheimnisse, aber noch keinen sauber belegten, wirklich
    # eindeutigen Code dafuer (siehe Recherche-Notiz) - lieber kein
    # erfundener Code als einer, der spaeter falsch zugeordnet wird.
}
SECRET_CODE_MAXLEN = max(len(seq) for seq in SECRET_CODES.values())

# NEU (Nutzerwunsch: "ein Geheimnis im Geheimnis"): BEWUSST NICHT Teil
# von SECRET_CODES/check_secret_code() - jene Pruefung laeuft nur auf
# Seite 0 (Hauptmenue, siehe run()) und wuerde diesen Code sonst AUCH
# dort ausloesen. draw_dev_room_screen() prueft diese eigene, kurze
# Sequenz komplett unabhaengig, in einem eigenen kleinen Puffer -
# dadurch nur WAEHREND man sich tatsaechlich bereits im Entwicklerraum
# befindet eingebbar. Trotzdem ueber dieselbe _unlock_secret()/
# _load_secrets_unlocked()-Speicherung wie die "echten" Geheimnisse
# (die validieren nicht gegen SECRET_CODES, reine ID-Menge) - zaehlt
# deshalb ganz normal mit, siehe die beiden "+1"-Stellen bei den
# X-von-Y-Anzeigen unten.
DEV_ROOM_BONUS_ID = "dev_room_bonus"
DEV_ROOM_BONUS_CODE = ["letter:E", "letter:G", "letter:G"]

RAINBOW_CURSOR_SECONDS = 120   # wie lange der Regenbogen-Cursor-Effekt anhaelt

def _load_secrets_unlocked():
    """Menge der IDs bereits per Geheimcode freigeschalteter
    Geheimnisse - gleiches Speicherprinzip wie bei den versteckten
    Erfolgen (siehe _load_hidden_unlocked())."""
    try:
        with open(SECRETS_FILE) as f:
            data = json.load(f)
            return set(data) if isinstance(data, list) else set()
    except (OSError, ValueError):
        return set()

def _unlock_secret(secret_id):
    """Schaltet ein Geheimnis dauerhaft frei. Rueckgabe: True, wenn es
    JETZT neu freigeschaltet wurde, False, wenn es das schon vorher
    war (z.B. Code versehentlich zweimal eingegeben)."""
    data = _load_secrets_unlocked()
    if secret_id in data:
        return False
    data.add(secret_id)
    try:
        os.makedirs(os.path.dirname(SECRETS_FILE), exist_ok=True)
        with open(SECRETS_FILE, "w") as f:
            json.dump(sorted(data), f)
    except OSError:
        pass
    return True

def check_secret_code(buffer):
    """Prueft, ob der Schluss des Aktions-Puffers (Liste der zuletzt
    gedrueckten Aktionen, neueste zuletzt) exakt einem der bekannten
    Geheim-Codes entspricht. Liefert die passende secret_id oder None.
    Reine Vergleichsfunktion ohne Seiteneffekt - das eigentliche
    Freischalten uebernimmt der Aufrufer (siehe Frontend._check_secret_
    codes())."""
    for secret_id, seq in SECRET_CODES.items():
        n = len(seq)
        if len(buffer) >= n and list(buffer[-n:]) == seq:
            return secret_id
    return None


def top_played_games(by="seconds", n=10):
    """Liefert die n Spiele mit dem hoechsten Wert fuer "seconds"
    (Gesamtspielzeit) oder "launches" (Anzahl Starts), absteigend
    sortiert, als Liste von (label, seconds, launches)-Tupeln. Spiele
    mit 0 in der gesuchten Kategorie werden ausgelassen (kein Sinn,
    "Platz 7: 0 Starts" anzuzeigen)."""
    data = load_playtime()
    items = [(label, e["seconds"], e["launches"])
             for label, e in data.items() if e.get(by, 0) > 0]
    idx = 1 if by == "seconds" else 2
    items.sort(key=lambda t: -t[idx])
    return items[:n]

def format_playtime(seconds):
    """Formatiert eine Sekundenzahl fuer die Anzeige - z.B. "2h 15min"
    oder "5min" oder "< 1min"."""
    if seconds is None or seconds <= 0:
        return None
    mins = int(seconds // 60)
    if mins < 1:
        return None   # unter einer Minute - noch nichts Sinnvolles zu zeigen
    h, m = divmod(mins, 60)
    if h > 0:
        return "%dh %dmin" % (h, m) if m else "%dh" % h
    return "%dmin" % m
