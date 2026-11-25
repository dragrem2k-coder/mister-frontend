#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Heft-Tests von kultboy.com (Build 350).

NUTZERWUNSCH: zu einem Spiel die Tests aus den alten Magazinen zeigen -
die Liste mit Heft, Ausgabe und Wertung und die gescannte Heftseite
als Bild. Die Seiten werden ONLINE geholt, nur auf Knopfdruck, und
NICHT gespeichert ("wer die lesen will muss halt 2-3 Sekunden
warten"). Gemerkt werden darf nur, welche Kultboy-Seite zu welchem
Spiel gehoert - eine Nummer, kein Inhalt.

DER AUFBAU DER SEITEN (vom Nutzer im Browser gespeichert, Stand
11/2026):

  Suche     /index.php?site=testb/testb&q=<Titel>&...&system=<Nr>
            Tabelle, je Spiel ein Link /testbericht-uebersicht/<Nr>/,
            alle Namen des Spiels im Link, durch <br> getrennt.
  Uebersicht /testbericht-uebersicht/<Nr>/
            je Test eine Zeile <tr bgcolor="#eee8aa">: Heft+Ausgabe,
            "Testbericht"/"Vorschau" mit Link index.php?site=t&id=<Nr>,
            Grafik, Sound, Wertung (oder EINE Zelle colspan=3 fuer
            "Super", "-" ...), System, Datentraeger, Hits, Autor.
            Mehrere Systeme in einer Zeile: Werte durch <br> getrennt.
  Test      /index.php?site=t&id=<Nr>
            Heft+Ausgabe im Link /magazin/<Nr>/, der Scan als
            HINTERGRUND einer Tabellenzelle (background="/gfx/..."),
            darueber ein durchsichtiges testbericht.gif.

WAS HIER STEHT: Adressen, Lesen der Seiten, das Zuordnen eines
Spielnamens, der Merker. Gezeichnet wird in frontend.py. Das Netz wird
ueber holer() erreicht - die Pruefstaende reichen einen eigenen herein
und kommen so ohne Netz aus.

EIN SCHALTER, Vorgabe AUS: kultboy.com verbietet in seiner robots.txt
Programmen den Ordner /gfx/, in dem die Scans liegen. Eingeschaltet
wird das vom Nutzer, wenn Kultboy zugestimmt hat.
"""
import html
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

BASIS = "https://www.kultboy.com"
ORDNER = "/media/fat/frontend"
AN_FLAG = os.path.join(ORDNER, "kultboy_an")
ZUORDNUNG_FILE = os.path.join(ORDNER, "kultboy_zuordnung.json")
ZEITLIMIT = 8.0
UA = "Mozilla/5.0 (X11; Linux armv7l)"
MAX_BYTES = 6 * 1024 * 1024          # eine Seite oder ein Scan, hoechstens
MAX_TREFFER = 12

# Dragend-Systemschluessel -> Kultboy-Systemnummern (Suchfeld "system").
# Mehrere Nummern: das erste ist die Suche, alle zaehlen beim Sortieren.
SYSTEME = {
    "NES": (17,), "FDS": (17,), "SNES": (18,), "SMW_HACKS": (18,),
    "SNES_ALTTP_TRACKER": (18,), "Genesis": (15,), "N64": (56,),
    "PSX": (57,), "GAMEBOY": (23,), "SUPERGAMEBOY": (23,), "GBC": (46,),
    "GBA": (47,), "SMS": (33,), "GAMEGEAR": (70,), "TGFX16": (22, 81),
    "TGFX16CD": (83,), "MegaCD": (16,), "S32X": (44,), "Saturn": (48,),
    "NEOGEO": (13,), "NEOGEOCD": (85,), "VIRTUALBOY": (52,), "3DO": (14,),
    "ATARI2600": (38,), "ATARI7800": (40,), "ATARILYNX": (24,),
    "JAGUAR": (19, 103), "CDI": (37,), "COLECOVISION": (41,),
    "INTELLIVISION": (42,), "ODYSSEY2": (43,), "VECTREX": (68,),
    "WONDERSWAN": (53,), "WONDERSWANCOLOR": (53,), "C64": (1,),
    "AMIGA": (21, 7, 8, 9), "AMSTRAD": (27,), "AO486": (11, 12),
    "ARCADE": (25,),
}
SYSTEM_NAMEN = {
    1: "C64/128", 7: "Amiga 1200/4000", 8: "Amiga CD32", 9: "Amiga CDTV",
    11: "PC", 12: "PC CD-ROM", 13: "Neo Geo", 14: "3DO", 15: "Mega Drive",
    16: "Mega CD", 17: "NES", 18: "SNES", 19: "Atari Jaguar",
    21: "Amiga", 22: "PC-Engine", 23: "Game Boy", 24: "Lynx",
    25: "Arcade", 27: "CPC", 33: "Master System", 37: "Philips CD-i",
    38: "Atari 2600", 40: "Atari 7800", 41: "CBS Colecovision",
    42: "Mattel Intellivision", 43: "Philips Videopac", 44: "Mega 32X",
    46: "Game Boy Color", 47: "Game Boy Advance", 48: "Saturn",
    52: "Virtual Boy", 53: "WonderSwan", 56: "Nintendo 64",
    57: "PlayStation", 68: "Vectrex", 70: "Game Gear", 81: "Super Grafx",
    83: "PC-Engine CD", 85: "Neo Geo CD", 103: "Atari Jaguar CD",
}


class KultboyFehler(Exception):
    """art: 'netz' (keine Verbindung), 'zeit' (zu langsam), 'seite'
    (Seite nicht lesbar), 'nichts' (kein Treffer)."""

    def __init__(self, art, text=""):
        Exception.__init__(self, text or art)
        self.art = art


# ======================================================================
# SCHALTER UND MERKER
# ======================================================================
_an = [None]


def an():
    if _an[0] is None:
        _an[0] = os.path.exists(AN_FLAG)
    return _an[0]


def toggle_an():
    try:
        if an():
            os.remove(AN_FLAG)
        else:
            os.makedirs(os.path.dirname(AN_FLAG), exist_ok=True)
            open(AN_FLAG, "w").close()
    except OSError:
        pass
    _an[0] = None
    return an()


def _schluessel(syskey, label):
    return "%s|%s" % (syskey or "", label or "")


def zuordnung(syskey, label):
    try:
        with open(ZUORDNUNG_FILE, encoding="utf-8") as f:
            d = json.load(f)
        nr = d.get(_schluessel(syskey, label)) if isinstance(d, dict) \
            else None
        return int(nr) if nr else None
    except (OSError, ValueError, TypeError):
        return None


def _zuordnung_schreiben(aendern):
    try:
        with open(ZUORDNUNG_FILE, encoding="utf-8") as f:
            d = json.load(f)
        if not isinstance(d, dict):
            d = {}
    except (OSError, ValueError):
        d = {}
    aendern(d)
    try:
        os.makedirs(os.path.dirname(ZUORDNUNG_FILE), exist_ok=True)
        tmp = ZUORDNUNG_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, sort_keys=True)
        os.replace(tmp, ZUORDNUNG_FILE)
    except OSError:
        pass


def zuordnung_merken(syskey, label, nr):
    _zuordnung_schreiben(
        lambda d: d.__setitem__(_schluessel(syskey, label), int(nr)))


def zuordnung_vergessen(syskey, label):
    _zuordnung_schreiben(lambda d: d.pop(_schluessel(syskey, label), None))


# ======================================================================
# DAS NETZ
# ======================================================================
def holen(url, zeitlimit=ZEITLIMIT):
    """Bytes einer Adresse - oder KultboyFehler. Nichts wird
    gespeichert. Hoechstens MAX_BYTES."""
    import socket
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=zeitlimit) as r:
            daten = r.read(MAX_BYTES + 1)
            art = r.headers.get_content_charset() if r.headers else None
    except socket.timeout:
        raise KultboyFehler("zeit")
    except urllib.error.HTTPError as e:
        raise KultboyFehler("seite", "HTTP %s" % e.code)
    except (urllib.error.URLError, OSError) as e:
        if "timed out" in str(e):
            raise KultboyFehler("zeit")
        raise KultboyFehler("netz", str(e))
    if len(daten) > MAX_BYTES:
        raise KultboyFehler("seite", "zu gross")
    holen.zuletzt_charset = art
    return daten


holen.zuletzt_charset = None


def _text(daten):
    """Die Seiten nennen windows-1252, kommen aber auch als UTF-8."""
    try:
        return daten.decode("utf-8")
    except UnicodeDecodeError:
        return daten.decode("cp1252", errors="replace")


def _absolut(pfad):
    pfad = html.unescape(pfad or "").strip()
    if pfad.startswith("//"):
        return "https:" + pfad
    if pfad.startswith("/"):
        return BASIS + pfad
    return pfad


def _rein(s):
    """HTML-Schnipsel -> Text: Tags weg, Entitaeten aufgeloest."""
    s = re.sub(r"<[^>]+>", "", s or "")
    return re.sub(r"\s+", " ", html.unescape(s).replace("\xa0", " ")).strip()


def _zeilen(s):
    """Zellinhalt mit <br> -> Liste der Zeilen (leere weg)."""
    teile = re.split(r"<br\s*/?>", s or "", flags=re.I)
    return [z for z in (_rein(t) for t in teile) if z]


# ======================================================================
# NAMEN
# ======================================================================
def suchname(label):
    """'Super Metroid (Japan, USA) (En,Ja)' -> 'Super Metroid'."""
    s = re.sub(r"\([^)]*\)|\[[^\]]*\]", " ", label or "")
    s = s.replace("_", " ")
    return re.sub(r"\s+", " ", s).strip(" -")


_ROEMISCH = {"ii": "2", "iii": "3", "iv": "4", "v": "5", "vi": "6"}


def vergleich(name):
    """Fuer den Vergleich: klein, nur Buchstaben/Ziffern, roemische
    Zahlen als Ziffern, Artikel 'the' vorn weg."""
    s = suchname(name).lower()
    s = s.replace("&", " and ")
    woerter = re.findall(r"[a-z0-9äöüß]+", s)
    woerter = [_ROEMISCH.get(w, w) for w in woerter]
    if woerter and woerter[0] == "the":
        woerter = woerter[1:]
    return " ".join(woerter)


def _guete(gesucht, namen):
    """3 = gleich, 2 = gleich bis zum Doppelpunkt/Gedankenstrich,
    1 = faengt damit an, 0 = sonst."""
    g = vergleich(gesucht)
    best = 0
    for n in namen:
        v = vergleich(n)
        kurz = vergleich(re.split(r":| - ", n, maxsplit=1)[0])
        if v == g:
            return 3
        if kurz == g:
            best = max(best, 2)
        elif g and v.startswith(g + " "):
            best = max(best, 1)
    return best


# ======================================================================
# DIE SEITEN LESEN
# ======================================================================
def such_url(name, sysnr=99, kodierung="utf-8"):
    q = urllib.parse.quote_plus(suchname(name), encoding=kodierung,
                                errors="replace")
    return ("%s/index.php?site=testb/testb&q=%s&firma=0&orderby=a.name"
            "&mag=99&discs_art=0&spieltype=0&a=99&system=%d&sort=ASC"
            "&jahr=0&limit=50" % (BASIS, q, int(sysnr)))


def suchtreffer(seite):
    """[(nr, [namen])] aus einer Trefferliste."""
    treffer = []
    gesehen = set()
    # Nur die Zeilen der Ergebnistabelle (class row2/row3) - auf der
    # Seite stehen ueber dem Formular weitere Links auf Uebersichten.
    zeilen = re.findall(r'<tr class="row[23]">(.*?)</tr>', seite, re.S | re.I)
    for nr, inhalt in re.findall(
            r'<a href="(?:https?://www\.kultboy\.com)?/testbericht-uebersicht/'
            r'(\d+)/?">(.*?)</a>', "\n".join(zeilen), re.S):
        nr = int(nr)
        if nr in gesehen:
            continue
        namen = _zeilen(inhalt)
        if namen:
            gesehen.add(nr)
            treffer.append((nr, namen))
    return treffer


def uebersicht_url(nr):
    return "%s/testbericht-uebersicht/%d/" % (BASIS, int(nr))


def test_url(tid):
    return "%s/index.php?site=t&id=%d" % (BASIS, int(tid))


def tests(seite):
    """Die Tests einer Uebersichtsseite: Liste von dicts mit heft, art,
    id, wertung, grafik, sound (je eine Liste, eine Zeile je System),
    systeme."""
    raus = []
    for zeile in re.findall(r'<tr bgcolor="#eee8aa">(.*?)</tr>', seite,
                            re.S | re.I):
        zellen = re.findall(r"<td([^>]*)>(.*?)</td>", zeile, re.S | re.I)
        if len(zellen) < 5:
            continue
        m = re.search(r"site=t(?:&amp;|&)id=(\d+)", zellen[1][1])
        if not m:
            continue
        heft = _zeilen(zellen[0][1])
        art = _zeilen(zellen[1][1])
        if 'colspan="3"' in zellen[2][0] or "colspan=3" in zellen[2][0]:
            wertung, grafik, sound = _zeilen(zellen[2][1]), [], []
            rest = zellen[3:]
        else:
            if len(zellen) < 7:
                continue
            grafik = _zeilen(zellen[2][1])
            sound = _zeilen(zellen[3][1])
            wertung = _zeilen(zellen[4][1])
            rest = zellen[5:]
        systeme = _zeilen(rest[0][1]) if rest else []
        raus.append({"heft": heft[0] if heft else "?",
                     "art": art[0] if art else "",
                     "id": int(m.group(1)),
                     "wertung": [w for w in wertung if w != "-"],
                     "grafik": grafik, "sound": sound,
                     "systeme": systeme})
    return raus


def scans(seite):
    """(heft, [Bildadressen]) einer Testseite. Der Scan steht als
    Hintergrund einer Zelle; ein <img> darunter ist das durchsichtige
    testbericht.gif."""
    heft = ""
    m = re.search(r'<a href="(?:https?://www\.kultboy\.com)?/magazin/\d+/?">'
                  r"(.*?)<br", seite, re.S | re.I)
    if m:
        heft = _rein(m.group(1))
    bilder = []
    for pfad in re.findall(r'background="([^"]+)"', seite, re.I):
        p = html.unescape(pfad)
        if not re.search(r"\.(jpe?g|png|gif)$", p, re.I):
            continue
        if "streifen" in p.lower() or "/gfx/" not in p:
            continue
        url = _absolut(p)
        if url not in bilder:
            bilder.append(url)
    return heft, bilder


# ======================================================================
# DER WEG ZUM SPIEL
# ======================================================================
def systemnummern(syskey):
    return SYSTEME.get(syskey or "", ())


def finden(syskey, label, holer=None):
    """Kultboy-Nummer der Uebersichtsseite eines Spiels.
    ('treffer', nr) - eindeutig;
    ('auswahl', [(nr, name)]) - mehrere, der Nutzer waehlt;
    KultboyFehler('nichts') - kein Treffer."""
    # holen zur Laufzeit nachschlagen, nicht beim Definieren binden.
    holer = holer or holen
    name = suchname(label)
    if not name:
        raise KultboyFehler("nichts")
    nummern = systemnummern(syskey)
    versuche = []
    if nummern:
        versuche.append((name, nummern[0]))
    versuche.append((name, 99))
    kurz = re.split(r":| - ", name, maxsplit=1)[0].strip()
    if kurz and kurz != name:
        versuche.append((kurz, 99))
    for q, nr in versuche:
        kodierungen = ["utf-8"]
        if any(ord(c) > 127 for c in q):
            kodierungen.append("cp1252")
        for kod in kodierungen:
            treffer = suchtreffer(_text(holer(such_url(q, nr, kod))))
            if not treffer:
                continue
            gewertet = sorted(((_guete(name, n), i, k, n)
                               for i, (k, n) in enumerate(treffer)),
                              key=lambda x: (-x[0], x[1]))
            beste = [g for g in gewertet if g[0] == gewertet[0][0]]
            if gewertet[0][0] >= 2 and len(beste) == 1:
                return "treffer", beste[0][2]
            if len(treffer) == 1 and gewertet[0][0] >= 1:
                return "treffer", treffer[0][0]
            return "auswahl", [(k, n[0]) for _g, _i, k, n in
                               gewertet[:MAX_TREFFER]]
    raise KultboyFehler("nichts")


def tests_sortiert(liste, syskey):
    """Tests zum eigenen System zuerst, sonst Reihenfolge der Seite."""
    eigene = set(SYSTEM_NAMEN.get(n) for n in systemnummern(syskey))
    return sorted(liste, key=lambda t: 0 if eigene & set(t["systeme"])
                  else 1)


def zeile(test, syskey=None):
    """'Amiga Joker 3/91  89%  Amiga' - eine Zeile der Auswahl. Bei
    mehreren Systemen die Wertung des eigenen."""
    eigene = set(SYSTEM_NAMEN.get(n) for n in systemnummern(syskey))
    systeme = test["systeme"]
    i = 0
    for k, s in enumerate(systeme):
        if s in eigene:
            i = k
            break
    wert = ""
    if test["wertung"]:
        wert = test["wertung"][min(i, len(test["wertung"]) - 1)]
    teile = [test["heft"]]
    if wert:
        teile.append(wert)
    elif test["art"]:
        teile.append(test["art"])
    if systeme:
        teile.append(systeme[i])
    return "  ".join(teile)
