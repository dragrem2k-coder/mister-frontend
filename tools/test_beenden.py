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

# Den finally-Block von run() herausschneiden: ab dem Marker bis zum
# Ende der Methode.
start = quelle.index("# HERUNTERFAHREN (umgestellt in Build 163)")
rest = quelle[start:]
ende = rest.index("\n    # Pause zwischen dem F12")
block = rest[:ende]

# Kommentare raus - sonst trifft die Suche die Erklaerung statt des
# Codes. (Genau der Fehler, der test_filter.py rot gemacht hat: nach
# Quelltext suchen, ohne zu pruefen, ob es der ausgefuehrte ist.)
code = "\n".join(z for z in block.splitlines()
                 if not z.strip().startswith("#"))


def pos(muster, was):
    m = re.search(muster, code)
    if m is None:
        check("gefunden: %s" % was, False)
        return None
    return m.start()


p_reissleine = pos(r"self\._notausgang_stellen\(\)", "Reissleine")
p_grab = pos(r"self\.inp\.grab\(False\)", "Griff loesen")
p_clear = pos(r"self\.fb\.clear\(", "Bildschirm leeren")
p_fbclose = pos(r"self\.fb\.close\(\)", "Framebuffer schliessen")
p_f12 = pos(r"self\.inp\.inject\(KEY_F12\)", "F12")
p_inpclose = pos(r"self\.inp\.close\(\)", "Eingaben schliessen")
p_konsole = pos(r"self\.konsole_cursor_an\(\)", "Konsole zurueck")
p_prewarm = pos(r"PREWARMER\.beenden\(\)", "Vorauslader beenden")
p_musik = pos(r"self\.music\.shutdown\(\)", "Musik beenden")

alle = [p_reissleine, p_grab, p_clear, p_fbclose, p_f12, p_inpclose,
        p_konsole, p_prewarm, p_musik]

print("Test 1: DIE REGEL - der Framebuffer ist weg, bevor F12 kommt")
if None not in (p_clear, p_fbclose, p_f12):
    check("Bildschirm wird VOR dem F12 geleert", p_clear < p_f12)
    check("fb.close() passiert VOR dem F12", p_fbclose < p_f12)
    check("nach dem F12 wird NICHTS mehr gezeichnet",
          "fb.clear" not in code[p_f12:] and "fb.flip" not in code[p_f12:])

print()
print("Test 2: was Build 162/163 gebracht hat, bleibt")
if None not in alle:
    check("die Reissleine steht als Allererstes",
          p_reissleine < min(p_grab, p_clear, p_f12))
    check("der Griff auf die Eingaben wird frueh geloest",
          p_grab < p_f12)
    check("die Eingaben werden erst NACH dem F12 geschlossen",
          p_inpclose > p_f12)
    check("die Konsole wird wiederhergestellt, bevor langsam "
          "aufgeraeumt wird", p_konsole < p_prewarm)
    check("das langsame Aufraeumen kommt zuletzt",
          p_prewarm > p_f12 and p_musik > p_f12)

print()
print("Test 3: nichts davon darf den Ausstieg blockieren")
check("das Freigeben des Framebuffers ist abgesichert",
      re.search(r"try:\s*\n\s*self\.fb\.clear\(", code) is not None)
check("eine fehlgeschlagene F12-Einspeisung wird nur protokolliert",
      "Exit-Injection fehlgeschlagen" in block)
check("die Reissleine hat eine Obergrenze",
      "HERUNTERFAHREN_MAX" in quelle)

# Der Notausgang selbst: ein daemon-Thread, der hart beendet.
i = quelle.index("    def _notausgang_stellen(self")
notausgang = quelle[i:i + 2500]
check("der Notausgang laeuft als daemon-Thread",
      "daemon=True" in notausgang)
check("er beendet den Prozess hart (os._exit)", "os._exit(" in notausgang)
check("er gibt vorher die Einzelinstanz frei",
      "release_single_instance()" in notausgang)

print()
print("Test 4: die zweite Haelfte derselben Sache - der Start")
# enter_console_mode() macht die Gegenrichtung (F9). Dort war die
# Reihenfolge immer richtig und soll es bleiben: Griff loesen, kurz
# warten, einspeisen.
j = quelle.index("    def enter_console_mode(self")
ecm = quelle[j:j + 800]
check("enter_console_mode loest den Griff vor dem F9",
      ecm.index("self.inp.grab(False)") < ecm.index("inject(KEY_F9)"))
check("und wartet dazwischen", "time.sleep(0.1)" in ecm)

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
