#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Der ROM-Waechter liest von selbst nach - und das Pad wird schneller
gefunden (Build 296).

ZWEI NUTZERWUENSCHE

1. "kannst du bitte noch einrichten das wenn ich neue roms drauf
   kopiere, sagt mir der rom waechter ja bescheid, das auch automatisch
   aktualisiert wird? ist bloede es immer per hand erst durchlaufen zu
   lassen fuer das jeweilige system wo was neu gekommen ist!"

2. "ausserdem ist mir aufgefallen das mein joypad 8bitdo manchmal erst
   Recht spaet nach einen Neustart oder Kaltstart reagiert oder lagt"

WAS BEIM ERSTEN UMGEDREHT WURDE, UND WARUM DAS ERLAUBT IST

Build 258 hat das automatische Nachlesen ausdruecklich NICHT gebaut:

    "Das dauert bei einer grossen Sammlung Sekunden bis Minuten, und
    mitten im Scrollen waere es ein sichtbarer Haenger. Es ist
    ausserdem eine Entscheidung des Nutzers und keine des Programms."

Der erste Satz war zu vorsichtig, und das steht im Code: scan_games()
vergleicht seit Build 248 den Fingerabdruck JE SYSTEM und liest alles
Unveraenderte aus dem Zwischenspeicher. Nachgelesen wird also EIN
System - genau das, was der Nutzer heute von Hand anstoesst.

Der zweite Satz bleibt richtig, deshalb der Schalter. Und "mitten im
Scrollen" ist der Grund fuer die vier Bedingungen, die dieser Test
einzeln durchgeht.

DIE WICHTIGSTE BEDINGUNG IST NICHT DIE NAHELIEGENDE: wer ROMs ueber
WinSCP oder das Netz kopiert, aendert den Ordner WAEHREND des Kopierens
immer weiter. Sofort nachzulesen hiesse, in einen halb fertigen Ordner
zu lesen. Deshalb beginnt die Frist erst, wenn ein ganzer Waechterblick
KEINE weitere Aenderung mehr gesehen hat.

Ausfuehren:
    python3 tools/test_rom_auto.py
