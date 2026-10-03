#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MiSTers Lochmasken im Frontend (Build 226).

WUNSCH DES NUTZERS: "Masken vom Mister selbst benutzen, bitte mit
eigener Kategorie unter System, mit Auswahl und an und aus Schalter".

Dieselbe Haltung wie bei den Schriften aus Build 223: die Dateien liegen
in /media/fat/Shadow_Masks auf SEINER Karte, wir lesen sie nur. Dieses
Paket enthaelt keine einzige Maskendatei - Test 6 geht das ganze Paket
durch und meldet jede, die sich einschleicht.

DIE DREI STELLEN, AN DENEN ES KIPPEN KANN, und jede hat hier ihren Test:

  1. Das FORMAT. Eine Datei kann MEHRERE Muster fuer verschiedene
     Bildhoehen enthalten - 106 von 1207 Dateien der echten Sammlung tun
     das. Ein Leser, der nur den ersten Block kennt, wirft ausgerechnet
     die aufwendigsten Masken weg (Sony PVM, Commodore 1084).
  2. Der PUFFER MUSS SAUBER BLEIBEN. Die Maske liegt auf dem Weg zum
     Bildspeicher, nicht im Puffer - sonst legte der naechste
     Teilaufbau sie ein zweites Mal darueber, und das Bild wuerde mit
     jedem Scrollschritt dunkler.
  3. Die BILDWAECHTER vergleichen byteweise gegen gemerkte Proben. Auf
     dem Schirm steht mit Maske "Puffer MAL Maske" - merken sie sich
     den Puffer, melden sie in JEDEM Bild "das ist nicht mehr unser
     Bild" und kopieren alles neu.

Ausfuehren:
    python3 tools/test_masken.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H          # noqa: E402

import fe.masken as M         # noqa: E402
import fe.art as A            # noqa: E402
import fe.settings as S       # noqa: E402

fails = []
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def check(name, ok, info=""):
    if ok:
        print("  OK   %s %s" % (name, info))
    else:
        print("  FEHL %s %s" % (name, info))
        fails.append(name)


EINFACH = """####
# Name: Test
####

Resolution=0
v2
2,2
700,007
007,700
"""

MEHRTEILIG = """####
# Name: Zweiteilig
####
v2
1,1
777

Resolution=1080
v2
2,1
000,7ff
"""


