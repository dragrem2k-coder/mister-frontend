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

def _normalize_for_search(s):
    """Kleinschreibung + Akzente entfernt, fuer eine tolerante Suche
    (z.B. 'zelda' findet auch 'Zelda' unabhaengig von Gross-/
    Kleinschreibung; 'pokemon' findet auch 'Pokémon')."""
    nfkd = unicodedata.normalize("NFKD", s)
    stripped = "".join(c for c in nfkd if not unicodedata.combining(c))
    return stripped.lower()

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

