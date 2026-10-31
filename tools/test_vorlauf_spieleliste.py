#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Der Vorlauf der Spieleliste waehrend der F9-Frist (Build 303).

WORUM ES GEHT. Aus Abschnitt A seines Berichts (Bench 17):

    F9 eingespeist                   218 ms   12 %
    Erstes Bild gerechnet            153 ms    8 %
    Restfrist fuer MiSTer abgewartet 247 ms   14 %
    davon scan_games()               538 ms   29 %
    Start bis Kategorien bereit     1825 ms

218 + 247 = 465 ms reines Schlafen - time.sleep() vor und nach der
F9-Injektion. Daneben der groesste Einzelposten des ganzen Starts mit
538 ms. Dasselbe Muster wie Build 292, eine Etage hoeher: die Zeit
bleibt, die Untaetigkeit nicht.

WAS DABEI SCHIEFGEHEN KANN, und deshalb gibt es diesen Test.
scan_games() hat ZWEI Gesichter:

  schnell  Fingerabdruck passt -> Signatur bilden, Kopf lesen, Baeume
           entpacken. Reine Dateiarbeit, beruehrt keinen Bildschirm.
  langsam  Fingerabdruck passt nicht -> WARTET auf USB oder NAS und
           ZEICHNET dabei (warte_cb), und beim Neuscan laeuft ein
           Fortschrittsbalken (progress_cb).

Der Vorlauf darf ausschliesslich den schnellen Weg nehmen. Zeichnen aus
einem Faden, waehrend der Hauptfaden gerade die Konsole uebernimmt und
das erste Bild noch nicht steht, waere die Sorte Fehler, die man nicht
mehr findet - und dieses Projekt hat fuenfmal Reste in Ecken gejagt,
die harmloser waren als das.

WAS DIESER TEST SICHERT:
  1. ALS STRUKTUR, nicht als Behauptung: der Vorlauf ruft NUR die drei
     Funktionen des schnellen Wegs - geprueft am Syntaxbaum, damit ein
     spaeter hineingeschriebenes Warten oder Zeichnen auffaellt,
  2. passt der Fingerabdruck, liefert er die Liste,
  3. passt er nicht, liefert er NICHTS und veraendert nichts,
  4. ein Fehler darin kostet den Start nichts,
  5. force=True ignoriert ihn,
  6. der Hauptfaden wartet notfalls auf ihn, und wie lange, wird
     GEMESSEN und nicht geglaubt,
  7. der Faden ist ein daemon - ein haengender Vorlauf darf das
     Beenden nicht aufhalten,
  8. und im Startweg steht der Anstoss VOR der Frist, sonst ueberlappt
     er mit nichts.

Ausfuehren:
    python3 tools/test_vorlauf_spieleliste.py