# ---------------------------------------------------------------------------
print("Test 1: das Format")
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    p = os.path.join(tmp, "Test.txt")
    open(p, "w").write(EINFACH)
    m = M.maske_lesen(p)
    check("eine einfache Datei wird gelesen", m is not None)
    check("Masse stimmen", m[:2] == (2, 2), "%r" % (m[:2],))
    # "700" = Farbe 7 (alle Kanaele an), An-Staerke 0 -> 16/16,
    # Aus-Staerke 0. Alle drei Kanaele sind an, also ueberall 16.
    check("'700' ergibt dreimal 16 (unveraendert)",
          m[2][:3] == [16, 16, 16], "%r" % (m[2][:3],))
    # "007" = Farbe 0 (Grau, kein Kanal an), Aus-Staerke 7 -> 7/16.
    check("'007' ergibt dreimal 7 (abgedunkelt)",
          m[2][3:6] == [7, 7, 7], "%r" % (m[2][3:6],))
    check("der Name kommt aus dem Dateinamen", m[4] == "Test", m[4])

    # Die Kanal-Bits: 1=Blau, 2=Gruen, 4=Rot
    for zelle, erwartet in (("400", [16, 0, 0]), ("200", [0, 16, 0]),
                            ("100", [0, 0, 16]), ("40f", [16, 15, 15])):
        check("Zelle %s -> %r" % (zelle, erwartet),
              list(M._zelle(zelle)) == erwartet, "%r" % (M._zelle(zelle),))

    # ---------------------------------------------------------------
    print()
    print("Test 2: eine Datei mit MEHREREN Mustern")
    # ---------------------------------------------------------------
    p2 = os.path.join(tmp, "Zwei.txt")
    open(p2, "w").write(MEHRTEILIG)
    m0 = M.maske_lesen(p2)
    m1 = M.maske_lesen(p2, 1080)
    check("ohne Hoehe kommt der Block ohne Resolution",
          m0 is not None and m0[:2] == (1, 1), "%r" % (m0 and m0[:2],))
    check("mit 1080 der passende", m1 is not None and m1[:2] == (2, 1),
          "%r" % (m1 and m1[:2],))
    check("und mit einer unbekannten Hoehe wieder der allgemeine",
          M.maske_lesen(p2, 999)[:2] == (1, 1))

    # ---------------------------------------------------------------
    print()
    print("Test 3: kaputte Dateien aendern nichts")
    # ---------------------------------------------------------------
    for name, inhalt in (("leer", ""),
                         ("ohne Masse", "v2\n700,007\n"),
                         ("zu gross", "v2\n99,99\n700\n"),
                         ("falsche Zellenzahl", "v2\n2,2\n700\n007,700\n"),
                         ("Unfug", "das ist keine Maske\n")):
        p3 = os.path.join(tmp, "Kaputt.txt")
        open(p3, "w").write(inhalt)
        check("%-20s liefert None" % name, M.maske_lesen(p3) is None)
    check("eine Datei, die es nicht gibt",
          M.maske_lesen(os.path.join(tmp, "weg.txt")) is None)

    # Eine Maske, die nichts tut, wird als neutral erkannt
    p4 = os.path.join(tmp, "Neutral.txt")
    open(p4, "w").write("v2\n1,1\n700\n")
    check("eine wirkungslose Maske wird erkannt",
          M.ist_neutral(M.maske_lesen(p4)),
          "sonst rechnet C je Bildpunkt fuer nichts")

# ---------------------------------------------------------------------------
print()
print("Test 4: C rechnet, was die Tabelle sagt")
# ---------------------------------------------------------------------------
check("libdragend kann es", getattr(A, "_HAT_MASKE", False))
B, HO = 4, 2
src = bytearray()
for _y in range(HO):
    for _x in range(B):
        src += bytes((100, 100, 100, 255))        # BGRA, ueberall 100
dst = bytearray(len(src))
# 2x1-Muster: links alles aus (0), rechts das Hoechste, was das Format
# kann - 31/16, also 193,75 %. Mehr gibt es nicht: die An-Staerke geht
# von 0 bis f und steht fuer (16+f)/16.
maske = (2, 1, [0, 0, 0, 31, 31, 31])
ok = A.rechtecke_maske(bytes(src), dst, B * 4, HO, len(dst),
                       ((0, 0, B, HO),), maske)
check("der Aufruf geht durch", ok)
werte = [dst[i * 4] for i in range(B)]
check("abwechselnd 0 und 193", werte == [0, 193, 0, 193], "%r" % werte)
check("und die Deckkraft bleibt",
      all(dst[i * 4 + 3] == 255 for i in range(B)))

# Ueberlauf wird geklemmt, nicht umgebrochen
src2 = bytes((200, 200, 200, 255)) * 4
dst2 = bytearray(len(src2))
A.rechtecke_maske(src2, dst2, 4 * 4, 1, len(dst2), ((0, 0, 4, 1),),
                  (1, 1, [31, 31, 31]))
check("200 mal 1,94 wird zu 255, nicht zu 131",
      all(dst2[i * 4] == 255 for i in range(4)),
      "%r" % [dst2[i * 4] for i in range(4)])

# DIE PHASE HAENGT AN DER BILDSCHIRMPOSITION, nicht am Rechteck - sonst
# saesse das Muster in jedem Teilstueck woanders und das Bild zerfiele
# in sichtbare Kacheln.
src3 = bytes((100, 100, 100, 255)) * 4
ganz = bytearray(len(src3))
A.rechtecke_maske(src3, ganz, 4 * 4, 1, len(ganz), ((0, 0, 4, 1),), maske)
stueck = bytearray(len(src3))
A.rechtecke_maske(src3, stueck, 4 * 4, 1, len(stueck),
                  ((0, 0, 2, 1), (2, 0, 2, 1)), maske)
