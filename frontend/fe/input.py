#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Eingabe: Tastatur + Gamepads parallel, mit Hotplug und exklusivem Grab.
Ausgelagert aus frontend.py (Modularisierung, Git-Branch
'modular-refactor').

KEYMAP ist ein normales, veraenderliches Dictionary - wird an mehreren
Stellen (hier UND weiterhin in frontend.py selbst, fuer das Remap-
Feature im System-Menue) per .update()/.clear()/Item-Zuweisung
mutiert, NIE komplett neu zugewiesen. Ein einfaches
"from fe.input import KEYMAP" ist hier deshalb GEFAHRLOS (anders als
z.B. CURRENT_LANG in fe/translations.py) - alle Seiten teilen sich
dasselbe Dict-Objekt im Speicher, eine Mutation von der einen Seite
ist sofort auch von der anderen sichtbar.
"""
import os, sys, struct, fcntl, time, select, threading, json, re, glob
from collections import defaultdict
from fe.log import LOG
from fe.launch import current_core
from fe.hidraw import (_find_keyboard_hidraws, _hid_report_has_exit_key,
                        _hid_report_has_reset_key)
from fe.reset_trigger import send_reset_combo

KEYMAP_CUSTOM_FILE = "/media/fat/frontend/keymap_custom.json"

EVIOCGRAB = 0x40044590
EV_SYN, EV_KEY, EV_ABS = 0, 1, 3
KEY_ESC, KEY_ENTER = 1, 28
KEY_BACKSPACE = 14
KEY_SLASH = 53
# BUGFIX (Nutzer-Rueckmeldung: "F2 Volltextsuche erkennt keine
# Leertaste? Wenn ich super mario suchen will schreibt der
# supermario"): die Leertaste war bisher komplett unbelegt (kein
# Eintrag in KEYMAP) - jeder Tastendruck ohne bekannte Zuordnung wird
# von read_action() stillschweigend verworfen (kein Fehler, einfach
# keine Aktion), das Leerzeichen landete dadurch nie in
# self._search_query. Bindet die Leertaste an dieselbe "letter:X"-
# Aktion wie die normalen Buchstabentasten weiter unten (LETTER_KEYS),
# nur mit X=" " (ein Leerzeichen) - im Suchmodus haengt
# jump_to_substring() das genau wie jeden anderen Buchstaben einfach an
# self._search_query an (siehe run()). Ausserhalb des Suchmodus loest
# dieselbe Aktion den klassischen Anfangsbuchstaben-Sprung
# (jump_to_letter()) aus - dort schadet ein Leerzeichen nichts: KEIN
# Name beginnt mit einem Leerzeichen, jump_to_letter() findet also nie
# einen Treffer und laesst die Auswahl unveraendert, exakt wie bei
# jeder anderen ungenutzten Buchstabentaste.
KEY_SPACE = 57
KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT = 103, 108, 105, 106
# NEUES FEATURE (Nutzerwunsch: "waere F2 im Frontend noch frei? wuerde
# gerne die Volltextsuche mit der Taste einbauen"): F2 war bislang
# tatsaechlich komplett unbelegt (siehe Kommentar bei KEY_F5 weiter
# unten: "F1-F5 waren noch nie belegt" - F1/F3/F4 sind es bis heute
# immer noch nicht). Bindet KEIN neues Feature, sondern nur eine
# ZWEITE Taste fuer den schon vorhandenen Suchmodus (siehe KEY_SLASH
# unten) - wer eine Tastatur nutzt, muss dafuer nicht mehr "/" tippen,
# beide Tasten loesen exakt dieselbe, bereits bestehende Logik aus.
KEY_F2 = 60
KEY_F7 = 65
KEY_F6 = 64
KEY_F8, KEY_F9, KEY_F10, KEY_F11, KEY_F12 = 66, 67, 68, 87, 88
# Gamepad-Buttons (Linux-Standardcodes)
BTN_A, BTN_B, BTN_X, BTN_Y = 304, 305, 307, 308
KEY_Y = 21                   # Scancode an der QWERTY-"Y"-Position (evdev
                              # KEY_Y) - auf deutschen Tastaturen physisch
                              # mit "Z" beschriftet, siehe LETTER_KEYS
                              # weiter unten. Aktuell nirgends mehr aktiv
                              # gebunden (siehe Kommentar direkt darunter),
                              # nur noch importiert/historisch vorhanden.
# BUGFIX (Nutzer-Rueckmeldung: "die Y-Taste zum Musik skippen hat mich
# ziemlich verwirrt, ich dachte das ist nur eine Controller-Belegung" -
# bei der Untersuchung noch etwas Wichtigeres gefunden, als zunaechst
# vermutet): KEY_Y: "music_next" stand zwar in der KEYMAP, wurde aber
# von der LETTER_KEYS-Schleife weiter unten STILLSCHWEIGEND ueberschrieben
# ("Y" ist eine der Buchstabentasten fuer den Direktsprung im Menue,
# z.B. zu "Yoshi's Island") - diese Tastatur-Bindung hat vermutlich noch
# NIE funktioniert, unabhaengig vom Tastaturlayout (QWERTY oder QWERTZ
# waere gleichermassen betroffen gewesen, da beide "Y" UND "Z" als
# Buchstaben fuer den Direktsprung verwenden). Y als Musik-Taste zu
# erzwingen wuerde umgekehrt den Buchstabensprung zu "Y"-Spielen kaputt
# machen - keine der beiden Funktionen sollte der anderen geopfert werden.
# Neue, konfliktfreie Loesung: eine bislang komplett ungenutzte
# Funktionstaste (F1-F5 waren noch nie belegt) PLUS die dedizierte
# Multimedia-Taste "naechster Titel", die viele Tastaturen ohnehin
# haben (Linux-Standardcode, siehe KEY_NEXTSONG unten) - bei sowas
# druecken Nutzer intuitiv genau diese Taste, ganz ohne Anleitung.
KEY_F5 = 63
KEY_NEXTSONG = 163            # Medientaste "naechster Titel", falls vorhanden
BTN_TL, BTN_TR = 310, 311
BTN_TL2, BTN_TR2 = 312, 313  # zusaetzliche Schultertasten (L2/R2), sofern vorhanden
BTN_SELECT, BTN_START, BTN_MODE = 314, 315, 316
BTN_DPAD_UP, BTN_DPAD_DOWN, BTN_DPAD_LEFT, BTN_DPAD_RIGHT = 544, 545, 546, 547
# Achsen
ABS_X, ABS_Y, ABS_HAT0X, ABS_HAT0Y = 0, 1, 16, 17
ABS_Z, ABS_RZ = 2, 5   # analoge L2/R2-Trigger bei vielen Xbox-artigen Pads
# Interne Pseudo-Codes fuer L2/R2, WENN sie analog (als Achse) statt als
# eigene Taste ankommen - negative Zahlen, damit sie garantiert nicht mit
# einem echten evdev-Code (immer >= 0) kollidieren. Werden genau wie ein
# normaler Tastencode im KEYMAP behandelt (siehe InputManager._translate()
# und read_raw_key()) - dadurch bleiben sie ganz normal frei belegbar,
# auch wenn L2/R2 auf dem jeweiligen Pad nicht als BTN_TL2/BTN_TR2 ankommen.
AXIS_L2, AXIS_R2 = -2, -5
EVENT_FMT  = "llHHi"
EVENT_SIZE = struct.calcsize(EVENT_FMT)

# Standard-evdev-Scancodes der Buchstabentasten - fuer den Direktsprung
# per Tastatur: A druecken -> naechster Eintrag mit A. Ausserdem die
# Grundlage fuer die Buchstaben-Positionen in den Geheimcodes (siehe
# SECRET_CODES in fe/achievements.py).
#
# BUGFIX (Nutzer-Rueckmeldung: "der Code fuer den Entwicklerraum
# funktioniert nicht", dann auf Nachfrage bestaetigt: "geh davon aus,
# dass jeder eine deutsche Tastatur hat"): Linux liest Tastatureingaben
# als rohe, layoutlose Scancodes - der Kernel selbst nennt sie nur nach
# ihrer PHYSISCHEN Position auf einem US-QWERTY-Referenzboard (KEY_Y=21
# an der Position, wo QWERTY ein "Y" hat). Y und Z sind die einzigen
# beiden Buchstaben, die zwischen QWERTY und QWERTZ (deutsches Layout)
# die Position tauschen: physisch mit "Z" beschriftet sitzt auf
# Scancode 21 (der "QWERTY-Y-Position"), physisch mit "Y" beschriftet
# sitzt auf Scancode 44 (der "QWERTY-Z-Position"). Dieses Projekt ist
# durchgehend auf deutsche Nutzer ausgelegt (Sprache, Doku, Community) -
# deshalb bewusst NICHT layoutneutral geloest (z.B. durch Vermeiden von
# Y/Z in Codes), sondern die Zuordnung direkt an die tatsaechliche
# deutsche Tastatur angepasst: 21 -> "Z", 44 -> "Y" (vertauscht
# gegenueber der reinen US-QWERTY-Scancode-Bedeutung). Wer eine
# US-QWERTY-Tastatur anschliesst, bekommt dadurch umgekehrt ein
# vertauschtes Y/Z beim Buchstabensprung - fuer die weit ueberwiegende
# Nutzerbasis (DE-Tastatur) ist das der richtige Kompromiss.
LETTER_KEYS = {
    16: "Q", 17: "W", 18: "E", 19: "R", 20: "T", 21: "Z", 22: "U",
    23: "I", 24: "O", 25: "P",
    30: "A", 31: "S", 32: "D", 33: "F", 34: "G", 35: "H", 36: "J",
    37: "K", 38: "L",
    44: "Y", 45: "X", 46: "C", 47: "V", 48: "B", 49: "N", 50: "M",
}

# Tasten/Buttons -> logische Aktionen des Frontends
# Seit v1.11 bewusst schlank gehalten: Enter oeffnet/startet, ESC/B geht
# eine Ebene zurueck (bzw. fragt im Hauptmenue nach), hoch/runter
# navigiert einzeln, links/rechts springt seitenweise. Bild auf/ab und
# Pos1/Ende gibt es dafuer nicht mehr - die Schultertasten L/R sind
# jetzt einfach ein zweiter Weg fuer den Seitensprung (wie D-Pad
# links/rechts), statt eine eigene Buchstabensprung-Logik zu haben.
KEYMAP = {
    KEY_UP: "up", KEY_DOWN: "down", KEY_LEFT: "left", KEY_RIGHT: "right",
    KEY_ENTER: "ok", KEY_ESC: "exit",
    KEY_F12: "osd", KEY_F10: "back_fe", KEY_F9: None, KEY_F11: "random",
    KEY_F8: "favorite", BTN_TL2: "favorite", BTN_TR2: "favorite",
    AXIS_L2: "favorite", AXIS_R2: "favorite",
    KEY_F7: "completed",
    # NEUES FEATURE (Nutzerwunsch: Volltextsuche statt nur Anfangs-
    # buchstaben-Sprung, "bei vielen ROMs ist das besser") - "/" ist die
    # klassische Suche-Taste (vim/less-Konvention), Backspace loescht
    # das letzte eingegebene Zeichen der Suchanfrage. Siehe
    # self._search_mode/self._search_query weiter unten.
    KEY_SLASH: "search",
    # NEUES FEATURE (Nutzerwunsch: "F2 als Taste fuer die Suche"): zweite,
    # gleichwertige Taste fuer denselben Suchmodus wie "/" oben - manche
    # finden eine dedizierte Funktionstaste intuitiver als "/". Loest
    # exakt dieselbe Aktion "search" aus, keine eigene Logik noetig.
    KEY_F2: "search",
    KEY_BACKSPACE: "search_backspace",
    # BUGFIX (siehe ausfuehrlicher Kommentar bei KEY_SPACE weiter oben):
    # Leertaste fehlte bisher komplett in der KEYMAP.
    KEY_SPACE: "letter: ",
    KEY_F6: "ra_showcase",
    BTN_A: "ok", BTN_START: "ok",
    BTN_B: "back", BTN_X: "back_fe",
    BTN_Y: "music_next", KEY_F5: "music_next", KEY_NEXTSONG: "music_next",
    BTN_TL: "left", BTN_TR: "right",
    BTN_MODE: "osd", BTN_SELECT: "select",
    BTN_DPAD_UP: "up", BTN_DPAD_DOWN: "down",
    BTN_DPAD_LEFT: "left", BTN_DPAD_RIGHT: "right",
}
for _code, _ch in LETTER_KEYS.items():
    KEYMAP[_code] = "letter:" + _ch

# Schnappschuss der Standardbelegung (fuer "Auf Standard zuruecksetzen")
DEFAULT_KEYMAP = dict(KEYMAP)

def _load_custom_keymap():
    """Eigene Tastenbelegung laden und in KEYMAP einmischen (ueberschreibt
    einzelne Eintraege, der Rest bleibt Standard)."""
    try:
        data = json.load(open(KEYMAP_CUSTOM_FILE))
        for k, v in data.items():
            KEYMAP[int(k)] = v
    except (OSError, ValueError, TypeError):
        pass

_load_custom_keymap()

# NEU (Nutzerwunsch: "waere es nicht sinnvoll, sich darauf zu verlassen,
# was im MiSTer entsprechend gemapped ist? Grade sowas ist einfach ne
# bloede Conveniencefalle" - anschliessende Recherche ergab: MiSTers
# eigene Belegungsdateien unter /media/fat/config/inputs/*.map sind ein
# undokumentiertes, sich zwischen Firmware-Versionen bereits mehrfach
# geaendertes Binaerformat (Suffix "_v3" beweist mind. zwei stille
# Formatwechsel seither) - selbst die MiSTer-Community-eigenen Tools
# behandeln diese Dateien nur als komplette, undurchsichtige Kopier-
# Bloecke, nie als auswertbare Daten. Verlaesslich auslesen ist damit
# nicht seriös machbar. Praktikablere Abhilfe fuer den haeufigsten
# Einzelfall (Bestaetigen/Abbrechen ist auf dem eigenen Pad andersherum
# belegt als hier angenommen, z.B. Nintendo- vs. Xbox-Layout): ein
# einziger, expliziter Umschalter statt der kompletten Remap-Prozedur -
# vertauscht ueberall dort, wo aktuell "ok" bzw. "back" hinterlegt ist,
# beide Rollen. Wirkt UNABHAENGIG von einer eigenen Tastenbelegung
# (KEYMAP_CUSTOM_FILE, oben bereits eingemischt) und ist sein eigenes
# Gegenstueck (zweimal anwenden = wieder Ausgangszustand) - siehe
# save_swap_ok_back() fuer den Umschalt-Aufruf aus dem Menue.
SWAP_OK_BACK_FILE = "/media/fat/frontend/swap_ok_back.flag"

def swap_ok_back_enabled():
    """Liest die Einstellung "Bestaetigen/Abbrechen vertauscht" -
    Standard NEIN (reine Existenz der Datei als Schalter, kein Inhalt
    noetig)."""
    return os.path.exists(SWAP_OK_BACK_FILE)

def _swap_ok_back_in_keymap():
    """Vertauscht in KEYMAP (dem tatsaechlich aktiven Dict, siehe
    Modul-Docstring oben - eine Mutation ist ueberall sofort sichtbar)
    einmalig alle "ok"<->"back"-Eintraege. Selbstinvers: zweimaliger
    Aufruf stellt den Ausgangszustand wieder her - genau deshalb reicht
    beim Umschalten im Menue ein einzelner Aufruf in beide Richtungen."""
    for code, act in list(KEYMAP.items()):
        if act == "ok":
            KEYMAP[code] = "back"
        elif act == "back":
            KEYMAP[code] = "ok"

def save_swap_ok_back(enabled):
    """Schalter setzen/loeschen UND sofort auf die laufende KEYMAP
    anwenden (kein Neustart noetig, wirkt ab dem naechsten Tastendruck)."""
    try:
        if enabled:
            d = os.path.dirname(SWAP_OK_BACK_FILE)
            if d:
                os.makedirs(d, exist_ok=True)
            open(SWAP_OK_BACK_FILE, "w").close()
        else:
            if os.path.exists(SWAP_OK_BACK_FILE):
                os.remove(SWAP_OK_BACK_FILE)
    except OSError:
        pass
    _swap_ok_back_in_keymap()

# Beim Programmstart bereits eingeschalteter Schalter (aus einer
# frueheren Sitzung) muss einmalig angewendet werden, BEVOR irgendeine
# Eingabe verarbeitet wird - sonst wuerde er erst beim naechsten
# manuellen Umschalten im Menue wirksam.
if swap_ok_back_enabled():
    _swap_ok_back_in_keymap()

# Richtungs-Aktionen, die beim Halten wiederholt werden - sowohl
# hoch/runter (einzelne Position) als auch links/rechts (Seitensprung)
# beschleunigen beim Halten.
REPEAT_ACTIONS = {"up", "down", "left", "right"}
REPEAT_DELAY    = 0.40      # Sekunden bis zur ersten Wiederholung
REPEAT_INTERVAL = 0.14      # Start-Intervall, beschleunigt bis 0.05

# BUGFIX (Nutzer-Rueckmeldung: "wenn ich nach unten gedrueckt halte und
# dann wieder nach oben druecke um zu scrollen, bleibt der kurz haengen,
# das fuehlt sich klemmig an"). Ursache nachgerechnet: _hold() setzt bei
# JEDEM frischen Tastendruck die volle Anlaufverzoegerung von 400ms und
# wirft die bereits erreichte Beschleunigung weg - ein Richtungswechsel
# ist fuer die Eingabeschicht aber genau so ein frischer Tastendruck.
# Wer gerade mit 80ms pro Schritt gescrollt hat, landet dadurch
# schlagartig bei 400ms (Faktor 5) und ist erst nach 0.79s und 5
# Schritten wieder auf voller Geschwindigkeit.
#
# Die 400ms haben ihren Sinn - sie verhindern, dass ein EINZELNER,
# bewusster Tastendruck ungewollt in eine Wiederholung laeuft. Dieser
# Fall liegt hier aber nachweislich nicht vor: es wurde ja unmittelbar
# davor bereits wiederholt. Deshalb greift die verkuerzte Anlaufzeit
# ausschliesslich dann, wenn die letzte echte Wiederholung derselben
# Achse (hoch/runter bzw. links/rechts) weniger als
# REPEAT_CONTINUE_WINDOW zurueckliegt - ein normaler einzelner
# Tastendruck aus dem Stand behaelt die volle 400ms-Sperre unveraendert.
REPEAT_REVERSE_DELAY  = 0.14   # Anlaufzeit bei Richtungswechsel im Scrollen
REPEAT_CONTINUE_WINDOW = 0.5   # so lange gilt ein Scrollvorgang als "laufend"

# BUGFIX (Nutzer-Rueckmeldung: "wenn ich nach links oder rechts druecke um
# mehrere zu ueberspringen, fuehlt sich das auch noch etwas stockend an im
# HDMI-Modus"). Ursache gemessen: links/rechts springt eine ganze
# Bildschirmseite weit, danach zeigen ALLE sichtbaren Zeilen Titel, die
# noch nie gezeichnet wurden - die Trefferquote des Text-Caches bricht
# dabei von ~86% auf ~20% ein, und einen leichten Zeichenpfad gibt es
# fuer Seitenspruenge nicht (den gibt es nur fuer Einzelschritte
# hoch/runter). Gemessen kostet ein Seitensprung dadurch das 4-fache
# eines normalen Schritts; hochgerechnet auf die auf echter Hardware
# gemessenen 45-110ms fuer einen vollen Aufbau sind das rund 110-260ms.
#
# Bei einem gemeinsamen Wiederhol-Boden von 0.08s werden aber 12.5
# Seitenspruenge pro Sekunde ANGEFORDERT - liefern lassen sich real nur
# etwa 4-9. Das Frontend hinkt dauerhaft hinterher, und weil die Dauer je
# nach Anteil neuer Titel schwankt, kommen die Bildaktualisierungen
# unregelmaessig an: genau das fuehlt sich als Stocken an.
#
# Deshalb ein EIGENER, langsamerer Boden fuer links/rechts. Es wird nur
# noch so viel angefordert, wie sich gleichmaessig liefern laesst - ruhige,
# regelmaessige Seitenwechsel statt unregelmaessig durchkommender. Der
# erste Tastendruck reagiert unveraendert sofort; betroffen ist nur die
# WIEDERHOLRATE bei gehaltener Taste. Nebeneffekt: man kann ueberhaupt
# noch lesen, wo man gelandet ist.
PAGE_ACTIONS      = {"left", "right"}
REPEAT_FLOOR      = 0.08   # hoch/runter: eine Zeile pro Schritt
REPEAT_FLOOR_PAGE = 0.25   # links/rechts: eine ganze Seite pro Schritt
# Zuordnung Aktion -> Achse: nur ein Wechsel INNERHALB derselben Achse
# gilt als Richtungswechsel (hoch<->runter, links<->rechts).
REPEAT_AXIS = {"up": "y", "down": "y", "left": "x", "right": "x"}

def _absinfo(fd, axis):
    """min/max einer Achse per EVIOCGABS-ioctl auslesen."""
    buf = bytearray(24)
    fcntl.ioctl(fd, 0x80184540 + axis, buf)
    _val, amin, amax, _f, _fl, _res = struct.unpack("6i", buf)
    return amin, amax

class Device:
    def __init__(self, path, name, is_kbd):
        self.path = path
        self.name = name
        self.is_kbd = is_kbd
        self.fd = os.open(path, os.O_RDWR)
        self.grabbed = False
        self.axis = {}            # axis -> (min, max)
        self.axis_state = {}      # axis -> -1/0/1 (fuer Flankenerkennung)
        for ax in (ABS_X, ABS_Y, ABS_HAT0X, ABS_HAT0Y, ABS_Z, ABS_RZ):
            try:
                self.axis[ax] = _absinfo(self.fd, ax)
                self.axis_state[ax] = 0
            except OSError:
                pass

    def grab(self, on):
        try:
            fcntl.ioctl(self.fd, EVIOCGRAB, 1 if on else 0)
            self.grabbed = on
        except OSError:
            pass

    def close(self):
        try:
            self.grab(False)
            os.close(self.fd)
        except OSError:
            pass

def scan_devices():
    """Alle echten Input-Geraete finden (MiSTers virtuelles ueberspringen)."""
    devs = []
    try:
        blocks = open("/proc/bus/input/devices").read().split("\n\n")
    except OSError:
        return devs
    for b in blocks:
        if "event" not in b or "MiSTer virtual" in b:
            continue
        m = re.search(r"event(\d+)", b)
        n = re.search(r'N: Name="([^"]*)"', b)
        if not m:
            continue
        path = "/dev/input/event" + m.group(1)
        devs.append((path, n.group(1) if n else "?", "kbd" in b))
    return devs

class InputManager:
    RESCAN_EVERY = 3.0            # Sekunden - fuer Hotplug neuer Pads

    def __init__(self):
        self.devices = {}
        self.want_grab = False
        self.last_scan = 0.0
        self.held = None          # (key_id, aktion, naechste_zeit, intervall)
        # Letzte TATSAECHLICHE Wiederholung (nicht: letzter Tastendruck) -
        # Grundlage fuer die verkuerzte Anlaufzeit beim Richtungswechsel,
        # siehe REPEAT_REVERSE_DELAY und _hold(). Bewusst nur bei einer
        # echten Wiederholung gesetzt: so gilt ein Scrollvorgang nur dann
        # als "laufend", wenn wirklich gescrollt wurde - einzelne
        # Tastendruecke hintereinander loesen die Verkuerzung nicht aus.
        self._last_repeat_time = 0.0
        self._last_repeat_act = None
        self._last_repeat_iv = REPEAT_INTERVAL
        self._last_input_mtime = None
        self.rescan(force=True)

    def rescan(self, force=False):
        # Billiger Schnellcheck: aendert sich /dev/input ueberhaupt? Neue
        # oder entfernte Geraete aendern die mtime des Ordners. Solange
        # die gleich bleibt (im Menue-Alltag praktisch immer), sparen wir
        # uns das teure Parsen von /proc/bus/input/devices - nur ein
        # einziger stat()-Syscall alle RESCAN_EVERY Sekunden statt
        # unnoetiger Dauerlast auf der eher schwachen CPU. Hotplug wird
        # weiterhin zuverlaessig erkannt, nur eben nicht teurer als noetig.
        self.last_scan = time.monotonic()
        try:
            mt = os.stat("/dev/input").st_mtime
        except OSError:
            mt = 0.0
        if not force and mt == self._last_input_mtime:
            return
        self._last_input_mtime = mt
        seen = set()
        for path, name, is_kbd in scan_devices():
            seen.add(path)
            if path not in self.devices:
                try:
                    d = Device(path, name, is_kbd)
                    d.grab(self.want_grab)
                    self.devices[path] = d
                    LOG("Geraet: %s '%s' kbd=%s achsen=%s"
                        % (path, name, is_kbd, sorted(d.axis)))
                except OSError as e:
                    LOG("Geraet %s nicht nutzbar: %s" % (path, e))
        for path in list(self.devices):
            if path not in seen:
                self.devices[path].close()
                del self.devices[path]

    def grab(self, on):
        LOG("grab(%s)" % on)
        self.want_grab = on
        for d in self.devices.values():
            d.grab(on)

    @staticmethod
    def _repeat_floor(act):
        """Kleinstmoegliches Wiederhol-Intervall fuer eine Aktion - fuer
        links/rechts bewusst groesser, siehe REPEAT_FLOOR_PAGE."""
        return REPEAT_FLOOR_PAGE if act in PAGE_ACTIONS else REPEAT_FLOOR

    def _hold(self, key_id, act):
        if act not in REPEAT_ACTIONS:
            return
        now = time.monotonic()
        floor = self._repeat_floor(act)
        # Das Start-Intervall darf den Boden nicht unterschreiten - bei
        # links/rechts liegt REPEAT_INTERVAL (0.14s) bereits darunter,
        # dort wird also von Anfang an mit dem groesseren Boden gearbeitet.
        delay, iv = REPEAT_DELAY, max(REPEAT_INTERVAL, floor)
        # Richtungswechsel mitten in einem laufenden Scrollvorgang -
        # siehe ausfuehrliche Begruendung bei REPEAT_REVERSE_DELAY oben.
        # Statt der vollen Anlaufsperre nur eine kurze Pause, und das
        # bereits erreichte Tempo wird beibehalten, statt den kompletten
        # Beschleunigungs-Anlauf von vorne zu beginnen.
        if (self._last_repeat_act is not None
                and REPEAT_AXIS.get(act) is not None
                and REPEAT_AXIS.get(act) == REPEAT_AXIS.get(self._last_repeat_act)
                and now - self._last_repeat_time < REPEAT_CONTINUE_WINDOW):
            # Auch die verkuerzte Anlaufzeit darf den Boden nicht
            # unterschreiten - sonst wuerde ein Links/Rechts-Wechsel
            # sofort wieder mehr anfordern als lieferbar ist.
            delay = max(REPEAT_REVERSE_DELAY, floor)
            iv = max(self._last_repeat_iv, floor)
        self.held = (key_id, act, now + delay, iv)

    def _release(self, key_id):
        if self.held and self.held[0] == key_id:
            self.held = None

    def _cancel_repeat(self):
        """Eine laufende Tasten-Wiederholung abbrechen, sobald eine NICHT
        wiederholbare Aktion kommt (Zurueck, OK, Menue, ...).

        BUGFIX (Nutzer-Rueckmeldung: "wenn ich in einem Ordner laenger
        gescrollt habe und dann einen Ordner zurueckgehe, bewegt sich der
        Cursor teilweise nicht und dann kommt auf einmal eine ploetzliche
        Bewegung"). Ursache: _translate() fasste self.held im Zweig fuer
        nicht wiederholbare Aktionen ueberhaupt nicht an - weder setzend
        noch loeschend. Wer beim Druecken von "Zurueck" die Richtungstaste
        noch gedrueckt hielt, dessen Wiederholung lief im uebergeordneten
        Ordner einfach weiter, ohne dass er etwas Neues gedrueckt hat.
        Der zugehoerige Loslass-Event kommt zwar spaeter und raeumt
        korrekt auf - bis dahin ist der Cursor aber schon von selbst
        weitergewandert. Ein bewusster Tastendruck auf etwas anderes
        beendet den Scrollvorgang jetzt sofort.

        Setzt auch die Merker fuer die verkuerzte Anlaufzeit zurueck
        (siehe _hold()) - nach einem Ordnerwechsel soll die naechste
        Richtungstaste wieder ganz normal mit voller Sperre anlaufen."""
        self.held = None
        self._last_repeat_act = None
        self._last_repeat_iv = REPEAT_INTERVAL

    def _translate(self, dev, etype, code, value):
        if etype == EV_KEY:
            if code in (BTN_DPAD_UP, BTN_DPAD_DOWN,
                        BTN_DPAD_LEFT, BTN_DPAD_RIGHT):
                key_id = (dev.path, "k", code)
                if value == 1:
                    act = KEYMAP.get(code)
                    self._hold(key_id, act)
                    return act
                if value == 0:
                    self._release(key_id)
                return None
            act = KEYMAP.get(code)
            key_id = (dev.path, "key", code)
            if act in REPEAT_ACTIONS:
                # Wiederholbare Aktionen (Navigation) laufen über unsere
                # EIGENE kontrollierte, beschleunigende Wiederholung -
                # die Auto-Wiederholung der Tastatur selbst (value==2)
                # wird ignoriert, sonst staut sich das bei ARM-Tempo
                # und laeuft nach dem Loslassen noch Sekunden nach.
                if value == 1:
                    self._hold(key_id, act)
                    return act
                if value == 0:
                    self._release(key_id)
                return None
            if value == 1:
                if act:
                    self._cancel_repeat()
                return act
            return None
        if etype == EV_ABS and code in (ABS_Z, ABS_RZ) and code in dev.axis:
            # Analoger L2/R2-Trigger: Schwellwert-Erkennung (>50% =
            # "gedrueckt"), danach ganz normal ueber KEYMAP behandelt -
            # wie ein echter Tastencode frei belegbar (Pseudo-Code
            # AXIS_L2/AXIS_R2), inklusive derselben Wiederholungslogik
            # wie bei echten Tasten, falls die zugewiesene Aktion
            # wiederholbar ist (z.B. bei Belegung auf Navigation).
            amin, amax = dev.axis[code]
            span = max(1, amax - amin)
            rel = (value - amin) / span
            pressed = 1 if rel > 0.5 else 0
            if pressed == dev.axis_state.get(code, 0):
                return None
            dev.axis_state[code] = pressed
            pseudo_code = AXIS_L2 if code == ABS_Z else AXIS_R2
            key_id = (dev.path, "a2", code)
            act = KEYMAP.get(pseudo_code)
            if not pressed:
                self._release(key_id)
                return None
            if act in REPEAT_ACTIONS:
                self._hold(key_id, act)
                return act
            if act:
                self._cancel_repeat()   # siehe dort - gleiche Begruendung
            return act
        if etype == EV_ABS and code in dev.axis:
            amin, amax = dev.axis[code]
            if code in (ABS_HAT0X, ABS_HAT0Y):
                direction = -1 if value < 0 else (1 if value > 0 else 0)
            else:
                span = max(1, amax - amin)
                rel = (value - amin) / span
                direction = -1 if rel < 0.30 else (1 if rel > 0.70 else 0)
            if direction == dev.axis_state.get(code, 0):
                return None
            dev.axis_state[code] = direction
            key_id = (dev.path, "a", code)
            if direction == 0:
                self._release(key_id)
                return None
            if code in (ABS_HAT0X, ABS_X):
                act = "left" if direction < 0 else "right"
            else:
                act = "up" if direction < 0 else "down"
            self._hold(key_id, act)
            return act
        return None

    def read_action(self, timeout=None):
        """Blockierend (oder mit Timeout) auf die naechste logische
        Aktion warten. Geraete-Events haben IMMER Vorrang vor Halte-
        Wiederholungen, damit ein Loslassen nie verloren geht.

        BUGFIX (Nutzer-Rueckmeldung von echter Hardware: Bildschirm
        bleibt nach dem Start schwarz, ueberlebte sogar den v3.1-Fix,
        der flip()/VSync als Ursache ausschloss - also musste das
        eigentliche Haengenbleiben anderswo stecken): die Deadline-
        Pruefung stand bisher NUR am ENDE der Schleife. Schlaegt
        select.select() mit OSError fehl (z.B. ein kaputtes/abgezogenes
        Eingabegeraet), sprang der Code per "continue" DIREKT zurueck
        an den Schleifenanfang - UNTER UMGEHUNG der Deadline-Pruefung
        am Ende. Wiederholt sich der Fehler (z.B. weil rescan() dasselbe
        problematische Geraet immer wieder findet, ohne das
        zugrundeliegende Problem zu loesen), entsteht eine Endlosschleife,
        die die Zeitueberschreitung NIE prueft - unabhaengig vom
        uebergebenen timeout-Wert. Das erklaert vermutlich, warum der
        erste Fix (VSync in der Boot-Animation umgehen) allein nicht
        reichte: das eigentliche Haengenbleiben steckte in DIESER
        Funktion, nicht im Bildschirmaufbau selbst - read_action(timeout=
        ...) wird durch die neue Boot-Animation zum ALLERERSTEN MAL so
        frueh im Programmablauf aufgerufen, zu einem Zeitpunkt, an dem
        Eingabegeraete moeglicherweise noch nicht vollstaendig bereit
        sind.

        Fix: Deadline-Pruefung zusaetzlich an den ANFANG jeder
        Schleifenrunde verschoben - dadurch kann KEIN Pfad durch die
        Schleife (auch nicht nach einem continue) die Pruefung mehr
        umgehen. Selbst eine dauerhaft fehlschlagende select()-Abfrage
        kann die Funktion jetzt nicht mehr laenger als die angeforderte
        Zeit blockieren."""
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            now = time.monotonic()
            if deadline is not None and now >= deadline:
                return None
            if now - self.last_scan > self.RESCAN_EVERY:
                self.rescan()
            due = self.held is not None and now >= self.held[2]
            wait = 0.0 if due else self.RESCAN_EVERY
            if not due:
                if deadline is not None:
                    wait = min(wait, max(0.0, deadline - now))
                if self.held is not None:
                    wait = min(wait, max(0.0, self.held[2] - now))
            fds = {d.fd: d for d in self.devices.values()}
            if not fds:
                time.sleep(0.5)
            else:
                try:
                    r, _, _ = select.select(list(fds), [], [], wait)
                except OSError:
                    self.rescan()
                    continue
                got_event = False
                for fd in r:
                    dev = fds[fd]
                    try:
                        data = os.read(fd, EVENT_SIZE)
                    except OSError:          # Geraet abgezogen
                        self.rescan()
                        continue
                    if len(data) < EVENT_SIZE:
                        continue
                    got_event = True
                    _, _, etype, code, value = struct.unpack(EVENT_FMT, data)
                    act = self._translate(dev, etype, code, value)
                    if act:
                        return act
                if got_event:
                    continue      # erst die Warteschlange leeren, dann Repeat
            if self.held is not None and time.monotonic() >= self.held[2]:
                kid, act, _t, iv = self.held
                # Untergrenze bewusst bei 0.08s (12.5/s) statt zuvor 0.05s
                # (20/s) - auf HDMI dauert ein volles Neuzeichnen auf
                # schwacher ARM-Hardware laenger als 0.05s, wodurch sich
                # Eingaben stauen konnten (spuerbarer "Lag" beim Halten
                # einer Richtungstaste). CRT ist so schnell, dass es den
                # Unterschied nicht merkt - 12.5 Spruenge/Sekunde sind
                # immer noch sehr flott fuer eine kleine Liste.
                # Untergrenze jetzt aktionsabhaengig (siehe
                # _repeat_floor()): hoch/runter behaelt die bisherigen
                # 0.08s, links/rechts bekommt den groesseren Boden, da
                # dort jeder Schritt eine ganze Seite neu aufbaut.
                iv = max(self._repeat_floor(act), iv * 0.85)
                self.held = (kid, act, time.monotonic() + iv, iv)
                # Nur HIER (bei einer echten Wiederholung) vermerken,
                # nicht bei jedem Tastendruck - siehe _hold()/
                # REPEAT_REVERSE_DELAY: nur ein nachweislich laufender
                # Scrollvorgang darf die verkuerzte Anlaufzeit ausloesen.
                self._last_repeat_time = time.monotonic()
                self._last_repeat_act = act
                self._last_repeat_iv = iv
                return act
            if deadline is not None and time.monotonic() >= deadline:
                return None

    def read_raw_key(self, timeout=None, allow_axis_skip=False):
        """Blockierend auf den naechsten PHYSISCHEN Tastendruck warten
        und dessen rohen evdev-Code liefern - ignoriert KEYMAP. Fuer den
        Tastenbelegungs-Assistenten: so kann auch eine bisher unbelegte
        oder anders belegte Taste erfasst werden.

        allow_axis_skip=True: ein klarer Analogstick-/D-Pad-Ausschlag
        (egal in welche Richtung) wird als "diese Aktion funktioniert
        schon nativ ueber die Achse" gewertet und liefert die spezielle
        Rueckgabe "AXIS" statt eines Codes - der Aufrufer soll dann
        einfach zur naechsten Abfrage weitergehen, ohne etwas zu
        ueberschreiben. Ohne diese Erkennung wuerde der Assistent bei
        Pads, deren D-Pad als Achse (nicht als Taste) ankommt, bei der
        allerersten Abfrage endlos haengen bleiben."""
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            now = time.monotonic()
            if now - self.last_scan > self.RESCAN_EVERY:
                self.rescan()
            wait = self.RESCAN_EVERY
            if deadline is not None:
                wait = min(wait, max(0.0, deadline - now))
            fds = {d.fd: d for d in self.devices.values()}
            if not fds:
                time.sleep(0.3)
            else:
                try:
                    r, _, _ = select.select(list(fds), [], [], wait)
                except OSError:
                    self.rescan()
                    continue
                for fd in r:
                    dev = fds.get(fd)
                    if not dev:
                        continue
                    try:
                        data = os.read(fd, EVENT_SIZE)
                    except OSError:
                        self.rescan()
                        continue
                    if len(data) < EVENT_SIZE:
                        continue
                    _, _, etype, code, value = struct.unpack(EVENT_FMT, data)
                    if etype == EV_KEY and value == 1:
                        return code
                    if etype == EV_ABS and code in (ABS_Z, ABS_RZ) and code in dev.axis:
                        # Analoger L2/R2-Trigger - unabhaengig von
                        # allow_axis_skip erkennbar, damit sich JEDE
                        # Aktion (nicht nur Navigation) darauf legen
                        # laesst. Schwellwert wie beim eigentlichen
                        # Ablesen im Hauptbetrieb (siehe _translate()).
                        amin, amax = dev.axis[code]
                        span = max(1, amax - amin)
                        rel = (value - amin) / span
                        if rel > 0.5:
                            return AXIS_L2 if code == ABS_Z else AXIS_R2
                    if allow_axis_skip and etype == EV_ABS and code in dev.axis:
                        amin, amax = dev.axis[code]
                        if code in (ABS_HAT0X, ABS_HAT0Y):
                            direction = -1 if value < 0 else (1 if value > 0 else 0)
                        else:
                            span = max(1, amax - amin)
                            rel = (value - amin) / span
                            direction = -1 if rel < 0.30 else (1 if rel > 0.70 else 0)
                        if direction != 0:
                            return "AXIS"
            if deadline is not None and time.monotonic() >= deadline:
                return None

    COMBO_HOLD = 0.8          # Sekunden Start+Select halten

    KBD_COMBO_HOLD = 0.6      # Sekunden Esc halten (hidraw-Notausstieg) -
                              # bewusst laenger als bei Strg+Alt+Esc, da
                              # ein einzelnes Esc leichter mal kurz in
                              # einem spiel-eigenen Pause-Menue gedrueckt
                              # wird als eine Dreifach-Kombination

    RESET_HOLD = 0.0          # NUTZERWUNSCH (Build 75): "F5-Reset-Funktion
                              # haette ich gerne auf sofortigen Tastendruck,
                              # wenn das geht". 0 = ausloesen, sobald die
                              # Taste erkannt wird - siehe die Stelle in
                              # wait_game_exit(), wo das Bit gesetzt wird:
                              # bei 0 wird DORT sofort ausgeloest, nicht erst
                              # in der naechsten Schleifenrunde (die haengt
                              # an select(..., 0.2) und haette allein schon
                              # bis zu 0,2 s Verzoegerung gebracht).
                              #
                              # EHRLICH BENANNTES RISIKO: ein versehentlicher
                              # F5-Antipper waehrend des Spielens ist jetzt
                              # sofort ein Reset, also im Zweifel ein
                              # verlorener Spielstand. Die Haltezeit war
                              # genau dafuer da. Der Nutzer hat das
                              # ausdruecklich so gewuenscht; wer sie
                              # zurueckhaben will, setzt hier wieder 0.6.
                              # Ein mehrfaches Ausloesen durch blosses
                              # HALTEN ist unabhaengig davon ausgeschlossen
                              # (siehe reset_gefeuert unten) - es braucht
                              # immer erst ein Loslassen.
                              #
                              # Frueherer Wert: 0.6 Sekunden halten.
                              #
                              # Reset im laufenden
                              # Core, ueber denselben hidraw-Weg wie
                              # der Esc-Notausstieg - siehe dortiger
                              # Kommentar). Nutzerwunsch: Reset per
                              # Tastatur fuer ALLE Cores, nicht nur
                              # RA-Cores, OHNE den Core selbst neu zu
                              # laden (wichtig fuer RA-Fortschritt).
                              # War urspruenglich Tab - nach einem
                              # echten Hardware-Test auf F5 umgestellt,
                              # siehe Kommentar bei
                              # _hid_report_has_reset_key() in
                              # fe/hidraw.py fuer den genauen Grund.

    def wait_game_exit(self):
        """Waehrend ein Core laeuft: warten, bis MiSTer zurueck im
        Menue ist, F10 gedrueckt wird, Start+Select lange genug
        gehalten werden, ODER Esc auf der Tastatur laenger gehalten
        wird - erkannt ueber die rohe HID-Ebene. Rueckgabe: "menu",
        "f10", "combo" oder "hid_combo".

        WICHTIG: F10/Start+Select werden ueber die normale evdev-Ebene
        gelesen, die MiSTer waehrend eines laufenden Cores exklusiv
        sperrt - vermutlich hat dieser Zweig dadurch in der Praxis nie
        tatsaechlich ausgeloest. Bleibt trotzdem als Absicherung
        bestehen. Esc laeuft stattdessen ueber /dev/hidrawX (siehe
        _find_keyboard_hidraws()).

        BUGFIX Runde 3 (per echter Nutzer-Log-Datei bestaetigt: manche
        Tastaturen legen MEHRERE hidraw-Schnittstellen unter demselben
        Namen an, z.B. eine "Boot"- und eine NKRO-Schnittstelle - die
        tatsaechlichen Tastendruecke koennen ueber eine ANDERE
        Schnittstelle laufen als die zuerst erkannte): _find_keyboard_
        hidraws() liefert jetzt eine LISTE aller Schnittstellen
        desselben Tastatur-Namens, ALLE werden hier gleichzeitig
        ueberwacht (kbd_fds statt kbd_fd) - welche davon tatsaechlich
        die Tasten sendet, muss dadurch nicht mehr erraten werden."""
        down = set()              # (geraetepfad, code) gedrueckter Tasten
        combo_since = None
        # NEU: siehe ausfuehrlicher Kommentar an der eigentlichen
        # Protokollierstelle unten - eigenes Budget PRO Geraetepfad
        # (gleiches Muster wie kbd_diag_budget), damit ein einzelner
        # "gespraechiger" Controller nicht das ganze Log flutet oder
        # das Budget fuer andere Geraete vorwegnimmt. defaultdict statt
        # vorab bekannter Pfade, da Controller waehrend des laufenden
        # Spiels erst noch erkannt werden koennen.
        combo_diag_budget = defaultdict(lambda: 40)
        last_core_check = 0.0
        kbd_paths = _find_keyboard_hidraws()
        kbd_fds = {}               # fd -> True/False (Esc gerade gehalten?)
        kbd_fd_paths = {}          # fd -> Pfad (nur fuers Diagnose-Log)
        for kp in kbd_paths:
            try:
                fd = os.open(kp, os.O_RDONLY | os.O_NONBLOCK)
                kbd_fds[fd] = False
                kbd_fd_paths[fd] = kp
            except OSError as e:
                LOG("wait_game_exit: Oeffnen fehlgeschlagen fuer %s: %s" % (kp, e))
        LOG("wait_game_exit: %d von %d Schnittstelle(n) erfolgreich geoeffnet: %s"
            % (len(kbd_fds), len(kbd_paths), list(kbd_fd_paths.values())))
        # DIAGNOSE (Nutzerwunsch: Esc wird trotz korrekt gefundener und
        # geoeffneter Schnittstellen weiterhin nicht erkannt - naechster
        # Verdacht: das Report-FORMAT selbst, nicht mehr die Schnittstellen-
        # Auswahl. Manche NKRO-faehigen Tastaturen senden Tastendruecke als
        # BITMASKE statt als Byte-Array von Tastencodes - _hid_report_
        # has_esc() sucht aber nach dem blossen Byte-WERT 0x29 irgendwo im
        # Report, was bei einer Bitmaske nie zutrifft). Protokolliert die
        # rohen Bytes der ersten 30 tatsaechlich empfangenen Reports (ueber
        # alle Schnittstellen zusammen begrenzt, nicht pro Schnittstelle -
        # sonst koennte eine sehr "gespraechige" Schnittstelle das Log
        # fluten) - zeigt beim naechsten Testlauf schwarz auf weiss, wie
        # ein Tastendruck auf DIESER Tastatur tatsaechlich aussieht.
        #
        # BUGFIX (per echter Diagnose-Ausgabe von Sutefan bestaetigt):
        # ein GEMEINSAMES Budget ueber alle Schnittstellen hinweg war
        # ein Fehler - hidraw2 sendete ALLE 30 protokollierten Reports
        # (regelmaessig wechselndes Muster, sieht nach einem periodischen
        # Status-/Heartbeat-Signal aus, NICHT nach Tastendruecken), noch
        # bevor hidraw0/hidraw1 - die vermutlich tatsaechlichen
        # Tastatur-Schnittstellen - ueberhaupt einmal zu Wort kamen.
        # Jetzt: eigenes Budget PRO Schnittstelle, damit eine
        # "gespraechige" Schnittstelle die anderen nicht mehr verdraengt.
        kbd_diag_budget = {fd: 10 for fd in kbd_fds}
        kbd_combo_since = None
        # NEU (Nutzer-Rueckmeldung: "Start+Select am Controller
        # funktioniert gar nicht, auch nach breiterer Diagnose kommt
        # WAEHREND des Spiels ueberhaupt kein Ereignis mehr an - egal
        # welche Taste"): per echtem Test bestaetigt, dass die normale
        # evdev-Ebene fuer Controller waehrend eines laufenden Cores
        # komplett taub ist (bekanntes MiSTer-Verhalten, siehe
        # _find_keyboard_hidraws() oben). Bei Tastaturen hilft der
        # tiefere hidraw-Kanal - ob das bei DIESEM Controller-Empfaenger
        # (siehe _find_keyboard_hidraws()-Log: '8BitDo 8BitDo Receiver'
        # hat eine EIGENE hidraw-Schnittstelle, wurde bisher aber nie
        # ueberwacht, da _find_keyboard_hidraws() nur nach Tastaturen
        # sucht) ebenfalls funktioniert oder ob auch dieser Kanal
        # gesperrt ist, ist noch unbekannt - genau das soll diese
        # Diagnose klaeren. ALLE hidraw-Geraete oeffnen, die NICHT
        # bereits als Tastatur erkannt/geoeffnet wurden (kbd_paths),
        # und jeden eingehenden rohen Report protokollieren (gleiches
        # Budget-pro-Geraet-Muster wie bei kbd_diag_budget oben, verhindert
        # Log-Flut durch periodische Status-/Heartbeat-Reports).
        try:
            all_hidraws = sorted(glob.glob("/dev/hidraw*"))
        except OSError:
            all_hidraws = []
        extra_hidraw_paths = [p for p in all_hidraws if p not in kbd_paths]
        extra_hidraw_fds = {}      # fd -> Pfad
        for hp in extra_hidraw_paths:
            try:
                fd = os.open(hp, os.O_RDONLY | os.O_NONBLOCK)
                extra_hidraw_fds[fd] = hp
            except OSError as e:
                LOG("wait_game_exit: Controller-hidraw-Oeffnen "
                    "fehlgeschlagen fuer %s: %s" % (hp, e))
        LOG("wait_game_exit: %d weitere(s) (Nicht-Tastatur-)hidraw-"
            "Geraet(e) zusaetzlich geoeffnet: %s"
            % (len(extra_hidraw_fds), list(extra_hidraw_fds.values())))
        extra_hidraw_budget = {fd: 15 for fd in extra_hidraw_fds}
        # NEU (Nutzerwunsch: Reset per F5 laenger halten, fuer ALLE
        # Cores inkl. RA, ohne Core-Wechsel): eigene Verfolgung analog
        # zu kbd_fds/kbd_combo_since oben, aber komplett unabhaengig -
        # F5 und Esc/F10 sollen sich gegenseitig nicht beeinflussen
        # koennen (z.B. F5+Esc gleichzeitig gehalten soll trotzdem
        # beides unabhaengig weiterzaehlen, nicht das jeweils andere
        # zuruecksetzen).
        kbd_reset_fds = {fd: False for fd in kbd_fds}
        reset_since = None
        # NEU (Build 75, sofortiges Ausloesen): merkt sich, dass fuer den
        # AKTUELLEN Tastendruck bereits ein Reset gesendet wurde. Ohne
        # das wuerde blosses Halten von F5 immer wieder ausloesen - bei
        # der frueheren Haltezeit von 0,6 s fiel das nicht auf, bei 0 s
        # waere es ein Dauerfeuer. Wird erst zurueckgesetzt, wenn die
        # Taste nachweislich losgelassen wurde.
        reset_gefeuert = False
        try:
            while True:
                now = time.monotonic()
                if now - self.last_scan > self.RESCAN_EVERY:
                    self.rescan()
                    down = {k for k in down if k[0] in self.devices}
                if now - last_core_check > 0.7:
                    last_core_check = now
                    if current_core() == "MENU":
                        return "menu"
                # WICHTIG (per Test gefunden): Reset-Pruefung bewusst VOR
                # den beiden Ausstiegs-Pruefungen - bei exakt
                # gleichzeitigem Erreichen beider Haltezeiten (seltener,
                # aber moeglicher Randfall) wuerde sonst der Ausstieg per
                # "return" die Funktion sofort verlassen, BEVOR der
                # bereits faellige Reset in derselben Schleifenrunde noch
                # ausgeloest werden konnte - der Reset ginge dadurch
                # spurlos verloren. Der Reset selbst verlaesst die
                # Funktion nicht (kein "return"), die nachfolgenden
                # Ausstiegs-Pruefungen laufen also in jedem Fall noch mit.
                if (reset_since is not None
                        and now - reset_since >= self.RESET_HOLD):
                    LOG("wait_game_exit: F5 %.1fs gehalten - loese "
                        "Reset aus (Strg+Alt+AltGr ueber uinput)"
                        % self.RESET_HOLD)
                    send_reset_combo()
                    reset_since = None
                    reset_gefeuert = True
                if combo_since is not None and now - combo_since >= self.COMBO_HOLD:
                    return "combo"
                if (kbd_combo_since is not None
                        and now - kbd_combo_since >= self.KBD_COMBO_HOLD):
                    return "hid_combo"
                fds = {d.fd: d for d in self.devices.values()}
                for kfd in kbd_fds:
                    fds[kfd] = None
                for hfd in extra_hidraw_fds:
                    fds[hfd] = None
                if not fds:
                    time.sleep(0.5)
                    continue
                try:
                    r, _, _ = select.select(list(fds), [], [], 0.2)
                except OSError:
                    self.rescan()
                    continue
                for fd in r:
                    if fd in extra_hidraw_fds:
                        try:
                            data = os.read(fd, 64)
                        except OSError:
                            try:
                                os.close(fd)
                            except OSError:
                                pass
                            extra_hidraw_fds.pop(fd, None)
                            extra_hidraw_budget.pop(fd, None)
                            continue
                        if extra_hidraw_budget.get(fd, 0) > 0:
                            extra_hidraw_budget[fd] -= 1
                            LOG("wait_game_exit DIAGNOSE Controller-hidraw "
                                "(%s): %s" % (extra_hidraw_fds.get(fd, "?"),
                                              data.hex()))
                        continue
                    if fd in kbd_fds:
                        try:
                            data = os.read(fd, 64)
                        except OSError:
                            try:
                                os.close(fd)
                            except OSError:
                                pass
                            kbd_fds.pop(fd, None)
                            kbd_reset_fds.pop(fd, None)
                            kbd_diag_budget.pop(fd, None)
                            continue
                        if kbd_diag_budget.get(fd, 0) > 0:
                            kbd_diag_budget[fd] -= 1
                            LOG("wait_game_exit DIAGNOSE (%s): %s"
                                % (kbd_fd_paths.get(fd, "?"), data.hex()))
                        kbd_fds[fd] = _hid_report_has_exit_key(data)
                        any_held = any(kbd_fds.values())
                        if any_held and kbd_combo_since is None:
                            kbd_combo_since = time.monotonic()
                        elif not any_held:
                            kbd_combo_since = None
                        kbd_reset_fds[fd] = _hid_report_has_reset_key(data)
                        any_reset_held = any(kbd_reset_fds.values())
                        # NEU (Nutzer-Rueckmeldung: Bit-Position stimmt
                        # nachweislich exakt (Byte 9 = 0x40 im Log
                        # bestaetigt), aber der Reset loest trotzdem
                        # nicht aus - Codepruefung fand keinen
                        # offensichtlichen Fehler). Zusaetzliches,
                        # gezieltes Logging genau an der Stelle, wo es
                        # bisher im Dunkeln blieb: wird reset_since
                        # ueberhaupt gesetzt, und bleibt es bis zur
                        # Ausloese-Schwelle bestehen, oder wird es
                        # vorher wieder auf None zurueckgesetzt (z.B.
                        # durch zwischenzeitliche "losgelassen"-Reports,
                        # die bei einem echten, ununterbrochenen Halten
                        # eigentlich nicht auftreten sollten)?
                        if any_reset_held and reset_since is None \
                                and not reset_gefeuert:
                            reset_since = time.monotonic()
                            LOG("wait_game_exit: reset_since GESETZT "
                                "(F5-Bit erkannt)")
                            # NEU (Build 75, Nutzerwunsch "sofortiger
                            # Tastendruck"): ohne Haltezeit HIER
                            # ausloesen, im selben Moment, in dem die
                            # Taste erkannt wird. Wuerde man auf den
                            # Schleifenanfang warten, kaeme die
                            # Wartezeit von select(..., 0.2) obendrauf -
                            # bis zu 0,2 s, die man deutlich merkt,
                            # wenn man "sofort" erwartet.
                            if self.RESET_HOLD <= 0:
                                LOG("wait_game_exit: F5 gedrueckt - loese "
                                    "Reset SOFORT aus (Strg+Alt+AltGr "
                                    "ueber uinput)")
                                send_reset_combo()
                                reset_since = None
                                reset_gefeuert = True
                        elif not any_reset_held:
                            if reset_since is not None:
                                LOG("wait_game_exit: reset_since ZURUECKGESETZT "
                                    "nach %.2fs (F5-Bit nicht mehr erkannt, "
                                    "Schwelle war %.1fs)"
                                    % (time.monotonic() - reset_since,
                                       self.RESET_HOLD))
                            reset_since = None
                            # Taste losgelassen: der naechste Druck darf
                            # wieder ausloesen.
                            reset_gefeuert = False
                        continue
                    dev = fds.get(fd)
                    try:
                        data = os.read(fd, EVENT_SIZE)
                    except OSError:
                        self.rescan()
                        continue
                    if len(data) < EVENT_SIZE:
                        continue
                    _, _, etype, code, value = struct.unpack(EVENT_FMT, data)
                    if etype == EV_KEY and code == KEY_F10 and value == 1:
                        return "f10"
                    # ERWEITERTE DIAGNOSE (Nutzer-Test bestaetigt: bei einem
                    # 8BitDo-Controller kam ueber mehrere Tests hinweg nur EIN
                    # einziges, unzusammenhaengend wirkendes EV_KEY-Ereignis
                    # an - weder von der Gamepad- noch von der zusaetzlichen
                    # "Receiver Keyboard"-Schnittstelle des Adapters kam
                    # irgendetwas Erwartbares. Zwei verbliebene Verdaechte:
                    # (a) der Empfaenger sendet fuer diese Kombination einen
                    # ANDEREN Ereignistyp als EV_KEY (bisher komplett
                    # ausgefiltert), oder (b) der Empfaenger faengt die
                    # Kombination selbst ab, noch bevor sie Linux erreicht.
                    # Jetzt werden ALLE Ereignistypen protokolliert (ausser
                    # dem reinen SYN-Trennzeichen, das viel zu haeufig und
                    # bedeutungslos ist und sonst das Budget sofort
                    # aufbrauchen wuerde) - zeigt beim naechsten Test, ob
                    # ueberhaupt IRGENDETWAS ankommt, wenn die Kombination
                    # gedrueckt wird.
                    if etype != EV_SYN and etype != EV_ABS:
                        if combo_diag_budget[dev.path] > 0:
                            combo_diag_budget[dev.path] -= 1
                            LOG("wait_game_exit DIAGNOSE Controller (%s): "
                                "etype=%d code=%d value=%d (EV_KEY=%d "
                                "BTN_START=%d BTN_SELECT=%d BTN_MODE=%d)"
                                % (dev.path, etype, code, value, EV_KEY,
                                   BTN_START, BTN_SELECT, BTN_MODE))
                    if etype == EV_KEY and code in (BTN_START, BTN_SELECT):
                        key = (dev.path, code)
                        if value == 1:
                            down.add(key)
                        elif value == 0:
                            down.discard(key)
                        # Kombo: Start UND Select am selben Geraet gedrueckt?
                        active = False
                        for path in set(p for p, _c in down):
                            codes = {c for p, c in down if p == path}
                            if BTN_START in codes and BTN_SELECT in codes:
                                active = True
                        if active and combo_since is None:
                            combo_since = time.monotonic()
                        elif not active:
                            combo_since = None
        finally:
            for fd in kbd_fds:
                try:
                    os.close(fd)
                except OSError:
                    pass
            for fd in extra_hidraw_fds:
                try:
                    os.close(fd)
                except OSError:
                    pass

    def flush(self):
        for d in self.devices.values():
            fl = fcntl.fcntl(d.fd, fcntl.F_GETFL)
            fcntl.fcntl(d.fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
            try:
                while os.read(d.fd, EVENT_SIZE * 64):
                    pass
            except (BlockingIOError, OSError):
                pass
            finally:
                fcntl.fcntl(d.fd, fcntl.F_SETFL, fl)

    def inject(self, keycode):
        """Tasten-Event einspeisen (bevorzugt ueber die Tastatur).
        Funktioniert nur bei geloestem Grab.

        BUGFIX (Nutzer-Rueckmeldung): auf MiSTer-Setups mit einem
        Sony/PlayStation-artigen Controller wurde bisher IMMER dessen
        "Consumer Control"- bzw. "System Control"-Nebenschnittstelle
        getroffen statt der tatsaechlichen Tastatur - is_kbd basiert
        nur darauf, ob der Linux-Kernel IRGENDEINEN "kbd"-Handler an
        das Geraet gehaengt hat (siehe scan_devices()), was bei
        Controller-Nebenschnittstellen mit Medien-/Systemtasten
        ebenfalls zutrifft. Landete diese Nebenschnittstelle in der
        Aufzaehlung VOR der echten Tastatur, ging das injizierte F9
        (fuer den Wechsel in den Konsolenmodus) ins Leere - MiSTer
        blieb dauerhaft im eigenen Menue haengen, ohne dass unser Code
        abstuerzte (schwer zu finden, weil das Log ganz normal
        aussah). Deshalb jetzt ZUERST gezielt nach einem Geraet
        suchen, das "keyboard" im NAMEN traegt (deutlich zuverlaessigeres
        Signal als der generische Kernel-Handler) - nur wenn keins
        gefunden wird, auf die bisherige is_kbd-Heuristik zurueckfallen."""
        target = None
        for d in self.devices.values():
            if "keyboard" in d.name.lower():
                target = d
                break
        if target is None:
            for d in self.devices.values():
                if d.is_kbd:
                    target = d
                    break
        if target is None and self.devices:
            target = next(iter(self.devices.values()))
        if target is None:
            LOG("inject(%d): KEIN Zielgeraet!" % keycode)
            return
        LOG("inject(%d) -> %s" % (keycode, target.path))
        for value in (1, 0):
            ev  = struct.pack(EVENT_FMT, 0, 0, EV_KEY, keycode, value)
            syn = struct.pack(EVENT_FMT, 0, 0, EV_SYN, 0, 0)
            try:
                os.write(target.fd, ev + syn)
            except OSError:
                pass
            time.sleep(0.05)

    def close(self):
        for d in self.devices.values():
            d.close()
        self.devices = {}
