#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Der Startweg wartet auf nichts, was man nicht sieht (Build 291/292).

BUILD 292 kam aus dem Bench, den Build 291 moeglich gemacht hat. Die
vier neuen Marken haben sofort geliefert:

    Konsole uebernommen        609 ms   29 %
    Erstes Bild gewischt       182 ms    9 %

Beides war vorher in einem Posten namens "Musik, RA-Abruf angestossen"
versteckt. Und beides war behebbar:

- Die 609 ms waren REINES SCHLAFEN: 0,1 s vor der F9-Injektion,
  zweimal 0,05 s in inject() selbst, 0,4 s danach. Die 0,4 s bleiben
  (MiSTers Main muss die Taste sehen, bevor wir die Eingabegeraete
  wieder an uns nehmen - die Jagd der Builds 146-152), aber sie
  werden jetzt GENUTZT statt abgesessen.
- Die 182 ms waren der Vignetten-Hintergrund, und Build 291 hatte in
  den Quelltext geschrieben, der Bench solle sagen, ob die Vorwaermung
  in run() diese Farbe erfasst. Antwort: nein - und beim Nachsehen
  auch, warum nicht. Dort stand (16, 18, 24) als Zahlentripel, und
  C_BG IST (16, 18, 24). Dieselbe Farbe, zweimal verschieden
  geschrieben; die Vorwaermung lief NACH diesem clear() und war immer
  nur ein Treffer im Zwischenspeicher. Diese Rechnung fuellt jetzt die
  F9-Frist.
- Dabei fiel auf, dass run() auch SCHWARZ vorwaermt - rund 180 ms und
  7,9 MB, die liegenbleiben -, obwohl Schwarz nur gebraucht wird, wenn
  gleich eine Boot-Animation laeuft. Die laeuft einmal je
  MiSTer-Start. Bei jedem spaeteren Start des Frontends wurde eine
  Farbe vorgewaermt, die niemand benutzt.

Die urspruengliche Aufgabe von Build 291 steht darunter.

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
print("Test 2: die Markenkette, und zwar in der Reihenfolge des Codes")

NEU = ("Waechter angelegt", "Konsole uebernommen",
       "Erstes Bild gezeigt", "Musikspieler angelegt")
for name in NEU:
    check("Marke '%s'" % name, '_startmarke("%s")' % name in fe_src)

# DIE REIHENFOLGE IST DER EIGENTLICHE PUNKT (Build 276): eine Marke
# misst die Zeit seit der VORIGEN. Steht sie an der falschen Stelle,
# traegt sie fremde Millisekunden und zeigt woanders null an. Geprueft
# wird deshalb die Reihenfolge im Quelltext, nicht nur das Vorkommen.
# ERWEITERT IN BUILD 292 um die Marken, die dort dazugekommen sind.
# Die Kette ist die eigentliche Zusage dieses Tests: sie haelt die
# Reihenfolge fest, in der der Start durch seine Abschnitte laeuft.
kette = ("Vorlauf bis in den Konstruktor",
         "Framebuffer und Eingaben offen", "Waechter angelegt",
         "F9 eingespeist", "Erstes Bild gerechnet",
         "Restfrist fuer MiSTer abgewartet", "Konsole uebernommen",
         "Erstes Bild gezeigt", "Musikspieler angelegt",
         "Musik, RA-Abruf angestossen", "Spieleliste eingelesen",
         "Rest des Aufbaus", "Musikstart angestossen")
stellen = [fe_src.find('_startmarke("%s")' % n) for n in kette]
check("alle %d Marken der Kette gefunden" % len(kette),
      all(s > 0 for s in stellen))
check("und sie stehen in dieser Reihenfolge im Quelltext",
      stellen == sorted(stellen),
      " -> ".join(n for _s, n in sorted(zip(stellen, kette))))

# Jede Marke muss das einschliessen, was ihr Name sagt - sonst misst
# sie etwas anderes, und genau daran ist Bench 13 haengengeblieben.
i_f9 = fe_src.find('_startmarke("F9 eingespeist")')
i_gerechnet = fe_src.find('_startmarke("Erstes Bild gerechnet")')
i_konsole = fe_src.find('_startmarke("Konsole uebernommen")')
i_gezeigt = fe_src.find('_startmarke("Erstes Bild gezeigt")')
i_clear = fe_src.find("self.fb.clear(C_BG)")
i_flip = fe_src.find("self.fb.flip()", i_konsole)
check("das clear() liegt in der Scheibe 'Erstes Bild gerechnet'",
      i_f9 < i_clear < i_gerechnet)
