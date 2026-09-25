#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Die Reihenfolge beim Beenden (Build 165).

DER VORFALL - UND ER WAR MEINER

Zwei Tage lang kam der Nutzer beim Beenden nicht mehr ins MiSTer-OSD:
"erst der blinkende _, dann Welcome to MiSTer ... login:, dann
passiert nichts mehr". Vorher ging das jahrelang.

Die alte Reihenfolge war:

    Bildschirm schwarz  ->  fb.close()  ->  DANN F12

Build 163 hat das F12 nach vorne gezogen - richtig, denn der
exklusive Griff auf die Eingabegeraete darf nicht gehalten werden,
waehrend hinten etwas haengt. Aber das Leeren und Schliessen des
Framebuffers blieb hinten stehen:

    F12  ->  0,4 s  ->  Bildschirm schwarz  ->  fb.close()

Damit wurde der Bildschirm schwarz gemalt, NACHDEM MiSTer auf das
F12 hin sein OSD aufbaut. Wir haben es uebermalt. Das F12 kam die
ganze Zeit an - sein Ergebnis wurde sofort wieder weggewischt.

DIE REGEL, DIE DIESER TEST FESTHAELT

    Der Bildschirm gehoert ab dem F12 MiSTer.
    Also: Framebuffer freigeben VOR dem F12, nie danach.

Und die Verbesserungen aus 162/163 bleiben: Griff frueh loesen,
Reissleine gestellt, langsames Aufraeumen erst hinterher.

Geprueft wird die REIHENFOLGE im Herunterfahren-Block - die ist hier
die eigentliche Zusage, nicht irgendeine einzelne Zeile.

Ausfuehren:
    python3 tools/test_beenden.py
