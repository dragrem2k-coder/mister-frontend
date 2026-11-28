# -*- coding: utf-8 -*-
"""Die Vorfuehrung: Dragend in sechs Kapiteln (Build 345).

WUNSCH DES NUTZERS: "show mit demo gerne zusammengefuehrt damit das
frontend besser dargestellt wird, funktionen anleitungen zeigen ect -
statt einfach Textseiten durchzublaettern, wuerde ich die Vorfuehrung
in thematische Praesentationsseiten aufteilen." Dazu: die
Geschwindigkeit verstaendlich und EHRLICH zeigen ("die Anzeige muss die
tatsaechlich gemessenen Werte verwenden und darf nicht einfach eine
pauschale Bewertung vergeben"), die Einstellungen in Gruppen, eine
echte Design-Vorschau, Bedienung mit Weiter/Zurueck/Blaettern, ein
Fortschrittsbalken und eine richtige Abschlussseite.

DER AUFBAU. Sechs Kapitel; jedes besteht aus Schritten:

  - einer PRAESENTATIONSSEITE, die dieses Modul selbst zeichnet - mit
    Kopf (Fortschrittsbalken "4 / 6"), Titel, Inhalt und Fusszeile, in
    den Farben des eingestellten Schemas;
  - und LIVE-STATIONEN: das echte Frontend, mit den echten Kategorien,
    Covern und Bildschirmen. Die Stationen sind die aus fe/demo.py -
    kein zweiter Zeichenweg (siehe dort, warum das wichtig ist). Vor
    jeder Station steht eine kurze Ansage im Stil der Seiten; ueber
    dem laufenden Bild steht NICHTS - eine Einblendung muesste bei
    jedem Schritt mitgezeichnet werden und verfaelschte genau das,
    was gezeigt wird.

DIE BEDIENUNG
    Rechts / A / Start     weiter
    Links / B              zurueck (auf der ersten Seite: Ende)
    Hoch / Runter          innerhalb einer Seite blaettern
    Select                 von vorn
    B eine Sekunde halten, Esc      beenden
Ohne Taste laeuft alles von selbst. Die erste Taste schaltet auf
Handbetrieb; der Kopf zeigt das an.

DIE GESCHWINDIGKEIT wird nicht gegen 16,7 ms (ein Bild bei 60 Hz)
gestellt - ein Scrollschritt braucht keine 60 Bilder je Sekunde, und
neben dieser Zahl stuende ueberall "zu langsam", obwohl es sich fluessig
anfuehlt. Gestellt wird sie gegen das, was beim Halten einer Taste
WIRKLICH passiert: wie oft die Wiederholung bei der eingestellten
Scrollgeschwindigkeit kommt und wie weit ein Schritt springt - gerechnet
mit genau den Funktionen aus fe/input.py, die das im Betrieb tun.

GESCHRIEBEN WIRD NICHTS. Ansichten, Farbschema und Position werden am
Ende zurueckgesetzt; das Farbschema wird fuer die Vorfuehrung nur
angewendet, nie gespeichert.
"""
import fcntl
import os
import sys
import time

import fe.demo as DEMO
import fe.messwerte as MESS
from fe.translations import current_lang, t

VORFUEHRUNG_VERSION = 1

KAPITEL = (
    (1, ("WILLKOMMEN BEI DRAGEND", "WELCOME TO DRAGEND")),
    (2, ("DEINE SPIELESAMMLUNG", "YOUR GAME COLLECTION")),
    (3, ("GESTALTUNG UND EINSTELLUNGEN", "DESIGN AND SETTINGS")),
    (4, ("WIE SCHNELL IST DRAGEND?", "HOW FAST IS DRAGEND?")),
    (5, ("DEIN DRAGEND", "YOUR DRAGEND")),
    (6, ("DAS ERGEBNIS", "THE RESULT")),
)

# Wie lange B gehalten werden muss, damit die Vorfuehrung endet.
HALTEN_ENDE = 0.9
TAKT = 0.05


def _t(de, en):
    return de if current_lang() == "de" else en


def _zahl(n):
    try:
        s = "{:,}".format(int(n))
    except Exception:                                    # noqa: BLE001
        return str(n)
    return s.replace(",", ".") if current_lang() == "de" else s


def _dez(x, stellen=1):
    s = ("%." + str(stellen) + "f") % x
    return s.replace(".", ",") if current_lang() == "de" else s


# ======================================================================
# DIE EINSTELLUNGEN IN SECHS GRUPPEN
# ======================================================================
# Nach dem, was eine Einstellung FUER DEN NUTZER tut - nicht nach dem
# Ordner, in dem sie im Systemmenue steht. Damit die Zuordnung nicht
# still veraltet, prueft tools/test_vorfuehrung.py, dass JEDE Aktion aus
# fe/menu.py hier einer Gruppe zugeordnet ist.
#
# (schluessel, (Name de, en), (Erklaerung de, en), Aktionen, gezeigt)
# "gezeigt" sind die Aktionen, deren aktueller Wert auf der Seite steht.
GRUPPEN = (
    ("darstellung", ("Darstellung", "Appearance"),
     ("Farben, Ansichten, Schrift, Masken, Rand und Effekte.",
      "Colours, views, font, masks, margins and effects."),
     ("theme", "theme_eigen_speichern", "theme_eigen_bearbeiten",
      "dragend_logo", "schrift", "feinheiten", "hintergrund", "masken",
      "ansicht", "ansicht_haupt", "overscan_x", "overscan_y",
      "pulse_effect", "weihnachten", "eq_effect", "track_marquee",
      "crtmenu", "scharf_verkleinern", "tastenlegende", "crt_test"),
     ("theme", "ansicht_haupt", "ansicht", "masken")),
    ("navigation", ("Navigation", "Navigation"),
     ("Wie schnell und in welcher Ordnung du durch die Listen kommst.",
      "How fast and in what order you move through the lists."),
     ("scroll_tempo", "ordner_zuerst", "favoriten_zuerst",
      "ordner_zahlen", "versteckt", "hauptseite"),
     ("scroll_tempo", "ordner_zuerst", "favoriten_zuerst")),
    ("bibliothek", ("Spielebibliothek", "Game library"),
     ("Was in den Listen steht, woher Cover kommen, Cores und Erfolge.",
      "What is in the lists, where covers come from, cores, achievements."),
     ("curated", "rom_filter", "einzelordner", "fremdquellen",
      "cover_basis", "multidisc", "romwacht", "romwacht_auto", "rescan",
      "nachscan", "boxart_download", "gameinfo_download", "cores",
      "core_neu", "core_uebersicht", "zaparoo", "computer_check",
      "invade_a_load", "ra_status", "ra_settings", "ra_settings_missing",
      "ra_toggle", "ra_profil", "top10_time", "top10_launches",
      "milestones", "trophy_room", "year_review", "diary",
      # Build 346: die eigenen Wertungen
      "wertungen", "wertung_fragen", "wertung_fragen_ab", "wertung_liste",
      "wertung_kategorien", "wertung_stempel", "wertung_zweit",
      "wertung_heft", "wertung_monatsheft", "wertung_csv",
      # Build 350
      "kultboy_an",
      # Build 351
      "zeitmaschine_an",
      # Build 352
      "zeitreise_effekt_an"),
     ("fremdquellen", "rom_filter", "multidisc")),
    ("performance", ("Performance", "Performance"),
     ("Was das Frontend schneller macht - Miniaturen, Auflösung, Scrollen.",
      "What makes the frontend faster - thumbnails, resolution, scrolling."),
     ("thumb_prewarm", "thumb_auftrag", "thumb_clear", "arbeitskopien",
      "fb_size", "fast_scroll", "cover_sofort", "network_wait"),
     ("fb_size", "fast_scroll", "cover_sofort")),
    ("bedienung", ("Bedienung", "Controls"),
     ("Tasten, Sprache, Ton, Musik und der Bildschirmschoner.",
      "Buttons, language, sound, music and the screensaver."),
     ("language", "remap", "remap_reset", "swap_ok_back", "padtest",
      "sfx", "music", "music_source", "volume", "attract",
      "attract_delay", "ziehung_spannung", "zufall_systeme", "help",
      "setup_wizard"),
     ("language", "music", "attract")),
    ("system", ("System", "System"),
     ("Start, Updates, Uhrzeit, Stream und alles rund um den MiSTer.",
      "Start-up, updates, clock, stream and everything about the MiSTer."),
     ("timezone", "autostart", "update_check", "update_all", "osd",
      "reboot", "quit", "redraw", "secrets", "credits", "stream_overlay",
      "screen_mirror", "vorfuehrung"),
     ("autostart", "update_check", "timezone")),
)


