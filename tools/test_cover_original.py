#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft den Download im Originalformat, den Enter-Fehler beim
Tauschschalter und das laengere Warten auf eine USB-Platte (Build 119).

DREI DINGE, DIE NICHTS MITEINANDER ZU TUN HABEN - ausser dass sie
alle aus derselben Rueckmeldungsrunde stammen.

1. COVER IM ORIGINAL ABLEGEN. Nutzerwunsch: "ich wuerde ganz gerne JPG
   und PNG beim Cover-Download bevorzugen, anstatt auf .art
   umzuwandeln - denke mal das ist der bessere und schnellere Weg,
   wenn einer alles auf einmal runterladen moechte". Seit Build 115
   liest das Frontend PNG und JPG selbst, also spricht nichts mehr
   dagegen. Der Download ist dann nur noch Download - das Dekodieren
   und Verkleinern in Python auf der MiSTer-CPU faellt weg -, und die
   Datei behaelt ihre volle Aufloesung, bedient also CRT UND HDMI.

   WAS DABEI SCHIEFGEHEN KANN und hier geprueft wird: das Frontend
   muss die abgelegte Datei auch FINDEN. Der Cover-Index kannte bis
   Build 118 nur ".art" - ohne die Erweiterung laege das Cover auf der
   Karte und wuerde nie gefunden.

2. ENTER-TASTE. Nutzer-Rueckmeldung: "wenn ich unter Eingabe und
   Sprache Bestaetigen/Abbrechen vertauschen aktiviere, aendert auf
   einmal die Enter-Taste auf der Tastatur ihre Funktion - das ist
   Mist". Der Schalter ist fuer das PAD gedacht (Nintendo- gegen
   Xbox-Anordnung), fasste aber die ganze Tastenbelegung an.

3. USB-WARTEZEIT. Nutzer-Rueckmeldung: "er liest sie beim Start quasi
   nochmal ein, das macht er bei jedem kalten Neustart". Zehn Sekunden
   waren fuer eine anlaufende Festplatte zu knapp.

Ausfuehren:
    python3 tools/test_cover_original.py
