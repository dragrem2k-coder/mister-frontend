#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Die Dauerwache gegen den Login-Prompt (Build 157/158).

NUTZER-RUECKMELDUNG MIT BILDSCHIRMFOTO: "wenn ich spiele liste neu
einlesen machen springt der manchmal um in denn welcome to mister ...
auch so manchmal macht das frontend das im menue". Auf dem Foto steht
oben links, ueber unserem Bild:

    Welcome to MiSTer (www.MiSTerFPGA.org)
    login: _

ZWEI DINGE GREIFEN INEINANDER:

  1. Der Login-Prozess auf tty1 schreibt in denselben Framebuffer wie
     wir. Seit Build 150 bekannt - aber nur im STARTFENSTER behandelt,
     weil es dort als Folge des eingespeisten F9 galt.
  2. flip() kopiert das ganze Bild und wischt den Prompt mit weg. Im
     Ruhezustand laeuft aber meistens nur flip_rows() (Laufschrift,
     Uhr, Equalizer), und das fasst die obersten Zeilen nicht an.
     Genau dort steht der Prompt. Er bleibt also stehen, bis zufaellig
     ein voller Aufbau kommt.

WAS DIESER TEST VOR ALLEM ABSICHERT, IST NICHT DAS ERKENNEN, SONDERN
DAS NICHT-ERKENNEN. Build 151 hat der Nutzer gemeldet: "es geht aber
es flakert jetzt alle paar sekunden". Ursache damals: die Pruefung
fragte nur, ob mm und buf ungleich sind - und das sind sie auch mitten
in einem eigenen Bildaufbau. Eine Wache, die jede Sekunde nachsieht,
darf diesen Fehler nicht wiederholen.

Deshalb zaehlt _fremdausgabe_zaehlen() gerichtet: hell auf dem SCHIRM,
dunkel im GEZEICHNETEN Bild. Ein eigener halbfertiger Aufbau hat es
genau andersherum.

BUILD 158 kam dazu, nachdem ein Bildschirmvideo zeigte, dass beim
Scrollen ein kleiner Strich links oben aufblitzt - der CURSOR der
Textkonsole. Tests 8 und 9 decken ihn und die Rueckkehr aus einem
Script ab.

Ausfuehren:
    python3 tools/test_konsole_wache.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H                                        # noqa: E402

fm = H.fm
fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


def aufbau():
    f = H.make_frontend(page=0)
    f.draw()
    f.fb.mm[:] = f.fb.buf          # Schirm und Zeichnung sind gleich
    f._wache_naechste = 0.0
    f._wache_verdacht = 0
    f._gewischt = []
    f._konsole_wischen = lambda grund: f._gewischt.append(grund)
    return f


def prompt_schreiben(f, text=b"Welcome to MiSTer (www.MiSTerFPGA.org)"):
    """Weissen Text oben links DIREKT in den Schirm malen - so, wie es
    der Login-Prozess tut: an uns vorbei, nur in mm, nicht in buf."""
    punkte = 0
    for zeile in range(2):
        y = 4 + zeile * 10
        for i in range(len(text)):
            for dx in range(5):        # fuenf helle Punkte je Zeichen
                x = 2 + i * 6 + dx
                if x >= f.fb.width:
                    break
                for dy in range(3):
                    off = (y + dy) * f.fb.stride + x * 4
                    f.fb.mm[off:off + 4] = b"\xff\xff\xff\x00"
                    punkte += 1
    return punkte


def takten(f, sekunden):
    """Die Wache n-mal im eigenen Takt laufen lassen."""
    for _ in range(sekunden):
        f._konsole_wache()
        H.NOW[0] += fm.Frontend.KONSOLE_WACHE_TAKT


# ---------------------------------------------------------------------------
print("Test 1: ein sauberes Bild loest nichts aus")
# ---------------------------------------------------------------------------
f = aufbau()
check("nichts Fremdes gefunden", f._fremdausgabe_zaehlen() == 0,
      "%d Punkte" % f._fremdausgabe_zaehlen())
takten(f, 10)
check("zehn Sekunden Ruhe, kein einziges Wischen", f._gewischt == [],
      str(f._gewischt))

