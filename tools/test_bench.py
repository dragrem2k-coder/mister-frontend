#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Der Bench-Modus (Build 177).

WORUM ES GEHT

Jede Messung in diesem Projekt seit Build 73 war Handarbeit:
DRAGEND_PROFILE setzen, scrollen, "grep PERF", abtippen. Das ergibt
Zahlen fuer GENAU dieses Geraet an GENAU diesem Tag - zwischen zwei
Geraeten laesst sich damit nichts vergleichen.

"--bench" macht daraus einen festen Ablauf. Der entscheidende Teil
des Entwurfs ist, dass die Kernzahlen NICHT vom Bestand abhaengen:
das Testbild wird erzeugt, die Bildgroessen stehen fest, die Zahl der
Schritte steht fest.

DIE ZWEI FALLEN, DIE DIESER TEST BEWACHT

1. DER BENCH DARF NICHTS AUF DER KARTE ANFASSEN. Er rechnet
   Miniaturen aus und schreibt sie - wenn das im echten Cache landet,
   ist der erste Bench-Lauf eines Nutzers ein stiller Eingriff in
   seinen Bestand. Test 4 legt eine Attrappe ueber /media/fat und
   prueft, dass dort nichts entsteht.

2. EIN BENCH, DER BEIM ERSTEN UNERWARTETEN DING ABBRICHT, IST
   NUTZLOS. Er laeuft auf fremden Geraeten, mit fremden Bestaenden,
   ohne Artwork, ohne C-Modul. Test 5 nimmt ihm nacheinander Teile
   weg und prueft, dass trotzdem ein vollstaendiger Bericht
   herauskommt.

Ausfuehren:
    python3 tools/test_bench.py
