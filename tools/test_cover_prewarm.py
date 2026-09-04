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

# ----------------------------------------------------------------------
print()
print("Test 6: die Verdraengungs-Pruefung zaehlt nicht mehr bei jedem Schreiben")
# GEMESSEN auf dem Geraet des Nutzers: "Ordner durchzaehlen (7700
# Dateien): 167 ms". Diese Pruefung lief nach JEDEM geschriebenen
# Miniaturbild und stritt sich dabei mit dem Zeichnen um dieselbe
# SD-Karte - im Log schlug das als Cache-TREFFER mit 169 ms durch,
# also ausgerechnet dort, wo gar nichts gerechnet wird.
shutil.rmtree(A.THUMB_CACHE_DIR, ignore_errors=True)
os.makedirs(A.THUMB_CACHE_DIR, exist_ok=True)
A._thumb_cache_anzahl = None
A._thumb_cache_seit_zaehlung = 0
zaehlungen = [0]
_echtes_listdir = os.listdir


def _gezaehltes_listdir(pfad, _echt=_echtes_listdir):
    if str(pfad) == A.THUMB_CACHE_DIR:
        zaehlungen[0] += 1
    return _echt(pfad)


os.listdir = _gezaehltes_listdir
try:
    for i in range(30):
        A._thumb_cache_evict_if_needed()
finally:
    os.listdir = _echtes_listdir
check("bei 30 Schreibvorgaengen wird hoechstens EINMAL gezaehlt",
      zaehlungen[0] <= 1, "%d Zaehlungen" % zaehlungen[0])
check("die Anzahl wird danach mitgefuehrt",
      A._thumb_cache_anzahl is not None and A._thumb_cache_anzahl >= 29,
      str(A._thumb_cache_anzahl))

print()
print("Test 6b: bei Ueberschreiten der Obergrenze wird trotzdem verdraengt")
shutil.rmtree(A.THUMB_CACHE_DIR, ignore_errors=True)
os.makedirs(A.THUMB_CACHE_DIR, exist_ok=True)
for i in range(12):
    with open(os.path.join(A.THUMB_CACHE_DIR, "d%02d.art" % i), "wb") as f:
        f.write(b"x")
    os.utime(os.path.join(A.THUMB_CACHE_DIR, "d%02d.art" % i),
             (1000 + i, 1000 + i))       # aelteste zuerst
_alte_grenze = A.THUMB_CACHE_MAX_FILES
A.THUMB_CACHE_MAX_FILES = 8
A._thumb_cache_anzahl = None
A._thumb_cache_seit_zaehlung = 0
try:
    A._thumb_cache_evict_if_needed()
    uebrig = sorted(x for x in os.listdir(A.THUMB_CACHE_DIR)
                    if x.endswith(".art"))
    check("auf die Obergrenze heruntergeraeumt", len(uebrig) == 8,
          "%d uebrig" % len(uebrig))
    check("und zwar die AELTESTEN entfernt",
          uebrig[0] == "d04.art", str(uebrig))
    check("der Zaehler stimmt danach",
          A._thumb_cache_anzahl == 8, str(A._thumb_cache_anzahl))
finally:
    A.THUMB_CACHE_MAX_FILES = _alte_grenze
    A._thumb_cache_anzahl = None
    A._thumb_cache_seit_zaehlung = 0

# ----------------------------------------------------------------------
print()
print("Test 7: der Skalierungs-Cache haelt nach Speicherbudget")
# GEMESSEN: ein Lesen vom Festplatten-Cache kostet 11 ms im Schnitt.
# Fuer ein Cover, das eben noch auf dem Bildschirm war, ist das
# unnoetig - frueher fielen aber schon nach 20 Bildern die aeltesten
# heraus, unabhaengig davon, ob es winzige CRT- oder riesige
# HDMI-Miniaturen waren.
cache = A.ArtCache()


def ablegen(nr, groesse):
    cache._scaled_cache_put(("p%d" % nr, "box", 1, 1),
                            (1, 1, b"\x00" * groesse))


KLEIN = 96 * 165 * 4          # eine CRT-Miniatur, rund 63 KB
for i in range(400):
    ablegen(i, KLEIN)
check("CRT: deutlich mehr als die frueheren 20 Miniaturen passen hinein",
      len(cache.scaled) > 200, "%d Stueck" % len(cache.scaled))
check("CRT: das Speicherbudget wird eingehalten",
      cache.scaled_bytes <= cache.SCALED_BUDGET,
      "%.1f MB" % (cache.scaled_bytes / 1048576.0))

cache2 = A.ArtCache()
GROSS = 697 * 772 * 4         # ein HDMI-Cover, rund 2,1 MB


def ablegen2(nr):
    cache2._scaled_cache_put(("q%d" % nr, "box", 1, 1),
                             (1, 1, b"\x00" * GROSS))


for i in range(60):
    ablegen2(i)
