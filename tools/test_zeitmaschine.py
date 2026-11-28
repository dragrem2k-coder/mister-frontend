#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Die Zeitmaschine (Build 351, ueberarbeitet in Build 353).

GEPRUEFT WIRD:
  1. Schalter (Vorgabe AN), Systemmenue, Kategorie da/weg.
  2. Nichts kostet, solange niemand reist: beim Start und beim Zeichnen
     wird kein Verzeichnis gebaut, kein Merker geladen, nichts gelesen.
  3. Das Verzeichnis: Jahre, ohne Jahr, unplausible Jahre, doppelte
     Eintraege, Arcade (.mra), Happen und Abbruch, das Weiterdrehen
     ueber leere Jahre.
  3b. Der Merker (Build 353): gelesen wird nur einmal, auch ueber einen
     Neustart; eine geaenderte Quelle liest nur ihr System neu; kaputte
     oder fremde Datei; Speichern im Hintergrund.
  4. Der Knoten fuer EIN Jahr: "Zurueck" und "Anderes Jahr" oben, dann
     "Alle Spiele aus", "Deine Wertungen", die Systeme - nur dieses Jahr.
  5. Das Drehrad: +-1 und +-10 nur auf Jahre mit Spielen, A, B,
     klemmende Eingabe.
  6. Die Reise im Frontend: Name mit Jahr, Kuerzel, Abzeichen, Liste,
     Zurueck ueber den Punkt, ueber B oben, NICHT ueber B im Unterordner;
     ein Neuaufbau laesst die Reise stehen, Neu-Einlesen beendet sie;
     Neustart liest nichts neu.
  7. Vorbereitung mit B abgebrochen: alles bleibt, das Gelesene bleibt
     gemerkt.
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
      not gebaut and getattr(fe, "_zm_vz", None) is None, gebaut)
check("... keine Spieldaten gelesen, kein Merker geladen",
      not GELESEN and not ZM._merker["geladen"]
      and not os.path.exists(ZM.MERKER_DATEI), GELESEN[:5])
fe.build_categories()
fe.cats = kategorien() + fe.cats
fe._zm_sync_kategorie()
fe.draw()
check("... auch nicht nach einem Neu-Aufbau",
      not gebaut and getattr(fe, "_zm_vz", None) is None and not GELESEN
      and not ZM._merker["geladen"])
knoten0 = fe.cats[fe._zm_index()][1]
check("vor der Reise: ein einziger Eintrag 'Zeitreise starten'",
      [(l, k) for l, k, _a in knoten0["items"]]
      == [(fm.t("zm_starten"), "zeitmaschine")] and not knoten0["folders"])
bq = H.koerper(fq, "build_categories")
check("im Aufbau nur Name und Startknoten (kein bauen())",
      "ZM.bauen" not in bq and "ZM.offen" not in bq
      and "self._zm_knoten()" in bq)

# ---------------------------------------------------------------------------
print()
print("Test 3: das Verzeichnis")
# ---------------------------------------------------------------------------
ZM.merker_vergessen()
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
check("zaehlen: Spiele aus genau diesem Jahr, Systeme",
      vz.zaehlen(1991) == 2 and vz.zaehlen(1992) == 0
      and vz.systeme(1991) == 1 and vz.systeme(1990) == 1)
check("bereich und Startjahr (meiste Spiele, bei Gleichstand das fruehere)",
      vz.bereich() == (1981, 1995) and vz.startjahr() == 1990,
      (vz.bereich(), vz.startjahr()))
check("weiter +1/-1: nur Jahre mit Spielen, am Rand stehen bleiben",
      vz.weiter(1990, 1) == 1991 and vz.weiter(1991, 1) == 1994
      and vz.weiter(1995, 1) == 1995 and vz.weiter(1990, -1) == 1981
      and vz.weiter(1981, -1) == 1981)
check("weiter +10/-10: zehn Jahre, dann das naechste mit Spielen",
      vz.weiter(1981, 10) == 1991 and vz.weiter(1990, 10) == 1995
      and vz.weiter(1994, -10) == 1981 and vz.weiter(1995, -10) == 1981,
      (vz.weiter(1981, 10), vz.weiter(1994, -10)))
