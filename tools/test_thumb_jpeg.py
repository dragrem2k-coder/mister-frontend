#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Miniaturen als JPEG - aber nur dort, wo es etwas holt (Build 201).

DER ANLASS, aus einem DRAGEND_PROFILE-Lauf des Nutzers auf dem Geraet.
Ein Ordner zu oeffnen kostete 241 ms:

    _draw_page_items_impl        241 ms
      draw_art_panel             197 ms
        get_scaled               136 ms
          _thumb_cache_get       132 ms
            3x read()             66 ms
            zlib.decompress       64 ms

Das ganze Oeffnen war das Cover. Und im Kommentar bei
_thumb_cache_get() stand die Annahme, die das gedeckt hat: eine
Cache-Datei zu lesen koste 5.9 ms. Das war korrekt gemessen - bei der
damaligen Kastengroesse. Auf 1080p sind 132 ms daraus geworden.

WARUM NICHT ALLES AUF JPEG: die eigene Messtabelle im Cache-Code
widerspricht.

    fotoaehnlich (Boxart)  zlib Stufe 1: 10.1 ms / 373 KB
    flaechig (ein Logo)    zlib Stufe 1:  0.7 ms /   2.5 KB

Beim Logo holt JPEG nichts, macht die Datei groesser UND setzt Ringing
an harte Kanten. Entschieden wird deshalb nach der gepackten Groesse.

WAS DIESER TEST ABSICHERT

  - dass ein Foto als JPG landet und ein flaechiges Bild BITGENAU als
    ART1 bleibt,
  - dass der Rundlauf die Masse exakt erhaelt (ein falsch grosses Bild
    im Zeichenweg waere schlimmer als ein langsames),
  - dass alte ART1-Dateien weiter gelesen werden - es muss nichts neu
    aufgebaut werden,
  - dass das Nachziehen NEBENHER laeuft und nicht im Zeichenweg,
  - dass eine kaputte oder halbe Datei None liefert und nie eine
    Ausnahme,
  - dass ohne libjpeg alles beim Alten bleibt,
  - und dass es wirklich schneller ist.

Ausfuehren:
    python3 tools/test_thumb_jpeg.py
