#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MiSTer Custom Frontend - v4.2
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

import os, sys, mmap, struct, fcntl, time, re, glob, subprocess, traceback, zlib, json, random, math, signal, socket, threading

# EINZIGE QUELLE DER WAHRHEIT fuer die Versionsnummer (Vereinbarung,
# da mehrere Leute an derselben Codebasis arbeiten - siehe Nutzer-
# Vorgabe zur Versionierung). Muss mit dem Header-Kommentar oben,
# README, CHANGELOG und der VERSION-Datei (frontend/VERSION)
# UEBEREINSTIMMEN. Wird NUR bei einem ausdruecklich angewiesenen
# Release-Bump geaendert - niemals von sich aus hochgezaehlt, auch
# nicht bei Zwischenstaenden/Diagnose-Builds/Bugfix-Versuchen (die
# bekommen hoechstens einen Zusatz wie "4.2-test3", nie eine neue
# Nummer hier).
FRONTEND_VERSION = "4.2"

LOGFILE = "/tmp/frontend.log"
LOG_MAX_BYTES = 512 * 1024      # ab dieser Groesse wird gekuerzt
LOG_KEEP_BYTES = 256 * 1024     # so viel vom Ende bleibt erhalten
_log_call_count = 0

def _trim_log_if_needed():
    """Log-Datei kuerzen, falls sie zu gross geworden ist - behaelt nur
    das juengste Ende. Wird nicht bei jedem LOG()-Aufruf geprueft
    (Dateigroesse abfragen kostet Zeit), sondern nur gelegentlich -
    das Log waechst nicht so schnell, dass es dazwischen aus dem
    Ruder laeuft."""
    try:
        size = os.path.getsize(LOGFILE)
    except OSError:
        return
    if size <= LOG_MAX_BYTES:
        return
    try:
        with open(LOGFILE, "rb") as f:
            f.seek(-LOG_KEEP_BYTES, os.SEEK_END)
            tail = f.read()
        # Am ersten Zeilenumbruch abschneiden, damit keine abgeschnittene
        # Zeile am Anfang des gekuerzten Logs steht.
        nl = tail.find(b"\n")
        if nl >= 0:
            tail = tail[nl + 1:]
        with open(LOGFILE, "wb") as f:
            f.write(("--- Log gekuerzt (war > %d KB) ---\n"
                     % (LOG_MAX_BYTES // 1024)).encode())
            f.write(tail)
    except OSError:
        pass

def LOG(msg):
    global _log_call_count
    try:
        _log_call_count += 1
        if _log_call_count % 50 == 0:
            _trim_log_if_needed()
        with open(LOGFILE, "a") as f:
            f.write("%s  %s\n" % (time.strftime("%H:%M:%S"), msg))
    except OSError:
        pass

# ----------------------------------------------------------------------------
# SINGLE-INSTANCE-LOCK
# Verhindert, dass zwei Instanzen gleichzeitig /dev/fb0 mappen und die
# Eingabegeraete grabben. Die Lock-Datei enthaelt die PID, damit sie -
# wie in der README beschrieben - per "kill $(cat /tmp/frontend.lock)"
# beendet werden kann. pkill/pgrep gibt es auf dem MiSTer nicht.
# ----------------------------------------------------------------------------

LOCKFILE = "/tmp/frontend.lock"

def _pid_alive(pid):
    """True, wenn die PID existiert UND es sich nachweislich um unseren
    eigenen frontend.py-Prozess handelt - nicht nur irgendeinen
    Prozess, der zufaellig dieselbe Nummer hat.

    BUGFIX (Nutzer-Rueckmeldung: nach einem "Soft Reset" - vermutlich
    OHNE echten Linux-Kernel-Neustart, im Gegensatz zu einem echten
    Stromzyklus - kommt das Frontend manchmal nicht wieder, MiSTer
    bleibt im eigenen OSD haengen, OHNE jede Log-Zeile): reine "existiert
    die PID"-Pruefung (os.kill(pid, 0)) reicht nicht aus, wenn /tmp
    (und damit unsere Lock-Datei) einen Soft-Reset UEBERLEBT - Linux
    vergibt PID-Nummern nach einer Weile wieder neu, ein voellig
    unabhaengiger, neuer Prozess koennte zufaellig dieselbe Nummer wie
    der alte (laengst beendete) Frontend-Prozess bekommen haben. Die
    Sperrdatei-Pruefung haette das dann faelschlicherweise als "laeuft
    noch" gewertet und den Neustart stillschweigend verweigert - kein
    Absturz, keine Logzeile, einfach nichts (passt zum gemeldeten Bild).
    Fix: zusaetzlich pruefen, ob /proc/<pid>/cmdline tatsaechlich
    "frontend.py" enthaelt. Ist /proc nicht lesbar (sollte auf MiSTer
    nicht vorkommen), faellt die Funktion sicherheitshalber auf das
    alte Verhalten zurueck (PID existiert -> als lebendig werten),
    statt einen falschen Negativ-Befund zu riskieren."""
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    try:
        with open("/proc/%d/cmdline" % pid, "rb") as f:
            cmdline = f.read()
    except OSError:
        return True   # /proc nicht lesbar - alte, vorsichtige Annahme beibehalten
    return b"frontend.py" in cmdline

def acquire_single_instance():
    """True, wenn wir die einzige Instanz sind (Lock gesetzt). False,
    wenn bereits eine LEBENDE Instanz laeuft. Eine verwaiste Lock-Datei
    (Prozess existiert nicht mehr, z.B. nach Absturz) wird uebernommen."""
    try:
        with open(LOCKFILE) as f:
            old = f.read().strip()
        if old.isdigit() and _pid_alive(int(old)):
            LOG("Bereits aktive Instanz (PID %s) - Abbruch." % old)
            return False
    except OSError:
        pass
    try:
        with open(LOCKFILE, "w") as f:
            f.write(str(os.getpid()))
    except OSError as e:
        LOG("Lock-Datei nicht schreibbar: %s" % e)
    return True

def release_single_instance():
    try:
        with open(LOCKFILE) as f:
            mine = f.read().strip() == str(os.getpid())
        if mine:
            os.remove(LOCKFILE)
    except OSError:
        pass

# ----------------------------------------------------------------------------
# KONFIGURATION
# ----------------------------------------------------------------------------

BASE        = "/media/fat"
SCRIPTS_DIR = "/media/fat/Scripts"

def _discover_games_bases():
    """Alle Orte, an denen ROMs liegen koennen (SD + USB-Laufwerke).

    BUGFIX (Nutzer-Rueckmeldung: "Spiele ausser von /media/fat/games
    werden nicht angezeigt"): die feste Liste deckte nur usb0 bis
    usb5 ab - Speicherorte ausserhalb dieses festen Musters (z.B. ein
    Netzlaufwerk unter einem anderen Namen, oder ein USB-Geraet mit
    hoeherer Nummer) wurden dadurch nie gefunden, komplett unabhaengig
    davon, was tatsaechlich am MiSTer angeschlossen ist. Jetzt
    zusaetzlich dynamisch: alles, was tatsaechlich unter /media
    eingehaengt ist (ausser "fat" selbst, das schon feststeht), wird
    automatisch mit aufgenommen - deckt damit auch Faelle ab, die die
    feste Liste nicht vorgesehen hatte. Die urspruengliche feste Liste
    bleibt zusaetzlich bestehen (Vorhersagbarkeit/Ruecksichtigung auf
    den ueblichen Fall, auch wenn /media aus irgendeinem Grund gerade
    nicht lesbar sein sollte)."""
    bases = ["/media/fat/games"]
    bases += ["/media/usb%d/games" % i for i in range(6)]
    bases += ["/media/usb%d" % i for i in range(6)]
    try:
        for entry in sorted(os.listdir("/media")):
            if entry == "fat":
                continue   # schon oben abgedeckt
            path = "/media/" + entry
            if not os.path.isdir(path):
                continue
            games_sub = os.path.join(path, "games")
            if games_sub not in bases:
                bases.append(games_sub)
            if path not in bases:
                bases.append(path)
    except OSError:
        pass   # /media nicht lesbar - bei der festen Liste bleiben
    return bases

# Bewusst als Funktionsergebnis statt als literale Liste - siehe
# _discover_games_bases() oben fuer die Begruendung (dynamische
# Erkennung zusaetzlich zur festen Liste).
GAMES_BASES = _discover_games_bases()
ART_BASE    = "/media/fat/frontend/art"
ART_HD      = "/media/fat/frontend/art_hd"

# --- Stream-Overlay (optional, siehe stream_server.py) -----------------
STREAM_ENABLED_FILE = "/media/fat/frontend/stream_enabled"
STREAM_CONFIG_FILE  = "/media/fat/frontend/stream_config.json"
STREAM_PORT = 8080

try:
    from stream_server import StreamServer
except Exception:
    StreamServer = None
BG_BASE     = "/media/fat/frontend/bg"
SYSART_BASE = "/media/fat/frontend/sysart"
META_BASE   = "/media/fat/frontend/meta"
MGL_TMP     = "/tmp/frontend_launch.mgl"
GAMES_CACHE = "/media/fat/frontend/games_cache.json"
RECENT_FILE = "/media/fat/frontend/recently_played.json"
RECENT_MAX = 15
FAVORITES_FILE = "/media/fat/frontend/favorites.json"
LAST_CORE_CHOICE_FILE = "/media/fat/frontend/last_core_choice.json"
PLAYTIME_FILE = "/media/fat/frontend/playtime.json"
COMPLETED_FILE = "/media/fat/frontend/completed.json"

def _load_completed_raw():
    """Menge der als 'durchgespielt' markierten Spiele (per Name,
    gleiche Konvention wie Favoriten/Zuletzt gespielt)."""
    try:
        with open(COMPLETED_FILE) as f:
            data = json.load(f)
            return set(data) if isinstance(data, list) else set()
    except (OSError, ValueError):
        return set()

def toggle_completed(label):
    """Durchgespielt-Status umschalten. Rueckgabe: True, wenn jetzt
    als durchgespielt markiert, sonst False."""
    if not label:
        return False
    data = _load_completed_raw()
    if label in data:
        data.discard(label)
        now_completed = False
    else:
        data.add(label)
        now_completed = True
    try:
        os.makedirs(os.path.dirname(COMPLETED_FILE), exist_ok=True)
        with open(COMPLETED_FILE, "w") as f:
            json.dump(sorted(data), f)
    except OSError:
        pass
    return now_completed

# ----------------------------------------------------------------------------
# RETROACHIEVEMENTS (optional - komplett unsichtbar, solange nicht
# eingerichtet)
#
# Einrichtung per SSH/Texteditor (keine Bildschirmtastatur im Frontend -
# ein API-Schluessel waere per Steuerkreuz kaum eintippbar): Datei mit
# zwei Zeilen, erste der RA-Benutzername, zweite der Web-API-Schluessel
# (aus dem eigenen RA-Kontrollbereich, Abschnitt "Keys").
RA_CONFIG_FILE = "/media/fat/frontend/retroachievements.cfg"

def load_ra_config():
    """Liest Benutzername + API-Schluessel aus RA_CONFIG_FILE. Liefert
    (benutzername, schluessel) oder (None, None), wenn die Datei fehlt,
    leer ist oder nicht mindestens zwei nicht-leere Zeilen enthaelt -
    JEDER Fehlerfall wird als "nicht eingerichtet" behandelt, nie als
    Absturz. Das ist bewusst die EINZIGE Stelle, die entscheidet, ob
    RetroAchievements ueberhaupt aktiv ist - alle anderen RA-Funktionen
    bauen darauf auf."""
    try:
        with open(RA_CONFIG_FILE) as f:
            lines = [ln.strip() for ln in f.readlines()]
    except OSError:
        return None, None
    lines = [ln for ln in lines if ln]   # leere Zeilen ueberspringen
    if len(lines) < 2:
        return None, None
    return lines[0], lines[1]

def ra_enabled():
    """Kurzform: ist RetroAchievements ueberhaupt eingerichtet?"""
    u, k = load_ra_config()
    return u is not None and k is not None

RA_API_URL = "https://retroachievements.org/API/API_GetUserCompletionProgress.php"

def fetch_ra_progress(username, api_key, timeout=5.0):
    """Fragt bei RetroAchievements die komplette Fortschrittsliste des
    Nutzers ab (ein Aufruf fuer ALLE Spiele, mit denen er je zu tun
    hatte). Liefert eine Liste von (titel, systemname, erreicht,
    moeglich)-Tupeln, oder None bei JEDEM Fehler (kein Internet,
    falscher Schluessel, Zeitueberschreitung, unerwartete Antwort) -
    NIE eine Ausnahme nach aussen, das ruft aus einem Hintergrund-
    Thread heraus auf (siehe Schritt 3) und darf den Rest des
    Frontends unter keinen Umstaenden beeintraechtigen.

    EHRLICHER HINWEIS: die genauen Feldnamen der Antwort sind anhand
    der oeffentlichen RA-API-Dokumentation nachgebaut, aber NICHT gegen
    den echten Server verifiziert (in dieser Umgebung nicht moeglich).
    Deshalb werden mehrere plausible Feldnamen-Varianten akzeptiert und
    JEDES fehlende/anders benannte Feld fuehrt zu einem stillen
    Auslassen dieses EINEN Eintrags statt einem Abbruch - falls sich
    beim ersten echten Test ein Feldname als falsch herausstellt,
    liefert die Funktion einfach eine leere oder unvollstaendige Liste
    statt abzustuerzen."""
    try:
        params = urllib.parse.urlencode({"u": username, "y": api_key})
        url = RA_API_URL + "?" + params
        req = urllib.request.Request(url, headers={"User-Agent": "MiSTerFrontend/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                LOG("fetch_ra_progress: HTTP-Status %d" % resp.status)
                return None
            raw = resp.read()
        data = json.loads(raw)
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as e:
        LOG("fetch_ra_progress: fehlgeschlagen: %s" % e)
        return None

    # Die Ergebnisliste kann je nach Antwortform direkt eine Liste sein
    # ODER unter einem Schluessel wie "Results" liegen - beides
    # abdecken.
    if isinstance(data, dict):
        entries = data.get("Results") or data.get("results") or []
    elif isinstance(data, list):
        entries = data
    else:
        entries = []

    out = []
    for e in entries:
        if not isinstance(e, dict):
            continue
        title = e.get("Title") or e.get("title")
        system = e.get("ConsoleName") or e.get("consoleName") or e.get("console")
        total = e.get("MaxPossible") or e.get("maxPossible") or e.get("NumAchievements")
        earned = e.get("NumAwarded") or e.get("numAwarded") or e.get("NumAwardedHardcore")
        game_id = e.get("GameID") or e.get("gameId") or e.get("ID")
        if not title or not total:
            continue   # Eintrag ohne verwertbare Kernangaben - auslassen statt raten
        try:
            total = int(total)
            earned = int(earned) if earned is not None else 0
            game_id = int(game_id) if game_id is not None else None
        except (TypeError, ValueError):
            continue
        if total <= 0:
            continue
        out.append((str(title), str(system) if system else "", earned, total, game_id))
    return out

def fetch_ra_progress_bounded(timeout=5.0):
    """Holt die RA-Fortschrittsliste, FALLS eingerichtet und ein
    lokales Netzwerk vorhanden ist - in einem separaten Thread mit
    hartem Zeitlimit, exakt dasselbe Prinzip wie
    sync_system_clock_from_ntp() (siehe dort fuer die Begruendung:
    haengende DNS-Aufloesung wird von urlopen()s eigenem timeout NICHT
    zuverlaessig erfasst). Liefert None, wenn nicht eingerichtet, kein
    Netzwerk vorhanden ist, oder die Abfrage fehlschlaegt/zu lange
    braucht - NIE eine Ausnahme, NIE eine Verzoegerung ueber `timeout`
    Sekunden hinaus."""
    username, api_key = load_ra_config()
    if username is None:
        return None
    if not _has_network():
        return None
    result = {"data": None}
    def worker():
        result["data"] = fetch_ra_progress(username, api_key, timeout=timeout)
    th = threading.Thread(target=worker, daemon=True)
    th.start()
    th.join(timeout=timeout + 0.5)
    return result["data"]

# ----------------------------------------------------------------------------
# EINZELNE ERFOLGSLISTE EINES SPIELS (Nutzerwunsch: "Trophaeen-Vitrine")
#
# Bewusst als EIGENSTAENDIGE, separate Funktion aufgebaut - nutzt zwar
# dieselben Grundbausteine (load_ra_config(), _has_network(), dasselbe
# Zeitlimit-Prinzip) wie die bestehende Fortschrittsabfrage, aendert
# aber NICHTS an ihr. Ruft einen ANDEREN RA-Endpunkt auf (Erfolgsdetails
# zu EINEM Spiel statt der Sammelliste ueber alle Spiele).
RA_GAME_API_URL = "https://retroachievements.org/API/API_GetGameInfoAndUserProgress.php"

def fetch_ra_game_achievements(game_id, timeout=5.0):
    """Fragt bei RetroAchievements die komplette Erfolgsliste EINES
    Spiels ab (Name, Beschreibung, Punkte, Badge-Name, freigeschaltet/
    wann). Liefert eine Liste von (titel, beschreibung, punkte,
    badge_name, freigeschaltet, datum)-Tupeln, sortiert nach RAs
    eigener Anzeigereihenfolge, oder None bei JEDEM Fehler - NIE eine
    Ausnahme nach aussen.

    EHRLICHER HINWEIS: wie bei fetch_ra_progress() sind die genauen
    Feldnamen anhand der oeffentlichen API-Dokumentation nachgebaut,
    nicht gegen den echten Server verifiziert. Mehrere plausible
    Feldnamen-Varianten werden akzeptiert, ein einzelner fehlerhafter
    Erfolgs-Eintrag wird stillschweigend ausgelassen statt die ganze
    Liste abzubrechen."""
    username, api_key = load_ra_config()
    if username is None:
        return None
    try:
        params = urllib.parse.urlencode({"u": username, "y": api_key, "g": game_id})
        url = RA_GAME_API_URL + "?" + params
        req = urllib.request.Request(url, headers={"User-Agent": "MiSTerFrontend/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                LOG("fetch_ra_game_achievements: HTTP-Status %d" % resp.status)
                return None
            raw = resp.read()
        data = json.loads(raw)
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as e:
        LOG("fetch_ra_game_achievements: fehlgeschlagen: %s" % e)
        return None
    if not isinstance(data, dict):
        return None
    achievements = data.get("Achievements") or data.get("achievements")
    if not isinstance(achievements, dict):
        return None

    out = []
    for ach in achievements.values():
        if not isinstance(ach, dict):
            continue
        title = ach.get("Title") or ach.get("title")
        desc = ach.get("Description") or ach.get("description") or ""
        points = ach.get("Points") or ach.get("points")
        badge = ach.get("BadgeName") or ach.get("badgeName")
        order = ach.get("DisplayOrder") or ach.get("displayOrder") or 0
        date_earned = (ach.get("DateEarned") or ach.get("dateEarned")
                       or ach.get("DateEarnedHardcore") or ach.get("dateEarnedHardcore"))
        if not title:
            continue
        try:
            points = int(points) if points is not None else 0
            order = int(order) if order is not None else 0
        except (TypeError, ValueError):
            points, order = 0, 0
        out.append((str(title), str(desc), points, str(badge) if badge else None,
                    bool(date_earned), str(date_earned) if date_earned else None, order))
    out.sort(key=lambda a: a[6])   # RAs eigene Anzeigereihenfolge
    return [a[:6] for a in out]

def fetch_ra_game_achievements_bounded(game_id, timeout=5.0):
    """Wie fetch_ra_game_achievements(), aber zeitlich hart begrenzt in
    einem separaten Thread - exakt dasselbe Prinzip wie
    fetch_ra_progress_bounded() (siehe dort fuer die Begruendung)."""
    if not _has_network():
        return None
    result = {"data": None}
    def worker():
        result["data"] = fetch_ra_game_achievements(game_id, timeout=timeout)
    th = threading.Thread(target=worker, daemon=True)
    th.start()
    th.join(timeout=timeout + 0.5)
    return result["data"]

# BUGFIX/NEUES FEATURE (Nutzerwunsch: F6-Erfolgsliste dauert "ganz
# schoen" lang, laesst sich das speichern/beschleunigen?): bisher
# holte draw_ra_showcase_screen() die komplette Erfolgsliste bei
# JEDEM Aufruf frisch aus dem Netz (bis zu 5s Zeitlimit), auch wenn
# man kurz zuvor schon dasselbe Spiel angesehen hatte - kein eigener
# Cache in der ersten Fassung (siehe damaliger Kommentar: "kann
# spaeter ergaenzt werden, sobald sich das Format in der Praxis
# bewaehrt hat" - hat es jetzt). Kurzlebiger, dateibasierter Cache
# (15 Minuten) nach demselben Prinzip wie BadgeCache/ArtCache: kurz
# genug, dass frisch verdiente Erfolge zeitnah als "freigeschaltet"
# auftauchen, lang genug, um wiederholtes Ansehen desselben Spiels
# (z.B. waehrend einer Session mehrfach F6 druecken) spuerbar zu
# beschleunigen.
RA_ACHIEVEMENTS_CACHE_FILE = "/media/fat/frontend/ra_achievements_cache.json"
RA_ACHIEVEMENTS_CACHE_TTL = 900   # 15 Minuten

def _load_ra_achievements_cache():
    try:
        with open(RA_ACHIEVEMENTS_CACHE_FILE) as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}

def _save_ra_achievements_cache(cache):
    try:
        os.makedirs(os.path.dirname(RA_ACHIEVEMENTS_CACHE_FILE), exist_ok=True)
        with open(RA_ACHIEVEMENTS_CACHE_FILE, "w") as f:
            json.dump(cache, f)
    except OSError:
        pass

# NEUES FEATURE (Nutzerwunsch: F6-Erfolgsvitrine soll "schneller
# einblenden" - bisher blockierte draw_ra_showcase_screen() bei
# abgelaufenem/fehlendem Cache-Eintrag bis zu 5s auf den Netzwerkabruf,
# bevor ueberhaupt eine Erfolgsliste zu sehen war): Stale-while-
# revalidate - IST bereits ein (auch veralteter) Cache-Eintrag da,
# wird der SOFORT zurueckgegeben (kein Warten), waehrend im
# Hintergrund-Thread ein frischer Abruf angestossen wird, der den
# Cache fuer den NAECHSTEN F6-Aufruf desselben Spiels aktualisiert.
# Nur beim ALLERERSTEN Ansehen eines Spiels (noch gar kein Cache-
# Eintrag vorhanden) bleibt ein einmaliger, kurzer synchroner Abruf
# noetig - da gibt es schlicht noch nichts Vorhandenes zum Anzeigen.
# _ra_achievements_refresh_inflight verhindert parallele Mehrfach-
# abrufe fuer dasselbe Spiel bei schnell wiederholtem F6-Druecken.
_ra_achievements_refresh_inflight = set()
_ra_achievements_refresh_lock = threading.Lock()

def _refresh_ra_achievements_background(game_id, timeout=5.0):
    key = str(game_id)
    with _ra_achievements_refresh_lock:
        if key in _ra_achievements_refresh_inflight:
            return
        _ra_achievements_refresh_inflight.add(key)
    try:
        data = fetch_ra_game_achievements_bounded(game_id, timeout=timeout)
        if data is not None:
            cache = _load_ra_achievements_cache()
            cache[key] = {"ts": time.time(), "data": data}
            _save_ra_achievements_cache(cache)
    finally:
        with _ra_achievements_refresh_lock:
            _ra_achievements_refresh_inflight.discard(key)

def fetch_ra_game_achievements_cached(game_id, timeout=5.0):
    """Wie fetch_ra_game_achievements_bounded(), aber mit kurzlebigem
    Cache nach dem Stale-while-revalidate-Prinzip (siehe Kommentar
    oben): ein VORHANDENER Cache-Eintrag wird IMMER sofort
    zurueckgegeben, auch wenn er aelter als RA_ACHIEVEMENTS_CACHE_TTL
    ist - in dem Fall wird zusaetzlich, nicht-blockierend, ein
    Hintergrund-Abruf gestartet, der den Cache fuer naechstes Mal
    aktualisiert. Nur wenn NOCH GAR NICHTS im Cache steht (allererster
    Blick auf dieses Spiel), erfolgt ein einmaliger synchroner Abruf."""
    cache = _load_ra_achievements_cache()
    key = str(game_id)
    entry = cache.get(key)
    now = time.time()
    if entry:
        if (now - entry.get("ts", 0)) >= RA_ACHIEVEMENTS_CACHE_TTL:
            threading.Thread(
                target=_refresh_ra_achievements_background,
                args=(game_id,), kwargs={"timeout": timeout},
                daemon=True).start()
        return entry.get("data")
    data = fetch_ra_game_achievements_bounded(game_id, timeout=timeout)
    if data is not None:
        cache[key] = {"ts": now, "data": data}
        _save_ra_achievements_cache(cache)
    return data

# ----------------------------------------------------------------------------
# NAMENS-/SYSTEM-ABGLEICH
#
# RA liefert Spieltitel + Systemnamen, keine Dateipfade - der Abgleich
# mit unserer Bibliothek laeuft ueber einen NORMALISIERTEN Namen
# (Region-/Versionsangaben, Satzzeichen, Gross-/Kleinschreibung werden
# ignoriert), zusaetzlich ueber das System abgesichert. Bewusst
# KONSERVATIV: fehlt fuer unser System eine bekannte RA-Entsprechung,
# wird lieber GAR NICHTS angezeigt als ein potenziell falscher Treffer.
def _ra_normalize_name(name):
    """Normalisiert einen Titel fuer den Abgleich."""
    n = name.lower()
    n = re.sub(r"\([^)]*\)", " ", n)    # (USA), (Europe), (Rev 1) usw.
    n = re.sub(r"\[[^\]]*\]", " ", n)   # [T-En] usw.
    n = re.sub(r"[^a-z0-9 ]", " ", n)   # Satzzeichen -> Leerzeichen
    n = re.sub(r"\s+", " ", n).strip()
    return n

# Bekannte Entsprechungen unserer Systemschluessel zu RA-Konsolennamen.
# BUGFIX (Nutzer-Rueckmeldung, zweite Runde: RA-Fortschritt fehlte bei
# NES/SNES und weiteren Systemen, obwohl dort laengst Achievements
# gesammelt wurden): per Recherche gegen echte RA-API-Beispiele
# bestaetigt, dass RA fuer manche Systeme LAENGERE, kombinierte Namen
# verwendet als hier eingetragen - z.B. "SNES/Super Famicom" statt
# nur "SNES", "Mega Drive" statt "Genesis Mega Drive". Der bisherige
# EXAKTE Abgleich (voller String muss 1:1 passen) schlug dadurch fuer
# genau diese Systeme IMMER fehl, obwohl die Kernbezeichnung eigentlich
# passte. Fix: siehe _ra_console_matches() weiter unten - prueft jetzt,
# ob unsere erwartete Bezeichnung als zusammenhaengende WORTFOLGE in
# RAs tatsaechlichem Namen vorkommt, nicht mehr per exaktem Vergleich.
#
# EHRLICHER HINWEIS bleibt bestehen: auch diese Kurzbezeichnungen sind
# anhand allgemeiner Kenntnis/einzelner API-Beispiele zusammengestellt,
# nicht vollstaendig gegen jedes einzelne System verifiziert - fehlt
# eine Zuordnung oder stimmt sie nicht, fuehrt das zu KEINER Anzeige
# fuer dieses System (sicherer Fehlerfall), nie zu einer falschen.
RA_CONSOLE_MAP = {
    "NES": "nes", "SNES": "snes", "Genesis": "mega drive",
    "GAMEBOY": "game boy", "GBC": "game boy color", "GBA": "game boy advance",
    "PSX": "playstation", "N64": "nintendo 64", "ARCADE": "arcade",
    "SMS": "master system", "TGFX16": "pc engine",
    "NEOGEO": "neo geo", "MegaCD": "sega cd", "Saturn": "saturn",
}

def _ra_console_matches(expected, ra_console_normalized):
    """Prueft, ob die erwartete (bereits normalisierte, ggf. mehrteilige)
    Systembezeichnung als ZUSAMMENHAENGENDE Wortfolge in RAs
    tatsaechlichem, normalisierten Konsolennamen vorkommt - z.B.
    "snes" in "snes super famicom" (Treffer), aber NICHT "nes" in
    "snes super famicom" (kein Treffer trotz Teilstring-Uebereinstimmung
    auf Zeichenebene) - reiner Wortgrenzen-Vergleich, sonst wuerde NES
    faelschlich jedes SNES-Spiel treffen."""
    exp_words = expected.split()
    ra_words = ra_console_normalized.split()
    n = len(exp_words)
    if n == 0 or n > len(ra_words):
        return False
    for i in range(len(ra_words) - n + 1):
        if ra_words[i:i + n] == exp_words:
            return True
    return False

def build_ra_lookup(ra_entries):
    """Baut aus der RA-Fortschrittsliste ein Nachschlage-Woerterbuch:
    normalisierter_titel -> Liste von (normalisiertes_system, erreicht,
    moeglich, game_id)-Tupeln. Mehrere Eintraege pro Titel sind normal
    (dasselbe Spiel kann auf mehreren Konsolen erschienen sein) - die
    eigentliche System-Auswahl passiert erst in lookup_ra_progress()."""
    lookup = {}
    for title, system, earned, total, game_id in ra_entries or []:
        key = _ra_normalize_name(title)
        lookup.setdefault(key, []).append(
            (_ra_normalize_name(system), earned, total, game_id))
    return lookup

def lookup_ra_progress(lookup, our_name, our_syskey):
    """Sucht den RA-Fortschritt fuer ein Spiel aus unserer Bibliothek.
    Liefert (erreicht, moeglich) oder None, wenn kein Treffer - auch
    wenn fuer our_syskey keine bekannte RA-Entsprechung existiert
    (bewusst KEIN Rateversuch). Bei mehreren zum System passenden
    Eintraegen (sollte selten vorkommen) gewinnt der mit den meisten
    erreichten Achievements.

    UNVERAENDERTE Rueckgabe (nur (erreicht, moeglich) oder None) trotz
    jetzt zusaetzlich gespeicherter GameID - keine bestehende
    Aufrufstelle soll sich anpassen muessen. Fuer die GameID selbst
    siehe die separate lookup_ra_game_id()."""
    best = _lookup_ra_candidate(lookup, our_name, our_syskey)
    return (best[0], best[1]) if best else None

def lookup_ra_game_id(lookup, our_name, our_syskey):
    """Wie lookup_ra_progress(), liefert aber die RA-GameID des
    Treffers (fuer die Erfolgsdetails, siehe fetch_ra_game_achievements())
    statt des Fortschritts - oder None, wenn kein Treffer oder keine
    GameID bekannt ist (z.B. bei aelteren zwischengespeicherten Daten
    ohne dieses Feld)."""
    best = _lookup_ra_candidate(lookup, our_name, our_syskey)
    return best[2] if best else None

def _lookup_ra_candidate(lookup, our_name, our_syskey):
    """Gemeinsamer Kern von lookup_ra_progress()/lookup_ra_game_id():
    liefert (erreicht, moeglich, game_id) des besten Treffers oder
    None."""
    expected = RA_CONSOLE_MAP.get(our_syskey)
    if not expected:
        return None
    candidates = lookup.get(_ra_normalize_name(our_name))
    if not candidates:
        return None
    best = None
    for ra_system, earned, total, game_id in candidates:
        if _ra_console_matches(expected, ra_system):
            if best is None or earned > best[0]:
                best = (earned, total, game_id)
    return best

def load_playtime():
    """Laedt die Spielzeit-/Start-Statistik. JEDER Eintrag wird auf das
    Format {"seconds": X, "launches": N, "syskey": S} normalisiert -
    frueher (v1.79/v1.80) fehlte "syskey" komplett bzw. war es nur
    eine reine Zahl ohne Start-Zaehler. Diese alten Eintraege werden
    beim Laden transparent umgewandelt (launches=0/syskey=None, da
    dafuer keine historischen Daten existieren), damit ein Update
    nicht die bisherige Spielzeit verwirft."""
    try:
        with open(PLAYTIME_FILE) as f:
            raw = json.load(f)
    except (OSError, ValueError):
        return {}
    data = {}
    for label, val in raw.items():
        if isinstance(val, dict):
            data[label] = {"seconds": val.get("seconds", 0),
                          "launches": val.get("launches", 0),
                          "syskey": val.get("syskey")}
        else:
            data[label] = {"seconds": val, "launches": 0, "syskey": None}
    return data

def record_playtime(label, seconds, syskey=None):
    """Addiert die gespielte Zeit (in Sekunden) UND zaehlt einen
    weiteren Start fuer dieses Spiel hoch (identifiziert ueber den
    Namen - gleiche Konvention wie record_recent()/Favoriten). Wird
    ganz am Ende von run_core() aufgerufen, NUR mit der Zeit vom
    bestaetigten Core-Start bis zur Rueckkehr ins Menue - Ladezeiten
    und fehlgeschlagene Starts zaehlen bewusst nicht mit (und werden
    dementsprechend auch nicht als Start gezaehlt - run_core() ruft
    diese Funktion nur bei einem TATSAECHLICH bestaetigten Start auf).
    syskey (optional, seit v1.89): fuers "Entdecker"-Achievement
    (verschiedene Systeme ausprobiert) - wird bei jedem Aufruf
    aktualisiert (falls mitgegeben), falls sich der Systemschluessel
    fuer denselben Namen mal aendern sollte."""
    if not label or seconds <= 0:
        return
    data = load_playtime()
    entry = data.get(label, {"seconds": 0, "launches": 0, "syskey": None})
    entry["seconds"] += seconds
    entry["launches"] += 1
    if syskey:
        entry["syskey"] = syskey
    data[label] = entry
    try:
        os.makedirs(os.path.dirname(PLAYTIME_FILE), exist_ok=True)
        with open(PLAYTIME_FILE, "w") as f:
            json.dump(data, f)
    except OSError:
        pass

# ----------------------------------------------------------------------------
# JAHRES-BUENDELUNG DER SPIELZEIT (Fundament fuer einen spaeteren
# echten Jahresrueckblick, Nutzerwunsch: "digitales Retro-Wohnzimmer").
# Unser bisheriges Tracking (record_playtime() oben) kennt nur
# KUMULIERTE Gesamtwerte pro Spiel, keine Kalenderjahr-Zuordnung - ein
# "Jahresrueckblick 2026" waere damit technisch gar kein echter
# Jahresrueckblick, sondern ein "seit Aufzeichnungsbeginn"-Rueckblick.
#
# Bewusst als KOMPLETT EIGENSTAENDIGE, separate Datei/Funktionen gebaut
# - aendert NICHTS an record_playtime()/load_playtime() selbst, kein
# Risiko fuer bestehende Funktionen, die auf die kumulierten
# Gesamtwerte angewiesen sind (Trophaeenraum, Top-10-Listen, eigene
# Erfolge usw. bleiben komplett unberuehrt). Wird IMMER ZUSAETZLICH zu
# record_playtime() aufgerufen, nie stattdessen.
PLAYTIME_YEARLY_FILE = "/media/fat/frontend/playtime_yearly.json"
FIRST_PLAYED_FILE = "/media/fat/frontend/first_played.json"

def _current_year():
    """Aktuelles Jahr als String - eigene kleine Funktion (statt
    ueberall einzeln time.localtime() aufzurufen), damit Tests den
    Jahreswechsel leicht simulieren koennen (siehe Tests: einfach
    ersetzen statt die Systemzeit zu verstellen)."""
    return str(time.localtime().tm_year)

def load_playtime_yearly():
    """Laedt die nach Kalenderjahr gebuendelte Spielzeit-Statistik.
    Struktur: {jahr_als_string: {"seconds": X, "launches": N,
    "games": {name: sekunden}, "systems": {syskey: sekunden}}}."""
    try:
        with open(PLAYTIME_YEARLY_FILE) as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}

def _load_first_played():
    """Jahr des allerersten Starts pro Spiel (als String) - fuer eine
    spaetere 'dieses Jahr entdeckt'-Sammlung. Eigene, winzige Datei
    statt Teil von playtime_yearly.json, damit ein einzelner
    fehlerhafter Schreibvorgang nicht die Jahres-Hauptstatistik
    gefaehrdet."""
    try:
        with open(FIRST_PLAYED_FILE) as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}

def _record_first_played(label, year):
    """Merkt sich das Jahr des allerersten Starts eines Spiels - wird
    NUR beim allerersten Mal fuer dieses Spiel gesetzt, ein spaeterer
    Aufruf fuer dasselbe Spiel aendert nichts mehr (das reine
    Vorhandensein des Eintrags zaehlt als 'schon gesehen')."""
    data = _load_first_played()
    if label in data:
        return
    data[label] = year
    try:
        os.makedirs(os.path.dirname(FIRST_PLAYED_FILE), exist_ok=True)
        with open(FIRST_PLAYED_FILE, "w") as f:
            json.dump(data, f)
    except OSError:
        pass

def record_yearly_playtime(label, seconds, syskey=None):
    """Wie record_playtime(), aber zusaetzlich nach Kalenderjahr
    gebuendelt - siehe Modul-Kommentar oben fuer die Begruendung.
    Aktualisiert nebenbei _record_first_played()."""
    if not label or seconds <= 0:
        return
    year = _current_year()
    data = load_playtime_yearly()
    entry = data.get(year, {"seconds": 0, "launches": 0, "games": {}, "systems": {}})
    entry["seconds"] = entry.get("seconds", 0) + seconds
    entry["launches"] = entry.get("launches", 0) + 1
    games = entry.setdefault("games", {})
    games[label] = games.get(label, 0) + seconds
    if syskey:
        systems = entry.setdefault("systems", {})
        systems[syskey] = systems.get(syskey, 0) + seconds
    data[year] = entry
    try:
        os.makedirs(os.path.dirname(PLAYTIME_YEARLY_FILE), exist_ok=True)
        with open(PLAYTIME_YEARLY_FILE, "w") as f:
            json.dump(data, f)
    except OSError:
        pass
    _record_first_played(label, year)

def compute_year_review_stats(year=None):
    """Berechnet die Kennzahlen fuer den Jahresrueckblick (Nutzerwunsch:
    "digitales Retro-Wohnzimmer") - baut auf load_playtime_yearly()/
    _load_first_played() auf (siehe v4.1-Fundament oben). year=None
    verwendet das aktuelle Kalenderjahr. Liefert None, wenn fuer das
    gewaehlte Jahr noch gar keine Daten vorliegen (z.B. frisch
    installiert oder der Jahreswechsel ist gerade erst passiert) -
    der Aufrufer zeigt dann eine freundliche "noch nichts hier"-
    Meldung statt leerer/falscher Werte."""
    year = year or _current_year()
    yearly = load_playtime_yearly()
    entry = yearly.get(year)
    if not entry or entry.get("seconds", 0) <= 0:
        return None

    games = entry.get("games", {})
    systems = entry.get("systems", {})
    top_game = max(games, key=games.get) if games else None
    favorite_system = max(systems, key=systems.get) if systems else None

    first_played = _load_first_played()
    discovered_this_year = sum(1 for g in games if first_played.get(g) == year)

    return {
        "year": year,
        "total_seconds": entry.get("seconds", 0),
        "total_launches": entry.get("launches", 0),
        "distinct_games": len(games),
        "distinct_systems": len(systems),
        "top_game": top_game,
        "top_game_seconds": games.get(top_game, 0) if top_game else 0,
        "favorite_system": favorite_system,
        "discovered_this_year": discovered_this_year,
    }

# ----------------------------------------------------------------------------
# SPIELTAGEBUCH (Nutzerwunsch: "digitales Retro-Wohnzimmer" - kleine
# Version zunaechst, "schauen wie es ankommt", volle dauerhafte Version
# mit Archivierung bewusst zurueckgestellt). Rollierendes Protokoll der
# letzten DIARY_RETENTION_DAYS Tage - raeumt sich bei jedem Schreib-
# vorgang automatisch selbst auf, waechst dadurch NIE unbegrenzt (im
# Gegensatz zu playtime_yearly.json/first_played.json, die bewusst
# dauerhaft wachsen duerfen, weil sie nur wenige Bytes pro Spiel/Jahr
# kosten - ein taegliches Sitzungsprotokoll waere das nicht).
#
# Komplett EIGENSTAENDIG - aendert nichts an record_playtime()/
# record_yearly_playtime(), wird IMMER zusaetzlich zu beiden
# aufgerufen, nie stattdessen.
DIARY_FILE = "/media/fat/frontend/diary.json"
DIARY_RETENTION_DAYS = 30

def _current_date_str():
    """Heutiges Datum als 'YYYY-MM-DD' - eigene kleine Funktion (wie
    _current_year()), damit Tests einen Tageswechsel leicht simulieren
    koennen, statt die Systemzeit zu verstellen."""
    return time.strftime("%Y-%m-%d", time.localtime())

def load_diary():
    """Laedt das Spieltagebuch. Struktur: {datum_str: [{"name":...,
    "syskey":..., "seconds":...}, ...]} - ein Eintrag pro tatsaechlich
    beendeter Spielsitzung, mehrere Sitzungen desselben Spiels am
    selben Tag bleiben als SEPARATE Eintraege erhalten (anders als bei
    playtime_yearly.json, wo sie aufaddiert werden) - im Tagebuch soll
    ja der zeitliche Ablauf sichtbar bleiben, nicht nur die Summe."""
    try:
        with open(DIARY_FILE) as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}

def _prune_diary(data):
    """Entfernt Tage, die aelter als DIARY_RETENTION_DAYS sind - haelt
    die Datei dauerhaft klein. Vergleicht ueber epoch-Sekunden statt
    reinem String-Vergleich, damit Monats-/Jahresgrenzen (z.B. Ende
    Januar -> Anfang Februar) korrekt behandelt werden. Ungueltige
    Datumsschluessel (z.B. durch Handbearbeitung entstanden) werden
    still verworfen statt einen Absturz auszuloesen."""
    cutoff = time.time() - DIARY_RETENTION_DAYS * 86400
    kept = {}
    for date_str, entries in data.items():
        try:
            day_epoch = time.mktime(time.strptime(date_str, "%Y-%m-%d"))
        except ValueError:
            continue
        if day_epoch >= cutoff:
            kept[date_str] = entries
    return kept

def record_diary_entry(label, seconds, syskey=None):
    """Traegt eine beendete Spielsitzung ins Tagebuch ein - IMMER
    zusaetzlich zu record_playtime()/record_yearly_playtime()
    aufgerufen (gleicher Aufrufpunkt in run_core()), komplett
    eigenstaendig. Raeumt bei jedem Aufruf automatisch alte Eintraege
    auf (siehe _prune_diary())."""
    if not label or seconds <= 0:
        return
    date_str = _current_date_str()
    data = load_diary()
    data = _prune_diary(data)
    day_entries = data.setdefault(date_str, [])
    day_entries.append({"name": label, "syskey": syskey, "seconds": seconds})
    try:
        os.makedirs(os.path.dirname(DIARY_FILE), exist_ok=True)
        with open(DIARY_FILE, "w") as f:
            json.dump(data, f)
    except OSError:
        pass

# Eigene, sprachabhaengige Monatsnamen statt strftime("%B") - das
# haengt von der SYSTEM-Locale ab (typischerweise Englisch auf einem
# frischen MiSTer), nicht von unserem eigenen CURRENT_LANG-Umschalter.
MONTH_NAMES_DE = ["Januar", "Februar", "Maerz", "April", "Mai", "Juni",
                  "Juli", "August", "September", "Oktober", "November",
                  "Dezember"]
MONTH_NAMES_EN = ["January", "February", "March", "April", "May", "June",
                  "July", "August", "September", "October", "November",
                  "December"]

def _format_diary_date(date_str):
    """Formatiert ein 'YYYY-MM-DD'-Datum fuer die Anzeige im Tagebuch -
    "Heute"/"Gestern" fuer die letzten beiden Tage, sonst "Tag.
    Monatsname" (eigene, sprachabhaengige Monatsnamen, siehe oben)."""
    try:
        parsed = time.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return date_str
    today = _current_date_str()
    yesterday = time.strftime("%Y-%m-%d", time.localtime(time.time() - 86400))
    if date_str == today:
        return t("diary_today")
    if date_str == yesterday:
        return t("diary_yesterday")
    names = MONTH_NAMES_DE if CURRENT_LANG == "de" else MONTH_NAMES_EN
    return "%d. %s" % (parsed.tm_mday, names[parsed.tm_mon - 1])

# ----------------------------------------------------------------------------
# EIGENES, LOKALES ACHIEVEMENT-SYSTEM
#
# Komplett unabhaengig von RetroAchievements - basiert nur auf unseren
# eigenen, laengst vorhandenen Daten (Spielzeit-Tracker, Start-Zaehler,
# Durchgespielt-Markierung). Schwellenwerte werden bei jedem Aufruf
# LIVE aus den aktuellen Daten berechnet (kein separater "erreicht am
# ..."-Zustand, der aus dem Ruder laufen koennte) - simpler und
# robuster als ein eigenes Fortschritts-Tracking zu pflegen.
MILESTONE_DEFS = [
    ("playtime_seconds", 3600,   "milestone_playtime_1h"),
    ("playtime_seconds", 36000,  "milestone_playtime_10h"),
    ("playtime_seconds", 180000, "milestone_playtime_50h"),
    ("playtime_seconds", 360000, "milestone_playtime_100h"),
    ("launches", 10,  "milestone_launches_10"),
    ("launches", 50,  "milestone_launches_50"),
    ("launches", 100, "milestone_launches_100"),
    ("launches", 500, "milestone_launches_500"),
    ("systems", 3,  "milestone_systems_3"),
    ("systems", 5,  "milestone_systems_5"),
    ("systems", 10, "milestone_systems_10"),
    ("completed", 1,  "milestone_completed_1"),
    ("completed", 5,  "milestone_completed_5"),
    ("completed", 10, "milestone_completed_10"),
    ("completed", 25, "milestone_completed_25"),
]

def compute_milestone_progress():
    """Aktuelle Werte fuer alle Meilenstein-Kategorien, aus den
    bereits vorhandenen Daten berechnet (kein zusaetzlicher Scan)."""
    playtime = load_playtime()
    total_seconds = sum(e.get("seconds", 0) for e in playtime.values())
    total_launches = sum(e.get("launches", 0) for e in playtime.values())
    distinct_systems = len(set(
        e["syskey"] for e in playtime.values() if e.get("syskey")))
    completed_count = len(_load_completed_raw())
    return {
        "playtime_seconds": total_seconds,
        "launches": total_launches,
        "systems": distinct_systems,
        "completed": completed_count,
    }

def _format_seconds_short(seconds):
    """Wie format_playtime(), liefert aber IMMER einen Text (auch unter
    einer Minute) - fuer die Meilenstein-Anzeige, wo bei jedem
    Fortschrittswert etwas Lesbares stehen soll, nicht nur ab einer
    bestimmten Groessenordnung.

    BUGFIX (Nutzer-Rueckmeldung anhand eines CRT-Fotos: Fortschritts-
    anzeige zeigte z.B. "14min/100h" - Aktuell- und Zielwert in
    UNTERSCHIEDLICHEN Einheiten nebeneinander, schwer auf einen Blick
    vergleichbar): zeigt jetzt IMMER konsequent "Stunden dann Minuten"
    (auch "0h"), damit beide Seiten des Bruchs im selben Format stehen -
    z.B. "0h 14min/100h 0min" statt des vorherigen Mix aus "14min" und
    "100h"."""
    seconds = max(0, int(seconds))
    mins = seconds // 60
    h, m = divmod(mins, 60)
    return "%dh %dmin" % (h, m)

def get_milestones():
    """Liste aller Meilensteine als (label_key, erreicht, aktueller_wert,
    schwellenwert, kind)-Tupel, in der definierten Reihenfolge. kind
    wird fuer die richtige Anzeige-Formatierung gebraucht (Sekunden
    lesbar als "3min"/"2h 15min" statt roher Zahl, siehe
    draw_milestones_screen())."""
    progress = compute_milestone_progress()
    out = []
    for kind, threshold, label_key in MILESTONE_DEFS:
        current = progress.get(kind, 0)
        out.append((label_key, current >= threshold, current, threshold, kind))
    return out

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
HIDDEN_UNLOCKED_FILE = "/media/fat/frontend/hidden_achievements.json"

def _load_hidden_unlocked():
    """Menge der IDs bereits freigeschalteter, EREIGNIS-basierter
    versteckter Erfolge."""
    try:
        with open(HIDDEN_UNLOCKED_FILE) as f:
            data = json.load(f)
            return set(data) if isinstance(data, list) else set()
    except (OSError, ValueError):
        return set()

def _unlock_hidden(achievement_id):
    """Schaltet einen ereignis-basierten versteckten Erfolg frei
    (dauerhaft gespeichert). Rueckgabe: True, wenn er JETZT neu
    freigeschaltet wurde, False, wenn er es schon vorher war."""
    data = _load_hidden_unlocked()
    if achievement_id in data:
        return False
    data.add(achievement_id)
    try:
        os.makedirs(os.path.dirname(HIDDEN_UNLOCKED_FILE), exist_ok=True)
        with open(HIDDEN_UNLOCKED_FILE, "w") as f:
            json.dump(sorted(data), f)
    except OSError:
        pass
    return True

def check_hidden_session_achievements(session_start_walltime, elapsed_seconds):
    """Nach einer gespielten Sitzung (siehe run_core()) pruefen, ob
    dadurch ein ereignis-basierter versteckter Erfolg freigeschaltet
    wird. session_start_walltime: echte Wanduhrzeit (time.time()) beim
    Sitzungsbeginn - NICHT die monotone Zeit, die fuer die
    Dauer-Berechnung genutzt wird (die ist unempfindlich gegen
    Uhr-Korrekturen, sagt aber nichts ueber die Tageszeit aus)."""
    try:
        hour = time.localtime(session_start_walltime).tm_hour
        if 0 <= hour < 5:
            _unlock_hidden("night_owl")
    except Exception:
        pass
    if elapsed_seconds >= 3 * 3600:
        _unlock_hidden("marathon")

def get_hidden_achievements():
    """Liste (id, label_key, freigeschaltet)-Tupel fuer alle
    versteckten Erfolge."""
    unlocked_events = _load_hidden_unlocked()
    favorites_count = len(_load_favorites_raw())
    playtime = load_playtime()
    max_launches = max((e.get("launches", 0) for e in playtime.values()),
                       default=0)
    progress = compute_milestone_progress()
    legend_unlocked = (progress["playtime_seconds"] >= 360000 and
                       progress["launches"] >= 500 and
                       progress["systems"] >= 10 and
                       progress["completed"] >= 25)
    return [
        ("night_owl", "hidden_night_owl", "night_owl" in unlocked_events),
        ("marathon", "hidden_marathon", "marathon" in unlocked_events),
        ("collector", "hidden_collector", favorites_count >= 10),
        ("completionist", "hidden_completionist", max_launches >= 20),
        ("legend", "hidden_legend", legend_unlocked),
    ]

# ----------------------------------------------------------------------------
# POP-UP BEI NEU ERREICHTEN ERFOLGEN - vergleicht den aktuellen Stand
# (normale Meilensteine UND versteckte Erfolge, jeweils live berechnet)
# gegen eine dauerhafte Liste "das wurde dem Nutzer schon gezeigt", damit
# nach einem Neustart nicht ploetzlich alle laengst erreichten Erfolge
# erneut aufploppen - nur ECHT NEUE loesen ein Pop-up aus.
ACHIEVEMENTS_SEEN_FILE = "/media/fat/frontend/achievements_seen.json"

def _load_achievements_seen():
    try:
        with open(ACHIEVEMENTS_SEEN_FILE) as f:
            data = json.load(f)
            return set(data) if isinstance(data, list) else set()
    except (OSError, ValueError):
        return set()

def _save_achievements_seen(seen):
    try:
        os.makedirs(os.path.dirname(ACHIEVEMENTS_SEEN_FILE), exist_ok=True)
        with open(ACHIEVEMENTS_SEEN_FILE, "w") as f:
            json.dump(sorted(seen), f)
    except OSError:
        pass

def _ensure_achievements_seen_initialized():
    """Initialisiert ACHIEVEMENTS_SEEN_FILE einmalig GLEICH BEIM START
    (Frontend.__init__()), falls sie noch nicht existiert - markiert
    alle zu DIESEM Zeitpunkt bereits erreichten Erfolge als "gezeigt",
    OHNE dafuer ein Pop-up auszuloesen (sonst gaebe es bei jemandem mit
    laengerer Spielhistorie eine Flut von Meldungen fuer laengst
    Erreichtes).

    BUGFIX (Nutzer-Rueckmeldung): 3 verschiedene Systeme gestartet,
    "Entdecker"-Erfolg korrekt in "Meine Erfolge" als erreicht
    angezeigt - aber KEIN Pop-up/Ton beim Zurueckkehren aus dem Spiel.
    Ursache: die Erstlauf-Sonderbehandlung sass bisher direkt IN
    check_new_achievements() und griff beim ALLERERSTEN Aufruf dieser
    Funktion ueberhaupt - der aber zufaellig GENAU in dem Moment
    passieren konnte, in dem der Erfolg WIRKLICH neu erreicht wurde
    (z.B. die erste jemals gespielte Sitzung, bei der zugleich das
    dritte System erreicht wird). Der Erfolg wurde dadurch faelschlich
    als "schon vorher da gewesen" behandelt und sein Pop-up
    unterdrueckt. Fix: die Baseline wird jetzt explizit VOR jeder
    moeglichen Nutzeraktion initialisiert (siehe Frontend.__init__()),
    dadurch ist die Datei bei JEDEM tatsaechlichen Ereignis-Aufruf
    (Sitzungsende, Favorit/Durchgespielt umschalten) bereits vorhanden
    - check_new_achievements() selbst braucht dadurch keine Erstlauf-
    Sonderbehandlung mehr und meldet zuverlaessig jeden Erfolg, der
    NACH dem Start neu erreicht wird."""
    if os.path.exists(ACHIEVEMENTS_SEEN_FILE):
        return
    seen = set()
    for label_key, achieved, _current, _threshold, _kind in get_milestones():
        if achieved:
            seen.add(label_key)
    for hid, _label_key, unlocked in get_hidden_achievements():
        if unlocked:
            seen.add(hid)
    _save_achievements_seen(seen)

def check_new_achievements():
    """Vergleicht den aktuellen Erfolgs-Stand gegen die bereits gezeigten
    - liefert eine Liste der NEU erreichten label_keys (in der
    Reihenfolge: normale Meilensteine, dann versteckte Erfolge) und
    merkt sie SOFORT als gezeigt, damit derselbe Erfolg nicht ein
    zweites Mal ein Pop-up ausloest. Leere Liste, wenn nichts Neues
    dazugekommen ist - der haeufigste Fall, entsprechend guenstig
    (nur Mengen-Operationen, kein Datei-Schreiben ohne Aenderung).

    Setzt voraus, dass _ensure_achievements_seen_initialized() bereits
    beim Start gelaufen ist (siehe Frontend.__init__()) - deshalb hier
    KEINE eigene Erstlauf-Sonderbehandlung mehr noetig (siehe dort fuer
    die Begruendung/den Bugfix)."""
    seen = _load_achievements_seen()
    newly = []
    for label_key, achieved, _current, _threshold, _kind in get_milestones():
        if achieved and label_key not in seen:
            newly.append(label_key)
            seen.add(label_key)
    for hid, label_key, unlocked in get_hidden_achievements():
        if unlocked and hid not in seen:
            newly.append(label_key)
            seen.add(hid)
    if newly:
        _save_achievements_seen(seen)
    return newly


# ----------------------------------------------------------------------------
# TROPHAEENRAUM - persoenlicher Profil-Bildschirm: meistgespieltes Spiel,
# Lieblingssystem, Erfolgs-Zaehler, kurze Zusammenfassung. Baut komplett
# auf Daten auf, die wir ohnehin schon sammeln (Spielzeit-Tracker,
# Meilensteine) - reine Zusammenfassung, keine neue Datenquelle.
def compute_profile_stats():
    """Sammelt die Kennzahlen fuer den Trophaeenraum-Bildschirm.
    Liefert ein dict - alle Werte auch bei komplett leerer Historie
    sicher (0/None statt eines Fehlers), damit der Bildschirm auch
    fuer jemanden ohne jede Spielzeit sinnvoll etwas anzeigen kann."""
    playtime = load_playtime()
    total_seconds = sum(e.get("seconds", 0) for e in playtime.values())
    total_launches = sum(e.get("launches", 0) for e in playtime.values())

    top = top_played_games(by="seconds", n=1)
    top_game = top[0] if top else None   # (label, seconds, launches)

    # Lieblingssystem: Summe der Spielzeit pro System (nur Eintraege mit
    # bekanntem syskey - siehe record_playtime()/v1.92).
    system_seconds = {}
    for e in playtime.values():
        sk = e.get("syskey")
        if sk:
            system_seconds[sk] = system_seconds.get(sk, 0) + e.get("seconds", 0)
    favorite_system = (max(system_seconds, key=system_seconds.get)
                       if system_seconds else None)

    milestones = get_milestones()
    hidden = get_hidden_achievements()
    unlocked = (sum(1 for m in milestones if m[1])
               + sum(1 for h in hidden if h[2]))
    total_achievements = len(milestones) + len(hidden)

    return {
        "total_seconds": total_seconds,
        "total_launches": total_launches,
        "top_game": top_game,
        "favorite_system": favorite_system,
        "distinct_systems": len(system_seconds),
        "unlocked": unlocked,
        "total_achievements": total_achievements,
    }

# ----------------------------------------------------------------------------
# FRONTEND-LEVEL (Nutzerwunsch: "das Menue sammelt Erfahrungspunkte,
# nicht der Spieler") - rein abgeleitet aus Werten, die wir ohnehin
# schon dauerhaft speichern (Spielzeit, Starts, versteckte Erfolge).
# Kein zusaetzlicher Speicherbedarf, kann bei jedem Aufruf frisch
# berechnet werden - und ist von Natur aus monoton (kann nie sinken,
# da die zugrunde liegenden Werte nur wachsen koennen).
FRONTEND_LEVEL_MAX = 5

def compute_frontend_level():
    """Liefert das aktuelle Frontend-Level (1-5). Stufen bewusst grosszuegig
    UND ueber mehrere Wege erreichbar (Spielzeit ODER Starts ODER
    versteckte Erfolge) - niemand soll sich durch eine einzelne, enge
    Anforderung ausgeschlossen fuehlen."""
    stats = compute_profile_stats()
    hours = stats["total_seconds"] / 3600.0
    launches = stats["total_launches"]
    hidden = get_hidden_achievements()
    hidden_count = sum(1 for h in hidden if h[2])
    legend_unlocked = any(h[0] == "legend" and h[2] for h in hidden)

    if legend_unlocked:
        return 5
    if hours >= 50 or hidden_count >= 3:
        return 4
    if hours >= 20 or launches >= 50:
        return 3
    if hours >= 5 or launches >= 20:
        return 2
    return 1

# ----------------------------------------------------------------------------
# GEHEIME CODES (Nutzerwunsch: "Easter Egg System" - ein paar
# Cheat-Code-Sequenzen, jede schaltet ein anderes Geheimnis frei). Auf
# unser Aktions-Vokabular uebertragen. Absichtlich KEINE ausfuehrliche
# Erklaerung hier im Kommentar, welche Codes das sind oder woher sie
# stammen - das darf sich jede/r selbst erspielen, siehe
# draw_secrets_screen().
#
# WICHTIG (Nutzer-Nachfrage, Design zweimal korrigiert):
#   1. Versuch: "ok"/"back" fuer die Bestaetigungs-Positionen - FALSCH,
#      beide loesen im Hauptmenue IMMER eine echte Wirkung aus
#      (Kategorie betreten bzw. Beenden-Bestaetigung, siehe
#      _go_back_or_confirm_quit()), auch waehrend einer laufenden
#      Code-Eingabe. Einer der Codes haette dadurch NIE vollstaendig
#      eingegeben werden koennen.
#   2. Versuch: "favorite"/"completed" (F7/F8) statt ok/back - beide
#      nachweislich wirkungslos, ABER: "completed" hat GAR KEINE
#      Joypad-Taste (nur Tastatur F7), und "favorite" liegt auf L2/R2 -
#      auf SNES-Nachbau-Pads (bei MiSTer-Nutzern verbreitet) oft gar
#      nicht vorhanden. Auf einem einfachen Pad war praktisch KEINE
#      Taste mehr frei, die garantiert wirkungslos ist.
#   FINALE LOESUNG (auf Nutzerwunsch): Codes werden bewusst NUR per
#   TASTATUR eingegeben - Pfeiltasten fuer die Richtungen, echte
#   Buchstabentasten fuer die Bestaetigungs-Positionen. Buchstabentasten
#   loesen im Hauptmenue nur einen harmlosen Buchstaben-Sprung in der
#   Kategorienliste aus (siehe LETTER_KEYS/"letter:"-Aktion,
#   jump_to_letter()) - GENAUSO sicher wie hoch/runter/links/rechts,
#   kein Seitenwechsel, kein Dialog. Per Joypad sind diese Codes damit
#   bewusst NICHT eingebbar - siehe Hinweistext auf dem Geheimnisse-
#   Bildschirm.
SECRETS_FILE = "/media/fat/frontend/secrets_unlocked.json"

SECRET_CODES = {
    # Schaltet das erste geheime Theme frei. Nur per Tastatur eingebbar.
    "secret_theme_1": ["up", "up", "down", "down", "left", "right",
                       "left", "right", "letter:B", "letter:A"],
    # Schaltet den Entwicklerraum frei. Nur per Tastatur eingebbar.
    "entwicklerraum": ["down", "letter:R", "up", "letter:L",
                      "letter:Y", "letter:B"],
    # Schaltet einen geheimen Sound frei. Nur per Tastatur eingebbar.
    "secret_sound": ["letter:A", "letter:B", "letter:B", "letter:A"],
}
SECRET_CODE_MAXLEN = max(len(seq) for seq in SECRET_CODES.values())

def _load_secrets_unlocked():
    """Menge der IDs bereits per Geheimcode freigeschalteter
    Geheimnisse - gleiches Speicherprinzip wie bei den versteckten
    Erfolgen (siehe _load_hidden_unlocked())."""
    try:
        with open(SECRETS_FILE) as f:
            data = json.load(f)
            return set(data) if isinstance(data, list) else set()
    except (OSError, ValueError):
        return set()

def _unlock_secret(secret_id):
    """Schaltet ein Geheimnis dauerhaft frei. Rueckgabe: True, wenn es
    JETZT neu freigeschaltet wurde, False, wenn es das schon vorher
    war (z.B. Code versehentlich zweimal eingegeben)."""
    data = _load_secrets_unlocked()
    if secret_id in data:
        return False
    data.add(secret_id)
    try:
        os.makedirs(os.path.dirname(SECRETS_FILE), exist_ok=True)
        with open(SECRETS_FILE, "w") as f:
            json.dump(sorted(data), f)
    except OSError:
        pass
    return True

def check_secret_code(buffer):
    """Prueft, ob der Schluss des Aktions-Puffers (Liste der zuletzt
    gedrueckten Aktionen, neueste zuletzt) exakt einem der bekannten
    Geheim-Codes entspricht. Liefert die passende secret_id oder None.
    Reine Vergleichsfunktion ohne Seiteneffekt - das eigentliche
    Freischalten uebernimmt der Aufrufer (siehe Frontend._check_secret_
    codes())."""
    for secret_id, seq in SECRET_CODES.items():
        n = len(seq)
        if len(buffer) >= n and list(buffer[-n:]) == seq:
            return secret_id
    return None


def top_played_games(by="seconds", n=10):
    """Liefert die n Spiele mit dem hoechsten Wert fuer "seconds"
    (Gesamtspielzeit) oder "launches" (Anzahl Starts), absteigend
    sortiert, als Liste von (label, seconds, launches)-Tupeln. Spiele
    mit 0 in der gesuchten Kategorie werden ausgelassen (kein Sinn,
    "Platz 7: 0 Starts" anzuzeigen)."""
    data = load_playtime()
    items = [(label, e["seconds"], e["launches"])
             for label, e in data.items() if e.get(by, 0) > 0]
    idx = 1 if by == "seconds" else 2
    items.sort(key=lambda t: -t[idx])
    return items[:n]

def format_playtime(seconds):
    """Formatiert eine Sekundenzahl fuer die Anzeige - z.B. "2h 15min"
    oder "5min" oder "< 1min"."""
    if seconds is None or seconds <= 0:
        return None
    mins = int(seconds // 60)
    if mins < 1:
        return None   # unter einer Minute - noch nichts Sinnvolles zu zeigen
    h, m = divmod(mins, 60)
    if h > 0:
        return "%dh %dmin" % (h, m) if m else "%dh" % h
    return "%dmin" % m

MISTER_CMD  = "/dev/MiSTer_cmd"

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
    """Prueft einen rohen HID-Tastatur-Report auf Escape (0x29) ODER
    F10 (0x44) - UNABHAENGIG von Modifikatortasten (frueher Strg+Alt+
    Esc, auf Nutzerwunsch auf reines Esc vereinfacht, da einfacher zu
    druecken).

    ERWEITERT (Nutzer-Rueckmeldung: "F10 funktioniert nicht"): F10 war
    bisher NUR ueber die normale evdev-Ebene abgefragt
    (KEY_F10-Vergleich in wait_game_exit()) - die MiSTer waehrend
    eines laufenden Cores exklusiv sperrt (dasselbe bereits bekannte
    Problem wie beim Start+Select-Kombo, siehe dortiger Kommentar).
    F10 haette dadurch praktisch nie tatsaechlich ausgeloest. Jetzt
    laeuft F10 ueber denselben bereits bestaetigt funktionierenden
    HID-Weg wie Esc - zwei gleichwertige Ausstiegs-Tasten statt einer,
    beide ueber den zuverlaessigen Pfad.

    WICHTIG: viele Spiele nutzen Esc selbst schon fuer eigene Pause-/
    Menue-Funktionen - deshalb bleibt die Haltezeit (KBD_COMBO_HOLD,
    siehe wait_game_exit()) als Sicherung bestehen. Ein kurzer,
    normaler Tastendruck im Spiel loest dadurch NICHT versehentlich
    den Ausstieg aus - nur ein bewusst LAENGER GEHALTENES Esc oder F10
    tut das.

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
    if 0x29 in data or 0x44 in data:
        return True
    if len(data) > 7 and data[0] == 0x06 and (data[7] & 0x02):
        return True
    return False


MUSIC_DIR   = "/media/fat/music"
MUSIC_ENABLED_FILE = "/media/fat/frontend/music_enabled"
MUSIC_SOURCE_FILE  = "/media/fat/frontend/music_source"   # "mp3"/"radio" + Stations-sid
VOLUME_FILE = "/media/fat/frontend/volume"   # Lautstaerke 0-100 (Musik + Menue-Sounds)

# NEUES FEATURE (Nutzerwunsch: Lautstaerke-Regler fuer Musik UND
# Menue-Sounds, uebernommen aus einem separat vorbereiteten, auf
# echter MiSTer-Hardware getesteten Vorschlag - siehe
# CHANGES_VOLUME.md). Zwei unterschiedliche Mechanismen, weil Musik
# und Menue-Sounds technisch verschieden abgespielt werden: Musik
# laeuft ueber mpg123, das einen eingebauten Skalierungsfaktor
# (-f 0..32768) hat. Menue-Sounds sind selbst erzeugte WAVs, abgespielt
# ueber aplay - aplay hat KEINEN Lautstaerke-Schalter, deshalb steckt
# die Lautstaerke dort in der AMPLITUDE der erzeugten WAV-Datei selbst
# (werden bei einer Aenderung neu erzeugt statt nur neu abgespielt).
def _load_volume():
    try:
        return max(0, min(100, int(open(VOLUME_FILE).read().strip())))
    except (OSError, ValueError):
        return 100

def _save_volume(v):
    try:
        os.makedirs(os.path.dirname(VOLUME_FILE), exist_ok=True)
        with open(VOLUME_FILE, "w") as f:
            f.write(str(int(v)))
    except OSError:
        pass

VOLUME = _load_volume()   # 0-100; global, von Musik (mpg123 -f) UND SFX genutzt

def _mpg_scale():
    """mpg123 -f Skalierungsfaktor (0..32768) fuer die aktuelle Lautstaerke."""
    return str(int(32768 * VOLUME / 100))

def _regenerate_sfx():
    """Menue-Sound-WAVs bei geaenderter Lautstaerke neu erzeugen - aplay hat
    keinen Volume-Schalter, also steckt die Lautstaerke in der Amplitude."""
    try:
        for _f in glob.glob(os.path.join(SFX_DIR, "*.wav")):
            os.remove(_f)
    except OSError:
        pass
    _ensure_sfx_files()

_volume_apply_lock = None

def _apply_volume_async(player):
    """SFX-Neuerzeugung + Musik-Neustart im Hintergrund - beides ist auf dem
    MiSTer traege bzw. blockierend (Popen.wait bis 2s), also NICHT im
    Menue-Thread. Ein Lock serialisiert schnelle Mehrfach-Druecke; jeder
    Lauf nutzt das dann aktuelle VOLUME (letzter gewinnt).

    BUGFIX (uebernommen aus separat vorbereitetem Vorschlag, siehe
    CHANGES_v4.2_FIXES.md): rief bisher player._stop_current() und
    player._start_current() als ZWEI getrennte Aufrufe auf - dazwischen
    konnte tick() (aus dem Menue-Thread) ebenfalls einen Start ausloesen,
    zwei mpg123-Prozesse liefen dann gleichzeitig (doppelter/verzerrter
    Radio-Stream). _start_current() beendet jetzt selbst, unter
    _proc_lock, zuerst den alten Prozess, bevor der neue startet - ein
    einziger, atomarer Aufruf reicht."""
    global _volume_apply_lock
    if _volume_apply_lock is None:
        _volume_apply_lock = threading.Lock()
    def _worker():
        with _volume_apply_lock:
            _regenerate_sfx()
            if player.enabled and not player.paused_for_core:
                player._start_current()
    threading.Thread(target=_worker, daemon=True).start()

LANGUAGE_FILE = "/media/fat/frontend/language"
KEYMAP_CUSTOM_FILE = "/media/fat/frontend/keymap_custom.json"
BOOTANIM_DIR = "/media/fat/frontend/bootanim"
BOOTANIM_PLAYED_MARKER = "/tmp/frontend_bootanim_played"
MPG123_BIN  = "/usr/bin/mpg123"

# NEUES FEATURE (Nutzerwunsch: vereinfachte Installation, ein
# Ersteinrichtungs-Assistent, der einmalig durch alle wichtigen
# Schritte fuehrt): anders als BOOTANIM_PLAYED_MARKER (liegt in /tmp,
# wird bei JEDEM Neustart neu abgespielt) liegt diese Markierung
# bewusst auf der SD-Karte (/media/fat/...) - der Assistent soll nur
# EINMAL im Leben automatisch erscheinen, nicht bei jedem Boot.
SETUP_WIZARD_DONE_FILE = "/media/fat/frontend/setup_wizard_done"

def setup_wizard_done():
    return os.path.exists(SETUP_WIZARD_DONE_FILE)

def mark_setup_wizard_done():
    try:
        os.makedirs(os.path.dirname(SETUP_WIZARD_DONE_FILE), exist_ok=True)
        open(SETUP_WIZARD_DONE_FILE, "w").close()
    except OSError:
        pass

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
FBDEV       = "/dev/fb0"

# Ordner, die bei der automatischen Kategorie-Suche uebersprungen werden
SKIP_DIRS = {"_Scripts"}

# Freundliche Anzeigenamen fuer bekannte Ordner
NICE_NAMES = {
    "Arcade": "Arcade", "Console": "Consoles", "Computer": "Computer",
    "Other": "Other", "Utility": "Utilities", "RA_Cores": "RA Cores",
}

# Spielesysteme: (Anzeigename, Systemkey, ROM-Ordner, Core-RBF,
#                  {Endung: (mgl_delay, mgl_type, mgl_index)})
# MGL-Parameter stammen aus der mrext-Systemdatenbank (wizzomafizzo).
GAME_SYSTEMS = [
    ("NES",           "NES",     ["NES"],                  "_Console/NES",
        {".nes": (2, "f", 1)}),
    ("SNES",          "SNES",    ["SNES"],                 "_Console/SNES",
        {".sfc": (2, "f", 0), ".smc": (2, "f", 0)}),
    ("Mega Drive",    "Genesis", ["MegaDrive", "Genesis"], "_Console/MegaDrive",
        {".md": (1, "f", 1), ".gen": (1, "f", 1), ".bin": (1, "f", 1)}),
    ("Nintendo 64",   "N64",     ["N64"],                  "_Console/N64",
        {".n64": (1, "f", 1), ".z64": (1, "f", 1)}),
    ("PlayStation",   "PSX",     ["PSX"],                  "_Console/PSX",
        {".chd": (1, "s", 1), ".cue": (1, "s", 1)}),
    ("Game Boy",      "GAMEBOY", ["GAMEBOY"],              "_Console/Gameboy",
        {".gb": (2, "f", 1)}),
    ("Game Boy Color","GBC",     ["GAMEBOY"],              "_Console/Gameboy",
        {".gbc": (2, "f", 1)}),
    ("GBA",           "GBA",     ["GBA"],                  "_Console/GBA",
        {".gba": (2, "f", 1)}),
    ("Master System", "SMS",     ["SMS"],                  "_Console/SMS",
        {".sms": (1, "f", 1), ".gg": (1, "f", 2)}),
    ("TurboGrafx16",  "TGFX16",  ["TGFX16"],               "_Console/TurboGrafx16",
        {".pce": (1, "f", 0), ".sgx": (1, "f", 1)}),
    ("Mega CD",       "MegaCD",  ["MegaCD"],               "_Console/MegaCD",
        {".chd": (1, "s", 0), ".cue": (1, "s", 0)}),
    ("Saturn",        "Saturn",  ["Saturn"],               "_Console/Saturn",
        {".chd": (1, "s", 0), ".cue": (1, "s", 0)}),
    ("Neo Geo",       "NEOGEO",  ["NEOGEO"],               "_Console/NeoGeo",
        {".neo": (1, "f", 1)}),
    # SMW Hacks (Nutzerwunsch): eigenes System im Hauptmenue, LAEUFT
    # ABER mit dem ganz normalen SNES-Core (rbf-Pfad identisch zu
    # "SNES" oben) - eigener Systemschluessel nur fuer eigene
    # Akzentfarbe/eigenes Sysart (siehe SYSTEM_ACCENT), NICHT weil ein
    # eigener Core noetig waere. ROMs liegen unter games/SNES/SMW_HACKS
    # (wird per claimed_subfolders aus der regulaeren SNES-Kategorie
    # ausgeschlossen, siehe _scan_games_disk() - sonst Doppel-Anzeige).
    ("SMW Hacks",     "SMW_HACKS", ["SNES/SMW_HACKS"],      "_Console/SNES",
        {".sfc": (2, "f", 0), ".smc": (2, "f", 0)}),
]

# OPTIONALE Systeme (Nutzerwunsch): wie GAME_SYSTEMS oben, aber
# zusaetzlich mit einer echten Core-Datei-Praesenzpruefung
# (core_check_path) - erscheinen NUR, wenn diese exakte Datei
# tatsaechlich auf der SD-Karte liegt, sonst komplett unsichtbar
# (nicht einmal ein leerer/deaktivierter Eintrag). Anders als die
# Standardsysteme oben, deren offizielle Cores praktisch immer
# vorhanden sind und deshalb nie geprueft wurden - hier handelt es
# sich um einen einzelnen, von Hand installierten Custom-Core
# (kein versionierter, datumsgestempelter Ordner wie bei den
# offiziellen Cores, sondern eine einzelne feste Datei direkt in
# _Console - vom Nutzer bestaetigt: "SNES_Tracker.rbf", Ordner
# "_Console").
#
# Feld-Reihenfolge identisch zu GAME_SYSTEMS (Anzeigename, Systemschluessel,
# ROM-Unterordner-Liste relativ zu GAMES_BASES, rbf-Pfad OHNE Endung fuer
# die .mgl-Datei, Dateiendungen-Map), plus fuenftes Feld core_check_path
# (absoluter Pfad zur tatsaechlichen .rbf-Datei fuer die Praesenzpruefung).
OPTIONAL_GAME_SYSTEMS = [
    ("SNES ALTTP Tracker", "SNES_ALTTP_TRACKER", ["SNES/ZELDA_MSU"],
        "_Console/SNES_Tracker",
        {".sfc": (2, "f", 0), ".smc": (2, "f", 0)},
        "/media/fat/_Console/SNES_Tracker.rbf"),
]

def system_display_name(syskey):
    """Anzeigename zu einem Systemschluessel (z.B. "Genesis" ->
    "Mega Drive") - fuer Stellen, die einen menschenlesbaren Namen
    statt des internen Schluessels brauchen (siehe Trophaeenraum).
    Prueft auch OPTIONAL_GAME_SYSTEMS mit."""
    for disp, sk, *_ in GAME_SYSTEMS:
        if sk == syskey:
            return disp
    for disp, sk, *_ in OPTIONAL_GAME_SYSTEMS:
        if sk == syskey:
            return disp
    return syskey or "?"

# ----------------------------------------------------------------------------
# RA-CORE-ERKENNUNG (sage2050s "MiSTer_RetroAchievements"-Werkzeug -
# legt RA-faehige Core-Varianten in einen separaten Ordner, getrennt
# von den Standard-Cores)
#
# EHRLICHER HINWEIS: die exakte Dateibenennung dieses Werkzeugs wurde
# inzwischen per echter Nutzer-Installation verifiziert (siehe die
# .mgl-Struktur unten bei write_mgl()/setname). Fuer Systeme ohne
# bestaetigte Namensliste werden trotzdem mehrere plausible Varianten
# durchprobiert - der erste tatsaechlich EXISTIERENDE Treffer gewinnt,
# findet sich keiner, wird fuer dieses System einfach KEINE Auswahl
# angezeigt (nie ein nicht-existierender Pfad referenziert). Arcade
# ist bei diesem RA-Core-Set nicht enthalten - taucht deshalb hier
# bewusst nicht auf.
RA_CORES_DIR_ABS = "/media/fat/_RA_Cores/Cores"
RA_CORES_DIR_REL = "_RA_Cores/Cores"

RA_CORE_NAME_CANDIDATES = {
    "NES":     ["NES"],
    "SNES":    ["SNES"],
    "Genesis": ["Genesis", "MegaDrive"],
    "N64":     ["N64"],
    "PSX":     ["PSX", "PlayStation"],
    "GAMEBOY": ["Gameboy", "GAMEBOY", "GB"],
    "GBC":     ["Gameboy", "GAMEBOY", "GBC"],
    "GBA":     ["GBA"],
    "SMS":     ["SMS", "MasterSystem"],
    "TGFX16":  ["TGFX16", "TurboGrafx16"],
    "MegaCD":  ["MegaCD", "SegaCD"],
    "NEOGEO":  ["NeoGeo", "NEOGEO"],
    "Saturn":  ["Saturn"],
    "SMW_HACKS": ["SNES"],   # laeuft mit dem normalen SNES-(RA-)Core, siehe GAME_SYSTEMS-Kommentar
}

def find_ra_core(syskey):
    """Sucht die RA-faehige Core-Datei fuer ein System. Liefert
    (mgl_rbf_pfad, setname) bei einem tatsaechlichen Treffer, sonst
    None. setname entspricht exakt dem Format, das sage2050s eigene
    .mgl-Dateien verwenden (per echter Nutzer-Installation
    verifiziert: <rbf>_RA_Cores/Cores/NES</rbf> +
    <setname same_dir="1">RA_NES</setname>) - ohne dieses Element
    wird der RA-Core von MiSTer offenbar nicht korrekt als eigene,
    von der Standard-Konfiguration getrennte Core-Variante behandelt."""
    for name in RA_CORE_NAME_CANDIDATES.get(syskey, []):
        if os.path.exists(os.path.join(RA_CORES_DIR_ABS, name + ".rbf")):
            return (RA_CORES_DIR_REL + "/" + name, "RA_" + name)
    return None

# Overscan-Sicherheitsrand in Prozent pro Seite (CRTs beschneiden das Bild).
# Bei Bedarf anpassen: mehr, wenn weiterhin Raender fehlen; weniger auf LCD.
OVERSCAN_X = 7
OVERSCAN_Y = 5

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

def accent_for(syskey):
    """Akzentfarbe fuer ein System - faellt auf den Standard zurueck,
    wenn kein syskey vorhanden ist (Scripts/System/Core-Ordner) oder
    das System nicht in SYSTEM_ACCENT gelistet ist."""
    return SYSTEM_ACCENT.get(syskey, C_ACCENT)
C_TEXT   = (220, 224, 232)
C_DIM    = (120, 126, 140)
C_TITLE  = (255, 255, 255)   # Logo/Systemname: weiss (Retro-Look)

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
}
THEME_ORDER = ["dark", "light", "green"]
THEME_NAMES_DE = {"dark": "Dunkel (Standard)", "light": "Hell",
                  "green": "Retro-Gruen", "secret_gold": "??? Geheim ???"}
THEME_NAMES_EN = {"dark": "Dark (default)", "light": "Light",
                  "green": "Retro Green", "secret_gold": "??? Secret ???"}

def _available_theme_order():
    """THEME_ORDER, erweitert um freigeschaltete Geheim-Themes - so
    bleiben sie in der normalen Durchschalt-Reihenfolge (cycle_theme())
    unsichtbar, bis der zugehoerige Geheimcode gefunden wurde."""
    order = list(THEME_ORDER)
    if "secret_theme_1" in _load_secrets_unlocked():
        order.append("secret_gold")
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
    verwendet werden (kein Umbau an anderer Stelle noetig)."""
    global C_BG, C_PANEL, C_TEXT, C_DIM, C_TITLE, C_ACCENT
    theme = THEMES.get(name, THEMES["dark"])
    C_BG = theme["C_BG"]
    C_PANEL = theme["C_PANEL"]
    C_TEXT = theme["C_TEXT"]
    C_DIM = theme["C_DIM"]
    C_TITLE = theme["C_TITLE"]
    C_ACCENT = theme["C_ACCENT"]

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
# 8x8 BITMAP-FONT (Public Domain, IBM VGA / Marcel Sondaar / Daniel Hepper)
# ----------------------------------------------------------------------------
FONT8X8 = bytes.fromhex('000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000183c3c1818001800363600000000000036367f367f3636000c3e031e301f0c00006333180c6663001c361c6e3b336e000606030000000000180c0606060c1800060c1818180c060000663cff3c660000000c0c3f0c0c000000000000000c0c060000003f0000000000000000000c0c006030180c060301003e63737b6f673e000c0e0c0c0c0c3f001e33301c06333f001e33301c30331e00383c36337f3078003f031f3030331e001c06031f33331e003f3330180c0c0c001e33331e33331e001e33333e30180e00000c0c00000c0c00000c0c00000c0c06180c0603060c180000003f00003f0000060c1830180c06001e3330180c000c003e637b7b7b031e000c1e33333f3333003f66663e66663f003c66030303663c001f36666666361f007f46161e16467f007f46161e16060f003c66030373667c003333333f333333001e0c0c0c0c0c1e007830303033331e006766361e366667000f06060646667f0063777f7f6b63630063676f7b736363001c36636363361c003f66663e06060f001e3333333b1e38003f66663e366667001e33070e38331e003f2d0c0c0c0c1e003333333333333f0033333333331e0c006363636b7f7763006363361c1c3663003333331e0c0c1e007f6331184c667f001e06060606061e0003060c18306040001e18181818181e00081c36630000000000000000000000ff0c0c18000000000000001e303e336e000706063e66663b0000001e3303331e003830303e33336e0000001e333f031e001c36060f06060f0000006e33333e301f0706366e666667000c000e0c0c0c1e00300030303033331e070666361e3667000e0c0c0c0c0c1e000000337f7f6b630000001f333333330000001e3333331e0000003b66663e060f00006e33333e307800003b6e66060f0000003e031e301f00080c3e0c0c2c18000000333333336e0000003333331e0c000000636b7f7f3600000063361c36630000003333333e301f00003f190c263f00380c0c070c0c38001818180018181800070c0c380c0c07006e3b0000000000000000000000000000')

# ----------------------------------------------------------------------------
# FRAMEBUFFER
# ----------------------------------------------------------------------------

ROWCACHE_MAX_ENTRIES = 150  # siehe Framebuffer.rect()/clear() - verhindert
                            # unbegrenztes Cache-Wachstum durch leicht
                            # wechselnde (Farbe, Breite)-Kombinationen
VIGNETTE_ENABLED = True    # dezente Randabdunkelung auf einfarbigen
                            # Flaechen (siehe Framebuffer.clear()) - rein
                            # optisch, kostet dank Zeilen-Cache nichts
                            # beim eigentlichen Zeichnen

class Framebuffer:
    # FBIO_WAITFORVSYNC (siehe linux/fb.h: _IOW('F', 0x20, __u32)) - wartet
    # auf den naechsten vertikalen Bildwechsel der Anzeige-Hardware, BEVOR
    # in den Framebuffer geschrieben wird. Ohne das kann ein Schreibvorgang
    # (egal ob flip() oder flip_rows()) mitten in einem laufenden Scanvorgang
    # der Hardware landen - der Bildschirm zeigt dann fuer einen Sekundenbruch-
    # teil einen Mix aus altem und neuem Bildinhalt ("Tearing"). Sichtbar wird
    # das z.B. als leicht verschobener, "doppelt belichtet" wirkender Text bei
    # der markierten Zeile (Nutzer-Rueckmeldung: Text ueberlappt beim
    # Scrollen). Je groesser der Schreibvorgang (volle Seite vs. einzelne
    # Zeile), desto laenger dauert er und desto wahrscheinlicher ein
    # sichtbarer Treffer mitten im Scan.
    FBIO_WAITFORVSYNC = 0x40044620

    def __init__(self):
        # BUGFIX Teil 2 (Nutzer-Rueckmeldung: "1 von 10 Faellen startet
        # nicht richtig, bleibt im OSD" - siehe frontend_boot.sh fuer
        # Teil 1/die volle Herleitung): selbst mit der grosszuegigeren
        # 120s-Wartezeit in frontend_boot.sh kann es in seltenen Faellen
        # noch vorkommen, dass MiSTer's eigener Uebergang vom OSD zum
        # Framebuffer im exakt falschen Sekundenbruchteil noch nicht
        # ganz abgeschlossen ist, wenn wir hier ankommen - das Oeffnen
        # des Geraets (oder das Lesen seiner Geometrie) schlaegt dann
        # kurzzeitig fehl, obwohl eine Sekunde spaeter alles bereit
        # waere. Bisher fuehrte das zu einem sofortigen, harten Absturz
        # (sauber geloggt, aber das Frontend erschien nie - das alte
        # OSD blieb einfach stehen). Fix: bis zu 5 Versuche mit 0.5s
        # Pause dazwischen (insgesamt max. 2.5s zusaetzliche Wartezeit,
        # nur im Fehlerfall - beim ERSTEN, ueblichen erfolgreichen
        # Versuch entsteht KEINE zusaetzliche Verzoegerung).
        last_error = None
        for attempt in range(5):
            try:
                self._read_geometry()
                self.fd = os.open(FBDEV, os.O_RDWR)
                break
            except OSError as e:
                last_error = e
                LOG("Framebuffer-Oeffnen fehlgeschlagen (Versuch %d/5): %s"
                    % (attempt + 1, e))
                time.sleep(0.5)
        else:
            raise last_error
        self._map()
        self._rowcache = {}
        self._rectcache = {}   # eigener Cache fuer rect() (siehe dort) -
                                # getrennt von _rowcache, damit dessen
                                # Obergrenze nicht die selten wechselnden,
                                # teuren Hintergrundmuster von clear() mitloescht
        self._glyphcache = {}
        self._textcache = {}          # (text, scale, fg, bg) -> Liste von Byte-Zeilen
        self._textcache_order = []
        self._TEXTCACHE_LIMIT = 400   # ~12MB bei typischen Labellaengen -
                                      # vertretbar auf einem MiSTer mit ~1GB RAM
        # None = noch nicht getestet, True/False = Ergebnis des ersten
        # Versuchs. Wird nur EINMAL probiert - unterstuetzt der Treiber es
        # nicht (ENOTTY/EINVAL o.ae.), schalten wir dauerhaft ab, statt bei
        # JEDEM Frame erneut einen fehlschlagenden ioctl-Aufruf zu riskieren.
        self._vsync_supported = None

    def _wait_vsync(self):
        """Wartet, falls moeglich, auf den naechsten vertikalen Bildwechsel -
        siehe FBIO_WAITFORVSYNC oben. Schlaegt der ioctl fehl (Treiber
        unterstuetzt es nicht), wird das dauerhaft vermerkt und nie wieder
        versucht - kostet dann nichts mehr, faellt einfach auf das bisherige
        Verhalten (ohne Vsync-Wartezeit) zurueck."""
        if self._vsync_supported is False:
            return
        try:
            fcntl.ioctl(self.fd, self.FBIO_WAITFORVSYNC, struct.pack("I", 0))
            self._vsync_supported = True
        except (OSError, AttributeError):
            self._vsync_supported = False

    def _read_geometry(self):
        w, h = open("/sys/class/graphics/fb0/virtual_size").read().split(",")
        self.width  = int(w)
        self.height = int(h)
        self.bpp    = int(open("/sys/class/graphics/fb0/bits_per_pixel").read())
        self.stride = int(open("/sys/class/graphics/fb0/stride").read())
        if self.bpp != 32:
            sys.exit("Nur 32bpp wird unterstuetzt, gefunden: %d" % self.bpp)
        self.size = self.stride * self.height

    def _map(self):
        self.mm = mmap.mmap(self.fd, self.size, mmap.MAP_SHARED,
                            mmap.PROT_READ | mmap.PROT_WRITE)
        self.buf = bytearray(self.size)

    def refresh_geometry(self):
        """Nach Rueckkehr aus einem Core neu einlesen - die Aufloesung
        kann sich geaendert haben (z.B. anderer Videomodus)."""
        old = (self.width, self.height, self.stride)
        self._read_geometry()
        if (self.width, self.height, self.stride) != old:
            try:
                self.mm.close()
            except Exception:
                pass
            self._map()
            self._rowcache.clear()

    @staticmethod
    def _vignette_row_variants(rgb, width, stride, levels=12, strength=0.30):
        """Vorberechnet `levels` unterschiedlich dunkle Varianten einer
        vollen Bildzeile in EINER Farbe - Grundlage fuer eine schnelle,
        zeilenbasierte Vignette (siehe clear()). NUR fuer Flaechen mit
        einer einzelnen Fuellfarbe geeignet (kein Bild), da eine ganze
        Zeile hier IMMER dieselbe Farbe hat - genau das macht die
        Kopie so billig (eine Slice-Zuweisung pro Zeile statt Pixel
        fuer Pixel).

        WICHTIG (Performance-Grund): eine echte, pixelgenaue radiale
        Vignette (mit Verlauf auch in X-Richtung, wie bei einem Foto)
        wurde direkt gemessen - ueber 1 Sekunde fuer eine einzelne
        1080p-Flaeche, selbst nur EINMALIG berechnet. Bei bis zu zwei
        Systemwechseln zwischen Hintergrundbildern (BgCache.LIMIT=2)
        haette das zu spuerbaren Haengern beim Navigieren gefuehrt -
        nicht vertretbar. Diese Zeilen-Variante ist rein vertikal
        (oben/unten dunkler, kein staerkerer Effekt in den Ecken) -
        optisch ein etwas einfacherer, aber immer noch deutlich
        hochwertiger wirkender Verlauf, dafuer um Groessenordnungen
        schneller (siehe _apply_vignette_rows())."""
        pad = b"\x00" * (stride - width * 4)
        r, g, b = rgb
        out = []
        for lvl in range(levels):
            f = 1.0 - strength * (lvl / max(1, levels - 1))
            drgb = (int(r * f), int(g * f), int(b * f))
            out.append(Framebuffer.px(drgb) * width + pad)
        return out

    @staticmethod
    def _apply_vignette_rows(out, height, stride, row_variants):
        """Setzt out (bytearray, bereits mit vollem Puffer-Speicher
        allokiert) zeilenweise aus den vorberechneten, unterschiedlich
        dunklen Varianten zusammen - Mitte hell, Rand oben/unten
        dunkler. Aufeinanderfolgende Zeilen mit derselben (quantisierten)
        Helligkeitsstufe werden zu einem Block zusammengefasst und per
        EINER Bytes-Multiplikation (variante * anzahl) statt einzelner
        Zeilen-Kopien geschrieben - deutlich weniger Einzeloperationen."""
        levels = len(row_variants)
        cy = height / 2.0
        y = 0
        while y < height:
            d = abs(y - cy) / cy if cy else 0.0
            lvl = min(levels - 1, int(d * d * (levels - 1)))
            run_start = y
            y += 1
            while y < height:
                d2 = abs(y - cy) / cy if cy else 0.0
                lvl2 = min(levels - 1, int(d2 * d2 * (levels - 1)))
                if lvl2 != lvl:
                    break
                y += 1
            run_len = y - run_start
            off = run_start * stride
            block = row_variants[lvl] * run_len
            out[off:off + len(block)] = block

    @staticmethod
    def px(rgb):
        r, g, b = rgb
        return bytes((b, g, r, 0))

    @staticmethod
    def _darken(rgb, factor=0.82):
        r, g, b = rgb
        return (int(r*factor), int(g*factor), int(b*factor))

    def clear(self, rgb):
        key = ("bg", rgb, self.width, self.height)
        bg = self._rowcache.get(key)
        if bg is None:
            if VIGNETTE_ENABLED:
                variants = self._vignette_row_variants(rgb, self.width, self.stride)
                bg = bytearray(self.stride * self.height)
                self._apply_vignette_rows(bg, self.height, self.stride, variants)
            else:
                row = self.px(rgb) * self.width
                pad = b"\x00" * (self.stride - self.width * 4)
                bg = (row + pad) * self.height
            self._rowcache[key] = bg
        self.buf[:] = bg

    def blend_rect(self, x, y, w, h, rgb, alpha):
        """Rechteck mit einer Farbe UEBERBLENDEN statt zu ueberschreiben -
        fuer Glow-/Schatten-Effekte. alpha=0..1 (0=keine Wirkung, 1=wie
        rect()). Kann NICHT gecacht werden (haengt vom vorhandenen
        Bildinhalt ab) - deshalb bewusst nur fuer kleine Bereiche
        (Glow-Ringe, Schatten), nicht fuer grosse Flaechen. Wie bei
        allen anderen Zeichenmethoden: schreibt nie mehr/weniger Bytes
        als der Zielbereich hat, um den Puffer nicht zu verschieben."""
        x = max(0, x); y = max(0, y)
        w = min(w, self.width - x); h = min(h, self.height - y)
        if w <= 0 or h <= 0 or alpha <= 0:
            return
        alpha = min(1.0, alpha)
        nb, ng, nr = rgb[2], rgb[1], rgb[0]  # BGRA-Reihenfolge im Puffer
        buflen = len(self.buf)
        need = w * 4
        for yy in range(y, y + h):
            off = yy * self.stride + x * 4
            end = off + need
            if end > buflen:
                continue
            row = bytearray(self.buf[off:end])
            for i in range(0, need, 4):
                row[i]   = int(row[i]   + (nb - row[i])   * alpha)
                row[i+1] = int(row[i+1] + (ng - row[i+1]) * alpha)
                row[i+2] = int(row[i+2] + (nr - row[i+2]) * alpha)
            if len(row) == need:
                self.buf[off:end] = row

    def blend_border(self, x, y, w, h, rgb, alpha, thickness=2):
        """Nur den RAND eines Rechtecks ueberblenden (vier duenne
        Streifen) statt der ganzen Flaeche - fuer Glow-Ringe deutlich
        billiger als blend_rect() auf die volle Flaeche, da nur der
        Umfang statt die Flaeche skaliert. Fuer KLEINE, bildschirm-
        unabhaengige Bereiche gedacht (z.B. Boxart-Rahmen/Schatten) -
        fuer breite, bildschirmfuellende Streifen (Listenmarkierung auf
        HDMI) stattdessen glow_border_fast() nutzen, siehe dort."""
        t = max(1, thickness)
        self.blend_rect(x, y, w, t, rgb, alpha)                    # oben
        self.blend_rect(x, y + h - t, w, t, rgb, alpha)             # unten
        self.blend_rect(x, y, t, h, rgb, alpha)                     # links
        self.blend_rect(x + w - t, y, t, h, rgb, alpha)             # rechts

    def glow_border_fast(self, x, y, w, h, base_bg, accent, alpha, thickness):
        """Schnelle Glow-Ring-Variante: statt jedes Pixel einzeln mit
        dem VORHANDENEN Bildinhalt zu mischen (blend_border, teuer bei
        breiten Bereichen), wird die Zielfarbe VORAB einmal berechnet
        (Grundfarbe + Akzent bei gegebenem Alpha) und dann ueber das
        normale, gecachte rect() gezeichnet. Auf breiten HDMI-Zeilen
        um ein Vielfaches schneller, weil rect() dieselbe Zeile fuer
        gleiche Breite wiederverwendet statt sie jedes Mal neu
        durchzurechnen. Nimmt an, dass der Hintergrund unter dem Ring
        etwa base_bg entspricht - bei aktivem Hintergrundbild kann die
        Farbe dadurch minimal abweichen, bewusster Kompromiss fuer
        Geschwindigkeit."""
        mixed = tuple(int(bg + (ac - bg) * alpha)
                      for bg, ac in zip(base_bg, accent))
        t = max(1, thickness)
        self.rect(x, y, w, t, mixed)
        self.rect(x, y + h - t, w, t, mixed)
        self.rect(x, y, t, h, mixed)
        self.rect(x + w - t, y, t, h, mixed)

    def blend_rect_fast(self, x, y, w, h, base_bg, color, alpha):
        """Wie blend_rect(), aber mit vorgemischter FESTER Farbe statt
        echter Pixel-fuer-Pixel-Mischung - fuer FLAECHEN (z.B. den
        Boxart-Schatten). Derselbe Trick wie glow_border_fast(): die
        Zielfarbe wird EINMAL berechnet statt pro Pixel, dann ueber
        das gecachte rect() gezeichnet. Wichtig bei groesseren
        Flaechen (z.B. schattenbreite = Cover-Breite) - echtes
        Pixel-Blending kostete hier auf HDMI bei einem Boxart-Schatten
        gemessen ueber 60% der gesamten Zeichenzeit einer Navigation
        (per cProfile bestaetigt), obwohl der Schatten selbst klein
        wirkt. Nimmt an, dass der Untergrund etwa base_bg entspricht -
        bei aktivem Hintergrundbild kann die Farbe dadurch leicht
        abweichen, bewusster Kompromiss fuer Geschwindigkeit."""
        mixed = tuple(int(bg + (c - bg) * alpha)
                      for bg, c in zip(base_bg, color))
        self.rect(x, y, w, h, mixed)

    def rect(self, x, y, w, h, rgb, scanlines=False):
        """scanlines=True: jede 2. Zeile dezent abgedunkelt (Retro-Look) -
        nur fuer reine Hintergrundflaechen, nicht fuer Markierungsbalken."""
        x = max(0, x); y = max(0, y)
        w = min(w, self.width - x); h = min(h, self.height - y)
        if w <= 0 or h <= 0:
            return
        # WICHTIG (Bugfix): _rectcache cacht nach (Farbe, EXAKTER Breite)
        # - bei leicht wechselnden Breiten (z.B. je nach Cover-
        # Seitenverhaeltnis, Glow-Ring-Position, Info-Textlaenge) sammelt
        # sich ueber viele Navigationen hinweg eine WACHSENDE Zahl nie
        # wieder verwendeter Eintraege an, die nie geloescht wird -
        # aehnliches Muster wie der in v1.32 behobene Pulsier-Cache-Bug,
        # nur an anderer Stelle. Per Differenzmessung bestaetigt: das
        # macht sich als spuerbare, mit der Zeit zunehmende Verzoegerung
        # bemerkbar. Einfache, sichere Absicherung: Cache bei
        # Ueberschreiten einer Obergrenze komplett leeren, statt einzelne
        # Eintraege aufwendig zu verwalten (LRU o.ae.) - der haeufige
        # Fall (dieselbe Farbe/Breite ueber mehrere Bilder hinweg, z.B.
        # Equalizer-Balken, Zeilen-Markierungen) bleibt dadurch weiterhin
        # schnell. Eigener Cache (nicht _rowcache), damit das Leeren
        # nicht die selten wechselnden, teuren Hintergrundmuster von
        # clear() mitreisst.
        if len(self._rectcache) > ROWCACHE_MAX_ENTRIES:
            self._rectcache.clear()
        key = (rgb, w)
        row = self._rectcache.get(key)
        if row is None:
            row = self.px(rgb) * w
            self._rectcache[key] = row
        row_dark = None
        if scanlines:
            key2 = (rgb, w, "dark")
            row_dark = self._rectcache.get(key2)
            if row_dark is None:
                row_dark = self.px(self._darken(rgb)) * w
                self._rectcache[key2] = row_dark
        for yy in range(y, y + h):
            off = yy * self.stride + x * 4
            use_row = row_dark if (scanlines and yy % 2) else row
            self.buf[off:off + w * 4] = use_row

    def rect_rounded(self, x, y, w, h, rgb, radius=None):
        """Wie rect(), aber mit abgerundeten Ecken. radius in Pixeln
        (bereits skaliert) - ohne Angabe ein kleiner, dezenter Wert.
        Kostet nur ein paar zusaetzliche, KUERZERE Randzeilen (die
        Eckenrundung), nicht die ganze Flaeche neu - der Mittelteil
        laeuft weiterhin ueber das normale, gecachte rect(). Die
        Einzugstabelle pro Randzeile wird nur einmal pro radius-Wert
        berechnet und mitgecacht, nicht bei jedem Aufruf neu."""
        x = max(0, x); y = max(0, y)
        w = min(w, self.width - x); h = min(h, self.height - y)
        if w <= 0 or h <= 0:
            return
        if radius is None:
            radius = max(1, min(w, h) // 8)
        radius = max(0, min(radius, w // 2, h // 2))
        if radius <= 0:
            self.rect(x, y, w, h, rgb)
            return
        key_ind = ("rounded_indent", radius)
        indents = self._rectcache.get(key_ind)
        if indents is None:
            indents = []
            r2 = radius * radius
            for ry in range(radius):
                dy = radius - ry - 1
                dx = 0
                while dx < radius and (radius - dx - 1) ** 2 + dy * dy <= r2:
                    dx += 1
                indents.append(radius - dx)
            self._rectcache[key_ind] = indents
        px = self.px(rgb)
        for i, indent in enumerate(indents):
            rw = w - 2 * indent
            if rw <= 0:
                continue
            row = px * rw
            yy_top = y + i
            yy_bot = y + h - 1 - i
            if 0 <= yy_top < self.height:
                off = yy_top * self.stride + (x + indent) * 4
                self.buf[off:off + rw * 4] = row
            if yy_bot != yy_top and 0 <= yy_bot < self.height:
                off = yy_bot * self.stride + (x + indent) * 4
                self.buf[off:off + rw * 4] = row
        mid_top = y + radius
        mid_h = h - 2 * radius
        if mid_h > 0:
            self.rect(x, mid_top, w, mid_h, rgb)

    def _glyph_row(self, bits, scale, fg, bg):
        key = (bits, scale, fg, bg)
        row = self._glyphcache.get(key)
        if row is None:
            f = self.px(fg); b = self.px(bg)
            row = b"".join((f if bits >> i & 1 else b) * scale for i in range(8))
            self._glyphcache[key] = row
        return row

    def text(self, x, y, s, scale=2, fg=None, bg=None):
        if fg is None:
            fg = C_TEXT
        if bg is None:
            bg = C_BG
        cw = 8 * scale
        if y + 8 * scale > self.height or y < 0 or x < 0:
            return
        # Nur so viele Zeichen wie auf den Schirm passen - identischer
        # Abschneidepunkt wie die alte, zeichenweise Fassung (die bei
        # gx + cw > self.width abgebrochen hat), nur vorab statt
        # mitten in der Schleife berechnet.
        maxch = (self.width - x) // cw
        if maxch <= 0:
            return
        if len(s) > maxch:
            s = s[:maxch]
        if not s:
            return
        # Ganze Text-Zeile cachen: Beim Scrollen/Neuzeichnen sind die
        # meisten Labels bereits bekannt (Spieltitel, Menuepunkte usw.)
        # - dann reicht ein fertiger Streifen zum Blitten, statt jedes
        # Mal wieder Buchstabe fuer Buchstabe (und Zeile fuer Zeile pro
        # Buchstabe) zusammenzusetzen. Groesster Hebel bei den reinen
        # Zeichenkosten, siehe Kopfkommentar-Changelog.
        key = (s, scale, fg, bg)
        strip = self._textcache.get(key)
        if strip is None:
            w4 = len(s) * cw * 4
            rows = [bytearray(w4) for _ in range(8 * scale)]
            for ci, ch in enumerate(s):
                code = ord(ch)
                if code > 127:
                    code = ord("?")
                xo = ci * cw * 4
                for gy in range(8):
                    grow = self._glyph_row(FONT8X8[code * 8 + gy], scale, fg, bg)
                    for rep in range(scale):
                        rows[gy * scale + rep][xo:xo + cw * 4] = grow
            strip = [bytes(r) for r in rows]
            self._textcache[key] = strip
            self._textcache_order.append(key)
            if len(self._textcache_order) > self._TEXTCACHE_LIMIT:
                self._textcache.pop(self._textcache_order.pop(0), None)
        w4 = len(strip[0])
        xo = x * 4
        for i, row in enumerate(strip):
            off = (y + i) * self.stride + xo
            self.buf[off:off + w4] = row

    def flip(self):
        # Erst auf den Vertical-Blank warten (falls unterstuetzt), DANN
        # schreiben - vermeidet Tearing bei der grossen Vollbild-Kopie.
        self._wait_vsync()
        # Direkte Slice-Zuweisung: mmap nimmt das bytearray ohne die
        # teure bytes()-Zwischenkopie (auf 1080p ~8 MB pro Frame).
        self.mm[:] = self.buf

    def flip_rows(self, y, h):
        """Nur einen Zeilenbereich auf den Schirm bringen (Laufschrift)."""
        y0 = max(0, y)
        y1 = min(self.height, y + h)
        if y1 <= y0:
            return
        self._wait_vsync()
        off = y0 * self.stride
        end = y1 * self.stride
        self.mm[off:end] = self.buf[off:end]

    def close(self):
        try:
            self.mm.close(); os.close(self.fd)
        except Exception:
            pass

# ----------------------------------------------------------------------------
# EINGABE: Tastatur + Gamepads parallel, mit Hotplug und exklusivem Grab
# ----------------------------------------------------------------------------

import select
import threading
import urllib.request
import urllib.parse
import urllib.error

EVIOCGRAB = 0x40044590
EV_SYN, EV_KEY, EV_ABS = 0, 1, 3
KEY_ESC, KEY_ENTER = 1, 28
KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT = 103, 108, 105, 106
KEY_F7 = 65
KEY_F6 = 64
KEY_F8, KEY_F9, KEY_F10, KEY_F11, KEY_F12 = 66, 67, 68, 87, 88
# Gamepad-Buttons (Linux-Standardcodes)
BTN_A, BTN_B, BTN_X, BTN_Y = 304, 305, 307, 308
KEY_Y = 21                   # Y key on keyboard
BTN_TL, BTN_TR = 310, 311
BTN_TL2, BTN_TR2 = 312, 313  # zusaetzliche Schultertasten (L2/R2), sofern vorhanden
BTN_SELECT, BTN_START, BTN_MODE = 314, 315, 316
BTN_DPAD_UP, BTN_DPAD_DOWN, BTN_DPAD_LEFT, BTN_DPAD_RIGHT = 544, 545, 546, 547
# Achsen
ABS_X, ABS_Y, ABS_HAT0X, ABS_HAT0Y = 0, 1, 16, 17
ABS_Z, ABS_RZ = 2, 5   # analoge L2/R2-Trigger bei vielen Xbox-artigen Pads
# Interne Pseudo-Codes fuer L2/R2, WENN sie analog (als Achse) statt als
# eigene Taste ankommen - negative Zahlen, damit sie garantiert nicht mit
# einem echten evdev-Code (immer >= 0) kollidieren. Werden genau wie ein
# normaler Tastencode im KEYMAP behandelt (siehe InputManager._translate()
# und read_raw_key()) - dadurch bleiben sie ganz normal frei belegbar,
# auch wenn L2/R2 auf dem jeweiligen Pad nicht als BTN_TL2/BTN_TR2 ankommen.
AXIS_L2, AXIS_R2 = -2, -5
EVENT_FMT  = "llHHi"
EVENT_SIZE = struct.calcsize(EVENT_FMT)

# Standard-evdev-Scancodes der Buchstabentasten (QWERTY-Zeilen) - fuer
# den Direktsprung per Tastatur: A druecken -> naechster Eintrag mit A.
LETTER_KEYS = {
    16: "Q", 17: "W", 18: "E", 19: "R", 20: "T", 21: "Y", 22: "U",
    23: "I", 24: "O", 25: "P",
    30: "A", 31: "S", 32: "D", 33: "F", 34: "G", 35: "H", 36: "J",
    37: "K", 38: "L",
    44: "Z", 45: "X", 46: "C", 47: "V", 48: "B", 49: "N", 50: "M",
}

# Tasten/Buttons -> logische Aktionen des Frontends
# Seit v1.11 bewusst schlank gehalten: Enter oeffnet/startet, ESC/B geht
# eine Ebene zurueck (bzw. fragt im Hauptmenue nach), hoch/runter
# navigiert einzeln, links/rechts springt seitenweise. Bild auf/ab und
# Pos1/Ende gibt es dafuer nicht mehr - die Schultertasten L/R sind
# jetzt einfach ein zweiter Weg fuer den Seitensprung (wie D-Pad
# links/rechts), statt eine eigene Buchstabensprung-Logik zu haben.
KEYMAP = {
    KEY_UP: "up", KEY_DOWN: "down", KEY_LEFT: "left", KEY_RIGHT: "right",
    KEY_ENTER: "ok", KEY_ESC: "exit",
    KEY_F12: "osd", KEY_F10: "back_fe", KEY_F9: None, KEY_F11: "random",
    KEY_F8: "favorite", BTN_TL2: "favorite", BTN_TR2: "favorite",
    AXIS_L2: "favorite", AXIS_R2: "favorite",
    KEY_F7: "completed",
    KEY_F6: "ra_showcase",
    BTN_A: "ok", BTN_START: "ok",
    BTN_B: "back", BTN_X: "back_fe",
    BTN_Y: "music_next", KEY_Y: "music_next",
    BTN_TL: "left", BTN_TR: "right",
    BTN_MODE: "osd", BTN_SELECT: "select",
    BTN_DPAD_UP: "up", BTN_DPAD_DOWN: "down",
    BTN_DPAD_LEFT: "left", BTN_DPAD_RIGHT: "right",
}
for _code, _ch in LETTER_KEYS.items():
    KEYMAP[_code] = "letter:" + _ch

# Schnappschuss der Standardbelegung (fuer "Auf Standard zuruecksetzen")
DEFAULT_KEYMAP = dict(KEYMAP)

def _load_custom_keymap():
    """Eigene Tastenbelegung laden und in KEYMAP einmischen (ueberschreibt
    einzelne Eintraege, der Rest bleibt Standard)."""
    try:
        data = json.load(open(KEYMAP_CUSTOM_FILE))
        for k, v in data.items():
            KEYMAP[int(k)] = v
    except (OSError, ValueError, TypeError):
        pass

_load_custom_keymap()

# Richtungs-Aktionen, die beim Halten wiederholt werden - sowohl
# hoch/runter (einzelne Position) als auch links/rechts (Seitensprung)
# beschleunigen beim Halten.
REPEAT_ACTIONS = {"up", "down", "left", "right"}
REPEAT_DELAY    = 0.40      # Sekunden bis zur ersten Wiederholung
REPEAT_INTERVAL = 0.14      # Start-Intervall, beschleunigt bis 0.05

def _absinfo(fd, axis):
    """min/max einer Achse per EVIOCGABS-ioctl auslesen."""
    buf = bytearray(24)
    fcntl.ioctl(fd, 0x80184540 + axis, buf)
    _val, amin, amax, _f, _fl, _res = struct.unpack("6i", buf)
    return amin, amax

class Device:
    def __init__(self, path, name, is_kbd):
        self.path = path
        self.name = name
        self.is_kbd = is_kbd
        self.fd = os.open(path, os.O_RDWR)
        self.grabbed = False
        self.axis = {}            # axis -> (min, max)
        self.axis_state = {}      # axis -> -1/0/1 (fuer Flankenerkennung)
        for ax in (ABS_X, ABS_Y, ABS_HAT0X, ABS_HAT0Y, ABS_Z, ABS_RZ):
            try:
                self.axis[ax] = _absinfo(self.fd, ax)
                self.axis_state[ax] = 0
            except OSError:
                pass

    def grab(self, on):
        try:
            fcntl.ioctl(self.fd, EVIOCGRAB, 1 if on else 0)
            self.grabbed = on
        except OSError:
            pass

    def close(self):
        try:
            self.grab(False)
            os.close(self.fd)
        except OSError:
            pass

def scan_devices():
    """Alle echten Input-Geraete finden (MiSTers virtuelles ueberspringen)."""
    devs = []
    try:
        blocks = open("/proc/bus/input/devices").read().split("\n\n")
    except OSError:
        return devs
    for b in blocks:
        if "event" not in b or "MiSTer virtual" in b:
            continue
        m = re.search(r"event(\d+)", b)
        n = re.search(r'N: Name="([^"]*)"', b)
        if not m:
            continue
        path = "/dev/input/event" + m.group(1)
        devs.append((path, n.group(1) if n else "?", "kbd" in b))
    return devs

class InputManager:
    RESCAN_EVERY = 3.0            # Sekunden - fuer Hotplug neuer Pads

    def __init__(self):
        self.devices = {}
        self.want_grab = False
        self.last_scan = 0.0
        self.held = None          # (key_id, aktion, naechste_zeit, intervall)
        self._last_input_mtime = None
        self.rescan(force=True)

    def rescan(self, force=False):
        # Billiger Schnellcheck: aendert sich /dev/input ueberhaupt? Neue
        # oder entfernte Geraete aendern die mtime des Ordners. Solange
        # die gleich bleibt (im Menue-Alltag praktisch immer), sparen wir
        # uns das teure Parsen von /proc/bus/input/devices - nur ein
        # einziger stat()-Syscall alle RESCAN_EVERY Sekunden statt
        # unnoetiger Dauerlast auf der eher schwachen CPU. Hotplug wird
        # weiterhin zuverlaessig erkannt, nur eben nicht teurer als noetig.
        self.last_scan = time.monotonic()
        try:
            mt = os.stat("/dev/input").st_mtime
        except OSError:
            mt = 0.0
        if not force and mt == self._last_input_mtime:
            return
        self._last_input_mtime = mt
        seen = set()
        for path, name, is_kbd in scan_devices():
            seen.add(path)
            if path not in self.devices:
                try:
                    d = Device(path, name, is_kbd)
                    d.grab(self.want_grab)
                    self.devices[path] = d
                    LOG("Geraet: %s '%s' kbd=%s achsen=%s"
                        % (path, name, is_kbd, sorted(d.axis)))
                except OSError as e:
                    LOG("Geraet %s nicht nutzbar: %s" % (path, e))
        for path in list(self.devices):
            if path not in seen:
                self.devices[path].close()
                del self.devices[path]

    def grab(self, on):
        LOG("grab(%s)" % on)
        self.want_grab = on
        for d in self.devices.values():
            d.grab(on)

    def _hold(self, key_id, act):
        if act in REPEAT_ACTIONS:
            self.held = (key_id, act, time.monotonic() + REPEAT_DELAY,
                         REPEAT_INTERVAL)

    def _release(self, key_id):
        if self.held and self.held[0] == key_id:
            self.held = None

    def _translate(self, dev, etype, code, value):
        if etype == EV_KEY:
            if code in (BTN_DPAD_UP, BTN_DPAD_DOWN,
                        BTN_DPAD_LEFT, BTN_DPAD_RIGHT):
                key_id = (dev.path, "k", code)
                if value == 1:
                    act = KEYMAP.get(code)
                    self._hold(key_id, act)
                    return act
                if value == 0:
                    self._release(key_id)
                return None
            act = KEYMAP.get(code)
            key_id = (dev.path, "key", code)
            if act in REPEAT_ACTIONS:
                # Wiederholbare Aktionen (Navigation) laufen über unsere
                # EIGENE kontrollierte, beschleunigende Wiederholung -
                # die Auto-Wiederholung der Tastatur selbst (value==2)
                # wird ignoriert, sonst staut sich das bei ARM-Tempo
                # und laeuft nach dem Loslassen noch Sekunden nach.
                if value == 1:
                    self._hold(key_id, act)
                    return act
                if value == 0:
                    self._release(key_id)
                return None
            if value == 1:
                return act
            return None
        if etype == EV_ABS and code in (ABS_Z, ABS_RZ) and code in dev.axis:
            # Analoger L2/R2-Trigger: Schwellwert-Erkennung (>50% =
            # "gedrueckt"), danach ganz normal ueber KEYMAP behandelt -
            # wie ein echter Tastencode frei belegbar (Pseudo-Code
            # AXIS_L2/AXIS_R2), inklusive derselben Wiederholungslogik
            # wie bei echten Tasten, falls die zugewiesene Aktion
            # wiederholbar ist (z.B. bei Belegung auf Navigation).
            amin, amax = dev.axis[code]
            span = max(1, amax - amin)
            rel = (value - amin) / span
            pressed = 1 if rel > 0.5 else 0
            if pressed == dev.axis_state.get(code, 0):
                return None
            dev.axis_state[code] = pressed
            pseudo_code = AXIS_L2 if code == ABS_Z else AXIS_R2
            key_id = (dev.path, "a2", code)
            act = KEYMAP.get(pseudo_code)
            if not pressed:
                self._release(key_id)
                return None
            if act in REPEAT_ACTIONS:
                self._hold(key_id, act)
                return act
            return act
        if etype == EV_ABS and code in dev.axis:
            amin, amax = dev.axis[code]
            if code in (ABS_HAT0X, ABS_HAT0Y):
                direction = -1 if value < 0 else (1 if value > 0 else 0)
            else:
                span = max(1, amax - amin)
                rel = (value - amin) / span
                direction = -1 if rel < 0.30 else (1 if rel > 0.70 else 0)
            if direction == dev.axis_state.get(code, 0):
                return None
            dev.axis_state[code] = direction
            key_id = (dev.path, "a", code)
            if direction == 0:
                self._release(key_id)
                return None
            if code in (ABS_HAT0X, ABS_X):
                act = "left" if direction < 0 else "right"
            else:
                act = "up" if direction < 0 else "down"
            self._hold(key_id, act)
            return act
        return None

    def read_action(self, timeout=None):
        """Blockierend (oder mit Timeout) auf die naechste logische
        Aktion warten. Geraete-Events haben IMMER Vorrang vor Halte-
        Wiederholungen, damit ein Loslassen nie verloren geht.

        BUGFIX (Nutzer-Rueckmeldung von echter Hardware: Bildschirm
        bleibt nach dem Start schwarz, ueberlebte sogar den v3.1-Fix,
        der flip()/VSync als Ursache ausschloss - also musste das
        eigentliche Haengenbleiben anderswo stecken): die Deadline-
        Pruefung stand bisher NUR am ENDE der Schleife. Schlaegt
        select.select() mit OSError fehl (z.B. ein kaputtes/abgezogenes
        Eingabegeraet), sprang der Code per "continue" DIREKT zurueck
        an den Schleifenanfang - UNTER UMGEHUNG der Deadline-Pruefung
        am Ende. Wiederholt sich der Fehler (z.B. weil rescan() dasselbe
        problematische Geraet immer wieder findet, ohne das
        zugrundeliegende Problem zu loesen), entsteht eine Endlosschleife,
        die die Zeitueberschreitung NIE prueft - unabhaengig vom
        uebergebenen timeout-Wert. Das erklaert vermutlich, warum der
        erste Fix (VSync in der Boot-Animation umgehen) allein nicht
        reichte: das eigentliche Haengenbleiben steckte in DIESER
        Funktion, nicht im Bildschirmaufbau selbst - read_action(timeout=
        ...) wird durch die neue Boot-Animation zum ALLERERSTEN MAL so
        frueh im Programmablauf aufgerufen, zu einem Zeitpunkt, an dem
        Eingabegeraete moeglicherweise noch nicht vollstaendig bereit
        sind.

        Fix: Deadline-Pruefung zusaetzlich an den ANFANG jeder
        Schleifenrunde verschoben - dadurch kann KEIN Pfad durch die
        Schleife (auch nicht nach einem continue) die Pruefung mehr
        umgehen. Selbst eine dauerhaft fehlschlagende select()-Abfrage
        kann die Funktion jetzt nicht mehr laenger als die angeforderte
        Zeit blockieren."""
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            now = time.monotonic()
            if deadline is not None and now >= deadline:
                return None
            if now - self.last_scan > self.RESCAN_EVERY:
                self.rescan()
            due = self.held is not None and now >= self.held[2]
            wait = 0.0 if due else self.RESCAN_EVERY
            if not due:
                if deadline is not None:
                    wait = min(wait, max(0.0, deadline - now))
                if self.held is not None:
                    wait = min(wait, max(0.0, self.held[2] - now))
            fds = {d.fd: d for d in self.devices.values()}
            if not fds:
                time.sleep(0.5)
            else:
                try:
                    r, _, _ = select.select(list(fds), [], [], wait)
                except OSError:
                    self.rescan()
                    continue
                got_event = False
                for fd in r:
                    dev = fds[fd]
                    try:
                        data = os.read(fd, EVENT_SIZE)
                    except OSError:          # Geraet abgezogen
                        self.rescan()
                        continue
                    if len(data) < EVENT_SIZE:
                        continue
                    got_event = True
                    _, _, etype, code, value = struct.unpack(EVENT_FMT, data)
                    act = self._translate(dev, etype, code, value)
                    if act:
                        return act
                if got_event:
                    continue      # erst die Warteschlange leeren, dann Repeat
            if self.held is not None and time.monotonic() >= self.held[2]:
                kid, act, _t, iv = self.held
                # Untergrenze bewusst bei 0.08s (12.5/s) statt zuvor 0.05s
                # (20/s) - auf HDMI dauert ein volles Neuzeichnen auf
                # schwacher ARM-Hardware laenger als 0.05s, wodurch sich
                # Eingaben stauen konnten (spuerbarer "Lag" beim Halten
                # einer Richtungstaste). CRT ist so schnell, dass es den
                # Unterschied nicht merkt - 12.5 Spruenge/Sekunde sind
                # immer noch sehr flott fuer eine kleine Liste.
                iv = max(0.08, iv * 0.85)
                self.held = (kid, act, time.monotonic() + iv, iv)
                return act
            if deadline is not None and time.monotonic() >= deadline:
                return None

    def read_raw_key(self, timeout=None, allow_axis_skip=False):
        """Blockierend auf den naechsten PHYSISCHEN Tastendruck warten
        und dessen rohen evdev-Code liefern - ignoriert KEYMAP. Fuer den
        Tastenbelegungs-Assistenten: so kann auch eine bisher unbelegte
        oder anders belegte Taste erfasst werden.

        allow_axis_skip=True: ein klarer Analogstick-/D-Pad-Ausschlag
        (egal in welche Richtung) wird als "diese Aktion funktioniert
        schon nativ ueber die Achse" gewertet und liefert die spezielle
        Rueckgabe "AXIS" statt eines Codes - der Aufrufer soll dann
        einfach zur naechsten Abfrage weitergehen, ohne etwas zu
        ueberschreiben. Ohne diese Erkennung wuerde der Assistent bei
        Pads, deren D-Pad als Achse (nicht als Taste) ankommt, bei der
        allerersten Abfrage endlos haengen bleiben."""
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            now = time.monotonic()
            if now - self.last_scan > self.RESCAN_EVERY:
                self.rescan()
            wait = self.RESCAN_EVERY
            if deadline is not None:
                wait = min(wait, max(0.0, deadline - now))
            fds = {d.fd: d for d in self.devices.values()}
            if not fds:
                time.sleep(0.3)
            else:
                try:
                    r, _, _ = select.select(list(fds), [], [], wait)
                except OSError:
                    self.rescan()
                    continue
                for fd in r:
                    dev = fds.get(fd)
                    if not dev:
                        continue
                    try:
                        data = os.read(fd, EVENT_SIZE)
                    except OSError:
                        self.rescan()
                        continue
                    if len(data) < EVENT_SIZE:
                        continue
                    _, _, etype, code, value = struct.unpack(EVENT_FMT, data)
                    if etype == EV_KEY and value == 1:
                        return code
                    if etype == EV_ABS and code in (ABS_Z, ABS_RZ) and code in dev.axis:
                        # Analoger L2/R2-Trigger - unabhaengig von
                        # allow_axis_skip erkennbar, damit sich JEDE
                        # Aktion (nicht nur Navigation) darauf legen
                        # laesst. Schwellwert wie beim eigentlichen
                        # Ablesen im Hauptbetrieb (siehe _translate()).
                        amin, amax = dev.axis[code]
                        span = max(1, amax - amin)
                        rel = (value - amin) / span
                        if rel > 0.5:
                            return AXIS_L2 if code == ABS_Z else AXIS_R2
                    if allow_axis_skip and etype == EV_ABS and code in dev.axis:
                        amin, amax = dev.axis[code]
                        if code in (ABS_HAT0X, ABS_HAT0Y):
                            direction = -1 if value < 0 else (1 if value > 0 else 0)
                        else:
                            span = max(1, amax - amin)
                            rel = (value - amin) / span
                            direction = -1 if rel < 0.30 else (1 if rel > 0.70 else 0)
                        if direction != 0:
                            return "AXIS"
            if deadline is not None and time.monotonic() >= deadline:
                return None

    COMBO_HOLD = 0.8          # Sekunden Start+Select halten

    KBD_COMBO_HOLD = 0.6      # Sekunden Esc halten (hidraw-Notausstieg) -
                              # bewusst laenger als bei Strg+Alt+Esc, da
                              # ein einzelnes Esc leichter mal kurz in
                              # einem spiel-eigenen Pause-Menue gedrueckt
                              # wird als eine Dreifach-Kombination

    def wait_game_exit(self):
        """Waehrend ein Core laeuft: warten, bis MiSTer zurueck im
        Menue ist, F10 gedrueckt wird, Start+Select lange genug
        gehalten werden, ODER Esc auf der Tastatur laenger gehalten
        wird - erkannt ueber die rohe HID-Ebene. Rueckgabe: "menu",
        "f10", "combo" oder "hid_combo".

        WICHTIG: F10/Start+Select werden ueber die normale evdev-Ebene
        gelesen, die MiSTer waehrend eines laufenden Cores exklusiv
        sperrt - vermutlich hat dieser Zweig dadurch in der Praxis nie
        tatsaechlich ausgeloest. Bleibt trotzdem als Absicherung
        bestehen. Esc laeuft stattdessen ueber /dev/hidrawX (siehe
        _find_keyboard_hidraws()).

        BUGFIX Runde 3 (per echter Nutzer-Log-Datei bestaetigt: manche
        Tastaturen legen MEHRERE hidraw-Schnittstellen unter demselben
        Namen an, z.B. eine "Boot"- und eine NKRO-Schnittstelle - die
        tatsaechlichen Tastendruecke koennen ueber eine ANDERE
        Schnittstelle laufen als die zuerst erkannte): _find_keyboard_
        hidraws() liefert jetzt eine LISTE aller Schnittstellen
        desselben Tastatur-Namens, ALLE werden hier gleichzeitig
        ueberwacht (kbd_fds statt kbd_fd) - welche davon tatsaechlich
        die Tasten sendet, muss dadurch nicht mehr erraten werden."""
        down = set()              # (geraetepfad, code) gedrueckter Tasten
        combo_since = None
        last_core_check = 0.0
        kbd_paths = _find_keyboard_hidraws()
        kbd_fds = {}               # fd -> True/False (Esc gerade gehalten?)
        kbd_fd_paths = {}          # fd -> Pfad (nur fuers Diagnose-Log)
        for kp in kbd_paths:
            try:
                fd = os.open(kp, os.O_RDONLY | os.O_NONBLOCK)
                kbd_fds[fd] = False
                kbd_fd_paths[fd] = kp
            except OSError as e:
                LOG("wait_game_exit: Oeffnen fehlgeschlagen fuer %s: %s" % (kp, e))
        LOG("wait_game_exit: %d von %d Schnittstelle(n) erfolgreich geoeffnet: %s"
            % (len(kbd_fds), len(kbd_paths), list(kbd_fd_paths.values())))
        # DIAGNOSE (Nutzerwunsch: Esc wird trotz korrekt gefundener und
        # geoeffneter Schnittstellen weiterhin nicht erkannt - naechster
        # Verdacht: das Report-FORMAT selbst, nicht mehr die Schnittstellen-
        # Auswahl. Manche NKRO-faehigen Tastaturen senden Tastendruecke als
        # BITMASKE statt als Byte-Array von Tastencodes - _hid_report_
        # has_esc() sucht aber nach dem blossen Byte-WERT 0x29 irgendwo im
        # Report, was bei einer Bitmaske nie zutrifft). Protokolliert die
        # rohen Bytes der ersten 30 tatsaechlich empfangenen Reports (ueber
        # alle Schnittstellen zusammen begrenzt, nicht pro Schnittstelle -
        # sonst koennte eine sehr "gespraechige" Schnittstelle das Log
        # fluten) - zeigt beim naechsten Testlauf schwarz auf weiss, wie
        # ein Tastendruck auf DIESER Tastatur tatsaechlich aussieht.
        #
        # BUGFIX (per echter Diagnose-Ausgabe von Sutefan bestaetigt):
        # ein GEMEINSAMES Budget ueber alle Schnittstellen hinweg war
        # ein Fehler - hidraw2 sendete ALLE 30 protokollierten Reports
        # (regelmaessig wechselndes Muster, sieht nach einem periodischen
        # Status-/Heartbeat-Signal aus, NICHT nach Tastendruecken), noch
        # bevor hidraw0/hidraw1 - die vermutlich tatsaechlichen
        # Tastatur-Schnittstellen - ueberhaupt einmal zu Wort kamen.
        # Jetzt: eigenes Budget PRO Schnittstelle, damit eine
        # "gespraechige" Schnittstelle die anderen nicht mehr verdraengt.
        kbd_diag_budget = {fd: 10 for fd in kbd_fds}
        kbd_combo_since = None
        try:
            while True:
                now = time.monotonic()
                if now - self.last_scan > self.RESCAN_EVERY:
                    self.rescan()
                    down = {k for k in down if k[0] in self.devices}
                if now - last_core_check > 0.7:
                    last_core_check = now
                    if current_core() == "MENU":
                        return "menu"
                if combo_since is not None and now - combo_since >= self.COMBO_HOLD:
                    return "combo"
                if (kbd_combo_since is not None
                        and now - kbd_combo_since >= self.KBD_COMBO_HOLD):
                    return "hid_combo"
                fds = {d.fd: d for d in self.devices.values()}
                for kfd in kbd_fds:
                    fds[kfd] = None
                if not fds:
                    time.sleep(0.5)
                    continue
                try:
                    r, _, _ = select.select(list(fds), [], [], 0.2)
                except OSError:
                    self.rescan()
                    continue
                for fd in r:
                    if fd in kbd_fds:
                        try:
                            data = os.read(fd, 64)
                        except OSError:
                            try:
                                os.close(fd)
                            except OSError:
                                pass
                            kbd_fds.pop(fd, None)
                            kbd_diag_budget.pop(fd, None)
                            continue
                        if kbd_diag_budget.get(fd, 0) > 0:
                            kbd_diag_budget[fd] -= 1
                            LOG("wait_game_exit DIAGNOSE (%s): %s"
                                % (kbd_fd_paths.get(fd, "?"), data.hex()))
                        kbd_fds[fd] = _hid_report_has_exit_key(data)
                        any_held = any(kbd_fds.values())
                        if any_held and kbd_combo_since is None:
                            kbd_combo_since = time.monotonic()
                        elif not any_held:
                            kbd_combo_since = None
                        continue
                    dev = fds.get(fd)
                    try:
                        data = os.read(fd, EVENT_SIZE)
                    except OSError:
                        self.rescan()
                        continue
                    if len(data) < EVENT_SIZE:
                        continue
                    _, _, etype, code, value = struct.unpack(EVENT_FMT, data)
                    if etype == EV_KEY and code == KEY_F10 and value == 1:
                        return "f10"
                    if etype == EV_KEY and code in (BTN_START, BTN_SELECT):
                        key = (dev.path, code)
                        if value == 1:
                            down.add(key)
                        elif value == 0:
                            down.discard(key)
                        # Kombo: Start UND Select am selben Geraet gedrueckt?
                        active = False
                        for path in set(p for p, _c in down):
                            codes = {c for p, c in down if p == path}
                            if BTN_START in codes and BTN_SELECT in codes:
                                active = True
                        if active and combo_since is None:
                            combo_since = time.monotonic()
                        elif not active:
                            combo_since = None
        finally:
            for fd in kbd_fds:
                try:
                    os.close(fd)
                except OSError:
                    pass

    def flush(self):
        for d in self.devices.values():
            fl = fcntl.fcntl(d.fd, fcntl.F_GETFL)
            fcntl.fcntl(d.fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
            try:
                while os.read(d.fd, EVENT_SIZE * 64):
                    pass
            except (BlockingIOError, OSError):
                pass
            finally:
                fcntl.fcntl(d.fd, fcntl.F_SETFL, fl)

    def inject(self, keycode):
        """Tasten-Event einspeisen (bevorzugt ueber die Tastatur).
        Funktioniert nur bei geloestem Grab.

        BUGFIX (Nutzer-Rueckmeldung): auf MiSTer-Setups mit einem
        Sony/PlayStation-artigen Controller wurde bisher IMMER dessen
        "Consumer Control"- bzw. "System Control"-Nebenschnittstelle
        getroffen statt der tatsaechlichen Tastatur - is_kbd basiert
        nur darauf, ob der Linux-Kernel IRGENDEINEN "kbd"-Handler an
        das Geraet gehaengt hat (siehe scan_devices()), was bei
        Controller-Nebenschnittstellen mit Medien-/Systemtasten
        ebenfalls zutrifft. Landete diese Nebenschnittstelle in der
        Aufzaehlung VOR der echten Tastatur, ging das injizierte F9
        (fuer den Wechsel in den Konsolenmodus) ins Leere - MiSTer
        blieb dauerhaft im eigenen Menue haengen, ohne dass unser Code
        abstuerzte (schwer zu finden, weil das Log ganz normal
        aussah). Deshalb jetzt ZUERST gezielt nach einem Geraet
        suchen, das "keyboard" im NAMEN traegt (deutlich zuverlaessigeres
        Signal als der generische Kernel-Handler) - nur wenn keins
        gefunden wird, auf die bisherige is_kbd-Heuristik zurueckfallen."""
        target = None
        for d in self.devices.values():
            if "keyboard" in d.name.lower():
                target = d
                break
        if target is None:
            for d in self.devices.values():
                if d.is_kbd:
                    target = d
                    break
        if target is None and self.devices:
            target = next(iter(self.devices.values()))
        if target is None:
            LOG("inject(%d): KEIN Zielgeraet!" % keycode)
            return
        LOG("inject(%d) -> %s" % (keycode, target.path))
        for value in (1, 0):
            ev  = struct.pack(EVENT_FMT, 0, 0, EV_KEY, keycode, value)
            syn = struct.pack(EVENT_FMT, 0, 0, EV_SYN, 0, 0)
            try:
                os.write(target.fd, ev + syn)
            except OSError:
                pass
            time.sleep(0.05)

    def close(self):
        for d in self.devices.values():
            d.close()
        self.devices = {}

# ----------------------------------------------------------------------------
# PNG-DECODER (Nutzerwunsch: RA-Erfolgs-Icons direkt im Frontend zeigen,
# nicht nur im Browser-Overlay, das PNGs von selbst versteht). Reines
# Standard-Python (zlib fuer die eigentliche Kompression - das macht der
# schwierige Teil bereits selbst), die PNG-eigene ZEILENFILTERUNG muss
# aber von Hand rekonstruiert werden - das ist der eigentliche Aufwand
# an einem PNG-Decoder.
#
# BEWUSST EINGESCHRAENKT (lieber None als ein falsches/kaputtes Bild):
# nur 8-Bit Farbtiefe, nicht interlaced, Farbtypen 0/2/3/4/6 - deckt
# praktisch jedes uebliche kleine Web-/Icon-Bild ab (fuer RA-Badges
# also die ueberwiegende Mehrheit der Faelle), NICHT aber 16-Bit-Tiefe,
# Adam7-Interlacing oder 1/2/4-Bit-Farbtiefen. Chunk-CRCs werden NICHT
# geprueft (vertrauenswuerdige Quelle: RAs eigenes CDN, keine
# Nutzereingabe) - das spart Aufwand, ohne die eigentliche Bild-
# Rekonstruktion zu beeintraechtigen.
def _paeth_predictor(a, b, c):
    """PNG-Paeth-Praediktor (siehe PNG-Spezifikation) - waehlt von den
    drei Nachbarn (links/oben/oben-links) den, der dem linearen
    Schaetzwert am naechsten liegt."""
    p = a + b - c
    pa = abs(p - a)
    pb = abs(p - b)
    pc = abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c

def _png_unfilter(raw, width, height, bpp):
    """Entfernt die PNG-Zeilenfilterung - jede Zeile im entpackten
    IDAT-Strom beginnt mit einem Filtertyp-Byte (0-4), gefolgt von den
    GEFILTERTEN (nicht den echten) Pixel-Bytes dieser Zeile. Liefert
    die rekonstruierten Rohpixel OHNE die Filter-Byte-Praefixe, oder
    None bei einem unbekannten Filtertyp oder zu kurzen Daten.
    bpp: Bytes pro Pixel (fuer den Filter-Rueckbezug - z.B. 4 bei
    RGBA/8-Bit, 1 bei Graustufen/8-Bit)."""
    stride = width * bpp
    row_len = stride + 1
    if len(raw) < row_len * height:
        return None
    out = bytearray(stride * height)
    prev_row = bytearray(stride)
    for y in range(height):
        off = y * row_len
        ftype = raw[off]
        line = raw[off + 1:off + 1 + stride]
        cur = bytearray(stride)
        if ftype == 0:      # None - unveraendert
            cur[:] = line
        elif ftype == 1:    # Sub - relativ zum Pixel LINKS
            for i in range(stride):
                a = cur[i - bpp] if i >= bpp else 0
                cur[i] = (line[i] + a) & 0xff
        elif ftype == 2:    # Up - relativ zum Pixel DARUEBER
            for i in range(stride):
                cur[i] = (line[i] + prev_row[i]) & 0xff
        elif ftype == 3:    # Average - Mittelwert aus links+oben
            for i in range(stride):
                a = cur[i - bpp] if i >= bpp else 0
                cur[i] = (line[i] + ((a + prev_row[i]) // 2)) & 0xff
        elif ftype == 4:    # Paeth - siehe _paeth_predictor()
            for i in range(stride):
                a = cur[i - bpp] if i >= bpp else 0
                c = prev_row[i - bpp] if i >= bpp else 0
                cur[i] = (line[i] + _paeth_predictor(a, prev_row[i], c)) & 0xff
        else:
            return None   # unbekannter Filtertyp - lieber abbrechen als raten
        out[y * stride:(y + 1) * stride] = cur
        prev_row = cur
    return bytes(out)

def decode_png(data):
    """Dekodiert eine PNG-Bilddatei (Bytes) zu (breite, hoehe,
    rgba_bytes) - fuer RA-Erfolgs-Icons direkt im Frontend. Liefert
    None bei JEDEM nicht unterstuetzten oder fehlerhaften Fall - NIE
    eine Ausnahme nach aussen (siehe Modul-Kopfkommentar fuer die
    bewussten Einschraenkungen)."""
    try:
        if not data.startswith(b"\x89PNG\r\n\x1a\n"):
            return None
        pos = 8
        width = height = bitdepth = colortype = None
        palette = None
        trns = None
        idat_parts = []
        n = len(data)
        while pos + 8 <= n:
            length = struct.unpack(">I", data[pos:pos + 4])[0]
            ctype = data[pos + 4:pos + 8]
            cstart = pos + 8
            cdata = data[cstart:cstart + length]
            pos = cstart + length + 4   # +4 = CRC, bewusst nicht geprueft
            if ctype == b"IHDR":
                if len(cdata) != 13:
                    return None
                (width, height, bitdepth, colortype,
                 comp, filt, interlace) = struct.unpack(">IIBBBBB", cdata)
                if comp != 0 or filt != 0 or interlace != 0:
                    return None   # Interlacing/exotische Kompression: nicht unterstuetzt
                if bitdepth != 8:
                    return None   # nur 8-Bit-Tiefe unterstuetzt
                if width <= 0 or height <= 0 or width * height > 4_000_000:
                    return None   # Groessen-Notbremse gegen kaputte/boesartige Header
            elif ctype == b"PLTE":
                palette = cdata
            elif ctype == b"tRNS":
                trns = cdata
            elif ctype == b"IDAT":
                idat_parts.append(cdata)
            elif ctype == b"IEND":
                break
        if width is None or not idat_parts:
            return None
        if colortype not in (0, 2, 3, 4, 6):
            return None

        channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[colortype]
        raw = zlib.decompress(b"".join(idat_parts))
        pixels = _png_unfilter(raw, width, height, channels)
        if pixels is None:
            return None

        # Zu RGBA vereinheitlichen, unabhaengig vom Quell-Farbtyp - so
        # muss der Rest des Frontends (blit() usw.) nur EIN Format
        # kennen, egal welcher PNG-Farbtyp reinkam.
        n_px = width * height
        out = bytearray(n_px * 4)
        if colortype == 6:      # RGBA schon direkt passend
            out[:] = pixels
        elif colortype == 2:    # RGB -> RGBA (Alpha immer deckend)
            for i in range(n_px):
                out[i * 4:i * 4 + 3] = pixels[i * 3:i * 3 + 3]
                out[i * 4 + 3] = 255
        elif colortype == 0:    # Graustufen -> RGBA
            for i in range(n_px):
                g = pixels[i]
                out[i * 4] = out[i * 4 + 1] = out[i * 4 + 2] = g
                out[i * 4 + 3] = 255
        elif colortype == 4:    # Graustufen+Alpha -> RGBA
            for i in range(n_px):
                g = pixels[i * 2]
                out[i * 4] = out[i * 4 + 1] = out[i * 4 + 2] = g
                out[i * 4 + 3] = pixels[i * 2 + 1]
        elif colortype == 3:    # Palette -> RGBA
            if not palette:
                return None
            for i in range(n_px):
                idx = pixels[i]
                p = idx * 3
                if p + 3 > len(palette):
                    return None
                out[i * 4:i * 4 + 3] = palette[p:p + 3]
                out[i * 4 + 3] = (trns[idx] if trns and idx < len(trns) else 255)
        return (width, height, bytes(out))
    except (struct.error, zlib.error, IndexError, ValueError):
        return None

# ----------------------------------------------------------------------------
# RA-ERFOLGS-ICONS (Badges) FUERS FRONTEND SELBST - baut auf decode_png()
# auf (siehe oben). Gleiches Grundprinzip wie ArtCache: dauerhaft als
# rohe PNG-Bytes lokal zwischengespeichert (Icons aendern sich nie mehr,
# sobald ein Erfolg veroeffentlicht ist), zusaetzlich die BEREITS
# DEKODIERTEN Bilder im Speicher gehalten (begrenzt, wie bei ArtCache).
# ----------------------------------------------------------------------------
BADGE_DIR = "/media/fat/frontend/ra_badges"
RA_BADGE_URL = "https://media.retroachievements.org/Badge/%s.png"

class BadgeCache:
    LIMIT = 60   # gleicher Gedanke wie ArtCache - Icons sind winzig,
                # koennte durchaus hoeher, aber kein Grund zur Eile

    def __init__(self):
        self.cache = {}   # badge_name -> (w, h, rgba) oder None
        self.order = []

    def get(self, badge_name):
        """Liefert (breite, hoehe, rgba) fuer ein RA-Badge, oder None,
        wenn der Name unbrauchbar ist oder das Icon nicht geladen/
        dekodiert werden konnte. Laedt/dekodiert bei Bedarf, danach
        aus dem Speicher-Cache."""
        if not badge_name or not re.match(r"^[A-Za-z0-9_-]+$", badge_name):
            return None   # kein Pfad-Trick moeglich, siehe _load_bytes()
        if badge_name in self.cache:
            return self.cache[badge_name]
        data = self._load_bytes(badge_name)
        result = decode_png(data) if data else None
        self.cache[badge_name] = result
        self.order.append(badge_name)
        if len(self.order) > self.LIMIT:
            old = self.order.pop(0)
            self.cache.pop(old, None)
        return result

    def _load_bytes(self, badge_name):
        """Rohe PNG-Bytes eines Badges - aus dem lokalen Dauer-Cache,
        falls vorhanden, sonst live von RA heruntergeladen und
        gespeichert. NIE eine Ausnahme nach aussen."""
        try:
            os.makedirs(BADGE_DIR, exist_ok=True)
        except OSError:
            pass
        path = os.path.join(BADGE_DIR, badge_name + ".png")
        try:
            with open(path, "rb") as f:
                return f.read()
        except OSError:
            pass
        try:
            req = urllib.request.Request(
                RA_BADGE_URL % badge_name,
                headers={"User-Agent": "MiSTerFrontend/1.0"})
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                if resp.status != 200:
                    return None
                data = resp.read()
        except (urllib.error.URLError, OSError, TimeoutError):
            return None
        try:
            with open(path, "wb") as f:
                f.write(data)
        except OSError:
            pass
        return data

BADGES = BadgeCache()

# ----------------------------------------------------------------------------
# ARTWORK (.art) UND METADATEN
# .art-Format: b"ART1" + uint16 Breite + uint16 Hoehe + zlib(BGRA-Rohpixel)
# Die Dateien werden am PC mit art_convert.py erzeugt - der MiSTer
# muss nur noch entpacken (zlib ist Standardbibliothek) und blitten.
# ----------------------------------------------------------------------------

class ArtCache:
    LIMIT = 60                       # max. Bilder im Speicher halten - moderat
                                      # erhoeht (vorher 40): die tolerante
                                      # Cover-Suche findet jetzt mehr Cover als
                                      # zuvor, wodurch der alte Wert beim Hin-
                                      # und-Herscrollen zu haeufigem erneuten
                                      # Dekodieren fuehrte. Bewusst NICHT so
                                      # stark erhoeht wie urspruenglich
                                      # vorgeschlagen (90) - bei grossen HD-
                                      # Covern (~4MB/Bild unkomprimiert) waere
                                      # das ein spuerbarer RAM-Batzen auf einem
                                      # MiSTer mit typischerweise ~1GB RAM.

    def __init__(self):
        self.cache = {}              # pfad -> (w, h, pixelbytes) oder None
        self.order = []
        self._defer_uncached = False # beim schnellen Scrollen: noch nicht
                                     # dekodierte Cover ueberspringen (siehe
                                     # get_scaled()/COVER_SETTLE)

    def get(self, path):
        if path in self.cache:
            return self.cache[path]
        # WICHTIG (Bugfix): "Datei existiert nicht" (FileNotFoundError,
        # eine OSError-Unterklasse) ist ein STABILER Fall - sicher
        # dauerhaft zu cachen, da sich das waehrend der Sitzung normal-
        # erweise nicht mehr aendert. Eine BESCHAEDIGTE oder noch
        # UNVOLLSTAENDIGE Datei (z.B. waehrend eines noch laufenden
        # Kopier-/Downloadvorgangs) ist dagegen ein moeglicherweise
        # VORUEBERGEHENDER Zustand - struct.error/zlib.error traten
        # bisher NICHT gefangen ("except OSError" allein deckt das
        # nicht ab, waere sonst ein Absturz gewesen) und wurden trotzdem
        # als "nicht gefunden" dauerhaft gecacht, was ein spaeteres
        # erneutes Laden verhinderte, selbst wenn die Datei danach
        # vollstaendig und gueltig vorlag. Deshalb: bei einem
        # unerwarteten Format-/Dekomprimierungsfehler NICHT cachen -
        # naechster Zugriff versucht es einfach erneut.
        art = None
        cache_result = True
        try:
            with open(path, "rb") as f:
                if f.read(4) == b"ART1":
                    w, h = struct.unpack("<HH", f.read(4))
                    pix = zlib.decompress(f.read())
                    if len(pix) == w * h * 4:
                        art = (w, h, pix)
        except FileNotFoundError:
            pass                     # stabil - Cache-Eintrag bleibt bestehen
        except OSError:
            cache_result = False    # z.B. Berechtigung/IO-Fehler - lieber erneut versuchen
        except (struct.error, zlib.error, ValueError):
            cache_result = False    # unvollstaendige/beschaedigte Datei - erneut versuchen
        if not cache_result:
            return art
        self.cache[path] = art
        self.order.append(path)
        if len(self.order) > self.LIMIT:
            old = self.order.pop(0)
            self.cache.pop(old, None)
        return art

    SCALED_LIMIT = 20   # moderat erhoeht (vorher 10), gleicher Grund wie LIMIT

    def _scaled_cache_put(self, key, result):
        if not hasattr(self, "scaled"):
            self.scaled = {}
            self.scaled_order = []
        self.scaled[key] = result
        self.scaled_order.append(key)
        if len(self.scaled_order) > self.SCALED_LIMIT:
            old = self.scaled_order.pop(0)
            self.scaled.pop(old, None)

    def get_scaled(self, path, max_w, max_h):
        _t0 = time.monotonic()
        r = self._get_scaled_impl(path, max_w, max_h)
        _dt = time.monotonic() - _t0
        if _dt > 0.025:
            LOG("PERF cover: %.0f ms (%s)" % (_dt * 1000, os.path.basename(path)))
        return r

    def _get_scaled_impl(self, path, max_w, max_h):
        """Bild in die verfuegbare Flaeche einpassen. Kleine Cover werden
        ganzzahlig hochskaliert (Pixel-Look). Cover, die groesser als die
        Box sind, werden seit v1.8.1 per Nearest-Neighbor VERKLEINERT statt
        unskaliert zu bleiben - sonst ragen sie ueber den reservierten
        Platz hinaus und ueberlappen den Info-Text darunter."""
        # Waehrend aktiv gescrollt wird: ein noch nicht dekodiertes Cover
        # NICHT hier (im Zeichen-/Scroll-Pfad) dekodieren - das ruckelt auf
        # der schwachen CPU. Stattdessen ueberspringen; kurz nach dem
        # letzten Tastendruck laedt die Idle-Nachzeichnung es nach (siehe
        # COVER_SETTLE in der Hauptschleife).
        if self._defer_uncached and path not in self.cache:
            return None
        base = self.get(path)
        if not base:
            return None
        w, h, pix = base
        if max_w <= 0 or max_h <= 0:
            return None
        if not hasattr(self, "scaled"):
            self.scaled = {}
            self.scaled_order = []

        if w <= max_w and h <= max_h:
            # Kein hartes Limit mehr wie in v1.8.1 (dort noch 4x) - seit
            # v1.9 hat die Boxart-Spalte deutlich mehr Platz, ein Deckel
            # von 4x liess kleine Cover unnoetig klein und von Leerraum
            # umgeben wirken. 10x ist grosszuegig genug, um jede Box zu
            # fuellen, aber immer noch klein genug, um den Speicher- und
            # Rechenaufwand des Nearest-Neighbor-Upscales im Rahmen zu
            # halten (Cache haelt ohnehin nur SCALED_LIMIT Bilder).
            scale = max(1, min(max_w // w, max_h // h, 10))
            if scale == 1:
                return base
            key = (path, "up", scale)
            if key in self.scaled:
                return self.scaled[key]
            sw, sh = w * scale, h * scale
            out = bytearray(sw * sh * 4)
            row_out = sw * 4
            for y in range(h):
                o = y * w * 4
                row = b"".join(pix[o + x*4:o + x*4 + 4] * scale
                               for x in range(w))
                base_off = y * scale * row_out
                for rep in range(scale):
                    off = base_off + rep * row_out
                    out[off:off + row_out] = row
            result = (sw, sh, bytes(out))
            self._scaled_cache_put(key, result)
            return result

        # Bild ist in mindestens einer Richtung groesser als die Box -
        # verkleinern statt es unskaliert ueberstehen zu lassen.
        scale = min(max_w / w, max_h / h)
        tw = max(1, int(w * scale))
        th = max(1, int(h * scale))
        key = (path, "down", tw, th)
        if key in self.scaled:
            return self.scaled[key]
        # WICHTIG (Bugfix): frueher eine einzelne 4-Byte-Zuweisung PRO
        # ZIEL-PIXEL in einer doppelt verschachtelten Schleife (bei
        # z.B. 480x600 Zielgroesse: 288.000 einzelne bytearray-Slice-
        # Zuweisungen!) - jede einzelne Python-Anweisung hat spuerbaren
        # Overhead. Per Differenzmessung bestaetigt: ~90ms fuer eine
        # einzelne Verkleinerung, genau der Fall bei jeder echten
        # Navigation zu einem neuen Spiel mit einem HD-Cover, das
        # nicht exakt in den verfuegbaren Platz passt. Jetzt wie bei
        # der Vergroesserung: pro Zeile EIN b\"\".join() (in C
        # implementiert, deutlich weniger Python-Interpreter-Overhead
        # pro Zeile) statt einzelner Zuweisungen pro Pixel.
        xmap = [min(w - 1, int(x / scale)) * 4 for x in range(tw)]
        out = bytearray(tw * th * 4)
        row_out = tw * 4
        for ty in range(th):
            sy = min(h - 1, int(ty / scale))
            srow = pix[sy * w * 4:(sy + 1) * w * 4]
            row_bytes = b"".join([srow[sx:sx + 4] for sx in xmap])
            out[ty * row_out:(ty + 1) * row_out] = row_bytes
        result = (tw, th, bytes(out))
        self._scaled_cache_put(key, result)
        return result

ART = ArtCache()

class BgCache:
    """Haelt pro System einen fertig komponierten Vollbild-Puffer
    (inkl. Stride-Padding), damit der Hintergrund beim Zeichnen nur
    noch per Blockkopie eingesetzt werden muss."""
    LIMIT = 2

    def __init__(self):
        self.cache = {}
        self.order = []

    def get(self, syskey, fb):
        key = (syskey, fb.width, fb.height, fb.stride)
        if key in self.cache:
            return self.cache[key]
        buf = None
        for fn in ("%s_%dx%d.art" % (syskey, fb.width, fb.height),
                   "%s.art" % syskey):
            art = ART.get(os.path.join(BG_BASE, fn))
            if art:
                buf = self._compose(art, fb)
                break
        self.cache[key] = buf
        self.order.append(key)
        if len(self.order) > self.LIMIT:
            self.cache.pop(self.order.pop(0), None)
        return buf

    @staticmethod
    def _compose(art, fb):
        w, h, pix = art
        base = Framebuffer.px(C_BG)
        row_bg = base * fb.width + b"\x00" * (fb.stride - fb.width * 4)
        out = bytearray(row_bg * fb.height)
        # Bild zentrieren, bei Ueberbreite mittig beschneiden
        sx = max(0, (w - fb.width) // 2)
        dx = max(0, (fb.width - w) // 2)
        cw = min(w, fb.width)
        sy = max(0, (h - fb.height) // 2)
        dy = max(0, (fb.height - h) // 2)
        ch = min(h, fb.height)
        for y in range(ch):
            so = ((sy + y) * w + sx) * 4
            do = (dy + y) * fb.stride + dx * 4
            out[do:do + cw * 4] = pix[so:so + cw * 4]
        return bytes(out)

BG = BgCache()

_art_index_cache = {}   # (basis_ordner, syskey) -> {Name ohne "NNN "-Praefix: Dateiname}

def _art_index(base_dir, syskey):
    """Index fuer <base_dir>/<syskey>: Name OHNE fuehrende "NNN "-Nummer
    -> tatsaechlicher Dateiname. Ermoeglicht Cover aus nummerierten
    (kuratierten) Sets wie "007 Super Mario Kart (USA).art", obwohl
    das Spiel intern nur "Super Mario Kart (USA)" heisst. Pro
    (Ordner, System) gecacht - wird nur beim ERSTEN Cache-Fehltreffer
    fuer ein System ueberhaupt aufgebaut (siehe art_path()), nicht bei
    jedem Cover-Aufruf."""
    key = (base_dir, syskey)
    idx = _art_index_cache.get(key)
    if idx is None:
        idx = {}
        try:
            for fn in os.listdir(os.path.join(base_dir, syskey)):
                if not fn.endswith(".art"):
                    continue
                base = fn[:-4]
                stripped = re.sub(r"^\d+\s+", "", base)
                if stripped != base and stripped not in idx:
                    idx[stripped] = fn
        except OSError:
            pass
        _art_index_cache[key] = idx
    return idx

def _art_path_in(base_dir, syskey, rom_basename):
    """Cover-Pfad innerhalb eines bestimmten Basisordners (ART_BASE
    oder ART_HD) - erst der exakte Name, sonst wird eine fuehrende
    "NNN "-Nummer im tatsaechlichen Dateinamen ignoriert (siehe
    _art_index()). Liefert IMMER einen Pfad zurueck (auch wenn er
    nicht existiert) - der Aufrufer prueft ohnehin schon selbst auf
    Existenz, hier nur der BESSERE Pfad-Kandidat."""
    exact = os.path.join(base_dir, syskey, rom_basename + ".art")
    if os.path.exists(exact):
        return exact
    fn = _art_index(base_dir, syskey).get(rom_basename)
    if fn:
        return os.path.join(base_dir, syskey, fn)
    return exact

def art_path(syskey, rom_basename):
    return _art_path_in(ART_BASE, syskey, rom_basename)

_meta_cache = {}
_mra_cache = {}

def mra_meta(path):
    """Jahr/Hersteller/Kategorie/Spieler aus einer MRA-Datei lesen."""
    if path in _mra_cache:
        return _mra_cache[path]
    meta = {}
    try:
        with open(path, "r", errors="replace") as f:
            head = f.read(4096)
        for tag, key in (("year", "year"), ("manufacturer", "manufacturer"),
                         ("category", "genre"), ("players", "players")):
            m = re.search(r"<%s>\s*([^<]+?)\s*</%s>" % (tag, tag), head,
                          re.I)
            if m:
                meta[key] = m.group(1)
    except OSError:
        pass
    _mra_cache[path] = meta
    if len(_mra_cache) > 200:
        _mra_cache.pop(next(iter(_mra_cache)))
    return meta

def get_meta(syskey, rom_basename):
    """Metadaten (players/year/genre) fuer ein Spiel, lazy geladen."""
    if syskey not in _meta_cache:
        data = {}
        try:
            with open(os.path.join(META_BASE, syskey + ".json")) as f:
                data = json.load(f)
        except (OSError, ValueError):
            pass
        _meta_cache[syskey] = data
    return _meta_cache[syskey].get(rom_basename, {})

# ----------------------------------------------------------------------------
# KATEGORIEN & AKTIONEN
# ----------------------------------------------------------------------------

_TAGS = re.compile(r"\s*[\(\[][^\)\]]*[\)\]]")

# Datentraeger-Marker (Disc 1/2, CD 2, Side B, Part 3 ...). Diese Klammer-
# Zusaetze duerfen NICHT wie Regions-Tags behandelt werden: sie
# unterscheiden echte, eigenstaendige Eintraege desselben Spiels. Ohne
# diese Ausnahme faenden "Spiel (Disc 1)" und "Spiel (Disc 2)" auf
# demselben Dedupe-Schluessel zusammen - Disc 2+ waere aus der Liste
# verschwunden und nicht mehr startbar.
_DISC = re.compile(r"[\(\[]\s*(?:disc|disk|cd|side|part|tape|track)\s*"
                   r"[0-9a-z]+\s*[\)\]]", re.I)

def display_name(full):
    """Klammer-Zusaetze fuer die Anzeige entfernen - Disc-/CD-Marker
    bleiben aber stehen, sonst waeren mehrteilige Spiele in der Liste
    nicht auseinanderzuhalten."""
    short = _TAGS.sub("", full).strip()
    m = _DISC.search(full)
    if m and short:
        short += " " + m.group(0).strip()
    return short if short else full

# Region-Prioritaet fuer die Dedupe-Logik beim Scannen - dieselbe
# Reihenfolge wie in mister_boxart.py/mister_gameinfo.py bei der
# Boxart-/Info-Zuordnung, damit alles konsistent dieselbe Region
# bevorzugt.
REGION_PRIORITY = ["(germany)", "(europe)", "(world)", "(usa)", "(japan)"]

def _region_rank(name):
    low = name.lower()
    for i, tag in enumerate(REGION_PRIORITY):
        if tag in low:
            return i
    return len(REGION_PRIORITY)

def _canonical_key(name):
    """Name ohne Klammer-Zusaetze, kleingeschrieben - fuer die Erkennung
    von Mehrfach-Regionen desselben Spiels ("Spiel (USA)" und
    "Spiel (Europe)" landen auf demselben Schluessel).

    Ausnahme: ein Disc-/CD-/Side-Marker bleibt Teil des Schluessels,
    damit mehrteilige Spiele (Disc 1/2/3) NICHT zusammengefasst und
    dadurch unerreichbar werden."""
    key = _TAGS.sub("", name).strip().lower()
    m = _DISC.search(name)
    if m:
        key += " " + re.sub(r"\s+", "", m.group(0).lower())
    return key

# Tags, die ein ROM als Beta/Prototyp/Demo/defekten Dump o.ae.
# kennzeichnen - werden beim Scannen ausgefiltert.
JUNK_TAGS = ("(beta", "(proto", "(demo", "(sample", "[b]",
            "(program", "(test", "(kiosk")
# BUGFIX/AENDERUNG (Nutzerwunsch: "Was ist mit ROM Hacks und Zelda
# Randomizer" - Spielhacks und Randomizer-Ausgaben wurden bisher
# GAR NICHT angezeigt): "(hack" stand bisher in dieser Liste und
# wurde damit komplett ausgefiltert, genau wie unfertige Beta-/Proto-
# Dumps. Anders als diese sind Hacks (und Randomizer-Ausgaben, die
# haeufig aehnlich getaggt werden) aber vollstaendige, spielbare
# Inhalte, die viele Nutzer bewusst suchen - keine unfertigen/
# kaputten Dumps. Deshalb aus der Ausschlussliste entfernt.
#
# BUGFIX Runde 2 (Nutzer-Rueckmeldung anhand eines echten Datei-
# Screenshots: "NES-Ordner zeigt nur 2 ROMs an, sind aber viel mehr"):
# "(unl)" und "(pirate" standen ebenfalls noch in dieser Liste - die
# Screenshot-Dateiliste zeigte, dass ein GROSSER TEIL einer typischen
# NES-Sammlung aus genau diesen Tags besteht (unzaehlige beliebte,
# VOLLSTAENDIGE Mehrfach-Cartridges/unlizenzierte Spiele, gerade im
# asiatischen Raum sehr verbreitet und kommerziell verkauft) - wurden
# bisher komplett wie kaputte Dumps behandelt und ausgeblendet, obwohl
# es sich um voll spielbare, oft gesuchte Inhalte handelt. Aus der
# Ausschlussliste entfernt, gleiche Begruendung wie bei "(hack" oben.
# "[b]" (explizit als fehlerhafter Dump markiert) bleibt bewusst
# bestehen - das ist ein echter Qualitaetsmangel, kein blosser
# Lizenzstatus.

def _is_junk(name):
    low = name.lower()
    return any(tag in low for tag in JUNK_TAGS)

# Rein japanische ROMs ausblenden (auf Wunsch - EU/USA reicht den
# meisten). Erkennt "(Japan)"/"[Japan]" und die abgekuerzte Variante
# "(J)" aus aelteren ROM-Sets. WICHTIG: Mehrfach-Region-Tags wie
# "(Japan, USA)" oder "(USA, Japan)" bleiben erhalten, da diese Version
# auch USA/Europa abdeckt - das Muster verlangt eine direkt schliessende
# Klammer OHNE weiteren Text/Komma dazwischen.
_JAPAN_ONLY = re.compile(r"[\(\[]\s*(?:japan|j)\s*[\)\]]", re.I)

def _is_japan_only(name):
    return bool(_JAPAN_ONLY.search(name))

# Bekannte Boot-/Test-/Demo-Dateien, die manche MiSTer-Verteilungen
# direkt in die ROM-Ordner legen (fuer den Hardware-Selbsttest). Haben
# zufaellig die richtige Endung (z.B. .chd/.gb/.gba) und wuerden sonst
# faelschlich als "Spiel" in der Liste auftauchen.
IGNORE_ROM_BASENAMES = {"boot", "boot1", "boot2", "mister-boot", "mister-demo"}

def nice_name(dirname):
    raw = dirname.lstrip("_")
    return NICE_NAMES.get(raw, raw.replace("_", " "))

RECENT_MARKER = ".frontend_recent"   # Marker-Datei, mit der ein externes
                            # Skript (z.B. TheRealSutefans "Recently
                            # Played"-Skript) einen _*-Ordner als Quelle
                            # kennzeichnet - siehe find_marked_recent_dir().

def _folder_items(d, by_mtime=False):
    """Startbare Items (.mra/.rbf/.mgl) eines _*-Ordners - wie scan_cores
    sie baut. Ausgelagert, damit auch der markierte Recently-Ordner
    dieselbe Logik nutzt.

    by_mtime=True sortiert nach Datei-mtime absteigend (neueste zuerst) -
    fuer den markierten "Zuletzt gespielt"-Ordner, dessen Skript die
    mtimes auf die jeweilige Spielzeit stempelt. Bei gleichen mtimes
    (Skript ohne Zeitstempel) faellt es auf alphabetisch zurueck."""
    files = (glob.glob(os.path.join(d, "*.mra")) +
             glob.glob(os.path.join(d, "*.rbf")) +
             glob.glob(os.path.join(d, "*.mgl")))
    if by_mtime:
        def _key(f):
            try:
                mt = os.path.getmtime(f)
            except OSError:
                mt = 0
            return (-mt, os.path.basename(f).lower())
        files = sorted(files, key=_key)
    else:
        files = sorted(files)
    items = []
    for f in files:
        name = os.path.splitext(os.path.basename(f))[0]
        name = re.sub(r"_\d{8}[a-zA-Z]?$", "", name)
        items.append((name, "core", f))
    return items

def find_marked_recent_dir():
    """Den _*-Ordner suchen, den ein externes Skript per RECENT_MARKER
    als Zuletzt-gespielt-Quelle kennzeichnet. Gibt den Pfad zurueck oder
    None. Ueber den Marker unabhaengig vom Ordnernamen - der ist im
    externen Skript frei konfigurierbar. Ohne ein solches Skript
    (Normalfall) existiert kein Marker irgendwo - diese Funktion liefert
    dann einfach None, und alles verhaelt sich wie bisher."""
    for d in sorted(glob.glob(os.path.join(BASE, "_*"))):
        if os.path.isdir(d) and os.path.exists(os.path.join(d, RECENT_MARKER)):
            return d
    return None

def scan_cores(skip_dir=None):
    """Alle /media/fat/_*-Ordner nach .rbf/.mra/.mgl durchsuchen.
    skip_dir wird ausgelassen (der markierte Recently-Ordner, der bereits
    separat als "Zuletzt gespielt" gefuehrt wird - sonst doppelt)."""
    cats = []
    skip_real = os.path.realpath(skip_dir) if skip_dir else None
    for d in sorted(glob.glob(os.path.join(BASE, "_*"))):
        if not os.path.isdir(d) or os.path.basename(d) in SKIP_DIRS:
            continue
        if skip_real and os.path.realpath(d) == skip_real:
            continue
        # .mgl mit aufnehmen: so tauchen MGL-Shortcut-Ordner (z.B. das
        # "Recently Played"-Skript) auf und sind direkt startbar - der
        # Start-Pfad (load_core) verarbeitet .mgl genauso wie .rbf/.mra.
        items = _folder_items(d)
        if items:
            # Arcade-Ordner bekommen ein Info-Panel (MRA-Metadaten)
            base = os.path.basename(d).lstrip("_").lower()
            syskey = "ARCADE" if "arcade" in base else None
            cats.append((nice_name(os.path.basename(d)), items, syskey))
    return cats

# BUGFIX (Nutzer-Rueckmeldung anhand einer echten Verzeichnisliste mit
# 3202 Dateien: "es werden immer noch nur zwei Spiele angezeigt" - TROTZ
# des vorherigen (unl)/(pirate)-Fixes): _games_signature() (siehe unten)
# ist bewusst NUR ein schneller Fingerabdruck basierend auf Ordner-
# Aenderungszeiten, keine Tiefensuche (Performance-Grund, siehe
# Kommentar dort). Aendert sich NUR unsere FILTER-LOGIK im Code (z.B.
# JUNK_TAGS), nicht aber die Dateien selbst, bleibt die Ordner-mtime
# UNVERAENDERT - der alte, noch mit der alten Logik erzeugte
# Cache-Eintrag wurde dadurch munter weiterverwendet, obwohl der Code
# laengst repariert war. Nur ein manueller Rescan (System -> Wartung)
# half bisher, JEDE zukuenftige Filter-Logik-Aenderung haette denselben
# Effekt gehabt. Fix: eine eigene Versionsnummer, die bei jeder
# Aenderung an der FILTER-/DEDUPE-Logik selbst (nicht bei jedem Code-
# Release) von Hand hochgezaehlt wird - fliesst mit in die Signatur
# ein, macht den Cache dadurch automatisch ungueltig, sobald sich die
# Auswertung selbst geaendert hat, ganz unabhaengig von Datei-mtimes.
SCAN_LOGIC_VERSION = 4   # 1 = Basis, 2 = "(unl)"/"(pirate)" nicht mehr Junk,
                         # 3 = OPTIONAL_GAME_SYSTEMS (SNES_Tracker-Core),
                         # 4 = SMW Hacks (games/SNES/SMW_HACKS)

def _games_signature():
    """Schneller Fingerabdruck der ROM-Ordner (ohne Tiefensuche):
    existierende Wurzeln + deren mtime. Aendert sich der Inhalt einer
    Wurzel direkt, aendert sich die Signatur; bei Aenderungen tief in
    Unterordnern hilft der System-Eintrag 'Spieleliste neu einlesen'.

    HINWEIS (v1.32 zurueckgerollt): Ein Zwischenstand hat versucht,
    hierfuer ALLE Unterordner rekursiv mit einzubeziehen, um Aende-
    rungen tief in Sammlungen (z.B. 'Favoriten') automatisch zu
    erkennen. Das hat sich bei einer echten, grossen Sammlung (v.a.
    ueber USB mit hoeherer Zugriffszeit als ein schneller lokaler
    Datentraeger) als deutlich zu langsam herausgestellt - der
    komplette Ordnerbaum wurde dadurch bei JEDEM Boot durchlaufen,
    bevor der Bildschirm ueberhaupt wechselt (Musik lief bereits,
    das Frontend blieb aber minutenlang unsichtbar). Zurueck auf die
    schnelle, nur-oberste-Ebene-Pruefung - das war der urspruengliche,
    bewusste Kompromiss: schneller Boot immer, dafuer Aenderungen tief
    in Unterordnern nur per manuellem Rescan erkannt.

    WICHTIG (v1.53): statt des ABSOLUTEN Pfads geht nur eine Ort-
    Kennung ("usb:" oder "fat:") + der relative Ordnername in die
    Signatur ein. Eine USB-Platte mountet nach einem Kaltstart nicht
    immer unter derselben Nummer (mal /media/usb0, mal /media/usb1) -
    mit dem absoluten Pfad haette sich die Signatur dadurch bei jedem
    Boot geaendert, obwohl sich am Inhalt nichts geaendert hat, und
    jedes Mal einen unnoetigen kompletten Neuscan ausgeloest. Sortiert,
    damit auch die Reihenfolge der Basispfade die Signatur nicht
    veraendert."""
    sig = []
    for base in GAMES_BASES:
        if not os.path.isdir(base):
            continue
        tag = "usb:" if "/media/usb" in base else "fat:"
        for _d, _sk, folders, _r, _e in GAME_SYSTEMS:
            for folder in folders:
                root = os.path.join(base, folder)
                try:
                    mtime = int(os.path.getmtime(root))
                except OSError:
                    continue
                sig.append((tag + folder, mtime))
        for _d, _sk, folders, _r, _e, _core in OPTIONAL_GAME_SYSTEMS:
            for folder in folders:
                root = os.path.join(base, folder)
                try:
                    mtime = int(os.path.getmtime(root))
                except OSError:
                    continue
                sig.append((tag + folder, mtime))
    # Core-Datei der optionalen Systeme selbst mit in die Signatur
    # aufnehmen (nicht nur den ROM-Ordner oben) - sonst wuerde ein
    # nachtraeglich installierter/entfernter SNES_Tracker-Core NICHT
    # erkannt, solange sich am ROM-Ordner nichts aendert, und die neue
    # Kategorie bliebe bis zum naechsten manuellen Rescan unsichtbar.
    for _d, _sk, _f, _r, _e, core_check_path in OPTIONAL_GAME_SYSTEMS:
        try:
            sig.append(("core:" + core_check_path,
                       int(os.path.getmtime(core_check_path))))
        except OSError:
            sig.append(("core:" + core_check_path, None))
    sig.sort(key=lambda t: (t[0], t[1] is None, t[1]))
    sig.append(("__scan_logic_version__", SCAN_LOGIC_VERSION))
    return sig

def _sig_expects_usb(sig):
    """True, wenn eine Signatur mindestens einen USB-Ordner enthaelt -
    genutzt, um zu entscheiden, ob sich das Warten auf einen USB-Mount
    ueberhaupt lohnt (siehe scan_games())."""
    return any(entry[0].startswith("usb:") for entry in sig)

def _node_to_json(node):
    return {"folders": {k: _node_to_json(v) for k, v in node["folders"].items()},
            "items": [[i0, i1, list(i2[:4]) + [list(i2[4])]] for i0, i1, i2 in node["items"]]}

def _node_from_json(data):
    return {"folders": {k: _node_from_json(v) for k, v in data["folders"].items()},
            "items": [(i0, i1, (i2[0], i2[1], i2[2], i2[3], tuple(i2[4])))
                     for i0, i1, i2 in data["items"]]}

def _cats_to_json(cats):
    return [[n, _node_to_json(node), sk] for n, node, sk in cats]

def _cats_from_json(data):
    return [(n, _node_from_json(node), sk) for n, node, sk in data]

def load_recent():
    """Liste der zuletzt gespielten Spiele laden - Rueckgabe im
    gleichen (label, kind, arg)-Format wie normale Kategorie-Eintraege,
    direkt startbar. Leere Liste, wenn noch nie etwas gestartet wurde
    oder die Datei fehlt/beschaedigt ist."""
    try:
        with open(RECENT_FILE) as f:
            data = json.load(f)
        return [(e["label"], "game", e["arg"]) for e in data]
    except (OSError, ValueError, KeyError, TypeError):
        return []

def _bare_game_name(label):
    """Loest aus einer Zuletzt-gespielt-Beschriftung den reinen
    Spielnamen heraus - fuer externe Listen (siehe find_marked_recent_
    dir()), deren Eintraege ein Core-/RA-Praefix vorne dran haben
    (z.B. TheRealSutefans "RA SNES - Chrono Trigger", Format
    "<Anzeige> - <Spielname>" mit dem Spielnamen NACH dem ERSTEN
    " - "). Ohne " - " im Label wird das Label unveraendert
    zurueckgegeben (unsere eigene load_recent()-Liste hat kein
    Praefix, braucht diese Behandlung also nicht)."""
    return label.split(" - ", 1)[1] if " - " in label else label

def find_continue_game():
    """Sucht das zuletzt gespielte Spiel, das noch NICHT als
    durchgespielt markiert ist - fuer die "Weiterspielen"-Vorschlag
    ganz oben im Hauptmenue (Nutzerwunsch: "genau hier bist du stehen-
    geblieben" statt nur eine chronologische Liste). Liefert (label,
    "game"/"core", arg) oder None, wenn nichts passt (z.B. alles
    bereits durchgespielt markiert, oder noch nie etwas gestartet).

    Bevorzugt die ueber RECENT_MARKER eingebundene externe Liste
    (TheRealSutefans "Last Played"-Skript), FALLS vorhanden - MiSTers
    eigene *_recent_1.cfg-Dateien erfassen JEDEN Spielstart, egal ob
    ueber unser Frontend, MiSTers eigenes Menue oder ein anderes Tool.
    Unsere eigene load_recent()-Liste kennt dagegen nur, was ueber
    UNSER Frontend gestartet wurde - waere sonst zunehmend veraltet
    gegenueber der darunter angezeigten "Zuletzt gespielt"-Liste,
    sobald ein solches externes Skript aktiv ist.

    WICHTIG beim Abgleich gegen die Durchgespielt-Markierung: die
    externe Liste hat Core-/RA-Praefixe im Label (z.B. "RA SNES -
    Chrono Trigger"), unsere Markierung speichert aber den REINEN
    Spielnamen ("Chrono Trigger") - ein direkter Vergleich wuerde nie
    treffen. Siehe _bare_game_name() fuer die Praefix-Behandlung.
    Ohne aktiven Marker unveraendert unsere eigene load_recent()."""
    completed = _load_completed_raw()
    marked_recent = find_marked_recent_dir()
    if marked_recent:
        for entry in _folder_items(marked_recent, by_mtime=True):
            if _bare_game_name(entry[0]) not in completed:
                return entry
        return None
    for entry in load_recent():
        label = entry[0]
        if label not in completed:
            return entry
    return None

def record_recent(label, arg):
    """Ein gestartetes Spiel oben in die 'Zuletzt gespielt'-Liste
    einreihen (Duplikate werden nach oben verschoben statt doppelt zu
    erscheinen - Erkennung ueber den Namen, nicht ueber arg: nach
    einer JSON-Speicherrunde werden verschachtelte Tupel zu Listen,
    ein direkter Tupel-Vergleich wuerde also nie zutreffen), auf
    RECENT_MAX Eintraege gekappt."""
    try:
        with open(RECENT_FILE) as f:
            data = json.load(f)
    except (OSError, ValueError):
        data = []
    data = [e for e in data if e.get("label") != label]
    data.insert(0, {"label": label, "arg": list(arg)})
    data = data[:RECENT_MAX]
    try:
        os.makedirs(os.path.dirname(RECENT_FILE), exist_ok=True)
        with open(RECENT_FILE, "w") as f:
            json.dump(data, f)
    except OSError:
        pass

def _load_favorites_raw():
    try:
        with open(FAVORITES_FILE) as f:
            return json.load(f)
    except (OSError, ValueError):
        return []

def load_favorites():
    """Favoriten laden - selbes (label, kind, arg)-Format wie
    load_recent(), direkt als eigene Kategorie nutzbar. Reihenfolge:
    zuletzt hinzugefuegt zuerst (wie bei 'Zuletzt gespielt'), aber OHNE
    Obergrenze - Favoriten sind eine bewusste, dauerhafte Auswahl,
    keine automatische Verlaufsliste."""
    return [(e["label"], "game", e["arg"]) for e in _load_favorites_raw()
            if "label" in e and "arg" in e]

def is_favorite(label):
    """Ob ein Spiel (per Name) aktuell als Favorit markiert ist - fuer
    die kleine Markierung in der Liste."""
    return any(e.get("label") == label for e in _load_favorites_raw())

def toggle_favorite(label, arg):
    """Favoritenstatus eines Spiels umschalten (per Name erkannt,
    genau wie bei 'Zuletzt gespielt' - aus demselben Grund: nach dem
    Speichern sind es Listen, kein direkter Tupel-Vergleich moeglich).
    Rueckgabe: True, wenn jetzt Favorit ist, sonst False."""
    data = _load_favorites_raw()
    if any(e.get("label") == label for e in data):
        data = [e for e in data if e.get("label") != label]
        now_fav = False
    else:
        data.insert(0, {"label": label, "arg": list(arg)})
        now_fav = True
    try:
        os.makedirs(os.path.dirname(FAVORITES_FILE), exist_ok=True)
        with open(FAVORITES_FILE, "w") as f:
            json.dump(data, f)
    except OSError:
        pass
    return now_fav

# NEUES FEATURE (Nutzer-Rueckfrage: "werden bei Weiterspielen und
# Zuletzt gespielt auch die richtigen Cores fuer die Spiele verwendet,
# womit sie zuletzt gestartet wurden?"): Antwort war NEIN - die
# bisherige Core-Wahl (Standard/RA) wurde nur SITZUNGS-lokal in
# self._ra_core_choice gemerkt, und zwar pro SYSTEM (z.B. "SNES"),
# nicht pro einzelnem Spiel, UND nur, wenn die echte Kategorie in
# DERSELBEN Sitzung schon einmal betreten wurde - startete man ein
# Spiel direkt aus "Weiterspielen"/"Zuletzt gespielt" heraus, griff
# das oft gar nicht, es lief still (und ohne Nachfrage) der
# Standard-Core, selbst wenn das Spiel zuletzt mit RA gestartet wurde.
#
# Fix: zusaetzlich zur bestehenden Sitzungs-Erinnerung eine
# PERSISTIERTE, pro einzelnem Spiel (nach Name) gespeicherte "zuletzt
# tatsaechlich verwendete Core-Wahl" - ueberlebt einen Neustart. Wird
# in der Hauptschleife als Rueckfallebene genutzt, wenn fuer das
# aktuelle System in DIESER Sitzung noch keine frische Wahl getroffen
# wurde (siehe Kommentar dort). Favoriten fragen bewusst IMMER neu
# (siehe dort) und nutzen diese Datei nur zum Schreiben, nicht zum
# Lesen.
def load_last_core_choice(label):
    """(rbf, setname) oder None - die zuletzt fuer GENAU DIESES Spiel
    (nach Namen) tatsaechlich verwendete Core-Wahl. None bedeutet
    sowohl "noch nie erfasst" als auch "zuletzt bewusst Standard-Core
    gewaehlt" - in beiden Faellen ist das Ergebnis (Standard-Core
    verwenden) identisch, die Unterscheidung waere ohne Nutzen."""
    try:
        with open(LAST_CORE_CHOICE_FILE) as f:
            data = json.load(f)
        v = data.get(label)
        return tuple(v) if v else None
    except (OSError, ValueError, AttributeError, TypeError):
        return None

def record_core_choice(label, ra_choice):
    """Speichert, welche Core-Wahl (ra_choice: (rbf, setname) oder
    None fuer Standard) beim letzten tatsaechlichen Start dieses
    Spiels verwendet wurde."""
    try:
        with open(LAST_CORE_CHOICE_FILE) as f:
            data = json.load(f)
    except (OSError, ValueError):
        data = {}
    data[label] = list(ra_choice) if ra_choice else None
    try:
        os.makedirs(os.path.dirname(LAST_CORE_CHOICE_FILE), exist_ok=True)
        with open(LAST_CORE_CHOICE_FILE, "w") as f:
            json.dump(data, f)
    except OSError:
        pass

def _wait_for_usb_stable(max_wait=10.0, poll=0.5, min_wait_if_none=3.0):
    """Kurz warten, falls USB-Laufwerke gerade erst einhaengen - nur
    relevant fuer den (seltenen) tatsaechlichen Scan-Fall, verzoegert
    NICHT den schnellen Cache-Treffer-Normalfall.

    Prueft nicht nur, OB der Mountpunkt existiert (das kann bei einer
    langsam hochlaufenden Festplatte schon der Fall sein, WAEHREND die
    Dateiliste dahinter noch nachzieht) - sondern die tatsaechliche
    Anzahl an Eintraegen in jedem USB-Basisordner (os.listdir). Erst
    wenn sich diese Anzahl zwischen zwei Abfragen nicht mehr aendert,
    gilt das Laufwerk als wirklich fertig eingehaengt.

    Rueckgabe (v1.53): drei moegliche Zustaende, damit der Aufrufer
    weiss, ob das Ergebnis vertrauenswuerdig genug zum Zwischen-
    speichern ist:
    - True  = mindestens ein USB-Pfad gefunden UND stabil - Ergebnis
      vollstaendig, cachen ist sicher.
    - None  = ueberhaupt kein USB im Spiel (Setup ohne USB-Laufwerk) -
      Ergebnis vollstaendig, cachen ist sicher.
    - False = ein USB-Mountpunkt wurde gesehen, ist aber bis zum
      Zeitlimit nicht stabil geworden - das Scan-Ergebnis KOENNTE
      unvollstaendig sein, cachen ist NICHT sicher (siehe scan_games()).

    Hintergrund: seit v1.48 passiert der Bildschirmwechsel VOR dem
    Scan (behebt das Haengenbleiben im MiSTer-OSD) - das aendert aber
    nichts daran, WANN der Scan selbst startet. Laeuft er, bevor ein
    USB-Laufwerk nach einem Kaltstart wirklich fertig eingehaengt ist,
    fehlen dessen Spiele im Ergebnis."""
    usb_candidates = [b for b in GAMES_BASES if "/media/usb" in b]
    if not usb_candidates:
        return None

    def snapshot():
        found = False
        total = 0
        for b in usb_candidates:
            if os.path.isdir(b):
                found = True
                try:
                    total += len(os.listdir(b))
                except OSError:
                    pass
        return found, total

    t0 = time.monotonic()
    last_total = None
    stable_streak = 0
    while True:
        elapsed = time.monotonic() - t0
        found, total = snapshot()
        if elapsed >= max_wait:
            LOG("_wait_for_usb_stable: Zeitlimit (%.1fs) erreicht, fahre trotzdem fort"
               % max_wait)
            # Beim Zeitlimit unterscheiden: ist ueberhaupt ein
            # Mountpunkt da? Wenn ja, ist er evtl. nur noch nicht
            # stabil - trotzdem unsicher, also nicht cachen (False).
            # Wenn gar keiner kam, ist es ein Setup ohne USB (None).
            return False if found else None
        # BUGFIX (Nutzer-Rueckmeldung): ein durchgehend LEERER, aber
        # STABILER Ordner (Anzahl bleibt bei 0) wurde bisher NIE als
        # stabil erkannt, weil "has_content" das ausdruecklich
        # voraussetzte - nur ein durchgehend GEFUELLTER Ordner konnte
        # jemals "stabil" werden. MiSTer legt aber haeufig leere
        # /media/usb0, /media/usb1 usw. als Platzhalter an, VOELLIG
        # unabhaengig davon, ob dort tatsaechlich ein USB-Laufwerk
        # angeschlossen ist. Bei so einem Setup blieb die Anzahl immer
        # bei 0, "stable_streak" wurde nie hochgezaehlt, das Zeitlimit
        # wurde dadurch IMMER erreicht - das Scan-Ergebnis wurde NIE
        # gecacht, die Spieleliste wurde bei JEDEM Start komplett neu
        # gescannt. Jetzt zaehlt auch eine durchgehend stabile Null als
        # stabil (mit etwas mehr Vorsicht: doppelt so viele
        # aufeinanderfolgende Abfragen wie bei echtem Inhalt, damit ein
        # Laufwerk, das gerade erst zu befuellen beginnt, nicht zu
        # frueh faelschlich als "leer und fertig" gilt).
        if total == last_total:
            stable_streak += 1
            required = 2 if total > 0 else 4
            if stable_streak >= required:
                LOG("_wait_for_usb_stable: USB-Inhalt stabil (%d Eintraege) nach %.1fs"
                   % (total, elapsed))
                return True if total > 0 else None
        else:
            stable_streak = 0
        if not found and elapsed >= min_wait_if_none:
            return None
        last_total = total
        time.sleep(poll)

# ----------------------------------------------------------------------------
# NETZWERK/NAS-WARTEOPTION (Nutzerwunsch): liegen die ROMs auf einem
# Netzlaufwerk (NAS, ueber CIFS/SMB oder NFS eingebunden - MiSTer haengt
# das typischerweise unter /media/fat/cifs ein bzw. blendet es direkt in
# die games-Ordner ein, siehe cifs_mount.sh), kann der Scan starten,
# BEVOR die Verbindung wirklich steht - das Ergebnis (leer oder
# unvollstaendig) wuerde dann sogar dauerhaft gecacht werden. Standard
# AUS (die meisten Nutzer haben SD-Karte/USB, fuer die das nur unnoetig
# verzoegern wuerde) - NUR fuer NAS-Nutzer per Option einschaltbar.
NETWORK_WAIT_FILE = "/media/fat/frontend/network_wait"

def network_wait_enabled():
    """Liest die Einstellung "beim Start auf Netzwerk/NAS warten" -
    Standard NEIN."""
    try:
        with open(NETWORK_WAIT_FILE) as f:
            return f.read().strip().lower() in ("yes", "1", "ja", "true")
    except OSError:
        return False

def save_network_wait(enabled):
    try:
        os.makedirs(os.path.dirname(NETWORK_WAIT_FILE), exist_ok=True)
        with open(NETWORK_WAIT_FILE, "w") as f:
            f.write("yes" if enabled else "no")
    except OSError:
        pass

def _has_network_mount():
    """True, wenn eine Netzwerk-Freigabe (CIFS/NFS) gemountet ist - das
    eigentliche Signal, dass das NAS jetzt wirklich da ist. Uebernommener
    Vorschlag - siehe _wait_for_network_ready()."""
    try:
        with open("/proc/mounts") as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 3 and parts[2] in (
                        "cifs", "smb3", "smbfs", "nfs", "nfs4"):
                    return True
    except OSError:
        pass
    return False

def _wait_for_network_ready(max_wait=45.0, poll=0.5):
    """NUR aktiv, wenn network_wait_enabled() - sonst sofortige
    Rueckkehr (kein Einfluss auf den ganz ueberwiegenden Regelfall SD-
    Karte/USB).

    ERWEITERT (uebernommener Vorschlag - loest eine Luecke der
    urspruenglichen Fassung): die vorherige Version wartete nur auf
    "irgendeine Netzwerkverbindung" und dann auf einen stabilen Inhalt
    von GAMES_BASES - GAMES_BASES war aber beim Modul-Import bereits
    (leer) eingefroren, BEVOR das NAS ueberhaupt gemountet war, und ein
    schon stabiler, aber rein LOKALER Ordner (nur Cores, kein NAS)
    konnte das Warten faelschlich vorzeitig beenden lassen. Jetzt wird
    zusaetzlich echt geprueft, ob eine CIFS/NFS-Freigabe TATSAECHLICH
    gemountet ist (_has_network_mount()) - erst NACHDEM das gesehen
    wurde, zaehlt ein stabiler Inhalt. GAMES_BASES wird ausserdem bei
    jeder Pruefung sowie am Ende neu ermittelt (_discover_games_bases()),
    damit ein erst waehrend der Wartezeit erscheinendes NAS-Mount auch
    tatsaechlich erfasst wird."""
    if not network_wait_enabled():
        return
    global GAMES_BASES
    t0 = time.monotonic()
    while not _has_network():
        if time.monotonic() - t0 >= max_wait:
            LOG("_wait_for_network_ready: keine Netzwerkverbindung nach %.0fs - fahre trotzdem fort"
               % max_wait)
            GAMES_BASES = _discover_games_bases()
            return
        time.sleep(poll)

    def snapshot():
        # Wurzeln JEDES Mal neu ermitteln - erfasst ein erst jetzt
        # erscheinendes NFS/CIFS-Mount (GAMES_BASES ist eingefroren).
        total = 0
        for b in _discover_games_bases():
            if os.path.isdir(b):
                try:
                    total += len(os.listdir(b))
                except OSError:
                    pass
        return total

    last_total = None
    stable_streak = 0
    saw_mount = False
    while True:
        elapsed = time.monotonic() - t0
        if elapsed >= max_wait:
            LOG("_wait_for_network_ready: Zeitlimit (%.0fs) erreicht, fahre trotzdem fort"
               % max_wait)
            break
        if _has_network_mount():
            saw_mount = True
        total = snapshot()
        # Erst als fertig gelten, wenn das NAS-Mount GESEHEN wurde - sonst
        # bricht der schon stabile LOKALE Ordner (nur Cores) das Warten ab,
        # bevor das NAS ueberhaupt gemountet ist.
        if saw_mount and total == last_total:
            stable_streak += 1
            required = 2 if total > 0 else 4   # bei leer vorsichtiger, siehe _wait_for_usb_stable()
            if stable_streak >= required:
                LOG("_wait_for_network_ready: NAS gemountet, Inhalt stabil (%d Eintraege) nach %.1fs"
                   % (total, elapsed))
                break
        else:
            stable_streak = 0
        last_total = total
        time.sleep(poll)
    GAMES_BASES = _discover_games_bases()

def scan_games(force=False, progress_cb=None):
    """ROM-Listen laden - aus dem Cache, wenn er noch passt.
    progress_cb(i, total, name): wird NUR beim tatsaechlichen Scannen
    von der Platte aufgerufen (nicht beim schnellen Cache-Treffer) -
    normale Boots (Cache passt) bleiben also unveraendert schnell,
    nur der seltene "erster Start"/"ROMs geaendert"-Fall zeigt Fortschritt."""
    sig = _games_signature()
    cached_sig = None
    data = None
    if not force:
        try:
            with open(GAMES_CACHE) as f:
                data = json.load(f)
            cached_sig = [tuple(s) for s in data["sig"]]
            if cached_sig == sig:
                LOG("Spieleliste aus Cache (%d Systeme)"
                    % len(data["cats"]))
                return _cats_from_json(data["cats"])
        except (OSError, ValueError, KeyError, IndexError, TypeError):
            cached_sig = None
            data = None

    usb_ready = None
    waited_already = False
    # Cache passt (noch) nicht. Haeufigster Grund bei einem KALTSTART:
    # die USB-Platte war in dem Moment, in dem die Signatur oben
    # gebildet wurde, schlicht noch nicht gemountet - die aktuelle
    # Signatur hat dann keine USB-Ordner, der Cache (vom letzten Scan
    # MIT USB) aber schon. Nur in genau diesem Fall lohnt sich das
    # Warten VOR einem kompletten Neuscan: erwartet der Cache USB,
    # sehen wir aber noch keines, dann warten und erneut vergleichen.
    # SD-only-Systeme (Cache ohne USB) und warme Boots (Signatur passt
    # sofort) warten hier gar nicht.
    if (not force and cached_sig is not None
            and _sig_expects_usb(cached_sig) and not _sig_expects_usb(sig)):
        LOG("scan_games: Cache erwartet USB, noch nicht gemountet - warte")
        usb_ready = _wait_for_usb_stable()
        waited_already = True
        sig = _games_signature()
        if cached_sig == sig:
            LOG("Spieleliste aus Cache nach USB-Mount (%d Systeme)"
                % len(data["cats"]))
            return _cats_from_json(data["cats"])

    if not waited_already:
        usb_ready = _wait_for_usb_stable()
    cats = _scan_games_disk(progress_cb)

    # usb_ready: True = USB sauber eingehaengt, None = gar kein USB im
    # Spiel (beides -> Ergebnis vollstaendig, cachen ok). False = ein
    # USB-Mountpunkt war da, wurde aber nicht rechtzeitig stabil - das
    # Ergebnis KOENNTE unvollstaendig sein. Dann NICHT cachen, sonst
    # bliebe eine Luecke dauerhaft bestehen (der Cache passt beim
    # naechsten Boot ja wieder) - ohne Cache scannt der naechste Boot
    # einfach erneut, bis die Platte einmal rechtzeitig bereit war.
    if usb_ready is False:
        LOG("scan_games: USB nicht sicher bereit - Ergebnis wird NICHT gecacht")
        return cats

    sig = _games_signature()
    try:
        with open(GAMES_CACHE, "w") as f:
            json.dump({"sig": [list(s) for s in sig],
                       "cats": _cats_to_json(cats)}, f)
    except OSError:
        pass
    return cats

def _wrap_flat(items_list):
    """Eine bestehende flache Liste (Scripts/System/Cores/Zuletzt
    gespielt) als Baumknoten ohne Unterordner einwickeln - macht alle
    Kategorien einheitlich zu Baumknoten, der Rest des Codes muss
    dadurch nicht zwischen 'flacher Liste' und 'Baum' unterscheiden."""
    return {"folders": {}, "items": items_list}

def _count_tree_items(node):
    """Zaehlt rekursiv alle Eintraege in einem Baumknoten - auch in
    verschachtelten Unterordnern (Nutzerwunsch: die Kategorien
    "Sammlungen"/"RA-Erfolgsjaeger" zeigten im Hauptmenue selbst keine
    Anzahl, man musste erst reingehen um zu sehen ob ueberhaupt was
    drinsteckt). Nur fuer die kleinen, abgeleiteten Kategorien gedacht
    (Sammlungen/RA-Erfolgsjaeger haben wenige Dutzend Eintraege) - fuer
    die grossen ROM-Kategorien waere das zu teuer, dort zaehlen wir
    bewusst nicht."""
    total = len(node.get("items", ()))
    for sub in node.get("folders", {}).values():
        total += _count_tree_items(sub)
    return total

def _empty_node():
    """Leerer Baumknoten: {'folders': {Name: Knoten, ...}, 'items':
    [(label,kind,arg), ...]}. Wird fuer ALLE Kategorien einheitlich
    genutzt - auch fuer Scripts/System/Cores/Zuletzt-gespielt, die
    einfach 'folders'={} bekommen (flach, wie bisher)."""
    return {"folders": {}, "items": []}

def _merge_node(dst, src):
    """src-Knoten in dst hineinmischen - noetig, falls derselbe
    Systemordner (z.B. 'SNES') von mehreren GAMES_BASES aus existiert
    (SD-Karte UND ein USB-Laufwerk)."""
    for name, sub in src["folders"].items():
        if name in dst["folders"]:
            _merge_node(dst["folders"][name], sub)
        else:
            dst["folders"][name] = sub
    dst["items"].extend(src["items"])

def _dedupe_items(raw_items):
    """BUGFIX/AENDERUNG (Nutzerwunsch: "mehrere Spielversionen muessen
    auch im Menue zur Auswahl stehen, PAL/NTSC etcpp"): frueher wurde
    hier pro kanonischem Namen (ohne Region-/Versions-Tags) NUR die
    Kopie mit der besten Region behalten (Germany > Europe > World >
    USA > Japan, siehe REGION_PRIORITY), alle anderen Versionen
    verschwanden komplett aus der Liste - nicht mehr auswaehlbar,
    unabhaengig davon, ob man gezielt die PAL- oder NTSC-Fassung
    wollte. Jetzt bleiben ALLE gefundenen Versionen erhalten, nur
    alphabetisch sortiert - REGION_PRIORITY/_region_rank() bleiben im
    Code bestehen (werden an anderer Stelle noch fuer die Boxart-/
    Info-Zuordnung gebraucht), wirken sich hier aber nicht mehr
    aus."""
    items = list(raw_items)
    items.sort(key=lambda t: t[0].lower())
    return items

def _node_count(node):
    """Rekursive Gesamtzahl aller Eintraege (inkl. aller Unterordner)
    fuer die Anzeige in der Kategorienliste."""
    n = len(node["items"])
    for sub in node["folders"].values():
        n += _node_count(sub)
    return n

def _scan_folder_tree(path, syskey, rbf, extmap):
    """Rekursiv EINEN Ordner scannen, gibt einen Baumknoten zurueck -
    beliebig tief verschachtelt, spiegelt die eigene Ordnerstruktur/
    Sortierung 1:1 wider. Bekannte Boot-/Testdateien, Beta/Proto/Hack-
    Tags und rein japanische Titel werden wie bisher ausgefiltert."""
    node = _empty_node()
    try:
        entries = sorted(os.listdir(path), key=str.lower)
    except OSError:
        return node
    raw_items = []
    for entry in entries:
        if entry.startswith("."):
            continue
        full = os.path.join(path, entry)
        if os.path.isdir(full):
            sub = _scan_folder_tree(full, syskey, rbf, extmap)
            if sub["folders"] or sub["items"]:
                node["folders"][entry] = sub
        else:
            name, ext = os.path.splitext(entry)
            ext = ext.lower()
            if name.lower() in IGNORE_ROM_BASENAMES:
                continue
            if _is_junk(name):
                continue
            if _is_japan_only(name):
                continue
            if ext in extmap:
                raw_items.append((name, "game",
                                  (full, ext, syskey, rbf, extmap[ext])))
    node["items"] = _dedupe_items(raw_items)
    return node

def _scan_games_disk(progress_cb=None):
    """Fuer jedes bekannte System die ROMs einsammeln. Rueckgabe: Liste
    (Anzeigename, Baumknoten, Systemkey) - der Baumknoten spiegelt die
    eigene Ordnerstruktur 1:1 wider (beliebig tief verschachtelt),
    statt wie bisher alles in eine flache Liste zu quetschen. Das
    Frontend zeigt Unterordner als eigene Eintraege, die man oeffnen
    kann - genau wie auf dem Datentraeger abgelegt.

    Bekannte Boot-/Testdateien (IGNORE_ROM_BASENAMES) sowie Beta/Proto/
    Demo/Hack/Bad-Dump-Tags (JUNK_TAGS) werden ausgefiltert. Mehrfach-
    Regionen desselben Spiels werden INNERHALB jedes einzelnen Ordners
    zu EINEM Eintrag zusammengefasst (beste Region gewinnt,
    REGION_PRIORITY)."""
    cats = []
    total_sys = len(GAME_SYSTEMS) + len(OPTIONAL_GAME_SYSTEMS)
    # Unterordner, die ein ANDERER Eintrag (egal ob GAME_SYSTEMS oder
    # OPTIONAL_GAME_SYSTEMS) exklusiv fuer sich beansprucht (z.B.
    # "ZELDA_MSU" oder "SMW_HACKS" unter "SNES"), muessen aus der
    # REGULAEREN Kategorie desselben Basisordners ausgeschlossen werden -
    # sonst wuerden dieselben ROMs zusaetzlich unter der normalen SNES-
    # Kategorie auftauchen und liessen sich dort versehentlich mit dem
    # falschen Core statt dem dafuer vorgesehenen starten. Nur EIN
    # Ordner tief beruecksichtigt (passend zu den bisherigen
    # Anwendungsfaellen) - Schluessel ist der oberste Ordnername (z.B.
    # "SNES"), Wert die Menge auszuschliessender direkter
    # Unterordnernamen (z.B. {"ZELDA_MSU", "SMW_HACKS"}).
    claimed_subfolders = {}
    for _d, _sk, sub_folders, _r, _e in GAME_SYSTEMS:
        for f in sub_folders:
            if "/" in f:
                top, sub = f.split("/", 1)
                claimed_subfolders.setdefault(top, set()).add(sub.split("/", 1)[0])
    for _d, _sk, opt_folders, _r, _e, _core in OPTIONAL_GAME_SYSTEMS:
        for f in opt_folders:
            if "/" in f:
                top, sub = f.split("/", 1)
                claimed_subfolders.setdefault(top, set()).add(sub.split("/", 1)[0])
    for sys_idx, (disp, syskey, folders, rbf, extmap) in enumerate(GAME_SYSTEMS):
        if progress_cb:
            try:
                progress_cb(sys_idx, total_sys, disp)
            except Exception:
                pass
        sys_node = _empty_node()
        seen_roots = set()
        for base in GAMES_BASES:
            if not os.path.isdir(base):
                continue
            for folder in folders:
                root = os.path.join(base, folder)
                real = os.path.realpath(root)
                if not os.path.isdir(root) or real in seen_roots:
                    continue
                seen_roots.add(real)
                sub_node = _scan_folder_tree(root, syskey, rbf, extmap)
                _merge_node(sys_node, sub_node)
            for excluded in claimed_subfolders.get(folder, ()):
                sys_node["folders"].pop(excluded, None)
        if sys_node["folders"] or sys_node["items"]:
            cats.append((disp, sys_node, syskey))

    # OPTIONALE Systeme (Nutzerwunsch: SNES_Tracker-Core "wie ein
    # eigenes System behandeln, falls installiert - falls NICHT
    # installiert darf das auch nicht mit angezeigt werden"): exakt
    # dieselbe Scan-Logik wie oben, aber zusaetzlich VORAB die
    # core_check_path-Datei pruefen - fehlt sie, wird gar nicht erst
    # gescannt, das System taucht dann so auf, als gaebe es den
    # Eintrag nicht (kein leerer/ausgegrauter Platzhalter).
    for opt_idx, (disp, syskey, folders, rbf, extmap, core_check_path) \
            in enumerate(OPTIONAL_GAME_SYSTEMS):
        if progress_cb:
            try:
                progress_cb(len(GAME_SYSTEMS) + opt_idx, total_sys, disp)
            except Exception:
                pass
        if not os.path.isfile(core_check_path):
            continue
        sys_node = _empty_node()
        seen_roots = set()
        for base in GAMES_BASES:
            if not os.path.isdir(base):
                continue
            for folder in folders:
                root = os.path.join(base, folder)
                real = os.path.realpath(root)
                if not os.path.isdir(root) or real in seen_roots:
                    continue
                seen_roots.add(real)
                sub_node = _scan_folder_tree(root, syskey, rbf, extmap)
                _merge_node(sys_node, sub_node)
        if sys_node["folders"] or sys_node["items"]:
            cats.append((disp, sys_node, syskey))
    return cats

def write_mgl(rbf, rom_path, delay, ftype, index, setname=None):
    """MGL-Startdatei erzeugen (Pfad-Konvention wie in mrext).
    setname (optional): fuer RA-Cores noetig (siehe find_ra_core()) -
    <setname same_dir="1">...</setname> zwischen <rbf> und <file>,
    exakt wie in einer echten .mgl-Datei von sage2050s Werkzeug
    verifiziert."""
    setname_xml = ('\t<setname same_dir="1">%s</setname>\n' % setname) \
        if setname else ""
    xml = ('<mistergamedescription>\n'
           '\t<rbf>%s</rbf>\n'
           '%s'
           '\t<file delay="%d" type="%s" index="%d" '
           'path="../../../../..%s"/>\n'
           '</mistergamedescription>\n'
           % (rbf, setname_xml, delay, ftype, index, rom_path))
    with open(MGL_TMP, "w") as f:
        f.write(xml)
    return MGL_TMP

def scan_scripts():
    items = []
    for f in sorted(glob.glob(os.path.join(SCRIPTS_DIR, "*.sh"))):
        name = os.path.splitext(os.path.basename(f))[0].replace("_", " ")
        items.append((name, "script", f))
    return items

MISTER_INI = "/media/fat/MiSTer.ini"
CRT_MENU_BLOCK = """
[Menu]
vga_scaler=1
fb_terminal=1
video_mode=320,8,32,24,240,4,3,16,6048
"""

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

# ----------------------------------------------------------------------------
# NTP-ZEITSYNCHRONISIERUNG BEIM START
#
# MiSTer hat keine batteriegepufferte Echtzeituhr - die Systemuhr startet
# beim Booten nahe Null (siehe v1.70: Log-Zeitstempel begannen bei
# "00:00:11") und wird sonst erst spaet (falls ueberhaupt) per NTP
# korrigiert, oft mitten in der Sitzung als ploetzlicher Sprung. Deshalb
# holt das Frontend die Uhrzeit selbst, EINMALIG und MOEGLICHST FRUEH
# beim Start (noch vor dem ersten Log-Eintrag), per einfacher SNTP-
# Abfrage (RFC 5905, reines socket/struct - keine externe Bibliothek).
NTP_SERVER = "pool.ntp.org"
NTP_EPOCH_OFFSET = 2208988800   # Sekunden zwischen 1.1.1900 (NTP) und 1.1.1970 (Unix)
TIMEZONE_OFFSET_FILE = "/media/fat/frontend/timezone_offset"

def load_timezone_offset():
    """Stunden-Versatz zur UTC-Zeit (z.B. 2.0 fuer UTC+2/deutsche
    Sommerzeit). MiSTer hat keine echte Zeitzonen-Datenbank und keine
    automatische Erkennung - NTP liefert grundsaetzlich nur UTC, ohne
    diesen manuell eingestellten Versatz wuerde die angezeigte Uhrzeit
    je nach Zeitzone des Nutzers falsch sein (Bugfix: genau das wurde
    gemeldet - Anzeige zeigte UTC statt der tatsaechlichen Ortszeit,
    zwei Stunden Differenz durch die deutsche Sommerzeit)."""
    try:
        with open(TIMEZONE_OFFSET_FILE) as f:
            return float(f.read().strip())
    except (OSError, ValueError):
        return 0.0

def save_timezone_offset(hours):
    try:
        os.makedirs(os.path.dirname(TIMEZONE_OFFSET_FILE), exist_ok=True)
        with open(TIMEZONE_OFFSET_FILE, "w") as f:
            f.write(str(hours))
    except OSError:
        pass

TIMEZONE_STEPS = [x * 0.5 for x in range(-24, 29)]   # -12.0 .. +14.0 in 0.5h-Schritten

def cycle_timezone_offset():
    """Naechsten Wert in TIMEZONE_STEPS waehlen (wrap-around). Liefert
    den neuen Versatz."""
    current = load_timezone_offset()
    try:
        idx = min(range(len(TIMEZONE_STEPS)),
                  key=lambda i: abs(TIMEZONE_STEPS[i] - current))
        new_idx = (idx + 1) % len(TIMEZONE_STEPS)
    except ValueError:
        new_idx = 0
    new_offset = TIMEZONE_STEPS[new_idx]
    save_timezone_offset(new_offset)
    return new_offset

def format_timezone_offset(hours):
    """z.B. 'UTC+2', 'UTC-3.5', 'UTC' fuer 0."""
    if hours == 0:
        return "UTC"
    sign = "+" if hours > 0 else "-"
    h = abs(hours)
    if h == int(h):
        return "UTC%s%d" % (sign, int(h))
    return "UTC%s%.1f" % (sign, h)

def _ntp_time(server=NTP_SERVER, timeout=2.0):
    """Fragt die aktuelle Unix-Zeit per SNTP ab. Liefert None bei jedem
    Fehler (kein Internet, Zeitueberschreitung, unplausible Antwort) -
    wird NIE eine Ausnahme nach aussen weiterreichen, damit ein
    Zeitserver-Problem den Start niemals blockieren oder zum Absturz
    fuehren kann."""
    s = None
    try:
        packet = bytearray(48)
        packet[0] = 0x1B   # LI=0, VN=3 (NTPv3), Mode=3 (Client)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(timeout)
        s.sendto(bytes(packet), (server, 123))
        data, _ = s.recvfrom(48)
        if len(data) < 48:
            return None
        secs = struct.unpack("!I", data[40:44])[0]
        frac = struct.unpack("!I", data[44:48])[0]
        unix_time = secs - NTP_EPOCH_OFFSET + frac / 2**32
        # Grobe Plausibilitaetspruefung (nach 2020, vor 2100) - schuetzt
        # vor einer kaputten Antwort, die die Uhr auf einen abwegigen
        # Wert setzen wuerde.
        if unix_time < 1577836800 or unix_time > 4102444800:
            return None
        return unix_time
    except (OSError, struct.error, socket.gaierror):
        return None
    finally:
        if s is not None:
            try:
                s.close()
            except OSError:
                pass

NTP_SYNC_OK = False   # von sync_system_clock_from_ntp() bei jedem Aufruf
                      # aktuell gehalten - ermoeglicht spaeteren Code (z.B.
                      # dem RA-Neuversuch) zu pruefen, ob die Systemuhr
                      # zum jetzigen Zeitpunkt als verlaesslich gilt.

def _apply_ntp_result(unix_time):
    """Setzt die Systemuhr anhand eines per NTP ermittelten UTC-
    Zeitstempels (oder None bei Fehlschlag) und haelt NTP_SYNC_OK
    aktuell. Ausgelagert, damit sowohl der blockierende als auch der
    nicht-blockierende Modus von sync_system_clock_from_ntp() dieselbe
    Logik nutzen (siehe dort)."""
    global NTP_SYNC_OK
    if unix_time is None:
        NTP_SYNC_OK = False
        return False
    try:
        # BUGFIX (Nutzer-Rueckmeldung: Uhr zeigte 2 Stunden zu wenig,
        # deutsche Sommerzeit): NTP liefert grundsaetzlich UTC. Die alte
        # Fassung nutzte time.localtime(), das sich auf die System-
        # Zeitzone verlaesst - MiSTer hat aber vermutlich gar keine
        # echte Zeitzone konfiguriert (Standard UTC), wodurch die
        # angezeigte Uhrzeit der reinen UTC-Zeit entsprach statt der
        # tatsaechlichen Ortszeit. Jetzt wird der manuell eingestellte
        # Versatz (siehe load_timezone_offset()) selbst angewendet und
        # mit time.gmtime() formatiert - unabhaengig davon, was die
        # Systemzeitzone gerade zu sein glaubt.
        local_unix_time = unix_time + load_timezone_offset() * 3600
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(local_unix_time))
        subprocess.run(["date", "-s", ts], capture_output=True, timeout=2.0)
        NTP_SYNC_OK = True
        return True
    except (OSError, subprocess.SubprocessError):
        NTP_SYNC_OK = False
        return False

def sync_system_clock_from_ntp(timeout=2.5, blocking=True):
    """Setzt die Systemuhr per NTP, FALLS ein lokales Netzwerk vorhanden
    ist - in einem separaten Thread mit hartem Zeitlimit, damit eine
    haengende DNS-Aufloesung (die von socket.settimeout() NICHT
    zuverlaessig erfasst wird) den Start niemals um mehr als `timeout`
    Sekunden verzoegert. Der Thread laeuft im schlimmsten Fall im
    Hintergrund weiter, blockiert dabei aber nichts mehr (Daemon-Thread) -
    sein Ergebnis wird dann einfach verworfen. Ohne lokales Netzwerk wird
    gar nicht erst versucht (spart die Wartezeit komplett).

    blocking=False (Nutzerwunsch: schnellerer Programmstart): startet
    die Synchronisierung nur im Hintergrund und kehrt SOFORT zurueck
    (Rueckgabewert dann None - das Ergebnis steht ja noch nicht fest),
    ohne auf das Ergebnis zu warten. Der Hintergrund-Thread setzt die
    Uhr trotzdem zuverlaessig, sobald er fertig ist - der bestehende
    RA-Neuversuch-Mechanismus (Frontend._maybe_retry_ra()) faengt den
    Fall "Uhr war beim allerersten RA-Abruf noch nicht fertig" schon
    ab, dafuer aendert sich durch blocking=False nichts.

    Haelt NTP_SYNC_OK bei jedem Aufruf aktuell (auch bei spaeteren
    Neuversuchen) - andere Code-Stellen koennen darueber pruefen, ob
    die Systemuhr aktuell als verlaesslich gilt, ohne selbst NTP
    abfragen zu muessen."""
    if not _has_network():
        return False
    result = {"t": None}
    def worker():
        result["t"] = _ntp_time(timeout=timeout)
        if not blocking:
            # Niemand wartet auf dieses Ergebnis - der Hintergrund-
            # Thread muss die Uhr deshalb selbst setzen.
            _apply_ntp_result(result["t"])
    th = threading.Thread(target=worker, daemon=True)
    th.start()
    if not blocking:
        return None   # Ergebnis noch nicht bekannt, laeuft im Hintergrund weiter
    th.join(timeout=timeout + 0.5)
    return _apply_ntp_result(result["t"])

def crt_menu_active():
    try:
        return "[Menu]" in open(MISTER_INI).read()
    except OSError:
        return False

def toggle_crt_menu():
    """[Menu]-Block in der MiSTer.ini setzen/entfernen.
    Rueckgabe: True wenn danach CRT-Modus aktiv ist."""
    try:
        ini = open(MISTER_INI).read()
    except OSError:
        return None
    if "[Menu]" in ini:
        # Block entfernen: von der [Menu]-Zeile bis zur naechsten
        # Sektion oder zum Dateiende
        i = ini.index("[Menu]")
        j = ini.find("\n[", i + 1)
        ini = ini[:i].rstrip() + "\n" + (ini[j + 1:] if j != -1 else "")
        active = False
    else:
        ini = ini.rstrip() + "\n" + CRT_MENU_BLOCK
        active = True
    # Atomar schreiben: erst in eine Temp-Datei, dann umbenennen. Sonst
    # kann ein Abbruch mitten im Schreiben die MiSTer.ini leeren/zerstoeren.
    tmp = MISTER_INI + ".tmp"
    try:
        with open(tmp, "w") as f:
            f.write(ini)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, MISTER_INI)
    except OSError:
        try:
            os.remove(tmp)
        except OSError:
            pass
        return None
    return active

# ----------------------------------------------------------------------------
# NAVIGATIONS-SOUNDEFFEKTE (selbst erzeugte Sinuston-WAVs, aplay)
#
# Kein Download noetig - die kurzen Toene werden beim ersten Start
# einmalig selbst synthetisiert (reines math/struct) und unter
# SFX_DIR abgelegt. Abgespielt wird "fire and forget" ueber `aplay`
# (Teil von alsa-utils, auf MiSTer bereits vorhanden) - laeuft parallel
# zur Hintergrundmusik; ist die Soundkarte gerade belegt ("device
# busy"), wird der Effekt einfach uebersprungen statt etwas zu stoeren.
# Eine Drossel verhindert, dass beim Halten einer Richtungstaste (mit
# Turbo-Beschleunigung) zu viele Prozesse pro Sekunde losgehen.
SFX_DIR = "/media/fat/frontend/sfx"
SFX_ENABLED_FLAG_FILE = "/media/fat/frontend/sfx_disabled"
SFX_MIN_GAP = 0.07   # Sekunden zwischen zwei Soundeffekten (Drossel)

def sfx_enabled_flag():
    return not os.path.exists(SFX_ENABLED_FLAG_FILE)

def toggle_sfx():
    if os.path.exists(SFX_ENABLED_FLAG_FILE):
        try:
            os.remove(SFX_ENABLED_FLAG_FILE)
        except OSError:
            pass
    else:
        try:
            dirname = os.path.dirname(SFX_ENABLED_FLAG_FILE)
            if dirname:
                os.makedirs(dirname, exist_ok=True)
            open(SFX_ENABLED_FLAG_FILE, "w").close()
        except OSError:
            pass

def _synth_tone_samples(freq_start, freq_end, duration_ms, volume, sample_rate):
    """Erzeugt die rohen 16-Bit-Samples fuer EINEN Frequenz-Sweep
    (kumulative Phase statt sin(2*pi*freq*t) mit wechselndem freq -
    sonst wuerden bei einem Sweep hoerbare Spruenge entstehen). Kern
    von _write_wav_tone()/_write_wav_chime()."""
    n = max(1, int(sample_rate * duration_ms / 1000))
    fade = max(1, n // 8)
    samples = bytearray(n * 2)
    phase = 0.0
    for i in range(n):
        freq = freq_start + (freq_end - freq_start) * (i / max(1, n - 1))
        phase += 2 * math.pi * freq / sample_rate
        env = 1.0
        if i < fade:
            env = i / fade
        elif i > n - fade:
            env = (n - i) / fade
        val = int(math.sin(phase) * volume * env * 32767)
        val = max(-32768, min(32767, val))
        struct.pack_into("<h", samples, i * 2, val)
    return samples

def _write_wav(path, data, sample_rate=22050):
    """Schreibt fertige 16-Bit-Mono-Samples als WAV-Datei."""
    byte_rate = sample_rate * 2
    header = (b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVE"
             + b"fmt " + struct.pack("<IHHIIHH", 16, 1, 1, sample_rate,
                                     byte_rate, 2, 16)
             + b"data" + struct.pack("<I", len(data)))
    with open(path, "wb") as f:
        f.write(header + data)

def _write_wav_tone(path, freq_start, freq_end, duration_ms,
                    volume=0.35, sample_rate=22050):
    """Erzeugt eine kurze Mono-WAV-Datei mit einem einzelnen Sinuston
    (linearer Frequenz-Sweep von freq_start zu freq_end)."""
    samples = _synth_tone_samples(freq_start, freq_end, duration_ms,
                                  volume, sample_rate)
    _write_wav(path, bytes(samples), sample_rate)

def _write_wav_chime(path, segments, volume=0.35, sample_rate=22050):
    """Wie _write_wav_tone(), aber fuer mehrere Toene HINTEREINANDER -
    segments: Liste von (freq_start, freq_end, duration_ms)-Tupeln.
    Fuer den Erfolgs-Sound (kurzer aufsteigender Doppelklang), der mit
    einem einzelnen Sweep nicht "erfolgreich" genug klingt."""
    all_samples = bytearray()
    for freq_start, freq_end, duration_ms in segments:
        all_samples += _synth_tone_samples(freq_start, freq_end, duration_ms,
                                           volume, sample_rate)
    _write_wav(path, bytes(all_samples), sample_rate)

SFX_DEFS = {
    "move":    (760, 900, 30),
    "confirm": (600, 1100, 70),
    "back":    (700, 420, 55),
}
SFX_CHIME_DEFS = {
    # Kurzer aufsteigender Doppelklang - deutlich von den einfachen
    # Sweeps oben abgesetzt, fuer den Erfolgs-Sound.
    "achievement": [(600, 900, 60), (950, 1400, 90)],
    # Geheimer Sound (Nutzerwunsch: "Easter Egg System") -
    # verspielter, mehrstufiger Klang, bewusst deutlich anders
    # als die anderen Sounds (auffaelliger "Fund"-Charakter).
    "secret_found": [(300, 600, 50), (600, 450, 40), (450, 900, 70), (900, 700, 90)],
}

def _ensure_sfx_files():
    """Erzeugt die WAV-Dateien einmalig, falls sie noch fehlen (erster
    Start bzw. nach einem Update). Amplitude skaliert mit der
    eingestellten Lautstaerke (VOLUME) - aplay hat selbst keinen
    Lautstaerke-Schalter, siehe _regenerate_sfx()."""
    try:
        os.makedirs(SFX_DIR, exist_ok=True)
    except OSError:
        return
    for name, (f0, f1, dur) in SFX_DEFS.items():
        path = os.path.join(SFX_DIR, name + ".wav")
        if not os.path.exists(path):
            try:
                _write_wav_tone(path, f0, f1, dur, volume=0.35 * VOLUME / 100.0)
            except OSError:
                pass
    for name, segments in SFX_CHIME_DEFS.items():
        path = os.path.join(SFX_DIR, name + ".wav")
        if not os.path.exists(path):
            try:
                _write_wav_chime(path, segments, volume=0.35 * VOLUME / 100.0)
            except OSError:
                pass

_last_sfx_time = 0.0
_sfx_enabled_cache = True
_sfx_enabled_check_next = 0.0
_sfx_proc = None   # laufender aplay-Prozess (oder None) - siehe play_sfx()

def _sfx_enabled_cached():
    """Zwischengespeicherte sfx_enabled_flag()-Abfrage, alle 5 Sekunden
    neu geprueft - selbes Prinzip wie beim Netzwerkstatus/Attract-Modus
    (siehe _network_connected()/_attract_enabled_cached()). Wird von
    play_sfx() genutzt, damit nicht bei jedem einzelnen Aufruf eine
    Datei-Existenzpruefung noetig ist."""
    global _sfx_enabled_cache, _sfx_enabled_check_next
    now = time.monotonic()
    if now >= _sfx_enabled_check_next:
        _sfx_enabled_cache = sfx_enabled_flag()
        _sfx_enabled_check_next = now + 5.0
    return _sfx_enabled_cache

def play_sfx(name, music_playing=False):
    """Spielt einen Soundeffekt ab, falls aktiviert - "fire and forget",
    jeder Fehler (aplay fehlt, Soundkarte belegt, Datei fehlt) wird
    still ignoriert. Nie eine Ausnahme nach aussen. Gedrosselt
    (SFX_MIN_GAP) - sonst wuerden beim Halten einer Richtungstaste mit
    Turbo-Beschleunigung zu viele aplay-Prozesse pro Sekunde entstehen.

    BUGFIX (Nutzer-Rueckmeldung): die reine Zeit-Drossel allein hat
    NICHT verhindert, dass sich bei schneller Navigation mehrere
    aplay-Prozesse ueberlappen - jeder einzelne Aufruf brauchte
    laenger als die Drosselzeit, bis er tatsaechlich fertig war
    (vermutlich, weil aplay auf die Soundkarte warten musste, die
    gleichzeitig von mpg123 fuer die Hintergrundmusik belegt ist).
    Ergebnis: ein wachsender Rueckstau, der noch Toene abspielte, lange
    nachdem der Cursor schon wieder stillstand - UND dabei offenbar
    kurze Aussetzer in der Musik verursachte, weil beide Programme sich
    dieselbe Audioausgabe streitig machten. Zwei Absicherungen dagegen:
    (1) ein neuer Ton wird NICHT gestartet, solange der vorherige
    aplay-Prozess noch laeuft (kein Rueckstau moeglich, hoechstens
    EIN Ton gleichzeitig unterwegs). (2) Solange Musik TATSAECHLICH
    gerade spielt (music_playing=True, vom Aufrufer per
    self.music._proc_alive() ermittelt), wird gar nicht erst
    versucht - vermeidet die Geraete-Ueberschneidung von vornherein,
    statt nur ihre Folgen abzumildern.

    WICHTIG: die guenstige, rein im Speicher liegende Drossel-Pruefung
    muss VOR der (Datei-basierten) Ein/Aus-Pruefung passieren, nicht
    danach - sonst waere bei jedem einzelnen Navigations-Schritt
    waehrend eines Turbo-Sprungs eine Datei-Existenzpruefung noetig
    gewesen. Zusaetzlich per _sfx_enabled_cached() auf 5s
    zwischengespeichert."""
    global _last_sfx_time, _sfx_proc
    now = time.monotonic()
    if now - _last_sfx_time < SFX_MIN_GAP:
        return
    if music_playing:
        return
    if _sfx_proc is not None and _sfx_proc.poll() is None:
        return   # voriger Ton laeuft noch - lieber auslassen als stapeln
    if not _sfx_enabled_cached():
        return
    _last_sfx_time = now
    path = os.path.join(SFX_DIR, name + ".wav")
    try:
        _sfx_proc = subprocess.Popen(["aplay", "-q", path],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        pass

# ----------------------------------------------------------------------------
# BACKGROUND MUSIC (mpg123, extern - no own MP3 decoder needed)
# ----------------------------------------------------------------------------

class MusicPlayer:
    """Plays MP3s from MUSIC_DIR in random order in the background.
    Uses the external mpg123 command-line player (present on MiSTer)
    instead of decoding audio ourselves. Non-blocking: the current
    track runs via subprocess.Popen, the switch to the next track
    happens whenever tick() is called from the main loop."""

    MAX_TRACK_SECONDS = 20 * 60   # Sicherheitsnetz, siehe tick()

    def __init__(self):
        self.enabled = self._load_enabled()
        self.source, _radio_sid = self._load_source()   # "mp3" oder "radio" + sid
        self.radio = rainwave.RainwaveRadio(sid=_radio_sid, log=LOG) \
            if rainwave is not None else None
        self.playlist = []
        self.pos = 0
        self.proc = None
        self._track_started_at = None
        self._proc_lock = threading.Lock()   # BUGFIX (uebernommen aus separat
                                              # vorbereitetem Vorschlag, siehe
                                              # CHANGES_v4.2_FIXES.md): verhindert
                                              # doppelte mpg123-Prozesse - der
                                              # Lautstaerke-Hintergrund-Thread und
                                              # tick() konnten bisher gleichzeitig
                                              # einen Start ausloesen, zwei mpg123
                                              # gleichzeitig fuehrten zu doppeltem/
                                              # verzerrtem Radio-Stream.
        self.paused_for_core = False
        self._rescan()

    @staticmethod
    def _load_enabled():
        try:
            return open(MUSIC_ENABLED_FILE).read().strip() != "0"
        except OSError:
            return True    # default: on, until toggled once

    def _save_enabled(self):
        try:
            os.makedirs(os.path.dirname(MUSIC_ENABLED_FILE), exist_ok=True)
            with open(MUSIC_ENABLED_FILE, "w") as f:
                f.write("1" if self.enabled else "0")
        except OSError:
            pass

    @staticmethod
    def _load_source():
        """(quelle, sid) aus MUSIC_SOURCE_FILE - Default ("mp3", 1).
        Faellt zusaetzlich auf "mp3" zurueck, falls das rainwave-Modul
        nicht geladen werden konnte (siehe Import-Absicherung oben) -
        eine gespeicherte "radio"-Quelle darf dann nicht blind
        uebernommen werden, sonst gaebe es keine Musik mehr."""
        if rainwave is None:
            return "mp3", 1
        try:
            parts = open(MUSIC_SOURCE_FILE).read().split()
            src = parts[0] if parts and parts[0] in ("mp3", "radio") else "mp3"
            sid = int(parts[1]) if len(parts) > 1 else 1
            if sid not in rainwave.RAINWAVE_STATIONS:
                sid = 1
            return src, sid
        except (OSError, ValueError):
            return "mp3", 1

    def _save_source(self):
        if self.radio is None:
            return
        try:
            os.makedirs(os.path.dirname(MUSIC_SOURCE_FILE), exist_ok=True)
            with open(MUSIC_SOURCE_FILE, "w") as f:
                f.write("%s %d" % (self.source, self.radio.sid))
        except OSError:
            pass

    def _rescan(self):
        try:
            files = [os.path.join(MUSIC_DIR, f)
                    for f in os.listdir(MUSIC_DIR)
                    if f.lower().endswith(".mp3")]
        except OSError:
            files = []
        random.shuffle(files)
        self.playlist = files
        self.pos = 0

    def available(self):
        if self.source == "radio":
            return self.radio is not None and os.path.exists(MPG123_BIN)
        return bool(self.playlist) and os.path.exists(MPG123_BIN)

    def _proc_alive(self):
        return self.proc is not None and self.proc.poll() is None

    def _start_current(self):
        """Startet die aktuelle Quelle (MP3/Radio). Lock + 'vorher
        alten Prozess beenden' -> nie zwei mpg123 gleichzeitig (siehe
        _proc_lock-Kommentar im __init__)."""
        with self._proc_lock:
            self._kill_proc()
            self._start_current_impl()

    def _start_current_impl(self):
        if self.source == "radio":
            if self.radio is None:
                return
            url = self.radio.stream_url()
            if not url:
                return
            try:
                self.proc = subprocess.Popen(
                    [MPG123_BIN, "-q", "-f", _mpg_scale(), url],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL)
                self._track_started_at = time.monotonic()
                LOG("Radio: %s -> %s" % (rainwave.station_name(self.radio.sid), url))
            except OSError as e:
                LOG("Radio: mpg123-Start fehlgeschlagen: %s" % e)
                self.proc = None
            return
        if not self.playlist:
            return
        path = self.playlist[self.pos]
        try:
            self.proc = subprocess.Popen(
                [MPG123_BIN, "-q", "-f", _mpg_scale(), path],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL)
            self._track_started_at = time.monotonic()
            LOG("Music: playing %s" % os.path.basename(path))
        except OSError as e:
            LOG("Music: failed to start mpg123: %s" % e)
            self.proc = None

    def _kill_proc(self):
        """Beendet den laufenden mpg123-Prozess. Aufrufer haelt _proc_lock."""
        if self.proc is not None:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=2)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass
            self.proc = None

    def _stop_current(self):
        with self._proc_lock:
            self._kill_proc()

    def _advance(self):
        if not self.playlist:
            return
        self.pos += 1
        if self.pos >= len(self.playlist):
            random.shuffle(self.playlist)   # new round, reshuffled
            self.pos = 0

    def current_track_name(self):
        """Anzeigename des aktuell (bzw. zuletzt gestarteten) Songs,
        ohne Pfad und Dateiendung - oder None, wenn gerade nichts
        gespielt wird/werden soll."""
        if not self.enabled or self.paused_for_core:
            return None
        if self.source == "radio":
            if self.radio is None:
                return None
            return self.radio.now_playing() or \
                ("Radio: %s" % rainwave.station_name(self.radio.sid))
        if not self.playlist:
            return None
        path = self.playlist[self.pos]
        return os.path.splitext(os.path.basename(path))[0]

    def tick(self):
        """Call regularly from the main loop. Starts playback if
        needed, automatically advances to the next track once the
        current one has ended.

        Sicherheitsnetz: manche MP3-Dateien (beschaedigte/unuebliche
        Tags) koennen mpg123 nach dem eigentlichen Ende haengen lassen,
        statt sauber zu beenden - poll() wuerde dann faelschlich
        weiterhin 'laeuft noch' melden. Nach MAX_TRACK_SECONDS wird
        deshalb trotzdem zum naechsten Song gewechselt."""
        if not self.enabled or self.paused_for_core:
            return
        if self.source == "radio":
            if self.radio is None:
                return
            self.radio.tick()                 # Now-Playing aktuell halten (nur alle 15s)
            if not self._proc_alive():
                # (neu) verbinden - kleiner Backoff gegen Haemmern bei Netzausfall
                if self._track_started_at is None or \
                   time.monotonic() - self._track_started_at > 3:
                    self._start_current()
            return
        if not self.playlist:
            return
        alive = self._proc_alive()
        had_proc = self.proc is not None  # VOR _stop_current() merken -
                                          # das setzt self.proc selbst auf None
        if alive and self._track_started_at is not None and \
           time.monotonic() - self._track_started_at > self.MAX_TRACK_SECONDS:
            LOG("Music: Sicherheitsnetz ausgeloest (Song laeuft laenger "
                "als %d Minuten) - erzwinge Wechsel"
                % (self.MAX_TRACK_SECONDS // 60))
            self._stop_current()
            alive = False
        if not alive:
            if had_proc:
                LOG("Music: Song beendet, wechsle weiter")
                self._advance()
            self._start_current()

    def next_track(self):
        """Manual track skip (Y button)."""
        if not self.playlist:
            return
        self._stop_current()
        self._advance()
        if self.enabled and not self.paused_for_core:
            self._start_current()

    def toggle(self):
        self.enabled = not self.enabled
        self._save_enabled()
        if self.enabled:
            if not self.paused_for_core:
                self.tick()
        else:
            self._stop_current()

    def cycle_source(self):
        """Musik-Quelle umschalten: MP3 -> Radio(Game..All) -> zurueck zu MP3.
        Laesst den An/Aus-Zustand (self.enabled) bewusst unberuehrt.
        Ohne geladenes rainwave-Modul (siehe Import-Absicherung oben)
        bleibt das ein no-op - es gaebe nichts, wohin man umschalten
        koennte."""
        if self.radio is None:
            return
        stations = sorted(rainwave.RAINWAVE_STATIONS)
        self._stop_current()   # laufende Quelle stoppen; tick() startet die neue
        if self.source == "mp3":
            self.source = "radio"
            self.radio.set_station(stations[0])
        else:
            idx = stations.index(self.radio.sid) if self.radio.sid in stations else -1
            if idx + 1 < len(stations):
                self.radio.set_station(stations[idx + 1])
            else:
                self.source = "mp3"
        self._track_started_at = None
        self._save_source()
        if self.enabled:
            if not self.paused_for_core:
                self.tick()
        else:
            self._stop_current()

    def cycle_volume(self):
        """Lautstaerke 0->20->...->100->0 (Musik UND Menue-Sounds)."""
        global VOLUME
        levels = [0, 20, 40, 60, 80, 100]
        idx = levels.index(VOLUME) if VOLUME in levels else len(levels) - 1
        VOLUME = levels[(idx + 1) % len(levels)]
        _save_volume(VOLUME)
        _apply_volume_async(self)   # SFX-Regen + Musik-Neustart im Hintergrund

    def pause_for_core(self):
        """Before starting a core/game: stop music so it doesn't mix
        with the game's own audio."""
        self.paused_for_core = True
        self._stop_current()

    def resume_after_core(self):
        """After returning to the frontend: resume music automatically
        if it's enabled."""
        self.paused_for_core = False
        if self.enabled:
            self.tick()

    def shutdown(self):
        self._stop_current()


# ----------------------------------------------------------------------------
# LANGUAGE / TRANSLATIONS
# ----------------------------------------------------------------------------

TRANSLATIONS = {
    "categories":      {"en": "%d categories",  "de": "%d Kategorien"},
    "entries":         {"en": "%d entries",      "de": "%d Eintraege"},
    "footer_cats_wide":   {"en": "Up/Down:Nav  Left/Right:Page  Enter:Open  ESC:Quit",
                           "de": "Hoch/Runter:Nav  Links/Rechts:Seite  Enter:Oeffnen  ESC:Beenden"},
    "footer_cats_mid":    {"en": "Nav  Page  Enter:Open  ESC:Quit",
                           "de": "Nav  Seite  Enter:Oeffnen  ESC:Beenden"},
    "footer_cats_narrow": {"en": "Enter:Open  ESC:Quit",
                           "de": "Enter:Oeffnen  ESC:Beenden"},
    "footer_items_wide":   {"en": "Up/Down:Nav  Left/Right:Page  Enter/A:Start  ESC/B:Back",
                            "de": "Hoch/Runter:Nav  Links/Rechts:Seite  Enter/A:Start  ESC/B:Zurueck"},
    "footer_items_mid":    {"en": "L/R:Page  Enter/A:Start  ESC/B:Back",
                            "de": "L/R:Seite  Enter/A:Start  ESC/B:Zurueck"},
    "footer_items_narrow": {"en": "A:Start  B:Back", "de": "A:Start  B:Zurueck"},
    "quit_confirm":    {"en": "Quit the frontend?", "de": "Frontend wirklich beenden?"},
    "yes":             {"en": "Yes", "de": "Ja"},
    "no":              {"en": "No",  "de": "Nein"},
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
                        "de": "Marathon: eine Sitzung ueber 3 Stunden am Stueck"},
    "hidden_collector": {"en": "Collector: 10 favorites at once",
                         "de": "Sammlerin: 10 Favoriten gleichzeitig"},
    "hidden_completionist": {"en": "Regular: one game launched 20+ times",
                             "de": "Stammspieler: ein Spiel 20+ mal gestartet"},
    "hidden_legend": {"en": "Legend: reached every top-tier milestone at once",
                      "de": "Legende: alle hoechsten Meilensteine gleichzeitig erreicht"},
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
    "max_level_boot_effect": {"en": "FRONTEND LEVEL MAX", "de": "FRONTEND-LEVEL MAX"},
    "secret_name_secret_theme_1": {"en": "hidden theme", "de": "geheimes Theme"},
    "secret_name_entwicklerraum": {"en": "developer room", "de": "Entwicklerraum"},
    "secret_name_secret_sound": {"en": "hidden sound", "de": "geheimer Sound"},
    "dev_room_title": {"en": "DEVELOPER ROOM", "de": "ENTWICKLERRAUM"},
    "dev_room_level": {"en": "Frontend level: %d of %d", "de": "Frontend-Level: %d von %d"},
    "dev_room_secrets": {"en": "Secrets found: %d of %d", "de": "Geheimnisse gefunden: %d von %d"},
    "dev_room_credits_1": {"en": "Built by Dragrem.",
                           "de": "Gebaut von Dragrem."},
    "dev_room_credits_2": {"en": "With contributions from TheRealSutefan and Dfense1980.",
                           "de": "Mit Beitraegen von TheRealSutefan und Dfense1980."},
    "dev_room_thanks": {"en": "Thanks for playing around with hidden things.",
                        "de": "Danke, dass du an geheimen Dingen herumprobierst."},
    "credits_title": {"en": "CREDITS", "de": "MITWIRKENDE"},
    "credits_creator_heading": {"en": "Created by", "de": "Erstellt von"},
    "credits_creator_entry": {"en": "Dragrem", "de": "Dragrem"},
    "credits_contrib_heading": {"en": "Contributions", "de": "Beitraege"},
    "credits_contrib_sutefan": {"en": "TheRealSutefan - patches, RA tools, bugfixes",
                                "de": "TheRealSutefan - Patches, RA-Werkzeuge, Bugfixes"},
    "credits_contrib_dfense": {"en": "Dfense1980 - contributions",
                               "de": "Dfense1980 - Mitwirkung"},
    "credits_contrib_dennsen": {"en": "Dennsen86 - streaming and testing",
                                "de": "Dennsen86 - Streaming und Testen"},
    "credits_thanks_heading": {"en": "Thanks", "de": "Danke"},
    "credits_thanks_entry": {"en": "To everyone playing, testing and reporting bugs.",
                             "de": "An alle, die spielen, testen und Fehler melden."},
    "trophy_room_title": {"en": "TROPHY ROOM", "de": "TROPHAEENRAUM"},
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
    "year_review_title": {"en": "YEAR IN REVIEW %s", "de": "JAHRESRUECKBLICK %s"},
    "year_review_empty": {"en": "Nothing recorded for this year yet - keep playing!",
                          "de": "Fuer dieses Jahr noch nichts aufgezeichnet - einfach weiterspielen!"},
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
    "sys_help_action": {"en": "Help / Overview", "de": "Hilfe / Uebersicht"},
    "boot_default_title": {"en": "MISTER FRONTEND", "de": "MISTER FRONTEND"},
    "help_title": {"en": "HELP / OVERVIEW", "de": "HILFE / UEBERSICHT"},
    "help_section_nav": {"en": "Navigation", "de": "Navigation"},
    "help_nav_move_key": {"en": "Arrow keys", "de": "Pfeiltasten"},
    "help_nav_move_desc": {"en": "Move around", "de": "Bewegen"},
    "help_nav_ok_key": {"en": "OK / A", "de": "OK / A"},
    "help_nav_ok_desc": {"en": "Select, enter category/folder",
                         "de": "Auswaehlen, Kategorie/Ordner betreten"},
    "help_nav_back_key": {"en": "Back / B", "de": "Zurueck / B"},
    "help_nav_back_desc": {"en": "One level back, at the top: exit dialog",
                           "de": "Eine Ebene zurueck, ganz oben: Beenden-Dialog"},
    "help_nav_letter_key": {"en": "Letter key (keyboard)",
                            "de": "Buchstabentaste (Tastatur)"},
    "help_nav_letter_desc": {"en": "Jump to next entry with that letter",
                             "de": "Springt zum naechsten Eintrag mit diesem Buchstaben"},
    "help_section_list": {"en": "In the game list", "de": "In der Spieleliste"},
    "help_list_showcase_key": {"en": "F6", "de": "F6"},
    "help_list_showcase_desc": {"en": "RA achievement showcase for the selected game",
                                "de": "RA-Erfolgs-Vitrine fuer das markierte Spiel"},
    "help_list_completed_key": {"en": "F7", "de": "F7"},
    "help_list_completed_desc": {"en": "Toggle completed status",
                                 "de": "Durchgespielt-Status umschalten"},
    "help_list_favorite_key": {"en": "F8 / L2 or R2", "de": "F8 / L2 oder R2"},
    "help_list_favorite_desc": {"en": "Toggle favorite", "de": "Favorit umschalten"},
    "help_list_random_key": {"en": "F11", "de": "F11"},
    "help_list_random_desc": {"en": "Start a random game across all systems",
                              "de": "Zufaelliges Spiel ueber alle Systeme starten"},
    "help_section_menu": {"en": "Special entries in the main menu",
                          "de": "Besondere Eintraege im Hauptmenue"},
    "help_menu_continue_key": {"en": "Continue playing", "de": "Weiterspielen"},
    "help_menu_continue_desc": {"en": "Your last unfinished game",
                                "de": "Dein zuletzt offenes Spiel"},
    "help_menu_collections_key": {"en": "Collections", "de": "Sammlungen"},
    "help_menu_collections_desc": {"en": "Automatic groupings",
                                   "de": "Automatische Gruppierungen"},
    "help_menu_hunter_key": {"en": "RA Achievement Hunter", "de": "RA-Erfolgsjaeger"},
    "help_menu_hunter_desc": {"en": "Open achievements in your library",
                              "de": "Offene Erfolge in deiner Bibliothek"},
    "help_section_system": {"en": "System menu", "de": "System-Menue"},
    "help_system_stats_key": {"en": "Statistics & achievements",
                              "de": "Statistiken & Erfolge"},
    "help_system_stats_desc": {"en": "Top-10 lists, trophy room, year in review, diary",
                               "de": "Top-10-Listen, Trophaeenraum, Jahresrueckblick, Spieltagebuch"},
    "help_system_secrets_key": {"en": "Secrets", "de": "Geheimnisse"},
    "help_system_secrets_desc": {"en": "Hidden things to discover for yourself",
                                 "de": "Verstecktes, das du selbst entdecken kannst"},
    "help_system_credits_key": {"en": "Credits", "de": "Mitwirkende"},
    "help_system_credits_desc": {"en": "Who made this", "de": "Wer das gebaut hat"},
    "help_section_playing": {"en": "While playing", "de": "Waehrend des Spielens"},
    "help_playing_exit_key": {"en": "Esc or F10 (hold ~0.6s)",
                              "de": "Esc oder F10 (ca. 0,6s halten)"},
    "help_playing_exit_desc": {"en": "Back to the menu immediately",
                               "de": "Sofort zurueck ins Menue"},
    "help_playing_exit_pad_key": {"en": "Start + Select (pad, hold ~0.8s)",
                                  "de": "Start + Select (Pad, ca. 0,8s halten)"},
    "help_playing_exit_pad_desc": {"en": "Back to the menu immediately",
                                   "de": "Sofort zurueck ins Menue"},
    "help_playing_music_key": {"en": "Y", "de": "Y"},
    "help_playing_music_desc": {"en": "Next music track",
                                "de": "Naechster Musiktitel"},
    "help_section_general": {"en": "Anywhere", "de": "Ueberall"},
    "help_general_osd_key": {"en": "F12 / Mode (pad)", "de": "F12 / Mode-Taste (Pad)"},
    "help_general_osd_desc": {"en": "Open the MiSTer OSD (joystick setup, settings)",
                              "de": "MiSTer-OSD oeffnen (Joystick-Definition, Einstellungen)"},
    "help_general_osd_back_key": {"en": "F10 / X (pad)", "de": "F10 / X (Pad)"},
    "help_general_osd_back_desc": {"en": "Back to the frontend from the OSD",
                                   "de": "Zurueck ins Frontend aus dem OSD"},
    "sys_trophy_action": {"en": "My trophy room", "de": "Mein Trophaeenraum"},
    "sys_year_review_action": {"en": "Year in review", "de": "Jahresrueckblick"},
    "sys_secrets_action": {"en": "Secrets", "de": "Geheimnisse"},
    "sys_credits_action": {"en": "Credits", "de": "Mitwirkende"},
    "sys_crt_test_action": {"en": "CRT test pattern", "de": "CRT-Testbild"},
    "ra_showcase_title": {"en": "RA ACHIEVEMENTS - %s", "de": "RA-ERFOLGE - %s"},
    "ra_showcase_loading": {"en": "Loading achievements ...",
                            "de": "Erfolge werden geladen ..."},
    "ra_showcase_error": {"en": "Could not load achievements (no network/timeout)",
                          "de": "Erfolge konnten nicht geladen werden (kein Netz/Zeitlimit)"},
    "ra_showcase_empty": {"en": "No achievements found for this game",
                          "de": "Keine Erfolge fuer dieses Spiel gefunden"},
    "ra_showcase_none": {"en": "No RetroAchievements data for this game",
                         "de": "Keine RetroAchievements-Daten fuer dieses Spiel"},
    "ra_showcase_not_setup": {"en": "RetroAchievements not set up (see README)",
                              "de": "RetroAchievements nicht eingerichtet (siehe README)"},
    "sys_milestones_action": {"en": "My achievements", "de": "Meine Erfolge"},
    "sys_ra_setup": {"en": "RetroAchievements: not set up",
                     "de": "RetroAchievements: nicht eingerichtet"},
    "sys_ra_configured": {"en": "RetroAchievements: %s (reload)",
                          "de": "RetroAchievements: %s (neu laden)"},
    "core_choice_title": {"en": "%s - CHOOSE CORE",
                          "de": "%s - CORE WAEHLEN"},
    "core_choice_normal": {"en": "Standard core",
                           "de": "Standard-Core"},
    "core_choice_ra": {"en": "RetroAchievements core",
                       "de": "RetroAchievements-Core"},
    "core_choice_hint": {"en": "Up/Down to choose, OK to confirm",
                         "de": "Hoch/Runter waehlen, OK bestaetigen"},
    "ra_setup_title": {"en": "RETROACHIEVEMENTS SETUP",
                       "de": "RETROACHIEVEMENTS EINRICHTEN"},
    "ra_setup_line1": {"en": "Create this file via SSH/text editor:",
                       "de": "Diese Datei per SSH/Texteditor anlegen:"},
    "ra_setup_line2": {"en": "Line 1: your RA username",
                       "de": "Zeile 1: dein RA-Benutzername"},
    "ra_setup_line3": {"en": "Line 2: your RA web API key (from your",
                       "de": "Zeile 2: dein RA-Web-API-Schluessel (aus"},
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
                           "de": "Hoch/Runter: waehlen   OK: bestaetigen   ESC: Einrichtung abbrechen"},
    "wizard_skip_hint": {"en": "OK: continue   ESC: skip this step",
                         "de": "OK: weiter   ESC: diesen Schritt ueberspringen"},
    "wizard_continue_hint": {"en": "Any key: continue", "de": "Beliebige Taste: weiter"},
    "wizard_video_reboot_note": {
        "en": "Saved - takes effect after the next restart. Setup continues now.",
        "de": "Gespeichert - wird erst nach dem naechsten Neustart aktiv. Die Einrichtung geht jetzt weiter."},
    "wizard_timezone_current": {"en": "Current: %s -> change", "de": "Aktuell: %s -> aendern"},
    "wizard_continue_option": {"en": "Continue", "de": "Weiter"},
    "wizard_download_now": {"en": "Download now", "de": "Jetzt herunterladen"},
    "wizard_download_skip": {"en": "Skip (can be done later from Scripts)",
                             "de": "Ueberspringen (spaeter jederzeit ueber Scripts moeglich)"},
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
                        "de": "MiSTer-OSD oeffnen (Settings/Buttons)"},
    "sys_video_crt":   {"en": "Menu video: CRT -> switch to HDMI",
                        "de": "Menue-Video: CRT -> auf HDMI wechseln"},
    "sys_video_hdmi":  {"en": "Menu video: HDMI -> switch to CRT",
                        "de": "Menue-Video: HDMI -> auf CRT wechseln"},
    "sys_video_suffix":{"en": " (reboot)", "de": " (Neustart)"},
    "sys_music_on":    {"en": "Music: On -> turn off", "de": "Musik: an -> ausschalten"},
    "sys_music_off":   {"en": "Music: Off -> turn on", "de": "Musik: aus -> einschalten"},
    "sys_music_source": {"en": "Music source: %s", "de": "Musik-Quelle: %s"},
    "sys_volume": {"en": "Volume: %d%%", "de": "Lautstaerke: %d%%"},
    "sys_language":    {"en": "Language: English -> switch to German",
                        "de": "Sprache: Deutsch -> auf Englisch wechseln"},
    "sys_configure_buttons": {"en": "Configure buttons",
                              "de": "Tastenbelegung anpassen"},
    "sys_reset_buttons":     {"en": "Reset to default buttons",
                              "de": "Auf Standardbelegung zuruecksetzen"},
    "sys_curated_on":  {"en": "Curated list (DB-matched only): ON -> turn off",
                        "de": "Kuratierte Liste (nur DB-Treffer): AN -> ausschalten"},
    "sys_curated_off": {"en": "Curated list (DB-matched only): OFF -> turn on",
                        "de": "Kuratierte Liste (nur DB-Treffer): AUS -> einschalten"},
    "sys_attract_on":  {"en": "Attract mode (screensaver): ON -> turn off",
                        "de": "Attract-Modus (Bildschirmschoner): AN -> ausschalten"},
    "sys_attract_off": {"en": "Attract mode (screensaver): OFF -> turn on",
                        "de": "Attract-Modus (Bildschirmschoner): AUS -> einschalten"},
    "sys_attract_delay": {"en": "Attract mode delay: %s -> next",
                          "de": "Attract-Modus Verzoegerung: %s -> naechste"},
    "sys_theme": {"en": "Color theme: %s -> next",
                  "de": "Farbschema: %s -> naechstes"},
    "sys_timezone": {"en": "Timezone: %s -> next",
                      "de": "Zeitzone: %s -> naechste"},
    "sys_network_wait_off": {"en": "Wait for NAS/network at boot: OFF -> turn on",
                             "de": "Beim Start auf NAS/Netzwerk warten: AUS -> einschalten"},
    "sys_network_wait_on": {"en": "Wait for NAS/network at boot: ON -> turn off",
                            "de": "Beim Start auf NAS/Netzwerk warten: AN -> ausschalten"},
    "sys_sfx_on": {"en": "Navigation sounds: ON -> turn off",
                   "de": "Navigations-Soundeffekte: AN -> ausschalten"},
    "sys_sfx_off": {"en": "Navigation sounds: OFF -> turn on",
                    "de": "Navigations-Soundeffekte: AUS -> einschalten"},
    "attract_hint": {"en": "Press any button to continue",
                     "de": "Beliebige Taste zum Fortfahren"},
    "scanning":  {"en": "Scanning: %s", "de": "Durchsuche: %s"},
    "recent_cat": {"en": "Recently Played", "de": "Zuletzt gespielt"},
    "continue_cat": {"en": "Continue Playing", "de": "Weiterspielen"},
    "ra_hunter_cat": {"en": "RA Achievement Hunter", "de": "RA-Erfolgsjaeger"},
    "collections_cat": {"en": "Collections", "de": "Sammlungen"},
    "collection_discovered_this_year": {"en": "Discovered in %s", "de": "%s entdeckt"},
    "collection_quick_games": {"en": "Quick games", "de": "Kurzweilige Spiele"},
    "favorites_cat": {"en": "Favorites", "de": "Favoriten"},
    "favorite_added": {"en": "Added to favorites", "de": "Zu Favoriten hinzugefuegt"},
    "favorite_removed": {"en": "Removed from favorites", "de": "Aus Favoriten entfernt"},
    "completed_added": {"en": "Marked as completed", "de": "Als durchgespielt markiert"},
    "completed_removed": {"en": "Completed mark removed", "de": "Durchgespielt-Markierung entfernt"},
    "sys_rescan":      {"en": "Rescan game list", "de": "Spieleliste neu einlesen"},
    "sys_redraw":      {"en": "Redraw display",   "de": "Anzeige neu aufbauen"},
    "sys_reboot":      {"en": "Restart MiSTer",   "de": "MiSTer neu starten"},
    "sys_quit":        {"en": "Quit frontend",    "de": "Frontend beenden"},
    "remap_prompt":    {"en": "Press a button for: %s",
                        "de": "Taste druecken fuer: %s"},
    "remap_action_up":     {"en": "Up",     "de": "Hoch"},
    "remap_action_down":   {"en": "Down",   "de": "Runter"},
    "remap_action_left":   {"en": "Left",   "de": "Links"},
    "remap_action_right":  {"en": "Right",  "de": "Rechts"},
    "remap_action_ok":     {"en": "OK / Start", "de": "OK / Start"},
    "remap_action_back":   {"en": "Back",   "de": "Zurueck"},
    "remap_action_osd":    {"en": "Open MiSTer menu", "de": "MiSTer-Menue oeffnen"},
    "remap_action_random": {"en": "Random game", "de": "Zufaelliges Spiel"},
    "remap_action_favorite": {"en": "Toggle favorite", "de": "Favorit umschalten"},
    "remap_action_completed": {"en": "Toggle completed", "de": "Durchgespielt umschalten"},
    "remap_done":      {"en": "Button mapping saved!",
                        "de": "Tastenbelegung gespeichert!"},
    "remap_cancelled": {"en": "Cancelled - keeping previous mapping",
                        "de": "Abgebrochen - alte Belegung bleibt aktiv"},
    "remap_esc_hint":  {"en": "(ESC to cancel)", "de": "(ESC zum Abbrechen)"},
    "remap_f9_blocked": {"en": "F9 is reserved for MiSTer - press another key",
                        "de": "F9 ist fuer MiSTer reserviert - andere Taste druecken"},
    "now_playing":     {"en": "Now playing: %s", "de": "Es laeuft: %s"},
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


def system_items(music_enabled=None, music_source="mp3", music_station=""):
    """Liefert die Inhalte der 'System'-Kategorie als Baumknoten mit
    thematischen Unterordnern (Nutzerwunsch: die Liste war auf 23
    flache Eintraege angewachsen, kaum noch ueberschaubar) - nutzt
    dieselbe Ordner-Navigation wie eigene ROM-Unterordner, kein neuer
    Code-Pfad noetig. Die Aktions-"kind"-Werte in jedem Eintrag bleiben
    UNVERAENDERT (siehe Aktions-Dispatch in run()) - nur die
    Gruppierung/Anzeige aendert sich, kein bestehendes Verhalten.

    music_source/music_station (neu, Nutzerwunsch: Rainwave-
    Internetradio als zweite Musikquelle, siehe CHANGES_RAINWAVE.md):
    fuer die Beschriftung des neuen "Musik-Quelle"-Eintrags."""
    crt = crt_menu_active()
    video = t("sys_video_crt") if crt else t("sys_video_hdmi")
    music_label = t("sys_music_on") if music_enabled else t("sys_music_off")
    music_src_label = (t("sys_music_source", "Radio - %s" % (music_station or "?"))
                       if music_source == "radio" else t("sys_music_source", "MP3"))
    volume_label = t("sys_volume", VOLUME)
    curated_label = t("sys_curated_on") if curated_only_active() \
        else t("sys_curated_off")
    attract_label = t("sys_attract_on") if attract_enabled() \
        else t("sys_attract_off")
    attract_delay_label = t("sys_attract_delay", format_attract_delay(load_attract_delay()))
    theme_names = THEME_NAMES_DE if CURRENT_LANG == "de" else THEME_NAMES_EN
    theme_label = t("sys_theme", theme_names.get(current_theme_name(), "?"))
    tz_label = t("sys_timezone", format_timezone_offset(load_timezone_offset()))
    netwait_label = t("sys_network_wait_on" if network_wait_enabled()
                      else "sys_network_wait_off")
    sfx_label = t("sys_sfx_on") if sfx_enabled_flag() else t("sys_sfx_off")
    ra_user, _ra_key = load_ra_config()
    ra_label = t("sys_ra_configured", ra_user) if ra_user else t("sys_ra_setup")

    def folder(*items):
        return {"folders": {}, "items": list(items)}

    return {
        "folders": {
            t("sys_group_ra"): folder(
                (ra_label, "ra_status", None),
            ),
            t("sys_group_stats"): folder(
                (t("top10_time_action"), "top10_time", None),
                (t("top10_launches_action"), "top10_launches", None),
                (t("sys_milestones_action"), "milestones", None),
                (t("sys_trophy_action"), "trophy_room", None),
                (t("sys_year_review_action"), "year_review", None),
                (t("sys_diary_action"), "diary", None),
            ),
            t("sys_group_display"): folder(
                (video + t("sys_video_suffix"), "crtmenu", None),
                (theme_label, "theme", None),
                (sfx_label, "sfx", None),
                (music_label, "music", None),
                (music_src_label, "music_source", None),
                (volume_label, "volume", None),
            ),
            t("sys_group_behavior"): folder(
                (t("sys_crt_test_action"), "crt_test", None),
                (curated_label, "curated", None),
                (attract_label, "attract", None),
                (attract_delay_label, "attract_delay", None),
                (tz_label, "timezone", None),
                (netwait_label, "network_wait", None),
            ),
            t("sys_group_input"): folder(
                (t("sys_language"), "language", None),
                (t("sys_configure_buttons"), "remap", None),
                (t("sys_reset_buttons"), "remap_reset", None),
            ),
            t("sys_group_info"): folder(
                (t("sys_help_action"), "help", None),
                (t("sys_setup_wizard"), "setup_wizard", None),
                (t("sys_secrets_action"), "secrets", None),
                (t("sys_credits_action"), "credits", None),
            ),
            t("sys_group_maintenance"): folder(
                (t("sys_osd"), "osd", None),
                (t("sys_rescan"), "rescan", None),
                (t("sys_redraw"), "redraw", None),
                (t("sys_reboot"), "reboot", None),
                (t("sys_quit"), "quit", None),
            ),
        },
        "items": [],
    }


def _node_has_any_meta(node, syskey):
    """Rekursiv prüfen, ob IRGENDWO im Baum ein Eintrag Metadaten hat -
    entscheidet, ob das Sicherheitsnetz (kein Filtern bei komplett
    fehlender Datenbank) greift."""
    for it in node["items"]:
        label, kind, arg = it
        meta = mra_meta(arg) if (syskey == "ARCADE" and kind == "core") \
              else ({} if syskey == "ARCADE" else get_meta(syskey, label))
        if meta:
            return True
    for sub in node["folders"].values():
        if _node_has_any_meta(sub, syskey):
            return True
    return False

def _filter_node_curated(node, syskey):
    """Rekursiv jeden Knoten auf katalogisierte Eintraege einschraenken.
    Ordner, die dadurch komplett leer werden (keine Items, keine
    nicht-leeren Unterordner), fallen ganz weg."""
    kept_items = []
    for it in node["items"]:
        label, kind, arg = it
        meta = mra_meta(arg) if (syskey == "ARCADE" and kind == "core") \
              else ({} if syskey == "ARCADE" else get_meta(syskey, label))
        if meta:
            kept_items.append(it)
    kept_folders = {}
    for fname, sub in node["folders"].items():
        filtered_sub = _filter_node_curated(sub, syskey)
        if filtered_sub["folders"] or filtered_sub["items"]:
            kept_folders[fname] = filtered_sub
    return {"folders": kept_folders, "items": kept_items}

def filter_curated(name, node, syskey):
    """Wenn der 'Nur katalogisierte Spiele'-Schalter aktiv ist (System-
    Menue), auf Eintraege einschraenken, die einen Treffer in der
    libretro-Datenbank haben (von mister_gameinfo.py geladen,
    meta/<System>.json bzw. fuer Arcade die MRA-Datei selbst) - das ist
    die "Source of Authority", die Hyperspin frueher mit seinen
    XML-Datenbanken pro System bereitgestellt hat: nur tatsaechlich
    katalogisierte, offiziell erschienene Spiele, keine Hacks/Homebrew/
    unbekannten Dumps. Arbeitet rekursiv ueber die komplette
    Ordnerstruktur - leer gewordene Unterordner fallen weg.

    Sicherheitsnetz: Hat ein System UEBERHAUPT keine Metadaten (z.B.
    weil mister_gameinfo.py dafuer noch nie gelaufen ist), wird NICHT
    gefiltert - sonst wuerde die Liste faelschlich komplett leer
    werden, nur weil noch keine Datenbank geladen wurde."""
    if not syskey or not (node["folders"] or node["items"]):
        return (name, node, syskey)
    if not _node_has_any_meta(node, syskey):
        return (name, node, syskey)
    return (name, _filter_node_curated(node, syskey), syskey)

CURATED_FLAG = "/media/fat/frontend/curated_only"
ATTRACT_DISABLED_FLAG = "/media/fat/frontend/attract_disabled"
ATTRACT_DELAY_FILE = "/media/fat/frontend/attract_delay"
# NEUES FEATURE (Nutzerwunsch: "fuer denn attract Modus eventuell aus
# nur an und aus zu machen noch eine Einstellung dabei damit man sich
# selber aussuchen kann ab wieviel Minuten der anfaengt"): bisher war
# die Verzoegerung mit ATTRACT_IDLE_SECONDS = 90 fest verdrahtet, nur
# AN/AUS liess sich einstellen (siehe attract_enabled()). Jetzt
# zusaetzlich einstellbar - gleiches Muster wie die bestehende
# Zeitzonen-Einstellung (load/save/cycle-Dreiklang mit einer festen
# Schrittliste).
ATTRACT_DELAY_STEPS = [30, 60, 90, 120, 180, 300, 600, 900]   # Sekunden

def load_attract_delay():
    try:
        with open(ATTRACT_DELAY_FILE) as f:
            val = int(f.read().strip())
            return val if val in ATTRACT_DELAY_STEPS else 90
    except (OSError, ValueError):
        return 90   # bisheriger fester Standardwert bleibt der Default

def save_attract_delay(seconds):
    try:
        os.makedirs(os.path.dirname(ATTRACT_DELAY_FILE), exist_ok=True)
        with open(ATTRACT_DELAY_FILE, "w") as f:
            f.write(str(seconds))
    except OSError:
        pass

def cycle_attract_delay():
    """Naechsten Wert in ATTRACT_DELAY_STEPS waehlen (wrap-around).
    Liefert den neuen Wert in Sekunden."""
    current = load_attract_delay()
    try:
        idx = ATTRACT_DELAY_STEPS.index(current)
    except ValueError:
        idx = -1
    new_val = ATTRACT_DELAY_STEPS[(idx + 1) % len(ATTRACT_DELAY_STEPS)]
    save_attract_delay(new_val)
    return new_val

def format_attract_delay(seconds):
    """z.B. '30s', '2min', '10min' - fuer die Menu-Beschriftung."""
    if seconds < 60:
        return "%ds" % seconds
    if seconds % 60 == 0:
        return "%dmin" % (seconds // 60)
    return "%.1fmin" % (seconds / 60)

ATTRACT_IDLE_SECONDS = 90   # so lange ohne Eingabe, bevor der Attract-
                            # Modus (Bildschirmschoner) automatisch startet
                            # - BLEIBT als Standardwert/Sicherheitsnetz
                            # bestehen (siehe load_attract_delay()), wird
                            # aber nicht mehr direkt fuer den eigentlichen
                            # Check verwendet (siehe next_action()).
ATTRACT_CHANGE_SECONDS = 6  # wie lange ein Spiel im Attract-Modus gezeigt wird
COVER_SETTLE = 0.15         # s nach letzter Eingabe, bis waehrend des
                            # Scrollens uebersprungene Cover nachgeladen
                            # werden (haelt das Scrollen selbst fluessig)

def attract_enabled():
    """Standardmaessig AN (im Gegensatz zu curated_only_active(), das
    standardmaessig AUS ist) - die Datei bedeutet hier 'abgeschaltet',
    nicht 'aktiviert'."""
    return not os.path.exists(ATTRACT_DISABLED_FLAG)

def toggle_attract_mode():
    existed_before = os.path.exists(ATTRACT_DISABLED_FLAG)
    if existed_before:
        try:
            os.remove(ATTRACT_DISABLED_FLAG)
        except OSError as e:
            LOG("toggle_attract_mode: Loeschen der Markierungsdatei "
                "fehlgeschlagen: %s" % e)
    else:
        try:
            dirname = os.path.dirname(ATTRACT_DISABLED_FLAG)
            if dirname:
                os.makedirs(dirname, exist_ok=True)
            open(ATTRACT_DISABLED_FLAG, "w").close()
        except OSError as e:
            LOG("toggle_attract_mode: Anlegen der Markierungsdatei "
                "fehlgeschlagen: %s" % e)
    LOG("toggle_attract_mode: vorher %s -> jetzt %s (Datei existiert: %s)"
        % ("AUS" if existed_before else "AN",
           "AN" if existed_before else "AUS",
           os.path.exists(ATTRACT_DISABLED_FLAG)))

def curated_only_active():
    return os.path.exists(CURATED_FLAG)

def toggle_curated_only():
    if os.path.exists(CURATED_FLAG):
        try:
            os.remove(CURATED_FLAG)
        except OSError:
            pass
    else:
        try:
            dirname = os.path.dirname(CURATED_FLAG)
            if dirname:
                os.makedirs(dirname, exist_ok=True)
            open(CURATED_FLAG, "w").close()
        except OSError:
            pass

def _letter_of(name):
    for ch in name:
        if ch.isalnum():
            return ch.upper()
    return "#"

def jump_to_letter(names, cur_i, ch):
    """Index des naechsten Eintrags (zyklisch, ab cur_i+1 gesucht),
    dessen Anfangsbuchstabe ch entspricht. Mehrfaches Druecken derselben
    Taste springt dadurch der Reihe nach durch alle Treffer - wie die
    Direktsprung-Suche in klassischen Dateibrowsern."""
    n = len(names)
    if n == 0:
        return cur_i
    for step in range(1, n + 1):
        idx = (cur_i + step) % n
        if _letter_of(names[idx]) == ch:
            return idx
    return cur_i

def current_core():
    try:
        return open(CORENAME).read().strip("\x00 \n\r\t")
    except OSError:
        return ""

def launch_core(path):
    with open(MISTER_CMD, "w") as f:
        f.write("load_core " + path)

# ----------------------------------------------------------------------------
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
            elif not NTP_SYNC_OK:
                # Wahrscheinlichste Erklaerung fuer einen fehlgeschlagenen
                # Abruf direkt beim Start: die Systemuhr war noch falsch
                # (MiSTer hat keine batteriegepufferte Uhr), wodurch die
                # HTTPS-Zertifikatspruefung fehlschlaegt - unabhaengig
                # davon, ob der RA-Server eigentlich erreichbar waere.
                # Neuversuch, sobald die Zeit sich (per _maybe_retry_ra())
                # doch noch synchronisiert.
                self._ra_retry_next = time.monotonic() + 30.0

        self.build_categories()
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
        self.cats.extend((n, _wrap_flat(it), sk)
                         for n, it, sk in scan_cores(skip_dir=marked_recent))
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
        scripts = scan_scripts()
        if scripts:
            self.cats.append(("Scripts", _wrap_flat(scripts), None))
        self.cats.append(("System", system_items(
            self.music.enabled, self.music.source,
            rainwave.station_name(self.music.radio.sid) if self.music.radio else ""
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
        self.draw()

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
                self.cats[i] = (name, system_items(
                    self.music.enabled, self.music.source,
                    rainwave.station_name(self.music.radio.sid) if self.music.radio else ""
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
        reinen Ordnernamen (zum Nachschlagen beim Reinwechseln)."""
        node = self._current_node()
        folder_names = sorted(node["folders"].keys(), key=str.lower)
        folder_entries = [(fname + "/", "folder", fname)
                          for fname in folder_names]
        return folder_entries + node["items"]

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
        nicht auf, siehe build_categories())."""
        if not ra_enabled() or not self._ra_lookup:
            return None
        self._attract_pool = None   # sicherstellen, dass der frische
                                    # Kategorienstand gescannt wird,
                                    # nicht ein evtl. veralteter Cache
        pool = self._attract_games_pool()
        by_system = {}
        for name, syskey, arg in pool:
            result = lookup_ra_progress(self._ra_lookup, name, syskey)
            if result is None:
                continue
            earned, total = result
            if total > 0 and earned == 0:
                by_system.setdefault(syskey, []).append((name, total, arg))
        if not by_system:
            return None
        folders = {}
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
        volle Breite."""
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
        return {"s": s, "ox": ox, "oy": oy, "list_x": list_x,
                "list_y": list_y, "list_right": list_right,
                "rowh": rowh, "footer_y": footer_y, "visible": visible}

    def draw(self, message=None):
        self._sync_track_marquee()
        self._maybe_retry_ra()
        self._maybe_retry_clock()
        if self.attract_mode:
            self.draw_attract()
            return
        # Wenn der Bestaetigungsdialog kommt, soll die Seite dahinter
        # NICHT extra geflippt werden - sonst blitzt fuer einen Frame
        # der Hintergrund ohne Dialog auf, bevor der Dialog erscheint
        # (genau das war das Flackern beim Wechseln zwischen den
        # Optionen).  Nur der letzte Zeichenschritt flippt.
        if self.page == 0:
            self.draw_page_cats(message, flip=not self.confirm_quit)
        else:
            self.draw_page_items(message, flip=not self.confirm_quit)
        if self.confirm_quit:
            self.draw_confirm_dialog()

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
        if H >= 720:
            hd = _art_path_in(ART_HD, syskey, name)
            art = ART.get_scaled(hd, cover_max_w, cover_max_h)
        if art is None:
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
    def draw_page_cats(self, message=None, flip=True):
        fb = self.fb
        W, H = fb.width, fb.height
        L = self.layout_cats()
        s, ox, oy = L["s"], L["ox"], L["oy"]
        rowh, y0, visible = L["rowh"], L["y0"], L["visible"]
        self.cats_visible = visible

        fb.clear(C_BG)
        fb.text(ox, oy, "MiSTer", 3 * s, C_TITLE, C_BG)
        fb.text(ox, oy + 28 * s, t("categories", len(self.cats)), s, C_DIM, C_BG)

        # Songtitel als Laufschrift NEBEN dem Logo (nicht darunter,
        # sonst ueberschneidet er sich mit dem Listenbeginn). Davor
        # ein paar kleine animierte Balken (rein dekorativ, keine
        # echte Lautstaerke-Messung) als visueller "hier laeuft was"-
        # Hinweis.
        logo_w = len("MiSTer") * 8 * 3 * s
        eq_w = 0
        if self._track_mq_name:
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
        # BUGFIX (uebernommen aus einer parallelen Fehlerdiagnose - siehe
        # Kopfkommentar-Changelog fuer die volle Herleitung): die
        # markierte Zeile hat einen Leucht-Rand (glow_border_fast()), der
        # ABSICHTLICH etwas ueber die eigene Zeile hinausragt. Beim obigen
        # Durchlauf in AUFSTEIGENDER Reihenfolge wird die Zeile DARUEBER
        # zuerst gezeichnet, die Markierung danach - ihr Glow blutet dabei
        # auf den bereits fertigen oberen Nachbarn, ohne dass ihn danach
        # etwas uebermalt (nach unten faellt das nie auf, da die naechste
        # Zeile im selben Durchlauf ohnehin erst DANACH kommt). Zeile
        # direkt darueber (falls sichtbar) hier einmal sauber neu zeichnen.
        if (self.cat_scroll <= self.cat_i - 1 < end
                and self.cat_scroll <= self.cat_i < end):
            self._draw_cat_row(self.cat_i - 1, self.cat_i - 1 - self.cat_scroll,
                               L, maxc)
        # BUGFIX (Sonderfall, von der Korrektur oben nicht abgedeckt):
        # steht die Markierung auf der ALLERERSTEN sichtbaren Zeile, gibt
        # es keine Listenzeile darueber, die den Bleed auffangen koennte -
        # der Glow blutet stattdessen nach oben in die Kopfzeile hinein
        # ("X categories"-Text). Der Glow-Rand ist ein Streifen ueber die
        # VOLLE Zeilenbreite, nicht nur ueber die Textbreite - deshalb
        # zuerst ein rect() ueber die volle Breite (aber nur ueber die vom
        # Glow tatsaechlich erreichte Hoehe), dann der Text neu.
        if self.cat_i == self.cat_scroll:
            max_p = 3 * 2 * s
            gx = ox - 4 * s
            gw = list_right - ox + 8 * s
            clear_top = y0 - 4 * s - max_p
            clear_bot = y0 - 4 * s
            fb.rect(gx, clear_top, gw, clear_bot - clear_top, C_BG)
            fb.text(ox, oy + 28 * s, t("categories", len(self.cats)),
                    s, C_DIM, C_BG)

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
        if flip:
            fb.flip()

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
        bg = self._pulsed(accent) if sel else C_BG
        if not sel:
            fb.rect(ox - 4 * s, y - 4 * s, list_right - ox + 8 * s,
                    rowh - 4 * s, C_BG)
        else:
            fb.rect(ox - 4 * s, y - 4 * s, list_right - ox + 8 * s,
                    rowh - 4 * s, bg)
            gx, gy = ox - 4 * s, y - 4 * s
            gw, gh = list_right - ox + 8 * s, rowh - 4 * s
            for ring, a in enumerate((0.22, 0.13, 0.06)):
                p = (ring + 1) * 2 * s
                fb.glow_border_fast(gx - p, gy - p, gw + 2 * p, gh + 2 * p,
                                    C_BG, accent, a, thickness=2 * s)
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

    def _maybe_retry_ra(self):
        """Periodisch (aus draw(), wie _network_connected()) geprueft:
        falls RA eingerichtet ist, der letzte Abrufversuch aber
        fehlgeschlagen ist - moeglicherweise wegen einer beim Start noch
        falschen Systemuhr, siehe __init__() - wird in wachsenden
        Abstaenden (30s, 60s, 120s, 240s, gedeckelt bei 300s) ein
        Neuversuch unternommen. Netzwerk-Aufrufe laufen dabei in einem
        Hintergrund-Thread, damit die Navigation nie blockiert wird.
        Hoert nach 5 Versuchen von selbst auf (kein endloses Nachfragen,
        falls RA dauerhaft nicht erreichbar ist)."""
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
        need_ntp_first = not NTP_SYNC_OK
        def worker():
            if need_ntp_first:
                sync_system_clock_from_ntp()
                if not NTP_SYNC_OK:
                    return   # weiterhin keine verlaessliche Uhr - beim naechsten Mal wieder
            ra_data = fetch_ra_progress_bounded(timeout=5.0)
            if ra_data is not None:
                self._ra_lookup = build_ra_lookup(ra_data)
                self._ra_fetch_ok = True
        threading.Thread(target=worker, daemon=True).start()

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
        if NTP_SYNC_OK or self._clock_retry_count >= 5:
            return
        now = time.monotonic()
        if now < self._clock_retry_next:
            return
        self._clock_retry_count += 1
        backoff = min(30.0 * (2 ** (self._clock_retry_count - 1)), 300.0)
        self._clock_retry_next = now + backoff
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

    def _draw_dynamic_cats(self):
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
        Differenzvergleich gegen einen vollen Aufbau getestet."""
        fb = self.fb
        H = fb.height
        L = self.layout_cats()
        s, ox, oy = L["s"], L["ox"], L["oy"]
        rowh, y0, visible = L["rowh"], L["y0"], L["visible"]
        list_right = L["list_right"]

        y_min, y_max = H, 0

        logo_w = len("MiSTer") * 8 * 3 * s
        if self._track_mq_name:
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
            max_p = 3 * 2 * s
            fb.rect(gx - max_p, gy - max_p, gw + 2 * max_p, gh + 2 * max_p, C_BG)
            fb.rect(gx, gy, gw, gh, bg)
            for ring, a in enumerate((0.22, 0.13, 0.06)):
                p = (ring + 1) * 2 * s
                fb.glow_border_fast(gx - p, gy - p, gw + 2 * p, gh + 2 * p,
                                    C_BG, accent, a, thickness=2 * s)
            maxc = max(4, (list_right - ox) // (8 * s))
            label = name if len(name) <= maxc else name[:max(1, maxc - 1)] + "~"
            fb.text(ox, y, label, s, C_TITLE, bg)
            y_min = min(y_min, gy - max_p)
            y_max = max(y_max, gy - max_p + gh + 2 * max_p)
            # BUGFIX (uebernommen aus einer parallelen Fehlerdiagnose,
            # siehe draw_page_cats()/_draw_dynamic_items()): die breite
            # Randloeschung oben (max_p, wegen des ueber die eigene Zeile
            # hinausragenden Glow-Rands) reicht bisher bis in die Zeile
            # DARUEBER hinein - und NICHTS hat sie danach wieder
            # aufgefrischt. Bei bis zu 12.5 Ticks/Sekunde waere der obere
            # Nachbar dadurch praktisch dauerhaft teilweise geloescht
            # geblieben. Zeile darueber (falls sichtbar) bzw. die
            # Kopfzeile (falls die Markierung ganz oben steht) hier
            # ebenfalls wieder sauber zeichnen.
            prev_row = row - 1
            if prev_row >= 0:
                self._draw_cat_row(self.cat_i - 1, prev_row, L, maxc)
                prev_y = y0 + prev_row * rowh
                y_min = min(y_min, prev_y - 4 * s)
                y_max = max(y_max, prev_y - 4 * s + rowh - 4 * s)
            else:
                # Keine Listenzeile darueber vorhanden - der Glow blutet
                # stattdessen in die Kopfzeile ("X categories"-Text)
                # hinein. Glow-Rand ist ein Streifen ueber die VOLLE
                # Zeilenbreite (siehe ausfuehrliche Begruendung in
                # draw_page_cats()) - deshalb erst ein rect() ueber die
                # volle Breite (nur ueber die vom Glow tatsaechlich
                # erreichte Hoehe), dann der Text neu.
                clear_top = y0 - 4 * s - max_p
                clear_bot = y0 - 4 * s
                fb.rect(gx, clear_top, gw, clear_bot - clear_top, C_BG)
                fb.text(ox, oy + 28 * s, t("categories", len(self.cats)),
                        s, C_DIM, C_BG)
                y_min = min(y_min, clear_top)
                y_max = max(y_max, oy + 36 * s)

        if y_max > y_min:
            fb.flip_rows(y_min, y_max - y_min)

    def _draw_navigate_items(self, old_item_i):
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
        old_has_prev = old_item_i > self.scroll
        old_has_next = (old_item_i + 1 < self.scroll + visible
                        and old_item_i + 1 < total)
        old_y_top, old_max_p = self._clear_row_glow_margin(old_item_i)
        regions = []
        if old_y_top is not None:
            if old_has_prev:
                self.draw_list_row(old_item_i - 1)
            self.draw_list_row(old_item_i)
            if old_has_next:
                self.draw_list_row(old_item_i + 1)
            s, rowh = v["s"], v["rowh"]
            flip_y0 = old_y_top - (rowh if old_has_prev else old_max_p)
            flip_y1 = (old_y_top + rowh - 2 * s + old_max_p
                      + (rowh if old_has_next else 0))
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
        if has_art:
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
            fb.flip_rows(y0, y1 - y0)
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
        max_p = 3 * 2 * s
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
        y_top, max_p = self._clear_row_glow_margin(self.item_i)
        has_prev = self.item_i > self.scroll
        has_next = (self.item_i + 1 < self.scroll + self.items_visible
                    and self.item_i + 1 < total)
        self.draw_list_row(self.item_i)
        if has_prev:
            self.draw_list_row(self.item_i - 1)
        if has_next:
            self.draw_list_row(self.item_i + 1)
        # Grosszuegiger Bereich, der die tatsaechlich aufgefrischten
        # Zeilen (markierte Zeile + evtl. Nachbarn) komplett abdeckt -
        # ein paar zusaetzliche Pixel zu flippen kostet kaum etwas,
        # verglichen mit dem Risiko, eine aufgefrischte Nachbarzeile
        # nur teilweise auf den Schirm zu bringen.
        flip_y0 = y_top - (rowh if has_prev else max_p)
        flip_y1 = y_top + rowh - 2 * s + max_p + (rowh if has_next else 0)
        if flip:
            fb.flip_rows(flip_y0, flip_y1 - flip_y0)
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
            eq_w = 4 * (3 * s + 2 * s) + 10 * s
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
            fb.flip_rows(y, h)
        else:
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
            cur_bg = getattr(self, "_cur_bg", None)
            row_w = (W - 2 * ox)
            if cur_bg is None:
                fb.rect(ox, footer_y, row_w, h, C_BG)
            else:
                buflen, need = len(fb.buf), row_w * 4
                for yy in range(max(0, footer_y), min(fb.height, footer_y + h)):
                    off = yy * fb.stride + ox * 4
                    end = off + need
                    if end > buflen or end > len(cur_bg) or off < 0:
                        continue
                    chunk = cur_bg[off:end]
                    if len(chunk) == need:
                        fb.buf[off:end] = chunk
            track_display = self.track_marquee_text(foot_maxc)
            if track_display:
                fb.text(ox, footer_y, track_display, s, C_DIM)
            fb.flip_rows(footer_y, h)

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
        art = ART.get_scaled(os.path.join(SYSART_BASE, "%s.art" % syskey),
                             art_w - 2 * pad, box_h) if syskey else None
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
        _t0 = time.monotonic()
        r = self._draw_page_items_impl(message=message, flip=flip)
        _dt = time.monotonic() - _t0
        if _dt > 0.040:
            LOG("PERF draw_page_items: %.0f ms" % (_dt * 1000))
        return r

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

        self._cur_bg = BG.get(syskey, fb) if syskey else None
        _tb = time.monotonic()
        if self._cur_bg is not None:
            fb.buf[:] = self._cur_bg
        else:
            fb.clear(C_BG)
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
        _tr = time.monotonic()
        for idx in range(self.scroll, end):
            self.draw_list_row(idx, bg_fresh=self._cur_bg is not None)
        # BUGFIX (uebernommen aus einer parallelen Fehlerdiagnose - siehe
        # Kopfkommentar-Changelog): der obige Durchlauf zeichnet die
        # Zeilen in AUFSTEIGENDER Reihenfolge - die markierte Zeile (samt
        # ihrem absichtlich etwas ueber die eigene Zeile hinausragenden
        # Glow-Rand, siehe draw_list_row()/glow_border_fast()) wird dabei
        # NACH ihrem oberen Nachbarn gezeichnet. Der Glow blendet dabei
        # direkt auf den bereits fertigen oberen Nachbarn - und NICHTS
        # zeichnet ihn danach nochmal darueber, der Bleed bleibt also
        # dauerhaft sichtbar (nicht nur kurz waehrend eines Redraws).
        # Nach unten faellt das nie auf, weil die jeweils naechste Zeile
        # im selben Durchlauf ohnehin erst DANACH gezeichnet wird und
        # den Bleed automatisch uebermalt. Fix: die Zeile direkt UEBER
        # der Markierung (falls sichtbar) wird hier einmal mit vollem
        # Hintergrund-Restore (bg_fresh=False) neu gezeichnet - malt
        # einen eventuellen Bleed zuverlaessig weg, ohne den schnellen
        # bg_fresh-Pfad fuer alle anderen Zeilen im Hauptdurchlauf zu
        # verlangsamen.
        if self.scroll <= self.item_i - 1 < end and self.scroll <= self.item_i < end:
            self.draw_list_row(self.item_i - 1, bg_fresh=False)
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
        if flip:
            _tf = time.monotonic()
            fb.flip()
            _fdt = time.monotonic() - _tf
        else:
            _fdt = 0.0
        _bg = getattr(self, "_perf_bg", 0); _rw = getattr(self, "_perf_rows", 0)
        _ar = getattr(self, "_perf_art", 0); _nr = getattr(self, "_perf_nrows", 0)
        if (_bg + _rw + _ar + _fdt) > 0.1:
            LOG("PERF split: bg=%.0f rows=%.0f(%d) art=%.0f flip=%.0f ms"
                % (_bg * 1000, _rw * 1000, _nr, _ar * 1000, _fdt * 1000))
        self._perf_art = 0

    def draw_confirm_dialog(self):
        """Beenden-Bestaetigung: ueberlagert die aktuelle Seite mit
        einem kleinen Dialog. Links waehlt 'Ja', Rechts waehlt 'Nein'
        (Standardauswahl), Enter bestaetigt die Auswahl. ESC/B im
        Dialog bricht sofort ab (sicherer Standard)."""
        fb = self.fb
        W, H = fb.width, fb.height
        s = max(1, H // 360)
        msg = t("quit_confirm")
        maxc = max(10, (W - 40 * s) // (8 * s))
        lines = self._wrap(msg, maxc, max_lines=2)
        labels = [t("yes"), t("no")]

        line_h = 12 * s
        btn_h = 16 * s
        btn_w = max(len(l) for l in labels) * 8 * s + 16 * s
        gap = 14 * s
        pad = 12 * s

        text_w = max(len(ln) for ln in lines) * 8 * s
        buttons_w = btn_w * 2 + gap
        box_w = min(W - 16 * s, max(text_w, buttons_w) + 2 * pad)
        box_h = pad + len(lines) * line_h + gap + btn_h + pad
        x0 = (W - box_w) // 2
        y0 = (H - box_h) // 2

        fb.rect(x0, y0, box_w, 2 * s, C_ACCENT)
        fb.rect(x0, y0 + 2 * s, box_w, box_h - 2 * s, C_PANEL)

        ty = y0 + pad
        for ln in lines:
            tw = len(ln) * 8 * s
            fb.text(x0 + (box_w - tw) // 2, ty, ln, s, C_TITLE, C_PANEL)
            ty += line_h

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
        if bg_fresh and cur_bg is not None:
            # Voller Redraw: der Hintergrund wurde gerade erst komplett in
            # den Puffer kopiert - die Zeile NICHT nochmal Zeile-fuer-Zeile
            # wiederherstellen (das war der teure, hier redundante Teil).
            # Nur die Auswahl braucht noch ihr farbiges Feld obendrauf.
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

        if sel:
            for ring, a in enumerate((0.20, 0.11, 0.05)):
                p = (ring + 1) * 2 * s
                fb.glow_border_fast(x0 - p, y_top - p, rw + 2 * p,
                                    rowh - 2 * s + 2 * p, C_BG, accent, a,
                                    thickness=2 * s)

        full = v["items"][idx][0]
        item_kind = v["items"][idx][1]
        # Markierung nur bei echten Spielen, per Namen im bereits
        # geladenen Speicher-Cache nachgeschlagen (kein Datei-Zugriff
        # hier - das waere bei haeufigem Neuzeichnen ein echtes
        # Performance-Problem).
        is_fav = item_kind == "game" and full in self._favorites_set
        is_done = item_kind == "game" and hasattr(self, "_completed_set") \
            and full in self._completed_set
        prefix = ("* " if is_fav else "") + ("V " if is_done else "")
        maxc = (list_right - list_x - 8 * s) // (8 * s) - len(prefix)
        if sel:
            # Markierte Zeile: voller Name, bei Bedarf als Laufschrift
            if len(full) > maxc:
                off = min(self.mq_off, max(0, len(full) - maxc))
                label = full[off:off + maxc]
            else:
                label = full
        else:
            label = display_name(full)
            if len(label) > maxc:
                label = label[:max(1, maxc - 1)] + "~"
        label = prefix + label
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
        self.fb.flip_rows(y - 3 * v["s"], v["rowh"])

    def marquee_reset(self):
        self.mq_off = 0
        self.mq_pause = 4
        self._mq_tick_next = 0.0

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
                if need_mq:
                    self.marquee_tick()
                # Beim schnellen Scrollen uebersprungene Cover ~COVER_SETTLE
                # nach dem letzten Tastendruck EINMAL nachladen (voller
                # Aufbau der Listenseite - defer ist dann aus, also werden
                # sie jetzt dekodiert). Passiert nur einmal pro Stillstand,
                # nicht bei jedem Schleifendurchlauf.
                if (not self._settled_redrawn and self.page == 1 and
                        time.monotonic() - self._last_input_time >= COVER_SETTLE):
                    self.draw_page_items()
                    self._settled_redrawn = True
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
                if self._track_mq_name and self._eq_tick():
                    redraw_dynamic = True
                if self._pulse_tick():
                    redraw_dynamic = True
                if redraw_marquee or redraw_dynamic:
                    if self.confirm_quit:
                        # Beenden-Dialog liegt ueber allem - der leichte
                        # Pfad wuerde darunter durchscheinen, deshalb
                        # hier immer der volle, sichere Aufbau.
                        self.draw()
                    else:
                        # Deutlich billiger als der komplette Aufbau
                        # (~5ms voller Aufbau vs. ~0.4ms hier auf HDMI
                        # gemessen) - genau die Ticks, die am
                        # haeufigsten laufen (bis zu 12.5x/Sekunde).
                        if redraw_dynamic:
                            if self.page == 0:
                                self._draw_dynamic_cats()
                            else:
                                self._draw_dynamic_items()
                        if redraw_marquee:
                            self._draw_dynamic_track_marquee()
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
        if H >= 720:
            hd = _art_path_in(ART_HD, syskey, lookup_name)
            art = ART.get_scaled(hd, avail_w, cover_h)
        if art is None:
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
                        for name, desc, points, badge, earned, date in achievements:
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
        if ra_watch_stop:
            ra_watch_stop.set()
        played_seconds = time.monotonic() - play_start
        record_playtime(label, played_seconds, syskey=syskey)
        record_yearly_playtime(label, played_seconds, syskey=syskey)
        record_diary_entry(label, played_seconds, syskey=syskey)
        check_hidden_session_achievements(play_start_wall, time.monotonic() - play_start)
        self._playtime_cache = load_playtime()
        time.sleep(1.0)
        self.music.resume_after_core()
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
        CRT/HDMI-Profil direkt an boxart_download.sh durchreichen,
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
        try:
            tty = open("/dev/tty1", "r+b", buffering=0)
        except OSError:
            tty = None
        cmd = ["/bin/bash", path] + (list(args) if args else [])
        # Bildschirm dem Script ueberlassen
        try:
            if tty:
                tty.write(b"\x1b[2J\x1b[H")     # Konsole loeschen
                subprocess.call(cmd,
                                stdin=tty, stdout=tty, stderr=tty,
                                env=dict(os.environ, TERM="linux",
                                         HOME="/root"))
                tty.write(b"\n-- Script finished, press any key --\n")
            else:
                subprocess.call(cmd)
        finally:
            if tty:
                tty.close()
        self.inp.read_action()                    # auf Eingabe warten
        self.music.resume_after_core()
        self.back_to_frontend()

    def draw_core_choice_screen(self, syskey, display_name):
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
        explizit None, und NUR das bricht wirklich ab."""
        fb = self.fb
        W, H = fb.width, fb.height
        s = max(1, H // 360)
        ox = W * OVERSCAN_X // 100
        oy = H * OVERSCAN_Y // 100
        accent = accent_for(syskey)
        choice = 0   # 0 = normaler Core, 1 = RA-Core
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
        idx = 0 if CURRENT_LANG == "de" else 1
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
            self.run_script(os.path.join(SCRIPTS_DIR, "boxart_download.sh"),
                            args=[profile])

        # Schritt 6: Gameinfo-Download - optional, ueberspringbar.
        do_gameinfo = self._wizard_choice(
            t("wizard_step_title", 6, total, t("wizard_step_gameinfo")),
            [t("wizard_download_now"), t("wizard_download_skip")], initial=0)
        if do_gameinfo is None:
            return
        if do_gameinfo == 0:
            self.run_script(os.path.join(SCRIPTS_DIR, "gameinfo_download.sh"))

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

    def _on_secret_triggered(self, secret_id, is_new):
        """Wird aufgerufen, sobald ein Geheimcode
        erfolgreich erkannt wurde (siehe run()) - fuehrt die eigentliche
        Aktion aus (Theme wechseln/Entwicklerraum oeffnen/Sound
        abspielen), JEDES MAL wenn der Code eingegeben wird, nicht nur
        beim allerersten Mal - passend zum Vorbild echter Cheat-Codes,
        die man beliebig oft eingeben kann. Die "neu freigeschaltet"-
        Meldung erscheint dagegen nur einmalig (is_new)."""
        if is_new:
            play_sfx("achievement", music_playing=self.music._proc_alive())
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
            self.draw()
        elif secret_id == "entwicklerraum":
            self.draw_dev_room_screen()
            self.draw()
        elif secret_id == "secret_sound":
            play_sfx("secret_found", music_playing=self.music._proc_alive())
            if not is_new:
                self.draw(message=t("secret_sound_replay"))

    def _check_achievement_popup(self):
        """Prueft auf neu erreichte Erfolge und liefert bei einem
        Treffer die fertige Popup-Nachricht (spielt dabei den
        Erfolgston ab) - sonst None. Aufrufer entscheiden selbst, ob/
        wie sie das anzeigen (z.B. anstelle ihrer eigenen
        Standardmeldung wie "Favorit hinzugefuegt")."""
        newly = check_new_achievements()
        if not newly:
            return None
        play_sfx("achievement", music_playing=self.music._proc_alive())
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
        for name, desc, points, badge, earned, date in achievements:
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
                name, desc, points, badge, earned, date = achievements[i]
                scaled_icon = get_processed_icon(badge, earned)
                if scaled_icon:
                    self.blit(ox, y, icon_size, icon_size, scaled_icon)
                mark = "[x] " if earned else "[ ] "
                line1 = "%s%s (%d)" % (mark, name, points)
                color = C_TEXT if earned else C_DIM
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
                t("secrets_summary", len(unlocked), len(SECRET_CODES)), maxc):
            rows.append((line, accent_for(None), 0))
        for line in self._wrap_text(t("secrets_keyboard_hint"), maxc):
            rows.append((line, C_DIM, 0))
        rows.append(("", C_DIM, 0))

        order = ["secret_theme_1", "entwicklerraum", "secret_sound"]
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
        - keine neue Datenquelle noetig."""
        fb = self.fb
        W, H = fb.width, fb.height
        s = max(1, H // 360)
        ox = W * OVERSCAN_X // 100
        oy = H * OVERSCAN_Y // 100
        fb.clear(C_BG)

        title = t("dev_room_title")
        title_scale = self._fit_scale(title, W - 2 * ox, s + 1)
        fb.text(ox, oy, title, title_scale, C_TITLE, C_BG)

        level = compute_frontend_level()
        secrets = _load_secrets_unlocked()

        y = oy + 50 * s
        line_h = 26 * s

        def line(text, color=C_TEXT):
            nonlocal y
            fb.text(ox, y, text, s, color, C_BG)
            y += line_h

        line(t("dev_room_level", level, FRONTEND_LEVEL_MAX), C_ACCENT)
        line(t("dev_room_secrets", len(secrets), len(SECRET_CODES)), C_ACCENT)
        y += line_h // 2
        line(t("dev_room_credits_1"), C_DIM)
        line(t("dev_room_credits_2"), C_DIM)
        y += line_h
        line(t("dev_room_thanks"), C_TEXT)

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
        aber nirgends erwaehnt)."""
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
            ("item", "help_nav_letter"),
            ("header", "help_section_list"), ("item", "help_list_showcase"),
            ("item", "help_list_completed"), ("item", "help_list_favorite"),
            ("item", "help_list_random"),
            ("header", "help_section_menu"), ("item", "help_menu_continue"),
            ("item", "help_menu_collections"), ("item", "help_menu_hunter"),
            ("header", "help_section_system"), ("item", "help_system_stats"),
            ("item", "help_system_secrets"), ("item", "help_system_credits"),
            ("header", "help_section_playing"), ("item", "help_playing_exit"),
            ("item", "help_playing_exit_pad"), ("item", "help_playing_music"),
            ("header", "help_section_general"), ("item", "help_general_osd"),
            ("item", "help_general_osd_back"),
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
                if H >= 720:
                    hd = _art_path_in(ART_HD, top_syskey, top_label)
                    art = ART.get_scaled(hd, cover_w, cover_h)
                if art is None:
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
                if H >= 720:
                    hd = _art_path_in(ART_HD, top_syskey, top_label)
                    art = ART.get_scaled(hd, cover_w, cover_h)
                if art is None:
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
        Rueckkehr ins Frontend mit F10."""
        LOG("open_osd: Start")
        self.music.pause_for_core()
        self.draw("MiSTer OSD active - F10 or X button = back")
        self.inp.grab(False)
        time.sleep(0.2)
        self.inp.inject(KEY_F12)
        LOG("open_osd: F12 injiziert, warte auf back_fe (F10/X)")
        while True:
            act = self.inp.read_action()
            LOG("open_osd passthrough: %s" % act)
            if act == "back_fe":
                break
        LOG("open_osd: Rueckkehr")
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

    def _publish_stream(self):
        if not self.stream:
            return
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
            try:
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

                # Zustand VOR der Aktion merken - fuer die Entscheidung,
                # ob nach einem einzelnen hoch/runter-Schritt der leichte
                # Navigations-Zeichenpfad ausreicht (siehe unten, nach
                # der kompletten Aktionsverarbeitung).
                pre_page = self.page
                pre_item_i = self.item_i

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
                    if act == "left":
                        self.confirm_choice = 0    # Ja
                    elif act == "right":
                        self.confirm_choice = 1    # Nein
                    elif act == "ok":
                        if self.confirm_choice == 0:
                            break                   # Ja bestaetigt
                        self.confirm_quit = False    # Nein
                    elif act in ("exit", "back"):
                        self.confirm_quit = False    # ESC/B im Dialog = Nein
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
                move_step = (10 if move_streak > 40 else
                            4 if move_streak > 20 else
                            2 if move_streak > 8 else 1)

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
                    if self.page == 0:
                        self.cat_i = (self.cat_i - move_step) % len(self.cats)
                    elif items:
                        self.item_i = (self.item_i - move_step) % len(items)
                        self.marquee_reset()
                elif act == "down":
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
                                use_ra = self.draw_core_choice_screen(syskey, label)
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
                            if toggle_crt_menu() is not None:
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
                            set_language("de" if CURRENT_LANG == "en" else "en")
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
                            self.draw(t("remap_done"))
                            time.sleep(1.0)
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
                        and self._draw_navigate_items(pre_item_i)):
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
    Verhalten, das update_frontend.sh/install.sh beim Neustarten einer
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
    try:
        Frontend().run()
    except Exception:
        LOG("CRASH:\n" + traceback.format_exc())
        print("")
        print("ABSTURZ - Details siehe oben und in %s" % LOGFILE)
        raise
    finally:
        release_single_instance()