vz_r = ZM.Verzeichnis()
vz_r.aufnehmen("X", "a", "game", None, 1980)
vz_r.aufnehmen("X", "b", "game", None, 1990)
vz_r.aufnehmen("X", "c", "game", None, 1999)
check("weiter -10 bei Gleichstand: zuerst in Laufrichtung",
      vz_r.weiter(1995, -10) == 1980 and vz_r.weiter(1975, 10) == 1990,
      (vz_r.weiter(1995, -10), vz_r.weiter(1975, 10)))
check("weiter 0: das naechste Jahr mit Spielen",
      vz.weiter(1993, 0) == 1994 and vz.weiter(1990, 0) == 1990
      and ZM.Verzeichnis().weiter(1990, 1) == 1990)
check("Jahr bis: 'bis' zaehlt mit", ZM.jahr_zahl("2026", 2026) == 2026
      and ZM.jahr_zahl("2027", 2026) == 0 and ZM.jahr_zahl("1970") == 1970
      and ZM.jahr_zahl("1969") == 0 and ZM.jahr_zahl(None) == 0)
viele = [("SNES", {"folders": {}, "items": [
    spiel("S%d" % i, "SNES") for i in range(ZM.HAPPEN * 2 + 5)]}, "SNES")]
blicke = []
ZM.merker_vergessen()
vz2 = _bauen_echt(viele, meta, None, 2026, lambda n: blicke.append(n))
check("zwischendurch alle HAPPEN gelesenen Spiele",
      blicke == [ZM.HAPPEN, ZM.HAPPEN * 2] and vz2.ohne == ZM.HAPPEN * 2 + 5,
      blicke)
ZM.merker_vergessen()
check("zwischendurch False bricht ab (None)",
      _bauen_echt(viele, meta, None, 2026, lambda n: False) is None)
ZM.merker_vergessen()
kaputt = _bauen_echt(kategorien(), lambda s, l: 1 / 0, lambda p: 1 / 0, 2026)
check("Fehler in den Spieldaten: das Spiel faehrt ohne Jahr",
      not kaputt.jahre and kaputt.ohne == 10, kaputt.ohne)
check("anzahl: genau so viele, wie bauen() aufnimmt",
      ZM.anzahl(kategorien(), mra) == 10 and ZM.anzahl(kategorien()) == 9
      and len(vz.gesehen) == 10, ZM.anzahl(kategorien(), mra))
check("leeres Verzeichnis: kein Bereich, kein Startjahr",
      ZM.Verzeichnis().bereich() is None
      and ZM.Verzeichnis().startjahr() is None)

# ---------------------------------------------------------------------------
print()
print("Test 3b: der Merker")
# ---------------------------------------------------------------------------
STAND = {"SNES": "a", "MEGADRIVE": "a", "ARCADE": "a"}
stand = lambda sk: STAND.get(sk, "")                     # noqa: E731
ZM.merker_vergessen()
try:
    os.remove(ZM.MERKER_DATEI)
except OSError:
    pass
check("offen: alles, solange nichts gemerkt ist",
      ZM.offen(kategorien(), mra, stand) == 10)
del GELESEN[:]
_bauen_echt(kategorien(), meta, mra, 2026, stand_fn=stand)
n1 = len(GELESEN)
check("offen danach: nichts", ZM.offen(kategorien(), mra, stand) == 0)
del GELESEN[:]
vz3 = _bauen_echt(kategorien(), meta, mra, 2026, stand_fn=stand)
check("zweiter Aufbau: nichts gelesen, dasselbe Verzeichnis",
      n1 == 9 and not GELESEN and sorted(vz3.jahre) == sorted(vz.jahre)
      and vz3.ohne == vz.ohne, (n1, len(GELESEN)))
check("Speichern ohne Faden: Datei da, ueber .tmp",
      ZM.merker_speichern(hintergrund=False) is True
      and os.path.exists(ZM.MERKER_DATEI)
      and not os.path.exists(ZM.MERKER_DATEI + ".tmp"))
check("nichts Neues: nicht nochmal geschrieben",
      ZM.merker_speichern() is None)
ZM.merker_vergessen()                    # wie ein Neustart
del GELESEN[:]
vz4 = _bauen_echt(kategorien(), meta, mra, 2026, stand_fn=stand)
check("nach einem Neustart: aus der Datei, nichts gelesen",
      not GELESEN and sorted(vz4.jahre) == sorted(vz.jahre)
      and ZM._merker["geladen"])
STAND["MEGADRIVE"] = "b"
del GELESEN[:]
_bauen_echt(kategorien(), meta, mra, 2026, stand_fn=stand)
check("geaenderte Quelle: NUR dieses System neu gelesen",
      sorted(GELESEN) == [("MEGADRIVE", "Sonic"),
                          ("MEGADRIVE", "Streets of Rage")], GELESEN)
