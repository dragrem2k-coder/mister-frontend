#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MiSTer Custom Frontend - v1.29
=======================================
Reines Standard-Python, keine externen Abhaengigkeiten.

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

import os, sys, mmap, struct, fcntl, time, re, glob, subprocess, traceback, zlib, json, random, math

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
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True

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
# Alle Orte, an denen ROMs liegen koennen (SD + USB-Laufwerke)
GAMES_BASES = (["/media/fat/games"]
               + ["/media/usb%d/games" % i for i in range(6)]
               + ["/media/usb%d" % i for i in range(6)])
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
MISTER_CMD  = "/dev/MiSTer_cmd"
MUSIC_DIR   = "/media/fat/music"
MUSIC_ENABLED_FILE = "/media/fat/frontend/music_enabled"
LANGUAGE_FILE = "/media/fat/frontend/language"
KEYMAP_CUSTOM_FILE = "/media/fat/frontend/keymap_custom.json"
BOOTANIM_DIR = "/media/fat/frontend/bootanim"
BOOTANIM_PLAYED_MARKER = "/tmp/frontend_bootanim_played"
MPG123_BIN  = "/usr/bin/mpg123"
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
]

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
# 8x8 BITMAP-FONT (Public Domain, IBM VGA / Marcel Sondaar / Daniel Hepper)
# ----------------------------------------------------------------------------
FONT8X8 = bytes.fromhex('000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000183c3c1818001800363600000000000036367f367f3636000c3e031e301f0c00006333180c6663001c361c6e3b336e000606030000000000180c0606060c1800060c1818180c060000663cff3c660000000c0c3f0c0c000000000000000c0c060000003f0000000000000000000c0c006030180c060301003e63737b6f673e000c0e0c0c0c0c3f001e33301c06333f001e33301c30331e00383c36337f3078003f031f3030331e001c06031f33331e003f3330180c0c0c001e33331e33331e001e33333e30180e00000c0c00000c0c00000c0c00000c0c06180c0603060c180000003f00003f0000060c1830180c06001e3330180c000c003e637b7b7b031e000c1e33333f3333003f66663e66663f003c66030303663c001f36666666361f007f46161e16467f007f46161e16060f003c66030373667c003333333f333333001e0c0c0c0c0c1e007830303033331e006766361e366667000f06060646667f0063777f7f6b63630063676f7b736363001c36636363361c003f66663e06060f001e3333333b1e38003f66663e366667001e33070e38331e003f2d0c0c0c0c1e003333333333333f0033333333331e0c006363636b7f7763006363361c1c3663003333331e0c0c1e007f6331184c667f001e06060606061e0003060c18306040001e18181818181e00081c36630000000000000000000000ff0c0c18000000000000001e303e336e000706063e66663b0000001e3303331e003830303e33336e0000001e333f031e001c36060f06060f0000006e33333e301f0706366e666667000c000e0c0c0c1e00300030303033331e070666361e3667000e0c0c0c0c0c1e000000337f7f6b630000001f333333330000001e3333331e0000003b66663e060f00006e33333e307800003b6e66060f0000003e031e301f00080c3e0c0c2c18000000333333336e0000003333331e0c000000636b7f7f3600000063361c36630000003333333e301f00003f190c263f00380c0c070c0c38001818180018181800070c0c380c0c07006e3b0000000000000000000000000000')

# ----------------------------------------------------------------------------
# FRAMEBUFFER
# ----------------------------------------------------------------------------

class Framebuffer:
    def __init__(self):
        self._read_geometry()
        self.fd = os.open(FBDEV, os.O_RDWR)
        self._map()
        self._rowcache = {}
        self._glyphcache = {}

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

    def rect(self, x, y, w, h, rgb, scanlines=False):
        """scanlines=True: jede 2. Zeile dezent abgedunkelt (Retro-Look) -
        nur fuer reine Hintergrundflaechen, nicht fuer Markierungsbalken."""
        x = max(0, x); y = max(0, y)
        w = min(w, self.width - x); h = min(h, self.height - y)
        if w <= 0 or h <= 0:
            return
        key = (rgb, w)
        row = self._rowcache.get(key)
        if row is None:
            row = self.px(rgb) * w
            self._rowcache[key] = row
        row_dark = None
        if scanlines:
            key2 = (rgb, w, "dark")
            row_dark = self._rowcache.get(key2)
            if row_dark is None:
                row_dark = self.px(self._darken(rgb)) * w
                self._rowcache[key2] = row_dark
        for yy in range(y, y + h):
            off = yy * self.stride + x * 4
            use_row = row_dark if (scanlines and yy % 2) else row
            self.buf[off:off + w * 4] = use_row

    def _glyph_row(self, bits, scale, fg, bg):
        key = (bits, scale, fg, bg)
        row = self._glyphcache.get(key)
        if row is None:
            f = self.px(fg); b = self.px(bg)
            row = b"".join((f if bits >> i & 1 else b) * scale for i in range(8))
            self._glyphcache[key] = row
        return row

    def text(self, x, y, s, scale=2, fg=C_TEXT, bg=None):
        if bg is None:
            bg = C_BG
        cw = 8 * scale
        if y + 8 * scale > self.height or y < 0:
            return
        for ci, ch in enumerate(s):
            code = ord(ch)
            if code > 127:
                code = ord("?")
            gx = x + ci * cw
            if gx + cw > self.width:
                break
            for gy in range(8):
                bits = FONT8X8[code * 8 + gy]
                row = self._glyph_row(bits, scale, fg, bg)
                base = (y + gy * scale) * self.stride + gx * 4
                for rep in range(scale):
                    off = base + rep * self.stride
                    self.buf[off:off + cw * 4] = row

    def flip(self):
        # Direkte Slice-Zuweisung: mmap nimmt das bytearray ohne die
        # teure bytes()-Zwischenkopie (auf 1080p ~8 MB pro Frame).
        self.mm[:] = self.buf

    def flip_rows(self, y, h):
        """Nur einen Zeilenbereich auf den Schirm bringen (Laufschrift)."""
        y0 = max(0, y)
        y1 = min(self.height, y + h)
        if y1 <= y0:
            return
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

