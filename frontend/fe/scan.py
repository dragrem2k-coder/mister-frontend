#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kern des ROM-Scans: Cores durchsuchen, Ordnerbaeume aufbauen,
Cache-Verwaltung (Pickle), USB-/Netzwerk-Bereitschaft abwarten.
Ausgelagert aus frontend.py (Modularisierung, Git-Branch
'modular-refactor').

BASE, SKIP_DIRS, GAMES_CACHE, GAMES_CACHE_OLD_JSON hierher verschoben
(waren vorher an frontend.py-Stellen definiert, die NUR von diesem
Bereich gebraucht wurden - reine Verschiebung, keine Duplikate noetig,
siehe Namensabgleich beim Commit).

GAMES_BASES kommt aus fe.paths (siehe dortiger Modul-Kommentar zur
Einfrier-Falle) - modul-qualifizierter Zugriff, nicht per direktem
Import. _wait_for_network_ready() haelt fe.paths.GAMES_BASES bei
jeder Neuermittlung synchron.
"""
import os, glob, re, time, pickle, socket
from fe.log import LOG
from fe.systems import (GAME_SYSTEMS, OPTIONAL_GAME_SYSTEMS,
                        optional_core_file)
from fe.naming import IGNORE_ROM_BASENAMES, JUNK_TAGS, REGION_PRIORITY, nice_name, _is_junk, _is_japan_only
from fe.game_state import _folder_items
import fe.paths

BASE = "/media/fat"
SKIP_DIRS = {"_Scripts"}
GAMES_CACHE = "/media/fat/frontend/games_cache.pkl"
GAMES_CACHE_OLD_JSON = "/media/fat/frontend/games_cache.json"

def _has_network():
    """Prueft, ob irgendein Netzwerk-Interface eine Adresse hat -
    ueber den klassischen 'UDP connect'-Trick: verbindet einen UDP-
    Socket zu einer beliebigen externen Adresse (verschickt dabei
    KEIN einziges Paket, UDP-connect() ist rein lokales Routing) und
    schaut, welche lokale Adresse das Betriebssystem dafuer waehlen
    wuerde. Funktioniert auch ohne echten Internetzugang, solange das
    lokale Netzwerk (WLAN/LAN) steht - genau das, wonach gefragt war,
    nicht ob das Internet erreichbar ist."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return bool(ip) and not ip.startswith("127.")
    except OSError:
        return False

def _arcade_folder_tree(path):
    """Wie _folder_items(), aber REKURSIV - nur fuer den Arcade-Ordner
    gedacht (siehe scan_cores() unten).

    NEU (Nutzerfrage: "wenn ich ueber das OSD auf Arcade gehe werden
    mir noch Ordner angezeigt 'alternatives' 'insert Coin' 'organized'
    'st-v' - warum sehe ich diese nicht im Frontend?"): kuratierte
    Arcade-Sammlungen legen ihre .mra-Dateien haeufig NICHT direkt in
    _Arcade/ ab, sondern in frei benannten Unterordnern zur eigenen
    Organisation (nach Hersteller/Board/Status usw.) - MiSTers eigenes
    OSD durchsucht Ordner ganz normal rekursiv, zeigt diese Unterordner
    also anstandslos an. _folder_items() (bisher fuer Arcade genutzt,
    siehe scan_cores()) macht dagegen bewusst nur einen FLACHEN
    glob() OHNE Rekursion - alles, was nicht DIREKT in _Arcade/ selbst
    liegt, blieb dadurch fuers Frontend unsichtbar, ganz ohne
    Fehlermeldung. Baut - genau wie _scan_folder_tree() fuer die
    regulaeren Spielesysteme (siehe dort) - einen beliebig tief
    verschachtelten Baumknoten, der die eigene Ordnerstruktur 1:1
    widerspiegelt, damit Unterordner im Frontend genauso als eigene,
    oeffenbare Eintraege erscheinen wie im OSD. Bewusst NUR fuer Arcade
    eingefuehrt - die anderen generischen _*-Core-Ordner (Console/
    Computer/Utility/...) bleiben unveraendert flach, dort ist eine
    tiefe Ordnerorganisation in der Praxis kaum gebraeuchlich."""
    node = _empty_node()
    try:
        entries = sorted(os.listdir(path), key=str.lower)
    except OSError:
        return node
    files = []
    for entry in entries:
        if entry.startswith("."):
            continue
        full = os.path.join(path, entry)
        if os.path.isdir(full):
            sub = _arcade_folder_tree(full)
            if sub["folders"] or sub["items"]:
                node["folders"][entry] = sub
        else:
            ext = os.path.splitext(entry)[1].lower()
            if ext in (".mra", ".rbf", ".mgl"):
                files.append(full)
    items = []
    for f in sorted(files, key=lambda p: os.path.basename(p).lower()):
        name = os.path.splitext(os.path.basename(f))[0]
        name = re.sub(r"_\d{8}[a-zA-Z]?$", "", name)
        items.append((name, "core", f))
    node["items"] = items
    return node

