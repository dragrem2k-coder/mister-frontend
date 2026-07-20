#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MiSTer Custom Frontend - v1.1
=======================================
Reines Standard-Python, keine externen Abhaengigkeiten.

Neu in v1.1:
  - Im Spiel: START+SELECT ca. 1 Sekunde gemeinsam halten
    -> zurueck ins Frontend (ohne OSD-Umweg)

Neu in v1.0:
  - System-Hintergrundbilder: legt man unter
    /media/fat/frontend/bg/ eine Datei <Systemkey>_<BREITE>x<HOEHE>.art
    (oder <Systemkey>.art) ab, wird sie in dieser Kategorie als
    abgedunkelter Vollbild-Hintergrund gezeigt.
    Erzeugen am PC:  python art_convert.py --bg --images nes.jpg
                     --out NES_320x240.art --size 320x240

Neu in v0.9:
  - Boxart wird auf grossen Aufloesungen automatisch ganzzahlig
    hochskaliert (Pixel-Look, gecacht) - sd-Cover fuellen 1080p
  - Arcade-Kategorie mit Info-Panel: Jahr, Hersteller, Kategorie
    werden live aus der jeweiligen MRA-Datei gelesen

Neu in v0.8:
  - BUGFIX: Eingaben-Freeze nach langem Gedrueckthalten behoben
    (Geraete-Events haben jetzt immer Vorrang vor Wiederholungen)
  - Schnellstart: Spieleliste wird gecacht statt bei jedem Start
    die Platte zu durchsuchen; System-Eintrag "Spieleliste neu einlesen"
  - System-Eintrag "Menue-Video: CRT/HDMI umschalten" - setzt den
    [Menu]-Block in der MiSTer.ini und startet neu

Neu in v0.7:
  - Kategorien-Spalte scrollt mit (Pfeil-Indikatoren oben/unten)
  - Gedrueckt halten von D-Pad/Stick wiederholt mit Beschleunigung
  - L/R bzw. Bild auf/ab springen zum naechsten Anfangsbuchstaben

Neu in v0.6:
  - Anzeigenamen ohne Klammer-Zusaetze (voller Name bleibt intern)
  - Laufschrift in der Auswahlzeile fuer lange Namen
  - Kategorien-Spalte passt ihre Breite automatisch an,
    kompaktere Kopf-/Fusszeile bei kleinen CRT-Aufloesungen

Neu in v0.5:
  - Spiele-Browser: eigene Kategorie pro System (NES, SNES, ...)
    mit allen ROMs aus /media/fat/games/<System>/
  - Spielstart per automatisch erzeugter MGL-Datei (Parameter
    aus der mrext-Systemdatenbank uebernommen)
  - Boxart-Anzeige aus vorkonvertierten .art-Dateien
    (/media/fat/frontend/art/...) plus Metadaten (Spieler, Jahr,
    Genre) aus /media/fat/frontend/meta/<System>.json

Neu in v0.4:
  - Gamepad-Unterstuetzung: D-Pad/Analogstick = Navigieren,
    A/Start = OK, B = zurueck, L/R = 15er-Spruenge,
    Guide/Home-Button = MiSTer-OSD, Select 3x hintereinander = Beenden
  - Hotplug: Pads koennen bei laufendem Frontend an-/abgesteckt werden

Neu in v0.3:
  - Schaltet MiSTer beim Start automatisch in den Konsolenmodus (F9),
    damit das MiSTer-Wallpaper unser Bild nicht mehr uebermalt;
    beim Beenden geht es per F12 zurueck ins normale Menue

