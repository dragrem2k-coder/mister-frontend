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
import os, glob, re, struct, time, pickle, socket
import threading as _threading
from fe.log import LOG
from fe.systems import (GAME_SYSTEMS, OPTIONAL_GAME_SYSTEMS,
                        optional_core_file)
from fe.naming import IGNORE_ROM_BASENAMES, JUNK_TAGS, REGION_PRIORITY, nice_name, _is_junk, _is_japan_only
from fe.game_state import _folder_items
from fe.settings import rom_filter_enabled, einzelordner_aufloesen
import fe.paths

BASE = "/media/fat"
SKIP_DIRS = {"_Scripts"}
GAMES_CACHE = "/media/fat/frontend/games_cache.pkl"
GAMES_CACHE_OLD_JSON = "/media/fat/frontend/games_cache.json"

# ======================================================================
# DER SPIELELISTEN-CACHE, JE SYSTEM LESBAR (Build 248)
# ======================================================================
#
# WOHER DIE FRAGE KOMMT. Die Messung vom 18.09.
# (claude/FUND_Speicher_je_Eintrag.md) hat die Posten aufgeteilt:
#
#     Spielebaum                       383 B je Eintrag
#     Anzeigenamen-Cache               123 B je Eintrag
#     Pickle-Puffer beim Schreiben     144 B je Eintrag
#     zweite Kopie beim Einlesen       439 B je Eintrag
#     ------------------------------------------------
#     Dauerlast                        506 B je Eintrag
#     SPITZE                          1089 B je Eintrag
#
# Der begrenzende Faktor ist NICHT der Ruhezustand - 50.000 Spiele sind
# im Betrieb rund 24 MB, auf einem Geraet mit 1 GB nichts. Der
# begrenzende Faktor ist die SPITZE, und die entsteht beim RESCAN:
# der alte Baum ist noch referenziert, waehrend der neue entsteht.
#
# GEMESSEN mit tools/diag_startspitze.py, 20.000 Eintraege:
#
#     wie bisher                      1005 B je Eintrag
#     alter Baum vorher freigegeben    594 B je Eintrag   -41 %
#     dazu je System geschrieben       514 B je Eintrag   -49 %
#
# WAS DAS FORMAT DAFUER KOENNEN MUSS: einzelne Systeme lesen, ohne die
# ganze Datei zu einem Baum zu machen. Beim inkrementellen Rescan
# werden die geaenderten Systeme gerade frisch von der Platte gelesen -
# sie zusaetzlich aus dem Cache mitzulesen heisst, sie doppelt im
# Speicher zu halten, nur um sie gleich wegzuwerfen.
#
# DER AUFBAU, bewusst einfach gehalten:
#
#     [Pickle System 1][Pickle System 2]...[Pickle Kopf][8 Byte Zeiger]
#
# Jedes System liegt als eigenes Pickle hintereinander. Am Ende steht
# der Kopf (Fassung, Signatur, per_syskey, und je System Anzeigename,
# Kuerzel, Offset und Laenge), und die letzten acht Byte sagen, wo der
# Kopf anfaengt. Lesen heisst also: acht Byte vom Ende, Kopf lesen,
# dann GENAU die gebrauchten Stuecke.
#
# WARUM DER KOPF HINTEN STEHT: die Offsets sind erst bekannt, wenn
# alles geschrieben ist. Vorne haette es einen zweiten Durchlauf oder
# eine Platzhalter-Luecke gebraucht - beides mehr Code und mehr, was
# schiefgehen kann.
#
# DIE ALTE DATEI WIRD WEITER GELESEN. Jeder vorhandene Nutzer hat eine
# Datei im alten Format ({"sig","per_syskey","cats"} in einem Stueck).
# Sie wird erkannt und ganz gelesen - langsamer und speicherhungriger,
# aber richtig, und nach dem ersten Schreiben ist sie weg. Ohne diesen
# Rueckfall haette jeder nach dem Update EINEN vollen Scan - bei 30.000
# Spielen Minuten, fuer nichts.
CACHE_FASSUNG = 2
_CACHE_ZEIGER = 8          # Byte am Dateiende, die auf den Kopf zeigen


def _cache_schreiben(sig, per_syskey, cats):
    """Den Cache schreiben: je System ein Pickle, Kopf am Ende.

    Geschrieben wird ueber eine .tmp-Datei und os.replace() - ein
    abgebrochener Schreibvorgang (Stromausfall, voll gelaufene Karte)
    darf keine halbe Datei hinterlassen, die beim naechsten Start als
    gueltig gelesen wird.

    JE SYSTEM EIN pickle.dump IN DIE DATEI, nicht in einen Puffer: das
    ist der Posten 'Pickle-Puffer beim Schreiben' aus der Messung oben
    (144 B je Eintrag). Ein pickle.dumps() des ganzen Baums haette die
    komplette Serialisierung zusaetzlich im Speicher."""
    verzeichnis = os.path.dirname(GAMES_CACHE)
    if verzeichnis:
        os.makedirs(verzeichnis, exist_ok=True)
    tmp = GAMES_CACHE + ".tmp%d" % os.getpid()
    try:
        with open(tmp, "wb") as f:
            inhalt = []
            for eintrag in cats:
                disp, node, sk = eintrag[0], eintrag[1], eintrag[2]
                start = f.tell()
                pickle.dump(node, f, protocol=pickle.HIGHEST_PROTOCOL)
                inhalt.append((disp, sk, start, f.tell() - start))
            kopf_start = f.tell()
            pickle.dump({"fassung": CACHE_FASSUNG, "sig": sig,
                         "per_syskey": per_syskey, "inhalt": inhalt},
                        f, protocol=pickle.HIGHEST_PROTOCOL)
            f.write(struct.pack("<Q", kopf_start))
        os.replace(tmp, GAMES_CACHE)
    except Exception:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def _cache_kopf_lesen():
    """(sig, per_syskey, handle) - und der handle enthaelt NOCH KEINEN
    Baum.

    Das ist der ganze Zweck: die Signatur entscheidet, ob der Cache
    ueberhaupt taugt, und diese Entscheidung soll nicht erst nach dem
    Aufbau von dreissigtausend Tupeln fallen.

    Faellt beim neuen Format irgendetwas aus dem Rahmen, wird die alte
    Fassung versucht (ein Stueck). Bleibt auch die unlesbar, fliegt der
    Fehler nach oben - scan_games() faengt genau diese Sorte ab und
    scannt neu."""
    with open(GAMES_CACHE, "rb") as f:
        try:
            f.seek(0, os.SEEK_END)
            gesamt = f.tell()
            if gesamt <= _CACHE_ZEIGER:
                raise ValueError("Cache-Datei zu kurz")
            f.seek(gesamt - _CACHE_ZEIGER)
            (kopf_start,) = struct.unpack("<Q", f.read(_CACHE_ZEIGER))
            if not 0 < kopf_start < gesamt - _CACHE_ZEIGER:
                raise ValueError("Kopf-Zeiger ausserhalb der Datei")
            f.seek(kopf_start)
            kopf = pickle.load(f)
            if (not isinstance(kopf, dict)
                    or kopf.get("fassung") != CACHE_FASSUNG):
                raise ValueError("fremde Cache-Fassung")
            inhalt = kopf["inhalt"]
        except Exception:
            # DIE ALTE FASSUNG: alles in einem Stueck. Sie wird ganz
            # gelesen - anders geht es nicht, dafuer war sie nicht
            # gebaut.
            f.seek(0)
            alt = pickle.load(f)
            if not isinstance(alt, dict):
                raise ValueError("Cache ist kein Verzeichnis")
            return (alt["sig"], alt.get("per_syskey"),
                    ("alt", alt["cats"]))
    return (kopf["sig"], kopf.get("per_syskey"),
            ("neu", GAMES_CACHE, inhalt))


