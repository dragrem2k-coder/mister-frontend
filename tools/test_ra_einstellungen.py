#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft die RA-Einstellungen der MiSTer-Hauptanwendung (Build 95).

AUSLOESER (Nutzer, zwei Nachrichten):
  "Sute hat eine neue Main MiSTer gebaut, die hat nun RA Settings -
   koennen wir das irgendwie mit ins Frontend einbauen?"
  "Das haette ich auch gerne bei uns im Frontend, und zwar dann
   einstellbar unter System und dann RetroAchievements."

WAS HIER AUF DEM SPIEL STEHT: /media/fat/retroachievements.cfg gehoert
NICHT uns. Darin stehen die RA-Zugangsdaten des Nutzers (Benutzername
UND Passwort), moeglicherweise Kommentare, und in einer kuenftigen
MiSTer-Version Schluessel, die es heute noch nicht gibt. Ein Fehler in
diesem Modul kostet nicht ein falsches Pixel, sondern im schlimmsten
Fall den Zugang zu RetroAchievements.

Die Tests pruefen deshalb vor allem EINES: dass beim Schreiben wirklich
nur genau die eine gemeinte Zeile angefasst wird und alles andere Byte
fuer Byte stehen bleibt.

Ausfuehren:
    python3 tools/test_ra_einstellungen.py
"""
import os
import shutil
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import _harness as H                                  # noqa: E402

fm = H.fm
sys.path.insert(0, os.path.dirname(H.FRONTEND_PY))
import fe.ra_settings as R                            # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


TMP = tempfile.mkdtemp(prefix="ra_cfg_")
R.RA_SETTINGS_FILE = os.path.join(TMP, "retroachievements.cfg")

# Eine Datei, wie sie realistisch aussieht: Kommentar, Zugangsdaten,
# ein paar gesetzte Werte, ein Core-Abschnitt, ein Schluessel den wir
# NICHT kennen, und eine auskommentierte Zeile.
ORIGINAL = """\
# RetroAchievements fuer MiSTer
# Zugangsdaten nicht weitergeben!
username=Dragrem
password=streng_geheim
show_progress_popups=1
popup_position=left
#multiline_desc=1
irgendein_zukuenftiger_schluessel=42

[SNES]
popup_h_offset=-12

