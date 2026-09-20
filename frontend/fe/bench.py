#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bench-Modus (Build 177): eine feste, wiederholbare Messung.

    python3 /media/fat/frontend/frontend.py --bench

WARUM ES DEN GIBT

Jede Zahl in diesem Projekt seit Build 73 wurde von Hand erhoben:
DRAGEND_PROFILE setzen, scrollen, "grep PERF" im Log, abtippen. Das
hat funktioniert, aber es ist jedes Mal ein anderer Ablauf, und
zwischen zwei Geraeten laesst sich so gar nichts vergleichen. Degauss
veroeffentlicht Messreihen; wer mitreden will, braucht dieselbe Art
von Zahl.

DER ENTWURFSGRUNDSATZ: VERGLEICHBAR HEISST UNABHAENGIG VOM BESTAND

Die wichtigsten Zahlen hier haengen NICHT davon ab, was auf der Karte
liegt. Das Testbild wird erzeugt, nicht gelesen; die Bildgroessen sind
fest; die Zahl der Schritte ist fest. Zwei Geraete, die diesen Lauf
machen, messen dasselbe.

Was doch vom Bestand abhaengt - Einlesen, Speicher je Spiel - wird JE
SPIEL normiert ausgegeben, damit 2000 und 97000 Spiele vergleichbar
bleiben. Und was sich prinzipiell nicht vergleichen laesst (das
Dekodieren einer echten JPEG-Datei haengt an genau dieser Datei),
steht in einem eigenen Abschnitt mit genau diesem Hinweis daneben.

WAS DER BENCH NICHT TUT

Er schreibt NICHTS nach /media/fat. Keine Miniatur, keine
Einstellung, keine Cache-Datei. Die Messung des Cache-Schreibens
laeuft in einem temporaeren Ordner, der danach wieder verschwindet -
sonst waere der erste Bench-Lauf eines Nutzers ein stiller Eingriff
in seinen Bestand.

