#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Der Startweg wartet auf nichts, was man nicht sieht (Build 291).

WORUM ES GEHT

Bench 13 hat den Start in benannte Stuecke zerlegt. Drei Posten
trugen zusammen ~2,5 von ~3 Sekunden:

    Musik gestartet                 942 ms
    Musik, RA-Abruf angestossen     820 ms
    davon scan_games()              750 ms

Beim Nachlesen stellte sich heraus, dass die ersten zwei nicht das
sind, was ihre Namen sagen:

1. "Musik gestartet" war ein BLOCKIERENDER Aufruf (music.tick()) als
   letzte Anweisung in __init__(), also unmittelbar vor dem ersten
   draw(). Bei Radio als Quelle haengt daran eine Netzabfrage. Der
   Bildschirm blieb knapp eine Sekunde dunkel fuer etwas, das man
   nicht sieht.

2. "Musik, RA-Abruf angestossen" hat 820 ms getragen, die ihr nicht
   gehoeren: zwischen ihr und der vorigen Marke lagen 220 Zeilen ohne
   eine einzige Marke. Der RA-Abruf selbst wird dort nur angestossen
   und kostet nichts. Derselbe Fehler wie in Build 276, nur eine
   Ebene tiefer - dort war die Reihenfolge falsch, hier fehlten die
   Marken.

3. In diesen 820 ms steckt unter anderem MusicPlayer(), und dessen
   erste Anweisung wartete bis zu 1,1 Sekunden auf verwaiste
   mpg123-Prozesse. Verwaiste Prozesse gibt es ausgerechnet nach
   einem Neustart des Frontends - also im haeufigsten Fall.

Dieser Test sichert alle drei Aenderungen ab. Teil 1 prueft den
Quelltext, Teil 2 FUEHRT die neue Torlogik tatsaechlich aus - ein
Test, der nur Zeichen zaehlt, haette uns in diesem Projekt schon
mehrfach das Falsche bestaetigt.

Ausfuehren:
    python3 tools/test_startweg.py