faden = ZM.merker_speichern()
faden.join(10)
import json as _json                                     # noqa: E402
d_ = _json.load(open(ZM.MERKER_DATEI, encoding="utf-8"))
check("im Hintergrund gespeichert, mit Stand und Version",
      not faden.is_alive() and d_["version"] == ZM.MERKER_VERSION
      and d_["stand"]["MEGADRIVE"] == "b"
      and d_["jahre"]["SNES"]["F-Zero"] == 1990
      and d_["jahre"]["SNES"]["Zukunft"] == 2999)
check("gemerkt wird das ROHE Jahr - geprueft wird beim Einsortieren",
      d_["jahre"]["SNES"]["Zu frueh"] == 1965
      and d_["jahre"]["SNES"]["Ohne Jahr"] == 0)
_voll = _json.dumps({"version": 99, "stand": STAND,
                     "jahre": d_["jahre"]})
for inhalt, was in (("{kaputt", "kaputte Datei"),
                    (_voll, "fremde Version (mit passendem Inhalt)"),
                    ('{"version": 1, "stand": {"SNES": 5}, "jahre": '
                     '{"SNES": {"F-Zero": 1990}}}', "falscher Stand")):
    open(ZM.MERKER_DATEI, "w").write(inhalt)
    ZM.merker_vergessen()
    del GELESEN[:]
    try:
        _bauen_echt(kategorien(), meta, mra, 2026, stand_fn=stand)
        ok_ = len(GELESEN) == 9
    except Exception as e_:                              # noqa: BLE001
        ok_ = e_
    check("%s: von vorn, kein Absturz" % was, ok_ is True, ok_)
import fe.art as _A                                      # noqa: E402
import tempfile as _tf                                   # noqa: E402
_meta_alt = _A.META_BASE
_A.META_BASE = _tf.mkdtemp(prefix="zm_meta_")
try:
    s0 = _A.meta_stand("SNES")
    open(os.path.join(_A.META_BASE, "SNES.json"), "w").write("{}")
    s1 = _A.meta_stand("SNES")
    s1b = _A.meta_stand("SNES")
    open(os.path.join(_A.META_BASE, "SNES.json"), "w").write('{"a": 1}')
    s2 = _A.meta_stand("SNES")
    check("meta_stand: gleich bleibt gleich, eine neue oder geaenderte "
          "Tabelle aendert ihn, ein anderes System nicht",
          s0 != s1 and s1 == s1b and s1 != s2
          and _A.meta_stand("NES") == s0.replace("SNES", "NES"),
          (s0, s1, s2))
finally:
    _A.META_BASE = _meta_alt
check("der Merker liegt im Frontend-Ordner, nie in docs/zaparoo",
      ZM.MERKER_DATEI.endswith("zeitmaschine_jahre.json")
      and "/docs" not in open(ZM.__file__, encoding="utf-8").read()
      .split("MERKER_DATEI = ")[1].split("\n")[0])

# ---------------------------------------------------------------------------
print()
print("Test 4: der Knoten fuer ein Jahr - nur dieses Jahr")
# ---------------------------------------------------------------------------
TX = {"alle": "Alle Spiele aus %d", "wertungen": "Deine Wertungen",
      "zurueck": "Zurueck", "anderes": "Anderes"}
SN = {"SNES": "SNES", "MEGADRIVE": "Mega Drive", "ARCADE": "Arcade"}
k = ZM.knoten(vz, 1991, lambda s: SN.get(s, s), TX)
check("oben: Zurueck und Anderes Jahr",
      [(l, kd) for l, kd, _a in k["oben"]]
      == [("Zurueck", "zeitmaschine_zurueck"), ("Anderes", "zeitmaschine")]
      and k["items"] == [])
check("1991: alle Spiele aus 1991 zuerst, nach Name",
      k["folge"] == ["Alle Spiele aus 1991"]
      and [e[0] for e in k["folders"]["Alle Spiele aus 1991"]["items"]]
      == ["Sonic", "Streets of Rage"])
check("1991: nur die Systeme mit Spielen aus 1991",
      sorted(k["folders"]) == ["Alle Spiele aus 1991", "Mega Drive"]
      and [e[0] for e in k["folders"]["Mega Drive"]["items"]]
      == ["Sonic", "Streets of Rage"], sorted(k["folders"]))
