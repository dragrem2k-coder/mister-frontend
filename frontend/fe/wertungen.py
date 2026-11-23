#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Eigene Wertungen im Heft-Stil (Build 346).

NUTZERWUNSCH: "Eigenes Bewertungssystem ... wenn man ein Spiel
verlaesst und wieder ins Frontend wechselt ... mit Liste je System" -
in der Variante "wie frueher im Heft": Spielspass als Hauptzahl in
Prozent, dazu Grafik, Sound und Co. je nach Geraet, ein Stempel ab
85 %, ein Testarchiv je System. Und ausdruecklich: "Das ganze muss
aber an und abschaltbar sein".

WAS HIER STEHT, und was nicht. Hier stehen die Daten, die Schalter und
die Regeln (Kategorien je Geraet, Stempel, Vorschlag). Gezeichnet wird
in frontend.py - wie bei den Favoriten (fe/game_state.py).

DIE SCHALTER. Alle sind Flag-Dateien unter /media/fat/frontend, wie
die anderen Schalter auch. Der Hauptschalter ist AUS, solange die
Datei fehlt: wer ein Update einspielt, sieht nichts Neues, bis er es
selbst einschaltet. Bei AUS wird die Wertungsdatei nicht einmal
gelesen - jede Abfrage aus der Liste fragt zuerst an().

DIE DATEI. /media/fat/frontend/bewertungen.json, ein Eintrag je Spiel,
Schluessel "<System>|<Name>" - derselbe Name, an dem Favoriten und
Spielzeit ein Spiel erkennen, dazu das System, damit "Sonic" auf Mega
Drive und Master System zwei Spiele bleiben. Geschrieben wird ueber
eine .tmp-Datei und os.replace(): ein Stromausfall mitten im Schreiben
laesst die alte Datei stehen. Ist die Datei kaputt, wird sie vor dem
naechsten Schreiben als .kaputt beiseitegelegt statt ueberschrieben.

