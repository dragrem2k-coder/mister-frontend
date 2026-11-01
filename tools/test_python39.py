#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Laeuft das noch auf dem Python des Geraets? (Build 304)

WARUM ES DIESEN TEST GIBT. Aus dem Bericht des Nutzers vom 31.10.,
Build 303:

    ABSCHNITT K ABGEBROCHEN: TypeError:
    'staticmethod' object is not callable

Und weil der Wiederherstell-Zweig denselben Fehler machte, blieb die
Framebuffer-Instanz fuer den REST des Laufs kaputt: vier von sechs
Ansichten in Abschnitt L fielen mit aus, und Teil 4 - der Beweis, um
den es in Build 303 ging - meldete "nicht abfragbar".

DIE URSACHE IST NICHT DER CODE ALLEIN, SONDERN EIN UNTERSCHIED ZWISCHEN
ZWEI PYTHON-FASSUNGEN:

    Geraet des Nutzers   Python 3.9.6   (der Bench schreibt es in den Kopf)
    Entwicklungscontainer Python 3.13

Ab Python 3.10 ist ein staticmethod-Objekt AUFRUFBAR, davor nicht. Der
Fehler lief im Container also durch, und `tools/test_bench.py` hat ihn
nicht gefunden - obwohl der Test die richtige Pruefung enthaelt
("kein Abschnitt ist abgebrochen"). Er war gruen, weil die Maschine
unter ihm eine andere war.

> Ein Test ist nur so gut wie die Maschine, auf der er laeuft.

Das ist dieselbe Sorte Befund wie in Build 298 (zwei Helfer waren
"gruen aus dem falschen Grund"), nur eine Ebene tiefer: dort war die
Pruefung falsch gebaut, hier ist die UMGEBUNG eine andere.

WAS DIESER TEST SICHERT - zwei Tore, von denen das erste alles
erwischt, was Python selbst als Syntax erkennt:

  1. JEDE Datei unter frontend/ und tools/ wird mit
     ast.parse(feature_version=(3, 9)) gelesen. Damit lehnt Python
     selbst ab, was es in 3.9 nicht gab - match/case, except*, und
     was spaeter dazukommt. Keine Liste, die ich pflegen muss.
  2. Namentlich die Fallen, die KEINE Syntax sind und deshalb durch
     Tor 1 fallen: ein staticmethod-Objekt, das auf eine INSTANZ
     gesetzt wird (genau der Fehler aus Build 303), und eine kurze
     Liste von Funktionen, die es in 3.9 noch nicht gab.

WAS ER NICHT KANN: er ersetzt kein Python 3.9 im Container. Ein
Verhalten, das sich still aendert und keinen Namen hat, findet er
nicht. Deshalb steht im Bench weiterhin die Python-Fassung des
Geraets im Kopf - damit ein Bericht sagt, worauf er entstanden ist.

Ausfuehren:
    python3 tools/test_python39.py
