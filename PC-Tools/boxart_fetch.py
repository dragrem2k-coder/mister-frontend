#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
boxart_fetch.py - Automatischer Boxart-Downloader fuer das MiSTer-Frontend
==========================================================================
v1.1
Laeuft auf dem PC (nicht auf dem MiSTer). Benoetigt:  pip install Pillow

Versionshistorie:
  v1.1 - Neu: IGNORE_ROM_BASENAMES ueberspringt bekannte Boot-/Test-/
         Demo-Dateien (boot.rom, boot1.rom, boot2.rom, mister-boot.*,
         mister-demo.*), die manche MiSTer-Verteilungen direkt in die
         ROM-Ordner legen und die sonst faelschlich gegen die Boxart-
         Datenbank gematcht wuerden. Die Ordnertiefe war hier schon
         immer unbegrenzt (kein Aendungsbedarf).
  v1.0 - Erste Version.

Das Skript:
  1. liest deine ROM-Dateinamen pro System ein
  2. holt die Liste aller verfuegbaren Cover von thumbnails.libretro.com
     (Fallback: GitHub-Spiegel)
  3. gleicht ROM-Namen mit Cover-Namen ab
     (exakt -> normalisiert -> ohne Regions-Tags -> Aehnlichkeitssuche)
  4. laedt die Treffer herunter (Cache, laedt nichts doppelt)
  5. konvertiert sie direkt ins .art-Format fuer das Frontend

Aufruf-Beispiele (PowerShell):

  # Alle Systeme, ROMs liegen unter D:\\roms\\<System> (SNES, NES, ...):
  python boxart_fetch.py --roms-base "D:\\roms" --out "art_out" --profile sd

  # ROMs direkt vom MiSTer ueber das Netzwerk (Samba aktiviert):
  python boxart_fetch.py --roms-base "\\\\192.168.178.128\\fat\\games" --out "art_out" --profile sd

  # Nur bestimmte Systeme:
  python boxart_fetch.py --roms-base "D:\\roms" --out "art_out" --systems SNES,NES

