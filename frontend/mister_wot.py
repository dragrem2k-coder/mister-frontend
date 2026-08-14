"""mister_wot.py - "Wonne oder Tonne" (Dennsens Bewertungs-Format): zieht
zufaellig ein noch nicht gespieltes NES/SNES-Spiel aus einer CSV-Liste,
findet die passende ROM-Datei (US-Version bevorzugt fuer RetroAchievements),
liest die RA_ID mit und markiert gestartete Spiele dauerhaft als gespielt.

Ausgelagert aus frontend.py: reine Logik ohne Framebuffer, eigenstaendig
testbar. Die ANZEIGE + der Start (draw_wot_screen, inkl. RA-Core-Start)
bleiben in frontend.py. Das Frontend ruft einmalig configure(...) auf."""

import re
import os
import csv
import json
import random
import difflib
import hashlib
import unicodedata

# --- Vom Frontend injizierte Abhaengigkeiten (via configure) ---
GAME_SYSTEMS = []                    # System-Definitionen (disp, syskey, folders, rbf, extmap)
_games_bases_getter = lambda: []     # liefert die AKTUELLEN ROM-Basispfade

def _default_log(msg):
    try:
        print(msg)
    except Exception:
        pass

LOG = _default_log

def configure(game_systems, games_bases_getter, log=None):
    """EINMAL vom Frontend beim Start aufrufen. game_systems: System-
    Definitionsliste; games_bases_getter: Funktion, die die AKTUELLEN ROM-
    Basispfade liefert (Getter, weil GAMES_BASES nach dem NAS-Warten neu
    ermittelt wird); log: die LOG-Funktion des Frontends."""
    global GAME_SYSTEMS, _games_bases_getter, LOG
    GAME_SYSTEMS = game_systems
    _games_bases_getter = games_bases_getter
    if log is not None:
        LOG = log


# ============================================================================
# Kernlogik (ausgelagert aus frontend.py; nur GAMES_BASES -> _games_bases_getter())
# ============================================================================
WOT_CSV_FILE = "/media/fat/frontend/wot_games.csv"
WOT_ALIASES_FILE = "/media/fat/frontend/wot_aliases.json"
WOT_MATCH_CACHE_FILE = "/media/fat/frontend/wot_rom_cache.json"
WOT_SYSTEMS = ["NES", "SNES"]
WOT_MATCH_THRESHOLD = 0.72   # difflib-Aehnlichkeit, ab der ein ROM-Treffer akzeptiert wird
WOT_TAG_PATTERN = re.compile(r"[\(\[][^\)\]]*[\)\]]")
WOT_ALL_ARTICLES = ["Das", "Die", "Der", "The"]

def _wot_strip_accents(s):
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c))

def wot_normalize_title(raw):
    """Bringt CSV-Anzeigename oder ROM-Dateiname auf eine vergleichbare
    Form: Klammer-Tags (Region/Sprache/Rev) weg, Artikel-Inversion
    aufgeloest ("X, The" <-> "The X", genauso De/Die/Der), Satzzeichen/
    Mehrfach-Leerzeichen normalisiert, Kleinschreibung, keine Akzente."""
    s = raw.strip()
    s = WOT_TAG_PATTERN.sub("", s)
    s = s.strip()
    m = re.match(r"^(.*),\s*(Das|Die|Der|The)$", s, flags=re.IGNORECASE)
    if m:
        s = "%s %s" % (m.group(2), m.group(1))
    s = _wot_strip_accents(s)
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    for art in WOT_ALL_ARTICLES:
        prefix = art.lower() + " "
        if s.startswith(prefix):
            s = s[len(prefix):]
            break
    return s