# BUGFIX/PERFORMANCE (Nutzer-Rueckmeldung: "warum braucht das Frontend
# nach dem letzten Update jetzt solange zum starten??? das ist sehr
# schlecht!"): direkte, selbst verschuldete Folge der Arcade-Unterordner-
# Rekursion von eben. _arcade_folder_tree() durchsucht den KOMPLETTEN
# Ordnerbaum - bei einer grossen, tief organisierten Arcade-Sammlung
# (Hersteller-/Board-/Status-Unterordner wie "alternatives"/"organized"/
# "ST-V", oft mehrere Tausend .mra-Dateien in Dutzenden Unterordnern)
# potenziell viele einzelne os.listdir()-Aufrufe. Eigene Messung dazu:
# rein in dieser Sandbox (RAM statt SD-Karte) bereits ca. 22x teurer als
# der alte flache Scan bei ~3000 Dateien/97 Ordnern - auf echter SD-
# Karten-Hardware (siehe fruehere, aehnliche Messung zu kalten Cover-
# Verzeichnissen: ueber 1000ms fuer EIN einziges os.listdir()) faellt der
# Unterschied erfahrungsgemaess noch deutlich staerker aus. Und anders
# als scan_games() (siehe GAMES_CACHE/_games_signature() oben - dort
# laengst eine ausgereifte Mtime-Signatur+Pickle-Cache-Loesung) hatte
# scan_cores() BISHER UEBERHAUPT KEINEN Cache - lief bei jedem einzelnen
# build_categories()-Aufruf (JEDEN Boot, JEDEN manuellen/automatischen
# Kategorien-Neuaufbau) komplett frisch von der Platte. Das war bisher
# harmlos, weil der alte, flache Arcade-Scan nur EINEN einzigen
# os.listdir()-Aufruf kostete - durch die Rekursion jetzt nicht mehr.
#
# Fix: genau dieselbe Grund-Idee wie bei _games_signature() (siehe
# dortiger Kommentar) - ein SCHNELLER, flacher Fingerabdruck (nur die
# eigene Mtime des _Arcade-Ordners selbst, kein tieferer Baumdurchlauf
# dafuer) genuegt, um zu erkennen, ob sich an der OBERSTEN Ebene etwas
# getan hat (neuer/entfernter Ordner oder neue/entfernte Datei DIREKT in
# _Arcade/). Passt der Fingerabdruck noch zum letzten Cache-Eintrag,
# wird der bereits fertige Baum aus dem Pickle-Cache uebernommen, KEIN
# erneuter Rekursions-Durchlauf. EHRLICH DOKUMENTIERTE, bewusst in Kauf
# genommene Einschraenkung (identisch zu scan_games()s eigener, laengst
# akzeptierter Grenze): eine Aenderung TIEF in einem bereits bestehenden
# Unterordner (z.B. eine neue .mra-Datei in "organized/Capcom/", ohne
# dass sich "organized" selbst oder _Arcade/ selbst aendert) aendert
# unter Linux NICHT die Mtime des Elternordners - wird dadurch nicht
# automatisch erkannt, genau wie bei allen anderen Systemen auch. Ein
# manueller Rescan (System -> Wartung -> "Spieleliste neu einlesen",
# force=True) erzwingt in dem Fall wie gewohnt einen vollstaendigen
# Neuaufbau.
ARCADE_TREE_CACHE = "/media/fat/frontend/arcade_tree_cache.pkl"

def _load_arcade_tree_cache():
    try:
        with open(ARCADE_TREE_CACHE, "rb") as f:
            data = pickle.load(f)
            return data if isinstance(data, dict) else {}
    except (OSError, ValueError, EOFError, pickle.UnpicklingError,
            KeyError, AttributeError):
        return {}

def _save_arcade_tree_cache(data):
    try:
        os.makedirs(os.path.dirname(ARCADE_TREE_CACHE), exist_ok=True)
        with open(ARCADE_TREE_CACHE, "wb") as f:
            pickle.dump(data, f)
    except OSError:
        pass

def _arcade_tree_cached(path, force=False):
    """_arcade_folder_tree(path), aber mit Mtime-Signatur-Cache (siehe
    ausfuehrliche Begruendung oben) - baut den Baum nur dann wirklich
    neu auf, wenn sich die Mtime von 'path' selbst seit dem letzten
    Aufruf geaendert hat, oder force=True (manueller Rescan)."""
    try:
        sig = int(os.path.getmtime(path))
    except OSError:
        sig = None
    if not force:
        cached = _load_arcade_tree_cache()
        if cached.get("path") == path and cached.get("sig") == sig:
            return cached.get("node", _empty_node())
    node = _arcade_folder_tree(path)
    _save_arcade_tree_cache({"path": path, "sig": sig, "node": node})
    return node

def scan_cores(skip_dir=None, force=False):
    """Alle /media/fat/_*-Ordner nach .rbf/.mra/.mgl durchsuchen.
    skip_dir wird ausgelassen (der markierte Recently-Ordner, der bereits
    separat als "Zuletzt gespielt" gefuehrt wird - sonst doppelt).

    GEAENDERT: liefert fuer den Arcade-Ordner jetzt einen echten,
    rekursiven Baumknoten (siehe _arcade_folder_tree()/_arcade_tree_
    cached()) statt einer flachen Liste - Unterordner wie "alternatives"/
    "organized"/"ST-V" werden dadurch sichtbar, per Mtime-Signatur-Cache
    OHNE bei jedem Aufruf neu von der Platte zu lesen (siehe Kommentar
    dort). Alle anderen _*-Ordner liefern weiterhin eine flache Liste
    wie bisher, der Aufrufer (Frontend._partition_core_cats())
    unterscheidet anhand des Rueckgabetyps (dict = bereits fertiger
    Baumknoten, Liste = wie bisher noch in _wrap_flat() zu verpacken).

    force=True (manueller Rescan) erzwingt fuer Arcade einen
    vollstaendigen Neuaufbau des Baums, ignoriert also einen eventuell
    noch passenden Cache-Eintrag."""
    cats = []
    skip_real = os.path.realpath(skip_dir) if skip_dir else None
    for d in sorted(glob.glob(os.path.join(BASE, "_*"))):
        if not os.path.isdir(d) or os.path.basename(d) in SKIP_DIRS:
            continue
        if skip_real and os.path.realpath(d) == skip_real:
            continue
        # Arcade-Ordner bekommen ein Info-Panel (MRA-Metadaten)
        base = os.path.basename(d).lstrip("_").lower()
        syskey = "ARCADE" if "arcade" in base else None
        if syskey == "ARCADE":
            node = _arcade_tree_cached(d, force=force)
            if node["folders"] or node["items"]:
                cats.append((nice_name(os.path.basename(d)), node, syskey))
            continue
        # .mgl mit aufnehmen: so tauchen MGL-Shortcut-Ordner (z.B. das
        # "Recently Played"-Skript) auf und sind direkt startbar - der
        # Start-Pfad (load_core) verarbeitet .mgl genauso wie .rbf/.mra.
        items = _folder_items(d)
        if items:
            cats.append((nice_name(os.path.basename(d)), items, syskey))
    return cats

