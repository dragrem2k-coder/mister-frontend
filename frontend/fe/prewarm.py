#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cover-Miniaturen im Leerlauf vorberechnen.

NEUES FEATURE (Build 73). Anlass sind echte Messwerte vom Geraet des
Nutzers, nachdem drei Vermutungen von mir nacheinander widerlegt waren
(Dateisystem, Sortierung, Bildschirm-Spiegel/Stream-Overlay):

    PERF split: bgbild=0 bg=0 restore=3 rows=5(13) art=225 flip=1 ms
    PERF draw_page_items: 251 ms

Von 251 ms Seitenaufbau entfallen 225 ms auf EIN Cover, das noch nicht
vorberechnet war. Das Zeichnen selbst - Hintergrund, Zeilen, Ausgabe -
kostet zusammen rund 20 ms. Beim zweiten Besuch kostet dasselbe Cover
1-6 ms. Der Festplatten-Cache funktioniert also einwandfrei, er ist beim
ersten Durchgang durch eine Liste nur eben noch leer. Genau das erlebt
der Nutzer als "geht man in einen Unterordner und wieder zurueck, haengt
es 1-2 Sekunden" - dort werden mehrere solcher Cover hintereinander zum
ersten Mal berechnet.

Der Ansatz hier verschiebt diesen einmaligen Preis dorthin, wo niemand
darauf wartet: waehrend jemand eine Seite ansieht, rechnet der
Vorauslader die Cover der als naechstes zu erwartenden Eintraege vor und
legt sie auf der Karte ab. Scrollt der Nutzer weiter, liegen sie schon
da.

GEAENDERT (Build 102): EIGENER PROZESS STATT HINTERGRUND-THREAD
===============================================================

Bis Build 101 lief das Vorrechnen in einem Thread DIESES Prozesses. Die
erste der beiden hier frueher dokumentierten Einschraenkungen lautete:

    "Die MiSTer-CPU ist schwach, und das Skalieren ist reines Python.
     Ein Hintergrund-Thread nimmt dem Zeichnen also tatsaechlich
     Rechenzeit weg (Pythons GIL laesst immer nur einen Thread
     rechnen). [...] Er kann eine bereits begonnene Miniatur nicht
     mittendrin abbrechen - schlimmstenfalls teilt er sich also noch
     fuer die Dauer EINER Berechnung die CPU mit dem Zeichnen."

Diese eine Berechnung war der wunde Punkt, und zwar praktisch nur auf
HDMI: ein Cover fuer 1080p hat rund neunmal so viele Bildpunkte wie
eines fuer 240p. Auf dem Geraet gemessen 200-500 ms je Erstberechnung,
bei einem Kategorie-Logo 722 ms. Wer genau dann eine Taste drueckt,
wartet, bis sie fertig ist. Nutzer-Rueckmeldung: "das Scrollen ist mir
auf HDMI zu langsam, vor allem wenn Zeilen nach unten neu ins Bild
kommen, auch wenn ich zwischen den Ordnern hin und her wechsle" - genau
die beiden Situationen, in denen reihenweise unberechnete Cover
anstehen.

Der DE10-Nano hat zwei CPU-Kerne, und Pythons GIL gilt nur innerhalb
eines Prozesses. Als eigener Prozess (fe/prewarm_worker.py) rechnet der
Vorauslader auf dem zweiten Kern. Die zweite fruehere Einschraenkung -
"fasst die Arbeitsspeicher-Caches von ArtCache mit keinem Byte an" -
gilt jetzt von selbst: ein eigener Prozess hat seinen eigenen
Adressraum und KANN sie nicht anfassen.

NACHGEMESSEN (tools/diag_vorauslader.py, Rechner mit ebenfalls zwei
Kernen; Dauer eines Scrollschritts waehrend der Vorauslader arbeitet,
und wie viele Miniaturen er in denselben drei Sekunden schafft):

                Leerlauf    Thread (bis 101)    Prozess (ab 102)
    CRT          0.252 ms    0.448 ms  +78%  32   0.294 ms  +17%  57
    HDMI         1.001 ms    1.075 ms   +7%   3   1.060 ms   +6%  25

