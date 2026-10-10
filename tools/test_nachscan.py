#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Nur das Geaenderte nachlesen (Build 251).

DER BEFUND, und er ist aergerlich, weil die Mechanik schon da war.
Steckt man im Betrieb einen USB-Stick ein, sagt das Frontend seit
Build 213 Bescheid - einmal, und dann ist die Meldung weg. Wer sie
verpasst hatte, musste "Spieleliste neu einlesen" nehmen, und das ist
`force_rescan=True`:

    build_categories(force_rescan=True) -> scan_games(force=True)

`force=True` schaltet in scan_games() den INKREMENTELLEN Zweig ab. Der
vergleicht die Signatur je System und liest alles Unveraenderte aus
dem Cache - genau das, was man nach einem eingesteckten Stick will.
Gebaut wurde er in Build 248, und benutzt hat ihn niemand, weil jeder
Rescan-Weg im Frontend force=True setzt.

Bei 30.000 Spielen ist das der Unterschied zwischen Minuten und
Sekunden, und zwar fuer eine Aenderung an EINEM Ordner.

WAS JETZT ANDERS IST

  * Die Meldung des Waechters wird gemerkt (self._nachscan_grund).
  * Im Systemmenue erscheint DANN ein zweiter Punkt, direkt ueber dem
    vollen Neueinlesen - und nur dann.
  * Er ruft build_categories() OHNE force, nimmt also den
    inkrementellen Weg.
  * Die Meldung sagt, WAS dazugekommen ist (USB, Netzlaufwerk,
    Speicher) und nicht nur "usb0".

UND EIN WORT ZU "PHYSISCHEN DISCS": MiSTer hat keine Unterstuetzung
fuer optische Laufwerke. Ein USB-Laufwerk mit einer CD darin
erscheint unter /media wie jeder andere USB-Datentraeger, und eine
Spiele-CD liegt ohnehin als Abbild (.cue/.chd) auf der Karte. Es gibt
hier nichts eigenes zu erkennen - was es gibt, ist die ehrliche
Auskunft, was dazugekommen ist.

Ausfuehren:
    python3 tools/test_nachscan.py
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H                                        # noqa: E402

import fe.mister_system as MSYS                             # noqa: E402
import fe.menu as MENU                                      # noqa: E402
import fe.scan as SCAN                                      # noqa: E402
import fe.translations as TR                                # noqa: E402

fm = H.fm
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_QF = io.open(os.path.join(_REPO, "frontend", "frontend.py"),
              encoding="utf-8").read()
_CODE = "\n".join(z for z in _QF.split("\n")
                  if not z.strip().startswith("#"))
fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


def _menue_eintraege(**kw):
    knoten = MENU.system_items(False, "lokal", "", **kw)
    raus = []
    rest = [knoten]
    while rest:
        n = rest.pop()
        if not isinstance(n, dict):
            continue
        raus.extend(n.get("items") or ())
        rest.extend((n.get("folders") or {}).values())
    return raus


# ---------------------------------------------------------------------------
print("Test 1: die Einordnung des Mediums")
# ---------------------------------------------------------------------------
for _name, _erw in (("usb0", "usb"), ("usb7", "usb"), ("USB1", "usb"),
                    ("cifs", "netz"), ("cifs2", "netz"), ("nfs0", "netz"),
                    ("smb1", "netz"), ("fat", "karte"), ("mmcblk0", "karte"),
                    ("sr0", ""), ("irgendwas", ""), ("", ""), (None, "")):
    check("%-12r -> %r" % (_name, _erw),
          MSYS.medium_art(_name) == _erw,
          repr(MSYS.medium_art(_name)))
check("die Begruendung zu optischen Laufwerken steht dabei",
      "optische Laufwerke" in io.open(
          os.path.join(_REPO, "frontend", "fe", "mister_system.py"),
          encoding="utf-8").read(),
      "MiSTer hat keine - eine CD kommt als USB-Datentraeger an")

