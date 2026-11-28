#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Die Zeitmaschine (Build 351).

GEPRUEFT WIRD:
  1. Schalter (Vorgabe AN), Systemmenue, Kategorie da/weg.
  2. Nichts kostet, solange niemand reist: beim Start und beim Zeichnen
     wird kein Verzeichnis gebaut und keine Spieldaten gelesen.
  3. Das Verzeichnis: Jahre, ohne Jahr, unplausible Jahre, doppelte
     Eintraege, Arcade (.mra), Happen und Abbruch.
  4. Der Knoten fuer ein Jahr: "Zurueck" und "Anderes Jahr" oben, dann
     "Neu in", "Deine Wertungen", die Systeme; das Neueste zuerst.
  5. Das Drehrad: +-1, +-10, Grenzen, A, B, klemmende Eingabe.
  6. Die Reise im Frontend: Name mit Jahr, Kuerzel bleibt, Liste,
     Zurueck ueber den Punkt, ueber B oben, NICHT ueber B im Unterordner,
     Ausschalten und Neu-Einlesen beenden die Reise.
  7. Vorbereitung mit B abgebrochen: alles bleibt, wie es war.
  8. Keine Jahre: Hinweis statt Rad.
  9. Bildschirme bei 1280x720 und 320x240.

Ausfuehren:
    python3 tools/test_zeitmaschine.py