# BUGFIX (Nutzer-Rueckmeldung anhand einer echten Verzeichnisliste mit
# 3202 Dateien: "es werden immer noch nur zwei Spiele angezeigt" - TROTZ
# des vorherigen (unl)/(pirate)-Fixes): _games_signature() (siehe unten)
# ist bewusst NUR ein schneller Fingerabdruck basierend auf Ordner-
# Aenderungszeiten, keine Tiefensuche (Performance-Grund, siehe
# Kommentar dort). Aendert sich NUR unsere FILTER-LOGIK im Code (z.B.
# JUNK_TAGS), nicht aber die Dateien selbst, bleibt die Ordner-mtime
# UNVERAENDERT - der alte, noch mit der alten Logik erzeugte
# Cache-Eintrag wurde dadurch munter weiterverwendet, obwohl der Code
# laengst repariert war. Nur ein manueller Rescan (System -> Wartung)
# half bisher, JEDE zukuenftige Filter-Logik-Aenderung haette denselben
# Effekt gehabt. Fix: eine eigene Versionsnummer, die bei jeder
# Aenderung an der FILTER-/DEDUPE-Logik selbst (nicht bei jedem Code-
# Release) von Hand hochgezaehlt wird - fliesst mit in die Signatur
# ein, macht den Cache dadurch automatisch ungueltig, sobald sich die
# Auswertung selbst geaendert hat, ganz unabhaengig von Datei-mtimes.
SCAN_LOGIC_VERSION = 4   # 1 = Basis, 2 = "(unl)"/"(pirate)" nicht mehr Junk,
                         # 3 = OPTIONAL_GAME_SYSTEMS (SNES_Tracker-Core),
                         # 4 = SMW Hacks (games/SNES/SMW_HACKS)

def _games_signature():
    """Schneller Fingerabdruck der ROM-Ordner (ohne Tiefensuche):
    existierende Wurzeln + deren mtime. Aendert sich der Inhalt einer
    Wurzel direkt, aendert sich die Signatur; bei Aenderungen tief in
    Unterordnern hilft der System-Eintrag 'Spieleliste neu einlesen'.

    HINWEIS (v1.32 zurueckgerollt): Ein Zwischenstand hat versucht,
    hierfuer ALLE Unterordner rekursiv mit einzubeziehen, um Aende-
    rungen tief in Sammlungen (z.B. 'Favoriten') automatisch zu
    erkennen. Das hat sich bei einer echten, grossen Sammlung (v.a.
    ueber USB mit hoeherer Zugriffszeit als ein schneller lokaler
    Datentraeger) als deutlich zu langsam herausgestellt - der
    komplette Ordnerbaum wurde dadurch bei JEDEM Boot durchlaufen,
    bevor der Bildschirm ueberhaupt wechselt (Musik lief bereits,
    das Frontend blieb aber minutenlang unsichtbar). Zurueck auf die
    schnelle, nur-oberste-Ebene-Pruefung - das war der urspruengliche,
    bewusste Kompromiss: schneller Boot immer, dafuer Aenderungen tief
    in Unterordnern nur per manuellem Rescan erkannt.

    WICHTIG (v1.53): statt des ABSOLUTEN Pfads geht nur eine Ort-
    Kennung ("usb:" oder "fat:") + der relative Ordnername in die
    Signatur ein. Eine USB-Platte mountet nach einem Kaltstart nicht
    immer unter derselben Nummer (mal /media/usb0, mal /media/usb1) -
    mit dem absoluten Pfad haette sich die Signatur dadurch bei jedem
    Boot geaendert, obwohl sich am Inhalt nichts geaendert hat, und
    jedes Mal einen unnoetigen kompletten Neuscan ausgeloest. Sortiert,
    damit auch die Reihenfolge der Basispfade die Signatur nicht
    veraendert.

    NEU (Phase 2, Nutzerwunsch "ROM-Index/inkrementelles Scannen"):
    liefert zusaetzlich per_syskey - dieselben Fingerabdruck-Eintraege,
    aber nach Systemkey aufgeschluesselt statt in einer einzigen
    flachen Liste. Kostet NICHTS zusaetzlich an Festplattenzugriffen
    (dieselben os.path.getmtime()-Aufrufe wie bisher, nur anders
    einsortiert) - ermoeglicht aber scan_games(), bei einer Aenderung
    NUR die tatsaechlich betroffenen Systeme neu zu scannen, statt wie
    bisher immer ALLE 14+ Systeme neu einzulesen, auch wenn sich nur an
    einem einzigen etwas veraendert hat."""
    sig = []
    per_syskey = {}
    for base in fe.paths.GAMES_BASES:
        if not os.path.isdir(base):
            continue
        tag = "usb:" if "/media/usb" in base else "fat:"
        for _d, sk, folders, _r, _e in GAME_SYSTEMS:
            for folder in folders:
                root = os.path.join(base, folder)
                try:
                    mtime = int(os.path.getmtime(root))
                except OSError:
                    continue
                entry = (tag + folder, mtime)
                sig.append(entry)
                per_syskey.setdefault(sk, []).append(entry)
        for _d, sk, folders, _r, _e, _core in OPTIONAL_GAME_SYSTEMS:
            for folder in folders:
                root = os.path.join(base, folder)
                try:
                    mtime = int(os.path.getmtime(root))
                except OSError:
                    continue
                entry = (tag + folder, mtime)
                sig.append(entry)
                per_syskey.setdefault(sk, []).append(entry)
    # Core-Datei der optionalen Systeme selbst mit in die Signatur
    # aufnehmen (nicht nur den ROM-Ordner oben) - sonst wuerde ein
    # nachtraeglich installierter/entfernter SNES_Tracker-Core NICHT
    # erkannt, solange sich am ROM-Ordner nichts aendert, und die neue
    # Kategorie bliebe bis zum naechsten manuellen Rescan unsichtbar.
    for _d, sk, _f, _r, _e, core_check_path in OPTIONAL_GAME_SYSTEMS:
        # Als Schluessel bewusst das MUSTER verwenden, nicht den gefundenen
        # Dateinamen: sonst wuerde schon ein reines Core-Update (neuer
        # Datumsstempel im Namen) die Signatur aendern und einen kompletten
        # Neuaufbau ausloesen, obwohl sich an der Spieleliste nichts getan
        # hat. Der Zeitstempel unten faengt eine echte Aenderung ohnehin ab.
        _core_file = optional_core_file(core_check_path)
        try:
            entry = ("core:" + core_check_path,
                     int(os.path.getmtime(_core_file)))
        except (OSError, TypeError):
            entry = ("core:" + core_check_path, None)
        sig.append(entry)
        per_syskey.setdefault(sk, []).append(entry)
    sig.sort(key=lambda t: (t[0], t[1] is None, t[1]))
    sig.append(("__scan_logic_version__", SCAN_LOGIC_VERSION))
    for sk in per_syskey:
        per_syskey[sk].sort(key=lambda t: (t[0], t[1] is None, t[1]))
    return sig, per_syskey

def _sig_expects_usb(sig):
    """True, wenn eine Signatur mindestens einen USB-Ordner enthaelt -
    genutzt, um zu entscheiden, ob sich das Warten auf einen USB-Mount
    ueberhaupt lohnt (siehe scan_games())."""
    return any(entry[0].startswith("usb:") for entry in sig)