check("ein Faktor ausserhalb 0..31 wird ABGEWIESEN",
      A.rechtecke_maske(src3, bytearray(len(src3)), 4 * 4, 1,
                        len(src3), ((0, 0, 4, 1),),
                        (1, 1, [99, 16, 16])) is False,
      "das waere ein Lesefehler in fe/masken.py - lieber nichts tun")
check("in zwei Stuecken kommt dasselbe heraus wie am Stueck",
      bytes(ganz) == bytes(stueck),
      "sonst zerfaellt das Bild beim Teilaufbau in Kacheln")

# ---------------------------------------------------------------------------
print()
print("Test 5: der Puffer bleibt sauber, die Waechter lernen mit")
# ---------------------------------------------------------------------------
quelle = open(os.path.join(_REPO, "frontend", "fe", "framebuffer.py"),
              encoding="utf-8").read()
check("die Maske wird NICHT in den Puffer gerechnet",
      "self.buf, self.mm, self.stride" in quelle,
      "Quelle ist der Puffer, Ziel der Bildspeicher")
check("beide Waechter merken sich mit Maske den SCHIRM",
      quelle.count("self.mm if self.maske is not None") == 2,
      "sonst meldet der Waechter in jedem Bild fremden Inhalt")
check("auch das Vollbild geht ueber die Maske",
      "_maske_kopieren(((0, 0, self.width, self.height),))" in quelle)
check("und das Band ebenfalls",
      "_maske_kopieren(((0, y0, self.width, y1 - y0),))" in quelle)
check("faellt C aus, wird ohne Maske kopiert",
      "return False" in quelle.split("def _maske_kopieren")[1][:900],
      "lieber ein Bild ohne Effekt als gar keines")

# ---------------------------------------------------------------------------
print()
print("Test 6: Auswahl UND Schalter - und keine mitgelieferte Datei")
# ---------------------------------------------------------------------------
check("es gibt eine Auswahl", hasattr(S, "maske_lesen"))
check("und einen eigenen Schalter", hasattr(S, "toggle_maske"))
check("beide sind getrennt", S.MASKE_FILE != S.MASKE_AUS_FLAG,
      "wer kurz abschaltet, soll seine Auswahl behalten")
check("der Ordner ist MiSTers eigener",
      M.MASKEN_DIR == "/media/fat/Shadow_Masks")

gefunden = []
for wurzel, _dirs, dateien in os.walk(_REPO):
    if ".git" in wurzel or "node_modules" in wurzel:
        continue
    if os.path.basename(wurzel).lower() in ("shadow_masks", "filters"):
        gefunden.extend(os.path.join(wurzel, d) for d in dateien)
check("keine Maskendatei im Paket", not gefunden,
      "%s" % (gefunden[:2] if gefunden else ""))

quelle_f = open(H.FRONTEND_PY, encoding="utf-8", errors="replace").read()
check("es gibt eine eigene Seite dafuer",
      "def masken_bildschirm" in quelle_f,
      "ueber tausend Masken lassen sich nicht mit links/rechts durchblaettern")
check("sie wird beim Start angewandt",
      "maske_anwenden(self.fb, maske_pfad_oder_leer())" in quelle_f)
check("und ein Absturz dort schaltet sie ab",
      "self.fb.maske = None" in quelle_f.split("masken_bildschirm CRASH")[1]
      [:300] if "masken_bildschirm CRASH" in quelle_f else False)

