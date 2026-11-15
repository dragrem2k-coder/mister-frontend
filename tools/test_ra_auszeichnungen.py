#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RetroAchievements: Auszeichnungen, Sitzungsbilanz, Profil (Build 327).

NUTZERWUNSCH: "1, 2 und 5 machen" - aus den Vorschlaegen zu Build 326:
  1. Mastered/Beaten-Kennzeichen in der Liste und am Cover
  2. Bilanz nach dem Spiel ("+3 Erfolge, +25 Punkte, jetzt 18/40")
  5. RA-Profil: Punkte, Rang, zuletzt freigeschaltete Erfolge

Dazu ein Fund beim Bauen: die Fortschrittsabfrage lieferte ohne
Seitenangabe nur die ersten 100 Spiele.

GEPRUEFT WIRD (ohne Netz - die Antworten des Servers sind nachgestellt):
  1. Fortschritt ueber mehrere Seiten; Auszeichnungen aus HighestAwardKind
     und aus den Zahlen; ein Fehler auf Seite 2 behaelt Seite 1; ein
     leerer Abruf loescht keine bekannten Auszeichnungen.
  2. Die Liste: "M " / "B " vor dem Namen, an der echten draw_list_row();
     die Laufschrift rechnet mit demselben Vorzeichen. GEGENPROBE: ohne
     Auszeichnung kein Vorzeichen; neuer Stand -> neuer Merker.
  3. Das Abzeichen auf dem Cover und die Infozeile.
  4. Die Sitzungsbilanz: neu per Vergleich, per Datum, ohne beides
     nichts; Auswertung zieht Fortschritt und Auszeichnung nach; der
     Bildschirm kommt NUR bei neuen Erfolgen; der Spielstart reicht
     ra=True nur beim RA-Core durch.
  5. Das Profil: Antwort lesen, Bildschirm mit und ohne Verbindung,
     Zaehlung der Sammlung, Menuepunkt.

Ausfuehren:
    python3 tools/test_ra_auszeichnungen.py
