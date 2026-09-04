#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verstreute kleine Ein/Aus-Einstellungen: eigenes Boot-Logo, Setup-
Assistent-Erledigt-Markierung, CRT-Menue-Modus (MiSTer.ini), kuratierte
Filterung (nur Spiele mit Metadaten anzeigen), Attract-Modus
(Verzoegerung/Ein-Aus). Ausgelagert aus frontend.py (Modularisierung,
Git-Branch 'modular-refactor') - mehrere ehemals ueber die Datei
verstreute kleine Bloecke hier sinnvoll zusammengefuehrt.
"""
import os, glob, time, re
from fe.log import LOG
from fe.art import get_meta, mra_meta

DRAGEND_LOGO_FILE = "/media/fat/frontend/boot_logo/dragend_logo.art"
DRAGEND_LOGO_DISABLED_FLAG = "/media/fat/frontend/dragend_logo_disabled"

def dragend_logo_enabled():
    return not os.path.exists(DRAGEND_LOGO_DISABLED_FLAG)

def toggle_dragend_logo():
    if dragend_logo_enabled():
        try:
            os.makedirs(os.path.dirname(DRAGEND_LOGO_DISABLED_FLAG), exist_ok=True)
            open(DRAGEND_LOGO_DISABLED_FLAG, "w").close()
        except OSError:
            pass
    else:
        try:
            os.remove(DRAGEND_LOGO_DISABLED_FLAG)
        except OSError:
            pass

# NEUES FEATURE (Nutzerwunsch: "bitte den bg-Ordner komplett rausnehmen,
# glaube der laggt ein wenig" - System-Hintergrundbilder hinter der
# Spieleliste UND als Cover-Rueckfall fuer Spiele ohne eigenes Artwork,
# siehe BG_BASE/BgCache in fe/art.py). Fehlende Dateien werden bereits
# sicher/guenstig behandelt (ART.get() cached "nicht gefunden" dauerhaft
# nach dem ersten Fehlschlag) - dieser Schalter betrifft den Fall, dass
# die Dateien VORHANDEN sind, aber trotzdem uebersprungen werden sollen.
# Bewusst ALS SCHALTER statt den Code fest zu entfernen - andere Nutzer
# (Sutefan/Dennsen/Community) moechten das visuelle Feature evtl.
# behalten. Standard AN (bestehendes Verhalten bleibt fuer alle
# unveraendert, die den Schalter nicht anfassen) - nach demselben
# "Standard an, per Datei abschaltbar"-Muster wie beim Boot-Logo oben.
SYSTEM_BG_DISABLED_FLAG = "/media/fat/frontend/system_bg_disabled"

def system_bg_enabled():
    return not os.path.exists(SYSTEM_BG_DISABLED_FLAG)

def toggle_system_bg():
    if system_bg_enabled():
        try:
            os.makedirs(os.path.dirname(SYSTEM_BG_DISABLED_FLAG), exist_ok=True)
            open(SYSTEM_BG_DISABLED_FLAG, "w").close()
        except OSError:
            pass
    else:
        try:
            os.remove(SYSTEM_BG_DISABLED_FLAG)
        except OSError:
            pass

# NEUES FEATURE (Nutzerwunsch: "wenn wir den Schimmer-Effekt rausnehmen
# wuerde das noch was bringen?" - Puls-/Schimmer-Animation auf der
# markierten Zeile/Kachel, siehe _pulse_tick()/_pulsed() in
# frontend.py). Haengt am selben leichten Tick-Mechanismus, der gerade
# erst per DRAGEND_PROFILE messbar gemacht wurde (siehe "PERF tick" in
# next_action()) - laeuft bis zu 12.5x/Sekunde UNABHAENGIG vom
# Scrollen, sobald man einfach nur auf einem Eintrag steht. Bewusst
# ALS SCHALTER statt fest zu entfernen (rein optische Praeferenz,
# manche moegen die Animation) - Standard AN (bestehendes Verhalten
# bleibt unveraendert), gleiches Muster wie oben.
PULSE_EFFECT_DISABLED_FLAG = "/media/fat/frontend/pulse_effect_disabled"

def pulse_effect_enabled():
    return not os.path.exists(PULSE_EFFECT_DISABLED_FLAG)

def toggle_pulse_effect():
    if pulse_effect_enabled():
        try:
            os.makedirs(os.path.dirname(PULSE_EFFECT_DISABLED_FLAG), exist_ok=True)
            open(PULSE_EFFECT_DISABLED_FLAG, "w").close()
        except OSError:
            pass
    else:
        try:
            os.remove(PULSE_EFFECT_DISABLED_FLAG)
        except OSError:
            pass

# NEUES FEATURE (Nutzerwunsch: "ich haette gerne denn Equalizer im HDMI-
# Modus abschaltbar, um zu sehen ob es dadurch besser wird mit dem
# Scrollen im Menue"): gleiches Ein/Aus-Muster wie beim Schimmer-Effekt
# oben. Wichtig fuer die Erwartungshaltung: die eigentliche HDMI-Scroll-
# Traegheit wurde bereits an anderer Stelle behoben (siehe
# _scroll_skip_vsync() in frontend.py - urspruenglich GENAU wegen des
# Verdachts "liegt es am Equalizer/der Laufschrift?" eingefuehrt, aber
# als Vsync-Wartezeit bei den Tick-Pfaden identifiziert, nicht als
# Equalizer-Zeichenkosten selbst). Dieser Schalter existiert trotzdem,
# damit der Nutzer es auf seiner eigenen Hardware selbst gegenpruefen
# kann - schadet im deaktivierten Zustand nichts (die Balken werden dann
# schlicht nie gezeichnet, kein eigener Tick faellig).
EQ_EFFECT_DISABLED_FLAG = "/media/fat/frontend/eq_effect_disabled"

def eq_effect_enabled():
    return not os.path.exists(EQ_EFFECT_DISABLED_FLAG)

def toggle_eq_effect():
    if eq_effect_enabled():
        try:
            os.makedirs(os.path.dirname(EQ_EFFECT_DISABLED_FLAG), exist_ok=True)
            open(EQ_EFFECT_DISABLED_FLAG, "w").close()
        except OSError:
            pass
    else:
        try:
            os.remove(EQ_EFFECT_DISABLED_FLAG)
        except OSError:
            pass

# NEUES FEATURE (Nutzerwunsch: "Musik-Laufschrift haette ich auch gerne
# noch ein und ausschaltbar"): gleiches Ein/Aus-Muster wie beim
# Equalizer direkt oberhalb - betrifft NUR die scrollende Songtitel-
# Anzeige (frontend.py: track_marquee_text()/_track_marquee_tick()),
# NICHT die Laufschrift fuer zu lange Spieletitel in der Liste
# (marquee_needed()/marquee_tick() - komplett getrenntes, eigenes
# System, siehe dortige Kommentare). Deaktiviert zeigt der Songtitel
# weiterhin (nur) seinen Anfang statt zu scrollen, statt ganz zu
# verschwinden - naeher an "Laufschrift aus" als an "Songtitel
# ausblenden".
TRACK_MARQUEE_DISABLED_FLAG = "/media/fat/frontend/track_marquee_disabled"

def track_marquee_enabled():
    return not os.path.exists(TRACK_MARQUEE_DISABLED_FLAG)

def toggle_track_marquee():
    if track_marquee_enabled():
        try:
            os.makedirs(os.path.dirname(TRACK_MARQUEE_DISABLED_FLAG), exist_ok=True)
            open(TRACK_MARQUEE_DISABLED_FLAG, "w").close()
        except OSError:
            pass
    else:
        try:
            os.remove(TRACK_MARQUEE_DISABLED_FLAG)
        except OSError:
            pass

# NEUES FEATURE (Nutzerwunsch: "kann man das mit Stream Overlay in den
# Optionen mit einem an/aus schaltbar machen?"): bisher nur ueber das
# externe Scripts/Frontend_Stream_Toggle.sh umschaltbar (legt/entfernt dieselbe
# Datei) - Kern-Mechanismus unveraendert (siehe frontend.py __init__:
# der StreamServer wird nur gestartet, wenn diese Datei beim Start
# existiert), NUR der Zugriffsweg ist jetzt zusaetzlich direkt im
# Menue moeglich, ohne SSH/externes Skript. GLEICHE Einschraenkung wie
# beim externen Skript (dort auch so dokumentiert): wirkt erst nach
# einem Neustart des Frontends, da der StreamServer (Port-Bindung,
# Hintergrund-Thread) nur einmal beim Start aufgebaut wird - ein
# Live-Start/Stop waere ein groesserer, riskanterer Eingriff fuer
# denselben Nutzen.
STREAM_ENABLED_FLAG = "/media/fat/frontend/stream_enabled"

def stream_overlay_enabled():
    return os.path.exists(STREAM_ENABLED_FLAG)

def toggle_stream_overlay():
    if stream_overlay_enabled():
        try:
            os.remove(STREAM_ENABLED_FLAG)
        except OSError:
            pass
    else:
        try:
            os.makedirs(os.path.dirname(STREAM_ENABLED_FLAG), exist_ok=True)
            open(STREAM_ENABLED_FLAG, "w").close()
        except OSError:
            pass

# NEUES FEATURE (Nutzerwunsch: "waere es machbar diese Funktion unter
# der Kategorie System an/aus schaltbar zu machen?" - zum Bildschirm-
# spiegel-Feature, siehe publish_screen() in stream_server.py): setzt
# technisch auf dem Stream-Overlay-Server auf, deshalb NUR wirksam,
# wenn Stream-Overlay (oben) ebenfalls aktiv ist - eigener Schalter,
# da nicht jeder, der das Overlay fuer OBS nutzt, auch den Bildschirm
# spiegeln moechte (staendiges Kodieren kostet etwas CPU, siehe
# Drosselung in frontend.py).
SCREEN_MIRROR_ENABLED_FLAG = "/media/fat/frontend/screen_mirror_enabled"

def screen_mirror_enabled():
    return os.path.exists(SCREEN_MIRROR_ENABLED_FLAG)

def toggle_screen_mirror():
    if screen_mirror_enabled():
        try:
            os.remove(SCREEN_MIRROR_ENABLED_FLAG)
        except OSError:
            pass
    else:
        try:
            os.makedirs(os.path.dirname(SCREEN_MIRROR_ENABLED_FLAG), exist_ok=True)
            open(SCREEN_MIRROR_ENABLED_FLAG, "w").close()
        except OSError:
            pass

# NEUES FEATURE (Nutzerwunsch: vereinfachte Installation, ein
# Ersteinrichtungs-Assistent, der einmalig durch alle wichtigen
# Schritte fuehrt): anders als BOOTANIM_PLAYED_MARKER (liegt in /tmp,
# wird bei JEDEM Neustart neu abgespielt) liegt diese Markierung
# bewusst auf der SD-Karte (/media/fat/...) - der Assistent soll nur
# EINMAL im Leben automatisch erscheinen, nicht bei jedem Boot.
SETUP_WIZARD_DONE_FILE = "/media/fat/frontend/setup_wizard_done"

def setup_wizard_done():
    return os.path.exists(SETUP_WIZARD_DONE_FILE)

def mark_setup_wizard_done():
    try:
        os.makedirs(os.path.dirname(SETUP_WIZARD_DONE_FILE), exist_ok=True)
        open(SETUP_WIZARD_DONE_FILE, "w").close()
    except OSError:
        pass

MISTER_INI = "/media/fat/MiSTer.ini"
CRT_MENU_BLOCK = """
[Menu]
vga_scaler=1
fb_terminal=1
video_mode=320,8,32,24,240,4,3,16,6048
"""

# NEUES FEATURE (Nutzerwunsch nach einem Fehlerbild bei einem Bekannten,
# bei dem das HDMI-Bild nach dem Frontend-Start wackelte: "falls das die
# Ursache ist, sollten wir da Vorkehrungen treffen, das heisst bei
# uninstall mit raus ... nicht dass es noch mehrere betrifft"):
#
# Das Frontend setzt selbst KEINEN Videomodus - es liest die Geometrie aus
# /sys/class/graphics/fb0/ und schreibt Pixel. Die EINZIGEN beiden Stellen,
# an denen es das Bild des MiSTers ueberhaupt beeinflussen kann, sind
# dieser [Menu]-Block und fb_size in der [MiSTer]-Sektion. Genau deshalb
# muessen beide bei einer Deinstallation zuverlaessig wieder verschwinden -
# sonst bleibt eine Video-Einstellung zurueck, die niemand mehr dem
# Frontend zuordnet.
#
# Die Schwierigkeit dabei: ein [Menu]-Block kann auch VOM NUTZER SELBST
# stammen (der Block ist eine ganz normale MiSTer-Funktion). Den einfach
# mitzuloeschen waere schlimmer als das Problem. Deshalb zwei Merkmale,
# und nur wenn eines zutrifft, gilt der Block als "vom Frontend erzeugt":
#
#   1. die Markierungsdatei unten - wird beim Einschalten angelegt und
#      beim Ausschalten wieder entfernt;
#   2. der Blockinhalt entspricht Zeile fuer Zeile CRT_MENU_BLOCK.
#
# Merkmal 2 ist der Rueckfall fuer alle, die den CRT-Modus mit einer
# aelteren Fassung eingeschaltet haben, als es die Markierung noch nicht
# gab - ohne ihn waere die Aufraeumfunktion genau bei den bestehenden
# Installationen wirkungslos, um die es hier eigentlich geht.
CRT_MENU_OWNED_FLAG = "/media/fat/frontend/crt_menu_by_frontend"


def _mister_ini_schreiben(text):
    """MiSTer.ini sicher ersetzen. Rueckgabe True/False.

    Gleiches Vorgehen wie beim Autostart-Eintrag (_startup_schreiben):
    einmalige Sicherungskopie, Schreiben in eine Temp-Datei im SELBEN
    Verzeichnis (sonst waere os.replace kein atomarer Rename), Rueck-Lesen
    zur Kontrolle und erst dann das atomare Umbenennen. Eine halb
    geschriebene MiSTer.ini kann einen MiSTer unbedienbar machen - hier ist
    Vorsicht billiger als eine Fehlersuche am Fernseher.
    """
    sicherung = MISTER_INI + ".dragend_backup"
    if not os.path.exists(sicherung):
        try:
            with open(MISTER_INI) as f:
                alt = f.read()
            with open(sicherung, "w") as f:
                f.write(alt)
        except OSError:
            pass          # kein Grund abzubrechen - nur eine Bequemlichkeit
    tmp = MISTER_INI + ".tmp"
    try:
        with open(tmp, "w") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        with open(tmp) as f:
            if f.read() != text:
                raise OSError("Rueck-Lesen der Temp-Datei stimmt nicht ueberein")
        os.replace(tmp, MISTER_INI)
    except OSError as e:
        LOG("MiSTer.ini konnte nicht geschrieben werden: %s" % e)
        try:
            os.remove(tmp)
        except OSError:
            pass
        return False
    return True


def _crt_menu_block_text(ini):
    """Den [Menu]-Block aus dem ini-Text ausschneiden (ohne Rest).
    Rueckgabe: (start, ende, text) oder None, wenn kein Block da ist."""
    i = ini.find("[Menu]")
    if i == -1:
        return None
    j = ini.find("\n[", i + 1)
    ende = len(ini) if j == -1 else j + 1
    return i, ende, ini[i:ende]


def _block_zeilen(text):
    """Vergleichsform eines ini-Blocks: leere Zeilen und Randzeichen weg,
    damit ein zusaetzlicher Zeilenumbruch keinen Unterschied macht."""
    return [z.strip() for z in text.strip().splitlines() if z.strip()]


def crt_menu_block_is_ours(ini=None):
    """True, wenn der vorhandene [Menu]-Block inhaltlich genau der ist,
    den dieses Frontend schreibt (siehe Merkmal 2 oben)."""
    if ini is None:
        try:
            ini = open(MISTER_INI).read()
        except OSError:
            return False
    teil = _crt_menu_block_text(ini)
    if teil is None:
        return False
    return _block_zeilen(teil[2]) == _block_zeilen(CRT_MENU_BLOCK)


def crt_menu_by_frontend():
    """True, wenn der [Menu]-Block der MiSTer.ini dem Frontend zuzurechnen
    ist - nur dann darf eine Deinstallation ihn entfernen."""
    if not crt_menu_active():
        return False
    if os.path.exists(CRT_MENU_OWNED_FLAG):
        return True
    return crt_menu_block_is_ours()


def _mark_crt_menu_owned(an):
    try:
        if an:
            os.makedirs(os.path.dirname(CRT_MENU_OWNED_FLAG), exist_ok=True)
            open(CRT_MENU_OWNED_FLAG, "w").close()
        else:
            os.remove(CRT_MENU_OWNED_FLAG)
    except OSError:
        pass


def crt_menu_active():
    try:
        return "[Menu]" in open(MISTER_INI).read()
    except OSError:
        return False

def toggle_crt_menu():
    """[Menu]-Block in der MiSTer.ini setzen/entfernen.
    Rueckgabe: True wenn danach CRT-Modus aktiv ist."""
    try:
        ini = open(MISTER_INI).read()
    except OSError:
        return None
    teil = _crt_menu_block_text(ini)
    if teil is not None:
        # Block entfernen: von der [Menu]-Zeile bis zur naechsten
        # Sektion oder zum Dateiende
        i, ende, _text = teil
        ini = ini[:i].rstrip() + "\n" + ini[ende:]
        active = False
    else:
        ini = ini.rstrip() + "\n" + CRT_MENU_BLOCK
        active = True
    if not _mister_ini_schreiben(ini):
        return None
    _mark_crt_menu_owned(active)
    # Eine verkleinerte Framebuffer-Groesse in BEIDE Richtungen zuruecknehmen:
    #
    # Richtung CRT: der CRT-Framebuffer ist ohnehin nur 320x240, halbiert
    # (160x120) waere er unlesbar - und der Menuepunkt dafuer ist im
    # CRT-Modus bewusst ausgeblendet (siehe fe/menu.py), der Nutzer koennte
    # ihn dort also gar nicht selbst zuruecksetzen.
    #
    # Richtung HDMI (NEU): genau weil der Menuepunkt im CRT-Modus
    # ausgeblendet ist, kann ein dort vorgefundener Wert gar keine bewusste
    # Entscheidung sein - er ist ein Rest aus einer aelteren Fassung oder
    # von Hand eingetragen. Ihn beim Rueckweg auf HDMI stehenzulassen hiesse,
    # jemanden mit einem halb aufgeloesten Bild sitzen zu lassen, ohne dass
    # er weiss, woher es kommt. Umgekehrt geht dabei nichts verloren: eine
    # bewusst auf HDMI getroffene Wahl kann hier nicht betroffen sein, weil
    # dieser Zweig nur aus dem CRT-Modus heraus erreicht wird.
    try:
        if fb_size_value():
            set_fb_size(0)
    except Exception:
        pass
    return active


def remove_crt_menu_block(force=False):
    """Den [Menu]-Block bei einer Deinstallation entfernen.

    Rueckgabe: True  = entfernt
               False = nichts zu tun / fremder Block bewusst stehengelassen
               None  = Datei nicht les-/schreibbar
    """
    try:
        ini = open(MISTER_INI).read()
    except OSError:
        return None
    teil = _crt_menu_block_text(ini)
    if teil is None:
        return False
    if not force and not crt_menu_by_frontend():
        # Fremder [Menu]-Block: NICHT anfassen. Lieber ein Rest, den der
        # Nutzer selbst gesetzt hat, als eine geloeschte Einstellung, die
        # er nie wieder findet.
        return False
    i, ende, _text = teil
    neu = ini[:i].rstrip() + "\n" + ini[ende:]
    if not _mister_ini_schreiben(neu):
        return None
    _mark_crt_menu_owned(False)
    return True


def mister_ini_video_zustand():
    """Kurzfassung dessen, was das Frontend beim Start in der MiSTer.ini
    an Video-Einstellungen VORFINDET - fuer eine Zeile im Log.

    Hintergrund: bei einem Fehlerbild ("das Bild wackelt, seit das
    Frontend laeuft") gab es bisher nichts, woran man haette ablesen
    koennen, ob ueberhaupt eine dieser beiden Einstellungen gesetzt war.
    Das kostet jedes Mal eine Rueckfrage-Runde. Diese Zeile beantwortet
    sie im Voraus.
    """
    try:
        ini = open(MISTER_INI).read()
    except OSError:
        return "MiSTer.ini nicht lesbar"
    teil = _crt_menu_block_text(ini)
    if teil is None:
        menu = "[Menu] nicht vorhanden"
    elif crt_menu_by_frontend():
        menu = "[Menu] vorhanden (vom Frontend gesetzt)"
    else:
        eigene = " | ".join(_block_zeilen(teil[2])[1:]) or "leer"
        menu = "[Menu] vorhanden (NICHT vom Frontend - eigener Block: %s)" % eigene
    return "%s, fb_size=%d" % (menu, fb_size_value())


# NEUES FEATURE (Nutzerwunsch: "sowas darf nicht passieren, wenn jemand im
# CRT-Modus landet, der kein CRT hat - wie soll er da wieder rauskommen?"):
# eine ECHTE Sperre ("CRT nur waehlbar, wenn wirklich eins angeschlossen
# ist") laesst sich auf einem MiSTer software-seitig NICHT zuverlaessig
# bauen - anders als HDMI (EDID/Hotplug-Erkennung) meldet ein per VGA/SCART
# angeschlossener CRT dem System normalerweise gar nichts zurueck, es gibt
# also kein generisches Signal "CRT ist da". Und selbst wenn: das Zeichnen
# selbst laeuft immer weiter, ob am anderen Ende tatsaechlich ein Bild
# ankommt, weiss die Software nie.
#
# Deshalb hier das praktische Gegenstueck: ein Sicherheitsnetz NACH dem
# Umschalten statt einer Sperre VORHER. Wird kurz vor einem Neustart in den
# CRT-Modus diese Markierung gesetzt, ueberwacht next_action() nach dem
# naechsten Boot automatisch, ob innerhalb von CRT_CONFIRM_TIMEOUT Sekunden
# UEBERHAUPT eine Eingabe ankommt (siehe next_action()-Kommentar dort). Bleibt
# es (z.B. mangels Bild) komplett still, wechselt das System GANZ VON ALLEIN
# zurueck auf HDMI und startet neu - der Nutzer muss dafuer nichts sehen
# oder druecken koennen. Jede echte Eingabe beweist dagegen, dass das Bild
# ankommt UND bedienbar ist, und bestaetigt CRT dauerhaft.
CRT_PENDING_CONFIRM_FILE = "/media/fat/frontend/crt_menu_pending_confirm"
CRT_CONFIRM_TIMEOUT = 20   # s ohne jede Eingabe nach einem Wechsel IN den
                          # CRT-Modus, bevor automatisch auf HDMI zurueck-
                          # gewechselt wird - grosszuegig genug fuer jemanden,
                          # der tatsaechlich vor einem CRT sitzt und kurz
                          # liest, kurz genug, um nicht ewig auf einem
                          # dunklen Fernseher zu warten.

def crt_pending_confirm():
    return os.path.exists(CRT_PENDING_CONFIRM_FILE)

def mark_crt_pending_confirm():
    try:
        os.makedirs(os.path.dirname(CRT_PENDING_CONFIRM_FILE), exist_ok=True)
        open(CRT_PENDING_CONFIRM_FILE, "w").close()
    except OSError:
        pass

def clear_crt_pending_confirm():
    try:
        os.remove(CRT_PENDING_CONFIRM_FILE)
    except OSError:
        pass


# ----------------------------------------------------------------------------

def _node_has_any_meta(node, syskey):
    """Rekursiv prüfen, ob IRGENDWO im Baum ein Eintrag Metadaten hat -
    entscheidet, ob das Sicherheitsnetz (kein Filtern bei komplett
    fehlender Datenbank) greift."""
    for it in node["items"]:
        label, kind, arg = it
        meta = mra_meta(arg) if (syskey == "ARCADE" and kind == "core") \
              else ({} if syskey == "ARCADE" else get_meta(syskey, label))
        if meta:
            return True
    for sub in node["folders"].values():
        if _node_has_any_meta(sub, syskey):
            return True
    return False

def _filter_node_curated(node, syskey):
    """Rekursiv jeden Knoten auf katalogisierte Eintraege einschraenken.
    Ordner, die dadurch komplett leer werden (keine Items, keine
    nicht-leeren Unterordner), fallen ganz weg."""
    kept_items = []
    for it in node["items"]:
        label, kind, arg = it
        meta = mra_meta(arg) if (syskey == "ARCADE" and kind == "core") \
              else ({} if syskey == "ARCADE" else get_meta(syskey, label))
        if meta:
            kept_items.append(it)
    kept_folders = {}
    for fname, sub in node["folders"].items():
        filtered_sub = _filter_node_curated(sub, syskey)
        if filtered_sub["folders"] or filtered_sub["items"]:
            kept_folders[fname] = filtered_sub
    return {"folders": kept_folders, "items": kept_items}

def filter_curated(name, node, syskey):
    """Wenn der 'Nur katalogisierte Spiele'-Schalter aktiv ist (System-
    Menue), auf Eintraege einschraenken, die einen Treffer in der
    libretro-Datenbank haben (von mister_gameinfo.py geladen,
    meta/<System>.json bzw. fuer Arcade die MRA-Datei selbst) - das ist
    die "Source of Authority", die Hyperspin frueher mit seinen
    XML-Datenbanken pro System bereitgestellt hat: nur tatsaechlich
    katalogisierte, offiziell erschienene Spiele, keine Hacks/Homebrew/
    unbekannten Dumps. Arbeitet rekursiv ueber die komplette
    Ordnerstruktur - leer gewordene Unterordner fallen weg.

    Sicherheitsnetz: Hat ein System UEBERHAUPT keine Metadaten (z.B.
    weil mister_gameinfo.py dafuer noch nie gelaufen ist), wird NICHT
    gefiltert - sonst wuerde die Liste faelschlich komplett leer
    werden, nur weil noch keine Datenbank geladen wurde."""
    if not syskey or not (node["folders"] or node["items"]):
        return (name, node, syskey)
    if not _node_has_any_meta(node, syskey):
        return (name, node, syskey)
    return (name, _filter_node_curated(node, syskey), syskey)

CURATED_FLAG = "/media/fat/frontend/curated_only"
ATTRACT_DISABLED_FLAG = "/media/fat/frontend/attract_disabled"
ATTRACT_DELAY_FILE = "/media/fat/frontend/attract_delay"
# NEUES FEATURE (Nutzerwunsch: "fuer denn attract Modus eventuell aus
# nur an und aus zu machen noch eine Einstellung dabei damit man sich
# selber aussuchen kann ab wieviel Minuten der anfaengt"): bisher war
# die Verzoegerung mit ATTRACT_IDLE_SECONDS = 90 fest verdrahtet, nur
# AN/AUS liess sich einstellen (siehe attract_enabled()). Jetzt
# zusaetzlich einstellbar - gleiches Muster wie die bestehende
# Zeitzonen-Einstellung (load/save/cycle-Dreiklang mit einer festen
# Schrittliste).
ATTRACT_DELAY_STEPS = [30, 60, 90, 120, 180, 300, 600, 900]   # Sekunden

def load_attract_delay():
    try:
        with open(ATTRACT_DELAY_FILE) as f:
            val = int(f.read().strip())
            return val if val in ATTRACT_DELAY_STEPS else 90
    except (OSError, ValueError):
        return 90   # bisheriger fester Standardwert bleibt der Default

def save_attract_delay(seconds):
    try:
        os.makedirs(os.path.dirname(ATTRACT_DELAY_FILE), exist_ok=True)
        with open(ATTRACT_DELAY_FILE, "w") as f:
            f.write(str(seconds))
    except OSError:
        pass

def cycle_attract_delay():
    """Naechsten Wert in ATTRACT_DELAY_STEPS waehlen (wrap-around).
    Liefert den neuen Wert in Sekunden."""
    current = load_attract_delay()
    try:
        idx = ATTRACT_DELAY_STEPS.index(current)
    except ValueError:
        idx = -1
    new_val = ATTRACT_DELAY_STEPS[(idx + 1) % len(ATTRACT_DELAY_STEPS)]
    save_attract_delay(new_val)
    return new_val

def format_attract_delay(seconds):
    """z.B. '30s', '2min', '10min' - fuer die Menu-Beschriftung."""
    if seconds < 60:
        return "%ds" % seconds
    if seconds % 60 == 0:
        return "%dmin" % (seconds // 60)
    return "%.1fmin" % (seconds / 60)

ATTRACT_IDLE_SECONDS = 90   # so lange ohne Eingabe, bevor der Attract-
                            # Modus (Bildschirmschoner) automatisch startet
                            # - BLEIBT als Standardwert/Sicherheitsnetz
                            # bestehen (siehe load_attract_delay()), wird
                            # aber nicht mehr direkt fuer den eigentlichen
                            # Check verwendet (siehe next_action()).
ATTRACT_CHANGE_SECONDS = 6  # wie lange ein Spiel im Attract-Modus gezeigt wird
COVER_SETTLE = 0.15         # s nach letzter Eingabe, bis waehrend des
                            # Scrollens uebersprungene Cover nachgeladen
                            # werden (haelt das Scrollen selbst fluessig)

# NEUES FEATURE (Nutzerwunsch: "kann man das Vsync-Warten beim Scrollen
# weglassen, um schneller zu werden? Will ich probieren" - AUSDRUECKLICH
# vom Nutzer angefragter Kompromiss, nicht unilateral entschieden): siehe
# ausfuehrliche Begruendung/Risiko-Erklaerung bei flip()/flip_rows() in
# fe/framebuffer.py. Standard AUS (bewusster Opt-in) - Bildriss-Risiko
# soll niemand ungefragt bekommen, der einfach nur aktualisiert.
FAST_SCROLL_ENABLED_FLAG = "/media/fat/frontend/fast_scroll_enabled"
FAST_SCROLL_WINDOW = 0.15   # s nach letzter Eingabe, in der Vsync beim
                            # Scrollen uebersprungen wird (danach: normal
                            # synchronisiert, kein Tearing im Ruhezustand) -
                            # bewusst derselbe Wert wie COVER_SETTLE, beide
                            # beschreiben dasselbe "gerade aktiv am
                            # Scrollen"-Zeitfenster.

def fast_scroll_enabled():
    return os.path.exists(FAST_SCROLL_ENABLED_FLAG)

def toggle_fast_scroll():
    if fast_scroll_enabled():
        try:
            os.remove(FAST_SCROLL_ENABLED_FLAG)
        except OSError:
            pass
    else:
        try:
            os.makedirs(os.path.dirname(FAST_SCROLL_ENABLED_FLAG), exist_ok=True)
            open(FAST_SCROLL_ENABLED_FLAG, "w").close()
        except OSError:
            pass


# NEUES FEATURE (Nutzerwunsch: "eventuell unter System und dann unter
# Optionen dafuer einen Schalter einbauen, der beim Neustart das an- und
# ausschaltet"): Groesse des Linux-Framebuffers ueber die MiSTer.ini
# steuern.
#
# HINTERGRUND (gemessen, nicht geschaetzt): der gesamte Aufwand eines
# Bildaufbaus - Hintergrund fuellen, Zeilen zeichnen, Text setzen,
# Hintergrund wiederherstellen UND die fertige Seite in den Framebuffer
# kopieren - haengt direkt an der Pixelzahl. Derselbe Seitenaufbau kostet
# im Profiling auf 1920x1080 rund das Sechsfache von 320x240. MiSTer kann
# den Linux-Framebuffer kleiner betreiben und per Hardware wieder auf die
# Ausgabeaufloesung hochskalieren - bei halber Groesse sind das ein
# Viertel der Pixel, bei einem Viertel sogar ein Sechzehntel, ohne dass am
# Frontend selbst irgendetwas geaendert werden muss (die Geometrie wird
# beim Start aus /sys/class/graphics/fb0 gelesen, das Layout skaliert
# automatisch mit).
#
# Der Preis ist ehrlich zu nennen: das Bild wird sichtbar weicher bzw.
# kloetziger, weil die Hardware wieder hochrechnet. Deshalb bewusst als
# Menuepunkt zum Ausprobieren statt als stille Voreinstellung - Standard
# bleibt die volle Groesse.
#
# Die Einstellung ist ein GLOBALER Schluessel der MiSTer.ini (also vor der
# ersten [Sektion]) - bewusst NICHT im [Menu]-Block, den der CRT-Schalter
# oben komplett anlegt und wieder entfernt; sonst wuerde ein
# CRT-Umschalten diese Einstellung stillschweigend mit loeschen.
FB_SIZE_STEPS = [0, 2, 4]   # 0 = volle Groesse (MiSTer-Standard/automatisch),
                            # 2 = halbe Aufloesung, 4 = ein Viertel
                            # (Werte laut MiSTer.ini: "0 - automatic,
                            # 1 - full size, 2 - 1/2 of resolution,
                            # 4 - 1/4 of resolution")

_FB_SIZE_RE = re.compile(r"^[ \t]*fb_size[ \t]*=[ \t]*([0-9]+)",
                         re.MULTILINE)

# In WELCHE Sektion der Schluessel gehoert.
#
# BUGFIX (Nutzer-Rueckmeldung: "ich merke da keinen Unterschied, egal was
# ich auswaehle und dann Neustart mache"): die erste Fassung schrieb
# fb_size VOR die erste [Sektion], in der Annahme, es gaebe in der
# MiSTer.ini so etwas wie einen "globalen Teil". Den gibt es NICHT - im
# ini-Parser des MiSTers (cfg.cpp, ini_parse()) startet die Variable
# 'section' auf 0, und Zeilen werden nur ausgewertet, solange eine
# Sektion aktiv ist ("else if (section) ini_parse_var(line);"). Alles vor
# der ersten Sektionszeile wird also STILLSCHWEIGEND VERWORFEN - die
# Einstellung kam nie beim MiSTer an, deshalb sah jede Stufe gleich aus.
#
# Die allgemeine Sektion heisst [MiSTer] und passt laut ini_get_section()
# immer (fester Namensvergleich, unabhaengig vom geladenen Core). Genau
# dorthin gehoert der Schluessel. Bewusst NICHT nach [Menu]: den Block
# legt der CRT-Schalter komplett an und entfernt ihn wieder, die
# Einstellung waere beim naechsten CRT-Umschalten stillschweigend weg.
FB_SIZE_SECTION = "MiSTer"


def _ini_split_section(ini, name):
    """Teilt den ini-Text in (davor, Inhalt der Sektion, danach).

    Der mittlere Teil ist der Inhalt der genannten Sektion OHNE deren
    Kopfzeile - also alles zwischen "[name]" und der naechsten
    Sektionszeile bzw. dem Dateiende. Fehlt die Sektion, ist der mittlere
    Teil None (der Aufrufer legt sie dann an).
    """
    m = re.search(r"^[ \t]*\[[ \t]*" + re.escape(name) + r"[ \t]*\][ \t]*\r?\n",
                  ini, re.MULTILINE | re.IGNORECASE)
    if m is None:
        return ini, None, ""
    start = m.end()
    m2 = re.search(r"^[ \t]*\[", ini[start:], re.MULTILINE)
    end = start + m2.start() if m2 else len(ini)
    return ini[:start], ini[start:end], ini[end:]


def fb_size_value():
    """Aktueller fb_size-Wert aus der [MiSTer]-Sektion der MiSTer.ini
    (0 wenn nicht gesetzt oder nicht lesbar - das entspricht dem
    MiSTer-Standard)."""
    try:
        ini = open(MISTER_INI).read()
    except OSError:
        return 0
    _vor, mitte, _nach = _ini_split_section(ini, FB_SIZE_SECTION)
    if mitte is None:
        return 0
    m = _FB_SIZE_RE.search(mitte)
    if not m:
        return 0
    try:
        val = int(m.group(1))
    except ValueError:
        return 0
    return val if val in FB_SIZE_STEPS else 0


def set_fb_size(value):
    """fb_size in der [MiSTer]-Sektion der MiSTer.ini setzen. value=0
    entfernt die Zeile wieder (zurueck zum MiSTer-Standard). Rueckgabe:
    der neue Wert, oder None wenn die Datei nicht geschrieben werden
    konnte."""
    try:
        ini = open(MISTER_INI).read()
    except OSError:
        return None
    vor, mitte, nach = _ini_split_section(ini, FB_SIZE_SECTION)
    if mitte is None:
        # Sektion fehlt - ohne sie wuerde der Schluessel wieder ins Leere
        # laufen (siehe Kommentar bei FB_SIZE_SECTION). Nur anlegen, wenn
        # ueberhaupt etwas gesetzt werden soll.
        if not value:
            return 0
        vor = ini.rstrip("\n")
        vor = (vor + "\n\n") if vor else ""
        vor += "[" + FB_SIZE_SECTION + "]\n"
        mitte, nach = "", ""
    # Bestehende Zeile(n) in der Sektion zuerst entfernen - so entsteht
    # auch bei mehrfach vorhandenem Schluessel ein eindeutiger Zustand.
    mitte = re.sub(r"^[ \t]*fb_size[ \t]*=[^\n]*\n?", "", mitte,
                   flags=re.MULTILINE)
    if value:
        if mitte and not mitte.endswith("\n"):
            mitte += "\n"
        mitte += "fb_size=%d\n" % value
    new_ini = vor + mitte + nach
    # Sicher schreiben (Sicherung, Temp-Datei, Rueck-Lesen, atomarer
    # Rename - siehe _mister_ini_schreiben): ein Abbruch mitten im
    # Schreiben darf die MiSTer.ini nicht zerstoeren.
    if not _mister_ini_schreiben(new_ini):
        return None
    return value


def cycle_fb_size():
    """Naechsten Wert aus FB_SIZE_STEPS waehlen (wrap-around).
    Rueckgabe: der neue Wert, oder None bei Schreibfehler."""
    current = fb_size_value()
    try:
        idx = FB_SIZE_STEPS.index(current)
    except ValueError:
        idx = -1
    return set_fb_size(FB_SIZE_STEPS[(idx + 1) % len(FB_SIZE_STEPS)])


def fb_size_label_key(value=None):
    """Uebersetzungs-Schluessel fuer die Menuezeile zum aktuellen Wert."""
    if value is None:
        value = fb_size_value()
    return {2: "sys_fb_size_half", 4: "sys_fb_size_quarter"}.get(
        value, "sys_fb_size_full")


# ENTFERNT (Build 77, Nutzerwunsch: "F4 kann raus komplett, auch der
# Schalter unter System, weil die Funktion ja nicht geht").
#
# Hier stand der F4-Schnellstart: ein eigener Hintergrund-Waechter
# (frontend/f4_hotkey.py), der beim Booten die Eingabegeraete mitlas
# und das Frontend startete, sobald im MiSTer-OSD F4 gedrueckt wurde -
# gedacht fuer alle, die keinen Autostart eingerichtet haben.
#
# In der Sandbox und in der Tastenerkennung auf dem Geraet lief er
# nachweislich ("Taste gedrueckt: Code 62" im Log des Nutzers), im
# Alltag hat er beim Nutzer trotzdem nie zuverlaessig getan, was er
# sollte. Statt weiter daran zu suchen, faellt er ersatzlos weg: der
# Autostart-Schalter (siehe unten) erfuellt denselben Zweck ohne
# zusaetzlichen Dauerprozess, der bei jedem Boot alle Eingabegeraete
# mitliest.
#
# Die Installer und Frontend_Update.sh raeumen die Startzeile aus
# /media/fat/linux/user-startup.sh sowie die zurueckgebliebenen
# Dateien bei bestehenden Installationen aktiv weg - sonst startete
# dort bei jedem Boot ein Waechter, den es nicht mehr gibt.


# NEUES FEATURE (Nutzerfrage: "ist da jetzt quasi ein Schalter unter
# System/Optionen drin, der den Autostart an- und ausschaltbar macht?" -
# war bis dahin NEIN: der Autostart wurde einmalig beim Installieren
# eingerichtet und liess sich danach nur per SSH wieder loswerden).
#
# WARUM NICHT die vorhandene "disable"-Datei
# ---------------------------------------------------------------
# /media/fat/frontend/disable gibt es laengst - die prueft aber AUCH
# Frontend_Start.sh. Damit waere alles aus, auch der manuelle Start -
# das genaue Gegenteil des Wunsches ("Autostart aus, aber von Hand
# starten koennen").
#
# WAS HIER PASSIERT - und warum das die heikelste Stelle im Projekt ist
# ---------------------------------------------------------------
# Auf ausdruecklichen Wunsch wird die Zeile WIRKLICH aus
# /media/fat/linux/user-startup.sh entfernt (statt sie nur ueber eine
# Schalterdatei wirkungslos zu machen). Diese Datei gehoert dem MiSTer,
# und ein kaputter Inhalt legt den naechsten Boot lahm. Deshalb wird
# hier deutlich mehr Aufwand getrieben als bei jedem anderen Schalter:
#
#   1. Vor der ERSTEN Aenderung wird eine Sicherheitskopie angelegt
#      (user-startup.sh.dragend_backup) - einmalig, sie wird nie
#      ueberschrieben, damit sie den Originalzustand bewahrt.
#   2. Geschrieben wird NIE in die Zieldatei selbst, sondern in eine
#      Nebendatei im GLEICHEN Verzeichnis, die anschliessend per
#      os.replace() darueber geschoben wird. Das ist auf demselben
#      Dateisystem ein atomarer Vorgang: entweder die alte oder die
#      neue Fassung ist da, niemals eine halb geschriebene.
#   3. Vor dem Umbenennen wird der neue Inhalt zurueckgelesen und
#      geprueft (Shebang vorhanden, gewuenschte Aenderung tatsaechlich
#      drin). Faellt die Pruefung durch, wird die Nebendatei verworfen
#      und die Zieldatei bleibt unangetastet.
#   4. Alle anderen Zeilen bleiben zeichengenau erhalten - alles, was
#      der Nutzer sonst dort stehen hat, wird nicht angefasst.
USER_STARTUP_FILE = "/media/fat/linux/user-startup.sh"
AUTOSTART_MARKER = "frontend_boot.sh"
AUTOSTART_LINE = "/media/fat/frontend/frontend_boot.sh &"
_AUTOSTART_BACKUP = USER_STARTUP_FILE + ".dragend_backup"


def _startup_zeilen():
    """Inhalt von user-startup.sh als Zeilenliste, oder None wenn die
    Datei nicht lesbar ist."""
    try:
        with open(USER_STARTUP_FILE, "r", encoding="utf-8",
                  errors="surrogateescape") as f:
            return f.read().splitlines()
    except OSError:
        return None


def autostart_enabled():
    """True, wenn das Frontend beim Booten mitgestartet wird.

    Bewusst am tatsaechlichen Dateiinhalt abgelesen statt an einer
    eigenen Merkdatei: der Eintrag kann auch vom Installer, per SSH oder
    von Hand gesetzt/entfernt worden sein. Eine Merkdatei wuerde in dem
    Fall etwas anderes behaupten als der MiSTer tatsaechlich tut."""
    zeilen = _startup_zeilen()
    if not zeilen:
        return False
    for z in zeilen:
        s = z.strip()
        if s and not s.startswith("#") and AUTOSTART_MARKER in s:
            return True
    return False


def _startup_schreiben(neue_zeilen, pruefung):
    """Schreibt user-startup.sh sicher neu. Liefert True bei Erfolg.

    pruefung(text) muss True liefern, damit die neue Fassung ueberhaupt
    an ihren Platz geschoben wird - siehe Punkt 3 im Kopfkommentar."""
    verzeichnis = os.path.dirname(USER_STARTUP_FILE)
    text = "\n".join(neue_zeilen).rstrip("\n") + "\n"
    try:
        os.makedirs(verzeichnis, exist_ok=True)
        # Einmalige Sicherheitskopie des Originals
        if os.path.exists(USER_STARTUP_FILE) \
                and not os.path.exists(_AUTOSTART_BACKUP):
            with open(USER_STARTUP_FILE, "rb") as q, \
                    open(_AUTOSTART_BACKUP, "wb") as z:
                z.write(q.read())
            LOG("autostart: Sicherheitskopie angelegt: %s" % _AUTOSTART_BACKUP)
        tmp = USER_STARTUP_FILE + ".dragend_tmp"
        with open(tmp, "w", encoding="utf-8", errors="surrogateescape") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        # Zurueckgelesen pruefen, BEVOR die Datei an ihren Platz kommt
        with open(tmp, "r", encoding="utf-8", errors="surrogateescape") as f:
            zurueck = f.read()
        if not pruefung(zurueck):
            os.remove(tmp)
            LOG("autostart: Pruefung der neuen Fassung fehlgeschlagen - "
                "user-startup.sh bleibt unveraendert.")
            return False
        os.chmod(tmp, 0o755)
        os.replace(tmp, USER_STARTUP_FILE)     # atomar
        return True
    except OSError as e:
        LOG("autostart: Schreiben fehlgeschlagen: %s" % e)
        try:
            os.remove(USER_STARTUP_FILE + ".dragend_tmp")
        except OSError:
            pass
        return False


def set_autostart(an):
    """Autostart ein- oder ausschalten. Liefert True bei Erfolg.

    Wirkt ab dem naechsten Neustart - beim Booten liest MiSTer die Datei
    einmal, ein laufendes Frontend ist davon nicht betroffen."""
    zeilen = _startup_zeilen()
    if zeilen is None:
        if not an:
            # Keine Datei -> es gibt auch keinen Eintrag zu entfernen.
            return True
        zeilen = ["#!/bin/bash"]
    if an:
        if autostart_enabled():
            return True
        neu = list(zeilen)
        if not neu or not neu[0].startswith("#!"):
            neu.insert(0, "#!/bin/bash")
        neu.append(AUTOSTART_LINE)
        return _startup_schreiben(
            neu, lambda t: t.startswith("#!") and AUTOSTART_MARKER in t)
    # Ausschalten: NUR die Zeilen mit dem Marker fallen weg, alles
    # andere bleibt zeichengenau stehen.
    behalten = [z for z in zeilen if AUTOSTART_MARKER not in z]
    if len(behalten) == len(zeilen):
        return True                            # war schon aus
    if not behalten or not behalten[0].startswith("#!"):
        behalten.insert(0, "#!/bin/bash")
    return _startup_schreiben(
        behalten, lambda t: t.startswith("#!") and AUTOSTART_MARKER not in t)


def toggle_autostart():
    """Schaltet um. Liefert (erfolgreich, neuer_zustand)."""
    ziel = not autostart_enabled()
    ok = set_autostart(ziel)
    return ok, autostart_enabled()


# NEUES FEATURE (Nutzerwunsch: "vielleicht sollten wir das komplett
# rausnehmen, dass jeder wirklich das angezeigt bekommt, was er auch in
# seinen ROM-Ordnern sieht").
#
# Vorgeschichte: beim Einlesen liefen ZWEI Filter, immer, ohne Schalter
# und ohne Hinweis - _is_junk() (beta/proto/demo/sample/[b]/program/
# test/kiosk) und _is_japan_only(). Sie laufen VOR der kuratierten
# Liste, weshalb deren Abschalten nichts half: die Datei war da schon
# verworfen. Aufgefallen ist das an "Tetris (Japan) (En).gb", das
# nirgends auftauchte - weder mit noch ohne kuratierte Liste.
#
# Das eigentliche Problem war nicht die Filterregel, sondern dass sie
# unsichtbar war. Ein Nutzer sieht eine Datei im Ordner und im Frontend
# nicht, und nichts sagt ihm warum. Deshalb jetzt ein Schalter -
# und zwar STANDARDMAESSIG AUS, also standardmaessig wird nichts mehr
# weggefiltert. Das ist eine bewusste Verhaltensaenderung fuer alle:
# "zeig mir, was in meinen Ordnern liegt" ist die Erwartung, die
# niemanden ueberrascht. Wer die Aufraeumfunktion moechte, schaltet sie
# ein.
#
# Die Datei bedeutet also "Filter AN", nicht "abgeschaltet" - was
# standardmaessig aus ist, wird durch eine Datei eingeschaltet, nicht
# umgekehrt.
ROM_FILTER_FLAG = "/media/fat/frontend/rom_filter"


def rom_filter_enabled():
    """True, wenn Beta/Proto/Demo- und Nur-Japan-Titel beim Einlesen
    ausgefiltert werden sollen. Standard: False (nichts filtern)."""
    return os.path.exists(ROM_FILTER_FLAG)


def toggle_rom_filter():
    """Schaltet um. Liefert den NEUEN Zustand.

    WICHTIG: der Aufrufer MUSS danach die Spieleliste neu einlesen
    lassen - die Filter wirken beim Einlesen, nicht beim Anzeigen. Der
    Cache-Fingerabdruck enthaelt den Schalterzustand (siehe
    _games_signature() in fe/scan.py), ein Neustart wuerde also ohnehin
    neu einlesen; der Menuepunkt stoesst es sofort an."""
    if rom_filter_enabled():
        try:
            os.remove(ROM_FILTER_FLAG)
        except OSError as e:
            LOG("toggle_rom_filter: Loeschen fehlgeschlagen: %s" % e)
            return True
        return False
    try:
        d = os.path.dirname(ROM_FILTER_FLAG)
        if d:
            os.makedirs(d, exist_ok=True)
        open(ROM_FILTER_FLAG, "w").close()
    except OSError as e:
        LOG("toggle_rom_filter: Anlegen fehlgeschlagen: %s" % e)
        return False
    return True


def attract_enabled():
    """Standardmaessig AN (im Gegensatz zu curated_only_active(), das
    standardmaessig AUS ist) - die Datei bedeutet hier 'abgeschaltet',
    nicht 'aktiviert'."""
    return not os.path.exists(ATTRACT_DISABLED_FLAG)

def toggle_attract_mode():
    existed_before = os.path.exists(ATTRACT_DISABLED_FLAG)
    if existed_before:
        try:
            os.remove(ATTRACT_DISABLED_FLAG)
        except OSError as e:
            LOG("toggle_attract_mode: Loeschen der Markierungsdatei "
                "fehlgeschlagen: %s" % e)
    else:
        try:
            dirname = os.path.dirname(ATTRACT_DISABLED_FLAG)
            if dirname:
                os.makedirs(dirname, exist_ok=True)
            open(ATTRACT_DISABLED_FLAG, "w").close()
        except OSError as e:
            LOG("toggle_attract_mode: Anlegen der Markierungsdatei "
                "fehlgeschlagen: %s" % e)
    LOG("toggle_attract_mode: vorher %s -> jetzt %s (Datei existiert: %s)"
        % ("AUS" if existed_before else "AN",
           "AN" if existed_before else "AUS",
           os.path.exists(ATTRACT_DISABLED_FLAG)))

def curated_only_active():
    return os.path.exists(CURATED_FLAG)

def toggle_curated_only():
    if os.path.exists(CURATED_FLAG):
        try:
            os.remove(CURATED_FLAG)
        except OSError:
            pass
    else:
        try:
            dirname = os.path.dirname(CURATED_FLAG)
            if dirname:
                os.makedirs(dirname, exist_ok=True)
            open(CURATED_FLAG, "w").close()
        except OSError:
            pass
