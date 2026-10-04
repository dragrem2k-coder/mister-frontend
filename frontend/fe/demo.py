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

DEMO_VERSION = 2

# Ab wievielen Eintraegen eine Kategorie fuer die Spieleliste-Stationen
# taugt. Acht ist die Zahl, bei der im kleinsten Fenster (CRT, grosse
# Schrift) ueberhaupt gescrollt wird - darunter steht der Zeiger nur
# herum. Begruendung bei kat_n in lauf().
LISTE_MIN_EINTRAEGE = 8

# Die Vorfuehrung in Stationen. Das Gewicht sagt, welchen ANTEIL der
# Gesamtzeit eine Station bekommt - so bleibt die Laenge einstellbar,
# ohne dass man neun Zahlen von Hand nachzieht.
#
# (schluessel, titel, erklaerung, gewicht)
# WAS DIE EINSTELLUNGS-STATIONEN ZEIGEN, und zwar NAMENTLICH.
#
# NUTZERMELDUNG ZU BUILD 239: "ich sehe am ende immer noch zufalls zock
# anstatt dass dort unter der kategorie ein paar einstellungs sachen
# gezeigt werden. finde ich bloed! dann lieber weniger zeit in denn
# ansichten zeigen dafuer mehr auf die einstellungen hinweisen
# durchscrollen was man alles machen kann mit dem frontend als
# vorfuehrung!"
#
# HIER STAND EINE HEURISTIK, und das war der Fehler: Build 239 stieg in
# den Unterordner mit dem MEISTEN Inhalt ab. Auf dem Pruefstand ist das
# "Anzeige & Sound" mit 27 Eintraegen - auf einem echten Geraet aber
# zaehlen "Scripts" und die Standalone-Cores mit, und die sind bei
# jemandem mit einer gewachsenen Karte schnell groesser. Die
# Vorfuehrung zeigte dann eine Liste von Skriptnamen, und das ist
# genau nicht, was sie zeigen soll.
#
# JETZT STEHEN DIE GRUPPEN NAMENTLICH DA - ueber ihren
# Uebersetzungsschluessel, damit es in beiden Sprachen stimmt. Findet
# sich eine Gruppe auf diesem Geraet nicht, wird ihre Station
# uebersprungen; es wird NICHTS ersetzt. Eine Vorfuehrung, die etwas
# anderes zeigt als angekuendigt, ist schlimmer als eine, die eine
# Station weglaesst.
#
# (schluessel der Gruppe, Titel, Erklaerung, Gewicht)
EINSTELLUNGEN = (
    ("sys_group_display", "Anzeige & Sound",
     "Thema, Schrift, Lochmaske, Hintergrundbild, Ansicht, Overscan.", 1.6),
    ("sys_group_behavior", "Optionen",
     "CRT-Test, Miniaturen vorbereiten, Cores, Filter, Autostart.", 1.4),
    ("sys_group_stats", "Statistiken & Erfolge",
     "Spielzeit, Meilensteine, Pokalregal, Jahresrueckblick, Tagebuch.", 1.0),
    ("sys_group_input", "Eingabe & Sprache",
     "Tasten belegen, Sprache, OK/Zurueck tauschen.", 1.0),
    ("sys_group_maintenance", "Wartung",
     "Neu einlesen, Zwischenspeicher, Boxarts und Spieldaten nachladen.", 1.2),
)

