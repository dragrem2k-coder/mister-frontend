#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Der Rahmen um das Cover in EINEM Aufruf (Build 241).

DIE FRAGE VOM GERAET: "wenn ich in arcade ordner gehe mit cover wechsel
anzeigen und nach unten gedrueckt scrolle, kann man da noch was an
anzeigezeit bzw geschwindigkeit rausholen?"

DER BEWEIS, DASS AUFRUFE TEUER SIND, steht in seinem eigenen Bench, in
Abschnitt I.3:

    60x40     Python 0.543 ms    C 0.489 ms
    697x3     Python 0.329 ms    C 0.318 ms

Beides sind winzige Flaechen, und beide kosten in C rund ein Drittel
bis eine halbe Millisekunde. Das ist nicht die Flaeche, das ist der
AUFRUF. Und "karten" zaehlt rect() mit: im Bericht vom 04.10. steht der
Posten in der Listenansicht mit 13,81 ms bei sechs Aufrufen je Schritt.

Der Rahmen um das Cover bestand aus VIER rect()-Aufrufen - derselbe
Fall, den Build 220 fuer den Kachelrahmen und den Platzhalterrahmen
schon zusammengefasst hat. Der Rahmen um das TATSAECHLICHE Cover war
dabei uebersehen worden.

WARUM DAS VORHER KEIN TEST GEFUNDEN HAT: der Pruefstand hat keine
Cover-Dateien. art bleibt None, der Rahmen wird gar nicht gezeichnet -
und damit war jede Messung an dieser Stelle blind. Dieser Test
SCHIEBT ein Cover UNTER, genauso wie tools/diag_cover_panel.py und
Abschnitt K des Bench.

Ausfuehren:
    python3 tools/test_fuellaufrufe.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H          # noqa: E402

import fe.art as ART          # noqa: E402
import fe.bench as BENCH      # noqa: E402
import fe.settings as S       # noqa: E402

fails = []
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QF = open(H.FRONTEND_PY, encoding="utf-8", errors="replace").read()
BQ = open(os.path.join(_REPO, "frontend", "fe", "bench.py"),
          encoding="utf-8").read()


def check(name, ok, info=""):
    print(("  OK   " if ok else "  FEHL ") + name
          + (("  " + str(info)) if info else ""))
    if not ok:
        fails.append(name)


def _cover_unterschieben(fest=None):
    """get_scaled() liefert ab jetzt ein erzeugtes Cover. fest=(b,h)
    haelt die Groesse konstant, sonst wechselt sie wie bei echten
    Boxarts."""
    echt = ART.ART.get_scaled
    zaehler = [0]

    def _ersatz(quelle, breite, hoehe, **k):
        zaehler[0] += 1
        if fest:
            aw, ah = fest
        else:
            aw = max(8, int(breite) - (zaehler[0] % 3) * 7)
            ah = max(8, int(hoehe) - (zaehler[0] % 4) * 5)
        return (aw, ah, bytes(bytearray([40, 90, 160, 0])) * aw * ah)

    ART.ART.get_scaled = _ersatz

    def _zurueck():
        ART.ART.get_scaled = echt

    return _zurueck


# ---------------------------------------------------------------------------
print("Test 1: der Rahmen ist EIN Aufruf, nicht vier")
# ---------------------------------------------------------------------------
_panel = QF.split("def draw_art_panel")[1].split("\n    def ")[0]
check("er geht ueber rect_viele", "fb.rect_viele((" in _panel)
check("und es stehen keine vier Einzelaufrufe mehr da",
      _panel.count("fb.rect(ax - 2 * s") == 0
      and _panel.count("fb.rect(ax + aw") == 0,
      "das war der Fall aus Build 220, nur an anderer Stelle")
check("rect_viele gibt es seit Build 220",
      "def rect_viele" in open(
          os.path.join(_REPO, "frontend", "fe", "framebuffer.py"),
          encoding="utf-8").read())

# ---------------------------------------------------------------------------
print()
print("Test 2: er zeichnet BITGENAU dasselbe")
# ---------------------------------------------------------------------------
# Das ist der eigentliche Punkt. Ein Rahmen, der um einen Bildpunkt
# anders liegt, faellt nicht auf - er sieht nur etwas anders aus.
H.set_screen(1920, 1080)
fe = H.make_frontend(page=1)
fb = fe.fb