# ---------------------------------------------------------------------------
print()
print("Test 2: der Login-Prompt wird gefunden und weggewischt")
# ---------------------------------------------------------------------------
f = aufbau()
gemalt = prompt_schreiben(f)
gefunden = f._fremdausgabe_zaehlen()
check("die Fremdpunkte werden gezaehlt",
      gefunden >= fm.Frontend.KONSOLE_WACHE_MINDEST,
      "%d von %d gemalten, Schwelle %d"
      % (gefunden, gemalt, fm.Frontend.KONSOLE_WACHE_MINDEST))
f._konsole_wache()
check("beim ERSTEN Blick passiert noch nichts", f._gewischt == [],
      "einmal koennte ein halber Bildaufbau sein")
H.NOW[0] += fm.Frontend.KONSOLE_WACHE_TAKT
f._konsole_wache()
check("beim zweiten wird gewischt", len(f._gewischt) == 1,
      str(f._gewischt))

# ---------------------------------------------------------------------------
print()
print("Test 3: DAS FLACKERN VON BUILD 151 DARF NICHT WIEDERKEHREN")
# ---------------------------------------------------------------------------
# Ein halbfertiger eigener Aufbau: buf ist schon hell, mm noch alt.
# Genau diese Lage hat die alte Pruefung ("mm != buf") jedes Mal als
# Fremdausgabe gewertet - und der Nutzer sah alle paar Sekunden ein
# Zucken.
f = aufbau()
for y in range(20):
    off = y * f.fb.stride
    f.fb.buf[off:off + 400 * 4] = b"\xff\xff\xff\x00" * 400
check("mm und buf sind jetzt ungleich",
      bytes(f.fb.mm[:20 * f.fb.stride]) != bytes(f.fb.buf[:20 * f.fb.stride]))
check("die Wache wertet das NICHT als Fremdausgabe",
      f._fremdausgabe_zaehlen() == 0,
      "%d Punkte" % f._fremdausgabe_zaehlen())
takten(f, 10)
check("und wischt auch nach zehn Takten nicht", f._gewischt == [],
      str(f._gewischt))

# ---------------------------------------------------------------------------
print()
print("Test 4: ein paar helle Punkte reichen nicht")
# ---------------------------------------------------------------------------
# Ein einzelner verirrter Bildpunkt - etwa vom Mauszeiger des Kernels -
# darf keinen vollen Neuaufbau ausloesen.
f = aufbau()
for i in range(10):
    off = 5 * f.fb.stride + (20 + i) * 4
    f.fb.mm[off:off + 4] = b"\xff\xff\xff\x00"
check("zehn Punkte liegen unter der Schwelle",
      f._fremdausgabe_zaehlen() < fm.Frontend.KONSOLE_WACHE_MINDEST,
      "%d Punkte" % f._fremdausgabe_zaehlen())
takten(f, 6)
check("also wird nicht gewischt", f._gewischt == [], str(f._gewischt))

# ---------------------------------------------------------------------------
print()
print("Test 5: der Verdacht verfaellt, wenn er sich nicht bestaetigt")
# ---------------------------------------------------------------------------
# Ein Aufblitzen darf keinen Zaehler fuellen, der irgendwann spaeter
# zusammen mit einem zweiten Aufblitzen ausloest.
f = aufbau()
prompt_schreiben(f)
f._konsole_wache()                       # Verdacht 1
check("Verdacht ist vermerkt", f._wache_verdacht == 1)
f.fb.mm[:] = f.fb.buf                    # Prompt weg (voller flip)
H.NOW[0] += fm.Frontend.KONSOLE_WACHE_TAKT
f._konsole_wache()
check("sauberes Bild setzt den Verdacht zurueck", f._wache_verdacht == 0)
check("und es wurde nie gewischt", f._gewischt == [], str(f._gewischt))

# ---------------------------------------------------------------------------
print()
print("Test 6: die Wache haelt ihren Takt ein")
# ---------------------------------------------------------------------------
f = aufbau()
prompt_schreiben(f)
for _ in range(20):                      # zwanzig Schleifendurchlaeufe,
    f._konsole_wache()                   # aber keine Zeit vergeht
check("ohne vergehende Zeit bleibt es bei einem Blick",
      f._wache_verdacht == 1 and f._gewischt == [],
      "Verdacht %d, gewischt %s" % (f._wache_verdacht, f._gewischt))