def _node_to_json(node):
    return {"folders": {k: _node_to_json(v) for k, v in node["folders"].items()},
            "items": [[i0, i1, list(i2[:4]) + [list(i2[4])]] for i0, i1, i2 in node["items"]]}

def _node_from_json(data):
    return {"folders": {k: _node_from_json(v) for k, v in data["folders"].items()},
            "items": [(i0, i1, (i2[0], i2[1], i2[2], i2[3], tuple(i2[4])))
                     for i0, i1, i2 in data["items"]]}

def _cats_to_json(cats):
    return [[n, _node_to_json(node), sk] for n, node, sk in cats]

def _cats_from_json(data):
    return [(n, _node_from_json(node), sk) for n, node, sk in data]


def _wait_for_usb_stable(max_wait=10.0, poll=0.5, min_wait_if_none=3.0):
    """Kurz warten, falls USB-Laufwerke gerade erst einhaengen - nur
    relevant fuer den (seltenen) tatsaechlichen Scan-Fall, verzoegert
    NICHT den schnellen Cache-Treffer-Normalfall.

    Prueft nicht nur, OB der Mountpunkt existiert (das kann bei einer
    langsam hochlaufenden Festplatte schon der Fall sein, WAEHREND die
    Dateiliste dahinter noch nachzieht) - sondern die tatsaechliche
    Anzahl an Eintraegen in jedem USB-Basisordner (os.listdir). Erst
    wenn sich diese Anzahl zwischen zwei Abfragen nicht mehr aendert,
    gilt das Laufwerk als wirklich fertig eingehaengt.

    Rueckgabe (v1.53): drei moegliche Zustaende, damit der Aufrufer
    weiss, ob das Ergebnis vertrauenswuerdig genug zum Zwischen-
    speichern ist:
    - True  = mindestens ein USB-Pfad gefunden UND stabil - Ergebnis
      vollstaendig, cachen ist sicher.
    - None  = ueberhaupt kein USB im Spiel (Setup ohne USB-Laufwerk) -
      Ergebnis vollstaendig, cachen ist sicher.
    - False = ein USB-Mountpunkt wurde gesehen, ist aber bis zum
      Zeitlimit nicht stabil geworden - das Scan-Ergebnis KOENNTE
      unvollstaendig sein, cachen ist NICHT sicher (siehe scan_games()).

    Hintergrund: seit v1.48 passiert der Bildschirmwechsel VOR dem
    Scan (behebt das Haengenbleiben im MiSTer-OSD) - das aendert aber
    nichts daran, WANN der Scan selbst startet. Laeuft er, bevor ein
    USB-Laufwerk nach einem Kaltstart wirklich fertig eingehaengt ist,
    fehlen dessen Spiele im Ergebnis."""
    usb_candidates = [b for b in fe.paths.GAMES_BASES if "/media/usb" in b]
    if not usb_candidates:
        return None

    def snapshot():
        found = False
        total = 0
        for b in usb_candidates:
            if os.path.isdir(b):
                found = True
                try:
                    total += len(os.listdir(b))
                except OSError:
                    pass
        return found, total

    t0 = time.monotonic()
    last_total = None
    stable_streak = 0
    while True:
        elapsed = time.monotonic() - t0
        found, total = snapshot()
        if elapsed >= max_wait:
            LOG("_wait_for_usb_stable: Zeitlimit (%.1fs) erreicht, fahre trotzdem fort"
               % max_wait)
            # Beim Zeitlimit unterscheiden: ist ueberhaupt ein
            # Mountpunkt da? Wenn ja, ist er evtl. nur noch nicht
            # stabil - trotzdem unsicher, also nicht cachen (False).
            # Wenn gar keiner kam, ist es ein Setup ohne USB (None).
            return False if found else None
        # BUGFIX (Nutzer-Rueckmeldung): ein durchgehend LEERER, aber
        # STABILER Ordner (Anzahl bleibt bei 0) wurde bisher NIE als
        # stabil erkannt, weil "has_content" das ausdruecklich
        # voraussetzte - nur ein durchgehend GEFUELLTER Ordner konnte
        # jemals "stabil" werden. MiSTer legt aber haeufig leere
        # /media/usb0, /media/usb1 usw. als Platzhalter an, VOELLIG
        # unabhaengig davon, ob dort tatsaechlich ein USB-Laufwerk
        # angeschlossen ist. Bei so einem Setup blieb die Anzahl immer
        # bei 0, "stable_streak" wurde nie hochgezaehlt, das Zeitlimit
        # wurde dadurch IMMER erreicht - das Scan-Ergebnis wurde NIE
        # gecacht, die Spieleliste wurde bei JEDEM Start komplett neu
        # gescannt. Jetzt zaehlt auch eine durchgehend stabile Null als
        # stabil (mit etwas mehr Vorsicht: doppelt so viele
        # aufeinanderfolgende Abfragen wie bei echtem Inhalt, damit ein
        # Laufwerk, das gerade erst zu befuellen beginnt, nicht zu
        # frueh faelschlich als "leer und fertig" gilt).
        if total == last_total:
            stable_streak += 1
            required = 2 if total > 0 else 4
            if stable_streak >= required:
                LOG("_wait_for_usb_stable: USB-Inhalt stabil (%d Eintraege) nach %.1fs"
                   % (total, elapsed))
                return True if total > 0 else None
        else:
            stable_streak = 0
        if not found and elapsed >= min_wait_if_none:
            return None
        last_total = total
        time.sleep(poll)

# ----------------------------------------------------------------------------
# NETZWERK/NAS-WARTEOPTION (Nutzerwunsch): liegen die ROMs auf einem
# Netzlaufwerk (NAS, ueber CIFS/SMB oder NFS eingebunden - MiSTer haengt
# das typischerweise unter /media/fat/cifs ein bzw. blendet es direkt in
# die games-Ordner ein, siehe cifs_mount.sh), kann der Scan starten,
# BEVOR die Verbindung wirklich steht - das Ergebnis (leer oder
# unvollstaendig) wuerde dann sogar dauerhaft gecacht werden. Standard
# AUS (die meisten Nutzer haben SD-Karte/USB, fuer die das nur unnoetig
# verzoegern wuerde) - NUR fuer NAS-Nutzer per Option einschaltbar.
NETWORK_WAIT_FILE = "/media/fat/frontend/network_wait"

