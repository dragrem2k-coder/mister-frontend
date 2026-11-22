#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mister_boxart.py - Boxart-Downloader fuer den MiSTer
========================================================
v4.0
Keine Abhaengigkeiten - nur Python-Standardbibliothek.

ZWEI STUFEN, automatisch der Reihe nach (Build 336):
  0. DAS GERAET SELBST: zuerst wird nachgesehen, ob update_all (Extra
     Content -> Game Artwork DBs) oder ein Artpack schon Cover auf die
     Karte gelegt hat (/media/fat/docs und daneben) - das Ergebnis
     steht gleich am Anfang auf dem Bildschirm. Was dort liegt, wird
     nicht geladen: das Frontend zeigt es ohnehin. Kostet null
     Bandbreite und null Platz.
  1. LIBRETRO: fuer alles, was dann noch fehlt, PNG-Cover von
     thumbnails.libretro.com (Rueckfall: GitHub).

ENTFERNT (Build 336, Nutzerwunsch): die Mirror-Quelle, die bis dahin
zwischen Stufe 0 und libretro lag.

Aufruf (SSH oder ueber die Scripts-Kategorie des Frontends):
  python3 /media/fat/frontend/mister_boxart.py            # alle Systeme, CRT-Profil
  python3 /media/fat/frontend/mister_boxart.py hd         # 1080p-Profil
  python3 /media/fat/frontend/mister_boxart.py sd SNES NES  # nur bestimmte Systeme
  python3 /media/fat/frontend/mister_boxart.py hd neu       # vorhandene ERSETZEN

Bereits vorhandene Cover (.art, .png, .jpg) werden uebersprungen - das
Skript kann jederzeit abgebrochen (Strg+C) und spaeter fortgesetzt
werden.

NEU AB BUILD 119: der Rueckfall-Weg legt das heruntergeladene Cover als
ORIGINAL ab (PNG/JPG) und wandelt es nicht mehr in .art um. Das ist
schneller (kein Dekodieren und Verkleinern in Python auf der
MiSTer-CPU) und behaelt die volle Aufloesung - dieselbe Datei bedient
damit CRT UND HDMI, statt wie bisher pro Profil einen eigenen
Durchlauf zu brauchen. Der Preis ist Platz auf der Karte; mit dem
zusaetzlichen Wort "art" laeuft es wie frueher.

Mit dem zusaetzlichen Wort "neu" werden vorhandene Cover NICHT
uebersprungen, sondern noch einmal erzeugt. Das ist einmalig sinnvoll,
seit das Verkleinern ueber die zusammenfallenden Bildpunkte mittelt
statt sie wegzuwerfen (siehe scale_to_box()): vorher geladene Cover
liegen in der alten, groberen Qualitaet auf der Karte und wuerden sonst
fuer immer uebersprungen. Der Lauf dauert damit natuerlich so lange wie
beim ersten Mal - er laesst sich jederzeit abbrechen und fortsetzen.

Versionshistorie:
  v4.1 - (Build 336) Mirror-Quelle entfernt; vor dem Download wird
         angezeigt, was update_all schon geliefert hat, und solche
         Cover werden auch im Modus "neu" nicht geladen.
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

# ---------------------------------------------------------------------------
# SYSTEMTABELLE - kommt seit Build 79 aus fe/systems.py
# ---------------------------------------------------------------------------
# Hier stand bis Build 78 eine EIGENE, von Hand gepflegte Liste. Genau
# daran ist Virtual Boy gescheitert: das System kam ins Frontend, diese
# Tabelle wurde uebersehen, und der Download lief brav durch, ohne es zu
# beruecksichtigen - kein Fehler, nur keine Cover. Und dieselbe Liste
# gab es noch zweimal woanders.
#
# Jetzt ist fe/systems.py die einzige Quelle: was das Frontend als
# Kategorie anzeigen kann UND wofuer es eine Datenbank gibt, wird hier
# automatisch bedient. Ein neues System einzutragen genuegt dort.
#
# Rueckfall: laesst sich fe.systems nicht importieren (z.B. weil dieses
# Skript einzeln irgendwohin kopiert wurde), bleibt SYSTEMS leer und
# das Skript sagt das deutlich, statt kommentarlos nichts zu tun.
try:
    _hier = os.path.dirname(os.path.abspath(__file__))
    if _hier not in sys.path:
        sys.path.insert(0, _hier)
    from fe.systems import download_systeme as _download_systeme
    SYSTEMS = _download_systeme()
