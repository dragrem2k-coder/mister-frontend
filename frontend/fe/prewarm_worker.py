#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Arbeitsprozess fuer den Cover-Vorauslader (Build 102).

WARUM EIN EIGENER PROZESS UND KEIN THREAD MEHR
==============================================

Seit Build 73 rechnet der Vorauslader die Miniaturen in einem
Hintergrund-THREAD vor. Der Kopf von fe/prewarm.py nannte dabei von
Anfang an die Einschraenkung, die das erkauft:

    "Die MiSTer-CPU ist schwach, und das Skalieren ist reines Python.
     Ein Hintergrund-Thread nimmt dem Zeichnen also tatsaechlich
     Rechenzeit weg (Pythons GIL laesst immer nur einen Thread
     rechnen). [...] Er kann eine bereits begonnene Miniatur nicht
     mittendrin abbrechen - schlimmstenfalls teilt er sich also noch
     fuer die Dauer EINER Berechnung die CPU mit dem Zeichnen."

Genau diese eine Berechnung ist das Problem, und zwar fast nur auf
HDMI. Ein Cover fuer 1080p hat rund neunmal so viele Bildpunkte wie
eines fuer 240p - gemessen auf dem Geraet des Nutzers kostete eine
einzelne Erstberechnung 200-500 ms, ein Kategorie-Logo sogar 722 ms
("PERF cover: 722 ms (CONTINUE.art)"). Wer in genau diesem Moment eine
Taste drueckt, wartet, bis sie fertig ist. Nutzer-Rueckmeldung dazu:
"das Scrollen ist mir auf HDMI zu langsam, vor allem wenn Zeilen nach
unten neu ins Bild kommen, auch wenn ich zwischen den Ordnern hin und
her wechsle" - also exakt in den beiden Situationen, in denen reihen-
weise noch nicht berechnete Cover anstehen.

DER AUSWEG: der DE10-Nano hat ZWEI CPU-Kerne. Pythons GIL gilt aber nur
innerhalb EINES Prozesses. Als eigener Prozess rechnet der Vorauslader
auf dem zweiten Kern, der bisher brachlag - und nimmt dem Zeichnen
keine einzige Rechenoperation mehr weg. Eine begonnene Miniatur darf
dann sogar ruhig zu Ende laufen; sie stoert niemanden mehr.

WARUM DAS HIER SO WENIG MACHT WIE MOEGLICH
==========================================

Dieser Prozess liest Zeilen von der Standardeingabe, rechnet, schreibt
eine Datei und meldet ein Zeichen zurueck. Er haelt KEINEN Zustand, den
das Frontend kennen muesste, und fasst dessen Speicher-Caches nicht an
(kann er auch gar nicht - er hat seinen eigenen Adressraum). Damit
faellt die ganze Sorgfalt weg, die beim Thread noetig war.

Das Protokoll ist bewusst eine Zeile je Auftrag:

    <cache-ordner>\\t<breite>\\t<hoehe>\\t<pfad>\\n

Der Cache-Ordner steht MIT drin, statt einmal ausgehandelt zu werden.
Das Frontend schaltet ihn zur Laufzeit um (HD/SD, siehe
thumb_cache_modus_setzen() in fe/art.py, Build 85). Haette dieser
Prozess seine eigene Vorstellung davon, schriebe er nach einem Wechsel
stillschweigend in den falschen Ordner - die Miniaturen waeren
berechnet, und der Zeichenpfad faende sie trotzdem nie. Selbstbe-
schreibende Auftraege koennen gar nicht auseinanderlaufen.

Antwort je Auftrag, genau ein Zeichen plus Zeilenumbruch:
    f = fertig (neu berechnet)   t = Treffer (lag schon da)
    u = uebersprungen            e = Fehler

Der Aufrufer wartet jede Antwort ab, bevor er den naechsten Auftrag
schickt. Nicht aus Hoeflichkeit: nur so bleibt "Abbrechen" wirksam.
Schoebe er zehn Auftraege auf einmal in die Leitung, liessen die sich
nicht mehr zurueckholen.

Eigenstaendig startbar (fuer Tests):
    echo -e "/tmp/c\\t100\\t100\\t/pfad/bild.art" | python3 fe/prewarm_worker.py
"""
import os
import sys


def main():
    # Der eigene Ordner ist fe/, eine Ebene darueber liegt frontend/ -
    # von dort aus ist "fe.art" importierbar, genau wie im Frontend
    # selbst. Bewusst ueber __file__ statt ueber das Arbeitsverzeichnis:
    # der Prozess wird vom laufenden Frontend gestartet, und dessen
    # Arbeitsverzeichnis ist nicht garantiert.
    hier = os.path.dirname(os.path.abspath(__file__))
    wurzel = os.path.dirname(hier)
    if wurzel not in sys.path:
        sys.path.insert(0, wurzel)

    try:
        import fe.art as art
    except Exception:                                    # noqa: BLE001
        # Ohne fe.art kann dieser Prozess nichts ausrichten. Stumm
        # beenden statt eine Fehlermeldung in die Leitung zu schreiben:
        # der Aufrufer erkennt am geschlossenen Rohr, dass er wieder auf
        # den Thread zurueckfallen muss, und das Frontend laeuft normal
        # weiter - es geht hier nur um Vorratshaltung.
        return 1

    aus = sys.stdout
    for zeile in sys.stdin:
        zeile = zeile.rstrip("\n")
        if not zeile:
            continue
        teile = zeile.split("\t", 3)
        if len(teile) != 4:
            aus.write("e\n")
            aus.flush()
            continue
        cachedir, bw, bh, pfad = teile
        try:
            bw = int(bw)
            bh = int(bh)
        except ValueError:
            aus.write("e\n")
            aus.flush()
            continue
        # Der Ordner kommt aus dem Auftrag, siehe Kopfkommentar.
        art.THUMB_CACHE_DIR = cachedir
        try:
            ergebnis = art.prewarm_thumb(pfad, bw, bh)
        except Exception:                                # noqa: BLE001
            # Ein Fehler hier darf den Prozess nie beenden - sonst
            # verliert das Frontend den Vorauslader wegen eines einzigen
            # kaputten Bildes fuer den Rest der Sitzung.
            ergebnis = "fehler"
        aus.write({"fertig": "f", "treffer": "t",
                   "uebersprungen": "u"}.get(ergebnis, "e") + "\n")
        aus.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