# ---------------------------------------------------------------------------
print()
print("Test 7: die ORDNERSTRUKTUR, nicht eine Liste aus 1207 Zeilen")
# ---------------------------------------------------------------------------
# NACHGEREICHT IN BUILD 227, auf Zuruf des Nutzers: "lochmasken in
# unterordner anzeigen sonst zuviel auswahl, die ordnerstruktur wie sie
# dort selbst angezeigt ist". MiSTers Sammlung ist bereits sortiert -
# diese Ordnung ist die Arbeit von jemandem, der die Masken kennt.
with tempfile.TemporaryDirectory() as tmp:
    gut = "v2\n1,1\n407\n"
    for rel in ("Complex/CRT Styles/Sony PVM.txt",
                "Complex/CRT Styles/Commodore 1084.txt",
                "Complex/Fein/Aperture.txt",
                "Simple/Scanlines.txt",
                "Direkt.txt",
                "Ohne Masken/liesmich.md"):
        voll = os.path.join(tmp, rel)
        os.makedirs(os.path.dirname(voll), exist_ok=True)
        open(voll, "w").write(gut)

    wurzel = M.masken_eintraege("", tmp)
    check("die Wurzel zeigt Ordner und lose Dateien",
          [e[1] for e in wurzel] == ["Complex", "Simple", "Direkt"],
          "%r" % ([e[1] for e in wurzel],))
    check("Ordner stehen VORN", wurzel[0][0] is True and wurzel[-1][0] is False)
    check("ein Ordner sagt, wieviel darin liegt",
          wurzel[0][3] == 3, "%r" % (wurzel[0][3],))
    check("ein Ordner OHNE Maske faellt weg",
          all(e[1] != "Ohne Masken" for e in wurzel),
          "sonst laeuft man in eine Sackgasse")

    tiefer = M.masken_eintraege("Complex", tmp)
    check("eine Ebene tiefer stehen die Unterordner",
          [e[1] for e in tiefer] == ["CRT Styles", "Fein"],
          "%r" % ([e[1] for e in tiefer],))
    blatt = M.masken_eintraege("Complex/CRT Styles", tmp)
    check("und ganz unten die Masken, alphabetisch",
          [e[1] for e in blatt] == ["Commodore 1084", "Sony PVM"],
          "%r" % ([e[1] for e in blatt],))
    check("der Pfad eines Blattes ist relativ zur Wurzel",
          blatt[0][2] == os.path.join("Complex/CRT Styles",
                                      "Commodore 1084.txt"),
          "%r" % (blatt[0][2],))
    check("und er laesst sich auch wirklich lesen",
          M.maske_lesen(os.path.join(tmp, blatt[0][2])) is not None)

    check("ein Ordner, den es nicht gibt, liefert eine leere Liste",
          M.masken_eintraege("gibt/es/nicht", tmp) == [])

# DER WEG HINAUF. Ohne ihn kaeme man in einen Ordner hinein und nicht
# wieder heraus - und genau das waere schlimmer als die lange Liste.
check("eine Ebene hoch aus zwei Ebenen",
      M.oberordner("Complex/CRT Styles") == "Complex")
check("eine Ebene hoch aus einer", M.oberordner("Complex") == "")
check("und ueber die Wurzel hinaus geht es nicht",
      M.oberordner("") == "")

check("der Bildschirm baut die Liste je EBENE",
      "MASKEN.ebene(ordner, {" in quelle_f,
      "und zwar in fe/masken.py, nicht in der Zeichenschleife")
check("Zurueck geht erst an der Wurzel aus der Seite heraus",
      "if ordner:" in quelle_f.split("elif akt in (\"back\", \"exit\")")[1]
      [:400], "sonst waere man aus Versehen draussen")
check("und der Cursor landet auf dem Ordner, aus dem man kommt",
      quelle_f.count('if e[0] in ("ordner", "presets")') == 2,
      "sonst sucht man ihn in einer langen Liste wieder")
check("die flache Liste ist WEG, nicht nur ungenutzt",
      not hasattr(M, "masken_dateien"),
      "zwei Wege in dieselbe Sammlung sind einer zuviel")

