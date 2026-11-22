#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Die Vorfuehrung: Dragend in sechs Kapiteln (Build 345).

NUTZERWUNSCH: --show und --demo zusammenfuehren, thematische
Praesentationsseiten statt Textseiten, die Geschwindigkeit ehrlich
(gemessene Werte, keine pauschale Bewertung), Einstellungen in Gruppen,
eine Design-Vorschau, Weiter/Zurueck/Blaettern, Fortschrittsbalken und
eine Abschlussseite.

GEPRUEFT WIRD:
  1. Jede Aktion aus fe/menu.py steht in GENAU einer der sechs Gruppen;
     jede Gruppe hat Name und Erklaerung in beiden Sprachen.
  2. Die Gruppierung liest das echte Systemmenue - mit den Werten von
     jetzt, ohne etwas zu verlieren.
  3. Alle Seiten zeichnen sich in vier Aufloesungen (1080p bis Roehre),
     der Fortschrittsbalken zeigt das Kapitel, die Fusszeile passt in
     die Zeile, lange Namen werden auf schmalem Schirm nicht
     abgeschnitten.
  4. Die Geschwindigkeit: gemessen mit der Schrittfunktion des Bench,
     "gehalten" gerechnet mit den Funktionen aus fe/input.py, eine
     Taste bricht die Messung ab, die Position bleibt.
  5. Die Tasten: weiter, zurueck, von vorn, Ende (Esc, B halten, B auf
     der ersten Seite); jede Taste schaltet auf Handbetrieb.
  6. Ein ganzer Durchlauf ohne Taste kommt zum Ende; danach steht alles
     wie vorher: Seite, Position, Ansichten, Farbschema - und nichts
     wurde geschrieben (Farbschema-Datei, Merkdatei der Ansichten).
  7. Mit Tasten: weiter, dann Ende - die Vorfuehrung endet dort.
  8. Die Design-Vorschau zeigt nur freigeschaltete Schemata.
  9. Menuepunkt, Behandlung, Uebersetzung, --show/--demo.

Ausfuehren:
    python3 tools/test_vorfuehrung.py
