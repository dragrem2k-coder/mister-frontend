#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Der ROM-Waechter (Build 258).

NUTZERWUNSCH: "wenn ich im laufenden Betrieb mit WinSCP oder MiSTer
Companion ROMs entferne oder neue hinzufuege, erkennt das Frontend
diese nicht, ohne die Spieleliste neu einzulesen. Kann man das on the
fly machen?"

DIE HALBE ARBEIT WAR SCHON DA, und darum ist dieses Modul so klein:

  * _games_signature() in fe/scan.py bildet seit jeher einen
    Fingerabdruck je System - je ROM-Ordner ein os.path.getmtime(),
    mehr nicht.
  * scan_games() liest seit Build 248 NUR die Systeme neu ein, deren
    Fingerabdruck sich geaendert hat.
  * Build 251 hat daraus den Menuepunkt "nur das Geaenderte nachlesen"
    gemacht, ausgeloest vom Speicher-Waechter.

Es fehlte also weder das Erkennen noch das Nachlesen - es fehlte, dass
im LAUFENDEN Betrieb jemand nachfragt. Genau das tut dieser Waechter,
und er benutzt dafuer dieselbe Mechanik: er setzt denselben Grund, den
auch der Speicher-Waechter setzt, und der vorhandene Menuepunkt
erledigt den Rest.

DREI ENTSCHEIDUNGEN, DIE DEN UNTERSCHIED MACHEN

1. ER LIEST NICHT VON SELBST NACH. Das dauert bei einer grossen
   Sammlung Sekunden bis Minuten, und mitten im Scrollen waere es ein
   sichtbarer Haenger. Es ist ausserdem eine Entscheidung des Nutzers
   und keine des Programms - dieselbe Linie wie beim Speicher-Waechter
   seit Build 213.

2. ER LAEUFT NUR IM RUHEMOMENT. Ein Fingerabdruck ist ein Dutzend
   Dateisystemzugriffe; die haben im Zeichenweg nichts verloren.
   Eigene Uhr (ROMWACHT_TAKT), damit auch der Ruhemoment nicht
   staendig auf die Karte greift.

3. ER SIEHT NUR DIE OBERSTE EBENE - UND DEN GEOEFFNETEN ORDNER.
   Das ist die wichtigste Einschraenkung, und sie ist keine
   Nachlaessigkeit: ein rekursiver Fingerabdruck wurde in v1.32 schon
   einmal gebaut und WIEDER ENTFERNT, weil bei einer grossen Sammlung
   ueber USB jeder Start minutenlang dauerte, bevor ueberhaupt ein
   Bild kam (die Begruendung steht woertlich im Docstring von
   _games_signature()). Ein ROM, das direkt in games/SNES/ landet,
   wird also erkannt; eines in games/SNES/Hacks/ nicht.

   Der Ausgleich kostet genau einen zusaetzlichen Zugriff: der Ordner,
   den der Nutzer GERADE ANSIEHT, wird mitgeprueft. Dort ist die
   Erwartung "das muesste jetzt auftauchen" am groessten, und es ist
   ein einziger getmtime() mehr.