def _cache_systeme_lesen(handle, nur=None):
    """Aus einem handle von _cache_kopf_lesen() die Liste
    [(Anzeigename, Knoten, Kuerzel), ...] bauen.

    nur=None liefert alle Systeme, nur={"NES", "SNES"} genau diese.
    Beim inkrementellen Rescan ist das der Punkt: die geaenderten
    Systeme stehen schon frisch eingelesen da und werden hier
    ausgelassen, statt den Speicher zweimal zu belegen.

    Die Reihenfolge der Datei bleibt erhalten - der Aufrufer sortiert
    anschliessend ohnehin nach GAME_SYSTEMS, aber eine Funktion, die
    je Aufruf eine andere Reihenfolge liefert, waere eine Falle fuer
    den naechsten Leser."""
    if not handle:
        return []
    if handle[0] == "alt":
        if nur is None:
            return handle[1]
        return [e for e in handle[1] if e[2] in nur]
    _, pfad, inhalt = handle
    raus = []
    with open(pfad, "rb") as f:
        for disp, sk, start, laenge in inhalt:
            if nur is not None and sk not in nur:
                continue
            f.seek(start)
            # Nur dieses Stueck - pickle.loads() auf den gelesenen
            # Bytes statt pickle.load(f), damit ein beschaedigter
            # Eintrag nicht ueber seine Grenze hinaus weiterliest.
            raus.append((disp, pickle.loads(f.read(laenge)), sk))
    return raus

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
SCAN_LOGIC_VERSION = 5   # 1 = Basis, 2 = "(unl)"/"(pirate)" nicht mehr Junk,
                         # 3 = OPTIONAL_GAME_SYSTEMS (SNES_Tracker-Core),
                         # 4 = SMW Hacks (games/SNES/SMW_HACKS),
                         # 5 = Einzelspiel-Ordner aufloesen (Build 156)

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
    netz = _netz_mountpunkte()
    for base in fe.paths.GAMES_BASES:
        if not os.path.isdir(base):
            continue
        # BUGFIX (Nutzer-Rueckmeldung ueber einen Bekannten: "seine Spiele
        # liegen auf einem NAS, bei JEDEM Neustart werden sie neu
        # eingelesen"): hier stand bisher nur
        #     tag = "usb:" if "/media/usb" in base else "fat:"
        # Ein NAS haengt ueblicherweise unter /media/fat/cifs/... - es
        # bekam damit dieselbe Kennung wie die SD-Karte. Zwei Folgen,
        # beide schlecht:
        #
        # 1. Beim Kaltstart ist die Freigabe oft noch nicht eingehaengt.
        #    Die frisch gebildete Signatur enthaelt die NAS-Ordner dann
        #    nicht, der Cache (vom letzten Lauf MIT NAS) schon - die
        #    Signaturen weichen ab, es wird komplett neu eingelesen.
        #    Genau dafuer gibt es in scan_games() bereits ein
        #    Sicherheitsnetz ("Cache erwartet X, X fehlt -> warten"),
        #    das aber ausschliesslich auf "usb:" geprueft hat und beim
        #    NAS deshalb nie ansprang.
        # 2. Ein Ordner "SNES" auf der SD-Karte und einer auf dem NAS
        #    ergaben denselben Signatur-Schluessel "fat:SNES" - beim
        #    inkrementellen Vergleich waren sie nicht auseinanderzuhalten.
        #
        # Eine eigene Kennung "nas:" loest beides. Sie ist genauso
        # ortsunabhaengig wie "usb:"/"fat:" (nur Kennung + relativer
        # Ordnername, siehe Erklaerung oben), aendert sich also nicht,
        # wenn die Freigabe einmal woanders eingehaengt wird.
        if any(base == mp or base.startswith(mp.rstrip("/") + "/")
               for mp in netz):
            tag = "nas:"
        elif "/media/usb" in base:
            tag = "usb:"
        else:
            tag = "fat:"
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
    global _LETZTE_SIGNATUR_MIT_NAS
    _LETZTE_SIGNATUR_MIT_NAS = any(e[0].startswith("nas:") for e in sig)
    sig.append(("__scan_logic_version__", SCAN_LOGIC_VERSION))
    # NEU: der Filterschalter gehoert in den Fingerabdruck. Die Filter
    # wirken beim EINLESEN - ohne diesen Eintrag wuerde ein Umschalten
    # erst beim naechsten ohnehin faelligen Neuscan sichtbar, und der
    # Nutzer haette den Eindruck, der Schalter tue nichts.
    sig.append(("__rom_filter__", 1 if rom_filter_enabled() else 0))
    # Build 156: derselbe Grund - der Schalter formt den Baum beim
    # Einlesen, nicht beim Anzeigen.
    sig.append(("__einzelordner__", 1 if einzelordner_aufloesen() else 0))
    for sk in per_syskey:
        per_syskey[sk].sort(key=lambda t: (t[0], t[1] is None, t[1]))
    return sig, per_syskey

