#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Die Zeitmaschine (Build 351, ueberarbeitet in Build 353).

NUTZERWUNSCH: "das ultimative Feature" - ein Jahr waehlen, und Dragend
zeigt die Spiele aus diesem Jahr. Ein- und ausschaltbar, "Zurueck in die
Gegenwart" als eigener Punkt und auf B. Und: "die Performance, die wir
jetzt haben, darf nicht darunter leiden".

BUILD 353, ZWEI RUECKMELDUNGEN:
  * "es sollten wirklich nur die spiele angezeigt werden, die auch
    wirklich in dem ausgewaehlten jahr erschienen sind, und nicht alle,
    die es bis dahin schon gab" - der Knoten zeigt jetzt nur noch das
    eine Jahr. Das Drehrad ueberspringt Jahre ohne ein einziges Spiel.
  * "wenn ich die zeitmaschine neu starte, liest er immer wieder die
    spiele neu ein" - die Jahre wurden bisher nur fuer die Sitzung und
    nur bis zum naechsten Neuaufbau der Kategorien gemerkt (den loesen
    auch die RetroAchievements im Hintergrund aus). Jetzt stehen sie in
    einem MERKER auf der Karte (zeitmaschine_jahre.json), je System mit
    einem Stand der Quellen (fe/art.meta_stand). Gelesen wird nur noch,
    was neu ist oder dessen Quelle sich geaendert hat.

KOSTEN: keine, solange man nicht reist. Der Merker wird erst bei der
ersten Reise einer Sitzung geladen, nicht beim Start.