# ---------------------------------------------------------------------------
print()
print("Test 8: MiSTers PRESETS - die kuerzeste Antwort auf 'zuviel Auswahl'")
# ---------------------------------------------------------------------------
# NACHGESCHAUT AUF ZURUF DES NUTZERS: "die sachen dafuer liegen in ordner
# /media/fat/Presets einmal nachschauen bitte". Ein Preset ist eine
# winzige INI mit einem ganzen Satz Videoeinstellungen. Die Filterzeilen
# gehen MiSTers Scaler an und uns nichts - die Zeile "mask=" dagegen
# nennt genau eine Datei aus /media/fat/Shadow_Masks.
with tempfile.TemporaryDirectory() as tmp:
    mk = os.path.join(tmp, "masks")
    pr = os.path.join(tmp, "presets")
    os.makedirs(os.path.join(mk, "Complex", "CRT Styles"))
    os.makedirs(pr)
    open(os.path.join(mk, "Complex", "CRT Styles", "Sony PVM.txt"),
         "w").write("v2\n1,1\n407\n")

    def _preset(name, inhalt):
        open(os.path.join(pr, name), "w").write(inhalt)

    _preset("Sony PVM 1080p.ini",
            "# Kommentar\n[Video]\nhfilter=Upscaling/lanczos2_10.txt\n"
            "vfilter=same\ngamma=off\n"
            "mask=Complex/CRT Styles/Sony PVM.txt\nmaskmode=1x\n")
    _preset("Mit Praefix.ini",
            "mask=Shadow_Masks/Complex/CRT Styles/Sony PVM.txt\n")
    _preset("Nur Filter.ini", "vfilter=same\nmask=off\n")
    _preset("Zeigt ins Leere.ini", "mask=Gibt/Es/Nicht.txt\n")
    _preset("keine_ini.txt", "mask=Complex/CRT Styles/Sony PVM.txt\n")

    gefunden = M.preset_masken(pr, mk)
    namen = [e[0] for e in gefunden]
    check("ein Preset mit Maske wird gefunden", "Sony PVM 1080p" in namen,
          "%r" % (namen,))
    check("auch mit vorangestelltem Ordner", "Mit Praefix" in namen)
    check("'mask=off' faellt weg", "Nur Filter" not in namen,
          "ein Eintrag, der nichts tut, ist schlimmer als keiner")
    check("eine Maske, die nicht da ist, faellt weg",
          "Zeigt ins Leere" not in namen)
    check("und was keine .ini ist, wird gar nicht angefasst",
          "keine_ini" not in namen)
    check("der Pfad zeigt auf die echte Datei",
          os.path.isfile(os.path.join(mk, gefunden[0][1])))
    check("kein Preset-Ordner heisst: leere Liste, kein Absturz",
          M.preset_masken(os.path.join(tmp, "weg"), mk) == [])
    check("der Ordner ist MiSTers eigener",
          M.PRESETS_DIR == "/media/fat/Presets")

check("geoeffnet werden sie wie ein Ordner",
      'if art in ("ordner", "presets"):' in quelle_f)

# ---------------------------------------------------------------------------
print()
print("Test 10: DIE VIER MODI - 1x, 2x, gedreht (Build 228)")
# ---------------------------------------------------------------------------
# ZURUF DES NUTZERS: "bei denn masken ist mir noch aufgefallen das man
# mehrere optionen hat shadow mask 1x, shadow mask 2x, shadow mask 1x
# rotated und shadow mask 2x rotated". Das sind MiSTers eigene vier
# Einstellungen, und beide Umformungen passieren EINMAL beim Laden -
# danach rechnet C genau wie vorher.
check("es sind genau diese vier",
      M.MODI == ("1x", "2x", "1x_gedreht", "2x_gedreht"), "%r" % (M.MODI,))

# Ein Muster, in dem jede Zelle eindeutig ist: 2 breit, 1 hoch,
# links Rot, rechts Gruen.
ROH = (2, 1, [16, 0, 0,  0, 16, 0], 0, "Probe")

check("1x laesst alles, wie es ist",
      M.modus_anwenden(ROH, "1x") == ROH)

gedreht = M.modus_anwenden(ROH, "1x_gedreht")
check("gedreht tauscht Breite und Hoehe", gedreht[:2] == (1, 2),
      "%r" % (gedreht[:2],))