# Merker (siehe _maybe_rescan_for_late_mount() in frontend.py): enthielt
# die zuletzt verwendete Signatur bereits Eintraege von einer Netzwerk-
# Freigabe? Nur wenn NICHT, lohnt sich spaeter ein automatisches
# Nachziehen, sobald eine Freigabe auftaucht.
_LETZTE_SIGNATUR_MIT_NAS = False


def letzter_scan_hatte_nas():
    """True, wenn beim letzten Ermitteln der Spieleliste bereits Ordner
    von einer Netzwerk-Freigabe dabei waren."""
    return _LETZTE_SIGNATUR_MIT_NAS


# Welche ROM-Ordner beim letzten Einlesen ueberhaupt DA waren (nur die
# Kennungen, ohne Zeitstempel). Siehe ordner_sind_dazugekommen().
_LETZTE_ORDNER = set()

# Die Selbstsperre von ordner_sind_dazugekommen() - siehe dort.
DAZU_SPERRE = 8.0
_DAZU_BIS = 0.0
_DAZU_WERT = False

# NEU (Build 229): der Fingerabdruck wird NEBENHER gebildet.
#
# DER BEFUND DES NUTZERS: "ab und an wenn ich ordner und kategorien
# wechseln hab ich manchmal denn eindruck das es kleine haenger gibt."
# Im Bericht vom 03.10. steht dazu, Abschnitt J, Liste galerie:
#
#     20.9/Schritt  _games_signature > getmtime
#      0.6/Schritt  _games_signature > isdir
#
# Ueber 30 Schritte sind das rund 630 getmtime-Aufrufe. Abschnitt G
# nennt ein warmes os.stat mit 0,18 ms - also rund 110 ms, und zwar in
# EINEM einzigen Schritt. Das ist kein Rauschen, das ist genau der
# Haenger, den er beschreibt.
#
# WARUM AUSGERECHNET BEIM WECHSELN: der Aufrufer in frontend.py schiebt
# die Frage auf, solange eine Taste gehalten wird (_nav_active()). Sie
# laeuft also genau dann, wenn man AUFHOERT zu scrollen oder die
# Kategorie wechselt.
#
# Die Sperre von Build 224 war richtig, aber sie macht die Frage nur
# selten - nicht billig. Jetzt laeuft die Arbeit in einem eigenen
# Faden, und der Zeichenweg bekommt sofort die zuletzt bekannte
# Antwort. Die ist hoechstens acht Sekunden alt, und genau das stand
# schon bei Build 224 hier: es geht um ein Laufwerk, das ohnehin erst
# irgendwann auftaucht.
_DAZU_FADEN = None
_DAZU_SPERRE_OBJ = _threading.Lock()

# NACHGEMESSEN (Build 230): nebenher war nicht genug.
#
# Der Bericht vom 03.10., 10:43, mit Build 229: REST in der Galerie von
# 14,04 auf 6,83 ms - der Zeichenweg wartet also wirklich nicht mehr.
# ABER: "cover 1.91 (davon Karte 19.68 in 22 Zugriffen)", vorher 2,83 ms
# fuer dieselben 23 Zugriffe. Die Arbeit war nicht weg, sie lag jetzt
# NEBENAN - und streitet sich mit dem Zeichenweg um dieselbe SD-Karte.
# "20.8/Schritt _games_signature > getmtime" steht unveraendert da.
#
# Also der Blick in die Funktion statt noch eine Verlagerung, und dort
# steht der eigentliche Fehler schwarz auf weiss: die Frage lautet "ist
# ein Ordner DAZUGEKOMMEN", verglichen werden ueber _ordner_kennungen()
# nur die NAMEN - und trotzdem holt _games_signature() fuer jeden
# Systemordner jedes Basispfads einen Zeitstempel. Rund 630 stat-Aufrufe
# je Durchgang, deren Ergebnis anschliessend weggeworfen wird.
#
# Ein neuer Name kann aber nur auftauchen, wenn sich an einem BASISPFAD
# etwas getan hat: entweder ist einer aufgetaucht (die spaet angelaufene
# USB-Platte, um die es hier geht), oder in einem ist etwas angelegt
# worden - und das steht in seinem eigenen Zeitstempel. Das sind eine
# Handvoll stat-Aufrufe statt sechshundert. Erst wenn sich dort etwas
# geruehrt hat, lohnt der teure Durchgang.
_LETZTE_BASEN = ()


def _basen_merkmal():
    """Welche Basispfade gibt es, und wann wurden sie zuletzt angefasst?

    Eine Handvoll stat-Aufrufe - die billige Vorfrage zu
    ordner_sind_dazugekommen(). Ein Basispfad, den es nicht gibt, faellt
    weg; taucht er auf, ist das Merkmal allein dadurch ein anderes."""
    merkmal = []
    for base in fe.paths.GAMES_BASES:
        try:
            merkmal.append((base, int(os.path.getmtime(base))))
        except OSError:
            continue
    merkmal.sort()
    return tuple(merkmal)


def dazu_sperre_loesen():
    """Die Selbstsperre sofort aufheben.

    Zwei Aufrufer, und beide aus gutem Grund: nach einem echten
    Einlesen aendert sich _LETZTE_ORDNER, die gemerkte Antwort waere
    also auf eine andere Frage gegeben worden - und die Tests pruefen
    die Erkennung selbst, nicht die Sperre."""
    global _DAZU_BIS, _DAZU_WERT
    _DAZU_BIS = 0.0
    _DAZU_WERT = False


def dazu_fertig_abwarten(sekunden=5.0):
    """Auf einen laufenden Hintergrundfaden warten - NUR fuer Tests.

    Im Betrieb wartet niemand: der Zeichenweg nimmt die zuletzt
    bekannte Antwort. Ein Test, der die ERKENNUNG prueft, braucht aber
    ein Ergebnis und keine Zusage."""
    faden = _DAZU_FADEN
    if faden is not None and faden.is_alive():
        faden.join(sekunden)
    return faden is None or not faden.is_alive()


