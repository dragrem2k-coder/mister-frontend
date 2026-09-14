#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bilder dekodieren ueber die Systembibliotheken des MiSTer.

WARUM DAS UEBERHAUPT GEHT. Auf dem MiSTer ist weder Pillow installiert
noch liegt ein Kommandozeilenwerkzeug wie djpeg oder ffmpeg im Pfad -
danach war mehrfach gesucht worden, und die Antwort war jedesmal nein.
Uebersehen wurde dabei das Naheliegende: die Bibliotheken selbst sind
da.

    /lib/libturbojpeg.so.0.2.0
    /lib/libpng16.so.16.37.0
    /lib/libjpeg.so.8.2.2

Python bringt ctypes mit, also laesst sich die zweite direkt aufrufen -
ohne Compiler, ohne Installation, ohne neue Abhaengigkeit. Das
Dekodieren passiert dann in C. Ein JPEG im Interpreter zu dekodieren
haette pro Cover Sekunden gekostet (die Huffman-Dekodierung laeuft Bit
fuer Bit); so sind es Millisekunden.

WARUM AUSDRUECKLICH TurboJPEG UND NICHT libjpeg. Die klassische
libjpeg-Schnittstelle verlangt, dass der Aufrufer
`struct jpeg_decompress_struct` bitgenau nachbaut und ihre Groesse an
jpeg_CreateDecompress() meldet - die haengt von der Uebersetzung ab,
ein Fehlgriff faellt nicht auf, sondern beschaedigt Speicher. Und
libjpeg beendet bei einem kaputten Bild den ganzen Prozess ueber
exit(), was ohne setjmp/longjmp aus Python heraus nicht abzufangen ist.

TurboJPEG ist die zweite Schnittstelle derselben Bibliothek: ein
undurchsichtiger Zeiger statt einer offengelegten Struktur, und Fehler
kommen als Rueckgabewert -1 zurueck statt als exit(). Damit ist die
Anbindung sowohl kurz als auch sicher.

Trotzdem gilt: Bildformate aus fremder Hand sind Angriffsflaeche, und
diese Bibliothek liegt ausserhalb unserer Kontrolle. Der Aufruf gehoert
deshalb bevorzugt in den Vorauslader-PROZESS (fe/prewarm_worker.py,
Build 104) - stuerzt dort etwas ab, merkt es der Elternprozess, startet
neu und zeigt "kein Artwork". Das ist derselbe Schutz, der seit Build
82 verhindert, dass die Miniaturenvorbereitung das Frontend mitreisst.

UND DAS EIGENTLICH WICHTIGE: libpng. Unser eigener PNG-Dekoder in
fe/art.py ist reines Python und braucht fuer ein Cover 200 bis 500 ms
auf dem Geraet. Genau diese Zahl ist der Grund fuer den Vorauslader im
zweiten Prozess (Build 104), die Notbremse nach zwei Sekunden (Build
105) und das Auslagern kalter Cover (Build 107). Ueber libpng sind es
gemessen 2,6 ms im Container, auf dem MiSTer also grob 30 ms - und
bitgenau dasselbe Bild bei jedem Farbtyp, den unserer beherrscht
(nachgewiesen in tools/test_bildlib.py). Interlaced PNG kann unserer
gar nicht, libpng schon.

Unser Python-Dekoder bleibt trotzdem drin, als Rueckfall. Fehlt die
Bibliothek auf einem Geraet, laeuft alles exakt wie bisher - ein
Rueckschritt ist dadurch unmoeglich.