# ---------------------------------------------------------------------------
print()
print("Test 2: der Menuepunkt erscheint nur, wenn es etwas gibt")
# ---------------------------------------------------------------------------
_ohne = _menue_eintraege()
check("ohne Grund kein Nachscan-Punkt",
      not [e for e in _ohne if len(e) > 1 and e[1] == "nachscan"],
      "%d Eintraege durchsucht - ein Punkt, der meistens nichts zu tun "
      "hat, ist einer zu viel" % len(_ohne))
check("aber das volle Neueinlesen ist da",
      [e for e in _ohne if len(e) > 1 and e[1] == "rescan"],
      "das bleibt unveraendert")

_mit = _menue_eintraege(nachscan_grund="+usb0")
_treffer = [e for e in _mit if len(e) > 1 and e[1] == "nachscan"]
check("mit Grund erscheint er", len(_treffer) == 1, str(_treffer))
check("und nennt das Medium",
      _treffer and TR.TRANSLATIONS["medium_usb"]["de"] in _treffer[0][0],
      str(_treffer[:1]))
check("sowie den Grund selbst",
      _treffer and "usb0" in _treffer[0][0], str(_treffer[:1]))
# Ein unbekannter Name darf nicht zu einer leeren Beschriftung fuehren.
_mit2 = _menue_eintraege(nachscan_grund="+irgendwas9")
_t2 = [e for e in _mit2 if len(e) > 1 and e[1] == "nachscan"]
check("ein unbekanntes Medium bekommt ein Wort",
      _t2 and TR.TRANSLATIONS["medium_unbekannt"]["de"] in _t2[0][0],
      str(_t2[:1]))
# Und die Reihenfolge: der schnelle Weg steht ueber dem langsamen.
_kinds = [e[1] for e in _mit if len(e) > 1]
check("er steht VOR dem vollen Neueinlesen",
      "nachscan" in _kinds and "rescan" in _kinds
      and _kinds.index("nachscan") < _kinds.index("rescan"),
      "wer das eine sucht, soll sehen, dass es das schnellere gibt")

# ---------------------------------------------------------------------------
print()
print("Test 3: die Aktion nimmt den inkrementellen Weg")
# ---------------------------------------------------------------------------
# DAS IST DER KERN. force_rescan=True wuerde genau den Zweig
# abschalten, um den es hier geht.
_blk = _CODE.split('elif kind == "nachscan":')[1].split("elif kind ==")[0]
check("sie ruft build_categories OHNE force",
      "self.build_categories()" in _blk
      and "force_rescan" not in _blk,
      "force=True schaltet den Vergleich je System ab - dann wird "
      "alles neu gelesen, und der ganze Punkt ist weg")
check("und vergisst den Grund danach",
      "self._nachscan_grund = None" in _blk,
      "sonst bleibt der Punkt stehen, obwohl er schon gelaufen ist")
check("sie sagt, dass sie laeuft", "nachscan_laeuft" in _blk,
      "ein Scan ohne Anzeige sieht wie ein Haenger aus")
check("und meldet sich fertig", "nachscan_fertig" in _blk)

# Die Gegenprobe am vollen Rescan: der benutzt weiterhin force.
_rb = _CODE.split('elif kind == "rescan":')[1].split("elif kind ==")[0]
check("das volle Neueinlesen benutzt weiterhin force_rescan=True",
      "force_rescan=True" in _rb,
      "beide Wege sollen es geben - der eine schnell, der andere "
      "gruendlich")

# ---------------------------------------------------------------------------
print()
print("Test 4: der Waechter merkt sich seine Meldung")
# ---------------------------------------------------------------------------
_w = _CODE.split("_sp = self._speicher.pruefen()")[1][:900]
check("der Grund wird gemerkt", "self._nachscan_grund = _sp" in _w)
check("und das Systemmenue sofort aufgefrischt",
      "self._refresh_system_category()" in _w,
      "sonst erscheint der Punkt erst beim naechsten vollen Aufbau")
