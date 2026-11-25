#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Heft-Tests von kultboy.com (Build 350).

GEPRUEFT WIRD - ohne Netz, die Seiten sind nachgebaute Ausschnitte mit
genau dem Aufbau, den der Nutzer im Browser gespeichert hat:
  1. Schalter (Vorgabe AUS), Menue, Kontextmenue nur bei AN.
  2. Lesen: Suchtreffer (nur die Ergebnistabelle), Uebersicht (normale
     Zeile, colspan=3, mehrere Systeme, Vorschau), Testseite (Heft, Scan
     als Hintergrund, Layout-Bilder nicht), Namen und Vergleich.
  3. Finden: eindeutig, Auswahl, Systemnummer in der Suche, zweiter
     Versuch ohne System und mit dem Namen vor dem Doppelpunkt, nichts.
  4. Merker: nur die Nummer, ueber .tmp, vergessen.
  5. Der ganze Ablauf im Frontend mit einem nachgebauten Netz: Suche ->
     Auswahl -> Liste -> Seite -> Betrachter; beim zweiten Mal ohne
     Suche; Fehler (kein Netz, Zeit, nichts, kaputte gemerkte Seite);
     Abbruch mit B.
  6. Der Betrachter: Zoomstufen, Verschieben, Seiten, nichts auf die
     Karte geschrieben.

Ausfuehren:
    python3 tools/test_kultboy.py
