#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft das Vorberechnen der Cover-Miniaturen (Build 73).

AUSLOESER: Messwerte vom Geraet des Nutzers, nachdem drei Vermutungen
von mir nacheinander widerlegt waren (Dateisystem, Sortierung,
Bildschirm-Spiegel/Stream-Overlay):

    PERF split: bgbild=0 bg=0 restore=3 rows=5(13) art=225 flip=1 ms
    PERF draw_page_items: 251 ms

Von 251 ms Seitenaufbau entfallen 225 ms auf EIN noch nicht
vorberechnetes Cover; das Zeichnen selbst kostet rund 20 ms. Beim
zweiten Besuch kostet dasselbe Cover 1-6 ms. Der Nutzer erlebt das als
"in einen Unterordner und zurueck haengt 1-2 Sekunden".

DER WICHTIGSTE TEST HIER IST TEST 1. Der Schluessel des Festplatten-
Caches enthaelt die KASTENGROESSE, in die das Cover eingepasst wird -
und die ist pro Spiel verschieden, weil sie am Text darunter haengt (im
Log des Nutzers gut zu sehen: 96x99, 96x111, 96x135 in derselben
Liste). Fragt der Vorauslader auch nur ein Pixel anders an als der
Zeichenpfad, legt er fleissig Miniaturen ab, die nie jemand findet -
und niemand merkt es, weil nichts kaputtgeht, es bleibt nur langsam.
Genau diese Falle prueft Test 1, indem er die tatsaechlich vom
Zeichenpfad angefragten Masse mitschneidet und vergleicht.

Ausfuehren:
    python3 tools/test_cover_prewarm.py