# ---------------------------------------------------------------------------
print()
print("Test 7: die Wache haengt nicht mehr am Startfenster")
# ---------------------------------------------------------------------------
# Das war der eigentliche Fehler: _konsole_aufraeumen() steigt sofort
# aus, wenn _f9_aufraeumen_ab None ist - und das wird nur von
# _konsole_sichern() im Startfenster gesetzt. Danach raeumte niemand
# mehr auf, und genau das hat der Nutzer gemeldet.
f = aufbau()
f._f9_aufraeumen_ab = None               # Startfenster laengst vorbei
H.NOW[0] += 3600.0                       # eine Stunde spaeter
f._wache_naechste = 0.0
prompt_schreiben(f)
f._konsole_aufraeumen()
check("die alte Funktion allein tut nichts mehr", f._gewischt == [],
      str(f._gewischt))
f._konsole_wache()
H.NOW[0] += fm.Frontend.KONSOLE_WACHE_TAKT
f._konsole_wache()
check("die Wache raeumt trotzdem auf", len(f._gewischt) == 1,
      str(f._gewischt))
check("und nennt den Grund im Log", "Dauerwache" in (f._gewischt or [""])[0],
      str(f._gewischt))

# ---------------------------------------------------------------------------
print()
print("Test 8: der Cursor der Textkonsole (Build 158)")
# ---------------------------------------------------------------------------
# Im Bildschirmvideo des Nutzers blitzt beim Scrollen ein kleiner grauer
# Strich links oben auf - ausserhalb unseres Layouts, das erst bei x=112
# beginnt. Das ist der Cursor der Textkonsole.
#
# set_cursor_blink(False) allein genuegt NICHT: das schaltet nur das
# Blinken ab, der Cursor steht danach dauerhaft da. Das war die ganze
# Zeit ein Missverstaendnis im Code.
quelle = open(os.path.join(os.path.dirname(os.path.abspath(fm.__file__)),
                           "frontend.py"), encoding="utf-8").read()
check("es gibt eine Funktion, die den Cursor ausblendet",
      "def konsole_cursor_aus" in quelle)
check("sie schickt die richtige Sequenz (ESC[?25l)",
      "?25l" in quelle)
check("und es gibt ein Gegenstueck fuers Beenden",
      "def konsole_cursor_an" in quelle and "?25h" in quelle)
check("beim Start wird sie gerufen",
      "self.konsole_cursor_aus()" in quelle.split("self.inp.grab(True)")[0])
check("beim Beenden wird der Cursor wiederhergestellt",
      "self.konsole_cursor_an()" in quelle)
# Beim Wischen muss der Cursor mitgehen - sonst steht er sofort wieder
# oben links, die Wache schlaegt erneut an, und daraus wird das
# Flackern aus Build 151.
wisch = quelle.split("def _konsole_wischen")[1][:900]
check("das Wischen blendet den Cursor gleich mit aus", "?25l" in wisch,
      "sonst flackert es")

# ---------------------------------------------------------------------------
print()
print("Test 9: nach einem Script wird nachgefasst (Build 158)")
# ---------------------------------------------------------------------------
# Nutzer-Rueckmeldung: "wenn ich ueber frontend ein Script zum Beispiel
# Frontend_install ausgefuehrt hab ploppte der Welcome to misterfpga mit
# Login: auch auf". back_to_frontend() zeichnet zwar das ganze Bild neu
# und wischt damit alles weg - aber der Login-Prozess meldet sich ERST
# DANACH zurueck.
zurueck = quelle.split("def back_to_frontend")[1][:1400]
check("back_to_frontend setzt einen Nachfass-Termin",
      "_f9_aufraeumen_ab" in zurueck, zurueck[:80])
check("und blendet den Cursor aus", "konsole_cursor_aus" in zurueck)
check("der Termin liegt nicht sofort, sondern etwas spaeter",
      fm.Frontend.NACHFASSEN_SEK >= 0.5,
      "%.1f s" % fm.Frontend.NACHFASSEN_SEK)

f = aufbau()
f._f9_aufraeumen_ab = H.NOW[0] + fm.Frontend.NACHFASSEN_SEK
prompt_schreiben(f)
f._konsole_aufraeumen()
check("vor dem Termin passiert nichts", f._gewischt == [], str(f._gewischt))
H.NOW[0] += fm.Frontend.NACHFASSEN_SEK + 0.1
f._konsole_aufraeumen()
check("zum Termin wird gewischt", len(f._gewischt) == 1, str(f._gewischt))