check("HDMI: es bleiben nie weniger Plaetze als frueher (SCALED_MIN)",
      len(cache2.scaled) >= cache2.SCALED_MIN, "%d Stueck" % len(cache2.scaled))
check("HDMI: nicht alle 60 grossen Bilder werden gehalten",
      len(cache2.scaled) < 60, "%d Stueck" % len(cache2.scaled))
check("die Buchfuehrung stimmt mit dem tatsaechlichen Inhalt ueberein",
      cache2.scaled_bytes == sum(len(v[2]) for v in cache2.scaled.values()),
      "%d vs %d" % (cache2.scaled_bytes,
                    sum(len(v[2]) for v in cache2.scaled.values())))
check("die aeltesten fielen heraus, die neuesten sind da",
      ("q59", "box", 1, 1) in cache2.scaled
      and ("q0", "box", 1, 1) not in cache2.scaled)

# ----------------------------------------------------------------------
print()
print("Test 8: die Kategorie-Logos der Hauptseite werden mit vorgewaermt")
# Nutzer-Rueckmeldung: "sind immer noch ein paar Ausreisser drin, zum
# Beispiel CONTINUE.art" - im Log dazu "PERF cover: 722 ms
# (CONTINUE.art)". Die Logos sind mit 900 px Breite die groessten
# Bilder im Frontend, und sie stehen auf der Seite, die man beim Start
# als erstes sieht.
H.set_screen(320, 240)
fe = H.make_frontend(page=0)
auftraege = fe.kategorie_logo_auftraege()
check("es kommen ueberhaupt Logo-Auftraege heraus", len(auftraege) > 0,
      "%d Auftraege" % len(auftraege))
check("alle zeigen in den sysart-Ordner",
      all(p.startswith(A.SYSART_BASE) for p, _w, _h in auftraege),
      str(auftraege[:2]))
check("alle haben dieselbe Kastengroesse (kein Text darunter)",
      len({(w, h) for _p, w, h in auftraege}) == 1,
      str({(w, h) for _p, w, h in auftraege}))

# Gegenprobe wie bei Test 1: fragt der Zeichenpfad wirklich genau diese
# Groesse an?
angefragt = []
_echt = A.ART.get_scaled


def _mit(pfad, mw, mh, _e=_echt):
    angefragt.append((pfad, mw, mh))
    return _e(pfad, mw, mh)


A.ART.get_scaled = _mit
try:
    fe.draw_page_cats()
finally:
    A.ART.get_scaled = _echt
vom_zeichnen = [a for a in angefragt if a[0].startswith(A.SYSART_BASE)]
check("der Zeichenpfad fragt ein Logo an", bool(vom_zeichnen))
if vom_zeichnen and auftraege:
    check("und zwar in derselben Kastengroesse wie der Vorauslader",
          vom_zeichnen[0][1:] == auftraege[0][1:],
          "Zeichnen=%s Vorauslader=%s"
          % (vom_zeichnen[0][1:], auftraege[0][1:]))
fe_py_2 = open(H.FRONTEND_PY, encoding="utf-8").read()
check("der Vorauslader wird auch auf der Hauptseite angestossen",
      "self.page in (0, 1)" in fe_py_2)
check('und "Miniaturen vorbereiten" nimmt die Logos mit',
      "kategorie_logo_auftraege()" in fe_py_2
      and fe_py_2.count("kategorie_logo_auftraege()") >= 3)