check("das flip() liegt in der Scheibe 'Erstes Bild gezeigt'",
      i_konsole < i_flip < i_gezeigt)

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
         "zwei mpg123 gleichzeitig auf derselben"),
        ("die genutzte F9-Frist", fe_src, "BUILD 292"),
        ("warum an der Frist nicht geschraubt wird", fe_src,
         "Jagd der Builds 146-152"),
        ("die doppelt geschriebene Farbe", fe_src,
         "C_BG IST (16, 18, 24)")):
    check("%s ist erklaert" % was, txt in wo)

print()

# ---------------------------------------------------------------- 7
print("Test 7: die F9-Frist wird genutzt, nicht verkuerzt (Build 292)")

ecm = koerper(fe_src, "enter_console_mode", klasse="Frontend")
check("enter_console_mode ist gefunden", bool(ecm))
check("die 0,4 s stehen nicht mehr als nackte Zahl darin",
      "time.sleep(0.4)" not in ecm)
check("die Zeit hat jetzt einen Namen",
      "F9_NACHLAUF_SEK = 0.4" in fe_src
      and "self.F9_NACHLAUF_SEK" in ecm)
# DIE ZWILLINGE MUESSEN GLEICH BLEIBEN. EXIT_NACH_F12_SEK ist seit
# Build 162 ausdruecklich "dieselbe Zeit, die enter_console_mode()
# seit jeher nach seiner Injektion wartet". Zwei Zahlen mit einer
# Begruendung sind genau die Sorte Paar, bei der spaeter nur eine
# geaendert wird.
check("und sie ist dieselbe wie auf dem Ausstiegsweg",
      "EXIT_NACH_F12_SEK = 0.4" in fe_src,
      "Build 162: dieselbe Zeit in der Gegenrichtung")
check("die Frist wird gesetzt", "self._f9_frist = time.monotonic()" in ecm)
check("gewartet wird nur, wenn der Aufrufer es will",
      "def enter_console_mode(self, nachlauf=True)" in fe_src
      and "if nachlauf:" in ecm,
      "Vorgabe True - alle bisherigen Aufrufer merken nichts")

# Die anderen beiden Aufrufer duerfen NICHT umgestellt sein: nur der
# Startweg hat etwas Nuetzliches zu tun, das in die Frist passt.
check("nur EIN Aufrufer verzichtet auf das Warten",
      fe_src.count("enter_console_mode(nachlauf=False)") == 1,
      "%d x" % fe_src.count("enter_console_mode(nachlauf=False)"))

init_fe = koerper(fe_src, "__init__", klasse="Frontend")
# DAS IST DIE TRAGENDE ZUSAGE DIESES BUILDS, und sie ist die eine,
# die man nicht verletzen darf: MiSTers Main muss das F9 gesehen
# haben, BEVOR wir die Eingabegeraete wieder an uns nehmen. Das war
# die Jagd der Builds 146-152. Verschoben werden darf nur eine
# Rechnung im eigenen Puffer - nie der Griff und nie die
# Konsolen-Aufrufe.
i_warten = init_fe.find("self._f9_nachlauf_abwarten()")
check("der Startweg wartet die Restfrist selbst ab", i_warten > 0)
for was, nadel in (("set_cursor_blink", "self.set_cursor_blink(False)"),
                   ("konsole_cursor_aus", "self.konsole_cursor_aus()"),
                   ("konsole_ruhig_stellen", "self.konsole_ruhig_stellen()"),
                   ("textkonsole_grafik_an", "self.textkonsole_grafik_an()"),
                   ("der Griff auf die Eingaben", "self.inp.grab(True)"),
                   ("das erste sichtbare Bild", "self.fb.flip()")):
    i = init_fe.find(nadel)
    check("%s steht HINTER der vollen Frist" % was,
          i > i_warten > 0, "sonst sieht MiSTer das F9 nicht")
