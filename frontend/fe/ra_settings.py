#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RetroAchievements-Einstellungen der MiSTer-Hauptanwendung lesen und
schreiben (Build 95).

NUTZERWUNSCH: "Sute hat eine neue Main MiSTer gebaut, die hat nun
RA Settings - koennen wir das irgendwie mit ins Frontend einbauen?" und,
nach dem naechsten Update mit den Offsets: "Das haette ich auch gerne
bei uns im Frontend, und zwar dann einstellbar unter System und dann
RetroAchievements."

==========================================================================
ACHTUNG - ZWEI VERSCHIEDENE DATEIEN MIT DEMSELBEN NAMEN
==========================================================================

    /media/fat/frontend/retroachievements.cfg   <- UNSERE (fe/retroachievements.py)
        zwei Zeilen: RA-Benutzername, Web-API-Schluessel.
        Nur fuer die Fortschrittsanzeige im Frontend (Web-API).

    /media/fat/retroachievements.cfg            <- DIE VON MiSTer (dieses Modul)
        schluessel=wert, plus [Core]-Abschnitte.
        Benutzername + PASSWORT (nicht API-Schluessel) und alle
        Einstellungen der eigentlichen Achievement-Engine.

Verschiedene Ordner, verschiedenes Format, verschiedene Zugangsdaten.
Sie duerfen NIE verwechselt werden - deshalb steht dieses Modul bewusst
getrennt von fe/retroachievements.py und importiert nichts daraus.

==========================================================================
DAS DATEIFORMAT
==========================================================================

Aus der MiSTer-Binary (Build "SelAddr v29-b1") herausgelesen:

    RA: ra_save: %s=%s              <- globaler Wert
    RA: ra_save_sec: [%s] %s=%s     <- Wert in einem Core-Abschnitt
    %s.tmp / rename                 <- geschrieben wird ueber eine
                                       temporaere Datei und umbenannt

Also ganz normaler INI-Stil:

    username=Dragrem
    password=...
    show_progress_popups=1
    popup_position=left

    [SNES]
    popup_h_offset=-12
    popup_v_offset=2