Danach den Inhalt von art_out\\ per WinSCP nach
/media/fat/frontend/art/  kopieren (Ordnernamen muessen erhalten bleiben).
"""

import argparse, difflib, html, json, os, re, struct, sys, time, zlib
import urllib.request, urllib.parse
import concurrent.futures

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow fehlt. Bitte installieren:  pip install Pillow")

# ---------------------------------------------------------------------------
# Systeme: Frontend-Systemkey -> (ROM-Ordnernamen, libretro-Systemname)
# Die ROM-Ordnernamen entsprechen den MiSTer-Standardordnern unter games/.
# ---------------------------------------------------------------------------
# syskey: (ROM-Ordner, ROM-Endungen, libretro-Thumbnail-Name)
# GAMEBOY und GBC teilen sich den Ordner "GAMEBOY", getrennt ueber die
# Endung (.gb vs .gbc). syskeys identisch zu Frontend/mister_boxart.
# ---------------------------------------------------------------------------
# SYSTEMTABELLE
# ---------------------------------------------------------------------------
# {syskey: (ROM-Ordner, {Endung: Datenbankname})}
#
# ACHTUNG - AUTOMATISCH ERZEUGT (Build 79). Die Quelle ist
# frontend/fe/systems.py (GAME_SYSTEMS + OPTIONAL_GAME_SYSTEMS +
# LIBRETRO_DB). Hier von Hand etwas einzutragen bringt nichts: dieses
# Skript laeuft zwar eigenstaendig auf einem PC und kann deshalb nichts
# aus fe/ importieren, aber tools/test_system_abdeckung.py vergleicht
# diese Tabelle bei jedem Testlauf mit der Quelle und schlaegt bei jeder
# Abweichung fehl.
#
# Warum ueberhaupt eine Kopie: bis Build 78 gab es DREI von Hand
# gepflegte Listen mit demselben Inhalt. Virtual Boy stand in keiner
# davon - das System kam ins Frontend, die Tabellen wurden uebersehen,
# und der Download lief brav durch, ohne es zu beruecksichtigen. Kein
# Fehler, nur keine Cover. Die beiden Werkzeuge auf dem MiSTer lesen
# jetzt direkt aus fe/systems.py; nur diese eine Kopie bleibt, weil das
# Skript einzeln auf einen Windows-PC kopiert wird.
SYSTEMS = {
    "3DO": (['3DO'], {".chd": "The 3DO Company - 3DO", ".cue": "The 3DO Company - 3DO"}),
    "ADVENTUREVISION": (['AVision'], {".bin": "Entex - Adventure Vision"}),
    "ARCADIA": (['Arcadia'], {".bin": "Emerson - Arcadia 2001"}),
    "ATARI2600": (['Atari2600', 'ATARI7800'], {".a26": "Atari - 2600"}),
    "ATARI5200": (['ATARI5200'], {".a52": "Atari - 5200", ".bin": "Atari - 5200", ".car": "Atari - 5200", ".rom": "Atari - 5200"}),
    "ATARI7800": (['ATARI7800'], {".a78": "Atari - 7800", ".bin": "Atari - 7800"}),
    "ATARILYNX": (['AtariLynx'], {".lnx": "Atari - Lynx"}),
    "CASIOPV1000": (['Casio_PV-1000'], {".bin": "Casio - PV-1000"}),
    "CDI": (['CD-i'], {".chd": "Philips - CD-i", ".cue": "Philips - CD-i"}),
    "CHANNELF": (['ChannelF'], {".bin": "Fairchild - Channel F", ".rom": "Fairchild - Channel F"}),
    "COLECOVISION": (['Coleco'], {".bin": "Coleco - ColecoVision", ".col": "Coleco - ColecoVision", ".rom": "Coleco - ColecoVision"}),
    "CREATIVISION": (['CreatiVision'], {".bas": "VTech - CreatiVision", ".bin": "VTech - CreatiVision", ".rom": "VTech - CreatiVision"}),
    "FDS": (['FDS', 'NES'], {".fds": "Nintendo - Family Computer Disk System"}),
    "GAMEBOY": (['GAMEBOY'], {".gb": "Nintendo - Game Boy"}),
    "GAMEGEAR": (['GameGear'], {".gg": "Sega - Game Gear"}),
    "GBA": (['GBA'], {".gba": "Nintendo - Game Boy Advance"}),
    "GBC": (['GAMEBOY'], {".gbc": "Nintendo - Game Boy Color"}),
    "Genesis": (['MegaDrive', 'Genesis'], {".bin": "Sega - Mega Drive - Genesis", ".gen": "Sega - Mega Drive - Genesis", ".md": "Sega - Mega Drive - Genesis"}),
    "INTELLIVISION": (['Intellivision'], {".bin": "Mattel - Intellivision", ".int": "Mattel - Intellivision"}),
    "JAGUAR": (['Jaguar'], {".bin": "Atari - Jaguar", ".j64": "Atari - Jaguar", ".jag": "Atari - Jaguar", ".rom": "Atari - Jaguar"}),
    "MegaCD": (['MegaCD'], {".chd": "Sega - Mega-CD - Sega CD", ".cue": "Sega - Mega-CD - Sega CD"}),
    "N64": (['N64'], {".n64": "Nintendo - Nintendo 64", ".z64": "Nintendo - Nintendo 64"}),
    "NEOGEO": (['NEOGEO'], {".neo": "SNK - Neo Geo"}),
    "NEOGEOCD": (['NeoGeo-CD'], {".chd": "SNK - Neo Geo CD", ".cue": "SNK - Neo Geo CD"}),
    "NES": (['NES'], {".nes": "Nintendo - Nintendo Entertainment System"}),
    "ODYSSEY2": (['ODYSSEY2'], {".bin": "Magnavox - Odyssey2"}),
    "POKEMONMINI": (['PokemonMini'], {".min": "Nintendo - Pokemon Mini"}),
    "PSX": (['PSX'], {".chd": "Sony - PlayStation", ".cue": "Sony - PlayStation"}),
    "S32X": (['S32X'], {".32x": "Sega - 32X"}),
    "SG1000": (['SG1000', 'Coleco', 'SMS'], {".sg": "Sega - SG-1000"}),
    "SMS": (['SMS'], {".gg": "Sega - Game Gear", ".sms": "Sega - Master System - Mark III"}),
    "SNES": (['SNES'], {".sfc": "Nintendo - Super Nintendo Entertainment System", ".smc": "Nintendo - Super Nintendo Entertainment System"}),
    "SUPERGAMEBOY": (['SGB'], {".gb": "Nintendo - Game Boy", ".gbc": "Nintendo - Game Boy"}),
    "Saturn": (['Saturn'], {".chd": "Sega - Saturn", ".cue": "Sega - Saturn"}),
    "TGFX16": (['TGFX16'], {".pce": "NEC - PC Engine - TurboGrafx 16", ".sgx": "NEC - PC Engine - TurboGrafx 16"}),
    "TGFX16CD": (['TGFX16-CD'], {".chd": "NEC - PC Engine CD - TurboGrafx-CD", ".cue": "NEC - PC Engine CD - TurboGrafx-CD"}),
    "VECTREX": (['VECTREX'], {".bin": "GCE - Vectrex", ".rom": "GCE - Vectrex", ".vec": "GCE - Vectrex"}),
    "VIRTUALBOY": (['VirtualBoy'], {".vb": "Nintendo - Virtual Boy"}),
    "WONDERSWAN": (['WonderSwan'], {".ws": "Bandai - WonderSwan"}),
    "WONDERSWANCOLOR": (['WonderSwanColor', 'WonderSwan'], {".wsc": "Bandai - WonderSwan Color"}),
}

# NEU (siehe ausfuehrliche Begruendung in frontend/mister_boxart.py -
# per echter Hardware-Diagnose bestaetigt: kleinere Quelldateien lesen
# spuerbar schneller von der SD-Karte UND treffen bei typischen 1080p-
# Boxgroessen den Sprung auf Skalierungsfaktor 2x, was die Box sogar
# BESSER ausfuellt als die bisherigen 360x420 (die dort meist bei 1x
# blieben, kein tatsaechliches Hochskalieren).
# NEU (siehe ausfuehrliche Begruendung in frontend/mister_boxart.py -
# nachgerechnet statt "aggressiver" geraten: das CRT-Boxart-Panel ist
# rechnerisch nie groesser als ~101x165px, 104x168 deckt das mit kleiner
# Marge ab, ohne unnoetig ueber den Bildschirm hinaus aufzuloesen).
PROFILES = {
    "sd": (104, 168),   # max Breite x Hoehe fuer CRT-Modi (240 Zeilen)
    "hd": (300, 350),   # max Breite x Hoehe fuer 1080p
}

# Bekannte Boot-/Test-/Demo-Dateien, die manche MiSTer-Verteilungen
# direkt in die ROM-Ordner legen (fuer den Hardware-Selbsttest). Haben
# zufaellig die richtige Endung und wuerden sonst versucht werden, wie
# ein echtes Spiel gegen die Boxart-Datenbank zu matchen. Identisch zur
# gleichnamigen Konstante im Frontend (frontend.py) und in
# mister_boxart.py/mister_gameinfo.py.
IGNORE_ROM_BASENAMES = {"boot", "boot1", "boot2", "mister-boot", "mister-demo"}

# Tags, die ein ROM als Beta/Prototyp/Demo/Hack/defekten Dump o.ae.
# kennzeichnen - werden beim Einsammeln uebersprungen (identisch zur
# gleichnamigen Konstante in frontend.py).
JUNK_TAGS = ("(beta", "(proto", "(demo", "(sample", "(unl)", "[b]",
            "(pirate", "(program", "(test", "(kiosk", "(hack")

# Rein japanische ROMs ausblenden (identisch zur gleichnamigen Logik
# in frontend.py) - Mehrfach-Region-Tags wie "(Japan, USA)" bleiben
# erhalten, da diese Version auch USA/Europa abdeckt.
_JAPAN_ONLY = re.compile(r"[\(\[]\s*(?:japan|j)\s*[\)\]]", re.I)

def _is_japan_only(name):
    return bool(_JAPAN_ONLY.search(name))

LIBRETRO_BASE = "https://thumbnails.libretro.com"
GITHUB_RAW    = "https://raw.githubusercontent.com/libretro-thumbnails"
GITHUB_API    = "https://api.github.com/repos/libretro-thumbnails"

UA = {"User-Agent": "MiSTer-Frontend-BoxartFetch/1.0"}

# Zeichen, die libretro in Dateinamen durch _ ersetzt
BADCHARS = re.compile(r"[&*/:`<>?\\|]")

# ---------------------------------------------------------------------------
# Namens-Matching
# ---------------------------------------------------------------------------

def sanitize(name):
    """ROM-Name in die libretro-Dateinamenskonvention ueberfuehren."""
    return BADCHARS.sub("_", name)

def norm(name):
    """Fuer den Vergleich: klein, nur Buchstaben/Ziffern."""
    return re.sub(r"[^a-z0-9]", "", name.lower())

def strip_tags(name):
    """Klammer-Tags entfernen: 'Spiel (Europe) (Rev 1)' -> 'Spiel'."""
    return re.sub(r"[\(\[][^\)\]]*[\)\]]", "", name).strip()

# BUGFIX (siehe frontend/mister_boxart.py fuer die ausfuehrliche
# Begruendung - identische Region-Verwechslung: USA-ROMs bekamen bei
# fehlendem exaktem Cover-Treffer systematisch europaeische Cover
# zugeordnet statt umgekehrt, da Germany/Europe/World bisher vor USA
# standen).
REGION_PRIORITY = ["(usa)", "(world)", "(europe)", "(japan)", "(germany)"]

def region_rank(name):
    low = name.lower()
    for i, tag in enumerate(REGION_PRIORITY):
        if tag in low:
            return i
    return len(REGION_PRIORITY)

def build_index(cover_names):
    idx_exact = {}
    idx_strip = {}
    for cn in cover_names:
        base = os.path.splitext(cn)[0]
        idx_exact.setdefault(norm(base), []).append(cn)
        idx_strip.setdefault(norm(strip_tags(base)), []).append(cn)
    return idx_exact, idx_strip

def match_rom(rom_base, idx_exact, idx_strip, all_norms):
    """Bestes Cover fuer einen ROM-Namen finden. Rueckgabe (covername, art)"""
    n = norm(sanitize(rom_base))
    if n in idx_exact:
        cands = sorted(idx_exact[n], key=region_rank)
        return cands[0], "exakt"
    ns = norm(strip_tags(sanitize(rom_base)))
    if ns in idx_strip:
        cands = sorted(idx_strip[ns], key=region_rank)
        return cands[0], "ohne-tags"
    close = difflib.get_close_matches(ns, all_norms, n=1, cutoff=0.90)
    if close:
        cands = sorted(idx_strip[close[0]], key=region_rank)
        return cands[0], "aehnlich"
    return None, None

# ---------------------------------------------------------------------------
# Cover-Listen holen
# ---------------------------------------------------------------------------

def http_get(url, timeout=30):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def list_covers_libretro(sysname):
    """HTML-Verzeichnisindex von thumbnails.libretro.com parsen."""
    url = "%s/%s/Named_Boxarts/" % (
        LIBRETRO_BASE, urllib.parse.quote(sysname))
    data = http_get(url).decode("utf-8", "replace")
    names = re.findall(r'href="([^"]+\.png)"', data)
    return [html.unescape(urllib.parse.unquote(n)) for n in names
            if not n.startswith("http")]

def list_covers_github(sysname):
    """Fallback: Dateiliste ueber die GitHub-API (1 Request pro System)."""
    repo = sysname.replace(" ", "_")
    url = "%s/%s/git/trees/master?recursive=1" % (GITHUB_API, repo)
    tree = json.loads(http_get(url))
    return [os.path.basename(e["path"]) for e in tree.get("tree", [])
            if e["path"].startswith("Named_Boxarts/")
            and e["path"].endswith(".png")]

def get_cover_list(sysname, cache_dir):
    cache_file = os.path.join(cache_dir, "_list_%s.json"
                              % re.sub(r"\W+", "_", sysname))
    if os.path.exists(cache_file):
        with open(cache_file) as f:
            return json.load(f)
    try:
        names = list_covers_libretro(sysname)
        quelle = "thumbnails.libretro.com"
    except Exception as e1:
        try:
            names = list_covers_github(sysname)
            quelle = "GitHub-API"
        except Exception as e2:
            print("  Liste nicht abrufbar (%s / %s)" % (e1, e2))
            return []
    print("  %d Cover verfuegbar (%s)" % (len(names), quelle))
    with open(cache_file, "w") as f:
        json.dump(names, f)
    return names

def download_cover(sysname, covername, dest):
    urls = [
        "%s/%s/Named_Boxarts/%s" % (LIBRETRO_BASE,
            urllib.parse.quote(sysname), urllib.parse.quote(covername)),
        "%s/%s/master/Named_Boxarts/%s" % (GITHUB_RAW,
            sysname.replace(" ", "_"), urllib.parse.quote(covername)),
    ]
    for url in urls:
        try:
            data = http_get(url, timeout=60)
            with open(dest, "wb") as f:
                f.write(data)
            return True
        except Exception:
            continue
    return False

# ---------------------------------------------------------------------------
# .art-Konvertierung (identisch zu art_convert.py)
# ---------------------------------------------------------------------------

def convert(img_path, out_path, box):
    """Bild proportional in die Begrenzungsbox (max_w, max_h) einpassen."""
    max_w, max_h = box
    img = Image.open(img_path).convert("RGB")
    scale = min(max_w / img.width, max_h / img.height)
    w = max(1, round(img.width * scale))
    h = max(1, round(img.height * scale))
    img = img.resize((w, h), Image.LANCZOS)
    rgb = img.tobytes()
    pix = bytearray(len(rgb) // 3 * 4)
    pix[0::4] = rgb[2::3]
    pix[1::4] = rgb[1::3]
    pix[2::4] = rgb[0::3]
    with open(out_path, "wb") as f:
        f.write(b"ART1" + struct.pack("<HH", w, h)
                + zlib.compress(bytes(pix), 9))

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

def collect_roms(base, folders, exts):
    """Hatte hier nie eine Tiefenbegrenzung (im Gegensatz zum
    Frontend/mister_boxart.py/mister_gameinfo.py) - beliebige
    Ordnerstruktur/Sortierung wurde also immer schon unterstuetzt.
    Seit v1.1: bekannte Boot-/Testdateien (siehe IGNORE_ROM_BASENAMES)
    werden anhand des Dateinamens uebersprungen. Seit v1.2 zusaetzlich:
    bekannte Beta/Proto/Demo/Hack/Bad-Dump-Tags (JUNK_TAGS) werden
    uebersprungen, und Mehrfach-Regionen desselben Spiels werden zu
    EINER Kopie zusammengefasst (beste Region gewinnt, region_rank)."""
    raw = []
    for folder in folders:
        root = os.path.join(base, folder)
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, files in os.walk(root):
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]
            for fn in files:
                b, ext = os.path.splitext(fn)
                if b.lower() in IGNORE_ROM_BASENAMES:
                    continue
                low = b.lower()
                if any(tag in low for tag in JUNK_TAGS):
                    continue
                if _is_japan_only(b):
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

def process_one_rom(rom, sysname, idx_exact, idx_strip, all_norms,
                    out_dir, cache_dir, box, force):
    """Ein einzelnes ROM verarbeiten: Cover suchen, herunterladen (falls
    noch nicht im Cache), konvertieren. Sicher aus mehreren Threads
    gleichzeitig aufrufbar - jedes ROM schreibt eine eigene Datei."""
    art_out = os.path.join(out_dir, rom + ".art")
    if os.path.exists(art_out) and not force:
        return (rom, "already_ok", None)
    cover, how = match_rom(rom, idx_exact, idx_strip, all_norms)
    if not cover:
        return (rom, "missing", None)
    png = os.path.join(cache_dir, cover)
    if not os.path.exists(png):
        if not download_cover(sysname, cover, png):
            return (rom, "dl_failed", cover)
    try:
        convert(png, art_out, box)
        return (rom, "ok", (how, cover))
    except Exception as e:
        return (rom, "convert_error", str(e))

DOWNLOAD_WORKERS = 6   # gleichzeitige Downloads - genug fuer spuerbare
                       # Beschleunigung, ohne den Server zu ueberlasten

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--roms-base", required=True,
                    help="Ordner mit den System-Unterordnern (SNES, NES, ...)")
    ap.add_argument("--out", required=True, help="Ausgabeordner fuer .art")
    ap.add_argument("--cache", default="boxart_cache",
                    help="Download-Cache (Standard: boxart_cache)")
    ap.add_argument("--profile", choices=PROFILES, default="sd")
    ap.add_argument("--systems", help="Nur diese Systemkeys, kommagetrennt")
    ap.add_argument("--force", action="store_true",
                    help="Vorhandene .art-Dateien neu erzeugen")
    args = ap.parse_args()

    box = PROFILES[args.profile]
    os.makedirs(args.cache, exist_ok=True)
    only = set(s.strip() for s in args.systems.split(",")) \
        if args.systems else None

    gesamt = {"roms": 0, "ok": 0, "fehlend": 0}
    for syskey, (folders, ext_db_map) in SYSTEMS.items():
        if only and syskey not in only:
            continue
        roms = collect_roms(args.roms_base, folders, set(ext_db_map))
        if not roms:
            continue
        print("== %s: %d ROMs" % (syskey, len(roms)))
        # Ein Core kann Spiele mehrerer Systeme abspielen, deren Cover
        # bei libretro getrennt liegen (Master System / Game Gear).
        # Deshalb die Cover-Listen aller beteiligten Datenbanken
        # zusammenfuehren, statt nur eine abzufragen.
        covers = []
        for datenbank in sorted(set(ext_db_map.values())):
            covers.extend(get_cover_list(datenbank, args.cache) or [])
        sysname = sorted(set(ext_db_map.values()))[0]
        if not covers:
            continue
        idx_exact, idx_strip = build_index(covers)
        all_norms = list(idx_strip.keys())

        out_dir = os.path.join(args.out, syskey)
        cache_dir = os.path.join(args.cache, syskey)
        os.makedirs(out_dir, exist_ok=True)
        os.makedirs(cache_dir, exist_ok=True)

        missing = []
        done = 0
        with concurrent.futures.ThreadPoolExecutor(
                max_workers=DOWNLOAD_WORKERS) as executor:
            futures = {
                executor.submit(process_one_rom, rom, sysname, idx_exact,
                               idx_strip, all_norms, out_dir, cache_dir,
                               box, args.force): rom
                for rom in roms
            }
            try:
                for future in concurrent.futures.as_completed(futures):
                    rom = futures[future]
                    gesamt["roms"] += 1
                    done += 1
                    try:
                        _, status, info = future.result()
                    except Exception as e:
                        status, info = "error", str(e)
                    if status in ("ok", "already_ok"):
                        gesamt["ok"] += 1
                        if status == "ok":
                            how, cover = info
                            if how != "exakt":
                                print("  [%s] %s  ->  %s" % (how, rom, cover))
                    elif status == "missing":
                        missing.append(rom)
                        gesamt["fehlend"] += 1
                    elif status == "dl_failed":
                        print("  Download fehlgeschlagen: %s" % info)
                        missing.append(rom)
                        gesamt["fehlend"] += 1
                    else:
                        print("  Konvertierung fehlgeschlagen %s: %s" % (rom, info))
                        missing.append(rom)
                        gesamt["fehlend"] += 1
            except KeyboardInterrupt:
                print("\nAbgebrochen - breche laufende Downloads ab...")
                executor.shutdown(wait=False, cancel_futures=True)
                raise
                gesamt["fehlend"] += 1

        if missing:
            miss_file = os.path.join(args.out, "fehlend_%s.txt" % syskey)
            with open(miss_file, "w", encoding="utf-8") as f:
                f.write("\n".join(missing))
            print("  %d ohne Cover -> %s" % (len(missing), miss_file))

    print("\nGesamt: %(roms)d ROMs, %(ok)d mit Cover, %(fehlend)d ohne"
          % gesamt)

if __name__ == "__main__":
    main()
