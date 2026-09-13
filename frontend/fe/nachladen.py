#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fertige Miniaturen von der Karte in den Arbeitsspeicher holen.

NEUES FEATURE (Build 125). Nutzerfrage, und sie trifft den Punkt:

    "kann man nicht was anlegen, JSON oder txt Datei, dass der RAM
     schnell gefuellt wird? Muss es doch eine Loesung geben."

EINE DATEI MIT PFADEN HILFT NICHT, und zwar aus einem einzigen Grund:
teuer ist nicht das FINDEN einer Miniatur, sondern das Entpacken. Eine
Miniatur auf der Karte ist zlib-gepackt (siehe _thumb_cache_get() in
fe/art.py); ein Treffer kostet Oeffnen, Lesen und Auspacken. Auf dem
grossen Galerie-Cover (426x569 = 970 KB roh) sind das auf dem MiSTer
nachgerechnet zweistellige Millisekunden - unabhaengig davon, ob
irgendwo eine Liste steht, wo die Datei liegt.

DIE RICHTUNG STIMMT TROTZDEM, sie muss nur auf die richtige Stelle
zielen. Nach einem Neustart ist der Arbeitsspeicher leer, und zwar
auch dann, wenn "Miniaturen vorbereiten" komplett durchgelaufen ist -
das fuellt die KARTE, nicht den RAM. Genau das erlebt man als "bei
jedem Neustart laedt es wieder nach".

WARUM DER VORHANDENE VORAUSLADER DAS NICHT ERLEDIGEN KANN: er ist seit
Build 102 ein EIGENER PROZESS (siehe fe/prewarm.py). Das war richtig
und ist es weiterhin - das Verkleinern ist reines Python und wuerde als
Thread dem Zeichnen die Rechenzeit wegnehmen. Aber ein eigener Prozess
hat einen eigenen Adressraum und KANN unseren RAM-Cache gar nicht
fuellen. Er meldet eine schon vorhandene Miniatur als "Treffer" und
geht weiter; in unserem Prozess liegt sie deswegen trotzdem nicht.

HIER GEHT EIN THREAD, WO DORT EINER FALSCH WAERE. Der Unterschied ist
die Arbeit selbst:

    Verkleinern   reines Python      haelt die GIL die ganze Zeit
    Auspacken     zlib (C-Modul)     GIBT DIE GIL FREI

zlib.decompress() laesst waehrend des Auspackens andere Threads laufen,
und das Lesen von der Karte ebenfalls. Ein Nachlade-Thread nimmt dem
Zeichnen also fast nichts weg - anders als das Verkleinern, das genau
deshalb in einen eigenen Prozess musste.

DIE FERTIGE MINIATUR TRAEGT DIESER THREAD TROTZDEM NICHT SELBST EIN.
Sie wandert ueber eine Warteschlange in den Hauptthread, der sie im
Leerlauf abholt. Grund: der Cache raeumt beim Eintragen auch auf
(_scaled_cache_put loescht die aeltesten, wenn das Budget reisst), und
zwei Threads, die gleichzeitig dieselbe Liste kuerzen, sind eine
Fehlerquelle, die man sich fuer eine reine Beschleunigung nicht
einhandelt. Der teure Teil - Lesen und Auspacken - passiert im Thread,
das Eintragen ist eine Zuweisung.

WAS ER NICHT TUT: rechnen. Findet er keine fertige Miniatur, geht er
weiter. Das Berechnen bleibt beim Vorauslader (eigener Prozess).
"""
import queue
import threading
import time

from fe.log import LOG


class MiniaturLader:
    """Ein Thread, eine Auftragsliste, jederzeit abbrechbar."""

    # Kurze Pause zwischen zwei Miniaturen. Auch wenn zlib die GIL
    # freigibt: die SD-Karte teilen sich Zeichenpfad, Vorauslader-
    # Prozess und dieser Thread. Ohne Pause nimmt er den anderen beiden
    # den Datendurchsatz weg - genau der Fehler, der beim Vorauslader
    # schon einmal gemessen wurde (siehe PAUSE in fe/prewarm.py).
    PAUSE = 0.01

    # Mehr als das bringt nichts: was darueber hinaus im Voraus geholt
    # wird, ist bis zum Hinsehen laengst wieder verdraengt.
    MAX_OFFEN = 64

    def __init__(self, lesen):
        """lesen(pfad, breite, hoehe) -> (bw, bh, pixel) oder None.

        Wird von aussen hereingereicht (in der Praxis
        fe.art._thumb_cache_get), damit dieses Modul nichts ueber die
        Ablage auf der Karte wissen muss - und damit ein Test eine
        Attrappe einsetzen kann."""
        self._lesen = lesen
        self._auftraege = []
        self._generation = 0
        self._wecker = threading.Condition()
        self._thread = None
        self._ende = False
        self.fertig = queue.Queue()
        # Nur fuer die Protokollzeile.
        self.geholt = 0
        self.nicht_da = 0

    # -- Steuerung aus dem Hauptthread -----------------------------------

    def start(self):
        if self._thread is not None:
            return
        self._ende = False
        t = threading.Thread(target=self._schleife, name="miniatur-lader",
                             daemon=True)
        self._thread = t
        t.start()

    def uebergeben(self, auftraege):
        """Neue Liste [(pfad, breite, hoehe), ...] setzen. Ersetzt eine
        noch laufende vollstaendig - was vorher anstand, ist mit der
        neuen Position ueberholt."""
        with self._wecker:
            self._auftraege = list(auftraege)[:self.MAX_OFFEN]
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
        t, self._thread = self._thread, None
        if t is not None and t.is_alive():
            t.join(timeout=1.0)

    def abholen(self, hoechstens=8):
        """Was der Thread fertig hat, als Liste
        [(pfad, breite, hoehe, (bw, bh, pixel)), ...].

        Aus dem LEERLAUF des Hauptthreads zu rufen. hoechstens begrenzt,
        wie viel pro Runde eingetragen wird - das Eintragen selbst ist
        billig, aber der Aufraeum-Durchlauf im Cache nicht unbedingt,
        und niemand muss 64 Bilder in einem einzigen Tick sehen."""
        raus = []
        for _ in range(hoechstens):
            try:
                raus.append(self.fertig.get_nowait())
            except queue.Empty:
                break
        return raus

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
            for auftrag in auftraege:
                with self._wecker:
                    if (self._ende or self._thread is not meiner
                            or self._generation != meine_generation):
                        break
                pfad, bw, bh = auftrag
                try:
                    ergebnis = self._lesen(pfad, bw, bh)
                except Exception as e:                   # noqa: BLE001
                    # Ein Fehler hier darf das Frontend NIE
                    # beeintraechtigen - es geht um Vorratshaltung.
                    LOG("NACHLADEN Fehler (%s): %s" % (pfad, e))
                    ergebnis = None
                if ergebnis is None:
                    self.nicht_da += 1
                else:
                    self.geholt += 1
                    self.fertig.put((pfad, bw, bh, ergebnis))
                time.sleep(self.PAUSE)
            with self._wecker:
                if self._generation == meine_generation:
                    self._auftraege = []
