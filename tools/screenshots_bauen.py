#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Die Bilder fuer README und VORSCHAU aus dem ECHTEN Zeichenpfad
erzeugen (Build 129).

WARUM ES DAS GIBT. Die Bilder im Verzeichnis screenshots/ waren von
Hand entstanden und danach nie wieder angefasst worden. Beim Nutzer
kam das als "auch die Screenshots sind veraltet" zurueck - zu Recht:
sie zeigten die Spieleliste von Build 100, die drei Ansichten (Build
122/124) gab es darauf ueberhaupt nicht, und die Hauptseite sah anders
aus als heute.

Ein Bild, das nur einmal von Hand entsteht, veraltet zwangslaeufig.
Dieses Skript macht daraus etwas, das sich nach jedem groesseren Build
in einer Minute neu erzeugen laesst.

WAS ECHT IST UND WAS NICHT. Gezeichnet wird mit fb.rect/fb.text/
draw() - demselben Weg, den das Frontend auf dem Geraet nimmt,
inklusive Overscan, Kastenstufen, Schriften und Farben. Was hier zu
eng aussieht, ist auf dem Geraet auch zu eng.

Nicht echt sind die INHALTE: Spieltitel, Cover und Spielstaende sind
Platzhalter. Cover sind urheberrechtlich geschuetzt und haben in einem
oeffentlichen Bilderverzeichnis nichts verloren - die hier erzeugten
Ersatzcover sind einfache Farbflaechen mit Rahmen und Titelbalken. Die
Sysart-Abzeichen der Hauptseite sind dagegen die echten aus
frontend/sysart, die gehoeren zum Projekt.

Ausfuehren:
    python3 tools/screenshots_bauen.py [Zielordner]
