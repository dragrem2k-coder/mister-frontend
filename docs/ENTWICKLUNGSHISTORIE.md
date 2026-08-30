# Entwicklungs- und Versionshistorie

Dieser Text stand bis Build 52 als Modul-Docstring im Kopf von
`frontend/frontend.py` (Zeilen 3-3363, rund 202.000 Zeichen bzw. 26 % der
Datei). Er wurde unveraendert hierher ausgelagert: der Docstring wurde bei
jedem Import als Zeichenkette in den Speicher geladen, obwohl ihn kein
Code je gelesen hat, und er machte die eigentliche Programmlogik in
Editoren und bei der Suche schwer auffindbar. Im Dateikopf stehen jetzt nur
noch Projektname, Steuerungsuebersicht und Startbefehl.

Inhaltlich ist nichts geaendert - der folgende Block ist eine woertliche
Kopie des ausgelagerten Teils.

---

```text
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
```
