#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Was hat update_all geaendert? (Build 250)

Idee aus dem Vergleich mit Degauss: dort sieht man nach einem Update,
was neu ist. Bei uns konnte man update_all seit Build 213 aus dem Menue
starten, und danach stand da - nichts. Das Skript schreibt Hunderte
Zeilen auf die Konsole, und wer nicht mitgelesen hat, weiss hinterher
nicht, ob ueberhaupt etwas passiert ist.

WARUM NICHT DAS PROTOKOLL VON update_all GELESEN WIRD, und das ist die
Entscheidung, um die es hier geht. Ein Logleser haengt am Format einer
fremden Datei: eine geaenderte Zeile bei update_all, und wir zeigen
Unsinn oder nichts. Dasselbe Argument, mit dem fe/cores.py die
Datenbanken des MiSTer-Downloaders nicht nachbaut, und mit dem
fe/mister_system.py eine "Updates verfuegbar"-Abfrage ueber das Netz
ausdruecklich ablehnt:

    "dafuer muesste das Frontend die Datenbanken des MiSTer-Downloaders
    selbst auswerten und ihre Versionslogik nachbauen - genau die
    zweite Quelle der Wahrheit, die fe/cores.py ausschliesst."

VERGLICHEN WIRD DESHALB DIE KARTE MIT SICH SELBST. Vor dem Start von
update_all wird aufgeschrieben, welche .rbf-Dateien in den
Core-Ordnern liegen; danach wird nachgesehen. Was dabei herauskommt,
ist keine Behauptung ueber Versionen, sondern eine Beobachtung an
unserem eigenen Dateisystem - und die ist richtig, egal was update_all
intern tut oder in welcher Fassung es vorliegt.

