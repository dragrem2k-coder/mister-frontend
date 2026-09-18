#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Der Rechenkern des PC-Werkzeugs - Miniaturen im Format des Frontends.

ACHTUNG, WICHTIGSTE REGEL DIESER DATEI:

    Die drei Funktionen zielmass(), verkleinern_flaechenmittel() und
    hochskalieren() sind WORTGLEICHE KOPIEN aus frontend/fe/art.py.

Sie muessen es bleiben. Der Miniaturen-Cache verlangt, dass eine
gespeicherte Miniatur bit-identisch zu einer frisch berechneten ist -
laufen die beiden Fassungen auseinander, legt der PC Bilder ab, die
sich vom Ergebnis des MiSTer unterscheiden, und niemand merkt es, weil
beide Seiten fuer sich genommen richtig aussehen.

Deshalb gibt es tools/test_pc_kern.py: der Test rechnet dieselben
Zufallsbilder einmal hier und einmal in fe/art.py durch und vergleicht
Byte fuer Byte. Wer hier etwas aendert, ohne dort etwas zu aendern (oder
umgekehrt), bekommt einen roten Test.

Was hier BEWUSST anders ist als auf dem MiSTer: JPEG-Quellen werden in
voller Aufloesung dekodiert. Der MiSTer laesst TurboJPEG verkleinert
dekodieren (1/2, 1/4, 1/8), weil ihm sonst die Rechenzeit davonlaeuft.
Die ZIELGROESSE ist in beiden Faellen dieselbe - sie kommt aus
zielmass() und den echten Dateimassen -, nur die Bildpunkte, ueber die
gemittelt wird, sind auf dem PC die feineren. Das Ergebnis ist also
nicht schlechter, sondern minimal besser; es ist nur nicht bitgleich.
Auf den Cache-Schluessel hat das keinen Einfluss.
"""
import io
import operator
import struct
import zlib

# Muss zu THUMB_ALGO_VERSION in fe/art.py passen. Der Auftrag vom
# MiSTer traegt die Nummer mit; weichen sie ab, bricht das Werkzeug ab,
# statt Miniaturen abzulegen, die niemand findet.
THUMB_ALGO_VERSION = "3"

_addiere = operator.add
_ganzzahlig = operator.floordiv


# --------------------------------------------------------------------------
# WORTGLEICHE KOPIEN AUS fe/art.py - siehe Kopfkommentar
# --------------------------------------------------------------------------
def zielmass(nw, nh, max_w, max_h):
    """Auf welche Groesse ein Bild von nw x nh in einem Kasten von
    max_w x max_h landet - oder None, wenn es hineinpasst und
    stattdessen ganzzahlig VERGROESSERT wird."""
    if nw <= max_w and nh <= max_h:
        return None
    sc = min(max_w / float(nw), max_h / float(nh))
    return max(1, int(nw * sc)), max(1, int(nh * sc))


def verkleinern_flaechenmittel(pix, w, h, tw, th):
    """Bild auf tw x th verkleinern (Kastenfilter)."""
    if tw <= 0 or th <= 0 or w <= 0 or h <= 0:
        return None
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


def hochskalieren(pix, w, h, scale):
    """Ganzzahliges Vergroessern (Nearest-Neighbor).
    Rueckgabe: (breite, hoehe, bytearray)."""
    sw, sh = w * scale, h * scale
    out = bytearray(sw * sh * 4)
    row_out = sw * 4
    for y in range(h):
        src_row = pix[y * w * 4:(y + 1) * w * 4]
        zeile = b"".join([src_row[x * 4:x * 4 + 4] * scale
                          for x in range(w)])
        basis = y * scale * row_out
        for k in range(scale):
            out[basis + k * row_out:basis + (k + 1) * row_out] = zeile
    return sw, sh, out


# --------------------------------------------------------------------------
# Dateiformat des Zwischenspeichers
# --------------------------------------------------------------------------
MARKE_ORIGINAL_PASST = b"ARTO" + struct.pack("<HH", 0, 0)


def art_bytes(tw, th, pix):
    """Der Inhalt einer .art-Datei: Kennung, Masse, gepackte Bildpunkte."""
    return b"ART1" + struct.pack("<HH", tw, th) + zlib.compress(pix, 6)


def cache_pfad(cache_basis, hd, key):
    """<cache>/<hd|sd>/<zwei Zeichen>/<schluessel>.art"""
    return "%s/%s/%s/%s.art" % (cache_basis, "hd" if hd else "sd",
                                key[:2], key)


# --------------------------------------------------------------------------
# Bild lesen
# --------------------------------------------------------------------------
def bild_lesen(daten):
    """Bilddaten zu (breite, hoehe, BGRA-Bytes).

    Der Bildspeicher des MiSTer ist BGRA, Pillow liefert RGBA - die
    beiden aeusseren Kanaele muessen also getauscht werden. Genau das
    hat auf dem Geraet einmal gefehlt (Build 126, "Rot und Blau
    vertauscht"), und es ist nicht zu sehen, solange man nur seine
    eigenen Bilder anschaut: ein blaustichiges Cover sieht aus wie ein
    blaustichiges Cover."""
    from PIL import Image
    img = Image.open(io.BytesIO(daten))
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    w, h = img.size
    r, g, b, a = img.split()
    return w, h, Image.merge("RGBA", (b, g, r, a)).tobytes()


def miniatur_bauen(w, h, pix, max_w, max_h):
    """Eine Miniatur fuer einen Kasten - dieselbe Fallunterscheidung wie
    _prewarm_aus_gelesenem() in fe/art.py.

    Rueckgabe: fertige Dateibytes (.art), oder None bei einem Fehler.
    """
    if w <= 0 or h <= 0:
        return None
    if w <= max_w and h <= max_h:
        scale = max(1, min(max_w // w, max_h // h, 10))
        if scale == 1:
            # Das Original passt unveraendert - auf der Karte steht dann
            # nur eine acht Byte grosse Marke statt einer Kopie.
            return MARKE_ORIGINAL_PASST
        sw, sh, out = hochskalieren(pix, w, h, scale)
        return art_bytes(sw, sh, bytes(out))
    ziel = zielmass(w, h, max_w, max_h)
    if not ziel:
        return None
    tw, th = ziel
    data = verkleinern_flaechenmittel(pix, w, h, tw, th)
    if data is None:
        return None
    return art_bytes(tw, th, data)
