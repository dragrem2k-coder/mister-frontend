#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mister_boxart.py - Boxart-Downloader, laeuft DIREKT AUF DEM MISTER
===================================================================
v1.1
Keine Abhaengigkeiten - nur Python-Standardbibliothek.

Versionshistorie:
  v1.1 - collect_roms() ohne Tiefenbegrenzung (vorher max. 2 Ordner-
         ebenen "wie im Frontend") - beliebig tief sortierte ROM-
         Ordner werden jetzt vollstaendig durchsucht. Neu:
         IGNORE_ROM_BASENAMES ueberspringt bekannte Boot-/Test-/Demo-
         Dateien (boot.rom, boot1.rom, boot2.rom, mister-boot.*,
         mister-demo.*), die manche MiSTer-Verteilungen direkt in die
         ROM-Ordner legen und die sonst faelschlich gegen die Boxart-
         Datenbank gematcht wuerden.
  v1.0 - Erste Version.

Das Skript:
  1. liest die ROMs aus /media/fat/games/<System>/
  2. holt die Coverlisten von thumbnails.libretro.com
     (Fallback: GitHub), gleicht die Namen ab
     (exakt -> normalisiert -> ohne Tags -> Aehnlichkeit,
      Regions-Prioritaet: Germany > Europe > World > USA > Japan)
  3. laedt die Treffer und dekodiert die PNGs in reinem Python
  4. schreibt fertige .art-Dateien nach /media/fat/frontend/art/

Aufruf (SSH oder ueber die Scripts-Kategorie des Frontends):
  python3 /media/fat/frontend/mister_boxart.py            # alle Systeme, CRT-Profil
  python3 /media/fat/frontend/mister_boxart.py hd         # 1080p-Profil
  python3 /media/fat/frontend/mister_boxart.py sd SNES NES  # nur bestimmte Systeme

