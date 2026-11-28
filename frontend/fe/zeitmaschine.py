#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Die Zeitmaschine (Build 351).

NUTZERWUNSCH: "das ultimative Feature" - ein Jahr waehlen, und Dragend
zeigt die Sammlung, wie sie damals war: die Spiele, die es bis dahin
gab, und was in genau diesem Jahr neu war. Ein- und ausschaltbar,
"Zurueck in die Gegenwart" als eigener Punkt und auf B. Und: "die
Performance, die wir jetzt haben, darf nicht darunter leiden".

DESHALB KOSTET SIE NICHTS, SOLANGE MAN SIE NICHT OEFFNET. Beim Start
steht nur eine Kategorie mit einem einzigen Eintrag da. Das
Jahresverzeichnis wird erst gebaut, wenn man zum ersten Mal reist -
aus den Spieldaten (get_meta), die das Frontend ohnehin hat - und dann
fuer die Sitzung gemerkt. Gebaut wird in Happen auf dem Hauptfaden;
dazwischen fragt der Aufrufer die Eingabe (B bricht ab) und zeichnet
den Fortschritt.

WAS HIER STEHT: der Schalter, das Verzeichnis, der Baumknoten fuer ein
Jahr. Gezeichnet wird in frontend.py.
"""
import os

ORDNER = "/media/fat/frontend"
AUS_FLAG = os.path.join(ORDNER, "zeitmaschine_aus")
FRUEHESTES = 1970
HAPPEN = 300                 # so viele Spiele zwischen zwei Blicken
ARCADE = "ARCADE"            # wie fe/wertungen.ARCADE


# ======================================================================
# SCHALTER (Vorgabe AN - sie kostet nichts, solange man nicht reist)
# ======================================================================
_aus = [None]


def an():
    if _aus[0] is None:
        _aus[0] = os.path.exists(AUS_FLAG)
    return not _aus[0]


def toggle_an():
    try:
        if an():
            os.makedirs(os.path.dirname(AUS_FLAG), exist_ok=True)
            open(AUS_FLAG, "w").close()
        elif os.path.exists(AUS_FLAG):
            os.remove(AUS_FLAG)
    except OSError:
        pass
    _aus[0] = None
    return an()


# ======================================================================
# DAS VERZEICHNIS
# ======================================================================
def jahr_zahl(roh, bis=None):
    """Das Jahr aus einem Metadatenwert - nur plausible."""
    from fe.filter import jahr_zahl as _jz
    j = _jz(roh)
    if not j or j < FRUEHESTES or (bis and j > bis):
        return 0
    return j


class Verzeichnis(object):
    """{jahr: [(syskey, label, kind, arg)]} plus die Zahl der Spiele
    ohne bekanntes Jahr."""

    def __init__(self):
        self.jahre = {}
        self.ohne = 0
        self.gesehen = set()

    def aufnehmen(self, syskey, label, kind, arg, jahr):
        schl = (syskey, label)
        if schl in self.gesehen:
            return
        self.gesehen.add(schl)
        if jahr:
            self.jahre.setdefault(jahr, []).append((syskey, label, kind, arg))
        else:
            self.ohne += 1

    def bereich(self):
        if not self.jahre:
            return None
        return min(self.jahre), max(self.jahre)

    def zaehlen(self, jahr):
        """(bis einschliesslich jahr, neu in jahr)."""
        bis = sum(len(v) for j, v in self.jahre.items() if j <= jahr)
        return bis, len(self.jahre.get(jahr, ()))

    def startjahr(self):
        """Das Jahr mit den meisten Neuerscheinungen der Sammlung."""
        if not self.jahre:
            return None
        return max(self.jahre, key=lambda j: (len(self.jahre[j]), -j))

    def jahr_von(self, syskey, label):
        for j, v in self.jahre.items():
            for e in v:
                if e[0] == syskey and e[1] == label:
                    return j
        return 0


def eintraege(cats):
    """Alle Spiele der System-Kategorien: (syskey, label, kind, arg) -
    durch die Unterordner. Nur Kategorien mit Systemschluessel; die
    abgeleiteten (Favoriten, Testarchiv ...) wuerden sie doppelt
    liefern."""
    for _name, knoten, syskey in cats:
        if not syskey or not isinstance(knoten, dict):
            continue
        stapel = [knoten]
        while stapel:
            k = stapel.pop()
            for unter in (k.get("folders") or {}).values():
                if isinstance(unter, dict):
                    stapel.append(unter)
            for e in k.get("items") or ():
                if len(e) >= 3 and e[1] in ("game", "core"):
                    yield syskey, e[0], e[1], e[2]


def _zaehlt(kind, arg, mra_fn):
    """Kommt der Eintrag ins Verzeichnis? Spiele immer, Cores nur als
    .mra (Arcade) - ein .rbf-Core hat kein Erscheinungsjahr."""
    if kind != "core":
        return True
    return bool(mra_fn) and isinstance(arg, str) \
        and arg.lower().endswith(".mra")


def anzahl(cats, mra_fn=None):
    """So viele Spiele liest bauen() - fuer die Fortschrittsanzeige."""
    gesehen = set()
    for syskey, label, kind, arg in eintraege(cats):
        if _zaehlt(kind, arg, mra_fn):
            gesehen.add((syskey, label))
    return len(gesehen)


def bauen(cats, meta_fn, mra_fn=None, bis=None, zwischendurch=None):
    """Das Verzeichnis bauen. meta_fn(syskey, label) -> dict,
    mra_fn(pfad) -> dict (Arcade). zwischendurch(anzahl) alle HAPPEN
    Spiele; liefert es False, wird abgebrochen (Rueckgabe None)."""
    vz = Verzeichnis()
    n = 0
    for syskey, label, kind, arg in eintraege(cats):
        if (syskey, label) in vz.gesehen:
            continue             # schon da - die Spieldaten nicht nochmal
        if not _zaehlt(kind, arg, mra_fn):
            continue
        if kind == "core":
            try:
                meta = mra_fn(arg) or {}
            except Exception:                            # noqa: BLE001
                meta = {}
        else:
            try:
                meta = meta_fn(syskey, label) or {}
            except Exception:                            # noqa: BLE001
                meta = {}
        vz.aufnehmen(syskey, label, kind, arg,
                     jahr_zahl(meta.get("year"), bis))
        n += 1
        if zwischendurch is not None and not n % HAPPEN:
            if zwischendurch(n) is False:
                return None
    return vz


def knoten(vz, jahr, systemname, texte, wertungen=None):
    """Der Baumknoten fuer ein Jahr:
      folders: "Neu in <jahr>" (alle Systeme, nach Name) und je System
               "<System>" mit allem bis zum Jahr, das Neueste zuerst;
               dazu "Deine Wertungen" (bewertete Spiele bis zum Jahr,
               bester zuerst), wenn es welche gibt.
      folge:   "Neu in <jahr>", "Deine Wertungen" vor den Systemen
      oben:    "Zurueck in die Gegenwart", "Anderes Jahr ..." - vor
               allen Ordnern (frontend._display_items)
    texte: dict mit 'neu' (Format mit %d), 'wertungen', 'zurueck',
    'anderes'. wertungen: {(syskey, label): spielspass} oder None."""
    ordner = {}
    folge = []
    neu = sorted(vz.jahre.get(jahr, ()), key=lambda e: e[1].lower())
    if neu:
        ordner[texte["neu"] % jahr] = {
            "folders": {}, "items": [(e[1], e[2], e[3]) for e in neu]}
        folge.append(texte["neu"] % jahr)
    je_system = {}
    for j, liste in vz.jahre.items():
        if j > jahr:
            continue
        for e in liste:
            je_system.setdefault(e[0], []).append((j, e))
    for sk, liste in je_system.items():
        liste.sort(key=lambda x: (-x[0], x[1][1].lower()))
        name = systemname(sk)
        if name in ordner:
            name = "%s (%s)" % (name, sk)
        ordner[name] = {"folders": {},
                        "items": [(e[1], e[2], e[3]) for _j, e in liste]}
    if wertungen:
        bewertet = []
        for liste in je_system.values():
            for _j, e in liste:
                # Arcade-Spiele (.mra) stehen in den Wertungen unter
                # ARCADE (fe/wertungen.ist_automat) - im Verzeichnis
                # sind nur .mra-Cores, also reicht hier die Art.
                sk = ARCADE if e[2] == "core" else e[0]
                w = wertungen.get((sk, e[1]))
                if w is not None:
                    bewertet.append((-w, e[1].lower(), e))
        if bewertet:
            bewertet.sort(key=lambda x: x[:2])
            ordner[texte["wertungen"]] = {
                "folders": {}, "items": [(e[1], e[2], e[3])
                                         for _w, _n, e in bewertet]}
            folge.append(texte["wertungen"])
    # Die Systeme danach - ihre Ordnung (nach Name) macht die Liste.
    # "oben" steht vor allen Ordnern: zurueck geht es immer mit einem
    # Druck, ohne durch zwanzig Systeme zu scrollen.
    return {"folders": ordner, "folge": folge,
            "oben": [(texte["zurueck"], "zeitmaschine_zurueck", None),
                     (texte["anderes"], "zeitmaschine", None)],
            "items": []}