# NEU (Nutzer-Rueckmeldung: "Option 'wait for Network' habe ich gesetzt,
# kein Effekt. Besser waere hier eher, zu pruefen, ob im Autostart
# ueberhaupt ein Cifs_Mount konfiguriert ist - dann spart man sich den
# haendischen Eingriff"): MiSTers eigener Autostart-Mechanismus haengt
# ALLE Zeilen in user-startup.sh beim Booten aus - typischerweise auch
# den Aufruf eines cifs_mount.sh o.ae. Steht dort tatsaechlich ein
# CIFS-Bezug drin, ist ziemlich sicher ein NAS im Spiel, OHNE dass der
# Nutzer das erst manuell im Frontend-Menue nachtragen muesste.
USER_STARTUP_FILE = "/media/fat/linux/user-startup.sh"

def _autostart_has_cifs_entry():
    """True, wenn user-startup.sh eine (nicht auskommentierte) Zeile
    mit einem CIFS-Bezug enthaelt (z.B. ein Aufruf von cifs_mount.sh) -
    reines Textmuster, absichtlich simpel/tolerant gehalten (keine
    Annahme ueber den genauen Skriptnamen), damit auch abweichend
    benannte eigene Mount-Skripte erkannt werden. Fehlt die Datei oder
    ist sie nicht lesbar, wird sicherheitshalber NEIN angenommen (wie
    bisher - kein Verhalten fuer den ganz ueberwiegenden Regelfall ohne
    NAS aendert sich dadurch)."""
    try:
        with open(USER_STARTUP_FILE) as f:
            for line in f:
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                if "cifs" in stripped.lower():
                    return True
    except OSError:
        pass
    return False

def network_wait_enabled():
    """Liest die Einstellung "beim Start auf Netzwerk/NAS warten".

    NEU: wurde die Option noch NIE von Hand gesetzt (Datei fehlt ganz),
    wird nicht mehr stur NEIN angenommen, sondern automatisch anhand
    von _autostart_has_cifs_entry() entschieden - steht dort ein
    CIFS-Mount im Autostart, ist die Wartezeit von Anfang an sinnvoll
    aktiv, ganz ohne manuellen Eingriff im Menue. Eine einmal explizit
    getroffene Nutzerentscheidung (Datei vorhanden, "yes"/"no") hat
    IMMER Vorrang vor dieser automatischen Erkennung - siehe auch
    network_wait_is_auto() fuer den entsprechenden Menue-Hinweis."""
    try:
        with open(NETWORK_WAIT_FILE) as f:
            return f.read().strip().lower() in ("yes", "1", "ja", "true")
    except OSError:
        return _autostart_has_cifs_entry()

def network_wait_is_auto():
    """True, wenn die Warteoption (noch) nicht von Hand gesetzt wurde,
    ihr aktueller AN/AUS-Stand also rein automatisch (ueber
    _autostart_has_cifs_entry()) zustande kommt - nur fuer einen
    kleinen "(automatisch erkannt)"-Hinweis im Menue gedacht, damit ein
    von selbst aktiviertes "AN" niemanden verwirrt."""
    return not os.path.exists(NETWORK_WAIT_FILE)

def save_network_wait(enabled):
    try:
        os.makedirs(os.path.dirname(NETWORK_WAIT_FILE), exist_ok=True)
        with open(NETWORK_WAIT_FILE, "w") as f:
            f.write("yes" if enabled else "no")
    except OSError:
        pass

def _has_network_mount():
    """True, wenn eine Netzwerk-Freigabe (CIFS/NFS) gemountet ist - das
    eigentliche Signal, dass das NAS jetzt wirklich da ist. Uebernommener
    Vorschlag - siehe _wait_for_network_ready()."""
    try:
        with open("/proc/mounts") as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 3 and parts[2] in (
                        "cifs", "smb3", "smbfs", "nfs", "nfs4"):
                    return True
    except OSError:
        pass
    return False

def _wait_for_network_ready(max_wait=45.0, poll=0.5):
    """NUR aktiv, wenn network_wait_enabled() - sonst sofortige
    Rueckkehr (kein Einfluss auf den ganz ueberwiegenden Regelfall SD-
    Karte/USB).

    ERWEITERT (uebernommener Vorschlag - loest eine Luecke der
    urspruenglichen Fassung): die vorherige Version wartete nur auf
    "irgendeine Netzwerkverbindung" und dann auf einen stabilen Inhalt
    von GAMES_BASES - GAMES_BASES war aber beim Modul-Import bereits
    (leer) eingefroren, BEVOR das NAS ueberhaupt gemountet war, und ein
    schon stabiler, aber rein LOKALER Ordner (nur Cores, kein NAS)
    konnte das Warten faelschlich vorzeitig beenden lassen. Jetzt wird
    zusaetzlich echt geprueft, ob eine CIFS/NFS-Freigabe TATSAECHLICH
    gemountet ist (_has_network_mount()) - erst NACHDEM das gesehen
    wurde, zaehlt ein stabiler Inhalt. GAMES_BASES wird ausserdem bei
    jeder Pruefung sowie am Ende neu ermittelt (_discover_games_bases()),
    damit ein erst waehrend der Wartezeit erscheinendes NAS-Mount auch
    tatsaechlich erfasst wird."""
    if not network_wait_enabled():
        return
    t0 = time.monotonic()
    while not _has_network():
        if time.monotonic() - t0 >= max_wait:
            LOG("_wait_for_network_ready: keine Netzwerkverbindung nach %.0fs - fahre trotzdem fort"
               % max_wait)
            fe.paths.GAMES_BASES = fe.paths._discover_games_bases()
            return
        time.sleep(poll)

    def snapshot():
        # Wurzeln JEDES Mal neu ermitteln - erfasst ein erst jetzt
        # erscheinendes NFS/CIFS-Mount (GAMES_BASES ist eingefroren).
        total = 0
        for b in fe.paths._discover_games_bases():
            if os.path.isdir(b):
                try:
                    total += len(os.listdir(b))
                except OSError:
                    pass
        return total

    last_total = None
    stable_streak = 0
    saw_mount = False
    while True:
        elapsed = time.monotonic() - t0
        if elapsed >= max_wait:
            LOG("_wait_for_network_ready: Zeitlimit (%.0fs) erreicht, fahre trotzdem fort"
               % max_wait)
            break
        if _has_network_mount():
            saw_mount = True
        total = snapshot()
        # Erst als fertig gelten, wenn das NAS-Mount GESEHEN wurde - sonst
        # bricht der schon stabile LOKALE Ordner (nur Cores) das Warten ab,
        # bevor das NAS ueberhaupt gemountet ist.
        if saw_mount and total == last_total:
            stable_streak += 1
            required = 2 if total > 0 else 4   # bei leer vorsichtiger, siehe _wait_for_usb_stable()
            if stable_streak >= required:
                LOG("_wait_for_network_ready: NAS gemountet, Inhalt stabil (%d Eintraege) nach %.1fs"
                   % (total, elapsed))
                break
        else:
            stable_streak = 0
        last_total = total
        time.sleep(poll)
    fe.paths.GAMES_BASES = fe.paths._discover_games_bases()