except Exception as _e:                              # noqa: BLE001
    print("FEHLER: Systemliste (fe/systems.py) nicht lesbar: %s" % _e)
    print("Dieses Skript gehoert in denselben Ordner wie frontend.py "
          "und der Unterordner fe/.")
    SYSTEMS = {}

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
# ENTFERNT (Build 336): die fruehere Mirror-Quelle (Quelle 1 und 2, .art-
# und png/-Baum), auf Wunsch des Nutzers. Geblieben ist nur, was der
# libretro-Weg weiterhin braucht: das Ablegen des Originals samt
# JPEG-Arbeitskopie.
# ---------------------------------------------------------------------------

DOWNLOAD_WORKERS = 6


def endung_nach_inhalt(data):
    """".png" / ".jpg" nach den ersten Bytes - oder None.

    None heisst ausdruecklich "das ist kein Bild": dann wird nichts
    geschrieben und der Eintrag wandert an die naechste Quelle. Der
    Server meldet fuer manche Dateien einen falschen Content-Type, auf
    den ist also kein Verlass; die Magic-Bytes sind eindeutig."""
    if not data or len(data) < 4:
        return None
    if data[:4] == b"\x89PNG":
        return ".png"
    if data[:3] == b"\xff\xd8\xff":
        return ".jpg"
    return None


# NEU (Build 129): die JPEG-Arbeitskopie.
#
# WARUM. Ein Cover wird nach dem Download drei Mal verkleinert (Liste,
# Kachel, Galerie). Die Flaechenmittelung liest dabei jeden QUELLPUNKT -
# es zaehlt also, wie gross die Datei ist, aus der gerechnet wird.
# TurboJPEG kann verkleinert DEKODIEREN (1/2, 1/4, 1/8 direkt aus dem
# Dekoder), libpng kann das nicht. Gemessen an einem 900x1200-Cover mit
# den drei HDMI-Kaesten: 674 ms aus dem PNG, 438 ms aus dem JPEG.
#
# WAS DABEI NICHT PASSIERT: das Original wird nicht angefasst. Build 119
# hat ausdruecklich eingefuehrt, dass PNG/JPG im Original liegen bleiben
# ("Cover im Original"), und dabei bleibt es - die Arbeitskopie kommt
# DANEBEN. Wer sie nicht will, loescht die .jpg; das Frontend nimmt dann
# wieder das PNG (siehe die Reihenfolge in _art_index() in fe/art.py).
#
# UND WAS SIE NICHT KANN: JPEG kennt keine Transparenz. Fuer die
# Kategorie-Abzeichen wird deshalb nie eine Arbeitskopie angelegt - die
# brauchen ihren durchsichtigen Rand. Dieser Weg hier laeuft nur ueber
# Spiel-Cover.
ARBEITSKOPIE_GUETE = 90

try:
    import fe.bildlib as _bildlib
except Exception:                                        # noqa: BLE001
    _bildlib = None


