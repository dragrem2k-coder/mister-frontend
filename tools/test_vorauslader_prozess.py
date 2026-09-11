#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft den Cover-Vorauslader als eigenen Prozess (Build 102).

NUTZER-RUECKMELDUNG, aus der das entstanden ist: "HDMI-Modus laeuft
auch, aber das Scrollen ist mir da zu langsam, vor allem wenn Zeilen
nach unten neu ins Bild kommen, auch wenn ich zwischen den Ordnern hin
und her wechsle. Laufen da noch irgendwelche Sachen im Hintergrund, die
das verlangsamen?"

Ja - der Vorauslader. Bis Build 101 rechnete er in einem THREAD dieses
Prozesses, und Pythons GIL laesst immer nur einen Thread rechnen. Eine
begonnene Miniatur liess sich nicht mittendrin abbrechen; auf dem Geraet
kostet eine solche Erstberechnung 200-500 ms (ein Kategorie-Logo 722 ms).
Wer in genau diesem Moment eine Taste drueckte, wartete. Als eigener
Prozess rechnet der Vorauslader auf dem zweiten CPU-Kern des DE10-Nano
und nimmt dem Zeichnen nichts mehr weg.

WORAUF ES BEI DIESEM TEST ANKOMMT - drei Dinge, die schiefgehen koennen
und die man am laufenden Frontend NICHT bemerken wuerde:

  1. Der Prozess rechnet zwar, schreibt aber in den falschen Ordner.
     Das Frontend schaltet zwischen HD- und SD-Zwischenspeicher um
     (Build 85). Haette der Arbeitsprozess seine eigene Vorstellung
     davon, waeren die Miniaturen berechnet - und der Zeichenpfad
     faende sie trotzdem nie. Es sieht dann einfach nur so aus, als
     brauchte das Vorrechnen nichts.
  2. Der Rueckfall greift nicht. Ohne startbaren Prozess MUSS wieder
     der Thread rechnen; sonst waere das Vorrechnen auf Geraeten ohne
     passendes python3 stillschweigend tot.
  3. Ein einziges kaputtes Bild beendet den Arbeitsprozess. Dann waere
     der Vorauslader fuer den Rest der Sitzung weg - ohne dass irgendwo
     etwas auffiele.

Ausfuehren:
    python3 tools/test_vorauslader_prozess.py