WAS HIER STEHT: der Schalter, der Merker, das Verzeichnis, der
Baumknoten fuer ein Jahr. Gezeichnet wird in frontend.py.
"""
import json
import os
import threading

ORDNER = "/media/fat/frontend"
AUS_FLAG = os.path.join(ORDNER, "zeitmaschine_aus")
MERKER_DATEI = os.path.join(ORDNER, "zeitmaschine_jahre.json")
MERKER_VERSION = 1
FRUEHESTES = 1970
HAPPEN = 300                 # so viele gelesene Spiele zwischen zwei Blicken
ARCADE = "ARCADE"            # wie fe/wertungen.ARCADE


# ======================================================================
# SCHALTER (Vorgabe AN - sie kostet nichts, solange man nicht reist)
# ======================================================================
_aus = [None]


def an():
    if _aus[0] is None:
        _aus[0] = os.path.exists(AUS_FLAG)
    return not _aus[0]


def toggle_an():
    try:
        if an():
            os.makedirs(os.path.dirname(AUS_FLAG), exist_ok=True)
            open(AUS_FLAG, "w").close()
        elif os.path.exists(AUS_FLAG):
            os.remove(AUS_FLAG)
    except OSError:
        pass
    _aus[0] = None
    return an()


# ======================================================================
# DER MERKER: {syskey: {label: jahr}} plus der Stand der Quellen je System
# ======================================================================
# jahr ist die rohe Zahl aus den Spieldaten (0 = keines bekannt) - die
# Plausibilitaet (ab 1970, nicht in der Zukunft) wird beim Einsortieren
# geprueft, nicht beim Merken. Sonst haenge das Gemerkte am Tag, an dem
# es gemerkt wurde.
_merker = {"geladen": False, "stand": {}, "jahre": {}, "neu": False}
_schreiber = [None]
_lock = threading.Lock()


def merker_vergessen():
    """Alles vergessen (Pruefstand). Die Datei bleibt liegen."""
    with _lock:
        _merker.update(geladen=False, stand={}, jahre={}, neu=False)


def merker_laden():
    """Einmal je Sitzung, und erst bei der ersten Reise. Eine kaputte
    oder fremde Datei heisst: von vorn, nicht: abstuerzen."""
    if _merker["geladen"]:
        return
    _merker["geladen"] = True
    try:
        with open(MERKER_DATEI, encoding="utf-8") as f:
            daten = json.load(f)
    except (OSError, ValueError):
        return
    if not isinstance(daten, dict) or daten.get("version") != MERKER_VERSION:
        return
    stand, jahre = daten.get("stand"), daten.get("jahre")
    if not isinstance(stand, dict) or not isinstance(jahre, dict):
        return
    for sk, tab in jahre.items():
        if not isinstance(tab, dict) or not isinstance(stand.get(sk), str):
            continue
        _merker["jahre"][sk] = dict(
            (l, j) for l, j in tab.items() if isinstance(j, int))
        _merker["stand"][sk] = stand[sk]


def _schreiben(abzug):
    tmp = MERKER_DATEI + ".tmp"
    try:
        os.makedirs(os.path.dirname(MERKER_DATEI), exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(abzug, f, ensure_ascii=False, separators=(",", ":"))
        os.replace(tmp, MERKER_DATEI)
        return True
    except (OSError, ValueError, TypeError):
        try:
            os.remove(tmp)
        except OSError:
            pass
        return False


def merker_speichern(hintergrund=True):
    """Den Merker auf die Karte schreiben, wenn es Neues gibt - ueber
    .tmp und os.replace(). Im Hintergrund: 40 000 Spiele sind rund
    1,5 MB JSON, und das Drehrad soll nicht darauf warten. Geschrieben
    wird ein ABZUG, damit der Faden nichts sieht, was sich gerade
    aendert. Rueckgabe: der Faden (oder True/False ohne Faden)."""
    with _lock:
        if not _merker["neu"]:
            return None
        abzug = {"version": MERKER_VERSION,
                 "stand": dict(_merker["stand"]),
                 "jahre": dict((sk, dict(tab))
                               for sk, tab in _merker["jahre"].items())}
        _merker["neu"] = False
    if not hintergrund:
        return _schreiben(abzug)
    alt = _schreiber[0]
    if alt is not None and alt.is_alive():
        alt.join()
    faden = threading.Thread(target=_schreiben, args=(abzug,), daemon=True)
    _schreiber[0] = faden
    faden.start()
    return faden


def _tabelle(syskey, stand_fn, gesehen):
    """Die gemerkten Jahre eines Systems - verworfen, wenn sich die
    Quelle seither geaendert hat. Je Aufbau einmal je System."""
    tab = gesehen.get(syskey)
    if tab is not None:
        return tab
    stand = stand_fn(syskey) if stand_fn else ""
    with _lock:
        if _merker["stand"].get(syskey) != stand:
            _merker["jahre"][syskey] = {}
            _merker["stand"][syskey] = stand
            _merker["neu"] = True
        tab = _merker["jahre"].setdefault(syskey, {})
    gesehen[syskey] = tab
    return tab


# ======================================================================
# DAS VERZEICHNIS
# ======================================================================
def jahr_zahl(roh, bis=None):
    """Das Jahr aus einem Metadatenwert - nur plausible."""
    from fe.filter import jahr_zahl as _jz
    return plausibel(_jz(roh), bis)


def plausibel(j, bis=None):
    if not j or j < FRUEHESTES or (bis and j > bis):
        return 0
    return j


class Verzeichnis(object):
    """{jahr: [(syskey, label, kind, arg)]} plus die Zahl der Spiele
    ohne bekanntes Jahr."""

    def __init__(self):
        self.jahre = {}
        self.ohne = 0
        self.gesehen = set()

    def aufnehmen(self, syskey, label, kind, arg, jahr):
        schl = (syskey, label)
        if schl in self.gesehen:
            return
        self.gesehen.add(schl)
        if jahr:
            self.jahre.setdefault(jahr, []).append((syskey, label, kind, arg))
        else:
            self.ohne += 1

    def bereich(self):
        if not self.jahre:
            return None
        return min(self.jahre), max(self.jahre)

    def zaehlen(self, jahr):
        """Spiele aus genau diesem Jahr."""
        return len(self.jahre.get(jahr, ()))

    def systeme(self, jahr):
        return len(set(e[0] for e in self.jahre.get(jahr, ())))

    def startjahr(self):
        """Das Jahr mit den meisten Spielen der Sammlung."""
        if not self.jahre:
            return None
        return max(self.jahre, key=lambda j: (len(self.jahre[j]), -j))

    def jahr_von(self, syskey, label):
        for j, v in self.jahre.items():
            for e in v:
                if e[0] == syskey and e[1] == label:
                    return j
        return 0

    def weiter(self, jahr, schritt):
        """Das Drehrad (Build 353): vom Jahr um schritt weiter, aber nur
        auf Jahre mit Spielen. +-1 springt zum naechsten Jahr mit
        Spielen in dieser Richtung (keines mehr: bleibt stehen); +-10
        geht zehn Jahre und nimmt von dort das naechste Jahr mit Spielen,
        zuerst in Laufrichtung."""
        if not self.jahre:
            return jahr
        von, bis = self.bereich()
        if schritt in (1, -1):
            j = jahr + schritt
            while von <= j <= bis:
                if j in self.jahre:
                    return j
                j += schritt
            return jahr
        ziel = max(von, min(bis, jahr + schritt))
        richtung = 1 if schritt > 0 else -1
        for d in range(0, bis - von + 1):
            for j in (ziel + d * richtung, ziel - d * richtung):
                if von <= j <= bis and j in self.jahre:
                    return j
        return jahr


def eintraege(cats):
    """Alle Spiele der System-Kategorien: (syskey, label, kind, arg) -
    durch die Unterordner. Nur Kategorien mit Systemschluessel; die
    abgeleiteten (Favoriten, Testarchiv ...) wuerden sie doppelt
    liefern."""
    for _name, knoten, syskey in cats:
        if not syskey or not isinstance(knoten, dict):
            continue
        stapel = [knoten]
        while stapel:
            k = stapel.pop()
            for unter in (k.get("folders") or {}).values():
                if isinstance(unter, dict):
                    stapel.append(unter)
            for e in k.get("items") or ():
                if len(e) >= 3 and e[1] in ("game", "core"):
                    yield syskey, e[0], e[1], e[2]


def _zaehlt(kind, arg, mra_fn):
    """Kommt der Eintrag ins Verzeichnis? Spiele immer, Cores nur als
    .mra (Arcade) - ein .rbf-Core hat kein Erscheinungsjahr."""
    if kind != "core":
        return True
    return bool(mra_fn) and isinstance(arg, str) \
        and arg.lower().endswith(".mra")


def offen(cats, mra_fn=None, stand_fn=None):
    """So viele Spiele muss bauen() noch aus den Spieldaten LESEN - die
    uebrigen kennt der Merker. 0 heisst: keine Fortschrittsanzeige
    noetig."""
    merker_laden()
    gesehen, doppelt, n = {}, set(), 0
    for syskey, label, kind, arg in eintraege(cats):
        if (syskey, label) in doppelt or not _zaehlt(kind, arg, mra_fn):
            continue
        doppelt.add((syskey, label))
        if label not in _tabelle(syskey, stand_fn, gesehen):
            n += 1
    return n


def anzahl(cats, mra_fn=None):
    """So viele Spiele umfasst das Verzeichnis."""
    gesehen = set()
    for syskey, label, kind, arg in eintraege(cats):
        if _zaehlt(kind, arg, mra_fn):
            gesehen.add((syskey, label))
    return len(gesehen)


def _lesen(syskey, label, kind, arg, meta_fn, mra_fn):
    from fe.filter import jahr_zahl as _jz
    try:
        meta = (mra_fn(arg) if kind == "core" else meta_fn(syskey, label)) \
            or {}
    except Exception:                                    # noqa: BLE001
        meta = {}
    try:
        return int(_jz(meta.get("year")) or 0)
    except (TypeError, ValueError):
        return 0


def bauen(cats, meta_fn, mra_fn=None, bis=None, zwischendurch=None,
          stand_fn=None):
    """Das Verzeichnis bauen. Was der Merker kennt, wird nicht gelesen.
    meta_fn(syskey, label) -> dict, mra_fn(pfad) -> dict (Arcade),
    stand_fn(syskey) -> str (Stand der Quellen). zwischendurch(n) alle
    HAPPEN GELESENEN Spiele; liefert es False, wird abgebrochen
    (Rueckgabe None) - das bis dahin Gelesene bleibt gemerkt."""
    merker_laden()
    vz = Verzeichnis()
    gesehen = {}
    n = 0
    for syskey, label, kind, arg in eintraege(cats):
        if (syskey, label) in vz.gesehen:
            continue             # schon da - die Spieldaten nicht nochmal
        if not _zaehlt(kind, arg, mra_fn):
            continue
        tab = _tabelle(syskey, stand_fn, gesehen)
        roh = tab.get(label)
        if roh is None:
            roh = _lesen(syskey, label, kind, arg, meta_fn, mra_fn)
            with _lock:
                tab[label] = roh
                _merker["neu"] = True
            n += 1
            if zwischendurch is not None and not n % HAPPEN:
                if zwischendurch(n) is False:
                    return None
        vz.aufnehmen(syskey, label, kind, arg, plausibel(roh, bis))
    return vz


def knoten(vz, jahr, systemname, texte, wertungen=None):
    """Der Baumknoten fuer EIN Jahr (Build 353: nur dieses Jahr):
      oben:    "Zurueck in die Gegenwart", "Anderes Jahr ..." - vor
               allen Ordnern (frontend._display_items)
      folge:   "Alle Spiele aus <jahr>", "Deine Wertungen" vor den
               Systemen
      folders: die beiden und je System ein Ordner mit seinen Spielen
               aus diesem Jahr, nach Name.
    texte: dict mit 'alle' (Format mit %d), 'wertungen', 'zurueck',
    'anderes'. wertungen: {(syskey, label): spielspass} oder None."""
    ordner = {}
    folge = []
    liste = sorted(vz.jahre.get(jahr, ()), key=lambda e: e[1].lower())
    if liste:
        ordner[texte["alle"] % jahr] = {
            "folders": {}, "items": [(e[1], e[2], e[3]) for e in liste]}
        folge.append(texte["alle"] % jahr)
    je_system = {}
    for e in liste:
        je_system.setdefault(e[0], []).append(e)
    if wertungen:
        bewertet = []
        for e in liste:
            # Arcade-Spiele (.mra) stehen in den Wertungen unter
            # ARCADE (fe/wertungen.ist_automat) - im Verzeichnis sind
            # nur .mra-Cores, also reicht hier die Art.
            sk = ARCADE if e[2] == "core" else e[0]
            w = wertungen.get((sk, e[1]))
            if w is not None:
                bewertet.append((-w, e[1].lower(), e))
        if bewertet:
            bewertet.sort(key=lambda x: x[:2])
            ordner[texte["wertungen"]] = {
                "folders": {}, "items": [(e[1], e[2], e[3])
                                         for _w, _n, e in bewertet]}
            folge.append(texte["wertungen"])
    for sk, eintr in je_system.items():
        name = systemname(sk)
        if name in ordner:
            name = "%s (%s)" % (name, sk)
        ordner[name] = {"folders": {},
                        "items": [(e[1], e[2], e[3]) for e in eintr]}
    return {"folders": ordner, "folge": folge,
            "oben": [(texte["zurueck"], "zeitmaschine_zurueck", None),
                     (texte["anderes"], "zeitmaschine", None)],
            "items": []}