check("die Meldung bleibt wie bisher", "mount_neu" in _w,
      "der Hinweis war richtig, er war nur fluechtig")
# BEIDE Stellen, die system_items() rufen, muessen den Grund
# durchreichen - sonst verschwindet der Punkt beim naechsten
# Umschalten einer beliebigen Einstellung wieder.
check("beide system_items()-Aufrufe reichen den Grund durch",
      _CODE.count("nachscan_grund=getattr(self") == 2,
      "%d von 2" % _CODE.count("nachscan_grund=getattr(self"))

# ---------------------------------------------------------------------------
print()
print("Test 5: der inkrementelle Zweig existiert und wird nicht umgangen")
# ---------------------------------------------------------------------------
_sq = io.open(os.path.join(_REPO, "frontend", "fe", "scan.py"),
              encoding="utf-8").read()
_sc = "\n".join(z for z in _sq.split("\n")
                if not z.strip().startswith("#"))
_sg = _sc.split("def scan_games")[1].split("\ndef ")[0]
check("scan_games() vergleicht je System",
      "changed_syskeys" in _sg,
      "die Mechanik aus Build 248 - sie war nur ungenutzt")
check("und liest den Rest aus dem Cache",
      "_cache_systeme_lesen(" in _sg and "nur=" in _sg)
check("force=True umgeht sie - genau deshalb wird es nicht gesetzt",
      "if not force:" in _sg,
      "das ist der Grund, warum der neue Punkt ohne force arbeitet")
check("_cache_systeme_lesen nimmt wirklich eine Auswahl",
      "def _cache_systeme_lesen(handle, nur=None)" in _sq)

# ---------------------------------------------------------------------------
print()
print("Test 6: am echten Frontend")
# ---------------------------------------------------------------------------
H.set_screen(1920, 1080)
fe = H.make_frontend(page=0)
check("ohne Grund kennt das Systemmenue keinen Nachscan",
      not [e for e in _menue_eintraege(
          nachscan_grund=getattr(fe, "_nachscan_grund", None))
          if len(e) > 1 and e[1] == "nachscan"])
# Den Waechter eine Aenderung melden lassen und nachsehen, ob der
# Punkt danach wirklich im Menue steht.
_alt_eing = MSYS.eingehaengt
try:
    fe._speicher.merken(frozenset(["fat"]))
    MSYS.eingehaengt = lambda: frozenset(["fat", "usb0"])
    fe._speicher.naechster_blick = 0.0
    _grund = fe._speicher.pruefen(jetzt=1e6)
    check("der Waechter meldet die Aenderung", bool(_grund), repr(_grund))
    fe._nachscan_grund = _grund
    fe._refresh_system_category()
    _idx = None
    for i, (_n, _knoten, _sk) in enumerate(fe.cats):
        if _sk is None and _n == "System":
            _idx = i
    check("die System-Kategorie wurde neu gebaut", _idx is not None)
    _eintraege = []
    _rest = [fe.cats[_idx][1]] if _idx is not None else []
    while _rest:
        _n = _rest.pop()
        if not isinstance(_n, dict):
            continue
        _eintraege.extend(_n.get("items") or ())
        _rest.extend((_n.get("folders") or {}).values())
    check("und der Nachscan-Punkt steht darin",
          [e for e in _eintraege if len(e) > 1 and e[1] == "nachscan"],
          "%d Eintraege" % len(_eintraege))
finally:
    MSYS.eingehaengt = _alt_eing
    fe._nachscan_grund = None

for _schl in ("sys_nachscan", "nachscan_laeuft", "nachscan_fertig",
              "medium_usb", "medium_netz", "medium_karte",
              "medium_unbekannt"):
    _e = TR.TRANSLATIONS.get(_schl)
    check("%-20s zweisprachig" % _schl,
          bool(_e) and bool(_e.get("de")) and bool(_e.get("en")))

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
