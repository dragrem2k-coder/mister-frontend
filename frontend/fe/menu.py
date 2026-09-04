#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Aufbau der 'System'-Kategorie als Baumknoten mit thematischen
Unterordnern (system_items()). Ausgelagert aus frontend.py
(Modularisierung, Git-Branch 'modular-refactor').

Einige kleine Theme-bezogene Stuecke hier bewusst dupliziert statt
importiert (THEME_FILE, die gueltigen Themennamen, THEME_NAMES_DE/EN,
current_theme_name()) - das VOLLSTAENDIGE Theme-System (apply_theme/
accent_for mit den ueber 80 Farbvariablen-Lesestellen in der
Frontend-Klasse) bleibt bewusst ein spaeterer, eigener Schritt (siehe
fruehere Analyse). system_items() braucht aber nur den Namen des
aktuell aktiven Themes fuer die Menuebeschriftung, nicht die Farben
selbst - dafuer reicht ein schlanker, unabhaengiger
current_theme_name()-Nachbau ohne die riskanten Teile.

FRONTEND_VERSION liegt NICHT mehr dupliziert hier UND in frontend.py
UND in fe/update_check.py (fruesher gleich DREIMAL der Fall, beim
v4.4-Bump als echtes Drift-Risiko gefunden - siehe Kommentar dort).
Kanonische Quelle ist jetzt fe/update_check.py (liegt am tiefsten in
der Abhaengigkeitskette) - hier nur noch importiert, frontend.py
importiert wiederum von hier (transitiv).
"""
import os
from fe.translations import t, current_lang
from fe.audio import get_volume, sfx_enabled_flag
from fe.settings import (
    attract_enabled, crt_menu_active, curated_only_active,
    dragend_logo_enabled, format_attract_delay, load_attract_delay,
    screen_mirror_enabled, stream_overlay_enabled, system_bg_enabled,
    fast_scroll_enabled, pulse_effect_enabled, eq_effect_enabled,
    track_marquee_enabled, fb_size_label_key,
    autostart_enabled, rom_filter_enabled,
)
from fe.timekeeping import format_timezone_offset, load_timezone_offset
from fe.retroachievements import load_ra_config, ra_toggle_enabled
from fe.update_check import (
    load_update_state, update_check_enabled, _version_newer,
    FRONTEND_VERSION,
)
from fe.scan import network_wait_enabled, network_wait_is_auto
from fe.input import swap_ok_back_enabled

THEME_FILE = "/media/fat/frontend/theme"
# BUGFIX (Nutzer-Rueckmeldung: "freigeschaltete Geheim-Themes sollten im
# Anzeige-Menue unter Farbschema auswaehlbar erscheinen"): diese Liste/
# diese Namen sind eine BEWUSSTE, unabhaengige Kopie (siehe Modul-
# Kommentar oben) - sie kannte die 9 neuen Konsolen-Geheim-Themes aus
# frontend.py's SECRET_THEME_META (Secret-Themes-Feature) bisher gar
# nicht. Folge: current_theme_name() gab fuer ein aktives, aber HIER
# unbekanntes Geheim-Theme still auf "dark" zurueck (nicht in
# _VALID_THEME_NAMES) - die Menuezeile zeigte dadurch faelschlich
# "Farbschema: Dunkel (Standard)" an, obwohl tatsaechlich laengst ein
# Geheim-Theme aktiv war. Jetzt nachgezogen - bei einem kuenftigen
# neuen Geheim-Theme MUSS diese Liste hier mit aktualisiert werden
# (genau wie THEMES/SECRET_THEME_META in frontend.py selbst).
_VALID_THEME_NAMES = {
    "dark", "light", "green", "secret_gold",
    "snes_16bit", "dmg_green", "gbc_neon", "n64_turbo", "ps1_classic",
    "sega_sonic", "sms_sonic", "gamegear_sonic", "saturn_sonic",
}
# Anzeigenamen: sobald ein Geheim-Theme HIER als current_theme_name()
# auftaucht, ist es zwangslaeufig bereits gefunden (siehe Begruendung
# bei SECRET_THEME_DISPLAY_NAMES in frontend.py) - der echte Name kann
# also gefahrlos direkt gezeigt werden statt fuer immer "??? Geheim
# ???" zu bleiben.
THEME_NAMES_DE = {"dark": "Dunkel (Standard)", "light": "Hell",
                  "green": "Retro-Gruen", "secret_gold": "Gold (geheim)",
                  "snes_16bit": "SNES (geheim)",
                  "dmg_green": "Game Boy (geheim)",
                  "gbc_neon": "Game Boy Color (geheim)",
                  "n64_turbo": "N64 (geheim)",
                  "ps1_classic": "PS1 (geheim)",
                  "sega_sonic": "Mega Drive (geheim)",
                  "sms_sonic": "Master System (geheim)",
                  "gamegear_sonic": "Game Gear (geheim)",
                  "saturn_sonic": "Saturn (geheim)"}
THEME_NAMES_EN = {"dark": "Dark (default)", "light": "Light",
                  "green": "Retro Green", "secret_gold": "Gold (secret)",
                  "snes_16bit": "SNES (secret)",
                  "dmg_green": "Game Boy (secret)",
                  "gbc_neon": "Game Boy Color (secret)",
                  "n64_turbo": "N64 (secret)",
                  "ps1_classic": "PS1 (secret)",
                  "sega_sonic": "Mega Drive (secret)",
                  "sms_sonic": "Master System (secret)",
                  "gamegear_sonic": "Game Gear (secret)",
                  "saturn_sonic": "Saturn (secret)"}

def current_theme_name():
    """Schlanker, unabhaengiger Nachbau (siehe Modul-Kommentar oben) -
    liefert nur den NAMEN des aktiven Themes, nicht die Farben."""
    try:
        name = open(THEME_FILE).read().strip()
        if name in _VALID_THEME_NAMES:
            return name
    except OSError:
        pass
    return "dark"

def system_items(music_enabled=None, music_source="mp3", music_station="",
                 cores_subcats=None, standalone_items=None, scripts_items=None):
    """Liefert die Inhalte der 'System'-Kategorie als Baumknoten mit
    thematischen Unterordnern (Nutzerwunsch: die Liste war auf 23
    flache Eintraege angewachsen, kaum noch ueberschaubar) - nutzt
    dieselbe Ordner-Navigation wie eigene ROM-Unterordner, kein neuer
    Code-Pfad noetig. Die Aktions-"kind"-Werte in jedem Eintrag bleiben
    UNVERAENDERT (siehe Aktions-Dispatch in run()) - nur die
    Gruppierung/Anzeige aendert sich, kein bestehendes Verhalten.

    music_source/music_station (neu, Nutzerwunsch: Rainwave-
    Internetradio als zweite Musikquelle, siehe CHANGES_RAINWAVE.md):
    fuer die Beschriftung des neuen "Musik-Quelle"-Eintrags.

    ERWEITERT (Nutzerwunsch: Hauptmenue aufraeumen, "zu viele
    Eintraege" - Utilities/Other/Scripts sowie Consoles/
    Console (autoboot)/RA Cores waren bisher eigene Top-Level-
    Kategorien): cores_subcats - Liste von (Anzeigename, Items) fuer
    die vormals eigenstaendigen Core-Ordner-Kategorien (Consoles,
    Console (autoboot), RA Cores), die hier gemeinsam unter einem
    NEUEN "Cores"-Unterordner landen (als je EIGENER Unter-Unterordner
    darunter - bleiben so weiterhin unterscheidbar, nur eine Ebene
    tiefer verschachtelt, nicht zu einer einzigen Liste vermischt).
    standalone_items - dict Anzeigename -> Items fuer Kategorien, die
    je einen EIGENEN Unterordner direkt im System-Menue bekommen
    (Utilities, Other). scripts_items - Items fuer einen neuen
    "Scripts"-Unterordner (ehemals eigene Top-Level-Kategorie). Alle
    drei bewusst optional (None/leer = Verhalten unveraendert wie vor
    dieser Erweiterung) - betrifft nur, ob der jeweilige Ordner
    ueberhaupt auftaucht, keine bestehende Logik wird angefasst."""
    crt = crt_menu_active()
    video = t("sys_video_crt") if crt else t("sys_video_hdmi")
    music_label = t("sys_music_on") if music_enabled else t("sys_music_off")
    music_src_label = (t("sys_music_source", "Radio - %s" % (music_station or "?"))
                       if music_source == "radio" else t("sys_music_source", "MP3"))
    volume_label = t("sys_volume", get_volume())
    curated_label = t("sys_curated_on") if curated_only_active() \
        else t("sys_curated_off")
    attract_label = t("sys_attract_on") if attract_enabled() \
        else t("sys_attract_off")
    attract_delay_label = t("sys_attract_delay", format_attract_delay(load_attract_delay()))
    theme_names = THEME_NAMES_DE if current_lang() == "de" else THEME_NAMES_EN
    theme_label = t("sys_theme", theme_names.get(current_theme_name(), "?"))
    tz_label = t("sys_timezone", format_timezone_offset(load_timezone_offset()))
    netwait_label = t("sys_network_wait_on" if network_wait_enabled()
                      else "sys_network_wait_off")
    # NEU (siehe network_wait_is_auto() in fe/scan.py): solange der
    # Stand rein automatisch anhand von user-startup.sh erkannt wurde
    # (Nutzer hat den Menuepunkt noch nie selbst angefasst), bekommt
    # die Zeile einen kleinen Hinweis - sonst wirkt ein von selbst
    # aktiviertes "AN" wie ein Bug statt wie ein Feature. Sobald der
    # Nutzer den Punkt einmal selbst umschaltet, verschwindet der
    # Hinweis (network_wait_is_auto() wird dann False).
    if network_wait_is_auto():
        netwait_label = "%s %s" % (netwait_label, t("sys_network_wait_auto_hint"))
    swap_ok_back_label = t("sys_swap_ok_back_on" if swap_ok_back_enabled()
                           else "sys_swap_ok_back_off")
    sfx_label = t("sys_sfx_on") if sfx_enabled_flag() else t("sys_sfx_off")
    dragend_logo_label = t("sys_dragend_logo_on") if dragend_logo_enabled() \
        else t("sys_dragend_logo_off")
    system_bg_label = t("sys_system_bg_on") if system_bg_enabled() \
        else t("sys_system_bg_off")
    fast_scroll_label = t("sys_fast_scroll_on") if fast_scroll_enabled() \
        else t("sys_fast_scroll_off")
    # NEUES FEATURE (Nutzerwunsch: Schalter fuer die Framebuffer-Groesse):
    # drei Stufen (voll / halb / viertel), die Zeile nennt den aktuellen
    # Wert - siehe fb_size_label_key() in fe/settings.py.
    fb_size_label = t(fb_size_label_key())
    pulse_label = t("sys_pulse_on") if pulse_effect_enabled() \
        else t("sys_pulse_off")
    eq_label = t("sys_eq_on") if eq_effect_enabled() \
        else t("sys_eq_off")
    track_marquee_label = t("sys_track_marquee_on") if track_marquee_enabled() \
        else t("sys_track_marquee_off")
    stream_label = t("sys_stream_on") if stream_overlay_enabled() \
        else t("sys_stream_off")
    screen_mirror_label = t("sys_screen_mirror_on") if screen_mirror_enabled() \
        else t("sys_screen_mirror_off")
    if not update_check_enabled():
        update_label = t("sys_update_off")
    else:
        _remote_v = load_update_state().get("remote_version")
        if _remote_v and _version_newer(_remote_v, FRONTEND_VERSION):
            update_label = t("sys_update_available", _remote_v)
        else:
            update_label = t("sys_update_on")
    ra_user, _ra_key = load_ra_config()
    ra_label = t("sys_ra_configured", ra_user) if ra_user else t("sys_ra_setup")
    # NEU (Nutzerwunsch: "ich würde gerne die Option haben, die
    # RetroAchievements von dort an und aus zu schalten" - bisher gab es
    # hier nur "neu laden"): zusaetzliche Ein/Aus-Zeile, NUR sichtbar,
    # wenn ueberhaupt Zugangsdaten hinterlegt sind (ra_user) - ohne
    # Einrichtung gibt es noch nichts zum An-/Ausschalten, siehe
    # ra_toggle_enabled()/ra_enabled() in fe/retroachievements.py.
    ra_toggle_label = (t("sys_ra_toggle_on") if ra_toggle_enabled()
                       else t("sys_ra_toggle_off"))

    # NEUES FEATURE (Nutzerwunsch: "koennen wir das Script
    # Frontend_Start.sh, wenn einer kein Autostart eingerichtet hat,
    # irgendwie auf F4 im OSD einbinden?"). Standard AUS - siehe
    # F4_HOTKEY_FLAG in fe/settings.py fuer die Begruendung.
    # NEUES FEATURE (Nutzerfrage: "ist da jetzt quasi ein Schalter unter
    # System/Optionen drin, der den Autostart an- und ausschaltbar
    # macht?"). Steht bewusst DIREKT ueber dem F4-Schalter: die beiden
    # gehoeren zusammen ("Autostart aus, dafuer F4"), und wer den einen
    # sucht, findet so den anderen gleich mit.
    # NEUES FEATURE (Nutzerwunsch: "dass jeder wirklich das angezeigt
    # bekommt, was er auch in seinen ROM-Ordnern sieht") - siehe
    # rom_filter_enabled() in fe/settings.py. Standard AUS.
    rom_filter_label = t("sys_rom_filter_on") if rom_filter_enabled() \
        else t("sys_rom_filter_off")
    autostart_label = t("sys_autostart_on") if autostart_enabled() \
        else t("sys_autostart_off")

    def folder(*items):
        return {"folders": {}, "items": list(items)}

    ra_items = [(ra_label, "ra_status", None)]
    if ra_user:
        ra_items.append((ra_toggle_label, "ra_toggle", None))

    # NEUES FEATURE (Nutzerwunsch: Schalter fuer die Framebuffer-Groesse):
    # die Zeile erscheint bewusst NUR, wenn der CRT-Modus AUS ist. Im
    # CRT-Modus ist der Framebuffer ohnehin nur 320x240 - eine halbe oder
    # gar geviertelte Auflösung davon (160x120 bzw. 80x60) waere praktisch
    # unlesbar, und es gaebe dort auch nichts zu gewinnen: der gemessene
    # Aufwand pro Bildaufbau liegt auf CRT bereits bei einem Sechstel des
    # HDMI-Werts. Der Punkt loest also genau das Problem, das es nur auf
    # HDMI gibt, und kann im CRT-Modus gar nicht erst falsch gesetzt werden.
    display_items = [
        (video + t("sys_video_suffix"), "crtmenu", None),
        (theme_label, "theme", None),
        (sfx_label, "sfx", None),
        (dragend_logo_label, "dragend_logo", None),
        (system_bg_label, "system_bg", None),
        (fast_scroll_label, "fast_scroll", None),
    ]
    if not crt:
        display_items.append((fb_size_label, "fb_size", None))
    display_items += [
        (pulse_label, "pulse_effect", None),
        (eq_label, "eq_effect", None),
        (track_marquee_label, "track_marquee", None),
        (stream_label, "stream_overlay", None),
        (screen_mirror_label, "screen_mirror", None),
        (music_label, "music", None),
        (music_src_label, "music_source", None),
        (volume_label, "volume", None),
    ]

    groups = {
        t("sys_group_ra"): folder(*ra_items),
        t("sys_group_stats"): folder(
            (t("top10_time_action"), "top10_time", None),
            (t("top10_launches_action"), "top10_launches", None),
            (t("sys_milestones_action"), "milestones", None),
            (t("sys_trophy_action"), "trophy_room", None),
            (t("sys_year_review_action"), "year_review", None),
            (t("sys_diary_action"), "diary", None),
        ),
        t("sys_group_display"): folder(*display_items),
        t("sys_group_behavior"): folder(
            (t("sys_crt_test_action"), "crt_test", None),
            # NEU (Build 73): einmalig alle Cover-Miniaturen vorberechnen.
            # Bewusst HIER unter "Verhalten" und nicht unter "Anzeige":
            # es aendert nichts am Aussehen, sondern nur daran, wie
            # schnell sich das Frontend anfuehlt.
            (t("sys_thumb_prewarm_action"), "thumb_prewarm", None),
            (curated_label, "curated", None),
            (rom_filter_label, "rom_filter", None),
            (attract_label, "attract", None),
            (attract_delay_label, "attract_delay", None),
            (tz_label, "timezone", None),
            (netwait_label, "network_wait", None),
            (autostart_label, "autostart", None),
        ),
        t("sys_group_input"): folder(
            (t("sys_language"), "language", None),
            (t("sys_configure_buttons"), "remap", None),
            (t("sys_reset_buttons"), "remap_reset", None),
            # NEU (Nutzerwunsch: Bestaetigen/Abbrechen auf manchen Pads
            # andersherum als vom Frontend angenommen - siehe
            # save_swap_ok_back()/swap_ok_back_enabled() in fe/input.py):
            # ein einziger Umschalter statt der kompletten Remap-
            # Prozedur fuer genau diesen (haeufigsten) Einzelfall.
            (swap_ok_back_label, "swap_ok_back", None),
        ),
        t("sys_group_info"): folder(
            (t("sys_help_action"), "help", None),
            (t("sys_setup_wizard"), "setup_wizard", None),
            (t("sys_secrets_action"), "secrets", None),
            (t("sys_credits_action"), "credits", None),
            (update_label, "update_check", None),
        ),
        t("sys_group_maintenance"): folder(
            (t("sys_osd"), "osd", None),
            (t("sys_rescan"), "rescan", None),
            (t("sys_redraw"), "redraw", None),
            (t("sys_reboot"), "reboot", None),
            (t("sys_quit"), "quit", None),
        ),
    }

    if cores_subcats:
        groups["Cores"] = {
            "folders": {name: folder(*items) for name, items in cores_subcats if items},
            "items": [],
        }
    if standalone_items:
        for name, items in standalone_items.items():
            if items:
                groups[name] = folder(*items)
    if scripts_items:
        groups["Scripts"] = folder(*scripts_items)

    return {"folders": groups, "items": []}



from fe.search import _normalize_for_search, jump_to_letter, jump_to_substring

# ----------------------------------------------------------------------------
# FRONTEND
# ----------------------------------------------------------------------------