Bereits vorhandene .art-Dateien werden uebersprungen - das Skript
kann jederzeit abgebrochen (Strg+C) und spaeter fortgesetzt werden.
Hinweis: Die PNG-Dekodierung in reinem Python braucht ein paar
Sekunden pro Bild. Grosse Sammlungen laufen am besten ueber Nacht.
"""

import re, difflib, glob, html, json, os, ssl, struct, sys, threading, time, zlib
import urllib.request, urllib.parse
import concurrent.futures

BASE = "/media/fat"   # fuer die Arcade-Ordnersuche (_Arcade liegt direkt hier)
GAMES_BASES = (["/media/fat/games"]
               + ["/media/usb%d/games" % i for i in range(6)]
               + ["/media/usb%d" % i for i in range(6)])
ART_BASE   = "/media/fat/frontend/art"      # sd-Profil (CRT)
ART_HD     = "/media/fat/frontend/art_hd"   # hd-Profil (HDMI)

# Bekannte Boot-/Test-/Demo-Dateien, die manche MiSTer-Verteilungen
# direkt in die ROM-Ordner legen (fuer den Hardware-Selbsttest). Haben
# zufaellig die richtige Endung und wuerden sonst versucht werden, wie
# ein echtes Spiel gegen die Boxart-Datenbank zu matchen. Identisch zur
# gleichnamigen Konstante im Frontend (frontend.py).
IGNORE_ROM_BASENAMES = {"boot", "boot1", "boot2", "mister-boot", "mister-demo"}

# Tags, die ein ROM als Beta/Prototyp/Demo/Hack/defekten Dump o.ae.
# kennzeichnen - werden beim Einsammeln uebersprungen, spart Zeit und
# Traffic fuer Dateien, die im Frontend ohnehin ausgefiltert werden
# (identisch zur gleichnamigen Konstante in frontend.py).
JUNK_TAGS = ("(beta", "(proto", "(demo", "(sample", "(unl)", "[b]",
            "(pirate", "(program", "(test", "(kiosk", "(hack")

# Rein japanische ROMs ausblenden (identisch zur gleichnamigen Logik
# in frontend.py) - Mehrfach-Region-Tags wie "(Japan, USA)" bleiben
# erhalten, da diese Version auch USA/Europa abdeckt.
_JAPAN_ONLY = re.compile(r"[\(\[]\s*(?:japan|j)\s*[\)\]]", re.I)

def _is_japan_only(name):
    return bool(_JAPAN_ONLY.search(name))

# syskey: (ROM-Ordner, ROM-Endungen, libretro-Thumbnail-Name)
# Wichtig: GAMEBOY und GBC teilen sich den Ordner "GAMEBOY", werden aber
# ueber die Endung getrennt (.gb vs .gbc) - sonst wuerde jedes GBC-Spiel
# doppelt geladen und dekodiert. Die syskeys sind identisch zu denen im
# Frontend, damit die .art-Ordner gefunden werden.
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

# NEU (Nutzer-Rueckmeldung: "Scrollen im HDMI-Modus fuehlt sich nicht
# fluessig an" - per echter Hardware-Diagnose bestaetigt: die 360x420-
# HD-Cover wurden bei typischen 1080p-Boxgroessen NIE tatsaechlich
# hochskaliert (Skalierungsfaktor blieb bei 1x, siehe get_scaled() in
# fe/art.py), das Bild sass nur mit ungenutztem Rand in der Box - die
# gemessenen 26-28ms pro neu geladenem Cover waren dabei GANZ ueberwiegend
# reine Lesezeit von der SD-Karte, nicht Rechenarbeit (Vergleichsmessung
# in einer schnellen Umgebung: unter 3ms fuer dieselbe Entpack-Arbeit).
# 300x350 (69% der bisherigen Pixelzahl, gleiches 6:7-Seitenverhaeltnis)
# reduziert die zu lesende Datenmenge SPUERBAR, UND trifft bei ueblichen
# 1080p-Boxgroessen zufaellig genau den Sprung auf Skalierungsfaktor 2x -
# damit wird die Box tatsaechlich BESSER ausgefuellt als vorher (86%/96%
# statt 52%/58%), nicht nur schneller geladen. Betrifft AUSSCHLIESSLICH
# neu erzeugte .art-Dateien - bereits vorhandene werden von diesem
# Skript uebersprungen (siehe Docstring oben), muessen also fuer den
# Effekt einmalig geloescht und neu erzeugt werden.
# NEU (Nutzerfrage: "sollte die Boxart auf CRT nicht aggressiver, z.B.
# 240x280, sein?"): NACHGERECHNET statt geraten - das tatsaechliche
# Boxart-Panel im CRT-Layout (320x240, siehe layout_items()/draw_art_panel())
# ist rechnerisch NIE breiter als ~101px und NIE hoeher als ~165px (obere
# Kappung bei 85% der Panel-Hoehe, siehe cover_h-Berechnung dort) - selbst
# im guenstigsten Fall (gar kein Text darunter). 240x280 waere also mehr
# als das Doppelte dessen, was auf dem CRT-Bildschirm je zu sehen ist: die
# Datei wuerde beim Zeichnen ohnehin wieder auf ~101x165 herunterskaliert
# (siehe get_scaled() in fe/art.py) - keine sichtbare Verbesserung, aber
# spuerbar mehr Lesezeit von der SD-Karte UND mehr Rechenarbeit beim
# Skalieren pro NEU geladenem Cover (genau der Kostenfaktor, der oben bei
# der HD-Reduzierung von 360x420 auf 300x350 schon einmal gemessen wurde -
# hier in die andere Richtung). Die bisherigen 100x120 waren dagegen in der
# Breite schon fast exakt richtig, aber in der Hoehe (120 statt bis zu 165)
# zu knapp bemessen - das ist der tatsaechliche Rest-Verbesserungsspielraum,
# den 100x120 noch liegen liess: 104x168 deckt den rechnerischen Maximalfall
# jetzt mit etwas Marge ab, ohne unnoetig ueber den CRT-Bildschirm hinaus
# aufzuloesen.
PROFILES = {"sd": (104, 168), "hd": (300, 350)}

LIBRETRO_BASE = "https://thumbnails.libretro.com"
GITHUB_RAW    = "https://raw.githubusercontent.com/libretro-thumbnails"
GITHUB_API    = "https://api.github.com/repos/libretro-thumbnails"
UA = {"User-Agent": "MiSTer-Frontend-Boxart/1.0"}

# ---------------------------------------------------------------------------
# PNG-Dekoder (reine Standardbibliothek), validiert gegen Pillow
# ---------------------------------------------------------------------------


PANEL_BG = (28, 32, 44)          # C_PANEL des Frontends

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
    # BUGFIX (Nutzer-Rueckmeldung zu Abstuerzen beim Konvertieren, siehe
    # CONVERT_WORKERS/_convert_semaphore in mister_boxart.py): idat wird
    # ab hier nicht mehr gebraucht (schon zu raw entpackt) - frueh
    # freigeben statt bis zum Funktionsende mitzuschleppen, spart auf
    # einem speicherknappen Geraet zusaetzlich zur Parallelitaets-
    # Drosselung noch etwas Spitzenlast pro einzelnem Dekodiervorgang.
    del idat
    pix = _unfilter(raw, w, h, ch)
    # raw wird ab hier ebenfalls nicht mehr gebraucht (schon zu pix
    # entfiltert) - aus demselben Grund frueh freigeben.
    del raw

    # In RGB wandeln
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


# ---------------------------------------------------------------------------
# HTTP (mit SSL-Fallback, falls dem MiSTer CA-Zertifikate fehlen)
# ---------------------------------------------------------------------------

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

# ---------------------------------------------------------------------------
# Namens-Matching (identisch zur PC-Version)
# ---------------------------------------------------------------------------

BADCHARS = re.compile(r"[&*/:`<>?\\|]")

def sanitize(name):
    return BADCHARS.sub("_", name)

def norm(name):
    return re.sub(r"[^a-z0-9]", "", name.lower())

def strip_tags(name):
    return re.sub(r"[\(\[][^\)\]]*[\)\]]", "", name).strip()

# BUGFIX (Nutzer-Rueckmeldung: "Scrollen im HDMI-Modus fuehlt sich
# schlecht an" - bei der Fehlersuche gefunden: das Frontend suchte
# nach 'Addams Family, The (USA)', gefunden wurde aber nur 'Addams
# Family, The (Europe) (En,Fr,De).art' - eine ROM/Cover-Region-
# Verwechslung, KEINE fehlende Datei). Ursache: wenn der EXAKTE Name
# (inklusive Region-Tag) keine Cover-Entsprechung findet, greift der
# "ohne-tags"-Rueckfall in match_rom() weiter unten - der entfernt
# testweise ALLE Klammer-Tags (auch die Region) und sucht danach
# erneut. Bei MEHREREN passenden Cover-Kandidaten verschiedener
# Regionen entschied bisher diese Prioritaetsliste, welche gewinnt -
# und die stellte Germany/Europe/World bisher VOR USA. Fuer eine
# ueberwiegend USA-getaggte ROM-Sammlung (weit verbreiteter
# Normalfall bei No-Intro/Redump-Sets) fuehrte das systematisch dazu,
# dass viele USA-ROMs faelschlich europaeische Cover zugeordnet
# bekamen, sobald keine exakte USA-Datei in der Quelle vorhanden war -
# nicht nur bei einzelnen Spielen, sondern bei einem grossen Teil der
# Sammlung, was das durchgaengig "unrunde" Scroll-Gefuehl erklaert
# (staendiger SD-Rueckfall statt eines einzigen, echten Treffers).
# USA/World jetzt bewusst vorne (deckt die meisten gaengigen ROM-Sets
# ab), Japan/Germany hinten (nur relevant fuer entsprechend
# spezialisierte Sammlungen). Bei Bedarf hier direkt anpassen, falls
# die eigene ROM-Sammlung ueberwiegend eine andere Region nutzt (z.B.
# reine PAL/Europe-Sammlung) - eine Kommandozeilen-Option war fuer
# diesen Fix bewusst nicht der Ansatz, um die Aenderung einfach und
# gut nachvollziehbar zu halten.
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
    n = norm(sanitize(rom_base))
    if n in idx_exact:
        return sorted(idx_exact[n], key=region_rank)[0], "exakt"
    ns = norm(strip_tags(sanitize(rom_base)))
    if ns in idx_strip:
        return sorted(idx_strip[ns], key=region_rank)[0], "ohne-tags"
    close = difflib.get_close_matches(ns, all_norms, n=1, cutoff=0.90)
    if close:
        return sorted(idx_strip[close[0]], key=region_rank)[0], "aehnlich"
    return None, None

# ---------------------------------------------------------------------------
# Coverlisten + Download
# ---------------------------------------------------------------------------

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
        print("  Coverliste nicht abrufbar: %s / %s" % (err1, e))
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
    damit sie nicht versehentlich gegen die Boxart-Datenbank
    gematcht werden.

    Seit v1.2 zusaetzlich: bekannte Beta/Proto/Demo/Hack/Bad-Dump-Tags
    (JUNK_TAGS) werden uebersprungen, und Mehrfach-Regionen desselben
    Spiels werden zu EINER Kopie zusammengefasst (beste Region gewinnt,
    region_rank) - identisch zur Dedupe-Logik im Frontend
    (frontend.py), damit fuer Mehrfach-Region-Sets nicht unnoetig
    mehrfach dieselbe Boxart heruntergeladen wird."""
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

