"""mister_wot.py - "Zufalls-Zock" (Spieleroulette): schlaegt dem
Nutzer zufaellig Spiele aus ALLEN Systemen vor, zu denen er ROMs hat, und
schliesst bereits gespielte Spiele aus.

Umbau gegenueber der CSV-Version:
  - Quelle der Spiele sind jetzt die TATSAECHLICH VORHANDENEN ROM-Dateien
    (Katalog quer ueber alle Systeme aus GAME_SYSTEMS), NICHT mehr eine
    CSV-Liste. Damit ist das Feature auch ohne CSV voll sichtbar/nutzbar.
  - "Bereits gespielt" liegt in einer JSON-Datenbank (WOT_PLAYED_FILE).
    Gespielte Spiele tauchen nicht mehr im Roulette auf.
  - Der RetroAchievements-Ansatz bleibt: bei mehreren Regionen wird die
    US-Version bevorzugt (RA-Hashes zaehlen i.d.R. die US-Version). Die
    RA-ID kommt - sofern vorhanden - aus der OPTIONALEN CSV-Anreicherung.
  - Kein Fuzzy-Matching (difflib) mehr: da der ROM selbst die Quelle ist,
    ist jeder Katalog-/Pool-Eintrag per Definition spielbar. Das war der
    langsame Teil der alten Version und faellt komplett weg.

Ausgelagert aus frontend.py: reine Logik ohne Framebuffer, eigenstaendig
testbar (siehe __main__). ANZEIGE + Start (draw_wot_screen, inkl. RA-Core-
Start) bleiben in frontend.py. Das Frontend ruft einmalig configure(...) auf.

Rueckgabeform der Ziehungen bleibt bewusst gleich wie bisher:
  (system, title, genre, ra_id, rom_path, score)
so dass die Anzeige in draw_wot_screen praktisch unveraendert bleibt
(score ist jetzt konstant 1.0)."""

import re
import os
import csv
import json
import time
import random
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
# Dateipfade + Konfiguration
# ============================================================================
WOT_PLAYED_FILE = "/media/fat/frontend/wot_played.json"          # gespielt-DB (Wahrheit)
WOT_CATALOG_CACHE_FILE = "/media/fat/frontend/wot_catalog_cache.json"  # Katalog-Platten-Cache
WOT_CSV_FILE = "/media/fat/frontend/wot_games.csv"               # OPTIONAL: Anreicherung
WOT_ALIASES_FILE = "/media/fat/frontend/wot_aliases.json"        # OPTIONAL: Alias-Tabelle

# Systemauswahl fuers Roulette:
#   None  -> ALLE Systeme aus GAME_SYSTEMS, zu denen ROMs vorhanden sind.
#   Liste -> nur diese syskeys (z.B. ["NES","SNES","MegaDrive"]).
WOT_SYSTEMS = None

WOT_TAG_PATTERN = re.compile(r"[\(\[][^\)\]]*[\)\]]")
WOT_ALL_ARTICLES = ["Das", "Die", "Der", "The"]
WOT_ARTICLE_INVERT = re.compile(r"^(.*?),\s*(Das|Die|Der|The)(\b.*)$", flags=re.IGNORECASE)


# ============================================================================
# Titel-Normalisierung (fuer Vergleich/Dedup) + Anzeige-Aufhuebschung
# ============================================================================
def _wot_strip_accents(s):
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c))

def wot_normalize_title(raw):
    """Bringt CSV-Anzeigename oder ROM-Dateiname auf eine vergleichbare
    Form (fuer Dedup + gespielt-Abgleich): Klammer-Tags weg, Artikel-
    Inversion aufgeloest ("X, The" -> "The X"), Satzzeichen/Mehrfach-
    Leerzeichen normalisiert, Kleinschreibung, keine Akzente, fuehrender
    Artikel entfernt. NUR fuer den Vergleich - nicht fuer die Anzeige."""
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

def wot_pretty_title(name):
    """Erzeugt aus einem ROM-Dateinamen (oder Pfad) einen anzeigetauglichen
    Titel: Endung + Klammer-Tags (Region/Sprache/Rev) weg, Artikel-Inversion
    aufgeloest ("Zelda, The - ..." -> "The Zelda - ..."), Original-Gross-/
    Kleinschreibung bleibt erhalten. Faellt auf den rohen Stem zurueck, falls
    nach dem Saeubern nichts uebrig bliebe."""
    stem = os.path.splitext(os.path.basename(name))[0]
    s = WOT_TAG_PATTERN.sub("", stem)
    s = re.sub(r"\s{2,}", " ", s).strip(" -_.\t")
    m = WOT_ARTICLE_INVERT.match(s)
    if m:
        s = ("%s %s%s" % (m.group(2), m.group(1), m.group(3)))
    s = re.sub(r"\s{2,}", " ", s).strip()
    return s or stem.strip()


