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

# 4 ab Build 216 (Abschnitt J), 3 ab Build 215 (Abschnitt I),
# 2 ab Build 214 (Abschnitt H). Die Nummer steht im Kopf
# jedes Berichts, damit zwei Berichte vergleichbar SIND und nicht nur so
# aussehen - wer eine 1 und eine 2 nebeneinanderlegt, sieht sofort, dass
# in der einen ein Abschnitt fehlt. Die Abschnitte A bis G haben sich
# dabei nicht geaendert, ihre Zahlen bleiben also vergleichbar.
BENCH_VERSION = 7

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
    # DIE PROFILIERUNG MUSS HIER STEHEN, und zwar laut (Build 224).
    #
    # WAS PASSIERT IST: auf dem Geraet des Nutzers lag seit einer
    # frueheren Fehlersuche die Datei /media/fat/frontend/profile. Damit
    # laeuft um JEDEN Seitenaufbau ein vollstaendiges cProfile, und
    # danach gehen PERF-Zeile, zwoelf PROFILE-Zeilen und die
    # TEXTCACHE-Bilanz EINZELN auf die SD-Karte - achtzehn Dateizugriffe
    # je Scrollschritt. Aufgefallen ist es erst, als Abschnitt J in
    # Build 222 anfing, die Rufer der Dateizugriffe zu nennen.
    #
    # Die Zahlen davor waren dadurch rund doppelt so hoch wie die
    # Wirklichkeit: Spieleliste 97,7 gegen 47,2 ms je Schritt,
    # Hauptseite-Galerie 106,7 gegen 58,3. Mehrere Builds lang wurde an
    # Zehntelmillisekunden gefeilt, waehrend daneben ein Profiler lief.
    #
    # Ein Messgeraet, das seinen eigenen Zustand verschweigt, ist ein
    # schlechtes Messgeraet. Deshalb steht es jetzt im Kopf, mit
    # Ausrufezeichen und mit dem Befehl zum Abstellen daneben.
    # fm ist das Frontend-Modul selbst (dort liegt auch _skala und die
    # LATEST_BUILD.json daneben) - der Schalter wird also direkt dort
    # gefragt, nicht ueber sys.modules und den Klassennamen.
    try:
        _an = bool(fm.profiling_an())
        _flagge = getattr(fm, "PROFILE_FLAG", "?")
    except Exception:                                    # noqa: BLE001
        _an, _flagge = False, "?"
    if _an:
        b("")
        b("!!! ACHTUNG: DIE PROFILIERUNG IST EINGESCHALTET !!!")
        b("    Um jeden Seitenaufbau laeuft ein vollstaendiges cProfile,")
        b("    und jede Messung darunter ist dadurch ZU HOCH - auf dem")
        b("    DE10-Nano gemessen rund um das Doppelte.")
        b("    Abstellen:  rm %s" % _flagge)
        b("    (oder DRAGEND_PROFILE aus der Umgebung nehmen), dann")
        b("    diesen Bench noch einmal laufen lassen.")
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