check("aus nebeneinander wird uebereinander",
      gedreht[2] == [16, 0, 0,  0, 16, 0],
      "oben Rot, darunter Gruen - %r" % (gedreht[2],))

doppelt = M.modus_anwenden(ROH, "2x")
check("2x verdoppelt beide Kanten", doppelt[:2] == (4, 2),
      "%r" % (doppelt[:2],))
check("jede Zelle deckt jetzt 2x2 Punkte",
      doppelt[2][:12] == [16, 0, 0, 16, 0, 0, 0, 16, 0, 0, 16, 0]
      and doppelt[2][12:] == doppelt[2][:12],
      "zweite Zeile muss der ersten gleichen")

beides = M.modus_anwenden(ROH, "2x_gedreht")
check("2x gedreht ist beides", beides[:2] == (2, 4), "%r" % (beides[:2],))

check("Name und Aufloesung bleiben dran",
      beides[3:] == ROH[3:], "%r" % (beides[3:],))
check("zweimal drehen ergibt das Muster zurueck",
      M._gedreht(M._gedreht(ROH)) == ROH,
      "sonst stimmt die Reihenfolge der Zellen nicht")

# DAS IST DER PUNKT DER GANZEN SACHE: die Umformung darf nur das
# MUSTER aendern, nie die Faktoren - sonst stuende in der Tabelle
# etwas, das C ablehnt (erlaubt sind 0..31).
for name in M.MODI:
    um = M.modus_anwenden((2, 2, [31, 0, 16, 7, 8, 9,
                                  0, 31, 2, 5, 16, 16], 0, "x"), name)
    check("%-12s haelt alle Faktoren in 0..31" % name,
          all(0 <= w <= 31 for w in um[2])
          and len(um[2]) == um[0] * um[1] * 3,
          "%d Werte fuer %dx%d" % (len(um[2]), um[0], um[1]))

check("und 2x bleibt unter der C-Grenze von 64",
      M.modus_anwenden((16, 16, [16] * 768, 0, "x"), "2x_gedreht")[0] == 32,
      "16x16 ist die groesste Maske, 2x macht 32x32")

# Der eingestellte Modus ueberlebt - und ein Unfug darin nicht.
import tempfile as _tf                                      # noqa: E402
with _tf.TemporaryDirectory() as tmp:
    _alt = M.MODUS_FILE
    try:
        M.MODUS_FILE = os.path.join(tmp, "maske_modus")
        check("ohne Datei ist es 1x", M.modus_lesen() == "1x")
        M.modus_schreiben("2x_gedreht")
        check("und was geschrieben wurde, kommt zurueck",
              M.modus_lesen() == "2x_gedreht")
        open(M.MODUS_FILE, "w").write("3x_kopfueber")
        check("Unfug in der Datei faellt auf 1x zurueck",
              M.modus_lesen() == "1x",
              "lieber die Vorgabe als eine Maske, die C ablehnt")
        M.modus_schreiben("gibtsnicht")
        check("und schreiben laesst sich auch nur Gueltiges",
              M.modus_lesen() == "1x")
    finally:
        M.MODUS_FILE = _alt

check("die Moduszeile steht im Bildschirm",
      '"modus"' in quelle_f and "MASKEN.modus_weiter(modus" in quelle_f)
# Gesucht wird IM MASKENBILDSCHIRM, nicht irgendwo in frontend.py -
# "links/rechts" kommt in mehreren Seiten vor (Cores zum Beispiel).
_seite = quelle_f.split("def masken_bildschirm")[1].split("\n    def ")[0]
check("links/rechts dreht dort den Modus statt an/aus",
      'if art == "modus":' in _seite.split('elif akt in ("left", "right")')
      [1][:500],
      "auf jeder anderen Zeile bleibt es der An/Aus-Schalter")
check("und OK tut auf der Zeile dasselbe",
      'if art == "modus":' in _seite.split('elif akt in ("select", "ok")')
      [1][:300],
      "wer OK drueckt, erwartet keine Auswahl einer Zeile ohne Datei")
