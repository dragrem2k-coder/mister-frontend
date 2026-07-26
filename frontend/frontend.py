#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MiSTer Custom Frontend - v1.63
=======================================
Reines Standard-Python, keine externen Abhaengigkeiten.

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

import os, sys, mmap, struct, fcntl, time, re, glob, subprocess, traceback, zlib, json, random, math, signal, socket

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
FAVORITES_FILE = "/media/fat/frontend/favorites.json"
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
                # Untergrenze bewusst bei 0.08s (12.5/s) statt zuvor 0.05s
                # (20/s) - auf HDMI dauert ein volles Neuzeichnen auf
                # schwacher ARM-Hardware laenger als 0.05s, wodurch sich
                # Eingaben stauen konnten (spuerbarer "Lag" beim Halten
                # einer Richtungstaste). CRT ist so schnell, dass es den
                # Unterschied nicht merkt - 12.5 Spruenge/Sekunde sind
                # immer noch sehr flott fuer eine kleine Liste.
                iv = max(0.08, iv * 0.85)
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
    sig.sort()
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

    t0 = time.time()
    last_total = None
    stable_streak = 0
    while True:
        elapsed = time.time() - t0
        found, total = snapshot()
        # Ein VORHANDENER, aber noch LEERER Ordner zaehlt NICHT als
        # stabil - genau der Fall, wo der Mountpunkt schon existiert,
        # der Inhalt aber noch nachzieht. Erst echter (nicht-leerer)
        # Inhalt, der sich zwischen zwei Abfragen nicht mehr aendert,
        # gilt als fertig.
        has_content = found and total > 0
        if elapsed >= max_wait:
            LOG("_wait_for_usb_stable: Zeitlimit (%.1fs) erreicht, fahre trotzdem fort"
               % max_wait)
            # Beim Zeitlimit unterscheiden: ist ueberhaupt ein
            # Mountpunkt da? Wenn ja, ist er evtl. nur noch nicht
            # stabil - trotzdem unsicher, also nicht cachen (False).
            # Wenn gar keiner kam, ist es ein Setup ohne USB (None).
            return False if found else None
        if has_content and total == last_total:
            stable_streak += 1
            if stable_streak >= 2:
                LOG("_wait_for_usb_stable: USB-Inhalt stabil (%d Eintraege) nach %.1fs"
                   % (total, elapsed))
                return True
        else:
            stable_streak = 0
        if not found and elapsed >= min_wait_if_none:
            return None
        last_total = total if has_content else None
        time.sleep(poll)

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
    """Pro kanonischem Namen (ohne Region-/Versions-Tags) nur die
    Kopie mit der besten Region behalten (Germany > Europe > World >
    USA > Japan). Wird PRO ORDNER angewendet (nicht global ueber das
    ganze System), damit typische nach Anfangsbuchstabe/Region
    aufgeteilte Sammlungen nicht faelschlich ueber Ordnergrenzen
    hinweg zusammengemischt werden."""
    best = {}
    for entry in raw_items:
        key = _canonical_key(entry[0])
        rank = _region_rank(entry[0])
        cur = best.get(key)
        if cur is None or rank < cur[0]:
            best[key] = (rank, entry)
    items = [entry for _rank, entry in best.values()]
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
    total_sys = len(GAME_SYSTEMS)
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
        if sys_node["folders"] or sys_node["items"]:
            cats.append((disp, sys_node, syskey))
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
    "sys_attract_on":  {"en": "Attract mode (screensaver): ON -> turn off",
                        "de": "Attract-Modus (Bildschirmschoner): AN -> ausschalten"},
    "sys_attract_off": {"en": "Attract mode (screensaver): OFF -> turn on",
                        "de": "Attract-Modus (Bildschirmschoner): AUS -> einschalten"},
    "attract_hint": {"en": "Press any button to continue",
                     "de": "Beliebige Taste zum Fortfahren"},
    "scanning":  {"en": "Scanning: %s", "de": "Durchsuche: %s"},
    "recent_cat": {"en": "Recently Played", "de": "Zuletzt gespielt"},
    "favorites_cat": {"en": "Favorites", "de": "Favoriten"},
    "favorite_added": {"en": "Added to favorites", "de": "Zu Favoriten hinzugefuegt"},
    "favorite_removed": {"en": "Removed from favorites", "de": "Aus Favoriten entfernt"},
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