[Gameboy]
popup_v_offset=4
"""


def frisch():
    with open(R.RA_SETTINGS_FILE, "w", encoding="utf-8") as f:
        f.write(ORIGINAL)


def inhalt():
    with open(R.RA_SETTINGS_FILE, encoding="utf-8") as f:
        return f.read()


def zeilen_ausser(neu, alt):
    """Welche Zeilen sind hinzugekommen bzw. verschwunden?"""
    a, b = alt.split("\n"), neu.split("\n")
    weg = [z for z in a if z not in b]
    dazu = [z for z in b if z not in a]
    return weg, dazu


print("Test 1: die Datei wird nur an der gemeinten Zeile veraendert")
# Der wichtigste Test des ganzen Moduls.
frisch()
R.schalter_umschalten("show_progress_popups", True)
weg, dazu = zeilen_ausser(inhalt(), ORIGINAL)
check("genau eine Zeile weg, eine dazu", len(weg) == 1 and len(dazu) == 1,
      "(weg=%s dazu=%s)" % (weg, dazu))
check("und zwar die gemeinte",
      weg == ["show_progress_popups=1"] and dazu == ["show_progress_popups=0"])
check("Zugangsdaten unangetastet",
      "username=Dragrem" in inhalt() and "password=streng_geheim" in inhalt())
check("Kommentare unangetastet",
      "# RetroAchievements fuer MiSTer" in inhalt()
      and "# Zugangsdaten nicht weitergeben!" in inhalt())
check("unbekannter Schluessel unangetastet",
      "irgendein_zukuenftiger_schluessel=42" in inhalt())

print("Test 2: auskommentierte Zeilen bleiben auskommentiert")
# "#multiline_desc=1" darf NICHT als vorhandener Wert gelten - sonst
# wuerde das Frontend eine bewusst deaktivierte Zeile wiederbeleben.
frisch()
check("auskommentierter Wert zaehlt nicht als gesetzt",
      R.roh_lesen("multiline_desc") is None)
R.schalter_umschalten("multiline_desc", False)
check("die Kommentarzeile steht noch da",
      "#multiline_desc=1" in inhalt())
check("der neue Wert steht als eigene Zeile da",
      "multiline_desc=1" in inhalt().replace("#multiline_desc=1", ""))

print("Test 3: ein neuer globaler Wert landet VOR dem ersten Abschnitt")
# Haengte er am Dateiende, stuende er hinter "[Gameboy]" und waere
# damit ploetzlich ein Gameboy-Wert - ein stiller, boeser Fehler.
frisch()
R.schalter_umschalten("list_hotkey", False)
text = inhalt()
check("neuer Wert steht vor dem ersten [Abschnitt]",
      text.index("list_hotkey=") < text.index("[SNES]"),
      "(Position %d vs %d)" % (text.index("list_hotkey="),
                               text.index("[SNES]")))

print("Test 4: Core-Werte landen im richtigen Abschnitt")
frisch()
R.offset_schreiben("popup_v_offset", 3, "SNES")
text = inhalt()
snes = text[text.index("[SNES]"):text.index("[Gameboy]")]
check("neuer SNES-Wert steht im SNES-Abschnitt", "popup_v_offset=3" in snes)
check("Gameboy behaelt seinen eigenen Wert",
      "popup_v_offset=4" in text[text.index("[Gameboy]"):])
R.offset_schreiben("popup_h_offset", 7, "Genesis")
text = inhalt()
check("ein fehlender Abschnitt wird angelegt", "[Genesis]" in text)
check("und bekommt seinen Wert",
      "popup_h_offset=7" in text[text.index("[Genesis]"):])

print("Test 5: geerbt oder eigener Wert - der Unterschied ist sichtbar")
# Ohne diese Unterscheidung sehen "0, weil global 0" und "0, weil hier
# ausdruecklich gesetzt" gleich aus, verhalten sich aber verschieden.
frisch()
check("SNES hat einen eigenen H-Offset",
      R.wert_mit_herkunft("popup_h_offset", "SNES") == (-12, True))
check("SNES erbt den V-Offset",
      R.wert_mit_herkunft("popup_v_offset", "SNES") == (0, False))
check("global gibt es keine Herkunftsfrage",
      R.wert_mit_herkunft("popup_h_offset", None)[1] is False)
R.offset_schreiben("popup_v_offset", -2, None)
check("nach globaler Aenderung erbt SNES den neuen Wert",
      R.wert_mit_herkunft("popup_v_offset", "SNES") == (-2, False))
check("SNES' eigener H-Offset bleibt davon unberuehrt",
      R.wert_mit_herkunft("popup_h_offset", "SNES") == (-12, True))

print("Test 6: Grenzen werden eingehalten")
frisch()
for key, (lo, hi) in R.OFFSETS.items():
    R.offset_schreiben(key, hi + 500, None)
    check("%s wird oben bei %+d gekappt" % (key, hi),
          R.offset_lesen(key, None) == hi)
    R.offset_schreiben(key, lo - 500, None)
    check("%s wird unten bei %+d gekappt" % (key, lo),
          R.offset_lesen(key, None) == lo)

print("Test 7: Position kennt nur die drei erlaubten Werte")
frisch()
gesehen = set()
for _ in range(6):
    gesehen.add(R.position_weiter(None))
check("Durchlauf trifft genau links/mitte/rechts",
      gesehen == set(R.POSITION_WERTE), "(%s)" % sorted(gesehen))
R.roh_schreiben(R.POSITION_KEY, "voellig_kaputt", None)
check("ein unsinniger Wert faellt auf den Standard zurueck",
      R.position_lesen(None) == R.POSITION_STANDARD)
R.roh_schreiben(R.POSITION_KEY, "centre", None)
check("die britische Schreibweise wird verstanden",
      R.position_lesen(None) == "center")

print("Test 8: Wahrheitswerte werden in ihrer Schreibweise belassen")
# Wer seine Datei von Hand mit true/false pflegt, soll sie nicht
# stillschweigend auf 1/0 umgeschrieben bekommen.
frisch()
R.roh_schreiben("show_progress_popups", "true", None)
R.schalter_umschalten("show_progress_popups", True)
check("true -> false (nicht 0)",
      "show_progress_popups=false" in inhalt(),
      "(gefunden: %r)" % R.roh_lesen("show_progress_popups"))
R.roh_schreiben("show_progress_popups", "1", None)
R.schalter_umschalten("show_progress_popups", True)
check("1 -> 0 (Standard)", R.roh_lesen("show_progress_popups") == "0")

print("Test 9: Zuruecksetzen entfernt nur die Pro-Core-Werte")
frisch()
R.roh_schreiben("irgendwas_von_mister", "wichtig", "SNES")
R.offset_schreiben("popup_v_offset", 5, "SNES")
R.sektion_zuruecksetzen("SNES")
text = inhalt()
snes = text[text.index("[SNES]"):text.index("[Gameboy]")]
check("eigene Offsets sind weg",
      "popup_h_offset" not in snes and "popup_v_offset" not in snes,
      "(%r)" % snes)
check("fremde Schluessel im selben Abschnitt bleiben",
      "irgendwas_von_mister=wichtig" in snes)
check("andere Abschnitte bleiben unberuehrt",
      "popup_v_offset=4" in text[text.index("[Gameboy]"):])

print("Test 10: fehlende Datei wird NICHT angelegt")
# Die Datei enthaelt Zugangsdaten. Eine von uns erzeugte Datei mit
# lauter Einstellungen und ohne Benutzername waere fuer MiSTer wertlos
# und fuer den Nutzer verwirrend.
os.remove(R.RA_SETTINGS_FILE)
check("vorhanden() meldet False", R.vorhanden() is False)
check("Schreiben schlaegt sauber fehl",
      R.roh_schreiben("show_progress_popups", "1", None) is False)
check("und legt nichts an", not os.path.exists(R.RA_SETTINGS_FILE))
check("Lesen liefert den Standard statt zu werfen",
      R.schalter_lesen("show_progress_popups", True) is True)

print("Test 11: Abschnittsnamen kommen vom CORE, nicht vom System")
# MiSTer legt pro Core ab. Game Boy und Game Boy Color benutzen
# denselben Core - ein Wert dort gilt zwangslaeufig fuer beide.
check("_Console/Gameboy -> Gameboy", R.core_name("_Console/Gameboy") == "Gameboy")
check("_Console/MegaDrive -> MegaDrive",
      R.core_name("_Console/MegaDrive") == "MegaDrive")
check("leerer Pfad -> None", R.core_name("") is None)

frisch()
H.set_screen(1920, 1080)
f = H.make_frontend(page=0)
cores = dict(f._ra_settings_cores())
check("Game Boy und Game Boy Color teilen sich einen Eintrag",
      "Gameboy" in cores and "Game Boy" in cores["Gameboy"]
      and "Game Boy Color" in cores["Gameboy"],
      "(%r)" % cores.get("Gameboy"))
check("SNES und SMW Hacks ebenso",
      "SMW Hacks" in cores.get("SNES", []), "(%r)" % cores.get("SNES"))
# Und der Bildschirm muss das auch SAGEN - wer den Wert fuer Game Boy
# aendert, aendert ihn zwangslaeufig auch fuer Game Boy Color.
zeilen = f._ra_settings_zeilen("Gameboy")
koepfe = " | ".join(z[1] for z in zeilen if z[0] == "kopf")
check("der Bildschirm nennt die mitbetroffenen Systeme",
      "Game Boy Color" in koepfe, "(%r)" % koepfe)

print("Test 12: der Bildschirm baut sich auf beiden Aufloesungen auf")
for w, h, name in ((320, 240, "CRT"), (1920, 1080, "HDMI")):
    frisch()
    H.set_screen(w, h)
    f = H.make_frontend(page=0)
    zeilen = f._ra_settings_zeilen(None)
    werte = [z for z in zeilen if z[0] == "wert"]
    check("%s: neun Schalter + Bereich + Position + zwei Offsets"
          % name, len(werte) == 13, "(%d)" % len(werte))
    check("%s: kein Zuruecksetzen im globalen Bereich" % name,
          not any(z[1] == "reset" for z in werte))
    zeilen = f._ra_settings_zeilen("SNES")
    werte = [z for z in zeilen if z[0] == "wert"]
    check("%s: im Core-Bereich kommt Zuruecksetzen dazu" % name,
          any(z[1] == "reset" for z in werte))
    check("%s: und die Herkunft steht dran" % name,
          any("(" in z[4] for z in werte if z[1] in ("position", "offset")))

    # Wirklich zeichnen - ein Layout-Fehler (Division durch Null bei
    # wenig Platz, zu lange Zeile) faellt sonst erst auf dem Geraet auf.
    gezeichnet = []

    def lesen(timeout=None, **kw):
        gezeichnet.append(bytes(f.fb.buf))
        return "back"

    f.inp.read_action = lesen
    f.draw_ra_settings_screen()
    check("%s: Bildschirm wurde gezeichnet" % name, len(gezeichnet) == 1)
    check("%s: und ist nicht leer" % name,
          gezeichnet and len(set(gezeichnet[0])) > 4)

print("Test 13: jede Beschriftung ist uebersetzt")
import fe.translations as T                            # noqa: E402
for key, tkey, _d in R.SCHALTER:
    eintrag = T.TRANSLATIONS.get(tkey)
    check("%s uebersetzt" % tkey,
          bool(eintrag) and bool(eintrag.get("de")) and bool(eintrag.get("en")))
for tkey in ("ra_set_title", "ra_set_hint", "ra_set_position",
             "ra_set_scope_global", "ra_set_scope_core", "ra_set_reset",
             "ra_set_inherited", "ra_set_own", "ra_set_takes_effect",
             "ra_on", "ra_off", "sys_ra_settings",
             "sys_ra_settings_missing"):
    eintrag = T.TRANSLATIONS.get(tkey)
    check("%s uebersetzt" % tkey,
          bool(eintrag) and bool(eintrag.get("de")) and bool(eintrag.get("en")))

print("Test 14: die beiden gleichnamigen Dateien werden nicht verwechselt")
# Der gefaehrlichste denkbare Fehler in diesem Modul.
import fe.retroachievements as RAWEB                   # noqa: E402
check("unsere Datei liegt unter /media/fat/frontend/",
      RAWEB.RA_CONFIG_FILE.startswith("/media/fat/frontend/"))
check("MiSTers Datei liegt direkt unter /media/fat/",
      "/media/fat/retroachievements.cfg" in
      open(os.path.join(os.path.dirname(H.FRONTEND_PY), "fe",
                        "ra_settings.py"), encoding="utf-8").read())
check("die Pfade sind verschieden",
      RAWEB.RA_CONFIG_FILE != "/media/fat/retroachievements.cfg")
quelle = open(os.path.join(os.path.dirname(H.FRONTEND_PY), "fe",
                           "ra_settings.py"), encoding="utf-8").read()
check("ra_settings.py importiert nichts aus retroachievements.py",
      "from fe.retroachievements" not in quelle
      and "import fe.retroachievements" not in quelle)

shutil.rmtree(TMP, ignore_errors=True)

print()
if fails:
    print("FEHLGESCHLAGEN (%d):" % len(fails))
    for f_ in fails:
        print("  -", f_)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