def arbeitskopie_schreiben(pfad_png, daten):
    """Neben einem frisch abgelegten PNG eine JPEG-Arbeitskopie
    anlegen. Rueckgabe: der Pfad, oder None wenn nichts geschrieben
    wurde.

    Scheitert das aus irgendeinem Grund, ist das KEIN Fehler: dann gibt
    es eben keine Arbeitskopie und alles laeuft wie in Build 128. Ein
    Cover soll nie deshalb fehlen, weil eine Beschleunigung nicht
    geklappt hat."""
    if _bildlib is None or not _bildlib.schreiben_verfuegbar():
        return None
    if not daten or daten[:4] != b"\x89PNG":
        return None                       # schon JPEG, oder kein PNG
    try:
        bild = _bildlib.decode_png_lib(daten)
        if not bild:
            return None
        w, h, pix = bild
        jpg = _bildlib.encode_jpeg(w, h, pix, ARBEITSKOPIE_GUETE)
        if not jpg:
            return None
        # KEINE Groessenbremse - zweimal falsch angesetzt, bevor die
        # Messung es geklaert hat.
        #
        # Erst stand hier "nur schreiben, wenn das JPEG kleiner ist als
        # das PNG", dann "hoechstens doppelt so gross". Beides geht von
        # der Annahme aus, die Arbeitskopie solle Platz sparen. Tut sie
        # nicht - sie spart RECHENZEIT, und die haengt an der
        # BILDPUNKTZAHL, nicht an der Dateigroesse.
        #
        # Ein PNG, das sich gut komprimieren laesst, ist klein auf der
        # Karte und beim Verkleinern trotzdem genauso teuer wie jedes
        # andere Bild derselben Masse. Eine Groessenbremse haette die
        # Arbeitskopie ausgerechnet dort verhindert.
        #
        # Was sie kostet, steht in der README: rund 0.2-0.4 MB je Cover,
        # zusaetzlich zum Original. Wer das nicht will, loescht die
        # .jpg-Dateien - das Frontend nimmt dann wieder die PNG.
        ziel = pfad_png[:-4] + ".jpg"
        tmp = ziel + ".tmp%d" % os.getpid()
        with open(tmp, "wb") as f:
            f.write(jpg)
        os.replace(tmp, ziel)
        return ziel
    except Exception:                                    # noqa: BLE001
        return None


def original_ablegen(out_dir, rom, daten):
    """Ein heruntergeladenes Cover ablegen - Original plus, wenn es ein
    PNG ist, die JPEG-Arbeitskopie daneben.

    EINE Stelle fuer alle Quellen (frueher auch der Mirror). Vorher stand
    das Schreiben an zwei Stellen; mit der Arbeitskopie waeren es vier
    geworden, und zwei davon haetten irgendwann auseinandergelebt."""
    endung = endung_nach_inhalt(daten)
    if endung is None:
        return None
    pfad = os.path.join(out_dir, rom + endung)
    with open(pfad, "wb") as f:
        f.write(daten)
    if endung == ".png":
        arbeitskopie_schreiben(pfad, daten)
    return pfad


# ---------------------------------------------------------------------------
# DOWNLOAD: libretro (seit Build 336 die einzige Quelle im Netz), siehe
# Modul-Docstring.
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

# Wird von main() gesetzt (Aufruf mit "neu"): bereits vorhandene
# .art-Dateien noch einmal erzeugen, statt sie zu ueberspringen.
FORCE_NEU = False