def scan_games(force=False, progress_cb=None):
    """ROM-Listen laden - aus dem Cache, wenn er noch passt.
    progress_cb(i, total, name): wird NUR beim tatsaechlichen Scannen
    von der Platte aufgerufen (nicht beim schnellen Cache-Treffer) -
    normale Boots (Cache passt) bleiben also unveraendert schnell,
    nur der seltene "erster Start"/"ROMs geaendert"-Fall zeigt Fortschritt.

    PERFORMANCE (Nutzerwunsch: "performance-technisch noch was
    rausholen"): Cache-Datei laeuft seit hier auf Pickle statt JSON -
    bei einer grossen Sammlung (getestet mit ~4700 Spielen, angelehnt
    an eine echte Nutzer-Sammlung) ca. 9x schnelleres Schreiben, ca.
    2.7x schnelleres Lesen, UND kleinere Datei. Pickle erhaelt Tupel
    nativ, dadurch entfaellt zusaetzlich der komplette Umweg ueber
    _cats_to_json()/_cats_from_json() (Tupel<->Liste-Konvertierung
    fuer JEDES einzelne Spiel) - das war selbst schon ein spuerbarer
    Teil der Kosten, nicht nur die reine Serialisierung.

    NEU (Phase 2, Nutzerwunsch "ROM-Index/inkrementelles Scannen"):
    passt die flache Signatur NICHT mehr komplett (z.B. weil ein
    einziges neues NES-ROM dazukam), wird NICHT mehr zwangslaeufig
    ALLES neu gescannt. Stattdessen wird per-System verglichen -
    NUR die tatsaechlich veraenderten Systeme werden von der Platte
    gelesen, alle anderen unveraendert aus dem alten Cache
    uebernommen. Bei einer grossen Sammlung mit vielen Systemen kann
    das den seltenen 'ROMs geaendert'-Fall deutlich beschleunigen -
    ohne die bewusste Entscheidung von v1.32 anzutasten (siehe
    _games_signature()): es wird weiterhin NUR die oberste Ebene
    geprueft, kein tieferer Ordnerbaum zusaetzlich durchlaufen, um
    diese Entscheidung zu treffen."""
    sig, per_syskey = _games_signature()
    cached_sig = None
    cached_per_syskey = None
    data = None
    if not force:
        try:
            with open(GAMES_CACHE, "rb") as f:
                data = pickle.load(f)
            cached_sig = data["sig"]
            cached_per_syskey = data.get("per_syskey")
            if cached_sig == sig:
                LOG("Spieleliste aus Cache (%d Systeme)"
                    % len(data["cats"]))
                return data["cats"]
        except (OSError, ValueError, KeyError, IndexError, TypeError,
                pickle.UnpicklingError, EOFError, AttributeError):
            cached_sig = None
            cached_per_syskey = None
            data = None

    usb_ready = None
    waited_already = False
    # Cache passt (noch) nicht. Haeufigster Grund bei einem KALTSTART:
    # die USB-Platte war in dem Moment, in dem die Signatur oben
    # gebildet wurde, schlicht noch nicht gemountet - die aktuelle
    # Signatur hat dann keine USB-Ordner, der Cache (vom letzten Scan
    # MIT USB) aber schon. Nur in genau diesem Fall lohnt sich das
    # Warten VOR einem kompletten Neuscan: erwartet der Cache USB,
    # sehen wir aber noch keines, dann warten und erneut vergleichen.
    # SD-only-Systeme (Cache ohne USB) und warme Boots (Signatur passt
    # sofort) warten hier gar nicht.
    if (not force and cached_sig is not None
            and _sig_expects_usb(cached_sig) and not _sig_expects_usb(sig)):
        LOG("scan_games: Cache erwartet USB, noch nicht gemountet - warte")
        usb_ready = _wait_for_usb_stable()
        waited_already = True
        sig, per_syskey = _games_signature()
        if cached_sig == sig:
            LOG("Spieleliste aus Cache nach USB-Mount (%d Systeme)"
                % len(data["cats"]))
            return data["cats"]

    if not waited_already:
        usb_ready = _wait_for_usb_stable()

    # Inkrementelles Scannen: nur versuchen, wenn ein gueltiger alter
    # Cache MIT per_syskey-Aufschluesselung vorliegt (aeltere Cache-
    # Dateien vor diesem Feature haben das Feld nicht - dann faellt
    # dies automatisch auf den kompletten Scan zurueck, sicherer
    # Normalfall beim allerersten Lauf nach einem Update). Ein
    # geaenderter SCAN_LOGIC_VERSION-Eintrag betrifft ALLE Systeme
    # gleichermassen (z.B. neue Filterregeln) - in diesem Fall lohnt
    # sich der Versuch, nur einen Teil zu scannen, ohnehin nicht, also
    # bewusst nicht extra behandelt: der Versuch, per-System zu ver-
    # gleichen, findet dann ganz natuerlich JEDES System als 'veraendert'
    # (der Versions-Eintrag ist Teil jeder per_syskey-Teilliste), das
    # Ergebnis ist also automatisch korrekt identisch zu einem vollen Scan.
    cats = None
    if cached_per_syskey:
        changed_syskeys = set()
        all_syskeys = set(per_syskey.keys()) | set(cached_per_syskey.keys())
        for sk in all_syskeys:
            if per_syskey.get(sk) != cached_per_syskey.get(sk):
                changed_syskeys.add(sk)
        if changed_syskeys and changed_syskeys != all_syskeys:
            LOG("scan_games: inkrementell - %d von %d Systemen veraendert (%s)"
                % (len(changed_syskeys), len(all_syskeys),
                   ", ".join(sorted(changed_syskeys))))
            fresh = _scan_games_disk(progress_cb, only_syskeys=changed_syskeys)
            fresh_by_sk = {sk: (disp, node) for disp, node, sk in fresh}
            old_by_sk = {sk: (disp, node) for disp, node, sk in data["cats"]}
            cats = []
            for disp, sk, *_rest in GAME_SYSTEMS:
                if sk in changed_syskeys:
                    if sk in fresh_by_sk:
                        d, node = fresh_by_sk[sk]
                        cats.append((d, node, sk))
                elif sk in old_by_sk:
                    d, node = old_by_sk[sk]
                    cats.append((d, node, sk))
            for disp, sk, *_rest in OPTIONAL_GAME_SYSTEMS:
                if sk in changed_syskeys:
                    if sk in fresh_by_sk:
                        d, node = fresh_by_sk[sk]
                        cats.append((d, node, sk))
                elif sk in old_by_sk:
                    d, node = old_by_sk[sk]
                    cats.append((d, node, sk))
        elif not changed_syskeys:
            # Sollte praktisch nicht vorkommen (sig haette dann oben
            # schon vollstaendig gepasst) - reiner Sicherheits-Rueckfall.
            cats = data["cats"]

    if cats is None:
        cats = _scan_games_disk(progress_cb)

    # usb_ready: True = USB sauber eingehaengt, None = gar kein USB im
    # Spiel (beides -> Ergebnis vollstaendig, cachen ok). False = ein
    # USB-Mountpunkt war da, wurde aber nicht rechtzeitig stabil - das
    # Ergebnis KOENNTE unvollstaendig sein. Dann NICHT cachen, sonst
    # bliebe eine Luecke dauerhaft bestehen (der Cache passt beim
    # naechsten Boot ja wieder) - ohne Cache scannt der naechste Boot
    # einfach erneut, bis die Platte einmal rechtzeitig bereit war.
    if usb_ready is False:
        LOG("scan_games: USB nicht sicher bereit - Ergebnis wird NICHT gecacht")
        return cats

    sig, per_syskey = _games_signature()
    try:
        with open(GAMES_CACHE, "wb") as f:
            pickle.dump({"sig": sig, "per_syskey": per_syskey, "cats": cats},
                        f, protocol=pickle.HIGHEST_PROTOCOL)
        # Einmalige Aufraeumung: eine alte JSON-Cache-Datei aus der Zeit
        # vor dem Pickle-Wechsel wuerde sonst nutzlos auf der SD-Karte
        # liegen bleiben (wird nie wieder gelesen, seit GAMES_CACHE auf
        # .pkl zeigt) - einfach mit entfernen, kein Fehler wenn nicht
        # vorhanden.
        try:
            os.remove(GAMES_CACHE_OLD_JSON)
        except OSError:
            pass
    except OSError:
        pass
    return cats

