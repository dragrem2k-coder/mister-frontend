#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Persistenter Spielstatus pro Nutzer: Durchgespielt-Markierung,
"Zuletzt gespielt", Favoriten, zuletzt tatsaechlich verwendete Core-
Wahl pro Spiel. Ausgelagert aus frontend.py (Modularisierung, Git-
Branch 'modular-refactor').

Drei ehemals GETRENNTE Bloecke aus dem Original hier zusammengefuehrt
(Durchgespielt-Tracking lag deutlich frueher im Code als der
Hauptblock Zuletzt-gespielt/Favoriten/Core-Wahl) - gehoeren inhaltlich
klar zusammen (alles "kleine, persistente Datei pro Spiel-Eigenschaft").

BASE wird hier bewusst noch einmal definiert (nicht importiert) -
frontend.py selbst braucht denselben Wert AUCH noch fuer scan_cores()
(bleibt dort, Teil des noch nicht ausgelagerten Scan-Clusters). Ein
Import waere hier nicht moeglich gewesen (frontend.py laeuft als
Hauptskript, nicht als benanntes, importierbares Modul - ein
Ruecksfall-Import haette einen Zirkelbezug ausgeloest). Da BASE ein
fester, nie neu zugewiesener Pfad ist, ist eine zweite, identische
Definition hier unproblematisch (kein Synchronisierungsrisiko wie bei
CURRENT_LANG/C_BG/VOLUME/GAMES_BASES).
"""
import os, glob, re, json
from fe.log import LOG

BASE = "/media/fat"
RECENT_FILE = "/media/fat/frontend/recently_played.json"
# Nutzerwunsch (Rueckmeldung: "Zuletzt gespielt" zeigte nicht wirklich
# alle zuletzt gespielten Spiele) - von 15 auf 100 angehoben, damit die
# Liste bei aktiver Nutzung nicht schon nach wenigen Sitzungen aeltere
# Spiele stillschweigend verdraengt.
RECENT_MAX = 100
FAVORITES_FILE = "/media/fat/frontend/favorites.json"
LAST_CORE_CHOICE_FILE = "/media/fat/frontend/last_core_choice.json"

COMPLETED_FILE = "/media/fat/frontend/completed.json"

def _load_completed_raw():
    """Menge der als 'durchgespielt' markierten Spiele (per Name,
    gleiche Konvention wie Favoriten/Zuletzt gespielt)."""
    try:
        with open(COMPLETED_FILE) as f:
            data = json.load(f)
            return set(data) if isinstance(data, list) else set()
    except (OSError, ValueError):
        return set()

def toggle_completed(label):
    """Durchgespielt-Status umschalten. Rueckgabe: True, wenn jetzt
    als durchgespielt markiert, sonst False."""
    if not label:
        return False
    data = _load_completed_raw()
    if label in data:
        data.discard(label)
        now_completed = False
    else:
        data.add(label)
        now_completed = True
    try:
        os.makedirs(os.path.dirname(COMPLETED_FILE), exist_ok=True)
        with open(COMPLETED_FILE, "w") as f:
            json.dump(sorted(data), f)
    except OSError:
        pass
    return now_completed

RECENT_MARKER = ".frontend_recent"   # Marker-Datei, mit der ein externes
                            # Skript (z.B. TheRealSutefans "Recently
                            # Played"-Skript) einen _*-Ordner als Quelle
                            # kennzeichnet - siehe find_marked_recent_dir().

def _folder_items(d, by_mtime=False):
    """Startbare Items (.mra/.rbf/.mgl) eines _*-Ordners - wie scan_cores
    sie baut. Ausgelagert, damit auch der markierte Recently-Ordner
    dieselbe Logik nutzt.

    by_mtime=True sortiert nach Datei-mtime absteigend (neueste zuerst) -
    fuer den markierten "Zuletzt gespielt"-Ordner, dessen Skript die
    mtimes auf die jeweilige Spielzeit stempelt. Bei gleichen mtimes
    (Skript ohne Zeitstempel) faellt es auf alphabetisch zurueck."""
    files = (glob.glob(os.path.join(d, "*.mra")) +
             glob.glob(os.path.join(d, "*.rbf")) +
             glob.glob(os.path.join(d, "*.mgl")))
    if by_mtime:
        def _key(f):
            try:
                mt = os.path.getmtime(f)
            except OSError:
                mt = 0
            return (-mt, os.path.basename(f).lower())
        files = sorted(files, key=_key)
    else:
        files = sorted(files)
    items = []
    for f in files:
        name = os.path.splitext(os.path.basename(f))[0]
        name = re.sub(r"_\d{8}[a-zA-Z]?$", "", name)
        items.append((name, "core", f))
    return items

def find_marked_recent_dir():
    """Den _*-Ordner suchen, den ein externes Skript per RECENT_MARKER
    als Zuletzt-gespielt-Quelle kennzeichnet. Gibt den Pfad zurueck oder
    None. Ueber den Marker unabhaengig vom Ordnernamen - der ist im
    externen Skript frei konfigurierbar. Ohne ein solches Skript
    (Normalfall) existiert kein Marker irgendwo - diese Funktion liefert
    dann einfach None, und alles verhaelt sich wie bisher."""
    for d in sorted(glob.glob(os.path.join(BASE, "_*"))):
        if os.path.isdir(d) and os.path.exists(os.path.join(d, RECENT_MARKER)):
            return d
    return None

def load_recent():
    """Liste der zuletzt gespielten Spiele laden - Rueckgabe im
    gleichen (label, kind, arg)-Format wie normale Kategorie-Eintraege,
    direkt startbar. Leere Liste, wenn noch nie etwas gestartet wurde
    oder die Datei fehlt/beschaedigt ist."""
    try:
        with open(RECENT_FILE) as f:
            data = json.load(f)
        return [(e["label"], "game", e["arg"]) for e in data]
    except (OSError, ValueError, KeyError, TypeError):
        return []

def _bare_game_name(label):
    """Loest aus einer Zuletzt-gespielt-Beschriftung den reinen
    Spielnamen heraus - fuer externe Listen (siehe find_marked_recent_
    dir()), deren Eintraege ein Core-/RA-Praefix vorne dran haben
    (z.B. TheRealSutefans "RA SNES - Chrono Trigger", Format
    "<Anzeige> - <Spielname>" mit dem Spielnamen NACH dem ERSTEN
    " - "). Ohne " - " im Label wird das Label unveraendert
    zurueckgegeben (unsere eigene load_recent()-Liste hat kein
    Praefix, braucht diese Behandlung also nicht)."""
    return label.split(" - ", 1)[1] if " - " in label else label

def find_continue_game():
    """Sucht das zuletzt gespielte Spiel, das noch NICHT als
    durchgespielt markiert ist - fuer die "Weiterspielen"-Vorschlag
    ganz oben im Hauptmenue (Nutzerwunsch: "genau hier bist du stehen-
    geblieben" statt nur eine chronologische Liste). Liefert (label,
    "game"/"core", arg) oder None, wenn nichts passt (z.B. alles
    bereits durchgespielt markiert, oder noch nie etwas gestartet).

    Bevorzugt die ueber RECENT_MARKER eingebundene externe Liste
    (TheRealSutefans "Last Played"-Skript), FALLS vorhanden - MiSTers
    eigene *_recent_1.cfg-Dateien erfassen JEDEN Spielstart, egal ob
    ueber unser Frontend, MiSTers eigenes Menue oder ein anderes Tool.
    Unsere eigene load_recent()-Liste kennt dagegen nur, was ueber
    UNSER Frontend gestartet wurde - waere sonst zunehmend veraltet
    gegenueber der darunter angezeigten "Zuletzt gespielt"-Liste,
    sobald ein solches externes Skript aktiv ist.

    WICHTIG beim Abgleich gegen die Durchgespielt-Markierung: die
    externe Liste hat Core-/RA-Praefixe im Label (z.B. "RA SNES -
    Chrono Trigger"), unsere Markierung speichert aber den REINEN
    Spielnamen ("Chrono Trigger") - ein direkter Vergleich wuerde nie
    treffen. Siehe _bare_game_name() fuer die Praefix-Behandlung.
    Ohne aktiven Marker unveraendert unsere eigene load_recent()."""
    completed = _load_completed_raw()
    marked_recent = find_marked_recent_dir()
    if marked_recent:
        for entry in _folder_items(marked_recent, by_mtime=True):
            if _bare_game_name(entry[0]) not in completed:
                return entry
        return None
    for entry in load_recent():
        label = entry[0]
        if label not in completed:
            return entry
    return None

def _recent_syskey(arg):
    """Systemschluessel aus einem (rom, ext, syskey, rbf, (dl, ft, ix))-
    Argument - defensiv, falls arg mal kuerzer/anders geformt ist."""
    return arg[2] if len(arg) > 2 else None

def record_recent(label, arg):
    """Ein gestartetes Spiel oben in die 'Zuletzt gespielt'-Liste
    einreihen (Duplikate werden nach oben verschoben statt doppelt zu
    erscheinen - Erkennung ueber den Namen, nicht ueber arg: nach
    einer JSON-Speicherrunde werden verschachtelte Tupel zu Listen,
    ein direkter Tupel-Vergleich wuerde also nie zutreffen), auf
    RECENT_MAX Eintraege gekappt.

    BUGFIX (Nutzer-Rueckmeldung: "Zuletzt gespielt" zeigte nicht
    wirklich alle zuletzt gespielten Spiele an): die Duplikat-Erkennung
    verglich bisher NUR den Anzeigenamen - zwei gleichnamige Spiele auf
    UNTERSCHIEDLICHEN Systemen (z.B. "Sonic the Hedgehog" auf Mega
    Drive UND Master System) galten dadurch als ein und dasselbe:
    startete man das eine, verschwand der Eintrag des anderen
    ersatzlos aus der Liste, statt dass beide nebeneinander stehen.
    Jetzt zusaetzlich der Systemschluessel (arg[2]) mit in den
    Vergleich - nur wirklich dasselbe Spiel auf demselben System wird
    noch als Duplikat nach oben verschoben."""
    try:
        with open(RECENT_FILE) as f:
            data = json.load(f)
    except (OSError, ValueError):
        data = []
    syskey = _recent_syskey(arg)
    data = [e for e in data if not (e.get("label") == label
                                     and _recent_syskey(e.get("arg") or []) == syskey)]
    data.insert(0, {"label": label, "arg": list(arg)})
    data = data[:RECENT_MAX]
    try:
        os.makedirs(os.path.dirname(RECENT_FILE), exist_ok=True)
        with open(RECENT_FILE, "w") as f:
            json.dump(data, f)
    except OSError:
        pass

def _load_favorites_raw():
    try:
        with open(FAVORITES_FILE) as f:
            return json.load(f)
    except (OSError, ValueError):
        return []

def load_favorites():
    """Favoriten laden - selbes (label, kind, arg)-Format wie
    load_recent(), direkt als eigene Kategorie nutzbar. Reihenfolge:
    zuletzt hinzugefuegt zuerst (wie bei 'Zuletzt gespielt'), aber OHNE
    Obergrenze - Favoriten sind eine bewusste, dauerhafte Auswahl,
    keine automatische Verlaufsliste."""
    return [(e["label"], "game", e["arg"]) for e in _load_favorites_raw()
            if "label" in e and "arg" in e]

def is_favorite(label):
    """Ob ein Spiel (per Name) aktuell als Favorit markiert ist - fuer
    die kleine Markierung in der Liste."""
    return any(e.get("label") == label for e in _load_favorites_raw())

def toggle_favorite(label, arg):
    """Favoritenstatus eines Spiels umschalten (per Name erkannt,
    genau wie bei 'Zuletzt gespielt' - aus demselben Grund: nach dem
    Speichern sind es Listen, kein direkter Tupel-Vergleich moeglich).
    Rueckgabe: True, wenn jetzt Favorit ist, sonst False."""
    data = _load_favorites_raw()
    if any(e.get("label") == label for e in data):
        data = [e for e in data if e.get("label") != label]
        now_fav = False
    else:
        data.insert(0, {"label": label, "arg": list(arg)})
        now_fav = True
    try:
        os.makedirs(os.path.dirname(FAVORITES_FILE), exist_ok=True)
        with open(FAVORITES_FILE, "w") as f:
            json.dump(data, f)
    except OSError:
        pass
    return now_fav

# NEUES FEATURE (Nutzer-Rueckfrage: "werden bei Weiterspielen und
# Zuletzt gespielt auch die richtigen Cores fuer die Spiele verwendet,
# womit sie zuletzt gestartet wurden?"): Antwort war NEIN - die
# bisherige Core-Wahl (Standard/RA) wurde nur SITZUNGS-lokal in
# self._ra_core_choice gemerkt, und zwar pro SYSTEM (z.B. "SNES"),
# nicht pro einzelnem Spiel, UND nur, wenn die echte Kategorie in
# DERSELBEN Sitzung schon einmal betreten wurde - startete man ein
# Spiel direkt aus "Weiterspielen"/"Zuletzt gespielt" heraus, griff
# das oft gar nicht, es lief still (und ohne Nachfrage) der
# Standard-Core, selbst wenn das Spiel zuletzt mit RA gestartet wurde.
#
# Fix: zusaetzlich zur bestehenden Sitzungs-Erinnerung eine
# PERSISTIERTE, pro einzelnem Spiel (nach Name) gespeicherte "zuletzt
# tatsaechlich verwendete Core-Wahl" - ueberlebt einen Neustart. Wird
# in der Hauptschleife als Rueckfallebene genutzt, wenn fuer das
# aktuelle System in DIESER Sitzung noch keine frische Wahl getroffen
# wurde (siehe Kommentar dort). Favoriten fragen bewusst IMMER neu
# (siehe dort) und nutzen diese Datei nur zum Schreiben, nicht zum
# Lesen.
def load_last_core_choice(label):
    """(rbf, setname) oder None - die zuletzt fuer GENAU DIESES Spiel
    (nach Namen) tatsaechlich verwendete Core-Wahl. None bedeutet
    sowohl "noch nie erfasst" als auch "zuletzt bewusst Standard-Core
    gewaehlt" - in beiden Faellen ist das Ergebnis (Standard-Core
    verwenden) identisch, die Unterscheidung waere ohne Nutzen."""
    try:
        with open(LAST_CORE_CHOICE_FILE) as f:
            data = json.load(f)
        v = data.get(label)
        return tuple(v) if v else None
    except (OSError, ValueError, AttributeError, TypeError):
        return None

def record_core_choice(label, ra_choice):
    """Speichert, welche Core-Wahl (ra_choice: (rbf, setname) oder
    None fuer Standard) beim letzten tatsaechlichen Start dieses
    Spiels verwendet wurde."""
    try:
        with open(LAST_CORE_CHOICE_FILE) as f:
            data = json.load(f)
    except (OSError, ValueError):
        data = {}
    data[label] = list(ra_choice) if ra_choice else None
    try:
        os.makedirs(os.path.dirname(LAST_CORE_CHOICE_FILE), exist_ok=True)
        with open(LAST_CORE_CHOICE_FILE, "w") as f:
            json.dump(data, f)
    except OSError:
        pass