def scale_to_box(w, h, rgb, max_w, max_h):
    """Verkleinerung in die Begrenzungsbox - mit Mittelung ueber die
    zusammenfallenden Bildpunkte (Kastenfilter).

    GEAENDERT (Nutzer-Rueckfrage: "kann das sein, dass du das bei den
    Boxarts bei den Spielen/ROMs selbst vergessen hast?" - ja, genau
    hier): dieses Skript erzeugt die .art-Dateien der Spiele-Cover
    ueberhaupt erst. Es hat dabei bisher Nearest-Neighbor verwendet, also
    schlicht Bildzeilen und -spalten WEGGEWORFEN.

    Das faellt hier besonders ins Gewicht, weil die Verkleinerung gross
    ist: die heruntergeladenen Vorlagen sind typischerweise mehrere
    hundert bis ueber tausend Pixel breit, das Ziel misst 300x350 (hd)
    bzw. 104x168 (sd). Bei einer Verkleinerung auf ein Drittel traegt
    jeder uebernommene Bildpunkt die Information von neun - acht davon
    fielen einfach weg. Genau daher stammt der ausgefranste Eindruck,
    und zwar UNABHAENGIG davon, wie gut das Frontend spaeter beim
    Anzeigen skaliert: was hier verloren geht, ist endgueltig weg.

    Das Gegenstueck fuer den PC (PC-Tools/art_convert.py) hat schon
    immer ordentlich skaliert (Pillow/LANCZOS) - auf dem MiSTer selbst
    ging das nicht, weil dort bewusst keine Bildbibliothek vorausgesetzt
    wird. Deshalb hier dieselbe Mittelung von Hand, ohne zusaetzliche
    Abhaengigkeit.

    LAUFZEIT (ehrlich benannt): Mitteln ist deutlich teurer als
    Wegwerfen, weil jeder Bildpunkt der Vorlage angefasst werden muss
    statt nur jeder dritte oder neunte. Das faellt einmalig beim
    Umwandeln an - also in genau dem Lauf, den man ohnehin startet und
    nebenbei laufen laesst -, nicht spaeter im Betrieb. Die inneren
    Summen laufen ueber sum() auf Ausschnitten mit Schrittweite 3, das
    ist eine C-Schleife statt einer Python-Schleife.
    """
    scale = min(max_w / w, max_h / h, 1.0)
    tw = max(1, round(w * scale))
    th = max(1, round(h * scale))
    if tw >= w and th >= h:
        # Nichts zu verkleinern (Vorlage ist bereits klein genug) -
        # unveraendert uebernehmen, kein Rechenaufwand, kein
        # Qualitaetsverlust.
        return w, h, bytes(rgb)
    xr = []
    nx = []
    for x in range(tw):
        a = int(x * w / tw)
        b = max(a + 1, int((x + 1) * w / tw))
        xr.append((a * 3, b * 3))
        nx.append(b - a)
    rw = w * 3
    out = bytearray(tw * th * 3)
    for ty in range(th):
        y0 = int(ty * h / th)
        y1 = max(y0 + 1, int((ty + 1) * h / th))
        n = y1 - y0
        acc = None
        for y in range(y0, y1):
            row = rgb[y * rw:(y + 1) * rw]
            cur = []
            _an = cur.append
            for a, b in xr:
                _an(sum(row[a:b:3]))
                _an(sum(row[a + 1:b:3]))
                _an(sum(row[a + 2:b:3]))
            acc = cur if acc is None else [p + q for p, q in zip(acc, cur)]
        o = ty * tw * 3
        for x in range(tw):
            d = nx[x] * n
            i = x * 3
            out[o] = acc[i] // d
            out[o + 1] = acc[i + 1] // d
            out[o + 2] = acc[i + 2] // d
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

# NEUES VERHALTEN (Build 119, Nutzerwunsch: "ich wuerde ganz gerne JPG
# und PNG beim Cover-Download bevorzugen, anstatt auf .art umzuwandeln -
# denke mal das ist der bessere und schnellere Weg, wenn einer alles auf
# einmal runterladen moechte").
#
# Er hat in beiden Punkten recht, und seit Build 115 spricht nichts mehr
# dagegen: das Frontend liest PNG und JPG inzwischen selbst.
#
#   SCHNELLER: das Dekodieren und Verkleinern hier lief in reinem
#   Python auf der MiSTer-CPU - deshalb steht CONVERT_WORKERS auf 2 und
#   deshalb gab es frueher Abstuerze durch Spitzenspeicher. Faellt das
#   weg, ist der Download nur noch Download.
#
#   BESSER: die Datei behaelt ihre volle Aufloesung. Bisher wurde beim
#   Herunterladen auf die Kastengroesse EINES Profils verkleinert - wer
#   zwischen CRT und HDMI wechselt, brauchte deshalb zwei Durchlaeufe
#   und bekam sonst ein hochgerechnetes Bild. Das Original bedient
#   beide.
#
#   DER PREIS, ehrlich genannt: Platz auf der Karte. Ein volles
#   libretro-Cover ist ein Vielfaches einer fertig verkleinerten
#   .art-Datei. Wer knapp bei Platz ist, nimmt "art" als drittes Wort
#   auf der Kommandozeile und bekommt das alte Verhalten.
ORIGINAL_BEHALTEN = True