# Datum-Suffix, das MiSTer-Updater an manche RBF/MRA-Dateien anhaengt
# (z.B. "Pac-Man_20230115.mra") - identisch zu scan_cores() im
# Frontend selbst (frontend.py), damit der hier verwendete Name exakt
# dem entspricht, unter dem das Frontend spaeter nach dem Cover sucht.
_CORE_DATE_SUFFIX = re.compile(r"_\d{8}[a-zA-Z]?$")

def find_arcade_folders():
    """Alle /media/fat/_*-Ordner, deren Name 'arcade' enthaelt - exakt
    dieselbe Erkennung wie scan_cores() im Frontend, damit hier
    gefundene und dort erwartete Ordner uebereinstimmen."""
    found = []
    for d in sorted(glob.glob(os.path.join(BASE, "_*"))):
        if not os.path.isdir(d):
            continue
        base = os.path.basename(d).lstrip("_").lower()
        if "arcade" in base:
            found.append(d)
    return found

def collect_arcade_names():
    """Wie collect_roms(), aber fuer Arcade: sammelt .mra-Dateinamen
    (ohne Endung, ohne das Datum-Suffix) statt ROM-Dateien mit fester
    Endungsliste - der MRA-Dateiname ist bei MiSTer-Arcade-Sammlungen
    ueblicherweise bereits der Spieletitel, genau das, was auch das
    Frontend selbst als Anzeigename verwendet (siehe scan_cores())."""
    raw = []
    for root in find_arcade_folders():
        for dirpath, dirnames, files in os.walk(root):
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]
            for fn in files:
                if not fn.lower().endswith(".mra"):
                    continue
                name = os.path.splitext(fn)[0]
                name = _CORE_DATE_SUFFIX.sub("", name)
                raw.append(name)
    seen = set()
    result = []
    for n in sorted(raw):
        if n not in seen:
            seen.add(n)
            result.append(n)
    return result