Neu in v0.2:
  - Aufloesungsadaptives Layout: funktioniert von 1080p (HDMI)
    bis 640x480 (VGA/CRT) - Framebuffer-Groesse wird live gelesen
  - Kategorien werden automatisch aus allen /media/fat/_*-Ordnern
    erkannt (.rbf und .mra), inkl. deiner eigenen Ordner
  - Neue Kategorie "Scripts": startet /media/fat/Scripts/*.sh
    direkt auf der Konsole, danach uebernimmt das Frontend wieder
  - Neue Kategorie "System": oeffnet das echte MiSTer-OSD
    (fuer "Define joystick buttons", ini-Settings usw.) per
    F12-Injection; Rueckkehr ins Frontend mit F10
  - F12 im Frontend oeffnet das OSD jederzeit direkt

Steuerung:
  Pfeiltasten  Navigieren (links/rechts wechselt Spalte)
  Enter        Starten / Ausfuehren
  Bild auf/ab  15 Eintraege springen
  F12          MiSTer-OSD oeffnen (zurueck mit F10)
  ESC          Frontend beenden

Start auf dem MiSTer (per SSH oder als Startscript):
  python3 /media/fat/frontend/frontend.py
"""

import os, sys, mmap, struct, fcntl, time, re, glob, subprocess, traceback, zlib, json

LOGFILE = "/tmp/frontend.log"

def LOG(msg):
    try:
        with open(LOGFILE, "a") as f:
            f.write("%s  %s\n" % (time.strftime("%H:%M:%S"), msg))
    except OSError:
        pass

# ----------------------------------------------------------------------------
# KONFIGURATION
# ----------------------------------------------------------------------------

BASE        = "/media/fat"
SCRIPTS_DIR = "/media/fat/Scripts"
# Alle Orte, an denen ROMs liegen koennen (SD + USB-Laufwerke)
GAMES_BASES = (["/media/fat/games"]
               + ["/media/usb%d/games" % i for i in range(6)]
               + ["/media/usb%d" % i for i in range(6)])
ART_BASE    = "/media/fat/frontend/art"
ART_HD      = "/media/fat/frontend/art_hd"
BG_BASE     = "/media/fat/frontend/bg"
META_BASE   = "/media/fat/frontend/meta"
MGL_TMP     = "/tmp/frontend_launch.mgl"
GAMES_CACHE = "/media/fat/frontend/games_cache.json"
MISTER_CMD  = "/dev/MiSTer_cmd"
CORENAME    = "/tmp/CORENAME"
FBDEV       = "/dev/fb0"

# Ordner, die bei der automatischen Kategorie-Suche uebersprungen werden
SKIP_DIRS = {"_Scripts"}

# Huebschere Anzeigenamen fuer bekannte Ordner
NICE_NAMES = {
    "Arcade": "Arcade", "Console": "Konsolen", "Computer": "Computer",
    "Other": "Sonstige", "Utility": "Werkzeuge", "RA_Cores": "RA Cores",
}

# Spielesysteme: (Anzeigename, Systemkey, ROM-Ordner, Core-RBF,
#                  {Endung: (mgl_delay, mgl_type, mgl_index)})
# MGL-Parameter stammen aus der mrext-Systemdatenbank (wizzomafizzo).
GAME_SYSTEMS = [
    ("NES",           "NES",     ["NES"],                  "_Console/NES",
        {".nes": (2, "f", 1)}),
    ("SNES",          "SNES",    ["SNES"],                 "_Console/SNES",
        {".sfc": (2, "f", 0), ".smc": (2, "f", 0)}),
    ("Mega Drive",    "Genesis", ["MegaDrive", "Genesis"], "_Console/MegaDrive",
        {".md": (1, "f", 1), ".gen": (1, "f", 1), ".bin": (1, "f", 1)}),
    ("Nintendo 64",   "N64",     ["N64"],                  "_Console/N64",
        {".n64": (1, "f", 1), ".z64": (1, "f", 1)}),
    ("PlayStation",   "PSX",     ["PSX"],                  "_Console/PSX",
        {".chd": (1, "s", 1), ".cue": (1, "s", 1)}),
    ("Game Boy",      "GAMEBOY", ["GAMEBOY"],              "_Console/Gameboy",
        {".gb": (2, "f", 1), ".gbc": (2, "f", 1)}),
    ("GBA",           "GBA",     ["GBA"],                  "_Console/GBA",
        {".gba": (2, "f", 1)}),
    ("Master System", "SMS",     ["SMS"],                  "_Console/SMS",
        {".sms": (1, "f", 1), ".gg": (1, "f", 2)}),
    ("TurboGrafx16",  "TGFX16",  ["TGFX16"],               "_Console/TurboGrafx16",
        {".pce": (1, "f", 0), ".sgx": (1, "f", 1)}),
    ("Mega CD",       "MegaCD",  ["MegaCD"],               "_Console/MegaCD",
        {".chd": (1, "s", 0), ".cue": (1, "s", 0)}),
    ("Saturn",        "Saturn",  ["Saturn"],               "_Console/Saturn",
        {".chd": (1, "s", 0), ".cue": (1, "s", 0)}),
    ("Neo Geo",       "NEOGEO",  ["NEOGEO"],               "_Console/NeoGeo",
        {".neo": (1, "f", 1)}),
]

# Overscan-Sicherheitsrand in Prozent pro Seite (CRTs beschneiden das Bild).
# Bei Bedarf anpassen: mehr, wenn weiterhin Raender fehlen; weniger auf LCD.
OVERSCAN_X = 7
OVERSCAN_Y = 5

# Farben als (R, G, B)
C_BG     = (16, 18, 24)
C_PANEL  = (28, 32, 44)
C_ACCENT = (66, 133, 244)
C_ACCENT2= (40, 70, 120)
C_TEXT   = (220, 224, 232)
C_DIM    = (120, 126, 140)
C_TITLE  = (255, 200, 60)

# ----------------------------------------------------------------------------
# 8x8 BITMAP-FONT (Public Domain, IBM VGA / Marcel Sondaar / Daniel Hepper)
# ----------------------------------------------------------------------------
FONT8X8 = bytes.fromhex('000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000183c3c1818001800363600000000000036367f367f3636000c3e031e301f0c00006333180c6663001c361c6e3b336e000606030000000000180c0606060c1800060c1818180c060000663cff3c660000000c0c3f0c0c000000000000000c0c060000003f0000000000000000000c0c006030180c060301003e63737b6f673e000c0e0c0c0c0c3f001e33301c06333f001e33301c30331e00383c36337f3078003f031f3030331e001c06031f33331e003f3330180c0c0c001e33331e33331e001e33333e30180e00000c0c00000c0c00000c0c00000c0c06180c0603060c180000003f00003f0000060c1830180c06001e3330180c000c003e637b7b7b031e000c1e33333f3333003f66663e66663f003c66030303663c001f36666666361f007f46161e16467f007f46161e16060f003c66030373667c003333333f333333001e0c0c0c0c0c1e007830303033331e006766361e366667000f06060646667f0063777f7f6b63630063676f7b736363001c36636363361c003f66663e06060f001e3333333b1e38003f66663e366667001e33070e38331e003f2d0c0c0c0c1e003333333333333f0033333333331e0c006363636b7f7763006363361c1c3663003333331e0c0c1e007f6331184c667f001e06060606061e0003060c18306040001e18181818181e00081c36630000000000000000000000ff0c0c18000000000000001e303e336e000706063e66663b0000001e3303331e003830303e33336e0000001e333f031e001c36060f06060f0000006e33333e301f0706366e666667000c000e0c0c0c1e00300030303033331e070666361e3667000e0c0c0c0c0c1e000000337f7f6b630000001f333333330000001e3333331e0000003b66663e060f00006e33333e307800003b6e66060f0000003e031e301f00080c3e0c0c2c18000000333333336e0000003333331e0c000000636b7f7f3600000063361c36630000003333333e301f00003f190c263f00380c0c070c0c38001818180018181800070c0c380c0c07006e3b0000000000000000000000000000')

# ----------------------------------------------------------------------------
# FRAMEBUFFER
# ----------------------------------------------------------------------------

class Framebuffer:
    def __init__(self):
        self._read_geometry()
        self.fd = os.open(FBDEV, os.O_RDWR)
        self._map()
        self._rowcache = {}
        self._glyphcache = {}

    def _read_geometry(self):
        w, h = open("/sys/class/graphics/fb0/virtual_size").read().split(",")
        self.width  = int(w)
        self.height = int(h)
        self.bpp    = int(open("/sys/class/graphics/fb0/bits_per_pixel").read())
        self.stride = int(open("/sys/class/graphics/fb0/stride").read())
        if self.bpp != 32:
            sys.exit("Nur 32bpp wird unterstuetzt, gefunden: %d" % self.bpp)
        self.size = self.stride * self.height

    def _map(self):
        self.mm = mmap.mmap(self.fd, self.size, mmap.MAP_SHARED,
                            mmap.PROT_READ | mmap.PROT_WRITE)
        self.buf = bytearray(self.size)

    def refresh_geometry(self):
        """Nach Rueckkehr aus einem Core neu einlesen - die Aufloesung
        kann sich geaendert haben (z.B. anderer Videomodus)."""
        old = (self.width, self.height, self.stride)
        self._read_geometry()
        if (self.width, self.height, self.stride) != old:
            try:
                self.mm.close()
            except Exception:
                pass
            self._map()
            self._rowcache.clear()

    @staticmethod
    def px(rgb):
        r, g, b = rgb
        return bytes((b, g, r, 0))

    def clear(self, rgb):
        key = ("bg", rgb, self.width, self.height)
        bg = self._rowcache.get(key)
        if bg is None:
            row = self.px(rgb) * self.width
            pad = b"\x00" * (self.stride - self.width * 4)
            bg = (row + pad) * self.height
            self._rowcache[key] = bg
        self.buf[:] = bg

    def rect(self, x, y, w, h, rgb):
        x = max(0, x); y = max(0, y)
        w = min(w, self.width - x); h = min(h, self.height - y)
        if w <= 0 or h <= 0:
            return
        key = (rgb, w)
        row = self._rowcache.get(key)
        if row is None:
            row = self.px(rgb) * w
            self._rowcache[key] = row
        for yy in range(y, y + h):
            off = yy * self.stride + x * 4
            self.buf[off:off + w * 4] = row

    def _glyph_row(self, bits, scale, fg, bg):
        key = (bits, scale, fg, bg)
        row = self._glyphcache.get(key)
        if row is None:
            f = self.px(fg); b = self.px(bg)
            row = b"".join((f if bits >> i & 1 else b) * scale for i in range(8))
            self._glyphcache[key] = row
        return row

    def text(self, x, y, s, scale=2, fg=C_TEXT, bg=None):
        if bg is None:
            bg = C_BG
        cw = 8 * scale
        if y + 8 * scale > self.height or y < 0:
            return
        for ci, ch in enumerate(s):
            code = ord(ch)
            if code > 127:
                code = ord("?")
            gx = x + ci * cw
            if gx + cw > self.width:
                break
            for gy in range(8):
                bits = FONT8X8[code * 8 + gy]
                row = self._glyph_row(bits, scale, fg, bg)
                base = (y + gy * scale) * self.stride + gx * 4
                for rep in range(scale):
                    off = base + rep * self.stride
                    self.buf[off:off + cw * 4] = row

    def flip(self):
        self.mm.seek(0)
        self.mm.write(bytes(self.buf))

    def flip_rows(self, y, h):
        """Nur einen Zeilenbereich auf den Schirm bringen (Laufschrift)."""
        y0 = max(0, y)
        y1 = min(self.height, y + h)
        if y1 <= y0:
            return
        off = y0 * self.stride
        self.mm.seek(off)
        self.mm.write(bytes(self.buf[off:y1 * self.stride]))

    def close(self):
        try:
            self.mm.close(); os.close(self.fd)
        except Exception:
            pass

# ----------------------------------------------------------------------------
# EINGABE: Tastatur + Gamepads parallel, mit Hotplug und exklusivem Grab
# ----------------------------------------------------------------------------

import select

EVIOCGRAB = 0x40044590
EV_SYN, EV_KEY, EV_ABS = 0, 1, 3
KEY_ESC, KEY_ENTER = 1, 28
KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT = 103, 108, 105, 106
KEY_PGUP, KEY_PGDN = 104, 109
KEY_F9, KEY_F10, KEY_F12 = 67, 68, 88
# Gamepad-Buttons (Linux-Standardcodes)
BTN_A, BTN_B, BTN_X, BTN_Y = 304, 305, 307, 308
BTN_TL, BTN_TR = 310, 311
BTN_SELECT, BTN_START, BTN_MODE = 314, 315, 316
BTN_DPAD_UP, BTN_DPAD_DOWN, BTN_DPAD_LEFT, BTN_DPAD_RIGHT = 544, 545, 546, 547
# Achsen
ABS_X, ABS_Y, ABS_HAT0X, ABS_HAT0Y = 0, 1, 16, 17
EVENT_FMT  = "llHHi"
EVENT_SIZE = struct.calcsize(EVENT_FMT)

# Tasten/Buttons -> logische Aktionen des Frontends
KEYMAP = {
    KEY_UP: "up", KEY_DOWN: "down", KEY_LEFT: "left", KEY_RIGHT: "right",
    KEY_ENTER: "ok", KEY_ESC: "exit", KEY_PGUP: "pgup", KEY_PGDN: "pgdn",
    KEY_F12: "osd", KEY_F10: "back_fe", KEY_F9: None,
    BTN_A: "ok", BTN_START: "ok",
    BTN_B: "back", BTN_X: "back_fe",
    BTN_TL: "pgup", BTN_TR: "pgdn",
    BTN_MODE: "osd", BTN_SELECT: "select",
    BTN_DPAD_UP: "up", BTN_DPAD_DOWN: "down",
    BTN_DPAD_LEFT: "left", BTN_DPAD_RIGHT: "right",
}

# Richtungs-Aktionen, die beim Halten wiederholt werden
REPEAT_ACTIONS = {"up", "down", "left", "right"}
REPEAT_DELAY    = 0.40      # Sekunden bis zur ersten Wiederholung
REPEAT_INTERVAL = 0.14      # Start-Intervall, beschleunigt bis 0.05

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
        for ax in (ABS_X, ABS_Y, ABS_HAT0X, ABS_HAT0Y):
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
        self.rescan()

    def rescan(self):
        self.last_scan = time.time()
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

    def _hold(self, key_id, act):
        if act in REPEAT_ACTIONS:
            self.held = (key_id, act, time.time() + REPEAT_DELAY,
                         REPEAT_INTERVAL)

    def _release(self, key_id):
        if self.held and self.held[0] == key_id:
            self.held = None

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
            if value in (1, 2):       # Tastatur wiederholt selbst (value 2)
                return KEYMAP.get(code)
            return None
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
        Wiederholungen, damit ein Loslassen nie verloren geht."""
        deadline = None if timeout is None else time.time() + timeout
        while True:
            now = time.time()
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
            if self.held is not None and time.time() >= self.held[2]:
                kid, act, _t, iv = self.held
                iv = max(0.05, iv * 0.85)
                self.held = (kid, act, time.time() + iv, iv)
                return act
            if deadline is not None and time.time() >= deadline:
                return None

    COMBO_HOLD = 0.8          # Sekunden Start+Select halten

    def wait_game_exit(self):
        """Waehrend ein Core laeuft: warten, bis MiSTer zurueck im
        Menue ist ODER Start+Select lange genug gehalten werden.
        Rueckgabe: "menu" oder "combo"."""
        down = set()              # (geraetepfad, code) gedrueckter Tasten
        combo_since = None
        last_core_check = 0.0
        while True:
            now = time.time()
            if now - self.last_scan > self.RESCAN_EVERY:
                self.rescan()
                down = {k for k in down if k[0] in self.devices}
            if now - last_core_check > 0.7:
                last_core_check = now
                if current_core() == "MENU":
                    return "menu"
            if combo_since is not None and now - combo_since >= self.COMBO_HOLD:
                return "combo"
            fds = {d.fd: d for d in self.devices.values()}
            if not fds:
                time.sleep(0.5)
                continue
            try:
                r, _, _ = select.select(list(fds), [], [], 0.2)
            except OSError:
                self.rescan()
                continue
            for fd in r:
                dev = fds.get(fd)
                try:
                    data = os.read(fd, EVENT_SIZE)
                except OSError:
                    self.rescan()
                    continue
                if len(data) < EVENT_SIZE:
                    continue
                _, _, etype, code, value = struct.unpack(EVENT_FMT, data)
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
                        combo_since = time.time()
                    elif not active:
                        combo_since = None

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
        Funktioniert nur bei geloestem Grab."""
        target = None
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

# ----------------------------------------------------------------------------
# ARTWORK (.art) UND METADATEN
# .art-Format: b"ART1" + uint16 Breite + uint16 Hoehe + zlib(BGRA-Rohpixel)
# Die Dateien werden am PC mit art_convert.py erzeugt - der MiSTer
# muss nur noch entpacken (zlib ist Standardbibliothek) und blitten.
# ----------------------------------------------------------------------------

class ArtCache:
    LIMIT = 40                       # max. Bilder im Speicher halten

    def __init__(self):
        self.cache = {}              # pfad -> (w, h, pixelbytes) oder None
        self.order = []

    def get(self, path):
        if path in self.cache:
            return self.cache[path]
        art = None
        try:
            with open(path, "rb") as f:
                if f.read(4) == b"ART1":
                    w, h = struct.unpack("<HH", f.read(4))
                    pix = zlib.decompress(f.read())
                    if len(pix) == w * h * 4:
                        art = (w, h, pix)
        except OSError:
            pass
        self.cache[path] = art
        self.order.append(path)
        if len(self.order) > self.LIMIT:
            old = self.order.pop(0)
            self.cache.pop(old, None)
        return art

    SCALED_LIMIT = 10

    def get_scaled(self, path, max_w, max_h):
        """Bild ganzzahlig auf den verfuegbaren Platz hochskalieren."""
        base = self.get(path)
        if not base:
            return None
        w, h, pix = base
        scale = max(1, min(max_w // w, max_h // h, 4))
        if scale == 1:
            return base
        key = (path, scale)
        if not hasattr(self, "scaled"):
            self.scaled = {}
            self.scaled_order = []
        if key in self.scaled:
            return self.scaled[key]
        sw, sh = w * scale, h * scale
        out = bytearray(sw * sh * 4)
        row_out = sw * 4
        for y in range(h):
            o = y * w * 4
            row = b"".join(pix[o + x*4:o + x*4 + 4] * scale
                           for x in range(w))
            base_off = y * scale * row_out
            for rep in range(scale):
                off = base_off + rep * row_out
                out[off:off + row_out] = row
        result = (sw, sh, bytes(out))
        self.scaled[key] = result
        self.scaled_order.append(key)
        if len(self.scaled_order) > self.SCALED_LIMIT:
            old = self.scaled_order.pop(0)
            self.scaled.pop(old, None)
        return result

ART = ArtCache()

class BgCache:
    """Haelt pro System einen fertig komponierten Vollbild-Puffer
    (inkl. Stride-Padding), damit der Hintergrund beim Zeichnen nur
    noch per Blockkopie eingesetzt werden muss."""
    LIMIT = 2

    def __init__(self):
        self.cache = {}
        self.order = []

    def get(self, syskey, fb):
        key = (syskey, fb.width, fb.height, fb.stride)
        if key in self.cache:
            return self.cache[key]
        buf = None
        for fn in ("%s_%dx%d.art" % (syskey, fb.width, fb.height),
                   "%s.art" % syskey):
            art = ART.get(os.path.join(BG_BASE, fn))
            if art:
                buf = self._compose(art, fb)
                break
        self.cache[key] = buf
        self.order.append(key)
        if len(self.order) > self.LIMIT:
            self.cache.pop(self.order.pop(0), None)
        return buf

    @staticmethod
    def _compose(art, fb):
        w, h, pix = art
        base = Framebuffer.px(C_BG)
        row_bg = base * fb.width + b"\x00" * (fb.stride - fb.width * 4)
        out = bytearray(row_bg * fb.height)
        # Bild zentrieren, bei Ueberbreite mittig beschneiden
        sx = max(0, (w - fb.width) // 2)
        dx = max(0, (fb.width - w) // 2)
        cw = min(w, fb.width)
        sy = max(0, (h - fb.height) // 2)
        dy = max(0, (fb.height - h) // 2)
        ch = min(h, fb.height)
        for y in range(ch):
            so = ((sy + y) * w + sx) * 4
            do = (dy + y) * fb.stride + dx * 4
            out[do:do + cw * 4] = pix[so:so + cw * 4]
        return bytes(out)

BG = BgCache()

def art_path(syskey, rom_basename):
    return os.path.join(ART_BASE, syskey, rom_basename + ".art")

_meta_cache = {}
_mra_cache = {}

def mra_meta(path):
    """Jahr/Hersteller/Kategorie/Spieler aus einer MRA-Datei lesen."""
    if path in _mra_cache:
        return _mra_cache[path]
    meta = {}
    try:
        with open(path, "r", errors="replace") as f:
            head = f.read(4096)
        for tag, key in (("year", "year"), ("manufacturer", "manufacturer"),
                         ("category", "genre"), ("players", "players")):
            m = re.search(r"<%s>\s*([^<]+?)\s*</%s>" % (tag, tag), head,
                          re.I)
            if m:
                meta[key] = m.group(1)
    except OSError:
        pass
    _mra_cache[path] = meta
    if len(_mra_cache) > 200:
        _mra_cache.pop(next(iter(_mra_cache)))
    return meta

def get_meta(syskey, rom_basename):
    """Metadaten (players/year/genre) fuer ein Spiel, lazy geladen."""
    if syskey not in _meta_cache:
        data = {}
        try:
            with open(os.path.join(META_BASE, syskey + ".json")) as f:
                data = json.load(f)
        except (OSError, ValueError):
            pass
        _meta_cache[syskey] = data
    return _meta_cache[syskey].get(rom_basename, {})

# ----------------------------------------------------------------------------
# KATEGORIEN & AKTIONEN
# ----------------------------------------------------------------------------

_TAGS = re.compile(r"\s*[\(\[][^\)\]]*[\)\]]")

def display_name(full):
    """Klammer-Zusaetze fuer die Anzeige entfernen."""
    short = _TAGS.sub("", full).strip()
    return short if short else full

def nice_name(dirname):
    raw = dirname.lstrip("_")
    return NICE_NAMES.get(raw, raw.replace("_", " "))

def scan_cores():
    """Alle /media/fat/_*-Ordner nach .rbf/.mra durchsuchen."""
    cats = []
    for d in sorted(glob.glob(os.path.join(BASE, "_*"))):
        if not os.path.isdir(d) or os.path.basename(d) in SKIP_DIRS:
            continue
        items = []
        for f in sorted(glob.glob(os.path.join(d, "*.mra")) +
                        glob.glob(os.path.join(d, "*.rbf"))):
            name = os.path.splitext(os.path.basename(f))[0]
            name = re.sub(r"_\d{8}[a-zA-Z]?$", "", name)
            items.append((name, "core", f))
        if items:
            # Arcade-Ordner bekommen ein Info-Panel (MRA-Metadaten)
            base = os.path.basename(d).lstrip("_").lower()
            syskey = "ARCADE" if "arcade" in base else None
            cats.append((nice_name(os.path.basename(d)), items, syskey))
    return cats

def _games_signature():
    """Schneller Fingerabdruck der ROM-Ordner (ohne Tiefensuche):
    existierende Wurzeln + deren mtime. Aendert sich der Inhalt einer
    Wurzel direkt, aendert sich die Signatur; bei Aenderungen tief in
    Unterordnern hilft der System-Eintrag 'Spieleliste neu einlesen'."""
    sig = []
    for base in GAMES_BASES:
        if not os.path.isdir(base):
            continue
        for _d, _sk, folders, _r, _e in GAME_SYSTEMS:
            for folder in folders:
                root = os.path.join(base, folder)
                try:
                    sig.append((root, int(os.path.getmtime(root))))
                except OSError:
                    pass
    return sig

def _cats_to_json(cats):
    return [[n, [[i0, i1, list(i2[:4]) + [list(i2[4])]] for i0, i1, i2 in it], sk]
            for n, it, sk in cats]

def _cats_from_json(data):
    cats = []
    for n, it, sk in data:
        items = [(i0, i1, (i2[0], i2[1], i2[2], i2[3], tuple(i2[4])))
                 for i0, i1, i2 in it]
        cats.append((n, items, sk))
    return cats

def scan_games(force=False):
    """ROM-Listen laden - aus dem Cache, wenn er noch passt."""
    sig = _games_signature()
    if not force:
        try:
            with open(GAMES_CACHE) as f:
                data = json.load(f)
            if data.get("sig") == [list(s) for s in sig]:
                LOG("Spieleliste aus Cache (%d Systeme)"
                    % len(data["cats"]))
                return _cats_from_json(data["cats"])
        except (OSError, ValueError, KeyError, IndexError, TypeError):
            pass
    cats = _scan_games_disk()
    try:
        with open(GAMES_CACHE, "w") as f:
            json.dump({"sig": [list(s) for s in sig],
                       "cats": _cats_to_json(cats)}, f)
    except OSError:
        pass
    return cats

def _scan_games_disk():
    """Fuer jedes bekannte System die ROMs einsammeln (Tiefensuche).
    Rueckgabe: Liste (Anzeigename, Items, Systemkey)."""
    cats = []
    for disp, syskey, folders, rbf, extmap in GAME_SYSTEMS:
        items = []
        seen_roots = set()
        for base in GAMES_BASES:
            if not os.path.isdir(base):
                continue
            for folder in folders:
                root = os.path.join(base, folder)
                real = os.path.realpath(root)
                if not os.path.isdir(root) or real in seen_roots:
                    continue
                seen_roots.add(real)
                base_depth = root.rstrip("/").count("/")
                for dirpath, dirnames, filenames in os.walk(root):
                    # max. 2 Ebenen tief, versteckte Ordner auslassen
                    if dirpath.count("/") - base_depth >= 2:
                        dirnames[:] = []
                        continue
                    dirnames[:] = [d for d in dirnames
                                   if not d.startswith(".")]
                    for fn in filenames:
                        ext = os.path.splitext(fn)[1].lower()
                        if ext in extmap:
                            name = os.path.splitext(fn)[0]
                            items.append((name, "game",
                                          (os.path.join(dirpath, fn), ext,
                                           syskey, rbf, extmap[ext])))
        if items:
            items.sort(key=lambda t: t[0].lower())
            cats.append((disp, items, syskey))
    return cats

def write_mgl(rbf, rom_path, delay, ftype, index):
    """MGL-Startdatei erzeugen (Pfad-Konvention wie in mrext)."""
    xml = ('<mistergamedescription>\n'
           '\t<rbf>%s</rbf>\n'
           '\t<file delay="%d" type="%s" index="%d" '
           'path="../../../../..%s"/>\n'
           '</mistergamedescription>\n'
           % (rbf, delay, ftype, index, rom_path))
    with open(MGL_TMP, "w") as f:
        f.write(xml)
    return MGL_TMP

def scan_scripts():
    items = []
    for f in sorted(glob.glob(os.path.join(SCRIPTS_DIR, "*.sh"))):
        name = os.path.splitext(os.path.basename(f))[0].replace("_", " ")
        items.append((name, "script", f))
    return items

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
    open(MISTER_INI, "w").write(ini)
    return active

def system_items():
    crt = crt_menu_active()
    video = ("Menue-Video: CRT -> auf HDMI wechseln" if crt
             else "Menue-Video: HDMI -> auf CRT wechseln")
    return [
        ("MiSTer-OSD oeffnen (Settings/Buttons)", "osd",     None),
        (video + " (Neustart)",                   "crtmenu", None),
        ("Spieleliste neu einlesen",              "rescan",  None),
        ("Anzeige neu aufbauen",                  "redraw",  None),
        ("MiSTer neu starten",                    "reboot",  None),
        ("Frontend beenden",                      "quit",    None),
    ]

def _letter_of(name):
    for ch in name:
        if ch.isalnum():
            return ch.upper()
    return "#"

def letter_jump(items, i, direction):
    """Index des naechsten/vorherigen Anfangsbuchstaben-Blocks."""
    if not items:
        return i
    cur = _letter_of(items[i][0])
    j = i
    if direction > 0:
        while j < len(items) - 1:
            j += 1
            if _letter_of(items[j][0]) != cur:
                break
    else:
        start = j
        while start > 0 and _letter_of(items[start - 1][0]) == cur:
            start -= 1
        if start != j:
            return start          # erst zum Anfang des eigenen Blocks
        if start > 0:
            j = start - 1
            prev = _letter_of(items[j][0])
            while j > 0 and _letter_of(items[j - 1][0]) == prev:
                j -= 1
    return j

def current_core():
    try:
        return open(CORENAME).read().strip("\x00 \n\r\t")
    except OSError:
        return ""

def launch_core(path):
    with open(MISTER_CMD, "w") as f:
        f.write("load_core " + path)

# ----------------------------------------------------------------------------
# FRONTEND
# ----------------------------------------------------------------------------

class Frontend:
    def __init__(self):
        self.fb = Framebuffer()
        self.inp = InputManager()
        self.build_categories()
        self.cat_i = self.item_i = self.scroll = 0
        self.cat_scroll = 0
        self.focus = 0
        self.mq_off = 0            # Laufschrift-Versatz (Zeichen)
        self.mq_pause = 0          # Pausen-Ticks an den Enden

    def build_categories(self, force_rescan=False):
        # Reihenfolge: Spiele-Systeme, dann Core-Ordner, Scripts, System
        self.cats = scan_games(force=force_rescan)
        self.cats.extend(scan_cores())
        scripts = scan_scripts()
        if scripts:
            self.cats.append(("Scripts", scripts, None))
        self.cats.append(("System", system_items(), None))

    # ------------------------------------------------------------------
    # Adaptives Layout: alles wird aus der Framebuffer-Hoehe abgeleitet.
    # 1080p -> Schrift 3x, 720p -> 2x, 480p -> 1x
    # ------------------------------------------------------------------
    def layout(self):
        W, H = self.fb.width, self.fb.height
        s  = max(1, H // 360)            # Basisschrift-Skalierung
        ox = W * OVERSCAN_X // 100
        oy = H * OVERSCAN_Y // 100
        L = {
            "s": s, "ox": ox, "oy": oy,
            # Panelbreite: laengster Kategoriename + Rand, gedeckelt auf 1/3
            "panel_w": self._panel_width(W - 2 * ox, s),
            "rowh":    15 * s,
            "cat_rowh": 20 * s,
            "margin":  10 * s,
        }
        L["list_x"] = ox + L["panel_w"] + 12 * s
        L["list_y"] = oy + (44 if H >= 400 else 28) * s
        L["visible"] = max(3, (H - L["list_y"] - 20 * s - oy) // L["rowh"])
        return L

    def _panel_width(self, W, s):
        longest = max((len(n) for n, _i, _sk in self.cats), default=8)
        want = longest * 8 * s + 14 * s
        return min(max(72, want), W // 3)

    def draw(self, message=None):
        fb = self.fb
        W, H = fb.width, fb.height
        L = self.layout()
        s = L["s"]

        ox, oy = L["ox"], L["oy"]
        _n, _i, _sk = self.cats[self.cat_i]
        self._cur_bg = BG.get(_sk, fb) if _sk else None
        if self._cur_bg is not None:
            fb.buf[:] = self._cur_bg
        else:
            fb.clear(C_BG)
        fb.rect(0, 0, ox + L["panel_w"], H, C_PANEL)
        fb.text(ox + 6 * s, oy + 10 * s, "MiSTer", 2 * s, C_TITLE, C_PANEL)

        # Kategorien links (mit eigenem Scrollfenster)
        cat_y0 = oy + 34 * s
        cat_vis = max(2, (H - cat_y0 - oy - 18 * s) // L["cat_rowh"])
        if self.cat_i < self.cat_scroll:
            self.cat_scroll = self.cat_i
        if self.cat_i >= self.cat_scroll + cat_vis:
            self.cat_scroll = self.cat_i - cat_vis + 1
        self.cat_scroll = max(0, min(self.cat_scroll,
                                     max(0, len(self.cats) - cat_vis)))
        cat_end = min(self.cat_scroll + cat_vis, len(self.cats))
        if self.cat_scroll > 0:
            fb.text(ox + L["panel_w"] // 2 - 4 * s, cat_y0 - 11 * s,
                    "^", s, C_DIM, C_PANEL)
        if cat_end < len(self.cats):
            fb.text(ox + L["panel_w"] // 2 - 4 * s,
                    cat_y0 + cat_vis * L["cat_rowh"] - 2 * s,
                    "v", s, C_DIM, C_PANEL)
        for row, i in enumerate(range(self.cat_scroll, cat_end)):
            name, items, _sk = self.cats[i]
            y = cat_y0 + row * L["cat_rowh"]
            sel = (i == self.cat_i)
            bg = (C_ACCENT if self.focus == 0 else C_ACCENT2) if sel else C_PANEL
            if sel:
                fb.rect(ox + 2 * s, y - 3 * s, L["panel_w"] - 4 * s, 14 * s, bg)
            label = name
            maxc = (L["panel_w"] - 10 * s) // (8 * s)
            if len(label) > maxc:
                label = label[:max(1, maxc - 1)] + "~"
            fb.text(ox + 6 * s, y, label, s, C_TEXT if sel else C_DIM, bg)

        # Eintraege rechts
        name, items, syskey = self.cats[self.cat_i]
        total = len(items)
        # Bei Spiele-Kategorien rechts Platz fuer das Art-Panel lassen
        art_w = int(W * 0.34) if syskey else 0
        list_right = W - art_w - L["ox"]
        if self.item_i < self.scroll:
            self.scroll = self.item_i
        if self.item_i >= self.scroll + L["visible"]:
            self.scroll = self.item_i - L["visible"] + 1

        if H >= 400:
            fb.text(L["list_x"], oy + 12 * s, name.upper(), 2 * s, C_TITLE)
            fb.text(L["list_x"], oy + 32 * s, "%d Eintraege" % total, s, C_DIM)
        else:
            # niedrige CRT-Aufloesung: einzeilig, Platz sparen
            head = name.upper()
            fb.text(L["list_x"], oy + 12 * s, head, s, C_TITLE)
            cnt = "(%d)" % total
            fb.text(min(W - ox - len(cnt) * 8 * s,
                        L["list_x"] + (len(head) + 1) * 8 * s),
                    oy + 12 * s, cnt, s, C_DIM)

        # Ansichts-Zustand fuer Zeilen-Neuzeichnung (Laufschrift) merken
        self.view = {"L": L, "list_right": list_right, "items": items}
        end = min(self.scroll + L["visible"], total)
        for row, idx in enumerate(range(self.scroll, end)):
            self.draw_list_row(idx)

        # Art-Panel rechts (Boxart + Metadaten des markierten Spiels)
        if syskey and total:
            self.draw_art_panel(list_right, art_w, syskey,
                                items[self.item_i], L)

        # Fusszeile
        foot = message or (
            "Pfeile/D-Pad:Nav  Enter/A:Start  F12/Guide:OSD  ESC:Ende"
            if W >= 560 else "Nav:Pfeile  A:Start  F12:OSD")
        fb.text(ox + 6 * s, H - oy - 13 * s, foot, s, C_DIM, C_PANEL)
        fb.flip()

    def draw_list_row(self, idx):
        """Eine Listenzeile zeichnen. Die markierte Zeile zeigt bei
        Ueberlaenge einen Laufschrift-Ausschnitt des vollen Namens."""
        fb = self.fb
        v = self.view
        L = v["L"]; s = L["s"]
        row = idx - self.scroll
        y = L["list_y"] + row * L["rowh"]
        sel = (idx == self.item_i)
        bg = (C_ACCENT if self.focus == 1 else C_ACCENT2) if sel else C_BG
        x0 = L["list_x"] - 4 * s
        rw = v["list_right"] - L["list_x"] - 2 * s
        cur_bg = getattr(self, "_cur_bg", None)
        if cur_bg is not None:
            # Listenstreifen aus dem Hintergrundbild wiederherstellen
            for yy in range(max(0, y - 3 * s),
                            min(fb.height, y - 3 * s + L["rowh"] - 2 * s)):
                off = yy * fb.stride + x0 * 4
                fb.buf[off:off + rw * 4] = cur_bg[off:off + rw * 4]
            if sel:
                fb.rect(x0, y - 3 * s, rw, L["rowh"] - 2 * s, bg)
        else:
            fb.rect(x0, y - 3 * s, rw, L["rowh"] - 2 * s,
                    bg if sel else C_BG)
        full = v["items"][idx][0]
        maxc = (v["list_right"] - L["list_x"] - 8 * s) // (8 * s)
        if sel:
            # Markierte Zeile: voller Name, bei Bedarf als Laufschrift
            if len(full) > maxc:
                off = min(self.mq_off, len(full) - maxc)
                label = full[off:off + maxc]
            else:
                label = full
        else:
            label = display_name(full)
            if len(label) > maxc:
                label = label[:max(1, maxc - 1)] + "~"
        fb.text(L["list_x"], y, label, s, C_TEXT if sel else C_DIM, bg)
        return y

    def marquee_needed(self):
        v = getattr(self, "view", None)
        if not v or self.focus != 1 or not v["items"]:
            return False
        L = v["L"]; s = L["s"]
        maxc = (v["list_right"] - L["list_x"] - 8 * s) // (8 * s)
        return len(v["items"][self.item_i][0]) > maxc

    def marquee_tick(self):
        v = self.view
        L = v["L"]; s = L["s"]
        maxc = (v["list_right"] - L["list_x"] - 8 * s) // (8 * s)
        full = v["items"][self.item_i][0]
        max_off = len(full) - maxc
        if self.mq_pause > 0:
            self.mq_pause -= 1
            if self.mq_pause == 0 and self.mq_off >= max_off:
                self.mq_off = 0            # zurueck zum Anfang
                self.mq_pause = 4
        elif self.mq_off < max_off:
            self.mq_off += 1
            if self.mq_off >= max_off:
                self.mq_pause = 6          # am Ende kurz stehenbleiben
        y = self.draw_list_row(self.item_i)
        self.fb.flip_rows(y - 3 * L["s"], L["rowh"])

    def marquee_reset(self):
        self.mq_off = 0
        self.mq_pause = 4

    def next_action(self):
        """Wie read_action, treibt aber nebenbei die Laufschrift an."""
        while True:
            if not self.marquee_needed():
                return self.inp.read_action()
            act = self.inp.read_action(timeout=0.18)
            if act is not None:
                self.marquee_reset()
                return act
            self.marquee_tick()

    def draw_art_panel(self, x0, w, syskey, item, L):
        """Boxart + Metadaten rechts neben der Spieleliste."""
        fb = self.fb
        s = L["s"]
        H = fb.height
        name = item[0]
        fb.rect(x0, 0, self.fb.width - x0, H, C_PANEL)
        w = w  # Inhaltbreite (rechter Overscan liegt ausserhalb von w)
        pad = 6 * s
        y = L["list_y"]
        avail_w = w - 2 * pad
        avail_h = max(40, (H - y) * 3 // 5)
        # Auf grossen Aufloesungen zuerst die scharfe hd-Variante versuchen,
        # sonst die sd-Version ganzzahlig hochskalieren
        art = None
        if H >= 720:
            hd = os.path.join(ART_HD, syskey, name + ".art")
            art = ART.get_scaled(hd, avail_w, avail_h)
        if art is None:
            art = ART.get_scaled(art_path(syskey, name), avail_w, avail_h)
        if art:
            aw, ah, pix = art
            ax = x0 + max(0, (w - aw) // 2)
            self.blit(ax, y, aw, ah, pix)
            y += ah + 6 * s
        else:
            ph = min(int(w * 1.2), H // 2)
            fb.rect(x0 + pad, y, w - 2 * pad, ph, C_ACCENT2)
            fb.text(x0 + pad + 2 * s, y + ph // 2 - 4 * s, "kein", s,
                    C_DIM, C_ACCENT2)
            fb.text(x0 + pad + 2 * s, y + ph // 2 + 5 * s, "Artwork", s,
                    C_DIM, C_ACCENT2)
            y += ph + 6 * s
        if syskey == "ARCADE":
            meta = mra_meta(item[2])
        else:
            meta = get_meta(syskey, name)
        lines = []
        if meta.get("players"):
            lines.append("Spieler: %s" % meta["players"])
        if meta.get("year"):
            lines.append("Jahr: %s" % meta["year"])
        if meta.get("genre"):
            lines.append(str(meta["genre"]))
        if meta.get("manufacturer"):
            lines.append(str(meta["manufacturer"]))
        maxc = (w - 2 * pad) // (8 * s)
        for ln in lines:
            if y + 9 * s > H - 16 * s:
                break
            fb.text(x0 + pad, y, ln[:maxc], s, C_TEXT, C_PANEL)
            y += 11 * s

    def blit(self, x, y, w, h, pix):
        """Vordekodierte BGRA-Pixel zeilenweise in den Puffer kopieren."""
        fb = self.fb
        if x >= fb.width or y >= fb.height:
            return
        cw = min(w, fb.width - x)
        ch = min(h, fb.height - y)
        for row in range(ch):
            src_off = row * w * 4
            dst_off = (y + row) * fb.stride + x * 4
            fb.buf[dst_off:dst_off + cw * 4] = pix[src_off:src_off + cw * 4]

    # ------------------------------------------------------------------
    # Aktionen
    # ------------------------------------------------------------------

    def run_core(self, path):
        self.inp.grab(False)
        launch_core(path)
        t0 = time.time()
        while current_core() in ("", "MENU") and time.time() - t0 < 15:
            time.sleep(0.5)
        while current_core() != "MENU":
            res = self.inp.wait_game_exit()
            if res == "combo":
                LOG("Start+Select erkannt - zurueck ins Menue")
                launch_core("/media/fat/menu.rbf")
                t1 = time.time()
                while current_core() != "MENU" and time.time() - t1 < 10:
                    time.sleep(0.3)
        time.sleep(1.0)
        self.back_to_frontend()

    def run_script(self, path):
        """Script auf der Konsole (tty1) laufen lassen, danach zurueck."""
        self.inp.grab(False)
        self.set_cursor_blink(True)
        try:
            tty = open("/dev/tty1", "r+b", buffering=0)
        except OSError:
            tty = None
        # Bildschirm dem Script ueberlassen
        try:
            if tty:
                tty.write(b"\x1b[2J\x1b[H")     # Konsole loeschen
                subprocess.call(["/bin/bash", path],
                                stdin=tty, stdout=tty, stderr=tty,
                                env=dict(os.environ, TERM="linux",
                                         HOME="/root"))
                tty.write(b"\n-- Script beendet, Taste druecken --\n")
            else:
                subprocess.call(["/bin/bash", path])
        finally:
            if tty:
                tty.close()
        self.inp.read_action()                    # auf Eingabe warten
        self.back_to_frontend()

    def open_osd(self):
        """Echtes MiSTer-OSD oeffnen (fuer Joystick-Definition, Settings).
        Rueckkehr ins Frontend mit F10."""
        LOG("open_osd: Start")
        self.draw("MiSTer-OSD aktiv - F10 oder X-Button = zurueck")
        self.inp.grab(False)
        time.sleep(0.2)
        self.inp.inject(KEY_F12)
        LOG("open_osd: F12 injiziert, warte auf back_fe (F10/X)")
        while True:
            act = self.inp.read_action()
            LOG("open_osd passthrough: %s" % act)
            if act == "back_fe":
                break
        LOG("open_osd: Rueckkehr")
        self.back_to_frontend()

    def enter_console_mode(self):
        """MiSTer per F9 in den Konsolenmodus schalten - sonst uebermalt
        das MiSTer-Wallpaper unseren Framebuffer permanent.
        Muss bei GELOESTEM Grab passieren, damit MiSTer die Taste sieht."""
        LOG("enter_console_mode (F9)")
        self.inp.grab(False)
        time.sleep(0.1)
        self.inp.inject(KEY_F9)
        time.sleep(0.4)

    def back_to_frontend(self):
        self.enter_console_mode()
        self.set_cursor_blink(False)
        self.fb.refresh_geometry()
        self.inp.flush()
        self.inp.grab(True)
        self.draw()

    @staticmethod
    def set_cursor_blink(on):
        try:
            open("/sys/class/graphics/fbcon/cursor_blink", "w") \
                .write("1" if on else "0")
        except OSError:
            pass

    # ------------------------------------------------------------------
    # Hauptschleife
    # ------------------------------------------------------------------

    def run(self):
        self.enter_console_mode()
        self.set_cursor_blink(False)
        self.inp.grab(True)
        self.draw()
        try:
            select_count = 0
            while True:
                act = self.next_action()
                LOG("aktion: %s" % act)
                name, items, _syskey = self.cats[self.cat_i]
                if act == "select":
                    select_count += 1
                    if select_count >= 3:      # 3x Select = Beenden per Pad
                        break
                    continue
                select_count = 0
                if act == "exit":
                    break
                elif act == "osd":
                    self.open_osd()
                    continue
                elif act in ("back", "left"):
                    self.focus = 0
                elif act == "right":
                    self.focus = 1
                elif act == "up":
                    if self.focus == 0:
                        self.cat_i = (self.cat_i - 1) % len(self.cats)
                        self.item_i = self.scroll = 0
                    else:
                        self.item_i = max(0, self.item_i - 1)
                elif act == "down":
                    if self.focus == 0:
                        self.cat_i = (self.cat_i + 1) % len(self.cats)
                        self.item_i = self.scroll = 0
                    else:
                        self.item_i = min(len(items) - 1, self.item_i + 1)
                elif act == "pgup" and self.focus == 1:
                    self.item_i = letter_jump(items, self.item_i, -1)
                elif act == "pgdn" and self.focus == 1:
                    self.item_i = letter_jump(items, self.item_i, +1)
                elif act == "ok":
                    if self.focus == 0:
                        self.focus = 1
                    else:
                        label, kind, arg = items[self.item_i]
                        if kind == "core":
                            self.run_core(arg)
                            continue
                        elif kind == "game":
                            rom, ext, syskey, rbf, (dl, ft, ix) = arg
                            LOG("Spielstart: %s (%s)" % (label, syskey))
                            mgl = write_mgl(rbf, rom, dl, ft, ix)
                            self.run_core(mgl)
                            continue
                        elif kind == "script":
                            self.run_script(arg)
                            continue
                        elif kind == "osd":
                            self.open_osd()
                            continue
                        elif kind == "redraw":
                            self.fb.refresh_geometry()
                        elif kind == "rescan":
                            self.draw("Lese Spieleliste neu ein ...")
                            self.build_categories(force_rescan=True)
                            self.cat_i = self.item_i = 0
                            self.scroll = self.cat_scroll = 0
                        elif kind == "crtmenu":
                            self.draw("Schalte Menue-Video um, Neustart ...")
                            if toggle_crt_menu() is not None:
                                os.system("sync; reboot")
                                return
                        elif kind == "reboot":
                            os.system("reboot")
                            return
                        elif kind == "quit":
                            break
                self.draw()
        finally:
            self.set_cursor_blink(True)
            self.fb.clear((0, 0, 0))
            self.fb.flip()
            self.fb.close()
            # zurueck ins normale MiSTer-Menue
            LOG("Exit: gebe Eingaben frei, injiziere F12")
            self.inp.grab(False)
            time.sleep(0.2)
            try:
                self.inp.inject(KEY_F12)
            except OSError as e:
                LOG("Exit-Injection fehlgeschlagen: %s" % e)
            self.inp.close()
            LOG("Exit: fertig")

if __name__ == "__main__":
    LOG("==== Frontend-Start ====")
    try:
        Frontend().run()
    except Exception:
        LOG("CRASH:\n" + traceback.format_exc())
        raise