# Und das Einzige, was davor darf, ist die Rechnung.
check("nur das clear() nutzt die Frist",
      0 < init_fe.find("self.fb.clear(C_BG)") < i_warten,
      "reine Rechnung im eigenen Puffer, nichts davon ist zu sehen")

print()

# ---------------------------------------------------------------- 8
print("Test 8: und das Abwarten wird AUSGEFUEHRT")

# GEZAEHLT, NICHT GEMESSEN. Der Pruefstand friert time.monotonic ein
# (siehe _harness.py: fm.time.monotonic = lambda: NOW[0]) - eine
# Stoppuhr liefe hier in genau die eingefrorene Uhr, die uns in
# Build 267 schon einmal ein falsches Ergebnis gegeben hat. Also
# wird time.sleep durch einen Zaehler ersetzt und gefragt, wie lange
# die Funktion zu schlafen VERLANGT. Dasselbe Verfahren wie beim
# inject()-Test.
import _harness as H                                      # noqa: E402

geschlafen = []
_echt_sleep = H.fm.time.sleep
H.fm.time.sleep = lambda s: geschlafen.append(s)
try:
    jetzt = H.fm.time.monotonic()
    abwarten = H.fm.Frontend._f9_nachlauf_abwarten

    class F9Attrappe(object):
        pass

    # 8a) Frist laeuft noch: genau der REST wird abgesessen, nicht
    #     die ganzen 0,4 s.
    a = F9Attrappe()
    a._f9_frist = jetzt + 0.25
    abwarten(a)
    check("bei offener Frist wird nur der Rest gewartet",
          len(geschlafen) == 1 and abs(geschlafen[0] - 0.25) < 1e-6,
          geschlafen)

    # 8b) Frist abgelaufen: gar nicht schlafen. Das ist der Fall, den
    #     Build 292 herbeifuehren will - die Arbeit dazwischen hat
    #     gereicht.
    geschlafen[:] = []
    a = F9Attrappe()
    a._f9_frist = jetzt - 0.01
    abwarten(a)
    check("bei abgelaufener Frist wird NICHT gewartet",
          geschlafen == [], geschlafen)

    # 8c) Ohne Frist (nie gesetzt) darf es nicht krachen und nicht
    #     warten - getattr mit Vorgabe 0.0.
    geschlafen[:] = []
    abwarten(F9Attrappe())
    check("ohne gesetzte Frist passiert nichts", geschlafen == [])
finally:
    H.fm.time.sleep = _echt_sleep

# Und die Summe, die der Startweg dadurch spart: vorher 0,4 s blind,
# jetzt 0,4 s minus der Rechnung. Die Rechnung lag auf dem Geraet des
# Nutzers bei 182 ms - also rund 0,2 s statt 0,4 s.
check("die Zeit selbst ist unveraendert 0,4 s",
      abs(H.fm.Frontend.F9_NACHLAUF_SEK - 0.4) < 1e-9,
      str(H.fm.Frontend.F9_NACHLAUF_SEK))
check("und beide Richtungen halten dieselbe ein",
      H.fm.Frontend.F9_NACHLAUF_SEK
      == H.fm.Frontend.EXIT_NACH_F12_SEK,
      "Eintritt F9 / Austritt F12 - Build 162")

print()

# ---------------------------------------------------------------- 9
print("Test 9: das Vorwaermen von Schwarz haengt an der Animation")

run_k = koerper(fe_src, "run", klasse="Frontend")
check("run() ist gefunden", bool(run_k))
check("Schwarz wird nur noch bedingt vorgewaermt",
      "if not os.path.exists(BOOTANIM_PLAYED_MARKER):" in run_k
      and "self.fb.clear((0, 0, 0))" in run_k)
# C_BG bleibt stehen - als Absicherung, falls __init__ seinen Wisch
# verliert. Es darf aber nicht in denselben if-Zweig geraten.
i_cbg = run_k.find("self.fb.clear(C_BG)")
i_if = run_k.find("if not os.path.exists(BOOTANIM_PLAYED_MARKER):")
check("C_BG wird weiterhin unbedingt gewaermt", 0 < i_cbg < i_if,
      "Absicherung, falls __init__ seinen Wisch eines Tages verliert")

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
