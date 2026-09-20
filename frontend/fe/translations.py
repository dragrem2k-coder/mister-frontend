#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Uebersetzungen (Deutsch/Englisch) - ausgelagert aus frontend.py als
ersten Schritt der schrittweisen Modularisierung (siehe Git-Branch
'modular-refactor'). Komplett in sich geschlossen: TRANSLATIONS,
Sprachauswahl-Persistierung (LANGUAGE_FILE), und die t()-Hilfsfunktion,
die im restlichen Code an ueber 200 Stellen verwendet wird.

WICHTIG (Python-Import-Falle bei mutierbaren Modul-Variablen):
CURRENT_LANG wird von set_language() nachtraeglich per "global"
umgeschrieben. Ein einfaches "from fe.translations import CURRENT_LANG"
an anderer Stelle wuerde dort eine EINGEFRORENE Kopie zum Import-
Zeitpunkt erzeugen, die spaetere Aenderungen NICHT mehr mitbekommt -
deshalb gibt es zusaetzlich current_lang() als Funktion, die man
stattdessen aufruft (liest IMMER den aktuellen Wert aus diesem Modul).
"""
import os

LANGUAGE_FILE = "/media/fat/frontend/language"

TRANSLATIONS = {
    "categories":      {"en": "%d categories",  "de": "%d Kategorien"},
    "entries":         {"en": "%d entries",      "de": "%d Einträge"},
    "footer_cats_wide":   {"en": "Up/Down:Nav  Left/Right:Page  Enter:Open  ESC:Quit",
                           "de": "Hoch/Runter:Nav  Links/Rechts:Seite  Enter:Öffnen  ESC:Beenden"},
    "footer_cats_mid":    {"en": "Nav  Page  Enter:Open  ESC:Quit",
                           "de": "Nav  Seite  Enter:Öffnen  ESC:Beenden"},
    "footer_cats_narrow": {"en": "Enter:Open  ESC:Quit",
                           "de": "Enter:Öffnen  ESC:Beenden"},
    "footer_items_wide":   {"en": "Up/Down:Nav  Left/Right:Page  Enter/A:Start  ESC/B:Back",
                            "de": "Hoch/Runter:Nav  Links/Rechts:Seite  Enter/A:Start  ESC/B:Zurück"},
    "footer_items_mid":    {"en": "L/R:Page  Enter/A:Start  ESC/B:Back",
                            "de": "L/R:Seite  Enter/A:Start  ESC/B:Zurück"},
    "footer_items_narrow": {"en": "A:Start  B:Back", "de": "A:Start  B:Zurück"},
    "quit_confirm":    {"en": "Quit the frontend?", "de": "Frontend wirklich beenden?"},
    "yes":             {"en": "Yes", "de": "Ja"},
    "no":              {"en": "No",  "de": "Nein"},
    # NEU (Nutzer-Rueckmeldung: "Frontend beenden" schien nicht zu
    # funktionieren - ein echtes frontend.log zeigte, dass wiederholt
    # NUR "ok" gedrueckt wurde, nie "links"/"rechts" davor, wodurch
    # immer die vorausgewaehlte "Nein"-Option bestaetigt wurde, siehe
    # draw_confirm_dialog()/_confirm_dialog_toggle()): sichtbarer
    # Hinweistext direkt im Ja/Nein-Dialog, analog zum bereits
    # bestehenden core_choice_hint.
    "confirm_dialog_hint": {"en": "Left/Right or Up/Down to choose, OK to confirm",
                            "de": "Links/Rechts oder Hoch/Runter wählen, OK bestätigen"},
    # NEUES FEATURE (Nutzerwunsch: "koennen wir das Update-Popup um eine
    # Abfrage 'jetzt installieren oder spaeter' erweitern?") - siehe
    # _start_update_install_dialog()/draw_confirm_dialog() in frontend.py.
    "update_install_confirm": {"en": "Update v%s available. Install now?",
                               "de": "Update v%s verfügbar. Jetzt installieren?"},
    "build_install_confirm": {"en": "New: %s. Install now?",
                              "de": "Neu: %s. Jetzt installieren?"},
    "install_now":     {"en": "Now",   "de": "Jetzt"},
    "install_later":   {"en": "Later", "de": "Später"},
    "players":         {"en": "Players: %s", "de": "Spieler: %s"},
    "year":            {"en": "Year: %s",    "de": "Jahr: %s"},
    "playtime_shown":  {"en": "Played: %s",  "de": "Gespielt: %s"},
    "ra_progress_shown": {"en": "RA: %d/%d", "de": "RA: %d/%d"},
    "completed_shown": {"en": "Completed", "de": "Durchgespielt"},
    "milestone_playtime_1h": {"en": "Played 1 hour total", "de": "Insgesamt 1 Stunde gespielt"},
    "milestone_playtime_10h": {"en": "Played 10 hours total", "de": "Insgesamt 10 Stunden gespielt"},
    "milestone_playtime_50h": {"en": "Played 50 hours total", "de": "Insgesamt 50 Stunden gespielt"},
    "milestone_playtime_100h": {"en": "Played 100 hours total", "de": "Insgesamt 100 Stunden gespielt"},
    "milestone_launches_10": {"en": "Launched 10 games", "de": "10 Spiele gestartet"},
    "milestone_launches_50": {"en": "Launched 50 games", "de": "50 Spiele gestartet"},
    "milestone_launches_100": {"en": "Launched 100 games", "de": "100 Spiele gestartet"},
    "milestone_launches_500": {"en": "Launched 500 games", "de": "500 Spiele gestartet"},
    "milestone_systems_3": {"en": "Explorer: 3 different systems", "de": "Entdecker: 3 verschiedene Systeme"},
    "milestone_systems_5": {"en": "Explorer: 5 different systems", "de": "Entdecker: 5 verschiedene Systeme"},
    "milestone_systems_10": {"en": "Explorer: 10 different systems", "de": "Entdecker: 10 verschiedene Systeme"},
    "milestone_completed_1": {"en": "First game completed", "de": "Erstes Spiel durchgespielt"},
    "milestone_completed_5": {"en": "5 games completed", "de": "5 Spiele durchgespielt"},
    "milestone_completed_10": {"en": "10 games completed", "de": "10 Spiele durchgespielt"},
    "milestone_completed_25": {"en": "25 games completed", "de": "25 Spiele durchgespielt"},
    "milestones_title": {"en": "MY ACHIEVEMENTS", "de": "MEINE ERFOLGE"},
    "milestones_summary": {"en": "%d of %d unlocked", "de": "%d von %d freigeschaltet"},
    "hidden_section_title": {"en": "Hidden achievements (%d/%d)",
                             "de": "Versteckte Erfolge (%d/%d)"},
    "hidden_mystery": {"en": "??? (keep playing to find out)",
                       "de": "??? (einfach weiterspielen)"},
    "hidden_night_owl": {"en": "Night Owl: played between midnight and 5am",
                         "de": "Nachteule: zwischen 0 und 5 Uhr gespielt"},
    "hidden_marathon": {"en": "Marathon: a single session over 3 hours",
                        "de": "Marathon: eine Sitzung über 3 Stunden am Stück"},
    "hidden_collector": {"en": "Collector: 10 favorites at once",
                         "de": "Sammlerin: 10 Favoriten gleichzeitig"},
    "hidden_completionist": {"en": "Regular: one game launched 20+ times",
                             "de": "Stammspieler: ein Spiel 20+ mal gestartet"},
    "hidden_legend": {"en": "Legend: reached every top-tier milestone at once",
                      "de": "Legende: alle höchsten Meilensteine gleichzeitig erreicht"},
    "hidden_early_bird": {"en": "Early Bird: played between 5am and 7am",
                          "de": "Frühaufsteher: zwischen 5 und 7 Uhr gespielt"},
    "hidden_weekend_warrior": {"en": "Weekend Warrior: played both Saturday and Sunday of the same week",
                               "de": "Wochenend-Krieger: an Samstag UND Sonntag derselben Woche gespielt"},
    "hidden_comeback": {"en": "Comeback: returned to a game after 6+ months away",
                        "de": "Comeback: ein Spiel nach 6+ Monaten Pause wieder gestartet"},
    "hidden_versatile": {"en": "Versatile: 4+ different systems in a single day",
                         "de": "Vielseitig: an einem Tag Spiele aus 4+ verschiedenen Systemen gestartet"},
    "hidden_perfectionist": {"en": "Perfectionist: 100% RetroAchievements completion on a game",
                             "de": "Perfektionist: ein Spiel zu 100% bei RetroAchievements abgeschlossen"},
    "achievement_popup": {"en": "Achievement unlocked: %s",
                          "de": "Erfolg freigeschaltet: %s"},
    "achievement_popup_multi": {"en": "%d achievements unlocked!",
                                "de": "%d Erfolge freigeschaltet!"},
    "secret_unlocked": {"en": "Secret unlocked: %s", "de": "Geheimnis freigeschaltet: %s"},
    "secret_sound_replay": {"en": "\u2669 secret sound \u2669", "de": "\u2669 geheimer Sound \u2669"},
    "secrets_title": {"en": "SECRETS", "de": "GEHEIMNISSE"},
    "secrets_summary": {"en": "%d of %d found", "de": "%d von %d gefunden"},
    "secrets_keyboard_hint": {"en": "Codes only work via keyboard, not gamepad",
                              "de": "Codes funktionieren nur per Tastatur, nicht per Gamepad"},
    "secret_origin_secret_theme_1": {"en": "Origin: the Konami Code (Contra, Gradius, ...)",
                                     "de": "Herkunft: der Konami-Code (Contra, Gradius, ...)"},
    "secret_origin_entwicklerraum": {"en": "Origin: the Capcom Code (Street Fighter II)",
                                     "de": "Herkunft: der Capcom-Code (Street Fighter II)"},
    "secret_origin_secret_sound": {"en": "Origin: the Ikari Warriors continue code",
                                   "de": "Herkunft: der Ikari-Warriors-Weiterspielen-Code"},
    "secret_origin_dev_room_bonus": {"en": "Origin: found by trying things inside a secret itself",
                                     "de": "Herkunft: gefunden, indem im Geheimnis selbst weiterprobiert wurde"},
    "secret_origin_rainbow_cursor": {"en": "Origin: just spell it out",
                                     "de": "Herkunft: einfach buchstabieren"},
    "secret_origin_chiptune_sound": {"en": "Origin: an 8-bit state of mind",
                                     "de": "Herkunft: eine 8-Bit-Geisteshaltung"},
    "max_level_boot_effect": {"en": "FRONTEND LEVEL MAX", "de": "FRONTEND-LEVEL MAX"},
    "secret_name_secret_theme_1": {"en": "hidden theme", "de": "geheimes Theme"},
    "secret_name_entwicklerraum": {"en": "developer room", "de": "Entwicklerraum"},
    "secret_name_secret_sound": {"en": "hidden sound", "de": "geheimer Sound"},
    "secret_name_dev_room_bonus": {"en": "a secret within a secret", "de": "ein Geheimnis im Geheimnis"},
    "secret_name_rainbow_cursor": {"en": "rainbow cursor", "de": "Regenbogen-Cursor"},
    "secret_name_chiptune_sound": {"en": "chiptune jingle", "de": "Chiptune-Jingle"},
    "secret_origin_theme_snes": {"en": "Origin: Batman Forever (SNES) stage select",
                                 "de": "Herkunft: Batman Forever (SNES) Stage-Auswahl"},
    "secret_name_theme_snes": {"en": "hidden theme: SNES", "de": "geheimes Theme: SNES"},
    "secret_origin_theme_gb": {"en": "Origin: Game Genie \"Message 2\" (Game Boy)",
                               "de": "Herkunft: Game Genie \"Message 2\" (Game Boy)"},
    "secret_name_theme_gb": {"en": "hidden theme: Game Boy", "de": "geheimes Theme: Game Boy"},
    "secret_origin_theme_gbc": {"en": "Origin: cheat menu code from Space Invaders (Game Boy Color)",
                                "de": "Herkunft: Cheat-Menü-Code aus Space Invaders (Game Boy Color)"},
    "secret_name_theme_gbc": {"en": "hidden theme: Game Boy Color", "de": "geheimes Theme: Game Boy Color"},
    "secret_origin_theme_n64": {"en": "Origin: Robotron 64 (N64)",
                                "de": "Herkunft: Robotron 64 (N64)"},
    "secret_name_theme_n64": {"en": "hidden theme: N64", "de": "geheimes Theme: N64"},
    "secret_origin_theme_ps1": {"en": "Origin: Aladdin (PS1)",
                                "de": "Herkunft: Aladdin (PS1)"},
    "secret_name_theme_ps1": {"en": "hidden theme: PS1", "de": "geheimes Theme: PS1"},
    "secret_origin_theme_megadrive": {"en": "Origin: Sonic 2 (Mega Drive) sound test code",
                                      "de": "Herkunft: Sonic 2 (Mega Drive) Sound-Test-Code"},
    "secret_name_theme_megadrive": {"en": "hidden theme: Mega Drive", "de": "geheimes Theme: Mega Drive"},
    "secret_origin_theme_sms": {"en": "Origin: Sonic Chaos (Master System) sound test code",
                                "de": "Herkunft: Sonic Chaos (Master System) Sound-Test-Code"},
    "secret_name_theme_sms": {"en": "hidden theme: Master System", "de": "geheimes Theme: Master System"},
    "secret_origin_theme_gamegear": {"en": "Origin: Sonic Chaos (Game Gear) sound test code",
                                     "de": "Herkunft: Sonic Chaos (Game Gear) Sound-Test-Code"},
    "secret_name_theme_gamegear": {"en": "hidden theme: Game Gear", "de": "geheimes Theme: Game Gear"},
    "secret_origin_theme_saturn": {"en": "Origin: Sonic Jam / Sonic 2 level select (Saturn)",
                                   "de": "Herkunft: Sonic Jam / Sonic 2 Level-Auswahl (Saturn)"},
    "secret_name_theme_saturn": {"en": "hidden theme: Saturn", "de": "geheimes Theme: Saturn"},
    "flourish_snes": {"en": "SUPER NINTENDO MODE", "de": "SUPER-NINTENDO-MODUS"},
    "flourish_gb": {"en": "GAME BOY MODE", "de": "GAME-BOY-MODUS"},
    "flourish_gbc": {"en": "GAME BOY COLOR MODE", "de": "GAME-BOY-COLOR-MODUS"},
    "flourish_n64": {"en": "N64 TURBO MODE", "de": "N64-TURBO-MODUS"},
    "flourish_ps1": {"en": "PLAYSTATION MODE", "de": "PLAYSTATION-MODUS"},
    "flourish_megadrive": {"en": "MEGA DRIVE MODE", "de": "MEGA-DRIVE-MODUS"},
    "flourish_sms": {"en": "MASTER SYSTEM MODE", "de": "MASTER-SYSTEM-MODUS"},
    "flourish_gamegear": {"en": "GAME GEAR MODE", "de": "GAME-GEAR-MODUS"},
    "flourish_saturn": {"en": "SATURN MODE", "de": "SATURN-MODUS"},
    "dev_room_title": {"en": "DEVELOPER ROOM", "de": "ENTWICKLERRAUM"},
    "dev_room_level": {"en": "Frontend level: %d of %d", "de": "Frontend-Level: %d von %d"},
    "dev_room_secrets": {"en": "Secrets found: %d of %d", "de": "Geheimnisse gefunden: %d von %d"},
    "dev_room_credits_1": {"en": "Built by Dragrem.",
                           "de": "Gebaut von Dragrem."},
    "dev_room_credits_2": {"en": "With contributions from TheRealSutefan and Dfense1980.",
                           "de": "Mit Beiträgen von TheRealSutefan und Dfense1980."},
    "dev_room_thanks": {"en": "Thanks for playing around with hidden things.",
                        "de": "Danke, dass du an geheimen Dingen herumprobierst."},
    "dev_room_bonus_message": {
        "en": "Thanks for looking closely!",
        "de": "Danke fürs genaue Hinschauen!"},
    "seasonal_xmas": {"en": "* Merry Christmas! *", "de": "* Frohe Weihnachten! *"},
    "seasonal_nye": {"en": "* Happy New Year! *", "de": "* Guten Rutsch! *"},
    "credits_title": {"en": "CREDITS", "de": "MITWIRKENDE"},
    "credits_creator_heading": {"en": "Created by", "de": "Erstellt von"},
    "credits_creator_entry": {"en": "Dragrem", "de": "Dragrem"},
    "credits_contrib_heading": {"en": "Contributions", "de": "Beiträge"},
    "credits_contrib_sutefan": {"en": "TheRealSutefan - patches, RA tools, bugfixes",
                                "de": "TheRealSutefan - Patches, RA-Werkzeuge, Bugfixes"},
    "credits_contrib_dfense": {"en": "Dfense1980 - contributions",
                               "de": "Dfense1980 - Mitwirkung"},
    "credits_contrib_dennsen": {"en": "Dennsen86 - streaming and testing",
                                "de": "Dennsen86 - Streaming und Testen"},
    "credits_thanks_heading": {"en": "Thanks", "de": "Danke"},
    "credits_thanks_entry": {"en": "To everyone playing, testing and reporting bugs.",
                             "de": "An alle, die spielen, testen und Fehler melden."},
    "trophy_room_title": {"en": "TROPHY ROOM", "de": "TROPHÄENRAUM"},
    "trophy_favorite_system": {"en": "Favorite system: %s",
                               "de": "Lieblingssystem: %s"},
    "trophy_top_game": {"en": "Most played: %s", "de": "Meistgespielt: %s"},
    "trophy_total_playtime": {"en": "Total playtime: %s",
                              "de": "Insgesamt gespielt: %s"},
    "trophy_launches": {"en": "Games launched: %d", "de": "Spiele gestartet: %d"},
    "trophy_systems": {"en": "Systems explored: %d",
                       "de": "Systeme ausprobiert: %d"},
    "trophy_achievements": {"en": "Achievements: %d of %d",
                            "de": "Erfolge: %d von %d"},
    "trophy_summary": {"en": "A retro gamer on %d systems, %d of %d achievements unlocked.",
                       "de": "Retro-Spieler(in) auf %d Systemen, %d von %d Erfolgen freigeschaltet."},
    "year_review_title": {"en": "YEAR IN REVIEW %s", "de": "JAHRESRÜCKBLICK %s"},
    "year_review_empty": {"en": "Nothing recorded for this year yet - keep playing!",
                          "de": "Für dieses Jahr noch nichts aufgezeichnet - einfach weiterspielen!"},
    "year_review_favorite_system": {"en": "Favorite system this year: %s",
                                    "de": "Lieblingssystem dieses Jahr: %s"},
    "year_review_top_game": {"en": "Most played this year: %s",
                             "de": "Meistgespielt dieses Jahr: %s"},
    "year_review_total_playtime": {"en": "Played this year: %s",
                                   "de": "Dieses Jahr gespielt: %s"},
    "year_review_launches": {"en": "Games launched: %d", "de": "Spiele gestartet: %d"},
    "year_review_games": {"en": "Different games: %d", "de": "Verschiedene Spiele: %d"},
    "year_review_systems": {"en": "Systems used: %d", "de": "Genutzte Systeme: %d"},
    "year_review_discovered": {"en": "Discovered this year: %d",
                               "de": "Dieses Jahr entdeckt: %d"},
    "year_review_summary": {"en": "Your %s: %d games, %d of them brand new discoveries.",
                            "de": "Dein %s: %d Spiele, davon %d ganz neu entdeckt."},
    "diary_title": {"en": "GAME DIARY", "de": "SPIELTAGEBUCH"},
    "diary_summary": {"en": "%d sessions in the last %d days",
                      "de": "%d Sitzungen in den letzten %d Tagen"},
    "diary_empty": {"en": "Nothing recorded yet - keep playing!",
                    "de": "Noch nichts aufgezeichnet - einfach weiterspielen!"},
    "diary_today": {"en": "Today", "de": "Heute"},
    "diary_yesterday": {"en": "Yesterday", "de": "Gestern"},
    "sys_diary_action": {"en": "Game diary", "de": "Spieltagebuch"},
    "sys_help_action": {"en": "Help / Overview", "de": "Hilfe / Übersicht"},
    "boot_default_title": {"en": "MISTER FRONTEND", "de": "MISTER FRONTEND"},
    "help_title": {"en": "HELP / OVERVIEW", "de": "HILFE / UEBERSICHT"},
    "help_section_nav": {"en": "Navigation", "de": "Navigation"},
    "help_nav_move_key": {"en": "Arrow keys", "de": "Pfeiltasten"},
    "help_nav_move_desc": {"en": "Move around", "de": "Bewegen"},
    "help_nav_ok_key": {"en": "OK / A", "de": "OK / A"},
    "help_nav_ok_desc": {"en": "Select, enter category/folder",
                         "de": "Auswählen, Kategorie/Ordner betreten"},
    "help_nav_back_key": {"en": "Back / B", "de": "Zurück / B"},
    "help_nav_back_desc": {"en": "One level back, at the top: exit dialog",
                           "de": "Eine Ebene zurück, ganz oben: Beenden-Dialog"},
    "help_nav_letter_key": {"en": "Letter key (keyboard)",
                            "de": "Buchstabentaste (Tastatur)"},
    "help_nav_letter_desc": {"en": "Jump to next entry with that letter",
                             "de": "Springt zum nächsten Eintrag mit diesem Buchstaben"},
    "help_nav_search_key": {"en": "/ or F2 (keyboard), Select+A (pad)",
                            "de": "/ oder F2 (Tastatur), Select+A (Pad)"},
    "help_nav_search_desc":
        {"en": "Search the game list, jumps to the first match. Up/down step through "
               "the matches, the bar counts them (3/17). Started from the pad "
               "an on-screen letter grid opens (A picks, B goes back, the OK field "
               "finishes)",
         "de": "Spieleliste durchsuchen, springt zum ersten Treffer. Hoch/runter "
               "blättert durch die Treffer, der Balken zählt sie mit (3/17). Vom Pad "
               "aus erscheint ein Buchstabenraster auf dem Bildschirm (A wählt, "
               "B zurück, das Feld OK beendet)"},
    # Build 114: F3/F4 waren die letzten unbelegten Funktionstasten.
    "help_nav_ends_key": {"en": "F3 / F4 (keyboard), Select+L / Select+R (pad)",
                          "de": "F3 / F4 (Tastatur), Select+L / Select+R (Pad)"},
    "help_nav_ends_desc": {"en": "Jump to the start / the end of the list",
                           "de": "An den Anfang / ans Ende der Liste springen"},
    "help_nav_select_key": {"en": "Select (pad)", "de": "Select (Pad)"},
    "help_nav_select_desc": {"en": "Shows the combos; held down it is the modifier "
                                   "for Select+A, Select+X and Select+L/R "
                                   "(B goes back)",
                             "de": "Zeigt die Kombinationen an; GEHALTEN ist Select "
                                   "der Umschalter für Select+A, Select+X und "
                                   "Select+L/R (zurück geht B)"},
    "help_section_list": {"en": "In the game list", "de": "In der Spieleliste"},
    "help_list_showcase_key": {"en": "F6 (keyboard), Select+X (pad)",
                               "de": "F6 (Tastatur), Select+X (Pad)"},
    "help_list_showcase_desc": {"en": "RA achievement showcase for the selected game",
                                "de": "RA-Erfolgs-Vitrine für das markierte Spiel"},
    "help_list_completed_key": {"en": "F7 (keyboard only)",
                                "de": "F7 (nur Tastatur)"},
    "help_list_completed_desc": {"en": "Toggle completed status",
                                 "de": "Durchgespielt-Status umschalten"},
    "help_list_favorite_key": {"en": "F8 / L2 or R2", "de": "F8 / L2 oder R2"},
    "help_list_favorite_desc": {"en": "Toggle favorite", "de": "Favorit umschalten"},
    # NEU (Build 122): die Ansichts-Umschaltung gehoert genau hierhin -
    # "In der Spieleliste" ist die einzige Stelle, an der sie wirkt.
    "help_list_ansicht_key": {"en": "F10 / Select+Y (pad)",
                              "de": "F10 / Select+Y (Pad)"},
    "help_list_ansicht_desc": {
        "en": "Switch view: list, grid, gallery (main page too)",
        "de": "Ansicht wechseln: Liste, Raster, Galerie (auch Hauptseite)"},
    "help_list_random_key": {"en": "F11 (keyboard only)",
                             "de": "F11 (nur Tastatur)"},
    "help_list_random_desc": {"en": "Start a random game across all systems",
                              "de": "Zufälliges Spiel über alle Systeme starten"},
    "help_section_menu": {"en": "Special entries in the main menu",
                          "de": "Besondere Einträge im Hauptmenü"},
    "help_menu_continue_key": {"en": "Continue playing", "de": "Weiterspielen"},
    "help_menu_continue_desc": {"en": "Your last unfinished game",
                                "de": "Dein zuletzt offenes Spiel"},
    "help_menu_collections_key": {"en": "Collections", "de": "Sammlungen"},
    "help_menu_collections_desc": {"en": "Automatic groupings",
                                   "de": "Automatische Gruppierungen"},
    "help_menu_hunter_key": {"en": "RA Achievement Hunter", "de": "RA-Erfolgsjäger"},
    "help_menu_hunter_desc": {"en": "Open achievements in your library",
                              "de": "Offene Erfolge in deiner Bibliothek"},
    "help_section_system": {"en": "System menu", "de": "System-Menü"},
    "help_system_stats_key": {"en": "Statistics & achievements",
                              "de": "Statistiken & Erfolge"},
    "help_system_stats_desc": {"en": "Top-10 lists, trophy room, year in review, diary",
                               "de": "Top-10-Listen, Trophäenraum, Jahresrückblick, Spieltagebuch"},
    "help_system_secrets_key": {"en": "Secrets", "de": "Geheimnisse"},
    "help_system_secrets_desc": {"en": "Hidden things to discover for yourself",
                                 "de": "Verstecktes, das du selbst entdecken kannst"},
    "help_system_credits_key": {"en": "Credits", "de": "Mitwirkende"},
    "help_system_credits_desc": {"en": "Who made this", "de": "Wer das gebaut hat"},
    # NEU (Build 88): die beiden Nachlade-Punkte gab es bis dahin nur im
    # Ersteinrichtungs-Assistenten - entsprechend wusste auch niemand,
    # dass man sie spaeter noch braucht.
    "help_system_downloads_key": {"en": "Maintenance", "de": "Wartung"},
    "help_system_downloads_desc":
        {"en": "Download box art and game info later on, rescan the game list, "
               "open the MiSTer OSD",
         "de": "Boxarts und Spieledaten nachträglich laden, Spieleliste neu "
               "einlesen, MiSTer-OSD öffnen"},
    "help_section_playing": {"en": "While playing", "de": "Während des Spielens"},
    # KORRIGIERT (Build 88, Nutzer-Rueckmeldung: "die Hilfe muss eh
    # ueberarbeitet werden, da stehen Sachen drin die sind nicht mehr
    # aktuell"). Hier stand "Esc oder F10 (ca. 0,6s halten)" - F10 ist
    # seit Build 77 ERSATZLOS ENTFALLEN (es lief ueber die evdev-Ebene,
    # die MiSTer waehrend eines Cores sperrt, und die HID-Pruefung dafuer
    # verglich versehentlich F11). F1 hat die Aufgabe uebernommen und
    # stand bisher gar nicht in der Hilfe.
    "help_playing_exit_key": {"en": "F1 (keyboard)", "de": "F1 (Tastatur)"},
    "help_playing_exit_desc": {"en": "Back to the menu immediately",
                               "de": "Sofort zurück ins Menü"},
    "help_playing_exit_esc_key": {"en": "Esc (keyboard, hold ~0.6s)",
                                  "de": "Esc (Tastatur, ca. 0,6s halten)"},
    "help_playing_exit_esc_desc":
        {"en": "Also back to the menu - Esc keeps the hold time because many "
               "games use Esc themselves for their own pause menu",
         "de": "Ebenfalls zurück ins Menü - Esc behält die Haltezeit, weil viele "
               "Spiele Esc selbst für ihr eigenes Pausenmenü benutzen"},
    # EHRLICH GEMACHT (Build 88): hier stand "Start + Select (Pad, ca.
    # 0,8s halten) - Sofort zurueck ins Menue", als waere das ein
    # gleichwertiger Weg. Ist es nicht. MiSTer sperrt waehrend eines
    # laufenden Cores die evdev-Ebene exklusiv; bei einer Tastatur liegt
    # darunter noch der hidraw-Kanal, bei den bisher getesteten
    # Controller-Empfaengern kam dort aber nichts an. Der Code-Zweig
    # bleibt als Absicherung bestehen, falls es auf anderer Hardware
    # doch geht - die Hilfe darf es aber nicht als sichere Zusage
    # verkaufen.
    "help_playing_exit_pad_key": {"en": "Start + Select (pad, hold ~0.8s)",
                                  "de": "Start + Select (Pad, ca. 0,8s halten)"},
    "help_playing_exit_pad_desc":
        {"en": "Only works if MiSTer does not lock the controller - on the pads "
               "tested so far it does. The reliable way out is the keyboard.",
         "de": "Funktioniert nur, wenn MiSTer den Controller nicht sperrt - bei "
               "den bisher getesteten Pads tut es das. Verlässlich ist der "
               "Ausstieg über die Tastatur."},
    # KORRIGIERT (Build 88): stand als "ca. 0,6s halten" drin. Seit
    # Build 75 ist RESET_HOLD = 0.0, der Reset loest also beim ersten
    # erkannten Tastendruck aus - genau so war es damals gewuenscht.
    "help_playing_reset_key": {"en": "F5 (keyboard)",
                               "de": "F5 (Tastatur)"},
    "help_playing_reset_desc": {"en": "Reset the running core, without reloading it "
                                       "(experimental, RA progress is kept)",
                                "de": "Laufenden Core zurücksetzen, ohne ihn neu zu laden "
                                      "(experimentell, RA-Fortschritt bleibt erhalten)"},
    "help_section_general": {"en": "Anywhere", "de": "Überall"},
    "help_general_music_key": {"en": "Y (pad) / F5 (keyboard)",
                               "de": "Y (Pad) / F5 (Tastatur)"},
    "help_general_music_desc": {"en": "Next music track (menu only)",
                                "de": "Nächster Musiktitel (nur im Menü)"},
    "help_general_osd_key": {"en": "F12 / Mode (pad)", "de": "F12 / Mode-Taste (Pad)"},
    "help_general_osd_desc": {"en": "Open the MiSTer OSD (joystick setup, settings)",
                              "de": "MiSTer-OSD öffnen (Joystick-Definition, Einstellungen)"},
    # ENTFERNT (Nutzer-Rueckmeldung: "unter System/Hilfe steht ganz
    # unten noch F10/X zurueck ins Frontend, das muss raus, das
    # funktioniert ja garnicht"): "help_general_osd_back"-Eintrag aus
    # der Hilfe-Uebersicht (draw_help_screen()) entfernt - die
    # Uebersetzungen selbst bleiben absichtlich NICHT hier stehen
    # (nirgends mehr referenziert), um niemanden ueber eine tote
    # Uebersetzung zu verwirren, falls der Eintrag spaeter versehentlich
    # wieder aufgenommen wuerde.
    "sys_trophy_action": {"en": "My trophy room", "de": "Mein Trophäenraum"},
    "sys_year_review_action": {"en": "Year in review", "de": "Jahresrückblick"},
    "sys_secrets_action": {"en": "Secrets", "de": "Geheimnisse"},
    "sys_credits_action": {"en": "Credits", "de": "Mitwirkende"},
    "sys_crt_test_action": {"en": "CRT test pattern", "de": "CRT-Testbild"},
    "ra_showcase_title": {"en": "RA ACHIEVEMENTS - %s", "de": "RA-ERFOLGE - %s"},
    "ra_showcase_loading": {"en": "Loading achievements ...",
                            "de": "Erfolge werden geladen ..."},
    "ra_showcase_error": {"en": "Could not load achievements (no network/timeout)",
                          "de": "Erfolge konnten nicht geladen werden (kein Netz/Zeitlimit)"},
    "ra_showcase_empty": {"en": "No achievements found for this game",
                          "de": "Keine Erfolge für dieses Spiel gefunden"},
    "ra_showcase_none": {"en": "No RetroAchievements data for this game",
                         "de": "Keine RetroAchievements-Daten für dieses Spiel"},
    "ra_showcase_not_setup": {"en": "RetroAchievements not set up (see README)",
                              "de": "RetroAchievements nicht eingerichtet (siehe README)"},
    "sys_milestones_action": {"en": "My achievements", "de": "Meine Erfolge"},
    "sys_ra_setup": {"en": "RetroAchievements: not set up",
                     "de": "RetroAchievements: nicht eingerichtet"},
    "sys_ra_configured": {"en": "RetroAchievements: %s (reload)",
                          "de": "RetroAchievements: %s (neu laden)"},
    # NEU (Nutzerwunsch: RetroAchievements aus dem System-Menue heraus
    # an-/ausschalten koennen, ohne die Zugangsdaten per SSH loeschen zu
    # muessen) - gleiches "AN -> ausschalten"/"AUS -> einschalten"-Muster
    # wie die uebrigen Ein/Aus-Menuepunkte (siehe z.B. sys_fast_scroll_on).
    "sys_ra_toggle_on": {"en": "RetroAchievements: ON -> turn off (progress/badges/lists pause, RA-capable cores still launch normally)",
                         "de": "RetroAchievements: AN -> ausschalten (Fortschritt/Abzeichen/Listen pausieren, RA-fähige Cores starten weiterhin normal)"},
    "sys_ra_toggle_off": {"en": "RetroAchievements: OFF -> turn on",
                          "de": "RetroAchievements: AUS -> einschalten"},

    # NEU (Build 95, Nutzerwunsch: "Sute hat eine neue Main MiSTer
    # gebaut, die hat nun RA Settings - koennen wir das mit ins Frontend
    # einbauen?" und spaeter: "Das haette ich auch gerne bei uns im
    # Frontend, einstellbar unter System und dann RetroAchievements").
    #
    # Die Beschriftungen sind bewusst NICHT die englischen Kuerzel aus
    # dem OSD ("Multiline Description"), sondern ausgeschrieben: wer im
    # Wohnzimmer sitzt, soll lesen koennen, was der Schalter tut. Die
    # Reihenfolge im Menue entspricht dagegen genau dem OSD, damit sich
    # niemand umgewoehnen muss, der beides benutzt.
    # Kurzform AN/AUS. Die uebrigen Ein/Aus-Menuepunkte im System-Menue
    # tragen jeweils einen ganzen Satz ("AN -> ausschalten (...)"), weil
    # sie einzeln in einer langen Liste stehen und sich selbst erklaeren
    # muessen. Auf dem RA-Bildschirm stehen neun Schalter untereinander
    # in einer Spalte - dort waeren ganze Saetze nur Rauschen.
    # NEU (Build 113): Bildrand/Bildlage, einstellbar im Menue statt
    # als feste Zahl im Quelltext. Der Zusatz nennt ausdruecklich die
    # Roehre - auf HDMI braucht das praktisch niemand.
    "sys_overscan_x": {
        "en": "Side margin: %d %% -> next (for CRTs that cut off "
              "left/right)",
        "de": "Rand seitlich: %d %% -> weiter (für Röhren, die links/"
              "rechts abschneiden)"},
    "sys_overscan_y": {
        "en": "Top/bottom margin: %d %% -> next (for CRTs that cut off "
              "top/bottom)",
        "de": "Rand oben/unten: %d %% -> weiter (für Röhren, die oben/"
              "unten abschneiden)"},
    "ra_on": {"en": "ON", "de": "AN"},
    "ra_off": {"en": "OFF", "de": "AUS"},
    "sys_ra_settings": {"en": "Popups & display (MiSTer RA settings)",
                        "de": "Popups & Anzeige (MiSTer-RA-Einstellungen)"},
    "sys_ra_settings_missing": {
        "en": "Popups & display: RA not set up in MiSTer itself",
        "de": "Popups & Anzeige: RA in MiSTer selbst nicht eingerichtet"},
    "ra_set_title": {"en": "RETROACHIEVEMENTS - POPUPS",
                     "de": "RETROACHIEVEMENTS - POPUPS"},
    "ra_set_group_popups": {"en": "Popups", "de": "Popups"},
    "ra_set_group_list": {"en": "List", "de": "Liste"},
    "ra_set_group_pos": {"en": "Position", "de": "Position"},
    "ra_set_challenge_start": {"en": "Challenge start popup",
                               "de": "Popup bei Herausforderungs-Start"},
    "ra_set_challenge_end": {"en": "Challenge end popup",
                             "de": "Popup bei Herausforderungs-Ende"},
    "ra_set_progress": {"en": "Progress popups",
                        "de": "Fortschritts-Popups"},
    "ra_set_progress_name": {"en": "Show name in progress popup",
                             "de": "Name im Fortschritts-Popup"},
    "ra_set_lb_updates": {"en": "Leaderboard updates",
                          "de": "Bestenlisten-Aktualisierungen"},
    "ra_set_lb_submission": {"en": "Leaderboard submission",
                             "de": "Bestenlisten-Eintrag"},
    "ra_set_multiline": {"en": "Multi-line description",
                         "de": "Beschreibung mehrzeilig"},
    "ra_set_list_ticker": {"en": "Scrolling description in list",
                           "de": "Laufschrift in der Erfolgsliste"},
    "ra_set_list_hotkey": {"en": "Open list with Menu+Y",
                           "de": "Erfolgsliste mit Menü+Y öffnen"},
    "ra_set_position": {"en": "Popup position: %s",
                        "de": "Popup-Position: %s"},
    "ra_set_pos_left": {"en": "left", "de": "links"},
    "ra_set_pos_center": {"en": "centre", "de": "mittig"},
    "ra_set_pos_right": {"en": "right", "de": "rechts"},
    "ra_set_offsets": {"en": "Fine-tune popup position ...",
                       "de": "Popup-Position feinjustieren ..."},
    "ra_set_offsets_sys": {"en": "Fine-tune popup position for %s ...",
                           "de": "Popup-Position für %s feinjustieren ..."},
    "ra_set_h": {"en": "Horizontal", "de": "Waagerecht"},
    "ra_set_v": {"en": "Vertical", "de": "Senkrecht"},
    "ra_set_scope_global": {"en": "applies to all cores",
                            "de": "gilt für alle Cores"},
    "ra_set_scope_all": {"en": "all cores", "de": "alle Cores"},
    "ra_set_scope_core": {"en": "applies to the %s core",
                          "de": "gilt für den %s-Core"},
    # Wenn mehrere Systeme denselben Core benutzen (Game Boy und Game
    # Boy Color teilen sich "Gameboy", SNES und SMW Hacks teilen sich
    # "SNES"), gilt die Einstellung zwangslaeufig fuer alle davon. Das
    # ist keine Eigenart unserer Umsetzung, sondern die Art, wie MiSTer
    # die Werte ablegt - also sagen wir es dazu, statt es zu verstecken.
    "ra_set_scope_shared": {"en": "applies to the %s core - also used by: %s",
                            "de": "gilt für den %s-Core – den nutzt auch: %s"},
    # Bewusst SEHR kurz: die Marke haengt rechts hinter dem Wert, und
    # dort ist auf CRT (34 Zeichen Gesamtbreite) fast kein Platz. Der
    # ausgeschriebene Satz stand hier zuerst und liess auf CRT vom Wert
    # selbst nichts mehr uebrig ("+0  (vom globalen~").
    "ra_set_inherited": {"en": "inherited", "de": "geerbt"},
    "ra_set_own": {"en": "own", "de": "eigen"},
    "ra_set_reset": {"en": "Back to the global values",
                     "de": "Zurück auf die globalen Werte"},
    "ra_set_scope_label": {"en": "Applies to", "de": "Gilt für"},
    "ra_set_hint": {"en": "Up/Down: choose   Left/Right: change   "
                          "Back: done",
                    "de": "Hoch/Runter: wählen   Links/Rechts: ändern   "
                          "Zurück: fertig"},
    # Kurzfassung fuer CRT - die lange Zeile passt bei 320 Bildpunkten
    # Breite nicht und wurde mitten im Wort abgeschnitten.
    "ra_set_hint_kurz": {"en": "Left/Right: change   Back: done",
                         "de": "Links/Rechts: ändern   Zurück: fertig"},
    # Und noch eine Stufe kuerzer - bei 320 Bildpunkten Breite bleiben
    # nach Overscan nur 34 Zeichen, da passt auch die mittlere nicht.
    "ra_set_hint_minimal": {"en": "L/R: change   B: back",
                            "de": "L/R: ändern   B: zurück"},
    "ra_set_preview": {"en": "Achievement unlocked", "de": "Erfolg freigeschaltet"},
    "ra_set_preview_sub": {"en": "Preview - this is where the popup sits",
                           "de": "Vorschau – hier sitzt das Popup"},
    "ra_set_takes_effect": {"en": "Takes effect the next time a core starts.",
                            "de": "Wirkt ab dem nächsten Core-Start."},
    "ra_set_write_failed": {"en": "Could not save - is the SD card write-protected?",
                            "de": "Konnte nicht gespeichert werden – SD-Karte schreibgeschützt?"},
    "core_choice_title": {"en": "%s - CHOOSE CORE",
                          "de": "%s - CORE WÄHLEN"},
    "core_choice_normal": {"en": "Standard core",
                           "de": "Standard-Core"},
    "core_choice_ra": {"en": "RetroAchievements core",
                       "de": "RetroAchievements-Core"},
    "core_choice_hint": {"en": "Up/Down to choose, OK to confirm",
                         "de": "Hoch/Runter wählen, OK bestätigen"},
    "wot_title": {"en": "ZUFALLS-ZOCK", "de": "ZUFALLS-ZOCK"},
    "wot_hint": {"en": "Up/Down: select   OK: confirm   ESC: back",
                 "de": "Hoch/Runter: wählen   OK: bestätigen   ESC: zurück"},
    # GEAENDERT (Build 144): bis Build 143 bekamen zwei voellig verschiedene
    # Lagen dieselbe Meldung - "gar keine Spiele gescannt" und "alle Spiele
    # waren schon einmal dran". Im ersten Fall ist ein Scan faellig, im
    # zweiten hilft nur das Zuruecksetzen der gespielt-Liste. Deshalb jetzt
    # getrennte Texte, und im zweiten Fall eine Wahl statt einer Sackgasse.
    "wot_pool_empty": {
        "en": "All %d games have been drawn already. The list remembers "
              "every start.",
        "de": "Alle %d Spiele waren schon dran. Die Liste merkt sich "
              "jeden Start."},
    "wot_pool_keine_spiele": {
        "en": "No games found. Scan the game list first (System - Rescan game list).",
        "de": "Keine Spiele gefunden. Bitte zuerst die Spieleliste einlesen "
              "(System - Spieleliste neu einlesen)."},
    "wot_reset_option": {
        "en": "Reset list", "de": "Liste zurücksetzen"},
    "wot_reset_done": {
        "en": "List reset - all %d games are back in the pool.",
        "de": "Liste zurückgesetzt - alle %d Spiele sind wieder dabei."},
    "wot_no_rom_match": {
        "en": "Drew several games but found no matching ROM file for any of them.",
        "de": "Mehrere Spiele gezogen, aber für keins eine passende ROM-Datei gefunden."},
    "wot_option_start": {"en": "Start", "de": "Starten"},
    "wot_option_redraw": {"en": "Draw again", "de": "Neu ziehen"},
    "wot_option_back": {"en": "Back", "de": "Zurück"},
    "wot_checking": {"en": "Checking games... %d/%d",
                     "de": "Prüfe Spiele... %d/%d"},
    # NEU (Build 145): den Rechenauftrag an einen PC abgeben.
    "sys_thumb_auftrag_action": {
        "en": "Write thumbnail job for PC",
        "de": "Miniaturen-Auftrag für PC schreiben"},
    "thumb_auftrag_done": {
        "en": "Job written: %d thumbnails. Now run the PC tool.",
        "de": "Auftrag geschrieben: %d Miniaturen. Jetzt das PC-Programm starten."},
    "thumb_auftrag_failed": {
        "en": "Could not write the job file.",
        "de": "Auftragsdatei konnte nicht geschrieben werden."},
    "sys_wot_action": {"en": "Zufalls-Zock - draw a game", "de": "Zufalls-Zock - Spiel ziehen"},
    "ra_setup_title": {"en": "RETROACHIEVEMENTS SETUP",
                       "de": "RETROACHIEVEMENTS EINRICHTEN"},
    "ra_setup_line1": {"en": "Create this file via SSH/text editor:",
                       "de": "Diese Datei per SSH/Texteditor anlegen:"},
    "ra_setup_line2": {"en": "Line 1: your RA username",
                       "de": "Zeile 1: dein RA-Benutzername"},
    "ra_setup_line3": {"en": "Line 2: your RA web API key (from your",
                       "de": "Zeile 2: dein RA-Web-API-Schlüssel (aus"},
    "ra_setup_line4": {"en": "RA control panel, section \"Keys\")",
                       "de": "deinem RA-Kontrollbereich, Abschnitt \"Keys\")"},

    # Ersteinrichtungs-Assistent (Nutzerwunsch: vereinfachte
    # Installation, einmalig durch alle wichtigen Schritte fuehren).
    "wizard_step_title": {"en": "Setup %d/%d - %s", "de": "Einrichtung %d/%d - %s"},
    "wizard_step_language": {"en": "Language", "de": "Sprache"},
    "wizard_step_video": {"en": "Display", "de": "Bildschirm"},
    "wizard_step_timezone": {"en": "Time zone", "de": "Zeitzone"},
    "wizard_step_ra": {"en": "RetroAchievements", "de": "RetroAchievements"},
    "wizard_step_boxart": {"en": "Box art", "de": "Boxart"},
    "wizard_step_gameinfo": {"en": "Game info", "de": "Gameinfos"},
    "wizard_step_scan": {"en": "Finding your games", "de": "Spiele werden gesucht"},
    "wizard_step_esc_hint": {"en": "Good to know", "de": "Gut zu wissen"},
    "wizard_choice_hint": {"en": "Up/Down: select   OK: confirm   ESC: cancel setup",
                           "de": "Hoch/Runter: wählen   OK: bestätigen   ESC: Einrichtung abbrechen"},
    "wizard_skip_hint": {"en": "OK: continue   ESC: skip this step",
                         "de": "OK: weiter   ESC: diesen Schritt überspringen"},
    "wizard_continue_hint": {"en": "Any key: continue", "de": "Beliebige Taste: weiter"},
    "wizard_video_reboot_note": {
        "en": "Saved - takes effect after the next restart. Setup continues now.",
        "de": "Gespeichert - wird erst nach dem nächsten Neustart aktiv. Die Einrichtung geht jetzt weiter."},
    "wizard_timezone_current": {"en": "Current: %s -> change", "de": "Aktuell: %s -> ändern"},
    "wizard_continue_option": {"en": "Continue", "de": "Weiter"},
    "wizard_download_now": {"en": "Download now", "de": "Jetzt herunterladen"},
    "wizard_download_skip": {"en": "Skip (can be done later from Scripts)",
                             "de": "Überspringen (später jederzeit über Scripts möglich)"},
    "wizard_scan_patience": {
        "en": "If you have a lot of ROMs, this can take a while - that's normal, not frozen.",
        "de": "Bei vielen ROMs kann das etwas dauern - das ist normal, kein Einfrieren."},
    "wizard_scan_progress": {"en": "%d/%d - %s", "de": "%d/%d - %s"},
    "wizard_scan_done": {"en": "Done: %d systems, %d games found.",
                         "de": "Fertig: %d Systeme, %d Spiele gefunden."},
    "wizard_esc_hint_1": {
        "en": "To exit a running game, hold Esc on a connected keyboard.",
        "de": "Um ein laufendes Spiel zu verlassen: Esc auf einer angeschlossenen Tastatur halten."},
    "wizard_esc_hint_2": {
        "en": "Needs a keyboard - a gamepad alone can't do this.",
        "de": "Braucht eine Tastatur - mit einem Controller allein geht das nicht."},
    "sys_setup_wizard": {"en": "Run setup wizard again", "de": "Einrichtung erneut starten"},

    "ra_reload_done": {"en": "RetroAchievements: %d games matched",
                       "de": "RetroAchievements: %d Spiele zugeordnet"},
    "ra_reload_failed": {"en": "RetroAchievements: could not reach server",
                         "de": "RetroAchievements: Server nicht erreichbar"},
    "top10_time_action": {"en": "Top 10: most played",
                          "de": "Top 10: meistgespielt"},
    "top10_launches_action": {"en": "Top 10: most launched",
                              "de": "Top 10: meistgestartet"},
    "top10_time_title": {"en": "TOP 10 - MOST PLAYED",
                         "de": "TOP 10 - MEISTGESPIELT"},
    "top10_launches_title": {"en": "TOP 10 - MOST LAUNCHED",
                             "de": "TOP 10 - MEISTGESTARTET"},
    "top10_empty": {"en": "No games played yet",
                    "de": "Noch keine Spiele gespielt"},
    "top10_launches_count": {"en": "%dx", "de": "%dx"},
    "top10_scroll_hint": {"en": "%d-%d of %d - Up/Down to scroll",
                          "de": "%d-%d von %d - Hoch/Runter zum Scrollen"},
    "no_artwork_1":    {"en": "no",      "de": "kein"},
    "no_artwork_2":    {"en": "artwork", "de": "Artwork"},
    "sys_group_ra": {"en": "RetroAchievements", "de": "RetroAchievements"},
    "sys_group_stats": {"en": "Statistics & achievements", "de": "Statistiken & Erfolge"},
    "sys_group_display": {"en": "Display & sound", "de": "Anzeige & Sound"},
    "sys_group_behavior": {"en": "Options", "de": "Optionen"},
    "sys_group_input": {"en": "Input & language", "de": "Eingabe & Sprache"},
    "sys_group_info": {"en": "Info", "de": "Info"},
    "sys_group_maintenance": {"en": "Maintenance", "de": "Wartung"},
    "sys_osd":         {"en": "Open MiSTer OSD (Settings/Buttons)",
                        "de": "MiSTer-OSD öffnen (Settings/Buttons)"},
    "sys_video_crt":   {"en": "Menu video: CRT -> switch to HDMI",
                        "de": "Menü-Video: CRT -> auf HDMI wechseln"},
    "sys_video_hdmi":  {"en": "Menu video: HDMI -> switch to CRT",
                        "de": "Menü-Video: HDMI -> auf CRT wechseln"},
    "sys_video_suffix":{"en": " (reboot)", "de": " (Neustart)"},
    # NEUES FEATURE (CRT-Sicherheitsnetz, siehe mark_crt_pending_confirm()
    # in fe/settings.py): kurz genug gehalten, um auch auf CRT (320px
    # Breite) sicher in eine Zeile zu passen.
    "crt_pending_notice": {"en": "CRT active - else HDMI in %ds",
                           "de": "CRT aktiv - sonst HDMI in %ds"},
    "sys_music_on":    {"en": "Music: On -> turn off", "de": "Musik: an -> ausschalten"},
    "sys_music_off":   {"en": "Music: Off -> turn on", "de": "Musik: aus -> einschalten"},
    "sys_music_source": {"en": "Music source: %s", "de": "Musik-Quelle: %s"},
    "sys_volume": {"en": "Volume: %d%%", "de": "Lautstärke: %d%%"},
    "sys_language":    {"en": "Language: English -> switch to German",
                        "de": "Sprache: Deutsch -> auf Englisch wechseln"},
    "sys_configure_buttons": {"en": "Configure buttons",
                              "de": "Tastenbelegung anpassen"},
    "sys_reset_buttons":     {"en": "Reset to default buttons",
                              "de": "Auf Standardbelegung zurücksetzen"},
    "sys_curated_on":  {"en": "Curated list (DB-matched only): ON -> turn off",
                        "de": "Kuratierte Liste (nur DB-Treffer): AN -> ausschalten"},
    "sys_curated_off": {"en": "Curated list (DB-matched only): OFF -> turn on",
                        "de": "Kuratierte Liste (nur DB-Treffer): AUS -> einschalten"},
    "sys_attract_on":  {"en": "Attract mode (screensaver): ON -> turn off",
                        "de": "Attract-Modus (Bildschirmschoner): AN -> ausschalten"},
    "sys_attract_off": {"en": "Attract mode (screensaver): OFF -> turn on",
                        "de": "Attract-Modus (Bildschirmschoner): AUS -> einschalten"},
    "sys_attract_delay": {"en": "Attract mode delay: %s -> next",
                          "de": "Attract-Modus Verzögerung: %s -> nächste"},
    "sys_theme": {"en": "Color theme: %s -> next",
                  "de": "Farbschema: %s -> nächstes"},
    "sys_timezone": {"en": "Timezone: %s -> next",
                      "de": "Zeitzone: %s -> nächste"},
    "sys_network_wait_off": {"en": "Wait for NAS/network at boot: OFF -> turn on",
                             "de": "Beim Start auf NAS/Netzwerk warten: AUS -> einschalten"},
    "sys_network_wait_on": {"en": "Wait for NAS/network at boot: ON -> turn off",
                            "de": "Beim Start auf NAS/Netzwerk warten: AN -> ausschalten"},
    "sys_network_wait_auto_hint": {"en": "(auto-detected)",
                                   "de": "(automatisch erkannt)"},
    "sys_swap_ok_back_off": {"en": "Swap Confirm/Cancel: OFF -> turn on",
                             "de": "Bestätigen/Abbrechen vertauschen: AUS -> einschalten"},
    "sys_swap_ok_back_on": {"en": "Swap Confirm/Cancel: ON -> turn off",
                            "de": "Bestätigen/Abbrechen vertauschen: AN -> ausschalten"},
    "sys_sfx_on": {"en": "Navigation sounds: ON -> turn off",
                   "de": "Navigations-Soundeffekte: AN -> ausschalten"},
    "sys_sfx_off": {"en": "Navigation sounds: OFF -> turn on",
                    "de": "Navigations-Soundeffekte: AUS -> einschalten"},
    "sys_dragend_logo_on": {"en": "Boot logo: Dragend -> switch to plain",
                            "de": "Boot-Logo: Dragend -> auf neutral wechseln"},
    "sys_dragend_logo_off": {"en": "Boot logo: plain -> switch to Dragend",
                             "de": "Boot-Logo: neutral -> auf Dragend wechseln"},
    # Build 119: waehrend auf eine noch anlaufende USB-Platte gewartet
    # wird. Der Hinweis nennt den Grund, damit niemand den Stecker
    # zieht, weil er einen Absturz vermutet.
    "warte_laufwerk": {
        "en": "Waiting for the USB drive ...",
        "de": "Warte auf das USB-Laufwerk ..."},
    "warte_laufwerk_hinweis": {
        "en": "Your games are on it. Spinning up takes a moment after a "
              "cold start.",
        "de": "Dort liegen deine Spiele. Nach einem Kaltstart braucht "
              "das Anlaufen einen Moment."},
    # Build 115. Bewusst ohne den Pfad im Text - der interessiert
    # niemanden, der das Menue bedient; wichtig ist, was der Schalter
    # bewirkt und dass eigenes Artwork Vorrang behaelt.
    "sys_fremdquellen_on": {
        "en": "Foreign artwork/data: ON -> turn off (fills gaps from the "
              "MiSTer docs database, never replaces your own)",
        "de": "Fremdes Artwork/Daten: AN -> ausschalten (füllt Lücken aus der "
              "MiSTer-docs-Datenbank, ersetzt nie eigenes)"},
    "sys_fremdquellen_off": {
        "en": "Foreign artwork/data: OFF -> turn on (covers and game data "
              "from /media/fat/docs, if installed)",
        "de": "Fremdes Artwork/Daten: AUS -> einschalten (Cover und Spieledaten "
              "aus /media/fat/docs, falls vorhanden)"},
    # NEU (Build 122): Ansicht der Spieleliste. Der Menuepunkt zeigt,
    # was gerade eingestellt ist, und schaltet eine Stufe weiter - genau
    # wie der Bildrand darueber. Die Taste steht mit im Text, sonst
    # findet sie niemand.
    "sys_ansicht": {
        "en": "Game list view: %s -> next (F10, or Select+Y on the pad, "
              "switches live)",
        "de": "Ansicht Spieleliste: %s -> weiter (F10, am Pad Select+Y, "
              "schaltet sofort um)"},
    "sys_ansicht_haupt": {
        "en": "Main page view: %s -> next (F10 on the main page)",
        "de": "Ansicht Hauptseite: %s -> weiter (F10 auf der Hauptseite)"},
    "ansicht_umgeschaltet": {"en": "View: %s", "de": "Ansicht: %s"},
    "ansicht_nur_spieleliste": {
        "en": "No covers here - the view stays a list",
        "de": "Hier gibt es keine Cover - die Ansicht bleibt eine Liste"},
    # NEUES FEATURE (Build 142): Listenfilter, siehe fe/filter.py.
    # NEUES FEATURE (Build 143): JPEG-Arbeitskopien beim Vorbereiten.
    "sys_arbeitskopien_on": {
        "en": "JPEG working copies: ON -> turn off (created while "
              "preparing thumbnails, makes PNG covers ~5x faster)",
        "de": "JPEG-Arbeitskopien: AN -> ausschalten (entstehen beim "
              "Miniaturen-Vorbereiten, machen PNG-Cover ~5x schneller)"},
    "sys_arbeitskopien_off": {
        "en": "JPEG working copies: OFF -> turn on (writes a .jpg next "
              "to each PNG cover while preparing thumbnails)",
        "de": "JPEG-Arbeitskopien: AUS -> einschalten (legt beim "
              "Miniaturen-Vorbereiten je PNG-Cover eine .jpg daneben)"},
    "filter_titel": {"en": "FILTER", "de": "FILTER"},
    "filter_merken": {"en": "Save as category",
                      "de": "Als Kategorie merken"},
    "filter_vergessen": {"en": "Remove this category",
                         "de": "Diese Kategorie entfernen"},
    "filter_gemerkt": {"en": "Saved - now in the main menu",
                       "de": "Gemerkt - steht jetzt im Hauptmenü"},
    "filter_genre": {"en": "Genre", "de": "Genre"},
    "filter_jahr": {"en": "Year", "de": "Jahr"},
    "filter_spieler": {"en": "Players", "de": "Spieler"},
    "filter_entwickler": {"en": "Developer", "de": "Entwickler"},
    "filter_alle": {"en": "all", "de": "alle"},
    "filter_leer": {"en": "(no data)", "de": "(keine Daten)"},
    "filter_spieler_min": {"en": "%d or more", "de": "ab %d"},
    "filter_treffer": {"en": "%d of %d games", "de": "%d von %d Spielen"},
    # Kurz genug, dass es auf der Roehre in zwei Zeilen passt (dort
    # sind es 40 Zeichen je Zeile) - siehe filter_bildschirm().
    "filter_hinweis": {
        "en": "L/R changes · OK applies · Back cancels · "
              "Favourite resets",
        "de": "L/R ändert · OK übernimmt · Zurück verwirft · "
              "Favorit setzt zurück"},
    "filter_keine_daten": {
        "en": "No game data for this category - nothing to filter",
        "de": "Keine Spieledaten für diese Kategorie - nichts zu filtern"},
    "ansicht_liste":   {"en": "list",    "de": "Liste"},
    "ansicht_raster":  {"en": "grid",    "de": "Raster"},
    "ansicht_galerie": {"en": "gallery", "de": "Galerie"},
    "sys_fast_scroll_on": {"en": "Fast scroll: ON -> turn off (may cause brief tearing while scrolling)",
                           "de": "Schnelles Scrollen: AN -> ausschalten (kann beim Scrollen kurz Bildrisse verursachen)"},
    "sys_fast_scroll_off": {"en": "Fast scroll: OFF -> turn on (trades a small tearing risk for less scroll delay)",
                            "de": "Schnelles Scrollen: AUS -> einschalten (etwas Bildriss-Risiko gegen kürzere Scroll-Verzögerung)"},
    # NEUES FEATURE (Build 138, Nutzerwunsch: "ich haette gerne mal
    # ausprobiert, ob wir in der Listenansicht das Cover sofort anzeigen
    # lassen"). Die Beschriftung nennt bewusst den Preis mit: waehrend
    # des Scrollens wird mehr gezeichnet.
    "sys_cover_sofort_on": {"en": "Cover while scrolling: ON -> turn off (list shows the cover only once you stop)",
                            "de": "Cover beim Scrollen: AN -> ausschalten (Liste zeigt das Cover erst im Stillstand)"},
    "sys_cover_sofort_off": {"en": "Cover while scrolling: OFF -> turn on (list shows the cover right away, like the gallery)",
                             "de": "Cover beim Scrollen: AUS -> einschalten (Liste zeigt das Cover sofort, wie die Galerie)"},
    # NEUES FEATURE (Nutzerwunsch: Schalter fuer die Framebuffer-Groesse):
    # drei Stufen statt AN/AUS, deshalb keine on/off-Paare wie sonst -
    # jede Zeile nennt den AKTUELLEN Wert und wohin der naechste
    # Tastendruck schaltet. Der Neustart-Hinweis steht bewusst in JEDER
    # der drei Zeilen: die Aenderung wirkt erst nach einem Neustart, und
    # ohne diesen Hinweis wirkt ein "es aendert sich ja nichts" wie ein
    # Fehler.
    "sys_fb_size_full": {
        "en": "Menu resolution: full -> switch to half (faster HDMI, softer picture, needs restart)",
        "de": "Menü-Auflösung: voll -> auf halb stellen (schnelleres HDMI, weicheres Bild, nach Neustart)"},
    "sys_fb_size_half": {
        "en": "Menu resolution: half -> switch to quarter (fastest, clearly blockier, needs restart)",
        "de": "Menü-Auflösung: halb -> auf viertel stellen (am schnellsten, deutlich klotziger, nach Neustart)"},
    "sys_fb_size_quarter": {
        "en": "Menu resolution: quarter -> back to full (original sharpness, needs restart)",
        "de": "Menü-Auflösung: viertel -> zurück auf voll (ursprüngliche Schärfe, nach Neustart)"},
    "sys_fb_size_changed": {
        "en": "Menu resolution changed - takes effect after the next restart. At a smaller size, covers are scaled down: the first view of each cover takes a moment, after that it comes from the cache.",
        "de": "Menü-Auflösung geändert - wirkt nach dem nächsten Neustart. Bei kleinerer Größe werden Cover verkleinert: das erste Betrachten dauert je Cover kurz, danach kommt es aus dem Zwischenspeicher."},
    "sys_fb_size_failed": {
        "en": "Could not write MiSTer.ini - menu resolution unchanged.",
        "de": "MiSTer.ini nicht beschreibbar - Menü-Auflösung unverändert."},
    # NEUES FEATURE (Nutzerfrage: "ist da jetzt quasi ein Schalter unter
    # System/Optionen drin, der den Autostart an- und ausschaltbar
    # macht?"). Der Neustart-Hinweis steht in beiden Meldungen: die
    # Autostart-Zeile liest MiSTer nur beim Booten, ein laufendes
    # Frontend merkt von der Umschaltung nichts - ohne den Hinweis
    # wirkt genau das wie ein Fehler.
    "sys_autostart_on": {
        "en": "Autostart: ON -> turn off (frontend no longer starts on boot)",
        "de": "Autostart: AN -> ausschalten (Frontend startet dann nicht mehr beim Booten)"},
    "sys_autostart_off": {
        "en": "Autostart: OFF -> turn on (frontend starts with the MiSTer)",
        "de": "Autostart: AUS -> einschalten (Frontend startet zusammen mit dem MiSTer)"},
    "sys_autostart_enabled": {
        "en": "Autostart on - the frontend starts from the next boot onwards.",
        "de": "Autostart an - das Frontend startet ab dem nächsten Neustart wieder mit."},
    "sys_autostart_disabled": {
        "en": "Autostart off from the next boot. You can still start it from the OSD under Scripts -> Frontend_Start.",
        "de": "Autostart ab dem nächsten Neustart aus. Starten geht weiter über OSD -> Scripts -> Frontend_Start."},
    "sys_autostart_failed": {
        "en": "Could not write user-startup.sh - autostart unchanged.",
        "de": "user-startup.sh nicht beschreibbar - Autostart unverändert."},
    # NEUES FEATURE (Nutzerwunsch: "dass jeder wirklich das angezeigt
    # bekommt, was er auch in seinen ROM-Ordnern sieht"). Die Zeilen
    # nennen bewusst, WAS gefiltert wird - "Filter an/aus" allein sagt
    # niemandem, welche Dateien dann fehlen. Genau diese Unsichtbarkeit
    # war das eigentliche Problem.
    "sys_rom_filter_on": {
        "en": "Hide beta/proto/demo and Japan-only: ON -> turn off (then every ROM in your folders shows up)",
        "de": "Beta/Proto/Demo und Nur-Japan ausblenden: AN -> ausschalten (dann erscheint jede ROM aus deinen Ordnern)"},
    "sys_rom_filter_off": {
        "en": "Hide beta/proto/demo and Japan-only: OFF -> turn on (tidier list, but files disappear)",
        "de": "Beta/Proto/Demo und Nur-Japan ausblenden: AUS -> einschalten (aufgeräumtere Liste, dafür fehlen Dateien)"},
    "sys_rom_filter_changed": {
        "en": "Filter changed - reading the game list again now.",
        "de": "Filter geändert - die Spieleliste wird jetzt neu eingelesen."},
    # NEU (Build 156): Ordner, in denen genau ein Spiel liegt, werden
    # aufgeloest. Der Text nennt bewusst den Grund und nicht nur den
    # Schalter - "Einzelordner auflösen" allein sagt niemandem, warum
    # er das wollen sollte.
    # NEU (Build 171): das eigene Farbschema. Der Menuepunkt sagt
    # ausdruecklich, WO die Datei liegt - wer die Farben feiner
    # einstellen will, bearbeitet sie direkt, bis der Editor da ist.
    "sys_theme_eigen_speichern": {
        "en": "Save current colours as your own scheme",
        "de": "Aktuelle Farben als eigenes Schema speichern"},
    "sys_theme_eigen_gespeichert": {
        "en": "Saved as your own scheme and activated. The colours are "
              "in frontend/theme_eigen.json.",
        "de": "Als eigenes Schema gespeichert und aktiviert. Die Farben "
              "stehen in frontend/theme_eigen.json."},
    "sys_theme_eigen_fehler": {
        "en": "Could not save the colour scheme.",
        "de": "Das Farbschema liess sich nicht speichern."},
    "sys_einzelordner_on": {
        "en": "Folders with a single game: shown as the game -> keep them as folders",
        "de": "Ordner mit nur einem Spiel: als Spiel anzeigen -> als Ordner belassen"},
    "sys_einzelordner_off": {
        "en": "Folders with a single game: kept as folders -> show as the game (cover and grid/gallery work then)",
        "de": "Ordner mit nur einem Spiel: als Ordner belassen -> als Spiel anzeigen (dann gibt es dort Cover, Raster und Galerie)"},
    "sys_einzelordner_changed": {
        "en": "Changed - reading the game list again now.",
        "de": "Geändert - die Spieleliste wird jetzt neu eingelesen."},
    # NEU (Build 73): Cover-Miniaturen einmalig vorberechnen. Die Texte
    # sagen bewusst, WAS das bringt und WAS es kostet - ein Vorgang, der
    # Minuten dauern kann, darf nicht als harmloser Schalter aussehen.
    "sys_thumb_prewarm_action": {
        "en": "Prepare cover thumbnails (one-off, takes a few minutes)",
        "de": "Miniaturen vorbereiten (einmalig, dauert einige Minuten)"},
    "thumb_prewarm": {"en": "Preparing cover thumbnails",
                      "de": "Miniaturen werden vorbereitet"},
    # NEU (Build 82): das Zusammenstellen der Liste kann bei mehreren
    # zehntausend Eintraegen selbst ein paar Sekunden dauern. Ohne
    # eigene Ueberschrift sah das aus, als haenge der Vorgang gleich
    # zu Beginn.
    "thumb_prewarm_collect": {"en": "Collecting covers",
                              "de": "Cover werden zusammengestellt"},
    "thumb_prewarm_cancel": {"en": "Any button cancels - what is done stays done.",
                             "de": "Jede Taste bricht ab - Gerechnetes bleibt erhalten."},
    "thumb_prewarm_eta_min": {"en": "about %d min left",
                              "de": "noch etwa %d Min."},
    "thumb_prewarm_eta_sec": {"en": "about %d s left",
                              "de": "noch etwa %d Sek."},
    "thumb_prewarm_done": {
        "en": "Done: %d thumbnails computed in %d s. Scrolling should feel smooth now.",
        "de": "Fertig: %d Miniaturen in %d Sek. berechnet. Das Scrollen sollte jetzt fluessig sein."},
    "thumb_prewarm_aborted": {
        "en": "Cancelled - %d thumbnails computed in %d s. They are kept; you can continue later.",
        "de": "Abgebrochen - %d Miniaturen in %d Sek. berechnet. Sie bleiben erhalten, du kannst später weitermachen."},
    "thumb_prewarm_nothing": {"en": "No games found - nothing to prepare.",
                              "de": "Keine Spiele gefunden - nichts vorzubereiten."},
    "thumb_prewarm_failed": {"en": "Could not determine the cover size - nothing prepared.",
                             "de": "Cover-Größe nicht ermittelbar - nichts vorbereitet."},
    "sys_pulse_on": {"en": "Selection glow: ON -> turn off (static highlight instead of animation)",
                     "de": "Markierungs-Schimmer: AN -> ausschalten (feste statt animierte Hervorhebung)"},
    "sys_pulse_off": {"en": "Selection glow: OFF -> turn on",
                      "de": "Markierungs-Schimmer: AUS -> einschalten"},
    "sys_eq_on": {"en": "Equalizer bars: ON -> turn off (test if this helps HDMI scrolling)",
                 "de": "Equalizer-Balken: AN -> ausschalten (testen ob es beim HDMI-Scrollen hilft)"},
    "sys_eq_off": {"en": "Equalizer bars: OFF -> turn on",
                  "de": "Equalizer-Balken: AUS -> einschalten"},
    "sys_track_marquee_on": {"en": "Music title scroll: ON -> turn off (static instead of scrolling)",
                             "de": "Musik-Titel-Laufschrift: AN -> ausschalten (fest statt scrollend)"},
    "sys_track_marquee_off": {"en": "Music title scroll: OFF -> turn on",
                              "de": "Musik-Titel-Laufschrift: AUS -> einschalten"},
    "sys_stream_on": {"en": "Stream overlay: ON -> turn off (takes effect after restart)",
                      "de": "Stream-Overlay: AN -> ausschalten (wirkt nach Neustart)"},
    "sys_stream_off": {"en": "Stream overlay: OFF -> turn on (takes effect after restart)",
                       "de": "Stream-Overlay: AUS -> einschalten (wirkt nach Neustart)"},
    "sys_screen_mirror_on": {"en": "Screen mirror: ON -> turn off (needs stream overlay, takes effect after restart)",
                             "de": "Bildschirmspiegel: AN -> ausschalten (braucht Stream-Overlay, wirkt nach Neustart)"},
    "sys_screen_mirror_off": {"en": "Screen mirror: OFF -> turn on (needs stream overlay, takes effect after restart)",
                              "de": "Bildschirmspiegel: AUS -> einschalten (braucht Stream-Overlay, wirkt nach Neustart)"},
    "search_prompt": {"en": "Search: ", "de": "Suche: "},
    # Build 88: Bedienhilfe unter dem Buchstabenwaehler (Suche per Pad).
    # Bewusst kurz - auf CRT steht dafuer eine einzige schmale Zeile zur
    # Verfuegung.
    "picker_hint": {"en": "A pick   B back",
                    "de": "A waehlen  B zurueck"},
    # Build 90: Select allein geht nicht mehr zurueck (das macht B) -
    # stattdessen sagt es, wofuer es jetzt da ist.
    "select_hint": {"en": "Hold Select + A = search, + X = RA showcase",
                    "de": "Select halten + A = Suche, + X = RA-Schaukasten"},
    "sys_update_on": {"en": "Check for updates: ON -> turn off",
                      "de": "Auf Updates prüfen: AN -> ausschalten"},
    "sys_update_off": {"en": "Check for updates: OFF -> turn on",
                       "de": "Auf Updates prüfen: AUS -> einschalten"},
    "sys_update_available": {"en": "Update available: v%s! -> turn check off",
                             "de": "Update verfügbar: v%s! -> Prüfung ausschalten"},
    "update_available_popup": {"en": "Update v%s!",
                               "de": "Update v%s!"},
    "build_available_popup": {"en": "GitHub: %s", "de": "Neu: %s"},
    "on_this_day_popup": {"en": "%d years ago today, you first started %s",
                          "de": "Vor %d Jahren hast du an diesem Tag zum ersten Mal %s gestartet"},
    "attract_hint": {"en": "Press any button to continue",
                     "de": "Beliebige Taste zum Fortfahren"},
    "scanning":  {"en": "Scanning: %s", "de": "Durchsuche: %s"},
    "recent_cat": {"en": "Recently Played", "de": "Zuletzt gespielt"},
    "continue_cat": {"en": "Continue Playing", "de": "Weiterspielen"},
    "ra_hunter_cat": {"en": "RA Achievement Hunter", "de": "RA-Erfolgsjäger"},
    "ra_almost_done_cat": {"en": "Almost there", "de": "Fast geschafft"},
    "collections_cat": {"en": "Collections", "de": "Sammlungen"},
    "collection_discovered_this_year": {"en": "Discovered in %s", "de": "%s entdeckt"},
    "collection_quick_games": {"en": "Quick games", "de": "Kurzweilige Spiele"},
    "favorites_cat": {"en": "Favorites", "de": "Favoriten"},
    "favorite_added": {"en": "Added to favorites", "de": "Zu Favoriten hinzugefügt"},
    "favorite_removed": {"en": "Removed from favorites", "de": "Aus Favoriten entfernt"},
    "completed_added": {"en": "Marked as completed", "de": "Als durchgespielt markiert"},
    "completed_removed": {"en": "Completed mark removed", "de": "Durchgespielt-Markierung entfernt"},
    "sys_rescan":      {"en": "Rescan game list", "de": "Spieleliste neu einlesen"},
    "sys_redraw":      {"en": "Redraw display",   "de": "Anzeige neu aufbauen"},
    # Build 88: bis dahin nur im Ersteinrichtungs-Assistenten erreichbar.
    # Die Beschriftung nennt bewusst, dass es dauert und Netz braucht -
    # beides sieht man dem Menuepunkt sonst nicht an.
    # Build 91: Miniaturen-Zwischenspeicher von Hand leeren.
    "sys_thumb_clear": {"en": "Clear thumbnail cache (CRT / HDMI)",
                        "de": "Miniaturen-Zwischenspeicher leeren (CRT / HDMI)"},
    "choice_hint_plain": {"en": "Up/Down: choose   OK: confirm   ESC: back",
                          "de": "Hoch/Runter: wählen   OK: bestätigen   ESC: zurück"},
    "thumb_clear_title": {"en": "Clear thumbnail cache",
                          "de": "Miniaturen-Zwischenspeicher leeren"},
    "thumb_clear_sd": {"en": "CRT (SD): %s files, %s",
                       "de": "CRT (SD): %s Dateien, %s"},
    "thumb_clear_hd": {"en": "HDMI (HD): %s files, %s",
                       "de": "HDMI (HD): %s Dateien, %s"},
    "thumb_clear_both": {"en": "Clear both", "de": "Beide leeren"},
    "thumb_clear_cancel": {"en": "Cancel", "de": "Abbrechen"},
    "thumb_clear_done": {"en": "%d files removed - they are rebuilt as needed",
                         "de": "%d Dateien entfernt - sie entstehen bei Bedarf neu"},
    "thumb_clear_empty": {"en": "Nothing to clear",
                          "de": "Da war nichts zu leeren"},
    "sys_boxart_download":
        {"en": "Download box art (needs network, takes a while)",
         "de": "Boxarts nachladen (braucht Netz, dauert etwas)"},
    "sys_gameinfo_download":
        {"en": "Download game info (needs network, takes a while)",
         "de": "Spieledaten nachladen (braucht Netz, dauert etwas)"},
    "sys_reboot":      {"en": "Restart MiSTer",   "de": "MiSTer neu starten"},
    "sys_quit":        {"en": "Quit frontend",    "de": "Frontend beenden"},
    "remap_prompt":    {"en": "Press a button for: %s",
                        "de": "Taste drücken für: %s"},
    "remap_action_up":     {"en": "Up",     "de": "Hoch"},
    "remap_action_down":   {"en": "Down",   "de": "Runter"},
    "remap_action_left":   {"en": "Left",   "de": "Links"},
    "remap_action_right":  {"en": "Right",  "de": "Rechts"},
    "remap_action_ok":     {"en": "OK / Start", "de": "OK / Start"},
    "remap_action_back":   {"en": "Back",   "de": "Zurück"},
    "remap_action_osd":    {"en": "Open MiSTer menu", "de": "MiSTer-Menü öffnen"},
    "remap_action_back_fe": {"en": "Back to frontend (from MiSTer menu)",
                             "de": "Zurück ins Frontend (aus dem MiSTer-Menü)"},
    "remap_action_random": {"en": "Random game", "de": "Zufälliges Spiel"},
    "remap_action_favorite": {"en": "Toggle favorite", "de": "Favorit umschalten"},
    "remap_action_completed": {"en": "Toggle completed", "de": "Durchgespielt umschalten"},
    "remap_action_music_next": {"en": "Next song", "de": "Nächster Song"},
    "remap_done":      {"en": "Button mapping saved!",
                        "de": "Tastenbelegung gespeichert!"},
    "remap_cancelled": {"en": "Cancelled - keeping previous mapping",
                        "de": "Abgebrochen - alte Belegung bleibt aktiv"},
    "remap_esc_hint":  {"en": "(ESC to cancel)", "de": "(ESC zum Abbrechen)"},
    "remap_f9_blocked": {"en": "F9 is reserved for MiSTer - press another key",
                        "de": "F9 ist für MiSTer reserviert - andere Taste drücken"},
    "now_playing":     {"en": "Now playing: %s", "de": "Es läuft: %s"},
}

def _load_language():
    try:
        lang = open(LANGUAGE_FILE).read().strip()
        return lang if lang in ("en", "de") else "en"
    except OSError:
        return "en"

CURRENT_LANG = _load_language()

def set_language(lang):
    global CURRENT_LANG
    CURRENT_LANG = lang
    try:
        os.makedirs(os.path.dirname(LANGUAGE_FILE), exist_ok=True)
        with open(LANGUAGE_FILE, "w") as f:
            f.write(lang)
    except OSError:
        pass

def t(key, *fmt_args):
    """Uebersetzten Text fuer den aktuellen Sprachstand liefern.
    Faellt bei fehlendem Schluessel/fehlender Sprache auf Englisch
    bzw. den Schluessel selbst zurueck, statt abzustuerzen."""
    entry = TRANSLATIONS.get(key)
    if entry is None:
        return key
    text = entry.get(CURRENT_LANG, entry.get("en", key))
    if fmt_args:
        try:
            return text % fmt_args
        except (TypeError, ValueError):
            return text
    return text

def current_lang():
    """Liefert IMMER den aktuellen Sprachstand - siehe Modul-Kommentar
    oben, warum ein direktes 'from fe.translations import CURRENT_LANG'
    an anderer Stelle gefaehrlich waere (eingefrorene Kopie)."""
    return CURRENT_LANG