"""
import ast
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# DIE FASSUNG DES GERAETS, an einer Stelle. Der Bench schreibt sie in
# jeden Bericht ("Python : 3.9.6"), also ist sie nicht geraten.
ZIEL = (3, 9)

fails = []


def check(name, ok, info=""):
    if ok:
        print("  OK   %s %s" % (name, info))
    else:
        print("  FEHL %s %s" % (name, info))
        fails.append(name)


print(__doc__.strip().split("\n")[0])
print()


def dateien():
    """Alles, was auf dem Geraet laeuft - und die Pruefungen dazu.

    Die Pruefungen laufen zwar auf dem Entwicklungsrechner, aber sie
    lesen und bauen denselben Code; eine 3.10-Konstruktion in einem
    Testhelfer ist eine Falle fuer den naechsten, der ihn auf dem
    Geraet laufen laesst (und genau das macht der Nutzer per SSH)."""
    for ordner in ("frontend", "tools"):
        for wurzel, _dirs, namen in os.walk(os.path.join(_REPO, ordner)):
            if "__pycache__" in wurzel:
                continue
            for n in sorted(namen):
                if n.endswith(".py"):
                    yield os.path.join(wurzel, n)


# ---------------------------------------------------------------------------
print("Test 1: jede Datei ist in Python %d.%d lesbar" % ZIEL)
# ---------------------------------------------------------------------------
# DAS BREITE TOR, und es kostet nichts: ast.parse() nimmt
# feature_version und lehnt dann ab, was es in der Zielfassung nicht
# gab. Die Liste pflegt Python, nicht ich.
_zu_neu = []
_anzahl = 0
for pfad in dateien():
    _anzahl += 1
    quelle = io.open(pfad, encoding="utf-8").read()
    try:
        ast.parse(quelle, filename=pfad, feature_version=ZIEL)
    except SyntaxError as e:
        _zu_neu.append((os.path.relpath(pfad, _REPO), e.lineno,
                        str(e).split("(")[0].strip()))
check("alle %d Dateien" % _anzahl, not _zu_neu,
      "%r" % (_zu_neu[:3],) if _zu_neu else
      "geprueft gegen die Fassung aus dem Bench-Kopf des Geraets")

# ---------------------------------------------------------------------------
print()
print("Test 2: kein staticmethod-Objekt auf einer Instanz")
# ---------------------------------------------------------------------------
# GENAU DER FEHLER AUS BUILD 303, und er ist KEINE Syntax - Tor 1
# findet ihn nicht.
#
# Das Deskriptor-Protokoll, das ein staticmethod-Objekt wieder zur
# Funktion macht, laeuft nur bei einem Zugriff ueber die KLASSE. Wer
# es auf eine Instanz setzt, legt das Objekt selbst ins
# Instanz-Verzeichnis - und das ist erst ab Python 3.10 aufrufbar.
#
# ERLAUBT ist also die Zuweisung an ein Attribut einer KLASSE. Die
# fuenf echten Stellen im Projekt sehen alle so aus:
#
#     Framebuffer.zeilen_kopierer = staticmethod(_c_zeilen_kopieren)
#
# Erkannt wird eine Klasse an der Schreibweise (grosser Anfangs-
# buchstabe). Das ist eine Heuristik, und sie ist hier die richtige:
# sie ist in diesem Projekt ausnahmslos erfuellt, sie braucht keine
# Pflege, und im Zweifel schlaegt sie an statt zu schweigen.
_verdacht = []
for pfad in dateien():
    baum = ast.parse(io.open(pfad, encoding="utf-8").read(), filename=pfad)
    for knoten in ast.walk(baum):
        if not (isinstance(knoten, ast.Assign)
                and isinstance(knoten.value, ast.Call)
                and isinstance(knoten.value.func, ast.Name)
                and knoten.value.func.id == "staticmethod"):
            continue
        for ziel in knoten.targets:
            if isinstance(ziel, ast.Name):
                continue              # Klassenebene, der Normalfall
            if (isinstance(ziel, ast.Attribute)
                    and isinstance(ziel.value, ast.Name)
                    and ziel.value.id[:1].isupper()):
                continue              # Klasse.attr = staticmethod(...)
            _verdacht.append((os.path.relpath(pfad, _REPO), knoten.lineno))
check("keine Zuweisung an eine Instanz", not _verdacht,
      "%r" % (_verdacht,) if _verdacht else
      "die fuenf echten Stellen setzen alle auf Framebuffer, also auf "
      "die Klasse")

# ---------------------------------------------------------------------------
print()
print("Test 3: keine Funktion, die es in 3.9 noch nicht gab")
# ---------------------------------------------------------------------------
# DIE ZWEITE SORTE FALLE, die durch Tor 1 fiele: ein Name, der
# syntaktisch einwandfrei ist und erst spaeter existierte. Die Liste
# ist bewusst kurz und nennt nur, was in diesem Projekt plausibel
# versehentlich hineingeriete - eine vollstaendige Liste waere nicht
# zu pflegen und wuerde das Vertrauen in den Test verwechseln mit
# Vollstaendigkeit.
ZU_NEU = {
    "pairwise": "itertools.pairwise - Python 3.10",
    "bit_count": "int.bit_count() - Python 3.10",
    "anext": "anext() - Python 3.10",
    "aiter": "aiter() - Python 3.10",
    "TaskGroup": "asyncio.TaskGroup - Python 3.11",
    "ExceptionGroup": "ExceptionGroup - Python 3.11",
    "StrEnum": "enum.StrEnum - Python 3.11",
    "cbrt": "math.cbrt - Python 3.11",
    "tomllib": "tomllib - Python 3.11",
    "batched": "itertools.batched - Python 3.12",
    "process_cpu_count": "os.process_cpu_count - Python 3.13",
}
_gefunden = []
for pfad in dateien():
    quelle = io.open(pfad, encoding="utf-8").read()
    baum = ast.parse(quelle, filename=pfad)
    for knoten in ast.walk(baum):
        name = None
        if isinstance(knoten, ast.Attribute):
            name = knoten.attr
        elif isinstance(knoten, ast.Name):
            name = knoten.id
        elif isinstance(knoten, (ast.Import, ast.ImportFrom)):
            for a in knoten.names:
                if a.name.split(".")[0] in ZU_NEU:
                    _gefunden.append((os.path.relpath(pfad, _REPO),
                                      knoten.lineno,
                                      ZU_NEU[a.name.split(".")[0]]))
            continue
        if name in ZU_NEU:
            _gefunden.append((os.path.relpath(pfad, _REPO), knoten.lineno,
                              ZU_NEU[name]))
        # strict= bei zip() ist ein Schluesselwort, kein Name.
        if (isinstance(knoten, ast.Call)
                and isinstance(knoten.func, ast.Name)
                and knoten.func.id == "zip"
                and any(k.arg == "strict" for k in knoten.keywords)):
            _gefunden.append((os.path.relpath(pfad, _REPO), knoten.lineno,
                              "zip(strict=...) - Python 3.10"))
check("keine der %d gelisteten Neuerungen" % len(ZU_NEU), not _gefunden,
      "%r" % (_gefunden[:3],) if _gefunden else
      "kurz gehalten mit Absicht - Vollstaendigkeit waere nicht zu "
      "pflegen, und Tor 1 traegt die Hauptlast")

# ---------------------------------------------------------------------------
print()
print("Test 4: der Bericht nennt die Fassung, auf der er entstand")
# ---------------------------------------------------------------------------
# OHNE DIESE ZEILE WAERE DER BEFUND AUS BUILD 303 NICHT ZU FINDEN
# GEWESEN. Dass im Kopf "Python : 3.9.6" stand, war der Hinweis, der
# den Unterschied zum Container ueberhaupt sichtbar machte.
_bench = io.open(os.path.join(_REPO, "frontend", "fe", "bench.py"),
                 encoding="utf-8").read()
check("Abschnitt Kopf schreibt die Python-Fassung",
      "Python" in _bench and "version" in _bench.lower(),
      "ein Bericht muss sagen, worauf er entstanden ist")

# ---------------------------------------------------------------------------
print()
if fails:
    print("FEHLGESCHLAGEN (%d):" % len(fails))
    for f in fails:
        print("  - %s" % f)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
