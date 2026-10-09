#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Die Hauptseite selbst bestimmen - Reihenfolge und Sichtbarkeit der
Kategorien (Build 250).

NUTZERWUNSCH, aus dem Vergleich mit Degauss: dort kann man die
Startseite einrichten. Bei uns stand die Reihenfolge der Kategorien
fest in build_categories(), an zehn verschiedenen insert()- und
append()-Stellen verteilt, und ausblenden ging gar nicht.

REINE RECHNEREI, KEIN ZEICHNEN. Dieses Modul kennt die Einstellung und
die Regel, nach der sie angewendet wird; der Bildschirm dazu steht in
frontend.py (hauptseite_bildschirm()). Dieselbe Trennung wie bei
fe/filter.py und fe/cores.py - und der Grund ist derselbe: eine Regel,
die man ohne Bildschirm pruefen kann, wird auch geprueft.

DREI DINGE, DIE HIER NICHT VERHANDELBAR SIND

  1. "System" bleibt IMMER sichtbar und IMMER zuletzt. Das ist der
     einzige Weg zu den Einstellungen - wer sie ausblenden koennte,
     koennte sich aus dem eigenen Frontend aussperren und muesste die
     Datei per SSH wieder loeschen. Eine Bildschirmtastatur hat am
     MiSTer nicht jeder.
  2. Eine unbekannte Kategorie bleibt sichtbar. Wer ein neues System
     dazustellt oder einen Filter merkt, soll es sehen und nicht
     suchen muessen. Sie landet am Ende (vor "System") und kann von
     dort verschoben werden.
  3. Eine kaputte oder halb geschriebene Datei darf den Start nicht
     umwerfen. Dann gilt eben die Vorgabe - genau wie bei den
     gemerkten Filtern.

