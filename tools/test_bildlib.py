#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft die Systembibliotheken fuer Bilder und die fremde Quelle
unter /media/fat/docs (Build 115).

WORUM ES GEHT. Auf dem MiSTer liegen libpng und libturbojpeg - nur
eben weder als Python-Modul noch als Kommandozeilenwerkzeug, weshalb
mehrere Suchen daran vorbeigingen. Ueber ctypes sind sie trotzdem
erreichbar, und der Unterschied ist kein Feinschliff: unser eigener
PNG-Dekoder in Python braucht fuer ein Cover 140 ms (hier gemessen),
libpng 2,6 ms. Auf dem Geraet des Nutzers sind das 200-500 ms gegen
grob 30.

DIE ZWEI FRAGEN, DIE DIESER TEST BEANTWORTEN MUSS:

1. Liefert die Bibliothek WIRKLICH dasselbe Bild wie unser Dekoder?
   Ein Unterschied faellt nicht auf, er zeigt nur irgendwann ein
   falsches Cover. Geprueft wird deshalb bitgenau ueber alle
   Farbtypen, nicht an einem Beispielbild. Dieselbe Beweisform wie
   beim Cover-Index in Build 110.

2. Kann die Aenderung etwas VERSCHLECHTERN? Nein, und das muss so
   bleiben: fehlt die Bibliothek, uebernimmt der bisherige Dekoder
   unveraendert. Test 3 schaltet sie deshalb kuenstlich ab und prueft,
   dass trotzdem ein Bild herauskommt.

Laeuft auch auf einem Rechner OHNE diese Bibliotheken - dann werden
die betroffenen Pruefungen ausdruecklich als "nicht pruefbar" gemeldet
statt stillschweigend zu bestehen.

Ausfuehren:
    python3 tools/test_bildlib.py
