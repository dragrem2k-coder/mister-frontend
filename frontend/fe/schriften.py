# -*- coding: utf-8 -*-
"""MiSTers eigene OSD-Schriften, in Ordnern durchblaettert (Build 228).

ZURUF DES NUTZERS: "das was wir mit masken gemacht haben sollte auch mit
denn fonts also der schrift passieren".

Er hat recht. Build 223 hat die Schriften eingebaut, aber nur als
Durchschalten mit links/rechts im Systemmenue. Das geht bei drei
Dateien; MiSTers Schriftsammlung hat ueber hundert, und wer sie per
update_all holt, bekommt sie in Unterordnern. Links/rechts waere dort
keine Auswahl, sondern eine Strafe - dasselbe Argument wie bei den
Masken.

GELESEN, NICHT MITGELIEFERT - dieselbe Haltung wie bei Masken und bei
der fremden Artwork-Datenbank: die Dateien liegen in /media/fat/font auf
der Karte des Nutzers. Dieses Paket enthaelt keine einzige .pf-Datei.

WAS DIESES MODUL NICHT TUT: in die MiSTer.ini schreiben. Welche Schrift
MiSTers eigenes OSD benutzt, steht dort unter font= und geht uns nichts
an - wir LESEN den Wert, damit "wie im OSD" waehlbar ist. Geschrieben
wird in die MiSTer.ini an genau einer Stelle (dem [Menu]-Block fuer den
Roehrenmodus), und das ist eine bewusste Ausnahme mit Sicherungskopie.
"""
import os

import fe.dateibaum as BAUM

SCHRIFTEN_DIR = "/media/fat/font"
ENDUNG = ".pf"


def schrift_eintraege(unterordner="", wurzel=None):
    """EINE Ebene des Schriftbaums - siehe fe/dateibaum.py."""
    return BAUM.eintraege(wurzel or SCHRIFTEN_DIR, unterordner, ENDUNG)


def oberordner(unterordner):
    """Eine Ebene hoeher - "" ist die Wurzel und das Ende des Weges."""
    return BAUM.oberordner(unterordner)


def ebene(ordner="", texte=None, wurzel=None, osd_vorhanden=False):
    """Die sichtbare Liste EINER Ebene - fertig zum Hinmalen.

    texte: {"zurueck": .., "eigen": .., "osd": ..} - die uebersetzten
    Beschriftungen. Uebersetzen tut dieses Modul nicht.

    osd_vorhanden: steht in der MiSTer.ini ueberhaupt eine Schrift? Wenn
    nicht, faellt die Zeile weg - ein Eintrag, der beim Druecken nichts
    tut, ist schlimmer als keiner.

    Rueckgabe: Liste von (art, anzeige, rel). Zu den Arten aus
    fe/dateibaum.py ("hoch", "ordner", "datei") kommen hier zwei:

        "eigen" - die mitgelieferte Schrift des Frontends (Vorgabe)
        "osd"   - die, die in der MiSTer.ini unter font= steht
    """
    texte = texte or {}
    kopf = [("eigen", texte.get("eigen", "eigene"), "")]
    if osd_vorhanden:
        kopf.append(("osd", texte.get("osd", "wie im OSD"), ""))
    return BAUM.zeilen(wurzel or SCHRIFTEN_DIR, ordner, ENDUNG,
                       texte, kopf)
