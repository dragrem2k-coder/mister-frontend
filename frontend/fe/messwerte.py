# -*- coding: utf-8 -*-
"""Messwerte aus dem echten Betrieb (Build 343).

ANLASS: ein Vergleich mit einem anderen Frontend, der dem Nutzer
vorgelegt wurde. Dort stand bei Dragend zweimal "kein belastbarer
Messwert": beim Speicherbedarf und bei der Rueckkehr aus einem Core.
Beides laesst sich in einem Pruefstand nicht nachstellen - ein Core
startet nur auf dem Geraet, und der Speicher eines Pruefstands sagt
nichts ueber den des Frontends. Gemessen wird deshalb dort, wo es
passiert:

  - RUECKKEHR: run_core() misst jede echte Rueckkehr in Abschnitten
    und legt die letzten RUECKKEHR_MAX in RUECKKEHR_FILE ab. Der Bench
    (Abschnitt S) liest sie aus.
  - SPEICHER: /proc/self/status, so wie es der Kernel zaehlt -
    belegter Speicher jetzt, die Spitze seit dem Start, und beim
    Core-Start mit in die Rueckkehr-Datei geschrieben.

Dieses Modul importiert nichts aus dem Frontend; es wird vom Frontend
und vom Bench benutzt.
"""
import json
import os
import time

RUECKKEHR_FILE = "/media/fat/frontend/rueckkehr_zeiten.json"
RUECKKEHR_MAX = 20
STATUS_FILE = "/proc/self/status"
MEMINFO_FILE = "/proc/meminfo"


def _kb_felder(pfad, felder):
    """{Feldname: Wert in kB} aus einer Datei im Format von
    /proc/self/status ("VmRSS:   12345 kB"). Fehlende Felder fehlen."""
    raus = {}
    try:
        with open(pfad) as f:
            for zeile in f:
                name, _, rest = zeile.partition(":")
                if name in felder:
                    teile = rest.split()
                    if teile and teile[0].isdigit():
                        raus[name] = int(teile[0])
    except OSError:
        pass
    return raus


def speicher(pfad=None):
    """Speicher DIESES Prozesses in kB:
    {"belegt": VmRSS, "spitze": VmHWM, "anonym": RssAnon}.
    Leeres dict, wenn es nicht zu lesen ist (kein Linux)."""
    roh = _kb_felder(pfad or STATUS_FILE, ("VmRSS", "VmHWM", "RssAnon"))
    raus = {}
    for alt, neu in (("VmRSS", "belegt"), ("VmHWM", "spitze"),
                     ("RssAnon", "anonym")):
        if alt in roh:
            raus[neu] = roh[alt]
    return raus


def system_speicher(pfad=None):
    """{"gesamt": MemTotal, "verfuegbar": MemAvailable} in kB - was
    Linux auf dem MiSTer ueberhaupt hat. Die Cores haben ihren eigenen
    Bereich ausserhalb davon."""
    roh = _kb_felder(pfad or MEMINFO_FILE, ("MemTotal", "MemAvailable"))
    raus = {}
    if "MemTotal" in roh:
        raus["gesamt"] = roh["MemTotal"]
    if "MemAvailable" in roh:
        raus["verfuegbar"] = roh["MemAvailable"]
    return raus


def rueckkehr_laden(pfad=None):
    """Die gemerkten Rueckkehr-Messungen, aelteste zuerst. Eine kaputte
    oder fremde Datei ergibt eine leere Liste, nie einen Fehler."""
    try:
        with open(pfad or RUECKKEHR_FILE) as f:
            daten = json.load(f)
    except (OSError, ValueError):
        return []
    if not isinstance(daten, list):
        return []
    return [e for e in daten if isinstance(e, dict)
            and isinstance(e.get("gesamt_ms"), (int, float))]


def rueckkehr_merken(eintrag, pfad=None):
    """Eine Messung anhaengen, nur die letzten RUECKKEHR_MAX behalten.
    Geschrieben ueber eine .tmp-Datei und os.replace(): ein Stromausfall
    mitten im Schreiben hinterlaesst die alte Datei, keine halbe.
    True, wenn geschrieben."""
    pfad = pfad or RUECKKEHR_FILE
    alle = rueckkehr_laden(pfad)
    e = dict(eintrag)
    e.setdefault("zeit", int(time.time()))
    alle.append(e)
    alle = alle[-RUECKKEHR_MAX:]
    tmp = pfad + ".tmp"
    try:
        d = os.path.dirname(pfad)
        if d:
            os.makedirs(d, exist_ok=True)
        with open(tmp, "w") as f:
            json.dump(alle, f, indent=1)
        os.replace(tmp, pfad)
        return True
    except OSError:
        try:
            os.remove(tmp)
        except OSError:
            pass
        return False


def median(werte):
    w = sorted(v for v in werte if isinstance(v, (int, float)))
    if not w:
        return None
    m = len(w) // 2
    return w[m] if len(w) % 2 else (w[m - 1] + w[m]) / 2.0


def rueckkehr_zeile(e):
    """Die Logzeile zu einer Messung - an EINER Stelle, damit Log und
    Bench dieselben Abschnitte nennen."""
    teile = ", ".join("%s %d" % (name, e.get(k, 0))
                      for name, k in (("Nacharbeit", "nacharbeit_ms"),
                                      ("Pause", "pause_ms"),
                                      ("Musik/Listen", "listen_ms"),
                                      ("Konsole", "konsole_ms"),
                                      ("Zeichnen", "zeichnen_ms")))
    zeile = ("RUECKKEHR: %d ms vom erkannten Menue bis zum ersten Bild (%s)"
             % (e.get("gesamt_ms", 0), teile))
    if isinstance(e.get("ab_ausstieg_ms"), (int, float)):
        zeile += " - %d ms ab der Ausstiegs-Taste (%s)" % (
            e["ab_ausstieg_ms"], e.get("weg", "?"))
    if isinstance(e.get("speicher_im_core_kb"), (int, float)):
        zeile += ", waehrend des Spiels %d kB belegt" % e["speicher_im_core_kb"]
    return zeile