Laut MiSTers eigener Log-Zeile werden PRO CORE gelesen:
popup_position, popup_h_offset, popup_v_offset ("RA: Popup settings for
core '%s': ..."). Genau diese drei bietet das Frontend deshalb auch pro
System an - die uebrigen Schalter bleiben global. Bewusst nicht mehr:
was MiSTer nachweislich pro Core auswertet, steht in seinem Log; alles
darueber hinaus waere geraten.

==========================================================================
WARUM EIN ZEILENWEISER EDITOR STATT configparser
==========================================================================

Die Datei gehoert NICHT uns. Darin stehen Zugangsdaten, moeglicherweise
Kommentare, und in einer kuenftigen MiSTer-Version stehen dort
Schluessel, die es heute noch nicht gibt. Ein "einlesen, Objekt bauen,
neu herausschreiben" wuerde all das stillschweigend wegwerfen oder
umformatieren.

Dieses Modul aendert deshalb immer nur GENAU DIE EINE ZEILE, die
gemeint ist, und laesst jede andere Zeile Byte fuer Byte unberuehrt -
Kommentare, Leerzeilen, Reihenfolge, Schreibweise, sogar unbekannte
Schluessel. Gibt es die Zeile noch nicht, wird sie am Ende des
passenden Abschnitts eingefuegt.

Geschrieben wird wie bei MiSTer selbst: erst in <datei>.tmp, dann
os.replace() - damit kann ein Stromausfall mitten im Schreiben die
Datei nicht halb zerstoeren.
"""
import os

from fe.log import LOG

RA_SETTINGS_FILE = "/media/fat/retroachievements.cfg"

# Die zehn Schalter aus dem OSD-Menue "Misc. Options -> RA Settings",
# in genau der Reihenfolge, in der sie dort stehen - wer beides benutzt,
# soll nicht suchen muessen.
#
# (Schluessel, Uebersetzungsschluessel, Standardwert)
#
# Die Standardwerte stammen aus dem Auslieferungszustand, wie er im
# eingeschickten OSD-Bildschirmfoto zu sehen war. Sie greifen nur, wenn
# der Schluessel in der Datei ueberhaupt nicht vorkommt.
SCHALTER = (
    ("show_challenge_show_popup",   "ra_set_challenge_start", True),
    ("show_challenge_hide_popup",   "ra_set_challenge_end",   True),
    ("show_progress_popups",        "ra_set_progress",        True),
    ("show_progress_name",          "ra_set_progress_name",   True),
    ("show_leaderboards_updates",   "ra_set_lb_updates",      True),
    ("show_leaderboards_submission", "ra_set_lb_submission",  True),
    ("multiline_desc",              "ra_set_multiline",       False),
    ("list_desc_ticker",            "ra_set_list_ticker",     False),
    ("list_hotkey",                 "ra_set_list_hotkey",     False),
)

# Aeltere Schreibweise mit Bindestrich, die in der Binary ebenfalls
# vorkommt - beim LESEN akzeptiert, beim SCHREIBEN nie erzeugt.
ALIAS = {
    "show_leaderboards_updates":    "show-leaderboards-updates",
    "show_leaderboards_submission": "show-leaderboards-submission",
}

POSITION_KEY = "popup_position"
POSITION_WERTE = ("left", "center", "right")
POSITION_STANDARD = "left"

# Grenzen exakt wie im OSD (aus der Ankuendigung: "H-Offset verschiebt
# die Popups horizontal (-80 bis +80), V-Offset vertikal (-10 bis +10)").
OFFSETS = {
    "popup_h_offset": (-80, 80),
    "popup_v_offset": (-10, 10),
}

# Diese drei wertet MiSTer pro Core aus - nur sie duerfen in einem
# [Core]-Abschnitt stehen.
PRO_CORE = (POSITION_KEY,) + tuple(OFFSETS)

# Wahrheitswerte grosszuegig lesen, sparsam schreiben: MiSTer selbst
# schreibt sehr wahrscheinlich 1/0 (in der Binary gibt es keine
# "on"/"off"/"true"-Zeichenketten fuer diese Schluessel). Wer die Datei
# aber von Hand mit "true" bearbeitet hat, soll trotzdem verstanden
# werden - und beim Zurueckschreiben seine Schreibweise behalten, siehe
# _bool_text().
_WAHR = ("1", "true", "yes", "on", "ja", "an")
_FALSCH = ("0", "false", "no", "off", "nein", "aus")


def _als_bool(text, standard=False):
    if text is None:
        return standard
    t = text.strip().lower()
    if t in _WAHR:
        return True
    if t in _FALSCH:
        return False
    return standard


def _bool_text(wert, vorlage=None):
    """Wahrheitswert in Text - moeglichst in DER Schreibweise, die in
    der Datei schon fuer diesen Schluessel stand. Wer seine Datei mit
    "true"/"false" pflegt, bekommt sie nicht stillschweigend auf 1/0
    umgeschrieben."""
    if vorlage is not None:
        v = vorlage.strip().lower()
        paare = (("true", "false"), ("yes", "no"), ("on", "off"),
                 ("ja", "nein"), ("an", "aus"))
        for ja, nein in paare:
            if v in (ja, nein):
                return ja if wert else nein
    return "1" if wert else "0"


def _zeilen_lesen():
    """Die Datei als Liste von Zeilen OHNE Zeilenumbruch. Fehlt sie oder
    ist sie nicht lesbar, gibt es None - der Aufrufer unterscheidet
    "nicht eingerichtet" von "leer"."""
    try:
        with open(RA_SETTINGS_FILE, "r", encoding="utf-8",
                  errors="replace") as f:
            return f.read().split("\n")
    except OSError:
        return None


def vorhanden():
    """Gibt es die MiSTer-RA-Datei ueberhaupt? Wenn nicht, ist RA in der
    MiSTer-Hauptanwendung nicht eingerichtet - dann legen wir die Datei
    bewusst NICHT an. Sie enthaelt Zugangsdaten; eine von uns erzeugte
    Datei mit lauter Einstellungen und ohne Benutzername/Passwort waere
    fuer MiSTer wertlos und fuer den Nutzer verwirrend."""
    return os.path.exists(RA_SETTINGS_FILE)


def _abschnitt_von(zeile):
    """Liefert den Abschnittsnamen, wenn die Zeile eine
    Abschnitts-Ueberschrift ist ("[SNES]"), sonst None."""
    z = zeile.strip()
    if len(z) >= 2 and z.startswith("[") and z.endswith("]"):
        return z[1:-1].strip()
    return None


def _schluessel_von(zeile):
    """Liefert (schluessel, wert) einer Zuweisungszeile, sonst
    (None, None). Kommentarzeilen (# oder ;) zaehlen ausdruecklich
    NICHT als Zuweisung - eine auskommentierte Zeile soll
    auskommentiert bleiben und nicht versehentlich ueberschrieben
    werden."""
    z = zeile.strip()
    if not z or z[0] in "#;" or "=" not in z:
        return None, None
    k, _, v = zeile.partition("=")
    return k.strip(), v.strip()


def roh_lesen(schluessel, sektion=None):
    """Rohen Textwert eines Schluessels lesen, oder None.

    sektion=None meint den globalen Bereich VOR der ersten
    Abschnitts-Ueberschrift. Wird in einer Sektion nichts gefunden,
    liefert diese Funktion bewusst NICHT den globalen Wert - dafuer gibt
    es wert_mit_herkunft(), damit der Aufrufer den Unterschied zwischen
    "eigener Wert" und "erbt global" anzeigen kann."""
    zeilen = _zeilen_lesen()
    if zeilen is None:
        return None
    namen = [schluessel]
    if schluessel in ALIAS:
        namen.append(ALIAS[schluessel])
    aktuell = None
    for zeile in zeilen:
        s = _abschnitt_von(zeile)
        if s is not None:
            aktuell = s
            continue
        if aktuell != sektion and not (aktuell is None and sektion is None):
            continue
        k, v = _schluessel_von(zeile)
        if k in namen:
            return v
    return None


def roh_schreiben(schluessel, wert, sektion=None):
    """Einen Schluessel setzen und die Datei zurueckschreiben - alles
    andere bleibt Byte fuer Byte erhalten (siehe Modul-Kommentar).

    Liefert True bei Erfolg. JEDER Fehlerfall wird geloggt und liefert
    False, statt zu werfen: eine Einstellung, die sich nicht speichern
    laesst, darf das Frontend nicht abstuerzen lassen."""
    zeilen = _zeilen_lesen()
    if zeilen is None:
        LOG("ra_settings: %s nicht lesbar - nichts geschrieben"
            % RA_SETTINGS_FILE)
        return False

    namen = [schluessel]
    if schluessel in ALIAS:
        namen.append(ALIAS[schluessel])
    neue_zeile = "%s=%s" % (schluessel, wert)

    # 1. Versuch: die Zeile steht schon da - dann genau sie ersetzen.
    aktuell = None
    for i, zeile in enumerate(zeilen):
        s = _abschnitt_von(zeile)
        if s is not None:
            aktuell = s
            continue
        if aktuell != sektion and not (aktuell is None and sektion is None):
            continue
        k, _v = _schluessel_von(zeile)
        if k in namen:
            zeilen[i] = neue_zeile
            return _zeilen_schreiben(zeilen, schluessel, wert, sektion)

    # 2. Die Zeile fehlt. Einfuegen ans ENDE des passenden Abschnitts -
    #    nicht am Dateiende, sonst landete ein globaler Wert hinter
    #    einer Abschnitts-Ueberschrift und gehoerte damit ploetzlich zu
    #    diesem Core.
    if sektion is None:
        einfuegen = len(zeilen)
        for i, zeile in enumerate(zeilen):
            if _abschnitt_von(zeile) is not None:
                einfuegen = i
                break
        # Hinter der letzten nicht-leeren Zeile davor einhaengen, damit
        # keine Leerzeile mitten in den Block rutscht.
        while einfuegen > 0 and not zeilen[einfuegen - 1].strip():
            einfuegen -= 1
        zeilen.insert(einfuegen, neue_zeile)
        return _zeilen_schreiben(zeilen, schluessel, wert, sektion)

    # 3. Abschnitt suchen; gibt es ihn nicht, am Dateiende anlegen.
    start = None
    for i, zeile in enumerate(zeilen):
        if _abschnitt_von(zeile) == sektion:
            start = i
            break
    if start is None:
        while zeilen and not zeilen[-1].strip():
            zeilen.pop()
        zeilen += ["", "[%s]" % sektion, neue_zeile, ""]
        return _zeilen_schreiben(zeilen, schluessel, wert, sektion)

    ende = len(zeilen)
    for i in range(start + 1, len(zeilen)):
        if _abschnitt_von(zeilen[i]) is not None:
            ende = i
            break
    while ende > start + 1 and not zeilen[ende - 1].strip():
        ende -= 1
    zeilen.insert(ende, neue_zeile)
    return _zeilen_schreiben(zeilen, schluessel, wert, sektion)


def _zeilen_schreiben(zeilen, schluessel, wert, sektion):
    """Gleiches Vorgehen wie MiSTers eigenes ra_save(): erst in eine
    temporaere Datei daneben, dann umbenennen. os.replace() ist auf
    demselben Dateisystem atomar - entweder die alte oder die neue
    Datei, nie eine halbe."""
    tmp = RA_SETTINGS_FILE + ".dragend.tmp"
    text = "\n".join(zeilen)
    if not text.endswith("\n"):
        text += "\n"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, RA_SETTINGS_FILE)
    except OSError as e:
        LOG("ra_settings: Schreiben fehlgeschlagen (%s=%s, Sektion %s): %s"
            % (schluessel, wert, sektion, e))
        try:
            os.remove(tmp)
        except OSError:
            pass
        return False
    LOG("ra_settings: [%s] %s=%s" % (sektion or "global", schluessel, wert))
    return True


# ----------------------------------------------------------------- Schalter
def schalter_lesen(schluessel, standard=False):
    return _als_bool(roh_lesen(schluessel), standard)


def schalter_umschalten(schluessel, standard=False):
    """Umschalten und den NEUEN Zustand liefern. Schlaegt das Schreiben
    fehl, wird der alte Zustand geliefert - die Anzeige zeigt dann
    weiterhin die Wahrheit statt einer Aenderung, die gar nicht in der
    Datei steht."""
    alt_text = roh_lesen(schluessel)
    neu = not _als_bool(alt_text, standard)
    if roh_schreiben(schluessel, _bool_text(neu, alt_text)):
        return neu
    return not neu


# ----------------------------------------------------------------- Position
def position_lesen(sektion=None):
    """Popup-Position. In einer Sektion faellt ein fehlender Wert auf
    den globalen zurueck - genauso, wie MiSTer es liest."""
    roh = roh_lesen(POSITION_KEY, sektion)
    if roh is None and sektion is not None:
        roh = roh_lesen(POSITION_KEY, None)
    if roh is None:
        return POSITION_STANDARD
    w = roh.strip().lower()
    if w == "centre":            # MiSTer akzeptiert beide Schreibweisen
        w = "center"
    return w if w in POSITION_WERTE else POSITION_STANDARD


def position_weiter(sektion=None):
    """Zur naechsten Position wechseln (links -> mitte -> rechts -> ...)
    und die neue liefern."""
    jetzt = position_lesen(sektion)
    neu = POSITION_WERTE[(POSITION_WERTE.index(jetzt) + 1)
                         % len(POSITION_WERTE)]
    if roh_schreiben(POSITION_KEY, neu, sektion):
        return neu
    return jetzt


# ------------------------------------------------------------------ Offsets
def offset_grenzen(schluessel):
    return OFFSETS[schluessel]


def offset_lesen(schluessel, sektion=None):
    """Wie position_lesen(): in einer Sektion faellt ein fehlender Wert
    auf den globalen zurueck."""
    roh = roh_lesen(schluessel, sektion)
    if roh is None and sektion is not None:
        roh = roh_lesen(schluessel, None)
    lo, hi = OFFSETS[schluessel]
    try:
        return max(lo, min(hi, int(str(roh).strip())))
    except (TypeError, ValueError):
        return 0


def offset_schreiben(schluessel, wert, sektion=None):
    lo, hi = OFFSETS[schluessel]
    wert = max(lo, min(hi, int(wert)))
    return roh_schreiben(schluessel, "%d" % wert, sektion)


def wert_mit_herkunft(schluessel, sektion):
    """(wert, eigen) fuer einen der drei Pro-Core-Schluessel.

    eigen=True bedeutet: in DIESEM Abschnitt steht ein eigener Wert.
    eigen=False: der Abschnitt erbt den globalen. Der Unterschied ist
    fuer die Anzeige wichtig - "0 (global)" und "0 (eigener Wert)" sehen
    sonst gleich aus, verhalten sich aber verschieden, sobald der
    globale Wert geaendert wird."""
    eigen = sektion is not None and roh_lesen(schluessel, sektion) is not None
    if schluessel == POSITION_KEY:
        return position_lesen(sektion), eigen
    return offset_lesen(schluessel, sektion), eigen


def sektion_zuruecksetzen(sektion):
    """Alle Pro-Core-Werte eines Abschnitts entfernen, damit er wieder
    die globalen erbt. Der Abschnitt selbst bleibt stehen, falls MiSTer
    dort noch andere Schluessel fuehrt, die uns nichts angehen."""
    zeilen = _zeilen_lesen()
    if zeilen is None:
        return False
    behalten = []
    aktuell = None
    entfernt = 0
    for zeile in zeilen:
        s = _abschnitt_von(zeile)
        if s is not None:
            aktuell = s
            behalten.append(zeile)
            continue
        k, _v = _schluessel_von(zeile)
        if aktuell == sektion and k in PRO_CORE:
            entfernt += 1
            continue
        behalten.append(zeile)
    if not entfernt:
        return True
    return _zeilen_schreiben(behalten, "(zurueckgesetzt)", "", sektion)


def core_name(rbf):
    """Abschnittsname fuer ein System: MiSTer fuehrt seine Abschnitte
    pro CORE, nicht pro System - und den Corenamen kennen wir aus dem
    RBF-Pfad in GAME_SYSTEMS ("_Console/Gameboy" -> "Gameboy"). Das ist
    derselbe Name, den MiSTer in /tmp/CORENAME schreibt.

    WICHTIG und in der Anzeige auch so benannt: mehrere Systeme koennen
    denselben Core benutzen. Game Boy und Game Boy Color teilen sich
    "Gameboy", SNES und SMW Hacks teilen sich "SNES" - eine Aenderung
    dort gilt zwangslaeufig fuer beide. Das ist kein Mangel unserer
    Umsetzung, sondern die Art, wie MiSTer die Werte ablegt."""
    if not rbf:
        return None
    return os.path.basename(str(rbf)).strip() or None
