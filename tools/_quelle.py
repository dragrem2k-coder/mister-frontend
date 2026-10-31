#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Quelltext lesen, aber richtig (Build 298).

Viele Tests in diesem Verzeichnis pruefen nicht nur Verhalten, sondern
auch, dass eine bestimmte Zeile im Quelltext steht. Dabei sind in
diesem Projekt FUENF Fehler derselben Sorte passiert:

  * test_anleitung, test_konsole_wache, test_startweg (291),
    test_bildarten (294): der gesuchte Begriff stand auch im KOMMENTAR
    daneben - die Pruefung war aus dem falschen Grund gruen.
  * test_bildarten (294) und test_rom_auto (296) streiften danach die
    Kommentarzeilen ab, die DOCSTRINGS aber nicht. Derselbe Fehler, nur
    eine Etage hoeher: in diesem Projekt steht die Begruendung meist im
    Docstring und nicht in #-Zeilen.
  * test_cover_basis (298), erste Fassung: suchte das Schlusszeichen
    eines Docstrings am ZEILENANFANG. Hier steht es fast immer hinter
    dem letzten Satz, also blieb die Funktion bis zum Dateiende im
    Docstring und gab LEEREN Code zurueck - sechs Pruefungen waren aus
    dem falschen Grund ROT.

Die Lehre ist nicht "besser aufpassen", sondern EINE Fassung statt
fuenf nachgebauten. Dasselbe Argument steht im Projekt schon
ausgeschrieben, im Docstring von cover_datei() in fe/art.py: "Eine
zweite, nachgebaute Suche GEHT IRGENDWANN IMMER AUSEINANDER."

WARUM EIN EIGENES MODUL UND NICHT _harness.py: das Geruest laedt beim
Import das ganze Frontend, faelscht den Framebuffer und friert die Uhr
ein. Tests, die nur Quelltext lesen (test_bildarten zum Beispiel),
brauchen davon nichts und sollen es auch nicht bekommen - ein Test, der
mehr aufbaut als er braucht, scheitert irgendwann an etwas, das mit
seiner Frage nichts zu tun hat. _harness.py reicht diese beiden
Funktionen weiter, damit die Tests, die das Geruest ohnehin laden, sie
dort finden.

Beide Funktionen fragen ast, statt nach Textmerkmalen zu suchen - ein
Parser beantwortet genau die Frage, um die es geht.
"""
import ast
import textwrap


def koerper(quelle, name, klasse=None):
    """Der Quelltext genau EINER Funktion oder Methode.

    NICHT ueber ein Zeichenfenster wie [:1800] - das trifft irgendwann
    die naechste Funktion mit, und dann prueft der Test etwas anderes,
    als er behauptet.

    Mit "klasse" wird nur innerhalb dieser Klasse gesucht. Ohne sie
    gewinnt bei mehreren gleichnamigen Methoden die erste gefundene -
    wer es genauer braucht, nennt die Klasse.

    Liefert "" wenn es den Namen nicht gibt. Eine Pruefung auf einem
    leeren Text schlaegt an, und das ist richtig: eine Funktion, die
    nicht mehr existiert, ist ein Befund und kein Grund zum
    Durchwinken."""
    try:
        baum = ast.parse(quelle)
    except SyntaxError:
        return ""
    zeilen = quelle.splitlines()
    wurzel = baum
    if klasse is not None:
        for knoten in ast.walk(baum):
            if isinstance(knoten, ast.ClassDef) and knoten.name == klasse:
                wurzel = knoten
                break
        else:
            return ""
    for knoten in ast.walk(wurzel):
        if isinstance(knoten, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                and knoten.name == name:
            return "\n".join(zeilen[knoten.lineno - 1:knoten.end_lineno])
    return ""


def nur_code(quelle):
    """Dieselbe Quelle ohne Kommentarzeilen UND ohne Docstrings.

    Die #-Zeilen fallen nach Textmerkmal weg (da gibt es keine
    Zweifel), die Docstrings nach ast - gefragt wird also nicht "sieht
    diese Zeile wie ein Docstring aus", sondern "ist sie einer".

    Laesst sich die Quelle nicht parsen (etwa ein eingerueckter
    Ausschnitt), wird sie ausgerueckt und noch einmal versucht; geht
    auch das nicht, fallen nur die Kommentarzeilen weg. Dann ist das
    Ergebnis unscharf, aber nie leer - lieber eine Pruefung, die zu
    viel sieht, als eine, die stillschweigend nichts mehr sieht."""
    text = quelle
    baum = None
    try:
        baum = ast.parse(text)
    except SyntaxError:
        text = textwrap.dedent(quelle)
        try:
            baum = ast.parse(text)
        except SyntaxError:
            baum = None
    doczeilen = set()
    if baum is not None:
        for knoten in ast.walk(baum):
            if not isinstance(knoten, (ast.Module, ast.ClassDef,
                                       ast.FunctionDef,
                                       ast.AsyncFunctionDef)):
                continue
            koerp = getattr(knoten, "body", None)
            if not koerp or not isinstance(koerp[0], ast.Expr):
                continue
            wert = koerp[0].value
            if isinstance(wert, ast.Constant) and isinstance(wert.value, str):
                doczeilen.update(range(koerp[0].lineno,
                                       (koerp[0].end_lineno or
                                        koerp[0].lineno) + 1))
    raus = []
    for nr, zeile in enumerate(text.splitlines(), 1):
        if nr in doczeilen or zeile.lstrip().startswith("#"):
            continue
        raus.append(zeile.split("  #")[0])
    return "\n".join(raus)