"""
import os
import re
import sys
import time

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
sys.path.insert(0, _HIER)
import _harness as H                                     # noqa: E402

import fe.vorfuehrung as V                               # noqa: E402
import fe.bench as B                                     # noqa: E402
import fe.settings as S                                  # noqa: E402
import fe.menu as M                                      # noqa: E402
import fe.masken as MA                                   # noqa: E402
import fe.schriften as SC                                # noqa: E402
import fe.art as A                                       # noqa: E402
import fe.demo as DEMO                                   # noqa: E402

fm = H.fm
fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


def neu(fe, **k):
    return V.Vorfuehrung(fe, fm, S, B, M, MA, SC, A, **k)


print(__doc__.strip().split("\n")[0])
print()
# ---------------------------------------------------------------------------
print("Test 1: jede Aktion in genau einer Gruppe")
# ---------------------------------------------------------------------------
MENU_Q = open(os.path.join(_REPO, "frontend", "fe", "menu.py"),
              encoding="utf-8").read()
_i = MENU_Q.index("    ra_items")
_j = MENU_Q.index("\n    }\n", MENU_Q.index("    groups = {"))
aktionen = set(re.findall(r'"([a-z0-9_]+)",\s*None\)', MENU_Q[_i:_j]))
aktionen |= {"nachscan", "core_neu"}          # entstehen erst zur Laufzeit
check("Aktionen gefunden", len(aktionen) > 80, len(aktionen))
ohne = sorted(a for a in aktionen if V.gruppe_von(a) is None)
check("keine Aktion ohne Gruppe", not ohne, ohne)
alle = [k for g in V.GRUPPEN for k in g[3]]
doppelt = sorted(set(k for k in alle if alle.count(k) > 1))
check("keine Aktion in zwei Gruppen", not doppelt, doppelt)
check("sechs Gruppen", len(V.GRUPPEN) == 6)
check("Name und Erklaerung in beiden Sprachen, gezeigte Werte gehoeren "
      "zur Gruppe",
      all(len(g[1]) == 2 and all(g[1]) and len(g[2]) == 2 and all(g[2])
          and set(g[4]) <= set(g[3]) for g in V.GRUPPEN))
check("die Vorfuehrung selbst ist eingeordnet",
      V.gruppe_von("vorfuehrung") == "system")

# ---------------------------------------------------------------------------
print()
print("Test 2: gruppiert aus dem echten Systemmenue")
# ---------------------------------------------------------------------------
gr = V.einstellungen_gruppiert(M)


def zaehle(k, t=0):
    n = 0
    for u in (k.get("folders") or {}).values():
        n += zaehle(u, t + 1)
    return n + sum(1 for e in k.get("items", ()) if isinstance(e[1], str))


check("nichts verloren", sum(len(v) for v in gr.values())
      == zaehle(M.system_items()))
check("jede Gruppe hat Eintraege", all(gr[g[0]] for g in V.GRUPPEN),
      dict((k, len(v)) for k, v in gr.items()))
check("Werte stehen vor dem Pfeil",
      V.wert_aus_beschriftung("Farbschema: Dunkel -> nächstes")
      == "Farbschema: Dunkel" and V.wert_aus_beschriftung("Musik") == "Musik")

# ---------------------------------------------------------------------------
print()
print("Test 3: alle Seiten in vier Aufloesungen")
# ---------------------------------------------------------------------------
messung_fest = [{"seite": 0, "ansicht": "liste", "ms": 21.7,
                 "schritte_s": 46.1, "iv_ms": 40.0, "sprung": 1,
                 "zeilen_s": 25.0},
                {"seite": 1, "ansicht": "galerie", "ms": 32.1,
                 "schritte_s": 31.2, "iv_ms": 36.9, "sprung": 1,
                 "zeilen_s": 27.1}]
fehler = []
for W, Hh in ((1920, 1080), (1280, 720), (640, 480), (320, 240)):
    H.set_screen(W, Hh)
    fe = H.make_frontend(page=0)
    fe._startdauer = 1.9
    v = neu(fe, messung=messung_fest)
    v.oeffnen = (83.0, "Commodore 64", 2139)
    for name in ("willkommen", "sammlung", "designs", "einstellungen",
                 "tempo", "dein", "ergebnis"):
        try:
            seite = getattr(v, "seite_" + name)()
            mx = seite.zeichnen(fe, fm, 0, True)
            mx2 = seite.zeichnen(fe, fm, 999, True)
            if bytes(fe.fb.mm) != bytes(fe.fb.buf):
                fehler.append((W, name, "nicht geflippt"))
            if mx2 != mx or mx < 0:
                fehler.append((W, name, "scroll", mx, mx2))
            # Fortschrittsbalken: genau 'kapitel' Segmente in Akzentfarbe
            lw = V.Leinwand(fe, fm)
            y = lw.oy + 10 * lw.s
            n = len(V.KAPITEL)
            luecke = max(2, 2 * lw.s)
            sw = (lw.breite - (n - 1) * luecke) // n
            akzent = fe.fb.px(lw.akzent)
            gefuellt = 0
            for i in range(n):
                x = lw.ox + i * (sw + luecke) + sw // 2
                o = y * fe.fb.stride + x * 4
                if bytes(fe.fb.buf[o:o + 4]) == akzent:
                    gefuellt += 1
            if gefuellt != seite.kapitel:
                fehler.append((W, name, "Balken", gefuellt, seite.kapitel))
        except Exception as e:                           # noqa: BLE001
            fehler.append((W, name, repr(e)))
    # Fusszeile passt
    lw = V.Leinwand(fe, fm)
    for oben, unten in ((False, False), (True, True)):
        gemerkt = []
        _echt = lw.schrift
        lw.schrift = (lambda x, y, text, *a, **k:
                      gemerkt.append(str(text)))
        V.fuss_zeichnen(lw, None, oben, unten)
        lw.schrift = _echt
        if not gemerkt or len(gemerkt[-1]) > lw.zeichen:
            fehler.append((W, "Fusszeile", gemerkt))
check("alle Seiten, alle Aufloesungen, Balken und Fusszeile stimmen",
      not fehler, fehler[:5])
H.set_screen(320, 240)
fe = H.make_frontend(page=0)
lw = V.Leinwand(fe, fm)
seite = V.Seite(1, "X", [("kv", "Ansicht Hauptseite ganz lang", "Liste")])
zeilen = seite.alle_zeilen(lw)
gezeichnet = []
lw.schrift = lambda x, y, text, *a, **k: gezeichnet.append((x, str(text)))
for _h, z in zeilen:
    z(0)
check("schmaler Schirm: langer Name auf eigener Zeile, nichts abgeschnitten",
      ("Ansicht Hauptseite ganz lang" in [t for _x, t in gezeichnet])
      and len(zeilen) == 2, gezeichnet)
H.set_screen(1920, 1080)

# ---------------------------------------------------------------------------
print()
print("Test 4: die Geschwindigkeit")
# ---------------------------------------------------------------------------
fe = H.make_frontend(page=1)
fe.item_i = 3
vorher = (fe.page, fe.cat_i, fe.item_i, list(fe.nav_path))
fe.inp._sprung_je_akt = {"down": 3, "up": 2}
fe.ansicht_haupt_setzen("liste")
fe.ansicht_setzen("liste")
je_kat4, haupt4 = dict(fe._ansicht_je_kat), fe._ansicht_haupt
if os.path.exists(S.ANSICHTEN_BENUTZT_FILE):
    os.remove(S.ANSICHTEN_BENUTZT_FILE)
merken4 = fm.ansicht_benutzt_merken
# Auf Stufe 3x, damit "gehalten" sich von der blossen Untergrenze
# unterscheidet - so faellt auf, wenn die Rechnung der Bedienung fehlt.
_tempo_echt = S.load_scroll_tempo
S.load_scroll_tempo = lambda: 3.0
messung, (kat_name, kat_n) = V.tempo_messen(fe, S, B, schritte=4)
check("die Messung merkt keine Ansicht als benutzt (auch fuer --show)",
      not os.path.exists(S.ANSICHTEN_BENUTZT_FILE)
      and fm.ansicht_benutzt_merken is merken4)
check("und die Ansichten der Sitzung stehen danach wie vorher",
      fe._ansicht_je_kat == je_kat4 and fe._ansicht_haupt == haupt4,
      (fe._ansicht_je_kat, fe._ansicht_haupt))
check("die Sprungweite der echten Eingabe bleibt, wie sie war",
      fe.inp._sprung_je_akt == {"down": 3, "up": 2}, fe.inp._sprung_je_akt)
check("gemessen, mit allen Feldern",
      messung and all(set(m) >= {"seite", "ansicht", "ms", "schritte_s",
                                 "iv_ms", "sprung", "zeilen_s"}
                      for m in messung), messung[:1])
check("Position danach unveraendert",
      (fe.page, fe.cat_i, fe.item_i, list(fe.nav_path)) == vorher)
import fe.input as I                                     # noqa: E402
m0 = messung[0]
g = m0["ms"] / 1000.0
boden = min(I.REPEAT_FLOOR_MAX, max(I.REPEAT_FLOOR_MIN,
                                    g * I.REPEAT_MESS_RESERVE))
iv = fe.inp._tempo_anwenden(boden, g, I.REPEAT_FLOOR_MIN, False)
S.load_scroll_tempo = _tempo_echt
check("'gehalten' wie im Betrieb gerechnet (Stufe 3x)",
      abs(m0["iv_ms"] - iv * 1000.0) < 0.01
      and abs(m0["zeilen_s"] - 1000.0 / (iv * 1000.0) * m0["sprung"]) < 0.01
      and abs(iv - boden) > 1e-6,
      (m0["iv_ms"], iv * 1000.0, boden * 1000.0))
q = open(V.__file__, encoding="utf-8").read()
check("mit der Schrittfunktion des Bench",
      "BENCH.schritt_funktion(fe, seite)" in q
      and "BENCH.fenster_spanne(fe, seite)" in q)
gefragt = [0]


def abbrechen():
    gefragt[0] += 1
    return gefragt[0] > 1
teil, _k = V.tempo_messen(fe, S, B, schritte=2, abbrechen=abbrechen)
check("eine Taste bricht ab - mit dem, was da ist",
      len(teil) == 1, len(teil))
from _quelle import nur_code                              # noqa: E402
check("kein Vergleich mit 16,7 ms auf den Seiten (nur im Kommentar, "
      "der erklaert, warum nicht)",
      "16,7" not in nur_code(q) and "60 Hz" not in nur_code(q))
show_q = open(os.path.join(_REPO, "frontend", "fe", "show.py"),
              encoding="utf-8").read()
check("und auch nicht mehr im Textbericht",
      "fluessig" not in nur_code(show_q) and "16,7" not in nur_code(show_q)
      and "VORF.tempo_messen(" in show_q)

# ---------------------------------------------------------------------------
print()
print("Test 5: die Tasten")
# ---------------------------------------------------------------------------
fe = H.make_frontend(page=0)
v = neu(fe)
n = 10
ergebnisse = {}
for akt, i in (("right", 3), ("ok", 3), ("left", 3), ("left", 0),
               ("back", 3), ("back", 0), ("exit", 5), ("select", 5),
               ("favorite", 5)):
    v.auto = True
    ergebnisse[(akt, i)] = (v._taste_behandeln(akt, i, n), v.auto)
erwartet = {("right", 3): 4, ("ok", 3): 4, ("left", 3): 2, ("left", 0): None,
            ("back", 3): 2, ("back", 0): None, ("exit", 5): None,
            ("select", 5): 0, ("favorite", 5): 5}
check("weiter, zurueck, von vorn, Ende, hier bleiben",
      all(ergebnisse[k][0] == w for k, w in erwartet.items()),
      dict((k, v_[0]) for k, v_ in ergebnisse.items()))
check("jede Taste schaltet auf Handbetrieb",
      all(not a for _n, a in ergebnisse.values()))
_echt_geh = V.taste_gehalten
try:
    V.taste_gehalten = lambda inp, codes: True
    _echt_sleep = fm.time.sleep
    fm.time.sleep = lambda d: H.NOW.__setitem__(0, H.NOW[0] + d)
    try:
        r = v._taste_behandeln("back", 4, n)
    finally:
        fm.time.sleep = _echt_sleep
finally:
    V.taste_gehalten = _echt_geh
check("B gehalten: Ende", r is None)


class FakeGeraet(object):
    fd = -1


class FakeInp(object):
    devices = {"x": FakeGeraet()}
check("ohne lesbares Geraet ist nichts gehalten",
      V.taste_gehalten(FakeInp(), [305]) is False)
r_fd, w_fd = os.pipe()
try:
    class PipeGeraet(object):
        fd = r_fd
    FakeInp.devices = {"p": PipeGeraet()}
    check("ein Geraet ohne EVIOCGKEY: auch nichts",
          V.taste_gehalten(FakeInp(), [305]) is False)
finally:
    os.close(r_fd)
    os.close(w_fd)

# ---------------------------------------------------------------------------
print()
print("Test 6: ein ganzer Durchlauf ohne Taste - und alles wie vorher")
# ---------------------------------------------------------------------------
fe = H.make_frontend(page=1)
fe.item_i = 2
fe.ansicht_setzen("raster")
fe.ansicht_haupt_setzen("liste")
vorher = dict((f, getattr(fe, f)) for f in ("page", "cat_i", "item_i",
                                            "nav_path"))
je_kat = dict(fe._ansicht_je_kat)
haupt = fe._ansicht_haupt
bg = fm.C_BG
merk_datei = S.ANSICHTEN_BENUTZT_FILE
# Leer anfangen: so faellt JEDER Eintrag auf, den die Vorfuehrung schriebe.
if os.path.exists(merk_datei):
    os.remove(merk_datei)
merk_vorher = None
theme_vorher = (open(fm.THEME_FILE).read() if os.path.exists(fm.THEME_FILE)
                else None)
merken_echt = fm.ansicht_benutzt_merken
meldungen = []
v = neu(fe, log=meldungen.append, tempo=0.01)
# Der Pruefstand friert die Uhr ein (tools/_harness.py). Die echten
# Bildschirme der Live-Stationen warten aber auf die Uhr (fe/demo.py:
# _Hand) - hier laeuft sie deshalb mit jedem Blick ein wenig weiter.
_echt_mono = fm.time.monotonic


def _laufende_uhr():
    H.NOW[0] += 0.005
    return H.NOW[0]
fm.time.monotonic = _laufende_uhr
t0 = time.time()
try:
    ok = v.lauf()
finally:
    fm.time.monotonic = _echt_mono
dauer = time.time() - t0
check("kommt von selbst zum Ende", ok is True, (dauer, meldungen[-2:]))
check("in vertretbarer Zeit (Pruefstand)", dauer < 240, "%.0f s" % dauer)
check("Seite und Position wie vorher",
      dict((f, getattr(fe, f)) for f in vorher) == vorher,
      dict((f, getattr(fe, f)) for f in vorher))
check("Ansichten der Sitzung wie vorher",
      fe._ansicht_je_kat == je_kat and fe._ansicht_haupt == haupt,
      (fe._ansicht_je_kat, je_kat))
check("Farbschema wie vorher", fm.C_BG == bg)
check("nichts geschrieben: Merkdatei der Ansichten",
      (open(merk_datei).read() if os.path.exists(merk_datei) else None)
      == merk_vorher)
check("nichts geschrieben: Farbschema-Datei",
      (open(fm.THEME_FILE).read() if os.path.exists(fm.THEME_FILE)
       else None) == theme_vorher)
check("das Merken der Ansichten ist wieder das echte",
      fm.ansicht_benutzt_merken is merken_echt)
check("gemessen wurde dabei", bool(v.messung), len(v.messung or []))
check("Log: Beginn und Ende",
      any("beginnt" in m for m in meldungen)
      and any("durchgelaufen" in m for m in meldungen))

# ---------------------------------------------------------------------------
print()
print("Test 7: mit Tasten")
# ---------------------------------------------------------------------------


class Skript(object):
    """Liefert die Tasten der Reihe nach, dann nichts mehr."""

    def __init__(self, echt, tasten):
        self.echt = echt
        self.tasten = list(tasten)

    def __getattr__(self, n):
        return getattr(self.echt, n)

    def read_action(self, timeout=None):
        if self.tasten:
            return self.tasten.pop(0)
        return "exit"
fe = H.make_frontend(page=0)
echt_inp = fe.inp
fe.inp = Skript(echt_inp, ["right", "down", "exit"])
meldungen = []
v = neu(fe, log=meldungen.append, tempo=0.01)
fm.time.monotonic = _laufende_uhr
try:
    ok = v.lauf()
finally:
    fe.inp = echt_inp
    fm.time.monotonic = _echt_mono
check("weiter, dann Ende: endet auf der zweiten Seite",
      ok is False and any("beendet bei Schritt sammlung" in m
                          for m in meldungen), meldungen[-2:])
check("und steht danach im Handbetrieb", v.auto is False)
DEMO.LETZTE_TASTE[0] = None
fe.inp = Skript(echt_inp, ["left"])
try:
    DEMO._warten(fe, 1.0)
finally:
    fe.inp = echt_inp
check("eine Station meldet, WELCHE Taste es war",
      DEMO.LETZTE_TASTE[0] == "left")


class Kaputt(object):
    """Erst eine Taste (schaltet in den Handbetrieb), dann klemmt sie."""

    def __init__(self, echt):
        self.echt = echt
        self.n = 0

    def __getattr__(self, n):
        return getattr(self.echt, n)

    def read_action(self, timeout=None):
        self.n += 1
        if self.n == 1:
            return "right"
        raise OSError("Geraet weg")
kaputt = Kaputt(echt_inp)
fe.inp = kaputt
meldungen = []
v = neu(fe, log=meldungen.append, tempo=0.01)
_alle = v.schritte
v.schritte = lambda: [st_ for st_ in _alle() if st_.art == "seite"][:3]
t0 = time.time()
fm.time.monotonic = _laufende_uhr
try:
    ok = v.lauf()
finally:
    fm.time.monotonic = _echt_mono
check("klemmt die Eingabe im Handbetrieb: laeuft von selbst zu Ende",
      ok is True and time.time() - t0 < 60, (ok, meldungen[-2:]))
check("und fragt die kaputte Eingabe nicht weiter", kaputt.n == 2, kaputt.n)
check("fe.inp bleibt fuer das Frontend erhalten", fe.inp is kaputt)
fe.inp = echt_inp

# ---------------------------------------------------------------------------
print()
print("Test 8: nur freigeschaltete Schemata")
# ---------------------------------------------------------------------------
v = neu(fe)
schemata, geheim = v._schemata()
erlaubt = set(fm._available_theme_order())
check("die Vorschau zeigt genau die verfuegbaren",
      [k for k, _n, _f, _a in schemata]
      == [k for k in fm._available_theme_order() if k in fm.THEMES])
check("Geheimes bleibt geheim (nur gezaehlt)",
      all(k in erlaubt for k, _n, _f, _a in schemata) and geheim >= 1,
      geheim)
check("genau ein Schema ist als aktiv markiert",
      sum(1 for s_ in schemata if s_[3]) == 1)

# ---------------------------------------------------------------------------
print()
print("Test 9: Menue, Uebersetzung, Startoptionen")
# ---------------------------------------------------------------------------
fq = open(H.FRONTEND_PY, encoding="utf-8").read()
check("Menuepunkt unter Info", '(t("sys_vorfuehrung"), "vorfuehrung", None)'
      in MENU_Q)
check("Behandlung im Frontend",
      'elif kind == "vorfuehrung":' in fq and "self._vorfuehrung_zeigen()"
      in fq)
import fe.translations as TR                             # noqa: E402
check("Beschriftung in beiden Sprachen",
      all(TR.TRANSLATIONS["sys_vorfuehrung"].get(s_) for s_ in ("de", "en")))
check("--show zeigt danach die Vorfuehrung mit den Messwerten",
      "_fe._vorfuehrung_zeigen(messung=SHOW.LETZTE_MESSUNG[0])" in fq)
check("--demo zeigt die Vorfuehrung",
      "_fe._vorfuehrung_zeigen()" in fq.split('if "--demo" in sys.argv:')[1])
check("die Startzeit kommt mit", "_fe._startdauer = _startdauer" in fq)
sys.modules.setdefault(type(fe).__module__, fm)
_lauf_echt = V.lauf
gerufen = []
V.lauf = lambda *a, **k: gerufen.append((a, k)) or True
try:
    ok1 = fe._vorfuehrung_zeigen(messung=["m"])
finally:
    V.lauf = _lauf_echt
check("das Frontend ruft die Vorfuehrung mit seinem Modul und den Messwerten",
      ok1 is True and gerufen and gerufen[0][0][1] is fm
      and gerufen[0][1].get("messung") == ["m"])


def _kaputt(*_a, **_k):
    raise RuntimeError("absichtlich")
V.lauf = _kaputt
try:
    try:
        ok2 = fe._vorfuehrung_zeigen()
        fehler = None
    except Exception as e_:                              # noqa: BLE001
        ok2, fehler = None, e_
finally:
    V.lauf = _lauf_echt
check("ein Fehler in der Vorfuehrung nimmt das Frontend nicht mit",
      ok2 is False and fehler is None, fehler)

print()
if fails:
    print("ROT: %d Pruefung(en) fehlgeschlagen:" % len(fails))
    for f_ in fails:
        print("   - " + f_)
    sys.exit(1)
print("ALLES GRUEN")
