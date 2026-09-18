#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Boxart-Verwaltung: eigener PNG-Decoder (fuer RA-Erfolgs-Icons),
ArtCache (Cover/Logos im eigenen .art-Format), Metadaten-Cache.
Ausgelagert aus frontend.py (Modularisierung, Git-Branch
'modular-refactor').

Pfad-Konstanten (ART_BASE/ART_HD/SYSART_BASE/META_BASE) leben
jetzt HIER als ihr eigentliches Zuhause (vorher in frontend.py, an
mehreren weit entfernten Stellen im restlichen Code verwendet) -
frontend.py importiert sie von hier zurueck, damit alle bisherigen
Verwendungsstellen unveraendert weiterlaufen.
"""
import os, re, struct, zlib, json, time, urllib.request, hashlib, threading
import operator
from fe.log import LOG
from fe.translations import t

# Systembibliotheken fuer Bilder (Build 115). Bewusst mit Netz und
# doppeltem Boden geladen: fehlt das Modul oder laesst sich keine
# Bibliothek finden, bleibt _BILDLIB None und alles laeuft wie vorher
# ueber den Python-Dekoder weiter.
try:
    import fe.bildlib as _BILDLIB
    if not (_BILDLIB.png_verfuegbar() or _BILDLIB.verfuegbar()):
        _BILDLIB = None
except Exception:       # pragma: no cover - nur auf kaputten Installationen
    _BILDLIB = None

ART_BASE    = "/media/fat/frontend/art"
ART_HD      = "/media/fat/frontend/art_hd"
SYSART_BASE = "/media/fat/frontend/sysart"
META_BASE   = "/media/fat/frontend/meta"

# FREMDE QUELLE (Build 115): die Handbuch-/Artwork-Datenbank, die viele
# MiSTer-Nutzer ueber den Downloader installiert haben. Aufbau:
#
#   /media/fat/docs/<Core>/Artwork/<ROM-Name>.jpg
#   /media/fat/docs/<Core>/Artwork/gameinfo.tsv
#   /media/fat/docs/<Core>/Manuals/*.pdf
#
# Auf dem Geraet des Nutzers liegen dort 21.198 Cover und 147
# Systemordner, benannt wie die MiSTer-Cores - also genau wie die
# Ordnernamen, die unsere eigene Systemliste ohnehin schon fuehrt.
# Gefunden wurde das erst, nachdem die Suche nach Ordnern namens
# "*artwork*" und nach gamelist.xml zweimal ins Leere lief: der
# Elternordner heisst "docs", dort wurden Handbuecher vermutet.
#
# WIR SCHREIBEN DORT NIE HIN. Reiner Lesepfad, und nur als Rueckfall -
# eigenes Artwork hat immer Vorrang.
DOCS_BASE   = "/media/fat/docs"
DOCS_INFO   = "gameinfo.tsv"

# NEUES FEATURE (Build 139, Nutzerfund): neben gameinfo.tsv liegt in
# denselben Ordnern eine BESCHREIBUNG je Spiel - und zwar in sechs
# Sprachen, eine Datei je Sprache:
#
#   synopsis_de.tsv  synopsis_en.tsv  synopsis_es.tsv
#   synopsis_fr.tsv  synopsis_it.tsv  synopsis_pt.tsv
#
# Aufbau wie gameinfo.tsv: "#key<TAB>synopsis", ein Spiel je Zeile.
#
# NACHGEMESSEN an der SNES-Datei des Nutzers: 1785 von 1802
# Schluesseln haben eine Beschreibung (99%), das Einlesen einer
# Systemdatei dauert 4 ms, sie belegt danach 1,3 MB, und ein Text ist
# im Mittel 640 Zeichen lang.
#
# Das Frontend fuehrt nur Deutsch und Englisch (siehe
# fe/translations.py) - die uebrigen vier Dateien werden bewusst nicht
# gelesen. Wer Deutsch eingestellt hat und fuer ein Spiel keinen
# deutschen Text findet, bekommt den englischen; umgekehrt nicht, das
# waere in einer englischen Oberflaeche ein deutscher Absatz.
DOCS_SYNOPSIS = "synopsis_%s.tsv"
DOCS_SPRACHEN = ("de", "en")
# Wie viele Systemdateien gleichzeitig im Speicher bleiben duerfen.
# Anders als gameinfo.tsv (168 kB) ist eine Synopsis-Datei 1,3 MB
# gross - wer durch zwanzig Systeme blaettert, haette sonst 26 MB
# Text im Speicher, den niemand mehr anschaut. Zwei reichen: das
# aktuelle System und das, aus dem man gerade gekommen ist.
DOCS_SYNOPSIS_MAX = 2

# Weitere Orte, an denen Artpacks landen (Build 120). Nicht jedes Paket
# legt sich unter "docs" ab - manche bringen einen eigenen
# Artwork-Ordner mit. Die Spiele-Wurzeln kommen zusaetzlich dazu, siehe
# fremd_wurzeln().
FREMD_ZUSATZ_WURZELN = (
    "/media/fat/Artwork",
    "/media/fat/artwork",
    "/media/fat/boxart",
    "/media/fat/Boxart",
)

# Unterordner, in denen ein Paket seine Bilder ablegt - "" steht fuer
# "direkt im Systemordner", das kommt ebenfalls vor. Reihenfolge =
# Suchreihenfolge.
#
# Die Named_*-Namen stammen aus der libretro-/EmulationStation-Welt und
# sind bei Artpacks die verbreitetste Schreibweise. Bewusst NUR
# Boxarts: Named_Snaps und Named_Titles sind Bildschirmfotos, und ein
# Bildschirmfoto an der Stelle einer Verpackung waere eine unangenehme
# Ueberraschung. Wer sie will, legt sie in einen der obigen Ordner.
DOCS_UNTERORDNER = ("Artwork", "Named_Boxarts", "Boxarts", "boxart",
                    "Covers", "covers", "")

# Rueckwaertskompatibel: einzelner Unterordner, wie ihn Build 115
# kannte. Bleibt erhalten, weil Tests und aeltere Fassungen ihn
# benutzen.
DOCS_UNTER  = "Artwork"

# Obergrenze fuer fremde Bilder: ein Cover ist ein Cover, kein
# Buchseiten-Scan. Siehe ArtCache.get().
FREMD_MAX_KANTE = 1200

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
    rgba_bytes). Liefert None bei JEDEM nicht unterstuetzten oder
    fehlerhaften Fall - NIE eine Ausnahme nach aussen.

    GEAENDERT (Build 115): zuerst wird libpng ueber fe/bildlib.py
    versucht. Auf dem MiSTer liegt die Bibliothek da, nur eben weder
    als Python-Modul noch als Kommandozeilenwerkzeug - deshalb ist sie
    jahrelang uebersehen worden. Der Unterschied ist kein Feinschliff:
    gemessen 2,6 ms gegen 140 ms fuer dasselbe Bild, auf dem Geraet
    also grob 30 ms statt 200-500 ms.

    Die Fassung darunter bleibt vollstaendig erhalten und uebernimmt,
    wenn die Bibliothek fehlt. Damit kann diese Aenderung nichts
    verschlechtern: entweder es wird schneller, oder es bleibt genau
    wie es war. Dass beide Wege dasselbe Bild liefern, ist ueber alle
    Farbtypen bitgenau nachgewiesen (tools/test_bildlib.py)."""
    if _BILDLIB is not None:
        fertig = _BILDLIB.decode_png_lib(data)
        if fertig is not None:
            return fertig
        # Kein stiller Verzicht: libpng kann an einem Bild scheitern,
        # das unsere Fassung noch schafft (und umgekehrt). Wer hier
        # ankommt, hat nichts verloren ausser ein paar Mikrosekunden.
    return _decode_png_python(data)


def _decode_png_python(data):
    """Der urspruengliche, reine Python-Dekoder (siehe decode_png()).

    BEWUSST EINGESCHRAENKT (lieber None als ein falsches Bild): nur
    8-Bit Farbtiefe, nicht interlaced, Farbtypen 0/2/3/4/6."""
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

        # Zu BGRA vereinheitlichen, unabhaengig vom Quell-Farbtyp - so
        # muss der Rest des Frontends (blit() usw.) nur EIN Format
        # kennen, egal welcher PNG-Farbtyp reinkam.
        #
        # BUGFIX (Build 126, Nutzer-Rueckmeldung: "die Farben von den
        # Boxarts passen nicht"): hier stand RGBA. Der Bildspeicher des
        # MiSTer ist aber BGRA - dieselbe Farbe, die fb.rect((255,0,0))
        # als (0,0,255,a) ablegt, und dasselbe, was der .art-Dekoder
        # liefert. Rot und Blau waren auf jedem PNG vertauscht.
        #
        # PNG legt seine Bytes als R,G,B ab. Umgedreht wird deshalb
        # HIER, an der einen Stelle, an der aus Quellbytes unsere
        # Bildpunkte werden - nicht spaeter mit einem zweiten Durchlauf
        # ueber Millionen Bytes.
        n_px = width * height
        out = bytearray(n_px * 4)
        if colortype == 6:      # RGBA -> BGRA
            out[:] = pixels
            out[0::4] = pixels[2::4]
            out[2::4] = pixels[0::4]
        elif colortype == 2:    # RGB -> BGRA (Alpha immer deckend)
            for i in range(n_px):
                r, g, b = pixels[i * 3], pixels[i * 3 + 1], pixels[i * 3 + 2]
                out[i * 4] = b
                out[i * 4 + 1] = g
                out[i * 4 + 2] = r
                out[i * 4 + 3] = 255
        elif colortype == 0:    # Graustufen - Reihenfolge egal
            for i in range(n_px):
                g = pixels[i]
                out[i * 4] = out[i * 4 + 1] = out[i * 4 + 2] = g
                out[i * 4 + 3] = 255
        elif colortype == 4:    # Graustufen+Alpha - Reihenfolge egal
            for i in range(n_px):
                g = pixels[i * 2]
                out[i * 4] = out[i * 4 + 1] = out[i * 4 + 2] = g
                out[i * 4 + 3] = pixels[i * 2 + 1]
        elif colortype == 3:    # Palette -> BGRA
            if not palette:
                return None
            for i in range(n_px):
                idx = pixels[i]
                p = idx * 3
                if p + 3 > len(palette):
                    return None
                out[i * 4] = palette[p + 2]
                out[i * 4 + 1] = palette[p + 1]
                out[i * 4 + 2] = palette[p]
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
# GEAENDERT (Build 85, Nutzerwunsch: "bitte fuer jeden Modus, also CRT
# und HDMI, einen eigenen Cache anlegen - quasi einmal SD-Variante fuer
# CRT-Modus und einmal HD-Variante fuer HDMI-Modus").
#
# Ab jetzt drei Ebenen statt einer:
#
#   thumb_cache/hd/a7/a7f3....art      HDMI-Miniaturen
#   thumb_cache/sd/1c/1c90....art      CRT-Miniaturen
#
# WARUM getrennt nach Modus: die Kastengroessen der beiden Modi haben
# nichts miteinander zu tun, und wer nur einen davon benutzt, schleppt
# den anderen als toten Ballast mit. Getrennt laesst sich der ungenutzte
# Teil in einem Rutsch loeschen, und eine lange HDMI-Sitzung kann die
# CRT-Eintraege nicht mehr nach und nach verdraengen.
#
# WARUM die zusaetzliche Zwischenebene aus zwei Zeichen des Schluessels:
# /media/fat ist ueblicherweise exFAT, und dort ist das Nachschlagen in
# einem Verzeichnis LINEAR - jedes Oeffnen einer Datei laeuft die
# Verzeichniseintraege durch. Mit der auf Nutzerwunsch angehobenen
# Obergrenze von 40000 waere ein einzelner flacher Ordner doppelt so
# teuer wie der bisherige. 256 Unterordner machen daraus rund 156
# Eintraege je Ordner - der Punkt faellt damit ganz weg.
#
# EHRLICH BENANNT: die Umstellung entwertet den bestehenden
# Zwischenspeicher nicht (die Schluessel bleiben gleich), aber die alten
# Dateien liegen am falschen Ort und werden nicht mehr gefunden. Sie
# werden beim ersten Start nach dem Update im Hintergrund aufgeraeumt -
# siehe alten_flachen_cache_aufraeumen().
THUMB_CACHE_BASE = "/media/fat/frontend/thumb_cache"
THUMB_CACHE_DIR = os.path.join(THUMB_CACHE_BASE, "hd")


def thumb_cache_modus_setzen(hd):
    """Legt fest, ob der HD- oder der SD-Zwischenspeicher benutzt wird.

    Aufgerufen vom Frontend beim Start (und nach einem Aufloesungs-
    wechsel) anhand derselben Bedingung, nach der auch die Cover-Quelle
    gewaehlt wird: ART_HD ab 720 Bildzeilen, sonst ART_BASE."""
    global THUMB_CACHE_DIR, _thumb_cache_anzahl, _thumb_cache_seit_zaehlung
    neu_dir = os.path.join(THUMB_CACHE_BASE, "hd" if hd else "sd")
    if neu_dir == THUMB_CACHE_DIR:
        return THUMB_CACHE_DIR
    THUMB_CACHE_DIR = neu_dir
    # Der mitgefuehrte Zaehler gilt fuer den ALTEN Ordner - verwerfen,
    # sonst wuerde im neuen sofort falsch verdraengt.
    _thumb_cache_anzahl = None
    _thumb_cache_seit_zaehlung = 0
    LOG("THUMB_CACHE: Modus %s -> %s" % ("HD" if hd else "SD", THUMB_CACHE_DIR))
    return THUMB_CACHE_DIR


def alten_flachen_cache_aufraeumen():
    """Die Dateien der Vorgaengerfassung entfernen, die direkt in
    thumb_cache/ liegen statt in hd/ bzw. sd/.

    Sie werden nach der Umstellung nie wieder gefunden - liegen bleiben
    wuerden sie trotzdem, bei einer grossen Sammlung mehrere Gigabyte.
    Bewusst nur die losen .art-Dateien der obersten Ebene, die
    Unterordner bleiben unangetastet."""
    entfernt = 0
    try:
        for fn in os.listdir(THUMB_CACHE_BASE):
            if not (fn.endswith(".art") or ".art.tmp" in fn):
                continue
            try:
                os.remove(os.path.join(THUMB_CACHE_BASE, fn))
                entfernt += 1
            except OSError:
                pass
    except OSError:
        return 0
    if entfernt:
        LOG("THUMB_CACHE: %d Dateien der alten, flachen Ablage entfernt "
            "(liegen seit Build 85 in hd/ bzw. sd/)" % entfernt)
    return entfernt

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
# DRITTE ERHOEHUNG 20000 -> 40000 (Nutzerwunsch, nachdem sein Ordner mit
# 20008 Dateien exakt an der Grenze klebte): 10000 Spiele mit Cover in
# zwei Modi sind 20000 Eintraege - die alte Grenze war damit auf Kante
# genaeht. Die Grenze gilt jetzt JE MODUS (hd/ und sd/ getrennt), es
# koennen also bis zu 80000 Dateien zusammenkommen. Bei grob 150 KB je
# HDMI- und 15 KB je CRT-Miniatur sind das im Extremfall rund 6.6 GB -
# auf einer 128-GB-Karte unkritisch, auf einer kleinen nicht. Wer knapp
# bei Platz ist, setzt den Wert hier herunter; thumb_cache_stand()
# schreibt die tatsaechliche Belegung nach jedem Durchlauf ins Log.
# GEAENDERT (Build 128): 40000 -> 150000.
#
# Der Nutzer, der Build 128 ausgeloest hat, meldete einen Durchlauf von
# "Miniaturen vorbereiten", der nach SECHS STUNDEN nicht fertig war. Die
# Zahlen von seinem Geraet:
#
#     28517 Cover
#      x  4 Kastengroessen (Build 122-127)
#     -------------------------------------
#    114068 Dateien noetig  -  bei einer Obergrenze von 40000
#
# Das war kein Geschwindigkeitsproblem. Der Durchlauf haette NIE fertig
# werden koennen: ab 40000 Dateien raeumt die Verdraengung auf 36000
# herunter, und das Aelteste ist genau das, was derselbe Durchlauf zwei
# Stunden vorher gerechnet hat. Er hat sich im Kreis gedreht, und die
# Zeile "THUMB_CACHE Verdraengung" haette es gesagt - nur steht das Log
# in /tmp und ist nach einem Neustart weg.
#
# Build 128 nimmt eine der vier Kastengroessen wieder heraus (siehe
# kachel_cover_kasten() in frontend.py), es bleiben 85551. Die Grenze
# muss also darueber liegen, mit Luft fuer eine groessere Sammlung.
#
# WARUM UEBERHAUPT EINE GRENZE, und warum diese: sie schuetzt nicht den
# Speicherplatz - die Dateien sind klein und der Ordner darf jederzeit
# von Hand geleert werden -, sondern die Verdraengung selbst. Die
# durchlaeuft im Ernstfall den ganzen Ordner mit einem
# os.path.getmtime je Datei. Bei 150000 Dateien auf einer SD-Karte
# dauert das, und deshalb steht daneben, dass es hoechstens alle 15000
# Schreibvorgaenge passiert (Zielfuellung 90 %).
#
# EHRLICH DAZU: bei sehr grossen Sammlungen braucht der Zwischenspeicher
# Platz. Auf dem Geraet des Nutzers lagen bei 26403 Dateien 9.8 GB. Die
# Marke aus Build 128 (siehe ORIGINAL_PASST) nimmt davon den groessten
# Einzelposten weg, aber zweistellige Gigabyte bleiben moeglich. Wer das
# nicht hat, kann den Ordner jederzeit loeschen oder ueber
# "Zwischenspeicher leeren" im Menue leeren - es geht dabei nichts
# verloren ausser Rechenzeit.
THUMB_CACHE_MAX_FILES = 150000

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
# GEAENDERT (Build 126): von "2" auf "3". Alle Miniaturen, die aus
# einem PNG oder JPG gerechnet wurden, liegen mit vertauschtem Rot und
# Blau auf der Karte (siehe _decode_png_python() oben). Sie sind nicht
# daran zu erkennen - im Schluessel steht der Quellpfad, nicht das
# Quellformat -, also muessen sie alle einmal neu.
#
# Der Preis ist ein einmaliger Durchlauf von "Miniaturen vorbereiten".
# Die Alternative waere, nach der Dateiendung der Quelle zu
# unterscheiden und nur die betroffenen zu verwerfen - mehr Code, mehr
# Wege, etwas zu uebersehen, und am Ende blieben genau die falschen
# Bilder liegen, die man loswerden will.
THUMB_ALGO_VERSION = "3"