"""
import os
import shutil
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)

import _harness as H                                    # noqa: E402

fm = H.fm
ZIEL = sys.argv[1] if len(sys.argv) > 1 else os.path.join(_REPO,
                                                          "screenshots")

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow fehlt - ohne das kann ich nichts speichern.\n"
             "  pip install Pillow")


# Farben fuer die Ersatzcover. Bewusst kraeftig und unterschiedlich:
# an einer Kachelwand aus Grautoenen sieht man nicht, ob das Raster
# taugt.
FARBEN = [
    (176, 58, 46), (40, 116, 166), (34, 153, 84), (183, 149, 11),
    (125, 60, 152), (23, 165, 137), (211, 84, 0), (52, 73, 94),
    (192, 57, 43), (41, 128, 185), (39, 174, 96), (243, 156, 18),
    (142, 68, 173), (26, 188, 156), (230, 126, 34), (44, 62, 80),
    (169, 50, 38), (36, 113, 163), (30, 132, 73), (185, 119, 14),
]

TITEL = [
    "Super Mario World",
    "The Legend of Zelda - A Link to the Past",
    "König der Löwen",
    "F-Zero",
    "Chrono Trigger",
    "Secret of Mana",
    "Super Metroid",
    "Grüße aus Straßburg",
    "Mega Man X",
    "Donkey Kong Country 2 - Diddy's Kong Quest",
    "Star Fox",
    "Earthbound",
    "Terranigma",
    "Pilotwings",
    "Actraiser",
    "Tetris Attack",
    "Yoshi's Island",
    "Final Fantasy VI",
    "Illusion of Time",
    "Soul Blazer",
]

# Echte Namen und Systemschluessel - zu jedem gibt es eine Datei in
# frontend/sysart, sonst stuenden auf der Hauptseite nur Platzhalter.
KATEGORIEN = [
    ("Favoriten", "FAVORITES"), ("Weiterspielen", "CONTINUE"),
    ("Zuletzt gespielt", "RECENT"), ("Sammlungen", "COLLECTIONS"),
    ("Zufalls-Zock", "WOT"), ("Arcade", "ARCADE"),
    ("NES", "NES"), ("SNES", "SNES"), ("Game Boy", "GAMEBOY"),
    ("Game Boy Color", "GBC"), ("Game Boy Advance", "GBA"),
    ("Nintendo 64", "N64"), ("Mega Drive", "Genesis"),
    ("Master System", "SMS"), ("Game Gear", "GAMEGEAR"),
    ("Mega CD", "MegaCD"), ("PC Engine", "TGFX16"),
    ("Neo Geo", "NEOGEO"), ("Atari 2600", "ATARI2600"),
    ("Atari Lynx", "ATARILYNX"), ("ColecoVision", "COLECOVISION"),
    ("Intellivision", "INTELLIVISION"), ("Computer", "COMPUTER"),
    ("System", "SYSTEM"),
]

_TMP = tempfile.mkdtemp(prefix="screenshots_")


# 400x533 ist kein Zufall. Der groesste Kasten ist der Listenkasten auf
# HDMI (733x909) - ein Cover, das hineinpasst, ohne ganzzahlig
# vergroessert zu werden, laeuft dort durch den Passt-genau-Zweig und
# muss gar nicht verkleinert werden. Beim ersten Anlauf standen hier
# 600x800, und das Skript lief nach zehn Minuten noch: zwanzig Cover
# mal ein halbes Dutzend Kastengroessen mal reine Python-
# Flaechenmittelung. Die Bildgroesse ist fuer Platzhalter voellig egal,
# die Laufzeit nicht.
COVER_B, COVER_H = 400, 533


def cover_bauen(pfad, farbe, w=COVER_B, h=COVER_H):
    """Ein Ersatzcover als .art - Rahmen, Flaeche, Titelbalken.

    Als .art statt PNG, weil das Frontend das ohne Bildbibliothek
    liest: so entstehen die Bilder auch auf einem Rechner ohne libpng
    gleich.

    Gebaut wird ZEILENWEISE aus drei fertigen Mustern statt Punkt fuer
    Punkt - es gibt hier nur drei Sorten Zeile, und eine Schleife ueber
    213 200 Bildpunkte je Cover ist der Unterschied zwischen zwei
    Sekunden und zehn Minuten."""
    import struct
    import zlib
    r, g, b = farbe
    hell = (min(255, r + 55), min(255, g + 55), min(255, b + 55))
    dunkel = (r // 3, g // 3, b // 3)
    rand_x = max(1, w // 14)
    rand_y = max(1, h // 18)

    def zeile(fuellung):
        p = bytes((fuellung[2], fuellung[1], fuellung[0], 255))
        d = bytes((dunkel[2], dunkel[1], dunkel[0], 255))
        return d * rand_x + p * (w - 2 * rand_x) + d * rand_x

    voll = bytes((dunkel[2], dunkel[1], dunkel[0], 255)) * w
    normal = zeile(farbe)
    balken = zeile(hell)
    balken_ab = h * 3 // 4
    balken_bis = balken_ab + max(2, h // 11)

    zeilen = []
    for y in range(h):
        if y < rand_y or y >= h - rand_y:
            zeilen.append(voll)
        elif balken_ab <= y < balken_bis:
            zeilen.append(balken)
        else:
            zeilen.append(normal)
    roh = b"".join(zeilen)
    with open(pfad, "wb") as f:
        f.write(b"ART1" + struct.pack("<HH", w, h) + zlib.compress(roh, 6))


def cover_vorbereiten():
    """Fuer jeden Beispieltitel ein Ersatzcover anlegen und ART_BASE
    darauf zeigen lassen."""
    basis = os.path.join(_TMP, "art")
    os.makedirs(os.path.join(basis, "SNES"), exist_ok=True)
    # Der Dateiname richtet sich nach dem TITEL, nicht nach dem
    # ROM-Pfad - so sucht das Frontend (siehe cover_pfad_und_kasten()).
    # Beim ersten Anlauf hiessen die Dateien "0.art".."19.art", und das
    # Ergebnis war ein Raster aus lauter leeren Kacheln.
    for i, titel in enumerate(TITEL):
        cover_bauen(os.path.join(basis, "SNES", titel + ".art"),
                    FARBEN[i % len(FARBEN)])
    fm.ART_BASE = basis
    fm.ART_HD = basis
    import fe.art as A
    A.ART_BASE = basis
    A.ART_HD = basis
    A._art_index_cache.clear()
    # Der Miniatur-Zwischenspeicher gehoert in den Temporaerordner -
    # sonst schreibt ein Bilderlauf in den echten Cache des Rechners.
    A.THUMB_CACHE_DIR = os.path.join(_TMP, "thumbs")
    os.makedirs(A.THUMB_CACHE_DIR, exist_ok=True)
    fm.SYSART_BASE = os.path.join(_REPO, "frontend", "sysart")
    A.SYSART_BASE = fm.SYSART_BASE


# Spieldaten als Platzhalter. Ohne sie steht in der Infospalte nur der
# Titel, und die Galerie - deren halbe Daseinsberechtigung diese Spalte
# ist - saehe auf dem Bild leer aus. Ein frisch installiertes Frontend
# ohne Artwork-Datenbank sieht tatsaechlich so aus; als Werbebild waere
# es trotzdem irrefuehrend.
META = {
    "Super Mario World": {"year": "1990", "players": "2",
                          "genre": "Jump & Run"},
    "The Legend of Zelda - A Link to the Past":
        {"year": "1991", "players": "1", "genre": "Action-Adventure"},
    "König der Löwen": {"year": "1994", "players": "1", "genre": "Jump & Run"},
    "F-Zero": {"year": "1990", "players": "1", "genre": "Rennspiel"},
    "Chrono Trigger": {"year": "1995", "players": "1", "genre": "Rollenspiel"},
    "Secret of Mana": {"year": "1993", "players": "3",
                       "genre": "Action-Rollenspiel"},
    "Super Metroid": {"year": "1994", "players": "1", "genre": "Action"},
    "Mega Man X": {"year": "1993", "players": "1", "genre": "Action"},
    "Star Fox": {"year": "1993", "players": "1", "genre": "Shooter"},
    "Earthbound": {"year": "1994", "players": "1", "genre": "Rollenspiel"},
}

SPIELZEIT = {
    "Chrono Trigger": {"seconds": 41 * 3600 + 12 * 60, "launches": 23},
    "Super Mario World": {"seconds": 9 * 3600 + 40 * 60, "launches": 14},
    "Secret of Mana": {"seconds": 3 * 3600 + 5 * 60, "launches": 4},
    "Super Metroid": {"seconds": 12 * 3600, "launches": 8},
}


# Beschreibungen als Platzhalter (Build 139). Auf dem Geraet kommen
# sie aus synopsis_de.tsv/synopsis_en.tsv der Artwork-Datenbank unter
# /media/fat/docs; hier wird genau so eine Datei in einem
# Temporaerordner angelegt und DOCS_BASE darauf gezeigt. Damit laeuft
# der Text durch denselben Weg wie spaeter auf dem MiSTer - inklusive
# Namensabgleich und Umbruch.
#
# Die Texte sind eigene Kurzfassungen, nicht die der Datenbank: ein
# Bilderverzeichnis im Repo ist nicht der Ort, fremde Texte zu
# verbreiten.
BESCHREIBUNG = {
    "Super Mario World":
        "Mario und Luigi im Dinosaurierland: 96 Ausgänge, zahlreiche "
        "Geheimwege und der erstmals spielbare Yoshi, der Gegner "
        "verschlucken und dadurch besondere Fähigkeiten erlangen kann. "
        "Startspiel des Super Nintendo und bis heute eine der am "
        "dichtesten gebauten Welten der Reihe.",
    "The Legend of Zelda - A Link to the Past":
        "Link zieht aus, um Zelda und die sieben Weisen zu retten. Das "
        "Abenteuer führt durch eine helle Oberwelt und eine dunkle "
        "Spiegelwelt, zwischen denen man hin und her wechselt, um "
        "Rätsel zu lösen und Wege zu öffnen.",
    "König der Löwen":
        "Jump & Run zum Zeichentrickfilm, in zwei Lebensaltern: erst "
        "als junger Simba, spaeter als ausgewachsener Löwe mit anderen "
        "Fähigkeiten. Bekannt vor allem fuer seinen hohen "
        "Schwierigkeitsgrad.",
    "F-Zero":
        "Rennspiel mit schwebenden Gleitern auf Hochgeschwindigkeits"
        "kursen. Eines der ersten Spiele, das den Mode-7-Effekt des "
        "Super Nintendo fuer eine drehbare Streckenansicht nutzte.",
    "Chrono Trigger":
        "Eine Gruppe von Helden reist durch mehrere Zeitalter, um eine "
        "Katastrophe abzuwenden. Was in einer Epoche geschieht, "
        "verändert die nächste - daraus ergeben sich mehrere "
        "mögliche Enden.",
    "Secret of Mana":
        "Action-Rollenspiel, das bis zu drei Spieler gleichzeitig "
        "zulässt. Statt eines Menüs wählt man Angriffe und Zauber "
        "über einen Ring, der sich um die Figur legt.",
    "Super Metroid":
        "Samus Aran erkundet den Planeten Zebes. Neue Ausrüstung "
        "öffnet Wege, an denen man vorher vorbeigelaufen ist - die "
        "Vorlage fuer ein ganzes Genre.",
    "Mega Man X":
        "Schneller, beweglicher Ableger der Mega-Man-Reihe mit "
        "Wandsprung und Sprint. Besiegte Gegner hinterlassen ihre "
        "Waffe, und die Reihenfolge entscheidet über den "
        "Schwierigkeitsgrad.",
    "Star Fox":
        "Raumkampf in echtem 3D, moeglich durch den Super-FX-Chip im "
        "Modul. Drei Streckenzweige mit steigendem Schwierigkeitsgrad.",
    "Earthbound":
        "Rollenspiel in einer heutigen Vorstadt statt in einer "
        "Fantasiewelt: Baseballschläger statt Schwert, Hamburger "
        "statt Heiltrank, Bus statt Reitvogel.",
}


def beschreibungen_unterschieben():
    """Eine synopsis_de.tsv anlegen und die Datenbank darauf zeigen."""
    import fe.art as A
    import fe.translations as T
    ordner = os.path.join(_TMP, "docs", "SNES", "Artwork")
    os.makedirs(ordner, exist_ok=True)
    with open(os.path.join(ordner, "synopsis_de.tsv"), "w",
              encoding="utf-8") as fh:
        fh.write("#key\tsynopsis\n")
        for titel, text in BESCHREIBUNG.items():
            fh.write("%s\t%s\n" % (titel, text))
    A.DOCS_BASE = os.path.join(_TMP, "docs")
    A.FREMD_ZUSATZ_WURZELN = ()
    A.docs_caches_leeren()
    T.CURRENT_LANG = "de"


def daten_unterschieben():
    """Platzhalter-Spieldaten einhaengen.

    Die Spielzeit kommt NICHT ueber eine Attrappe an einer Funktion,
    sondern ueber die DATEI, aus der sie sonst gelesen wird. Grund: sie
    wird an vier Stellen gelesen (frontend.py, fe/achievements.py,
    fe/playtime.py selbst), und wer nur einen dieser Namen ersetzt,
    bekommt ein Bild, in dem die Galerie Stunden anzeigt und der
    Trophaeenraum daneben lauter Nullen - genau so beim ersten Anlauf
    passiert."""
    import json
    import fe.playtime as PT
    fm.get_meta = lambda syskey, name: META.get(name, {})

    daten = {t: dict(w, syskey="SNES") for t, w in SPIELZEIT.items()}
    pfad = os.path.join(_TMP, "playtime.json")
    with open(pfad, "w") as f:
        json.dump(daten, f)
    PT.PLAYTIME_FILE = pfad

    jahr = os.path.join(_TMP, "playtime_yearly.json")
    import datetime
    with open(jahr, "w") as f:
        json.dump({str(datetime.date.today().year):
                   {t: w["seconds"] for t, w in SPIELZEIT.items()}}, f)
    PT.PLAYTIME_YEARLY_FILE = jahr

    erst = os.path.join(_TMP, "first_played.json")
    with open(erst, "w") as f:
        json.dump({t: "2026-0%d-1%d" % (i + 1, i)
                   for i, t in enumerate(SPIELZEIT)}, f)
    PT.FIRST_PLAYED_FILE = erst


def ohne_vorauslader(f):
    """Den Vorauslader stilllegen.

    Sonst startet ein echter Arbeitsprozess, und der Bild-Cache liefert
    fuer einen Teil der Kacheln "kommt gleich" statt eines Bildes - auf
    dem Geraet richtig, in einem Standbild nur ein halb gefuelltes
    Raster.

    Muss NACH make_frontend() passieren: der Konstruktor setzt
    ART.auslagern selbst und wuerde eine Zuweisung davor
    ueberschreiben."""
    fm.ART.auslagern = None
    f.lader.beenden()
    return f


def speichern(fb, name):
    bild = Image.frombytes("RGBA", (fb.width, fb.height), bytes(fb.buf))
    b, g, r, _a = bild.split()
    Image.merge("RGB", (r, g, b)).save(os.path.join(ZIEL, name),
                                       optimize=True)
    print("    %s  (%dx%d)" % (name, fb.width, fb.height))


def spieleliste(breite, hoehe):
    """Die Spieleliste einer Kategorie, die auch SNES HEISST.

    make_frontend() nimmt die erste Kategorie, die auf dem
    Testrechner existiert - hier "Zufalls-Zock". Fuer ein Bild in der
    README ist das irrefuehrend: es zeigt SNES-Titel unter einer
    Ueberschrift, unter der so nie etwas stuende."""
    H.set_screen(breite, hoehe)
    f = ohne_vorauslader(H.make_frontend(page=1))
    spiele = [(t, "game", ("/f/%d.sfc" % i, ".sfc", "SNES", None, None))
              for i, t in enumerate(TITEL)]
    f.cats = [("SNES", {"folders": {}, "items": spiele}, "SNES")]
    f.cat_i = 0
    f.nav_path = []
    f.item_i = 4
    f.scroll = 0
    f._playtime_cache = dict(SPIELZEIT)
    return f


def hauptseite(breite, hoehe):
    H.set_screen(breite, hoehe)
    f = ohne_vorauslader(H.make_frontend(page=0))
    spiele = [(t, "game", ("/f/%d.sfc" % i, ".sfc", "SNES", None, None))
              for i, t in enumerate(TITEL)]
    f.cats = [(n, {"folders": {}, "items": list(spiele)}, k)
              for n, k in KATEGORIEN]
    f.cat_i = 7                                       # SNES
    return f


def main():
    os.makedirs(ZIEL, exist_ok=True)
    cover_vorbereiten()
    daten_unterschieben()
    beschreibungen_unterschieben()
    print("Bilder nach %s" % ZIEL)

    print("  Hauptseite:")
    for ansicht, name in (("liste", "preview_1_kategorien.png"),
                          ("raster", "preview_7_hauptseite_raster.png"),
                          ("galerie", "preview_8_hauptseite_galerie.png")):
        f = hauptseite(1920, 1080)
        f.ansicht_haupt_setzen(ansicht)
        f.draw()
        speichern(f.fb, name)

    print("  Spieleliste:")
    for ansicht, name in (("liste", "preview_2_spieleliste.png"),
                          ("raster", "preview_9_liste_raster.png"),
                          ("galerie", "preview_10_liste_galerie.png")):
        f = spieleliste(1920, 1080)
        f.ansicht_setzen(ansicht)
        f.draw()
        speichern(f.fb, name)

    print("  Ordner-Navigation:")
    f = spieleliste(1920, 1080)
    _n, node, _k = f.cats[f.cat_i]
    node["folders"] = {
        "Final Fantasy VII": {"folders": {}, "items": [
            ("Final Fantasy VII (Disc 1)", "game",
             ("/f/ff7d1.chd", ".chd", "PSX", None, None)),
            ("Final Fantasy VII (Disc 2)", "game",
             ("/f/ff7d2.chd", ".chd", "PSX", None, None)),
            ("Final Fantasy VII (Disc 3)", "game",
             ("/f/ff7d3.chd", ".chd", "PSX", None, None))]},
        "Metal Gear Solid": {"folders": {}, "items": [
            ("Metal Gear Solid (Disc 1)", "game",
             ("/f/mgs1.chd", ".chd", "PSX", None, None)),
            ("Metal Gear Solid (Disc 2)", "game",
             ("/f/mgs2.chd", ".chd", "PSX", None, None))]},
    }
    node.pop("_display_items_cache", None)
    f.item_i = 0
    f.ansicht_setzen("liste")
    f.draw()
    speichern(f.fb, "preview_3_ordner.png")

    print("  Attract-Modus:")
    f = spieleliste(1920, 1080)
    try:
        f._enter_attract_mode()
        f.draw_attract()
        speichern(f.fb, "preview_4_attract.png")
    except Exception as e:                               # noqa: BLE001
        print("    (uebersprungen: %s)" % e)

    print("  Trophaeenraum und Jahresrueckblick:")
    # Diese beiden zeichnen NICHT nur - sie zeichnen und warten dann auf
    # eine Taste ("beliebige Taste kehrt zurueck"). Ohne Tastatur laeuft
    # das Skript an dieser Stelle endlos; beim ersten Anlauf lief es
    # nach zehn Minuten noch.
    #
    # Die Loesung ist nicht, die Schleife zu umgehen, sondern ihr zu
    # antworten: eine Attrappe liefert beim ersten Lesen "ok". Gezeichnet
    # wurde zu dem Zeitpunkt bereits (fb.flip() steht davor), das Bild
    # steht also vollstaendig im Puffer.
    for name, ruf in (("preview_5_trophaeenraum.png",
                       "draw_trophy_room_screen"),
                      ("preview_6_jahresrueckblick.png",
                       "draw_year_review_screen")):
        f = spieleliste(1920, 1080)
        f.inp.read_action = lambda *a, **k: "ok"
        try:
            getattr(f, ruf)()
            speichern(f.fb, name)
        except Exception as e:                           # noqa: BLE001
            print("    (%s uebersprungen: %s)" % (ruf, e))

    print("  CRT 320x240 - dort entscheidet sich, ob eine Ansicht taugt:")
    for ansicht, name in (("liste", "preview_crt_1_liste.png"),
                          ("raster", "preview_crt_2_raster.png"),
                          ("galerie", "preview_crt_3_galerie.png")):
        f = spieleliste(320, 240)
        f.ansicht_setzen(ansicht)
        f.draw()
        speichern(f.fb, name)
    f = hauptseite(320, 240)
    f.ansicht_haupt_setzen("liste")
    f.draw()
    speichern(f.fb, "preview_crt_0_hauptseite.png")

    shutil.rmtree(_TMP, ignore_errors=True)
    print()
    print("Fertig. Die Inhalte sind Platzhalter, das Layout ist echt.")


if __name__ == "__main__":
    main()