# ----------------------------------------------------------------------
print()
print("Test 9: die SONDERKATEGORIEN sind genauso abgedeckt")
# NUTZERWUNSCH (Build 75): "bitte auch die anderen bedenken wie die
# Kategorie Zuletzt gespielt, Weiterspielen, SMW Hacks, SNES ALTTP
# Tracker, Sammlungen, RA-Erfolgsjaeger, Zufalls-Zock, System - nicht
# dass da auch noch irgendwo was haengt, so wie jetzt erkannt auf der
# Hauptseite."
#
# Diese Kategorien sind der gefaehrliche Fall, weil sie ANDERS gebaut
# sind als ein normales System: sie haben KEINEN eigenen Systemkey
# (syskey=None), weil sie Spiele aus mehreren Systemen mischen. Der
# Systemkey steckt stattdessen in jedem Eintrag selbst
# (_item_syskey()). Wuerde der Vorauslader hier den Kategorie-Systemkey
# nehmen, suchte er die Cover im falschen Ordner - und wieder faellt es
# nicht auf, es bleibt nur langsam.
#
# In dieser Sandbox liegen keine echten ROMs, deshalb werden die
# Kategorien hier so nachgebaut, wie build_categories() sie anlegt:
# Name aus der Uebersetzungstabelle, syskey=None, Eintraege aus
# verschiedenen Systemen.
SONDER = [
    (fm.t("recent_cat"), "Zuletzt gespielt"),
    (fm.t("continue_cat"), "Weiterspielen"),
    (fm.t("favorites_cat"), "Favoriten"),
    ("%s (3)" % fm.t("collections_cat"), "Sammlungen"),
    ("%s (7)" % fm.t("ra_hunter_cat"), "RA-Erfolgsjaeger"),
]
GEMISCHT = [
    ("Super Mario World", "game", ("/f/smw.sfc", ".sfc", "SNES", None, None)),
    ("Sonic the Hedgehog", "game", ("/f/sonic.md", ".md", "Genesis", None, None)),
    ("Super Mario Land", "game", ("/f/sml.gb", ".gb", "GAMEBOY", None, None)),
    ("Castlevania - Symphony of the Night", "game",
     ("/f/sotn.cue", ".cue", "PSX", None, None)),
]
for w, h, aufl in ((320, 240, "CRT"), (1920, 1080, "HDMI")):
    for kat_name, klartext in SONDER:
        H.set_screen(w, h)
        fe = H.make_frontend(page=1)
        # Die Kategorie so umbauen, wie build_categories() sie anlegt.
        _name, node, _sk = fe.cats[fe.cat_i]
        fe.cats[fe.cat_i] = (kat_name, node, None)
        node["folders"] = {}
        node["items"] = list(GEMISCHT)
        node.pop("_display_items_cache", None)
        fe.item_i = 0
        fe.scroll = 0
        geo = fe._art_panel_geometrie()
        if geo is None:
            check("%s/%s: Boxart-Spalte vorhanden" % (aufl, klartext), False)
            continue
        angefragt = []
        _e = A.ART.get_scaled

        def _mit(pfad, mw, mh, _ee=_e):
            angefragt.append((pfad, mw, mh))
            return _ee(pfad, mw, mh)

        A.ART.get_scaled = _mit
        try:
            items = fe._display_items()
            alle_gleich = True
            details = ""
            for i in range(len(items)):
                fe.item_i = i
                angefragt.clear()
                fe.draw_page_items()
                gez = [a for a in angefragt if a[0].startswith(A.ART_BASE)
                       or a[0].startswith(A.ART_HD)]
                vorher = fe.cover_pfad_und_kasten(items[i], None, geo)
                if not gez or not vorher or tuple(gez[0]) != tuple(vorher):
                    alle_gleich = False
                    details = "Zeichnen=%s Vorauslader=%s" % (
                        gez[0] if gez else None, vorher)
                    break
        finally:
            A.ART.get_scaled = _e
        check("%s/%s: jeder Eintrag wird richtig vorhergesagt"
              % (aufl, klartext), alle_gleich, details)

print()
print("Test 9b: bei gemischten Kategorien zaehlt der Systemkey des EINTRAGS")
# Der eigentliche Stolperstein dieser Kategorien - hier ausdruecklich
# festgenagelt, damit niemand spaeter versehentlich auf den
# Kategorie-Systemkey zurueckfaellt.
H.set_screen(320, 240)
fe = H.make_frontend(page=1)
_name, node, _sk = fe.cats[fe.cat_i]
fe.cats[fe.cat_i] = (fm.t("recent_cat"), node, None)
node["folders"] = {}
node["items"] = list(GEMISCHT)
node.pop("_display_items_cache", None)
geo = fe._art_panel_geometrie()
pfade = [fe.cover_pfad_und_kasten(it, None, geo)[0] for it in GEMISCHT]
check("das SNES-Spiel wird im SNES-Ordner gesucht", "/SNES/" in pfade[0],
      pfade[0])
check("das Genesis-Spiel im Genesis-Ordner", "/Genesis/" in pfade[1],
      pfade[1])
check("das Game-Boy-Spiel im GAMEBOY-Ordner", "/GAMEBOY/" in pfade[2],
      pfade[2])
check("das PSX-Spiel im PSX-Ordner", "/PSX/" in pfade[3], pfade[3])

print()
print("Test 9c: die Logos der Sonderkategorien werden vorgewaermt")
# Diese Kategorien haben syskey=None, ihr Logo findet sich nur ueber
# _category_art_key() (CONTINUE.art, RECENT.art, COLLECTIONS.art,
# RA_HUNTER.art ...). Genau dieses CONTINUE.art war der 722-ms-Posten
# aus dem Log des Nutzers.
H.set_screen(320, 240)
fe = H.make_frontend(page=0)
node = fe.cats[0][1]
fe.cats = [(kat_name, node, None) for kat_name, _kl in SONDER] + [
    (fm.t("wot_cat"), node, None) if hasattr(fm, "t") else fe.cats[0]]
auftraege = fe.kategorie_logo_auftraege()
namen = {os.path.basename(p) for p, _w, _h in auftraege}
for erwartet in ("CONTINUE.art", "RECENT.art", "FAVORITES.art",
                 "COLLECTIONS.art", "RA_HUNTER.art"):
    check("%s steht in der Vorwaermliste" % erwartet, erwartet in namen,
          str(sorted(namen)))

shutil.rmtree(TMP, ignore_errors=True)

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for f in fails:
        print("   ", f)
    sys.exit(1)
print("Alle Tests bestanden.")
