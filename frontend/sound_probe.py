#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sound-Probe: sagt in Klartext, warum ein Klang nicht kommt.

    python3 /media/fat/frontend/sound_probe.py
    python3 /media/fat/frontend/sound_probe.py zufall_ziehung

ENTSTANDEN AUS EINER RUECKMELDUNG (Build 247): "bei zufallszock hoere
ich denn sound nicht wird nicht abgespielt". Daran war nichts zu sehen -
das Frontend hat den Fehlschlag damals nirgends hingeschrieben. Diese
Probe geht die Kette durch, die ein Klang nehmen muss, und sagt bei
jedem Glied, ob es haelt:

    1. gibt es den Ordner, und was liegt darin?
    2. gibt es die Datei fuer DIESEN Namen - mp3 oder wav?
    3. gibt es das Abspielprogramm dafuer?
    4. laeuft gerade etwas anderes auf der Soundkarte?
    5. und zuletzt: einmal wirklich abspielen und den Rueckgabewert
       nennen.

Sie aendert NICHTS auf der Karte und laeuft ohne das Frontend.
"""
import os
import subprocess
import sys

SFX_DIR = "/media/fat/frontend/sfx"
MPG123 = "/usr/bin/mpg123"
VOLUME_FILE = "/media/fat/frontend/volume"
SFX_DISABLED = "/media/fat/frontend/sfx_disabled"
ZIEHUNG_DATEI = "/media/fat/frontend/ziehung_spannung"


def sagen(text=""):
    print(text)


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "zufall_ziehung"
    sagen("=" * 62)
    sagen(" Sound-Probe fuer '%s'" % name)
    sagen("=" * 62)

    # --- 1. der Ordner -------------------------------------------
    if not os.path.isdir(SFX_DIR):
        sagen("FEHLT: der Ordner %s gibt es nicht." % SFX_DIR)
        sagen("       Das Frontend legt ihn beim ersten Start an. Lief")
        sagen("       es auf diesem Geraet ueberhaupt schon?")
        return 1
    dateien = sorted(os.listdir(SFX_DIR))
    sagen("Ordner   : %s  (%d Dateien)" % (SFX_DIR, len(dateien)))

    # --- 2. die Datei fuer diesen Namen --------------------------
    mp3 = os.path.join(SFX_DIR, name + ".mp3")
    wav = os.path.join(SFX_DIR, name + ".wav")
    hat_mp3 = os.path.exists(mp3)
    hat_wav = os.path.exists(wav)
    sagen("  %s.mp3 : %s" % (name,
                             ("%d Byte" % os.path.getsize(mp3))
                             if hat_mp3 else "FEHLT"))
    sagen("  %s.wav : %s" % (name,
                             ("%d Byte" % os.path.getsize(wav))
                             if hat_wav else "FEHLT"))
    if not hat_mp3 and not hat_wav:
        sagen()
        sagen("DAS IST DIE URSACHE: fuer diesen Namen liegt keine Datei")
        sagen("da. Die .wav erzeugt das Frontend beim Start selbst - wenn")
        sagen("sie fehlt, lief es nach dem Update noch nicht neu. Die .mp3")
        sagen("kommt vom Installer (Scripts -> Frontend Install).")
        return 1

    # --- 3. das Abspielprogramm ----------------------------------
    sagen()
    sagen("Abspielprogramme")
    sagen("  mpg123 (fuer mp3) : %s"
          % (MPG123 if os.path.exists(MPG123) else "FEHLT - %s" % MPG123))
    try:
        aplay = subprocess.call(["aplay", "--version"],
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL) == 0
    except OSError:
        aplay = False
    sagen("  aplay  (fuer wav) : %s" % ("da" if aplay else "FEHLT"))
    nimmt_mp3 = hat_mp3 and os.path.exists(MPG123)
    if not nimmt_mp3 and not (hat_wav and aplay):
        sagen()
        sagen("DAS IST DIE URSACHE: zur vorhandenen Datei fehlt das")
        sagen("passende Abspielprogramm.")
        return 1
    sagen("  -> benutzt wird   : %s" % (mp3 if nimmt_mp3 else wav))

    # --- 4. Einstellungen, die mitreden -------------------------
    sagen()
    sagen("Einstellungen")
    try:
        vol = open(VOLUME_FILE).read().strip()
    except OSError:
        vol = "nicht gesetzt (Standard)"
    sagen("  Lautstaerke       : %s" % vol)
    sagen("  Navigationstoene  : %s"
          % ("AUS" if os.path.exists(SFX_DISABLED) else "an"))
    sagen("                      (seit Build 247 egal fuer die Ziehung -")
    sagen("                       sie haengt nur an der Dauer darunter)")
    try:
        zieh = open(ZIEHUNG_DATEI).read().strip()
        zieh = "aus" if zieh == "0" else "%s ms" % zieh
    except OSError:
        zieh = "2000 ms (Standard)"
    sagen("  Ziehung Spannung  : %s" % zieh)
    if zieh == "aus":
        sagen()
        sagen("DAS IST DIE URSACHE: die Spannungsphase steht auf 'aus',")
        sagen("und damit gibt es auch keinen Ton. System -> Verhalten &")
        sagen("Optionen -> 'Ziehung Spannung'.")
        return 1

    # --- 5. wer belegt die Soundkarte? ---------------------------
    sagen()
    try:
        belegt = subprocess.check_output(
            ["sh", "-c", "fuser -v /dev/snd/* 2>&1 | head -5"]).decode(
                "utf-8", "replace").strip()
    except Exception:                                    # noqa: BLE001
        belegt = ""
    sagen("Soundkarte        : %s"
          % (belegt.replace("\n", " | ") if belegt else "niemand gemeldet"))

    # --- 6. einmal wirklich abspielen ---------------------------
    sagen()
    sagen("Jetzt wird einmal abgespielt - du solltest es hoeren.")
    if nimmt_mp3:
        cmd = [MPG123, "-q", mp3]
    else:
        cmd = ["aplay", "-q", wav]
    sagen("  %s" % " ".join(cmd))
    try:
        rc = subprocess.call(cmd)
    except OSError as e:
        sagen("  FEHLER beim Starten: %s" % e)
        return 1
    sagen("  Rueckgabewert: %d" % rc)
    sagen()
    if rc == 0:
        sagen("Das Abspielen selbst geht. Hoerst du HIER etwas, aber im")
        sagen("Frontend nicht, dann schicke /tmp/frontend.log - dort steht")
        sagen("seit Build 247 eine Zeile, wenn ein Klang nicht startet.")
    else:
        sagen("Das Abspielen selbst schlaegt fehl - die Meldung darueber")
        sagen("ist die eigentliche Auskunft. Haeufigste Ursache: die")
        sagen("Soundkarte ist von einem anderen Programm belegt.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