def _wrap_flat(items_list):
    """Eine bestehende flache Liste (Scripts/System/Cores/Zuletzt
    gespielt) als Baumknoten ohne Unterordner einwickeln - macht alle
    Kategorien einheitlich zu Baumknoten, der Rest des Codes muss
    dadurch nicht zwischen 'flacher Liste' und 'Baum' unterscheiden."""
    return {"folders": {}, "items": items_list}

def _count_tree_items(node):
    """Zaehlt rekursiv alle Eintraege in einem Baumknoten - auch in
    verschachtelten Unterordnern (Nutzerwunsch: die Kategorien
    "Sammlungen"/"RA-Erfolgsjaeger" zeigten im Hauptmenue selbst keine
    Anzahl, man musste erst reingehen um zu sehen ob ueberhaupt was
    drinsteckt). Nur fuer die kleinen, abgeleiteten Kategorien gedacht
    (Sammlungen/RA-Erfolgsjaeger haben wenige Dutzend Eintraege) - fuer
    die grossen ROM-Kategorien waere das zu teuer, dort zaehlen wir
    bewusst nicht."""
    total = len(node.get("items", ()))
    for sub in node.get("folders", {}).values():
        total += _count_tree_items(sub)
    return total

def _empty_node():
    """Leerer Baumknoten: {'folders': {Name: Knoten, ...}, 'items':
    [(label,kind,arg), ...]}. Wird fuer ALLE Kategorien einheitlich
    genutzt - auch fuer Scripts/System/Cores/Zuletzt-gespielt, die
    einfach 'folders'={} bekommen (flach, wie bisher)."""
    return {"folders": {}, "items": []}

def _merge_node(dst, src):
    """src-Knoten in dst hineinmischen - noetig, falls derselbe
    Systemordner (z.B. 'SNES') von mehreren GAMES_BASES aus existiert
    (SD-Karte UND ein USB-Laufwerk)."""
    for name, sub in src["folders"].items():
        if name in dst["folders"]:
            _merge_node(dst["folders"][name], sub)
        else:
            dst["folders"][name] = sub
    dst["items"].extend(src["items"])

def _dedupe_items(raw_items):
    """BUGFIX/AENDERUNG (Nutzerwunsch: "mehrere Spielversionen muessen
    auch im Menue zur Auswahl stehen, PAL/NTSC etcpp"): frueher wurde
    hier pro kanonischem Namen (ohne Region-/Versions-Tags) NUR die
    Kopie mit der besten Region behalten (Germany > Europe > World >
    USA > Japan, siehe REGION_PRIORITY), alle anderen Versionen
    verschwanden komplett aus der Liste - nicht mehr auswaehlbar,
    unabhaengig davon, ob man gezielt die PAL- oder NTSC-Fassung
    wollte. Jetzt bleiben ALLE gefundenen Versionen erhalten, nur
    alphabetisch sortiert - REGION_PRIORITY/_region_rank() bleiben im
    Code bestehen (werden an anderer Stelle noch fuer die Boxart-/
    Info-Zuordnung gebraucht), wirken sich hier aber nicht mehr
    aus."""
    items = list(raw_items)
    items.sort(key=lambda t: t[0].lower())
    return items

def _node_count(node):
    """Rekursive Gesamtzahl aller Eintraege (inkl. aller Unterordner)
    fuer die Anzeige in der Kategorienliste."""
    n = len(node["items"])
    for sub in node["folders"].values():
        n += _node_count(sub)
    return n