for (ax, ay, aw, ah, s) in ((100, 50, 700, 900, 3),
                            (0, 0, 40, 40, 1),
                            (1900, 1060, 60, 60, 2),
                            (10, 10, 1, 1, 4),
                            (-5, -5, 50, 50, 2)):
    accent = (200, 60, 90)
    fb.clear((7, 9, 14))
    fb.rect(ax - 2 * s, ay - 2 * s, aw + 4 * s, 2 * s, accent)
    fb.rect(ax - 2 * s, ay + ah, aw + 4 * s, 2 * s, accent)
    fb.rect(ax - 2 * s, ay - 2 * s, 2 * s, ah + 4 * s, accent)
    fb.rect(ax + aw, ay - 2 * s, 2 * s, ah + 4 * s, accent)
    einzeln = bytes(fb.buf)

    fb.clear((7, 9, 14))
    fb.rect_viele(((ax - 2 * s, ay - 2 * s, aw + 4 * s, 2 * s),
                   (ax - 2 * s, ay + ah, aw + 4 * s, 2 * s),
                   (ax - 2 * s, ay - 2 * s, 2 * s, ah + 4 * s),
                   (ax + aw, ay - 2 * s, 2 * s, ah + 4 * s)), accent)
    zusammen = bytes(fb.buf)
    anders = sum(1 for a, b in zip(einzeln, zusammen) if a != b)
    check("Cover %dx%d an (%d,%d), Skala %d" % (aw, ah, ax, ay, s),
          einzeln == zusammen, "%d Bytes anders" % anders)

# ---------------------------------------------------------------------------
print()
print("Test 3: wieviele Fuellaufrufe macht ein Schritt MIT Cover?")
# ---------------------------------------------------------------------------
# OHNE COVER IST DIESE MESSUNG BLIND, und genau daran ist die
# Aenderung vorher vorbeigegangen: art bleibt None, der Rahmen wird
# nicht gezeichnet, und die vier Aufrufe tauchen in keiner Messung auf.
zurueck = _cover_unterschieben()
try:
    kat_i, kat_n, kat_name = BENCH._groesste_kategorie(fe)
    check("es gibt eine Kategorie zum Messen", kat_i is not None,
          "%r mit %d Eintraegen" % (kat_name, kat_n))
    fe.page = 1
    fe.cat_i = kat_i
    fe.nav_path = []

    _NAMEN = ("karte_mit_schatten", "rect_rounded_schatten",
              "rect_rounded", "rect", "rect_viele")
    gemessen = {}
    for ansicht in ("liste", "raster", "galerie"):
        try:
            fe.ansicht_setzen(ansicht)
        except Exception:                                # noqa: BLE001
            continue
        schritt = BENCH.schritt_funktion(fe, 1)
        schritt(0)                          # erst zeichnen (Build 239)
        spanne = BENCH.fenster_spanne(fe, 1)
        for i in range(6):
            schritt(i % spanne)

        zaehler = {"n": 0}
        tiefe = [0]
        echte = [(n, getattr(fb, n)) for n in _NAMEN if hasattr(fb, n)]

        def _haken(echt):
            def ersatz(*a, **k):
                if tiefe[0]:
                    return echt(*a, **k)
                zaehler["n"] += 1
                tiefe[0] += 1
                try:
                    return echt(*a, **k)
                finally:
                    tiefe[0] -= 1
            return ersatz

        for n, e in echte:
            setattr(fb, n, _haken(e))
        try:
            for i in range(12):
                schritt(i % spanne)
        finally:
            for n, e in echte:
                setattr(fb, n, e)
        gemessen[ansicht] = zaehler["n"] / 12.0
        print("   %-8s %.1f aeussere Fuellaufrufe je Schritt"
              % (ansicht, gemessen[ansicht]))

    # DIE GRENZE IST KEINE SCHOENE ZAHL, sondern der gemessene Stand:
    # fuenf in der Liste, einer im Raster, vier in der Galerie. Steigt
    # einer davon wieder, ist ein Aufruf dazugekommen - und auf dem
    # Geraet kostet jeder rund 0,40 ms.
    check("Liste: hoechstens 5 Aufrufe je Schritt",
          gemessen.get("liste", 99) <= 5.0,
          "%.1f - vor Build 241 waren es 8" % gemessen.get("liste", -1))
    check("Galerie: hoechstens 4", gemessen.get("galerie", 99) <= 4.0,
          "%.1f" % gemessen.get("galerie", -1))
    check("Raster: hoechstens 2", gemessen.get("raster", 99) <= 2.0,
          "%.1f" % gemessen.get("raster", -1))
finally:
    zurueck()

