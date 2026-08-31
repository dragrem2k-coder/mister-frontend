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
import os, re, struct, zlib, json, time, urllib.request, hashlib, threading
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
#
# ERHOEHT 800 -> 4000 (Nutzer-Rueckmeldung: "rendert der die ganzen
# Boxarts jetzt immer neu? Ich bin schon mehrmals neu gestartet und
# denke jedes Mal: warum macht der das").
#
# 800 war fuer eine grosse Sammlung schlicht zu wenig. Jedes Cover
# braucht einen eigenen Eintrag JE Zielgroesse - und CRT und HDMI haben
# unterschiedliche Zielgroessen, ebenso aendert sich die Cover-Hoehe mit
# der Zahl der Metadatenzeilen eines Spiels. Wer ein paar tausend Spiele
# hat, verdraengt sich damit dauerhaft selbst: einmal quer durch zwei
# Systeme gescrollt, und die Eintraege des ersten sind schon wieder weg.
# Nach aussen sieht das genau so aus, wie es gemeldet wurde - "der
# rendert alles immer wieder neu".
#
# ZWEITE ERHOEHUNG 4000 -> 20000 (Nutzer: "koennen wir den Cache noch
# hoeher setzen? Platz genug ist auf einer 128GB-SD-Karte sowieso").
# Damit passt praktisch jede realistische Sammlung vollstaendig hinein,
# in beiden Aufloesungen - der Zwischenspeicher waermt sich einmal auf
# und bleibt danach warm, auch ueber Neustarts.
#
# EHRLICH BENANNTER PREIS: Platz auf der SD-Karte. Eine CRT-Miniatur
# liegt bei grob 10-20 KB, eine HDMI-Miniatur bei grob 100-200 KB.
# 20000 Eintraege koennen also im Extremfall (alles HDMI) mehrere GB
# belegen - auf einer 128-GB-Karte unkritisch, auf einer 16-GB-Karte
# nicht. Wer knapp bei Platz ist, setzt den Wert hier herunter oder
# loescht den Ordner thumb_cache; er wird bei Bedarf neu aufgebaut, es
# geht dabei nichts verloren ausser Wartezeit.
#
# Die Obergrenze wird nur beim SCHREIBEN geprueft, und die Pruefung ist
# ein einzelnes os.listdir() - auch bei 20000 Dateien kostet das nichts
# Spuerbares, zumal sie nur nach einer neu berechneten Miniatur laeuft.
THUMB_CACHE_MAX_FILES = 20000

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
        sig = "%s|%d|%d|%d|%.6f|%s" % (path, w, h, st.st_size, st.st_mtime,
                                       THUMB_ALGO_VERSION)
    except OSError:
        sig = "%s|%d|%d|%s" % (path, w, h, THUMB_ALGO_VERSION)
    return hashlib.sha1(sig.encode("utf-8", "surrogateescape")).hexdigest()[:24]

# VERSION DES SKALIERVERFAHRENS - Teil des Cache-Schluessels.
#
# Wird das Verkleinerungsverfahren geaendert, muessen die bereits auf der
# SD-Karte liegenden Miniaturen entwertet werden: sie wurden mit dem ALTEN
# Verfahren berechnet und wuerden sonst weiterhin getroffen, wodurch die
# Verbesserung bei genau den Covern NICHT ankaeme, die man am haeufigsten
# anschaut (die naemlich liegen sicher im Cache). Die Nummer hier einfach
# hochzaehlen - alte Eintraege werden dann nie wieder getroffen und
# veralten von selbst aus dem Cache heraus (siehe
# _thumb_cache_evict_if_needed()), es muss nichts von Hand geloescht
# werden.
#
# 2 = Flaechenmittel beim Verkleinern (vorher: Nearest-Neighbor)
THUMB_ALGO_VERSION = "2"