# Die beiden Rechenoperationen als fertige Funktionen - map() ruft sie
# dann in C auf, statt fuer jedes Element einen Python-Rahmen zu bauen.
# Siehe _verkleinern_flaechenmittel().
_addiere = operator.add
_ganzzahlig = operator.floordiv


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

    UMSETZUNG: getrennt nach Achsen. Es wird immer nur EINE Zielzeile
    im Speicher gehalten (kein kompletter Zwischenpuffer) - auf einem
    Geraet mit ~1 GB RAM und HD-Covern ein bewusster Verzicht.

    UMGEBAUT (Build 118). Nach Build 115/116 war dieses Verkleinern der
    ganze Rest: vom kalten Cover auf HDMI entfielen 97 von 101 ms
    darauf. Gemessen steckten 73 % davon in der inneren Summenschleife,
    19 % in den Divisionen.

    Zwei Aenderungen, beide bitgenau ergebnisgleich (nachgewiesen in
    tools/test_verkleinern.py ueber Zufallsgroessen):

    1. EIN SCHNELLER WEG fuer den Fall, dass jede Zielspalte aus
       hoechstens ZWEI Quellspalten entsteht - also fuer jede
       Verkleinerung schwaecher als 3:1. Genau das ist der HDMI-Fall
       (424x768 in einen 360x420-Kasten sind Faktor 1,8). Dort kostete
       ein sum() auf einem Ausschnitt von zwei Werten mehr als die zwei
       Werte selbst: der Ausschnitt muss angelegt, der Aufruf gemacht
       werden. Jetzt werden die beiden Quellwerte direkt adressiert.
       Gemessen 99 -> 46 ms.

    2. Auch der allgemeine Weg arbeitet jetzt auf KANALEBENEN
       (row[0::4] einmal je Zeile) statt auf Ausschnitten mit
       Schrittweite 4, und die Zielzeile wird per Ausschnitt-Zuweisung
       gesetzt statt Bildpunkt fuer Bildpunkt. Gemessen rund 10 %
       weniger, quer ueber alle Verkleinerungsfaktoren.

    Bewusst kein numpy o.ae. - das Frontend bleibt abhaengigkeitsfrei."""
    if tw <= 0 or th <= 0 or w <= 0 or h <= 0:
        return None
    # Quell-Spaltenbereich je Zielspalte, einmal vorab.
    grenzen = []
    nx = []
    for x in range(tw):
        a = int(x * w / tw)
        b = max(a + 1, int((x + 1) * w / tw))
        grenzen.append((a, b))
        nx.append(b - a)
    rw = w * 4
    ro = tw * 4
    out = bytearray(tw * th * 4)
    ziel = memoryview(out)
    schmal = max(nx) <= 2

    if schmal:
        # Zwei feste Quellspalten je Zielspalte. Bei einer Ein-Pixel-
        # Gruppe zeigen beide auf denselben Wert - er zaehlt dann
        # doppelt, weshalb der Teiler unten ebenfalls verdoppelt wird.
        # Das ist billiger als eine Fallunterscheidung im inneren
        # Durchlauf, und das Ergebnis ist dasselbe.
        paare = [(a, b - 1) for a, b in grenzen]
        gewicht = [2 if v == 1 else v for v in nx]
    else:
        paare = None
        gewicht = nx

    for ty in range(th):
        y0 = int(ty * h / th)
        y1 = max(y0 + 1, int((ty + 1) * h / th))
        n = y1 - y0
        teiler = [v * n for v in gewicht]
        acc = None
        for y in range(y0, y1):
            row = pix[y * rw:(y + 1) * rw]
            if schmal:
                cur = [[e[i] + e[j] for i, j in paare]
                       for e in (row[0::4], row[1::4], row[2::4])]
            else:
                cur = [[sum(e[a:b]) for a, b in grenzen]
                       for e in (row[0::4], row[1::4], row[2::4])]
            if acc is None:
                acc = cur
            else:
                acc = [list(map(_addiere, p, q)) for p, q in zip(acc, cur)]
        zeile = ziel[ty * ro:(ty + 1) * ro]
        for k in (0, 1, 2):
            zeile[k::4] = bytes(map(_ganzzahlig, acc[k], teiler))
    return bytes(out)


def _thumb_cache_path(key):
    """Ablageort einer Miniatur: <cache>/<modus>/<2 Zeichen>/<schluessel>.art

    Die Zwischenebene aus den ersten zwei Zeichen des (hexadezimalen)
    Schluessels verteilt die Dateien auf 256 Unterordner - siehe
    Begruendung bei THUMB_CACHE_BASE."""
    return os.path.join(THUMB_CACHE_DIR, key[:2], key + ".art")

# ----------------------------------------------------------------------------
# DIE UHR, DIE NACH DEM START SPRINGT
# ----------------------------------------------------------------------------
# BUGFIX (Build 84, Nutzer-Rueckmeldung - und der entscheidende Hinweis
# kam von ihm selbst: "wenn das an der Uhr liegt, die aktualisiert sich
# ja immer erst nach ein paar Sekunden. Ich starte das Frontend, dann
# steht da 1.00, dann nach ein paar Sekunden springt sie auf die
# tatsaechliche Uhrzeit").
#
# Der MiSTer hat keine batteriegepufferte Uhr. Nach dem Einschalten
# steht sie auf 01:00; ein paar Sekunden spaeter setzt der
# NTP-Hintergrundthread sie auf die echte Zeit - im gemeldeten Fall ein
# Sprung um fast ZWOELF Stunden nach vorn.
#
# Die Verdraengung unten benutzt die Aenderungszeit der Cache-Datei als
# "zuletzt benutzt"-Marke. Damit passierte Folgendes:
#
#   1. Das Frontend liest beim Start alle Kategorie-Logos aus dem Cache
#      und stempelt sie per os.utime mit der FALSCHEN Zeit (01:00).
#   2. Sekunden spaeter springt die Uhr auf 12:48.
#   3. Damit liegen ausgerechnet die eben erst gelesenen Logos rund zwoelf
#      Stunden in der Vergangenheit - sie sind schlagartig die aeltesten
#      Dateien im ganzen Zwischenspeicher.
#   4. Ist der Cache voll, verdraengt der naechste Schreibvorgang genau
#      sie.
#
# Ergebnis: die Logos flogen raus, WEIL sie gerade benutzt wurden - die
# Umkehrung dessen, was eine Verdraengung tun soll. Im Log des Nutzers
# steht beides Sekunden auseinander: erst "THUMB_CACHE Treffer: 6.3ms
# (ATARI2600.art)", dann "PERF cover: 1732 ms (ATARI2600.art)".
#
# Deshalb: solange die Uhr nicht nachweislich steht, wird KEINE
# Aenderungszeit gesetzt (die Datei behaelt ihre alte, richtige Marke).
# Die in dieser Zeit beruehrten Dateien werden gemerkt und nachgeholt,
# sobald die Uhr steht - siehe uhr_ist_gestellt().
_uhr_verlaesslich = False
_vor_uhrstellung_beruehrt = []
_VOR_UHRSTELLUNG_MAX = 500      # Notbremse, falls die Uhr nie gestellt wird


def uhr_ist_gestellt():
    """Meldet, dass die Systemuhr jetzt stimmt (aufgerufen von
    fe/timekeeping.py nach einer erfolgreichen NTP-Synchronisierung).

    Holt fuer alle seit dem Start beruehrten Cache-Dateien die
    "zuletzt benutzt"-Marke nach. Ohne das behielten genau die Dateien,
    die beim Start gebraucht wurden, eine Marke aus der Zeit VOR dem
    Sprung - und waeren weiterhin die ersten Verdraengungsopfer, nur aus
    dem umgekehrten Grund."""
    global _uhr_verlaesslich, _vor_uhrstellung_beruehrt
    _uhr_verlaesslich = True
    nachzuholen, _vor_uhrstellung_beruehrt = _vor_uhrstellung_beruehrt, []
    geholt = 0
    for cpath in nachzuholen:
        try:
            os.utime(cpath, None)
            geholt += 1
        except OSError:
            pass
    if geholt:
        LOG("THUMB_CACHE: %d beim Start gelesene Eintraege auf die jetzt "
            "richtige Uhrzeit gesetzt" % geholt)


def _benutzt_vermerken(cpath):
    """"Zuletzt benutzt"-Marke setzen - oder vormerken, falls die Uhr
    noch nicht steht (siehe Kommentarblock oben)."""
    if _uhr_verlaesslich:
        try:
            os.utime(cpath, None)
        except OSError:
            pass
        return
    if len(_vor_uhrstellung_beruehrt) < _VOR_UHRSTELLUNG_MAX:
        _vor_uhrstellung_beruehrt.append(cpath)


# NEU (Build 128): die Antwort "das Original passt, wie es ist".
#
# WARUM ES DAS GIBT. Bis Build 127 legte der Passt-genau-Fall eine
# vollstaendige KOPIE des dekodierten Originals auf der Karte ab (siehe
# die Begruendung von Build 92 in _get_scaled_impl()). Die Absicht war
# richtig - ohne Eintrag meldet thumb_cache_has() fuer immer "nicht da"
# -, der Preis war es nicht. Nachgemessen bei einem 600x800-Cover im
# HDMI-Listenkasten (733x909):
#
#     Cache-Datei                548 KB
#     Cache lesen + entpacken    5.9 ms
#     Original-PNG dekodieren    4.8 ms
#
# Die gespeicherte Miniatur war also GROESSER als das Original und
# gleichzeitig LANGSAMER als es einfach neu zu dekodieren. Ein halbes
# Megabyte SD-Karte, um nichts zu sparen.
#
# Beim Nutzer, der das aufgebracht hat: 28517 Cover, 9.8 GB
# Zwischenspeicher bei erst zwei Dritteln der Arbeit. Dieser eine Fall
# war der groesste Posten darin.
#
# Jetzt steht dort eine acht Byte lange Marke. thumb_cache_has() sagt
# weiterhin "da" (das war der ganze Zweck), "Miniaturen vorbereiten"
# hakt das Cover ab, und der Zeichenpfad dekodiert das Original - was
# er nach der Messung oben ohnehin lieber tut.
ORIGINAL_PASST = "original_passt"

_MARKE = b"ARTO"


def _thumb_cache_get(path, w, h):
    """Liefert (breite, hoehe, pixelbytes) bei einem Treffer, sonst
    None. Vermerkt bei einem Treffer die Benutzung (dient als einfacher,
    robuster "zuletzt benutzt"-Zeitstempel fuer die Verdraengung weiter
    unten - keine separate Indexdatei noetig, die nach einem
    Absturz/Stromausfall inkonsistent werden koennte).

    Sonderfall seit Build 128: liegt dort die Marke ORIGINAL_PASST (acht
    Byte statt einer halben Megabyte-Kopie), wird genau diese Zeichen-
    kette zurueckgegeben. Jeder Aufrufer muss sie von einem echten
    Bild-Treffer unterscheiden - siehe den Kommentarblock bei
    ORIGINAL_PASST."""
    cpath = _thumb_cache_path(_thumb_cache_key(path, w, h))
    try:
        with open(cpath, "rb") as f:
            kopf = f.read(4)
            if kopf == _MARKE:
                _benutzt_vermerken(cpath)
                return ORIGINAL_PASST
            if kopf != b"ART1":
                return None
            tw, th = struct.unpack("<HH", f.read(4))
            pix = zlib.decompress(f.read())
            if len(pix) != tw * th * 4:
                return None
        _benutzt_vermerken(cpath)
        return (tw, th, pix)
    except FileNotFoundError:
        return None
    except OSError:
        return None
    except (struct.error, zlib.error, ValueError):
        return None


def _thumb_cache_put_marke(path, w, h):
    """Die Marke "das Original passt, wie es ist" ablegen - acht Byte
    statt einer Kopie. Siehe den Kommentarblock bei ORIGINAL_PASST.

    Geschrieben wird wie jede Cache-Datei ueber .tmp + os.replace(),
    damit ein Abbruch mittendrin keine halbe Datei hinterlaesst."""
    try:
        cpath = _thumb_cache_path(_thumb_cache_key(path, w, h))
        os.makedirs(os.path.dirname(cpath), exist_ok=True)
        tmp = cpath + ".tmp%d_%d" % (os.getpid(), threading.get_ident())
        with open(tmp, "wb") as f:
            f.write(_MARKE + struct.pack("<HH", 0, 0))
        os.replace(tmp, cpath)
    except OSError as e:
        LOG("THUMB_CACHE Schreibfehler (%s): %s" % (os.path.basename(path), e))
        return
    if not _uhr_verlaesslich and len(_vor_uhrstellung_beruehrt) < _VOR_UHRSTELLUNG_MAX:
        _vor_uhrstellung_beruehrt.append(cpath)
    _thumb_cache_evict_if_needed()

def thumb_cache_lesen(path, w, h):
    """Oeffentlicher Eingang zu _thumb_cache_get() (Build 125).

    Gibt es, damit der Nachlade-Thread (fe/nachladen.py) eine fertige
    Miniatur von der Karte holen kann, ohne dass dieses Modul den
    privaten Namen exportieren muss - und damit in einem Test eine
    Attrappe an dieselbe Stelle passt.

    Die Marke ORIGINAL_PASST (Build 128) wird hier zu None: der
    Nachlader soll Bilder in den Arbeitsspeicher holen, und eine Marke
    ist kein Bild. Der Zeichenpfad dekodiert das Original dann selbst -
    nachgemessen billiger, als die frueher dort abgelegte Kopie zu lesen
    (4.8 gegen 5.9 ms), es geht also nichts verloren."""
    ergebnis = _thumb_cache_get(path, w, h)
    if ergebnis is ORIGINAL_PASST:
        return None
    return ergebnis


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
        cpath = _thumb_cache_path(_thumb_cache_key(path, w, h))
        os.makedirs(os.path.dirname(cpath), exist_ok=True)
        tmp = cpath + ".tmp%d_%d" % (os.getpid(), threading.get_ident())
        with open(tmp, "wb") as f:
            f.write(b"ART1" + struct.pack("<HH", tw, th) + zlib.compress(pix, 6))
        os.replace(tmp, cpath)
    except OSError as e:
        LOG("THUMB_CACHE Schreibfehler (%s): %s" % (os.path.basename(path), e))
        return
    # Auch frisch geschriebene Dateien bekommen ihre Marke von der
    # Systemuhr - steht die noch nicht (siehe Kommentarblock bei
    # uhr_ist_gestellt()), wird sie hier vorgemerkt und nachgeholt.
    if not _uhr_verlaesslich and len(_vor_uhrstellung_beruehrt) < _VOR_UHRSTELLUNG_MAX:
        _vor_uhrstellung_beruehrt.append(cpath)
    _thumb_cache_evict_if_needed()

def _thumb_cache_put_marke_async(path, w, h):
    """Wie _thumb_cache_put_marke(), aber nicht-blockierend - gleicher
    Grund wie bei _thumb_cache_put_async() darunter. Die Marke selbst
    ist zwar winzig, aber _thumb_cache_evict_if_needed() haengt daran,
    und das kann ein Verzeichnisdurchlauf sein."""
    def _run():
        try:
            _thumb_cache_put_marke(path, w, h)
        except Exception:                                # noqa: BLE001
            pass
    threading.Thread(target=_run, daemon=True).start()


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

# Mitgefuehrter Dateizaehler - siehe die lange Begruendung in
# _thumb_cache_evict_if_needed(). None = "noch nie gezaehlt".
_thumb_cache_anzahl = None
_thumb_cache_seit_zaehlung = 0

# Nach so vielen Schreibvorgaengen wird trotz gueltigem Zaehler noch
# einmal wirklich nachgezaehlt. Der Zaehler kann naemlich abdriften,
# wenn jemand von aussen Dateien in den Ordner legt oder daraus loescht
# (was ausdruecklich erlaubt ist - der Ordner darf jederzeit von Hand
# geleert werden). Alle 2000 Schreibvorgaenge ist oft genug, damit das
# nie aus dem Ruder laeuft, und selten genug, dass es niemand merkt.
#
# GEAENDERT (Build 128): 2000 -> 15000. Das Nachzaehlen ist ein
# Verzeichnisdurchlauf, und der kostet mit der neuen Obergrenze das
# Vierfache. Bei 2000 waere "Miniaturen vorbereiten" ueber einen ganzen
# Durchlauf hinweg 40 mal durch 150000 Dateien gelaufen, nur um eine
# Zahl zu pruefen, die es selbst mitzaehlt. 15000 ist derselbe Abstand
# wie die Menge, die eine Verdraengung freiraeumt - haeufiger nachsehen
# als aufraeumen bringt nichts.
_THUMB_CACHE_NACHZAEHLEN_ALLE = 15000


# Cache-Dateien, die niemals verdraengt werden duerfen - siehe
# ausfuehrliche Begruendung in _thumb_cache_evict_if_needed().
_geschuetzte_cache_dateien = set()


def thumb_cache_schuetzen(auftraege):
    """Die uebergebenen (pfad, breite, hoehe)-Tripel vor der Verdraengung
    schuetzen. Ersetzt die bisherige Liste vollstaendig, damit ein
    geaenderter Kategoriesatz (oder eine andere Aufloesung) keine
    veralteten Schutzeintraege hinterlaesst."""
    global _geschuetzte_cache_dateien
    _geschuetzte_cache_dateien = {
        _thumb_cache_path(_thumb_cache_key(p, w, h)) for p, w, h in auftraege}
    return len(_geschuetzte_cache_dateien)


def _thumb_cache_evict_if_needed():
    """Verdraengung nach Anzahl Dateien: die am laengsten nicht mehr
    gelesenen/geschriebenen (aelteste Aenderungszeit) zuerst entfernen,
    bis wieder unter der Obergrenze.

    GEAENDERT (Build 74, Messung auf dem Geraet des Nutzers):

        Ordner durchzaehlen (7700 Dateien): 167 ms
        lesen     Schnitt 11.2 ms, max 26 ms
        entpacken Schnitt  1.3 ms, max  2 ms
        utime     Schnitt  0.1 ms, max  0 ms

    Diese Funktion lief nach JEDEM geschriebenen Miniaturbild und begann
    mit genau diesem os.listdir - 167 ms, die sich der Hintergrund-
    Schreiber mit dem Zeichnen um dieselbe SD-Karte streitet. Im Log
    schlug das als Cache-TREFFER mit 169 ms durch (sonst 1-16 ms), also
    ausgerechnet dort, wo gar nichts gerechnet wird. Ich hatte zuvor
    os.utime bei jedem Lesen verdaechtigt - die Messung sagt 0.1 ms,
    diese Vermutung war falsch.

    Jetzt wird die Anzahl EINMAL ermittelt und danach mitgezaehlt. Im
    Normalbetrieb (Anzahl unter der Obergrenze) findet gar kein
    Verzeichniszugriff mehr statt.
    """
    global _thumb_cache_anzahl, _thumb_cache_seit_zaehlung

    if _thumb_cache_anzahl is not None:
        _thumb_cache_anzahl += 1
        _thumb_cache_seit_zaehlung += 1
        if (_thumb_cache_anzahl <= THUMB_CACHE_MAX_FILES
                and _thumb_cache_seit_zaehlung < _THUMB_CACHE_NACHZAEHLEN_ALLE):
            return

    # GEAENDERT (Build 85): die Dateien liegen jetzt in 256 Unterordnern
    # (siehe _thumb_cache_path), es muss also gelaufen statt gelistet
    # werden. Gesammelt wird gleich der VOLLE Pfad - der wird unten
    # ohnehin gebraucht, und ein zweites os.path.join je Datei bei
    # 40000 Dateien ist unnoetig.
    namen = []
    reste = []
    try:
        for unterordner, _dirs, dateien in os.walk(THUMB_CACHE_DIR):
            for f in dateien:
                if f.endswith(".art"):
                    namen.append(os.path.join(unterordner, f))
                elif ".art.tmp" in f:
                    reste.append(os.path.join(unterordner, f))
    except OSError:
        return
    names = namen
    # Liegengebliebene Zwischendateien mitnehmen, wenn wir schon einmal
    # hier sind: _thumb_cache_put() schreibt erst nach "<name>.tmpPID_TID"
    # und benennt dann um. Bricht der Vorgang dazwischen ab (Absturz,
    # Stromausfall), bleibt die Zwischendatei fuer immer liegen - bisher
    # hat sie niemand aufgeraeumt, weil die Verdraengung nur auf ".art"
    # sieht. Beim Nutzer standen 20008 Dateien im Ordner bei einer
    # Obergrenze von 20000.
    for fp in reste:
        try:
            os.remove(fp)
        except OSError:
            pass
    _thumb_cache_anzahl = len(names)
    _thumb_cache_seit_zaehlung = 0
    if len(names) <= THUMB_CACHE_MAX_FILES:
        return
    entries = []
    for fp in names:
        # GESCHUETZTE Eintraege ueberspringen (siehe
        # thumb_cache_schuetzen()): die Kategorie-Logos der Startseite
        # sind nur rund vier Dutzend Dateien, aber die teuersten im
        # ganzen Frontend (auf dem Geraet des Nutzers 1.4-3.7 SEKUNDEN
        # je Neuberechnung, weil sie mit 900 px die groessten Bilder
        # sind). Sie duerfen unter keinen Umstaenden verdraengt werden -
        # sie stehen auf genau der Seite, die man beim Start sieht.
        if fp in _geschuetzte_cache_dateien:
            continue
        try:
            entries.append((os.path.getmtime(fp), fp))
        except OSError:
            pass
    entries.sort()
    # GEAENDERT (Build 84): frueher wurde exakt auf die Obergrenze
    # heruntergeraeumt, also bei einem vollen Cache GENAU EIN Eintrag je
    # Schreibvorgang entfernt - bei vollem Preis. Der Preis ist das
    # os.listdir plus ein os.path.getmtime JE DATEI; beim Nutzer mit
    # 20000 Dateien sind das 20000 Systemaufrufe auf der SD-Karte. Aus
    # seinen Messungen laesst sich das herausrechnen:
    #
    #   Zeit eines Fehltreffers = 1030 ms + 7.4 us je Quellpixel
    #
    # Die 1030 ms sind bildgroessen-UNABHAENGIG - das ist genau dieser
    # Durchgang. Jetzt wird auf ZIELFUELLUNG heruntergeraeumt (90 %),
    # der teure Durchgang laeuft dadurch nur noch etwa alle 2000
    # Schreibvorgaenge statt bei jedem einzelnen.
    ziel = int(THUMB_CACHE_MAX_FILES * 0.9)
    to_remove = max(0, len(names) - ziel)
    to_remove = min(to_remove, len(entries))
    entfernt = 0
    for _, fp in entries[:to_remove]:
        try:
            os.remove(fp)
            entfernt += 1
        except OSError:
            pass
    _thumb_cache_anzahl = len(names) - entfernt
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

def _ist_kategorie_logo(pfad):
    """Gehoert dieses Bild zu einer Kategorie (SYSART_BASE)?

    Wird bei JEDER Verdraengung im RAM-Bildspeicher gefragt (siehe
    _scaled_cache_put()) - deshalb bewusst ein reiner
    Praefix-Vergleich ohne Dateizugriff. SYSART_BASE wird bei jedem
    Aufruf frisch gelesen: Tests und der CRT/HDMI-Wechsel biegen die
    Konstante um, ein einmal gemerkter Wert waere danach falsch.

    Siehe die ausfuehrliche Begruendung bei _scaled_cache_put()."""
    return bool(pfad) and isinstance(pfad, str) \
        and pfad.startswith(SYSART_BASE)


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
        # NEU (Build 89, Nutzer-Rueckmeldung: "wenn ich durch die ROMs
        # scrolle, ploppt immer erst 'kein Artwork' auf und dann wird das
        # Cover nachgeladen").
        #
        # get_scaled() liefert None fuer ZWEI voellig verschiedene Faelle:
        # "es gibt kein Cover" und "ich habe es waehrend des Scrollens
        # bewusst uebersprungen, es kommt gleich". Der Zeichenpfad konnte
        # die beiden nicht unterscheiden und malte deshalb auch im
        # zweiten Fall den "kein Artwork"-Platzhalter - der 150 ms
        # spaeter vom nachgeladenen Cover wieder ersetzt wurde. Genau
        # dieses Aufblitzen hat der Nutzer beschrieben.
        #
        # _deferred_something reicht dafuer nicht: das Flag bleibt bis
        # zum naechsten Nachladen stehen, sagt also nichts darueber, ob
        # GERADE DIESER Aufruf uebersprungen wurde. Ein Zaehler schon -
        # der Aufrufer merkt sich den Stand davor und vergleicht.
        self._defer_count = 0
        self._defer_uncached = False # beim schnellen Scrollen: noch nicht
                                     # dekodierte Cover ueberspringen (siehe
                                     # get_scaled()/COVER_SETTLE)
        # NEU (Build 105): ein KALTES Cover im Stillstand nicht mehr hier
        # im Zeichen-Thread rechnen, sondern an den Arbeitsprozess auf dem
        # zweiten CPU-Kern geben und eine Runde spaeter nachzeichnen.
        #
        # WARUM: bis hierher galt "waehrend des Scrollens ueberspringen,
        # im Stillstand rechnen". Der Stillstand ist aber genau der
        # Moment, in dem jemand hinschaut - und eine Erstberechnung
        # kostet auf HDMI 200-500 ms, in denen die Bedienung steht.
        # Nutzer-Rueckmeldung: "wenn ich beim Scrollen schnell die
        # Richtung wechsle, haengt es kurz".
        #
        # auslagern() wird vom Frontend gesetzt (auf PREWARMER.dringend)
        # und liefert True, wenn der Auftrag angenommen wurde. Im
        # Thread-Betrieb liefert sie bewusst False: dort gibt es keinen
        # zweiten Kern, das Rechnen wuerde dem Zeichnen dieselbe Zeit
        # wegnehmen - nur eben spaeter. Dann bleibt es beim bisherigen
        # Verhalten, und schlechter als vorher wird es nirgends.
        self.auslagern = None
        # box_key -> Zeitpunkt, seit wann auf den Arbeitsprozess gewartet
        # wird. Der Eintrag ist zugleich die Notbremse: nach
        # AUSLAGERN_MAX Sekunden rechnet der naechste Aufruf selbst.
        # OHNE diese Grenze haette ein haengender oder abgestuerzter
        # Arbeitsprozess zur Folge, dass ein Cover NIE erscheint - und
        # zwar lautlos.
        self._warte_start = {}
        # NEU (Build 116): die ECHTEN Masse der Datei, getrennt vom
        # gemerkten Bild. Bei JPEG kann verkleinert dekodiert werden -
        # dann liegt im Cache etwas Kleineres als in der Datei, und jede
        # Groessenrechnung muss sich trotzdem nach der Datei richten.
        self.nativ = {}
        # Pfade, deren gemerktes Bild die volle Groesse hat. Nur die
        # taugen ohne weitere Pruefung fuer JEDEN Kasten.
        self._voll = set()

    # Wie lange hoechstens auf den Arbeitsprozess gewartet wird, bevor
    # der Zeichen-Thread die Miniatur doch selbst berechnet. Grosszuegig:
    # der Arbeiter kann noch an einer vorigen Miniatur sitzen (bis ~0.5 s)
    # und braucht dann selbst noch einmal so lange. Knapper bemessen
    # wuerde die Notbremse regelmaessig ohne Not ausloesen und damit
    # genau den Ruckler zurueckholen, den die Auslagerung vermeidet.
    AUSLAGERN_MAX = 2.0

    def _auslagern_versuchen(self, box_key, path, max_w, max_h):
        """Das Rechnen an den Arbeitsprozess abgeben. True = abgegeben,
        der Aufrufer soll fuer diese Runde nichts zeichnen."""
        if self.auslagern is None:
            return False
        # WICHTIG: nur auslagern, wenn es ueberhaupt eine Quelldatei
        # gibt. Ohne diese Pruefung wuerde ein Spiel OHNE Cover - in
        # einer frisch installierten Sammlung der Normalfall - zwei
        # Sekunden lang auf einen Arbeitsprozess warten, der nichts
        # finden kann, statt sofort "kein Artwork" zu zeigen. Ein
        # os.path.isfile() ist hier vernachlaessigbar: wir sind bereits
        # im teuren Zweig, der sonst das ganze Bild dekodieren wuerde.
        if not os.path.isfile(path):
            return False
        t0 = self._warte_start.get(box_key)
        if t0 is not None and time.monotonic() - t0 > self.AUSLAGERN_MAX:
            # Notbremse: zu lange nichts gekommen. Eintrag loeschen und
            # selbst rechnen - lieber ein einmaliger Ruckler als ein
            # Cover, das gar nicht mehr auftaucht.
            self._warte_start.pop(box_key, None)
            LOG("COVER: Arbeitsprozess zu langsam, rechne selbst (%s)"
                % os.path.basename(path))
            return False
        try:
            angenommen = self.auslagern(path, max_w, max_h)
        except Exception:                                # noqa: BLE001
            angenommen = False
        if not angenommen:
            return False
        if t0 is None:
            self._warte_start[box_key] = time.monotonic()
        return True

    def warte_pruefen(self):
        """Ist eine ausgelagerte Miniatur inzwischen da (oder die Geduld
        am Ende)? Dann lohnt sich ein Nachzeichnen.

        Wird aus dem Leerlauf-Zweig der Hauptschleife gerufen und ist
        bewusst billig: eine Dateiabfrage je wartendem Cover, und es
        wartet praktisch nie mehr als eines."""
        if not self._warte_start:
            return False
        jetzt = time.monotonic()
        for box_key, t0 in list(self._warte_start.items()):
            pfad, _marke, mw, mh = box_key
            if thumb_cache_has(pfad, mw, mh):
                self._warte_start.pop(box_key, None)
                return True
            if jetzt - t0 > self.AUSLAGERN_MAX:
                # Eintrag bleibt stehen - _auslagern_versuchen() sieht
                # ihn, zieht die Notbremse und rechnet selbst.
                return True
        return False

    def get(self, path, ziel_b=0, ziel_h=0):
        """Das Original als (breite, hoehe, pix) oder None.

        ziel_b/ziel_h (Build 116): in welchen Kasten es spaeter soll.
        Bei JPEG wird dann gleich verkleinert dekodiert - siehe
        original_lesen(). Die ECHTEN Masse der Datei stehen danach in
        self.nativ[path]; jede Groessenrechnung muss sich nach ihnen
        richten, nicht nach dem, was hier zurueckkommt."""
        # ABSICHERUNG (siehe _art_path_in()): der Pfad kann jetzt None
        # sein, wenn es fuer einen Eintrag gar keinen Cover-Ordner gibt
        # (Sonderkategorie ohne Systemkey). Hier abfangen statt an jeder
        # der acht Aufrufstellen - alle wollen dasselbe: kein Pfad, kein
        # Bild.
        if not path:
            return None
        if path in self.cache:
            vorhanden = self.cache[path]
            # Ein gemerktes Bild taugt nur, wenn es den jetzt
            # verlangten Kasten noch ueberdeckt. Ein voll dekodiertes
            # taugt immer; ein verkleinertes nur fuer Kaesten, die
            # nicht groesser sind als beim ersten Mal. Ohne diese
            # Pruefung bekaeme der Trophaeenraum die Miniatur aus der
            # Spieleliste vorgesetzt und muesste sie hochrechnen.
            if (vorhanden is None or path in self._voll
                    or ziel_b <= 0 or ziel_h <= 0
                    or (vorhanden[0] >= ziel_b and vorhanden[1] >= ziel_h)):
                return vorhanden
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
        #
        # GEAENDERT (Build 116): das eigentliche Lesen steht jetzt in
        # original_lesen(), gemeinsam mit prewarm_thumb(). Der
        # Unterschied in der Fehlerbehandlung bleibt: existiert die
        # Datei nicht, ist das ein STABILER Fall und wird gemerkt; ist
        # sie kaputt oder gerade erst halb kopiert, wird nichts gemerkt,
        # damit der naechste Zugriff es erneut versucht.
        vorhanden = os.path.exists(path)
        gelesen = original_lesen(path, ziel_b or FREMD_MAX_KANTE,
                                 ziel_h or FREMD_MAX_KANTE)
        if gelesen is None and vorhanden:
            # Die Datei war da, ergab aber kein Bild - nicht merken.
            return None
        if gelesen is None:
            art, nativ = None, None
        else:
            w, h, pix, nativ = gelesen
            art = (w, h, pix)
        self.cache[path] = art
        if nativ is not None:
            self.nativ[path] = nativ
            if (w, h) == nativ:
                self._voll.add(path)
            else:
                self._voll.discard(path)
        self.order.append(path)
        if len(self.order) > self.LIMIT:
            old = self.order.pop(0)
            self.cache.pop(old, None)
            self.nativ.pop(old, None)
            self._voll.discard(old)
        return art

    # GEAENDERT (Build 74): frueher eine feste Stueckzahl (SCALED_LIMIT
    # = 20). Das war fuer CRT viel zu wenig und fuer HDMI eher zu viel -
    # ein CRT-Cover belegt rund 60 KB, ein HDMI-Cover ueber 2 MB. Mit
    # 20 Plaetzen fuer beide passte auf CRT nicht einmal eine ganze
    # Bildschirmseite (13 Zeilen) plus ein bisschen Umfeld hinein: beim
    # Hoch- und Runterscrollen fiel ein Cover schon wieder heraus, bevor
    # man es wiedersah, und musste erneut von der Karte gelesen werden.
    #
    # Genau das kostet laut Messung auf dem Geraet des Nutzers 11 ms im
    # Schnitt (max 26 ms) - nicht dramatisch, aber bei jedem Schritt,
    # und voellig unnoetig fuer ein Bild, das eben noch da war.
    #
    # Deshalb jetzt ein SPEICHER-Budget statt einer Stueckzahl: auf CRT
    # passen damit mehrere hundert Miniaturen hinein (die ganze
    # Umgebung, in der man sich bewegt), auf HDMI weiterhin nur eine
    # Handvoll grosser Bilder. SCALED_MIN sorgt dafuer, dass selbst bei
    # sehr grossen Einzelbildern nie weniger Plaetze bleiben als frueher.
    # ERHOEHT (Build 120, Nutzer-Rueckmeldung auf die Frage, ob der
    # zweite Durchlauf durch eine Liste deshalb schneller ist, weil der
    # erste noch rechnet: "ja, das stoert mich sehr").
    #
    # Er tut es, und dieser Wert war der Grund. Ein HDMI-Cover in der
    # ueblichen Groesse (231x420) belegt rund 388 KB - mit 24 MB passten
    # etwa sechzig Stueck hinein. Bei einer Liste mit tausenden
    # Eintraegen faellt ein Cover damit laengst wieder heraus, bevor man
    # es wiedersieht, und muss beim naechsten Vorbeikommen erneut von
    # der Karte gelesen und entpackt werden (gemessen 5-7 ms je Cover).
    # Genau das ist der Unterschied, den er zwischen erstem und zweitem
    # Durchlauf spuert.
    #
    # 96 MB fassen rund 250 HDMI-Cover - genug fuer die ganze Umgebung,
    # in der man sich beim Blaettern bewegt. Auf CRT belegt ein Cover
    # rund 50 KB, dort sind es entsprechend Tausende.
    #
    # WARUM NICHT NOCH MEHR: der MiSTer hat rund 1 GB, das sich Linux
    # mit dem FPGA-Kern teilt, und dieser Cache ist nicht der einzige -
    # daneben liegen die unskalierten Originale (self.cache, 60 Stueck).
    # 96 MB ist der Punkt, an dem der Nutzen praktisch ausgereizt ist,
    # ohne dass der Speicher zum Thema wird.
    SCALED_BUDGET = 96 * 1024 * 1024
    SCALED_MIN = 20                    # niemals weniger als bisher

    def _ist_logo_pfad(self, pfad):
        """Nur damit Tests die Regel einzeln pruefen koennen."""
        return _ist_kategorie_logo(pfad)

    def _scaled_cache_put(self, key, result):
        if not hasattr(self, "scaled"):
            self.scaled = {}
            self.scaled_order = []
            self.scaled_bytes = 0
        self.scaled[key] = result
        self.scaled_order.append(key)
        self.scaled_bytes = getattr(self, "scaled_bytes", 0) + len(result[2])
        while (len(self.scaled_order) > self.SCALED_MIN
               and self.scaled_bytes > self.SCALED_BUDGET):
            # GEAENDERT (Build 141, Nutzer-Rueckmeldung: "wenn man
            # durch die Galerie scrollt und dann zurueck auf die
            # Hauptseite geht, gibt es ab und zu einen kleinen
            # Haenger - nicht immer, ab und zu").
            #
            # Die Verdraengung war reines FIFO: was zuerst hereinkam,
            # flog zuerst raus. Die Kategorie-Logos kommen als ERSTE
            # herein (beim Start, auf der Hauptseite) und sind mit bis
            # zu 900 Bildpunkten Breite die GROESSTEN Bilder im ganzen
            # Frontend. Ein Galerie-Cover belegt auf HDMI 624 KB - nach
            # rund 150 gescrollten Eintraegen sind die 96 MB voll, und
            # die Aeltesten, die fliegen, sind genau die Logos.
            #
            # Beim Zuruecksehen muss das Logo dann neu von der Karte
            # gelesen und entpackt werden. Fuer genau diesen Fall steht
            # weiter oben eine Messung vom Geraet: 722 ms fuer
            # CONTINUE.art. Und es erklaert das "ab und zu" exakt: kurz
            # gescrollt, Logo noch da, kein Haenger.
            #
            # Fuer den Festplatten-Cache gibt es diesen Schutz laengst
            # (_geschuetzte_cache_dateien) - fuer den Arbeitsspeicher
            # fehlte er. Es sind zwei Dutzend Bilder, und ausgerechnet
            # die, zu denen man immer zurueckkommt.
            old = None
            for _i, _k in enumerate(self.scaled_order):
                if not _ist_kategorie_logo(_k[0]):
                    old = self.scaled_order.pop(_i)
                    break
            if old is None:
                # Nur noch Logos drin - dann lieber das Budget
                # ueberschreiten als das wegwerfen, was gleich wieder
                # gebraucht wird. Kann in der Praxis nicht vorkommen
                # (zwei Dutzend Logos sprengen keine 96 MB), steht hier
                # aber, damit die Schleife unter keinen Umstaenden
                # endlos laeuft.
                break
            alt = self.scaled.pop(old, None)
            if alt is not None:
                self.scaled_bytes -= len(alt[2])

    def nur_im_ram_fehlt(self, path, max_w, max_h):
        """True, wenn die Miniatur auf der KARTE liegt, aber nicht im
        Arbeitsspeicher.

        Genau diese Faelle lohnt sich nachzuladen (Build 125): rechnen
        muss dafuer niemand mehr, es fehlt nur das Lesen und Auspacken.
        Alles andere - schon im RAM, oder ueberhaupt nicht vorhanden -
        gehoert nicht in die Nachladeliste."""
        if not path:
            return False
        if (path, "box", max_w, max_h) in getattr(self, "scaled", {}):
            return False
        return thumb_cache_has(path, max_w, max_h)

    def nachgeladen_eintragen(self, path, max_w, max_h, ergebnis):
        """Eine vom Nachlade-Thread gelesene Miniatur in den RAM-Cache
        legen. AUSSCHLIESSLICH aus dem Hauptthread zu rufen - siehe den
        Kopfkommentar von fe/nachladen.py fuer die Begruendung."""
        if not ergebnis or len(ergebnis) != 3:
            return False
        box_key = (path, "box", max_w, max_h)
        if box_key in getattr(self, "scaled", {}):
            return False
        self._scaled_cache_put(box_key, ergebnis)
        return True

    def get_scaled(self, path, max_w, max_h, auslagern_ok=False):
        """auslagern_ok (Build 105): darf eine noch nicht berechnete
        Miniatur an den Arbeitsprozess abgegeben werden?

        Standard False, und das ist die wichtige Voreinstellung. True
        heisst "liefert in diesem Fall vielleicht None, obwohl es das
        Cover gibt" - das darf nur setzen, wer damit umgehen kann, also
        ein Zeichenpfad, der gleich darauf noch einmal gerufen wird
        (Cover-Panel und Kategorie-Kasten, beide ueber den
        COVER_SETTLE-Nachlader abgesichert).

        Alle uebrigen Aufrufer brauchen ein Ergebnis: das Vorwaermen
        beim Start wuerde sonst stillschweigend gar nichts waermen, und
        Einmal-Anzeigen wie Trophaeenraum oder Attract-Modus haetten
        einfach ein leeres Bild. Genau das hat
        tools/test_cover_prewarm.py beim ersten Anlauf gefunden, als
        das Auslagern noch fuer alle galt."""
        _t0 = time.monotonic()
        r = self._get_scaled_impl(path, max_w, max_h, auslagern_ok)
        _dt = time.monotonic() - _t0
        if _dt > 0.025:
            LOG("PERF cover: %.0f ms (%s)" % (_dt * 1000, os.path.basename(path)))
        return r

    def _get_scaled_impl(self, path, max_w, max_h, auslagern_ok=False):
        """Bild in die verfuegbare Flaeche einpassen. Kleine Cover werden
        ganzzahlig hochskaliert (Pixel-Look). Cover, die groesser als die
        Box sind, werden seit v1.8.1 per Nearest-Neighbor VERKLEINERT statt
        unskaliert zu bleiben - sonst ragen sie ueber den reservierten
        Platz hinaus und ueberlappen den Info-Text darunter."""
        if not path or max_w <= 0 or max_h <= 0:
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
        # NEU (Build 128): die Marke "das Original passt" ist KEIN
        # Bildtreffer - sie sagt nur, dass hier nichts zu rechnen ist.
        # Das Original muss trotzdem noch dekodiert werden.
        #
        # WICHTIG ist, was gleich darunter NICHT passiert: bei einer
        # Marke wird die Ueberspring-Pruefung (_defer_uncached)
        # uebergangen. Sonst waere genau der Fehler von Build 92 zur
        # Haelfte zurueck - das Cover wuerde beim Scrollen wieder
        # uebersprungen und danach nachgeladen, also das Aufblitzen aus
        # dem Video des Nutzers.
        #
        # Das ist erlaubt, weil es messbar nichts kostet: die Marke
        # ersetzt eine Cache-Datei, deren Lesen 5.9 ms brauchte, durch
        # ein Dekodieren, das 4.8 ms braucht. Der Zeichenpfad wird an
        # dieser Stelle also nicht langsamer, sondern schneller.
        marke = disk_hit is ORIGINAL_PASST
        if marke:
            disk_hit = None
        if disk_hit is not None:
            _tcache_dt = (time.monotonic() - _tcache_t0) * 1000
            # GEAENDERT (Build 91): die Einzelzeile je Treffer lief bei
            # JEDEM gezeichneten Cover - in einer langen Sitzung sind das
            # Tausende Zeilen, die das eigentlich Interessante zudecken.
            # Sie steht jetzt nur noch bei eingeschalteter Messung; immer
            # mitgezaehlt wird stattdessen die BILANZ (siehe unten).
            if LOG_JEDEN_TREFFER:
                LOG("THUMB_CACHE Treffer: %.1fms (%s, %dx%d)"
                    % (_tcache_dt, os.path.basename(path), max_w, max_h))
            _bilanz_zaehlen(True)
            self._scaled_cache_put(box_key, disk_hit)
            # Falls auf genau dieses Cover gewartet wurde: angekommen.
            self._warte_start.pop(box_key, None)
            return disk_hit

        # Waehrend aktiv gescrollt wird: ein noch nicht dekodiertes Cover
        # NICHT hier (im Zeichen-/Scroll-Pfad) dekodieren - das ruckelt auf
        # der schwachen CPU. Stattdessen ueberspringen; kurz nach dem
        # letzten Tastendruck laedt die Idle-Nachzeichnung es nach (siehe
        # COVER_SETTLE in der Hauptschleife).
        if not marke and self._defer_uncached and path not in self.cache:
            # NEU (siehe _settle_needed in frontend.py): festhalten,
            # DASS hier tatsaechlich etwas uebersprungen wurde. Nur dann
            # muss der COVER_SETTLE-Nachlader spaeter ueberhaupt neu
            # zeichnen - liegen alle Cover bereits im Cache (der
            # Normalfall, sobald der Festplatten-Cache warm ist), gibt es
            # nichts nachzuladen, und der komplette Seitenaufbau nach
            # jedem Stillstand entfaellt.
            self._deferred_something = True
            self._defer_count += 1
            return None
        # NEU (Build 105): im STILLSTAND ist die Miniatur nicht auf der
        # Karte - genau hier stand bisher der 200-500-ms-Ruckler. Erst den
        # Arbeitsprozess fragen; nimmt er an, wird diese Runde nichts
        # gezeichnet und der COVER_SETTLE-Nachlader holt es, sobald die
        # Datei da ist (siehe warte_pruefen() und den Leerlauf-Zweig in
        # frontend.py).
        #
        # Bewusst NACH der Defer-Pruefung darueber: waehrend aktiv
        # gescrollt wird, ist der billige Sprung oben richtig - der
        # Eintrag wechselt ohnehin gleich wieder.
        if (not marke and auslagern_ok and not self._defer_uncached
                and self._auslagern_versuchen(box_key, path, max_w, max_h)):
            self._deferred_something = True
            self._defer_count += 1
            return None
        base = self.get(path, max_w, max_h)
        if not base:
            return None
        w, h, pix = base
        # Build 116: Entscheidungen nach den ECHTEN Massen der Datei.
        # Bei einem verkleinert dekodierten JPEG stimmt (w, h) nicht mehr
        # damit ueberein - wuerde man danach rechnen, landete das Bild
        # mal ein paar Bildpunkte neben der bisherigen Groesse und
        # gelegentlich sogar im Hochskalier-Zweig.
        nw, nh = self.nativ.get(path, (w, h))

        if nw <= max_w and nh <= max_h:
            # Kein hartes Limit mehr wie in v1.8.1 (dort noch 4x) - seit
            # v1.9 hat die Boxart-Spalte deutlich mehr Platz, ein Deckel
            # von 4x liess kleine Cover unnoetig klein und von Leerraum
            # umgeben wirken. 10x ist grosszuegig genug, um jede Box zu
            # fuellen, aber immer noch klein genug, um den Speicher- und
            # Rechenaufwand des Nearest-Neighbor-Upscales im Rahmen zu
            # halten (der Skalierungs-Cache ist ohnehin nach
            # Speicherbudget begrenzt, siehe SCALED_BUDGET).
            scale = max(1, min(max_w // nw, max_h // nh, 10))
            if scale == 1:
                self._scaled_cache_put(box_key, base)
                # BUGFIX (Build 92, Nutzer-Rueckmeldung: "das passiert bei
                # NES, Master System, Atari 2600, Atari 5200, Jaguar, Sega
                # 32X, Arcade ... was mir aufgefallen ist, dass die Boxarts
                # in diesen Kategorien andere GROESSEN haben im Gegensatz
                # zu den anderen - kann es daran liegen?").
                #
                # Ja, genau daran. Hier wurde bisher NICHTS auf der Karte
                # abgelegt, mit der Begruendung "das Bild passt genau, ein
                # Eintrag waere byte-identisch zum Original". Stimmt - und
                # ist trotzdem falsch, wegen zweier Folgen:
                #
                #   1. thumb_cache_has() meldet fuer dieses Cover FUER
                #      IMMER "nicht da". "Miniaturen vorbereiten" rechnet
                #      es also bei JEDEM Durchlauf neu und hakt es nie ab -
                #      diese Systeme konnten durch das Vorbereiten gar
                #      nicht schneller werden.
                #   2. Der Treffer weiter oben (_thumb_cache_get) kommt VOR
                #      der Ueberspring-Pruefung. Ohne Eintrag laeuft jeder
                #      Aufruf in diese Pruefung, und sobald der Rohbild-
                #      Cache (60 Eintraege) das Cover verdraengt hat, wird
                #      beim Scrollen wieder uebersprungen - genau das
                #      Aufblitzen und Nachladen aus dem Video.
                #
                # Betroffen ist ein schmales Band: Cover, die in den Kasten
                # passen, aber nicht um einen GANZZAHLIGEN Faktor >= 2
                # kleiner sind. Deshalb traf es nur die Systeme, deren
                # Scans zufaellig in diesem Bereich liegen.
                #
                # GEAENDERT (Build 128): eine MARKE statt der Kopie. Die
                # beiden oben genannten Folgen bleiben beide behoben -
                # thumb_cache_has() sagt weiterhin "da", und der Treffer
                # kommt weiterhin vor der Ueberspring-Pruefung (siehe
                # dort). Was wegfaellt, ist nur die halbe Megabyte
                # Kopie, die langsamer zu lesen war als das Original zu
                # dekodieren. Siehe den Kommentarblock bei
                # ORIGINAL_PASST.
                if not marke:
                    _thumb_cache_put_marke_async(path, max_w, max_h)
                return base
            # BUGFIX (Nutzer-Rueckmeldung: "beim Scrollen durch viele
            # ROMs ruckelt es spuerbar"): die Defer-Pruefung oben
            # schuetzte bisher NUR vor dem erneuten DEKODIEREN, nicht
            # vor der hier folgenden Skalierung. Bei grossen Sammlungen
            # (mehr Cover, als das Speicherbudget des Skalierungs-
            # Caches gleichzeitig fasst, pro
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
                self._defer_count += 1
                return None
            _bilanz_zaehlen(False)
            sw, sh, out = _hochskalieren(pix, w, h, scale)
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
        # Gerechnet nach den ECHTEN Massen (siehe oben), damit dieselbe
        # Zielgroesse herauskommt wie vor Build 116 - die Miniatur auf
        # der Karte traegt den Kasten im Schluessel, nicht die
        # Zielgroesse, und muss ueber Fassungen hinweg dieselbe bleiben.
        tw, th = zielmass(nw, nh, max_w, max_h)
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
            self._defer_count += 1
            return None
        _bilanz_zaehlen(False)
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
        # gleicher Grund wie beim Hochskalieren oben.
        _thumb_cache_put_async(path, max_w, max_h, tw, th, result[2])
        return result


# NEU (Build 91, Nutzer-Rueckmeldung: "irgendwie hab ich das Gefuehl,
# dass der letzte Build nicht greift, was das Scrollen angeht - ein paar
# Mal kalt neu gestartet und das Verhalten ist das alte").
#
# Genau diese Frage war bisher nur ueber Umwege zu beantworten. Die
# Bilanz macht aus dem Gefuehl eine Zahl: greift der Zwischenspeicher,
# stehen dort fast nur Treffer. Steht dort eine hohe Fehltreffer-Quote,
# wird tatsaechlich immer wieder neu gerechnet - und DANN lohnt es sich,
# nach dem Warum zu suchen (Vorbereiten nie gelaufen, Verdraengung,
# geaenderte Kastengroesse).
LOG_JEDEN_TREFFER = False     # die Einzelzeile je Cover - nur zum Messen
_bilanz = [0, 0]              # [Treffer, Fehltreffer]
_bilanz_gemeldet = [0]


def _bilanz_zaehlen(treffer):
    _bilanz[0 if treffer else 1] += 1
    gesamt = _bilanz[0] + _bilanz[1]
    # Alle 50 Vorgaenge eine kompakte Zeile - haeufig genug, um beim
    # Mitlesen etwas zu sehen, selten genug, um das Log nicht zu fluten.
    if gesamt - _bilanz_gemeldet[0] >= 50:
        _bilanz_gemeldet[0] = gesamt
        LOG("THUMB_CACHE Bilanz: %d Treffer, %d Fehltreffer (%d%% Treffer)"
            % (_bilanz[0], _bilanz[1], _bilanz[0] * 100 // max(1, gesamt)))


def thumb_cache_bilanz():
    """(Treffer, Fehltreffer) dieser Sitzung."""
    return tuple(_bilanz)


def thumb_cache_stand():
    """(Anzahl Dateien, Obergrenze, belegte Bytes) im Miniaturen-
    Zwischenspeicher des AKTUELLEN Modus (hd/ oder sd/).

    NEU (Nutzerfrage: "die Miniaturen werden ja gecacht, quasi
    gespeichert, und nicht immer neu erstellt? Kam mir gerade so vor").
    Die Frage war bisher nur ueber Umwege zu beantworten. Ein Durchlauf
    von "Miniaturen vorbereiten" schreibt die Zahl jetzt ins Log - steht
    sie an der Obergrenze, verdraengt sich die Sammlung selbst und genau
    dann wird tatsaechlich immer wieder neu gerechnet.

    Kostet ein os.listdir (auf dem Geraet des Nutzers 167 ms bei 7700
    Dateien) - vertretbar, weil es EINMAL am Ende eines Vorgangs laeuft,
    der ohnehin Minuten dauert."""
    n = 0
    bytes_ = 0
    try:
        for unterordner, _dirs, dateien in os.walk(THUMB_CACHE_DIR):
            for f in dateien:
                if not f.endswith(".art"):
                    continue
                n += 1
                try:
                    bytes_ += os.path.getsize(os.path.join(unterordner, f))
                except OSError:
                    pass
    except OSError:
        pass
    return n, THUMB_CACHE_MAX_FILES, bytes_


def thumb_cache_stand_modus(hd):
    """Wie thumb_cache_stand(), aber fuer einen BESTIMMTEN Modus statt
    fuer den gerade aktiven. Der Menuepunkt zum Leeren muss beide Zahlen
    nebeneinander zeigen koennen - man raeumt ja meistens genau den
    Modus weg, in dem man gerade NICHT unterwegs ist."""
    ordner = os.path.join(THUMB_CACHE_BASE, "hd" if hd else "sd")
    n = 0
    bytes_ = 0
    try:
        for unter, _d, dateien in os.walk(ordner):
            for f in dateien:
                if not f.endswith(".art"):
                    continue
                n += 1
                try:
                    bytes_ += os.path.getsize(os.path.join(unter, f))
                except OSError:
                    pass
    except OSError:
        pass
    return n, bytes_


def thumb_cache_leeren(hd):
    """Loescht den Miniaturen-Zwischenspeicher EINES Modus.

    NEUES FEATURE (Build 91, Nutzerwunsch: "vielleicht sollten wir noch
    einbauen, dass man per Hand den Cache fuer SD sowie HD unter System/
    Wartung einmal leeren kann"). Bis dahin ging das nur ueber SSH.

    Loescht bewusst NUR .art-Dateien und liegengebliebene .art.tmp -
    alles andere in dem Ordner ruehrt die Funktion nicht an, und die
    Unterordner selbst bleiben stehen (sie werden sofort wieder
    gebraucht). Setzt danach den Mitzaehler zurueck, damit die
    Verdraengung nicht mit einer veralteten Zahl weiterrechnet."""
    global _thumb_cache_anzahl
    ordner = os.path.join(THUMB_CACHE_BASE, "hd" if hd else "sd")
    entfernt = 0
    fehler = 0
    try:
        for unter, _d, dateien in os.walk(ordner):
            for f in dateien:
                if not (f.endswith(".art") or ".art.tmp" in f):
                    continue
                try:
                    os.remove(os.path.join(unter, f))
                    entfernt += 1
                except OSError:
                    fehler += 1
    except OSError:
        pass
    _thumb_cache_anzahl = None
    LOG("THUMB_CACHE geleert (%s): %d Dateien entfernt%s"
        % ("hd" if hd else "sd", entfernt,
           ", %d nicht loeschbar" % fehler if fehler else ""))
    return entfernt


def thumb_cache_has(path, w, h):
    """Liegt die Miniatur fuer diese Kastengroesse schon auf der Karte?
    Nur eine Existenzpruefung - bewusst OHNE die Datei zu lesen und zu
    entpacken (das macht _thumb_cache_get()). Der Vorauslader fragt das
    fuer viele Eintraege hintereinander; ihn dafuer jedes Mal ein
    fertiges Bild entpacken zu lassen, das er gar nicht anzeigen will,
    waere reine Verschwendung."""
    try:
        return os.path.exists(_thumb_cache_path(_thumb_cache_key(path, w, h)))
    except OSError:
        return False


def zielmass(nw, nh, max_w, max_h):
    """Auf welche Groesse ein Bild von nw x nh in einem Kasten von
    max_w x max_h landet - oder None, wenn es hineinpasst und
    stattdessen ganzzahlig VERGROESSERT wird.

    HERAUSGELOEST (Build 116). Diese Rechnung stand an drei Stellen
    (Zeichenpfad, Vorbereitung, Arbeitsprozess) und muss ueberall
    dasselbe ergeben - der Schluessel des Miniaturen-Caches enthaelt den
    KASTEN, nicht die Zielgroesse. Laufen die Fassungen auseinander,
    legt die eine Seite Bilder unter einem Schluessel ab, unter dem die
    andere etwas anderes erwartet, und niemand merkt es.

    Und seit Build 116 braucht sie noch jemand: das verkleinerte
    Dekodieren. Der Unterschied ist nicht klein - ein 424x768-Cover in
    einem 360x420-Kasten wird 231x420, nicht 360x420. Wer den KASTEN
    als Dekodierziel nimmt, bekommt 371x672 statt 265x480 und verschenkt
    den halben Gewinn. Genau so war die erste Fassung, und die Messung
    hat es gezeigt: 89 statt 65 ms."""
    if nw <= max_w and nh <= max_h:
        return None
    sc = min(max_w / float(nw), max_h / float(nh))
    return max(1, int(nw * sc)), max(1, int(nh * sc))


def original_lesen(path, ziel_b=0, ziel_h=0):
    """Ein Bild von der Karte holen: (breite, hoehe, pix, (nb, nh)).
    None, wenn daraus nichts wird - NIE eine Ausnahme nach aussen.

    Das letzte Paar sind die ECHTEN Masse der Datei. Sie koennen von
    (breite, hoehe) abweichen, wenn verkleinert dekodiert wurde (siehe
    unten) - und jede Entscheidung ueber die Zielgroesse muss sich nach
    ihnen richten, nicht nach dem, was gerade im Speicher liegt.

    HERAUSGELOEST (Build 116), weil DREI Stellen dasselbe Bild lesen:
    ArtCache.get(), prewarm_thumb() und der Arbeitsprozess. Der
    Modul-Kommentar verlangt, dass eine gespeicherte Miniatur
    bit-identisch zu einer frisch berechneten ist - mit drei Fassungen
    desselben Ablaufs waere das irgendwann still auseinandergelaufen.
    Genau das war bei prewarm_thumb() schon passiert: die Funktion
    kannte NUR "ART1" und gab bei einem JPG "fehler" zurueck. Die
    fremden Cover aus Build 115 wurden dadurch von "Miniaturen
    vorbereiten" komplett uebergangen - jedes einzelne musste der
    Zeichenpfad berechnen, wieder und wieder.

    ziel_b/ziel_h: die KASTENGROESSE, in die das Bild spaeter soll.
    Bei JPEG dekodiert TurboJPEG dann gleich verkleinert - so klein wie
    moeglich, aber NIE unter der Groesse, die am Ende gebraucht wird.
    Das spart nicht am Dekodieren (das ist ohnehin billig), sondern an
    der Flaechenmittelung danach, und die ist nach Build 115 der ganze
    Rest: gemessen 43,1 -> 13,8 ms auf CRT."""
    try:
        with open(path, "rb") as f:
            kopf = f.read(4)
            if kopf == b"ART1":
                w, h = struct.unpack("<HH", f.read(4))
                pix = zlib.decompress(f.read())
                if len(pix) != w * h * 4 or w <= 0 or h <= 0:
                    return None
                return w, h, pix, (w, h)
            if _BILDLIB is None:
                return None
            daten = kopf + f.read()
    except (OSError, struct.error, zlib.error, ValueError):
        return None
    # Erst die echten Masse aus dem Dateikopf holen (kostet nichts),
    # dann daraus das ECHTE Ziel rechnen - nicht den Kasten nehmen.
    nativ = _BILDLIB.masse(daten)
    dek_b = dek_h = 0
    if nativ and ziel_b > 0 and ziel_h > 0:
        ziel = zielmass(nativ[0], nativ[1], ziel_b, ziel_h)
        if ziel:
            dek_b, dek_h = ziel
    bild = _BILDLIB.decode(daten, dek_b, dek_h)
    if not bild:
        return None
    w, h, pix = bild
    return w, h, pix, (nativ or (w, h))


def prewarm_thumb(path, max_w, max_h):
    """Eine Miniatur berechnen und AUSSCHLIESSLICH auf der Karte ablegen.

    NEU (Build 73). Hintergrund, mit echten Messwerten vom Geraet des
    Nutzers: ein noch nicht vorberechnetes Cover kostet dort 200-500 ms
    (Entpacken des Originals + Verkleinern mit Flaechenmittelung, beides
    reines Python), das Zeichnen der Seite drumherum nur ~20 ms. Beim
    ersten Durchgang durch eine Liste faellt dieser Preis bei JEDEM
    Eintrag an - genau das, was der Nutzer als "das haengt 1-2 Sekunden"
    beschreibt. Beim zweiten Mal kostet dasselbe Cover 1-6 ms. Es geht
    hier also nicht darum, etwas schneller zu machen, sondern darum, den
    einmaligen Preis dorthin zu verschieben, wo niemand wartet.

    Rueckgabe: "treffer" (lag schon da), "fertig" (neu berechnet),
    "uebersprungen" (nichts zu tun - z.B. passt das Bild exakt, dann
    legt auch der Zeichenpfad nichts ab) oder "fehler".

    WICHTIG - was diese Funktion BEWUSST NICHT tut: sie fasst die
    Arbeitsspeicher-Caches von ArtCache (self.cache/self.scaled) mit
    keinem Byte an. Sie ist dafuer gedacht, aus einem HINTERGRUND-Thread
    aufgerufen zu werden, waehrend der Hauptthread zeichnet - und die
    beiden Caches sind Liste+Wurgeboerse ohne Sperre (siehe
    _scaled_cache_put()); zwei Threads darin gleichzeitig waeren genau
    die Sorte Fehler, die sich nie zuverlaessig nachstellen laesst.
    Deshalb liest sie ihr Original selbst ein, rechnet, schreibt die
    Datei - fertig. Der Zeichenpfad findet das Ergebnis spaeter ganz
    normal ueber _thumb_cache_get().
    """
    if max_w <= 0 or max_h <= 0:
        return "uebersprungen"
    if thumb_cache_has(path, max_w, max_h):
        return "treffer"
    # Original selbst einlesen - ueber DIESELBE Funktion wie
    # ArtCache.get(), aber ohne dessen Cache anzufassen (siehe
    # Docstring). Bis Build 115 stand hier eine eigene Fassung, die nur
    # "ART1" kannte; siehe original_lesen() fuer die Folgen.
    gelesen = original_lesen(path, max_w, max_h)
    if gelesen is None:
        return "fehler"
    return _prewarm_aus_gelesenem(path, max_w, max_h, gelesen)


def _skaliert_dekodierbar(path):
    """True, wenn dieses Bild VERKLEINERT dekodiert werden kann - also
    ein JPEG ist und die Bibliothek da ist.

    Das ist der Unterschied, der ueber die Rechenzeit entscheidet:
    TurboJPEG liefert 1/2, 1/4 oder 1/8 direkt aus dem Dekoder, libpng
    kann das nicht (siehe decode() in fe/bildlib.py). Fuer ein Bild, das
    verkleinert ankommt, muss die teure Flaechenmittelung nur noch ueber
    einen Bruchteil der Bildpunkte laufen."""
    if _BILDLIB is None:
        return False
    try:
        with open(path, "rb") as f:
            return f.read(3) == b"\xff\xd8\xff"
    except OSError:
        return False


def _arbeitskopie_aus_pixeln(path, w, h, pix):
    """Neben einem PNG eine JPEG-Arbeitskopie anlegen - aus BEREITS
    dekodierten Bildpunkten (Build 143).

    Der Nutzer fragte, ob die Arbeitskopien aus Build 129 nicht
    nachtraeglich auf dem MiSTer entstehen koennen. Das hier ist die
    billige Antwort: "Miniaturen vorbereiten" dekodiert jedes PNG
    ohnehin in voller Groesse (libpng kann nicht verkleinert
    dekodieren), die Bildpunkte liegen also schon da. Uebrig bleibt
    nur das JPEG-Kodieren. Ein eigener Durchlauf muesste beides tun.

    Was der Zeichenpfad davon hat, steht im Geraete-Profil: PNG-Cover
    kosteten dort 353-410 ms, JPEG-Cover 71-85 ms.

    DREI SICHERUNGEN, jede aus einem eigenen Grund:

    1. NUR IN UNSERE EIGENEN ORDNER. Die fremde Datenbank unter
       DOCS_BASE gehoert uns nicht - siehe den Kopfkommentar dort:
       "WIR SCHREIBEN DORT NIE HIN". Dasselbe gilt fuer Artpacks und
       fuer die Spiele-Ordner.
    2. NUR, WENN NOCH KEINE DA IST. Sonst schriebe jeder Durchlauf
       dieselbe Datei neu.
    3. FEHLER SIND KEINE FEHLER. Klappt das Kodieren oder Schreiben
       nicht (Karte voll, schreibgeschuetzt, Bibliothek fehlt), passiert
       einfach nichts. Ein Cover darf nie deshalb fehlen, weil eine
       Beschleunigung nicht geklappt hat - dieselbe Regel wie in
       mister_boxart.arbeitskopie_schreiben()."""
    if not path or not pix or w <= 0 or h <= 0:
        return False
    if path[-4:].lower() != ".png":
        return False
    eigene = [b for b in (ART_BASE, ART_HD) if b]
    if not any(path.startswith(b + os.sep) or path.startswith(b + "/")
               for b in eigene):
        return False
    ziel = path[:-4] + ".jpg"
    if os.path.exists(ziel):
        return False
    try:
        from fe import bildlib as _bl
        if not _bl.schreiben_verfuegbar():
            return False
        jpg = _bl.encode_jpeg(w, h, pix, 90)
        if not jpg:
            return False
        # Ueber eine .tmp-Datei und os.replace(): ein abgebrochener
        # Durchlauf darf kein halbes JPEG hinterlassen, das der
        # Zeichenpfad danach dem PNG vorzieht.
        tmp = ziel + ".tmp"
        with open(tmp, "wb") as fh:
            fh.write(jpg)
        os.replace(tmp, ziel)
        LOG("Arbeitskopie angelegt: %s" % os.path.basename(ziel))
        return True
    except Exception:                                    # noqa: BLE001
        try:
            os.remove(ziel + ".tmp")
        except OSError:
            pass
        return False


def prewarm_thumb_mehrfach(path, kaesten):
    """Mehrere Kastengroessen desselben Covers - mit EINEM Lesen und
    EINEM Dekodieren. Rueckgabe: Liste der Einzelergebnisse, in der
    Reihenfolge von "kaesten".

    NEU (Build 128). "Miniaturen vorbereiten" rechnet je Cover drei
    Kastengroessen (Liste, Kachel, Galerie-Cover). Bis Build 127 lief
    dafuer dreimal prewarm_thumb() - also dreimal die Datei von der
    SD-Karte lesen und dreimal dasselbe PNG dekodieren, um danach
    dreimal unterschiedlich zu verkleinern.

    Gemessen an einem 900x1200-PNG: Dekodieren 10.6 ms, Verkleinern
    zusammen 482 ms. Das Mehrfach-Dekodieren ist also nicht der grosse
    Posten - aber es ist reine Verschwendung, und auf der SD-Karte des
    MiSTer wiegt das Lesen schwerer als auf der Messmaschine.

    WICHTIG - was hier NICHT passiert: es wird keine fertige Miniatur
    weiterverarbeitet. Jede Kastengroesse wird aus DEMSELBEN dekodierten
    Original gerechnet, genau wie vorher. Die Regel aus dem
    Modul-Kommentar ("eine gespeicherte Miniatur ist bit-identisch zu
    einer frisch berechneten") bleibt damit unberuehrt; die Ergebnisse
    sind bitgenau dieselben wie bei drei Einzelaufrufen. Nachgewiesen in
    tools/test_vorbereiten_tempo.py."""
    ergebnisse = []
    offen = []
    for (bw, bh) in kaesten:
        if bw <= 0 or bh <= 0:
            ergebnisse.append("uebersprungen")
        elif thumb_cache_has(path, bw, bh):
            ergebnisse.append("treffer")
        else:
            ergebnisse.append(None)
            offen.append(len(ergebnisse) - 1)
    if not offen:
        return ergebnisse

    # KORRIGIERT (Build 129): bei JPEG ist gemeinsames Dekodieren FALSCH.
    #
    # Build 128 hat hier einmal auf das groesste Ziel dekodiert und alle
    # Kaesten daraus gerechnet. Bei PNG ist das richtig und schneller.
    # Bei JPEG war es beides nicht:
    #
    #   FALSCH, weil TurboJPEG verkleinert dekodiert (siehe
    #   original_lesen()). Der ZEICHENPFAD fragt sein Bild je Kasten an
    #   und bekommt fuer eine kleine Kachel ein 1/8 dekodiertes Bild.
    #   Die Vorbereitung rechnete dieselbe Kachel aus dem grossen -
    #   andere Bildpunkte. Die gespeicherte Miniatur war damit NICHT
    #   mehr bit-identisch zu einer frisch berechneten, und genau das
    #   verlangt der Modul-Kommentar oben. Aufgefallen ist es nicht,
    #   weil mein Test in Build 128 nur PNG-Quellen benutzt hat.
    #
    #   LANGSAMER, weil die Flaechenmittelung danach ueber das GROSSE
    #   Bild laufen musste. Gemessen an einem 900x1200-JPEG mit den drei
    #   HDMI-Kaesten: 520 ms gemeinsam gegen 438 ms einzeln, bei
    #   600x800 sogar 193 gegen 128 ms.
    #
    # Also: kann die Bibliothek fuer dieses Bild verkleinert dekodieren,
    # wird je Kasten einzeln gerechnet - das ist zugleich der Weg, den
    # der Zeichenpfad geht. Sonst bleibt es beim gemeinsamen Dekodieren.
    if _skaliert_dekodierbar(path):
        for i in offen:
            try:
                ergebnisse[i] = prewarm_thumb(path, *kaesten[i])
            except Exception:                            # noqa: BLE001
                ergebnisse[i] = "fehler"
        return ergebnisse

    # Dekodiert wird EINMAL, und zwar auf das GROESSTE offene Ziel.
    #
    # Warum das groesste: bei JPEG dekodiert TurboJPEG gleich
    # verkleinert (siehe original_lesen()). Naehme man hier das
    # kleinste, bekaeme der grosse Kasten ein zu kleines Bild und muesste
    # es hochskalieren - das Ergebnis waere schlechter UND anders als
    # bei einem Einzelaufruf. Das groesste Ziel ist fuer alle anderen
    # immer noch gross genug.
    max_b = max(kaesten[i][0] for i in offen)
    max_h_ = max(kaesten[i][1] for i in offen)
    gelesen = original_lesen(path, max_b, max_h_)
    if gelesen is None:
        for i in offen:
            ergebnisse[i] = "fehler"
        return ergebnisse
    # Build 143: die Bildpunkte liegen jetzt ohnehin da - siehe
    # _arbeitskopie_aus_pixeln(). Nur wenn der Nutzer es eingeschaltet
    # hat; der Schalter wird hier gelesen und nicht weiter oben, damit
    # er nichts kostet, solange es gar nichts zu schreiben gibt.
    try:
        from fe.settings import arbeitskopien_enabled as _ak_an
        if _ak_an():
            _arbeitskopie_aus_pixeln(path, gelesen[0], gelesen[1],
                                     gelesen[2])
    except Exception:                                    # noqa: BLE001
        pass
    for i in offen:
        bw, bh = kaesten[i]
        try:
            ergebnisse[i] = _prewarm_aus_gelesenem(path, bw, bh, gelesen)
        except Exception:                                # noqa: BLE001
            ergebnisse[i] = "fehler"
    return ergebnisse


def _prewarm_aus_gelesenem(path, max_w, max_h, gelesen):
    """Der Rechenteil von prewarm_thumb(), losgeloest vom Lesen -
    damit prewarm_thumb_mehrfach() dasselbe dekodierte Original
    mehrfach benutzen kann, ohne dass die Rechnung ein zweites Mal
    dasteht und auseinanderlaufen kann."""
    w, h, pix, (nw, nh) = gelesen

    # Alle Groessenentscheidungen nach den ECHTEN Massen der Datei -
    # nicht nach dem, was gerade im Speicher liegt. Sonst faellt ein
    # verkleinert dekodiertes Bild in den Hochskalier-Zweig oder landet
    # ein paar Bildpunkte neben der Groesse, die der Zeichenpfad
    # erwartet, und die Miniatur waere fuer ihn wertlos.
    if nw <= max_w and nh <= max_h:
        scale = max(1, min(max_w // w, max_h // h, 10))
        if scale == 1:
            # GEAENDERT (Build 92): hier stand "der Zeichenpfad gibt das
            # Original unveraendert zurueck und legt nichts ab, ein
            # Eintrag waere einer, den nie jemand abfragt". Der erste Satz
            # stimmte, der Schluss war falsch - siehe die ausfuehrliche
            # Begruendung in _get_scaled_impl(). Kurz: OHNE Eintrag meldet
            # thumb_cache_has() fuer immer "nicht da", das Vorbereiten
            # hakt dieses Cover nie ab, und der Zeichenpfad ueberspringt
            # es beim Scrollen immer wieder neu.
            #
            # GEAENDERT (Build 128): eine MARKE statt der Kopie - acht
            # Byte statt einer halben Megabyte. Siehe den
            # Kommentarblock bei ORIGINAL_PASST; dort steht auch die
            # Messung, nach der die Kopie nicht nur groesser, sondern
            # sogar langsamer war als das Original neu zu dekodieren.
            _thumb_cache_put_marke(path, max_w, max_h)
            return "fertig"
        sw, sh, out = _hochskalieren(pix, w, h, scale)
        _thumb_cache_put(path, max_w, max_h, sw, sh, bytes(out))
        return "fertig"

    tw, th = zielmass(nw, nh, max_w, max_h)
    data = _verkleinern_flaechenmittel(pix, w, h, tw, th)
    if data is None:
        return "fehler"
    _thumb_cache_put(path, max_w, max_h, tw, th, data)
    return "fertig"


def _hochskalieren(pix, w, h, scale):
    """Ganzzahliges Vergroessern (Pixel-Look, Nearest-Neighbor).
    Rueckgabe: (breite, hoehe, bytearray).

    HERAUSGELOEST (Build 73) aus _get_scaled_impl(), damit die
    Vorberechnung fuer den Festplatten-Cache (prewarm_thumb() unten)
    exakt dieselbe Rechnung benutzt. Das ist keine Kosmetik: der
    Modul-Kommentar oben verlangt, dass eine gespeicherte Miniatur
    BIT-IDENTISCH zu einer frisch berechneten ist - mit zwei getrennten
    Fassungen desselben Algorithmus waere genau das irgendwann still
    auseinandergelaufen."""
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
    return sw, sh, out


ART = ArtCache()

# ENTFERNT (Build 87, Nutzerentscheidung: "grossen
# Systembildhintergrund komplett rausnehmen, war eh bloede"). Hier stand
# BgCache: der haelt je System einen fertig zusammengesetzten
# Vollbild-Puffer, den draw_page_items() beim Kategoriewechsel per
# Blockkopie einsetzte. Der Aufbau eines solchen Puffers (_compose())
# setzte den kompletten Bildschirminhalt zeilenweise in Python neu
# zusammen - bei 1920x1080 sind das 8,3 MB und hier gemessene 41-67 ms,
# auf der schwaecheren MiSTer-CPU entsprechend mehr. Dazu kamen bis zu
# vier gehaltene Vollbildpuffer, bei 1080p rund 33 MB Arbeitsspeicher.
# Beides faellt jetzt ersatzlos weg; der Hintergrund ist die einfarbige
# Flaeche mit Vignette, die fb.clear() ohnehin schon aufbaut und in
# fb._rowcache wiederverwendet.

_art_index_cache = {}   # (basis_ordner, syskey) -> {Name ohne "NNN "-Praefix: Dateiname}

def _ohne_fuehrende_nummer(base):
    """"007 Super Mario Kart (USA)" -> "Super Mario Kart (USA)".

    GEAENDERT (Build 107, Nutzer-Rueckmeldung: "warum ist nach einem
    Neustart das Hauptmenue so traege? Das Scrollen ist total langsam,
    wird erst nach ein paar Sekunden besser").

    Hier stand re.sub(r"^\d+\s+", "", base) - einmal JE COVER-DATEI, und
    _art_index() laeuft beim Start ueber jeden Cover-Ordner jedes
    Systems, in ART_BASE UND ART_HD. Bei einer grossen Sammlung sind
    das schnell sechsstellig viele Aufrufe, und weil das reines Python
    ist, haelt der Hintergrund-Thread dabei durchgehend die GIL - genau
    in den Sekunden, in denen das Hauptmenue zum ersten Mal bedient
    wird. Nachgemessen an 48 Systemen zu je 1500 Covern: der regulaere
    Ausdruck allein war 69 % des gesamten Index-Aufbaus.

    Diese Fassung braucht ihn nicht. Der entscheidende Teil ist die
    erste Zeile: die allermeisten Cover-Namen fangen gar nicht mit einer
    Ziffer an, und fuer die ist nach EINER Pruefung Schluss. Gemessen
    viermal schneller als der regulaere Ausdruck.

    GLEICHWERTIGKEIT IST HIER NICHT VERHANDELBAR, denn ein Unterschied
    faellt nicht auf, er zeigt nur irgendwann das falsche Cover.
    isdecimal() ist deshalb bewusst gewaehlt und nicht das
    naheliegendere isdigit(): \d im regulaeren Ausdruck trifft genau die
    Dezimalziffern, isdigit() zusaetzlich Dinge wie die hochgestellte
    Zwei. Nachgewiesen ueber alle 65536 Zeichen der Basic Multilingual
    Plane in vier Stellungen - null Abweichungen, siehe
    tools/test_cover_index.py."""
    if not base[:1].isdecimal():
        return base
    i, n = 0, len(base)
    while i < n and base[i].isdecimal():
        i += 1
    j = i
    while j < n and base[j].isspace():
        j += 1
    return base[j:] if j > i else base


def vergleichsname(base):
    """Ein Name, unter dem sich dasselbe Spiel aus verschiedenen
    Sammlungen wiederfindet: alles in Klammern faellt weg, danach nur
    noch Buchstaben und Ziffern in Grossschreibung.

        "007 - The World is Not Enough (U) [!]"  ->  007THEWORLDISNOTENOUGH
        "007 - The World Is Not Enough (USA)"    ->  007THEWORLDISNOTENOUGH

    NEUES FEATURE (Build 117, Nutzer-Rueckmeldung: "bei N64 und Sega
    32X werden mir keine Boxarts mehr angezeigt"). Die Ursache war
    keine Aenderung am Code, sondern eine ausgetauschte USB-Platte:
    die ROMs darauf tragen die alte GoodTools-Schreibweise mit "(U)"
    und "[!]", die heruntergeladenen Cover die No-Intro-Schreibweise
    mit "(USA)". Zeichenweise verglichen passt davon nichts zusammen -
    auch nicht die Gross-/Kleinschreibung in "is"/"Is".

    Dasselbe gilt fuer die fremde Datenbank aus Build 115: sie ist
    durchgehend No-Intro benannt. Ohne diesen Abgleich trifft sie nur
    bei Sammlungen, die zufaellig dieselbe Schreibweise benutzen.

    WAS DAS KOSTET: die Regionskennung faellt weg, also koennen die
    US- und die japanische Fassung desselben Spiels auf denselben
    Namen fallen. Das ist der Preis und er ist bewusst bezahlt - er
    faellt nur an, wenn der EXAKTE Name nichts gefunden hat, und ein
    Cover der falschen Region ist besser als gar keins. Voellig
    verschiedene Spiele treffen sich dabei nicht: "Super Mario 64"
    und "Super Mario World" bleiben verschieden."""
    aus = []
    tief = 0
    for c in base:
        if c in "([{":
            tief += 1
            continue
        if c in ")]}":
            if tief:
                tief -= 1
            continue
        if tief:
            continue
        if c.isalnum():
            aus.append(c.upper())
    return "".join(aus)


def _index_ergaenzen(idx, namen, wert_fn):
    """Die zwei Ausweich-Schreibweisen als LUECKENFUELLER nachtragen:
    erst ohne fuehrende Nummer, dann der Vergleichsname.

    Die Reihenfolge ist nicht beliebig. Der exakte Name muss immer
    gewinnen, danach die Nummern-Variante, erst zuletzt der unscharfe
    Vergleich - sonst schlaegt eine zufaellige Dateisystem-Reihenfolge
    durch und mal trifft das eine, mal das andere Cover. Aus demselben
    Grund werden die Namen vorher sortiert: bei zwei Dateien, die
    denselben Vergleichsnamen ergeben, soll immer dieselbe gewinnen."""
    for fn in sorted(namen):
        base = fn.rsplit(".", 1)[0]
        ohne = _ohne_fuehrende_nummer(base)
        if ohne != base and ohne not in idx:
            idx[ohne] = wert_fn(fn)
    for fn in sorted(namen):
        base = fn.rsplit(".", 1)[0]
        knapp = vergleichsname(base)
        if knapp and knapp not in idx:
            idx[knapp] = wert_fn(fn)


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
    # BUGFIX (Nutzer-Rueckmeldung: "wenn er mit Miniaturen erstellen
    # fertig ist, springt das Frontend ins OSD"): ohne Systemkey ist
    # os.path.join(base_dir, None) ein TypeError - und der ist KEIN
    # OSError, wurde vom except unten also nicht gefangen. Er flog bis
    # aus run() heraus, wo der Aufraeum-Block den Bildschirm leert und
    # F12 injiziert. Fuer den Nutzer sah das nicht nach einem Absturz
    # aus, sondern nach "das Frontend springt ins OSD".
    #
    # Ohne Systemkey gibt es schlicht keinen Cover-Ordner - das ist ein
    # normaler Fall (Sonderkategorien wie System oder Zufalls-Zock haben
    # bewusst syskey=None, siehe build_categories()), kein Fehler.
    if not syskey:
        return {}
    key = (base_dir, syskey)
    idx = _art_index_cache.get(key)
    if idx is None:
        idx = {}
        try:
            # GEAENDERT (Build 119): auch PNG und JPG zaehlen als Cover.
            # Der Download legt sie seither im Original ab, statt sie in
            # unser .art-Format umzuwandeln - ohne diese Zeile laege das
            # Cover auf der Karte und wuerde nie gefunden.
            #
            # Reihenfolge: unser eigenes Format zuerst. Liegt zu einem
            # Spiel beides, gewinnt die bereits fertig verkleinerte
            # .art-Datei - sie ist billiger zu zeichnen.
            # KORRIGIERT (Build 129): die Reihenfolge unter den fremden
            # Formaten war bisher die von os.listdir(), also dem Zufall
            # ueberlassen. Liegen zu einem Spiel BEIDE Formate - und
            # genau das passiert seit der JPEG-Arbeitskopie staendig -,
            # entschied das Dateisystem, welches gewinnt. Auf zwei
            # Karten mit demselben Inhalt konnte dasselbe Frontend
            # unterschiedlich schnell sein, ohne dass irgendetwas
            # darauf hingedeutet haette.
            #
            # Feste Reihenfolge: .art, dann JPEG, dann PNG.
            #
            # JPEG vor PNG, weil TurboJPEG verkleinert dekodieren kann
            # und libpng nicht - bei den kleinen Kacheln ist das ein
            # Vielfaches (siehe _skaliert_dekodierbar()). Wer das fuer
            # ein bestimmtes Cover nicht will, loescht die .jpg daneben;
            # das PNG bleibt ja liegen.
            alle = os.listdir(os.path.join(base_dir, syskey))
            names = [fn for fn in alle if fn.endswith(".art")]
            _jpeg = sorted(fn for fn in alle
                           if fn.rsplit(".", 1)[-1].lower() in ("jpg", "jpeg"))
            _png = sorted(fn for fn in alle
                          if fn.rsplit(".", 1)[-1].lower() == "png")
            fremde = _jpeg + _png
            for fn in names:
                idx[fn[:-4]] = fn
            for fn in fremde:
                idx.setdefault(fn.rsplit(".", 1)[0], fn)
            _index_ergaenzen(idx, names + fremde, lambda fn: fn)
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
    # Siehe _art_index(): ohne Systemkey (oder ohne Namen) gibt es
    # keinen Cover-Ordner. Frueher lief das in einen TypeError, der bis
    # aus run() herausflog - siehe dortigen Kommentar.
    if not syskey or not rom_basename:
        return None
    idx = _art_index(base_dir, syskey)
    fn = idx.get(rom_basename)
    if fn is None:
        # Build 117: zuletzt der unscharfe Vergleich - siehe
        # vergleichsname(). Erst hier, damit der exakte Name immer
        # gewinnt.
        fn = idx.get(vergleichsname(rom_basename))
    if fn:
        return os.path.join(base_dir, syskey, fn)
    # NEU (Build 115): erst wenn es bei UNS nichts gibt, wird in der
    # fremden Datenbank nachgesehen. Diese Reihenfolge ist der ganze
    # Sicherheitsgurt der Aenderung - eigenes Artwork behaelt immer
    # Vorrang, und wer die Datenbank gar nicht hat, merkt von alldem
    # nichts (ein os.listdir() je System, das leer zurueckkommt).
    #
    # Bewusst HIER und nicht an den acht Aufrufstellen: die bekommen
    # damit alle denselben Rueckfall, ohne dass eine davon vergessen
    # werden kann.
    if fremdquellen_enabled():
        fremd = docs_cover(syskey, rom_basename)
        if fremd:
            return fremd
    return os.path.join(base_dir, syskey, rom_basename + ".art")

def art_path(syskey, rom_basename):
    return _art_path_in(ART_BASE, syskey, rom_basename)


# ---------------------------------------------------------------------------
# FREMDE ARTWORK-/METADATENQUELLE unter DOCS_BASE (Build 115)
# ---------------------------------------------------------------------------

_docs_ordner_cache = None     # normalisierter Name -> echter Ordnername
_docs_index_cache = {}        # syskey -> {ROM-Name: voller Bildpfad}
_docs_info_cache = {}         # syskey -> {ROM-Name: {year, genre, ...}}
_docs_info_knapp = {}         # syskey -> {vergleichsname: {...}}, faul
_docs_syn_cache = {}          # (syskey, sprache) -> {ROM-Name: Text}
_docs_syn_knapp = {}          # (syskey, sprache) -> {vergleichsname: Text}
_docs_syn_order = []          # aelteste zuerst, siehe DOCS_SYNOPSIS_MAX
_docs_syn_laeuft = set()      # gerade im Hintergrund eingelesen
_docs_syn_sperre = threading.Lock()
_fremd_an = None              # Schalterzustand, einmal je Sitzung


def fremdquellen_enabled():
    """Darf die fremde Datenbank gelesen werden?

    Der Schalter selbst wohnt in fe/settings.py - das Modul importiert
    aber seinerseits aus fe/art.py, ein Import oben im Kopf waere also
    ein Ringschluss. Deshalb hier verzoegert geholt UND gemerkt: der
    Wert wird bei jeder Cover-Suche gebraucht, und eine Dateiabfrage
    je Eintrag waere genau die Sorte stiller Kosten, gegen die die
    Builds 104 bis 110 angegangen sind. Ein Schalterwechsel ruft
    docs_caches_leeren() und setzt ihn damit zurueck."""
    global _fremd_an
    if _fremd_an is None:
        try:
            from fe.settings import fremdquellen_enabled as _schalter
            _fremd_an = bool(_schalter())
        except Exception:
            _fremd_an = True
    return _fremd_an


def _schlank(name):
    """Nur Buchstaben und Ziffern, gross. "Mega Drive", "MegaDrive"
    und "mega-drive" werden damit derselbe Name.

    Dieselbe Vergleichsform wie bei den Kategorie-Abzeichen in Build
    112 - dort hat sie sich bewaehrt, weil Ordnernamen auf fremden
    Karten eben nicht genau so geschrieben sind wie bei uns."""
    return "".join(c for c in name.upper() if c.isalnum())


def fremd_wurzeln():
    """Alle Orte, an denen fremdes Artwork liegen kann - in der
    Reihenfolge, in der gesucht wird.

    ERWEITERT (Build 120, Nutzerwunsch "Unterstuetzung fuer
    MiSTer-Artpacks"). Bis dahin war nur die Handbuch-/Artwork-
    Datenbank unter /media/fat/docs gemeint (Build 115). Artpacks
    landen aber je nach Paket woanders - mal in einem eigenen
    Artwork-Ordner, mal neben den ROMs.

    DOCS_BASE steht bewusst zuerst und wird bei jedem Aufruf frisch
    gelesen: die Tests setzen es um, und eine eingefrorene Kopie waere
    genau die Falle, die in diesem Projekt schon mehrfach zugeschnappt
    ist (siehe GAMES_BASES in fe/paths.py).

    Die Spiele-Wurzeln kommen zuletzt: dort liegen die ROMs, und
    manche Pakete legen ihre Bilder direkt daneben."""
    wurzeln = [DOCS_BASE]
    wurzeln.extend(FREMD_ZUSATZ_WURZELN)
    try:
        import fe.paths
        wurzeln.extend(fe.paths.GAMES_BASES)
    except Exception:                                    # noqa: BLE001
        pass
    # Reihenfolge erhalten, Doppelte raus.
    gesehen = set()
    ergebnis = []
    for w in wurzeln:
        if w and w not in gesehen:
            gesehen.add(w)
            ergebnis.append(w)
    return ergebnis


def _docs_ordner():
    """Was unter den Fremdquellen tatsaechlich liegt: normalisierter
    Systemname -> Liste der echten Ordnerpfade, in Suchreihenfolge.
    Einmal je Sitzung gelesen.

    Bewusst dynamisch statt als feste Tabelle: welche Systeme dort
    liegen, entscheidet der Nutzer mit dem, was er installiert hat -
    eine einprogrammierte Liste waere schon beim naechsten
    Datenbank-Update falsch."""
    global _docs_ordner_cache
    if _docs_ordner_cache is None:
        gefunden = {}
        for wurzel in fremd_wurzeln():
            try:
                namen = os.listdir(wurzel)
            except OSError:
                continue
            for name in namen:
                voll = os.path.join(wurzel, name)
                if os.path.isdir(voll):
                    gefunden.setdefault(_schlank(name), []).append(voll)
        _docs_ordner_cache = gefunden
    return _docs_ordner_cache


def _docs_ordner_fuer(syskey):
    """Der ERSTE passende Fremdordner zu einem Systemschluessel, sonst
    None. Fuer alle siehe _docs_ordner_alle().

    Gesucht wird in dieser Reihenfolge: der Systemschluessel selbst
    (GBC findet so seinen eigenen Ordner, obwohl seine ROMs bei uns
    unter GAMEBOY liegen), danach die ROM-Ordnernamen aus unserer
    Systemliste (Mega Drive heisst dort MegaDrive ODER Genesis - beide
    kommen vor, und beide gibt es auch in der Datenbank)."""
    alle = _docs_ordner_alle(syskey)
    return alle[0] if alle else None


def _docs_ordner_alle(syskey):
    """Alle passenden Fremdordner zu einem Systemschluessel, in
    Suchreihenfolge. Ein System kann in mehreren Paketen vorkommen -
    dann ergaenzen sie sich, statt dass eines gewinnt."""
    if not syskey:
        return []
    ordner = _docs_ordner()
    if not ordner:
        return []
    kandidaten = [syskey]
    try:
        from fe.systems import GAME_SYSTEMS, OPTIONAL_GAME_SYSTEMS
        alle = list(GAME_SYSTEMS) + list(OPTIONAL_GAME_SYSTEMS)
    except Exception:
        alle = []
    for eintrag in alle:
        if eintrag[1] != syskey:
            continue
        for rom_ordner in eintrag[2]:
            # "SNES/SMW_HACKS" -> "SNES": Unterordner einer Sammlung
            # haben in der Datenbank keinen eigenen Eintrag, ihre
            # Spiele aber sehr wohl.
            kandidaten.append(rom_ordner.split("/")[0])
    treffer = []
    gesehen = set()
    for k in kandidaten:
        for pfad in ordner.get(_schlank(k), ()):
            if pfad not in gesehen:
                gesehen.add(pfad)
                treffer.append(pfad)
    return treffer


def _docs_index(syskey):
    """{ROM-Name ohne Endung: voller Bildpfad} fuer ein System.

    Aufgebaut nach demselben Muster wie _art_index(): ein os.listdir()
    je System, beim ersten Fehltreffer, danach gecacht. Zusaetzlich
    wird - wie dort - die Fassung ohne fuehrende "NNN "-Nummer als
    Luecke nachgetragen, damit kuratierte Sammlungen ihre Cover
    wiederfinden."""
    if not syskey:
        return {}
    idx = _docs_index_cache.get(syskey)
    if idx is not None:
        return idx
    idx = {}
    # ERWEITERT (Build 120): mehrere Wurzeln, mehrere Unterordner. Der
    # erste Fund gewinnt - deshalb ergaenzen weitere Pakete nur, was das
    # erste nicht hatte, statt es zu ueberschreiben.
    #
    # Der Aufwand bleibt derselbe wie vorher: ein os.listdir() je
    # tatsaechlich vorhandenem Ordner, beim ersten Fehltreffer, danach
    # gecacht. Ordner, die es nicht gibt, kosten einen fehlschlagenden
    # Systemaufruf.
    for basis in _docs_ordner_alle(syskey):
        for unter in DOCS_UNTERORDNER:
            ordner = os.path.join(basis, unter) if unter else basis
            try:
                namen = [fn for fn in os.listdir(ordner)
                         if fn.rsplit(".", 1)[-1].lower()
                         in ("jpg", "jpeg", "png")]
            except OSError:
                continue
            if not namen:
                continue
            for fn in namen:
                idx.setdefault(fn.rsplit(".", 1)[0], os.path.join(ordner, fn))
            _index_ergaenzen(idx, namen,
                             lambda fn, _o=ordner: os.path.join(_o, fn))
    _docs_index_cache[syskey] = idx
    return idx


def docs_cover(syskey, rom_basename):
    """Pfad zu einem fremden Cover, sonst None.

    Der unscharfe Vergleich (Build 117) ist hier besonders wichtig: die
    Datenbank ist durchgehend No-Intro benannt. Wer seine ROMs anders
    benannt hat, haette sonst 21.198 Cover auf der Karte, von denen
    keines gefunden wird."""
    if not syskey or not rom_basename:
        return None
    idx = _docs_index(syskey)
    return idx.get(rom_basename) or idx.get(vergleichsname(rom_basename))


def _docs_infos(syskey):
    """gameinfo.tsv eines Systems als {ROM-Name: {...}}.

    Spalten laut Kopfzeile der Datei:
        #key  name  year  genre  developer  players

    Das ist dieselbe Schluesselung wie in unserem eigenen
    meta/<system>.json (ROM-Basisname), nur mit einem Feld mehr - den
    Entwickler kannte unsere libretro-Quelle nicht. Und es steht
    bereits auf der Karte: wer seinen MiSTer nicht am Netz hat,
    bekommt damit ueberhaupt zum ersten Mal Spieledaten."""
    if not syskey:
        return {}
    daten = _docs_info_cache.get(syskey)
    if daten is not None:
        return daten
    daten = {}
    # Build 120: dieselbe Tabelle kann in mehreren Paketen liegen. Die
    # erste gefundene gewinnt - danach wird nicht weitergesucht, weil
    # zwei Tabellen desselben Systems sich sonst gegenseitig
    # ueberschreiben wuerden, je nach Reihenfolge mal so, mal so.
    for pfad in _docs_info_pfade(syskey):
        try:
            with open(pfad, "r", encoding="utf-8", errors="replace") as fh:
                for zeile in fh:
                    if not zeile or zeile.startswith("#"):
                        continue
                    teile = zeile.rstrip("\r\n").split("\t")
                    if len(teile) < 2 or not teile[0]:
                        continue
                    eintrag = {}
                    for spalte, feld in ((2, "year"), (3, "genre"),
                                         (4, "developer"), (5, "players")):
                        if len(teile) > spalte and teile[spalte].strip():
                            eintrag[feld] = teile[spalte].strip()
                    if eintrag:
                        daten[teile[0]] = eintrag
                        # ENTFERNT (Build 141): hier stand der
                        # Ausweich-Schluessel aus Build 117 -
                        # vergleichsname() JE ZEILE, beim Einlesen.
                        #
                        # Im DRAGEND_PROFILE des Nutzers kostete das
                        # 803 ms von 1089 ms, also 74 % des ganzen
                        # Einlesens, und zwar mitten im Zeichenweg.
                        # Gebraucht wird der Schluessel aber nur, wenn
                        # der exakte Name NICHT trifft - bei einer
                        # No-Intro-benannten Sammlung also nie. Er
                        # entsteht jetzt faul, siehe _knapp_index().
        except OSError:
            continue
        except Exception:
            # Eine kaputte Tabelle darf nichts umwerfen - lieber keine
            # Zusatzdaten als ein Absturz beim Zeichnen einer Zeile.
            daten = {}
        if daten:
            break
    _docs_info_cache[syskey] = daten
    return daten


def _docs_info_pfade(syskey):
    """Wo eine gameinfo.tsv fuer dieses System liegen koennte - in
    Suchreihenfolge. Dieselben Ordner wie bei den Covern."""
    pfade = []
    for basis in _docs_ordner_alle(syskey):
        for unter in DOCS_UNTERORDNER:
            ordner = os.path.join(basis, unter) if unter else basis
            pfade.append(os.path.join(ordner, DOCS_INFO))
    return pfade


def _knapp_index(daten, cache, schluessel):
    """Der Ausweich-Index (Build 141): {vergleichsname: Wert}.

    Wird ERST GEBAUT, wenn ihn jemand braucht - also wenn ein exakter
    Name nicht getroffen hat. Vorher entstand er beim Einlesen, fuer
    jede Zeile, ob gebraucht oder nicht: 1787 Aufrufe von
    vergleichsname() fuer eine SNES-Tabelle, gemessen 803 ms auf dem
    Geraet, mitten im Zeichenweg.

    Wer seine ROMs wie die Datenbank benennt (No-Intro, der Normalfall
    seit dem Boxart-Download), trifft immer exakt und zahlt jetzt gar
    nichts mehr. Wer anders benennt, zahlt es einmal je System.

    Der Index liegt im mitgegebenen Cache-Dict unter demselben
    Schluessel wie die Tabelle - so verschwindet er zusammen mit ihr,
    wenn docs_caches_leeren() oder die Verdraengung zuschlaegt."""
    idx = cache.get(schluessel)
    if idx is not None:
        return idx
    idx = {}
    for name, wert in daten.items():
        knapp = vergleichsname(name)
        if knapp and knapp not in idx:
            idx[knapp] = wert
    cache[schluessel] = idx
    return idx


def docs_meta(syskey, rom_basename):
    """Metadaten aus der fremden Datenbank, sonst {}."""
    if not syskey or not rom_basename:
        return {}
    daten = _docs_infos(syskey)
    if not daten:
        return {}
    treffer = daten.get(rom_basename)
    if treffer is None:
        treffer = _knapp_index(daten, _docs_info_knapp,
                               syskey).get(vergleichsname(rom_basename))
    return treffer or {}


def _docs_synopsis_lesen(syskey, sprache):
    """Die eigentliche Lesearbeit - OHNE Cache, OHNE Verdraengung.

    Bewusst herausgeloest (Build 141), damit derselbe Code aus dem
    Hintergrund-Thread laufen kann. Der Ausweich-Schluessel aus
    Build 117 entsteht hier NICHT mehr mit: siehe _knapp_index()."""
    daten = {}
    for pfad in _docs_synopsis_pfade(syskey, sprache):
        try:
            with open(pfad, "r", encoding="utf-8", errors="replace") as fh:
                for zeile in fh:
                    if not zeile or zeile.startswith("#"):
                        continue
                    teile = zeile.rstrip("\r\n").split("\t", 1)
                    if len(teile) < 2 or not teile[0] or not teile[1].strip():
                        continue
                    daten[teile[0]] = teile[1].strip()
        except OSError:
            continue
        except Exception:
            # Eine kaputte Tabelle darf nichts umwerfen - lieber keine
            # Beschreibung als ein Absturz beim Zeichnen.
            daten = {}
        if daten:
            break
    return daten


def _docs_synopsis_eintragen(schluessel, daten):
    """Fertig gelesene Tabelle in den Speicher legen und verdraengen."""
    _docs_syn_cache[schluessel] = daten
    _docs_syn_order.append(schluessel)
    while len(_docs_syn_order) > DOCS_SYNOPSIS_MAX:
        alt = _docs_syn_order.pop(0)
        if alt != schluessel:
            _docs_syn_cache.pop(alt, None)
            _docs_syn_knapp.pop(alt, None)


def _docs_synopsis_tabelle(syskey, sprache, im_hintergrund=True):
    """synopsis_<sprache>.tsv eines Systems als {ROM-Name: Text}.

    GEAENDERT (Build 141, aus einem Profil vom Geraet): das Einlesen
    stand vorher MITTEN IM ZEICHENWEG und kostete dort gemessen
    1089 ms - einmal je System, aber als voll sichtbarer Haenger.
    Davon entfielen 803 ms auf vergleichsname() je Zeile (jetzt faul,
    siehe _knapp_index()) und der Rest auf das Lesen selbst.

    Die verbleibenden rund 300 ms gehoeren trotzdem nicht in den
    Zeichenweg. Sie laufen deshalb in einem Hintergrund-Thread; bis er
    fertig ist, gibt es einfach noch keine Beschreibung, und der
    COVER_SETTLE-Nachlader zeichnet sie nach - genau wie bei einem
    Cover, das der zweite Kern gerade rechnet.

    Der Thread liest nur (open/read), traegt das Ergebnis mit EINER
    Zuweisung ein und fasst sonst nichts an. Deshalb braucht es hier
    keine weitere Absicherung ausser dem Merker, dass derselbe
    Schluessel nicht zweimal gleichzeitig gelesen wird."""
    if not syskey or sprache not in DOCS_SPRACHEN:
        return {}
    schluessel = (syskey, sprache)
    daten = _docs_syn_cache.get(schluessel)
    if daten is not None:
        return daten
    if not im_hintergrund:
        daten = _docs_synopsis_lesen(syskey, sprache)
        _docs_synopsis_eintragen(schluessel, daten)
        return daten
    with _docs_syn_sperre:
        if schluessel in _docs_syn_laeuft:
            return {}
        _docs_syn_laeuft.add(schluessel)

    def _arbeit():
        try:
            erg = _docs_synopsis_lesen(syskey, sprache)
        except Exception:                                    # noqa: BLE001
            erg = {}
        _docs_synopsis_eintragen(schluessel, erg)
        with _docs_syn_sperre:
            _docs_syn_laeuft.discard(schluessel)
        # Den Nachlader wecken, damit die fertige Tabelle auch auf den
        # Schirm kommt, ohne dass jemand eine Taste druecken muss.
        ART._deferred_something = True

    threading.Thread(target=_arbeit, daemon=True).start()
    return {}


def _docs_synopsis_pfade(syskey, sprache):
    """Wo eine synopsis_<sprache>.tsv liegen koennte - dieselben Ordner
    wie bei den Covern und bei gameinfo.tsv."""
    datei = DOCS_SYNOPSIS % sprache
    pfade = []
    for basis in _docs_ordner_alle(syskey):
        for unter in DOCS_UNTERORDNER:
            ordner = os.path.join(basis, unter) if unter else basis
            pfade.append(os.path.join(ordner, datei))
    return pfade


def docs_synopsis(syskey, rom_basename, sprache="en"):
    """Beschreibung eines Spiels aus der fremden Datenbank, sonst "".

    Reihenfolge: gewuenschte Sprache, dann Englisch als Rueckfall -
    und zwar je Spiel, nicht je Datei: die deutsche Tabelle hat
    einzelne Luecken, die die englische fuellt. Umgekehrt NICHT, damit
    in einer englischen Oberflaeche kein deutscher Absatz auftaucht."""
    if not syskey or not rom_basename:
        return ""
    # Der Schalter "fremde Quellen" gilt hier genauso wie fuer Cover
    # und Spieledaten (siehe get_meta()). Bewusst HIER geprueft und
    # nicht beim Aufrufer: eine Quelle, die man abschalten kann, darf
    # nicht davon abhaengen, dass jeder Aufrufer daran denkt.
    if not fremdquellen_enabled():
        return ""
    # Wir fuehren nur Deutsch und Englisch (DOCS_SPRACHEN). Kaeme doch
    # einmal etwas anderes an, gilt Englisch - und die fremde Datei
    # wird gar nicht erst gesucht.
    if sprache not in DOCS_SPRACHEN:
        sprache = "en"
    knapp = None
    reihe = [sprache] if sprache == "en" else [sprache, "en"]
    for spr in reihe:
        tabelle = _docs_synopsis_tabelle(syskey, spr)
        if not tabelle:
            # Noch nicht da (wird gerade im Hintergrund gelesen) oder
            # gibt es nicht. In BEIDEN Faellen hier aufhoeren statt zur
            # naechsten Sprache zu gehen: sonst wuerde eine einzige
            # fehlende deutsche Zeile die komplette englische Tabelle
            # von der Karte holen. Genau das stand im Profil des
            # Nutzers - _docs_synopsis_tabelle() zweimal, 1051 ms.
            # Ist die deutsche Tabelle erst da, greift der Rueckfall
            # beim naechsten Zeichnen ganz normal.
            if spr == reihe[0]:
                return ""
            continue
        treffer = tabelle.get(rom_basename)
        if treffer is None:
            if knapp is None:
                knapp = vergleichsname(rom_basename)
            treffer = _knapp_index(tabelle, _docs_syn_knapp,
                                   (syskey, spr)).get(knapp)
        if treffer:
            return treffer
    return ""


def docs_caches_leeren():
    """Nach einem erneuten Einlesen oder einem Schalterwechsel."""
    global _docs_ordner_cache, _fremd_an
    _docs_ordner_cache = None
    _fremd_an = None
    _docs_index_cache.clear()
    _docs_info_cache.clear()
    _docs_info_knapp.clear()
    _docs_syn_cache.clear()
    _docs_syn_knapp.clear()
    del _docs_syn_order[:]
    # Der eigene Cover-Index wird vorsichtshalber mit geleert. Noetig
    # ist es nach heutigem Stand nicht - _art_path_in() fragt die
    # fremde Quelle bei jedem Aufruf frisch -, aber ein Schalterwechsel
    # passiert einmal im Jahr, und die Alternative waere, sich diese
    # Feinheit dauerhaft merken zu muessen.
    _art_index_cache.clear()

def _category_art_key(name, syskey):
    """Kuenstlicher Schluessel NUR fuer die Sysart-Suche
    (SYSART_BASE) - fuer echte Systeme identisch mit syskey.

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
    # NEU (Build 112, Nutzerwunsch: zwei weitere Abzeichen fuer "Custom
    # Cores" und "Physical Disc Cores").
    #
    # Das sind Ordner auf der SD-Karte, also derselbe Fall wie
    # "Computer" weiter oben: syskey=None, der Kategoriename ist genau
    # der Ordnername. Bei "Computer" steht dort ein woertlicher
    # Vergleich, samt der ehrlichen Einschraenkung "bei anderen Nutzern
    # mit anders benanntem Ordner greift dieser Sonderfall nicht".
    #
    # Fuer diese beiden wird es etwas nachsichtiger gemacht: verglichen
    # wird der auf Buchstaben und Ziffern eingedampfte Name. Damit
    # treffen "Custom Cores", "custom cores", "CustomCores" und
    # "_Custom Cores" alle dasselbe Abzeichen - Ordnernamen schreibt
    # jeder ein bisschen anders, und ein fehlendes Bild waere die
    # unnoetigste aller Enttaeuschungen.
    schlank = "".join(c for c in name.upper() if c.isalnum())
    return ORDNER_ABZEICHEN.get(schlank)


# Ordnername (eingedampft auf Buchstaben/Ziffern) -> Abzeichen-Datei.
# Siehe _category_art_key() fuer die Begruendung des nachsichtigen
# Vergleichs.
ORDNER_ABZEICHEN = {
    "CUSTOMCORES": "CUSTOM_CORES",
    "PHYSICALDISCCORES": "PHYSICAL_DISC_CORES",
    # Die beiden folgenden sind nur Abkuerzungen derselben Ordner, wie
    # sie in freier Wildbahn ebenfalls vorkommen.
    "DISCCORES": "PHYSICAL_DISC_CORES",
    "PHYSICALDISC": "PHYSICAL_DISC_CORES",
}

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
    eigene = _meta_cache[syskey].get(rom_basename, {})
    # NEU (Build 115): die fremde Tabelle fuellt Luecken auf, ersetzt
    # aber nichts. Sie kennt ein Feld mehr als unsere libretro-Quelle
    # (den Entwickler), deshalb wird auch bei einem vorhandenen
    # eigenen Eintrag nachgesehen - aber nur fuer Felder, die wir
    # selbst nicht haben.
    #
    # Der Reihenfolge wegen: unsere eigenen Daten hat der Nutzer
    # bewusst heruntergeladen, die fremden lagen zufaellig auf der
    # Karte. Bei Widerspruch gewinnt das Gewollte.
    if not fremdquellen_enabled():
        return eigene
    fremd = docs_meta(syskey, rom_basename)
    if not fremd:
        return eigene
    if not eigene:
        return fremd
    zusammen = dict(fremd)
    zusammen.update(eigene)
    return zusammen