def _abschnitt_b(b, fe, S, spiele, A=None):
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
    b("   kalt  = Miniatur muss erst gerechnet werden")
    b("   Karte = Miniatur liegt auf der Karte, aber nicht im RAM")
    b("   warm  = sie liegt im RAM")
    b("   (beim echten Scrollen laesst das Frontend die Boxart-Spalte")
    b("    aus, sobald schnell geblaettert wird - kalt ist die")
    b("    Obergrenze, nicht der Alltag)")
    # EHRLICHKEIT UEBER DIE EIGENE MESSUNG (Build 218): diese Zahlen
    # kommen aus fe.draw(), und das ist fuer die LISTE der volle
    # Neuaufbau - ihr leichter Pfad (_draw_navigate_items) wird von
    # draw() nie gerufen. Die Reihe bleibt absichtlich so, damit sie mit
    # allen Laeufen seit Build 177 vergleichbar bleibt; wer den echten
    # Schritt sehen will, liest Abschnitt J.
    b("   HINWEIS: fuer die LISTE ist das der volle Neuaufbau (so wie")
    b("   nach dem Stillstand). Den leichten Schritt, der beim Scrollen")
    b("   laeuft, misst Abschnitt J.")
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
                # DER DRITTE ZUSTAND (Build 188). Zwischen "muss
                # gerechnet werden" und "liegt im RAM" liegt der Fall,
                # der beim Scrollen durch eine grosse Sammlung der
                # HAEUFIGSTE ist: die Miniatur liegt auf der Karte,
                # aber nicht mehr im Speicher - verdraengt, oder das
                # Frontend wurde neu gestartet. Der Weg dorthin ist
                # Lesen, Entpacken und Eintragen, und der stand bisher
                # in keiner Zahl. Genau dieser Zustand entscheidet
                # aber, wie sich das Geraet im Alltag anfuehlt.
                karte = None
                if A is not None:
                    try:
                        A.ART.ram_leeren()
                        karte, _ = messen(_durchlauf, 1)
                    except Exception:                    # noqa: BLE001
                        karte = None
                warm, _ = messen(_durchlauf, 1)
                b.posten("%s %-8s je Schritt kalt" % (name, ansicht),
                         kalt / SCHRITTE)
                if karte is not None:
                    zus = ""
                    if warm > 0 and karte / warm >= 1.2:
                        zus = "(%.1fx teurer als warm)" % (karte / warm)
                    b.posten("%s %-8s je Schritt Karte" % (name, ansicht),
                             karte / SCHRITTE, None, zus)
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
        # BUILD 205: derselbe Transport, aber als BAND - und zwar in
        # Millisekunden JE MEGABYTE, damit beide vergleichbar sind.
        #
        # DIE FRAGE, UND WARUM SIE HIER STEHT. Im Profillauf des Nutzers
        # kostete ein Schritt in der Rasteransicht 68 ms, davon 45 im
        # Flippen: zwei Baender mit zusammen 385 Bildzeilen, also rund
        # 2,8 MB, mit 28 ms reiner Kopierzeit. Mit der Rate des vollen
        # Flips (7,9 MB in 12,6 ms) waeren das 4,5 ms gewesen -
        # sechsmal weniger. Entweder ist eine Teilkopie je Byte
        # tatsaechlich viel teurer als eine ganze, oder eine meiner
        # Annahmen stimmt nicht.
        #
        # Eine Erklaerung habe ich schon widerlegt: flip_rows() legt mit
        # "self.buf[off:end]" eine Zwischenkopie an, flip() nicht. Auf
        # dem Entwicklungsrechner kostet das nichts (Faktor 1,00-1,05
        # gemessen) - dort ist mm aber ein bytearray und kein mmap auf
        # ungepufferten Bildspeicher. Genau deshalb muss es das Geraet
        # beantworten und nicht ich.
        #
        # Wenn ein Band je Megabyte deutlich teurer ist als ein
        # Vollbild, betrifft das JEDEN leichten Zeichenweg im Frontend -
        # dann waere das die wichtigste Zahl im ganzen Bericht.
        try:
            hoehe = max(1, min(fbo.height // 3, fbo.height))
            mb_band = (hoehe * fbo.stride) / 1048576.0
            mb_voll = fbo.size / 1048576.0
            band, b_best = messen(
                lambda: fbo.flip_rows(0, hoehe, skip_vsync=True),
                WDH_TEUER)
            b.posten("Band-Flip ohne Vsync (%.1f MB)" % mb_band,
                     band, b_best)
            # BUILD 206: der direkte A/B-Vergleich, damit der Gewinn
            # belegt ist und nicht gerechnet. Links der alte Weg mit
            # Zwischenkopie, rechts der neue ueber memoryview - dieselbe
            # Datenmenge, derselbe Lauf, dieselbe Maschine.
            try:
                _off = 0
                _ende = hoehe * fbo.stride

                def _alt():
                    fbo.mm[_off:_ende] = fbo.buf[_off:_ende]

                alt_ms, alt_best = messen(_alt, WDH_TEUER)
                b.posten("  derselbe Streifen auf dem alten Weg",
                         alt_ms, alt_best)
                if band > 0:
                    b("   MEMORYVIEW   : spart %.1f ms auf %.1f MB "
                      "(Faktor %.1f)"
                      % (max(0.0, alt_ms - band), mb_band,
                         alt_ms / band if band else 0))
            except Exception as e:                       # noqa: BLE001
                b("   Vergleich alt/neu: nicht messbar (%s)" % e)
            if ohne > 0 and mb_band > 0 and mb_voll > 0:
                r_voll = ohne / mb_voll
                r_band = band / mb_band
                b("   JE MEGABYTE : Vollbild %.2f ms, Band %.2f ms"
                  % (r_voll, r_band))
                if r_band > r_voll * 1.5:
                    b("                 -> ein Band ist je Byte %.1fmal"
                      % (r_band / r_voll))
                    b("                    teurer. Das betrifft JEDEN")
                    b("                    leichten Zeichenweg.")
                elif r_band < r_voll * 0.67:
                    b("                 -> ein Band ist sogar billiger")
                    b("                    je Byte. Dann liegen die")
                    b("                    45 ms aus dem Profil woanders.")
                else:
                    b("                 -> gleich teuer je Byte. Die")
                    b("                    Teilkopie ist also nicht das")
                    b("                    Problem.")
        except Exception as e:                           # noqa: BLE001
            b("   Band-Flip: nicht messbar (%s)" % e)
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


class _KeinVergleich(Exception):
    """Kein Vergleichswert zu holen - siehe _abschnitt_e().

    Eine eigene Ausnahme und kein return: der Abschnitt hat einen
    except-Zweig, der "uebersprungen" meldet und den Rest des Berichts
    stehen laesst, und genau dort soll dieser Fall landen."""


def _abschnitt_e(b, fe):
    """Lohnt Scroll-Blitting auf der Hauptseite - AUF DIESEM GERAET?

    DIE FRAGE, UND WARUM SIE UEBERHAUPT NOCH EINMAL GESTELLT WIRD.

    Rollt beim Scrollen im Hauptmenue die Liste weiter, gibt es keinen
    leichten Zeichenweg: es laeuft ein voller Aufbau. Im Log des Nutzers
    kostet das "rows=77", also 77 ms fuer zwoelf Zeilen Text.

    Die naheliegende Abhilfe waere, den schon gezeichneten Block im
    Speicher um eine Zeile zu verschieben und nur die neu freigewordene
    Zeile zu setzen. Genau das gab es schon einmal (Build 96) und wurde
    wieder entfernt (Build 102), mit Messwerten:

        CRT  320x240    0.50 ms voll -> 0.65 ms geblittet
        720p 1280x720   1.25 ms voll -> 1.63 ms geblittet
        HDMI 1920x1080  2.04 ms voll -> 2.84 ms geblittet

    Es kostete in jeder Aufloesung. Der Kommentar an der Fundstelle sagt
    ausdruecklich, dass das festgehalten wurde, damit niemand dieselbe
    Idee ein zweites Mal baut - und daran halte ich mich.

    ABER: "2.04 ms voll" ist ein Wert vom Entwicklungsrechner. Auf dem
    Geraet des Nutzers kostet derselbe Aufbau 77 ms. Das Verhaeltnis
    zwischen Schrift setzen und Speicher schieben ist auf einer schwachen
    ARM-CPU ein voellig anderes als auf einem PC - dort ist Text billig
    und die Kopie teuer, hier umgekehrt. Ein Schluss, der auf dem einen
    Rechner richtig ist, kann auf dem anderen falsch sein.

    Deshalb wird hier NICHT das Feature nachgebaut, sondern es werden
    seine ZUTATEN gemessen, jede einzeln und jede so einfach, dass an
    ihrer Richtigkeit nichts zu deuten ist:

        - was ein voller Aufbau der Hauptseite kostet,
        - was das Verschieben des Listenblocks kostet,
        - was EINE Kategoriezeile kostet.

    Die Entscheidung folgt dann aus der Rechnung, nicht aus einer
    Vermutung. Gezeichnet wird nur in den Puffer, nie auf den Schirm."""
    b("")
    b("E  SCROLL-BLITTING IM HAUPTMENUE: LOHNT ES HIER?")
    b("   Gemessen werden die Zutaten, nicht das Feature. Siehe den")
    b("   Kommentar im Quelltext: dieselbe Idee war schon einmal")
    b("   gebaut und wurde als Verlust entfernt - allerdings mit")
    b("   Messwerten vom Entwicklungsrechner.")
    fb = getattr(fe, "fb", None)
    if fb is None:
        b("   -- kein Bildspeicher, uebersprungen")
        return
    try:
        L = fe.layout_cats()
    except Exception as e:                               # noqa: BLE001
        b("   -- Layout nicht ermittelbar (%s), uebersprungen" % e)
        return
    visible = int(L.get("visible") or 0)
    rowh = int(L.get("rowh") or 0)
    y0 = int(L.get("y0") or 0)
    if visible < 3 or rowh < 2:
        b("   -- Liste zu kurz fuer eine Aussage, uebersprungen")
        return
    stride = fb.stride
    hoehe = min(visible * rowh, max(0, fb.height - y0))
    if hoehe <= rowh:
        b("   -- Listenbereich zu klein, uebersprungen")
        return
    b("   Liste      : %d Zeilen a %d Punkte, Block %d Zeilen hoch"
      % (visible, rowh, hoehe))

    try:
        ms_voll, best_voll = messen(lambda: fe.draw_page_cats(flip=False))
        b.posten("voller Aufbau der Hauptseite", ms_voll, best_voll)

        # Der Block um genau eine Zeile nach oben. Eine einzige
        # Schnittzuweisung - mehr ist ein Verschieben nicht.
        a = y0 * stride
        e = (y0 + hoehe - rowh) * stride
        q0 = a + rowh * stride
        q1 = e + rowh * stride
        if q1 > len(fb.buf):
            b("   -- Block passt nicht, Verschieben uebersprungen")
            return

        def schieben():
            fb.buf[a:e] = fb.buf[q0:q1]

        ms_schieb, best_schieb = messen(schieben)
        b.posten("Listenblock um eine Zeile verschieben",
                 ms_schieb, best_schieb)

        maxc = max(4, (int(L.get("list_right") or 0) - int(L.get("ox") or 0))
                   // (8 * int(L.get("s") or 1)))

        def eine_zeile():
            fe._draw_cat_row(fe.cat_scroll, 0, L, maxc)

        ms_zeile, best_zeile = messen(eine_zeile)
        b.posten("eine Kategoriezeile zeichnen", ms_zeile, best_zeile)

        # DER VERGLEICHSWERT WAR FALSCH GEWAEHLT, und der Fehler ist
        # meiner (bemerkt beim Nachrechnen des Laufs vom 28.09.2026).
        #
        # Verglichen wurde gegen den VOLLEN Aufbau (dort 83,1 ms). Beim
        # gehaltenen Scrollen laeuft aber nicht der volle Aufbau, sondern
        # der schnelle Pfad - und der stand im selben Bericht, in
        # Abschnitt B, mit 59,7 ms. Die Ersparnis war damit um 23 ms zu
        # gross angegeben, und aus Faktor 1,5 wurde Faktor 2,1.
        #
        # Es bleibt ein Gewinn, aber die richtige Zahl entscheidet, ob er
        # den Umbau wert ist. Deshalb wird der schnelle Pfad jetzt selbst
        # gemessen - EIN Schritt, so wie er beim Scrollen anfaellt.
        # DIESER BLOCK IST BEIM ERSTEN LAUF AUF DEM GERAET GESTORBEN,
        # und der Fehler war meiner: "nicht messbar (IndexError: list
        # index out of range), uebersprungen" - und damit war das
        # ERGEBNIS des ganzen Abschnitts weg, obwohl alle drei Zutaten
        # darueber sauber gemessen waren.
        #
        # Die Ursache: draw() zeichnet die Seite, die gerade eingestellt
        # ist. Abschnitt B laeuft VOR diesem hier und laesst fe.page auf
        # 1 stehen, dazu einen item_i, der zu einer anderen Kategorie
        # gehoerte. draw() ist dann in der Spieleliste gelandet und dort
        # ueber das Ende gelaufen.
        #
        # Die Lehre steht schon zweimal in diesem Modul: ein Abschnitt
        # darf sich NICHT darauf verlassen, in welchem Zustand der
        # vorige ihn zuruecklaesst (siehe _groesste_kategorie() in
        # Abschnitt B, Build 178). Also selbst einstellen - und
        # hinterher zuruecksetzen, damit der naechste Abschnitt es
        # ebenso vorfindet wie erwartet.
        _alte_seite = getattr(fe, "page", 0)
        _alter_cat = getattr(fe, "cat_i", 0)
        fe.page = 0
        if not getattr(fe, "cats", None):
            b("   -- keine Kategorien, Schritt-Vergleich uebersprungen")
            raise _KeinVergleich()
        fe.cat_i = min(_alter_cat, len(fe.cats) - 1)

        # DER VERGLEICH WAR NOCH IMMER SCHIEF, und das hat der Lauf vom
        # 28.09. selbst gezeigt: "EIN Schritt, schneller Pfad = 123,06
        # ms" bei einem VOLLEN Aufbau von 80,95 ms. Ein Schritt kann
        # nicht teurer sein als der ganze Neuaufbau. Zwei Fehler steckten
        # darin:
        #
        #   1. fe.draw() ruft den leichten Pfad der Hauptseite GAR NICHT
        #      (_draw_navigate_cats haengt an run(), nicht an draw()) -
        #      gemessen wurde also wieder der volle Aufbau.
        #   2. Dazu kamen ein Vollbild-Flip und die Hausarbeit, waehrend
        #      auf der anderen Seite der Rechnung (verschieben + zwei
        #      Zeilen) NUR in den Puffer gezeichnet wird.
        #
        # Jetzt der leichte Pfad, und beide Seiten OHNE Flip: dessen Zeit
        # ist in _perf_flip ausgewiesen und wird abgezogen. Damit stehen
        # links und rechts dieselbe Sorte Arbeit.
        _fenster_e = max(2, min(int(getattr(fe, "cats_visible", 0) or 0) - 2,
                                len(fe.cats) - 1))
        _zaehler_e = [0]
        _flip_e = [0.0]

        def _schritt():
            _zaehler_e[0] += 1
            alt = fe.cat_i
            fe.cat_i = _zaehler_e[0] % _fenster_e
            _f0 = getattr(fe, "_perf_flip", 0.0)
            if not fe._draw_navigate_cats(alt):
                fe.draw()
            _flip_e[0] += getattr(fe, "_perf_flip", 0.0) - _f0

        try:
            for _ in range(4):
                _schritt()                   # warmlaufen, nicht messen
            _flip_e[0] = 0.0
            _vorher = _zaehler_e[0]
            ms_schritt, best_schritt = messen(_schritt)
            _laeufe = max(1, _zaehler_e[0] - _vorher)
            ms_flip_e = _flip_e[0] * 1000.0 / _laeufe
        finally:
            fe.page = _alte_seite
            fe.cat_i = min(_alter_cat, max(0, len(fe.cats) - 1))
        b.posten("EIN Schritt, leichter Pfad", ms_schritt, best_schritt)
        # best ausdruecklich als None: die Attrappe in tools/test_bench.py
        # verlangt das dritte Argument, und ein Messabschnitt soll nicht
        # daran haengen, welche Vorgabewerte der Bericht gerade hat.
        b.posten("davon der Flip (wird abgezogen)", ms_flip_e, None)
        ms_schritt = max(0.0, ms_schritt - ms_flip_e)

        # Die Rechnung, offen hingeschrieben: beim Weiterrollen muessen
        # zwei Zeilen neu gesetzt werden (die neu freigewordene und die
        # Markierung).
        geblittet = ms_schieb + 2 * ms_zeile
        b("")
        b("   RECHNUNG   : verschieben %.1f + zwei Zeilen %.1f = %.1f ms"
          % (ms_schieb, 2 * ms_zeile, geblittet))
        b("                leichter Pfad OHNE Flip          = %.1f ms"
          % ms_schritt)
        b("                voller Aufbau (nur zum Einordnen)= %.1f ms"
          % ms_voll)
        # Ab hier wird gegen den SCHNELLEN PFAD gerechnet, nicht gegen
        # den vollen Aufbau.
        ms_voll = ms_schritt
        # KEIN URTEIL AUS NICHTS. Beim ersten Anlauf stand hier direkt
        # der Vergleich - und im Pruefstand, der die Uhr einfriert, kamen
        # drei Nullen heraus, woraufhin der Abschnitt seelenruhig "es
        # lohnt NICHT" meldete. Ein Messwerkzeug, das aus fehlenden Daten
        # ein Ergebnis macht, ist schlimmer als keines: es klingt wie ein
        # Befund. Deshalb erst die Frage, ob ueberhaupt etwas gemessen
        # wurde.
        if ms_voll < 0.05:
            b("   ERGEBNIS   : NICHT MESSBAR - der volle Aufbau kommt auf")
            b("                %.3f ms heraus. Das ist keine Aussage,"
              % ms_voll)
            b("                sondern eine stehende oder zu grobe Uhr.")
        elif geblittet < ms_voll * 0.8:
            b("   ERGEBNIS   : es LOHNT hier - %.1f ms gespart je Schritt,"
              % (ms_voll - geblittet))
            b("                also Faktor %.1f. Auf dem Entwicklungs-"
              % (ms_voll / max(0.01, geblittet)))
            b("                rechner war es umgekehrt.")
            b("                (Verglichen mit dem SCHNELLEN Pfad - bis")
            b("                 Build 215 stand hier der volle Aufbau,")
            b("                 und die Ersparnis war zu gross.)")
        elif geblittet < ms_voll:
            b("   ERGEBNIS   : knapp besser (%.1f ms) - zu wenig fuer den"
              % (ms_voll - geblittet))
            b("                Aufwand und das Risiko. Finger weg.")
        else:
            b("   ERGEBNIS   : es lohnt NICHT, genau wie damals auf dem")
            b("                Entwicklungsrechner. Build 102 bleibt")
            b("                richtig, und zwar auch hier.")
    except Exception as e:                               # noqa: BLE001
        # UEBERSPRUNGEN, nicht ABGEBROCHEN - und das ist ein
        # Unterschied, auf den tools/test_bench.py besteht. Ein
        # Messabschnitt, der nicht messen kann, sagt das und laesst den
        # Rest des Berichts stehen; beim ersten Anlauf ist genau das
        # schiefgegangen (ein unlesbarer Kategoriebaum liess
        # draw_page_cats() auffliegen, und der ganze Abschnitt meldete
        # ABGEBROCHEN). Der Bench ist ein Werkzeug fuer den Notfall - er
        # muss auch dann noch das liefern, was er messen KONNTE.
        b("   -- nicht messbar (%s: %s), uebersprungen"
          % (type(e).__name__, e))
    finally:
        # Der Puffer ist jetzt halb bemalt. Den naechsten echten Aufbau
        # voll erzwingen, damit auf dem Schirm nichts Halbes landet.
        try:
            fb.mark_full_redraw()
            fe._force_full_redraw = True
        except Exception:                                # noqa: BLE001
            pass


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



def _abschnitt_f(b, fe):
    """Was kostet ein Blick in den BILDSPEICHER - auf diesem Geraet?

    DER ANLASS IST EIN FEHLER VON MIR, und deshalb steht dieser
    Abschnitt hier. In Build 209 habe ich den Bildwaechter von acht
    einzelnen Bildpunkten auf ganze Zeilen umgestellt und die Kosten auf
    dem Entwicklungsrechner gemessen: 0,013 ms fuer 150 kB. Damit habe
    ich sogar begruendet, dass sich C dafuer nicht lohnt.

    Im Profillauf auf dem Geraet des Nutzers stand dann:

        2   0.004   0.002   0.004   0.002   _waechter_pruefen

    ZWEI MILLISEKUNDEN je Blick, das Hundertfuenfzigfache. Der
    Unterschied ist nicht die CPU, sondern WELCHER SPEICHER: auf dem PC
    ist mm ein bytearray im normalen RAM, auf dem Geraet ist es der
    Bildspeicher - ungecacht, ueber den Bus, und beim Lesen noch
    unangenehmer als beim Schreiben.

    Genau diese Zahl kann nur das Geraet liefern. Der Abschnitt misst
    deshalb drei Dinge nebeneinander, und die Verhaeltnisse sind die
    Aussage:

      - dieselbe Menge Bytes aus dem PUFFER lesen (normaler RAM),
      - dieselbe Menge aus dem BILDSPEICHER lesen,
      - und was ein Waechter-Blick in seiner jetzigen Form kostet.

    Wer hier spaeter etwas an den Proben aendert, sieht in einer Zeile,
    was es kostet - und muss es nicht auf dem falschen Rechner raten."""
    b("")
    b("-" * 62)
    b(" F  Lesen aus dem Bildspeicher (der Fehler aus Build 209)")
    b("-" * 62)
    fb = fe.fb
    if not getattr(fb, "_waechter_an", False):
        b("   -- Bildwaechter ist aus, nichts zu messen")
        return
    zb = int(getattr(fb, "_waechter_zeile_bytes", 0) or 0)
    proben = len(getattr(fb, "_waechter_offsets", ()) or ())
    if zb <= 0 or proben <= 0:
        b("   -- keine Proben eingerichtet, uebersprungen")
        return
    pro_blick = min(int(getattr(fb, "WAECHTER_PRO_BLICK", proben)), proben)
    b("   Proben     : %d Zeilen a %d Byte, %d je Blick (%d kB)"
      % (proben, zb, pro_blick, pro_blick * zb // 1024))

    menge = pro_blick * zb
    if menge > len(fb.buf) or menge > getattr(fb, "size", 0):
        b("   -- Bild zu klein fuer diese Menge, uebersprungen")
        return

    # Die drei Messungen. Bewusst mit demselben Byte-Umfang, sonst
    # vergleicht man Aepfel mit Birnen.
    ziel = bytearray(menge)
    mvz = memoryview(ziel)

    def aus_puffer():
        mvz[:] = memoryview(fb.buf)[0:menge]

    def aus_bildspeicher():
        mvz[:] = memoryview(fb.mm)[0:menge]

    ms_buf, best_buf = messen(aus_puffer)
    b.posten("%d kB aus dem Puffer (RAM)" % (menge // 1024),
             ms_buf, best_buf)
    ms_mm, best_mm = messen(aus_bildspeicher)
    b.posten("%d kB aus dem Bildspeicher" % (menge // 1024),
             ms_mm, best_mm)
    if ms_buf > 0:
        b("   %-38s %9.1fx" % ("Bildspeicher teurer als RAM um Faktor",
                               ms_mm / ms_buf))

    ms_w, best_w = messen(fb._waechter_pruefen)
    b.posten("ein Waechter-Blick, wie er jetzt laeuft", ms_w, best_w)
    b("")
    b("   Zum Vergleich: im Profillauf des Nutzers stand der Blick mit")
    b("   2,00 ms, als noch ALLE %d Proben je Blick angesehen wurden."
      % proben)
    ganz = ms_w * proben / float(max(1, pro_blick))
    b("   Alle %d auf einmal waeren hier %.2f ms." % (proben, ganz))


def _abschnitt_g(b, fe, A):
    """Was kostet die Dateisystem-Arbeit im Zeichenweg - auf DIESEM
    Geraet?

    ZWEI UMBAUTEN AUS BUILD 212 werden hier nachgemessen, und zwar
    getrennt, weil sie unterschiedlich gut begruendet sind:

    1. os.utime() je Cache-Treffer ist aus dem Lesepfad heraus. Fuer den
       ZEITgewinn gibt es schon eine Zahl von diesem Geraet (Build 74:
       0,1 ms je Marke) - der Umbau ist deshalb NICHT mit Geschwindigkeit
       begruendet, sondern mit Schreibzugriffen auf die Karte waehrend
       des Scrollens. Hier steht die Zahl trotzdem, damit niemand sie
       spaeter schaetzen muss.

    2. os.stat() je Nachschlagen ist aus dem Zeichenweg heraus. Dafuer
       gibt es KEINE Messung von echter Hardware, also wird auch nichts
       behauptet - das erledigt dieser Abschnitt.

    Gemessen wird mit einer echten Datei im Miniaturen-Zwischenspeicher,
    nicht mit einer erfundenen: nur so trifft es dieselbe Karte, dasselbe
    Dateisystem und dieselben Puffer wie im Betrieb."""
    b("")
    b("-" * 62)
    b(" G  Dateisystem im Zeichenweg (Build 212)")
    b("-" * 62)
    import os as _os
    import tempfile as _tempfile
    verz = getattr(A, "THUMB_CACHE_DIR", None)
    if not verz or not _os.path.isdir(verz):
        b("   -- kein Miniaturen-Verzeichnis, uebersprungen")
        return
    try:
        fd, probe = _tempfile.mkstemp(prefix="bench_", dir=verz)
        _os.write(fd, b"x" * 4096)
        _os.close(fd)
    except OSError as e:
        b("   -- konnte keine Probedatei anlegen (%s), uebersprungen" % e)
        return
    try:
        b("   Probedatei  : %s" % _os.path.basename(probe))

        ms_utime, best_utime = messen(lambda: _os.utime(probe, None))
        b.posten("os.utime auf die Karte (eine Marke)", ms_utime, best_utime)
        b("   %-38s %9.2f ms" % ("21 Kacheln, wie bisher je Aufbau",
                                 ms_utime * 21))

        ms_stat, best_stat = messen(lambda: _os.stat(probe))
        b.posten("os.stat, warm (Kernel kennt die Datei)", ms_stat, best_stat)
        b("   %-38s %9.2f ms" % ("21 Kacheln, wie bisher je Aufbau",
                                 ms_stat * 21))

        # Und der Schluessel als Ganzes - stat plus Zeichenkette plus
        # SHA1 -, einmal mit dem neuen Zwischenspeicher und einmal ohne.
        if hasattr(A, "_thumb_cache_key") and hasattr(A, "_quell_stat"):
            def mit_speicher():
                A._thumb_cache_key(probe, 270, 361)

            def ohne_speicher():
                A._quell_stat.pop(probe, None)
                A._thumb_cache_key(probe, 270, 361)

            ms_ohne, best_ohne = messen(ohne_speicher)
            b.posten("Cache-Schluessel OHNE Zwischenspeicher",
                     ms_ohne, best_ohne)
            A._thumb_cache_key(probe, 270, 361)     # einmal warmlaufen
            ms_mit, best_mit = messen(mit_speicher)
            b.posten("Cache-Schluessel MIT Zwischenspeicher",
                     ms_mit, best_mit)
            if ms_mit > 0:
                b("   %-38s %9.1fx" % ("gespart je Schluessel, Faktor",
                                       ms_ohne / ms_mit))
            b("   %-38s %9.2f ms" % ("21 Kacheln gespart je Aufbau",
                                     (ms_ohne - ms_mit) * 21))
            A._quell_stat.pop(probe, None)
        b("")
        b("   Zur Einordnung: das LESEN einer Miniatur kostet auf diesem")
        b("   Geraet laut Build 74 rund 11,2 ms, das Entpacken 1,3 ms.")
        b("   Daran gemessen entscheidet sich, ob die Zahlen oben ueber-")
        b("   haupt eine Rolle spielen.")
    finally:
        try:
            _os.unlink(probe)
        except OSError:
            pass



def _abschnitt_h(b, fe):
    """Die Uebertragungs-Matrix: was kostet eine Kopie in den
    Bildspeicher, in Abhaengigkeit von GROESSE und ZAHL DER AUFRUFE?

    WOZU DAS GEBRAUCHT WIRD, und zwar fuer eine ganz konkrete
    Entscheidung. _baender_flippen() in frontend.py fasst zwei Baender
    zusammen, wenn sie sich UEBERLAPPEN oder direkt aneinandergrenzen -
    sonst kopiert es zweimal. Bei zwei Kacheln in derselben Reihe, aber
    nicht nebeneinander, liegt dazwischen eine LUECKE: ein Streifen, der
    sich nicht geaendert hat. Zwei Kopien heissen zwei Aufrufe (und ohne
    Auslassen zwei Wartezeiten), eine Kopie heisst die Luecke mit
    uebertragen. Ab welcher Luecke lohnt sich was?

    Diese Frage ist mit einer Zahl beantwortet - aber nur mit einer von
    DIESEM Geraet. Auf dem Entwicklungsrechner ist der Bildspeicher
    normaler RAM, und genau dieser Unterschied hat in Build 209 schon
    einmal zu einer falschen Entscheidung gefuehrt (siehe Abschnitt F).
    Deshalb rechnet dieser Abschnitt die Schwelle nicht aus, er MISST
    ihre drei Bestandteile:

      1. den Preis JE BYTE, ueber die Groesse hinweg - denn wenn er
         konstant ist, ist die Luecke einfach Bytes;
      2. den Aufschlag JE AUFRUF - dieselbe Menge in einem Stueck gegen
         dieselbe Menge in N Stuecken. Das ist der Teil, der eine
         Zusammenfassung ueberhaupt lohnend macht;
      3. die WARTEZEIT auf den Bildwechsel, allein gemessen.

    Und daraus die Schwelle, in Bildzeilen, zweimal: mit Warten (Schalter
    aus) und ohne (Schalter an). Zwei Zahlen, weil es zwei verschiedene
    Antworten sind und nicht eine mit Sternchen.

    WAS HIER IN DEN BILDSPEICHER GESCHRIEBEN WIRD: ausschliesslich der
    INHALT DES EIGENEN PUFFERS, an dieselbe Stelle - also genau das, was
    ein flip() auch schreiben wuerde. Kein Testmuster. Damit kann dieser
    Abschnitt das Bild nicht beschaedigen, egal wo er abbricht; am Ende
    steht trotzdem ein voller flip(), damit der Bildwaechter seinen
    Sollwert wieder hat. NUR RAM->RAM und RAM->Bildspeicher: aus dem
    Bildspeicher LESEN kostet laut Abschnitt F ein Vielfaches, und das
    hier soll den Schreibweg vermessen, nicht ihn mit dem Lesepreis
    verruehren."""
    b("")
    b("-" * 62)
    b(" H  Uebertragungs-Matrix (Build 214)")
    b("-" * 62)
    fb = getattr(fe, "fb", None)
    if fb is None or not hasattr(fb, "mm") or not hasattr(fb, "buf"):
        b("   -- kein Bildspeicher, uebersprungen")
        return
    stride = int(getattr(fb, "stride", 0) or 0)
    groesse = min(int(getattr(fb, "size", 0) or 0), len(fb.buf))
    if stride <= 0 or groesse <= 0:
        b("   -- Bildspeicher ohne Masse, uebersprungen")
        return
    mvm = memoryview(fb.mm)
    mvb = memoryview(fb.buf)
    ram = bytearray(groesse)
    mvr = memoryview(ram)
    b("   Bild       : %dx%d, %d Byte je Zeile, %.1f MB gesamt"
      % (getattr(fb, "width", 0), getattr(fb, "height", 0), stride,
         groesse / 1048576.0))

    # ------------------------------------------------------------------
    # 1. Der Preis je Byte ueber die Groesse hinweg.
    # ------------------------------------------------------------------
    b("")
    b("   1) je Groesse - Preis je MB sagt, ob es linear ist")
    b("   %-14s %10s %10s %10s %10s"
      % ("Menge", "RAM ms", "je MB", "Bild ms", "je MB"))
    stufen = [1024, 4096, 16384, 65536, 262144, 1048576, 4194304, groesse]
    gesehen = set()
    je_mb_bild = {}
    for n in stufen:
        n = min(n, groesse)
        if n in gesehen or n <= 0:
            continue
        gesehen.add(n)

        def r2r(_n=n):
            mvr[0:_n] = mvb[0:_n]

        def r2f(_n=n):
            mvm[0:_n] = mvb[0:_n]

        wdh = WDH_BILLIG if n <= 262144 else WDH_TEUER
        ms_r, _best_r = messen(r2r, wdh)
        ms_f, _best_f = messen(r2f, wdh)
        mb = n / 1048576.0
        je_mb_bild[n] = (ms_f / mb) if mb > 0 else 0.0
        b("   %-14s %10.3f %10.2f %10.3f %10.2f"
          % (_menge(n), ms_r, (ms_r / mb) if mb else 0.0,
             ms_f, je_mb_bild[n]))

    # ------------------------------------------------------------------
    # 2. Der Aufschlag je Aufruf: dieselbe Menge, in N Stuecken.
    # ------------------------------------------------------------------
    b("")
    b("   2) je Aufruf - DIESELBE Menge, in N Stuecken kopiert")
    gesamt = min(1048576, groesse)
    b("   %-14s %10s %10s" % ("Stuecke", "Bild ms", "Aufschlag"))
    ms_eins = None
    aufschlag = 0.0
    ms_teile = {}
    for teile in (1, 2, 4, 8, 16, 32, 64):
        stueck = gesamt // teile
        if stueck < 64:
            continue
        starts = [i * stueck for i in range(teile)]

        def stueckweise(_s=starts, _l=stueck):
            for _o in _s:
                mvm[_o:_o + _l] = mvb[_o:_o + _l]

        ms, _best = messen(stueckweise, WDH_BILLIG)
        ms_teile[teile] = ms
        if ms_eins is None:
            ms_eins = ms
            b("   %-14s %10.3f %10s" % ("1", ms, "-"))
            continue
        # Der Aufschlag JE ZUSAETZLICHEM Aufruf - nicht der Unterschied
        # zum vorigen Zeile, sondern immer gegen das eine Stueck. Sonst
        # steht in der Spalte das Rauschen zwischen zwei Nachbarn.
        auf = (ms - ms_eins) / float(teile - 1)
        b("   %-14s %10.3f %10.3f ms" % (str(teile), ms, auf))
        # ACHT IST DIE ZAHL, MIT DER WEITERGERECHNET WIRD, und das ist
        # eine Wahl mit Grund: bei zwei Stuecken verschwindet der eine
        # zusaetzliche Aufruf im Rauschen, bei 64 misst man vor allem die
        # Python-Schleife um die Kopie herum. Acht liegt dazwischen und
        # entspricht der Groessenordnung, die im Betrieb vorkommt (die
        # Kachelansicht kopiert zwei bis drei Baender). Faellt die
        # Acht-Stufe aus, weil das Bild zu klein ist, gilt der letzte
        # gemessene Wert - besser als gar keiner, und die Tabelle
        # darueber zeigt, welcher es war.
        if teile == 8 or aufschlag <= 0.0:
            aufschlag = max(0.0, auf)

    # ------------------------------------------------------------------
    # 3. Die Wartezeit auf den Bildwechsel, allein.
    # ------------------------------------------------------------------
    b("")
    ms_vsync = 0.0
    if hasattr(fb, "_wait_vsync"):
        ms_vsync, best_v = messen(fb._wait_vsync, WDH_BILLIG)
        if getattr(fb, "_vsync_supported", None) is False:
            b("   3) dieses Geraet kennt kein Vsync-Warten (0 ms)")
            ms_vsync = 0.0
        else:
            b.posten("3) Warten auf den Bildwechsel", ms_vsync, best_v)
        # Der Zaehler aus Build 214 darf von dieser Messung nichts
        # behalten - sonst stuende sie in der naechsten RUCKLER-Zeile.
        if hasattr(fb, "vsync_ms_und_zuruecksetzen"):
            fb.vsync_ms_und_zuruecksetzen()
    else:
        b("   3) kein _wait_vsync vorhanden, uebersprungen")

    # ------------------------------------------------------------------
    # 4. Die Schwelle, in Bildzeilen.
    # ------------------------------------------------------------------
    b("")
    b("   4) daraus die Luecken-Schwelle fuer _baender_flippen()")
    # Der Preis einer Zeile: aus der Stufe, die einem echten Band am
    # naechsten kommt (256 kB), nicht aus dem Vollbild - dort ist der
    # Preis je Byte gemessen guenstiger, und mit einer zu guenstigen
    # Zahl faellt die Schwelle zu gross aus.
    bezug = 262144 if 262144 in je_mb_bild else max(je_mb_bild or {0: 0.0})
    je_mb = je_mb_bild.get(bezug, 0.0)
    ms_zeile = je_mb * stride / 1048576.0
    b("   %-38s %9.4f ms" % ("eine Bildzeile (%s-Stufe)" % _menge(bezug),
                             ms_zeile))
    # KEIN URTEIL AUS RAUSCHEN, und diese Schranke steht hier aus einem
    # Grund: auf dem Entwicklungsrechner ist mm ein bytearray im
    # normalen RAM, eine Kopie von 128 kB kostet dort Mikrosekunden, und
    # der "Aufschlag je Aufruf" faellt dann mal positiv, mal NEGATIV aus
    # (gemessen: 4 Stuecke schneller als 1). Aus solchen Zahlen eine
    # Schwelle zu rechnen ergibt eine Zahl, die aussieht wie ein Befund -
    # genau der Fehler, den Abschnitt E schon einmal gemacht hat und
    # seither ausdruecklich verweigert.
    #
    # Verlangt wird deshalb: der Aufschlag ist positiv UND acht Stuecke
    # sind messbar teurer als eines (mindestens ein Zehntel). Trifft das
    # nicht zu, steht hier NICHT MESSBAR und sonst nichts.
    ms_acht = ms_teile.get(8, ms_teile.get(4, 0.0))
    belastbar = (ms_zeile > 0 and aufschlag > 0 and ms_eins
                 and ms_acht >= ms_eins * 1.10)
    if ms_zeile <= 0:
        b("   -- ohne Preis je Zeile keine Schwelle")
    elif not belastbar:
        b("   ERGEBNIS   : NICHT MESSBAR - der Aufschlag je Aufruf liegt")
        b("                im Rauschen (1 Stueck %.3f ms, 8 Stuecke"
          % (ms_eins or 0.0))
        b("                %.3f ms). Das ist keine Schwelle, sondern eine"
          % ms_acht)
        b("                Kopie, die zu billig ist, um sie zu zaehlen -")
        b("                auf dem Geraet ist sie es nicht. Dort messen.")
    else:
        mit = (aufschlag + ms_vsync) / ms_zeile
        ohne = aufschlag / ms_zeile
        b("   %-38s %9.0f Zeilen" % ("Schwelle MIT Warten (Schalter aus)",
                                     mit))
        b("   %-38s %9.0f Zeilen" % ("Schwelle OHNE Warten (Schalter an)",
                                     ohne))
        if ms_vsync <= 0:
            b("   (beide gleich, weil dieses Geraet kein Vsync-Warten")
            b("    kennt - dort ist der Schalter ohnehin ohne Wirkung.)")
        b("")
        b("   Zu lesen als: liegen zwei Baender weniger als so viele")
        b("   Zeilen auseinander, ist EINE Kopie ueber die Luecke hinweg")
        b("   billiger als zwei Kopien. Mehr nicht - ob es auch besser")
        b("   AUSSIEHT, steht hier nicht, und die Entscheidung darueber")
        b("   gehoert nicht in einen Bench.")

    # ------------------------------------------------------------------
    # Und einmal ueber den echten Weg, damit die Zahlen oben nicht in
    # einer eigenen Welt leben: flip_rows() macht mehr als die Kopie
    # (Bildwaechter, Rueckleser, Buchfuehrung).
    # ------------------------------------------------------------------
    hoehe = int(getattr(fb, "height", 0) or 0)
    if hoehe >= 8 and hasattr(fb, "flip_rows"):
        band = max(1, hoehe // 8)
        b("")
        b("   5) derselbe Umfang ueber flip_rows(), mit allem Drumherum")
        for tag, skip in (("mit Warten", False), ("ohne Warten", True)):
            ms, best = messen(
                lambda _b=band, _s=skip: fb.flip_rows(0, _b, skip_vsync=_s),
                WDH_BILLIG)
            b.posten("%d Zeilen, %s" % (band, tag), ms, best)
        if hasattr(fb, "vsync_ms_und_zuruecksetzen"):
            fb.vsync_ms_und_zuruecksetzen()
    # Sollwert des Bildwaechters wieder herstellen: oben wurde in mm
    # geschrieben, ohne dass er es erfahren hat.
    try:
        fb.flip()
        if hasattr(fb, "vsync_ms_und_zuruecksetzen"):
            fb.vsync_ms_und_zuruecksetzen()
    except Exception:                                    # noqa: BLE001
        pass


def _menge(n):
    """1024 -> "1 kB", 1048576 -> "1,0 MB" - damit die Spalte lesbar
    bleibt und nicht siebenstellig wird."""
    if n >= 1048576:
        return "%.1f MB" % (n / 1048576.0)
    if n >= 1024:
        return "%d kB" % (n // 1024)
    return "%d B" % n


def _abschnitt_i(b, fe, A):
    """Kurze Zeilen gegen lange: was kostet der Rechteck-Flip wirklich?

    DIE FRAGE, DIE DIESER ABSCHNITT ENTSCHEIDET, und sie ist die einzige
    offene aus Build 215. Ein Rechteck-Flip kopiert weniger Bytes, aber
    in kuerzeren Stuecken: eine Rasterkachel ist 270 Punkte breit, das
    sind 1080 Byte je Zeile, ein Band hat 7680. Abschnitt H hat gezeigt,
    dass kleine Kopien je Byte dramatisch teurer sind (auf dem DE10-Nano
    59,79 ms/MB bei 1 kB gegen 1,68 bei 1 MB, Faktor 37). Damit ist die
    Frage nicht mehr, ob weniger Bytes schneller sind - sondern ob der
    Aufschlag je STUECK aus dem Weg ist.

    Er ist es nur, wenn die Schleife in C laeuft. Genau das messen die
    zwei Teile hier:

      1. DERSELBE BYTE-UMFANG, einmal in langen und einmal in kurzen
         Zeilen - und zwar je dreimal: naiv in Python, ueber memoryview,
         und ueber rechtecke_kopieren() in C. Das Verhaeltnis "kurz zu
         lang" IST die Antwort. Steht es in C bei etwa eins, ist der
         Rechteck-Flip so schnell wie er aussieht; steht es bei fuenf,
         ist er ein Verlust, und dann gehoert die Schalterdatei
         rechteck_flip_aus auf die Karte.

      2. DIE ECHTEN FORMEN eines Scrollschritts, damit nicht nur ein
         Verhaeltnis dasteht, sondern die Millisekunden, die der Nutzer
         erlebt: das Band aus Build 133 (888 Zeilen voll) gegen die
         Rechtecke aus Build 215 (zwei Kacheln, Namenszeile, Fusszeile).

    Geschrieben wird - wie in Abschnitt H - ausschliesslich der Inhalt
    des EIGENEN Puffers an dieselbe Stelle, also genau das, was ein
    Flip auch schreibt. Der Abschnitt kann das Bild deshalb nicht
    beschaedigen; am Ende steht trotzdem ein voller flip(), damit der
    Bildwaechter seinen Sollwert wiederhat."""
    b("")
    b("-" * 62)
    b(" I  Kurze Zeilen gegen lange: der Rechteck-Flip (Build 215)")
    b("-" * 62)
    fb = getattr(fe, "fb", None)
    if fb is None or not hasattr(fb, "mm") or not hasattr(fb, "buf"):
        b("   -- kein Bildspeicher, uebersprungen")
        return
    stride = int(getattr(fb, "stride", 0) or 0)
    breite = int(getattr(fb, "width", 0) or 0)
    hoehe = int(getattr(fb, "height", 0) or 0)
    if stride <= 0 or breite <= 0 or hoehe <= 0:
        b("   -- Bildspeicher ohne Masse, uebersprungen")
        return
    kop = getattr(A, "rechtecke_kopieren", None) if A is not None else None
    hat_c = bool(kop) and getattr(A, "_LIB", None) is not None
    b("   Bild       : %dx%d, %d Byte je Zeile" % (breite, hoehe, stride))
    b("   C-Kopierer : %s" % ("rechtecke_kopieren aus libdragend"
                              if hat_c else "NICHT da - nur Python"))
    mvm = memoryview(fb.mm)
    mvb = memoryview(fb.buf)

    def python_naiv(rechtecke):
        for (x, y, w, h) in rechtecke:
            n = w * 4
            off = y * stride + x * 4
            for _ in range(h):
                fb.mm[off:off + n] = fb.buf[off:off + n]
                off += stride

    def python_mv(rechtecke):
        for (x, y, w, h) in rechtecke:
            n = w * 4
            off = y * stride + x * 4
            for _ in range(h):
                mvm[off:off + n] = mvb[off:off + n]
                off += stride

    def ueber_c(rechtecke):
        kop(fb.buf, fb.mm, stride, hoehe, fb.size, rechtecke)

    def bytes_von(rechtecke):
        return sum(w * 4 * h for (_x, _y, w, h) in rechtecke)

    # ------------------------------------------------------------------
    # 1. Derselbe Umfang, lange gegen kurze Zeilen.
    # ------------------------------------------------------------------
    # Ziel: rund ein MB, und zwar GENAU gleich viel in beiden Faellen -
    # sonst vergleicht man zwei Sachen auf einmal. Die kurze Fassung ist
    # ein Siebtel breit und bekommt dafuer siebenmal so viele Zeilen,
    # verteilt auf sieben Rechtecke nebeneinander.
    # EIN Siebtel breit, dafuer siebenmal so viele Zeilen - derselbe
    # Byte-Umfang, nur anders geschnitten. Die Zeilenzahl der langen
    # Fassung wird so gewaehlt, dass die kurze noch ins Bild passt
    # (hoehe // 7), und zusaetzlich auf rund ein MB begrenzt.
    #
    # WARUM NUR EIN Rechteck und nicht sieben nebeneinander: sieben
    # Rechtecke waeren siebenmal der Umfang, und dann verglichen wir
    # zwei Dinge auf einmal. Was hier gemessen werden soll, ist allein
    # die ZEILENLAENGE.
    teiler = 7
    schmal = max(1, breite // teiler)
    zeilen_lang = max(1, min(hoehe // teiler, 1048576 // stride))
    zeilen_kurz = min(hoehe, zeilen_lang * teiler)
    lang = [(0, 0, breite, zeilen_lang)]
    kurz = [(0, 0, schmal, zeilen_kurz)]
    b("")
    b("   1) einmal %d Byte in %d langen Zeilen a %d Byte,"
      % (bytes_von(lang), zeilen_lang, breite * 4))
    b("      einmal %d Byte in %d kurzen Zeilen a %d Byte"
      % (bytes_von(kurz), zeilen_kurz, schmal * 4))
    if bytes_von(lang) > 0:
        _abw = 100.0 * abs(bytes_von(kurz) - bytes_von(lang)) / bytes_von(lang)
        if _abw > 5.0:
            b("      (Umfang weicht um %.0f %% ab - das Verhaeltnis unten"
              % _abw)
            b("       ist entsprechend zu lesen)")
    b("   %-20s %10s %10s %10s" % ("", "lang ms", "kurz ms", "kurz/lang"))
    ergebnis = {}
    wege = [("Python naiv", python_naiv), ("Python memoryview", python_mv)]
    if hat_c:
        wege.append(("C rechtecke_kopieren", ueber_c))
    for name, fn in wege:
        ms_l, _bl = messen(lambda _f=fn: _f(lang), WDH_TEUER)
        ms_k, _bk = messen(lambda _f=fn: _f(kurz), WDH_TEUER)
        ergebnis[name] = (ms_l, ms_k)
        b("   %-20s %10.2f %10.2f %10s"
          % (name, ms_l, ms_k,
             ("%.1fx" % (ms_k / ms_l)) if ms_l > 0 else "-"))

    # ------------------------------------------------------------------
    # 2. Die echten Formen eines Scrollschritts.
    # ------------------------------------------------------------------
    # Die Masse sind die gemessenen aus Build 215, auf diese Bildhoehe
    # umgerechnet: eine Kachel ist 270x361 auf 1080p (plus 3*Skala Rand
    # fuer die Markierung), die Namenszeile 11 und die Fusszeile 8
    # Textzeilen hoch.
    f = hoehe / 1080.0
    kb = max(1, min(breite // 2, int(288 * (breite / 1920.0))))
    kh = max(1, min(hoehe, int(379 * f)))
    nz = max(1, int(33 * f))
    fz = max(1, int(24 * f))
    band = [(0, 0, breite, min(hoehe, max(1, int(888 * f))))]
    rechte = []
    for i in range(2):
        x = min(breite - kb, i * (kb + 8))
        rechte.append((max(0, x), 0, kb, kh))
    rechte.append((0, min(hoehe - nz, int(880 * f)), breite, nz))
    rechte.append((0, max(0, hoehe - fz), breite, fz))
    b("")
    b("   2) ein echter Scrollschritt, beide Wege")
    b("   %-24s %9s %9s %9s" % ("", "MB", "ms", "ms je MB"))
    for name, rechtecke, wie in (
            ("Band (Build 133)", band, python_mv),
            ("Rechtecke, Python", rechte, python_mv),
            ("Rechtecke, C", rechte, ueber_c if hat_c else None)):
        if wie is None:
            continue
        n = bytes_von(rechtecke)
        mb = n / 1048576.0
        ms, _best = messen(lambda _f=wie, _r=rechtecke: _f(_r), WDH_TEUER)
        b("   %-24s %9.2f %9.2f %9.2f"
          % (name, mb, ms, (ms / mb) if mb > 0 else 0.0))

    # ------------------------------------------------------------------
    # 3. Flaechen fuellen: Python gegen C (Build 219).
    # ------------------------------------------------------------------
    # DIE ANDERE HAELFTE DERSELBEN FRAGE. Teil 1 und 2 messen das
    # KOPIEREN (Puffer -> Bildspeicher), hier geht es um das FUELLEN
    # (eine Farbe in den Puffer) - fb.rect() und die Karte mit Schatten.
    # Abschnitt J weist die vier zusammen als "karten" aus, und das war
    # im Lauf vom 28.09. der groesste benannte Posten eines Schritts:
    # 47,0 ms in der Spieleliste bei 10 Aufrufen.
    #
    # WARUM DAS HIER STEHEN MUSS: auf dem Entwicklungsrechner ist C
    # EXAKT gleich schnell wie Python (0,53 gegen 0,51 ms auf 700x900) -
    # dort kostet eine Zuweisung je Bildzeile fast nichts. Ob es auf
    # diesem Geraet lohnt, haengt allein am Grundaufwand je Zeile, und
    # den kennt nur dieses Geraet.
    fueller = getattr(fb, "flaechen_fueller", None)
    b("")
    b("   3) Flaechen fuellen: Python gegen C (fb.rect)")
    if fueller is None:
        b("      -- kein C-Fueller eingehaengt (alte libdragend oder")
        b("         flaechen_c_aus), nichts zu vergleichen")
    else:
        _mz = getattr(fb, "FLAECHEN_C_MIN_ZEILEN", 0)
        _mp = getattr(fb, "FLAECHEN_C_MIN_PUNKTE", 0)
        b("      C wird ab %d Zeilen ODER ab %d Punkten benutzt -"
          % (_mz, _mp))
        b("      darunter ist der Sprung teurer als die gesparten")
        b("      Zuweisungen. ZWEI Schwellen, weil es zwei Gruende gibt:")
        b("      viele ZEILEN (der Aufwand je Zeile faellt weg) und viel")
        b("      FLAECHE (die Nutzlast wandert in memcpy). Ein 3x771-")
        b("      Balken hat nur 2314 Punkte und kostet Python trotzdem")
        b("      771 Zuweisungen - das ist der Fund aus Build 220.")
        b("   %-24s %9s %9s %9s %s" % ("Flaeche", "Python ms", "C ms",
                                       "Faktor", "genutzt"))
        for fw, fh in ((700, 900), (400, 300), (60, 40),
                       (3, 771), (9, 361), (697, 3), (128, 128)):
            fw = min(fw, breite)
            fh = min(fh, hoehe)
            if fw <= 0 or fh <= 0:
                continue
            _echt = fb.flaechen_fueller
            try:
                fb.flaechen_fueller = None
                ms_py, _bp = messen(
                    lambda _w=fw, _h=fh: fb.rect(0, 0, _w, _h, (7, 9, 11)),
                    WDH_TEUER)
                fb.flaechen_fueller = _echt
                ms_c, _bc = messen(
                    lambda _w=fw, _h=fh: fb.rect(0, 0, _w, _h, (7, 9, 11)),
                    WDH_TEUER)
            finally:
                fb.flaechen_fueller = _echt
            b("   %-24s %9.3f %9.3f %9s %s"
              % ("%dx%d" % (fw, fh), ms_py, ms_c,
                 ("%.1fx" % (ms_py / ms_c)) if ms_c > 0 else "-",
                 "ja" if (fh >= _mz or fw * fh >= _mp) else "nein"))
        # UND DER RAHMEN - vier Balken, von denen einzeln keiner die
        # Schwelle erreicht. Genau so zeichnet die Rasteransicht die
        # Markierung um die Kachel, und das ist der Posten, den Build
        # 220 angegangen ist.
        _rahmen = [(0, 0, min(288, breite), 9),
                   (0, 352, min(288, breite), 9),
                   (0, 0, 9, min(361, hoehe)),
                   (min(279, breite - 9), 0, 9, min(361, hoehe))]
        _rahmen = [r for r in _rahmen if r[2] > 0 and r[3] > 0]
        if _rahmen and hasattr(fb, "rect_viele"):
            _echt = fb.flaechen_fueller
            try:
                fb.flaechen_fueller = None
                ms_py, _bp = messen(
                    lambda: [fb.rect(*r, (7, 9, 11)) for r in _rahmen],
                    WDH_TEUER)
                fb.flaechen_fueller = _echt
                ms_c, _bc = messen(
                    lambda: fb.rect_viele(_rahmen, (7, 9, 11)), WDH_TEUER)
            finally:
                fb.flaechen_fueller = _echt
            b("   %-24s %9.3f %9.3f %9s %s"
              % ("Rahmen aus 4 Balken", ms_py, ms_c,
                 ("%.1fx" % (ms_py / ms_c)) if ms_c > 0 else "-", "ja"))
        b("      (Gefuellt wird in den PUFFER, nicht auf den Schirm -")
        b("       auf dem Bild landet davon nichts.)")

    # ------------------------------------------------------------------
    # 4. Das Urteil - und nur, wenn es eines gibt.
    # ------------------------------------------------------------------
    b("")
    if not hat_c:
        b("   ERGEBNIS   : KEINE AUSSAGE - ohne libdragend laeuft der")
        b("                Rechteck-Flip in Python, und dort entscheidet")
        b("                der Aufschlag je Stueck. Dieses Geraet kann die")
        b("                Frage also nicht beantworten.")
    else:
        ms_l, ms_k = ergebnis.get("C rechtecke_kopieren", (0.0, 0.0))
        if ms_l <= 0:
            b("   ERGEBNIS   : NICHT MESSBAR - die lange Fassung kam auf")
            b("                0 ms heraus. Das ist eine stehende oder zu")
            b("                grobe Uhr, kein Befund.")
        else:
            verh = ms_k / ms_l
            b("   ERGEBNIS   : kurze Zeilen kosten in C das %.1f-fache"
              % verh)
            # Die Schwelle: der Rechteck-Weg kopiert beim Schritt nach
            # oben/unten 1,19 gegen 6,50 MB, also ein Fuenftel. Bis zu
            # einem Aufschlag von fuenf bleibt er also vorn.
            if verh < 3.0:
                b("                -> der Rechteck-Flip lohnt klar, er")
                b("                   kopiert ein Fuenftel der Bytes.")
            elif verh < 5.0:
                b("                -> er lohnt noch, aber knapp. Die")
                b("                   Zahlen aus Teil 2 sind hier die")
                b("                   Entscheidung, nicht dieses")
                b("                   Verhaeltnis.")
            else:
                b("                -> ER LOHNT NICHT. Dann gehoert")
                b("                   /media/fat/frontend/rechteck_flip_aus")
                b("                   angelegt, und Build 215 war ein")
                b("                   Irrtum. Kein Update noetig.")
    try:
        fb.flip()
        if hasattr(fb, "vsync_ms_und_zuruecksetzen"):
            fb.vsync_ms_und_zuruecksetzen()
    except Exception:                                    # noqa: BLE001
        pass


def schritt_funktion(fe, seite):
    """EIN Scrollschritt, genau wie ihn die Bedienung ausloest.

    HERAUSGELOEST (Build 231), weil fe/show.py dieselbe Messung
    braucht. Zwei Fassungen desselben Schritts waeren zwei Gelegenheiten
    auseinanderzulaufen - und genau daran ist Abschnitt J in Build 218
    schon einmal gescheitert (gemessen wurde der volle Neuaufbau statt
    des leichten Pfads, 132,87 ms statt des echten Schritts).

    Die Reihenfolge ist die aus run(): erst den leichten Pfad
    versuchen, und nur wenn der ablehnt, den vollen Aufbau. Fuer Raster
    und Galerie lehnt er immer ab (er kennt nur Zeilen)."""
    if seite == 0:
        def _schritt(i):
            alt = fe.cat_i
            fe.cat_i = i % max(1, len(fe.cats))
            if not fe._draw_navigate_cats(alt):
                fe.draw()
    else:
        def _schritt(i):
            # Dieselbe Quelle wie in Abschnitt B - eine zweite waere
            # eine zweite Gelegenheit, auseinanderzulaufen.
            try:
                n = len(fe._display_items())
            except Exception:                            # noqa: BLE001
                n = 0
            alt = fe.item_i
            fe.item_i = i % max(1, n)
            if not fe._draw_navigate_items(alt):
                fe.draw()
    return _schritt


def fenster_spanne(fe, seite):
    """Wie weit darf der Zeiger pendeln, ohne das Fenster zu verlassen?

    IM SICHTBAREN FENSTER PENDELN, nicht durch die Liste laufen - die
    Korrektur aus Build 219. Sobald das Fenster weiterscrollen muss,
    lehnt der leichte Pfad ab und es laeuft ein VOLLER Aufbau; gemessen
    waere dann ein Mittelwert aus beidem, also keine von beiden Zahlen.

    Ein Rand von zwei Zeilen, weil der leichte Pfad verlangt, dass ALTE
    und NEUE Zeile im Fenster liegen."""
    if seite == 0:
        fenster = int(getattr(fe, "cats_visible", 0) or 0)
        gesamt = max(1, len(getattr(fe, "cats", ()) or ()))
    else:
        fenster = int(getattr(fe, "items_visible", 0) or 0)
        try:
            gesamt = max(1, len(fe._display_items()))
        except Exception:                                # noqa: BLE001
            gesamt = 1
    return max(2, min(fenster - 2, gesamt - 1))


def _abschnitt_j(b, fe, S, A, fm):
    """WORAUS besteht ein Scrollschritt? Auf DIESEM Geraet.

    DER ANLASS IST EINE LUECKE IN MEINER EIGENEN BUCHFUEHRUNG. Abschnitt
    B sagt seit Build 177, was ein Schritt KOSTET - auf dem DE10-Nano
    zuletzt 67 ms in der Kachelansicht und 164 ms in der Galerie. Was
    darin steckt, sagt er nicht. Und weil Build 215 die Kopie in den
    Bildspeicher auf ein Fuenftel gebracht hat (gemessen: 18,55 -> 3,46
    ms), ist die Kopie als Erklaerung erledigt: es bleiben rund 150 ms
    ohne Namen.

    Die haben mich zweimal zu einer falschen Vermutung verleitet, und
    beide Male stand die Zahl auf dem Entwicklungsrechner - wo dieselben
    Schritte 0,7 bis 1,7 ms brauchen, also das Sechzigfache schneller
    sind. Deshalb steht hier kein Urteil, sondern eine Aufteilung.

    GEMESSEN WIRD MIT HAKEN AN DEN VERDAECHTIGEN, nicht mit Zaehlern im
    Zeichenweg: der Bench ist ein Messgeraet und darf umhaengen, der
    Betrieb soll nichts davon merken. Drei Posten werden namentlich
    ausgewiesen, weil sie die drei verschiedenen SORTEN Arbeit sind:

      restore   Hintergrund freiraeumen - Kopie im RAM (Vorlage ->
                Puffer), zeilenweise.
      blit      ein fertiges Cover in den Puffer - Kopie im RAM, aber
                aus einem ANDERS gerasterten Quellpuffer, deshalb
                zeilenweise in Python.
      flip      Puffer -> Bildspeicher, seit Build 215 ueber Rechtecke
                und in C.

    Dazu Zahl der Aufrufe und Zahl der ZEILEN - die sind
    geraeteunabhaengig und damit das, was ein Vergleich zweier Geraete
    ueberhaupt erlaubt.

    Was NICHT ausgewiesen wird, steht als "Rest" da: Text, Rahmen,
    Karten mit Schatten, die Beschreibung, Hausarbeit. Ist der Rest der
    groesste Posten, ist das das Ergebnis dieses Abschnitts - dann ist
    die naechste Messung dort faellig und nicht bei den Kopien."""
    b("")
    b("-" * 62)
    b(" J  Woraus besteht ein Scrollschritt? (Build 216)")
    b("-" * 62)
    fbo = getattr(fe, "fb", None)
    if fbo is None:
        b("   -- kein Framebuffer, uebersprungen")
        return
    if not hasattr(fe, "ansicht_setzen") or not hasattr(S, "ANSICHTEN"):
        b("   -- Ansichten nicht ansprechbar, uebersprungen")
        return

    K = type(fe)
    echt_restore = K._restore_row_bg
    echt_blit = K.blit
    echt_rect = getattr(fbo, "flip_rechtecke", None)
    echt_rows = fbo.flip_rows
    echt_voll = fbo.flip
    echt_text = fbo.text
    echt_beschr = getattr(K, "_beschreibung_zeichnen", None)
    echt_cover = getattr(K, "_ansicht_cover", None)
    # NEU (Build 238): die Boxart-Karte der LISTENANSICHT. Bis hierher
    # hatte "cover" nur _ansicht_cover() am Haken - das ist der Weg von
    # Raster und Galerie. In der Liste kommt das Cover ueber
    # draw_art_panel(), und dessen Arbeit stand deshalb namenlos im
    # REST. Genau dort steht in der Listenansicht "karten 14,4 ms" und
    # "REST 9,8 ms", und genau dort haben wir drei Builds lang an der
    # Stelle vorbeigemessen, die im Alltag staendig laeuft.
    echt_panel = getattr(K, "draw_art_panel", None)
    # os.stat UND builtins.open - nicht io.open: der eingebaute open()
    # ist eine eigene Bindung, ein Haken an io.open ginge daran vorbei.
    # os.path.exists() und isfile() gehen ueber os.stat und sind damit
    # mitgezaehlt.
    _os = __import__("os")
    _bi = __import__("builtins")
    _sys = __import__("sys")
    _wer = {}
    _datei_echt = [(_os, "stat", _os.stat), (_bi, "open", _bi.open)]
    _KARTEN = [(fbo, n) for n in ("karte_mit_schatten",
                                  "rect_rounded_schatten",
                                  "rect_rounded", "rect")
               if hasattr(fbo, n)]
    _karten_echt = [(o, n, getattr(o, n)) for (o, n) in _KARTEN]
    konto = {}

    # DIE POSTEN, und jeder ist eine andere SORTE Arbeit. Ohne diese
    # Aufteilung stand in Build 216 ein "Rest" von 27 bis 63 ms da - der
    # groesste Posten ueberall, und ohne Namen.
    _POSTEN = ("restore", "blit", "flip", "text", "karten", "beschr",
               "cover", "datei", "panel")

    def _null():
        konto.clear()
        for p in _POSTEN:
            konto[p + "_ms"] = 0.0
            konto[p + "_n"] = 0.0
        _wer.clear()
        for k in ("restore_zeilen", "blit_zeilen", "flip_bytes",
                  "text_zeichen", "text_in_beschr_ms", "in_beschr",
                  "in_karte", "karten_innen"):
            konto[k] = 0.0

    def h_restore(self, x, y, w, h):
        t0 = time.monotonic()
        r = echt_restore(self, x, y, w, h)
        konto["restore_ms"] += time.monotonic() - t0
        konto["restore_n"] += 1
        konto["restore_zeilen"] += max(0, h)
        return r

    def h_blit(self, x, y, w, h, pix):
        t0 = time.monotonic()
        r = echt_blit(self, x, y, w, h, pix)
        konto["blit_ms"] += time.monotonic() - t0
        konto["blit_n"] += 1
        konto["blit_zeilen"] += max(0, h)
        return r

    def h_rect(rechtecke, skip_vsync=False):
        rechtecke = list(rechtecke)
        t0 = time.monotonic()
        n = echt_rect(rechtecke, skip_vsync=skip_vsync)
        konto["flip_ms"] += time.monotonic() - t0
        konto["flip_n"] += 1
        konto["flip_bytes"] += n or 0
        return n

    def h_rows(y, h, skip_vsync=False):
        t0 = time.monotonic()
        r = echt_rows(y, h, skip_vsync)
        konto["flip_ms"] += time.monotonic() - t0
        konto["flip_n"] += 1
        konto["flip_bytes"] += max(0, h) * fbo.stride
        return r

    def h_voll(skip_vsync=False):
        t0 = time.monotonic()
        r = echt_voll(skip_vsync)
        konto["flip_ms"] += time.monotonic() - t0
        konto["flip_n"] += 1
        konto["flip_bytes"] += fbo.size
        return r

    # --- und die Posten, die bisher im "Rest" verschwunden sind -------
    #
    # TEXT. Gezaehlt werden auch die ZEICHEN: eine Zeile Beschreibung und
    # eine Kopfzeile sind beides "ein text()-Aufruf", kosten aber nicht
    # dasselbe.
    def h_text(x, y, txt, *a, **k):
        t0 = time.monotonic()
        r = echt_text(x, y, txt, *a, **k)
        dt = time.monotonic() - t0
        konto["text_ms"] += dt
        konto["text_n"] += 1
        try:
            konto["text_zeichen"] += len(txt)
        except TypeError:
            pass
        # Laeuft dieser Aufruf INNERHALB der Beschreibung, wird er dort
        # noch einmal mitgemessen - sonst stuende dieselbe Zeit zweimal
        # in der Tabelle und der Rest waere zu klein. Siehe h_beschr().
        if konto["in_beschr"]:
            konto["text_in_beschr_ms"] += dt
        return r

    # KARTEN UND RAHMEN: abgerundete Rechtecke, Schatten, Flaechen. Auf
    # dem Geraet sind das Python-Schleifen ueber Bildzeilen, genau wie
    # restore - nur ohne Vorlage.
    #
    # UND DIESE VIER RUFEN SICH GEGENSEITIG: karte_mit_schatten() ruft
    # rect_rounded_schatten() und rect_rounded(), und die rufen rect().
    # Ohne Zaehler stand dieselbe Zeit deshalb bis zu dreimal in
    # "karten" - der Posten war zu gross und der REST um denselben
    # Betrag zu klein, also genau dort falsch, wo ich als naechstes
    # suche. Gezaehlt wird nur der AEUSSERSTE Aufruf; die inneren
    # stecken in seiner Zeit schon drin. Dieselbe Bauweise wie bei
    # h_beschr() und "text".
    def _h_karte(echt):
        def haken(*a, **k):
            if konto["in_karte"]:
                konto["karten_innen"] += 1
                return echt(*a, **k)
            t0 = time.monotonic()
            konto["in_karte"] += 1
            try:
                r = echt(*a, **k)
            finally:
                konto["in_karte"] -= 1
            konto["karten_ms"] += time.monotonic() - t0
            konto["karten_n"] += 1
            return r
        return haken

    # DAS COVER SUCHEN - und das ist der erste Verdaechtige fuer den
    # REST (Build 221). _ansicht_cover() fragt den Bild-Cache, baut
    # Cache-Schluessel, vergleicht Namen und fasst dabei die KARTE an.
    # Abschnitt G hat gemessen, was das dort kostet: ein os.stat 0,20 ms
    # warm, 21 Kacheln 4,24 ms. Im Bericht vom 29.09. steht REST mit 38
    # bis 79 ms je Schritt, also mehr als alle benannten Posten
    # zusammen - und wer nicht misst, raet.
    def h_cover(self, *a, **k):
        t0 = time.monotonic()
        try:
            return echt_cover(self, *a, **k)
        finally:
            konto["cover_ms"] += time.monotonic() - t0
            konto["cover_n"] += 1

    # UND DIE KARTE SELBST, eine Ebene tiefer: os.stat und open im
    # Zeichenweg. Gezaehlt wird beides zusammen, denn beide gehen auf
    # dieselbe SD-Karte. Liegt "datei" hoch, ist der naechste Schritt
    # ein Zwischenspeicher und keine schnellere Schleife.
    def _h_datei(echt):
        def haken(*a, **k):
            t0 = time.monotonic()
            try:
                return echt(*a, **k)
            finally:
                konto["datei_ms"] += time.monotonic() - t0
                konto["datei_n"] += 1
                # WER FRAGT? (Build 222) Ohne diese Zeile stand im
                # Bericht nur "20 Zugriffe" und niemand wusste, welche.
                # Genommen wird der Rahmen des Aufrufers, NICHT
                # traceback.extract_stack(): das liest die
                # Quelltextzeilen ueber linecache und ruft dabei selbst
                # os.stat - also eine Endlosschleife in genau diesem
                # Haken. Ein f_code-Zugriff kostet nichts.
                try:
                    _f = _sys._getframe(1)
                    _w = _f.f_code.co_name
                    if _f.f_back is not None:
                        _w = _f.f_back.f_code.co_name + " > " + _w
                    # AUCH DIE ZEIT, nicht nur die Zahl (Build 241).
                    #
                    # Hier stand nur ein Zaehler, und dadurch war die
                    # Zeile nicht zu beurteilen. Im Bericht vom 04.10.
                    # stand "0.6/Schritt _basen_merkmal > getmtime", und
                    # das sah nach einem Posten aus - bis man
                    # nachrechnet: 0,6 Zugriffe mal 0,18 ms (Abschnitt
                    # G, os.stat warm) sind 0,1 ms je Schritt. Eine
                    # Zahl, die man erst mit einem anderen Abschnitt
                    # multiplizieren muss, um sie zu lesen, ist eine
                    # Einladung zur falschen Vermutung. Jetzt steht die
                    # Zeit daneben.
                    _e = _wer.get(_w)
                    if _e is None:
                        _wer[_w] = [1, time.monotonic() - t0]
                    else:
                        _e[0] += 1
                        _e[1] += time.monotonic() - t0
                except Exception:                        # noqa: BLE001
                    pass
        return haken

    # DIE BESCHREIBUNG rechnet Umbrueche (reine Zeichenkettenarbeit) und
    # zeichnet dann Zeilen. Ausgewiesen wird nur ihr EIGENER Anteil, die
    # Textzeit darin gehoert zu "text".
    # DIE BOXART-KARTE DER LISTE. Ausgewiesen wird nur ihr EIGENER
    # Anteil: Karten, Kopien und Text darin haben ihre eigenen Posten
    # und wuerden sonst doppelt zaehlen. Uebrig bleibt, was wirklich
    # nur hier passiert - vor allem das Beschaffen des Bildes.
    def h_panel(self, *a, **k):
        t0 = time.monotonic()
        _vor = (konto["karten_ms"] + konto["blit_ms"] + konto["text_ms"]
                + konto["restore_ms"])
        try:
            return echt_panel(self, *a, **k)
        finally:
            _innen = (konto["karten_ms"] + konto["blit_ms"]
                      + konto["text_ms"] + konto["restore_ms"]) - _vor
            konto["panel_ms"] += max(0.0, time.monotonic() - t0 - _innen)
            konto["panel_n"] += 1

    def h_beschr(self, *a, **k):
        t0 = time.monotonic()
        konto["in_beschr"] += 1
        try:
            r = echt_beschr(self, *a, **k)
        finally:
            konto["in_beschr"] -= 1
        konto["beschr_ms"] += time.monotonic() - t0
        konto["beschr_n"] += 1
        return r

    # ERST das Konto anlegen, DANN die Haken setzen. Andersherum lief
    # das Warmlaufen in einen KeyError, weil die Haken in ein leeres
    # Konto schreiben wollten - und weil der Abschnitt seine Ansichten
    # einzeln absichert, stand als Ergebnis "uebersprungen (KeyError)"
    # statt einer Tabelle. Genau die Sorte Fehler, die ein grosszuegiges
    # except verdeckt.
    _null()
    schritte = max(10, SCHRITTE // 2)
    b("   %d Schritte je Ansicht, alles warm, INNERHALB des sichtbaren"
      % schritte)
    b("   Fensters (sonst laeuft die Haelfte als voller Aufbau, siehe")
    b("   Quelltext). Zeiten je SCHRITT.")
    b("")
    K._restore_row_bg = h_restore
    K.blit = h_blit
    if echt_rect is not None:
        fbo.flip_rechtecke = h_rect
    fbo.flip_rows = h_rows
    fbo.flip = h_voll
    fbo.text = h_text
    for (_o, _n, _e) in _karten_echt:
        setattr(_o, _n, _h_karte(_e))
    if echt_beschr is not None:
        K._beschreibung_zeichnen = h_beschr
    if echt_cover is not None:
        K._ansicht_cover = h_cover
    if echt_panel is not None:
        K.draw_art_panel = h_panel
    for (_o, _n, _e) in _datei_echt:
        setattr(_o, _n, _h_datei(_e))
    # DIE GROESSTE KATEGORIE, genau wie Abschnitt B sie waehlt - und aus
    # demselben Grund.
    #
    # BEIM ERSTEN LAUF AUF DEM GERAET WAR DAS DER FEHLER: hier stand nur
    # "fe.page = 1", und der Zeiger blieb dort liegen, wo die
    # Hauptseiten-Schleife ihn hatte. Ergebnis im Bericht: die drei
    # "Liste"-Zeilen waren BUCHSTABENGLEICH (849 Zeilen, 0 blit, ein
    # Vollbild) - dreimal dieselbe Messung, weil die Ansicht nie
    # gewechselt hat. Sichtbar wurde es erst am Widerspruch zu Abschnitt
    # B: der sagt fuer die Galerie 157,7 ms, dieser hier 59,3.
    #
    # Genau derselbe Fehler steckte in Build 178 schon einmal in
    # Abschnitt B ("der bench landet immer im supergameboy"). Deshalb
    # jetzt dieselbe Loesung an derselben Funktion.
    kat_i, kat_n, kat_name = _groesste_kategorie(fe)
    if kat_i is not None:
        b("   gemessen in: %s (%d Eintraege)" % (kat_name, kat_n))
    try:
        for seite, name in ((0, "Haupt"), (1, "Liste")):
            fe.page = seite
            if seite == 1:
                if kat_i is None:
                    b("   %-20s -- keine Kategorie mit Eintraegen" % "Liste")
                    continue
                fe.cat_i = kat_i
                fe.nav_path = []
            for ansicht in S.ANSICHTEN:
                try:
                    if seite == 0:
                        fe.ansicht_haupt_setzen(ansicht)
                    else:
                        fe.ansicht_setzen(ansicht)
                except Exception:                        # noqa: BLE001
                    continue

                # DER SCHRITT, WIE IHN DIE BEDIENUNG MACHT - und das
                # ist in Build 218 der eigentliche Umbau an diesem
                # Abschnitt.
                #
                # Bisher stand hier nur fe.draw(). Das ist fuer Raster
                # und Galerie richtig: dort baut die Ansicht ihren
                # schnellen Weg INNERHALB von draw_page_items(). Fuer die
                # LISTE ist es falsch - deren leichter Pfad heisst
                # _draw_navigate_items() und wird von draw() nie
                # gerufen. Gemessen wurde also der volle Neuaufbau, und
                # im Bericht vom 28.09. stand fuer die Liste 132,87 ms,
                # waehrend der echte Schritt ein voellig anderer ist.
                #
                # Jetzt genau die Reihenfolge aus run(): erst den
                # leichten Pfad versuchen, und nur wenn der ablehnt, den
                # vollen Aufbau. Fuer Raster und Galerie lehnt er immer
                # ab (er kennt nur Zeilen), dort aendert sich also
                # nichts.
                # Build 231: der Schritt steht jetzt in
                # schritt_funktion() - fe/show.py misst denselben.
                _schritt = schritt_funktion(fe, seite)

                # WARMLAUFEN, und zwar zweimal durch: beim ersten Mal
                # werden die Miniaturen gerechnet, erst beim zweiten
                # liegen alle im RAM. Ohne das misst dieser Abschnitt
                # das Rechnen von Covern und nennt es "Rest".
                try:
                    for _r in range(2):
                        for i in range(schritte):
                            _schritt(i)
                except Exception as e:                   # noqa: BLE001
                    b("   %-20s -- uebersprungen (%s)"
                      % (name + " " + ansicht, type(e).__name__))
                    continue

                # IM SICHTBAREN FENSTER PENDELN, nicht durch die Liste
                # laufen - und das ist die Korrektur aus Build 219.
                #
                # WAS VORHER HERAUSKAM: der Zeiger lief mit i % n durch
                # die Liste, und sobald das Fenster weiterscrollen muss,
                # lehnt der leichte Pfad ab (scroll hat sich geaendert)
                # und es laeuft ein VOLLER Aufbau. Bei 17 sichtbaren
                # Zeilen waren das rund 13 von 30 Schritten. Im Bericht
                # vom 28.09. stand deshalb "Liste liste 126,53 ms" mit
                # einem Flip von 5,5 MB - ein Mittelwert aus leichten
                # Schritten (3,12 MB) und vollen Aufbauten, also keine
                # von beiden Zahlen.
                #
                # Genau dieselbe Sorte Fehler wie in Build 178 ("der
                # bench landet immer im supergameboy") und in Build 216
                # (J waehlte die Kategorie nicht): der Zustand, in dem
                # gemessen wird, muss zur Frage passen.
                _fenster = fenster_spanne(fe, seite)
                _null()
                _haus0 = getattr(fe, "_perf_house", 0.0)
                t0 = time.monotonic()
                for i in range(schritte):
                    _schritt(i % _fenster)
                ges = (time.monotonic() - t0) * 1000.0 / schritte
                je = 1000.0 / schritte
                r = konto["restore_ms"] * je
                bl = konto["blit_ms"] * je
                fl = konto["flip_ms"] * je
                tx = konto["text_ms"] * je
                ka = konto["karten_ms"] * je
                # Die Textzeit INNERHALB der Beschreibung steht schon
                # unter "text" - sonst zaehlte sie doppelt und der Rest
                # waere zu klein.
                be = max(0.0, (konto["beschr_ms"]
                               - konto["text_in_beschr_ms"]) * je)
                ha = max(0.0, (getattr(fe, "_perf_house", 0.0) - _haus0) * je)
                co = konto["cover_ms"] * je
                # Die Dateizeit steckt zum groessten Teil IN "cover" -
                # sie wird deshalb nur ausgewiesen, nicht abgezogen.
                da = konto["datei_ms"] * je
                # Build 238: die Boxart-Karte der Liste. Ihr EIGENER
                # Anteil - Karten, Kopien und Text darin stehen schon in
                # den eigenen Posten (siehe h_panel).
                pa = konto["panel_ms"] * je
                rest = max(0.0,
                           ges - r - bl - fl - tx - ka - be - ha - co - pa)
                b("   %-18s  ges %8.2f ms" % (name + " " + ansicht, ges))
                b("     restore %6.2f   blit %6.2f   flip %6.2f"
                  % (r, bl, fl))
                b("     text    %6.2f   karten %5.2f   beschr %5.2f"
                  "   haus %5.2f" % (tx, ka, be, ha))
                # %.1f STATT %d (Build 241): hier stand "davon Karte
                # 3.35 in 0 Zugriffen" - 3,35 ms fuer null Zugriffe.
                # Das war kein Widerspruch im Frontend, sondern ein
                # Formatfehler: %d auf 0,7 schreibt 0.
                b("     cover   %6.2f   panel %5.2f"
                  "   (davon Karte %.2f in %.1f Zugriffen)"
                  % (co, pa, da, konto["datei_n"] / float(schritte)))
                for _w, _e in sorted(_wer.items(),
                                     key=lambda e: -e[1][1])[:3]:
                    b("        %5.1f/Schritt %6.2f ms  %s"
                      % (_e[0] / float(schritte),
                         _e[1] * 1000.0 / schritte, _w[-40:]))
                b("     REST    %6.2f   (%.0f %% des Schritts)"
                  % (rest, 100.0 * rest / max(0.01, ges)))
                b("     Aufrufe: restore %d/%dz  blit %d/%dz  flip %d/%.1fMB"
                  % (konto["restore_n"] / schritte,
                     konto["restore_zeilen"] / schritte,
                     konto["blit_n"] / schritte,
                     konto["blit_zeilen"] / schritte,
                     konto["flip_n"] / schritte,
                     konto["flip_bytes"] / schritte / 1048576.0))
                b("              text %d/%dZeichen  karten %d(+%d innen)"
                  "  beschr %d"
                  % (konto["text_n"] / schritte,
                     konto["text_zeichen"] / schritte,
                     konto["karten_n"] / schritte,
                     konto["karten_innen"] / schritte,
                     konto["beschr_n"] / schritte))
    finally:
        K._restore_row_bg = echt_restore
        K.blit = echt_blit
        if echt_rect is not None:
            fbo.flip_rechtecke = echt_rect
        fbo.flip_rows = echt_rows
        fbo.flip = echt_voll
        fbo.text = echt_text
        for (_o, _n, _e) in _karten_echt:
            setattr(_o, _n, _e)
        if echt_beschr is not None:
            K._beschreibung_zeichnen = echt_beschr
        if echt_cover is not None:
            K._ansicht_cover = echt_cover
        if echt_panel is not None:
            K.draw_art_panel = echt_panel
        for (_o, _n, _e) in _datei_echt:
            setattr(_o, _n, _e)
    b("")
    b("   Zu lesen als: der groesste Posten sagt, wo die naechste Arbeit")
    b("   liegt - und nur er. restore, blit und karten sind zeilenweise")
    b("   Kopien bzw. Schleifen; bei ihnen zaehlt die Zahl der ZEILEN,")
    b("   nicht die der Bytes (siehe Abschnitt I). Bleibt REST gross,")
    b("   fehlt weiterhin ein Posten - dann ist die naechste Aufgabe,")
    b("   ihn zu finden, und nicht, irgendwas zu beschleunigen.")

def _abschnitt_k(b, fe, S, A):
    """Welche Fuellaufrufe macht ein Scrollschritt - und wieviele?
    (Build 241)

    WARUM DIESER ABSCHNITT NOETIG WURDE, und das ist eine Rechnung, die
    nicht aufging. Im Bericht vom 04.10. steht fuer die Listenansicht
    "karten 13,81 ms". Nach dem Kostenmodell aus Abschnitt H und I
    muessten es rund drei sein:

        5 Aufrufe x 0,40 ms Aufruf-Overhead      = 2,0 ms
        174.000 Punkte x 0,0000057 ms            = 1,0 ms

    Zwischen 3 und 13,81 liegen zehn Millisekunden, und die sind in
    JEDEM Schritt da. Woran das liegt, liess sich auf dem
    Entwicklungsrechner nicht feststellen - dort kostet derselbe
    Schritt 1,36 ms statt 39, und die Unterschiede verschwinden im
    Rauschen. Also wird es hier gemessen, auf dem Geraet.

    DAS COVER WIRD UNTERGESCHOBEN. Ohne Cover ist diese Messung blind:
    der Rahmen um das Cover, der Schlagschatten darunter und die
    Aussparung in der Karte entstehen nur, wenn get_scaled() etwas
    liefert. Genau diese Teile sind der Gegenstand. Es wird ein
    ERZEUGTES Bild benutzt, nicht eines von der Karte - gemessen werden
    soll der Zeichenweg, nicht das Dekodieren (das steht in Abschnitt
    C und D).

    DIE ZAHL DER AUFRUFE IST DIE UEBERTRAGBARE GROESSE. Abschnitt I.3
    misst eine 60x40-Flaeche mit 0,489 ms in C und eine 697x3 mit
    0,318 ms - beides winzige Flaechen. Das ist nicht die Flaeche, das
    ist der Aufruf."""
    b("")
    b("-" * 62)
    b(" K  Welche Fuellaufrufe macht ein Scrollschritt? (Build 241)")
    b("-" * 62)
    fbo = getattr(fe, "fb", None)
    if fbo is None:
        b("   kein Bildspeicher - uebersprungen")
        return
    kat_i, kat_n, kat_name = _groesste_kategorie(fe)
    if kat_i is None:
        b("   keine Kategorie mit Eintraegen - uebersprungen")
        return
    b("   Das Cover ist ERZEUGT, nicht gelesen: hier geht es um den")
    b("   Zeichenweg, nicht um das Dekodieren (Abschnitt C und D).")
    b("   Gezaehlt wird nur der AEUSSERSTE Aufruf - karte_mit_schatten()")
    b("   ruft rect_rounded(), und die ruft rect().")
    b("")

    # Das Cover unterschieben. Die Groesse wechselt von Schritt zu
    # Schritt, wie bei echten Boxarts - sonst waere die Aussparung in
    # der Karte immer dieselbe, und das ist der Fall, den es nicht gibt.
    echt_scaled = getattr(A, "get_scaled", None)
    if echt_scaled is None:
        b("   kein Bild-Zwischenspeicher - uebersprungen")
        return
    zaehler = [0]
    puffer = {}

    def _cover(quelle, breite, hoehe, **k):
        zaehler[0] += 1
        aw = max(8, int(breite) - (zaehler[0] % 3) * 7)
        ah = max(8, int(hoehe) - (zaehler[0] % 4) * 5)
        pix = puffer.get((aw, ah))
        if pix is None:
            pix = bytes(bytearray([40, 90, 160, 0])) * aw * ah
            puffer[(aw, ah)] = pix
        return (aw, ah, pix)

    _NAMEN = ("karte_mit_schatten", "rect_rounded_schatten",
              "rect_rounded", "rect", "rect_viele")
    echte = [(n, getattr(fbo, n)) for n in _NAMEN if hasattr(fbo, n)]
    konto = {}
    tiefe = [0]

    def _haken(name, echt):
        def ersatz(*a, **k):
            if tiefe[0]:
                return echt(*a, **k)
            try:
                if name == "rect_viele":
                    masse = "%d Rechtecke" % len(list(a[0]))
                else:
                    masse = "%dx%d" % (int(a[2]), int(a[3]))
            except Exception:                            # noqa: BLE001
                masse = "?"
            t0 = time.monotonic()
            tiefe[0] += 1
            try:
                return echt(*a, **k)
            finally:
                tiefe[0] -= 1
                e = konto.setdefault((name, masse), [0, 0.0])
                e[0] += 1
                e[1] += time.monotonic() - t0
        return ersatz

    schritte = max(10, SCHRITTE // 3)
    A.get_scaled = _cover
    try:
        fe.page = 1
        fe.cat_i = kat_i
        fe.nav_path = []
        for ansicht in S.ANSICHTEN:
            try:
                fe.ansicht_setzen(ansicht)
            except Exception:                            # noqa: BLE001
                continue
            try:
                schritt = schritt_funktion(fe, 1)
                schritt(0)              # erst zeichnen (siehe Build 239)
                spanne = fenster_spanne(fe, 1)
                for i in range(schritte):       # warmlaufen
                    schritt(i % spanne)
            except Exception as e:                       # noqa: BLE001
                b("   %-8s uebersprungen (%s)" % (ansicht,
                                                  type(e).__name__))
                continue
            konto.clear()
            for n, _e in echte:
                setattr(fbo, n, _haken(n, getattr(fbo, n)))
            try:
                t0 = time.monotonic()
                for i in range(schritte):
                    schritt(i % spanne)
                ges = (time.monotonic() - t0) * 1000.0 / schritte
            finally:
                for n, _e in echte:
                    setattr(fbo, n, _e)
            aufrufe = sum(e[0] for e in konto.values()) / float(schritte)
            summe = sum(e[1] for e in konto.values()) * 1000.0 / schritte
            b("   Liste %-8s Schritt %7.2f ms, davon Fuellen %6.2f ms"
              % (ansicht, ges, summe))
            b("      %.1f Aufrufe je Schritt, im Schnitt %.3f ms je Aufruf"
              % (aufrufe, summe / max(0.001, aufrufe)))
            for (name, masse), (n, sek) in sorted(
                    konto.items(), key=lambda e: -e[1][1])[:6]:
                b("        %-22s %-13s %5.2f x  %7.3f ms"
                  % (name, masse, n / float(schritte),
                     sek * 1000.0 / schritte))
            b("")
    finally:
        A.get_scaled = echt_scaled
        for n, _e in echte:
            setattr(fbo, n, _e)

    b("   Zu lesen als: 'ms je Aufruf' ist die Zahl, auf die es")
    b("   ankommt. Liegt sie deutlich ueber dem, was die Flaechen")
    b("   erklaeren (Abschnitt I.3: eine 60x40-Flaeche kostet in C")
    b("   0,489 ms, eine 697x3 0,318 ms - beides fast reiner")
    b("   Aufruf-Overhead), dann ist ZUSAMMENFASSEN die Abhilfe und")
    b("   nicht eine kleinere Flaeche. Steht sie darunter, steckt die")
    b("   Zeit in der Flaeche, und dann zaehlt die Aussparung.")


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
            _abschnitt_b(b, fe, S, spiele, A)
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
    try:
        _abschnitt_e(b, fe)
    except Exception as e:                               # noqa: BLE001
        b("   ABSCHNITT E ABGEBROCHEN: %s: %s" % (type(e).__name__, e))
    try:
        _abschnitt_f(b, fe)
    except Exception as e:                               # noqa: BLE001
        b("   ABSCHNITT F ABGEBROCHEN: %s: %s" % (type(e).__name__, e))
    try:
        _abschnitt_g(b, fe, A)
    except Exception as e:                               # noqa: BLE001
        b("   ABSCHNITT G ABGEBROCHEN: %s: %s" % (type(e).__name__, e))
    try:
        _abschnitt_h(b, fe)
    except Exception as e:                               # noqa: BLE001
        b("   ABSCHNITT H ABGEBROCHEN: %s: %s" % (type(e).__name__, e))
    try:
        _abschnitt_i(b, fe, A)
    except Exception as e:                               # noqa: BLE001
        b("   ABSCHNITT I ABGEBROCHEN: %s: %s" % (type(e).__name__, e))
    try:
        hd2 = getattr(fe, "fb", None) is not None and fe.fb.height >= 720
        with _Messbedingungen(A, fm, fe, hd2):
            _abschnitt_j(b, fe, S, A, fm)
    except Exception as e:                               # noqa: BLE001
        b("   ABSCHNITT J ABGEBROCHEN: %s: %s" % (type(e).__name__, e))
    try:
        hd3 = getattr(fe, "fb", None) is not None and fe.fb.height >= 720
        with _Messbedingungen(A, fm, fe, hd3):
            _abschnitt_k(b, fe, S, A)
    except Exception as e:                               # noqa: BLE001
        b("   ABSCHNITT K ABGEBROCHEN: %s: %s" % (type(e).__name__, e))
    b("")
    b("=" * 62)
    b("Ende. Nichts auf der Karte wurde veraendert.")
    b("=" * 62)
    return b.text()
