#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Zaparoo (NFC-Tags) - erkennen, starten, und den ZapScript-Befehl
nennen (Build 251).

WAS ZAPAROO IST. Ein eigenes Projekt (vormals TapTo), das am MiSTer
NFC-Tags liest und das Spiel startet, das auf dem Tag steht. Ein
Kaertchen auf den Leser legen, das Spiel laeuft. Es laeuft als eigener
Dienst, hat eine eigene Konfiguration und eine eigene App.

WAS DIESES MODUL TUT - UND VOR ALLEM, WAS NICHT

Es tut drei Dinge:

  * nachsehen, ob Zaparoo installiert ist und ob der Dienst
    eingetragen wurde,
  * das vorhandene Skript starten (ueber run_script(), denselben Weg
    wie update_all - es wird KEIN eigener Startweg gebaut),
  * den ZapScript-Befehl fuer ein Spiel nennen, damit man ihn mit der
    Zaparoo-App auf einen Tag schreiben kann.

Es schreibt NICHTS in /media/fat/zaparoo, und das ist die wichtigste
Entscheidung dieser Datei. Dort liegen die Konfiguration und die
Zuordnungen eines fremden Programms. Dieselbe Haltung wie bei
/media/fat/docs (die fremde Artwork-Datenbank, in die wir nie
schreiben) und bei MiSTers Favoritendatei (die wir nur lesen).

Drei Gruende, und der dritte allein wuerde reichen:

  1. Es ist nicht unser Verzeichnis. Wer dort schreibt, uebernimmt
     Verantwortung fuer das Format eines Programms, das sich
     weiterentwickelt, ohne uns zu fragen.
  2. Zaparoo muss nach einer Aenderung an den Dateien neu gestartet
     werden, damit sie gilt. Wir koennten also etwas hinschreiben, das
     erst nach einem Neustart wirkt - und dem Nutzer bliebe unklar,
     ob es ueberhaupt angekommen ist.
  3. Tags beschreibt man mit der Zaparoo-App am Telefon. Dort steht
     man ohnehin, wenn man einen Tag anlegt. Was dort fehlt, ist nur
     die eine Zeile, die man eintippen muss - und genau die liefern
     wir.

GELESEN WIRD AUCH NUR, WAS SICH NICHT AENDERN KANN: ob Dateien da
sind, und ob in /media/fat/linux/user-startup.sh das Wort "zaparoo"
steht. Das Protokoll von Zaparoo (/tmp/zaparoo/core.log) wird NICHT
ausgewertet - dieselbe Absage wie bei update_all in
fe/mister_system.py: ein Logleser haengt am Zeilenformat eines fremden
Programms.

