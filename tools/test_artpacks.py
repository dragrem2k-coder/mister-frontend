#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft Artpack-Quellen, Arcade beim Vorbereiten und den groesseren
Bild-Zwischenspeicher (Build 120).

DREI PUNKTE AUS EINER RUECKMELDUNG:

1. ARCADE. "Habe eine neue SD-Karte verbaut, noch keine ROMs drauf,
   aber Arcade ueber Update All bekommen - wenn ich jetzt Miniaturen
   dafuer vorbereiten will, sagt das Frontend 'keine Spiele
   gefunden'."

   Stimmte. cover_pfad_und_kasten() hatte eine Ausnahme fuer ARCADE
   mit der Begruendung, Arcade-Cover haengen an mra_meta() und es gebe
   keinen einfachen Dateipfad. Der erste Teil stimmt - die METADATEN
   kommen aus der MRA-Datei -, der Schluss war falsch: das COVER liegt
   wie ueberall unter <art>/ARCADE/<Name>, und der Zeichenpfad sucht es
   dort auch. Nur das Vorbereiten machte einen Bogen darum. Wer
   ausschliesslich Arcade hat, bekam eine leere Arbeitsliste.

2. ARTPACKS. Bis Build 119 war nur die Datenbank unter /media/fat/docs
   gemeint. Artpacks landen je nach Paket woanders - in einem eigenen
   Artwork-Ordner, oder gleich neben den ROMs.

3. ZWISCHENSPEICHER. "Der zweite Durchlauf durch eine Liste ist
   schneller - stoert mich sehr." Ein HDMI-Cover belegt rund 388 KB,
   in 24 MB passten damit etwa sechzig. Bei tausenden Eintraegen faellt
   ein Cover laengst wieder heraus, bevor man es wiedersieht.

Ausfuehren:
    python3 tools/test_artpacks.py