"""
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import zlib

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
_FRONTEND = os.path.join(_REPO, "frontend")
sys.path.insert(0, _FRONTEND)

import fe.art as art                                    # noqa: E402
import fe.prewarm as P                                  # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


def art_datei(pfad, w, h):
    """Ein echtes .art-Bild schreiben - dasselbe Format, das auf der
    Karte liegt: "ART1", Breite, Hoehe, zlib-gepackte BGRA-Punkte."""
    pix = bytearray()
    for y in range(h):
        for x in range(w):
            pix += bytes(((x * 3) % 256, (y * 5) % 256,
                          ((x + y) * 7) % 256, 0))
    with open(pfad, "wb") as f:
        f.write(b"ART1" + struct.pack("<HH", w, h) + zlib.compress(bytes(pix), 1))


def warten_bis(pruefung, sekunden=20.0):
    ende = time.monotonic() + sekunden
    while time.monotonic() < ende:
        if pruefung():
            return True
        time.sleep(0.05)
    return pruefung()


TMP = tempfile.mkdtemp(prefix="vorauslader_")
QUELLE = os.path.join(TMP, "quelle")
os.makedirs(QUELLE)
BILD = os.path.join(QUELLE, "cover.art")
art_datei(BILD, 240, 336)
KAPUTT = os.path.join(QUELLE, "kaputt.art")
open(KAPUTT, "wb").write(b"keine gueltige ART1-Datei")

print("Test 1: der Arbeitsprozess allein - rechnet und antwortet")
# Bewusst OHNE die Prewarmer-Klasse: wenn hier etwas klemmt, liegt es am
# Arbeitsprozess selbst und nicht an der Ansteuerung.
cache1 = os.path.join(TMP, "cache_allein")
p = subprocess.Popen([sys.executable, P.WORKER],
                     stdin=subprocess.PIPE, stdout=subprocess.PIPE)
auftrag = "%s\t%d\t%d\t%s\n" % (cache1, 80, 112, BILD)
p.stdin.write(auftrag.encode())
p.stdin.flush()
antwort = p.stdout.readline()
check("erste Antwort ist 'fertig'", antwort[:1] == b"f", "(%r)" % antwort)

# Derselbe Auftrag noch einmal: jetzt liegt die Miniatur schon da.
p.stdin.write(auftrag.encode())
p.stdin.flush()
antwort = p.stdout.readline()
check("zweite Antwort ist 'Treffer'", antwort[:1] == b"t", "(%r)" % antwort)

# Punkt 3 von oben: ein kaputtes Bild darf den Prozess nicht umbringen.
p.stdin.write(("%s\t80\t112\t%s\n" % (cache1, KAPUTT)).encode())
p.stdin.flush()
antwort = p.stdout.readline()
check("kaputtes Bild ergibt 'Fehler'", antwort[:1] == b"e", "(%r)" % antwort)
p.stdin.write(auftrag.encode())
p.stdin.flush()
antwort = p.stdout.readline()
check("Prozess lebt danach weiter", antwort[:1] == b"t", "(%r)" % antwort)

p.stdin.close()
check("Prozess endet, wenn das Rohr schliesst",
      warten_bis(lambda: p.poll() is not None, 10.0),
      "(Rueckgabewert %r)" % p.poll())

print("Test 2: der Vorauslader benutzt den Prozess")
art.THUMB_CACHE_BASE = os.path.join(TMP, "base")
art.THUMB_CACHE_DIR = os.path.join(TMP, "cache_prozess")
pw = P.CoverPrewarmer()
pw.start()
check("Betriebsart ist 'prozess'", pw.betriebsart() == "prozess",
      "(%s)" % pw.betriebsart())
check("vorher liegt nichts im Zwischenspeicher",
      not art.thumb_cache_has(BILD, 90, 126))
pw.uebergeben([(BILD, 90, 126)])
check("Miniatur kommt an",
      warten_bis(lambda: art.thumb_cache_has(BILD, 90, 126)))
check("als 'gerechnet' gezaehlt", pw.gerechnet >= 1, "(%d)" % pw.gerechnet)

print("Test 3: der Auftrag bestimmt den Ordner (HD/SD-Umschaltung)")
# Punkt 1 von oben. Die Klasse schickt art.THUMB_CACHE_DIR mit JEDEM
# Auftrag mit. Schaltet das Frontend um, muss die naechste Miniatur im
# NEUEN Ordner landen - und der alte darf davon nichts abbekommen.
alt_dir = art.THUMB_CACHE_DIR
neu_dir = os.path.join(TMP, "cache_umgeschaltet")
art.THUMB_CACHE_DIR = neu_dir
pw.uebergeben([(BILD, 70, 98)])
check("Miniatur landet im neuen Ordner",
      warten_bis(lambda: art.thumb_cache_has(BILD, 70, 98)))
art.THUMB_CACHE_DIR = alt_dir
check("und NICHT im alten", not art.thumb_cache_has(BILD, 70, 98))
art.THUMB_CACHE_DIR = neu_dir
pw.beenden()

print("Test 4: Rueckfall auf den Thread, wenn der Prozess nicht startet")
# Punkt 2 von oben.
art.THUMB_CACHE_DIR = os.path.join(TMP, "cache_thread")
echter_worker = P.WORKER
P.WORKER = os.path.join(TMP, "gibt_es_nicht.py")
pw2 = P.CoverPrewarmer()
pw2.start()
check("Betriebsart ist 'thread'", pw2.betriebsart() == "thread",
      "(%s)" % pw2.betriebsart())
pw2.uebergeben([(BILD, 60, 84)])
check("auch im Rueckfall kommt die Miniatur an",
      warten_bis(lambda: art.thumb_cache_has(BILD, 60, 84)))
pw2.beenden()
P.WORKER = echter_worker

print("Test 5: Abbrechen wirkt nach hoechstens EINER Miniatur")
# Das ist die eigentliche Zusage des Abbruchs, und sie ist bewusst so
# formuliert statt als "sofort": ein bereits begonnener Auftrag laeuft
# zu Ende, weiter geht es danach nicht. Genau so geprueft - "wie viele
# waren nach 0,4 Sekunden fertig" waere keine Eigenschaft des Codes,
# sondern eine des Testrechners.
art.THUMB_CACHE_DIR = os.path.join(TMP, "cache_abbruch")
bilder = []
for i in range(60):
    b = os.path.join(QUELLE, "reihe%d.art" % i)
    shutil.copyfile(BILD, b)      # gleicher Inhalt, anderer Pfad =
    bilder.append(b)              # anderer Schluessel im Zwischenspeicher


def fertige():
    return sum(1 for b in bilder if art.thumb_cache_has(b, 85, 119))


pw3 = P.CoverPrewarmer()
pw3.start()
pw3.uebergeben([(b, 85, 119) for b in bilder])
time.sleep(0.3)                   # kurz arbeiten lassen
pw3.abbrechen()                   # wie es jede Eingabe tut
n1 = fertige()
time.sleep(1.5)                   # reichlich Zeit fuer viele weitere
n2 = fertige()
check("beim Abbruch war die Liste noch nicht durch", n1 < len(bilder),
      "(%d von %d)" % (n1, len(bilder)))
check("danach kommt hoechstens noch die begonnene dazu", n2 - n1 <= 1,
      "(%d -> %d)" % (n1, n2))
check("die Auftragsliste ist leer", not pw3.beschaeftigt())
pw3.beenden()

print("Test 6: beenden() laesst keinen Prozess zurueck")
art.THUMB_CACHE_DIR = os.path.join(TMP, "cache_ende")
pw4 = P.CoverPrewarmer()
pw4.start()
kind = pw4._proc
check("Prozess laeuft", kind is not None and kind.poll() is None)
pw4.beenden()
check("nach beenden() ist er weg",
      warten_bis(lambda: kind.poll() is not None, 10.0),
      "(Rueckgabewert %r)" % (kind.poll() if kind else None))

print("Test 7: nach beenden() laeuft start() wieder an (Build 103)")
# Gebraucht beim Spielstart: dort wird der Vorauslader abgeraeumt, damit
# waehrend eines laufenden Cores weder ein Prozess herumliegt noch eine
# begonnene Miniatur weiterrechnet. Kehrt man ins Menue zurueck, muss er
# von selbst wieder hochkommen - sonst waere das Vorrechnen nach dem
# ersten Spiel fuer den Rest der Sitzung tot.
art.THUMB_CACHE_DIR = os.path.join(TMP, "cache_neustart")
pw5 = P.CoverPrewarmer()
pw5.start()
erster = pw5._proc
pw5.beenden()
check("nach beenden() kein Prozess mehr", pw5._proc is None)
pw5.start()
check("start() danach wieder im Prozess-Betrieb",
      pw5.betriebsart() == "prozess", "(%s)" % pw5.betriebsart())
check("und es ist ein NEUER Prozess",
      pw5._proc is not None and erster is not None
      and pw5._proc.pid != erster.pid)
pw5.uebergeben([(BILD, 55, 77)])
check("er rechnet auch wieder",
      warten_bis(lambda: art.thumb_cache_has(BILD, 55, 77)))

# Der gefaehrliche Teil daran: der alte Arbeiter-Thread darf nach dem
# Neustart NICHT als zweiter weiterlaufen. Zwei Threads auf derselben
# Leitung zum Arbeitsprozess, und keine Antwort gehoerte mehr eindeutig
# zu einer Frage.
lebende = [t for t in __import__("threading").enumerate()
           if t.name == "cover-prewarm" and t.is_alive()]
check("genau ein Arbeiter-Thread", len(lebende) <= 1,
      "(%d)" % len(lebende))
pw5.beenden()

print("Test 8: der Arbeitsprozess stellt sich freiwillig zurueck")
# Die Sicherung fuer den Fall, dass doch einmal etwas gleichzeitig
# laeuft: mit zurueckgestellter Prioritaet bekommt das MiSTer-Programm
# die CPU zuerst.
quelle_w = open(P.WORKER, encoding="utf-8").read()
check("os.nice() im Arbeitsprozess", "os.nice(" in quelle_w)
pw6 = P.CoverPrewarmer()
pw6.start()
if pw6._proc is not None:
    def nice_wert():
        # Feld 19 der Zeile; vor dem ersten Feld steht der Programmname
        # in Klammern, der selbst Leerzeichen enthalten darf - deshalb
        # hinter der letzten ") " trennen. Danach ist Feld 3 (Zustand)
        # der Index 0, die Prioritaet also Index 16.
        felder = open("/proc/%d/stat" % pw6._proc.pid).read() \
            .rsplit(") ", 1)[1].split()
        return int(felder[16])
    # Kurz warten: os.nice() ist die erste Handlung des Arbeitsprozesses,
    # aber bis dahin muss Python erst hochgefahren sein.
    warten_bis(lambda: nice_wert() > 0, 15.0)
    check("Prozess laeuft zurueckgestellt", nice_wert() > 0,
          "(nice %d)" % nice_wert())
pw6.beenden()

print("Test 9: das Frontend raeumt ihn beim Beenden und beim Spielstart ab")
# Ohne diesen Aufruf koennte ein Arbeitsprozess, der gerade mitten in
# einer Miniatur steckt, den Frontend-Ausstieg ueberleben und weiter auf
# die SD-Karte schreiben.
quelle = open(os.path.join(_FRONTEND, "frontend.py"),
              encoding="utf-8", errors="replace").read()
check("PREWARMER.beenden() steht im Aufraeumzweig von run()",
      "PREWARMER.beenden()" in quelle)
# Und direkt vor dem Core-Start - dort ist es keine Aufraeumarbeit,
# sondern die Zusage, dass waehrend eines laufenden Spiels nichts von
# uns auf dem zweiten Kern sitzt.
check("PREWARMER.beenden() steht vor launch_core()",
      "PREWARMER.beenden()\n        launch_core(path)" in quelle)

shutil.rmtree(TMP, ignore_errors=True)

print()
if fails:
    print("FEHLGESCHLAGEN (%d):" % len(fails))
    for f_ in fails:
        print("  -", f_)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
