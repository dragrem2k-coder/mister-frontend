#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MiSTer Custom Frontend - v4.4
=======================================
Reines Standard-Python, keine externen Abhaengigkeiten.

VERSIONIERUNG NEU GEREGELT (Nutzer-Feedback, hier dokumentiert statt
nur "gemerkt": "die Spruenge pro Aenderung sind einfach zu viel" - die
Versionsnummer war zuletzt (v4.0 bis v5.2) fuer praktisch JEDE
einzelne Aenderung hochgezaehlt worden, auch fuer kleine Bugfixes und
Dokumentations-Politur. Das ergab eine zerfledderte, schwer lesbare
Versionshistorie und keine verlaessliche Aussage mehr darueber, wie
GROSS eine Aenderung tatsaechlich war.

Ab hier gilt (Vereinbarung, kein Vorschlag): die Versionsnummer zaehlt
NUR noch bei einem tatsaechlich in sich abgeschlossenen, spuerbaren
Funktionsumfang hoch - neue Faehigkeit, echter Bugfix mit spuerbarer
Auswirkung, oder eine bewusst gebuendelte Sammlung mehrerer kleiner
Aenderungen, die zusammen ausgeliefert werden. Reine interne Politur,
Kommentar-/Dokumentations-Korrekturen oder Testergaenzungen OHNE
Verhaltensaenderung bekommen KEINE eigene Versionsnummer mehr, sondern
werden im laufenden CHANGELOG-Eintrag der aktuellen Version mit
aufgefuehrt. Diese Datei beginnt technisch bei v3.0 neu zu zaehlen -
der komplette bisherige Funktionsumfang (Trophaeenraum, Sammlungen,
Jahresrueckblick, Spieltagebuch, Boot-Fixes, Performance-Arbeit usw.)
bleibt vollstaendig erhalten, nur die Nummerierung wird bewusst
zurueckhaltender.

ZWEITE KONSOLIDIERUNGSRUNDE: trotz der neuen Regelung waren zwischen
v3.0 und v3.5 in kurzer Zeit sechs Versionsnummern entstanden (vor
allem, weil ein kritischer Bug drei Anlaeufe brauchte, bis die echte
Ursache gefunden war). Nutzerwunsch: "bitte alles was ab v3.1 gekommen
ist zusammenfuehren auf v3.2, nicht wieder dieses schnelle
Hochzaehlen". Alles inhaltlich Passierte (Boot-Animation, drei
Bugfix-Anlaeufe, CRT-Textumbruch-Fixes, RA-Vitrine-Cache) bleibt
vollstaendig erhalten - nur als EIN gebuendelter v3.2-Eintrag statt
sechs einzelner.

Neu in v4.2 (BUGFIX: Uhrzeit blieb bei manchen Nutzern trotz
korrekt eingestelltem Zeitzonen-Versatz dauerhaft falsch):
  - Nutzer-Rueckmeldung (Dennsen, UTC+2 eingestellt, Uhr trotzdem
    falsch): der bisherige Neuversuch-Mechanismus fuer eine beim Start
    fehlgeschlagene NTP-Synchronisierung lief NUR ueber
    _maybe_retry_ra() - und der ist an ra_enabled() gekoppelt. Nutzer
    OHNE eingerichtetes RetroAchievements hatten dadurch ueberhaupt
    keinen Wiederholungsmechanismus: schlug der allererste, nicht-
    blockierende NTP-Versuch beim Programmstart fehl (z.B. weil das
    Netzwerk in diesem Moment noch nicht bereit war), blieb die Uhr
    fuer die komplette Sitzung falsch.
  - Fix: neue, von RA komplett unabhaengige _maybe_retry_clock() -
    gleiches Rueckfall-Muster (wachsende Abstaende, max. 5 Versuche),
    aber ausschliesslich an NTP_SYNC_OK gekoppelt statt an
    ra_enabled(). Wird zusaetzlich zu _maybe_retry_ra() aus draw()
    aufgerufen.
  - Getestet: Neuversuch funktioniert nachweislich auch OHNE
    eingerichtetes RA. Backoff-Zeitfenster wird korrekt eingehalten
    (kein zu frueher zweiter Versuch). Nach Ablauf der Backoff-Zeit
    erfolgt zuverlaessig ein weiterer Versuch. Nach erfolgreicher
    Synchronisierung stoppt der Mechanismus korrekt. 70 Kombinationen
    kompletter Regressionstest bestanden.

Neu in v4.1 (NEUES FEATURE: Lautstaerke-Regler, uebernommen aus
einem separat vorbereiteten, auf echter MiSTer-Hardware getesteten
Vorschlag von TheRealSutefan - siehe CHANGES_VOLUME.md):
  - Regler fuer Musik UND Menue-Sounds gemeinsam, Stufen 0/20/40/60/
    80/100%, neuer Menuepunkt "Lautstaerke: X%" in "Anzeige & Sound"
    (direkt nach der Musik-Quelle - Nutzerwunsch, dort einsortiert).
  - Zwei unterschiedliche Mechanismen, da Musik und Menue-Sounds
    technisch verschieden abgespielt werden: Musik laeuft ueber
    mpg123, bekommt den eingebauten Skalierungsfaktor -f (0..32768,
    fuer MP3-Wiedergabe UND Rainwave-Radio). Menue-Sounds sind selbst
    erzeugte WAVs ueber aplay - aplay hat KEINEN Lautstaerke-Schalter,
    die Lautstaerke steckt deshalb in der AMPLITUDE der erzeugten WAV-
    Datei selbst (wird bei einer Aenderung neu erzeugt statt nur neu
    abgespielt).
  - SFX-Neuerzeugung + Musik-Neustart laufen bewusst im Hintergrund-
    Thread (_apply_volume_async(), mit Lock gegen schnelle Mehrfach-
    Druecke) - beides ist auf dem MiSTer traege/blockierend, sollte
    den Menue-Thread nicht einfrieren lassen.
  - Getestet: _mpg_scale() fuer 0/50/100% bestaetigt. Kompletter Zyklus
    (100->0->20->40->60->80->100->0) bestaetigt, inkl. Persistenz.
    mpg123-Aufruf enthaelt nachweislich den korrekten -f-Faktor.
    Menuepunkt sitzt korrekt in "Anzeige & Sound" mit korrekter
    Prozent-Anzeige. 70 Kombinationen kompletter Regressionstest
    bestanden.

Neu in v4.0 (mehrere Aenderungen/Bugfixes aus einer weiteren
Sammel-Rueckmeldung):
  - AENDERUNG: F11 ("Zufallssprung") springt nicht mehr nur zu einem
    zufaelligen Eintrag, sondern waehlt jetzt ein zufaelliges Spiel
    ueber ALLE Systeme hinweg und STARTET es direkt - inklusive der
    RA-Core-Abfrage, falls das getroffene System eine RA-faehige
    Core-Variante hat (dieselbe Abfrage wie beim normalen Betreten
    einer Kategorie).
  - GEPRUEFT (keine Aenderung noetig): "nur Systeme mit vorhandenen
    ROMs anzeigen" ist bereits so - _scan_games_disk() fuegt ein
    System nur hinzu, wenn tatsaechlich Inhalte gefunden wurden.
  - BUGFIX: Core-Auswahl-Titel ("Mega Drive - Core waehlen") lief auf
    CRT ohne jede Breitenpruefung ueber den Rand, das Wort "waehlen"
    verschwand dadurch unsichtbar. Jetzt mit Schriftanpassung
    abgesichert.
  - BUGFIX: Kopfzeile in der Spieleliste schnitt bei langen
    Systemnamen mitten im Wort ab (z.B. "MEGA DR~"). Wird jetzt
    verkleinert statt abgeschnitten.
  - NEUES FEATURE: Attract-Modus-Verzoegerung einstellbar (vorher fest
    auf 90 Sekunden) - neuer Menuepunkt zyklisch durch 30s bis 15min.
  - AENDERUNG: System-Menue umsortiert - Musik-Eintraege (An/Aus,
    Quelle) sind jetzt unter "Anzeige & Sound" zu finden, CRT-Testbild
    ist jetzt unter dem ehemaligen "Verhalten"-Ordner (jetzt
    "Optionen" genannt).
  - BUGFIX: Scripts, die aus dem Frontend gestartet wurden, liefen
    ohne den Wechsel in MiSTers Konsolenmodus (enter_console_mode(),
    sendet F9) - der eigene Framebuffer blieb dadurch vermutlich ueber
    der Text-Konsole liegen, obwohl das Script korrekt auf tty1
    schrieb. run_core()/back_to_frontend() machten diesen Wechsel
    bereits an vergleichbarer Stelle, run_script() bisher nicht.
  - OFFENE FRAGE: "Lautstaerke"-Regelung wurde als zu verschiebender
    Menuepunkt genannt, existiert aber noch gar nicht als Feature
    (nur unabhaengige Kommentare zu Equalizer-Anzeigen gefunden) -
    keine Aenderung vorgenommen, braucht Klaerung, ob das als neues
    Feature gewuenscht ist (Anbindung an MiSTers Audiosystem noetig).
  - Getestet: Core-Auswahl-Titel bleibt komplett im Bild, Kopfzeile
    schneidet nicht mehr ab, neue Attract-Verzoegerung kompletter
    Zyklus + Formatierung + Persistenz bestaetigt, neue Menuestruktur
    (Ordnernamen + Eintrags-Zuordnung) bestaetigt, run_script()-
    Aufrufreihenfolge (enter_console_mode() vor dem eigentlichen
    Start) bestaetigt. 70 Kombinationen kompletter Regressionstest
    bestanden (56 Basis + 2 neue Ordnerpfade).

Neu in v3.9 (mehrere Bugfixes/Aenderungen aus einer groesseren
Sammel-Rueckmeldung):
  - BUGFIX: "Spiele ausser von /media/fat/games werden nicht
    angezeigt" - GAMES_BASES deckte nur usb0 bis usb5 fest ab.
    _discover_games_bases() erkennt jetzt zusaetzlich dynamisch alles,
    was tatsaechlich unter /media eingehaengt ist (Netzlaufwerke,
    hoehere USB-Nummern usw.), die feste Liste bleibt als Ruecksicht-
    nahme zusaetzlich bestehen.
  - AENDERUNG: ROM-Hacks (und aehnlich getaggte Randomizer-Ausgaben)
    wurden bisher als "Junk" komplett ausgefiltert (gleiche Liste wie
    Beta/Proto/Demo). Anders als diese sind Hacks vollstaendige,
    spielbare Inhalte - "(hack" aus JUNK_TAGS entfernt.
  - AENDERUNG: Regions-Entdopplung entfernt - frueher wurde pro Spiel
    nur die "beste" Region behalten (Germany > Europe > World > USA >
    Japan), alle anderen Versionen (PAL/NTSC/etc.) verschwanden
    komplett. Jetzt bleiben alle gefundenen Versionen erhalten und
    waehlbar.
  - BUGFIX: F10 zum Verlassen eines Spiels funktionierte praktisch nie
    (lief bisher ueber dieselbe waehrend des Spielens gesperrte evdev-
    Ebene wie zuvor schon Start+Select). _hid_report_has_esc() ->
    _hid_report_has_exit_key(), prueft jetzt auf Esc UND F10 ueber den
    bereits bestaetigt funktionierenden HID-Weg.
  - GEKLAERT (kein Bug): F11 ("springe zu zufaelligem Eintrag", seit
    v1.28) startet nichts von selbst, sondern bewegt nur die Auswahl -
    im Code bestaetigt. Vermutlich wurde danach noch OK gedrueckt.
  - Neue boxart_download.sh uebernommen (interaktive Profilauswahl SD/
    HD statt fest auf SD, zusaetzlich per SSH-Argument aufrufbar).
  - OFFENE PUNKTE (noch keine Aenderung, brauchen mehr Informationen
    vom Nutzer, bevor blind etwas geaendert wird): "SNES Tracker"-Core
    fehlt in der Kategorienliste (unklar, welche Datei-Endung/welcher
    Core genau gemeint ist); kuratierte Liste "zeigt nicht immer
    korrekt" (vermutlich exakter Namensabgleich gegen die Datenbank,
    braucht ein konkretes Beispiel); Esc-Ausstieg bei Sutefan weiterhin
    ungeklaert (Diagnose zeigt wiederholt NUR das vermutete Status-
    Signal einer Schnittstelle, nichts von den anderen beiden -
    braucht weitere Untersuchung).
  - Getestet: dynamische Geraete-Erkennung mit simuliertem Netzlauf-
    werk UND einer USB-Nummer ausserhalb 0-5 bestaetigt. Kompletter
    Scan-Test bestaetigt: mehrere Regionsversionen bleiben alle
    erhalten, ROM-Hack bleibt erhalten, Beta/Proto werden weiterhin
    korrekt ausgefiltert. Esc- UND F10-Erkennung ueber HID einzeln
    bestaetigt. 56 Kombinationen kompletter Regressionstest bestanden.

Neu in v3.8 (NEUES FEATURE: Rainwave-Internetradio als zweite
Musikquelle, uebernommen aus einem separat vorbereiteten, auf echter
MiSTer-Hardware getesteten Vorschlag - siehe CHANGES_RAINWAVE.md):
  - Neues eigenstaendiges Modul frontend/rainwave.py (reines stdlib,
    passend zur "keine externen Abhaengigkeiten"-Linie): Stationstabelle
    (Game/OCReMix/Covers/Chiptune/All), stream_url(), RainwaveRadio mit
    tick() (pollt alle 15s), now_playing(), set_station(). mpg123 spielt
    den Stream direkt (http, kein https - mpg123 kann das nicht), der
    Titel wird anonym ueber die oeffentliche api4/info-Schnittstelle
    geholt (kein Login noetig).
  - MusicPlayer erweitert: neue Quelle "radio" neben der bisherigen
    "mp3" - cycle_source() schaltet MP3 -> Radio(Game..All) -> MP3 um,
    laesst den bestehenden An/Aus-Zustand unberuehrt. Now-Playing-Titel
    fliesst automatisch ins bestehende Stream-Overlay (kein Overlay-
    Code geaendert).
  - Neuer Menuepunkt "Musik-Quelle" im System-Menue (Verhalten-Ordner,
    direkt unter "Musik").
  - ZUSAETZLICHE ABSICHERUNG gegenueber der uebernommenen Fassung: der
    Import von rainwave steht jetzt in einem try/except (gleiches
    Muster wie beim bestehenden, ebenfalls optionalen stream_server) -
    sollte die Datei beim Kopieren mal fehlen oder aus einem anderen
    Grund nicht laden, bleibt die normale MP3-Wiedergabe unveraendert
    nutzbar statt abzustuerzen; "Musik-Quelle" wird dann zu einem
    stillen No-Op.
  - Getestet: kompletter Quellen-Zyklus MP3 -> alle 5 Sender -> MP3
    bestaetigt, Quelle+Sender bleiben ueber einen Neustart hinweg
    korrekt gespeichert. Menuepunkt-Beschriftung fuer beide Quellen
    ("MP3" bzw. "Radio - <Sender>") bestaetigt. Verhalten OHNE
    geladenes rainwave-Modul einzeln bestaetigt (kein Absturz, no-op).
    56 Kombinationen kompletter Regressionstest bestanden.

Neu in v3.7 (DIAGNOSE-VERSION Teil 2, IMMER NOCH KEIN Fix - der
v3.6-Diagnoseansatz hatte selbst einen Fehler):
  - Sutefans Log zeigte: alle 30 protokollierten Reports kamen von
    hidraw2, mit einem regelmaessig wechselnden Muster (sieht nach
    einem periodischen Status-/Heartbeat-Signal aus, NICHT nach
    Tastendruecken) - hidraw0 und hidraw1, die vermutlich
    tatsaechlichen Tastatur-Schnittstellen, kamen dabei nie zu Wort.
  - Ursache: das Diagnose-Budget aus v3.6 war ein GEMEINSAMES Budget
    ueber alle Schnittstellen hinweg - eine "gespraechige"
    Schnittstelle (hidraw2) konnte dadurch die anderen komplett
    verdraengen, bevor diese ueberhaupt einmal gemeldet wurden.
  - Fix: eigenes Budget PRO Schnittstelle (je 10 statt 30 gemeinsam) -
    jede der drei Schnittstellen bekommt jetzt garantiert ihre eigenen
    Log-Zeilen, unabhaengig davon, wie oft die anderen sich melden.
  - Getestet: genau das beobachtete Muster nachgebaut (eine sehr
    gespraechige Schnittstelle plus eine seltene, aber wichtige) -
    bestaetigt, dass die seltene Schnittstelle jetzt zuverlaessig im
    Log auftaucht, trotz der gespraechigen Konkurrenz. 56
    Kombinationen kompletter Regressionstest bestanden.

Neu in v3.6 (DIAGNOSE-VERSION, KEIN Fix - Esc-Ausstieg funktioniert
trotz v3.5 (korrekt gefundene UND ueberwachte Schnittstellen) bei
Sutefans Tastatur weiterhin nicht):
  - Per Log bestaetigt: alle drei Tiger80-Schnittstellen werden
    korrekt gefunden und ueberwacht (v3.5 arbeitet wie gedacht) - das
    Problem liegt also vermutlich NICHT mehr an der Schnittstellen-
    Auswahl, sondern am REPORT-FORMAT selbst. Vermutung: manche NKRO-
    faehigen Tastaturen senden Tastendruecke als BITMASKE statt als
    Byte-Array von Tastencodes - _hid_report_has_esc() sucht aber nach
    dem blossen Byte-WERT 0x29 irgendwo im Report, was bei einer
    Bitmaske nie zutrifft.
  - Bewusst KEIN weiterer Rate-Versuch diesmal: stattdessen
    Diagnose-Protokollierung ergaenzt, die beim naechsten Testlauf die
    ROHEN BYTES zeigt, die tatsaechlich ankommen, wenn eine Taste
    gedrueckt wird - damit der naechste Fix auf echten Daten statt auf
    einer weiteren Vermutung aufbaut.
  - Protokolliert: welche Schnittstellen erfolgreich geoeffnet wurden
    (falls os.open() fuer eine davon fehlschlagen sollte, war das
    bisher komplett unsichtbar), sowie die rohen Hex-Bytes der ersten
    30 tatsaechlich empfangenen Reports (Budget bewusst ueber ALLE
    Schnittstellen zusammen begrenzt, nicht pro Schnittstelle - sonst
    koennte eine sehr "gespraechige" Schnittstelle das Log fluten).
  - Getestet: Budget-Begrenzung bestaetigt (exakt 30 Diagnose-Zeilen
    trotz 50 simulierter Lesevorgaenge, keine Log-Flut). Oeffnungs-
    Protokollierung bestaetigt. 56 Kombinationen kompletter
    Regressionstest bestanden.

Neu in v3.5 (BUGFIX Runde 3: Esc-Ausstieg endlich per ECHTER Log-
Datei auf die tatsaechliche Ursache zurueckgefuehrt):
  - Nutzer schickte die tatsaechliche Diagnose-Log-Zeile (aus dem
    v3.4-Logging): 4 HID-Kandidaten, davon DREI mit IDENTISCHEM Namen
    "KBDFans Tiger80" (eine hochwertige mechanische Custom-Tastatur),
    nur EINER davon mit bInterfaceProtocol==1. Die Funktion waehlte
    genau diese eine "Boot"-Schnittstelle - aber bei Tastaturen mit
    NKRO/Rollover-Unterstuetzung koennen die TATSAECHLICHEN
    Tastendruecke ueber eine der ANDEREN, gleichnamigen Schnittstellen
    laufen, nicht ueber die zuerst erkannte.
  - Fix: _find_keyboard_hidraw() -> _find_keyboard_hidraws() (Mehrzahl!)
    - identifiziert weiterhin dreistufig, WELCHE Tastatur angeschlossen
    ist, sammelt dann aber ALLE hidraw-Schnittstellen mit demselben
    HID-Namen und gibt sie ALLE zurueck. wait_game_exit() ueberwacht
    jetzt alle gleichzeitig (kbd_fds statt kbd_fd) - welche der
    mehreren Schnittstellen tatsaechlich die Tasten sendet, muss
    dadurch nicht mehr erraten werden.
  - Getestet: das EXAKTE gemeldete Szenario nachgebaut (3x identischer
    Name, nur einer mit Boot-Protokoll, plus ein irrelevantes viertes
    Geraet) - liefert nachweislich alle drei passenden Schnittstellen,
    schliesst das irrelevante Geraet korrekt aus. wait_game_exit()
    zusaetzlich end-to-end getestet: Esc wird nachweislich erkannt,
    wenn es ueber die ZWEITE (nicht die zuerst identifizierte)
    Schnittstelle ankommt - genau der Kern des gemeldeten Problems.
    56 Kombinationen kompletter Regressionstest bestanden.

Neu in v3.4 (BUGFIX Runde 2: Esc-Ausstieg funktionierte bei
denselben zwei Nutzern WEITERHIN nicht, trotz des v3.3-Fixes):
  - Der v3.3-Rueckfall (bInterfaceProtocol==1, "Boot Protocol") reichte
    nicht - dieses Feld ist im USB-HID-Standard zwar definiert, aber
    OPTIONAL. Viele Tastaturen (v.a. kabellose ueber einen Funk-Dongle,
    oder Gaming-/Multimedia-Tastaturen) implementieren das "Boot
    Protocol" gar nicht und melden bInterfaceProtocol=0 - genau bei
    dieser Art Tastatur haette Runde 1 erneut nichts gefunden.
  - Fix: dritte Erkennungsstufe - der HID-Report-Deskriptor selbst
    (im Gegensatz zu bInterfaceProtocol VERPFLICHTEND fuer jedes HID-
    Geraet, keine optionale Zusatzangabe). Sucht nach der Byte-Signatur
    fuer "Usage Page: Generic Desktop" + "Usage: Keyboard" - eine sehr
    verbreitete, gut erkennbare Kennzeichnung in Tastatur-Deskriptoren.
  - ZUSAETZLICH (Lehre aus den ersten beiden gescheiterten Versuchen):
    _find_keyboard_hidraw() protokolliert jetzt jede Stufe (gefundene
    Kandidaten, deren Namen, welche Stufe angeschlagen hat oder ob gar
    keine). Bisher war die Funktion komplett stumm, was jede
    Ferndiagnose zum Ratespiel gemacht hat - sollte auch Stufe 3 noch
    nicht reichen, zeigt das naechste Log wenigstens exakt, was an
    HID-Geraeten tatsaechlich vorhanden war, statt eine vierte
    Vermutung ins Blaue zu riskieren.
  - Getestet: alle drei Stufen einzeln bestaetigt (Namens-Erkennung UND
    Boot-Protokoll-Rueckfall weiterhin als Regression bestaetigt), NEUE
    dritte Stufe bestaetigt GENAU fuer das vermutete Szenario (weder
    Name noch Boot-Protokoll passend, aber Report-Deskriptor eindeutig
    als Tastatur erkennbar). Kein Fehlalarm bei einem Geraet, das in
    KEINER der drei Stufen passt (z.B. eine Maus mit eigenem, klar
    unterscheidbarem Report-Deskriptor). 56 Kombinationen kompletter
    Regressionstest bestanden.

Neu in v3.3 (BUGFIX: Esc-Ausstieg aus dem Spiel funktionierte bei
manchen Nutzern trotz angeschlossener Tastatur ueberhaupt nicht):
  - Nutzer-Rueckmeldung: Esc-Ausstieg laeuft bei einem Nutzer
    zuverlaessig, bei zwei anderen (mit nachweislich angeschlossener
    Tastatur) gar nicht.
  - Ursache gefunden: _find_keyboard_hidraw() suchte NUR nach einem
    Geraet, dessen selbstgemeldeter HID-Name das Wort "keyboard"
    enthaelt - funktioniert nur bei Herstellern/Modellen, die dieses
    Wort tatsaechlich im Namen fuehren (z.B. "Logitech Wireless
    Keyboard" - Zufallstreffer beim ersten Nutzer). Andere Tastaturen
    melden oft nur einen Marken-/Modellnamen ohne dieses Wort - bei
    denen fand die Funktion GAR NICHTS, voellig lautlos (kein Fehler
    im Log, da eine fehlende Tastatur ein regulaerer, erwarteter Fall
    ist).
  - Genau dasselbe Grundmuster war schon einmal in InputManager.
    inject() aufgetreten und dort bereits mit einem zweistufigen
    Rueckfall geloest - _find_keyboard_hidraw() hatte diesen Rueckfall
    bisher NICHT.
  - Fix: zweite Erkennungsstufe als Rueckfall - bInterfaceProtocol==1,
    die im USB-HID-STANDARD SELBST festgelegte Kennung fuer "Boot
    Interface Subclass: Keyboard". Herstellerunabhaengig, kein Namens-
    Ratespiel mehr noetig. Steht am zugehoerigen USB-INTERFACE (nicht
    am HID-Geraet selbst), deshalb wird bis zu vier Verzeichnisebenen
    im sysfs nach oben gesucht.
  - Getestet: mit nachgebauter, realistischer /dev/hidraw+/sys/class/
    hidraw-Verzeichnisstruktur (echte Symlink-Aufloesung, kein reines
    Mocking) - Namens-Erkennung weiterhin bestaetigt (keine
    Regression), der neue Protokoll-Rueckfall bestaetigt GENAU fuer
    das gemeldete Szenario (Tastatur angeschlossen, Name enthaelt
    "keyboard" nicht), UND bestaetigt korrekt KEINEN Fehlalarm bei
    einem Geraet, das weder Name noch Protokoll passend hat (z.B. eine
    Maus). 56 Kombinationen kompletter Regressionstest bestanden.

Neu in v3.2 (Nutzerwunsch: "bitte alles was ab v3.1 gekommen ist
zusammenfuehren auf v3.2, nicht wieder dieses schnelle Hochzaehlen" -
konsolidierte Zusammenfassung von allem, was zwischen dem Start bei
v3.0 und hier passiert ist):

  STANDARD-BOOT-ANIMATION: D-Pad-Symbol, das flackernd "zum Leben
  erwacht", statt eines direkten Sprungs ins Menue, wenn keine eigene
  Boot-Animation existiert (der Normalfall). Komplett aus eigenen
  Zeichen-Mitteln gebaut, bewusst eigenstaendig gestaltet.

  DREI AUFEINANDERFOLGENDE VERSUCHE, EINEN KRITISCHEN BUGFIX ZU FINDEN
  (Nutzer-Rueckmeldung von echter Hardware: nach dem Update auf die
  neue Boot-Animation blieb der Bildschirm schwarz, nichts passierte
  mehr):
  - Versuch 1 (vermutet): flip()/VSync in der neuen Boot-Animation
    koennte so frueh im Programmablauf haengen bleiben - umgangen,
    reichte allein aber nicht.
  - Versuch 2 (vermutet, dann per Test bewiesen): read_action(timeout=
    ...) pruefte die Zeitueberschreitung nur am Schleifenende - ein
    wiederholt fehlschlagender Geraete-Abruf konnte diese Pruefung
    umgehen und die Funktion fuer immer blockieren. Per gezieltem Test
    mit einer dauerhaft fehlschlagenden Simulation nachgewiesen und
    behoben.
  - Versuch 3 (JETZT MIT ECHTER LOG-DATEI BESTAETIGT, die eigentliche
    Ursache): AttributeError: 'Frontend' object has no attribute
    '_ra_lookup' - build_categories() wurde in __init__() aufgerufen,
    BEVOR der RA-Setup-Block das Attribut gesetzt hatte. Reiner
    Reihenfolge-Fehler, betraf nur Nutzer mit eingerichtetem
    RetroAchievements. Keiner der eigenen Regressionstests hatte das
    gefangen, weil sie alle _ra_lookup manuell vorab setzten statt den
    echten Konstruktor zu durchlaufen - jetzt auch DURCH den echten
    Konstruktor getestet.

  CRT-TEXTABSCHNEIDE-/SCROLL-FIXES UEBER NEUN INFO-BILDSCHIRME
  (mehrere Runden Nutzer-Rueckmeldungen, teils mit echten CRT-Fotos):
  - Neue _wrap_text(): bricht Text an WORTGRENZEN um statt hart mitten
    im Wort mit "~" abzuschneiden.
  - Mitwirkende + Geheimnisse: komplett auf scrollbare Liste
    umgestellt (vorher weder scrollbar noch umbruchsicher).
  - Trophaeenraum: Text lief auf CRT quer durchs Boxart-Cover (zu
    wenig Vertikalraum fuer Cover+Statistik+Zusammenfassung
    gleichzeitig). Jetzt: Cover bleibt fest, Statistik+Zusammenfassung
    sind eine gemeinsame SCROLLBARE Liste.
    Zusaetzlicher Bugfix dabei: eine erste Umbruch-Fassung zeigte bei
    versteckten Erfolgen nur die erste umgebrochene Zeile, der Rest
    verschwand STILLSCHWEIGEND - schlimmer als das urspruengliche
    Tilde-Problem. Behoben mit vollstaendiger Mehrzeilen-Darstellung
    UND einer eigenen, breiteren maxc-Berechnung (die vorige Fassung
    teilte sich die fuer Fortschrittsanzeigen eingeschraenkte Breite
    mit Zeilen, die gar keine Fortschrittsanzeige haben).
  - Jahresrueckblick, Spieltagebuch, Hilfe-Uebersicht: Leermeldungen
    und Zeilen ebenfalls umbruchsicher statt abgeschnitten/verloren.
  - Gleiche Schwaeche zusaetzlich in Erfolge-Liste, Top-10-Listen und
    RA-Erfolgs-Vitrine gefunden und mitbehoben.
  - Zeitanzeige bei Fortschrittswerten (war z.B. "14min/100h" -
    unterschiedliche Einheiten nebeneinander): jetzt durchgaengig
    "Stunden dann Minuten" (z.B. "0h 14min/100h 0min").
  - Geheimcode-Popup erschien links unten am Rand statt zentriert -
    jetzt an beiden Anzeigestellen horizontal zentriert.
  - Geklaert (kein Bug): der geheime Sound existiert (vierstufiger
    Klang) - vermutlich nur unhoerbar geblieben, weil Soundeffekte
    grundsaetzlich unterdrueckt werden, solange Musik laeuft.

  NEUES FEATURE: kurzlebiger Cache (15 Minuten) fuer die F6-RA-
  Erfolgs-Vitrine (Nutzerwunsch: "dauert ganz schoen bis die Erfolge
  angezeigt werden, kann man das speichern/beschleunigen?"). Bewusst
  NUR fuer die Vitrine (einmaliges Ansehen eines beendeten Spiels) -
  der separate Hintergrund-Watcher, der waehrend des Spielens auf neu
  verdiente Erfolge lauscht, bleibt bewusst UNGECACHT, damit neue
  Erfolge zeitnah erkannt werden.

  Getestet: durchgaengig mit Regressionstests (56 Kombinationen je
  Zwischenschritt), gezielten Simulationen fuer die schwer
  reproduzierbaren Faelle (dauerhaft fehlschlagende Geraeteabfrage,
  echter Frontend()-Konstruktor-Durchlauf), und Positionsvergleichen
  fuer visuelle Fixes (Popup-Zentrierung). Cache-Logik einzeln fuer
  Treffer/Fehltreffer/Ablauf bestaetigt.

Neu in v3.9 (Credits angepasst: Dfense als Mitwirkender ergaenzt):
  - Nutzerwunsch: "Erstellt von" knapper halten, dafuer Dfense
    bei den Beitraegen ergaenzen.
  - Angepasst in draw_credits_screen() (sichtbarer Menuepunkt) UND im
    Entwicklerraum (draw_dev_room_screen(), Geheimnis) - fuer
    Konsistenz an beiden Stellen gleichermassen aktualisiert.
  - Getestet: "Dfense" ist nachweislich enthalten, alle anderen Namen
    (Dragrem, TheRealSutefan, Dennsen) bleiben unveraendert vorhanden.
    42 Kombinationen kompletter Regressionstest bestanden.

Neu in v3.8 (NEUES FEATURE: Credits-Bildschirm im System-Menue):
  - Nutzerwunsch: kleiner Credits-Teil im System-Menue - Ersteller,
    wer mitgeholfen hat. Anders als der Entwicklerraum (Geheimnis)
    bewusst ein normaler, sichtbarer Menuepunkt.
  - Neuer Bildschirm draw_credits_screen() (System-Menue -> "Mit-
    wirkende"): Ersteller (Dragrem), Beitraege (TheRealSutefan -
    Patches/RA-Werkzeuge/Bugfixes, Dennsen - Streaming und Testen),
    und ein Dank an alle Spieler.
  - Getestet: beide Aufloesungen ohne Absturz, alle Namen nachweislich
    im Text enthalten. 42 Kombinationen kompletter Regressionstest
    bestanden.

Neu in v3.7 (Geheimcodes auf Nutzerwunsch auf reine Tastatur-
Eingabe umgestellt):
  - Nutzer-Nachfrage: wie gibt man das ueberhaupt am Joypad ein? Beim
    Nachschauen: die v3.6-Loesung hatte auf manchen Pads (gerade
    SNES-Nachbauten ohne L2/R2, bei MiSTer-Nutzern verbreitet)
    praktisch KEINE Taste mehr frei, die garantiert wirkungslos ist.
  - Nutzerentscheidung: Codes bewusst NUR per Tastatur eingebbar -
    Pfeiltasten fuer die Richtungen, echte Buchstabentasten fuer die
    Bestaetigungs-Positionen.
  - Dabei ein Gewinn entdeckt: die bestehende Buchstaben-Sprung-Aktion
    ("letter:X", siehe LETTER_KEYS/jump_to_letter()) ist im Hauptmenue
    GENAUSO sicher wie hoch/runter/links/rechts (nur ein harmloser
    Kategorien-Sprung, kein Seitenwechsel, kein Dialog).
  - Neuer Hinweistext auf dem Geheimnisse-Bildschirm: "Codes
    funktionieren nur per Tastatur, nicht per Gamepad" - ehrliche
    Kommunikation der Einschraenkung statt sie zu verschweigen.
  - Getestet: alle Codes end-to-end ueber die echte Hauptschleife -
    waehrend der GESAMTEN Eingabe nachweislich kein Seitenwechsel,
    kein confirm_quit=True. Alle loesen weiterhin korrekt ihre
    jeweilige Aktion aus. Hinweistext auf dem Geheimnisse-Bildschirm
    bestaetigt sichtbar. 42 Kombinationen kompletter Regressionstest
    bestanden.

Neu in v3.6 (ECHTER DESIGNFEHLER behoben: Geheimcodes konnten mit
"ok"/"back" gar nicht vollstaendig eingegeben werden):
  - Scharfe Nutzer-Nachfrage nach der Joypad-Eingabe deckte auf: "ok"
    loest im Hauptmenue IMMER das Betreten der markierten Kategorie
    aus, "back" IMMER die Beenden-Bestaetigung
    (_go_back_or_confirm_quit()) - unabhaengig davon, ob gerade ein
    Geheimcode eingegeben wird. Einer der (kurzen) Codes haette
    dadurch NIE vollstaendig eingegeben werden koennen: der allererste
    Druck auf "ok" haette sofort die Seite gewechselt, wodurch die (an
    Seite 0 gebundene, siehe v3.5) Code-Erkennung sofort abgebrochen
    waere. Weitere Codes waren durch dieselbe Ursache ebenso
    betroffen.
  - Fix: "ok"/"back" durch "favorite" (F8) und "completed" (F7)
    ersetzt - beide nachweislich WIRKUNGSLOS im Hauptmenue (die
    jeweiligen Handler pruefen "nur bei einem echten Spiele-Eintrag
    auf Seite 1"), koennen also gefahrlos als Tastendruck "verbraucht"
    werden, ohne jemals eine Navigation oder einen Dialog auszuloesen.
  - Getestet: alle Codes end-to-end ueber die ECHTE Hauptschleife
    bestaetigt - UND waehrend der GESAMTEN Eingabe nachweislich KEIN
    einziger Seitenwechsel, KEIN einziges Mal confirm_quit=True (per
    Beobachtung von self.page/self.confirm_quit nach JEDER einzelnen
    Aktion der Sequenz, nicht nur am Ende). Alle Codes loesen
    weiterhin korrekt ihre jeweilige Aktion aus - jetzt aber
    tatsaechlich VOLLSTAENDIG eingebbar. REGRESSION bestaetigt: ein
    normales, einzelnes "ok" (kein Code) betritt weiterhin ganz normal
    die Kategorie, ein normales "back" zeigt weiterhin ganz normal den
    Beenden-Dialog. 42 Kombinationen kompletter Regressionstest
    bestanden.

Neu in v3.5 (BUGFIX: Geheimcodes konnten ausserhalb des Hauptmenues
ungewollt ausgeloest werden):
  - Auf Nutzer-Nachfrage ("ist auch wirklich alles bug- und
    fehlerfrei?") nochmal eine gruendliche Endpruefung gemacht - dabei
    gefunden: die Geheimcode-Erkennung (siehe v3.3) prüfte den
    Aktions-Puffer auf JEDER Seite, nicht nur im Hauptmenue (Seite 0)
    wie eigentlich vorgesehen und dem Nutzer auch so kommuniziert.
  - Konkretes Risiko: einer der (kurzen) Codes haette dadurch
    potenziell auch waehrend ganz normaler Navigation in einer
    Spieleliste ungewollt ausloesbar sein koennen - eine Aktion haette
    unerwartet ausgeloest, im schlimmeren Fall waere ein voller
    Bildschirm mitten im Browsen aufgepoppt.
  - Fix: die Pruefung ist jetzt an self.page == 0 gebunden. Auf anderen
    Seiten wird der Puffer aktiv geleert statt "angehalten" - ein
    Seitenwechsel mitten in einer Code-Eingabe bricht den Versuch damit
    sauber ab, statt ihn spaeter im Hauptmenue ueberraschend
    fortzusetzen.
  - Getestet: gezielt nachgestellt (Seite 1, Spieleliste, exakte
    Tastenfolge eines Codes als normale Navigation) - loeste vor dem
    Fix nachweislich aus, danach nachweislich NICHT mehr. Im
    Hauptmenue (Seite 0) funktionieren alle Codes weiterhin
    unveraendert korrekt (Regressionscheck). Zusaetzlich:
    automatisierte Duplikat-/Ungenutzt-Pruefung (AST-Analyse) und
    Uebersetzungsschluessel-Abgleich liefen erneut sauber durch, keine
    weiteren Funde. 42 Kombinationen kompletter Regressionstest
    bestanden.

Neu in v3.4 (NEUES FEATURE: Max-Level-Boot-Effekt - letzter Teil des
"Easter Egg System"):
  - Nutzerwunsch: kurze zusaetzliche Einblendung beim Booten, sobald
    das Frontend-Level das Maximum (5) erreicht hat. Eine komplett
    alternative Boot-Animation waere deutlich aufwendiger gewesen
    (eigene Gestaltung + eigene CRT/HDMI-Performance-Abstimmung, siehe
    Erklaerung im Gespraech) - bewusst zurueckgestellt, dieser Teil
    ist der leichtere, sofort machbare Baustein.
  - Neue Frontend._show_max_level_boot_effect(): eigenstaendige,
    separate Methode - ruehrt die performance-kritische Bildsequenz-
    Schleife in play_boot_animation() bewusst NICHT an (dort wurde
    bereits mehrfach gezielt auf Geschwindigkeit optimiert). Anders
    als die Bildsequenz selbst NICHT durch einen "einmal pro Boot"-
    Marker begrenzt - erscheint bei JEDEM Boot, solange das Level
    gehalten wird.
  - Getestet: unter Max-Level kein Effekt, kein einziger flip()-Aufruf
    (keine verschwendete Zeit). Bei tatsaechlich erreichtem Level 5
    (ueber echten Spielfortschritt: 100h+, 25 durchgespielt, 10
    Systeme, 500 Starts - "legend"-Bedingung) genau EIN flip()-Aufruf
    und ueberspringbare Wartezeit bestaetigt. 42 Kombinationen
    kompletter Regressionstest bestanden.

Neu in v3.3 (NEUES FEATURE: "Easter Egg System" - Frontend-Level +
geheime Cheat-Codes mit echten, wirksamen Freischaltungen):
  - Nutzerwunsch: das Frontend-Level-System (compute_frontend_level(),
    baut komplett auf vorhandenen Daten auf - Spielzeit/Starts/
    versteckte Erfolge, kein neuer Speicherbedarf) UND ein paar
    geheime Cheat-Code-Sequenzen (auf unser Aktions-Vokabular
    uebertragen), jede schaltet ein anderes Geheimnis frei. Details zu
    den einzelnen Codes/Zuordnungen bewusst NICHT hier im Kopfkommentar
    dokumentiert (siehe SECRET_CODES) - sonst waere es kein Geheimnis
    mehr, siehe auch draw_secrets_screen().
  - WICHTIG: Codes sind wiederholbar wie echte Cheat-Codes - jede
    Eingabe loest die Aktion erneut aus, die "neu freigeschaltet"-
    Meldung erscheint aber nur beim allerersten Mal.
  - Neuer Bildschirm draw_secrets_screen() (System-Menue -> "Geheim-
    nisse"): "???" fuer noch nicht Gefundenes, Name + Herkunfts-Hinweis
    nach dem Entdecken - verraet bewusst NIE die genaue Code-Sequenz
    selbst.
  - Getestet: alle 5 Level-Schwellen einzeln an jeder Grenze bestaetigt
    (inkl. "legend" ueberstimmt alles). Alle Codes einzeln erkannt,
    falsche/kurze Sequenzen loesen nichts aus. Kompletter Ablauf ueber
    die ECHTE Hauptschleife bestaetigt: jeder Code loest tatsaechlich
    seine zugehoerige Aktion aus. Wiederholbarkeit bestaetigt (zweite
    Eingabe loest die Aktion erneut aus, aber ohne erneute "neu"-
    Meldung). Geheimnisse-Bildschirm: ohne Freischaltung ueberall
    "???", nach Freischaltung Name+Herkunft korrekt sichtbar, Rest
    bleibt "???". 42 Kombinationen kompletter Regressionstest
    bestanden.

Neu in v3.2 (UEBERNOMMEN aus einer parallelen Entwicklungslinie:
Flackern beim Scrollen + dauerhafte Zeilen-Ueberlappung behoben):
  - Der Nutzer hat in einer separaten Sitzung, ausgehend von unserem
    gemeinsamen v2.0-Stand, denselben Scroll-/Anzeigefehler ueber vier
    Iterationen (dortige v2.1-v2.4) diagnostiziert und behoben, waehrend
    wir hier parallel mit anderen Funktionen weitergemacht haben
    (Weiterspielen-Feintuning, NAS-Option, Erfolgsjaeger, Trophaeenraum-
    Bugfix, RA-Vitrine mit Icons, PNG-Decoder). Diese Version ueberfuehrt
    die dortige, sehr sorgfaeltig diagnostizierte und mit echten
    Regressionstests abgesicherte Fehlerbehebung in unseren aktuellen
    Stand, unter Beibehaltung aller seither entstandenen Funktionen.
  - Ursache (dreistufig diagnostiziert):
    1. Mehrere getrennte flip_rows()-Aufrufe direkt hintereinander beim
       Navigieren (alte Zeile, neue Zeile, Boxart-Panel) - ohne echtes
       Doppelpuffern konnte die Hardware zwischen den Teil-Updates einen
       inkonsistenten Zwischenzustand einlesen (leichtes Flackern).
    2. Der eigentliche Kern: die markierte Zeile hat einen absichtlich
       ueber die eigene Zeile hinausragenden Leucht-Rand. Wurde die
       Zeile DARUEBER vor der Markierung selbst gezeichnet (aufsteigende
       Reihenfolge), blieb der Glow-Bleed auf dem oberen Nachbarn
       DAUERHAFT sichtbar - nichts hat ihn hinterher uebermalt. Nach
       unten fiel das nie auf, weil die naechste Zeile ohnehin danach
       gezeichnet wurde.
    3. Sonderfall: Markierung auf der allerersten sichtbaren Zeile - der
       Bleed geht dann in die Kopfzeile ("X categories") statt in eine
       Listenzeile.
  - Fix, an allen betroffenen Zeichenpfaden konsistent angewendet:
    - Framebuffer: neue VSync-Wartefunktion (_wait_vsync(), einmalig
      getestet, dauerhaft deaktiviert falls nicht unterstuetzt - kostet
      dann nichts mehr) vor flip()/flip_rows().
    - draw_page_cats()/_draw_dynamic_cats(): Zeilen-Zeichenlogik in neue
      _draw_cat_row() ausgelagert, Zeile ueber der Markierung (bzw. die
      Kopfzeile im Sonderfall) wird nach dem Hauptdurchlauf zusaetzlich
      sauber neu gezeichnet.
    - _draw_page_items_impl(): analoge Korrektur fuer die Spieleliste.
    - _draw_dynamic_items(): Zeichenreihenfolge korrigiert - markierte
      Zeile jetzt IMMER zuerst, Nachbarn danach (uebermalen damit
      zuverlaessig). Neuer flip-Parameter (Standard True, unveraendert
      fuer bestehende Aufrufer) fuer gebuendeltes Flippen.
    - _draw_navigate_items(): sammelt jetzt alle Teil-Updates im
      Speicherpuffer und bringt sie in EINEM gemeinsamen flip_rows()-
      Aufruf auf den Schirm statt bis zu drei einzelnen.
  - Getestet: kompletter Regressionstest (42 Kombinationen) nach der
    Uebernahme weiterhin bestanden - nichts von unseren seither
    entstandenen Funktionen (Erfolgsjaeger, RA-Vitrine, Trophaeenraum
    usw.) wurde beeintraechtigt. VSync-Fallback direkt geprueft (erster
    Fehlschlag korrekt vermerkt, danach nie wieder versucht). Neue
    Zeichenreihenfolge in _draw_navigate_items() gezielt nachgewiesen:
    genau EIN gebuendelter flip_rows()-Aufruf statt bis zu drei, die
    NEUE Markierung steht innerhalb ihres Blocks nachweislich VOR ihren
    Nachbarn. Kopfzeilen-Sonderfall (Markierung auf erster sichtbarer
    Zeile) bestaetigt: Kopfzeile wird korrekt erneut gezeichnet.

Neu in v3.1 (Abschliessende Fehlerpruefung vor dem Gesamtpaket -
ein echter Bug gefunden und behoben):
  - Systematische Endpruefung: Syntax aller Dateitypen, kompletter
    Regressionstest, Suche nach doppelten Definitionen/Debug-Resten/
    ungenutzten Funktionen (automatisiert per AST-Analyse), und ein
    Abgleich ALLER t()-Aufrufe gegen die tatsaechlich definierten
    Uebersetzungs-Schluessel.
  - Dabei gefunden: draw_trophy_room_screen() rief bei fehlendem Cover
    t("no_artwork") auf - dieser Schluessel existiert gar nicht (die
    bestehende Konvention nutzt zwei getrennte Schluessel
    "no_artwork_1"/"no_artwork_2", siehe draw_art_panel()). t() selbst
    stuerzt bei einem fehlenden Schluessel zwar nicht ab (faellt auf
    den Schluesselnamen selbst zurueck), aber der interne Bezeichner
    "no_artwork" waere dadurch woertlich auf dem Bildschirm erschienen
    statt eines uebersetzten Texts.
  - Fix: nutzt jetzt dieselben, bereits vorhandenen Schluessel wie
    draw_art_panel() ("no_artwork_1"+"no_artwork_2") statt eines
    nicht existierenden dritten.
  - Nebenbei aufgeraeumt: ein paar aus frueheren Testsitzungen liegen
    gebliebene, nie eingecheckte Debug-/Vorschau-Dateien im Arbeits-
    verzeichnis entfernt (waren nie in Git oder in ausgelieferten
    Paketen enthalten, rein kosmetisch).
  - Getestet: Fix direkt bestaetigt (liefert jetzt "kein Artwork"
    statt des internen Schluesselnamens). Stichprobe der vom
    automatisierten Abgleich als "unbenutzt" gemeldeten Schluessel
    bestaetigt: alle tatsaechlich per Variable (nicht woertlich)
    verwendet, keine echten Karteileichen - nur eine Grenze des
    Pruef-Skripts selbst. 42 Kombinationen kompletter Regressionstest
    nach dem Fix erneut bestanden. Git-Arbeitsverzeichnis final
    "clean" bestaetigt, Build-Ordner exakt deckungsgleich mit dem
    Repo-Stand.

Neu in v3.0 (NEUES FEATURE: eigener PNG-Decoder + echte RA-Erfolgs-
Icons direkt im Frontend - Abschluss der "separaten Option" aus v2.7-
2.9):
  - Nutzerwunsch: RA-Erfolgs-Icons nicht nur im Browser-Overlay
    (der PNG von selbst versteht), sondern auch direkt am MiSTer-
    Bildschirm in der Erfolgs-Vitrine (F6).
  - Neuer, kompletter PNG-Decoder (decode_png()): Chunk-Parsing,
    zlib-Dekompression (Standardbibliothek), volle Zeilen-
    ENTFILTERUNG (alle 5 PNG-Filtertypen inkl. Paeth-Praediktor - der
    eigentlich aufwendige Teil an einem PNG-Decoder), Vereinheit-
    lichung aller unterstuetzten Farbtypen (Graustufen, RGB, Palette+
    Transparenz, Graustufen+Alpha, RGBA) zu einem gemeinsamen RGBA-
    Format. Bewusst eingeschraenkt (lieber None als ein falsches
    Ergebnis): nur 8-Bit-Tiefe, nicht interlaced - deckt praktisch
    jedes uebliche kleine Icon-Bild ab.
  - Neue BadgeCache-Klasse: laedt/dekodiert/cacht RA-Erfolgs-Icons
    fuers Frontend selbst, gleiches Grundprinzip wie ArtCache
    (dauerhafter Datei-Cache + begrenzter Speicher-Cache).
  - draw_ra_showcase_screen() (F6) zeigt jetzt echte Icons neben jedem
    Erfolg - vorab geladen waehrend der "Laedt..."-Anzeige (haelt das
    spaetere Scrollen frei von Netzwerkzugriffen), einfache naechste-
    Nachbar-Skalierung auf einheitliche Groesse, nicht freigeschaltete
    Erfolge dezent abgedunkelt statt komplett auszublenden.
  - Getestet: decode_png() gegen Pillow (Referenz-Bibliothek) bei
    ECHTEN, tool-erzeugten PNG-Dateien byte-identisch bestaetigt (RGBA
    mit Zufallsrauschen, RGB, Palette, Graustufen). Alle 5 Filtertypen
    einzeln mit einem eigenen Test-Encoder verifiziert. Alle Farbtypen
    (inkl. Palette+tRNS-Transparenz) korrekt zu RGBA vereinheitlicht.
    Fehlerfaelle robust (falsche Signatur, kaputte/zufaellige Daten,
    16-Bit, Interlacing, unrealistische Groesse -> alle liefern None,
    nie eine Ausnahme). BadgeCache: Sicherheitspruefung, Download+
    Dekodierung+Speicherung, Speicher-Cache-Treffer, persistenter
    Datei-Cache nach simuliertem Neustart (kein erneuter Download).
    Vitrine mit echten Icons bei CRT UND HDMI ohne Absturz (inkl.
    Skalierung, Abdunklung, Fall "kein Icon vorhanden"). 42
    Kombinationen kompletter Regressionstest bestanden.

Neu in v2.9 (NEUES FEATURE: RA-Erfolgs-Einblendung im Streamer-
Overlay in Echtzeit - Fortsetzung der Vitrine aus v2.7/2.8):
  - Nutzerwunsch: Zuschauer sollen einen RA-Erfolg SOFORT sehen, wenn
    er passiert - nicht erst, wenn das Frontend nach dem Spiel wieder
    sichtbar ist (unsere Hauptschleife steht waehrend des Spielens
    ja still).
  - Neue Frontend._watch_ra_achievements_during_play(): Hintergrund-
    Thread, gestartet in run_core() NUR wenn das Streamer-Overlay
    aktiv ist UND fuer das gestartete Spiel eine RA-GameID bekannt ist
    (kein unnoetiger Netzwerk-/API-Aufwand fuer alle anderen). Fragt
    alle 25s RAs Erfolgsliste fuer GENAU DIESES Spiel ab (nutzt die
    schon vorhandene fetch_ra_game_achievements_bounded()). Erster
    Abruf legt nur die Baseline fest (bereits vorher freigeschaltete
    Erfolge werden NICHT faelschlich als neu gemeldet) - gleiches
    Prinzip wie bei unseren eigenen Erfolgen. Wird beim Spielende
    sauber gestoppt.
  - Overlay-Server (stream_server.py): neue _badge_png() - laedt RAs
    Erfolgs-Icons (schon fertige PNGs, KEINE Formatumwandlung noetig)
    einmalig herunter und speichert sie DAUERHAFT lokal (Icons
    aendern sich nie mehr, sobald ein Erfolg veroeffentlicht ist).
    Abgesichert gegen Pfad-Tricks im Badge-Namen. Neuer /badge-
    Endpunkt, mit langer Browser-Cache-Zeit (anders als /art oder
    /state). Nebenbei einen Bug in _send() gefunden und behoben: das
    Standard-"no-store" wurde bisher IMMER gesetzt, auch wenn per
    extra-Parameter ein anderer Cache-Control-Wert gewuenscht war -
    zwei widerspruechliche Header waeren gleichzeitig gesendet worden.
  - Neue StreamServer.publish_achievement(): eigener SSE-Event-Typ
    ("achievement"), unabhaengig vom normalen Auswahl-State.
  - stream_overlay.html: neue Einblendung oben rechts (kollidiert nie
    mit der normalen Auswahl-Karte, egal welche Ecke dort eingestellt
    ist) - Icon, Titel, Beschreibung, Punkte, blendet nach 8s
    automatisch aus. Neuer Admin-Schalter "Erfolgs-Einblendung".
  - Getestet: Badge-Cache (Sicherheitspruefung, Download+Cache, Cache-
    Treffer ohne erneuten Download, Netzwerkfehler abgefangen).
    _send()-Fix: genau EIN Cache-Control-Header in beiden Faellen statt
    zwei widerspruechlichen. Hintergrund-Beobachtung: Baseline-Erfolg
    wird NICHT gemeldet, waehrend der Sitzung neu erreichter Erfolg
    GENAU EINMAL, keine Wiederholung bei unveraendertem Zustand, kein
    Absturz bei Abfragefehlern. Overlay-Anzeige mit jsdom bestaetigt
    (alle Daten korrekt, Konfigurationsschalter respektiert). Admin-
    Schalter mit jsdom bestaetigt (klickbar, Zustand korrekt
    uebernommen). 42 Kombinationen kompletter Python-Regressionstest
    bestanden.

Neu in v2.8 (F6 (RA-Erfolgs-Vitrine) zeigte ohne RA-Einrichtung
gar keine Rueckmeldung):
  - Nutzer-Nachfrage: F6 ohne RA-Einrichtung wirkte wie eine tote
    Taste - kein Hinweis, nichts passiert sichtbar.
  - Fix: neue Unterscheidung im Handler - "RetroAchievements nicht
    eingerichtet" (ra_showcase_not_setup), wenn ueberhaupt keine
    RA-Konfigurationsdatei existiert, weiterhin getrennt von
    "Keine RetroAchievements-Daten fuer dieses Spiel"
    (ra_showcase_none), wenn RA zwar eingerichtet ist, aber genau
    dieses Spiel keine RA-Daten hat - zwei unterschiedliche, klare
    Meldungen statt einer stillen nichts-passiert-Taste.
  - Getestet: alle drei Faelle einzeln bestaetigt (nicht eingerichtet
    -> klare Meldung; eingerichtet aber kein Treffer -> die ANDERE,
    weiterhin korrekt unterschiedene Meldung; normaler Erfolgsfall
    mit echten RA-Daten -> Vitrine oeffnet sich weiterhin unveraendert
    korrekt, Regressionscheck bestanden). 42 Kombinationen kompletter
    Regressionstest bestanden.

Neu in v2.7 (NEUES FEATURE, bewusst als SEPARATE Option gebaut: RA-
Erfolgs-Vitrine - komplette Erfolgsliste eines Spiels statt nur der
Zahl neben dem Cover):
  - Nutzerwunsch: eine "schicke Pokal-Vitrine" statt nur "X von Y" -
    Name, Beschreibung, Punkte, freigeschaltet/nicht pro Erfolg. Text-
    Fassung zuerst (ohne Icons - dafuer braeuchten wir einen eigenen
    PNG-Decoder, den wir noch nicht haben, siehe unten).
  - Fundament: fetch_ra_progress()/build_ra_lookup() erweitert, um
    zusaetzlich die RA-GameID zu erfassen (war in der Antwort schon
    immer enthalten, wurde bisher nur nicht ausgelesen) - GEGEN DIE
    ECHTE, RECHERCHIERTE API-Antwortform verifiziert. WICHTIG:
    lookup_ra_progress()s bestehende Rueckgabe bleibt UNVERAENDERT
    (weiterhin nur (erreicht, moeglich) oder None) - keine bestehende
    Aufrufstelle musste sich anpassen. Neue, separate
    lookup_ra_game_id() fuer die GameID.
  - Neue fetch_ra_game_achievements()/_bounded(): ruft einen ANDEREN
    RA-Endpunkt auf (Erfolgsdetails zu EINEM Spiel per GameID statt
    der Sammelliste ueber alle Spiele) - komplett eigenstaendig,
    aendert nichts an der bestehenden Fortschrittsabfrage. Feldnamen
    ebenfalls gegen die recherchierte, echte API-Antwortform
    verifiziert (Achievements-Dict mit Title/Description/Points/
    BadgeName/DateEarned).
  - Neuer Bildschirm draw_ra_showcase_screen() - scrollt wie Top-10/
    Erfolge, zwei Zeilen pro Erfolg (Name+Punkte, darunter
    Beschreibung gedimmt). NEUE, eigene Taste F6 -> Aktion
    "ra_showcase", ausgeloest beim Betrachten eines Spiels mit RA-
    Unterstuetzung - komplett getrennt von den bestehenden RA-
    Anzeigen (Cover-Fortschritt/Erfolgsjaeger/Trophaeenraum bleiben
    unangetastet).
  - Naechster Schritt (noch nicht in dieser Version): Overlay-
    Anbindung mit den Erfolgs-Icons - braucht KEINEN eigenen PNG-
    Decoder (der Browser decodiert PNGs selbst), nur Icons cachen und
    ausliefern wie bei den Boxart-Covers.
  - Getestet: GameID-Extraktion gegen die echte API-Antwortform,
    bestehende lookup_ra_progress()-Logik nachweislich UNVERAENDERT
    (Regressionscheck: NES trifft weiterhin nicht SNES, korrekte
    Treffer bleiben korrekt). Neue lookup_ra_game_id() liefert
    korrekte GameIDs. fetch_ra_game_achievements(): Parsing mit der
    recherchierten echten Datenstruktur (Sortierung nach RAs eigener
    Reihenfolge, freigeschaltet-Status korrekt anhand DateEarned),
    fehlerhafter Einzeleintrag wird uebersprungen statt die ganze
    Liste abzubrechen, kein RA eingerichtet -> kein Netzwerkversuch,
    Netzwerkfehler sauber abgefangen. draw_ra_showcase_screen(): alle
    Zustaende (Fehler/leer/viele Eintraege+Scrollen) bei CRT UND HDMI
    ohne Absturz. Vollstaendige Aktions-Einbindung (F6 -> korrekter
    Aufruf mit Name+GameID) end-to-end bestaetigt. 42 Kombinationen
    kompletter Regressionstest bestanden.

Neu in v2.6 (System-Jingles (v2.5) auf Nutzerwunsch wieder
entfernt):
  - Nutzer-Rueckmeldung nach dem Anhoeren: gefielen nicht. Komplett
    zurueckgebaut - SYSTEM_JINGLE_DEFS, _jingle_path(),
    play_system_jingle() entfernt, Aufruf in _enter_category() und
    die Vorab-Erzeugung in _ensure_sfx_files() ebenfalls entfernt.
    Der CRT-Testbild-Bildschirm (ebenfalls aus v2.5) bleibt bestehen -
    davon war nicht die Rede.
  - Getestet: keine Code-Reste mehr (weder SYSTEM_JINGLE_DEFS noch
    play_system_jingle existieren noch), Systemeinstieg funktioniert
    weiterhin unveraendert ohne jede Jingle-Funktion. 42 Kombinationen
    kompletter Regressionstest bestanden.

Neu in v2.5 (ZWEI NEUE FEATURES: System-Jingles beim Betreten eines
Systems + CRT-Testbild im System-Menue):
  - Nutzerwunsch: kurzer, eigener Klang beim Betreten jedes Systems -
    "fuehlt sich wie eine echte Konsole an". BEWUSST eigene, erfundene
    Klaenge (SYSTEM_JINGLE_DEFS, 14 Systeme) - KEINE Nachbildung
    echter Konsolen-Startsounds (Urheberrecht). Spielt NUR beim
    Betreten einer System-Kategorie im Menue, VOR jedem moeglichen
    Core-/Spielstart - kollidiert dadurch grundsaetzlich nicht mit
    einem etwaigen Intro-Video (das erst beim tatsaechlichen
    Spielstart liefe).
  - Neue play_system_jingle(): erzeugt die WAV-Datei bei Bedarf
    einmalig, nutzt danach die BESTEHENDE play_sfx()-Logik unveraendert
    (Pfad wird dort schon aus SFX_DIR+Name gebaut - "jingle_SNES"
    passt genauso wie "move"/"confirm") - respektiert automatisch
    denselben SFX-An/Aus-Schalter und dieselbe "nicht ueber Musik/
    nicht stapeln"-Absicherung, ohne Code-Duplizierung. In
    _ensure_sfx_files() mit vorab-generiert (kein Erzeugungs-Delay
    beim allerersten Betreten eines Systems).
  - Neuer CRT-Testbild-Bildschirm (draw_crt_test_pattern_screen(),
    System-Menue -> "CRT-Testbild"): Geometrie-Rahmen am Bildrand,
    Raster fuer Linearitaet, Zentrierkreuz, Farbbalken - wie das alte
    Servicemenue echter Roehren-Monitore. Bewusst OHNE Overscan-
    Ausgleich - das Testbild soll ja gerade zeigen, wie der Bildschirm
    den vollen Bereich darstellt.
  - Getestet: Jingle-Erzeugung fuer alle 14 Systeme bestaetigt, kein
    Fehler bei unbekanntem/fehlendem Systemschluessel. _enter_category()
    loest den Jingle nachweislich NUR bei echten Systemen aus (nicht
    bei Weiterspielen/Favoriten/Zuletzt gespielt/Scripts/System, die
    alle sk=None haben). _ensure_sfx_files() erzeugt alle Jingles
    korrekt vorab. CRT-Testbild bei beiden Aufloesungen (CRT/HDMI)
    ohne Absturz, visuell ueberprueft. 42 Kombinationen kompletter
    Regressionstest bestanden.

Neu in v2.4 (BUGFIX: Erfolgs-Pop-up blieb beim ersten tatsaechlich
neu erreichten Erfolg aus):
  - Nutzer-Rueckmeldung: 3 verschiedene Systeme gestartet, der
    "Entdecker"-Erfolg wurde korrekt in "Meine Erfolge" als erreicht
    angezeigt - aber beim Zurueckkehren aus dem Spiel kam KEIN Pop-up/
    Ton.
  - Ursache: die Erstlauf-Sonderbehandlung (verhindert eine Pop-up-
    Flut bei laengerer Spielhistorie nach einem Update) sass bisher
    DIREKT in check_new_achievements() und griff beim allerersten
    Aufruf dieser Funktion ueberhaupt. Das konnte aber zufaellig GENAU
    der Moment sein, in dem ein Erfolg WIRKLICH neu erreicht wurde
    (z.B. die allererste jemals gespielte Sitzung, bei der zugleich
    das dritte System erreicht wird) - der Erfolg wurde dadurch
    faelschlich als "schon vorher da gewesen" behandelt.
  - Fix: neue _ensure_achievements_seen_initialized(), explizit in
    Frontend.__init__() aufgerufen - initialisiert die "bereits
    gezeigt"-Baseline GLEICH BEIM START, VOR jeder moeglichen
    Nutzeraktion. check_new_achievements() selbst braucht dadurch
    keine eigene Erstlauf-Sonderbehandlung mehr und meldet
    zuverlaessig JEDEN Erfolg, der NACH dem Start neu erreicht wird -
    auch wenn das schon waehrend der allerersten Sitzung passiert.
  - Getestet: genau das gemeldete Szenario nachgestellt (Frontend-
    Start mit leerem Zustand, direkt in der ERSTEN Sitzung das dritte
    System erreicht) - Pop-up wird jetzt nachweislich korrekt
    ausgeloest. Der urspruengliche Flut-Schutz bleibt bestaetigt
    erhalten: nach einem Update mit bereits laengerer Spielhistorie
    (100h+ Spielzeit, durchgespieltes Spiel, 10 Favoriten) loest der
    Start weiterhin KEINE Pop-ups fuer laengst Erreichtes aus, echte
    neue Fortschritte danach werden aber zuverlaessig gemeldet. 42
    Kombinationen kompletter Regressionstest bestanden.

Neu in v2.3 (NEUES FEATURE: "RA-Erfolgsjaeger" - Spiele mit
ungenutzten RetroAchievements-Erfolgen):
  - Nutzerwunsch: alle Spiele in der Sammlung finden, die RA-
    Erfolge haben, bei denen aber noch NICHTS freigeschaltet wurde -
    "hier warten unbenutzte Erfolge". Design-Entscheidung des Nutzers:
    als eigene Ordnerstruktur (System-Ordner -> Spieleliste darin,
    komplett statt auf eine Anzahl begrenzt), NICHT im System-Menue,
    sondern als eigene Kategorie direkt vor "Scripts" einsortiert.
  - Neue Frontend.build_ra_hunter_category(): geht per
    _attract_games_pool() (bestehende rekursive Sammel-Funktion,
    schon fuer den Attract-Modus da) einmal durch die komplette
    Sammlung, prueft fuer jedes Spiel lookup_ra_progress() - landet in
    der Liste, wenn RA-Daten existieren (total > 0) UND noch nichts
    erreicht wurde (earned == 0). Gruppiert nach System (Ordner-Label
    "<Anzeigename> (<Anzahl>)"), pro System nach Erfolgsanzahl
    absteigend sortiert (die groessten Gelegenheiten zuerst). Liefert
    None (Kategorie taucht dann gar nicht auf), wenn RA nicht
    eingerichtet ist oder nichts passt.
  - Wiederverwendet komplett die BESTEHENDE Ordner-Navigation (wie bei
    eigenen ROM-Unterordnern) - kein neuer Navigationsmechanismus
    noetig, dadurch auch kein zusaetzliches Testrisiko fuer die
    Navigation selbst.
  - Getestet: RA nicht eingerichtet -> keine Kategorie. Mit Daten:
    korrekte Gruppierung nach System (Anzeigename, nicht Systemkey,
    im Ordner-Label), Spiele mit BEREITS erreichten Erfolgen UND
    Spiele OHNE jede RA-Daten werden nachweislich korrekt
    ausgeschlossen. Sortierung nach Erfolgsanzahl absteigend
    bestaetigt. "Alles schon angefangen" -> keine Kategorie bestaetigt.
    Komplette Navigation (Kategorie betreten, Systemordner oeffnen,
    Spiele sehen) im Regressionstest ueberprueft. 64 Kombinationen
    kompletter Regressionstest bestanden (42 Standard + 22 neue mit
    der Erfolgsjaeger-Kategorie und ihrer Ordner-Navigation).

Neu in v2.2 (NEUE OPTION: beim Start auf NAS/Netzwerk warten -
Nutzerwunsch fuer ROMs auf Netzlaufwerk):
  - Nutzer-Hinweis: liegen ROMs auf einem NAS (ueber CIFS/SMB oder NFS
    eingebunden - MiSTer haengt das typischerweise unter /media/fat/
    cifs ein bzw. blendet es direkt in die games-Ordner ein, siehe
    cifs_mount.sh), kann der Scan starten, BEVOR die Verbindung wirklich
    steht. Das Mount-Skript laeuft zeitlich unabhaengig von unserem
    Frontend-Start - echtes Rennen-Risiko beim Booten. Das Ergebnis
    (leer/unvollstaendig) wuerde sogar dauerhaft gecacht werden.
  - Neue Option (Standard AUS - die meisten Nutzer haben SD-Karte/USB,
    fuer die das nur unnoetig verzoegern wuerde): network_wait_enabled()/
    save_network_wait(), Datei network_wait. Neuer Menuepunkt "Beim
    Start auf NAS/Netzwerk warten" im System-Menue.
  - Neue _wait_for_network_ready(): NUR aktiv, wenn eingeschaltet -
    wartet erst auf eine grundlegende Netzwerkverbindung, dann darauf,
    dass sich der Inhalt ALLER GAMES_BASES-Pfade zwischen zwei
    Abfragen nicht mehr aendert. Gleiches Prinzip wie das bestehende
    _wait_for_usb_stable() (inkl. derselben Vorsicht bei einem
    durchgehend leeren, aber stabilen Ergebnis), bewusst NICHT auf
    USB-Pfade beschraenkt, damit auch CIFS/NFS-Einhaengungen erfasst
    werden, unabhaengig vom genauen Mount-Punkt. Eigenstaendige,
    separate Funktion - kein Regressionsrisiko fuer den etablierten
    USB-Fall (_wait_for_usb_stable() selbst unveraendert).
  - Getestet: Standardwert AUS, Speichern/Laden. KRITISCHER Test: bei
    ausgeschalteter Option (Regelfall) kehrt die Wartefunktion
    NACHWEISLICH sofort zurueck (< 0.05s), keinerlei Verzoegerung fuer
    SD-Karte/USB-Nutzer. Bei eingeschalteter Option: kein Netzwerk ->
    wartet bis zum Zeitlimit; Netzwerk da + leerer aber stabiler
    Ordner -> schnell erkannt; Netzwerk da + waehrend der Wartezeit
    befuellter Ordner (simuliert langsam einhaengende NAS) -> wartet
    nachweislich bis zur tatsaechlichen Stabilisierung, nicht nur bis
    zur ersten Pruefung. Menue-Umschalter getestet. 42 Kombinationen
    kompletter Regressionstest bestanden.

Neu in v2.1 ("Weiterspielen" abgestimmt auf TheRealSutefans neues
"ra_lastplayed.sh"-Skript):
  - Nutzeranalyse: TheRealSutefan hat ein neues, ausgereiftes "Last
    Played"-Skript gebaut (ra_lastplayed.sh, nutzt MiSTers eigene
    *_recent_1.cfg-Dateien - erfasst dadurch JEDEN Spielstart, egal ob
    ueber unser Frontend, MiSTers eigenes Menue oder ein anderes Tool)
    und bindet es ueber unseren RECENT_MARKER-Mechanismus (v1.96) ein.
  - Erkannte Reibung: find_continue_game() nutzte bisher IMMER unsere
    eigene, schmalere load_recent()-Liste (nur was ueber UNSER
    Frontend gestartet wurde) - waere zunehmend veraltet/inkonsistent
    gegenueber der darunter angezeigten "Zuletzt gespielt"-Liste,
    sobald ein Marker-Skript wie seines aktiv ist und DIE zeigt.
  - Fix: find_continue_game() bevorzugt jetzt die ueber RECENT_MARKER
    eingebundene externe Liste, FALLS vorhanden (genauere, umfassendere
    Quelle) - ohne aktiven Marker unveraendert unsere eigene Liste.
  - Zweite erkannte Reibung: externe Labels haben ein Core-/RA-Praefix
    (z.B. "RA SNES - Chrono Trigger"), unsere Durchgespielt-Markierung
    speichert aber den REINEN Spielnamen ("Chrono Trigger") - ein
    direkter Abgleich haette nie getroffen, "Weiterspielen" haette
    laengst durchgespielte Titel weiter vorgeschlagen. Neue
    _bare_game_name(): loest den reinen Spielnamen NACH dem ERSTEN
    " - " heraus (nicht dem letzten - ein Bindestrich IM Spielnamen
    selbst, z.B. bei einem Untertitel, bleibt so korrekt erhalten).
  - Getestet: _bare_game_name() fuer alle Praefix-Formen (RA-Core,
    Test-Core, kein Praefix) UND den Sonderfall Bindestrich im
    Spielnamen selbst. find_continue_game() Ende-zu-Ende: ohne Marker
    unveraendert, mit Marker wird die externe Liste bevorzugt
    (neuestes zuerst bestaetigt), und der Praefix-Abgleich funktioniert
    nachweislich (unsere reine Namensmarkierung trifft korrekt auf das
    praefixierte externe Label). 42 Kombinationen kompletter
    Regressionstest bestanden.

Neu in v2.0 (NEUES FEATURE: "Trophaeenraum" - persoenlicher
Profil-Bildschirm):
  - Nutzerwunsch: ein zentraler Screen mit grossem Cover des
    meistgespielten Spiels, Akzentfarbe des Lieblingssystems, Erfolgs-
    Zaehler, kurze "Das bin ich als Retro-Spieler"-Zusammenfassung.
    Baut komplett auf Daten auf, die wir ohnehin schon sammeln - keine
    neue Datenquelle, reine Zusammenfassung.
  - Neue compute_profile_stats(): meistgespieltes Spiel (top_played_
    games()), Lieblingssystem (Summe der Spielzeit PRO System, nicht
    nur das einzelne meistgespielte Spiel - ein System mit mehreren
    mittelmaessig gespielten Titeln kann so vor einem System mit nur
    einem Blockbuster gewinnen), Erfolgs-Zaehler (normale Meilensteine
    + versteckte Erfolge zusammen, 20 insgesamt).
  - Neue system_display_name(): Anzeigename zu einem Systemschluessel
    (z.B. "Genesis" -> "Mega Drive") aus GAME_SYSTEMS abgeleitet.
  - Neuer Bildschirm draw_trophy_room_screen() - Cover mit Akzent-
    rahmen links (gleiches Muster wie draw_attract()), Statistik-Text
    rechts, kurze Zusammenfassung unten. Alle Werte auch bei komplett
    leerer Historie sicher (kein Fehler, sinnvolle Platzhalter). Neuer
    Menuepunkt "Mein Trophaeenraum" im System-Menue.
  - Getestet: compute_profile_stats() leerer Zustand (alles sicher auf
    0/None) UND mit Daten (Lieblingssystem korrekt anhand der
    GESAMTEN Spielzeit pro System ermittelt, nicht nur des einzelnen
    Spiels). system_display_name() fuer bekannte/unbekannte/fehlende
    Schluessel. Bildschirm in allen vier Kombinationen (leer/mit
    Daten x CRT/HDMI) ohne Absturz bestaetigt, visuell ueberprueft.
    42 Kombinationen kompletter Regressionstest bestanden.

Neu in v1.99 (NEUES FEATURE: "Weiterspielen" - intelligenter
Vorschlag ganz oben im Hauptmenue):
  - Nutzerwunsch: statt nur eine chronologische "Zuletzt gespielt"-
    Liste zu zeigen, ein hervorgehobener Vorschlag ganz oben, der
    gezielt das Spiel vorschlaegt, das zuletzt gestartet, aber noch
    NICHT als durchgespielt markiert wurde - "genau hier bist du
    stehengeblieben".
  - Neue find_continue_game(): geht die "Zuletzt gespielt"-Liste
    (neuestes zuerst) durch und liefert den ERSTEN Eintrag, der noch
    nicht durchgespielt ist. None, wenn nichts passt (z.B. alles
    bereits durchgespielt, oder noch nie etwas gestartet) - dann
    taucht die Kategorie einfach gar nicht auf, kein leerer Eintrag.
    Nutzt bewusst NICHT die ueber RECENT_MARKER eingebundene externe
    Liste (TheRealSutefans separates Skript) - die Durchgespielt-
    Markierung ist eine rein eigene Funktion, die nur zur EIGENEN
    "Zuletzt gespielt"-Aufzeichnung sauber passt.
  - Neue Kategorie "Weiterspielen" (enthaelt genau diesen einen
    Vorschlag) erscheint ganz oben im Hauptmenue, VOR "Zuletzt
    gespielt" - Reihenfolge jetzt: Weiterspielen, Zuletzt gespielt,
    Favoriten, jeweils nur wenn tatsaechlich vorhanden.
  - Getestet: kein Vorschlag ohne Spielhistorie, korrekter Vorschlag
    bei einem offenen Spiel, korrekte Reihenfolge aller drei
    Spezialkategorien zusammen, Vorschlag verschwindet nachweislich
    wieder, sobald das betreffende Spiel als durchgespielt markiert
    wird (naechstaelteres offenes Spiel wird dann korrekt vorgeschlagen,
    getestet). Komplette Kategorien-Aufbau-Logik mit vier verschiedenen
    Datenkombinationen einzeln bestaetigt. 42 Kombinationen kompletter
    Regressionstest bestanden (36 Standard + 6 neue mit der
    "Weiterspielen"-Kategorie).

Neu in v1.98 (Start-Beschleunigung durch NTP-Entkopplung + BUGFIX:
Cursor ueberspringt gelegentlich beim Scrollen):
  - Nutzerwunsch (Start-Geschwindigkeit): sync_system_clock_from_ntp()
    wartete bisher immer bis zu ~3s (Thread-Join), BEVOR das Menue
    ueberhaupt aufgebaut wurde. Neuer blocking-Parameter (Standard
    weiterhin True, unveraendertes Verhalten fuer alle anderen
    Aufrufstellen) - der Programmstart nutzt jetzt blocking=False:
    die Synchronisierung laeuft komplett im Hintergrund weiter, das
    Menue erscheint sofort. Kein Stabilitaetsrisiko: der bestehende
    RA-Neuversuch-Mechanismus faengt den Fall "Uhr war beim
    allerersten RA-Abruf noch nicht fertig" schon ab (genau wie
    vorher bei einem regulaeren Timeout). Logik in _apply_ntp_result()
    ausgelagert, damit blockierender und nicht-blockierender Modus
    dieselbe Kernlogik nutzen.
  - BUGFIX (Nutzer-Rueckmeldung: Cursor "ueberspringt" beim Scrollen
    gelegentlich etwas): die Bedingung fuer den leichten Navigations-
    Zeichenpfad (_draw_navigate_items(), fuer EINEN Schritt gebaut)
    pruefte bisher nur die Tastenrichtung (up/down), NICHT ob der
    Schritt durch einen Turbo-Sprung (gehaltene Richtungstaste,
    move_step > 1) tatsaechlich groesser als 1 Position war. Bei
    einem Turbo-Sprung aktualisierte der leichte Pfad nur die
    unmittelbare Umgebung der ALTEN und NEUEN Position, nicht die
    dazwischenliegenden Zeilen - sichtbar als scheinbar uebersprungene
    Zeilen. Fix: der leichte Pfad wird jetzt nur noch bei echtem
    Einzelschritt (move_step == 1) versucht, sonst korrekt der volle,
    immer richtige Aufbau.
  - Getestet: NTP blocking=True (Standard) weiterhin unveraendert,
    blocking=False kehrt nachweislich sofort zurueck (< 0.05s) UND
    setzt die Uhr trotzdem zuverlaessig im Hintergrund. Cursor-Fix:
    echter Durchlauf durch run() mit simuliertem Turbo-Sprung (15x
    schnelles "down") bestaetigt mehrfachen Ruecksprung auf den vollen
    Aufbau; Gegentest mit echten Einzelschritten (deutlicher Abstand
    zwischen den Tastendruecken, kein Turbo-Streak) bestaetigt: der
    leichte Pfad wird weiterhin korrekt genutzt, keine Regression.
    36 Kombinationen kompletter Regressionstest bestanden.

Neu in v1.97 (NEUES FEATURE: Pop-up-Benachrichtigung bei neu
erreichten Erfolgen, mit eigenem Erfolgston):
  - Nutzerwunsch: kurze, dezente Einblendung + Ton, wenn ein Erfolg
    (normaler Meilenstein ODER versteckter Erfolg) neu erreicht wird.
  - Tonerzeugung erweitert: _write_wav_tone()/neue _write_wav_chime()
    teilen sich jetzt einen gemeinsamen Kern (_synth_tone_samples()/
    _write_wav()) - Mehrton-Faehigkeit fuer einen kurzen aufsteigenden
    Doppelklang (SFX_CHIME_DEFS["achievement"]), deutlich von den
    einfachen Sweeps (move/confirm/back) abgesetzt.
  - Neue check_new_achievements(): vergleicht den aktuellen (live
    berechneten) Erfolgs-Stand gegen eine dauerhafte "bereits gezeigt"-
    Liste (ACHIEVEMENTS_SEEN_FILE), liefert nur ECHT NEUE zurueck.
    WICHTIGER Erstlauf-Sonderfall: existiert die Datei noch gar nicht
    (z.B. jemand mit laengerer Spielhistorie nach diesem Update),
    werden bereits erreichte Erfolge NUR stillschweigend markiert,
    OHNE dafuer ein Pop-up auszuloesen - sonst gaebe es beim ersten
    Start eine ganze Flut von Meldungen fuer laengst Erreichtes.
  - _check_achievement_popup()/_notify_new_achievements(): erstere
    liefert bei einem Treffer die fertige Meldung (spielt dabei den
    Ton ab) und laesst den Aufrufer entscheiden, wie er sie anzeigt -
    bei Favorit/Durchgespielt-Umschalten ERSETZT sie die normale
    Standardmeldung ("Favorit hinzugefuegt"), bei der Rueckkehr aus
    einem Spiel (keine eigene Standardmeldung vorhanden) wird direkt
    angezeigt.
  - Eingebunden an drei Stellen: nach jeder Spielsitzung (run_core(),
    NACH back_to_frontend() - damit die Einblendung dessen normalen
    Redraw ueberschreibt statt sofort zu verschwinden), beim Favorit-
    Umschalten, beim Durchgespielt-Umschalten.
  - Getestet: Tonerzeugung byte-identisch fuer die bestehenden Sweeps
    (Regressionscheck der Umstrukturierung), neue Mehrton-Datei mit
    korrekter kombinierter Laenge, _ensure_sfx_files() erzeugt jetzt
    alle vier Toene inkl. des neuen. KRITISCHER Erstlauf-Test:
    simulierter Nutzer mit bereits erreichten Erfolgen (100h+
    Spielzeit, durchgespieltes Spiel) loest beim allerersten Aufruf
    NACHWEISLICH keine Pop-ups aus, Datei wird trotzdem angelegt.
    Danach: genau ein Pop-up fuer einen neu erreichten Erfolg, kein
    wiederholtes Pop-up bei erneuter Pruefung ohne Aenderung. Ton wird
    nur bei einem echten neuen Erfolg abgespielt, nie sonst. 36
    Kombinationen kompletter Regressionstest bestanden.

Neu in v1.96 (Drittes Paket von TheRealSutefan uebernommen + vier
direkt gemeldete Bugfixes):
  - Marker-Mechanismus (RECENT_MARKER=".frontend_recent"): ein
    externes Skript (TheRealSutefans separates, noch in Arbeit
    befindliches "Recently Played"-Skript) kann einen _*-Ordner als
    "Zuletzt gespielt"-Quelle kennzeichnen - dann nach Aktualitaet
    (Datei-mtime) sortiert, korrekte Cores inkl. RA-Varianten, kein
    Doppel-Listing (der markierte Ordner wird aus scan_cores()
    ausgeschlossen). OHNE ein solches Skript (Normalfall) unveraendert.
  - Boot-Ueberwachung (_active_vt()/_boot_watch()): reine Diagnose fuer
    das Soft-Reboot-Problem (manchmal OSD statt Frontend nach einem
    Neustart) - protokolliert 30s lang VT+CORENAME, um ein moegliches
    Timing-Rennen sichtbar zu machen. Aendert selbst nichts am
    Verhalten.
  - Overlay-Timing-Fix: _publish_stream() wird jetzt VOR dem
    blockierenden next_action() aufgerufen statt danach - vorher hing
    das Overlay einen Schritt hinterher (zeigte das vorherige Spiel,
    bis die naechste Eingabe kam).
  - BUGFIX (Nutzer-Rueckmeldung, ernst): aus der RA-Core-Auswahl kam
    man mit KEINER Taste zurueck. Ursache: draw_core_choice_screen()
    lieferte bei ESC/back IMMER False ("normaler Core") zurueck - der
    Aufrufer (_enter_category()) konnte das nicht von einer bewussten
    OK-Bestaetigung fuer "normal" unterscheiden und ist deshalb IMMER
    in die Kategorie gewechselt, auch bei ESC. Fix: ESC liefert jetzt
    explizit None, und NUR das bricht das Betreten der Kategorie
    wirklich ab (Seite 0 bleibt bestehen).
  - BUGFIX (Nutzer-Rueckmeldung): auf CRT passten bei beiden Top-10-
    Listen und beim Erfolge-Bildschirm nur ein Bruchteil der Zeilen auf
    den Bildschirm (fb.text() bricht bei Ueberlaenge still ab) - der
    Rest war schlicht nicht erreichbar. Beide Bildschirme scrollen
    jetzt mit Hoch/Runter, wenn noetig (Scroll-Hinweis statt des
    normalen Bedienhinweises), mit sauberer Grenzpruefung.
  - BUGFIX (Nutzer-Rueckmeldung): der Titel "TOP 10 - MEISTGESTARTET"
    (23 Zeichen) war bei der festen CRT-Skalierung breiter als der
    Bildschirm und wurde abgeschnitten. Neue _fit_scale(): waehlt die
    groesste Skalierung, mit der ein Text noch in die verfuegbare
    Breite passt - auf beide Top-10-Titel UND den Erfolge-Titel
    angewendet.
  - Getestet: Marker-Mechanismus mit und ohne Marker (unveraendertes
    Verhalten ohne, korrekte Sortierung/kein Doppel-Listing mit).
    Boot-Watch: Drosselung, 30s-Fenster. Core-Auswahl-Fix: alle drei
    Faelle (ESC bricht wirklich ab, explizite Normal-Wahl, explizite
    RA-Wahl) einzeln bestaetigt. _fit_scale() mit dem exakt gemeldeten
    Titel getestet. Scrollen: CRT-Sichtbarkeit direkt nachgerechnet (5
    von 10 bzw. 4 von 21 Zeilen sichtbar - Scrollen tatsaechlich
    noetig), Grenzpruefung bei deutlich zu vielen Tastendruecken in
    beide Richtungen, HDMI (kein Scrollen noetig) funktioniert
    weiterhin mit einem einzelnen Tastendruck. Visuelle Ueberpruefung
    des CRT-Top-10-Bildschirms. 36 Kombinationen kompletter
    Regressionstest bestanden.

Neu in v1.95 (BUGFIX: Spielzeit-Fortschritt zeigte rohe Sekunden;
NEUES FEATURE: fuenf versteckte Erfolge):
  - Nutzer-Rueckmeldung: "warum steht da 198/3600" - die Meilenstein-
    Anzeige zeigte bei Spielzeit-Kategorien die rohe Sekundenzahl statt
    einer lesbaren Zeit. Neue _format_seconds_short() (wie
    format_playtime(), aber liefert IMMER einen Text, auch unter einer
    Minute). get_milestones() liefert jetzt zusaetzlich "kind" mit,
    damit draw_milestones_screen() Spielzeit-Werte als "3min"/"1h"
    statt als rohe Zahl anzeigt.
  - Nutzerwunsch: ein paar versteckte Erfolge. Fuenf neue, in zwei
    Arten: EREIGNIS-basiert (Nachteule: Spiel zwischen 0-5 Uhr
    gestartet; Marathon: eine Sitzung 3+ Stunden am Stueck) - haengen
    von einem bestimmten Moment ab, brauchen eine eigene dauerhafte
    Freischalt-Markierung (HIDDEN_UNLOCKED_FILE), geprueft in
    run_core() nach jeder Sitzung. LIVE-berechnet (Sammlerin: 10
    Favoriten gleichzeitig; Stammspieler: ein Spiel 20+ mal gestartet;
    Legende: alle vier hoechsten Meilensteine gleichzeitig erreicht) -
    wie die normalen Meilensteine bei jedem Aufruf neu aus dem
    aktuellen Datenstand berechnet. Werden im Erfolge-Bildschirm als
    "???" gezeigt, bis sie erreicht sind - Name/Beschreibung bleibt
    bis dahin verborgen.
  - Getestet: Formatierung fuer alle Groessenordnungen (Sekunden,
    Minuten, Stunden) sowie genau den gemeldeten Fall (198 Sekunden).
    Versteckte Erfolge einzeln: Freischalten/Wiederholtes-Freischalten,
    Sammlerin exakt bei 10 Favoriten, Stammspieler exakt bei 20 Starts
    EINES Spiels, Legende nur wenn ALLE vier Bedingungen gleichzeitig
    erfuellt sind. Ereignis-basierte Pruefung: Marathon loest bei 3+
    Stunden aus, NICHT bei kurzen Sitzungen; Nachteule loest bei einem
    Start zwischen 0-5 Uhr aus, NICHT tagsueber. Einbindung in
    run_core() bestaetigt (echte Wanduhrzeit UND tatsaechliche
    Sitzungsdauer werden korrekt uebergeben). Visuelle Ueberpruefung
    des Erfolge-Bildschirms mit teils freigeschalteten, teils noch
    versteckten Eintraegen, kein Absturz. 36 Kombinationen kompletter
    Regressionstest bestanden.

Neu in v1.94 (BUGFIX: RA-Fortschritt fehlte weiterhin bei NES/SNES
und weiteren Systemen, trotz vorhandener Achievements):
  - Nutzer-Rueckmeldung: nach dem Fix in v1.92 (GAMEBOY/Saturn) fehlte
    RA-Fortschritt immer noch bei NES, SNES und weiteren Systemen,
    obwohl dort laengst Achievements gesammelt wurden.
  - Ursache per Recherche gegen echte RA-API-Beispiele bestaetigt: RA
    verwendet fuer manche Systeme LAENGERE, kombinierte Konsolennamen
    als in RA_CONSOLE_MAP eingetragen - z.B. "SNES/Super Famicom"
    statt nur "SNES", "Mega Drive" statt "Genesis Mega Drive". Der
    bisherige Abgleich verlangte eine EXAKTE Uebereinstimmung des
    kompletten Strings - das schlug fuer genau diese Systeme IMMER
    fehl, obwohl die Kernbezeichnung eigentlich passte.
  - Fix: build_ra_lookup()/lookup_ra_progress() grundlegend umgebaut.
    Statt eines exakten (Titel, System)-Schluessels wird jetzt pro
    Titel eine Liste aller RA-Eintraege gefuehrt (mehrere Konsolen fuer
    denselben Titel sind normal, z.B. Aladdin auf Genesis UND SNES).
    Neue _ra_console_matches(): prueft, ob unsere erwartete
    Systembezeichnung als ZUSAMMENHAENGENDE WORTFOLGE in RAs
    tatsaechlichem Namen vorkommt - wortgrenzen-bewusst, nicht per
    rohem Teilstring-Vergleich (sonst haette "nes" faelschlich JEDES
    SNES-Spiel getroffen, da "SNES" den Teilstring "nes" enthaelt).
  - Getestet: mit den ECHTEN, per Recherche bestaetigten RA-
    Konsolennamen nachgestellt ("SNES/Super Famicom", "NES/Famicom",
    "Mega Drive", "PlayStation") - alle vier Systeme liefern jetzt
    korrekte Treffer. KRITISCHER Test bestanden: NES-Systemschluessel
    trifft nachweislich NICHT faelschlich ein SNES-Spiel. Mehrfach-
    Konsolen-Fall (derselbe Titel auf zwei Systemen) korrekt getrennt
    zugeordnet, nicht vermischt. Kein falscher Treffer bei nicht
    passendem Titel oder System. 36 Kombinationen kompletter
    Regressionstest bestanden.

Neu in v1.93 (Optischer Feinschliff - hochwertiger wirkendes Design,
OHNE laufende Zusatzkosten):
  - Wunsch: "optisch hochwertiger" wirken, aber ausdruecklich ohne
    Performance-Verluste. Vier Richtungen umgesetzt, alle so gebaut,
    dass sie nur EINMALIG (nicht pro Frame) etwas kosten.
  - Neue Framebuffer.rect_rounded(): abgerundete Ecken, kostet nur ein
    paar zusaetzliche KUERZERE Randzeilen (die Rundung selbst), nicht
    die ganze Flaeche - der Mittelteil laeuft weiterhin ueber das
    normale, gecachte rect(). Angewendet auf die Auswahl-Markierung in
    der Liste (nur im tatsaechlich ausgewaehlten Zustand, nicht bei
    reinen Hintergrund-Fuellungen).
  - Boxart-Bereich als "Karte": dezenter, versetzter Schlagschatten
    (einfaches dunkles Rechteck dahinter, kein teures Alpha-Blending)
    + abgerundete Ecken statt einer flachen Flaeche.
    -
  - Vignette (Randabdunkelung) auf einfarbigen Hintergrundflaechen -
    EHRLICHER HINWEIS zur Performance: eine echte, pixelgenaue radiale
    Vignette wurde zuerst gemessen und wieder verworfen (ueber 1
    Sekunde fuer eine einzelne 1080p-Flaeche, selbst nur einmalig
    berechnet - bei bis zu zwei Systemwechseln zwischen Hintergrund-
    bildern haette das zu spuerbaren Haengern gefuehrt). Stattdessen:
    rein zeilenbasierte Variante (oben/unten dunkler, kein staerkerer
    Effekt in den Ecken) - vorberechnete, unterschiedlich dunkle
    Zeilen-Varianten, aufeinanderfolgende Zeilen mit gleicher Stufe zu
    Bloecken zusammengefasst, dazu die unnoetige finale bytes()-
    Umwandlung eingespart. Von ueber 1000ms auf ca. 3-20ms gedrueckt,
    und selbst das nur EINMALIG pro (Farbe, Aufloesung)-Kombination,
    dank Cache spaeter praktisch kostenlos. Wirkt bewusst NICHT auf
    echte Hintergrundbilder (BgCache) - dort waere derselbe Trick
    (ganze Zeile hat dieselbe Farbe) nicht anwendbar, eine sichere
    Grenze statt eines riskanten Kompromisses.
  - Feinere Abstaende: mehr Luft zwischen Kopfzeile und Liste (40->46px
    Basiswert) sowie zwischen Liste und Boxart-Karte (14->20px).
  - Getestet: rect_rounded() radius=0 byte-identisch zu rect()
    bestaetigt, Eckpixel bleiben ausgespart/Mitte gefuellt, kein
    Absturz bei Rand-/Ueberlauf-Faellen, nur 1.29x Kosten gegenueber
    normalem rect() (bei 1-3 Aufrufen pro Bild vernachlaessigbar).
    bg_fresh-Konsistenz (siehe v1.91) mit den neuen abgerundeten Ecken
    erneut bestaetigt - weiterhin byte-identisch zwischen beiden
    Zeichenpfaden. Karte mit Schatten visuell ueberprueft. Vignette:
    Geschwindigkeit bei mehreren Farben/Aufloesungen gemessen (CRT
    praktisch kostenlos, HDMI im einstelligen bis niedrigen zwei-
    stelligen ms-Bereich, nur beim ERSTEN Aufruf pro Farbe). Komplette
    Seite visuell mit allen vier Aenderungen zusammen ueberprueft.
    Laufende Zeichenkosten nach Cache-Aufwaermen bei 1080p gemessen:
    3.37ms pro vollem Neuzeichnen - weiterhin im etablierten schnellen
    Bereich, keine spuerbare Verlangsamung der eigentlichen Navigation.
    36 Kombinationen kompletter Regressionstest bestanden.

Neu in v1.92 (ZWEI BUGFIXES: Uhrzeit falsch nach NTP-Sync,
RetroAchievements fehlte bei manchen Systemen):
  - Nutzer-Rueckmeldung: Uhrzeit zeigte 15:09 statt der tatsaechlichen
    17:09 (2 Stunden Differenz, deutsche Sommerzeit).
  - Ursache: NTP liefert grundsaetzlich UTC. sync_system_clock_from_ntp()
    nutzte bisher time.localtime(), das sich auf die Systemzeitzone
    verlaesst - MiSTer hat aber vermutlich gar keine echte Zeitzone
    konfiguriert (Standard UTC), wodurch die gesetzte/angezeigte Uhrzeit
    der reinen UTC-Zeit entsprach statt der tatsaechlichen Ortszeit.
  - Fix: neue manuell einstellbare Zeitzonen-Verschiebung
    (load_timezone_offset()/save_timezone_offset(), Datei
    timezone_offset, Standard 0=UTC). sync_system_clock_from_ntp()
    wendet diesen Versatz selbst an und nutzt time.gmtime() statt
    time.localtime() - unabhaengig davon, was die Systemzeitzone zu
    sein glaubt. Neuer System-Menuepunkt "Zeitzone: UTC+X -> naechste"
    (0.5h-Schritte, -12 bis +14, Rundlauf) - loest nach dem Umschalten
    sofort eine Neusynchronisierung im Hintergrund aus.
  - Zweiter Fund (Nutzer-Rueckmeldung: RA-Fortschritt fehlte bei
    manchen Covern): RA_CONSOLE_MAP hatte "GB" als Schluessel
    eingetragen, unser tatsaechlicher Systemschluessel fuer Game Boy
    ist aber "GAMEBOY" (siehe GAME_SYSTEMS) - die Zuordnung schlug fuer
    Game Boy dadurch IMMER fehl. Saturn fehlte komplett in der Tabelle,
    obwohl unterstuetzt. Ausserdem mehrere tote Eintraege fuer Systeme,
    die es in unserem Code gar nicht gibt (Atari2600, AtariLynx, PCE
    als eigener Schluessel, S32X).
  - Fix: RA_CONSOLE_MAP direkt gegen die echte GAME_SYSTEMS-Tabelle
    abgeglichen und korrigiert - deckt jetzt GENAU unsere echten
    Systeme ab, nichts fehlt, nichts ist tot.
  - Getestet: Zeitzonen-Fix mit dem GENAU gemeldeten Szenario
    nachgestellt (UTC 15:09 + Versatz +2h -> gesetzte Zeit 17:09
    bestaetigt). Formatierung/Umschalten (0.5h-Schritte, Rundlauf bei
    +14/-12) einzeln getestet. RA-Fix: automatischer Abgleich zwischen
    RA_CONSOLE_MAP und GAME_SYSTEMS bestaetigt keine toten/fehlenden
    Eintraege mehr; Game Boy und Saturn liefern jetzt nachweislich
    einen Treffer, bestehendes System (SNES) weiterhin ohne Regression.
    36 Kombinationen kompletter Regressionstest bestanden.

Neu in v1.91 (Zweiter Patch von TheRealSutefan uebernommen -
Admin-Oberflaeche, Overlay-Cover, grosser Performance-Schub):
  - TheRealSutefan (nicht Dennsen selbst, der ist nur Tester/Streamer)
    hat einen zweiten, umfangreicheren Patch eingereicht. Wieder jede
    einzelne Aenderung verifiziert und auf unseren aktuellen Stand
    uebertragen, nichts blind uebernommen.
  - Admin-Schalter (stream_admin.html): waren <span>-Elemente um die
    Checkbox - nicht klickbar ausserhalb der winzigen echten Checkbox-
    Flaeche. Jetzt <label>, macht den ganzen sichtbaren Schalter
    klickbar (Browser-Standardverhalten). Dazu 16:9-Vorschau statt
    fester Pixelhoehe.
  - Overlay (stream_overlay.html): applyConfig() rendert jetzt den
    zuletzt bekannten Zustand sofort neu - Schalter wirken dadurch
    SOFORT statt erst beim naechsten Zustandswechsel am MiSTer. Ordner
    (Name endet auf "/") fragen kein Cover mehr an (vorher unnoetige
    404). object-fit von cover auf contain - Cover werden nicht mehr
    beschnitten.
  - Overlay-Server durchsucht jetzt ART_HD UND ART_BASE (vorher nur
    SD) - findet dieselben HD-Cover wie das Frontend selbst.
  - Alpha-Kanal-Fix im Overlay-Server: ECHTER, bisher unbemerkter
    Fehler bestaetigt - rgb_to_art() (mister_boxart.py) und
    art_convert.py setzen den Alpha-Kanal beim Erzeugen von .art-
    Dateien NIE explizit (bytearray startet bei 0), der MiSTer-
    Framebuffer ignoriert Alpha ohnehin - ein Browser aber nicht. Jedes
    Cover waere im Overlay komplett durchsichtig/schwarz erschienen.
    Fix direkt vor der PNG-Kodierung (Alpha auf 255 setzen), betrifft
    dadurch auch laengst vorhandene .art-Dateien, ohne sie neu
    erzeugen zu muessen.
  - Input-Rescan-Optimierung: guenstiger stat("/dev/input")-Check statt
    des teuren /proc/bus/input/devices-Parsens bei jedem Intervall,
    wenn sich nichts geaendert hat. Hotplug wird weiterhin zuverlaessig
    erkannt.
  - Text-Zeilen-Cache in Framebuffer.text() - GROESSTER Hebel bei den
    reinen Zeichenkosten: ganze Textstreifen (Schluessel: Text+Groesse+
    Farben) werden als fertiger Pixel-Streifen gecacht und nur noch
    geblittet, statt bei jedem Aufruf Buchstabe fuer Buchstabe neu
    zusammenzusetzen. Byte-identisch zur alten Ausgabe verifiziert.
  - Aufgeschobenes Cover-Laden beim Scrollen: waehrend aktiv navigiert
    wird (< COVER_SETTLE=150ms seit der letzten Eingabe), werden noch
    nicht dekodierte Cover uebersprungen statt den Scroll-Pfad zu
    ruckeln - ~150ms nach dem letzten Tastendruck laedt ein einmaliger
    Nachlade-Redraw sie nach.
  - bg_fresh-Optimierung in draw_list_row(): direkt nach einem vollen
    Redraw (Puffer wurde gerade komplett aus dem Hintergrundbild
    kopiert) entfaellt die redundante Zeile-fuer-Zeile-Wiederherstellung
    - der Puffer entspricht an der Stelle ja bereits dem Hintergrund.
    NUR am einen Aufruf innerhalb des vollen Redraws aktiviert, alle
    anderen Aufrufstellen (Puls-Takt, Laufschrift, Einzelschritt-
    Navigation) bleiben unveraendert beim sicheren Standardwert False.
  - PERF-Log-Zeilen (bg/rows/art/flip-Aufschluesselung, einzelne
    Cover-Ladezeiten, draw_page_items-Gesamtzeit) bewusst mit
    uebernommen, nur bei ueberschrittener Schwelle aktiv - zum
    Nachmessen auf echter Hardware, spaeter wieder entfernbar.
  - Getestet: Admin-Label-Fix mit jsdom (Klick auf den Schalter-Bereich
    schaltet jetzt um). Overlay: object-fit, applyConfig-Sofort-
    Rendering, Ordner-ohne-Coveranfrage (mit Gegentest fuer normale
    Spiele) einzeln bestaetigt. HD+SD-Suche im Overlay-Server mit
    Vorrang-Test. Alpha-Fix direkt am uebergebenen RGBA-Puffer
    verifiziert (durchgehend 255 trotz Quelle mit 0). Input-Rescan:
    kein erneuter teurer Scan bei unveraenderter mtime, force=True
    erzwingt trotzdem, echte Aenderung wird weiterhin erkannt. Text-
    Cache: 252 Faelle (3 Aufloesungen x 7 Texte x 3 Skalierungen x 4
    Positionen) byte-identisch zur alten Implementierung bestaetigt,
    dazu Cache-Wiederverwendung/Obergrenze/negative-x-Absicherung
    einzeln. Defer-Logik: uebersprungen wenn noch nicht dekodiert UND
    Defer aktiv, normal dekodiert sonst, bereits dekodierte Cover
    trotz aktivem Defer weiterhin angezeigt. bg_fresh: Bytevergleich
    zeigt IDENTISCHES Ergebnis zu False bei ausgewaehlter UND nicht
    ausgewaehlter Zeile (Voraussetzung: Puffer entspricht bereits dem
    Hintergrund), zusaetzlich 2.1x Geschwindigkeitsmessung bestaetigt.
    Settle-Nachladen: genau ein zusaetzlicher draw_page_items()-Aufruf
    nach Ablauf von COVER_SETTLE, Defer korrekt deaktiviert, KEIN
    wiederholtes Nachladen bei mehreren Leerlauf-Durchlaeufen
    hintereinander. 36 Kombinationen kompletter Regressionstest
    bestanden.

Neu in v1.90 (Sieben Verbesserungen aus Dennsens Test-Patch
uebernommen, geprueft und auf unseren Stand angepasst):
  - Ein Nutzer hat unabhaengig einen eigenen Patch gebaut (basierend
    auf einem aelteren Zwischenstand vor dem Durchgespielt-/
    Achievement-System aus v1.89) und als ZIP eingereicht. Jede
    einzelne Aenderung wurde erst verifiziert (Diff gegen unseren
    Stand, Ursache nachvollzogen), dann sauber auf den AKTUELLEN Stand
    uebertragen und neu getestet - nichts wurde blind uebernommen.
  - Admin-Oberflaeche des Stream-Overlays: Checkboxen und das Ecke-
    Auswahlfeld reagierten nicht (nur Text/Farbe/Regler funktionierten) -
    es wurde nur auf "input" gelauscht, Checkboxen/Auswahlfelder feuern
    aber "change". Jetzt beides.
  - frontend_boot.sh robuster: las /tmp/CORENAME bisher nur mit
    Nullbyte-Bereinigung, anders als current_core() im Python-Code
    (das zusaetzlich Leerzeichen/CR/LF/Tab entfernt) - bei Firmware,
    die dort etwas anhaengt, matchte "MENU" nie, das Skript wartete
    dadurch sinnlos bis zum 60s-Limit.
  - Tolerante Cover-Suche: Cover aus kuratierten Sets mit fuehrender
    Nummer ("007 Super Mario Kart (USA).art") wurden nicht gefunden,
    weil das Spiel intern ohne Nummer heisst. Erst exakter Name, dann
    Fallback ueber einen Index (fuehrende "NNN "-Nummer ignoriert) -
    wirkt jetzt in Frontend UND Overlay UND fuer HD-Cover (Erweiterung
    gegenueber der eingereichten Fassung, die nur SD-Cover im Frontend
    abdeckte - koennte auch das aeltere "Beyond the Beyond"-Problem
    mitloesen).
  - Overlay zeigt jetzt den laufenden Titel waehrend eines Spiels
    (vorher blieb es leer/veraltet, da die Hauptschleife waehrend des
    Spiels blockiert ist) - wird direkt vor dem Core-Start und nach
    der Rueckkehr zwangsweise aktualisiert.
  - Cover-Caches moderat vergroessert (roh 40->60, skaliert 10->20) -
    nimmt den Ruckler beim Hin-und-Herscrollen, den die jetzt
    gefundenen (vorher fehlenden) Cover verursachten. BEWUSST
    vorsichtiger als der eingereichte Wert (40->90/10->48) - bei
    grossen HD-Covern (~4MB/Bild unkomprimiert) waere das ein
    spuerbarer RAM-Batzen auf einem MiSTer mit typischerweise ~1GB RAM.
  - Sichtbare Konsolenausgabe bei jeder Startphase - vor allem der
    Fall "es laeuft schon eine Instanz" (z.B. durch Autostart) endete
    bisher KOMPLETT LAUTLOS per sys.exit(0), wirkte wie ein stiller
    Absturz. Zeigt jetzt direkt einen fertigen Kill-Befehl an.
  - install_offline.sh findet sein Paket jetzt zuverlaessig - aus dem
    Paketordner selbst, dessen Scripts/-Unterordner, oder als Kopie in
    /media/fat/Scripts/ (OSD-Aufruf) - und verwechselt das bereits
    installierte Frontend nicht mit der Quelle (Unterscheidung ueber
    das Vorhandensein von install_offline.sh selbst neben
    frontend/frontend.py).
  - Getestet: Admin-Fix mit jsdom (Checkbox/Auswahlfeld ueber "change"
    bestaetigt ausgeloest, Text-Eingabe ueber "input" weiterhin ohne
    Regression). Boot-Skript mit sieben verschiedenen problematischen
    Dateiinhalten (Nullbyte/Leerzeichen/CR/Tab/Kombination) UND einem
    Gegentest (anderer Core darf nicht als MENU durchgehen). Tolerante
    Cover-Suche: exakter Name hat Vorrang, Fallback ueber Index,
    Dubletten-Fall, Cache-Verhalten (kein wiederholtes listdir) - fuer
    Frontend UND Overlay-Server einzeln bestaetigt. Overlay-Update:
    genau 2x aufgerufen (vor Start, nach Rueckkehr) mit erzwungenem
    Signatur-Reset, UND korrekt gar nicht aufgerufen, wenn kein Overlay
    aktiv ist. Cache-Obergrenzen direkt verifiziert. Start-Diagnose:
    normaler Start, "laeuft schon"-Fall mit korrekter PID/Kill-Befehl,
    try/except-Absicherung um NTP/Sound-Erzeugung. Offline-Installer:
    drei realistische Aufruf-Orte (Paketordner, dessen Scripts/, OSD-
    Kopie) UND ein Negativtest (gar kein Paket vorhanden) bestaetigt,
    kompletter End-zu-Ende-Installationslauf gegen eine simulierte
    SD-Struktur erfolgreich. 36 Kombinationen kompletter Python-
    Regressionstest bestanden.

Neu in v1.89 (NEUE FEATURES: Durchgespielt-Status + eigenes,
lokales Achievement-System):
  - "Durchgespielt"-Status: F7 (Tastatur, auch im Belegungs-Assistenten
    umbelegbar) markiert das aktuelle Spiel als durchgespielt/wieder
    zurueck - eigene Speicherdatei (completed.json), Markierung in der
    Liste ("V ", kombinierbar mit dem Favoriten-Stern), Anzeige im
    Info-Bereich.
  - Spielzeit-Daten um das System erweitert (record_playtime() nimmt
    jetzt optional syskey entgegen, run_core() reicht es durch) -
    rueckwaertskompatibel zu beiden aelteren Datenformaten (v1.79
    reine Zahl, v1.80 ohne syskey-Feld).
  - Eigenes, komplett lokales Achievement-System (unabhaengig von
    RetroAchievements, nur auf unseren eigenen Daten basierend): 15
    Meilensteine ueber vier Kategorien (Spielzeit 1/10/50/100h, Starts
    10/50/100/500, Entdecker 3/5/10 verschiedene Systeme, Durchgespielt
    1/5/10/25 Spiele). Werte werden bei jedem Aufruf LIVE aus den
    vorhandenen Daten berechnet (kein separater Fortschritts-Zustand,
    der aus dem Ruder laufen koennte).
  - Neuer Anzeige-Bildschirm ("Meine Erfolge" im System-Menue) - zeigt
    alle Meilensteine, erreichte hervorgehoben, offene mit
    Fortschrittsangabe.
  - Getestet: Durchgespielt-Speicherlogik (mehrere Eintraege, Abwaehlen,
    leere/kaputte Datei, fehlender Name). Listen-Markierung fuer alle
    vier Kombinationen (Favorit/Durchgespielt/beides/keins), visuell
    ueberprueft. Spielzeit-Erweiterung mit allen drei Datenformaten
    (neu mit syskey, v1.80 ohne syskey-Feld, v1.79 reine Zahl)
    rueckwaertskompatibel bestaetigt - top_played_games() weiterhin
    ohne Regression. Meilenstein-Berechnung mit realistischen Daten
    fuer alle vier Kategorien einzeln bestaetigt. Anzeige-Bildschirm
    mit leerem und vollem Zustand, beiden Aufloesungen getestet, kein
    Absturz - visuell ueberprueft. 36 Kombinationen kompletter
    Regressionstest bestanden.

Neu in v1.88 (BUGFIX: RA-Core-Auswahl startete immer den normalen
Core statt des gewaehlten RA-Cores):
  - Nutzer-Rueckmeldung: Auswahl-Bildschirm erscheint und funktioniert,
    aber egal welche Option gewaehlt wird, startet immer der normale
    Core.
  - Ursache gefunden (per echter Datei vom Nutzer verifiziert): eine
    echte .mgl-Datei von sage2050s Werkzeug enthaelt neben <rbf> noch
    ein zweites, bisher fehlendes Element:
    <setname same_dir="1">RA_NES</setname> - ohne dieses Element
    behandelt MiSTer den RA-Core offenbar nicht korrekt als eigene,
    von der Standard-Konfiguration getrennte Variante.
  - Fix: find_ra_core() liefert jetzt (rbf_pfad, setname) statt nur
    des Pfads. write_mgl() hat einen neuen optionalen setname-
    Parameter, der bei Bedarf ein <setname same_dir="1">...</setname>-
    Element zwischen <rbf> und <file> einfuegt - exakt an der
    Position, im exakten Format, wie in der echten Datei bestaetigt.
  - Dabei auch eine falsche Annahme korrigiert: Saturn wurde bisher
    als "von odelots Fork nicht unterstuetzt" eingestuft - die reale
    Dateiliste des Nutzers zeigt aber eine vorhandene Saturn.rbf,
    Saturn ist deshalb jetzt in der Namensliste ergaenzt.
  - Getestet: write_mgl() erzeugt mit gesetztem setname exakt dieselbe
    Struktur wie die echte, vom Nutzer geschickte .mgl-Datei (Zeile
    fuer Zeile verglichen), ohne setname weiterhin unveraendertes
    Verhalten. find_ra_core() mit der kompletten, echten Dateiliste
    des Nutzers getestet (alle bestaetigten Systeme korrekt gefunden,
    inkl. Saturn). Kompletter Ablauf per echtem Durchlauf durch run()
    bestaetigt: Auswahl bei Kategorie-Eintritt erzeugt am Ende eine
    MGL-Datei, die pixelgenau der echten Referenzdatei entspricht.
    36 Kombinationen kompletter Regressionstest bestanden.

Neu in v1.87 (KRITISCHER BUGFIX: Spieleliste wurde bei JEDEM Start
komplett neu gescannt statt aus dem Cache geladen):
  - Nutzer-Rueckmeldung: nach der Installation auf einem weiteren
    MiSTer scannt das Frontend bei jedem einzelnen Start die komplette
    Spieleliste neu, statt den Cache zu nutzen.
  - Ursache: _wait_for_usb_stable() behandelte einen durchgehend
    LEEREN, aber VORHANDENEN USB-Ordner NIE als stabil - "stable_streak"
    wurde nur hochgezaehlt, wenn tatsaechlich Inhalt (total > 0) da war.
    MiSTer legt haeufig leere /media/usb0, /media/usb1 usw. als
    Platzhalter an, VOELLIG unabhaengig davon, ob dort ein echtes
    USB-Laufwerk angeschlossen ist. Bei so einem Setup blieb die
    Anzahl immer bei 0, das Zeitlimit (10s) wurde dadurch JEDES MAL
    erreicht, scan_games() cachte das Ergebnis deshalb NIE - die
    Spieleliste wurde bei jedem Start komplett neu gescannt.
  - Fix: eine durchgehend STABILE Null (leer, aber ueber mehrere
    Abfragen hinweg unveraendert) zaehlt jetzt AUCH als stabil - mit
    etwas mehr Vorsicht als bei echtem Inhalt (4 statt 2 aufeinander-
    folgende Abfragen), damit ein Laufwerk, das gerade erst zu
    befuellen beginnt, nicht zu frueh faelschlich als "leer und
    fertig" durchgeht.
  - Getestet: genau das gemeldete Szenario (leerer, aber vorhandener
    USB-Ordner, bleibt durchgehend leer) nachgestellt - wird jetzt
    nach kurzer Bestaetigungszeit korrekt als "sicher zu cachen"
    erkannt, statt das volle Zeitlimit auszureizen. Bestehende Faelle
    weiterhin korrekt: kein USB-Ordner vorhanden, echter von Anfang an
    stabiler Inhalt, Inhalt der erst waehrend der Wartezeit eintrifft.
    Randfall (Zeitlimit kuerzer als die fuer den leeren Fall noetigen
    Abfragen) faellt weiterhin sicher auf "nicht cachen" zurueck statt
    abzustuerzen oder haengen zu bleiben. 36 Kombinationen kompletter
    Regressionstest bestanden.

Neu in v1.86 (NEUES FEATURE: Wahl zwischen Standard- und
RetroAchievements-Core beim Betreten eines Systems):
  - Nutzerwunsch: beim Betreten eines Systems (z.B. SNES) waehlen
    koennen, ob der normale Core oder ein RA-faehiger Core (aus
    sage2050s "MiSTer_RetroAchievements"-Werkzeug, separater
    _RA_Cores-Ordner) geladen wird - fuer ALLE Systeme, fuer die eine
    RA-Core-Variante gefunden wird.
  - Neue Funktion find_ra_core(syskey) sucht die RA-Core-Datei ueber
    mehrere plausible Namensvarianten pro System (die exakte
    Dateibenennung dieses Drittanbieter-Werkzeugs konnte nicht gegen
    eine echte Installation verifiziert werden - EHRLICHER HINWEIS:
    findet sich keine passende Datei, wird fuer dieses System einfach
    KEINE Auswahl angezeigt, nie ein nicht-existierender Pfad
    referenziert). Systeme ohne RA-Unterstuetzung bei odelots Fork
    (Saturn, Arcade usw.) sind bewusst nicht in der Namensliste
    enthalten.
  - Neuer Auswahl-Bildschirm (draw_core_choice_screen()) beim Betreten
    einer Kategorie mit gefundenem RA-Core - Hoch/Runter waehlt,
    OK bestaetigt, ESC waehlt sicherheitshalber den normalen Core.
    Kategorien ohne gefundenen RA-Core zeigen die Abfrage gar nicht
    erst (unveraendertes Verhalten).
  - Die Wahl wird pro System fuer die Sitzung gemerkt
    (self._ra_core_choice) und beim tatsaechlichen Spielstart auf den
    Core-Pfad angewendet, der in die MGL-Startdatei geschrieben wird.
  - Getestet: RA-Core-Erkennung mit mehreren Namensvarianten, Systemen
    ohne Treffer und unbekannten Systemschluesseln. Auswahl-Bildschirm
    fuer alle drei Ausgaenge (Standard per OK, RA-Core nach Wechsel,
    ESC als sichere Vorgabe). Einbindung in _enter_category(): Abfrage
    wird nachweislich KOMPLETT uebersprungen, wenn kein RA-Core
    gefunden wird oder die Kategorie keinen Systemschluessel hat (kein
    einziger zusaetzlicher Eingabe-Aufruf). Komplette Kette per
    echtem Durchlauf durch run() bestaetigt: Auswahl bei Kategorie-
    Eintritt wird beim tatsaechlichen Spielstart korrekt in die MGL-
    Datei uebernommen. 36 Kombinationen kompletter Regressionstest
    bestanden.

Neu in v1.85 (KRITISCHER BUGFIX: Frontend blieb auf manchen Setups
dauerhaft im MiSTer-OSD haengen):
  - Nutzer-Rueckmeldung: nach Installation auf einem MiSTer mit einem
    Sony/PlayStation-artigen Controller startete das Frontend zwar
    (kein Absturz, Log sah normal aus, "Menue sichtbar" wurde
    protokolliert), der Bildschirm blieb aber dauerhaft im MiSTer-
    eigenen Menue haengen - auch bei manuellem Start per SSH, nicht
    nur beim Autostart.
  - Ursache: inject() (fuer den F9-Tastendruck, der MiSTer in den
    Konsolenmodus schaltet) waehlt bislang einfach das ERSTE Geraet
    mit is_kbd=True - und is_kbd basiert nur darauf, ob der Linux-
    Kernel IRGENDEINEN "kbd"-Handler an das Geraet gehaengt hat (siehe
    scan_devices(), "kbd" in b). Das trifft auch auf die "Consumer
    Control"- bzw. "System Control"-Nebenschnittstellen eines Sony-
    Controllers zu (Medien-/Systemtasten) - landen diese in der
    Geraete-Aufzaehlung VOR der echten Tastatur (wie beim meldenden
    Nutzer), ging das injizierte F9 dorthin und damit ins Leere.
  - Fix: inject() sucht jetzt ZUERST gezielt nach einem Geraet, das
    "keyboard" im NAMEN traegt (deutlich zuverlaessigeres Signal) -
    nur wenn keins gefunden wird, faellt es auf die bisherige
    is_kbd-Heuristik zurueck (Rueckwaertskompatibilitaet fuer Setups
    ohne eine im Namen erkennbare Tastatur). Genau dasselbe Muster
    wird bereits von _find_keyboard_hidraw() (Esc-Notausstieg, v1.75)
    genutzt - dort war es von Anfang an richtig geloest.
  - Getestet: mit der EXAKTEN vom Nutzer gemeldeten Geraete-
    Konstellation (Sony-Controller mit zwei Nebenschnittstellen VOR
    der echten Logitech-Tastatur) nachgestellt - injiziert jetzt
    nachweislich in die echte Tastatur statt die Nebenschnittstelle.
    Rueckfallebenen einzeln bestaetigt: kein Geraet mit "Keyboard" im
    Namen faellt korrekt auf die alte Heuristik zurueck; keine Geraete
    vorhanden stuerzt nicht ab; bestehende, bereits funktionierende
    Setups (Tastatur zuerst in der Liste) aendern ihr Verhalten NICHT;
    Gross-/Kleinschreibung im Geraetenamen spielt keine Rolle. Keine
    weitere Fundstelle desselben is_kbd-Musters im restlichen Code
    gefunden. 36 Kombinationen kompletter Regressionstest bestanden.

Neu in v1.84 (BUGFIX: Soundeffekte stoerten die Musik und stapelten
sich bei schneller Navigation):
  - Nutzer-Rueckmeldung: kurze Aussetzer in der Musik, sobald
    Soundeffekte spielen, und Toene, die verzoegert oder mehrfach
    nacheinander kommen, obwohl der Cursor schon wieder stillsteht.
  - Ursache: die reine Zeit-Drossel (SFX_MIN_GAP) hat nicht verhindert,
    dass sich mehrere aplay-Prozesse ueberlappen, wenn ein einzelner
    Aufruf laenger braucht als die Drosselzeit, bis er tatsaechlich
    fertig ist - vermutlich, weil aplay auf die Soundkarte warten
    musste, die gleichzeitig von mpg123 fuer die Hintergrundmusik
    belegt ist. Ergebnis: ein wachsender Rueckstau, der noch Toene
    abspielte, lange nachdem der Cursor schon stillstand, UND dabei
    offenbar kurze Aussetzer in der Musik verursachte.
  - Fix, zwei Absicherungen: (1) play_sfx() startet keinen neuen Ton
    mehr, solange der vorherige aplay-Prozess noch laeuft (per
    Popen.poll() geprueft) - hoechstens EIN Ton gleichzeitig
    unterwegs, kein Rueckstau moeglich. (2) Solange Musik TATSAECHLICH
    gerade spielt (self.music._proc_alive(), nicht nur "Musik ist
    eingeschaltet"), wird gar nicht erst versucht, einen Soundeffekt
    abzuspielen - vermeidet die Geraete-Ueberschneidung von vornherein.
  - Getestet: music_playing=True verhindert das Abspielen komplett;
    ohne laufende Musik spielt es normal weiter. Der genaue gemeldete
    Fall direkt nachgestellt - 10 schnelle Navigationsschritte, bei
    denen der vorherige Ton NIE fertig wird (Worst Case): nur noch 1
    tatsaechlicher aplay-Aufruf statt 10, kein Rueckstau mehr. Nach
    Fertigstellung des vorherigen Tons spielt der naechste wieder
    normal. Echter Durchlauf durch run() mit aktiv laufender Musik
    bestaetigt: music_playing wird korrekt aus self.music._proc_alive()
    ermittelt und bei jedem Aufruf durchgereicht. 36 Kombinationen
    kompletter Regressionstest bestanden.

Neu in v1.83 (OBS-Stream-Overlay verfeinert: Genre/Jahr, Spielzeit,
RetroAchievements-Fortschritt, Favoriten-Stern):
  - stream_state() liefert jetzt zusaetzlich genre/year (dieselbe
    Quelle wie der Info-Bereich im Frontend, inkl. Arcade-Sonderfall
    ueber mra_meta()), playtime (formatiert, aus self._playtime_cache),
    ra_progress (aus self._ra_lookup, nur bei Treffer) und favorite
    (aus self._favorites_set).
  - _publish_stream()s Aenderungserkennung um diese neuen Felder
    erweitert - sonst haette sich z.B. eine gerade aktualisierte
    Spielzeit nicht sofort im Overlay gezeigt, solange man auf
    demselben Spiel stehen bleibt.
  - stream_overlay.html: neue Fakten-Zeile (Genre, Jahr, Spielzeit,
    RA-Fortschritt), jede einzeln nur sichtbar bei vorhandener Angabe;
    Favoriten-Stern neben dem Titel. Vier neue Konfigurationsschalter
    (show_genre, show_playtime, show_ra, show_favorite) in
    stream_admin.html UND im Server (DEFAULT_CONFIG in
    stream_server.py, sonst haette der Server sie beim Speichern
    verworfen).
  - Getestet: Python-Seite (stream_state()) mit realistischen Daten
    inkl. Randfaellen (leere Liste, fehlende Cache-Attribute,
    Kategorien-Seite, Arcade-System, JSON-Serialisierbarkeit).
    HTML/JS-Seite mit jsdom (echte Browser-DOM-Engine, keine reine
    Simulation) - 20 Tests: alle vier neuen Anzeigen mit/ohne Daten,
    alle vier Konfigurationsschalter einzeln geprueft. Server-seitige
    Konfigurationsfilterung ebenfalls getestet. 36 Kombinationen
    kompletter Python-Regressionstest bestanden.
  - EHRLICHER HINWEIS: kein echter Browser zum visuellen Rendern in
    dieser Umgebung verfuegbar - die CSS-Gestaltung folgt eng den
    bestehenden Mustern der Datei, ein tatsaechlicher Blick im Browser/
    OBS bleibt sinnvoll.

Neu in v1.82 (NEUES FEATURE: RetroAchievements-Fortschritt anzeigen -
komplett unsichtbar/kostenlos, solange nicht eingerichtet):
  - Einrichtung per SSH/Texteditor (retroachievements.cfg, zwei Zeilen:
    Benutzername + RA-Web-API-Schluessel) - KEINE Bildschirmtastatur
    im Frontend noetig/vorhanden.
  - Abfrage ueber die OFFIZIELLE, oeffentliche RA-API
    (API_GetUserCompletionProgress, ein Aufruf fuer die komplette
    Fortschrittsliste) - komplett UNABHAENGIG von einer speziellen
    RA-faehigen MiSTer-Version (odelots Fork); zeigt entsprechend nur
    dann etwas, wenn tatsaechlich schon Achievements erreicht wurden
    (ueber odelots Fork ODER weil dasselbe Spiel schon anderswo
    RA-getrackt gespielt wurde).
  - Abruf zeitlich begrenzt (gleiches Prinzip wie die NTP-
    Zeitsynchronisierung, Hintergrund-Thread mit hartem Zeitlimit) -
    Nutzer OHNE Einrichtung bekommen NULL Verzoegerung beim Start.
  - Namensabgleich (RA liefert keine Dateipfade) ueber einen
    normalisierten Titel + System, bewusst KONSERVATIV: fehlt fuer
    unser System eine bekannte RA-Entsprechung oder passt der Name
    nicht exakt, wird NICHTS angezeigt statt eines potenziell falschen
    Treffers.
  - Anzeige im Info-Bereich ("RA: 20/50"), nur bei tatsaechlichem
    Treffer. Neuer Menuepunkt im System-Menue zeigt den Status
    ("nicht eingerichtet" mit Anleitung, oder "eingeloggt als NAME
    (neu laden)").
  - EHRLICHER HINWEIS: die genauen Feldnamen der RA-Antwort sowie die
    RA-Konsolennamen (RA_CONSOLE_MAP) wurden anhand der oeffentlichen
    Dokumentation nachgebaut, aber NICHT gegen den echten Server
    verifiziert - beides so gestaltet, dass eine Abweichung zu KEINER
    Anzeige fuehrt statt zu einer falschen oder einem Absturz.
  - Getestet, Schritt fuer Schritt, jeder Baustein einzeln BEVOR er
    mit dem naechsten verbunden wurde: Konfigurationsdatei-Erkennung
    (5 Randfaelle), API-Abfrage (3 Antwortformate + 5 Fehlerfaelle +
    URL-Konstruktion), zeitlich begrenzter Abruf (4 Faelle inkl.
    haengender Verbindung), Namensabgleich (7 Normalisierungs-Faelle +
    bewusst simulierter Fehltreffer zur Bestaetigung der sicheren
    Ausweichlogik), komplette Einbindung (Start ohne Verzoegerung fuer
    normale Nutzer, Anzeige mit/ohne Treffer, Anleitungs-Bildschirm in
    beiden Aufloesungen/Sprachen, Menue-Beschriftung in beiden
    Zustaenden/Sprachen, Refresh-Aktion erfolgreich/fehlgeschlagen).
    36 Kombinationen kompletter Regressionstest bestanden. Visuell
    ueberprueft (Info-Bereich mit RA-Zeile, Anleitungs-Bildschirm).

Neu in v1.81 (Ueberpruefung der letzten 5 Versionen v1.76-v1.80 auf
Bugs und Performance):
  - Systematisch alle Aufrufstellen der neuen Funktionen aus v1.76-
    v1.80 darauf geprueft, ob versehentlich etwas Teures (Datei-I/O,
    Cache-Invalidierung) in einem haeufig durchlaufenen Pfad
    (Navigation, Neuzeichnen) gelandet ist.
  - ECHTER FUND: play_sfx() (v1.78) pruefte die Ein/Aus-Markierungsdatei
    VOR der guenstigen, rein im Speicher liegenden Drossel-Pruefung -
    bei einem Turbo-Sprung (gehaltene Richtungstaste) waere dadurch bei
    JEDEM einzelnen Navigationsschritt eine Datei-Existenzpruefung
    noetig gewesen, obwohl die meisten dieser Aufrufe ohnehin gedrosselt
    (verworfen) werden. Fix: Drossel-Pruefung zuerst, zusaetzlich die
    Ein/Aus-Abfrage selbst per _sfx_enabled_cached() 5 Sekunden
    zwischengespeichert (gleiches Prinzip wie Netzwerkstatus/Attract-
    Modus).
  - VERDACHT GEPRUEFT UND ENTKRAEFTET: eine erste, grobe Messung liess
    vermuten, die neue Spielzeit-Anzeige im Info-Bereich (v1.79) koennte
    die Navigation um bis zu 65ms verlangsamen (durch eine minimal
    andere Cover-Zielgroesse wegen der zusaetzlichen Textzeile). Ein
    sauberer, kontrollierter Vergleich (jeweils 10 Wiederholungen mit
    komplett frischem Cover-Cache, abwechselnde Reihenfolge) zeigte
    dagegen KEINEN nennenswerten Unterschied (46,98ms vs. 50,50ms,
    innerhalb der normalen Messschwankung) - die urspruengliche grosse
    Differenz war ein Mess-Artefakt durch Datei-System-Caching-Effekte
    in der Sandbox-Umgebung (aehnliches Muster wie schon bei der
    clear()-Untersuchung in v1.67 gesehen), keine echte Verlangsamung
    im Code selbst.
  - Alle anderen Aufrufstellen (current_theme_name(),
    _find_keyboard_hidraw(), top_played_games()) liegen ausschliesslich
    in seltenen, nutzerausgeloesten Pfaden (Menue oeffnen, Spiel
    beenden), nicht in einer haeufig durchlaufenen Schleife - keine
    weiteren Performance-Funde.
  - Getestet: play_sfx()-Umstellung erneut end-to-end bestaetigt (20
    schnelle Aufrufe loesen nur 1x tatsaechlich aus UND nur 1x eine
    Datei-Existenzpruefung, statt 20x; Ein-/Ausschalten funktioniert
    weiterhin korrekt). 36 Kombinationen kompletter Regressionstest
    bestanden.

Neu in v1.80 (NEUES FEATURE: zwei Top-10-Listen im System-Menue):
  - "Top 10: meistgespielt" und "Top 10: meistgestartet" - zeigen die
    10 Spiele mit der laengsten Gesamtspielzeit bzw. den meisten
    Starts als Vollbild-Liste (rein informativ, keine beliebige Taste
    startet sie direkt - druecken einer Taste kehrt zurueck ins
    System-Menue).
  - Dafuer die Spielzeit-Datenstruktur erweitert: playtime.json
    speichert jetzt pro Spiel {"seconds": X, "launches": N} statt nur
    einer reinen Zahl - RUECKWAERTSKOMPATIBEL zum alten v1.79-Format
    (eine reine Zahl wird beim Laden transparent zu {"seconds": Zahl,
    "launches": 0} umgewandelt, bisherige Spielzeit geht dadurch NICHT
    verloren).
  - Neue Funktion top_played_games(by="seconds"|"launches", n=10) -
    liefert die n Spiele mit dem hoechsten Wert in der gewaehlten
    Kategorie, absteigend sortiert; Spiele mit 0 in dieser Kategorie
    werden ausgelassen.
  - Getestet: Sekunden UND Start-Zaehler werden korrekt gemeinsam
    aufaddiert. Altes v1.79-Format (reine Zahl) wird beim Laden korrekt
    migriert, bisherige Zeit bleibt erhalten, danach normal weiter
    nutzbar. Sortierung fuer beide Kategorien unabhaengig voneinander
    korrekt (unterschiedliche Rangfolgen je nach Kategorie bestaetigt).
    Leere Statistik liefert korrekt eine leere Liste. Anzeige-Bildschirm
    stuerzt in keinem Fall ab (mit Daten, ohne Daten, mit sehr langem
    Spieletitel als Kuerzungstest, beide Aufloesungen, beide
    Kategorien) - visuell ueberprueft. Menuepunkte in beiden Sprachen
    korrekt beschriftet. 36 Kombinationen kompletter Regressionstest
    bestanden.

Neu in v1.79 (NEUES FEATURE: automatischer Spielzeit-Tracker):
  - Neue Funktionen load_playtime()/record_playtime()/format_playtime()
    - Spielzeit wird pro Spiel (identifiziert ueber denselben Namen wie
    "Zuletzt gespielt"/Favoriten) in playtime.json aufaddiert.
  - run_core() nimmt jetzt einen optionalen label-Parameter entgegen
    und misst NUR die Zeit vom bestaetigten Core-Start bis zur
    Rueckkehr ins Menue - Ladezeiten und fehlgeschlagene Starts
    (Core kam nie hoch) zaehlen bewusst NICHT mit.
  - Anzeige im Info-Bereich (Boxart-Panel): "Gespielt: 2h 15min" o.ae.,
    direkt neben Spieleranzahl/Jahr/Genre - ueber einen Speicher-Cache
    (self._playtime_cache, gleiches Prinzip wie der Favoriten-Cache)
    ohne Datei-Lesevorgang bei jedem Neuzeichnen, wird nach jedem
    Spielaufruf aktualisiert.
  - Getestet: Spielzeiten werden korrekt pro Spiel aufaddiert (nicht
    ueberschrieben), andere Eintraege bleiben unberuehrt, ungueltige
    Eingaben (kein Name, 0/negative Sekunden) werden korrekt ignoriert.
    Formatierung fuer alle Faelle (< 1 Minute, Minuten, Stunden+Minuten,
    glatte Stunden) korrekt. End-to-End mit simuliertem Core-Start:
    erfolgreicher Spielverlauf zeichnet die Zeit korrekt auf, ein
    fehlgeschlagener Start (Core startet nie) zeichnet NICHTS auf.
    Anzeige im Info-Bereich stuerzt nicht ab (mit Eintrag, ohne
    Eintrag, sogar ganz ohne Cache-Attribut als Testfall) und setzt
    den Text nachweislich korrekt zusammen. 36 Kombinationen
    kompletter Regressionstest bestanden.

Neu in v1.78 (NEUES FEATURE: Navigations-Soundeffekte):
  - Kurze, selbst synthetisierte Sinuston-WAVs (kein Download noetig,
    passt zu unserem "keine Abhaengigkeiten"-Grundsatz) fuer Bewegen
    (move), Bestaetigen (confirm) und Zurueck (back) - werden beim
    ersten Start einmalig erzeugt (_ensure_sfx_files()) und unter
    SFX_DIR abgelegt.
  - Abspielen ueber `aplay` (Teil von alsa-utils, auf MiSTer bereits
    vorhanden), "fire and forget" per subprocess.Popen() - jeder
    Fehler (aplay fehlt, Soundkarte gerade durch die Hintergrundmusik
    belegt) wird still ignoriert, nie eine Ausnahme nach aussen.
  - Gedrosselt (SFX_MIN_GAP=0.07s) - sonst wuerden beim Halten einer
    Richtungstaste mit Turbo-Beschleunigung zu viele aplay-Prozesse
    pro Sekunde entstehen.
  - Zentral an EINER Stelle in der Aktionsverarbeitung ausgeloest
    (nicht in jedem der vielen Aktions-Zweige einzeln) - deckt dadurch
    automatisch jeden Kontext ab (Hauptliste, Beenden-Dialog,
    Buchstaben-Sprung usw.).
  - Neuer Menuepunkt "Navigations-Soundeffekte" im System-Menue zum
    Ein-/Ausschalten (Standard: AN).
  - Getestet: erzeugte WAV-Datei mit Pythons eigenem wave-Modul
    verifiziert (gueltiges Format, kein Knacksen durch das Ein-/Aus-
    blenden, keine Uebersteuerung). Dateien werden nur einmalig erzeugt
    (zweiter Aufruf ueberschreibt nicht unnoetig). Drossel verhindert
    nachweislich eine Ueberflutung bei schnell aufeinanderfolgenden
    Aufrufen, laesst aber nach Ablauf der Drosselzeit wieder korrekt
    durch. play_sfx() stuerzt nachweislich nicht ab, auch wenn aplay
    fehlt. Menue-Beschriftung aktualisiert sich korrekt nach dem
    Umschalten. Echter Durchlauf durch run() mit einer Folge
    tatsaechlicher Aktionen bestaetigt: Soundeffekte werden in der
    richtigen Reihenfolge (move/move/move/back) ausgeloest. 36
    Kombinationen kompletter Regressionstest bestanden.

Neu in v1.77 (NTP-Zeitsynchronisierung + Themes/Farbschemata):
  - NTP-ZEITSYNCHRONISIERUNG: MiSTer hat keine batteriegepufferte
    Echtzeituhr - die Systemuhr startet nahe Null (siehe v1.70: Log-
    Zeitstempel begannen bei "00:00:11") und wird sonst erst spaet
    (falls ueberhaupt) per Netzwerk korrigiert, oft als ploetzlicher
    Sprung mitten in der Sitzung. Neu: _ntp_time()/
    sync_system_clock_from_ntp() - reines SNTP ueber socket/struct
    (keine externe Bibliothek), laeuft ganz am Anfang, noch vor dem
    allerersten Log-Eintrag. Ueber einen Hintergrund-Thread mit hartem
    Zeitlimit abgesichert, damit eine haengende DNS-Aufloesung (die
    socket.settimeout() nicht zuverlaessig erfasst) den Start niemals
    unkontrolliert lange blockieren kann. Ohne lokales Netzwerk wird
    gar nicht erst versucht.
  - THEMES/FARBSCHEMATA: drei umschaltbare Farbschemata (Dunkel/
    Standard, Hell, Retro-Gruen) ueber einen neuen Menuepunkt im
    System-Menue. Technisch einfach gehalten: die "Chrome"-Farben
    (C_BG/C_TEXT/C_PANEL/C_TITLE/C_ACCENT) werden beim Wechseln direkt
    neu belegt - kein Umbau an den hunderten Stellen im Code noetig,
    die diese Namen bereits verwenden. SYSTEM_ACCENT (pro-System-
    Farben) bleibt bewusst themaunabhaengig (eigene visuelle Sprache).
  - Dabei einen echten Python-Fallstrick gefunden und behoben:
    text()s Parameter-Vorgabewert (fg=C_TEXT) haette sich bei einem
    spaeteren Themenwechsel NICHT aktualisiert, da Python Vorgabewerte
    nur EINMAL beim Definieren der Funktion auswertet, nicht bei jedem
    Aufruf - auf denselben Sentinel-Musterstil wie bg=None umgestellt.
  - Getestet: NTP - Zeitstempel-Dekodierung exakt (< 10ms Abweichung
    im Roundtrip-Test), kein Netzwerk fuehrt zu sofortigem Abbruch ohne
    Wartezeit, ein haengender Server blockiert den Start dennoch nicht
    laenger als das Zeitlimit, Plausibilitaetspruefung filtert
    unsinnige Zeitstempel, Systemuhr-Befehl wird korrekt aufgerufen.
    Themes - zyklisches Durchschalten, Speichern/Laden, Menue-
    Beschriftung in beiden Sprachen, der Parameter-Vorgabewert-Fix
    direkt verifiziert (Text nutzt nach einem Wechsel nachweislich die
    NEUE statt der eingefrorenen Farbe). Alle drei Themes visuell
    ueberprueft. 108 Kombinationen kompletter Regressionstest (alle
    drei Themes x beide Aufloesungen x mehrere Seiten/Kategorien)
    bestanden. Dabei einen eigenen Fehler beim Bearbeiten gefunden und
    behoben (eine Funktionsdefinition ging bei einer Einfuegung
    verloren) - durch den Regressionstest aufgefallen.

Neu in v1.76 (Notausstieg vereinfacht: reines Esc statt Strg+Alt+Esc):
  - Nutzerwunsch: nur die Esc-Taste statt der Dreifach-Kombination.
    _hid_report_has_esc() (vormals _hid_report_has_ctrl_alt_esc())
    prueft jetzt ausschliesslich auf den Escape-Keycode (0x29),
    unabhaengig von Modifikatortasten - und sucht ihn irgendwo im
    Report statt an einer festen Byte-Position (robuster gegenueber
    unterschiedlichen Report-Layouts).
  - Haltezeit (KBD_COMBO_HOLD) bewusst von 0.3s auf 0.6s erhoeht: ein
    einzelnes Esc wird leichter mal kurz in einem spiel-eigenen Pause-
    Menue gedrueckt als eine Dreifach-Kombination - die laengere
    Haltezeit verhindert, dass ein normaler, kurzer Esc-Druck im Spiel
    versehentlich den Ausstieg auslöst.
  - Pad-Anfrage (Start+Select am Joypad soll denselben Effekt haben):
    nach der eigenen Diagnose des Nutzers kam beim eingesetzten 8BitDo-
    Controller waehrend eines laufenden Spiels UEBER KEINEN der beiden
    gepruefen Kanaele (evdev gesperrt, hidraw liefert dort nichts)
    ueberhaupt etwas durch - dafuer gibt es aktuell keinen bestaetigten
    Lesepfad, daher (noch) nicht umgesetzt.
  - Getestet: reines Esc (mit und ohne gehaltene Modifikatoren) wird
    erkannt, andere Tasten loesen nicht aus. Ende-zu-Ende mit
    simulierter Tastatur: laenger gehaltenes Esc (>0.6s) loest
    zuverlaessig aus, ein kurzer Antipp (0.15s, wie im Spielmenue)
    loest NICHT aus. 36 Kombinationen kompletter Regressionstest
    weiterhin bestanden.

Neu in v1.75 (NEUES FEATURE: Notausstieg per Strg+Alt+Esc waehrend
eines laufenden Spiels, ueber die rohe HID-Ebene):
  - Hintergrund: der bestehende F10-/Start+Select-Ausstieg in
    wait_game_exit() liest ueber die normale evdev-Ebene
    (/dev/input/eventX) - die wird von MiSTer waehrend eines laufenden
    Cores exklusiv gesperrt. Per gezielter Nutzer-Diagnose bestaetigt
    (eigens dafuer geschriebenes Testwerkzeug, parallel zu einem
    laufenden Spiel mitgelesen): `cat /dev/input/eventX` liefert dabei
    0 Bytes - der bestehende Ausstieg konnte dadurch in der Praxis
    vermutlich nie tatsaechlich ausgeloest werden. Die ROHE HID-Ebene
    (/dev/hidrawX) liegt darunter und blieb bei einer angeschlossenen
    TASTATUR nachweislich lesbar (beim getesteten 8BitDo-Controller-
    Empfaenger dagegen nicht - dessen Tasten laufen offenbar ueber
    einen anderen, ebenfalls gesperrten Kanal).
  - Neu: _find_keyboard_hidraw() findet die Tastatur dynamisch unter
    /dev/hidraw* (ueber den HID-Namen, nicht fest verdrahtet - die
    hidraw-Nummerierung haengt von der Anschlussreihenfolge ab und kann
    sich zwischen Boots verschieben). _hid_report_has_ctrl_alt_esc()
    erkennt Strg+Alt+Esc im rohen HID-Report (Modifikator 0x05 +
    Escape-Keycode 0x29, geprueft in zwei moeglichen Report-Layouts -
    mit und ohne vorangestelltes Report-ID-Byte, je nach Tastatur).
  - wait_game_exit() ueberwacht jetzt zusaetzlich diese hidraw-Ebene
    (KBD_COMBO_HOLD=0.3s Haltezeit, analog zum bestehenden
    COMBO_HOLD=0.8s fuer Start+Select) und liefert bei Erkennung
    "hid_combo" - run_core() behandelt das identisch zu "combo"/"f10"
    (zurueck ins Menue). Der bestehende evdev-basierte Pfad bleibt
    unveraendert als Absicherung bestehen (falls er auf anderen MiSTer-
    Konfigurationen doch funktioniert).
  - Getestet: _hid_report_has_ctrl_alt_esc() erkennt die Kombination
    exakt bei den echten, vom Nutzer per Diagnose ermittelten Bytes
    (sowohl mit als auch ohne Report-ID-Praefix), loest NICHT bei
    normalen Tastendruecken faelschlich aus. _find_keyboard_hidraw()
    findet unter mehreren Geraeten (Maus, Empfaenger, Controller)
    korrekt nur die Tastatur. wait_game_exit() end-to-end mit einer
    simulierten Tastatur (named pipe) getestet: zu kurzes Halten (0.1s)
    loest NICHT aus, ausreichend langes Halten (>0.3s) loest zuverlaessig
    "hid_combo" aus, bestehende Menue-Erkennung und der Fall "keine
    Tastatur gefunden" funktionieren unveraendert korrekt. 36
    Kombinationen kompletter Regressionstest weiterhin bestanden.
  - EHRLICHER HINWEIS: das HID-Report-Format ist geraeteabhaengig - bei
    Tastaturen mit einem anderen Format als den beiden hier
    beruecksichtigten Varianten muesste _hid_report_has_ctrl_alt_esc()
    ggf. angepasst werden (z.B. mit hid_probe.py das tatsaechliche
    Format ermitteln).

Neu in v1.74 (BUGFIX: v1.73-Fix fuer den Attract-Modus-Schalter war
selbst noch fehlerhaft):
  - Nutzer-Rueckmeldung: Attract-Modus zeigt trotz v1.73 immer noch
    "AUS -> einschalten", egal wie oft man draufklickt.
  - Ursache gefunden: der v1.73-Fix suchte die "System"-Kategorie ueber
    "syskey ist None" - aber das ist NICHT eindeutig! "Zuletzt
    gespielt", "Favoriten" UND "Scripts" nutzen ALLE ebenfalls
    syskey=None und stehen in self.cats VOR "System" (werden per
    insert(0, ...) einsortiert bzw. vor dem abschliessenden System-
    Eintrag angehaengt). Dadurch wurde bisher die FALSCHE Kategorie
    ueberschrieben (meist "Zuletzt gespielt"), waehrend "System" selbst
    NIE aktualisiert wurde - die Beschriftung blieb dadurch dauerhaft
    eingefroren, unabhaengig davon, wie oft man umschaltet.
  - Fix: "System" wird jetzt eindeutig ueber den (nicht uebersetzten,
    immer gleichen) Kategorienamen gefunden, nicht nur ueber
    syskey=None.
  - Ausserdem: Protokollierung fuer toggle_attract_mode() ergaenzt
    (zeigt Vorher-/Nachher-Zustand und etwaige Fehler beim Anlegen/
    Loeschen der Markierungsdatei) sowie fuer _refresh_system_category()
    (bestaetigt, ob und wo die System-Kategorie gefunden wurde) - fuer
    den Fall, dass es doch noch an einer tieferliegenden Ursache liegt.
  - Getestet: mit einer realistischen Kategorienliste, die "Zuletzt
    gespielt", "Favoriten" UND "Scripts" (alle mit syskey=None) VOR
    "System" enthaelt - bestaetigt, dass jetzt ausschliesslich "System"
    aktualisiert wird und alle anderen unberuehrt bleiben. 36
    Kombinationen kompletter Regressionstest bestanden.

Neu in v1.73 (zwei weitere BUGFIXES: Attract-Modus-Umschalter,
"Zurueck" springt an den Listenanfang):
  - BUGFIX 1: Attract-Modus liess sich im System-Menue scheinbar nicht
    ein-/ausschalten. Ursache: toggle_attract_mode() aenderte nur die
    zugrundeliegende Markierungsdatei - die im Menue ANGEZEIGTE
    Beschriftung ("Attract-Modus: AN/AUS") blieb eingefroren auf dem
    Stand vom letzten build_categories()-Aufruf, da system_items() nur
    EINMAL beim Kategorien-Aufbau berechnet wird. Der Vergleichsfall
    "kuratiert" macht es richtig (ruft danach build_categories() auf),
    "attract" tat das nicht. Fix: neue schlanke
    _refresh_system_category() (nach demselben Prinzip wie
    _sync_favorites_category() - aktualisiert NUR die System-Kategorie,
    ohne die teure komplette Neuerstellung/den Spiele-Scan anzustossen).
  - BUGFIX 2: "Zurueck" aus einem Unterordner sprang immer auf Position
    0 der uebergeordneten Ebene, z.B. bei einer alphabetisch sortierten
    PSX-Sammlung immer zurueck zu "A", statt zu der Stelle, wo man vor
    dem Betreten des Unterordners stand (z.B. bei "Q"). Fix: Position
    (Auswahl + Scroll-Stand) wird beim Betreten eines Unterordners auf
    einem Stapel gemerkt (self._nav_position_stack) und beim
    Zurueckgehen wiederhergestellt - funktioniert auch ueber mehrere
    verschachtelte Ebenen hinweg.
  - Boxart-Problem (verpixeltes Cover beim Scrollen, HD-Cover danach)
    weiterhin in Untersuchung - der Fallback-Mechanismus (HD nicht
    gefunden -> CRT-Cover als Ersatz statt gar nichts) funktioniert wie
    vorgesehen; die eigentliche Frage ist, WARUM die HD-Suche bei
    bestimmten Titeln zunaechst fehlschlaegt. Bei Mehrfach-CD-Spielen
    (haeufig als Ordner organisiert) nutzt die Cover-Suche den
    Ordnernamen statt des Anzeigenamens - ein moeglicher Ansatzpunkt,
    aber ohne Zugriff auf die tatsaechlichen Dateien nicht abschliessend
    zu verifizieren.
  - Getestet: Attract-Beschriftung aktualisiert sich nachweislich nach
    dem Umschalten, andere Kategorien bleiben unberuehrt. Positions-
    Wiederherstellung fuer einzelne UND mehrfach verschachtelte
    Ordnerebenen bestaetigt. 24 Kombinationen kompletter
    Regressionstest weiterhin bestanden.

Neu in v1.72 (BUGFIX: fehlendes Boxart bei manchen Titeln bis zum
naechsten Blick):
  - Nutzer-Rueckmeldung: beim Durchscrollen der PS1-Spiele fehlt bei
    manchen Titeln (z.B. Battle Arena Toshinden) die Boxart, wird aber
    sichtbar, sobald man spaeter erneut darauf schaut - bei mehreren
    Titeln so.
  - Ursache gefunden: ArtCache.get() cachte JEDEN fehlgeschlagenen
    Ladeversuch dauerhaft (auch bei einer beschaedigten oder noch
    UNVOLLSTAENDIGEN Cover-Datei, z.B. waehrend eines noch laufenden
    Kopier-/Downloadvorgangs) - kein erneuter Versuch, ausser der
    Eintrag wird durch den 40-Bilder-Cache-Grenzwert irgendwann wieder
    verdraengt (was das beobachtete "geht spaeter doch" erklaert).
    Ausserdem faengt "except OSError" allein weder struct.error (bei
    abgeschnittenem Header) noch zlib.error (bei unvollstaendigen
    komprimierten Daten) ab - waere bei einer wirklich mitten im
    Schreiben erwischten Datei ein Absturz gewesen.
  - Fix: "Datei existiert nicht" (stabiler Fall) bleibt weiterhin
    dauerhaft gecacht. Ein Format-/Dekomprimierungsfehler (moeglicher-
    weise voruebergehend) wird jetzt NICHT gecacht - der naechste
    Zugriff versucht es einfach erneut, ohne auf eine Cache-Verdraengung
    warten zu muessen.
  - EHRLICHER HINWEIS: dies ist die wahrscheinlichste Erklaerung basierend
    auf dem beschriebenen Verhalten (fehlt zunaechst, erscheint spaeter),
    liess sich aber ohne Zugriff auf die tatsaechlichen Cover-Dateien
    nicht 1:1 nachstellen. Sollte es weiterhin auftreten, waere der
    genaue Dateiname/Pfad der betroffenen Cover hilfreich, um eine
    moegliche Namensabweichung separat zu pruefen.
  - Getestet: Datei-nicht-vorhanden bleibt korrekt dauerhaft gecacht,
    gueltige Datei wird korrekt geladen und gecacht, eine beschaedigte/
    unvollstaendige Datei wird NICHT gecacht und ein spaeterer Versuch
    nach "Reparatur" laedt sie korrekt (der eigentliche Bugfix-Fall),
    ein abgeschnittener Header fuehrt zu keinem Absturz mehr. 24
    Kombinationen kompletter Regressionstest weiterhin bestanden.

Neu in v1.71 (Leichter Zeichenpfad jetzt auch fuer echte Navigation,
nicht nur Hintergrund-Ticks):
  - Nutzer-Rueckmeldung: HDMI fuehlt sich weiterhin stockend an. Frisch
    profiliert: clear() (kompletter Bildschirm-Hintergrund) kostete in
    der echten Navigations-Pipeline weiterhin 23-64ms pro Aufruf, trotz
    nachweislich nur EINEM Cache-Eintrag - auch mit deaktivierter
    Garbage Collection blieb das Muster bestehen (schliesst GC als
    Ursache aus). Die genaue Ursache (vermutlich ein Speicher-/Seiten-
    zuweisungs-Effekt auf Betriebssystem-Ebene) liess sich nicht
    abschliessend klaeren - stattdessen ein groesserer Hebel: bei einem
    EINZELNEN hoch/runter-Schritt OHNE Scrollen (der weitaus haeufigste
    Fall beim normalen Durchbrowsen) muss die komplette Seite gar nicht
    neu aufgebaut werden.
  - Neuer leichter Pfad _draw_navigate_items(): aktualisiert nur die
    alte und neue markierte Zeile (inkl. noetiger Nachbarn wegen Glow-
    Ueberlappung - diesmal auch fuer die ALTE Position, die durch einen
    eigenen Fund noetig wurde: ihr Glow-Rand reichte beim Wegschalten
    ebenfalls in Nachbarzeilen hinein) sowie das Boxart-Panel. Faellt
    bei Scrollen, Ordnerwechsel, Kategorie-Seite usw. automatisch auf
    den vollen, bewaehrten draw()-Pfad zurueck. Da clear() dabei gar
    nicht mehr aufgerufen wird, ist dessen ungeklaerte Verlangsamung
    fuer den haeufigsten Fall jetzt hinfaellig.
  - Gemessene Einsparung: 73.22ms -> 35.54ms pro Navigationsschritt
    (51%% weniger) bei einem realistischen, nicht exakt passenden
    HD-Cover.
  - Getestet: pixelgenauer Differenzvergleich gegen volle draw()-
    Aufrufe fuer 18 verschiedene Sprungkombinationen (einzelne Schritte
    vorwaerts/rueckwaerts, groessere Spruenge, erste/letzte sichtbare
    Zeile, mit Favoriten-Markierung, mit Hintergrundbild) - null
    Abweichungen. Korrekter Ruecksprung auf den vollen Pfad bei
    Scrollen-noetig und bei der Kategorienseite bestaetigt. Echter
    Durchlauf durch run() mit einer Folge tatsaechlicher Navigations-
    schritte bestaetigt: Position wird korrekt nachgehalten, leichter
    Pfad wird bei jedem Schritt angewendet, kein Absturz. 24
    Kombinationen kompletter Regressionstest weiterhin bestanden.

Neu in v1.70 (WICHTIGER FUND: Attract-Modus-Ursache wahrscheinlich
gefunden - Systemuhr-Spruenge):
  - Nutzer schickte einen Log-Ausschnitt und fragte sich, warum die
    Zeitstempel bei "00:00:11" begannen. Aufgeklaert: LOG() nutzt
    time.strftime() - das ist die ECHTE Systemuhr, nicht "Sekunden seit
    Boot". MiSTer hat offenbar keine batteriegepufferte Echtzeituhr,
    die Uhr startet nahe Null und wird erst per Netzwerk (NTP)
    nachtraeglich korrigiert - das kann mitten in einer Sitzung
    passieren, oft als PLOETZLICHER SPRUNG um Stunden.
  - Das ist hoechstwahrscheinlich die eigentliche Ursache fuer den
    Attract-Modus, der "kurz nach dem Intro" oder "obwohl gerade
    navigiert wurde" einsetzte: der Leerlauf-Zaehler nutzte time.time()
    (die Systemuhr) - ein Sprung um mehrere Stunden waere SOFORT wie
    "90 Sekunden Leerlauf" ausgesehen, obwohl real nur Sekunden
    vergangen waren.
  - Fix: alle 42 Stellen im Code, die time.time() fuer ZEITDAUER-
    Messungen nutzen (Leerlauf-Zaehler, Equalizer-/Pulsier-/Laufschrift-
    Takte, Tasten-Wiederholung, USB-Wartelogik, Boot-Animation-Timing,
    Attract-Wechsel-Timer usw.), auf time.monotonic() umgestellt - eine
    Uhr, die garantiert NIE springt oder rueckwaerts laeuft, unabhaengig
    von Systemzeit-Korrekturen. Die ECHTE Uhrzeit-Anzeige (Uhrzeit im
    Hauptmenue, Log-Zeitstempel) nutzt bewusst weiterhin time.strftime()
    - die SOLL ja die echte, ggf. gerade korrigierte Uhrzeit zeigen.
  - Getestet: direkter Vergleichstest - bei einem simulierten Uhrsprung
    von 5 Echtzeit-Sekunden auf "5 Stunden Sprung in der Wanduhr" bleibt
    die monotone Messung korrekt bei 5 Sekunden (vorher: faelschlich
    17010 Sekunden). Laufschrift-Zeitbremse (v1.68) und alle Tick-
    Mechanismen erneut mit monotonic() bestaetigt korrekt, kompletter
    next_action()-Durchlauf ohne Absturz auf beiden Aufloesungen. 24
    Kombinationen kompletter Regressionstest weiterhin bestanden.
  - EHRLICHER HINWEIS: dies ist die wahrscheinlichste, aber nicht 100%%
    verifizierte Ursache (die genaue NTP-Konfiguration von MiSTer laesst
    sich in der Sandbox nicht nachstellen). Sollte der Attract-Modus
    trotzdem noch zu frueh einsetzen, waere das ein Hinweis auf eine
    GANZ ANDERE Ursache - bitte weiterhin per Log-Ausschnitt (diesmal
    nach einem tatsaechlichen Vorfall) melden.

Neu in v1.69 (GROSSER Fund: Cover-Verkleinerung war extrem langsam -
betrifft jede echte Navigation, nicht nur Hintergrund-Ticks):
  - Nutzer-Rueckmeldung: HDMI fuehlt sich trotz v1.62/v1.63/v1.67
    weiterhin laghaft an. Gezielt die bisher NICHT untersuchte
    Cover-Skalierung profiliert (ART.get_scaled(), lief bei jeder
    echten Navigation zu einem neuen Spiel): die VERKLEINERUNG (fuer
    HD-Cover, die groesser als der verfuegbare Platz sind - der
    Normalfall bei den meisten HD-Thumbnail-Quellen) machte pro
    Ziel-PIXEL eine einzelne 4-Byte bytearray-Slice-Zuweisung in einer
    doppelt verschachtelten Schleife. Bei einer realistischen
    Verkleinerung auf 480x600 sind das 288.000 einzelne Python-
    Anweisungen - gemessen: ~90ms fuer EIN einzelnes Cover!
  - Die VERGROESSERUNG (fuer kleine Cover) nutzte bereits die richtige
    Technik (b"".join() pro Zeile, in C implementiert) - die
    Verkleinerung wurde bislang uebersehen.
  - Fix: dieselbe Zeilen-weise b"".join()-Technik jetzt auch fuer die
    Verkleinerung. Ein Zeilen-Cache (dieselbe Quellzeile fuer mehrere
    Zielzeilen wiederverwenden) wurde erwogen, aber verworfen - beim
    hier verwendeten Naechster-Nachbar-Verfahren wird so gut wie nie
    dieselbe Quellzeile zweimal gebraucht, ein Cache haette nur
    zusaetzlichen Aufwand ohne Nutzen bedeutet (per Messung bestaetigt).
  - Gemessene Einsparung: 89.65ms -> 27.81ms fuer eine 800x1000 ->
    480x600-Verkleinerung (69%% weniger). Betrifft JEDE echte
    Navigation mit einem zu grossen HD-Cover, nicht nur die bisher
    optimierten Hintergrund-Ticks (Equalizer/Puls/Laufschrift) - eine
    andere Kategorie von Verzoegerung als die bisherigen Funde.
  - Getestet: Ergebnis pixelgenau identisch zur alten (langsamen)
    Implementierung bei 5 verschiedenen Zielgroessen (mit zufaelligem,
    nicht-uniformem Testbild, damit Positionsfehler auffallen wuerden).
    24 Kombinationen kompletter Regressionstest weiterhin bestanden.
  - Ausserdem: Logging fuer den Attract-Modus-Start ergaenzt (zeigt
    beim naechsten Vorfall die tatsaechliche Leerlaufzeit in Sekunden,
    fuer den Fall, dass "startet zu frueh" weiterhin auftritt).

Neu in v1.68 (BUGFIX: Namens-Laufschrift auf CRT viel zu schnell):
  - Nutzer-Rueckmeldung: Laufschrift bei langen Spieletiteln jetzt sehr
    schnell auf CRT, auf HDMI kaum ein Unterschied spuerbar. Ursache
    gefunden: marquee_tick() (Namens-Laufschrift fuer zu lange Titel in
    der Spieleliste) hatte KEINE eigene Zeitbremse - rueckte bei JEDEM
    Aufruf der aeusseren Schleife um ein Zeichen vor, nicht nach
    tatsaechlich verstrichener Zeit (im Gegensatz zu _eq_tick()/
    _pulse_tick(), die schon immer eine eigene Zeitbremse hatten).
  - Solange das Zeichnen selbst teuer war (vor v1.62/v1.63), bremste
    das die effektive Geschwindigkeit automatisch aus - die aeussere
    Schleife konnte gar nicht so oft aufrufen. Seit die Ticks viel
    billiger sind, laeuft die Schleife auf CRT nahe ihrem theoretischen
    Maximum (bis 100x/Sekunde ueber pulse_interval=0.01) - die
    Laufschrift wurde dadurch ungewollt bis zu 100 Zeichen/Sekunde
    schnell statt der beabsichtigten ~5.5 Zeichen/Sekunde (passend zum
    0.18s-Kandidaten, der in next_action() fuer die Laufschrift genutzt
    wird). Auf HDMI (von Haus aus langsamerer Grundtakt, 0.08s) fiel
    das kaum auf - passt exakt zur Nutzer-Rueckmeldung.
  - Fix: marquee_tick() bekommt dieselbe Art Zeitbremse wie
    _eq_tick()/_pulse_tick() (0.18s pro Zeichen, unabhaengig davon wie
    oft die aeussere Schleife tatsaechlich aufruft).
  - Getestet: 20 Aufrufe OHNE Zeitfortschritt bewegen die Laufschrift
    nicht mehr (vorher: 20 Zeichen), 10 Aufrufe MIT 0.18s Zeitabstand
    bewegen sie korrekt weiter, kompletter next_action()-Durchlauf mit
    langem Spieletitel auf beiden Aufloesungen ohne Absturz. 24
    Kombinationen kompletter Regressionstest weiterhin bestanden.

Neu in v1.67 (Absicherung gegen unbegrenzt wachsenden Zeichen-Cache):
  - Bei der weiteren Suche nach HDMI-Performance-Potenzial (Fortsetzung
    von v1.62/v1.63) gefunden: die generische rect()-Funktion (die
    meistgenutzte Zeichenfunktion ueberhaupt - Markierungen, Glow-
    Raender, Equalizer-Balken) cachte nach (Farbe, EXAKTER Breite) OHNE
    jede Obergrenze. Bei leicht wechselnden Breiten (Cover-
    Seitenverhaeltnis, Glow-Ring-Position, Info-Textlaenge) sammelt sich
    ueber viele Navigationen eine wachsende Zahl nie wieder verwendeter
    Eintraege an - dasselbe Grundmuster wie der in v1.32 behobene
    Pulsier-Cache-Bug, nur an anderer Stelle.
  - Fix: eigener Cache fuer rect() (_rectcache, getrennt von clear()s
    Hintergrund-Cache) mit Obergrenze (ROWCACHE_MAX_ENTRIES=150) - bei
    Ueberschreiten wird komplett geleert statt einzelne Eintraege
    aufwendig zu verwalten. clear()s selten wechselnde, aber teure
    Hintergrundmuster bleiben davon unberuehrt (eigener Cache).
  - EHRLICHER HINWEIS: die urspruengliche Beobachtung ("clear() wird
    ueber viele Navigationen hinweg spuerbar langsamer") liess sich in
    der Sandbox nicht eindeutig auf die Cache-Groesse zurueckfuehren -
    Messungen blieben nach dem Fix uneinheitlich (vermutlich Rauschen
    aus der x86-Sandbox-Umgebung, nicht zwingend repraesentativ fuer
    echte ARM-Hardware). Die Absicherung selbst ist trotzdem wertvoll
    (verhindert unbegrenztes Speicherwachstum ueber lange Sitzungen)
    und wird deshalb ausgeliefert - ob sie das gemeldete Lag-Gefuehl
    zusaetzlich verbessert, muss sich auf echter Hardware zeigen.
  - Getestet: rect() liefert identisches Ergebnis unabhaengig vom
    Cache-Zustand, Cache waechst nachweislich nicht ueber die
    Obergrenze hinaus, clear()s Hintergrund-Cache bleibt von rect()-
    Cache-Leerungen unberuehrt. 24 Kombinationen kompletter
    Regressionstest.

Neu in v1.66 (Attract-Modus: grosszuegigere Schwelle + gecachte
Abfrage):
  - Nutzer-Rueckmeldung: Attract-Modus startete manchmal kurz, obwohl
    gerade noch navigiert wurde. Bei nochmaliger, gruendlicher
    Durchsicht der kompletten Update-Kette fuer den Leerlauf-Zaehler
    (self._last_input_time) keinen weiteren Fehler ueber den v1.65-Fix
    hinaus gefunden - alle Aktualisierungsstellen sehen korrekt aus.
  - Trotzdem zwei sinnvolle Verbesserungen: ATTRACT_IDLE_SECONDS von
    45 auf 90 Sekunden erhoeht (grosszuegigerer Puffer), UND
    attract_enabled() (bisher bei JEDEM Leerlauf-Durchlauf per Datei-
    Existenzpruefung abgefragt, bis zu 12x/Sekunde) jetzt 5 Sekunden
    zwischengespeichert (_attract_enabled_cached()) - selbe Idee wie
    beim Netzwerkstatus (v1.55), passt auch zum Performance-Thema.
  - Falls das Problem weiterhin auftritt: bitte moeglichst genau
    schildern, wie lange die Pause vor dem ungewollten Einsetzen
    tatsaechlich war - hilft bei der weiteren Eingrenzung.
  - Getestet: Cache verhindert wiederholte Dateipruefungen (isoliert
    bestaetigt), 24 Kombinationen kompletter Regressionstest.

Neu in v1.65 (zwei kleinere, aber echte Bugfixes: Attract-Modus-
Timing, Turbo-Sprung bei schnellen Einzelklicks):
  - BUGFIX 1: Attract-Modus startete manchmal sehr schnell nach dem
    Neustart. Ursache: der Leerlauf-Zaehler (self._last_input_time)
    wurde schon in __init__() gesetzt - also VOR dem (potenziell
    langsamen) Scan und der Boot-Animation. Dauerten beide zusammen
    laenger, war ein Grossteil der 45 Sekunden Leerlaufzeit schon
    verstrichen, BEVOR der Nutzer das Menue ueberhaupt zu sehen bekam.
    Jetzt wird der Zaehler in run() erst NACH Boot-Animation und
    erstem Zeichnen zurueckgesetzt - genau dann, wenn das Menue
    tatsaechlich sichtbar und bedienbar ist.
  - BUGFIX 2: Cursor sprang gelegentlich zwei Zeilen statt einer beim
    Klicken durch das Menue. Ursache: der Turbo-Sprung-Zaehler
    (fuer schnelleres Springen beim HALTEN einer Richtungstaste)
    unterschied nicht zwischen einem echten Tastendruck-Halten und
    mehreren schnellen, aber EINZELNEN Klicks in dieselbe Richtung -
    beides sah fuer den Zaehler gleich aus ("dieselbe Richtung wie
    beim letzten Mal"), unabhaengig davon, wie viel Zeit dazwischen
    verging. Nach genug schnellen Einzelklicks schaltete der Zaehler
    faelschlich auf Turbo (2 statt 1 Schritt).
  - Fix: der Zaehler baut sich nur noch auf, wenn der Abstand zum
    letzten Tastendruck unter 0.5s liegt (knapp ueber REPEAT_DELAY=
    0.4s, der groessten natuerlichen Pause innerhalb eines echten
    Haltevorgangs) - bei einer spuerbaren Pause (z.B. 0.6s+) faengt
    er wieder bei 1 an, unabhaengig von der Richtung. Betrifft sowohl
    hoch/runter als auch links/rechts (Seitensprung).
  - Getestet: echtes Halten (schnelle Wiederholungen im 0.1s-Abstand)
    schaltet weiterhin korrekt auf Turbo, bewusste Einzelklicks mit
    spuerbarer Pause (0.6s) loesen NIEMALS mehr faelschlich Turbo aus,
    Richtungswechsel setzt den Zaehler korrekt zurueck. 48
    Kombinationen kompletter Regressionstest weiterhin bestanden.

Neu in v1.64 (KRITISCHER BUGFIX: Absturz kurz nach dem Boot bei
aktivierter Musik):
  - Nutzer-Rueckmeldung: Frontend spielt die Boot-Animation ab und
    wechselt danach zurueck ins MiSTer-OSD. Direkt nachgestellt (echtes
    next_action() ueber mehrere Durchlaeufe mit simulierter "keine
    Eingabe"-Situation, genau wie kurz nach dem Boot) - reproduzierte
    den Absturz sofort: NameError in _draw_dynamic_track_marquee()
    (aus v1.63), sobald der erste Equalizer-/Laufschrift-Tick faellig
    wurde. Ursache: beim Einfuegen dieser Funktion ist versehentlich
    ein Codeblock aus _draw_dynamic_items() (der dortige flip_rows()-
    Aufruf samt Bereichsberechnung) an ihr Ende hineingerutscht -
    referenzierte dort nicht existierende Variablen.
  - Zweiter, stiller Fehler dabei gefunden: durch dieses Verrutschen
    hatte _draw_dynamic_items() selbst KEINEN flip_rows()-Aufruf mehr -
    die markierte Zeile waere zwar korrekt neu gezeichnet, aber nie
    auf den echten Bildschirm uebertragen worden (kein Absturz, aber
    ein eingefrorenes Bild).
  - Beide Codebloecke an die richtige Stelle zurueckgesetzt.
  - LEHRE FUER KUENFTIGE AENDERUNGEN: der pixelgenaue Differenzvergleich
    (der beim Bauen dieser Funktionen verwendet wurde) prueft nur die
    KORREKTHEIT der Ausgabe, wenn die Funktion durchlaeuft - er haette
    diesen Fehler nicht gefangen, wenn der fehlerhafte Code zufaellig
    VOR dem eigentlichen Rueckgabepunkt gelandet waere. Ab jetzt
    zusaetzlich: ein direkter Testlauf durch next_action() selbst
    (mit simulierter Zeit, wie hier geschehen), um sicherzustellen,
    dass der komplette Ablauf durch den echten Code tatsaechlich
    fehlerfrei durchlaeuft, nicht nur die Bildausgabe stimmt.
  - Getestet: next_action() laeuft jetzt ueber mehrere Sekunden
    simulierter Zeit (mit echtem Sleep, wie eine reale Wartesituation)
    ohne Absturz auf beiden Seiten und beiden Aufloesungen. Beide
    betroffenen Funktionen erneut per pixelgenauem Vergleich bestaetigt
    (16 bzw. 6 Kombinationen). 48 Kombinationen kompletter
    Regressionstest weiterhin bestanden.

Neu in v1.63 (Performance-Verbesserung fortgesetzt: Songtitel-
Laufschrift jetzt ebenfalls ueber den leichten Pfad):
  - Fortsetzung von v1.62: die Songtitel-Laufschrift (Header auf Seite
    0, Fusszeile auf Seite 1) loeste noch immer einen vollen Aufbau
    aus, da dafuer explizit KEIN leichter Pfad vorgesehen war. Jetzt
    nachgeholt: _draw_dynamic_track_marquee() erneuert nur die eine
    Textzeile, kombinierbar mit dem Equalizer-/Pulsier-Pfad, falls
    beides im selben Tick faellig ist (unterschiedliche Bildbereiche,
    keine Ueberschneidung).
  - Gemessene Einsparung: von 3.88ms (voller Aufbau) auf praktisch
    nicht mehr messbar (<0.01ms) - reiner Text auf einfarbigem oder
    Bild-Hintergrund, kein Glow-Rand, keine Nachbar-Ueberlappung wie
    bei der Zeilen-Markierung, daher deutlich einfacher umzusetzen.
  - Beenden-Dialog weiterhin ausgenommen (voller, sicherer Aufbau).
  - Getestet: pixelgenauer Differenzvergleich gegen volle draw()-
    Aufrufe (beide Seiten, verschiedene Laufschrift-Positionen, mit/
    ohne Hintergrundbild, UND der kombinierte Fall - Equalizer/Puls
    UND Laufschrift im selben Tick) - null Abweichungen. 48
    Kombinationen kompletter Regressionstest weiterhin bestanden.

Neu in v1.62 (GROSSE Performance-Verbesserung - Ursache fuer das
gefuehlte HDMI-Lag gefunden):
  - Nutzer-Rueckmeldung: HDMI fuehlt sich weiterhin traege an, trotz
    aller bisherigen Tuning-Runden. Neu profiliert (cProfile mit
    realistischen HD-Covern): jeder Equalizer-/Pulsier-Tick (bis zu
    12.5x/Sekunde seit v1.55) loeste einen KOMPLETTEN Bildschirmaufbau
    aus - alle sichtbaren Zeilen-Texte, Boxart-Panel, Header - obwohl
    sich tatsaechlich nur die Glow-Farbe der markierten Zeile und ein
    paar Equalizer-Balken aendern. text() allein machte 46%% der
    gesamten Zeichenzeit aus.
  - Neue leichte Zeichenpfade: _draw_dynamic_cats() (Seite 0: nur
    Equalizer-Bereich + markierte Zeile) und _draw_dynamic_items()
    (Seite 1: nur markierte Zeile + noetige Nachbarn), nutzen
    flip_rows() statt der kompletten flip(). Werden anstelle des
    vollen draw() aufgerufen, wenn NUR Equalizer/Pulsieren ausgeloest
    haben (nicht bei Laufschrift-Aenderung oder aktivem Beenden-
    Dialog - dafuer bleibt der volle, sichere Pfad bestehen).
  - Gemessene Einsparung: Spieleliste 5.15ms -> 0.42ms (92%%),
    Kategorienseite 2.80ms -> 0.29ms (90%%) auf HDMI: CRT profitiert
    ebenfalls (0.37ms -> 0.08ms), auch wenn dort ohnehin kaum Kosten
    anfielen.
  - ZWEI ECHTE BUGS BEIM BAUEN GEFUNDEN (nicht ausgeliefert): (1) der
    halbtransparente Glow-Rand blendet auf den bestehenden Bildinhalt,
    ohne den erweiterten Randbereich vorher zurueckzusetzen, haette
    sich sonst bei jedem Tick weiter aufaddiert. (2) Bei der engen
    Zeilenhoehe der Spieleliste reicht der Glow-Rand in die
    Nachbarzeile hinein - deren Neuzeichnen muss in EXAKT derselben
    Reihenfolge wie beim vollen Aufbau passieren (aufsteigender Index),
    sonst uebermalt die falsche Zeichnung den Glow wieder. Beide per
    Differenzvergleich (pixelgenau) gegen den vollen Aufbau gefunden,
    bevor sie ausgeliefert wurden.
  - Getestet: pixelgenauer Differenzvergleich gegen volle draw()-Aufrufe
    fuer beide Seiten (CRT+HDMI, mehrere ausgewaehlte Zeilen, mit/ohne
    Favoriten-Markierung, mit/ohne Hintergrundbild) - null Abweichungen.
    48 Kombinationen kompletter Regressionstest weiterhin bestanden.

Neu in v1.61 (BUGFIX: v1.60-Theorie war falsch - echte Ursache
gefunden und mit zwei Absicherungen versehen):
  - Nutzer-Rueckmeldung: der v1.60-Fix (Grab durchgehend halten) hat
    das Einfrieren beim Konfigurieren von "OSD oeffnen" NICHT behoben -
    weiterhin kein Log-Eintrag danach, weiterhin schwarzer Bildschirm
    mit MiSTers Login-Prompt.
  - Neue, tiefere Theorie: F9 ist bei MiSTer fuer den Wechsel zwischen
    Konsole und Grafikmodus reserviert (siehe enter_console_mode()) -
    vermutlich ueber die Kernel-eigene VT-Umschaltung, nicht ueber
    einen gewoehnlichen evdev-Listener, den ein Grab ueberhaupt
    beeinflussen koennte. Sendet das Pad (z.B. ueber eine Home-/Guide-
    Taste, die bei manchen Empfaengern als eigene Tastatur-Taste
    ankommt) ein echtes F9, faengt der Kernel das vermutlich ab, BEVOR
    unser Prozess es je zu sehen bekommt - erklaert sowohl "nichts
    weiter im Log" (Ereignis kommt nie an) als auch den schwarzen
    Bildschirm (MiSTer wechselt weg von unserem Framebuffer).
  - Zwei Absicherungen: (1) read_raw_key() bekommt in configure_buttons()
    ein Zeitlimit (20s) statt endlos zu warten - bleibt eine
    Rueckmeldung zu lange aus, wird NUR diese eine Abfrage uebersprungen
    (bisherige Belegung bleibt bestehen), der Assistent haengt dadurch
    nie mehr unbegrenzt fest. (2) Ein tatsaechlich erfasstes F9 wird NIE
    als Belegung akzeptiert (klare Meldung, erneute Abfrage fuer
    dieselbe Aktion) - sonst wuerde eine Zuweisung auf F9 das exakt
    gleiche Einfrieren spaeter bei JEDEM Druck dieser Taste erneut
    ausloesen, nicht nur waehrend der Konfiguration selbst.
  - Getestet: Zeitlimit greift zuverlaessig (liefert None, keine
    Ausnahme), F9 wird als Rohcode weiterhin korrekt gelesen (Ablehnung
    passiert eine Ebene hoeher), kompletter Assistenten-Ablauf mit
    simulierter Eingabefolge (Achsen-Ueberspringen, normale Tasten,
    F9-Ablehnung mit erneuter Abfrage, Zeitlimit-Ueberspringen) fuehrt
    korrekt bis zum Ende durch, 12 Kombinationen Regressionstest.
  - EHRLICHER HINWEIS: auch diese Theorie ist mangels echter Hardware
    nicht abschliessend verifizierbar - falls es weiterhin auftritt,
    bitte den Log-Ausschnitt direkt nach dem naechsten Versuch schicken
    (zeigt jetzt zusaetzlich, OB und WANN das Zeitlimit greift).

Neu in v1.60 (BUGFIX: Tastenbelegungs-Assistent - Absturz/eingefrorener
Bildschirm speziell beim Konfigurieren von "OSD oeffnen"):
  - Nutzer-Rueckmeldung + Log-Analyse (kein "CRASH:"-Eintrag, der
    Prozess brach kommentarlos ab - kein Python-Fehler, sondern ein
    externer Eingriff): configure_buttons() loeste den Eingabe-Grab
    fuer die GESAMTE Dauer des Assistenten (alle 9 Abfragen). Beim
    Konfigurieren von "OSD oeffnen" testet man zwangslaeufig genau die
    Taste, die MiSTer selbst schon als eigene Menue-Taste kennt - war
    der Grab geloest, reagierte MiSTer PARALLEL zu unserem Prozess
    darauf und wechselte eigenstaendig in seinen Video-/Menuemodus,
    waehrend unser Prozess noch mitten im Assistenten haengen blieb.
  - EVIOCGRAB betrifft nur, ob ANDERE Leser desselben Geraets (wie
    MiSTers eigene Hotkey-Erkennung) die Tastendruecke ebenfalls sehen -
    unser EIGENES Lesen ueber os.read() auf dem selbst geoeffneten
    Datei-Deskriptor funktioniert unabhaengig vom Grab-Status. Das
    Loesen war hier also gar nicht noetig (vermutlich unreflektiert
    aus run_core()/run_script()/open_osd() uebernommen, wo es fuer eine
    ECHTE Kontrolluebergabe tatsaechlich noetig ist).
  - Fix: Grab bleibt waehrend der gesamten Tastenbelegung gehalten,
    grab(True) am Ende bleibt als Absicherung bestehen.
  - Getestet: configure_buttons() ruft grab(False) nicht mehr auf,
    grab(True) am Ende weiterhin vorhanden, 12 Kombinationen
    Regressionstest fuer den Rest der Anwendung. Kann mangels echter
    Hardware nicht 1:1 nachstellen (der eigentliche Konflikt entsteht
    erst durch MiSTers eigene, externe Hotkey-Erkennung) - Rueckmeldung
    nach echtem Test auf betroffener Hardware willkommen.

Neu in v1.59 (L1/L2/R1/R2 vollstaendig belegbar, insbesondere fuer
Favoriten):
  - Ursache gefunden: viele Xbox-artige Controller senden L2/R2 nicht
    als eigene Taste (BTN_TL2/BTN_TR2), sondern als ANALOGEN Trigger
    (ABS_Z/ABS_RZ) - dafuer gab es bisher ueberhaupt keine Erkennung,
    diese beiden Achsen wurden beim Oeffnen des Geraets nicht mal
    registriert. Auf solchen Pads passierte bei L2/R2 schlicht gar
    nichts, auch nicht ueber den Tastenbelegungs-Assistenten.
  - ABS_Z/ABS_RZ werden jetzt mit erfasst, per Schwellwert (>50%
    durchgezogen = "gedrueckt") in ganz normale, ueber KEYMAP frei
    belegbare Pseudo-Tastencodes (AXIS_L2/AXIS_R2, negative Zahlen -
    kollidieren garantiert nicht mit echten evdev-Codes) uebersetzt.
    Dieselbe Wiederholungslogik wie bei echten Tasten greift, falls
    eine wiederholbare Aktion (Navigation) darauf gelegt wird.
  - read_raw_key() (Tastenbelegungs-Assistent) erkennt den analogen
    Trigger jetzt ebenfalls, UNABHAENGIG von allow_axis_skip (das war
    bisher nur fuer die vier Richtungsaktionen aktiv) - dadurch laesst
    sich JEDE Aktion (nicht nur Navigation) auf einen analogen L2/R2
    legen.
  - Standardbelegung: L2 UND R2 (jeweils digital UND analog) zeigen
    jetzt beide von Haus aus auf "favorite" - unabhaengig davon, wie
    das eigene Pad sie sendet, funktioniert sofort eine davon. L1/R1
    bleiben unveraendert beim Blaettern, lassen sich aber wie jede
    andere Taste ueber den Assistenten umbelegen.
  - Getestet: Schwellwert-Erkennung (feuert genau einmal beim
    Ueberschreiten, nicht bei jedem Zwischenwert), Loslassen setzt
    korrekt zurueck, L2/R2 funktionieren unabhaengig voneinander,
    unbelegter Pseudo-Code stuerzt nicht ab, read_raw_key() erfasst
    den analogen Trigger korrekt (echte Pipe + simulierte evdev-
    Ereignisse, kein Mocking auf Quellcode-Ebene), normale Tasten
    funktionieren regressionsfrei weiter, Wiederholungslogik bei auf
    Navigation umgelegtem L2 funktioniert korrekt. 48 Kombinationen
    kompletter Regressionstest.

Neu in v1.58 (Favoriten-Liste):
  - Eigene, bewusst kuratierte Auswahl - unabhaengig von "Zuletzt
    gespielt" (automatische Verlaufsliste). F8 (Tastatur) bzw. L2
    (Gamepad, neue Konstanten BTN_TL2/BTN_TR2) schaltet den
    Favoritenstatus des markierten Spiels um, nur bei echten Spiele-
    Eintraegen. Kleines "*" vor dem Namen in der Liste zeigt bereits
    favorisierte Spiele.
  - Neue Kategorie "Favoriten" (direkt nach "Zuletzt gespielt"),
    erscheint/verschwindet automatisch je nachdem ob Favoriten
    vorhanden sind - OHNE build_categories() aufzurufen (das wuerde
    unnoetig einen Scan/Cache-Check aller Spiele-Systeme anstossen,
    nur um ein einzelnes Flag zu aktualisieren). Neue schlanke
    _sync_favorites_category(): haelt die aktuell betrachtete
    Kategorie ueber Name+Systemkey identifiziert, damit sich die
    Auswahl nicht verschiebt, wenn Favoriten weiter oben eingefuegt
    wird oder verschwindet.
  - WICHTIG (Performance-Vorsicht): is_favorite() liest bei jedem
    Aufruf die Datei - das waere im Zeichenpfad (draw_list_row(),
    bis zu 100x/Sekunde auf CRT) ein echtes Performance-Problem
    gewesen. Stattdessen self._favorites_set (Set im Speicher, O(1)-
    Abfrage), nur bei tatsaechlichen Aenderungen aktualisiert, nie
    erneut aus der Datei gelesen.
  - Getestet: Speicherfunktionen isoliert (Hinzufuegen/Entfernen,
    mehrere Favoriten parallel), _sync_favorites_category() mit allen
    kritischen Grenzfaellen (Favorit hinzufuegen waehrend man eine
    ANDERE Kategorie betrachtet - Position bleibt korrekt; einen von
    mehreren Favoriten entfernen waehrend man Favoriten betrachtet -
    bleibt dort; LETZTEN Favoriten entfernen waehrend man Favoriten
    betrachtet - wechselt korrekt zurueck zu Seite 0), visuelle
    Markierung per Differenzvergleich bestaetigt, 48 Kombinationen
    kompletter Regressionstest.

Neu in v1.57 (Attract-Modus/Bildschirmschoner - Code bereits
vorhanden, jetzt gruendlich geprueft und dokumentiert):
  - Der komplette Attract-Modus (_attract_games_pool(), draw_attract(),
    _enter_attract_mode(), _advance_attract(), next_action()-
    Integration, System-Menue-Eintrag zum An/Aus-Schalten) war im Code
    bereits vollstaendig und sauber umgesetzt, aber nirgends
    dokumentiert und ohne erkennbaren eigenen Test-Nachweis. Da ich
    keine eigene Erinnerung an diese Arbeit hatte, wurde der gesamte
    Mechanismus wie neuer Fremdcode gruendlich nachgeprueft, statt ihm
    blind zu vertrauen.
  - Getestet: attract_enabled()/toggle_attract_mode() (Standard: AN),
    _attract_games_pool() sammelt rekursiv ueber Ordnerstrukturen,
    schliesst syskey=None-Kategorien (Zuletzt gespielt/Scripts/System)
    korrekt aus, draw_attract() mit und ohne ausgewaehltes Spiel auf
    CRT und HDMI ohne Absturz, Start bei Leerlauf, Wechsel zwischen
    mehreren Spielen (vermeidet Wiederholung), UND der wichtige
    Grenzfall: startet korrekt NICHT bei komplett leerer Sammlung
    (kein Absturz, Leerlauf-Uhr wird stattdessen zurueckgesetzt).
    48 Kombinationen kompletter Regressionstest weiterhin bestanden.
  - Verhalten: nach 45 Sekunden ohne Eingabe erscheint automatisch ein
    zufaelliges Spiel grossflaechig mit Cover, wechselt alle 6 Sekunden
    weiter - jede Taste beendet es sofort wieder (wird NICHT zusaetzlich
    als normale Navigation verarbeitet). Ueber System-Menue an/aus
    schaltbar, Standard ist AN.

Neu in v1.56 (Arcade-Boxart - NEU, kein Code in frontend.py selbst
geaendert):
  - Bisher: Arcade zeigte Infos aus den MRA-Dateien (mra_meta() liest
    Jahr/Hersteller/Genre/Spieler direkt aus der MRA, kein Download
    noetig), aber NIE ein Cover - der Boxart-Downloader (mister_boxart.py)
    kannte Arcade schlicht nicht.
  - mister_boxart.py um vollstaendige Arcade-Unterstuetzung erweitert:
    findet alle _Arcade-Ordner (gleiche Erkennung wie scan_cores() im
    Frontend), sammelt MRA-Dateinamen (Datum-Suffix entfernt, identisch
    zum Anzeigenamen im Frontend), lädt passende Cover von
    libretro-thumbnails/MAME (Named_Boxarts-Konvention, wie alle
    anderen Systeme - list_covers()/download_cover()/match_rom() dafuer
    UNVERAENDERT wiederverwendet, keine neue Download-Logik noetig).
  - Kein einziger Code in frontend.py selbst musste sich aendern - die
    Anzeige-Logik (draw_art_panel(), art_path()) war schon immer bereit,
    es fehlten nur die Dateien auf der Platte.
  - Aufruf identisch zu vorher: python3 mister_boxart.py (bzw. hd),
    Arcade laeuft automatisch mit, keine Extra-Option noetig.
  - Getestet: MRA-Sammlung inkl. Datum-Suffix-Entfernung, kompletter
    Downloadlauf mit gefaelschtem Netzwerk (Treffer + echter Fehl-
    treffer), End-to-End-Anzeige im Frontend mit dem exakt vom
    Downloader erzeugten Dateinamen (Pixel-Analyse bestaetigt),
    bestehende Konsolen-Sammellogik per Gegenprobe unveraendert korrekt.

Neu in v1.55 (HDMI nochmal aufgedreht, Uhrzeit+Netzwerksymbol im
Hauptmenue):
  - HDMI auf ausdruecklichen Wunsch nochmal naeher an das CRT-Erlebnis
    herangeholt: Equalizer-Takt 0.15s -> 0.08s (Schwingung 5.0 -> 7.0),
    Pulsier-Takt 0.15s -> 0.08s (Zyklus 1.6s -> 1.0s), Laufschrift-Takt
    0.2s -> 0.1s. Die 0.08s-Untergrenze ist bewusst an REPEAT_INTERVAL
    (v1.39) angelehnt - dort schon als sicher fuer HDMI erprobt (12.5
    Tastenwiederholungen/Sekunde), also ein vertretbares Ziel auch fuer
    die Hintergrund-Ticks. Getestet: ~10.6 Zeichenvorgaenge/Sekunde
    auf HDMI bei aktiver Laufschrift (v1.54: ~5.9/s). CRT unveraendert.
  - NEU: Uhrzeit + Netzwerksymbol unten rechts im Hauptmenue. Uhrzeit
    (HH:MM) immer sichtbar, das kleine Balkensymbol nur bei
    bestehender Netzwerkverbindung (WLAN/LAN) - Erkennung ueber den
    klassischen "UDP-connect"-Trick (verschickt kein einziges Paket,
    rein lokales Routing, <2ms), Ergebnis 5 Sekunden zwischen-
    gespeichert. Getestet: Cache verhindert wiederholte Pruefungen,
    Anzeige per Pixel-Analyse bestaetigt, Grenzfall bei sehr kleiner
    Aufloesung und gleichzeitige Statusmeldung ohne Kollision geprueft.
  - 36+ Kombinationen kompletter Regressionstest.

Neu in v1.54 (HDMI-Profil: Laufschrift, Equalizer und Pulsieren
ebenfalls beschleunigt):
  - Auf ausdruecklichen Wunsch, nachdem sich die HDMI-Performance seit
    dem Boxart-Schatten-Fix (v1.34) als stabil erwiesen hat: alle drei
    Effekte auch auf HDMI moderat schneller (nicht so extrem wie auf
    CRT, wo draw() praktisch nichts kostet - auf HDMI bewusst
    zurueckhaltender).
  - Equalizer-Takt: 0.35s -> 0.15s, Schwingungsfrequenz 2.2 -> 5.0.
  - Pulsier-Takt: 0.9s -> 0.15s, Zykluslaenge 3.2s -> 1.6s.
  - Laufschrift-Takt: 0.35s -> 0.2s (Schrittweite von 2 Zeichen/Tick
    bleibt - kombiniert ergibt das eine deutlich hoehere gefuehlte
    Geschwindigkeit).
  - Aeusserer Aufwach-Takt in next_action() entsprechend angepasst
    (min()-Kandidaten pulse_interval/eq_interval jetzt auch 0.15s auf
    HDMI), damit die schnelleren internen Takte tatsaechlich bedient
    werden.
  - Getestet: alle Werte einzeln direkt gemessen, effektive Bildrate
    mit realistischer Zeitsimulation bestaetigt (~5.9 Zeichenvorgaenge/
    Sekunde auf HDMI bei aktiver Laufschrift, vorher ~2.9/Sekunde -
    rund 2x schneller). CRT-Werte per Gegenprobe unveraendert
    bestaetigt (weiterhin 0.01s). 48 Kombinationen kompletter
    Regressionstest.

Neu in v1.53 (BUGFIX: USB-Kaltstart - unnoetiger Vollscan + unsichere
Cache-Eintraege; SIGHUP-Absicherung):
  - Ein externer Vergleichslauf (vom Nutzer hochgeladen, unabhaengig
    selbst verifiziert und NEU implementiert, nicht blind uebernommen)
    deckte zwei tiefere USB-Probleme auf, die trotz v1.49-v1.52
    bestehen blieben:
  - (a) SIGNATUR-INSTABILITAET: _games_signature() nutzte bisher den
    ABSOLUTEN Pfad jedes Systemordners. Mountet eine USB-Platte nach
    einem Kaltstart nicht immer unter derselben Nummer (mal
    /media/usb0, mal /media/usb1), aendert sich die Signatur bei
    JEDEM Boot, obwohl sich am Inhalt nichts geaendert hat -> jedes
    Mal unnoetiger kompletter Neuscan. Jetzt nur noch eine Ort-
    Kennung ("usb:"/"fat:") + relativer Ordnername + mtime, sortiert.
    Mit vertauschtem Mountpunkt bei identischem Inhalt getestet:
    Signatur bleibt jetzt stabil.
  - (b) VOLLSCAN TROTZ KURZER VERZOEGERUNG: der erste Cache-Vergleich
    lief VOR _wait_for_usb_stable() - bei einem Kaltstart, wo USB im
    Moment der Signatur-Bildung noch nicht gemountet ist, fuehrte das
    IMMER zu einem Mismatch und kompletten Neuscan, selbst wenn sich
    am Inhalt gar nichts geaendert hatte. scan_games() prueft jetzt:
    erwartet der Cache USB, sehen wir aber noch keines, wird erst
    gewartet und NEU verglichen, bevor komplett neu gescannt wird.
    Getestet: Kaltstart mit 0.5s verzoegertem Mount nutzt jetzt den
    Cache (~1.5s statt Vollscan).
  - _wait_for_usb_stable() liefert jetzt drei Zustaende (True=stabil,
    None=kein USB im Spiel, False=USB da aber nicht rechtzeitig
    stabil) statt nur True/False - scan_games() cached das Ergebnis
    bei False NICHT mehr, damit eine moeglicherweise unvollstaendige
    Liste nicht dauerhaft haengen bleibt (naechster Boot scannt dann
    einfach erneut). Alle drei Zustaende einzeln getestet, dazu ein
    deterministischer Test der Kernlogik ohne Threading (ein erster
    Thread-basierter Test hatte ein GIL-Zeitplanungsproblem, das sich
    als Testartefakt herausstellte, kein echter Bug).
  - SIGHUP-Handler ergaenzt (nutzt denselben, bereits getesteten
    Handler wie SIGTERM aus v1.37) - schuetzt vor eingefrorenem
    Bildschirm, wenn die SSH-Sitzung waehrend eines manuellen Tests
    (der in der README empfohlene Weg: "python3 frontend.py" direkt
    per SSH) getrennt wird.
  - Neu im Paket: install_offline.sh (Offline-Gegenstueck zu
    install.sh, mit automatischer Sicherung der alten Version vor
    jedem Update) und PC-Tools/obs_setup.py + OBS_Setup_starten.bat
    (legt eine lokale OBS-Overlay-Kopie mit fest eingetragener
    MiSTer-IP an) - beide unabhaengig getestet (install_offline.sh:
    Neuinstallation und Update-Fall inkl. Erhalt eigener Anpassungen
    und Backup-Erstellung; obs_setup.py: IP-Validierung und HTML-
    Generierung gegen die echte aktuelle stream_overlay.html).
  - 48 Kombinationen kompletter Regressionstest weiterhin bestanden.

Neu in v1.52 (Boxart schon auf Ordner-Ebene, wenn der Ordner ein
Spiel ist):
  - Manche Sammlungen (haeufig bei PSX mit Mehrfach-CD-Spielen) legen
    pro Spiel einen eigenen Unterordner mit den Disc-Dateien an - der
    Ordnername entspricht dann dem Spieletitel. Bisher zeigte das
    Frontend fuer JEDEN Ordner-Eintrag "kein Artwork", auch wenn der
    Ordner eigentlich ein einzelnes, katalogisiertes Spiel ist.
  - draw_art_panel() nutzt fuer Ordner-Eintraege jetzt den reinen
    Ordnernamen (ohne den anzeigenden Schraegstrich-Suffix) fuer die
    Cover-/Metadaten-Suche - findet sich ein Treffer (z.B. weil der
    Ordner "Final Fantasy VII" heisst und dafuer ein Cover vorliegt),
    wird er genauso angezeigt wie bei einem normalen Spiele-Eintrag.
    Der Titel behaelt den Schraegstrich, bleibt also weiterhin klar
    als Ordner erkennbar. Reine Organisations-Ordner (z.B.
    "1 US-A-E") ohne passenden Datenbank-Treffer zeigen unveraendert
    "kein Artwork" statt eines Fehlers.
  - Getestet: Ordner mit passendem Spielenamen zeigt Cover+Infos
    korrekt (Pixel-Analyse bestaetigt), Organisations-Ordner ohne
    Treffer zeigt weiterhin sauber "kein Artwork" ohne Absturz,
    48 Kombinationen kompletter Regressionstest.

Neu in v1.51 (BUGFIX: USB-Absicherung aus v1.49 griff nicht zuverlaessig):
  - Nutzer-Rueckmeldung: nach einem Kaltstart tauchten immer noch
    nicht alle Spiele auf. Ursache: die v1.49-Pruefung testete nur, OB
    der USB-Mountpunkt EXISTIERT - bei einer langsam hochlaufenden
    Festplatte kann der Ordner selbst aber schon da sein, WAEHREND
    die Dateiliste dahinter noch nachzieht. "Existiert" war also kein
    verlaesslicher Hinweis auf "wirklich fertig".
  - Fix: prueft jetzt die TATSAECHLICHE Anzahl an Eintraegen in jedem
    USB-Basisordner (os.listdir), nicht nur dessen Existenz. Ein
    vorhandener, aber noch LEERER Ordner zaehlt bewusst NICHT als
    stabil. Verlangt ausserdem zwei aufeinanderfolgende gleiche
    Messungen (statt nur einer) - robuster gegen zufaellige Treffer
    beim Abtasten. Zeitlimit grosszuegiger (10s statt 4s).
  - Dabei einen echten, noch ungetesteten Fehler in der eigenen
    Zwischenversion gefunden UND behoben, bevor er auslieferte: eine
    verwaiste Codezeile haette bei jedem Aufruf einen Laufzeitfehler
    (NameError) ausgeloest.
  - Getestet: 5 Szenarien - Ordner existiert sofort aber Inhalt kommt
    langsam nach (wartet jetzt korrekt bis zur echten Stabilisierung,
    vorher haette es faelschlich sofort "fertig" gemeldet), kein USB
    konfiguriert, Ordner bleibt dauerhaft leer, USB schon vollstaendig
    bereit, Inhalt aendert sich staendig (Zeitlimit greift zuverlaessig).

Neu in v1.50 (Anzahl-Anzeige in der Kategorienliste entfernt):
  - Die Zahl neben jedem Kategorienamen (z.B. "NES  7631") ist auf
    Nutzerwunsch entfernt - der freiwerdende Platz kommt jetzt dem
    Kategorienamen selbst zugute (maxc-Berechnung entsprechend
    erweitert, keine unnoetig kurze Abschneidung mehr).

Neu in v1.49 (Ordnerstruktur-Navigation, USB-Timing-Absicherung):
  - GROSSER UMBAU: Spiele-Systeme werden nicht mehr flach aufgelistet,
    sondern als Baumstruktur ({"folders":{...}, "items":[...]})
    gescannt und angezeigt - die eigene Ordnerstruktur (beliebig tief
    verschachtelt) wird 1:1 im Frontend nachgebildet. Ordner erscheinen
    als eigene, anklickbare Eintraege (immer zuerst in der Liste, dann
    die Spiele, je alphabetisch sortiert). Enter/A wechselt in einen
    Ordner hinein, ESC/B geht eine Ordnerebene nach oben (erst danach
    zurueck zu den Kategorien). Kopfzeile zeigt den Pfad als Breadcrumb
    ("SNES / 1 US-A-E"). Systeme ohne Unterordner ueberspringen diesen
    Zwischenschritt automatisch.
  - Region-Dedup laeuft jetzt PRO ORDNER statt global ueber das ganze
    System - verhindert, dass alphabetisch/regional aufgeteilte
    Sammlungen faelschlich ueber Ordnergrenzen hinweg zusammengemischt
    werden.
  - Alle anderen Kategorien (Zuletzt gespielt/Cores/Scripts/System)
    werden einheitlich als "flache" Baumknoten (ohne Unterordner)
    dargestellt - der komplette Rendering-/Navigations-Code behandelt
    dadurch alle Kategorien gleich.
  - games_cache.json-Speicherformat auf die Baumstruktur umgestellt
    (rekursive Serialisierung). "Nur katalogisierte Spiele"-Filter
    arbeitet jetzt rekursiv, leer gefilterte Unterordner fallen weg.
  - BUGFIX: Scan lief manchmal, bevor USB-Laufwerke nach einem
    Kaltstart fertig eingehaengt waren (moeglich seit v1.48s vor-
    gezogenem Bildschirmwechsel) - fehlende Spiele wurden dann noch
    dazu gecacht. Neue _wait_for_usb_stable(): wartet bis zu 4s,
    aber NUR beim seltenen tatsaechlichen Scan-Fall, nie beim
    schnellen Cache-Treffer-Normalfall.
  - Getestet: rekursiver Scan mit realistischer mehrstufiger Struktur,
    Region-Dedup pro Ordner, Mehrfach-Laufwerk-Zusammenfuehrung,
    JSON-Rundlauf mit tiefer Verschachtelung, rekursive Curated-
    Filterung (inkl. Ordner-Bereinigung), komplette Navigation
    (rein/verschachtelt/schrittweise raus), Spielstart aus 2 Ebenen
    Tiefe (Pfad/RBF/Zuletzt-gespielt korrekt), USB-Wartelogik mit 4
    Szenarien, 48 Kombinationen kompletter Regressionstest.

Neu in v1.48 (BUGFIX: Frontend blieb manchmal beim Booten im MiSTer-OSD
haengen, Musik lief aber schon):
  - Strukturfehler gefunden: enter_console_mode() (schaltet MiSTer per
    F9-Injektion ueberhaupt erst auf UNSEREN Framebuffer um - vorher
    ueberdeckt MiSTers eigenes Wallpaper alles permanent) passierte
    bisher in run(), also NACH dem kompletten build_categories()-Scan
    in __init__(). War der Scan aus irgendeinem Grund langsam (z.B.
    ein USB-Laufwerk, das nach laengerem vollstaendigem Ausschalten
    erst noch verzoegert bereit wird, oder ein tatsaechlicher Neu-
    Scan), blieb der Bildschirm bis dahin im MiSTer-OSD haengen -
    Musik lief bereits (MusicPlayer startet noch frueher), das
    eigentliche Frontend blieb aber unsichtbar. Exakt das gemeldete
    Verhalten.
  - Fix: enter_console_mode()/set_cursor_blink()/inp.grab() jetzt ganz
    am Anfang von __init__(), VOR dem Scan. Der Lade-Fortschrittsbalken
    (_draw_scan_progress(), seit v1.30 vorhanden) wird dadurch jetzt
    auch tatsaechlich sichtbar, egal wie lange der Scan braucht -
    vorher zeichnete er auf einen Framebuffer, der noch gar nicht der
    aktive Bildschirm war.
  - EHRLICHER HINWEIS: __init__() selbst kann in der Sandbox nicht
    automatisiert durchlaufen werden (braucht echte /dev/fb0, echte
    Eingabegeraete - war waehrend des gesamten Projekts nie moeglich,
    alle Tests nutzen Frontend.__new__() und ueberspringen __init__).
    Die neue Reihenfolge wurde daher per sorgfaeltiger Code-Durchsicht
    verifiziert (keine Abhaengigkeit auf self.music/self.cats vor deren
    Definition), nicht per automatisiertem Test der echten Boot-
    Sequenz. Rueckmeldung nach dem naechsten echten Kaltstart (nach
    laengerem vollstaendigem Ausschalten) willkommen.

Neu in v1.47 (WICHTIGE KORREKTUR: Bewegung selbst beschleunigt, nicht
nur die Abtastrate):
  - Nutzer-Rueckmeldung nach v1.46: trotz 100Hz-Abtastung "blieben
    Equalizer und Glow-Farbwechsel gleich". Ursache gefunden: beide
    Effekte sind auf grobe, DISKRETE Stufen begrenzt (Equalizer:
    max. ~8 Pixel-Hoehenstufen bei CRT-Groesse; Pulsieren: 20
    Farbstufen aus dem v1.32-Cache-Fix). Ab einem Punkt bringt
    schnelleres NACHSCHAUEN nichts mehr, wenn sich der zugrunde
    liegende Wert selbst nicht oefter aendern KANN - v1.42-46 haben
    also weit ueber den Punkt hinaus optimiert, an dem es noch etwas
    gebracht hat.
  - Fix: die Bewegung selbst beschleunigt, nicht nur die Abtastung.
    Equalizer-Schwingungsfrequenz auf CRT von 2.2 auf 9.0 (rund 4x
    schnellerer Zyklus). Pulsier-Zykluslaenge auf CRT von 3.2s auf
    0.8s (4x), PLUS Farbstufen von 20 auf 60 erhoeht (feinere
    Abstufung, da auf CRT der Cache-Vorteil aus v1.32 kaum ins
    Gewicht faellt - draw() kostet dort ohnehin <1ms). HDMI ueberall
    unangetastet (Cache-Vorteil bleibt dort wichtig).
  - Getestet: tatsaechliche Anzahl VERSCHIEDENER Farbwerte/Hoehen pro
    Sekunde direkt gemessen (nicht nur Tick-Frequenz) - CRT zeigt
    jetzt 7 statt 2 echte Pulsierfarben/Sekunde, durchlaeuft den
    Equalizer-Hoehenbereich ca. 4x oefter pro Sekunde als HDMI.

Neu in v1.46 (Equalizer + Pulsieren auf CRT nochmal deutlich schneller):
  - Nach dem elif-Bugfix in v1.45 (der die eigentliche Bremse war) auf
    ausdruecklichen Wunsch nochmal aufgedreht: CRT-Takt von 0.025s auf
    0.01s (Ziel ~100 Aktualisierungen/Sekunde). Betrifft alle vier
    zusammengehoerigen Stellen (_eq_tick(), _pulse_tick(), beide
    Kandidaten-Intervalle in next_action()). HDMI ueberall unangetastet.
  - Getestet mit realistischer Zeitsimulation: ~87 Zeichenvorgaenge/
    Sekunde gemessen (vorher 37/s in v1.45) - deutlich mehr als
    doppelt so schnell. draw() bleibt auf CRT durchgehend <1ms, bei
    87-100 Aufrufen/Sekunde also weiterhin >90% Leerlaufzeit uebrig.

Neu in v1.45 (BUGFIX: Equalizer/Glow liefen nie mit eigenem Takt):
  - Echter Logikfehler gefunden: next_action() nutzte eine elif-Kette
    fuer die drei Tick-Mechanismen (Laufschrift/Equalizer/Pulsieren).
    Da "track_needs" (Songtitel muss scrollen) bei praktisch jedem
    echten Songnamen zutrifft, wurde der Equalizer-Tick dadurch DAUER-
    HAFT uebersprungen - er lief nie mit seinem eigenen 0.025s-Takt,
    sondern nur als Zufallsprodukt des 6x langsameren Laufschrift-
    Taktes (0.15s). Das erklaert das gemeldete "Stocken" trotz der
    Beschleunigungen in v1.42-44.
  - Gleicher Fehler auch beim AEUSSEREN Aufwach-Timeout: bevorzugte
    bisher den 0.18s-Laufschrift-Takt vor dem schnelleren Equalizer-
    Takt. Jetzt min() ueber alle relevanten Kandidaten statt einer
    Prioritaetsreihenfolge.
  - Fix: alle drei Ticks werden jetzt unabhaengig (if statt elif)
    geprueft und koennen je einzeln einen Redraw ausloesen - jeder
    Tick drosselt sich weiterhin selbst ueber seinen eigenen internen
    Zeitstempel, daher ist das gefahrlos.
  - Getestet: mit realistischer Zeitsimulation (echtes time.sleep()
    zwischen Zyklen) gemessen - 37 Zeichenvorgaenge/Sekunde auf CRT
    TROTZ aktiver Laufschrift (vorher waere es bei ~6.7 gedeckelt
    gewesen). Aeussere Timeout-Werte end-to-end bestaetigt (0.025s
    CRT trotz track_needs=True, HDMI weiterhin sinnvoll bei 0.18s).
    8 Kombinationen kompletter Regressionstest.

Neu in v1.44 (Pulsierende Markierung auf CRT viel schneller):
  - _pulse_tick() (die "atmende" Markierungsfarbe) lief seit v1.29
    unveraendert auf 0.9s - wirkte neben dem inzwischen viel
    schnelleren Equalizer (v1.42/43) traege/nachhinkend. Jetzt auf
    CRT genauso flott wie der Equalizer (0.01s). HDMI unangetastet
    bei 0.9s.
  - Zusaetzlich musste der STANDARD-Aufwach-Takt in next_action() (der
    "else"-Zweig ohne Musik/Marquee) auflösungsabhaengig werden - die
    Markierung pulsiert naemlich IMMER (nicht nur bei laufender
    Musik), der bisherige feste 1.0s-Standardtakt haette den neuen
    schnellen internen Puls-Takt sonst nie oft genug abgefragt. Auf
    CRT jetzt ebenfalls 0.025s, HDMI bleibt bei 1.0s.
  - Getestet: beide Aufloesungen direkt gemessen, UND end-to-end mit
    aufgezeichneten Timeout-Werten bestaetigt, dass next_action() im
    Leerlauf (keine Musik) auf CRT tatsaechlich mit 0.025s statt 1.0s
    aufwacht.

Neu in v1.43 (Equalizer auf CRT ~3x schneller als v1.42):
  - CRT-Takt von 0.08s weiter auf 0.025s verkuerzt (~40 Aktualisierungen/
    Sekunde) - HDMI unangetastet bei 0.35s. Beide zusammengehoerigen
    Stellen wieder angepasst (_eq_tick() + Aufwach-Intervall).

Neu in v1.42 (Equalizer auf CRT nochmal schneller):
  - CRT-Takt von 0.15s (v1.40) weiter auf 0.08s verkuerzt - dieselbe
    sichere Untergrenze wie bei REPEAT_INTERVAL fuer die Navigation.
    12.5 statt 6.7 Aktualisierungen/Sekunde. HDMI bleibt unangetastet
    bei 0.35s. Betrifft wieder beide Stellen (_eq_tick() UND das
    Aufwach-Intervall in next_action()), die zusammenpassen muessen.

Neu in v1.41 (Songtitel-Laufschrift schneller):
  - CRT: Takt von 0.35s auf 0.15s verkuerzt (wie beim Equalizer in
    v1.40) - draw() ist dort guenstig genug, dass es nicht ins
    Gewicht faellt.
  - HDMI: Takt bleibt bei 0.35s (kein zusaetzliches Neuzeichnen, um
    den in v1.39 entschaerften Eingabestau nicht zu riskieren) -
    stattdessen ruecken pro Tick 2 Zeichen statt 1 weiter. Verdoppelt
    die gefuehlte Geschwindigkeit (2.86 -> 5.71 Zeichen/s) OHNE eine
    einzige zusaetzliche Neuzeichnung.
  - Randfall getestet: die groessere Schrittweite auf HDMI schiesst
    beim Erreichen des Textendes nie ueber max_off hinaus (min()-
    Begrenzung), Pause-am-Ende-Verhalten bleibt unveraendert korrekt.

Neu in v1.40 (Equalizer-Takt auf CRT verkuerzt):
  - Equalizer-Balken pulsieren auf CRT jetzt alle 0.15s statt 0.35s -
    draw() ist dort so guenstig (durchgehend <1ms gemessen), dass die
    haeufigere Aktualisierung nicht ins Gewicht faellt. HDMI bleibt
    bewusst bei 0.35s, um den in v1.39 entschaerften Eingabestau nicht
    wieder zu riskieren. Betrifft sowohl den Tick selbst (_eq_tick())
    als auch das Aufwach-Intervall in next_action() - beide muessen
    zusammenpassen, sonst wuerde der schnellere Tick nie rechtzeitig
    abgefragt. Mit Grenzfall (Hoehe genau 400) getestet.

Neu in v1.39 (Wiederholrate gedrosselt gegen HDMI-Eingabestau):
  - Frisch profiliert (realistische HD-Cover, echte Navigation): kein
    einzelner Flaschenhals mehr uebrig - text()/clear()/rect() liegen
    nun alle in aehnlicher Groessenordnung, alle bereits ueber die
    gecachten, schnellen Pfade. Die Restkosten sind inhaerent am
    "immer komplett neu zeichnen"-Ansatz.
  - Maximale Wiederholrate beim Halten einer Richtungstaste von 0.05s
    (20/s) auf 0.08s (12.5/s) gedrosselt - auf schwacher ARM-Hardware
    kann ein volles HDMI-Neuzeichnen laenger als 0.05s dauern, wodurch
    sich Eingaben stauen konnten (spuerbarer Lag beim Halten). CRT ist
    schnell genug, dass der Unterschied dort nicht auffaellt. Mit
    echten simulierten Tastendruecken bestaetigt: Intervall pendelt
    sich jetzt bei 0.08s ein statt Richtung 0.05s zu laufen.
  - text()-Mikrooptimierung bewusst NICHT vorgenommen: bereits klug
    pro Zeilenmuster gecacht (nicht nur pro Zeichen), weiterer Umbau
    haette nur Wörterbuch-Nachschlaege gespart (Bruchteile von
    Mikrosekunden) bei echtem Risiko fuer diese zentrale, gut
    getestete Funktion - Aufwand/Risiko stand in keinem Verhaeltnis
    zum Nutzen.

Neu in v1.38 (Boot-Animation-Tempo, Boxart-Downloader parallel):
  - Boot-Animation zeigt Frames jetzt in ihrer tatsaechlich
    gespeicherten Groesse (zentriert, mit Rand) statt sie zwanghaft
    auf Vollbild hochzuskalieren - gemessen ca. 7x fluessiger auf
    HDMI bei einer 960x540- statt 1920x1080-Quelle (weniger zu
    dekodierende Bilddaten pro Frame ist der dominante Kostenfaktor,
    per cProfile bestaetigt: zlib.decompress dominierte vorher die
    Zeit). Ist eine Quelle doch groesser als der Bildschirm, wird
    automatisch (aber langsamer) heruntskaliert statt abzustuerzen.
  - mister_boxart.py und boxart_fetch.py (PC-Tools) laden jetzt mit
    6 parallelen Downloads statt einem nach dem anderen (plus einem
    festen 0.2s-Delay pro Cover, das jetzt entfaellt) - gemessen ca.
    5x schneller in einem realistischen Testszenario mit simulierter
    Netzwerklatenz, ohne Race-Conditions (jedes ROM schreibt seine
    eigene Datei).

Neu in v1.37 (KORREKTUREN_fuer_Dragrem.md - vier Fixes):
  - BUGFIX (schwerwiegend): kill sendet SIGTERM, das Python ohne
    Handler OHNE jeden finally-Block beendet - der Aufraeum-Code in
    run() (Bildschirm loeschen, Eingaben freigeben, F12 zurueck ins
    MiSTer-Menue) lief deshalb nie, wenn update_frontend.sh/install.sh
    eine laufende Instanz per kill beendet hat. Bildschirm blieb im
    letzten Frontend-Zustand haengen. Neuer SIGTERM-Handler wandelt
    das Signal in SystemExit um, die bestehenden finally-Bloecke
    laufen jetzt normal durch. Mit echtem Prozess + echtem kill
    bestaetigt.
  - BUGFIX: install.sh's sysart-Kopierlogik (cp -rf) hat bei jedem
    erneuten Lauf (z.B. Update) ALLE Logos ueberschrieben, auch selbst
    ersetzte. Jetzt cp -rn (no-clobber) - nur fehlende Dateien werden
    ergaenzt, vorhandene (Standard ODER eigene) bleiben unangetastet.
  - Diese Versionszeile + die Changelog-Eintraege v1.30-v1.36 waren im
    Git-Repository nicht nachgezogen worden (nur in der separaten
    Build-Kopie aktualisiert) - hiermit nachgeholt.
  - Fehlender Shebang ergaenzt (siehe KORREKTUREN_fuer_Dragrem.md fuer
    Details, welche Datei betroffen war).

Neu in v1.30-v1.36 (nachtraeglich ergaenzt, siehe Git-Commit-Historie
fuer die vollstaendigen Einzelbeschreibungen):
  - v1.30: "Zuletzt gespielt"-Kategorie, Mini-Icons (spaeter auf
    Nutzerwunsch wieder entfernt), Lade-Fortschrittsbalken beim
    tatsaechlichen Scan (nicht beim Cache-Treffer).
  - v1.31: Musik-Sicherheitsnetz gegen haengenden mpg123, Cache-
    Signatur-Fix (spaeter in v1.33 wegen Boot-Regression zurueckgerollt),
    install.sh (Erstversion).
  - v1.32: Standard-Fusszeile entfernt, Header-Ueberlappung bei langen
    Systemnamen behoben, Glyphen-Cache-Fix gegen HDMI-Lag (Pulsierfarbe
    auf 20 Stufen gerundet).
  - v1.33: Boot-Regression von v1.31 zurueckgerollt (Cache-Signatur
    wieder auf schnelle Nur-oberste-Ebene-Pruefung).
  - v1.34: Boxart-Schlagschatten von echtem Pixel-Blending auf
    vorgemischte, gecachte Farbe umgestellt - Hauptursache fuer
    verbliebenen HDMI-Lag, vierfache Beschleunigung.
  - v1.35: Now-Playing-Anzeige in die Fusszeile verschoben, rein
    japanische ROM-Titel werden ausgefiltert (Mehrfach-Region-Tags
    bleiben erhalten).
  - v1.36: Boot-Animation erkennt automatisch CRT/HDMI-Modus,
    install.sh zeigt echte Fehlermeldungen + automatischer Fallback
    ohne SSL-Zertifikatspruefung.

Neu in v1.29 (optische Verfeinerungen):
  - Pro-System-Akzentfarbe: Markierung, Boxart-Rahmen und Artbox-Rahmen
    faerben sich jetzt passend zum aktuellen System ein (NES-Rot,
    Sega-Blau, SNES-Lila usw.) statt immer Standard-Blau.
  - Pulsierende Markierung: dezentes, LANGSAMES Aufhellen/Abdunkeln
    der Auswahl (mehrere Sekunden pro Zyklus, bewusst selten aktualisiert
    - siehe Hinweis zu Bildschirmriss-Vermeidung in frueheren Versionen).
  - Glow-Effekt um die Markierung, Schlagschatten unter dem Boxart-
    Cover - ueber einen neuen Alpha-Blend-Helfer in der Framebuffer-
    Klasse (mischt vorhandene Pixel mit einer Farbe, statt sie zu
    ueberschreiben).
  - Equalizer-Balken neben der Now-Playing-Anzeige, solange Musik
    laeuft (rein animiert, keine echte Lautstaerke-Messung noetig).

Neu in v1.28 (Zufalls-Taste):
  - Neue Aktion "random": springt zu einem zufaelligen Eintrag - in
    der Spieleliste (Seite 2) zu einem zufaelligen Spiel, im
    Kategorien-Menue (Seite 1) zu einer zufaelligen Kategorie. Wird
    nie zweimal hintereinander derselbe Eintrag (bei mehr als einem
    vorhandenen). Standardmaessig auf die R-Taste gelegt, ueber
    "Configure buttons" auf eine beliebige andere Taste umlegbar.

Neu in v1.27 (Log-Datei-Begrenzung):
  - /tmp/frontend.log wuchs bisher unbegrenzt - bei laengerer Laufzeit
    oder haeufigen Neustarts haette das auf Dauer Speicher auf der
    (meist RAM-basierten) /tmp-Partition verbraucht. LOG() kuerzt die
    Datei jetzt automatisch, sobald sie 512 KB ueberschreitet (behaelt
    die letzten 256 KB, mit Hinweiszeile). Zusaetzlich prueft
    frontend_boot.sh beim Booten selbst, falls die Datei durch rohe
    Fehlerausgaben (Python-Tracebacks ueber stderr) trotzdem waechst.

Neu in v1.26 (BUGFIX Mehrteiler + Overlay-Politur):
  - KRITISCH: Die Region-Dedupe aus v1.23 fasste auch Disc-/CD-Marker
    zusammen - "Spiel (Disc 1)" und "Spiel (Disc 2)" landeten auf
    demselben Schluessel, wodurch Disc 2+ komplett aus der Liste fiel
    und nicht mehr startbar war (betraf PSX/Saturn/MegaCD). Der
    kanonische Schluessel behaelt Disc-/CD-/Side-/Part-Marker jetzt
    bei; Mehrfach-Regionen werden weiterhin zusammengefasst. Dieselbe
    Korrektur in mister_boxart.py, mister_gameinfo.py und
    boxart_fetch.py, damit auch Disc 2+ Cover/Metadaten bekommt.
  - display_name() zeigt den Disc-Marker mit an, sonst waeren
    mehrteilige Spiele in der Liste nicht auseinanderzuhalten.
  - Stream-Overlay: im Kategorien-Menue (Seite 0) wird jetzt die
    markierte Kategorie gezeigt statt eines veralteten Spieltitels aus
    der zuletzt geoeffneten Liste. Titel im Overlay ohne Klammer-Tags
    (Cover wird weiter ueber den echten Dateinamen geladen).

Neu in v1.25 (Musik-Pause beim echten OSD, F10-Grenze dokumentiert):
  - BUGFIX: open_osd() pausierte die Musik nie - beim Oeffnen des
    echten MiSTer-OSD (F12) lief die Wiedergabe einfach weiter. Jetzt
    pausiert/setzt sie fort wie bei run_core()/run_script().
  - Per direktem Geraetetest bestaetigt (cat /dev/input/eventX waehrend
    ein Core laeuft liefert 0 Bytes, unabhaengig von der gedrueckten
    Taste): MiSTer beansprucht die Tastatur waehrend eines laufenden
    Spiels exklusiv. F10 und die Start+Select-Kombo koennen deshalb
    NIE waehrend des Spiels selbst ankommen - das ist eine echte
    Plattformgrenze, kein Frontend-Bug. Der einzige zuverlaessige Weg
    zurueck: MiSTer's eigenes Menue per F12/Menue-Taste oeffnen, dort
    "Exit to Menu Core" waehlen - das erkennt das Frontend automatisch
    (current_core()=="MENU"-Abfrage, unabhaengig von F10/Kombo). Die
    F10/Kombo-Erkennung in wait_game_exit() bleibt als harmloser
    Fallback im Code, falls sich das MiSTer-Verhalten je aendert.

Neu in v1.24 (BUGFIX: F10 im Spiel tat nichts):
  - Die README versprach seit langem "F10 im Spiel -> zurueck ins
    Frontend" als zuverlaessigen Weg (im Gegensatz zu Start+Select am
    Pad, das per FPGA-Routing nicht immer ankommt) - tatsaechlich
    wurde F10 in wait_game_exit() aber nie abgefragt, nur die Start+
    Select-Kombo und der Core-Wechsel selbst. F10 auf der Tastatur
    waehrend eines laufenden Spiels tat also schlicht nichts.
    wait_game_exit() erkennt F10 jetzt genauso wie die Kombo und
    kehrt sofort ins Menue zurueck.

Neu in v1.23 (Zusammenfuehrung: Scan-Bereinigung + Curated-List):
  - Aus einem parallel gewachsenen Zweig uebernommen (dortige v1.23-25):
    Spiele-Scan geht jetzt beliebig tief (nicht mehr nur 2 Ordner-
    ebenen), bekannte Boot-/Test-Dateien (IGNORE_ROM_BASENAMES) sowie
    Beta/Proto/Demo/Hack/Bad-Dump-Tags (JUNK_TAGS) werden ausgefiltert,
    und Mehrfach-Regionen desselben Spiels werden zu einem Eintrag
    zusammengefasst (beste Region gewinnt). Neuer Menuepunkt "Curated
    list (DB-matched only)" zeigt optional nur Spiele mit Datenbank-
    Treffer (mister_gameinfo.py) - mit Sicherheitsnetz: Systeme ganz
    ohne Metadaten werden nicht gefiltert. Boot-Animation, Stream-
    Overlay und System-Artbox (aus diesem Zweig) sind unveraendert
    erhalten geblieben - die Hauptmenue-Einschraenkung auf nur
    Konsolen+Arcade aus dem parallelen Zweig wurde bewusst NICHT
    uebernommen, damit die Scripts-Kategorie (Boxart-/Musik-/Stream-
    Werkzeuge) weiterhin im Frontend selbst erreichbar bleibt.
  - Dieselbe Bereinigung (JUNK_TAGS + Region-Dedupe) steckt jetzt auch
    in mister_boxart.py, mister_gameinfo.py und boxart_fetch.py.

Neu in v1.22 (System-Artbox im Kategorien-Menue):
  - Kategorienamen jetzt kleiner geschrieben (Platz gespart).
  - Rechts neben der Liste erscheint eine Artbox mit dem Logo/
    Cover des gerade markierten Systems (aus /media/fat/frontend/
    sysart/<Systemkey>.art) - wechselt live beim Hoch/Runter-
    Scrollen durch die Kategorien. Ohne passende Datei erscheint
    ein dezenter Platzhalter statt eines Fehlers.

Neu in v1.21 (Zusammenfuehrung Boot-Animation + Stream-Overlay):
  - Boot-Animation (aus v1.20) und Stream-Overlay fuer OBS (dieser
    Merge) liefen als getrennte Zweige auseinander - hier
    zusammengefuehrt: beide Features sind jetzt gemeinsam aktiv.

Neu in v1.19 (Now-Playing als Laufschrift, Position korrigiert):
  - Now-Playing ueberlappte auf der Kategorien-Seite mit dem Beginn
    der Liste. Steht jetzt rechts neben dem "MiSTer"-Logo, in eigener
    Zeile daneben statt darunter.
  - Kein "Now playing:"-Label mehr - stattdessen laeuft der volle
    Songtitel als Laufschrift durch (wie bei langen Spieletiteln in
    der Liste), an beiden Stellen (neben dem Logo UND unter den
    Spielinfos im Boxart-Block). Vorher wurde der Titel bei zu
    langen Dateinamen einfach abgeschnitten/lief ins Leere.

Neu in v1.18 (Now-Playing-Anzeige + Bugfix Tastenbelegung):
  - BUGFIX: Der Tastenbelegungs-Assistent blieb bei "Hoch" haengen,
    wenn das Pad sein D-Pad als Analogachse meldet (die meisten
    Pads tun das) - der Assistent wartete auf ein reines Tasten-
    Event (EV_KEY) und ignorierte Achsen-Events komplett. Erkennt
    jetzt einen klaren Analogausschlag in die passende Richtung als
    "funktioniert schon nativ" und springt automatisch zur naechsten
    Abfrage, statt endlos zu warten.
  - Neu: Anzeige des aktuell spielenden Songs. Oben links auf der
    Kategorien-Uebersicht, und unterhalb der Spielinfos im Boxart-
    Block auf der Kategorie-Ansicht. Aktualisiert sich sofort beim
    manuellen Ueberspringen (Y-Taste).

Neu in v1.17 (Sprachumschaltung + eigene Tastenbelegung):
  - Sprachumschaltung Deutsch/Englisch fuer alle sichtbaren Texte im
    Frontend (Kopf-/Fusszeilen, System-Menue, Beenden-Dialog, Boxart-
    Infos, "no artwork"). Umschaltbar im System-Menue, Auswahl bleibt
    ueber Neustarts erhalten (/media/fat/frontend/language).
  - Eigene Tastenbelegung: neuer Menuepunkt "Configure buttons" im
    System-Menue startet einen Assistenten, der nacheinander nach
    jeder Kernaktion (Hoch/Runter/Links/Rechts/OK/Zurueck/Menue)
    fragt und den naechsten tatsaechlichen Tastendruck (Tastatur
    ODER Pad, egal welches Geraet) als Belegung uebernimmt. Wird in
    /media/fat/frontend/keymap_custom.json gespeichert und beim
    naechsten Start automatisch bevorzugt (vor der Standardbelegung).
    "Reset to default buttons" setzt sie wieder zurueck.

Neu in v1.16 (Hintergrundmusik):
  - MP3-Hintergrundmusik per mpg123 (extern, kein eigener Decoder
    noetig). Playlist aus /media/fat/music/*.mp3, zufaellig gemischt
    beim Start, naechster Song automatisch sobald einer zu Ende ist.
  - Musik pausiert automatisch beim Start eines Spiels/Cores und
    laeuft beim Zurueckkehren ins Frontend automatisch weiter.
  - Neuer Menuepunkt im System-Menue: Music On/Off. Status wird in
    /media/fat/frontend/music_enabled gespeichert (bleibt ueber
    Neustarts hinweg erhalten).
  - Y-Taste im Frontend: naechster Song (manueller Songwechsel).
  - UI-Texte auf Englisch, passend zum Rest seit v1.13.

Neu in v1.15 (Boxart-Spalte nutzt die volle Hoehe):
  - Die Boxart-Spalte begann bisher auf Hoehe der Liste (list_y), nicht
    auf Hoehe der Kopfzeile (oy) - der Header nutzt aber nur den linken
    Teil der Zeile (Kategorie-Name + Anzahl), rechts daneben blieb ein
    ungenutzter Streifen bis zur Liste stehen. Die Spalte beginnt jetzt
    auf Hoehe der Kopfzeile, das Cover bekommt dadurch spuerbar mehr
    Platz (rund 20-25% mehr Hoehe, je nach Aufloesung).

Neu in v1.14 (Footer aufgeraeumt):
  - BUGFIX: Der Footer-Text wird nicht umgebrochen, sondern bricht beim
    Erreichen des Bildschirmrands einfach ab (Framebuffer.text()) - auf
    schmalen Aufloesungen (z.B. CRT) fehlte dadurch oft das Wichtigste
    am Ende ("ESC:Quit"). Beide Footer haben jetzt eine dritte,
    kompakte Stufe fuer schmale Bildschirme, die garantiert komplett
    ins Bild passt.
  - Die "^ more"/"v more"-Scroll-Hinweise im Hauptmenue sind weg -
    unnoetiger Text, der Platz weg genommen hat.
  - Im Spiele-Menue faellt in den kompakten Footer-Stufen das
    ueberfluessige, alleinstehende "Nav" weg - "A:Start"/"B:Back"
    ruecken dadurch weiter nach links.

Neu in v1.13 (Uebersetzung ins Englische):
  - Alle Texte, die im Frontend auf dem Bildschirm erscheinen, sind
    jetzt auf Englisch statt Deutsch - fuer ein internationales
    Publikum. Betrifft: Kopfzeilen, Fusszeilen-Hinweise, Zaehler
    ("X categories"/"X entries"), Scroll-Pfeile, den System-Menue
    (Open MiSTer OSD, Rescan game list, Restart MiSTer, Quit frontend,
    ...), die Beenden-Bestaetigung (Quit the frontend? / Yes / No),
    Boxart-Infos (Players/Year) und den "no artwork"-Platzhalter.
  - Code-Kommentare und die Versionshistorie in diesem Docstring
    bleiben bewusst auf Deutsch (reine Entwickler-Dokumentation, nicht
    im laufenden Frontend sichtbar). Bei Bedarf auch das noch
    uebersetzbar.

Neu in v1.12 (Kleinkram am Beenden-Dialog):
  - Labels von "Abbrechen/Beenden" auf "Ja/Nein" umgestellt. "Nein"
    ist die Standardauswahl und steht rechts (Links waehlt weiterhin
    Ja, Rechts Nein).
  - BUGFIX Flackern beim Umschalten zwischen den beiden Optionen: Beim
    Neuzeichnen wurde vorher erst die Seite dahinter OHNE Dialog
    geflippt (fb.flip()) und direkt danach nochmal MIT Dialog drueber -
    der erste Flip war fuer einen Frame sichtbar und sorgte fuer das
    kurze Aufblitzen. draw_page_cats()/draw_page_items() bekommen jetzt
    einen flip-Parameter und lassen den Flip aus, wenn direkt danach
    noch der Dialog draufkommt - geflippt wird dann nur noch einmal,
    ganz am Ende.

Neu in v1.11 (Steuerung neu geordnet + Beenden-Bestaetigung):
  - Klarere, schlankere Belegung: Enter/A oeffnet ein Menue bzw. startet
    ein Spiel - die einzige Aktion dafuer. ESC/B geht eine Ebene
    zurueck; im Hauptmenue (Kategorien-Uebersicht) loest ESC/B jetzt
    eine BESTAETIGUNG aus statt sofort zu beenden.
  - Beenden-Bestaetigung: kleiner Dialog "Frontend wirklich beenden?"
    mit den Optionen Ja/Nein (Nein vorausgewaehlt, rechts). Links
    waehlt Ja, Rechts waehlt Nein, Enter bestaetigt die Auswahl. ESC/B
    im Dialog bricht sofort ab (sicherer Standard gegen Vertipper). Gilt
    fuer ESC, den B-Button, den 3x-Select-Kurzbefehl per Pad UND den
    Menuepunkt "Frontend beenden" im System-Menue - alle vier Wege
    fragen jetzt nach, keiner schliesst mehr sofort.
  - Hoch/Runter navigiert weiterhin einzelne Positionen (mit
    Turbo-Beschleunigung beim Halten, seit v1.10).
  - NEU: Links/Rechts springt jetzt seitenweise (eine sichtbare
    Bildschirmseite pro Druck) statt wie bisher nur "eine Ebene
    zurueck"/"Kategorie oeffnen". Wird die Taste gehalten, wachsen auch
    hier die Spruenge (1 -> 2 -> 3 -> 5 Bildschirmseiten pro Tick).
    Funktioniert auf beiden Seiten (Kategorien und Spieleliste).
  - Bild-auf/-ab, Pos1 und Ende sind komplett raus - dafuer springen
    jetzt L/R an der Schultertaste ebenfalls seitenweise (wie D-Pad
    links/rechts), statt einer eigenen Buchstabensprung-Logik zu
    folgen.
  - Der Buchstaben-Direktsprung per Tastatur (A-Z, seit v1.10) bleibt
    unveraendert bestehen - der nutzt eigene Tasten und kollidiert
    nicht mit der neuen Links/Rechts-Belegung.

Neu in v1.10 (Navigation deutlich beschleunigt):
  - BUGFIX/Feature: Die Spieleliste (Seite 2) sprang bisher am ersten
    bzw. letzten Eintrag einfach nicht weiter - man musste die komplette
    Liste durchscrollen, um z.B. von "#" zu "Z" zu kommen. Jetzt springt
    "runter" vom letzten Eintrag zum ersten und umgekehrt, genau wie es
    bei der Kategorienliste schon funktioniert hat.
  - Turbo-Sprung: Haelt man die Richtungstaste laenger gedrueckt, wird
    nicht nur schneller getickt (das gab es schon), sondern die
    Schrittweite waechst zusaetzlich mit (1 -> 2 -> 4 -> 10 Eintraege
    pro Tick). Bei sehr langen Listen kommt man dadurch in derselben
    Haltezeit deutlich weiter.
  - L/R bzw. Bild-auf/-ab (Sprung zum naechsten Anfangsbuchstaben-Block)
    liessen sich bisher nur einzeln druecken. Jetzt sind sie wie die
    Richtungstasten wiederholbar - gehalten hangelt man sich am Stueck
    durchs Alphabet.
  - Neu: Direktsprung per Tastatur. Eine Buchstabentaste (A-Z, Q-P-Reihe
    des QWERTY-Layouts) springt zum naechsten Eintrag mit diesem
    Anfangsbuchstaben, erneutes Druecken springt zyklisch zum
    naechsten Treffer - wie die Sprungsuche in klassischen
    Datei-Browsern. Funktioniert auf beiden Seiten (Kategorien und
    Spieleliste).
  - Neu: Pos1/Ende-Tasten springen direkt zum ersten bzw. letzten
    Eintrag der aktuellen Liste.

Neu in v1.9 (Cover nutzt den verfuegbaren Platz voll aus):
  - Die Cover-Hoehe war bisher fest auf 55% der Boxart-Spalte gedeckelt,
    egal wie viel oder wenig Text (Titel + Spieler/Jahr/Genre) tatsaechlich
    da war. Fehlten Spiele-Infos (z.B. mister_gameinfo.py noch nicht
    gelaufen), blieb darunter viel ungenutzter Platz. Jetzt wird zuerst
    die tatsaechlich benoetigte Texthoehe berechnet, das Cover bekommt
    danach den kompletten Rest (gedeckelt auf 35-85% der Spaltenhoehe,
    damit weder ein winziges Cover bei viel Text noch ein den Text
    verdraengendes Cover bei wenig/keinem Text entsteht).
  - Die kuenstliche 4x-Deckelung beim Hochskalieren kleiner Cover ist weg
    (jetzt 10x) - ein Relikt aus dem alten, viel kleineren Boxart-Block
    von v1.7. Dadurch fuellen kleine Cover die ihnen zustehende Flaeche
    jetzt tatsaechlich aus, statt klein und von Leerraum umgeben zu
    wirken.

Neu in v1.8.1 (Bugfix):
  - BUGFIX Boxart ueberlappte den Info-Text: Cover, die groesser als
    der fuer sie reservierte Platz waren (z.B. auf CRT-Aufloesungen mit
    wenig Platz in der Boxart-Spalte), wurden bisher NICHT verkleinert,
    sondern in Originalgroesse gezeichnet - dadurch ragten sie in den
    Bereich mit Spieler/Jahr/Genre hinein. ArtCache.get_scaled()
    verkleinert zu grosse Cover jetzt per Nearest-Neighbor passend in
    die Box. Zusaetzlich richtet sich die Textposition zur Sicherheit
    nach der tatsaechlich gezeichneten Bildhoehe statt nur nach dem
    reservierten Platz - so kann es auch bei sehr schmalen/kleinen
    Boxart-Spalten nicht mehr zur Ueberlappung kommen.

Neu in v1.8 (Zweiseitige Navigation):
  - Das Frontend zeigt jetzt zwei getrennte Seiten statt einer geteilten
    Ansicht. Seite 1 (Start): nur die Kategorien (Systeme, Arcade,
    Scripts, System) als grosse Liste ueber die volle Breite. Enter/A
    oeffnet die gewaehlte Kategorie auf Seite 2.
  - Seite 2 (Kategorie-Ansicht): Spieleliste links, bei Spiele- und
    Arcade-Systemen daneben eine eigene, breite Boxart+Info-Spalte -
    nicht mehr ein kleiner Block unten rechts, der Listenzeilen
    ueberlappt und diese ausblenden musste. Dadurch ist jetzt mehr
    Platz fuer Cover UND fuer die Titelzeilen der Liste gleichzeitig.
  - Navigation: B-Taste bzw. Pfeil links geht von der Kategorie-Ansicht
    zurueck ins Hauptmenue; ESC macht auf Seite 2 dasselbe, erst auf
    Seite 1 beendet ESC das Frontend. Enter/A auf Seite 1 oeffnet die
    Kategorie, auf Seite 2 startet es den markierten Eintrag - wie
    gehabt.
  - "Spieleliste neu einlesen" springt danach zurueck ins Hauptmenue,
    da sich Kategorien dabei geaendert haben koennen.

Neu in v1.7 (Fixes):
  - Single-Instance-Lock (/tmp/frontend.lock) - verhindert doppelte
    Instanzen, die um Framebuffer/Eingaben streiten. War in der
    README beschrieben, aber bisher nicht implementiert.
  - MGL-Shortcuts: Ordner mit .mgl-Dateien (z.B. das "Recently
    Played"-Skript) erscheinen jetzt im Frontend und sind startbar.
  - Game Boy Color als eigenes System (.gbc) - GBC-Cover/Metadaten
    werden jetzt gefunden statt doppelt geladen und ignoriert.
  - MiSTer.ini wird atomar geschrieben (Temp + rename) - ein Abbruch
    beim CRT/HDMI-Umschalten kann die Config nicht mehr zerstoeren.
  - Core-Start robuster: wartet auf den echten Core statt fixe 15s;
    langsam ladende CHDs werfen das Frontend nicht mehr ins Menue.
  - flip() ohne bytes()-Zwischenkopie (spart pro Frame eine ~8-MB-
    Allokation auf 1080p); "MiSTer neu starten" macht vorher sync.

Neu in v1.6:
  - Boxart-Block umgestaltet: Cover jetzt oben, Titel+Infos darunter
    ueber die VOLLE Blockbreite (statt in einer schmalen Spalte
    links vom Cover mit nur ~5 Zeichen Platz). Auf CRT jetzt ca.
    17 Zeichen pro Zeile statt 5. Der Titel bricht bei Bedarf auf
    eine zweite Zeile um, statt abgeschnitten zu werden.

Neu in v1.5:
  - BUGFIX: Die Auswahlmarkierung konnte beim Scrollen hinter den
    Boxart-Block "verschwinden" (Zeile lag im ausgeblendeten Bereich).
    Jetzt scrollt die Liste so, dass die Markierung IMMER oberhalb
    des Boxart-Blocks sichtbar bleibt - der nutzbare Sichtbereich
    endet effektiv kurz vor dem Block, nicht erst am Bildschirmrand.

Neu in v1.4:
  - BUGFIX Nachlauf-Scrollen: normale Tastatur-Pfeiltasten nutzten
    bisher die unkontrollierte Auto-Wiederholung der Tastatur selbst
    (jedes einzelne Event = ein voller Bildschirmaufbau -> nach
    laengerem Halten staute sich das und lief nach Loslassen noch
    Sekunden nach). Jetzt laufen auch normale Tasten ueber unsere
    eigene kontrollierte, beschleunigende Wiederholung wie beim
    Gamepad - reagiert sofort auf Loslassen.
  - Layout: Spieletitel werden nur noch OBERHALB des Boxart-Blocks
    angezeigt. Im Boxart-Bereich selbst steht links neben dem Cover
    jetzt Titel + Spieler/Jahr/Genre des ausgewaehlten Spiels.

Neu in v1.3:
  - Layout Variante A: Boxart+Infos sitzen jetzt als kompakter
    Block unten rechts statt die ganze rechte Spalte einzunehmen.
    Die Spieleliste ist dadurch fast ueber die volle Breite lesbar -
    nur die unteren Zeilen (dort wo der Boxart-Block liegt) sind
    schmaler. Laengere Spieletitel passen dadurch komplett rein.
  - blit() zusaetzlich defensiv abgesichert (schreibt nie eine
    andere Byte-Anzahl als angefordert - reine Vorsichtsmassnahme,
    aendert am Verhalten nichts).

Neu in v1.2:
  - "MiSTer"-Logo und Systemname jetzt weiss statt gelb
  - Kategorien-Spalte breiter auf kleinen Aufloesungen (CRT) ->
    "PlayStation", "Master System" etc. passen jetzt komplett
  - Dezente Scanlines (Retro-Touch) im linken Panel

Neu in v1.1:
  - Im Spiel: START+SELECT ca. 1 Sekunde gemeinsam halten
    -> zurueck ins Frontend (ohne OSD-Umweg)

Neu in v1.0:
  - System-Hintergrundbilder: legt man unter
    /media/fat/frontend/bg/ eine Datei <Systemkey>_<BREITE>x<HOEHE>.art
    (oder <Systemkey>.art) ab, wird sie in dieser Kategorie als
    abgedunkelter Vollbild-Hintergrund gezeigt.
    Erzeugen am PC:  python art_convert.py --bg --images nes.jpg
                     --out NES_320x240.art --size 320x240

Neu in v0.9:
  - Boxart wird auf grossen Aufloesungen automatisch ganzzahlig
    hochskaliert (Pixel-Look, gecacht) - sd-Cover fuellen 1080p
  - Arcade-Kategorie mit Info-Panel: Jahr, Hersteller, Kategorie
    werden live aus der jeweiligen MRA-Datei gelesen

Neu in v0.8:
  - BUGFIX: Eingaben-Freeze nach langem Gedrueckthalten behoben
    (Geraete-Events haben jetzt immer Vorrang vor Wiederholungen)
  - Schnellstart: Spieleliste wird gecacht statt bei jedem Start
    die Platte zu durchsuchen; System-Eintrag "Spieleliste neu einlesen"
  - System-Eintrag "Menue-Video: CRT/HDMI umschalten" - setzt den
    [Menu]-Block in der MiSTer.ini und startet neu

Neu in v0.7:
  - Kategorien-Spalte scrollt mit (Pfeil-Indikatoren oben/unten)
  - Gedrueckt halten von D-Pad/Stick wiederholt mit Beschleunigung
  - L/R bzw. Bild auf/ab springen zum naechsten Anfangsbuchstaben

Neu in v0.6:
  - Anzeigenamen ohne Klammer-Zusaetze (voller Name bleibt intern)
  - Laufschrift in der Auswahlzeile fuer lange Namen
  - Kategorien-Spalte passt ihre Breite automatisch an,
    kompaktere Kopf-/Fusszeile bei kleinen CRT-Aufloesungen

Neu in v0.5:
  - Spiele-Browser: eigene Kategorie pro System (NES, SNES, ...)
    mit allen ROMs aus /media/fat/games/<System>/
  - Spielstart per automatisch erzeugter MGL-Datei (Parameter
    aus der mrext-Systemdatenbank uebernommen)
  - Boxart-Anzeige aus vorkonvertierten .art-Dateien
    (/media/fat/frontend/art/...) plus Metadaten (Spieler, Jahr,
    Genre) aus /media/fat/frontend/meta/<System>.json

Neu in v0.4:
  - Gamepad-Unterstuetzung: D-Pad/Analogstick = Navigieren,
    A/Start = OK, B = zurueck, L/R = 15er-Spruenge,
    Guide/Home-Button = MiSTer-OSD, Select 3x hintereinander = Beenden
  - Hotplug: Pads koennen bei laufendem Frontend an-/abgesteckt werden

Neu in v0.3:
  - Schaltet MiSTer beim Start automatisch in den Konsolenmodus (F9),
    damit das MiSTer-Wallpaper unser Bild nicht mehr uebermalt;
    beim Beenden geht es per F12 zurueck ins normale Menue

Neu in v0.2:
  - Aufloesungsadaptives Layout: funktioniert von 1080p (HDMI)
    bis 640x480 (VGA/CRT) - Framebuffer-Groesse wird live gelesen
  - Kategorien werden automatisch aus allen /media/fat/_*-Ordnern
    erkannt (.rbf und .mra), inkl. deiner eigenen Ordner
  - Neue Kategorie "Scripts": startet /media/fat/Scripts/*.sh
    direkt auf der Konsole, danach uebernimmt das Frontend wieder
  - Neue Kategorie "System": oeffnet das echte MiSTer-OSD
    (fuer "Define joystick buttons", ini-Settings usw.) per
    F12-Injection; Rueckkehr ins Frontend mit F10
  - F12 im Frontend oeffnet das OSD jederzeit direkt

Steuerung:
  Pfeiltasten  Navigieren (links/rechts wechselt Spalte)
  Enter        Starten / Ausfuehren
  Bild auf/ab  15 Eintraege springen
  F12          MiSTer-OSD oeffnen (zurueck mit F10)
  ESC          Frontend beenden

Start auf dem MiSTer (per SSH oder als Startscript):
  python3 /media/fat/frontend/frontend.py
"""

import os, sys, mmap, struct, fcntl, time, re, glob, subprocess, traceback, zlib, json, random, math, signal, socket, threading, termios, csv, difflib, unicodedata, wave, pickle

# MODULARISIERUNG (Git-Branch 'modular-refactor'): eigenen Ordner
# explizit in sys.path aufnehmen, damit "import fe.xyz" zuverlaessig
# funktioniert - EGAL ob frontend.py direkt als Skript gestartet wird
# (dann macht Python das automatisch) ODER ueber importlib als Modul
# geladen wird (z.B. tools/regression_test.py) - dort passiert das
# NICHT automatisch, ohne diese Zeile wuerde "ModuleNotFoundError:
# No module named 'fe'" auftreten.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# EINZIGE QUELLE DER WAHRHEIT fuer die Versionsnummer liegt in
# fe/menu.py (nicht hier) - Vereinbarung, da mehrere Leute an derselben
# Codebasis arbeiten (siehe Nutzer-Vorgabe zur Versionierung). Muss mit
# dem Header-Kommentar oben, README, CHANGELOG und der VERSION-Datei
# (frontend/VERSION) UEBEREINSTIMMEN. Wird NUR bei einem ausdruecklich
# angewiesenen Release-Bump geaendert - niemals von sich aus
# hochgezaehlt, auch nicht bei Zwischenstaenden/Diagnose-Builds/
# Bugfix-Versuchen (die bekommen hoechstens einen Zusatz wie
# "4.2-test3", nie eine neue Nummer hier).
#
# BUGFIX (beim v4.4-Bump gefunden): FRONTEND_VERSION war bisher
# ZWEIMAL unabhaengig als Zeichenkette hinterlegt - hier UND in
# fe/menu.py - mit demselben Drift-Risiko wie zuvor schon bei den
# Scripts/-Kopien der Installationsskripte gefunden und behoben (ein
# Bump an nur einer der beiden Stellen faellt lange nicht auf). fe.menu
# wird bereits von frontend.py importiert (nicht umgekehrt) - ein
# Rueckimport haette einen Zirkelbezug erzeugt, deshalb liegt die
# kanonische Definition jetzt dort (siehe Import weiter unten
# zusammen mit system_items), hier bewusst KEIN eigener Import mehr,
# um die Reihenfolge/Lesbarkeit der bestehenden fe.menu-Importzeile
# nicht zu verdoppeln.

# NEUES FEATURE (Nutzerwunsch: "wenn es ein Update gibt, einmal eine
# Info anzeigen" - das eigentliche Herunterladen/Installieren bleibt
# bewusst manuell ueber Frontend_Install.sh, hier geht es NUR um die
# Benachrichtigung). Die VERSION-Datei liegt im Repo bereits neben
# frontend.py - ein Rohtext-Abruf dieser EINEN Datei via
# raw.githubusercontent.com reicht als Versionspruefung, kein API-
# Rate-Limit, keine JSON-Antwort noetig.

from fe.log import LOGFILE, LOG

from fe.single_instance import LOCKFILE, _pid_alive, acquire_single_instance, release_single_instance

# ----------------------------------------------------------------------------
# KONFIGURATION
# ----------------------------------------------------------------------------

BASE        = "/media/fat"
SCRIPTS_DIR = "/media/fat/Scripts"

# --- Stream-Overlay (optional, siehe stream_server.py) -----------------
STREAM_ENABLED_FILE = "/media/fat/frontend/stream_enabled"
STREAM_CONFIG_FILE  = "/media/fat/frontend/stream_config.json"
STREAM_PORT = 8080

try:
    from stream_server import StreamServer
except Exception:
    StreamServer = None
MGL_TMP     = "/tmp/frontend_launch.mgl"
GAMES_CACHE = "/media/fat/frontend/games_cache.pkl"
GAMES_CACHE_OLD_JSON = "/media/fat/frontend/games_cache.json"   # fuer die
        # einmalige Aufraeumung einer Cache-Datei aus der Zeit vor dem
        # Wechsel auf Pickle (siehe scan_games()) - wird nie neu
        # geschrieben, nur einmalig geloescht, falls noch vorhanden.
RECENT_FILE = "/media/fat/frontend/recently_played.json"
RECENT_MAX = 100   # kanonischer Wert in fe/game_state.py - siehe Import
                   # gleich darunter, der diese Zeile ueberschreibt;
                   # hier nur mitgefuehrt, damit beide Stellen nicht
                   # auseinanderlaufen (gleiches Drift-Risiko wie bei
                   # FRONTEND_VERSION, siehe fe/update_check.py).
FAVORITES_FILE = "/media/fat/frontend/favorites.json"
LAST_CORE_CHOICE_FILE = "/media/fat/frontend/last_core_choice.json"
PLAYTIME_FILE = "/media/fat/frontend/playtime.json"
from fe.game_state import (
    COMPLETED_FILE, FAVORITES_FILE, LAST_CORE_CHOICE_FILE, RECENT_FILE,
    RECENT_MARKER, RECENT_MAX, _bare_game_name, _folder_items,
    _load_completed_raw, _load_favorites_raw, find_continue_game, find_marked_recent_dir,
    is_favorite, load_favorites, load_last_core_choice, load_recent,
    record_core_choice, record_recent, toggle_completed, toggle_favorite,
)

# ----------------------------------------------------------------------------
from fe.retroachievements import (
    RA_ACHIEVEMENTS_CACHE_FILE, RA_ACHIEVEMENTS_CACHE_TTL, RA_API_URL,
    RA_CONFIG_FILE, RA_CONSOLE_MAP, RA_GAME_API_URL,
    RA_PROGRESS_SUMMARY_FILE, _load_ra_achievements_cache, _lookup_ra_candidate,
    _ra_console_matches, _ra_normalize_name, _refresh_ra_achievements_background,
    _save_ra_achievements_cache, build_ra_lookup, fetch_ra_game_achievements,
    fetch_ra_game_achievements_bounded, fetch_ra_game_achievements_cached, fetch_ra_progress,
    fetch_ra_progress_bounded, load_ra_config, lookup_ra_game_id,
    lookup_ra_progress, ra_enabled, toggle_ra_enabled,
)
from fe.playtime import (
    DIARY_FILE, DIARY_RETENTION_DAYS, FIRST_PLAYED_FILE, MILESTONE_DEFS,
    MONTH_NAMES_DE, MONTH_NAMES_EN, PLAYTIME_YEARLY_FILE, _current_date_str,
    _current_year, _format_diary_date, _format_seconds_short, _load_first_played,
    _prune_diary, _record_first_played, compute_milestone_progress, compute_year_review_stats,
    find_on_this_day_hint, get_milestones, load_diary, load_playtime,
    load_playtime_yearly, record_diary_entry, record_playtime, record_yearly_playtime,
)

# ----------------------------------------------------------------------------
# VERSTECKTE ERFOLGE - Name/Beschreibung bleibt verborgen ("???"), bis
# sie erreicht sind (siehe draw_milestones_screen()). Zwei Arten:
#
# EREIGNIS-basiert (night_owl, marathon): haengen von EINEM bestimmten
# Moment ab (wann ein Spiel gestartet wurde, wie lange eine einzelne
# Sitzung dauerte) - lassen sich NICHT aus dem aktuellen Datenstand neu
# berechnen, brauchen deshalb eine eigene, dauerhafte "freigeschaltet"-
# Markierung (siehe HIDDEN_UNLOCKED_FILE). Wird in run_core() geprueft.
#
# LIVE-berechnet (collector, completionist, legend): wie die normalen
# Meilensteine einfach aus dem aktuellen Datenstand abgeleitet, jedes
# Mal neu - keine eigene Speicherung noetig.
from fe.achievements import (
    ACHIEVEMENTS_SEEN_FILE, DAILY_SYSTEMS_FILE, DEV_ROOM_BONUS_CODE,
    DEV_ROOM_BONUS_ID, FRONTEND_LEVEL_MAX, HIDDEN_UNLOCKED_FILE,
    LAST_PLAYED_FILE, RAINBOW_CURSOR_SECONDS, SECRETS_FILE,
    SECRET_CODES, SECRET_CODE_MAXLEN, WEEKEND_TRACKER_FILE,
    _check_comeback, _check_versatile, _check_weekend_warrior,
    _ensure_achievements_seen_initialized, _load_achievements_seen, _load_hidden_unlocked,
    _load_secrets_unlocked, _ra_100pct_achieved, _save_achievements_seen,
    _unlock_hidden, _unlock_secret, check_hidden_session_achievements,
    check_new_achievements, check_secret_code, compute_frontend_level,
    compute_profile_stats, format_playtime, get_hidden_achievements,
    top_played_games,
)

MISTER_CMD  = "/dev/MiSTer_cmd"

from fe.hidraw import _find_keyboard_hidraws, _hid_report_has_exit_key

from fe.audio import (
    MUSIC_DIR, MUSIC_ENABLED_FILE, MUSIC_SOURCE_FILE, VOLUME_FILE,
    _load_volume, _save_volume, _mpg_scale, _regenerate_sfx,
    _apply_volume_async, MPG123_BIN, ACHIEVEMENT_SFX_SOURCE, SFX_DIR,
    SFX_ENABLED_FLAG_FILE, SFX_MIN_GAP, SFX_DEFS, SFX_CHIME_DEFS,
    play_sfx, sfx_enabled_flag, toggle_sfx, MusicPlayer, get_volume,
    _ensure_sfx_files,
)

BOOTANIM_DIR = "/media/fat/frontend/bootanim"
BOOTANIM_PLAYED_MARKER = "/tmp/frontend_bootanim_played"

# NEUES FEATURE (Nutzerwunsch: eigenes Logo beim Start zeigen, statt
# des bisherigen generischen D-Pad-Symbols - mit demselben Flacker-
# Effekt wie vorher). Liegt als vorbereitete .art-Datei bei (siehe
# frontend/boot_logo/), wird NUR gezeigt, wenn KEIN eigenes Boot-
# Animation-Verzeichnis (BOOTANIM_DIR) existiert - genau wie beim
# bisherigen D-Pad-Symbol auch. Per Menuepunkt (System -> Anzeige &
# Sound) abschaltbar - dann erscheint wieder das alte, neutrale
# D-Pad-Symbol statt des personalisierten Logos (fuer alle, die das
# nicht wollen, z.B. TheRealSutefan/Dennsen/Dfense mit eigenem Namen
# an der Sache).
from fe.settings import (
    ATTRACT_CHANGE_SECONDS, ATTRACT_DELAY_FILE, ATTRACT_DELAY_STEPS,
    ATTRACT_DISABLED_FLAG, ATTRACT_IDLE_SECONDS, COVER_SETTLE,
    CRT_MENU_BLOCK, CURATED_FLAG, DRAGEND_LOGO_DISABLED_FLAG,
    DRAGEND_LOGO_FILE, MISTER_INI, SETUP_WIZARD_DONE_FILE,
    _filter_node_curated, _node_has_any_meta, attract_enabled,
    crt_menu_active, curated_only_active, cycle_attract_delay,
    dragend_logo_enabled, filter_curated, format_attract_delay,
    load_attract_delay, mark_setup_wizard_done, save_attract_delay,
    setup_wizard_done, toggle_attract_mode, toggle_crt_menu,
    toggle_curated_only, toggle_dragend_logo, screen_mirror_enabled,
    toggle_screen_mirror, toggle_stream_overlay, system_bg_enabled,
    toggle_system_bg, fast_scroll_enabled, toggle_fast_scroll,
    FAST_SCROLL_WINDOW, pulse_effect_enabled, toggle_pulse_effect,
    CRT_CONFIRM_TIMEOUT, crt_pending_confirm, mark_crt_pending_confirm,
    clear_crt_pending_confirm, eq_effect_enabled, toggle_eq_effect,
    track_marquee_enabled, toggle_track_marquee,
)

# NEUES FEATURE (Nutzerwunsch: Rainwave-Internetradio als zweite
# Musikquelle neben den lokalen MP3s, uebernommen aus einem separat
# vorbereiteten, auf echter MiSTer-Hardware getesteten Vorschlag -
# siehe CHANGES_RAINWAVE.md). Eigenstaendiges stdlib-Modul
# (frontend/rainwave.py, neben frontend.py) - komplett optional, damit
# die MP3-Wiedergabe unveraendert weiterlaeuft, selbst falls die Datei
# beim Kopieren mal fehlen sollte (gleiches defensives Muster wie
# stream_server oben).
try:
    import rainwave
except Exception:
    rainwave = None
CORENAME    = "/tmp/CORENAME"

# Ordner, die bei der automatischen Kategorie-Suche uebersprungen werden
SKIP_DIRS = {"_Scripts"}

from fe.naming import (
    IGNORE_ROM_BASENAMES, JUNK_TAGS, NICE_NAMES, REGION_PRIORITY,
    _DISC, _JAPAN_ONLY, _TAGS, _is_japan_only,
    _is_junk, _region_rank, display_name, nice_name,
)

from fe.systems import GAME_SYSTEMS, OPTIONAL_GAME_SYSTEMS, system_display_name

import fe.paths
import mister_wot
mister_wot.configure(GAME_SYSTEMS, lambda: fe.paths.GAMES_BASES, LOG)
from mister_wot import (
    wot_mark_played, wot_normalize_title, wot_load_played,
)

from fe.ra_core import RA_CORES_DIR_ABS, RA_CORES_DIR_REL, RA_CORE_NAME_CANDIDATES, find_ra_core

# Overscan-Sicherheitsrand in Prozent pro Seite (CRTs beschneiden das Bild).
# Bei Bedarf anpassen: mehr, wenn weiterhin Raender fehlen; weniger auf LCD.
OVERSCAN_X = 7
OVERSCAN_Y = 5

# NEU (Nutzer-Rueckmeldung: "Frontend beenden"-Dialog ploppte nur kurz
# auf und verschwand wieder, ohne dass eine Auswahl moeglich war) -
# siehe self._confirm_dialog_opened_at/_confirm_dialog_toggle(): eine
# "ok"-Eingabe, die INNERHALB dieses Zeitfensters nach dem Oeffnen des
# Ja/Nein-Dialogs ankommt, wird bewusst ignoriert (nur neu gezeichnet,
# nicht als Bestaetigung gewertet) - verhindert, dass ein reflexartiges
# zweites OK (das den Dialog erst geoeffnet hat) ihn im selben Atemzug
# wieder mit der vorausgewaehlten "Nein"/"Spaeter"-Option schliesst,
# bevor der Nutzer ueberhaupt eine echte Chance hatte, zu reagieren.
# 350ms sind deutlich laenger als jede normale Doppel-Eingabe/Prellen,
# aber kurz genug, um bei einer bewusst schnellen zweiten Eingabe nicht
# selbst wie eine Verzoegerung/ein Bug zu wirken.
CONFIRM_DIALOG_IGNORE_OK_WINDOW = 0.35

# Farben als (R, G, B)
C_BG     = (16, 18, 24)
C_PANEL  = (28, 32, 44)
C_ACCENT = (66, 133, 244)
C_ACCENT2= (40, 70, 120)

# Pro-System-Akzentfarbe: Markierung/Rahmen faerben sich passend zum
# aktuellen System ein statt immer Standard-Blau zu zeigen. Kategorien
# ohne Systemkey (Scripts, System, Core-Ordner) behalten C_ACCENT.
SYSTEM_ACCENT = {
    "NES":     (210, 70, 70),
    "SNES":    (140, 120, 220),
    "Genesis": (60, 150, 255),
    "N64":     (70, 160, 100),
    "PSX":     (130, 140, 190),
    "GAMEBOY": (150, 180, 100),
    "GBC":     (230, 185, 60),
    "GBA":     (175, 120, 225),
    "SMS":     (230, 90, 90),
    "TGFX16":  (240, 150, 50),
    "MegaCD":  (90, 175, 205),
    "Saturn":  (200, 200, 215),
    "NEOGEO":  (220, 70, 70),
    "ARCADE":  (255, 185, 50),
    "SNES_ALTTP_TRACKER": (210, 175, 70),   # Gold, angelehnt an das Triforce-Logo
    "SMW_HACKS": (225, 100, 40),            # Mario-Rot/Orange, abgesetzt von SNES-Lila
}

from fe.seasonal import seasonal_decoration

# NEUES FEATURE (siehe ausfuehrliche Begruendung bei display_name() in
# fe/naming.py - dieselbe Ueberlegung): accent_for() ist ebenfalls eine
# reine Funktion, wird pro sichtbarer Zeile bei jedem Neuzeichnen erneut
# aufgerufen, obwohl sich der Systemschluessel einer Zeile so gut wie
# nie aendert. Eingaberaum hier besonders klein (nur die paar Dutzend
# bekannten Systemschluessel) - idealer Fall fuer einen Cache. WICHTIG:
# CURRENT_THEME_MONOCHROME kann sich zur Laufzeit aendern (Themenwechsel
# im Menue) - der Cache wird deshalb explizit dort geleert (siehe
# apply_theme()), sonst wuerde nach einem Themenwechsel die alte Farbe
# haengen bleiben.
_ACCENT_FOR_CACHE = {}

def accent_for(syskey):
    """Akzentfarbe fuer ein System - faellt auf den Standard zurueck,
    wenn kein syskey vorhanden ist (Scripts/System/Core-Ordner) oder
    das System nicht in SYSTEM_ACCENT gelistet ist.

    Im monochromen Theme (aktuell: Retro-Gruen) wird die bunte System-
    Farbe zu 70% Richtung Theme-Akzentfarbe abgemischt statt pur
    durchzuschlagen - auf einem echten monochromen Gruen-Bildschirm
    haette es ohnehin nie unterschiedliche Farbtoene gegeben, eine
    z.B. pure SNES-Lila-Markierung riss bisher komplett aus dem
    Phosphor-Look raus. Bewusst nicht 100% Theme-Farbe (0% System-
    Farbe) - ein leichter Farbstich bleibt erhalten, genug um
    Systeme im Zweifel noch unterscheiden zu koennen."""
    if syskey in _ACCENT_FOR_CACHE:
        return _ACCENT_FOR_CACHE[syskey]
    color = SYSTEM_ACCENT.get(syskey, C_ACCENT)
    if CURRENT_THEME_MONOCHROME and syskey is not None:
        mix = 0.7
        color = tuple(int(c * (1 - mix) + a * mix) for c, a in zip(color, C_ACCENT))
    _ACCENT_FOR_CACHE[syskey] = color
    return color
C_TEXT   = (220, 224, 232)
C_DIM    = (120, 126, 140)
C_TITLE  = (255, 255, 255)   # Logo/Systemname: weiss (Retro-Look)
# NEU (Nutzerwunsch: Hardcore/Softcore-Unterscheidung in der F6-Erfolgs-
# Vitrine): warmer Gold-/Amber-Ton, angelehnt an RAs eigene Farbgebung
# fuer Hardcore-Freischaltungen - hebt sich bewusst deutlich von der
# neutralen C_TEXT-Farbe (Softcore) und dem gedimmten C_DIM (noch nicht
# erreicht) ab.
C_RA_HARDCORE = (255, 195, 40)
CURRENT_THEME_MONOCHROME = False   # von apply_theme() gesetzt, siehe accent_for()

# ----------------------------------------------------------------------------
# THEMES/FARBSCHEMATA
#
# Die "Chrome"-Farben (Hintergrund, Text, Panel, Standard-Akzent) lassen
# sich umschalten - SYSTEM_ACCENT (pro-System-Farben) bleibt bewusst
# THEMA-UNABHAENGIG bestehen (eigene visuelle Sprache zur Unterscheidung
# der Systeme, kein Teil der "Chrome"). Technisch simpel gehalten: die
# globalen Variablen (C_BG, C_TEXT, ...) werden beim Wechseln einfach
# NEU BELEGT (siehe apply_theme()) - dadurch muss an den hunderten
# Stellen im Code, die diese Namen direkt verwenden, NICHTS geaendert
# werden.
THEME_FILE = "/media/fat/frontend/theme"

THEMES = {
    "dark": {   # Standard (unveraendertes Erscheinungsbild von vorher)
        "C_BG": (16, 18, 24), "C_PANEL": (28, 32, 44),
        "C_TEXT": (220, 224, 232), "C_DIM": (120, 126, 140),
        "C_TITLE": (255, 255, 255), "C_ACCENT": (66, 133, 244),
    },
    "light": {  # Hell-Modus
        "C_BG": (238, 240, 244), "C_PANEL": (218, 221, 228),
        "C_TEXT": (28, 30, 36), "C_DIM": (100, 104, 114),
        "C_TITLE": (10, 10, 14), "C_ACCENT": (20, 90, 210),
    },
    "green": {  # Retro-Gruen (CRT-Phosphor-Look)
        "C_BG": (6, 16, 9), "C_PANEL": (11, 28, 15),
        "C_TEXT": (150, 255, 165), "C_DIM": (60, 140, 80),
        "C_TITLE": (205, 255, 215), "C_ACCENT": (80, 255, 120),
        # NEU (Nutzer-Rueckmeldung anhand eines Screenshots: die pro-
        # System-Akzentfarbe - z.B. SNES-Lila - riss hier komplett aus
        # dem monochromen Phosphor-Look raus): "monochrome" = True
        # sorgt dafuer, dass accent_for() hier NICHT die bunte System-
        # Farbe direkt verwendet, sondern zum Theme-eigenen Gruenton
        # HIN abblendet (siehe accent_for()) - genau wie ein echter
        # monochromer Gruen-Bildschirm, auf dem es ohnehin nie
        # unterschiedliche Farbtoene gegeben haette. Andere Themes
        # (dark/light/secret_gold) sind bewusst NICHT monochrom
        # angelegt, dort bleibt die Systemfarbe unveraendert bunt.
        "monochrome": True,
    },
    "secret_gold": {   # Geheimes Theme (Nutzerwunsch: "Easter Egg
        # System") - Gold/Violett, angelehnt an klassische
        # Arcade-Automaten-Kunst statt an ein reales Spiel (Urheberrecht).
        # Nur ueber cycle_theme() erreichbar, wenn "secret_theme_1"
        # freigeschaltet ist (siehe _available_theme_order()) - taucht
        # sonst nicht in der normalen Durchschalt-Reihenfolge auf.
        "C_BG": (18, 8, 26), "C_PANEL": (38, 18, 50),
        "C_TEXT": (255, 224, 130), "C_DIM": (150, 110, 170),
        "C_TITLE": (255, 200, 60), "C_ACCENT": (255, 170, 30),
    },

    # NEU (Nutzerwunsch: "Secret-Sammlung" - ein eigenes Theme pro
    # klassischem Retro-System, siehe die zugehoerigen SECRET_CODES in
    # fe/achievements.py und SECRET_THEME_META weiter unten). Jedes nur
    # ueber cycle_theme() erreichbar, sobald der jeweilige Code gefunden
    # wurde (siehe _available_theme_order()) - taucht vorher nirgends
    # in der normalen Durchschalt-Reihenfolge auf, genau wie secret_gold
    # oben.
    "snes_16bit": {   # Batman Forever (SNES) - dunkles Violett/Magenta
        "C_BG": (24, 14, 36), "C_PANEL": (46, 26, 64),
        "C_TEXT": (230, 220, 240), "C_DIM": (150, 120, 170),
        "C_TITLE": (255, 255, 255), "C_ACCENT": (190, 60, 220),
    },
    "dmg_green": {   # Game Boy - klassisches LCD-Gruen, monochrom
        "C_BG": (15, 30, 15), "C_PANEL": (24, 44, 20),
        "C_TEXT": (155, 188, 15), "C_DIM": (90, 130, 60),
        "C_TITLE": (200, 220, 90), "C_ACCENT": (139, 172, 15),
        "monochrome": True,
    },
    "gbc_neon": {   # Game Boy Color - Cyan/Magenta-Neon
        "C_BG": (10, 8, 20), "C_PANEL": (24, 16, 40),
        "C_TEXT": (255, 255, 255), "C_DIM": (150, 150, 180),
        "C_TITLE": (0, 255, 220), "C_ACCENT": (255, 0, 180),
    },
    "n64_turbo": {   # N64 - Grau mit kraeftigem Rot-Akzent
        "C_BG": (20, 20, 24), "C_PANEL": (40, 40, 46),
        "C_TEXT": (230, 230, 235), "C_DIM": (140, 140, 150),
        "C_TITLE": (255, 255, 255), "C_ACCENT": (220, 60, 50),
    },
    "ps1_classic": {   # PS1 - Anthrazit mit PlayStation-Blau
        "C_BG": (14, 14, 18), "C_PANEL": (28, 28, 36),
        "C_TEXT": (220, 224, 232), "C_DIM": (120, 126, 140),
        "C_TITLE": (255, 255, 255), "C_ACCENT": (0, 60, 180),
    },
    "sega_sonic": {   # Mega Drive/Sonic - SEGA-Blau/Gelb
        "C_BG": (10, 10, 40), "C_PANEL": (20, 20, 70),
        "C_TEXT": (255, 255, 255), "C_DIM": (150, 160, 220),
        "C_TITLE": (255, 220, 0), "C_ACCENT": (0, 90, 200),
    },
    "sms_sonic": {   # Master System/Sonic Chaos - dunkles Blau
        "C_BG": (8, 8, 30), "C_PANEL": (18, 18, 60),
        "C_TEXT": (255, 255, 255), "C_DIM": (140, 150, 200),
        "C_TITLE": (255, 255, 255), "C_ACCENT": (30, 80, 220),
    },
    "gamegear_sonic": {   # Game Gear/Sonic Chaos - Handheld-LCD-Blau,
        # monochrom (wie DMG - eigener Handheld-Charakter)
        "C_BG": (8, 10, 30), "C_PANEL": (18, 22, 55),
        "C_TEXT": (220, 230, 255), "C_DIM": (110, 130, 180),
        "C_TITLE": (255, 255, 255), "C_ACCENT": (60, 140, 255),
        "monochrome": True,
    },
    "saturn_sonic": {   # Saturn/Sonic Jam - fast Schwarz mit Violett
        "C_BG": (10, 10, 10), "C_PANEL": (30, 26, 40),
        "C_TEXT": (230, 220, 255), "C_DIM": (130, 120, 160),
        "C_TITLE": (255, 255, 255), "C_ACCENT": (140, 90, 230),
    },
}
THEME_ORDER = ["dark", "light", "green"]

# NEU: Metadaten fuer die 9 neuen Secret-Themes, an EINER Stelle
# gebuendelt statt ueber mehrere if/elif-Ketten verteilt (secret_id ->
# Theme-Name, Unlock-Spruch fuer die Flourish-Anzeige, optionale
# Zusatzwirkung). _on_secret_triggered() und _available_theme_order()
# lesen beide von hier - ein neues Theme spaeter hinzuzufuegen heisst
# nur noch: ein THEMES-Eintrag, ein SECRET_CODES-Eintrag, ein
# SFX_CHIME_DEFS-Eintrag, zwei Uebersetzungen und EIN Eintrag hier.
SECRET_THEME_META = {
    "theme_snes":      {"theme": "snes_16bit",      "flourish": "flourish_snes"},
    "theme_gb":        {"theme": "dmg_green",        "flourish": "flourish_gb"},
    "theme_gbc":       {"theme": "gbc_neon",         "flourish": "flourish_gbc"},
    # N64: einziges Theme mit echtem Zusatzeffekt (Nutzerwunsch/
    # Recherche-Notiz: "koennte tatsaechlich den schnelleren
    # ROM-Listen-Scroll aktivieren") - schaltet beim allerersten
    # Freischalten den bestehenden "Schnelles Scrollen"-Schalter (siehe
    # fe/settings.py) mit ein, falls noch aus. Rein additiv: wer den
    # Schalter schon an hatte oder ihn danach wieder ausschaltet, wird
    # dadurch nicht bevormundet - siehe _on_secret_triggered().
    "theme_n64":       {"theme": "n64_turbo",        "flourish": "flourish_n64",
                        "enable_fast_scroll": True},
    "theme_ps1":       {"theme": "ps1_classic",      "flourish": "flourish_ps1"},
    "theme_megadrive": {"theme": "sega_sonic",       "flourish": "flourish_megadrive"},
    "theme_sms":       {"theme": "sms_sonic",        "flourish": "flourish_sms"},
    "theme_gamegear":  {"theme": "gamegear_sonic",   "flourish": "flourish_gamegear"},
    "theme_saturn":    {"theme": "saturn_sonic",     "flourish": "flourish_saturn"},
}


# BUGFIX (Nutzer-Rueckmeldung: "freigeschaltete Geheim-Themes sollten
# im Anzeige-Menue unter Farbschema auswaehlbar erscheinen"): die
# Anzeigenamen standen hier bisher DAUERHAFT auf "??? Geheim ???" -
# auch dann noch, wenn ein Theme laengst gefunden und AKTIV war. Das
# ist unproblemlos aufzuloesen: current_theme_name() liefert einen
# Geheim-Theme-Namen ueberhaupt nur dann, wenn er zuvor in THEME_FILE
# geschrieben wurde - und das passiert ausschliesslich ueber
# cycle_theme() (nur unter _available_theme_order(), also nur
# freigeschaltete Themes) oder _on_secret_triggered() (nur wenn der
# Code gerade gefunden wurde). Ein Geheim-Theme kann also gar nicht
# aktiv sein, ohne bereits gefunden zu sein - der echte Name kann
# hier also gefahrlos direkt gezeigt werden, sobald es aktiv ist,
# statt fuer immer geheimnisvoll zu bleiben.
THEME_NAMES_DE = {"dark": "Dunkel (Standard)", "light": "Hell",
                  "green": "Retro-Gruen", "secret_gold": "Gold (geheim)"}
THEME_NAMES_EN = {"dark": "Dark (default)", "light": "Light",
                  "green": "Retro Green", "secret_gold": "Gold (secret)"}
# Anzeigename je Geheim-Theme (siehe SECRET_THEME_META oben) - eine
# Stelle, die sowohl hier als auch in fe/menu.py's eigener, bewusst
# unabhaengiger Kopie (siehe dortiger Modul-Kommentar) gepflegt werden
# MUSS, wenn ein neues Geheim-Theme dazukommt.
SECRET_THEME_DISPLAY_NAMES = {
    "snes_16bit":      ("SNES (geheim)", "SNES (secret)"),
    "dmg_green":       ("Game Boy (geheim)", "Game Boy (secret)"),
    "gbc_neon":        ("Game Boy Color (geheim)", "Game Boy Color (secret)"),
    "n64_turbo":       ("N64 (geheim)", "N64 (secret)"),
    "ps1_classic":     ("PS1 (geheim)", "PS1 (secret)"),
    "sega_sonic":      ("Mega Drive (geheim)", "Mega Drive (secret)"),
    "sms_sonic":       ("Master System (geheim)", "Master System (secret)"),
    "gamegear_sonic":  ("Game Gear (geheim)", "Game Gear (secret)"),
    "saturn_sonic":    ("Saturn (geheim)", "Saturn (secret)"),
}
for _sm in SECRET_THEME_META.values():
    _de, _en = SECRET_THEME_DISPLAY_NAMES[_sm["theme"]]
    THEME_NAMES_DE[_sm["theme"]] = _de
    THEME_NAMES_EN[_sm["theme"]] = _en
del _sm, _de, _en

def _available_theme_order():
    """THEME_ORDER, erweitert um freigeschaltete Geheim-Themes - so
    bleiben sie in der normalen Durchschalt-Reihenfolge (cycle_theme())
    unsichtbar, bis der zugehoerige Geheimcode gefunden wurde."""
    order = list(THEME_ORDER)
    unlocked = _load_secrets_unlocked()
    if "secret_theme_1" in unlocked:
        order.append("secret_gold")
    for secret_id, meta in SECRET_THEME_META.items():
        if secret_id in unlocked:
            order.append(meta["theme"])
    return order

def current_theme_name():
    try:
        name = open(THEME_FILE).read().strip()
        if name in THEMES:
            return name
    except OSError:
        pass
    return "dark"

def apply_theme(name):
    """Aktiviert ein Farbschema - schreibt direkt in die gleichnamigen
    globalen Variablen, die im gesamten restlichen Code bereits
    verwendet werden (kein Umbau an anderer Stelle noetig).

    MODULARISIERUNG: fe.framebuffer.C_BG/C_TEXT (siehe dortiger Modul-
    Kommentar) werden hier zusaetzlich per modul-qualifiziertem
    Zugriff synchron gehalten - das ist eine normale Zuweisung auf das
    fe.framebuffer-Modul selbst, kein Neu-Binden einer importierten
    Kopie hier in frontend.py, wirkt also sofort auch dort."""
    global C_BG, C_PANEL, C_TEXT, C_DIM, C_TITLE, C_ACCENT, CURRENT_THEME_MONOCHROME
    theme = THEMES.get(name, THEMES["dark"])
    C_BG = theme["C_BG"]
    C_PANEL = theme["C_PANEL"]
    C_TEXT = theme["C_TEXT"]
    C_DIM = theme["C_DIM"]
    C_TITLE = theme["C_TITLE"]
    C_ACCENT = theme["C_ACCENT"]
    CURRENT_THEME_MONOCHROME = theme.get("monochrome", False)
    # NEU: siehe Kommentar bei _ACCENT_FOR_CACHE oben - C_ACCENT und
    # CURRENT_THEME_MONOCHROME aendern sich hier gerade, alte
    # zwischengespeicherte Farben waeren ab jetzt falsch.
    _ACCENT_FOR_CACHE.clear()
    import fe.framebuffer
    fe.framebuffer.C_BG = C_BG
    fe.framebuffer.C_TEXT = C_TEXT

def cycle_theme():
    """Zum naechsten Farbschema wechseln (der Reihe nach), speichert
    die Wahl UND wendet sie sofort an. Gibt den neuen Themennamen
    zurueck. Nutzt _available_theme_order() statt THEME_ORDER direkt,
    damit freigeschaltete Geheim-Themes automatisch mit durchlaufen."""
    cur = current_theme_name()
    order = _available_theme_order()
    idx = order.index(cur) if cur in order else 0
    new_name = order[(idx + 1) % len(order)]
    try:
        dirname = os.path.dirname(THEME_FILE)
        if dirname:
            os.makedirs(dirname, exist_ok=True)
        with open(THEME_FILE, "w") as f:
            f.write(new_name)
    except OSError:
        pass
    apply_theme(new_name)
    return new_name

apply_theme(current_theme_name())   # beim Laden des Moduls sofort anwenden

# ----------------------------------------------------------------------------
# FRAMEBUFFER (siehe fe/framebuffer.py - Zeichen-Grundfunktionen +
# 8x8-Bitmap-Font komplett ausgelagert)
# ----------------------------------------------------------------------------
from fe.framebuffer import FBDEV, Framebuffer

# ----------------------------------------------------------------------------
# EINGABE: Tastatur + Gamepads parallel, mit Hotplug und exklusivem Grab
# ----------------------------------------------------------------------------

import select
import threading
import urllib.request
import urllib.parse
import urllib.error

from fe.input import (
    ABS_HAT0X, ABS_HAT0Y, ABS_RZ, ABS_X, ABS_Y, ABS_Z,
    AXIS_L2, AXIS_R2, BTN_A, BTN_B, BTN_DPAD_DOWN, BTN_DPAD_LEFT,
    BTN_DPAD_RIGHT, BTN_DPAD_UP, BTN_MODE, BTN_SELECT, BTN_START, BTN_TL,
    BTN_TL2, BTN_TR, BTN_TR2, BTN_X, BTN_Y, DEFAULT_KEYMAP,
    Device, EV_ABS, EV_KEY, EV_SYN, InputManager, KEYMAP,
    KEYMAP_CUSTOM_FILE, KEY_BACKSPACE, KEY_DOWN, KEY_ENTER, KEY_ESC, KEY_F10,
    KEY_F11, KEY_F12, KEY_F6, KEY_F7, KEY_F8, KEY_F9,
    KEY_LEFT, KEY_RIGHT, KEY_SLASH, KEY_UP, KEY_Y, LETTER_KEYS,
    REPEAT_ACTIONS, REPEAT_DELAY, REPEAT_INTERVAL, scan_devices,
    SWAP_OK_BACK_FILE, swap_ok_back_enabled, save_swap_ok_back,
)

from fe.art import (
    decode_png, BadgeCache, ArtCache, BgCache, _art_path_in, _art_index,
    art_path, mra_meta, get_meta, ART, ART_BASE,
    ART_HD, BG_BASE, SYSART_BASE, META_BASE, BADGE_DIR,
    RA_BADGE_URL, BG, BADGES, _category_art_key,
)

# ----------------------------------------------------------------------------
# KATEGORIEN & AKTIONEN
# ----------------------------------------------------------------------------



from fe.scan import (
    GAMES_CACHE, GAMES_CACHE_OLD_JSON, NETWORK_WAIT_FILE, SCAN_LOGIC_VERSION,
    _count_tree_items, _dedupe_items, _empty_node, _games_signature,
    _has_network_mount, _merge_node, _node_count, _scan_folder_tree,
    _scan_games_disk, _sig_expects_usb, _wait_for_network_ready, _wait_for_usb_stable,
    _wrap_flat, network_wait_enabled, save_network_wait, scan_cores,
    scan_games,
)

from fe.launch import write_mgl, scan_scripts, current_core, launch_core, MGL_TMP

def _has_network():
    """Prueft, ob irgendein Netzwerk-Interface eine Adresse hat -
    ueber den klassischen 'UDP connect'-Trick: verbindet einen UDP-
    Socket zu einer beliebigen externen Adresse (verschickt dabei
    KEIN einziges Paket, UDP-connect() ist rein lokales Routing) und
    schaut, welche lokale Adresse das Betriebssystem dafuer waehlen
    wuerde. Funktioniert auch ohne echten Internetzugang, solange das
    lokale Netzwerk (WLAN/LAN) steht - genau das, wonach gefragt war,
    nicht ob das Internet erreichbar ist."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return bool(ip) and not ip.startswith("127.")
    except OSError:
        return False

from fe.update_check import (
    UPDATE_CHECK_DISABLED_FLAG_FILE, UPDATE_CHECK_STATE_FILE, UPDATE_CHECK_URL, _parse_version,
    _version_newer, check_for_update, load_update_state, save_update_state,
    toggle_update_check, update_check_enabled, check_for_build_update,
)
from fe.timekeeping import (
    NTP_EPOCH_OFFSET, NTP_SERVER, TIMEZONE_OFFSET_FILE, TIMEZONE_STEPS,
    _apply_ntp_result, _ntp_time, cycle_timezone_offset, format_timezone_offset,
    get_ntp_sync_ok, load_timezone_offset, save_timezone_offset, sync_system_clock_from_ntp,
)

# LANGUAGE / TRANSLATIONS
# ----------------------------------------------------------------------------

from fe.translations import TRANSLATIONS, t, set_language, current_lang


from fe.menu import system_items, FRONTEND_VERSION
from fe.search import jump_to_substring, jump_to_letter
# FRONTEND
# ----------------------------------------------------------------------------

class Frontend:
    """
    Seit v1.8 zweiseitig:
      Seite 0 - Hauptmenue: nur die Kategorien (Systeme, Arcade, Scripts,
                System) als grosse, gut lesbare Liste ueber die volle Breite.
      Seite 1 - Kategorie-Ansicht: Liste links, bei Spiele-/Arcade-Systemen
                daneben eine eigene, breite Boxart+Info-Spalte (statt eines
                kleinen ueberlappenden Blocks unten rechts wie in v1.7).
    """

    def __init__(self):
        self.fb = Framebuffer()
        self.inp = InputManager()
        # WICHTIG: Erst auf unseren eigenen Bildschirm umschalten (F9),
        # DANACH erst den (potenziell langsamen) Scan starten - vorher
        # passierte das in umgekehrter Reihenfolge (in run(), also nach
        # __init__ komplett durchgelaufen war). Wenn build_categories()
        # aus irgendeinem Grund laenger braucht (z.B. ein USB-Laufwerk,
        # das nach laengerem Ausschalten erst noch verzoegert bereit
        # wird, oder ein tatsaechlicher Neu-Scan), blieb der Bildschirm
        # bis dahin im MiSTer-OSD haengen - Musik lief bereits (die
        # startet noch frueher), das eigentliche Frontend blieb aber
        # unsichtbar. Jetzt sieht man sofort unseren Bildschirm samt
        # Lade-Fortschrittsbalken (siehe _draw_scan_progress()), auch
        # wenn der Scan mal laenger dauert.
        self.enter_console_mode()
        self.set_cursor_blink(False)
        self.inp.grab(True)
        self.fb.clear((16, 18, 24))
        self.fb.flip()
        self.music = MusicPlayer()

        # DIAGNOSE (Nutzer-Rueckmeldung: "habe nach dem Update immer
        # noch das alte Zufalls-Zock-Bild") - inzwischen als Ursache
        # identifiziert und behoben (siehe Korrektur-Kommentar in
        # _draw_wot_title()): das Bild wurde bisher an der FALSCHEN
        # Stelle ausgetauscht (ein eigens dafuer angelegter, aber
        # falscher wot_logo/-Ordner) - die tatsaechlich angezeigte
        # Datei (SYSART_BASE/WOT.art, ueber den bereits VORHER
        # bestehenden Sysart-Mechanismus) wurde dabei nie angefasst.
        # Trotzdem bei jedem Start geloggt, damit ein kuenftiger
        # Austausch immer nachvollziehbar bleibt.
        try:
            _wot_st = os.stat(os.path.join(SYSART_BASE, "WOT.art"))
            LOG("SYSART WOT.art: %d Bytes, zuletzt geaendert %s" % (
                _wot_st.st_size,
                time.strftime("%Y-%m-%d %H:%M:%S",
                               time.localtime(_wot_st.st_mtime))))
        except OSError as _e:
            LOG("SYSART WOT.art: nicht vorhanden (%s) - Platzhalter in der "
                "Boxart-Vorschau" % _e)

        # BUGFIX (KRITISCH - Nutzer-Rueckmeldung von echter Hardware:
        # Frontend startet, Bildschirm bleibt schwarz, Absturz laut Log
        # in build_ra_hunter_category(): "'Frontend' object has no
        # attribute '_ra_lookup'"): dieser komplette RA-Setup-Block
        # stand bisher WEITER UNTEN in __init__(), NACH dem Aufruf von
        # self.build_categories() - build_categories() ruft aber intern
        # build_ra_hunter_category() auf, die self._ra_lookup bereits
        # braucht. Reihenfolge-Fehler: das Attribut existierte zum
        # Zeitpunkt des Zugriffs schlicht noch nicht.
        #
        # Warum meine eigenen Regressionstests das nie gefangen haben:
        # jeder einzelne Test in dieser Datei setzt "f._ra_lookup = {}"
        # als Standard-Testaufbau von Hand, BEVOR draw()/build_categories()
        # aufgerufen wird - das hat genau diesen Reihenfolge-Fehler die
        # ganze Zeit ueberdeckt, da der echte Frontend()-Konstruktor nie
        # end-to-end durchlaufen wurde. Erst der echte Absturz-Log von
        # echter Hardware hat den tatsaechlichen Fehler gezeigt (siehe
        # Vereinbarung "mehr Hardware-Gegenprobe als Selbst-
        # Regressionstests").
        #
        # RetroAchievements - komplett unsichtbar/kostenlos, solange
        # nicht eingerichtet (ra_enabled() prueft nur eine Datei,
        # sofortiger Rueckweg). Nur FALLS eingerichtet, zeitlich
        # begrenzter Abruf (siehe fetch_ra_progress_bounded()) - blockiert
        # den Start dadurch nie unkontrolliert lange, selbst wenn RA
        # gerade langsam/nicht erreichbar ist.
        self._ra_lookup = {}
        self._ra_fetch_ok = False   # eigenstaendig von "hat Treffer" - auch
                                    # eine leere, aber ERFOLGREICH abgerufene
                                    # Liste zaehlt als Erfolg. Grundlage fuer
                                    # den Neuversuch in _maybe_retry_ra().
        self._ra_retry_next = 0.0
        self._ra_retry_count = 0
        # BUGFIX (Nutzer-Rueckmeldung: "RA-Erfolgsjaeger erscheint manchmal
        # gar nicht, taucht dann irgendwann ploetzlich doch auf"): siehe
        # _maybe_rebuild_ra_categories() weiter unten fuer die volle
        # Erklaerung - kurz gesagt wurde self.cats bisher nur in sehr
        # wenigen, teils zufaelligen Situationen neu aufgebaut, nachdem
        # frische RA-Fortschrittsdaten im Hintergrund eintrafen. Dieses
        # Flag wird gesetzt, sobald neue Daten da sind, aber die
        # Kategorienliste noch nicht entsprechend aktualisiert wurde.
        self._ra_categories_dirty = False

        # BUGFIX (Nutzer-Rueckmeldung: Uhrzeit war bei einem Nutzer
        # trotz korrekt eingestelltem Zeitzonen-Versatz falsch): der
        # bisherige Neuversuch-Mechanismus fuer eine beim Start noch
        # fehlgeschlagene NTP-Synchronisierung lief NUR ueber
        # _maybe_retry_ra() - und der ist an ra_enabled() gekoppelt.
        # Nutzer OHNE eingerichtetes RetroAchievements hatten dadurch
        # ueberhaupt keinen Wiederholungsmechanismus: schlug der
        # allererste, nicht-blockierende Versuch beim Programmstart
        # fehl (z.B. weil das Netzwerk in diesem Moment noch nicht
        # bereit war), blieb die Uhr fuer die komplette Sitzung falsch.
        # Eigenstaendige Zustandsvariablen fuer einen von RA
        # unabhaengigen Neuversuch, siehe _maybe_retry_clock().
        self._clock_retry_next = 0.0
        self._clock_retry_count = 0
        if ra_enabled():
            ra_data = fetch_ra_progress_bounded(timeout=3.0)
            if ra_data is not None:
                self._ra_lookup = build_ra_lookup(ra_data)
                self._ra_fetch_ok = True
            elif not get_ntp_sync_ok():
                # Wahrscheinlichste Erklaerung fuer einen fehlgeschlagenen
                # Abruf direkt beim Start: die Systemuhr war noch falsch
                # (MiSTer hat keine batteriegepufferte Uhr), wodurch die
                # HTTPS-Zertifikatspruefung fehlschlaegt - unabhaengig
                # davon, ob der RA-Server eigentlich erreichbar waere.
                # Neuversuch, sobald die Zeit sich (per _maybe_retry_ra())
                # doch noch synchronisiert.
                self._ra_retry_next = time.monotonic() + 30.0
        # PERFORMANCE (Nutzerwunsch: "mehr Performance rausholen", darf
        # dabei nichts kaputt machen): der RA-Fortschritts-Abruf
        # blockierte bisher SYNCHRON genau hier bis zu 3,5 Sekunden
        # (siehe fetch_ra_progress_bounded()s eigener join()-Timeout,
        # timeout=3.0 + 0.5 Sicherheitsspanne) - der Bildschirm zeigte
        # in der Zeit nur den leeren dunklen Screen von oben, noch
        # bevor ueberhaupt build_categories() mit dem eigentlichen
        # Lade-Fortschrittsbalken lief.
        #
        # Jetzt genau nach demselben, bereits bewaehrten Muster wie
        # der bestehende _maybe_retry_ra() (siehe dort) ein Hintergrund-
        # Thread: self.build_categories() unten laeuft sofort weiter,
        # self._ra_lookup bleibt fuer diesen allerersten Moment leer -
        # build_ra_hunter_category() liefert dafuer sicher None (siehe
        # dort), also KEIN Absturz, die RA-Erfolgsjaeger-Kategorie
        # taucht in diesem Fall schlicht noch nicht auf. Sobald die
        # Daten eintreffen, uebernimmt sie _maybe_apply_pending_ra_data()
        # (aus draw() periodisch geprueft, wie _maybe_retry_ra() selbst) -
        # baut die Kategorienliste aber bewusst NUR dann neu auf, wenn
        # der Nutzer seit dem Start noch GAR NICHT navigiert hat, um
        # self.cat_i/self.page niemals unter dem Nutzer wegzuziehen
        # (siehe dortiger Kommentar - "es darf nichts kaputt gehen"
        # hat hier Vorrang vor "RA-Kategorie garantiert sofort da").
        self._ra_pending_result = None
        if ra_enabled():
            # _ra_retry_next hochsetzen, BEVOR der Hintergrund-Thread
            # gestartet wird - verhindert, dass _maybe_retry_ra() (das
            # unabhaengig davon periodisch aus draw() geprueft wird)
            # sofort einen ZWEITEN, ueberlappenden Abruf lostritt, noch
            # bevor der erste ueberhaupt eine Chance hatte zu antworten.
            self._ra_retry_next = time.monotonic() + 4.0

            def _initial_ra_fetch():
                ra_data = fetch_ra_progress_bounded(timeout=3.0)
                if ra_data is not None:
                    self._ra_pending_result = (build_ra_lookup(ra_data), True)
                else:
                    self._ra_pending_result = (None, False)
                    if not get_ntp_sync_ok():
                        # Wahrscheinlichste Erklaerung fuer einen
                        # fehlgeschlagenen Abruf direkt beim Start: die
                        # Systemuhr war noch falsch (MiSTer hat keine
                        # batteriegepufferte Uhr), wodurch die HTTPS-
                        # Zertifikatspruefung fehlschlaegt - unabhaengig
                        # davon, ob der RA-Server eigentlich erreichbar
                        # waere. Neuversuch, sobald die Zeit sich (per
                        # _maybe_retry_ra()) doch noch synchronisiert.
                        self._ra_retry_next = time.monotonic() + 30.0
            threading.Thread(target=_initial_ra_fetch, daemon=True).start()

        self.build_categories()

        def _prewarm_one_cat_art(name, syskey):
            """Waermt die Sysart-Datei fuer GENAU eine Kategorie vor -
            derselbe Cache-Schluessel (Pfad + Box-Groesse), den
            _draw_cat_artbox() beim tatsaechlichen Zeichnen anfordert
            (siehe ArtCache.get_scaled() in fe/art.py). Eigene kleine
            Hilfsfunktion, damit sie SOWOHL synchron (fuer die zuerst
            sichtbare Kategorie, siehe direkt unten) ALS AUCH aus dem
            Hintergrund-Thread (fuer alle uebrigen Kategorien, siehe
            _prewarm_art_dirs()) genutzt werden kann, ohne die
            Box-Groessen-Berechnung zu duplizieren."""
            try:
                art_key = _category_art_key(name, syskey)
                if not art_key:
                    return
                L = self.layout_cats()
                s, art_w, y0, oy = L["s"], L["art_w"], L["y0"], L["oy"]
                y_max = self.fb.height - oy - 20 * s
                box_h = max(20, y_max - y0)
                pad = 6 * s
                ART.get_scaled(os.path.join(SYSART_BASE, "%s.art" % art_key),
                               art_w - 2 * pad, box_h)
            except Exception:
                pass   # Vorwaermen darf den Start nie zum Absturz bringen

        # BUGFIX/PERFORMANCE (Nutzer-Rueckmeldung: "das muss unter HDMI
        # insgesamt fluessiger laufen" - per DRAGEND_PROFILE auf echter
        # Hardware nachgemessen: "PERF draw_page_cats: 863 ms", davon
        # "THUMB_CACHE Treffer: 511.6ms (CONTINUE.art)"): ein erster
        # Versuch, die Sysart-Datei nur im (unten stehenden) Hintergrund-
        # Thread vorzuwaermen, brachte auf echter Hardware bei einer
        # ZWEITEN Messung nur eine kleine Verbesserung (863ms -> 755ms),
        # keine wirkliche Behebung - der Haupt-Thread erreicht seinen
        # allerersten draw()-Aufruf (der genau diese Datei braucht) auf
        # echter Hardware oft SCHNELLER, als der Hintergrund-Thread zur
        # Datei kommt. Ein Hintergrund-Thread MACHT einen Wettlauf nur
        # wahrscheinlicher, gewinnt ihn aber nicht garantiert.
        #
        # Fix: fuer GENAU die Kategorie, die beim Start als erste
        # sichtbar ist (self.cats[0], self.cat_i startet weiter unten
        # bei 0), wird die Sysart-Datei jetzt SYNCHRON hier vorgewaermt,
        # bevor ueberhaupt ein erster draw() moeglich ist - kein
        # Wettlauf mehr, garantiert warm. Kostet einmalig denselben
        # ~400-500ms-Lesevorgang wie vorher, aber jetzt WAEHREND der
        # ohnehin sichtbaren Boot-Animation/Ladephase weiter unten in
        # run(), nicht mehr als eigener, ueberraschender Ruckler,
        # NACHDEM das Menue schon fertig aussehen sollte. Alle UEBRIGEN
        # Kategorien (fuer den Fall, dass der Nutzer sofort in der
        # Kategorienliste weiterscrollt) bleiben beim bisherigen,
        # asynchronen Vorwaermen im Hintergrund-Thread unten - dort ist
        # ein verlorener Wettlauf unkritisch, da fuer diese der Nutzer
        # ohnehin erst noch aktiv navigieren muss.
        if self.cats:
            _first_name, _first_node, _first_syskey = self.cats[0]
            _prewarm_one_cat_art(_first_name, _first_syskey)

        # NEU (Nutzerwunsch: "beim Scrollen fuehlt es sich laghaft an" -
        # echtes Profiling auf echter Hardware fand einen viel groesseren
        # Verdaechtigen als das eigentliche Scrollen: der ALLERERSTE
        # Eintritt in ein System pro Sitzung kostete teils ueber 1
        # SEKUNDE (PERF cover: 1077 ms, 1057 ms) - zurueckverfolgt auf
        # _art_index() -> os.listdir() ueber den kompletten Cover-Ordner
        # des Systems. Ein zweiter Testlauf (neuer Prozess, derselbe
        # Ordner) brauchte dafuer nur noch ~20ms - kein Python-Problem,
        # sondern ein KALTES Verzeichnis auf der SD-Karte: der erste
        # Zugriff ist langsam, das Betriebssystem haelt die
        # Verzeichniseintraege danach automatisch im eigenen
        # Speicher-Cache vor.
        #
        # Fix nach demselben, bereits bewaehrten Muster wie der RA-
        # Vorabruf oben: ein Hintergrund-Thread liest gleich beim Start
        # (parallel, ohne die Oberflaeche zu blockieren) einmal alle
        # Cover-Ordner durch - wenn der Nutzer tatsaechlich in ein
        # System wechselt, ist das Verzeichnis dann schon "warm",
        # unabhaengig davon, ob das ueber unseren eigenen Index-Cache
        # oder den Cache des Betriebssystems passiert. Waermt (siehe
        # Kommentar oben) jetzt zusaetzlich die Sysart-Bilder der
        # UEBRIGEN Kategorien vor (alles ausser self.cats[0], das ist
        # ja schon synchron oben erledigt) - hier ist ein Ruecksfall auf
        # den langsamen Erstzugriff unkritisch, da der Nutzer dafuer
        # erst aktiv navigieren muesste.
        def _prewarm_art_dirs():
            seen_keys = set()
            for _name, _node, _syskey in self.cats:
                _art_key = _category_art_key(_name, _syskey)
                if not _art_key or _art_key in seen_keys:
                    continue
                seen_keys.add(_art_key)
                _prewarm_one_cat_art(_name, _syskey)
            for _name, _node, _syskey in self.cats:
                if _syskey:
                    _art_index(ART_BASE, _syskey)
                    _art_index(ART_HD, _syskey)
        threading.Thread(target=_prewarm_art_dirs, daemon=True).start()

        self.page = 0              # 0 = Kategorien-Menue, 1 = Kategorie-Ansicht
        self.cat_i = 0
        self.cat_scroll = 0
        self.item_i = self.scroll = 0
        # Wie tief man gerade in die Ordnerstruktur der aktuellen
        # Kategorie navigiert ist (Liste von Ordnernamen, leer = auf
        # der obersten Ebene). Wird beim Wechsel der Kategorie und
        # beim Verlassen zurueck zu Seite 0 geleert.
        self.nav_path = []
        self._nav_position_stack = []   # merkt Position je Ordnerebene fuer "Zurueck"

        # Netzwerkstatus fuer die Anzeige unten rechts im Hauptmenue -
        # mit kurzer Zwischenspeicherung (alle paar Sekunden neu
        # geprueft), damit auch bei sehr haeufigem Neuzeichnen (CRT
        # bis 100x/Sekunde) nicht bei jedem einzelnen Bild ein
        # Systemaufruf noetig ist, obwohl die Pruefung selbst schon
        # sehr guenstig ist (kein echter Netzwerkverkehr, <2ms).
        self._net_status = False
        self._net_check_next = 0.0

        # Sicherheitsnetz fuer NAS/CIFS-Nutzer, siehe
        # _maybe_rescan_for_late_mount() - ergaenzt (nicht ersetzt) die
        # optionale, blockierende "beim Start warten"-Option weiter
        # unten in main().
        self._late_mount_rescan_pending = False
        self._late_mount_rescan_done = False
        self._late_mount_check_next = 0.0
        self._late_mount_deadline = time.monotonic() + 300.0   # nach 5 Min. aufgeben (nur Phase 1)

        # Attract-Modus-Einstellung ebenfalls zwischengespeichert (siehe
        # _attract_enabled_cached()) - attract_enabled() wird bei JEDEM
        # Leerlauf-Durchlauf abgefragt (bis zu 12x/Sekunde), ohne Cache
        # waere das eine unnoetig haeufige Datei-Existenzpruefung.
        self._attract_enabled_cache = True
        self._attract_enabled_check_next = 0.0

        # Gleiches Caching-Muster fuer die neue, einstellbare Attract-
        # Verzoegerung (siehe cycle_attract_delay()) - genauso haeufig
        # abgefragt wie attract_enabled(), braucht denselben Schutz vor
        # zu haeufigen Datei-Lesevorgaengen.
        self._attract_delay_cache = ATTRACT_IDLE_SECONDS
        self._attract_delay_check_next = 0.0

        # Favoriten-Namen im Speicher gehalten (Set fuer O(1)-Abfrage
        # beim Zeichnen) - NUR bei tatsaechlichen Aenderungen ueber
        # toggle_favorite() aktualisiert, nie durch erneutes Einlesen
        # der Datei bei jedem Neuzeichnen (das waere bei bis zu
        # 100 Bildern/Sekunde auf CRT ein spuerbares Performance-
        # Problem - genau das haben wir an anderer Stelle in diesem
        # Projekt schon mehrfach gefunden und behoben).
        self._favorites_set = set(
            e.get("label") for e in _load_favorites_raw() if "label" in e)

        # Durchgespielt-Status ebenfalls im Speicher gehalten - gleicher
        # Grund wie beim Favoriten-Cache.
        self._completed_set = _load_completed_raw()

        # Spielzeiten ebenfalls im Speicher gehalten - gleicher Grund
        # wie beim Favoriten-Cache (keine Datei-Lesevorgaenge bei jedem
        # Neuzeichnen). Wird nach jedem run_core()-Aufruf aktualisiert,
        # damit die gerade gespielte Zeit sofort sichtbar wird.
        self._playtime_cache = load_playtime()

        # BUGFIX (Nutzer-Rueckmeldung: Erfolgs-Pop-up blieb beim ersten
        # tatsaechlich neu erreichten Erfolg aus): die "bereits gezeigt"-
        # Baseline fuer Erfolgs-Pop-ups muss VOR jeder moeglichen
        # Nutzeraktion feststehen, nicht erst beim ersten tatsaechlichen
        # Ereignis (siehe _ensure_achievements_seen_initialized() fuer
        # die volle Begruendung). Tut nichts, wenn die Datei schon
        # existiert (Normalfall nach dem ersten Start).
        _ensure_achievements_seen_initialized()

        # Geheimcode-Puffer (siehe check_secret_
        # code()) - reine Liste, kein deque noetig fuer die paar
        # Eintraege. Wird in run() nach jeder Aktion befuellt/geprueft.
        self._secret_buffer = []

        # Attract-Modus (Bildschirmschoner): blaettert nach einer
        # Weile ohne Eingabe von selbst durch zufaellige Spiele mit
        # Boxart - siehe next_action()/draw_attract().
        self.attract_mode = False
        self._last_input_time = time.monotonic()
        self._settled_redrawn = True   # Cover-Nachladen erst nach Bewegung
        # BUGFIX (Nutzer-Rueckmeldung: "ich hatte einen Erfolg, z.B.
        # Entdecker 5 verschiedene Systeme, aber es kam kein Popup und
        # kein Ton"): gefunden ueber die vom Nutzer selbst geaeusserte
        # Vermutung, die Songtitel-Laufschrift koennte damit zu tun
        # haben - bestaetigt richtig, nur an anderer Stelle als gedacht.
        # draw(message=...) und _draw_dynamic_track_marquee() (Seite 1)
        # zeichnen beide an EXAKT derselben Stelle (footer_y) - die
        # Laufschrift kennt aber keine gerade angezeigte Meldung und
        # ueberschreibt sie beim naechsten faelligen Tick (bis zu
        # 12.5x/Sekunde) einfach wieder mit dem Songtitel, oft
        # innerhalb von unter 100ms - die Meldung war dann de facto nie
        # wahrnehmbar, obwohl draw() sie korrekt gezeichnet hatte.
        # Schutzfenster: solange time.monotonic() < diesem Zeitpunkt,
        # verzichtet _draw_dynamic_track_marquee() bewusst auf ihren
        # eigenen Tick, statt die Meldung zu riskieren.
        self._popup_message_until = 0.0
        # NEU: siehe Kommentar bei layout_items() - Cache-Dict, nie
        # groesser als 2 Eintraege in der Praxis (has_art: True/False,
        # Aufloesung fest fuer die Sitzung), kein Verdraengungslimit
        # noetig.
        self._layout_items_cache = {}
        # NEUES FEATURE (Nutzerwunsch: "sollte nach dem Logo mittig als
        # Infobox fuer ein paar Sekunden erscheinen" - fuer wichtige,
        # eigenstaendige Ankuendigungen wie "neues Update verfuegbar",
        # die mehr Aufmerksamkeit verdienen als eine kurze Bestaetigung
        # wie "Favorit hinzugefuegt" in der Fusszeile): separater
        # Zustand von self._popup_message_until - komplett eigene
        # Anzeigeform (siehe _draw_prominent_message()), kein Konflikt
        # mit dem bestehenden Fusszeilen-Mechanismus.
        self._prominent_message = None
        self._prominent_message_until = 0.0
        # NEU (Phase 2, Nutzerwunsch "Vorab-Laden nach Scrollrichtung"):
        # merkt sich, ob zuletzt nach unten (1) oder oben (-1) navigiert
        # wurde - _prefetch_neighbor_covers() bevorzugt beim Vorab-Laden
        # die Richtung, in die man vermutlich weiterscrollt. Vorgabe 1
        # (runter) - beim allerersten Aufruf noch keine echte Richtung
        # bekannt, runter ist die haeufigere erste Bewegung.
        self._last_scroll_dir = 1
        self._attract_game = None
        self._attract_change_next = 0.0
        self._attract_pool = None   # zwischengespeicherte flache Spieleliste
        # Boot-Ueberwachung (Diagnose fuer das Soft-Reboot-Problem: manchmal
        # landet man nach einem Neustart im MiSTer-OSD statt im Frontend). In
        # den ersten Sekunden nach dem Start kann der noch hochfahrende
        # MiSTer die Anzeige zurueckholen (Wallpaper ueber unserem
        # Framebuffer). Wir protokollieren dazu die aktive VT + CORENAME, um
        # ein Timing-Rennen sichtbar zu machen.
        self._boot_time = time.monotonic()
        self._last_vt_check = 0.0
        self._last_bootstate = None
        self._last_snapshot = 0.0

        # Optionaler Stream-Overlay-Server (nur wenn Freigabe-Datei da ist)
        self.stream = None
        self._stream_sig = None
        if StreamServer and os.path.exists(STREAM_ENABLED_FILE):
            try:
                self.stream = StreamServer(ART_BASE, port=STREAM_PORT,
                                           config_path=STREAM_CONFIG_FILE,
                                           art_hd=ART_HD,
                                           log=LOG)
                if not self.stream.start():
                    self.stream = None
            except Exception as e:
                LOG("Stream-Server-Start fehlgeschlagen: %s" % e)
                self.stream = None

        # Bildschirmspiegel (Nutzerwunsch: "CRT und HDMI koennen nicht
        # gleichzeitig laufen - waere es machbar, den Inhalt trotzdem
        # per Stream-Overlay sichtbar zu machen? Und unter System
        # an/aus schaltbar machen?") - eigener Hintergrund-Thread, NUR
        # gestartet wenn sowohl der Stream-Server laeuft ALS AUCH die
        # eigene Freigabe-Datei existiert (siehe screen_mirror_enabled()
        # in fe/settings.py). Setzt technisch auf dem Stream-Server auf
        # (publish_screen() dort), braucht ihn deshalb als Voraus-
        # setzung - eigener Schalter, da nicht jeder OBS-Overlay-Nutzer
        # auch den Bildschirm spiegeln moechte.
        if self.stream is not None and screen_mirror_enabled():
            threading.Thread(target=self._screen_mirror_loop,
                             daemon=True).start()
        self.mq_off = 0            # Laufschrift-Versatz (Zeichen)
        self.mq_pause = 0          # Pausen-Ticks an den Enden
        self._mq_tick_next = 0.0   # Zeitbremse fuer marquee_tick() (Bugfix)
        # Laufschrift fuer den aktuell spielenden Songtitel - eigener,
        # unabhaengiger Zustand, weil sie an zwei verschiedenen Stellen
        # (neben dem Logo UND im Boxart-Block) gleichzeitig laufen kann.
        self.track_mq_off = 0
        self.track_mq_pause = 0
        self._track_mq_name = None
        self._track_tick_next = 0.0
        # Pulsierende Markierung: bewusst LANGSAM (mehrere Sekunden pro
        # Zyklus) und selten aktualisiert (~1x/Sekunde), um die
        # Zeichenhaeufigkeit nicht spuerbar zu erhoehen - frueh in
        # diesem Projekt gab es eine lange Bildschirmriss-Geschichte,
        # die u.a. durch haeufige komplette Neuzeichnungen entstand.
        self._pulse_tick_next = 0.0
        self._pulse_t0 = time.monotonic()
        # Equalizer-Balken: eigener, etwas schnellerer Takt als das
        # Pulsieren (0.35s statt 0.9s) fuer fluessigere Bewegung, aber
        # bewusst deutlich langsamer als die Laufschrift (0.18s) - ein
        # Kompromiss, da haeufigeres Neuzeichnen auf HDMI spuerbar mehr
        # Rechenzeit kostet (siehe Performance-Hinweis in next_action()).
        self._eq_tick_next = 0.0
        # Seit v1.11: Seitensprung-Groesse (links/rechts) = sichtbare
        # Zeilenzahl der jeweiligen Liste - wird beim Zeichnen aktuell
        # gehalten, damit der Sprung immer genau einen Bildschirm
        # weiterspringt, egal welche Aufloesung/Layout gerade aktiv ist.
        self.cats_visible = 5
        self.items_visible = 5
        # Beenden-Bestaetigung (ESC/B im Hauptmenue)
        self.confirm_quit = False
        self.confirm_choice = 1    # 0 = Ja, 1 = Nein (Standard)
        # NEU (Nutzer-Rueckmeldung: "das Fenster ploppt nur kurz auf und
        # verschwindet wieder, ich kann nicht mal was auswaehlen" -
        # zusaetzlich zum echten frontend.log, das eine Folge von reinen
        # "ok"-Eingaben OHNE Links/Rechts dazwischen zeigte): sehr
        # plausibel ein reflexartiges zweites OK direkt nach dem OK, das
        # den Dialog ueberhaupt erst geoeffnet hat (z.B. aus Gewohnheit,
        # weil man bei anderen Menuepunkten einfach OK druecken kann) -
        # dieses zweite OK bestaetigte bisher SOFORT die vorausgewaehlte
        # "Nein"-Option, noch bevor der Nutzer den Dialog ueberhaupt
        # bewusst wahrnehmen/reagieren konnte. self._confirm_dialog_
        # opened_at haelt fest, WANN ein Dialog geoeffnet wurde - siehe
        # die kurze Sperrzeit in der Hauptschleife (CONFIRM_DIALOG_
        # IGNORE_OK_WINDOW), die ein SOFORTIGES OK direkt danach bewusst
        # ignoriert (Richtungstasten bleiben davon unberuehrt, die darf
        # man weiterhin sofort druecken).
        self._confirm_dialog_opened_at = 0.0
        self._confirm_dialog_touched = False   # siehe _confirm_dialog_toggle()
        # NEUES FEATURE (Nutzerwunsch: "koennen wir das Update-Popup um
        # eine Abfrage 'jetzt installieren oder spaeter' erweitern?") -
        # eigener, vom Beenden-Dialog unabhaengiger Zustand fuer den
        # "Update jetzt installieren?"-Dialog (siehe
        # _start_update_install_dialog()/draw_confirm_dialog()), nutzt
        # aber bewusst dasselbe self.confirm_choice-Feld direkt oberhalb
        # zur Knopf-Auswahl mit - beide Dialoge schliessen sich
        # gegenseitig aus (nie beide gleichzeitig aktiv), ein eigenes
        # zweites Auswahl-Feld waere hier nur unnoetige Dopplung.
        self.confirm_update = False
        self._update_install_message = ""
        # NEUES FEATURE (Nutzerwunsch: Volltextsuche statt nur
        # Anfangsbuchstaben-Sprung) - siehe jump_to_substring().
        self._search_mode = False
        self._search_query = ""
        if self.music.available():
            self.music.tick()      # start playback right away

    def _item_syskey(self, item, fallback):
        """Bevorzugt den im Eintrag SELBST gespeicherten Systemkey -
        wichtig fuer 'Zuletzt gespielt', wo Eintraege aus verschiedenen
        Systemen gemischt sind (die Kategorie selbst hat dort
        syskey=None). Bei normalen Kategorien liefert das denselben
        Wert wie der Kategorie-Systemkey, aendert dort also nichts."""
        try:
            if item[1] == "game" and item[2] and len(item[2]) >= 3:
                return item[2][2]
        except (IndexError, TypeError):
            pass
        return fallback

    def _draw_scan_progress(self, i, total, name):
        """Einfacher Lade-Fortschritt waehrend des (seltenen)
        tatsaechlichen Plattenscans (erster Start oder ROM-Aenderungen)
        - unabhaengig von der normalen Seiten-Infrastruktur, da
        self.cats zu diesem Zeitpunkt noch nicht existiert. Wird beim
        normalen Boot (Cache passt) gar nicht aufgerufen."""
        fb = self.fb
        W, H = fb.width, fb.height
        s = max(1, H // 360)
        ox = W * OVERSCAN_X // 100
        oy = H * OVERSCAN_Y // 100
        fb.clear(C_BG)
        fb.text(ox, oy, "MiSTer", 3 * s, C_TITLE, C_BG)
        msg = t("scanning", name)
        maxc = max(4, (W - 2 * ox) // (8 * s))
        if len(msg) > maxc:
            msg = msg[:max(1, maxc - 1)] + "~"
        fb.text(ox, oy + 50 * s, msg, s, C_TEXT, C_BG)
        bar_w = min(W - 2 * ox, 300 * s)
        bar_h = 10 * s
        by = oy + 70 * s
        fb.rect(ox, by, bar_w, bar_h, C_PANEL)
        filled = int(bar_w * (i + 1) / max(1, total))
        fb.rect(ox, by, filled, bar_h, C_ACCENT)
        fb.text(ox, by + 16 * s, "%d / %d" % (i + 1, total), s, C_DIM, C_BG)
        fb.flip()

    # Nutzerwunsch (Hauptmenue aufraeumen, "zu viele Eintraege"):
    # "Consoles", "Console (autoboot)" und "RA Cores" wandern gemeinsam
    # in einen neuen "Cores"-Unterordner im System-Menue (als je
    # eigener Unter-Unterordner darin - bleiben unterscheidbar).
    # "Utilities"/"Other" (spaeter ebenfalls Nutzerwunsch: "die
    # brauchen wir im Frontend nicht, die kann man ueber das OSD
    # starten wenn man sie braucht") werden komplett ausgelassen -
    # weder Top-Level-Kategorie noch System-Unterordner. ALLES ANDERE
    # (z.B. Arcade) bleibt unveraendert eine Top-Level-Kategorie.
    #
    # Ausgelagert in eine EIGENE Methode statt die Partitionierung
    # direkt in build_categories() zu belassen: _refresh_system_category()
    # (fuer kleine Live-Updates wie Attract-Modus umschalten) baut
    # system_items() UNABHAENGIG davon neu auf und braucht exakt
    # dasselbe Ergebnis - sonst wuerden die verschobenen Ordner nach
    # jedem solchen Toggle wieder verschwinden (im Testrendering
    # bemerkt, noch vor der Auslieferung korrigiert).
    MOVE_TO_CORES_FOLDER = {"Consoles", "Console (autoboot)", "RA Cores"}
    DROP_ENTIRELY = {"Utilities", "Other"}

    def _partition_core_cats(self, marked_recent=None, force_rescan=False):
        """scan_cores() einmal auswerten und aufteilen in
        (top_level_core_cats, cores_subcats) - siehe Klassenkommentar
        oben fuer die Zuordnung. DROP_ENTIRELY-Eintraege landen in
        keiner der beiden Listen (bewusst verworfen).

        force_rescan wird an scan_cores() durchgereicht - erzwingt fuer
        Arcade einen echten Neuaufbau des (seit dem Performance-Fix
        gecachten) Ordnerbaums statt eines eventuell noch passenden,
        aber inzwischen veralteten Cache-Eintrags (siehe fe/scan.py,
        _arcade_tree_cached())."""
        top_level = []
        cores_subcats = []
        for n, it, sk in scan_cores(skip_dir=marked_recent, force=force_rescan):
            if n in self.MOVE_TO_CORES_FOLDER:
                cores_subcats.append((n, it))
            elif n in self.DROP_ENTIRELY:
                continue
            else:
                top_level.append((n, it, sk))
        return top_level, cores_subcats

    def build_categories(self, force_rescan=False):
        # Zwischengespeicherte Attract-Modus-Spieleliste verwerfen -
        # nach einem Rescan koennten sich neue Spiele dazugesellt oder
        # welche entfernt worden sein.
        self._attract_pool = None
        # Reihenfolge: Spiele-Systeme, dann Core-Ordner, Scripts, System
        # ALLE Kategorien werden einheitlich als Baumknoten dargestellt
        # ({"folders":{...}, "items":[...]}) - Spiele-Systeme koennen
        # echte Unterordner haben, alle anderen bekommen einfach
        # folders={} (flach, wie bisher) - dadurch kann der Rest des
        # Codes (Rendering, Navigation) alle Kategorien gleich behandeln.
        self.cats = scan_games(force=force_rescan,
                               progress_cb=self._draw_scan_progress)
        # "Weiterspielen" (Nutzerwunsch): ganz oben ein einzelner,
        # hervorgehobener Vorschlag - das zuletzt gespielte Spiel, das
        # noch NICHT als durchgespielt markiert ist. Faellt weg, wenn
        # nichts passt (siehe find_continue_game()) - kein leerer
        # Eintrag fuer niemanden, der die Durchgespielt-Markierung gar
        # nicht nutzt oder gerade alles durch hat.
        continue_game = find_continue_game()
        if continue_game:
            self.cats.insert(0, (t("continue_cat"), _wrap_flat([continue_game]), None))

        # "Zuletzt gespielt": hat ein externes Skript einen _*-Ordner per
        # RECENT_MARKER gekennzeichnet, ist DER die Quelle (korrekte
        # Cores inklusive RA-Varianten, nach Spielzeit sortiert) und
        # unsere eingebaute JSON-Liste bleibt aus - sonst genau eine
        # Liste statt zweier unterschiedlicher. Ohne ein solches Skript
        # (Normalfall) liefert find_marked_recent_dir() None, und alles
        # verhaelt sich exakt wie bisher.
        marked_recent = find_marked_recent_dir()
        if marked_recent:
            recent_items = _folder_items(marked_recent, by_mtime=True)
        else:
            recent_items = load_recent()
        if recent_items:
            # Direkt nach "Weiterspielen" (falls vorhanden, sonst ganz
            # vorne), damit sie ohne Scrollen erreichbar ist.
            # syskey=None (wie Scripts/System), da die Liste mehrere
            # Systeme mischt - jeder Eintrag traegt seinen eigenen
            # Systemkey in arg[2], der beim Zeichnen bevorzugt wird
            # (siehe _item_syskey()).
            pos = 1 if continue_game else 0
            self.cats.insert(pos, (t("recent_cat"), _wrap_flat(recent_items), None))
        favorite_items = load_favorites()
        if favorite_items:
            # Direkt nach "Zuletzt gespielt"/"Weiterspielen" (je
            # nachdem, was vorhanden ist) - eigene, bewusst kuratierte
            # Auswahl, im Gegensatz zur automatischen Verlaufsliste.
            pos = (1 if continue_game else 0) + (1 if recent_items else 0)
            self.cats.insert(pos, (t("favorites_cat"), _wrap_flat(favorite_items), None))
        # Nutzerwunsch (Hauptmenue aufraeumen, "zu viele Eintraege"):
        # "Consoles", "Console (autoboot)" und "RA Cores" wandern
        # gemeinsam in einen neuen "Cores"-Unterordner im System-Menue
        # (als je eigener Unter-Unterordner darin - bleiben
        # unterscheidbar). "Utilities"/"Other" werden komplett
        # ausgelassen ("die brauchen wir im Frontend nicht, die kann
        # man ueber das OSD starten wenn man sie braucht") - weder
        # Top-Level-Kategorie noch System-Unterordner. ALLES ANDERE
        # (z.B. Arcade) bleibt unveraendert eine Top-Level-Kategorie.
        # "Scripts" wurde aus demselben Grund zunaechst ebenfalls
        # ausgelassen, auf spaeteren Wunsch aber wieder als eigener
        # Unterordner im System-Menue ergaenzt (siehe scripts_items
        # unten) - NICHT als Top-Level-Kategorie.
        top_level_core_cats, cores_subcats = self._partition_core_cats(
            marked_recent, force_rescan=force_rescan)
        # GEAENDERT (Nutzerfrage: Arcade-Unterordner wie "alternatives"/
        # "organized"/"ST-V" fehlten im Frontend, siehe _arcade_folder_
        # tree() in fe/scan.py): scan_cores() liefert fuer Arcade jetzt
        # bereits einen FERTIGEN Baumknoten (echte Unterordner) statt
        # einer flachen Liste - der darf NICHT nochmal durch
        # _wrap_flat() (das wuerde "items" auf den ganzen Baumknoten
        # statt einer Liste setzen und jede Navigation dort zerstoeren).
        # Alle anderen _*-Ordner liefern weiterhin eine flache Liste wie
        # bisher und werden entsprechend weiterhin gewickelt.
        self.cats.extend(
            (n, it if isinstance(it, dict) else _wrap_flat(it), sk)
            for n, it, sk in top_level_core_cats)
        collections = self.build_collections_category()
        if collections:
            count = _count_tree_items(collections)
            self.cats.append(("%s (%d)" % (t("collections_cat"), count),
                              collections, None))
        ra_hunter = self.build_ra_hunter_category()
        if ra_hunter:
            count = _count_tree_items(ra_hunter)
            self.cats.append(("%s (%d)" % (t("ra_hunter_cat"), count),
                              ra_hunter, None))
        # Zufalls-Zock (internes Kuerzel im Code weiterhin WOT): eigene Kategorie,
        # gleiches Prinzip wie RA-Erfolgsjaeger direkt darueber. IMMER aktiv -
        # das Feature ist jetzt ROM-first (Spiele kommen aus den vorhandenen
        # ROMs, gespielt-DB als JSON), eine CSV ist nicht mehr noetig. Nur EIN
        # Eintrag ("Spiel ziehen"), kein Ordnerbaum - das Ziehen selbst
        # passiert im Bildschirm (draw_wot_screen()), nicht ueber Navigation.
        # Anlegen des Menuepunkts ist billig; der (nur beim ersten Oeffnen /
        # nach ROM-Aenderung) teure Katalogbau laeuft erst in draw_wot_screen().
        self.cats.append((t("wot_title"), _wrap_flat(
            [(t("sys_wot_action"), "wot_draw", None)]), None))
        self.cats.append(("System", system_items(
            self.music.enabled, self.music.source,
            rainwave.station_name(self.music.radio.sid) if self.music.radio else "",
            cores_subcats=cores_subcats,
            scripts_items=scan_scripts(),
        ), None))
        if curated_only_active():
            # filter_curated() laesst Kategorien ohne syskey (Scripts,
            # System, Core-Ordner) unveraendert - nur echte Spiele-
            # Systeme werden eingeschraenkt.
            self.cats = [filter_curated(n, it, sk) for n, it, sk in self.cats]

    def _go_back_or_confirm_quit(self):
        """ESC/B (und der 3x-Select-Kurzbefehl): auf Seite 1 zuerst
        eine Ordnerebene hoch (falls man in einem Unterordner ist),
        erst danach zurueck zu den Kategorien; im Hauptmenue (Seite 0)
        stattdessen die Beenden-Bestaetigung einblenden statt sofort
        zu schliessen.

        BUGFIX: sprang bisher beim Zurueckgehen IMMER auf Position 0
        der uebergeordneten Ebene, unabhaengig davon, wo man vor dem
        Betreten des Unterordners stand - z.B. aus einem alphabetisch
        sortierten Unterordner "Q" zurueck landete man wieder ganz oben
        bei "A" statt bei "Q", wo man weiterbrowsen wollte. Jetzt wird
        die Position beim Betreten eines Unterordners auf einem Stapel
        gemerkt (siehe self._nav_position_stack) und beim Zurueckgehen
        wiederhergestellt."""
        if self.page == 1:
            if self.nav_path:
                self.nav_path.pop()
                if self._nav_position_stack:
                    self.item_i, self.scroll = self._nav_position_stack.pop()
                else:
                    self.item_i = 0
                    self.scroll = 0
                self.marquee_reset()
            else:
                self.page = 0
        else:
            self.confirm_quit = True
            self.confirm_choice = 1    # Nein vorausgewaehlt
        self.draw()

    def _confirm_quit_dialog(self):
        """Der explizite Menuepunkt 'Frontend beenden' im System-Menue -
        zeigt immer die Bestaetigung, unabhaengig von der Seite."""
        self.confirm_quit = True
        self.confirm_choice = 1    # Nein vorausgewaehlt
        # NEU: siehe CONFIRM_DIALOG_IGNORE_OK_WINDOW/_confirm_dialog_toggle()
        self._confirm_dialog_opened_at = time.monotonic()
        self._confirm_dialog_touched = False
        self.draw()

    def _start_update_install_dialog(self, msg):
        """NEUES FEATURE (Nutzerwunsch: "koennen wir das Update-Popup um
        eine Abfrage 'jetzt installieren oder spaeter' erweitern? Wenn
        man dann ja anklickt, dass Frontend_Install.sh ausgefuehrt wird"):
        zeigt den Update-Installieren-Dialog (self.confirm_update, siehe
        __init__ und draw()) mit dem uebergebenen, bereits fertig
        formatierten Hinweistext (Versions- ODER Build-Popup-Text, siehe
        die beiden Aufrufer in next_action()). "Spaeter" vorausgewaehlt -
        derselbe sichere Standard wie beim Beenden-Dialog, ein
        versehentliches Enter darf niemals ungefragt einen Download/
        Update-Lauf anstossen."""
        self.confirm_update = True
        self.confirm_choice = 1    # Spaeter vorausgewaehlt
        self._update_install_message = msg
        # NEU: siehe CONFIRM_DIALOG_IGNORE_OK_WINDOW/_confirm_dialog_toggle()
        self._confirm_dialog_opened_at = time.monotonic()
        self._confirm_dialog_touched = False
        self.draw()

    def _confirm_dialog_toggle(self, act):
        """Gemeinsame Richtungs-Logik fuer BEIDE Ja/Nein-Bestaetigungs-
        dialoge (Beenden UND Update-Installieren - identische
        Button-Reihenfolge: Option 0 links, Option 1 rechts). Liefert
        True, wenn act tatsaechlich eine Richtungseingabe war (nur fuer
        den Aufrufer/Tests praktisch, sonst ungenutzt).

        NEU (Nutzer-Rueckmeldung: siehe ausfuehrlicher Kommentar bei
        draw_confirm_dialog() - ein echtes frontend.log zeigte, dass
        Nutzer wiederholt NUR "ok" gedrueckt haben, nie "links"/
        "rechts" davor, wodurch immer die vorausgewaehlte "Nein"/
        "Spaeter"-Option bestaetigt wurde): hoch/runter schalten jetzt
        GENAUSO wie links/rechts zwischen den beiden Optionen um - das
        entspricht exakt dem bereits bestehenden, vertrauten Muster aus
        draw_core_choice_screen()/draw_wot_screen() (dort toggelt JEDE
        Richtungstaste zwischen den beiden bzw. mehreren Optionen).
        "Hoch" wechselt zur ERSTEN Option (wie "links"), "runter" zur
        ZWEITEN (wie "rechts") - entspricht der Lese-/Leserichtung
        oben-nach-unten genauso wie links-nach-rechts."""
        if act in ("left", "up"):
            self.confirm_choice = 0
            self._confirm_dialog_touched = True
            return True
        if act in ("right", "down"):
            self.confirm_choice = 1
            self._confirm_dialog_touched = True
            return True
        return False

    def _confirm_dialog_ok_too_soon(self):
        """True, wenn ein "ok" bewusst NICHT als Bestaetigung gewertet
        werden soll, weil es vermutlich nur das reflexartige Echo des
        OK ist, das den Dialog gerade erst geoeffnet hat - NUR
        relevant, solange der Nutzer noch KEINE einzige bewusste
        Richtungseingabe im Dialog gemacht hat (self._confirm_dialog_
        touched, siehe _confirm_dialog_toggle()) UND seit dem Oeffnen
        noch keine CONFIRM_DIALOG_IGNORE_OK_WINDOW Sekunden vergangen
        sind. Sobald der Nutzer einmal bewusst links/rechts/hoch/runter
        gedrueckt hat, greift diese Sperre NIE MEHR fuer diesen offenen
        Dialog - ein direkt darauf folgendes "ok" ist dann eindeutig
        eine bewusste, schnelle Bestaetigung und darf NICHT mehr
        verzoegert werden (siehe Testfall: 'hoch' + sofortiges 'ok')."""
        if self._confirm_dialog_touched:
            return False
        return (time.monotonic() - self._confirm_dialog_opened_at
                < CONFIRM_DIALOG_IGNORE_OK_WINDOW)

    def _refresh_system_category(self):
        """Nach dem Umschalten einer System-Menue-Einstellung (z.B.
        Attract-Modus) die 'System'-Kategorie in self.cats mit frisch
        berechneten Beschriftungen aktualisieren - OHNE die teure
        komplette build_categories() aufzurufen (die wuerde unnoetig
        einen Scan/Cache-Check aller Spiele-Systeme anstossen, nur um
        eine einzelne Beschriftung wie 'Attract-Modus: AN/AUS' zu
        aktualisieren). Gleiches Prinzip wie _sync_favorites_category().

        BUGFIX (v1.73 hatte selbst noch einen Fehler): toggle_attract_mode()
        aenderte bisher nur die zugrundeliegende Markierungsdatei - die
        im Menue ANGEZEIGTE Beschriftung blieb dabei eingefroren, da
        system_items() nur EINMAL beim Kategorien-Aufbau berechnet wird.
        Der urspruengliche v1.73-Fix suchte dafuer die erste Kategorie
        mit syskey=None - aber das ist NICHT eindeutig: 'Zuletzt
        gespielt', 'Favoriten' und 'Scripts' nutzen ALLE ebenfalls
        syskey=None und stehen in self.cats VOR 'System' (werden per
        insert(0, ...) bzw. vor dem abschliessenden append() einsortiert).
        Dadurch wurde bisher die FALSCHE Kategorie ueberschrieben (meist
        'Zuletzt gespielt'), waehrend 'System' selbst nie aktualisiert
        wurde - die Beschriftung blieb dadurch dauerhaft eingefroren,
        egal wie oft man umschaltet. Jetzt eindeutig ueber den (nicht
        uebersetzten, immer gleichen) Namen \"System\" gefunden."""
        for i, (name, node, sk) in enumerate(self.cats):
            if sk is None and name == "System":
                _top, cores_subcats = self._partition_core_cats(find_marked_recent_dir())
                self.cats[i] = (name, system_items(
                    self.music.enabled, self.music.source,
                    rainwave.station_name(self.music.radio.sid) if self.music.radio else "",
                    cores_subcats=cores_subcats,
                    scripts_items=scan_scripts(),
                ), sk)
                LOG("_refresh_system_category: System-Kategorie an Position %d aktualisiert" % i)
                return
        LOG("_refresh_system_category: KEINE System-Kategorie gefunden!")

    def _sync_favorites_category(self):
        """Nach toggle_favorite() die 'Favoriten'-Kategorie in
        self.cats aktuell halten - OHNE build_categories() aufzurufen
        (das wuerde unnoetig einen Scan/Cache-Check aller Spiele-
        Systeme mit anstossen, nur um ein einzelnes Flag zu
        aktualisieren). Haelt die aktuell betrachtete Kategorie ueber
        Namen+Systemkey identifiziert, damit sich die Auswahl nicht
        verschiebt, wenn Favoriten weiter oben in der Liste erscheint
        oder verschwindet."""
        current_ref = self.cats[self.cat_i][0], self.cats[self.cat_i][2] \
            if self.cats else None

        favs = load_favorites()
        fav_name = t("favorites_cat")
        self.cats = [c for c in self.cats
                    if not (c[0] == fav_name and c[2] is None)]
        if favs:
            recent_name = t("recent_cat")
            pos = 1 if (self.cats and self.cats[0][0] == recent_name) else 0
            self.cats.insert(pos, (fav_name, _wrap_flat(favs), None))

        if current_ref is not None:
            for i, c in enumerate(self.cats):
                if (c[0], c[2]) == current_ref:
                    self.cat_i = i
                    break
            else:
                # Die Kategorie, die wir gerade betrachtet haben, gibt
                # es nicht mehr (Favoriten wurde gerade komplett leer
                # und wir waren genau dort) - zurueck zu den
                # Kategorien statt auf eine falsche Liste zu zeigen.
                self.cat_i = min(self.cat_i, len(self.cats) - 1) if self.cats else 0
                if self.page == 1:
                    self.page = 0
                    self.nav_path = []
                    self._nav_position_stack = []

        if self.page == 1:
            display = self._display_items()
            if self.item_i >= len(display):
                self.item_i = max(0, len(display) - 1)

    def _sync_recent_category(self):
        """Nach der Rueckkehr aus einem Spiel (run_core()) 'Weiterspielen'
        und 'Zuletzt gespielt' in self.cats aktuell halten - OHNE die
        teure komplette build_categories() aufzurufen (die einen
        Scan/Cache-Check ALLER Spiele-Systeme anstossen wuerde, nur um
        zwei kleine Listen aufzufrischen - das wuerde nach JEDEM Spiel
        spuerbar Ladezeit kosten). Gleiches Prinzip wie
        _sync_favorites_category() direkt darueber.

        BUGFIX (Nutzer-Rueckmeldung: "Weiterspielen und Zuletzt gezockt
        funktioniert bei mir doch nicht so richtig. Er zeigt zwar nun
        andere Spiele an. Aber Tetris (NES RA) zB was ich vorhin kurz
        gespielt habe, zeigt er nicht."): per Diagnose (recently_played.json
        UND frontend.log vom Nutzer gegengeprueft) bestaetigt, dass
        record_recent() (siehe Spielstart-Code oben, wird bei JEDEM
        Spielstart aufgerufen, unabhaengig vom gewaehlten Core) die
        Aufzeichnung selbst immer korrekt und sofort VOR dem Start in
        recently_played.json schreibt - Tetris stand tatsaechlich an
        Position 0. Der Fehler lag also nicht in der Aufzeichnung,
        sondern in der ANZEIGE: self.cats (und damit die Eintraege
        'Weiterspielen'/'Zuletzt gespielt') wird nur beim Programmstart
        bzw. bei einem echten Rescan neu aufgebaut - run_core() rief
        bisher an keiner Stelle einen Refresh dieser beiden Kategorien
        auf, weshalb das Menue nach der Rueckkehr aus einem Spiel
        weiterhin den Stand von DAVOR zeigte, bis rein zufaellig ein
        anderer Vorgang (Rescan, Sprachwechsel, Musik-Umschalten -
        alle rufen intern build_categories() auf) einen kompletten
        Neuaufbau ausloeste."""
        current_ref = (self.cats[self.cat_i][0], self.cats[self.cat_i][2]) \
            if self.cats else None

        continue_name = t("continue_cat")
        recent_name = t("recent_cat")
        self.cats = [c for c in self.cats
                    if not (c[2] is None and c[0] in (continue_name, recent_name))]

        marked_recent = find_marked_recent_dir()
        if marked_recent:
            recent_items = _folder_items(marked_recent, by_mtime=True)
        else:
            recent_items = load_recent()
        continue_game = find_continue_game()

        # Reihenfolge wie in build_categories(): "Weiterspielen" ganz
        # vorne, "Zuletzt gespielt" direkt danach (bzw. ganz vorne,
        # falls kein "Weiterspielen"-Vorschlag vorhanden ist).
        if recent_items:
            self.cats.insert(0, (recent_name, _wrap_flat(recent_items), None))
        if continue_game:
            self.cats.insert(0, (continue_name, _wrap_flat([continue_game]), None))

        if current_ref is not None:
            for i, c in enumerate(self.cats):
                if (c[0], c[2]) == current_ref:
                    self.cat_i = i
                    break
            else:
                # Die Kategorie, die wir gerade betrachtet haben, gibt
                # es nicht mehr (z.B. "Weiterspielen" ist gerade
                # weggefallen und wir waren genau dort) - zurueck zu
                # den Kategorien statt auf eine falsche Liste zu zeigen.
                self.cat_i = min(self.cat_i, len(self.cats) - 1) if self.cats else 0
                if self.page == 1:
                    self.page = 0
                    self.nav_path = []
                    self._nav_position_stack = []

        if self.page == 1:
            display = self._display_items()
            if self.item_i >= len(display):
                self.item_i = max(0, len(display) - 1)
        LOG("_sync_recent_category: Weiterspielen/Zuletzt gespielt nach "
            "Spielende aktualisiert (Weiterspielen=%s, Zuletzt-gespielt-"
            "Eintraege=%d)" % (bool(continue_game), len(recent_items)))

    def _enter_category(self):
        """Von Seite 0 (Kategorien-Menue) in Seite 1 (Liste der
        aktuellen Kategorie, oberste Ordnerebene) wechseln."""
        name, node, sk = self.cats[self.cat_i]
        if not node["folders"] and not node["items"]:
            return
        # RA-Core-Auswahl: nur anzeigen, wenn fuer dieses System
        # tatsaechlich eine RA-faehige Core-Variante gefunden wurde
        # (siehe find_ra_core()) - sonst unveraendertes Verhalten wie
        # bisher, keine zusaetzliche Abfrage fuer alle anderen.
        if sk:
            ra_core = find_ra_core(sk)
            if ra_core:
                use_ra = self.draw_core_choice_screen(sk, name)
                if use_ra is None:
                    return   # ESC/back - Kategorie NICHT betreten, Seite 0 bleibt
                if not hasattr(self, "_ra_core_choice"):
                    self._ra_core_choice = {}
                self._ra_core_choice[sk] = ra_core if use_ra else None
        self.page = 1
        self.nav_path = []
        self._nav_position_stack = []
        self.item_i = 0
        self.scroll = 0
        self.marquee_reset()

    def _current_node(self):
        """Baumknoten, der der aktuellen Navigationstiefe (nav_path)
        innerhalb der gewaehlten Kategorie entspricht."""
        node = self.cats[self.cat_i][1]
        for folder_name in self.nav_path:
            node = node["folders"].get(folder_name, _empty_node())
        return node

    def _display_items(self):
        """Aktuell anzuzeigende flache Liste fuer Seite 1: erst
        Unterordner (kind='folder', anklickbar zum Reinwechseln), dann
        die Eintraege des aktuellen Knotens - alphabetisch sortiert
        innerhalb jeder Gruppe. Ordner-Eintraege tragen als arg den
        reinen Ordnernamen (zum Nachschlagen beim Reinwechseln).

        PERFORMANCE-FIX (Nutzer-Review, gegen den echten Code geprueft
        und bestaetigt): wird an sehr vielen Stellen verwendet
        (Zeichnen, Stream-State, Navigation, Suche, Zufall, Cover-
        Prefetch) und sortierte bisher bei JEDEM einzelnen Aufruf neu -
        bei einer grossen Sammlung mit vielen Unterordnern spuerbar
        unnoetige Arbeit, da sich die Sortierung zwischen zwei Aufrufen
        so gut wie nie aendert.

        Cache direkt AM Knoten (nicht in einem separaten, global
        wachsenden Dict) - Knoten werden im ganzen Projekt nachweislich
        NIE nachtraeglich veraendert (kein einziges node['items'].
        append()/node['folders'][...]=... o.ae. im gesamten Code
        gefunden), sondern bei Aenderungen (Rescan, Favoriten-Wechsel,
        kuratierter Filter, ...) immer als KOMPLETT NEUER Baum via
        build_categories() aufgebaut. Ein frisch gebauter Knoten ist
        dadurch automatisch ohne Cache-Eintrag - keine manuelle
        Invalidierung an jeder Aenderungsstelle noetig, dasselbe
        risikoarme Prinzip wie schon beim Stream-Dirty-Flag."""
        node = self._current_node()
        cached = node.get("_display_items_cache")
        if cached is not None:
            return cached
        folder_names = sorted(node["folders"].keys(), key=str.lower)
        folder_entries = [(fname + "/", "folder", fname)
                          for fname in folder_names]
        result = folder_entries + node["items"]
        node["_display_items_cache"] = result
        return result

    QUICK_GAME_MIN_LAUNCHES = 2       # mindestens 2 Starts, sonst zu
                                      # wenig Aussagekraft
    QUICK_GAME_MAX_AVG_SECONDS = 900  # 15 Minuten durchschnittliche
                                      # Sitzungsdauer als Schwelle

    def build_collections_category(self):
        """Baut die "Sammlungen"-Kategorie (Nutzerwunsch: "digitales
        Retro-Wohnzimmer") - automatische, aus bereits vorhandenen
        Daten abgeleitete Gruppierungen. Aktuell zwei: "Dieses Jahr
        entdeckt" (baut auf dem v4.1-Fundament auf, siehe
        _load_first_played()) und "Kurzweilige Spiele" (kurze
        durchschnittliche Sitzungsdauer, aus dem bestehenden
        Spielzeit-Tracker). Wiederverwendet die normale Ordner-
        Navigation, gleiches Prinzip wie build_ra_hunter_category().
        Liefert None, wenn beide Sammlungen leer sind (Kategorie
        taucht dann gar nicht auf, siehe build_categories())."""
        self._attract_pool = None   # sicherstellen, dass der frische
                                    # Kategorienstand gescannt wird
        pool = self._attract_games_pool()
        pool_by_name = {}
        for name, _syskey, arg in pool:
            pool_by_name.setdefault(name, arg)   # erster Treffer
                                                 # gewinnt bei
                                                 # Namenskollisionen

        folders = {}

        # --- "Dieses Jahr entdeckt" ---
        year = _current_year()
        first_played = _load_first_played()
        discovered = sorted(name for name, y in first_played.items()
                            if y == year and name in pool_by_name)
        # Gleicher Kompatibilitaets-Grund wie in compute_year_review_stats():
        # first_played.json speichert jetzt volle Datumsangaben statt nur
        # Jahreszahlen - [:4] funktioniert fuer beide Formate.
        discovered = sorted(name for name, y in first_played.items()
                            if y[:4] == year and name in pool_by_name)
        if discovered:
            items = [(name, "game", pool_by_name[name]) for name in discovered]
            label = t("collection_discovered_this_year", year) + " (%d)" % len(items)
            folders[label] = {"folders": {}, "items": items}

        # --- "Kurzweilige Spiele" (kurze durchschnittliche Sitzung) ---
        playtime = load_playtime()
        quick = []
        for name, e in playtime.items():
            launches = e.get("launches", 0)
            seconds = e.get("seconds", 0)
            # Mindestens QUICK_GAME_MIN_LAUNCHES Starts noetig, sonst
            # zu wenig Aussagekraft (ein einzelner kurzer Testlauf
            # soll nicht sofort als "kurzweiliges Spiel" gelten).
            if launches >= self.QUICK_GAME_MIN_LAUNCHES and name in pool_by_name:
                avg = seconds / launches
                if avg <= self.QUICK_GAME_MAX_AVG_SECONDS:
                    quick.append((name, avg))
        if quick:
            quick.sort(key=lambda g: g[1])   # kuerzeste zuerst
            items = [(name, "game", pool_by_name[name]) for name, _avg in quick]
            label = t("collection_quick_games") + " (%d)" % len(items)
            folders[label] = {"folders": {}, "items": items}

        if not folders:
            return None
        return {"folders": folders, "items": []}

    def build_ra_hunter_category(self):
        """Baut die "RA-Erfolgsjaeger"-Kategorie: ein Ordner pro
        System, das mindestens ein Spiel mit RA-Erfolgen aber noch
        KEINEM einzigen freigeschalteten enthaelt - "hier warten
        unbenutzte Erfolge". Wiederverwendet die normale Ordner-
        Navigation (wie bei eigenen ROM-Unterordnern) - kein neuer
        Navigationsmechanismus noetig. Liefert None, wenn RA nicht
        eingerichtet ist oder nichts passt (Kategorie taucht dann gar
        nicht auf, siehe build_categories()).

        ERWEITERT (Nutzerwunsch: Erfolgsjaeger um eine "Fast geschafft"-
        Gruppe erweitern): zusaetzlicher, EIGENER Unterordner (ueber
        alle Systeme hinweg, nicht nach System aufgeteilt - meist nur
        eine Handvoll Spiele, eine zusaetzliche Aufteilung waere hier
        eher unuebersichtlich als hilfreich) fuer Spiele, bei denen nur
        noch WENIGE Erfolge fehlen (<=3) - sortiert nach am wenigsten
        Fehlendem zuerst, damit das naechste erreichbare Ziel immer
        oben steht."""
        if not ra_enabled() or not self._ra_lookup:
            return None
        self._attract_pool = None   # sicherstellen, dass der frische
                                    # Kategorienstand gescannt wird,
                                    # nicht ein evtl. veralteter Cache
        pool = self._attract_games_pool()
        by_system = {}
        almost_done = []   # (name, fehlend, total, arg) - systemuebergreifend
        for name, syskey, arg in pool:
            result = lookup_ra_progress(self._ra_lookup, name, syskey)
            if result is None:
                continue
            earned, total = result
            if total > 0 and earned == 0:
                by_system.setdefault(syskey, []).append((name, total, arg))
            elif total > 0 and 0 < earned < total and (total - earned) <= 3:
                almost_done.append((name, total - earned, arg))
        if not by_system and not almost_done:
            return None
        folders = {}
        if almost_done:
            almost_done.sort(key=lambda g: g[1])   # am wenigsten fehlend zuerst
            items = [(name, "game", arg) for name, remaining, arg in almost_done]
            label = "%s (%d)" % (t("ra_almost_done_cat"), len(almost_done))
            folders[label] = {"folders": {}, "items": items}
        for syskey, games in by_system.items():
            games.sort(key=lambda g: -g[1])   # meiste Erfolge zuerst
            items = [(name, "game", arg) for name, total, arg in games]
            label = "%s (%d)" % (system_display_name(syskey), len(games))
            folders[label] = {"folders": {}, "items": items}
        return {"folders": folders, "items": []}

    def _attract_games_pool(self):
        """Flache Liste ALLER Spiele (kind='game') ueber alle echten
        Spiele-Systeme hinweg (Scripts/System/Zuletzt-gespielt bleiben
        aussen vor, da syskey=None) - fuer den Attract-Modus. Wird
        einmal gebaut und zwischengespeichert, nicht bei jedem
        Wechsel neu durchsucht."""
        if self._attract_pool is not None:
            return self._attract_pool

        def walk(node, syskey):
            found = []
            for it in node["items"]:
                if it[1] == "game":
                    found.append((it[0], syskey, it[2]))
            for sub in node["folders"].values():
                found.extend(walk(sub, syskey))
            return found

        pool = []
        for _name, node, syskey in self.cats:
            if syskey:
                pool.extend(walk(node, syskey))
        self._attract_pool = pool
        return pool

    # NEUES FEATURE (Nutzerwunsch: "im Leerlauf/Attract-Modus nach und
    # nach die ganze Bibliothek im Hintergrund vorladen, damit wirklich
    # JEDES Spiel beim ersten F6-Druck schon sofort da ist" - Ausbau
    # des Stale-while-revalidate-Fixes von vorhin, der nur EINZELNE,
    # bereits einmal angesehene Spiele beschleunigt hat). Kostet KEINE
    # zusaetzliche RA-Abfrage fuer die Kandidatenliste selbst - welche
    # Bibliotheksspiele ueberhaupt eine RA-GameID haben, steht schon
    # aus dem einen Sammel-Abruf beim Programmstart bereit
    # (self._ra_lookup, siehe __init__ und lookup_ra_game_id()).
    RA_PREWARM_STALE_SECONDS = 6 * 3600   # deutlich grosszuegiger als die
                                          # 15-Minuten-Frische beim aktiven
                                          # Ansehen (F6) - ein Spiel, das
                                          # innerhalb der letzten 6 Stunden
                                          # vorgewaermt wurde, wird bei
                                          # laengerem Leerlauf NICHT gleich
                                          # wieder angefasst, sonst wuerde
                                          # eine grosse Bibliothek bei jedem
                                          # laengeren Leerlauf komplett neu
                                          # abgefragt.
    RA_PREWARM_THROTTLE_SECONDS = 4.0     # Pause zwischen zwei Abrufen -
                                          # schont RA-API und Netzwerk,
                                          # kein Sturm auf einmal.

    def _ra_prewarm_candidates(self):
        """Geordnete Kandidatenliste fuers Vorwaermen: alle Bibliotheks-
        Spiele mit bekannter RA-GameID, Favoriten und zuletzt Gespielte
        zuerst (die schaut man sich ohnehin am ehesten mit F6 an -
        sollen deshalb als erstes fertig sein), Rest danach."""
        pool = self._attract_games_pool()
        fav_names = {e[0] for e in load_favorites()}
        recent_names = {e[0] for e in load_recent()}
        seen = set()
        scored = []
        for name, syskey, arg in pool:
            if name in seen:
                continue
            game_id = lookup_ra_game_id(self._ra_lookup, name, syskey)
            if not game_id:
                continue
            seen.add(name)
            prio = 0 if name in fav_names else (1 if name in recent_names else 2)
            scored.append((prio, name, game_id))
        scored.sort(key=lambda t: t[0])
        return [(name, game_id) for _prio, name, game_id in scored]

    def _prewarm_ra_achievements(self):
        """Laeuft in einem eigenen Hintergrund-Thread, EIN einmaliger
        Durchlauf pro Sitzung (kein endloses Wiederholen). Pausiert bei
        jeder Nutzer-Eingabe (wartet dann einfach weiter statt
        abzubrechen), ueberspringt bereits ausreichend frische
        Eintraege (RA_PREWARM_STALE_SECONDS), und nutzt fuer den
        eigentlichen Abruf dieselbe Sperren-geschuetzte
        _refresh_ra_achievements_background() wie der F6-Bildschirm
        selbst - kein Doppel-Abruf moeglich, falls der Nutzer
        waehrenddessen zufaellig genau dasselbe Spiel per F6 ansieht.
        Wird synchron (nicht als weiterer Thread pro Spiel) innerhalb
        DIESES einen Hintergrund-Threads aufgerufen, damit die
        Drosselung (Pause zwischen Abrufen) auch wirklich greift.

        GEAENDERT (Nutzerwunsch: "F6 dauert ganz schoen bis die Erfolge
        angezeigt werden"): _refresh_ra_achievements_background() laedt
        inzwischen nicht mehr nur die Text-Erfolgsliste vor, sondern
        gleich auch alle zugehoerigen Badge-Icons (siehe dort) - beim
        tatsaechlichen F6-Druck ist damit im Regelfall (Favoriten/
        zuletzt Gespielte zuerst, siehe _ra_prewarm_candidates())
        wirklich alles bereits lokal vorhanden, nicht nur der Text.

        BUGFIX/PERFORMANCE (Nutzer-Rueckmeldung: "es nervt total wenn
        ich in meiner gameboy sammlung oder sonst einer sammlung
        rumscrolle und wieder auf zurueck gehe das das teilweise
        sekunden braucht"): die Leerlauf-Pruefung unten (die while-
        True-Warteschleife) griff bislang nur VOR jedem Spiel - war ein
        Spiel erstmal dran, dekodierte _refresh_ra_achievements_
        background() alle seine Badge-Icons am Stueck durch, egal ob
        der Nutzer zwischendurch wieder aktiv wurde. Das reine Python-
        Dekodieren (fe/art.py, decode_png(), keine C-Beschleunigung)
        ist auf MiSTers ARM-Kern spuerbar teuer und haelt dabei den
        GIL fest, was den Haupt-Zeichen-/Eingabe-Thread ausbremst -
        genau das war das gemeldete "teilweise Sekunden"-Stocken beim
        Scrollen/Zurueckgehen. _refresh_ra_achievements_background()
        bekommt jetzt should_abort() uebergeben, das nach JEDEM
        einzelnen Icon erneut denselben Leerlauf-Massstab prueft wie
        die Warteschleife hier - wird der Nutzer waehrenddessen aktiv,
        bricht das Vorwaermen fuer dieses eine Spiel sofort ab (die
        restlichen Icons holt entweder der naechste Leerlauf-Durchlauf
        nach, oder sie laden ganz normal beim tatsaechlichen F6-Aufruf,
        wie vor dem Icon-Vorwaermen-Feature)."""
        candidates = self._ra_prewarm_candidates()
        if not candidates:
            return
        LOG("RA-Hintergrund-Vorwaermen: %d Kandidat(en)" % len(candidates))

        def _idle_enough():
            return (time.monotonic() - self._last_input_time) > self._attract_delay_cached()

        warmed = 0
        for name, game_id in candidates:
            while True:
                if _idle_enough():
                    break
                time.sleep(2.0)
            cache = _load_ra_achievements_cache()
            entry = cache.get(str(game_id))
            if entry and (time.time() - entry.get("ts", 0)) < self.RA_PREWARM_STALE_SECONDS:
                continue
            _refresh_ra_achievements_background(
                game_id, timeout=5.0,
                should_abort=lambda: not _idle_enough())
            warmed += 1
            time.sleep(self.RA_PREWARM_THROTTLE_SECONDS)
        LOG("RA-Hintergrund-Vorwaermen: fertig (%d von %d tatsaechlich abgerufen)"
            % (warmed, len(candidates)))

    def _check_for_update_background(self):
        """Laeuft in einem eigenen Hintergrund-Thread (Nutzerwunsch:
        "wenn es ein Update gibt, einmal eine Info anzeigen" - das
        eigentliche Herunterladen/Installieren bleibt bewusst manuell
        ueber Frontend_Install.sh, hier geht es NUR um die
        Benachrichtigung). EIN einzelner, leiser Abruf pro Sitzung -
        schlaegt er fehl (kein Internet, DNS-Problem), wird es beim
        naechsten Neustart einfach wieder versucht, kein Wiederholungs-
        Loop und keine Fehlermeldung, die stoert.

        self._update_popup_pending wird NUR gesetzt (nicht selbst
        gezeichnet - Framebuffer-Zugriff bleibt dem Haupt-Thread
        vorbehalten) und von next_action() im Haupt-Thread konsumiert,
        siehe dortiger Kommentar."""
        LOG("Update-Check gestartet (Hauptmenue sichtbar)")
        remote = check_for_update()
        state = load_update_state()
        if remote:
            state["remote_version"] = remote
            state["last_checked"] = time.time()
            if _version_newer(remote, FRONTEND_VERSION) and state.get("notified_version") != remote:
                self._update_popup_pending = remote
                # BUGFIX (Nutzer-Rueckmeldung: "ich bekomme seit ein paar
                # Updates keine Popup-Info mehr, ich krieg sie erst wenn
                # ich manuell update gemacht habe"): "notified_version"
                # wurde FRUEHER genau HIER, direkt beim Erkennen im
                # Hintergrund-Thread, gesetzt UND sofort persistiert (siehe
                # save_update_state() unten) - lange BEVOR der Haupt-Thread
                # den Dialog ueberhaupt gezeichnet hat. Traf in derselben
                # Leerlauf-Runde der (jetzt behobene) Uebermal-Fehler zu
                # (marquee_tick()/COVER_SETTLE-Redraw loeschten den Dialog
                # sofort wieder, siehe next_action()), war die Version
                # trotzdem schon dauerhaft als "gezeigt" markiert - der
                # Dialog erschien dadurch nie wieder, auch nicht nach einem
                # Neustart, obwohl der Nutzer ihn nie zu Gesicht bekommen
                # hatte. Jetzt wird "notified_version" NICHT mehr hier,
                # sondern erst markiert, NACHDEM der Dialog im Haupt-Thread
                # tatsaechlich gezeichnet wurde (siehe next_action(),
                # Block "pending_update") - schlaegt das Zeichnen aus
                # irgendeinem Grund fehl oder wird die Sitzung vorher
                # beendet, fragt der naechste Start einfach erneut nach,
                # statt die Meldung fuer immer zu unterdruecken.
        # NEUES FEATURE (siehe check_for_build_update() in
        # fe/update_check.py fuer die ausfuehrliche Begruendung, warum
        # das ein EIGENSTAENDIGER, von der Versionsnummer unabhaengiger
        # Check ist) - im selben Hintergrund-Aufruf mit erledigt (ein
        # Thread statt zwei), aber bewusst UNABHAENGIG vom obigen
        # Versions-Ergebnis: wird auch dann geprueft/angezeigt, wenn
        # remote oben leer war oder keine neuere Version meldet.
        build = check_for_build_update()
        if build:
            build_id, summary = build
            if state.get("notified_build_id") != build_id:
                self._build_popup_pending = summary
                # BUGFIX: siehe ausfuehrlicher Kommentar beim
                # Versions-Popup oben - "notified_build_id" wird jetzt
                # ebenso erst nach dem tatsaechlichen Zeichnen markiert
                # (next_action(), Block "pending_build"), nicht schon
                # hier beim blossen Erkennen. build_id selbst muss dafuer
                # zwischengespeichert werden, da _build_popup_pending nur
                # die Kurzbeschreibung (summary) enthaelt.
                self._pending_build_id = build_id
        save_update_state(state)

    def _scroll_skip_vsync(self):
        """NEUES FEATURE (Nutzerwunsch: "Schnelles Scrollen wirkt sich
        merkbar hauptsaechlich auf HDMI aus - koennte das am Equalizer/
        der Laufschrift liegen?"): urspruenglich nur an EINER Stelle
        berechnet (der Haupt-Zeichenfunktion, siehe draw_page_items()) -
        die leichten Tick-Pfade fuer Puls/Glow (_draw_dynamic_cats(),
        _draw_dynamic_items()), Einzelschritt-Navigation
        (_draw_navigate_items()) und Songtitel-Laufschrift
        (_draw_dynamic_track_marquee()) riefen bislang IMMER das volle,
        Vsync-wartende flip_rows() auf - unabhaengig vom "Schnelles
        Scrollen"-Schalter. Auf CRT faellt das kaum auf (dort kostet
        Vsync-Warten ohnehin praktisch nichts), auf HDMI (8-17ms pro
        Aufruf, siehe fruehere Profiling-Runde) ist JEDES dieser
        Aufblitzen ein echtes, spuerbares Vsync-Warten - erklaert die
        Nutzer-Beobachtung "merkbar hauptsaechlich bei HDMI" sehr sauber.
        Gemeinsame Hilfsmethode statt fuenffacher Duplikation derselben
        Bedingung - dieselbe Logik wie am urspruenglichen Einsatzort:
        NUR wenn BEIDES zutrifft (Schalter aktiviert UND nachweislich
        noch im "gerade aktiv"-Zeitfenster) wird Vsync uebersprungen -
        im Ruhezustand bleibt es bei jedem dieser Pfade unveraendert
        beim bisherigen, sicheren Verhalten."""
        return (fast_scroll_enabled() and
               (time.monotonic() - self._last_input_time) < FAST_SCROLL_WINDOW)

    # ------------------------------------------------------------------
    # Adaptives Layout: alles wird aus der Framebuffer-Hoehe abgeleitet.
    # 1080p -> Schrift 3x, 720p -> 2x, 480p -> 1x
    # ------------------------------------------------------------------
    def layout_cats(self):
        """Layout fuer Seite 0. Rechts wird eine Artbox-Spalte reserviert,
        die das Logo/Cover des gerade markierten Systems zeigt - der
        Rest der Breite gehoert der Kategorienliste."""
        W, H = self.fb.width, self.fb.height
        s = max(1, H // 360)
        ox = W * OVERSCAN_X // 100
        oy = H * OVERSCAN_Y // 100
        rowh = 22 * s
        y0 = oy + 40 * s
        visible = max(3, (H - y0 - oy - 20 * s) // rowh)
        art_w = min(int(W * 0.34), 340)
        list_right = W - ox - art_w - 12 * s
        return {"s": s, "ox": ox, "oy": oy, "rowh": rowh,
                "y0": y0, "visible": visible,
                "art_w": art_w, "list_right": list_right}

    def layout_items(self, has_art):
        """Layout fuer Seite 1. Bei Systemen mit Boxart teilt sich der
        Platz in eine Listenspalte links und eine Boxart-Spalte rechts;
        ohne Boxart (Scripts/System/Core-Ordner) nutzt die Liste die
        volle Breite.

        NEU (siehe Begruendung bei display_name()/accent_for() weiter
        oben - dieselbe Ueberlegung): haengt AUSSCHLIESSLICH von der
        Aufloesung (fb.width/height - aendert sich waehrend einer
        Sitzung nie) und has_art (nur zwei moegliche Werte) ab -
        maximal ZWEI moegliche Ergebnisse pro Sitzung insgesamt, wurde
        aber bislang bei JEDEM Neuzeichnen (inkl. Laufschrift-/Puls-
        Ticks, bis zu 12.5x/Sekunde) komplett neu berechnet. Cache-
        Schluessel bewusst inkl. Aufloesung (nicht nur has_art), falls
        sich diese durch einen Aufloesungswechsel zur Laufzeit doch
        einmal aendern sollte - dann bleibt der alte Cache-Eintrag
        einfach ungenutzt liegen, statt eine falsche Aufloesung
        zurueckzuliefern."""
        key = (self.fb.width, self.fb.height, has_art)
        cached = self._layout_items_cache.get(key)
        if cached is not None:
            return cached
        W, H = self.fb.width, self.fb.height
        s = max(1, H // 360)
        ox = W * OVERSCAN_X // 100
        oy = H * OVERSCAN_Y // 100
        list_y = oy + 46 * s   # etwas mehr Luft zwischen Kopfzeile und Liste
        footer_y = H - oy - 13 * s
        rowh = 15 * s
        avail_w = W - 2 * ox
        list_w = int(avail_w * 0.52) if has_art else avail_w
        list_x = ox
        list_right = list_x + list_w
        visible = max(3, (footer_y - 6 * s - list_y) // rowh)
        result = {"s": s, "ox": ox, "oy": oy, "list_x": list_x,
                 "list_y": list_y, "list_right": list_right,
                 "rowh": rowh, "footer_y": footer_y, "visible": visible}
        self._layout_items_cache[key] = result
        return result

    def draw(self, message=None, prominent=False, prominent_duration=5.0):
        self._maybe_apply_pending_ra_data()
        self._sync_track_marquee()
        self._maybe_retry_ra()
        self._maybe_retry_clock()
        self._maybe_rebuild_ra_categories()
        self._maybe_rescan_for_late_mount()
        if message and prominent:
            # NEUES FEATURE (siehe Kommentar bei self._prominent_message
            # in __init__): bewusst NICHT auch noch die kleine
            # Fusszeilen-Meldung setzen (message bleibt fuer
            # draw_page_cats()/draw_page_items() unten auf None) - die
            # auffaellige Box unten uebernimmt das komplett allein,
            # sonst zeigt der Bildschirm dieselbe Information doppelt.
            self._prominent_message = message
            self._prominent_message_until = time.monotonic() + prominent_duration
            message = None
        elif message:
            # Schutzfenster setzen (siehe Kommentar bei
            # self._popup_message_until in __init__) - 2 Sekunden sind
            # grosszuegig genug, um eine kurze Meldung sicher lesen zu
            # koennen, aber kurz genug, dass die Laufschrift danach
            # zuegig wieder normal weiterlaeuft.
            self._popup_message_until = time.monotonic() + 2.0
        if self.attract_mode:
            self.draw_attract()
            return
        # Wenn ein Bestaetigungsdialog kommt (Beenden ODER - NEU, siehe
        # self.confirm_update - Update installieren), soll die Seite
        # dahinter NICHT extra geflippt werden - sonst blitzt fuer einen
        # Frame der Hintergrund ohne Dialog auf, bevor der Dialog
        # erscheint (genau das war das Flackern beim Wechseln zwischen
        # den Optionen). Nur der letzte Zeichenschritt flippt.
        any_dialog = self.confirm_quit or self.confirm_update
        if self.page == 0:
            self.draw_page_cats(message, flip=not any_dialog)
        else:
            self.draw_page_items(message, flip=not any_dialog)
        if self.confirm_quit:
            self.draw_confirm_dialog()
        elif self.confirm_update:
            # NEUES FEATURE (Nutzerwunsch, siehe
            # _start_update_install_dialog()): gleicher Dialog-Rahmen wie
            # die Beenden-Bestaetigung, nur mit eigenem Text/eigenen
            # Knopfbeschriftungen - draw_confirm_dialog() wurde dafuer um
            # optionale msg/labels-Parameter erweitert (Standardwerte
            # entsprechen exakt dem bisherigen, festen Beenden-Dialog).
            self.draw_confirm_dialog(msg=self._update_install_message,
                                     labels=[t("install_now"), t("install_later")],
                                     max_lines=3)
        elif self._prominent_message and time.monotonic() < self._prominent_message_until:
            self._draw_prominent_message()

    def _draw_prominent_message(self):
        """Auffaellige, mittig platzierte Infobox fuer wichtige,
        eigenstaendige Ankuendigungen (aktuell: "neues Update
        verfuegbar") - bewusst deutlich sichtbarer als die kleine
        Fusszeilen-Meldung, die fuer schnelle Bestaetigungen wie
        "Favorit hinzugefuegt" gedacht ist. Platzierung: unterhalb der
        Kopfzeile (auf Seite 0 direkt unter Logo + "N Kategorien"),
        auf beiden Seiten konsistent an derselben vertikalen Position,
        damit der Aufruf unabhaengig von der aktuellen Seite immer
        gleich aussieht.

        Wird NICHT von next_action()'s leichten Tick-Pfaden beruehrt
        oder ueberschrieben (die pruefen nur self._popup_message_until,
        ein komplett separater Zustand) - bleibt also stabil stehen,
        bis draw() sie nach Ablauf von self._prominent_message_until
        selbst wegzeichnet (siehe next_action()-Tick-Aufruf dafuer).

        BUGFIX (Nutzer-Rueckmeldung: "die Update-Infobox ist im CRT-
        Modus zu gross und da steht nichts drin"): text_w wurde bisher
        direkt aus der vollen Zeichenlaenge berechnet, ganz ohne
        Ruecksicht auf die tatsaechlich verfuegbare Bildschirmbreite.
        Beim kurzen Versions-Hinweis ("Update v4.5!") faellt das nicht
        auf, aber der zweite Aufrufer (build_available_popup, zeigt den
        frei formulierten LATEST_BUILD.json-"summary"-Text, der bewusst
        ein ganzer, oft laengerer Satz ist statt eines Codeworts)
        sprengte auf CRT (320px breit, s=1) die Box leicht um ein
        Vielfaches der Bildschirmbreite - box_x wurde dadurch stark
        negativ, Box UND Text landeten praktisch komplett ausserhalb
        des sichtbaren Bereichs, sichtbar blieb nur ein leerer
        Ausschnitt. Jetzt wie beim Beenden-Dialog (draw_confirm_dialog(),
        selbes Muster) wortweise umgebrochen und auf maximal 3 Zeilen
        begrenzt (_wrap() kappt eine dann immer noch zu lange letzte
        Zeile zusaetzlich mit "~") - Box bleibt dadurch auf jeder
        Aufloesung garantiert innerhalb des Bildschirms."""
        fb = self.fb
        W = fb.width
        L = self.layout_cats()
        s, oy = L["s"], L["oy"]
        text = self._prominent_message
        pad_x, pad_y = 16 * s, 10 * s
        maxc = max(10, (W - 4 * pad_x) // (8 * s))
        lines = self._wrap(text, maxc, max_lines=3)
        line_h = 12 * s
        text_w = max(len(ln) for ln in lines) * 8 * s
        box_w = min(W - 16 * s, text_w + 2 * pad_x)
        box_h = len(lines) * line_h + 2 * pad_y
        box_x = (W - box_w) // 2
        box_y = oy + 55 * s
        fb.rect_rounded(box_x, box_y, box_w, box_h, C_PANEL)
        # Rahmen: vier duenne Linien in Akzentfarbe statt einer vollen
        # zweiten rect_rounded() (die wuerde das Panel darunter komplett
        # uebermalen statt nur einen Rand zu zeigen)
        border = max(1, s // 2)
        fb.rect(box_x, box_y, box_w, border, C_ACCENT)
        fb.rect(box_x, box_y + box_h - border, box_w, border, C_ACCENT)
        fb.rect(box_x, box_y, border, box_h, C_ACCENT)
        fb.rect(box_x + box_w - border, box_y, border, box_h, C_ACCENT)
        ty = box_y + pad_y
        for ln in lines:
            tw = len(ln) * 8 * s
            fb.text(box_x + (box_w - tw) // 2, ty, ln, s, C_TEXT, C_PANEL)
            ty += line_h
        fb.flip_rows(box_y, box_h)

    def draw_attract(self):
        """Attract-Modus (Bildschirmschoner): zeigt grossflaechig ein
        zufaelliges Spiel mit Cover - startet automatisch nach
        laengerer Untaetigkeit (siehe next_action()), jede Eingabe
        beendet ihn sofort wieder (siehe run())."""
        fb = self.fb
        W, H = fb.width, fb.height
        s = max(1, H // 360)
        fb.clear((0, 0, 0))
        game = self._attract_game
        if game is None:
            fb.flip()
            return
        name, syskey, _arg = game
        accent = accent_for(syskey)

        cover_max_w = int(W * 0.5)
        cover_max_h = int(H * 0.72)
        art = None
        # BUGFIX (Nutzer-Rueckmeldung, siehe ausfuehrlicher Kommentar in
        # draw_art_panel(): kein SD-Rueckfall mehr im HD-Modus, wenn
        # keine art_hd-Datei existiert - fehlt sie, bleibt art=None und
        # es wird schlicht kein Cover gezeigt statt eines matschig
        # hochskalierten SD-Bilds).
        if H >= 720:
            hd = _art_path_in(ART_HD, syskey, name)
            art = ART.get_scaled(hd, cover_max_w, cover_max_h)
        else:
            art = ART.get_scaled(art_path(syskey, name), cover_max_w, cover_max_h)

        if art:
            aw, ah, pix = art
            ax = (W - aw) // 2
            ay = int(H * 0.06)
            pad = 6 * s
            fb.rect(ax - pad, ay - pad, aw + 2 * pad, ah + 2 * pad, accent)
            fb.blend_rect_fast(ax + 3 * s, ay + ah - 4 * s, aw, 10 * s,
                              (0, 0, 0), (0, 0, 0), 0.35)
            self.blit(ax, ay, aw, ah, pix)
            title_y = ay + ah + pad + 14 * s
        else:
            title_y = int(H * 0.4)

        title = name
        maxc = max(4, (W - 40 * s) // (16 * s))
        if len(title) > maxc:
            title = title[:max(1, maxc - 1)] + "~"
        title_w = len(title) * 16 * s
        fb.text(max(0, (W - title_w) // 2), title_y, title, 2 * s, C_TITLE, (0, 0, 0))

        sysname_w = len(syskey) * 8 * s
        fb.text(max(0, (W - sysname_w) // 2), title_y + 30 * s, syskey, s, accent, (0, 0, 0))

        hint = t("attract_hint")
        hint_w = len(hint) * 8 * s
        fb.text(max(0, (W - hint_w) // 2), H - 24 * s, hint, s, C_DIM, (0, 0, 0))
        fb.flip()

    # ------------------------------------------------------------------
    # Seite 0: Kategorien-Menue
    # ------------------------------------------------------------------
    def _perf_profiled_call(self, label, fn, args=(), threshold=0.020):
        """Gemeinsame PERF-Messhilfe fuer die zentralen Navigations-
        Zeichenpfade (draw_page_cats/_items, _draw_navigate_cats/_items).

        PERF-DIAGNOSE (Nutzer-Rueckmeldung: "das muss unter HDMI
        insgesamt fluessiger laufen, vor allem beim Wechsel rein in
        einen Ordner/zurueck UND beim reinen Scrollen" - trotz bereits
        aktiviertem "Schnelles Scrollen"; RA-Icon-Vorwaermen als eine
        konkrete Ursache bereits separat behoben, siehe Changelog):
        noch KEIN weiterer Fix, sondern gezielte Messung. Existierte
        bisher NUR fuer draw_page_items() (siehe dortige, ausfuehrliche
        Vorgeschichte: "auf echter Hardware messen" - dort gemessene
        150-250ms liessen sich in dieser Cloud-Sandbox trotz nachgebauter
        grosser Sammlungen NIE auch nur annaehernd reproduzieren,
        vermutlich schlicht die deutlich schwaechere MiSTer-ARM-CPU oder
        etwas, das nur mit echten Metadaten/RA-Daten auftritt). Jetzt
        fuer alle vier zentralen Zeichenpfade vereinheitlicht (statt die
        cProfile-Logik viermal separat zu kopieren), damit ein einziger
        DRAGEND_PROFILE=1-Lauf auf dem echten Geraet ueberall dieselbe
        Detailtiefe liefert - sowohl fuer den vollen Seitenwechsel
        (Wechsel rein/zurueck) als auch fuer einen einzelnen
        Scroll-Schritt.

        Normalbetrieb (DRAGEND_PROFILE nicht gesetzt): nur eine leichte
        Zeitmessung, Log-Zeile nur bei Ueberschreiten von threshold -
        vernachlaessigbarer Overhead. Mit DRAGEND_PROFILE=1: zusaetzlich
        ein vollstaendiges cProfile fuer genau diesen einen Aufruf, bei
        Ueberschreiten der Schwelle als "PROFILE: ..."-Zeilen mitgeloggt
        (Top 12 nach kumulativer Zeit) - zeigt beim naechsten
        Auftreten des Rucklers auf dem echten Geraet genau, WELCHE
        Funktion(en) die Zeit tatsaechlich verbrauchen, statt weiter zu
        raten (gleiches Prinzip, das beim F5-Problem frueher schon den
        Ausschlag gegeben hat)."""
        if os.environ.get("DRAGEND_PROFILE") == "1":
            import cProfile, pstats, io as _io
            _pr = cProfile.Profile()
            _pr.enable()
            _t0 = time.monotonic()
            r = fn(*args)
            _dt = time.monotonic() - _t0
            _pr.disable()
            if _dt > threshold:
                LOG("PERF %s: %.0f ms" % (label, _dt * 1000))
                _s = _io.StringIO()
                _stats = pstats.Stats(_pr, stream=_s).sort_stats("cumulative")
                _stats.print_stats(12)
                for _line in _s.getvalue().splitlines():
                    if _line.strip():
                        LOG("PROFILE: " + _line)
                _th = self.fb._textcache_hits
                _tm = self.fb._textcache_misses
                _te = self.fb._textcache_evictions
                _ttotal = _th + _tm
                _trate = (_th / _ttotal * 100) if _ttotal else 0.0
                LOG("TEXTCACHE: Treffer=%d Fehltreffer=%d Verdraengungen=%d "
                    "Trefferquote=%.1f%%" % (_th, _tm, _te, _trate))
            return r
        _t0 = time.monotonic()
        r = fn(*args)
        _dt = time.monotonic() - _t0
        if _dt > threshold:
            LOG("PERF %s: %.0f ms" % (label, _dt * 1000))
        return r

    def draw_page_cats(self, message=None, flip=True):
        return self._perf_profiled_call(
            "draw_page_cats", self._draw_page_cats_impl, (message, flip))

    def _draw_page_cats_impl(self, message=None, flip=True):
        fb = self.fb
        W, H = fb.width, fb.height
        L = self.layout_cats()
        s, ox, oy = L["s"], L["ox"], L["oy"]
        rowh, y0, visible = L["rowh"], L["y0"], L["visible"]
        self.cats_visible = visible

        fb.clear(C_BG)
        fb.text(ox, oy, "MiSTer", 3 * s, C_TITLE, C_BG)
        fb.text(ox, oy + 28 * s, t("categories", len(self.cats)), s, C_DIM, C_BG)

        # Easter Egg (Nutzerwunsch): kleine Jahreszeiten-Deko oben rechts,
        # nur am 24.12./31.12. (siehe seasonal_decoration()) - rein
        # optisch, keine Interaktion, kollidiert mit nichts anderem hier
        # oben (Kategorienliste ist links, Sysart-Box weiter unten).
        deco = seasonal_decoration()
        if deco:
            deco_text, deco_color = deco
            deco_w = len(deco_text) * 8 * s
            if deco_w <= W - 2 * ox:
                fb.text(W - ox - deco_w, oy, deco_text, s, deco_color, C_BG)

        # Songtitel als Laufschrift NEBEN dem Logo (nicht darunter,
        # sonst ueberschneidet er sich mit dem Listenbeginn). Davor
        # ein paar kleine animierte Balken (rein dekorativ, keine
        # echte Lautstaerke-Messung) als visueller "hier laeuft was"-
        # Hinweis.
        logo_w = len("MiSTer") * 8 * 3 * s
        eq_w = 0
        if self._track_mq_name and eq_effect_enabled():
            self._draw_equalizer(ox + logo_w + 10 * s, oy + 8 * s, s)
            eq_w = 4 * (3 * s + 2 * s) + 10 * s
        track_x = ox + logo_w + eq_w + 16 * s
        track_maxc = max(0, (W - ox - track_x) // (8 * s))
        if track_maxc >= 6:
            track_text = self.track_marquee_text(track_maxc)
            if track_text:
                fb.text(track_x, oy + 8 * s, track_text, s, C_DIM, C_BG)

        if self.cat_i < self.cat_scroll:
            self.cat_scroll = self.cat_i
        if self.cat_i >= self.cat_scroll + visible:
            self.cat_scroll = self.cat_i - visible + 1
        self.cat_scroll = max(0, min(self.cat_scroll,
                                     max(0, len(self.cats) - visible)))
        end = min(self.cat_scroll + visible, len(self.cats))

        list_right = L["list_right"]
        maxc = max(4, (list_right - ox) // (8 * s))
        for row, i in enumerate(range(self.cat_scroll, end)):
            self._draw_cat_row(i, row, L, maxc)
        # ENTFALLEN (Nutzerwunsch: "glow Effekt komplett raus"): hier
        # wurden bisher zwei Korrekturen gebraucht, die es AUSSCHLIESSLICH
        # wegen des Leucht-Rands gab - die Zeile ueber der Markierung
        # musste ein zweites Mal gezeichnet werden (der Glow blutete beim
        # Durchlauf von oben nach unten auf den bereits fertigen oberen
        # Nachbarn), und stand die Markierung ganz oben, musste
        # zusaetzlich die Kopfzeile freigeraeumt und neu gesetzt werden.
        # Ohne Glow bleibt jede Zeile in ihrem eigenen Bereich, beides
        # ist damit hinfaellig.

        # Artbox rechts: Logo/Cover des gerade markierten Systems
        self._draw_cat_artbox(L)

        if message:
            # BUGFIX (Nutzer-Rueckmeldung: Geheimcode-Popup erschien
            # links unten am Bildschirmrand statt zentriert): text
            # jetzt horizontal zentriert statt am linken Rand (ox)
            # ausgerichtet - deutlich auffaelliger/besser lesbar,
            # gerade fuer kurze, wichtige Meldungen wie dieses Popup.
            msg_scale = self._fit_scale(message, W - 2 * ox, s)
            msg_w = len(message) * 8 * msg_scale
            fb.text((W - msg_w) // 2, H - oy - 13 * s, message, msg_scale, C_DIM, C_BG)
        self._draw_status_bar(L)
        self._draw_search_overlay()
        if flip:
            # PERFORMANCE-FIX (Nutzer-Rueckmeldung: "im Hauptmenü wenn ich
            # schnell scrolle macht das Zeilensprünge und lagt etwas"):
            # dieser Aufruf wartete bisher IMMER auf Vsync, unabhaengig vom
            # "Schnelles Scrollen"-Schalter - alle anderen Zeichenpfade
            # (Spieleliste, Puls-/Navigations-Ticks, siehe
            # _scroll_skip_vsync()) beruecksichtigen ihn laengst. Faellt
            # besonders beim "Turbo-Sprung" (move_step > 1 bei gehaltener
            # Taste, siehe run()) ins Gewicht - der landet IMMER hier
            # (siehe _draw_navigate_cats(), die nur echte Einzelschritte
            # abdeckt), also ausgerechnet waehrend aktiven schnellen
            # Scrollens.
            fb.flip(skip_vsync=self._scroll_skip_vsync())

    def _draw_search_overlay(self):
        """Zeigt die aktuelle Sucheingabe als auffaelligen Balken oben
        im Bild, wenn der Suchmodus aktiv ist (siehe self._search_mode/
        jump_to_substring()) - bewusst als eigene, wiederverwendbare
        Methode statt dupliziertem Code in draw_page_cats() UND
        draw_page_items(), da der Suchmodus auf beiden Seiten
        funktioniert."""
        if not self._search_mode:
            return
        fb = self.fb
        W, H = fb.width, fb.height
        s = max(1, H // 360)
        label = t("search_prompt") + self._search_query + "_"
        scale = self._fit_scale(label, W - 40 * s, s + 1)
        bar_h = 22 * scale
        fb.rect(0, 0, W, bar_h, accent_for(None))
        text_w = len(label) * 8 * scale
        fb.text((W - text_w) // 2, 3 * scale, label, scale, C_BG, accent_for(None))
        # BUGFIX (Nutzer-Rueckmeldung: Suchbalken blieb nach Enter/Abbruch
        # als Bildschirm-Leiche stehen, "wird nicht wieder richtig
        # ausgeblendet"): dieser Balken wird direkt auf den Puffer
        # gemalt, OHNE ueber clear() zu laufen - der Schnellpfad in
        # _draw_page_items_impl() (siehe dort, "_fast_path") merkt sich
        # aber nur, ob SEIT dem letzten vollen Neuaufbau ueberhaupt
        # etwas anderes den Puffer veraendert hat, erkennt an diesem
        # direkten rect()/text() hier also nichts. Verlaesst der Nutzer
        # den Suchmodus (naechster Aufruf mit self._search_mode=False),
        # gibt _draw_search_overlay() dann sofort zurueck, OHNE den
        # Balken wegzuraeumen - trifft der Schnellpfad in genau diesem
        # Moment zu (Kategorie/Ordner/Trefferzahl unveraendert, was beim
        # reinen Suchen-und-Bestaetigen der Normalfall ist), bleibt der
        # Balken als Leiche stehen, da gar kein voller Neuaufbau mehr
        # passiert. Fix: full_redraw_gen bei JEDEM tatsaechlichen
        # Balken-Aufbau hochzaehlen - macht die Schnellpfad-Momentaufnahme
        # dieses Bildes fuer das NAECHSTE Bild ungueltig, erzwingt dort
        # also einen echten Neuaufbau. Kostet whaerend des aktiven
        # Suchens einen vollen Neuaufbau pro Tastendruck statt des
        # Schnellpfads - unproblematisch, da Tippen im Suchfeld ein
        # einzelner, menschlich getakteter Tastendruck ist, kein
        # durchlaufendes Scrollen (die eigentliche "keine Scroll-Lags"-
        # Vorgabe betrifft ausschliesslich Navigation, nicht die Suche).
        fb.mark_full_redraw()

    def _draw_cat_row(self, i, row, L, maxc):
        """Eine einzelne Zeile der Kategorienliste (Seite 0) zeichnen -
        aus draw_page_cats() ausgelagert, damit dieselbe Zeichenlogik
        sowohl im Hauptdurchlauf als auch fuer die nachtraegliche
        Bleed-Korrektur (siehe dort) genutzt werden kann, ohne Code zu
        duplizieren."""
        fb = self.fb
        s, ox = L["s"], L["ox"]
        rowh, y0 = L["rowh"], L["y0"]
        list_right = L["list_right"]
        name, _node, sk = self.cats[i]
        y = y0 + row * rowh
        sel = (i == self.cat_i)
        accent = accent_for(sk)
        # Easter Egg (Nutzerwunsch: Regenbogen-Cursor) - nur fuer die
        # AUSGEWAEHLTE Zeile und nur solange der Effekt noch aktiv ist
        # (siehe _on_secret_triggered()), sonst ganz normal die System-
        # Akzentfarbe wie immer.
        if sel and time.monotonic() < getattr(self, "_rainbow_cursor_until", 0):
            accent = self._rainbow_color(time.monotonic() * 2)
        else:
            accent = accent_for(sk)
        bg = self._pulsed(accent) if sel else C_BG
        if not sel:
            fb.rect(ox - 4 * s, y - 4 * s, list_right - ox + 8 * s,
                    rowh - 4 * s, C_BG)
        else:
            # GEAENDERT (Nutzerwunsch: "glow Effekt komplett raus"): der
            # markierte Eintrag hatte hier zusaetzlich drei konzentrische
            # Leucht-Ringe (glow_border_fast(), je 4 rect()-Aufrufe, also
            # 12 pro markierter Zeile). Die Markierung selbst - der
            # farbige Balken darunter - bleibt unveraendert. Weil der Glow
            # bewusst UEBER die eigene Zeile hinausragte, mussten bisher
            # an mehreren Stellen zusaetzlich die Nachbarzeilen bzw. die
            # Kopfzeile mitgezeichnet werden, damit kein Rest stehen
            # blieb; all diese Zusatzarbeit entfaellt jetzt ebenfalls
            # (siehe die entsprechenden Stellen in draw_page_cats(),
            # _draw_dynamic_cats() und _draw_navigate_cats_impl()).
            fb.rect(ox - 4 * s, y - 4 * s, list_right - ox + 8 * s,
                    rowh - 4 * s, bg)
        label = name if len(name) <= maxc else name[:max(1, maxc-1)] + "~"
        fb.text(ox, y, label, s, C_TITLE if sel else C_TEXT, bg)

    def _network_connected(self):
        """Zwischengespeicherter Netzwerkstatus, alle 5 Sekunden neu
        geprueft (nicht bei jedem einzelnen Neuzeichnen - unnoetig
        haeufige Systemaufrufe vermeiden, auch wenn die Pruefung
        selbst schon sehr guenstig ist)."""
        now = time.monotonic()
        if now >= self._net_check_next:
            self._net_status = _has_network()
            self._net_check_next = now + 5.0
        return self._net_status

    def _maybe_apply_pending_ra_data(self):
        """Uebernimmt das Ergebnis des asynchronen RA-Start-Abrufs aus
        __init__() (siehe dortiger Kommentar), sobald es eingetroffen
        ist - periodisch aus draw() geprueft, als ALLERERSTES (noch
        vor jeder eigentlichen Zeichenarbeit).

        BUGFIX (Nutzer-Rueckmeldung: "RA-Erfolgsjaeger erscheint
        manchmal gar nicht auf der Hauptseite, taucht dann ab und zu
        ploetzlich doch auf, wenn ich irgendwas mache"): baute die
        Kategorienliste bisher NUR dann neu auf, wenn der Nutzer seit
        dem Programmstart noch GAR NICHT navigiert hatte (Seite 0,
        erste Kategorie, keine Ordnertiefe) - in JEDEM anderen Fall
        (praktisch immer, sobald man auch nur einen einzigen Schritt
        navigiert, bevor der Netzwerk-Abruf durch ist) wurde
        self._ra_lookup zwar aktualisiert, self.cats aber NIE wieder
        neu aufgebaut - die Kategorie blieb dadurch fuer den Rest der
        Sitzung komplett unsichtbar, bis zufaellig eine ANDERE Stelle
        (Einstellung geaendert, Rescan, Assistent) ohnehin einen vollen
        Neuaufbau ausgeloest hat ("ab und zu ploetzlich doch auf, wenn
        ich irgendwas mache" - genau das). Jetzt wird nur noch
        self._ra_categories_dirty gesetzt; den eigentlichen (sicheren)
        Neuaufbau uebernimmt _maybe_rebuild_ra_categories() weiter
        unten, das GARANTIERT reagiert, sobald es gefahrlos moeglich
        ist - nicht mehr nur zufaellig."""
        pending = self._ra_pending_result
        if pending is None:
            return
        self._ra_pending_result = None
        lookup, fetch_ok = pending
        if lookup is not None:
            self._ra_lookup = lookup
            self._ra_fetch_ok = True
            self._ra_categories_dirty = True

    def _maybe_retry_ra(self):
        """Periodisch (aus draw(), wie _network_connected()) geprueft:
        falls RA eingerichtet ist, der letzte Abrufversuch aber
        fehlgeschlagen ist - moeglicherweise wegen einer beim Start noch
        falschen Systemuhr, siehe __init__() - wird in wachsenden
        Abstaenden (30s, 60s, 120s, 240s, gedeckelt bei 300s) ein
        Neuversuch unternommen. Netzwerk-Aufrufe laufen dabei in einem
        Hintergrund-Thread, damit die Navigation nie blockiert wird.
        Hoert nach 5 Versuchen von selbst auf (kein endloses Nachfragen,
        falls RA dauerhaft nicht erreichbar ist).

        BUGFIX (siehe _maybe_apply_pending_ra_data() fuer die
        ausfuehrliche Begruendung derselben Nutzer-Rueckmeldung): dieser
        Neuversuchspfad hat self._ra_lookup bisher aktualisiert, aber
        self.cats ueberhaupt NIE neu aufgebaut - selbst im guenstigsten
        Fall (Netzwerk beim Start nur kurz nicht bereit, erster
        Neuversuch nach 30s klappt) blieb RA-Erfolgsjaeger dadurch bis
        zum naechsten zufaelligen Neuaufbau unsichtbar. Setzt jetzt
        ebenfalls nur das Dirty-Flag - siehe
        _maybe_rebuild_ra_categories()."""
        if self._ra_fetch_ok or self._ra_retry_count >= 5:
            return
        if not ra_enabled():
            return
        now = time.monotonic()
        if now < self._ra_retry_next:
            return
        self._ra_retry_count += 1
        backoff = min(30.0 * (2 ** (self._ra_retry_count - 1)), 300.0)
        self._ra_retry_next = now + backoff
        need_ntp_first = not get_ntp_sync_ok()
        def worker():
            if need_ntp_first:
                sync_system_clock_from_ntp()
                if not get_ntp_sync_ok():
                    return   # weiterhin keine verlaessliche Uhr - beim naechsten Mal wieder
            ra_data = fetch_ra_progress_bounded(timeout=5.0)
            if ra_data is not None:
                self._ra_lookup = build_ra_lookup(ra_data)
                self._ra_fetch_ok = True
                self._ra_categories_dirty = True
        threading.Thread(target=worker, daemon=True).start()

    @staticmethod
    def _category_match_key(entry):
        """Liefert einen stabilen Vergleichsschluessel fuer einen
        self.cats-Eintrag (Anzeigename, Baumknoten, syskey) - benutzt
        von _rebuild_categories_preserving_selection(), um dieselbe
        Kategorie nach einem Neuaufbau wiederzufinden, selbst wenn sich
        ihr Anzeigename (z.B. eine mitgezaehlte Anzahl in Klammern wie
        "Sammlungen (12)") zwischenzeitlich veraendert hat. Echte
        Spiele-Systeme haben einen stabilen syskey - der reicht allein.
        Kategorien ohne syskey (Weiterspielen/Zuletzt gespielt/
        Favoriten/Sammlungen/RA-Erfolgsjaeger/Zufalls-Zock/System)
        vergleichen nur den Teil des Anzeigenamens VOR einer moeglichen
        Klammer, damit ein reiner Zaehlerwechsel nicht wie eine andere
        Kategorie aussieht."""
        name, _node, syskey = entry
        if syskey is not None:
            return ("sys", syskey)
        return ("label", name.split(" (")[0])

    def _rebuild_categories_preserving_selection(self, force_rescan=False):
        """build_categories() neu aufrufen, OHNE die Kategorien-Auswahl
        (self.cat_i) unter dem Nutzer wegzuziehen - Kategorien koennen
        beim Neuaufbau in Anzahl/Reihenfolge wechseln (z.B. wenn
        RA-Erfolgsjaeger/Sammlungen neu dazukommen oder Weiterspielen/
        Zuletzt gespielt/Favoriten je nach Zustand vorne ein-/
        ausgeblendet werden), ein reiner Index-Vergleich waere dadurch
        unzuverlaessig. Merkt sich stattdessen den _category_match_key()
        der aktuell ausgewaehlten Kategorie, baut neu auf, und sucht
        genau diesen Schluessel in der neuen Liste wieder heraus. Bleibt
        die Kategorie nicht mehr vorhanden (z.B. Favoriten leer
        geworden), faellt cat_i auf einen gueltigen Index zurueck. Nur
        fuer den Aufruf gedacht, waehrend self.page == 0 ist (siehe
        _maybe_rebuild_ra_categories()) - self.nav_path/self.item_i auf
        Seite 1 werden hier bewusst nicht angefasst.

        force_rescan (NEU, Nutzerwunsch: verlaesslichere CIFS/NAS-
        Erkennung statt einer starren Wartezeit beim Start) - an
        build_categories() durchgereicht: True erzwingt einen echten
        Festplatten-Neuscan (wie beim manuellen "Spieleliste neu
        einlesen"), statt nur den ohnehin schon vorhandenen Cache zu
        uebernehmen. Siehe _maybe_rescan_for_late_mount()."""
        old_key = None
        if 0 <= self.cat_i < len(self.cats):
            old_key = self._category_match_key(self.cats[self.cat_i])
        self.build_categories(force_rescan=force_rescan)
        if old_key is not None:
            for i, entry in enumerate(self.cats):
                if self._category_match_key(entry) == old_key:
                    self.cat_i = i
                    break
            else:
                self.cat_i = min(self.cat_i, max(0, len(self.cats) - 1))
        else:
            self.cat_i = 0

    def _maybe_rebuild_ra_categories(self):
        """Periodisch (aus draw()) geprueft: holt einen von
        _maybe_apply_pending_ra_data()/_maybe_retry_ra() hinterlegten
        "es gibt frische RA-Daten, aber self.cats ist noch nicht auf
        dem neuesten Stand"-Zustand nach, SOBALD das gefahrlos moeglich
        ist. Bewusst nur auf Seite 0 (Kategorien-Uebersicht) - befindet
        sich der Nutzer gerade IN einer Kategorie (Seite 1, evtl. tief
        verschachtelt ueber nav_path), wuerde ein Neuaufbau von
        self.cats dort erst recht fuer Verwirrung sorgen (Ordnerpfad/
        Scroll-Position koennten nicht mehr zum frisch aufgebauten Baum
        passen). Bleibt das Flag laenger stehen, wird es einfach beim
        naechsten Blick auf Seite 0 nachgeholt - GARANTIERT, nicht nur
        zufaellig wie vor diesem Fix."""
        if not getattr(self, "_ra_categories_dirty", False):
            return
        if self.page != 0:
            return
        self._ra_categories_dirty = False
        self._rebuild_categories_preserving_selection()

    def _maybe_rescan_for_late_mount(self):
        """Periodisch (aus draw(), gleiches Muster wie
        _maybe_rebuild_ra_categories()) geprueft: eigenstaendiges
        Sicherheitsnetz fuer NAS/CIFS-Nutzer, UNABHAENGIG von der "beim
        Start warten"-Option (network_wait_enabled()/
        _wait_for_network_ready() in fe/scan.py).

        NEU (Nutzer-Rueckmeldung: "das Einhaengen via CIFS funktioniert
        einwandfrei automatisch, sobald mein WLAN up and running ist -
        im Grunde hat dein Frontend hier einen Workaround fuer das
        Henne-Ei-Problem geschaffen, welches leider dauerhaft eine
        Sollbruchstelle schafft"): eine EINMALIGE, starre Wartezeit
        beim Programmstart (max. 45s) bleibt immer eine gewisse
        Sollbruchstelle, ganz gleich wie grosszuegig sie bemessen ist -
        je nach WLAN/Router kann die tatsaechliche Einhaengung mal
        laenger dauern. Statt sich nur darauf zu verlassen, prueft das
        Frontend deshalb zusaetzlich waehrend der ersten paar Minuten
        Laufzeit alle paar Sekunden ganz nebenbei (billiger Check, kein
        eigener Netzwerkverkehr - siehe _has_network_mount()), ob GERADE
        JETZT ein Netzlaufwerk auftaucht, das beim letzten Scan noch
        fehlte - und zieht dann GENAU EINMAL automatisch nach, exakt wie
        "Spieleliste neu einlesen", nur automatisch statt von Hand
        ausgeloest. Bewusst nur auf Seite 0 (Kategorien-Uebersicht) und
        ausserhalb von Suche/Beenden-Dialog ausgeloest - aus demselben
        Grund wie bei _maybe_rebuild_ra_categories() waere ein
        unangekuendigter Neuaufbau mitten in einer Kategorie oder
        Eingabe nur verwirrend; bleibt die Bedingung laenger unerfuellt,
        wird einfach beim naechsten sicheren Moment nachgeholt.

        Haengt sich NICHT dauerhaft ein: nach dem einen erfolgreichen
        Nachziehen ODER (solange noch GAR KEIN Netzlaufwerk gesehen
        wurde) spaetestens nach 5 Minuten Laufzeit (grosszuegig genug
        fuer jede realistische WLAN-Verzoegerung) ist endgueltig Schluss
        - kein dauerhafter Hintergrund-Overhead fuer die grosse
        Mehrheit ohne NAS/CIFS. Wurde dagegen bereits eine Einhaengung
        GESEHEN, aber noch nicht nachgezogen (Nutzer stand z.B. gerade
        mitten in einer Kategorie), wird NICHT mehr aufgegeben, sondern
        weiter auf den naechsten sicheren Moment gewartet - sonst
        koennten die NAS-Spiele fuer den Rest der Sitzung stumm
        verschwinden, nur weil das Zeitfenster ungluecklich lag."""
        if self._late_mount_rescan_done:
            return
        now = time.monotonic()
        if not self._late_mount_rescan_pending:
            # Phase 1: noch keine Einhaengung gesehen - regelmaessig,
            # aber zeitlich begrenzt nachsehen.
            if now >= self._late_mount_deadline:
                self._late_mount_rescan_done = True   # aufgeben, nicht mehr pruefen
                return
            if now < self._late_mount_check_next:
                return
            self._late_mount_check_next = now + 8.0
            if not _has_network_mount():
                return
            LOG("_maybe_rescan_for_late_mount: neues Netzlaufwerk erkannt")
            self._late_mount_rescan_pending = True
        # Phase 2: Einhaengung gesehen, Nachziehen steht noch aus - kein
        # weiteres Zeitlimit mehr, nur noch auf einen sicheren Moment
        # warten (billiger Flag-Check bei jedem draw()).
        if self.page != 0 or self.confirm_quit or self._search_mode:
            return
        LOG("_maybe_rescan_for_late_mount: ziehe Spieleliste automatisch nach")
        self._late_mount_rescan_done = True
        self._rebuild_categories_preserving_selection(force_rescan=True)

    def _maybe_retry_clock(self):
        """Periodisch (aus draw(), gleiches Muster wie _maybe_retry_ra())
        geprueft: falls die Systemuhr noch NICHT erfolgreich per NTP
        gesetzt wurde (NTP_SYNC_OK == False), wird in wachsenden
        Abstaenden (30s, 60s, 120s, 240s, gedeckelt bei 300s) ein
        eigenstaendiger Neuversuch unternommen - UNABHAENGIG davon, ob
        RetroAchievements eingerichtet ist.

        BUGFIX (Nutzer-Rueckmeldung: Uhrzeit war trotz korrekt
        eingestelltem Zeitzonen-Versatz falsch): der bisherige
        Neuversuch lief NUR ueber _maybe_retry_ra(), gekoppelt an
        ra_enabled() - Nutzer ohne eingerichtetes RA hatten dadurch
        ueberhaupt keinen Wiederholungsmechanismus. Schlug der
        allererste, nicht-blockierende Versuch beim Programmstart fehl
        (z.B. weil das Netzwerk in diesem Moment noch nicht bereit
        war), blieb die Uhr fuer die komplette Sitzung falsch. Jetzt
        unabhaengig davon abgesichert.

        Hoert nach 5 Versuchen von selbst auf (kein endloses
        Nachfragen, falls kein Netzwerk vorhanden ist)."""
        if get_ntp_sync_ok() or self._clock_retry_count >= 5:
            return
        now = time.monotonic()
        if now < self._clock_retry_next:
            return
        self._clock_retry_count += 1
        backoff = min(30.0 * (2 ** (self._clock_retry_count - 1)), 300.0)
        self._clock_retry_next = now + backoff
        LOG("NTP-Neuversuch %d/5" % self._clock_retry_count)
        threading.Thread(target=sync_system_clock_from_ntp, daemon=True).start()

    def _attract_enabled_cached(self):
        """Zwischengespeicherte attract_enabled()-Abfrage, alle 5
        Sekunden neu geprueft - wird sonst bei JEDEM Leerlauf-
        Durchlauf (bis zu 12x/Sekunde) erneut per Datei-Existenzpruefung
        abgefragt, obwohl sich die Einstellung praktisch nie waehrend
        des Betriebs aendert (nur ueber das System-Menue)."""
        now = time.monotonic()
        if now >= self._attract_enabled_check_next:
            self._attract_enabled_cache = attract_enabled()
            self._attract_enabled_check_next = now + 5.0
        return self._attract_enabled_cache

    def _attract_delay_cached(self):
        """Zwischengespeicherte load_attract_delay()-Abfrage - gleiches
        Muster/gleiche Begruendung wie _attract_enabled_cached()."""
        now = time.monotonic()
        if now >= self._attract_delay_check_next:
            self._attract_delay_cache = load_attract_delay()
            self._attract_delay_check_next = now + 5.0
        return self._attract_delay_cache

    def _draw_dynamic_cats(self, flip=True):
        """Leichter Zeichenpfad fuer Equalizer-/Pulsier-Ticks auf Seite 0:
        aktualisiert NUR den Equalizer-Bereich und die markierte Zeile
        (deren Glow-Farbe sich veraendert), statt die komplette Seite
        (alle Kategorienamen, Artbox) neu aufzubauen. Bei bis zu 12.5
        Ticks/Sekunde auf HDMI ein erheblicher Unterschied (~6.8ms voller
        Aufbau vs. ~1-2ms hier) - genau diese haeufigen Hintergrund-Ticks
        waren die Hauptursache fuer das gefuehlte HDMI-Lag, nicht die
        eigentliche Reaktion auf eine Eingabe selbst.

        Muss PIXELGENAU dasselbe Ergebnis liefern wie draw_page_cats()
        fuer dieselben Bereiche, sonst drohen Bildfehler - deshalb per
        Differenzvergleich gegen einen vollen Aufbau getestet.

        flip (NEU, fuer _draw_navigate_cats() - siehe dort): False zeichnet
        nur in den Speicherpuffer und liefert stattdessen den betroffenen
        Bildbereich als (y_min, y_max) zurueck (bzw. (None, None), falls
        nichts gezeichnet wurde), OHNE selbst zu flippen - derselbe
        Rueckgabe-Kontrakt wie bei _draw_dynamic_items(flip=False). Damit
        kann der Aufrufer mehrere Teil-Updates zu EINEM einzigen
        flip_rows()-Aufruf zusammenfassen (mehrere direkt hintereinander
        auf den echten Framebuffer geschriebene Teil-Updates konnten an
        anderer Stelle bereits sichtbare Zwischenbilder verursachen, siehe
        Bugfix-Kommentar in _draw_navigate_items()). Der bestehende Aufrufer
        (Puls-Tick weiter unten in next_action()) ruft weiterhin ohne
        Argument auf und verhaelt sich dadurch exakt wie bisher."""
        fb = self.fb
        H = fb.height
        L = self.layout_cats()
        s, ox, oy = L["s"], L["ox"], L["oy"]
        rowh, y0, visible = L["rowh"], L["y0"], L["visible"]
        list_right = L["list_right"]

        y_min, y_max = H, 0

        logo_w = len("MiSTer") * 8 * 3 * s
        if self._track_mq_name and eq_effect_enabled():
            eq_x, eq_y = ox + logo_w + 10 * s, oy + 8 * s
            eq_h = 10 * s
            eq_w = 4 * (3 * s + 2 * s)
            fb.rect(eq_x, eq_y, eq_w, eq_h, C_BG)
            self._draw_equalizer(eq_x, eq_y, s)
            y_min, y_max = min(y_min, eq_y), max(y_max, eq_y + eq_h)

        row = self.cat_i - self.cat_scroll
        if 0 <= row < visible:
            y = y0 + row * rowh
            name, _node, sk = self.cats[self.cat_i]
            accent = accent_for(sk)
            bg = self._pulsed(accent)
            gx, gy = ox - 4 * s, y - 4 * s
            gw, gh = list_right - ox + 8 * s, rowh - 4 * s
            # GEAENDERT (Nutzerwunsch: "glow Effekt komplett raus"): hier
            # standen zuvor die drei Leucht-Ringe, dazu eine breite
            # Randloeschung (max_p) rund um die Zeile, weil der Glow
            # ueber die eigene Zeile hinausragte - und, als Folgekosten
            # daraus, das Mitzeichnen der Zeile DARUEBER bzw. der
            # Kopfzeile bei jedem einzelnen Tick. Ohne Glow faellt das
            # alles weg: die markierte Zeile fuellt ihren eigenen
            # Bereich per rect() vollstaendig selbst, ein Ueberstand in
            # Nachbarzeilen entsteht nicht mehr.
            fb.rect(gx, gy, gw, gh, bg)
            maxc = max(4, (list_right - ox) // (8 * s))
            label = name if len(name) <= maxc else name[:max(1, maxc - 1)] + "~"
            fb.text(ox, y, label, s, C_TITLE, bg)
            y_min = min(y_min, gy)
            y_max = max(y_max, gy + gh)

        if y_max > y_min:
            if flip:
                fb.flip_rows(y_min, y_max - y_min,
                            skip_vsync=self._scroll_skip_vsync())
                return None, None
            return y_min, y_max
        return None, None

    def _bg_fill(self, x, y, w, h):
        """Einen Bereich auf den Hintergrund zuruecksetzen - wie
        fb.rect(x, y, w, h, C_BG), aber unter Beruecksichtigung einer
        eventuell aktiven Rand-Abdunkelung (VIGNETTE_ENABLED in
        fe/framebuffer.py): dort ist der Hintergrund NICHT einfarbig,
        sondern je Bildzeile leicht unterschiedlich. fb.clear(C_BG)
        (der normale Weg, den draw_page_cats() nutzt) speichert sein
        fertiges Muster bereits in fb._rowcache - hier einfach denselben
        Ausschnitt daraus wiederverwenden, statt naiv einfarbig zu
        fuellen (das erzeugte an duennen Uebergangsstellen - Artbox-
        Raendern, Zeilen-Zwischenraeumen, der Kopfzeile - einen kleinen,
        aber per Pixel-Differenzvergleich nachweisbaren Farbunterschied
        zum vollen Aufbau). Faellt auf die einfarbige Variante zurueck,
        falls noch nie geclear't wurde (Muster dann noch nicht im
        Cache)."""
        fb = self.fb
        bg_pattern = fb._rowcache.get(("bg", C_BG, fb.width, fb.height))
        if bg_pattern is None:
            fb.rect(x, y, w, h, C_BG)
            return
        x = max(0, x); y = max(0, y)
        w = min(w, fb.width - x); h = min(h, fb.height - y)
        if w <= 0 or h <= 0:
            return
        stride = fb.stride
        row_bytes = w * 4
        for yy in range(y, y + h):
            off = yy * stride + x * 4
            end = off + row_bytes
            fb.buf[off:end] = bg_pattern[off:end]

    def _draw_navigate_cats(self, old_cat_i):
        # PERF-DIAGNOSE (siehe ausfuehrlichen Kommentar bei
        # _perf_profiled_call()) - derselbe Grund, hier fuer den "beim
        # reinen Scrollen"-Fall aus derselben Nutzer-Rueckmeldung.
        return self._perf_profiled_call(
            "navigate_cats", self._draw_navigate_cats_impl, (old_cat_i,))

    def _draw_navigate_cats_impl(self, old_cat_i):
        """Leichter Zeichenpfad fuer EINEN Navigationsschritt (hoch/
        runter) auf Seite 0 (Kategorien-Hauptmenue), OHNE dass dabei
        gescrollt werden musste - Pendant zu _draw_navigate_items()
        (Seite 1) fuer die Kategorienliste.

        PERFORMANCE (Nutzer-Rueckmeldung: "im Hauptmenü wenn ich schnell
        scrolle macht das ab und zu Zeilensprünge und lagt etwas, koennte
        man das fluessiger/schneller machen?"): fuer Seite 0 gab es bisher
        UEBERHAUPT KEINEN guenstigen Teil-Redraw-Pfad - jeder einzelne
        Navigationsschritt loeste immer den kompletten draw_page_cats()
        aus (fb.clear() + jede sichtbare Zeile + Artbox + Statusleiste +
        volles Vsync-Warten), laut einer frueheren Profiling-Runde
        47-57ms auf HDMI. Bei gehaltener Taste (die Wiederholrate steigt
        ab REPEAT_INTERVAL, siehe fe/input.py) kann das mit der Eingabe-
        Wiederholung kollidieren - der zwischen zwei TATSAECHLICH
        gezeichneten Bildern sichtbare Fortschritt wirkt dadurch groesser
        als ein einzelner Schritt, sieht also wie ein Ruckler/Zeilensprung
        aus, obwohl der Cursor intern korrekt nur um 1 weiterspringt.

        Nutzt fuer die NEUE Auswahl (samt allen dortigen Sonderfaellen,
        v.a. der Kopfzeilen-Bleed-Korrektur ganz oben in der Liste) die
        bereits vorhandene, gegen einen vollen Aufbau pixelgenau getestete
        _draw_dynamic_cats() (bisher nur fuer Pulsier-Ticks genutzt) - hier
        kommt nur das dafuer noch fehlende Stueck dazu: die ALTE Zeile
        unmarkiert zuruecksetzen und die Artbox (Logo/Cover) rechts auf
        den neuen Stand bringen. WICHTIG: alle Teil-Updates sammeln ihre
        Bildbereiche nur im Speicherpuffer (kein eigenes flip_rows()) und
        werden erst ganz am Ende in EINEM einzigen flip_rows()-Aufruf auf
        den Bildschirm gebracht - mehrere einzelne, direkt hintereinander
        auf denselben echten Framebuffer geschriebene Teil-Updates haben an
        anderer Stelle bereits einmal ein sichtbares Zwischenbild verursacht
        (siehe Bugfix-Kommentar in _draw_navigate_items()), das wird hier
        von vornherein vermieden.

        Deckt bewusst NICHT jeden Fall ab (scrollen, aktiver Regenbogen-
        Cursor-Sondereffekt) - gibt dann False zurueck, Aufrufer nutzt in
        diesen Faellen den vollen, bewaehrten draw()-Pfad (gleiches Prinzip
        wie bei _draw_navigate_items())."""
        if self.page != 0:
            return False
        new_cat_i = self.cat_i
        L = self.layout_cats()
        visible = L["visible"]
        if not (self.cat_scroll <= old_cat_i < self.cat_scroll + visible):
            return False
        if not (self.cat_scroll <= new_cat_i < self.cat_scroll + visible):
            return False
        if time.monotonic() < getattr(self, "_rainbow_cursor_until", 0):
            return False

        fb = self.fb
        s, ox, oy = L["s"], L["ox"], L["oy"]
        rowh, y0 = L["rowh"], L["y0"]
        list_right = L["list_right"]
        maxc = max(4, (list_right - ox) // (8 * s))
        gx = ox - 4 * s
        gw = list_right - ox + 8 * s

        old_row = old_cat_i - self.cat_scroll
        y = y0 + old_row * rowh
        gy = y - 4 * s
        gh = rowh - 4 * s
        # Alte Zeile unmarkiert neu zeichnen - _draw_cat_row() fuellt den
        # kompletten eigenen Zeilenbereich selbst mit C_BG, ein separates
        # Freiraeumen davor ist nicht noetig.
        #
        # GEAENDERT (Nutzerwunsch: "glow Effekt komplett raus"): hier
        # stand zuvor ein breites _bg_fill() um die Zeile herum (max_p,
        # wegen des ueberstehenden Leucht-Rands) und, als Folgekosten
        # daraus, das Mitzeichnen der Zeile darueber, der Zeile darunter
        # und ggf. der Kopfzeile - bei JEDEM Navigationsschritt. Ohne
        # Glow bleibt jede Zeile in ihrem eigenen Bereich; damit
        # entfaellt das alles.
        self._draw_cat_row(old_cat_i, old_row, L, maxc)
        y_min = gy
        y_max = gy + gh

        # Neue Auswahl (markierte Zeile inkl. Glow, Equalizer, Kopfzeilen-
        # Sonderfall) - siehe Docstring oben: flip=False zeichnet nur in
        # den Puffer, ohne selbst zu flippen.
        new_y0, new_y1 = self._draw_dynamic_cats(flip=False)
        if new_y0 is not None:
            y_min = min(y_min, new_y0)
            y_max = max(y_max, new_y1)

        # ENTFALLEN (Nutzerwunsch: "glow Effekt komplett raus"): der
        # Leucht-Rand der NEUEN Auswahl ragte auch nach UNTEN in die
        # Zeile darunter hinein, weshalb diese hier zusaetzlich neu
        # gezeichnet werden musste. Ohne Glow gibt es keinen Ueberstand
        # mehr - die Korrektur ist hinfaellig.

        # Artbox rechts: Logo/Cover des jetzt markierten Systems. Vorher
        # auf den Hintergrund zuruecksetzen (draw_page_cats() erledigt das
        # sonst ueber sein fb.clear() ganz am Anfang - hier bewusst nicht,
        # sonst waere der gesamte Vorteil dieses Pfads dahin; siehe
        # _bg_fill() fuer den Grund, warum nicht einfach fb.rect(...,C_BG)),
        # sonst kann bei unterschiedlich grossen/foermigen Bildern ein Rand
        # des vorherigen Covers stehen bleiben.
        art_w = L["art_w"]
        W, H = fb.width, fb.height
        art_x0 = W - ox - art_w
        art_y0 = y0
        art_y_max = H - oy - 20 * s
        art_h = max(20, art_y_max - art_y0)
        self._bg_fill(art_x0, art_y0, art_w, art_h)
        self._draw_cat_artbox(L)
        y_min = min(y_min, art_y0)
        y_max = max(y_max, art_y0 + art_h)

        fb.flip_rows(y_min, y_max - y_min, skip_vsync=self._scroll_skip_vsync())
        return True

    def _draw_navigate_items(self, old_item_i):
        # PERF-DIAGNOSE (siehe ausfuehrlichen Kommentar bei
        # _perf_profiled_call()) - hier fuer die weitaus haeufigere
        # Item-Liste (Seite 1) statt der Kategorienliste (Seite 0).
        return self._perf_profiled_call(
            "navigate_items", self._draw_navigate_items_impl, (old_item_i,))

    def _draw_navigate_items_impl(self, old_item_i):
        """Leichter Zeichenpfad fuer EINEN Navigationsschritt (hoch/
        runter) auf Seite 1, OHNE dass dabei gescrollt werden musste:
        aktualisiert nur die alte und neue markierte Zeile (plus
        noetige Nachbarn wegen Glow-Ueberlappung, siehe
        _draw_dynamic_items()) sowie das Boxart-Panel, statt die
        komplette Seite (Hintergrund, alle anderen Zeilen, Header)
        neu aufzubauen - bei weitem der haeufigste Einzelschritt beim
        normalen Durchbrowsen einer Liste.

        Gibt True zurueck, wenn der leichte Pfad angewendet wurde,
        sonst False (Aufrufer soll dann den vollen, bewaehrten
        draw()-Pfad nutzen - z.B. bei Scrollen, Ordnerwechsel o.ae.)."""
        v = getattr(self, "view", None)
        if not v or not v["items"] or self.page != 1:
            return False
        new_item_i = self.item_i
        visible = self.items_visible
        if not (self.scroll <= old_item_i < self.scroll + visible):
            return False
        if not (self.scroll <= new_item_i < self.scroll + visible):
            return False

        # Alte Position hatte ggf. einen ueber die eigene Zeile hinaus
        # reichenden Glow-Rand (war ja vorher markiert) - erst auf den
        # Hintergrund zuruecksetzen und unmarkiert neu zeichnen, sonst
        # bleibt ein Rest des Glows sichtbar. Genau wie in
        # _draw_dynamic_items() reicht dieses Zuruecksetzen bei der
        # engen Zeilenhoehe in die NACHBARN der alten Position hinein -
        # deshalb werden alte Nachbarn (falls sichtbar) ebenfalls mit
        # aufgefrischt (per Differenzvergleich gefunden). Faellt einer
        # davon zufaellig mit der neuen Auswahl oder deren eigenen
        # Nachbarn zusammen, wird er von _draw_dynamic_items() direkt
        # danach ohnehin nochmal in der dafuer richtigen Reihenfolge
        # gezeichnet - harmlos.
        #
        # BUGFIX (uebernommen aus einer parallelen Fehlerdiagnose, siehe
        # Kopfkommentar-Changelog: leichtes Flackern beim Scrollen,
        # Zeilen wirken teilweise ueberlappend): dieser Pfad schrieb
        # bisher bis zu DREI getrennte flip_rows()-Aufrufe direkt
        # hintereinander in den echten Framebuffer (alte Zeile, neue
        # Zeile ueber _draw_dynamic_items(), Boxart-Panel). Da hier
        # direkt in /dev/fb0 geschrieben wird, konnte die Anzeige-
        # Hardware zwischen diesen einzelnen Teil-Updates kurz einen
        # inkonsistenten Zwischenzustand einlesen (alte Zeile schon
        # geloescht, neue Markierung noch nicht gezeichnet) - genau das
        # erklaert sowohl das gemeldete leichte Flackern als auch die
        # scheinbar ueberlappenden Eintraege. Fix: alle drei Teil-
        # Updates werden jetzt nur noch in den Speicherpuffer gezeichnet,
        # OHNE zwischendurch zu flippen (flip=False), und erst ganz am
        # Ende in EINEM einzigen zusammengefassten flip_rows()-Aufruf auf
        # den Bildschirm gebracht - fuer den Nutzer sieht der komplette
        # Schritt dadurch als ein einziges, atomares Update aus. (Die
        # jetzt zusaetzliche Vsync-Wartezeit in flip_rows() selbst, siehe
        # Framebuffer._wait_vsync(), verstaerkt diesen Effekt weiter.)
        fb = self.fb
        total = len(v["items"])
        # GEAENDERT (Nutzerwunsch: "glow Effekt komplett raus"): fuer die
        # ALTE Position wurden bisher DREI Zeilen neu gezeichnet (sie
        # selbst plus beide Nachbarn), weil ihr Leucht-Rand in die
        # Nachbarzeilen hineinragte und dort sonst sichtbare Reste
        # hinterlassen haette. Ohne Glow genuegt die Zeile selbst - sie
        # fuellt ihren eigenen Bereich vollstaendig.
        old_y_top, old_max_p = self._clear_row_glow_margin(old_item_i)
        regions = []
        if old_y_top is not None:
            self.draw_list_row(old_item_i)
            s, rowh = v["s"], v["rowh"]
            flip_y0 = old_y_top - old_max_p
            flip_y1 = old_y_top + rowh - 2 * s + old_max_p
            regions.append((flip_y0, flip_y1))

        new_y0, new_y1 = self._draw_dynamic_items(flip=False)
        if new_y0 is not None:
            regions.append((new_y0, new_y1))

        # Boxart-Panel fuer die neue Auswahl - zeichnet seinen
        # Hintergrund selbst (siehe draw_art_panel()), daher genuegt
        # ein einfacher erneuter Aufruf mit der neuen Auswahl.
        syskey = v.get("syskey")
        has_art = len(v["items"]) > 0 and (bool(syskey) or
                                           v["items"][0][1] == "game")

        # NEUES FEATURE ("Turbo-Scroll", Nutzervorschlag): Waehrend eines
        # schnellen Scroll-Bursts (Taste gedrueckt halten, siehe
        # _scroll_skip_vsync() - dasselbe Zeitfenster wie FAST_SCROLL_WINDOW,
        # bewusst derselbe Opt-in-Schalter wie beim Vsync-Ueberspringen)
        # wird das Boxart-/Info-Panel bewusst NICHT bei jedem einzelnen
        # Schritt neu gezeichnet. Grund: rect_rounded()/text() cachen zwar
        # die BERECHNUNG (Farben, Glyphen), nicht aber das eigentliche
        # Kopieren der fertigen Pixel in den Framebuffer - das faellt bei
        # jedem Aufruf erneut an, allen voran self.blit() fuer das Cover
        # (bei HD-Profil bis zu 360x420 Pixel, zeilenweise kopiert). Bei
        # zehn oder mehr Schritten/Sekunde beim Gedruecktalten summiert
        # sich genau dieser Kopieraufwand spuerbar.
        #
        # Das zuletzt gezeichnete Panel bleibt einfach stehen (der alte
        # Framebuffer-Inhalt wird nicht angetastet), bis der ohnehin
        # bereits vorhandene COVER_SETTLE-Mechanismus (siehe next_action():
        # ~150ms nach der letzten Eingabe, sobald wirklich Stillstand
        # herrscht) automatisch einen vollen draw_page_items()-Aufbau
        # ausloest - der zeichnet das Panel fuer die dann endgueltige
        # Auswahl ohnehin bereits vollstaendig neu, kein zusaetzlicher
        # Timer noetig. Bei normaler, langsamer Navigation (kein aktives
        # Fast-Scroll-Fenster) aendert sich am Verhalten NICHTS - das
        # Panel wird weiterhin sofort bei jedem Schritt aktualisiert, wie
        # bisher. Die Vsync-Skip-Logik selbst (_scroll_skip_vsync()) bleibt
        # unangetastet, wird hier nur gelesen.
        defer_panel = has_art and self._scroll_skip_vsync()

        if has_art and not defer_panel:
            L = self.layout_items(has_art)
            s, ox, oy = L["s"], L["ox"], L["oy"]
            list_right, footer_y = L["list_right"], L["footer_y"]
            art_x0 = list_right + 20 * s   # etwas mehr Abstand zur Boxart-Karte
            art_y0 = oy
            art_w = (self.fb.width - ox) - art_x0
            art_h = footer_y - 8 * s - art_y0
            if art_w > 20 and art_h > 20:
                item_syskey = self._item_syskey(v["items"][new_item_i], syskey)
                self.draw_art_panel(art_x0, art_w, art_y0, art_h,
                                    item_syskey, v["items"][new_item_i], s)
                regions.append((art_y0, art_y0 + art_h))

        if regions:
            y0 = min(r[0] for r in regions)
            y1 = max(r[1] for r in regions)
            fb.flip_rows(y0, y1 - y0, skip_vsync=self._scroll_skip_vsync())
        return True

    def _clear_row_glow_margin(self, item_i):
        """Den erweiterten Randbereich (bis zu max_p Pixel ueber die
        eigentliche Zeile hinaus) einer bestimmten Zeile auf den
        Hintergrund zuruecksetzen - gemeinsam genutzt von
        _draw_dynamic_items() (neue Auswahl) UND _draw_navigate_items()
        (alte Auswahl, deren Glow-Rand sonst teilweise stehen bleibt,
        wenn die Markierung zu einer anderen Zeile weiterspringt)."""
        v = self.view
        s, rowh = v["s"], v["rowh"]
        row = item_i - self.scroll
        if not (0 <= row < self.items_visible):
            return None, None
        fb = self.fb
        list_x, list_right = v["list_x"], v["list_right"]
        y = v["list_y"] + row * rowh
        y_top = y - 3 * s
        x0 = list_x - 4 * s
        rw = max(4, list_right - list_x - 2 * s)
        # GEAENDERT (Nutzerwunsch: "glow Effekt komplett raus"): war
        # vorher 3 * 2 * s - so weit ragte der Leucht-Rand ueber die
        # eigene Zeile hinaus, und genau so breit musste hier
        # freigeraeumt werden. Ohne Glow reicht der eigene Zeilenbereich.
        # Die Funktion selbst bleibt trotzdem noetig: die markierte Zeile
        # wird mit ABGERUNDETEN Ecken gezeichnet (rect_rounded()), die
        # Eckpixel ausserhalb der Rundung bleiben dabei unberuehrt und
        # muessen vorher auf den Hintergrund zurueckgesetzt werden.
        max_p = 0
        cur_bg = getattr(self, "_cur_bg", None)
        if cur_bg is None:
            fb.rect(x0 - max_p, y_top - max_p, rw + 2 * max_p,
                    rowh - 2 * s + 2 * max_p, C_BG)
        else:
            buflen = len(fb.buf)
            need = (rw + 2 * max_p) * 4
            for yy in range(max(0, y_top - max_p),
                            min(fb.height, y_top + rowh - 2 * s + max_p)):
                off = yy * fb.stride + (x0 - max_p) * 4
                end = off + need
                if end > buflen or end > len(cur_bg) or off < 0:
                    continue
                chunk = cur_bg[off:end]
                if len(chunk) == need:
                    fb.buf[off:end] = chunk
        return y_top, max_p

    def _draw_dynamic_items(self, flip=True):
        """Leichter Zeichenpfad fuer Pulsier-Ticks auf Seite 1: zeichnet
        NUR die markierte Zeile (plus direkte Nachbarn) neu, statt die
        komplette Spieleliste + Boxart-Panel neu aufzubauen.

        WICHTIG (per Differenzvergleich gegen einen vollen Aufbau
        gefunden): der Glow-Rand reicht bis zu max_p=6*s Pixel ueber die
        Zeile hinaus - bei der engen Zeilenhoehe hier (rowh, oft nur
        wenig groesser als die Zeile selbst) ueberlappt das in die
        Text-Position der NAECHSTEN Zeile hinein. Wird nur die markierte
        Zeile neu gezeichnet, bleibt der obere Rand des Nachbar-Textes
        teilweise geloescht zurueck. Deshalb werden Zeile davor/danach
        (falls sichtbar) im selben Zug mit aufgefrischt - kostet kaum
        mehr (kein Glow dort), verhindert das Artefakt aber zuverlaessig.

        BUGFIX (uebernommen aus einer parallelen Fehlerdiagnose - siehe
        Kopfkommentar-Changelog: "der obere Eintrag wird vom aktuell
        angezeigten ein wenig ueberlappt", dauerhaft sichtbar, nicht nur
        waehrend eines Uebergangs): die Zeile VOR der Markierung wurde
        bisher VOR der markierten Zeile selbst gezeichnet (um angeblich
        exakt dasselbe Ergebnis wie der volle Aufbau zu liefern) - der
        Glow-Rand der danach gezeichneten Markierung blieb dadurch
        dauerhaft sichtbar auf dem oberen Nachbarn liegen, da NICHTS ihn
        hinterher wieder uebermalt hat. Nach unten fiel das nie auf, weil
        die naechste Zeile ohnehin bereits danach gezeichnet wurde. Der
        volle Aufbau hatte GENAU dasselbe Problem - "byte-identisch"
        hiess bisher also "byte-identisch fehlerhaft". Fix: die markierte
        Zeile (samt Glow) wird jetzt IMMER ZUERST gezeichnet, beide
        Nachbarn (falls sichtbar) danach - so uebermalt der obere Nachbar
        einen eventuellen Bleed zuverlaessig mit seinem eigenen, korrekten
        Inhalt. Siehe auch die analoge Korrektur in
        _draw_page_items_impl() fuer den vollen Aufbau.

        flip=False (siehe _draw_navigate_items()/BUGFIX Flackern beim
        Scrollen): zeichnet nur in den Speicherpuffer, OHNE selbst zu
        flippen - der Aufrufer sammelt dann mehrere Teil-Updates ein und
        bringt sie in EINEM gemeinsamen flip_rows()-Aufruf auf den
        Bildschirm, statt mehrerer sichtbarer Einzelschritte. Rueckgabe
        immer (y0, y1) des betroffenen Bereichs, oder (None, None), wenn
        nichts zu zeichnen war."""
        v = getattr(self, "view", None)
        if not v or not v["items"]:
            return None, None
        s, rowh = v["s"], v["rowh"]
        row = self.item_i - self.scroll
        if not (0 <= row < self.items_visible):
            return None, None
        fb = self.fb
        total = len(v["items"])
        # GEAENDERT (Nutzerwunsch: "glow Effekt komplett raus"): bisher
        # wurden hier bei JEDEM Puls-Tick DREI Zeilen gezeichnet - die
        # markierte plus beide Nachbarn -, ausschliesslich weil der
        # Leucht-Rand in die Nachbarzeilen hineinblutete und dort sonst
        # Reste stehen geblieben waeren. Ohne Glow bleibt die Markierung
        # in ihrem eigenen Bereich: eine Zeile genuegt, und der auf den
        # Schirm zu bringende Streifen ist entsprechend schmaler.
        y_top, max_p = self._clear_row_glow_margin(self.item_i)
        self.draw_list_row(self.item_i)
        flip_y0 = y_top - max_p
        flip_y1 = y_top + rowh - 2 * s + max_p
        if flip:
            fb.flip_rows(flip_y0, flip_y1 - flip_y0,
                        skip_vsync=self._scroll_skip_vsync())
        return flip_y0, flip_y1

    def _draw_dynamic_track_marquee(self):
        """Leichter Zeichenpfad fuer die Songtitel-Laufschrift: erneuert
        NUR die eine Textzeile (Header auf Seite 0 neben dem Logo,
        Fusszeile auf Seite 1), statt die komplette Seite neu
        aufzubauen. Anders als bei der Zeilen-Markierung gibt es hier
        keinen halbtransparenten Glow-Rand und keine Nachbar-
        Ueberlappung - reiner Text auf einfarbigem oder Bild-
        Hintergrund, daher deutlich einfacher."""
        if not self._track_mq_name:
            return
        fb = self.fb
        W = fb.width
        s = max(1, fb.height // 360)

        if self.page == 0:
            L = self.layout_cats()
            ox, oy = L["ox"], L["oy"]
            logo_w = len("MiSTer") * 8 * 3 * s
            eq_w = (4 * (3 * s + 2 * s) + 10 * s) if eq_effect_enabled() else 0
            track_x = ox + logo_w + eq_w + 16 * s
            track_maxc = max(0, (W - ox - track_x) // (8 * s))
            if track_maxc < 6:
                return
            y = oy + 8 * s
            h = 8 * s
            fb.rect(track_x, y, (W - ox) - track_x, h, C_BG)
            track_text = self.track_marquee_text(track_maxc)
            if track_text:
                fb.text(track_x, y, track_text, s, C_DIM, C_BG)
            fb.flip_rows(y, h, skip_vsync=self._scroll_skip_vsync())
        else:
            # BUGFIX (siehe self._popup_message_until in __init__) -
            # Meldung UND Laufschrift teilen sich hier dieselbe Zeile
            # (footer_y) - ohne diesen Schutz wuerde eine gerade erst
            # gezeigte Meldung (z.B. Erfolgs-Popup) vom naechsten
            # faelligen Laufschrift-Tick sofort wieder ueberschrieben,
            # oft binnen unter 100ms, bevor sie ueberhaupt wahrnehmbar
            # war. Einfaches Aussetzen fuer die Dauer des
            # Schutzfensters - die Laufschrift bewegt sich in dieser
            # kurzen Zeit ohnehin kaum spuerbar, kein wahrnehmbarer
            # Nachteil fuer die Laufschrift selbst.
            if time.monotonic() < self._popup_message_until:
                return
            v = getattr(self, "view", None)
            if not v:
                return
            L = self.layout_items(bool(v.get("syskey")) or
                                  (v["items"] and v["items"][0][1] == "game"))
            ox, footer_y = L["ox"], L["footer_y"]
            foot_maxc = max(0, (W - 2 * ox) // (8 * s))
            if foot_maxc < 6:
                return
            h = 8 * s
            self._restore_row_bg(ox, footer_y, W - 2 * ox, h)
            track_display = self.track_marquee_text(foot_maxc)
            if track_display:
                fb.text(ox, footer_y, track_display, s, C_DIM)
            fb.flip_rows(footer_y, h, skip_vsync=self._scroll_skip_vsync())

    def _draw_status_bar(self, L):
        """Netzwerksymbol (nur wenn verbunden) + Uhrzeit unten rechts
        im Hauptmenue - auf derselben Zeile wie eine etwaige Status-
        meldung (die steht links), damit sich nichts ueberschneidet."""
        fb = self.fb
        W, H = fb.width, fb.height
        s, ox, oy = L["s"], L["ox"], L["oy"]
        y = H - oy - 13 * s

        clock_text = time.strftime("%H:%M")
        clock_w = len(clock_text) * 8 * s
        x = W - ox - clock_w
        fb.text(x, y, clock_text, s, C_DIM, C_BG)

        if self._network_connected():
            # Drei aufsteigende Saeulen (Signalstaerke-Optik) - rein
            # statusanzeigend ("Netzwerk vorhanden"), kein echter
            # Signalstaerke-Messwert, den liefert uns niemand.
            icon_w = 11 * s
            icon_x = x - icon_w - 6 * s
            bar_w = 3 * s
            gap = 1 * s
            base_y = y + 10 * s
            for i, bh in enumerate((4 * s, 7 * s, 10 * s)):
                bx = icon_x + i * (bar_w + gap)
                fb.rect(bx, base_y - bh, bar_w, bh, C_DIM)

    def _draw_cat_artbox(self, L):
        """Zeigt rechts neben der Kategorienliste ein Logo/Cover fuer
        das gerade markierte System (aus SYSART_BASE/<Systemkey>.art).
        Ohne passende Datei erscheint ein dezenter Platzhalter statt
        eines Fehlers."""
        fb = self.fb
        s = L["s"]
        W, H = fb.width, fb.height
        ox, oy = L["ox"], L["oy"]
        art_w = L["art_w"]
        x0 = W - ox - art_w
        y0 = L["y0"]
        y_max = H - oy - 20 * s
        box_h = max(20, y_max - y0)
        pad = 6 * s

        name, _items, syskey = self.cats[self.cat_i]
        accent = accent_for(syskey)
        art_key = _category_art_key(name, syskey)
        art = ART.get_scaled(os.path.join(SYSART_BASE, "%s.art" % art_key),
                             art_w - 2 * pad, box_h) if art_key else None
        if art:
            aw, ah, pix = art
            ax = x0 + pad + max(0, (art_w - 2 * pad - aw) // 2)
            ay = y0 + max(0, (box_h - ah) // 2)
            fb.blend_rect_fast(ax + 3 * s, ay + ah - 4 * s, aw, 10 * s,
                              C_BG, (0, 0, 0), 0.35)
            self.blit(ax, ay, aw, ah, pix)
            fb.rect(ax - 2 * s, ay - 2 * s, aw + 4 * s, 2 * s, accent)
            fb.rect(ax - 2 * s, ay + ah, aw + 4 * s, 2 * s, accent)
            fb.rect(ax - 2 * s, ay - 2 * s, 2 * s, ah + 4 * s, accent)
            fb.rect(ax + aw, ay - 2 * s, 2 * s, ah + 4 * s, accent)
        else:
            fb.rect(x0 + pad, y0, art_w - 2 * pad, box_h, C_ACCENT2)
            fb.text(x0 + pad + 4 * s, y0 + box_h // 2 - 4 * s,
                    t("no_artwork_1"), s, C_DIM, C_ACCENT2)
            fb.text(x0 + pad + 4 * s, y0 + box_h // 2 + 5 * s,
                    t("no_artwork_2"), s, C_DIM, C_ACCENT2)

    # ------------------------------------------------------------------
    # Seite 1: Liste + (falls vorhanden) grosse Boxart-Spalte
    # ------------------------------------------------------------------
    def draw_page_items(self, message=None, flip=True):
        # NEU (Nutzerwunsch: "auf echter Hardware messen" - Sandbox
        # erreichte die realen 150-250ms nicht annaehernd, egal wie
        # gross die nachgebaute Sammlung war - moeglicherweise einfach
        # deutlich schwaechere ARM-CPU, moeglicherweise etwas, das sich
        # nur mit ECHTEN Metadaten/RA-Daten zeigt). Statt weiter zu
        # raten: optionales, per Umgebungsvariable einschaltbares
        # Profiling direkt auf dem echten Geraet - zeigt beim naechsten
        # Log genau, WELCHE Funktion(en) die Zeit tatsaechlich
        # verbrauchen, nach demselben Prinzip, das beim F5-Problem am
        # Ende den Ausschlag gegeben hat (echte Daten statt Vermutung).
        # Bewusst NICHT dauerhaft aktiv (cProfile kostet selbst Zeit,
        # wuerde die normale Bedienung spuerbar verlangsamen) - nur
        # wenn DRAGEND_PROFILE=1 in der Umgebung gesetzt ist.
        #
        # GEAENDERT (Nutzer-Rueckmeldung: "muss unter HDMI insgesamt
        # fluessiger laufen, auch beim Wechsel rein/zurueck und beim
        # reinen Scrollen"): dieselbe Mess-/Profiling-Logik ist jetzt in
        # _perf_profiled_call() ausgelagert und wird zusaetzlich auch von
        # draw_page_cats()/_draw_navigate_cats()/_draw_navigate_items()
        # genutzt (siehe dortiger Kommentar) - hier unveraendert derselbe
        # Schwellenwert (40ms) wie zuvor.
        return self._perf_profiled_call(
            "draw_page_items", self._draw_page_items_impl,
            (message, flip), threshold=0.040)

    def _draw_page_items_impl(self, message=None, flip=True):
        fb = self.fb
        W, H = fb.width, fb.height
        name, _root_node, syskey = self.cats[self.cat_i]
        items = self._display_items()
        total = len(items)
        # Bei "Zuletzt gespielt" ist der Kategorie-Systemkey None (die
        # Liste mischt mehrere Systeme) - trotzdem soll die Boxart-
        # Spalte erscheinen, da jeder einzelne Eintrag seinen eigenen
        # Systemkey mitbringt (siehe _item_syskey()).
        has_art = total > 0 and (bool(syskey) or
                                 (items and items[0][1] == "game"))

        L = self.layout_items(has_art)
        s, ox, oy = L["s"], L["ox"], L["oy"]
        list_x, list_y = L["list_x"], L["list_y"]
        list_right, rowh = L["list_right"], L["rowh"]
        footer_y, visible = L["footer_y"], L["visible"]
        self.items_visible = visible

        art_key = _category_art_key(name, syskey)
        # NEUES FEATURE (Nutzerwunsch: "bg-Ordner rausnehmen, glaube der
        # laggt" - siehe system_bg_enabled() in fe/settings.py). Nutzt
        # bewusst denselben None-Pfad, der ohnehin schon existiert (fuer
        # Kategorien ohne art_key) - kein neuer Sonderfall noetig, self.
        # _cur_bg=None ist bereits ueberall sicher gehandhabt.
        self._cur_bg = (BG.get(art_key, fb)
                        if art_key and system_bg_enabled() else None)
        _tb = time.monotonic()
        # NEU (Nutzerwunsch: "HDMI-Modus muss fluessiger laufen" - echtes
        # Profiling zeigte den vollen Pufferaufbau/-kopie (47-57ms bei
        # JEDEM Bild) als groessten verbliebenen Einzelposten, deutlich
        # groesser als z.B. der Schimmer-Effekt (6-8ms), der zuerst als
        # Verdaechtiger geprueft wurde). Beim reinen Scrollen INNERHALB
        # derselben Liste (gleiche Kategorie, gleicher Ordnerpfad,
        # gleiche Eintragsanzahl, gleicher Hintergrund) aendert sich am
        # Hintergrund nichts - der volle Neuaufbau ist dann komplett
        # ueberfluessig, da Kopfzeile/Eintragsanzahl unveraendert bleiben
        # und Zeilen sowie Cover-Panel ohnehin bei JEDEM Bild ihren
        # kompletten eigenen Bereich neu fuellen (siehe draw_list_row()/
        # draw_art_panel() - beide bereits entsprechend abgesichert).
        #
        # SICHERHEIT (wichtig, da "alle Funktionen muessen weiter
        # funktionieren" ausdruecklich gefordert war): fb.full_redraw_gen
        # (siehe fe/framebuffer.py) wird bei JEDEM vollstaendigen
        # Neuaufbau hochgezaehlt, unabhaengig von hier - lief zwischen-
        # durch irgendeine ANDERE Bildschirmseite (Hilfe, WoT, Bestaeti-
        # gungsdialog, Attract-Modus, ...), stimmt die eigene gemerkte
        # Generation nicht mehr mit fb.full_redraw_gen ueberein, und der
        # schnelle Pfad wird automatisch NICHT genommen - dann laeuft
        # wie bisher immer der volle, sichere Neuaufbau.
        _fast_key = (self.cat_i, tuple(self.nav_path), total, art_key, W, H)
        _fast_path = (getattr(self, "_pgi_fast_key", None) == _fast_key and
                      getattr(self, "_pgi_fast_gen", -1) == fb.full_redraw_gen)
        self._pgi_fast_taken = _fast_path
        if _fast_path:
            pass   # Hintergrund unveraendert - kompletter Neuaufbau nicht noetig
        elif self._cur_bg is not None:
            fb.buf[:] = self._cur_bg
            fb.mark_full_redraw()
            self._pgi_fast_key = _fast_key
            self._pgi_fast_gen = fb.full_redraw_gen
        else:
            fb.clear(C_BG)
            self._pgi_fast_key = _fast_key
            self._pgi_fast_gen = fb.full_redraw_gen
        self._perf_bg = time.monotonic() - _tb

        # Breadcrumb: Kategorie + aktueller Ordnerpfad (falls in einen
        # Unterordner gewechselt wurde), z.B. "SNES / 1 US-A-E".
        #
        # BUGFIX (Nutzer-Rueckmeldung: Kopfzeile schnitt bei langen
        # Pfaden mitten im Wort ab, z.B. "SAMMLUNGEN / DIESES JAHR ~" -
        # seit die Kategorienamen selbst eine Anzahl in Klammern tragen
        # (siehe _count_tree_items()), sind die Pfade im Schnitt laenger
        # geworden, das Problem also haeufiger sichtbar): passt der
        # VOLLE Pfad nicht, wird jetzt statt eines mitten abgeschnittenen
        # Textes nur noch der AKTUELLE (tiefste) Ordnername gezeigt -
        # weniger Kontext, aber lesbar statt kryptisch abgehackt. Nur
        # wenn selbst dieser einzelne Name noch zu lang ist, wird
        # (jetzt an einer sinnvolleren Stelle) doch noch gekuerzt.
        full_header = name if not self.nav_path else name + " / " + " / ".join(self.nav_path)
        full_header = full_header.upper()
        header_maxc = max(4, (list_right - ox) // (16 * s))
        header_scale = 2 * s
        if len(full_header) <= header_maxc:
            header = full_header
        else:
            # BUGFIX (Nutzer-Rueckmeldung: selbst der einzelne, tiefste
            # Ordnername war auf CRT manchmal noch zu lang, z.B. "MEGA
            # DRIVE" -> "MEGA DR~" - kaum noch lesbar): statt weiter
            # mitten im Wort abzuschneiden, wird die Schriftgroesse
            # jetzt so weit verkleinert, dass der komplette Name passt -
            # konsistent mit der Loesung bei anderen Titeln (z.B.
            # draw_core_choice_screen()). Eine vollwertige Laufschrift
            # waere hier ebenfalls denkbar (Nutzerwunsch geaeussert),
            # ist aber ein groesserer, eigener Umbau (neuer Tick-
            # Zustand, Reset bei jeder Navigation) - bewusst nicht in
            # dieser Sammel-Aenderung mit erledigt.
            leaf = (self.nav_path[-1] if self.nav_path else name).upper()
            header = leaf
            header_scale = self._fit_scale(leaf, list_right - ox, 2 * s)
        fb.text(ox, oy, header, header_scale, C_TITLE)
        fb.text(ox, oy + 22 * s, t("entries", total), s, C_DIM)

        self.view = {"list_x": list_x, "list_y": list_y,
                    "list_right": list_right, "rowh": rowh, "s": s,
                    "items": items, "syskey": syskey}

        if self.item_i < self.scroll:
            self.scroll = self.item_i
        if self.item_i >= self.scroll + visible:
            self.scroll = self.item_i - visible + 1
        self.scroll = max(0, min(self.scroll, max(0, total - visible)))
        end = min(self.scroll + visible, total)

        # BUGFIX (per Pixelvergleich schneller/langsamer Pfad gefunden,
        # mehrere Anlaeufe): der neue schnelle Pfad (siehe Kommentar
        # beim Hintergrund weiter oben) nimmt fuer NICHT markierte
        # Zeilen an, deren Hintergrund sei bereits korrekt - stimmt
        # aber NUR, wenn seit dem letzten ECHTEN Neuaufbau nichts
        # anderes an dieser Bildschirm-POSITION sass. Aendert sich die
        # SCROLL-Position, rutscht die vorher markierte Zeile (samt
        # ihrem Schimmer-Rand, siehe glow_border_fast() - der ragt bis
        # zu 6*s Pixel ueber die Zeile hinaus, nach ALLEN Seiten) an
        # eine ANDERE Bildschirm-Position.
        #
        # Ein erster Versuch, gezielt nur die ALTE markierte Position
        # (+Nachbarn, +Schimmer-Rand) zu restaurieren, ist zweimal
        # fehlgeschlagen: Rand-Ueberlappung frisst sich in nicht
        # mitverwaltete Nachbarzeilen, und selbst eine breitere,
        # randlose Zeilengruppe hat die Differenz nur verschoben statt
        # beseitigt - die genaue Nachverfolgung ist fehleranfaelliger
        # als der Performance-Gewinn wert ist. Stattdessen die simple,
        # robuste Loesung: beim schnellen Pfad wird die KOMPLETTE
        # Listenspalte (nicht der ganze Bildschirm!) einmal restauriert -
        # das macht jede Row-Position garantiert wieder "frisch", genau
        # wie ein echter clear() es fuer den ganzen Bildschirm tut, nur
        # auf die Listenspalte begrenzt. Spart weiterhin die Kosten fuer
        # Cover-Panel-Bereich, Kopf-/Fusszeile und Raender, ohne die
        # Fehleranfaelligkeit der Positions-genauen Variante.
        #
        # Rand (10*s, grosszuegig ueber die glow_border_fast()-
        # Reichweite hinaus) rundum die Liste mit dazu - dort liegt
        # keine andere verwaltete Flaeche (nur Rand-/Vignette-
        # Hintergrund bzw. der freie Zwischenraum zur Kopfzeile/
        # Fusszeile), ein Uebergriff dorthin ist also unbedenklich.
        # Der Abstand Kopfzeile->list_y betraegt 46*s minus der
        # Kopfzeilen-Hoehe (~30*s) = ca. 16*s freier Zwischenraum -
        # der 10*s-Rand bleibt also sicher innerhalb dieser Luecke.
        # Deckt den vom Schimmer-Rand seitlich UND oben/unten (bei der
        # ersten/letzten sichtbaren Zeile) ueberragten Bereich ab
        # (jeweils per Pixelvergleich mit unterschiedlichen Scroll-
        # Sequenzen als verbliebene Differenzen gefunden).
        if getattr(self, "_pgi_fast_taken", False):
            _lm = 10 * s
            self._restore_row_bg(list_x - _lm, list_y - _lm,
                                 (list_right - list_x) + 2 * _lm,
                                 visible * rowh + 2 * _lm)

        _tr = time.monotonic()
        for idx in range(self.scroll, end):
            # BUGFIX (Nutzer-Rueckmeldung: "beim Scrollen durch meine
            # NES-Sammlung auf HDMI fuehlt es sich immer noch laghaft
            # an" - echtes Profiling auf echter Hardware zeigte
            # fb.rect() als Hauptkosten, 37 Aufrufe pro Bildaufbau bei
            # 17-18 sichtbaren Zeilen). Ursache gefunden: bg_fresh war
            # bisher NUR True, wenn ein Bild-Hintergrund kopiert wurde
            # (self._cur_bg is not None) - der GENAUSO gueltige Fall
            # "gerade eben fb.clear(C_BG) aufgerufen" (kein Bild
            # verfuegbar, einfarbiger Hintergrund) wurde dabei NICHT
            # als "frisch" erkannt, obwohl auch clear() den KOMPLETTEN
            # Puffer (inklusive aller Zeilenbereiche) bereits mit der
            # exakt gleichen Farbe fuellt, die draw_list_row() fuer
            # nicht markierte Zeilen sonst extra nochmal zeichnet -
            # bei JEDER einzelnen der 17-18 sichtbaren Zeilen komplett
            # redundant. bg_fresh=True gilt jetzt fuer BEIDE Faelle
            # (direkt nach fb.buf[:]=... ODER fb.clear() in diesem
            # Durchlauf) - draw_list_row() selbst wurde entsprechend
            # um einen dritten Zweig ergaenzt (siehe dort).
            self.draw_list_row(idx, bg_fresh=True)
        # BUGFIX (uebernommen aus einer parallelen Fehlerdiagnose - siehe
        # Kopfkommentar-Changelog): der obige Durchlauf zeichnet die
        # Zeilen in AUFSTEIGENDER Reihenfolge - die markierte Zeile (samt
        # ihrem absichtlich etwas ueber die eigene Zeile hinausragenden
        # Glow-Rand, siehe draw_list_row()/glow_border_fast()) wird dabei
        # NACH ihrem oberen Nachbarn gezeichnet. Der Glow blendet dabei
        # direkt auf den bereits fertigen oberen Nachbarn - und NICHTS
        # zeichnet ihn danach nochmal darueber, der Bleed bleibt also
        # dauerhaft sichtbar (nicht nur kurz waehrend eines Redraws).
        # Fix: die Zeile direkt UEBER der Markierung (falls sichtbar)
        # wird hier einmal mit vollem Hintergrund-Restore (bg_fresh=False)
        # neu gezeichnet - malt einen eventuellen Bleed zuverlaessig weg,
        # ohne den schnellen bg_fresh-Pfad fuer alle anderen Zeilen im
        # Hauptdurchlauf zu verlangsamen.
        #
        # GEAENDERT (Nutzer-Rueckmeldung: "beim Scrollen fuehlt es sich
        # immer noch laghaft an" - echtes Profiling zeigte redundante
        # rect()-Aufrufe pro Zeile als Hauptkosten, siehe bg_fresh=True
        # weiter oben). Der urspruengliche Kommentar "Nach unten faellt
        # das nie auf, weil die naechste Zeile im selben Durchlauf
        # ohnehin erst DANACH gezeichnet wird und den Bleed automatisch
        # uebermalt" stimmte nur, WEIL bisher jede einzelne Zeile ihren
        # Hintergrund individuell neu gezeichnet hat - genau das war der
        # jetzt behobene, teure Teil. Ohne dieses "Nebenbei-Uebermalen"
        # blutet der Glow jetzt genauso sichtbar nach UNTEN wie zuvor
        # schon nach oben (per Differenzmessung zweier Screenshots vor/
        # nach der Optimierung bestaetigt, Zeile 678 betroffen) - deshalb
        # jetzt symmetrisch: auch die Zeile direkt UNTER der Markierung
        # (falls sichtbar) wird einmal mit vollem Hintergrund-Restore
        # neu gezeichnet.
        # ENTFALLEN (Nutzerwunsch: "glow Effekt komplett raus"): hier
        # wurden bisher die Zeile UEBER und die Zeile UNTER der
        # Markierung ein zweites Mal gezeichnet (mit vollem
        # Hintergrund-Restore), weil der Leucht-Rand der markierten Zeile
        # ueber die eigene Zeile hinausragte und auf beide Nachbarn
        # blutete. Ohne Glow gibt es keinen Ueberstand mehr - beide
        # Zusatz-Durchgaenge sind hinfaellig.
        self._perf_rows = time.monotonic() - _tr
        self._perf_nrows = end - self.scroll

        if has_art:
            # Die Spalte beginnt jetzt auf Hoehe der Kopfzeile (oy) statt
            # erst auf Hoehe der Liste (list_y) - der Header nutzt nur
            # den linken Teil der Zeile, rechts daneben blieb bisher ein
            # ungenutzter Streifen bis zur Liste. Das Cover bekommt so
            # spuerbar mehr Platz nach oben.
            art_x0 = list_right + 20 * s   # etwas mehr Abstand zur Boxart-Karte
            art_y0 = oy
            art_w = (W - ox) - art_x0
            art_h = footer_y - 8 * s - art_y0
            if art_w > 20 and art_h > 20:
                item_syskey = self._item_syskey(items[self.item_i], syskey)
                _ta = time.monotonic()
                self.draw_art_panel(art_x0, art_w, art_y0, art_h,
                                    item_syskey, items[self.item_i], s)
                self._perf_art = time.monotonic() - _ta

        # ABSICHERUNG fuer den neuen schnellen Pfad oben: dieser Bereich
        # (Nachricht ODER Musiktitel) kann sich AUCH bei reinem Scrollen
        # unabhaengig aendern (z.B. wechselt der Song, waehrend man
        # gerade browst) - anders als Kopfzeile/Eintragsanzahl, die bei
        # gleicher Kategorie stabil bleiben. Ohne diese explizite
        # Wiederherstellung koennte bei einem kuerzeren neuen Text ein
        # Rest des vorherigen, laengeren Textes sichtbar bleiben, wenn
        # der volle Bildschirm-Neuaufbau übersprungen wurde. Kostet nur
        # eine schmale Zeile, nicht den ganzen Bildschirm - vernachlaessigbar,
        # selbst wenn der volle Neuaufbau ohnehin schon lief.
        self._restore_row_bg(ox, footer_y, W - 2 * ox, 8 * s)
        if message:
            # BUGFIX (Nutzer-Rueckmeldung: Geheimcode-Popup erschien
            # links unten am Bildschirmrand statt zentriert) - gleicher
            # Fix wie in draw_page_cats().
            msg_scale = self._fit_scale(message, W - 2 * ox, s)
            msg_w = len(message) * 8 * msg_scale
            fb.text((W - msg_w) // 2, footer_y, message, msg_scale, C_DIM)
        else:
            # Songtitel als Laufschrift in der Fusszeile - bleibt so
            # an derselben Stelle sichtbar, egal ob/wie viel Platz das
            # Boxart-Panel gerade braucht.
            foot_maxc = max(0, (W - 2 * ox) // (8 * s))
            if foot_maxc >= 6:
                track_display = self.track_marquee_text(foot_maxc)
                if track_display:
                    fb.text(ox, footer_y, track_display, s, C_DIM)
        self._draw_search_overlay()
        if flip:
            _tf = time.monotonic()
            # NEUES FEATURE (Nutzerwunsch: "kann man das Vsync-Warten
            # beim Scrollen weglassen? Will ich probieren" - siehe
            # ausfuehrliche Erklaerung/Risiko-Abwaegung bei flip() in
            # fe/framebuffer.py). NUR wenn BEIDES zutrifft: der Schalter
            # ist aktiviert UND wir befinden uns nachweislich noch im
            # "gerade aktiv am Scrollen"-Fenster (dieselbe Zeitspanne
            # wie COVER_SETTLE) - im Ruhezustand bleibt Vsync IMMER
            # aktiv, kein Tearing-Risiko beim blossen Betrachten.
            _skip_vsync = self._scroll_skip_vsync()
            fb.flip(skip_vsync=_skip_vsync)
            _fdt = time.monotonic() - _tf
        else:
            _fdt = 0.0
        _bg = getattr(self, "_perf_bg", 0); _rw = getattr(self, "_perf_rows", 0)
        _ar = getattr(self, "_perf_art", 0); _nr = getattr(self, "_perf_nrows", 0)
        if (_bg + _rw + _ar + _fdt) > 0.1:
            LOG("PERF split: bg=%.0f rows=%.0f(%d) art=%.0f flip=%.0f ms"
                % (_bg * 1000, _rw * 1000, _nr, _ar * 1000, _fdt * 1000))
        self._perf_art = 0

    def draw_confirm_dialog(self, msg=None, labels=None, max_lines=2):
        """Beenden-Bestaetigung (Standardaufruf ohne Argumente):
        ueberlagert die aktuelle Seite mit einem kleinen Dialog. Links
        waehlt 'Ja', Rechts waehlt 'Nein' (Standardauswahl), Enter
        bestaetigt die Auswahl. ESC/B im Dialog bricht sofort ab
        (sicherer Standard).

        ERWEITERT (Nutzerwunsch: Update-Installieren-Abfrage) - msg/
        labels/max_lines optional, damit derselbe Dialograhmen auch fuer
        den "Update jetzt installieren?"-Dialog wiederverwendet werden
        kann (siehe self.draw()), statt die komplette Geometrie-/Zeichen-
        Logik ein zweites Mal zu duplizieren. Ohne Argumente identisches
        Verhalten wie zuvor.

        BUGFIX (Nutzer-Rueckmeldung: "Frontend beenden funktioniert
        nicht" - ein echtes frontend.log zeigte reproduzierbar eine
        lange Folge aus AUSSCHLIESSLICH "down"+"ok"-Eingaben, OHNE ein
        einziges "left"/"right" dazwischen: der Dialog oeffnete sich,
        wurde per "ok" bestaetigt - aber da nie zur "Ja"-Option
        gewechselt wurde, bestaetigte das jedes Mal nur die
        vorausgewaehlte "Nein"-Option, der Dialog schloss sich wieder,
        OHNE dass das Frontend tatsaechlich beendet wurde. Fuer den
        Nutzer sah das aus wie "das Fenster schliesst sich wieder, ich
        kann das Frontend damit nicht verlassen" - technisch hat der
        Dialog aber die ganze Zeit korrekt funktioniert, es war nur nie
        sichtbar/klar genug, dass ueberhaupt erst eine Auswahl noetig
        ist. Jetzt zusaetzlich ein sichtbarer Hinweistext im Dialog
        selbst (analog zum bereits bestehenden core_choice_hint bei
        draw_core_choice_screen()) - siehe auch
        _confirm_dialog_toggle() fuer den zugehoerigen zweiten Teil des
        Fixes (hoch/runter schalten jetzt GENAUSO wie links/rechts
        zwischen den beiden Optionen um)."""
        fb = self.fb
        W, H = fb.width, fb.height
        s = max(1, H // 360)
        if msg is None:
            msg = t("quit_confirm")
        maxc = max(10, (W - 40 * s) // (8 * s))
        lines = self._wrap(msg, maxc, max_lines=max_lines)
        if labels is None:
            labels = [t("yes"), t("no")]
        hint = t("confirm_dialog_hint")
        hint_s = max(1, s - 1)

        line_h = 12 * s
        btn_h = 16 * s
        btn_w = max(len(l) for l in labels) * 8 * s + 16 * s
        gap = 14 * s
        pad = 12 * s
        hint_h = 10 * hint_s

        text_w = max(len(ln) for ln in lines) * 8 * s
        buttons_w = btn_w * 2 + gap
        hint_w = len(hint) * 8 * hint_s
        box_w = min(W - 16 * s, max(text_w, buttons_w, hint_w) + 2 * pad)
        box_h = pad + len(lines) * line_h + hint_h + gap + btn_h + pad
        x0 = (W - box_w) // 2
        y0 = (H - box_h) // 2

        fb.rect(x0, y0, box_w, 2 * s, C_ACCENT)
        fb.rect(x0, y0 + 2 * s, box_w, box_h - 2 * s, C_PANEL)

        ty = y0 + pad
        for ln in lines:
            tw = len(ln) * 8 * s
            fb.text(x0 + (box_w - tw) // 2, ty, ln, s, C_TITLE, C_PANEL)
            ty += line_h

        hw = len(hint) * 8 * hint_s
        fb.text(x0 + (box_w - hw) // 2, ty, hint, hint_s, C_DIM, C_PANEL)

        bx = x0 + (box_w - buttons_w) // 2
        by = y0 + box_h - pad - btn_h
        for i, label in enumerate(labels):
            sel = (self.confirm_choice == i)
            bg = C_ACCENT if sel else C_ACCENT2
            fb.rect(bx, by, btn_w, btn_h, bg)
            tw = len(label) * 8 * s
            fb.text(bx + (btn_w - tw) // 2, by + 4 * s, label,
                    s, C_TITLE if sel else C_TEXT, bg)
            bx += btn_w + gap
        fb.flip()

    def draw_list_row(self, idx, bg_fresh=False):
        """Eine Listenzeile zeichnen. Die markierte Zeile zeigt bei
        Ueberlaenge einen Laufschrift-Ausschnitt des vollen Namens.
        Die Boxart-Spalte liegt seit v1.8 NEBEN der Liste statt darueber,
        darum muss hier keine Zeile mehr wegen Ueberlappung ausgeblendet
        werden.

        bg_fresh=True NUR, wenn direkt zuvor der GESAMTE Puffer frisch aus
        dem Hintergrundbild kopiert wurde (siehe _draw_page_items_impl())
        - dann steht an dieser Stelle ohnehin schon der Hintergrund, die
        Wiederherstellung darunter waere reine Verschwendung. Bei jeder
        Teil-Neuzeichnung (Puls-Takt, Laufschrift, Einzelschritt-
        Navigation) bleibt es beim Standardwert False, da der Puffer dort
        noch Reste vom letzten Zeichenschritt enthalten kann."""
        fb = self.fb
        v = self.view
        list_x, list_right = v["list_x"], v["list_right"]
        rowh, s = v["rowh"], v["s"]
        row = idx - self.scroll
        y = v["list_y"] + row * rowh
        y_top = y - 3 * s

        sel = (idx == self.item_i)
        item_syskey = self._item_syskey(v["items"][idx], v.get("syskey"))
        accent = accent_for(item_syskey)
        bg = self._pulsed(accent) if sel else C_BG
        x0 = list_x - 4 * s
        rw = max(4, list_right - list_x - 2 * s)
        need = rw * 4
        sel_radius = 3 * s
        cur_bg = getattr(self, "_cur_bg", None)
        if bg_fresh:
            # Voller Redraw: der Puffer wurde gerade erst KOMPLETT frisch
            # etabliert - entweder durch Kopie eines Bild-Hintergrunds
            # (cur_bg is not None) ODER durch fb.clear(C_BG) (kein Bild
            # verfuegbar, einfarbig - cur_bg is None). BEIDE Faelle
            # bedeuten: der Zeilenhintergrund steht an dieser Stelle
            # bereits korrekt im Puffer - die Zeile NICHT nochmal
            # Zeile-fuer-Zeile wiederherstellen (das war der teure, hier
            # redundante Teil, siehe Aufrufstelle weiter oben). Nur die
            # Auswahl braucht noch ihr farbiges Feld obendrauf.
            if sel:
                fb.rect_rounded(x0, y_top, rw, rowh - 2 * s, bg, sel_radius)
        elif cur_bg is not None:
            # Listenstreifen aus dem Hintergrundbild wiederherstellen -
            # hart abgesichert: nie eine falsche Byte-Anzahl schreiben,
            # sonst verschiebt sich der GESAMTE Framebuffer-Puffer.
            buflen = len(fb.buf)
            cur_bg_len = len(cur_bg)
            for yy in range(max(0, y_top), min(fb.height, y_top + rowh - 2 * s)):
                off = yy * fb.stride + x0 * 4
                end = off + need
                if end > buflen or end > cur_bg_len or off < 0:
                    continue
                chunk = cur_bg[off:end]
                if len(chunk) != need:
                    continue
                fb.buf[off:end] = chunk
            if sel:
                fb.rect_rounded(x0, y_top, rw, rowh - 2 * s, bg, sel_radius)
        else:
            if sel:
                fb.rect_rounded(x0, y_top, rw, rowh - 2 * s, bg, sel_radius)
            else:
                fb.rect(x0, y_top, rw, rowh - 2 * s, C_BG)

        # GEAENDERT (Nutzerwunsch: "glow Effekt komplett raus"): hier
        # standen drei konzentrische Leucht-Ringe um die markierte Zeile
        # (glow_border_fast(), je 4 rect()-Aufrufe - also 12 zusaetzliche
        # rect()-Aufrufe pro markierter Zeile, bei jedem Bildaufbau und
        # bei jedem Puls-/Navigations-Tick). Die abgerundete
        # Markierungsflaeche selbst bleibt unveraendert bestehen. Da der
        # Glow absichtlich ueber die eigene Zeile hinausragte, mussten
        # bisher zusaetzlich beide Nachbarzeilen mitgezeichnet werden -
        # diese Zusatzarbeit entfaellt damit ebenfalls (siehe
        # _draw_page_items_impl(), _draw_navigate_items_impl() und
        # _draw_dynamic_items()).

        full = v["items"][idx][0]
        item_kind = v["items"][idx][1]
        # Nutzerwunsch: der abschliessende "/" bei Ordner-Eintraegen
        # (z.B. "Anzeige & Sound/") sieht in der Liste unschoen aus -
        # NUR hier fuers Zeichnen entfernt (lokale Kopie von full,
        # NICHT der zugrundeliegende Wert in v["items"]/_display_items()
        # selbst) - das Stream-Overlay (stream_state()) und der
        # Favoriten-/Durchgespielt-Abgleich weiter unten nutzen
        # weiterhin die unveraenderten Rohdaten mit "/", da das
        # Overlay per "endet auf /" erkennt, dass ein Eintrag ein
        # Ordner ist und dafuer kein Cover anfragt (siehe Kommentar
        # bei stream_overlay.html im Aenderungsprotokoll).
        if item_kind == "folder" and full.endswith("/"):
            full = full[:-1]
        # Markierung nur bei echten Spielen, per Namen im bereits
        # geladenen Speicher-Cache nachgeschlagen (kein Datei-Zugriff
        # hier - das waere bei haeufigem Neuzeichnen ein echtes
        # Performance-Problem).
        is_fav = item_kind == "game" and full in self._favorites_set
        is_done = item_kind == "game" and hasattr(self, "_completed_set") \
            and full in self._completed_set
        prefix = ("* " if is_fav else "") + ("V " if is_done else "")
        maxc = (list_right - list_x - 8 * s) // (8 * s) - len(prefix)
        mq_off = None      # != None: markierte Zeile laeuft als Laufschrift
        if sel:
            # Markierte Zeile: voller Name, bei Bedarf als Laufschrift
            if len(full) > maxc:
                mq_off = min(self.mq_off, max(0, len(full) - maxc))
                label = full[mq_off:mq_off + maxc]
            else:
                label = full
        else:
            label = display_name(full)
            if len(label) > maxc:
                # BUGFIX (Nutzer-Rueckmeldung anhand eines Screenshots:
                # "The Legend of Zelda - A Link to t~" - mitten im Wort
                # abgeschnitten): schneidet jetzt an der letzten
                # Wortgrenze VOR der Grenze, statt stur bei maxc-1 zu
                # kappen - "A Link to t~" wird so zu "A Link~" statt
                # ein Wortfragment stehen zu lassen. Nur wenn sich
                # dadurch nicht MEHR als 40% der verfuegbaren Breite
                # verschenken wuerde (sehr kurze erste Woerter bei
                # extrem schmaler Spalte) - sonst lieber die alte,
                # einfache Zeichen-Grenze als Rueckfall.
                cut = maxc - 1
                space_pos = label.rfind(" ", 0, cut)
                if space_pos > cut * 0.6:
                    cut = space_pos
                label = label[:max(1, cut)] + "~"
        label = prefix + label
        if mq_off is not None:
            # PERFORMANCE-FIX (siehe ausfuehrliche Begruendung bei
            # Framebuffer.text_window()): die Laufschrift zeigt immer
            # einen Ausschnitt DESSELBEN Titels - jeder Ausschnitt war
            # fuer den Text-Cache bisher ein neuer Schluessel und damit
            # ein garantierter Fehltreffer alle 0.18s. Jetzt wird der
            # volle Titel einmal gerendert und nur noch ein Fenster
            # daraus geblittet. Ein eventuelles Praefix (Favoriten-Stern/
            # Durchgespielt-Haken) wird davor separat gezeichnet - es ist
            # nur ein bis vier Zeichen lang und dauerhaft im Cache, und
            # da jedes Zeichen eine feste Breite hat (keine
            # Unterschneidung), ergibt das exakt dasselbe Bild wie das
            # bisherige Zeichnen von praefix+ausschnitt am Stueck.
            if prefix:
                fb.text(list_x, y, prefix, s, C_TEXT, bg)
            fb.text_window(list_x + len(prefix) * 8 * s, y, full,
                           mq_off, maxc, s, C_TEXT, bg)
        else:
            fb.text(list_x, y, label, s, C_TEXT if sel else C_DIM, bg)
        return y

    def marquee_needed(self):
        v = getattr(self, "view", None)
        if not v or self.page != 1 or not v["items"]:
            return False
        s = v["s"]
        label, kind, _arg = v["items"][self.item_i]
        is_fav = kind == "game" and label in self._favorites_set
        is_done = kind == "game" and hasattr(self, "_completed_set") \
            and label in self._completed_set
        prefix_len = (2 if is_fav else 0) + (2 if is_done else 0)
        maxc = (v["list_right"] - v["list_x"] - 8 * s) // (8 * s) - prefix_len
        return len(label) > maxc

    def marquee_tick(self):
        """WICHTIG (Bugfix): frueher OHNE eigene Zeitbremse - rueckte bei
        JEDEM Aufruf der aeusseren Schleife um ein Zeichen vor, nicht
        nach tatsaechlich verstrichener Zeit. Solange das Zeichnen selbst
        teuer war (vor v1.62/v1.63), bremste das die effektive Geschwin-
        digkeit automatisch aus. Seit die Ticks viel billiger sind, laeuft
        die aeussere Schleife auf CRT nahe ihrem theoretischen Maximum
        (bis 100x/Sekunde ueber pulse_interval=0.01) - die Laufschrift
        wurde dadurch ungewollt sehr schnell (bis zu 100 Zeichen/Sekunde
        statt der beabsichtigten ~5.5 Zeichen/Sekunde, die dem 0.18s-
        Kandidaten in next_action() entsprechen). Auf HDMI (langsamerer
        Grundtakt) fiel das kaum auf, auf CRT sehr deutlich - passt genau
        zur Nutzer-Rueckmeldung. Jetzt mit derselben Zeitbremse wie
        _eq_tick()/_pulse_tick()."""
        now = time.monotonic()
        if now < self._mq_tick_next:
            return
        self._mq_tick_next = now + 0.18
        v = self.view
        s = v["s"]
        maxc = (v["list_right"] - v["list_x"] - 8 * s) // (8 * s)
        full = v["items"][self.item_i][0]
        max_off = len(full) - maxc
        if self.mq_pause > 0:
            self.mq_pause -= 1
            if self.mq_pause == 0 and self.mq_off >= max_off:
                self.mq_off = 0            # zurueck zum Anfang
                self.mq_pause = 4
        elif self.mq_off < max_off:
            self.mq_off += 1
            if self.mq_off >= max_off:
                self.mq_pause = 6          # am Ende kurz stehenbleiben
        y = self.draw_list_row(self.item_i)
        self.fb.flip_rows(y - 3 * v["s"], v["rowh"],
                          skip_vsync=self._scroll_skip_vsync())

    def marquee_reset(self):
        self.mq_off = 0
        self.mq_pause = 4
        self._mq_tick_next = 0.0

    def _restore_row_bg(self, x, y, w, h):
        """Stellt einen einzelnen, schmalen Zeilenbereich des Hintergrunds
        wieder her (aus self._cur_bg, falls ein Bild-Hintergrund aktiv
        ist, sonst aus der GLEICHEN zwischengespeicherten Vorlage, die
        auch fb.clear() verwendet - siehe unten) - OHNE den kompletten
        Bildschirm neu aufzubauen. Extrahiert aus der bereits
        vorhandenen, bewaehrten Logik der Musiktitel-Laufschrift (siehe
        _sync_track_marquee()) in eine gemeinsame Stelle, damit
        _draw_page_items_impl() beim NEUEN schnellen Pfad (siehe
        dortiger Kommentar) denselben, bereits bewaehrten Ansatz fuer
        die Fusszeile UND fuer die Listenspalte nutzen kann.

        BUGFIX (per Pixelvergleich gefunden): urspruenglich fuellte der
        einfarbige Fall per fb.rect(x, y, w, h, C_BG) - das ignoriert
        den Vignette-Effekt (dezente Randabdunkelung, siehe
        VIGNETTE_ENABLED in fe/framebuffer.py), den fb.clear() fuer den
        KOMPLETTEN Bildschirm anwendet. Das erzeugte einen sichtbaren,
        harten Bruch zwischen der wiederhergestellten Flaeche (flach)
        und dem Rest des Bildschirms (mit Vignette) - ueber 260.000
        abweichende Pixel im Test, verteilt ueber die ganze Liste.
        Jetzt wird stattdessen dieselbe zwischengespeicherte Vorlage
        (fb._rowcache) verwendet, die fb.clear() selbst aufbaut und
        wiederverwendet - Zeile fuer Zeile herauskopiert, genau wie
        beim Bild-Hintergrund-Fall."""
        fb = self.fb
        cur_bg = getattr(self, "_cur_bg", None)
        if cur_bg is None:
            cur_bg = fb._rowcache.get(("bg", C_BG, fb.width, fb.height))
        if cur_bg is None:
            # Vorlage (noch) nicht vorhanden (sollte im schnellen Pfad
            # eigentlich nie vorkommen, da der einen vorherigen echten
            # clear()-Aufruf voraussetzt) - sicherer Rueckfall auf die
            # einfache, flache Fuellung statt eines Fehlers.
            fb.rect(x, y, w, h, C_BG)
            return
        buflen, need = len(fb.buf), w * 4
        for yy in range(max(0, y), min(fb.height, y + h)):
            off = yy * fb.stride + x * 4
            end = off + need
            if end > buflen or end > len(cur_bg) or off < 0:
                continue
            chunk = cur_bg[off:end]
            if len(chunk) == need:
                fb.buf[off:end] = chunk

    def _sync_track_marquee(self):
        """Bei Songwechsel den Laufschrift-Zustand des Titels
        zuruecksetzen - wird vor jedem Zeichnen aufgerufen."""
        name = self.music.current_track_name() if hasattr(self, "music") \
            else None
        if name != self._track_mq_name:
            self._track_mq_name = name
            self.track_mq_off = 0
            self.track_mq_pause = 4

    def track_marquee_text(self, maxc):
        """Ausschnitt des aktuellen Songtitels fuer die gegebene
        Zeichenbreite - voller Titel, falls er passt."""
        name = self._track_mq_name
        if not name:
            return None
        if len(name) <= maxc:
            return name
        off = min(self.track_mq_off, len(name) - maxc)
        return name[off:off + maxc]

    def _track_marquee_needs_scroll(self, maxc):
        # NEUES FEATURE (Nutzerwunsch: "Musik-Laufschrift haette ich auch
        # gerne noch ein und ausschaltbar"): einziger Pruefpunkt, den
        # sowohl next_action() (Aufwach-/Tick-Steuerung) als auch der
        # eigentliche Tick-Aufruf (_track_marquee_tick(), siehe next_action())
        # konsultieren, bevor ueberhaupt weitergescrollt wird - bei
        # deaktiviertem Schalter also einfach IMMER False, unabhaengig
        # von der Titellaenge. self.track_mq_off bleibt dadurch dauerhaft
        # bei 0 (siehe _sync_track_marquee() bei jedem Songwechsel) -
        # track_marquee_text() zeigt weiterhin den (Anfang des) Songtitel(s),
        # nur eben statisch statt scrollend.
        if not track_marquee_enabled():
            return False
        name = self._track_mq_name
        return bool(name) and len(name) > maxc

    def _track_marquee_tick(self, maxc):
        """Versatz weiterschieben (mit Pause an den Enden) - gedrosselt
        ueber _track_tick_next. Auflösungsabhaengig: auf CRT laeuft es
        ueber einen kuerzeren Takt (0.15s statt 0.35s, wie beim
        Equalizer - draw() ist dort so guenstig, dass es nicht ins
        Gewicht faellt). Auf HDMI bleibt der Takt bei 0.35s (kein
        zusaetzliches Neuzeichnen), stattdessen ruecken pro Tick 2
        Zeichen statt 1 weiter - verdoppelt die gefuehlte Geschwindig-
        keit, ohne die Redraw-Haeufigkeit zu erhoehen."""
        now = time.monotonic()
        if now < self._track_tick_next:
            return False
        is_crt = self.fb.height < 400
        interval = 0.15 if is_crt else 0.1
        step = 1 if is_crt else 2
        self._track_tick_next = now + interval
        name = self._track_mq_name
        max_off = max(0, len(name) - maxc)
        if self.track_mq_pause > 0:
            self.track_mq_pause -= 1
            if self.track_mq_pause == 0 and self.track_mq_off >= max_off:
                self.track_mq_off = 0
                self.track_mq_pause = 4
        elif self.track_mq_off < max_off:
            self.track_mq_off = min(max_off, self.track_mq_off + step)
            if self.track_mq_off >= max_off:
                self.track_mq_pause = 6
        return True

    def _pulse_factor(self):
        """Aktueller Helligkeits-Multiplikator (0.90..1.0) fuer die
        pulsierende Markierung - sinusfoermig. Zykluslaenge
        auflösungsabhaengig: auf CRT viel kuerzer (0.8s statt 3.2s),
        da schnelleres Abfragen allein (v1.42-46) nichts mehr brachte,
        sobald man haeufiger abfragt als sich der (quantisierte) Wert
        UeBERHAUPT aendern kann - die zugrundeliegende Bewegung selbst
        muss schneller werden, nicht nur die Abtastrate."""
        is_crt = self.fb.height < 400
        period = 0.8 if is_crt else 1.0
        elapsed = time.monotonic() - self._pulse_t0
        return 0.90 + 0.10 * (0.5 + 0.5 * math.sin(elapsed * 2 * math.pi / period))

    def _pulsed(self, rgb):
        # NEUES FEATURE (Nutzerwunsch: "wenn wir den Schimmer-Effekt
        # rausnehmen wuerde das noch was bringen?"): bei Deaktivierung
        # (siehe pulse_effect_enabled() in fe/settings.py) einfach die
        # volle Helligkeit zurueckgeben (entspricht dem Spitzenwert des
        # bisherigen Pulses, f=1.0) - eine feste, aber weiterhin klar
        # erkennbare Hervorhebung, ohne die laufende Neuberechnung/
        # das wiederholte Zeichnen, die die Animation braucht.
        if not pulse_effect_enabled():
            return rgb
        f = self._pulse_factor()
        # Auf feste Stufen runden statt eines fein-kontinuierlichen
        # Wertes - sonst erzeugt praktisch jeder Aufruf eine LEICHT
        # andere Farbe. Der Glyphen-Cache der Framebuffer-Klasse
        # schluesselt ueber die Hintergrundfarbe (siehe _glyph_row) -
        # bei einer staendig neuen Farbe traf der Cache nie, die
        # markierte Zeile wurde bei JEDER Navigation komplett neu
        # gerendert (auf HDMI wegen der groesseren Glyphen spuerbar
        # langsamer) UND der Cache wuchs dabei unbegrenzt weiter, da
        # alte Farbvarianten nie wiederverwendet wurden. Auf HDMI
        # bleiben es 20 Stufen (Cache-Treffer bleiben dort wichtig),
        # auf CRT (wo draw() ohnehin <1ms kostet, Cache-Treffer also
        # kaum ins Gewicht fallen) 60 Stufen fuer feinere Abstufung -
        # zusammen mit dem kuerzeren Zyklus oben macht das den
        # Farbwechsel auf CRT spuerbar lebendiger.
        levels = 60 if self.fb.height < 400 else 20
        f = round(f * levels) / levels
        return tuple(min(255, int(c * f)) for c in rgb)

    def _pulse_tick(self):
        """True, wenn seit dem letzten Aufruf genug Zeit vergangen ist,
        um eine neue Pulsier-Stufe zu zeigen. Auflösungsabhaengig: auf
        CRT genauso flott wie der Equalizer (0.01s), da draw() dort
        durchgehend <1ms kostet - sonst wirkt die Markierung neben dem
        schnellen Equalizer traege/nachhinkend. Auf HDMI bewusst bei
        0.9s belassen (unangetastet), um den in v1.39 entschaerften
        Eingabestau nicht zu riskieren - nutzt dort weiterhin das
        ohnehin vorhandene ~1s-Idle-Aufwachen in next_action() mit."""
        now = time.monotonic()
        if now < self._pulse_tick_next:
            return False
        interval = 0.01 if self.fb.height < 400 else 0.08
        self._pulse_tick_next = now + interval
        return True

    def _eq_tick(self):
        """Wie _pulse_tick(), aber fuer die Equalizer-Balken. Takt ist
        auflösungsabhaengig: auf CRT (klein, draw() kostet dort schon
        gemessen meist <1ms) darf es extrem flott pulsieren (0.01s -
        dieselbe sichere Untergrenze wie bei REPEAT_INTERVAL fuer die
        Navigation) - auf HDMI bleibt es bei 0.35s, da dort jedes
        zusaetzliche Neuzeichnen wieder Richtung Eingabe-Stau geht
        (siehe REPEAT_INTERVAL-Drosselung in v1.39)."""
        now = time.monotonic()
        if now < self._eq_tick_next:
            return False
        interval = 0.01 if self.fb.height < 400 else 0.08
        self._eq_tick_next = now + interval
        return True

    def _draw_equalizer(self, x, y, s):
        """Kleine animierte Balken neben der Now-Playing-Anzeige - rein
        dekorativ (mpg123 liefert uns keine echte Lautstaerke), nutzt
        eine Zeit-basierte Sinuskurve pro Balken statt Zufallszahlen
        (deterministisch, kein eigener Zustand noetig). Schwingungs-
        frequenz auflösungsabhaengig: auf CRT deutlich schneller, da
        bei der kleinen Balkenhoehe (h_max) nur wenige Pixel-Stufen
        moeglich sind - schnelleres Abfragen allein (v1.42-46) half ab
        einem Punkt nicht mehr weiter, die Bewegung selbst musste
        schneller werden."""
        fb = self.fb
        now = time.monotonic()
        bar_w = 3 * s
        gap = 2 * s
        h_max = 10 * s
        col = (224, 182, 74)
        freq = 9.0 if self.fb.height < 400 else 7.0
        for i in range(4):
            phase = now * freq + i * 1.7
            frac = 0.35 + 0.65 * (0.5 + 0.5 * math.sin(phase))
            bh = max(2 * s, int(h_max * frac))
            bx = x + i * (bar_w + gap)
            fb.rect(bx, y + h_max - bh, bar_w, bh, col)

    def _enter_attract_mode(self):
        """Attract-Modus starten - waehlt ein zufaelliges Spiel. Findet
        sich gar kein Spiel (z.B. komplett leere Sammlung), wird die
        Leerlauf-Uhr zurueckgesetzt, statt bei jedem Tick erneut
        erfolglos zu versuchen."""
        pool = self._attract_games_pool()
        if not pool:
            self._last_input_time = time.monotonic()
            return
        idle_for = time.monotonic() - self._last_input_time
        LOG("Attract-Modus startet nach %.1fs Leerlauf (Schwelle: %ds)"
            % (idle_for, self._attract_delay_cached()))
        self.attract_mode = True
        self._attract_game = random.choice(pool)
        self._attract_change_next = time.monotonic() + ATTRACT_CHANGE_SECONDS
        self.draw()

    def _advance_attract(self):
        """Naechstes zufaelliges Spiel im Attract-Modus - vermeidet,
        wenn moeglich, direkt zweimal hintereinander dasselbe."""
        pool = self._attract_games_pool()
        if not pool:
            self.attract_mode = False
            return
        if len(pool) > 1:
            choices = [g for g in pool if g != self._attract_game]
            self._attract_game = random.choice(choices) if choices else pool[0]
        else:
            self._attract_game = pool[0]
        self._attract_change_next = time.monotonic() + ATTRACT_CHANGE_SECONDS
        self.draw()

    def next_action(self):
        """Wie read_action, treibt aber nebenbei die Laufschrift(en) UND
        die Musikwiedergabe (naechster Song bei Bedarf) an. Blockiert
        nie unbegrenzt, damit Musik und Laufschrift auch ohne
        Tasteneingabe rechtzeitig weiterlaufen."""
        while True:
            self._sync_track_marquee()
            # Grobe, aber ausreichende Breitenschaetzung fuer die
            # Track-Laufschrift (echte Spaltenbreite kennt erst
            # draw()) - reicht, um zu wissen ob ueberhaupt gescrollt
            # werden muss.
            track_needs = self._track_marquee_needs_scroll(24)
            need_mq = self.marquee_needed()
            # Aufwach-Zeit = das KLEINSTE aller gerade relevanten
            # Intervalle, nicht eine Prioritaetsreihenfolge - sonst
            # wuerde z.B. der 0.18s-Takt der Laufschrift den viel
            # schnelleren 0.025s-Equalizer-Takt ausbremsen (das genau
            # war der Bug: "elif" liess den Equalizer nie eigenstaendig
            # feuern, solange die Laufschrift aktiv war - praktisch
            # immer der Fall bei echten Songnamen).
            eq_interval = 0.01 if self.fb.height < 400 else 0.08
            pulse_interval = 0.01 if self.fb.height < 400 else 0.08
            if self.attract_mode:
                # Im Attract-Modus reicht ein grobes ~1s-Aufwachen,
                # um rechtzeitig das naechste Spiel zu zeigen.
                timeout = 1.0
            else:
                candidates = [pulse_interval]
                if need_mq or track_needs:
                    candidates.append(0.18)
                if self._track_mq_name:
                    candidates.append(eq_interval)
                timeout = min(candidates)
            act = self.inp.read_action(timeout=timeout)
            if act is not None:
                # SICHERHEITSNETZ CRT-Wechsel (siehe die ausfuehrliche
                # Begruendung weiter unten im Idle-Zweig sowie bei
                # mark_crt_pending_confirm() in fe/settings.py): JEDE echte
                # Eingabe - egal welche - ist der Beweis, dass das Bild
                # ankommt UND bedienbar ist. Sofort hier abklemmen (nicht
                # erst im Idle-Zweig unten warten), sonst wuerde eine
                # spaetere, ganz normale Lesepause von >= CRT_CONFIRM_
                # TIMEOUT Sekunden faelschlich als "kein Bild" gewertet,
                # obwohl CRT laengst bestaetigt ist.
                if crt_pending_confirm():
                    clear_crt_pending_confirm()
                    self._crt_confirm_handled = True
                    self._prominent_message = None   # Hinweisbox nicht
                                                      # unnoetig weiter
                                                      # anzeigen - CRT ist
                                                      # ja jetzt bestaetigt
                if self.attract_mode:
                    # Erste Eingabe beendet NUR den Attract-Modus -
                    # wird nicht zusaetzlich als normale Navigation
                    # verarbeitet (uebliches Bildschirmschoner-
                    # Verhalten: aufwecken statt gleich handeln).
                    self.attract_mode = False
                    self._last_input_time = time.monotonic()
                    self.draw()
                    self.music.tick()
                    continue
                self._last_input_time = time.monotonic()
                self._settled_redrawn = False
                if need_mq:
                    self.marquee_reset()
                return act

            # SICHERHEITSNETZ CRT-Wechsel (Nutzerwunsch: "wie soll er da
            # wieder rauskommen, wenn jemand ohne CRT im CRT-Modus landet?"
            # - siehe ausfuehrliche Begruendung bei mark_crt_pending_confirm()
            # in fe/settings.py, warum eine echte Sperre VORHER nicht robust
            # baubar ist). Wird nur EINMAL pro Sitzung behandelt (getattr-
            # Ein-mal-Schalter, gleiches Muster wie _ra_prewarm_started
            # weiter unten). idle_for misst hier bewusst ab self.
            # _last_input_time - genau derselbe Zeitpunkt, den run() setzt,
            # sobald das Menue tatsaechlich sichtbar/bedienbar ist (siehe
            # dortiger Kommentar) - startet die Uhr also nicht schon
            # waehrend Boot-Animation/Scan.
            if (not getattr(self, "_crt_confirm_handled", False)
                    and crt_pending_confirm()):
                if not crt_menu_active():
                    # Zwischenzeitlich (z.B. manuell ueber das Systemmenue)
                    # schon wieder auf HDMI zurueckgestellt - Markierung nur
                    # noch aufraeumen, nichts weiter zu tun.
                    clear_crt_pending_confirm()
                    self._crt_confirm_handled = True
                elif time.monotonic() - self._last_input_time >= CRT_CONFIRM_TIMEOUT:
                    LOG("CRT-Sicherheitsnetz: %ds keine Eingabe seit dem "
                        "Wechsel in den CRT-Modus - automatischer "
                        "Ruecksprung auf HDMI" % CRT_CONFIRM_TIMEOUT)
                    clear_crt_pending_confirm()
                    self._crt_confirm_handled = True
                    if toggle_crt_menu() is not None:
                        os.system("sync; reboot")
                        # KEIN return hier: next_action() darf laut eigenem
                        # Vertrag niemals None zurueckgeben (siehe die
                        # anderen Idle-Zweige unten, die ebenfalls einfach
                        # durchlaufen statt zurueckzukehren) - der Reboot
                        # selbst braucht ohnehin noch einen Moment, bis er
                        # tatsaechlich greift, ein paar weitere Schleifen-
                        # durchlaeufe hier sind harmlos.

            # RA-Hintergrund-Vorwaermen (Nutzerwunsch, siehe
            # _prewarm_ra_achievements()): EINMAL pro Sitzung starten,
            # sobald wirklich Leerlauf herrscht - bewusst UNABHAENGIG
            # davon, ob der visuelle Attract-Modus selbst eingeschaltet
            # ist (self._attract_enabled_cached()), da es hier nur um
            # Leerlauf-Erkennung geht, nicht um die Diashow. getattr()-
            # Ein-mal-Schalter statt einer neuen __init__-Zuweisung -
            # gleiches, bereits etablierte Muster wie bei
            # self._ra_core_choice (siehe dortiger Kommentar zur
            # Reihenfolge-Lehre).
            if (not getattr(self, "_ra_prewarm_started", False)
                    and ra_enabled() and self._ra_lookup
                    and time.monotonic() - self._last_input_time > self._attract_delay_cached()):
                self._ra_prewarm_started = True
                threading.Thread(target=self._prewarm_ra_achievements,
                                 daemon=True).start()

            # Update-Pruefung (Nutzerwunsch): der eigentliche Start des
            # Hintergrund-Threads (_check_for_update_background()) ist
            # umgezogen nach run(), direkt beim Sichtbarwerden des Menues
            # (Nutzerwunsch: "sofort im Hauptmenue", nicht erst nach
            # Leerlauf) - siehe dortiger Kommentar. Hier wird weiterhin nur
            # das FERTIGE Ergebnis abgeholt und gezeichnet, unabhaengig
            # davon, ob gerade echter Leerlauf herrscht oder nicht.
            pending_update = getattr(self, "_update_popup_pending", None)
            if pending_update:
                self._update_popup_pending = None

                # BUGFIX (Nutzer-Rueckmeldung: "keine Info, dass ein
                # Update verfuegbar ist"): draw(message=...) verwirft
                # die Meldung komplett, wenn self.attract_mode gerade
                # aktiv ist (siehe draw(): "if self.attract_mode:
                # self.draw_attract(); return" - message wird dabei nie
                # erreicht). Update-Check UND Attract-Modus loesen beide
                # bei EXAKT demselben Leerlauf-Schwellenwert aus - da der
                # Update-Check ein Netzwerkaufruf im Hintergrund ist
                # (braucht Zeit bis zum Ergebnis), ist der Attract-Modus
                # so gut wie immer schon aktiv, BEVOR das Ergebnis
                # ueberhaupt vorliegt. Fix: Attract-Modus hier explizit
                # verlassen (wie durch eine echte Eingabe), bevor die
                # Meldung gezeichnet wird - sonst kam sie nie sichtbar
                # an, obwohl der Check laengst erfolgreich war. (Der
                # urspruenglich HIER VOR dem Fix stehende erste, vom Fix
                # selbst schon als "eigentlich ueberfluessig" dokumentierte
                # draw()-Aufruf ist jetzt entfernt - genau wie beim Build-
                # Update-Hinweis direkt darunter, der denselben Fix ohne
                # diese Dopplung uebernommen hatte.)
                if self.attract_mode:
                    self.attract_mode = False
                self._last_input_time = time.monotonic()
                # NEUES FEATURE (Nutzerwunsch: "Update-Info sehe ich nicht -
                # ueberschneidet sich das mit dem Boot-Logo?", dann
                # weiter praezisiert: "soll sofort im Hauptmenue
                # eingeblendet werden, wenn ein Update verfuegbar ist, fuer
                # 2-3 Sekunden"): keine Ueberschneidung mit dem Boot-Logo
                # gefunden - der eigentliche Grund war zunaechst die kleine,
                # nur 2s sichtbare Fusszeilen-Meldung (draw(message=...)
                # ohne prominent=True), dann (Zwischenstand) noch der
                # Leerlauf-Schwellenwert (_attract_delay_cached()), der den
                # Update-Check ueberhaupt erst startete - der Hinweis kam
                # dadurch fruehestens nach etlichen Sekunden Leerlauf an,
                # nicht "sofort". Der Update-Check-Thread wird jetzt direkt
                # in run() gestartet, sobald das Menue sichtbar/bedienbar
                # ist (siehe dortiger Kommentar) - dieser Codeblock hier
                # (next_action()-Idle-Zweig) bleibt unveraendert die Stelle,
                # die das Ergebnis abholt und zeichnet, sobald der
                # Hintergrund-Thread fertig ist; da next_action() auch ohne
                # echten Leerlauf alle paar hundert Millisekunden neu
                # abgefragt wird (siehe Aufwach-Zeitberechnung oben), taucht
                # die Meldung praktisch sofort nach Abschluss des
                # Netzwerk-Abrufs auf. prominent_duration=3.0 statt der
                # Standard-5s (siehe draw()) - eigens auf den gewuenschten
                # 2-3-Sekunden-Rahmen verkuerzt; der Build-Update-Hinweis
                # ("Neue Fixes") direkt darunter behaelt bewusst die
                # laengeren 5s, da dort kein entsprechender Wunsch geaeussert
                # wurde.
                #
                # ERWEITERUNG (Nutzer-Rueckmeldung: "koennen wir das
                # Update-Popup wenn die Info kommt gleich eine Abfrage
                # hinzufuegen, ob man jetzt das Update installieren will
                # oder spaeter?"): die bisherige rein passive, nach 2-3s
                # von selbst verschwindende Meldung (self.draw(message=...,
                # prominent=True, ...) siehe oben) reichte dafuer nicht -
                # ersetzt durch einen echten Ja/Nein-Dialog (gleiches
                # Grundmuster wie die Beenden-Bestaetigung, siehe
                # self.confirm_quit/draw_confirm_dialog()), der so lange
                # sichtbar bleibt, bis der Nutzer aktiv "Jetzt" oder
                # "Spaeter" waehlt (siehe _start_update_install_dialog()
                # und die Eingabebehandlung in run(), Block
                # "if self.confirm_update:").
                self._start_update_install_dialog(
                    t("update_install_confirm", pending_update))
                # BUGFIX: siehe ausfuehrlicher Kommentar in
                # _check_for_update_background() - "notified_version" wird
                # jetzt ERST HIER, direkt nach dem tatsaechlichen Zeichnen
                # des Dialogs (siehe _start_update_install_dialog(), das
                # am Ende self.draw() aufruft), dauerhaft markiert, nicht
                # schon beim blossen Erkennen im Hintergrund-Thread.
                _upd_state = load_update_state()
                _upd_state["notified_version"] = pending_update
                save_update_state(_upd_state)

            # NEUES FEATURE (Nutzerwunsch: "ich moechte bei v4.4 bleiben,
            # aber trotzdem einen Hinweis sehen, wenn es neue Fixes gibt")
            # - komplett unabhaengig vom obigen Versions-Popup, eigener
            # Zustand, kann also auch dann anschlagen, wenn KEIN
            # Versions-Update ansteht. Gleicher Attract-Modus-Fix wie
            # oben (direkt uebernommen, keine Dopplung des ersten,
            # eigentlich ueberfluessigen draw()-Aufrufs von oben).
            #
            # BUGFIX (beim Testen des Timing-Fixes oben gefunden): sind
            # Versions- UND Build-Update im SELBEN Leerlauf-Tick faellig
            # (beide Bloecke liefen bislang bedingungslos nacheinander),
            # ueberschrieb dieser zweite _start_update_install_dialog()-
            # Aufruf sofort wieder self.confirm_update/_update_install_
            # message des ersten - der Versions-Dialog waere dadurch nie
            # sichtbar geworden, obwohl er korrekt gezeichnet wurde (nur
            # eben im selben Funktionsaufruf sofort ueberschrieben, bevor
            # next_action() zu einer echten Eingabe zurueckkehrt - exakt
            # dieselbe Symptomatik wie der bereits behobene Uebermal-
            # Fehler, nur diesmal durch den EIGENEN zweiten Dialog statt
            # durch Laufschrift/Cover-Redraw). "and not self.confirm_update"
            # sorgt dafuer, dass der Build-Hinweis in diesem Fall einfach
            # bis zum naechsten Leerlauf-Tick wartet, sobald der Nutzer den
            # Versions-Dialog beantwortet hat - _build_popup_pending bleibt
            # dafuer bewusst unveraendert (noch nicht auf None gesetzt).
            pending_build = getattr(self, "_build_popup_pending", None)
            if pending_build and not self.confirm_update:
                self._build_popup_pending = None
                if self.attract_mode:
                    self.attract_mode = False
                self._last_input_time = time.monotonic()
                # NEUES FEATURE (Nutzerwunsch: "sollte nach dem Logo
                # mittig als Infobox erscheinen") - prominent=True statt
                # der kleinen Fusszeilen-Meldung, siehe
                # _draw_prominent_message().
                #
                # ERWEITERUNG (Nutzer-Rueckmeldung, siehe ausfuehrlicher
                # Kommentar beim Versions-Update-Hinweis oben): derselbe
                # Wechsel von einer passiven Meldung zu einem aktiven
                # "Jetzt installieren?"-Dialog, unabhaengig davon, ob der
                # Hinweis von der Versionsnummer (oben) oder - wie hier -
                # vom versionsunabhaengigen Build-Check ausgeloest wurde;
                # beide fuehren zum selben Frontend_Install.sh-Lauf.
                self._start_update_install_dialog(
                    t("build_install_confirm", pending_build))
                # BUGFIX: siehe Kommentar beim Versions-Popup oben -
                # gleiches Prinzip, "notified_build_id" wird jetzt ebenso
                # erst nach dem tatsaechlichen Zeichnen markiert.
                _upd_build_id = getattr(self, "_pending_build_id", None)
                if _upd_build_id:
                    _upd_state = load_update_state()
                    _upd_state["notified_build_id"] = _upd_build_id
                    save_update_state(_upd_state)

            # "Auf diesen Tag vor X Jahren" (Nutzerwunsch): rein lokale
            # Dateiabfrage, kein Netzwerk - trotzdem bewusst genauso wie
            # RA-Vorwaermen/Update-Check erst im echten Leerlauf gezeigt
            # (nicht sofort beim Start), damit es niemanden mitten in
            # der Navigation unterbricht. Kein Hintergrund-Thread noetig
            # (siehe find_on_this_day_hint()), einfacher direkter Aufruf.
            if (not getattr(self, "_on_this_day_checked", False)
                    and time.monotonic() - self._last_input_time > self._attract_delay_cached()):
                self._on_this_day_checked = True
                hint = find_on_this_day_hint()
                if hint:
                    label, years_ago = hint
                    # Gleicher Bugfix wie beim Update-Hinweis oben -
                    # dieselbe Ursache (Attract-Modus verschluckt die
                    # Meldung sonst lautlos).
                    if self.attract_mode:
                        self.attract_mode = False
                    self._last_input_time = time.monotonic()
                    self.draw(message=t("on_this_day_popup", years_ago, label))

            if self.attract_mode:
                if time.monotonic() >= self._attract_change_next:
                    self._advance_attract()
            elif (self._attract_enabled_cached()
                  and time.monotonic() - self._last_input_time > self._attract_delay_cached()):
                self._enter_attract_mode()
            else:
                # Beim schnellen Scrollen (kurz nach einer Eingabe) noch
                # nicht dekodierte Cover ueberspringen - sie wuerden sonst
                # den Scroll-Pfad ruckeln lassen. Zentral hier gesetzt,
                # damit ALLE Zeichenpfade es sehen; nach dem Settle laedt
                # die Idle-Schleife unten sie einmalig nach.
                ART._defer_uncached = (time.monotonic() - self._last_input_time
                                       < COVER_SETTLE)
                # BUGFIX (Nutzer-Rueckmeldung: "wenn ich das Steuerkreuz
                # nach rechts oder links druecke, kommt der Beenden-
                # Dialog kurz wieder, und verschwindet dann wieder" -
                # exakt reproduziert: marquee_tick() UND der COVER_SETTLE-
                # Nachlade-Redraw direkt darunter zeichneten bisher OHNE
                # jede Ruecksicht auf einen offenen Ja/Nein-Dialog direkt
                # auf den physischen Bildschirm (marquee_tick() nur eine
                # einzelne Listenzeile per flip_rows(), der COVER_SETTLE-
                # Redraw sogar die KOMPLETTE Seite per draw_page_items())
                # - beide UEBERMALTEN den Dialog dadurch wieder, sobald
                # sie als naechstes fielligen wurden, OHNE ihn erneut
                # obendrauf zu zeichnen. COVER_SETTLE liegt bei nur
                # 150ms, self._last_input_time wird bei JEDER Eingabe
                # (auch innerhalb des Dialogs!) zurueckgesetzt - der
                # Nachlade-Redraw feuerte dadurch praktisch IMMER kurz
                # nach jedem Links/Rechts im Dialog, das fuehlte sich an
                # wie "ploppt auf und verschwindet sofort wieder wieder".
                # Fix: beide Pfade pausieren jetzt, solange ein Dialog
                # (Beenden ODER Update-Installieren) offen ist - genau
                # das bereits etablierte Muster der Musiktitel-Laufschrift
                # weiter unten (dort schon immer korrekt abgesichert).
                # Fuer den Nutzer unsichtbar, da die dahinterliegende
                # Liste waehrend eines Dialogs ohnehin nicht sichtbar
                # sein soll - nach dem Schliessen laeuft beides einfach
                # normal weiter.
                any_dialog = self.confirm_quit or self.confirm_update
                if need_mq and not any_dialog:
                    self.marquee_tick()
                # Beim schnellen Scrollen uebersprungene Cover ~COVER_SETTLE
                # nach dem letzten Tastendruck EINMAL nachladen (voller
                # Aufbau der Listenseite - defer ist dann aus, also werden
                # sie jetzt dekodiert). Passiert nur einmal pro Stillstand,
                # nicht bei jedem Schleifendurchlauf.
                if (not self._settled_redrawn and self.page == 1 and not any_dialog
                        and time.monotonic() - self._last_input_time >= COVER_SETTLE):
                    self.draw_page_items()
                    self._settled_redrawn = True
                    self._prefetch_neighbor_covers()
                self._boot_watch()   # Diagnose: Anzeige-Zustand nach dem Boot
                # WICHTIG: unabhaengige if-Abfragen statt einer elif-Kette.
                # Mit elif haette "track_needs" (Songtitel muss scrollen -
                # trifft auf praktisch jeden echten Songnamen zu) den
                # Equalizer-Takt DAUERHAFT blockiert, da die elif-Zweige
                # danach nie mehr geprueft wurden. Der Equalizer wurde
                # dadurch nur als Zufallsprodukt des viel langsameren
                # Songtitel-Taktes mitgezeichnet, nie mit seinem eigenen
                # schnellen Rhythmus - daher das gemeldete "Stocken". Jeder
                # Tick prueft sich selbst und meldet nur "True", wenn er
                # WIRKLICH faellig ist (eigene interne Drosselung), daher
                # ist es sicher, alle drei unabhaengig abzufragen.
                redraw_marquee = False
                redraw_dynamic = False
                if track_needs and self._track_marquee_tick(24):
                    redraw_marquee = True
                # NEUES FEATURE (siehe eq_effect_enabled() in
                # fe/settings.py): gleiches Muster wie beim Schimmer-
                # Effekt direkt darunter - bei Deaktivierung wird
                # _eq_tick() gar nicht erst aufgerufen.
                if eq_effect_enabled() and self._track_mq_name and self._eq_tick():
                    redraw_dynamic = True
                # NEUES FEATURE (siehe pulse_effect_enabled() in
                # fe/settings.py): bei Deaktivierung wird _pulse_tick()
                # gar nicht erst aufgerufen - vermeidet nicht nur die
                # Animation selbst, sondern auch den wiederholten
                # Neuaufbau (redraw_dynamic), den jeder faellige Tick
                # sonst ausloesen wuerde (siehe "PERF tick" Profiling).
                if pulse_effect_enabled() and self._pulse_tick():
                    redraw_dynamic = True
                # NEUES FEATURE (siehe _draw_prominent_message()): die
                # auffaellige Box muss auch OHNE weitere Nutzereingabe
                # nach Ablauf ihrer Anzeigedauer wieder verschwinden -
                # dieser leichte Tick-Pfad laeuft ohnehin schon
                # regelmaessig (bis zu 12.5x/Sekunde), daher reicht ein
                # einfacher Zeitvergleich hier, statt einen eigenen
                # Timer-Mechanismus aufzusetzen. Passiert nur EINMAL pro
                # Anzeige (self._prominent_message wird dabei auf None
                # gesetzt), kein wiederholter Aufwand danach.
                if (self._prominent_message
                        and time.monotonic() >= self._prominent_message_until):
                    self._prominent_message = None
                    self.draw()
                if redraw_marquee or redraw_dynamic:
                    if self.confirm_quit or self.confirm_update:
                        # Beenden-Dialog ODER (NEU) Update-Installieren-
                        # Dialog liegt ueber allem - der leichte Pfad
                        # wuerde darunter durchscheinen, deshalb hier
                        # immer der volle, sichere Aufbau.
                        self.draw()
                    else:
                        # Deutlich billiger als der komplette Aufbau
                        # (~5ms voller Aufbau vs. ~0.4ms hier auf HDMI
                        # gemessen) - genau die Ticks, die am
                        # haeufigsten laufen (bis zu 12.5x/Sekunde).
                        #
                        # NEUES PROFILING (Nutzer-Vermutung: "waere es
                        # sinnvoll, die Laufschrift/den Equalizer beim
                        # Scrollen rauszunehmen?"): die "~0.4ms"-Messung
                        # oben stammt vermutlich aus einer Umgebung OHNE
                        # echte Vsync-Synchronisierung - _draw_dynamic_
                        # items() ruft flip_rows() auf, das denselben
                        # ioctl-Vsync-Wartevorgang ausloest, der bei
                        # draw_page_items() auf echter Hardware bereits
                        # 8-17ms gekostet hat (siehe PERF-Logs). Ob das
                        # hier GENAUSO viel kostet und sich mit bis zu
                        # 12.5 Ticks/Sekunde spuerbar aufsummiert, ist
                        # noch unbestaetigt - deshalb dieselbe Art
                        # DRAGEND_PROFILE-Messung wie bei draw_page_items,
                        # NUR wenn die Umgebungsvariable gesetzt ist
                        # (kein Zusatzaufwand im Normalbetrieb).
                        if os.environ.get("DRAGEND_PROFILE") == "1":
                            _dt0 = time.monotonic()
                        if redraw_dynamic:
                            if self.page == 0:
                                self._draw_dynamic_cats()
                            else:
                                self._draw_dynamic_items()
                        if redraw_marquee:
                            self._draw_dynamic_track_marquee()
                        if os.environ.get("DRAGEND_PROFILE") == "1":
                            _dtick = time.monotonic() - _dt0
                            if _dtick > 0.003:   # bewusst NIEDRIGE Schwelle
                                                  # (3ms) - selbst bei der
                                                  # behaupteten 0.4ms-Kosten
                                                  # waere das noch 7x Spielraum,
                                                  # aber faengt jeden echten
                                                  # Vsync-Ausreisser zuverlaessig
                                LOG("PERF tick: %.1f ms (marquee=%s dynamic=%s)"
                                    % (_dtick * 1000, redraw_marquee, redraw_dynamic))
            self.music.tick()

    @staticmethod
    def _wrap(text, maxc, max_lines=2):
        """Text wortweise auf max_lines Zeilen umbrechen. Die letzte
        Zeile wird mit '~' abgeschnitten, falls immer noch zu lang."""
        words = text.split(" ")
        lines, cur = [], ""
        for word in words:
            trial = (cur + " " + word).strip()
            if len(trial) <= maxc:
                cur = trial
            else:
                if cur:
                    lines.append(cur)
                cur = word
                if len(lines) >= max_lines - 1:
                    break
        if cur:
            lines.append(cur)
        if len(lines) > max_lines:
            lines = lines[:max_lines]
        if lines and len(lines[-1]) > maxc:
            lines[-1] = lines[-1][:max(1, maxc - 1)] + "~"
        # Falls Woerter selbst laenger als maxc sind (z.B. lange
        # zusammengeschriebene Titel), hart kappen als Sicherheitsnetz
        lines = [ln if len(ln) <= maxc else ln[:max(1, maxc-1)] + "~"
                for ln in lines]
        return lines

    def _prefetch_neighbor_covers(self):
        """NEUES FEATURE (Nutzerwunsch: 'kann man da was vorcachen?' -
        nach dem Ruckel-Fix beim erneuten Skalieren). Dekodiert (aber
        skaliert NICHT) Cover in der Naehe der aktuellen Auswahl im
        Hintergrund, sobald die Liste stillsteht - wer kurz guckt und
        dann weiterscrollt, findet das naechste Cover so oft schon
        roh dekodiert vor.

        ERWEITERT (Phase 2, Sutefans Prioritaeten-Vorschlag): statt
        nur der direkten Nachbarn (+-1) jetzt mehrere Stufen mit
        sinkender Prioritaet, bevorzugt in der zuletzt genutzten
        Scrollrichtung (_last_scroll_dir):
          Stufe 1: direkter Nachbar in Scrollrichtung
          Stufe 2: direkter Nachbar in Gegenrichtung
          Stufe 3: zwei Felder in Scrollrichtung
          Stufe 4: zwei Felder in Gegenrichtung, drei in Scrollrichtung
        'Prioritaet 4: alles andere' aus dem Vorschlag bewusst NICHT
        als echtes Vorladen der kompletten Liste umgesetzt - anders
        als bei RA-Erfolgen (reiner Netzwerk-Abruf) muesste hier
        potenziell die GESAMTE Sammlung im begrenzten Bildspeicher
        gehalten werden, mit denselben Nachteilen, die schon beim
        RA-Vorlade-Feature gegen ein volles Cover-Vorladen gesprochen
        haben (siehe damalige Entscheidung: kleiner LRU-Bildspeicher
        wuerde die meisten Bilder sofort wieder verdraengen, bevor sie
        ueberhaupt gesehen werden).

        Zeitbudget bewusst begrenzt (PREFETCH_BUDGET) - auf schwacher
        Hardware soll ein Stillstand mit vielen gleichzeitig neuen
        Covern (z.B. nach einem Sprung in der Liste) niemals spuerbar
        haengen bleiben; bricht einfach fruehzeitig ab, die naechste
        Ruhephase erledigt den Rest.

        Bewusst NUR das rohe Dekodieren (ART.get()), NICHT die fertige
        Skalierung (ART.get_scaled()): die tatsaechliche Zielgroesse
        haengt vom Titeltext des jeweiligen Spiels ab (laengere Titel
        -> mehr Zeilen -> weniger Platz fuer das Cover selbst, siehe
        draw_art_panel()) und liesse sich hier nicht ohne die komplette
        Layout-Berechnung erneut zu duplizieren zuverlaessig vorher-
        sagen. Das rohe Dekodieren (Datei lesen + zlib-Dekompression)
        ist ohnehin der teurere Teil - die anschliessende Skalierung
        ist seit dem Performance-Fix (Zeilen-weises b\"\".join()) auch
        bei falscher Vorhersage schnell genug, um beim tatsaechlichen
        Hinscrollen kaum noch aufzufallen.

        Nur bei Stillstand aufgerufen (siehe COVER_SETTLE-Handler oben)
        - waehrend aktiven Scrollens passiert hier nichts, das wuerde
        den gerade behobenen Ruckel-Fehler nur an anderer Stelle
        wieder einfuehren."""
        if self.page != 1:
            return
        items = self._display_items()
        if not items:
            return
        fb = self.fb
        _name, _root_node, cat_syskey = self.cats[self.cat_i]
        d = 1 if getattr(self, "_last_scroll_dir", 1) >= 0 else -1
        # Prioritaets-Reihenfolge: Stufe 1+2 (direkte Nachbarn, in
        # Scrollrichtung zuerst), dann Stufe 3+4 (weiter weg, weiterhin
        # Scrollrichtung bevorzugt).
        offsets = [d, -d, 2*d, -2*d, 3*d]
        PREFETCH_BUDGET = 0.06   # Sekunden - grosszuegig genug fuer
                                 # mehrere Dekodierungen, aber niemals
                                 # spuerbar haengend auf schwacher HW.
        t0 = time.monotonic()
        for offset in offsets:
            if time.monotonic() - t0 > PREFETCH_BUDGET:
                break
            idx = self.item_i + offset
            if not (0 <= idx < len(items)):
                continue
            item = items[idx]
            item_syskey = self._item_syskey(item, cat_syskey)
            lookup_name = item[2] if item[1] == "folder" else item[0]
            if item_syskey == "ARCADE":
                continue   # Arcade-Cover kommen aus mra_meta(), kein einfacher Pfad hier
            try:
                # BUGFIX (Nutzer-Rueckmeldung, siehe ausfuehrlicher
                # Kommentar in draw_art_panel(): die Anzeige selbst faellt
                # im HD-Modus nicht mehr auf das SD-Cover zurueck, wenn
                # keine art_hd-Datei existiert - das bisherige zusaetzliche
                # Vorab-Laden des SD-Covers hier waere in dem Fall reine
                # Verschwendung des knappen Zeitbudgets (PREFETCH_BUDGET),
                # da es ohnehin nie angezeigt wird).
                if fb.height >= 720:
                    ART.get(_art_path_in(ART_HD, item_syskey, lookup_name))
                else:
                    ART.get(art_path(item_syskey, lookup_name))
            except Exception:
                pass   # Vorab-Laden ist rein optional - niemals den Hauptablauf stoeren

    def draw_art_panel(self, x0, w, y0, h, syskey, item, s):
        """Eigene Boxart+Info-Spalte rechts neben der Liste (seit v1.8
        deutlich groesser als der alte Block unten rechts, weil sie sich
        keinen Platz mehr mit der Liste teilen muss).

        Seit v1.9 wird die Text-Hoehe ZUERST anhand des tatsaechlichen
        Titels und der vorhandenen Spiele-Infos berechnet - das Cover
        bekommt danach den kompletten restlichen Platz. Vorher war fest
        55% fuer das Cover reserviert; fehlten Spiele-Infos (z.B. noch
        nicht mit mister_gameinfo.py geladen), blieb darunter viel Platz
        ungenutzt, statt dem Cover zugute zu kommen."""
        fb = self.fb
        H = fb.height
        name = item[0]
        # Bei einem Ordner-Eintrag (kind='folder') fuer die Cover-/
        # Metadaten-Suche den REINEN Ordnernamen nutzen (ohne den
        # anzeigenden Schraegstrich-Suffix aus item[0]) - wichtig z.B.
        # bei PSX-Sammlungen, wo jedes Spiel einen eigenen Unterordner
        # mit seinen Disc-Dateien hat: der Ordnername entspricht dann
        # dem Spieletitel, und Cover/Infos lassen sich genauso finden
        # wie bei einem normalen Spiele-Eintrag. Der Titel zeigt
        # weiterhin den Schraegstrich, damit klar bleibt, dass es sich
        # um einen anklickbaren Ordner handelt.
        lookup_name = item[2] if item[1] == "folder" else name
        if w < 20 or h < 20:
            return

        pad = 6 * s
        card_radius = 4 * s
        shadow_off = 3 * s
        # Dezenter Schlagschatten: einfaches, versetztes dunkles Rechteck
        # dahinter - kostet genauso wenig wie ein normaler rect()-Aufruf,
        # kein teures Alpha-Blending noetig fuer den gewuenschten Effekt.
        fb.rect_rounded(x0 - pad + shadow_off, y0 - pad + shadow_off,
                        w + 2 * pad, h + 2 * pad, fb._darken(C_BG, 0.55),
                        card_radius)
        fb.rect_rounded(x0 - pad, y0 - pad, w + 2 * pad, h + 2 * pad,
                        C_PANEL, card_radius)
        avail_w = w - 2 * pad
        maxc = max(4, avail_w // (8 * s))

        if syskey == "ARCADE":
            meta = mra_meta(item[2]) if item[1] == "core" else {}
        else:
            meta = get_meta(syskey, lookup_name)

        title = display_name(name)
        title_lines = self._wrap(title, maxc, max_lines=3)

        info_src = []
        if meta.get("players"):
            info_src.append(t("players", meta["players"]))
        if meta.get("year"):
            info_src.append(t("year", meta["year"]))
        if meta.get("genre"):
            info_src.append(str(meta["genre"]))
        if meta.get("manufacturer"):
            info_src.append(str(meta["manufacturer"]))
        # Spielzeit - mit demselben Namen (item[0], inkl. Schraegstrich-
        # Suffix bei Ordnern) nachgeschlagen, mit dem run_core() sie
        # aufgezeichnet hat (siehe record_playtime()) - NICHT
        # lookup_name, das waere bei Ordnern ein anderer String.
        played_entry = self._playtime_cache.get(name) \
            if hasattr(self, "_playtime_cache") else None
        played = format_playtime(played_entry.get("seconds") if played_entry else None)
        if played:
            info_src.append(t("playtime_shown", played))
        # RetroAchievements - nur sichtbar, wenn ein Treffer gefunden
        # wurde (kein Treffer = keine Zeile, kein Unterschied zu vorher
        # fuer alle, die RA nicht eingerichtet haben, siehe
        # lookup_ra_progress()).
        ra_progress = lookup_ra_progress(self._ra_lookup, name, syskey) \
            if hasattr(self, "_ra_lookup") and self._ra_lookup else None
        if ra_progress:
            info_src.append(t("ra_progress_shown", ra_progress[0], ra_progress[1]))
        if hasattr(self, "_completed_set") and name in self._completed_set:
            info_src.append(t("completed_shown"))
        info_lines = []
        for ln in info_src:
            info_lines.extend(self._wrap(ln, maxc, max_lines=1))

        # Songtitel steht jetzt in der Fusszeile (siehe draw_page_items),
        # nicht mehr hier im Boxart-Block - macht mehr Platz fuers Cover
        # frei und ist an einer Stelle sichtbar, die bei jedem System
        # gleich bleibt (auch wenn kein Cover/keine Infos vorhanden sind).

        line_h = 12 * s
        text_h = len(title_lines) * line_h
        if info_lines:
            text_h += 4 * s + len(info_lines) * line_h

        # Cover bekommt den nach dem Text uebrig bleibenden Platz -
        # zwischen 35% und 85% der Spaltenhoehe gedeckelt, damit weder
        # ein winziges Cover (sehr viel Text) noch ein den Text
        # verdraengendes Cover (kaum/kein Text) entsteht.
        cover_h = h - text_h - 8 * s
        cover_h = max(int(h * 0.35), min(cover_h, int(h * 0.85)))
        cover_h = max(20, cover_h)

        # ---- Cover oben, zentriert ----
        cy = y0
        accent = accent_for(syskey)
        art = None
        # BUGFIX (Nutzer-Rueckmeldung: "waere es machbar, dass wenn es
        # keine art_hd-Cover fuer den HDMI-Modus gibt, auch einfach
        # keine angezeigt werden, anstatt die SD-Cover dort einzublenden?
        # Das sieht bloed aus"): bis hierher (wie an allen anderen HD-
        # Cover-Stellen im Code, siehe ART_HD-Suche) ein automatischer
        # Rueckfall auf art_path() (SD-Bild), sobald keine passende
        # HD-Datei existierte - genau die vorherige Diagnose-Notiz
        # direkt oberhalb (jetzt entfernt, da der Rueckfall selbst
        # wegfaellt) hatte diesen Fall extra sichtbar gemacht, um genau
        # diese Nutzerfrage zu klaeren. Ein auf HDMI-Aufloesung stark
        # hochskaliertes SD-Bild ist unvermeidbar sichtbar matschig -
        # deshalb jetzt bewusst OHNE Rueckfall im HD-Modus: fehlt die
        # HD-Datei, bleibt art=None, und die schon vorhandene
        # "kein Artwork"/System-Hintergrundbild-Platzhalteranzeige
        # weiter unten greift automatisch - exakt dasselbe, bereits
        # etablierte Verhalten wie bei einem Spiel ganz ohne jedes
        # Cover (siehe "if art: ... else: ..." unterhalb). Reines
        # SD-Layout (H < 720, z.B. CRT) bleibt UNVERAENDERT: dort gab
        # es noch nie eine HD-Datei zu suchen, art_path() greift
        # weiterhin direkt, ohne Umweg. Gleiches Prinzip an den
        # uebrigen ART_HD-Fundstellen (draw_attract(), Wonne-oder-
        # Tonne-Screens, Trophaeenraum/Jahresrueckblick) mitgezogen.
        if H >= 720:
            hd = _art_path_in(ART_HD, syskey, lookup_name)
            art = ART.get_scaled(hd, avail_w, cover_h)
        else:
            art = ART.get_scaled(art_path(syskey, lookup_name), avail_w, cover_h)
        if art:
            aw, ah, pix = art
            ax = x0 + max(0, (avail_w - aw) // 2)
            ay = cy + max(0, (cover_h - ah) // 2)
            # Schlagschatten: dunkler, leicht versetzter Bereich UNTER
            # dem Cover, VOR dem eigentlichen Bild gezeichnet.
            fb.blend_rect_fast(ax + 3 * s, ay + ah - 4 * s, aw, 10 * s,
                              C_BG, (0, 0, 0), 0.35)
            self.blit(ax, ay, aw, ah, pix)
            fb.rect(ax - 2 * s, ay - 2 * s, aw + 4 * s, 2 * s, accent)
            fb.rect(ax - 2 * s, ay + ah, aw + 4 * s, 2 * s, accent)
            fb.rect(ax - 2 * s, ay - 2 * s, 2 * s, ah + 4 * s, accent)
            fb.rect(ax + aw, ay - 2 * s, 2 * s, ah + 4 * s, accent)
            # NEU (Nutzerwunsch: "100%-Trophaeen-Icon auf dem Cover"):
            # kleines goldenes Abzeichen oben rechts auf dem Cover,
            # NUR wenn dieses Spiel bei RetroAchievements zu 100%
            # abgeschlossen ist. ra_progress ist bereits weiter oben in
            # dieser Funktion ermittelt (siehe info_lines) - hier nur
            # noch die Bedingung pruefen, kein zusaetzlicher Nachschlag.
            # Dieselbe Gold-Farbe wie beim SNES-ALTTP-Tracker-Akzent
            # (SYSTEM_ACCENT), damit keine neue, willkuerliche Farbe in
            # den Code kommt.
            if ra_progress and ra_progress[1] > 0 and ra_progress[0] >= ra_progress[1]:
                badge_w, badge_h = 34 * s, 12 * s
                bx = min(ax + aw - badge_w - 2 * s, fb.width - badge_w - 2 * s)
                by = ay + 2 * s
                gold = (210, 175, 70)
                fb.rect_rounded(bx, by, badge_w, badge_h, gold)
                fb.text(bx + 3 * s, by + 2 * s, "100%", s, (10, 10, 14), gold)
            art_bottom = ay + ah
        else:
            # NEU (Nutzerwunsch): statt der reinen Textmeldung erst
            # versuchen, das SYSTEM-Hintergrundbild (dasselbe wie im
            # Hintergrund der Spieleliste, siehe BG_BASE/BgCache) klein
            # als Cover-Ersatz zu zeigen - deutlich weniger "leer" als
            # eine reine Farbflaeche, und zeigt trotzdem sofort, um
            # welches System es sich handelt. Nutzt dieselbe Aufloesungs-
            # bewusste Namenskonvention wie BgCache.get() (erst die zur
            # aktuellen Aufloesung passende Variante, dann die
            # allgemeine). Nur wenn GAR KEIN Hintergrundbild fuer dieses
            # System existiert (z.B. ein sehr seltenes/eigenes System
            # ohne mitgeliefertes BG), bleibt der reine Textplatzhalter
            # als letzter Rueckfall bestehen.
            #
            # PERFORMANCE-BUGFIX (Nutzer-Rueckmeldung: "beim Scrollen
            # fuehlt es sich laghaft an" - echtes Profiling auf echter
            # Hardware fand hier einen erheblichen, sich WIEDERHOLENDEN
            # Kostenfaktor, keinen Einmal-Fall): dieses Rueckfallbild
            # ist das GROSSE, fast bildschirmfuellende Systembild -
            # jedes Herunterskalieren auf Panel-Groesse kostete 200-
            # 700+ ms. Der Festplatten-Cache (siehe THUMB_CACHE) haette
            # das eigentlich nach dem ersten Mal abfangen sollen - tat
            # es aber nicht, weil cover_h (die Zielhoehe) von Spiel zu
            # Spiel geringfuegig schwankt (unterschiedlich viele
            # Metadaten-Zeilen: Genre/Jahr/Spielzeit/RA-Fortschritt/
            # Durchgespielt-Markierung aendern die verbleibende
            # Cover-Hoehe) - jede Abweichung war ein neuer Cache-
            # Schluessel, also ein neuer Fehltreffer, obwohl inhaltlich
            # dasselbe Bild in praktisch derselben Groesse gebraucht
            # wurde. Bestaetigt im echten Log: bei GBC-Spielen ohne
            # eigenes Cover wiederholte sich der teure Fall bei JEDEM
            # einzelnen Spiel (201/653/224/39/590/212/650/183/674/200/
            # 632/182/45/629/768/629 ms - nicht nur einmal).
            #
            # Fix: NUR fuer dieses Rueckfallbild (nicht fuer normale
            # Spiele-Cover, wo Pixelgenauigkeit zaehlt) wird die
            # Zielgroesse auf ein groberes Raster (8px) gerundet - bei
            # einem grossen, generischen Hintergrundbild als Platz-
            # halter faellt eine Abweichung von wenigen Pixeln optisch
            # nicht auf, ermoeglicht aber, dass praktisch alle Spiele
            # desselben Systems denselben Cache-Eintrag treffen.
            bg_fallback = None
            if syskey and system_bg_enabled():
                _bg_fb_w = max(1, (avail_w // 8) * 8)
                _bg_fb_h = max(1, (cover_h // 8) * 8)
                for fn in ("%s_%dx%d.art" % (syskey, fb.width, fb.height),
                          "%s.art" % syskey):
                    bg_fallback = ART.get_scaled(os.path.join(BG_BASE, fn), _bg_fb_w, _bg_fb_h)
                    if bg_fallback:
                        break
            if bg_fallback:
                aw, ah, pix = bg_fallback
                ax = x0 + max(0, (avail_w - aw) // 2)
                ay = cy + max(0, (cover_h - ah) // 2)
                self.blit(ax, ay, aw, ah, pix)
                fb.rect(ax - 2 * s, ay - 2 * s, aw + 4 * s, 2 * s, accent)
                fb.rect(ax - 2 * s, ay + ah, aw + 4 * s, 2 * s, accent)
                fb.rect(ax - 2 * s, ay - 2 * s, 2 * s, ah + 4 * s, accent)
                fb.rect(ax + aw, ay - 2 * s, 2 * s, ah + 4 * s, accent)
                art_bottom = ay + ah
            else:
                fb.rect(x0, cy, avail_w, cover_h, C_ACCENT2)
                fb.text(x0 + 4 * s, cy + cover_h // 2 - 4 * s,
                        t("no_artwork_1"), s, C_DIM, C_ACCENT2)
                fb.text(x0 + 4 * s, cy + cover_h // 2 + 5 * s,
                        t("no_artwork_2"), s, C_DIM, C_ACCENT2)
                art_bottom = cy + cover_h

        # ---- Titel + Infos darunter, volle Spaltenbreite ----
        # Text startet erst UNTER dem tatsaechlich gezeichneten Cover -
        # falls das Bild (z.B. wegen krummer Rundung) doch groesser als
        # cover_h ausfaellt, verhindert das trotzdem zuverlaessig eine
        # Ueberlappung mit den Infos.
        iy = max(cy + cover_h, art_bottom) + 6 * s
        y_max = y0 + h - 2 * s

        for ln in title_lines:
            if iy + 9 * s > y_max:
                break
            fb.text(x0, iy, ln, s, C_TITLE, C_PANEL)
            iy += line_h

        if info_lines:
            iy += 4 * s
            for ln in info_lines:
                if iy + 9 * s > y_max:
                    break
                fb.text(x0, iy, ln, s, C_TEXT, C_PANEL)
                iy += line_h

    def blit(self, x, y, w, h, pix):
        """Vordekodierte BGRA-Pixel zeilenweise in den Puffer kopieren.
        Schreibt nie eine andere Byte-Anzahl als angefordert - eine
        zu-kurze Quelle wuerde sonst (bytearray-Verhalten) den ganzen
        Puffer verkuerzen und verschieben."""
        fb = self.fb
        if x < 0 or y < 0 or x >= fb.width or y >= fb.height:
            return
        cw = min(w, fb.width - x)
        ch = min(h, fb.height - y)
        need = cw * 4
        buflen = len(fb.buf)
        for row in range(ch):
            src_off = row * w * 4
            dst_off = (y + row) * fb.stride + x * 4
            if dst_off + need > buflen:
                continue
            chunk = pix[src_off:src_off + need]
            if len(chunk) != need:
                continue
            fb.buf[dst_off:dst_off + need] = chunk

    # ------------------------------------------------------------------
    # Aktionen
    # ------------------------------------------------------------------

    RA_WATCH_POLL_INTERVAL = 25.0   # Sekunden zwischen zwei Abfragen -
                                    # bewusst nicht zu haeufig (RAs API
                                    # nicht unnoetig belasten), aber kurz
                                    # genug, dass sich ein Erfolg fuer
                                    # Zuschauer noch "frisch" anfuehlt

    def _watch_ra_achievements_during_play(self, game_id, stop_event):
        """Laeuft als Hintergrund-Thread WAEHREND ein Spiel laeuft
        (siehe run_core()) - fragt periodisch RAs Erfolgsliste fuer
        GENAU DIESES Spiel ab und pusht neu freigeschaltete Erfolge
        sofort ans Overlay (siehe StreamServer.publish_achievement()),
        damit Zuschauer sie in Echtzeit sehen - nicht erst, wenn das
        Frontend nach dem Spiel wieder sichtbar ist (unsere Haupt-
        schleife steht waehrend des Spiels ja still).

        Der ERSTE Abruf legt nur die Baseline fest (welche Erfolge
        waren schon VOR dieser Beobachtung frei) - genau wie bei
        _ensure_achievements_seen_initialized() fuer unsere eigenen
        Erfolge, sonst wuerden bereits laengst freigeschaltete Erfolge
        beim Sitzungsstart faelschlich als "neu" gemeldet."""
        seen_titles = None
        while not stop_event.is_set():
            achievements = fetch_ra_game_achievements_bounded(game_id, timeout=5.0)
            if achievements:
                earned_now = set(a[0] for a in achievements if a[4])
                if seen_titles is None:
                    seen_titles = earned_now
                else:
                    new_ones = earned_now - seen_titles
                    if new_ones and self.stream:
                        for name, desc, points, badge, earned, date, hardcore in achievements:
                            if name in new_ones:
                                try:
                                    self.stream.publish_achievement({
                                        "title": name, "description": desc,
                                        "points": points, "badge": badge,
                                    })
                                except Exception:
                                    pass   # Overlay-Push ist nie kritisch
                    seen_titles = earned_now
            stop_event.wait(self.RA_WATCH_POLL_INTERVAL)

    def run_core(self, path, label=None, syskey=None):
        """label (optional): Anzeigename fuer die Spielzeit-Aufzeichnung
        (siehe record_playtime()) - nur die Zeit vom bestaetigten Core-
        Start bis zur Rueckkehr ins Menue zaehlt, Ladezeiten und
        fehlgeschlagene Starts NICHT. syskey (optional): fuers
        "Entdecker"-Achievement (verschiedene Systeme ausprobiert)."""
        self.music.pause_for_core()
        self.inp.grab(False)
        # Overlay: den gerade gestarteten Titel noch zeigen, BEVOR wir
        # in die blockierende Warteschleife gehen - waehrend das Spiel
        # laeuft, aktualisiert sich das Overlay sonst gar nicht mehr
        # (die Hauptschleife, die es normalerweise anstoesst, steht ja
        # still), es wuerde also einfach auf dem letzten Zwischenstand
        # haengen bleiben oder leer wirken.
        if hasattr(self, "stream") and self.stream:
            self._stream_sig = None
            self._publish_stream()
        launch_core(path)
        t0 = time.monotonic()
        started = False
        # Auf den tatsaechlichen Core-Start warten (nicht mehr Menue).
        # Grosse CHDs auf langsamer SD brauchen laenger - deshalb 30s.
        while time.monotonic() - t0 < 30:
            if current_core() not in ("", "MENU"):
                started = True
                break
            time.sleep(0.3)
        if not started:
            # Core kam nie hoch (fehlendes RBF/ROM o.ae.). Nicht
            # faelschlich "Spiel beendet" annehmen, sondern zurueck -
            # sonst kehrt das Frontend bei langsamen Ladevorgaengen
            # oder Fehlstarts sofort ins Menue zurueck.
            LOG("run_core: Core nicht gestartet: %s" % path)
            self.music.resume_after_core()
            self.back_to_frontend()
            return
        # NEUES FEATURE (Nutzerwunsch: "das Frontend muesste registrieren,
        # wann ein Spiel startet, und OBS entsprechend umschalten") - ERST
        # HIER, nachdem der Core nachweislich lief (started=True oben),
        # nicht schon beim blossen Tastendruck - sonst wuerde OBS bei
        # einem fehlgeschlagenen Start (siehe "if not started" gerade
        # eben) faelschlich zur Spiel-Szene wechseln, obwohl gar kein
        # Spiel laeuft. Komplett wirkungslos, falls nicht konfiguriert
        # (siehe obs_switch_to_game() in stream_server.py).
        if self.stream:
            self.stream.obs_switch_to_game()
        play_start = time.monotonic()
        play_start_wall = time.time()   # fuer die Nachteule-Pruefung (Tageszeit) -
                                        # play_start selbst ist absichtlich
                                        # monotonic (unempfindlich gegen
                                        # Uhr-Korrekturen waehrend des Spiels),
                                        # sagt aber nichts ueber die Uhrzeit aus
        # RA-Erfolge WAEHREND des Spielens beobachten (Nutzerwunsch:
        # Zuschauer sollen einen Erfolg SOFORT sehen, nicht erst wenn
        # das Frontend wieder sichtbar ist) - NUR wenn das Overlay
        # ueberhaupt laeuft (sonst pollt niemand zu, unnoetiger
        # Netzwerk-/API-Aufwand) UND fuer dieses Spiel eine RA-GameID
        # bekannt ist. Siehe _watch_ra_achievements_during_play().
        ra_watch_stop = None
        if self.stream and self._ra_lookup and label:
            game_id = lookup_ra_game_id(self._ra_lookup, label, syskey)
            if game_id:
                ra_watch_stop = threading.Event()
                threading.Thread(
                    target=self._watch_ra_achievements_during_play,
                    args=(game_id, ra_watch_stop), daemon=True).start()
        while current_core() != "MENU":
            res = self.inp.wait_game_exit()
            if res in ("combo", "f10", "hid_combo"):
                LOG({"combo": "Start+Select erkannt - zurueck ins Menue",
                     "f10": "F10 erkannt - zurueck ins Menue",
                     "hid_combo": "Esc (HID-Notausstieg) erkannt - "
                                  "zurueck ins Menue"}[res])
                launch_core("/media/fat/menu.rbf")
                t1 = time.monotonic()
                while current_core() != "MENU" and time.monotonic() - t1 < 10:
                    time.sleep(0.3)
        # Bewusst HIER, direkt nach der Schleife (deckt BEIDE Wege
        # zurueck ab: normales Core-Ende UND manueller Notausstieg
        # ueber combo/f10/hid_combo oben) - EINE Stelle statt an jedem
        # der beiden Ausstiegspfade einzeln, da beide hier zusammen-
        # laufen. Komplett wirkungslos, falls nicht konfiguriert.
        if self.stream:
            self.stream.obs_switch_to_frontend()
        if ra_watch_stop:
            ra_watch_stop.set()
        played_seconds = time.monotonic() - play_start
        record_playtime(label, played_seconds, syskey=syskey)
        record_yearly_playtime(label, played_seconds, syskey=syskey)
        record_diary_entry(label, played_seconds, syskey=syskey)
        check_hidden_session_achievements(play_start_wall, time.monotonic() - play_start)
        check_hidden_session_achievements(play_start_wall, time.monotonic() - play_start,
                                          label=label, syskey=syskey)
        self._playtime_cache = load_playtime()
        time.sleep(1.0)
        self.music.resume_after_core()
        # BUGFIX (Nutzer-Rueckmeldung: "Weiterspielen und Zuletzt gezockt
        # funktioniert bei mir doch nicht so richtig ... Tetris zeigt er
        # nicht"): 'Weiterspielen'/'Zuletzt gespielt' in self.cats VOR
        # back_to_frontend() (das mit draw() endet) auffrischen - siehe
        # ausfuehrlichen Kommentar in _sync_recent_category(). Bewusst
        # HIER (ein einziger Ort, deckt alle drei Aufrufer von run_core()
        # ab: normaler Kategorie-Start, Zufalls-Zock, F11-Schnellstart),
        # statt an jeder record_recent()-Stelle einzeln.
        self._sync_recent_category()
        # Overlay wieder auf den (jetzt evtl. veraenderten, z.B. neue
        # Spielzeit) Menue-Stand auffrischen.
        if hasattr(self, "stream") and self.stream:
            self._stream_sig = None
            self._publish_stream()
        self.back_to_frontend()
        # NACH back_to_frontend() (das mit einem normalen draw() endet),
        # damit die Einblendung diesen Redraw ueberschreibt statt sofort
        # wieder zu verschwinden.
        self._notify_new_achievements()

    def run_script(self, path, args=None):
        """Script auf der Konsole (tty1) laufen lassen, danach zurueck.
        args (neu, fuer den Ersteinrichtungs-Assistenten): optionale
        Zusatzargumente, z.B. das im Assistenten bereits gewaehlte
        CRT/HDMI-Profil direkt an Frontend_Boxart_Download.sh durchreichen,
        statt es dort ein zweites Mal abzufragen. Bestehende Aufrufe
        ohne args bleiben unveraendert (Rueckwaertskompatibel).

        BUGFIX (Nutzer-Rueckmeldung: "Scripts werden wenn sie im
        frontend gestartet werden nicht sauber ausgefuehrt"): bisher
        wurde hier NUR self.inp.grab(False) aufgerufen, MiSTer aber nie
        per F9 in den Konsolenmodus geschaltet (siehe
        enter_console_mode() - "sonst uebermalt das MiSTer-Wallpaper
        unseren Framebuffer permanent", hier greift das Gegenteil: OHNE
        diesen Wechsel bleibt vermutlich unser eigener, zuletzt
        gezeichneter Framebuffer ueber der Text-Konsole liegen, das
        Skript schreibt zwar korrekt auf tty1, aber sichtbar/nutzbar
        ist das dadurch nicht sauber. run_core()/back_to_frontend()
        machen diesen Wechsel bereits an vergleichbarer Stelle -
        run_script() hatte ihn bisher NICHT."""
        self.music.pause_for_core()
        self.enter_console_mode()
        self.set_cursor_blink(True)
        # NEUE DIAGNOSE (Nutzer-Rueckmeldung: "wenn ich ein Script starte,
        # wechselt das Frontend in den Konsolenmodus und dann passiert
        # nichts weiter") - bislang wurde ein fehlgeschlagenes Oeffnen
        # von /dev/tty1 KOMPLETT still abgefangen (tty=None), und der
        # Fallback-Pfad (subprocess.call(raw) weiter unten) leitet
        # Ein-/Ausgabe NIRGENDS explizit um - das Script liefe dann mit
        # den geerbten Datei-Deskriptoren des Frontend-Prozesses selbst,
        # die je nach Start-Methode (Dienst/SSH/Skript) NICHT der
        # sichtbare Bildschirm sein muessen. Genau das wuerde das
        # gemeldete Symptom erklaeren: der Bildschirm wechselt (passiert
        # bedingungslos VOR diesem try/except), aber das Script selbst
        # landet sichtbar nirgends. Ohne Log-Zeile war bisher nicht mal
        # unterscheidbar, OB dieser Fall ueberhaupt eintritt.
        try:
            tty = open("/dev/tty1", "r+b", buffering=0)
            LOG("run_script: /dev/tty1 erfolgreich geoeffnet fuer %s" % path)
        except OSError as e:
            tty = None
            LOG("run_script: /dev/tty1 KONNTE NICHT geoeffnet werden (%s) - "
                "Skript laeuft ohne explizite Ein-/Ausgabe-Umleitung, "
                "vermutlich NICHT sichtbar auf dem Bildschirm!" % e)
        # UEBERNOMMENER VORSCHLAG (TheRealSutefan): tty1 zum STEUERNDEN
        # Terminal des Scripts machen (neuer Session-Leader + TIOCSCTTY).
        # Erst dann laufen dialog/whiptail und alles, was /dev/tty
        # DIREKT oeffnet, sauber - genau wie beim Start aus MiSTers OSD.
        # Ohne das leitet subprocess nur stdin/out/err um, das Script hat
        # aber kein steuerndes Terminal -> interaktive Scripts scheitern.
        def _ctty():
            os.setsid()
            try:
                fcntl.ioctl(0, termios.TIOCSCTTY, 1)
            except OSError:
                pass
        # UEBERNOMMEN (TheRealSutefan): "Script beendet (Code X) -
        # Taste druecken" jetzt auf Konsolenebene selbst (bash-Wrapper
        # mit read -rsn1) statt ueber self.inp.read_action() zu warten -
        # zeigt zusaetzlich den Exit-Code, unabhaengig davon, ob das
        # Frontend-Eingabesystem waehrend des Konsolenmodus zuverlaessig
        # mitliest. Deutscher Text statt des bisherigen englischen.
        inner = ('printf "\\033[2J\\033[H"; '
                 'bash "$0" "$@"; _ec=$?; '
                 'printf "\\n-- Script beendet (Code %s) - Taste druecken --\\n" "$_ec"; '
                 'read -rsn1')
        wrapped = ["/bin/bash", "-c", inner, path] + (list(args) if args else [])
        raw     = ["/bin/bash", path] + (list(args) if args else [])
        # Bildschirm dem Script ueberlassen
        try:
            if tty:
                LOG("run_script: starte mit tty1-Umleitung: %s" % wrapped)
                rc = subprocess.call(wrapped, preexec_fn=_ctty,
                                     stdin=tty, stdout=tty, stderr=tty,
                                     env=dict(os.environ, TERM="linux",
                                              HOME="/root"))
            else:
                LOG("run_script: starte OHNE tty1-Umleitung (Fallback): %s" % raw)
                rc = subprocess.call(raw)
            LOG("run_script: %s beendet, Ruecksprungwert=%s" % (path, rc))
        except Exception as e:
            LOG("run_script: Fehler bei %s: %s" % (path, e))
        finally:
            if tty:
                try:
                    tty.close()
                except OSError:
                    pass
        self.music.resume_after_core()
        self.back_to_frontend()

    def draw_core_choice_screen(self, syskey, display_name, default_ra=False):
        """Zwei-Optionen-Auswahl (Normal-Core / RA-Core), gezeigt beim
        Betreten eines Systems, fuer das find_ra_core() eine RA-
        faehige Core-Variante gefunden hat. Hoch/Runter wechselt die
        Auswahl, OK bestaetigt. Liefert True fuer RA-Core, False fuer
        normal (jeweils ueber OK bestaetigt), oder None bei ESC/back -
        NUR dann bricht der Aufrufer das Betreten der Kategorie
        komplett ab (siehe _enter_category()).

        BUGFIX (Nutzer-Rueckmeldung): ESC lieferte bisher IMMER False
        zurueck ("normaler Core") - der Aufrufer konnte das nicht von
        einer bewussten OK-Bestaetigung fuer "normal" unterscheiden und
        ist deshalb IMMER in die Kategorie gewechselt, selbst bei ESC.
        Das fuehlte sich fuer den Nutzer an, als koenne man aus diesem
        Bildschirm ueberhaupt nicht mehr zurueck. Jetzt liefert ESC
        explizit None, und NUR das bricht wirklich ab.

        BUGFIX (Nutzer-Rueckmeldung: "Weiterspielen"/"Zuletzt gespielt"
        funktionierten nicht sauber, u.a. weil nicht richtig
        unterschieden wurde, mit welchem Core ein Spiel zuletzt lief):
        die Auswahl stand hier bisher IMMER fest auf "normaler Core",
        unabhaengig davon, ob genau dieses Spiel zuletzt tatsaechlich
        mit dem RA-Core gestartet wurde. Wer schnell OK gedrueckt hat
        (etwa aus Gewohnheit), landete dadurch stillschweigend im
        falschen Core - ohne RA-Fortschrittserfassung, wenn zuletzt RA
        lief. default_ra (vom Aufrufer typischerweise aus
        load_last_core_choice() abgeleitet) laesst den Cursor jetzt auf
        der zuletzt tatsaechlich genutzten Variante starten - gefragt
        wird weiterhin JEDES Mal (bewusst keine stille Automatik, siehe
        Kommentar beim Aufruf in der Hauptschleife), nur die Vorauswahl
        stimmt jetzt."""
        fb = self.fb
        W, H = fb.width, fb.height
        s = max(1, H // 360)
        ox = W * OVERSCAN_X // 100
        oy = H * OVERSCAN_Y // 100
        accent = accent_for(syskey)
        choice = 1 if default_ra else 0   # 0 = normaler Core, 1 = RA-Core
        options = [t("core_choice_normal"), t("core_choice_ra")]
        while True:
            fb.clear(C_BG)
            title = t("core_choice_title", display_name)
            title_scale = self._fit_scale(title, W - 2 * ox, s + 1)
            fb.text(ox, oy, title, title_scale, C_TITLE, C_BG)
            y = oy + 90 * s
            for i, label in enumerate(options):
                sel = i == choice
                color = accent if sel else C_TEXT
                prefix = "> " if sel else "  "
                fb.text(ox, y, prefix + label, s, color, C_BG)
                y += 40 * s
            hint = t("core_choice_hint")
            sc = s - 1 if s > 1 else 1
            hint_w = len(hint) * 8 * sc
            fb.text((W - hint_w) // 2, H - oy - 8 * sc, hint, sc, C_DIM, C_BG)
            fb.flip()
            act = self.inp.read_action()
            if act in ("up", "down", "left", "right"):
                choice = 1 - choice
            elif act == "ok":
                return choice == 1
            elif act in ("back", "exit"):
                return None   # Abbruch - Kategorie wird NICHT betreten

    def _draw_wot_title(self, fb, ox, oy, text_w, s):
        """Zeichnet den 'Zufalls-Zock'-Titel als Text.

        KORRIGIERT (Nutzer-Rueckmeldung: "das Bild fuer Zufalls-Zock
        muss in den Ordner sysart. Du hast einen eigenen wot_logo-
        Ordner dafuer erstellt, das war nicht richtig"): dieser
        Bildschirm hatte urspruenglich NIE eigenes Bild-Artwork - der
        Nutzerwunsch "das alte Bild in der Boxart neben der Kategorie
        ZUFALLS-ZOCK austauschen" bezog sich die ganze Zeit auf die
        kleine Vorschau links im Kategorien-Hauptmenue (siehe
        _draw_cat_artbox()), die bereits VOR dieser Session ueber den
        etablierten Sysart-Mechanismus lief (SYSART_BASE/WOT.art,
        siehe _category_art_key() in fe/art.py). Hier wurde
        faelschlich ein KOMPLETT NEUER, eigener Mechanismus samt
        eigenem wot_logo/-Ordner fuer eine andere Stelle (dieser
        Bildschirm hier) eingefuehrt - der eigentliche Ort, an dem der
        Nutzer das alte Bild sah, blieb dadurch unveraendert, das neue
        Bild landete bisher an der falschen Stelle. Jetzt entfernt;
        das neue Bild liegt korrekt unter SYSART_BASE/WOT.art."""
        fb.text(ox, oy, t("wot_title"),
                self._fit_scale(t("wot_title"), text_w, s + 1), C_TITLE, C_BG)

    def draw_wot_screen(self):
        """'Zufalls-Zock': bietet drei zufaellige Spiele GLEICHZEITIG zur Wahl
        an (je Zeile voller Name + System; die drei Cover nebeneinander unten).
        Hoch/Runter waehlt, OK oeffnet den Starten-Screen. "Neu ziehen" zeigt
        drei neue - wiederholungsfrei, bis alle Spiele einmal dran waren.

        Quelle ist die SELBE Spieleliste, die das Frontend beim Scannen fuer
        seine Menues aufbaut (_attract_games_pool()) - dadurch ist das Roulette
        immer deckungsgleich mit dem, was tatsaechlich auf dem MiSTer liegt,
        und aktualisiert sich automatisch mit jedem Rescan. Bereits gespielte
        Spiele (wot_played.json) werden herausgefiltert."""
        fb = self.fb
        W, H = fb.width, fb.height
        s = max(1, H // 360)
        ox = W * OVERSCAN_X // 100
        oy = H * OVERSCAN_Y // 100
        text_w = W - 2 * ox
        # Untere sichere Grenze oberhalb der Hinweiszeile (siehe deren
        # Position weiter unten: H - oy - 8*sc) - Zeilen/Cover duerfen
        # nie tiefer reichen, sonst ueberlappen sie den Hinweis oder
        # ragen ueber den Bildschirmrand hinaus (siehe BUGFIX weiter
        # unten bei row_h).
        sc = s - 1 if s > 1 else 1
        bottom_limit = H - oy - 8 * sc - 6 * s
        # ABGLEICH mit dem tatsaechlichen MiSTer-Bestand: die spielbare Liste
        # kommt direkt aus _attract_games_pool() - der flachen Liste ALLER
        # gescannten Spiele, die das Frontend ohnehin schon fuer seine Menues
        # gebaut hat. Damit kann das Roulette nicht mehr vom echten Bestand
        # abweichen (kein separater Zweitscan, kein eigener Cache), und ein
        # Rescan aktualisiert es automatisch mit. Bereits gespielte Spiele
        # (wot_played.json) werden herausgefiltert. Jeder Attract-Eintrag ist
        # (label, syskey, arg) mit arg=(rom, ext, syskey, rbf, load); wir
        # bringen ihn in die bewaehrte Roulette-Form
        # (system, title, genre, ra_id, rom, score) - genre/ra_id bleiben leer,
        # Ziehen/Anzeige/Start darunter bleiben unveraendert.
        played_set, _ = wot_load_played()
        playable = []
        for label, syskey, arg in self._attract_games_pool():
            if (syskey, wot_normalize_title(label)) in played_set:
                continue
            playable.append((syskey, label, "", "", arg[0], 1.0))
        if not playable:
            self._wizard_info(t("wot_title"), [t("wot_pool_empty")], skippable=False)
            return

        # Rotations-Queue: gemischte spielbare Liste, jeweils drei entnehmen;
        # ist sie fast leer, neu mischen -> keine Wiederholung, bis alle
        # spielbaren Spiele einmal dran waren.
        queue = []
        def _next_three():
            if len(queue) < 3:
                del queue[:]
                fresh = list(playable)
                random.shuffle(fresh)
                queue.extend(fresh)
            return [queue.pop() for _ in range(min(3, len(queue)))]

        cover_cache = {}          # (system, rom_base) -> Cover | None (ueber Neu ziehen hinweg)
        picks = _next_three()

        while True:
            n_games = len(picks)
            redraw_i = n_games
            back_i = n_games + 1
            n_rows = n_games + 2

            # Zeilen (voller Name + System - Genre + RA-ID); gemeinsame
            # Schriftgroesse bis s+1, so dass die laengste Zeile komplett passt
            # (statt zu schneiden) - erst im Extremfall wird der Titel gekuerzt.
            glines = []
            for p in picks:
                clean = " ".join(p[1].split())
                meta = system_display_name(p[0])
                if p[2]:
                    meta += " - %s" % p[2]
                if p[3]:
                    meta += "  RA-ID: %s" % p[3]
                glines.append((clean, meta))
            rows_scale = s + 1
            for clean, meta in glines:
                rows_scale = min(rows_scale,
                                 self._fit_scale("%s   %s" % (clean, meta), text_w, s + 1))
            maxchars = max(8, text_w // (8 * rows_scale))
            row_strs = []
            for clean, meta in glines:
                ln = "%s   %s" % (clean, meta)
                if len(ln) > maxchars:
                    # BUGFIX (Nutzer-Rueckmeldung: auf CRT (320x240, wo diese
                    # Zeilen ueberhaupt erst gekuerzt werden - auf HDMI ist
                    # meist genug Platz) erschien statt einer Ellipse ein
                    # "?" mitten im Titel, z.B. "Beauty and the ?" statt
                    # "Beauty and the...". Ursache: "\u2026" (Ellipse) liegt
                    # weit ausserhalb der beiden Zeichensaetze, die fb.text()
                    # kennt (FONT8X8 fuer 0-127, FONT_EXTRA fuer Latin-1
                    # 0xA0-0xFF - siehe fe/framebuffer.py) und faellt dort auf
                    # den "?"-Platzhalter zurueck. Der Rest des Frontends
                    # kuerzt genau deshalb schon immer mit "~" statt "..."
                    # (siehe z.B. die Kategorie-/Item-Listen) - hier an
                    # dieselbe, garantiert im Font vorhandene Konvention
                    # angeglichen.
                    keep = maxchars - len(meta) - 5
                    if keep < 4:
                        ln = ln[:maxchars - 1] + "~"
                    else:
                        ln = "%s~   %s" % (clean[:keep], meta)
                row_strs.append(ln)

            games_top = oy + 70 * s
            # BUGFIX (Nutzer-Rueckmeldung + Foto: auf CRT wurden die Cover
            # unten abgeschnitten, und "Zurueck" tauchte gar nicht mehr auf).
            # Ursache: Zeilenhoehe/Abstaende/Cover-Mindesthoehe waren feste
            # 44*s/14*s/40*s/26*s-Vielfache, zugeschnitten auf HDMI (1080px,
            # s=3, jede Menge Platz) - auf CRT (240px, s=1) passte diese
            # Summe rechnerisch gar nicht mehr in die verfuegbare Hoehe.
            # fb.text()/blit() schneiden ueberschuessigen Inhalt aber still
            # ab (kein Fehler, nur unsichtbar), daher fiel es erst jetzt auf.
            # Fix: Zeilenhoehe, Aktionszeilen-Abstand und Cover-Mindesthoehe
            # werden jetzt aus der TATSAECHLICH verfuegbaren Hoehe (bis
            # bottom_limit) abgeleitet - genau wie schon _fit_scale es fuer
            # die Breite tut. Auf HDMI aendert sich dadurch nichts (dort
            # greift min(44*s, ...) weiterhin bei 44*s, da reichlich Platz
            # ist); auf CRT schrumpfen Zeilen/Abstaende/Cover-Mindesthoehe
            # jetzt so weit, dass wirklich alles sichtbar bleibt.
            covers_min = max(16, 20 * s)
            avail_for_rows = bottom_limit - games_top - 14 * s - covers_min
            row_h = max(8 * rows_scale + 4 * s,
                       min(44 * s, avail_for_rows // max(1, n_games)))
            action_top = games_top + n_games * row_h + 14 * s
            action_row_gap = max(8 * s + 2 * s,
                                 min(40 * s, (bottom_limit - action_top) // 2))

            # Cover-Streifen unten rechts: die drei Cover nebeneinander, auf
            # Hoehe der Aktionszeilen. Wuerde die Aktionsspalte links zu breit,
            # rueckt der Streifen nach rechts (kein Ueberlappen).
            action_labels = [t("wot_option_redraw"), t("wot_option_back")]
            action_col = ox + max(len(a) for a in action_labels) * 8 * s + 16 * s
            covers_block_w = int(W * 0.62)
            covers_x0 = max(action_col, W - ox - covers_block_w)
            covers_block_w = max(30 * s, W - ox - covers_x0)
            covers_h = max(covers_min, bottom_limit - action_top)
            cell_w = covers_block_w // max(1, n_games)

            sel = 0
            redraw = False
            back_to_menu = False
            while True:
                fb.clear(C_BG)
                self._draw_wot_title(fb, ox, oy, text_w, s)

                # Spielzeilen (volle Breite)
                y = games_top
                for i, ln in enumerate(row_strs):
                    selrow = i == sel
                    color = accent_for(picks[i][0]) if selrow else C_TEXT
                    prefix = "> " if selrow else "  "
                    fb.text(ox, y, prefix + ln, rows_scale, color, C_BG)
                    y += row_h

                # Aktionszeilen (links)
                y = action_top
                for label, ri in ((action_labels[0], redraw_i), (action_labels[1], back_i)):
                    selrow = ri == sel
                    color = accent_for(None) if selrow else C_DIM
                    prefix = "> " if selrow else "  "
                    fb.text(ox, y, prefix + label, s, color, C_BG)
                    y += action_row_gap

                # Drei Cover nebeneinander (rechts, auf Hoehe der Aktionen);
                # das markierte Spiel bekommt einen farbigen Rahmen.
                for i, p in enumerate(picks):
                    psys = p[0]
                    prom_base = os.path.splitext(os.path.basename(p[4]))[0]
                    ckey = (psys, prom_base)
                    if ckey not in cover_cache:
                        art = None
                        # BUGFIX (Nutzer-Rueckmeldung, siehe ausfuehrlicher
                        # Kommentar in draw_art_panel(): kein SD-Rueckfall
                        # mehr im HD-Modus - fehlende HD-Datei = kein Cover
                        # statt matschig hochskaliertem SD-Bild).
                        if H >= 720:
                            art = ART.get_scaled(_art_path_in(ART_HD, psys, prom_base),
                                                 cell_w - 10 * s, covers_h)
                        else:
                            art = ART.get_scaled(art_path(psys, prom_base),
                                                 cell_w - 10 * s, covers_h)
                        cover_cache[ckey] = art
                    art = cover_cache[ckey]
                    if not art:
                        continue
                    caw, cah, cpix = art
                    cell_x = covers_x0 + i * cell_w
                    cax = cell_x + (cell_w - caw) // 2
                    cay = action_top
                    if i == sel:
                        cpad = 5 * s
                        fb.rect(cax - cpad, cay - cpad, caw + 2 * cpad, cah + 2 * cpad,
                                accent_for(psys))
                    self.blit(cax, cay, caw, cah, cpix)

                hint = t("wot_hint")
                sc = s - 1 if s > 1 else 1
                hint_w = len(hint) * 8 * sc
                fb.text((W - hint_w) // 2, H - oy - 8 * sc, hint, sc, C_DIM, C_BG)
                fb.flip()

                act = self.inp.read_action()
                if act == "up":
                    sel = (sel - 1) % n_rows
                elif act == "down":
                    sel = (sel + 1) % n_rows
                elif act == "ok":
                    if sel < n_games:
                        if self._wot_start_screen(picks[sel]):
                            return
                    elif sel == redraw_i:
                        picks = _next_three()
                        redraw = True
                        break
                    else:
                        back_to_menu = True
                        break
                elif act in ("back", "exit"):
                    back_to_menu = True
                    break

            if back_to_menu:
                return
            # redraw -> aeussere Schleife mit den neuen picks

    def _wot_start_screen(self, pick):
        """Bestaetigungs-/Starten-Screen fuer ein aus der Dreier-Auswahl
        gewaehltes Spiel: grosses Cover + Starten/Zurueck. Liefert True, wenn
        gestartet wurde (Aufrufer kehrt ins Menue zurueck), sonst False
        (zurueck zur Dreier-Auswahl). Der Start-Ablauf (RA-Core-Erkennung,
        dauerhaftes Als-gespielt-Markieren, MGL/Core-Start) ist unveraendert
        aus dem frueheren Einzel-Screen uebernommen."""
        fb = self.fb
        W, H = fb.width, fb.height
        s = max(1, H // 360)
        ox = W * OVERSCAN_X // 100
        oy = H * OVERSCAN_Y // 100
        # Gleicher CRT-Bugfix wie in draw_wot_screen() (siehe dortiger
        # Kommentar): sichere untere Grenze oberhalb der Hinweiszeile, an
        # der sich der Abstand vor/zwischen den Optionszeilen weiter unten
        # orientiert, statt fest 70*s/40*s anzunehmen.
        sc = s - 1 if s > 1 else 1
        bottom_limit = H - oy - 8 * sc - 6 * s
        system, title, genre, ra_id, rom_path, score = pick
        accent = accent_for(system)
        clean_title = " ".join(title.split())
        rom_base = os.path.splitext(os.path.basename(rom_path))[0]
        cov_w = int(W * 0.40)
        cov_h = int(H * 0.62)
        wot_art = None
        # BUGFIX (Nutzer-Rueckmeldung, siehe ausfuehrlicher Kommentar in
        # draw_art_panel(): kein SD-Rueckfall mehr im HD-Modus - fehlende
        # HD-Datei = kein Cover statt matschig hochskaliertem SD-Bild).
        if H >= 720:
            wot_art = ART.get_scaled(_art_path_in(ART_HD, system, rom_base), cov_w, cov_h)
        else:
            wot_art = ART.get_scaled(art_path(system, rom_base), cov_w, cov_h)
        text_w = W - 2 * ox
        if wot_art:
            text_w = max(80 * s, W - 2 * ox - wot_art[0] - 20 * s)
        choice = 0
        options = [t("wot_option_start"), t("wot_option_back")]
        while True:
            fb.clear(C_BG)
            self._draw_wot_title(fb, ox, oy, text_w, s)
            y = oy + 70 * s
            fb.text(ox, y, clean_title, self._fit_scale(clean_title, text_w, s + 1), accent, C_BG)
            y += 50 * s
            meta = system_display_name(system)
            if genre:
                meta += " - %s" % genre
            fb.text(ox, y, meta, s, C_DIM, C_BG)
            if ra_id:
                y += 45 * s
                fb.text(ox, y, "RA-ID: %s" % ra_id, s, C_DIM, C_BG)
            # BUGFIX (gleiche Ursache wie in draw_wot_screen(), siehe dortiger
            # Kommentar): auf CRT reichte die feste Kombination aus 70*s
            # Abstand + 2x 40*s Optionszeilen rechnerisch nicht mehr in die
            # verfuegbare Hoehe - "Zurueck" landete dadurch unsichtbar
            # unterhalb des Bildschirms. remaining/option_row_h leiten den
            # Abstand jetzt aus der TATSAECHLICH verfuegbaren Hoehe ab (wie
            # _fit_scale es fuer die Breite tut); auf HDMI bleibt durch die
            # min()-Deckelung alles exakt wie bisher (dort ist reichlich
            # Platz, min() greift immer bei den alten 70*s/40*s-Werten).
            remaining = max(0, bottom_limit - y)
            option_row_h = max(8 * s + 4 * s,
                               min(40 * s, remaining // (len(options) + 1)))
            y += min(70 * s, max(option_row_h, remaining - len(options) * option_row_h))
            if wot_art:
                caw, cah, cpix = wot_art
                cax = W - ox - caw
                cay = oy + 70 * s
                cpad = 6 * s
                fb.rect(cax - cpad, cay - cpad, caw + 2 * cpad, cah + 2 * cpad, accent)
                self.blit(cax, cay, caw, cah, cpix)
            for i, label in enumerate(options):
                selrow = i == choice
                color = accent if selrow else C_TEXT
                prefix = "> " if selrow else "  "
                fb.text(ox, y, prefix + label, s, color, C_BG)
                y += option_row_h
            hint = t("wot_hint")
            hint_w = len(hint) * 8 * sc
            fb.text((W - hint_w) // 2, H - oy - 8 * sc, hint, sc, C_DIM, C_BG)
            fb.flip()
            act = self.inp.read_action()
            if act == "up":
                choice = (choice - 1) % len(options)
            elif act == "down":
                choice = (choice + 1) % len(options)
            elif act == "ok":
                if choice == 0:      # Starten
                    sysdef = next((sd for sd in GAME_SYSTEMS if sd[1] == system), None)
                    if sysdef:
                        ext = os.path.splitext(rom_path)[1].lower()
                        dl, ftype, idx = sysdef[4].get(ext, (2, "f", 0))
                        ra_core = find_ra_core(system)
                        if ra_core:
                            launch_rbf, setname = ra_core
                            LOG("Zufalls-Zock: gestartet mit RA-Core - %s (%s)"
                                % (title, rom_path))
                        else:
                            launch_rbf, setname = sysdef[3], None
                            LOG("Zufalls-Zock: kein RA-Core fuer %s, Standard-Core - %s"
                                % (system, title))
                        wot_mark_played(system, title)   # dauerhaft aus dem Pool nehmen
                        record_recent(title, (rom_path, ext, system, sysdef[3], (dl, ftype, idx)))
                        mgl = write_mgl(launch_rbf, rom_path, dl, ftype, idx, setname=setname)
                        self.run_core(mgl, label=title, syskey=system)
                    return True
                else:                # Zurueck -> zurueck zur Dreier-Auswahl
                    return False
            elif act in ("back", "exit"):
                return False


    def draw_ra_setup_screen(self):
        """Zeigt eine kurze Anleitung zur RetroAchievements-Einrichtung
        (keine Bildschirmtastatur vorhanden - die Datei wird per SSH/
        Texteditor angelegt). Beliebige Taste kehrt zurueck."""
        fb = self.fb
        W, H = fb.width, fb.height
        s = max(1, H // 360)
        ox = W * OVERSCAN_X // 100
        oy = H * OVERSCAN_Y // 100
        fb.clear(C_BG)
        fb.text(ox, oy, t("ra_setup_title"), s + 1, C_TITLE, C_BG)
        y = oy + 70 * s // 2 + 20 * s
        fb.text(ox, y, t("ra_setup_line1"), s, C_TEXT, C_BG)
        y += 34 * s
        fb.text(ox, y, RA_CONFIG_FILE, s, accent_for(None), C_BG)
        y += 50 * s
        for key in ("ra_setup_line2", "ra_setup_line3", "ra_setup_line4"):
            fb.text(ox, y, t(key), s - 1 if s > 1 else 1, C_DIM, C_BG)
            y += 28 * s
        hint = t("attract_hint")
        hint_w = len(hint) * 8 * (s - 1 if s > 1 else 1)
        fb.text((W - hint_w) // 2, H - oy - 8 * (s - 1 if s > 1 else 1),
                hint, s - 1 if s > 1 else 1, C_DIM, C_BG)
        fb.flip()
        while True:
            act = self.inp.read_action()
            if act is not None:
                break

    # ------------------------------------------------------------------
    # ERSTEINRICHTUNGS-ASSISTENT (Nutzerwunsch: vereinfachte Installation,
    # einmalig durch alle wichtigen Schritte fuehren) - siehe
    # run_setup_wizard() fuer den Gesamtablauf. Zwei generische
    # Bausteine (Auswahl-Bildschirm, Info-Bildschirm) werden fuer alle
    # acht Schritte wiederverwendet, statt fuer jeden Schritt eigenen
    # Zeichencode zu duplizieren.
    # ------------------------------------------------------------------

    def _wizard_choice(self, title, options, initial=0):
        """Generische Ein-aus-N-Auswahl (gleiches Muster wie
        draw_core_choice_screen()). Hoch/Runter wechselt, OK liefert
        den gewaehlten Index. ESC/back bricht den KOMPLETTEN
        Assistenten ab (liefert None) - der Aufrufer (run_setup_
        wizard()) muss darauf mit einem sofortigen Ruecksprung
        reagieren, OHNE die "erledigt"-Markierung zu setzen."""
        fb = self.fb
        W, H = fb.width, fb.height
        s = max(1, H // 360)
        ox = W * OVERSCAN_X // 100
        oy = H * OVERSCAN_Y // 100
        accent = accent_for(None)
        choice = initial
        while True:
            fb.clear(C_BG)
            title_scale = self._fit_scale(title, W - 2 * ox, s + 1)
            fb.text(ox, oy, title, title_scale, C_TITLE, C_BG)
            y = oy + 70 * s
            for i, label in enumerate(options):
                sel = i == choice
                color = accent if sel else C_TEXT
                prefix = "> " if sel else "  "
                fb.text(ox, y, prefix + label, s, color, C_BG)
                y += 36 * s
            hint = t("wizard_choice_hint")
            sc = s - 1 if s > 1 else 1
            hint_w = len(hint) * 8 * sc
            fb.text((W - hint_w) // 2, H - oy - 8 * sc, hint, sc, C_DIM, C_BG)
            fb.flip()
            act = self.inp.read_action()
            if act in ("up", "left"):
                choice = (choice - 1) % len(options)
            elif act in ("down", "right"):
                choice = (choice + 1) % len(options)
            elif act == "ok":
                return choice
            elif act in ("back", "exit"):
                return None

    def _wizard_info(self, title, lines, skippable=True):
        """Generischer Info-Bildschirm: Text (an Wortgrenzen umgebrochen,
        siehe _wrap_text()) + OK bestaetigt/fahrt fort (True). Bei
        skippable=True kann zusaetzlich mit ESC uebersprungen werden
        (liefert dann False statt True) - der Aufrufer entscheidet
        selbst, ob True/False fuer diesen Schritt ueberhaupt einen
        Unterschied macht (z.B. bei reinen Hinweis-Bildschirmen wie
        dem Esc-Ausstieg-Hinweis egal, bei Download-Bestaetigungen
        wichtig)."""
        fb = self.fb
        W, H = fb.width, fb.height
        s = max(1, H // 360)
        ox = W * OVERSCAN_X // 100
        oy = H * OVERSCAN_Y // 100
        fb.clear(C_BG)
        title_scale = self._fit_scale(title, W - 2 * ox, s + 1)
        fb.text(ox, oy, title, title_scale, C_TITLE, C_BG)
        y = oy + 60 * s
        maxc = max(8, (W - 2 * ox) // (8 * s))
        for line in lines:
            for wrapped in self._wrap_text(line, maxc):
                fb.text(ox, y, wrapped, s, C_TEXT, C_BG)
                y += 24 * s
            y += 10 * s
        hint = t("wizard_skip_hint") if skippable else t("wizard_continue_hint")
        sc = s - 1 if s > 1 else 1
        hint_w = len(hint) * 8 * sc
        fb.text((W - hint_w) // 2, H - oy - 8 * sc, hint, sc, C_DIM, C_BG)
        fb.flip()
        while True:
            act = self.inp.read_action()
            if act == "ok":
                return True
            if act in ("back", "exit") and skippable:
                return False
            if act is not None and not skippable:
                return True

    def _wizard_scanning_step(self, title):
        """Schritt 7: Spiele suchen (erzwungener Neu-Scan, mit
        Fortschrittsanzeige). Nutzerwunsch: Hinweis, dass es bei
        vielen ROMs etwas dauern kann, damit niemand meint, das
        Frontend sei abgestuerzt/eingefroren."""
        fb = self.fb
        W, H = fb.width, fb.height
        s = max(1, H // 360)
        ox = W * OVERSCAN_X // 100
        oy = H * OVERSCAN_Y // 100

        def progress_cb(i, total, name):
            fb.clear(C_BG)
            title_scale = self._fit_scale(title, W - 2 * ox, s + 1)
            fb.text(ox, oy, title, title_scale, C_TITLE, C_BG)
            y = oy + 60 * s
            maxc = max(8, (W - 2 * ox) // (8 * s))
            for wrapped in self._wrap_text(t("wizard_scan_patience"), maxc):
                fb.text(ox, y, wrapped, s, C_DIM, C_BG)
                y += 24 * s
            y += 16 * s
            fb.text(ox, y, t("wizard_scan_progress", i, total, name), s, C_TEXT, C_BG)
            fb.flip()

        self.cats = scan_games(force=True, progress_cb=progress_cb)
        n_sys = len(self.cats)
        n_games = sum(_count_tree_items(node) for _n, node, _sk in self.cats
                     if isinstance(node, dict))
        self._wizard_info(
            title, [t("wizard_scan_done", n_sys, n_games)], skippable=False)

    def run_setup_wizard(self):
        """Ersteinrichtungs-Assistent - fuehrt (automatisch beim
        allerersten Start, danach jederzeit ueber das System-Menue
        erneut aufrufbar) durch acht Schritte: Sprache, CRT/HDMI,
        Zeitzone, RetroAchievements (Info), Boxart-Download,
        Gameinfo-Download, Spiele-Suche, Esc-Ausstieg-Hinweis.

        Bricht bei einem bewussten ESC auf einem AUSWAHL-Bildschirm
        sofort und vollstaendig ab (kein Schritt danach, KEINE
        "erledigt"-Markierung gesetzt - erscheint dann beim naechsten
        Start erneut). Reine Info-/Download-Schritte lassen sich
        dagegen einzeln ueberspringen, ohne den ganzen Assistenten
        abzubrechen."""
        total = 8

        # Schritt 1: Sprache
        lang_options = ["Deutsch", "English"]
        idx = 0 if current_lang() == "de" else 1
        choice = self._wizard_choice(
            t("wizard_step_title", 1, total, t("wizard_step_language")),
            lang_options, initial=idx)
        if choice is None:
            return
        set_language("de" if choice == 0 else "en")

        # Schritt 2: CRT/HDMI (Aenderung braucht einen Neustart - wird
        # angewendet, der Assistent laeuft aber in der AKTUELLEN
        # Aufloesung zu Ende, statt eine komplexe "Assistent nach
        # Neustart fortsetzen"-Logik zu bauen).
        video_options = [t("sys_video_hdmi"), t("sys_video_crt")]
        idx2 = 1 if crt_menu_active() else 0
        choice2 = self._wizard_choice(
            t("wizard_step_title", 2, total, t("wizard_step_video")),
            video_options, initial=idx2)
        if choice2 is None:
            return
        want_crt = (choice2 == 1)
        if want_crt != crt_menu_active():
            toggle_crt_menu()
            # SICHERHEITSNETZ (siehe Kommentar bei mark_crt_pending_confirm()
            # in fe/settings.py): nur beim Wechsel IN den CRT-Modus setzen -
            # der naechste Boot ueberwacht dann automatisch, ob ueberhaupt
            # eine Eingabe ankommt, und wechselt sonst von selbst zurueck.
            if want_crt:
                mark_crt_pending_confirm()
            else:
                clear_crt_pending_confirm()
            self._wizard_info(
                t("wizard_step_title", 2, total, t("wizard_step_video")),
                [t("wizard_video_reboot_note")], skippable=False)

        # Schritt 3: Zeitzone (wiederholbar zyklisch, wie im System-
        # Menue - "Weiter" als eigene, zweite Option in dieser
        # Auswahl statt einer neuen Interaktionsart).
        while True:
            tz_label = format_timezone_offset(load_timezone_offset())
            choice3 = self._wizard_choice(
                t("wizard_step_title", 3, total, t("wizard_step_timezone")),
                [t("wizard_timezone_current", tz_label),
                 t("wizard_continue_option")], initial=1)
            if choice3 is None:
                return
            if choice3 == 0:
                cycle_timezone_offset()
                continue
            break
        threading.Thread(target=sync_system_clock_from_ntp, daemon=True).start()

        # Schritt 4: RetroAchievements - reiner Info-Bildschirm (keine
        # Bildschirmtastatur, Einrichtung passiert extern per SSH) -
        # der bereits bestehende draw_ra_setup_screen() wird direkt
        # wiederverwendet statt eines eigenen, aehnlichen Bildschirms.
        self.draw_ra_setup_screen()

        # Schritt 5: Boxart-Download - optional, ueberspringbar.
        do_boxart = self._wizard_choice(
            t("wizard_step_title", 5, total, t("wizard_step_boxart")),
            [t("wizard_download_now"), t("wizard_download_skip")], initial=0)
        if do_boxart is None:
            return
        if do_boxart == 0:
            profile = "sd" if want_crt else "hd"
            self.run_script(os.path.join(SCRIPTS_DIR, "Frontend_Boxart_Download.sh"),
                            args=[profile])

        # Schritt 6: Gameinfo-Download - optional, ueberspringbar.
        do_gameinfo = self._wizard_choice(
            t("wizard_step_title", 6, total, t("wizard_step_gameinfo")),
            [t("wizard_download_now"), t("wizard_download_skip")], initial=0)
        if do_gameinfo is None:
            return
        if do_gameinfo == 0:
            self.run_script(os.path.join(SCRIPTS_DIR, "Frontend_Gameinfo_Download.sh"))

        # Schritt 7: Spiele suchen (erzwungener Neu-Scan mit Fortschritt).
        self._wizard_scanning_step(
            t("wizard_step_title", 7, total, t("wizard_step_scan")))

        # Schritt 8: Esc-Ausstieg-Hinweis (reiner Hinweis, ESC hier
        # bedeutet "verstanden, weiter" statt "abbrechen" - skippable=
        # True, aber run_setup_wizard() behandelt False identisch zu
        # True, da es hier nichts zu ueberspringen gibt ausser dem
        # Lesen selbst).
        self._wizard_info(
            t("wizard_step_title", 8, total, t("wizard_step_esc_hint")),
            [t("wizard_esc_hint_1"), t("wizard_esc_hint_2")], skippable=True)

        mark_setup_wizard_done()
        self.build_categories()   # Sprache/Video koennten sich geaendert haben

    def _active_vt(self):
        try:
            return open("/sys/class/tty/tty0/active").read().strip()
        except OSError:
            return "?"

    def _boot_watch(self):
        """Reine Diagnose: die ersten 30s nach dem Start den Anzeige-
        Zustand (aktive VT + CORENAME) protokollieren. Im Erfolgsfall
        bleibt die VT auf tty1 (Konsolenmodus, Frontend sichtbar). Holt
        der bootende MiSTer die Anzeige zurueck, taucht das hier als
        VT-Wechsel auf - genau die Signatur, die fuer eine gezielte
        Diagnose des Soft-Reboot-Problems gebraucht wird. Aendert selbst
        nichts am Verhalten, protokolliert nur."""
        el = time.monotonic() - self._boot_time
        if el > 30.0:
            return
        now = time.monotonic()
        if now - self._last_vt_check < 1.0:
            return
        self._last_vt_check = now
        vt = self._active_vt()
        try:
            core = open(CORENAME).read().strip("\x00 \n\r\t")
        except OSError:
            core = "?"
        state = (vt, core)
        changed = state != self._last_bootstate
        if changed or now - self._last_snapshot > 5.0:
            LOG("boot-watch +%02.0fs: VT=%s CORENAME=%s%s"
                % (el, vt, core, "   <-- AENDERUNG" if changed else ""))
            self._last_bootstate = state
            self._last_snapshot = now

    def _play_ducked_sfx(self, name):
        """Spielt EINEN Soundeffekt (SFX_DIR/<name>.mp3 bevorzugt, sonst
        <name>.wav) GARANTIERT hoerbar ab - unabhaengig von der SFX-Ein/
        Aus-Einstellung und unabhaengig davon, ob gerade Musik laeuft
        (wird in dem Fall kurz gedaempft/gestoppt und danach automatisch
        fortgesetzt). Gedacht fuer bewusste, seltene Benachrichtigungen
        (geheimer Sound, Erfolgs-Jingle) - NICHT fuer haeufige
        Navigations-Klicks, dafuer bleibt weiterhin das normale
        play_sfx() mit seiner Drossel/Ein-Aus-Pruefung zustaendig.

        Verallgemeinert aus der urspruenglich nur fuer den geheimen
        Sound gebauten Fassung (Nutzerwunsch: "sobald einer den
        geheimen Sound aktiviert muss der hoerbar sein" - bisher lief
        das ueber das normale play_sfx(), das den Sound STUMM
        uebersprang, sobald entweder Musik lief ODER die normalen
        Navigations-Soundeffekte deaktiviert waren). Jetzt genauso fuer
        Erfolgs-Pop-ups genutzt (Nutzerwunsch: "dazu einen Jingle
        abspielen, andere Sachen wie MP3/Radio muessten kurz
        verstummen").

        Laeuft komplett in einem Hintergrund-Thread (nicht-blockierend,
        gleiches Prinzip wie cycle_source()).

        BUGFIX (Nutzer-Rueckmeldung: "Sound kommt beim Code, aber MP3/
        Radio pausiert nicht dabei, es kommt zur Ueberlagerung und faengt
        das Stottern an"): bei einer Erst-Freischaltung ruft
        _on_secret_triggered() diese Funktion oft ZWEIMAL kurz
        hintereinander auf (allgemeiner Erfolgs-Ton, direkt gefolgt vom
        eigenen Theme-/Raum-/Chiptune-Ton). Jeder Aufruf startete bisher
        einen komplett eigenstaendigen Thread, der unabhaengig von den
        anderen die Musik anhielt/neu startete und seine eigene mpg123/
        aplay-Instanz startete - zwei Aufrufe kurz hintereinander liefen
        dadurch teilweise GLEICHZEITIG (zwei Sound-Dateien gleichzeitig
        auf derselben Audioausgabe), und der zuerst fertige Aufruf
        startete die Musik bereits wieder, waehrend der zweite Sound noch
        lief. Jetzt ueber music._jingle_count_lock/_jingle_depth
        koordiniert (siehe Kommentar in fe/audio.py, MusicPlayer.
        __init__): nur der ERSTE gleichzeitig aktive Aufruf haelt die
        Musik an, nur der LETZTE startet sie wieder, und
        music._jingle_play_lock sorgt dafuer, dass die Sound-Dateien
        selbst bei mehreren nahezu gleichzeitigen Aufrufen strikt
        NACHEINANDER abgespielt werden statt sich zu ueberlagern."""
        mp3_path = os.path.join(SFX_DIR, name + ".mp3")
        wav_path = os.path.join(SFX_DIR, name + ".wav")
        use_mp3 = os.path.exists(mp3_path) and os.path.exists(MPG123_BIN)
        if not use_mp3 and not os.path.exists(wav_path):
            return   # kein Sound fuer diesen Namen hinterlegt
        music = self.music

        def _worker():
            with music._jingle_count_lock:
                first = music._jingle_depth == 0
                if first:
                    music._jingle_was_playing = (music._proc_alive()
                                                  and not music.paused_for_core)
                music._jingle_depth += 1
                # paused_for_jingle UEBER die gesamte Dauer gesetzt (nicht
                # erst kurz vor dem eigentlichen Abspielen) - tick() laeuft
                # staendig im Haupt-Loop und wuerde sonst genau in einer
                # Luecke selbst versuchen, die Musik neu zu starten.
                music.paused_for_jingle = True
            if first and music._jingle_was_playing:
                music._stop_current()
            try:
                # Serialisiert NUR das eigentliche Abspielen - zwei
                # nahezu gleichzeitige ducked-Sounds spielen dadurch
                # sauber nacheinander, ohne dass die Musik zwischendurch
                # (faelschlich) wieder anspringt.
                with music._jingle_play_lock:
                    try:
                        if use_mp3:
                            cmd = [MPG123_BIN, "-q", "-f", _mpg_scale(), mp3_path]
                        else:
                            cmd = ["aplay", "-q", wav_path]
                        proc = subprocess.Popen(
                            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            stdin=subprocess.DEVNULL)
                        proc.wait()
                    except OSError:
                        pass
            finally:
                with music._jingle_count_lock:
                    music._jingle_depth -= 1
                    last = music._jingle_depth == 0
                    if last:
                        music.paused_for_jingle = False
                if last and music._jingle_was_playing and music.enabled \
                        and not music.paused_for_core:
                    music._start_current()

        threading.Thread(target=_worker, daemon=True).start()

    def _play_secret_sound(self):
        """Duenner, namensgleicher Wrapper um _play_ducked_sfx() - alle
        Aufrufstellen (siehe _on_secret_triggered()) bleiben unveraendert."""
        self._play_ducked_sfx("secret_found")

    def _on_secret_triggered(self, secret_id, is_new):
        """Wird aufgerufen, sobald ein Geheimcode
        erfolgreich erkannt wurde (siehe run()) - fuehrt die eigentliche
        Aktion aus (Theme wechseln/Entwicklerraum oeffnen/Sound
        abspielen), JEDES MAL wenn der Code eingegeben wird, nicht nur
        beim allerersten Mal - passend zum Vorbild echter Cheat-Codes,
        die man beliebig oft eingeben kann. Die "neu freigeschaltet"-
        Meldung erscheint dagegen nur einmalig (is_new)."""
        if is_new:
            # BUGFIX (siehe Kommentar in _play_ducked_sfx()): frueher
            # zusaetzlich ein direkter play_sfx("achievement", ...)-Aufruf
            # hier - reines Ueberbleibsel aus der Zeit VOR
            # _play_ducked_sfx() (das den Ton bereits garantiert hoerbar
            # UND sauber gedaempft abspielt). Die beiden liefen parallel
            # und ueberlagerten sich hoerbar mit sich selbst.
            self._play_ducked_sfx("achievement")
            self.draw(message=t("secret_unlocked", t("secret_name_" + secret_id)))
        if secret_id == "secret_theme_1":
            apply_theme("secret_gold")
            try:
                dirname = os.path.dirname(THEME_FILE)
                if dirname:
                    os.makedirs(dirname, exist_ok=True)
                with open(THEME_FILE, "w") as f:
                    f.write("secret_gold")
            except OSError:
                pass
            # NEU (Nutzerwunsch: eigener Sound je Geheimnis/Theme, siehe
            # SFX_DIR/secret_theme_1.mp3 bzw. der synthetische Ersatzton
            # in SFX_CHIME_DEFS) - bisher spielte dieser Zweig ueberhaupt
            # keinen Ton ab, obwohl _play_ducked_sfx() (Musik kurz
            # pausieren, Sound abspielen, danach automatisch fortsetzen)
            # laengst existiert und fuer die 9 Konsolen-Themes weiter
            # unten schon genau so genutzt wird.
            self._play_ducked_sfx("secret_theme_1")
            self.draw()
        elif secret_id == "entwicklerraum":
            # NEU (Nutzerwunsch, siehe Kommentar bei "secret_theme_1"
            # oben): eigener Sound beim Betreten des Entwicklerraums -
            # laeuft nicht-blockierend im Hintergrund (siehe
            # _play_ducked_sfx()), startet also schon waehrend der Raum
            # gezeichnet wird.
            self._play_ducked_sfx("entwicklerraum")
            self.draw_dev_room_screen()
            self.draw()
        elif secret_id == "secret_sound":
            self._play_secret_sound()
            if not is_new:
                self.draw(message=t("secret_sound_replay"))
        elif secret_id == "rainbow_cursor":
            # Faerbt den Auswahl-Cursor im Hauptmenue (_draw_cat_row())
            # fuer eine begrenzte Zeit in Regenbogenfarben statt der
            # System-Akzentfarbe - siehe dort fuer die genaue Anwendung.
            # Bewusst NUR die Kategorien-Auswahl betroffen, nicht die
            # ganze Oberflaeche (Cover-Raender, Statistik-Bildschirme
            # usw. bleiben unveraendert) - kleineres, klar abgegrenztes
            # Risiko als eine globale Farbaenderung.
            self._rainbow_cursor_until = time.monotonic() + RAINBOW_CURSOR_SECONDS
            self.draw()
        elif secret_id == "chiptune_sound":
            self._play_ducked_sfx("chiptune")
        elif secret_id in SECRET_THEME_META:
            # Die 9 neuen Konsolen-Themes (siehe SECRET_THEME_META ganz
            # oben) - EIN gemeinsamer Zweig statt neun fast identischer
            # elif-Bloecke, weil sich Theme setzen/speichern, Sound
            # abspielen und Flourish zeigen fuer alle neun exakt gleich
            # abspielen und sich nur die Daten (Theme-Name, Sound-Datei,
            # Anzeigetext, Akzentfarbe) unterscheiden.
            meta = SECRET_THEME_META[secret_id]
            apply_theme(meta["theme"])
            try:
                dirname = os.path.dirname(THEME_FILE)
                if dirname:
                    os.makedirs(dirname, exist_ok=True)
                with open(THEME_FILE, "w") as f:
                    f.write(meta["theme"])
            except OSError:
                pass
            self._play_ducked_sfx(secret_id)
            accent = THEMES[meta["theme"]]["C_ACCENT"]
            self._show_theme_unlock_flourish(t(meta["flourish"]), accent)
            # Zusatzwirkung (aktuell nur N64): rein additiv, siehe
            # Kommentar bei SECRET_THEME_META - schaltet den Schalter nur
            # EIN, nie wieder aus, und nur wenn er noch aus war.
            if meta.get("enable_fast_scroll") and not fast_scroll_enabled():
                toggle_fast_scroll()
            self.draw()

    def _rainbow_color(self, phase):
        """Leichte Regenbogenfarbe ohne zusaetzliche Abhaengigkeit -
        drei um 120 Grad phasenverschobene Sinuswellen (klassischer,
        billiger Trick fuer weiche RGB-Uebergaenge). phase in Sekunden,
        z.B. time.monotonic()."""
        r = int(127 + 127 * math.sin(phase))
        g = int(127 + 127 * math.sin(phase + 2.0944))    # +120 Grad
        b = int(127 + 127 * math.sin(phase + 4.1888))    # +240 Grad
        return (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))

    def _check_achievement_popup(self):
        """Prueft auf neu erreichte Erfolge und liefert bei einem
        Treffer die fertige Popup-Nachricht (spielt dabei den
        Erfolgston ab) - sonst None. Aufrufer entscheiden selbst, ob/
        wie sie das anzeigen (z.B. anstelle ihrer eigenen
        Standardmeldung wie "Favorit hinzugefuegt")."""
        newly = check_new_achievements()
        if not newly:
            return None
        # BUGFIX (siehe Kommentar in _play_ducked_sfx()): kein
        # zusaetzlicher play_sfx(...)-Aufruf mehr hier - lief bisher
        # parallel zu _play_ducked_sfx() und ueberlagerte sich damit
        # hoerbar selbst.
        self._play_ducked_sfx("achievement")
        if len(newly) == 1:
            return t("achievement_popup", t(newly[0]))
        return t("achievement_popup_multi", len(newly))

    def _notify_new_achievements(self):
        """Wie _check_achievement_popup(), zeigt eine gefundene
        Meldung aber direkt an - fuer Stellen ohne eigene
        Standardmeldung (z.B. nach der Rueckkehr aus einem Spiel)."""
        msg = self._check_achievement_popup()
        if msg:
            self.draw(message=msg)

    def draw_ra_showcase_screen(self, game_name, game_id):
        """RA-Erfolgs-Vitrine (Nutzerwunsch, BEWUSST als separate,
        eigenstaendige Option von der bisherigen RA-Anzeige gebaut -
        aendert nichts an Cover-Fortschritt/Erfolgsjaeger/Trophaeenraum)
        - komplette Erfolgsliste EINES Spiels (Name, Beschreibung,
        Punkte, freigeschaltet/nicht). Holt die Daten live bei jedem
        Aufruf (bounded, kein eigener Cache in dieser ersten Fassung -
        das kann spaeter ergaenzt werden, sobald sich das Format in
        der Praxis bewaehrt hat). Scrollt wie die anderen Vollbild-
        Listen (Top-10/Erfolge), falls nicht alles passt."""
        fb = self.fb
        W, H = fb.width, fb.height
        s = max(1, H // 360)
        ox = W * OVERSCAN_X // 100
        oy = H * OVERSCAN_Y // 100
        hint_scale = s - 1 if s > 1 else 1
        title = t("ra_showcase_title", game_name)
        title_scale = self._fit_scale(title, W - 2 * ox, s + 1)
        list_y0 = oy + 56 * s // 2 + 30 * s

        fb.clear(C_BG)
        fb.text(ox, oy, title, title_scale, C_TITLE, C_BG)
        fb.text(ox, list_y0, t("ra_showcase_loading"), s, C_DIM, C_BG)
        fb.flip()

        # NEUES FEATURE (Nutzerwunsch: "dauert ganz schoen bis die
        # Erfolge angezeigt werden, kann man das speichern?"): hier
        # (im Gegensatz zum Hintergrund-Watcher weiter oben in dieser
        # Datei, der bewusst UNGECACHT bleibt, um neu verdiente Erfolge
        # waehrend des Spielens zeitnah zu erkennen) macht ein Cache
        # Sinn - man sieht sich hier ein SCHON BEENDETES Spiel an,
        # wiederholtes F6 fuer dasselbe Spiel muss nicht jedes Mal neu
        # ueber das Netz gehen.
        achievements = fetch_ra_game_achievements_cached(game_id, timeout=5.0)

        def wait_any_key():
            while True:
                act = self.inp.read_action()
                if act is not None:
                    return

        if achievements is None:
            fb.clear(C_BG)
            fb.text(ox, oy, title, title_scale, C_TITLE, C_BG)
            fb.text(ox, list_y0, t("ra_showcase_error"), s, C_DIM, C_BG)
            fb.flip()
            wait_any_key()
            return
        if not achievements:
            fb.clear(C_BG)
            fb.text(ox, oy, title, title_scale, C_TITLE, C_BG)
            fb.text(ox, list_y0, t("ra_showcase_empty"), s, C_DIM, C_BG)
            fb.flip()
            wait_any_key()
            return

        # Icons VOR der eigentlichen Anzeige-Schleife laden/dekodieren
        # (waehrend noch "Laedt..." zu sehen ist) - haelt das spaetere
        # Scrollen selbst frei von Netzwerkzugriffen, kein Ruckeln beim
        # ersten Sichtbarwerden eines neuen Eintrags. BadgeCache cacht
        # ohnehin pro Name, ein doppelter Abruf fuer dasselbe Badge
        # (z.B. mehrere Erfolge mit identischem Icon) kostet dadurch
        # praktisch nichts.
        for name, desc, points, badge, earned, date, hardcore in achievements:
            if badge:
                BADGES.get(badge)

        list_y1 = H - oy - 8 * hint_scale - 6 * s
        rowh = 22 * s
        icon_size = 2 * rowh - 4 * s
        text_x = ox + icon_size + 10 * s
        maxc = max(8, (W - text_x - ox) // (8 * s))
        visible = max(1, (list_y1 - list_y0) // (rowh * 2))
        scroll = 0
        max_scroll = max(0, len(achievements) - visible)
        # BUGFIX (beim Erstellen von Beispiel-Screenshots aufgefallen):
        # die Icon-Aufbereitung (Kanaltausch RGBA->BGRA, Abdunklung fuer
        # nicht freigeschaltete Erfolge, Skalierung) lief bisher bei
        # JEDEM einzelnen Neuzeichnen neu - auch beim blossen Scrollen,
        # obwohl sich am Icon selbst nichts aendert. Gemessen: ca. 11ms
        # allein dafuer bei 4 sichtbaren Icons UND EINEM Neuzeichnen -
        # bei jedem Scroll-Schritt, auf einer eher schwachen CPU
        # potenziell noch deutlich mehr. Fix: fertig aufbereitete Icons
        # pro (Badge, freigeschaltet, Groesse) zwischenspeichern - exakt
        # dieselbe Cache-Philosophie wie ArtCache/BadgeCache im Rest des
        # Projekts, hier nur lokal fuer die Dauer dieses Bildschirms.
        processed_cache = {}
        def get_processed_icon(badge, earned):
            key = (badge, earned)
            if key in processed_cache:
                return processed_cache[key]
            icon = BADGES.get(badge) if badge else None
            if not icon:
                processed_cache[key] = None
                return None
            iw, ih, rgba = icon
            bgra = bytearray(rgba)
            bgra[0::4], bgra[2::4] = bgra[2::4], bgra[0::4]
            if not earned:
                for k in range(0, len(bgra), 4):
                    bgra[k] = bgra[k] * 2 // 5
                    bgra[k + 1] = bgra[k + 1] * 2 // 5
                    bgra[k + 2] = bgra[k + 2] * 2 // 5
            scaled = bytearray(icon_size * icon_size * 4)
            for py in range(icon_size):
                sy = py * ih // icon_size
                for px in range(icon_size):
                    sx = px * iw // icon_size
                    so = (sy * iw + sx) * 4
                    do = (py * icon_size + px) * 4
                    scaled[do:do + 4] = bgra[so:so + 4]
            result = bytes(scaled)
            processed_cache[key] = result
            return result
        while True:
            fb.clear(C_BG)
            fb.text(ox, oy, title, title_scale, C_TITLE, C_BG)
            y = list_y0
            for i in range(scroll, min(scroll + visible, len(achievements))):
                name, desc, points, badge, earned, date, hardcore = achievements[i]
                scaled_icon = get_processed_icon(badge, earned)
                if scaled_icon:
                    self.blit(ox, y, icon_size, icon_size, scaled_icon)
                # NEU (Nutzerwunsch: "wir unterscheiden gar nicht zwischen
                # Softcore- oder Hardcore-Mode bei den Erfolgen"): statt
                # eines einzigen "[x]" fuer "irgendwie erreicht" zeigt die
                # Markierung jetzt, in welchem Modus - "[HC]" gold
                # hervorgehoben fuer Hardcore, "[SC]" in der normalen
                # Erreicht-Farbe fuer Softcore-Erfolge, "[ ]" gedimmt wie
                # bisher fuer noch nicht freigeschaltete. Kommt direkt aus
                # dem schon abgerufenen "hardcore"-Feld (siehe
                # fetch_ra_game_achievements() in fe/retroachievements.py),
                # kein zusaetzlicher RA-Aufruf noetig.
                if hardcore:
                    mark = "[HC] "
                elif earned:
                    mark = "[SC] "
                else:
                    mark = "[ ] "
                line1 = "%s%s (%d)" % (mark, name, points)
                color = C_RA_HARDCORE if hardcore else (C_TEXT if earned else C_DIM)
                # BUGFIX (Nutzer-Rueckmeldung, gleiche Ursache wie bei
                # anderen Info-Bildschirmen): Name+Punkte wird an
                # Wortgrenzen umgebrochen statt hart abgeschnitten -
                # nur die erste umgebrochene Zeile wird gezeigt (Namen
                # sind fast immer kurz genug fuer eine Zeile).
                fb.text(text_x, y, self._wrap_text(line1, maxc)[0], s, color, C_BG)
                y += rowh
                # Beschreibung darf bis zu ZWEI kleinere Unterzeilen
                # im ohnehin reservierten Platz nutzen (rowh bleibt
                # insgesamt gleich, damit Symbol-Hoehe/Scroll-Mathematik
                # unveraendert bleiben) - deutlich seltener abgeschnitten
                # als vorher, wo IMMER nur eine Zeile zur Verfuegung stand.
                desc_maxc = max(8, (W - text_x - ox) // (8 * hint_scale))
                desc_lines = self._wrap_text(desc, desc_maxc)[:2]
                sub_h = rowh // 2
                for dl in desc_lines:
                    fb.text(text_x, y, dl, hint_scale, C_DIM, C_BG)
                    y += sub_h
                y += rowh - len(desc_lines) * sub_h
            if max_scroll > 0:
                scroll_hint = t("top10_scroll_hint", scroll + 1,
                                min(scroll + visible, len(achievements)),
                                len(achievements))
                hint_w = len(scroll_hint) * 8 * hint_scale
                fb.text((W - hint_w) // 2, H - oy - 8 * hint_scale,
                        scroll_hint, hint_scale, C_DIM, C_BG)
            else:
                hint = t("attract_hint")
                hint_w = len(hint) * 8 * hint_scale
                fb.text((W - hint_w) // 2, H - oy - 8 * hint_scale,
                        hint, hint_scale, C_DIM, C_BG)
            fb.flip()
            act = self.inp.read_action()
            if act in ("up", "down") and max_scroll > 0:
                scroll = max(0, min(max_scroll, scroll + (1 if act == "down" else -1)))
                continue
            if act is not None:
                break

    def draw_secrets_screen(self):
        """Uebersicht aller bekannten Geheimnisse (Nutzerwunsch: "Easter
        Egg System") - "???" fuer noch nicht Gefundenes, Name +
        Herkunfts-Hinweis nach dem Entdecken. Bewusst OHNE die genaue
        Code-Sequenz selbst zu verraten - sonst waere es kein Geheimnis
        mehr.

        BUGFIX (Nutzer-Rueckmeldung): frueher als "kurze, feste Liste,
        kein Scrollen noetig" gebaut - stimmte auf CRT nicht mehr:
        lange Zeilen (z.B. der Tastatur-Hinweis) wurden einfach mit
        "~" abgeschnitten, der Rest war unlesbar, UND es fehlte
        Scrollen fuer den Fall, dass spaeter mehr Geheimnisse
        dazukommen. Jetzt: echter Zeilenumbruch (_wrap_text()) statt
        Abschneiden, UND scrollbar wie draw_milestones_screen()."""
        fb = self.fb
        W, H = fb.width, fb.height
        s = max(1, H // 360)
        ox = W * OVERSCAN_X // 100
        oy = H * OVERSCAN_Y // 100
        title = t("secrets_title")
        title_scale = self._fit_scale(title, W - 2 * ox, s + 1)
        maxc = max(8, (W - 2 * ox) // (8 * s))

        unlocked = _load_secrets_unlocked()

        rows = []
        for line in self._wrap_text(
                t("secrets_summary", len(unlocked), len(SECRET_CODES) + 1), maxc):
            rows.append((line, accent_for(None), 0))
        for line in self._wrap_text(t("secrets_keyboard_hint"), maxc):
            rows.append((line, C_DIM, 0))
        rows.append(("", C_DIM, 0))

        order = ["secret_theme_1", "entwicklerraum", "secret_sound"]
        order = ["secret_theme_1", "entwicklerraum", "secret_sound",
                 "rainbow_cursor", "chiptune_sound", DEV_ROOM_BONUS_ID]
        # Die 9 neuen Konsolen-Themes (SECRET_THEME_META) in derselben
        # Reihenfolge wie dort definiert - haengen einfach hinten an,
        # damit die bereits bekannten Geheimnisse ihre Position behalten.
        order = order + list(SECRET_THEME_META.keys())
        for secret_id in order:
            found = secret_id in unlocked
            mark = "[x] " if found else "[ ] "
            name = t("secret_name_" + secret_id) if found else t("hidden_mystery")
            for line in self._wrap_text(mark + name, maxc):
                rows.append((line, C_TEXT if found else C_DIM, 0))
            if found:
                for line in self._wrap_text(
                        t("secret_origin_" + secret_id), max(4, maxc - 2)):
                    rows.append((line, C_DIM, 1))
            rows.append(("", C_DIM, 0))

        rowh = 22 * s
        list_y0 = oy + 44 * s
        hint_scale = s - 1 if s > 1 else 1
        list_y1 = H - oy - 8 * hint_scale - 6 * s
        visible = max(1, (list_y1 - list_y0) // rowh)
        scroll = 0
        max_scroll = max(0, len(rows) - visible)
        while True:
            fb.clear(C_BG)
            fb.text(ox, oy, title, title_scale, C_TITLE, C_BG)
            y = list_y0
            for text, color, indent in rows[scroll:scroll + visible]:
                fb.text(ox + indent * 16 * s, y, text, s, color, C_BG)
                y += rowh
            if max_scroll > 0:
                scroll_hint = t("top10_scroll_hint", scroll + 1,
                                min(scroll + visible, len(rows)), len(rows))
                hint_w = len(scroll_hint) * 8 * hint_scale
                fb.text((W - hint_w) // 2, H - oy - 8 * hint_scale,
                        scroll_hint, hint_scale, C_DIM, C_BG)
            else:
                hint = t("attract_hint")
                hint_w = len(hint) * 8 * hint_scale
                fb.text((W - hint_w) // 2, H - oy - 8 * hint_scale,
                        hint, hint_scale, C_DIM, C_BG)
            fb.flip()
            act = self.inp.read_action()
            if act in ("up", "down") and max_scroll > 0:
                scroll = max(0, min(max_scroll, scroll + (1 if act == "down" else -1)))
                continue
            if act is not None:
                break

    def draw_credits_screen(self):
        """Credits (Nutzerwunsch) - wer das Frontend gebaut hat und wer
        mitgeholfen hat. Anders als der Entwicklerraum (Geheimnis,
        siehe draw_dev_room_screen()) ein normaler, sichtbarer
        Menuepunkt im System-Menue - kein Versteckspiel, einfach ein
        Danke.

        BUGFIX (Nutzer-Rueckmeldung): auf CRT wurde z.B. "TheRealSutefan
        - patches, RA tools, bugfixes" einfach mit "~" abgeschnitten,
        UND es fehlte Scrollen, falls der Inhalt (mit mehr Mitwirkenden)
        mal nicht mehr auf einen Bildschirm passt. Jetzt: echter
        Zeilenumbruch (_wrap_text()) statt Abschneiden, UND scrollbar
        wie draw_milestones_screen()."""
        fb = self.fb
        W, H = fb.width, fb.height
        s = max(1, H // 360)
        ox = W * OVERSCAN_X // 100
        oy = H * OVERSCAN_Y // 100
        title = t("credits_title")
        title_scale = self._fit_scale(title, W - 2 * ox, s + 1)
        maxc = max(8, (W - 2 * ox) // (8 * s))

        rows = []

        def heading(text):
            rows.append((text, accent_for(None), 0))

        def entry(text):
            for line in self._wrap_text(text, max(4, maxc - 2)):
                rows.append((line, C_TEXT, 1))

        heading(t("credits_creator_heading"))
        entry(t("credits_creator_entry"))
        rows.append(("", C_DIM, 0))
        heading(t("credits_contrib_heading"))
        entry(t("credits_contrib_sutefan"))
        entry(t("credits_contrib_dfense"))
        entry(t("credits_contrib_dennsen"))
        rows.append(("", C_DIM, 0))
        heading(t("credits_thanks_heading"))
        entry(t("credits_thanks_entry"))

        rowh = 24 * s
        list_y0 = oy + 44 * s
        hint_scale = s - 1 if s > 1 else 1
        list_y1 = H - oy - 8 * hint_scale - 6 * s
        visible = max(1, (list_y1 - list_y0) // rowh)
        scroll = 0
        max_scroll = max(0, len(rows) - visible)
        while True:
            fb.clear(C_BG)
            fb.text(ox, oy, title, title_scale, C_TITLE, C_BG)
            y = list_y0
            for text, color, indent in rows[scroll:scroll + visible]:
                fb.text(ox + indent * 16 * s, y, text, s, color, C_BG)
                y += rowh
            if max_scroll > 0:
                scroll_hint = t("top10_scroll_hint", scroll + 1,
                                min(scroll + visible, len(rows)), len(rows))
                hint_w = len(scroll_hint) * 8 * hint_scale
                fb.text((W - hint_w) // 2, H - oy - 8 * hint_scale,
                        scroll_hint, hint_scale, C_DIM, C_BG)
            else:
                hint = t("attract_hint")
                hint_w = len(hint) * 8 * hint_scale
                fb.text((W - hint_w) // 2, H - oy - 8 * hint_scale,
                        hint, hint_scale, C_DIM, C_BG)
            fb.flip()
            act = self.inp.read_action()
            if act in ("up", "down") and max_scroll > 0:
                scroll = max(0, min(max_scroll, scroll + (1 if act == "down" else -1)))
                continue
            if act is not None:
                break

    def draw_dev_room_screen(self):
        """Entwicklerraum (Nutzerwunsch: "Easter Egg System") - Geheimnis,
        ausgeloest durch einen Geheimcode (siehe SECRET_CODES). Rein
        informativ/persoenlich, beliebige Taste kehrt zurueck. Zeigt
        einige "hinter den Kulissen"-Angaben, die sich aus bereits
        vorhandenen Daten ergeben (Frontend-Level, gefundene Geheimnisse)
        - keine neue Datenquelle noetig.

        ERWEITERT (Nutzerwunsch: "ein Geheimnis im Geheimnis"): waehrend
        man sich HIER befindet, wird zusaetzlich ein eigener, kurzer
        Tasten-Puffer gefuehrt (DEV_ROOM_BONUS_CODE) - komplett getrennt
        vom Hauptmenue-Mechanismus (der laeuft nur auf Seite 0, siehe
        run(), und erreicht diesen Bildschirm gar nicht). Passt die
        Eingabe zum Bonus-Code, bleibt der Bildschirm STEHEN (neu
        gezeichnet, jetzt mit der Bonus-Zeile) statt wie sonst bei jeder
        Taste sofort zu verlassen - jede ANDERE Eingabe, die keine
        gueltige Teilsequenz des Bonus-Codes ist, verlaesst weiterhin
        wie bisher sofort den Raum.

        BUGFIX (Nutzer-Rueckmeldung: "kann den EGG-Code nicht eingeben,
        der Raum wird sofort wieder verlassen"): frueher zeichnete diese
        Methode den Bildschirm EINMAL und wartete dort per read_action()
        auf eine erste, komplett verworfene Taste ("bloss zum Bestaetigen
        des Betretens"), BEVOR die eigentliche Bonus-Code-Erkennung
        (nested_buffer-Schleife) ueberhaupt anfing zuzuhoeren. Genau
        dieser erste Tastendruck war beim Eintippen von "EGG" aber
        bereits das "E" - es verschwand spurlos in dieser Warteschleife,
        die Erkennung sah nur noch "G" als vermeintlich ERSTEN Buchstaben,
        der nicht zum Code passte, und verliess den Raum sofort wieder.
        Fix: der doppelte Zeichnen-und-Warten-Schritt entfaellt komplett -
        render() zeichnet einmal, direkt danach beginnt dieselbe
        nested_buffer-Schleife, die auch jede weitere Taste verarbeitet.
        Der allererste Tastendruck nach dem Betreten zaehlt dadurch
        ebenfalls schon fuer den Bonus-Code (oder verlaesst den Raum,
        wenn er nicht passt - unveraendertes Verhalten fuer alle anderen
        Tasten).

        BUGFIX (Nutzer-Rueckmeldung: "auf CRT kann man nicht alles
        lesen"): die festen Zeilen (Credits/Danksagung) liefen bisher
        UNGEWRAPPT durch line() - auf CRT (320x240, deutlich weniger
        Zeichen pro Zeile als HDMI) wurden laengere Saetze (z.B. die
        Mitwirkenden-Zeile) am Bildschirmrand einfach abgeschnitten statt
        umgebrochen. Jetzt laufen ALLE Zeilen durch _wrap_text() wie
        schon die Bonus-Nachricht. Die dadurch zusaetzlich noetigen
        Zeilen wuerden mit der bisherigen, grosszuegigen Zeilenhoehe auf
        CRT wiederum unten aus dem Bild bzw. in die Fusszeile
        hineinlaufen - deshalb passt sich die Zeilenhoehe jetzt dynamisch
        an den TATSAECHLICH benoetigten Platz an (nie groesser als
        vorher, wird aber automatisch kompakter, sobald mehr Zeilen durch
        Umbruch dazukommen, bis wirklich alles in den sichtbaren Bereich
        passt) - unabhaengig von Sprache/Textlaenge/Aufloesung."""
        fb = self.fb
        W, H = fb.width, fb.height
        s = max(1, H // 360)
        ox = W * OVERSCAN_X // 100
        oy = H * OVERSCAN_Y // 100
        maxc = max(8, (W - 2 * ox) // (8 * s))

        def render():
            fb.clear(C_BG)
            title = t("dev_room_title")
            title_scale = self._fit_scale(title, W - 2 * ox, s + 1)
            fb.text(ox, oy, title, title_scale, C_TITLE, C_BG)

            level = compute_frontend_level()
            secrets = _load_secrets_unlocked()
            bonus_shown = DEV_ROOM_BONUS_ID in secrets

            # Inhalt als flache Liste von (Zeilentext, Farbe, Abstand-
            # danach-in-Zeilenhoehen) aufbauen - jeder Absatz laeuft durch
            # _wrap_text(), damit lange Saetze auf CRT umbrechen statt
            # abgeschnitten zu werden. gap_after in "Zeilenhoehen" (0.5/
            # 1.0) statt fester Pixelwerte, damit sich die spaeter
            # ermittelte, ggf. gestauchte Zeilenhoehe gleichmaessig auf
            # Text UND Absatzabstaende auswirkt.
            blocks = []

            def add(text, color, gap_after=0.0):
                wrapped = self._wrap_text(text, maxc)
                for wl in wrapped:
                    blocks.append([wl, color, 0.0])
                if blocks:
                    blocks[-1][2] = gap_after

            add(t("dev_room_level", level, FRONTEND_LEVEL_MAX), C_ACCENT)
            add(t("dev_room_secrets", len(secrets), len(SECRET_CODES) + 1),
                C_ACCENT, gap_after=0.5)
            add(t("dev_room_credits_1"), C_DIM)
            add(t("dev_room_credits_2"), C_DIM, gap_after=1.0)
            add(t("dev_room_thanks"), C_TEXT,
                gap_after=(0.5 if bonus_shown else 0.0))
            if bonus_shown:
                add(t("dev_room_bonus_message"), C_ACCENT)

            hint = t("attract_hint")
            hint_scale = s - 1 if s > 1 else 1

            # Verfuegbarer Platz zwischen Titel und Fusszeile - die
            # Zeilenhoehe wird unten so gewaehlt, dass ALLE Zeilen
            # (inklusive Umbrueche) garantiert hineinpassen.
            y_top = oy + 40 * s
            y_bottom = H - oy - 8 * hint_scale - 10 * s
            avail = max(8 * s, y_bottom - y_top)

            natural_line_h = 26 * s   # bisherige, grosszuegige Standardhoehe
            needed_units = len(blocks) + sum(b[2] for b in blocks)
            fitted_line_h = avail / needed_units if needed_units > 0 else natural_line_h
            # Nie kleiner als die reine Glyphenhoehe (sonst ueberlappen
            # sich Zeilen), nie groesser als der bisherige Standard (auf
            # HDMI/wenig Inhalt bleibt das Layout dadurch unveraendert).
            line_h = max(8 * s, min(natural_line_h, fitted_line_h))

            y = float(y_top)
            for text, color, gap_after in blocks:
                fb.text(ox, int(y), text, s, color, C_BG)
                y += line_h * (1.0 + gap_after)

            hint_w = len(hint) * 8 * hint_scale
            fb.text((W - hint_w) // 2, H - oy - 8 * hint_scale,
                    hint, hint_scale, C_DIM, C_BG)
            fb.flip()

        render()
        nested_buffer = []
        while True:
            act = self.inp.read_action()
            if act is None:
                continue
            nested_buffer.append(act)
            if len(nested_buffer) > len(DEV_ROOM_BONUS_CODE):
                nested_buffer.pop(0)
            if nested_buffer == DEV_ROOM_BONUS_CODE:
                is_new = _unlock_secret(DEV_ROOM_BONUS_ID)
                if is_new:
                    # NEU (Nutzerwunsch: eigener Sound je Geheimnis) -
                    # spielte bisher den generischen "achievement"-Ton;
                    # DEV_ROOM_BONUS_ID ("dev_room_bonus") hat jetzt
                    # einen eigenen, dedizierten Sound (siehe
                    # SFX_DIR/dev_room_bonus.mp3 bzw. der synthetische
                    # Ersatzton in SFX_CHIME_DEFS).
                    self._play_ducked_sfx(DEV_ROOM_BONUS_ID)
                nested_buffer = []
                render()
                continue
            if nested_buffer == DEV_ROOM_BONUS_CODE[:len(nested_buffer)]:
                continue   # koennte noch werden - nicht verlassen
            break

    def draw_crt_test_pattern_screen(self):
        """Testbild zur CRT-Kalibrierung (Nutzerwunsch) - Geometrie-
        Rahmen, Raster (Linearitaet), Farbbalken (Farbabgleich),
        Zentrierkreuz. Wie beim alten Servicemenue echter Roehren-
        Monitore. Rein informativ, beliebige Taste kehrt zurueck.
        Bewusst OHNE Text/Overscan-Ausgleich - das Testbild soll ja
        gerade zeigen, WIE der Bildschirm den vollen Bereich darstellt,
        ein Text-Rand wuerde das verfaelschen."""
        fb = self.fb
        W, H = fb.width, fb.height
        line_c = (0, 200, 60)
        # Aeusserer Rahmen - exakt am Bildrand, zeigt Ueberscan/
        # Geometrie-Abschneidung.
        fb.rect(0, 0, W, 2, line_c)
        fb.rect(0, H - 2, W, 2, line_c)
        fb.rect(0, 0, 2, H, line_c)
        fb.rect(W - 2, 0, 2, H, line_c)
        # Raster (Linearitaet) - gleichmaessig verteilte Linien.
        cols, rows = 8, 6
        for i in range(1, cols):
            x = i * W // cols
            fb.rect(x, 0, 1, H, line_c)
        for i in range(1, rows):
            y = i * H // rows
            fb.rect(0, y, W, 1, line_c)
        # Zentrierkreuz.
        cx, cy = W // 2, H // 2
        fb.rect(cx - 20, cy, 40, 2, (255, 255, 255))
        fb.rect(cx, cy - 20, 2, 40, (255, 255, 255))
        # Farbbalken (Farbabgleich) - unterer Bildstreifen.
        bars = [(255, 255, 255), (255, 0, 0), (0, 255, 0), (0, 0, 255),
               (0, 255, 255), (255, 0, 255), (255, 255, 0), (0, 0, 0)]
        bar_h = max(20, H // 8)
        bar_y = H - bar_h
        bar_w = W // len(bars)
        for i, color in enumerate(bars):
            fb.rect(i * bar_w, bar_y, bar_w, bar_h, color)
        fb.flip()
        while True:
            act = self.inp.read_action()
            if act is not None:
                break

    def draw_help_screen(self):
        """Hilfe-Uebersicht (Nutzerwunsch: "so viel angesammelt, dass
        selbst ich beim Aufzaehlen kurz ueberlegen musste" - eine
        zentrale Stelle, die zeigt, was das Frontend alles kann).
        Statischer Inhalt (im Gegensatz zum Spieltagebuch, das echte
        Daten anzeigt), gleiche Scroll-Logik wie draw_milestones_
        screen()/draw_diary_screen(). Erwaehnt bewusst NUR, DASS es
        Geheimnisse gibt (der System-Menue-Eintrag "Geheimnisse" ist
        ohnehin fuer jeden sichtbar) - nicht WELCHE das sind, siehe
        SECRET_CODES-Kommentar fuer die volle Begruendung.

        UEBERARBEITET (Nutzerwunsch: bessere, gerade auf CRT gut
        erkennbare Darstellung, welche Taste was bewirkt): bisher ein
        einziger Fliesstext-Satz pro Zeile ("F7: Durchgespielt-Status
        umschalten") - auf einem 320x240-CRT bei Schriftgroesse 1
        muehsam am Stueck zu lesen, und die eigentliche Taste ging im
        Satz unter. Jetzt Taste/Menuepunkt GROSS UND HELL (C_TITLE,
        gleiche Farbe wie Ueberschriften/Logo - bewusst der hoechste
        Kontrast im ganzen Farbschema) farblich abgesetzt von der
        Wirkung in normaler Textfarbe - dadurch laesst sich die Liste
        an den hellen Tasten-Namen entlang "scannen", ohne jede Zeile
        ganz lesen zu muessen.

        Zwei Layout-Varianten je Eintrag, je nachdem ob genug Platz
        ist: KURZE Tasten (z.B. "F6", "OK / A") bleiben zusammen mit
        der Wirkung auf EINER Zeile (spart Scroll-Laenge gegenueber
        durchgehend zweizeilig) - nur die paar wirklich LANGEN
        Bezeichnungen (z.B. die Esc/F10-Haltezeit, die Pad-Kombo)
        bekommen weiterhin eine eigene Zeile fuer sich, mit der
        Wirkung darunter eingerueckt, da sie sonst kaum noch Platz
        fuer die Wirkung daneben liessen. Lange Wirkungstexte duerfen
        in beiden Faellen ueber mehrere eingerueckte Zeilen umbrechen,
        ohne dass die Taste selbst irgendwo mitten im Text verschwindet.

        Ausserdem ergaenzt um bisher gar nicht aufgefuehrte, aber
        real vorhandene Tasten (beim Durchgehen der KEYMAP aufgefallen:
        F11/F12/F10/Y/Start+Select existierten, waren in der Hilfe
        aber nirgends erwaehnt).

        AKTUALISIERT (Nutzer-Rueckmeldung: "es fehlen einige Tasten"):
        erneut gegen die tatsaechliche KEYMAP (fe/input.py) und die
        hidraw-Sondertasten (fe/reset_trigger.py) geprueft, seither
        dazugekommen und ergaenzt: "/"/F2 (Volltextsuche in der
        Spieleliste, KEY_SLASH/KEY_F2 -> "search"), Select allein am
        Pad (BTN_SELECT -> "select", macht dasselbe wie Zurueck/B) und
        F5 als Reset-Taste WAEHREND ein Core laeuft (RESET_HOLD in
        fe/input.py, ueber den hidraw-Weg, unabhaengig vom normalen
        KEYMAP). Dabei aufgefallen und korrigiert: "Y: naechster
        Musiktitel" stand bisher unter "Waehrend des Spielens" - lief
        aber schon immer nur ueber die normale KEYMAP/evdev-Ebene, die
        MiSTer waehrend eines laufenden Cores exklusiv sperrt (siehe
        Kommentar bei InputManager.wait_game_exit()), funktioniert
        also tatsaechlich nur beim Bedienen des Menues selbst - jetzt
        entsprechend unter "Ueberall" gefuehrt, mit F5 als zweiter,
        gleichwertiger Taste dafuer (KEY_F5 -> "music_next" im
        Menuekontext - nicht zu verwechseln mit F5 als Reset-Taste
        WAEHREND des Spielens direkt oben, zwei unterschiedliche
        Kontexte, dieselbe physische Taste)."""
        fb = self.fb
        W, H = fb.width, fb.height
        s = max(1, H // 360)
        ox = W * OVERSCAN_X // 100
        oy = H * OVERSCAN_Y // 100
        title = t("help_title")
        title_scale = self._fit_scale(title, W - 2 * ox, s + 1)
        stack_indent = 14 * s
        maxc_key = max(8, (W - 2 * ox) // (8 * s))
        maxc_desc_stacked = max(8, (W - 2 * ox - stack_indent) // (8 * s))
        gap_chars = 2   # Abstand (in Zeichen) zwischen Taste und Wirkung bei einzeiligem Layout
        min_inline_chars = 10   # unter diesem Rest-Platz lohnt sich Inline nicht mehr - stapeln

        section_keys = [
            ("header", "help_section_nav"), ("item", "help_nav_move"),
            ("item", "help_nav_ok"), ("item", "help_nav_back"),
            ("item", "help_nav_letter"), ("item", "help_nav_search"),
            ("item", "help_nav_select"),
            ("header", "help_section_list"), ("item", "help_list_showcase"),
            ("item", "help_list_completed"), ("item", "help_list_favorite"),
            ("item", "help_list_random"),
            ("header", "help_section_menu"), ("item", "help_menu_continue"),
            ("item", "help_menu_collections"), ("item", "help_menu_hunter"),
            ("header", "help_section_system"), ("item", "help_system_stats"),
            ("item", "help_system_secrets"), ("item", "help_system_credits"),
            ("header", "help_section_playing"), ("item", "help_playing_exit"),
            ("item", "help_playing_exit_pad"), ("item", "help_playing_reset"),
            ("header", "help_section_general"), ("item", "help_general_music"),
            ("item", "help_general_osd"),
        ]
        # BUGFIX (Nutzer-Rueckmeldung: auf CRT wurde z.B. "OK/A:
        # auswaehlen, Kategorie/Ord~" abgeschnitten): jede Zeile
        # bereits HIER, vor dem Scroll-Aufbau, an Wortgrenzen umbrechen
        # (_wrap_text()) statt spaeter beim Zeichnen hart abzuschneiden.
        # Zeilenarten: "header" (Abschnittsueberschrift), "inline"
        # (Taste + erster Wirkungsteil auf einer Zeile, Taste bei x=ox,
        # Wirkung bei x=ox+desc_indent), "key"/"desc" (gestapeltes
        # Layout fuer lange Tasten-Bezeichnungen).
        rows = []
        for kind, key in section_keys:
            if kind == "header":
                rows.append(("header", t(key), None))
                continue
            key_text = t(key + "_key")
            desc_text = t(key + "_desc")
            desc_indent_chars = len(key_text) + gap_chars
            desc_width = maxc_key - desc_indent_chars
            longest_word = max((len(w) for w in desc_text.split(" ")), default=0)
            # Inline NUR, wenn daneben genug Platz ist, UND das laengste
            # einzelne Wort der Wirkung dort auch OHNE harten Wortumbruch
            # hineinpasst - sonst reisst _wrap_text() lange Woerter (z.B.
            # "Trophaeenraum,") haesslich mitten durch. In dem Fall lieber
            # auf das gestapelte Layout ausweichen, das deutlich mehr
            # Breite fuer die Wirkung hat.
            if desc_width >= min_inline_chars and desc_width >= longest_word:
                desc_lines = self._wrap_text(desc_text, desc_width) or [""]
                rows.append(("inline", key_text, desc_lines[0], desc_indent_chars))
                for extra in desc_lines[1:]:
                    rows.append(("desc", extra, desc_indent_chars))
            else:
                for line in self._wrap_text(key_text, maxc_key):
                    rows.append(("key", line, None))
                for line in self._wrap_text(desc_text, maxc_desc_stacked):
                    rows.append(("desc", line, stack_indent // (8 * s)))

        rowh = 22 * s
        list_y0 = oy + 56 * s // 2 + 44 * s
        hint_scale = s - 1 if s > 1 else 1
        list_y1 = H - oy - 8 * hint_scale - 6 * s
        visible = max(1, (list_y1 - list_y0) // rowh)
        scroll = 0
        max_scroll = max(0, len(rows) - visible)
        while True:
            fb.clear(C_BG)
            fb.text(ox, oy, title, title_scale, C_TITLE, C_BG)
            y = list_y0
            for row in rows[scroll:scroll + visible]:
                kind = row[0]
                if kind == "header":
                    fb.text(ox, y, row[1], s, accent_for(None), C_BG)
                elif kind == "key":
                    fb.text(ox, y, row[1], s, C_TITLE, C_BG)
                elif kind == "desc":
                    _, text, indent_chars = row
                    fb.text(ox + indent_chars * 8 * s, y, text, s, C_TEXT, C_BG)
                else:   # "inline": Taste hell, Wirkung daneben in Normalfarbe
                    _, key_text, desc_first, desc_indent_chars = row
                    fb.text(ox, y, key_text, s, C_TITLE, C_BG)
                    fb.text(ox + desc_indent_chars * 8 * s, y, desc_first, s, C_TEXT, C_BG)
                y += rowh
            if max_scroll > 0:
                scroll_hint = t("top10_scroll_hint", scroll + 1,
                                min(scroll + visible, len(rows)), len(rows))
                hint_w = len(scroll_hint) * 8 * hint_scale
                fb.text((W - hint_w) // 2, H - oy - 8 * hint_scale,
                        scroll_hint, hint_scale, C_DIM, C_BG)
            else:
                hint = t("attract_hint")
                hint_w = len(hint) * 8 * hint_scale
                fb.text((W - hint_w) // 2, H - oy - 8 * hint_scale,
                        hint, hint_scale, C_DIM, C_BG)
            fb.flip()
            act = self.inp.read_action()
            if act in ("up", "down") and max_scroll > 0:
                scroll = max(0, min(max_scroll, scroll + (1 if act == "down" else -1)))
                continue
            if act is not None:
                break

    def draw_diary_screen(self):
        """Spieltagebuch (Nutzerwunsch: "digitales Retro-Wohnzimmer",
        kleine rollierende Version - siehe Modul-Kommentar bei
        DIARY_FILE fuer die Begruendung). Gleiche Scroll-Logik wie
        draw_milestones_screen() - baut eine einzige gemischte Liste
        aus Datums-Ueberschriften und Sitzungs-Zeilen und scrollt
        darin wie in einer normalen Liste."""
        fb = self.fb
        W, H = fb.width, fb.height
        s = max(1, H // 360)
        ox = W * OVERSCAN_X // 100
        oy = H * OVERSCAN_Y // 100
        title = t("diary_title")
        title_scale = self._fit_scale(title, W - 2 * ox, s + 1)

        diary = load_diary()
        total_entries = sum(len(v) for v in diary.values())

        if total_entries == 0:
            fb.clear(C_BG)
            fb.text(ox, oy, title, title_scale, C_TITLE, C_BG)
            maxc_empty = max(8, (W - 2 * ox) // (8 * s))
            y_empty = oy + 50 * s
            for line in self._wrap_text(t("diary_empty"), maxc_empty):
                fb.text(ox, y_empty, line, s, C_DIM, C_BG)
                y_empty += 22 * s
            hint = t("attract_hint")
            hint_scale = s - 1 if s > 1 else 1
            hint_w = len(hint) * 8 * hint_scale
            fb.text((W - hint_w) // 2, H - oy - 8 * hint_scale,
                    hint, hint_scale, C_DIM, C_BG)
            fb.flip()
            while True:
                act = self.inp.read_action()
                if act is not None:
                    break
            return

        maxc = max(8, (W - 2 * ox - 10 * s) // (8 * s))
        # BUGFIX (Nutzer-Rueckmeldung): das bisherige feste "2 Zeilen
        # pro Eintrag"-Layout (Name oben, System+Dauer darunter) schnitt
        # auf CRT bei langen Titeln immer noch mit "~" ab, da fuer den
        # Namen nur EINE Zeile Platz vorgesehen war. Jetzt komplett auf
        # einzeln umgebrochene, gleich hohe Zeilen umgestellt (wie bei
        # Mitwirkende/Geheimnisse/Hilfe) - ein langer Name bekommt
        # automatisch so viele Zeilen wie er braucht, kein Abschneiden
        # mehr.
        rows = []
        for date_str in sorted(diary.keys(), reverse=True):
            rows.append(("header", _format_diary_date(date_str)))
            for entry in reversed(diary[date_str]):
                for line in self._wrap_text("  " + entry["name"], maxc):
                    rows.append(("name", line))
                sysname = system_display_name(entry.get("syskey")) \
                    if entry.get("syskey") else ""
                dur = format_playtime(entry.get("seconds", 0)) or "0min"
                info_text = "    %s - %s" % (sysname, dur) if sysname \
                    else "    " + dur
                for line in self._wrap_text(info_text, maxc):
                    rows.append(("info", line))

        rowh = 20 * s
        list_y0 = oy + 56 * s // 2 + 16 * s + 44 * s
        hint_scale = s - 1 if s > 1 else 1
        list_y1 = H - oy - 8 * hint_scale - 6 * s
        visible = max(1, (list_y1 - list_y0) // rowh)
        scroll = 0
        max_scroll = max(0, len(rows) - visible)
        info_scale = s - 1 if s > 1 else 1
        while True:
            fb.clear(C_BG)
            fb.text(ox, oy, title, title_scale, C_TITLE, C_BG)
            y = oy + 56 * s // 2 + 16 * s
            fb.text(ox, y, t("diary_summary", total_entries, DIARY_RETENTION_DAYS),
                    s, accent_for(None), C_BG)
            y = list_y0
            for kind, text in rows[scroll:scroll + visible]:
                if kind == "header":
                    fb.text(ox, y, text, s, accent_for(None), C_BG)
                elif kind == "name":
                    fb.text(ox, y, text, s, C_TEXT, C_BG)
                else:
                    fb.text(ox, y, text, info_scale, C_DIM, C_BG)
                y += rowh
            if max_scroll > 0:
                scroll_hint = t("top10_scroll_hint", scroll + 1,
                                min(scroll + visible, len(rows)), len(rows))
                hint_w = len(scroll_hint) * 8 * hint_scale
                fb.text((W - hint_w) // 2, H - oy - 8 * hint_scale,
                        scroll_hint, hint_scale, C_DIM, C_BG)
            else:
                hint = t("attract_hint")
                hint_w = len(hint) * 8 * hint_scale
                fb.text((W - hint_w) // 2, H - oy - 8 * hint_scale,
                        hint, hint_scale, C_DIM, C_BG)
            fb.flip()
            act = self.inp.read_action()
            if act in ("up", "down") and max_scroll > 0:
                scroll = max(0, min(max_scroll, scroll + (1 if act == "down" else -1)))
                continue
            if act is not None:
                break

    def draw_year_review_screen(self):
        """Jahresrueckblick (Nutzerwunsch: "digitales Retro-Wohnzimmer")
        - baut auf compute_year_review_stats() auf (v4.1-Fundament:
        Spielzeit zusaetzlich nach Kalenderjahr gebuendelt). Gleicher
        Aufbau wie der Trophaeenraum (Cover + Statistik + Zusammen-
        fassung), aber eingegrenzt auf das aktuelle Jahr statt "seit
        Aufzeichnungsbeginn". Zeigt eine freundliche Meldung, wenn fuer
        das laufende Jahr noch keine Daten vorliegen, statt leerer/
        irrefuehrender Werte."""
        fb = self.fb
        W, H = fb.width, fb.height
        s = max(1, H // 360)
        ox = W * OVERSCAN_X // 100
        oy = H * OVERSCAN_Y // 100
        fb.clear(C_BG)

        stats = compute_year_review_stats()
        title = t("year_review_title", _current_year())
        title_scale = self._fit_scale(title, W - 2 * ox, s + 1)
        fb.text(ox, oy, title, title_scale, C_TITLE, C_BG)

        if not stats:
            maxc_empty = max(8, (W - 2 * ox) // (8 * s))
            y_empty = oy + 50 * s
            for line in self._wrap_text(t("year_review_empty"), maxc_empty):
                fb.text(ox, y_empty, line, s, C_DIM, C_BG)
                y_empty += 22 * s
            hint = t("attract_hint")
            hint_scale = s - 1 if s > 1 else 1
            hint_w = len(hint) * 8 * hint_scale
            fb.text((W - hint_w) // 2, H - oy - 8 * hint_scale,
                    hint, hint_scale, C_DIM, C_BG)
            fb.flip()
            while True:
                act = self.inp.read_action()
                if act is not None:
                    break
            return

        accent = accent_for(stats["favorite_system"])
        top_y = oy + 44 * s

        # Cover links, gleiches Muster wie draw_trophy_room_screen().
        cover_w = int(W * 0.36)
        cover_h = int(H * 0.60)
        art = None
        top_label = stats["top_game"]
        if top_label:
            top_syskey = load_playtime().get(top_label, {}).get("syskey")
            if top_syskey:
                # BUGFIX (Nutzer-Rueckmeldung, siehe ausfuehrlicher
                # Kommentar in draw_art_panel(): kein SD-Rueckfall mehr
                # im HD-Modus - fehlende HD-Datei = kein Cover statt
                # matschig hochskaliertem SD-Bild; die "kein Artwork"-
                # Anzeige direkt unten greift dann wie gewohnt).
                if H >= 720:
                    hd = _art_path_in(ART_HD, top_syskey, top_label)
                    art = ART.get_scaled(hd, cover_w, cover_h)
                else:
                    art = ART.get_scaled(art_path(top_syskey, top_label),
                                         cover_w, cover_h)
        pad = 5 * s
        if art:
            aw, ah, pix = art
            ax = ox + (cover_w - aw) // 2
            ay = top_y
            fb.rect_rounded(ax - pad, ay - pad, aw + 2 * pad, ah + 2 * pad,
                            accent, 4 * s)
            self.blit(ax, ay, aw, ah, pix)
        else:
            fb.rect_rounded(ox, top_y, cover_w, cover_h, C_PANEL, 4 * s)
            no_art = t("no_artwork_1") + " " + t("no_artwork_2")
            fb.text(ox + 10 * s, top_y + 10 * s, no_art, s, C_DIM, C_PANEL)

        text_x = ox + cover_w + 24 * s
        y = top_y
        line_h = 28 * s
        maxc = max(8, (W - text_x - ox) // (8 * s))

        def stat_line(txt, color=C_TEXT):
            nonlocal y
            for line in self._wrap_text(txt, maxc):
                fb.text(text_x, y, line, s, color, C_BG)
                y += line_h

        if stats["favorite_system"]:
            stat_line(t("year_review_favorite_system",
                       system_display_name(stats["favorite_system"])), accent)
        if top_label:
            stat_line(t("year_review_top_game", top_label))
        played_str = format_playtime(stats["total_seconds"]) or "0min"
        stat_line(t("year_review_total_playtime", played_str))
        stat_line(t("year_review_launches", stats["total_launches"]))
        stat_line(t("year_review_games", stats["distinct_games"]))
        stat_line(t("year_review_systems", stats["distinct_systems"]))
        stat_line(t("year_review_discovered", stats["discovered_this_year"]))

        summary = t("year_review_summary", stats["year"],
                    stats["distinct_games"], stats["discovered_this_year"])
        maxc_sum = max(8, (W - 2 * ox) // (8 * s))
        summary_lines = self._wrap_text(summary, maxc_sum)
        line_h_sum = 18 * s
        sum_y = H - oy - 34 * (s - 1 if s > 1 else 1) - 16 * s \
            - (len(summary_lines) - 1) * line_h_sum
        for _sline in summary_lines:
            fb.text(ox, sum_y, _sline, s, C_DIM, C_BG)
            sum_y += line_h_sum

        hint = t("attract_hint")
        hint_scale = s - 1 if s > 1 else 1
        hint_w = len(hint) * 8 * hint_scale
        fb.text((W - hint_w) // 2, H - oy - 8 * hint_scale,
                hint, hint_scale, C_DIM, C_BG)
        fb.flip()
        while True:
            act = self.inp.read_action()
            if act is not None:
                break

    def draw_trophy_room_screen(self):
        """Persoenlicher Profil-Bildschirm ("Trophaeenraum") - grosses
        Cover des meistgespielten Spiels, Lieblingssystem (meiste
        Gesamtspielzeit), Erfolgs-Zaehler, kurze Zusammenfassung. Baut
        komplett auf Daten auf, die wir ohnehin schon sammeln (siehe
        compute_profile_stats()). Rein informativ, beliebige Taste
        kehrt zurueck.

        BUGFIX (Nutzer-Rueckmeldung anhand eines CRT-Fotos: die
        Zusammenfassung ganz unten lief quer durch das Boxart-Bild):
        auf CRT reicht die Bildschirmhoehe schlicht nicht fuer Cover +
        alle Statistik-Zeilen + Zusammenfassung gleichzeitig - das
        vorherige "nach oben wachsen lassen" der Zusammenfassung
        verschob das Ueberlappungsproblem nur, statt es zu loesen.
        Jetzt: Cover bleibt an fester Position, die Statistik-Zeilen UND
        die Zusammenfassung werden zu EINER gemeinsamen, scrollbaren
        Liste zusammengefasst (wie bei draw_milestones_screen()) - passt
        auf CRT nicht alles gleichzeitig hin, kann man es durchscrollen,
        statt dass sich Text und Bild gegenseitig ueberlagern."""
        fb = self.fb
        W, H = fb.width, fb.height
        s = max(1, H // 360)
        ox = W * OVERSCAN_X // 100
        oy = H * OVERSCAN_Y // 100

        stats = compute_profile_stats()
        title = t("trophy_room_title")
        title_scale = self._fit_scale(title, W - 2 * ox, s + 1)

        accent = accent_for(stats["favorite_system"])
        top_y = oy + 44 * s

        cover_w = int(W * 0.36)
        cover_h = int(H * 0.60)
        art = None
        top_label = None
        if stats["top_game"]:
            top_label = stats["top_game"][0]
            top_syskey = load_playtime().get(top_label, {}).get("syskey")
            if top_syskey:
                # BUGFIX (Nutzer-Rueckmeldung, siehe ausfuehrlicher
                # Kommentar in draw_art_panel(): kein SD-Rueckfall mehr
                # im HD-Modus - fehlende HD-Datei = kein Cover statt
                # matschig hochskaliertem SD-Bild; die "kein Artwork"-
                # Anzeige weiter unten greift dann wie gewohnt).
                if H >= 720:
                    hd = _art_path_in(ART_HD, top_syskey, top_label)
                    art = ART.get_scaled(hd, cover_w, cover_h)
                else:
                    art = ART.get_scaled(art_path(top_syskey, top_label),
                                         cover_w, cover_h)
        pad = 5 * s

        text_x = ox + cover_w + 24 * s
        maxc = max(8, (W - text_x - ox) // (8 * s))

        rows = []
        if stats["favorite_system"]:
            for line in self._wrap_text(t("trophy_favorite_system",
                    system_display_name(stats["favorite_system"])), maxc):
                rows.append((line, accent))
        if top_label:
            for line in self._wrap_text(t("trophy_top_game", top_label), maxc):
                rows.append((line, C_TEXT))
        played_str = format_playtime(stats["total_seconds"]) or "0min"
        for line in self._wrap_text(t("trophy_total_playtime", played_str), maxc):
            rows.append((line, C_TEXT))
        for line in self._wrap_text(t("trophy_launches", stats["total_launches"]), maxc):
            rows.append((line, C_TEXT))
        for line in self._wrap_text(t("trophy_systems", stats["distinct_systems"]), maxc):
            rows.append((line, C_TEXT))
        for line in self._wrap_text(t("trophy_achievements", stats["unlocked"],
                   stats["total_achievements"]), maxc):
            rows.append((line, C_TEXT))
        rows.append(("", C_DIM))
        summary = t("trophy_summary", stats["distinct_systems"],
                    stats["unlocked"], stats["total_achievements"])
        for line in self._wrap_text(summary, maxc):
            rows.append((line, C_DIM))

        line_h = 22 * s
        hint_scale = s - 1 if s > 1 else 1
        list_y1 = H - oy - 8 * hint_scale - 6 * s
        visible = max(1, (list_y1 - top_y) // line_h)
        scroll = 0
        max_scroll = max(0, len(rows) - visible)
        while True:
            fb.clear(C_BG)
            fb.text(ox, oy, title, title_scale, C_TITLE, C_BG)

            if art:
                aw, ah, pix = art
                ax = ox + (cover_w - aw) // 2
                ay = top_y
                fb.rect_rounded(ax - pad, ay - pad, aw + 2 * pad, ah + 2 * pad,
                                accent, 4 * s)
                self.blit(ax, ay, aw, ah, pix)
            else:
                fb.rect_rounded(ox, top_y, cover_w, cover_h, C_PANEL, 4 * s)
                no_art = t("no_artwork_1") + " " + t("no_artwork_2")
                fb.text(ox + 10 * s, top_y + 10 * s, no_art, s, C_DIM, C_PANEL)

            y = top_y
            for text, color in rows[scroll:scroll + visible]:
                fb.text(text_x, y, text, s, color, C_BG)
                y += line_h

            if max_scroll > 0:
                scroll_hint = t("top10_scroll_hint", scroll + 1,
                                min(scroll + visible, len(rows)), len(rows))
                hint_w = len(scroll_hint) * 8 * hint_scale
                fb.text((W - hint_w) // 2, H - oy - 8 * hint_scale,
                        scroll_hint, hint_scale, C_DIM, C_BG)
            else:
                hint = t("attract_hint")
                hint_w = len(hint) * 8 * hint_scale
                fb.text((W - hint_w) // 2, H - oy - 8 * hint_scale,
                        hint, hint_scale, C_DIM, C_BG)
            fb.flip()
            act = self.inp.read_action()
            if act in ("up", "down") and max_scroll > 0:
                scroll = max(0, min(max_scroll, scroll + (1 if act == "down" else -1)))
                continue
            if act is not None:
                break

    def draw_milestones_screen(self):
        """Vollbild-Uebersicht aller eigenen, lokalen Erfolge - erreichte
        hervorgehoben, offene gedimmt mit Fortschrittsangabe. Hoch/Runter
        scrollt, falls nicht alles auf den Bildschirm passt (v.a. auf
        CRT relevant, siehe draw_top10_screen() fuer denselben Fix) -
        OK/ESC kehrt zurueck ins System-Menue.

        Baut sich eine einzige, gemischte Liste aus Meilenstein-Zeilen,
        Abschnitts-Ueberschriften und versteckten Erfolgen zusammen und
        scrollt darin wie in einer normalen Liste - einfacher als zwei
        getrennte Scroll-Bereiche zu verwalten."""
        fb = self.fb
        W, H = fb.width, fb.height
        s = max(1, H // 360)
        ox = W * OVERSCAN_X // 100
        oy = H * OVERSCAN_Y // 100
        title = t("milestones_title")
        title_scale = self._fit_scale(title, W - 2 * ox, s + 1)
        milestones = get_milestones()
        unlocked = sum(1 for m in milestones if m[1])
        hidden = get_hidden_achievements()
        hidden_unlocked = sum(1 for h in hidden if h[2])
        # BUGFIX: reservierter Platz fuer die Fortschrittsanzeige rechts
        # von 60*s auf 170*s erhoeht - das neue durchgaengige "Stunden
        # dann Minuten"-Format (siehe _format_seconds_short()) ist
        # laenger als das alte gemischte Format, hier passend erweitert
        # damit Beschriftung und Fortschrittswert nicht ueberlappen.
        maxc = max(8, (W - 2 * ox - 170 * s) // (8 * s))

        rows = []
        for label_key, achieved, current, threshold, kind in milestones:
            rows.append(("milestone", label_key, achieved, current, threshold, kind))
        rows.append(("header", t("hidden_section_title", hidden_unlocked, len(hidden))))
        # BUGFIX (Nutzer-Rueckmeldung, Foto von echter CRT-Hardware:
        # "??? (einfach" und dann nichts mehr): die vorige Version
        # nutzte fuer "hidden"-Zeilen dieselbe (schmale) maxc wie fuer
        # "milestone"-Zeilen, die extra Platz fuer eine Fortschritts-
        # anzeige rechts reserviert (170*s) - "hidden"-Zeilen haben
        # aber GAR KEINE Fortschrittsanzeige und wurden dadurch
        # unnoetig eingeengt (nur ~13 Zeichen auf CRT statt der vollen
        # verfuegbaren Breite), wodurch selbst "weiterspielen)" schon
        # als "zu langes Einzelwort" hart getrennt wurde. Jetzt eigene,
        # breitere Berechnung nur fuer "hidden"-Zeilen.
        maxc_hidden = max(8, (W - 2 * ox) // (8 * s))
        for hid, label_key, hunlocked in hidden:
            mark = "[x] " if hunlocked else "[ ] "
            label = mark + (t(label_key) if hunlocked else t("hidden_mystery"))
            for line in self._wrap_text(label, maxc_hidden):
                rows.append(("hidden_line", line, hunlocked))

        rowh = 24 * s
        list_y0 = oy + 56 * s // 2 + 16 * s + 44 * s
        hint_scale = s - 1 if s > 1 else 1
        list_y1 = H - oy - 8 * hint_scale - 6 * s
        visible = max(1, (list_y1 - list_y0) // rowh)
        scroll = 0
        max_scroll = max(0, len(rows) - visible)
        while True:
            fb.clear(C_BG)
            fb.text(ox, oy, title, title_scale, C_TITLE, C_BG)
            y = oy + 56 * s // 2 + 16 * s
            fb.text(ox, y, t("milestones_summary", unlocked, len(milestones)),
                    s, accent_for(None), C_BG)
            y = list_y0
            for row in rows[scroll:scroll + visible]:
                if row[0] == "header":
                    fb.text(ox, y, row[1], s, accent_for(None), C_BG)
                elif row[0] == "milestone":
                    _, label_key, achieved, current, threshold, kind = row
                    mark = "[x] " if achieved else "[ ] "
                    label = mark + t(label_key)
                    color = C_TEXT if achieved else C_DIM
                    fb.text(ox, y, self._wrap_text(label, maxc)[0], s, color, C_BG)
                    if not achieved:
                        if kind == "playtime_seconds":
                            prog = "%s/%s" % (_format_seconds_short(current),
                                              _format_seconds_short(threshold))
                        else:
                            prog = "%d/%d" % (current, threshold)
                        prog_w = len(prog) * 8 * s
                        fb.text(W - ox - prog_w, y, prog, s, C_DIM, C_BG)
                else:   # "hidden_line" - bereits fertig umgebrochene Zeile
                    _, text, hunlocked = row
                    color = C_TEXT if hunlocked else C_DIM
                    fb.text(ox, y, text, s, color, C_BG)
                y += rowh
            if max_scroll > 0:
                scroll_hint = t("top10_scroll_hint", scroll + 1,
                                min(scroll + visible, len(rows)), len(rows))
                hint_w = len(scroll_hint) * 8 * hint_scale
                fb.text((W - hint_w) // 2, H - oy - 8 * hint_scale,
                        scroll_hint, hint_scale, C_DIM, C_BG)
            else:
                hint = t("attract_hint")
                hint_w = len(hint) * 8 * hint_scale
                fb.text((W - hint_w) // 2, H - oy - 8 * hint_scale,
                        hint, hint_scale, C_DIM, C_BG)
            fb.flip()
            act = self.inp.read_action()
            if act in ("up", "down") and max_scroll > 0:
                scroll = max(0, min(max_scroll, scroll + (1 if act == "down" else -1)))
                continue
            if act is not None:
                break

    def _fit_scale(self, text, max_width, max_scale):
        """Groesste Skalierung (mindestens 1), mit der `text` noch in
        max_width Pixel passt - fuer Titelzeilen, die auf CRT (320px
        breit) bei fester grosser Skalierung sonst abgeschnitten
        werden (z.B. "TOP 10 - MEISTGESTARTET" bei 23 Zeichen)."""
        for scale in range(max_scale, 0, -1):
            if len(text) * 8 * scale <= max_width:
                return scale
        return 1

    def _wrap_text(self, text, maxc):
        """Bricht einen Text an WORTGRENZEN um, sodass jede Zeile
        hoechstens maxc Zeichen lang ist - liefert eine Liste von
        Zeilen zurueck. Nutzerwunsch/-Rueckmeldung: mehrere Info-
        Bildschirme (Mitwirkende, Geheimnisse, Hilfe, Trophaeenraum,
        Jahresrueckblick, Spieltagebuch) schnitten auf CRT lange
        Zeilen bisher einfach mit "~" ab - der Rest war unlesbar.
        GANZE WOERTER bleiben beim Umbruch zusammen; nur wenn ein
        EINZELNES Wort selbst schon laenger als maxc ist (extrem
        selten), wird ausschliesslich dieses eine Wort hart getrennt -
        unvermeidbar, aber der Normalfall bleibt sauber lesbar."""
        maxc = max(4, maxc)
        words = text.split(" ")
        lines = []
        current = ""
        for word in words:
            candidate = (current + " " + word) if current else word
            if len(candidate) <= maxc:
                current = candidate
            else:
                if current:
                    lines.append(current)
                if len(word) > maxc:
                    while len(word) > maxc:
                        lines.append(word[:maxc])
                        word = word[maxc:]
                    current = word
                else:
                    current = word
        if current:
            lines.append(current)
        return lines or [""]

    def draw_top10_screen(self, by):
        """Zeigt eine Vollbild-Liste der 10 meistgespielten (by=
        "seconds") oder meistgestarteten (by="launches") Spiele. Rein
        informativ (kein direktes Starten von hier aus). Hoch/Runter
        scrollt, falls nicht alle Eintraege auf den Bildschirm passen
        (v.a. auf CRT relevant) - OK/ESC kehrt zurueck ins System-Menue.

        BUGFIX (Nutzer-Rueckmeldung): auf CRT passten rechnerisch nur
        ca. 6 von 10 Zeilen auf den Bildschirm, der Rest wurde einfach
        nicht gezeichnet (fb.text() bricht bei ueberschrittener Hoehe
        still ab) - ohne jede Moeglichkeit, den Rest zu sehen. Ausserdem
        war der Titel ("TOP 10 - MEISTGESTARTET", 23 Zeichen) bei der
        festen Skalierung auf CRT breiter als der Bildschirm und wurde
        abgeschnitten - siehe _fit_scale()."""
        fb = self.fb
        W, H = fb.width, fb.height
        s = max(1, H // 360)
        ox = W * OVERSCAN_X // 100
        oy = H * OVERSCAN_Y // 100
        title = t("top10_time_title") if by == "seconds" \
            else t("top10_launches_title")
        title_scale = self._fit_scale(title, W - 2 * ox, s + 1)
        rows = top_played_games(by=by, n=10)
        rowh = 26 * s
        list_y0 = oy + 56 * s // 2 + 20 * s
        hint_scale = s - 1 if s > 1 else 1
        list_y1 = H - oy - 8 * hint_scale - 6 * s
        visible = max(1, (list_y1 - list_y0) // rowh)
        maxc = max(8, (W - 2 * ox - 90 * s) // (8 * s))
        scroll = 0
        max_scroll = max(0, len(rows) - visible)
        while True:
            fb.clear(C_BG)
            fb.text(ox, oy, title, title_scale, C_TITLE, C_BG)
            y = list_y0
            if not rows:
                fb.text(ox, y, t("top10_empty"), s, C_DIM, C_BG)
            for i in range(scroll, min(scroll + visible, len(rows))):
                label, seconds, launches = rows[i]
                rank = "%2d." % (i + 1)
                fb.text(ox, y, rank, s, C_DIM, C_BG)
                name = self._wrap_text(label, maxc)[0]
                fb.text(ox + 44 * s, y, name, s, C_TEXT, C_BG)
                if by == "seconds":
                    stat = format_playtime(seconds) or "-"
                else:
                    stat = t("top10_launches_count", launches)
                stat_w = len(stat) * 8 * s
                fb.text(W - ox - stat_w, y, stat, s, accent_for(None), C_BG)
                y += rowh
            if max_scroll > 0:
                # Scroll-Hinweis statt des normalen Bedienhinweises -
                # zeigt zugleich, dass/wie weit noch mehr Eintraege
                # folgen.
                scroll_hint = t("top10_scroll_hint", scroll + 1,
                                min(scroll + visible, len(rows)), len(rows))
                hint_w = len(scroll_hint) * 8 * hint_scale
                fb.text((W - hint_w) // 2, H - oy - 8 * hint_scale,
                        scroll_hint, hint_scale, C_DIM, C_BG)
            else:
                hint = t("attract_hint")
                hint_w = len(hint) * 8 * hint_scale
                fb.text((W - hint_w) // 2, H - oy - 8 * hint_scale,
                        hint, hint_scale, C_DIM, C_BG)
            fb.flip()
            act = self.inp.read_action()
            if act in ("up", "down") and max_scroll > 0:
                scroll = max(0, min(max_scroll, scroll + (1 if act == "down" else -1)))
                continue
            if act is not None:
                break

    def open_osd(self):
        """Echtes MiSTer-OSD oeffnen (fuer Joystick-Definition, Settings).

        BUGFIX (Nutzer-Rueckmeldung: "wenn ich mit F12 aus dem Frontend
        rausgehe, komme ich nicht wieder rein" - start_frontend.sh
        meldete dabei "Frontend laeuft bereits (PID ...), nichts zu
        tun"): der Prozess laeuft in diesem Fall tatsaechlich die ganze
        Zeit weiter - er haengt nur GENAU HIER fest, in der
        Warteschleife unten, die bisher AUSSCHLIESSLICH auf die Aktion
        "back_fe" reagierte (Standard: Taste F10 oder Pad-Button X).
        Ist der Pad-Button, den der Nutzer fuer "X"/Zurueck haelt, ueber
        MiSTers eigene Joystick-Belegung anders zugeordnet als hier
        angenommen (siehe Diskussion zur fehlenden Ruecksicht auf
        MiSTers Belegung), kommt dieses "back_fe" schlicht NIE an - der
        einzige Ausweg war bisher ein SSH-Zugriff mit
        "kill $(cat /tmp/frontend.lock)". configure_buttons() erlaubt
        jetzt zusaetzlich, "back_fe" explizit auf eine beliebige eigene
        Taste zu legen (siehe dortige "remap_action_back_fe"-Aktion).
        Als weiteres, unabhaengiges Sicherheitsnetz akzeptiert die
        Schleife jetzt zusaetzlich "exit" (ESC-Taste), "back" (Standard:
        Pad-Button B) und "osd" (Standard: F12/Guide-Button, als
        Umschalter gedacht - nochmal draufdruecken bringt einen
        zurueck) - vier voneinander unabhaengige Wege zurueck statt
        nur eines starren, dadurch bleibt man selbst bei ungewoehnlicher
        Tasten-/Pad-Belegung praktisch nie mehr dauerhaft im MiSTer-OSD
        gefangen."""
        LOG("open_osd: Start")
        self.music.pause_for_core()
        self.draw("MiSTer OSD active - Back/Menu/ESC/F10 = back to frontend")
        self.inp.grab(False)
        time.sleep(0.2)
        self.inp.inject(KEY_F12)
        # BUGFIX (Nutzer-Rueckmeldung: "die F12-Taste um ins OSD zu
        # kommen springt jetzt sofort wieder ins Frontend, ist das
        # normal?" - war es nicht, echter Bug): inject() schreibt das
        # F12-Tastenevent auf DIESELBE Geraeteverbindung (O_RDWR), von
        # der dieselbe InputManager-Instanz gleich darunter auch wieder
        # LIEST - das selbst erzeugte Event landet dadurch (Grab ist ja
        # bewusst geloest, siehe oben) sofort auch in unserer EIGENEN
        # Lesewarteschlange zurueck. "osd" (F12) zaehlt bewusst als
        # eine von mehreren Rueckkehr-Aktionen (siehe Kommentar oben,
        # frueherer Fix gegen dauerhaftes Haengenbleiben im OSD) - ohne
        # dieses flush() erfuellte das selbst injizierte Event diese
        # Bedingung sofort, noch bevor der Nutzer ueberhaupt reagieren
        # konnte: die Schleife unten brach augenblicklich wieder ab,
        # als haette der Nutzer selbst schon ein zweites Mal gedrueckt.
        # Kurze Wartezeit, damit das injizierte Event sicher in der
        # Warteschlange angekommen ist, dann verwerfen (flush()) - eine
        # ECHTE, spaeter eintreffende Rueckkehr-Eingabe des Nutzers ist
        # davon nicht betroffen (mit einem gezielten Test simuliert und
        # geprueft, siehe /tmp/diag_f12_bounce.py).
        time.sleep(0.05)
        self.inp.flush()
        LOG("open_osd: F12 injiziert, warte auf Rueckkehr-Aktion "
            "(back_fe/exit/back/osd)")
        RETURN_ACTIONS = ("back_fe", "exit", "back", "osd")
        act = None
        while True:
            act = self.inp.read_action()
            LOG("open_osd passthrough: %s" % act)
            if act in RETURN_ACTIONS:
                break
        LOG("open_osd: Rueckkehr (ausgeloest durch %r)" % act)
        self.music.resume_after_core()
        self.back_to_frontend()

    def configure_buttons(self):
        """Tastenbelegungs-Assistent: fragt nacheinander nach jeder
        Kernaktion und uebernimmt den naechsten tatsaechlichen
        Tastendruck (Tastatur ODER Pad) als Belegung. ESC bricht ab
        und behaelt die vorherige Belegung.

        Bei den vier Richtungsaktionen wird ein Analogstick-/D-Pad-
        Ausschlag als "funktioniert schon nativ" akzeptiert und
        automatisch uebersprungen - sonst wuerde der Assistent bei
        Pads, deren D-Pad als Achse ankommt, bei "Hoch" haengen
        bleiben, weil dort kein reines Tasten-Event eintrifft.

        WICHTIG (v1.60 KORRIGIERT, v1.61): die urspruengliche Annahme
        (Eingabe-Grab loesen laesst MiSTers eigene Hotkey-Erkennung
        parallel reagieren) hat das Problem NICHT behoben - der Grab
        bleibt seit v1.60 durchgehend gehalten, trotzdem fror es beim
        Konfigurieren von "OSD oeffnen" weiterhin ein. Die tatsaechliche
        Ursache liegt vermutlich TIEFER: F9 ist bei MiSTer fuer den
        Wechsel zwischen Konsole/Grafikmodus reserviert (siehe
        enter_console_mode()) - vermutlich ueber die Kernel-eigene
        VT-Umschaltung, NICHT ueber einen gewoehnlichen evdev-Listener,
        den ein Grab ueberhaupt beeinflussen koennte. Sendet das Pad
        (z.B. ueber die Home-/Guide-Taste, die bei manchen Empfaengern
        als eigene Tastatur-Taste ankommt) ein echtes F9, wird das
        vermutlich schon vom Kernel abgefangen, BEVOR unser Prozess es
        je zu sehen bekommt - das erklaert sowohl das "nichts weiter im
        Log" (wir bekommen das Ereignis nie) als auch den schwarzen
        Bildschirm mit Login-Prompt (MiSTer wechselt weg von unserem
        Framebuffer).

        Zwei Absicherungen dagegen: (1) read_raw_key() bekommt hier ein
        Zeitlimit statt endlos zu warten - bleibt eine Rueckmeldung zu
        lange aus, wird diese EINE Abfrage uebersprungen (bisherige
        Belegung bleibt bestehen) statt fuer immer haengen zu bleiben.
        (2) Ein tatsaechlich erfasstes F9 wird NIE als Belegung
        akzeptiert (fuer MiSTers eigenen Konsolen-Wechsel reserviert -
        eine Zuweisung wuerde das exakt gleiche Einfrieren spaeter bei
        JEDEM Druck dieser Taste erneut ausloesen), sondern erneut
        fuer dieselbe Aktion nachgefragt."""
        DIRECTIONAL = {"up", "down", "left", "right"}
        REMAP_TIMEOUT = 20.0   # Sekunden, bevor eine Abfrage uebersprungen wird
        actions = [
            ("up", "remap_action_up"), ("down", "remap_action_down"),
            ("left", "remap_action_left"), ("right", "remap_action_right"),
            ("ok", "remap_action_ok"), ("back", "remap_action_back"),
            ("osd", "remap_action_osd"), ("random", "remap_action_random"),
            ("favorite", "remap_action_favorite"),
            ("completed", "remap_action_completed"),
            # NEU (BUGFIX: siehe ausfuehrlicher Kommentar bei
            # open_osd() - Nutzer konnte nach F12/OSD manchmal dauerhaft
            # nicht mehr zurueck ins Frontend finden, wenn "back_fe"
            # (Standard F10/X) auf der eigenen Pad-Belegung nicht wie
            # erwartet ankam): "back_fe" ("Zurueck ins Frontend, wenn
            # das echte MiSTer-OSD offen ist") ist jetzt genauso frei
            # zuweisbar wie jede andere Aktion, statt nur ueber die
            # feste Vorgabe erreichbar zu sein.
            ("back_fe", "remap_action_back_fe"),
            # NEUES FEATURE (Nutzerwunsch: "ist es moeglich der Tastatur
            # auch einen Shortcut zuzuweisen, um die Musik zu wechseln?" -
            # der feste F5/Medientaste-Fix deckt den Normalfall ab, aber
            # hierueber kann sich jeder Nutzer zusaetzlich eine GANZ
            # BELIEBIGE eigene Taste dafuer eintragen, genau wie fuer
            # Favorit/Durchgespielt schon moeglich).
            ("music_next", "remap_action_music_next"),
        ]
        new_map = {}
        cancelled = False
        for act_name, label_key in actions:
            is_dir = act_name in DIRECTIONAL
            code = None
            while True:
                msg = "%s   %s" % (t("remap_prompt", t(label_key)),
                                    t("remap_esc_hint"))
                self.draw(msg)
                code = self.inp.read_raw_key(timeout=REMAP_TIMEOUT,
                                             allow_axis_skip=is_dir)
                if code == KEY_F9:
                    # Fuer MiSTers eigenen Konsolen-/Grafikmodus-Wechsel
                    # reserviert - eine Zuweisung wuerde spaeter bei
                    # jedem Druck dasselbe Einfrieren wieder ausloesen.
                    LOG("configure_buttons: F9 abgelehnt (fuer MiSTer reserviert), "
                        "erneute Abfrage fuer %s" % act_name)
                    self.draw("%s   %s" % (t("remap_f9_blocked"),
                                          t("remap_esc_hint")))
                    time.sleep(1.5)
                    continue
                break
            if code is None:
                # Zeitlimit erreicht ODER Geraet lieferte gar nichts
                # (z.B. weil MiSTer das Ereignis abgefangen hat, bevor
                # es uns erreichte) - diese EINE Abfrage ueberspringen,
                # bisherige Belegung bleibt fuer diese Aktion bestehen,
                # der Assistent haengt dadurch nie mehr unbegrenzt.
                LOG("configure_buttons: Zeitlimit bei %s - uebersprungen"
                    % act_name)
                continue
            if code == KEY_ESC:
                cancelled = True
                break
            if code == "AXIS":
                # D-Pad/Analogstick deckt diese Richtung schon nativ ab -
                # nichts zu ueberschreiben, einfach weiter zur naechsten Abfrage
                LOG("configure_buttons: %s per Achse erkannt, uebersprungen"
                    % act_name)
                continue
            new_map[code] = act_name
        self.inp.flush()
        self.inp.grab(True)
        if cancelled:
            LOG("configure_buttons: abgebrochen")
            self.draw(t("remap_cancelled"))
        else:
            KEYMAP.update(new_map)
            try:
                os.makedirs(os.path.dirname(KEYMAP_CUSTOM_FILE),
                            exist_ok=True)
                with open(KEYMAP_CUSTOM_FILE, "w") as f:
                    json.dump({str(k): v for k, v in new_map.items()}, f)
                LOG("configure_buttons: gespeichert: %s" % new_map)
            except OSError as e:
                LOG("configure_buttons: Speichern fehlgeschlagen: %s" % e)
            self.draw(t("remap_done"))
        time.sleep(1.2)
        self.draw()

    def enter_console_mode(self):
        """MiSTer per F9 in den Konsolenmodus schalten - sonst uebermalt
        das MiSTer-Wallpaper unseren Framebuffer permanent.
        Muss bei GELOESTEM Grab passieren, damit MiSTer die Taste sieht."""
        LOG("enter_console_mode (F9)")
        self.inp.grab(False)
        time.sleep(0.1)
        self.inp.inject(KEY_F9)
        time.sleep(0.4)

    def back_to_frontend(self):
        self.enter_console_mode()
        self.set_cursor_blink(False)
        self.fb.refresh_geometry()
        self.inp.flush()
        self.inp.grab(True)
        self.draw()

    @staticmethod
    def set_cursor_blink(on):
        try:
            open("/sys/class/graphics/fbcon/cursor_blink", "w") \
                .write("1" if on else "0")
        except OSError:
            pass

    # ------------------------------------------------------------------
    # Hauptschleife
    # ------------------------------------------------------------------

    def stream_state(self):
        """Aktuelle Auswahl als Dict fuer das Web-Overlay."""
        name, _root_node, syskey = self.cats[self.cat_i]
        items = self._display_items() if self.page == 1 else []
        nowplaying = (self.music.current_track_name()
                      if hasattr(self, "music") else None)

        if self.page == 0:
            # Kategorien-Menue: der Zuschauer sieht, durch welche
            # Systeme geblaettert wird. self.item_i gehoert hier noch
            # zur zuletzt geoeffneten Kategorie und waere irrefuehrend.
            total = len(self.cats)
            lo = max(0, self.cat_i - 2)
            hi = min(total, lo + 5)
            return {
                "category": "",
                "system": "",
                "syskey": "",           # kein Cover im Kategorien-Menue
                "name": name,
                "index": self.cat_i,
                "total": total,
                "nowplaying": nowplaying,
                "list": [self.cats[i][0] for i in range(lo, hi)],
                "list_index": self.cat_i - lo,
            }

        total = len(items)
        sel_item = items[self.item_i] if 0 <= self.item_i < total else None
        sel = sel_item[0] if sel_item else ""
        lo = max(0, self.item_i - 2)
        hi = min(total, lo + 5)
        window = [display_name(items[i][0]) for i in range(lo, hi)]

        # Zusaetzliche Angaben fuers Overlay - dieselben Quellen, die
        # auch der Info-Bereich im Frontend selbst nutzt (siehe
        # draw_art_panel()), damit Zuschauer dieselben Infos sehen wie
        # der Spieler vor Ort.
        genre = year = None
        playtime_str = None
        ra_str = None
        is_favorite = False
        if sel_item:
            item_kind = sel_item[1]
            lookup_name = sel_item[2] if item_kind == "folder" else sel
            if syskey == "ARCADE":
                meta = mra_meta(sel_item[2]) if item_kind == "core" else {}
            else:
                meta = get_meta(syskey, lookup_name) if syskey else {}
            genre = meta.get("genre")
            year = meta.get("year")
            if hasattr(self, "_playtime_cache"):
                entry = self._playtime_cache.get(sel)
                playtime_str = format_playtime(entry.get("seconds")) if entry else None
            if hasattr(self, "_ra_lookup") and self._ra_lookup:
                ra = lookup_ra_progress(self._ra_lookup, sel, syskey)
                if ra:
                    ra_str = "%d/%d" % ra
            is_favorite = item_kind == "game" and hasattr(self, "_favorites_set") \
                and sel in self._favorites_set

        return {
            "category": name,
            "system": name,                 # lesbarer Name fuers Badge
            "syskey": syskey or "",         # Key fuer die Cover-URL (/art)
            "name": display_name(sel),
            "art_name": sel,                # echter Dateiname fuers Cover
            "index": self.item_i,
            "total": total,
            "nowplaying": nowplaying,
            "list": window,
            "list_index": self.item_i - lo,
            "genre": genre,
            "year": year,
            "playtime": playtime_str,
            "ra_progress": ra_str,
            "favorite": is_favorite,
        }

    def _screen_mirror_loop(self):
        """Haengt im Hintergrund, bis das Frontend beendet wird (daemon-
        Thread, siehe Start-Stelle in __init__) - kodiert den aktuellen
        Framebuffer-Inhalt periodisch als PNG und stellt ihn ueber den
        Stream-Server bereit (siehe publish_screen() in
        stream_server.py, dort auch die eigentliche BGRA->RGBA/Stride-
        Umwandlung).

        Absichtlich EIGENER Thread statt in next_action()/draw()
        eingehaengt: PNG-Kodierung ist CPU-gebunden (dieselbe Lehre wie
        beim Boxart-Konvertieren, siehe CONVERT_WORKERS-Kommentar in
        mister_boxart.py - reine Python-Pixelarbeit ist teuer), soll
        aber die Reaktionsfaehigkeit der Eingabe-Hauptschleife nicht
        blockieren.

        BUGFIX (Nutzer-Nachfrage: "laeuft das wirklich lagfrei, ohne
        Performance-Einbussen?" - direkt nachgemessen, nicht nur
        angenommen): der urspruengliche Kommentar hier behauptete, die
        2-Sekunden-Drosselung wuerde "besonders bei HDMI" reichen -
        das war eine unbelegte Annahme, keine Messung. Tatsaechlich
        gemessen (selbst auf einer deutlich staerkeren Cloud-CPU als
        dem schwachen MiSTer-ARM-Kern): CRT (320x240) ~15-30ms pro
        Bild, voellig unbedenklich - aber HDMI (1920x1080) ~400-830ms
        PRO EINZELNEM BILD, und ein parallel simulierter Haupt-Thread
        verlor waehrend eines einzelnen HDMI-Kodiervorgangs nachweis-
        lich 57% seines Durchsatzes (GIL-Konkurrenz, da reine Python-
        Pixelarbeit den Interpreter blockiert). Auf echter, schwaecherer
        MiSTer-Hardware waere das noch deutlich schlimmer - genau die
        Art sptürbarer Verzoegerung, die dieses Feature laut Nutzer
        NICHT verursachen sollte.

        Fix: HDMI-Aufloesungen werden komplett uebersprungen (kein
        publish_screen()-Aufruf, keine Kodierung) - inhaltlich auch
        sinnvoll, da der eigentliche Zweck (Bildschirminhalt sehen,
        waehrend man auf CRT laeuft und HDMI nicht direkt einsehen
        kann) bei HDMI ohnehin nicht gebraucht wird: dort sieht man
        den Bildschirm ja bereits direkt.

        BUGFIX 2 (Nutzer-Rueckmeldung NACH dem ersten echten Test:
        "die 2-Sekunden-Aktualisierung sieht aus wie Standbilder, geht
        das fluessiger?"): das pauschale 2-Sekunden-Intervall einfach
        zu verkuerzen haette bei UNVERAENDERTEM Bildschirm (z.B. wenn
        man einfach nur im Menue steht) unnoetig oft neu kodiert -
        dieselbe Art Verschwendung, die full_redraw_gen beim HDMI-
        Fast-Path schon vermeidet. Stattdessen: das Pruefintervall
        selbst wird kuerzer (oefter nachschauen), aber NUR wenn sich
        der Bildschirm seit dem letzten Schnappschuss TATSAECHLICH
        veraendert hat (fb.flip_gen, siehe fe/framebuffer.py - zaehlt
        bei JEDER sichtbaren Aenderung hoch, auch Laufschrift/Puls,
        nicht nur bei vollen Neuaufbauten), wird ueberhaupt neu
        kodiert. Bei Stillstand bleibt die Kosten praktisch bei null,
        bei aktiver Navigation wirkt es deutlich fluessiger als vorher
        - ohne das GROSSZUEGIG-Prinzip von vorhin (kein Dauerfeuer bei
        HDMI-Aufloesung, siehe oben) aufzugeben, da dieser Dirty-Check
        UNABHAENGIG von der HDMI-Ausschluss-Pruefung wirkt.

        NACHTRAEGLICH WEITER VERKUERZT (Nutzer-Nachfrage nach dem
        ersten echten Test: "noch fluessiger geht nicht?"): risikoarm,
        da der Dirty-Check oben die Leerlauf-Kosten UNABHAENGIG vom
        Pruefintervall bei null haelt - nur die maximale Verzoegerung
        zwischen einer echten Aenderung und ihrem Erscheinen im
        Spiegel sinkt. Bewusst nicht extremer (z.B. 50ms) - das waere
        kein Schnappschuss-Mechanismus mehr, sondern naeherte sich
        einer echten Videoausgabe an, fuer die dieser Bild-per-HTTP-
        Ansatz architektonisch nicht gebaut ist. 0.2s ist ein
        vernuenftiger Punkt: spuerbar fluessiger, ohne die
        Kodierhaeufigkeit bei AKTIVER Nutzung uebermaessig zu
        steigern (die einzelnen Kodiervorgaenge selbst bleiben exakt
        gleich teuer wie vorher, nur die maximale Wartezeit sinkt).

        NACHTRAEGLICH EREIGNISGESTEUERT GEMACHT (Nutzerwunsch: "kann
        man beim Mirror noch mehr rausholen?"): das Pruefintervall
        von 0.2s bedeutete bisher, dass selbst eine einzelne,
        isolierte Aenderung (z.B. Menuewechsel nach laengerem
        Stillstand) im schlimmsten Fall bis zu 200ms brauchte, bevor
        der Spiegel sie ueberhaupt bemerkte. fb.flip_event (siehe
        fe/framebuffer.py, wird von flip()/flip_rows() gesetzt) weckt
        die Schleife jetzt SOFORT auf, statt starr zu schlafen. Die
        MINDESTABSTAND-Drosselung zwischen zwei tatsaechlichen
        Kodiervorgaengen bleibt UNVERAENDERT bei 0.2s bestehen -
        schnelles, durchgehendes Scrollen loest weiterhin nicht
        haeufiger als bisher eine echte Kodierung aus, nur eine
        EINZELNE, ISOLIERTE Aenderung erscheint jetzt praktisch
        sofort statt erst beim naechsten Prüf-Zyklus."""
        MIN_ENCODE_INTERVAL = 0.2
        # Sicherheitsnetz-Timeout: falls das Event aus irgendeinem
        # Grund nie ausgeloest wird (sollte nicht vorkommen, da JEDER
        # sichtbare Bildschirmwechsel ueber flip()/flip_rows() laeuft),
        # schaut die Schleife trotzdem spaetestens hier wieder nach -
        # kein permanentes Haengenbleiben moeglich.
        SAFETY_TIMEOUT = 1.0
        # Schwelle bewusst grosszuegig ueber typischen CRT-Aufloesungen
        # (320x240 bis hoch zu z.B. 640x480 bei einigen Cores) und klar
        # UNTER jeder HDMI-Aufloesung (kleinste ueblicherweise 1280x720)
        # angesetzt - kein Grenzfall zu erwarten.
        MAX_MIRROR_WIDTH = 640
        last_gen = -1
        last_encode = 0.0
        while True:
            try:
                fb = self.fb
                fb.flip_event.wait(timeout=SAFETY_TIMEOUT)
                fb.flip_event.clear()
                # Mindestabstand seit dem letzten ECHTEN Kodiervorgang
                # erzwingen - bei einer Serie schneller Aenderungen
                # (durchgehendes Scrollen) wuerde das Event sonst weit
                # oefter als alle 0.2s auswachen.
                since_last = time.monotonic() - last_encode
                if since_last < MIN_ENCODE_INTERVAL:
                    time.sleep(MIN_ENCODE_INTERVAL - since_last)
                if fb.width <= MAX_MIRROR_WIDTH and fb.flip_gen != last_gen:
                    self.stream.publish_screen(fb.width, fb.height,
                                               fb.stride, fb.buf)
                    last_gen = fb.flip_gen
                    last_encode = time.monotonic()
            except Exception:
                pass  # naechster Durchlauf versucht es erneut - ein
                      # einzelner fehlgeschlagener Schnappschuss ist
                      # kein Grund, den Hintergrund-Thread zu beenden

    def _publish_stream(self):
        if not self.stream:
            return
        # PERFORMANCE-FIX (Analyse eines Nutzer-Reviews, gegen den echten
        # Code geprueft und bestaetigt): _publish_stream() lief bisher bei
        # JEDEM Schleifendurchlauf in run() - auf CRT bis zu ~100x/Sekunde -
        # und baute dabei IMMER den kompletten stream_state() auf (inkl.
        # der ungecachten _display_items()-Sortierung sowie Metadaten-/RA-
        # Lookups), nur um DANACH festzustellen, dass sich meistens gar
        # nichts geaendert hat. Betrifft nur Sitzungen mit aktivem Stream-
        # Overlay, dort aber potenziell sehr haeufig.
        #
        # Fix: guenstige Vorpruefung OHNE _display_items()/Metadaten-
        # Zugriff (nur bereits vorhandene Attribute: Seite/Kategorie/
        # Auswahl/Scroll/Songtitel) - hat sich NICHTS davon geaendert,
        # lohnt sich der teure volle Aufbau meistens nicht. BEWUSST kein
        # rein ereignisbasiertes Dirty-Flag (haette an JEDER Stelle im
        # Code manuell gesetzt werden muessen, die RA-Fortschritt/
        # Spielzeit/Favoriten aendert - hohes Risiko, eine Stelle zu
        # uebersehen und damit den Zuschauern einen veralteten Stand zu
        # zeigen). Stattdessen zusaetzliches Zeit-Sicherheitsnetz: selbst
        # ohne Aenderung an den guenstigen Feldern wird spaetestens alle
        # 2 Sekunden trotzdem einmal voll aufgebaut - faengt Hintergrund-
        # Aenderungen ab (RA-Fortschritt kommt asynchron rein, Spielzeit
        # laeuft weiter), OHNE bei jedem einzelnen Tick die teure Arbeit
        # zu wiederholen.
        now = time.monotonic()
        nowplaying = (self.music.current_track_name()
                      if hasattr(self, "music") else None)
        cheap_sig = (self.page, self.cat_i, self.item_i, self.scroll, nowplaying)
        last_cheap = getattr(self, "_stream_cheap_sig", None)
        last_full_check = getattr(self, "_stream_last_full_check", 0.0)
        if cheap_sig == last_cheap and now - last_full_check < 2.0:
            return
        self._stream_cheap_sig = cheap_sig
        self._stream_last_full_check = now
        try:
            st = self.stream_state()
        except Exception:
            return
        sig = (st["category"], st["name"], st["nowplaying"],
               st["index"], st["total"], st.get("playtime"),
               st.get("ra_progress"), st.get("favorite"))
        if sig != self._stream_sig:
            self._stream_sig = sig
            self.stream.publish(st)

    def _show_max_level_boot_effect(self):
        """Kurzer Extra-Effekt beim Booten, NUR wenn das Frontend-Level
        das Maximum erreicht hat (Nutzerwunsch: "Easter Egg System",
        Frontend-Level-Teil). Bewusst als EIGENSTAENDIGE, separate
        Methode gebaut - ruehrt die performance-kritische Bildsequenz-
        Schleife in play_boot_animation() nicht an (dort wurde bereits
        mehrfach gezielt auf Geschwindigkeit optimiert, ein Umbau dort
        haette dieses Risiko unnoetig wieder aufgemacht). Anders als die
        Bildsequenz selbst NICHT durch einen "einmal pro Boot"-Marker
        begrenzt - bewusst bei JEDEM Boot sichtbar, solange das Level
        gehalten wird (kurz genug, um nicht zu stoeren, wuerdigt den
        erreichten Stand aber jedes Mal aufs Neue)."""
        if compute_frontend_level() < FRONTEND_LEVEL_MAX:
            return
        fb = self.fb
        W, H = fb.width, fb.height
        s = max(1, H // 360)
        accent = THEMES.get(current_theme_name(), THEMES["dark"])["C_ACCENT"]
        msg = t("max_level_boot_effect")
        msg_scale = self._fit_scale(msg, W - 40 * s, s + 1)
        msg_w = len(msg) * 8 * msg_scale
        fb.clear((0, 0, 0))
        fb.text((W - msg_w) // 2, (H - 8 * msg_scale) // 2, msg, msg_scale,
                accent, (0, 0, 0))
        fb.flip()
        self.inp.read_action(timeout=1.2)   # ueberspringbar wie die Bildsequenz

    def _show_theme_unlock_flourish(self, msg, accent):
        """Kurzer Vollbild-Effekt beim Freischalten eines der 9 neuen
        Secret-Themes (SECRET_THEME_META) - bewusst nach dem Vorbild von
        _show_max_level_boot_effect() gebaut (gleiches Muster: Bildschirm
        leeren, zentrierten Text in der neuen Akzentfarbe zeigen,
        ueberspringbar per Tastendruck warten), aber als eigene, generische
        Methode statt Kopie, weil sie hier zusaetzlich die Akzentfarbe als
        Parameter bekommt (jedes der 9 Themes hat eine eigene) und WAEHREND
        des laufenden Betriebs aufgerufen wird, nicht nur beim Boot.
        Genau wie bei _draw_search_overlay() (siehe dort) wird hier direkt
        auf den Framebuffer gemalt, OHNE die normale Seiten-Zeichenroutine
        - deshalb am Ende zwingend fb.mark_full_redraw(), sonst haelt der
        Fast-Path in _draw_page_items_impl() faelschlich den alten Puffer-
        Stand fuer aktuell und der Flourish-Text bliebe als Geisterbild
        auf dem Screen stehen (identischer Bug wie beim Suchbalken)."""
        fb = self.fb
        W, H = fb.width, fb.height
        s = max(1, H // 360)
        msg_scale = self._fit_scale(msg, W - 40 * s, s + 1)
        msg_w = len(msg) * 8 * msg_scale
        fb.clear((0, 0, 0))
        fb.text((W - msg_w) // 2, (H - 8 * msg_scale) // 2, msg, msg_scale,
                accent, (0, 0, 0))
        fb.flip()
        self.inp.read_action(timeout=1.2)   # ueberspringbar
        fb.mark_full_redraw()

    def _draw_dragend_logo_boot(self):
        """Eigenes Logo beim Start (Nutzerwunsch: 'mein eigenes Logo
        beim Startup anzeigen lassen und gegen das alte ersetzen'),
        mit demselben Flacker-Effekt wie zuvor beim generischen D-Pad-
        Symbol - nur auf ein echtes Bild angewendet statt auf simple
        Rechtecke (siehe Framebuffer._scale_brightness()). Wird NUR
        aufgerufen, wenn dragend_logo_enabled() zutrifft (Menuepunkt
        System -> Anzeige & Sound) UND die Logo-Datei tatsaechlich
        existiert - beide Bedingungen bereits vom Aufrufer geprueft
        (_draw_default_boot_icon() bleibt als Rueckfall bestehen, falls
        eine der beiden nicht zutrifft)."""
        fb = self.fb
        W, H = fb.width, fb.height
        art = ART.get(DRAGEND_LOGO_FILE)
        if not art:
            self._draw_default_boot_icon()
            return
        lw, lh, pix = art
        # In den verfuegbaren Platz einpassen (max. 70% der kleineren
        # Bildschirmseite) - genug Rand ringsum, passt auf CRT genauso
        # wie auf HDMI, ohne eigene Fallunterscheidung noetig.
        max_dim = int(min(W, H) * 0.7)
        scale = min(1.0, max_dim / max(lw, lh))
        dw, dh = max(1, int(lw * scale)), max(1, int(lh * scale))
        if scale < 1.0:
            scaled = ART.get_scaled(DRAGEND_LOGO_FILE, dw, dh)
            if scaled:
                dw, dh, pix = scaled
        ax = (W - dw) // 2
        ay = (H - dh) // 2 - 10 * max(1, H // 360)

        # Gleiche Flacker-Sequenz (Helligkeitsstufe, Wartezeit) wie
        # beim bisherigen D-Pad-Symbol - simuliert eine alte Roehre,
        # die "warm wird". Bild wird bei jeder Stufe frisch aus dem
        # ORIGINAL skaliert (nicht kumulativ nachgedunkelt), damit
        # Rundungsfehler sich nicht ueber mehrere Stufen aufsummieren.
        sequence = [0.06, 0.0, 0.35, 0.0, 0.7, 0.45, 1.0]
        holds =    [0.10, 0.05, 0.10, 0.05, 0.10, 0.06, 0.55]
        title = t("boot_default_title")
        s = max(1, H // 360)
        title_scale = self._fit_scale(title, W - 40 * s, s)
        title_w = len(title) * 8 * title_scale
        title_y = ay + dh + 14 * s

        for factor, hold in zip(sequence, holds):
            fb.clear((0, 0, 0))
            if factor > 0:
                frame = pix if factor >= 1.0 else fb._scale_brightness(pix, factor)
                self.blit(ax, ay, dw, dh, frame)
                if factor >= 1.0:
                    accent = accent_for(None)
                    fb.text((W - title_w) // 2, title_y, title,
                            title_scale, accent, (0, 0, 0))
            # Gleicher VSync-Umgehungs-Bugfix wie beim D-Pad-Symbol
            # (siehe dortiger Kommentar) - direkter Speicherschreib-
            # vorgang statt flip(), da dieser fruehe Boot-Zeitpunkt
            # einen haengenden ioctl-Aufruf ausloesen kann.
            fb.mm[:] = fb.buf
            if self.inp.read_action(timeout=hold) is not None:
                return

    def _draw_default_boot_icon(self):
        """Zeigt eine kurze, selbst gezeichnete Standard-Boot-Animation
        (D-Pad-Symbol, das flackernd "zum Leben erwacht"), wenn KEIN
        eigenes Boot-Animation-Verzeichnis vorhanden ist - der
        Normalfall, die meisten Nutzer erstellen sich nie eine eigene
        Animation ueber video_to_bootanim.py. Nutzerwunsch: "standard-
        maessig was dabei haben". Bisher passierte in diesem Fall gar
        nichts Sichtbares (play_boot_animation() kehrte sofort zurueck,
        direkter Sprung ins Menue).

        Komplett aus unseren eigenen, laengst vorhandenen Zeichen-
        Mitteln gebaut (nur rect()/text(), kein Bild/Video-Codec noetig)
        - passt zur "keine zusaetzliche Last"-Philosophie. Das D-Pad-
        Kreuz besteht aus nur zwei sich ueberlappenden Rechtecken -
        bewusst simpel gehalten statt eines Pixel-Bitmaps, damit jeder
        Frame nur zwei billige rect()-Aufrufe kostet. Bewusst
        EIGENSTAENDIG gestaltet, keine Anlehnung an ein echtes
        Konsolen-Boot-Logo (gleiche Vorsicht wie beim Soundthema)."""
        fb = self.fb
        W, H = fb.width, fb.height
        s = max(1, H // 360)
        cx, cy = W // 2, H // 2 - 20 * s
        arm = 10 * s       # Balkenbreite des Kreuzes
        length = 34 * s    # Gesamtlaenge je Achse

        def draw_dpad(color):
            fb.rect(cx - arm // 2, cy - length // 2, arm, length, color)
            fb.rect(cx - length // 2, cy - arm // 2, length, arm, color)

        accent = accent_for(None)
        dim = tuple(c // 4 for c in accent)
        mid = tuple(c // 2 for c in accent)

        # Flacker-Sequenz: dunkel -> aus -> mittel -> aus -> voll, dann
        # kurz halten - simuliert eine alte Roehre, die "warm wird".
        # (Farbe, Wartezeit in Sekunden) - None = kurz schwarz (Flackern).
        sequence = [
            (dim, 0.10), (None, 0.05), (mid, 0.10), (None, 0.05),
            (accent, 0.10), (mid, 0.06), (accent, 0.55),
        ]
        title = t("boot_default_title")
        title_scale = self._fit_scale(title, W - 40 * s, s)
        title_w = len(title) * 8 * title_scale
        title_y = cy + length // 2 + 20 * s

        for color, hold in sequence:
            fb.clear((0, 0, 0))
            if color is not None:
                draw_dpad(color)
                if color == accent:
                    fb.text((W - title_w) // 2, title_y, title,
                            title_scale, accent, (0, 0, 0))
            # BUGFIX (Nutzer-Rueckmeldung von echter Hardware: nach dem
            # Update bleibt der Bildschirm schwarz, nichts passiert mehr -
            # per Analyse hergeleitet, da keine Log-Datei half): normales
            # flip() wartet per ioctl (FBIO_WAITFORVSYNC) auf den naechsten
            # Bildwechsel, BEVOR geschrieben wird - bisher war das immer
            # sicher, WEIL flip() erst beim allerersten ECHTEN Menue-Aufbau
            # aufgerufen wurde, zu einem Zeitpunkt, an dem das System
            # laengst stabil laeuft. Diese neue Standard-Animation ruft
            # flip() jetzt aber viel FRUEHER auf, direkt nach dem
            # Systemstart, moeglicherweise waehrend MiSTer selbst noch
            # mitten im Uebergang steckt. Schlaegt der ioctl in diesem
            # fragilen Fenster nicht sauber und schnell fehl, sondern
            # HAENGT er (statt einen Fehler zu werfen), wuerde das
            # exakt zum gemeldeten Bild passen - und ein try/except haette
            # das NICHT retten koennen, da ein haengender ioctl-Aufruf sich
            # nicht per Python-Exception unterbrechen laesst. Deshalb hier
            # bewusst der VSync-Wartemechanismus komplett umgangen (direkter
            # Speicherschreibvorgang) - fuer eine derart kurze, wenige Mal
            # flackernde Animation ist ein winziges Tearing-Risiko ein
            # deutlich kleineres Uebel als ein moeglicher kompletter
            # Stillstand des gesamten Frontends.
            fb.mm[:] = fb.buf
            if self.inp.read_action(timeout=hold) is not None:
                return   # ESC/beliebige Taste ueberspringt den Rest

    def play_boot_animation(self):
        """Spielt eine Bildsequenz ab (frame_0001.art, frame_0002.art,
        ...), einmal pro MiSTer-Boot, bevor das normale Menue
        erscheint. Erkennt automatisch, ob CRT- oder HDMI-Menuemodus
        aktiv ist, und sucht zuerst in BOOTANIM_DIR_crt/ bzw.
        BOOTANIM_DIR_hdmi/ - fehlt dieser modusspezifische Ordner
        (z.B. bei einer Installation von vor dieser Funktion), wird
        ersatzweise BOOTANIM_DIR/ ohne Suffix verwendet (alte,
        ungeteilte Struktur bleibt so weiterhin nutzbar). Jedes Bild
        wird formatfuellend (letterboxed, keine Verzerrung) zentriert
        gezeigt. Fehlt am Ende trotzdem jeder passende Ordner, ist er
        leer, oder wurde die Animation in diesem Boot schon gezeigt,
        passiert einfach nichts - kein Fehler, direkt weiter ins Menue."""
        if os.path.exists(BOOTANIM_PLAYED_MARKER):
            return
        mode = "crt" if crt_menu_active() else "hdmi"
        bootanim_dir = BOOTANIM_DIR + "_" + mode
        if not os.path.isdir(bootanim_dir):
            bootanim_dir = BOOTANIM_DIR   # Rueckwaerts-kompatibel
        try:
            frames = sorted(f for f in os.listdir(bootanim_dir)
                            if f.lower().endswith(".art"))
        except OSError:
            frames = []
        if not frames:
            # Kein eigenes Boot-Animation-Verzeichnis vorhanden (der
            # Normalfall) - Standard-Animation zeigen statt direkt ins
            # Menue zu springen (siehe _draw_default_boot_icon()).
            # NEU: bevorzugt das Dragend-Logo (eigener Flacker-Effekt,
            # siehe _draw_dragend_logo_boot()) - abschaltbar ueber
            # System -> Anzeige & Sound, faellt dann auf das alte,
            # neutrale D-Pad-Symbol zurueck.
            try:
                if dragend_logo_enabled() and os.path.exists(DRAGEND_LOGO_FILE):
                    self._draw_dragend_logo_boot()
                else:
                    self._draw_default_boot_icon()
            except Exception:
                LOG("_draw_default_boot_icon CRASH:\n" + traceback.format_exc())
            # BUGFIX (beim eigenen Testen gefunden, noch vor jeder
            # Auslieferung): ohne dies wuerde die Markierungsdatei hier
            # NIE geschrieben (das passiert normalerweise erst ganz am
            # Ende der Funktion, den dieser fruehe Ruecksprung ueberspringt)
            # - die Standard-Animation liefe dann bei JEDEM Aufruf erneut,
            # nicht nur einmal pro Boot wie die eigene Animation.
            try:
                with open(BOOTANIM_PLAYED_MARKER, "w") as f:
                    f.write("1")
            except OSError:
                pass
            return

        # Optionale Zeitsteuerung: bootanim.json neben den Frames kann
        # {"fps": 12} enthalten - Standard 10 fps, falls nichts angegeben.
        fps = 10
        try:
            meta = json.load(open(os.path.join(bootanim_dir, "bootanim.json")))
            fps = max(1, min(30, int(meta.get("fps", fps))))
        except (OSError, ValueError, TypeError):
            pass
        frame_time = 1.0 / fps

        fb = self.fb
        W, H = fb.width, fb.height
        LOG("play_boot_animation: %s-Modus, %d Frames bei %d fps aus %s"
           % (mode.upper(), len(frames), fps, bootanim_dir))
        try:
            for fn in frames:
                t0 = time.monotonic()
                path = os.path.join(bootanim_dir, fn)
                # Native Groesse nutzen (kein Hochskalieren) - deutlich
                # schneller, besonders bei HDMI: ein Frame, das schon
                # in Bildschirmgroesse vorliegt, braucht dann nur noch
                # dekodiert und direkt gezeigt zu werden, statt
                # zusaetzlich teuer auf Vollbild aufgeblasen zu werden.
                # Nur falls die Quelle GROESSER als der Bildschirm ist
                # (z.B. versehentlich zu hochaufgeloest erzeugt), wird
                # zur Sicherheit doch herunterskaliert.
                art = ART.get(path)
                if art and (art[0] > W or art[1] > H):
                    art = ART.get_scaled(path, W, H)
                fb.clear((0, 0, 0))
                if art:
                    aw, ah, pix = art
                    ax = max(0, (W - aw) // 2)
                    ay = max(0, (H - ah) // 2)
                    self.blit(ax, ay, aw, ah, pix)
                fb.flip()
                # ESC oder ein beliebiger Tastendruck ueberspringt den Rest
                if self.inp.read_action(timeout=max(0.0,
                        frame_time - (time.monotonic() - t0))) is not None:
                    LOG("play_boot_animation: uebersprungen")
                    break
        except Exception:
            LOG("play_boot_animation CRASH:\n" + traceback.format_exc())
        try:
            with open(BOOTANIM_PLAYED_MARKER, "w") as f:
                f.write("1")
        except OSError:
            pass

    def run(self):
        # enter_console_mode()/set_cursor_blink()/inp.grab() passieren
        # jetzt schon in __init__(), VOR dem Scan - siehe Kommentar dort.
        #
        # BUGFIX (Performance-Nachfrage des Nutzers, gezielt nachgemessen):
        # clear() berechnet die zeilenbasierte Vignette (siehe
        # _apply_vignette_rows()) beim ALLERERSTEN Aufruf fuer eine
        # bestimmte Hintergrundfarbe+Aufloesung frisch (~370ms bei 1080p
        # in dieser Sandbox, auf der schwaecheren MiSTer-CPU vermutlich
        # eher mehr) - alle folgenden Aufrufe mit derselben Farbe/
        # Aufloesung sind dann durch den Cache (self._rowcache) praktisch
        # kostenlos. Ohne Vorwaermen traf dieser einmalige Ruck bisher
        # ausgerechnet den ALLERERSTEN echten Menue-Aufbau - also genau
        # den Moment, in dem der Nutzer zum ersten Mal hinschaut. Da die
        # Boot-Animation (siehe play_boot_animation()) bei JEDEM MiSTer-
        # Neustart erneut abgespielt wird (Marker liegt in /tmp, das bei
        # jedem Reboot geleert wird), ist das der ideale Ort, den Ruck zu
        # verstecken: einmal clear() mit der normalen Hintergrundfarbe
        # aufrufen, BEVOR die Animation beginnt - waehrend der Nutzer
        # ohnehin auf die Animation schaut, nicht auf das eigentliche Menue.
        #
        # ERWEITERT fuer die neue Standard-Boot-Animation (siehe
        # _draw_default_boot_icon()): die zeichnet auf reinem Schwarz
        # (0,0,0), einer ANDEREN Farbe als C_BG - ohne separates
        # Vorwaermen haette genau dieselbe Art Ruckler dort erneut
        # zugeschlagen, direkt am Anfang der neuen Animation.
        try:
            self.fb.clear(C_BG)
            self.fb.clear((0, 0, 0))
        except Exception:
            pass   # rein vorsorglich - selbst ein Fehlschlag hier darf
                   # den eigentlichen Start nicht verhindern
        self.play_boot_animation()
        self._show_max_level_boot_effect()
        self.draw()
        # NEUES FEATURE (Nutzerwunsch: vereinfachte Installation, ein
        # Ersteinrichtungs-Assistent) - erscheint automatisch NUR beim
        # allerersten Start (SETUP_WIZARD_DONE_FILE liegt auf der SD-
        # Karte, nicht in /tmp - bleibt also auch nach einem Neustart
        # bestehen). Danach jederzeit ueber das System-Menue erneut
        # aufrufbar (kind == "setup_wizard"). Laeuft NACH dem ersten
        # draw() (damit im Hintergrund schon ein normales Menue zu
        # sehen ist, kein leerer/schwarzer Uebergang) und VOR dem
        # Zuruecksetzen der Leerlauf-Uhr (der Assistent selbst soll
        # nicht schon vom Attract-Modus unterbrochen werden koennen).
        if not setup_wizard_done():
            try:
                self.run_setup_wizard()
            except Exception:
                LOG("run_setup_wizard CRASH:\n" + traceback.format_exc())
            self.draw()
        # WICHTIG (Bugfix): der Leerlauf-Zaehler fuer den Attract-Modus
        # wurde bisher schon in __init__() gesetzt - also VOR dem
        # (potenziell langsamen) Scan und der Boot-Animation. Dauerten
        # beide zusammen laenger, war ein Grossteil der 45 Sekunden
        # schon verstrichen, BEVOR der Nutzer das Menue ueberhaupt zu
        # sehen bekam - der Attract-Modus konnte dadurch fast sofort
        # nach dem sichtbaren Start einsetzen. Erst hier zuruecksetzen,
        # wenn das Menue tatsaechlich sichtbar und bedienbar ist.
        self._last_input_time = time.monotonic()
        LOG("Menue sichtbar, Leerlauf-Uhr fuer Attract-Modus gestartet")
        # NEUES FEATURE (Nutzerwunsch: "Update-Nachricht soll sofort im
        # Hauptmenue eingeblendet werden, wenn ein Update verfuegbar ist,
        # fuer 2-3 Sekunden" - vorher hing der Update-Check-Start am
        # selben Leerlauf-Schwellenwert wie der Attract-Modus, siehe
        # _attract_delay_cached() weiter unten in next_action(), der
        # Hinweis kam dadurch fruehestens nach vielen Sekunden Leerlauf
        # an). Bewusst hierher verschoben, an dieselbe Stelle, an der
        # bereits die Leerlauf-Uhr selbst zurueckgesetzt wird - das Menue
        # ist ab hier sichtbar/bedienbar, ein einzelner leiser
        # Netzwerk-Abruf im Hintergrund verzoegert nichts (siehe
        # _check_for_update_background(), laeuft in einem eigenen
        # Thread). Gleiches Ein-mal-pro-Sitzung-Muster (_update_check_
        # started) wie zuvor - next_action()'s Idle-Zweig holt das
        # Ergebnis weiterhin ab und zeichnet es, sobald es vorliegt (dort
        # jetzt ohne eigene Start-Bedingung mehr, siehe dortiger
        # Kommentar).
        if (not getattr(self, "_update_check_started", False)
                and update_check_enabled()):
            self._update_check_started = True
            threading.Thread(target=self._check_for_update_background,
                             daemon=True).start()
        # SICHERHEITSNETZ CRT-Wechsel (siehe mark_crt_pending_confirm() in
        # fe/settings.py und den zugehoerigen Idle-Zweig in next_action()):
        # falls das Bild tatsaechlich ankommt, soll der Nutzer sofort sehen,
        # WARUM das Menue sich gleich von selbst zurueckschalten koennte,
        # statt sich nur zu wundern - bewusst eine laengere Anzeigedauer als
        # die eingebauten 5s von draw(message=..., prominent=True) (siehe
        # dortiger Kommentar), deshalb hier direkt gesetzt statt ueber den
        # message-Parameter.
        if crt_pending_confirm():
            self._prominent_message = t("crt_pending_notice", CRT_CONFIRM_TIMEOUT)
            self._prominent_message_until = time.monotonic() + CRT_CONFIRM_TIMEOUT
            self.draw()
        try:
            move_streak = 0     # zaehlt gehaltene hoch/runter-Wiederholungen
            move_last = None    # fuer den Turbo-Sprung (einzelne Position)
            move_last_time = 0.0
            page_streak = 0     # zaehlt gehaltene links/rechts-Wiederholungen
            page_last = None    # fuer den Turbo-Sprung (seitenweise)
            page_last_time = 0.0
            while True:
                # Zustand VOR dem Blockieren veroeffentlichen - spiegelt
                # die aktuell ANGEZEIGTE Auswahl (Ergebnis der vorigen
                # Aktion). Vorher direkt NACH next_action(), also VOR der
                # Verarbeitung dieser neuen Aktion - dadurch hing das
                # Overlay einen Schritt hinterher (zeigte noch das
                # "vorherige Spiel", bis die naechste Eingabe kam).
                self._publish_stream()
                act = self.next_action()
                LOG("aktion: %s (Seite %d, confirm=%s)"
                    % (act, self.page, self.confirm_quit))

                # Geheimcode-Erkennung (siehe
                # check_secret_code()) - beobachtet nur, greift nie in
                # die normale Verarbeitung ein. Absichtlich VOR jeder
                # Reaktion auf die Aktion selbst, damit z.B. "ok" am
                # Ende eines Codes nicht zuerst schon etwas anderes
                # ausloest (z.B. ein Spiel startet), bevor der Code
                # erkannt wird.
                #
                # BUGFIX (beim abschliessenden Durchcheck gefunden): die
                # Pruefung lief bisher auf JEDER Seite, nicht nur im
                # Hauptmenue (Seite 0) wie eigentlich vorgesehen und
                # kommuniziert. Einer der (kurzen) Codes waere dadurch
                # potenziell auch waehrend ganz normaler Navigation in
                # einer Spieleliste ungewollt ausloesbar gewesen (z.B.
                # einen Ordner betreten+verlassen+etwas bestaetigen).
                # Jetzt nur noch aktiv, wenn self.page == 0 - der Puffer
                # wird auf den anderen Seiten auch nicht weiter befuellt,
                # damit ein Seitenwechsel mitten in einer Eingabe den Code
                # sauber
                # abbricht statt ihn "anzuhalten" und spaeter im
                # Hauptmenue ueberraschend fortzusetzen.
                if act is not None and self.page == 0:
                    self._secret_buffer.append(act)
                    if len(self._secret_buffer) > SECRET_CODE_MAXLEN:
                        self._secret_buffer.pop(0)
                    secret_id = check_secret_code(self._secret_buffer)
                    if secret_id:
                        self._secret_buffer = []  # verhindert Doppel-Treffer
                        is_new = _unlock_secret(secret_id)
                        self._on_secret_triggered(secret_id, is_new)
                        continue
                elif act is not None:
                    self._secret_buffer = []

                # NEUES FEATURE (Nutzerwunsch: Volltextsuche statt nur
                # Anfangsbuchstaben-Sprung - "bei vielen ROMs ist das
                # besser"). Bewusst VOR der normalen Aktionsverarbeitung
                # abgefangen, wie beim Geheimcode-Puffer oben - im
                # Suchmodus sollen Buchstabentasten die Anfrage
                # aufbauen statt wie sonst einzeln zu springen.
                if self._search_mode:
                    items = [] if self.page == 0 else self._display_items()
                    names = ([c[0] for c in self.cats] if self.page == 0
                             else [it[0] for it in items] if items else [])
                    if act == "search_backspace":
                        self._search_query = self._search_query[:-1]
                        idx = jump_to_substring(names, self._search_start_i, self._search_query) \
                            if self._search_query else self._search_start_i
                        if self.page == 0:
                            self.cat_i = idx
                        elif items:
                            self.item_i = idx
                        self.draw()
                        continue
                    elif act is not None and act.startswith("letter:"):
                        self._search_query += act.split(":", 1)[1]
                        cur = self.cat_i if self.page == 0 else self.item_i
                        idx = jump_to_substring(names, cur, self._search_query)
                        if self.page == 0:
                            self.cat_i = idx
                        elif items:
                            self.item_i = idx
                            self.marquee_reset()
                        self.draw()
                        continue
                    elif act == "ok":
                        # Suche bestaetigen - am gefundenen Eintrag stehen
                        # bleiben, Suchmodus verlassen.
                        self._search_mode = False
                        self.draw()
                        continue
                    elif act in ("back", "exit", "search"):
                        # Suche abbrechen - zurueck zur Position VOR
                        # Suchbeginn (klassisches Abbrechen-Verhalten,
                        # kein "haengengebliebener" Zufallstreffer).
                        self._search_mode = False
                        if self.page == 0:
                            self.cat_i = self._search_start_i
                        else:
                            self.item_i = self._search_start_i
                        self.draw()
                        continue
                    else:
                        # Jede andere Taste (hoch/runter/links/rechts
                        # etc.) beendet die Suche stillschweigend und
                        # laesst die Aktion danach ganz normal weiter-
                        # laufen (faellt einfach durch, kein continue).
                        self._search_mode = False
                elif act == "search":
                    self._search_mode = True
                    self._search_query = ""
                    self._search_start_i = self.cat_i if self.page == 0 else self.item_i
                    self.draw()
                    continue

                # Zustand VOR der Aktion merken - fuer die Entscheidung,
                # ob nach einem einzelnen hoch/runter-Schritt der leichte
                # Navigations-Zeichenpfad ausreicht (siehe unten, nach
                # der kompletten Aktionsverarbeitung).
                pre_page = self.page
                pre_item_i = self.item_i
                pre_cat_i = self.cat_i

                # Soundeffekt zentral an EINER Stelle ausloesen, statt
                # in jedem einzelnen der vielen Aktions-Zweige weiter
                # unten - deckt dadurch automatisch jeden Kontext ab
                # (Hauptliste, Beenden-Dialog, Buchstaben-Sprung usw.),
                # ohne an vielen Stellen Code duplizieren zu muessen.
                # music_playing: TATSAECHLICH gerade laufender mpg123-
                # Prozess (nicht nur "Musik ist eingeschaltet") - siehe
                # play_sfx() fuer den Grund (Geraete-Ueberschneidung).
                music_playing = self.music._proc_alive()
                if act in ("up", "down", "left", "right"):
                    play_sfx("move", music_playing)
                elif act == "ok":
                    play_sfx("confirm", music_playing)
                elif act in ("back", "exit"):
                    play_sfx("back", music_playing)

                # ---- Beenden-Bestaetigung hat Vorrang vor allem anderen ----
                if self.confirm_quit:
                    # BUGFIX (Nutzer-Rueckmeldung, siehe ausfuehrlicher
                    # Kommentar bei draw_confirm_dialog()/
                    # _confirm_dialog_toggle()): bisher NUR links/rechts,
                    # jetzt auch hoch/runter.
                    if self._confirm_dialog_toggle(act):
                        pass
                    elif act == "ok":
                        # NEU: siehe CONFIRM_DIALOG_IGNORE_OK_WINDOW -
                        # ein OK unmittelbar nach dem Oeffnen (z.B. ein
                        # reflexartiges zweites OK) wird bewusst
                        # ignoriert, statt sofort "Nein" zu bestaetigen.
                        if not self._confirm_dialog_ok_too_soon():
                            if self.confirm_choice == 0:
                                break                   # Ja bestaetigt
                            self.confirm_quit = False    # Nein
                    elif act in ("exit", "back"):
                        self.confirm_quit = False    # ESC/B im Dialog = Nein
                    self.draw()
                    continue

                # ---- Update-Installieren-Abfrage hat ebenfalls Vorrang ----
                # NEUES FEATURE (Nutzerwunsch: "koennen wir das
                # Update-Popup um eine Abfrage 'jetzt installieren oder
                # spaeter' erweitern? Wenn man dann ja anklickt, dass
                # Frontend_Install.sh ausgefuehrt wird und danach der
                # MiSTer einmal neugestartet wird"): gleiches Grundmuster
                # wie die Beenden-Bestaetigung direkt oberhalb - links
                # waehlt "Jetzt" (self.confirm_choice==0), rechts/
                # Standard "Spaeter". Ein "Jetzt" hier startet
                # Frontend_Install.sh ueber genau denselben, bereits
                # ausfuehrlich getesteten Weg wie ein manueller Tap auf
                # "Frontend Install" im Scripts-Menue (run_script(), siehe
                # dortiger Kommentar) - der Kopfkommentar in
                # Frontend_Install.sh/Frontend_Update.sh dokumentiert im
                # Detail, warum dieser Weg den ALTEN Frontend-Prozess
                # (auch wenn er selbst gerade blockierend darauf wartet)
                # sauber beendet.
                #
                # GEAENDERT (Nutzer-Rueckmeldung: "sollten wir nach der
                # Installation einen Hardreset/kompletten Neustart machen
                # lassen, damit die Aenderungen auch definitiv uebernommen
                # sind?" - bestaetigt, ausdruecklich fuer BEIDE Wege
                # gleichermassen, also auch hier): anders als zuvor endet
                # Frontend_Install.sh -> Frontend_Update.sh jetzt NICHT
                # mehr in einem einfachen Neustart des Frontend-PROZESSES,
                # sondern in einem kompletten MiSTer-Neustart (sync;
                # reboot) - ein zusaetzlicher manueller Neustart ist zwar
                # weiterhin nicht noetig, ABER anders als der Kommentar
                # hier frueher behauptete, findet jetzt sehr wohl ein
                # echter kompletter MiSTer-Neustart statt (siehe
                # Frontend_Update.sh fuer die ausfuehrliche Begruendung,
                # warum das zuverlaessiger ist als der reine
                # Prozess-Neustart).
                if self.confirm_update:
                    # BUGFIX: siehe Kommentar beim confirm_quit-Zweig
                    # oben - hoch/runter jetzt ebenfalls unterstuetzt.
                    if self._confirm_dialog_toggle(act):
                        pass
                    elif act == "ok":
                        # NEU: siehe Kommentar beim confirm_quit-Zweig oben.
                        if not self._confirm_dialog_ok_too_soon():
                            self.confirm_update = False
                            if self.confirm_choice == 0:
                                self.run_script(os.path.join(SCRIPTS_DIR, "Frontend_Install.sh"))
                                continue
                    elif act in ("exit", "back"):
                        self.confirm_update = False    # ESC/B im Dialog = Spaeter
                    self.draw()
                    continue

                name, _root_node, _syskey = self.cats[self.cat_i]
                items = self._display_items() if self.page == 1 else []

                # Turbo-Sprung hoch/runter: je laenger GEHALTEN, desto
                # groesser die Schrittweite (1 -> 2 -> 4 -> 10). Das
                # beschleunigende Wiederholungs-Intervall aus dem
                # InputManager laesst die Tick-Rate schon steigen; hier
                # kommt zusaetzlich eine steigende Sprungweite dazu.
                #
                # WICHTIG (Bugfix): der Streak-Zaehler darf NUR bei
                # einem tatsaechlich GEHALTENEN Tastendruck hochzaehlen,
                # nicht bei mehreren schnellen, aber EINZELNEN Klicks in
                # dieselbe Richtung - sonst sprang der Cursor gelegent-
                # lich unerwartet zwei Zeilen, wenn jemand zuegig
                # mehrfach hintereinander geklickt hat. Ein echtes
                # Halten erzeugt Wiederholungen im Abstand von hoechstens
                # REPEAT_DELAY (0.4s); liegt mehr Zeit dazwischen, war es
                # ein neuer, einzelner Tastendruck - Zaehler faengt dann
                # wieder bei 1 an, unabhaengig von der Richtung.
                now_t = time.monotonic()
                if act in ("up", "down"):
                    if act == move_last and (now_t - move_last_time) < 0.5:
                        move_streak += 1
                    else:
                        move_streak = 1
                    move_last = act
                    move_last_time = now_t
                else:
                    move_streak = 0
                    move_last = None
                # BUGFIX/NEUES FEATURE (Nutzer-Rueckmeldung: "diese
                # Zeilensprünge durch das Überspringen nach unten
                # gedrückt halten, in den ROMs wenn sie angezeigt
                # werden, sollen wegfallen - könnte das laggig machen?"):
                # Ja, genau das war der Fall. Die Sprungweite (1 -> 2 ->
                # 4 -> 10, siehe Kommentar oben) ist NICHT nur optisch
                # ein Zeilensprung, sondern erzwingt ab move_step > 1 IMMER
                # den vollen, teuren Bildschirmaufbau (siehe die
                # "move_step == 1"-Bedingung vor _draw_navigate_items()/
                # _draw_navigate_cats() weiter unten) - der leichte,
                # billige Zeichenpfad greift dadurch nur fuer die ersten
                # ~8 Wiederholungen einer gehaltenen Taste, danach
                # (move_streak > 8) schaltet es bei JEDEM weiteren Schritt
                # auf den vollen Aufbau um, spuerbar besonders auf HDMI.
                # Fuer die Spieleliste (Seite 1) bleibt move_step deshalb
                # jetzt IMMER bei 1 - kein Zeilensprung mehr, und der
                # leichte Zeichenpfad bleibt durchgehend aktiv, auch bei
                # lange gehaltener Taste. Schnelleres Durchlaufen langer
                # Listen bleibt trotzdem moeglich: die vom InputManager
                # selbst beschleunigte Wiederhol-Taktrate (siehe Kommentar
                # oben, bis zu ~12,5 Schritte/Sekunde) sorgt weiterhin fuer
                # zuegiges Scrollen, nur eben Zeile fuer Zeile statt in
                # Spruengen. Seite 0 (Kategorien-Hauptmenue, in aller
                # Regel eine deutlich kuerzere Liste) bleibt bewusst
                # unveraendert - dazu wurde kein entsprechender Wunsch
                # geaeussert.
                #
                # ERWEITERT (Nutzerwunsch: "3 Zeilen Sprung komplett beim
                # Scrollen rausnehmen"): der obige Absatz galt bisher nur
                # fuer die Spieleliste (Seite 1) - im Kategorien-
                # Hauptmenue (Seite 0) sprang die Auswahl bei gehaltener
                # Taste weiterhin um 2, dann 4, dann 10 Zeilen, mit exakt
                # denselben Folgekosten: ab move_step > 1 greift der
                # leichte Zeichenpfad (_draw_navigate_cats()) nicht mehr,
                # jeder weitere Schritt loest wieder den vollen
                # draw_page_cats()-Aufbau aus. Jetzt auch dort dauerhaft
                # ein Schritt pro Tastendruck - zuegiges Durchlaufen
                # bleibt ueber die vom InputManager selbst beschleunigte
                # Wiederhol-Taktrate erhalten, nur eben Zeile fuer Zeile.
                move_step = 1

                # Turbo-Sprung links/rechts: Grundschritt ist eine volle
                # Bildschirmseite, waechst beim Halten auf mehrere Seiten.
                # Gleiche Zeit-Absicherung wie oben bei hoch/runter.
                if act in ("left", "right"):
                    if act == page_last and (now_t - page_last_time) < 0.5:
                        page_streak += 1
                    else:
                        page_streak = 1
                    page_last = act
                    page_last_time = now_t
                else:
                    page_streak = 0
                    page_last = None
                page_mult = (5 if page_streak > 40 else
                            3 if page_streak > 20 else
                            2 if page_streak > 8 else 1)
                base_page = self.cats_visible if self.page == 0 \
                    else self.items_visible
                page_step = max(1, base_page) * page_mult

                if act == "select":
                    # 3x Select = Beenden-Kurzbefehl per Pad, laeuft ueber
                    # dieselbe Bestaetigung wie ESC/B.
                    move_streak = page_streak = 0
                    self._go_back_or_confirm_quit()
                    continue
                if act == "exit" or act == "back":
                    self._go_back_or_confirm_quit()
                    continue
                elif act == "osd":
                    self.open_osd()
                    continue
                elif act == "music_next":
                    self.music.next_track()
                    self.draw()   # Anzeige des neuen Songs sofort aktualisieren
                    continue
                elif act == "up":
                    # Rundum-Navigation: vom ersten Eintrag nach oben
                    # geht's zum letzten - erspart langes Zurueckscrollen.
                    self._last_scroll_dir = -1
                    if self.page == 0:
                        self.cat_i = (self.cat_i - move_step) % len(self.cats)
                    elif items:
                        self.item_i = (self.item_i - move_step) % len(items)
                        self.marquee_reset()
                elif act == "down":
                    self._last_scroll_dir = 1
                    if self.page == 0:
                        self.cat_i = (self.cat_i + move_step) % len(self.cats)
                    elif items:
                        self.item_i = (self.item_i + move_step) % len(items)
                        self.marquee_reset()
                elif act == "left":
                    if self.page == 0:
                        self.cat_i = (self.cat_i - page_step) % len(self.cats)
                    elif items:
                        self.item_i = (self.item_i - page_step) % len(items)
                        self.marquee_reset()
                elif act == "right":
                    if self.page == 0:
                        self.cat_i = (self.cat_i + page_step) % len(self.cats)
                    elif items:
                        self.item_i = (self.item_i + page_step) % len(items)
                        self.marquee_reset()
                elif act.startswith("letter:"):
                    # Direktsprung per Tastatur: Buchstabentaste druecken
                    # springt zum naechsten passenden Eintrag, erneutes
                    # Druecken zum uebernaechsten (zyklisch).
                    ch = act.split(":", 1)[1]
                    if self.page == 0:
                        self.cat_i = jump_to_letter(
                            [c[0] for c in self.cats], self.cat_i, ch)
                    elif items:
                        self.item_i = jump_to_letter(
                            [it[0] for it in items], self.item_i, ch)
                        self.marquee_reset()
                elif act == "random":
                    # AENDERUNG (Nutzerwunsch): bisher sprang diese
                    # Aktion nur zu einem zufaelligen EINTRAG in der
                    # aktuellen Ansicht (Kategorie oder Spieleliste),
                    # startete aber nichts von selbst - dokumentiertes,
                    # beabsichtigtes Verhalten seit v1.28. Der Nutzer
                    # hatte das anders erwartet ("F11 druecken, irgend-
                    # ein Spiel wird gestartet") - jetzt tatsaechlich
                    # so umgesetzt: waehlt ein zufaelliges Spiel ueber
                    # ALLE Systeme hinweg (_attract_games_pool(), die
                    # gleiche Sammlung, die auch der Attract-Modus
                    # nutzt) und startet es direkt - inklusive derselben
                    # RA-Core-Abfrage, die auch beim normalen Betreten
                    # einer Kategorie mit RA-faehigem Core erscheint
                    # (siehe _enter_category()), falls das zufaellig
                    # getroffene System eine hat.
                    move_streak = page_streak = 0
                    pool = self._attract_games_pool()
                    if pool:
                        name, syskey, rand_arg = random.choice(pool)
                        ra_core = find_ra_core(syskey)
                        ra_choice = None
                        if ra_core:
                            use_ra = self.draw_core_choice_screen(syskey, name)
                            if use_ra is None:
                                # BUGFIX (Nutzer-Rueckmeldung: nach F11 +
                                # "Zurueck" am Core-Auswahlbildschirm baute
                                # sich das Hauptmenue nicht mehr richtig
                                # auf): draw_core_choice_screen() zeichnet
                                # sein eigenes Bild direkt ins Framebuffer
                                # (fb.flip()), voellig unabhaengig von
                                # self.draw(). Beim normalen Betreten einer
                                # Kategorie (_enter_category()) faengt das
                                # nachfolgende, allgemeine self.draw() am
                                # Ende der Hauptschleife das automatisch
                                # wieder auf - hier aber nicht, weil dieser
                                # Zweig IMMER mit "continue" endet (auch im
                                # Erfolgsfall, siehe unten) und diesen
                                # Aufbau-Schritt dadurch ueberspringt. Erst
                                # explizit draw(), DANN abbrechen.
                                self.draw()
                                continue   # ESC/back - Zufallsstart abgebrochen
                            ra_choice = ra_core if use_ra else None
                        rom, ext, _sk, rbf, (dl, ft, ix) = rand_arg
                        setname = None
                        if ra_choice:
                            rbf, setname = ra_choice
                        LOG("Zufallsstart (F11): %s (%s)%s"
                            % (name, syskey, " [RA-Core]" if ra_choice else ""))
                        record_recent(name, rand_arg)
                        mgl = write_mgl(rbf, rom, dl, ft, ix, setname=setname)
                        self.run_core(mgl, label=name, syskey=syskey)
                    continue
                elif act == "favorite":
                    # Favoritenstatus des markierten Spiels umschalten
                    # - nur bei einem echten Spiele-Eintrag sinnvoll
                    # (nicht bei Ordnern/Cores/Scripts/System).
                    if self.page == 1 and items:
                        label, kind, arg = items[self.item_i]
                        if kind == "game":
                            now_fav = toggle_favorite(label, arg)
                            if now_fav:
                                self._favorites_set.add(label)
                            else:
                                self._favorites_set.discard(label)
                            self._sync_favorites_category()
                            msg = self._check_achievement_popup() or (
                                t("favorite_added") if now_fav
                                else t("favorite_removed"))
                            self.draw(message=msg)
                            continue
                elif act == "completed":
                    # Durchgespielt-Status umschalten - genau wie bei
                    # "favorite", nur ohne eigene Kategorie (rein
                    # informativ, keine Navigationsliste dafuer).
                    if self.page == 1 and items:
                        label, kind, arg = items[self.item_i]
                        if kind == "game":
                            now_completed = toggle_completed(label)
                            if now_completed:
                                self._completed_set.add(label)
                            else:
                                self._completed_set.discard(label)
                            msg = self._check_achievement_popup() or (
                                t("completed_added") if now_completed
                                else t("completed_removed"))
                            self.draw(message=msg)
                            continue
                elif act == "ra_showcase":
                    # RA-Erfolgs-Vitrine (Nutzerwunsch, separate Option) -
                    # zeigt bei einem Spiel mit RA-Unterstuetzung die
                    # komplette Erfolgsliste statt nur der Zahl neben
                    # dem Cover.
                    if self.page == 1 and items:
                        label, kind, arg = items[self.item_i]
                        if kind == "game":
                            if not ra_enabled():
                                # Unterscheidet sich bewusst von
                                # "ra_showcase_none" (RA ist eingerichtet,
                                # aber GENAU DIESES Spiel hat keine
                                # RA-Daten) - sonst wirkt F6 ohne
                                # RA-Einrichtung wie eine tote Taste.
                                self.draw(message=t("ra_showcase_not_setup"))
                                continue
                            if self._ra_lookup:
                                item_syskey = self._item_syskey(
                                    items[self.item_i], self.cats[self.cat_i][2])
                                game_id = lookup_ra_game_id(
                                    self._ra_lookup, label, item_syskey)
                                if game_id:
                                    self.draw_ra_showcase_screen(label, game_id)
                                    self.draw()
                                    continue
                            self.draw(message=t("ra_showcase_none"))
                            continue
                elif act == "ok":
                    if self.page == 0:
                        self._enter_category()
                    else:
                        label, kind, arg = items[self.item_i]
                        if kind == "folder":
                            self._nav_position_stack.append((self.item_i, self.scroll))
                            self.nav_path.append(arg)
                            self.item_i = 0
                            self.scroll = 0
                            self.marquee_reset()
                        elif kind == "core":
                            self.run_core(arg, label=label)
                            continue
                        elif kind == "game":
                            rom, ext, syskey, rbf, (dl, ft, ix) = arg
                            ra_core = find_ra_core(syskey) if syskey else None
                            # Nutzerwunsch (nach Rueckmeldung praezisiert:
                            # "es wird das Spiel wieder geladen ohne
                            # Abfrage welcher Core benutzt werden soll" -
                            # eine STILLE automatische Wiederverwendung
                            # des zuletzt genutzten Cores, wie in einer
                            # frueheren Fassung gebaut, war NICHT das
                            # Gewuenschte): in WEITERSPIELEN, ZULETZT
                            # GESPIELT und FAVORITEN wird jetzt bei JEDEM
                            # Start aktiv gefragt, welcher Core verwendet
                            # werden soll (sofern fuer das jeweilige
                            # System ueberhaupt eine RA-Variante existiert) -
                            # in allen drei Faellen aus demselben Grund:
                            # es handelt sich um flache Listen aus
                            # UNTERSCHIEDLICHEN Systemen (Kategorie selbst
                            # hat syskey=None), bei denen die normale,
                            # EINMALIGE Abfrage beim Kategorie-Eintritt
                            # (_enter_category(), nur fuer echte
                            # Ein-System-Kategorien sinnvoll) nicht greift.
                            always_ask_core = self.cats[self.cat_i][0] in (
                                t("favorites_cat"), t("recent_cat"), t("continue_cat"))
                            if always_ask_core and ra_core:
                                # Vorauswahl auf der zuletzt fuer GENAU
                                # DIESES Spiel tatsaechlich verwendeten
                                # Core-Variante (siehe Bugfix-Kommentar
                                # in draw_core_choice_screen()) - gefragt
                                # wird trotzdem weiterhin jedes Mal.
                                default_ra = load_last_core_choice(label) is not None
                                use_ra = self.draw_core_choice_screen(
                                    syskey, label, default_ra=default_ra)
                                if use_ra is None:
                                    # Siehe F11-Bugfix (gleicher Grund):
                                    # draw_core_choice_screen() zeichnet
                                    # eigenstaendig - nach Abbruch explizit
                                    # neu zeichnen, sonst bleibt der
                                    # Auswahlbildschirm haengen.
                                    self.draw()
                                    continue
                                ra_choice = ra_core if use_ra else None
                            else:
                                # RA-Core-Wahl anwenden, falls beim Betreten
                                # dieser (normalen Ein-System-)Kategorie
                                # eine getroffen wurde (siehe
                                # _enter_category()/find_ra_core()) - sonst
                                # unveraendert der normale Core aus der
                                # Systemtabelle. find_ra_core() liefert
                                # (rbf_pfad, setname) - beide werden
                                # gebraucht, sonst behandelt MiSTer den
                                # RA-Core offenbar nicht korrekt als eigene,
                                # von der Standard-Konfiguration getrennte
                                # Variante (Nutzer-Rueckmeldung: startete
                                # sonst immer den normalen Core). Trifft
                                # z.B. noch auf RA-Erfolgsjaeger/Sammlungen
                                # zu (ebenfalls flache Mehr-System-Listen,
                                # aber vom Nutzer nicht als "jedes Mal
                                # fragen" gewuenscht) - dort weiterhin
                                # Rueckfall auf die zuletzt fuer GENAU
                                # DIESES Spiel tatsaechlich verwendete,
                                # persistierte Wahl (siehe
                                # load_last_core_choice()), falls in
                                # dieser Sitzung noch keine echte Kategorie
                                # betreten wurde.
                                ra_dict = getattr(self, "_ra_core_choice", {})
                                if syskey in ra_dict:
                                    ra_choice = ra_dict[syskey]
                                elif ra_core:
                                    ra_choice = load_last_core_choice(label)
                                else:
                                    ra_choice = None
                            setname = None
                            if ra_choice:
                                rbf, setname = ra_choice
                            LOG("Spielstart: %s (%s)%s" % (label, syskey,
                                " [RA-Core]" if ra_choice else ""))
                            record_recent(label, arg)
                            record_core_choice(label, ra_choice)
                            mgl = write_mgl(rbf, rom, dl, ft, ix, setname=setname)
                            self.run_core(mgl, label=label, syskey=syskey)
                            continue
                        elif kind == "script":
                            self.run_script(arg)
                            continue
                        elif kind == "osd":
                            self.open_osd()
                            continue
                        elif kind == "redraw":
                            self.fb.refresh_geometry()
                        elif kind == "rescan":
                            self.draw("Rescanning game list ...")
                            self.build_categories(force_rescan=True)
                            self.cat_i = self.item_i = 0
                            self.scroll = self.cat_scroll = 0
                            self.page = 0        # Kategorien koennten sich geaendert haben
                        elif kind == "crtmenu":
                            self.draw("Switching menu video, rebooting ...")
                            new_crt_state = toggle_crt_menu()
                            if new_crt_state is not None:
                                # SICHERHEITSNETZ (siehe Kommentar bei
                                # mark_crt_pending_confirm() in
                                # fe/settings.py): nur beim Wechsel IN den
                                # CRT-Modus setzen.
                                if new_crt_state:
                                    mark_crt_pending_confirm()
                                else:
                                    clear_crt_pending_confirm()
                                os.system("sync; reboot")
                                return
                        elif kind == "reboot":
                            os.system("sync; reboot")
                            return
                        elif kind == "quit":
                            self._confirm_quit_dialog()
                            continue
                        elif kind == "music":
                            self.music.toggle()
                            self.build_categories()   # refresh menu label
                        elif kind == "music_source":
                            self.music.cycle_source()
                            self.build_categories()   # refresh menu label
                        elif kind == "volume":
                            self.music.cycle_volume()
                            self.build_categories()   # refresh menu label
                        elif kind == "language":
                            set_language("de" if current_lang() == "en" else "en")
                            self.build_categories()
                            self.page = 0
                        elif kind == "remap":
                            self.configure_buttons()
                            continue
                        elif kind == "remap_reset":
                            KEYMAP.clear()
                            KEYMAP.update(DEFAULT_KEYMAP)
                            try:
                                os.remove(KEYMAP_CUSTOM_FILE)
                            except OSError:
                                pass
                            # NEU: "Auf Standard zuruecksetzen" soll
                            # auch einen aktiven OK/Zurueck-Tausch
                            # (siehe "swap_ok_back" weiter unten) mit
                            # zuruecksetzen - die Datei wird hier direkt
                            # entfernt statt ueber save_swap_ok_back(False),
                            # da KEYMAP oben bereits auf den echten
                            # (unvertauschten) Standard gesetzt wurde und
                            # ein zusaetzlicher Tausch-Aufruf ihn sonst
                            # sofort wieder vertauschen wuerde.
                            try:
                                os.remove(SWAP_OK_BACK_FILE)
                            except OSError:
                                pass
                            self.draw(t("remap_done"))
                            time.sleep(1.0)
                        elif kind == "swap_ok_back":
                            save_swap_ok_back(not swap_ok_back_enabled())
                            self._refresh_system_category()
                        elif kind == "curated":
                            toggle_curated_only()
                            self.build_categories()
                            self.scroll = self.cat_scroll = 0
                            self.page = 0
                        elif kind == "attract":
                            toggle_attract_mode()
                            self._refresh_system_category()
                        elif kind == "attract_delay":
                            cycle_attract_delay()
                            self._attract_delay_check_next = 0.0   # sofort neu einlesen
                            self._refresh_system_category()
                        elif kind == "theme":
                            cycle_theme()
                            self._refresh_system_category()
                            self.fb._rowcache.clear()
                            self.fb._rectcache.clear()
                        elif kind == "timezone":
                            cycle_timezone_offset()
                            # Sofort neu synchronisieren, damit die
                            # Uhrzeit ohne Neustart korrekt ist - laeuft
                            # im Hintergrund-Thread (Netzwerk-Aufruf),
                            # blockiert die Navigation daher nicht.
                            threading.Thread(
                                target=sync_system_clock_from_ntp,
                                daemon=True).start()
                            self._refresh_system_category()
                        elif kind == "network_wait":
                            save_network_wait(not network_wait_enabled())
                            self._refresh_system_category()
                        elif kind == "sfx":
                            toggle_sfx()
                            self._refresh_system_category()
                        elif kind == "dragend_logo":
                            toggle_dragend_logo()
                            self._refresh_system_category()
                        elif kind == "system_bg":
                            # NEUES FEATURE (Nutzerwunsch: "bg-Ordner
                            # rausnehmen, glaube der laggt ein wenig") -
                            # wirkt SOFORT (beide Aufrufstellen pruefen
                            # system_bg_enabled() live beim Zeichnen,
                            # kein zwischengespeicherter Zustand wie bei
                            # Stream-Overlay/Bildschirmspiegel), deshalb
                            # kein Neustart-Hinweis in der Beschriftung.
                            toggle_system_bg()
                            self._refresh_system_category()
                        elif kind == "fast_scroll":
                            # NEUES FEATURE (Nutzerwunsch: "kann man das
                            # Vsync-Warten beim Scrollen weglassen? Will
                            # ich probieren") - wirkt SOFORT wie system_bg
                            # oben (fast_scroll_enabled() wird live beim
                            # Zeichnen geprueft, siehe _draw_page_items_impl()),
                            # kein Neustart noetig.
                            toggle_fast_scroll()
                            self._refresh_system_category()
                        elif kind == "pulse_effect":
                            # NEUES FEATURE (Nutzerwunsch: "wenn wir den
                            # Schimmer-Effekt rausnehmen wuerde das noch
                            # was bringen?") - wirkt SOFORT (pulse_effect_
                            # enabled() wird live in _pulsed()/next_action()
                            # geprueft), kein Neustart noetig.
                            toggle_pulse_effect()
                            self._refresh_system_category()
                        elif kind == "eq_effect":
                            # NEUES FEATURE (Nutzerwunsch: "Equalizer im
                            # HDMI-Modus abschaltbar, um zu sehen ob es
                            # beim Scrollen besser wird") - wirkt SOFORT
                            # (eq_effect_enabled() wird live in
                            # draw_page_cats()/_draw_dynamic_cats()/
                            # next_action() geprueft), kein Neustart
                            # noetig.
                            toggle_eq_effect()
                            self._refresh_system_category()
                        elif kind == "track_marquee":
                            # NEUES FEATURE (Nutzerwunsch: "Musik-
                            # Laufschrift haette ich auch gerne noch ein
                            # und ausschaltbar") - wirkt SOFORT
                            # (track_marquee_enabled() wird live in
                            # _track_marquee_needs_scroll() geprueft,
                            # siehe dortiger Kommentar), kein Neustart
                            # noetig. Betrifft NUR den scrollenden
                            # Songtitel, nicht die Laufschrift fuer zu
                            # lange Spieletitel in der Liste (eigenes,
                            # getrenntes System).
                            toggle_track_marquee()
                            self._refresh_system_category()
                        elif kind == "stream_overlay":
                            # NEUES FEATURE (Nutzerwunsch: "kann man das
                            # mit Stream Overlay in den Optionen an/aus
                            # schaltbar machen?") - toggelt nur die
                            # Freigabe-Datei (siehe fe/settings.py), der
                            # StreamServer selbst wird weiterhin nur
                            # beim Frontend-Start aufgebaut (self.stream
                            # in __init__) - Menue-Beschriftung weist
                            # deshalb ausdruecklich auf "wirkt nach
                            # Neustart" hin, kein stiller Unterschied
                            # zum bisherigen externen Scripts/
                            # Frontend_Stream_Toggle.sh.
                            toggle_stream_overlay()
                            self._refresh_system_category()
                        elif kind == "screen_mirror":
                            # NEUES FEATURE (Nutzerwunsch: "CRT und HDMI
                            # koennen nicht gleichzeitig laufen - waere
                            # es machbar, den Bildschirminhalt trotzdem
                            # per Stream-Overlay sichtbar zu machen?
                            # Und das unter System an/aus schaltbar
                            # machen?") - toggelt nur die Freigabe-Datei,
                            # der eigentliche periodische Push (siehe
                            # _publish_screen_mirror_loop()) wird
                            # ebenfalls nur beim Frontend-Start
                            # aufgebaut - wirkt also, wie beim Stream-
                            # Overlay selbst, erst nach einem Neustart.
                            toggle_screen_mirror()
                            self._refresh_system_category()
                        elif kind == "update_check":
                            toggle_update_check()
                            self._refresh_system_category()
                        elif kind == "top10_time":
                            self.draw_top10_screen("seconds")
                            self.draw()
                        elif kind == "top10_launches":
                            self.draw_top10_screen("launches")
                            self.draw()
                        elif kind == "milestones":
                            self.draw_milestones_screen()
                            self.draw()
                        elif kind == "trophy_room":
                            self.draw_trophy_room_screen()
                            self.draw()
                        elif kind == "year_review":
                            self.draw_year_review_screen()
                            self.draw()
                        elif kind == "diary":
                            self.draw_diary_screen()
                            self.draw()
                        elif kind == "help":
                            self.draw_help_screen()
                            self.draw()
                        elif kind == "setup_wizard":
                            self.run_setup_wizard()
                            self.draw()
                        elif kind == "wot_draw":
                            self.draw_wot_screen()
                            self.draw()
                        elif kind == "secrets":
                            self.draw_secrets_screen()
                            self.draw()
                        elif kind == "credits":
                            self.draw_credits_screen()
                            self.draw()
                        elif kind == "crt_test":
                            self.draw_crt_test_pattern_screen()
                            self.draw()
                        elif kind == "ra_status":
                            ra_user, _ra_key = load_ra_config()
                            if ra_user is None:
                                self.draw_ra_setup_screen()
                            else:
                                ra_data = fetch_ra_progress_bounded(timeout=5.0)
                                if ra_data is not None:
                                    self._ra_lookup = build_ra_lookup(ra_data)
                                    msg = t("ra_reload_done", len(self._ra_lookup))
                                else:
                                    msg = t("ra_reload_failed")
                                self._refresh_system_category()
                                self.draw(message=msg)
                                time.sleep(1.5)
                            self.draw()
                        elif kind == "ra_toggle":
                            # NEU (Nutzerwunsch: RetroAchievements aus
                            # dem System-Menue heraus an-/ausschalten,
                            # ohne die Zugangsdaten per SSH loeschen zu
                            # muessen) - siehe toggle_ra_enabled()/
                            # ra_enabled() in fe/retroachievements.py.
                            # Gleiches Muster wie die uebrigen kleinen
                            # Ein/Aus-Schalter hier (z.B. "sfx"/
                            # "fast_scroll") - nur die Beschriftung im
                            # System-Menue aktualisieren, kein Neustart
                            # noetig.
                            toggle_ra_enabled()
                            self._refresh_system_category()
                # Bei einem einzelnen hoch/runter-Schritt (kein Scrollen,
                # keine Seite/Kategorie gewechselt) reicht der leichte
                # Navigations-Zeichenpfad - deutlich billiger als die
                # komplette Seite neu aufzubauen (misst sich vor allem
                # beim Boxart-Panel bemerkbar: kein Cover-Neuladen fuer
                # unveraenderte Nachbarzeilen noetig). Deckt NICHT jeden
                # Fall ab (Scrollen, Ordnerwechsel, Zufallssprung usw.
                # bleiben beim vollen, bewaehrten Aufbau) - _draw_navigate_items()
                # gibt in diesen Faellen False zurueck und faellt selbst
                # auf den vollen draw() zurueck.
                #
                # BUGFIX (Nutzer-Rueckmeldung: der Cursor "ueberspringt"
                # beim Scrollen gelegentlich etwas): move_step > 1
                # (Turbo-Sprung beim gehaltenen Hoch/Runter, siehe oben)
                # wurde hier bisher NICHT geprueft - die Bedingung liess
                # den leichten Pfad fuer JEDE hoch/runter-Aktion zu,
                # obwohl _draw_navigate_items() laut eigener Beschreibung
                # nur fuer EINEN Schritt ausgelegt ist. Bei einem
                # Turbo-Sprung (item_i springt z.B. um 4 oder 10 Position-
                # en) aktualisierte der leichte Pfad nur die unmittelbare
                # Umgebung der ALTEN und NEUEN Position, nicht die
                # dazwischenliegenden Zeilen - sichtbar als Cursor, der
                # scheinbar Zeilen ueberspringt/nicht sauber nachzieht.
                # Jetzt nur noch bei echtem Einzelschritt (move_step==1)
                # versucht, sonst korrekt der volle, immer richtige Aufbau.
                if (act in ("up", "down") and move_step == 1 and self.page == 1
                        and pre_page == 1 and not self.confirm_quit
                        and not self.confirm_update
                        and self._draw_navigate_items(pre_item_i)):
                    continue
                # ERWEITERUNG (Nutzer-Rueckmeldung: "im Hauptmenü wenn ich
                # schnell scrolle macht das Zeilensprünge und lagt etwas"):
                # dasselbe Prinzip wie direkt oberhalb, jetzt auch fuer Seite
                # 0 (Kategorien-Hauptmenue) - bisher gab es dafuer ueberhaupt
                # keinen leichten Pfad, jeder Einzelschritt loeste den vollen
                # draw_page_cats()-Aufbau aus. Siehe _draw_navigate_cats()
                # fuer die ausfuehrliche Begruendung.
                if (act in ("up", "down") and move_step == 1 and self.page == 0
                        and pre_page == 0 and not self.confirm_quit
                        and not self.confirm_update
                        and self._draw_navigate_cats(pre_cat_i)):
                    continue
                self.draw()
        finally:
            if self.stream:
                self.stream.stop()
            self.music.shutdown()
            self.set_cursor_blink(True)
            self.fb.clear((0, 0, 0))
            self.fb.flip()
            self.fb.close()
            # zurueck ins normale MiSTer-Menue
            LOG("Exit: gebe Eingaben frei, injiziere F12")
            self.inp.grab(False)
            time.sleep(0.2)
            try:
                self.inp.inject(KEY_F12)
            except OSError as e:
                LOG("Exit-Injection fehlgeschlagen: %s" % e)
            self.inp.close()
            LOG("Exit: fertig")

def _handle_sigterm(signum, frame):
    """kill sendet standardmaessig SIGTERM - Python fuehrt dabei OHNE
    diesen Handler KEINE finally-Bloecke aus, das Aufraeumen in
    Frontend.run() (Bildschirm loeschen, Eingaben freigeben, zurueck
    ins MiSTer-Menue per F12) wuerde also nie laufen und der Bildschirm
    bliebe eingefroren im letzten Frontend-Zustand haengen - genau das
    Verhalten, das Frontend_Update.sh/Frontend_Install_Remote.sh beim Neustarten einer
    laufenden Instanz ausgeloest hat. SystemExit sorgt dafuer, dass die
    bestehenden try/finally-Bloecke ganz normal durchlaufen werden."""
    LOG("Signal %d empfangen - fahre sauber herunter" % signum)
    raise SystemExit(0)

signal.signal(signal.SIGTERM, _handle_sigterm)
try:
    # SIGHUP: wird geschickt, wenn die kontrollierende SSH-Sitzung
    # getrennt wird, WAEHREND das Frontend manuell im Vordergrund laeuft
    # (genau der in der README empfohlene Testweg: "python3 frontend.py"
    # direkt per SSH, ohne es in den Hintergrund zu legen). Ohne diesen
    # Handler traf das Frontend derselbe Fehler wie bei SIGTERM vor
    # v1.37 - Bildschirm bleibt eingefroren, kein Aufraeumen. Nutzt
    # denselben, bereits getesteten Handler wie SIGTERM.
    signal.signal(signal.SIGHUP, _handle_sigterm)
except (AttributeError, ValueError, OSError):
    pass   # SIGHUP nicht verfuegbar (z.B. andere Plattform) - kein Problem

if __name__ == "__main__":
    # BUGFIX (Nutzer-Rueckmeldung, uebernommen aus einem Community-
    # Patch): startet man das Frontend manuell per SSH, waehrend
    # bereits eine Instanz laeuft (z.B. durch Autostart), beendete es
    # sich bisher KOMPLETT LAUTLOS ueber sys.exit(0) - der Abbruchgrund
    # stand nur in der Log-Datei, nicht auf der Konsole. Das wirkt wie
    # ein lautloser Absturz/Nichtstun, obwohl es die korrekte
    # Schutzfunktion gegen zwei gleichzeitig um Framebuffer/Eingaben
    # konkurrierende Instanzen ist. Jetzt gibt jede Startphase eine
    # sichtbare Meldung aus, und der Sperr-Fall zeigt direkt einen
    # fertigen Befehl zum Beenden der alten Instanz.
    print("Frontend-Start: initialisiere ...")
    # Systemuhr per NTP synchronisieren - MiSTer hat keine batterie-
    # gepufferte Echtzeituhr, ohne das waeren Log-Zeitstempel und die
    # Uhrzeit im Hauptmenue zunaechst falsch (siehe v1.70).
    #
    # NUTZERWUNSCH (schnellerer Start): laeuft seit v1.98 komplett im
    # Hintergrund (blocking=False) - der Start wartet NICHT mehr
    # darauf, das Menue erscheint dadurch schneller. Betrifft nur die
    # allerersten Log-Zeilen/die Uhrzeitanzeige, die fuer die paar
    # Sekunden bis der Hintergrund-Thread fertig ist, noch nicht
    # korrekt sein koennten - kein Stabilitaetsrisiko: der bestehende
    # RA-Neuversuch-Mechanismus (Frontend._maybe_retry_ra()) faengt
    # den Fall "Uhr war beim allerersten RA-Abruf noch nicht fertig"
    # bereits ab, genau wie vorher schon bei einem regulaeren Timeout.
    try:
        sync_system_clock_from_ntp(blocking=False)
    except Exception:
        print("WARNUNG: NTP-Zeitsync fehlgeschlagen (nicht kritisch):")
        traceback.print_exc()
    LOG("==== Frontend-Start ====")
    print("Log-Datei: %s (dort stehen alle weiteren Details)" % LOGFILE)
    try:
        _ensure_sfx_files()   # Sound-WAVs einmalig erzeugen, falls noch nicht vorhanden
    except Exception:
        print("WARNUNG: Sound-Dateien konnten nicht erzeugt werden (nicht kritisch):")
        traceback.print_exc()
    # Nutzeroption fuer NAS-Nutzer (Standard AUS, siehe network_wait_
    # enabled()): erst weiter, wenn Netzwerk + ROM-Ordner-Inhalt stabil
    # sind - sonst koennte beim Booten eine noch nicht fertig
    # eingehaengte Netzwerkfreigabe zu einer leeren/unvollstaendigen,
    # dauerhaft gecachten Spieleliste fuehren. Bewusst NUR aktiv, wenn
    # explizit eingeschaltet - fuer SD-Karte/USB (die meisten Faelle)
    # keinerlei zusaetzliche Wartezeit.
    if network_wait_enabled():
        print("Netzwerk-Warteoption aktiv: warte auf Verbindung + stabilen ROM-Ordner ...")
        try:
            _wait_for_network_ready()
        except Exception:
            print("WARNUNG: Netzwerk-Wartelogik fehlgeschlagen (nicht kritisch):")
            traceback.print_exc()
    if not acquire_single_instance():
        try:
            with open(LOCKFILE) as f:
                old_pid = f.read().strip()
        except OSError:
            old_pid = "?"
        print("")
        print("Abbruch: Es laeuft bereits eine Instanz des Frontends (PID %s)." % old_pid)
        print("Das ist wahrscheinlich der Grund, warum \"nichts passiert\" -")
        print("das Frontend laeuft schon (z.B. per Autostart beim Booten)")
        print("und blockiert auf dem Framebuffer/den Eingabegeraeten.")
        print("Falls das NICHT stimmen sollte (verwaiste Lock-Datei):")
        print("  kill %s ; rm -f %s" % (old_pid, LOCKFILE))
        sys.exit(0)
    print("Keine andere Instanz aktiv - starte Framebuffer/Eingaben ...")
    # DIAGNOSE (Nutzerfrage: "koennte man den Bootvorgang noch etwas
    # beschleunigen?") - bisher gab es keine Messung, WIE LANGE der
    # eigentliche Start (Framebuffer/Eingaben oeffnen, RA-Abruf anstossen,
    # Spieleliste einlesen - alles, was in Frontend() passiert, BEVOR
    # das Kategorien-Menue zum ersten Mal gezeichnet wird) auf echter
    # Hardware tatsaechlich dauert - jede weitere Optimierung waere ohne
    # diese Zahl nur Raten. Jetzt einmalig pro Start geloggt.
    _t_boot = time.monotonic()
    try:
        _fe = Frontend()
        LOG("Start-Dauer bis Kategorien-Menue bereit: %.2fs"
            % (time.monotonic() - _t_boot))
        _fe.run()
    except Exception:
        LOG("CRASH:\n" + traceback.format_exc())
        print("")
        print("ABSTURZ - Details siehe oben und in %s" % LOGFILE)
        raise
    finally:
        release_single_instance()