WARUM DER SCHLUESSEL NICHT DER ANZEIGENAME IST, und das ist der Teil,
den man leicht falsch macht: die Namen der besonderen Kategorien sind
UEBERSETZT ("Favoriten" / "Favorites"), und mehrere tragen einen
Zaehler ("Sammlungen (37)"). Wer den Anzeigenamen speichert, verliert
die ganze Einstellung beim Sprachwechsel und noch einmal bei jedem
hinzugekommenen Spiel. Gespeichert wird deshalb ein Kuerzel, das aus
dem Uebersetzungsschluessel kommt - und fuer die Spiele-Systeme,
Core-Ordner und gemerkten Filter der Name OHNE Zaehler, denn der ist
dort nicht uebersetzt.
"""
import io
import json
import os

import fe.translations as TR

DATEI = "/media/fat/frontend/hauptseite.json"

# Das Kuerzel der System-Kategorie. Sie wird ueber ihren nicht
# uebersetzten Namen gefunden - dieselbe Entscheidung und derselbe
# Grund wie in _refresh_system_category() (syskey=None ist nicht
# eindeutig).
SYSTEM = "system"

# Die Kategorien, deren Name aus einem Uebersetzungsschluessel
# entsteht. Ihr Kuerzel IST dieser Schluessel - damit ist es von der
# Sprache unabhaengig.
BESONDERE = ("continue_cat", "recent_cat", "favorites_cat",
             "collections_cat", "ra_hunter_cat", "wot_title")

_NAMENSMAP = None


def ohne_zaehler(name):
    """"Sammlungen (37)" -> "Sammlungen".

    Nur ein Zaehler am Ende wird abgeschnitten, nichts anderes: ein
    Systemname wie "Game Boy (Color)" darf nicht zu "Game Boy"
    werden. Deshalb die Ziffernpruefung."""
    roh = str(name or "")
    if roh.endswith(")") and " (" in roh:
        kopf, zahl = roh.rsplit(" (", 1)
        if zahl[:-1].isdigit():
            return kopf
    return roh


def _namensmap():
    """Anzeigename -> Kuerzel, ueber ALLE Sprachen.

    Ueber alle, nicht nur die aktuelle: wer auf Englisch umstellt, soll
    seine Reihenfolge behalten. Einmal gebaut und gemerkt - die
    Uebersetzungstabelle aendert sich im Lauf nicht."""
    global _NAMENSMAP
    if _NAMENSMAP is None:
        raus = {}
        for schl in BESONDERE:
            for _sprache, text in (TR.TRANSLATIONS.get(schl) or {}).items():
                if isinstance(text, str) and text:
                    raus[text] = schl
        _NAMENSMAP = raus
    return _NAMENSMAP


def schluessel(name, syskey=None, gemerkte=()):
    """Das stabile Kuerzel einer Kategorie.

    `gemerkte` sind die Namen der gemerkten Filter. Sie bekommen ein
    eigenes Kuerzel, und zwar aus einem konkreten Grund: ein gemerkter
    Filter traegt den syskey seiner Quellkategorie (siehe
    _syskey_fuer_kat() in frontend.py), ein Filter ueber SNES also
    "SNES" - genau wie das System SNES selbst. Ohne diese
    Unterscheidung waeren beide dasselbe, und wer den Filter
    ausblendet, verlore das System mit."""
    roh = ohne_zaehler(name)
    if roh == "System":
        return SYSTEM
    if roh in gemerkte:
        return "filter:" + roh
    besonders = _namensmap().get(roh)
    if besonders:
        return besonders
    if syskey:
        return "sys:" + str(syskey)
    return "name:" + roh


def laden(pfad=None):
    """(ausgeblendete Kuerzel als Menge, Reihenfolge als Liste).

    Eine kaputte Datei liefert (leere Menge, leere Liste) - dann gilt
    die Vorgabe, und niemand sitzt vor einem leeren Hauptmenue."""
    p = pfad or DATEI
    try:
        if not os.path.exists(p):
            return (set(), [])
        with io.open(p, "r", encoding="utf-8") as fh:
            daten = json.load(fh)
        if not isinstance(daten, dict):
            return (set(), [])
        aus = daten.get("aus")
        folge = daten.get("reihenfolge")
        aus = set(x for x in aus if isinstance(x, str)) \
            if isinstance(aus, list) else set()
        folge = [x for x in folge if isinstance(x, str)] \
            if isinstance(folge, list) else []
        # SICHERHEITSNETZ, und es ist das wichtigste dieser Datei: auch
        # eine von Hand verstellte Datei darf "System" nicht
        # ausblenden.
        aus.discard(SYSTEM)
        return (aus, folge)
    except Exception:                                    # noqa: BLE001
        return (set(), [])


def speichern(aus, reihenfolge, pfad=None):
    """Ueber eine .tmp-Datei und os.replace() - ein abgebrochener
    Schreibvorgang darf keine halbe Datei hinterlassen. Gleicher Weg
    wie fe/filter.py und fe/cores.py."""
    p = pfad or DATEI
    try:
        _aus = sorted(set(x for x in aus if isinstance(x, str)))
        if SYSTEM in _aus:
            _aus.remove(SYSTEM)
        daten = {"aus": _aus,
                 "reihenfolge": [x for x in reihenfolge
                                 if isinstance(x, str)]}
        ordner = os.path.dirname(p)
        if ordner:
            os.makedirs(ordner, exist_ok=True)
        tmp = p + ".tmp"
        with io.open(tmp, "w", encoding="utf-8") as fh:
            json.dump(daten, fh, ensure_ascii=False)
        os.replace(tmp, p)
        return True
    except Exception:                                    # noqa: BLE001
        return False


def anwenden(cats, gemerkte=(), aus=None, reihenfolge=None, pfad=None):
    """Die Einstellung auf eine Kategorienliste anwenden.

    `cats` ist die Liste der Tupel (Anzeigename, Knoten, syskey), wie
    build_categories() sie baut. Zurueck kommt eine NEUE Liste; die
    Tupel selbst werden nicht angefasst.

    Angewendet wird am Ende und an einer Stelle - nicht in den zehn
    insert()/append()-Stellen einzeln. Das war die Entscheidung, die
    diese Aenderung klein gehalten hat: die feste Grundreihenfolge
    bleibt, wie sie war, und wird danach umsortiert.

    DIE SORTIERUNG IST STABIL, und das ist nicht nur Ordnungsliebe:
    unbekannte Kategorien behalten dadurch ihre Reihenfolge
    untereinander, statt in einer willkuerlichen zu landen."""
    if aus is None or reihenfolge is None:
        _aus, _folge = laden(pfad)
        aus = _aus if aus is None else aus
        reihenfolge = _folge if reihenfolge is None else reihenfolge
    if not aus and not reihenfolge:
        return list(cats)

    platz = {k: i for i, k in enumerate(reihenfolge)}
    hinten = len(platz)
    behalten = []
    system = []
    for i, eintrag in enumerate(cats):
        name, _knoten, sk = eintrag[0], eintrag[1], eintrag[2]
        k = schluessel(name, sk, gemerkte)
        if k == SYSTEM:
            system.append(eintrag)
            continue
        if k in aus:
            continue
        behalten.append((platz.get(k, hinten + i), i, eintrag))
    behalten.sort(key=lambda z: (z[0], z[1]))
    return [z[2] for z in behalten] + system


def reihenfolge_aus(cats, gemerkte=()):
    """Die Kuerzel einer Kategorienliste, in ihrer jetzigen Reihenfolge
    und ohne "System".

    Das ist, was der Editor speichert: nicht die Namen, nicht die
    Indizes, sondern die Kuerzel in der Reihenfolge, die man gerade
    sieht."""
    raus = []
    for eintrag in cats:
        k = schluessel(eintrag[0], eintrag[2], gemerkte)
        if k != SYSTEM and k not in raus:
            raus.append(k)
    return raus