check("nichts aus frueheren Jahren (der Nutzerwunsch)",
      "F-Zero" not in str(k) and "Super Mario" not in str(k)
      and "Galaga" not in str(k))
check("nichts aus spaeteren", "Super Metroid" not in str(k)
      and "Chrono" not in str(k))
k95 = ZM.knoten(vz, 1995, lambda s: SN.get(s, s), TX)
check("1995: Chrono Trigger und sonst nichts",
      [e[0] for e in k95["folders"]["SNES"]["items"]] == ["Chrono Trigger"])
k90 = ZM.knoten(vz, 1990, lambda s: SN.get(s, s), TX)
check("1990: im System nach Name",
      [e[0] for e in k90["folders"]["SNES"]["items"]]
      == ["F-Zero", "Super Mario World"])
check("Eintraege tragen ihr echtes arg (startbar)",
      k90["folders"]["SNES"]["items"][0][1:] == (
          "game", ("/f/F-Zero.rom", ".rom", "SNES", None, None)))
check("ein Jahr ohne Spiele: keine Ordner",
      ZM.knoten(vz, 1992, str, TX)["folders"] == {})
kw = ZM.knoten(vz, 1990, lambda s: SN.get(s, s), TX,
               {("SNES", "Super Mario World"): 80, ("SNES", "F-Zero"): 90,
                ("SNES", "Chrono Trigger"): 99, ("SNES", "Fremd"): 99})
check("Deine Wertungen: nur aus diesem Jahr, bester zuerst",
      [e[0] for e in kw["folders"]["Deine Wertungen"]["items"]]
      == ["F-Zero", "Super Mario World"]
      and kw["folge"] == ["Alle Spiele aus 1990", "Deine Wertungen"])
kw81 = ZM.knoten(vz, 1981, lambda s: SN.get(s, s), TX,
                 {("ARCADE", "Galaga"): 88})
check("Arcade-Wertung unter ARCADE",
      [e[0] for e in kw81["folders"]["Deine Wertungen"]["items"]]
      == ["Galaga"])
kw0 = ZM.knoten(vz, 1991, lambda s: SN.get(s, s), TX,
                {("SNES", "Chrono Trigger"): 93})
check("keine Wertung aus dem Jahr: kein Ordner",
      "Deine Wertungen" not in kw0["folders"])
vz_neo = ZM.Verzeichnis()
vz_neo.aufnehmen("NEOGEO", "Metal Slug", "core", "/x/mslug.mra", 1996)
vz_neo.aufnehmen("NEOGEO", "Blazing Star", "game", ("/x/b.neo",), 1996)
kn = ZM.knoten(vz_neo, 1996, str, TX, {("ARCADE", "Metal Slug"): 90,
                                      ("NEOGEO", "Blazing Star"): 80})
check("ein .mra zaehlt mit seiner Arcade-Wertung (wie fe/wertungen)",
      [e[0] for e in kn["folders"]["Deine Wertungen"]["items"]]
      == ["Metal Slug", "Blazing Star"])
vz_g = ZM.Verzeichnis()
for sk_ in ("A", "B"):
    vz_g.aufnehmen(sk_, "X" + sk_, "game", None, 1990)
kd = ZM.knoten(vz_g, 1990, lambda s: "Gleich", TX)
check("gleiche Systemnamen: mit Kuerzel unterschieden",
      sum(1 for n in kd["folders"] if n.startswith("Gleich")) == 2)

# ---------------------------------------------------------------------------
print()
print("Test 5: das Drehrad")
# ---------------------------------------------------------------------------
fe = H.make_frontend(page=0)
fe._zm_vz = vz
fe._zm_veraltet = False
echt_inp = fe.inp


def rad(tasten, start=None):
    fe._zm_jahr = start
    fe.inp = Skript(echt_inp, tasten)
    try:
        return fe._zm_waehlen()
    finally:
        fe.inp = echt_inp


check("Start im Jahr mit den meisten Spielen, A reist", rad(["ok"]) == 1990)
check("rechts: das naechste Jahr mit Spielen",
      rad(["right", "ok"]) == 1991 and rad(["right", "right", "ok"]) == 1994)
check("links zurueck", rad(["right", "right", "left", "ok"]) == 1991)
check("hoch: +10, am Ende das letzte Jahr", rad(["up", "ok"]) == 1995)
check("runter: zum fruehesten", rad(["down", "ok"]) == 1981
      and rad(["down", "down", "left", "ok"]) == 1981)