# BUGFIX (Nutzer-Rueckmeldung: "Konvertieren der Boxarts bringt den
# MiSTer an seine Grenzen, hab jetzt einige Abstuerze gehabt" -
# aufgetreten NACHDEM die Download-Geschwindigkeit erhoeht wurde):
# decode_png() weiter unten entfaltet PNGs in reinem Python, pixel-
# weise (siehe dortige Kommentare) - bei DOWNLOAD_WORKERS gleich-
# zeitigen process_one_rom()-Aufrufen liefen bisher bis zu genauso
# viele Dekodier-/Skalier-/Konvertier-Vorgaenge parallel, jeder mit
# mehreren vollen Bildpuffern im Speicher (entpackte PNG-Rohdaten +
# entfilterte Pixel + RGB-Ausgabe). Da Pythons GIL bei reinem
# Python-Code ohnehin keine echte CPU-Parallelitaet erlaubt (nur
# EIN Thread fuehrt zu einem Zeitpunkt Python-Bytecode aus), brachte
# die hohe Parallelitaet dort keinen Geschwindigkeitsgewinn - nur
# mehrfachen Speicherbedarf gleichzeitig, auf einem Geraet mit
# begrenztem RAM.
#
# Fix: die Download-Parallelitaet (echter Nutzen, da Netzwerk-I/O
# das GIL freigibt) bleibt bei DOWNLOAD_WORKERS unveraendert - NUR
# der teure Dekodier-/Konvertier-Teil wird zusaetzlich durch einen
# Semaphor auf CONVERT_WORKERS gleichzeitige Vorgaenge begrenzt.
# Andere Threads koennen waehrenddessen weiter downloaden (kein
# Two-Phase-Split noetig, der die Ueberlappung von Download und
# Konvertierung zunichte gemacht haette) - nur das Betreten des
# Dekodier-Abschnitts selbst wird gedrosselt.
CONVERT_WORKERS = 2   # bewusst KLEIN (nicht DOWNLOAD_WORKERS) - der
                      # eigentliche Engpass ist Spitzenspeicher-
                      # verbrauch waehrend reiner Python-Pixelarbeit,
                      # nicht Netzwerk-Wartezeit
_convert_semaphore = threading.Semaphore(CONVERT_WORKERS)

def process_one_rom(rom, sysname, idx_exact, idx_strip, all_norms,
                    out_dir, box):
    """Ein einzelnes ROM verarbeiten: Cover suchen, herunterladen,
    skalieren, speichern. Nebenwirkungsfrei bis auf das Schreiben der
    eigenen Ausgabedatei (jedes ROM schreibt eine andere Datei) -
    sicher aus mehreren Threads gleichzeitig aufrufbar.

    Download (I/O-gebunden) laeuft mit voller Thread-Parallelitaet;
    der Dekodier-/Skalier-/Konvertier-Teil (CPU-gebunden, siehe
    CONVERT_WORKERS oben) ist zusaetzlich ueber einen Semaphor
    gedrosselt, um Speicherspitzen auf schwacher Hardware zu
    vermeiden."""
    cover, how = match_rom(rom, idx_exact, idx_strip, all_norms)
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

