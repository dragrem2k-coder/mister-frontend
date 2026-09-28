#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MiSTer-Systemnahes: update_all und der Speicher-Wächter (Build 213).

ZWEI KLEINE DINGE, DIE BEIDE AUS DEMSELBEN GRUND HIER STEHEN: sie
fassen den MiSTer an, nicht das Frontend, und sie duerfen deshalb
nicht mitten im Zeichenweg passieren.

--------------------------------------------------------------------
1. UPDATE_ALL
--------------------------------------------------------------------
Das Aktualisieren der Cores ist die Aufgabe von update_all, und
fe/cores.py sagt ausdruecklich, warum wir es nicht selbst nachbauen:
"Es hier noch einmal zu bauen hiesse, eine zweite Quelle der Wahrheit
fuer die wichtigsten Dateien auf der Karte zu schaffen."

Was fehlte, war nur der Weg dorthin - update_all liegt als Skript in
Scripts/, und Skripte kann das Frontend seit langem starten. Hier
steht deshalb NICHTS ausser: wo liegt es, und wann lief es zuletzt.

WARUM KEINE "UPDATES VERFUEGBAR"-ABFRAGE UEBER DAS NETZ, und das ist
eine bewusste Absage: dafuer muesste das Frontend die Datenbanken des
MiSTer-Downloaders selbst auswerten und ihre Versionslogik nachbauen -
genau die zweite Quelle der Wahrheit, die fe/cores.py ausschliesst.
Was stattdessen hier steht, ist nachpruefbar und kostet nichts: das
Datum des letzten Lauf(protokoll)s. "Zuletzt vor 23 Tagen" sagt dem
Nutzer genug, um zu entscheiden.

--------------------------------------------------------------------
2. DER SPEICHER-WAECHTER
--------------------------------------------------------------------
Steckt man einen USB-Stick ein, waehrend das Frontend laeuft, findet
das Frontend die Spiele darauf nicht - eingelesen wird beim Start
(siehe _discover_games_bases() in fe/paths.py, das SD, usb0-5, alles
unter /media und CIFS kennt). Bisher musste man das selbst wissen und
neu einlesen.

WAS DIESES MODUL TUT UND WAS NICHT: es merkt sich, was beim Einlesen
eingehaengt war, und meldet eine Aenderung. Es liest NICHT von selbst
neu ein. Ein Neueinlesen dauert bei 30.000 Spielen Minuten - das darf
nur passieren, wenn der Nutzer es will. Der Waechter sagt Bescheid,
entscheiden tut der Mensch.

