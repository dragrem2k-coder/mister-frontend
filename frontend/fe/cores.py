#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Core-Verwaltung: welcher Core startet ein System? (Build 174)

WARUM ES DAS BRAUCHT

MiSTer legt Cores mit Datum im Dateinamen ab:

    _Console/SNES_20260823.rbf
    _Computer/NeXT_20260908.rbf
    games/NeXT/NeXT_20260911_scsi_dma_csr_fix.rbf
    games/NeXT/NeXT_20260912_recording_adc_fix.rbf
    games/NeXT/NeXT_20260914_moves_fc.rbf

Meistens raeumt update_all die alten weg - aber eben nicht immer.
Beim NeXT-Core liegen im Log eines echten Nutzers vier Fassungen
nebeneinander, mit sprechenden Namen wie "scsi_dma_csr_fix". Wer die
eine braucht, die seinen Fehler behebt, konnte sie bisher nicht
waehlen: das Frontend hat immer den Namen ohne Datum in die .mgl
geschrieben (z.B. "_Console/SNES"), und MiSTer nimmt dann selbst
eine - welche, entscheidet es allein.

Dazu kommen die RA-faehigen Cores (siehe fe/ra_core.py, schon
vorhanden) und Cores, die in einem eigenen Ordner liegen.

WAS DIESES MODUL MACHT - UND WAS NICHT

  macht:   findet alle vorhandenen Fassungen eines Cores, merkt sich
           eine Auswahl je System, loest sie beim Start auf
  macht NICHT: Cores herunterladen oder aktualisieren

Das Aktualisieren ist die Aufgabe von update_all, und die macht es
gut. Es hier noch einmal zu bauen hiesse, eine zweite Quelle der
Wahrheit fuer die wichtigsten Dateien auf der Karte zu schaffen.

DIE SICHERHEITSREGEL, AN DER ALLES HAENGT

    Eine gemerkte Auswahl gilt nur, solange die Datei da ist.

update_all loescht bei jedem Lauf alte Cores ("Removing
/media/fat/_Console/SNES_20260603.rbf" - so stand es im Log des
Nutzers, dutzendfach). Eine gemerkte Auswahl zeigt danach ins Leere.
Wuerde sie trotzdem in die .mgl geschrieben, liesse sich das Spiel
nicht mehr starten - und zwar still, ohne erkennbaren Grund.