# ---------------------------------------------------------------------------
print()
print("Test 10: die Bildschirmschonung der Konsole ist abgeschaltet (Build 160)")
# ---------------------------------------------------------------------------
# Vier Meldungen an vier Stellen ohne Gemeinsamkeit im Code: beim
# Neueinlesen, im System-Menue beim schnellen Scrollen, in der Galerie,
# nach einem Skript. Gemeinsam haben sie nur, dass eine Taste gedrueckt
# wird, nachdem laengere Zeit nichts passiert ist - das ist das
# Aufwachen aus der Konsolen-Abdunklung, und dabei zeichnet der Kernel
# den Konsoleninhalt (den Login-Gruss) neu.
check("es gibt eine Funktion dafuer", "def konsole_ruhig_stellen" in quelle)
ruhig = quelle.split("def konsole_ruhig_stellen")[1][:2600]
check("sie schaltet die Abdunklung ab (ESC[9;0])", "9;0" in ruhig, ruhig[-200:])
check("und das VESA-Abschalten (ESC[14;0])", "14;0" in ruhig)
check("beim Start wird sie gerufen", "self.konsole_ruhig_stellen()" in quelle)
boot = open(os.path.join(os.path.dirname(os.path.abspath(fm.__file__)),
                         "frontend_boot.sh"), encoding="utf-8").read()
check("das Boot-Skript macht dasselbe, bevor wir ueberhaupt laufen",
      "9;0" in boot and "?25l" in boot)
# Die Wache bleibt trotzdem - falls die Erklaerung falsch ist, steht es
# beim naechsten Mal im Log statt in einer Rueckfrage.
check("die Wache ist NICHT entfernt worden",
      "def _konsole_wache" in quelle and "self._konsole_wache()" in quelle)

# ---------------------------------------------------------------------------
print()
print("Test 11: Erfolge sind in JEDER Ansicht zu sehen (Build 160)")
# ---------------------------------------------------------------------------
# Nutzer-Rueckmeldung: "wenn ich erfolg freischalte wird dieser nur ueber
# denn sound signalisiert ... wenn ich dann noch mitten in einen rom
# ordner bin egal in welcher ansicht sieht man nichts".
#
# Die Fusszeilen-Meldung hat nicht jede Ansicht. Die hervorgehobene Box
# wird in draw() gezeichnet, nachdem die Seite steht - sie liegt ueber
# jeder Ansicht und jeder Ordnerebene.
melden = quelle.split("def _notify_new_achievements")[1][:1600]
check("die Erfolgsmeldung nimmt die hervorgehobene Box",
      "prominent=True" in melden, melden[-160:])
check("und steht laenger als eine normale Meldung",
      fm.Frontend.ERFOLG_BOX_SEK > 5.0,
      "%.1f s" % fm.Frontend.ERFOLG_BOX_SEK)
# Auch beim Favoriten- und Durchgespielt-Schalter: ein Erfolg ist
# wichtiger als die Bestaetigung "Favorit hinzugefuegt".
check("Favorit/Durchgespielt zeigen einen Erfolg ebenfalls als Box",
      quelle.count("prominent_duration=self.ERFOLG_BOX_SEK") >= 3,
      "%d Fundstellen" % quelle.count("prominent_duration=self.ERFOLG_BOX_SEK"))


# ---------------------------------------------------------------------------
print()
print("Test 12: der Ausstieg laesst MiSTer Zeit fuer das F12 (Build 162)")
# ---------------------------------------------------------------------------
# Nutzer-Rueckmeldung: "frontend beenden bekomme ich jetzt einen
# schwarzen bildschirm wo der _ am blinken ist".
#
# enter_console_mode() wartet nach seiner Tasteninjektion seit jeher
# 0,4 s. Der Ausstieg schickt dieselbe Taste ueber denselben Weg - und
# schloss das Eingabegeraet DIREKT danach. Kommt das F12 nicht an,
# bleibt der gerade geschwaerzte Bildspeicher stehen, und darauf
# blinkt der Konsolen-Cursor. Genau das gemeldete Bild.
# ANKER GEAENDERT (Build 165): hier stand der Wortlaut einer
# LOG-Zeile ('Exit: gebe Eingaben frei'). Build 165 hat genau diese
# Zeile umformuliert, weil dort jetzt auch der Bildschirm freigegeben
# wird - und der Test ging rot, obwohl das gepruefte Verhalten
# unveraendert richtig war. Ein Test darf nicht an einer Formulierung
# haengen. Jetzt derselbe Anker wie in Test 13: der Kommentarkopf des
# Blocks.
_h = quelle.split("HERUNTERFAHREN (umgestellt in Build 163)")[1]
# Bis zum Ende des finally-Blocks, nicht "die naechsten N Zeichen":
# der Kommentarkopf ist in Build 165 laenger geworden, und ein
# festes Fenster haette dann nur noch Kommentar enthalten.
_h = _h[:_h.index("\n    # Pause zwischen dem F12")]
ausstieg = _h
check("nach dem F12 wird gewartet, bevor geschlossen wird",
      "EXIT_NACH_F12_SEK" in ausstieg
      and ausstieg.index("EXIT_NACH_F12_SEK") < ausstieg.index("inp.close()"),
      "sonst kann MiSTer die Taste nicht mehr entgegennehmen")