Zwei Dinge stehen da, und das zweite ist fuer die gemeldete Beschwerde
das wichtigere. Erstens bremst der Thread das Zeichnen deutlich staerker
(+78 % gegen +17 % auf CRT). Zweitens - und das ist der eigentliche
Gewinn auf HDMI - kommt der Vorauslader als Prozess ACHTMAL so weit: 25
statt 3 fertige Miniaturen. Der Thread bremst also nicht nur, er kommt
selbst kaum voran, weil er sich die Rechenzeit mit dem Zeichnen teilt.
Und je mehr Cover vorgerechnet sind, desto seltener muss der
Zeichenpfad beim Scrollen selbst rechnen - genau die Situation, in der
"Zeilen kommen unten neu ins Bild" sich zaeh angefuehlt hat.

EHRLICH DAZU: der Aufschlag ist auch im Prozess-Betrieb nicht null.
Beide teilen sich weiterhin Speicherbus und SD-Karte. Null war nie zu
erwarten; um den Faktor zwischen +78 % und +17 % ging es.

ABBRECHEN BLEIBT TROTZDEM DRIN, aus einem anderen Grund als vorher: der
Arbeitsprozess teilt sich zwar keine Rechenzeit mehr, aber sehr wohl die
SD-Karte und den Speicherbus. Ausserdem sind seine Auftraege nach einer
Eingabe fachlich veraltet. Neu ist, dass ein bereits begonnener Auftrag
nicht mehr stoert - er darf in Ruhe zu Ende laufen.