def _verkleinern_flaechenmittel(pix, w, h, tw, th):
    """Bild auf tw x th verkleinern, indem ueber die zusammenfallenden
    Quellpixel GEMITTELT wird (Kastenfilter).

    WARUM (Nutzer-Rueckmeldung: "auf halb und viertel sehen die Boxarts
    verpixelt aus"): das bisherige Verfahren war Nearest-Neighbor - es
    hat schlicht Bildzeilen und -spalten WEGGEWORFEN. Bei Fotos, und
    Boxart ist Foto-artig, erzeugt das genau den ausgefransten,
    "verpixelten" Eindruck: feine Strukturen fallen je nach Rasterlage
    mal ganz weg, mal bleiben sie hart stehen. Wird das Ergebnis danach
    noch von der Hardware vergroessert (kleinerer Framebuffer), faellt
    es doppelt auf.

    Aufgefallen ist es erst mit dem Menuepunkt "Menue-Aufloesung":
    bei voller Aufloesung ist die Cover-Flaeche groesser als ein
    uebliches Cover, es wird also gar nicht verkleinert - der Mangel
    konnte dort nie sichtbar werden.

    ZUR LAUFZEIT (ehrlich benannt, gemessen): das Mitteln ist rund
    zehnmal so teuer wie das blosse Wegwerfen - auf dieser Sandbox
    135 ms statt 11 ms fuer ein 600x800-Cover, auf der schwaecheren
    MiSTer-CPU entsprechend mehr. Das faellt aber NUR beim allerersten
    Betrachten eines Covers in einer bestimmten Groesse an:
      - waehrend aktiven Scrollens wird ohnehin nicht skaliert
        (siehe _defer_uncached weiter unten),
      - das Ergebnis landet im Festplatten-Cache und wird danach nur
        noch gelesen.
    Bewusst kein numpy o.ae. - das Frontend bleibt abhaengigkeitsfrei.

    UMSETZUNG: getrennt nach Achsen. Die inneren Summen laufen ueber
    sum() auf Ausschnitten mit Schrittweite 4 - das ist eine
    C-Schleife statt einer Python-Schleife und macht in der Messung
    den Unterschied zwischen 135 ms und rund 270 ms aus. Es wird immer
    nur EINE Zielzeile im Speicher gehalten (kein kompletter
    Zwischenpuffer) - auf einem Geraet mit ~1 GB RAM und HD-Covern ein
    bewusster Verzicht."""
    if tw <= 0 or th <= 0 or w <= 0 or h <= 0:
        return None
    # Quell-Spaltenbereich je Zielspalte, einmal vorab.
    xr = []
    nx = []
    for x in range(tw):
        a = int(x * w / tw)
        b = max(a + 1, int((x + 1) * w / tw))
        xr.append((a * 4, b * 4))
        nx.append(b - a)
    rw = w * 4
    ro = tw * 4
    out = bytearray(tw * th * 4)
    for ty in range(th):
        y0 = int(ty * h / th)
        y1 = max(y0 + 1, int((ty + 1) * h / th))
        n = y1 - y0
        acc = None
        for y in range(y0, y1):
            row = pix[y * rw:(y + 1) * rw]
            cur = []
            _an = cur.append
            for a, b in xr:
                _an(sum(row[a:b:4]))        # Blau
                _an(sum(row[a + 1:b:4]))    # Gruen
                _an(sum(row[a + 2:b:4]))    # Rot
            acc = cur if acc is None else [p + q for p, q in zip(acc, cur)]
        o = ty * ro
        i = 0
        for x in range(tw):
            d = nx[x] * n
            out[o] = acc[i] // d
            out[o + 1] = acc[i + 1] // d
            out[o + 2] = acc[i + 2] // d
            o += 4
            i += 3
    return bytes(out)


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
    wortet laesst. Jetzt wird jeder Fehlschlag explizit geloggt.

    GEAENDERT (Nutzerwunsch: "das muss schneller laufen!!" - echte
    Hardware-Messung via DRAGEND_PROFILE zeigte diesen Aufruf als
    zweitgroessten Einzelposten beim Aufreissen der Anzeige waehrend
    des Scrollens, z.B. "_thumb_cache_put: 380ms (Taekwon-Do (Korea).art)",
    davon 201ms allein fuer zlib.compress). Der Dateiname der
    temporaeren Datei enthaelt jetzt zusaetzlich zur Prozess-ID auch
    die Thread-ID: seit _thumb_cache_put_async() unten mehrere
    Aufrufe gleichzeitig aus verschiedenen Hintergrund-Threads
    passieren koennen (z.B. wenn kurz hintereinander zweimal dieselbe
    noch nicht gecachte Cover-Groesse gebraucht wird), wuerden zwei
    Threads sonst dieselbe .tmp-Datei benutzen und sich gegenseitig
    beim Schreiben ueberschreiben (kaputte/vermischte Bytes vor dem
    finalen os.replace()). Mit der Thread-ID im Namen bekommt jeder
    Aufruf garantiert seine eigene temporaere Datei - os.replace()
    bleibt weiterhin atomar, im schlimmsten Fall "gewinnt" einfach
    der zuletzt fertige Thread mit einem (identischen) Ergebnis."""
    try:
        os.makedirs(THUMB_CACHE_DIR, exist_ok=True)
        cpath = _thumb_cache_path(_thumb_cache_key(path, w, h))
        tmp = cpath + ".tmp%d_%d" % (os.getpid(), threading.get_ident())
        with open(tmp, "wb") as f:
            f.write(b"ART1" + struct.pack("<HH", tw, th) + zlib.compress(pix, 6))
        os.replace(tmp, cpath)
    except OSError as e:
        LOG("THUMB_CACHE Schreibfehler (%s): %s" % (os.path.basename(path), e))
        return
    _thumb_cache_evict_if_needed()

def _thumb_cache_put_async(path, w, h, tw, th, pix):
    """Wie _thumb_cache_put(), aber nicht-blockierend.

    NEU (Nutzerwunsch: "das muss schneller laufen!!" - dritte
    DRAGEND_PROFILE-Log-Datei mit echten Scroll-Messungen zeigte:
    das Schreiben der frisch berechneten Miniatur auf die SD-Karte
    (inkl. zlib.compress UND dem Verzeichnis-Scan in
    _thumb_cache_evict_if_needed()) lief bisher SYNCHRON mitten im
    Zeichenpfad - z.B. "_thumb_cache_put: 380ms" bei einem insgesamt
    1210ms-Aufruf fuer 'Taekwon-Do (Korea).art", also rund 30% der
    gesamten gemessenen Blockierzeit, nur fuer das Wegschreiben einer
    Kopie, die fuer die AKTUELLE Anzeige gar nicht mehr gebraucht
    wird (das fertige Bild liegt zu diesem Zeitpunkt schon im
    Speicher-Cache 'self.scaled' UND wird an den Aufrufer zurueck-
    gegeben). Der Festplatten-Cache ist reine Optimierung fuer
    SPAETERE Zugriffe (naechstes Vorbeiscrollen, naechster Start) -
    er muss also nicht fertig sein, bevor der aktuelle Frame steht.

    Bewusst ein eigener, kurzlebiger Thread PRO AUFRUF statt eines
    dauerhaften Warteschlangen-Worker-Threads: das Schreiben passiert
    ohnehin nur bei einem echten Skalierungs-Fehltreffer (nicht bei
    jedem Scrollschritt), der Thread beendet sich von selbst sobald
    die Datei geschrieben ist. daemon=True, damit ein noch laufender
    Schreibvorgang das Beenden des Frontends nicht blockiert. Fehler
    werden bewusst verschluckt (nicht Aufgabe des Aufrufers, auf
    einen Hintergrund-Schreibvorgang zu warten oder zu reagieren -
    _thumb_cache_put() selbst loggt einen etwaigen Fehlschlag ja
    bereits, siehe deren Docstring oben)."""
    def _run():
        try:
            _thumb_cache_put(path, w, h, tw, th, pix)
        except Exception:
            pass
    threading.Thread(target=_run, daemon=True).start()

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
    # NEU (Nutzer-Rueckmeldung "rendert der die Boxarts immer neu?"):
    # bisher lief die Verdraengung voellig lautlos. Ob der Zwischen-
    # speicher zu klein ist, liess sich damit nur raten. Diese Zeile
    # macht es im Log unmittelbar sichtbar - taucht sie regelmaessig
    # auf, ist die Sammlung groesser als THUMB_CACHE_MAX_FILES und
    # genau DAS ist der Grund fuer wiederkehrendes Neuberechnen.
    LOG("THUMB_CACHE Verdraengung: %d von %d Eintraegen entfernt "
        "(Obergrenze %d) - taucht das oft auf, ist die Obergrenze fuer "
        "diese Sammlung zu klein."
        % (to_remove, len(entries), THUMB_CACHE_MAX_FILES))

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
        # Wird gesetzt, sobald wegen _defer_uncached wirklich etwas
        # uebersprungen wurde - siehe die drei Fundstellen unten und
        # den COVER_SETTLE-Handler in frontend.py.
        self._deferred_something = False
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
            # NEU (siehe _settle_needed in frontend.py): festhalten,
            # DASS hier tatsaechlich etwas uebersprungen wurde. Nur dann
            # muss der COVER_SETTLE-Nachlader spaeter ueberhaupt neu
            # zeichnen - liegen alle Cover bereits im Cache (der
            # Normalfall, sobald der Festplatten-Cache warm ist), gibt es
            # nichts nachzuladen, und der komplette Seitenaufbau nach
            # jedem Stillstand entfaellt.
            self._deferred_something = True
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
                # NEU (siehe _settle_needed in frontend.py): festhalten,
                # DASS hier tatsaechlich etwas uebersprungen wurde. Nur dann
                # muss der COVER_SETTLE-Nachlader spaeter ueberhaupt neu
                # zeichnen - liegen alle Cover bereits im Cache (der
                # Normalfall, sobald der Festplatten-Cache warm ist), gibt es
                # nichts nachzuladen, und der komplette Seitenaufbau nach
                # jedem Stillstand entfaellt.
                self._deferred_something = True
                return None
            sw, sh = w * scale, h * scale
            out = bytearray(sw * sh * 4)
            row_out = sw * 4
            # GEAENDERT (Nutzerwunsch: "das muss schneller laufen!!" -
            # dritte DRAGEND_PROFILE-Log-Datei zeigte diese Schleife als
            # groessten Einzelposten beim Aufreissen der Anzeige, z.B.
            # "fe/art.py:570(<genexpr>): 565ms (65792 Aufrufe)" bei
            # einem 773ms-join fuer ein einzelnes Cover. Zwei kleine,
            # aber MESSBAR wirksame Aenderungen (per Differenzmessung
            # bestaetigt, siehe /tmp/bench_upscale.py):
            # 1) Die Ursprungszeile wird jetzt EINMAL pro Durchlauf aus
            #    "pix" herausgeschnitten ("src_row") statt bei JEDEM der
            #    w Pixel erneut ueber den vollen, viel groesseren "pix"-
            #    Puffer plus Offset-Arithmetik zuzugreifen.
            # 2) Eine LISTENABSTRAKTION ("[... for x in range(w)]") statt
            #    des vorherigen GENERATORS ("... for x in range(w)" ohne
            #    Klammern) - b"".join() kann eine fertige Liste schneller
            #    durchlaufen als einen Generator, der bei jedem Element
            #    einen eigenen Interpreter-Frame-Wechsel braucht. Genau
            #    dasselbe Muster (Liste statt Generator) wird beim
            #    Verkleinern weiter unten schon seit dessen eigenem
            #    Performance-Fix verwendet - hier war es bisher nur
            #    nicht konsequent uebernommen worden.
            # EHRLICH DOKUMENTIERT: das ist eine Verbesserung des
            # Konstantfaktors (in Sandbox-Messungen ca. 10-15% schneller),
            # KEIN grundlegend anderer, asymptotisch schnellerer
            # Algorithmus - die Schleife bleibt weiterhin ein reiner
            # Python-Pixel-Durchlauf ohne numpy/C-Erweiterung (bewusst,
            # um keine zusaetzliche Abhaengigkeit auf der ohnehin schon
            # eng bemessenen MiSTer-SD-Karte/Offline-Installation
            # einzufuehren). In Kombination mit dem asynchronen
            # Festplatten-Cache-Schreiben (siehe _thumb_cache_put_async()
            # in fe/art.py) sollte die spuerbare Blockierzeit trotzdem
            # deutlich sinken, auch wenn ein Rest bleibt - ob und wie
            # viel, muss die naechste echte Hardware-Messung zeigen.
            for y in range(h):
                src_row = pix[y * w * 4:(y + 1) * w * 4]
                row = b"".join([src_row[x*4:x*4 + 4] * scale
                                 for x in range(w)])
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
            #
            # GEAENDERT: _thumb_cache_put_async() statt _thumb_cache_put()
            # - siehe deren Docstring in fe/art.py (spart ca. 30% der
            # gemessenen Blockierzeit, da das Wegschreiben jetzt im
            # Hintergrund passiert statt die Anzeige des bereits fertig
            # berechneten "result" weiter zu verzoegern).
            _thumb_cache_put_async(path, max_w, max_h, sw, sh, result[2])
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
            # NEU (siehe _settle_needed in frontend.py): festhalten,
            # DASS hier tatsaechlich etwas uebersprungen wurde. Nur dann
            # muss der COVER_SETTLE-Nachlader spaeter ueberhaupt neu
            # zeichnen - liegen alle Cover bereits im Cache (der
            # Normalfall, sobald der Festplatten-Cache warm ist), gibt es
            # nichts nachzuladen, und der komplette Seitenaufbau nach
            # jedem Stillstand entfaellt.
            self._deferred_something = True
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
        # GEAENDERT (Nutzer-Rueckmeldung: "auf halb und viertel sehen die
        # Boxarts verpixelt aus"): hier stand bisher ein reines
        # Nearest-Neighbor-Verfahren - fuer jede Zielposition wurde EIN
        # Quellpixel gegriffen, der Rest fiel weg. Jetzt wird ueber die
        # zusammenfallenden Quellpixel gemittelt. Siehe die ausfuehrliche
        # Begruendung samt Messwerten bei _verkleinern_flaechenmittel().
        # Die Zielgroesse (tw/th) ist unveraendert - nur der Inhalt ist
        # ein anderer, deshalb ist auch THUMB_ALGO_VERSION hochgezaehlt
        # worden (sonst wuerden die alten, grob verkleinerten Miniaturen
        # aus dem Festplatten-Cache weiterverwendet).
        data = _verkleinern_flaechenmittel(pix, w, h, tw, th)
        if data is None:
            return None
        result = (tw, th, data)
        self._scaled_cache_put(box_key, result)
        # WICHTIGE QUALITAETS-REGEL (siehe Modul-Kommentar oben): immer
        # das soeben aus dem Original berechnete "result" speichern,
        # niemals eine bereits vorhandene Miniatur weiterverarbeiten.
        #
        # GEAENDERT: _thumb_cache_put_async() statt _thumb_cache_put() -
        # gleicher Grund wie beim Hochskalieren oben (siehe dortiger
        # Kommentar und der Docstring von _thumb_cache_put_async() in
        # fe/art.py): das Wegschreiben ist reine Optimierung fuer
        # spaeter und muss die Anzeige des schon fertigen "result"
        # nicht mehr blockieren.
        _thumb_cache_put_async(path, max_w, max_h, tw, th, result[2])
        return result

ART = ArtCache()

class BgCache:
    """Haelt pro System einen fertig komponierten Vollbild-Puffer
    (inkl. Stride-Padding), damit der Hintergrund beim Zeichnen nur
    noch per Blockkopie eingesetzt werden muss."""
    # ERHOEHT von 2 auf 4 (Nutzer-Rueckmeldung: "wenn ich aus einem
    # ROM-Ordner zurueckgehe, haengt das Frontend ab und zu kurz").
    #
    # Ein Fehltreffer hier ist teuer: _compose() setzt den kompletten
    # Bildschirminhalt neu zusammen - bei 1920x1080 sind das 8,3 MB,
    # zeilenweise in Python. Nachgemessen 41-67 ms auf einer schnellen
    # Sandbox, auf der MiSTer-CPU entsprechend deutlich mehr. Mit nur
    # ZWEI Plaetzen genuegte das Hin- und Herwechseln zwischen drei
    # Systemen, damit jeder Wechsel wieder einen kompletten Neuaufbau
    # ausgeloest hat.
    #
    # Preis ehrlich benannt: jeder Platz kostet einen vollen
    # Bildschirmpuffer - bei 1080p rund 8,3 MB, bei vier Plaetzen also
    # etwa 33 MB. Auf einem MiSTer mit typischerweise ~1 GB RAM
    # vertretbar, aber kein Freibier; deshalb 4 und nicht 8. Mit
    # kleinerem Framebuffer (Menuepunkt "Menue-Aufloesung") sinkt der
    # Bedarf entsprechend mit (bei halber Groesse ein Viertel davon).
    LIMIT = 4

    def __init__(self):
        self.cache = {}
        self.order = []

    def get(self, syskey, fb):
        # BUGFIX (beim erneuten Durchgehen ungetesteter Fixes gefunden,
        # nicht Teil der eigentlich angefragten Aenderung: der
        # zusammengesetzte Puffer bettet in _compose() die AKTUELL
        # aktive C_BG-Farbe als Rand-/Letterbox-Fuellung ein (fuer
        # Hintergrundbilder, die nicht exakt die Bildschirmgroesse
        # treffen) - der Cache-Schluessel enthielt das Theme bisher
        # NICHT. Nach einem Themenwechsel waehrend der Sitzung haette
        # ein bereits gecachter Eintrag fuer denselben syskey/dieselbe
        # Aufloesung die FARBE DES ALTEN THEMES behalten, bis er durch
        # LRU-Verdraengung (LIMIT=2) zufaellig rausfiel. Betrifft NICHT
        # den kuerzlich gebauten HDMI-Fast-Path (der verhaelt sich hier
        # nachweislich identisch zum vorherigen Code, siehe Pixel-
        # Vergleichstest) - ein eigenstaendiger, aelterer Fund.
        key = (syskey, fb.width, fb.height, fb.stride, _fb_mod.C_BG)
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
    # NEU (Nutzerwunsch: "solltest du das als sysart anlegen, wenn man
    # auf Wonne oder Tonne geht wird es in der Art-Box angezeigt" -
    # bisher zeigte die Art-Box beim Markieren dieses Menuepunkts nur
    # den generischen Platzhalter, da "Wonne oder Tonne" wie
    # Weiterspielen/Zuletzt gespielt mit syskey=None angelegt wird,
    # aber hier oben noch fehlte): gleiches Prinzip, fester
    # sprachunabhaengiger Schluessel "WOT" - Bilddatei liegt unter
    # SYSART_BASE/WOT.art.
    if name == t("wot_title"):
        return "WOT"
    # NEU (Nutzerwunsch: "fuer Arcade, Computer und System im Hauptmenue
    # kleine Sysart erstellen, da steht noch kein Artwork vorhanden") -
    # "Arcade" bekommt seinen Schluessel bereits automatisch (siehe
    # scan.py: syskey="ARCADE", sobald der Ordnername "arcade" enthaelt),
    # "System" und "Computer" aber nicht - beide werden mit syskey=None
    # angelegt (System: fest in frontend.py, "Computer": Name eines
    # Ordners auf der SD-Karte des Nutzers, kommt ueber scan_games()).
    # Bewusst GEGEN den woertlichen String verglichen, nicht ueber t() -
    # "System" ist im Code selbst nicht uebersetzt (siehe
    # self.cats.append(("System", ...)) in frontend.py), und
    # "Computer" ist kein Uebersetzungsschluessel, sondern exakt der
    # Ordnername des Nutzers, wie er im Menue erscheint - bei anderen
    # Nutzern mit anders benanntem Ordner greift dieser Sonderfall
    # entsprechend nicht, das ist eine bekannte, hier bewusst in Kauf
    # genommene Einschraenkung (im Gegensatz zu "System", das bei
    # JEDEM Nutzer identisch heisst).
    if name == "System":
        return "SYSTEM"
    if name == "Computer":
        return "COMPUTER"
    # NEU (Nutzerwunsch: eigenes Artwork auch fuer "Favoriten" und
    # "Sammlungen" im Hauptmenue) - gleiches Prinzip wie oben bei
    # Weiterspielen/Zuletzt gespielt/Wonne oder Tonne: beide Kategorien
    # werden mit syskey=None angelegt (build_categories(): eigene,
    # kuratierte bzw. gemischte Auswahl statt eines echten Systems),
    # der Vergleich laeuft daher wieder ueber t(...) statt eines festen
    # Strings. "Sammlungen" bekommt im Menuenamen zusaetzlich die
    # Anzahl angehaengt ("%s (%d)" % (t("collections_cat"), count)) -
    # deshalb hier bewusst startswith() statt "==", "Favoriten" bleibt
    # dagegen ein exakter Vergleich wie "Weiterspielen"/"Zuletzt
    # gespielt" (keine Zahl im Namen).
    if name == t("favorites_cat"):
        return "FAVORITES"
    if name.startswith(t("collections_cat")):
        return "COLLECTIONS"
    # NEU (Nutzerwunsch: "wir braeuchten fuer diese Kategorie auch noch
    # eine Artwork die dann daneben in der Boxart erscheint" - RA-
    # Erfolgsjaeger zeigte bisher nur den generischen "kein Artwork"-
    # Platzhalter): exakt dasselbe Muster wie bei "Sammlungen" - die
    # Kategorie wird mit syskey=None angelegt (build_ra_hunter_category()
    # mischt ja RA-Spiele aus mehreren Systemen) und der Menuename traegt
    # zusaetzlich die Trefferanzahl ("%s (%d)" % (t("ra_hunter_cat"),
    # count), siehe build_categories()) - deshalb wieder startswith()
    # statt "==". Bilddatei liegt unter SYSART_BASE/RA_HUNTER.art
    # (eigens erstelltes Pokal-/Controller-Motiv, bewusst KEIN Nachbau
    # des echten RetroAchievements-Markenlogos).
    if name.startswith(t("ra_hunter_cat")):
        return "RA_HUNTER"
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