check("am Rand stehen bleiben", rad(["up", "up", "right", "ok"]) == 1995)
check("B bricht ab", rad(["right", "back"]) is None)
check("das letzte Reisejahr ist der Start", rad(["ok"], 1994) == 1994)
check("ein leeres letztes Reisejahr: das naechste mit Spielen",
      rad(["ok"], 1993) == 1994 and rad(["ok"], 1970) == 1981)
check("klemmende Eingabe (nur leere Antworten): das Rad gibt auf",
      rad([]) is None)

# ---------------------------------------------------------------------------
print()
print("Test 6: die Reise im Frontend")
# ---------------------------------------------------------------------------
WT.an_setzen(True)
WT.speichern("MEGADRIVE", "Sonic", {"spass": 82})
ZM.merker_vergessen()
try:
    os.remove(ZM.MERKER_DATEI)
except OSError:
    pass


def reise_frontend():
    f_ = H.make_frontend(page=0)
    f_.cats = kategorien() + [(f_._zm_name(), f_._zm_knoten(), None)]
    f_._hauptseite_anwenden()
    f_.cat_i = f_._zm_index()
    f_.page = 1
    f_.nav_path = []
    f_.item_i = 0
    f_._zm_effekt = lambda von, nach: None
    return f_


schirme = []
fe = reise_frontend()
_schirm_echt = fe._zm_schirm
fe._zm_schirm = lambda z, h: schirme.append(z) or _schirm_echt(z, h)
del GELESEN[:]
del gebaut[:]
fe.inp = Skript(echt_inp, ["right", "ok"])
fe._zm_reisen()
fe.inp = echt_inp
name = fe.cats[fe._zm_index()][0]
check("Reise nach 1991: der Name traegt das Jahr",
      name == fm.t("zm_cat") + " \xb7 1991" and fe._zm_jahr == 1991, name)
check("erste Reise: gelesen (mit Fortschritt) und gemerkt",
      len(GELESEN) == 9 and schirme and gebaut == [1])
_t0 = __import__("time").time()
while ZM._schreiber[0] is not None and ZM._schreiber[0].is_alive() \
        and __import__("time").time() - _t0 < 10:
    __import__("time").sleep(0.02)
check("... und auf die Karte geschrieben", os.path.exists(ZM.MERKER_DATEI))
check("das Kuerzel bleibt (ausblenden/ordnen gilt weiter)",
      HS.schluessel(name) == "zm_cat" == HS.schluessel(fm.t("zm_cat"))
      and HS.schluessel("Zeitmaschine \xb7 1991") == "zm_cat"
      and HS.schluessel("Time machine \xb7 1991") == "zm_cat"
      and HS.schluessel("SNES \xb7 1991") != "zm_cat"
      and HS.schluessel(fm.t("zm_cat") + " \xb7 19x1") != "zm_cat")
import fe.art as _ART                                    # noqa: E402
check("Abzeichen: Zeitmaschine (mit und ohne Jahr) und Testarchiv",
      _ART._category_art_key(name, None) == "ZEITMASCHINE"
      and _ART._category_art_key("Zeitmaschine", None) == "ZEITMASCHINE"
      and _ART._category_art_key("Time machine \xb7 1985", None)
      == "ZEITMASCHINE"
      and _ART._category_art_key("Testarchiv", None) == "TESTARCHIV"
      and _ART._category_art_key("Test archive", None) == "TESTARCHIV"
      and _ART._category_art_key("Zeitmaschinen-Fan", None) is None
      and os.path.exists(os.path.join(os.path.dirname(H.FRONTEND_PY),
                                      "sysart", "ZEITMASCHINE.art"))
      and os.path.exists(os.path.join(os.path.dirname(H.FRONTEND_PY),
                                      "sysart", "TESTARCHIV.art")))
check("man steht in der Zeitmaschine, oben", fe.page == 1
      and fe.cat_i == fe._zm_index() and fe.item_i == 0 and not fe.nav_path)
liste = [(l, kd) for l, kd, _a in fe._display_items()]
check("die Liste: Zurueck, Anderes Jahr, Alle aus 1991, Wertungen, System",
      liste == [(fm.t("zm_zurueck"), "zeitmaschine_zurueck"),
                (fm.t("zm_anderes"), "zeitmaschine"),
                (fm.t("zm_alle") % 1991 + "/", "folder"),
                (fm.t("zm_wertungen") + "/", "folder"),
                ("Mega Drive/", "folder")], liste)