def system_items(music_enabled=None):
    crt = crt_menu_active()
    video = t("sys_video_crt") if crt else t("sys_video_hdmi")
    music_label = t("sys_music_on") if music_enabled else t("sys_music_off")
    curated_label = t("sys_curated_on") if curated_only_active() \
        else t("sys_curated_off")
    attract_label = t("sys_attract_on") if attract_enabled() \
        else t("sys_attract_off")
    return [
        (t("sys_osd"),                             "osd",       None),
        (video + t("sys_video_suffix"),             "crtmenu",   None),
        (music_label,                                "music",     None),
        (t("sys_language"),                          "language",  None),
        (t("sys_configure_buttons"),                 "remap",     None),
        (t("sys_reset_buttons"),                     "remap_reset", None),
        (curated_label,                              "curated",   None),
        (attract_label,                               "attract",   None),
        (t("sys_rescan"),                            "rescan",    None),
        (t("sys_redraw"),                            "redraw",    None),
        (t("sys_reboot"),                            "reboot",    None),
        (t("sys_quit"),                              "quit",      None),
    ]

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
ATTRACT_IDLE_SECONDS = 45   # so lange ohne Eingabe, bevor der Attract-
                            # Modus (Bildschirmschoner) automatisch startet
ATTRACT_CHANGE_SECONDS = 6  # wie lange ein Spiel im Attract-Modus gezeigt wird

def attract_enabled():
    """Standardmaessig AN (im Gegensatz zu curated_only_active(), das
    standardmaessig AUS ist) - die Datei bedeutet hier 'abgeschaltet',
    nicht 'aktiviert'."""
    return not os.path.exists(ATTRACT_DISABLED_FLAG)