"""
import io
import os
import shutil
import struct
import sys
import tempfile
import time
import zlib

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
sys.path.insert(0, _HIER)

import _harness as H                                     # noqa: E402

sys.path.insert(0, os.path.join(_REPO, "frontend"))
import fe.art as A                                       # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


TW, TH = 320, 420


def foto(tw=TW, th=TH):
    """Ein ECHTES Abzeichen aus diesem Repo, auf Kastengroesse gebracht.

    Beim ersten Anlauf stand hier ein erzeugtes Muster
    ((x*211 + y*97) % 256) - hochfrequentes Rauschen, der schlechteste
    Fall fuer JPEG und etwas, das kein Cover der Welt so aussieht. Der
    Test hat daraus "JPEG bringt nur Faktor 1,1" gemeldet, und das waere
    die falsche Schlussfolgerung aus einem falschen Bild gewesen. Jetzt
    kommt das Material aus dem Repo: gepackt 111 KB, also genau die
    Sorte, um die es geht."""
    import glob
    p = sorted(glob.glob(os.path.join(_REPO, "frontend", "sysart", "*.art")))
    d = io.open(p[0], "rb").read()
    aw, ah = struct.unpack("<HH", d[4:8])
    pix = zlib.decompress(d[8:])
    if (aw, ah) == (tw, th):
        return pix
    # Auf das gewuenschte Mass bringen, ohne Skalierer: zuschneiden oder
    # wiederholen. Der Inhalt bleibt echtes Bildmaterial.
    zeile_aus = tw * 4
    raus = bytearray(tw * th * 4)
    for y in range(th):
        qy = y % ah
        for x in range(0, tw, aw):
            breite = min(aw, tw - x)
            raus[y * zeile_aus + x * 4:y * zeile_aus + (x + breite) * 4] = \
                pix[qy * aw * 4:qy * aw * 4 + breite * 4]
    return bytes(raus)


def rauschen(tw=TW, th=TH):
    """Der GRENZFALL: ein Bild, das sich nicht packen laesst. Dort ist
    JPEG beim Auspacken sogar minimal langsamer und spart nur ein
    Drittel der Datei - gemessen 363 KB zlib gegen 253 KB JPEG. Der Test
    haelt das fest, damit niemand spaeter einen Faktor erwartet, den es
    nur bei gutartigem Material gibt."""
    raus = bytearray(tw * th * 4)
    i = 0
    for y in range(th):
        for x in range(tw):
            raus[i] = (x * 211 + y * 97) % 256
            raus[i + 1] = (x * 37 + y * 173) % 256
            raus[i + 2] = (x * 131 + y * 17) % 256
            raus[i + 3] = 255
            i += 4
    return bytes(raus)


def flaechig(tw=TW, th=TH):
    """Etwas Flaechiges: ein Logo auf einfarbigem Grund."""
    raus = bytearray(b"\x20\x30\x40\xff" * (tw * th))
    for y in range(th // 3, 2 * th // 3):
        for x in range(tw // 4, 3 * tw // 4):
            i = (y * tw + x) * 4
            raus[i:i + 4] = b"\xf0\xe0\x10\xff"
    return bytes(raus)


def aufbau():
    """Ein frischer Cache in einem temporaeren Ordner."""
    basis = tempfile.mkdtemp(prefix="dragend_thumbjpg_")
    A.THUMB_CACHE_DIR = os.path.join(basis, "hd")
    os.makedirs(A.THUMB_CACHE_DIR, exist_ok=True)
    quelle = os.path.join(basis, "Cover.png")
    io.open(quelle, "wb").write(b"\x89PNG" + b"\x00" * 64)
    A._jpg_nachgezogen.clear()
    return basis, quelle


def dateibytes(quelle):
    p = A._thumb_cache_path(A._thumb_cache_key(quelle, TW, TH))
    return io.open(p, "rb").read()


print("Test 1: ein Foto landet als JPG, ein Logo bleibt verlustfrei")
# ---------------------------------------------------------------------------
basis, quelle = aufbau()
try:
    pix = foto()
    gepackt = len(zlib.compress(pix, A.THUMB_PACKSTUFE))
    check("der Testfall ist wirklich fotoaehnlich (gepackt ueber der "
          "Schwelle)", gepackt >= A.THUMB_JPEG_AB_BYTES,
          "%d KB gepackt, Schwelle %d KB"
          % (gepackt // 1024, A.THUMB_JPEG_AB_BYTES // 1024))
    A._thumb_cache_put(quelle, TW, TH, TW, TH, pix)
    roh = dateibytes(quelle)
    check("es steht als JPG in der Datei", roh[:4] == A._KOPF_JPG, roh[:4])
    check("und sie ist deutlich kleiner als die gepackte Fassung",
          len(roh) * 2 < gepackt,
          "%d KB statt %d KB" % (len(roh) // 1024, gepackt // 1024))

    erg = A._thumb_cache_get(quelle, TW, TH)
    check("sie wird wieder gelesen", erg is not None)
    if erg:
        gw, gh, gpix = erg
        check("die Masse stimmen exakt", (gw, gh) == (TW, TH), (gw, gh))
        check("und die Byte-Zahl auch", len(gpix) == TW * TH * 4,
              len(gpix))
        # Verlustbehaftet, also kein Bitvergleich - aber der Fehler muss
        # klein sein, sonst waere das Bild sichtbar schlechter.
        _n = min(len(gpix), len(pix))
        _abw = [abs(gpix[i] - pix[i]) for i in range(0, _n, 4 * 97)]
        _mittel = sum(_abw) / max(1, len(_abw))
        check("der Farbfehler ist klein", _mittel < 12,
              "mittlere Abweichung %.1f von 255" % _mittel)
        check("und das Alpha-Byte ist voll (JPEG kennt keines, der "
              "Zeichenweg liest es nicht)",
              all(gpix[i] == 255 for i in range(3, min(_n, 4000), 4)))
finally:
    shutil.rmtree(basis, ignore_errors=True)

print()
print("Test 2: flaechig bleibt ART1 - und BITGENAU")
# ---------------------------------------------------------------------------
basis, quelle = aufbau()
try:
    pix = flaechig()
    gepackt = len(zlib.compress(pix, A.THUMB_PACKSTUFE))
    check("der Testfall ist wirklich flaechig (gepackt winzig)",
          gepackt < A.THUMB_JPEG_AB_BYTES,
          "%d Byte gepackt" % gepackt)
    A._thumb_cache_put(quelle, TW, TH, TW, TH, pix)
    roh = dateibytes(quelle)
    check("es bleibt ART1", roh[:4] == A._KOPF_ART, roh[:4])
    erg = A._thumb_cache_get(quelle, TW, TH)
    check("und kommt BITGENAU zurueck", erg is not None and erg[2] == pix,
          "ein Logo darf kein Ringing bekommen")
finally:
    shutil.rmtree(basis, ignore_errors=True)

print()
print("Test 3: alte ART1-Dateien bleiben gueltig und werden nachgezogen")
# ---------------------------------------------------------------------------
# Das ist die Zusage an den Bestand: 97.000 Eintraege muessen NICHT neu
# aufgebaut werden.
basis, quelle = aufbau()
try:
    pix = foto()
    cpath = A._thumb_cache_path(A._thumb_cache_key(quelle, TW, TH))
    os.makedirs(os.path.dirname(cpath), exist_ok=True)
    io.open(cpath, "wb").write(A._KOPF_ART + struct.pack("<HH", TW, TH)
                               + zlib.compress(pix, A.THUMB_PACKSTUFE))
    gerufen = []
    _echt = A._thumb_cache_put_async
    A._thumb_cache_put_async = lambda *a: gerufen.append(a)
    try:
        erg = A._thumb_cache_get(quelle, TW, TH)
    finally:
        A._thumb_cache_put_async = _echt
    check("die alte Datei wird gelesen", erg is not None and erg[2] == pix,
          "und zwar bitgenau, sie ist ja verlustfrei")
    check("das Nachziehen laeuft NEBENHER, nicht im Zeichenweg",
          len(gerufen) == 1,
          "%d Aufrufe von _thumb_cache_put_async" % len(gerufen))

    # Zweites Lesen darf nicht erneut anmelden - sonst wuerde ein
    # fehlgeschlagenes Nachziehen bei jedem Bild neu versucht.
    del gerufen[:]
    A._thumb_cache_put_async = lambda *a: gerufen.append(a)
    try:
        A._thumb_cache_get(quelle, TW, TH)
    finally:
        A._thumb_cache_put_async = _echt
    check("und nur einmal je Eintrag", not gerufen, gerufen)
finally:
    shutil.rmtree(basis, ignore_errors=True)

print()
print("Test 4: ein flaechiges ART1 wird NICHT angefasst")
# ---------------------------------------------------------------------------
basis, quelle = aufbau()
try:
    pix = flaechig()
    cpath = A._thumb_cache_path(A._thumb_cache_key(quelle, TW, TH))
    os.makedirs(os.path.dirname(cpath), exist_ok=True)
    io.open(cpath, "wb").write(A._KOPF_ART + struct.pack("<HH", TW, TH)
                               + zlib.compress(pix, A.THUMB_PACKSTUFE))
    gerufen = []
    _echt = A._thumb_cache_put_async
    A._thumb_cache_put_async = lambda *a: gerufen.append(a)
    try:
        A._thumb_cache_get(quelle, TW, TH)
    finally:
        A._thumb_cache_put_async = _echt
    check("kein Nachziehen - dort ist nichts zu holen", not gerufen,
          gerufen)
finally:
    shutil.rmtree(basis, ignore_errors=True)

print()
print("Test 5: kaputte Dateien liefern None, nie eine Ausnahme")
# ---------------------------------------------------------------------------
basis, quelle = aufbau()
try:
    cpath = A._thumb_cache_path(A._thumb_cache_key(quelle, TW, TH))
    os.makedirs(os.path.dirname(cpath), exist_ok=True)
    faelle = [
        ("leer", b""),
        ("zu kurz", b"JPG"),
        ("nur Kopf", A._KOPF_JPG),
        ("fremder Kopf", b"XXXX" + struct.pack("<HH", TW, TH) + b"abc"),
        ("JPG-Kopf, Muell dahinter",
         A._KOPF_JPG + struct.pack("<HH", TW, TH) + b"\x00" * 500),
        ("halbes JPG", A._KOPF_JPG + struct.pack("<HH", TW, TH)
         + (A._jpeg_packen(TW, TH, foto()) or b"")[:400]),
        ("ART1 mit Muell", A._KOPF_ART + struct.pack("<HH", TW, TH)
         + b"\x01\x02\x03"),
        ("ART1, falsche Masse", A._KOPF_ART + struct.pack("<HH", 7, 7)
         + zlib.compress(foto(), 1)),
    ]
    for name, daten in faelle:
        io.open(cpath, "wb").write(daten)
        try:
            erg = A._thumb_cache_get(quelle, TW, TH)
            ok = erg is None
            fehler = ""
        except Exception as e:                           # noqa: BLE001
            ok, fehler = False, repr(e)
        check("%-26s -> None" % name, ok, fehler)
finally:
    shutil.rmtree(basis, ignore_errors=True)

print()
print("Test 6: die Marke 'Original passt' funktioniert weiter")
# ---------------------------------------------------------------------------
basis, quelle = aufbau()
try:
    A._thumb_cache_put_marke(quelle, TW, TH)
    check("sie wird als solche erkannt",
          A._thumb_cache_get(quelle, TW, TH) is A.ORIGINAL_PASST,
          "sonst waere Build 128 zur Haelfte zurueck")
finally:
    shutil.rmtree(basis, ignore_errors=True)

print()
print("Test 7: ohne libjpeg bleibt alles beim Alten")
# ---------------------------------------------------------------------------
basis, quelle = aufbau()
try:
    _echt = A._jpeg_packen
    A._jpeg_packen = lambda *a, **k: None
    try:
        pix = foto()
        A._thumb_cache_put(quelle, TW, TH, TW, TH, pix)
        roh = dateibytes(quelle)
        check("geschrieben wird ART1", roh[:4] == A._KOPF_ART, roh[:4])
        erg = A._thumb_cache_get(quelle, TW, TH)
        check("und bitgenau gelesen", erg is not None and erg[2] == pix)
    finally:
        A._jpeg_packen = _echt
finally:
    shutil.rmtree(basis, ignore_errors=True)

print()
print("Test 8: EIN read() statt drei")
# ---------------------------------------------------------------------------
quelle_art = io.open(os.path.join(_REPO, "frontend", "fe", "art.py"),
                     encoding="utf-8").read()
_blk = quelle_art[quelle_art.index("def _thumb_cache_get("):]
_blk = _blk[:_blk.index("\ndef ", 10)]
check("die Datei wird in einem Zug gelesen",
      _blk.count("f.read()") == 1 and "f.read(4)" not in _blk,
      "im Profil standen 3 x read() mit zusammen 66 ms")

print()
print("Test 9: und es ist wirklich schneller")
# ---------------------------------------------------------------------------
basis, quelle = aufbau()
try:
    pix = foto()

    def zeit(fn, runden=7):
        for _ in range(2):
            fn()
        best = None
        for _ in range(runden):
            t0 = time.perf_counter()
            fn()
            d = (time.perf_counter() - t0) * 1000
            best = d if best is None or d < best else best
        return best

    A._thumb_cache_put(quelle, TW, TH, TW, TH, pix)
    t_jpg = zeit(lambda: A._thumb_cache_get(quelle, TW, TH))
    jpg_bytes = len(dateibytes(quelle))

    cpath = A._thumb_cache_path(A._thumb_cache_key(quelle, TW, TH))
    io.open(cpath, "wb").write(A._KOPF_ART + struct.pack("<HH", TW, TH)
                               + zlib.compress(pix, A.THUMB_PACKSTUFE))
    A._jpg_nachgezogen.clear()
    _echt = A._thumb_cache_put_async
    A._thumb_cache_put_async = lambda *a: None
    try:
        t_art = zeit(lambda: A._thumb_cache_get(quelle, TW, TH))
    finally:
        A._thumb_cache_put_async = _echt
    art_bytes = len(dateibytes(quelle))

    print("       ART1: %.2f ms, %d KB" % (t_art, art_bytes // 1024))
    print("       JPG1: %.2f ms, %d KB" % (t_jpg, jpg_bytes // 1024))
    check("JPG ist schneller zu lesen", t_jpg < t_art,
          "Faktor %.1f" % (t_art / t_jpg if t_jpg else 0))
    check("und die Datei deutlich kleiner", jpg_bytes * 2 < art_bytes,
          "%d gegen %d KB" % (jpg_bytes // 1024, art_bytes // 1024))
finally:
    shutil.rmtree(basis, ignore_errors=True)

print()
print("Test 10: DER GRENZFALL - ein Bild, das sich nicht packen laesst")
# ---------------------------------------------------------------------------
# Hier ist JPEG beim AUSPACKEN sogar minimal langsamer (gemessen 3.31
# gegen 3.10 ms) und spart nur ein Drittel der Datei. Trotzdem lohnt es,
# und der Grund steht im Profil des Nutzers: dort kostete das LESEN der
# Datei 66 ms und das Auspacken 64 - auf der SD-Karte entscheidet die
# Dateigroesse, nicht die Rechenzeit. Der Test haelt das fest, damit
# niemand spaeter einen Faktor erwartet, den es nur bei gutartigem
# Material gibt.
basis, quelle = aufbau()
try:
    pix = rauschen()
    gepackt = len(zlib.compress(pix, A.THUMB_PACKSTUFE))
    A._thumb_cache_put(quelle, TW, TH, TW, TH, pix)
    roh = dateibytes(quelle)
    # Und genau deshalb bleibt es hier VERLUSTFREI: die Entscheidung
    # haengt nicht nur an der Groesse der gepackten Fassung, sondern
    # daran, ob JPEG wenigstens die Haelfte spart. Hier spart es 3 von
    # 363 KB - also bleibt ART1, lossless und beim Auspacken schneller.
    check("es bleibt verlustfrei bei ART1", roh[:4] == A._KOPF_ART,
          "gepackt %d KB, JPEG haette dort fast nichts gespart"
          % (gepackt // 1024))
    erg = A._thumb_cache_get(quelle, TW, TH)
    check("und sie wird korrekt gelesen",
          erg is not None and (erg[0], erg[1]) == (TW, TH)
          and len(erg[2]) == TW * TH * 4)
finally:
    shutil.rmtree(basis, ignore_errors=True)

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
