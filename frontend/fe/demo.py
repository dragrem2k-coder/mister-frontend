# -*- coding: utf-8 -*-
"""--demo: drei Minuten, die alles einmal zeigen (Build 233).

WUNSCH DES NUTZERS: "eventuell sollte man auf dem bildschirm auch dort
einmal die menuepunkte kategorien ect angezeigt bekommen, am besten als
so 3 min demo die alles einmal zeigt".

DER UNTERSCHIED ZU --show, und er ist der Grund fuer ein eigenes Modul:
--show ist ein BERICHT. Er sagt in Worten, was da ist. --demo ZEIGT es -
es laeuft das echte Frontend, mit seinen echten Kategorien, Covern und
Farben. Wer wissen will, wie es sich anfuehlt, soll es sehen und nicht
darueber lesen.

WAS HIER NICHT PASSIERT: ein zweiter Zeichenweg. Gezeigt wird, was das
Frontend ohnehin zeichnet - dieselben Seitenaufbauten, dieselben
Ansichten, dieselbe Schrift, dieselbe Maske. Ein Demo-Modus, der sein
eigenes Bild malt, zeigt am Ende etwas, das es gar nicht gibt. Bewegt
wird deshalb nur der Zeiger, und zwar mit genau der Schrittfunktion,
die auch der Bench benutzt (fe/bench.py: schritt_funktion).

ZWISCHEN DEN STATIONEN steht eine Titelkarte. Das ist bewusst so: eine
dauerhafte Einblendung ueber dem laufenden Bild muesste bei JEDEM
Schritt neu gezeichnet werden und wuerde genau das verfaelschen, was
sie zeigen soll - die Geschwindigkeit.

JEDE TASTE BRICHT AB. Eine Vorfuehrung, die man nicht stoppen kann,
ist eine Zumutung.
"""
import time

DEMO_VERSION = 1

# Die Vorfuehrung in Stationen. Das Gewicht sagt, welchen ANTEIL der
# Gesamtzeit eine Station bekommt - so bleibt die Laenge einstellbar,
# ohne dass man neun Zahlen von Hand nachzieht.
#
# (schluessel, titel, erklaerung, gewicht)
STATIONEN = (
    ("titel", "Dragend", "", 0.5),
    ("haupt_liste", "Hauptseite - Liste",
     "Deine Kategorien. Rechts das Cover zum markierten Eintrag.", 1.4),
    ("haupt_raster", "Hauptseite - Raster",
     "Dieselbe Seite als Kachelwand.", 1.1),
    ("haupt_galerie", "Hauptseite - Galerie",
     "Und als Galerie, mit grossem Bild.", 1.1),
    ("liste_liste", "Spieleliste - Liste",
     "Die groesste Kategorie, Eintrag fuer Eintrag.", 1.6),
    ("liste_raster", "Spieleliste - Raster",
     "Dieselben Spiele als Kacheln.", 1.3),
    ("liste_galerie", "Spieleliste - Galerie",
     "Und als Galerie, mit Beschreibung.", 1.3),
    ("system", "Systemmenue",
     "Alles, was sich einstellen laesst - an einer Stelle.", 1.4),
    ("ende", "Ende der Vorfuehrung", "", 0.5),
)


def _gewicht_summe():
    return sum(st[3] for st in STATIONEN) or 1.0


