#!/bin/bash
# ============================================================
# KOMPATIBILITAETS-PLATZHALTER - bitte nicht mehr direkt verwenden.
#
# Diese Datei hiess bis einschliesslich Build 2026-08-24-5 die
# eigentliche "Frontend nach einem Update neu starten"-Logik - die
# steckt jetzt in Frontend_Update.sh (siehe dortiger Kopfkommentar
# fuer die Begruendung des "Frontend_"-Praefixes bei allen eigenen
# Scripts).
#
# Dieser winzige Platzhalter bleibt vorerst trotzdem hier liegen, rein
# aus Kompatibilitaetsgruenden: eine bereits auf der SD-Karte
# installierte, noch nicht aktualisierte Fassung von "install_frontend.sh"
# (dem alten Namen von Frontend_Install.sh) verweist in ihrem eigenen,
# schon vorher heruntergeladenen Code fest auf GENAU DIESEN Dateinamen
# ("update_frontend.sh") - ohne diesen Platzhalter wuerde ein erster
# Lauf dieser alten Datei nach der Umbenennung mit "Datei nicht
# gefunden" hier abbrechen, statt sauber durchzureichen. Reicht einfach
# nur weiter; Frontend_Update.sh raeumt beim Durchlaufen automatisch
# alle noch vorhandenen alten Dateinamen (auch diesen hier) auf - ab
# dem naechsten Lauf ist diese Datei also von selbst wieder weg.
# ============================================================
exec bash "$(dirname "$0")/Frontend_Update.sh" "$@"