# ============================================================================
# ROM-Scan (unveraendert: gleiche Mehrfachpfad-/Unterordner-Logik wie der Scan)
# ============================================================================
def wot_list_rom_files(syskey):
    """ROM-Dateien fuer ein System - nutzt dieselbe GAMES_BASES-Mehrfachpfad-
    Erkennung wie der normale Scan, inkl. Unterordnern (os.walk)."""
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
    Versionen gezielt die US-Version gewaehlt."""
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


# ============================================================================
# Optionale Anreicherung: Aliases + CSV (Genre / RA-ID)
# ============================================================================
def wot_load_aliases():
    """OPTIONALE manuelle Uebersetzungstabelle CSV-Titel -> ROM-Dateiname
    (fuer Faelle, die per Normalisierung nicht zusammenfinden). Fehlt die
    Datei, wird einfach nichts angereichert."""
    try:
        with open(WOT_ALIASES_FILE, encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}

def wot_load_csv_enrichment(aliases=None):
    """OPTIONAL: liest wot_games.csv (falls vorhanden) und liefert
    {(system, norm_title): (genre, ra_id)} zur Anreicherung der aus ROMs
    gebauten Katalog-Eintraege. Fehlt die CSV, ist das Roulette voll
    funktionsfaehig - Genre/RA-ID bleiben dann eben leer.

    Der Abgleich laeuft ueber die normalisierte Form (gleiche Normalisierung
    wie beim ROM-Namen -> exakter Treffer trotz Region-Tags). Fuer Alias-
    Faelle wird zusaetzlich unter der normalisierten Ziel-ROM-Form abgelegt."""
    aliases = aliases or {}
    enr = {}
    try:
        with open(WOT_CSV_FILE, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                system = (row.get("Konsole") or "").strip()
                title = (row.get("Spiel") or "").strip()
                if not system or not title:
                    continue
                genre = (row.get("Genre") or "").strip()
                ra_id = (row.get("RA_ID") or "").strip()
                enr[(system, wot_normalize_title(title))] = (genre, ra_id)
                if title in aliases:
                    enr[(system, wot_normalize_title(aliases[title]))] = (genre, ra_id)
    except (OSError, csv.Error):
        return {}
    return enr


# ============================================================================
# gespielt-Datenbank (JSON) - die einzige Wahrheit ueber "schon gespielt"
# ============================================================================
def wot_load_played():
    """Laedt die gespielt-DB. Liefert (played_set, raw_list):
      played_set = Menge {(system, norm_title)} zum schnellen Ausschluss,
      raw_list   = Original-Eintraege (Dicts) zum Zurueckschreiben.
    Fehlt/defekt die Datei, sind beide leer -> Roulette bietet alles an."""
    try:
        with open(WOT_PLAYED_FILE, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return set(), []
    raw = data.get("played", []) if isinstance(data, dict) else []
    if not isinstance(raw, list):
        return set(), []
    played = set()
    clean = []
    for e in raw:
        if not isinstance(e, dict):
            continue
        system = (e.get("system") or "").strip()
        title = (e.get("title") or "").strip()
        norm = (e.get("norm") or "").strip() or wot_normalize_title(title)
        if not system or not norm:
            continue
        played.add((system, norm))
        clean.append(e)
    return played, clean

def wot_save_played(raw_list):
    """Schreibt die gespielt-DB atomar (indent=2, damit sie von Hand lesbar/
    editierbar bleibt). Fehler werden nur geloggt, nie geworfen."""
    data = {"version": 1, "played": raw_list}
    try:
        tmp = WOT_PLAYED_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, WOT_PLAYED_FILE)
        return True
    except OSError as e:
        LOG("Zufalls-Zock: gespielt-DB schreiben fehlgeschlagen: %s" % e)
        return False

def wot_is_played(system, title, played_set=None):
    """True, wenn (system, title) bereits in der gespielt-DB steht."""
    if played_set is None:
        played_set, _ = wot_load_played()
    return (system, wot_normalize_title(title)) in played_set

def wot_mark_played(system, title, rom=None, ra_id=None):
    """Traegt ein Spiel in die gespielt-DB ein, damit es nicht mehr im
    Roulette auftaucht. Idempotent (kein Doppel-Eintrag), atomarer Write,
    Fehler werden nur geloggt - ein DB-Problem darf den Spielstart nicht
    stoeren. rom/ra_id sind optional (nur zur Dokumentation im Eintrag)."""
    system = (system or "").strip()
    title = (title or "").strip()
    if not system or not title:
        return
    norm = wot_normalize_title(title)
    played, raw = wot_load_played()
    if (system, norm) in played:
        return
    entry = {"system": system, "title": title, "norm": norm,
             "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}
    if rom:
        entry["rom"] = rom
    if ra_id:
        entry["ra_id"] = ra_id
    raw.append(entry)
    if wot_save_played(raw):
        LOG("Zufalls-Zock: '%s' (%s) als gespielt markiert" % (title, system))

def wot_unmark_played(system, title):
    """Nimmt ein Spiel wieder aus der gespielt-DB heraus (fuer den Fall, dass
    es faelschlich markiert wurde). Liefert True, wenn etwas entfernt wurde."""
    system = (system or "").strip()
    norm = wot_normalize_title(title or "")
    _played, raw = wot_load_played()
    new_raw = [e for e in raw
               if not ((e.get("system") or "").strip() == system
                       and ((e.get("norm") or "").strip()
                            or wot_normalize_title(e.get("title") or "")) == norm)]
    if len(new_raw) == len(raw):
        return False
    wot_save_played(new_raw)
    LOG("Zufalls-Zock: '%s' (%s) aus gespielt-DB entfernt" % (title, system))
    return True


# ============================================================================
# Katalog: alle verfuegbaren Spiele (aus vorhandenen ROMs, US-bevorzugt)
# ============================================================================
# Prozessweiter Katalog-Cache. Teuer ist NUR der Ordner-Scan (os.walk) ueber
# alle Systeme; der laeuft pro Sitzung hoechstens einmal und wird zusaetzlich
# auf Platte gecacht, damit er einen Reboot ueberdauert.
_CATALOG_CACHE = None   # [ (system, pretty_title, genre, ra_id, rom, norm), ... ]

def wot_reset_index_cache():
    """Verwirft den in-Prozess-Katalog UND den Platten-Katalog-Cache -
    aufrufen, wenn sich der ROM-Bestand geaendert hat (neue/entfernte ROMs,
    NAS neu eingehaengt). Der naechste Katalogbau scannt dann frisch."""
    global _CATALOG_CACHE
    _CATALOG_CACHE = None
    try:
        os.remove(WOT_CATALOG_CACHE_FILE)
    except OSError:
        pass

def _wot_target_syskeys():
    """Zu durchsuchende syskeys: standardmaessig ALLE aus GAME_SYSTEMS, sonst
    nur die in WOT_SYSTEMS gelisteten (in GAME_SYSTEMS-Reihenfolge)."""
    all_keys = [s[1] for s in GAME_SYSTEMS]
    if not WOT_SYSTEMS:
        return all_keys
    wanted = set(WOT_SYSTEMS)
    return [k for k in all_keys if k in wanted]

def _wot_catalog_fingerprint():
    """Fingerprint der katalogbestimmenden Konfiguration: Systemauswahl + je
    System Ordner/Endungen + die aktuellen ROM-Basispfade + mtime von CSV &
    Aliases (damit geaenderte Anreicherung den Cache erneuert). BEWUSST NICHT
    vom ROM-Inhalt abhaengig - das waere genau der teure Scan, den der Cache
    spart; entfernte ROMs faengt die Existenzpruefung im Pool-Bau ab, neue
    ROMs deckt wot_reset_index_cache()."""
    sysinfo = []
    wanted = set(WOT_SYSTEMS) if WOT_SYSTEMS else None
    for s in GAME_SYSTEMS:
        _disp, syskey, folders, _rbf, extmap = s
        if wanted is not None and syskey not in wanted:
            continue
        sysinfo.append([syskey, list(folders), sorted(extmap.keys())])
    def _mtime(p):
        try:
            return os.path.getmtime(p)
        except OSError:
            return 0
    payload = json.dumps({"v": 1,
                          "systems": sysinfo,
                          "bases": sorted(_games_bases_getter()),
                          "csv": _mtime(WOT_CSV_FILE),
                          "aliases": _mtime(WOT_ALIASES_FILE)},
                         sort_keys=True, ensure_ascii=False)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()

def _wot_load_catalog_disk():
    """Laedt den Katalog aus dem Platten-Cache, aber nur wenn der Fingerprint
    passt. Liefert die Katalogliste oder None (kein/ungueltiger Cache)."""
    try:
        with open(WOT_CATALOG_CACHE_FILE, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or data.get("fingerprint") != _wot_catalog_fingerprint():
        return None
    out = []
    for g in data.get("games", []):
        if isinstance(g, list) and len(g) == 6:
            out.append(tuple(g))
    LOG("Zufalls-Zock: Katalog aus Platten-Cache geladen (%d Spiele)" % len(out))
    return out

def _wot_save_catalog_disk(catalog):
    """Schreibt den Katalog atomar auf Platte (Fehler werden nur geloggt)."""
    data = {"version": 1, "fingerprint": _wot_catalog_fingerprint(),
            "games": [list(g) for g in catalog]}
    try:
        tmp = WOT_CATALOG_CACHE_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        os.replace(tmp, WOT_CATALOG_CACHE_FILE)
    except OSError as e:
        LOG("Zufalls-Zock: Katalog-Cache schreiben fehlgeschlagen: %s" % e)

def wot_build_catalog(force=False, progress_cb=None):
    """Baut den Katalog ALLER verfuegbaren Spiele aus den tatsaechlich
    vorhandenen ROM-Dateien - quer ueber alle Ziel-Systeme. Pro
    (System, normalisiertem Titel) EIN Eintrag; bei mehreren Regionen wird
    die US-Version bevorzugt (RetroAchievements-Ansatz). Jeder Eintrag wird -
    falls eine wot_games.csv da ist - um Genre + RA-ID angereichert.

    Liefert Liste von (system, pretty_title, genre, ra_id, rom, norm).
    Prozessweit + auf Platte gecacht. force=True erzwingt einen Neuscan.
    progress_cb(done, total) optional fuer eine Fortschrittsanzeige (done =
    fertige Systeme). Sollte erst NACH dem NAS-Warten laufen (wie der
    normale Scan), sonst wird ein unvollstaendiger Stand gecacht."""
    global _CATALOG_CACHE
    if not force and _CATALOG_CACHE is not None:
        return _CATALOG_CACHE
    if not force:
        disk = _wot_load_catalog_disk()
        if disk is not None:
            _CATALOG_CACHE = disk
            return disk

    aliases = wot_load_aliases()
    enrich = wot_load_csv_enrichment(aliases)
    syskeys = _wot_target_syskeys()
    total = len(syskeys)
    catalog = []
    for i, syskey in enumerate(syskeys):
        best = {}   # norm -> (region_rank, rom, pretty)
        for rom in wot_list_rom_files(syskey):
            stem = os.path.splitext(os.path.basename(rom))[0]
            norm = wot_normalize_title(stem)
            if not norm:
                continue
            rank = _wot_region_rank(rom)
            cur = best.get(norm)
            if cur is None or rank < cur[0]:
                best[norm] = (rank, rom, wot_pretty_title(stem))
        for norm, (_rank, rom, pretty) in best.items():
            genre, ra_id = enrich.get((syskey, norm), ("", ""))
            catalog.append((syskey, pretty, genre, ra_id, rom, norm))
        if progress_cb is not None:
            progress_cb(i + 1, total)

    _CATALOG_CACHE = catalog
    _wot_save_catalog_disk(catalog)
    LOG("Zufalls-Zock: Katalog gebaut - %d Spiele aus %d Systemen" % (len(catalog), total))
    return catalog


# ============================================================================
# Roulette-Pool (Katalog minus gespielt) + Ziehen
# ============================================================================
def wot_build_playable_pool(pool=None, aliases=None, index_cache=None,
                            progress_cb=None, force=False):
    """Liefert den ROULETTE-POOL: alle Katalog-Spiele MINUS der bereits
    gespielten (gespielt-DB). Rueckgabe wie bisher als
    (system, title, genre, ra_id, rom, score)-Tupel; score ist jetzt
    konstant 1.0 (direkt aus vorhandenen ROMs, kein Fuzzy-Matching).

    Die Alt-Parameter pool/aliases/index_cache werden aus Kompatibilitaet
    akzeptiert, aber ignoriert - die Grundmenge ergibt sich jetzt aus
    ROMs + gespielt-DB, nicht mehr aus einer CSV. force=True baut den
    Katalog neu (Neuscan)."""
    catalog = wot_build_catalog(force=force, progress_cb=progress_cb)
    played, _raw = wot_load_played()
    out = []
    for (system, pretty, genre, ra_id, rom, norm) in catalog:
        if (system, norm) in played:
            continue
        if not os.path.exists(rom):   # self-healing: inzwischen entfernte ROMs raus
            continue
        out.append((system, pretty, genre, ra_id, rom, 1.0))
    LOG("Zufalls-Zock: Pool - %d von %d Katalog-Spielen offen (Rest gespielt/entfernt)"
        % (len(out), len(catalog)))
    return out

# Sprechender Alias fuer neuen Code:
wot_get_pool = wot_build_playable_pool

def wot_draw(count=3, exclude=None, pool=None):
    """Zieht bis zu `count` VERSCHIEDENE Spiele aus dem Roulette-Pool - quer
    ueber alle Systeme/Genres. `exclude`: Titel, die nicht gezogen werden
    sollen (z.B. die zuletzt angebotenen drei, damit 'Neu ziehen' frische
    Spiele bringt). `pool`: bereits gebauter Pool (spart erneutes Filtern);
    None -> wird selbst gebaut.

    Liefert Liste von (system, title, genre, ra_id, rom, score) mit 0..count
    Eintraegen - weniger, wenn der (Rest-)Pool kleiner ist; nie ein Fehler,
    nie Doppelte."""
    if pool is None:
        pool = wot_build_playable_pool()
    ex = set(exclude) if exclude else set()
    candidates = [g for g in pool if g[1] not in ex]
    if not candidates:
        return []
    if len(candidates) <= count:
        picks = list(candidates)
        random.shuffle(picks)
        return picks
    return random.sample(candidates, count)

def wot_draw_multiple(pool=None, aliases=None, count=3, max_attempts=20,
                      index_cache=None, exclude=None):
    """Kompatibilitaets-Wrapper auf wot_draw() - gleiche Rueckgabe wie bisher.
    aliases/max_attempts/index_cache werden ignoriert (kein Fuzzy-Ziehen
    mehr: jeder Pool-Eintrag ist per Definition spielbar)."""
    return wot_draw(count=count, exclude=exclude, pool=pool)


# ============================================================================
# Kompatibilitaets-Shim + optionale Einmal-Migration
# ============================================================================
def wot_load_pool():
    """Kompatibilitaets-Shim: liefert den offenen Pool als (system, title,
    genre, ra_id) - fruehere 4-Tupel-Form. Neuer Code nutzt direkt
    wot_build_playable_pool() / wot_draw()."""
    return [(s, t, g, r) for (s, t, g, r, _rom, _sc) in wot_build_playable_pool()]

def wot_migrate_played_from_csv():
    """OPTIONAL, EINMALIG: uebernimmt bereits gespielte/bewertete Spiele aus
    einer vorhandenen wot_games.csv in die gespielt-DB, damit die bisherige
    Historie erhalten bleibt. "gespielt" = Spalte 'Gespielt'==JA ODER Spalte
    'Erstes Mal' befuellt. Idempotent. Liefert die Anzahl neu uebernommener
    Eintraege."""
    try:
        with open(WOT_CSV_FILE, encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
    except (OSError, csv.Error):
        return 0
    played, raw = wot_load_played()
    added = 0
    for row in rows:
        system = (row.get("Konsole") or "").strip()
        title = (row.get("Spiel") or "").strip()
        if not system or not title:
            continue
        is_played = ((row.get("Gespielt") or "").strip().upper() == "JA"
                     or (row.get("Erstes Mal") or "").strip() != "")
        if not is_played:
            continue
        norm = wot_normalize_title(title)
        if (system, norm) in played:
            continue
        raw.append({"system": system, "title": title, "norm": norm,
                    "ra_id": (row.get("RA_ID") or "").strip(),
                    "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "source": "csv-migration"})
        played.add((system, norm))
        added += 1
    if added:
        wot_save_played(raw)
        LOG("Zufalls-Zock: %d Spiele aus CSV in gespielt-DB uebernommen" % added)
    return added


# ============================================================================
# Standalone-Selbsttest (ohne Frontend/Framebuffer)
# ============================================================================
if __name__ == "__main__":
    # Ohne configure() gibt es keine GAME_SYSTEMS -> der Katalog bleibt leer.
    # Getestet werden hier die Bausteine, die keine ROMs brauchen.
    print("== Titel-Normalisierung / Anzeige ==")
    samples = [
        "Legend of Zelda, The - A Link to the Past (USA)",
        "Super Mario World (USA)",
        "Mega Man X3 (Europe)",
        "Castlevania - Rondo of Blood (Japan)",
        "Adventures of Batman & Robin, The (USA) (Rev 1)",
    ]
    for t in samples:
        print("  %-52s\n      norm=%-30s pretty=%s"
              % (t, wot_normalize_title(t), wot_pretty_title(t)))
    print("\n== gespielt-DB Roundtrip (Dummy) ==")
    print("  played (geladen):", wot_load_played()[0])