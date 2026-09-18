#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Listenfilter nach Genre, Jahr, Spielerzahl und Entwickler (Build 142).

WARUM ES DAS GIBT - UND WARUM ES NICHTS KOSTET.

Die vier Angaben stehen laengst im Speicher. gameinfo.tsv der
Artwork-Datenbank liefert sie seit Build 115, get_meta() haelt sie je
System zwischengespeichert. Ein Filter ist deshalb kein neues Feature
mit neuen Daten, sondern eine Abfrage auf etwas, das ohnehin da ist:
kein Kartenzugriff, kein Dekodieren, keine neue Datei.

Nachgemessen an der SNES-Tabelle des Nutzers (1803 Spiele):

    Jahr        99,2 % belegt      17 verschiedene Werte
    Genre       98,3 % belegt     160 -> 41 verschiedene Werte
    Entwickler  99,7 % belegt     468 verschiedene Werte
    Spieler     99,8 % belegt       9 verschiedene Werte

DREI DINGE, DIE DIE ROHDATEN NICHT HERGEBEN, und die dieses Modul
deshalb geradezieht:

1. GENRE ist zusammengesetzt und in dieser Form unbrauchbar:
   "Action / Adventure/Action", "Adults/Mahjong/Asiatic board game".
   Der Teil NACH dem letzten Schraegstrich ist die grobe Gattung -
   damit werden aus 160 Werten 41 bedienbare (Platform 285,
   Sports 283, Role Playing Game 225 ...).

2. SPIELER sind Bereiche: "1", "1-2", "1-4", "1-10". Ein
   Zeichenketten-Vergleich waere sinnlos; gefiltert wird nach
   "mindestens N", und dafuer zaehlt die groesste Zahl im Feld.

3. JAHR soll sich als SPANNE angeben lassen ("1992-1995"), nicht nur
   als Einzeljahr - danach sucht man tatsaechlich.

