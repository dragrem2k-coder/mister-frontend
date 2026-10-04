#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Das eigene Hintergrundbild (Build 235).

NUTZERWUNSCH: "wie aufwendig ist es ein background bild zu integrieren?
das benutzer ihr gewuenschtes background bild selbst in einen ordner
legen koennen ... die performence soll dadurch aber nicht
beeintraechtigt werden!"

DIE PERFORMANCE-ZUSAGE IST DER KERN DIESES TESTS, und sie ist
ueberpruefbar statt behauptet: fb.clear() kopiert SCHON HEUTE einen
Vollbildpuffer, weil die "einfarbige" Flaeche die Vignette traegt.
Dasselbe gilt fuer _restore_row_bg() und _bg_fill() beim Scrollen. Was
in dieser Vorlage steht, ist dem Kopieren egal.

Test 4 misst genau das: dieselbe Zahl von clear()-Aufrufen einmal mit
Farbvorlage und einmal mit Bildvorlage. Weicht es um mehr als ein
Drittel ab, ist die Zusage gebrochen und der Test rot.

DIE ZWEITE GEFAHR ist eine falsch grosse Vorlage. fb.clear() macht
buf[:] = bg - eine Vorlage mit falscher Schrittweite oder Groesse
verschoebe das ganze Bild, und zwar still. Test 2 wirft deshalb jede
Vorlage ab, die nicht genau passt.

Ausfuehren:
    python3 tools/test_hintergrund.py
