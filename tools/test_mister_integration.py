#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MiSTer-nahe Integration: Favoriten, update_all, Speicher (Build 213).

DREI DINGE, DIE ALLE DENSELBEN MiSTer ANFASSEN und deshalb dieselben
zwei Regeln einhalten muessen:

  1. Nichts davon darf im ZEICHENWEG passieren. Alles ist
     Einlese- oder Leerlaufarbeit.
  2. Nichts davon darf eine zweite Quelle der Wahrheit fuer Dateien
     auf der Karte schaffen - das ist die Regel, die fe/cores.py seit
     Build 174 ausdruecklich aufstellt.

WAS DIESER TEST ABSICHERT

  Favoriten (fe/mister_favs.py):
    - beide Pfadschreibweisen einer .mgl werden richtig aufgeloest,
      auch die unsere mit fuenf "../" vor einem absoluten Pfad (daran
      ist der erste Entwurf gescheitert),
    - eine kaputte oder fremde .mgl wird uebersprungen, nicht
      verweigert,
    - die Eintraege haben GENAU die Form einer normalen Spieleliste -
      nur so funktionieren Boxart, Spielzeit und RA an ihnen,
    - das System wird aus Ordner UND Endung bestimmt, nicht geraten.

  update_all (fe/mister_system.py):
    - es wird nur gestartet, nie nachgebaut,
    - die Beschriftung sagt in allen drei Faellen die Wahrheit.

  Speicher-Waechter:
    - meldet eine Aenderung genau einmal,
    - meldet NICHTS, wenn /media nicht lesbar ist,
    - liest nicht von selbst neu ein,
    - und wird nur im Leerlaufzweig gerufen.