# ---------------------------------------------------------------------------
print()
print("Test 4: Abschnitt K misst das auf dem GERAET")
# ---------------------------------------------------------------------------
# Warum er noetig ist: nach dem Kostenmodell aus Abschnitt H und I
# muesste "karten" in der Listenansicht rund 3 ms kosten, im Bericht
# stehen 13,81. Zehn Millisekunden ohne Namen, in jedem Schritt - und
# auf diesem Rechner nicht nachstellbar, weil derselbe Schritt hier
# 1,4 statt 39 ms braucht.
check("es gibt einen Abschnitt K", "def _abschnitt_k" in BQ)
check("er haengt im Lauf", "_abschnitt_k(b, fe, S, A)" in BQ)
check("und ist abgesichert wie die anderen",
      "ABSCHNITT K ABGEBROCHEN" in BQ)
check("BENCH_VERSION wurde hochgezaehlt", BENCH.BENCH_VERSION >= 7,
      "%d" % BENCH.BENCH_VERSION)
_k = BQ.split("def _abschnitt_k")[1].split("\ndef ")[0]
check("er schiebt ein Cover unter", "_traeger.get_scaled = _cover" in _k,
      "ohne Cover waere er so blind wie die Messung vorher")
# BUILD 242: und er findet get_scaled auch dann, wenn ihm das MODUL
# uebergeben wird statt der Instanz. Im ersten Bericht mit Abschnitt K
# stand "kein Bild-Zwischenspeicher - uebersprungen": das Bench bekommt
# absichtlich das Modul (siehe frontend.py), get_scaled sitzt aber auf
# dem ArtCache darin. Der ganze Abschnitt lief lautlos ins Leere.
check("er findet den ArtCache auch im Modul",
      'getattr(A, "ART", None)' in _k,
      "sonst laeuft der Abschnitt lautlos ins Leere")
# DASS ES WIRKLICH ZURUECKGESETZT WIRD, prueft weiter unten der LAUF
# selbst (die Pruefung "danach liefert get_scaled wieder echte Cover").
# Hier nur, dass es im finally steht und nicht am Ende des try-Blocks -
# sonst bliebe das Frontend nach einem Abbruch mitten im Bench ohne
# echte Cover, und das waere ein Fehler, den niemand mehr mit dem
# Bench in Verbindung bringt.
_nach_cover = _k.split("_traeger.get_scaled = _cover", 1)[1]
_finally_teil = _nach_cover.split("finally:")[-1] if "finally:" in \
    _nach_cover else ""
check("und gibt es im finally zurueck",
      "_traeger.get_scaled = echt_scaled" in _finally_teil,
      "sonst bliebe das Frontend nach einem Abbruch ohne echte Cover")
check("die Haken werden auch im finally geloest",
      _k.split("finally:")[-1].count("setattr(fbo, n, _e)") >= 1)
check("er zaehlt nur den AEUSSERSTEN Aufruf", "if tiefe[0]:" in _k,
      "sonst stuende dieselbe Zeit dreimal da")

# Und er laeuft wirklich durch.
class Ber(object):
    def __init__(self):
        self.z = []

    def __call__(self, t=""):
        self.z.append(str(t))


_b = Ber()
try:
    BENCH._abschnitt_k(_b, fe, S, ART.ART)
    _lief = True
except Exception as e:                                   # noqa: BLE001
    _lief = False
    print("       %s: %s" % (type(e).__name__, e))
_text = "\n".join(_b.z)
check("Abschnitt K laeuft durch", _lief)
check("und nennt Aufrufe je Schritt", "Aufrufe je Schritt" in _text)
check("und die drei Ansichten", all(a in _text for a in
                                    ("liste", "raster", "galerie")))
check("danach liefert get_scaled wieder echte Cover",
      ART.ART.get_scaled.__name__ == "get_scaled",
      "%r" % (ART.ART.get_scaled.__name__,))
# Die Zeiten sind hier 0, weil der Pruefstand die Uhr einfriert (siehe
# tools/_harness.py) - auf dem Geraet laeuft sie. Das ist KEIN Fehler,
# und deshalb steht hier auch keine Pruefung auf Zeiten.
check("auf dem Pruefstand stehen dort Nullen - erwartet",
      "0.000 ms" in _text or "0.00 ms" in _text,
      "die Uhr ist eingefroren; auf dem Geraet laeuft sie")

# ---------------------------------------------------------------------------
print()
print("Test 5: zwei Berichtsfehler, die beim Messen auffielen")
# ---------------------------------------------------------------------------
check("'in N Zugriffen' wird nicht mehr auf 0 abgeschnitten",
      '"   (davon Karte %.2f in %.1f Zugriffen)"' in BQ,
      "es stand '3.35 ms in 0 Zugriffen' da - %d auf 0,7 ist 0")