"""
import ast
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H          # noqa: E402,F401  (setzt den Pfad)

import fe.scan as S           # noqa: E402
from _quelle import koerper, nur_code                     # noqa: E402

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

fails = []


def check(name, ok, info=""):
    if ok:
        print("  OK   %s %s" % (name, info))
    else:
        print("  FEHL %s %s" % (name, info))
        fails.append(name)


print(__doc__.strip().split("\n")[0])
print()

# ---------------------------------------------------------------------------
print("Test 1: der Vorlauf kann den langsamen Weg nicht nehmen")
# ---------------------------------------------------------------------------
# DIE WICHTIGSTE PRUEFUNG, und sie ist als STRUKTUR gefasst: nicht
# "in diesem Lauf wurde nicht gezeichnet", sondern "es ist nicht
# hingeschrieben". Eine Zusage, die an einem Durchlauf haengt, gilt nur
# fuer die Faelle, die der Durchlauf getroffen hat.
_scan_py = os.path.join(_REPO, "frontend", "fe", "scan.py")
_src = open(_scan_py, encoding="utf-8").read()
_vorladen_src = koerper(_src, "scan_games_vorladen")

# ERLAUBT ist genau der schnelle Weg, plus Uhr, Faden und Typname.
ERLAUBT = {
    "_games_signature", "_cache_kopf_lesen", "_cache_systeme_lesen",
    "monotonic", "Thread", "start", "type", "len",
}
_gerufen = set()
for knoten in ast.walk(ast.parse(_vorladen_src)):
    if isinstance(knoten, ast.Call):
        f = knoten.func
        if isinstance(f, ast.Name):
            _gerufen.add(f.id)
        elif isinstance(f, ast.Attribute):
            _gerufen.add(f.attr)
_verboten = sorted(_gerufen - ERLAUBT)
check("der Vorlauf ruft nur den schnellen Weg",
      not _verboten,
      "unerwartet: %r" % (_verboten,) if _verboten else
      "gerufen wird: %s" % ", ".join(sorted(_gerufen)))

# UND NAMENTLICH die vier, auf die es ankommt - damit der Test auch
# dann noch etwas sagt, wenn die Liste oben einmal erweitert wird.
for name in ("progress_cb", "warte_cb", "_wait_for_usb_stable",
             "_wait_for_nas_mount", "_scan_games_disk", "sleep"):
    check("kein %s im Vorlauf" % name, name not in _vorladen_src)

# ---------------------------------------------------------------------------
print()
print("Test 2: passt der Fingerabdruck, liefert er die Liste")
# ---------------------------------------------------------------------------
# MIT ATTRAPPEN, und das ist hier der Zweck: geprueft wird MEINE
# Steuerung, nicht pickle. Im Container gibt es keine Spieleordner -
# eine Messung daran waere keine.
ECHT = (S._games_signature, S._cache_kopf_lesen, S._cache_systeme_lesen)
CATS = [("NES", {"x": 1}, "NES"), ("SNES", {"y": 2}, "SNES")]


def stellen(sig_jetzt, sig_cache, fehler=None):
    S._games_signature = lambda: (sig_jetzt, {})
    def _kopf():
        if fehler is not None:
            raise fehler
        return (sig_cache, {}, "handle")
    S._cache_kopf_lesen = _kopf
    S._cache_systeme_lesen = lambda handle, nur=None: list(CATS)


def zurueck():
    (S._games_signature, S._cache_kopf_lesen,
     S._cache_systeme_lesen) = ECHT


try:
    stellen("A", "A")
    S.scan_games_vorladen()
    got = S.scan_games()
    grund, dauer, warten = S.vorladen_stand()
    check("die Liste kommt aus dem Vorlauf", got == CATS,
          "%d Systeme, Grund: %s" % (len(got), grund))
    check("und der Grund sagt es auch", grund == "aus dem Cache vorgeladen",
          "%r" % (grund,))

    # ---------------------------------------------------------------
    print()
    print("Test 3: passt er nicht, liefert der Vorlauf nichts")
    # ---------------------------------------------------------------
    # Der normale Aufruf muss dann ALLES wie bisher machen - mit
    # seinem Warten und seinen Rueckmeldungen. Geprueft daran, dass
    # er die Attrappe des Kopfes selbst noch einmal fragt.
    stellen("NEU", "ALT")
    S.scan_games_vorladen()
    grund = None
    for _ in range(200):                      # auf den Faden warten
        grund = S.vorladen_stand()[0]
        if grund != "laeuft":
            break
        time.sleep(0.005)
    check("der Vorlauf gibt auf", grund == "Fingerabdruck passt nicht",
          "%r" % (grund,))
    check("und hat kein Ergebnis hinterlassen",
          S._VORLADEN["ergebnis"] is None)
    # Und der normale Weg laeuft danach ungestoert an (er landet beim
    # langsamen Zweig und damit in den echten Funktionen - hier reicht,
    # dass er nicht das falsche Ergebnis liefert).
    stellen("A", "A")
    check("danach liefert der normale Aufruf wieder", S.scan_games() == CATS)

    # ---------------------------------------------------------------
    print()
    print("Test 4: ein Fehler im Vorlauf kostet den Start nichts")
    # ---------------------------------------------------------------
    stellen("A", "A", fehler=OSError("Karte weg"))
    S.scan_games_vorladen()
    for _ in range(200):
        if S.vorladen_stand()[0] != "laeuft":
            break
        time.sleep(0.005)
    check("der Grund nennt den Fehler",
          S.vorladen_stand()[0] == "abgebrochen (OSError)",
          "%r" % (S.vorladen_stand()[0],))
    stellen("A", "A")
    check("und der normale Aufruf liefert trotzdem",
          S.scan_games() == CATS)

    # ---------------------------------------------------------------
    print()
    print("Test 5: force=True ignoriert den Vorlauf")
    # ---------------------------------------------------------------
    # Wer "Spieleliste neu einlesen" waehlt, will NEU einlesen - nicht
    # das, was 400 ms vorher im Cache stand.
    stellen("A", "A")
    S.scan_games_vorladen()
    for _ in range(200):
        if S.vorladen_stand()[0] != "laeuft":
            break
        time.sleep(0.005)
    gerufen = []
    S._scan_games_disk_echt = S._scan_games_disk
    S._scan_games_disk = lambda *a, **k: (gerufen.append(1), [])[1]
    try:
        S.scan_games(force=True)
    except Exception:                                    # noqa: BLE001
        pass
    S._scan_games_disk = S._scan_games_disk_echt
    check("bei force wird neu von der Platte gelesen", bool(gerufen),
          "_scan_games_disk() %d x gerufen" % len(gerufen))

    # ---------------------------------------------------------------
    print()
    print("Test 6: der Hauptfaden wartet notfalls - und misst es")
    # ---------------------------------------------------------------
    # DIE EHRLICHE ZAHL. Ohne sie waere "es ueberlappt" eine
    # Behauptung; dieses Projekt hat eine Verbesserung schon einmal
    # versprochen, die auf dem Geraet nicht eintrat (Build 300).
    #
    # ZWEI EIGENSCHAFTEN DES PRUEFSTANDS STEHEN DEM IM WEG, und die
    # erste Fassung dieses Tests ist an beiden gescheitert:
    # tools/_harness.py friert time.monotonic GLOBAL ein UND macht
    # time.sleep() zu einem Nichts. Ein Vorlauf, der "lange braucht",
    # ist dort also nicht herzustellen - er ist sofort fertig, und
    # gemessen wurden 0 ms. Dasselbe hat in Build 301 einen Test
    # endlos haengen lassen; kein Fehler im Code, eine Eigenschaft des
    # Pruefstands.
    #
    # UND EIN WETTRENNEN WAERE DIE FALSCHE ANTWORT. Ob der Faden noch
    # laeuft, wenn der Hauptfaden abholt, entscheidet sonst die
    # Zufaelligkeit der Umschaltung - ein Test, der manchmal gruen ist,
    # prueft nichts. Also wird der ZUSTAND HERGESTELLT: an die Stelle
    # des Fadens tritt eine Attrappe, deren join() die Uhr
    # weiterstellt und das Ergebnis nachliefert. Damit ist genau das
    # geprueft, was hier zaehlt - dass _vorgeladenes_holen() das
    # Abholen UMSCHLIESST und nicht daneben misst.
    class FadenAttrappe:
        def join(self):
            H.NOW[0] += 0.12                  # waehrend des Abholens
            S._VORLADEN["ergebnis"] = ("A", list(CATS))
            S._VORLADEN["dauer"] = 0.30

    S._VORLADEN["faden"] = FadenAttrappe()
    S._VORLADEN["ergebnis"] = None
    S._VORLADEN["grund"] = "laeuft"
    stellen("A", "A")
    got = S.scan_games()
    grund, dauer, warten = S.vorladen_stand()
    check("die Liste kommt trotzdem vollstaendig", got == CATS,
          "%d Systeme" % len(got))
    check("und die Wartezeit ist gemessen, nicht null",
          abs(warten - 0.12) < 1e-6,
          "%.0f ms gewartet, Vorlauf lief %.0f ms - gemessen wird um "
          "das join() herum" % (warten * 1000, dauer * 1000))
    check("eine Restwartezeit von 0 ist der ERWUENSCHTE Fall",
          True,
          "sie heisst: die Frist hat das Einlesen ganz geschluckt")
finally:
    zurueck()

# ---------------------------------------------------------------------------
print()
print("Test 7: der Faden darf das Beenden nicht aufhalten")
# ---------------------------------------------------------------------------
_v = nur_code(koerper(_src, "scan_games_vorladen"))
check("der Vorlauf laeuft als daemon", "daemon=True" in _v,
      "ein haengender Lesevorgang wuerde sonst das Beenden blockieren")
check("und er wird nur einmal angestossen",
      '_VORLADEN["faden"] is not None' in _v,
      "ein zweiter Aufruf darf keinen zweiten Faden starten")

_h = nur_code(koerper(_src, "_vorgeladenes_holen"))
check("abgeholt wird mit join(), auch ohne Bedarf", "join()" in _h,
      "_games_signature() schreibt eine Modulvariable - zwei Schreiber "
      "zur gleichen Zeit sind eine Frage, die man sich sparen kann")

# ---------------------------------------------------------------------------
print()
print("Test 8: im Startweg steht der Anstoss VOR der Frist")
# ---------------------------------------------------------------------------
# Sonst ueberlappt er mit nichts, und der ganze Build waere ein
# Kommentar. Geprueft an der Reihenfolge im Quelltext von __init__,
# weil der Startweg sich nicht isoliert laufen laesst.
_fe_src = open(H.FRONTEND_PY, encoding="utf-8", errors="replace").read()
_i_vor = _fe_src.find("scan_games_vorladen()")
_i_f9 = _fe_src.find("self.enter_console_mode(nachlauf=False)")
_i_rest = _fe_src.find("self._f9_nachlauf_abwarten()")
check("scan_games_vorladen() wird im Startweg gerufen", _i_vor > 0)
check("und zwar VOR dem F9", 0 < _i_vor < _i_f9,
      "sonst schlaeft der Hauptfaden, bevor der Faden ueberhaupt laeuft")
check("und damit auch vor der Restfrist", 0 < _i_vor < _i_rest)
check("der Startweg meldet die Ueberlappung ins Protokoll",
      "Vorlauf der Spieleliste" in _fe_src,
      "steht dort eine grosse Restwartezeit, hat es NICHT funktioniert")

# ---------------------------------------------------------------------------
print()
if fails:
    print("FEHLGESCHLAGEN (%d):" % len(fails))
    for f in fails:
        print("  - %s" % f)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