"""
import base64
import io
import os
import shutil
import struct
import sys
import tempfile
import time
import zlib

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)

import _harness as H                                    # noqa: E402

sys.path.insert(0, os.path.join(_REPO, "frontend"))
import fe.art as A                                      # noqa: E402
import fe.bildlib as B                                  # noqa: E402
import fe.settings as S                                 # noqa: E402

fails = []
offen = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


def ungeprueft(label, grund):
    print("  ----  " + label + "  (" + grund + ")")
    offen.append(label)


try:
    from PIL import Image
    HAT_PIL = True
except ImportError:
    HAT_PIL = False

# Ein echtes Adam7-verschachteltes PNG, 16x16 - siehe Test 2.
PNG_VERSCHACHTELT = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAIAAAHnlligAAAAIGNIUk0AAHomAACA"
    "hAAA+gAAAIDoAAB1MAAA6mAAADqYAAAXcJy6UTwAAAAGYktHRAD/AP8A/6C9p5MA"
    "AABbSURBVCjP7Y2xDYAwDATPEkVKj/CjeBRGyWiMRuEIIYGlpKNAuuZ99hugExs9"
    "IAh0sI9khIJBzpSY8JsJXaYOhly8kFv+ZF2Y04of8qLqi8Lw5iyQTW2e/2CGE0u+"
    "GqKDvW2yAAAAAElFTkSuQmCC")


def testbild(mode="RGB", w=120, h=90):
    im = Image.new(mode, (w, h))
    q = im.load()
    for y in range(h):
        for x in range(w):
            if mode == "RGB":
                q[x, y] = ((x * 2) % 256, (y * 3) % 256, (x + y) % 256)
            elif mode == "RGBA":
                q[x, y] = ((x * 2) % 256, (y * 3) % 256, (x + y) % 256,
                           255 if (x + y) % 7 else 40)
            elif mode == "L":
                q[x, y] = (x * y) % 256
    return im


def als_png(im, **kw):
    b = io.BytesIO()
    im.save(b, "PNG", **kw)
    return b.getvalue()


def als_jpg(im, **kw):
    b = io.BytesIO()
    im.convert("RGB").save(b, "JPEG", **kw)
    return b.getvalue()


print("Test 1: was dieses Geraet ueberhaupt kann")
print("  libpng      :", "ja" if B.png_verfuegbar() else "nein")
print("  TurboJPEG   :", "ja" if B.verfuegbar() else "nein")
print("  Pillow (Test):", "ja" if HAT_PIL else "nein")
check("fe/art.py haelt die Bibliothek genau dann fuer nutzbar, "
      "wenn eine da ist",
      (A._BILDLIB is not None)
      == (B.png_verfuegbar() or B.verfuegbar()))

print()
print("Test 2: libpng liefert bitgenau dasselbe wie unser Dekoder")
if not (HAT_PIL and B.png_verfuegbar()):
    ungeprueft("Vergleich aller Farbtypen",
               "Pillow oder libpng fehlt auf diesem Rechner")
else:
    quelle = testbild("RGB")
    faelle = [
        ("RGB 8 Bit", als_png(quelle)),
        ("RGBA 8 Bit", als_png(testbild("RGBA"))),
        ("Graustufen", als_png(testbild("L"))),
        ("Palette", als_png(quelle.convert(
            "P", palette=Image.ADAPTIVE, colors=200))),
    ]
    for name, daten in faelle:
        unser = A._decode_png_python(daten)
        lib = B.decode_png_lib(daten)
        check("%-12s bitgleich" % name,
              unser is not None and unser == lib,
              "unser=%s lib=%s" % (unser[:2] if unser else None,
                                   lib[:2] if lib else None))
    # Der umgekehrte Fall: etwas, das NUR die Bibliothek kann. Ohne
    # diese Pruefung waere "gleichwertig" die halbe Wahrheit.
    #
    # Das Bild steht hier als Konstante, weil Pillow kein
    # verschachteltes PNG schreiben kann und der Test sich nicht von
    # einem zufaellig installierten ImageMagick abhaengig machen soll.
    # 16x16, Adam7, mit dem Werkzeug erzeugt und geprueft.
    check("das Testbild ist wirklich verschachtelt",
          struct.unpack(">IIBBBBB", PNG_VERSCHACHTELT[16:29])[6] == 1)
    check("interlaced PNG: unserer kann es nicht",
          A._decode_png_python(PNG_VERSCHACHTELT) is None)
    lib = B.decode_png_lib(PNG_VERSCHACHTELT)
    check("libpng liefert es trotzdem",
          lib is not None and lib[:2] == (16, 16),
          "%r" % (lib[:2] if lib else None,))

print()
print("Test 3: ohne Bibliothek laeuft alles wie vorher")
# Die wichtigste Zusage der ganzen Aenderung. Ein Geraet ohne libpng
# darf nichts davon merken.
if not HAT_PIL:
    ungeprueft("Rueckfall auf den Python-Dekoder", "Pillow fehlt")
else:
    daten = als_png(testbild("RGB"))
    merker = A._BILDLIB
    try:
        A._BILDLIB = None
        ohne = A.decode_png(daten)
    finally:
        A._BILDLIB = merker
    mit = A.decode_png(daten)
    check("ohne Bibliothek kommt trotzdem ein Bild",
          ohne is not None and ohne[:2] == (120, 90))
    check("und es ist dasselbe wie mit Bibliothek", ohne == mit)

print()
print("Test 4: und sie ist wirklich schneller")
if not (HAT_PIL and B.png_verfuegbar()):
    ungeprueft("Geschwindigkeitsvergleich", "Pillow oder libpng fehlt")
else:
    gross = als_png(testbild("RGB", 400, 560))

    def zeit(fn, n, runden=3):
        bestes = None
        for _ in range(runden):
            t0 = time.perf_counter()
            for _ in range(n):
                fn()
            d = (time.perf_counter() - t0) / n * 1000
            bestes = d if bestes is None or d < bestes else bestes
        return bestes

    t_lib = zeit(lambda: B.decode_png_lib(gross), 20)
    t_py = zeit(lambda: A._decode_png_python(gross), 2)
    check("libpng mindestens zehnmal schneller", t_py > 10 * t_lib,
          "libpng %.2f ms, Python %.1f ms, Faktor %.0f"
          % (t_lib, t_py, t_py / t_lib if t_lib else 0))

print()
print("Test 5: JPEG - Groesse, Verkleinerung, Muell")
if not (HAT_PIL and B.verfuegbar()):
    ungeprueft("JPEG-Pruefungen", "Pillow oder TurboJPEG fehlt")
else:
    jpg = als_jpg(testbild("RGB", 600, 800), quality=90)
    check("Masse ohne Dekodieren", B.masse(jpg) == (600, 800),
          "%r" % (B.masse(jpg),))
    voll = B.decode_jpeg(jpg)
    check("voll dekodiert", voll is not None and voll[:2] == (600, 800))
    check("volle Deckkraft im vierten Byte",
          all(voll[2][i] == 255 for i in range(3, 4000, 4)))
    klein = B.decode_jpeg(jpg, 150, 200)
    check("verkleinert dekodiert", klein is not None and klein[:2] == (150, 200),
          "%r" % (klein[:2] if klein else None,))
    # Nie unter das Ziel - sonst muesste hinterher hochskaliert werden.
    for zb, zh in ((80, 100), (151, 201), (299, 399)):
        r = B.decode_jpeg(jpg, zb, zh)
        check("Ziel %dx%d wird nicht unterschritten" % (zb, zh),
              r is not None and r[0] >= zb and r[1] >= zh,
              "%r" % (r[:2] if r else None,))
    # Und nie darueber: TurboJPEG kennt auch Vergroesserungsstufen, die
    # erste Fassung ist genau da hineingelaufen.
    zu_gross = B.decode_jpeg(jpg, 5000, 5000)
    check("ein zu grosses Ziel vergroessert nicht",
          zu_gross is not None and zu_gross[:2] == (600, 800),
          "%r" % (zu_gross[:2] if zu_gross else None,))
    for name, daten in (("kein Bild", b"nur text"), ("leer", b""),
                        ("abgeschnitten", jpg[:120])):
        check("%-14s -> None" % name, B.decode_jpeg(daten) is None)

print()
print("Test 6: der Bild-Cache liest jetzt auch PNG und JPG")
# Der eigentliche Hebel: dadurch wird JEDE der acht Aufrufstellen zu
# einer, die fremdes Artwork anzeigen kann, ohne selbst angefasst zu
# werden.
if not HAT_PIL:
    ungeprueft("ArtCache liest Fremdformate", "Pillow fehlt")
else:
    tmp = tempfile.mkdtemp(prefix="bildlib_")
    try:
        p_png = os.path.join(tmp, "a.png")
        open(p_png, "wb").write(als_png(testbild("RGB", 64, 48)))
        cache = A.ArtCache()
        r = cache.get(p_png)
        check("PNG-Datei wird geladen",
              r is not None and r[:2] == (64, 48) if B.png_verfuegbar()
              else r is not None,
              "%r" % (r[:2] if r else None,))
        if B.verfuegbar():
            p_jpg = os.path.join(tmp, "b.jpg")
            open(p_jpg, "wb").write(als_jpg(testbild("RGB", 64, 48)))
            r = A.ArtCache().get(p_jpg)
            check("JPG-Datei wird geladen",
                  r is not None and r[:2] == (64, 48),
                  "%r" % (r[:2] if r else None,))
        else:
            ungeprueft("JPG-Datei wird geladen", "TurboJPEG fehlt")
        # Das eigene Format darf darunter nicht leiden.
        p_art = os.path.join(tmp, "c.art")
        roh = bytes([9, 9, 9, 255]) * (10 * 8)
        with open(p_art, "wb") as fh:
            fh.write(b"ART1" + struct.pack("<HH", 10, 8)
                     + zlib.compress(roh))
        r = A.ArtCache().get(p_art)
        check("unser .art-Format unveraendert",
              r is not None and r[:2] == (10, 8) and r[2] == roh)
        # Und eine Datei, die gar kein Bild ist, darf nichts umwerfen.
        p_muell = os.path.join(tmp, "d.png")
        open(p_muell, "wb").write(b"das ist kein PNG")
        check("Datei ohne erkennbares Bild -> None",
              A.ArtCache().get(p_muell) is None)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

print()
print("Test 7: die fremde Datenbank unter docs")
# Nachgebaut wird genau der Aufbau, der auf der Karte des Nutzers
# gefunden wurde - inklusive der Eigenheit, dass der Ordner nach dem
# CORE heisst (MegaDrive), nicht nach unserem Systemschluessel
# (Genesis).
tmp = tempfile.mkdtemp(prefix="docs_")
_alt_docs = A.DOCS_BASE
try:
    A.DOCS_BASE = tmp
    for ordner in ("SNES", "MegaDrive", "GBA"):
        os.makedirs(os.path.join(tmp, ordner, "Artwork"))
    open(os.path.join(tmp, "SNES", "Artwork",
                      "Super Mario World (USA).jpg"), "wb").write(b"x")
    open(os.path.join(tmp, "SNES", "Artwork",
                      "007 Nummeriert (USA).jpg"), "wb").write(b"x")
    open(os.path.join(tmp, "MegaDrive", "Artwork",
                      "Sonic (USA).jpg"), "wb").write(b"x")
    with open(os.path.join(tmp, "SNES", "Artwork", "gameinfo.tsv"),
              "w", encoding="utf-8") as fh:
        fh.write("#key\tname\tyear\tgenre\tdeveloper\tplayers\n")
        fh.write("Super Mario World (USA)\tSuper Mario World\t1990\t"
                 "Platformer\tNintendo EAD\t1-2\n")
        fh.write("Nur Jahr (USA)\tNur Jahr\t1993\t\t\t\n")
        fh.write("kaputte zeile ohne tabs\n")
        fh.write("\t\t\t\n")
    A.docs_caches_leeren()

    check("Ordner wird ueber den Systemschluessel gefunden",
          A.docs_cover("SNES", "Super Mario World (USA)") is not None)
    check("und ueber den Core-Namen aus unserer Systemliste",
          A.docs_cover("Genesis", "Sonic (USA)") is not None,
          "Genesis -> MegaDrive")
    check("SMW-Hacks landen beim SNES-Ordner",
          A.docs_cover("SMW_HACKS", "Super Mario World (USA)") is not None)
    check("fuehrende Nummer wird wie bei uns ignoriert",
          A.docs_cover("SNES", "Nummeriert (USA)") is not None)
    check("was es nicht gibt, gibt es nicht",
          A.docs_cover("SNES", "Gibts Nicht") is None)
    check("ohne Systemschluessel kein Treffer",
          A.docs_cover(None, "Super Mario World (USA)") is None)

    m = A.docs_meta("SNES", "Super Mario World (USA)")
    check("Spieledaten vollstaendig",
          m.get("year") == "1990" and m.get("genre") == "Platformer"
          and m.get("developer") == "Nintendo EAD"
          and m.get("players") == "1-2", "%r" % (m,))
    check("Zeile mit leeren Feldern liefert nur das Gefuellte",
          A.docs_meta("SNES", "Nur Jahr (USA)") == {"year": "1993"},
          "%r" % (A.docs_meta("SNES", "Nur Jahr (USA)"),))
    check("kaputte Zeilen werfen die Tabelle nicht um",
          A.docs_meta("SNES", "kaputte zeile ohne tabs") == {})
    check("Kopfzeile wird nicht als Spiel gelesen",
          A.docs_meta("SNES", "#key") == {})

    print()
    print("Test 8: eigenes Artwork behaelt Vorrang, der Schalter wirkt")
    eigen = tempfile.mkdtemp(prefix="eigen_")
    try:
        os.makedirs(os.path.join(eigen, "SNES"))
        open(os.path.join(eigen, "SNES",
                          "Super Mario World (USA).art"), "wb").write(b"ART1")
        A._art_index_cache.clear()
        pfad = A._art_path_in(eigen, "SNES", "Super Mario World (USA)")
        check("vorhandenes eigenes Cover gewinnt", pfad.endswith(".art"), pfad)
        pfad = A._art_path_in(eigen, "SNES", "Nummeriert (USA)")
        check("ohne eigenes Cover greift die fremde Quelle",
              pfad.startswith(tmp), pfad)

        merk = S.FREMDQUELLEN_AUS_FLAG
        aus = os.path.join(eigen, "fremdquellen_aus")
        try:
            S.FREMDQUELLEN_AUS_FLAG = aus
            open(aus, "w").close()
            A.docs_caches_leeren()
            check("abgeschaltet: kein fremdes Cover mehr",
                  A._art_path_in(eigen, "SNES",
                                 "Nummeriert (USA)").endswith(".art"))
            check("abgeschaltet: auch keine fremden Spieledaten",
                  A.get_meta("SNES", "Super Mario World (USA)") == {})
            os.remove(aus)
            A.docs_caches_leeren()
            check("wieder an: die fremde Quelle ist zurueck",
                  A._art_path_in(eigen, "SNES",
                                 "Nummeriert (USA)").startswith(tmp))
        finally:
            S.FREMDQUELLEN_AUS_FLAG = merk
            A.docs_caches_leeren()

        print()
        print("Test 9: eigene Spieledaten haben Vorrang, fremde fuellen auf")
        A._meta_cache["SNES"] = {
            "Super Mario World (USA)": {"year": "1991", "players": "2"}}
        z = A.get_meta("SNES", "Super Mario World (USA)")
        check("unser Jahr bleibt stehen", z.get("year") == "1991", "%r" % (z,))
        check("unsere Spielerzahl bleibt stehen", z.get("players") == "2")
        check("der Entwickler kommt dazu",
              z.get("developer") == "Nintendo EAD")
        check("und das Genre, das wir nicht hatten",
              z.get("genre") == "Platformer")
        A._meta_cache.clear()
    finally:
        shutil.rmtree(eigen, ignore_errors=True)
finally:
    A.DOCS_BASE = _alt_docs
    A.docs_caches_leeren()
    A._meta_cache.clear()
    shutil.rmtree(tmp, ignore_errors=True)

print()
print("Test 10: ohne die Datenbank passiert schlicht nichts")
_alt_docs = A.DOCS_BASE
try:
    A.DOCS_BASE = os.path.join(tempfile.gettempdir(), "gibt_es_nicht_115")
    A.docs_caches_leeren()
    check("kein Cover", A.docs_cover("SNES", "Irgendwas") is None)
    check("keine Daten", A.docs_meta("SNES", "Irgendwas") == {})
    check("und get_meta bleibt leer statt zu stolpern",
          A.get_meta("SNES", "Irgendwas") == {})
finally:
    A.DOCS_BASE = _alt_docs
    A.docs_caches_leeren()
    A._meta_cache.clear()

print()
print("Test 12: Vorbereitung und Zeichenpfad ergeben DASSELBE (Build 116)")
# Der Modul-Kommentar von fe/art.py verlangt, dass eine gespeicherte
# Miniatur bit-identisch zu einer frisch berechneten ist. Bis Build 115
# war das fuer JPG/PNG gar nicht pruefbar - prewarm_thumb() kannte nur
# "ART1" und gab bei allem anderen "fehler" zurueck. Die fremden Cover
# wurden von "Miniaturen vorbereiten" also komplett uebergangen; jedes
# einzelne musste der Zeichenpfad rechnen, immer wieder.
if not HAT_PIL:
    ungeprueft("Vorbereitung gegen Zeichenpfad", "Pillow fehlt")
else:
    tmp = tempfile.mkdtemp(prefix="vorwaermen_")
    _alt_thumb = A.THUMB_CACHE_DIR
    try:
        A.THUMB_CACHE_DIR = os.path.join(tmp, "thumbs")
        os.makedirs(A.THUMB_CACHE_DIR)
        gross = testbild("RGB", 424, 768)
        proben = [("PNG", "c.png", als_png(gross))]
        if B.verfuegbar():
            proben.append(("JPG", "c.jpg", als_jpg(gross, quality=90)))
        for name, dateiname, daten in proben:
            pfad = os.path.join(tmp, dateiname)
            open(pfad, "wb").write(daten)
            for kasten, bw, bh in (("CRT", 110, 150), ("HDMI", 360, 420)):
                ergebnis = A.prewarm_thumb(pfad, bw, bh)
                check("%s/%s: Vorbereitung schafft es ueberhaupt"
                      % (name, kasten), ergebnis == "fertig", repr(ergebnis))
                vom_band = A.ArtCache().get_scaled(pfad, bw, bh)
                aus_cache = A._thumb_cache_get(pfad, bw, bh)
                check("%s/%s: und liefert bitgenau dasselbe Bild"
                      % (name, kasten),
                      vom_band is not None and aus_cache == vom_band,
                      "vorbereitet=%s gezeichnet=%s"
                      % (aus_cache[:2] if aus_cache else None,
                         vom_band[:2] if vom_band else None))
        # Und die Zielgroesse muss dieselbe sein wie vor Build 116,
        # sonst passen alte Miniaturen nicht mehr zu neuen.
        for nw, nh, bw, bh in ((424, 768, 360, 420), (424, 768, 110, 150),
                               (300, 200, 360, 420), (1000, 100, 360, 420)):
            sc = min(bw / nw, bh / nh)
            alt = (max(1, int(nw * sc)), max(1, int(nh * sc)))
            neu = A.zielmass(nw, nh, bw, bh)
            if nw <= bw and nh <= bh:
                check("%dx%d passt in %dx%d -> kein Verkleinern"
                      % (nw, nh, bw, bh), neu is None, repr(neu))
            else:
                check("%dx%d in %dx%d -> %r wie bisher"
                      % (nw, nh, bw, bh, alt), neu == alt, repr(neu))
    finally:
        A.THUMB_CACHE_DIR = _alt_thumb
        shutil.rmtree(tmp, ignore_errors=True)

print()
print("Test 13: verkleinert dekodieren bringt wirklich etwas")
if not (HAT_PIL and B.verfuegbar()):
    ungeprueft("Gewinn durch Decode auf Mass", "Pillow oder TurboJPEG fehlt")
else:
    daten = als_jpg(testbild("RGB", 424, 768), quality=90)
    tmp = tempfile.mkdtemp(prefix="aufmass_")
    try:
        pfad = os.path.join(tmp, "c.jpg")
        open(pfad, "wb").write(daten)
        for kasten, bw, bh in (("CRT", 110, 150), ("HDMI", 360, 420)):
            c = A.ArtCache()
            gelesen = c.get(pfad, bw, bh)
            nativ = c.nativ.get(pfad)
            ziel = A.zielmass(nativ[0], nativ[1], bw, bh)
            check("%s: dekodiert kleiner als die Datei" % kasten,
                  gelesen[0] < nativ[0] and gelesen[1] < nativ[1],
                  "Datei %r -> dekodiert %r, Ziel %r"
                  % (nativ, gelesen[:2], ziel))
            check("%s: aber nie unter die Zielgroesse" % kasten,
                  gelesen[0] >= ziel[0] and gelesen[1] >= ziel[1],
                  "%r >= %r" % (gelesen[:2], ziel))
        # Ohne Kastenangabe muss weiterhin alles in voller Groesse
        # kommen - sonst bekaeme ein Aufrufer ohne Groesse (z.B. der
        # Trophaeenraum) heimlich ein verkleinertes Bild.
        c = A.ArtCache()
        voll = c.get(pfad)
        check("ohne Kastenangabe volle Groesse",
              (voll[0], voll[1]) == c.nativ.get(pfad),
              "%r" % (voll[:2],))
        # Und ein einmal klein gelesenes Bild darf einem groesseren
        # Kasten nicht untergeschoben werden.
        c = A.ArtCache()
        c.get(pfad, 110, 150)
        gross = c.get(pfad, 360, 420)
        ziel_gross = A.zielmass(c.nativ[pfad][0], c.nativ[pfad][1], 360, 420)
        check("groesserer Kasten bekommt ein passendes Bild",
              gross[0] >= ziel_gross[0] and gross[1] >= ziel_gross[1],
              "%r fuer Ziel %r" % (gross[:2], ziel_gross))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

print()
print("Test 11: Menuepunkt und Uebersetzungen")
quelle = open(os.path.join(_REPO, "frontend", "frontend.py"),
              encoding="utf-8", errors="replace").read()
menue = open(os.path.join(_REPO, "frontend", "fe", "menu.py"),
             encoding="utf-8", errors="replace").read()
check("Menuepunkt vorhanden", '"fremdquellen"' in menue)
check("Schalter wird verarbeitet", 'elif kind == "fremdquellen":' in quelle)
check("und die Zwischenspeicher fallen dabei",
      "docs_caches_leeren()" in quelle)
import fe.translations as T                             # noqa: E402
for key in ("sys_fremdquellen_on", "sys_fremdquellen_off"):
    e = T.TRANSLATIONS.get(key, {})
    check("%s in beiden Sprachen" % key,
          bool(e.get("de")) and bool(e.get("en")))
check("Standard ist AN (nur eine Datei schaltet ab)",
      S.fremdquellen_enabled() is True)

print()
if offen:
    print("Nicht pruefbar auf diesem Rechner (%d):" % len(offen))
    for o in offen:
        print("  -", o)
    print()
if fails:
    print("FEHLGESCHLAGEN (%d):" % len(fails))
    for f_ in fails:
        print("  -", f_)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
