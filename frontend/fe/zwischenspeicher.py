#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kurzlebiger Zwischenspeicher fuer Einstellungen (Build 135).

WARUM ES DAS GIBT, mit Messung. Ein einzelner Scrollschritt im Raster
fasste die SD-Karte FUENFMAL an:

    open    /media/fat/frontend/retroachievements.cfg
    open    /media/fat/frontend/ansicht
    exists  /media/fat/frontend/profile
    exists  /media/fat/frontend/thumb_cache/hd
    exists  /media/fat/frontend/fast_scroll_enabled

Bei jedem Tastendruck. Fuer Werte, die sich nur aendern, wenn der
Nutzer im Menue etwas umstellt.

Auf einer Entwicklungsmaschine faellt das nicht auf - dort liegen die
Dateien im Dateisystem-Cache des Betriebssystems und ein Zugriff kostet
Mikrosekunden. Auf dem MiSTer ist es exFAT auf einer SD-Karte: ein
open() plus read() kostet dort typisch 1-5 ms, und deutlich mehr, wenn
die Karte gerade beschaeftigt ist - der Vorauslader liest Cover, der
Nachlader Miniaturen, die Musik einen Titel.

DAS IST DIE ERKLAERUNG FUER "MEISTENS FLUESSIG, MANCHMAL EIN HAENGER".
Nicht der Durchschnitt ist das Problem, sondern der Ausreisser: fuenf
Kartenzugriffe je Tastendruck, von denen jeder einzelne unvorhersehbar
lange dauern kann.

WIE ES GELOEST IST, und warum genau so:

  - EINE Zeitspanne (GUELTIG_MS) statt "fuer immer merken". Die
    Einstellungsdateien duerfen jederzeit von aussen geaendert werden,
    etwa per SSH - das war schon immer so und soll so bleiben. Eine
    halbe Sekunde ist kurz genug, dass niemand es merkt, und lang
    genug, dass eine Scrollfolge mit dreissig Tastendruecken EINEN
    Zugriff macht statt dreissig.

  - Dazu ein ausdrueckliches vergessen(), das jeder Schreibvorgang
    aufruft. Ohne das wuerde eine Aenderung im Menue bis zu einer
    halben Sekunde brauchen, bis man sie sieht - und genau dort schaut
    man ja hin.

WAS HIER NICHT HINEINGEHOERT: alles, was sich ohne Zutun des Nutzers
aendern kann, und alles, was gross ist. Das hier ist fuer eine Handvoll
Schalter gedacht, nicht als allgemeiner Dateicache.

FUER TESTS, weil es beim Bauen genau einmal zugeschlagen hat: der
Pruefstand friert time.monotonic() ein (siehe NOW in tools/_harness.py).
Die Zeitspanne unten laeuft damit NIE ab. Wer in einem Test eine
Einstellungsdatei direkt anlegt oder loescht, statt die zugehoerige
toggle-Funktion zu benutzen, muss deshalb selbst vergessen() rufen -
tools/_harness.py bietet dafuer _zwischenspeicher_leeren() an und ruft
es bei jedem make_frontend() automatisch.

UND DER SCHLUESSEL ENTHAELT DEN PFAD, nicht nur einen Namen. Tests
biegen solche Konstanten um, und ein Wert, der unter dem alten Pfad
gemerkt wurde, waere danach schlicht falsch.
"""
import time

# Eine halbe Sekunde. Siehe die Begruendung im Kopf: kurz genug, dass
# eine Aenderung von aussen praktisch sofort ankommt, lang genug, dass
# eine ganze Scrollfolge mit einem Zugriff auskommt.
GUELTIG_MS = 0.5

_werte = {}


def hole(schluessel, lesen, gueltig=None):
    """Den Wert zu "schluessel" liefern - aus dem Zwischenspeicher, oder
    frisch ueber lesen().

    "lesen" wird nur aufgerufen, wenn wirklich nachgesehen werden muss.
    Wirft es eine Ausnahme, wird NICHTS gemerkt und die Ausnahme geht
    weiter nach oben - ein Lesefehler soll sich nicht eine halbe Sekunde
    lang festsetzen."""
    jetzt = time.monotonic()
    eintrag = _werte.get(schluessel)
    if eintrag is not None:
        gesetzt, wert = eintrag
        if jetzt - gesetzt < (GUELTIG_MS if gueltig is None else gueltig):
            return wert
    wert = lesen()
    _werte[schluessel] = (jetzt, wert)
    return wert


def vergessen(schluessel=None):
    """Einen Eintrag oder alles verwerfen - von jedem Schreibvorgang
    aufzurufen, damit eine Aenderung im Menue sofort sichtbar wird.

    Ohne Angabe wird alles verworfen. Das ist Absicht: ein Schalter
    haengt oft an mehreren Werten (das Umstellen der Ansicht aendert
    auch, welche Kastengroesse gilt), und ein vergessener Einzeleintrag
    waere ein Fehler, den niemand findet. Der Preis ist ein paar
    ueberfluessige Lesevorgaenge nach einer Menueaktion - dort wartet
    ohnehin niemand auf Millisekunden."""
    if schluessel is None:
        _werte.clear()
    else:
        _werte.pop(schluessel, None)


def stand():
    """Wieviele Eintraege liegen gerade drin - nur fuer Tests und
    Diagnose."""
    return len(_werte)
