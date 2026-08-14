#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Update-Benachrichtigung: prueft die VERSION-Datei auf GitHub, haelt
den Ein/Aus-Zustand und den zuletzt gemeldeten Stand fest. Ausgelagert
aus frontend.py (Modularisierung, Git-Branch 'modular-refactor').

Das eigentliche Herunterladen/Installieren bleibt bewusst manuell
ueber install_frontend.sh - hier geht es NUR um die Benachrichtigung.

FRONTEND_VERSION hier bewusst noch einmal definiert (nicht importiert)
- frontend.py braucht denselben Wert AUCH noch an mehreren Stellen
  (z.B. fuer die eigene Update-Pruefung in der Frontend-Klasse), ein
  Ruecksfall-Import haette einen Zirkelbezug ausgeloest (frontend.py
  laeuft als Hauptskript, nicht als benanntes, importierbares Modul).
  Da es ein fester Versions-String ist, ist die zweite Definition
  unproblematisch.
"""
import os, json, urllib.request
from fe.log import LOG

FRONTEND_VERSION = "4.3"

UPDATE_CHECK_URL = ("https://raw.githubusercontent.com/dragrem2k-coder/"
                    "mister-frontend/main/frontend/VERSION")
UPDATE_CHECK_STATE_FILE = "/media/fat/frontend/update_check_state.json"
UPDATE_CHECK_DISABLED_FLAG_FILE = "/media/fat/frontend/update_check_disabled"

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