def _dazu_nachsehen():
    """Der Fingerabdruck - laeuft im Hintergrundfaden.

    _games_signature() setzt _LETZTE_SIGNATUR_MIT_NAS als Nebenwirkung.
    Diese Abfrage hier ist aber nur eine ZWISCHENDURCH-Frage und darf
    den Merker des letzten echten Einlesens nicht ueberschreiben -
    sonst haette letzter_scan_hatte_nas() nach dem ersten Aufruf eine
    andere Bedeutung als sein Name sagt."""
    global _DAZU_WERT, _LETZTE_SIGNATUR_MIT_NAS
    merker = _LETZTE_SIGNATUR_MIT_NAS
    try:
        sig, _per = _games_signature()
    except Exception:                                    # noqa: BLE001
        return
    finally:
        _LETZTE_SIGNATUR_MIT_NAS = merker
    # EINE Zuweisung, und zwar die letzte: wer die Antwort liest,
    # bekommt entweder die alte oder die neue, nie etwas dazwischen.
    _DAZU_WERT = bool(_ordner_kennungen(sig) - _LETZTE_ORDNER)


def ordner_sind_dazugekommen():
    """Gibt es JETZT Spieleordner, die es beim letzten Einlesen noch
    nicht gab?

    NEUES FEATURE (Build 117, Nutzer-Rueckmeldung: "ich habe mal eine
    andere USB-Festplatte angeschlossen, die startet wohl etwas
    langsamer - also wird bei jedem Frontendstart versucht, die
    Spieleliste neu aufzubauen, und ich muss immer erst unter Wartung
    von Hand neu einlesen").

    Fuer genau dieses Problem gab es schon ein Sicherheitsnetz
    (_maybe_rescan_for_late_mount() in frontend.py) - es hat aber nur
    nach NETZLAUFWERKEN gesehen, weil es fuer einen NAS-Nutzer gebaut
    wurde. Eine langsam anlaufende USB-Platte fiel durchs Raster,
    obwohl es dasselbe Problem ist: beim Scan war der Ordner noch nicht
    da, kurz darauf schon.

    Bewusst NUR "dazugekommen", nicht "veraendert": ein veraenderter
    Zeitstempel passiert im Alltag staendig (ein gestartetes Spiel
    reicht) und wuerde das Netz in einen Dauerscanner verwandeln. Ein
    Ordner, den es vorher GAR NICHT gab, ist dagegen genau das Signal,
    auf das es ankommt.

    Der Aufruf kostet dasselbe wie der Fingerabdruck beim Start: ein
    os.path.isdir() je Basispfad und Systemordner, keine Tiefensuche."""
    global _LETZTE_SIGNATUR_MIT_NAS, _DAZU_BIS, _DAZU_WERT
    if not _LETZTE_ORDNER:
        return False        # noch gar nicht eingelesen - nichts zu vergleichen
    # EIGENE SPERRE, unabhaengig vom Aufrufer (Build 224).
    #
    # Der Aufrufer in frontend.py drosselt diese Frage bereits auf alle
    # acht Sekunden - und trotzdem stand im Bericht des Nutzers vom
    # 02.10. in Abschnitt J "20,9/Schritt _games_signature > getmtime",
    # also rund ein kompletter Durchlauf JE SCROLLSCHRITT. Woran die
    # Drosselung dort vorbeigeht, liess sich hier nicht nachstellen (der
    # Pruefstand friert die Uhr ein, siehe tools/_harness.py).
    #
    # Statt weiter zu raten, sperrt die Funktion sich jetzt SELBST: wer
    # auch immer sie ruft, bekommt innerhalb von acht Sekunden dieselbe
    # Antwort ohne einen einzigen Zugriff auf die Karte. Das ist genau
    # die Zusicherung, die der Zeichenweg braucht, und sie haengt nicht
    # mehr daran, dass eine zweite Stelle richtig zaehlt.
    #
    # Die Frage lautet "ist ein Ordner DAZUGEKOMMEN" - eine Antwort, die
    # acht Sekunden alt ist, war noch nie ein Problem: es geht um ein
    # Laufwerk, das ohnehin irgendwann auftaucht.
    jetzt = time.monotonic()
    if jetzt < _DAZU_BIS:
        return _DAZU_WERT
    _DAZU_BIS = jetzt + DAZU_SPERRE
    # DIE BILLIGE VORFRAGE (Build 230): hat sich an den Basispfaden
    # ueberhaupt etwas geruehrt? Wenn nicht, kann kein Ordner
    # dazugekommen sein - und der teure Durchgang entfaellt ganz. Siehe
    # den Block bei _basen_merkmal(): das sind eine Handvoll
    # stat-Aufrufe statt rund sechshundert.
    try:
        if _basen_merkmal() == _LETZTE_BASEN:
            return _DAZU_WERT
    except Exception:                                    # noqa: BLE001
        return _DAZU_WERT
    # GEAENDERT (Build 229): hier wird nichts mehr GERECHNET, hier wird
    # nur angestossen. Der Aufrufer sitzt im Zeichenweg und bekommt die
    # zuletzt bekannte Antwort - siehe den Block bei _DAZU_FADEN.
    global _DAZU_FADEN
    with _DAZU_SPERRE_OBJ:
        if _DAZU_FADEN is None or not _DAZU_FADEN.is_alive():
            _DAZU_FADEN = _threading.Thread(target=_dazu_nachsehen,
                                            name="dragend-ordnerblick",
                                            daemon=True)
            try:
                _DAZU_FADEN.start()
            except RuntimeError:
                # Kein Faden mehr zu haben ist kein Grund, das Frontend
                # aufzuhalten - dann eben beim naechsten Mal.
                _DAZU_FADEN = None
    return _DAZU_WERT


def _ordner_kennungen(sig):
    """Nur die Ort-Kennungen aus einem Fingerabdruck, ohne Zeitstempel
    und ohne die __-Sondereintraege."""
    return set(e[0] for e in sig
               if ":" in e[0] and not e[0].startswith("__"))


def ordner_merken(sig):
    """Festhalten, welche Ordner beim jetzt verwendeten Einlesen da
    waren - Grundlage fuer ordner_sind_dazugekommen()."""
    global _LETZTE_ORDNER, _LETZTE_BASEN
    _LETZTE_ORDNER = _ordner_kennungen(sig)
    # Build 230: dieselbe Momentaufnahme fuer die billige Vorfrage -
    # beide muessen vom selben Zeitpunkt stammen, sonst vergleicht die
    # eine Haelfte mit einem Stand, den die andere nie gesehen hat.
    _LETZTE_BASEN = _basen_merkmal()
    # Die Vergleichsgrundlage ist eine andere - was eben gemerkt wurde,
    # war die Antwort auf eine andere Frage (Build 224).
    dazu_sperre_loesen()


