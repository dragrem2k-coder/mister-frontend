#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mister_gameinfo.py - Spiele-Metadaten-Downloader, laeuft AUF DEM MISTER
========================================================================
v1.1
Keine Abhaengigkeiten - nur Python-Standardbibliothek.

Versionshistorie:
  v1.1 - collect_roms() ohne Tiefenbegrenzung (vorher max. 2 Ordner-
         ebenen "wie im Frontend") - beliebig tief sortierte ROM-
         Ordner werden jetzt vollstaendig durchsucht. Neu:
         IGNORE_ROM_BASENAMES ueberspringt bekannte Boot-/Test-/Demo-
         Dateien (boot.rom, boot1.rom, boot2.rom, mister-boot.*,
         mister-demo.*), die manche MiSTer-Verteilungen direkt in die
         ROM-Ordner legen und die sonst faelschlich gegen die
         libretro-Datenbank gematcht wuerden.
  v1.0 - Erste Version.

Holt Genre, Erscheinungsjahr und Spieleranzahl aus der libretro-Datenbank
(github.com/libretro/libretro-database), gleicht sie mit deinen ROMs ab
und schreibt die meta/<System>.json-Dateien, die das Frontend im
Info-Panel anzeigt.

Aufruf (SSH oder ueber die Scripts-Kategorie des Frontends):
  python3 /media/fat/frontend/mister_gameinfo.py            # alle Systeme
  python3 /media/fat/frontend/mister_gameinfo.py SNES NES   # nur bestimmte
  python3 /media/fat/frontend/mister_gameinfo.py --refresh  # DB neu laden

