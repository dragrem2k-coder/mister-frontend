#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Aus welchen Systemen zieht der Zufalls-Zock? (Build 354)

NUTZERWUNSCH: "Zufalls-Zock sollte man sich noch aussuchen koennen, aus
welchen Kategorien man Spiele dort auswaehlt! Wenn jemand zum Beispiel
nur von SNES, Mega Drive, NES, Game Boy Spiele haben will, sollte man
das einstellen koennen - am besten unter System."

GESPEICHERT WIRD, WAS GEWAEHLT IST, nicht was abgewaehlt ist: wer "nur
SNES und Mega Drive" will, will auch nach dem naechsten Einlesen kein
neues System dazubekommen. Keine Datei heisst: alle - auch die, die
spaeter dazukommen. Genau das ist die Vorgabe.

Datei: /media/fat/frontend/zufallszock_systeme.json, {"nur": [syskeys]}.
Geschrieben ueber .tmp und os.replace(); eine kaputte Datei heisst
"alle", damit der Zufalls-Zock nie wegen einer Datei leer bleibt.

Nur der Zufalls-Zock filtert. Attract-Modus, Zufallsstart (F11) und die
Sammlungen ziehen weiter aus allem - gefragt war die eine Kategorie.
"""
import json
import os

DATEI = "/media/fat/frontend/zufallszock_systeme.json"
_merker = [False, None]          # (gelesen, Menge oder None = alle)


def vergessen():
    _merker[0] = False
    _merker[1] = None


def laden():
    """Die gewaehlten Systeme als Menge - oder None fuer alle."""
    if _merker[0]:
        return _merker[1]
    _merker[0] = True
    _merker[1] = None
    try:
        with open(DATEI, encoding="utf-8") as f:
            daten = json.load(f)
    except (OSError, ValueError):
        return None
    nur = daten.get("nur") if isinstance(daten, dict) else None
    if isinstance(nur, list):
        menge = set(str(k) for k in nur if isinstance(k, str) and k)
        if menge:
            _merker[1] = menge
    return _merker[1]


def speichern(nur):
    """nur: Menge der Systeme, oder None/leer fuer alle (Datei weg).
    True, wenn es geklappt hat."""
    try:
        if not nur:
            if os.path.exists(DATEI):
                os.remove(DATEI)
        else:
            os.makedirs(os.path.dirname(DATEI), exist_ok=True)
            tmp = DATEI + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"nur": sorted(nur)}, f, ensure_ascii=False)
            os.replace(tmp, DATEI)
    except OSError:
        vergessen()
        return False
    _merker[0] = True
    _merker[1] = set(nur) if nur else None
    return True


def filtern(pool, nur=None):
    """Den Pool (label, syskey, arg) auf die gewaehlten Systeme
    beschraenken. nur=None liest die Einstellung."""
    if nur is None:
        nur = laden()
    if not nur:
        return pool
    return [p for p in pool if p[1] in nur]


def systeme(pool):
    """{syskey: Anzahl Spiele} im Pool."""
    zaehler = {}
    for _label, syskey, _arg in pool:
        if syskey:
            zaehler[syskey] = zaehler.get(syskey, 0) + 1
    return zaehler
