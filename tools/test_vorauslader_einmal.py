#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Der Vorauslader sieht jeden Eintrag einmal an - und der Coverflow wird vorbereitet, wenn man ihn benutzt (Build 322).

DER ANLASS steht im Log vom 14.11.:

    EINGABE-STAU: down lag 488 ms ungelesen beim Kernel (21.5 s nach dem
    Start; laengste Leerlauf-Arbeit davor: Vorauslader 462 ms)

_prewarm_anstossen() rief auftraege_bauen() je Kastengroesse zweimal -
fuer das Fehlende und (schon_da=True) fuer den Nachlade-Faden -, beide
Male mit demselben kastenmass(). Im Coverflow sind das drei
Kastengroessen, also sechs Durchgaenge auf dem Hauptfaden.

Und seine Frage: "kann es sein das bei denn miniaturen die neuen hdmi
ansichten nicht mit vorbereitet werden?" - ja: "Miniaturen vorbereiten"
nahm den Coverflow nur mit, wenn er die VORGABE war.

GEPRUEFT WIRD:
  1. auftraege_und_nachladen() liefert genau dasselbe wie zwei Aufrufe
     von auftraege_bauen() - an zufaelligen Listen, vorwaerts und
     rueckwaerts, mit Luecken und fehlenden Covern.
  2. kastenmass() und der Blick auf die Karte laufen je Eintrag EINMAL.
  3. zwischendurch() kann abbrechen; zurueck kommt, was bis dahin
     feststand (ein Anfang der vollen Listen).
  4. Von der anderen Seite: _prewarm_anstossen() fragt
     cover_pfad_und_kasten() je Eintrag und Kasten einmal (vorher
     zweimal), uebergibt dieselben Listen und bricht bei einer Eingabe
     ab.
  5. vorbereitungs_kaesten(): der Coverflow kommt mit, wenn er in dieser
     Sitzung benutzt wurde - GEGENPROBE ohne: nicht.

Ausfuehren:
    python3 tools/test_vorauslader_einmal.py