def gruppe_von(kind):
    """Der Gruppenschluessel einer Aktion - oder None."""
    for schl, _n, _e, kinds, _g in GRUPPEN:
        if kind in kinds:
            return schl
    return None


def einstellungen_gruppiert(MENU):
    """{gruppe: [(kind, beschriftung)]} aus GENAU dem Systemmenue, das der
    Nutzer sieht - mit den Werten von jetzt. Unbekanntes landet unter
    "system", damit nichts verschwindet."""
    raus = dict((g[0], []) for g in GRUPPEN)
    try:
        baum = MENU.system_items()
    except Exception:                                    # noqa: BLE001
        return raus

    def lauf(knoten, tiefe=0):
        if tiefe > 4 or not isinstance(knoten, dict):
            return
        for unter in (knoten.get("folders", {}) or {}).values():
            lauf(unter, tiefe + 1)
        for e in (knoten.get("items", ()) or ()):
            try:
                text, kind = str(e[0]), e[1]
            except Exception:                            # noqa: BLE001
                continue
            if not isinstance(kind, str):
                continue
            raus[gruppe_von(kind) or "system"].append((kind, text))
    lauf(baum)
    return raus


def wert_aus_beschriftung(text):
    """ "Farbschema: Dunkel (Standard) -> naechstes" -> "Farbschema:
    Dunkel (Standard)". Die Beschriftung nennt den Wert VOR dem Pfeil."""
    return str(text).split(" -> ")[0].strip()


# ======================================================================
# DIE GESCHWINDIGKEIT
# ======================================================================
def _wiederholung(fe, ms):
    """(Intervall in ms, Sprungweite) beim Halten von hoch/runter - mit
    den Funktionen, die das im Betrieb rechnen (fe/input.py)."""
    try:
        import fe.input as I
        g = ms / 1000.0
        boden = min(I.REPEAT_FLOOR_MAX,
                    max(I.REPEAT_FLOOR_MIN, g * I.REPEAT_MESS_RESERVE))
        iv = fe.inp._tempo_anwenden(boden, g, I.REPEAT_FLOOR_MIN, False)
        # _sprung_merken() legt die Weite in der echten Eingabe ab - nach
        # dem Ablesen wieder so wie vorher, die Vorfuehrung aendert nichts.
        alt = dict(getattr(fe.inp, "_sprung_je_akt", None) or {})
        try:
            fe.inp._sprung_merken("down", boden, iv, g, False)
            k = int(fe.inp._sprung_je_akt.get("down", 1) or 1)
        finally:
            fe.inp._sprung_je_akt = alt
        return iv * 1000.0, max(1, k)
    except Exception:                                    # noqa: BLE001
        return ms * 1.15, 1


class SitzungUnberuehrt(object):
    """Die Ansichten der Sitzung danach genau so, wie sie waren - und
    solange NICHT als "benutzt" merken: sonst bereitete "Miniaturen
    vorbereiten" danach Kastengroessen fuer Ansichten vor, die der Nutzer
    nie eingeschaltet hat (Build 338, ANSICHTEN_BENUTZT_FILE). Gilt fuer
    die Messung (auch die von --show) und die ganze Vorfuehrung; darf
    verschachtelt werden."""

    def __init__(self, fe, fm=None):
        self.fe = fe
        # Stillgelegt wird genau der Name, den ansicht_setzen() aufruft:
        # die globalen Namen seines Moduls (auf dem Geraet __main__).
        self.g = None
        methode = getattr(type(fe), "ansicht_setzen", None)
        if methode is not None:
            self.g = getattr(methode, "__globals__", None)
        if self.g is None:
            modul = fm if fm is not None else sys.modules.get(
                type(fe).__module__)
            self.g = getattr(modul, "__dict__", None)

    def __enter__(self):
        fe = self.fe
        self.je_kat = dict(getattr(fe, "_ansicht_je_kat", None) or {})
        self.hatte_je_kat = hasattr(fe, "_ansicht_je_kat")
        self.haupt = getattr(fe, "_ansicht_haupt", None)
        self.hatte_haupt = hasattr(fe, "_ansicht_haupt")
        self.echt = (self.g or {}).get("ansicht_benutzt_merken")
        if self.echt is not None:
            self.g["ansicht_benutzt_merken"] = lambda *a, **k: None
        return self

    def __exit__(self, *_a):
        fe = self.fe
        if self.echt is not None:
            self.g["ansicht_benutzt_merken"] = self.echt
        if self.hatte_je_kat:
            fe._ansicht_je_kat = self.je_kat
        if self.hatte_haupt:
            fe._ansicht_haupt = self.haupt
        return False


def tempo_messen(fe, S, BENCH, schritte=12, abbrechen=None):
    """Ein Scrollschritt je Ansicht, alles warm - mit DERSELBEN
    Schrittfunktion wie Abschnitt J des Bench. Liefert eine Liste von
    dicts (seite, ansicht, ms, schritte_s, iv_ms, sprung, zeilen_s) und
    (kategorie, eintraege). abbrechen() wird zwischen den Ansichten
    gefragt; True beendet die Messung mit dem, was da ist. Seite,
    Position und die Ansichten der Sitzung stehen danach wie vorher,
    auf die Karte wird nichts gemerkt (SitzungUnberuehrt)."""
    with SitzungUnberuehrt(fe):
        return _tempo_messen(fe, S, BENCH, schritte, abbrechen)


def _tempo_messen(fe, S, BENCH, schritte, abbrechen):
    raus = []
    merk = (getattr(fe, "page", 0), getattr(fe, "cat_i", 0),
            getattr(fe, "item_i", 0), list(getattr(fe, "nav_path", []) or []),
            getattr(fe, "scroll", 0))
    kat_i, kat_n, kat_name = BENCH._groesste_kategorie(fe)
    try:
        for seite in (0, 1):
            if seite == 1:
                if kat_i is None:
                    continue
                fe.cat_i = kat_i
                fe.nav_path = []
            fe.page = seite
            for ansicht in BENCH.ansichten_der_seite(S, seite):
                if abbrechen is not None and abbrechen():
                    return raus, (kat_name, kat_n)
                try:
                    if BENCH.ansicht_einstellen(fe, seite,
                                                ansicht) != ansicht:
                        continue
                    schritt = BENCH.schritt_funktion(fe, seite)
                    for i in range(schritte):
                        schritt(i)
                    fenster = BENCH.fenster_spanne(fe, seite)
                    t0 = time.perf_counter()
                    for i in range(schritte):
                        schritt(i % fenster)
                    ms = (time.perf_counter() - t0) * 1000.0 / schritte
                except Exception:                        # noqa: BLE001
                    continue
                iv, k = _wiederholung(fe, ms)
                raus.append({"seite": seite, "ansicht": ansicht,
                             "ms": ms, "schritte_s": 1000.0 / max(0.01, ms),
                             "iv_ms": iv, "sprung": k,
                             "zeilen_s": 1000.0 / max(0.01, iv) * k})
    finally:
        fe.page, fe.cat_i, fe.item_i, fe.nav_path, fe.scroll = merk
    return raus, (kat_name, kat_n)


def kategorie_oeffnen_ms(fe, BENCH):
    """Die groesste Kategorie oeffnen: Liste aufbereiten und erstes Bild
    (wie Abschnitt R des Bench, einmal). (ms, name, eintraege) oder
    None."""
    kat_i, kat_n, kat_name = BENCH._groesste_kategorie(fe)
    if kat_i is None:
        return None
    merk = (fe.page, fe.cat_i, getattr(fe, "item_i", 0),
            getattr(fe, "scroll", 0), list(getattr(fe, "nav_path", []) or []))
    try:
        node = fe.cats[kat_i][1]
        node.pop("_display_items_cache", None)
        if hasattr(fe, "_anzeige_geaendert"):
            fe._anzeige_geaendert()
        t0 = time.perf_counter()
        fe.page, fe.cat_i, fe.nav_path = 1, kat_i, []
        fe.item_i = fe.scroll = 0
        fe._force_full_redraw = True
        fe.fb.mark_full_redraw()
        fe.draw()
        return (time.perf_counter() - t0) * 1000.0, kat_name, kat_n
    except Exception:                                    # noqa: BLE001
        return None
    finally:
        (fe.page, fe.cat_i, fe.item_i, fe.scroll, fe.nav_path) = merk


