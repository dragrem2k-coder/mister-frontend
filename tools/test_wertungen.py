#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Eigene Wertungen im Heft-Stil (Build 346).

NUTZERWUNSCH: Spielspass in Prozent wie frueher im Heft, dazu Grafik,
Sound und Co. je nach Geraet, Stempel, Schnelleingabe mit Vorschlag,
ein Testarchiv je System - und: "Das ganze muss aber an und abschaltbar
sein".

GEPRUEFT WIRD:
  1. AUS ist die Vorgabe - und bei AUS ist nichts davon da: keine Datei
     wird gelesen, kein Vorzeichen, kein Testarchiv, kein Menuepunkt
     "Bewerten", keine Frage nach dem Spiel, im Systemmenue nur der
     Hauptschalter.
  2. Die Schalter und das Systemmenue bei EIN.
  3. Kategorien je Geraet, Stempel, Vorschlag.
  4. Die Datei: Schreiben ueber .tmp, Verlauf, Loeschen, eine kaputte
     Datei wird beiseitegelegt statt ueberschrieben.
  5. Das Testarchiv: Ordner je System ohne Zahl, Hits, Reihenfolge,
     nur Startbares.
  6. Im Frontend: Vorzeichen in der Liste, das Testarchiv in self.cats
     (Position, Auswahl bleibt, verschwindet bei AUS, Ordner weg ->
     zurueck).
  7. Die Rueckkehr-Leiste: Schwelle, schon bewertet, Links/Rechts + A,
     B, andere Taste wirkt weiter, Select oeffnet den Kasten.
  8. Der Wertungskasten: Zeilen je Geraet, Aendern, Leeren, Speichern,
     Loeschen, Abbrechen.
  9. Kontextmenue, Steckbrief, Einrichtung, Einbau in run_core().

Ausfuehren:
    python3 tools/test_wertungen.py