"""
import io
import os
import sys
import tempfile
import time
import zlib

# VOR dem Pruefstand merken: tools/_harness.py friert time.monotonic()
# auf einen festen Wert ein, damit Puls und Laufschrift in den
# Zeichentests reproduzierbar sind. Fuer ein BENCH ist das toedlich -
# jede Messung waere 0.00 ms, und der Test wuerde nur pruefen, dass
# Nullen an der richtigen Stelle stehen. Waehrend der Bench-Laeufe
# unten wird deshalb kurz die echte Uhr eingesetzt.
_ECHTE_UHR = time.monotonic

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
sys.path.insert(0, _HIER)

# Wie tools/test_c_modul.py: ohne die x86-Fassung wuerde der Vergleich
# "C gegen Python" nichts pruefen.
if not os.environ.get("DRAGEND_LIB"):
    for _k in (os.path.join(_REPO, "frontend", "c", "libdragend_x86.so"),
               os.path.join(_REPO, "frontend", "libdragend_x86.so")):
        if os.path.exists(_k):
            os.environ["DRAGEND_LIB"] = _k
            break

import _harness as H                                     # noqa: E402

fm = H.fm
import fe.art as A                                       # noqa: E402
import fe.settings as S                                  # noqa: E402
import fe.bench as B                                     # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


# Klein rechnen - dieser Test prueft den ABLAUF, nicht die
# Geschwindigkeit. Mit den echten Massen (1200x1600, 60 Schritte,
# neun Wiederholungen) liefe er Minuten.
B.QUELL_B, B.QUELL_H = 60, 80
B.ZIEL_B, B.ZIEL_H = 29, 38
B.KLEIN_B, B.KLEIN_H = 9, 12
B.WDH_BILLIG, B.WDH_TEUER = 2, 1
B.SCHRITTE = 3

H.SCREEN[:] = [1920, 1080]


def lauf(fe=None):
    gefroren = fm.time.monotonic
    fm.time.monotonic = _ECHTE_UHR
    try:
        return B.lauf(fe or H.make_frontend(page=0), fm, A, S,
                      startdauer=1.234, log=None)
    finally:
        fm.time.monotonic = gefroren


# ---------------------------------------------------------------------------
print("Test 1: der Bericht entsteht und ist vollstaendig")
# ---------------------------------------------------------------------------
text = lauf()
for marke in ("Dragend Bench", "A  START", "B  ZEICHNEN", "C  BILDKETTE",
              "D  ECHTE DATEI", "Nichts auf der Karte wurde veraendert"):
    check("Abschnitt %-24s steht im Bericht" % ("'" + marke + "'"),
          marke in text)
check("kein Abschnitt ist abgebrochen",
      "ABGEBROCHEN" not in text,
      [z for z in text.splitlines() if "ABGEBROCHEN" in z][:2])
check("keine FEHLER-Zeile im Bericht",
      "FEHLER" not in text,
      [z for z in text.splitlines() if "FEHLER" in z][:2])

# ---------------------------------------------------------------------------
print()
print("Test 2: die Kopfdaten sagen, WORAUF gemessen wurde")
# ---------------------------------------------------------------------------
# Ohne die ist eine Zahl wertlos - genau das war das Problem an den
# bisher von Hand abgetippten Messwerten.
for feld in ("Build", "System", "Python", "Anzeige", "C-Modul",
             "Verkleinern", "Bestand"):
    check("Kopfzeile %-12s vorhanden" % feld,
          any(z.startswith(feld) for z in text.splitlines()))
check("die Aufloesung steht wirklich drin", "1920x1080" in text)
check("und der Hinweis auf die Vergleichbarkeit",
      "VERGLEICHBAR" in text and "NICHT vergleichbar" in text)

# ---------------------------------------------------------------------------
print()
print("Test 3: die bestandsabhaengigen Zahlen sind JE SPIEL normiert")
# ---------------------------------------------------------------------------
# Das ist der Punkt, an dem 2000 und 97000 Spiele vergleichbar werden.
check("der Startwert wird je Spiel ausgewiesen",
      "je Spiel" in text or "kein Bestand erkannt" in text)
check("die Startdauer selbst steht da",
      "1234.00 ms" in text, [z for z in text.splitlines()
                             if "Start bis" in z][:1])

# ---------------------------------------------------------------------------
print()
print("Test 4: DER BENCH FASST DIE KARTE NICHT AN")
# ---------------------------------------------------------------------------
# Die Attrappe sandboxt /media/fat NICHT (siehe tools/_harness.py) -
# hier wird deshalb von Hand ein Ersatzordner untergeschoben und
# danach nachgesehen, ob etwas darin gelandet ist.
sandbox = tempfile.mkdtemp(prefix="bench_karte_")
alt_thumb = A.THUMB_CACHE_BASE
alt_art = A.ART_BASE
try:
    A.THUMB_CACHE_BASE = os.path.join(sandbox, "thumbs")
    A.ART_BASE = os.path.join(sandbox, "art")
    vorher = set()
    for wurzel, _d, dateien in os.walk(sandbox):
        for d in dateien:
            vorher.add(os.path.join(wurzel, d))
    lauf()
    nachher = set()
    for wurzel, _d, dateien in os.walk(sandbox):
        for d in dateien:
            nachher.add(os.path.join(wurzel, d))
    neu = nachher - vorher
    check("keine einzige Datei im Cache-Ordner entstanden",
          not neu, "%d neue: %s" % (len(neu), sorted(neu)[:3]))
finally:
    A.THUMB_CACHE_BASE = alt_thumb
    A.ART_BASE = alt_art

# Und der temporaere Ordner, in dem der Bench WIRKLICH schreibt, muss
# hinterher weg sein - sonst sammelt sich bei jedem Lauf Muell in /tmp.
vor_tmp = set(p for p in os.listdir(tempfile.gettempdir())
              if p.startswith("dragend_bench_"))
lauf()
nach_tmp = set(p for p in os.listdir(tempfile.gettempdir())
               if p.startswith("dragend_bench_"))
check("der temporaere Arbeitsordner wird wieder aufgeraeumt",
      nach_tmp <= vor_tmp, "uebrig: %s" % sorted(nach_tmp - vor_tmp)[:3])

# ---------------------------------------------------------------------------
print()
print("Test 5: er laeuft auch durch, wenn etwas FEHLT")
# ---------------------------------------------------------------------------
# Der Bench landet auf fremden Geraeten. Dort fehlt mal das C-Modul,
# mal das Artwork, mal sieht der Kategoriebaum anders aus als hier.
alt_lib = A._LIB
try:
    A._LIB = None
    t2 = lauf()
    check("ohne C-Modul laeuft er durch",
          "ABGEBROCHEN" not in t2 and "C  BILDKETTE" in t2)
    check("und sagt ehrlich, dass Python rechnet",
          "NICHT geladen" in t2)
finally:
    A._LIB = alt_lib

alt_pfad = A.art_path
try:
    A.art_path = lambda *a, **k: None
    t3 = lauf()
    check("ohne jedes Cover laeuft er durch",
          "ABGEBROCHEN" not in t3)
    check("und sagt, dass Abschnitt D uebersprungen wurde",
          "uebersprungen" in t3)
finally:
    A.art_path = alt_pfad


class KaputterBaum(object):
    """Ein Kategoriebaum, der auf jede Frage mit einer Ausnahme
    antwortet - das Schlimmste, was _zaehlen() passieren kann."""

    def __iter__(self):
        raise RuntimeError("kaputt")

    def values(self):
        raise RuntimeError("kaputt")


fe = H.make_frontend(page=0)
fe.cats = [("Kaputt", KaputterBaum(), "snes")]
t4 = lauf(fe)
check("ein unlesbarer Kategoriebaum bringt ihn nicht um",
      "ABGEBROCHEN" not in t4 and "Ende." in t4)

# ---------------------------------------------------------------------------
print()
print("Test 6: das erzeugte Testbild taugt als Messgrundlage")
# ---------------------------------------------------------------------------
# Wenn das Bild aus einer einzigen Farbe bestuende, waere die
# Cache-Messung eine Messung von "zlib komprimiert Nullen".
pix = B.testbild(64, 48)
check("es hat die richtige Groesse", len(pix) == 64 * 48 * 4,
      "%d" % len(pix))
check("es ist bei jedem Lauf dasselbe", pix == B.testbild(64, 48))
farben = set(bytes(pix[i:i + 4]) for i in range(0, len(pix), 4))
check("es hat viele verschiedene Farbwerte", len(farben) > 200,
      "%d" % len(farben))
# Das Packverhaeltnis MUSS an einem grossen Bild geprueft werden:
# bei 64x48 hat zlib gar kein Fenster, dort kommt immer ~98 % heraus,
# und die Pruefung wuerde nichts aussagen. Genau das war beim ersten
# Anlauf der Fall.
gross = B.testbild(600, 800)
gepackt = len(zlib.compress(gross, 1))
anteil = 100.0 * gepackt / len(gross)
check("es packt sich wie ein Cover, nicht wie eine Flaeche",
      25.0 <= anteil <= 80.0,
      "%.0f %% bei Packstufe 1 - das Geraet meldete an einem echten "
      "Cover 47 %%" % anteil)

# Und das erzeugte PNG muss ein PNG sein, das unser eigener Leseweg
# auch wirklich versteht - sonst misst Abschnitt C einen Fehlschlag.
png = B.testbild_png(pix, 64, 48)
check("das erzeugte PNG hat die richtige Signatur",
      png.startswith(b"\x89PNG\r\n\x1a\n"))
ordner = tempfile.mkdtemp(prefix="bench_png_")
try:
    p = os.path.join(ordner, "x.png")
    io.open(p, "wb").write(png)
    gelesen = A.original_lesen(p, 32, 24)
    check("und original_lesen() kann es lesen", gelesen is not None,
          "sonst misst Abschnitt C einen Fehlschlag statt eine Dauer")
    if gelesen:
        check("mit den richtigen Massen", gelesen[3] == (64, 48),
              str(gelesen[3]))
finally:
    import shutil
    shutil.rmtree(ordner, ignore_errors=True)

# Das eigene Format ebenso.
art1 = B.testbild_art1(pix, 64, 48, 1)
check("das erzeugte ART1 faengt mit der Kennung an",
      art1.startswith(b"ART1"))

# ---------------------------------------------------------------------------
print()
print("Test 7: der Median, nicht der Mittelwert")
# ---------------------------------------------------------------------------
# Auf einem Geraet, auf dem nebenher etwas laeuft, verschiebt EIN
# Ausreisser den Mittelwert und macht die Zahl unbrauchbar.
check("gerade Anzahl", abs(B._median([1, 2, 3, 4]) - 2.5) < 1e-9)
check("ungerade Anzahl", B._median([5, 1, 3]) == 3)
check("ein Ausreisser zieht ihn nicht mit",
      B._median([1, 1, 1, 1, 1000]) == 1)
check("leere Liste ergibt 0", B._median([]) == 0.0)

zaehler = [0]


def _zaehl():
    zaehler[0] += 1


ms, best = B.messen(_zaehl, 5)
check("messen() ruft genau so oft auf, wie verlangt", zaehler[0] == 5,
      "%d" % zaehler[0])
check("und liefert zwei Zahlen", ms >= 0 and best >= 0 and best <= ms)
import gc                                                # noqa: E402
check("die Muellabfuhr laeuft danach wieder", gc.isenabled(),
      "sonst waechst der Speicher bis zum Ende des Laufs")

# ---------------------------------------------------------------------------
print()
print("Test 8: der Schalter haengt am Einstieg")
# ---------------------------------------------------------------------------
quelle = io.open(os.path.join(_REPO, "frontend", "frontend.py"),
                 encoding="utf-8").read()
check('"--bench" wird in sys.argv gesucht', '"--bench" in sys.argv' in quelle)
check("das Bench-Modul wird dort geladen", "import fe.bench as BENCH" in quelle)
check("es bekommt das MODUL fe.art, nicht den ArtCache",
      'sys.modules["fe.art"]' in quelle,
      "ART ist eine Instanz - original_lesen() gaebe es dort nicht")
check("der Bericht wird zusaetzlich in eine Datei geschrieben",
      "BENCH_AUSGABE" in quelle)
check("und die liegt in /tmp, nicht auf der Karte",
      'BENCH_AUSGABE = "/tmp/' in quelle)
# Ohne das bliebe nach dem Bench ein schwarzer Schirm mit Cursor
# stehen, statt zurueck ins MiSTer-Menue zu gehen - genau der
# Fehler aus Build 163/165/166, nur an einer neuen Stelle.
_nach_bench = quelle.split('"--bench" in sys.argv')[1][:2500]
check("danach wird sauber beendet (Bildschirm zurueck an MiSTer)",
      "_fe._beenden()" in _nach_bench)
check("und der Prozess endet dort, statt in run() weiterzulaufen",
      "sys.exit(0)" in _nach_bench)

bq = io.open(os.path.join(_REPO, "frontend", "fe", "bench.py"),
             encoding="utf-8").read()
check("fe/bench.py importiert das Frontend NICHT",
      "import frontend" not in bq,
      "sonst gaebe es zwei Ladewege fuer dieselbe Datei")

# ---------------------------------------------------------------------------
print()
print("Test 9: die Fehler aus dem ERSTEN Lauf auf echter Hardware")
# ---------------------------------------------------------------------------
# Build 177 lief einmal auf dem DE10-Nano. Der Lauf hat vier Fehler
# im Messgeraet selbst aufgedeckt - dieser Block haelt jeden davon
# einzeln fest.

# (1) Die Packstufe MUSS dieselbe sein wie im echten Cache. Gemeldet
#     wurden 1176 ms fuer etwas, das in Wirklichkeit halb so lange
#     dauert - eine Zahl, die nach Produktionskosten aussah.
art_quelle = io.open(os.path.join(_REPO, "frontend", "fe", "art.py"),
                     encoding="utf-8").read()
check("art.py hat eine benannte Packstufe", hasattr(A, "THUMB_PACKSTUFE"))
check("und der echte Schreibweg benutzt sie",
      "zlib.compress(pix, THUMB_PACKSTUFE)" in art_quelle,
      "sonst kann sie wieder auseinanderlaufen")
check("keine feste Stufe mehr im Bench",
      "zlib.compress(pix, 6)" not in bq and "zlib.compress(pix, 1)" not in bq)
gross_art = B.testbild_art1(B.testbild(64, 48), 64, 48, A.THUMB_PACKSTUFE)
check("und testbild_art1 nimmt die Stufe entgegen",
      gross_art.startswith(b"ART1"))

# (2) Die Cover-Suche muss den ECHTEN Baum verstehen. Bei 30064
#     Spielen meldete der Bench "kein Cover gefunden".
baum = {"folders": {"Unter": {"folders": {},
                              "items": [("Tief", "rom", ("a", "b", "c", "d",
                                                         ()))]}},
        "items": [("Oben", "rom", ("a", "b", "c", "d", ())),
                  ("Ordner", "folder", ("a", "b", "c", "d", ()))]}
namen = [e[0] for e in B._eintraege(baum)]
check("Eintraege werden auch aus Unterordnern geholt",
      "Oben" in namen and "Tief" in namen, str(namen))
check("und Ordner zaehlen nicht als Spiel", "Ordner" not in namen)
check("_zaehlen kommt auf dieselbe Zahl", B._zaehlen(baum) == 2,
      "%d" % B._zaehlen(baum))
check("ein Nicht-Dict bringt beide nicht um",
      B._zaehlen(["kaputt"]) == 0 and list(B._eintraege("kaputt")) == [])

# (3) Das Testbild darf nicht die halbe Laufzeit kosten. 1200x1600
#     brauchte 25,5 Sekunden auf dem Geraet.
# _ECHTE_UHR, nicht time.monotonic(): der Pruefstand hat die
# eingefroren, sonst kaeme hier immer 0 ms heraus - und die
# Pruefung waere genau die Sorte Gruen, die nichts bedeutet.
_t = _ECHTE_UHR()
B.testbild(1200, 1600)
_dauer = (_ECHTE_UHR() - _t) * 1000.0
# Der Entwicklungsrechner ist rund 30x schneller als der DE10-Nano
# (nachgemessen, siehe Projektnotizen). 300 ms hier heissen also rund
# 9 s dort - immer noch viel, aber nie wieder 25 s.
check("1200x1600 entsteht in unter 300 ms", _dauer < 300.0,
      "%.0f ms (auf dem Geraet rund %.0fx so viel)" % (_dauer, 30))

# (4) Kalt und warm muessen GETRENNT im Bericht stehen.
check("der Bericht weist kalt getrennt aus", "je Schritt kalt" in text)
check("und warm getrennt", "je Schritt warm" in text)
check("und sagt, was der Unterschied bedeutet",
      "Miniatur muss erst gerechnet werden" in text)
check("und nennt die Einschraenkung ehrlich",
      "Obergrenze" in text,
      "beim echten Scrollen wird die Boxart-Spalte ausgelassen")

# (5) Der fuenfte Fehler, den erst das Nachlesen im Code zutage
#     brachte: Zeichnen RECHNET Cover, und ein gerechnetes Cover wird
#     weggeschrieben. Abschnitt B hat also sehr wohl auf die Karte
#     geschrieben, waehrend im Bericht stand, er tue das nicht.
check("es gibt eigene Messbedingungen fuer Abschnitt B",
      "class _Messbedingungen" in bq)
check("und Abschnitt B laeuft darin",
      "with _Messbedingungen(" in bq)

# ---------------------------------------------------------------------------
print()
print("Test 10: die Fehler aus dem ZWEITEN Lauf auf echter Hardware")
# ---------------------------------------------------------------------------
# Rueckmeldung des Nutzers: "der bench landet immer im supergameboy,
# dann passiert nichts mehr, es werden keine covers gescrollt nichts.
# der erste bench landete im playstation, dort scrollte er dann
# weiter."
#
# Genau so war es: der Zeiger blieb dort stehen, wo die Schleife ueber
# die Hauptseite ihn liegen gelassen hatte. In einer Kategorie mit
# einem einzigen Eintrag steht item_i durch die Modulo-Rechnung fest
# auf 0 - das Bild aendert sich nie, gemessen wird ein Standbild.
# Daher auch die 52.98 / 52.97 / 52.99 aus jenem Lauf: drei voellig
# verschiedene Zeichenwege, identisch auf die Hundertstel.

class FakeFE(object):
    def __init__(self, cats):
        self.cats = cats


def knoten(n, mit_ordner=0):
    return {"folders": {"U%d" % i: {"folders": {}, "items": []}
                        for i in range(mit_ordner)},
            "items": [("S%d" % i, "rom", ("a", "b", "c", "d", ()))
                      for i in range(n)]}


f_ = FakeFE([("Super Game Boy", knoten(1), "sgb"),
             ("PlayStation", knoten(800), "psx"),
             ("Kaputt", "keine Ahnung", "x")])
i_, n_, na_ = B._groesste_kategorie(f_)
check("die groesste Kategorie wird BEWUSST gewaehlt",
      (i_, n_, na_) == (1, 800, "PlayStation"), "%s" % ((i_, n_, na_),))
check("ein unbrauchbarer Knoten dazwischen stoert nicht", i_ == 1)
check("ohne jede Kategorie kommt (None, 0, '') zurueck",
      B._groesste_kategorie(FakeFE([])) == (None, 0, ""))
check("und eine Kategorie ohne Eintraege wird nicht gewaehlt",
      B._groesste_kategorie(FakeFE([("Leer", knoten(0), "x")]))[0] is None)
# Eine Kategorie, deren Spiele alle in UNTERordnern liegen, zeigt an
# der Wurzel nur Ordner - sie waere zum Messen genauso ungeeignet wie
# eine leere, obwohl _zaehlen() sie gross findet.
tief = {"folders": {"A": knoten(500)}, "items": []}
check("Spiele in Unterordnern zaehlen fuer die WAHL nicht mit",
      B._groesste_kategorie(FakeFE([("Tief", tief, "x")]))[0] is None,
      "gemessen wird die Liste auf dem Schirm, nicht der Baum")
check("_zaehlen findet sie trotzdem", B._zaehlen(tief) == 500)

check("der Bericht nennt die gemessene Kategorie",
      "gemessen in:" in text, [z for z in text.splitlines()
                               if "gemessen in" in z][:1])
check("und warnt bei einer zu kurzen Liste",
      "ACHTUNG" in bq and "sagen bei so kurzer Liste" in bq)

# Das Vsync-Warten darf nicht mehr in den Schrittwerten stecken.
check("die Messbedingungen schalten das Vsync-Warten ab",
      "_vsync_ueberspringen" in bq)
check("und der Flip wird getrennt mit und ohne ausgewiesen",
      "ohne Vsync" in text and "mit Vsync" in text)
check("mit der Angabe, was das Warten kostet",
      "das Warten kostet" in text)

# Und das Auslagern an den ARBEITSPROZESS muss aus sein, sonst
# schreibt der weiter auf die Karte (eigener Prozess, sieht die
# Umleitung nicht) und der Elternprozess findet nie etwas.
check("das Auslagern an den Arbeitsprozess wird abgeschaltet",
      "ART.auslagern = None" in bq)
check("und der Vorauslader beendet",
      "PREWARMER.beenden()" in bq)

class FakeFM(object):
    class PREWARMER(object):
        @staticmethod
        def beenden():
            pass


# ERST das Frontend bauen, DANN den Ausgangszustand merken: eine neue
# Frontend-Instanz haengt ihren eigenen Vorauslader in ART.auslagern.
# Andersherum verglichen der Test gegen einen Wert, den es zu dem
# Zeitpunkt gar nicht mehr gab - und meldete Rot, obwohl das
# Wiederherstellen stimmte.
fe_ = H.make_frontend(page=0)
alt_dir = A.THUMB_CACHE_DIR
alt_ausl = A.ART.auslagern
with B._Messbedingungen(A, FakeFM, fe_, True) as u:
    check("waehrenddessen zeigt der Cache woanders hin",
          A.THUMB_CACHE_DIR != alt_dir, A.THUMB_CACHE_DIR)
    check("und zwar in einen temporaeren Ordner",
          A.THUMB_CACHE_DIR.startswith(tempfile.gettempdir()))
    check("das Auslagern ist wirklich aus", A.ART.auslagern is None)
    check("und das Vsync-Warten wird uebersprungen",
          fe_._vsync_ueberspringen(None) is True)
    _tmp_ordner = u.ordner
check("danach steht der Cache wieder auf dem Original",
      A.THUMB_CACHE_DIR == alt_dir, A.THUMB_CACHE_DIR)
check("das Auslagern ist wiederhergestellt",
      A.ART.auslagern is alt_ausl)
check("und der temporaere Ordner ist weg",
      not os.path.exists(_tmp_ordner or "/nichts"))

# ---------------------------------------------------------------------------
print()
print("Block 11: der dritte Zustand - Miniatur auf der Karte, nicht im RAM")
# ---------------------------------------------------------------------------
# Zwischen "muss gerechnet werden" und "liegt im RAM" liegt der Fall,
# der beim Scrollen durch eine grosse Sammlung der haeufigste ist.
# Ohne ihn misst der Bench zwei Zustaende, die im Alltag beide selten
# sind.
import fe.art as _A                                      # noqa: E402

check("ArtCache kann seinen RAM leeren", hasattr(_A.ART, "ram_leeren"))
_A.ART._scaled_cache_put(("x",), (1, 1, b"\x00\x00\x00\xff"))
_A.ART.cache["/irgendwas"] = (1, 1, b"\x00\x00\x00\xff")
_A.ART.ram_leeren()
check("danach ist der Kasten-Cache leer", not _A.ART.scaled)
check("und der Original-Cache auch", not _A.ART.cache,
      "bleibt einer stehen, ist der naechste Durchgang halb warm")
check("die Buchhaltung wird mitgeleert",
      _A.ART.scaled_bytes == 0 and _A.ART._original_bytes == 0
      and not _A.ART.order and not _A.ART.scaled_order)

_q = io.open(os.path.join(_REPO, "frontend", "fe", "bench.py"),
             encoding="utf-8").read()
check("der Bench misst den Zustand auch", "je Schritt Karte" in _q)
check("und leert dafuer den RAM", "ram_leeren()" in _q)
check("die Kopfzeile erklaert alle drei Zustaende",
      "Karte = Miniatur liegt auf der Karte" in _q)
check("ohne A bleibt der Bench lauffaehig", "if A is not None:" in _q,
      "der Abschnitt wird auch aus Tests ohne Modul gerufen")

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
