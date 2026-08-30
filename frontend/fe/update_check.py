#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Update-Benachrichtigung: prueft die VERSION-Datei auf GitHub, haelt
den Ein/Aus-Zustand und den zuletzt gemeldeten Stand fest. Ausgelagert
aus frontend.py (Modularisierung, Git-Branch 'modular-refactor').

Das eigentliche Herunterladen/Installieren bleibt bewusst manuell
ueber Frontend_Install.sh - hier geht es NUR um die Benachrichtigung.

FRONTEND_VERSION liegt HIER als kanonische Quelle (nicht in
frontend.py oder fe/menu.py - beide importieren sie von hier), weil
dieses Modul in der Abhaengigkeitskette am weitesten unten steht
(importiert nur os/json/urllib/fe.log, wird selbst von fe/menu.py UND
frontend.py importiert - waere die Definition stattdessen in
fe/menu.py, haette fe/menu.py's Import von HIER (fuer
update_check_enabled/_version_newer) einen Zirkelbezug ausgeloest).

BUGFIX (beim v4.4-Bump gefunden): FRONTEND_VERSION war zuvor GLEICH
DREIMAL unabhaengig als Zeichenkette hinterlegt (hier, in frontend.py
UND in fe/menu.py) - dasselbe Drift-Risiko wie zuvor schon bei den
Scripts/-Kopien der Installationsskripte gefunden und behoben. Jetzt
genau eine Quelle, die beiden anderen Stellen importieren von hier
(direkt bzw. transitiv ueber fe/menu.py).
"""
import os, json, urllib.request
from fe.log import LOG

FRONTEND_VERSION = "4.4"

UPDATE_CHECK_URL = ("https://raw.githubusercontent.com/dragrem2k-coder/"
                    "mister-frontend/main/frontend/VERSION")
UPDATE_CHECK_STATE_FILE = "/media/fat/frontend/update_check_state.json"
UPDATE_CHECK_DISABLED_FLAG_FILE = "/media/fat/frontend/update_check_disabled"

# NEUES FEATURE (Nutzerwunsch: "ich bekomme keine Update-Benachrichtigung,
# wenn ich auf GitHub was aktualisiert habe" - Ursache geklaert: der
# obige Mechanismus vergleicht AUSSCHLIESSLICH die Versionsnummer, die
# sich bei laufenden Fixes innerhalb derselben Version (bewusst KEIN
# automatischer Bump, siehe FRONTEND_VERSION oben) gar nicht aendert.
# Nutzer moechte ausdruecklich bei v4.4 bleiben, aber trotzdem einen
# Hinweis sehen, wenn es neue Fixes gibt UND WAS sich geaendert hat).
# Komplett UNABHAENGIG von FRONTEND_VERSION/_version_newer() - eigene
# kleine JSON-Datei mit einer frei waehlbaren Kennung + Kurzbeschreibung,
# die bei jedem nennenswerten Fix-Batch aktualisiert wird (aehnliches
# Prinzip wie CHANGELOG.md, nur maschinenlesbar und bewusst SEHR kurz -
# fuer eine Popup-Zeile, kein vollstaendiger Changelog-Abruf).
# WICHTIG fuer den "summary"-Eintrag in LATEST_BUILD.json: dieser Text
# wird dem Nutzer UNVERAENDERT im Update-Dialog angezeigt (siehe
# _start_update_install_dialog() in frontend.py) - und der ist bewusst
# klein und auf drei Zeilen begrenzt. Es passen daher nur rund
#     96 Zeichen auf CRT (320x240)   bzw.   216 Zeichen auf HDMI
# hinein; alles darueber wird schlicht abgeschnitten. Genau das ist
# einmal passiert (Nutzer-Foto: der Text brach mitten im Satz bei
# "Ursache" ab, weil die Zusammenfassung ~380 Zeichen lang war). Der
# "summary" ist also eine KURZE Nutzer-Meldung in einem Satz - die
# ausfuehrliche Beschreibung gehoert in die CHANGELOG.md, nicht hierhin.
BUILD_CHECK_URL = ("https://raw.githubusercontent.com/dragrem2k-coder/"
                   "mister-frontend/main/frontend/LATEST_BUILD.json")

def update_check_enabled():
    return not os.path.exists(UPDATE_CHECK_DISABLED_FLAG_FILE)

def toggle_update_check():
    if os.path.exists(UPDATE_CHECK_DISABLED_FLAG_FILE):
        try:
            os.remove(UPDATE_CHECK_DISABLED_FLAG_FILE)
        except OSError:
            pass
    else:
        try:
            dirname = os.path.dirname(UPDATE_CHECK_DISABLED_FLAG_FILE)
            if dirname:
                os.makedirs(dirname, exist_ok=True)
            open(UPDATE_CHECK_DISABLED_FLAG_FILE, "w").close()
        except OSError:
            pass

def load_update_state():
    try:
        with open(UPDATE_CHECK_STATE_FILE) as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}

def save_update_state(state):
    try:
        os.makedirs(os.path.dirname(UPDATE_CHECK_STATE_FILE), exist_ok=True)
        with open(UPDATE_CHECK_STATE_FILE, "w") as f:
            json.dump(state, f)
    except OSError:
        pass

def _parse_version(s):
    """"4.2" -> (4, 2), "4.10-test3" -> (4, 10) - nur die fuehrenden
    Zahlenteile zaehlen fuer den Vergleich, ein Zusatz wie "-test3"
    (siehe Versionierungsregeln oben) wird ignoriert."""
    parts = []
    for chunk in s.strip().split("."):
        num = ""
        for ch in chunk:
            if ch.isdigit():
                num += ch
            else:
                break
        if not num:
            break
        parts.append(int(num))
    return tuple(parts)

def _version_newer(remote, local):
    """True, wenn remote (String) eine tatsaechlich hoehere Version als
    local (String) ist - reiner Zahlenvergleich, siehe _parse_version()."""
    try:
        return _parse_version(remote) > _parse_version(local)
    except (ValueError, AttributeError):
        return False
def check_for_update(timeout=5.0):
    """Fragt die aktuell auf GitHub liegende VERSION-Datei ab (reiner
    Rohtext-Abruf, kein API-Rate-Limit). Gibt den Versions-String
    zurueck (z.B. "4.3") oder None bei jedem Fehler (kein Internet,
    DNS-Problem, Zeitueberschreitung, Repo umbenannt usw.) - ein
    fehlgeschlagener Update-Check darf niemals irgendetwas anderes
    stoeren, deshalb ein einzelnes breites except.

    NACHGEBESSERT (Nutzer-Rueckmeldung: "es kommt keine Info, dass ein
    Update verfuegbar ist" - ohne jede Log-Ausgabe war das bisher gar
    nicht diagnostizierbar: lief der Check ueberhaupt, schlug er fehl,
    oder gibt es schlicht (noch) keine neuere Version auf GitHub?)."""
    try:
        with urllib.request.urlopen(UPDATE_CHECK_URL, timeout=timeout) as resp:
            text = resp.read(200).decode("utf-8", "ignore").strip()
        LOG("Update-Check: GitHub meldet Version %r (lokal: %r)" % (text, FRONTEND_VERSION))
        return text if text else None
    except Exception as e:
        LOG("Update-Check fehlgeschlagen: %s" % e)
        return None


def check_for_build_update(timeout=5.0):
    """Wie check_for_update(), aber komplett unabhaengig von der
    Versionsnummer - fragt stattdessen LATEST_BUILD.json ab (siehe
    BUILD_CHECK_URL oben). Gibt (build_id, summary) zurueck oder None
    bei jedem Fehler ODER wenn die Antwort nicht wie erwartet aussieht
    (fehlende Felder, kaputtes JSON) - dieselbe "niemals etwas anderes
    stoeren"-Regel wie beim Versions-Check."""
    try:
        with urllib.request.urlopen(BUILD_CHECK_URL, timeout=timeout) as resp:
            raw = resp.read(2000).decode("utf-8", "ignore")
        data = json.loads(raw)
        build_id = data.get("build_id")
        summary = data.get("summary")
        if not build_id or not summary:
            LOG("Build-Check: Antwort unvollstaendig: %r" % data)
            return None
        LOG("Build-Check: GitHub meldet Build %r" % build_id)
        return (build_id, summary)
    except Exception as e:
        LOG("Build-Check fehlgeschlagen: %s" % e)
        return None
