#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Die zweite Schrift (Build 223) - MiSTers eigene OSD-Schriften.

WUNSCH DES NUTZERS: "koennen wir diese font art mit verbauen als zweite
wahl?" - mit einem Link auf eine Digitalisierung der deutschen
Kfz-Kennzeichenschrift. Sein eigener Einwand war der bessere Weg:
"Mister liefert doch eigene Fonts die man in der ini wechseln kann,
koennen wir die nicht nutzen?"

Koennen wir, und es ist der saubere Weg: die Dateien liegen bereits auf
SEINER Karte. Dieses Paket liefert keine einzige fremde Schrift mit -
dieselbe Haltung wie bei /media/fat/docs: fremde Daten lesen wir,
verteilen sie aber nicht weiter.

DAS FORMAT, nachgesehen am Werkzeug pf2png.py aus MiSTer-devel/
Fonts_MiSTer und an einer echten Datei:

  * 768 Byte, 96 Zeichen zu je 8 Byte, ein Byte je Bildzeile
  * ab Leerzeichen (0x20) aufsteigend, also schlicht ASCII
  * das OBERSTE Bit ist der linke Bildpunkt - bei uns das unterste

Der letzte Punkt ist der einzige Unterschied zu FONT8X8, und genau den
prueft Test 2 bitgenau.

Ausfuehren:
    python3 tools/test_schrift.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H          # noqa: E402

import fe.framebuffer as fm   # noqa: E402
import fe.settings as S       # noqa: E402

fails = []


def check(name, ok, info=""):
    if ok:
        print("  OK   %s %s" % (name, info))
    else:
        print("  FEHL %s %s" % (name, info))
        fails.append(name)


def pf_bauen(glyphen):
    """Eine .pf-Datei bauen. glyphen: {Zeichen: [8 Zeilen aus '#' und '.']}"""
    roh = bytearray(96 * 8)
    for ch, zeilen in glyphen.items():
        i = ord(ch) - 0x20
        for z, muster in enumerate(zeilen):
            b = 0
            for k, p in enumerate(muster):
                if p == "#":
                    b |= 1 << (7 - k)      # OBERSTES Bit = links
            roh[i * 8 + z] = b
    return bytes(roh)


# ---------------------------------------------------------------------------
print("Test 1: eine .pf-Datei wird gelesen")
# ---------------------------------------------------------------------------
MUSTER = ["#.......",
          ".#......",
          "..#.....",
          "...#....",
          "....#...",
          ".....#..",
          "......#.",
          ".......#"]
with tempfile.TemporaryDirectory() as tmp:
    pfad = os.path.join(tmp, "Test.pf")
    with open(pfad, "wb") as f:
        f.write(pf_bauen({"A": MUSTER}))
    tab = fm.schrift_laden(pfad)
    check("die Datei wird angenommen", tab is not None)
    check("und hat die Groesse unserer Tabelle",
          tab is not None and len(tab) == len(fm.FONT8X8),
          "%d Byte" % (len(tab) if tab else 0))

    # -----------------------------------------------------------------
    print()
    print("Test 2: die Bitfolge wird gespiegelt")
    # -----------------------------------------------------------------
    # DER EINZIGE UNTERSCHIED ZWISCHEN BEIDEN FORMATEN, und wenn er
    # uebersehen wird, steht jeder Buchstabe spiegelverkehrt da.
    g = tab[ord("A") * 8:ord("A") * 8 + 8]
    gelesen = ["".join("#" if b >> k & 1 else "." for k in range(8))
               for b in g]
    check("die Diagonale laeuft in dieselbe Richtung", gelesen == MUSTER,
          "gelesen %r" % gelesen[:2])

    # -----------------------------------------------------------------
    print()
    print("Test 3: alles ausserhalb 0x20..0x7F bleibt unsere Schrift")
    # -----------------------------------------------------------------
    # Eine .pf hat 96 Zeichen und endet beim 'z'. Umlaute kommen deshalb
    # weiterhin aus FONT_EXTRA - ohne das stuenden "Koenig der Loewen"
    # und jeder zweite deutsche Titel voller Fragezeichen da.
    check("die Steuerzeichen sind unveraendert",
          tab[:0x20 * 8] == fm.FONT8X8[:0x20 * 8])
    check("und ueber 0x7F ebenso",
          tab[0x80 * 8:] == fm.FONT8X8[0x80 * 8:])

    # -----------------------------------------------------------------
    print()
    print("Test 4: kaputte oder fehlende Dateien aendern nichts")
    # -----------------------------------------------------------------
    check("eine Datei, die es nicht gibt",
          fm.schrift_laden(os.path.join(tmp, "weg.pf")) is None)
    kurz = os.path.join(tmp, "Kurz.pf")
    with open(kurz, "wb") as f:
        f.write(b"\x00" * 100)
    check("eine zu kurze Datei", fm.schrift_laden(kurz) is None,
          "lieber die eigene Schrift als ein halbes Alphabet")

    # -----------------------------------------------------------------
    print()
    print("Test 5: der Wechsel leert die Zeichen-Zwischenspeicher")
    # -----------------------------------------------------------------
    # DAS IST DIE HAELFTE, DIE MAN VERGISST. _glyphcache und _textcache
    # halten FERTIG GERECHNETE Bildpunkte. Wird nur die Tabelle
    # getauscht, bleibt jeder schon gezeichnete Text in der alten
    # Schrift stehen - und zwar genau die haeufigen, denn die liegen
    # sicher im Zwischenspeicher.
    H.set_screen(320, 240)
    fb = H.make_frontend(1).fb
    fb.text(0, 0, "HALLO", 1)
    check("nach dem Zeichnen liegt etwas im Speicher",
          len(fb._textcache) > 0, "%d Eintraege" % len(fb._textcache))
    vorher = bytes(fb.buf[:64])
    geaendert = fb.schrift_setzen(tab)
    check("der Wechsel meldet sich", geaendert is True)
    check("der Textspeicher ist leer", len(fb._textcache) == 0)
    check("der Zeichenspeicher auch", len(fb._glyphcache) == 0)
    check("und die Reihenfolge-Liste ebenso",
          len(fb._textcache_order) == 0)
    check("derselbe Wechsel noch einmal tut nichts",
          fb.schrift_setzen(tab) is False)

    fb.buf[:] = bytearray(len(fb.buf))
    fb.text(0, 0, "A", 1)
    neu = bytes(fb.buf[:4])
    fb.schrift_setzen(None)
    fb.buf[:] = bytearray(len(fb.buf))
    fb.text(0, 0, "A", 1)
    alt = bytes(fb.buf[:4])
    check("und das Bild sieht danach anders aus", neu != alt,
          "sonst waere die Schrift gar nicht angekommen")
    fb.schrift_setzen(None)
    assert vorher is not None