"""
import io
import json
import os
import sys

_HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HIER)

import _harness as H                                     # noqa: E402

fm = H.fm
import fe.retroachievements as RA                        # noqa: E402
import fe.menu as M                                      # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


print(__doc__.strip().split("\n")[0])
print()


# ---------------------------------------------------------------------------
# Nachgestellter Server
# ---------------------------------------------------------------------------
class Antwort(object):
    def __init__(self, daten, status=200):
        self.status = status
        self._roh = json.dumps(daten).encode("utf-8")

    def read(self):
        return self._roh

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def eintrag(i, kind=None, max_=10, aw=3, awhc=0):
    return {"GameID": 1000 + i, "Title": "Spiel %d" % i,
            "ConsoleName": "SNES/Super Famicom", "MaxPossible": max_,
            "NumAwarded": aw, "NumAwardedHardcore": awhc,
            "HighestAwardKind": kind}


ALLE = [eintrag(i) for i in range(1100)]
ALLE[5] = eintrag(5, "mastered", 10, 10, 10)
ALLE[600] = eintrag(600, "beaten-softcore", 20, 7, 0)
ALLE[1050] = eintrag(1050, None, 8, 8, 8)       # ohne Feld, alles hardcore
ALLE[1051] = eintrag(1051, None, 8, 8, 2)       # ohne Feld, alles softcore
abrufe = []


def server(fehler_ab_seite=None):
    def _urlopen(req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else req
        q = dict(p.split("=", 1) for p in url.split("?", 1)[1].split("&"))
        c, o = int(q.get("c", 100)), int(q.get("o", 0))
        abrufe.append((c, o))
        if fehler_ab_seite is not None and len(abrufe) >= fehler_ab_seite:
            raise OSError("Netz weg")
        return Antwort({"Count": min(c, len(ALLE) - o), "Total": len(ALLE),
                        "Results": ALLE[o:o + c]})
    return _urlopen


_echt_urlopen = RA.urllib.request.urlopen
try:
    # -----------------------------------------------------------------------
    print("Test 1: Fortschritt ueber alle Seiten, Auszeichnungen")
    # -----------------------------------------------------------------------
    RA.urllib.request.urlopen = server()
    del abrufe[:]
    RA.RA_AUSZEICHNUNGEN.clear()
    out = RA.fetch_ra_progress("nutzer", "schluessel")
    check("alle 1100 Spiele (vorher nur die ersten 100)",
          out is not None and len(out) == 1100, len(out or ()))
    check("in drei Abrufen zu je hoechstens 500", abrufe ==
          [(500, 0), (500, 500), (500, 1000)], abrufe)
    check("mastered aus dem Feld", RA.RA_AUSZEICHNUNGEN.get(1005)
          == "mastered")
    check("beaten auf Seite 2", RA.RA_AUSZEICHNUNGEN.get(1600)
          == "beaten-softcore")
    check("ohne Feld, alles hardcore -> mastered",
          RA.RA_AUSZEICHNUNGEN.get(2050) == "mastered")
    check("ohne Feld, alles softcore -> completed",
          RA.RA_AUSZEICHNUNGEN.get(2051) == "completed")
    check("ohne Auszeichnung kein Eintrag", 1001 not in RA.RA_AUSZEICHNUNGEN)
    stand = RA.RA_AUSZEICHNUNGEN_STAND[0]
    RA.urllib.request.urlopen = server(fehler_ab_seite=2)
    del abrufe[:]
    out2 = RA.fetch_ra_progress("nutzer", "schluessel")
    check("Fehler auf Seite 2: Seite 1 bleibt", out2 is not None
          and len(out2) == 500, len(out2 or ()))
    RA.urllib.request.urlopen = server(fehler_ab_seite=1)
    RA.RA_AUSZEICHNUNGEN[4242] = "mastered"
    check("Fehler gleich am Anfang: None",
          RA.fetch_ra_progress("nutzer", "schluessel") is None)
    check("und die bekannten Auszeichnungen bleiben",
          RA.RA_AUSZEICHNUNGEN.get(4242) == "mastered")
    check("jede neue Liste zaehlt den Stand hoch",
          RA.RA_AUSZEICHNUNGEN_STAND[0] > stand)
finally:
    RA.urllib.request.urlopen = _echt_urlopen

# ---------------------------------------------------------------------------
print()
print("Test 2: die Liste - M / B vor dem Namen")
# ---------------------------------------------------------------------------
H.set_screen(1920, 1080)
titel = ["Gemeistertes Spiel (USA)", "Beendetes Spiel (USA)",
         "Angefangenes Spiel (USA)", "Fremdes Spiel (USA)"]
f = H.make_frontend(page=1, titles=titel)
eintraege = [(titel[0], "SNES/Super Famicom", 10, 10, 77),
             (titel[1], "SNES/Super Famicom", 7, 20, 78),
             (titel[2], "SNES/Super Famicom", 3, 20, 79)]
f._ra_lookup = RA.build_ra_lookup(eintraege)
RA.RA_AUSZEICHNUNGEN.clear()
RA.RA_AUSZEICHNUNGEN.update({77: "mastered", 78: "beaten-hardcore"})
RA.RA_AUSZEICHNUNGEN_STAND[0] += 1
f._favorites_set = set()
f._completed_set = set()
check("gemeistert: M", f._zeilen_praefix(titel[0], "game", "SNES") == "M ",
      repr(f._zeilen_praefix(titel[0], "game", "SNES")))
check("beendet: B", f._zeilen_praefix(titel[1], "game", "SNES") == "B ")
check("GEGENPROBE angefangen: nichts",
      f._zeilen_praefix(titel[2], "game", "SNES") == "")
check("GEGENPROBE ohne RA-Eintrag: nichts",
      f._zeilen_praefix(titel[3], "game", "SNES") == "")
check("Ordner: nie", f._zeilen_praefix(titel[0], "folder", "SNES") == "")
f._favorites_set = {titel[0]}
check("Favorit und gemeistert: * M",
      f._zeilen_praefix(titel[0], "game", "SNES") == "* M ")
f._favorites_set = set()
# Am echten Zeichenweg: was steht in der Zeile?
f._force_full_redraw = True
f.draw()
gezeichnet = []
_echt_text = f.fb.text


def _text(x, y, txt, *a, **k):
    gezeichnet.append(txt)
    return _echt_text(x, y, txt, *a, **k)


f.fb.text = _text
f.item_i = 2
f.draw_list_row(0)
f.draw_list_row(1)
f.fb.text = _echt_text
check("draw_list_row schreibt M vor den Namen",
      any(g.startswith("M Gemeistertes") for g in gezeichnet), gezeichnet[:3])
check("und B vor den beendeten",
      any(g.startswith("B Beendetes") for g in gezeichnet), gezeichnet[:3])
# Laufschrift: dieselbe Laenge
v = f.view
s_ = v["s"]
maxc = (v["list_right"] - v["list_x"] - 8 * s_) // (8 * s_)
lang = "Gemeistertes Spiel mit sehr langem Namen " + "x" * (maxc - 41)
lang = lang[:maxc - 1]                    # passt ohne Vorzeichen genau
f.cats[0][1]["items"] = [(lang, "game", ("/f/0.sfc", ".sfc", "SNES",
                                         None, None))]
f.cats[0][1].pop("_display_items_cache", None)
f._ra_lookup = RA.build_ra_lookup([(lang, "SNES/Super Famicom", 10, 10, 77)])
f.item_i = 0
f.draw()
check("Laufschrift: mit Vorzeichen reicht der Platz nicht mehr",
      f.marquee_needed() is True,
      "%d Zeichen, Platz %d" % (len(lang), maxc))
RA.RA_AUSZEICHNUNGEN.clear()
RA.RA_AUSZEICHNUNGEN_STAND[0] += 1
f._ra_lookup = RA.build_ra_lookup([(lang, "SNES/Super Famicom", 3, 10, 77)])
check("GEGENPROBE: ohne Auszeichnung passt er (neuer Stand, neuer Merker)",
      f.marquee_needed() is False)

# ---------------------------------------------------------------------------
print()
print("Test 3: Abzeichen auf dem Cover und Infozeile")
# ---------------------------------------------------------------------------
f._ra_lookup = RA.build_ra_lookup(eintraege)
RA.RA_AUSZEICHNUNGEN.clear()
RA.RA_AUSZEICHNUNGEN.update({77: "mastered", 78: "beaten-hardcore",
                             79: "completed"})
RA.RA_AUSZEICHNUNGEN_STAND[0] += 1
spiel = lambda n: (n, "game", ("/f/x.sfc", ".sfc", "SNES", None, None))
check("mastered: MEISTER in Gold",
      f._ra_abzeichen(spiel(titel[0]), "SNES", (10, 10))
      == (fm.t("ra_badge_mastered"), f.RA_GOLD))
check("beaten: BEENDET in Silber",
      f._ra_abzeichen(spiel(titel[1]), "SNES", (7, 20))
      == (fm.t("ra_badge_beaten"), f.RA_SILBER))
check("completed: 100%",
      f._ra_abzeichen(spiel(titel[2]), "SNES", (20, 20))[0] == "100%")
check("GEGENPROBE: nichts bei einem angefangenen ohne Auszeichnung",
      f._ra_abzeichen(spiel(titel[3]), "SNES", (3, 20)) is None)
zeilen, _ra = f._spiel_infozeilen(spiel(titel[0]), "SNES", 80)
check("Infozeile: 'RA: 10/10 - gemeistert'",
      any(fm.t("ra_award_mastered") in z and "10/10" in z for z in zeilen),
      zeilen)

# ---------------------------------------------------------------------------
print()
print("Test 4: die Sitzungsbilanz")
# ---------------------------------------------------------------------------
def ach(name, frei, datum=None, punkte=5, hc=True):
    return (name, "", punkte, None, frei, datum, hc)


liste = [ach("Alt", True, "2026-11-14 20:00:00"),
         ach("Neu A", True, "2026-11-15 18:01:00", 10),
         ach("Neu B", True, "2026-11-15 18:30:00", 25),
         ach("Offen", False)]
neu = RA.ra_sitzung_neu({"Alt"}, liste)
check("per Vergleich: genau die zwei neuen",
      [a[0] for a in neu] == ["Neu A", "Neu B"], [a[0] for a in neu])
neu = RA.ra_sitzung_neu(None, liste, "2026-11-15 18:00:00")
check("per Datum (Abruf beim Start fehlgeschlagen): dieselben zwei",
      [a[0] for a in neu] == ["Neu A", "Neu B"])
check("ohne beides: lieber nichts als Falsches",
      RA.ra_sitzung_neu(None, liste, None) == [])

f._ra_lookup = RA.build_ra_lookup(
    [("Bilanzspiel", "SNES/Super Famicom", 1, 4, 555)])
RA.RA_AUSZEICHNUNGEN.clear()
bilanz = {"game_id": 555, "vorher": {"Alt"}, "start_utc": None}
erg = f._ra_bilanz_auswerten(bilanz, liste)
check("Auswertung: 2 neu, 35 Punkte, Stand 3/4",
      (len(erg["neu"]), erg["punkte"], erg["erreicht"], erg["gesamt"])
      == (2, 35, 3, 4), erg)
check("der Fortschritt in der Tabelle ist nachgezogen",
      RA.lookup_ra_progress(f._ra_lookup, "Bilanzspiel", "SNES") == (3, 4))
voll = [ach("Alt", True, hc=True), ach("Neu A", True, hc=True)]
erg = f._ra_bilanz_auswerten({"game_id": 555, "vorher": {"Alt"},
                              "start_utc": None}, voll)
check("alles im Hardcore-Modus: gemeistert, und es steht in den "
      "Auszeichnungen", erg["gemeistert"] == "mastered"
      and RA.RA_AUSZEICHNUNGEN.get(555) == "mastered", erg)
weich = [ach("Alt", True, hc=False), ach("Neu A", True, hc=True)]
RA.RA_AUSZEICHNUNGEN.clear()
erg = f._ra_bilanz_auswerten({"game_id": 555, "vorher": {"Alt"},
                              "start_utc": None}, weich)
check("teils Softcore: abgeschlossen", erg["gemeistert"] == "completed")

# Der Bildschirm nur bei neuen Erfolgen
import threading                                         # noqa: E402
gezeigt = []
f.ra_bilanz_bildschirm = lambda label, erg: gezeigt.append(erg)
_echt_fetch = fm.fetch_ra_game_achievements_bounded
try:
    fm.fetch_ra_game_achievements_bounded = lambda gid, timeout=5.0: liste
    b = {"game_id": 555, "vorher": {"Alt", "Neu A", "Neu B"},
         "start_utc": None, "fertig": threading.Event()}
    b["fertig"].set()
    check("ohne neue Erfolge: kein Bildschirm",
          f._ra_bilanz_zeigen(b, "Bilanzspiel") is False and not gezeigt)
    b["vorher"] = {"Alt"}
    check("mit neuen: Bildschirm", f._ra_bilanz_zeigen(b, "Bilanzspiel")
          is True and len(gezeigt) == 1)
    fm.fetch_ra_game_achievements_bounded = lambda gid, timeout=5.0: None
    check("Abruf scheitert: kein Bildschirm, kein Absturz",
          f._ra_bilanz_zeigen(b, "Bilanzspiel") is False)
finally:
    fm.fetch_ra_game_achievements_bounded = _echt_fetch
del f.ra_bilanz_bildschirm
# Der echte Bildschirm zeichnet ohne Fehler und zeigt die Zahlen
texte = []


def _text2(x, y, txt, *a, **k):
    texte.append(txt)
    return _echt_text(x, y, txt, *a, **k)


f.fb.text = _text2
f.inp.read_action = lambda timeout=None: None
f.ra_bilanz_bildschirm("Bilanzspiel", {"neu": liste[1:3], "punkte": 35,
                                       "erreicht": 3, "gesamt": 4,
                                       "gemeistert": None})
f.fb.text = _echt_text
check("Bildschirm: '+2 Erfolge  +35 Punkte'",
      fm.t("ra_bilanz_neu", 2, 35) in texte, texte[:4])
check("Bildschirm: die neuen Erfolge mit Punkten",
      "+ Neu A (10)" in texte and "+ Neu B (25)" in texte)
q = open(H.FRONTEND_PY, encoding="utf-8").read()
rc = H.nur_code(H.koerper(q, "run_core"))
check("run_core holt die Bilanz nur mit ra=True",
      "self._ra_bilanz_beginnen(label, syskey) if ra else None" in rc)
check("der Spielstart erkennt den RA-Core am Setnamen",
      "_ist_ra = bool(setname)" in q and '.startswith("RA_")' in q
      and "ra=_ist_ra)" in q)

# ---------------------------------------------------------------------------
print()
print("Test 5: das Profil")
# ---------------------------------------------------------------------------
antwort = {"TotalPoints": 4321, "TotalSoftcorePoints": 120,
           "TotalTruePoints": 9876, "Rank": 15000, "TotalRanked": 80000,
           "MemberSince": "2019-04-01 10:00:00", "Motto": "Hallo",
           "RecentAchievements": {
               "10": {"1": {"Title": "Erster", "GameTitle": "Spiel A",
                            "Points": 5, "DateAwarded": "2026-11-10 10:00:00",
                            "HardcoreAchieved": 1}},
               "11": {"2": {"Title": "Zweiter", "GameTitle": "Spiel B",
                            "Points": 10, "DateAwarded": "2026-11-12 10:00:00",
                            "HardcoreAchieved": 0}}}}
p = RA.ra_profil_lesen(antwort)
check("Punkte, Rang, seit", (p["punkte"], p["rang"], p["gewertet"], p["seit"])
      == (4321, 15000, 80000, "2019-04-01"), p)
check("letzte Erfolge, neueste zuerst",
      [e["titel"] for e in p["letzte"]] == ["Zweiter", "Erster"])
check("Hardcore erkannt", [e["hardcore"] for e in p["letzte"]]
      == [False, True])
check("eine kaputte Antwort: leere Felder statt Absturz",
      RA.ra_profil_lesen({"TotalPoints": "x", "RecentAchievements": 5})
      ["punkte"] is None)
f._ra_lookup = RA.build_ra_lookup(eintraege)
RA.RA_AUSZEICHNUNGEN.clear()
RA.RA_AUSZEICHNUNGEN.update({77: "mastered", 78: "beaten-hardcore"})
check("Sammlung: 1 gemeistert, 0 abgeschlossen, 1 beendet, 1 angefangen",
      f.ra_profil_zaehlen() == (1, 0, 1, 1), f.ra_profil_zaehlen())
texte = []
f.fb.text = _text2
f.ra_profil_bildschirm(profil=p)
check("Bildschirm: Punkte", fm.t("ra_profil_punkte", 4321) in texte)
check("Bildschirm: Rang", fm.t("ra_profil_rang_von", 15000, 80000) in texte)
check("Bildschirm: Sammlung",
      fm.t("ra_profil_sammlung", 1, 0, 1, 1) in texte)
texte = []
f.ra_profil_bildschirm(profil=None, abrufen=False)
f.fb.text = _echt_text
check("ohne Verbindung: Hinweis und trotzdem die Sammlung",
      any(fm.t("ra_profil_offline")[:30] in z for z in texte)
      and fm.t("ra_profil_sammlung", 1, 0, 1, 1) in texte)
_echt_cfg, _echt_an = M.load_ra_config, M.ra_toggle_enabled
try:
    M.load_ra_config = lambda: ("nutzer", "schluessel")
    M.ra_toggle_enabled = lambda: True

    def kinds():
        offen, raus = [M.system_items()], []
        while offen:
            k = offen.pop()
            raus.extend(e[1] for e in k.get("items", ()) if len(e) > 1)
            offen.extend(k.get("folders", {}).values())
        return raus
    check("Menuepunkt da, wenn eingerichtet", "ra_profil" in kinds())
    M.ra_toggle_enabled = lambda: False
    check("GEGENPROBE: nicht bei abgeschaltetem RA",
          "ra_profil" not in kinds())
    M.load_ra_config = lambda: (None, None)
    check("GEGENPROBE: nicht ohne Zugangsdaten", "ra_profil" not in kinds())
finally:
    M.load_ra_config, M.ra_toggle_enabled = _echt_cfg, _echt_an
    RA.RA_AUSZEICHNUNGEN.clear()

print()
if fails:
    print("ROT: %d Pruefung(en) fehlgeschlagen:" % len(fails))
    for f_ in fails:
        print("   - " + f_)
    sys.exit(1)
print("ALLES GRUEN")
