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
import os, glob, time
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
    if "[Menu]" in ini:
        # Block entfernen: von der [Menu]-Zeile bis zur naechsten
        # Sektion oder zum Dateiende
        i = ini.index("[Menu]")
        j = ini.find("\n[", i + 1)
        ini = ini[:i].rstrip() + "\n" + (ini[j + 1:] if j != -1 else "")
        active = False
    else:
        ini = ini.rstrip() + "\n" + CRT_MENU_BLOCK
        active = True
    # Atomar schreiben: erst in eine Temp-Datei, dann umbenennen. Sonst
    # kann ein Abbruch mitten im Schreiben die MiSTer.ini leeren/zerstoeren.
    tmp = MISTER_INI + ".tmp"
    try:
        with open(tmp, "w") as f:
            f.write(ini)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, MISTER_INI)
    except OSError:
        try:
            os.remove(tmp)
        except OSError:
            pass
        return None
    return active


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