"""
import os
import sys
import time

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
sys.path.insert(0, _HIER)
sys.path.insert(0, os.path.join(_REPO, "frontend"))

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


def koerper(quelle, name, klasse=None):
    """Der Koerper GENAU EINER Funktion oder Methode - per ast, nicht
    per Textsuche.

    DREI FASSUNGEN HAT DIESER HELFER GEBRAUCHT, und alle drei Fehler
    sind in diesem Projekt schon einmal vorgekommen. Sie stehen hier,
    weil der naechste, der eine Pruefung dazuschreibt, sonst denselben
    Weg noch einmal geht:

    1. quelle[i:i+1800] - ein ZEICHENFENSTER. Wird zu klein, sobald
       jemand einen Kommentar ergaenzt, und meldet dann einen Fehler,
       den es nicht gibt. (test_bench, test_konsole_wache)
    2. Schneiden bis zum naechsten "\\n    def " - setzt voraus, dass
       es eine METHODE ist. Bei einer Modulfunktion wie
       _kill_stray_mpg123() steht der naechste vierfach eingerueckte
       'def' erst in der naechsten Klasse; der Schnitt lief ueber das
       Ende der Funktion hinaus und fand fremden Code.
    3. Schneiden bis zum naechsten 'def'/'class' auf gleicher
       Einrueckung - sieht richtig aus, nimmt aber alles mit, was
       zwischen zwei Funktionen auf Modulebene steht. Hier waren das
       die beiden neuen Konstanten, und in deren Kommentaren steht
       das Wort "time.sleep" - also genau der Begriff, auf den die
       Pruefung schaut. Dieselbe Falle wie in test_anleitung: ein
       Wort, das auch in der ERKLAERUNG vorkommt.

    ast kennt die echten Grenzen. Keine Heuristik, kein Fenster.

    Zurueck kommt nur CODE, ohne Kommentarzeilen - eine Pruefung auf
    "hier wird nicht geschlafen" soll den Code lesen, nicht die Prosa
    darueber."""
    import ast
    baum = ast.parse(quelle)
    zeilen = quelle.split("\n")

    def suche(knoten):
        for k in knoten.body:
            if isinstance(k, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                    and k.name == name:
                return k
        return None

    wurzel = baum
    if klasse is not None:
        for k in baum.body:
            if isinstance(k, ast.ClassDef) and k.name == klasse:
                wurzel = k
                break
        else:
            return ""
    fn = suche(wurzel)
    if fn is None:
        return ""
    stueck = zeilen[fn.lineno - 1:fn.end_lineno]
    return "\n".join(z for z in stueck
                     if not z.lstrip().startswith("#"))


FE_PY = os.path.join(_REPO, "frontend", "frontend.py")
AUDIO_PY = os.path.join(_REPO, "frontend", "fe", "audio.py")
fe_src = open(FE_PY, encoding="utf-8").read()
audio_src = open(AUDIO_PY, encoding="utf-8").read()

print(__doc__.strip().split("\n")[0])
print()

# ---------------------------------------------------------------- 1
print("Test 1: der Musikstart haelt den Startweg nicht mehr auf")

# Die eine Stelle in __init__, nicht die im Hauptlauf: gesucht ist der
# Aufruf, der direkt vor der letzten Startmarke steht.
check("music.tick() steht nicht mehr nackt im Start",
      "self.music.tick()      # start playback right away" not in fe_src)
check("sondern in einem Thread",
      "threading.Thread(target=self.music.tick, daemon=True).start()"
      in fe_src)
check("und als daemon, damit er das Beenden nicht aufhaelt",
      "target=self.music.tick, daemon=True" in fe_src)
# Der Name der Marke muss sagen, was sie messen KANN. "gestartet"
# konnte sie nach dieser Aenderung nicht mehr messen.
check("die Marke heisst 'angestossen', nicht 'gestartet'",
      '_startmarke("Musikstart angestossen")' in fe_src
      and '_startmarke("Musik gestartet")' not in fe_src)
# Im Hauptlauf muss der Aufruf weiter stehen - sonst beginnt die Musik
# nie wieder, wenn ein Titel endet.
check("der Hauptlauf ruft tick() weiterhin selbst",
      fe_src.count("self.music.tick()") >= 2,
      "%d Aufrufe" % fe_src.count("self.music.tick()"))

print()

# ---------------------------------------------------------------- 2
print("Test 2: die vier neuen Marken, und zwar in der Reihenfolge des Codes")

NEU = ("Waechter angelegt", "Konsole uebernommen",
       "Erstes Bild gewischt", "Musikspieler angelegt")
for name in NEU:
    check("Marke '%s'" % name, '_startmarke("%s")' % name in fe_src)

# DIE REIHENFOLGE IST DER EIGENTLICHE PUNKT (Build 276): eine Marke
# misst die Zeit seit der VORIGEN. Steht sie an der falschen Stelle,
# traegt sie fremde Millisekunden und zeigt woanders null an. Geprueft
# wird deshalb die Reihenfolge im Quelltext, nicht nur das Vorkommen.
kette = ("Framebuffer und Eingaben offen", "Waechter angelegt",
         "Konsole uebernommen", "Erstes Bild gewischt",
         "Musikspieler angelegt", "Musik, RA-Abruf angestossen",
         "Spieleliste eingelesen", "Rest des Aufbaus",
         "Musikstart angestossen")
stellen = [fe_src.find('_startmarke("%s")' % n) for n in kette]
check("alle neun Marken der Kette gefunden", all(s > 0 for s in stellen))
check("und sie stehen in dieser Reihenfolge im Quelltext",
      stellen == sorted(stellen),
      " -> ".join(n for _s, n in sorted(zip(stellen, kette))))

# Die beiden neuen Marken um das erste Bild muessen das clear()/flip()
# wirklich einschliessen - sonst messen sie etwas anderes als ihr Name.
i_konsole = fe_src.find('_startmarke("Konsole uebernommen")')
i_bild = fe_src.find('_startmarke("Erstes Bild gewischt")')
i_clear = fe_src.find("self.fb.clear((16, 18, 24))")
check("clear()/flip() liegen zwischen den beiden Marken",
      i_konsole < i_clear < i_bild)

print()

# ---------------------------------------------------------------- 3
print("Test 3: das Warten auf verwaiste mpg123-Prozesse ist aus dem Start raus")

kill = koerper(audio_src, "_kill_stray_mpg123")   # Modulfunktion
check("die Funktion ist da", bool(kill))
check("sie schlaeft nicht mehr", "time.sleep" not in kill)
check("sie gibt die Opfer zurueck", "return victims" in kill)
check("und bei einem /proc-Fehler eine leere Liste, keine None",
      "return []" in kill)

# __init__ gibt es in dieser Datei mehrfach - gesucht ist das von
# MusicPlayer, und ast kennt den Unterschied.
init = koerper(audio_src, "__init__", klasse="MusicPlayer")
check("MusicPlayer.__init__ ist gefunden", bool(init))
check("__init__ merkt sich die Opfer",
      "self._fremde_mpg123 = _kill_stray_mpg123() or []" in init)
check("und setzt eine Frist", "self._fremde_frist" in init)
check("__init__ wartet selbst nicht", "time.sleep" not in init)

start_cur = koerper(audio_src, "_start_current", klasse="MusicPlayer")
check("_start_current fragt vor dem Start", "_fremde_weg()" in start_cur)
# Die Reihenfolge ist wichtig: erst fragen, dann den eigenen Prozess
# abschiessen und neu starten.
check("und zwar VOR _start_current_impl()",
      start_cur.find("_fremde_weg()")
      < start_cur.find("_start_current_impl()"))

print()

# ---------------------------------------------------------------- 4
print("Test 4: und die neue Torlogik wird AUSGEFUEHRT, nicht nur gelesen")

import fe.audio as A


class Attrappe(object):
    """Nur die vier Felder, die _fremde_weg() anfasst. Kein echter
    MusicPlayer: dessen __init__ wuerde /proc durchgehen und Signale
    verschicken - ein Test hat auf einem fremden Rechner nichts
    abzuschiessen."""

    def __init__(self, opfer, frist_in):
        self._fremde_mpg123 = list(opfer)
        self._fremde_frist = time.monotonic() + frist_in
        self._fremde_frei_ab = 0.0
        self._fremde_gemeldet = False


weg = A.MusicPlayer._fremde_weg
lebt = set()
getoetet = []
_echt_still_running = A._proc_still_running
_echt_kill = A.os.kill
A._proc_still_running = lambda pid: pid in lebt
A.os.kill = lambda pid, sig: getoetet.append((pid, sig))
try:
    # 4a) Kaltstart: niemand war da. Nichts darf warten.
    a = Attrappe([], 0.0)
    check("ohne Opfer sofort durch", weg(a) is True)

    # 4b) Ein Opfer lebt noch, Frist laeuft: kein Durchlass, kein
    #     SIGKILL - und vor allem kein Warten.
    lebt = {4711}
    a = Attrappe([4711], 1.0)
    t0 = time.monotonic()
    erst = weg(a)
    dauer = time.monotonic() - t0
    check("lebendes Opfer haelt den Start zurueck", erst is False)
    check("kein SIGKILL, solange die Frist laeuft", getoetet == [])
    # DAS IST DIE EIGENTLICHE ZUSAGE DIESES BUILDS, und sie ist
    # messbar: die Pruefung darf nicht warten. Vorher sass hier ein
    # time.sleep() von bis zu 1,1 s.
    check("und die Pruefung wartet nicht", dauer < 0.05,
          "%.1f ms" % (dauer * 1000))
    check("gemeldet wird einmal", a._fremde_gemeldet is True)

    # 4c) Dasselbe Opfer, Frist abgelaufen -> SIGKILL wie vorher.
    a = Attrappe([4711], -1.0)
    zweit = weg(a)
    check("nach Ablauf der Frist gibt es SIGKILL",
          getoetet == [(4711, A.signal.SIGKILL)], getoetet)
    check("durchgelassen wird in diesem Durchgang noch nicht",
          zweit is False, "erst die Gnadenfrist")
    check("die Gnadenfrist ist gesetzt", a._fremde_frei_ab > 0.0)

    # 4d) Opfer ist von allein weg: ein Durchgang Gnadenfrist, dann ja.
    lebt = set()
    getoetet[:] = []
    a = Attrappe([4711], 1.0)
    check("verschwundenes Opfer: erst die Gnadenfrist",
          weg(a) is False)
    check("ohne SIGKILL, es war ja schon weg", getoetet == [])
    check("die Liste ist jetzt leer", a._fremde_mpg123 == [])
    check("und waehrend der Gnadenfrist noch kein Durchlass",
          weg(a) is False)
    # Die Frist absitzen - 0,1 s, das ist der einzige Ort im ganzen
    # Test, an dem gewartet wird, und zwar vom Test, nicht vom Code.
    time.sleep(A.FREMD_GNADE + 0.02)
    check("nach der Gnadenfrist durch", weg(a) is True)
    check("und danach bleibt es dabei", weg(a) is True)
finally:
    A._proc_still_running = _echt_still_running
    A.os.kill = _echt_kill

print()

# ---------------------------------------------------------------- 5
print("Test 5: die Dauern sind unveraendert, nur nicht mehr abgesessen")

# 20 x 50 ms waren 1,0 s; die Gnadenfrist waren 0,1 s. Wer die Werte
# aendert, soll das bewusst tun und diesen Test mitaendern.
check("FREMD_FRIST ist 1,0 s wie die 20 x 50 ms vorher",
      abs(A.FREMD_FRIST - 1.0) < 1e-9, A.FREMD_FRIST)
check("FREMD_GNADE ist 0,1 s wie das time.sleep(0.1) vorher",
      abs(A.FREMD_GNADE - 0.1) < 1e-9, A.FREMD_GNADE)

print()

# ---------------------------------------------------------------- 6
print("Test 6: die Begruendungen stehen im Quelltext, nicht nur hier")

for was, wo, txt in (
        ("der Musikstart", fe_src, "BUILD 291"),
        ("die fehlenden Marken", fe_src, "KEINE HATTE"),
        ("das verlegte Warten", audio_src, "BUILD 291"),
        ("warum das Warten noetig BLEIBT", audio_src,
         "zwei mpg123 gleichzeitig auf derselben")):
    check("%s ist erklaert" % was, txt in wo)

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