check("die Wer-fragt-Zeilen nennen jetzt auch die ZEIT",
      "%5.1f/Schritt %6.2f ms" in BQ,
      "0,6 Zugriffe allein war nicht zu beurteilen")
check("und sie werden nach ZEIT sortiert, nicht nach Zahl",
      "key=lambda e: -e[1][1]" in BQ)

# ---------------------------------------------------------------------------
print()
print("Test 6: der kurze Weg im Cover-Panel (Build 244)")
# ---------------------------------------------------------------------------
# DER BEFUND KOMMT AUS ABSCHNITT K, Lauf vom 04.10. auf dem DE10-Nano:
#
#     karte_mit_schatten  769x945    8,295 ms je Schritt
#
# Beim gehaltenen Scrollen mit "Cover sofort" an wird das Cover
# uebersprungen, die Karte aber JEDEN Schritt komplett gefuellt -
# obwohl der Cover-Kasten genauso aussieht wie im Schritt davor:
# derselbe leere Kasten, derselbe Anfangsbuchstabe. Nur der Text
# darunter wechselt.
_p6 = QF.split("def draw_art_panel")[1].split("\n    def ")[0]
_p6_code = "\n".join(z for z in _p6.split("\n")
                     if not z.strip().startswith("#"))
check("es gibt den kurzen Weg", "_kurz = (" in _p6_code)
check("er haengt an drei Bedingungen",
      "full_redraw_gen" in _p6_code and "_panel_stand" in _p6_code
      and "_kasten" in _p6_code,
      "voller Aufbau dazwischen, Geometrie/Farben, Inhalt des Kastens")
check("die Kennung des Covers kommt vom PFAD, nicht von id()",
      "id(_pix0)" not in _p6_code and "_quelle_fuer_stand" in _p6_code,
      "CPython gibt die Adresse eines aufgeraeumten Objekts wieder aus")
check("er greift NUR ohne Cover",
      '_kasten_art == "marke"' in _p6_code,
      "mit Cover wechselt das Bild ohnehin jeden Schritt - dann gibt "
      "es nichts zu sparen, und der Vergleich kostete nur")
# GEAENDERT (Build 247): der Buchstabe steht NICHT mehr im Vergleich.
# Mit Cover muss der Inhalt des Kastens weiter mit hinein - dort
# wechselt das Bild wirklich.
check("der Inhalt zaehlt nur MIT Cover",
      "_kasten_inhalt = (_kasten[1:] if _kasten_art == \"bild\" else ())"
      in _p6_code,
      "ohne Cover ist es der Anfangsbuchstabe, und der darf wechseln")

# DER WEG SELBST: die Karte wird GEZEICHNET, nur der Kasten ausgespart.
check("ausgespart wird ueber den vorhandenen Mechanismus",
      "_kasten_luecke" in _p6_code
      and "aussparen=(_kasten_luecke if _kurz" in _p6_code,
      "karte_mit_schatten(aussparen=...) gibt es seit Build 234/238")
check("die Karte wird also weiter gezeichnet",
      _p6_code.count("fb.karte_mit_schatten(") == 1,
      "DAS war der Fehler des ersten Entwurfs - siehe unten")
check("und in den Kasten kommt nur noch der Buchstabe",
      "if _kurz:" in _p6_code.split("art_bottom = cy + cover_h")[0][-900:],
      "die Flaeche steht schon richtig da")

# ---------------------------------------------------------------------------
print()
print("Test 6b: warum die ganze Karte NICHT weggelassen werden darf")
# ---------------------------------------------------------------------------
# DER ERSTE ENTWURF HAT GENAU DAS GEMACHT - Karte weglassen, nur den
# Textblock malen. Gemessen sah es gut aus (gefuellt 2,71 auf 0,44 MB,
# geflippt 3,62 auf 1,13 MB). Dann hat tools/test_rechteck_flip.py ihn
# ueberfuehrt: 69 Bytes Unterschied zwischen Puffer und Schirm, an der
# unteren rechten Kartenecke.
#
# DER GRUND: die Umgebung der Eckenrundung wird NICHT von der Karte
# gefuellt - sie liegt ausserhalb der Kurve. Ohne den Kartenaufruf
# blieb dort, was der vorige Schritt hinterlassen hatte, und ein
# voller Aufbau malt dort etwas anderes. Siebzehn Bildpunkte in einer
# Ecke; genau die Sorte Rest, die dieses Projekt fuenfmal gejagt hat
# (Build 80, 122, 125, 128, 237).
check("die Begruendung steht im Quelltext",
      "69 Bytes" in _p6 or "69 Bytes Unterschied" in QF,
      "ein Fehler, der einmal gefunden wurde, gehoert aufgeschrieben")