"""
import ast
import os
import sys

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
    """Der Koerper genau einer Funktion, per ast, ohne Kommentarzeilen.

    Die lange Begruendung steht in tools/test_startweg.py: Zeichen-
    fenster und Textsuche sind in diesem Projekt mehrfach daneben-
    gegangen, und ein gesuchter Begriff steht oft auch in der
    ERKLAERUNG daneben."""
    baum = ast.parse(quelle)
    zeilen = quelle.split("\n")
    wurzel = baum
    if klasse is not None:
        for k in baum.body:
            if isinstance(k, ast.ClassDef) and k.name == klasse:
                wurzel = k
                break
        else:
            return ""
    for k in wurzel.body:
        if isinstance(k, ast.FunctionDef) and k.name == name:
            return "\n".join(z for z in zeilen[k.lineno - 1:k.end_lineno]
                             if not z.lstrip().startswith("#"))
    return ""


def nur_code(quelle):
    """Die Datei ohne Kommentarzeilen - siehe test_bildarten.py."""
    return "\n".join(z for z in quelle.split("\n")
                     if not z.lstrip().startswith("#"))


FE_PY = os.path.join(_REPO, "frontend", "frontend.py")
fe_src = open(FE_PY, encoding="utf-8").read()
fe_code = nur_code(fe_src)
set_src = open(os.path.join(_REPO, "frontend", "fe", "settings.py"),
               encoding="utf-8").read()
menu_src = open(os.path.join(_REPO, "frontend", "fe", "menu.py"),
                encoding="utf-8").read()
tr_src = open(os.path.join(_REPO, "frontend", "fe", "translations.py"),
              encoding="utf-8").read()

print(__doc__.strip().split("\n")[0])
print()

# ---------------------------------------------------------------- 1
print("Test 1: der Schalter, und seine Vorgabe")

check("es gibt romwacht_auto_an()", "def romwacht_auto_an()" in set_src)
check("und einen Umschalter", "def toggle_romwacht_auto()" in set_src)
# VORGABE AN: er hat danach gefragt. Die Abwesenheit der Datei heisst
# "an" - dieselbe Bauweise wie beim Waechter selbst.
check("Vorgabe ist AN (die Datei schaltet AUS)",
      'ROMWACHT_AUTO_AUS_FLAG = "/media/fat/frontend/romwacht_auto_aus"'
      in set_src
      and "return not _hole((\"romwacht_auto_aus\"" in set_src)
check("der Schalter des Waechters bleibt daneben bestehen",
      "def romwacht_an()" in set_src and "def toggle_romwacht()" in set_src,
      "der neue ist dessen Folge, nicht sein Ersatz")

print()

# ---------------------------------------------------------------- 2
print("Test 2: der Menuepunkt erscheint nur, wenn der Waechter an ist")

check("der Punkt ist definiert",
      '"romwacht_auto"' in menu_src)
check("und haengt am Waechter-Schalter",
      "if romwacht_an() else []" in menu_src,
      "ein Menuepunkt ohne Wirkung war Build 284 ein Fehlerbericht")
check("das Frontend verarbeitet ihn",
      'elif kind == "romwacht_auto":' in fe_src)
# Beim Abschalten muss das Vorgemerkte weg - sonst kommt das
# Nachlesen beim naechsten Einschalten aus dem Nichts.
_zweig = fe_src[fe_src.find('elif kind == "romwacht_auto":'):]
_zweig = _zweig[:_zweig.find('self._refresh_system_category()') + 40]
check("und verwirft beim Abschalten das Vorgemerkte",
      "_rom_auto_offen = None" in _zweig, _zweig.count("None"))

print()

# ---------------------------------------------------------------- 3
print("Test 3: zwei Fassungen der Meldung")

for k in ("rom_geaendert", "rom_geaendert_auto", "rom_nachgelesen",
          "sys_romwacht_auto_an", "sys_romwacht_auto_aus"):
    check("Text '%s' steht zweisprachig im Katalog" % k,
          ('"%s"' % k) in tr_src
          and tr_src.count('"%s"' % k) >= 1)
# DIE ALTE MELDUNG SAGT, WAS DER NUTZER TUN SOLL ("System -> nur
# Geaendertes nachlesen"). Bei automatischem Nachlesen waere das eine
# Anweisung zu etwas, das von selbst passiert.
check("die Meldung haengt am Schalter",
      'if romwacht_auto_an()' in fe_src
      and 'rom_geaendert_auto' in fe_src)

print()

# ---------------------------------------------------------------- 4
print("Test 4: die vier Bedingungen - ausgefuehrt, nicht gelesen")

# AUSGEFUEHRT heisst: die echte Methode wird aufgerufen, mit einer
# Attrappe als self. Ein Test, der nur Zeichen im Quelltext zaehlt,
# hat in diesem Projekt schon mehrfach das Falsche bestaetigt.
import _harness as H                                      # noqa: E402

pruef = koerper(fe_src, "_rom_nachscan_pruefen", klasse="Frontend")
check("_rom_nachscan_pruefen() ist gefunden", bool(pruef))

FE = H.fm.Frontend
pruefen = FE._rom_nachscan_pruefen
JETZT = H.fm.time.monotonic()          # der Pruefstand friert die Uhr ein


class Attrappe(object):
    """Nur die Felder, die _rom_nachscan_pruefen() anfasst.

    Kein echtes Frontend: dessen Konstruktor oeffnet Bildspeicher und
    Eingabegeraete, spielt ein F9 ein und startet Faeden - in einem
    Test hat das nichts zu suchen."""

    ROM_AUTO_BERUHIGUNG = FE.ROM_AUTO_BERUHIGUNG
    ROM_AUTO_RUHE = FE.ROM_AUTO_RUHE

    def __init__(self, offen="SNES", ruhig_vor=99.0, page=0,
                 eingabe_vor=99.0):
        self._rom_auto_offen = offen
        self._rom_auto_ruhig_ab = (None if ruhig_vor is None
                                   else JETZT - ruhig_vor)
        self.page = page
        self._last_input_time = JETZT - eingabe_vor
        self._nachscan_grund = "SNES"
        self._nachscan_rom = True
        self._force_full_redraw = False
        self._popup_message = None
        self._popup_message_until = 0.0
        self.neu_gebaut = 0
        self.gemerkt = 0
        self._romwacht = self

    def _rebuild_categories_preserving_selection(self):
        self.neu_gebaut += 1

    def _beobachtete_ordner(self):
        return ()

    def merken(self, _pfade):
        self.gemerkt += 1


_echt_rw_an = H.fm.romwacht_an
_echt_auto_an = H.fm.romwacht_auto_an
H.fm.romwacht_an = lambda: True
H.fm.romwacht_auto_an = lambda: True
try:
    # 4a) Alles erfuellt -> es wird nachgelesen.
    a = Attrappe()
    pruefen(a)
    check("alle Bedingungen erfuellt: es wird nachgelesen",
          a.neu_gebaut == 1, "%d Neuaufbauten" % a.neu_gebaut)
    check("und der Waechter merkt sich den neuen Stand",
          a.gemerkt == 1,
          "ohne das meldet er dieselbe Aenderung beim naechsten Blick "
          "wieder (siehe pruefen() in fe/romwacht.py)")
    check("das Vorgemerkte ist verbraucht",
          a._rom_auto_offen is None and a._rom_auto_ruhig_ab is None)
    check("und der Menuepunkt-Hinweis ebenfalls",
          a._nachscan_grund is None and a._nachscan_rom is False,
          "sonst stuende im Systemmenue weiter 'nachlesen', obwohl "
          "nichts mehr offen ist")
    check("gemeldet wird ueber die Einblendung",
          a._popup_message is not None and a._popup_message_until > 0,
          str(a._popup_message))
    check("und ein voller Neuaufbau des Bildes ist angesetzt",
          a._force_full_redraw is True)

    # 4b) DIE WICHTIGSTE BEDINGUNG: es aendert sich noch etwas.
    #     ruhig_ab=None heisst "der letzte Blick hat wieder eine
    #     Aenderung gesehen" - also kopiert jemand noch.
    a = Attrappe(ruhig_vor=None)
    pruefen(a)
    check("waehrend noch kopiert wird: nichts",
          a.neu_gebaut == 0,
          "sonst liest man in einen halb fertigen Ordner")
    check("und das Vorgemerkte bleibt stehen",
          a._rom_auto_offen == "SNES")

    # 4c) Beruhigung noch nicht abgelaufen.
    a = Attrappe(ruhig_vor=FE.ROM_AUTO_BERUHIGUNG - 0.5)
    pruefen(a)
    check("Beruhigungsfrist noch nicht um: nichts", a.neu_gebaut == 0)

    # 4d) Eingabe nicht ruhig.
    a = Attrappe(eingabe_vor=FE.ROM_AUTO_RUHE - 0.5)
    pruefen(a)
    check("Eingabe noch nicht ruhig: nichts", a.neu_gebaut == 0,
          "der Neuaufbau ist nicht billig und niemand hat ihn "
          "angefordert")

    # 4e) Nicht auf Seite 0. Dieselbe Regel wie beim RA-Neuaufbau:
    #     steht der Nutzer in einer Kategorie, passt der Ordnerpfad
    #     nach einem Neuaufbau nicht mehr zum Baum.
    a = Attrappe(page=1)
    pruefen(a)
    check("in einer Kategorie: nichts", a.neu_gebaut == 0)
    check("aber vorgemerkt bleibt es", a._rom_auto_offen == "SNES",
          "es wird nachgeholt, sobald er wieder auf Seite 0 ist")

    # 4f) Gar nichts vorgemerkt -> keine Arbeit.
    a = Attrappe(offen=None)
    pruefen(a)
    check("ohne Meldung passiert nichts", a.neu_gebaut == 0)

    # 4g) Schalter aus: nichts tun UND das Vorgemerkte verwerfen.
    H.fm.romwacht_auto_an = lambda: False
    a = Attrappe()
    pruefen(a)
    check("Schalter aus: es wird nicht nachgelesen", a.neu_gebaut == 0)
    check("und das Vorgemerkte wird verworfen",
          a._rom_auto_offen is None,
          "liegen lassen waere ein Nachlesen, das beim naechsten "
          "Einschalten aus dem Nichts kommt")
    # Und derselbe Fall ueber den Waechter-Schalter.
    H.fm.romwacht_auto_an = lambda: True
    H.fm.romwacht_an = lambda: False
    a = Attrappe()
    pruefen(a)
    check("Waechter aus: ebenfalls nichts, ebenfalls verworfen",
          a.neu_gebaut == 0 and a._rom_auto_offen is None)
finally:
    H.fm.romwacht_an = _echt_rw_an
    H.fm.romwacht_auto_an = _echt_auto_an

print()

# ---------------------------------------------------------------- 5
print("Test 5: der Neuaufbau erhaelt die Position")

# DIE MENUEAKTION setzt cat_i/item_i/page/nav_path auf null zurueck -
# beim bewussten Ausloesen richtig, bei einem automatischen Vorgang
# waere es ein Sprung aus dem Nichts.
check("genommen wird der Neuaufbau MIT Positionserhalt",
      "_rebuild_categories_preserving_selection()" in pruef)
check("und NICHT die Menueaktion mit ihrem Nullsetzen",
      "self.cat_i = self.item_i = 0" not in pruef
      and "self.nav_path = []" not in pruef,
      "dieselbe Ruecksicht wie beim RA-Neuaufbau in Build 274")
# force_rescan bleibt aus: nur das Geaenderte wird gelesen, der Rest
# kommt aus dem Zwischenspeicher. DAS ist der Grund, warum der
# Einwand von Build 258 ('Sekunden bis Minuten') hier nicht greift.
check("ohne force_rescan - nur das Geaenderte",
      "force_rescan" not in pruef,
      "scan_games() vergleicht die Signatur je System (Build 248)")
# Ein automatischer Vorgang darf nichts umbringen, was ohne ihn lief.
check("ein Fehlschlag wird abgefangen",
      "except Exception" in pruef and "traceback.format_exc()" in pruef)

print()

# ---------------------------------------------------------------- 6
print("Test 6: er laeuft in der Hausarbeit, nicht im Zeichenweg")

# _hausarbeit_jetzt() laesst die Liste aus, solange eine Taste
# GEHALTEN wird (Build 273/276). Genau das ist die Zusage, die ein
# Neuaufbau braucht.
check("der Aufruf steht in der Hausarbeit-Liste",
      '("rom_auto", self._rom_nachscan_pruefen)' in fe_src)
_haus = koerper(fe_src, "draw", klasse="Frontend")
check("und die Liste haengt hinter _hausarbeit_jetzt()",
      "_hausarbeit_jetzt(" in _haus
      and _haus.find("_hausarbeit_jetzt(")
      < _haus.find('("rom_auto"'))

print()

# ---------------------------------------------------------------- 7
print("Test 7: das Pad wird schneller gefunden, solange keines da ist")

import fe.input as I                                      # noqa: E402

check("es gibt den kurzen Takt",
      hasattr(I.InputManager, "RESCAN_OHNE_PAD"))
check("und er ist deutlich kuerzer als der normale",
      I.InputManager.RESCAN_OHNE_PAD < I.InputManager.RESCAN_EVERY,
      "%.2f s gegen %.2f s" % (I.InputManager.RESCAN_OHNE_PAD,
                               I.InputManager.RESCAN_EVERY))


class FakeDev(object):
    def __init__(self, kbd):
        self.is_kbd = kbd


im = I.InputManager.__new__(I.InputManager)
im.devices = {}
check("ohne Geraet: kurzer Takt",
      im._rescan_takt() == I.InputManager.RESCAN_OHNE_PAD)
im.devices = {"/dev/input/event0": FakeDev(True)}
check("nur Tastatur: weiter kurzer Takt",
      im._rescan_takt() == I.InputManager.RESCAN_OHNE_PAD,
      "wer ein Pad einschaltet, soll nicht drei Sekunden warten")
im.devices["/dev/input/event1"] = FakeDev(False)
check("sobald ein Pad da ist: normaler Takt",
      im._rescan_takt() == I.InputManager.RESCAN_EVERY,
      "der kurze Takt endet von selbst")

# UND DIE STELLEN, DIE IHN BENUTZEN. Bliebe eine auf der festen Zahl,
# waere der kurze Takt dort ohne Wirkung - und zwar ohne dass es
# auffaellt.
inp_code = nur_code(open(os.path.join(_REPO, "frontend", "fe",
                                      "input.py"),
                         encoding="utf-8").read())
check("keine Wartezeit haengt mehr an der festen Zahl",
      "self.RESCAN_EVERY" not in inp_code.replace(
          "return self.RESCAN_EVERY", ""),
      "bis auf die eine Stelle in _rescan_takt() selbst")
check("und der Takt wird mehrfach abgefragt",
      inp_code.count("_rescan_takt()") >= 4,
      "%d Stellen" % inp_code.count("_rescan_takt()"))

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