def _netz_mountpunkte():
    """Alle aktuell eingehaengten Netzwerk-Freigaben (CIFS/NFS) als Liste
    von Einhaengepunkten. Ein Lesevorgang auf /proc/mounts - kostet
    praktisch nichts und ist die einzige zuverlaessige Auskunft darueber,
    ob ein Pfad ueber das Netz kommt oder von der Karte."""
    punkte = []
    try:
        with open("/proc/mounts") as f:
            for line in f:
                teile = line.split()
                if len(teile) >= 3 and teile[2] in (
                        "cifs", "smb3", "smbfs", "nfs", "nfs4"):
                    punkte.append(teile[1].replace("\\040", " "))
    except OSError:
        pass
    return punkte


def _sig_expects(sig, praefix):
    """True, wenn eine Signatur mindestens einen Eintrag mit dieser
    Ortskennung enthaelt."""
    return any(entry[0].startswith(praefix) for entry in sig)


def _wait_for_nas_mount(max_wait=60.0, poll=0.5):
    """Auf eine Netzwerk-Freigabe warten.

    Bewusst UNABHAENGIG von der Option "Beim Start auf NAS/Netzwerk
    warten": diese Funktion wird nur aufgerufen, wenn der Cache selbst
    beweist, dass zuletzt Spiele von einer Freigabe gelesen wurden.
    Dann ist Warten keine Vermutung mehr, sondern die richtige Antwort -
    genau dieselbe Ueberlegung wie beim USB-Zweig, der ebenfalls ohne
    Option auskommt.

    Wartet nicht nur auf die Einhaengung selbst, sondern danach noch auf
    einen stabilen Ordnerinhalt: eine frisch eingehaengte Freigabe kann
    einen Moment lang leer erscheinen.
    """
    t0 = time.monotonic()
    while not _has_network_mount():
        if time.monotonic() - t0 >= max_wait:
            LOG("_wait_for_nas_mount: keine Freigabe nach %.0fs - "
                "fahre trotzdem fort" % max_wait)
            return False
        time.sleep(poll)
    fe.paths.GAMES_BASES = fe.paths._discover_games_bases()
    letzte = None
    while time.monotonic() - t0 < max_wait:
        netz = _netz_mountpunkte()
        jetzt = []
        for base in fe.paths.GAMES_BASES:
            if not any(base == mp or base.startswith(mp.rstrip("/") + "/")
                       for mp in netz):
                continue
            try:
                jetzt.append((base, len(os.listdir(base))))
            except OSError:
                jetzt.append((base, -1))
        if jetzt and jetzt == letzte:
            LOG("_wait_for_nas_mount: Freigabe da und stabil nach %.1fs"
                % (time.monotonic() - t0))
            return True
        letzte = jetzt
        time.sleep(poll)
        fe.paths.GAMES_BASES = fe.paths._discover_games_bases()
    LOG("_wait_for_nas_mount: Zeitlimit (%.0fs) erreicht" % max_wait)
    return False


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


# Wie lange beim KALTSTART auf eine USB-Platte gewartet wird, von der
# der Cache weiss, dass dort Spiele liegen. Grosszuegig, weil die
# Alternative teurer ist: ein kompletter Scan ohne die Platte, und kurz
# darauf der automatische zweite mit ihr (siehe scan_games()). Im
# Regelfall - Platte rechtzeitig oben - wird hier keine einzige Sekunde
# gewartet, weil der Zweig gar nicht betreten wird.
USB_WARTEN_KALTSTART = 45.0


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