# ---------------------------------------------------------------------------
print()
print("Test 6: die Einstellung kennt drei Faelle")
# ---------------------------------------------------------------------------
check("Vorgabe ist die eigene Schrift", S.SCHRIFT_EIGEN == "")
check("es gibt den OSD-Fall", S.SCHRIFT_OSD == "osd")
check("und einen Ordner, in dem MiSTer seine Schriften hat",
      S.SCHRIFT_DIR == "/media/fat/font")
check("der Pfad fuer die eigene Schrift ist None",
      S.schrift_pfad("") is None)
check("ein Dateiname wird an den Ordner gehaengt",
      S.schrift_pfad("Arcade_Pacman.pf")
      == "/media/fat/font/Arcade_Pacman.pf")
check("ein absoluter Pfad bleibt, wie er ist",
      S.schrift_pfad("/media/usb0/eigene.pf") == "/media/usb0/eigene.pf")

# ---------------------------------------------------------------------------
print()
print("Test 7: font= aus der MiSTer.ini wird GELESEN, nie geschrieben")
# ---------------------------------------------------------------------------
_echt_ini = S.MISTER_INI
with tempfile.TemporaryDirectory() as tmp:
    ini = os.path.join(tmp, "MiSTer.ini")
    S.MISTER_INI = ini
    try:
        with open(ini, "w") as f:
            f.write("[MiSTer]\n"
                    "; font=font/Auskommentiert.pf\n"
                    "video_mode=8\n"
                    "font=font/Arcade_Pacman.pf   ; mit Kommentar\n")
        check("die Zeile wird gefunden",
              S.schrift_aus_ini() == "font/Arcade_Pacman.pf",
              "%r" % S.schrift_aus_ini())
        check("und daraus wird ein Pfad unter /media/fat",
              S.schrift_pfad("osd")
              == "/media/fat/font/Arcade_Pacman.pf")
        vorher = open(ini, "rb").read()
        S.schrift_aus_ini()
        S.schrift_pfad("osd")
        check("die Datei ist dabei UNVERAENDERT",
              open(ini, "rb").read() == vorher,
              "in die MiSTer.ini schreibt dieses Frontend hier nicht")

        with open(ini, "w") as f:
            f.write("[MiSTer]\nvideo_mode=8\n")
        check("ohne font= kommt None", S.schrift_aus_ini() is None)
        check("und der OSD-Fall faellt auf die eigene zurueck",
              S.schrift_pfad("osd") is None)
        os.remove(ini)
        check("ohne MiSTer.ini ebenso", S.schrift_aus_ini() is None)
    finally:
        S.MISTER_INI = _echt_ini

# ---------------------------------------------------------------------------
print()
print("Test 8: es wird keine fremde Schrift mitgeliefert")
# ---------------------------------------------------------------------------
# DER PUNKT, UM DEN ES BEI DER GANZEN SACHE GING. Der Nutzer hatte eine
# Schrift von einer Download-Seite verlinkt; deren Lizenz ist unklar,
# und das Paket landet in einem oeffentlichen Repository.
_repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
gefunden = []
for wurzel, _dirs, dateien in os.walk(_repo):
    if ".git" in wurzel or "node_modules" in wurzel:
        continue
    for d in dateien:
        if d.lower().endswith((".pf", ".ttf", ".otf", ".woff", ".woff2")):
            gefunden.append(os.path.join(wurzel, d)[len(_repo) + 1:])
check("keine Schriftdatei im Paket", not gefunden,
      "gefunden: %s" % (gefunden[:3] if gefunden else ""))

quelle = open(H.FRONTEND_PY, encoding="utf-8", errors="replace").read()
check("die Schrift wird beim Start angewandt",
      "schrift_anwenden(self.fb)" in quelle)
check("und ein Fehlschlag faellt still auf die eigene zurueck",
      "bleibe bei der eigenen" in quelle)

print()
if fails:
    print("FEHLGESCHLAGEN (%d):" % len(fails))
    for f in fails:
        print("  - %s" % f)
    sys.exit(1)
print("Alles in Ordnung.")
