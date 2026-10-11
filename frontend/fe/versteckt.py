#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ausgeblendete Eintraege (Build 256).

NUTZERWUNSCH, und einer, der schon lange auf der Liste stand: einzelne
Spiele, Ordner oder ganze Systeme aus der Anzeige nehmen, ohne auf der
Karte etwas zu loeschen. Degauss hat dafuer "Hide this" samt "Show what
you hid" - die Idee ist von dort, der Code nicht (Degauss steht unter
PolyForm Noncommercial, das ist keine freie Lizenz).

DREI ENTSCHEIDUNGEN, DIE DEN UNTERSCHIED MACHEN:

1. AUF DER KARTE WIRD NICHTS ANGEFASST. Ausblenden ist eine
   Anzeigesache, kein Loeschen. Diese Datei ist das einzige, was
   entsteht; wer sie wegwirft, hat alles wieder. Das ist dieselbe
   Linie wie ueberall sonst in diesem Projekt - wir schreiben nicht in
   fremde Ordner und loeschen keine ROMs.

2. GESCHLUESSELT NACH SYSTEM UND BESCHRIFTUNG, nicht nach Pfad. Der
   Pfad eines Spiels aendert sich, sobald jemand seine Ordner
   umsortiert, und dann waere die Ausblendung weg. Die Beschriftung
   ist genau das, was der Nutzer gesehen und ausgeblendet hat - sie
   ist die ehrlichere Kennung. Ein System wird mit der leeren
   Beschriftung "" ausgeblendet: dieselbe Datei, eine Sonderzeile,
   keine zweite Liste.

3. GESCHRIEBEN WIRD ATOMAR (.tmp + os.replace). Bei einem Stromausfall
   mitten im Schreiben waere die Alternative eine halbe JSON-Datei -
   und die faengt load() zwar ab, aber dann waeren ALLE Ausblendungen
   weg. Dasselbe Muster wie bei ra_spielnummern.json aus Build 254.

NICHT UMGESETZT, bewusst: Platzhalterzeilen ("3 Eintraege
ausgeblendet") in der Liste. Wer etwas ausblendet, will es nicht
sehen; eine Zeile, die sagt "hier ist etwas, das du nicht sehen
willst", ist genau die Zeile zuviel. Die Uebersicht steht stattdessen
im Systemmenue, wo man sie sucht, wenn man sie braucht.
"""
import json
import os

from fe.zwischenspeicher import hole as _hole, vergessen as _vergessen

VERSTECKT_FILE = "/media/fat/frontend/versteckt.json"

# Nach oben begrenzt, damit eine kaputte oder von Hand aufgeblaehte
# Datei nicht bei jedem Listenaufbau Megabyte durchsucht. 20.000 ist
# weit mehr, als ein Mensch je von Hand ausblendet, und immer noch
# eine Datei von unter einem Megabyte.
MAX_EINTRAEGE = 20000


def _lesen(pfad=None):
    try:
        with open(pfad or VERSTECKT_FILE) as f:
            roh = json.load(f)
    except (OSError, ValueError):
        return {}
    if not isinstance(roh, dict):
        return {}
    raus = {}
    gesamt = 0
    for syskey, namen in roh.items():
        if not isinstance(syskey, str) or not isinstance(namen, list):
            continue
        menge = set()
        for n in namen:
            if isinstance(n, str):
                menge.add(n)
                gesamt += 1
                if gesamt >= MAX_EINTRAEGE:
                    break
        if menge:
            raus[syskey] = menge
        if gesamt >= MAX_EINTRAEGE:
            break
    return raus


def laden(pfad=None):
    """{syskey: set(beschriftung, ...)} - "" steht fuer das System
    selbst. Ueber denselben kurzlebigen Zwischenspeicher wie die
    uebrigen Einstellungen: die Abfrage liegt im Zeichenweg."""
    if pfad is not None:
        return _lesen(pfad)
    return _hole(("versteckt", VERSTECKT_FILE), _lesen)


def speichern(daten, pfad=None):
    ziel = pfad or VERSTECKT_FILE
    try:
        d = os.path.dirname(ziel)
        if d:
            os.makedirs(d, exist_ok=True)
        tmp = ziel + ".tmp"
        with open(tmp, "w") as f:
            json.dump({k: sorted(v) for k, v in sorted(daten.items()) if v},
                      f, ensure_ascii=False)
        os.replace(tmp, ziel)
    except OSError:
        pass
    if pfad is None:
        _vergessen("versteckt")


def leer():
    """Ist ueberhaupt nichts ausgeblendet? Eigene Frage, weil sie im
    Zeichenweg steht: solange niemand etwas ausgeblendet hat - und das
    ist der Normalfall - soll die Liste gar nicht erst angefasst
    werden."""
    return not laden()


def ist_versteckt(syskey, label, daten=None):
    """Ist dieser Eintrag ausgeblendet - oder sein ganzes System?"""
    d = laden() if daten is None else daten
    menge = d.get(syskey or "")
    if not menge:
        return False
    return label in menge


def system_versteckt(syskey, daten=None):
    d = laden() if daten is None else daten
    return "" in d.get(syskey or "", ())


def umschalten(syskey, label, pfad=None):
    """Einen Eintrag aus- oder wieder einblenden. Liefert True, wenn er
    jetzt versteckt ist."""
    daten = laden(pfad)
    schluessel = syskey or ""
    menge = set(daten.get(schluessel, ()))
    if label in menge:
        menge.discard(label)
    else:
        if sum(len(v) for v in daten.values()) >= MAX_EINTRAEGE:
            return False
        menge.add(label)
    if menge:
        daten[schluessel] = menge
    else:
        daten.pop(schluessel, None)
    speichern(daten, pfad)
    return label in menge


def liste(pfad=None):
    """Alles Ausgeblendete als [(syskey, label), ...], sortiert - fuer
    die Uebersicht im Systemmenue."""
    daten = laden(pfad)
    raus = []
    for syskey in sorted(daten):
        for label in sorted(daten[syskey]):
            raus.append((syskey, label))
    return raus


def anzahl(pfad=None):
    return sum(len(v) for v in laden(pfad).values())


def alles_zeigen(pfad=None):
    """Alle Ausblendungen aufheben. Liefert die Zahl der aufgehobenen."""
    n = anzahl(pfad)
    speichern({}, pfad)
    return n