"""
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H          # noqa: E402

import fe.hintergrund as HG   # noqa: E402
import fe.art as A            # noqa: E402
import fe.settings as S       # noqa: E402

_uhr = time.perf_counter      # der Pruefstand friert monotonic() ein

fm = H.fm
fails = []
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def check(name, ok, info=""):
    print(("  OK   " if ok else "  FEHL ") + name
          + (("  " + str(info)) if info else ""))
    if not ok:
        fails.append(name)


def _png(pfad, b, h):
    """Ein kleines, echtes PNG schreiben - kein nachgebautes Format."""
    pix = bytearray()
    for y in range(h):
        for x in range(b):
            pix += bytes(((x * 7) % 256, (y * 5) % 256,
                          ((x + y) * 3) % 256, 255))
    import fe.bench as B
    daten = B.testbild_png(bytes(pix), b, h)
    with open(pfad, "wb") as f:
        f.write(daten)
    return pix


# ---------------------------------------------------------------------------
print("Test 1: aus einem Bild wird eine Bildschirmvorlage")
# ---------------------------------------------------------------------------
H.set_screen(1920, 1080)
fb = fm.Framebuffer()
with tempfile.TemporaryDirectory() as tmp:
    klein = os.path.join(tmp, "klein.png")
    _png(klein, 320, 200)

    v = HG.vorlage_bauen(klein, fb.width, fb.height, 0, ART=A,
                         stride=fb.stride)
    check("ein zu kleines Bild wird hochgerechnet", v is not None)
    check("und hat genau die Groesse des Bildspeichers",
          v is not None and len(v) == fb.stride * fb.height,
          "%d statt %d" % (len(v) if v else -1, fb.stride * fb.height))

    # DAS FUELLENDE MASS: keine Balken. Ein 320x200-Bild auf 1920x1080
    # muss auf der HOEHE anschlagen, nicht auf der Breite.
    # 320x200 ist BREITER als 16:9 nicht - es ist 1,6 gegen 1,78. Auf
    # die Breite gezogen kommt 1200 heraus, also mehr als 1080: der
    # Ueberstand faellt oben und unten weg. Genau so soll es sein -
    # Balken gibt es nicht.
    check("gefuellt wird, nicht eingepasst",
          HG._fuellend(320, 200, 1920, 1080) == (1920, 1200),
          "%r" % (HG._fuellend(320, 200, 1920, 1080),))
    check("ein hochkantes Bild fuellt erst recht",
          HG._fuellend(200, 320, 1920, 1080) == (1920, 3072),
          "%r" % (HG._fuellend(200, 320, 1920, 1080),))
    check("und ein sehr breites schlaegt auf der Hoehe an",
          HG._fuellend(4000, 1000, 1920, 1080) == (4320, 1080),
          "%r" % (HG._fuellend(4000, 1000, 1920, 1080),))
    check("und ein passendes Bild bleibt, wie es ist",
          HG._fuellend(1920, 1080, 1920, 1080) == (1920, 1080))
    check("eine Groesse von null stuerzt nicht ab",
          HG._fuellend(0, 0, 1920, 1080) == (1920, 1080))

    # ---------------------------------------------------------------
    print()
    print("Test 2: eine falsche Vorlage wird ABGEWIESEN")
    # ---------------------------------------------------------------
    # fb.clear() macht buf[:] = bg. Eine Vorlage mit falscher Groesse
    # verschoebe das ganze Bild, und zwar still.
    fb.hintergrund_setzen(None, None)
    check("zu kurz wird abgewiesen",
          fb.hintergrund_setzen(bytearray(100), "x") is False
          and fb.hintergrund is None)
    check("zu lang ebenso",
          fb.hintergrund_setzen(bytearray(fb.stride * fb.height + 4), "x")
          is False and fb.hintergrund is None)
    check("genau passend wird genommen",
          fb.hintergrund_setzen(v, "probe") is True
          and fb.hintergrund is not None)
    check("und der Puffer behaelt seine Laenge",
          (fb.clear((0, 0, 0)), len(fb.buf))[1] == fb.stride * fb.height)

    # ---------------------------------------------------------------
    print()
    print("Test 3: der Wechsel kommt WIRKLICH an")
    # ---------------------------------------------------------------
    # Ohne das Bild im Schluessel zeigten _restore_row_bg() und
    # _bg_fill() nach einem Wechsel weiter den alten Hintergrund.
    fb.hintergrund_setzen(None, None)
    fb.clear((10, 20, 30))
    einfarbig = bytes(fb.buf[:4000])
    fb.hintergrund_setzen(v, "probe")
    fb.clear((10, 20, 30))
    mit_bild = bytes(fb.buf[:4000])
    check("mit Bild sieht der Hintergrund anders aus",
          einfarbig != mit_bild)
    check("das Bild steckt im Cache-Schluessel",
          fb.bg_key((10, 20, 30))[-1] == "probe",
          "%r" % (fb.bg_key((10, 20, 30)),))
    fb.hintergrund_setzen(None, None)
    fb.clear((10, 20, 30))
    check("und zurueck ist wieder einfarbig",
          bytes(fb.buf[:4000]) == einfarbig,
          "sonst bleibt das alte Bild still stehen")

    quelle = open(os.path.join(_REPO, "frontend", "fe", "framebuffer.py"),
                  encoding="utf-8").read()
    # _restore_row_bg() und _bg_fill() stehen in frontend.py und holen
    # ihre Zeilen aus demselben _rowcache - ueber bg_key(). Das ist der
    # Grund, warum das Bild dort automatisch ankommt, ohne dass eine
    # dieser Funktionen davon weiss.
    _qf = open(H.FRONTEND_PY, encoding="utf-8", errors="replace").read()
    check("_restore_row_bg und _bg_fill gehen ueber denselben Schluessel",
          _qf.count("fb._rowcache.get(fb.bg_key(") >= 3,
          "sonst fuellen sie einfarbig, waehrend clear() das Bild zeigt")
    check("und bg_key kennt das Bild",
          "self.hintergrund_kennung)" in quelle,
          "ohne das zeigten sie nach einem Wechsel weiter das alte")

    # ---------------------------------------------------------------
    print()
    print("Test 4: DIE ZUSAGE - im Zeichenweg kostet es nichts")
    # ---------------------------------------------------------------
    fb.hintergrund_setzen(None, None)
    fb.clear((12, 12, 18))
    t0 = _uhr()
    for _ in range(40):
        fb.clear((12, 12, 18))
    farbe_ms = (_uhr() - t0) * 1000.0 / 40
    fb.hintergrund_setzen(v, "probe")
    fb.clear((12, 12, 18))
    t0 = _uhr()
    for _ in range(40):
        fb.clear((12, 12, 18))
    bild_ms = (_uhr() - t0) * 1000.0 / 40
    check("clear() mit Bild kostet nicht mehr als mit Farbe",
          bild_ms <= farbe_ms * 1.35 + 0.05,
          "Farbe %.3f ms, Bild %.3f ms" % (farbe_ms, bild_ms))
    check("und die Vorlage wird nicht je Aufruf neu gebaut",
          fb._rowcache.get(fb.bg_key((12, 12, 18))) is not None,
          "sonst waere jedes Bild ein Neuaufbau")

    # ---------------------------------------------------------------
    print()
    print("Test 5: Abdunkeln - einmal, nicht je Bild")
    # ---------------------------------------------------------------
    hell = HG.vorlage_bauen(klein, 64, 48, 0, ART=A, stride=64 * 4)
    dunkel = HG.vorlage_bauen(klein, 64, 48, 50, ART=A, stride=64 * 4)
    check("abgedunkelt ist dunkler",
          sum(dunkel[0::4]) < sum(hell[0::4]),
          "%d gegen %d" % (sum(dunkel[0::4]), sum(hell[0::4])))
    check("und zwar ungefaehr um die Haelfte",
          abs(sum(dunkel[0::4]) - sum(hell[0::4]) // 2)
          <= max(1, sum(hell[0::4]) // 20))
    check("die Deckkraft bleibt unberuehrt",
          bytes(dunkel[3::4]) == bytes(hell[3::4]),
          "sonst waere der Hintergrund halb durchsichtig")
    check("0 Prozent aendert nichts",
          bytes(HG.vorlage_bauen(klein, 64, 48, 0, ART=A, stride=64 * 4))
          == bytes(hell))
    check("abgedunkelt wird in fe/hintergrund.py, nicht im Zeichenweg",
          "_abdunkeln(vorlage, dim)" in open(
              os.path.join(_REPO, "frontend", "fe", "hintergrund.py"),
              encoding="utf-8").read())

    # ---------------------------------------------------------------
    print()
    print("Test 6: alles, was schiefgehen kann, endet in None")
    # ---------------------------------------------------------------
    check("kein Pfad", HG.vorlage_bauen("", 100, 100, 0, ART=A) is None)
    check("eine Datei, die es nicht gibt",
          HG.vorlage_bauen(os.path.join(tmp, "weg.png"), 100, 100, 0,
                           ART=A) is None)
    kaputt = os.path.join(tmp, "kaputt.png")
    open(kaputt, "wb").write(b"das ist kein Bild")
    check("eine kaputte Datei",
          HG.vorlage_bauen(kaputt, 100, 100, 0, ART=A) is None)
    check("ohne Bildleser", HG.vorlage_bauen(klein, 100, 100, 0,
                                             ART=None) is None)

    # ---------------------------------------------------------------
    print()
    print("Test 7: der Baum, der Schalter und die Auswahl")
    # ---------------------------------------------------------------
    # EIGENER Ordner: oben liegen schon die Probebilder aus Test 1 und
    # 6, und eine Zaehlung, die die mitzaehlt, prueft nichts.
    baum = os.path.join(tmp, "baum")
    os.makedirs(os.path.join(baum, "Natur"))
    _png(os.path.join(baum, "Natur", "wald.png"), 32, 24)
    _png(os.path.join(baum, "oben.png"), 32, 24)
    open(os.path.join(baum, "liesmich.txt"), "w").write("x")
    tmp = baum

    wurzel = HG.ebene("", {"zurueck": "zurueck", "keine": "keines"}, tmp)
    check("oben steht 'keines'", wurzel[0][0] == "keine")
    check("dann der Ordner, dann die Datei",
          [e[0] for e in wurzel[1:]] == ["ordner", "datei"],
          "%r" % ([e[0] for e in wurzel],))
    check("eine .txt zaehlt nicht mit",
          all("liesmich" not in e[1] for e in wurzel))
    tiefer = HG.ebene("Natur", {"zurueck": "zurueck"}, tmp)
    check("eine Ebene tiefer fuehrt zurueck", tiefer[0][0] == "hoch")
    check("und zeigt das Bild", [e[0] for e in tiefer[1:]] == ["datei"])
    check("gezaehlt werden alle Endungen", HG.zaehlen(tmp) == 2,
          "%d" % HG.zaehlen(tmp))

# Auswahl und Schalter sind getrennt - wie bei der Maske.
check("es gibt eine Auswahl", hasattr(S, "hintergrund_lesen"))
check("einen eigenen Schalter", hasattr(S, "toggle_hintergrund"))
check("und eine Abdunklung", hasattr(S, "hintergrund_dim_lesen"))
check("alle drei sind getrennt",
      len({S.HINTERGRUND_FILE, S.HINTERGRUND_AUS_FLAG,
           S.HINTERGRUND_DIM_FILE}) == 3,
      "wer kurz abschaltet, soll seine Auswahl behalten")
check("der Ordner liegt bei den eigenen Einstellungen",
      HG.HINTERGRUND_DIR.startswith("/media/fat/frontend/"),
      "geschrieben wird nur dort - MiSTers Ordner fassen wir nicht an")

# ---------------------------------------------------------------------------
print()
print("Test 8: es wird kein Bild mitgeliefert")
# ---------------------------------------------------------------------------
gefunden = []
for w, _d, dateien in os.walk(_REPO):
    if ".git" in w or "node_modules" in w:
        continue
    if os.path.basename(w).lower() in ("backgrounds", "hintergrund"):
        gefunden.extend(os.path.join(w, d) for d in dateien)
check("kein Hintergrundbild im Paket", not gefunden,
      "%s" % (gefunden[:2] if gefunden else ""))

qf = open(H.FRONTEND_PY, encoding="utf-8", errors="replace").read()
check("es gibt eine eigene Seite dafuer",
      "def hintergrund_bildschirm" in qf)
check("sie wird beim Start angewandt",
      "hintergrund_anwenden(self.fb)" in qf)
check("und ein Absturz dort schaltet es ab",
      "self.fb.hintergrund_setzen(None, None)" in
      qf.split("hintergrund_bildschirm CRASH")[1][:300]
      if "hintergrund_bildschirm CRASH" in qf else False)
check("der Menueeintrag ist verdrahtet",
      '"hintergrund"' in open(os.path.join(_REPO, "frontend", "fe",
                                           "menu.py"),
                              encoding="utf-8").read())
check("ein ausgetauschtes Bild wird erkannt",
      "marke = int(os.path.getmtime(pfad))" in qf,
      "sonst zeigte es unter demselben Namen still das alte")

# ---------------------------------------------------------------------------
print()
print("Test 9: das Abdunkeln laeuft in C, nicht Byte fuer Byte in Python")
# ---------------------------------------------------------------------------
# DAS WAR DIE URSACHE der gemeldeten Wartezeit: "wenn ich mehrere
# background bilder in denn ordner packe und diese dann durchklicke
# dauert das immer sehr lang bis es angezeigt wird."
#
# tools/diag_hintergrundbild.py hat den Weg zerlegt - Skalieren 0 bis
# 26 ms, Zuschneiden 2 bis 5 ms, Abdunkeln 214 bis 233 ms. Das waren
# 90 bis 98 Prozent, und es war eine Python-Schleife ueber 8,3
# Millionen Bytes.
_hq = open(os.path.join(_REPO, "frontend", "fe", "hintergrund.py"),
           encoding="utf-8").read()
_fkt = _hq.split("def _abdunkeln")[1].split("\ndef ")[0]
# NUR DER CODE, NICHT DIE ERKLAERUNG: dort steht die alte Schreibweise
# wortwoertlich drin, damit nachlesbar bleibt, was der Fund war. Eine
# Pruefung, die darauf anspringt, prueft die Dokumentation.
_code = _fkt.split('"""')[2] if _fkt.count('"""') >= 2 else _fkt
check("es benutzt translate()", ".translate(tab)" in _code)
check("und KEINE Schleife je Byte", "for b in" not in _code,
      "gemessen 14,6x schneller - 214 ms auf 15 ms")
check("die Deckkraft wird nicht uebersetzt", "[k::4]" in _code,
      "das vierte Byte ist die Deckkraft und bleibt")

# GLEICHWERTIGKEIT GEGEN DIE ALTE SCHREIBWEISE, Byte fuer Byte. Ein
# Unterschied faellt nicht auf - das Bild sieht nur etwas anders aus.
def _alt_abdunkeln(pix, prozent):
    """Die Fassung aus Build 235, nur zum Vergleich."""
    if not prozent:
        return pix
    f = max(0, min(100, int(prozent)))
    tab = bytes(bytearray(((i * (100 - f)) // 100) for i in range(256)))
    aus = bytearray(pix)
    aus[0::4] = bytes(bytearray(tab[b] for b in aus[0::4]))
    aus[1::4] = bytes(bytearray(tab[b] for b in aus[1::4]))
    aus[2::4] = bytes(bytearray(tab[b] for b in aus[2::4]))
    return aus


# Alle 256 Bytewerte, in allen vier Stellungen.
probe = bytearray(bytes(bytearray(range(256))) * 64)
for dim in (0, 1, 25, 40, 55, 70, 99, 100):
    a = _alt_abdunkeln(bytearray(probe), dim)
    b = HG._abdunkeln(bytearray(probe), dim)
    check("%3d %% ist bitgenau wie vorher" % dim, bytes(a) == bytes(b))

# ---------------------------------------------------------------------------
print()
print("Test 10: die Teilzeiten stehen im Log")
# ---------------------------------------------------------------------------
# WARUM DAS EINE PRUEFUNG WERT IST: nach der Aenderung an _abdunkeln()
# ist der groesste Posten das DEKODIEREN, und den hat dieses Modul
# nicht in der Hand. Ohne Zahl vom Geraet waere jeder weitere Schritt
# geraten - und ein Zwischenspeicher fuer fertige Vorlagen war beim
# Bau von Build 240 schon fertig und ist nach der Messung wieder
# herausgeflogen, weil er LANGSAMER war als neu rechnen (JPEG
# dekodieren 33,9 ms gegen PNG 19,0 ms).
_vb = _hq.split("def vorlage_bauen")[1]
check("die Gesamtzeit wird gemessen", "_t.monotonic()" in _vb)
for teil in ("dekodieren", "skalieren", "zuschneiden", "abdunkeln"):
    check("das Log nennt %s" % teil, teil in _vb)
check("und es ist EINE Zeile je Bildwechsel, nicht je Teil",
      _vb.count("LOG(\"Hintergrund geladen") == 1,
      "vier Zeilen waeren vier Dateizugriffe fuer eine Auskunft")

print()
if fails:
    print("FEHLGESCHLAGEN (%d):" % len(fails))
    for f in fails:
        print("  - %s" % f)
    sys.exit(1)
print("Alles in Ordnung.")