Deshalb prueft aufloesen() bei JEDEM Start, ob die gewaehlte Datei
noch existiert, und faellt sonst auf den Standard zurueck. Lieber
der Core, den MiSTer selbst waehlt, als gar keiner.
"""
import glob
import json
import os

BASE = "/media/fat"
WAHL_DATEI = "/media/fat/frontend/core_wahl.json"

# Ordner, in denen Cores liegen koennen - in Suchreihenfolge.
CORE_ORDNER = ("_Console", "_Computer", "_Other", "_Utility", "_Arcade")


def _rbf_pfad(rel):
    """Aus "_Console/SNES" wird "/media/fat/_Console/SNES"."""
    return os.path.join(BASE, rel.replace("/", os.sep))


def core_existiert(rel):
    """Gibt es zu diesem .mgl-Namen ueberhaupt eine Datei?

    MiSTer loest einen Namen OHNE Datum als PRAEFIX auf: aus
    "_Console/SNES" wird die neueste Datei, die so anfaengt. Genau so
    wird hier gesucht - erst die exakte Datei, dann das Praefix.

    WICHTIG ist die Praefix-Falle: "_Console/SNES" wuerde per glob
    auch "SNES_Tracker_2026....rbf" finden. Deshalb muss auf das
    Praefix ein Datum folgen (Unterstrich + Ziffer) oder gleich das
    Dateiende - sonst waehlt eine Auswahl fuer SNES stillschweigend
    den Tracker-Core."""
    if not rel:
        return False
    voll = _rbf_pfad(rel)
    if os.path.exists(voll + ".rbf"):
        return True
    ordner = os.path.dirname(voll)
    name = os.path.basename(voll)
    try:
        for datei in os.listdir(ordner):
            if not datei.lower().endswith(".rbf"):
                continue
            rest = datei[:-4]
            if rest == name:
                return True
            if (rest.startswith(name + "_")
                    and rest[len(name) + 1:len(name) + 2].isdigit()):
                return True
    except OSError:
        pass
    return False


def fassungen(rel):
    """Alle Dateien, die zu diesem Core-Namen gehoeren - neueste
    zuerst.

    Geliefert werden .mgl-taugliche Namen (ohne .rbf, mit Ordner),
    also genau das, was in eine .mgl geschrieben werden kann."""
    if not rel:
        return []
    voll = _rbf_pfad(rel)
    ordner = os.path.dirname(voll)
    name = os.path.basename(voll)
    rel_ordner = os.path.dirname(rel)
    treffer = []
    try:
        for datei in sorted(os.listdir(ordner)):
            if not datei.lower().endswith(".rbf"):
                continue
            rest = datei[:-4]
            if rest == name or (
                    rest.startswith(name + "_")
                    and rest[len(name) + 1:len(name) + 2].isdigit()):
                treffer.append(rel_ordner + "/" + rest if rel_ordner
                               else rest)
    except OSError:
        return []
    # Neueste zuerst: die Datumsangabe steckt im Namen, alphabetisch
    # absteigend ist damit auch chronologisch absteigend.
    return sorted(treffer, reverse=True)


def wahl_laden(pfad=None):
    """Die gemerkten Auswahlen: {Systemschluessel: mgl-Name}.

    Eine kaputte Datei heisst "keine Auswahl", nicht "Absturz" -
    dieselbe Haltung wie bei den gemerkten Filtern und beim eigenen
    Farbschema."""
    try:
        with open(pfad or WAHL_DATEI, "r", encoding="utf-8") as fh:
            daten = json.load(fh)
    except (OSError, ValueError):
        return {}
    if not isinstance(daten, dict):
        return {}
    return {str(k): str(v) for k, v in daten.items()
            if isinstance(v, str) and v}


def wahl_speichern(wahl, pfad=None):
    """Ueber .tmp und os.replace() - eine halb geschriebene Datei
    waere hier besonders unangenehm, weil sie den Core-Start
    betrifft."""
    ziel = pfad or WAHL_DATEI
    ordner = os.path.dirname(ziel)
    if ordner:
        try:
            os.makedirs(ordner, exist_ok=True)
        except OSError:
            pass
    tmp = ziel + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump({k: v for k, v in wahl.items() if v}, fh,
                  indent=1, sort_keys=True)
    os.replace(tmp, ziel)
    return True


def wahl_setzen(syskey, mgl_name, pfad=None):
    """Eine Auswahl merken - oder mit None wieder loeschen."""
    wahl = wahl_laden(pfad)
    if mgl_name:
        wahl[syskey] = mgl_name
    else:
        wahl.pop(syskey, None)
    wahl_speichern(wahl, pfad)
    return wahl


def aufloesen(syskey, standard_rbf, pfad=None):
    """WELCHER CORE STARTET? Die eine Funktion, die der Startweg ruft.

    Liefert IMMER einen brauchbaren Namen:

      1. die gemerkte Auswahl - aber nur, wenn ihre Datei noch da ist
      2. sonst der Standard aus der Systemtabelle

    Punkt 1 ist die ganze Sicherheitsregel dieses Moduls. update_all
    loescht bei jedem Lauf alte Cores; eine gemerkte Auswahl zeigt
    danach ins Leere. Ohne diese Pruefung liesse sich das Spiel
    danach nicht mehr starten, und zwar ohne erkennbaren Grund.

    Auch der Standard wird NICHT geprueft: fehlt der ebenfalls, kann
    dieses Modul nichts mehr retten, und ein unveraendertes Verhalten
    ist besser als eine eigene Fehlermeldung an einer Stelle, die es
    bisher nicht gab."""
    if not syskey:
        return standard_rbf
    gewaehlt = wahl_laden(pfad).get(syskey)
    if gewaehlt and gewaehlt != standard_rbf and core_existiert(gewaehlt):
        return gewaehlt
    return standard_rbf


def uebersicht(systeme, auch_ohne=False):
    """Was ist da? [(Anzeigename, syskey, standard, [Fassungen])]

    systeme ist die Liste aus fe/systems.py.

    OHNE auch_ohne werden nur Systeme geliefert, von denen UEBERHAUPT
    ein Core auf der Karte liegt - das war bis Build 311 die einzige
    Betriebsart, und sie ist fuer die Wahl der Fassung richtig: eine
    Liste mit fuenfzig Eintraegen, von denen zwei existieren, waere
    keine Uebersicht.

    MIT auch_ohne (Build 312) kommen die anderen mit, und zwar mit
    einer LEEREN Fassungsliste. Sein Wunsch vom 08.11.: "Fehlende oder
    inkompatible Cores erkennen" - und das geht nur, wenn die
    Uebersicht die Luecken auch zeigt. Welche der beiden Betriebsarten
    gilt, entscheidet der Aufrufer; eine Liste, die mal so und mal so
    aussieht, waere an beiden Stellen falsch."""
    raus = []
    for eintrag in systeme:
        name, syskey, _ordner, rbf = eintrag[0], eintrag[1], eintrag[2], eintrag[3]
        alle = fassungen(rbf)
        if alle or auch_ohne:
            raus.append((name, syskey, rbf, alle))
    return raus


def ra_fassung(syskey):
    """Die RA-faehige Fassung dieses Systems, oder None.

    GEFRAGT WIRD fe/ra_core.py, NICHT NACHGEBAUT. Dort steht die
    Namensliste von sage2050s Werkzeug samt der ehrlichen Anmerkung,
    dass sie fuer manche Systeme geraten ist - und dort steht auch die
    Regel "der erste tatsaechlich EXISTIERENDE Treffer gewinnt". Diese
    Liste hier ein zweites Mal zu fuehren hiesse, sie beim naechsten
    neuen System an zwei Stellen zu pflegen.

    Der Import steht ABSICHTLICH in der Funktion: fe/ra_core.py ist
    eigenstaendig (nur os), aber fe/cores.py wird sehr frueh geladen,
    und eine Abhaengigkeit, die nur eine Anzeige braucht, gehoert
    nicht in den Startweg."""
    if not syskey:
        return None
    try:
        import fe.ra_core as _RA
        treffer = _RA.find_ra_core(syskey)
    except Exception:                                    # noqa: BLE001
        return None
    return treffer[0] if treffer else None


def bestand_cores(systeme):
    """Die Kopfzahlen der Core-Verwaltung (Build 312).

    {"systeme", "mit_core", "mehrere", "ohne", "ra"}

    `ohne` ist die Zahl, die seinen Wunsch beantwortet: zu so vielen
    Systemen liegt KEIN Core auf der Karte."""
    alle = uebersicht(systeme, auch_ohne=True)
    mit = [e for e in alle if e[3]]
    return {"systeme": len(alle),
            "mit_core": len(mit),
            "mehrere": len([e for e in mit if len(e[3]) > 1]),
            "ohne": len(alle) - len(mit),
            "ra": len([e for e in alle if ra_fassung(e[1])])}


# ===========================================================================
# BUILD 310: EINE FASSUNG FUER GENAU EIN SPIEL
# ===========================================================================
#
# NUTZERWUNSCH vom 08.11., und er steht in seiner Prioritaetenliste
# ausdruecklich als der wichtigste Punkt des wichtigsten Bereichs:
#
#     "Besonders wichtig: Core-Auswahl pro Spiel, damit beispielsweise
#      ein bestimmtes Spiel mit einer anderen Core-Version gestartet
#      werden kann."
#
# WARUM DAS NICHT DASSELBE IST WIE DIE WAHL JE SYSTEM. Der Kopf dieser
# Datei nennt den Fall, aus dem das Modul ueberhaupt entstanden ist:
# beim NeXT-Core liegen vier Fassungen nebeneinander, mit sprechenden
# Namen wie "scsi_dma_csr_fix". Wer die eine braucht, die SEINEN Fehler
# behebt, musste bisher das ganze System darauf umstellen - und damit
# auch alle anderen Spiele, bei denen genau diese Fassung vielleicht
# etwas anderes kaputtmacht. Die Wahl je System bleibt die richtige
# Antwort fuer den Normalfall; die Wahl je Spiel ist die Antwort fuer
# die Ausnahme.
#
# DER SCHLUESSEL IST DER ROM-PFAD, nicht der Anzeigename. Zwei Spiele
# koennen in zwei Systemen gleich heissen ("Pac-Man" gibt es auf jeder
# Maschine), und der Anzeigename haengt ausserdem an den
# Namensregeln aus fe/naming.py - aendert der Nutzer dort etwas,
# zeigte eine namensbasierte Wahl ins Leere, ohne dass es jemand
# merkt. Der Pfad ist eindeutig und aendert sich nur, wenn die Datei
# wirklich umzieht; dann faellt die Wahl sauber auf die Systemwahl
# zurueck, und das ist das richtige Verhalten.
#
# DIE SICHERHEITSREGEL AUS aufloesen() GILT UNVERAENDERT: eine
# gemerkte Fassung gilt nur, solange ihre Datei da ist. Sie steht
# nicht zweimal hier - aufloesen_spiel() ruft aufloesen(), statt die
# Pruefung nachzubauen.

SPIEL_WAHL_DATEI = "/media/fat/frontend/core_wahl_spiel.json"


def spiel_wahl_laden(pfad=None):
    """Die gemerkten Auswahlen je Spiel: {ROM-Pfad: mgl-Name}.

    Eine kaputte Datei heisst "keine Auswahl", nicht "Absturz" -
    dieselbe Haltung wie bei wahl_laden()."""
    try:
        with open(pfad or SPIEL_WAHL_DATEI, "r", encoding="utf-8") as fh:
            daten = json.load(fh)
    except (OSError, ValueError):
        return {}
    if not isinstance(daten, dict):
        return {}
    return {str(k): str(v) for k, v in daten.items()
            if isinstance(v, str) and v}


def spiel_wahl_speichern(wahl, pfad=None):
    """Ueber .tmp und os.replace() - wie wahl_speichern(), und aus
    demselben Grund: eine halb geschriebene Datei betrifft den
    Core-Start."""
    ziel = pfad or SPIEL_WAHL_DATEI
    ordner = os.path.dirname(ziel)
    if ordner:
        try:
            os.makedirs(ordner, exist_ok=True)
        except OSError:
            pass
    tmp = ziel + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump({k: v for k, v in wahl.items() if v}, fh,
                  indent=1, sort_keys=True)
    os.replace(tmp, ziel)
    return True


def spiel_wahl_setzen(spielpfad, mgl_name, pfad=None):
    """Eine Auswahl fuer EIN Spiel merken - oder mit None loeschen."""
    if not spielpfad:
        return spiel_wahl_laden(pfad)
    wahl = spiel_wahl_laden(pfad)
    if mgl_name:
        wahl[str(spielpfad)] = mgl_name
    else:
        wahl.pop(str(spielpfad), None)
    spiel_wahl_speichern(wahl, pfad)
    return wahl


def spiel_wahl_holen(spielpfad, pfad=None):
    """Was ist fuer dieses Spiel gemerkt? None heisst "nichts".

    Gibt den gemerkten Namen auch dann zurueck, wenn die Datei nicht
    mehr existiert - das braucht der Auswahlbildschirm, um "gewaehlt,
    aber fehlt" anzeigen zu koennen. Der STARTWEG nimmt dagegen
    aufloesen_spiel(), und die prueft."""
    if not spielpfad:
        return None
    return spiel_wahl_laden(pfad).get(str(spielpfad))


def aufloesen_spiel(spielpfad, syskey, standard_rbf, pfad=None,
                    spiel_datei=None):
    """WELCHER CORE STARTET DIESES SPIEL? (Build 310)

    Die Reihenfolge, und sie ist die ganze Funktion:

      1. die Wahl fuer GENAU DIESES SPIEL - wenn ihre Datei noch da ist
      2. sonst alles, was aufloesen() sagt (Systemwahl, dann Standard)

    Punkt 2 ruft aufloesen() und baut es NICHT nach. Die
    Sicherheitsregel - eine gemerkte Auswahl gilt nur, solange die
    Datei existiert - steht damit weiterhin an genau einer Stelle;
    eine zweite Fassung waere eine zweite Gelegenheit, sie zu
    vergessen (in Build 298 ist genau das fuenfmal passiert).

    Der RA-Core hat auch weiterhin Vorrang vor allem hier: er wird im
    Startweg VOR dieser Funktion entschieden, weil er ausdruecklich
    gewaehlt wurde."""
    if spielpfad:
        gewaehlt = spiel_wahl_laden(spiel_datei).get(str(spielpfad))
        if gewaehlt and core_existiert(gewaehlt):
            return gewaehlt
    return aufloesen(syskey, standard_rbf, pfad)