check("und es gibt keinen Pfad mehr, der die Karte auslaesst",
      "self._panel_text_zeichnen(" in QF
      and QF.count("self._panel_text_zeichnen(") == 1,
      "der Textblock hat einen Namen, aber nur einen Aufrufer")

# ---------------------------------------------------------------------------
print()
print("Test 7: er greift wirklich - und nur dann, wenn er darf")
# ---------------------------------------------------------------------------
H.set_screen(1920, 1080)
fe7 = H.make_frontend(page=1)


def _uebersprungen():
    """get_scaled() verhaelt sich wie beim Schnellscrollen: es liefert
    NICHTS und zaehlt _defer_count hoch.

    AUF DER INSTANZ, nicht am Modul - frontend.py importiert ART aus
    fe.art und meint damit den ArtCache. Am Modul gezaehlt blieb
    nur_verzoegert falsch, und die Messung zeigte brav, dass der kurze
    Weg nichts bringt."""
    echt = ART.ART.get_scaled

    def _ersatz(quelle, breite, hoehe, **k):
        ART.ART._defer_count = getattr(ART.ART, "_defer_count", 0) + 1
        return None

    ART.ART.get_scaled = _ersatz
    return lambda: setattr(ART.ART, "get_scaled", echt)


def _gefuellt(fe, n=10):
    """n Scrollschritte, und wieviele Bytes dabei gefuellt wurden."""
    schritt = BENCH.schritt_funktion(fe, 1)
    schritt(0)
    spanne = BENCH.fenster_spanne(fe, 1)
    for i in range(6):
        schritt(i % spanne)
    konto = {"bytes": 0}
    echt = fe.fb.flaechen_fueller

    def _h(buf, stride, hoehe, grenze, rechtecke):
        for r in rechtecke:
            konto["bytes"] += r[2] * r[3] * 4
        return echt(buf, stride, hoehe, grenze, rechtecke)

    fe.fb.flaechen_fueller = _h
    try:
        for i in range(n):
            schritt(i % spanne)
    finally:
        fe.fb.flaechen_fueller = echt
    return konto["bytes"] / float(n) / 1048576.0


def _liste_setzen(fe, muster):
    _, node, _ = fe.cats[fe.cat_i]
    node["items"] = [
        (muster(i), "game", ("/f/%d.sfc" % i, ".sfc", "SNES", None, None))
        for i in range(60)]
    node.pop("_display_items_cache", None)
    fe.item_i = 0
    fe.scroll = 0
    fe.ansicht_setzen("liste")


zurueck7 = _uebersprungen()
try:
    fe7.page = 1
    fe7.cat_i = 0
    fe7.nav_path = []
    _liste_setzen(fe7, lambda i: "Super Mario %03d" % i)
    gleich = _gefuellt(fe7)
    _liste_setzen(fe7, lambda i: "%s%03d" % (chr(65 + (i % 26)), i))
    wechsel = _gefuellt(fe7)
    print("   gleicher Buchstabe: %.2f MB je Schritt" % gleich)
    print("   wechselnder:        %.2f MB je Schritt" % wechsel)
    # GEAENDERT (Build 247). Bis Build 246 stand hier die Erwartung,
    # dass der wechselnde Buchstabe den VOLLEN Weg nimmt - und genau
    # das war der Fehler, den der Bench auf dem Geraet gefunden hat:
    #
    #     Abschnitt K, "Taste gedrueckt": 531.383 gefuellte Punkte,
    #     wo 174.240 (greift) oder 710.410 (greift nicht) zu
    #     erwarten waren. Also griff er in genau EINEM DRITTEL der
    #     Schritte - weil in einer echten Arcade-Liste der
    #     Anfangsbuchstabe oft wechselt.
    #
    # Seit Build 247 gehoert der Buchstabe nicht mehr in den
    # Vergleich; er wird auf dem kurzen Weg mitgezeichnet. Beide
    # Faelle muessen deshalb GLEICH guenstig sein.
    check("der wechselnde Buchstabe kostet nicht mehr als der gleiche",
          wechsel <= gleich * 1.25,
          "%.2f gegen %.2f MB - genau das war der Fund vom Geraet"
          % (wechsel, gleich))
    check("und beide liegen klar unter der ganzen Karte",
          max(gleich, wechsel) < 1.5,
          "%.2f MB - die ganze Karte waere rund 2,7 MB"
          % max(gleich, wechsel))
finally:
    zurueck7()

print()
if fails:
    print("FEHLGESCHLAGEN (%d):" % len(fails))
    for f in fails:
        print("  - %s" % f)
    sys.exit(1)
print("Alles in Ordnung.")