"""
import inspect
import os
import shutil
import sys
import tempfile

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
sys.path.insert(0, os.path.join(_REPO, "frontend"))

import fe.mister_favs as MFAV                             # noqa: E402
import fe.mister_system as MSYS                           # noqa: E402
from fe.systems import GAME_SYSTEMS                       # noqa: E402

fails = []


def check(name, ok, extra=""):
    print("  %s %s%s" % ("OK  " if ok else "FEHL", name,
                         ("  (%s)" % extra) if extra else ""))
    if not ok:
        fails.append(name + ((" - " + extra) if extra else ""))


TMP = tempfile.mkdtemp(prefix="dragend_mister_")


def mgl(ordner, name, inhalt):
    with open(os.path.join(ordner, name), "w") as f:
        f.write(inhalt)


# ---------------------------------------------------------------------------
print("Test 1: der Favoritenordner wird gefunden, aber nicht erfunden")
# ---------------------------------------------------------------------------
MFAV.BASE = TMP
check("ohne Ordner liefert fav_ordner() None", MFAV.fav_ordner() is None)
check("und favoriten_lesen() eine leere Liste",
      MFAV.favoriten_lesen(GAME_SYSTEMS) == [])
FAV = os.path.join(TMP, "_@Favorites")
os.makedirs(FAV)
check("mit Ordner wird er gefunden", MFAV.fav_ordner() == FAV)
check("mehrere Schreibweisen sind vorgesehen",
      len(MFAV.FAV_ORDNER_KANDIDATEN) >= 2,
      repr(MFAV.FAV_ORDNER_KANDIDATEN))

# ---------------------------------------------------------------------------
print()
print("Test 2: die Pfadaufloesung - hier ist der erste Entwurf gescheitert")
# ---------------------------------------------------------------------------
# write_mgl() setzt FUENF ".." vor einen ABSOLUTEN Pfad. Zaehlt man die
# "../" als Zeichenketten weg, frisst das fuenfte den Schraegstrich mit,
# und der Favorit zeigt still ins Nichts.
faelle = [
    ("../../../../../media/fat/games/SNES/Spiel.sfc",
     "/media/fat/games/SNES/Spiel.sfc", "unsere eigene Schreibweise (5x ..)"),
    ("../../media/fat/games/NES/Spiel.nes",
     "/media/fat/games/NES/Spiel.nes", "andere Tiefe (2x ..)"),
    ("../media/usb0/games/GBA/Spiel.gba",
     "/media/usb0/games/GBA/Spiel.gba", "USB, eine Ebene"),
    ("..\\..\\media\\fat\\games\\N64\\Spiel.z64",
     "/media/fat/games/N64/Spiel.z64", "Backslashes"),
]
for roh, soll, wie in faelle:
    ist = MFAV.pfad_aus_mgl(roh, "/irgendwo")
    check("%-34s -> %s" % (wie, soll), ist == soll, "ist %r" % ist)
# Ohne ".." ist es wirklich relativ zum Ordner der .mgl.
check("ohne .. relativ zum mgl-Ordner",
      MFAV.pfad_aus_mgl("games/GBA/X.gba", "/media/fat/_@Favorites")
      == "/media/fat/_@Favorites/games/GBA/X.gba")
check("leeres Attribut ergibt None", MFAV.pfad_aus_mgl("", "/x") is None)
check("nur Punkte ergeben None", MFAV.pfad_aus_mgl("../..", "/x") is None)

# ---------------------------------------------------------------------------
print()
print("Test 3: kaputte .mgl uebersprungen, gute gelesen")
# ---------------------------------------------------------------------------
mgl(FAV, "gut.mgl",
    '<mistergamedescription>\n\t<rbf>_Console/SNES</rbf>\n'
    '\t<file delay="2" type="f" index="0" '
    'path="../../../../../media/fat/games/SNES/Super Test.sfc"/>\n'
    '</mistergamedescription>\n')
mgl(FAV, "einfach_quotes.mgl",
    "<mistergamedescription><rbf>_Console/NES</rbf>"
    "<file delay='1' type='f' index='7' "
    "path='../../media/fat/games/NES/Beispiel.nes'/></mistergamedescription>")
mgl(FAV, "kaputt.mgl", "<kaputt/>")
mgl(FAV, "leer.mgl", "")
mgl(FAV, "ohne_pfad.mgl", "<mistergamedescription><rbf>_Console/SNES</rbf>"
                          "</mistergamedescription>")
mgl(FAV, "fremdes_system.mgl",
    '<mistergamedescription><rbf>_Console/XYZ</rbf>'
    '<file path="../../media/fat/games/XYZ/Unbekannt.xyz"/>'
    '</mistergamedescription>')
mgl(FAV, "keine_mgl.txt", "steht hier nur so rum")

items = MFAV.favoriten_lesen(GAME_SYSTEMS)
namen = sorted(i[0] for i in items)
check("zwei brauchbare Eintraege", len(items) == 2, repr(namen))
check("und zwar die richtigen", namen == ["Beispiel", "Super Test"],
      repr(namen))
check("eine Nicht-mgl wird nicht angefasst", "keine_mgl" not in namen)
check("ein unbekanntes System wird ausgelassen - lieber ein Favorit "
      "weniger als der falsche Core", "Unbekannt" not in namen)

# ---------------------------------------------------------------------------
print()
print("Test 4: die Eintraege haben die Form einer normalen Spieleliste")
# ---------------------------------------------------------------------------
# Das ist die eigentliche Zusage: nur in dieser Form funktionieren
# Boxart, Beschreibung, Spielzeit, RA und Start ohne einen einzigen
# Sonderfall. Vergleichsmass ist load_recent() in fe/game_state.py:
# [(label, "game", arg)] mit arg = (rom, ext, syskey, rbf, (dl, ft, ix)).
for name, kind, arg in items:
    check("%-12s kind ist 'game'" % name, kind == "game", kind)
    check("%-12s arg hat fuenf Felder" % name,
          isinstance(arg, tuple) and len(arg) == 5, repr(arg))
    rom, ext, syskey, rbf, dfi = arg
    check("%-12s ROM-Pfad ist absolut" % name, rom.startswith("/"), rom)
    check("%-12s Endung passt zum Pfad" % name,
          ext == os.path.splitext(rom)[1].lower(), "%r / %r" % (ext, rom))
    check("%-12s syskey ist gesetzt" % name, bool(syskey), repr(syskey))
    check("%-12s rbf ist gesetzt" % name, bool(rbf), repr(rbf))
    check("%-12s (delay, typ, index) ist ein Dreier" % name,
          isinstance(dfi, tuple) and len(dfi) == 3, repr(dfi))

# Die Werte kommen aus der SYSTEMTABELLE, nicht aus der .mgl - die
# .mgl kann von einem beliebigen Werkzeug stammen.
nes = [i for i in items if i[0] == "Beispiel"][0]
soll = dict((s[1], s) for s in GAME_SYSTEMS)["NES"]
check("delay/typ/index kommen aus der Systemtabelle, nicht aus der .mgl",
      nes[2][4] == soll[4][".nes"],
      "%r gegen %r (die .mgl sagte index=7)" % (nes[2][4], soll[4][".nes"]))
check("und der rbf ebenfalls - nur so greifen Core-Wahl und RA-Core",
      nes[2][3] == soll[3], "%r gegen %r" % (nes[2][3], soll[3]))
q = inspect.getsource(MFAV.favoriten_lesen)
check("der Grund dafuer steht im Quelltext",
      "aufloesen()" in q and "RA-Core" in q)

# Notbremse gegen einen Ordner mit Tausenden Dateien.
check("es gibt eine Obergrenze", "hoechstens" in q)
check("und sie wirkt", len(MFAV.favoriten_lesen(GAME_SYSTEMS,
                                                hoechstens=1)) <= 1)

# ---------------------------------------------------------------------------
print()
print("Test 5: update_all wird gestartet, nicht nachgebaut")
# ---------------------------------------------------------------------------
SCR = os.path.join(TMP, "Scripts")
os.makedirs(SCR)
MSYS.SCRIPTS_DIR = SCR
check("ohne Skript liefert update_all_pfad() None",
      MSYS.update_all_pfad() is None)
ua = os.path.join(SCR, "update_all.sh")
open(ua, "w").write("#!/bin/sh\n")
check("mit Skript wird es gefunden", MSYS.update_all_pfad() == ua)

check("heute sind null Tage", MSYS.tage_seit(1000.0, jetzt=1000.0) == 0)
check("86400 Sekunden sind ein Tag",
      MSYS.tage_seit(1000.0, jetzt=1000.0 + 86400) == 1)
check("ohne Zeitpunkt kein Ergebnis", MSYS.tage_seit(None) is None)
check("keine negativen Tage (Uhr nachgestellt)",
      MSYS.tage_seit(2000.0, jetzt=1000.0) == 0)

MSYS.UPDATE_ALL_SPUREN = (os.path.join(TMP, "gibtsnicht"),)
check("ohne Protokoll wird nichts behauptet",
      MSYS.update_all_letzter_lauf() is None)
spur = os.path.join(TMP, "ua.log")
open(spur, "w").write("x")
MSYS.UPDATE_ALL_SPUREN = (os.path.join(TMP, "gibtsnicht"), spur)
check("mit Protokoll kommt ein Zeitpunkt",
      MSYS.update_all_letzter_lauf() is not None)

# Das Wichtigste: es wird NICHT selbst aktualisiert.
qm = inspect.getsource(MSYS)
for verboten in ("urlopen", "urllib", "requests", "socket"):
    check("mister_system.py benutzt kein %s" % verboten, verboten not in qm)
check("und der Grund steht dabei",
      "zweite Quelle der Wahrheit" in qm)

fe_quelle = open(os.path.join(_REPO, "frontend", "frontend.py"),
                 encoding="utf-8").read()
i_ua = fe_quelle.find('elif kind == "update_all":')
check("die Aktion gibt es", i_ua > 0)
# BIS ZUM NAECHSTEN ZWEIG, NICHT 1400 ZEICHEN WEIT (korrigiert in Build
# 250). Hier stand fe_quelle[i_ua:i_ua + 1400], und das ist eine
# Zusage, die vom LAYOUT abhaengt statt von der Sache: Build 250 hat
# dem Zweig den Core-Vergleich hinzugefuegt, damit sind
# "self.run_script(" und der Fehlerfall aus dem Fenster gerutscht, und
# der Test wurde rot, obwohl beides unveraendert da steht.
#
# Dasselbe Muster, das dieses Projekt schon mehrfach bezahlt hat:
# Build 244 bei den Kommentaren, Build 249 bei der Stoppuhr. Eine
# Pruefung muss an dem haengen, was sie behauptet - hier also am
# Zweig, und der endet beim naechsten "elif kind ==".
block = fe_quelle[i_ua:]
_ende = block.find("elif kind ==", 10)
if _ende > 0:
    block = block[:_ende]
check("sie benutzt den vorhandenen Skript-Starter",
      "self.run_script(" in block)
check("und prueft vorher, ob das Skript noch da ist",
      "update_all_pfad()" in block)
check("fehlt es, wird es dem Nutzer gesagt",
      "sys_update_all_fehlt" in block)

# ---------------------------------------------------------------------------
print()
print("Test 6: der Speicher-Waechter meldet einmal und liest nicht neu ein")
# ---------------------------------------------------------------------------
w = MSYS.SpeicherWaechter()
w.merken(frozenset(["fat", "usb0"]))
MSYS.eingehaengt = lambda: frozenset(["fat", "usb0"])
check("ohne Aenderung keine Meldung", w.pruefen(jetzt=100.0) is None)
MSYS.eingehaengt = lambda: frozenset(["fat", "usb0", "usb1"])
meldung = w.pruefen(jetzt=100.0 + MSYS.MOUNT_TAKT)
check("eine Aenderung wird gemeldet", meldung is not None, repr(meldung))
check("und sie nennt, was dazukam", meldung and "usb1" in meldung,
      repr(meldung))
check("dieselbe Aenderung nur EINMAL",
      w.pruefen(jetzt=100.0 + 3 * MSYS.MOUNT_TAKT) is None)
MSYS.eingehaengt = lambda: frozenset(["fat"])
m2 = w.pruefen(jetzt=100.0 + 5 * MSYS.MOUNT_TAKT)
check("eine NEUE Aenderung wieder", m2 is not None, repr(m2))
check("und sie nennt, was wegfiel", m2 and "usb0" in m2, repr(m2))

# Der Takt muss wirken - sonst waere es ein Dateisystemzugriff je Bild.
w2 = MSYS.SpeicherWaechter()
w2.merken(frozenset(["fat"]))
rufe = [0]


def _zaehl():
    rufe[0] += 1
    return frozenset(["fat"])


MSYS.eingehaengt = _zaehl
for i in range(50):
    w2.pruefen(jetzt=200.0 + i * 0.02)      # 50 Aufrufe in einer Sekunde
check("50 Aufrufe in einer Sekunde -> hoechstens 2 Blicke auf /media",
      rufe[0] <= 2, "%d Blicke" % rufe[0])
print("    Takt: %.1f s, %d Blicke bei 50 Aufrufen"
      % (MSYS.MOUNT_TAKT, rufe[0]))

# Unlesbares /media darf NICHTS melden.
w3 = MSYS.SpeicherWaechter()
w3.merken(frozenset(["fat", "usb0"]))
MSYS.eingehaengt = lambda: None
check("unlesbares /media meldet nichts",
      w3.pruefen(jetzt=300.0) is None)

# Und der Waechter liest nicht von selbst neu ein.
qw = inspect.getsource(MSYS.SpeicherWaechter)
for verboten in ("scan_games", "build_categories", "rescan"):
    check("der Waechter ruft kein %s" % verboten, verboten not in qw)
check("der Grund steht im Modulkopf",
      "entscheiden tut der Mensch" in qm)

# ---------------------------------------------------------------------------
print()
print("Test 7: nichts davon im Zeichenweg")
# ---------------------------------------------------------------------------
zeilen = [z.strip() for z in fe_quelle.split("\n")]
check("der Waechter wird genau einmal gerufen",
      zeilen.count("_sp = self._speicher.pruefen()") == 1,
      str(zeilen.count("_sp = self._speicher.pruefen()")))
i_sp = fe_quelle.find("_sp = self._speicher.pruefen()")
umfeld = fe_quelle[max(0, i_sp - 1200):i_sp + 400]
check("im Leerlaufzweig, erkennbar an den Marken daneben",
      "marken_nachziehen()" in umfeld)
check("und in einem try, damit er den Betrieb nie stoert",
      "except Exception" in umfeld)
check("der Stand wird nach JEDEM Einlesen gemerkt",
      fe_quelle.count("self._speicher.merken()") == 2,
      "%d Aufrufe" % fe_quelle.count("self._speicher.merken()"))
# Die Favoriten werden beim Einlesen gelesen, nicht beim Zeichnen.
i_mf = fe_quelle.find("MFAV.favoriten_lesen(")
check("die Favoriten werden genau einmal gelesen",
      fe_quelle.count("MFAV.favoriten_lesen(") == 1)
check("und zwar beim Aufbau der Kategorien",
      "_favoriten_vereinen(" in fe_quelle[i_mf:i_mf + 900])
check("abgesichert, damit ein kaputter Ordner den Start nicht verhindert",
      "except Exception" in fe_quelle[i_mf - 300:i_mf + 600])

# ---------------------------------------------------------------------------
print()
print("Block 9: EINE Favoriten-Kategorie, zwei Quellen (Build 214)")
# ---------------------------------------------------------------------------
# NUTZER-URTEIL, das Build 213 hier umgestossen hat: "bitte misters
# eigene Favoriten nicht als eigene Kategorie anzeigen, die koennen bei
# uns mit in die Kategorie rein". Build 213 hatte sie getrennt gehalten
# und das mit "zwei Listen, an zwei Orten gepflegt" begruendet - eine
# Vermutung darueber, was der Nutzer unterscheiden will.
check("es gibt KEINE eigene Kategorie mehr",
      "mfav_cat" not in fe_quelle,
      "der Uebersetzungsschluessel muss mit weg, sonst bleibt toter Text")
import fe.translations as TR                             # noqa: E402

check("und der Uebersetzungsschluessel ist aus der Tabelle entfernt",
      "mfav_cat" not in TR.TRANSLATIONS,
      "sonst bleibt ein Eintrag stehen, den niemand mehr benutzt")
check("die Favoriten-Kategorie selbst gibt es natuerlich weiter",
      "favorites_cat" in TR.TRANSLATIONS)

# Und jetzt das Verhalten selbst - an der Methode, nicht am Quelltext.
# Dafuer wird hier zum ersten Mal in dieser Datei das Frontend-Modul
# geladen (die Bloecke davor pruefen absichtlich nur die zwei neuen
# fe/-Module). _harness.py wechselt dabei das Arbeitsverzeichnis; alle
# Pfade in dieser Datei sind absolut, es stoert also nichts.
sys.path.insert(0, _HIER)
import _harness as _H                                     # noqa: E402

fm = _H.fm


class _FE(object):
    _favoriten_vereinen = fm.Frontend._favoriten_vereinen


def _it(name, quelle="eigen"):
    return (name, "game", ("/f/%s.sfc" % quelle, ".sfc", "SNES", None, None))


_fe = _FE()
_fe._favorites_set = set(["A", "B"])
EIGENE = [_it("A"), _it("B")]
MISTERS = [_it("B", "mister"), _it("C", "mister")]
_erg = _fe._favoriten_vereinen(EIGENE, MISTERS)
check("die Namen stehen alle genau einmal drin",
      [e[0] for e in _erg] == ["A", "B", "C"],
      str([e[0] for e in _erg]))
check("UNSERE zuerst, MiSTers dahinter",
      _erg[:2] == EIGENE,
      "unsere Reihenfolge ist zuletzt-zuerst und damit eine Aussage")
check("bei einem Doppelten gewinnt UNSER Eintrag",
      _erg[1][2][0] == "/f/eigen.sfc",
      "sein arg kommt aus unserem Einlesen, nicht aus einer .mgl")
check("die Markierung in der Liste kennt die neuen Namen",
      _fe._favorites_set == set(["A", "B", "C"]),
      "sonst stehen sie in der Kategorie, haben aber keinen Stern")
check("ohne MiSTer-Favoriten wird die eigene Liste NICHT angefasst",
      _fe._favoriten_vereinen(EIGENE, []) is EIGENE)
_fe2 = _FE()
check("ohne _favorites_set laeuft es trotzdem",
      [e[0] for e in _fe2._favoriten_vereinen([], MISTERS)] == ["B", "C"])

# DAS WICHTIGSTE AN DER GANZEN AENDERUNG: es darf nichts in unsere
# Favoritendatei geschrieben werden. Sonst blieben MiSTers Favoriten bei
# uns stehen, nachdem er sie in MiSTer entfernt hat - und er haette
# keine Stelle mehr, an der er sie loswird.
import inspect as _inspect                               # noqa: E402

_q9 = _inspect.getsource(fm.Frontend._favoriten_vereinen)
for verboten in ("save_favorites", "toggle_favorite", "open(", "write"):
    check("die Zusammenfuehrung ruft kein %s" % verboten,
          verboten not in _q9,
          "angezeigt wird zusammen, gespeichert bleibt getrennt")

shutil.rmtree(TMP, ignore_errors=True)

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