DOWNLOAD_WORKERS = 6   # gleichzeitige Downloads - genug fuer spuerbare
                       # Beschleunigung, ohne den Server zu ueberlasten

def main():
    args = [a for a in sys.argv[1:]]
    profile = "sd"
    if args and args[0] in PROFILES:
        profile = args.pop(0)
    only = set(args) if args else None
    box = PROFILES[profile]
    art_base = ART_HD if profile == "hd" else ART_BASE
    print("Profil: %s (max %dx%d Pixel) -> %s"
          % (profile, box[0], box[1], art_base))

    gesamt = {"roms": 0, "neu": 0, "vorhanden": 0, "fehlend": 0}
    t_start = time.time()
    def process_system(syskey, roms, sysname):
        """Ein System komplett abarbeiten (Cover suchen, herunterladen,
        speichern) - fuer normale ROM-Systeme UND fuer Arcade (dort
        roms = MRA-Dateinamen statt ROM-Dateinamen, sysname='MAME')
        identisch nutzbar, da ab hier alles nur noch mit Namen und dem
        libretro-thumbnails-Repo-Namen arbeitet."""
        if not roms:
            return
        out_dir = os.path.join(art_base, syskey)
        os.makedirs(out_dir, exist_ok=True)

        todo = [r for r in roms
                if not os.path.exists(os.path.join(out_dir, r + ".art"))]
        gesamt["roms"] += len(roms)
        gesamt["vorhanden"] += len(roms) - len(todo)
        print("== %s: %d Eintraege, %d ohne .art" % (syskey, len(roms), len(todo)))
        if not todo:
            return

        covers, quelle = list_covers(sysname)
        if not covers:
            gesamt["fehlend"] += len(todo)
            return
        print("  %d Cover verfuegbar (%s)" % (len(covers), quelle))
        idx_exact, idx_strip = build_index(covers)
        all_norms = list(idx_strip.keys())

        missing = []
        done = 0
        with concurrent.futures.ThreadPoolExecutor(
                max_workers=DOWNLOAD_WORKERS) as executor:
            futures = {
                executor.submit(process_one_rom, rom, sysname, idx_exact,
                               idx_strip, all_norms, out_dir, box): rom
                for rom in todo
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
                        print("  [%3d/%3d] %s%s" % (done, len(todo), rom, note))
                    elif status == "missing":
                        missing.append(rom)
                        gesamt["fehlend"] += 1
                    elif status == "png_error":
                        print("  [%3d/%3d] PNG nicht dekodierbar (%s): %s"
                              % (done, len(todo), info, rom))
                        missing.append(rom)
                        gesamt["fehlend"] += 1
                    else:
                        print("  [%3d/%3d] Fehlgeschlagen: %s" % (done, len(todo), rom))
                        missing.append(rom)
                        gesamt["fehlend"] += 1
            except KeyboardInterrupt:
                print("\nAbgebrochen - breche laufende Downloads ab...")
                executor.shutdown(wait=False, cancel_futures=True)
                raise

        if missing:
            mf = os.path.join(art_base, "fehlend_%s.txt" % syskey)
            with open(mf, "w") as f:
                f.write("\n".join(missing))
            print("  %d ohne Cover -> %s" % (len(missing), mf))

    for syskey, (folders, exts, sysname) in SYSTEMS.items():
        if only and syskey not in only:
            continue
        process_system(syskey, collect_roms(folders, exts), sysname)

    # Arcade separat: MRA-Dateinamen statt ROM-Dateien mit fester
    # Endungsliste, Cover kommen aus libretro-thumbnails/MAME (dieselbe
    # Named_Boxarts-Konvention wie bei allen anderen Systemen, deshalb
    # funktionieren list_covers()/download_cover()/match_rom() unveraendert).
    if not only or "ARCADE" in only:
        arcade_names = collect_arcade_names()
        if arcade_names:
            process_system("ARCADE", arcade_names, "MAME")
        elif not find_arcade_folders():
            print("== ARCADE: kein _Arcade-Ordner gefunden, uebersprungen")

    mins = (time.time() - t_start) / 60
    print("\nFertig: %(roms)d ROMs, %(neu)d neu erstellt, "
          "%(vorhanden)d schon vorhanden, %(fehlend)d ohne Cover" % gesamt)
    print("Gesamtzeit: %.1f Minuten" % mins)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAbgebrochen - beim naechsten Start geht es dort weiter.")
