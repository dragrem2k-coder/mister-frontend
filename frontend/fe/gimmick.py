#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Das Gimmick unter System -> Wartung: Invade-a-Load auf dem C64-Core
(Build 329).

NUTZERWUNSCH: "kann man dieses spiel im frontend starten? sollte als
gimmick unter system wartung sein".

Invade-a-Load ist der Lader von 1987, in dem man Space Invaders spielt,
waehrend das eigentliche Spiel von der Kassette laedt (Programm Richard
Aplin, Musik Rob Hubbard). Hier: als eigenstaendiges Programm auf dem
C64-Core von MiSTer.

DAS SPIEL LIEGT NICHT IM FRONTEND. Es ist ein fremdes Programm, und das
Frontend wird oeffentlich verteilt - also wird es nicht mitgeliefert,
sondern dort gesucht, wo der Nutzer es selbst hinlegt (SUCHORDNER). Ohne
Datei oder ohne C64-Core steht der Menuepunkt gar nicht da: ein
Gimmick, das nur meldet, dass es nicht geht, ist keins.

T64 WIRD ZU PRG. Eine .T64 ist ein Archiv von Programmen im Format einer
Kassette. Der C64-Core laedt PRG-Dateien ueber den Dateiweg F1 (MGL:
type="f", index="1", so in der MiSTer-Community belegt) und startet sie,
wenn im Core "Reset & Run PRG" eingeschaltet ist. Das erste Programm der
T64 wird deshalb einmal herausgeschrieben - in den eigenen Ordner des
Frontends (GIMMICK_ORDNER), nie neben die Quelle.
"""
import glob
import os
import struct

from fe.log import LOG

GIMMICK_ORDNER = "/media/fat/frontend/gimmick"
SUCHORDNER = [GIMMICK_ORDNER, "/media/fat/games/C64"] + \
    ["/media/usb%d/games/C64" % i for i in range(6)]
COMPUTER_ORDNER = "/media/fat/_Computer"
C64_RBF = "_Computer/C64"
NAMEN = ("invade-a-load", "invade_a_load", "invadeaload", "invade a load")
ENDUNGEN = (".t64", ".prg")


def _passt(dateiname):
    klein = dateiname.lower()
    return klein.endswith(ENDUNGEN) and klein.startswith(NAMEN)


def finden(ordner=None):
    """Der Pfad zu Invade-a-Load (.T64 oder .PRG) oder None. Gesucht
    wird nur in den SUCHORDNERn, nicht rekursiv - das laeuft beim Bauen
    des Menues."""
    for o in (ordner or SUCHORDNER):
        try:
            namen = sorted(os.listdir(o))
        except OSError:
            continue
        for n in namen:
            if _passt(n):
                return os.path.join(o, n)
    return None


def c64_core_da(ordner=None):
    """Liegt ein C64-Core auf der Karte (C64.rbf oder C64_<Datum>.rbf)?"""
    o = ordner or COMPUTER_ORDNER
    try:
        return bool(glob.glob(os.path.join(o, "C64.rbf"))
                    or glob.glob(os.path.join(o, "C64_*.rbf")))
    except OSError:
        return False


def t64_erstes_programm(daten):
    """Das erste Programm einer T64 als PRG-Bytes (Ladeadresse + Inhalt)
    oder None.

    Aufbau: 64 Byte Kopf ("C64..." am Anfang, bei 0x22 die Zahl der
    Plaetze), ab 0x40 je Platz 32 Byte: Typ, C64-Dateityp, Start- und
    Endadresse, Versatz in der Datei. BEKANNTER FEHLER vieler T64: die
    Endadresse ist falsch (oft 0xC3C6) - die Laenge wird deshalb auch
    aus dem Abstand zum naechsten Programm bzw. zum Dateiende bestimmt
    und das Kleinere genommen."""
    if not daten or len(daten) < 0x60 or not daten[:3] == b"C64":
        return None
    try:
        plaetze = struct.unpack("<H", daten[0x22:0x24])[0]
    except struct.error:
        return None
    eintraege = []
    for i in range(max(0, min(plaetze, 1000))):
        p = 0x40 + 32 * i
        if p + 32 > len(daten):
            break
        typ, _ctyp, start, ende, _r, versatz = struct.unpack(
            "<BBHHHI", daten[p:p + 12])
        if typ == 0 or versatz <= 0 or versatz >= len(daten):
            continue
        eintraege.append((versatz, start, ende))
    if not eintraege:
        return None
    eintraege.sort()
    versatz, start, ende = eintraege[0]
    bis_naechster = (eintraege[1][0] if len(eintraege) > 1
                     else len(daten)) - versatz
    laenge = ende - start
    if laenge <= 0 or laenge > bis_naechster:
        laenge = bis_naechster
    if laenge <= 0:
        return None
    return struct.pack("<H", start) + daten[versatz:versatz + laenge]


def prg_bereitstellen(quelle, ziel_ordner=None):
    """Den Pfad einer startbaren PRG zur gefundenen Datei: eine .PRG
    selbst, aus einer .T64 das erste Programm (einmal herausgeschrieben,
    neu nur, wenn sich die Quelle geaendert hat). None, wenn es nicht
    geht. Geschrieben wird nur in ziel_ordner (Vorgabe GIMMICK_ORDNER),
    ueber eine .tmp-Datei."""
    if not quelle:
        return None
    if quelle.lower().endswith(".prg"):
        return quelle
    ziel_ordner = ziel_ordner or GIMMICK_ORDNER
    ziel = os.path.join(ziel_ordner, os.path.splitext(
        os.path.basename(quelle))[0] + ".prg")
    try:
        if (os.path.exists(ziel)
                and os.path.getmtime(ziel) >= os.path.getmtime(quelle)):
            return ziel
        with open(quelle, "rb") as f:
            prg = t64_erstes_programm(f.read())
        if not prg:
            LOG("Gimmick: %s ist keine lesbare T64" % quelle)
            return None
        os.makedirs(ziel_ordner, exist_ok=True)
        tmp = ziel + ".tmp"
        with open(tmp, "wb") as f:
            f.write(prg)
        os.replace(tmp, ziel)
        LOG("Gimmick: %s -> %s (%d Bytes)" % (quelle, ziel, len(prg)))
        return ziel
    except OSError as e:
        LOG("Gimmick: Bereitstellen fehlgeschlagen: %s" % e)
        return None


def verfuegbar():
    """Der Menuepunkt steht nur da, wenn Datei UND Core da sind."""
    return finden() is not None and c64_core_da()
