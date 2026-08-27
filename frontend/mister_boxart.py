#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mister_boxart.py - Boxart-Downloader fuer den MiSTer
========================================================
v4.0
Keine Abhaengigkeiten - nur Python-Standardbibliothek.

ZWEI QUELLEN, automatisch kombiniert:
  1. MIRROR (schnell, bevorzugt): ein vertrauenswuerdiger HTTP-Mirror
     mit bereits FERTIGEN .art-Dateien (einmalig auf einem PC erzeugt,
     siehe art_build_mirror.py auf der Mirror-Seite). Der MiSTer muss
     dabei selbst NICHTS dekodieren/skalieren - reiner Download.
  2. FALLBACK (langsamer, aber unabhaengig): fuer alles, was der
     Mirror nicht listet oder nicht zuordnen kann, faellt das Skript
     automatisch auf den bisherigen Weg zurueck - PNG-Cover von
     thumbnails.libretro.com (Fallback: GitHub) laden und in reinem
     Python selbst dekodieren/skalieren. Genau der Weg, den dieses
     Skript vor v4.0 exklusiv genutzt hat.

Warum beide statt nur der schnellen Mirror-Variante: der Mirror ist
ein einzelner, dritter Server - faellt er aus, hat eine reine
Mirror-Loesung KEINE Cover mehr. Mit dem automatischen Rueckfall auf
die etablierte, breit genutzte libretro-thumbnails-Quelle bleibt
Boxart-Download auch dann funktionsfaehig, nur eben langsamer fuer die
betroffenen Eintraege - kein Alles-oder-nichts.

Aufruf (SSH oder ueber die Scripts-Kategorie des Frontends):
  python3 /media/fat/frontend/mister_boxart.py            # alle Systeme, CRT-Profil
  python3 /media/fat/frontend/mister_boxart.py hd         # 1080p-Profil
  python3 /media/fat/frontend/mister_boxart.py sd SNES NES  # nur bestimmte Systeme

Bereits vorhandene .art-Dateien werden uebersprungen - das Skript
kann jederzeit abgebrochen (Strg+C) und spaeter fortgesetzt werden.

Versionshistorie:
  v4.0 - Mirror-Fetch als schnellen Hauptweg ergaenzt (Nutzerwunsch,
         nach Pruefung eines vom Nutzer als vertrauenswuerdig
         bestaetigten Mirrors uebernommen), mit automatischem
         Rueckfall auf den bisherigen Weg (Punkt 2 oben) fuer alles,
         was der Mirror nicht liefert - kein Verlust der bisherigen
         Zuverlaessigkeit. Beim Uebernehmen bewusst NICHT 1:1 kopiert,
         drei Korrekturen gegenueber der urspruenglich vorgeschlagenen
         Mirror-Fassung:
         (1) Regions-Prioritaet auf die bereits in v1.2 aus echter
             Nutzer-Rueckmeldung korrigierte Reihenfolge (USA/World
             zuerst) belassen, NICHT auf die im Mirror-Skript
             verwendete alte Reihenfolge zurueckgestellt - sonst waere
             genau der schon behobene Bug (Europa-Cover fuer
             USA-Sammlungen) wieder da gewesen.
         (2) Game Gear (.gg) bleibt wie im Frontend selbst (siehe
             fe/systems.py) im gemeinsamen "SMS"-Systemschluessel/
             -Ordner - ROMs UND fertige .art-Dateien liegen weiter
             zusammen, weil das Frontend genau dort danach sucht. Nur
             die COVER-QUELLE wird intern je nach Endung getrennt
             (.sms -> "Sega - Master System - Mark III", .gg ->
             "Sega - Game Gear") - vorher landeten Game-Gear-Cover in
             der Master-System-Datenbank und wurden praktisch nie
             gefunden.
         (3) SYSTEMS bewusst NICHT um die zusaetzlichen, im
             Mirror-Skript unterstuetzten Systeme (Atari-Familie, C64,
             Amiga, CD32, ScummVM, FDS, Satellaview, N64DD, 32X,
             SG1000, TGFX16CD, NGPC/NGPCC) erweitert - das Frontend
             selbst kennt aktuell nur die Systeme unten (siehe
             GAME_SYSTEMS in fe/systems.py), fuer alles Weitere gaebe
             es im Frontend gar keine Kategorie, in der die Cover
             jemals angezeigt wuerden - waere nur unnoetig belegter
             SD-Kartenplatz.
         Uebernommen wurde dagegen unveraendert: Trigramm-vorgefilterte
         unscharfe Namenssuche (schneller als der bisherige direkte
         difflib-Abgleich gegen die komplette Liste bei grossen
         Sammlungen), Download mit Wiederholungsversuchen samt
         kurzem Backoff, sowie eine echte Fortschrittsanzeige mit
         Geschwindigkeit/ETA statt nur einer Zeile pro Cover.
  v1.1 - collect_roms() ohne Tiefenbegrenzung (vorher max. 2 Ordner-
         ebenen "wie im Frontend") - beliebig tief sortierte ROM-
         Ordner werden jetzt vollstaendig durchsucht. Neu:
         IGNORE_ROM_BASENAMES ueberspringt bekannte Boot-/Test-/Demo-
         Dateien (boot.rom, boot1.rom, boot2.rom, mister-boot.*,
         mister-demo.*), die manche MiSTer-Verteilungen direkt in die
         ROM-Ordner legen und die sonst faelschlich gegen die Boxart-
         Datenbank gematcht wuerden.
  v1.0 - Erste Version.