"""
import os
import sys

_HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HIER)
import _harness as H                                     # noqa: E402
import fe.zeitmaschine as ZM                             # noqa: E402
import fe.hauptseite as HS                               # noqa: E402
import fe.menu as MENU                                   # noqa: E402
import fe.wertungen as WT                                # noqa: E402

fm = H.fm
fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


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


def spiel(name, sk):
    return (name, "game", ("/f/%s.rom" % name, ".rom", sk, None, None))


JAHRE = {"Super Mario World": "1990-11-21", "F-Zero": "1990",
         "Super Metroid": "1994", "Chrono Trigger": "1995",
         "Sonic": "1991", "Streets of Rage": "19910802",
         "Ohne Jahr": "", "Zu frueh": "1965", "Zukunft": "2999"}
GELESEN = []


def meta(sk, label):
    GELESEN.append((sk, label))
    return {"year": JAHRE.get(label, "")}


def mra(pfad):
    return {"year": "1981"} if "galaga" in pfad else {}


def kategorien():
    snes = {"folders": {"Hacks": {"folders": {}, "items": [
        spiel("Super Metroid", "SNES")]}},
        "items": [spiel(n, "SNES") for n in ("Super Mario World", "F-Zero",
                                            "Chrono Trigger", "Ohne Jahr",
                                            "Zu frueh", "Zukunft")]}
    md = {"folders": {}, "items": [spiel("Sonic", "MEGADRIVE"),
                                   spiel("Streets of Rage", "MEGADRIVE")]}
    arc = {"folders": {}, "items": [
        ("Galaga", "core", "/media/fat/_Arcade/galaga.mra"),
        ("Menu", "core", "/media/fat/menu.rbf")]}
    fav = {"folders": {}, "items": [spiel("Super Mario World", "SNES")]}
    return [("SNES", snes, "SNES"), ("Mega Drive", md, "MEGADRIVE"),
            ("Arcade", arc, "ARCADE"),
            ("Favoriten", fav, None),
            ("Doppelt", {"folders": {}, "items": [
                spiel("Sonic", "MEGADRIVE")]}, "MEGADRIVE")]


# ---------------------------------------------------------------------------
print("Test 1: Schalter, Menue, Kategorie")
# ---------------------------------------------------------------------------
check("Vorgabe AN", ZM.an() is True and not os.path.exists(ZM.AUS_FLAG))


def stats_items():
    sysm = MENU.system_items(False, "local", "")
    for _n, node in sysm["folders"].items():
        kinds = [k for _l, k, _a in node["items"]]
        if "diary" in kinds:
            return node["items"]
    return []


its = stats_items()
check("Schalter im Systemmenue (Statistiken & Erfolge)",
      ("zeitmaschine_an" in [k for _l, k, _a in its])
      and fm.t("sys_zm_an") in [l for l, _k, _a in its])
fe = H.make_frontend(page=0)
check("ohne ein einziges System: keine Zeitmaschine (nichts zu reisen)",
      not any(c[2] for c in fe.cats) and fe._zm_index() is None,
      [c[0] for c in fe.cats])
fe.cats = kategorien() + fe.cats
fe._zm_sync_kategorie()
namen = [c[0] for c in fe.cats]
check("mit Systemen steht die Kategorie auf der Hauptseite",
      fm.t("zm_cat") in namen, namen)
zi = fe._zm_index()
check("... vor dem Zufalls-Zock",
      zi is not None and (fm.t("zufallszock_title") not in namen
                          or zi < namen.index(fm.t("zufallszock_title"))))
check("ausschalten", ZM.toggle_an() is False and os.path.exists(ZM.AUS_FLAG))
fe._zm_sync_kategorie()
check("AUS: die Kategorie ist weg", fe._zm_index() is None)
its = stats_items()
check("AUS: der Schalter sagt AUS",
      fm.t("sys_zm_aus") in [l for l, _k, _a in its])
check("einschalten", ZM.toggle_an() is True
      and not os.path.exists(ZM.AUS_FLAG))
fe._zm_sync_kategorie()
check("AN: die Kategorie ist wieder da, genau einmal",
      [c[0] for c in fe.cats].count(fm.t("zm_cat")) == 1)
fq = open(H.FRONTEND_PY, encoding="utf-8").read()
check("Menueschalter und Eintraege sind verdrahtet",
      'elif kind == "zeitmaschine_an":' in fq
      and 'elif kind == "zeitmaschine":' in fq
      and 'elif kind == "zeitmaschine_zurueck":' in fq)
import fe.vorfuehrung as VF                              # noqa: E402
check("die Vorfuehrung kennt den Schalter",
      any("zeitmaschine_an" in g[3] for g in VF.GRUPPEN))

# ---------------------------------------------------------------------------
print()
print("Test 2: nichts kostet, solange niemand reist")
# ---------------------------------------------------------------------------
gebaut = []
_bauen_echt = ZM.bauen
ZM.bauen = lambda *a, **k: gebaut.append(1) or _bauen_echt(*a, **k)
_gm_echt, _mra_echt = fm.get_meta, fm.mra_meta
fm.get_meta = meta
fm.mra_meta = mra
del GELESEN[:]
fe = H.make_frontend(page=0)
fe.cats = kategorien() + fe.cats
fe._zm_sync_kategorie()
fe.draw()
fe.cat_i = fe._zm_index()
fe.draw()
check("Start und Zeichnen (auch auf der Kategorie): kein Verzeichnis",
      not gebaut and fe._zm_vz is None, gebaut)
check("... und keine Spieldaten fuer die Zeitmaschine gelesen",
      not GELESEN, GELESEN[:5])
fe.build_categories()
fe.cats = kategorien() + fe.cats
fe._zm_sync_kategorie()
fe.draw()
check("... auch nicht nach einem Neu-Aufbau",
      not gebaut and fe._zm_vz is None and not GELESEN)
knoten0 = fe.cats[fe._zm_index()][1]
check("vor der Reise: ein einziger Eintrag 'Zeitreise starten'",
      [(l, k) for l, k, _a in knoten0["items"]]
      == [(fm.t("zm_starten"), "zeitmaschine")] and not knoten0["folders"])
bq = H.koerper(fq, "build_categories")
check("im Aufbau nur Name und Startknoten (kein bauen())",
      "ZM.bauen" not in bq and "self._zm_knoten()" in bq)

# ---------------------------------------------------------------------------
print()
print("Test 3: das Verzeichnis")
# ---------------------------------------------------------------------------
vz = _bauen_echt(kategorien(), meta, mra, 2026)
check("Jahre gelesen (Datum, 8 Ziffern, Jahreszahl)",
      sorted(vz.jahre) == [1981, 1990, 1991, 1994, 1995],
      sorted(vz.jahre))
check("ohne Jahr, zu frueh (vor 1970), Zukunft: ohne Jahr gezaehlt",
      vz.ohne == 3, vz.ohne)
check("Unterordner durchsucht", vz.jahr_von("SNES", "Super Metroid") == 1994)
check("doppelte Eintraege (zwei Kategorien, ein System) einmal",
      sum(1 for e in vz.jahre[1991] if e[1] == "Sonic") == 1)
check("Favoriten (ohne System) nicht mitgezaehlt",
      len(vz.jahre[1990]) == 2, vz.jahre[1990])
check("Arcade: .mra mit Jahr, ein .rbf-Core gar nicht",
      [e[1] for e in vz.jahre[1981]] == ["Galaga"]
      and vz.jahr_von("ARCADE", "Menu") == 0)
check("zaehlen: bis 1991 und neu in 1991", vz.zaehlen(1991) == (5, 2),
      vz.zaehlen(1991))
check("bereich und Startjahr (meiste Neuerscheinungen, das fruehere)",
      vz.bereich() == (1981, 1995) and vz.startjahr() == 1990,
      (vz.bereich(), vz.startjahr()))
check("Jahr bis: 'bis' zaehlt mit", ZM.jahr_zahl("2026", 2026) == 2026
      and ZM.jahr_zahl("2027", 2026) == 0 and ZM.jahr_zahl("1970") == 1970
      and ZM.jahr_zahl("1969") == 0 and ZM.jahr_zahl(None) == 0)
viele = [("SNES", {"folders": {}, "items": [
    spiel("S%d" % i, "SNES") for i in range(ZM.HAPPEN * 2 + 5)]}, "SNES")]
blicke = []
vz2 = _bauen_echt(viele, meta, None, 2026, lambda n: blicke.append(n))
check("zwischendurch alle HAPPEN Spiele",
      blicke == [ZM.HAPPEN, ZM.HAPPEN * 2] and vz2.ohne == ZM.HAPPEN * 2 + 5,
      blicke)
check("zwischendurch False bricht ab (None)",
      _bauen_echt(viele, meta, None, 2026, lambda n: False) is None)
kaputt = _bauen_echt(kategorien(), lambda s, l: 1 / 0, lambda p: 1 / 0, 2026)
check("Fehler in den Spieldaten: das Spiel faehrt ohne Jahr",
      not kaputt.jahre and kaputt.ohne == 10, kaputt.ohne)
check("anzahl: genau so viele, wie bauen() liest",
      ZM.anzahl(kategorien(), mra) == 10 and ZM.anzahl(kategorien()) == 9
      and len(vz.gesehen) == 10, ZM.anzahl(kategorien(), mra))
check("leeres Verzeichnis: kein Bereich, kein Startjahr",
      ZM.Verzeichnis().bereich() is None
      and ZM.Verzeichnis().startjahr() is None)

# ---------------------------------------------------------------------------
print()
print("Test 4: der Knoten fuer ein Jahr")
# ---------------------------------------------------------------------------
TX = {"neu": "Neu in %d", "wertungen": "Deine Wertungen",
      "zurueck": "Zurueck", "anderes": "Anderes"}
SN = {"SNES": "SNES", "MEGADRIVE": "Mega Drive", "ARCADE": "Arcade"}
k = ZM.knoten(vz, 1991, lambda s: SN.get(s, s), TX)
check("oben: Zurueck und Anderes Jahr",
      [(l, kd) for l, kd, _a in k["oben"]]
      == [("Zurueck", "zeitmaschine_zurueck"), ("Anderes", "zeitmaschine")]
      and k["items"] == [])
check("Neu in 1991 zuerst, nach Name",
      k["folge"] == ["Neu in 1991"]
      and [e[0] for e in k["folders"]["Neu in 1991"]["items"]]
      == ["Sonic", "Streets of Rage"])
check("je System alles bis 1991, das Neueste zuerst",
      [e[0] for e in k["folders"]["SNES"]["items"]]
      == ["F-Zero", "Super Mario World"]
      and [e[0] for e in k["folders"]["Arcade"]["items"]] == ["Galaga"])
check("nichts aus der Zukunft",
      "Super Metroid" not in str(k) and "Chrono" not in str(k))
k90 = ZM.knoten(vz, 1990, lambda s: SN.get(s, s), TX)
check("auch nicht aus dem naechsten Jahr",
      "Sonic" not in str(k90) and "MEGADRIVE" not in k90["folders"]
      and "Mega Drive" not in k90["folders"], sorted(k90["folders"]))
k95 = ZM.knoten(vz, 1995, lambda s: SN.get(s, s), TX)
check("das Neueste zuerst, im selben Jahr nach Name",
      [e[0] for e in k95["folders"]["SNES"]["items"]]
      == ["Chrono Trigger", "Super Metroid", "F-Zero", "Super Mario World"])
check("Eintraege tragen ihr echtes arg (startbar)",
      k["folders"]["SNES"]["items"][0][1:] == (
          "game", ("/f/F-Zero.rom", ".rom", "SNES", None, None)))
check("ohne Neuerscheinung kein 'Neu in'",
      "Neu in 1992" not in ZM.knoten(vz, 1992, str, TX)["folders"])
kw = ZM.knoten(vz, 1995, lambda s: SN.get(s, s), TX,
               {("SNES", "Chrono Trigger"): 93, ("ARCADE", "Galaga"): 88,
                ("SNES", "F-Zero"): 88, ("SNES", "Fremd"): 99})
check("Deine Wertungen: nur bis zum Jahr, bester zuerst, Arcade dabei",
      [e[0] for e in kw["folders"]["Deine Wertungen"]["items"]]
      == ["Chrono Trigger", "F-Zero", "Galaga"]
      and kw["folge"] == ["Neu in 1995", "Deine Wertungen"])
kw0 = ZM.knoten(vz, 1990, lambda s: SN.get(s, s), TX,
                {("SNES", "Chrono Trigger"): 93})
check("keine Wertung bis zum Jahr: kein Ordner",
      "Deine Wertungen" not in kw0["folders"])
kd = ZM.knoten(vz, 1995, lambda s: "Gleich", TX)
vz_neo = ZM.Verzeichnis()
vz_neo.aufnehmen("NEOGEO", "Metal Slug", "core", "/x/mslug.mra", 1996)
vz_neo.aufnehmen("NEOGEO", "Metal Slug", "game", None, 1996)
vz_neo.aufnehmen("NEOGEO", "Blazing Star", "game", ("/x/b.neo",), 1998)
kn = ZM.knoten(vz_neo, 1998, str, TX, {("ARCADE", "Metal Slug"): 90,
                                      ("NEOGEO", "Blazing Star"): 80})
check("ein .mra zaehlt mit seiner Arcade-Wertung (wie fe/wertungen)",
      [e[0] for e in kn["folders"]["Deine Wertungen"]["items"]]
      == ["Metal Slug", "Blazing Star"])
check("gleiche Systemnamen: mit Kuerzel unterschieden",
      sum(1 for n in kd["folders"] if n.startswith("Gleich")) == 3)

# ---------------------------------------------------------------------------
print()
print("Test 5: das Drehrad")
# ---------------------------------------------------------------------------
fe = H.make_frontend(page=0)
fe._zm_vz = vz
echt_inp = fe.inp


def rad(tasten, start=None):
    fe._zm_jahr = start
    fe.inp = Skript(echt_inp, tasten)
    try:
        return fe._zm_waehlen()
    finally:
        fe.inp = echt_inp


check("Start im Jahr mit den meisten Neuerscheinungen, A reist",
      rad(["ok"]) == 1990)
check("rechts, rechts, links: +1", rad(["right", "right", "left", "ok"])
      == 1991)
check("hoch: +10, an der Grenze geklemmt", rad(["up", "ok"]) == 1995)
check("runter zweimal: geklemmt auf das frueheste Jahr",
      rad(["down", "down", "ok"]) == 1981)
check("von der Grenze sofort zurueck (nicht 'hinter' ihr)",
      rad(["up", "up", "left", "ok"]) == 1994)
check("B bricht ab", rad(["right", "back"]) is None)
check("das letzte Reisejahr ist der Start", rad(["ok"], 1993) == 1993)
check("klemmende Eingabe (nur leere Antworten): das Rad gibt auf",
      rad([]) is None)

# ---------------------------------------------------------------------------
print()
print("Test 6: die Reise im Frontend")
# ---------------------------------------------------------------------------
WT.an_setzen(True)
WT.speichern("SNES", "F-Zero", {"spass": 82})
fe = H.make_frontend(page=0)
fe.cats = kategorien() + [(fe._zm_name(), fe._zm_knoten(), None)]
fe._hauptseite_anwenden()
zi = fe._zm_index()
fe.cat_i = zi
fe.page = 1
fe.nav_path = []
fe.item_i = 0
del GELESEN[:]
fe.inp = Skript(echt_inp, ["right", "ok"])
fe._zm_reisen()
fe.inp = echt_inp
name = fe.cats[fe._zm_index()][0]
check("Reise nach 1991: der Name traegt das Jahr",
      name == fm.t("zm_cat") + " \xb7 1991" and fe._zm_jahr == 1991, name)
check("das Kuerzel bleibt (ausblenden/ordnen gilt weiter)",
      HS.schluessel(name) == "zm_cat" == HS.schluessel(fm.t("zm_cat"))
      and HS.schluessel("Zeitmaschine \xb7 1991") == "zm_cat"
      and HS.schluessel("Time machine \xb7 1991") == "zm_cat"
      and HS.schluessel("SNES \xb7 1991") != "zm_cat"
      and HS.schluessel(fm.t("zm_cat") + " \xb7 19x1") != "zm_cat")
check("man steht in der Zeitmaschine, oben", fe.page == 1
      and fe.cat_i == fe._zm_index() and fe.item_i == 0 and not fe.nav_path)
liste = [(l, kd) for l, kd, _a in fe._display_items()]
check("die Liste: Zurueck, Anderes Jahr, Neu in, Wertungen, Systeme",
      liste[:5] == [(fm.t("zm_zurueck"), "zeitmaschine_zurueck"),
                    (fm.t("zm_anderes"), "zeitmaschine"),
                    (fm.t("zm_neu") % 1991 + "/", "folder"),
                    (fm.t("zm_wertungen") + "/", "folder"),
                    ("Arcade/", "folder")], liste)
check("die Spieldaten nur einmal je Spiel gelesen",
      len(GELESEN) == len(set(GELESEN)) == 9, len(GELESEN))
# Anderes Jahr: kein zweiter Aufbau
fe._kategorie_position = {fe._zm_index(): (3, 0), 0: (2, 0)}
del gebaut[:]
fe.inp = Skript(echt_inp, ["left", "ok"])
fe._zm_reisen()
fe.inp = echt_inp
check("anderes Jahr: das Verzeichnis wird nicht neu gebaut",
      not gebaut and fe._zm_jahr == 1990)
check("die gemerkte Listenposition der alten Liste ist vergessen "
      "(nur die der Zeitmaschine)",
      fe._kategorie_position == {0: (2, 0)}, fe._kategorie_position)
# B im Unterordner: Reise bleibt
fe.nav_path = ["SNES"]
fe._nav_position_stack = [(4, 0)]
fe._go_back_or_confirm_quit()
check("B im Unterordner: eine Ebene hoch, die Reise bleibt",
      fe.page == 1 and fe._zm_jahr == 1990 and not fe.nav_path)
fe._go_back_or_confirm_quit()
check("B oben: zurueck in die Gegenwart, auf der Hauptseite",
      fe.page == 0 and fe._zm_jahr is None
      and fe.cats[fe.cat_i][0] == fm.t("zm_cat")
      and fe.cats[fe.cat_i][1]["items"][0][1] == "zeitmaschine")
# B auf einer anderen Kategorie beruehrt nichts
fe._zm_jahr = 1990
fe._zm_ersetzen()
fe.cat_i = 0
fe.page = 1
fe.nav_path = []
fe._go_back_or_confirm_quit()
check("B in einer anderen Kategorie: die Reise bleibt", fe._zm_jahr == 1990)
# Zurueck ueber den Punkt
fe.cat_i = fe._zm_index()
fe.page = 1
fe.nav_path = []
check("der Punkt 'Zurueck in die Gegenwart'",
      fe._zm_gegenwart() is True and fe.page == 0 and fe._zm_jahr is None
      and fe.cat_i == fe._zm_index())
check("zweimal Gegenwart: nichts passiert", fe._zm_gegenwart() is False)
# Ausschalten waehrend der Reise
fe._zm_jahr = 1990
fe._zm_ersetzen()
ZM.toggle_an()
fe._zm_jahr = None
fe._zm_sync_kategorie()
check("ausgeschaltet waehrend der Reise: weg, keine Reise mehr",
      fe._zm_index() is None and not any(
          c[0].startswith(fm.t("zm_cat")) for c in fe.cats))
ZM.toggle_an()
fe._zm_sync_kategorie()
fe._zm_jahr = 1990
fe._zm_ersetzen()
fe.cat_i = fe._zm_index()
check("Neuaufbau findet die Zeitmaschine wieder (Name ohne Jahr)",
      fe._position_merken() == (fm.t("zm_cat"), None)
      and fe._category_match_key(fe.cats[fe.cat_i])
      == fe._category_match_key((fm.t("zm_cat"), {}, None))
      and fe._category_match_key(("Zeitmaschine-Fan", {}, None))
      != ("label", "zm_cat"), fe._position_merken())
fe.build_categories()
check("Neu-Einlesen: Verzeichnis verworfen, Reise beendet",
      fe._zm_vz is None and fe._zm_jahr is None)
WT.an_setzen(False)

# ---------------------------------------------------------------------------
print()
print("Test 7: Vorbereitung mit B abgebrochen")
# ---------------------------------------------------------------------------
fe = H.make_frontend(page=0)
fe.cats = viele + [(fe._zm_name(), fe._zm_knoten(), None)]
fe._hauptseite_anwenden()
fe.cat_i = fe._zm_index()
fe.page = 1
vorher = list(fe.cats)
fe.inp = Skript(echt_inp, ["back", "ok"])
fe._zm_reisen()
fe.inp = echt_inp
check("abgebrochen: kein Verzeichnis, keine Reise, alles wie vorher",
      fe._zm_vz is None and fe._zm_jahr is None and fe.cats == vorher
      and fe.page == 1)

# ---------------------------------------------------------------------------
print()
print("Test 8: keine Jahre")
# ---------------------------------------------------------------------------
fe = H.make_frontend(page=0)
fe.cats = [("SNES", {"folders": {}, "items": [spiel("Ohne Jahr", "SNES")]},
            "SNES"), (fe._zm_name(), fe._zm_knoten(), None)]
fe._hauptseite_anwenden()
fe.cat_i = fe._zm_index()
gezeigt = []
fe._zm_schirm = lambda zeilen, h: gezeigt.append(zeilen)
fe.inp = Skript(echt_inp, ["ok"])
fe._zm_reisen()
fe.inp = echt_inp
check("Hinweis statt Rad, keine Reise",
      [fm.t("zm_keine")] in gezeigt and fe._zm_jahr is None)

# ---------------------------------------------------------------------------
print()
print("Test 9: Bildschirme")
# ---------------------------------------------------------------------------
for b_, h_ in ((1280, 720), (320, 240)):
    H.set_screen(b_, h_)
    fe = H.make_frontend(page=0)
    fe._zm_vz = vz
    try:
        fe._zm_rad_zeichnen(1991, 1981, 1995)
        buf = bytes(fe.fb.buf)
        ok_ = len(set(buf[i:i + 4] for i in range(0, len(buf), 4 * 97))) > 2
        fe._zm_schirm([fm.t("zm_vorbereiten"),
                       fm.t("zm_fortschritt", 300, 1200)],
                      fm.t("zm_abbrechen"))
    except Exception as e_:                              # noqa: BLE001
        ok_ = e_
    check("Rad und Vorbereitung %dx%d gezeichnet" % (b_, h_), ok_ is True,
          ok_)
H.set_screen(1280, 720)
fm.get_meta, fm.mra_meta = _gm_echt, _mra_echt
ZM.bauen = _bauen_echt

print()
if fails:
    print("ROT: %d Pruefung(en) fehlgeschlagen:" % len(fails))
    for f_ in fails:
        print("   - " + f_)
    sys.exit(1)
print("ALLES GRUEN")