# Die Artwork-Datenbank auf dem Geraet selbst (Build 115) als ERSTE
# Quelle. Bewusst als weicher Import: dieses Skript laeuft auch
# eigenstaendig per SSH, und eine aeltere Installation hat fe/art.py
# vielleicht gar nicht in dieser Fassung. Dann bleibt _docs_cover None
# und alles laeuft wie vorher.
try:
    import sys as _sys
    if "/media/fat/frontend" not in _sys.path:
        _sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from fe.art import docs_cover as _docs_cover
except Exception:                                        # noqa: BLE001
    _docs_cover = None


def process_one_rom_fallback(rom, sysname, idx_exact, idx_strip, tri, out_dir, box):
    cover, how = match_rom(rom, idx_exact, idx_strip, tri)
    if not cover:
        return (rom, "missing", None)
    png = download_cover(sysname, cover)
    if not png:
        return (rom, "dl_failed", cover)
    if ORIGINAL_BEHALTEN:
        # Kein Dekodieren, kein Verkleinern, kein Umwandeln - die Datei
        # wird genommen, wie sie kommt. Die Endung richtet sich nach dem
        # tatsaechlichen Inhalt, nicht nach dem Namen auf dem Server.
        # GEAENDERT (Build 129): ueber original_ablegen(), damit hier
        # dasselbe passiert wie beim Mirror - Original hinlegen und bei
        # einem PNG die JPEG-Arbeitskopie daneben.
        try:
            if original_ablegen(out_dir, rom, png) is None:
                return (rom, "png_error", "kein Bild")
        except OSError as e:
            return (rom, "png_error", str(e))
        return (rom, "ok", (how, cover))
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
    """Der libretro-Weg - seit Build 336 der einzige Download, fuer
    alle ROMs, fuer die auf dem Geraet noch kein Cover liegt."""
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

# Build 336: wo update_all seine Boxarts ablegt. Die Orte kommen aus
# fe/art.py (dieselben, an denen das Frontend sie zum ANZEIGEN sucht) -
# zwei Listen, die dasselbe bedeuten, laufen sonst irgendwann
# auseinander. Nur wenn das Modul fehlt, gilt die Ersatzliste.
try:
    from fe.art import (DOCS_BASE as _UA_DOCS,
                        FREMD_ZUSATZ_WURZELN as _UA_ZUSATZ,
                        DOCS_UNTERORDNER as _UA_UNTER)
except Exception:                                        # noqa: BLE001
    _UA_DOCS = "/media/fat/docs"
    _UA_ZUSATZ = ("/media/fat/Artwork", "/media/fat/artwork",
                  "/media/fat/boxart", "/media/fat/Boxart")
    _UA_UNTER = ("Artwork", "Named_Boxarts", "Boxarts", "boxart",
                 "Covers", "covers")


def update_all_artwork(wurzeln=None, unterordner=None):
    """(Systeme, Cover) der Boxarts, die update_all (Extra Content ->
    Game Artwork DBs) oder ein Artpack schon auf die Karte gelegt hat.

    Gezaehlt wird je Systemordner nur in den Boxart-Unterordnern
    ("Artwork", "Named_Boxarts", ...), nie in "Screenshots" oder
    "Titles" - die zaehlen nicht als Cover. Der leere Unterordner ""
    aus fe/art.py bleibt hier bewusst weg: dort laege auch jedes
    andere Bild eines Systemordners. os.scandir() liefert die Namen
    ohne einen stat() je Datei (siehe fe/scan.py, Build 336)."""
    if wurzeln is None:
        wurzeln = (_UA_DOCS,) + tuple(_UA_ZUSATZ)
    if unterordner is None:
        unterordner = tuple(u for u in _UA_UNTER if u)
    systeme, cover = set(), 0
    for wurzel in wurzeln:
        try:
            ordner = sorted(e.name for e in os.scandir(wurzel)
                            if e.is_dir() and not e.name.startswith("."))
        except OSError:
            continue
        for sysname in ordner:
            for unter in unterordner:
                try:
                    with os.scandir(os.path.join(wurzel, sysname, unter)) as it:
                        n = sum(1 for e in it
                                if e.name.rsplit(".", 1)[-1].lower()
                                in ("jpg", "jpeg", "png"))
                except OSError:
                    continue
                if n:
                    systeme.add(sysname)
                    cover += n
    return len(systeme), cover