def scan_games(force=False, progress_cb=None, warte_cb=None):
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
            cached_sig, cached_per_syskey, data = _cache_kopf_lesen()
            if cached_sig == sig:
                cats = _cache_systeme_lesen(data)
                LOG("Spieleliste aus Cache (%d Systeme)" % len(cats))
                ordner_merken(sig)
                return cats
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
    # NEU (siehe ausfuehrliche Begruendung bei der Ortskennung "nas:" in
    # _games_signature()): dasselbe Sicherheitsnetz fuer Netzwerk-
    # Freigaben. Erwartet der Cache NAS-Ordner, sehen wir aber gerade
    # keine, dann ist die Freigabe schlicht noch nicht eingehaengt -
    # warten und erneut vergleichen, statt die ganze Sammlung sinnlos
    # neu einzulesen. Ohne diesen Zweig passierte genau das bei JEDEM
    # Kaltstart, solange das Netz langsamer hochkam als das Frontend.
    if (not force and cached_sig is not None
            and _sig_expects(cached_sig, "nas:")
            and not _sig_expects(sig, "nas:")):
        LOG("scan_games: Cache erwartet NAS, noch nicht gemountet - warte")
        _wait_for_nas_mount()
        sig, per_syskey = _games_signature()
        if cached_sig == sig:
            cats = _cache_systeme_lesen(data)
            LOG("Spieleliste aus Cache nach NAS-Mount (%d Systeme)"
                % len(cats))
            return cats

    if (not force and cached_sig is not None
            and _sig_expects_usb(cached_sig) and not _sig_expects_usb(sig)):
        # GEAENDERT (Build 119, Nutzer-Rueckmeldung: "mit der USB-Platte
        # findet das Frontend sie jetzt zwar, aber er liest sie beim
        # Start quasi nochmal ein, das macht er bei jedem kalten
        # Neustart, das nervt").
        #
        # Das Nachziehen aus Build 117 hat das Symptom behoben, nicht
        # die Ursache: beim Kaltstart war die Platte nach zehn Sekunden
        # immer noch nicht da, also lief ein kompletter Scan OHNE sie -
        # und kurz darauf der automatische zweite MIT ihr. Zwei Scans
        # statt keinem.
        #
        # Hier zu warten kostet dagegen NICHTS im Normalfall: dieser
        # Zweig wird nur betreten, wenn der Cache USB-Ordner erwartet
        # und gerade keine da sind. Ist die Platte rechtzeitig oben -
        # der Regelfall - kommt das Frontend hier gar nicht vorbei. Eine
        # anlaufende Festplatte braucht nach einem Kaltstart durchaus
        # 15 bis 30 Sekunden; zehn waren schlicht zu knapp bemessen.
        LOG("scan_games: Cache erwartet USB, noch nicht gemountet - warte")
        if warte_cb:
            # Ohne ein Lebenszeichen waeren das bis zu 45 Sekunden
            # schwarzer Bildschirm - da haelt es niemand aus, ohne den
            # Stecker zu ziehen.
            try:
                warte_cb()
            except Exception:                            # noqa: BLE001
                pass
        usb_ready = _wait_for_usb_stable(max_wait=USB_WARTEN_KALTSTART)
        waited_already = True
        sig, per_syskey = _games_signature()
        if cached_sig == sig:
            cats = _cache_systeme_lesen(data)
            LOG("Spieleliste aus Cache nach USB-Mount (%d Systeme)"
                % len(cats))
            ordner_merken(sig)
            return cats

    if not waited_already:
        usb_ready = _wait_for_usb_stable()

    # DIAGNOSE (Nutzer-Rueckmeldung: "scannt schon wieder" - nach dem
    # nas:-Fix nur noch kurz, also inkrementell, aber eben immer noch).
    # Genau hier ist der Punkt, an dem feststeht: die Signatur passt
    # nicht. WELCHER Eintrag sich unterscheidet, stand bisher nirgends -
    # ohne diese Zeilen bleibt nur Raten. Laeuft ausschliesslich im
    # Fehlerfall (bei passendem Cache ist die Funktion langst zurueck),
    # kostet im Normalbetrieb also nichts.
    if cached_sig is not None:
        alt_map = dict(cached_sig)
        neu_map = dict(sig)
        nur_alt = sorted(set(alt_map) - set(neu_map))
        nur_neu = sorted(set(neu_map) - set(alt_map))
        geaendert = sorted(k for k in (set(alt_map) & set(neu_map))
                           if alt_map[k] != neu_map[k])
        LOG("SIG-DIFF: %d nur im Cache, %d nur jetzt, %d mit anderer Zeit"
            % (len(nur_alt), len(nur_neu), len(geaendert)))
        for k in nur_alt[:8]:
            LOG("SIG-DIFF   nur im Cache: %s (Zeit %s)" % (k, alt_map[k]))
        for k in nur_neu[:8]:
            LOG("SIG-DIFF   nur jetzt   : %s (Zeit %s)" % (k, neu_map[k]))
        for k in geaendert[:8]:
            LOG("SIG-DIFF   Zeit anders : %s  Cache=%s  jetzt=%s"
                % (k, alt_map[k], neu_map[k]))
        LOG("SIG-DIFF: Netz-Einhaengepunkte gerade: %s"
            % (", ".join(_netz_mountpunkte()) or "keine"))
        LOG("SIG-DIFF: Spiele-Wurzeln gerade: %s"
            % ", ".join(b for b in fe.paths.GAMES_BASES if os.path.isdir(b)))

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
            # NUR DIE UNVERAENDERTEN SYSTEME aus der Datei holen
            # (Build 248). Die geaenderten sind gerade frisch
            # eingelesen worden - sie aus dem Cache mitzulesen hiesse,
            # sie doppelt im Speicher zu halten, nur um sie gleich
            # wegzuwerfen.
            old_by_sk = {sk: (disp, node) for disp, node, sk
                         in _cache_systeme_lesen(
                             data, nur=(all_syskeys - changed_syskeys))}
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
            # Build 248: dieselbe Ueberlegung wie beim vollen Scan
            # unten, nur kleiner. 'cats' benutzt die unveraenderten
            # Knoten WEITER (dieselben Objekte, nicht Kopien) - frei
            # wird hier also nur, was zu den GEAENDERTEN Systemen
            # gehoert, plus die beiden Hilfs-Verzeichnisse. Bei einem
            # einzelnen neu eingelesenen System ist das wenig, bei
            # einem Rescan nach dem Umsortieren einer grossen Platte
            # viel - und es kostet nichts.
            fresh = None
            fresh_by_sk = None
            old_by_sk = None
            data = None
        elif not changed_syskeys:
            # Sollte praktisch nicht vorkommen (sig haette dann oben
            # schon vollstaendig gepasst) - reiner Sicherheits-Rueckfall.
            cats = _cache_systeme_lesen(data)

    if cats is None:
        # DEN ALTEN BAUM FREIGEBEN, BEVOR DER NEUE ENTSTEHT
        # (Build 248). Eine Zeile, und sie ist die groesste
        # Einzelersparnis am Speicher, die dieses Projekt hat.
        #
        # WAS VORHER PASSIERTE: 'data' haelt den komplett
        # eingelesenen alten Spielebaum und bleibt bis zum Ende
        # dieser Funktion referenziert. Der inkrementelle Zweig
        # darueber BRAUCHT ihn (er uebernimmt daraus die
        # unveraenderten Systeme) - dieser hier nicht: er baut alles
        # neu. Bis Build 247 lagen hier also zwei vollstaendige
        # Baeume gleichzeitig im Speicher, und gleich darauf kam der
        # Pickle-Puffer zum Wegschreiben obendrauf.
        #
        # GEMESSEN (tools/diag_startspitze.py, 50.000 Eintraege, je
        # Variante ein eigener Prozess, VmRSS):
        #
        #     wie bisher                 55,2 MB   1158 B je Eintrag
        #     nur diese Freigabe         35,6 MB    746 B je Eintrag
        #     dazu je System schreiben   23,8 MB    498 B je Eintrag
        #
        # Die Freigabe allein bringt 36 %, zusammen mit dem
        # stueckweisen Schreiben (_cache_schreiben() oben) sind es
        # 57 %. Die beiden gehoeren zusammen: diese Zeile nimmt den
        # alten Baum weg, das Schreiben vermeidet den Pickle-Puffer
        # fuer den neuen.
        #
        # Hochgerechnet: bei 250.000 Spielen 124 statt 290 MB. Die
        # DAUERLAST war nie das Problem (50.000 Spiele sind im
        # Betrieb rund 24 MB, siehe FUND_Speicher_je_Eintrag) - die
        # Spitze beim Rescan ist es, und genau sie ist die Grenze
        # fuer den groessten denkbaren Bestand.
        #
        # Kein gc.collect() noetig: der Baum ist eine Liste von
        # Dicts ohne Zyklen, die Zaehlung gibt ihn sofort frei.
        data = None
        cached_per_syskey = None
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
        # Trotzdem merken, welche Ordner beim Scan da waren - genau
        # DIESER Fall ist der, in dem spaeter welche dazukommen (die
        # Platte laeuft an), und das Sicherheitsnetz soll das sehen.
        ordner_merken(sig)
        return cats

    sig, per_syskey = _games_signature()
    # Festhalten, welche Ordner JETZT da waren - daran erkennt das
    # Sicherheitsnetz spaeter, ob nachtraeglich welche dazugekommen
    # sind (siehe ordner_sind_dazugekommen()).
    ordner_merken(sig)
    try:
        _cache_schreiben(sig, per_syskey, cats)
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

