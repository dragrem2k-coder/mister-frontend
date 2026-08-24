#!/bin/bash
# ============================================================
# Spiele-Infos (Genre, Jahr, Spieleranzahl) fuer das
# MiSTer-Frontend aus der libretro-Datenbank laden.
# Startbar aus dem OSD (Scripts), dem Frontend oder per SSH.
#
# NEU: diese Datei hiess bis einschliesslich Build 2026-08-24-5
# "gameinfo_download.sh" - jetzt umbenannt, siehe Kopfkommentar in
# Frontend_Install.sh fuer die Begruendung. frontend.py ruft sie
# passend dazu jetzt ebenfalls unter dem neuen Namen auf.
# ============================================================
echo "Lade Spiele-Metadaten ..."
exec /usr/bin/python3 /media/fat/frontend/mister_gameinfo.py