def toggle_attract_mode():
    if os.path.exists(ATTRACT_DISABLED_FLAG):
        try:
            os.remove(ATTRACT_DISABLED_FLAG)
        except OSError:
            pass
    else:
        try:
            dirname = os.path.dirname(ATTRACT_DISABLED_FLAG)
            if dirname:
                os.makedirs(dirname, exist_ok=True)
            open(ATTRACT_DISABLED_FLAG, "w").close()
        except OSError:
            pass

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

        # Netzwerkstatus fuer die Anzeige unten rechts im Hauptmenue -
        # mit kurzer Zwischenspeicherung (alle paar Sekunden neu
        # geprueft), damit auch bei sehr haeufigem Neuzeichnen (CRT
        # bis 100x/Sekunde) nicht bei jedem einzelnen Bild ein
        # Systemaufruf noetig ist, obwohl die Pruefung selbst schon
        # sehr guenstig ist (kein echter Netzwerkverkehr, <2ms).
        self._net_status = False
        self._net_check_next = 0.0

        # Favoriten-Namen im Speicher gehalten (Set fuer O(1)-Abfrage
        # beim Zeichnen) - NUR bei tatsaechlichen Aenderungen ueber
        # toggle_favorite() aktualisiert, nie durch erneutes Einlesen
        # der Datei bei jedem Neuzeichnen (das waere bei bis zu
        # 100 Bildern/Sekunde auf CRT ein spuerbares Performance-
        # Problem - genau das haben wir an anderer Stelle in diesem
        # Projekt schon mehrfach gefunden und behoben).
        self._favorites_set = set(
            e.get("label") for e in _load_favorites_raw() if "label" in e)

        # Attract-Modus (Bildschirmschoner): blaettert nach einer
        # Weile ohne Eingabe von selbst durch zufaellige Spiele mit
        # Boxart - siehe next_action()/draw_attract().
        self.attract_mode = False
        self._last_input_time = time.time()
        self._attract_game = None
        self._attract_change_next = 0.0
        self._attract_pool = None   # zwischengespeicherte flache Spieleliste

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
        recent_items = load_recent()
        if recent_items:
            # Ganz vorne, damit sie ohne Scrollen erreichbar ist.
            # syskey=None (wie Scripts/System), da die Liste mehrere
            # Systeme mischt - jeder Eintrag traegt seinen eigenen
            # Systemkey in arg[2], der beim Zeichnen bevorzugt wird
            # (siehe _item_syskey()).
            self.cats.insert(0, (t("recent_cat"), _wrap_flat(recent_items), None))
        favorite_items = load_favorites()
        if favorite_items:
            # Direkt nach "Zuletzt gespielt" (falls vorhanden, sonst
            # ganz vorne) - eigene, bewusst kuratierte Auswahl, im
            # Gegensatz zur automatischen Verlaufsliste.
            pos = 1 if recent_items else 0
            self.cats.insert(pos, (t("favorites_cat"), _wrap_flat(favorite_items), None))
        self.cats.extend((n, _wrap_flat(it), sk) for n, it, sk in scan_cores())
        scripts = scan_scripts()
        if scripts:
            self.cats.append(("Scripts", _wrap_flat(scripts), None))
        self.cats.append(("System", _wrap_flat(system_items(self.music.enabled)), None))
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
        zu schliessen."""
        if self.page == 1:
            if self.nav_path:
                self.nav_path.pop()
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

        if self.page == 1:
            display = self._display_items()
            if self.item_i >= len(display):
                self.item_i = max(0, len(display) - 1)

    def _enter_category(self):
        """Von Seite 0 (Kategorien-Menue) in Seite 1 (Liste der
        aktuellen Kategorie, oberste Ordnerebene) wechseln."""
        _name, node, _sk = self.cats[self.cat_i]
        if not node["folders"] and not node["items"]:
            return
        self.page = 1
        self.nav_path = []
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
            hd = os.path.join(ART_HD, syskey, name + ".art")
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
            name, node, _sk = self.cats[i]
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

        # Artbox rechts: Logo/Cover des gerade markierten Systems
        self._draw_cat_artbox(L)

        if message:
            fb.text(ox, H - oy - 13 * s, message, s, C_DIM, C_BG)
        self._draw_status_bar(L)
        if flip:
            fb.flip()

    def _network_connected(self):
        """Zwischengespeicherter Netzwerkstatus, alle 5 Sekunden neu
        geprueft (nicht bei jedem einzelnen Neuzeichnen - unnoetig
        haeufige Systemaufrufe vermeiden, auch wenn die Pruefung
        selbst schon sehr guenstig ist)."""
        now = time.time()
        if now >= self._net_check_next:
            self._net_status = _has_network()
            self._net_check_next = now + 5.0
        return self._net_status

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

        if y_max > y_min:
            fb.flip_rows(y_min, y_max - y_min)

    def _draw_dynamic_items(self):
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
        mehr (kein Glow dort), verhindert das Artefakt aber zuverlaessig."""
        v = getattr(self, "view", None)
        if not v or not v["items"]:
            return
        s, rowh = v["s"], v["rowh"]
        row = self.item_i - self.scroll
        if not (0 <= row < self.items_visible):
            return
        fb = self.fb
        list_x, list_right = v["list_x"], v["list_right"]
        total = len(v["items"])
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
        # Reihenfolge WICHTIG: beim vollen Aufbau werden die Zeilen in
        # AUFSTEIGENDER Reihenfolge gezeichnet (Index 0, 1, 2, ...) -
        # der Glow-Rand der markierten Zeile ueberlappt dadurch je nach
        # Position unterschiedlich: in eine VORHERIGE Zeile bleibt der
        # Glow sichtbar (die markierte Zeile wird SPAETER gezeichnet,
        # also obenauf), in eine NACHFOLGENDE Zeile wird der Glow vom
        # spaeter gezeichneten Nachbarn wieder begrenzt. Das muss hier
        # exakt in derselben Reihenfolge nachgebildet werden, sonst
        # bleiben Bildreste zurueck (per Differenzvergleich gefunden).
        has_prev = self.item_i > self.scroll
        has_next = (self.item_i + 1 < self.scroll + self.items_visible
                    and self.item_i + 1 < total)
        if has_prev:
            self.draw_list_row(self.item_i - 1)
        self.draw_list_row(self.item_i)
        if has_next:
            self.draw_list_row(self.item_i + 1)

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
        # Grosszuegiger Bereich, der die tatsaechlich aufgefrischten
        # Zeilen (markierte Zeile + evtl. Nachbarn) komplett abdeckt -
        # ein paar zusaetzliche Pixel zu flippen kostet kaum etwas,
        # verglichen mit dem Risiko, eine aufgefrischte Nachbarzeile
        # nur teilweise auf den Schirm zu bringen.
        flip_y0 = y_top - (rowh if has_prev else max_p)
        flip_y1 = y_top + rowh - 2 * s + max_p + (rowh if has_next else 0)
        fb.flip_rows(flip_y0, flip_y1 - flip_y0)

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
        if self._cur_bg is not None:
            fb.buf[:] = self._cur_bg
        else:
            fb.clear(C_BG)

        # Breadcrumb: Kategorie + aktueller Ordnerpfad (falls in einen
        # Unterordner gewechselt wurde), z.B. "SNES / 1 US-A-E".
        header = name if not self.nav_path else name + " / " + " / ".join(self.nav_path)
        header = header.upper()
        header_maxc = max(4, (list_right - ox) // (16 * s))
        if len(header) > header_maxc:
            header = header[:max(1, header_maxc - 1)] + "~"
        fb.text(ox, oy, header, 2 * s, C_TITLE)
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

        if message:
            fb.text(ox, footer_y, message, s, C_DIM)
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
        item_kind = v["items"][idx][1]
        # Markierung nur bei echten Spielen, per Namen im bereits
        # geladenen Speicher-Cache nachgeschlagen (kein Datei-Zugriff
        # hier - das waere bei haeufigem Neuzeichnen ein echtes
        # Performance-Problem).
        is_fav = item_kind == "game" and full in self._favorites_set
        prefix = "* " if is_fav else ""
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
        prefix_len = 2 if (kind == "game" and label in self._favorites_set) else 0
        maxc = (v["list_right"] - v["list_x"] - 8 * s) // (8 * s) - prefix_len
        return len(label) > maxc

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
        """Versatz weiterschieben (mit Pause an den Enden) - gedrosselt
        ueber _track_tick_next. Auflösungsabhaengig: auf CRT laeuft es
        ueber einen kuerzeren Takt (0.15s statt 0.35s, wie beim
        Equalizer - draw() ist dort so guenstig, dass es nicht ins
        Gewicht faellt). Auf HDMI bleibt der Takt bei 0.35s (kein
        zusaetzliches Neuzeichnen), stattdessen ruecken pro Tick 2
        Zeichen statt 1 weiter - verdoppelt die gefuehlte Geschwindig-
        keit, ohne die Redraw-Haeufigkeit zu erhoehen."""
        now = time.time()
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
        elapsed = time.time() - self._pulse_t0
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
        now = time.time()
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
        now = time.time()
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
        now = time.time()
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
            self._last_input_time = time.time()
            return
        self.attract_mode = True
        self._attract_game = random.choice(pool)
        self._attract_change_next = time.time() + ATTRACT_CHANGE_SECONDS
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
        self._attract_change_next = time.time() + ATTRACT_CHANGE_SECONDS
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
                    self._last_input_time = time.time()
                    self.draw()
                    self.music.tick()
                    continue
                self._last_input_time = time.time()
                if need_mq:
                    self.marquee_reset()
                return act

            if self.attract_mode:
                if time.time() >= self._attract_change_next:
                    self._advance_attract()
            elif (attract_enabled()
                  and time.time() - self._last_input_time > ATTRACT_IDLE_SECONDS):
                self._enter_attract_mode()
            else:
                if need_mq:
                    self.marquee_tick()
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
        fb.rect(x0 - pad, y0 - pad, w + 2 * pad, h + 2 * pad, C_PANEL)
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
            hd = os.path.join(ART_HD, syskey, lookup_name + ".art")
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
                t0 = time.time()
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
        # enter_console_mode()/set_cursor_blink()/inp.grab() passieren
        # jetzt schon in __init__(), VOR dem Scan - siehe Kommentar dort.
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

                name, _root_node, _syskey = self.cats[self.cat_i]
                items = self._display_items() if self.page == 1 else []

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
                            msg = t("favorite_added") if now_fav \
                                else t("favorite_removed")
                            self.draw(message=msg)
                            continue
                elif act == "ok":
                    if self.page == 0:
                        self._enter_category()
                    else:
                        label, kind, arg = items[self.item_i]
                        if kind == "folder":
                            self.nav_path.append(arg)
                            self.item_i = 0
                            self.scroll = 0
                            self.marquee_reset()
                        elif kind == "core":
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
                        elif kind == "attract":
                            toggle_attract_mode()
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
