# -*- coding: utf-8 -*-
"""Einen Ordner Ebene fuer Ebene durchblaettern (Build 228).

WARUM ES DIESES MODUL GIBT. Build 227 hat die Lochmasken in Ordnern
gezeigt, statt 1207 Dateien in eine Liste zu kippen. Der Nutzer hat
daraufhin gesagt: "das was wir mit masken gemacht haben sollte auch mit
denn fonts also der schrift passieren". Er hat recht - und damit gibt es
zwei Stellen, die dasselbe tun.

Zwei Stellen mit derselben Aufgabe laufen auseinander. Nicht sofort,
aber beim dritten Mal, wenn jemand den einen Baum um eine Kleinigkeit
erweitert und den anderen vergisst. Also steht das Blaettern EINMAL hier
und wird zweimal benutzt: fe/masken.py fuer /media/fat/Shadow_Masks,
fe/schriften.py fuer /media/fat/font.

WAS HIER NICHT HINEINGEHOERT: alles, was die eine Sammlung von der
anderen unterscheidet. Masken haben MiSTers Presets als Empfehlungen
obendrueber, Schriften haben die eigene Schrift des Frontends und die
aus der MiSTer.ini. Solche Zeilen gibt der Aufrufer als `kopf` mit -
dieses Modul kennt nur Ordner und Dateien.

ALLES, WAS SCHIEFGEHEN KANN, ENDET IN EINER LEEREN LISTE. Ein Ordner,
den es nicht gibt, ein Lesefehler, ein kaputter Name - nichts davon darf
ein Frontend aufhalten, das eigentlich Spiele starten soll.
"""
import os

# Eine Ebene, die es als Ordner nicht gibt (MiSTers Presets zum
# Beispiel). Der Name faengt mit einem Zeichen an, das in keinem
# Dateinamen vorkommen kann - eine Verwechslung mit einem echten Ordner
# ist damit ausgeschlossen.
VIRTUELL = "\x00"


def eintraege(wurzel, unterordner="", endung=".txt"):
    """EINE Ebene: Ordner und Dateien getrennt.

    Rueckgabe: Liste von (ist_ordner, anzeigename, relativer Pfad,
    anzahl). anzahl ist bei einem Ordner die Zahl der passenden Dateien
    DARIN, mitsamt seiner Unterordner - ohne sie waehlt man einen Ordner
    blind. Ordner stehen vorn, beides fuer sich sortiert.

    Ein Ordner OHNE eine einzige passende Datei wird weggelassen: er
    waere eine Sackgasse, und beide Sammlungen haben solche (Vorlagen,
    Lesetexte, Bilder)."""
    basis = os.path.join(wurzel, unterordner) if unterordner else wurzel
    ordner, dateien = [], []
    try:
        namen = os.listdir(basis)
    except OSError:
        return []
    for name in namen:
        voll = os.path.join(basis, name)
        rel = os.path.join(unterordner, name) if unterordner else name
        try:
            ist_ordner = os.path.isdir(voll)
        except OSError:
            continue
        if ist_ordner:
            n = zaehlen(voll, endung)
            if n:
                ordner.append((True, name, rel, n))
        elif name.lower().endswith(endung):
            dateien.append((False, os.path.splitext(name)[0], rel, 0))
    ordner.sort(key=lambda e: e[1].lower())
    dateien.sort(key=lambda e: e[1].lower())
    return ordner + dateien


def zaehlen(ordner, endung=".txt"):
    """Wieviele passende Dateien liegen darin, mitsamt Unterordnern?"""
    n = 0
    try:
        for _w, _u, dateien in os.walk(ordner):
            n += sum(1 for d in dateien if d.lower().endswith(endung))
    except OSError:
        return 0
    return n


def oberordner(unterordner):
    """Eine Ebene hoeher - "" ist die Wurzel und das Ende des Weges.

    Eine virtuelle Ebene fuehrt immer zur Wurzel zurueck: sie steht dort
    und nirgends sonst."""
    if not unterordner:
        return ""
    if unterordner.startswith(VIRTUELL):
        return ""
    return os.path.dirname(unterordner.rstrip(os.sep))


def zeilen(wurzel, ordner="", endung=".txt", texte=None, kopf=()):
    """Eine Ebene, fertig zum Hinmalen.

    texte: {"zurueck": ..} - die uebersetzte Beschriftung fuer den Weg
    nach oben. Uebersetzen tut dieses Modul nicht.

    kopf: Zeilen, die AUF DER WURZEL ganz oben stehen (und nur dort) -
    je (art, anzeige, rel). Hier haengt der Aufrufer an, was seine
    Sammlung von einem blossen Ordnerbaum unterscheidet.

    Rueckgabe: Liste von (art, anzeige, rel). art ist

        "hoch"   - eine Ebene hoeher (steht nur unterhalb der Wurzel)
        "ordner" - eine Ebene tiefer
        "datei"  - eine waehlbare Datei
        ...      - was der Aufrufer in `kopf` mitgegeben hat

    Gebaut wird die Liste beim WECHSEL der Ebene, nicht je Tastendruck:
    das Zaehlen laeuft ueber os.walk() und gehoert nicht an die
    Pfeiltasten."""
    texte = texte or {}
    if ordner:
        liste = [("hoch", ".. %s" % texte.get("zurueck", "zurueck"), "")]
    else:
        liste = list(kopf)
    for ist_ordner, name, rel, n in eintraege(wurzel, ordner, endung):
        if ist_ordner:
            liste.append(("ordner", "%s/   (%d)" % (name, n), rel))
        else:
            liste.append(("datei", name, rel))
    return liste