RUECKFALL: laesst sich der Prozess nicht starten (kein python3 im Pfad,
Speicher knapp, Rechte), faellt diese Klasse auf genau den Thread
zurueck, den es vorher gab. Schlechter als vorher wird es dadurch nie.
Dasselbe passiert, wenn der Prozess waehrend des Betriebs wegbricht.
"""
import os
import subprocess
import sys
import threading
import time

from fe.art import prewarm_thumb, thumb_cache_has
import fe.art as _art
from fe.log import LOG

WORKER = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "prewarm_worker.py")


class CoverPrewarmer:
    """Eine Auftragsliste, ein Arbeiter, jederzeit abbrechbar.

    Der Arbeiter ist bevorzugt ein eigener Prozess (zweiter CPU-Kern),
    ersatzweise ein Thread in diesem Prozess. Nach aussen ist das nicht
    zu unterscheiden - die vier Methoden start/uebergeben/abbrechen/
    beenden verhalten sich in beiden Faellen gleich."""

    # Kurze Pause zwischen zwei Miniaturen.
    #
    # IM THREAD-BETRIEB ist sie der Unterschied zwischen "arbeitet im
    # Hintergrund" und "macht die Bedienung zaeh": ohne sie haelt der
    # Thread die CPU dauerhaft besetzt, und die naechste Eingabe muss
    # sich ihren Anteil erst erkaempfen.
    #
    # IM PROZESS-BETRIEB geht es nicht mehr um Rechenzeit (die kommt vom
    # zweiten Kern), sondern um die SD-Karte und den Speicherbus, die
    # sich beide Prozesse weiterhin teilen. Deshalb dort kuerzer, aber
    # nicht null - ein Vorauslader, der die Karte ununterbrochen
    # beschaeftigt, macht das Nachladen im Zeichenpfad langsamer.
    PAUSE = 0.02
    PAUSE_PROZESS = 0.01

    def __init__(self):
        self._auftraege = []
        self._generation = 0
        self._wecker = threading.Condition()
        self._thread = None
        self._ende = False
        self._proc = None
        # None = noch nicht versucht. Danach True/False und dabei
        # bleibt es: ein einmal gescheiterter Start wird nicht bei jedem
        # Leerlauf erneut probiert.
        self._prozess_moeglich = None
        # Nur fuer die Protokollzeile - keine Steuerung haengt daran.
        self.gerechnet = 0
        self.lagen_schon_da = 0
        self.fehler = 0

    # -- Steuerung aus dem Hauptthread -----------------------------------

    def start(self):
        if self._thread is not None:
            return
        if self._prozess_moeglich is None:
            self._prozess_moeglich = self._prozess_starten()
        elif self._prozess_moeglich and self._proc is None:
            # Nach einem beenden() (z.B. beim Spielstart) wieder
            # hochfahren. Gelang der Start beim ersten Mal nicht, wird er
            # bewusst nicht erneut versucht - siehe _prozess_verloren().
            self._prozess_starten()
        t = threading.Thread(target=self._schleife, name="cover-prewarm",
                             daemon=True)
        # ERST merken, dann starten: die Schleife prueft bei jedem
        # Durchgang, ob sie noch der aktuelle Arbeiter ist (self._thread
        # is meiner). Startete sie vor der Zuweisung, koennte sie sich
        # selbst fuer abgeloest halten und sofort zurueckkehren.
        self._thread = t
        t.start()

    def uebergeben(self, auftraege):
        """Neue Auftragsliste [(pfad, breite, hoehe), ...] setzen.

        Ersetzt eine eventuell noch laufende Liste vollstaendig - was
        gerade noch anstand, ist mit der neuen Position ohnehin
        ueberholt. Die Generationsnummer sorgt dafuer, dass der Arbeiter
        die alte Liste nicht noch zu Ende bearbeitet."""
        with self._wecker:
            self._auftraege = list(auftraege)
            self._generation += 1
            self._wecker.notify_all()

    def dringend(self, pfad, bw, bh):
        """EIN Auftrag mit Vorrang - jemand schaut gerade darauf.

        NEU (Build 105). Gerufen aus dem Zeichenpfad, wenn die Miniatur
        eines gerade sichtbaren Covers noch nicht auf der Karte liegt
        (siehe ArtCache._auslagern_versuchen() in fe/art.py). Statt sie
        dort zu rechnen - auf HDMI 200-500 ms, in denen die Bedienung
        steht - wandert sie hierher.

        Die Vorratsliste wird dabei bewusst VERWORFEN: sie enthaelt
        Cover, die vielleicht gleich gebraucht werden, und dieses eine
        wird jetzt gebraucht. Nachgefuellt wird sie ohnehin beim
        naechsten Ruhemoment (PREWARM_SETTLE, 0.1 s).

        Rueckgabe False heisst "nicht angenommen, rechne selbst". Genau
        das passiert im THREAD-Betrieb, und zwar absichtlich: ohne
        zweiten Kern nimmt das Rechnen dem Zeichnen dieselbe Zeit weg -
        nur eben spaeter und mit einem leeren Cover-Platz dazwischen.
        Ohne Arbeitsprozess bleibt es deshalb beim bisherigen Verhalten."""
        self.start()
        if self._proc is None:
            return False
        self.uebergeben([(pfad, bw, bh)])
        return True

    def abbrechen(self):
        """Sofort aufhoeren. Wird bei JEDER Eingabe gerufen - muss
        deshalb billig sein und darf nie blockieren."""
        with self._wecker:
            if not self._auftraege:
                return
            self._auftraege = []
            self._generation += 1

    def beenden(self):
        """Alles anhalten und den Arbeitsprozess abraeumen.

        GEAENDERT (Build 103): danach ist ein erneutes start() wieder
        moeglich. Gebraucht wird das beim Core-Start - siehe run_core()
        in frontend.py: solange jemand spielt, soll hier weder ein
        Prozess herumliegen noch Speicher belegt sein. Vorher war
        beenden() endgueltig und wurde nur beim Herunterfahren gerufen.

        _prozess_moeglich wird bewusst NICHT zurueckgesetzt: ein einmal
        gescheiterter Prozessstart soll nicht bei jeder Rueckkehr aus
        einem Spiel erneut versucht werden."""
        with self._wecker:
            self._ende = True
            self._auftraege = []
            self._generation += 1
            self._wecker.notify_all()
        with self._wecker:
            # Ab hier ist KEIN Thread mehr der aktuelle Arbeiter. Ein
            # noch laufender sieht das beim naechsten Durchgang und
            # kehrt zurueck - auch dann noch, wenn _ende unten wieder
            # auf False steht. Ohne diese zweite, thread-eigene
            # Abbruchbedingung koennte ein alter Thread in seiner
            # Warteschleife haengenbleiben und nach einem spaeteren
            # start() als ZWEITER Arbeiter neben dem neuen weiterlaufen -
            # zwei Schreiber auf derselben Leitung zum Arbeitsprozess,
            # und die Antworten gehoerten niemandem mehr eindeutig.
            t, self._thread = self._thread, None
            self._wecker.notify_all()
        self._prozess_beenden()
        if t is not None and t is not threading.current_thread():
            # Kurz warten, aber nie haengen bleiben: der Thread kann in
            # einer bereits begonnenen Miniatur stecken, und darauf zu
            # warten waere genau die Verzoegerung, die wir vermeiden
            # wollen.
            t.join(timeout=0.2)
        with self._wecker:
            self._ende = False

    def beschaeftigt(self):
        with self._wecker:
            return bool(self._auftraege)

    def betriebsart(self):
        """"prozess", "thread" oder "aus" - fuer Protokoll und Tests."""
        if self._thread is None:
            return "aus"
        return "prozess" if self._proc is not None else "thread"

    # -- Der Arbeitsprozess ----------------------------------------------

    def _prozess_starten(self):
        """Versucht, den Arbeitsprozess zu starten. True bei Erfolg.

        Scheitert das, ist das kein Fehler, sondern ein Rueckfall: die
        Schleife unten arbeitet die Auftraege dann selbst ab, genau wie
        vor Build 102."""
        if not os.path.isfile(WORKER):
            LOG("PREWARM: %s fehlt - Vorauslader laeuft als Thread" % WORKER)
            return False
        try:
            self._proc = subprocess.Popen(
                [sys.executable or "python3", WORKER],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                # stderr bewusst NICHT abgefangen: niemand liest es hier,
                # und ein volles Rohr wuerde den Arbeitsprozess
                # irgendwann blockieren. Es landet dort, wo auch die
                # Ausgaben des Frontends landen.
                close_fds=True)
        except Exception as e:                           # noqa: BLE001
            LOG("PREWARM: Arbeitsprozess nicht startbar (%s) - "
                "Vorauslader laeuft als Thread" % e)
            self._proc = None
            return False
        LOG("PREWARM: Arbeitsprozess laeuft (PID %d) - rechnet auf dem "
            "zweiten CPU-Kern" % self._proc.pid)
        return True

    def _prozess_beenden(self):
        p, self._proc = self._proc, None
        if p is None:
            return
        try:
            if p.stdin:
                p.stdin.close()
        except OSError:
            pass
        try:
            p.terminate()
        except OSError:
            pass

    def _prozess_verloren(self, grund):
        """Der Arbeitsprozess antwortet nicht mehr - ab jetzt selbst
        rechnen. Bewusst kein Neustartversuch: bricht er einmal weg,
        bricht er meist aus einem Grund weg, der beim zweiten Mal wieder
        zutrifft (Speicher, Rechte), und eine Startschleife im Leerlauf
        waere schlimmer als der Rueckfall."""
        LOG("PREWARM: Arbeitsprozess weg (%s) - Vorauslader rechnet ab "
            "jetzt selbst" % grund)
        self._prozess_beenden()

    def _auftrag_im_prozess(self, pfad, bw, bh):
        """Einen Auftrag hinschicken und auf die Antwort warten.

        Das Warten ist beabsichtigt, nicht nachlaessig: nur so bleibt
        Abbrechen wirksam (siehe Kopf von fe/prewarm_worker.py). Waehrend
        des Wartens haelt dieser Thread die GIL nicht - er haengt in
        einem Lesevorgang, und genau deshalb kann der Hauptthread in
        dieser Zeit ungestoert zeichnen."""
        p = self._proc
        if p is None or p.stdin is None or p.stdout is None:
            return None
        # Ein Zeilenumbruch im Pfad wuerde das Protokoll zerlegen. Kommt
        # praktisch nicht vor, ist aber billig auszuschliessen.
        if "\n" in pfad or "\t" in pfad:
            return "uebersprungen"
        zeile = "%s\t%d\t%d\t%s\n" % (_art.THUMB_CACHE_DIR, bw, bh, pfad)
        try:
            p.stdin.write(zeile.encode("utf-8", "surrogateescape"))
            p.stdin.flush()
            antwort = p.stdout.readline()
        except (OSError, ValueError) as e:
            self._prozess_verloren(str(e))
            return None
        if not antwort:
            self._prozess_verloren("Rohr geschlossen")
            return None
        return {b"f": "fertig", b"t": "treffer",
                b"u": "uebersprungen"}.get(antwort[:1], "fehler")

    # -- Die Schleife -----------------------------------------------------

    def _schleife(self):
        meiner = threading.current_thread()
        while True:
            with self._wecker:
                while (not self._auftraege and not self._ende
                       and self._thread is meiner):
                    self._wecker.wait()
                if self._ende or self._thread is not meiner:
                    return
                meine_generation = self._generation
                auftraege = self._auftraege
            for pfad, bw, bh in auftraege:
                with self._wecker:
                    # Zwischen zwei Miniaturen pruefen, ob die Liste
                    # inzwischen ueberholt ist (Eingabe oder neue
                    # Position) - oder ob dieser Thread ueberhaupt noch
                    # der aktuelle Arbeiter ist (siehe beenden()).
                    if (self._ende or self._thread is not meiner
                            or self._generation != meine_generation):
                        break
                ergebnis = None
                if self._proc is not None:
                    ergebnis = self._auftrag_im_prozess(pfad, bw, bh)
                if ergebnis is None and (self._ende
                                         or self._thread is not meiner):
                    # Wir sind gerade beim Abraeumen - dann NICHT
                    # ersatzweise selbst rechnen, sonst zoegert genau das
                    # den Spielstart hinaus, den das Abraeumen freimachen
                    # sollte.
                    break
                if ergebnis is None:
                    # Rueckfall: entweder von Anfang an kein Prozess,
                    # oder er ist gerade weggebrochen. Dann rechnet
                    # dieser Thread selbst - wie vor Build 102.
                    try:
                        ergebnis = prewarm_thumb(pfad, bw, bh)
                    except Exception as e:               # noqa: BLE001
                        # Ein Fehler hier darf das Frontend NIE
                        # beeintraechtigen - es geht um Vorratshaltung,
                        # nicht um etwas, das jemand gerade sehen will.
                        LOG("PREWARM Fehler (%s): %s" % (pfad, e))
                        ergebnis = "fehler"
                if ergebnis == "fertig":
                    self.gerechnet += 1
                elif ergebnis == "treffer":
                    self.lagen_schon_da += 1
                elif ergebnis == "fehler":
                    self.fehler += 1
                time.sleep(self.PAUSE_PROZESS if self._proc is not None
                           else self.PAUSE)
            with self._wecker:
                if self._generation == meine_generation:
                    self._auftraege = []


PREWARMER = CoverPrewarmer()


def auftraege_bauen(eintraege, mitte, kastenmass, vorwaerts=True,
                    voraus=20, zurueck=6):
    """Aus einer Eintragsliste die Reihenfolge bauen, in der die Cover
    voraussichtlich gebraucht werden.

    'kastenmass' ist eine Funktion eintrag -> (breite, hoehe) oder None -
    sie MUSS dieselbe Groesse liefern, die der Zeichenpfad spaeter
    anfragt (in frontend.py ist das cover_box_size(); der Schluessel des
    Festplatten-Caches enthaelt die Kastengroesse, eine abweichende
    Rechnung erzeugte also fleissig Miniaturen, die nie jemand findet).

    In Scrollrichtung wird deutlich weiter vorausgeschaut als zurueck -
    wer nach unten blaettert, blaettert meistens weiter nach unten.
    Eintraege, deren Miniatur schon auf der Karte liegt, fallen hier
    schon heraus: die Pruefung ist ein reines os.path.exists() und damit
    um Groessenordnungen billiger, als sie erst im Arbeiter festzu-
    stellen.
    """
    if not eintraege:
        return []
    n = len(eintraege)
    d = 1 if vorwaerts else -1
    reihenfolge = []
    for i in range(1, voraus + 1):
        reihenfolge.append(mitte + i * d)
    for i in range(1, zurueck + 1):
        reihenfolge.append(mitte - i * d)
    auftraege = []
    gesehen = set()
    for idx in reihenfolge:
        if idx < 0 or idx >= n or idx in gesehen:
            continue
        gesehen.add(idx)
        try:
            mass = kastenmass(eintraege[idx])
        except Exception:                            # noqa: BLE001
            continue
        if not mass:
            continue
        pfad, bw, bh = mass
        if not pfad or bw <= 0 or bh <= 0:
            continue
        if thumb_cache_has(pfad, bw, bh):
            continue
        auftraege.append((pfad, bw, bh))
    return auftraege