GELESEN WIRD EINMAL. Die Liste fragt je Zeile nach der Wertung; eine
Datei je Zeile waere auf der SD-Karte zu langsam. Der Merker gilt, bis
diese Stelle selbst schreibt - niemand sonst schreibt die Datei.
"""
import json
import os
import time

DATEI = "/media/fat/frontend/bewertungen.json"
ORDNER = "/media/fat/frontend"
AN_FLAG = os.path.join(ORDNER, "wertungen_an")
FRAGEN_AUS_FLAG = os.path.join(ORDNER, "wertung_fragen_aus")
FRAGEN_AB_FILE = os.path.join(ORDNER, "wertung_fragen_ab")
LISTE_AUS_FLAG = os.path.join(ORDNER, "wertung_liste_aus")
NUR_SPASS_FLAG = os.path.join(ORDNER, "wertung_nur_spielspass")
STEMPEL_AUS_FLAG = os.path.join(ORDNER, "wertung_stempel_aus")
# Build 347: Zweitmeinung (Vorgabe AUS) und Monatsheft (Vorgabe AN).
ZWEIT_AN_FLAG = os.path.join(ORDNER, "wertung_zweitmeinung")
HEFT_AUS_FLAG = os.path.join(ORDNER, "wertung_heft_aus")
CSV_DATEI = os.path.join(ORDNER, "bewertungen.csv")

VERSION = 1
FRAGEN_AB_STUFEN = (5, 10, 20)       # Minuten Spielzeit
FRAGEN_AB_STD = 5
SCHRITT = 5                          # Prozent je Tastendruck
LEISTE_SEKUNDEN = 6.0                # so lange steht die Rueckkehr-Leiste

HIT_AB = 85
KLASSIKER_AB = 90
KLASSIKER_STUNDEN = 10
GURKE_UNTER = 30

# Was je Geraet bewertet wird - Spielspass gibt es immer und ist kein
# Durchschnitt der anderen, sondern das eigene Gesamturteil.
KATEGORIEN = {
    "konsole": ("grafik", "sound", "steuerung"),
    "computer": ("grafik", "musik", "effekte"),
    "automat": ("grafik", "sound", "credit"),
}
ALLE_PROZENTE = ("spass", "grafik", "sound", "musik", "effekte",
                 "steuerung", "credit")
SCHWIERIGKEITEN = ("leicht", "mittel", "knackig", "unfair")
SPIELER = ("1", "1-2", "2")
# Build 347: das Kurzfazit - ein Satz aus einer festen Liste, mit dem
# Pad waehlbar, ohne Tastatur. Gilt auch fuer die Zweitmeinung.
FAZITE = ("pflicht", "fans", "zu_zweit", "gut_gealtert", "nostalgie",
          "zu_schwer", "finger_weg")
CHARTS = 5
ARCADE = "ARCADE"


# ======================================================================
# SCHALTER
# ======================================================================
_schalter = {}


def _flag(pfad):
    if pfad not in _schalter:
        _schalter[pfad] = os.path.exists(pfad)
    return _schalter[pfad]


def _flag_setzen(pfad, anlegen):
    try:
        if anlegen:
            os.makedirs(os.path.dirname(pfad), exist_ok=True)
            open(pfad, "w").close()
        elif os.path.exists(pfad):
            os.remove(pfad)
    except OSError:
        pass
    _schalter.pop(pfad, None)


def schalter_neu_lesen():
    """Fuer Tests und nach einer Einrichtung von aussen."""
    _schalter.clear()


def an():
    return _flag(AN_FLAG)


def an_setzen(wert):
    _flag_setzen(AN_FLAG, bool(wert))
    return an()


def toggle_an():
    return an_setzen(not an())


def fragen():
    return an() and not _flag(FRAGEN_AUS_FLAG)


def toggle_fragen():
    _flag_setzen(FRAGEN_AUS_FLAG, not _flag(FRAGEN_AUS_FLAG))
    return not _flag(FRAGEN_AUS_FLAG)


def fragen_ab_minuten():
    if "fragen_ab" not in _schalter:
        wert = FRAGEN_AB_STD
        try:
            with open(FRAGEN_AB_FILE) as f:
                zahl = int(f.read().strip())
            if zahl in FRAGEN_AB_STUFEN:
                wert = zahl
        except (OSError, ValueError):
            pass
        _schalter["fragen_ab"] = wert
    return _schalter["fragen_ab"]


def cycle_fragen_ab():
    jetzt = fragen_ab_minuten()
    i = FRAGEN_AB_STUFEN.index(jetzt) if jetzt in FRAGEN_AB_STUFEN else 0
    neu = FRAGEN_AB_STUFEN[(i + 1) % len(FRAGEN_AB_STUFEN)]
    try:
        os.makedirs(os.path.dirname(FRAGEN_AB_FILE), exist_ok=True)
        with open(FRAGEN_AB_FILE, "w") as f:
            f.write(str(neu))
    except OSError:
        pass
    _schalter.pop("fragen_ab", None)
    return fragen_ab_minuten()


def in_listen():
    return an() and not _flag(LISTE_AUS_FLAG)


def toggle_in_listen():
    _flag_setzen(LISTE_AUS_FLAG, not _flag(LISTE_AUS_FLAG))
    return not _flag(LISTE_AUS_FLAG)


def nur_spielspass():
    return _flag(NUR_SPASS_FLAG)


def toggle_nur_spielspass():
    _flag_setzen(NUR_SPASS_FLAG, not _flag(NUR_SPASS_FLAG))
    return _flag(NUR_SPASS_FLAG)


def stempel_an():
    return an() and not _flag(STEMPEL_AUS_FLAG)


def zweitmeinung_an():
    return an() and _flag(ZWEIT_AN_FLAG)


def toggle_zweitmeinung():
    _flag_setzen(ZWEIT_AN_FLAG, not _flag(ZWEIT_AN_FLAG))
    return _flag(ZWEIT_AN_FLAG)


def heft_an():
    return an() and not _flag(HEFT_AUS_FLAG)


def toggle_heft():
    _flag_setzen(HEFT_AUS_FLAG, not _flag(HEFT_AUS_FLAG))
    return not _flag(HEFT_AUS_FLAG)


def toggle_stempel():
    _flag_setzen(STEMPEL_AUS_FLAG, not _flag(STEMPEL_AUS_FLAG))
    return not _flag(STEMPEL_AUS_FLAG)


# ======================================================================
# GERAETE UND REGELN
# ======================================================================
_computer = None


def _computer_syskeys():
    global _computer
    if _computer is None:
        try:
            from fe.systems import GAME_SYSTEMS, OPTIONAL_GAME_SYSTEMS
            _computer = frozenset(
                e[1] for e in list(GAME_SYSTEMS) + list(OPTIONAL_GAME_SYSTEMS)
                if str(e[3]).startswith("_Computer"))
        except Exception:                                # noqa: BLE001
            _computer = frozenset(("C64", "AMIGA", "AMSTRAD", "AO486"))
    return _computer


def geraet(syskey):
    """'konsole', 'computer' oder 'automat'."""
    if syskey == ARCADE:
        return "automat"
    if syskey in _computer_syskeys():
        return "computer"
    return "konsole"


def kategorien(syskey, nur_spass=None):
    """Die Prozent-Zeilen ausser Spielspass, in Anzeige-Reihenfolge."""
    if nur_spass is None:
        nur_spass = nur_spielspass()
    if nur_spass:
        return ()
    return KATEGORIEN[geraet(syskey)]


def ist_automat(kind, arg):
    """Ein Arcade-Spiel: ein .mra-Eintrag (kind 'core')."""
    return kind == "core" and isinstance(arg, str) \
        and arg.lower().endswith(".mra")


def bewertbar(kind, arg):
    return kind == "game" or ist_automat(kind, arg)


def stempel(eintrag, sekunden=0):
    """'klassiker', 'hit', 'gurke' oder None."""
    if not eintrag:
        return None
    try:
        spass = int(eintrag.get("spass"))
    except (TypeError, ValueError):
        return None
    if spass >= KLASSIKER_AB and (sekunden or 0) >= KLASSIKER_STUNDEN * 3600:
        return "klassiker"
    if spass >= HIT_AB:
        return "hit"
    if spass < GURKE_UNTER:
        return "gurke"
    return None


def vorschlag(sekunden, starts=0):
    """Der vorbelegte Spielspass - aus dem, wie gespielt wurde. Ein
    Vorschlag, den ein Druck auf A bestaetigt; kein Urteil."""
    sekunden = sekunden or 0
    starts = starts or 0
    if sekunden >= 10 * 3600:
        return 85
    if sekunden >= 3 * 3600 or starts >= 10:
        return 80
    if sekunden >= 3600 or starts >= 5:
        return 75
    return 70


def runden(wert):
    """Auf 0..100 begrenzen."""
    try:
        wert = int(wert)
    except (TypeError, ValueError):
        return None
    return max(0, min(100, wert))


def farbstufe(wert):
    """'rot' unter 50, 'gelb' bis 79, 'gruen' ab 80."""
    if wert is None:
        return None
    if wert < 50:
        return "rot"
    if wert < 80:
        return "gelb"
    return "gruen"


# ======================================================================
# DIE DATEI
# ======================================================================
_daten = None          # {schluessel: eintrag}
_kaputt = [False]


def schluessel(syskey, label):
    return "%s|%s" % (syskey or "", label or "")


def _laden():
    global _daten
    if _daten is not None:
        return _daten
    _kaputt[0] = False
    try:
        with open(DATEI, encoding="utf-8") as f:
            roh = json.load(f)
        spiele = roh.get("spiele") if isinstance(roh, dict) else None
        _daten = dict(spiele) if isinstance(spiele, dict) else {}
        if not isinstance(spiele, dict):
            _kaputt[0] = True
    except FileNotFoundError:
        _daten = {}
    except (OSError, ValueError):
        _daten = {}
        _kaputt[0] = os.path.exists(DATEI)
    return _daten


def vergessen():
    """Den Merker verwerfen (Tests; nach einem Tausch der Datei)."""
    global _daten
    _daten = None


def _schreiben(daten):
    os.makedirs(os.path.dirname(DATEI), exist_ok=True)
    if _kaputt[0] and os.path.exists(DATEI):
        # Nicht ueberschreiben, was wir nicht lesen konnten.
        try:
            os.replace(DATEI, DATEI + ".kaputt")
        except OSError:
            pass
        _kaputt[0] = False
    tmp = DATEI + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"version": VERSION, "spiele": daten}, f,
                  ensure_ascii=False, indent=1, sort_keys=True)
        f.flush()
        try:
            os.fsync(f.fileno())
        except OSError:
            pass
    os.replace(tmp, DATEI)


def wertung(syskey, label):
    """Der Eintrag eines Spiels oder None. Bei AUS immer None, ohne
    die Datei zu lesen."""
    if not an():
        return None
    return _laden().get(schluessel(syskey, label))


def spielspass(syskey, label):
    e = wertung(syskey, label)
    if not e:
        return None
    return runden(e.get("spass"))


def alle():
    if not an():
        return {}
    return dict(_laden())


def speichern(syskey, label, werte, kind=None, arg=None, heute=None):
    """werte: {'spass': 91, 'grafik': 85, ..., 'schwierigkeit': 'knackig',
    'spieler': '1'}. Leere Werte (None) fallen weg. Liefert den Eintrag
    oder None, wenn kein Spielspass da ist (ohne ihn keine Wertung)."""
    spass = runden((werte or {}).get("spass"))
    if spass is None or not label:
        return None
    daten = dict(_laden())
    k = schluessel(syskey, label)
    alt = daten.get(k) or {}
    datum = heute or time.strftime("%Y-%m-%d")
    e = {"label": label, "syskey": syskey or "", "spass": spass,
         "datum": datum}
    for name in ALLE_PROZENTE[1:]:
        w = runden(werte.get(name))
        if w is not None:
            e[name] = w
    if werte.get("schwierigkeit") in SCHWIERIGKEITEN:
        e["schwierigkeit"] = werte["schwierigkeit"]
    if werte.get("spieler") in SPIELER:
        e["spieler"] = werte["spieler"]
    # Build 347: Kurzfazit und Zweitmeinung.
    if werte.get("fazit") in FAZITE:
        e["fazit"] = werte["fazit"]
    zweit = runden(werte.get("zweit"))
    if zweit is not None:
        e["zweit"] = zweit
        if werte.get("zweit_fazit") in FAZITE:
            e["zweit_fazit"] = werte["zweit_fazit"]
    kind = kind or alt.get("kind")
    arg = arg if arg is not None else alt.get("arg")
    if kind:
        e["kind"] = kind
    if arg is not None:
        e["arg"] = list(arg) if isinstance(arg, (list, tuple)) else arg
    verlauf = list(alt.get("verlauf") or [])
    if not verlauf or verlauf[-1][1] != spass:
        verlauf.append([datum, spass])
    e["verlauf"] = verlauf[-20:]
    daten[k] = e
    _schreiben(daten)
    _laden_setzen(daten)
    return e


def _laden_setzen(daten):
    global _daten
    _daten = daten


def loeschen(syskey, label):
    daten = dict(_laden())
    if daten.pop(schluessel(syskey, label), None) is None:
        return False
    _schreiben(daten)
    _laden_setzen(daten)
    return True


# ======================================================================
# DAS TESTARCHIV
# ======================================================================
def _reihe(zeile):
    return zeile[:2]                  # Spielspass absteigend, dann Name


def testarchiv(systemname, hits_name):
    """Der Baumknoten der Kategorie: ein Ordner mit den Hits ueber alle
    Systeme und je System einer, darin sortiert nach Spielspass (die
    Liste sortiert Ordner nach Namen, Eintraege nicht). Ordnernamen
    OHNE Zahl - wer gerade darin steht und ein weiteres Spiel bewertet,
    soll nicht in einem umbenannten Ordner landen. None, wenn nichts
    startbar ist."""
    je_system = {}
    hits = []
    for e in alle().values():
        kind, arg = e.get("kind"), e.get("arg")
        if not kind or arg is None or not e.get("label"):
            continue
        spass = runden(e.get("spass")) or 0
        zeile = (-spass, e["label"].lower(), (e["label"], kind, arg))
        je_system.setdefault(e.get("syskey") or "", []).append(zeile)
        if spass >= HIT_AB:
            hits.append(zeile)
    if not je_system:
        return None
    ordner = {}
    if hits:
        ordner[hits_name] = {"folders": {},
                             "items": [z[2] for z in
                                       sorted(hits, key=_reihe)]}
    for sk in sorted(je_system, key=lambda s: systemname(s).lower()):
        name = systemname(sk)
        if name in ordner:            # zwei Systeme, ein Anzeigename
            name = "%s (%s)" % (name, sk)
        ordner[name] = {
            "folders": {},
            "items": [z[2] for z in sorted(je_system[sk], key=_reihe)]}
    return {"folders": ordner, "items": []}


# ======================================================================
# BUILD 347: DAMALS GEGEN HEUTE, DAS MONATSHEFT, DER EXPORT
# ======================================================================
def datum_lesbar(iso):
    """'2026-11-22' -> '22.11.2026'; Unlesbares bleibt, wie es ist."""
    teile = str(iso or "").split("-")
    if len(teile) == 3 and all(x.isdigit() for x in teile):
        return "%s.%s.%s" % (teile[2], teile[1], teile[0])
    return str(iso or "")


def damals_heute(eintrag):
    """((datum, wert) der ersten, (datum, wert) der letzten Wertung) -
    nur wenn sich der Spielspass seither geaendert hat, sonst None."""
    verlauf = [v for v in (eintrag or {}).get("verlauf") or ()
               if isinstance(v, (list, tuple)) and len(v) == 2]
    if len(verlauf) < 2:
        return None
    erst, letzt = verlauf[0], verlauf[-1]
    if runden(erst[1]) == runden(letzt[1]):
        return None
    return (erst[0], runden(erst[1])), (letzt[0], runden(letzt[1]))


def _monat(iso):
    teile = str(iso or "").split("-")
    try:
        return int(teile[0]), int(teile[1])
    except (ValueError, IndexError):
        return None


def monate():
    """Alle Monate mit mindestens einer Wertung, juengster zuerst."""
    gesehen = set()
    for e in alle().values():
        for v in e.get("verlauf") or ():
            m = _monat(v[0] if v else None)
            if m:
                gesehen.add(m)
    return sorted(gesehen, reverse=True)


def monatsheft(jahr, monat):
    """Was in einem Monat bewertet wurde. Ein dict:
        neu      - zum ERSTEN Mal bewertet, bester zuerst
        nach     - in dem Monat neu bewertet, aber schon frueher getestet
        spiel    - das Spiel des Monats (bester Wert des Monats) oder None
        hits     - wie viele davon ab HIT_AB
        gurke    - das schwaechste unter GURKE_UNTER oder None
        charts   - die besten CHARTS aller bis Monatsende bewerteten
    Jeder Eintrag ist (wert im Monat, label, syskey)."""
    ziel = (jahr, monat)
    neu, nach, charts = [], [], []
    for e in alle().values():
        verlauf = [v for v in e.get("verlauf") or ()
                   if isinstance(v, (list, tuple)) and len(v) == 2]
        if not verlauf:
            continue
        erst = _monat(verlauf[0][0])
        im_monat = [v for v in verlauf if _monat(v[0]) == ziel]
        bis_dahin = [v for v in verlauf if _monat(v[0]) and
                     _monat(v[0]) <= ziel]
        zeile_label = e.get("label") or ""
        if bis_dahin:
            charts.append((runden(bis_dahin[-1][1]) or 0, zeile_label,
                           e.get("syskey") or ""))
        if not im_monat:
            continue
        z = (runden(im_monat[-1][1]) or 0, zeile_label, e.get("syskey") or "")
        (neu if erst == ziel else nach).append(z)

    def _reihe(z):
        return (-z[0], z[1].lower())
    neu.sort(key=_reihe)
    nach.sort(key=_reihe)
    charts.sort(key=_reihe)
    alle_monat = sorted(neu + nach, key=_reihe)
    gurken = [z for z in alle_monat if z[0] < GURKE_UNTER]
    return {"neu": neu, "nach": nach,
            "spiel": alle_monat[0] if alle_monat else None,
            "hits": sum(1 for z in alle_monat if z[0] >= HIT_AB),
            "gurke": gurken[-1] if gurken else None,
            "charts": charts[:CHARTS]}


CSV_SPALTEN = ("system", "spiel", "spass", "grafik", "sound", "musik",
               "effekte", "steuerung", "credit", "schwierigkeit",
               "spieler", "fazit", "zweit", "zweit_fazit", "stempel",
               "datum", "erste_wertung", "spielzeit_h")


def csv_zeilen(systemname, sekunden_fn, texte):
    """Die Zeilen des Exports (ohne Kopf), sortiert nach System und
    Spielspass. texte(art, wert) liefert die Beschriftung fuer
    Schwierigkeit, Spieler, Fazit und Stempel."""
    zeilen = []
    for e in alle().values():
        sk = e.get("syskey") or ""
        sek = sekunden_fn(e.get("label") or "") or 0
        st = stempel(e, sek)
        verlauf = e.get("verlauf") or []
        zeile = {
            "system": systemname(sk), "spiel": e.get("label") or "",
            "schwierigkeit": texte("schwierigkeit", e.get("schwierigkeit")),
            "spieler": texte("spieler", e.get("spieler")),
            "fazit": texte("fazit", e.get("fazit")),
            "zweit_fazit": texte("fazit", e.get("zweit_fazit")),
            "stempel": texte("stempel", st),
            "datum": datum_lesbar(e.get("datum")),
            "erste_wertung": datum_lesbar(verlauf[0][0]) if verlauf else "",
            "spielzeit_h": ("%.1f" % (sek / 3600.0)).replace(".", ",")
            if sek else "",
        }
        for k in ALLE_PROZENTE + ("zweit",):
            w = runden(e.get(k))
            zeile[k] = "" if w is None else str(w)
        zeilen.append(zeile)
    zeilen.sort(key=lambda z: (z["system"].lower(),
                               -int(z["spass"] or 0), z["spiel"].lower()))
    return zeilen


def csv_schreiben(kopf, zeilen, pfad=None):
    """Der Export als CSV fuer Excel und Co.: Semikolon, UTF-8 mit BOM
    (sonst zeigt Excel die Umlaute falsch), ueber .tmp geschrieben.
    Liefert den Pfad."""
    import csv
    pfad = pfad or CSV_DATEI
    os.makedirs(os.path.dirname(pfad), exist_ok=True)
    tmp = pfad + ".tmp"
    with open(tmp, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow([kopf[k] for k in CSV_SPALTEN])
        for z in zeilen:
            w.writerow([z.get(k, "") for k in CSV_SPALTEN])
    os.replace(tmp, pfad)
    return pfad