Quellen fuer die Pfade und die Befehlsform: zaparoo.org/docs
(Plattform MiSTer, ZapScript "launch").
"""
import io
import os

SKRIPT_KANDIDATEN = ("/media/fat/Scripts/zaparoo.sh",
                     "/media/fat/Scripts/tapto.sh")
DATEN = "/media/fat/zaparoo"
KONFIG = "/media/fat/zaparoo/config.toml"
MAPPINGS = "/media/fat/zaparoo/mappings"
STARTUP = "/media/fat/linux/user-startup.sh"
# Zaparoo legt diesen Ordner an, wenn der Dienst laeuft (das Protokoll
# darin wird NICHT gelesen - nur, dass es den Ordner gibt).
LAUFSPUR = "/tmp/zaparoo"

# Der aeltere Name. Zaparoo hiess vorher TapTo, und wer von damals
# kommt, hat das Skript noch unter dem alten Namen liegen.
STARTUP_MARKEN = ("zaparoo", "tapto")


def skript_pfad():
    """Der Pfad des Zaparoo-Skripts, oder None.

    Der erste vorhandene zaehlt - genau wie bei update_all_pfad() in
    fe/mister_system.py."""
    for p in SKRIPT_KANDIDATEN:
        try:
            if os.path.isfile(p):
                return p
        except OSError:
            continue
    return None


def installiert():
    return skript_pfad() is not None


def dienst_eingetragen():
    """Steht Zaparoo in /media/fat/linux/user-startup.sh?

    Nur das WORT wird gesucht, nicht die Zeile ausgewertet: wie der
    Dienst genau eingetragen wird, entscheidet Zaparoo, und das darf
    sich aendern. Uns genuegt "da steht etwas davon" - alles andere
    waere eine Annahme ueber ein fremdes Format."""
    try:
        with io.open(STARTUP, "r", encoding="utf-8",
                     errors="replace") as fh:
            text = fh.read(65536).lower()
    except OSError:
        return False
    for zeile in text.split("\n"):
        s = zeile.strip()
        if not s or s.startswith("#"):
            continue
        if any(m in s for m in STARTUP_MARKEN):
            return True
    return False


def laeuft():
    """Laeuft der Dienst gerade?

    Erkannt am Ordner, den Zaparoo im Betrieb anlegt. Das ist ein
    Hinweis und kein Beweis - der Ordner kann aus einem frueheren Lauf
    stehengeblieben sein -, deshalb heisst er in der Anzeige auch nur
    "laeuft" und nicht "ist bereit"."""
    try:
        return os.path.isdir(LAUFSPUR)
    except OSError:
        return False


def tags_gezaehlt():
    """Wie viele Zuordnungsdateien liegen da?

    Gezaehlt werden .toml-Dateien unter mappings/, auch in
    Unterordnern (Zaparoo erlaubt sie). GELESEN WIRD KEINE EINZIGE -
    es geht nur um "ist dort etwas eingerichtet". Ueber die API
    angelegte Zuordnungen liegen in Zaparoos eigener Datenbank und
    tauchen hier nicht auf; die Zahl ist also eine Untergrenze, und so
    wird sie auch beschriftet."""
    n = 0
    try:
        for ordner, _unter, namen in os.walk(MAPPINGS):
            del ordner
            for name in namen:
                if name.lower().endswith(".toml"):
                    n += 1
    except OSError:
        return 0
    return n


def zapscript_fuer(pfad):
    """Der ZapScript-Befehl, der dieses Spiel startet.

    Form: "**launch:<Pfad>" - der eine ZapScript-Befehl, der einen
    Dateipfad direkt nimmt. Ein nackter Pfad ohne Befehl wuerde auch
    gehen ("Auto Launch"), aber mit dem Praefix ist es eindeutig, und
    eindeutig ist besser, wenn man es abtippt.

    Der Pfad wird NICHT umgeschrieben und nicht geprueft: er ist genau
    der, mit dem auch unser eigener Startweg das Spiel startet. Haengt
    das Spiel in einem ZIP-Archiv, steht das Archiv samt Eintrag
    darin - und Zaparoo kommt damit genauso zurecht wie MiSTer selbst,
    denn es ist derselbe Pfad, der in einer .mgl stehen wuerde."""
    p = str(pfad or "").strip()
    if not p:
        return ""
    return "**launch:" + p


def spiel_pfad(arg):
    """Der Dateipfad aus einem Kategorie-Eintrag (label, kind, arg).

    Unsere Einträge tragen in arg[0] den Pfad - dasselbe Feld, das
    run_core() benutzt. Alles andere (Endung, Systemschluessel) ist
    fuer den Tag ohne Bedeutung."""
    try:
        if isinstance(arg, (list, tuple)) and arg:
            return str(arg[0] or "")
    except Exception:                                    # noqa: BLE001
        pass
    return ""


def stand():
    """Alles, was die Anzeige braucht, in einem Dict.

    An einer Stelle geholt, damit der Menuepunkt und der Bildschirm
    nicht zweimal dasselbe nachsehen und dabei auseinanderlaufen."""
    p = skript_pfad()
    return {"pfad": p,
            "installiert": p is not None,
            "dienst": dienst_eingetragen(),
            "laeuft": laeuft(),
            "tags": tags_gezaehlt()}