# DIE GEWICHTE SIND NEU VERTEILT (Build 240), genau wie gewuenscht:
# "lieber weniger zeit in denn ansichten zeigen dafuer mehr auf die
# einstellungen hinweisen". Vorher 7,8 Gewicht fuer die Ansichten und
# 1,4 fuer die Einstellungen; jetzt 4,6 gegen 6,2 - die Vorfuehrung
# dreht sich damit um das, was man machen KANN, und nicht mehr um
# Scrollen in sechs Varianten.
STATIONEN = (
    ("titel", "Dragend", "", 0.5),
    ("haupt_liste", "Hauptseite - Liste",
     "Deine Kategorien. Rechts das Cover zum markierten Eintrag.", 0.8),
    ("haupt_raster", "Hauptseite - Raster",
     "Dieselbe Seite als Kachelwand.", 0.6),
    ("haupt_galerie", "Hauptseite - Galerie",
     "Und als Galerie, mit grossem Bild.", 0.6),
    ("liste_liste", "Spieleliste - Liste",
     "Die groesste Kategorie, Eintrag fuer Eintrag.", 1.0),
    ("liste_raster", "Spieleliste - Raster",
     "Dieselben Spiele als Kacheln.", 0.8),
    ("liste_galerie", "Spieleliste - Galerie",
     "Und als Galerie, mit Beschreibung.", 0.8),
) + tuple(("einst:" + schluessel, "Einstellungen - " + titel, erkl, gew)
          for schluessel, titel, erkl, gew in EINSTELLUNGEN) + (
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
    # EINE KATEGORIE MIT DREI EINTRAEGEN IST KEINE VORFUEHRUNG
    # (Build 240). _groesste_kategorie() zaehlt die Eintraege direkt in
    # der Wurzel - bei einer Karte, auf der alles in Unterordnern
    # liegt, kann die groesste davon winzig sein, und dann drei
    # Stationen lang auf einem Eintrag herumzuscrollen sieht nach
    # einem Fehler aus. Lieber weglassen und es ins Log schreiben.
    if kat_i is not None and kat_n < LISTE_MIN_EINTRAEGE:
        if log:
            log("--demo: groesste Kategorie %r hat nur %d Eintraege - "
                "die drei Spieleliste-Stationen fallen aus"
                % (kat_name, kat_n))
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
                if log:
                    log("--demo Station %s UEBERSPRUNGEN (auf diesem "
                        "Geraet nicht vorhanden)" % schluessel)
                continue
            # WAS DIESE STATION WIRKLICH ZEIGT, ins Log (Build 240).
            #
            # WARUM DAS HIER STEHT: zwei Builds hintereinander hat die
            # Vorfuehrung etwas anderes gezeigt als angekuendigt, und
            # beide Male war von hier aus nicht feststellbar, WAS - es
            # hing an Dingen, die nur auf dem Geraet des Nutzers so
            # sind (welche Kategorie die groesste ist, welche
            # Einstellungsgruppen es gibt, wieviele Skripte auf der
            # Karte liegen). Eine Zeile je Station beantwortet das beim
            # naechsten Bericht, statt dass wieder geraten wird.
            if log:
                try:
                    _wo = ("Kategorieliste" if seite == 0
                           else str(fe.cats[fe.cat_i][0]))
                    _n = len(fe._display_items() or ())
                except Exception:                        # noqa: BLE001
                    _wo, _n = "?", -1
                log("--demo Station %-22s Seite %d %-8s zeigt %r "
                    "(%d Eintraege, nav=%r)"
                    % (schluessel, seite, ansicht, _wo, _n,
                       getattr(fe, "nav_path", None)))
            if not _scrollen(fe, BENCH, seite, dauer - vorlauf):
                if log:
                    log("--demo bei Station %s abgebrochen (Taste)"
                        % schluessel)
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
        # DIE EINGABE-UHR NACHSTELLEN (Build 239).
        #
        # WARUM SIE HIER STEHT, und was daran falsch begruendet war:
        # Build 239 hat sie eingebaut, um die Meldung "dann oeffnet er
        # nur zufalls zock und bleibt dort stehen" zu erklaeren - der
        # Attract-Modus (im Menue "Zufalls-Zock - Spiel ziehen")
        # startet nach voreingestellt 90 Sekunden ohne Eingabe, und die
        # Vorfuehrung laeuft 180 Sekunden mit eigener Schleife.
        #
        # DIE ERKLAERUNG WAR FALSCH, und das ist beim Bau von Build 240
        # herausgekommen: --demo ruft nach lauf() sofort _beenden() und
        # sys.exit(0) (siehe den --demo-Zweig in frontend.py). Der
        # Leerlauf-Zweig von run() kommt danach ueberhaupt nicht mehr
        # dran, der Attract-Modus also auch nicht. Die WIRKLICHE
        # Ursache stand in _station_einstellen() und steht dort jetzt
        # auch beschrieben: die Station stieg in den Unterordner mit
        # dem meisten Inhalt ab, und das sind auf einem echten Geraet
        # die Skripte.
        #
        # DIE ZEILE BLEIBT TROTZDEM, aber als das, was sie ist: eine
        # Aufraeumzeile und keine Fehlerbehebung. Eine Vorfuehrung soll
        # keinen drei Minuten alten Eingabezeitpunkt hinterlassen -
        # heute faellt das nicht auf, weil --demo danach beendet; wird
        # die Vorfuehrung je aus dem Menue heraus aufrufbar, faellt es
        # sofort auf. Der finally-Block laeuft auch beim Abbruch durch
        # eine Taste und beim Abbruch in einer Titelkarte; jeder andere
        # Ort waere einer von mehreren.
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
        if schluessel.startswith("einst:"):
            # EINE NAMENTLICH BENANNTE EINSTELLUNGSGRUPPE (Build 240).
            # Begruendung bei EINSTELLUNGEN oben - hier wird NICHT
            # geraten und NICHT ersetzt.
            if sys_i is None:
                return None, None
            ordner = _gruppe_finden(fe, sys_i, schluessel[6:])
            if not ordner:
                return None, None
            fe.page = 1
            fe.cat_i = sys_i
            fe.item_i = 0
            fe.nav_path = [ordner]
            fe.ansicht_setzen("liste")
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


def _gruppe_finden(fe, sys_i, schluessel):
    """Der Ordnername der Einstellungsgruppe zu einem
    Uebersetzungsschluessel - oder "".

    UEBER DEN SCHLUESSEL UND NICHT UEBER DEN DEUTSCHEN TEXT: der
    Ordner heisst auf Englisch "Display & sound" und auf Deutsch
    "Anzeige & Sound". Ein fest eingetragener Text waere auf der
    jeweils anderen Sprache tot, und die Station fiele still aus -
    ohne dass jemand den Zusammenhang zur Spracheinstellung sieht.

    ZWEI VERSUCHE, dann ist Schluss: der uebersetzte Name genau so,
    und derselbe Name ohne Ruecksicht auf Gross- und Kleinschreibung.
    Danach wird NICHT auf einen anderen Ordner ausgewichen - siehe
    EINSTELLUNGEN oben, genau das war der Fehler von Build 239."""
    try:
        knoten = fe.cats[sys_i][1]
        ordner = (knoten.get("folders", {}) or {})
        if not ordner:
            return ""
        from fe.translations import t as _t
        name = _t(schluessel)
        if name in ordner:
            return name
        klein = str(name).strip().lower()
        for vorhanden in ordner:
            if str(vorhanden).strip().lower() == klein:
                return vorhanden
        return ""
    except Exception:                                    # noqa: BLE001
        return ""


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