def _titelkarte(fe, fm, titel, zeilen, sekunden):
    """Eine Zwischenkarte - gross, ruhig, in den eigenen Farben.

    Rueckgabe False, wenn abgebrochen werden soll."""
    fbo = fe.fb
    hg = getattr(fm, "C_BG", (0, 0, 0))
    vg = getattr(fm, "C_TITLE", (255, 255, 255))
    dim = getattr(fm, "C_DIM", (150, 150, 150))
    skala = max(2, min(6, fbo.height // 200))
    fbo.clear(hg)
    y = fbo.height // 2 - 4 * skala * 4
    fbo.text(max(10, (fbo.width - len(titel) * 8 * skala) // 2), y,
             titel, skala, vg)
    y += 14 * skala
    for z in zeilen:
        if not z:
            continue
        k = max(1, skala // 2)
        fbo.text(max(10, (fbo.width - len(z) * 8 * k) // 2), y, z, k, dim)
        y += 12 * k
    fbo.flip()
    return _warten(fe, sekunden)


# ZWEI NOTBREMSEN, und beide haben denselben Grund.
#
# Beide Schleifen unten warten auf die Uhr. Steht die Uhr, laeuft die
# Vorfuehrung ewig - auf einem Geraet, an dem vielleicht gar keine
# Tastatur haengt. Aufgefallen ist das beim Bauen des Tests: der
# Pruefstand friert time.monotonic() ein (siehe tools/_harness.py).
# Dieselbe Lage entsteht im Betrieb, wenn der Eingabe-Faden klemmt und
# jeder read_action() sofort mit einem Fehler zurueckkommt - dann
# schlaeft auch niemand mehr, und die Uhr ist das Einzige, was die
# Schleife noch begrenzt.
#
#   1. DAS WARTEN zaehlt seine Runden mit. Eine Runde dauert TAKT
#      Sekunden, also reichen dauer/TAKT Runden - mit etwas Zugabe.
#   2. DAS SCROLLEN sieht nach 200 Schritten EINMAL nach, ob die Uhr
#      ueberhaupt laeuft. Tut sie es nicht, laesst sich die Station
#      nicht zeitlich begrenzen, und dann ist Aufhoeren richtiger als
#      Weitermachen.
TAKT = 0.05
_UHRPROBE = 200


def _warten(fe, sekunden):
    """Warten und dabei auf eine Taste hoeren. False = abbrechen."""
    inp = getattr(fe, "inp", None)
    ende = time.monotonic() + sekunden
    runden = int(sekunden / TAKT) + 10
    while runden > 0 and time.monotonic() < ende:
        runden -= 1
        if inp is None:
            time.sleep(TAKT)
            continue
        try:
            if inp.read_action(timeout=TAKT) is not None:
                return False
        except Exception:                                # noqa: BLE001
            # Einmal klemmen reicht - wer wiederholt mit einem Fehler
            # antwortet, wird nicht weiter gefragt.
            inp = None
    return True


def _scrollen(fe, BENCH, seite, sekunden):
    """Den Zeiger laufen lassen, solange Zeit ist.

    Gependelt wird im sichtbaren Fenster - sonst laeuft die Haelfte als
    voller Neuaufbau, und die Vorfuehrung saehe langsamer aus, als das
    Frontend ist (derselbe Grund wie in Abschnitt J des Bench)."""
    try:
        schritt = BENCH.schritt_funktion(fe, seite)
        # ERST ZEICHNEN, DANN DIE FENSTERGROESSE HOLEN (Build 239).
        #
        # NUTZERMELDUNG ZU BUILD 233: "der demo mode zuckt in der
        # listen ansicht nur in denn ersten drei zeilen rum".
        #
        # Genau so war es, und der Grund steht in frontend.py:
        # cats_visible und items_visible werden WAEHREND des Zeichnens
        # gesetzt. Wer sie vorher liest, bekommt den Startwert 5 - und
        # fenster_spanne() macht daraus max(2, 5-2) = drei Zeilen. Der
        # Zeiger pendelte also zwischen Zeile 0, 1 und 2, in jeder
        # Ansicht, die ganze Vorfuehrung lang.
        #
        # Ein Schritt zeichnet die Seite und setzt die Werte; erst
        # danach steht die richtige Spanne da.
        schritt(0)
        spanne = BENCH.fenster_spanne(fe, seite)
    except Exception:                                    # noqa: BLE001
        return True
    inp = getattr(fe, "inp", None)
    t0 = time.monotonic()
    ende = t0 + sekunden
    i = 0
    while time.monotonic() < ende:
        try:
            schritt(i % spanne)
        except Exception:                                # noqa: BLE001
            return True
        i += 1
        if i == _UHRPROBE and time.monotonic() <= t0:
            # Die Uhr steht. Ohne sie laesst sich diese Station nicht
            # begrenzen - siehe oben.
            return True
        if inp is not None:
            try:
                if inp.read_action(timeout=0.01) is not None:
                    return False
            except Exception:                            # noqa: BLE001
                inp = None
    return True


def lauf(fe, fm, S, BENCH, sekunden=180.0, log=None):
    """Die Vorfuehrung. Rueckgabe True, wenn sie durchgelaufen ist.

    sekunden ist die GESAMTdauer; die Stationen teilen sie sich nach
    ihrem Gewicht."""
    fbo = getattr(fe, "fb", None)
    if fbo is None:
        return False
    je = float(sekunden) / _gewicht_summe()

    # Den Zustand merken und am Ende zurueckgeben - eine Vorfuehrung
    # darf nicht hinterlassen, dass man woanders steht als vorher.
    merk = {}
    for feld in ("page", "cat_i", "item_i", "nav_path"):
        if hasattr(fe, feld):
            merk[feld] = getattr(fe, feld)
    merk_ansicht = None
    merk_haupt = None
    try:
        merk_ansicht = S.ansicht_lesen()
        merk_haupt = S.ansicht_haupt_lesen()
    except Exception:                                    # noqa: BLE001
        pass

    try:
        kat_i, kat_n, kat_name = BENCH._groesste_kategorie(fe)
    except Exception:                                    # noqa: BLE001
        kat_i, kat_n, kat_name = None, 0, ""
    sys_i = _system_kategorie(fe)
    spiele = _spiele_zaehlen(fe)

    try:
        for schluessel, titel, erklaerung, gewicht in STATIONEN:
            dauer = je * gewicht
            if schluessel == "titel":
                if not _titelkarte(fe, fm, "Dragend",
                                   ("%s Spiele in %d Kategorien"
                                    % (_menge(spiele), _kategorien(fe)),
                                    "", "Eine Vorfuehrung - jede Taste "
                                    "bricht ab."), dauer):
                    return False
                continue
            if schluessel == "ende":
                if not _titelkarte(fe, fm, titel,
                                   ("Alles von hier aus erreichbar:",
                                    "F10 wechselt die Ansicht, F12 oeffnet "
                                    "das MiSTer-OSD.",
                                    "", "python3 frontend.py --show nennt "
                                    "die Zahlen dazu."), dauer):
                    return False
                continue

            # Zwei Drittel der Station gehoeren dem Bild, ein Drittel
            # der Ankuendigung - und die Ankuendigung hoechstens drei
            # Sekunden, sonst wird es zaeh.
            vorlauf = min(3.0, dauer / 3.0)
            zeilen = (erklaerung,)
            if schluessel.startswith("liste") and kat_name:
                zeilen = (erklaerung,
                          "%s - %s Eintraege" % (kat_name, _menge(kat_n)))
            if not _titelkarte(fe, fm, titel, zeilen, vorlauf):
                return False

            seite, ansicht = _station_einstellen(fe, S, schluessel,
                                                 kat_i, sys_i)
            if seite is None:
                continue
            if not _scrollen(fe, BENCH, seite, dauer - vorlauf):
                return False
    finally:
        # Zurueck auf den Stand von vorher - in dieser Reihenfolge:
        # erst die Ansichten, dann die Position, sonst zeichnet der
        # naechste Aufbau mit der falschen Ansicht.
        try:
            if merk_haupt:
                fe.ansicht_haupt_setzen(merk_haupt)
            if merk_ansicht:
                fe.ansicht_setzen(merk_ansicht)
        except Exception:                                # noqa: BLE001
            pass
        for feld, wert in merk.items():
            try:
                setattr(fe, feld, wert)
            except Exception:                            # noqa: BLE001
                pass
        # DIE EINGABE-UHR NACHSTELLEN (Build 239) - und das ist die
        # dritte Haelfte der Nutzermeldung zu Build 233:
        #
        #   "dann oeffnet er nur zufalls zock und bleibt dort stehen"
        #
        # Das war kein Fehler der Vorfuehrung, sondern ihre Folge. Der
        # Attract-Modus (im Menue heisst er "Zufalls-Zock - Spiel
        # ziehen") startet nach ATTRACT_DELAY Sekunden ohne Eingabe,
        # voreingestellt 90. Die Vorfuehrung laeuft 180 Sekunden und
        # hat ihre eigene Schleife - _last_input_time stand danach also
        # drei Minuten in der Vergangenheit, und der ERSTE Leerlauf-
        # Tick nach der Vorfuehrung erfuellte die Bedingung sofort. Was
        # er sah, war ein zufaellig gezogenes Spiel gross im Bild, und
        # was er daraus schloss, war genau richtig benannt.
        #
        # EINE ZEILE, UND SIE GEHOERT HIERHIN: der finally-Block laeuft
        # auch beim Abbruch durch eine Taste und beim Abbruch in einer
        # Titelkarte. Jeder andere Ort waere einer von mehreren.
        try:
            fe._last_input_time = time.monotonic()
        except Exception:                                # noqa: BLE001
            pass
        if log:
            log("--demo beendet")
    return True


def _station_einstellen(fe, S, schluessel, kat_i, sys_i):
    """Seite und Ansicht fuer eine Station setzen.

    Rueckgabe (seite, ansicht) - oder (None, None), wenn die Station
    auf diesem Geraet nicht geht (keine Kategorie, keine Ansicht)."""
    ansicht = schluessel.split("_")[-1]
    try:
        if schluessel.startswith("haupt"):
            fe.page = 0
            fe.ansicht_haupt_setzen(ansicht)
            return 0, ansicht
        if schluessel == "system":
            if sys_i is None:
                return None, None
            fe.page = 1
            fe.cat_i = sys_i
            fe.item_i = 0
            fe.ansicht_setzen("liste")
            # IN EINEN UNTERORDNER HINEIN (Build 239).
            #
            # NUTZERMELDUNG ZU BUILD 233: "system menue und einstellung
            # werden garnicht gezeigt". Die Wurzel der System-Kategorie
            # besteht fast nur aus ORDNERN ("Anzeige & Sound",
            # "Optionen", ...) - wer dort scrollt, sieht sechs
            # Ordnernamen und keine einzige Einstellung. Gezeigt werden
            # soll aber, was sich einstellen laesst.
            #
            # Also eine Ebene tiefer, in den ersten Ordner mit genug
            # Inhalt. Geht das nicht, bleibt es bei der Wurzel - eine
            # Vorfuehrung darf an so etwas nicht scheitern.
            fe.nav_path = []
            try:
                knoten = fe.cats[sys_i][1]
                ordner = sorted((knoten.get("folders", {}) or {}).items(),
                                key=lambda e: -len(
                                    (e[1] or {}).get("items", ()) or ()))
                if ordner and len(
                        (ordner[0][1] or {}).get("items", ()) or ()) >= 4:
                    fe.nav_path = [ordner[0][0]]
            except Exception:                            # noqa: BLE001
                fe.nav_path = []
            return 1, "liste"
        if kat_i is None:
            return None, None
        fe.page = 1
        fe.cat_i = kat_i
        fe.nav_path = []
        fe.item_i = 0
        fe.ansicht_setzen(ansicht)
        return 1, ansicht
    except Exception:                                    # noqa: BLE001
        return None, None


def _system_kategorie(fe):
    """Der Index der System-Kategorie - oder None."""
    try:
        for i, eintrag in enumerate(fe.cats):
            if str(eintrag[0]).strip().lower().startswith("system"):
                return i
    except Exception:                                    # noqa: BLE001
        pass
    return None


def _kategorien(fe):
    try:
        return len([e for e in fe.cats if isinstance(e[1], dict)])
    except Exception:                                    # noqa: BLE001
        return 0


def _spiele_zaehlen(fe):
    try:
        from fe.show import _zaehlen
        return sum(_zaehlen(e[1]) for e in fe.cats
                   if isinstance(e[1], dict))
    except Exception:                                    # noqa: BLE001
        return 0


def _menge(n):
    try:
        return "{:,}".format(int(n)).replace(",", ".")
    except Exception:                                    # noqa: BLE001
        return str(n)