check("und er wird beim Verlassen gespeichert",
      "MASKEN.modus_schreiben(modus)" in quelle_f)

# ---------------------------------------------------------------------------
print()
print("Test 9: DER WEG DURCH DEN BAUM, wirklich durchlaufen")
# ---------------------------------------------------------------------------
# Hier wird nicht im Quelltext gesucht, sondern navigiert. ebene() steht
# genau deshalb in fe/masken.py und nicht in der Zeichenschleife: was
# oben steht, was nach unten fuehrt und wie der Weg zurueck aussieht,
# soll pruefbar sein, ohne einen Bildschirm zu bauen.
with tempfile.TemporaryDirectory() as tmp:
    mk = os.path.join(tmp, "masks")
    pr = os.path.join(tmp, "presets")
    os.makedirs(os.path.join(mk, "Complex", "CRT Styles"))
    os.makedirs(os.path.join(mk, "Simple"))
    os.makedirs(pr)
    for rel in ("Complex/CRT Styles/Sony PVM.txt",
                "Complex/CRT Styles/Commodore 1084.txt",
                "Simple/Scanlines.txt"):
        open(os.path.join(mk, rel), "w").write("v2\n1,1\n407\n")
    open(os.path.join(pr, "Sony PVM 1080p.ini"), "w").write(
        "mask=Complex/CRT Styles/Sony PVM.txt\n")

    TEXTE = {"zurueck": "zurueck", "keine": "keine", "presets": "Presets"}

    def _ebene(ordner):
        return M.ebene(ordner, TEXTE, mk, pr)

    wurzel = _ebene("")
    check("oben steht 'keine'", wurzel[0][0] == "keine")
    check("danach die Presets", wurzel[1][0] == "presets",
          "%r" % ([e[0] for e in wurzel],))
    check("und KEIN Weg nach oben, wo keiner hinfuehrt",
          all(e[0] != "hoch" for e in wurzel))

    # Hinein in die Presets und wieder heraus.
    presets = _ebene(wurzel[1][2])
    check("die Presetebene fuehrt zurueck", presets[0][0] == "hoch")
    check("und enthaelt nur Masken",
          [e[0] for e in presets[1:]] == ["datei"],
          "%r" % ([e[0] for e in presets],))
    check("von dort geht es zur Wurzel",
          M.oberordner(wurzel[1][2]) == "")

    # Zwei Ebenen hinunter und Schritt fuer Schritt zurueck.
    tief = [e for e in wurzel if e[0] == "ordner"][0][2]
    stufe1 = _ebene(tief)
    check("ein Ordner fuehrt in einen Ordner", stufe1[1][0] == "ordner",
          "%r" % ([e[0] for e in stufe1],))
    stufe2 = _ebene(stufe1[1][2])
    check("und der zu den Masken",
          [e[0] for e in stufe2[1:]] == ["datei", "datei"],
          "%r" % ([e[0] for e in stufe2],))
    check("zurueck geht es Stufe fuer Stufe",
          M.oberordner(stufe1[1][2]) == tief
          and M.oberordner(tief) == "")

    # Und die Wahl am Ende ist ein Pfad, der sich lesen laesst.
    wahl = stufe2[1][2]
    check("die gewaehlte Maske laesst sich lesen",
          M.maske_lesen(os.path.join(mk, wahl)) is not None, wahl)

    # OHNE Presets verschwindet die Zeile - und nur sie.
    leer = M.ebene("", TEXTE, mk, os.path.join(tmp, "weg"))
    check("ohne Presetordner steht die Zeile nicht da",
          all(e[0] != "presets" for e in leer),
          "%r" % ([e[0] for e in leer],))
    check("der Rest bleibt unveraendert",
          [e[0] for e in leer] == ["keine", "ordner", "ordner"],
          "%r" % ([e[0] for e in leer],))

print()
if fails:
    print("FEHLGESCHLAGEN (%d):" % len(fails))
    for f in fails:
        print("  - %s" % f)
    sys.exit(1)
print("Alles in Ordnung.")