"""
import os
import random
import sys

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
sys.path.insert(0, _HIER)

import _harness as H                                     # noqa: E402

fm = H.fm
import fe.prewarm as P                                   # noqa: E402
import fe.art as A                                       # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


print(__doc__.strip().split("\n")[0])
print()

# ---------------------------------------------------------------------------
print("Test 1: dasselbe Ergebnis wie zwei Aufrufe von auftraege_bauen()")
# ---------------------------------------------------------------------------
random.seed(322)
_echt_has = P.thumb_cache_has
abw = 0
faelle = 0
try:
    for _ in range(400):
        n = random.randint(0, 60)
        eintraege = ["spiel%03d" % i for i in range(n)]
        auf_karte = {e for e in eintraege if random.random() < 0.5}
        ohne_cover = {e for e in eintraege if random.random() < 0.15}
        P.thumb_cache_has = lambda p, w, h, _k=auf_karte: p in _k

        def mass(e, _o=ohne_cover):
            return None if e in _o else (e, 100, 140)

        mitte = random.randint(0, max(0, n - 1))
        vor = random.random() < 0.5
        voraus = random.choice((5, 20, 40))
        a = P.auftraege_bauen(eintraege, mitte, mass, vorwaerts=vor,
                              voraus=voraus)
        b = P.auftraege_bauen(eintraege, mitte, mass, vorwaerts=vor,
                              voraus=voraus, schon_da=True)
        f, d = P.auftraege_und_nachladen(eintraege, mitte, mass,
                                         vorwaerts=vor, voraus=voraus)
        faelle += 1
        if (f, d) != (a, b):
            abw += 1
finally:
    P.thumb_cache_has = _echt_has
check("%d zufaellige Listen, keine Abweichung" % faelle, abw == 0, abw)

# ---------------------------------------------------------------------------
print()
print("Test 2: jeder Eintrag einmal")
# ---------------------------------------------------------------------------
gefragt = {"mass": 0, "karte": 0}
eintraege = ["spiel%03d" % i for i in range(80)]


def _mass(e):
    gefragt["mass"] += 1
    return (e, 100, 140)


def _has(p, w, h):
    gefragt["karte"] += 1
    return p.endswith("0")


P.thumb_cache_has = _has
try:
    gefragt.update(mass=0, karte=0)
    P.auftraege_bauen(eintraege, 30, _mass)
    P.auftraege_bauen(eintraege, 30, _mass, schon_da=True)
    vorher = dict(gefragt)
    gefragt.update(mass=0, karte=0)
    f, d = P.auftraege_und_nachladen(eintraege, 30, _mass)
    nachher = dict(gefragt)
finally:
    P.thumb_cache_has = _echt_has
check("vorher: jeder Eintrag zweimal (20 voraus + 6 zurueck = 26)",
      vorher == {"mass": 52, "karte": 52}, vorher)
check("jetzt: einmal", nachher == {"mass": 26, "karte": 26}, nachher)

# ---------------------------------------------------------------------------
print()
print("Test 3: zwischendurch bricht ab")
# ---------------------------------------------------------------------------
P.thumb_cache_has = lambda p, w, h: p.endswith("0")
try:
    voll_f, voll_d = P.auftraege_und_nachladen(eintraege, 30,
                                               lambda e: (e, 1, 1))
    zaehler = [0]

    def _zw():
        zaehler[0] += 1
        if zaehler[0] >= 2:
            raise RuntimeError("Taste")

    f, d = P.auftraege_und_nachladen(eintraege, 30, lambda e: (e, 1, 1),
                                     zwischendurch=_zw)
finally:
    P.thumb_cache_has = _echt_has
check("zwischendurch alle acht Eintraege gerufen", zaehler[0] == 2,
      zaehler[0])
check("abgebrochen: weniger als die volle Liste",
      len(f) + len(d) < len(voll_f) + len(voll_d),
      "%d von %d" % (len(f) + len(d), len(voll_f) + len(voll_d)))
check("und es ist der Anfang der vollen Listen",
      f == voll_f[:len(f)] and d == voll_d[:len(d)])

# ---------------------------------------------------------------------------
print()
print("Test 4: _prewarm_anstossen() von der anderen Seite")
# ---------------------------------------------------------------------------
H.set_screen(1920, 1080)
titel = ["Spiel Nummer %03d" % i for i in range(60)]
f = H.make_frontend(page=1, titles=titel)
f.item_i = 10
uebergeben = {"prewarm": None, "lader": None}
_echt_pw = fm.PREWARMER


class PrewarmAttrappe(object):
    def start(self):
        pass

    def uebergeben(self, a):
        uebergeben["prewarm"] = list(a)


class LaderAttrappe(object):
    def start(self):
        pass

    def uebergeben(self, a):
        uebergeben["lader"] = list(a)

    def abholen(self, *a):
        return []

    def abbrechen(self):
        pass


fm.PREWARMER = PrewarmAttrappe()
f.lader = LaderAttrappe()
gezaehlt = {}
_echt_cpk = f.cover_pfad_und_kasten


def _cpk(item, syskey, geo):
    k = (item[0], geo)
    gezaehlt[k] = gezaehlt.get(k, 0) + 1
    return ("/cover/%s.png" % item[0], 200, 280)


f.cover_pfad_und_kasten = _cpk
_echt_has_fm = fm.thumb_cache_has
_echt_has_p = P.thumb_cache_has
_karte = lambda p, w, h: p.endswith("1.png") or p.endswith("3.png")
P.thumb_cache_has = _karte


class InpAttrappe(object):
    def __init__(self, ja):
        self.ja = ja

    def eingabe_anstehend(self):
        return self.ja


_echt_inp = f.inp
# Build 324: der Vorauslader ueberspringt Systeme, deren Cover-Verzeichnis
# noch nicht steht (Test 7). Hier soll es stehen.
_echt_bereit = fm.cover_index_bereit
fm.cover_index_bereit = lambda sk: True
try:
    for ansicht in ("liste", "coverflow"):
        f.ansicht_setzen(ansicht)
        gezaehlt.clear()
        uebergeben.update(prewarm=None, lader=None)
        f.inp = InpAttrappe(False)
        f._prewarm_anstossen()
        geos = f._ansicht_geometrien(f.aktuelle_ansicht())
        mehrfach = [k for k, v in gezaehlt.items() if v > 1]
        check("%s: %d Kaesten, jeder Eintrag je Kasten genau einmal"
              % (ansicht, len(geos)), gezaehlt and not mehrfach,
              "%d Abfragen, %d doppelt" % (sum(gezaehlt.values()),
                                           len(mehrfach)))
        erw_f, erw_d = [], []
        for g in geos:
            a_ = P.auftraege_bauen(f._display_items(), f.item_i,
                                   lambda it, _g=g: _cpk(it, None, _g),
                                   vorwaerts=True, voraus=20)
            b_ = P.auftraege_bauen(f._display_items(), f.item_i,
                                   lambda it, _g=g: _cpk(it, None, _g),
                                   vorwaerts=True, voraus=20, schon_da=True)
            erw_f += a_
            erw_d += [n for n in b_ if not A.ART.im_ram(*n)]
        check("%s: dieselbe Auftragsliste wie mit zwei Durchgaengen"
              % ansicht, uebergeben["prewarm"] == erw_f,
              "%s gegen %s" % (len(uebergeben["prewarm"] or []),
                               len(erw_f)))
        check("%s: dieselbe Nachladeliste" % ansicht,
              uebergeben["lader"] == (erw_d or None),
              "%s gegen %s" % (len(uebergeben["lader"] or []), len(erw_d)))
    f.ansicht_setzen("coverflow")
    gezaehlt.clear()
    f.inp = InpAttrappe(True)
    f._prewarm_anstossen()
    check("steht eine Eingabe an: nach dem ersten Happen Schluss",
          0 < sum(gezaehlt.values()) <= 8, sum(gezaehlt.values()))
finally:
    fm.PREWARMER = _echt_pw
    P.thumb_cache_has = _echt_has_p
    f.cover_pfad_und_kasten = _echt_cpk
    f.inp = _echt_inp
    fm.cover_index_bereit = _echt_bereit

# ---------------------------------------------------------------------------
print()
print("Test 5: der Coverflow wird vorbereitet, wenn man ihn benutzt")
# ---------------------------------------------------------------------------
f2 = H.make_frontend(page=1, titles=titel)
_echt_lesen = fm.ansicht_lesen
fm.ansicht_lesen = lambda: "liste"
try:
    f2._ansicht_je_kat = {}
    ohne = f2.vorbereitungs_kaesten()
    flow = f2._ansicht_geometrien("coverflow", erzwingen=True)
    f2.ansicht_setzen("coverflow")
    mit = f2.vorbereitungs_kaesten()
finally:
    fm.ansicht_lesen = _echt_lesen
check("es gibt Coverflow-Kaesten (HDMI)", len(flow) == 3, flow)
check("GEGENPROBE: nie benutzt und nicht Vorgabe - nicht dabei",
      not any(g in ohne for g in flow), ohne)
check("in dieser Sitzung benutzt - alle drei dabei",
      all(g in mit for g in flow), mit)

# ---------------------------------------------------------------------------
print()
print("Test 6: die Hauptseite rechnet ihre Liste einmal (Build 324)")
# ---------------------------------------------------------------------------
# Im Log vom 15.11.: "laengste Leerlauf-Arbeit davor: Vorauslader 705 ms"
# - auf der Hauptseite, nach jeder Pause von vorn.
f3 = H.make_frontend(page=0)
f3.cats = [(k, {"items": [], "folders": {}}, k)
           for k in ("NES", "SNES", "GBA", "PSX", "N64", "ARCADE")]
f3._last_input_time = 0
A.ART.auslagern = None
uebergeben.update(prewarm=None, lader=None)
fm.PREWARMER = PrewarmAttrappe()
f3.lader = LaderAttrappe()
f3.inp = InpAttrappe(False)
gefragt_karte = [0]
_auf_karte = set()


def _has_f3(p, w, h):
    gefragt_karte[0] += 1
    return (p, w, h) in _auf_karte


_echt_has_fm = fm.thumb_cache_has
fm.thumb_cache_has = _has_f3
try:
    alt_auftraege = f3.kategorie_logo_auftraege()
    alt_nachladen = [a for a in f3.kategorie_logo_alle()
                     if a in _auf_karte and not A.ART.im_ram(*a)]
    gefragt_karte[0] = 0
    f3._prewarm_hauptseite()
    erster = gefragt_karte[0]
    check("erster Durchgang: dieselbe Auftragsliste wie bisher",
          uebergeben["prewarm"] == alt_auftraege,
          "%d gegen %d" % (len(uebergeben["prewarm"] or []),
                           len(alt_auftraege)))
    check("und dieselbe Nachladeliste (leer, nichts liegt da)",
          (uebergeben["lader"] or []) == alt_nachladen)
    # Jetzt liegt alles auf der Karte (der Vorauslader hat gerechnet).
    _auf_karte.update(alt_auftraege)
    gefragt_karte[0] = 0
    f3._prewarm_hauptseite()
    zweiter = gefragt_karte[0]
    gefragt_karte[0] = 0
    uebergeben.update(prewarm=None, lader=None)
    f3._prewarm_hauptseite()
    dritter = gefragt_karte[0]
    check("zweiter Durchgang: jede fehlende einmal nachgefragt",
          zweiter == erster, "%d / %d" % (zweiter, erster))
    check("dritter Durchgang: KEINE Frage mehr an die Karte",
          dritter == 0 and uebergeben["prewarm"] is None, dritter)
    check("und das Nachladen bekommt, was nur im Speicher fehlt",
          uebergeben["lader"] == [a for a in f3.kategorie_logo_alle()
                                  if not A.ART.im_ram(*a)])
    f3.logo_vorrat_vergessen()
    gefragt_karte[0] = 0
    f3._prewarm_hauptseite()
    check("GEGENPROBE: nach 'Zwischenspeicher leeren' wird neu gefragt",
          gefragt_karte[0] == erster, gefragt_karte[0])
    f3.logo_vorrat_vergessen()
    f3.inp = InpAttrappe(True)
    gefragt_karte[0] = 0
    f3._prewarm_hauptseite()
    check("steht eine Eingabe an: nach dem ersten Happen Schluss",
          0 < gefragt_karte[0] <= 8, gefragt_karte[0])
finally:
    fm.thumb_cache_has = _echt_has_fm
    fm.PREWARMER = _echt_pw

# ---------------------------------------------------------------------------
print()
print("Test 7: kein Namensverzeichnis nebenbei (Build 324)")
# ---------------------------------------------------------------------------
f4 = H.make_frontend(page=1, titles=titel)
f4.item_i = 10
fm.PREWARMER = PrewarmAttrappe()
f4.lader = LaderAttrappe()
f4.inp = InpAttrappe(False)
gefragt = [0]


def _cpk4(item, syskey, geo):
    gefragt[0] += 1
    return ("/cover/%s.png" % item[0], 200, 280)


f4.cover_pfad_und_kasten = _cpk4
_echt_bereit = fm.cover_index_bereit
try:
    fm.cover_index_bereit = lambda sk: False
    f4._prewarm_anstossen()
    check("Verzeichnis fehlt: kein einziger Cover-Pfad bestimmt",
          gefragt[0] == 0, gefragt[0])
    fm.cover_index_bereit = lambda sk: True
    f4._prewarm_anstossen()
    check("GEGENPROBE: Verzeichnis steht - dann schon", gefragt[0] > 0,
          gefragt[0])
finally:
    fm.cover_index_bereit = _echt_bereit
    fm.PREWARMER = _echt_pw
A.INDEX_WARM_WURZELN, _wz = ("/x/hd", "/x/base"), A.INDEX_WARM_WURZELN
try:
    A._art_index_cache.pop(("/x/hd", "TESTSYS"), None)
    A._art_index_cache.pop(("/x/base", "TESTSYS"), None)
    A._docs_index_cache.pop("TESTSYS", None)
    vorher = A.cover_index_bereit("TESTSYS")
    A._art_index_cache[("/x/hd", "TESTSYS")] = {}
    A._art_index_cache[("/x/base", "TESTSYS")] = {}
    halb = A.cover_index_bereit("TESTSYS")
    A._docs_index_cache["TESTSYS"] = {}
    ganz = A.cover_index_bereit("TESTSYS")
finally:
    A.INDEX_WARM_WURZELN = _wz
    for k in (("/x/hd", "TESTSYS"), ("/x/base", "TESTSYS")):
        A._art_index_cache.pop(k, None)
    A._docs_index_cache.pop("TESTSYS", None)
check("cover_index_bereit: erst nein, halb nein, ganz ja",
      (vorher, halb, ganz) == (False, False, True), (vorher, halb, ganz))

print()
if fails:
    print("ROT: %d Pruefung(en) fehlgeschlagen:" % len(fails))
    for f_ in fails:
        print("   - " + f_)
    sys.exit(1)
print("ALLES GRUEN")
