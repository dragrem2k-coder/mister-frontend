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
darauf wartet: waehrend jemand eine Seite ansieht, rechnet ein
Hintergrund-Thread die Cover der als naechstes zu erwartenden Eintraege
vor und legt sie auf der Karte ab. Scrollt der Nutzer weiter, liegen sie
schon da.

ZWEI EHRLICHE EINSCHRAENKUNGEN, die den ganzen Entwurf praegen:

1. Die MiSTer-CPU ist schwach, und das Skalieren ist reines Python.
   Ein Hintergrund-Thread nimmt dem Zeichnen also tatsaechlich
   Rechenzeit weg (Pythons GIL laesst immer nur einen Thread rechnen).
   Deshalb laeuft hier NICHTS, solange jemand bedient: jede Eingabe
   ruft abbrechen() auf, und der Thread laesst seine Liste augenblicklich
   fallen. Er kann eine bereits begonnene Miniatur nicht mittendrin
   abbrechen - schlimmstenfalls teilt er sich also noch fuer die Dauer
   EINER Berechnung die CPU mit dem Zeichnen. Genau deshalb wird auch
   nur bei laengerer Ruhe ueberhaupt gestartet.

2. Der Thread fasst die Arbeitsspeicher-Caches von ArtCache mit keinem
   Byte an - er schreibt ausschliesslich Dateien (siehe prewarm_thumb()
   in fe/art.py). Diese Caches sind Liste + Woerterbuch ohne jede
   Sperre; zwei Threads darin gleichzeitig waeren die Sorte Fehler, die
   sich hinterher nie zuverlaessig nachstellen laesst.
"""
import threading
import time

from fe.art import prewarm_thumb, thumb_cache_has
from fe.log import LOG


class CoverPrewarmer:
    """Ein Hintergrund-Thread, eine Auftragsliste, jederzeit abbrechbar."""

    # Kurze Pause zwischen zwei Miniaturen. Sieht nach Kleinigkeit aus,
    # ist aber der Unterschied zwischen "arbeitet im Hintergrund" und
    # "macht die Bedienung zaeh": ohne sie haelt der Thread die CPU
    # dauerhaft besetzt, und die naechste Eingabe muss sich ihren Anteil
    # erst erkaempfen. Mit ihr bleibt genug Luft, dass ein Tastendruck
    # sofort ankommt.
    PAUSE = 0.02

    def __init__(self):
        self._auftraege = []
        self._generation = 0
        self._wecker = threading.Condition()
        self._thread = None
        self._ende = False
        # Nur fuer die Protokollzeile - keine Steuerung haengt daran.
        self.gerechnet = 0
        self.lagen_schon_da = 0
        self.fehler = 0

    # -- Steuerung aus dem Hauptthread -----------------------------------

    def start(self):
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._schleife,
                                        name="cover-prewarm", daemon=True)
        self._thread.start()

    def uebergeben(self, auftraege):
        """Neue Auftragsliste [(pfad, breite, hoehe), ...] setzen.

        Ersetzt eine eventuell noch laufende Liste vollstaendig - was
        gerade noch anstand, ist mit der neuen Position ohnehin
        ueberholt. Die Generationsnummer sorgt dafuer, dass der Thread
        die alte Liste nicht noch zu Ende bearbeitet."""
        with self._wecker:
            self._auftraege = list(auftraege)
            self._generation += 1
            self._wecker.notify_all()

    def abbrechen(self):
        """Sofort aufhoeren. Wird bei JEDER Eingabe gerufen - muss
        deshalb billig sein und darf nie blockieren."""
        with self._wecker:
            if not self._auftraege:
                return
            self._auftraege = []
            self._generation += 1

    def beenden(self):
        with self._wecker:
            self._ende = True
            self._auftraege = []
            self._generation += 1
            self._wecker.notify_all()

    def beschaeftigt(self):
        with self._wecker:
            return bool(self._auftraege)

    # -- Der Thread selbst ------------------------------------------------

    def _schleife(self):
        while True:
            with self._wecker:
                while not self._auftraege and not self._ende:
                    self._wecker.wait()
                if self._ende:
                    return
                meine_generation = self._generation
                auftraege = self._auftraege
            for pfad, bw, bh in auftraege:
                with self._wecker:
                    # Zwischen zwei Miniaturen pruefen, ob die Liste
                    # inzwischen ueberholt ist (Eingabe oder neue
                    # Position). Das ist der einzige Abbruchpunkt - eine
                    # einmal begonnene Berechnung laeuft zu Ende.
                    if self._ende or self._generation != meine_generation:
                        break
                try:
                    ergebnis = prewarm_thumb(pfad, bw, bh)
                except Exception as e:              # noqa: BLE001
                    # Ein Fehler hier darf das Frontend NIE beeintraechtigen -
                    # es geht um Vorratshaltung, nicht um etwas, das
                    # jemand gerade sehen will.
                    LOG("PREWARM Fehler (%s): %s" % (pfad, e))
                    ergebnis = "fehler"
                if ergebnis == "fertig":
                    self.gerechnet += 1
                elif ergebnis == "treffer":
                    self.lagen_schon_da += 1
                elif ergebnis == "fehler":
                    self.fehler += 1
                time.sleep(self.PAUSE)
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
    um Groessenordnungen billiger, als sie erst im Thread festzustellen.
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