# ---------------------------------------------------------------------------
print()
print("Test 13: die Eingaben werden VOR dem Aufraeumen freigegeben (Build 163)")
# ---------------------------------------------------------------------------
# Nutzer-Rueckmeldung: ueber System -> Wartung landet er im OSD, ueber
# Hauptseite -> Zurueck -> Beenden im schwarzen Bild, in dem keine
# Taste mehr etwas bewirkt. Beide Wege verlassen die Schleife ueber
# DASSELBE break - im Beenden-Code koennen sie sich nicht
# unterscheiden. Unterscheiden kann sich nur, welcher
# Hintergrundprozess gerade arbeitet.
#
# Und dort lag die Reihenfolge falsch: erst auf Vorauslader,
# Nachlader, Stream und Musik warten, DANN die Tastatur freigeben.
# Haengt eines davon, behaelt der Prozess den exklusiven Griff auf die
# Eingabegeraete - und nichts reagiert mehr.
# Anker ist der Kommentarkopf des Blocks - "finally:" kommt in der
# Datei mehrfach vor, und der letzte Treffer war der falsche.
block = _h
pos_frei = block.index("self.inp.close()")
for langsam in ("PREWARMER.beenden()", "self.lader.beenden()",
                "self.music.shutdown()"):
    check("Eingaben sind frei, bevor %s laeuft" % langsam,
          pos_frei < block.index(langsam), "sonst haengt das Geraet")
check("die Konsole wird ebenfalls vor dem Aufraeumen zurueckgesetzt",
      block.index("konsole_schonung_zurueck()") < block.index("PREWARMER.beenden()"),
      "sonst faellt es bei der Reissleine unter den Tisch")

# ---------------------------------------------------------------------------
print()
print("Test 14: es gibt eine Reissleine fuer ein haengendes Aufraeumen")
# ---------------------------------------------------------------------------
check("der Wachhund wird gestellt", "_notausgang_stellen()" in block)
check("und zwar als ALLERERSTES im finally",
      block.index("_notausgang_stellen()") < pos_frei)
wach = quelle.split("def _notausgang_stellen")[1][:1800]
check("er beendet den Prozess hart", "os._exit(0)" in wach)
check("gibt vorher die Sperrdatei frei", "release_single_instance" in wach,
      "sonst blockiert sie den naechsten Start")
check("laeuft als Daemon-Thread (haelt das Beenden nicht auf)",
      "daemon=True" in wach)
check("die Frist ist grosszuegig, aber endlich",
      2.0 < fm.Frontend.HERUNTERFAHREN_MAX < 30.0,
      "%.0f s" % fm.Frontend.HERUNTERFAHREN_MAX)
check("und zwar so lange wie beim Konsolenwechsel",
      fm.Frontend.EXIT_NACH_F12_SEK >= 0.4,
      "%.1f s" % fm.Frontend.EXIT_NACH_F12_SEK)
# Was wir beim Start abgeschaltet haben, muss beim Beenden zurueck -
# eine Konsole, die nie mehr abdunkelt, waere ein Rueckstand.
check("die Bildschirmschonung wird wieder eingeschaltet",
      "def konsole_schonung_zurueck" in quelle
      and "self.konsole_schonung_zurueck()" in quelle)
zurueck = quelle.split("def konsole_schonung_zurueck")[1][:900]
check("und zwar auf einen echten Wert, nicht wieder auf null",
      "9;10" in zurueck, zurueck[-120:])


print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
