#!/bin/bash
# ============================================================
# Spiele-Infos (Genre, Jahr, Spieleranzahl) fuer das
# MiSTer-Frontend aus der libretro-Datenbank laden.
# Startbar aus dem OSD (Scripts), dem Frontend oder per SSH.
# ============================================================
echo "Lade Spiele-Metadaten ..."
exec /usr/bin/python3 /media/fat/frontend/mister_gameinfo.py