"""
import os
import shutil
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)

import _harness as H                                    # noqa: E402

sys.path.insert(0, os.path.join(_REPO, "frontend"))
import fe.art as A                                      # noqa: E402
import fe.paths                                         # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


print("Test 1: Arcade bekommt jetzt auch Miniaturen")
H.set_screen(1920, 1080)
f = H.make_frontend(page=1)
geo = (700, 800, 3)
arcade = ("Bubble Bobble", "core", "/media/fat/_Arcade/Bubble Bobble.mra")
auftrag = f.cover_pfad_und_kasten(arcade, "ARCADE", geo)
check("ein Arcade-Eintrag liefert einen Auftrag", auftrag is not None,
      repr(auftrag))
if auftrag:
    check("und zwar im ARCADE-Cover-Ordner",
          os.path.sep + "ARCADE" + os.path.sep in auftrag[0], auftrag[0])
    check("mit einer sinnvollen Kastengroesse",
          auftrag[1] > 0 and auftrag[2] > 0, "%r" % (auftrag[1:],))
# Und der Zeichenpfad muss denselben Pfad suchen - sonst laegen die
# Miniaturen unter einem Schluessel, den nie jemand abfragt.
gezeichnet = A._art_path_in(A.ART_HD, "ARCADE", "Bubble Bobble")
check("derselbe Pfad, den auch der Zeichenpfad sucht",
      auftrag is not None and auftrag[0] == gezeichnet,
      "%s vs %s" % (auftrag[0] if auftrag else None, gezeichnet))
quelle = open(os.path.join(_REPO, "frontend", "frontend.py"),
              encoding="utf-8", errors="replace").read()
check("die alte Ausnahme ist wirklich raus",
      'if item_syskey == "ARCADE":\n            # Arcade-Cover' not in quelle)

print()
print("Test 2: Artpacks in ihren verschiedenen Formen")
# Nachgebaut werden die drei Ablageformen, die in freier Wildbahn
# vorkommen: die docs-Datenbank, ein eigener Artwork-Ordner mit
# Named_Boxarts, und Bilder direkt neben den ROMs.
tmp = tempfile.mkdtemp(prefix="artpacks_")
_alt = (A.DOCS_BASE, A.FREMD_ZUSATZ_WURZELN, list(fe.paths.GAMES_BASES))
try:
    docs = os.path.join(tmp, "docs")
    pack = os.path.join(tmp, "Artwork")
    spiele = os.path.join(tmp, "games")
    os.makedirs(os.path.join(docs, "SNES", "Artwork"))
    os.makedirs(os.path.join(pack, "SNES", "Named_Boxarts"))
    os.makedirs(os.path.join(spiele, "SNES"))
    open(os.path.join(docs, "SNES", "Artwork",
                      "Aus docs (USA).jpg"), "wb").write(b"x")
    open(os.path.join(pack, "SNES", "Named_Boxarts",
                      "Aus Artpack (USA).png"), "wb").write(b"x")
    open(os.path.join(spiele, "SNES",
                      "Neben dem ROM (USA).png"), "wb").write(b"x")
    # Dasselbe Spiel in zwei Paketen - das zuerst durchsuchte gewinnt,
    # und zwar immer dasselbe, nicht mal so und mal so.
    open(os.path.join(docs, "SNES", "Artwork",
                      "Doppelt (USA).jpg"), "wb").write(b"x")
    open(os.path.join(pack, "SNES", "Named_Boxarts",
                      "Doppelt (USA).png"), "wb").write(b"x")

    A.DOCS_BASE = docs
    A.FREMD_ZUSATZ_WURZELN = (pack,)
    fe.paths.GAMES_BASES = [spiele]
    A.docs_caches_leeren()

    check("alle drei Wurzeln werden durchsucht",
          A.fremd_wurzeln()[:3] == [docs, pack, spiele],
          "%r" % (A.fremd_wurzeln()[:3],))
    for rom, wo in (("Aus docs (USA)", docs),
                    ("Aus Artpack (USA)", pack),
                    ("Neben dem ROM (USA)", spiele)):
        p = A.docs_cover("SNES", rom)
        check("%-20s gefunden" % rom, p is not None and p.startswith(wo),
              p or "None")
    p1 = A.docs_cover("SNES", "Doppelt (USA)")
    A.docs_caches_leeren()
    p2 = A.docs_cover("SNES", "Doppelt (USA)")
    check("bei zwei Paketen gewinnt immer dasselbe",
          p1 == p2 and p1 is not None and p1.startswith(docs), "%s" % p1)
    check("und was es nirgends gibt, gibt es nicht",
          A.docs_cover("SNES", "Gibt es nicht") is None)

    # Der unscharfe Namensabgleich aus Build 117 muss ueber alle
    # Quellen hinweg funktionieren, nicht nur ueber die erste.
    check("anders benannte ROMs finden auch im Artpack etwas",
          A.docs_cover("SNES", "Aus Artpack (U) [!]") is not None)

    # Eine gameinfo.tsv im Artpack-Ordner muss ebenso gelesen werden.
    with open(os.path.join(pack, "SNES", "Named_Boxarts", "gameinfo.tsv"),
              "w", encoding="utf-8") as fh:
        fh.write("#key\tname\tyear\tgenre\tdeveloper\tplayers\n")
        fh.write("Aus Artpack (USA)\tAus Artpack\t1994\tAction\tRare\t1\n")
    A.docs_caches_leeren()
    check("Spieledaten auch aus einem Artpack",
          A.docs_meta("SNES", "Aus Artpack (USA)").get("year") == "1994",
          "%r" % (A.docs_meta("SNES", "Aus Artpack (USA)"),))
finally:
    A.DOCS_BASE, A.FREMD_ZUSATZ_WURZELN = _alt[0], _alt[1]
    fe.paths.GAMES_BASES = _alt[2]
    A.docs_caches_leeren()
    shutil.rmtree(tmp, ignore_errors=True)

print()
print("Test 3: ohne Artpacks aendert sich nichts")
_alt_docs = A.DOCS_BASE
_alt_zusatz = A.FREMD_ZUSATZ_WURZELN
try:
    leer = os.path.join(tempfile.gettempdir(), "gibt_es_nicht_120")
    A.DOCS_BASE = leer
    A.FREMD_ZUSATZ_WURZELN = (leer + "_a", leer + "_b")
    A.docs_caches_leeren()
    check("kein Cover", A.docs_cover("SNES", "Irgendwas") is None)
    check("keine Daten", A.docs_meta("SNES", "Irgendwas") == {})
    check("und keine Ausnahme unterwegs", True)
finally:
    A.DOCS_BASE = _alt_docs
    A.FREMD_ZUSATZ_WURZELN = _alt_zusatz
    A.docs_caches_leeren()

print()
print("Test 4: der Bild-Zwischenspeicher fasst eine ganze Umgebung")
# Ein HDMI-Cover in der ueblichen Groesse belegt 231*420*4 Bytes.
hdmi_cover = 231 * 420 * 4
passt = A.ArtCache.SCALED_BUDGET // hdmi_cover
check("mindestens 200 HDMI-Cover passen hinein", passt >= 200,
      "%d Stueck bei %.0f KB je Cover" % (passt, hdmi_cover / 1024.0))
check("und die Untergrenze steht weiterhin", A.ArtCache.SCALED_MIN >= 20)
# Die Verdraengung muss trotzdem greifen - ein unbegrenzter Cache waere
# auf einem Geraet mit 1 GB die andere Sorte Fehler.
c = A.ArtCache()
c.scaled = {}
c.scaled_order = []
c.scaled_bytes = 0
brocken = bytes(4 * 1024 * 1024)
for i in range(40):
    c._scaled_cache_put(("p%d" % i, "box", 1, 1), (1, 1, brocken))
check("ueber dem Budget wird verdraengt",
      c.scaled_bytes <= A.ArtCache.SCALED_BUDGET + len(brocken),
      "%.0f MB in %d Eintraegen"
      % (c.scaled_bytes / 1048576.0, len(c.scaled_order)))
check("aber nie unter die Untergrenze",
      len(c.scaled_order) >= A.ArtCache.SCALED_MIN, "%d" % len(c.scaled_order))

print()
print("Test 5: der Download fragt zuerst das Geraet selbst")
boxart = open(os.path.join(_REPO, "frontend", "mister_boxart.py"),
              encoding="utf-8", errors="replace").read()
check("die Artwork-Datenbank wird vor dem Download geprueft",
      "_docs_cover(syskey, name)" in boxart)
check("und der Import ist weich genug fuer alte Installationen",
      "_docs_cover = None" in boxart)

print()
if fails:
    print("FEHLGESCHLAGEN (%d):" % len(fails))
    for f_ in fails:
        print("  -", f_)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