Die Datenbank-Dateien werden unter /media/fat/frontend/cache/
zwischengespeichert; ohne --refresh werden sie wiederverwendet.
Der Lauf ist schnell (reine Textverarbeitung, keine Bilder).
"""

import difflib, json, os, re, ssl, sys, time
import urllib.request, urllib.parse

GAMES_BASES = (["/media/fat/games"]
               + ["/media/usb%d/games" % i for i in range(6)]
               + ["/media/usb%d" % i for i in range(6)])
META_BASE  = "/media/fat/frontend/meta"
CACHE_BASE = "/media/fat/frontend/cache"

# Bekannte Boot-/Test-/Demo-Dateien, die manche MiSTer-Verteilungen
# direkt in die ROM-Ordner legen (fuer den Hardware-Selbsttest). Haben
# zufaellig die richtige Endung und wuerden sonst versucht werden, wie
# ein echtes Spiel gegen die libretro-Datenbank zu matchen. Identisch
# zur gleichnamigen Konstante im Frontend (frontend.py).
IGNORE_ROM_BASENAMES = {"boot", "boot1", "boot2", "mister-boot", "mister-demo"}

# Tags, die ein ROM als Beta/Prototyp/Demo/Hack/defekten Dump o.ae.
# kennzeichnen - werden beim Einsammeln uebersprungen, spart Zeit fuer
# Dateien, die im Frontend ohnehin ausgefiltert werden (identisch zur
# gleichnamigen Konstante in frontend.py).
JUNK_TAGS = ("(beta", "(proto", "(demo", "(sample", "(unl)", "[b]",
            "(pirate", "(program", "(test", "(kiosk", "(hack")

# syskey: (ROM-Ordner, ROM-Endungen, libretro-DB-Name)
# GAMEBOY und GBC teilen sich den Ordner "GAMEBOY", werden aber ueber die
# Endung getrennt (.gb vs .gbc). syskeys identisch zu Frontend/boxart.
SYSTEMS = {
    "NES":     (["NES"],                  {".nes"},                "Nintendo - Nintendo Entertainment System"),
    "SNES":    (["SNES"],                 {".sfc", ".smc"},        "Nintendo - Super Nintendo Entertainment System"),
    "Genesis": (["MegaDrive", "Genesis"], {".md", ".gen", ".bin"}, "Sega - Mega Drive - Genesis"),
    "N64":     (["N64"],                  {".n64", ".z64"},        "Nintendo - Nintendo 64"),
    "PSX":     (["PSX"],                  {".chd", ".cue"},        "Sony - PlayStation"),
    "GAMEBOY": (["GAMEBOY"],              {".gb"},                 "Nintendo - Game Boy"),
    "GBC":     (["GAMEBOY"],              {".gbc"},                "Nintendo - Game Boy Color"),
    "GBA":     (["GBA"],                  {".gba"},                "Nintendo - Game Boy Advance"),
    "SMS":     (["SMS"],                  {".sms", ".gg"},         "Sega - Master System - Mark III"),
    "TGFX16":  (["TGFX16"],               {".pce", ".sgx"},        "NEC - PC Engine - TurboGrafx 16"),
    "MegaCD":  (["MegaCD"],               {".chd", ".cue"},        "Sega - Mega-CD - Sega CD"),
    "Saturn":  (["Saturn"],               {".chd", ".cue"},        "Sega - Saturn"),
    "NEOGEO":  (["NEOGEO"],               {".neo"},                "SNK - Neo Geo"),
}

DB_RAW = ("https://raw.githubusercontent.com/libretro/"
          "libretro-database/master/metadat")
DB_KINDS = ["genre", "releaseyear", "maxusers"]
UA = {"User-Agent": "MiSTer-Frontend-Gameinfo/1.0"}

# ---------------------------------------------------------------------------
# HTTP mit SSL-Fallback
# ---------------------------------------------------------------------------

_ssl_ctx = None

def http_get(url, timeout=60):
    global _ssl_ctx
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=timeout,
                                    context=_ssl_ctx) as r:
            return r.read()
    except ssl.SSLError:
        if _ssl_ctx is None:
            print("  (SSL-Pruefung nicht moeglich - fahre unverifiziert fort)")
            _ssl_ctx = ssl._create_unverified_context()
            return http_get(url, timeout)
        raise

# ---------------------------------------------------------------------------
# DAT-Dateien holen und parsen
# ---------------------------------------------------------------------------

def fetch_dat(sysname, kind, refresh):
    os.makedirs(CACHE_BASE, exist_ok=True)
    cache = os.path.join(CACHE_BASE, "%s_%s.dat"
                         % (re.sub(r"\W+", "_", sysname), kind))
    if os.path.exists(cache) and not refresh:
        return open(cache, "r", errors="replace").read()
    url = "%s/%s/%s.dat" % (DB_RAW, kind, urllib.parse.quote(sysname))
    try:
        data = http_get(url).decode("utf-8", "replace")
    except Exception as e:
        print("  %s: nicht abrufbar (%s)" % (kind, e))
        return ""
    with open(cache, "w") as f:
        f.write(data)
    return data

_FIELD_RE = {
    "genre":       re.compile(r'genre\s+"([^"]*)"'),
    "releaseyear": re.compile(r'releaseyear\s+"([^"]*)"'),
    "maxusers":    re.compile(r'users\s+(\d+)'),
}
_COMMENT_RE = re.compile(r'comment\s+"([^"]*)"')

def parse_dat(text, kind):
    """DAT -> {Spielname: Wert}"""
    out = {}
    field_re = _FIELD_RE[kind]
    for block in text.split("game ("):
        cm = _COMMENT_RE.search(block)
        fm = field_re.search(block)
        if cm and fm:
            out.setdefault(cm.group(1), fm.group(1))
    return out

# ---------------------------------------------------------------------------
# Namens-Matching (identisch zum Boxart-Skript)
# ---------------------------------------------------------------------------

def norm(name):
    return re.sub(r"[^a-z0-9]", "", name.lower())

def strip_tags(name):
    return re.sub(r"[\(\[][^\)\]]*[\)\]]", "", name).strip()

REGION_PRIORITY = ["(germany)", "(europe)", "(world)", "(usa)", "(japan)"]

def region_rank(name):
    low = name.lower()
    for i, tag in enumerate(REGION_PRIORITY):
        if tag in low:
            return i
    return len(REGION_PRIORITY)

def build_index(names):
    idx_exact = {}
    idx_strip = {}
    buckets = {}
    for n in names:
        idx_exact.setdefault(norm(n), []).append(n)
        ns = norm(strip_tags(n))
        idx_strip.setdefault(ns, []).append(n)
        if ns:
            buckets.setdefault(ns[0], []).append(ns)
    return idx_exact, idx_strip, buckets

def match_name(rom_base, idx_exact, idx_strip, buckets):
    n = norm(rom_base)
    if n in idx_exact:
        return sorted(idx_exact[n], key=region_rank)[0]
    ns = norm(strip_tags(rom_base))
    if ns in idx_strip:
        return sorted(idx_strip[ns], key=region_rank)[0]
    if not ns:
        return None
    # Aehnlichkeitssuche nur im kleinen Kandidatenkreis:
    # gleicher Anfangsbuchstabe, Laenge +/- 3 Zeichen
    cands = [c for c in buckets.get(ns[0], ())
             if abs(len(c) - len(ns)) <= 3]
    close = difflib.get_close_matches(ns, cands, n=1, cutoff=0.92)
    if close:
        return sorted(idx_strip[close[0]], key=region_rank)[0]
    return None

# ---------------------------------------------------------------------------

# Datentraeger-Marker (Disc 1/2, CD 2, Side B ...) duerfen beim Dedupe
# NICHT wie ein Regions-Tag behandelt werden - sonst bekaeme nur Disc 1
# ein Cover/Metadaten und Disc 2+ ginge leer aus.
_DISC = re.compile(r"[\(\[]\s*(?:disc|disk|cd|side|part|tape|track)\s*"
                   r"[0-9a-z]+\s*[\)\]]", re.I)

def dedupe_key(name):
    """Kanonischer Schluessel: ohne Klammer-Zusaetze, aber MIT
    Disc-/CD-Marker, damit mehrteilige Spiele getrennt bleiben."""
    key = norm(strip_tags(name))
    m = _DISC.search(name)
    if m:
        key += " " + re.sub(r"\s+", "", m.group(0).lower())
    return key

def collect_roms(folders, exts):
    """Seit v1.1: OHNE Tiefenbegrenzung (vorher max. 2 Ordnerebenen,
    "wie im Frontend") - eigene Ordnerstruktur/Sortierung (beliebig
    tief) bleibt so erhalten. Bekannte Boot-/Testdateien (siehe
    IGNORE_ROM_BASENAMES) werden anhand des Dateinamens uebersprungen,
    damit sie nicht versehentlich gegen die libretro-Datenbank
    gematcht werden.

    Seit v1.2 zusaetzlich: bekannte Beta/Proto/Demo/Hack/Bad-Dump-Tags
    (JUNK_TAGS) werden uebersprungen, und Mehrfach-Regionen desselben
    Spiels werden zu EINER Kopie zusammengefasst (beste Region gewinnt,
    region_rank) - identisch zur Dedupe-Logik im Frontend
    (frontend.py)."""
    raw = []
    seen_roots = set()
    for base in GAMES_BASES:
        if not os.path.isdir(base):
            continue
        for folder in folders:
            root = os.path.join(base, folder)
            real = os.path.realpath(root)
            if not os.path.isdir(root) or real in seen_roots:
                continue
            seen_roots.add(real)
            for dirpath, dirnames, files in os.walk(root):
                dirnames[:] = [d for d in dirnames
                               if not d.startswith(".")]
                for fn in files:
                    b, ext = os.path.splitext(fn)
                    if b.lower() in IGNORE_ROM_BASENAMES:
                        continue
                    low = b.lower()
                    if any(tag in low for tag in JUNK_TAGS):
                        continue
                    if ext.lower() in exts:
                        raw.append(b)
    best = {}
    for name in raw:
        key = dedupe_key(name)
        rank = region_rank(name)
        cur = best.get(key)
        if cur is None or rank < cur[0]:
            best[key] = (rank, name)
    return sorted(name for _rank, name in best.values())

def main():
    args = sys.argv[1:]
    refresh = "--refresh" in args
    only = set(a for a in args if not a.startswith("--")) or None

    os.makedirs(META_BASE, exist_ok=True)
    total = with_meta = 0
    t0 = time.time()
    for syskey, (folders, exts, sysname) in SYSTEMS.items():
        if only and syskey not in only:
            continue
        roms = collect_roms(folders, exts)
        if not roms:
            continue
        print("== %s: %d ROMs" % (syskey, len(roms)), flush=True)

        db = {}                      # Spielname -> {genre, year, players}
        for kind, out_key in (("genre", "genre"),
                              ("releaseyear", "year"),
                              ("maxusers", "players")):
            text = fetch_dat(sysname, kind, refresh)
            parsed = parse_dat(text, kind)
            for name, val in parsed.items():
                db.setdefault(name, {})[out_key] = val
        if not db:
            print("  keine Datenbank verfuegbar")
            continue
        print("  Datenbank: %d Spiele" % len(db), flush=True)

        idx_exact, idx_strip, buckets = build_index(db.keys())

        meta = {}
        for nr, rom in enumerate(roms, 1):
            total += 1
            if nr % 200 == 0:
                print("  ... %d/%d verarbeitet (%d Treffer)"
                      % (nr, len(roms), len(meta)), flush=True)
            hit = match_name(rom, idx_exact, idx_strip, buckets)
            if hit:
                m = dict(db[hit])
                # "2 Spieler" lesbarer machen: users=1 -> "1", users=2 -> "1-2"
                if m.get("players") and m["players"].isdigit():
                    p = int(m["players"])
                    m["players"] = "1" if p <= 1 else "1-%d" % p
                meta[rom] = m
                with_meta += 1
        out = os.path.join(META_BASE, syskey + ".json")
        with open(out, "w") as f:
            json.dump(meta, f)
        print("  %d/%d mit Infos -> %s" % (len(meta), len(roms), out))

    print("\nFertig nach %.1f min: %d ROMs, %d mit Infos"
          % ((time.time() - t0) / 60, total, with_meta))
    print("Hinweis: Frontend neu starten bzw. Kategorie wechseln,")
    print("damit die neuen Infos geladen werden.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAbgebrochen.")
