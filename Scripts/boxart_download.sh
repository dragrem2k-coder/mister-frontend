#!/bin/bash
# ============================================================
# Boxart-Download fuer das MiSTer-Frontend
# Laedt Cover von thumbnails.libretro.com und erzeugt
# .art-Dateien unter /media/fat/frontend/art/
#
# Startbar aus dem MiSTer-OSD (Scripts), aus der Scripts-
# Kategorie des Frontends oder per SSH.
#
# Profil anpassen: "sd" fuer CRT (Standard), "hd" fuer 1080p.
# ============================================================
PROFIL="sd"

echo "Boxart-Download startet (Profil: $PROFIL) ..."
echo "Abbrechen jederzeit mit Strg+C - Fortschritt bleibt erhalten."
echo ""
exec /usr/bin/python3 /media/fat/frontend/mister_boxart.py "$PROFIL"