Er bewertet auch nichts. Hier steht, was gemessen wurde; was daraus
folgt, entscheidet ein Mensch.
"""
import gc
import os
import platform
import shutil
import struct
import sys
import tempfile
import time
import zlib

BENCH_VERSION = 1

# Feste Masse fuer die vergleichbaren Messungen. Bewusst KEINE
# Ableitung aus der Aufloesung: sonst misst ein 1080p-Geraet etwas
# anderes als ein CRT, und genau das soll dieser Teil ja ausschliessen.
#
# 1200x1600 ist ein typischer Scan aus der Artwork-Datenbank (siehe
# BUILD_119: Cover werden seit v4.4 in Originalgroesse gelesen), und
# 578x770 ist der Kasten, in den 1920x1080 sie einpasst.
QUELL_B, QUELL_H = 1200, 1600
ZIEL_B, ZIEL_H = 578, 770
# Der kleine Kasten - so gross wie eine Rasterkachel auf 1080p.
KLEIN_B, KLEIN_H = 176, 235

# Wie oft eine Einzelmessung wiederholt wird. Genommen wird der
# MEDIAN, nicht der Mittelwert: auf einem Geraet, auf dem nebenher
# noch etwas laeuft, verschiebt ein einzelner Ausreisser den
# Mittelwert, den Median nicht.
WDH_BILLIG = 9
WDH_TEUER = 3
# Zeichenschritte je Ansicht. 60 ist keine runde Zahl aus Bequem-
# lichkeit: darunter dominiert der erste, kalte Schritt das Ergebnis.
SCHRITTE = 60


# ---------------------------------------------------------------------
# Messwerkzeug
# ---------------------------------------------------------------------
def _median(werte):
    w = sorted(werte)
    n = len(w)
    if not n:
        return 0.0
    return w[n // 2] if n % 2 else (w[n // 2 - 1] + w[n // 2]) / 2.0


def messen(fn, wdh=WDH_BILLIG):
    """(Median, Bestwert) in Millisekunden.

    Der Bestwert steht mit dabei, weil er die andere Frage beantwortet:
    der Median sagt, was der Nutzer erlebt, der Bestwert, was das Geraet
    koennte, wenn nichts dazwischenfunkt. Laufen die beiden weit
    auseinander, stoert etwas - und das ist selbst ein Befund."""
    zeiten = []
    for _ in range(max(1, wdh)):
        # Die Muellabfuhr genau EINMAL vor der Messung anstossen, dann
        # abschalten: sonst faellt sie mal in die eine, mal in die
        # andere Wiederholung und macht aus einer Messung ein
        # Wuerfelspiel.
        gc.collect()
        gc.disable()
        try:
            t = time.monotonic()
            fn()
            zeiten.append((time.monotonic() - t) * 1000.0)
        finally:
            gc.enable()
    return _median(zeiten), min(zeiten)


class Bericht(object):
    """Sammelt die Zeilen und gibt sie auf stdout UND ins Log aus.

    Beides, weil beide Wege gebraucht werden: wer den Bench per SSH
    startet, will ihn sofort sehen; wer ihn jemandem schickt, schickt
    die Log-Datei."""

    def __init__(self, log=None):
        self.zeilen = []
        self._log = log

    def __call__(self, text=""):
        self.zeilen.append(text)
        try:
            print(text)
        except OSError:
            pass
        if self._log:
            try:
                self._log("BENCH " + text)
            except Exception:                            # noqa: BLE001
                pass

    def posten(self, name, ms, best=None, zusatz=""):
        """Eine Messzeile in einheitlicher Form."""
        zeile = "   %-38s %9.2f ms" % (name, ms)
        if best is not None and best > 0 and ms > best * 1.25:
            # Nur zeigen, wenn er wirklich abweicht - sonst ist es
            # Rauschen in der Ausgabe statt Information.
            zeile += "   (best %.2f)" % best
        if zusatz:
            zeile += "   " + zusatz
        self(zeile)

    def text(self):
        return "\n".join(self.zeilen) + "\n"


# ---------------------------------------------------------------------
# Erzeugte Testdaten - der Grund, warum der Lauf vergleichbar ist
# ---------------------------------------------------------------------
def testbild(w, h):
    """Deterministische BGRA-Pixel mit harten Kanten und Verlaeufen.

    Harte Kanten, weil das Flaechenmittel daran am meisten zu tun hat;
    Verlaeufe, damit zlib beim Cache-Schreiben nicht unrealistisch gut
    komprimiert. Ohne den zweiten Teil waere die Cache-Messung eine
    Messung von "eine Flaeche in einer Farbe"."""
    zeile_muster = []
    raus = bytearray(w * h * 4)
    for y in range(h):
        del zeile_muster[:]
        for x in range(w):
            kachel = ((x >> 5) + (y >> 5)) & 1
            zeile_muster.append(255 if kachel else (x * 7 + y * 3) & 255)
            zeile_muster.append((x * 5 + y) & 255)
            zeile_muster.append((y * 11 - x * 3) & 255)
            zeile_muster.append(0)
        raus[y * w * 4:(y + 1) * w * 4] = bytes(zeile_muster)
    return bytes(raus)


def _png_chunk(typ, daten):
    return (struct.pack(">I", len(daten)) + typ + daten
            + struct.pack(">I", zlib.crc32(typ + daten) & 0xFFFFFFFF))


def testbild_png(pix, w, h):
    """Aus denselben Pixeln eine echte PNG-Datei bauen.

    Von Hand, ohne Bibliothek - eine PNG-Datei ist ein Kopf, ein
    zlib-Strom mit einem Filterbyte je Zeile und ein Ende. Das ist
    hier die ganze Kunst und spart, eine feste Bilddatei mit
    auszuliefern. (Und ausgelieferte Dateien, die keine .py sind,
    hatten wir schon einmal: die Installer kopieren nur bestimmte
    Muster, siehe Build 161.)"""
    roh = bytearray()
    for y in range(h):
        roh.append(0)                                    # Filter "None"
        z = y * w * 4
        for x in range(w):
            i = z + x * 4
            # BGRA im Speicher -> RGB in der Datei
            roh.append(pix[i + 2])
            roh.append(pix[i + 1])
            roh.append(pix[i])
    kopf = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n"
            + _png_chunk(b"IHDR", kopf)
            + _png_chunk(b"IDAT", zlib.compress(bytes(roh), 6))
            + _png_chunk(b"IEND", b""))


def testbild_art1(pix, w, h):
    """Dasselbe im eigenen Format - so liegt eine Miniatur im Cache."""
    return b"ART1" + struct.pack("<HH", w, h) + zlib.compress(pix, 6)


# ---------------------------------------------------------------------
# Abschnitte
# ---------------------------------------------------------------------
def _kopf(b, fe, A, fm):
    b("=" * 62)
    b("Dragend Bench %d" % BENCH_VERSION)
    b("=" * 62)
    try:
        build = "?"
        import json
        # Neben frontend.py, nicht darueber: dort liegt sie sowohl im
        # Projektordner als auch nach der Installation unter
        # /media/fat/frontend (siehe Build 161, wo genau diese Datei
        # monatelang gar nicht erst mitkopiert wurde).
        p = os.path.join(os.path.dirname(os.path.abspath(fm.__file__)),
                         "LATEST_BUILD.json")
        with open(p) as f:
            build = json.load(f).get("build_id", "?")
    except Exception:                                    # noqa: BLE001
        build = "?"
    b("Build      : %s" % build)
    b("Zeit       : %s" % time.strftime("%Y-%m-%d %H:%M:%S"))
    b("System     : %s %s (%s)" % (platform.system(), platform.release(),
                                   platform.machine()))
    b("Python     : %s" % sys.version.split()[0])
    fbo = getattr(fe, "fb", None)
    if fbo is not None:
        b("Anzeige    : %dx%d, Skala %d"
          % (fbo.width, fbo.height, fm._skala(fbo.width, fbo.height)))
    lib = getattr(A, "_LIB", None)
    b("C-Modul    : %s"
      % ("libdragend Version %s" % A.DRAGEND_LIB_VERSION if lib
         else "NICHT geladen - alles rechnet in Python"))
    b("Verkleinern: %s"
      % ("scharf (nearest)" if A.scharf_verkleinern_an() else "weich (Mittel)"))
    spiele = 0
    systeme = 0
    try:
        for _name, node, _syskey in fe.cats:
            systeme += 1
            spiele += _zaehlen(node)
    except Exception:                                    # noqa: BLE001
        pass
    b("Bestand    : %d Spiele in %d Kategorien" % (spiele, systeme))
    b("")
    b("Die Abschnitte A und B haengen vom Bestand ab und sind deshalb")
    b("JE SPIEL normiert. Abschnitt C rechnet mit einem ERZEUGTEN Bild")
    b("fester Groesse und ist damit zwischen Geraeten direkt")
    b("vergleichbar. Abschnitt D ist es ausdruecklich nicht.")
    return spiele


def _zaehlen(node):
    """Spiele in einem Kategoriebaum - ohne Annahme ueber seine Form.

    Der Baum sieht je nach Kategorie anders aus (Ordner, Listen,
    Sonderfaelle wie Arcade). Ein Bench darf daran nicht scheitern,
    deshalb zaehlt das hier defensiv und gibt im Zweifel 0 zurueck."""
    try:
        if isinstance(node, dict):
            return sum(_zaehlen(v) for v in node.values())
        if isinstance(node, (list, tuple)):
            return sum(1 for x in node
                       if isinstance(x, (list, tuple)) and len(x) > 1
                       and x[1] != "folder") or len(node)
    except Exception:                                    # noqa: BLE001
        pass
    return 0


def _abschnitt_a(b, fe, spiele, startdauer):
    b("")
    b("A  START  (haengt vom Bestand ab)")
    if startdauer is None:
        b("   -- nicht gemessen (Bench ohne Startmessung aufgerufen)")
        return
    b("   %-38s %9.2f ms" % ("Start bis Kategorien bereit",
                             startdauer * 1000.0))
    if spiele > 0:
        b("   %-38s %9.4f ms" % ("davon je Spiel",
                                 startdauer * 1000.0 / spiele))
    else:
        b("   (kein Bestand erkannt - je-Spiel-Wert entfaellt)")


def _abschnitt_b(b, fe, S, spiele):
    b("")
    b("B  ZEICHNEN  (%d Schritte je Ansicht, Bestand des Geraets)"
      % SCHRITTE)
    fbo = fe.fb
    for seite, name in ((0, "Hauptseite"), (1, "Spieleliste")):
        fe.page = seite
        for ansicht in S.ANSICHTEN:
            try:
                if seite == 0:
                    fe.ansicht_haupt_setzen(ansicht)
                else:
                    fe.ansicht_setzen(ansicht)
            except Exception:                            # noqa: BLE001
                continue
            # Voller Aufbau: jedes Mal erzwungen, damit nicht der
            # schnelle Pfad gemessen wird und "voll" draufsteht.
            def _voll():
                fe._force_full_redraw = True
                fbo.mark_full_redraw()
                fe.draw()
            try:
                ms, best = messen(_voll, WDH_TEUER)
                b.posten("%s %-8s voller Aufbau" % (name, ansicht), ms, best)
            except Exception as e:                       # noqa: BLE001
                b("   %-38s FEHLER %s" % ("%s %s voll" % (name, ansicht), e))
                continue
            # Schritt: genau das, was beim Scrollen passiert. Ohne
            # _force_full_redraw, damit die schnellen Pfade aus Build
            # 76/122/125 auch wirklich greifen.
            def _schritt():
                for _ in range(SCHRITTE):
                    if seite == 0:
                        fe.cat_i = (fe.cat_i + 1) % max(1, len(fe.cats))
                    else:
                        # Umlaufen statt hochzaehlen: bei einer kurzen
                        # Liste liefe der Zeiger sonst ueber das Ende
                        # hinaus, und gemessen wuerde nicht mehr das
                        # Scrollen, sondern das Abfangen.
                        try:
                            n = len(fe._display_items())
                        except Exception:                # noqa: BLE001
                            n = 0
                        fe.item_i = (fe.item_i + 1) % max(1, n)
                    fe.draw()
            try:
                ms, best = messen(_schritt, 1)
                b.posten("%s %-8s je Schritt" % (name, ansicht),
                         ms / SCHRITTE, None,
                         "(%d Schritte in %.0f ms)" % (SCHRITTE, ms))
            except Exception as e:                       # noqa: BLE001
                b("   %-38s FEHLER %s"
                  % ("%s %s Schritt" % (name, ansicht), e))
    # Der reine Bildtransport, ohne alles davor. Die Zahl, gegen die
    # jede Zeichenoptimierung sich messen lassen muss - schneller als
    # das geht nicht.
    try:
        ms, best = messen(fbo.flip, WDH_TEUER)
        b.posten("Voller Flip (%.1f MB)" % (fbo.size / 1048576.0), ms, best)
    except Exception as e:                               # noqa: BLE001
        b("   Voller Flip: FEHLER %s" % e)


def _abschnitt_c(b, A):
    b("")
    b("C  BILDKETTE  (erzeugtes Bild %dx%d - VERGLEICHBAR)"
      % (QUELL_B, QUELL_H))
    t = time.monotonic()
    pix = testbild(QUELL_B, QUELL_H)
    b("   (Testbild in %.0f ms erzeugt, %.1f MB)"
      % ((time.monotonic() - t) * 1000.0, len(pix) / 1048576.0))

    for kb, kh, was in ((ZIEL_B, ZIEL_H, "Boxart-Spalte 1080p"),
                        (KLEIN_B, KLEIN_H, "Rasterkachel 1080p")):
        b("   -> %dx%d  (%s)" % (kb, kh, was))
        ms, best = messen(
            lambda: A._verkleinern_flaechenmittel(pix, QUELL_B, QUELL_H,
                                                  kb, kh), WDH_TEUER)
        b.posten("Flaechenmittel (C, wenn geladen)", ms, best)
        ms, best = messen(
            lambda: A._verkleinern_nearest(pix, QUELL_B, QUELL_H, kb, kh),
            WDH_TEUER)
        b.posten("Nearest (C, wenn geladen)", ms, best)
    # Python als Vergleichswert - das ist die Zahl, gegen die der
    # Gewinn des C-Moduls behauptet wird. Nur am kleinen Kasten: in
    # Python kostet der grosse auf dem Geraet Sekunden, und der
    # Faktor ist derselbe.
    if A._LIB is not None:
        ms_py, _ = messen(
            lambda: A._verkleinern_flaechenmittel_py(
                pix, QUELL_B, QUELL_H, KLEIN_B, KLEIN_H), 1)
        ms_c, _ = messen(
            lambda: A._verkleinern_flaechenmittel(
                pix, QUELL_B, QUELL_H, KLEIN_B, KLEIN_H), WDH_TEUER)
        b.posten("Dasselbe in Python (zum Vergleich)", ms_py, None,
                 "Faktor %.0f" % (ms_py / ms_c) if ms_c > 0 else "")

    # Der Cache-Weg: schreiben und lesen, so wie eine Miniatur
    # tatsaechlich abgelegt wird. In einem TEMPORAEREN Ordner.
    klein = A._verkleinern(pix, QUELL_B, QUELL_H, ZIEL_B, ZIEL_H)
    ordner = tempfile.mkdtemp(prefix="dragend_bench_")
    try:
        datei = os.path.join(ordner, "probe.art")
        roh = bytes(klein)

        def _schreiben():
            with open(datei, "wb") as f:
                f.write(testbild_art1(roh, ZIEL_B, ZIEL_H))
        ms, best = messen(_schreiben, WDH_TEUER)
        groesse = os.path.getsize(datei)
        b.posten("Miniatur packen und schreiben", ms, best,
                 "%d KB" % (groesse // 1024))

        def _lesen():
            with open(datei, "rb") as f:
                d = f.read()
            zlib.decompress(d[8:])
        ms, best = messen(_lesen, WDH_BILLIG)
        b.posten("Miniatur lesen und entpacken", ms, best)

        # PNG dekodieren - der Weg fuer eigene Cover im PNG-Format.
        # Das Bild wird hier erzeugt, also auch das vergleichbar.
        png = testbild_png(pix, QUELL_B, QUELL_H)
        pdatei = os.path.join(ordner, "probe.png")
        with open(pdatei, "wb") as f:
            f.write(png)
        ms, best = messen(lambda: A.original_lesen(pdatei, ZIEL_B, ZIEL_H),
                          WDH_TEUER)
        b.posten("PNG lesen und dekodieren", ms, best,
                 "%d KB" % (len(png) // 1024))
    finally:
        shutil.rmtree(ordner, ignore_errors=True)


def _abschnitt_d(b, fe, A):
    b("")
    b("D  ECHTE DATEI VON DER KARTE  (NICHT vergleichbar)")
    b("   Haengt an genau dieser Datei - Groesse, Format, wo sie auf")
    b("   der Karte liegt. Steht hier, weil der Unterschied zwischen")
    b("   C und D selbst eine Auskunft ist.")
    pfad = _irgendein_cover(fe, A)
    if not pfad:
        b("   -- kein Cover gefunden, uebersprungen")
        return
    try:
        groesse = os.path.getsize(pfad)
    except OSError:
        b("   -- Cover nicht lesbar, uebersprungen")
        return
    b("   Datei      : %s (%d KB)"
      % (os.path.basename(pfad), groesse // 1024))
    ms, best = messen(lambda: A.original_lesen(pfad, ZIEL_B, ZIEL_H),
                      WDH_TEUER)
    b.posten("lesen und dekodieren (auf Kastenmass)", ms, best)
    ms, best = messen(lambda: A.original_lesen(pfad, 0, 0), WDH_TEUER)
    b.posten("lesen und dekodieren (volle Groesse)", ms, best)


def _irgendein_cover(fe, A):
    """Das erste Cover, das sich finden laesst - oder None.

    Absichtlich anspruchslos: der Bench soll auch auf einem Geraet
    ohne Artwork durchlaufen, nur eben ohne diesen Abschnitt."""
    try:
        for name, node, syskey in fe.cats:
            eintraege = node if isinstance(node, (list, tuple)) else None
            if not eintraege:
                continue
            for eintrag in eintraege[:50]:
                if not isinstance(eintrag, (list, tuple)) or len(eintrag) < 2:
                    continue
                if eintrag[1] == "folder":
                    continue
                p = A.art_path(syskey, eintrag[0])
                if p and os.path.exists(p):
                    return p
    except Exception:                                    # noqa: BLE001
        pass
    return None


# ---------------------------------------------------------------------
def lauf(fe, fm, A, S, startdauer=None, log=None):
    """Den kompletten Bench fahren und den Bericht als Text
    zurueckgeben. Bekommt alles, was er braucht, uebergeben - dieses
    Modul importiert das Frontend nicht, sonst haette man zwei
    Ladewege fuer dieselbe Datei."""
    b = Bericht(log)
    spiele = _kopf(b, fe, A, fm)
    _abschnitt_a(b, fe, spiele, startdauer)
    try:
        _abschnitt_b(b, fe, S, spiele)
    except Exception as e:                               # noqa: BLE001
        b("   ABSCHNITT B ABGEBROCHEN: %s: %s" % (type(e).__name__, e))
    try:
        _abschnitt_c(b, A)
    except Exception as e:                               # noqa: BLE001
        b("   ABSCHNITT C ABGEBROCHEN: %s: %s" % (type(e).__name__, e))
    try:
        _abschnitt_d(b, fe, A)
    except Exception as e:                               # noqa: BLE001
        b("   ABSCHNITT D ABGEBROCHEN: %s: %s" % (type(e).__name__, e))
    b("")
    b("=" * 62)
    b("Ende. Nichts auf der Karte wurde veraendert.")
    b("=" * 62)
    return b.text()