Dieses Modul ist bewusst reine Rechnerei ohne Zeichnen und ohne
Dateizugriff: so laesst es sich vollstaendig pruefen, ohne den
Pruefstand hochzufahren.
"""

# Gemerkte Filter (Build 143, Nutzerwunsch "Filter als Kategorie
# merken"). Eine kleine JSON-Datei neben den uebrigen Einstellungen -
# kein neues Format, keine Datenbank. Jeder Eintrag ist
# {"name":…, "kat":…, "filter":…}: der ANZEIGENAME, die Kategorie, aus
# der gefiltert wird (ueber ihren Namen, nicht ihren Index - Indizes
# verschieben sich, sobald eine Kategorie dazukommt), und die
# Bedingung selbst.
KATEGORIEN_DATEI = "/media/fat/frontend/filter_kategorien.json"
KATEGORIEN_MAX = 20        # mehr waere kein Hauptmenue mehr

# Die vier Felder in Anzeigereihenfolge. Die Namen sind zugleich die
# Schluessel im Filter-Dict und (mit Vorsatz "filter_") die
# Uebersetzungsschluessel.
FELDER = ("genre", "jahr", "spieler", "entwickler")

# Ab so vielen verschiedenen Werten ist Durchblaettern keine Bedienung
# mehr, sondern eine Geduldsprobe - dann uebernimmt die Buchstabenwahl.
# Beim Nutzer trifft das genau den Entwickler (468 Werte).
ZU_VIELE = 40


def genre_kurz(roh):
    """Die grobe Gattung aus einem zusammengesetzten Genre-Feld.

    "Action / Adventure/Action"          -> "Action"
    "Adults/Mahjong/Asiatic board game"  -> "Asiatic board game"
    "Platform"                           -> "Platform"

    Der Teil nach dem letzten Schraegstrich ist in der Datenbank
    durchgehend die Oberkategorie; davor stehen Unterteilungen, die je
    Spiel anders geschnitten sind und deshalb keine brauchbare Liste
    ergeben."""
    if not roh:
        return ""
    return roh.rsplit("/", 1)[-1].strip()


def spieler_max(roh):
    """Die groesste Spielerzahl in einem Feld wie "1", "1-2", "1-10".

    Liefert 0, wenn sich nichts herauslesen laesst - damit faellt der
    Eintrag bei einem Filter "mindestens N" heraus, statt zufaellig
    hineinzurutschen."""
    if not roh:
        return 0
    zahl = 0
    aktuell = ""
    for zeichen in str(roh) + " ":
        if zeichen.isdigit():
            aktuell += zeichen
        else:
            if aktuell:
                try:
                    zahl = max(zahl, int(aktuell))
                except ValueError:
                    pass
                aktuell = ""
    return zahl


def jahr_zahl(roh):
    """Das Jahr als Zahl, sonst 0. Die Datenbank schreibt es vierstellig,
    einzelne Eintraege haben aber Zusaetze ("1994 (Japan)")."""
    if not roh:
        return 0
    ziffern = ""
    for zeichen in str(roh):
        if zeichen.isdigit():
            ziffern += zeichen
            if len(ziffern) == 4:
                break
        elif ziffern:
            break
    try:
        return int(ziffern) if len(ziffern) == 4 else 0
    except ValueError:
        return 0


def jahr_kette(jahre):
    """Die Auswahl fuer die Jahres-Zeile: erst die einzelnen Jahre
    (neueste zuerst), danach Fuenfjahres-Spannen.

    Nach einer Spanne sucht man tatsaechlich ("SNES-Klassiker der
    fruehen Neunziger"), nach einem exakten Jahr seltener - aber
    beides gehoert in dieselbe Zeile, sonst braeuchte es zwei. Die
    Spannen entstehen aus den DATEN, nicht aus einer festen Tabelle:
    eine Spanne, in der nichts liegt, waere nur im Weg."""
    if not jahre:
        return []
    jahre = sorted(set(jahre))
    von = (jahre[0] // 5) * 5
    spannen = []
    while von <= jahre[-1]:
        bis = von + 4
        if any(von <= j <= bis for j in jahre):
            spannen.append((von, bis))
        von += 5
    # Einzeljahre neueste zuerst, Spannen ebenso.
    return sorted(jahre, reverse=True) + sorted(spannen, reverse=True)


def werte_sammeln(eintraege, meta_fn):
    """Welche Werte kommen in DIESER Liste ueberhaupt vor?

    Liefert {feld: [wert, ...]} - sortiert, ohne Leereintraege. Nur was
    vorkommt, steht zur Wahl: eine Genre-Liste mit Eintraegen, die
    danach null Treffer liefern, ist eine Falle.

    eintraege sind die (label, kind, arg)-Tupel des Frontends;
    meta_fn(label) liefert das Metadaten-Dict dazu."""
    genres, jahre, spieler, entwickler = set(), set(), set(), set()
    for eintrag in eintraege:
        if not eintrag or len(eintrag) < 2 or eintrag[1] != "game":
            continue
        meta = meta_fn(eintrag[0]) or {}
        g = genre_kurz(meta.get("genre"))
        if g:
            genres.add(g)
        j = jahr_zahl(meta.get("year"))
        if j:
            jahre.add(j)
        s = spieler_max(meta.get("players"))
        if s:
            spieler.add(s)
        e = (meta.get("developer") or "").strip()
        if e:
            entwickler.add(e)
    return {
        "genre": sorted(genres, key=str.lower),
        # Jahre absteigend: das neueste sucht man oefter als das
        # aelteste, und man landet mit einem Tastendruck dort.
        "jahr": sorted(jahre, reverse=True),
        "spieler": sorted(spieler),
        "entwickler": sorted(entwickler, key=str.lower),
    }


def passt(meta, filter_, ):
    """Erfuellt EIN Eintrag den Filter?

    Ein Feld, das im Filter nicht gesetzt ist, schraenkt nicht ein.
    Ein Eintrag OHNE die gefragte Angabe faellt heraus - wer nach
    "1992" filtert, will keine Spiele ohne Jahresangabe sehen."""
    if not filter_:
        return True
    meta = meta or {}
    wunsch = filter_.get("genre")
    if wunsch and genre_kurz(meta.get("genre")) != wunsch:
        return False
    wunsch = filter_.get("jahr")
    if wunsch:
        j = jahr_zahl(meta.get("year"))
        if isinstance(wunsch, tuple):
            von, bis = wunsch
            if not (j and von <= j <= bis):
                return False
        elif j != wunsch:
            return False
    wunsch = filter_.get("spieler")
    if wunsch and spieler_max(meta.get("players")) < wunsch:
        return False
    wunsch = filter_.get("entwickler")
    if wunsch and (meta.get("developer") or "").strip() != wunsch:
        return False
    return True


def anwenden(eintraege, meta_fn, filter_):
    """Die Liste filtern.

    ORDNER BLEIBEN IMMER DRIN. Ein Filter, der die Navigation
    wegfiltert, sperrt einen in einem Unterordner ein - und Ordner
    haben ohnehin keine Spieledaten, waeren also immer draussen."""
    if not aktiv(filter_):
        return eintraege
    raus = []
    for eintrag in eintraege:
        if not eintrag or len(eintrag) < 2:
            continue
        if eintrag[1] != "game":
            raus.append(eintrag)
            continue
        if passt(meta_fn(eintrag[0]), filter_):
            raus.append(eintrag)
    return raus


def aktiv(filter_):
    """Schraenkt dieser Filter ueberhaupt etwas ein?"""
    return bool(filter_) and any(filter_.get(f) for f in FELDER)


def wert_text(feld, wert, t):
    """Ein Filterwert, wie er auf dem Schirm steht.

    t ist die Uebersetzungsfunktion des Frontends - dieses Modul
    kennt keine festen Texte."""
    if wert is None:
        return t("filter_alle")
    if feld == "jahr" and isinstance(wert, tuple):
        return "%d-%d" % wert
    if feld == "spieler":
        return t("filter_spieler_min", wert)
    return str(wert)


def beschriftung(filter_, t):
    """Kurzfassung fuer die Kopfzeile: "Platform · 1992-1995 · ab 2".

    Leer, wenn nichts eingeschraenkt ist - dann steht in der Kopfzeile
    wie bisher nur die Kategorie."""
    teile = [wert_text(f, filter_.get(f), t)
             for f in FELDER if filter_.get(f)]
    return " / ".join(teile)


def naechster_wert(werte, aktuell, richtung):
    """Einen Schritt durch die Werteliste - mit "alle" (None) als
    erstem Eintrag, damit man den Filter auf demselben Weg wieder
    loswird, auf dem man ihn gesetzt hat.

    Laeuft rundherum: am Ende geht es bei "alle" weiter."""
    kette = [None] + list(werte)
    try:
        i = kette.index(aktuell)
    except ValueError:
        i = 0
    return kette[(i + richtung) % len(kette)]


# ----------------------------------------------------------------------
# GEMERKTE FILTER
#
# Absichtlich ohne Texteingabe: der Name entsteht aus der Bedingung
# ("SNES / Platform / 1990-1994"). Eine Tastatur hat am MiSTer nicht
# jeder, und der Buchstabenwaehler fuer einen Namen waere drei
# Bildschirme fuer etwas, das sich von selbst ergibt.
# ----------------------------------------------------------------------

def name_fuer(kat_name, filter_, t):
    """Der Anzeigename einer gemerkten Kategorie."""
    teile = beschriftung(filter_, t)
    return "%s / %s" % (kat_name, teile) if teile else kat_name


def gemerkte_laden():
    """Die gemerkten Filter, oder eine leere Liste.

    Eine kaputte oder halb geschriebene Datei darf den Start nicht
    umwerfen - dann gibt es eben keine gemerkten Kategorien."""
    import json
    import os
    try:
        if not os.path.exists(KATEGORIEN_DATEI):
            return []
        with open(KATEGORIEN_DATEI, "r", encoding="utf-8") as fh:
            daten = json.load(fh)
        if not isinstance(daten, list):
            return []
        sauber = []
        for e in daten:
            if (isinstance(e, dict) and e.get("name") and e.get("kat")
                    and isinstance(e.get("filter"), dict)):
                # Jahres-Spannen sind in JSON Listen, keine Tupel -
                # zurueckwandeln, sonst schlaegt der Vergleich in
                # passt() fehl und niemand sieht, warum.
                f = dict(e["filter"])
                if isinstance(f.get("jahr"), list) and len(f["jahr"]) == 2:
                    f["jahr"] = tuple(f["jahr"])
                sauber.append({"name": e["name"], "kat": e["kat"],
                               "filter": f})
        return sauber[:KATEGORIEN_MAX]
    except Exception:                                    # noqa: BLE001
        return []


def gemerkte_speichern(liste):
    """Ueber eine .tmp-Datei und os.replace() - ein abgebrochener
    Schreibvorgang darf keine halbe Datei hinterlassen, die beim
    naechsten Start als kaputt gilt und alles verwirft."""
    import json
    import os
    try:
        os.makedirs(os.path.dirname(KATEGORIEN_DATEI), exist_ok=True)
        tmp = KATEGORIEN_DATEI + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(liste[:KATEGORIEN_MAX], fh, ensure_ascii=False)
        os.replace(tmp, KATEGORIEN_DATEI)
        return True
    except Exception:                                    # noqa: BLE001
        return False


def merken(kat_name, filter_, t):
    """Einen Filter als Kategorie merken. Liefert den Namen, oder None
    (nichts zu merken, oder schon vorhanden, oder voll)."""
    if not aktiv(filter_) or not kat_name:
        return None
    name = name_fuer(kat_name, filter_, t)
    liste = gemerkte_laden()
    if any(e["name"] == name for e in liste):
        return None
    if len(liste) >= KATEGORIEN_MAX:
        return None
    liste.append({"name": name, "kat": kat_name, "filter": dict(filter_)})
    return name if gemerkte_speichern(liste) else None


def vergessen(name):
    """Eine gemerkte Kategorie wieder entfernen."""
    liste = gemerkte_laden()
    rest = [e for e in liste if e["name"] != name]
    if len(rest) == len(liste):
        return False
    return gemerkte_speichern(rest)


def ist_gemerkt(name):
    return any(e["name"] == name for e in gemerkte_laden())
