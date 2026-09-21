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
    Messung von "eine Flaeche in einer Farbe".

    GEAENDERT (Build 178). Hier stand eine Schleife ueber jeden
    einzelnen Bildpunkt. Auf dem Geraet gemessen: **25,5 Sekunden**
    fuer 1200x1600 - zwei Drittel der gesamten Laufzeit des Benchs,
    und zwar reine Vorbereitung, bevor die erste Zahl entsteht. Fuer
    ein Werkzeug, das Leute auf ihren Geraeten laufen lassen sollen,
    ist das nicht zumutbar.

    Jetzt werden ACHT Zeilen ehrlich ausgerechnet, und jede Bildzeile
    entsteht daraus mit bytes.translate() - einer Tabelle je Zeile,
    damit nicht einfach dieselbe Zeile wiederholt dasteht.
    translate() laeuft in C; die Python-Schleife geht nur noch ueber
    die HOEHE statt ueber jeden Punkt. Gemessen 30 ms statt 25
    Sekunden.

    DIE ZUSAMMENSETZUNG IST NICHT BELIEBIG. Sie entscheidet ueber
    genau eine Zahl im Bericht: wie lange das Packen einer Miniatur
    dauert. Ein Bild aus einer Farbe waere in Nullkommanichts gepackt,
    reines Rauschen gar nicht. Deshalb halb flaechige Kacheln (wie der
    Hintergrund eines Covers), halb Rauschen und Verlaeufe (wie das
    Motiv). Das ergibt nachgemessen rund 48 % bei Packstufe 1 - und
    damit ungefaehr das, was das Geraet an einem echten Cover gemeldet
    hat. Der erreichte Wert steht im Bericht mit dabei, damit niemand
    ihn glauben muss."""
    basis = []
    for p in range(8):
        z = bytearray()
        s = (p * 2654435761 + 12345) & 0xFFFFFFFF
        for x in range(w):
            s = (1103515245 * s + 12345) & 0x7FFFFFFF
            if ((x >> 5) + p) & 1:
                # Flaechig, mit harter Kante zur Nachbarkachel.
                z.append((60 + p * 13) & 255)
                z.append((90 + p * 7) & 255)
                z.append((120 + p * 3) & 255)
            else:
                z.append((s >> 16) & 255)
                z.append(((x * 5 + p * 97) // 3) & 255)
                z.append(((x * 3) // 2) & 255)
            z.append(0)
        basis.append(bytes(z))
    raus = bytearray(w * h * 4)
    breite = w * 4
    for y in range(h):
        # Je Zeile eine eigene Verschiebung. Sie wandert nicht linear
        # mit y, sonst waeren zwei benachbarte Zeilen fuer zlib fast
        # dasselbe - und genau das soll die Messung nicht sein.
        d = (y * 37 + (y >> 3) * 11) & 255
        tabelle = bytes(((i + d) & 255) for i in range(256))
        raus[y * breite:(y + 1) * breite] = \
            basis[(y * 7 + (y >> 5)) % 8].translate(tabelle)
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


def testbild_art1(pix, w, h, stufe):
    """Dasselbe im eigenen Format - so liegt eine Miniatur im Cache.

    Die Packstufe wird UEBERGEBEN und kommt aus fe/art.py
    (THUMB_PACKSTUFE). Hier stand bis Build 178 eine feste 6, weil
    das der Vorgabewert von zlib ist - das Frontend packt aber seit
    Build 154 mit Stufe 1. Gemeldet wurden dadurch 1176 ms fuer
    etwas, das in Wirklichkeit rund halb so lange dauert. Eine Zahl,
    die nach Produktionskosten aussah und keine war."""
    return b"ART1" + struct.pack("<HH", w, h) + zlib.compress(pix, stufe)


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


def _zaehlen(node, tiefe=0):
    """Spiele in einem Kategoriebaum.

    GEAENDERT (Build 178): rechnet jetzt mit der ECHTEN Baumform
    ({"folders": {...}, "items": [...]}, siehe fe/scan.py) statt
    ueber alle Werte zu summieren und dabei zu hoffen. Das alte
    Vorgehen kam zufaellig auf die richtige Zahl - aber daneben stand
    _irgendein_cover() mit derselben Annahme und lag falsch. Eine
    Vermutung, die an einer Stelle aufgeht und an der naechsten nicht,
    ist keine Vermutung, die man stehen lassen sollte.

    Bleibt trotzdem defensiv: der Bench laeuft auf fremden Geraeten,
    und ein unerwarteter Knoten darf ihn nicht umbringen."""
    if tiefe > 6 or not isinstance(node, dict):
        return 0
    try:
        n = sum(1 for e in (node.get("items") or ())
                if isinstance(e, (list, tuple)) and len(e) >= 2
                and e[1] != "folder")
        for unter in (node.get("folders") or {}).values():
            n += _zaehlen(unter, tiefe + 1)
        return n
    except Exception:                                    # noqa: BLE001
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


def _groesste_kategorie(fe):
    """(Index, Eintragszahl, Name) der Kategorie mit den meisten
    Eintraegen DIREKT in ihrer Liste - oder (None, 0, "").

    Gezaehlt wird bewusst nur der Wurzelknoten und nicht der ganze
    Baum: gemessen wird ja die Liste, die tatsaechlich auf dem Schirm
    steht. Eine Kategorie mit 5000 Spielen in Unterordnern zeigt an
    der Wurzel vielleicht zwoelf Ordner - und waere damit genauso
    ungeeignet wie eine leere."""
    best_i, best_n, best_name = None, 0, ""
    try:
        for i, eintrag in enumerate(fe.cats):
            name, node = eintrag[0], eintrag[1]
            if not isinstance(node, dict):
                continue
            n = len(node.get("items") or ())
            if n > best_n:
                best_i, best_n, best_name = i, n, name
    except Exception:                                    # noqa: BLE001
        pass
    return best_i, best_n, best_name


def _abschnitt_b(b, fe, S, spiele):
    """Zeichnen - KALT und WARM getrennt (Build 178).

    Der erste Anlauf hat beides in eine Zahl geworfen, und die war
    dadurch nicht das, was draufstand. Auf dem Geraet des Nutzers kam
    "Spieleliste liste je Schritt 194 ms" heraus, waehrend das Raster
    daneben 72 ms brauchte. Das liest sich wie ein Befund ueber den
    Zeichenweg der Liste - in Wirklichkeit steckte darin, dass jeder
    Schritt ein Cover in voller Groesse NEU RECHNET, weil die
    Miniatur noch nicht vorlag.

    Beides ist echt und beides interessiert:

      KALT  So fuehlt es sich beim ersten Durchblaettern an, bevor
            "Miniaturen vorbereiten" gelaufen ist.
      WARM  Derselbe Weg noch einmal ueber dieselben Spiele, jetzt
            mit vorliegenden Miniaturen. DAS ist die Zahl ueber den
            Zeichenweg.

    Und noch eine ehrliche Einschraenkung, die in den Bericht gehoert:
    hier wird in einer engen Schleife gezeichnet. Beim echten
    Scrollen laesst das Frontend die Boxart-Spalte aus, sobald schnell
    geblaettert wird (Build 76) - das greift hier nicht. Die
    Kalt-Zahl ist damit die OBERGRENZE, nicht der Alltag.

    WELCHE KATEGORIE GEMESSEN WIRD (Build 179). Das stand hier
    nirgends - und war deshalb ein Zufall: der Zeiger blieb einfach
    dort stehen, wo die Schleife ueber die Hauptseite ihn liegen
    gelassen hatte. Auf dem Geraet des Nutzers war das im ersten Lauf
    PlayStation, im zweiten Super Game Boy. Seine Rueckmeldung:

        "der bench landet immer im supergameboy dann passiert nichts
         mehr, es werden keine covers gescrollt nichts. der erste
         bench landete im playstation, dort scrollte er dann weiter"

    Genau so ist es: eine Kategorie mit einem einzigen Eintrag laesst
    item_i durch die Modulo-Rechnung auf 0 stehen, das Bild aendert
    sich nie, und gemessen wird ein Standbild. Damit erklaeren sich
    auch die drei Zahlen 52.98 / 52.97 / 52.99 aus jenem Lauf - drei
    voellig verschiedene Zeichenwege, identisch auf die Hundertstel,
    weil keiner von ihnen etwas zu tun hatte.

    Und es macht den ganzen Abschnitt unvergleichbar: zwei Geraete
    haetten in verschiedenen Kategorien gemessen, ohne dass es
    irgendwo gestanden haette. Jetzt wird die groesste Kategorie
    bewusst gewaehlt, und ihr Name und ihre Eintragszahl stehen im
    Bericht."""
    b("")
    b("B  ZEICHNEN  (%d Schritte je Ansicht, Bestand des Geraets)"
      % SCHRITTE)
    b("   kalt = Miniatur muss erst gerechnet werden")
    b("   warm = dieselben Spiele noch einmal, Miniatur liegt vor")
    b("   (beim echten Scrollen laesst das Frontend die Boxart-Spalte")
    b("    aus, sobald schnell geblaettert wird - kalt ist die")
    b("    Obergrenze, nicht der Alltag)")
    fbo = fe.fb
    kat_i, kat_n, kat_name = _groesste_kategorie(fe)
    if kat_i is None:
        b("   -- keine Kategorie mit Eintraegen gefunden")
    else:
        b("   gemessen in: %s (%d Eintraege in der Liste)"
          % (kat_name, kat_n))
        if kat_n < 20:
            b("   ACHTUNG: das ist WENIG. Die Zahlen der Spieleliste")
            b("   sagen bei so kurzer Liste kaum etwas aus.")
    for seite, name in ((0, "Hauptseite"), (1, "Spieleliste")):
        fe.page = seite
        if seite == 1 and kat_i is not None:
            # NICHT dort messen, wo die Hauptseiten-Schleife den
            # Zeiger zufaellig liegen gelassen hat - siehe oben.
            fe.cat_i = kat_i
            fe.nav_path = []
        for ansicht in S.ANSICHTEN:
            try:
                if seite == 0:
                    fe.ansicht_haupt_setzen(ansicht)
                else:
                    fe.ansicht_setzen(ansicht)
            except Exception:                            # noqa: BLE001
                continue

            def _voll():
                # Erzwungen, damit nicht der schnelle Pfad gemessen
                # wird und trotzdem "voller Aufbau" darueber steht.
                fe._force_full_redraw = True
                fbo.mark_full_redraw()
                fe.draw()

            def _durchlauf():
                # Immer am selben Punkt anfangen - sonst laeuft der
                # warme Durchgang ueber ANDERE Spiele als der kalte,
                # und der Vergleich der beiden Zahlen waere wertlos.
                if seite == 0:
                    fe.cat_i = 0
                else:
                    fe.item_i = 0
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
                ms, best = messen(_voll, WDH_TEUER)
                b.posten("%s %-8s voller Aufbau" % (name, ansicht), ms, best)
            except Exception as e:                       # noqa: BLE001
                b("   %-38s FEHLER %s" % ("%s %s voll" % (name, ansicht), e))
                continue

            try:
                kalt, _ = messen(_durchlauf, 1)
                # Die Miniaturen werden im Hintergrund weggeschrieben
                # (_thumb_cache_put_async). Ohne diese Pause waere der
                # warme Durchgang teils noch ein kalter, und zwar je
                # nach Geraet unterschiedlich weit - also nicht
                # vergleichbar.
                time.sleep(1.0)
                warm, _ = messen(_durchlauf, 1)
                b.posten("%s %-8s je Schritt kalt" % (name, ansicht),
                         kalt / SCHRITTE)
                # Den Faktor nur nennen, wenn es wirklich einen gibt.
                # Sonst stuende bei jedem Eintrag "(1x billiger)" -
                # eine Aussage, die keine ist, und bei Rauschen sogar
                # eine falsche.
                zusatz = ""
                if warm > 0 and kalt / warm >= 1.2:
                    zusatz = "(%.1fx billiger als kalt)" % (kalt / warm)
                elif warm > 0 and kalt / warm <= 0.83:
                    zusatz = "(warm LANGSAMER - im Rauschen)"
                b.posten("%s %-8s je Schritt warm" % (name, ansicht),
                         warm / SCHRITTE, None, zusatz)
            except Exception as e:                       # noqa: BLE001
                b("   %-38s FEHLER %s"
                  % ("%s %s Schritt" % (name, ansicht), e))
    # Der reine Bildtransport, ohne alles davor. Die Zahl, gegen die
    # jede Zeichenoptimierung sich messen lassen muss - schneller als
    # das geht nicht.
    #
    # ZWEIMAL, und das ist der Punkt (Build 179): einmal ohne das
    # Warten auf den Bildaufbau, einmal mit. Die Werte oben sind alle
    # ohne gemessen, sonst raste jede Zahl auf ein Vielfaches der
    # Bildperiode ein und man saehe nur noch die Bildwiederholrate.
    # Was das Warten kostet, gehoert trotzdem in den Bericht - es ist
    # ja echte Wartezeit, nur eben keine Rechenzeit.
    try:
        ohne, best = messen(lambda: fbo.flip(skip_vsync=True), WDH_TEUER)
        b.posten("Voller Flip ohne Vsync (%.1f MB)"
                 % (fbo.size / 1048576.0), ohne, best)
        mit, _ = messen(lambda: fbo.flip(skip_vsync=False), WDH_TEUER)
        b.posten("Voller Flip mit Vsync", mit, None,
                 "das Warten kostet %.1f ms" % max(0.0, mit - ohne))
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

        stufe = getattr(A, "THUMB_PACKSTUFE", 1)

        def _schreiben():
            with open(datei, "wb") as f:
                f.write(testbild_art1(roh, ZIEL_B, ZIEL_H, stufe))
        ms, best = messen(_schreiben, WDH_TEUER)
        groesse = os.path.getsize(datei)
        # Das Packverhaeltnis steht bewusst mit dabei: wie lange das
        # Packen dauert, haengt am Bildinhalt, und so muss niemand
        # glauben, dass das Testbild sich wie ein echtes Cover
        # verhaelt - er sieht es.
        b.posten("Miniatur packen und schreiben", ms, best,
                 "%d KB aus %d KB (%.0f %%), Packstufe %d"
                 % (groesse // 1024, len(roh) // 1024,
                    100.0 * groesse / max(1, len(roh)), stufe))

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


def _eintraege(node, tiefe=0):
    """Alle Spiel-Eintraege eines Kategorieknotens, flach.

    NEU (Build 178). Vorher stand hier die Annahme, ein Knoten sei
    eine Liste. Er ist aber ein Dict aus "folders" und "items" (siehe
    fe/scan.py, _node_to_json) - und die Suche ist deshalb bei JEDER
    Kategorie sofort weitergesprungen. Auf einem Geraet mit 30064
    Spielen meldete der Bench "kein Cover gefunden", und der ganze
    Abschnitt D lief nie. Ein stiller Fehlschlag, der aussah wie ein
    Befund ueber den Bestand des Nutzers."""
    if tiefe > 6 or not isinstance(node, dict):
        return
    for e in node.get("items") or ():
        if isinstance(e, (list, tuple)) and len(e) >= 2 and e[1] != "folder":
            yield e
    for unter in (node.get("folders") or {}).values():
        for e in _eintraege(unter, tiefe + 1):
            yield e


def _irgendein_cover(fe, A):
    """Das erste Cover, das sich finden laesst - oder None.

    Absichtlich anspruchslos: der Bench soll auch auf einem Geraet
    ohne Artwork durchlaufen, nur eben ohne diesen Abschnitt. Die
    Obergrenze verhindert, dass die Suche bei einem grossen Bestand
    ohne jedes Artwork minutenlang ueber die Karte laeuft."""
    versuche = 0
    try:
        for _name, node, syskey in fe.cats:
            for eintrag in _eintraege(node):
                versuche += 1
                if versuche > 400:
                    return None
                p = A.art_path(syskey, eintrag[0])
                if p and os.path.exists(p):
                    return p
    except Exception:                                    # noqa: BLE001
        pass
    return None


# ---------------------------------------------------------------------
class _Messbedingungen(object):
    """Alles, was waehrend Abschnitt B anders sein muss als im
    Normalbetrieb - an einer Stelle, mit Begruendung, und hinterher
    wieder zurueckgestellt.

    DREI DINGE, jedes aus einem Fehler im vorigen Lauf geboren:

    1. DER MINIATUREN-CACHE ZEIGT IN EINEN TEMPORAEREN ORDNER.
       Zeichnen rechnet Cover, und ein gerechnetes Cover wird
       weggeschrieben - der Bench hat also auf die Karte geschrieben,
       waehrend im Bericht stand, er tue das nicht.

    2. DAS AUSLAGERN AN DEN ARBEITSPROZESS WIRD ABGESCHALTET.
       Der Vorauslader ist seit Build 102 ein EIGENER PROZESS
       (subprocess.Popen in fe/prewarm.py). Punkt 1 wirkt deshalb
       nur im Elternprozess: der Arbeitsprozess schrieb weiter auf
       die Karte, und der Elternprozess suchte im temporaeren Ordner
       und fand nie etwas. Ein dauerhafter Fehlschlag, bei dem jeder
       Schritt sofort abbrach - gemessen wurde nichts mehr.

       Mit auslagern=None rechnet der Zeichenweg selbst, im selben
       Prozess. Kalt misst damit die echte Berechnung, warm den
       Lesevorgang aus dem Cache, und auf der Karte landet nichts.

    3. DAS VSYNC-WARTEN FAELLT WEG.
       flip() wartet auf den Bildaufbau, im Code mit "8-17 ms auf
       echter Hardware" beziffert. Bei 60 Hz rastet damit jeder
       Schritt auf ein Vielfaches von 16,7 ms ein - im zweiten Lauf
       standen drei Ansichten bei 49.94, 50.21 und 49.95 ms, also
       exakt drei Bildperioden. Gemessen wurde die Bildwiederholrate,
       nicht das Frontend. Das Warten wird darum uebersprungen und
       weiter unten EINMAL separat ausgewiesen."""

    def __init__(self, A, fm, fe, hd):
        self.A, self.fm, self.fe, self.hd = A, fm, fe, hd
        self.ordner = None
        self.alt_base = self.alt_dir = None
        self.alt_auslagern = self._kein_auslagern = None
        self.alt_vsync = None

    def __enter__(self):
        A, fe = self.A, self.fe
        self.alt_base, self.alt_dir = A.THUMB_CACHE_BASE, A.THUMB_CACHE_DIR
        try:
            self.ordner = tempfile.mkdtemp(prefix="dragend_bench_cache_")
            A.THUMB_CACHE_BASE = self.ordner
            A.thumb_cache_modus_setzen(self.hd)
        except Exception:                                # noqa: BLE001
            pass
        # (2) Arbeitsprozess aus dem Spiel nehmen.
        try:
            self.alt_auslagern = A.ART.auslagern
            A.ART.auslagern = None
            self._kein_auslagern = True
        except Exception:                                # noqa: BLE001
            self._kein_auslagern = False
        try:
            self.fm.PREWARMER.beenden()
        except Exception:                                # noqa: BLE001
            pass
        # (3) Kein Warten auf den Bildaufbau.
        try:
            self.alt_vsync = fe._vsync_ueberspringen
            fe._vsync_ueberspringen = lambda *_a, **_k: True
        except Exception:                                # noqa: BLE001
            pass
        return self

    def __exit__(self, *_a):
        A, fe = self.A, self.fe
        if self.alt_vsync is not None:
            try:
                fe._vsync_ueberspringen = self.alt_vsync
            except Exception:                            # noqa: BLE001
                pass
        if self._kein_auslagern:
            try:
                A.ART.auslagern = self.alt_auslagern
            except Exception:                            # noqa: BLE001
                pass
        if self.alt_base is not None:
            A.THUMB_CACHE_BASE = self.alt_base
        if self.alt_dir is not None:
            A.THUMB_CACHE_DIR = self.alt_dir
        if self.ordner:
            # Kurz warten: ein Hintergrund-Thread, der nach dem
            # Aufraeumen noch schreibt, legt den Ordner wieder an.
            time.sleep(0.5)
            shutil.rmtree(self.ordner, ignore_errors=True)
            self.ordner = None
        return False



def lauf(fe, fm, A, S, startdauer=None, log=None):
    """Den kompletten Bench fahren und den Bericht als Text
    zurueckgeben. Bekommt alles, was er braucht, uebergeben - dieses
    Modul importiert das Frontend nicht, sonst haette man zwei
    Ladewege fuer dieselbe Datei."""
    b = Bericht(log)
    spiele = _kopf(b, fe, A, fm)
    _abschnitt_a(b, fe, spiele, startdauer)
    try:
        hd = getattr(fe, "fb", None) is not None and fe.fb.height >= 720
        with _Messbedingungen(A, fm, fe, hd):
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