"""
import os
import random
import shutil
import struct
import sys
import tempfile
import time
import zlib

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import _harness as H                                  # noqa: E402

fm = H.fm
sys.path.insert(0, os.path.dirname(H.FRONTEND_PY))
import fe.art as A                                    # noqa: E402
import fe.prewarm as P                                # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


TMP = tempfile.mkdtemp(prefix="prewarm_")
A.THUMB_CACHE_DIR = os.path.join(TMP, "thumb_cache")


def art_datei(pfad, w, h, seed=0):
    random.seed(seed)
    pix = bytes(random.randrange(256) for _ in range(w * h * 4))
    with open(pfad, "wb") as f:
        f.write(b"ART1" + struct.pack("<HH", w, h) + zlib.compress(pix, 6))


# ----------------------------------------------------------------------
print("Test 1: Vorauslader und Zeichenpfad fragen DIESELBE Kastengroesse an")
# Die Titel sind bewusst unterschiedlich lang: kurze Titel brauchen eine
# Zeile, lange drei - und genau das aendert die Kastenhoehe. Waeren alle
# gleich lang, wuerde dieser Test eine falsche Rechnung gar nicht
# bemerken.
TITEL = [
    "F-Zero",
    "The Legend of Zelda - A Link to the Past",
    "Donkey Kong Country 2 - Diddy's Kong Quest and a very long tail",
    "Actraiser",
    "Super Metroid",
]
for w, h, was in ((320, 240, "CRT"), (1920, 1080, "HDMI")):
    H.set_screen(w, h)
    fe = H.make_frontend(page=1, titles=TITEL)
    geo = fe._art_panel_geometrie()
    check("%s: Boxart-Spalte wird erkannt" % was, geo is not None)
    if geo is None:
        continue

    # Mitschneiden, welche Masse der ECHTE Zeichenpfad anfragt.
    angefragt = []
    echtes_get_scaled = A.ART.get_scaled

    def mitschnitt(pfad, mw, mh, _echt=echtes_get_scaled):
        angefragt.append((pfad, mw, mh))
        return _echt(pfad, mw, mh)

    A.ART.get_scaled = mitschnitt
    try:
        items = fe._display_items()
        for i in range(len(items)):
            fe.item_i = i
            angefragt.clear()
            fe.draw_page_items()
            # NUR Spiele-Cover betrachten: der Zeichenpfad fragt in
            # derselben Runde auch das System-Logo (sysart/) und
            # eventuell ein Hintergrundbild (bg/) an - beides gehoert
            # nicht dem markierten Eintrag und hat mit dem Vorauslader
            # nichts zu tun.
            gezeichnet = [a for a in angefragt
                          if a[0].startswith(A.ART_BASE)
                          or a[0].startswith(A.ART_HD)]
            # Das erste vom Zeichenpfad angefragte Cover ist das des
            # markierten Eintrags - genau das, was der Vorauslader
            # vorhersagen koennen muss.
            vom_zeichnen = gezeichnet[0] if gezeichnet else None
            _n, _node, cat_syskey = fe.cats[fe.cat_i]
            vom_vorauslader = fe.cover_pfad_und_kasten(
                items[i], cat_syskey, geo)
            check("%s: Eintrag %d - Pfad und Kasten identisch" % (was, i),
                  vom_zeichnen is not None
                  and vom_vorauslader is not None
                  and tuple(vom_zeichnen) == tuple(vom_vorauslader),
                  "Zeichnen=%s Vorauslader=%s"
                  % (vom_zeichnen, vom_vorauslader))
    finally:
        A.ART.get_scaled = echtes_get_scaled

# Dass die Titel ueberhaupt UNTERSCHIEDLICHE Kastenhoehen erzeugen, ist
# die Voraussetzung dafuer, dass Test 1 etwas wert ist - sonst wuerde er
# auch eine fest verdrahtete Groesse durchgehen lassen.
# Auf CRT ist das messbar: dort ist die Spalte niedrig genug, dass die
# Textzeilen wirklich Platz wegnehmen (im Log des Nutzers 96x99, 96x111,
# 96x135). Auf HDMI greift dagegen der 85%-Deckel und macht alle Kaesten
# gleich hoch - deshalb wird hier bewusst mit CRT geprueft.
H.set_screen(320, 240)
fe = H.make_frontend(page=1, titles=TITEL)
geo = fe._art_panel_geometrie()
_n, _node, cat_syskey = fe.cats[fe.cat_i]
hoehen = set()
for it in fe._display_items():
    ziel = fe.cover_pfad_und_kasten(it, cat_syskey, geo)
    if ziel:
        hoehen.add(ziel[2])
check("die Titel erzeugen auf CRT wirklich verschiedene Kastenhoehen",
      len(hoehen) > 1, "Hoehen: %s" % sorted(hoehen))

# ----------------------------------------------------------------------
print()
print("Test 2: die vorberechnete Miniatur ist BIT-IDENTISCH zur frischen")
# Der Modul-Kommentar in fe/art.py verlangt das ausdruecklich: eine
# gespeicherte Miniatur muss exakt der frisch berechneten entsprechen,
# sonst sieht ein Cover je nach Cache-Zustand anders aus. Deshalb
# benutzen beide Wege dieselben herausgeloesten Rechenfunktionen.
for quelle_w, quelle_h, kasten, was in (
        (300, 400, (96, 111), "verkleinern"),
        (20, 25, (96, 111), "vergroessern")):
    pfad = os.path.join(TMP, "%s.art" % was)
    art_datei(pfad, quelle_w, quelle_h, seed=quelle_w)
    shutil.rmtree(A.THUMB_CACHE_DIR, ignore_errors=True)
    A.ART.cache.clear()
    A.ART.order = []
    A.ART.scaled = {}
    A.ART.scaled_order = []
    frisch = A.ART._get_scaled_impl(pfad, *kasten)
    shutil.rmtree(A.THUMB_CACHE_DIR, ignore_errors=True)
    check("%s: Vorberechnung meldet 'fertig'" % was,
          A.prewarm_thumb(pfad, *kasten) == "fertig")
    aus_cache = A._thumb_cache_get(pfad, *kasten)
    check("%s: Groesse identisch" % was,
          aus_cache is not None and frisch[:2] == aus_cache[:2],
          "%s vs %s" % (frisch[:2] if frisch else None,
                        aus_cache[:2] if aus_cache else None))
    check("%s: Pixel Byte fuer Byte identisch" % was,
          aus_cache is not None and frisch[2] == aus_cache[2])
    check("%s: zweiter Aufruf meldet 'treffer'" % was,
          A.prewarm_thumb(pfad, *kasten) == "treffer")

print()
print("Test 2b: Sonderfaelle der Vorberechnung")
passt = os.path.join(TMP, "passt_genau.art")
art_datei(passt, 96, 111, seed=7)
check("passt das Bild exakt, wird nichts abgelegt "
      "(der Zeichenpfad legt dort auch nichts ab)",
      A.prewarm_thumb(passt, 96, 111) == "uebersprungen")
check("und es liegt wirklich keine Datei da",
      not A.thumb_cache_has(passt, 96, 111))
check("fehlende Datei meldet 'fehler' statt abzustuerzen",
      A.prewarm_thumb(os.path.join(TMP, "gibt_es_nicht.art"), 96, 111)
      == "fehler")
kaputt = os.path.join(TMP, "kaputt.art")
open(kaputt, "wb").write(b"NICHTART" + b"\x00" * 40)
check("beschaedigte Datei meldet 'fehler'",
      A.prewarm_thumb(kaputt, 96, 111) == "fehler")
check("ungueltige Kastengroesse wird uebersprungen",
      A.prewarm_thumb(passt, 0, 111) == "uebersprungen")

# ----------------------------------------------------------------------
print()
print("Test 3: die Vorberechnung fasst die Arbeitsspeicher-Caches NICHT an")
# Sie laeuft aus einem Hintergrund-Thread. ArtCache.cache/.scaled sind
# Woerterbuch + Liste OHNE Sperre - zwei Threads darin gleichzeitig
# waeren genau die Sorte Fehler, die sich nie zuverlaessig nachstellen
# laesst. Deshalb liest die Vorberechnung ihr Original selbst ein.
gross = os.path.join(TMP, "unangetastet.art")
art_datei(gross, 300, 400, seed=11)
shutil.rmtree(A.THUMB_CACHE_DIR, ignore_errors=True)
A.ART.cache.clear()
A.ART.order = []
A.ART.scaled = {}
A.ART.scaled_order = []
A.prewarm_thumb(gross, 96, 111)
check("der Rohbild-Cache ist unveraendert leer", not A.ART.cache)
check("der Skalierungs-Cache ist unveraendert leer", not A.ART.scaled)
check("die Datei auf der Karte liegt trotzdem",
      A.thumb_cache_has(gross, 96, 111))

# ----------------------------------------------------------------------
print()
print("Test 4: der Hintergrund-Thread arbeitet ab und laesst sich abbrechen")
shutil.rmtree(A.THUMB_CACHE_DIR, ignore_errors=True)
dateien = []
for i in range(6):
    p = os.path.join(TMP, "job%d.art" % i)
    art_datei(p, 120, 160, seed=100 + i)
    dateien.append(p)

pw = P.CoverPrewarmer()
pw.PAUSE = 0.0
pw.start()
pw.uebergeben([(p, 48, 64) for p in dateien])
for _ in range(200):
    if not pw.beschaeftigt():
        break
    time.sleep(0.02)
check("alle Auftraege wurden abgearbeitet", not pw.beschaeftigt())
check("und liegen jetzt auf der Karte",
      all(A.thumb_cache_has(p, 48, 64) for p in dateien),
      "%d von %d" % (sum(1 for p in dateien if A.thumb_cache_has(p, 48, 64)),
                     len(dateien)))
check("der Zaehler stimmt", pw.gerechnet == len(dateien), str(pw.gerechnet))

print()
print("Test 4b: eine neue Liste ueberholt die alte")
shutil.rmtree(A.THUMB_CACHE_DIR, ignore_errors=True)
langsam = []
for i in range(40):
    p = os.path.join(TMP, "viel%d.art" % i)
    art_datei(p, 200, 260, seed=200 + i)
    langsam.append(p)
pw2 = P.CoverPrewarmer()
pw2.PAUSE = 0.0
pw2.start()
pw2.uebergeben([(p, 64, 80) for p in langsam])
time.sleep(0.05)
pw2.abbrechen()
# Nach dem Abbruch darf hoechstens die EINE gerade laufende Berechnung
# noch fertig werden - eine begonnene laesst sich nicht mittendrin
# abbrechen, das ist im Entwurf so festgehalten.
stand = pw2.gerechnet
time.sleep(0.3)
check("nach dem Abbruch kommt hoechstens noch eine Miniatur dazu",
      pw2.gerechnet - stand <= 1,
      "vorher %d, nachher %d" % (stand, pw2.gerechnet))
check("und laengst nicht alle 40 wurden gerechnet",
      pw2.gerechnet < 40, str(pw2.gerechnet))
check("die Auftragsliste ist leer", not pw2.beschaeftigt())
pw2.beenden()
pw.beenden()

print()
print("Test 4c: die Auftragsliste laesst schon Vorhandenes weg")
vorhanden = dateien[0]
# dateien[0] wurde in Test 4 unter 48x64 abgelegt und dann geloescht -
# hier einen frischen, eindeutigen Fall bauen.
shutil.rmtree(A.THUMB_CACHE_DIR, ignore_errors=True)
a1 = os.path.join(TMP, "liste_a.art")
a2 = os.path.join(TMP, "liste_b.art")
art_datei(a1, 200, 250, seed=301)
art_datei(a2, 200, 250, seed=302)
A.prewarm_thumb(a1, 60, 70)          # a1 liegt jetzt schon da


def mass(eintrag):
    return {"a": (a1, 60, 70), "b": (a2, 60, 70)}.get(eintrag)


auftraege = P.auftraege_bauen(["x", "a", "b"], 0, mass, vorwaerts=True)
check("nur der noch fehlende Eintrag steht in der Liste",
      auftraege == [(a2, 60, 70)], str(auftraege))

print()
print("Test 4d: Reihenfolge - in Scrollrichtung zuerst")
eintraege = list(range(20))
gesehen = []


def mass2(i):
    p = os.path.join(TMP, "reihe.art")
    if not os.path.exists(p):
        art_datei(p, 50, 60, seed=9)
    gesehen.append(i)
    return (p + "#%d" % i, 30, 40)     # Pfad je Eintrag verschieden


auf = P.auftraege_bauen(eintraege, 10, mass2, vorwaerts=True,
                        voraus=3, zurueck=2)
check("erst vorwaerts, dann rueckwaerts",
      gesehen[:5] == [11, 12, 13, 9, 8], str(gesehen[:5]))
gesehen.clear()
P.auftraege_bauen(eintraege, 10, mass2, vorwaerts=False,
                  voraus=3, zurueck=2)
check("bei Rueckwaerts-Scrollen andersherum",
      gesehen[:5] == [9, 8, 7, 11, 12], str(gesehen[:5]))
gesehen.clear()
P.auftraege_bauen(eintraege, 0, mass2, vorwaerts=False, voraus=3, zurueck=2)
check("am Listenanfang wird nicht ins Leere gegriffen",
      all(0 <= i < 20 for i in gesehen), str(gesehen))

# ----------------------------------------------------------------------
print()
print("Test 5: Menuepunkt, Handler und Uebersetzungen")
menu_py = open(os.path.join(os.path.dirname(H.FRONTEND_PY), "fe", "menu.py"),
               encoding="utf-8").read()
check('der Menuepunkt "thumb_prewarm" ist eingetragen',
      '"thumb_prewarm", None' in menu_py)
fe_py = open(H.FRONTEND_PY, encoding="utf-8").read()
check("und wird in frontend.py behandelt", 'kind == "thumb_prewarm"' in fe_py)
check("bei jeder Eingabe wird der Vorauslader gestoppt",
      "PREWARMER.abbrechen()" in fe_py)
check("der Vorauslader wird im Leerlauf angestossen",
      "self._prewarm_anstossen()" in fe_py)

import fe.translations as T                           # noqa: E402
tabelle = getattr(T, "TRANSLATIONS", None) or getattr(T, "STRINGS", {})
for schluessel in ("sys_thumb_prewarm_action", "thumb_prewarm",
                   "thumb_prewarm_done", "thumb_prewarm_aborted",
                   "thumb_prewarm_cancel", "thumb_prewarm_nothing",
                   "thumb_prewarm_eta_min", "thumb_prewarm_eta_sec",
                   "thumb_prewarm_failed"):
    eintrag = tabelle.get(schluessel)
    check("Uebersetzung %s vorhanden (de+en)" % schluessel,
          bool(eintrag) and "de" in eintrag and "en" in eintrag)
# Der Menuepunkt kann Minuten dauern - das MUSS dranstehen, sonst
# waehlt ihn jemand aus und denkt, das Frontend haengt.
de = tabelle.get("sys_thumb_prewarm_action", {}).get("de", "").lower()
check("der Menuepunkt nennt die Dauer", "minuten" in de or "dauert" in de, de)
# Und der Abbruch-Hinweis muss sagen, dass nichts verlorengeht.
de_ab = tabelle.get("thumb_prewarm_cancel", {}).get("de", "").lower()
check("der Abbruch-Hinweis beruhigt ueber das schon Gerechnete",
      "bleibt" in de_ab or "erhalten" in de_ab, de_ab)

shutil.rmtree(TMP, ignore_errors=True)

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for f in fails:
        print("   ", f)
    sys.exit(1)
print("Alle Tests bestanden.")