"""
import io
import os
import shutil
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)

import _harness as H                                    # noqa: E402,F401

sys.path.insert(0, os.path.join(_REPO, "frontend"))
import fe.art as A                                      # noqa: E402
import fe.input as I                                    # noqa: E402
import fe.scan as S                                     # noqa: E402

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


print("Test 1: der Download legt das Original ab")
if not HAT_PIL:
    ungeprueft("Download im Original", "Pillow fehlt")
else:
    import mister_boxart as MB                          # noqa: E402
    tmp = tempfile.mkdtemp(prefix="dl_")
    try:
        out = os.path.join(tmp, "SNES")
        os.makedirs(out)
        bild = Image.new("RGB", (400, 560), (10, 20, 30))
        b = io.BytesIO()
        bild.save(b, "PNG")
        png = b.getvalue()
        b = io.BytesIO()
        bild.save(b, "JPEG")
        jpg = b.getvalue()

        echt_match = MB.match_rom
        echt_dl = MB.download_cover
        try:
            MB.match_rom = lambda *a, **k: ("Cover.png", "exakt")
            MB.download_cover = lambda *a, **k: png
            MB.ORIGINAL_BEHALTEN = True
            r = MB.process_one_rom_fallback("Spiel (USA)", "SNES", {}, {}, {},
                                            out, (300, 350))
            check("PNG wird als .png abgelegt",
                  r[1] == "ok" and os.path.exists(
                      os.path.join(out, "Spiel (USA).png")),
                  "%r -> %r" % (r, sorted(os.listdir(out))))
            check("und unveraendert, Byte fuer Byte",
                  open(os.path.join(out, "Spiel (USA).png"), "rb").read() == png)

            # Die Endung richtet sich nach dem INHALT, nicht nach dem
            # Namen auf dem Server - der heisst dort immer ".png".
            MB.download_cover = lambda *a, **k: jpg
            MB.process_one_rom_fallback("Zweites (USA)", "SNES", {}, {}, {},
                                        out, (300, 350))
            check("ein JPEG wird als .jpg abgelegt, nicht als .png",
                  os.path.exists(os.path.join(out, "Zweites (USA).jpg")),
                  "%r" % (sorted(os.listdir(out)),))

            # Der alte Weg muss weiter funktionieren - wer knapp bei
            # Platz ist, waehlt ihn bewusst.
            MB.download_cover = lambda *a, **k: png
            MB.ORIGINAL_BEHALTEN = False
            MB.process_one_rom_fallback("Drittes (USA)", "SNES", {}, {}, {},
                                        out, (300, 350))
            check("mit 'art' wird weiterhin umgewandelt",
                  os.path.exists(os.path.join(out, "Drittes (USA).art")),
                  "%r" % (sorted(os.listdir(out)),))
        finally:
            MB.match_rom = echt_match
            MB.download_cover = echt_dl
            MB.ORIGINAL_BEHALTEN = True

        print()
        print("Test 2: und das Frontend findet sie auch")
        # Der eigentliche Knackpunkt. Ohne den erweiterten Cover-Index
        # laegen die Dateien auf der Karte und wuerden nie gefunden.
        _alt_docs = A.DOCS_BASE
        try:
            A.DOCS_BASE = os.path.join(tmp, "keine_docs")
            A.docs_caches_leeren()
            A._art_index_cache.clear()
            for rom, endung in (("Spiel (USA)", ".png"),
                                ("Zweites (USA)", ".jpg"),
                                ("Drittes (USA)", ".art")):
                p = A._art_path_in(tmp, "SNES", rom)
                check("%-16s wird als %s gefunden" % (rom, endung),
                      p is not None and p.endswith(endung),
                      os.path.basename(p) if p else "None")
            # Und sie muessen sich auch lesen lassen.
            for rom in ("Spiel (USA)", "Zweites (USA)"):
                p = A._art_path_in(tmp, "SNES", rom)
                bild = A.ArtCache().get(p, 300, 350)
                check("%-16s laesst sich dekodieren" % rom,
                      bild is not None and bild[0] > 0,
                      "%r" % (bild[:2] if bild else None,))
            # Liegt beides, gewinnt unser eigenes Format - es ist
            # bereits fertig verkleinert und damit billiger.
            open(os.path.join(out, "Spiel (USA).art"), "wb").write(b"ART1")
            A._art_index_cache.clear()
            p = A._art_path_in(tmp, "SNES", "Spiel (USA)")
            check("bei beidem gewinnt .art", p.endswith(".art"),
                  os.path.basename(p))
        finally:
            A.DOCS_BASE = _alt_docs
            A.docs_caches_leeren()
            A._art_index_cache.clear()

        print()
        print("Test 3: ein zweiter Lauf laedt nichts doppelt")
        # Ohne das wuerde jeder weitere Durchlauf alles noch einmal
        # herunterladen, was der erste als Original abgelegt hat.
        quelle = open(os.path.join(_REPO, "frontend", "mister_boxart.py"),
                      encoding="utf-8", errors="replace").read()
        check("die Ueberspringen-Pruefung kennt alle drei Endungen",
              '(".art", ".png", ".jpg", ".jpeg")' in quelle)
        check("und es gibt einen Weg zurueck zum alten Verhalten",
              '"art", "--art", "umwandeln"' in quelle)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

print()
print("Test 4: der Tauschschalter laesst die Tastatur in Ruhe")
vorher = dict(I.KEYMAP)
try:
    I._swap_ok_back_in_keymap()
    check("Enter bleibt Bestaetigen",
          I.KEYMAP.get(I.KEY_ENTER) == "ok", repr(I.KEYMAP.get(I.KEY_ENTER)))
    check("Esc bleibt, was es war",
          I.KEYMAP.get(I.KEY_ESC) == vorher.get(I.KEY_ESC))
    check("A und B tauschen dagegen wirklich",
          I.KEYMAP.get(I.BTN_A) == "back" and I.KEYMAP.get(I.BTN_B) == "ok",
          "A=%r B=%r" % (I.KEYMAP.get(I.BTN_A), I.KEYMAP.get(I.BTN_B)))
    check("Start bleibt Bestaetigen",
          I.KEYMAP.get(I.BTN_START) == "ok", repr(I.KEYMAP.get(I.BTN_START)))
    check("X bleibt der Ausstieg",
          I.KEYMAP.get(I.BTN_X) == vorher.get(I.BTN_X))
    # Selbstinvers: zweimal anwenden muss den Ausgangszustand
    # wiederherstellen - darauf baut das Umschalten im Menue.
    I._swap_ok_back_in_keymap()
    check("zweimal angewendet ist wieder der Ausgangszustand",
          I.KEYMAP == vorher)
finally:
    I.KEYMAP.clear()
    I.KEYMAP.update(vorher)

print()
print("Test 5: eine anlaufende USB-Platte bekommt genug Zeit")
check("die Wartezeit ist grosszuegig bemessen",
      S.USB_WARTEN_KALTSTART >= 30.0, "%.0f s" % S.USB_WARTEN_KALTSTART)
quelle = open(os.path.join(_REPO, "frontend", "fe", "scan.py"),
              encoding="utf-8", errors="replace").read()
check("und wird nur dort benutzt, wo der Cache USB erwartet",
      "_wait_for_usb_stable(max_wait=USB_WARTEN_KALTSTART)" in quelle
      and quelle.count("USB_WARTEN_KALTSTART") == 2)
check("der allgemeine Fall wartet weiterhin kurz",
      "def _wait_for_usb_stable(max_wait=10.0" in quelle)
check("und es gibt ein Lebenszeichen auf dem Schirm",
      "warte_cb()" in quelle)
frontend = open(os.path.join(_REPO, "frontend", "frontend.py"),
                encoding="utf-8", errors="replace").read()
check("das Frontend reicht es durch",
      "warte_cb=self._draw_laufwerk_warten" in frontend)
check("und zeichnet etwas",
      "def _draw_laufwerk_warten(self):" in frontend)
import fe.translations as T                             # noqa: E402
for key in ("warte_laufwerk", "warte_laufwerk_hinweis"):
    e = T.TRANSLATIONS.get(key, {})
    check("%s in beiden Sprachen" % key,
          bool(e.get("de")) and bool(e.get("en")))

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