def _einzelspiel(node):
    """Das eine Spiel eines Knotens, der NUR dieses eine Spiel und
    keinen Unterordner enthaelt - sonst None (Build 156).

    Der Aufrufer setzt dieses Spiel dann an die Stelle des Ordners.
    Siehe einzelordner_aufloesen() in fe/settings.py fuer das Warum.

    Warum die Bedingung so eng ist: ein Ordner mit ZWEI Spielen ist
    eine echte Auswahl (Disc 1 / Disc 2), und ein Ordner mit einem
    Spiel UND einem Unterordner ist eine Sammlung. In beiden Faellen
    wuerde das Aufloesen etwas unerreichbar machen."""
    if node["folders"]:
        return None
    if len(node["items"]) != 1:
        return None
    return node["items"][0]


def _node_count(node):
    """Rekursive Gesamtzahl aller Eintraege (inkl. aller Unterordner)
    fuer die Anzeige in der Kategorienliste."""
    n = len(node["items"])
    for sub in node["folders"].values():
        n += _node_count(sub)
    return n

def _zip_baum(zip_pfad, syskey, rbf, extmap, filter_an):
    """Ein ZIP-Archiv als Baumknoten - genau so, als waere es ein
    Ordner. Unterordner im Archiv werden zu Unterordnern.

    NEUES FEATURE (Build 121, Nutzerwunsch nach dem Vergleich mit
    Degauss: "ZIP nehmen wir mit rein"). Bis dahin waren ROMs in
    Archiven schlicht unsichtbar - der einzige Punkt aus dem Vergleich,
    bei dem uns schlicht etwas fehlte.

    WARUM DAS UEBERHAUPT GEHT, ohne irgendetwas zu entpacken: MiSTer
    behandelt ein Archiv im MGL-Pfad wie einen Ordner. Die offizielle
    Dokumentation zeigt es ausdruecklich so:

        path="some/other.zip/path/dummy.gg"

    Damit aendert sich am Startweg (write_mgl() in fe/launch.py) KEINE
    Zeile - wir setzen den Pfad einfach durch das Archiv hindurch
    zusammen. Das Archiv wird nie entpackt, nicht einmal teilweise;
    gelesen wird nur das Inhaltsverzeichnis am Ende der Datei.

    Zwei Dinge bewusst so und nicht anders:

    - Ein Archiv OHNE passende ROMs taucht gar nicht erst auf. Viele
      Sammlungen legen neben den ROMs noch Handbuecher oder Textdateien
      als Archiv ab; ein leerer Ordner dafuer waere nur im Weg.
    - Ein kaputtes oder halb kopiertes Archiv darf den ganzen Scan
      nicht umwerfen. Es faellt still weg, so wie eine unlesbare Datei
      auch.
    """
    node = _empty_node()
    try:
        import zipfile
        with zipfile.ZipFile(zip_pfad) as archiv:
            eintraege = archiv.namelist()
    except Exception:                                    # noqa: BLE001
        # Kaputt, kein echtes Archiv, zu gross, mitten im Kopieren -
        # alles derselbe Fall: es gibt hier nichts zu sehen.
        return node

    for name in sorted(eintraege, key=str.lower):
        if name.endswith("/"):
            continue                                     # reiner Ordnereintrag
        teile = [t for t in name.split("/") if t and t not in (".", "..")]
        if not teile or any(t.startswith(".") for t in teile):
            continue
        basis, ext = os.path.splitext(teile[-1])
        ext = ext.lower()
        if ext not in extmap:
            continue
        if basis.lower() in IGNORE_ROM_BASENAMES:
            continue
        if filter_an and (_is_junk(basis) or _is_japan_only(basis)):
            continue
        # Bis zum Dateinamen absteigen, Unterordner im Archiv anlegen.
        ziel = node
        for ordner in teile[:-1]:
            ziel = ziel["folders"].setdefault(ordner, _empty_node())
        # Der Pfad laeuft DURCH das Archiv - genau die Schreibweise,
        # die MGL erwartet.
        voll = zip_pfad + "/" + "/".join(teile)
        ziel["items"].append((basis, "game",
                              (voll, ext, syskey, rbf, extmap[ext])))

    einzeln = einzelordner_aufloesen()

    def _aufraeumen(n):
        # Von unten nach oben: erst der Unterordner, dann die Frage, ob
        # er danach nur noch ein Spiel enthaelt. Andersherum bliebe ein
        # zweistufiger Ordner stehen, dessen Inhalt sich gerade erst
        # auf ein Spiel zusammengezogen hat.
        hoch = []
        for unter in list(n["folders"]):
            _aufraeumen(n["folders"][unter])
            sub = n["folders"][unter]
            nur = _einzelspiel(sub) if einzeln else None
            if nur is not None:
                hoch.append(nur)
                del n["folders"][unter]
            elif not (sub["items"] or sub["folders"]):
                del n["folders"][unter]
        n["items"] = _dedupe_items(n["items"] + hoch)

    _aufraeumen(node)
    return node


