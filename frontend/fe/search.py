#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Direktsprung/Volltextsuche in Listen: einzelner Anfangsbuchstabe
(jump_to_letter, klassischer Dateibrowser-Stil) und echte Volltext-
suche irgendwo im Namen (jump_to_substring, Nutzerwunsch: "bei vielen
ROMs ist das besser"). Ausgelagert aus frontend.py (Modularisierung,
Git-Branch 'modular-refactor'). Komplett eigenstaendig, reine
String-Verarbeitung.
"""
import unicodedata

def _letter_of(name):
    for ch in name:
        if ch.isalnum():
            return ch.upper()
    return "#"

if hasattr("", "isascii"):
    def _nur_ascii(s):
        return s.isascii()
else:                                   # Python < 3.7
    def _nur_ascii(s):
        try:
            s.encode("ascii")
        except UnicodeEncodeError:
            return False
        return True


def _normalize_for_search(s):
    """Kleinschreibung + Akzente entfernt, fuer eine tolerante Suche
    (z.B. 'zelda' findet auch 'Zelda' unabhaengig von Gross-/
    Kleinschreibung; 'pokemon' findet auch 'Pokémon').

    ABKUERZUNG FUER REINES ASCII (Build 114): fuer einen Namen ohne
    Sonderzeichen ist unicodedata.normalize() die Identitaet, und es
    gibt keine kombinierenden Zeichen zu entfernen - uebrig bleibt
    genau .lower(). Das ist nachweislich dasselbe Ergebnis (siehe
    tools/test_suchtreffer.py, Test ueber alle 128 ASCII-Zeichen) und
    war noetig, weil die Trefferzaehlung die GANZE Liste normalisieren
    muss statt beim ersten Treffer aufzuhoeren: ueber 12.605 Namen
    gemessen 21,8 ms gegen 1,6 ms, auf der MiSTer-CPU also der
    Unterschied zwischen unbenutzbar und unauffaellig."""
    if _nur_ascii(s):
        return s.lower()
    nfkd = unicodedata.normalize("NFKD", s)
    stripped = "".join(c for c in nfkd if not unicodedata.combining(c))
    return stripped.lower()


def treffer_suchen(names, query):
    """ALLE Indizes, deren Name query enthaelt, in Listenreihenfolge.

    Braucht man, sobald die Suche mehr koennen soll als "irgendein
    Treffer": ohne die vollstaendige Liste laesst sich weder "naechster
    Treffer" bilden noch "3 / 17" anzeigen."""
    if not query:
        return []
    q = _normalize_for_search(query)
    return [i for i, nm in enumerate(names) if q in _normalize_for_search(nm)]


def treffer_ab(treffer, cur_i, einschliesslich=True):
    """Erster Treffer ab cur_i, zyklisch. -1, wenn es keinen gibt.

    einschliesslich=True bildet genau jump_to_substring() nach (die
    aktuelle Position zaehlt als Treffer, damit ein laenger werdender
    Suchbegriff nicht unnoetig weiterspringt); False ist der Schritt
    zum NAECHSTEN Treffer."""
    if not treffer:
        return -1
    for i in treffer:
        if i > cur_i or (einschliesslich and i == cur_i):
            return i
    return treffer[0]


def treffer_davor(treffer, cur_i):
    """Letzter Treffer VOR cur_i, zyklisch. -1, wenn es keinen gibt."""
    if not treffer:
        return -1
    for i in reversed(treffer):
        if i < cur_i:
            return i
    return treffer[-1]


def treffer_rang(treffer, cur_i):
    """Der wievielte Treffer cur_i ist (1-basiert), sonst 0."""
    try:
        return treffer.index(cur_i) + 1
    except ValueError:
        return 0

def jump_to_substring(names, cur_i, query):
    """Index des naechsten Eintrags (ab der AKTUELLEN Position gesucht,
    cur_i selbst eingeschlossen - anders als jump_to_letter(), da hier
    bei JEDEM Tastendruck neu gesucht wird, waehrend die Anfrage waechst,
    und der aktuell markierte Treffer bei einem laengeren, weiterhin
    passenden Suchbegriff nicht unnoetig verlassen werden soll), dessen
    Name query IRGENDWO enthaelt (nicht nur am Anfang) - Volltextsuche
    statt reinem Anfangsbuchstaben-Sprung (Nutzerwunsch: 'bei vielen
    ROMs ist das besser'). Liefert cur_i unveraendert zurueck, wenn
    nichts passt (der zuletzt gueltige Treffer bleibt so stehen, statt
    bei einem Tippfehler ins Leere zu springen)."""
    n = len(names)
    if n == 0 or not query:
        return cur_i
    q = _normalize_for_search(query)
    if q in _normalize_for_search(names[cur_i]):
        return cur_i
    for step in range(1, n):
        idx = (cur_i + step) % n
        if q in _normalize_for_search(names[idx]):
            return idx
    return cur_i

def jump_to_letter(names, cur_i, ch):
    """Index des naechsten Eintrags (zyklisch, ab cur_i+1 gesucht),
    dessen Anfangsbuchstabe ch entspricht. Mehrfaches Druecken derselben
    Taste springt dadurch der Reihe nach durch alle Treffer - wie die
    Direktsprung-Suche in klassischen Dateibrowsern."""
    n = len(names)
    if n == 0:
        return cur_i
    for step in range(1, n + 1):
        idx = (cur_i + step) % n
        if _letter_of(names[idx]) == ch:
            return idx
    return cur_i