"""
import json
import os
import sys

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
sys.path.insert(0, _HIER)
import _harness as H                                     # noqa: E402
import fe.wertungen as WT                                # noqa: E402
import fe.menu as MENU                                   # noqa: E402

fm = H.fm
fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


def stats_items():
    sysm = MENU.system_items(False, "local", "")
    for name, node in sysm["folders"].items():
        kinds = [k for _l, k, _a in node["items"]]
        if "diary" in kinds:
            return node["items"]
    return []


class Skript(object):
    """Liefert die Aktionen der Reihe nach, dann None."""

    def __init__(self, echt, tasten):
        self.echt = echt
        self.tasten = list(tasten)
        self.gefragt = 0

    def __getattr__(self, n):
        return getattr(self.echt, n)

    def read_action(self, timeout=None):
        self.gefragt += 1
        if self.tasten:
            return self.tasten.pop(0)
        return None


def mit_tasten(fe, tasten, fn, *a, **k):
    echt = fe.inp
    fe.inp = Skript(echt, tasten)
    try:
        return fn(*a, **k), fe.inp
    finally:
        fe.inp = echt


H.set_screen(1280, 720)

# ---------------------------------------------------------------------------
print("Test 1: AUS ist die Vorgabe - und dann ist nichts davon da")
# ---------------------------------------------------------------------------
check("Hauptschalter AUS ohne Flag-Datei", WT.an() is False)
check("die Pruefstaende schreiben in einen eigenen Ordner",
      WT.DATEI.startswith("/tmp") or "harness_wertungen_" in WT.DATEI,
      WT.DATEI)
gelesen = []
_laden_echt = WT._laden
WT._laden = lambda: gelesen.append(1) or {}
fe = H.make_frontend(page=1)
lab, kind, arg = fe._display_items()[1]
check("keine Wertung, keine Liste, kein Spielspass",
      WT.wertung("SNES", lab) is None and WT.alle() == {}
      and WT.spielspass("SNES", lab) is None)
check("kein Vorzeichen in der Liste",
      fe._zeilen_praefix(lab, "game", "SNES") == "")
check("kein Testarchiv", fe._testarchiv_knoten() is None
      and all(c[0] != fm.t("testarchiv_cat") for c in fe.cats))
fe.inp_echt = fe.inp
ok, sk = mit_tasten(fe, ["ok"], fe._wertung_nach_spiel, lab, "SNES",
                    "/x.mgl", 3600)
check("keine Frage nach dem Spiel", ok is False and sk.gefragt == 0)
gewaehlt = []
_wc = fe._wizard_choice
fe._wizard_choice = lambda titel, opts, **k: gewaehlt.append(opts) or None
fe.kontextmenue()
fe._wizard_choice = _wc
check("kein 'Bewerten' im Kontextmenue",
      gewaehlt and fm.t("ctx_bewerten") not in gewaehlt[0])
check("die Wertungsdatei wurde dabei nie gelesen", not gelesen, len(gelesen))
WT._laden = _laden_echt
items = stats_items()
kinds = [k for _l, k, _a in items]
check("im Systemmenue nur der Hauptschalter",
      [k for k in kinds if k.startswith("wertung")] == ["wertungen"]
      and fm.t("sys_wertungen_aus") in [l_ for l_, _k, _a in items])

# ---------------------------------------------------------------------------
print()
print("Test 2: die Schalter bei EIN")
# ---------------------------------------------------------------------------
check("einschalten legt die Flag-Datei an",
      WT.toggle_an() is True and os.path.exists(WT.AN_FLAG))
kinds = [k for _l, k, _a in stats_items()]
check("das Systemmenue zeigt alle Schalter (Build 347: acht) und zwei "
      "Aktionen",
      [k for k in kinds if k.startswith("wertung")]
      == ["wertungen", "wertung_fragen", "wertung_fragen_ab",
          "wertung_liste", "wertung_kategorien", "wertung_stempel",
          "wertung_zweit", "wertung_heft", "wertung_monatsheft",
          "wertung_csv"], kinds)
check("Vorgaben bei EIN: fragen, ab 5 Minuten, in Listen, alle "
      "Kategorien, Stempel",
      WT.fragen() and WT.fragen_ab_minuten() == 5 and WT.in_listen()
      and not WT.nur_spielspass() and WT.stempel_an())
check("Fragen ab: 5 -> 10 -> 20 -> 5",
      [WT.cycle_fragen_ab() for _ in range(3)] == [10, 20, 5])
for name, toggle, lesen in (("fragen", WT.toggle_fragen, WT.fragen),
                            ("in Listen", WT.toggle_in_listen,
                             WT.in_listen),
                            ("Stempel", WT.toggle_stempel, WT.stempel_an)):
    toggle()
    aus = lesen()
    toggle()
    check("%s: umschalten und zurueck" % name, aus is False and lesen())
WT.toggle_nur_spielspass()
check("nur Spielspass: keine weiteren Kategorien",
      WT.nur_spielspass() and WT.kategorien("SNES") == ())
WT.toggle_nur_spielspass()
check("jede Menueaktion hat einen Schalter im Frontend",
      set(fm.Frontend.WERTUNG_SCHALTER) == {
          "wertungen", "wertung_fragen", "wertung_fragen_ab",
          "wertung_liste", "wertung_kategorien", "wertung_stempel",
          "wertung_zweit", "wertung_heft"})
fq = open(H.FRONTEND_PY, encoding="utf-8").read()
check("das Frontend behandelt sie (und frischt Liste und Archiv auf)",
      "elif kind in self.WERTUNG_SCHALTER:" in fq
      and "self._sync_testarchiv_category()" in fq.split(
          "elif kind in self.WERTUNG_SCHALTER:")[1][:600])

# ---------------------------------------------------------------------------
print()
print("Test 3: Kategorien je Geraet, Stempel, Vorschlag")
# ---------------------------------------------------------------------------
check("Konsole", WT.geraet("SNES") == "konsole"
      and WT.kategorien("SNES") == ("grafik", "sound", "steuerung"))
check("Computer (C64, Amiga, CPC, PC)",
      all(WT.geraet(k) == "computer"
          for k in ("C64", "AMIGA", "AMSTRAD", "AO486"))
      and WT.kategorien("AMIGA") == ("grafik", "musik", "effekte"))
check("Arcade", WT.geraet(WT.ARCADE) == "automat"
      and WT.kategorien(WT.ARCADE) == ("grafik", "sound", "credit"))
check("Arcade erkannt am .mra",
      WT.ist_automat("core", "/media/fat/_Arcade/x.mra")
      and not WT.ist_automat("core", "/media/fat/_Console/NES.rbf")
      and WT.bewertbar("game", ("a",)) and not WT.bewertbar("folder", "x"))
h = 3600
for spass, sek, soll in ((84, 0, None), (85, 0, "hit"), (90, 9 * h, "hit"),
                         (90, 10 * h, "klassiker"), (30, 0, None),
                         (29, 0, "gurke"), (None, 0, None)):
    check("Stempel %s%% / %d h -> %s" % (spass, sek // h, soll),
          WT.stempel({"spass": spass}, sek) == soll)
for sek, starts, soll in ((0, 0, 70), (h, 0, 75), (0, 5, 75), (3 * h, 0, 80),
                          (0, 10, 80), (10 * h, 0, 85)):
    check("Vorschlag %d h / %d Starts -> %d" % (sek // h, starts, soll),
          WT.vorschlag(sek, starts) == soll)
check("Farben: rot / gelb / gruen",
      [WT.farbstufe(w) for w in (49, 50, 79, 80)]
      == ["rot", "gelb", "gelb", "gruen"])

# ---------------------------------------------------------------------------
print()
print("Test 4: die Datei")
# ---------------------------------------------------------------------------
e = WT.speichern("SNES", "Zelda", {"spass": 91, "grafik": 85, "sound": None,
                                   "schwierigkeit": "knackig",
                                   "spieler": "9", "musik": 140},
                 kind="game", arg=("/z.sfc", ".sfc", "SNES", None, None),
                 heute="2026-11-22")
roh = json.load(open(WT.DATEI, encoding="utf-8"))
check("geschrieben, mit Version", roh.get("version") == 1
      and "SNES|Zelda" in roh["spiele"])
check("leere und ungueltige Werte fallen weg, zu grosse werden begrenzt",
      e["spass"] == 91 and e["grafik"] == 85 and "sound" not in e
      and e["schwierigkeit"] == "knackig" and "spieler" not in e
      and e["musik"] == 100, e)
check("startbar gemerkt", e["kind"] == "game" and e["arg"][0] == "/z.sfc")
check("keine .tmp-Datei bleibt liegen", not os.path.exists(WT.DATEI + ".tmp"))
WT.speichern("SNES", "Zelda", {"spass": 91}, heute="2026-11-23")
e = WT.speichern("SNES", "Zelda", {"spass": 95}, heute="2026-12-01")
check("Verlauf nur bei geaendertem Spielspass, kind/arg bleiben",
      e["verlauf"] == [["2026-11-22", 91], ["2026-12-01", 95]]
      and e["kind"] == "game", e["verlauf"])
check("ohne Spielspass keine Wertung",
      WT.speichern("SNES", "X", {"grafik": 50}) is None
      and WT.wertung("SNES", "X") is None)
check("gleicher Name, anderes System: zwei Spiele",
      WT.speichern("SMS", "Zelda", {"spass": 40}) and
      WT.spielspass("SNES", "Zelda") == 95
      and WT.spielspass("SMS", "Zelda") == 40)
WT.vergessen()
check("nach dem Neuladen noch da", WT.spielspass("SNES", "Zelda") == 95)
check("loeschen", WT.loeschen("SMS", "Zelda")
      and WT.wertung("SMS", "Zelda") is None
      and not WT.loeschen("SMS", "Zelda"))
inhalt = open(WT.DATEI, encoding="utf-8").read()
with open(WT.DATEI, "w", encoding="utf-8") as f:
    f.write("{kaputt")
WT.vergessen()
check("kaputte Datei: gelesen wird nichts", WT.alle() == {})
WT.speichern("SNES", "Neu", {"spass": 60})
check("kaputte Datei wird vor dem Schreiben beiseitegelegt",
      open(WT.DATEI + ".kaputt", encoding="utf-8").read() == "{kaputt"
      and WT.spielspass("SNES", "Neu") == 60)
os.remove(WT.DATEI + ".kaputt")
with open(WT.DATEI, "w", encoding="utf-8") as f:
    f.write(inhalt)
WT.vergessen()

# ---------------------------------------------------------------------------
print()
print("Test 5: das Testarchiv")
# ---------------------------------------------------------------------------
WT.speichern("SNES", "Alpha", {"spass": 70}, "game", ["/a", ".sfc", "SNES"])
WT.speichern("SNES", "Beta", {"spass": 88}, "game", ["/b", ".sfc", "SNES"])
WT.speichern(WT.ARCADE, "Galaga", {"spass": 86}, "core", "/g.mra")
WT.speichern("NES", "Ohne", {"spass": 99})          # nicht startbar
namen = {"SNES": "SNES", WT.ARCADE: "Arcade", "NES": "NES"}
k = WT.testarchiv(lambda s_: namen.get(s_, s_), "Alle Hits")
check("Ordner je System ohne Zahl, dazu die Hits",
      sorted(k["folders"]) == ["Alle Hits", "Arcade", "SNES"],
      sorted(k["folders"]))
check("je System nach Spielspass sortiert",
      [x[0] for x in k["folders"]["SNES"]["items"]]
      == ["Zelda", "Beta", "Alpha"])
check("Hits ab 85 ueber alle Systeme",
      [x[0] for x in k["folders"]["Alle Hits"]["items"]]
      == ["Zelda", "Beta", "Galaga"])
check("Eintraege sind startbar wie in jeder Liste",
      k["folders"]["Arcade"]["items"][0] == ("Galaga", "core", "/g.mra"))
k2 = WT.testarchiv(lambda s_: "Gleich", "Alle Hits")
check("zwei Systeme mit einem Anzeigenamen bleiben getrennt",
      len(k2["folders"]) == 3, sorted(k2["folders"]))

# ---------------------------------------------------------------------------
print()
print("Test 6: im Frontend - Vorzeichen und Testarchiv")
# ---------------------------------------------------------------------------
fe = H.make_frontend(page=1)
lab, kind, arg = fe._display_items()[1]
WT.speichern("SNES", lab, {"spass": 75}, kind, arg)
check("Vorzeichen vor dem Namen", fe._zeilen_praefix(lab, "game", "SNES")
      .startswith("75% "))
check("ohne Wertung kein Vorzeichen",
      fe._zeilen_praefix(fe._display_items()[2][0], "game", "SNES") == "")
check("Arcade: nur die Wertung",
      fe._zeilen_praefix("Galaga", "core", None) == "86% ")
WT.toggle_in_listen()
check("'Wertung in Listen: AUS' nimmt es weg",
      not fe._zeilen_praefix(lab, "game", "SNES").startswith("75%"))
WT.toggle_in_listen()
vorher = (fe.cats[fe.cat_i][0], fe.item_i)
fe._sync_testarchiv_category()
namen_c = [c[0] for c in fe.cats]
ta = fm.t("testarchiv_cat")
check("Testarchiv vor dem Zufalls-Zock",
      ta in namen_c and namen_c.index(ta) + 1
      == namen_c.index(fm.t("zufallszock_title")), namen_c)
check("die Auswahl bleibt, wo sie war",
      (fe.cats[fe.cat_i][0], fe.item_i) == vorher)
fe.cat_i = namen_c.index(ta)
fe.nav_path = ["Arcade"]
fe._nav_position_stack = [0]
fe.item_i = 0
WT.loeschen(WT.ARCADE, "Galaga")
fe._sync_testarchiv_category()
check("Ordner weg: zurueck in den Ordner darueber",
      fe.cats[fe.cat_i][0] == ta and fe.nav_path == []
      and fe._nav_position_stack == [], (fe.nav_path, fe.cats[fe.cat_i][0]))
fe.nav_path = []
fe.page = 0
WT.toggle_an()
fe._sync_testarchiv_category()
check("bei AUS verschwindet das Testarchiv",
      ta not in [c[0] for c in fe.cats])
WT.toggle_an()

# ---------------------------------------------------------------------------
print()
print("Test 7: die Rueckkehr-Leiste")
# ---------------------------------------------------------------------------
fe = H.make_frontend(page=1)
spiele = fe._display_items()
lab, kind, arg = spiele[3]
fm.load_recent = lambda: [(lab, "game", list(arg))]
ok, sk = mit_tasten(fe, ["right"], fe._wertung_nach_spiel, lab, "SNES",
                    "/x.mgl", 4 * 60)
check("unter 5 Minuten wird nicht gefragt", ok is False and sk.gefragt == 0)
ok, sk = mit_tasten(fe, ["right", "right", "ok"], fe._wertung_nach_spiel,
                    lab, "SNES", "/x.mgl", 42 * 60)
e = WT.wertung("SNES", lab)
check("Rechts, Rechts, A: Vorschlag 70 + 10 gespeichert, startbar",
      ok is True and e and e["spass"] == 80 and e["kind"] == "game"
      and e["arg"][0] == arg[0], e)
check("das Testarchiv kennt es danach",
      any(c[0] == fm.t("testarchiv_cat") for c in fe.cats))
ok, sk = mit_tasten(fe, ["ok"], fe._wertung_nach_spiel, lab, "SNES",
                    "/x.mgl", 3600)
check("schon bewertet: nicht noch einmal fragen",
      ok is False and sk.gefragt == 0)
lab2, kind2, arg2 = spiele[4]
fm.load_recent = lambda: [(lab2, "game", list(arg2))]
ok, sk = mit_tasten(fe, ["left", "back"], fe._wertung_nach_spiel, lab2,
                    "SNES", "/x.mgl", 3600)
check("B heisst spaeter: nichts gespeichert",
      ok is False and WT.wertung("SNES", lab2) is None)
fe._vorgemerkte_aktion = None
ok, sk = mit_tasten(fe, ["down"], fe._wertung_nach_spiel, lab2, "SNES",
                    "/x.mgl", 3600)
check("eine andere Taste schliesst die Leiste und wirkt danach weiter",
      ok is False and fe._vorgemerkte_aktion == "down"
      and WT.wertung("SNES", lab2) is None)
fe._vorgemerkte_aktion = None
ok, sk = mit_tasten(fe, [], fe._wertung_nach_spiel, lab2, "SNES", "/x.mgl",
                    3600)
check("ohne Taste: die Leiste geht von selbst",
      ok is False and WT.wertung("SNES", lab2) is None)
ok, sk = mit_tasten(fe, ["select", "up", "right", "ok"],
                    fe._wertung_nach_spiel, lab2, "SNES", "/x.mgl", 3600)
e = WT.wertung("SNES", lab2)
check("Select oeffnet den ganzen Kasten (mit dem Wert aus der Leiste)",
      ok is True and e and e["spass"] == 75 and e.get("fazit") == "pflicht",
      e)
fm.load_recent = lambda: []
ok, sk = mit_tasten(fe, ["ok"], fe._wertung_nach_spiel, "Invade-a-Load",
                    None, "/x.mgl", 3600)
check("kein Spiel aus der Liste (Gimmick, AmigaVision): keine Frage",
      ok is False and sk.gefragt == 0)
ok, sk = mit_tasten(fe, ["ok"], fe._wertung_nach_spiel, "Pac-Man", None,
                    "/media/fat/_Arcade/Pac-Man.mra", 3600)
check("Arcade (.mra): gefragt und unter ARCADE gespeichert",
      ok is True and WT.spielspass(WT.ARCADE, "Pac-Man") == 75
      and WT.wertung(WT.ARCADE, "Pac-Man")["kind"] == "core")
WT.toggle_fragen()
ok, sk = mit_tasten(fe, ["ok"], fe._wertung_nach_spiel, "Neu2", "SNES",
                    "/x.mgl", 3600)
check("'Nach dem Spielen fragen: AUS': keine Leiste",
      ok is False and sk.gefragt == 0)
WT.toggle_fragen()
_leiste = fe._wertung_leiste
fe._wertung_leiste = lambda *a: 1 / 0
fm.load_recent = lambda: [("Neu3", "game", ["/n", ".sfc", "SNES"])]
check("ein Fehler darin haelt die Rueckkehr nicht auf",
      fe._wertung_nach_spiel("Neu3", "SNES", "/x.mgl", 3600) is False)
fe._wertung_leiste = _leiste

# ---------------------------------------------------------------------------
print()
print("Test 8: der Wertungskasten")
# ---------------------------------------------------------------------------
check("Zeilen Konsole",
      fe._wertung_zeilen("SNES", False)
      == ["grafik", "sound", "steuerung", "schwierigkeit", "spieler",
          "fazit", "spass"])
check("Zeilen Computer mit Loeschen",
      fe._wertung_zeilen("C64", True)
      == ["grafik", "musik", "effekte", "schwierigkeit", "spieler", "fazit",
          "spass", "loeschen"])
WT.toggle_nur_spielspass()
check("nur Spielspass", fe._wertung_zeilen("SNES", False) == ["spass"])
WT.toggle_nur_spielspass()
erg, _sk = mit_tasten(fe, ["up", "up", "right", "up", "right", "right", "up",
                           "right", "right", "up", "up", "right", "select",
                           "down", "down", "down", "down", "down", "down",
                           "left", "ok"],
                      fe.wertungskasten, "Kasten", "game",
                      ["/k", ".sfc", "SNES"], "SNES")
e = WT.wertung("SNES", "Kasten")
check("aendern, leeren, speichern",
      erg == "gespeichert" and e["spieler"] == "1"
      and e["schwierigkeit"] == "mittel" and e["steuerung"] == 55
      and "grafik" not in e and e["spass"] == 65, e)
erg, _sk = mit_tasten(fe, ["right", "back"], fe.wertungskasten, "Kasten",
                      "game", ["/k", ".sfc", "SNES"], "SNES")
check("B bricht ab, nichts geaendert",
      erg is None and WT.spielspass("SNES", "Kasten") == 65)
erg, _sk = mit_tasten(fe, ["down", "ok"], fe.wertungskasten, "Kasten",
                      "game", ["/k", ".sfc", "SNES"], "SNES")
check("Wertung loeschen", erg == "geloescht"
      and WT.wertung("SNES", "Kasten") is None)
check("Werte bleiben in ihren Grenzen",
      fe._wertung_wert_aendern("grafik", 100, True) == 100
      and fe._wertung_wert_aendern("grafik", 0, False) == 0
      and fe._wertung_wert_aendern("grafik", None, True) == 50
      and fe._wertung_wert_aendern("spieler", "2", True) is None
      and fe._wertung_wert_aendern("schwierigkeit", None, False)
      == "unfair")
for b_, h_ in ((1920, 1080), (320, 240)):
    H.set_screen(b_, h_)
    fe2 = H.make_frontend(page=1)
    try:
        fe2._wertungskasten_zeichnen("Ein sehr langer Spielname mit Zusatz",
                                     "AMIGA",
                                     fe2._wertung_zeilen("AMIGA", True), 2,
                                     {"spass": 91, "musik": 100}, 40000)
        fe2._wertung_leiste_zeichnen("Ein sehr langer Spielname", 99999, 90)
        gezeichnet = True
    except Exception as e_:                              # noqa: BLE001
        gezeichnet = e_
    check("Kasten und Leiste zeichnen sich auf %dx%d" % (b_, h_),
          gezeichnet is True, gezeichnet)
H.set_screen(1280, 720)

# ---------------------------------------------------------------------------
print()
print("Test 9: Kontextmenue, Steckbrief, Einrichtung, run_core")
# ---------------------------------------------------------------------------
fe = H.make_frontend(page=1)
fe.item_i = 1
gewaehlt = []
fe._wizard_choice = lambda titel, opts, **k: (
    gewaehlt.append(opts) or opts.index(fm.t("ctx_bewerten")))
check("bei EIN steht 'Bewerten...' im Kontextmenue",
      fe.kontextmenue() == "bewerten")
lab = fe._display_items()[1][0]
WT.speichern("SNES", lab, {"spass": 92, "grafik": 80}, "game",
             fe._display_items()[1][2])
_sk = None
try:
    _r, _sk = mit_tasten(fe, ["back"], fe.spiel_info_bildschirm)
    steckbrief = True
except Exception as e_:                                  # noqa: BLE001
    steckbrief = e_
check("der Steckbrief zeichnet sich mit Wertung und Stempel",
      steckbrief is True, steckbrief)
rc_start = fq.index("    def run_core(")
rc = fq[rc_start:fq.index("\n    def ", rc_start + 10)]
check("run_core fragt ganz zuletzt, nach der RA-Bilanz",
      "self._wertung_nach_spiel(label, syskey, path, played_seconds)" in rc
      and rc.index("self._wertung_nach_spiel(") > rc.index(
          "self._ra_bilanz_zeigen("))
wz = fq[fq.index("    def run_setup_wizard("):fq.index("    def _active_vt(")]
check("die Einrichtung fragt einmal und setzt den Schalter",
      "WT.an_setzen(do_wertungen == 0)" in wz and "total = 8" in wz
      and 't("wizard_step_title", 8, total' in wz)
import fe.translations as TR                             # noqa: E402
neu = [k_ for k_ in TR.TRANSLATIONS
       if k_.startswith(("sys_wertung", "wertung_", "testarchiv_",
                         "wizard_wertungen", "info_wertung"))
       or k_ in ("ctx_bewerten", "wizard_step_wertungen")]
check("alle Texte in beiden Sprachen",
      len(neu) > 40 and all(TR.TRANSLATIONS[k_].get("de")
                            and TR.TRANSLATIONS[k_].get("en")
                            for k_ in neu), len(neu))
wq = open(WT.__file__, encoding="utf-8").read()
check("die Wertungen schreiben nur unter /media/fat/frontend",
      WT.DATEI.endswith("bewertungen.json")
      and '"/media/fat/frontend/bewertungen.json"' in wq
      and "/media/fat/docs" not in wq and "retroachievements" not in wq)

# ---------------------------------------------------------------------------
print()
print("Test 10: Kurzfazit, Zweitmeinung, damals/heute, Monatsheft, CSV")
# ---------------------------------------------------------------------------
check("Zweitmeinung AUS (Vorgabe): keine Zeilen dafuer",
      "zweit" not in fe._wertung_zeilen("SNES", False))
WT.toggle_zweitmeinung()
check("Zweitmeinung AN: zwei Zeilen vor dem Spielspass",
      fe._wertung_zeilen("SNES", False)[-3:]
      == ["zweit", "zweit_fazit", "spass"]
      and fe._wertung_zeilen("SNES", False) != [])
WT.toggle_nur_spielspass()
check("nur Spielspass + Zweitmeinung",
      fe._wertung_zeilen("SNES", False) == ["zweit", "zweit_fazit", "spass"])
WT.toggle_nur_spielspass()
e = WT.speichern("SNES", "Fazit", {"spass": 80, "fazit": "gut_gealtert",
                                   "zweit_fazit": "zu_schwer"})
check("Zweit-Fazit nur mit Zweitmeinung, Fazit gemerkt",
      e["fazit"] == "gut_gealtert" and "zweit_fazit" not in e
      and "zweit" not in e)
e = WT.speichern("SNES", "Fazit", {"spass": 80, "fazit": "quatsch",
                                   "zweit": 74, "zweit_fazit": "zu_schwer"})
check("ungueltiges Fazit faellt weg, Zweitmeinung mit Fazit",
      "fazit" not in e and e["zweit"] == 74
      and e["zweit_fazit"] == "zu_schwer")
import fe.translations as _TR9                          # noqa: E402
check("Build 349: das Fazit heisst 'Old but Gold' - in beiden Sprachen, "
      "unter dem alten Schluessel",
      all(_TR9.TRANSLATIONS["wertung_fazit_gut_gealtert"][_sp]
          == "Old but Gold" for _sp in ("de", "en"))
      and "gut_gealtert" in WT.FAZITE)
check("Fazit waehlen: vorwaerts, rueckwaerts, leer",
      fe._wertung_wert_aendern("fazit", None, True) == WT.FAZITE[0]
      and fe._wertung_wert_aendern("fazit", None, False) == WT.FAZITE[-1]
      and fe._wertung_wert_aendern("fazit", WT.FAZITE[-1], True) is None
      and fe._wertung_wert_aendern("zweit", None, True) == 50)
WT.speichern("SNES", "Verlauf", {"spass": 80}, heute="2026-10-01")
check("damals/heute: nur eine Wertung -> nichts",
      WT.damals_heute(WT.wertung("SNES", "Verlauf")) is None)
WT.speichern("SNES", "Verlauf", {"spass": 92}, heute="2026-11-20")
check("damals/heute: erste gegen letzte",
      WT.damals_heute(WT.wertung("SNES", "Verlauf"))
      == (("2026-10-01", 80), ("2026-11-20", 92)))
WT.speichern("SNES", "Hin und her", {"spass": 80}, heute="2026-09-01")
WT.speichern("SNES", "Hin und her", {"spass": 90}, heute="2026-10-01")
WT.speichern("SNES", "Hin und her", {"spass": 80}, heute="2026-11-01")
check("damals/heute: wieder beim alten Wert -> nichts",
      WT.damals_heute(WT.wertung("SNES", "Hin und her")) is None)
WT.loeschen("SNES", "Hin und her")
check("Datum lesbar", WT.datum_lesbar("2026-11-20") == "20.11.2026"
      and WT.datum_lesbar("kaputt") == "kaputt")
for lab_, w_, d_ in (("Neu A", 90, "2026-11-02"), ("Neu B", 20, "2026-11-03"),
                     ("Alt", 70, "2026-09-01")):
    WT.speichern("SNES", lab_, {"spass": w_}, heute=d_)
h = WT.monatsheft(2026, 11)
namen_neu = [z[1] for z in h["neu"]]
check("Monatsheft: neu getestet im Monat",
      "Neu A" in namen_neu and "Neu B" in namen_neu
      and "Alt" not in namen_neu and "Verlauf" not in namen_neu)
check("Monatsheft: nachgetestet",
      [z[1] for z in h["nach"]] == ["Verlauf"], h["nach"])
_im_monat = h["neu"] + h["nach"]
check("Monatsheft: Spiel des Monats ist der beste Wert des Monats",
      h["spiel"][0] == max(z[0] for z in _im_monat), h["spiel"])
check("Monatsheft: Hits gezaehlt, Gurke ist die schwaechste unter 30",
      h["hits"] == sum(1 for z in _im_monat if z[0] >= WT.HIT_AB)
      and h["gurke"][1] == "Neu B", (h["hits"], h["gurke"]))
check("Monatsheft: Charts hoechstens fuenf, bester zuerst",
      len(h["charts"]) <= WT.CHARTS
      and h["charts"] == sorted(h["charts"], key=lambda z: -z[0]))
h9 = WT.monatsheft(2026, 9)
check("Monatsheft eines frueheren Monats kennt die spaeteren nicht",
      [z[1] for z in h9["charts"]] == ["Alt"] and h9["spiel"][1] == "Alt",
      h9["charts"])
m_ = WT.monate()
check("Monate: juengster zuerst",
      m_ == sorted(m_, reverse=True) and (2026, 9) in m_)
meldung = fe._wertung_csv_speichern()
inhalt = open(WT.CSV_DATEI, "rb").read()
text = inhalt.decode("utf-8-sig")
check("CSV geschrieben: BOM, Semikolon, deutscher Kopf",
      inhalt.startswith(b"\xef\xbb\xbf")
      and text.splitlines()[0].startswith("System;Spiel;Spielspa")
      and str(WT.CSV_DATEI) in meldung, meldung)
check("CSV: eine Zeile je Spiel, Fazit als Text",
      len(text.splitlines()) == len(WT.alle()) + 1
      and "Zu schwer" in text)
check("CSV: ueber .tmp, nichts liegen geblieben",
      not os.path.exists(WT.CSV_DATEI + ".tmp"))
_alle = WT.alle
WT.alle = lambda: {}
check("CSV ohne Wertungen: nur eine Meldung",
      fe._wertung_csv_speichern() == fm.t("csv_leer"))
WT.alle = _alle
check("Monatsheft im Menue nur bei AN",
      "wertung_monatsheft" in [k for _l, k, _a in stats_items()])
WT.toggle_heft()
check("Monatsheft AUS: kein Menuepunkt",
      "wertung_monatsheft" not in [k for _l, k, _a in stats_items()])
WT.toggle_heft()
for b_, h_ in ((1920, 1080), (320, 240)):
    H.set_screen(b_, h_)
    fe3 = H.make_frontend(page=1)
    try:
        _r, sk3 = mit_tasten(fe3, ["left", "left", "right", "back"],
                             fe3.monatsheft_bildschirm)
        fe3._wertungskasten_zeichnen(
            "Ein Name", "SNES", fe3._wertung_zeilen("SNES", True), 0,
            {"spass": 92, "zweit": 74, "fazit": "pflicht"}, 0,
            (("2026-10-01", 80), ("2026-11-20", 92)))
        ok3 = sk3.gefragt == 4
    except Exception as e_:                              # noqa: BLE001
        ok3 = e_
    check("Monatsheft blaettert, Kasten mit allen Zeilen zeichnet "
          "(%dx%d)" % (b_, h_), ok3 is True, ok3)
H.set_screen(1280, 720)
fe = H.make_frontend(page=1)
fe.item_i = 1
lab = fe._display_items()[1][0]
WT.speichern("SNES", lab, {"spass": 92, "fazit": "pflicht", "zweit": 70,
                           "zweit_fazit": "fans"}, "game",
             fe._display_items()[1][2])
try:
    mit_tasten(fe, ["back"], fe.spiel_info_bildschirm)
    sb = True
except Exception as e_:                                  # noqa: BLE001
    sb = e_
check("Steckbrief mit Fazit, Zweitmeinung und Schnitt", sb is True, sb)
fq2 = fq[fq.index("    def spiel_info_bildschirm("):]
fq2 = fq2[:fq2.index("\n    def ", 10)]
check("Steckbrief rechnet den Schnitt und kennt damals/heute",
      't("info_schnitt")' in fq2 and "WT.damals_heute(_wert)" in fq2)
WT.toggle_zweitmeinung()

# ---------------------------------------------------------------------------
print()
print("Test 11: der Kasten im Heft-Stil (Build 348)")
# ---------------------------------------------------------------------------
fe = H.make_frontend(page=1)
_rects = []
_rect_echt = fe.fb.rect
fe.fb.rect = lambda x, y, w, h, c: _rects.append((x, w, c))
n_ = fe._wertung_segmente(0, 0, 400, 8, 92, 1)
fe.fb.rect = _rect_echt
_aus = fe.fb._darken(fm.C_TEXT, 0.18)
_F = fm.Frontend.WERTUNG_FARBEN
farben = [c for _x, _w, c in _rects]
check("Pegel: 20 Segmente, 18 an (92 %)",
      n_ == 20 and len(farben) == 20 and farben.count(_aus) == 2, n_)
check("jedes Segment in der Farbe seiner Stufe: 9 rot, 6 gelb, 3 gruen",
      farben[:9] == [_F["rot"]] * 9 and farben[9:15] == [_F["gelb"]] * 6
      and farben[15:18] == [_F["gruen"]] * 3)
_rects[:] = []
fe.fb.rect = lambda x, y, w, h, c: _rects.append((x, w, c))
n_ = fe._wertung_segmente(0, 0, 60, 8, None, 1)
fe.fb.rect = _rect_echt
check("schmal: 10 Segmente; ohne Wert alle aus",
      n_ == 10 and all(c == _aus for _x, _w, c in _rects))
check("Segmente laufen nicht ueber die Breite hinaus",
      max(x + w for x, w, _c in _rects) <= 60)
gefragt_c = []


def _cover(item, sk, bw, bh):
    gefragt_c.append(item[0])
    return ((4, 4, bytes(64)), False) if item[0] == "Mit" else (None, True)
fe._ansicht_cover = _cover
fe._wertung_cover(("Mit", "game", None), "SNES", 100, 100)
fe._wertung_cover(("Mit", "game", None), "SNES", 100, 100)
fe._wertung_cover(("Ohne", "game", None), "SNES", 100, 100)
fe._wertung_cover(("Ohne", "game", None), "SNES", 100, 100)
check("ein Cover wird einmal geholt, ein fehlendes jedes Mal neu gefragt",
      gefragt_c == ["Mit", "Ohne", "Ohne"], gefragt_c)
for st_ in ("hit", "klassiker", "gurke"):
    b_, h_ = fe._wertung_stempel_mass(st_, 2)
    check("Stempel %s: Rahmen passt um die Schrift" % st_,
          b_ >= max(len(z) for z in fe._wertung_stempel_zeilen(st_)) * 32
          + 16 and h_ > 0)
for b_, h_, cov in ((1920, 1080, True), (1280, 720, False), (640, 480, True),
                    (320, 240, False)):
    H.set_screen(b_, h_)
    fe4 = H.make_frontend(page=1)
    if cov:
        fe4._ansicht_cover = lambda item, sk, bw, bh: (
            (max(1, min(bw, 40)), max(1, min(bh, 40)),
             bytes(4 * max(1, min(bw, 40)) * max(1, min(bh, 40)))), False)
    try:
        for sel_ in range(len(fe4._wertung_zeilen("SNES", True))):
            fe4._wertungskasten_zeichnen(
                "Ein recht langer Spielname - Teil Zwei", "SNES",
                fe4._wertung_zeilen("SNES", True), sel_,
                {"spass": 92, "grafik": 85, "zweit": 74}, 40000,
                (("2026-10-01", 80), ("2026-11-20", 92)),
                eintrag=("X", "game", ["/x", ".sfc", "SNES"]))
        ok4 = True
    except Exception as e_:                              # noqa: BLE001
        ok4 = e_
    check("Kasten zeichnet sich %dx%d%s, jede Zeile markiert"
          % (b_, h_, " mit Cover" if cov else ""), ok4 is True, ok4)
H.set_screen(1280, 720)
fq3 = fq[fq.index("    def _wertungskasten_zeichnen("):]
fq3 = fq3[:fq3.index("\n    def ", 10)]
check("das Cover kommt ueber _wertung_cover, der Kasten bekommt den Eintrag",
      "self._wertung_cover(eintrag, syskey" in fq3
      and "eintrag=(label, kind, arg))" in fq)

print()
if fails:
    print("ROT: %d Pruefung(en) fehlgeschlagen:" % len(fails))
    for f_ in fails:
        print("   - " + f_)
    sys.exit(1)
print("ALLES GRUEN")