def _scan_folder_tree(path, syskey, rbf, extmap):
    """Rekursiv EINEN Ordner scannen, gibt einen Baumknoten zurueck -
    beliebig tief verschachtelt, spiegelt die eigene Ordnerstruktur/
    Sortierung 1:1 wider. Bekannte Boot-/Testdateien, Beta/Proto/Hack-
    Tags und rein japanische Titel werden wie bisher ausgefiltert."""
    node = _empty_node()
    try:
        entries = sorted(os.listdir(path), key=str.lower)
    except OSError:
        return node
    raw_items = []
    for entry in entries:
        if entry.startswith("."):
            continue
        full = os.path.join(path, entry)
        if os.path.isdir(full):
            sub = _scan_folder_tree(full, syskey, rbf, extmap)
            if sub["folders"] or sub["items"]:
                node["folders"][entry] = sub
        else:
            name, ext = os.path.splitext(entry)
            ext = ext.lower()
            if name.lower() in IGNORE_ROM_BASENAMES:
                continue
            if _is_junk(name):
                continue
            if _is_japan_only(name):
                continue
            if ext in extmap:
                raw_items.append((name, "game",
                                  (full, ext, syskey, rbf, extmap[ext])))
    node["items"] = _dedupe_items(raw_items)
    return node

def _scan_games_disk(progress_cb=None, only_syskeys=None):
    """Fuer jedes bekannte System die ROMs einsammeln. Rueckgabe: Liste
    (Anzeigename, Baumknoten, Systemkey) - der Baumknoten spiegelt die
    eigene Ordnerstruktur 1:1 wider (beliebig tief verschachtelt),
    statt wie bisher alles in eine flache Liste zu quetschen. Das
    Frontend zeigt Unterordner als eigene Eintraege, die man oeffnen
    kann - genau wie auf dem Datentraeger abgelegt.

    Bekannte Boot-/Testdateien (IGNORE_ROM_BASENAMES) sowie Beta/Proto/
    Demo/Hack/Bad-Dump-Tags (JUNK_TAGS) werden ausgefiltert. Mehrfach-
    Regionen desselben Spiels werden INNERHALB jedes einzelnen Ordners
    zu EINEM Eintrag zusammengefasst (beste Region gewinnt,
    REGION_PRIORITY).

    NEU (Phase 2, inkrementelles Scannen): only_syskeys - wenn gesetzt
    (Menge von Systemkeys), werden NUR diese Systeme tatsaechlich von
    der Platte gelesen, alle anderen komplett uebersprungen (kein
    os.listdir(), keine Ordner-Tiefensuche fuer sie). scan_games()
    fuegt die uebersprungenen Systeme anschliessend aus dem
    vorhandenen Cache wieder hinzu - siehe dortiger Kommentar. Bei
    only_syskeys=None (Vorgabe) unveraendertes Verhalten: alle Systeme
    werden gescannt, wie bisher."""
    cats = []
    total_sys = len(GAME_SYSTEMS) + len(OPTIONAL_GAME_SYSTEMS)
    # Unterordner, die ein ANDERER Eintrag (egal ob GAME_SYSTEMS oder
    # OPTIONAL_GAME_SYSTEMS) exklusiv fuer sich beansprucht (z.B.
    # "ZELDA_MSU" oder "SMW_HACKS" unter "SNES"), muessen aus der
    # REGULAEREN Kategorie desselben Basisordners ausgeschlossen werden -
    # sonst wuerden dieselben ROMs zusaetzlich unter der normalen SNES-
    # Kategorie auftauchen und liessen sich dort versehentlich mit dem
    # falschen Core statt dem dafuer vorgesehenen starten. Nur EIN
    # Ordner tief beruecksichtigt (passend zu den bisherigen
    # Anwendungsfaellen) - Schluessel ist der oberste Ordnername (z.B.
    # "SNES"), Wert die Menge auszuschliessender direkter
    # Unterordnernamen (z.B. {"ZELDA_MSU", "SMW_HACKS"}).
    claimed_subfolders = {}
    for _d, _sk, sub_folders, _r, _e in GAME_SYSTEMS:
        for f in sub_folders:
            if "/" in f:
                top, sub = f.split("/", 1)
                claimed_subfolders.setdefault(top, set()).add(sub.split("/", 1)[0])
    for _d, _sk, opt_folders, _r, _e, _core in OPTIONAL_GAME_SYSTEMS:
        for f in opt_folders:
            if "/" in f:
                top, sub = f.split("/", 1)
                claimed_subfolders.setdefault(top, set()).add(sub.split("/", 1)[0])
    for sys_idx, (disp, syskey, folders, rbf, extmap) in enumerate(GAME_SYSTEMS):
        if only_syskeys is not None and syskey not in only_syskeys:
            continue
        if progress_cb:
            try:
                progress_cb(sys_idx, total_sys, disp)
            except Exception:
                pass
        sys_node = _empty_node()
        seen_roots = set()
        for base in fe.paths.GAMES_BASES:
            if not os.path.isdir(base):
                continue
            for folder in folders:
                root = os.path.join(base, folder)
                real = os.path.realpath(root)
                if not os.path.isdir(root) or real in seen_roots:
                    continue
                seen_roots.add(real)
                sub_node = _scan_folder_tree(root, syskey, rbf, extmap)
                _merge_node(sys_node, sub_node)
            for excluded in claimed_subfolders.get(folder, ()):
                sys_node["folders"].pop(excluded, None)
        if sys_node["folders"] or sys_node["items"]:
            cats.append((disp, sys_node, syskey))

    # OPTIONALE Systeme (Nutzerwunsch: SNES_Tracker-Core "wie ein
    # eigenes System behandeln, falls installiert - falls NICHT
    # installiert darf das auch nicht mit angezeigt werden"): exakt
    # dieselbe Scan-Logik wie oben, aber zusaetzlich VORAB die
    # core_check_path-Datei pruefen - fehlt sie, wird gar nicht erst
    # gescannt, das System taucht dann so auf, als gaebe es den
    # Eintrag nicht (kein leerer/ausgegrauter Platzhalter).
    for opt_idx, (disp, syskey, folders, rbf, extmap, core_check_path) \
            in enumerate(OPTIONAL_GAME_SYSTEMS):
        if only_syskeys is not None and syskey not in only_syskeys:
            continue
        if progress_cb:
            try:
                progress_cb(len(GAME_SYSTEMS) + opt_idx, total_sys, disp)
            except Exception:
                pass
        if optional_core_file(core_check_path) is None:
            continue
        sys_node = _empty_node()
        seen_roots = set()
        for base in fe.paths.GAMES_BASES:
            if not os.path.isdir(base):
                continue
            for folder in folders:
                root = os.path.join(base, folder)
                real = os.path.realpath(root)
                if not os.path.isdir(root) or real in seen_roots:
                    continue
                seen_roots.add(real)
                sub_node = _scan_folder_tree(root, syskey, rbf, extmap)
                _merge_node(sys_node, sub_node)
        if sys_node["folders"] or sys_node["items"]:
            cats.append((disp, sys_node, syskey))
    return cats