# Build 200: Schutz gegen Symlink-Schleifen beim Einlesen.
#
# ANLASS: Degauss hat in v0.9.0 genau das reparieren muessen ("Arcade
# indexing now excludes top-level cores support directory, preventing
# symlink loops from aborting library rebuilds"). Beim Nachsehen stand
# es bei uns schlechter: die OBERE Ebene ist seit langem abgesichert
# (seen_roots mit realpath in _scan_system()), der rekursive Abstieg
# aber gar nicht. _scan_folder_tree() steigt in jeden Ordner, den
# os.path.isdir() bejaht - und isdir() folgt Symlinks. Ein Link, der
# nach oben zeigt (games/SNES/alles -> /media/fat/games), laesst das
# Einlesen endlos kreisen, bis Python mit RecursionError abbricht. Bei
# 97.000 Eintraegen ist das kein Gedankenspiel, und es trifft den
# unangenehmsten Moment: den Neuaufbau der Bibliothek.
#
# GEPRUEFT WIRD GEGEN DIE VORFAHREN, nicht gegen "schon mal gesehen".
# Der Unterschied ist wichtig: eine globale Menge wuerde auch einen
# Ordner ueberspringen, der voellig legitim ein zweites Mal auftaucht
# (zwei Links auf dieselbe Sammlung), und damit Eintraege verschwinden
# lassen. Nur ein Ordner, der auf dem WEG HIERHER schon vorkam, ist eine
# Schleife. Damit aendert sich fuer alle anderen nichts.
#
# UND FAST OHNE KOSTEN: realpath() ist teuer (mehrere Systemaufrufe je
# Ordner), wird hier aber nur fuer SYMLINKS gebraucht. Ein normaler
# Unterordner kann keine Schleife bauen, sein echter Pfad ist einfach
# der des Vaters plus Name - das rechnet man ohne einen einzigen
# Systemaufruf aus. Bezahlt wird also ein lstat je Ordner, nicht je
# Datei.
SCAN_MAX_TIEFE = 24

_SCAN_GEMELDET = set()


def _scan_schleife_melden(was, pfad):
    """Eine uebersprungene Stelle EINMAL ins Log schreiben.

    Einmal je Pfad, nicht je Versuch: bei einer Schleife kaeme dieselbe
    Meldung sonst dutzendfach, und ein Log, das sich wiederholt, liest
    niemand mehr. Gemeldet wird ueberhaupt, weil ein stillschweigend
    weggelassener Ordner genau die Sorte Fehler ist, die man erst
    bemerkt, wenn Spiele fehlen."""
    if pfad in _SCAN_GEMELDET:
        return
    _SCAN_GEMELDET.add(pfad)
    LOG("Einlesen: %s - uebersprungen: %s" % (was, pfad))


def _scan_folder_tree(path, syskey, rbf, extmap, _tiefe=0, _vorfahren=(),
                      _real=None):
    """Rekursiv EINEN Ordner scannen, gibt einen Baumknoten zurueck -
    beliebig tief verschachtelt, spiegelt die eigene Ordnerstruktur/
    Sortierung 1:1 wider. Bekannte Boot-/Testdateien, Beta/Proto/Hack-
    Tags und rein japanische Titel werden wie bisher ausgefiltert.

    _tiefe, _vorfahren, _real sind der Schleifenschutz aus Build 200 und
    gehen nur an die Rekursion - siehe SCAN_MAX_TIEFE oben. Aufrufer von
    aussen lassen sie weg."""
    node = _empty_node()
    if _real is None:
        try:
            _real = os.path.realpath(path)
        except OSError:
            _real = path
    if not _vorfahren:
        _vorfahren = (_real,)
    try:
        entries = sorted(os.listdir(path), key=str.lower)
    except OSError:
        return node
    # Einmal pro Ordner abfragen statt pro Datei - der Schalter ist eine
    # Dateisystem-Pruefung, und die soll bei mehreren tausend ROMs nicht
    # tausendfach laufen.
    _filter_an = rom_filter_enabled()
    # NEU (Build 156): ein Ordner mit genau einem Spiel wird durch
    # dieses Spiel ersetzt. Betrifft vor allem CD-Systeme, bei denen
    # jedes Spiel in einem eigenen Ordner liegt, weil eine .cue
    # mehrere .bin mitbringt - siehe _einzelspiel() und
    # einzelordner_aufloesen() in fe/settings.py.
    _einzeln = einzelordner_aufloesen()
    raw_items = []
    for entry in entries:
        if entry.startswith("."):
            continue
        full = os.path.join(path, entry)
        if os.path.isdir(full):
            # Build 200: der Schleifenschutz, siehe SCAN_MAX_TIEFE.
            if _tiefe + 1 >= SCAN_MAX_TIEFE:
                _scan_schleife_melden("zu tief verschachtelt", full)
                continue
            if os.path.islink(full):
                try:
                    _kind_real = os.path.realpath(full)
                except OSError:
                    continue
            else:
                # Kein Link - dann ist der echte Pfad der des Vaters plus
                # Name, ohne einen einzigen Systemaufruf.
                _kind_real = os.path.join(_real, entry)
            if _kind_real in _vorfahren:
                _scan_schleife_melden("Symlink-Schleife", full)
                continue
            sub = _scan_folder_tree(full, syskey, rbf, extmap,
                                    _tiefe + 1,
                                    _vorfahren + (_kind_real,),
                                    _kind_real)
            nur = _einzelspiel(sub) if _einzeln else None
            if nur is not None:
                raw_items.append(nur)
            elif sub["folders"] or sub["items"]:
                node["folders"][entry] = sub
        else:
            name, ext = os.path.splitext(entry)
            ext = ext.lower()
            # NEU (Build 121): ein Archiv ist fuer uns ein Ordner. Kein
            # System fuehrt ".zip" als ROM-Endung, ein Archiv war damit
            # bisher schlicht unsichtbar. _zip_baum() liest nur das
            # Inhaltsverzeichnis - entpackt wird nie etwas.
            if ext == ".zip" and ext not in extmap:
                sub = _zip_baum(full, syskey, rbf, extmap, _filter_an)
                nur = _einzelspiel(sub) if _einzeln else None
                if nur is not None:
                    raw_items.append(nur)
                elif sub["folders"] or sub["items"]:
                    node["folders"][entry] = sub
                continue
            if name.lower() in IGNORE_ROM_BASENAMES:
                continue
            # NEU (Nutzerwunsch: "dass jeder wirklich das angezeigt
            # bekommt, was er auch in seinen ROM-Ordnern sieht"):
            # diese beiden Filter liefen bisher IMMER. Jetzt nur noch,
            # wenn sie ausdruecklich eingeschaltet sind - siehe
            # rom_filter_enabled() in fe/settings.py fuer die
            # Begruendung. Standard ist AUS.
            if _filter_an:
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