"""
import json
import os
import sys
import time

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
sys.path.insert(0, _HIER)
import _harness as H                                     # noqa: E402
import fe.kultboy as KB                                  # noqa: E402
import fe.menu as MENU                                   # noqa: E402

fm = H.fm
fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


SUCHE = (
    '<a href="https://www.kultboy.com/testbericht-uebersicht/4971/">'
    'Test/Vorschau</a><table>'
    '<tr class="row"><td>Nr.</td></tr>'
    '<tr class="row2"><td>1. </td><td class="kl" align="left"><a href="'
    '/testbericht-uebersicht/338/">Turrican II: The Final Fight<br>'
    'Turrican 2</a></td><td> Diskette</td><td>89%</td></tr>'
    '<tr class="row3"><td>2. </td><td class="kl" align="left"><a href="'
    'https://www.kultboy.com/testbericht-uebersicht/337/">Turrican</a>'
    '</td></tr>'
    '<tr class="row2"><td>3. </td><td><a href="/testbericht-uebersicht/'
    '339/">Turrican 3<br>Turrican III: Payment Day</a></td></tr>'
    '</table>')
UEBERSICHT = (
    '<tr bgcolor="#eee8aa"><td class="km">64er&nbsp;6/91<br><a href="x">'
    '<img src="/gfx/kultmags/thumb/1592.jpg"></a></td><td class="km">'
    'Testbericht<br><a href="/index.php?site=t&amp;id=4254"><img src="'
    '4254.jpg"></a></td><td align="center">9/10<br></td><td align="center">'
    '7/10<br></td><td align="center"><font><b>10/10<br></b></font></td>'
    '<td align="center">C64/128<br></td><td>1 Diskette<br></td><td>3088</td>'
    '<td>Autor</td></tr>'
    '<tr bgcolor="#eee8aa"><td class="km">Amiga Joker&nbsp;3/92<br></td>'
    '<td class="km">Testbericht<br><a href="https://www.kultboy.com/index.'
    'php?site=t&amp;id=4814">x</a></td><td align="center" colspan="3">'
    '<font><b>Super</b></font></td><td align="center">Amiga CDTV<br></td>'
    '<td>1 CD</td><td>1604</td><td>-</td></tr>'
    '<tr bgcolor="#eee8aa"><td class="km">ASM&nbsp;3/91<br></td><td class='
    '"km">Testbericht<br><a href="/index.php?site=t&amp;id=3171">x</a></td>'
    '<td>10/12<br>11/12<br></td><td>9/12<br>10/12<br></td><td><font><b>'
    '10/12<br>9/12<br></b></font></td><td>Atari ST<br>Amiga<br></td><td>'
    '1 Diskette</td><td>2989</td><td>Sandra</td></tr>'
    '<tr bgcolor="#eee8aa"><td class="km">ASM&nbsp;1/91<br></td><td class='
    '"km">Vorschau<br><a href="/index.php?site=t&amp;id=11289">x</a></td>'
    '<td align="center" colspan="3">-</td><td>C64/128<br>Amiga<br></td>'
    '<td>Diskette</td><td>1063</td><td>-</td></tr>')
TEST = (
    '<td background="/gfx/streifen.gif"></td>'
    '<a href="/magazin/1592/">64er&#160;6/91<br /><img src="/gfx/kultmags/'
    'thumb/2000/1592.jpg"></a><div style="padding:5px"><table><tr><td '
    'width="800" height="722" background="/gfx/64/t/turrican2.jpg"><img '
    'src="/gfx/testbericht.gif" width="800" height="722"></td></tr></table>'
    '<table><tr><td background="/gfx/64/t/turrican2b.jpg"><img src="/gfx/'
    'testbericht.gif"></td></tr></table></div>')

# ---------------------------------------------------------------------------
print("Test 1: Schalter, Menue, Kontextmenue")
# ---------------------------------------------------------------------------
check("Vorgabe AUS", KB.an() is False)


def stats_kinds():
    sysm = MENU.system_items(False, "local", "")
    for _n, node in sysm["folders"].items():
        kinds = [k for _l, k, _a in node["items"]]
        if "diary" in kinds:
            return kinds, node["items"]
    return [], []


kinds, items = stats_kinds()
check("Schalter im Systemmenue (Statistiken & Erfolge)",
      "kultboy_an" in kinds and fm.t("sys_kultboy_aus")
      in [l for l, _k, _a in items])
fe = H.make_frontend(page=1)
gezeigt = []
fe._wizard_choice = lambda titel, opts, **k: gezeigt.append(opts) or None
fe.kontextmenue()
check("AUS: kein Eintrag im Kontextmenue",
      fm.t("ctx_kultboy") not in gezeigt[-1])
check("einschalten", KB.toggle_an() is True and os.path.exists(KB.AN_FLAG))
fe.kontextmenue()
check("AN: 'Heft-Tests (Kultboy)' im Kontextmenue",
      fm.t("ctx_kultboy") in gezeigt[-1])
fq = open(H.FRONTEND_PY, encoding="utf-8").read()
check("Menueschalter und Kontextmenue sind verdrahtet",
      'elif kind == "kultboy_an":' in fq and 'gewaehlt == "kultboy"' in fq)

# ---------------------------------------------------------------------------
print()
print("Test 2: die Seiten lesen")
# ---------------------------------------------------------------------------
tr = KB.suchtreffer(SUCHE)
check("Suchtreffer nur aus der Ergebnistabelle, mit allen Namen",
      tr == [(338, ["Turrican II: The Final Fight", "Turrican 2"]),
             (337, ["Turrican"]),
             (339, ["Turrican 3", "Turrican III: Payment Day"])], tr)
ts = KB.tests(UEBERSICHT)
check("vier Tests gelesen", [x["id"] for x in ts] == [4254, 4814, 3171,
                                                      11289], ts)
check("normale Zeile: Heft, Art, Grafik, Sound, Wertung, System",
      ts[0]["heft"] == "64er 6/91" and ts[0]["art"] == "Testbericht"
      and ts[0]["grafik"] == ["9/10"] and ts[0]["sound"] == ["7/10"]
      and ts[0]["wertung"] == ["10/10"] and ts[0]["systeme"] == ["C64/128"])
check("eine Zelle ueber drei Spalten ('Super')",
      ts[1]["wertung"] == ["Super"] and ts[1]["systeme"] == ["Amiga CDTV"])
check("mehrere Systeme: je System eine Wertung",
      ts[2]["systeme"] == ["Atari ST", "Amiga"]
      and ts[2]["wertung"] == ["10/12", "9/12"])
check("Vorschau ohne Wertung", ts[3]["wertung"] == []
      and ts[3]["art"] == "Vorschau")
check("Zeile: die Wertung des EIGENEN Systems",
      KB.zeile(ts[2], "AMIGA") == "ASM 3/91  9/12  Amiga"
      and KB.zeile(ts[3], "AMIGA") == "ASM 1/91  Vorschau  Amiga",
      (KB.zeile(ts[2], "AMIGA"), KB.zeile(ts[3], "AMIGA")))
check("Tests zum eigenen System zuerst",
      [x["id"] for x in KB.tests_sortiert(ts, "AMIGA")][:3]
      == [4814, 3171, 11289])
heft, bilder = KB.scans(TEST)
check("Testseite: Heft und Scans (Hintergrund), Layout-Bilder nicht",
      heft == "64er 6/91"
      and bilder == ["https://www.kultboy.com/gfx/64/t/turrican2.jpg",
                     "https://www.kultboy.com/gfx/64/t/turrican2b.jpg"],
      (heft, bilder))
check("Suchname ohne Klammern",
      KB.suchname("Super Metroid (Japan, USA) (En,Ja) [!]")
      == "Super Metroid")
check("Vergleich: roemische Zahlen, Artikel, Satzzeichen",
      KB.vergleich("The Turrican II!") == KB.vergleich("turrican 2"))
url = KB.such_url("Turrican II (Europe)", 21)
check("Suchadresse mit Titel und System",
      "site=testb/testb" in url and "q=Turrican+II&" in url
      and "&system=21&" in url, url)
check("Umlaute auch in der alten Kodierung",
      "q=K%F6nig" in KB.such_url("König", 99, "cp1252"))
check("Systemnummern fuer die Dragend-Systeme",
      KB.systemnummern("SNES") == (18,) and KB.systemnummern("AMIGA")[0]
      == 21 and KB.systemnummern("ARCADE") == (25,)
      and KB.systemnummern("C64") == (1,))

# ---------------------------------------------------------------------------
print()
print("Test 3: finden")
# ---------------------------------------------------------------------------
abgerufen = []


def netz(seiten):
    def _holer(u, zeitlimit=None):
        abgerufen.append(u)
        for teil, inhalt in seiten:
            if teil in u:
                if isinstance(inhalt, Exception):
                    raise inhalt
                return inhalt.encode("utf-8") if isinstance(inhalt, str) \
                    else inhalt
        return b"<html></html>"
    return _holer


h = netz([("q=Turrican+II&", SUCHE)])
check("eindeutig: 'Turrican II' -> 338 (Name bis zum Doppelpunkt)",
      KB.finden("AMIGA", "Turrican II (Europe)", h) == ("treffer", 338))
check("die erste Suche mit der Systemnummer",
      "&system=21&" in abgerufen[0], abgerufen[0])
del abgerufen[:]
art, liste = KB.finden("AMIGA", "Turrican", netz([("q=Turrican&", SUCHE)]))
check("'Turrican' ist eindeutig, auch wenn 'Turrican II' anfaengt "
      "wie er", (art, liste) == ("treffer", 337), (art, liste))
SUCHE2 = ('<tr class="row2"><td><a href="/testbericht-uebersicht/338/">'
          'Turrican II: The Final Fight</a></td></tr><tr class="row3"><td>'
          '<a href="/testbericht-uebersicht/999/">Turrican II</a></td></tr>')
check("genau gleicher Name schlaegt 'gleich bis zum Doppelpunkt'",
      KB.finden("AMIGA", "Turrican II", netz([("q=Turrican+II&", SUCHE2)]))
      == ("treffer", 999))
art, liste = KB.finden("AMIGA", "Turrican X",
                       netz([("q=Turrican+X&", SUCHE)]))
check("kein eindeutiger: Auswahl mit allen Treffern",
      art == "auswahl" and [k for k, _n in liste] == [338, 337, 339])
del abgerufen[:]
h = netz([("q=Turrican+II&firma", "<html></html>"),
          ("q=Turrican+II%3A+The", "<html></html>"),
          ("q=Turrican+II&", SUCHE)])
try:
    KB.finden("AMIGA", "Turrican II - The Final Fight",
              netz([("q=Turrican+II&", SUCHE)]))
    weiter = True
except KB.KultboyFehler:
    weiter = False
check("zweiter Versuch mit dem Namen vor dem Gedankenstrich", weiter)
try:
    KB.finden("SNES", "Gibt es nicht", netz([]))
    nichts = False
except KB.KultboyFehler as e:
    nichts = e.art == "nichts"
check("nichts gefunden -> Fehler 'nichts'", nichts)

# ---------------------------------------------------------------------------
print()
print("Test 4: der Merker")
# ---------------------------------------------------------------------------
KB.zuordnung_merken("AMIGA", "Turrican II", 338)
d = json.load(open(KB.ZUORDNUNG_FILE, encoding="utf-8"))
check("gemerkt wird nur die Nummer",
      d == {"AMIGA|Turrican II": 338} and KB.zuordnung("AMIGA",
                                                        "Turrican II") == 338)
check("ueber .tmp, nichts liegen geblieben",
      not os.path.exists(KB.ZUORDNUNG_FILE + ".tmp"))
KB.zuordnung_vergessen("AMIGA", "Turrican II")
check("vergessen", KB.zuordnung("AMIGA", "Turrican II") is None)

# ---------------------------------------------------------------------------
print()
print("Test 5: der ganze Ablauf im Frontend")
# ---------------------------------------------------------------------------


class Skript(object):
    def __init__(self, echt, tasten):
        self.echt = echt
        self.tasten = list(tasten)

    def __getattr__(self, n):
        return getattr(self.echt, n)

    def read_action(self, timeout=None):
        if self.tasten:
            return self.tasten.pop(0)
        return None


fe = H.make_frontend(page=1)
fe._kultboy_netz = lambda: True
BILD = (40, 30, bytes(40 * 30 * 4))
geladen = []
fe._kultboy_bild = lambda u: geladen.append(u) or BILD
wahl = []


def _waehlen(antworten):
    def _w(titel, opts, **k):
        wahl.append((titel, list(opts)))
        return antworten.pop(0) if antworten else None
    return _w


_holen_echt = KB.holen
del abgerufen[:]
KB.holen = netz([("q=Turrican+X", SUCHE), ("uebersicht/339/", UEBERSICHT),
                 ("site=t&id=", TEST)])
fe._wizard_choice = _waehlen([2, 1])
echt_inp = fe.inp
fe.inp = Skript(echt_inp, [None] * 50)
_bet = []
_betrachter_echt = fe._kultboy_betrachter
fe._kultboy_betrachter = lambda heft, urls: _bet.append((heft, urls))
try:
    fe._kultboy_ablauf("AMIGA", "Turrican X")
finally:
    fe.inp = echt_inp
check("Auswahl gezeigt, gewaehlt und gemerkt",
      wahl[0][1][2] == "Turrican 3" and KB.zuordnung("AMIGA",
                                                     "Turrican X") == 339)
check("die Testliste mit dem eigenen System zuerst",
      wahl[1][1][0].startswith("Amiga Joker 3/92"), wahl[1][1][:2])
check("der gewaehlte Test oeffnet den Betrachter mit seinen Scans",
      _bet == [("64er 6/91", ["https://www.kultboy.com/gfx/64/t/"
                              "turrican2.jpg",
                              "https://www.kultboy.com/gfx/64/t/"
                              "turrican2b.jpg"])], _bet)
del abgerufen[:]
fe._wizard_choice = _waehlen([])
fe.inp = Skript(echt_inp, [None] * 20)
try:
    fe._kultboy_ablauf("AMIGA", "Turrican X")
finally:
    fe.inp = echt_inp
check("beim zweiten Mal ohne Suche (gemerkte Nummer)",
      abgerufen and all("site=testb" not in u for u in abgerufen)
      and "uebersicht/339/" in abgerufen[0], abgerufen)
hinweise = []
fe._kultboy_hinweis = lambda text: hinweise.append(text)
KB.holen = netz([("uebersicht/339/", KB.KultboyFehler("seite"))])
fe.inp = Skript(echt_inp, [None] * 20)
try:
    fe._kultboy_ablauf("AMIGA", "Turrican X")
finally:
    fe.inp = echt_inp
check("gemerkte Seite kaputt: Meldung und Merker vergessen",
      hinweise[-1] == fm.t("kb_fehler_seite")
      and KB.zuordnung("AMIGA", "Turrican X") is None)
fe._kultboy_netz = lambda: False
fe._kultboy_ablauf("SNES", "Egal")
check("kein Netz: sofort die Meldung, kein Abruf",
      hinweise[-1] == fm.t("kb_fehler_netz"))
fe._kultboy_netz = lambda: True
KB.holen = netz([("site=testb", KB.KultboyFehler("zeit"))])
fe.inp = Skript(echt_inp, [None] * 20)
try:
    fe._kultboy_ablauf("SNES", "Langsam")
finally:
    fe.inp = echt_inp
check("Zeitueberschreitung: 'antwortet gerade nicht'",
      hinweise[-1] == fm.t("kb_fehler_zeit"))
KB.holen = netz([])
fe.inp = Skript(echt_inp, [None] * 20)
try:
    fe._kultboy_ablauf("SNES", "Gibt es nicht")
finally:
    fe.inp = echt_inp
check("nichts gefunden: Meldung",
      hinweise[-1] == fm.t("kb_fehler_nichts"))


def _langsam(u, zeitlimit=None):
    time.sleep(0.5)
    return SUCHE.encode()


KB.holen = _langsam
n_h = len(hinweise)
n_w = len(wahl)
fe._wizard_choice = _waehlen([])
fe.inp = Skript(echt_inp, ["back"])
try:
    fe._kultboy_ablauf("SNES", "Abbruch")
finally:
    fe.inp = echt_inp
check("B bricht das Warten ab: keine Auswahl, keine Meldung, kein Merker",
      len(hinweise) == n_h and len(wahl) == n_w
      and KB.zuordnung("SNES", "Abbruch") is None, (len(wahl), n_w))
KB.holen = _holen_echt
fe._kultboy_betrachter = _betrachter_echt

# ---------------------------------------------------------------------------
print()
print("Test 6: der Betrachter")
# ---------------------------------------------------------------------------
check("Zoomstufen: kleines Bild auf grossem Schirm",
      fm.Frontend._kultboy_faktoren(800, 722, 1800, 1000) == [1, 2])
check("Zoomstufen: grosses Bild auf kleinem Schirm",
      fm.Frontend._kultboy_faktoren(800, 722, 300, 200)[0] < 1
      and fm.Frontend._kultboy_faktoren(800, 722, 300, 200)[1:] == [1, 2])
check("Zoomstufen: doppelt passt schon",
      fm.Frontend._kultboy_faktoren(400, 300, 1800, 1000) == [3, 1])
pix = bytes(range(256)) * (4 * 10 * 8 // 256 + 1)
pix = pix[:4 * 10 * 8]
aus = fm.Frontend._kultboy_ausschnitt(pix, 10, 2, 3, 4, 2)
check("Ausschnitt: richtige Bytes, richtige Groesse",
      len(aus) == 4 * 4 * 2 and aus[:16] == pix[(3 * 10 + 2) * 4:
                                                 (3 * 10 + 6) * 4])
for b_, h_ in ((1920, 1080), (320, 240)):
    H.set_screen(b_, h_)
    fe = H.make_frontend(page=1)
    seiten = []
    w_, h2 = 300, 260
    fe._kultboy_bild = lambda u: seiten.append(u) or (
        w_, h2, bytes(w_ * h2 * 4))
    # Danach "exit" statt nichts: der Betrachter wartet auf dem Geraet
    # blockierend - hier soll er nie endlos auf leere Antworten warten.
    fe.inp = Skript(fe.inp, ["ok", "down", "right", "ok", "back", "select",
                             "left", "back"] + ["exit"] * 3)
    vorher = set(os.listdir("/media/fat/frontend")) \
        if os.path.isdir("/media/fat/frontend") else set()
    try:
        fe._kultboy_betrachter("Heft 1/91", ["u1", "u2"])
        ok_ = True
    except Exception as e_:                              # noqa: BLE001
        ok_ = e_
    nachher = set(os.listdir("/media/fat/frontend")) \
        if os.path.isdir("/media/fat/frontend") else set()
    check("Betrachter %dx%d: Zoom, Verschieben, Seiten, zurueck"
          % (b_, h_), ok_ is True and seiten[:2] == ["u1", "u2"], ok_)
    check("Betrachter %dx%d: nichts auf die Karte geschrieben" % (b_, h_),
          vorher == nachher, nachher - vorher)
H.set_screen(1280, 720)
fe = H.make_frontend(page=1)
fe._kultboy_bild = lambda u: (20, 20, bytes(20 * 20 * 4))
fe.inp = Skript(fe.inp, [])
try:
    fe._kultboy_betrachter("Heft", ["u1"])
    leer_ok = True
except Exception as e_:                                  # noqa: BLE001
    leer_ok = e_
check("klemmende Eingabe (nur leere Antworten): der Betrachter gibt auf",
      leer_ok is True, leer_ok)
kq = open(KB.__file__, encoding="utf-8").read()
check("die Seiten werden nur gelesen, nicht gespeichert",
      "ZUORDNUNG_FILE" in kq and kq.count('"w"') == 2
      and 'open(AN_FLAG, "w")' in kq and 'open(tmp, "w"' in kq
      and "Dragend" not in kq.split('UA = ')[1].split("\n")[0])

print()
if fails:
    print("ROT: %d Pruefung(en) fehlgeschlagen:" % len(fails))
    for f_ in fails:
        print("   - " + f_)
    sys.exit(1)
print("ALLES GRUEN")