WAS ER NICHT KANN: Karte raus, am PC bearbeiten, wieder rein. Dann
laeuft das Frontend nicht. Und inotify waere die vollstaendige
Loesung, braucht aber eine Ueberwachung JE ORDNER - bei 30.000 Ordnern
also 30.000 Stueck, gegen ein Standardlimit, das auf kleinen Systemen
oft bei 8192 liegt. Das waere zu messen, bevor man es verspricht.
"""
import os
import time

from fe.log import LOG

# Wie oft hoechstens nachgesehen wird. Bewusst traege: eine Aenderung
# am Dateisystem ist nichts, worauf jemand in derselben Sekunde
# wartet, und jeder Blick kostet Zugriffe auf die Karte.
ROMWACHT_TAKT = 20.0

# Obergrenze fuer die zusaetzlich beobachteten Ordner (der geoeffnete
# und seine Kette nach oben). Ohne sie waere eine tief verschachtelte
# Navigation ein wachsender Posten bei jedem Blick.
MAX_EXTRA = 8


def _mtime(pfad):
    try:
        return int(os.path.getmtime(pfad))
    except OSError:
        return None


class RomWaechter(object):
    """Merkt sich den Fingerabdruck beim Einlesen und meldet
    Aenderungen.

    Eine kleine Klasse und keine Modulvariablen - aus demselben Grund
    wie beim SpeicherWaechter: so kann der Test mehrere unabhaengig
    voneinander laufen lassen, und im Programm gibt es genau einen.

    `signatur_fn` wird hereingereicht statt hier importiert. Das ist
    kein Selbstzweck: der Test kann damit zaehlen, wie oft wirklich
    nachgesehen wird, ohne das halbe Frontend zu starten."""

    def __init__(self, signatur_fn=None):
        self._signatur_fn = signatur_fn
        self.stand = None            # {syskey: fingerabdruck}
        self.extra = {}              # {pfad: mtime}
        self.naechster_blick = 0.0
        self.gemeldet = None
        self.blicke = 0              # nur fuer Test und Diagnose

    # -- Signatur ---------------------------------------------------
    def _signatur(self):
        if self._signatur_fn is not None:
            return self._signatur_fn()
        from fe.scan import _games_signature
        return _games_signature()[1]

    def merken(self, extra_pfade=()):
        """Den jetzigen Stand als "so war es beim Einlesen"
        festhalten. Nach jedem Einlesen der Spieleliste zu rufen -
        sonst meldet der Waechter die gerade eingelesene Aenderung
        gleich noch einmal."""
        try:
            self.stand = self._signatur()
        except Exception:                                # noqa: BLE001
            self.stand = None
        self.extra = {p: _mtime(p) for p in self._begrenzt(extra_pfade)}
        self.gemeldet = None

    @staticmethod
    def _begrenzt(pfade):
        raus = []
        for p in pfade or ():
            if p and p not in raus:
                raus.append(p)
            if len(raus) >= MAX_EXTRA:
                break
        return raus

    # -- Pruefen ----------------------------------------------------
    def pruefen(self, extra_pfade=(), jetzt=None):
        """Hat sich etwas geaendert? Liefert eine kurze Beschreibung
        ("SNES") oder None.

        Meldet jede Aenderung nur EINMAL - sonst stuende die Meldung
        bei jedem Durchgang durch den Ruhemoment wieder da. Erst ein
        erneutes merken() (also ein Nachlesen) macht den Weg frei."""
        if jetzt is None:
            jetzt = time.monotonic()
        if jetzt < self.naechster_blick:
            return None
        self.naechster_blick = jetzt + ROMWACHT_TAKT
        if self.stand is None:
            return None
        self.blicke += 1

        # 1. Der geoeffnete Ordner. Zuerst, weil es der billigste Teil
        #    ist und der haeufigste Fall: der Nutzer sieht hin.
        pfade = self._begrenzt(extra_pfade)
        for p in pfade:
            jetzt_m = _mtime(p)
            vorher = self.extra.get(p, "__neu__")
            if vorher == "__neu__":
                # Erst jetzt im Blick - merken, aber nicht melden. Ein
                # Ordnerwechsel ist keine Aenderung am Dateisystem.
                self.extra[p] = jetzt_m
                continue
            if jetzt_m != vorher:
                self.extra[p] = jetzt_m
                name = os.path.basename(p.rstrip("/")) or p
                if self.gemeldet == ("ordner", name):
                    return None
                self.gemeldet = ("ordner", name)
                LOG("ROM-Waechter: Ordner %r hat sich geaendert" % name)
                return name

        # 2. Die Systeme.
        try:
            neu = self._signatur()
        except Exception:                                # noqa: BLE001
            return None
        if not neu or neu == self.stand:
            return None
        geaendert = sorted(
            sk for sk in set(neu) | set(self.stand)
            if neu.get(sk) != self.stand.get(sk))
        if not geaendert:
            return None
        marke = ("system", tuple(geaendert))
        if self.gemeldet == marke:
            return None
        self.gemeldet = marke
        # DER STAND WIRD HIER NICHT UEBERNOMMEN. Sonst waere die
        # Meldung nach dem ersten Mal weg, und wer sie verpasst hat,
        # saesse wieder vor einer Liste, die nicht stimmt - genau das
        # Problem, das Build 251 beim Speicher-Waechter behoben hat.
        # Uebernommen wird er erst beim naechsten merken(), also nach
        # dem Nachlesen.
        text = ", ".join(geaendert[:3])
        if len(geaendert) > 3:
            text += " +%d" % (len(geaendert) - 3)
        LOG("ROM-Waechter: geaendert: %s" % text)
        return text