def update_all_melden(wurzeln=None):
    """Vor dem ersten Download nachsehen und SAGEN, was update_all schon
    geliefert hat (Build 336). Liefert (Systeme, Cover)."""
    print("Schaue zuerst nach Boxarts von update_all ...")
    systeme, cover = update_all_artwork(wurzeln)
    if cover:
        print("  Gefunden: %d Cover in %d Systemen. Das Frontend zeigt sie "
              "direkt an - fuer diese Spiele wird NICHTS geladen."
              % (cover, systeme))
        if _docs_cover is None:
            print("  ACHTUNG: fe/art.py liess sich nicht laden - der Abgleich "
                  "je Spiel ist so nicht moeglich. Bitte das Frontend "
                  "aktualisieren.")
    else:
        print("  Keine gefunden. Tipp: update_all -> Einstellungen -> "
              "Extra Content -> Game Artwork DBs laedt fertige Cover fuer "
              "fast alle Systeme; danach muss hier kaum noch etwas geladen "
              "werden.")
    print("Geladen wird nur, was dann noch fehlt (thumbnails.libretro.com).")
    return systeme, cover


def process_system(syskey, roms, ext_sysname_map, art_base, remote_dir, box, gesamt):
    """Ein System komplett abarbeiten: erst nachsehen, was auf dem
    Geraet schon liegt (update_all-Datenbank, eigene Cover), fuer den
    Rest libretro (gruppiert nach Cover-Quelle je Endung, siehe SMS/Game
    Gear). remote_dir ist seit Build 336 ohne Bedeutung (frueher der
    Mirror-Ordner) und bleibt nur fuer die Aufrufform stehen."""
    if not roms:
        return
    out_dir = os.path.join(art_base, syskey)
    os.makedirs(out_dir, exist_ok=True)

    # NEU: mit FORCE_NEU werden auch bereits vorhandene .art-Dateien noch
    # einmal erzeugt. Gebraucht, seit das Verkleinern mittelt statt
    # wegzuwerfen (siehe scale_to_box()): wer seine Cover VOR dieser
    # Aenderung geladen hat, hat sie in der alten, groberen Qualitaet auf
    # der Karte liegen - ohne diesen Schalter wuerden sie fuer immer
    # uebersprungen und die Verbesserung kaeme nie an.
    # GEAENDERT (Build 119): auch ein PNG oder JPG zaehlt als
    # vorhandenes Cover. Ohne das wuerde ein zweiter Lauf alles noch
    # einmal herunterladen, was der erste als Original abgelegt hat.
    #
    # ERWEITERT (Build 120, Nutzerwunsch: "die Quelle auf dem MiSTer
    # soll als erstes abgefragt werden, dann die anderen"): liegt das
    # Cover bereits in der Artwork-Datenbank unter /media/fat/docs,
    # gibt es nichts herunterzuladen. Das Frontend zeigt es ohnehin
    # (siehe docs_cover() in fe/art.py) - ein Download waere reine
    # Bandbreite und Platz fuer dasselbe Bild.
    #
    # Bei einer vollstaendig installierten Datenbank sind das
    # zehntausende Eintraege, die gar nicht erst in die Warteschlange
    # kommen. Faellt der Import aus (aeltere Installation, Modul
    # fehlt), bleibt es beim bisherigen Verhalten - der Download laeuft
    # dann eben wie vorher.
    #
    # GEAENDERT (Build 336, Nutzerwunsch: "bevor man boxarts nachlaedt
    # sollte das frontend erst schauen automatisch ob schon jemand ueber
    # update_all sich die boxarts ect geladen hat"): ein Cover aus der
    # update_all-Datenbank wird jetzt AUCH im Modus "neu" nicht
    # geladen. "neu" ersetzt unsere EIGENEN alten Cover - eines, das
    # update_all schon geliefert hat, ist kein altes eigenes, und ein
    # zweites Bild desselben Spiels waere nur belegter Platz.
    def _eigenes_da(name):
        for endung in (".art", ".png", ".jpg", ".jpeg"):
            if os.path.exists(os.path.join(out_dir, name + endung)):
                return True
        return False

    def _update_all_da(name):
        if _docs_cover is None:
            return False
        try:
            return bool(_docs_cover(syskey, name))
        except Exception:                                # noqa: BLE001
            return False

    todo = []
    aus_update_all = 0
    for name, ext in roms:
        if _update_all_da(name):
            aus_update_all += 1
        elif FORCE_NEU or not _eigenes_da(name):
            todo.append((name, ext))
    gesamt["roms"] += len(roms)
    gesamt["vorhanden"] += len(roms) - len(todo)
    gesamt["update_all"] = gesamt.get("update_all", 0) + aus_update_all
    print("== %s: %d Eintraege, %d schon da (davon %d von update_all), "
          "%d ohne Cover" % (syskey, len(roms), len(roms) - len(todo),
                             aus_update_all, len(todo)))
    if not todo:
        return

    by_sysname = {}
    for name, ext in todo:
        by_sysname.setdefault(ext_sysname_map.get(ext, syskey), []).append(name)

    # DIE REIHENFOLGE DER QUELLEN (Build 336; vorher Build 123):
    #
    #   0. auf dem Geraet selbst      - update_all-Datenbank und eigene
    #                                   Cover, laeuft schon oben; was
    #                                   dort liegt, kommt gar nicht erst
    #                                   in diese Liste
    #   1. libretro                   - thumbnails.libretro.com, Rueckfall
    #                                   GitHub
    #
    # Die Mirror-Stufen dazwischen sind entfernt -
    # Nutzerwunsch, Build 336.
    still_missing = [(n, sysname) for sysname, names in by_sysname.items()
                     for n in names]

    if still_missing:
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
    global FORCE_NEU, ORIGINAL_BEHALTEN
    args = list(sys.argv[1:])
    for schalter in ("neu", "--neu", "force"):
        if schalter in args:
            args.remove(schalter)
            FORCE_NEU = True
    # Build 119: "art" schaltet auf das alte Verhalten zurueck -
    # umwandeln und verkleinern statt das Original behalten. Fuer alle,
    # bei denen der Platz auf der Karte knapper ist als die Geduld.
    for schalter in ("art", "--art", "umwandeln"):
        if schalter in args:
            args.remove(schalter)
            ORIGINAL_BEHALTEN = False
    profile = "sd"
    if args and args[0] in ("sd", "hd"):
        profile = args.pop(0)
    only = set(args) if args else None
    if FORCE_NEU:
        print("Modus 'neu': vorhandene Cover werden ERSETZT "
              "(dauert entsprechend laenger).")
    if ORIGINAL_BEHALTEN:
        print("Cover werden als Original (PNG/JPG) abgelegt - schneller "
              "und in voller Aufloesung, dafuer mehr Platz auf der Karte.")
        print("Mit dem Zusatz 'art' stattdessen wie frueher umwandeln "
              "und verkleinern.")

    art_base   = ART_HD if profile == "hd" else ART_BASE
    remote_dir = None          # Build 336: kein Mirror mehr
    box        = PROFILES[profile]
    print("Profil: %s -> %s" % (profile, art_base))
    update_all_melden()

    gesamt  = {"roms": 0, "neu": 0, "vorhanden": 0, "fehlend": 0,
               "update_all": 0}
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
    print("\nFertig: %(roms)d ROMs, %(neu)d neu, %(vorhanden)d vorhanden "
          "(davon %(update_all)d von update_all), %(fehlend)d ohne Cover"
          % gesamt)
    print("Gesamtzeit: %.1f Minuten" % mins)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAbgebrochen - beim naechsten Start geht es dort weiter.")
