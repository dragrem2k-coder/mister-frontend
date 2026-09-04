#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Notausstieg waehrend eines laufenden Cores (F1 sofort oder Esc laenger
halten, ueber die rohe HID-Ebene): MiSTer sperrt die normale evdev-Ebene exklusiv,
sobald ein Core laeuft - die rohe HID-Ebene (/dev/hidrawX) bleibt bei
einer angeschlossenen Tastatur dagegen lesbar. Ausgelagert aus
frontend.py (Modularisierung, Git-Branch 'modular-refactor').
"""
import os, glob, re
from fe.log import LOG

# ----------------------------------------------------------------------------
# NOTAUSSTIEG WAEHREND EINES LAUFENDEN CORES (Esc laenger halten, ueber
# die rohe HID-Ebene)
#
# MiSTer sperrt die normale evdev-Ebene (/dev/input/eventX) exklusiv,
# sobald ein Core laeuft - ein einfaches `cat /dev/input/eventX` liefert
# dann 0 Bytes. Der bisherige F10-/Start+Select-Ausstieg in
# wait_game_exit() liest genau darueber und konnte dadurch vermutlich
# nie tatsaechlich ausgeloest werden. Per gezielter Diagnose (eigens
# dafuer geschriebenes Testwerkzeug, das ein Nutzer waehrend eines
# laufenden Spiels mitlaufen liess) bestaetigt: die ROHE HID-Ebene
# (/dev/hidrawX) liegt darunter und bleibt bei einer angeschlossenen
# TASTATUR lesbar (bei manchen Controller-Empfaengern dagegen nicht -
# deren Tasten laufen offenbar ueber einen anderen, ebenfalls
# gesperrten Kanal). Deshalb: Esc laenger halten ueber die Tastatur als
# zusaetzlicher, zuverlaesslicherer Ausstiegsweg (urspruenglich
# Strg+Alt+Esc, auf Nutzerwunsch vereinfacht).
def _find_keyboard_hidraws():
    """Sucht unter /dev/hidraw* nach ALLEN Schnittstellen einer
    Tastatur - DREISTUFIGE Erkennung, um die Tastatur ueberhaupt zu
    IDENTIFIZIEREN, dann werden ALLE hidraw-Geraete mit demselben
    HID-Namen mit zurueckgegeben (Mehrzahl! - siehe BUGFIX Runde 3).

    BUGFIX Runde 1: die urspruengliche Fassung suchte NUR nach einem
    Geraet, dessen selbstgemeldeter HID-Name das Wort "keyboard"
    enthaelt - funktioniert nur, wenn Hersteller/Modell das Wort
    tatsaechlich im Namen fuehren.

    BUGFIX Runde 2: bInterfaceProtocol==1 ("Boot Protocol") ist im
    USB-HID-Standard zwar definiert, aber OPTIONAL - viele Tastaturen
    implementieren das gar nicht. Dritte Stufe ergaenzt: der HID-
    Report-Deskriptor selbst (VERPFLICHTEND fuer jedes HID-Geraet).

    BUGFIX Runde 3 (per echter Nutzer-Log-Datei bestaetigt - siehe
    Diagnose-Ausgabe: "4 Kandidaten", davon DREI mit identischem Namen
    "KBDFans Tiger80", nur EINER mit bInterfaceProtocol==1): manche
    Tastaturen (v.a. hochwertige mechanische Custom-Boards mit NKRO/
    Rollover-Unterstuetzung) legen GLEICHZEITIG MEHRERE hidraw-
    Schnittstellen unter demselben Namen an - eine "Boot"-Schnittstelle
    (6-Tasten-Rollover, kompatibel, oft die einzige mit
    bInterfaceProtocol==1) UND eine oder mehrere weitere fuer den
    eigentlichen NKRO-Betrieb. Die TATSAECHLICHEN Tastendruecke koennen
    ueber eine DIESER ANDEREN Schnittstellen laufen, nicht ueber die,
    die zufaellig als Erste die Erkennungskriterien erfuellt. Bisher
    wurde IMMER NUR EINE Schnittstelle zurueckgegeben und ueberwacht -
    war das die falsche der mehreren gleichnamigen, blieb Esc trotz
    korrekt erkannter Tastatur wirkungslos.

    Fix: sobald EINE Schnittstelle als Tastatur identifiziert ist,
    werden ZUSAETZLICH alle anderen hidraw-Geraete mit EXAKT demselben
    HID-Namen gesammelt und ALLE gemeinsam zurueckgegeben - der
    Aufrufer (wait_game_exit()) ueberwacht sie dann gleichzeitig, die
    Ambiguitaet "welche der mehreren Schnittstellen ist die richtige"
    muss dadurch gar nicht mehr aufgeloest werden.

    Protokolliert jede Stufe (LOG()) - bisher war die Funktion komplett
    stumm, was jede Ferndiagnose zu einem Ratespiel gemacht hat.

    Bewusst dynamisch (nicht fest verdrahtet) - die hidraw-
    Nummerierung haengt von Anschlussreihenfolge/USB-Bus ab und kann
    sich zwischen Boots verschieben."""
    candidates = sorted(glob.glob("/dev/hidraw*"))
    LOG("_find_keyboard_hidraws: %d Kandidat(en): %s" % (len(candidates), candidates))

    def read_uevent_name(base):
        uevent = "/sys/class/hidraw/%s/device/uevent" % base
        try:
            with open(uevent) as f:
                for line in f:
                    if line.startswith("HID_NAME="):
                        return line[len("HID_NAME="):].strip()
        except OSError:
            pass
        return None

    names = {}
    for path in candidates:
        names[path] = read_uevent_name(os.path.basename(path))
    LOG("_find_keyboard_hidraws: Namen: %s" % names)

    def siblings_with_same_name(found_path):
        """Alle Geraete (inkl. found_path selbst) mit demselben Namen."""
        found_name = names.get(found_path)
        if not found_name:
            return [found_path]
        result = [p for p, n in names.items() if n == found_name]
        LOG("_find_keyboard_hidraws: %d Schnittstelle(n) mit demselben "
            "Namen (%r): %s" % (len(result), found_name, result))
        return sorted(result)

    # Stufe 1: Name enthaelt "keyboard" (schnell, funktioniert oft).
    for path, name in names.items():
        if name and "keyboard" in name.lower():
            LOG("_find_keyboard_hidraws: Stufe 1 (Name) Treffer: %s (%r)" % (path, name))
            return siblings_with_same_name(path)

    # Stufe 2 (Rueckfall): USB-HID-Boot-Protokoll, sofern vorhanden -
    # optional, deshalb kein Treffer bei vielen Tastaturen.
    for path in candidates:
        base = os.path.basename(path)
        device_dir = "/sys/class/hidraw/%s/device" % base
        try:
            real = os.path.realpath(device_dir)
        except OSError:
            continue
        d = real
        for _ in range(4):
            d = os.path.dirname(d)
            proto_file = os.path.join(d, "bInterfaceProtocol")
            try:
                with open(proto_file) as f:
                    if f.read().strip() == "01":
                        LOG("_find_keyboard_hidraws: Stufe 2 (Boot-Protokoll) "
                            "Treffer: %s" % path)
                        return siblings_with_same_name(path)
            except OSError:
                continue

    # Stufe 3 (Rueckfall): HID-Report-Deskriptor selbst - VERPFLICHTEND
    # fuer jedes HID-Geraet, keine optionale Zusatzangabe.
    sig = bytes([0x05, 0x01, 0x09, 0x06])
    for path in candidates:
        base = os.path.basename(path)
        desc_file = "/sys/class/hidraw/%s/device/report_descriptor" % base
        try:
            with open(desc_file, "rb") as f:
                data = f.read()
        except OSError:
            continue
        if sig in data:
            LOG("_find_keyboard_hidraws: Stufe 3 (Report-Deskriptor) "
                "Treffer: %s" % path)
            return siblings_with_same_name(path)

    LOG("_find_keyboard_hidraws: KEIN Treffer in allen drei Stufen - "
        "Esc-Ausstieg wird nicht funktionieren.")
    return []

def _hid_report_has_exit_key(data):
    """Prueft einen rohen HID-Tastatur-Report auf Escape (0x29) -
    UNABHAENGIG von Modifikatortasten (frueher Strg+Alt+Esc, auf
    Nutzerwunsch auf reines Esc vereinfacht, da einfacher zu druecken).

    ENTFERNT (Build 77, Nutzer-Rueckmeldung: "F10 kann auch komplett
    raus, funktioniert genauso wenig"): hier stand zusaetzlich eine
    Pruefung auf 0x44. Bei der Gelegenheit gefunden, WARUM F10 nie
    ausgeloest hat - 0x44 ist im HID-Standard gar nicht F10, sondern
    **F11**. F10 hat die Usage 0x43. Die Taste, die hier all die Zeit
    erkannt wurde, war also F11; F10 selbst kam nie an. Da F10 laut
    Nutzerwunsch ohnehin ersatzlos wegfaellt (F1 uebernimmt, siehe
    _hid_report_has_f1_key() unten), wird die Pruefung ganz entfernt
    statt auf 0x43 korrigiert - sonst wuerde ein F11-Druck im Spiel
    weiterhin unerwartet aussteigen.

    WICHTIG: viele Spiele nutzen Esc selbst schon fuer eigene Pause-/
    Menue-Funktionen - deshalb bleibt die Haltezeit (KBD_COMBO_HOLD,
    siehe wait_game_exit()) als Sicherung bestehen. Ein kurzer,
    normaler Tastendruck im Spiel loest dadurch NICHT versehentlich
    den Ausstieg aus - nur ein bewusst LAENGER GEHALTENES Esc tut das.
    Wer es sofort will, nimmt F1 (siehe unten).

    Der Keycode wird IRGENDWO im Report gesucht, nicht an einer festen
    Position - robuster gegenueber unterschiedlichen Report-Layouts
    (manche Geraete stellen ein Report-ID-Byte voran) als eine feste
    Byte-Position anzunehmen.

    ERWEITERT (uebernommener Vorschlag): NKRO-Bitmap-Report (z.B.
    KBDFans Tiger80 im N-Key-Rollover-Modus) - Tasten kommen dort als
    BITS, nicht als normale Keycodes, die obige Prüfung faengt das
    nicht ab. Report-ID 0x06, dann ein Modifier-Byte, dann die Bitmap.
    Esc = HID-Usage 0x29 -> Bitmap-Byte 5, Bit 1 -> Report-Byte 7,
    Maske 0x02 (auf echter Hardware bestaetigt). Eindeutig Esc (jede
    Taste hat ihr eigenes Bit) - kein Fehl-Trigger."""
    if 0x29 in data:
        return True
    if len(data) > 7 and data[0] == 0x06 and (data[7] & 0x02):
        return True
    return False


def _hid_report_has_f1_key(data):
    """Prueft einen rohen HID-Tastatur-Report auf F1 (HID-Usage 0x3A).

    NEUES FEATURE (Nutzerwunsch: "Esc-Funktion haette ich dann gerne auf
    F1, und die soll so schnell ausloesen wie die F5-Reset-Funktion").

    Warum das mit F1 geht, mit Esc aber ausdruecklich NICHT: viele
    Spiele und Cores benutzen Esc selbst fuer eigene Pause-/Menue-
    Funktionen - deshalb braucht Esc die Haltezeit als Schutz gegen
    versehentliches Aussteigen mitten im Spiel. F1 wird von Cores
    praktisch nie belegt; dort ist ein sofortiges Ausloesen gefahrlos.
    Esc bleibt daneben unveraendert bestehen, mit seiner Haltezeit.

    Bit-Position nach derselben, an zwei Messpunkten bestaetigten Formel
    wie bei Esc und Tab (siehe _hid_report_has_reset_key()):

        Bitmap-Byte = HID-Usage // 8      Report-Byte = Bitmap-Byte + 2
        Bit         = HID-Usage % 8

    F1 (0x3A = 58): Bitmap-Byte 7 -> Report-Byte 9, Bit 2 (Maske 0x04).
    Dasselbe Report-Byte wie F5 (Bit 6, Maske 0x40) - dessen Position
    hat der Nutzer auf echter Hardware bereits bestaetigt, was die
    Formel fuer dieses Byte belegt.
    """
    if 0x3A in data:
        return True
    if len(data) > 9 and data[0] == 0x06 and (data[9] & 0x04):
        return True
    return False

def _hid_report_has_reset_key(data):
    """Wie _hid_report_has_exit_key(), aber fuer F5 (HID-Usage 0x3E) -
    Nutzerwunsch: Reset im laufenden Core (alle Cores, nicht nur RA)
    ueber F5 laenger halten, nach demselben bewaehrten Muster wie der
    Esc/F10-Notausstieg.

    GEAENDERT (Nutzer-Rueckmeldung nach echtem Hardware-Test: 'Tab und
    Reset-Funktion will nicht so recht'): urspruenglich stand hier Tab
    (HID-Usage 0x2B), bewusst OHNE die NKRO-Bitmap-Erweiterung (siehe
    _hid_report_has_exit_key()) - mit der Begruendung, die Esc-
    Bitposition liesse keine verlaessliche Aussage ueber andere Tasten
    zu. Das hat sich als der eigentliche Fehler herausgestellt: ein
    echtes Log zeigte, dass Tab auf der betroffenen NKRO-Tastatur
    (KBDFans Tiger80) niemals ueber den einfachen Byte-Array-Weg
    ankommt (0x2B erscheint dort nie als eigener Byte-Wert) - der
    Ausloeser hat deshalb ueberhaupt nie gefeuert, ganz unabhaengig von
    der gewaehlten Taste.

    Aus genau diesem Log liess sich die Bit-Position fuer Tab auf
    dieser Tastatur erstmals wirklich MESSEN (nicht nur vermuten):
    Report-Byte 7, Bit 3 (Maske 0x08). Zusammen mit der bereits
    vorher bestaetigten Esc-Position (Report-Byte 7, Bit 1) ergibt
    sich ein klares, konsistentes Muster:
        Bitmap-Byte = HID-Usage // 8      Report-Byte = Bitmap-Byte + 2
        Bit         = HID-Usage % 8
    Esc (0x29=41): Bitmap-Byte 5 -> Report-Byte 7, Bit 1 (bestaetigt).
    Tab (0x2B=43): Bitmap-Byte 5 -> Report-Byte 7, Bit 3 (bestaetigt,
    aus dem oben genannten Log).

    F5 (HID-Usage 0x3E=62) nach DERSELBEN Formel: Bitmap-Byte 7 ->
    Report-Byte 9, Bit 6 (Maske 0x40). WICHTIG - ehrlich einzuordnen:
    das ist eine HOCHRECHNUNG anhand von zwei bestaetigten Messpunkten,
    KEINE eigene Messung fuer F5 selbst. Sollte sich das beim naechsten
    Test als falsch herausstellen, zeigt die ohnehin vorhandene
    DIAGNOSE-Protokollierung in wait_game_exit() den tatsaechlichen
    Report - von dort laesst sich die richtige Position dann genauso
    ablesen wie diesmal bei Tab."""
    if 0x3E in data:
        return True
    if len(data) > 9 and data[0] == 0x06 and (data[9] & 0x40):
        return True
    return False