VERTRAG NACH AUSSEN: jede decode_*-Funktion liefert (breite, hoehe,
bgra) oder None - genau wie decode_png() in fe/art.py, und wie dort
wird NIE eine Ausnahme nach aussen gelassen. Fehlt die Bibliothek,
liefert die Funktion immer None.
"""
import ctypes
import os

# TurboJPEG-Pixelformate (tjPixelFormats in turbojpeg.h). Wir brauchen
# nur eines: BGRX schreibt B, G, R und laesst das vierte Byte in Ruhe -
# deshalb wird der Zielpuffer vorher mit 0xFF gefuellt und ist danach
# gueltiges BGRA mit voller Deckkraft, ohne dass ein Python-Durchlauf
# ueber Millionen Bytes noetig waere.
#
# BUGFIX (Build 126, Nutzer-Rueckmeldung mit Bildschirmfoto: "die Farben
# von den Boxarts passen nicht"). Hier stand TJPF_RGBX = 2, und
# derselbe Fehler steckte in der PNG-Seite: beide lieferten RGBA, der
# Bildspeicher des MiSTer ist aber BGRA. Rot und Blau waren also auf
# JEDEM Cover vertauscht, das nicht aus einer .art-Datei kam - das
# goldene Nintendo-Siegel wurde blau, der Himmel kippte ins Kalte.
#
# Warum es so lange niemandem auffiel: bis Build 119 wurden alle Cover
# beim Download in .art umgewandelt, und DER Weg war immer richtig
# (siehe rgb_to_art() in mister_boxart.py). Erst seit PNG/JPG im
# Original liegen bleiben - und seit Build 123 aus dem png-Spiegel
# kommen - laeuft die Anzeige ueberhaupt durch diese beiden Dekoder.
TJPF_BGRX = 3

TJ_MAX_KANTE = 8000        # groesser ist bei Coverbildern Unsinn
TJ_MAX_PIXEL = 16_000_000  # Schutz gegen absichtlich riesige Bilder

_KANDIDATEN = (
    "libturbojpeg.so.0",
    "libturbojpeg.so",
    "/lib/libturbojpeg.so.0",
    "/usr/lib/libturbojpeg.so.0",
)


class _Skalierung(ctypes.Structure):
    """tjscalingfactor - Zaehler/Nenner, z.B. 1/2, 1/4, 3/8."""
    _fields_ = [("num", ctypes.c_int), ("denom", ctypes.c_int)]


def _bibliothek_laden():
    """Liefert die geladene Bibliothek oder None.

    Bewusst tolerant: fehlt sie, ist das kein Fehler, sondern heisst
    nur, dass dieses Geraet keine JPGs lesen kann."""
    for name in _KANDIDATEN:
        try:
            lib = ctypes.CDLL(name)
        except OSError:
            continue
        try:
            lib.tjInitDecompress.restype = ctypes.c_void_p
            lib.tjInitDecompress.argtypes = []
            lib.tjDestroy.restype = ctypes.c_int
            lib.tjDestroy.argtypes = [ctypes.c_void_p]
            lib.tjDecompressHeader3.restype = ctypes.c_int
            lib.tjDecompressHeader3.argtypes = [
                ctypes.c_void_p, ctypes.c_char_p, ctypes.c_ulong,
                ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int),
                ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int)]
            lib.tjDecompress2.restype = ctypes.c_int
            lib.tjDecompress2.argtypes = [
                ctypes.c_void_p, ctypes.c_char_p, ctypes.c_ulong,
                ctypes.c_char_p, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                ctypes.c_int, ctypes.c_int]
            lib.tjGetScalingFactors.restype = ctypes.POINTER(_Skalierung)
            lib.tjGetScalingFactors.argtypes = [ctypes.POINTER(ctypes.c_int)]
        except AttributeError:
            # Eine Bibliothek dieses Namens, aber ohne die erwarteten
            # Funktionen - dann lieber gar nicht als halb.
            continue
        # NEU (Build 129): das SCHREIBEN von JPEG, fuer die
        # Arbeitskopie. Bewusst in einem EIGENEN try: es ist die
        # Kuer, nicht die Pflicht. Eine Bibliothek, die nur lesen kann,
        # soll weiterhin zum Lesen benutzt werden - dann gibt es eben
        # keine Arbeitskopien, und alles laeuft wie in Build 128.
        try:
            lib.tjInitCompress.restype = ctypes.c_void_p
            lib.tjInitCompress.argtypes = []
            lib.tjCompress2.restype = ctypes.c_int
            lib.tjCompress2.argtypes = [
                ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int,
                ctypes.c_int, ctypes.c_int, ctypes.c_int,
                ctypes.POINTER(ctypes.POINTER(ctypes.c_ubyte)),
                ctypes.POINTER(ctypes.c_ulong),
                ctypes.c_int, ctypes.c_int, ctypes.c_int]
            lib.tjFree.restype = None
            lib.tjFree.argtypes = [ctypes.POINTER(ctypes.c_ubyte)]
            lib._dragend_schreiben = True
        except AttributeError:
            lib._dragend_schreiben = False
        return lib
    return None


_LIB = _bibliothek_laden()


def verfuegbar():
    """Kann dieses Geraet JPGs lesen? Einmal beim Start beantwortet."""
    return _LIB is not None


def schreiben_verfuegbar():
    """Kann dieses Geraet JPGs auch SCHREIBEN? (Build 129)

    Getrennt von verfuegbar(), weil es eine eigene Antwort ist: das
    Lesen ist Pflicht (ohne kein fremdes Cover), das Schreiben Kuer
    (ohne keine Arbeitskopie, sonst alles wie gehabt)."""
    return _LIB is not None and getattr(_LIB, "_dragend_schreiben", False)


# Farbunterabtastung beim Schreiben. TJSAMP_444 = 0 heisst: KEINE.
#
# Der uebliche Wert waere 420 - halbe Farbaufloesung, deutlich kleinere
# Dateien, bei Fotos kaum sichtbar. Boxart ist aber kein reines Foto:
# darauf steht der Spieltitel, oft farbig auf farbigem Grund, und genau
# an solchen Kanten macht 420 sichtbare Farbsaeume. Die Arbeitskopie
# soll dem Original so nahe wie moeglich kommen; der Platz, den 444
# mehr braucht, ist neben dem gesparten Rechenaufwand zweitrangig.
TJSAMP_444 = 0


def encode_jpeg(breite, hoehe, pix_bgra, guete=90):
    """BGRA-Bildpunkte zu JPEG-Bytes. None, wenn das nicht geht.

    NEU (Build 129), fuer die Arbeitskopie beim Cover-Download.

    WOZU DAS GUT IST: TurboJPEG kann verkleinert DEKODIEREN (1/2, 1/4,
    1/8 direkt aus dem Dekoder), libpng kann das nicht. Bei den kleinen
    Kacheln muss die teure Flaechenmittelung dadurch nur ueber einen
    Bruchteil der Bildpunkte laufen. Gemessen an einem 900x1200-Cover
    mit den drei HDMI-Kaesten: 674 ms aus dem PNG, 438 ms aus dem JPEG.

    "pix_bgra" ist der Puffer, wie ihn dieses Modul auch liefert - vier
    Byte je Bildpunkt, Blau zuerst (der Bildspeicher des MiSTer ist
    BGRA, siehe TJPF_BGRX oben). Das Alpha-Byte geht verloren; JPEG
    kennt keine Transparenz. Deshalb wird diese Funktion fuer die
    Kategorie-Abzeichen NICHT benutzt - die brauchen ihren
    durchsichtigen Rand."""
    if not schreiben_verfuegbar() or breite <= 0 or hoehe <= 0:
        return None
    if len(pix_bgra) < breite * hoehe * 4:
        return None
    griff = None
    puffer = ctypes.POINTER(ctypes.c_ubyte)()
    groesse = ctypes.c_ulong(0)
    try:
        griff = _LIB.tjInitCompress()
        if not griff:
            return None
        if _LIB.tjCompress2(griff, bytes(pix_bgra), breite, breite * 4,
                            hoehe, TJPF_BGRX, ctypes.byref(puffer),
                            ctypes.byref(groesse), TJSAMP_444,
                            int(guete), 0) != 0:
            return None
        return bytes(bytearray(puffer[:groesse.value]))
    except Exception:                                    # noqa: BLE001
        return None
    finally:
        # tjFree ist Pflicht: der Puffer kommt aus der Bibliothek, nicht
        # von Python. Ohne das waechst der Speicher mit jedem Cover -
        # und ein Durchlauf ueber 28000 Stueck merkt das.
        try:
            if puffer:
                _LIB.tjFree(puffer)
        except Exception:                                # noqa: BLE001
            pass
        try:
            if griff:
                _LIB.tjDestroy(griff)
        except Exception:                                # noqa: BLE001
            pass


def _stufen():
    """Alle Skalierungsstufen, die die Bibliothek beherrscht.

    TurboJPEG kann beim Dekodieren gleich verkleinern (1/8, 1/4, 3/8,
    1/2 ...). Das ist kein Luxus: ein 600x800-Cover als Miniatur zu
    brauchen und trotzdem voll zu dekodieren waere auf der MiSTer-CPU
    das Sechzehnfache an Arbeit - und danach muesste Python die
    Verkleinerung auch noch selbst rechnen."""
    anzahl = ctypes.c_int(0)
    zeiger = _LIB.tjGetScalingFactors(ctypes.byref(anzahl))
    if not zeiger or anzahl.value <= 0:
        return [(1, 1)]
    stufen = []
    for i in range(anzahl.value):
        s = zeiger[i]
        if s.denom > 0 and s.num > 0:
            stufen.append((s.num, s.denom))
    return stufen or [(1, 1)]


def _beste_stufe(breite, hoehe, ziel_b, ziel_h):
    """Kleinste Stufe, deren Ergebnis das Ziel noch VOLL abdeckt.

    Nie unter die Zielgroesse - sonst muesste hinterher wieder
    hochskaliert werden, und aus einer Ersparnis wuerde sichtbarer
    Matsch.

    Und nie DARUEBER: TurboJPEG kennt auch Stufen groesser als 1 (bis
    2/1). Ein Ziel von 1000x1000 lieferte sonst aus einem 600x800-Bild
    ein 1050x1400 grosses - mehr Arbeit als das Original, ohne ein
    einziges zusaetzliches Bilddetail. Beim ersten Versuch ist genau
    das passiert."""
    beste = (1, 1)
    beste_pixel = None
    for num, denom in _stufen():
        if num > denom:
            continue          # Vergroessern bringt nichts als Aufwand
        # Dieselbe Rechnung wie TJSCALED() in turbojpeg.h.
        b = (breite * num + denom - 1) // denom
        h = (hoehe * num + denom - 1) // denom
        if b < ziel_b or h < ziel_h:
            continue
        if beste_pixel is None or b * h < beste_pixel:
            beste, beste_pixel = (num, denom), b * h
    return beste


def masse(data):
    """(breite, hoehe) ohne das Bild zu dekodieren, sonst None.

    Nuetzlich, um zu entscheiden, ob sich das Dekodieren ueberhaupt
    lohnt, bevor man die Arbeit anfaengt."""
    if _LIB is None or not data:
        return None
    griff = None
    try:
        griff = _LIB.tjInitDecompress()
        if not griff:
            return None
        b = ctypes.c_int(0)
        h = ctypes.c_int(0)
        unter = ctypes.c_int(0)
        farbraum = ctypes.c_int(0)
        if _LIB.tjDecompressHeader3(
                griff, data, len(data), ctypes.byref(b), ctypes.byref(h),
                ctypes.byref(unter), ctypes.byref(farbraum)) != 0:
            return None
        if not (0 < b.value <= TJ_MAX_KANTE and 0 < h.value <= TJ_MAX_KANTE):
            return None
        return b.value, h.value
    except Exception:
        return None
    finally:
        if griff:
            try:
                _LIB.tjDestroy(griff)
            except Exception:
                pass


def decode_jpeg(data, ziel_b=0, ziel_h=0):
    """JPEG-Bytes zu (breite, hoehe, rgba_bytes), sonst None.

    ziel_b/ziel_h: gewuenschte Mindestgroesse. Ist sie angegeben,
    dekodiert die Bibliothek gleich verkleinert - das Ergebnis ist dann
    MINDESTENS so gross wie gefordert, aber so klein wie moeglich. Der
    Aufrufer skaliert danach wie gewohnt auf das genaue Mass.

    Liefert None bei JEDEM Fehler und laesst nie eine Ausnahme nach
    aussen - derselbe Vertrag wie decode_png()."""
    if _LIB is None or not data:
        return None
    griff = None
    try:
        griff = _LIB.tjInitDecompress()
        if not griff:
            return None
        b = ctypes.c_int(0)
        h = ctypes.c_int(0)
        unter = ctypes.c_int(0)
        farbraum = ctypes.c_int(0)
        if _LIB.tjDecompressHeader3(
                griff, data, len(data), ctypes.byref(b), ctypes.byref(h),
                ctypes.byref(unter), ctypes.byref(farbraum)) != 0:
            return None
        breite, hoehe = b.value, h.value
        if not (0 < breite <= TJ_MAX_KANTE and 0 < hoehe <= TJ_MAX_KANTE):
            return None
        if breite * hoehe > TJ_MAX_PIXEL:
            return None

        if ziel_b > 0 and ziel_h > 0:
            num, denom = _beste_stufe(breite, hoehe, ziel_b, ziel_h)
            breite = (breite * num + denom - 1) // denom
            hoehe = (hoehe * num + denom - 1) // denom

        # Mit 0xFF vorgefuellt: TJPF_BGRX schreibt nur die ersten drei
        # Bytes je Bildpunkt, das vierte bleibt stehen - und ist damit
        # ohne weiteren Durchlauf die volle Deckkraft.
        puffer = ctypes.create_string_buffer(b"\xff" * (breite * hoehe * 4))
        if _LIB.tjDecompress2(griff, data, len(data), puffer,
                              breite, breite * 4, hoehe, TJPF_BGRX, 0) != 0:
            return None
        return breite, hoehe, puffer.raw[:breite * hoehe * 4]
    except Exception:
        return None
    finally:
        if griff:
            try:
                _LIB.tjDestroy(griff)
            except Exception:
                pass


def datei_lesen(pfad, ziel_b=0, ziel_h=0):
    """decode_jpeg() fuer einen Dateipfad. None, wenn irgendetwas daran
    nicht klappt - fehlende Datei eingeschlossen."""
    try:
        if not os.path.isfile(pfad):
            return None
        with open(pfad, "rb") as fh:
            return decode_jpeg(fh.read(), ziel_b, ziel_h)
    except OSError:
        return None


# ---------------------------------------------------------------------------
# PNG ueber libpng
#
# Benutzt wird die "vereinfachte" Schnittstelle von libpng 1.6
# (png_image_begin_read_from_memory / png_image_finish_read). Das ist
# fuer libpng dasselbe, was TurboJPEG fuer libjpeg ist: die klassische
# Schnittstelle verlangt setjmp/longjmp fuer die Fehlerbehandlung -
# aus Python heraus schlicht nicht machbar - und einen Haufen
# Rueckruffunktionen. Die vereinfachte meldet Fehler als Rueckgabewert
# 0 und schreibt den Grund in ein Textfeld.
#
# png_image ist dabei eine OFFENGELEGTE Struktur mit garantierter
# Reihenfolge (png.h), im Gegensatz zu den undurchsichtigen
# png_struct/png_info. Sie hier nachzubauen ist deshalb zulaessig und
# nicht dieselbe Wette wie bei jpeg_decompress_struct.
# ---------------------------------------------------------------------------

PNG_IMAGE_VERSION = 1
# Die Flags aus png.h, damit der Wert nachvollziehbar ist statt geraten:
#
#   PNG_FORMAT_FLAG_ALPHA  0x01
#   PNG_FORMAT_FLAG_COLOR  0x02
#   PNG_FORMAT_FLAG_BGR    0x10
#
# BUGFIX (Build 126): hier stand PNG_FORMAT_RGBA = 0x03. Der
# Bildspeicher des MiSTer ist BGRA - siehe die ausfuehrliche
# Begruendung bei TJPF_BGRX oben, es ist derselbe Fehler.
PNG_FORMAT_BGRA = 0x13      # FLAG_COLOR | FLAG_ALPHA | FLAG_BGR
PNG_MAX_PIXEL = 16_000_000

_PNG_KANDIDATEN = (
    "libpng16.so.16",
    "libpng16.so",
    "libpng.so",
    "/lib/libpng16.so.16",
    "/usr/lib/libpng16.so.16",
)


class _PngBild(ctypes.Structure):
    """png_image aus png.h - Reihenfolge und Typen sind Teil der
    oeffentlichen Schnittstelle von libpng 1.6."""
    _fields_ = [
        ("opaque", ctypes.c_void_p),
        ("version", ctypes.c_uint32),
        ("width", ctypes.c_uint32),
        ("height", ctypes.c_uint32),
        ("format", ctypes.c_uint32),
        ("flags", ctypes.c_uint32),
        ("colormap_entries", ctypes.c_uint32),
        ("warning_or_error", ctypes.c_uint32),
        ("message", ctypes.c_char * 64),
    ]


def _png_laden():
    for name in _PNG_KANDIDATEN:
        try:
            lib = ctypes.CDLL(name)
        except OSError:
            continue
        try:
            lib.png_image_begin_read_from_memory.restype = ctypes.c_int
            lib.png_image_begin_read_from_memory.argtypes = [
                ctypes.POINTER(_PngBild), ctypes.c_char_p, ctypes.c_size_t]
            lib.png_image_finish_read.restype = ctypes.c_int
            lib.png_image_finish_read.argtypes = [
                ctypes.POINTER(_PngBild), ctypes.c_void_p, ctypes.c_void_p,
                ctypes.c_int32, ctypes.c_void_p]
            lib.png_image_free.argtypes = [ctypes.POINTER(_PngBild)]
        except AttributeError:
            continue
        return lib
    return None


_PNG = _png_laden()


def png_verfuegbar():
    return _PNG is not None


def decode_png_lib(data):
    """PNG-Bytes zu (breite, hoehe, rgba_bytes), sonst None.

    Bewusst dieselbe Signatur und derselbe Vertrag wie decode_png() in
    fe/art.py - damit ist der eine der Rueckfall des anderen, ohne dass
    ein Aufrufer den Unterschied merkt."""
    if _PNG is None or not data:
        return None
    bild = _PngBild()
    try:
        ctypes.memset(ctypes.byref(bild), 0, ctypes.sizeof(bild))
        bild.version = PNG_IMAGE_VERSION
        if _PNG.png_image_begin_read_from_memory(
                ctypes.byref(bild), data, len(data)) == 0:
            return None
        breite, hoehe = int(bild.width), int(bild.height)
        if breite <= 0 or hoehe <= 0 or breite * hoehe > PNG_MAX_PIXEL:
            _PNG.png_image_free(ctypes.byref(bild))
            return None
        bild.format = PNG_FORMAT_BGRA
        puffer = ctypes.create_string_buffer(breite * hoehe * 4)
        ok = _PNG.png_image_finish_read(ctypes.byref(bild), None, puffer,
                                        breite * 4, None)
        # png_image_finish_read() raeumt bei Erfolg selbst auf, bei
        # einem Fehler nicht - free() ist in beiden Faellen erlaubt und
        # beim zweiten Mal wirkungslos.
        _PNG.png_image_free(ctypes.byref(bild))
        if not ok:
            return None
        return breite, hoehe, puffer.raw[:breite * hoehe * 4]
    except Exception:
        try:
            _PNG.png_image_free(ctypes.byref(bild))
        except Exception:
            pass
        return None


# ---------------------------------------------------------------------------
# Gemeinsamer Eingang
# ---------------------------------------------------------------------------

def format_erkennen(data):
    """"png", "jpeg" oder None - am Dateikopf, nicht an der Endung.

    Die Endung ist das, was jemand hingeschrieben hat; der Kopf ist,
    was wirklich drinsteht."""
    if not data:
        return None
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if data[:2] == b"\xff\xd8":
        return "jpeg"
    return None


def decode(data, ziel_b=0, ziel_h=0):
    """Beliebiges unterstuetztes Bild zu (breite, hoehe, rgba) oder
    None. ziel_b/ziel_h wirken nur bei JPEG (dort kann die Bibliothek
    gleich verkleinert dekodieren); PNG kennt das nicht."""
    art = format_erkennen(data)
    if art == "png":
        return decode_png_lib(data)
    if art == "jpeg":
        return decode_jpeg(data, ziel_b, ziel_h)
    return None
