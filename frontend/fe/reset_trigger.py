#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reset im laufenden Core ueber F5 - Nutzerwunsch, gilt fuer ALLE Cores
gleichermassen (Konsolen- wie RA-Cores), ohne den Core selbst neu zu
laden (wichtig fuer RA: kein Core-Wechsel -> kein Risiko,
versehentlich auf die Nicht-RA-Variante zu wechseln).

GEAENDERT (Build 75, Nutzerwunsch "F5-Reset-Funktion haette ich gerne
auf sofortigen Tastendruck"): frueher musste F5 0,6 Sekunden gehalten
werden (urspruenglich war es sogar Tab). Jetzt loest der erste
erkannte Tastendruck sofort aus - siehe RESET_HOLD in fe/input.py fuer
die Umschaltung und das dort ausdruecklich benannte Risiko.

HINTERGRUND: MiSTers eigener "User"-Knopf (gelber Knopf am Board/
IO-Board) loest per Firmware einen Reset INNERHALB des laufenden
Cores aus - dieselbe Funktion ist auch ueber die Tastenkombination
Strg+Alt+AltGr (links/links/rechts) erreichbar. Beides sind fuer
MiSTer nur zwei verschiedene HARDWARE-Ausloeser fuer denselben
internen Vorgang - es gibt keinen dokumentierten einfachen Software-
Befehl dafuer (anders als z.B. "load_core" ueber /dev/MiSTer_cmd).

ANSATZ: ueber ein virtuelles Tastatur-Geraet (/dev/uinput, der
Linux-Standardweg fuer synthetische Eingaben, die fuer ALLE Prozesse
im System wie eine echte Tastatur aussehen) wird genau diese
Tastenkombination nachgebildet.

WICHTIG - EHRLICH DOKUMENTIERTER STATUS: dies ist NEUES, ungetestetes
Terrain fuer dieses Projekt. Der Code selbst ist nach dem Linux-
Standardmuster fuer uinput aufgebaut und in der Sandbox auf
Korrektheit (Geraet wird erzeugt, Ereignisse werden im erwarteten
Format geschrieben) geprueft - OB MiSTers eigene Firmware synthetische
Ereignisse von einem uinput-Geraet tatsaechlich genauso behandelt wie
eine echte Tastatur, kann nur ein Test auf echter Hardware zeigen.
Schlaegt es fehl, passiert nichts Schlimmes (kein Absturz, keine
Seiteneffekte) - der Reset loest dann einfach nicht aus.
"""
import os, struct, fcntl, time
from fe.log import LOG

# uinput-ioctl-Konstanten (aus <linux/uinput.h> - dort mit dem
# Standard-_IOW/_IOR-Makro definiert, hier als bereits fertig
# berechnete Werte fuer denselben ARM-Kernel wie der Rest des
# Projekts (siehe EVENT_FMT in fe/input.py fuer dieselbe Architektur-
# Annahme: 32-Bit long, wie bei den uebrigen ioctl-Aufrufen im
# Projekt, z.B. _absinfo() in fe/input.py)
UI_SET_EVBIT  = 0x40045564
UI_SET_KEYBIT = 0x40045565
UI_DEV_CREATE  = 0x5501
UI_DEV_DESTROY = 0x5502

EV_KEY, EV_SYN = 1, 0
SYN_REPORT = 0

# HID-/evdev-Keycodes fuer die "User-Knopf"-Ersatzkombination
# (Strg+Alt+AltGr links/links/rechts - siehe MiSTer-eigene
# Dokumentation, "presses the USER button which usually is reset in
# emulated system").
KEY_LEFTCTRL, KEY_LEFTALT, KEY_RIGHTALT = 29, 56, 100

# Dasselbe Ereignis-Format wie der Rest des Projekts (fe/input.py,
# EVENT_FMT) - "llHHi": zwei 32-Bit-Zeitstempel (Sekunden/Mikrosekunden,
# hier bewusst auf 0 gesetzt, der Kernel setzt sie beim Schreiben
# ohnehin selbst neu), zwei unsigned short (Typ, Code), ein int (Wert).
_EVENT_FMT = "llHHi"

# NEU (Build 75, Nutzerwunsch "F5-Reset auf sofortigen Tastendruck"):
# das einmal angelegte virtuelle Geraet bleibt offen.
#
# Vorher wurde bei JEDEM Auslesen ein neues Geraet angelegt und danach
# 0,2 Sekunden gewartet, bis der Kernel es anderen Prozessen (inklusive
# MiSTers eigenem) bekannt gemacht hat. Diese Wartezeit ist echt und
# noetig - aber nur BEIM ANLEGEN. Sie bei jedem Reset erneut zu zahlen
# hiess: selbst bei sofortigem Tastendruck vergingen 0,2 s, bevor die
# Tastenkombination ueberhaupt losgeschickt wurde, plus 0,1 s
# Tastendruckdauer. Genau das, was "sofort" verhindert.
#
# Jetzt wird das Geraet beim ersten Reset angelegt und bleibt bestehen;
# jeder weitere Reset kostet nur noch die 0,1 s Tastendruckdauer, die
# der Empfaenger braucht, um den Druck ueberhaupt zu sehen.
_geraet_fd = None


def _geraet_holen():
    """Das virtuelle Tastatur-Geraet - beim ersten Aufruf anlegen,
    danach wiederverwenden. Rueckgabe: Dateideskriptor oder None."""
    global _geraet_fd
    if _geraet_fd is not None:
        return _geraet_fd
    try:
        fd = os.open("/dev/uinput", os.O_WRONLY | os.O_NONBLOCK)
    except OSError as e:
        LOG("send_reset_combo: /dev/uinput nicht verfuegbar: %s" % e)
        return None
    try:
        fcntl.ioctl(fd, UI_SET_EVBIT, EV_KEY)
        for k in (KEY_LEFTCTRL, KEY_LEFTALT, KEY_RIGHTALT):
            fcntl.ioctl(fd, UI_SET_KEYBIT, k)
        name = b"dragend-reset-trigger"
        uidev = (name + b"\x00" * (80 - len(name))
                 + struct.pack("HHHH", 0, 1, 1, 1)
                 + struct.pack("i", 0)
                 + b"\x00" * (4 * 64 * 4))
        os.write(fd, uidev)
        fcntl.ioctl(fd, UI_DEV_CREATE)
        # Diese Pause bleibt - sie ist beim ANLEGEN wirklich noetig
        # (der Kernel muss das Geraet erst bekannt machen). Sie faellt
        # jetzt nur noch EINMAL an, nicht bei jedem Reset.
        time.sleep(0.2)
    except Exception as e:                          # noqa: BLE001
        LOG("send_reset_combo: Geraet anlegen fehlgeschlagen (%s): %s"
            % (type(e).__name__, e))
        try:
            os.close(fd)
        except OSError:
            pass
        return None
    _geraet_fd = fd
    LOG("send_reset_combo: virtuelles Tastatur-Geraet angelegt "
        "(bleibt fuer weitere Resets bestehen)")
    return fd


def send_reset_combo():
    """Simuliert Strg+Alt+AltGr ueber ein virtuelles Tastatur-Geraet.
    Liefert True, wenn die Ereignisse geschrieben wurden (KEINE
    Garantie, dass MiSTer das auch tatsaechlich als Tastendruck erkennt -
    nur, dass unser Teil fehlerfrei durchgelaufen ist). False bei jedem
    Fehler (z.B. /dev/uinput nicht vorhanden - dann ist das
    uinput-Kernel-Modul nicht geladen)."""
    LOG("send_reset_combo: aufgerufen")
    fd = _geraet_holen()
    if fd is None:
        return False
    try:
        def emit(etype, code, value):
            os.write(fd, struct.pack(_EVENT_FMT, 0, 0, etype, code, value))

        for k in (KEY_LEFTCTRL, KEY_LEFTALT, KEY_RIGHTALT):
            emit(EV_KEY, k, 1)
        emit(EV_SYN, SYN_REPORT, 0)
        time.sleep(0.1)
        for k in (KEY_RIGHTALT, KEY_LEFTALT, KEY_LEFTCTRL):
            emit(EV_KEY, k, 0)
        emit(EV_SYN, SYN_REPORT, 0)
        LOG("send_reset_combo: Strg+Alt+AltGr ueber virtuelles Geraet gesendet")
        return True
    except Exception as e:                          # noqa: BLE001
        LOG("send_reset_combo: Fehler (%s): %s" % (type(e).__name__, e))
        # Das Geraet koennte kaputt sein (z.B. weil das uinput-Modul
        # entladen wurde) - beim naechsten Mal neu anlegen lassen.
        _geraet_schliessen()
        return False


def _geraet_schliessen():
    global _geraet_fd
    if _geraet_fd is None:
        return
    try:
        fcntl.ioctl(_geraet_fd, UI_DEV_DESTROY)
    except OSError:
        pass
    try:
        os.close(_geraet_fd)
    except OSError:
        pass
    _geraet_fd = None