"""

import re, difflib, glob, html, json, os, ssl, struct, sys, threading, time, zlib
import http.client
import queue
import urllib.request, urllib.parse
import concurrent.futures
from collections import Counter

BASE = "/media/fat"   # fuer die Arcade-Ordnersuche (_Arcade liegt direkt hier)
GAMES_BASES = (["/media/fat/games"]
              + ["/media/usb%d/games" % i for i in range(6)]
              + ["/media/usb%d" % i for i in range(6)])
ART_BASE = "/media/fat/frontend/art"       # sd-Profil (CRT)
ART_HD   = "/media/fat/frontend/art_hd"    # hd-Profil (HDMI)

# Bekannte Boot-/Test-/Demo-Dateien, die manche MiSTer-Verteilungen
# direkt in die ROM-Ordner legen (fuer den Hardware-Selbsttest) -
# identisch zur gleichnamigen Konstante im Frontend (frontend.py).
IGNORE_ROM_BASENAMES = {"boot", "boot1", "boot2", "mister-boot", "mister-demo"}

# Tags, die ein ROM als Beta/Prototyp/Demo/Hack/defekten Dump o.ae.
# kennzeichnen - werden beim Einsammeln uebersprungen (identisch zur
# gleichnamigen Konstante in frontend.py).
JUNK_TAGS = ("(beta", "(proto", "(demo", "(sample", "(unl)", "[b]",
            "(pirate", "(program", "(test", "(kiosk", "(hack")

_JAPAN_ONLY = re.compile(r"[\(\[]\s*(?:japan|j)\s*[\)\]]", re.I)

def _is_japan_only(name):
    return bool(_JAPAN_ONLY.search(name))

# syskey: (ROM-Ordner, {Endung: Cover-Quellenname})
# Der Cover-Quellenname ist der Ordnername bei thumbnails.libretro.com
# UND gleichzeitig der Systemname beim Mirror. Meist identisch fuer
# alle Endungen eines Systems - Ausnahme SMS/Game Gear (siehe v4.0-
# Changelog oben): gleicher ROM-Ordner "SMS" (wie im Frontend selbst,
# fe/systems.py), aber getrennte Cover-Quelle je nach Endung.
# WICHTIG: die syskeys UND ROM-Ordner sind bewusst exakt identisch zu
# GAME_SYSTEMS in fe/systems.py gehalten - nur Systeme, die das
# Frontend auch tatsaechlich als eigene Kategorie anzeigt, werden hier
# gelistet (siehe v4.0-Changelog, Punkt 3).
SYSTEMS = {
    "NES":     (["NES"], {
        ".nes": "Nintendo - Nintendo Entertainment System"}),
    "SNES":    (["SNES"], {
        ".sfc": "Nintendo - Super Nintendo Entertainment System",
        ".smc": "Nintendo - Super Nintendo Entertainment System"}),
    "Genesis": (["MegaDrive", "Genesis"], {
        ".md":  "Sega - Mega Drive - Genesis",
        ".gen": "Sega - Mega Drive - Genesis",
        ".bin": "Sega - Mega Drive - Genesis"}),
    "N64":     (["N64"], {
        ".n64": "Nintendo - Nintendo 64",
        ".z64": "Nintendo - Nintendo 64"}),
    "PSX":     (["PSX"], {
        ".chd": "Sony - PlayStation",
        ".cue": "Sony - PlayStation"}),
    "GAMEBOY": (["GAMEBOY"], {
        ".gb":  "Nintendo - Game Boy"}),
    "GBC":     (["GAMEBOY"], {
        ".gbc": "Nintendo - Game Boy Color"}),
    "GBA":     (["GBA"], {
        ".gba": "Nintendo - Game Boy Advance"}),
    "SMS":     (["SMS"], {
        ".sms": "Sega - Master System - Mark III",
        ".gg":  "Sega - Game Gear"}),
    "TGFX16":  (["TGFX16"], {
        ".pce": "NEC - PC Engine - TurboGrafx 16",
        ".sgx": "NEC - PC Engine - TurboGrafx 16"}),
    "MegaCD":  (["MegaCD"], {
        ".chd": "Sega - Mega-CD - Sega CD",
        ".cue": "Sega - Mega-CD - Sega CD"}),
    "Saturn":  (["Saturn"], {
        ".chd": "Sega - Saturn",
        ".cue": "Sega - Saturn"}),
    "NEOGEO":  (["NEOGEO"], {
        ".neo": "SNK - Neo Geo"}),
}

# ---------------------------------------------------------------------------
# Regions-Prioritaet (Nutzer-Rueckmeldung, siehe v4.0-Changelog Punkt 1
# oben - bewusst NICHT die im urspruenglichen Mirror-Skript verwendete
# Reihenfolge, sondern die bereits vorher aus echtem Bugreport
# korrigierte): USA/World zuerst deckt die meisten gaengigen ROM-Sets
# (No-Intro/Redump) ab, Japan/Germany hinten (nur relevant fuer
# entsprechend spezialisierte Sammlungen).
# ---------------------------------------------------------------------------
REGION_PRIORITY = ["(usa)", "(world)", "(europe)", "(japan)", "(germany)"]

def region_rank(name):
    low = name.lower()
    for i, tag in enumerate(REGION_PRIORITY):
        if tag in low:
            return i
    return len(REGION_PRIORITY)

# ---------------------------------------------------------------------------
# Namens-Matching - trigramm-vorgefiltert (schneller als ein direkter
# difflib-Abgleich gegen die komplette Liste bei grossen Sammlungen),
# unabhaengig davon, ob die Kandidatenliste .art-Dateinamen (Mirror)
# oder .png-Dateinamen (Fallback) enthaelt - beide werden vor dem
# Vergleich auf den reinen Basisnamen normiert.
# ---------------------------------------------------------------------------

BADCHARS = re.compile(r"[&*/:`<>?\\|]")
def sanitize(name): return BADCHARS.sub("_", name)
def norm(name):     return re.sub(r"[^a-z0-9]", "", name.lower())
def strip_tags(name): return re.sub(r"[\(\[][^\)\]]*[\)\]]", "", name).strip()

def build_index(cover_names):
    idx_exact, idx_strip = {}, {}
    for cn in cover_names:
        base = os.path.splitext(cn)[0]
        idx_exact.setdefault(norm(base), []).append(cn)
        idx_strip.setdefault(norm(strip_tags(base)), []).append(cn)
    return idx_exact, idx_strip

def _trigrams(s):
    if len(s) < 3:
        return {s} if s else set()
    return {s[i:i+3] for i in range(len(s) - 2)}

def build_trigram_index(idx_strip):
    tri = {}
    for key in idx_strip:
        for t in _trigrams(key):
            tri.setdefault(t, []).append(key)
    return tri

MATCH_TOPK = 60   # max. Trigramm-Kandidaten, die an difflib weitergereicht werden

def match_rom(rom_base, idx_exact, idx_strip, tri, cutoff=0.90):
    n = norm(sanitize(rom_base))
    hit = idx_exact.get(n)
    if hit:
        return sorted(hit, key=region_rank)[0], "exakt"
    ns = norm(strip_tags(sanitize(rom_base)))
    hit = idx_strip.get(ns)
    if hit:
        return sorted(hit, key=region_rank)[0], "ohne-tags"
    if len(ns) < 3:
        return None, None
    cnt = Counter()
    for t in _trigrams(ns):
        post = tri.get(t)
        if post:
            for key in post:
                cnt[key] += 1
    if not cnt:
        return None, None
    cand = [k for k, _ in cnt.most_common(MATCH_TOPK)]
    close = difflib.get_close_matches(ns, cand, n=1, cutoff=cutoff)
    if close:
        return sorted(idx_strip[close[0]], key=region_rank)[0], "aehnlich"
    return None, None

# ---------------------------------------------------------------------------
# ROM-Sammlung
# ---------------------------------------------------------------------------

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

def collect_roms(folders, ext_sysname_map):
    """Wie bisher, liefert aber (name, ext)-Paare statt nur Namen -
    die Endung wird gebraucht, um bei mehreren Cover-Quellen pro
    System (siehe SMS/Game Gear) die richtige zuzuordnen. Dedupe
    bleibt wie bisher rein namensbasiert (ohne Endung) - betrifft in
    der Praxis nur Mehrfach-Regionen DESSELBEN Spiels, nicht
    verschiedene Systeme/Endungen."""
    exts = set(ext_sysname_map)
    raw = []   # (name, ext)
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
                        raw.append((b, ext.lower()))
    best = {}
    for name, ext in raw:
        key = dedupe_key(name)
        rank = region_rank(name)
        cur = best.get(key)
        if cur is None or rank < cur[0]:
            best[key] = (rank, name, ext)
    return sorted(((name, ext) for _rank, name, ext in best.values()),
                 key=lambda t: t[0])

_CORE_DATE_SUFFIX = re.compile(r"_\d{8}[a-zA-Z]?$")

def find_arcade_folders():
    found = []
    for d in sorted(glob.glob(os.path.join(BASE, "_*"))):
        if os.path.isdir(d) and "arcade" in os.path.basename(d).lstrip("_").lower():
            found.append(d)
    return found

def collect_arcade_names():
    raw = []
    for root in find_arcade_folders():
        for dirpath, dirnames, files in os.walk(root):
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]
            for fn in files:
                if fn.lower().endswith(".mra"):
                    raw.append(_CORE_DATE_SUFFIX.sub("", os.path.splitext(fn)[0]))
    seen, result = set(), []
    for n in sorted(raw):
        if n not in seen:
            seen.add(n); result.append(n)
    return result

# ---------------------------------------------------------------------------
# Geschwindigkeits-Tracker + Fortschrittsanzeige (thread-safe)
# ---------------------------------------------------------------------------

class SpeedTracker:
    def __init__(self):
        self._lock = threading.Lock()
        self._bytes = 0; self._start = time.time(); self._window = []
        self._total_done = 0; self._total_jobs = 0
    def reset(self, total_jobs):
        with self._lock:
            self._bytes = 0; self._start = time.time(); self._window = []
            self._total_done = 0; self._total_jobs = total_jobs
    def add(self, n):
        now = time.time()
        with self._lock:
            self._bytes += n; self._window.append((now, n))
            cut = now - 5.0
            self._window = [(t, b) for t, b in self._window if t >= cut]
    def finish_one(self):
        with self._lock:
            self._total_done += 1
    def stats(self):
        now = time.time()
        with self._lock:
            done, total = self._total_done, self._total_jobs
            if self._window:
                wb = sum(b for _, b in self._window)
                el = now - self._window[0][0]
                speed = (wb / el) if el > 0.1 else 0.0
            else:
                speed = 0.0
            rem = total - done
            if speed > 0 and rem > 0:
                avg = (self._bytes / done) if done > 0 else 20000
                eta_str = _fmt_eta((avg * rem) / speed)
            else:
                eta_str = "--:--"
        return done, total, speed / (1024*1024), eta_str

_speed = SpeedTracker()

def _fmt_eta(sec):
    sec = int(sec)
    if sec < 60:   return "%ds" % sec
    if sec < 3600: return "%dm%02ds" % (sec // 60, sec % 60)
    return "%dh%02dm" % (sec // 3600, (sec % 3600) // 60)

_progress_stop = threading.Event()

def _download_progress():
    first = True
    while not _progress_stop.is_set():
        done, total, mbs, eta = _speed.stats()
        bw = 20; filled = int(bw * done / total) if total else 0
        bar = "#" * filled + "-" * (bw - filled)
        line = "  [%s] %d/%d  %.2f MB/s  ETA %s   " % (bar, done, total, mbs, eta)
        sys.stdout.write((line + "\n") if first else ("\r" + line))
        sys.stdout.flush(); first = False
        time.sleep(0.5)
    done, total, mbs, _ = _speed.stats()
    el = time.time() - _speed._start
    sys.stdout.write("\r  fertig: %d Dateien in %.1fs (%.2f MB/s)%s\n"
                     % (done, el, mbs, " " * 8))
    sys.stdout.flush()

def _match_bar(done, total, t0):
    el = time.time() - t0
    rate = done / el if el > 0 else 0.0
    pct = done * 100 // total if total else 100
    bw = 20; filled = bw * done // total if total else bw
    bar = "#" * filled + "-" * (bw - filled)
    sys.stdout.write("\r  Abgleich [%s] %d/%d (%d%%)  %.0f ROMs/s   "
                     % (bar, done, total, pct, rate))
    sys.stdout.flush()

# ---------------------------------------------------------------------------
# QUELLE 1: Mirror (schnell, fertige .art-Dateien, Klartext-HTTP,
# Keep-Alive) - siehe Modul-Docstring oben.
# ---------------------------------------------------------------------------

HTTP_HOST      = "dennsen86clips.de"
HTTP_BASE_PATH = "boxarts"
REMOTE_ART     = {"sd": "art", "hd": "art_hd"}   # muss zu art_build_mirror.py passen
DOWNLOAD_WORKERS = 6

_http_local = threading.local()

def _get_http():
    conn = getattr(_http_local, "conn", None)
    if conn is None:
        conn = http.client.HTTPConnection(HTTP_HOST, 80, timeout=30)
        _http_local.conn = conn
    return conn

_HREF_ART = re.compile(r'href="([^"?]+\.art)"', re.I)

def list_art(system, remote_dir):
    """Fertige .art per HTTP-Verzeichnisindex auflisten. Leere Liste
    bei jedem Fehler (Mirror nicht erreichbar, System dort nicht
    vorhanden usw.) - der Aufrufer faellt dann automatisch auf die
    langsamere Quelle 2 zurueck, siehe process_system_mirror()."""
    base = ("%s/" % HTTP_BASE_PATH.strip("/")) if HTTP_BASE_PATH else ""
    url  = "/" + urllib.parse.quote("%s%s/%s/" % (base, remote_dir, system))
    try:
        conn = _get_http()
        conn.request("GET", url, headers={"Connection": "keep-alive"})
        resp = conn.getresponse()
        body = resp.read()
        if resp.status != 200:
            return []
        if "text/html" not in (resp.getheader("Content-Type") or "").lower():
            return []
        names = []
        for href in _HREF_ART.findall(body.decode("utf-8", "replace")):
            fn = os.path.basename(urllib.parse.unquote(href))
            if fn.lower().endswith(".art"):
                names.append(fn)
        return names
    except Exception as e:
        _http_local.conn = None
        print("  Mirror-Listing-Fehler (%s): %s - falle auf Einzel-Quelle zurueck" % (system, e))
        return []

def download_art_http(system, remote_dir, artname, retries=3):
    base = ("%s/" % HTTP_BASE_PATH.strip("/")) if HTTP_BASE_PATH else ""
    url  = "/" + urllib.parse.quote("%s%s/%s/%s" % (base, remote_dir, system, artname))
    for attempt in range(retries):
        try:
            conn = _get_http()
            conn.request("GET", url, headers={"Connection": "keep-alive"})
            resp = conn.getresponse()
            data = resp.read()
            if resp.status == 200:
                return data
            return None
        except Exception:
            try: _get_http().close()
            except Exception: pass
            _http_local.conn = None
            if attempt == retries - 1:
                return None
            time.sleep(0.3 * (attempt + 1))
    return None

def _fetch_worker_mirror(jobs_q, sysname, remote_dir, out_dir, gesamt, lock):
    _DONE = _MIRROR_DONE
    while True:
        item = jobs_q.get()
        if item is _DONE:
            jobs_q.put(_DONE); break
        rom, art = item
        data = download_art_http(sysname, remote_dir, art)
        if data is None:
            _speed.finish_one()
            continue
        with open(os.path.join(out_dir, rom + ".art"), "wb") as f:
            f.write(data)
        _speed.add(len(data)); _speed.finish_one()
        with lock:
            gesamt["neu"] += 1

_MIRROR_DONE = object()

def process_system_mirror(syskey, roms, sysname, remote_dir, out_dir, gesamt):
    """Versucht den Mirror fuer eine Liste ROM-Namen (alle mit
    derselben Cover-Quelle 'sysname'). Liefert die Namen zurueck, die
    NICHT ueber den Mirror geloest werden konnten (Mirror hat das
    System nicht gelistet, oder einzelne ROMs ohne Treffer/Download-
    Fehler) - diese werden vom Aufrufer an process_system_fallback()
    weitergereicht, statt als endgueltig fehlend zu gelten."""
    if not roms:
        return []
    arts = list_art(sysname, remote_dir)
    if not arts:
        return list(roms)   # Mirror kennt dieses System (gerade) nicht - alles an Fallback
    idx_exact, idx_strip = build_index(arts)
    tri = build_trigram_index(idx_strip)
    print("  Mirror (%s): %d .art verfuegbar, %d ROMs abgleichen ..."
          % (sysname, len(arts), len(roms)))
    jobs, unresolved = [], []
    t1 = time.time()
    for i, rom in enumerate(roms, 1):
        art, how = match_rom(rom, idx_exact, idx_strip, tri)
        if art:
            jobs.append((rom, art))
        else:
            unresolved.append(rom)
        if i % 250 == 0 or i == len(roms):
            _match_bar(i, len(roms), t1)
    sys.stdout.write("\n")
    if not jobs:
        return unresolved

    _speed.reset(len(jobs))
    _progress_stop.clear()
    prog = threading.Thread(target=_download_progress, daemon=True)
    prog.start()

    jobs_q = queue.Queue(maxsize=DOWNLOAD_WORKERS * 4)
    lock = threading.Lock()
    threads = []
    before_ok = {"neu": gesamt.get("neu", 0)}
    got_names = set()
    lock2 = threading.Lock()

    def _worker():
        while True:
            item = jobs_q.get()
            if item is _MIRROR_DONE:
                jobs_q.put(_MIRROR_DONE); break
            rom, art = item
            data = download_art_http(sysname, remote_dir, art)
            if data is None:
                _speed.finish_one()
                with lock2:
                    unresolved.append(rom)
                continue
            with open(os.path.join(out_dir, rom + ".art"), "wb") as f:
                f.write(data)
            _speed.add(len(data)); _speed.finish_one()
            with lock2:
                got_names.add(rom)
            with lock:
                gesamt["neu"] += 1

    for _ in range(DOWNLOAD_WORKERS):
        t = threading.Thread(target=_worker, daemon=True)
        t.start(); threads.append(t)
    for job in jobs:
        jobs_q.put(job)
    jobs_q.put(_MIRROR_DONE)
    for t in threads:
        t.join()
    _progress_stop.set(); prog.join()

    return unresolved

# ---------------------------------------------------------------------------
# QUELLE 2: Fallback (langsamer, dekodiert selbst) - unveraendert der
# bisherige Weg dieses Skripts, siehe Modul-Docstring.
# ---------------------------------------------------------------------------

LIBRETRO_BASE = "https://thumbnails.libretro.com"
GITHUB_RAW    = "https://raw.githubusercontent.com/libretro-thumbnails"
GITHUB_API    = "https://api.github.com/repos/libretro-thumbnails"
UA = {"User-Agent": "MiSTer-Frontend-Boxart/1.0"}

PANEL_BG = (28, 32, 44)   # C_PANEL des Frontends

class PngError(Exception):
    pass

def decode_png(data):
    """PNG -> (breite, hoehe, RGB-Bytes). Wirft PngError bei Exoten."""
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise PngError("kein PNG")
    pos = 8
    idat = []
    plte = trns = None
    w = h = None
    while pos + 8 <= len(data):
        ln  = int.from_bytes(data[pos:pos+4], "big")
        typ = data[pos+4:pos+8]
        chunk = data[pos+8:pos+8+ln]
        pos += 12 + ln
        if typ == b"IHDR":
            w, h, bd, ct, comp, filt, inter = struct.unpack(">IIBBBBB", chunk)
            if bd != 8:
                raise PngError("Bittiefe %d" % bd)
            if inter != 0:
                raise PngError("interlaced")
            if ct not in (0, 2, 3, 4, 6):
                raise PngError("Farbtyp %d" % ct)
        elif typ == b"PLTE":
            plte = chunk
        elif typ == b"tRNS":
            trns = chunk
        elif typ == b"IDAT":
            idat.append(chunk)
        elif typ == b"IEND":
            break
    if w is None or not idat:
        raise PngError("unvollstaendig")

    ch = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[ct]
    raw = zlib.decompress(b"".join(idat))
    del idat
    pix = _unfilter(raw, w, h, ch)
    del raw

    bg_r, bg_g, bg_b = PANEL_BG
    if ct == 2:
        return w, h, bytes(pix)
    out = bytearray(w * h * 3)
    if ct == 0:                                     # Graustufen
        for i in range(w * h):
            v = pix[i]
            out[3*i] = out[3*i+1] = out[3*i+2] = v
    elif ct == 3:                                   # Palette
        if plte is None:
            raise PngError("Palette fehlt")
        alpha = trns or b""
        for i in range(w * h):
            p = pix[i]
            r, g, b = plte[3*p], plte[3*p+1], plte[3*p+2]
            a = alpha[p] if p < len(alpha) else 255
            if a < 255:
                r = (r*a + bg_r*(255-a)) // 255
                g = (g*a + bg_g*(255-a)) // 255
                b = (b*a + bg_b*(255-a)) // 255
            out[3*i], out[3*i+1], out[3*i+2] = r, g, b
    elif ct == 4:                                   # Grau + Alpha
        for i in range(w * h):
            v, a = pix[2*i], pix[2*i+1]
            if a < 255:
                r = (v*a + bg_r*(255-a)) // 255
                g = (v*a + bg_g*(255-a)) // 255
                b = (v*a + bg_b*(255-a)) // 255
            else:
                r = g = b = v
            out[3*i], out[3*i+1], out[3*i+2] = r, g, b
    else:                                           # ct == 6, RGBA
        for i in range(w * h):
            r, g, b, a = pix[4*i], pix[4*i+1], pix[4*i+2], pix[4*i+3]
            if a < 255:
                r = (r*a + bg_r*(255-a)) // 255
                g = (g*a + bg_g*(255-a)) // 255
                b = (b*a + bg_b*(255-a)) // 255
            out[3*i], out[3*i+1], out[3*i+2] = r, g, b
    return w, h, bytes(out)

def _unfilter(raw, w, h, ch):
    """PNG-Zeilenfilter rueckrechnen (Typen 0-4)."""
    stride = w * ch
    out = bytearray(h * stride)
    prev = bytes(stride)
    pos = 0
    for y in range(h):
        f = raw[pos]; pos += 1
        line = bytearray(raw[pos:pos+stride]); pos += stride
        if f == 0:
            pass
        elif f == 1:                                # Sub
            for i in range(ch, stride):
                line[i] = (line[i] + line[i-ch]) & 255
        elif f == 2:                                # Up
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 255
        elif f == 3:                                # Average
            for i in range(ch):
                line[i] = (line[i] + (prev[i] >> 1)) & 255
            for i in range(ch, stride):
                line[i] = (line[i] + ((line[i-ch] + prev[i]) >> 1)) & 255
        elif f == 4:                                # Paeth
            for i in range(ch):
                line[i] = (line[i] + prev[i]) & 255
            for i in range(ch, stride):
                a = line[i-ch]; b = prev[i]; c = prev[i-ch]
                p = a + b - c
                pa = p - a if p >= a else a - p
                pb = p - b if p >= b else b - p
                pc = p - c if p >= c else c - p
                if pa <= pb and pa <= pc:
                    pr = a
                elif pb <= pc:
                    pr = b
                else:
                    pr = c
                line[i] = (line[i] + pr) & 255
        else:
            raise PngError("Filter %d" % f)
        out[y*stride:(y+1)*stride] = line
        prev = line
    return out

def scale_to_box(w, h, rgb, max_w, max_h):
    """Nearest-Neighbor-Skalierung in die Begrenzungsbox."""
    scale = min(max_w / w, max_h / h, 1.0)
    tw = max(1, round(w * scale))
    th = max(1, round(h * scale))
    xmap = [min(w - 1, int(x * w / tw)) * 3 for x in range(tw)]
    out = bytearray(tw * th * 3)
    for ty in range(th):
        sy = min(h - 1, int(ty * h / th))
        row = rgb[sy*w*3:(sy+1)*w*3]
        o = ty * tw * 3
        for tx in range(tw):
            s = xmap[tx]
            out[o]   = row[s]
            out[o+1] = row[s+1]
            out[o+2] = row[s+2]
            o += 3
    return tw, th, bytes(out)

def rgb_to_art(w, h, rgb):
    """RGB -> .art-Datei-Bytes (BGRA + zlib)."""
    pix = bytearray(w * h * 4)
    pix[0::4] = rgb[2::3]
    pix[1::4] = rgb[1::3]
    pix[2::4] = rgb[0::3]
    return b"ART1" + struct.pack("<HH", w, h) + zlib.compress(bytes(pix), 6)

_ssl_ctx = None

def http_get(url, timeout=45):
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

def list_covers(sysname):
    url = "%s/%s/Named_Boxarts/" % (LIBRETRO_BASE,
                                    urllib.parse.quote(sysname))
    try:
        data = http_get(url).decode("utf-8", "replace")
        names = re.findall(r'href="([^"]+\.png)"', data)
        names = [html.unescape(urllib.parse.unquote(n)) for n in names
                if not n.startswith("http")]
        if names:
            return names, "thumbnails.libretro.com"
    except Exception as e:
        err1 = e
    try:
        repo = sysname.replace(" ", "_")
        url = "%s/%s/git/trees/master?recursive=1" % (GITHUB_API, repo)
        tree = json.loads(http_get(url))
        names = [os.path.basename(e["path"]) for e in tree.get("tree", [])
                if e["path"].startswith("Named_Boxarts/")
                and e["path"].endswith(".png")]
        return names, "GitHub"
    except Exception as e:
        print("  Coverliste nicht abrufbar (%s): %s / %s" % (sysname, err1, e))
        return [], None

def download_cover(sysname, covername):
    urls = [
        "%s/%s/Named_Boxarts/%s" % (LIBRETRO_BASE,
            urllib.parse.quote(sysname), urllib.parse.quote(covername)),
        "%s/%s/master/Named_Boxarts/%s" % (GITHUB_RAW,
            sysname.replace(" ", "_"), urllib.parse.quote(covername)),
    ]
    for url in urls:
        try:
            return http_get(url, timeout=90)
        except Exception:
            continue
    return None

PROFILES = {"sd": (104, 168), "hd": (300, 350)}   # nur fuer den Fallback-Pfad
                                                  # gebraucht - der Mirror liefert
                                                  # bereits fertig skalierte .art

CONVERT_WORKERS = 2   # bewusst KLEIN (nicht DOWNLOAD_WORKERS) - der
                      # eigentliche Engpass ist Spitzenspeicher-
                      # verbrauch waehrend reiner Python-Pixelarbeit,
                      # nicht Netzwerk-Wartezeit (siehe Nutzer-
                      # Rueckmeldung zu Abstuerzen in frueherer Version)
_convert_semaphore = threading.Semaphore(CONVERT_WORKERS)

def process_one_rom_fallback(rom, sysname, idx_exact, idx_strip, tri, out_dir, box):
    cover, how = match_rom(rom, idx_exact, idx_strip, tri)
    if not cover:
        return (rom, "missing", None)
    png = download_cover(sysname, cover)
    if not png:
        return (rom, "dl_failed", cover)
    with _convert_semaphore:
        try:
            w, h, rgb = decode_png(png)
            tw, th, small = scale_to_box(w, h, rgb, box[0], box[1])
            art = rgb_to_art(tw, th, small)
            with open(os.path.join(out_dir, rom + ".art"), "wb") as f:
                f.write(art)
            return (rom, "ok", (how, cover))
        except PngError as e:
            return (rom, "png_error", str(e))

def process_system_fallback(syskey, roms, sysname, out_dir, box, gesamt):
    """Der bisherige, langsame Weg (dekodiert selbst) - wird nur fuer
    die ROMs aufgerufen, die process_system_mirror() nicht loesen
    konnte."""
    if not roms:
        return []
    print("  Fallback (%s): %d ROMs ueber thumbnails.libretro.com ..." % (sysname, len(roms)))
    covers, quelle = list_covers(sysname)
    if not covers:
        return list(roms)
    print("    %d Cover verfuegbar (%s)" % (len(covers), quelle))
    idx_exact, idx_strip = build_index(covers)
    tri = build_trigram_index(idx_strip)

    missing = []
    done = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=DOWNLOAD_WORKERS) as executor:
        futures = {
            executor.submit(process_one_rom_fallback, rom, sysname, idx_exact,
                           idx_strip, tri, out_dir, box): rom
            for rom in roms
        }
        try:
            for future in concurrent.futures.as_completed(futures):
                rom = futures[future]
                done += 1
                try:
                    _, status, info = future.result()
                except Exception as e:
                    status, info = "error", str(e)
                if status == "ok":
                    gesamt["neu"] += 1
                    how, cover = info
                    note = "" if how == "exakt" else "  [%s: %s]" % (how, cover)
                    print("    [%3d/%3d] %s%s" % (done, len(roms), rom, note))
                else:
                    missing.append(rom)
        except KeyboardInterrupt:
            print("\nAbgebrochen - breche laufende Downloads ab...")
            executor.shutdown(wait=False, cancel_futures=True)
            raise
    return missing

def _write_missing(art_base, syskey, missing):
    if missing:
        mf = os.path.join(art_base, "fehlend_%s.txt" % syskey)
        with open(mf, "w") as f:
            f.write("\n".join(sorted(set(missing))))
        print("  %d ohne Cover -> %s" % (len(set(missing)), mf))

# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def process_system(syskey, roms, ext_sysname_map, art_base, remote_dir, box, gesamt):
    """Ein System komplett abarbeiten: erst der Mirror (gruppiert nach
    Cover-Quelle je Endung, siehe SMS/Game Gear), fuer alles ungeloeste
    danach automatisch der Fallback - beides schreibt in denselben
    out_dir, damit das Frontend (das nur den syskey-Ordner kennt,
    keinen Unterschied zwischen den Quellen macht) beides gleich
    findet."""
    if not roms:
        return
    out_dir = os.path.join(art_base, syskey)
    os.makedirs(out_dir, exist_ok=True)

    todo = [(name, ext) for name, ext in roms
            if not os.path.exists(os.path.join(out_dir, name + ".art"))]
    gesamt["roms"] += len(roms)
    gesamt["vorhanden"] += len(roms) - len(todo)
    print("== %s: %d Eintraege, %d ohne .art" % (syskey, len(roms), len(todo)))
    if not todo:
        return

    by_sysname = {}
    for name, ext in todo:
        by_sysname.setdefault(ext_sysname_map.get(ext, syskey), []).append(name)

    still_missing = []
    for sysname, names in by_sysname.items():
        still_missing.extend(
            (n, sysname) for n in
            process_system_mirror(syskey, names, sysname, remote_dir, out_dir, gesamt))

    if still_missing:
        print("  %d nicht ueber den Mirror gefunden - Rueckfall auf Einzel-Download ..."
              % len(still_missing))
        fb_by_sysname = {}
        for n, sn in still_missing:
            fb_by_sysname.setdefault(sn, []).append(n)
        final_missing = []
        for sysname, names in fb_by_sysname.items():
            final_missing.extend(
                process_system_fallback(syskey, names, sysname, out_dir, box, gesamt))
        gesamt["fehlend"] += len(final_missing)
        _write_missing(art_base, syskey, final_missing)

def main():
    args = list(sys.argv[1:])
    profile = "sd"
    if args and args[0] in ("sd", "hd"):
        profile = args.pop(0)
    only = set(args) if args else None

    art_base   = ART_HD if profile == "hd" else ART_BASE
    remote_dir = REMOTE_ART[profile]
    box        = PROFILES[profile]
    print("Profil: %s -> %s (Mirror-Ordner '%s')" % (profile, art_base, remote_dir))

    try:
        c = http.client.HTTPConnection(HTTP_HOST, 80, timeout=15)
        c.request("HEAD", "/"); c.getresponse().read(); c.close()
        print("Mirror erreichbar (%s)" % HTTP_HOST)
    except Exception as e:
        print("Mirror gerade nicht erreichbar (%s) - laeuft komplett ueber den "
              "langsameren Fallback (thumbnails.libretro.com)." % e)

    gesamt  = {"roms": 0, "neu": 0, "vorhanden": 0, "fehlend": 0}
    t_start = time.time()

    for syskey, (folders, ext_sysname_map) in SYSTEMS.items():
        if only and syskey not in only:
            continue
        process_system(syskey, collect_roms(folders, ext_sysname_map),
                       ext_sysname_map, art_base, remote_dir, box, gesamt)

    if not only or "ARCADE" in only:
        arcade_names = collect_arcade_names()
        if arcade_names:
            process_system("ARCADE", [(n, ".mra") for n in arcade_names],
                           {".mra": "MAME"}, art_base, remote_dir, box, gesamt)
        elif not find_arcade_folders():
            print("== ARCADE: kein _Arcade-Ordner gefunden, uebersprungen")

    mins = (time.time() - t_start) / 60
    print("\nFertig: %(roms)d ROMs, %(neu)d neu, %(vorhanden)d vorhanden, "
          "%(fehlend)d ohne Cover" % gesamt)
    print("Gesamtzeit: %.1f Minuten" % mins)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAbgebrochen - beim naechsten Start geht es dort weiter.")