DAS DATUM STECKT IM NAMEN, und darauf beruht die Unterscheidung
zwischen "neu" und "aktualisiert". MiSTer legt Cores als
"SNES_20260603.rbf" ab; fe/cores.py nutzt das schon, um die neueste
Fassung zu finden ("alphabetisch absteigend ist damit auch
chronologisch absteigend"). Hier wird derselbe Teil benutzt: alles vor
dem "_<Ziffern>" ist der Core, der Rest seine Fassung.

  * Der Kopf war vorher nicht da        -> NEU
  * Der Kopf war da, die Fassung anders -> AKTUALISIERT
  * Der Kopf ist jetzt gar nicht mehr da -> WEG

Der dritte Fall ist nicht theoretisch: update_all raeumt alte Cores
weg ("Removing /media/fat/_Console/SNES_20260603.rbf" - so stand es im
Log des Nutzers, dutzendfach). Ein verschwundener Core ist genau das,
was man wissen will, wenn ein Spiel danach nicht mehr startet.
"""
import io
import json
import os
import re
import time

import fe.cores as CORES

STAND_DATEI = "/media/fat/frontend/core_stand.json"
BERICHT_DATEI = "/media/fat/frontend/core_neu.json"

# Wie viele Posten ein Bericht hoechstens behaelt. Ein erster Lauf auf
# einer frischen Karte legt mehrere Hundert Cores an; die Liste soll
# lesbar bleiben und die Datei klein.
BERICHT_MAX = 200

_DATUM = re.compile(r"^(.*?)_(\d{4,}.*)$")


def kopf_und_fassung(name):
    """("SNES_20260603.rbf") -> ("SNES", "20260603").

    Ohne Datum im Namen ist der ganze Name der Kopf und die Fassung
    leer - dann gibt es fuer diesen Core nur "da" oder "nicht da", und
    das ist die ehrliche Auskunft.

    DIE PRAEFIX-FALLE AUS fe/cores.py GILT HIER GENAUSO: "SNES" und
    "SNES_Tracker" sind zwei verschiedene Cores. Deshalb muss nach dem
    Unterstrich eine ZIFFER kommen - "SNES_Tracker.rbf" hat damit den
    Kopf "SNES_Tracker" und nicht "SNES"."""
    roh = str(name or "")
    basis = roh[:-4] if roh.lower().endswith(".rbf") else roh
    m = _DATUM.match(basis)
    if m and m.group(1):
        return (m.group(1), m.group(2))
    return (basis, "")


def cores_jetzt(wurzel=None, ordner=None):
    """Die .rbf-Dateien in den Core-Ordnern, als sortierte Liste
    "_Console/SNES_20260603.rbf".

    Mit dem Ordner davor, nicht nur dem Dateinamen: dieselbe Datei in
    _Console und in _Arcade waere sonst dasselbe, und ein verschobener
    Core saehe wie "weg und neu" aus."""
    basis = wurzel or CORES.BASE
    raus = []
    for o in (ordner or CORES.CORE_ORDNER):
        pfad = os.path.join(basis, o)
        try:
            for n in os.listdir(pfad):
                if n.lower().endswith(".rbf"):
                    raus.append("%s/%s" % (o, n))
        except OSError:
            # Ein Ordner, den es nicht gibt, ist kein Fehler - nicht
            # jede Karte hat _Utility.
            continue
    return sorted(raus)


def stand_lesen(pfad=None):
    """(Zeitpunkt, Liste) des letzten aufgeschriebenen Stands, oder
    (None, None), wenn es keinen gibt.

    (None, None) und nicht (None, []): "nie nachgesehen" ist etwas
    anderes als "damals lag dort nichts". Wer das verwechselt, meldet
    beim ersten Lauf jeden einzelnen Core als neu."""
    p = pfad or STAND_DATEI
    try:
        if not os.path.exists(p):
            return (None, None)
        with io.open(p, "r", encoding="utf-8") as fh:
            daten = json.load(fh)
        if not isinstance(daten, dict):
            return (None, None)
        liste = daten.get("cores")
        if not isinstance(liste, list):
            return (None, None)
        zeit = daten.get("zeit")
        return (zeit if isinstance(zeit, (int, float)) else None,
                sorted(str(x) for x in liste if isinstance(x, str)))
    except Exception:                                    # noqa: BLE001
        return (None, None)


def stand_schreiben(liste, pfad=None, zeit=None):
    """Ueber .tmp und os.replace() - gleicher Weg wie fe/cores.py."""
    p = pfad or STAND_DATEI
    try:
        ordner = os.path.dirname(p)
        if ordner:
            os.makedirs(ordner, exist_ok=True)
        tmp = p + ".tmp"
        with io.open(tmp, "w", encoding="utf-8") as fh:
            json.dump({"zeit": float(zeit if zeit is not None
                                     else time.time()),
                       "cores": sorted(liste)}, fh, ensure_ascii=False)
        os.replace(tmp, p)
        return True
    except Exception:                                    # noqa: BLE001
        return False


def vergleich(vorher, jetzt):
    """{"neu": [...], "aktualisiert": [(Kopf, alt, neu)], "weg": [...]}

    `vorher` darf None sein (noch nie nachgesehen) - dann ist alles
    leer, und zwar ausdruecklich: beim ersten Mal ist nichts "neu",
    sondern einfach noch nichts bekannt."""
    if vorher is None:
        return {"neu": [], "aktualisiert": [], "weg": []}

    def _kopfe(liste):
        raus = {}
        for e in liste:
            ordner, _, name = e.rpartition("/")
            kopf, fassung = kopf_und_fassung(name)
            raus.setdefault("%s/%s" % (ordner, kopf), []).append(fassung)
        for k in raus:
            raus[k].sort()
        return raus

    a, b = _kopfe(vorher), _kopfe(jetzt)
    neu = sorted(k for k in b if k not in a)
    weg = sorted(k for k in a if k not in b)
    aktualisiert = []
    for k in sorted(set(a) & set(b)):
        if a[k] != b[k]:
            aktualisiert.append((k, ", ".join(x for x in a[k] if x),
                                 ", ".join(x for x in b[k] if x)))
    return {"neu": neu[:BERICHT_MAX],
            "aktualisiert": aktualisiert[:BERICHT_MAX],
            "weg": weg[:BERICHT_MAX]}


def leer(bericht):
    """Ob ein Bericht gar nichts zu sagen hat."""
    if not bericht:
        return True
    return not (bericht.get("neu") or bericht.get("aktualisiert")
                or bericht.get("weg"))


def anzahl(bericht):
    if not bericht:
        return 0
    return (len(bericht.get("neu") or ())
            + len(bericht.get("aktualisiert") or ())
            + len(bericht.get("weg") or ()))


def bericht_schreiben(bericht, pfad=None, zeit=None):
    p = pfad or BERICHT_DATEI
    try:
        ordner = os.path.dirname(p)
        if ordner:
            os.makedirs(ordner, exist_ok=True)
        daten = dict(bericht or {})
        daten["zeit"] = float(zeit if zeit is not None else time.time())
        tmp = p + ".tmp"
        with io.open(tmp, "w", encoding="utf-8") as fh:
            json.dump(daten, fh, ensure_ascii=False)
        os.replace(tmp, p)
        return True
    except Exception:                                    # noqa: BLE001
        return False


def bericht_lesen(pfad=None):
    """Der letzte Bericht, oder None.

    Die Tripel der aktualisierten Cores sind in JSON Listen - sie
    werden zurueckgewandelt, sonst muesste jeder Leser das selbst tun
    (und einer wuerde es vergessen). Genau dieser Fehler steckt in
    gemerkte_laden() als Kommentar: "Jahres-Spannen sind in JSON
    Listen, keine Tupel - zurueckwandeln, sonst schlaegt der Vergleich
    fehl und niemand sieht, warum.\""""
    p = pfad or BERICHT_DATEI
    try:
        if not os.path.exists(p):
            return None
        with io.open(p, "r", encoding="utf-8") as fh:
            daten = json.load(fh)
        if not isinstance(daten, dict):
            return None
        raus = {"zeit": daten.get("zeit")}
        for schl in ("neu", "weg"):
            w = daten.get(schl)
            raus[schl] = [str(x) for x in w if isinstance(x, str)] \
                if isinstance(w, list) else []
        w = daten.get("aktualisiert")
        raus["aktualisiert"] = [
            (str(x[0]), str(x[1]), str(x[2]))
            for x in w
            if isinstance(x, (list, tuple)) and len(x) == 3] \
            if isinstance(w, list) else []
        # EIN LEERER BERICHT IST KEIN BERICHT, und das ist mehr als
        # Ordnungsliebe: der Menuepunkt erscheint nur, wenn es einen
        # gibt. Kaeme hier ein Dict mit drei leeren Listen zurueck,
        # stuende im Systemmenue "was ist neu (0)" - ein Punkt, der
        # sagt, dass er nichts zu sagen hat.
        if leer(raus):
            return None
        return raus
    except Exception:                                    # noqa: BLE001
        return None


def nachsehen(wurzel=None, stand_pfad=None, bericht_pfad=None):
    """Nachsehen, was sich seit dem letzten Stand geaendert hat, den
    Bericht ablegen und den neuen Stand aufschreiben.

    Liefert den Bericht. Beim ersten Mal ist er leer - dann wird nur
    der Stand aufgeschrieben, damit es beim naechsten Mal etwas zu
    vergleichen gibt."""
    jetzt = cores_jetzt(wurzel)
    _zeit, vorher = stand_lesen(stand_pfad)
    bericht = vergleich(vorher, jetzt)
    stand_schreiben(jetzt, stand_pfad)
    if not leer(bericht):
        bericht_schreiben(bericht, bericht_pfad)
    return bericht
