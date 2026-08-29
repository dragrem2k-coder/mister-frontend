#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RetroAchievements-Integration (optional - komplett unsichtbar, solange
nicht eingerichtet): Konfiguration, Fortschritts-/Erfolgs-Abruf per
RA-Web-API, Erfolgs-Cache, Name/System-Zuordnung zwischen unseren
Spielenamen und RAs Datenbank. Ausgelagert aus frontend.py
(Modularisierung, Git-Branch 'modular-refactor').
"""
import os, json, time, re, urllib.request, urllib.parse, urllib.error, threading
from fe.log import LOG
from fe.art import BADGES

def _has_network():
    """Prueft, ob irgendein Netzwerk-Interface eine Adresse hat - siehe
    ausfuehrlichen Kommentar in fe/scan.py (dort dieselbe Funktion,
    bewusst dupliziert statt importiert, gleicher Grund: frontend.py
    braucht die Original-Kopie ebenfalls, ein Ruecksfall-Import haette
    einen Zirkelbezug ausgeloest)."""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return bool(ip) and not ip.startswith("127.")
    except OSError:
        return False

def _load_json_dict(path):
    """Generischer JSON-Dict-Lader - bewusst dupliziert (siehe
    frontend.py, wird auch von der 'Versteckte Erfolge'-Sektion
    gebraucht, die noch nicht ausgelagert ist)."""
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

# RETROACHIEVEMENTS (optional - komplett unsichtbar, solange nicht
# eingerichtet)
#
# Einrichtung per SSH/Texteditor (keine Bildschirmtastatur im Frontend -
# ein API-Schluessel waere per Steuerkreuz kaum eintippbar): Datei mit
# zwei Zeilen, erste der RA-Benutzername, zweite der Web-API-Schluessel
# (aus dem eigenen RA-Kontrollbereich, Abschnitt "Keys").
RA_CONFIG_FILE = "/media/fat/frontend/retroachievements.cfg"

def load_ra_config():
    """Liest Benutzername + API-Schluessel aus RA_CONFIG_FILE. Liefert
    (benutzername, schluessel) oder (None, None), wenn die Datei fehlt,
    leer ist oder nicht mindestens zwei nicht-leere Zeilen enthaelt -
    JEDER Fehlerfall wird als "nicht eingerichtet" behandelt, nie als
    Absturz. Das ist bewusst die EINZIGE Stelle, die entscheidet, ob
    RetroAchievements ueberhaupt aktiv ist - alle anderen RA-Funktionen
    bauen darauf auf."""
    try:
        with open(RA_CONFIG_FILE) as f:
            lines = [ln.strip() for ln in f.readlines()]
    except OSError:
        return None, None
    lines = [ln for ln in lines if ln]   # leere Zeilen ueberspringen
    if len(lines) < 2:
        return None, None
    return lines[0], lines[1]

# NEUES FEATURE (Nutzerwunsch: "ich würde gerne die Option haben, die
# RetroAchievements von dort [System-Menue] an und aus zu schalten" -
# bisher gab es im System-Menue unter "RetroAchievements" NUR "neu
# laden", ein tatsaechliches Abschalten ging ausschliesslich durch
# Loeschen/Umbenennen von RA_CONFIG_FILE per SSH). Bewusst GETRENNT von
# der Einrichtung selbst (Benutzername+API-Schluessel bleiben beim
# Deaktivieren unangetastet - ein spaeteres Wiedereinschalten braucht
# keine erneute Einrichtung) - reiner lokaler Ein/Aus-Schalter nach
# demselben "Standard an, per Markierungsdatei abschaltbar"-Muster wie
# die uebrigen kleinen Ein/Aus-Einstellungen (siehe fe/settings.py).
RA_DISABLED_FLAG = "/media/fat/frontend/retroachievements_disabled"

def ra_toggle_enabled():
    """NUR der lokale Ein/Aus-Schalter selbst (unabhaengig davon, ob
    ueberhaupt Zugangsdaten hinterlegt sind) - fuer die tatsaechlich
    massgebliche Kombination aus beidem siehe ra_enabled() unten."""
    return not os.path.exists(RA_DISABLED_FLAG)

def toggle_ra_enabled():
    if ra_toggle_enabled():
        try:
            os.makedirs(os.path.dirname(RA_DISABLED_FLAG), exist_ok=True)
            open(RA_DISABLED_FLAG, "w").close()
        except OSError:
            pass
    else:
        try:
            os.remove(RA_DISABLED_FLAG)
        except OSError:
            pass

def ra_enabled():
    """Kurzform: ist RetroAchievements gerade tatsaechlich aktiv? Das
    ist der Fall, wenn (a) Zugangsdaten hinterlegt sind UND (b) der
    Nutzer es nicht ueber den Ein/Aus-Schalter (ra_toggle_enabled())
    manuell pausiert hat. Bewusst als EINZIGE kombinierte Pruefung -
    ALLE anderen RA-Funktionen im Frontend (Fortschrittsanzeige,
    Abzeichen, Erfolgs-Vitrine, Bestenlisten/Meilensteine) bauen
    darauf auf, ein Aus-/Wiedereinschalten wirkt dadurch ueberall
    sofort konsistent, ohne jede einzelne Aufrufstelle einzeln
    anzupassen. Betrifft NICHT find_ra_core()/die RA-Core-Auswahl beim
    Betreten eines Systems (fe/ra_core.py) - das ist ein unabhaengiger
    Mechanismus (welche Core-BINARY gestartet wird), der weiterhin
    unveraendert funktioniert, auch wenn hier pausiert wurde."""
    u, k = load_ra_config()
    return u is not None and k is not None and ra_toggle_enabled()

RA_API_URL = "https://retroachievements.org/API/API_GetUserCompletionProgress.php"

def fetch_ra_progress(username, api_key, timeout=5.0):
    """Fragt bei RetroAchievements die komplette Fortschrittsliste des
    Nutzers ab (ein Aufruf fuer ALLE Spiele, mit denen er je zu tun
    hatte). Liefert eine Liste von (titel, systemname, erreicht,
    moeglich)-Tupeln, oder None bei JEDEM Fehler (kein Internet,
    falscher Schluessel, Zeitueberschreitung, unerwartete Antwort) -
    NIE eine Ausnahme nach aussen, das ruft aus einem Hintergrund-
    Thread heraus auf (siehe Schritt 3) und darf den Rest des
    Frontends unter keinen Umstaenden beeintraechtigen.

    EHRLICHER HINWEIS: die genauen Feldnamen der Antwort sind anhand
    der oeffentlichen RA-API-Dokumentation nachgebaut, aber NICHT gegen
    den echten Server verifiziert (in dieser Umgebung nicht moeglich).
    Deshalb werden mehrere plausible Feldnamen-Varianten akzeptiert und
    JEDES fehlende/anders benannte Feld fuehrt zu einem stillen
    Auslassen dieses EINEN Eintrags statt einem Abbruch - falls sich
    beim ersten echten Test ein Feldname als falsch herausstellt,
    liefert die Funktion einfach eine leere oder unvollstaendige Liste
    statt abzustuerzen."""
    try:
        params = urllib.parse.urlencode({"u": username, "y": api_key})
        url = RA_API_URL + "?" + params
        req = urllib.request.Request(url, headers={"User-Agent": "MiSTerFrontend/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                LOG("fetch_ra_progress: HTTP-Status %d" % resp.status)
                return None
            raw = resp.read()
        data = json.loads(raw)
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as e:
        LOG("fetch_ra_progress: fehlgeschlagen: %s" % e)
        return None

    # Die Ergebnisliste kann je nach Antwortform direkt eine Liste sein
    # ODER unter einem Schluessel wie "Results" liegen - beides
    # abdecken.
    if isinstance(data, dict):
        entries = data.get("Results") or data.get("results") or []
    elif isinstance(data, list):
        entries = data
    else:
        entries = []

    out = []
    for e in entries:
        if not isinstance(e, dict):
            continue
        title = e.get("Title") or e.get("title")
        system = e.get("ConsoleName") or e.get("consoleName") or e.get("console")
        total = e.get("MaxPossible") or e.get("maxPossible") or e.get("NumAchievements")
        earned = e.get("NumAwarded") or e.get("numAwarded") or e.get("NumAwardedHardcore")
        game_id = e.get("GameID") or e.get("gameId") or e.get("ID")
        if not title or not total:
            continue   # Eintrag ohne verwertbare Kernangaben - auslassen statt raten
        try:
            total = int(total)
            earned = int(earned) if earned is not None else 0
            game_id = int(game_id) if game_id is not None else None
        except (TypeError, ValueError):
            continue
        if total <= 0:
            continue
        out.append((str(title), str(system) if system else "", earned, total, game_id))
    return out

def fetch_ra_progress_bounded(timeout=5.0):
    """Holt die RA-Fortschrittsliste, FALLS eingerichtet und ein
    lokales Netzwerk vorhanden ist - in einem separaten Thread mit
    hartem Zeitlimit, exakt dasselbe Prinzip wie
    sync_system_clock_from_ntp() (siehe dort fuer die Begruendung:
    haengende DNS-Aufloesung wird von urlopen()s eigenem timeout NICHT
    zuverlaessig erfasst). Liefert None, wenn nicht eingerichtet, kein
    Netzwerk vorhanden ist, oder die Abfrage fehlschlaegt/zu lange
    braucht - NIE eine Ausnahme, NIE eine Verzoegerung ueber `timeout`
    Sekunden hinaus."""
    username, api_key = load_ra_config()
    if username is None:
        return None
    if not _has_network():
        return None
    result = {"data": None}
    def worker():
        result["data"] = fetch_ra_progress(username, api_key, timeout=timeout)
    th = threading.Thread(target=worker, daemon=True)
    th.start()
    th.join(timeout=timeout + 0.5)
    return result["data"]

# ----------------------------------------------------------------------------
# EINZELNE ERFOLGSLISTE EINES SPIELS (Nutzerwunsch: "Trophaeen-Vitrine")
#
# Bewusst als EIGENSTAENDIGE, separate Funktion aufgebaut - nutzt zwar
# dieselben Grundbausteine (load_ra_config(), _has_network(), dasselbe
# Zeitlimit-Prinzip) wie die bestehende Fortschrittsabfrage, aendert
# aber NICHTS an ihr. Ruft einen ANDEREN RA-Endpunkt auf (Erfolgsdetails
# zu EINEM Spiel statt der Sammelliste ueber alle Spiele).
RA_GAME_API_URL = "https://retroachievements.org/API/API_GetGameInfoAndUserProgress.php"

def fetch_ra_game_achievements(game_id, timeout=5.0):
    """Fragt bei RetroAchievements die komplette Erfolgsliste EINES
    Spiels ab (Name, Beschreibung, Punkte, Badge-Name, freigeschaltet/
    wann, Hardcore-Status). Liefert eine Liste von (titel, beschreibung,
    punkte, badge_name, freigeschaltet, datum, hardcore)-Tupeln,
    sortiert nach RAs eigener Anzeigereihenfolge, oder None bei JEDEM
    Fehler - NIE eine Ausnahme nach aussen.

    NEU (Nutzerwunsch: "wir unterscheiden gar nicht zwischen Softcore-
    oder Hardcore-Mode bei den Erfolgen"): RA liefert pro Erfolg zwei
    getrennte Freischalt-Zeitstempel - "DateEarned" (Softcore) und
    "DateEarnedHardcore" (Hardcore, wird bei einem Hardcore-Unlock
    IMMER zusaetzlich zum Softcore-Zeitstempel gesetzt, RA behandelt
    einen Hardcore-Unlock also als "beides"). Bisher wurde nur EINER
    von beiden ausgewertet ("welcher zuerst da ist"), der Modus selbst
    ging dabei verloren - ein Hardcore- und ein Softcore-Erfolg sahen
    in der F6-Vitrine identisch aus. Das neue siebte Tupel-Element
    "hardcore" haelt jetzt fest, ob ausdruecklich ein
    Hardcore-Zeitstempel vorlag.

    EHRLICHER HINWEIS: wie bei fetch_ra_progress() sind die genauen
    Feldnamen anhand der oeffentlichen API-Dokumentation nachgebaut,
    nicht gegen den echten Server verifiziert. Mehrere plausible
    Feldnamen-Varianten werden akzeptiert, ein einzelner fehlerhafter
    Erfolgs-Eintrag wird stillschweigend ausgelassen statt die ganze
    Liste abzubrechen."""
    username, api_key = load_ra_config()
    if username is None:
        return None
    try:
        params = urllib.parse.urlencode({"u": username, "y": api_key, "g": game_id})
        url = RA_GAME_API_URL + "?" + params
        req = urllib.request.Request(url, headers={"User-Agent": "MiSTerFrontend/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                LOG("fetch_ra_game_achievements: HTTP-Status %d" % resp.status)
                return None
            raw = resp.read()
        data = json.loads(raw)
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as e:
        LOG("fetch_ra_game_achievements: fehlgeschlagen: %s" % e)
        return None
    if not isinstance(data, dict):
        return None
    achievements = data.get("Achievements") or data.get("achievements")
    if not isinstance(achievements, dict):
        return None

    out = []
    for ach in achievements.values():
        if not isinstance(ach, dict):
            continue
        title = ach.get("Title") or ach.get("title")
        desc = ach.get("Description") or ach.get("description") or ""
        points = ach.get("Points") or ach.get("points")
        badge = ach.get("BadgeName") or ach.get("badgeName")
        order = ach.get("DisplayOrder") or ach.get("displayOrder") or 0
        date_earned_sc = ach.get("DateEarned") or ach.get("dateEarned")
        date_earned_hc = ach.get("DateEarnedHardcore") or ach.get("dateEarnedHardcore")
        date_earned = date_earned_hc or date_earned_sc
        if not title:
            continue
        try:
            points = int(points) if points is not None else 0
            order = int(order) if order is not None else 0
        except (TypeError, ValueError):
            points, order = 0, 0
        out.append((str(title), str(desc), points, str(badge) if badge else None,
                    bool(date_earned), str(date_earned) if date_earned else None, order,
                    bool(date_earned_hc)))
    out.sort(key=lambda a: a[6])   # RAs eigene Anzeigereihenfolge
    return [(a[0], a[1], a[2], a[3], a[4], a[5], a[7]) for a in out]

def fetch_ra_game_achievements_bounded(game_id, timeout=5.0):
    """Wie fetch_ra_game_achievements(), aber zeitlich hart begrenzt in
    einem separaten Thread - exakt dasselbe Prinzip wie
    fetch_ra_progress_bounded() (siehe dort fuer die Begruendung)."""
    if not _has_network():
        return None
    result = {"data": None}
    def worker():
        result["data"] = fetch_ra_game_achievements(game_id, timeout=timeout)
    th = threading.Thread(target=worker, daemon=True)
    th.start()
    th.join(timeout=timeout + 0.5)
    return result["data"]

# BUGFIX/NEUES FEATURE (Nutzerwunsch: F6-Erfolgsliste dauert "ganz
# schoen" lang, laesst sich das speichern/beschleunigen?): bisher
# holte draw_ra_showcase_screen() die komplette Erfolgsliste bei
# JEDEM Aufruf frisch aus dem Netz (bis zu 5s Zeitlimit), auch wenn
# man kurz zuvor schon dasselbe Spiel angesehen hatte - kein eigener
# Cache in der ersten Fassung (siehe damaliger Kommentar: "kann
# spaeter ergaenzt werden, sobald sich das Format in der Praxis
# bewaehrt hat" - hat es jetzt). Kurzlebiger, dateibasierter Cache
# (15 Minuten) nach demselben Prinzip wie BadgeCache/ArtCache: kurz
# genug, dass frisch verdiente Erfolge zeitnah als "freigeschaltet"
# auftauchen, lang genug, um wiederholtes Ansehen desselben Spiels
# (z.B. waehrend einer Session mehrfach F6 druecken) spuerbar zu
# beschleunigen.
RA_ACHIEVEMENTS_CACHE_FILE = "/media/fat/frontend/ra_achievements_cache.json"
RA_ACHIEVEMENTS_CACHE_TTL = 900   # 15 Minuten

def _load_ra_achievements_cache():
    try:
        with open(RA_ACHIEVEMENTS_CACHE_FILE) as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}

def _save_ra_achievements_cache(cache):
    try:
        os.makedirs(os.path.dirname(RA_ACHIEVEMENTS_CACHE_FILE), exist_ok=True)
        with open(RA_ACHIEVEMENTS_CACHE_FILE, "w") as f:
            json.dump(cache, f)
    except OSError:
        pass

# NEUES FEATURE (Nutzerwunsch: F6-Erfolgsvitrine soll "schneller
# einblenden" - bisher blockierte draw_ra_showcase_screen() bei
# abgelaufenem/fehlendem Cache-Eintrag bis zu 5s auf den Netzwerkabruf,
# bevor ueberhaupt eine Erfolgsliste zu sehen war): Stale-while-
# revalidate - IST bereits ein (auch veralteter) Cache-Eintrag da,
# wird der SOFORT zurueckgegeben (kein Warten), waehrend im
# Hintergrund-Thread ein frischer Abruf angestossen wird, der den
# Cache fuer den NAECHSTEN F6-Aufruf desselben Spiels aktualisiert.
# Nur beim ALLERERSTEN Ansehen eines Spiels (noch gar kein Cache-
# Eintrag vorhanden) bleibt ein einmaliger, kurzer synchroner Abruf
# noetig - da gibt es schlicht noch nichts Vorhandenes zum Anzeigen.
# _ra_achievements_refresh_inflight verhindert parallele Mehrfach-
# abrufe fuer dasselbe Spiel bei schnell wiederholtem F6-Druecken.
_ra_achievements_refresh_inflight = set()
_ra_achievements_refresh_lock = threading.Lock()

# NEU (Nutzerwunsch: F6-Erfolgs-Vitrine soll spuerbar schneller
# erscheinen): der Stale-while-revalidate-Cache oben beschleunigt
# bislang nur die TEXT-Erfolgsliste selbst - die Badge-ICONS wurden
# bisher ausschliesslich beim tatsaechlichen F6-Aufruf nachgeladen
# (draw_ra_showcase_screen() in frontend.py, dort noch dazu
# NACHEINANDER statt parallel), nie im Voraus. Bei einem zwar
# vorgewaermten (Text schon da), aber noch nie zuvor ANGESEHENEN Spiel
# mit vielen Erfolgen war genau das der spuerbare Rest-Bremsklotz.
# BADGES.get() (siehe fe/art.py, BadgeCache) cacht dauerhaft auf der
# SD-Karte - ein Icon wird dadurch nie zweimal aus dem Netz geholt,
# dieser Aufruf hier kostet fuer bereits vorhandene Icons praktisch
# nichts.
# BUGFIX/PERFORMANCE (Nutzer-Rueckmeldung: "es nervt total wenn ich in
# meiner gameboy sammlung oder sonst einer sammlung rumscrolle und
# wieder auf zurueck gehe das das teilweise sekunden braucht"):
# _prewarm_ra_achievements() in frontend.py prueft zwar VOR jedem Spiel,
# ob der Nutzer gerade aktiv ist (pausiert sonst) - aber einmal
# gestartet, dekodierte diese Funktion hier bislang ALLE Badge-Icons
# eines Spiels am Stueck durch, ohne zwischendurch nochmal nachzusehen.
# decode_png() (fe/art.py) ist reiner, interpretierter Python-Code ohne
# C-Beschleunigung (~3ms/Icon schon auf schneller x86-Hardware, auf dem
# MiSTer-ARM-Kern deutlich mehr) - bei einem Spiel mit vielen Erfolgen
# (30-80 Icons) hielt der Hintergrund-Thread den GIL damit am Stueck
# potenziell mehrere hundert Millisekunden bis über eine Sekunde fest
# und bremste dadurch den Haupt-Zeichen-/Eingabe-Thread genau dann aus,
# wenn der Nutzer zufaellig mitten in diesem Fenster wieder anfing zu
# scrollen/zurueckzugehen - das erklaert das "teilweise Sekunden"-
# Stocken, das dabei nicht auf Arcade beschraenkt war.
#
# Fix: optionaler should_abort()-Callback wird jetzt nach JEDEM
# einzelnen Icon geprueft (nicht nur einmal vor dem ganzen Spiel) -
# wird der Nutzer waehrenddessen aktiv, bricht das Vorwaermen fuer
# dieses Spiel sofort ab. Die uebrigen Icons dieses Spiels werden dann
# einfach beim naechsten echten Leerlauf nachgeholt (oder ganz normal
# erst beim tatsaechlichen F6-Aufruf geladen, wie vor dem Icon-
# Vorwaermen-Feature) - kein Datenverlust, nur etwas weniger
# Vorab-Beschleunigung fuer dieses eine unterbrochene Spiel.
# should_abort bleibt None (= nie abbrechen) fuer den stale-while-
# revalidate-Refresh unten in fetch_ra_game_achievements_cached() -
# der laeuft ja bereits WAEHREND der Nutzer sich das Spiel auf dem
# F6-Bildschirm ansieht, dort ist ein Abbruch nicht sinnvoll.
def _prewarm_badge_icons(achievements, should_abort=None):
    for entry in achievements or []:
        if should_abort is not None and should_abort():
            break
        badge = entry[3] if len(entry) > 3 else None
        if badge:
            try:
                BADGES.get(badge)
            except Exception:
                pass   # Icon-Vorwaermen darf den Hintergrund-Thread nie stoeren

def _refresh_ra_achievements_background(game_id, timeout=5.0, should_abort=None):
    key = str(game_id)
    with _ra_achievements_refresh_lock:
        if key in _ra_achievements_refresh_inflight:
            return
        _ra_achievements_refresh_inflight.add(key)
    try:
        data = fetch_ra_game_achievements_bounded(game_id, timeout=timeout)
        if data is not None:
            cache = _load_ra_achievements_cache()
            cache[key] = {"ts": time.time(), "data": data}
            _save_ra_achievements_cache(cache)
            _prewarm_badge_icons(data, should_abort=should_abort)
    finally:
        with _ra_achievements_refresh_lock:
            _ra_achievements_refresh_inflight.discard(key)

# BUGFIX/ABSTURZ (Nutzer-Rueckmeldung: "nach dem letzten Update, wenn
# ich jetzt ein Spiel auswaehle und F6 druecke, flieg ich komplett aus
# dem Frontend raus und lande im OSD"): direkte Folge der neuen
# Hardcore/Softcore-Unterscheidung von eben - fetch_ra_game_achievements()
# liefert seitdem pro Erfolg ein 7-Tupel (mit dem neuen "hardcore"-Feld
# am Ende) statt wie vorher ein 6-Tupel. draw_ra_showcase_screen() in
# frontend.py wurde zwar entsprechend angepasst - ABER: RA_ACHIEVEMENTS_
# CACHE_FILE auf der SD-Karte enthaelt bei jedem, der das Frontend
# schon vor diesem Update benutzt hat, noch massenhaft Eintraege im
# ALTEN 6-Tupel-Format. fetch_ra_game_achievements_cached() gibt einen
# vorhandenen Cache-Eintrag laut Stale-while-revalidate-Prinzip IMMER
# sofort zurueck, ganz ohne Formatpruefung - beim ersten F6-Druck auf
# ein Spiel, das schon VOR diesem Update einmal angesehen (oder vom
# Hintergrund-Vorwaermen erfasst) wurde, bekam draw_ra_showcase_screen()
# dadurch ploetzlich 6-elementige statt der jetzt erwarteten
# 7-elementigen Zeilen - "ValueError: not enough values to unpack"
# direkt in der Haupt-Eingabeschleife, dort NICHT abgefangen (siehe
# run()-Aufruf ganz unten in dieser Datei: ein Absturz dort wird
# geloggt und dann bewusst weitergereicht, nicht stillschweigend
# geschluckt) - genau das "raus aus dem Frontend, rein ins OSD".
#
# Fix: jede aus dem Cache gelesene Zeile wird jetzt IMMER auf exakt 7
# Elemente normalisiert - fehlt das "hardcore"-Feld (altes Format),
# wird es mit False ergaenzt (sicherste Annahme: ein vor diesem Update
# gecachter Erfolg zeigt dann uebergangsweise als "[SC]" statt "[HC]",
# bis der naechste Hintergrund-Refresh die echten Daten nachliefert -
# NIEMALS ein Absturz). Kein manuelles Loeschen von
# ra_achievements_cache.json noetig, das raeumt sich von selbst ueber
# das ohnehin bestehende 15-Minuten-TTL/Stale-while-revalidate auf.
def _normalize_achievement_row(row):
    try:
        row = tuple(row)
    except TypeError:
        return None
    if len(row) >= 7:
        return row[:7]
    if len(row) == 6:
        return row + (False,)   # altes Cache-Format ohne Hardcore-Feld
    return None   # unbrauchbare Zeile - auslassen statt abstuerzen

def _normalize_achievements_list(data):
    if data is None:
        return None
    out = []
    for row in data:
        norm = _normalize_achievement_row(row)
        if norm is not None:
            out.append(norm)
    return out

def fetch_ra_game_achievements_cached(game_id, timeout=5.0):
    """Wie fetch_ra_game_achievements_bounded(), aber mit kurzlebigem
    Cache nach dem Stale-while-revalidate-Prinzip (siehe Kommentar
    oben): ein VORHANDENER Cache-Eintrag wird IMMER sofort
    zurueckgegeben, auch wenn er aelter als RA_ACHIEVEMENTS_CACHE_TTL
    ist - in dem Fall wird zusaetzlich, nicht-blockierend, ein
    Hintergrund-Abruf gestartet, der den Cache fuer naechstes Mal
    aktualisiert. Nur wenn NOCH GAR NICHTS im Cache steht (allererster
    Blick auf dieses Spiel), erfolgt ein einmaliger synchroner Abruf.

    Jede zurueckgegebene Zeile laeuft durch _normalize_achievement_row()
    (siehe dortiger Kommentar) - schuetzt gegen Cache-Eintraege in
    einem aelteren Format, egal ob durch dieses oder ein kuenftiges
    Update entstanden."""
    cache = _load_ra_achievements_cache()
    key = str(game_id)
    entry = cache.get(key)
    now = time.time()
    if entry:
        if (now - entry.get("ts", 0)) >= RA_ACHIEVEMENTS_CACHE_TTL:
            threading.Thread(
                target=_refresh_ra_achievements_background,
                args=(game_id,), kwargs={"timeout": timeout},
                daemon=True).start()
        return _normalize_achievements_list(entry.get("data"))
    data = fetch_ra_game_achievements_bounded(game_id, timeout=timeout)
    if data is not None:
        cache[key] = {"ts": now, "data": data}
        _save_ra_achievements_cache(cache)
    return data

# ----------------------------------------------------------------------------
# NAMENS-/SYSTEM-ABGLEICH
#
# RA liefert Spieltitel + Systemnamen, keine Dateipfade - der Abgleich
# mit unserer Bibliothek laeuft ueber einen NORMALISIERTEN Namen
# (Region-/Versionsangaben, Satzzeichen, Gross-/Kleinschreibung werden
# ignoriert), zusaetzlich ueber das System abgesichert. Bewusst
# KONSERVATIV: fehlt fuer unser System eine bekannte RA-Entsprechung,
# wird lieber GAR NICHTS angezeigt als ein potenziell falscher Treffer.
def _ra_normalize_name(name):
    """Normalisiert einen Titel fuer den Abgleich."""
    n = name.lower()
    n = re.sub(r"\([^)]*\)", " ", n)    # (USA), (Europe), (Rev 1) usw.
    n = re.sub(r"\[[^\]]*\]", " ", n)   # [T-En] usw.
    n = re.sub(r"[^a-z0-9 ]", " ", n)   # Satzzeichen -> Leerzeichen
    n = re.sub(r"\s+", " ", n).strip()
    return n

# Bekannte Entsprechungen unserer Systemschluessel zu RA-Konsolennamen.
# BUGFIX (Nutzer-Rueckmeldung, zweite Runde: RA-Fortschritt fehlte bei
# NES/SNES und weiteren Systemen, obwohl dort laengst Achievements
# gesammelt wurden): per Recherche gegen echte RA-API-Beispiele
# bestaetigt, dass RA fuer manche Systeme LAENGERE, kombinierte Namen
# verwendet als hier eingetragen - z.B. "SNES/Super Famicom" statt
# nur "SNES", "Mega Drive" statt "Genesis Mega Drive". Der bisherige
# EXAKTE Abgleich (voller String muss 1:1 passen) schlug dadurch fuer
# genau diese Systeme IMMER fehl, obwohl die Kernbezeichnung eigentlich
# passte. Fix: siehe _ra_console_matches() weiter unten - prueft jetzt,
# ob unsere erwartete Bezeichnung als zusammenhaengende WORTFOLGE in
# RAs tatsaechlichem Namen vorkommt, nicht mehr per exaktem Vergleich.
#
# EHRLICHER HINWEIS bleibt bestehen: auch diese Kurzbezeichnungen sind
# anhand allgemeiner Kenntnis/einzelner API-Beispiele zusammengestellt,
# nicht vollstaendig gegen jedes einzelne System verifiziert - fehlt
# eine Zuordnung oder stimmt sie nicht, fuehrt das zu KEINER Anzeige
# fuer dieses System (sicherer Fehlerfall), nie zu einer falschen.
RA_CONSOLE_MAP = {
    "NES": "nes", "SNES": "snes", "Genesis": "mega drive",
    "GAMEBOY": "game boy", "GBC": "game boy color", "GBA": "game boy advance",
    "PSX": "playstation", "N64": "nintendo 64", "ARCADE": "arcade",
    "SMS": "master system", "TGFX16": "pc engine",
    "NEOGEO": "neo geo", "MegaCD": "sega cd", "Saturn": "saturn",
}

def _ra_console_matches(expected, ra_console_normalized):
    """Prueft, ob die erwartete (bereits normalisierte, ggf. mehrteilige)
    Systembezeichnung als ZUSAMMENHAENGENDE Wortfolge in RAs
    tatsaechlichem, normalisierten Konsolennamen vorkommt - z.B.
    "snes" in "snes super famicom" (Treffer), aber NICHT "nes" in
    "snes super famicom" (kein Treffer trotz Teilstring-Uebereinstimmung
    auf Zeichenebene) - reiner Wortgrenzen-Vergleich, sonst wuerde NES
    faelschlich jedes SNES-Spiel treffen."""
    exp_words = expected.split()
    ra_words = ra_console_normalized.split()
    n = len(exp_words)
    if n == 0 or n > len(ra_words):
        return False
    for i in range(len(ra_words) - n + 1):
        if ra_words[i:i + n] == exp_words:
            return True
    return False

RA_PROGRESS_SUMMARY_FILE = "/media/fat/frontend/ra_progress_summary.json"

def build_ra_lookup(ra_entries):
    """Baut aus der RA-Fortschrittsliste ein Nachschlage-Woerterbuch:
    normalisierter_titel -> Liste von (normalisiertes_system, erreicht,
    moeglich, game_id)-Tupeln. Mehrere Eintraege pro Titel sind normal
    (dasselbe Spiel kann auf mehreren Konsolen erschienen sein) - die
    eigentliche System-Auswahl passiert erst in lookup_ra_progress().

    NEU (Nutzerwunsch: 'Perfektionist'-Erfolg fuer 100% RA-Abschluss):
    persistiert nebenbei eine winzige Zusammenfassung (nur ein
    Wahrheitswert), damit auch reine Anzeige-Funktionen ohne Zugriff
    auf die lebende self._ra_lookup (z.B. get_hidden_achievements(),
    ueberall als einfache Modulfunktion aufgerufen) wissen, ob
    mindestens ein Spiel zu 100% abgeschlossen ist - OHNE selbst RA
    abfragen zu muessen. Nur geschrieben, wenn tatsaechlich Eintraege
    da waren (ein leerer/fehlgeschlagener Abruf darf einen bereits
    bekannten 100%-Abschluss nicht faelschlich wieder loeschen)."""
    lookup = {}
    any_100pct = False
    for title, system, earned, total, game_id in ra_entries or []:
        key = _ra_normalize_name(title)
        lookup.setdefault(key, []).append(
            (_ra_normalize_name(system), earned, total, game_id))
        if total and total > 0 and earned >= total:
            any_100pct = True
    if ra_entries:
        _save_json_dict(RA_PROGRESS_SUMMARY_FILE,
                        {"any_100pct": any_100pct, "ts": time.time()})
    return lookup

def lookup_ra_progress(lookup, our_name, our_syskey):
    """Sucht den RA-Fortschritt fuer ein Spiel aus unserer Bibliothek.
    Liefert (erreicht, moeglich) oder None, wenn kein Treffer - auch
    wenn fuer our_syskey keine bekannte RA-Entsprechung existiert
    (bewusst KEIN Rateversuch). Bei mehreren zum System passenden
    Eintraegen (sollte selten vorkommen) gewinnt der mit den meisten
    erreichten Achievements.

    UNVERAENDERTE Rueckgabe (nur (erreicht, moeglich) oder None) trotz
    jetzt zusaetzlich gespeicherter GameID - keine bestehende
    Aufrufstelle soll sich anpassen muessen. Fuer die GameID selbst
    siehe die separate lookup_ra_game_id()."""
    best = _lookup_ra_candidate(lookup, our_name, our_syskey)
    return (best[0], best[1]) if best else None

def lookup_ra_game_id(lookup, our_name, our_syskey):
    """Wie lookup_ra_progress(), liefert aber die RA-GameID des
    Treffers (fuer die Erfolgsdetails, siehe fetch_ra_game_achievements())
    statt des Fortschritts - oder None, wenn kein Treffer oder keine
    GameID bekannt ist (z.B. bei aelteren zwischengespeicherten Daten
    ohne dieses Feld)."""
    best = _lookup_ra_candidate(lookup, our_name, our_syskey)
    return best[2] if best else None

def _lookup_ra_candidate(lookup, our_name, our_syskey):
    """Gemeinsamer Kern von lookup_ra_progress()/lookup_ra_game_id():
    liefert (erreicht, moeglich, game_id) des besten Treffers oder
    None."""
    expected = RA_CONSOLE_MAP.get(our_syskey)
    if not expected:
        return None
    candidates = lookup.get(_ra_normalize_name(our_name))
    if not candidates:
        return None
    best = None
    for ra_system, earned, total, game_id in candidates:
        if _ra_console_matches(expected, ra_system):
            if best is None or earned > best[0]:
                best = (earned, total, game_id)
    return best