def wot_load_pool():
    """Laedt WOT_CSV_FILE, liefert die Liste noch nicht gespielter Spiele
    als (system, title, genre)-Tupel. Regel: Spalte "Erstes Mal" leer ->
    noch nicht gespielt -> Teil des Pools; befuellt (JA/NEIN) -> schon
    gespielt -> ausgeschlossen."""
    pool = []
    try:
        with open(WOT_CSV_FILE, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                system = (row.get("Konsole") or "").strip()
                if system not in WOT_SYSTEMS:
                    continue
                if (row.get("Erstes Mal") or "").strip() != "":
                    continue   # schon bewertet -> raus
                if (row.get("Gespielt") or "").strip().upper() == "JA":
                    continue   # vom Frontend als gespielt markiert -> raus
                title = (row.get("Spiel") or "").strip()
                if not title:
                    continue
                genre = (row.get("Genre") or "").strip()
                ra_id = (row.get("RA_ID") or "").strip()          # NEU
                pool.append((system, title, genre, ra_id))        # NEU: 4-Tupel
    except (OSError, csv.Error):
        return []
    return pool

def wot_load_aliases():
    """Optionale manuelle Uebersetzungstabelle CSV-Titel -> ROM-Dateiname
    (fuer Faelle wie 'Action in New York' -> 'S.C.A.T. - Special
    Cybernetic Attack Team (USA)', die per Fuzzy-Matching nicht
    zuverlaessig zu finden sind)."""
    try:
        with open(WOT_ALIASES_FILE, encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}

def wot_list_rom_files(syskey):
    """ROM-Dateien fuer ein System - nutzt dieselbe GAMES_BASES-
    Mehrfachpfad-Erkennung wie der normale Scan (nicht nur einen
    einzelnen fest vorgegebenen Ordner, wie im urspruenglichen
    Vorschlag), inkl. Unterordnern (os.walk, gleiche Logik wie
    _scan_folder_tree())."""
    sysdef = next((s for s in GAME_SYSTEMS if s[1] == syskey), None)
    if not sysdef:
        return []
    _disp, _sk, folders, _rbf, extmap = sysdef
    exts = tuple(extmap.keys())
    files = []
    seen_roots = set()
    for base in _games_bases_getter():
        for folder in folders:
            root = os.path.join(base, folder)
            try:
                real = os.path.realpath(root)
            except OSError:
                continue
            if not os.path.isdir(root) or real in seen_roots:
                continue
            seen_roots.add(real)
            for dirpath, _dirnames, filenames in os.walk(root):
                for fn in filenames:
                    if os.path.splitext(fn)[1].lower() in exts:
                        files.append(os.path.join(dirpath, fn))
    return files

def _wot_region_rank(rom):
    """Kleiner = bevorzugt. US zuerst (fuer RetroAchievements zaehlt i.d.R.
    die US-Version), dann World, Europe, Japan, Rest. So wird bei mehreren
    Versionen gezielt die US-Version gewaehlt statt der zufaellig ersten
    in der Ordner-Reihenfolge."""
    n = os.path.basename(rom).lower()
    if "usa" in n or re.search(r"\(u[,)]", n):
        return 0
    if "world" in n:
        return 1
    if "europe" in n or re.search(r"\(e[,)]", n):
        return 2
    if "japan" in n or re.search(r"\(j[,)]", n):
        return 3
    return 4

def wot_mark_played(system, title):
    """Markiert ein Spiel in der WoT-CSV als gespielt (eigene Spalte
    'Gespielt' = JA), damit es nicht mehr gezogen wird. Legt EINMALIG ein
    Backup (.bak) an, laesst die Bewertungsspalte 'Erstes Mal' unangetastet,
    schreibt alle anderen Zeilen/Spalten unveraendert + atomar zurueck.
    Fehler werden nur geloggt, nie geworfen - ein CSV-Problem darf den
    Spielstart nicht stoeren."""
    try:
        with open(WOT_CSV_FILE, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            fields = list(reader.fieldnames or [])
            rows = list(reader)
    except (OSError, csv.Error) as e:
        LOG("wot_mark_played: CSV nicht lesbar: %s" % e)
        return
    if "Gespielt" not in fields:
        fields.append("Gespielt")
    changed = False
    for row in rows:
        if ((row.get("Konsole") or "").strip() == system and
                (row.get("Spiel") or "").strip() == title):
            if (row.get("Gespielt") or "").strip().upper() != "JA":
                row["Gespielt"] = "JA"
                changed = True
            break
    if not changed:
        return
    try:
        if not os.path.exists(WOT_CSV_FILE + ".bak"):
            with open(WOT_CSV_FILE, "rb") as src, open(WOT_CSV_FILE + ".bak", "wb") as dst:
                dst.write(src.read())
    except OSError as e:
        LOG("wot_mark_played: Backup fehlgeschlagen: %s" % e)
    try:
        tmp = WOT_CSV_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            for row in rows:
                w.writerow({k: (row.get(k) or "") for k in fields})
        os.replace(tmp, WOT_CSV_FILE)
        LOG("wot_mark_played: '%s' (%s) als gespielt markiert" % (title, system))
    except OSError as e:
        LOG("wot_mark_played: Schreiben fehlgeschlagen: %s" % e)

# Prozessweite Caches. Der teure Teil ist NICHT das Zufallsziehen, sondern
# (1) das Einlesen ALLER ROM-Dateien eines Systems von SD/USB/NAS (os.walk)
# samt Normalisieren, (2) die difflib-Fuzzy-Suche ueber die komplette ROM-
# Liste bei jedem Titel ohne exakten Treffer, und (3) - der eigentliche
# Zeitfresser bei einer grossen CSV mit wenigen vorhandenen ROMs - das
# wiederholte, meist erfolglose Zufallsziehen. Diese Caches halten die
# Ergebnisse prozessweit fest: jedes System wird pro Sitzung HOECHSTENS
# EINMAL gescannt, jeder Titel HOECHSTENS EINMAL aufgeloest, und die
# spielbare Gesamtliste HOECHSTENS EINMAL gebaut.
_INDEX_CACHE = {}       # syskey -> (exact_map, norm_pairs)
_MATCH_CACHE = {}       # (syskey, csv_title) -> (rom_path | None, score)
_PLAYABLE_CACHE = {}    # pool-signature -> [ (system,title,genre,ra_id,rom,score), ... ]
_DISK_MATCH_LOADED = False   # Platten-Cache (Titel->ROM) pro Prozess nur einmal laden

def wot_reset_index_cache():
    """Verwirft alle prozessweiten Caches UND den Platten-Cache - aufrufen,
    wenn sich der ROM-Bestand geaendert hat (neue/entfernte ROMs, NAS neu
    eingehaengt). Der naechste Aufbau scannt dann frisch und schreibt den
    Platten-Cache neu."""
    global _DISK_MATCH_LOADED
    _INDEX_CACHE.clear()
    _MATCH_CACHE.clear()
    _PLAYABLE_CACHE.clear()
    _DISK_MATCH_LOADED = False
    try:
        os.remove(WOT_MATCH_CACHE_FILE)
    except OSError:
        pass

def wot_build_index(syskey, force=False):
    """Baut den ROM-Index eines Systems: exakte normalisierte Zuordnung
    (Sofort-Treffer, bei mehreren Versionen mit US-Vorzug) + vor-
    normalisierte Paare fuer die difflib-Suche (ebenfalls US zuerst). Das
    Ergebnis wird prozessweit gecacht (_INDEX_CACHE) - der teure Ordner-
    Scan laeuft pro System nur EINMAL pro Sitzung. force=True erzwingt einen
    Neuaufbau."""
    if not force and syskey in _INDEX_CACHE:
        return _INDEX_CACHE[syskey]
    best = {}     # norm -> (region_rank, rom)
    pairs = []
    for rom in wot_list_rom_files(syskey):
        stem = os.path.splitext(os.path.basename(rom))[0]
        n = wot_normalize_title(stem)
        pairs.append((n, rom))
        rank = _wot_region_rank(rom)
        cur = best.get(n)
        if cur is None or rank < cur[0]:
            best[n] = (rank, rom)
    exact = {n: rm for n, (rk, rm) in best.items()}
    pairs.sort(key=lambda pr: _wot_region_rank(pr[1]))   # Fuzzy-Ties: US zuerst
    _INDEX_CACHE[syskey] = (exact, pairs)
    return _INDEX_CACHE[syskey]

def wot_prewarm_indexes(pool):
    """Baut den ROM-Index fuer ALLE im Pool vorkommenden Systeme vor (nutzt
    _INDEX_CACHE -> nur beim allerersten Mal teuer)."""
    for syskey in dict.fromkeys(g[0] for g in pool):
        wot_build_index(syskey)

def wot_find_rom(title, index, aliases):
    """index = (exact_map, norm_pairs) aus wot_build_index(). Exakte
    (normalisierte) Treffer sofort, difflib nur als Rueckfall."""
    exact, pairs = index
    if title in aliases:
        rom = exact.get(wot_normalize_title(aliases[title]))
        if rom is not None:
            return rom, 1.0
    target = wot_normalize_title(title)
    rom = exact.get(target)
    if rom is not None:
        return rom, 1.0
    if not pairs:
        return None, 0.0
    # EINE SequenceMatcher-Instanz, target als (haeufige) seq2 - deren Index
    # wird einmal berechnet und wiederverwendet. Pro Kandidat nur set_seq1 +
    # billige obere Schranken (real_quick_ratio/quick_ratio) VOR der teuren
    # ratio(); uebersprungen werden nur Kandidaten, die den bisher Besten
    # ohnehin nicht schlagen koennen -> gleiches Ergebnis, deutlich schneller.
    sm = difflib.SequenceMatcher()
    sm.set_seq2(target)
    best_rom, best_score = None, 0.0
    for norm, rom in pairs:
        sm.set_seq1(norm)
        if sm.real_quick_ratio() <= best_score or sm.quick_ratio() <= best_score:
            continue
        score = sm.ratio()
        if score > best_score:
            best_rom, best_score = rom, score
    if best_score >= WOT_MATCH_THRESHOLD:
        return best_rom, best_score
    return None, best_score

def wot_draw_with_rom(pool, aliases, max_attempts=20, index_cache=None, exclude=None):
    """Zieht Spiele, bis eins mit passendem ROM gefunden wird (kein
    Treffer -> ueberspringen + neu ziehen, mit Log-Warnung statt
    Fehlerabbruch), oder gibt None nach max_attempts auf (Pool
    erschoepft / keine passenden ROMs gefunden). Liefert
    (system, title, genre, ra_id, rom_path, score) oder None."""
    tried = set(exclude) if exclude else set()
    if index_cache is None:
        index_cache = {}
    candidates = list(pool)
    for _ in range(max_attempts):
        remaining = [g for g in candidates if g[1] not in tried]
        if not remaining:
            return None
        system, title, genre, ra_id = random.choice(remaining)   # NEU: ra_id
        tried.add(title)
        if system not in index_cache:
            index_cache[system] = wot_build_index(system)   # prozessweit gecacht
        mkey = (system, title)
        if mkey in _MATCH_CACHE:
            rom, score = _MATCH_CACHE[mkey]                 # difflib nur EINMAL je Titel
        else:
            rom, score = wot_find_rom(title, index_cache[system], aliases)
            _MATCH_CACHE[mkey] = (rom, score)
        if rom is not None:
            return system, title, genre, ra_id, rom, score        # NEU: ra_id
        LOG("Wonne oder Tonne: kein ROM-Treffer fuer '%s' (Score %.2f) - neu ziehen"
            % (title, score))
    return None
def wot_draw_multiple(pool, aliases, count=3, max_attempts=20, index_cache=None, exclude=None):
    """Zieht bis zu `count` VERSCHIEDENE Spiele mit passender ROM-Datei -
    fuer die Auswahl "nach 'Spiel ziehen' drei zufaellige Spiele zur Wahl".
    Bewusst quer ueber ALLE Systeme/Genres im uebergebenen Pool; wer
    einschraenken will, uebergibt einfach einen bereits gefilterten Pool
    (diese Funktion filtert nicht selbst - die Wahl der Grundmenge bleibt
    beim Aufrufer).

    Baut direkt auf wot_draw_with_rom() auf: jeder gefundene Titel wandert
    in die Ausschlussmenge, damit kein Spiel doppelt erscheint; der
    index_cache (ROM-Index je System) wird ueber alle Ziehungen hinweg
    weitergereicht, es wird also nicht mehrfach gescannt/normalisiert.

    Liefert eine Liste von (system, title, genre, ra_id, rom_path, score)-
    Tupeln mit 0..count Eintraegen - bei kleinem Pool (oder wenig ROM-
    Treffern) koennen es weniger als count sein, nie ein Fehler, nie
    Doppelte.

    `exclude` (optional): Titel, die von vornherein nicht gezogen werden
    sollen - z.B. die zuletzt angebotenen drei, damit ein erneutes
    "Neu ziehen" nicht dieselbe Auswahl bringt."""
    if index_cache is None:
        index_cache = {}
    wot_prewarm_indexes(pool)
    tried = set(exclude) if exclude else set()
    picked = []
    for _ in range(count):
        result = wot_draw_with_rom(pool, aliases, max_attempts=max_attempts,
                                   index_cache=index_cache, exclude=tried)
        if result is None:
            break   # Pool erschoepft / keine weiteren ROM-Treffer
        picked.append(result)
        tried.add(result[1])   # result[1] = title -> kein Doppel bei der naechsten Ziehung
    return picked


def _wot_match_fingerprint(aliases):
    """Fingerprint der matching-relevanten Konfiguration (Aliases, Schwelle,
    Systeme). Aendert sich einer dieser Werte, wird der Platten-Cache
    verworfen. BEWUSST NICHT vom ROM-Bestand abhaengig - den zu erfassen
    wuerde genau den teuren Scan erfordern, den der Cache vermeiden soll;
    ROM-Aenderungen deckt die Existenzpruefung + wot_reset_index_cache ab."""
    payload = json.dumps({"v": 1, "aliases": aliases,
                          "threshold": WOT_MATCH_THRESHOLD, "systems": WOT_SYSTEMS},
                         sort_keys=True, ensure_ascii=False)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()

def _wot_load_disk_match_cache(aliases):
    """Laedt die Titel->ROM-Zuordnungen EINMAL pro Prozess aus dem Platten-
    Cache in _MATCH_CACHE - aber nur, wenn der Fingerprint passt. Damit
    entfaellt nach einem Neustart/Reboot der komplette Scan + difflib."""
    global _DISK_MATCH_LOADED
    if _DISK_MATCH_LOADED:
        return
    _DISK_MATCH_LOADED = True
    try:
        with open(WOT_MATCH_CACHE_FILE, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return
    if not isinstance(data, dict) or data.get("fingerprint") != _wot_match_fingerprint(aliases):
        return   # Aliases/Schwelle/Systeme geaendert -> Platten-Cache ignorieren
    loaded = 0
    for entry in data.get("matches", []):
        try:
            system, title, rom, score = entry
        except (ValueError, TypeError):
            continue
        _MATCH_CACHE[(system, title)] = (rom, score)
        loaded += 1
    LOG("Wonne oder Tonne: %d ROM-Zuordnungen aus Platten-Cache geladen" % loaded)

def _wot_save_disk_match_cache(aliases):
    """Schreibt _MATCH_CACHE atomar auf Platte (Fehler werden nur geloggt,
    nie geworfen - ein Cache-Problem darf WoT nicht stoeren)."""
    matches = [[sy, ti, rom, score] for (sy, ti), (rom, score) in _MATCH_CACHE.items()]
    data = {"version": 1, "fingerprint": _wot_match_fingerprint(aliases), "matches": matches}
    try:
        tmp = WOT_MATCH_CACHE_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        os.replace(tmp, WOT_MATCH_CACHE_FILE)
        LOG("Wonne oder Tonne: %d ROM-Zuordnungen in Platten-Cache gespeichert" % len(matches))
    except OSError as e:
        LOG("Wonne oder Tonne: Platten-Cache schreiben fehlgeschlagen: %s" % e)

def _wot_pool_signature(pool):
    """Stabile Signatur der Grundmenge (System+Titel) - der spielbare-Liste-
    Cache baut damit automatisch neu, wenn sich die CSV/der Pool aendert."""
    return (len(pool), tuple(sorted((g[0], g[1]) for g in pool)))

def wot_build_playable_pool(pool, aliases, index_cache=None, progress_cb=None, force=False):
    """Loest EINMAL fuer den KOMPLETTEN Pool die ROM-Zuordnung auf und liefert
    die Liste der tatsaechlich spielbaren Spiele als
    (system, title, genre, ra_id, rom_path, score)-Tupel.

    Hintergrund: die CSV listet i.d.R. viel mehr Spiele als ROMs vorhanden
    sind. Zufaelliges Ziehen aus der ganzen Liste traf dann meist "kein ROM"
    (langsam wegen difflib je Fehlversuch) und hatte nach wenigen Zuegen den
    kleinen spielbaren Rest verbraucht -> Wiederholungen. Mit der fertigen
    spielbaren Liste ist Ziehen/Neu ziehen sofort UND wiederholungsfrei.

    Ergebnis wird prozessweit gecacht (_PLAYABLE_CACHE, Schluessel = Pool-
    Signatur) - der (einmalige) Aufbau nutzt _INDEX_CACHE/_MATCH_CACHE, ist
    also beim zweiten Aufruf sofort da. progress_cb(done, total) optional
    fuer eine Fortschrittsanzeige waehrend des einmaligen Aufbaus."""
    if index_cache is None:
        index_cache = {}
    sig = _wot_pool_signature(pool)
    if not force and sig in _PLAYABLE_CACHE:
        return _PLAYABLE_CACHE[sig]

    # Grundmenge deduplizieren (doppelte CSV-Zeilen desselben Spiels)
    seen = set()
    items = []
    for (system, title, genre, ra_id) in pool:
        k = (system, title)
        if k in seen:
            continue
        seen.add(k)
        items.append((system, title, genre, ra_id))

    if force:
        # Kompletter Neuaufbau: Index + gemerkte Matches der Pool-Systeme
        # verwerfen, damit frisch gescannt/aufgeloest wird.
        for sk in {it[0] for it in items}:
            _INDEX_CACHE.pop(sk, None)
        for it in items:
            _MATCH_CACHE.pop((it[0], it[1]), None)
    else:
        # Titel->ROM-Zuordnungen vom Platten-Cache uebernehmen (falls gueltig)
        # -> nach Reboot kein Scan/difflib, sofern alle Titel schon bekannt.
        _wot_load_disk_match_cache(aliases)

    # Nur die noch NICHT aufgeloesten Titel muessen gescannt/ge-difflib-t
    # werden - der einzige teure Teil (nach Erst-Bau / Platten-Cache leer).
    misses = [it for it in items if (it[0], it[1]) not in _MATCH_CACHE]
    if misses:
        for sk in dict.fromkeys(m[0] for m in misses):
            wot_build_index(sk)   # nur die tatsaechlich benoetigten Systeme scannen
        total = len(misses)
        for j, (system, title, genre, ra_id) in enumerate(misses):
            if progress_cb is not None and (j % 20 == 0 or j == total - 1):
                progress_cb(j + 1, total)
            rom, score = wot_find_rom(title, _INDEX_CACHE[system], aliases)
            _MATCH_CACHE[(system, title)] = (rom, score)
        _wot_save_disk_match_cache(aliases)   # nur wenn wirklich neu aufgeloest wurde

    # Spielbare Liste aus dem (jetzt vollstaendigen) Match-Cache bauen.
    # os.path.exists filtert inzwischen entfernte ROMs heraus (self-healing);
    # bei kleinem spielbarem Bestand sind das nur wenige, billige stat-Aufrufe.
    playable = []
    for (system, title, genre, ra_id) in items:
        rom, score = _MATCH_CACHE.get((system, title), (None, 0.0))
        if rom is not None and os.path.exists(rom):
            playable.append((system, title, genre, ra_id, rom, score))
    _PLAYABLE_CACHE[sig] = playable
    LOG("Wonne oder Tonne: spielbare Liste - %d von %d Titeln spielbar (%d neu aufgeloest)"
        % (len(playable), len(items), len(misses)))
    return playable