"""
import io
import os
import re
import sys

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


quelle = io.open(os.path.join(_REPO, "frontend", "frontend.py"),
                 encoding="utf-8").read()

# GEAENDERT (Build 169): es gibt wieder nur EINEN Ausstieg.
#
# Build 167 hatte auf Wunsch den Ablauf von Build 145 als Standard
# zurueckgeholt (ein F12, kein Nachsehen). Eine Messung auf einem
# Geraet mit Kernel 6.18.38 hat danach gezeigt, dass genau das zu
# wenig ist:
#
#   11:28:38  Exit: injiziere F12 (1/3)
#   11:28:39  Exit: MiSTer bei   1% - das OSD ist NICHT gekommen
#   11:28:39  Exit: injiziere F12 (2/3)
#   11:28:40  Exit: MiSTer bei 100% - das OSD ist da
#
# Das erste eingespeiste F12 kommt auf dem neuen Kernel nicht an.
# Der 145er-Weg ist deshalb entfernt - Code, von dem wir WISSEN,
# dass er den gemeldeten Fehler erzeugt, gehoert nicht aufgehoben.
# Die REIHENFOLGE von Build 145 gilt unveraendert weiter und wird
# hier weiter geprueft; dazu kommen die Zusaetze aus 162-166.


def methode(name):
    """Den Rumpf EINER Methode herausschneiden."""
    anfang = quelle.index("    def %s(self" % name)
    rest = quelle[anfang + 10:]
    return rest[:rest.index("\n    def ")]


def ohne_kommentare(text):
    """Kommentare raus - sonst trifft die Suche die Erklaerung statt
    des Codes. (Genau der Fehler, der test_filter.py rot gemacht
    hat: nach Quelltext suchen, ohne zu pruefen, ob es der
    ausgefuehrte ist.)"""
    return "\n".join(z for z in text.splitlines()
                     if not z.strip().startswith("#"))


block = methode("_beenden")
code = ohne_kommentare(block)


def pos(muster, was):
    m = re.search(muster, code)
    if m is None:
        check("gefunden: %s" % was, False)
        return None
    return m.start()


print("Test 0: es gibt genau EINEN Ausstieg")
check("der 145er-Weg ist entfernt", "_beenden_wie_145" not in quelle)
check("und es gibt keine zweite Variante daneben",
      "_beenden_mit_mechanik" not in quelle)
lauf = methode("run")
check("das finally ruft ihn ohne Fallunterscheidung",
      "self._beenden()" in lauf
      and "konsole_mechanik()" not in lauf.split("self._beenden()")[0]
          .rsplit("finally:", 1)[-1])

print()
print("Test 0b: die REIHENFOLGE von Build 145 gilt unveraendert")
# Was Build 145 machte, passiert weiterhin genau so und in dieser
# Richtung - nur mit Messung und Nachfassen ergaenzt.
for frueher, spaeter in (("self.fb.clear(", "self.fb.close()"),
                         ("self.fb.close()", "_f12_bis_das_osd_kommt"),
                         ("self.inp.grab(False)", "_f12_bis_das_osd_kommt"),
                         ("_f12_bis_das_osd_kommt", "self.inp.close()"),
                         ("_f12_bis_das_osd_kommt", "PREWARMER.beenden()"),
                         ("_f12_bis_das_osd_kommt", "self.music.shutdown()")):
    check("%-28s vor %s" % (frueher, spaeter),
          code.index(frueher) < code.index(spaeter))

print()
p_reissleine = pos(r"self\._notausgang_stellen\(\)", "Reissleine")
p_grab = pos(r"self\.inp\.grab\(False\)", "Griff loesen")
p_clear = pos(r"self\.fb\.clear\(", "Bildschirm leeren")
p_fbclose = pos(r"self\.fb\.close\(\)", "Framebuffer schliessen")
p_f12 = pos(r"self\._f12_bis_das_osd_kommt\(\)", "F12-Abschnitt")
p_inpclose = pos(r"self\.inp\.close\(\)", "Eingaben schliessen")
p_konsole = pos(r"self\.konsole_cursor_an\(\)", "Konsole zurueck")
p_schonung = pos(r"self\.konsole_schonung_zurueck\(\)", "Schonung zurueck")
p_blink = pos(r"self\.set_cursor_blink\(True\)", "Cursorblinken zurueck")
p_prewarm = pos(r"PREWARMER\.beenden\(\)", "Vorauslader beenden")
p_musik = pos(r"self\.music\.shutdown\(\)", "Musik beenden")

alle = [p_reissleine, p_grab, p_clear, p_fbclose, p_f12, p_inpclose,
        p_konsole, p_schonung, p_blink, p_prewarm, p_musik]

print("Test 1: DIE REGEL - nach dem F12 wird NICHTS mehr angefasst")
# Build 165 hat die halbe Regel gebaut (Framebuffer), Build 166 die
# andere Haelfte (tty1). Beides aus demselben Grund: was nach dem F12
# noch schreibt, holt MiSTer die Anzeige wieder weg.
if None not in (p_clear, p_fbclose, p_f12, p_konsole, p_schonung, p_blink):
    check("Bildschirm wird VOR dem F12 geleert", p_clear < p_f12)
    check("fb.close() passiert VOR dem F12", p_fbclose < p_f12)
    check("der Konsolen-Cursor wird VOR dem F12 zurueckgesetzt",
          p_konsole < p_f12)
    check("die Bildschirmschonung ebenfalls VOR dem F12",
          p_schonung < p_f12)
    check("das Cursorblinken ebenfalls VOR dem F12", p_blink < p_f12)
    danach = code[p_f12:]
    check("nach dem F12 wird nicht mehr gezeichnet",
          "fb.clear" not in danach and "fb.flip" not in danach)
    check("nach dem F12 wird nicht mehr auf die Konsole geschrieben",
          "tty1_schreiben" not in danach
          and "konsole_" not in danach
          and "set_cursor_blink" not in danach)

print()
print("Test 2: was Build 162/163 gebracht hat, bleibt")
if None not in alle:
    check("die Reissleine steht als Allererstes",
          p_reissleine < min(p_grab, p_clear, p_f12))
    check("der Griff auf die Eingaben wird frueh geloest",
          p_grab < p_f12)

print()
print("Test 3: nichts davon darf den Ausstieg blockieren")
check("das Freigeben des Framebuffers ist abgesichert",
      re.search(r"try:\s*\n\s*self\.fb\.clear\(", code) is not None)
check("die Reissleine hat eine Obergrenze",
      "HERUNTERFAHREN_MAX" in quelle)

print()
print("Test 4: beim F12 wird nachgesehen, ob das OSD kommt (Build 166)")
# Beim START wiederholt _konsole_sichern() sein F9 sieben Mal, weil
# EIN eingespeistes Umschalt-Ereignis auf diesem Geraet oft nicht
# sitzt. Beim BEENDEN wurde dieselbe Unzuverlaessigkeit bis Build 165
# einfach gehofft weg zu sein.
i = quelle.index("    def _f12_bis_das_osd_kommt(self")
f12 = quelle[i:i + 3000]
f12 = f12[:f12.index("\n    # Nach so vielen Sekunden")]
check("es wird wirklich eingespeist", "self.inp.inject(KEY_F12)" in f12)
check("danach wird gewartet, bevor gemessen wird",
      f12.index("EXIT_NACH_F12_SEK") < f12.index("_anzeige_messen"))
check("gemessen wird MiSTers Last", "_anzeige_messen()" in f12)
check("die Schwelle ist dieselbe wie beim Start",
      "MISTER_BESCHAEFTIGT" in f12)
check("bei niedriger Last wird nachgefasst",
      "EXIT_F12_VERSUCHE" in f12 and "for " in f12)
check("eine fehlgeschlagene Einspeisung wird nur protokolliert",
      "Exit-Injection fehlgeschlagen" in f12)
check("ohne Messsignal wird NICHT blind wiederholt",
      "keine Lastmessung moeglich" in f12)
m = re.search(r"EXIT_F12_VERSUCHE = (\d+)", quelle)
check("und zwar klein genug fuer die Reissleine",
      m is not None and 1 <= int(m.group(1)) <= 5,
      m.group(1) if m else "")
mh = re.search(r"HERUNTERFAHREN_MAX = ([\d.]+)", quelle)
if m and mh:
    # Ein Versuch kostet hoechstens EXIT_NACH_F12_SEK + Messfenster.
    schlimmst = int(m.group(1)) * (0.4 + 2.5) + 1.0
    check("die Reissleine schneidet das Nachfassen nicht ab",
          float(mh.group(1)) > schlimmst,
          "%.0f s Frist, schlimmstenfalls %.1f s noetig"
          % (float(mh.group(1)), schlimmst))

# Der Notausgang selbst: ein daemon-Thread, der hart beendet.
i = quelle.index("    def _notausgang_stellen(self")
notausgang = quelle[i:i + 2500]
check("der Notausgang laeuft als daemon-Thread",
      "daemon=True" in notausgang)
check("er beendet den Prozess hart (os._exit)", "os._exit(" in notausgang)
check("er gibt vorher die Einzelinstanz frei",
      "release_single_instance()" in notausgang)

print()
print("Test 5: die zweite Haelfte derselben Sache - der Start")
# enter_console_mode() macht die Gegenrichtung (F9). Dort war die
# Reihenfolge immer richtig und soll es bleiben: Griff loesen, kurz
# warten, einspeisen.
j = quelle.index("    def enter_console_mode(self")
ecm = quelle[j:j + 800]
check("enter_console_mode loest den Griff vor dem F9",
      ecm.index("self.inp.grab(False)") < ecm.index("inject(KEY_F9)"))
check("und wartet dazwischen", "time.sleep(0.1)" in ecm)

print()
print("Test 6: alle Schreibvorgaenge auf tty1 gehen durch EINE Stelle")
# Bis Build 166 schrieb das Frontend an sechs Stellen direkt nach
# /dev/tty1. Damit liess sich weder nachvollziehen noch abschalten,
# was dort passiert - und genau das brauchte es, weil der Nutzer den
# Beginn der ganzen Sache auf diese Builds datiert hat.
offen = [z for z in quelle.splitlines()
         if 'open("/dev/tty1"' in z]
# Erlaubt: die eine Stelle in tty1_schreiben() und run_script(), das
# einem Skript bewusst die echte Konsole gibt.
check("hoechstens zwei Stellen oeffnen tty1 noch selbst",
      len(offen) <= 2, "%d Stellen" % len(offen))
check("es gibt einen gemeinsamen Weg", "def tty1_schreiben(" in quelle)
check("und einen Schalter, der ihn steuert",
      "KONSOLE_MECHANIK_FLAG" in quelle
      and "def konsole_mechanik(" in quelle)
i = quelle.index("    def tty1_schreiben(")
tw = quelle[i:i + 1200]
check("der Schalter hat Vorrang vor jedem Schreibvorgang",
      tw.index("konsole_mechanik()") < tw.index('open("/dev/tty1"'))
check("ohne Schalter wird NICHT geschrieben",
      "if not cls.konsole_mechanik():" in tw)
check("die Wache haengt am selben Schalter",
      "konsole_mechanik()" in quelle[quelle.index("def _konsole_wache"):
                                     quelle.index("def _konsole_wache")
                                     + 1400])
check("und die drei Aufrufe in der Hauptschleife ebenfalls",
      "if self.konsole_mechanik():\n                    "
      "self._konsole_sichern()" in quelle)

print()
print("Test 7: das Boot-Logo wartet, bis es jemand sehen kann")
# Nutzer-Log nach Build 165: "Dragend-Logo: vollstaendig gezeigt" -
# und er hat trotzdem nichts gesehen. Gezeichnet wurde in einen
# Bildspeicher, der zu dem Zeitpunkt nicht auf dem Schirm lag.
i = quelle.index("    def _auf_eigenes_bild_warten(self")
# Bis zur naechsten Methode, ohne feste Fenstergroesse. Mit 3000
# Zeichen lief das hier auf einen ValueError, sobald die Funktion durch
# Build 186 laenger wurde - ein Test, der an der LAENGE des geprueften
# Codes haengt, geht irgendwann kaputt, ohne dass etwas kaputt ist.
warten = quelle[i:]
warten = warten[:warten.index("\n    def ", 10)]
check("es gibt das Warten", bool(warten))
check("es misst dasselbe Signal wie beim Beenden",
      "_mister_last()" in warten and "MISTER_BESCHAEFTIGT" in warten)
check("eine Eingabe bricht das Warten ab", "read_action" in warten)
check("ohne Messsignal wird nicht gewartet",
      "keine Lastmessung moeglich" in warten)
check("und es endet in jedem Fall", "BOOTLOGO_WARTEN_MAX" in warten)
mb = re.search(r"BOOTLOGO_WARTEN_MAX = ([\d.]+)", quelle)
# ANGEHOBEN VON 10 AUF 15 (Build 186). Die Grenze stand auf 10, weil
# eine lange Wartezeit auf dem alten Kernel niemandem genuetzt haette.
# Auf 6.18 richtet MiSTer den Bildspeicher spaet ein, und mit 6 s
# Warten kam das Logo gar nicht mehr (Nutzer: "das Bootlogo wird nicht
# mehr eingeblendet"). Der Wert steht jetzt auf 12 und deckt die
# F9-Nachfasser bei 2, 5 und 9 s ab.
#
# Warum das trotzdem niemanden aufhaelt: gewartet wird nur, solange
# MiSTer noch sein eigenes Menue malt. Sobald er uebergibt, wenn
# jemand eine Taste drueckt oder wenn gar nicht gemessen werden kann,
# ist sofort Schluss. Die vollen 12 s laufen also nur dort ab, wo man
# ohnehin auf MiSTers Menue sieht.
check("die Obergrenze ist kurz genug, um nicht zu stoeren",
      mb is not None and float(mb.group(1)) <= 15.0,
      (mb.group(1) + " s") if mb else "")
check("und die Warteschleife loest die Uebergabe selbst aus",
      "_konsole_sichern(" in warten,
      "sonst wartet sie auf etwas, das nur die Hauptschleife ausloest")
# Und es muss VOR dem Zeichnen stehen, nicht danach.
pa = quelle.index("    def play_boot_animation(self")
pb = quelle[pa:pa + 6000]
check("gewartet wird, bevor gezeichnet wird",
      pb.index("_auf_eigenes_bild_warten()") < pb.index("_logo_an"))
check("aber nur mit eingeschalteter Mechanik - Build 145 wartete nicht",
      pb.index("self.konsole_mechanik()")
      < pb.index("_auf_eigenes_bild_warten()"))

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