# Anderes Jahr: kein zweiter Aufbau
fe._kategorie_position = {fe._zm_index(): (3, 0), 0: (2, 0)}
del gebaut[:]
del GELESEN[:]
fe.inp = Skript(echt_inp, ["left", "ok"])
fe._zm_reisen()
fe.inp = echt_inp
check("anderes Jahr: nichts gelesen, nichts neu gebaut",
      not gebaut and not GELESEN and fe._zm_jahr == 1990)
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
fe._zm_jahr = 1990
fe._zm_ersetzen()
fe.cat_i = 0
fe.page = 1
fe.nav_path = []
fe._go_back_or_confirm_quit()
check("B in einer anderen Kategorie: die Reise bleibt", fe._zm_jahr == 1990)
fe.cat_i = fe._zm_index()
fe.page = 1
fe.nav_path = []
check("der Punkt 'Zurueck in die Gegenwart'",
      fe._zm_gegenwart() is True and fe.page == 0 and fe._zm_jahr is None
      and fe.cat_i == fe._zm_index())
check("zweimal Gegenwart: nichts passiert", fe._zm_gegenwart() is False)
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
vz_vorher = fe._zm_vz
fe.build_categories()
check("Neuaufbau (z.B. RetroAchievements): die Reise bleibt, das "
      "Verzeichnis gilt als veraltet",
      fe._zm_jahr == 1990 and fe._zm_vz is vz_vorher
      and fe._zm_veraltet is True)
fe.cats = kategorien() + fe.cats
fe._zm_sync_kategorie()
fe.cat_i = fe._zm_index()
check("... und die Kategorie traegt weiter das Jahr",
      fe.cats[fe.cat_i][0].endswith("1990"))
del gebaut[:]
del GELESEN[:]
del schirme[:]
fe.page = 1
fe.inp = Skript(echt_inp, ["right", "ok"])
fe._zm_reisen()
fe.inp = echt_inp
check("naechste Jahreswahl danach: aus dem Merker, nichts gelesen, kein "
      "Fortschritt", gebaut == [1] and not GELESEN and not schirme
      and fe._zm_jahr == 1991 and fe._zm_veraltet is False)
fe.build_categories(force_rescan=True)
check("Neu-Einlesen: Verzeichnis verworfen, Reise beendet",
      fe._zm_vz is None and fe._zm_jahr is None)
# Ein Neustart: neue Instanz, Merker frisch von der Karte.
ZM.merker_vergessen()
fe = reise_frontend()
del GELESEN[:]
schirme2 = []
_schirm2 = fe._zm_schirm
fe._zm_schirm = lambda z, h: schirme2.append(z) or _schirm2(z, h)
fe.inp = Skript(echt_inp, ["ok"])
fe._zm_reisen()
fe.inp = echt_inp
check("nach einem Neustart: NICHTS neu gelesen (Nutzermeldung)",
      not GELESEN and fe._zm_jahr == 1990
      and schirme2 == [[fm.t("zm_vorbereiten")]], (len(GELESEN), schirme2))
WT.an_setzen(False)

# ---------------------------------------------------------------------------
print()
print("Test 7: Vorbereitung mit B abgebrochen")
# ---------------------------------------------------------------------------
ZM.merker_vergessen()
try:
    os.remove(ZM.MERKER_DATEI)
except OSError:
    pass
fe = H.make_frontend(page=0)
fe.cats = viele + [(fe._zm_name(), fe._zm_knoten(), None)]
fe._hauptseite_anwenden()
fe.cat_i = fe._zm_index()
fe.page = 1
vorher = list(fe.cats)
del GELESEN[:]
fe.inp = Skript(echt_inp, ["back", "ok"])
fe._zm_reisen()
fe.inp = echt_inp
check("abgebrochen: kein Verzeichnis, keine Reise, alles wie vorher",
      getattr(fe, "_zm_vz", None) is None and fe._zm_jahr is None
      and fe.cats == vorher and fe.page == 1)
check("das bis dahin Gelesene bleibt gemerkt",
      len(GELESEN) == ZM.HAPPEN
      and ZM.offen(viele, None, fm.meta_stand) == 5 + ZM.HAPPEN,
      (len(GELESEN), ZM.offen(viele, None, fm.meta_stand)))

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
        fe._zm_schirm([fm.t("zm_vorbereiten")], "")
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