UND ER DARF NICHT IM ZEICHENWEG LAUFEN. /media abzufragen ist ein
Dateisystemzugriff; bei jedem Bild waere das genau die Sorte stiller
Kosten, gegen die die Builds 104-110 und 212 angegangen sind. Deshalb
eine eigene Uhr (MOUNT_TAKT) und der Aufruf ausschliesslich im
Leerlaufzweig der Hauptschleife.
"""
import os
import time

from fe.log import LOG

SCRIPTS_DIR = "/media/fat/Scripts"

# update_all bringt seine eigenen Namen mit - je nach Fassung.
UPDATE_ALL_KANDIDATEN = ("update_all.sh", "update_all")

# Wo update_all seine Spuren hinterlaesst. Der erste vorhandene Pfad
# zaehlt; existiert keiner, wird kein Datum gezeigt (und nichts
# behauptet).
UPDATE_ALL_SPUREN = (
    "/media/fat/Scripts/.config/update_all/update_all.log",
    "/media/fat/Scripts/.config/update_all",
    "/media/fat/Scripts/.config/downloader/downloader.log",
)

MEDIA = "/media"

# Sekunden zwischen zwei Blicken auf /media. Drei Sekunden sind
# schnell genug, dass man das Einstecken noch mit dem Vorgang
# verbindet, und selten genug, dass es nicht auffaellt.
MOUNT_TAKT = 3.0


def update_all_pfad():
    """Das update_all-Skript - oder None, wenn es nicht da ist."""
    for name in UPDATE_ALL_KANDIDATEN:
        pfad = os.path.join(SCRIPTS_DIR, name)
        if os.path.isfile(pfad):
            return pfad
    return None


def update_all_letzter_lauf():
    """Wann update_all zuletzt lief, als Unix-Zeit - oder None.

    Abgelesen an der Aenderungszeit seiner Spuren, nicht an einem
    eigenen Vermerk: ein eigener Vermerk wuerde nur zeigen, wann das
    FRONTEND es gestartet hat, und der Nutzer startet es meistens
    direkt aus dem MiSTer-Menue."""
    for pfad in UPDATE_ALL_SPUREN:
        try:
            return os.path.getmtime(pfad)
        except OSError:
            continue
    return None


def tage_seit(zeitpunkt, jetzt=None):
    """Ganze Tage seit einem Zeitpunkt - oder None.

    Eigene kleine Funktion, damit der Test sie ohne Uhr pruefen kann."""
    if not zeitpunkt:
        return None
    if jetzt is None:
        jetzt = time.time()
    return max(0, int((jetzt - zeitpunkt) // 86400))


def eingehaengt():
    """Die Menge der aktuell unter /media eingehaengten Namen.

    Nur die NAMEN, nicht der Inhalt: es geht um "ist etwas dazu- oder
    weggekommen", und dafuer genuegt ein listdir. Ein Fehler beim
    Lesen liefert None - das heisst "unbekannt" und loest ausdruecklich
    KEINE Meldung aus, sonst meldete ein kurzzeitig nicht lesbares
    /media eine Aenderung, die es nicht gab."""
    try:
        return frozenset(os.listdir(MEDIA))
    except OSError:
        return None


class SpeicherWaechter(object):
    """Merkt sich den Stand beim Einlesen und meldet Aenderungen.

    Bewusst eine kleine Klasse und keine Handvoll Modulvariablen: so
    kann der Test mehrere Waechter unabhaengig voneinander laufen
    lassen, und im Programm gibt es genau einen."""

    def __init__(self):
        self.stand = None
        self.naechster_blick = 0.0
        self.gemeldet = None

    def merken(self, stand=None):
        """Den jetzigen Stand als "so war es beim Einlesen" festhalten.
        Wird nach jedem Einlesen der Spieleliste gerufen."""
        self.stand = eingehaengt() if stand is None else stand
        self.gemeldet = None

    def pruefen(self, jetzt=None):
        """Hat sich etwas geaendert? Liefert die Beschreibung der
        Aenderung (z.B. "usb0 dazu") oder None.

        Meldet jede Aenderung nur EINMAL - sonst stuende die Meldung
        bei jedem Leerlauf-Durchgang wieder da, und das waere genau das
        Aufploppen, ueber das der Nutzer sich bei anderen Dingen
        beschwert hat."""
        if jetzt is None:
            jetzt = time.monotonic()
        if jetzt < self.naechster_blick:
            return None
        self.naechster_blick = jetzt + MOUNT_TAKT
        if self.stand is None:
            return None
        jetzt_stand = eingehaengt()
        if jetzt_stand is None or jetzt_stand == self.stand:
            return None
        if jetzt_stand == self.gemeldet:
            return None          # diese Aenderung ist schon gemeldet
        self.gemeldet = jetzt_stand
        dazu = sorted(jetzt_stand - self.stand)
        weg = sorted(self.stand - jetzt_stand)
        teile = []
        if dazu:
            teile.append("+" + ", ".join(dazu))
        if weg:
            teile.append("-" + ", ".join(weg))
        text = " ".join(teile)
        LOG("Speicher-Waechter: %s (war: %s)"
            % (text, ", ".join(sorted(self.stand)) or "leer"))
        return text