EVIOCGRAB = 0x40044590
EV_SYN, EV_KEY, EV_ABS = 0, 1, 3
KEY_ESC, KEY_ENTER = 1, 28
KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT = 103, 108, 105, 106
KEY_F9, KEY_F10, KEY_F11, KEY_F12 = 67, 68, 87, 88
# Gamepad-Buttons (Linux-Standardcodes)
BTN_A, BTN_B, BTN_X, BTN_Y = 304, 305, 307, 308
KEY_Y = 21                   # Y key on keyboard
BTN_TL, BTN_TR = 310, 311
BTN_SELECT, BTN_START, BTN_MODE = 314, 315, 316
BTN_DPAD_UP, BTN_DPAD_DOWN, BTN_DPAD_LEFT, BTN_DPAD_RIGHT = 544, 545, 546, 547
# Achsen
ABS_X, ABS_Y, ABS_HAT0X, ABS_HAT0Y = 0, 1, 16, 17
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
        for ax in (ABS_X, ABS_Y, ABS_HAT0X, ABS_HAT0Y):
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
        self.rescan()

    def rescan(self):
        self.last_scan = time.time()
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
            self.held = (key_id, act, time.time() + REPEAT_DELAY,
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
        Wiederholungen, damit ein Loslassen nie verloren geht."""
        deadline = None if timeout is None else time.time() + timeout
        while True:
            now = time.time()
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
            if self.held is not None and time.time() >= self.held[2]:
                kid, act, _t, iv = self.held
                iv = max(0.05, iv * 0.85)
                self.held = (kid, act, time.time() + iv, iv)
                return act
            if deadline is not None and time.time() >= deadline:
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
        deadline = None if timeout is None else time.time() + timeout
        while True:
            now = time.time()
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
            if deadline is not None and time.time() >= deadline:
                return None

    COMBO_HOLD = 0.8          # Sekunden Start+Select halten

    def wait_game_exit(self):
        """Waehrend ein Core laeuft: warten, bis MiSTer zurueck im
        Menue ist, F10 gedrueckt wird, ODER Start+Select lange genug
        gehalten werden. Rueckgabe: "menu", "f10" oder "combo"."""
        down = set()              # (geraetepfad, code) gedrueckter Tasten
        combo_since = None
        last_core_check = 0.0
        while True:
            now = time.time()
            if now - self.last_scan > self.RESCAN_EVERY:
                self.rescan()
                down = {k for k in down if k[0] in self.devices}
            if now - last_core_check > 0.7:
                last_core_check = now
                if current_core() == "MENU":
                    return "menu"
            if combo_since is not None and now - combo_since >= self.COMBO_HOLD:
                return "combo"
            fds = {d.fd: d for d in self.devices.values()}
            if not fds:
                time.sleep(0.5)
                continue
            try:
                r, _, _ = select.select(list(fds), [], [], 0.2)
            except OSError:
                self.rescan()
                continue
            for fd in r:
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
                        combo_since = time.time()
                    elif not active:
                        combo_since = None

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
        Funktioniert nur bei geloestem Grab."""
        target = None
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
# ARTWORK (.art) UND METADATEN
# .art-Format: b"ART1" + uint16 Breite + uint16 Hoehe + zlib(BGRA-Rohpixel)
# Die Dateien werden am PC mit art_convert.py erzeugt - der MiSTer
# muss nur noch entpacken (zlib ist Standardbibliothek) und blitten.
# ----------------------------------------------------------------------------

class ArtCache:
    LIMIT = 40                       # max. Bilder im Speicher halten

    def __init__(self):
        self.cache = {}              # pfad -> (w, h, pixelbytes) oder None
        self.order = []

    def get(self, path):
        if path in self.cache:
            return self.cache[path]
        art = None
        try:
            with open(path, "rb") as f:
                if f.read(4) == b"ART1":
                    w, h = struct.unpack("<HH", f.read(4))
                    pix = zlib.decompress(f.read())
                    if len(pix) == w * h * 4:
                        art = (w, h, pix)
        except OSError:
            pass
        self.cache[path] = art
        self.order.append(path)
        if len(self.order) > self.LIMIT:
            old = self.order.pop(0)
            self.cache.pop(old, None)
        return art

    SCALED_LIMIT = 10

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
        """Bild in die verfuegbare Flaeche einpassen. Kleine Cover werden
        ganzzahlig hochskaliert (Pixel-Look). Cover, die groesser als die
        Box sind, werden seit v1.8.1 per Nearest-Neighbor VERKLEINERT statt
        unskaliert zu bleiben - sonst ragen sie ueber den reservierten
        Platz hinaus und ueberlappen den Info-Text darunter."""
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
        xmap = [min(w - 1, int(x / scale)) * 4 for x in range(tw)]
        out = bytearray(tw * th * 4)
        row_out = tw * 4
        for ty in range(th):
            sy = min(h - 1, int(ty / scale))
            srow = pix[sy * w * 4:(sy + 1) * w * 4]
            o = ty * row_out
            for tx in range(tw):
                sx = xmap[tx]
                out[o:o + 4] = srow[sx:sx + 4]
                o += 4
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

def art_path(syskey, rom_basename):
    return os.path.join(ART_BASE, syskey, rom_basename + ".art")

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

# Tags, die ein ROM als Beta/Prototyp/Demo/Hack/defekten Dump o.ae.
# kennzeichnen - werden beim Scannen ausgefiltert.
JUNK_TAGS = ("(beta", "(proto", "(demo", "(sample", "(unl)", "[b]",
            "(pirate", "(program", "(test", "(kiosk", "(hack")

def _is_junk(name):
    low = name.lower()
    return any(tag in low for tag in JUNK_TAGS)

# Bekannte Boot-/Test-/Demo-Dateien, die manche MiSTer-Verteilungen
# direkt in die ROM-Ordner legen (fuer den Hardware-Selbsttest). Haben
# zufaellig die richtige Endung (z.B. .chd/.gb/.gba) und wuerden sonst
# faelschlich als "Spiel" in der Liste auftauchen.
IGNORE_ROM_BASENAMES = {"boot", "boot1", "boot2", "mister-boot", "mister-demo"}

def nice_name(dirname):
    raw = dirname.lstrip("_")
    return NICE_NAMES.get(raw, raw.replace("_", " "))

def scan_cores():
    """Alle /media/fat/_*-Ordner nach .rbf/.mra durchsuchen."""
    cats = []
    for d in sorted(glob.glob(os.path.join(BASE, "_*"))):
        if not os.path.isdir(d) or os.path.basename(d) in SKIP_DIRS:
            continue
        items = []
        # .mgl mit aufnehmen: so tauchen MGL-Shortcut-Ordner (z.B. das
        # "Recently Played"-Skript) auf und sind direkt startbar - der
        # Start-Pfad (load_core) verarbeitet .mgl genauso wie .rbf/.mra.
        for f in sorted(glob.glob(os.path.join(d, "*.mra")) +
                        glob.glob(os.path.join(d, "*.rbf")) +
                        glob.glob(os.path.join(d, "*.mgl"))):
            name = os.path.splitext(os.path.basename(f))[0]
            name = re.sub(r"_\d{8}[a-zA-Z]?$", "", name)
            items.append((name, "core", f))
        if items:
            # Arcade-Ordner bekommen ein Info-Panel (MRA-Metadaten)
            base = os.path.basename(d).lstrip("_").lower()
            syskey = "ARCADE" if "arcade" in base else None
            cats.append((nice_name(os.path.basename(d)), items, syskey))
    return cats

def _games_signature():
    """Fingerabdruck der ROM-Ordner INKLUSIVE aller Unterordner (nur
    Verzeichnis-mtimes, keine einzelnen Dateien - deutlich billiger als
    der eigentliche Scan, aber empfindlich genug fuer Aenderungen in
    tief verschachtelten Sammlungen wie 'Favoriten'- oder 'Top 100'-
    Unterordnern). Frueher wurde nur die oberste Ebene geprueft -
    Aenderungen/Loeschungen in Unterordnern blieben dadurch unbemerkt,
    der Cache zeigte dann veraltete Eintraege bzw. Boxarts fuer nicht
    mehr vorhandene Spiele."""
    sig = []
    for base in GAMES_BASES:
        if not os.path.isdir(base):
            continue
        for _d, _sk, folders, _r, _e in GAME_SYSTEMS:
            for folder in folders:
                root = os.path.join(base, folder)
                try:
                    sig.append((root, int(os.path.getmtime(root))))
                except OSError:
                    continue
                for dirpath, dirnames, _filenames in os.walk(root):
                    dirnames[:] = [d for d in dirnames if not d.startswith(".")]
                    for d in dirnames:
                        sub = os.path.join(dirpath, d)
                        try:
                            sig.append((sub, int(os.path.getmtime(sub))))
                        except OSError:
                            pass
    return sig

def _cats_to_json(cats):
    return [[n, [[i0, i1, list(i2[:4]) + [list(i2[4])]] for i0, i1, i2 in it], sk]
            for n, it, sk in cats]

def _cats_from_json(data):
    cats = []
    for n, it, sk in data:
        items = [(i0, i1, (i2[0], i2[1], i2[2], i2[3], tuple(i2[4])))
                 for i0, i1, i2 in it]
        cats.append((n, items, sk))
    return cats

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

def scan_games(force=False, progress_cb=None):
    """ROM-Listen laden - aus dem Cache, wenn er noch passt.
    progress_cb(i, total, name): wird NUR beim tatsaechlichen Scannen
    von der Platte aufgerufen (nicht beim schnellen Cache-Treffer) -
    normale Boots (Cache passt) bleiben also unveraendert schnell,
    nur der seltene "erster Start"/"ROMs geaendert"-Fall zeigt Fortschritt."""
    sig = _games_signature()
    if not force:
        try:
            with open(GAMES_CACHE) as f:
                data = json.load(f)
            if data.get("sig") == [list(s) for s in sig]:
                LOG("Spieleliste aus Cache (%d Systeme)"
                    % len(data["cats"]))
                return _cats_from_json(data["cats"])
        except (OSError, ValueError, KeyError, IndexError, TypeError):
            pass
    cats = _scan_games_disk(progress_cb)
    try:
        with open(GAMES_CACHE, "w") as f:
            json.dump({"sig": [list(s) for s in sig],
                       "cats": _cats_to_json(cats)}, f)
    except OSError:
        pass
    return cats

def _scan_games_disk(progress_cb=None):
    """Fuer jedes bekannte System die ROMs einsammeln. Rueckgabe: Liste
    (Anzeigename, Items, Systemkey).

    Geht beliebig tief (keine Ordnerebenen-Begrenzung mehr) - die
    eigene Ordnerstruktur/Sortierung bleibt dabei komplett unangetastet.
    Bekannte Boot-/Testdateien (IGNORE_ROM_BASENAMES) sowie Beta/Proto/
    Demo/Hack/Bad-Dump-Tags (JUNK_TAGS) werden ausgefiltert. Mehrfach-
    Regionen desselben Spiels ("Spiel (USA)", "Spiel (Europe)", ...)
    werden zu EINEM Eintrag zusammengefasst (beste Region gewinnt,
    REGION_PRIORITY) - bei sehr grossen, mehrfach-region-vollstaendigen
    Sammlungen kann das die Listengroesse spuerbar reduzieren."""
    cats = []
    total_sys = len(GAME_SYSTEMS)
    for sys_idx, (disp, syskey, folders, rbf, extmap) in enumerate(GAME_SYSTEMS):
        if progress_cb:
            try:
                progress_cb(sys_idx, total_sys, disp)
            except Exception:
                pass
        raw = []
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
                for dirpath, dirnames, filenames in os.walk(root):
                    dirnames[:] = [d for d in dirnames
                                   if not d.startswith(".")]
                    for fn in filenames:
                        name = os.path.splitext(fn)[0]
                        if name.lower() in IGNORE_ROM_BASENAMES:
                            continue
                        if _is_junk(name):
                            continue
                        ext = os.path.splitext(fn)[1].lower()
                        if ext in extmap:
                            raw.append((name, "game",
                                        (os.path.join(dirpath, fn), ext,
                                         syskey, rbf, extmap[ext])))
        if raw:
            # Pro kanonischem Namen (ohne Region-/Versions-Tags) nur
            # die Kopie mit der besten Region behalten.
            best = {}
            for entry in raw:
                key = _canonical_key(entry[0])
                rank = _region_rank(entry[0])
                cur = best.get(key)
                if cur is None or rank < cur[0]:
                    best[key] = (rank, entry)
            items = [entry for _rank, entry in best.values()]
            items.sort(key=lambda t: t[0].lower())
            cats.append((disp, items, syskey))
    return cats

def write_mgl(rbf, rom_path, delay, ftype, index):
    """MGL-Startdatei erzeugen (Pfad-Konvention wie in mrext)."""
    xml = ('<mistergamedescription>\n'
           '\t<rbf>%s</rbf>\n'
           '\t<file delay="%d" type="%s" index="%d" '
           'path="../../../../..%s"/>\n'
           '</mistergamedescription>\n'
           % (rbf, delay, ftype, index, rom_path))
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
        self.playlist = []
        self.pos = 0
        self.proc = None
        self._track_started_at = None
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
        return bool(self.playlist) and os.path.exists(MPG123_BIN)

    def _proc_alive(self):
        return self.proc is not None and self.proc.poll() is None

    def _start_current(self):
        if not self.playlist:
            return
        path = self.playlist[self.pos]
        try:
            self.proc = subprocess.Popen(
                [MPG123_BIN, "-q", path],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL)
            self._track_started_at = time.time()
            LOG("Music: playing %s" % os.path.basename(path))
        except OSError as e:
            LOG("Music: failed to start mpg123: %s" % e)
            self.proc = None

    def _stop_current(self):
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
        if not self.enabled or self.paused_for_core or not self.playlist:
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
        if not self.playlist:
            return
        alive = self._proc_alive()
        had_proc = self.proc is not None  # VOR _stop_current() merken -
                                          # das setzt self.proc selbst auf None
        if alive and self._track_started_at is not None and \
           time.time() - self._track_started_at > self.MAX_TRACK_SECONDS:
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
    "no_artwork_1":    {"en": "no",      "de": "kein"},
    "no_artwork_2":    {"en": "artwork", "de": "Artwork"},
    "sys_osd":         {"en": "Open MiSTer OSD (Settings/Buttons)",
                        "de": "MiSTer-OSD oeffnen (Settings/Buttons)"},
    "sys_video_crt":   {"en": "Menu video: CRT -> switch to HDMI",
                        "de": "Menue-Video: CRT -> auf HDMI wechseln"},
    "sys_video_hdmi":  {"en": "Menu video: HDMI -> switch to CRT",
                        "de": "Menue-Video: HDMI -> auf CRT wechseln"},
    "sys_video_suffix":{"en": " (reboot)", "de": " (Neustart)"},
    "sys_music_on":    {"en": "Music: On -> turn off", "de": "Musik: an -> ausschalten"},
    "sys_music_off":   {"en": "Music: Off -> turn on", "de": "Musik: aus -> einschalten"},
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
    "scanning":  {"en": "Scanning: %s", "de": "Durchsuche: %s"},
    "recent_cat": {"en": "Recently Played", "de": "Zuletzt gespielt"},
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
    "remap_done":      {"en": "Button mapping saved!",
                        "de": "Tastenbelegung gespeichert!"},
    "remap_cancelled": {"en": "Cancelled - keeping previous mapping",
                        "de": "Abgebrochen - alte Belegung bleibt aktiv"},
    "remap_esc_hint":  {"en": "(ESC to cancel)", "de": "(ESC zum Abbrechen)"},
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


def system_items(music_enabled=None):
    crt = crt_menu_active()
    video = t("sys_video_crt") if crt else t("sys_video_hdmi")
    music_label = t("sys_music_on") if music_enabled else t("sys_music_off")
    curated_label = t("sys_curated_on") if curated_only_active() \
        else t("sys_curated_off")
    return [
        (t("sys_osd"),                             "osd",       None),
        (video + t("sys_video_suffix"),             "crtmenu",   None),
        (music_label,                                "music",     None),
        (t("sys_language"),                          "language",  None),
        (t("sys_configure_buttons"),                 "remap",     None),
        (t("sys_reset_buttons"),                     "remap_reset", None),
        (curated_label,                              "curated",   None),
        (t("sys_rescan"),                            "rescan",    None),
        (t("sys_redraw"),                            "redraw",    None),
        (t("sys_reboot"),                            "reboot",    None),
        (t("sys_quit"),                              "quit",      None),
    ]

def filter_curated(name, items, syskey):
    """Wenn der 'Nur katalogisierte Spiele'-Schalter aktiv ist (System-
    Menue), auf Eintraege einschraenken, die einen Treffer in der
    libretro-Datenbank haben (von mister_gameinfo.py geladen,
    meta/<System>.json bzw. fuer Arcade die MRA-Datei selbst) - das ist
    die "Source of Authority", die Hyperspin frueher mit seinen
    XML-Datenbanken pro System bereitgestellt hat: nur tatsaechlich
    katalogisierte, offiziell erschienene Spiele, keine Hacks/Homebrew/
    unbekannten Dumps.

    Sicherheitsnetz: Hat ein System UEBERHAUPT keine Metadaten (z.B.
    weil mister_gameinfo.py dafuer noch nie gelaufen ist), wird NICHT
    gefiltert - sonst wuerde die Liste faelschlich komplett leer
    werden, nur weil noch keine Datenbank geladen wurde."""
    if not syskey or not items:
        return (name, items, syskey)
    kept = []
    any_meta = False
    for it in items:
        label, kind, arg = it
        if syskey == "ARCADE":
            meta = mra_meta(arg) if kind == "core" else {}
        else:
            meta = get_meta(syskey, label)
        if meta:
            any_meta = True
            kept.append(it)
    if not any_meta:
        return (name, items, syskey)
    return (name, kept, syskey)

CURATED_FLAG = "/media/fat/frontend/curated_only"

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
        self.music = MusicPlayer()
        self.build_categories()
        self.page = 0              # 0 = Kategorien-Menue, 1 = Kategorie-Ansicht
        self.cat_i = 0
        self.cat_scroll = 0
        self.item_i = self.scroll = 0

        # Optionaler Stream-Overlay-Server (nur wenn Freigabe-Datei da ist)
        self.stream = None
        self._stream_sig = None
        if StreamServer and os.path.exists(STREAM_ENABLED_FILE):
            try:
                self.stream = StreamServer(ART_BASE, port=STREAM_PORT,
                                           config_path=STREAM_CONFIG_FILE,
                                           log=LOG)
                if not self.stream.start():
                    self.stream = None
            except Exception as e:
                LOG("Stream-Server-Start fehlgeschlagen: %s" % e)
                self.stream = None
        self.mq_off = 0            # Laufschrift-Versatz (Zeichen)
        self.mq_pause = 0          # Pausen-Ticks an den Enden
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
        self._pulse_t0 = time.time()
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
        # Reihenfolge: Spiele-Systeme, dann Core-Ordner, Scripts, System
        self.cats = scan_games(force=force_rescan,
                               progress_cb=self._draw_scan_progress)
        recent_items = load_recent()
        if recent_items:
            # Ganz vorne, damit sie ohne Scrollen erreichbar ist.
            # syskey=None (wie Scripts/System), da die Liste mehrere
            # Systeme mischt - jeder Eintrag traegt seinen eigenen
            # Systemkey in arg[2], der beim Zeichnen bevorzugt wird
            # (siehe _item_syskey()).
            self.cats.insert(0, (t("recent_cat"), recent_items, None))
        self.cats.extend(scan_cores())
        scripts = scan_scripts()
        if scripts:
            self.cats.append(("Scripts", scripts, None))
        self.cats.append(("System", system_items(self.music.enabled), None))
        if curated_only_active():
            # filter_curated() laesst Kategorien ohne syskey (Scripts,
            # System, Core-Ordner) unveraendert - nur echte Spiele-
            # Systeme werden eingeschraenkt.
            self.cats = [filter_curated(n, it, sk) for n, it, sk in self.cats]

    def _go_back_or_confirm_quit(self):
        """ESC/B (und der 3x-Select-Kurzbefehl): auf Seite 1 einfach
        eine Ebene zurueck; im Hauptmenue (Seite 0) stattdessen die
        Beenden-Bestaetigung einblenden statt sofort zu schliessen."""
        if self.page == 1:
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

    def _enter_category(self):
        """Von Seite 0 (Kategorien-Menue) in Seite 1 (Liste der
        aktuellen Kategorie) wechseln."""
        _name, items, _sk = self.cats[self.cat_i]
        if not items:
            return
        self.page = 1
        self.item_i = 0
        self.scroll = 0
        self.marquee_reset()

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
        list_y = oy + 40 * s
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
        maxc = max(4, (list_right - ox - 40 * s) // (8 * s))
        for row, i in enumerate(range(self.cat_scroll, end)):
            name, items, _sk = self.cats[i]
            y = y0 + row * rowh
            sel = (i == self.cat_i)
            accent = accent_for(_sk)
            bg = self._pulsed(accent) if sel else C_BG
            if sel:
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
            cnt = str(len(items))
            ccw = len(cnt) * 8 * s
            fb.text(list_right - ccw, y + 4 * s, cnt,
                    s, C_TEXT if sel else C_DIM, bg)

        # Artbox rechts: Logo/Cover des gerade markierten Systems
        self._draw_cat_artbox(L)

        foot = message or (
            t("footer_cats_wide") if W >= 700 else
            t("footer_cats_mid") if W >= 560 else
            t("footer_cats_narrow"))
        fb.text(ox, H - oy - 13 * s, foot, s, C_DIM, C_BG)
        if flip:
            fb.flip()

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
            fb.blend_rect(ax + 3 * s, ay + ah - 4 * s, aw, 10 * s,
                         (0, 0, 0), 0.35)
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
        fb = self.fb
        W, H = fb.width, fb.height
        name, items, syskey = self.cats[self.cat_i]
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
        if self._cur_bg is not None:
            fb.buf[:] = self._cur_bg
        else:
            fb.clear(C_BG)

        fb.text(ox, oy, name.upper(), 2 * s, C_TITLE)
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
        for idx in range(self.scroll, end):
            self.draw_list_row(idx)

        if has_art:
            # Die Spalte beginnt jetzt auf Hoehe der Kopfzeile (oy) statt
            # erst auf Hoehe der Liste (list_y) - der Header nutzt nur
            # den linken Teil der Zeile, rechts daneben blieb bisher ein
            # ungenutzter Streifen bis zur Liste. Das Cover bekommt so
            # spuerbar mehr Platz nach oben.
            art_x0 = list_right + 14 * s
            art_y0 = oy
            art_w = (W - ox) - art_x0
            art_h = footer_y - 8 * s - art_y0
            if art_w > 20 and art_h > 20:
                item_syskey = self._item_syskey(items[self.item_i], syskey)
                self.draw_art_panel(art_x0, art_w, art_y0, art_h,
                                    item_syskey, items[self.item_i], s)

        foot = message or (
            t("footer_items_wide") if W >= 700 else
            t("footer_items_mid") if W >= 560 else
            t("footer_items_narrow"))
        fb.text(ox, footer_y, foot, s, C_DIM)
        if flip:
            fb.flip()

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

    def draw_list_row(self, idx):
        """Eine Listenzeile zeichnen. Die markierte Zeile zeigt bei
        Ueberlaenge einen Laufschrift-Ausschnitt des vollen Namens.
        Die Boxart-Spalte liegt seit v1.8 NEBEN der Liste statt darueber,
        darum muss hier keine Zeile mehr wegen Ueberlappung ausgeblendet
        werden."""
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
        cur_bg = getattr(self, "_cur_bg", None)
        if cur_bg is not None:
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
                fb.rect(x0, y_top, rw, rowh - 2 * s, bg)
        else:
            fb.rect(x0, y_top, rw, rowh - 2 * s, bg if sel else C_BG)

        if sel:
            for ring, a in enumerate((0.20, 0.11, 0.05)):
                p = (ring + 1) * 2 * s
                fb.glow_border_fast(x0 - p, y_top - p, rw + 2 * p,
                                    rowh - 2 * s + 2 * p, C_BG, accent, a,
                                    thickness=2 * s)

        full = v["items"][idx][0]
        maxc = (list_right - list_x - 8 * s) // (8 * s)
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
        fb.text(list_x, y, label, s, C_TEXT if sel else C_DIM, bg)
        return y

    def marquee_needed(self):
        v = getattr(self, "view", None)
        if not v or self.page != 1 or not v["items"]:
            return False
        s = v["s"]
        maxc = (v["list_right"] - v["list_x"] - 8 * s) // (8 * s)
        return len(v["items"][self.item_i][0]) > maxc

    def marquee_tick(self):
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
        """Versatz um einen Schritt weiterschieben (mit Pause an den
        Enden) - gedrosselt ueber _track_tick_next, damit nicht bei
        jedem next_action()-Aufruf ein komplettes Neuzeichnen noetig
        wird, sondern nur alle ~0.35s."""
        now = time.time()
        if now < self._track_tick_next:
            return False
        self._track_tick_next = now + 0.35
        name = self._track_mq_name
        max_off = max(0, len(name) - maxc)
        if self.track_mq_pause > 0:
            self.track_mq_pause -= 1
            if self.track_mq_pause == 0 and self.track_mq_off >= max_off:
                self.track_mq_off = 0
                self.track_mq_pause = 4
        elif self.track_mq_off < max_off:
            self.track_mq_off += 1
            if self.track_mq_off >= max_off:
                self.track_mq_pause = 6
        return True

    def _pulse_factor(self):
        """Aktueller Helligkeits-Multiplikator (0.90..1.0) fuer die
        pulsierende Markierung - sinusfoermig, langsamer Zyklus
        (~3.2 Sekunden), bewusst dezent."""
        elapsed = time.time() - self._pulse_t0
        return 0.90 + 0.10 * (0.5 + 0.5 * math.sin(elapsed * 2 * math.pi / 3.2))

    def _pulsed(self, rgb):
        f = self._pulse_factor()
        return tuple(min(255, int(c * f)) for c in rgb)

    def _pulse_tick(self):
        """True, wenn seit dem letzten Aufruf genug Zeit vergangen ist,
        um eine neue Pulsier-Stufe zu zeigen - bewusst selten (~alle
        0.9s), damit KEINE zusaetzlichen haeufigen Neuzeichnungen
        entstehen. Nutzt das ohnehin vorhandene ~1s-Idle-Aufwachen in
        next_action() mit, statt eigene schnellere Abfragen zu
        erzwingen."""
        now = time.time()
        if now < self._pulse_tick_next:
            return False
        self._pulse_tick_next = now + 0.9
        return True

    def _draw_equalizer(self, x, y, s):
        """Kleine animierte Balken neben der Now-Playing-Anzeige - rein
        dekorativ (mpg123 liefert uns keine echte Lautstaerke), nutzt
        eine Zeit-basierte Sinuskurve pro Balken statt Zufallszahlen
        (deterministisch, kein eigener Zustand noetig). Bewegt sich nur
        dann sichtbar, wenn ohnehin gerade neu gezeichnet wird (ueber
        den Pulsier-Tick) - keine zusaetzlichen Redraws dafuer noetig."""
        fb = self.fb
        now = time.time()
        bar_w = 3 * s
        gap = 2 * s
        h_max = 10 * s
        col = (224, 182, 74)
        for i in range(4):
            phase = now * 2.2 + i * 1.7
            frac = 0.35 + 0.65 * (0.5 + 0.5 * math.sin(phase))
            bh = max(2 * s, int(h_max * frac))
            bx = x + i * (bar_w + gap)
            fb.rect(bx, y + h_max - bh, bar_w, bh, col)

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
            timeout = 0.18 if (need_mq or track_needs) else 1.0
            act = self.inp.read_action(timeout=timeout)
            if act is not None:
                if need_mq:
                    self.marquee_reset()
                return act
            if need_mq:
                self.marquee_tick()
            if track_needs:
                if self._track_marquee_tick(24):
                    self.draw()
            elif self._pulse_tick():
                # Nur neu zeichnen, wenn nicht ohnehin schon durch die
                # Track-Laufschrift ein Redraw passiert (sonst doppelt).
                self.draw()
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
        if w < 20 or h < 20:
            return

        pad = 6 * s
        fb.rect(x0 - pad, y0 - pad, w + 2 * pad, h + 2 * pad, C_PANEL)
        avail_w = w - 2 * pad
        maxc = max(4, avail_w // (8 * s))

        if syskey == "ARCADE":
            meta = mra_meta(item[2])
        else:
            meta = get_meta(syskey, name)

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
        info_lines = []
        for ln in info_src:
            info_lines.extend(self._wrap(ln, maxc, max_lines=1))

        # Songtitel als Laufschrift (voller Titel, kein Label-Text
        # mehr davor) - passt sich exakt der hier bekannten Spaltenbreite
        # an, laeuft bei Bedarf durch statt abgeschnitten zu werden.
        track_display = self.track_marquee_text(maxc)
        track_lines = [track_display] if track_display else []

        line_h = 12 * s
        text_h = len(title_lines) * line_h
        if info_lines:
            text_h += 4 * s + len(info_lines) * line_h
        if track_lines:
            text_h += 4 * s + len(track_lines) * line_h

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
            hd = os.path.join(ART_HD, syskey, name + ".art")
            art = ART.get_scaled(hd, avail_w, cover_h)
        if art is None:
            art = ART.get_scaled(art_path(syskey, name), avail_w, cover_h)
        if art:
            aw, ah, pix = art
            ax = x0 + max(0, (avail_w - aw) // 2)
            ay = cy + max(0, (cover_h - ah) // 2)
            # Schlagschatten: dunkler, leicht versetzter Bereich UNTER
            # dem Cover, VOR dem eigentlichen Bild gezeichnet.
            fb.blend_rect(ax + 3 * s, ay + ah - 4 * s, aw, 10 * s,
                         (0, 0, 0), 0.35)
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

        if track_lines:
            iy += 4 * s
            for ln in track_lines:
                if iy + 9 * s > y_max:
                    break
                fb.text(x0, iy, ln, s, C_DIM, C_PANEL)
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

    def run_core(self, path):
        self.music.pause_for_core()
        self.inp.grab(False)
        launch_core(path)
        t0 = time.time()
        started = False
        # Auf den tatsaechlichen Core-Start warten (nicht mehr Menue).
        # Grosse CHDs auf langsamer SD brauchen laenger - deshalb 30s.
        while time.time() - t0 < 30:
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
        while current_core() != "MENU":
            res = self.inp.wait_game_exit()
            if res in ("combo", "f10"):
                LOG("Start+Select bzw. F10 erkannt - zurueck ins Menue"
                    if res == "combo" else "F10 erkannt - zurueck ins Menue")
                launch_core("/media/fat/menu.rbf")
                t1 = time.time()
                while current_core() != "MENU" and time.time() - t1 < 10:
                    time.sleep(0.3)
        time.sleep(1.0)
        self.music.resume_after_core()
        self.back_to_frontend()

    def run_script(self, path):
        """Script auf der Konsole (tty1) laufen lassen, danach zurueck."""
        self.music.pause_for_core()
        self.inp.grab(False)
        self.set_cursor_blink(True)
        try:
            tty = open("/dev/tty1", "r+b", buffering=0)
        except OSError:
            tty = None
        # Bildschirm dem Script ueberlassen
        try:
            if tty:
                tty.write(b"\x1b[2J\x1b[H")     # Konsole loeschen
                subprocess.call(["/bin/bash", path],
                                stdin=tty, stdout=tty, stderr=tty,
                                env=dict(os.environ, TERM="linux",
                                         HOME="/root"))
                tty.write(b"\n-- Script finished, press any key --\n")
            else:
                subprocess.call(["/bin/bash", path])
        finally:
            if tty:
                tty.close()
        self.inp.read_action()                    # auf Eingabe warten
        self.music.resume_after_core()
        self.back_to_frontend()

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
        bleiben, weil dort kein reines Tasten-Event eintrifft."""
        DIRECTIONAL = {"up", "down", "left", "right"}
        actions = [
            ("up", "remap_action_up"), ("down", "remap_action_down"),
            ("left", "remap_action_left"), ("right", "remap_action_right"),
            ("ok", "remap_action_ok"), ("back", "remap_action_back"),
            ("osd", "remap_action_osd"), ("random", "remap_action_random"),
        ]
        self.inp.grab(False)
        new_map = {}
        cancelled = False
        for act_name, label_key in actions:
            msg = "%s   %s" % (t("remap_prompt", t(label_key)),
                                t("remap_esc_hint"))
            self.draw(msg)
            is_dir = act_name in DIRECTIONAL
            code = self.inp.read_raw_key(allow_axis_skip=is_dir)
            if code is None or code == KEY_ESC:
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
        name, items, syskey = self.cats[self.cat_i]
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
        sel = items[self.item_i][0] if 0 <= self.item_i < total else ""
        lo = max(0, self.item_i - 2)
        hi = min(total, lo + 5)
        window = [display_name(items[i][0]) for i in range(lo, hi)]
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
        }

    def _publish_stream(self):
        if not self.stream:
            return
        try:
            st = self.stream_state()
        except Exception:
            return
        sig = (st["category"], st["name"], st["nowplaying"],
               st["index"], st["total"])
        if sig != self._stream_sig:
            self._stream_sig = sig
            self.stream.publish(st)

    def play_boot_animation(self):
        """Spielt eine Bildsequenz aus BOOTANIM_DIR ab (frame_0001.art,
        frame_0002.art, ...), einmal pro MiSTer-Boot, bevor das normale
        Menue erscheint. Jedes Bild wird formatfuellend (letterboxed,
        keine Verzerrung) zentriert gezeigt. Fehlt der Ordner, ist er
        leer, oder wurde die Animation in diesem Boot schon gezeigt,
        passiert einfach nichts - kein Fehler, direkt weiter ins Menue."""
        if os.path.exists(BOOTANIM_PLAYED_MARKER):
            return
        try:
            frames = sorted(f for f in os.listdir(BOOTANIM_DIR)
                            if f.lower().endswith(".art"))
        except OSError:
            frames = []
        if not frames:
            return

        # Optionale Zeitsteuerung: bootanim.json neben den Frames kann
        # {"fps": 12} enthalten - Standard 10 fps, falls nichts angegeben.
        fps = 10
        try:
            meta = json.load(open(os.path.join(BOOTANIM_DIR, "bootanim.json")))
            fps = max(1, min(30, int(meta.get("fps", fps))))
        except (OSError, ValueError, TypeError):
            pass
        frame_time = 1.0 / fps

        fb = self.fb
        W, H = fb.width, fb.height
        LOG("play_boot_animation: %d Frames bei %d fps" % (len(frames), fps))
        try:
            for fn in frames:
                t0 = time.time()
                path = os.path.join(BOOTANIM_DIR, fn)
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
                        frame_time - (time.time() - t0))) is not None:
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
        self.enter_console_mode()
        self.set_cursor_blink(False)
        self.inp.grab(True)
        self.play_boot_animation()
        self.draw()
        try:
            move_streak = 0     # zaehlt gehaltene hoch/runter-Wiederholungen
            move_last = None    # fuer den Turbo-Sprung (einzelne Position)
            page_streak = 0     # zaehlt gehaltene links/rechts-Wiederholungen
            page_last = None    # fuer den Turbo-Sprung (seitenweise)
            while True:
                act = self.next_action()
                self._publish_stream()
                LOG("aktion: %s (Seite %d, confirm=%s)"
                    % (act, self.page, self.confirm_quit))

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

                name, items, _syskey = self.cats[self.cat_i]

                # Turbo-Sprung hoch/runter: je laenger gehalten, desto
                # groesser die Schrittweite (1 -> 2 -> 4 -> 10). Das
                # beschleunigende Wiederholungs-Intervall aus dem
                # InputManager laesst die Tick-Rate schon steigen; hier
                # kommt zusaetzlich eine steigende Sprungweite dazu.
                if act in ("up", "down"):
                    move_streak = move_streak + 1 if act == move_last else 1
                    move_last = act
                else:
                    move_streak = 0
                    move_last = None
                move_step = (10 if move_streak > 40 else
                            4 if move_streak > 20 else
                            2 if move_streak > 8 else 1)

                # Turbo-Sprung links/rechts: Grundschritt ist eine volle
                # Bildschirmseite, waechst beim Halten auf mehrere Seiten.
                if act in ("left", "right"):
                    page_streak = page_streak + 1 if act == page_last else 1
                    page_last = act
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
                    # "Weiss nicht was ich spielen soll" - springt zu
                    # einem zufaelligen Eintrag, nie zweimal hinter-
                    # einander demselben (falls mehr als einer da ist).
                    move_streak = page_streak = 0
                    if self.page == 0:
                        if len(self.cats) > 1:
                            choices = [i for i in range(len(self.cats))
                                      if i != self.cat_i]
                            self.cat_i = random.choice(choices)
                            self.cat_scroll = 0
                    elif items and len(items) > 1:
                        choices = [i for i in range(len(items))
                                  if i != self.item_i]
                        self.item_i = random.choice(choices)
                        self.marquee_reset()
                elif act == "ok":
                    if self.page == 0:
                        self._enter_category()
                    else:
                        label, kind, arg = items[self.item_i]
                        if kind == "core":
                            self.run_core(arg)
                            continue
                        elif kind == "game":
                            rom, ext, syskey, rbf, (dl, ft, ix) = arg
                            LOG("Spielstart: %s (%s)" % (label, syskey))
                            record_recent(label, arg)
                            mgl = write_mgl(rbf, rom, dl, ft, ix)
                            self.run_core(mgl)
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

if __name__ == "__main__":
    LOG("==== Frontend-Start ====")
    if not acquire_single_instance():
        sys.exit(0)
    try:
        Frontend().run()
    except Exception:
        LOG("CRASH:\n" + traceback.format_exc())
        raise
    finally:
        release_single_instance()
