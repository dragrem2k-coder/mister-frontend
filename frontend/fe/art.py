#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Boxart-Verwaltung: eigener PNG-Decoder (fuer RA-Erfolgs-Icons),
ArtCache (Cover/Logos im eigenen .art-Format), BgCache (System-
Hintergrundbilder), Metadaten-Cache. Ausgelagert aus frontend.py
(Modularisierung, Git-Branch 'modular-refactor').

Pfad-Konstanten (ART_BASE/ART_HD/BG_BASE/SYSART_BASE/META_BASE) leben
jetzt HIER als ihr eigentliches Zuhause (vorher in frontend.py, an
mehreren weit entfernten Stellen im restlichen Code verwendet) -
frontend.py importiert sie von hier zurueck, damit alle bisherigen
Verwendungsstellen unveraendert weiterlaufen.

C_BG (siehe BgCache._compose()) wird bewusst NICHT als eigene Kopie
gehalten wie noch in fe/framebuffer.py - _compose() wird deutlich
seltener aufgerufen als Framebuffer.text() (nicht pro Zeichen, nur
beim Zusammensetzen eines neuen Hintergrundbilds), ein modul-
qualifizierter Zugriff auf fe.framebuffer.C_BG (das dort bereits
korrekt synchron gehalten wird) ist hier voellig ausreichend und
spart eine weitere Synchronisierungsstelle.
"""
import os, re, struct, zlib, json, time, urllib.request, hashlib
from fe.log import LOG
from fe.framebuffer import Framebuffer
from fe.translations import t
import fe.framebuffer as _fb_mod

ART_BASE    = "/media/fat/frontend/art"
ART_HD      = "/media/fat/frontend/art_hd"
BG_BASE     = "/media/fat/frontend/bg"
SYSART_BASE = "/media/fat/frontend/sysart"
META_BASE   = "/media/fat/frontend/meta"

# PNG-DECODER (Nutzerwunsch: RA-Erfolgs-Icons direkt im Frontend zeigen,
# nicht nur im Browser-Overlay, das PNGs von selbst versteht). Reines
# Standard-Python (zlib fuer die eigentliche Kompression - das macht der
# schwierige Teil bereits selbst), die PNG-eigene ZEILENFILTERUNG muss
# aber von Hand rekonstruiert werden - das ist der eigentliche Aufwand
# an einem PNG-Decoder.
#
# BEWUSST EINGESCHRAENKT (lieber None als ein falsches/kaputtes Bild):
# nur 8-Bit Farbtiefe, nicht interlaced, Farbtypen 0/2/3/4/6 - deckt
# praktisch jedes uebliche kleine Web-/Icon-Bild ab (fuer RA-Badges
# also die ueberwiegende Mehrheit der Faelle), NICHT aber 16-Bit-Tiefe,
# Adam7-Interlacing oder 1/2/4-Bit-Farbtiefen. Chunk-CRCs werden NICHT
# geprueft (vertrauenswuerdige Quelle: RAs eigenes CDN, keine
# Nutzereingabe) - das spart Aufwand, ohne die eigentliche Bild-
# Rekonstruktion zu beeintraechtigen.
def _paeth_predictor(a, b, c):
    """PNG-Paeth-Praediktor (siehe PNG-Spezifikation) - waehlt von den
    drei Nachbarn (links/oben/oben-links) den, der dem linearen
    Schaetzwert am naechsten liegt."""
    p = a + b - c
    pa = abs(p - a)
    pb = abs(p - b)
    pc = abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c

def _png_unfilter(raw, width, height, bpp):
    """Entfernt die PNG-Zeilenfilterung - jede Zeile im entpackten
    IDAT-Strom beginnt mit einem Filtertyp-Byte (0-4), gefolgt von den
    GEFILTERTEN (nicht den echten) Pixel-Bytes dieser Zeile. Liefert
    die rekonstruierten Rohpixel OHNE die Filter-Byte-Praefixe, oder
    None bei einem unbekannten Filtertyp oder zu kurzen Daten.
    bpp: Bytes pro Pixel (fuer den Filter-Rueckbezug - z.B. 4 bei
    RGBA/8-Bit, 1 bei Graustufen/8-Bit)."""
    stride = width * bpp
    row_len = stride + 1
    if len(raw) < row_len * height:
        return None
    out = bytearray(stride * height)
    prev_row = bytearray(stride)
    for y in range(height):
        off = y * row_len
        ftype = raw[off]
        line = raw[off + 1:off + 1 + stride]
        cur = bytearray(stride)
        if ftype == 0:      # None - unveraendert
            cur[:] = line
        elif ftype == 1:    # Sub - relativ zum Pixel LINKS
            for i in range(stride):
                a = cur[i - bpp] if i >= bpp else 0
                cur[i] = (line[i] + a) & 0xff
        elif ftype == 2:    # Up - relativ zum Pixel DARUEBER
            for i in range(stride):
                cur[i] = (line[i] + prev_row[i]) & 0xff
        elif ftype == 3:    # Average - Mittelwert aus links+oben
            for i in range(stride):
                a = cur[i - bpp] if i >= bpp else 0
                cur[i] = (line[i] + ((a + prev_row[i]) // 2)) & 0xff
        elif ftype == 4:    # Paeth - siehe _paeth_predictor()
            for i in range(stride):
                a = cur[i - bpp] if i >= bpp else 0
                c = prev_row[i - bpp] if i >= bpp else 0
                cur[i] = (line[i] + _paeth_predictor(a, prev_row[i], c)) & 0xff
        else:
            return None   # unbekannter Filtertyp - lieber abbrechen als raten
        out[y * stride:(y + 1) * stride] = cur
        prev_row = cur
    return bytes(out)

def decode_png(data):
    """Dekodiert eine PNG-Bilddatei (Bytes) zu (breite, hoehe,
    rgba_bytes) - fuer RA-Erfolgs-Icons direkt im Frontend. Liefert
    None bei JEDEM nicht unterstuetzten oder fehlerhaften Fall - NIE
    eine Ausnahme nach aussen (siehe Modul-Kopfkommentar fuer die
    bewussten Einschraenkungen)."""
    try:
        if not data.startswith(b"\x89PNG\r\n\x1a\n"):
            return None
        pos = 8
        width = height = bitdepth = colortype = None
        palette = None
        trns = None
        idat_parts = []
        n = len(data)
        while pos + 8 <= n:
            length = struct.unpack(">I", data[pos:pos + 4])[0]
            ctype = data[pos + 4:pos + 8]
            cstart = pos + 8
            cdata = data[cstart:cstart + length]
            pos = cstart + length + 4   # +4 = CRC, bewusst nicht geprueft
            if ctype == b"IHDR":
                if len(cdata) != 13:
                    return None
                (width, height, bitdepth, colortype,
                 comp, filt, interlace) = struct.unpack(">IIBBBBB", cdata)
                if comp != 0 or filt != 0 or interlace != 0:
                    return None   # Interlacing/exotische Kompression: nicht unterstuetzt
                if bitdepth != 8:
                    return None   # nur 8-Bit-Tiefe unterstuetzt
                if width <= 0 or height <= 0 or width * height > 4_000_000:
                    return None   # Groessen-Notbremse gegen kaputte/boesartige Header
            elif ctype == b"PLTE":
                palette = cdata
            elif ctype == b"tRNS":
                trns = cdata
            elif ctype == b"IDAT":
                idat_parts.append(cdata)
            elif ctype == b"IEND":
                break
        if width is None or not idat_parts:
            return None
        if colortype not in (0, 2, 3, 4, 6):
            return None

        channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[colortype]
        raw = zlib.decompress(b"".join(idat_parts))
        pixels = _png_unfilter(raw, width, height, channels)
        if pixels is None:
            return None

        # Zu RGBA vereinheitlichen, unabhaengig vom Quell-Farbtyp - so
        # muss der Rest des Frontends (blit() usw.) nur EIN Format
        # kennen, egal welcher PNG-Farbtyp reinkam.
        n_px = width * height
        out = bytearray(n_px * 4)
        if colortype == 6:      # RGBA schon direkt passend
            out[:] = pixels
        elif colortype == 2:    # RGB -> RGBA (Alpha immer deckend)
            for i in range(n_px):
                out[i * 4:i * 4 + 3] = pixels[i * 3:i * 3 + 3]
                out[i * 4 + 3] = 255
        elif colortype == 0:    # Graustufen -> RGBA
            for i in range(n_px):
                g = pixels[i]
                out[i * 4] = out[i * 4 + 1] = out[i * 4 + 2] = g
                out[i * 4 + 3] = 255
        elif colortype == 4:    # Graustufen+Alpha -> RGBA
            for i in range(n_px):
                g = pixels[i * 2]
                out[i * 4] = out[i * 4 + 1] = out[i * 4 + 2] = g
                out[i * 4 + 3] = pixels[i * 2 + 1]
        elif colortype == 3:    # Palette -> RGBA
            if not palette:
                return None
            for i in range(n_px):
                idx = pixels[i]
                p = idx * 3
                if p + 3 > len(palette):
                    return None
                out[i * 4:i * 4 + 3] = palette[p:p + 3]
                out[i * 4 + 3] = (trns[idx] if trns and idx < len(trns) else 255)
        return (width, height, bytes(out))
    except (struct.error, zlib.error, IndexError, ValueError):
        return None

# ----------------------------------------------------------------------------
# RA-ERFOLGS-ICONS (Badges) FUERS FRONTEND SELBST - baut auf decode_png()
# auf (siehe oben). Gleiches Grundprinzip wie ArtCache: dauerhaft als
# rohe PNG-Bytes lokal zwischengespeichert (Icons aendern sich nie mehr,
# sobald ein Erfolg veroeffentlicht ist), zusaetzlich die BEREITS
# DEKODIERTEN Bilder im Speicher gehalten (begrenzt, wie bei ArtCache).
# ----------------------------------------------------------------------------
BADGE_DIR = "/media/fat/frontend/ra_badges"
RA_BADGE_URL = "https://media.retroachievements.org/Badge/%s.png"

class BadgeCache:
    LIMIT = 60   # gleicher Gedanke wie ArtCache - Icons sind winzig,
                # koennte durchaus hoeher, aber kein Grund zur Eile

    def __init__(self):
        self.cache = {}   # badge_name -> (w, h, rgba) oder None
        self.order = []

    def get(self, badge_name):
        """Liefert (breite, hoehe, rgba) fuer ein RA-Badge, oder None,
        wenn der Name unbrauchbar ist oder das Icon nicht geladen/
        dekodiert werden konnte. Laedt/dekodiert bei Bedarf, danach
        aus dem Speicher-Cache."""
        if not badge_name or not re.match(r"^[A-Za-z0-9_-]+$", badge_name):
            return None   # kein Pfad-Trick moeglich, siehe _load_bytes()
        if badge_name in self.cache:
            return self.cache[badge_name]
        data = self._load_bytes(badge_name)
        result = decode_png(data) if data else None
        self.cache[badge_name] = result
        self.order.append(badge_name)
        if len(self.order) > self.LIMIT:
            old = self.order.pop(0)
            self.cache.pop(old, None)
        return result

    def _load_bytes(self, badge_name):
        """Rohe PNG-Bytes eines Badges - aus dem lokalen Dauer-Cache,
        falls vorhanden, sonst live von RA heruntergeladen und
        gespeichert. NIE eine Ausnahme nach aussen."""
        try:
            os.makedirs(BADGE_DIR, exist_ok=True)
        except OSError:
            pass
        path = os.path.join(BADGE_DIR, badge_name + ".png")
        try:
            with open(path, "rb") as f:
                return f.read()
        except OSError:
            pass
        try:
            req = urllib.request.Request(
                RA_BADGE_URL % badge_name,
                headers={"User-Agent": "MiSTerFrontend/1.0"})
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                if resp.status != 200:
                    return None
                data = resp.read()
        except (urllib.error.URLError, OSError, TimeoutError):
            return None
        try:
            with open(path, "wb") as f:
                f.write(data)
        except OSError:
            pass
        return data

BADGES = BadgeCache()

# ----------------------------------------------------------------------------
# ARTWORK (.art) UND METADATEN
# .art-Format: b"ART1" + uint16 Breite + uint16 Hoehe + zlib(BGRA-Rohpixel)
# Die Dateien werden am PC mit art_convert.py erzeugt - der MiSTer
# muss nur noch entpacken (zlib ist Standardbibliothek) und blitten.
# ----------------------------------------------------------------------------

# ----------------------------------------------------------------------------
# MINIATUREN-CACHE AUF DER SD-KARTE (Nutzerwunsch: "beim Scrollen wird
# staendig dekodiert/skaliert, das kostet auf schwacher Hardware Zeit -
# koennte man fertige Miniaturen speichern?")
#
# Prinzip: Original -> dekodieren -> skalieren -> fertige Miniatur EINMAL
# auf der SD-Karte ablegen. Beim naechsten Mal (auch nach einem Neustart,
# der RAM-Cache ist dann ja leer) wird nur noch die kleine, fertige
# Miniatur eingelesen statt erneut zu dekodieren+skalieren.
#
# WICHTIGE QUALITAETS-REGEL (Nutzer-Rueckfrage: "darf die Bildqualitaet
# nicht leiden"): eine gespeicherte Miniatur wird NIEMALS erneut skaliert,
# um sie an eine ANDERE Zielgroesse anzupassen (das wuerde sichtbar
# schlechter aussehen als eine frische Skalierung vom Original). Bei
# einem Cache-Fehltreffer (andere Zielgroesse als gespeichert, z.B. weil
# ein anderer Titeltext mehr/weniger Zeilen braucht) wird IMMER frisch
# vom Original aus skaliert - der Festplatten-Cache liefert dann einfach
# keinen Treffer, kein Qualitaetsverlust, nur kein Geschwindigkeitsvorteil
# in diesem einen Fall.
#
# Format: dieselbe simple ART1-Kopfstruktur wie normale .art-Dateien -
# kein neues Format noetig, derselbe Lesecode funktioniert fuer beides.
THUMB_CACHE_DIR = "/media/fat/frontend/thumb_cache"

# Obergrenze nach ANZAHL Dateien (nicht Speicherplatz) - einfach zu
# pruefen, verhindert zuverlaessig "irgendwann liegen Zehntausende
# Dateien herum" unabhaengig von der tatsaechlichen Dateigroesse.
THUMB_CACHE_MAX_FILES = 800

def _thumb_cache_key(path, w, h):
    """Cache-Schluessel aus Quellpfad + Zielgroesse + Dateigroesse/
    Aenderungszeitpunkt der Quelle - letzteres sorgt fuer automatische
    Entwertung, falls jemand ein Cover durch ein anderes ersetzt (neue
    Datei an derselben Stelle -> anderer Schluessel -> alter Cache-
    Eintrag wird einfach nie wieder getroffen, veraltet spurlos aus dem
    Cache heraus statt ein falsches Bild zu zeigen).

    EHRLICH DOKUMENTIERTE GRENZE: die MiSTer-SD-Karte laeuft ueblicher-
    weise auf FAT32, das teils nur 2-Sekunden-Genauigkeit bei
    Aenderungszeiten kennt. Wird ein Cover durch ein ANDERES mit exakt
    derselben Dateigroesse ersetzt UND das passiert innerhalb desselben
    2-Sekunden-Fensters, koennte kurzzeitig noch die alte Miniatur
    getroffen werden (bis sie irgendwann verdraengt wird). Ein voller
    Inhaltsvergleich waere zuverlaessiger, wuerde aber bei JEDEM Aufruf
    die komplette Datei lesen muessen - genau der Aufwand, den der
    Cache ja vermeiden soll. Fuer den ueblichen Fall (Cover wird einmal
    ersetzt, danach lange nicht mehr angefasst) ist das unproblematisch."""
    try:
        st = os.stat(path)
        sig = "%s|%d|%d|%d|%.6f" % (path, w, h, st.st_size, st.st_mtime)
    except OSError:
        sig = "%s|%d|%d" % (path, w, h)
    return hashlib.sha1(sig.encode("utf-8", "surrogateescape")).hexdigest()[:24]

def _thumb_cache_path(key):
    return os.path.join(THUMB_CACHE_DIR, key + ".art")

def _thumb_cache_get(path, w, h):
    """Liefert (breite, hoehe, pixelbytes) bei einem Treffer, sonst
    None. Aktualisiert bei einem Treffer die Aenderungszeit der Datei
    (dient als einfacher, robuster "zuletzt benutzt"-Zeitstempel fuer
    die Verdraengung weiter unten - keine separate Indexdatei noetig,
    die nach einem Absturz/Stromausfall inkonsistent werden koennte)."""
    cpath = _thumb_cache_path(_thumb_cache_key(path, w, h))
    try:
        with open(cpath, "rb") as f:
            if f.read(4) != b"ART1":
                return None
            tw, th = struct.unpack("<HH", f.read(4))
            pix = zlib.decompress(f.read())
            if len(pix) != tw * th * 4:
                return None
        try:
            os.utime(cpath, None)
        except OSError:
            pass
        return (tw, th, pix)
    except FileNotFoundError:
        return None
    except OSError:
        return None
    except (struct.error, zlib.error, ValueError):
        return None

def _thumb_cache_put(path, w, h, tw, th, pix):
    """Speichert eine FRISCH vom Original berechnete Miniatur. Ueber
    eine temporaere Datei + os.replace() geschrieben (atomar) - ein
    Stromausfall/Absturz mitten im Schreiben kann so keine halb
    geschriebene, kaputte Cache-Datei hinterlassen.

    GEAENDERT (Nutzerwunsch: "Performance auf echter Hardware messen") -
    ein Schreibfehler wurde bisher STUMM verschluckt (nur "except
    OSError: return", keine Protokollierung). Auf einem echten Geraet
    koennte z.B. ein Rechte- oder Speicherplatzproblem den Cache
    dadurch dauerhaft wirkungslos machen, OHNE dass irgendwo im Log
    ein Hinweis darauf zu finden waere - genau die Art von stillem
    Fehler, die die Frage "warum wird es nicht schneller?" unbeant-
    wortet laesst. Jetzt wird jeder Fehlschlag explizit geloggt."""
    try:
        os.makedirs(THUMB_CACHE_DIR, exist_ok=True)
        cpath = _thumb_cache_path(_thumb_cache_key(path, w, h))
        tmp = cpath + ".tmp%d" % os.getpid()
        with open(tmp, "wb") as f:
            f.write(b"ART1" + struct.pack("<HH", tw, th) + zlib.compress(pix, 6))
        os.replace(tmp, cpath)
    except OSError as e:
        LOG("THUMB_CACHE Schreibfehler (%s): %s" % (os.path.basename(path), e))
        return
    _thumb_cache_evict_if_needed()

def _thumb_cache_evict_if_needed():
    """Einfache Verdraengung nach Anzahl Dateien: die am laengsten nicht
    mehr gelesenen/geschriebenen (aelteste Aenderungszeit) zuerst
    entfernen, bis wieder unter der Obergrenze. Laeuft nur, wenn
    tatsaechlich etwas Neues geschrieben wurde - nicht bei jedem
    Lesezugriff, um den haeufigen Fall (Cache-Treffer) nicht unnoetig
    zu verlangsamen."""
    try:
        names = [f for f in os.listdir(THUMB_CACHE_DIR) if f.endswith(".art")]
    except OSError:
        return
    if len(names) <= THUMB_CACHE_MAX_FILES:
        return
    entries = []
    for fn in names:
        fp = os.path.join(THUMB_CACHE_DIR, fn)
        try:
            entries.append((os.path.getmtime(fp), fp))
        except OSError:
            pass
    entries.sort()
    to_remove = len(entries) - THUMB_CACHE_MAX_FILES
    for _, fp in entries[:to_remove]:
        try:
            os.remove(fp)
        except OSError:
            pass

class ArtCache:
    LIMIT = 60                       # max. Bilder im Speicher halten - moderat
                                      # erhoeht (vorher 40): die tolerante
                                      # Cover-Suche findet jetzt mehr Cover als
                                      # zuvor, wodurch der alte Wert beim Hin-
                                      # und-Herscrollen zu haeufigem erneuten
                                      # Dekodieren fuehrte. Bewusst NICHT so
                                      # stark erhoeht wie urspruenglich
                                      # vorgeschlagen (90) - bei grossen HD-
                                      # Covern (~4MB/Bild unkomprimiert) waere
                                      # das ein spuerbarer RAM-Batzen auf einem
                                      # MiSTer mit typischerweise ~1GB RAM.

    def __init__(self):
        self.cache = {}              # pfad -> (w, h, pixelbytes) oder None
        self.order = []
        self._defer_uncached = False # beim schnellen Scrollen: noch nicht
                                     # dekodierte Cover ueberspringen (siehe
                                     # get_scaled()/COVER_SETTLE)

    def get(self, path):
        if path in self.cache:
            return self.cache[path]
        # WICHTIG (Bugfix): "Datei existiert nicht" (FileNotFoundError,
        # eine OSError-Unterklasse) ist ein STABILER Fall - sicher
        # dauerhaft zu cachen, da sich das waehrend der Sitzung normal-
        # erweise nicht mehr aendert. Eine BESCHAEDIGTE oder noch
        # UNVOLLSTAENDIGE Datei (z.B. waehrend eines noch laufenden
        # Kopier-/Downloadvorgangs) ist dagegen ein moeglicherweise
        # VORUEBERGEHENDER Zustand - struct.error/zlib.error traten
        # bisher NICHT gefangen ("except OSError" allein deckt das
        # nicht ab, waere sonst ein Absturz gewesen) und wurden trotzdem
        # als "nicht gefunden" dauerhaft gecacht, was ein spaeteres
        # erneutes Laden verhinderte, selbst wenn die Datei danach
        # vollstaendig und gueltig vorlag. Deshalb: bei einem
        # unerwarteten Format-/Dekomprimierungsfehler NICHT cachen -
        # naechster Zugriff versucht es einfach erneut.
        art = None
        cache_result = True
        try:
            with open(path, "rb") as f:
                if f.read(4) == b"ART1":
                    w, h = struct.unpack("<HH", f.read(4))
                    pix = zlib.decompress(f.read())
                    if len(pix) == w * h * 4:
                        art = (w, h, pix)
        except FileNotFoundError:
            pass                     # stabil - Cache-Eintrag bleibt bestehen
        except OSError:
            cache_result = False    # z.B. Berechtigung/IO-Fehler - lieber erneut versuchen
        except (struct.error, zlib.error, ValueError):
            cache_result = False    # unvollstaendige/beschaedigte Datei - erneut versuchen
        if not cache_result:
            return art
        self.cache[path] = art
        self.order.append(path)
        if len(self.order) > self.LIMIT:
            old = self.order.pop(0)
            self.cache.pop(old, None)
        return art

    SCALED_LIMIT = 20   # moderat erhoeht (vorher 10), gleicher Grund wie LIMIT

    def _scaled_cache_put(self, key, result):
        if not hasattr(self, "scaled"):
            self.scaled = {}
            self.scaled_order = []
        self.scaled[key] = result
        self.scaled_order.append(key)
        if len(self.scaled_order) > self.SCALED_LIMIT:
            old = self.scaled_order.pop(0)
            self.scaled.pop(old, None)

    def get_scaled(self, path, max_w, max_h):
        _t0 = time.monotonic()
        r = self._get_scaled_impl(path, max_w, max_h)
        _dt = time.monotonic() - _t0
        if _dt > 0.025:
            LOG("PERF cover: %.0f ms (%s)" % (_dt * 1000, os.path.basename(path)))
        return r

    def _get_scaled_impl(self, path, max_w, max_h):
        """Bild in die verfuegbare Flaeche einpassen. Kleine Cover werden
        ganzzahlig hochskaliert (Pixel-Look). Cover, die groesser als die
        Box sind, werden seit v1.8.1 per Nearest-Neighbor VERKLEINERT statt
        unskaliert zu bleiben - sonst ragen sie ueber den reservierten
        Platz hinaus und ueberlappen den Info-Text darunter."""
        if max_w <= 0 or max_h <= 0:
            return None
        if not hasattr(self, "scaled"):
            self.scaled = {}
            self.scaled_order = []

        # Festplatten-Cache ZUERST pruefen - noch VOR dem Dekodieren des
        # Originals. Schluessel ist die verfuegbare Kastengroesse
        # (max_w/max_h), nicht die erst noch zu berechnende Zielgroesse -
        # die kennen wir ja erst, nachdem wir das Original (Breite/Hoehe)
        # kennen, und genau DAS Dekodieren wollen wir bei einem Treffer
        # ja gerade vermeiden. Ein Treffer hier ist ein reiner kleiner
        # Lesevorgang - schnell genug, um auch waehrend aktivem Scrollen
        # sofort zurueckgegeben zu werden (keine Defer-Pruefung noetig).
        box_key = (path, "box", max_w, max_h)
        if box_key in self.scaled:
            return self.scaled[box_key]
        # NEU (Nutzerwunsch: "Performance auf echter Hardware messen") -
        # ein Festplatten-Cache-TREFFER ist so schnell (im Sandbox-Test
        # ~5-7ms), dass er die PERF-Schwelle weiter unten (>25ms) nie
        # erreicht - Treffer blieben dadurch bisher im Log UNSICHTBAR,
        # obwohl gerade DAS die interessante Frage ist ("greift der
        # Cache auf echter Hardware ueberhaupt?"). Deshalb hier ein
        # eigenes, unmittelbares Log-Signal, unabhaengig von der
        # Zeitschwelle - bewusst mit Zeitmessung, damit sich Treffer
        # und Fehltreffer direkt aus echten Log-Daten vergleichen lassen.
        _tcache_t0 = time.monotonic()
        disk_hit = _thumb_cache_get(path, max_w, max_h)
        if disk_hit is not None:
            _tcache_dt = (time.monotonic() - _tcache_t0) * 1000
            LOG("THUMB_CACHE Treffer: %.1fms (%s, %dx%d)"
                % (_tcache_dt, os.path.basename(path), max_w, max_h))
            self._scaled_cache_put(box_key, disk_hit)
            return disk_hit

        # Waehrend aktiv gescrollt wird: ein noch nicht dekodiertes Cover
        # NICHT hier (im Zeichen-/Scroll-Pfad) dekodieren - das ruckelt auf
        # der schwachen CPU. Stattdessen ueberspringen; kurz nach dem
        # letzten Tastendruck laedt die Idle-Nachzeichnung es nach (siehe
        # COVER_SETTLE in der Hauptschleife).
        if self._defer_uncached and path not in self.cache:
            return None
        base = self.get(path)
        if not base:
            return None
        w, h, pix = base

        if w <= max_w and h <= max_h:
            # Kein hartes Limit mehr wie in v1.8.1 (dort noch 4x) - seit
            # v1.9 hat die Boxart-Spalte deutlich mehr Platz, ein Deckel
            # von 4x liess kleine Cover unnoetig klein und von Leerraum
            # umgeben wirken. 10x ist grosszuegig genug, um jede Box zu
            # fuellen, aber immer noch klein genug, um den Speicher- und
            # Rechenaufwand des Nearest-Neighbor-Upscales im Rahmen zu
            # halten (Cache haelt ohnehin nur SCALED_LIMIT Bilder).
            scale = max(1, min(max_w // w, max_h // h, 10))
            if scale == 1:
                self._scaled_cache_put(box_key, base)
                return base
            # BUGFIX (Nutzer-Rueckmeldung: "beim Scrollen durch viele
            # ROMs ruckelt es spuerbar"): die Defer-Pruefung oben
            # schuetzte bisher NUR vor dem erneuten DEKODIEREN, nicht
            # vor der hier folgenden Skalierung. Bei grossen Sammlungen
            # (mehr als SCALED_LIMIT=20 unterschiedliche Cover pro
            # Sitzung) wird der Skalierungs-Cache haeufiger geleert als
            # der Rohbild-Cache (LIMIT=60) - ein bereits dekodiertes,
            # aber "verdraengtes" Cover wurde beim erneuten Vorbeiscrollen
            # trotzdem JEDES Mal neu skaliert, obwohl aktiv gescrollt
            # wurde. Jetzt: dieselbe Verzoegerung gilt auch hier.
            if self._defer_uncached:
                return None
            sw, sh = w * scale, h * scale
            out = bytearray(sw * sh * 4)
            row_out = sw * 4
            for y in range(h):
                o = y * w * 4
                row = b"".join(pix[o + x*4:o + x*4 + 4] * scale
                               for x in range(w))
                base_off = y * scale * row_out
                for rep in range(scale):
                    off = base_off + rep * row_out
                    out[off:off + row_out] = row
            result = (sw, sh, bytes(out))
            self._scaled_cache_put(box_key, result)
            # WICHTIGE QUALITAETS-REGEL (siehe Modul-Kommentar oben):
            # hier wird IMMER vom soeben aus dem Original berechneten
            # "result" gespeichert, NIEMALS von einer schon vorhandenen
            # Miniatur aus - so bleibt die gespeicherte Datei bit-
            # identisch zu einer frischen Berechnung.
            _thumb_cache_put(path, max_w, max_h, sw, sh, result[2])
            return result

        # Bild ist in mindestens einer Richtung groesser als die Box -
        # verkleinern statt es unskaliert ueberstehen zu lassen.
        scale = min(max_w / w, max_h / h)
        tw = max(1, int(w * scale))
        th = max(1, int(h * scale))
        # Gleicher Bugfix wie beim Hochskalieren oben (siehe dortiger
        # Kommentar) - auch die (teurere) Verkleinerung wird waehrend
        # aktivem Scrollen verzoegert, wenn sie noch nicht im
        # Skalierungs-Cache liegt.
        if self._defer_uncached:
            return None
        # WICHTIG (Bugfix): frueher eine einzelne 4-Byte-Zuweisung PRO
        # ZIEL-PIXEL in einer doppelt verschachtelten Schleife (bei
        # z.B. 480x600 Zielgroesse: 288.000 einzelne bytearray-Slice-
        # Zuweisungen!) - jede einzelne Python-Anweisung hat spuerbaren
        # Overhead. Per Differenzmessung bestaetigt: ~90ms fuer eine
        # einzelne Verkleinerung, genau der Fall bei jeder echten
        # Navigation zu einem neuen Spiel mit einem HD-Cover, das
        # nicht exakt in den verfuegbaren Platz passt. Jetzt wie bei
        # der Vergroesserung: pro Zeile EIN b\"\".join() (in C
        # implementiert, deutlich weniger Python-Interpreter-Overhead
        # pro Zeile) statt einzelner Zuweisungen pro Pixel.
        xmap = [min(w - 1, int(x / scale)) * 4 for x in range(tw)]
        out = bytearray(tw * th * 4)
        row_out = tw * 4
        for ty in range(th):
            sy = min(h - 1, int(ty / scale))
            srow = pix[sy * w * 4:(sy + 1) * w * 4]
            row_bytes = b"".join([srow[sx:sx + 4] for sx in xmap])
            out[ty * row_out:(ty + 1) * row_out] = row_bytes
        result = (tw, th, bytes(out))
        self._scaled_cache_put(box_key, result)
        # WICHTIGE QUALITAETS-REGEL (siehe Modul-Kommentar oben): immer
        # das soeben aus dem Original berechnete "result" speichern,
        # niemals eine bereits vorhandene Miniatur weiterverarbeiten.
        _thumb_cache_put(path, max_w, max_h, tw, th, result[2])
        return result

ART = ArtCache()

class BgCache:
    """Haelt pro System einen fertig komponierten Vollbild-Puffer
    (inkl. Stride-Padding), damit der Hintergrund beim Zeichnen nur
    noch per Blockkopie eingesetzt werden muss."""
    LIMIT = 2

    def __init__(self):
        self.cache = {}
        self.order = []

    def get(self, syskey, fb):
        key = (syskey, fb.width, fb.height, fb.stride)
        if key in self.cache:
            return self.cache[key]
        buf = None
        for fn in ("%s_%dx%d.art" % (syskey, fb.width, fb.height),
                   "%s.art" % syskey):
            art = ART.get(os.path.join(BG_BASE, fn))
            if art:
                buf = self._compose(art, fb)
                break
        self.cache[key] = buf
        self.order.append(key)
        if len(self.order) > self.LIMIT:
            self.cache.pop(self.order.pop(0), None)
        return buf

    @staticmethod
    def _compose(art, fb):
        w, h, pix = art
        base = Framebuffer.px(_fb_mod.C_BG)
        row_bg = base * fb.width + b"\x00" * (fb.stride - fb.width * 4)
        out = bytearray(row_bg * fb.height)
        # Bild zentrieren, bei Ueberbreite mittig beschneiden
        sx = max(0, (w - fb.width) // 2)
        dx = max(0, (fb.width - w) // 2)
        cw = min(w, fb.width)
        sy = max(0, (h - fb.height) // 2)
        dy = max(0, (fb.height - h) // 2)
        ch = min(h, fb.height)
        for y in range(ch):
            so = ((sy + y) * w + sx) * 4
            do = (dy + y) * fb.stride + dx * 4
            out[do:do + cw * 4] = pix[so:so + cw * 4]
        return bytes(out)

BG = BgCache()

_art_index_cache = {}   # (basis_ordner, syskey) -> {Name ohne "NNN "-Praefix: Dateiname}

def _art_index(base_dir, syskey):
    """Index fuer <base_dir>/<syskey>: Dateiname OHNE ".art" (exakt
    UND ohne fuehrende "NNN "-Nummer) -> tatsaechlicher Dateiname.
    Ermoeglicht sowohl den direkten Treffer als auch Cover aus
    nummerierten (kuratierten) Sets wie "007 Super Mario Kart (USA)
    .art", obwohl das Spiel intern nur "Super Mario Kart (USA)" heisst.
    Pro (Ordner, System) gecacht - wird nur beim ERSTEN Cache-
    Fehltreffer fuer ein System ueberhaupt aufgebaut (siehe
    art_path()), nicht bei jedem Cover-Aufruf.

    PERFORMANCE (Phase 2, Nutzerwunsch "Dateisystemzugriffe
    minimieren"): deckt jetzt AUCH den exakten Namen mit ab (frueher
    nur die "Nummer entfernt"-Variante) - _art_path_in() kommt dadurch
    komplett ohne eigenen os.path.exists()-Aufruf aus, der vorher bei
    JEDEM einzelnen Cover-Aufruf noetig war. Kostet hier nichts
    zusaetzlich (derselbe os.listdir()-Durchlauf wie bisher, nur
    zusaetzlich ausgewertet), spart aber einen Festplattenzugriff pro
    Cover-Anzeige im Aufrufer.

    ZWEI Durchlaeufe bewusst getrennt (nicht in einer Schleife
    gemischt): exakte Namen MUESSEN unabhaengig von der - nicht
    garantiert alphabetischen - Reihenfolge von os.listdir() immer
    Vorrang vor der "Nummer entfernt"-Variante haben (wie es der
    vorherige os.path.exists()-Aufruf VOR dem Index-Zugriff sichergestellt
    hat). Erst wenn alle exakten Namen eingetragen sind, fuellt der
    zweite Durchlauf nur noch LUECKEN mit den nummerierten Varianten -
    sonst koennte je nach Dateisystem-Reihenfolge zufaellig das falsche
    Cover treffen."""
    key = (base_dir, syskey)
    idx = _art_index_cache.get(key)
    if idx is None:
        idx = {}
        try:
            names = [fn for fn in os.listdir(os.path.join(base_dir, syskey))
                     if fn.endswith(".art")]
            for fn in names:
                idx[fn[:-4]] = fn
            for fn in names:
                base = fn[:-4]
                stripped = re.sub(r"^\d+\s+", "", base)
                if stripped != base and stripped not in idx:
                    idx[stripped] = fn
        except OSError:
            pass
        _art_index_cache[key] = idx
    return idx

def _art_path_in(base_dir, syskey, rom_basename):
    """Cover-Pfad innerhalb eines bestimmten Basisordners (ART_BASE
    oder ART_HD) - erst der exakte Name, sonst wird eine fuehrende
    "NNN "-Nummer im tatsaechlichen Dateinamen ignoriert (siehe
    _art_index()). Liefert IMMER einen Pfad zurueck (auch wenn er
    nicht existiert) - der Aufrufer prueft ohnehin schon selbst auf
    Existenz, hier nur der BESSERE Pfad-Kandidat."""
    fn = _art_index(base_dir, syskey).get(rom_basename)
    if fn:
        return os.path.join(base_dir, syskey, fn)
    return os.path.join(base_dir, syskey, rom_basename + ".art")

def art_path(syskey, rom_basename):
    return _art_path_in(ART_BASE, syskey, rom_basename)

def _category_art_key(name, syskey):
    """Kuenstlicher Schluessel NUR fuer die Sysart-/Hintergrundsuche
    (BG_BASE/SYSART_BASE) - fuer echte Systeme identisch mit syskey.

    NEU (Nutzerwunsch: eigenes Artwork fuer "Weiterspielen" und
    "Zuletzt gespielt"): diese beiden Kategorien mischen mehrere
    Systeme und haben deshalb bewusst syskey=None (siehe
    build_categories()) - das darf NICHT geaendert werden, da mehrere
    andere Stellen (z.B. filter_curated(), das Kategorien ohne syskey
    unangetastet laesst) genau daran erkennen, dass es sich um eine
    gemischte Spezialkategorie statt eines echten Spielesystems
    handelt. Stattdessen wird hier - NUR fuer die Kunstwerk-Suche -
    ueber den (uebersetzten) Kategorienamen ein fester, aber
    sprachunabhaengiger Ersatzschluessel ermittelt, exakt nach dem
    bereits bewaehrten Muster aus dem Core-Auswahl-Fix fuer Favoriten
    (Vergleich gegen t(...) zur Laufzeit statt eines gespeicherten
    festen Strings)."""
    if syskey:
        return syskey
    if name == t("continue_cat"):
        return "CONTINUE"
    if name == t("recent_cat"):
        return "RECENT"
    return None

_meta_cache = {}
_mra_cache = {}

def mra_meta(path):
    """Jahr/Hersteller/Kategorie/Spieler aus einer MRA-Datei lesen."""
    if path in _mra_cache:
        return _mra_cache[path]
    meta = {}
    try:
        with open(path, "r", errors="replace") as f:
            head = f.read(4096)
        for tag, key in (("year", "year"), ("manufacturer", "manufacturer"),
                         ("category", "genre"), ("players", "players")):
            m = re.search(r"<%s>\s*([^<]+?)\s*</%s>" % (tag, tag), head,
                          re.I)
            if m:
                meta[key] = m.group(1)
    except OSError:
        pass
    _mra_cache[path] = meta
    if len(_mra_cache) > 200:
        _mra_cache.pop(next(iter(_mra_cache)))
    return meta

def get_meta(syskey, rom_basename):
    """Metadaten (players/year/genre) fuer ein Spiel, lazy geladen.

    PHASE 2 (Nutzerwunsch "RAM-Verbrauch optimieren"): vorsorgliche
    Obergrenze ergaenzt. Aktuell durch die feste, kleine Anzahl an
    Systemen (GAME_SYSTEMS) ohnehin praktisch von selbst begrenzt (max.
    ein Eintrag pro System) - falls die Systemliste kuenftig waechst
    oder ein System eine ungewoehnlich grosse Metadaten-Datei hat,
    verhindert diese Grenze trotzdem unbegrenztes Wachstum, nach
    demselben einfachen Verdraengungs-Prinzip wie bei _mra_cache."""
    if syskey not in _meta_cache:
        data = {}
        try:
            with open(os.path.join(META_BASE, syskey + ".json")) as f:
                data = json.load(f)
        except (OSError, ValueError):
            pass
        _meta_cache[syskey] = data
        if len(_meta_cache) > 20:
            _meta_cache.pop(next(iter(_meta_cache)))
    return _meta_cache[syskey].get(rom_basename, {})