def ansicht_name(ansicht):
    try:
        return t("ansicht_" + ansicht)
    except Exception:                                    # noqa: BLE001
        return ansicht


# ======================================================================
# HALTEN ERKENNEN (B eine Sekunde = Ende)
# ======================================================================
def _eviocgkey(laenge):
    return (2 << 30) | (laenge << 16) | (ord("E") << 8) | 0x18


def taste_gehalten(inp, codes):
    """Ist eine dieser Tasten JETZT an irgendeinem Geraet gedrueckt?
    Gefragt wird der Kernel (EVIOCGKEY) - die Eingabeschicht meldet
    Tasten nur beim Druecken. Geht das nicht, ist die Antwort False."""
    try:
        geraete = list(getattr(inp, "devices", {}).values())
    except Exception:                                    # noqa: BLE001
        return False
    for d in geraete:
        fd = getattr(d, "fd", None)
        if fd is None or fd < 0:
            continue
        try:
            puffer = bytearray(96)
            fcntl.ioctl(fd, _eviocgkey(len(puffer)), puffer, True)
        except Exception:                                # noqa: BLE001
            continue
        for c in codes:
            if 0 <= c < len(puffer) * 8 and puffer[c // 8] & (1 << (c % 8)):
                return True
    return False


def _zurueck_codes():
    try:
        import fe.input as I
        return [c for c, a in I.KEYMAP.items() if a == "back" and c >= 0]
    except Exception:                                    # noqa: BLE001
        return []


# ======================================================================
# DAS ZEICHNEN DER SEITEN
# ======================================================================
class Leinwand(object):
    """Masse und Farben einer Seite - einmal je Zeichnen geholt, damit
    ein waehrend der Vorfuehrung angewendetes Farbschema sofort gilt."""

    def __init__(self, fe, fm):
        fb = fe.fb
        self.fb = fb
        self.W, self.H = fb.width, fb.height
        try:
            L = fe.layout_cats()
            self.ox, self.oy = L["ox"], L["oy"]
        except Exception:                                # noqa: BLE001
            self.ox, self.oy = self.W // 20, self.H // 20
        self.s = max(1, min(3, self.H // 360))
        # Titel eine Stufe groesser - ausser auf der Roehre, dort passt
        # die Haelfte der Kapiteltitel sonst nicht in die Zeile, und
        # wechselnde Groessen von Seite zu Seite saehen nach Fehler aus.
        self.st = self.s + 1 if self.W >= 640 else self.s
        self.zh = 12 * self.s                     # Zeilenhoehe
        self.bg = getattr(fm, "C_BG", (16, 18, 24))
        self.panel = getattr(fm, "C_PANEL", (28, 32, 44))
        self.text = getattr(fm, "C_TEXT", (220, 224, 232))
        self.dim = getattr(fm, "C_DIM", (120, 126, 140))
        self.titel = getattr(fm, "C_TITLE", (255, 255, 255))
        self.akzent = getattr(fm, "C_ACCENT", (66, 133, 244))
        self.breite = self.W - 2 * self.ox
        self.zeichen = max(10, self.breite // (8 * self.s))

    def schrift(self, x, y, text, skala, farbe, hg=None):
        if y < 0 or y + 8 * skala > self.H:
            return
        maxc = max(1, (self.W - x) // (8 * skala))
        self.fb.text(x, y, str(text)[:maxc], skala, farbe,
                     self.bg if hg is None else hg)

    def passend(self, text, skala, breite=None):
        """Die groesste Skala <= skala, in der text in die Breite passt."""
        breite = self.breite if breite is None else breite
        while skala > 1 and len(text) * 8 * skala > breite:
            skala -= 1
        return skala


def umbrechen(text, zeichen):
    zeilen, cur = [], ""
    for wort in str(text).split():
        probe = (cur + " " + wort).strip()
        if len(probe) <= zeichen:
            cur = probe
        else:
            if cur:
                zeilen.append(cur)
            cur = wort[:zeichen]
    if cur:
        zeilen.append(cur)
    return zeilen or [""]


def _rahmen(fb, x, y, w, h, farbe, dicke=1):
    fb.rect(x, y, w, dicke, farbe)
    fb.rect(x, y + h - dicke, w, dicke, farbe)
    fb.rect(x, y, dicke, h, farbe)
    fb.rect(x + w - dicke, y, dicke, h, farbe)


def mini_oberflaeche(lw, x, y, w, h, farben, name=None, aktiv=False):
    """Eine kleine Beispieloberflaeche in den Farben eines Schemas:
    Hintergrund, Titel, drei Listenzeilen (eine markiert), ein Panel."""
    fb = lw.fb
    bg, panel, text, dim, titel, akzent = (
        farben["C_BG"], farben["C_PANEL"], farben["C_TEXT"],
        farben["C_DIM"], farben["C_TITLE"], farben["C_ACCENT"])
    fb.rect(x, y, w, h, bg)
    _rahmen(fb, x, y, w, h, lw.akzent if aktiv else panel,
            max(1, lw.s) if aktiv else 1)
    pad = max(2, w // 16)
    k = max(1, min(lw.s, (w - 2 * pad) // (6 * 8 * 2) or 1))
    if 6 * 8 * k <= w - 2 * pad and 8 * k < h // 3:
        fb.text(x + pad, y + pad, "MiSTer", k, titel, bg)
    zeile_h = max(2, h // 9)
    y0 = y + pad + 10 * k
    liste_w = (w - 3 * pad) * 3 // 5
    for i, (farbe, laenge) in enumerate(((text, 0.8), (titel, 0.6),
                                         (dim, 0.7))):
        yy = y0 + i * (zeile_h + max(2, zeile_h // 2))
        if yy + zeile_h > y + h - pad:
            break
        if i == 1:
            fb.rect(x + pad, yy - 1, liste_w, zeile_h + 2, akzent)
        fb.rect(x + pad + 2, yy + zeile_h // 4,
                int((liste_w - 4) * laenge), max(1, zeile_h // 2), farbe)
    px = x + 2 * pad + liste_w
    ph = max(4, h - (y0 - y) - pad)
    if px + pad < x + w:
        fb.rect(px, y0, x + w - pad - px, ph, panel)
    if name:
        lw.schrift(x, y + h + 2 * lw.s, name[:max(1, w // (8 * lw.s))],
                   lw.s, lw.akzent if aktiv else lw.text)


class Seite(object):
    """Eine Praesentationsseite: Kopf, Titel, Bloecke, Fusszeile.

    Bloecke (Tupel):
      ("h", text)                    Zwischenueberschrift (Akzentfarbe)
      ("t", text)                    Fliesstext, umgebrochen
      ("d", text)                    leiser Text
      ("kv", schluessel, wert)       Zeile: links leise, rechts hell
      ("bar", text, wert, anteil)    Balken 0..1 mit Beschriftung
      ("gross", text)                grosse Zeile, zentriert
      ("schemata", [(name, farben, aktiv)])   Design-Vorschau
      ("muster", farben)             grosse Vorschau mit Farbfeldern
      ("leer",)
    """

    def __init__(self, kapitel, titel, bloecke, fuss=None):
        self.kapitel = kapitel
        self.titel = titel
        self.bloecke = list(bloecke)
        self.fuss = fuss

    # --- Hoehen -------------------------------------------------------
    def _zeilen(self, lw, block):
        """Ein Block als Liste von Teilzeilen (hoehe, zeichnen(y))."""
        art = block[0]
        s, zh, x0 = lw.s, lw.zh, lw.ox
        raus = []
        if art == "leer":
            raus.append((zh // 2, lambda y: None))
        elif art in ("t", "d"):
            farbe = lw.text if art == "t" else lw.dim
            for z in umbrechen(block[1], lw.zeichen):
                raus.append((zh, lambda y, z=z, f=farbe:
                             lw.schrift(x0, y, z, s, f)))
        elif art == "h":
            raus.append((zh + 3 * s, lambda y, z=block[1]:
                         lw.schrift(x0, y + 3 * s, z, s, lw.akzent)))
        elif art == "kv":
            k, v = str(block[1]), str(block[2])
            spalte = getattr(lw, "kv_spalte", None) or min(len(k) + 2,
                                                            lw.zeichen // 2)
            if len(k) + 2 > spalte:
                # Schmaler Schirm, langer Name: der Name bekommt eine
                # eigene Zeile, der Wert steht eingerueckt darunter -
                # abgeschnitten ("Ansicht Hauptsei") liest es niemand.
                raus.append((zh, lambda y, k=k: lw.schrift(x0, y, k, s,
                                                            lw.dim)))
                for z in umbrechen(v, max(6, lw.zeichen - 2)):
                    raus.append((zh, lambda y, z=z: lw.schrift(
                        x0 + 2 * 8 * s, y, z, s, lw.titel)))
            else:
                vz = umbrechen(v, max(6, lw.zeichen - spalte))
                for i, z in enumerate(vz):
                    def zeich(y, z=z, i=i):
                        if i == 0:
                            lw.schrift(x0, y, k, s, lw.dim)
                        lw.schrift(x0 + spalte * 8 * s, y, z, s, lw.titel)
                    raus.append((zh, zeich))
        elif art == "bar":
            text, wert, anteil = block[1], block[2], max(0.0, min(1.0,
                                                                   block[3]))

            def zeich(y):
                lw.schrift(x0, y, text, s, lw.text)
                wz = str(wert)
                lw.schrift(x0 + lw.breite - len(wz) * 8 * s, y, wz, s,
                           lw.titel)
                by = y + 9 * s
                bh = max(3, 4 * s)
                lw.fb.rect(x0, by, lw.breite, bh, lw.panel)
                lw.fb.rect(x0, by, max(1, int(lw.breite * anteil)), bh,
                           lw.akzent)
            raus.append((9 * s + max(3, 4 * s) + 5 * s, zeich))
        elif art == "gross":
            k = lw.passend(block[1], lw.st + 1)

            def zeich(y, k=k):
                tx = block[1]
                lw.schrift(x0 + max(0, (lw.breite - len(tx) * 8 * k) // 2),
                           y, tx, k, lw.titel)
            raus.append((12 * k, zeich))
        elif art == "schemata":
            eintraege = block[1]
            n = max(1, len(eintraege))
            spalten = min(n, 4 if lw.W >= 640 else 3)
            luecke = max(4, 6 * s)
            tw = (lw.breite - (spalten - 1) * luecke) // spalten
            th = max(24, tw * 9 // 16)
            reihen = (n + spalten - 1) // spalten
            zeile_h = th + 12 * s + luecke
            for r in range(reihen):
                def zeich(y, r=r):
                    for c in range(spalten):
                        i = r * spalten + c
                        if i >= n:
                            break
                        name, farben, aktiv = eintraege[i]
                        mini_oberflaeche(lw, x0 + c * (tw + luecke), y, tw,
                                         th, farben, name, aktiv)
                raus.append((zeile_h, zeich))
        elif art == "muster":
            farben = block[1]
            th = max(30, min(lw.H // 3, lw.breite * 9 // 32))
            tw = th * 16 // 9

            def zeich(y):
                mini_oberflaeche(lw, x0, y, tw, th, farben)
                fx = x0 + tw + 8 * s
                feld = max(6, 7 * s)
                namen = ((_t("Hintergrund", "Background"), "C_BG"),
                         (_t("Panel", "Panel"), "C_PANEL"),
                         (_t("Text", "Text"), "C_TEXT"),
                         (_t("Titel", "Title"), "C_TITLE"),
                         (_t("Akzent", "Accent"), "C_ACCENT"),
                         (_t("Leise", "Dim"), "C_DIM"))
                for i, (nm, key) in enumerate(namen):
                    yy = y + i * max(feld + 2 * s, th // 6)
                    if yy + feld > y + th + 6 * s:
                        break
                    lw.fb.rect(fx, yy, feld, feld, farben[key])
                    _rahmen(lw.fb, fx, yy, feld, feld, lw.dim)
                    lw.schrift(fx + feld + 4 * s, yy, nm, s, lw.text)
            raus.append((th + 8 * s, zeich))
        return raus

    def alle_zeilen(self, lw):
        # Alle Werte einer Seite in EINER Spalte - sonst springt der
        # rechte Rand von Zeile zu Zeile.
        schl = [len(str(b[1])) for b in self.bloecke if b[0] == "kv"]
        lw.kv_spalte = (min(max(schl) + 2, lw.zeichen // 2)
                        if schl else None)
        raus = []
        for b in self.bloecke:
            raus.extend(self._zeilen(lw, b))
        return raus

    # --- Zeichnen ----------------------------------------------------
    def zeichnen(self, fe, fm, scroll=0, auto=True, hinweis=None):
        """Die Seite zeichnen. Liefert das groesste sinnvolle scroll."""
        lw = Leinwand(fe, fm)
        fb, s = lw.fb, lw.s
        fb.clear(lw.bg)
        y = kopf_zeichnen(lw, self.kapitel, auto)
        k = lw.passend(self.titel, lw.st)
        lw.schrift(lw.ox, y, self.titel, k, lw.titel)
        y += 10 * k + 4 * s
        fb.rect(lw.ox, y, lw.breite, max(1, s // 2 or 1), lw.panel)
        y += 5 * s
        unten = lw.H - lw.oy - 2 * lw.zh
        zeilen = self.alle_zeilen(lw)
        # das groesste scroll, bei dem der Rest noch die Flaeche fuellt
        platz = unten - y
        maxscroll = 0
        rest = 0
        for i in range(len(zeilen) - 1, -1, -1):
            rest += zeilen[i][0]
            if rest > platz:
                maxscroll = i + 1
                break
        scroll = max(0, min(scroll, maxscroll))
        yy = y
        for hoehe, zeich in zeilen[scroll:]:
            if yy + hoehe > unten:
                break
            zeich(yy)
            yy += hoehe
        fuss_zeichnen(lw, self.fuss, scroll > 0, scroll < maxscroll,
                      hinweis)
        fb.flip()
        return maxscroll


def kopf_zeichnen(lw, kapitel, auto):
    """Kopf: 'DRAGEND - VORFUEHRUNG', 'k / 6', Fortschrittsbalken.
    Liefert das y unter dem Kopf."""
    s = lw.s
    y = lw.oy
    links = _t("DRAGEND - VORFÜHRUNG", "DRAGEND - PRESENTATION")
    rechts = "%d / %d" % (kapitel, len(KAPITEL))
    if not auto:
        rechts = _t("Handbetrieb   ", "manual   ") + rechts
    lw.schrift(lw.ox, y, links, s, lw.dim)
    lw.schrift(lw.ox + lw.breite - len(rechts) * 8 * s, y, rechts, s,
               lw.dim)
    y += 10 * s
    n = len(KAPITEL)
    luecke = max(2, 2 * s)
    sw = (lw.breite - (n - 1) * luecke) // n
    bh = max(2, 2 * s)
    for i in range(n):
        lw.fb.rect(lw.ox + i * (sw + luecke), y, sw, bh,
                   lw.akzent if i < kapitel else lw.panel)
    return y + bh + 8 * s


def fuss_zeichnen(lw, fuss, nach_oben, nach_unten, hinweis=None):
    s = lw.s
    y = lw.H - lw.oy - 9 * s
    if hinweis is None:
        # Die laengste Fassung, die in die Zeile passt - abgeschnitten
        # waere genau das Ende weg ("B halten: E...").
        blaettern = bool(nach_oben or nach_unten)
        fassungen = [
            ("^v " + _t("blättern   ", "scroll   ") if blaettern else "")
            + _t("< zurück   > weiter   Select: von vorn   B halten: Ende",
                 "< back   > next   Select: restart   hold B: end"),
            ("^v   " if blaettern else "")
            + _t("< zurück   > weiter   Select   B halten: Ende",
                 "< back   > next   Select   hold B: end"),
            ("^v  " if blaettern else "")
            + _t("<  >   Select   B halten", "<  >   Select   hold B"),
        ]
        hinweis = fassungen[-1]
        for f in fassungen:
            if len(f) <= lw.zeichen:
                hinweis = f
                break
    lw.schrift(lw.ox, y, hinweis[:lw.zeichen], s, lw.dim)
    if fuss:
        fy = y - lw.zh
        lw.schrift(lw.ox, fy, str(fuss)[:lw.zeichen], s, lw.dim)


def ansage_zeichnen(fe, fm, kapitel, titel, zeilen, auto):
    """Die kurze Ansage vor einer Live-Station - im Stil der Seiten."""
    Seite(kapitel, titel, [("leer",)] + [("t", z) for z in zeilen if z]
          + [("leer",), ("d", _t("Gleich live im Frontend ...",
                                  "Live in the frontend in a moment ..."))]
          ).zeichnen(fe, fm, auto=auto)


# ======================================================================
# DIE VORFUEHRUNG
# ======================================================================
class Schritt(object):
    """Eine Seite oder eine Live-Station.

    art "seite": bauen() liefert eine Seite.
    art "live":  ausfuehren(dauer) zeigt das echte Frontend und liefert
                 None (durchgelaufen) oder die gedrueckte Aktion."""

    def __init__(self, kapitel, art, name, dauer, bauen=None,
                 ausfuehren=None, ansage=None):
        self.kapitel = kapitel
        self.art = art
        self.name = name
        self.dauer = dauer
        self.bauen = bauen
        self.ausfuehren = ausfuehren
        self.ansage = ansage         # (titel, zeilen) vor einer Station


class Vorfuehrung(object):
    """Siehe Modulkommentar. lauf() ist der einzige Einstieg."""

    def __init__(self, fe, fm, S, BENCH, MENU=None, MASKEN=None,
                 SCHRIFTEN=None, A=None, log=None, messung=None,
                 tempo=1.0):
        self.fe, self.fm, self.S, self.BENCH = fe, fm, S, BENCH
        self.MENU, self.MASKEN, self.SCHRIFTEN, self.A = (MENU, MASKEN,
                                                          SCHRIFTEN, A)
        self.log = log
        self.messung = messung       # vorab gemessen (--show) oder None
        self.oeffnen = None
        self.tempo = tempo           # Faktor auf alle Dauern
        self.auto = True
        self.ende = False
        self._kat = None
        self._eingabe_kaputt = False

    # --- Hilfen -------------------------------------------------------
    def _log(self, text):
        if self.log:
            try:
                self.log("Vorfuehrung: " + text)
            except Exception:                            # noqa: BLE001
                pass

    def _taste(self, timeout):
        """Eine Taste lesen. Klemmt die Eingabe, wird sie nicht weiter
        gefragt - und die Vorfuehrung laeuft von selbst weiter (ohne
        Eingabe gaebe es aus dem Handbetrieb sonst keinen Ausweg).
        fe.inp selbst wird NICHT angefasst: das Frontend braucht es
        danach wieder."""
        inp = None if self._eingabe_kaputt else getattr(self.fe, "inp", None)
        if inp is None:
            self.auto = True
            time.sleep(timeout)
            return None
        try:
            return inp.read_action(timeout=timeout)
        except Exception:                                # noqa: BLE001
            self._eingabe_kaputt = True
            self.auto = True
            return None

    def _kapitel_titel(self, nr):
        for k, (de, en) in KAPITEL:
            if k == nr:
                return _t(de, en)
        return ""

    def _spiele(self):
        try:
            from fe.show import _zaehlen
            return sum(_zaehlen(e[1]) for e in self.fe.cats
                       if isinstance(e[1], dict))
        except Exception:                                # noqa: BLE001
            return 0

    def _kategorien(self):
        raus = []
        for e in getattr(self.fe, "cats", ()) or ():
            try:
                from fe.show import _zaehlen
                n = _zaehlen(e[1])
            except Exception:                            # noqa: BLE001
                continue
            if n:
                raus.append((n, str(e[0])))
        raus.sort(reverse=True)
        return raus

    def _schemata(self):
        """[(schluessel, name, farben, aktiv)] der VERFUEGBAREN Schemata
        und die Zahl der noch geheimen."""
        fm = self.fm
        try:
            reihe = list(fm._available_theme_order())
            aktiv = fm.current_theme_name()
            namen = (fm.THEME_NAMES_DE if current_lang() == "de"
                     else fm.THEME_NAMES_EN)
            raus = [(k, namen.get(k, k), fm.THEMES[k], k == aktiv)
                    for k in reihe if k in fm.THEMES]
            geheim_alle = 1 + len(getattr(fm, "SECRET_THEME_META", {}))
            geheim_frei = sum(1 for k in reihe
                              if k == "secret_gold"
                              or k in [m["theme"] for m in getattr(
                                  fm, "SECRET_THEME_META", {}).values()])
            return raus, max(0, geheim_alle - geheim_frei)
        except Exception:                                # noqa: BLE001
            return [], 0

    def _zaehlen_ordner(self, modul, attr, endung):
        try:
            return modul.BAUM.zaehlen(getattr(modul, attr), endung)
        except Exception:                                # noqa: BLE001
            return None

    def _c_modul(self):
        try:
            if self.A is not None and self.A._LIB is not None:
                return _t("C-Modul libdragend Version %d",
                          "C module libdragend version %d") \
                    % self.A._LIB.dragend_version()
        except Exception:                                # noqa: BLE001
            pass
        return _t("reines Python (C-Modul nicht geladen)",
                  "pure Python (C module not loaded)")

    def _build(self):
        try:
            import json
            hier = os.path.dirname(os.path.dirname(os.path.abspath(
                __file__)))
            with open(os.path.join(hier, "LATEST_BUILD.json")) as f:
                return json.load(f).get("build_id", "?")
        except Exception:                                # noqa: BLE001
            return "?"

    def _rueckkehr(self):
        """(Median ms, Anzahl) der Rueckkehr aus dem Spiel - bevorzugt
        die Messungen seit Build 344 (mit Vorzeichnen)."""
        alle = MESS.rueckkehr_laden()
        neu = [e for e in alle if "vorgezeichnet_ms" in e] or alle
        werte = [e["gesamt_ms"] for e in neu]
        if not werte:
            return None
        return MESS.median(werte), len(werte)

    def _einstellungen(self):
        if self.MENU is None:
            return dict((g[0], []) for g in GRUPPEN)
        return einstellungen_gruppiert(self.MENU)

    # --- Die Seiten ---------------------------------------------------
    def seite_willkommen(self):
        fe = self.fe
        kats = self._kategorien()
        bl = [("t", _t("Dragend ist ein eigenes Menü für deinen MiSTer: "
                       "Spiele nach Systemen, mit Cover, Jahr und "
                       "Beschreibung - mit einem Tastendruck gestartet.",
                       "Dragend is a menu of its own for your MiSTer: "
                       "games by system, with cover, year and description "
                       "- started with one button press.")),
              ("leer",),
              ("kv", "Build", self._build()),
              ("kv", _t("Version", "Version"), self._version()),
              ("kv", _t("System", "System"), self._system()),
              ("kv", _t("Auflösung", "Resolution"),
               "%d x %d" % (fe.fb.width, fe.fb.height)),
              ("kv", _t("Rechenkern", "Engine"), self._c_modul()),
              ("kv", _t("Sammlung", "Collection"),
               _t("%s Spiele in %d Kategorien",
                  "%s games in %d categories")
               % (_zahl(self._spiele()), len(kats))),
              ("leer",),
              ("d", _t("In sechs Kapiteln: deine Sammlung, Gestaltung und "
                       "Einstellungen, die Geschwindigkeit - gemessen, "
                       "nicht behauptet - und dein Dragend.",
                       "In six chapters: your collection, design and "
                       "settings, the speed - measured, not claimed - and "
                       "your Dragend."))]
        return Seite(1, self._kapitel_titel(1), bl)

    def _version(self):
        try:
            from fe.update_check import FRONTEND_VERSION
            return FRONTEND_VERSION
        except Exception:                                # noqa: BLE001
            return "?"

    def _system(self):
        try:
            u = os.uname()
            return "%s %s (%s)" % (u.sysname, u.release, u.machine)
        except Exception:                                # noqa: BLE001
            return "?"

    def seite_sammlung(self):
        kats = self._kategorien()
        gesamt = self._spiele()
        bl = [("kv", _t("Spiele", "Games"), _zahl(gesamt)),
              ("kv", _t("Kategorien", "Categories"), str(len(kats)))]
        try:
            kat_i, kat_n, kat_name = self.BENCH._groesste_kategorie(self.fe)
            if kat_i is not None:
                bl.append(("kv", _t("Längste Liste", "Longest list"),
                           _t("%s - %s Einträge", "%s - %s entries")
                           % (kat_name, _zahl(kat_n))))
        except Exception:                                # noqa: BLE001
            pass
        bl += [("leer",), ("h", _t("DIE GRÖSSTEN SAMMLUNGEN",
                                   "THE LARGEST COLLECTIONS"))]
        oben = kats[0][0] if kats else 1
        for n, name in kats[:8]:
            bl.append(("bar", name, _zahl(n), float(n) / max(1, oben)))
        if len(kats) > 8:
            bl.append(("d", _t("... und %d weitere Kategorien",
                               "... and %d more categories")
                       % (len(kats) - 8)))
        return Seite(2, self._kapitel_titel(2), bl)

    def seite_designs(self):
        schemata, geheim = self._schemata()
        bl = [("t", _t("Jedes Farbschema färbt das ganze Frontend - "
                       "hier im Kleinen, gleich darauf im Grossen.",
                       "Every colour scheme colours the whole frontend - "
                       "small here, full size in a moment.")),
              ("schemata", [(n, f, a) for _k, n, f, a in schemata])]
        zeilen = [("kv", _t("Farbschemata", "Colour schemes"),
                   _t("%d verfügbar", "%d available") % len(schemata)
                   + (_t(", %d weitere geheim", ", %d more secret")
                      % geheim if geheim else ""))]
        try:
            zeilen.append(("kv", _t("Ansichten", "Views"),
                           _t("Hauptseite %d, Spieleliste %d",
                              "main page %d, game list %d")
                           % (len(getattr(self.S, "ANSICHTEN_HAUPT", ())),
                              len(getattr(self.S, "ANSICHTEN", ())))))
        except Exception:                                # noqa: BLE001
            pass
        n = self._zaehlen_ordner(self.MASKEN, "MASKEN_DIR", ".txt")
        if n is not None:
            zeilen.append(("kv", _t("Lochmasken", "Shadow masks"),
                           _t("%d auf deiner Karte", "%d on your card") % n))
        n = self._zaehlen_ordner(self.SCHRIFTEN, "SCHRIFTEN_DIR", ".pf")
        if n is not None:
            zeilen.append(("kv", _t("Schriften", "Fonts"),
                           _t("%d auf deiner Karte", "%d on your card") % n))
        return Seite(3, self._kapitel_titel(3), bl + zeilen)

    def seite_einstellungen(self):
        gr = self._einstellungen()
        gesamt = sum(len(v) for v in gr.values())
        bl = [("t", _t("%d Einstellungen und Aktionen im Systemmenü - "
                       "nach dem geordnet, was sie für dich tun:",
                       "%d settings and actions in the system menu - "
                       "ordered by what they do for you:") % gesamt)]
        for schl, (de, en), (ede, een), _kinds, gezeigt in GRUPPEN:
            eintraege = gr.get(schl, [])
            bl.append(("h", "%s  (%d)" % (_t(de, en).upper(),
                                          len(eintraege))))
            bl.append(("d", _t(ede, een)))
            nach_kind = dict(eintraege)
            for kind in gezeigt:
                if kind in nach_kind:
                    bl.append(("t", "  " + wert_aus_beschriftung(
                        nach_kind[kind])))
        return Seite(3, _t("EINSTELLUNGEN IN SECHS GRUPPEN",
                           "SETTINGS IN SIX GROUPS"), bl)

    def seite_tempo(self):
        messung = self.messung or []
        bl = []
        try:
            faktor = float(self.S.load_scroll_tempo())
        except Exception:                                # noqa: BLE001
            faktor = 1.0
        if not messung:
            bl.append(("t", _t("Die Messung wurde abgebrochen - es gibt "
                               "keine Zahlen.",
                               "The measurement was cancelled - there "
                               "are no numbers.")))
        else:
            bl.append(("d", _t("Gemessen eben auf diesem Gerät: ms je "
                               "Schritt, wie viele Schritte das Bild "
                               "schafft, und - als Balken - wie viele "
                               "Zeilen je Sekunde kommen, wenn du die Taste "
                               "hältst (Scrollgeschwindigkeit %sx).",
                               "Measured just now on this device: ms per "
                               "step, how many steps the picture can do, "
                               "and - as bars - how many lines per second "
                               "arrive while you hold the button (scroll "
                               "speed %sx).")
                       % _dez(faktor, 2).rstrip("0").rstrip(",.")))
            oben = max(m["zeilen_s"] for m in messung) or 1.0
            for seite, kopf in ((0, _t("HAUPTSEITE", "MAIN PAGE")),
                                (1, _t("SPIELELISTE", "GAME LIST"))):
                teil = [m for m in messung if m["seite"] == seite]
                if not teil:
                    continue
                bl.append(("h", kopf))
                schmal = self.fe.fb.width < 640
                for m in teil:
                    if schmal:
                        wert = "%s ms  %d/s" % (_dez(m["ms"]),
                                                int(round(m["zeilen_s"])))
                    else:
                        wert = _t("%s ms - möglich %d/s - gehalten "
                                  "%d Zeilen/s",
                                  "%s ms - up to %d/s - held %d lines/s") % (
                            _dez(m["ms"]), int(round(m["schritte_s"])),
                            int(round(m["zeilen_s"])))
                    bl.append(("bar", ansicht_name(m["ansicht"]), wert,
                               m["zeilen_s"] / oben))
            bl.append(("d", _t("Eine gehaltene Taste wiederholt nie "
                               "schneller, als das Bild gezeichnet ist - "
                               "sonst liefe die Liste nach dem Loslassen "
                               "weiter. Auf 3x und 4x springt ein Schritt "
                               "mehrere Zeilen.",
                               "A held button never repeats faster than the "
                               "picture is drawn - otherwise the list would "
                               "keep running after you let go. At 3x and 4x "
                               "a step jumps several lines.")))
        bl.append(("h", _t("UND SONST", "AND ALSO")))
        sd = getattr(self.fe, "_startdauer", None)
        if sd:
            bl.append(("kv", _t("Start bis Kategorien", "Start to categories"),
                       "%s s" % _dez(sd)))
        if self.oeffnen:
            ms, name, n = self.oeffnen
            bl.append(("kv", _t("Kategorie öffnen", "Open a category"),
                       _t("%s ms (%s, %s Einträge)",
                          "%s ms (%s, %s entries)")
                       % (_dez(ms, 0), name, _zahl(n))))
        rk = self._rueckkehr()
        if rk:
            bl.append(("kv", _t("Rückkehr aus dem Spiel", "Back from a game"),
                       _t("%s s (Median aus %d)", "%s s (median of %d)")
                       % (_dez(rk[0] / 1000.0, 2), rk[1])))
        else:
            bl.append(("kv", _t("Rückkehr aus dem Spiel", "Back from a game"),
                       _t("noch nicht gemessen - einmal ein Spiel starten",
                          "not measured yet - start a game once")))
        return Seite(4, self._kapitel_titel(4), bl)

    def seite_dein(self):
        schemata, _g = self._schemata()
        aktiv = [s for s in schemata if s[3]]
        bl = []
        if aktiv:
            _k, name, farben, _a = aktiv[0]
            bl += [("kv", _t("Farbschema", "Colour scheme"), name),
                   ("muster", farben)]
        try:
            bl.append(("kv", _t("Ansicht Hauptseite", "Main page view"),
                           ansicht_name(self.S.ansicht_haupt_lesen())))
            bl.append(("kv", _t("Ansicht Spieleliste", "Game list view"),
                           ansicht_name(self.S.ansicht_lesen())))
        except Exception:                                # noqa: BLE001
            pass
        try:
            bl.append(("kv", _t("Scrollgeschwindigkeit", "Scroll speed"),
                       "%sx" % _dez(float(self.S.load_scroll_tempo()), 2)
                       .rstrip("0").rstrip(",.")))
        except Exception:                                # noqa: BLE001
            pass
        bl.append(("kv", _t("Sprache", "Language"),
                   _t("Deutsch", "English")))
        gr = self._einstellungen()
        alle = dict(kv for v in gr.values() for kv in v)
        for kind in ("music", "masken", "schrift", "hintergrund"):
            if kind in alle:
                text = wert_aus_beschriftung(alle[kind])
                if ":" in text:
                    k, v = text.split(":", 1)
                    bl.append(("kv", k.strip(), v.strip()))
        bl.append(("h", _t("RESSOURCEN", "RESOURCES")))
        sp = MESS.speicher()
        sysm = MESS.system_speicher()
        if sp.get("belegt"):
            bl.append(("kv", _t("Speicher", "Memory"),
                       _t("%s MB belegt", "%s MB in use")
                       % _dez(sp["belegt"] / 1024.0)
                       + (_t(" von %s MB", " of %s MB")
                          % _dez(sysm["gesamt"] / 1024.0, 0)
                          if sysm.get("gesamt") else "")))
        bl.append(("kv", _t("Rechenkern", "Engine"), self._c_modul()))
        return Seite(5, self._kapitel_titel(5), bl)

    def seite_ergebnis(self):
        schemata, geheim = self._schemata()
        gr = self._einstellungen()
        bl = [("kv", _t("Spiele", "Games"), _zahl(self._spiele())),
              ("kv", _t("Kategorien", "Categories"),
               str(len(self._kategorien()))),
              ("kv", _t("Einstellungen", "Settings"),
               str(sum(len(v) for v in gr.values()))),
              ("kv", _t("Designs", "Designs"),
               str(len(schemata)) + (_t(" (+%d geheim)", " (+%d secret)")
                                     % geheim if geheim else ""))]
        if self.messung:
            best = min(self.messung, key=lambda m: m["ms"])
            schnell = max(self.messung, key=lambda m: m["zeilen_s"])
            bl.append(("kv", _t("Schnellster Schritt", "Fastest step"),
                       "%s ms (%s)" % (_dez(best["ms"]),
                                       ansicht_name(best["ansicht"]))))
            bl.append(("kv", _t("Gehalten bis zu", "Held up to"),
                       _t("%d Zeilen/s", "%d lines/s")
                       % int(round(schnell["zeilen_s"]))))
        rk = self._rueckkehr()
        if rk:
            bl.append(("kv", _t("Zurück aus dem Spiel", "Back from a game"),
                       "%s s" % _dez(rk[0] / 1000.0, 2)))
        bl += [("kv", _t("Rechenkern", "Engine"), self._c_modul()),
               ("leer",),
               ("gross", _t("Das ist Dragend.", "This is Dragend.")),
               ("gross", _t("Deine Sammlung. Dein Design.",
                            "Your collection. Your design.")),
               ("gross", _t("Deine Geschwindigkeit.", "Your speed."))]
        return Seite(6, self._kapitel_titel(6), bl,
                     fuss=_t("Nichts auf der Karte geändert.",
                             "Nothing on the card was changed."))

    # --- Die Live-Stationen -------------------------------------------
    def _demo_station(self, schluessel):
        """Eine Station aus fe/demo.py als Ausfuehrung."""
        def ausfuehren(dauer):
            fe, S = self.fe, self.S
            DEMO.LETZTE_TASTE[0] = None
            try:
                kat_i, sys_i = self._kat
                if schluessel.startswith("schirm:"):
                    weiter = DEMO._schirm_station(fe, S, schluessel[7:],
                                                  dauer, kat_i, sys_i,
                                                  self.log)
                else:
                    seite, _a = DEMO._station_einstellen(fe, S, schluessel,
                                                         kat_i, sys_i)
                    if seite is None:
                        self._log("Station %s uebersprungen" % schluessel)
                        return None
                    weiter = DEMO._scrollen(fe, self.BENCH, seite, dauer)
            except Exception as e:                       # noqa: BLE001
                self._log("Station %s: %s" % (schluessel, e))
                return None
            if weiter:
                return None
            return DEMO.LETZTE_TASTE[0] or "right"
        return ausfuehren

    def _schemata_live(self, dauer):
        """Die echte Hauptseite in bis zu vier Farbschemata - nur
        angewendet, nie gespeichert."""
        fe = self.fe
        schemata, _g = self._schemata()
        if not schemata:
            return None
        auswahl = schemata[:4]
        je = max(1.0, dauer / len(auswahl))
        merk = (fe.page, getattr(fe, "cat_i", 0))
        try:
            fe.page = 0
            for k, _n, _f, _a in auswahl:
                self._schema_anwenden(k)
                fe._force_full_redraw = True
                fe.fb.mark_full_redraw()
                fe.draw()
                akt = self._warten(je)
                if akt is not None:
                    return akt
        finally:
            self._schema_anwenden(None)
            fe.page, fe.cat_i = merk
        return None

    def _schema_anwenden(self, name):
        fm, fb = self.fm, self.fe.fb
        try:
            fm.apply_theme(name if name else fm.current_theme_name())
            fb._rowcache.clear()
            fb._rectcache.clear()
        except Exception:                                # noqa: BLE001
            pass

    def _messen_live(self, dauer):
        """Kapitel 4: die Messung laeuft SICHTBAR - jede Ansicht wird
        echt gescrollt. Jede Taste beendet sie mit dem, was da ist."""
        if self.messung is None:
            gedrueckt = [None]

            def abbrechen():
                akt = self._taste(0)
                if akt is not None:
                    gedrueckt[0] = akt
                    return True
                return False
            self.messung, _kat = tempo_messen(self.fe, self.S, self.BENCH,
                                              abbrechen=abbrechen)
            if gedrueckt[0] is not None:
                return gedrueckt[0]
        if self.oeffnen is None:
            self.oeffnen = kategorie_oeffnen_ms(self.fe, self.BENCH)
        return None

    def _warten(self, sekunden):
        """Warten, auf eine Taste hoerend. Liefert die Taste oder None."""
        ende = time.monotonic() + max(0.0, sekunden)
        runden = int(sekunden / TAKT) + 10
        while runden > 0 and time.monotonic() < ende:
            runden -= 1
            akt = self._taste(TAKT)
            if akt is not None:
                return akt
        return None

    # --- Der Ablauf ---------------------------------------------------
    def schritte(self):
        L, S_ = "live", "seite"
        d = self.tempo

        def ansage(de_titel, en_titel, de, en):
            return (_t(de_titel, en_titel), [_t(de, en)])
        return [
            Schritt(1, S_, "willkommen", 10 * d, bauen=self.seite_willkommen),
            Schritt(2, S_, "sammlung", 11 * d, bauen=self.seite_sammlung),
            Schritt(2, L, "haupt_liste", 8 * d,
                    ausfuehren=self._demo_station("haupt_liste"),
                    ansage=ansage("DIE HAUPTSEITE", "THE MAIN PAGE",
                                  "Deine Kategorien, rechts das Cover zum "
                                  "markierten Eintrag.",
                                  "Your categories, on the right the cover "
                                  "of the selected entry.")),
            Schritt(2, L, "liste_liste", 8 * d,
                    ausfuehren=self._demo_station("liste_liste"),
                    ansage=ansage("DIE SPIELELISTE", "THE GAME LIST",
                                  "Die größte Kategorie, Eintrag für "
                                  "Eintrag.", "The largest category, entry "
                                  "by entry.")),
            Schritt(2, L, "suche", 6 * d,
                    ausfuehren=self._demo_station("schirm:suche"),
                    ansage=ansage("SUCHEN", "SEARCH",
                                  "Buchstabe für Buchstabe - am Pad mit "
                                  "Select+A.", "Letter by letter - Select+A "
                                  "on the pad.")),
            Schritt(2, L, "kontext", 6 * d,
                    ausfuehren=self._demo_station("schirm:kontext"),
                    ansage=ansage("DAS KONTEXTMENÜ", "THE CONTEXT MENU",
                                  "X am Pad: alles, was mit diesem Spiel "
                                  "geht.", "X on the pad: everything you "
                                  "can do with this game.")),
            Schritt(2, L, "zufallszock", 10 * d,
                    ausfuehren=self._demo_station("schirm:zufallszock"),
                    ansage=ansage(t("zufallszock_title"),
                                  t("zufallszock_title"),
                                  "Keine Lust zu suchen? Drei Spiele zur "
                                  "Wahl.", "Can't decide? Three games to "
                                  "choose from.")),
            Schritt(3, S_, "designs", 11 * d, bauen=self.seite_designs),
            Schritt(3, L, "schemata", 12 * d, ausfuehren=self._schemata_live,
                    ansage=ansage("FARBSCHEMATA LIVE", "COLOUR SCHEMES LIVE",
                                  "Dieselbe Hauptseite in verschiedenen "
                                  "Schemata.", "The same main page in "
                                  "different schemes.")),
            Schritt(3, S_, "einstellungen", 16 * d,
                    bauen=self.seite_einstellungen),
            Schritt(3, L, "haupt_raster", 5 * d,
                    ausfuehren=self._demo_station("haupt_raster"),
                    ansage=ansage("ANSICHTEN", "VIEWS",
                                  "Die Hauptseite als Raster und als "
                                  "Galerie.", "The main page as grid and "
                                  "gallery.")),
            Schritt(3, L, "haupt_galerie", 5 * d,
                    ausfuehren=self._demo_station("haupt_galerie")),
            Schritt(3, L, "liste_raster", 5 * d,
                    ausfuehren=self._demo_station("liste_raster"),
                    ansage=ansage("ANSICHTEN DER SPIELELISTE",
                                  "GAME LIST VIEWS",
                                  "Dieselben Spiele als Raster und als "
                                  "Galerie.", "The same games as grid and "
                                  "gallery.")),
            Schritt(3, L, "liste_galerie", 5 * d,
                    ausfuehren=self._demo_station("liste_galerie")),
            Schritt(3, L, "einst_anzeige", 8 * d,
                    ausfuehren=self._demo_station("einst:sys_group_display"),
                    ansage=ansage("DAS SYSTEMMENÜ", "THE SYSTEM MENU",
                                  "Jeder Punkt zeigt seinen Wert - OK "
                                  "schaltet weiter.", "Every entry shows its "
                                  "value - OK switches on.")),
            Schritt(3, L, "hilfe", 7 * d,
                    ausfuehren=self._demo_station("schirm:hilfe"),
                    ansage=ansage("HILFE IM FRONTEND", "HELP IN THE FRONTEND",
                                  "Alle Tasten und Kniffe auf einen Blick.",
                                  "Every button and trick at a glance.")),
            Schritt(4, L, "messen", 0,
                    ausfuehren=self._messen_live,
                    ansage=ansage("ES WIRD GEMESSEN", "MEASURING",
                                  "Jede Ansicht wird jetzt echt gescrollt - "
                                  "so schnell sie kann.",
                                  "Every view is now really scrolled - as "
                                  "fast as it can.")),
            Schritt(4, S_, "tempo", 16 * d, bauen=self.seite_tempo),
            Schritt(5, S_, "dein", 13 * d, bauen=self.seite_dein),
            Schritt(5, L, "trophy", 7 * d,
                    ausfuehren=self._demo_station("schirm:trophy"),
                    ansage=ansage("DEINE SPIELZEIT", "YOUR PLAY TIME",
                                  "Trophäenraum, Meilensteine, Top 10, "
                                  "Jahresrückblick, Tagebuch.",
                                  "Trophy room, milestones, top 10, year in "
                                  "review, diary.")),
            Schritt(5, L, "meilen", 6 * d,
                    ausfuehren=self._demo_station("schirm:meilen")),
            Schritt(5, L, "top10", 6 * d,
                    ausfuehren=self._demo_station("schirm:top10")),
            Schritt(5, L, "jahr", 5 * d,
                    ausfuehren=self._demo_station("schirm:jahr")),
            Schritt(5, L, "tagebuch", 5 * d,
                    ausfuehren=self._demo_station("schirm:tagebuch")),
            Schritt(6, S_, "ergebnis", 16 * d, bauen=self.seite_ergebnis),
        ]

    def _taste_behandeln(self, akt, i, n):
        """Neuer Index fuer eine Taste - oder None fuer Ende, oder i fuer
        'hier bleiben'. Jede Taste schaltet auf Handbetrieb."""
        self.auto = False
        if akt == "exit":
            return None
        if akt == "back":
            # B halten = Ende: noch gedrueckt nach HALTEN_ENDE?
            codes = _zurueck_codes()
            ende = time.monotonic() + HALTEN_ENDE
            gehalten = bool(codes)
            while gehalten and time.monotonic() < ende:
                if not taste_gehalten(self.fe.inp, codes):
                    gehalten = False
                    break
                time.sleep(TAKT)
            if gehalten:
                return None
            return i - 1 if i > 0 else None
        if akt == "left":
            return i - 1 if i > 0 else None
        if akt in ("right", "ok"):
            return i + 1
        if akt == "select":
            return 0
        return i

    def lauf(self):
        fe = self.fe
        if getattr(fe, "fb", None) is None:
            return False
        try:
            kat_i, kat_n, _nm = self.BENCH._groesste_kategorie(fe)
        except Exception:                                # noqa: BLE001
            kat_i, kat_n = None, 0
        if kat_i is not None and kat_n < DEMO.LISTE_MIN_EINTRAEGE:
            kat_i = None
        self._kat = (kat_i, DEMO._system_kategorie(fe))
        merk = {}
        for feld in ("page", "cat_i", "item_i", "scroll", "nav_path",
                     "cat_scroll"):
            if hasattr(fe, feld):
                merk[feld] = getattr(fe, feld)
        schritte = self.schritte()
        i = 0
        self._log("beginnt (%d Schritte)" % len(schritte))
        # Die Ansichten der Sitzung danach wie vorher, nichts als
        # "benutzt" gemerkt (SitzungUnberuehrt).
        unberuehrt = SitzungUnberuehrt(fe, self.fm).__enter__()
        try:
            while 0 <= i < len(schritte):
                st = schritte[i]
                if st.art == "seite":
                    akt = self._seite_zeigen(st)
                else:
                    akt = self._live_zeigen(st)
                if akt is None:
                    if self.auto:
                        i += 1
                        continue
                    # Handbetrieb: auf eine Taste warten - klemmt die
                    # Eingabe, schaltet _taste() zurueck auf Automatik.
                    while akt is None and not self.auto:
                        akt = self._taste(0.2)
                    if akt is None:
                        i += 1
                        continue
                neu = self._taste_behandeln(akt, i, len(schritte))
                if neu is None:
                    self._log("beendet bei Schritt %s (Taste)" % st.name)
                    return False
                i = neu
            self._log("durchgelaufen")
            return True
        finally:
            self._schema_anwenden(None)
            unberuehrt.__exit__(None, None, None)
            for feld, wert in merk.items():
                try:
                    setattr(fe, feld, wert)
                except Exception:                        # noqa: BLE001
                    pass
            try:
                fe._last_input_time = time.monotonic()
                fe._force_full_redraw = True
                fe.fb.mark_full_redraw()
            except Exception:                            # noqa: BLE001
                pass

    def _seite_zeigen(self, st):
        """Eine Seite zeigen. None = Zeit um (Automatik), sonst die
        Taste, die nicht hoch/runter war."""
        try:
            seite = st.bauen()
        except Exception as e:                           # noqa: BLE001
            self._log("Seite %s: %s" % (st.name, e))
            return None
        scroll = 0
        maxscroll = seite.zeichnen(self.fe, self.fm, scroll, self.auto)
        ende = time.monotonic() + st.dauer
        # Automatik: ist die Seite laenger als der Schirm, blaettert sie
        # sich in der zweiten Haelfte ihrer Zeit von selbst durch.
        naechstes = (time.monotonic() + st.dauer / 2.0) if maxscroll else None
        takt_scroll = (st.dauer / 2.0) / max(1, maxscroll)
        runden = int(max(st.dauer, 0.1) / TAKT) + 50
        while True:
            if self.auto:
                runden -= 1
                if time.monotonic() >= ende or runden <= 0:
                    return None
                if naechstes is not None and time.monotonic() >= naechstes \
                        and scroll < maxscroll:
                    scroll += 1
                    naechstes += takt_scroll
                    seite.zeichnen(self.fe, self.fm, scroll, self.auto)
            akt = self._taste(TAKT if self.auto else 0.2)
            if akt is None:
                continue
            if akt in ("up", "down"):
                war_auto = self.auto
                self.auto = False
                scroll = max(0, min(maxscroll,
                                    scroll + (1 if akt == "down" else -1)))
                maxscroll = seite.zeichnen(self.fe, self.fm, scroll, False)
                if war_auto:
                    naechstes = None
                continue
            return akt

    def _live_zeigen(self, st):
        """Ansage, dann die Station. None = durchgelaufen."""
        if st.ansage:
            titel, zeilen = st.ansage
            ansage_zeichnen(self.fe, self.fm, st.kapitel, titel, zeilen,
                            self.auto)
            akt = self._warten(1.8 * self.tempo if self.auto else 1.2)
            if akt is not None:
                return akt
        try:
            akt = st.ausfuehren(st.dauer)
        except Exception as e:                           # noqa: BLE001
            self._log("Station %s: %s" % (st.name, e))
            akt = None
        return akt


def lauf(fe, fm, S, BENCH, MENU=None, MASKEN=None, SCHRIFTEN=None, A=None,
         log=None, messung=None, tempo=1.0):
    """Die Vorfuehrung zeigen. True, wenn sie durchgelaufen ist."""
    return Vorfuehrung(fe, fm, S, BENCH, MENU, MASKEN, SCHRIFTEN, A, log,
                       messung, tempo).lauf()
