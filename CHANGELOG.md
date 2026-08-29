# Changelog

Was sich am Frontend so getan hat. Für die ganz kleinteiligen Details
schau am besten in die Git-Historie oder in den Kopf von
`frontend/frontend.py`.

## v4.4 — Reset-Feature, HDMI-Performance-Runde, Stream-Menüpunkt

**Neue Features:**
- RetroAchievements lässt sich jetzt direkt im System-Menü an- und
  ausschalten (Nutzerwunsch: "ich würde gerne die Option haben, die
  RetroAchievements von dort an und aus zu schalten" - bisher gab es
  unter "RetroAchievements" nur "neu laden", ein echtes Deaktivieren
  ging nur durch Löschen/Umbenennen der Zugangsdaten-Datei per SSH).
  Neue zweite Zeile direkt unter der bestehenden "neu laden"-Zeile,
  erscheint aber bewusst NUR, wenn überhaupt Zugangsdaten hinterlegt
  sind (ohne Einrichtung gibt es noch nichts zum Umschalten). Getrennt
  von der Einrichtung selbst - Benutzername/API-Schlüssel bleiben beim
  Ausschalten unangetastet, ein späteres Wiedereinschalten braucht
  keine erneute Einrichtung. Betrifft die Fortschrittsanzeige/
  Abzeichen/Erfolgs-Vitrine/Bestenlisten/Meilensteine (alles, was auf
  ra_enabled() aufbaut) - NICHT die RA-Core-Auswahl beim Betreten eines
  Systems (find_ra_core()), die unabhängig davon weiterläuft, falls
  eine RA-fähige Core-Variante im _RA_Cores-Ordner liegt. Standard
  unverändert AN für alle, die den neuen Schalter nicht anfassen.
  Verifiziert mit 9 gezielten Tests (u.a. dass die Zeile ohne
  Zugangsdaten korrekt NICHT erscheint, und dass die Zugangsdaten beim
  Aus-/Wiedereinschalten unverändert bleiben) plus der vollständigen
  Regressionssuite.
- N64_ALSA.rbf/PSX_ALSA.rbf im _RA_Cores-Ordner werden jetzt bevorzugt
  geladen (Nutzerwunsch): liegt eine dieser ALSA-Core-Varianten dort
  vor, wird sie fuer RetroAchievements-Starts des jeweiligen Systems
  verwendet statt der bisherigen normalen RA-Core-Datei (N64.rbf bzw.
  PSX.rbf). Ist keine ALSA-Datei vorhanden, greift wie gehabt der
  normale RA-Core aus diesem Ordner - keine Aenderung fuer alle, die
  keine ALSA-Variante installiert haben. Betrifft ausschliesslich
  find_ra_core() in fe/ra_core.py (eine einzige, zentrale Stelle,
  ueber die JEDER RA-Core-Start laeuft - Core-Auswahl-Bildschirm beim
  Kategorie-Eintritt, Weiterspielen/Zuletzt gespielt/Favoriten, Wonne
  oder Tonne) - keine weiteren Aenderungen an frontend.py noetig,
  find_ra_core() war fuer genau so eine Namens-Priorisierung schon von
  Anfang an ausgelegt ("mehrere plausible Varianten durchprobiert -
  die erste tatsaechlich existierende gewinnt").
- PERF-Profiling fuer die vier zentralen Navigations-Zeichenpfade
  (Nutzer-Rueckmeldung: "das muss unter HDMI insgesamt fluessiger
  laufen, auch beim Wechsel rein/zurueck und beim reinen Scrollen" -
  trotz bereits behobenem Icon-Vorwaerm-Bug und bereits aktiviertem
  "Schnelles Scrollen"). WICHTIG: dies ist noch KEIN weiterer Fix,
  sondern gezielte Messinfrastruktur - eine ausfuehrliche Durchsicht
  aller periodischen draw()-Prüfungen, Hintergrund-Threads, des
  Boxart-Ladepfads und der bereits mehrfach HDMI-optimierten
  Zeichenroutinen (rect_rounded()/glow_border_fast()/gebündeltes
  flip_rows() - alles schon aus frueheren Runden) ergab keinen
  weiteren offensichtlichen Verdaechtigen, der sich allein durch
  Code-Lesen sicher bestaetigen liesse. Es gab bereits einen
  optionalen, per Umgebungsvariable (`DRAGEND_PROFILE=1`)
  einschaltbaren cProfile-Mitschnitt fuer draw_page_items() (aus einer
  frueheren Runde, als reale Messwerte von 150-250ms sich in dieser
  Cloud-Sandbox trotz nachgebauter grosser Sammlungen nie reproduzieren
  liessen) - der ist jetzt auf alle vier zentralen Pfade ausgeweitet:
  draw_page_cats()/draw_page_items() (voller Seitenwechsel, z.B.
  rein in einen Ordner/zurueck) sowie _draw_navigate_cats()/
  _draw_navigate_items() (einzelner Scroll-Schritt). Normalbetrieb
  bleibt unveraendert leichtgewichtig (nur eine Zeitmessung, Log-Zeile
  nur bei ungewoehnlicher Dauer) - mit `DRAGEND_PROFILE=1` gesetzt
  liefert das Log beim naechsten Auftreten des Rucklers zusaetzlich
  eine vollstaendige Funktions-fuer-Funktion-Aufschluesselung (Top 12
  nach kumulativer Zeit) sowie Text-Cache-Trefferquote - das soll beim
  naechsten Mal endlich zeigen, WAS auf dem echten Geraet tatsaechlich
  die Zeit kostet, statt weiter zu raten.
- Arcade-Unterordner (z.B. "alternatives", "organized", "insert Coin",
  "ST-V" - übliche Ordnung bei kuratierten Arcade-Sammlungen) sind
  jetzt auch im Frontend sichtbar und navigierbar, genau wie im OSD
  (Nutzerfrage: "wenn ich über das OSD auf Arcade gehe werden mir
  noch Ordner angezeigt … warum sehe ich diese nicht im Frontend?").
  Ursache: Arcade nutzte bisher einen rein FLACHEN Ordner-Scan (nur
  .mra/.rbf/.mgl-Dateien DIREKT im `_Arcade`-Ordner selbst), anders
  als die regulären Spielesysteme, die schon länger beliebig tief
  verschachtelte Unterordner unterstützen. Arcade bekommt jetzt
  denselben rekursiven Ordnerbaum wie diese - Unterordner (auch
  mehrere Ebenen tief) erscheinen als eigene, öffenbare Einträge.
  Bewusst NUR für Arcade eingeführt, die übrigen generischen
  `_*`-Core-Ordner (Console/Computer/Utility/...) bleiben unverändert
  flach, dort ist eine tiefe Ordnerorganisation in der Praxis kaum
  gebräuchlich.
- Musik-Titel-Laufschrift jetzt ein/ausschaltbar (System -> Anzeige,
  Nutzerwunsch: "Musik Laufschrift hätte ich auch gerne noch ein und
  ausschaltbar"). Ausgeschaltet zeigt der Songtitel weiterhin (den
  Anfang von) sich selbst an, scrollt aber nicht mehr - betrifft nur die
  Songtitel-Laufschrift, nicht die separate Laufschrift für zu lange
  Spieletitel in der Liste selbst. Wirkt sofort, ohne Neustart, gleiches
  An/Aus-Muster wie beim Equalizer/Schimmer-Effekt.
- Update-/Fix-Hinweis fragt jetzt aktiv nach, statt nur kurz einzublenden
  (Nutzerwunsch: "können wir das Update-Popup wenn die Info kommt gleich
  eine Abfrage hinzufügen, ob man jetzt das Update gleich installieren
  will oder später?"): sowohl der Versions- als auch der unabhängige
  Build-/Fix-Hinweis (siehe "ich möchte bei v4.4 bleiben, aber trotzdem
  einen Hinweis sehen, wenn es neue Fixes gibt" weiter unten in diesem
  Changelog) zeigen jetzt einen echten Ja/Nein-Dialog ("Jetzt" /
  "Später", "Später" sicherheitshalber vorausgewählt) statt der
  bisherigen, nach wenigen Sekunden von selbst verschwindenden Meldung.
  "Jetzt" startet `Frontend_Install.sh` über denselben, bereits
  ausführlich getesteten Weg wie ein manueller Tap auf "Frontend
  Install" im Scripts-Menü - der beendet den alten Frontend-Prozess
  sauber und schließt danach automatisch mit einem kompletten
  MiSTer-Neustart ab, siehe "Hardreset nach Update-Installation" weiter
  unten unter Bugfixes.
- Neuer Menüpunkt "Bestätigen/Abbrechen vertauschen" (System -> Eingabe):
  ein einziger Umschalter für den häufigsten Fall unpassender Pad-
  Belegung (z.B. Nintendo- statt Xbox-Tastenlayout) - vertauscht überall
  im Frontend die Rollen von OK/Bestätigen und Zurück/Abbrechen, ohne
  die komplette Tastenbelegungs-Prozedur durchlaufen zu müssen. Hinweis
  dazu: MiSTers eigene Controller-Zuordnung (aus dem echten MiSTer-Menü,
  "Joystick-Belegung definieren") lässt sich nicht verlässlich vom
  Frontend mitgelesen werden - die zugrunde liegenden Dateien sind ein
  undokumentiertes, sich zwischen Firmware-Versionen bereits mehrfach
  geändertes Binärformat, das selbst MiSTer-eigene Community-Tools nur
  als unauswertbaren Kopier-Block behandeln. Der Umschalter hier ist
  daher eine bewusst eigenständige, robuste Lösung statt eines
  fragilen Versuchs, MiSTers interne Zuordnung nachzubauen.
- Reset im laufenden Core per F5 (Taste ~0,6s halten) - funktioniert
  bei allen Cores, auch RA-Cores, ohne den Core selbst neu zu laden
  (RA-Fortschritt bleibt erhalten). Ausdrücklich als experimentell
  gekennzeichnet. Die Tasten-Erkennung wurde über mehrere echte
  Hardware-Logs hinweg entwickelt und bestätigt (ursprünglich auf Tab
  gelegt, aber auf NKRO-Tastaturen wie dem KBDFans Tiger80 nie
  ausgelöst - aus genau diesem Log ließ sich die tatsächliche
  Bit-Position messen und auf F5 übertragen).
- Stream-Overlay jetzt direkt im Menü an/aus schaltbar (System ->
  Anzeige & Sound), zusätzlich zum bisherigen externen
  `stream_toggle.sh`. Wirkt wie bisher erst nach einem Neustart.
- Bildschirmspiegel (`/mirror`, eigener Menüpunkt, braucht Stream-
  Overlay): zeigt den aktuellen Frontend-Bildschirm zusätzlich im
  Browser - praktisch für CRT-Nutzer, die HDMI nicht direkt einsehen
  können. Zeigt nur den Frontend-Bildschirm selbst (Kategorien,
  Spieleliste), nicht das laufende Spiel (technisch nicht möglich,
  siehe Abschnitt 12.1 der README) - arbeitet deshalb bewusst nur bei
  CRT-typischen Auflösungen, HDMI wird komplett übersprungen (bei
  HDMI-Auflösung gemessen: bis zu 830ms pro Bild, spürbare
  CPU-Konkurrenz mit der Eingabe-Hauptschleife).
- Automatischer OBS-Szenenwechsel (Einrichtung über die bestehende
  `/admin`-Weboberfläche): wechselt OBS automatisch zur
  Capture-Karten-Szene, sobald ein Spiel startet, und zurück zur
  Frontend-Szene, sobald wieder im Menü - eigener, von Grund auf
  geschriebener OBS-WebSocket-v5-Client (reine Python-
  Standardbibliothek, keine externen Pakete). Komplett
  fehlertolerant: nicht konfiguriert oder OBS nicht erreichbar
  verzögert niemals Spielstart/Rückkehr zum Menü.
- F2 als zweite, gleichwertige Taste für die (bereits bestehende)
  Volltextsuche - bisher nur über "/" erreichbar. Löst exakt dieselbe
  Aktion aus, keinerlei Verhaltensänderung für die bestehende
  "/"-Taste. Gedacht für Sammlungen mit vielen Einträgen, bei denen
  ein Sprung mitten in den Namen praktischer ist als der klassische
  Erster-Buchstabe-Sprung.
- Equalizer-Balken jetzt einzeln über System -> Anzeige & Sound
  abschaltbar, unabhängig von der pulsierenden Markierung - gedacht
  zum Testen, ob das beim Scrollen im HDMI-Modus spürbar hilft.
- 9 neue geheime Konsolen-Themes (dazu passender Sound und kurzer
  Vollbild-Effekt beim Freischalten), jedes über einen eigenen
  Geheimcode nach dem Vorbild eines echten klassischen Cheat-/
  Level-Select-Codes: SNES (Batman Forever), Game Boy (Game Genie),
  Game Boy Color (Space Invaders), N64 (Robotron 64), PS1 (Aladdin),
  Mega Drive (Sonic 2 Sound-Test), Master System (Sonic Chaos),
  Game Gear (Sonic Chaos) und Saturn (Sonic Jam/Sonic 2
  Level-Auswahl). Alle 14 Geheimcodes (die 5 bisherigen plus die 9
  neuen) sind untereinander eindeutig geprüft - keiner löst
  versehentlich einen anderen vorzeitig aus. Dreamcast bewusst NICHT
  dabei, da sich kein wirklich eindeutiger, belegter Original-Code
  finden ließ. Das N64-Theme hat als einziges eine echte
  Zusatzwirkung: schaltet beim allerersten Freischalten automatisch
  das bereits bestehende "Schnelles Scrollen" ein (rein additiv, wird
  danach nie mehr von selbst wieder ausgeschaltet). Alle neuen
  Geheimnisse erscheinen wie gewohnt in der Geheimnis-Übersicht,
  sobald gefunden. Nur per Tastatur eingebbar, wie alle anderen
  Codes.
- CRT/HDMI-Sicherheitsnetz: Wechselst du auf CRT-Videomodus, ohne dass
  tatsächlich ein CRT angeschlossen ist, bleibt der Bildschirm nach
  dem Neustart schwarz - ohne echte CRT-Erkennung (technisch nicht
  möglich) bisher ein kompletter Aussperrer ohne physischen
  Hardware-Zugriff. Jetzt zeigt das Frontend direkt nach dem Umschalten
  einen Hinweis mit 20-Sekunden-Countdown; kommt in dieser Zeit keine
  einzige echte Eingabe an, schaltet es automatisch zurück auf HDMI
  und startet selbst neu. Eine einzige Eingabe bestätigt CRT dagegen
  dauerhaft.
- F6-Erfolgs-Vitrine unterscheidet jetzt zwischen Hardcore und Softcore
  (Nutzer-Rückmeldung: "wir unterscheiden gar nicht zwischen Softcore-
  oder Hardcore-Mode bei den Erfolgen"). RA liefert pro Erfolg zwei
  getrennte Freischalt-Zeitstempel (ein Hardcore-Unlock setzt dabei
  immer zusätzlich auch den Softcore-Stempel) - bisher wertete das
  Frontend nur "irgendeinen davon" aus, der Modus selbst ging
  verloren. Jede Zeile zeigt jetzt "[HC]" (golden hervorgehoben) für
  einen im Hardcore-Modus erreichten Erfolg, "[SC]" für einen nur im
  Softcore-Modus erreichten, "[ ]" wie bisher für noch offene - ohne
  zusätzlichen RA-Abruf, die Information stand in den ohnehin schon
  geladenen Rohdaten bereits bereit.
- F6 zeigt Erfolge jetzt spürbar schneller an (Nutzerfrage: "wäre es
  noch möglich, diese, wenn ich F6 gedrückt habe, noch schneller
  anzuzeigen?"). Das bestehende Hintergrund-Vorwärmen im Leerlauf
  (Favoriten/zuletzt Gespielte zuerst) lud bisher nur die
  Text-Erfolgsliste vor - die Badge-Icons wurden erst beim
  tatsächlichen F6-Druck selbst nachgeladen, bei einem noch nie
  angesehenen Spiel mit vielen Erfolgen durchaus spürbar. Das
  Vorwärmen lädt jetzt beides zusammen vor - im Regelfall (Spiel war
  in Reichweite des Vorwärmens) ist beim F6-Druck dadurch wirklich
  alles bereits lokal vorhanden.

**Performance (vor allem HDMI-Modus):**
- Größter Einzelfund: der komplette Bildschirm-Neuaufbau (47-57ms bei
  JEDEM Bild, auch beim reinen Scrollen) wird jetzt übersprungen, wenn
  sich seit dem letzten eigenen Neuaufbau nachweislich nichts anderes
  am Bildschirm verändert hat - abgesichert über einen Generations-
  zähler, der bei JEDER anderen Bildschirmseite automatisch mitzählt.
- Festplatten-Cache für skalierte Cover-Bilder (Miniaturen) - macht
  erneutes Laden praktisch kostenlos (bestätigt: über 1000ms auf
  wenige ms gesenkt).
- Cover-Ordner werden beim Start im Hintergrund vorgewärmt, behebt
  eine über 1 Sekunde lange Verzögerung beim ersten Betreten eines
  Systems pro Sitzung (kaltes SD-Karten-Verzeichnis).
- Zielgröße des Cover-Rückfallbilds (für Spiele ohne eigenes Cover)
  wird auf ein gröberes Raster gerundet - verhindert, dass praktisch
  jedes Spiel ohne Cover eine eigene, teure Neuberechnung auslöst.
- Abgerundete Ecken (Auswahl-Markierung, Cover-Panel-Karte) cachen
  jetzt ihre Randzeilen, statt sie bei jedem Bild neu zu berechnen.
- Sortierte Ordner-/Spieleliste (`_display_items()`) wird jetzt direkt
  am Navigations-Knoten gecacht, statt bei jedem der vielen Aufrufe
  (Zeichnen, Stream, Suche, Cover-Vorladen, ...) neu sortiert zu
  werden.
- Stream-Overlay-Publizierung prüft jetzt günstig vor (Auswahl/
  Songtitel), bevor die teure vollständige Zustands-Berechnung
  überhaupt angestoßen wird - betrifft nur Sitzungen mit aktivem
  Stream-Overlay, dort aber bei jedem Schleifendurchlauf.
- "Turbo-Scroll": Boxart- und Info-Panel-Neuaufbau wird während eines
  schnellen Scroll-Laufs (dieselbe Erkennung wie beim bestehenden
  VSync-Skip) verzögert und erst einmalig neu gezeichnet, sobald der
  Scroll-Lauf stoppt - reduziert die Bildlast zusätzlich genau in den
  Momenten, in denen ohnehin am schnellsten gescrollt wird.
- SD-Boxart-Zielgröße für CRT von 100×120 auf 104×168 angepasst -
  exakt anhand der tatsächlichen maximalen Panel-Geometrie berechnet
  (vorher spürbar kleiner als möglich, ohne dass es einen Grund dafür
  gab).

**Diagnose-Werkzeuge** (für Fehlersuche auf echter Hardware, ohne
Verhaltensänderung im Normalbetrieb):
- `DRAGEND_PROFILE=1`-Umgebungsvariable: detailliertes cProfile-
  Profiling bei langsamen Bildaufbauten, direkt ins Log geschrieben.
- Festplatten-Cache-Treffer/-Fehler für Cover jetzt im Log sichtbar
  (`THUMB_CACHE ...`).
- Textcache-Treffer/-Fehler/-Verdrängungen jetzt im Log sichtbar
  (`TEXTCACHE ...`, nur bei aktivem `DRAGEND_PROFILE`).
- Größe und Änderungsdatum von `sysart/WOT.art` (Zufalls-Zock-Vorschau
  in der Boxart) jetzt bei jedem Start im Log sichtbar.
- Start-Dauer bis das Kategorien-Menü zum ersten Mal bereit ist
  (Framebuffer/Eingaben öffnen, RA-Abruf anstoßen, Spieleliste
  einlesen) jetzt einmalig pro Start im Log sichtbar (Nutzerfrage: "ob
  man den Bootvorgang noch etwas beschleunigen könnte") - bisher gab
  es dafür keine Messung auf echter Hardware, jede weitere
  Optimierung wäre ohne diese Zahl nur Raten gewesen.

**KORREKTUR** (Nutzer-Rückmeldung: "das Bild für Zufalls-Zock muss in
den Ordner sysart, du hast einen eigenen wot_logo-Ordner dafür
erstellt, das war nicht richtig"): der vorherige Build hatte für das
neue Zufalls-Zock-Bild fälschlich einen komplett neuen, eigenen
Mechanismus samt eigenem `wot_logo/`-Ordner eingeführt (ein
zusätzliches Logo-Bild oben im Zufalls-Zock-Bildschirm selbst). Der
eigentliche, schon lange vor dieser Session bestehende Ort für dieses
Bild ist aber `sysart/WOT.art` - darüber läuft die kleine Vorschau
links neben der Kategorie "Zufalls-Zock" im Kategorien-Hauptmenü, auf
die sich der ursprüngliche Nutzerwunsch ("das alte Bild in der Boxart
neben der Kategorie ZUFALLS-ZOCK austauschen") die ganze Zeit bezog.
Diese Datei wurde beim vorherigen Versuch nie angefasst - das erklärt
auch, warum dort weiterhin das alte Bild zu sehen war. Jetzt korrigiert:
`wot_logo/` komplett entfernt, das neue Bild liegt jetzt korrekt unter
`sysart/WOT.art`, der Zufalls-Zock-Bildschirm selbst zeigt wieder nur
den reinen Text-Titel wie vor dieser Session.

**Bugfixes:**
- Der nicht mehr funktionierende Hinweis "F10 / X (Pad) zurück ins
  Frontend" ganz unten in System → Hilfe/Übersicht wurde entfernt
  (Nutzer-Rückmeldung: "das muss raus das funktioniert ja garnicht").
  Die zugehörige Tastenkombination gab es an dieser Stelle schlicht
  nicht mehr, der Eintrag war ein Überbleibsel aus einer früheren
  Bedienlogik - entfernt aus der `section_keys`-Liste in
  `draw_help_screen()`, die verwaisten Übersetzungsschlüssel gleich mit
  aufgeräumt.
- Durchgängige Rechtschreib-Auffrischung: sämtliche noch als "ae"/"oe"/
  "ue" geschriebenen Umlaute in den sichtbaren deutschen Texten (Menüs,
  Überschriften, Hinweise, Dialoge - alles aus `fe/translations.py`)
  wurden durch echte ä/ö/ü/Ä/Ö/Ü ersetzt (Nutzer-Rückmeldung: "dort
  steht überall noch die alte Schrift, mit zum Beispiel 'naechster
  Musiktitel' - das sieht blöd aus"). Der eigens dafür schon in einer
  früheren Runde erweiterte Zeichensatz (`FONT_EXTRA` in
  `fe/framebuffer.py`, deckt den Latin-1-Bereich inklusive ä/ö/ü/ß ab)
  konnte diese Zeichen technisch schon die ganze Zeit darstellen - nur
  die Übersetzungstexte selbst wurden nach dieser Erweiterung nie
  nachgezogen. Bewusst NUR die sichtbaren "de"-Texte geändert, NICHT
  die Code-Kommentare (die behalten wie gehabt die etablierte
  ASCII-Schreibweise) - 96 automatisiert geprüfte Ersetzungen plus eine
  von Hand nachgezogene ("Fuer" → "Für" in `year_review_empty`), dabei
  bewusst sechs echte Nicht-Umlaut-Wörter unangetastet gelassen
  (Aktuell, aufbauen, dauern, genaue, Hinschauen, Quelle - alle mit
  einem "ue"/"ae"/"oe", das kein Umlaut ist). Verifiziert per
  vollständigem Nachscan der Datei (nur noch die sechs beabsichtigten
  Ausnahmen übrig, jedes neu eingefügte Zeichen liegt im von
  `FONT_EXTRA` abgedeckten Bereich) sowie einer Syntaxprüfung.
- Update-Popup erscheint nach einem Update wieder zuverlässig, nicht
  mehr erst nach manuellem Update-Lauf (Nutzer-Rückmeldung: "ich
  bekomme seit ein paar Updates keine Popup-Info mehr, ich krieg die
  erst wenn ich manuell Update gemacht habe"). Gezielt nachgeprüft statt
  vermutet: der "Update jetzt installieren?"-Dialog (siehe
  `_start_update_install_dialog()`) läuft über exakt denselben
  Zeichenpfad wie der "Frontend beenden"-Dialog, dessen Übermal-Fehler
  im Build davor (2026-08-24-39) bereits behoben wurde (Laufschrift/
  Cover-Nachlade-Redraw löschten jeden offenen Dialog alle ~150ms
  wieder). Ein gezielter Test, der den echten Ablauf nachstellt (Update
  wird im Hintergrund erkannt, Dialog wird gezeichnet, direkt im selben
  Leerlauf-Tick ist zusätzlich ein Cover-Nachlade-Redraw fällig), bestätigt:
  dieser Fix behebt das Update-Popup-Problem bereits als Nebeneffekt mit -
  vorher wäre der frisch gezeichnete Dialog noch VOR der ersten
  Reaktionsmöglichkeit des Nutzers wieder übermalt worden, exakt die
  gemeldete Symptomatik.
  Zusätzlich zwei weitere, beim Nachprüfen gefundene Ursachen für
  denselben Effekt, die unabhängig vom obigen Fix bestanden und beide
  ebenfalls behoben wurden: (1) `_check_for_update_background()`
  markierte eine neue Version/einen neuen Build bereits beim blossen
  Erkennen im Hintergrund-Thread dauerhaft als "gezeigt"
  (`notified_version`/`notified_build_id` in
  `update_check_state.json`) - noch bevor der Haupt-Thread den Dialog
  überhaupt gezeichnet hatte. War der Dialog zu diesem Zeitpunkt (z.B.
  durch den oben behobenen Übermal-Fehler) trotzdem nicht sichtbar,
  blieb die Version/der Build für immer als "gezeigt" markiert - auch
  über einen Neustart hinweg, obwohl der Nutzer nie etwas zu sehen
  bekommen hatte. Jetzt wird "gezeigt" erst markiert und dauerhaft
  gespeichert, NACHDEM der Dialog tatsächlich gezeichnet wurde (siehe
  `next_action()`, Blöcke "pending_update"/"pending_build") - schlägt
  das Zeichnen fehl oder wird die Sitzung vorher beendet, fragt der
  nächste Start einfach erneut nach. (2) Sind ein Versions- UND ein
  Build-Update im SELBEN Leerlauf-Tick fällig, liefen beide Popup-
  Auslöser bisher bedingungslos nacheinander - der zweite Aufruf von
  `_start_update_install_dialog()` (Build-Hinweis) überschrieb dabei
  sofort wieder den gerade erst gezeichneten ersten Dialog
  (Versions-Hinweis), innerhalb desselben Funktionsaufrufs, noch bevor
  der Nutzer ihn zu Gesicht bekommen konnte - im Grunde dieselbe Art
  Fehler wie der Übermal-Fehler oben, nur durch den eigenen zweiten
  Dialog statt durch Laufschrift/Cover-Redraw ausgelöst. Der Build-
  Hinweis wartet jetzt einfach bis zum nächsten Leerlauf-Tick, sobald
  der Nutzer den Versions-Dialog beantwortet hat. Alle drei Fixe
  zusammen mit einer eigenen Testreihe verifiziert (u.a.: Erkennung
  allein markiert noch nichts als gezeigt; erst nach echtem Zeichnen
  wird gespeichert; zwei gleichzeitig fällige Popups überschreiben sich
  nicht mehr gegenseitig). Eine bereits VOR diesem Fix fälschlich als
  "gezeigt" markierte `update_check_state.json` auf einer bestehenden
  Installation kann dadurch nicht rückwirkend repariert werden - da
  sich die Build-Kennung (`build_id` in `LATEST_BUILD.json`) mit jeder
  Auslieferung ändert, wird der Zähler dafür aber automatisch mit
  diesem und jedem künftigen Build zurückgesetzt, ohne dass dafür etwas
  manuell gelöscht werden müsste.
  Im gleichen Zug (Nutzerwunsch: "prüfen ob irgendwo im Hintergrund
  zwei Mechanismen laufen und ob wir dadurch Einbußen beim
  Scrollverhalten haben") wurden sämtliche Hintergrund-Threads
  (Update-Check, RetroAchievements-Vorwärmen, Kunstwerk-Vorwärmen,
  NTP-Zeitabgleich, Bildschirmspiegelung fürs Streaming) sowie jeder
  periodische Zeichenpfad in `next_action()`s Leerlauf-Zweig gezielt
  daraufhin durchsucht, ob noch irgendwo direkt auf den Framebuffer
  geschrieben wird, ohne einen offenen Dialog oder laufende Navigation
  zu berücksichtigen. Ergebnis: außer den beiden oben beschriebenen,
  jetzt behobenen Fällen (Übermal-Fehler bei offenem Dialog,
  Popup-Kollision) schreibt kein Hintergrund-Thread direkt in den
  Framebuffer - alle setzen nur ein Ergebnis-Flag, das ausschließlich
  der Haupt-Thread konsumiert und zeichnet. Das RetroAchievements-
  Vorwärmen und die Bildschirmspiegelung waren bereits aus früheren
  Runden heraus eigens gegen genau dieses "Stocken beim Scrollen"
  gehärtet (Leerlauf-/Abbruch-Prüfung nach jedem einzelnen Schritt bzw.
  komplette Auslassung bei HDMI-Auflösung wegen GIL-Konkurrenz) - hier
  wurde keine neue Regression gefunden. Die volle Regressionssuite
  (18/18) läuft nach allen Änderungen weiterhin fehlerfrei durch.
- "Frontend beenden" (System → Wartung) schien bei manchen Nutzern
  nicht zu funktionieren (Nutzer-Rückmeldung: "die Meldung 'Frontend
  beenden' kam, dann wählte ich Ja und habe bestätigt, und das Fenster
  schloss sich wieder - konnte damit das Frontend nicht verlassen",
  reproduziert mit Joypad UND Tastatur). Ein echtes `frontend.log` von
  der betroffenen Hardware zeigte den tatsächlichen Ablauf: eine lange
  Folge aus ausschließlich "runter"+"OK"-Eingaben, ganz ohne ein
  einziges "links"/"rechts" dazwischen. Der Ja/Nein-Dialog selbst
  funktionierte technisch die ganze Zeit korrekt - er startet aber
  bewusst mit vorausgewähltem "Nein" (sicherer Standard gegen
  versehentliches Beenden), und ohne vorheriges Wechseln zu "Ja"
  bestätigt "OK" eben genau diese "Nein"-Option, der Dialog schließt
  sich wieder, ohne dass etwas passiert. Für den Nutzer sah das exakt
  wie "beenden geht nicht" aus. Zwei Verbesserungen direkt im Dialog:
  (1) ein sichtbarer Hinweistext ("Links/Rechts oder Hoch/Runter
  wählen, OK bestätigen") direkt im Dialog selbst, analog zum bereits
  bestehenden Hinweis beim Core-Auswahlbildschirm; (2) zusätzlich zu
  Links/Rechts schalten jetzt auch Hoch/Runter zwischen den beiden
  Optionen um - entspricht dem bereits vertrauten Verhalten an anderen
  Stellen im Frontend (Core-Auswahl, Zufalls-Zock), wo jede
  Richtungstaste umschaltet. Der sichere "Nein"/"Später"-Standard bei
  reiner OK-Wiederholung OHNE jede Richtungseingabe bleibt bewusst
  unverändert bestehen (per Test verifiziert) - es wurde nur die
  Bedienung selbst klarer und großzügiger gemacht, nicht die
  Sicherheitslogik geändert. Betrifft gleichermaßen den "Update jetzt
  installieren?"-Dialog, der denselben Dialograhmen wiederverwendet.
  NACHTRAG (weitere Nutzer-Rückmeldung, noch vor dem Hochladen dieses
  Builds: "sobald ich auf Frontend beenden klicke, ploppt das Fenster
  nur kurz auf und verschwindet wieder, ich kann nicht mal was
  auswählen"): das deutet zusätzlich auf ein reflexartiges zweites OK
  direkt nach dem OK hin, das den Dialog erst öffnet (z.B. aus
  Gewohnheit, weil man bei den meisten Menüpunkten einfach OK drücken
  kann) - dieses zweite OK bestätigte bisher SOFORT die vorausgewählte
  "Nein"-Option, noch bevor überhaupt eine bewusste Reaktion möglich
  war. Zusätzlicher dritter Teil des Fixes: ein OK, das innerhalb von
  350ms nach dem Öffnen ankommt UND bei dem der Nutzer vorher noch
  KEINE einzige Richtungstaste gedrückt hat, wird jetzt bewusst
  ignoriert (nur neu gezeichnet, keine Bestätigung) - eine echte,
  bewusste Richtungseingabe hebt diese Sperre sofort wieder auf, ein
  direkt danach folgendes OK bestätigt dann ganz normal ohne jede
  Verzögerung. Ebenfalls per Test verifiziert (u.a. die exakte
  Reflex-Sequenz sowie mehrere schnelle OK-Wiederholungen hintereinander).
  ZWEITER NACHTRAG (noch genauere Nutzer-Rückmeldung, hat den
  tatsächlichen Hauptverursacher entlarvt: "ich bestätige, das
  Infofenster öffnet sich, verschwindet aber wieder - drücke ich das
  Steuerkreuz nach rechts oder links, kommt es kurz wieder und man
  sieht ob Ja oder Nein hinterlegt ist, dann verschwindet es wieder
  wenn ich rechts/links drücke"): DAS war die eigentliche Ursache,
  nicht die beiden obigen Punkte. Zwei Stellen im Hintergrund-
  Zeichenpfad (next_action()) prüften bisher NICHT, ob gerade ein
  Ja/Nein-Dialog offen ist, bevor sie zeichneten: die Laufschrift für
  lange Menü-Beschriftungen (marquee_tick(), zeichnet direkt eine
  einzelne Listenzeile) und der "Cover-Nachlade"-Redraw nach
  COVER_SETTLE=150ms Stillstand (zeichnet die KOMPLETTE Seite ohne
  jeden Dialog). self._last_input_time wird bei JEDER Eingabe
  zurückgesetzt, auch innerhalb des Dialogs selbst - der 150ms-Redraw
  feuerte dadurch praktisch nach jedem Links/Rechts im Dialog und
  übermalte ihn wieder vollständig, bevor man reagieren konnte -
  exakt "ploppt auf und verschwindet wieder". Fix: beide Stellen
  pausieren jetzt, solange ein Dialog (Beenden ODER Update-
  Installieren) offen ist - für den Nutzer unsichtbar, da die
  dahinterliegende Liste während eines Dialogs ohnehin nicht sichtbar
  sein soll; nach dem Schließen läuft beides normal weiter (per Test
  verifiziert, inklusive eines direkten Belegs, dass die ungeschützten
  Originalfunktionen den Dialog tatsächlich übermalt hätten). Die
  vorherigen beiden Fixes (Hoch/Runter-Unterstützung, Hinweistext,
  Reflex-Sperre) bleiben trotzdem sinnvoll und wurden nicht wieder
  entfernt.
  Die zweite gemeldete Ursache (Absturz/Zahlensalat nach "Update jetzt
  installieren") ist noch nicht abschließend geklärt - dafür wird noch
  ein `frontend.log`-Ausschnitt vom eigentlichen Absturz benötigt.
- Gelegentliche 1-3 Sekunden lange Hänger beim Scrollen durch Spiele-
  listen spürbar reduziert (Nutzer-Rückmeldung: "das muss unter HDMI
  noch deutlich besser laufen ... da sind ab und zu ganz schöne Hänger
  drin"). Analyse einer dritten, diesmal vollständig erfolgreichen
  DRAGEND_PROFILE-Log-Datei (die ersten beiden scheiterten an einem
  eigenen Bedienungsfehler in der Mess-Anleitung - siehe unten) zeigte:
  anders als zunächst vermutet ist es NICHT die SD-Karte, die beim
  Scrollen zu Cover-Ladezeiten führt (die "kaltes Verzeichnis"-Ursache
  ist bereits behoben, siehe Artbox-Fix oben). Bei einzelnen
  Spiele-Covern lag die Zeit stattdessen an zwei anderen, ebenfalls im
  Zeichenpfad SYNCHRON laufenden Kosten, gemessen z.B. bei "Taekwon-Do
  (Korea).art" (1210ms gesamt): rund 65% reines Hochskalieren des
  Covers (eine Pixel-für-Pixel-Python-Schleife) und rund 30% das
  anschließende Wegschreiben der neu berechneten Miniatur in den
  Festplatten-Cache (inklusive `zlib.compress` und einem
  Verzeichnis-Scan für die Verdrängung) - beides blockierte bisher die
  Anzeige, obwohl das fertige Bild für den aktuellen Frame zu diesem
  Zeitpunkt schon vorlag. Zwei gezielte Fixes: (1) das
  Festplatten-Cache-Schreiben läuft jetzt in einem kurzlebigen
  Hintergrund-Thread (`_thumb_cache_put_async()` in `fe/art.py`) - das
  Ergebnis wird weiterhin garantiert bitidentisch geschrieben, blockiert
  aber die Anzeige nicht mehr; (2) die Hochskalierungs-Schleife nutzt
  jetzt dasselbe bereits bewährte Muster wie die benachbarte
  Verkleinerungs-Schleife (eine Zeile einmal herausschneiden statt bei
  jedem Pixel erneut über den ganzen Puffer zuzugreifen, sowie eine
  Listenabstraktion statt eines Generators für `b"".join()`) - laut
  eigener Differenzmessung ca. 10-15% schneller, pixel-identisch zur
  vorherigen Berechnung (eigener Test vergleicht beide Implementierungen
  Byte für Byte). EHRLICH DOKUMENTIERT: das ist eine Verbesserung des
  Konstantfaktors, kein grundlegend anderer Algorithmus - bewusst ohne
  numpy/C-Erweiterung, um keine zusätzliche Abhängigkeit für die
  Offline-Installation auf der MiSTer-SD-Karte einzuführen. Ob die
  verbleibende Restzeit beim nächsten Scrollen zu einem noch nicht
  berechneten Cover spürbar genug sinkt, muss die nächste echte
  Hardware-Messung zeigen - falls nicht, wäre der nächste sinnvolle
  Schritt ein begrenztes Vorausladen (z.B. der nächsten 1-2 Cover in
  Scrollrichtung), das aber eine größere, eigenständige Änderung wäre.
- HDMI-Ruckler beim allerersten Bildaufbau des Hauptmenüs behoben
  (Nutzer-Rückmeldung: "das muss unter HDMI insgesamt flüssiger laufen"
  - gefunden über das neue PERF-Profiling: `PERF draw_page_cats: 863
  ms`, davon allein `THUMB_CACHE Treffer: 511.6ms (CONTINUE.art)`).
  Derselbe "kaltes SD-Karten-Verzeichnis"-Effekt, der schon einmal bei
  den Cover-Ordnern behoben wurde (siehe frühere Messung "PERF cover:
  1077ms" weiter oben in diesem Changelog) - nur diesmal nicht bei
  einer Verzeichnisliste, sondern beim allerersten Lesen einer
  einzelnen Datei: das Bild für die rechte Artbox im Kategorien-Menü
  (`_draw_cat_artbox()`, z.B. `CONTINUE.art` für "Weiterspielen") wurde
  bisher NIE vorgewärmt - selbst ein an sich schneller
  Festplatten-Cache-Treffer brauchte dadurch beim allerersten Zugriff
  seit dem letzten Neustart über eine halbe Sekunde, weil die Datei
  noch nicht im Betriebssystem-Speicher lag. Fix: derselbe
  Hintergrund-Vorwärm-Thread, der schon die Cover-Ordner vorwärmt,
  lädt jetzt beim Start zusätzlich das Artbox-Bild für JEDE tatsächlich
  vorhandene Kategorie einmal vor (nicht nur für Systeme mit eigenem
  Systemkey wie bisher) - ist der Nutzer schneller als dieser
  Hintergrund-Thread, ändert sich nichts am bisherigen Verhalten.
  NACHTRAG (zweite Nachmessung auf echter Hardware zeigte weiterhin
  einen Ruckler, nur kleiner: 863ms -> 755ms statt behoben): der erste
  Versuch oben verließ sich allein auf einen Hintergrund-Thread - der
  gewann den Wettlauf mit dem allerersten `draw()`-Aufruf des
  Haupt-Threads auf echter Hardware aber nicht zuverlässig. Fix:
  für genau die beim Start zuerst sichtbare Kategorie wird die
  Artbox-Datei jetzt SYNCHRON (nicht mehr im Hintergrund-Thread)
  vorgewärmt, bevor überhaupt ein erster `draw()` möglich ist - kein
  Wettlauf mehr, garantiert warm. Alle übrigen Kategorien bleiben beim
  bisherigen, asynchronen Vorwärmen im Hintergrund (dort unkritisch,
  da der Nutzer dafür erst aktiv weiterscrollen müsste).
- Stocken beim Scrollen/Zurückgehen behoben: Navigieren innerhalb einer
  Sammlung (z.B. Game Boy) oder das Zurückgehen ins vorherige Menü
  brauchte gelegentlich mehrere Sekunden (Nutzer-Rückmeldung: "es nervt
  total wenn ich in meiner gameboy sammlung oder sonst einer sammlung
  rumscrolle und wieder auf zurück gehe das das teilweise sekunden
  braucht um in das vorherige menü wieder zu gelangen"). Direkte Folge
  des neuen Badge-Icon-Vorwärmens für F6 (siehe "Erfolgs-Vitrine (F6)"
  weiter oben unter Neue Features): das Hintergrund-Vorwärmen prüfte
  zwar VOR jedem Spiel, ob man gerade aktiv ist, dekodierte dann aber
  alle Badge-Icons eines Spiels am Stück durch, ohne zwischendurch noch
  einmal nachzusehen. Das Dekodieren selbst ist reiner, handgeschriebener
  Python-Code ohne Beschleunigung (eigene Messung: ca. 3ms pro Icon
  bereits auf schneller Hardware, auf MiSTers ARM-Kern deutlich mehr) -
  bei einem Spiel mit vielen Erfolgen (30-80 Icons) hielt das den
  Haupt-Zeichen-/Eingabe-Thread am Stück potenziell mehrere hundert
  Millisekunden bis über eine Sekunde auf, genau dann, wenn man
  zufällig mitten in diesem Fenster weiterscrollte oder zurückging.
  Fix: die Aktivitätsprüfung greift jetzt nach JEDEM einzelnen Icon,
  nicht nur vor jedem Spiel - wird man währenddessen aktiv, bricht das
  Vorwärmen für dieses eine Spiel sofort ab (die übrigen Icons holt der
  nächste echte Leerlauf nach, oder sie laden ganz normal beim
  tatsächlichen F6-Aufruf). Die Erfolgs-TEXTliste selbst bleibt davon
  unberührt, die ist ja bereits vollständig geladen, bevor die Icons
  überhaupt drankommen.
- PERFORMANCE-Regression behoben: das Frontend brauchte nach dem
  letzten Update spürbar länger zum Starten (Nutzer-Rückmeldung: "warum
  braucht das Frontend nach dem letzten Update jetzt solange zum
  starten??? das ist sehr schlecht!"). Direkte, selbst verschuldete
  Folge der neuen Arcade-Unterordner-Unterstützung: der dafür nötige
  rekursive Ordner-Scan durchsucht bei einer großen, tief organisierten
  Arcade-Sammlung (viele Unterordner, oft Tausende .mra-Dateien)
  potenziell sehr viele Verzeichnisse einzeln - und lief dabei, anders
  als die Spieleliste der übrigen Systeme (die längst einen
  ausgereiften Cache hat), bislang bei JEDEM einzelnen Start komplett
  neu von der SD-Karte. Eigene Messung: allein in einer schnellen
  Testumgebung bereits gut 20x teurer als der alte, flache Scan - auf
  echter SD-Karten-Hardware fällt der Unterschied erfahrungsgemäß noch
  deutlich stärker aus. Fix: derselbe Cache-Ansatz wie bei der übrigen
  Spieleliste (schneller Änderungs-Fingerabdruck statt jedes Mal
  neuem Scan) jetzt auch für den Arcade-Ordnerbaum - ein erneuter
  voller Scan passiert nur noch, wenn sich an der obersten Ebene von
  `_Arcade` wirklich etwas geändert hat, oder nach einem manuellen
  "Spieleliste neu einlesen". Mit einer gezielten Messung (kalt vs.
  warm vs. nach echter Änderung vs. erzwungener Neuscan) geprüft.
- Nach dem automatischen MiSTer-Neustart bei einer Update-Installation
  (siehe "Hardreset nach Update-Installation" weiter unten) blieb kurz
  die rohe Linux-Konsole ("Welcome to MiSTer ... login:") sichtbar,
  bei der man erst Enter drücken musste (Nutzer-Rückmeldung: "das
  nervt kann man das nicht umgehen?"). Das gab es bei jedem MiSTer-Boot
  eigentlich schon immer ganz am Anfang - nur löste "Update
  installieren" vorher nie einen echten Neustart aus, diese kurze
  Phase war beim Updaten also bisher nie sichtbar. `frontend_boot.sh`
  (unser Autostart-Skript) löscht die Konsolenausgabe jetzt gleich als
  allererste Aktion beim Boot aktiv, statt abzuwarten, bis das eigene
  Zeichnen das irgendwann von selbst überdeckt - kein Tastendruck mehr
  nötig.
- ABSTURZ behoben: F6 (Erfolgs-Vitrine) warf das komplette Frontend
  zurück ins MiSTer-OSD, statt die Erfolgsliste zu zeigen
  (Nutzer-Rückmeldung: "nach dem letzten Update, wenn ich jetzt ein
  Spiel auswähle und F6 drücke, flieg ich komplett aus dem Frontend
  raus und lande im OSD"). Direkte Folge der neuen Hardcore/
  Softcore-Kennzeichnung aus dem letzten Build: die Erfolgsliste
  besteht seitdem pro Zeile aus 7 statt vorher 6 Werten (neues
  "Hardcore ja/nein"-Feld) - der Bildschirm selbst wurde entsprechend
  angepasst, ABER auf der SD-Karte lag von vorherigen Sitzungen noch
  ein Zwischenspeicher (`ra_achievements_cache.json`) im ALTEN
  6-Werte-Format. Wurde beim F6-Druck auf ein bereits vorher
  angesehenes (oder automatisch im Hintergrund vorgewärmtes) Spiel
  ein solcher alter Eintrag geladen, scheiterte das Entpacken der
  Zeile mit einem Programmfehler, der nirgends abgefangen wurde -
  das Frontend beendete sich dadurch komplett, zurück blieb nur das
  MiSTer-OSD. Fix: jede aus dem Zwischenspeicher gelesene Zeile wird
  jetzt immer auf das aktuelle Format gebracht, ein fehlendes
  Hardcore-Feld wird sicher mit "nein" ergänzt - kein Absturz mehr,
  kein manuelles Löschen des Zwischenspeichers nötig. Betroffene
  Erfolge zeigen übergangsweise "[SC]" statt "[HC]", bis der ohnehin
  bestehende Hintergrund-Refresh sie mit den echten Daten
  überschreibt.
- Hardreset nach Update-Installation: nach "Jetzt installieren" im
  Update-Dialog (bzw. beim manuellen Ausführen von `Frontend_Install`
  über das Scripts-Menü) startete bisher nur der Frontend-PROZESS neu
  (frischer `python3 frontend.py`, sofort mit dem gerade installierten
  Code) - schnell, aber nicht wirklich vollständig (Nutzer-Rückmeldung/
  Einschätzung: "sollten wir nach der Installation einen Hardreset
  quasi kompletten Neustart machen lassen, damit die Änderungen auch
  definitiv übernommen sind und das Frontend einmal frisch neu
  hochfährt?"). Der reine Prozess-Neustart lädt zwar zuverlässig neuen
  Python-Code, fasst aber zwei Dinge NICHT an, die nur bei einem
  echten Boot neu geladen werden: `frontend_boot.sh` selbst (das
  Skript, das den Frontend-Prozess beim Hochfahren überhaupt erst
  startet) und die Autostart-Zeile in
  `/media/fat/linux/user-startup.sh`. Ändert ein Update genau daran
  etwas, würde der reine Prozess-Neustart das bisher stillschweigend
  nicht übernehmen - erst der nächste ECHTE Neustart hätte gegriffen.
  `Frontend_Update.sh` (gemeinsamer Endpunkt beider Installationswege)
  schließt jetzt stattdessen konsistent mit einem kompletten
  MiSTer-Neustart (`sync; reboot`) ab - dauert spürbar länger als
  vorher, garantiert dafür aber wirklich jede installierte Änderung,
  nicht nur den Python-Code. Gilt bewusst für beide Aufrufwege
  gleichermaßen (Update-Dialog im Frontend UND manueller Start über
  das Scripts-Menü), kein Sonderfall im Code.
- Leertaste wurde in der F2/"/"-Volltextsuche komplett ignoriert
  (Nutzer-Rückmeldung: "F2 Volltextsuche erkennt keine Leertaste? Wenn
  ich super mario suchen will schreibt der supermario"). Ursache: die
  Leertaste hatte schlicht noch nie eine Zuordnung in der Tastenbelegung
  (KEYMAP) - jeder Tastendruck ohne bekannte Zuordnung wird von der
  Eingabeverarbeitung stillschweigend verworfen, das Leerzeichen landete
  dadurch nie in der Suchanfrage. Jetzt behoben.
- Spieleliste (Seite 1): gehaltenes Hoch/Runter sprang beim "Turbo"
  nach kurzer Zeit über mehrere Zeilen auf einmal (Sprungweite 1 -> 2 ->
  4 -> 10), was sich sowohl als sichtbarer "Zeilensprung" bemerkbar
  machte als auch spürbar zum Laggen beitrug (Nutzer-Rückmeldung: "diese
  Zeilensprünge durch das Überspringen nach unten gedrückt halten, in
  den ROMs wenn sie angezeigt werden, sollen wegfallen - könnte das
  laggig machen?"). Bestätigt: jede Sprungweite über 1 hinaus erzwingt
  zwingend den vollen, teuren Bildschirmaufbau statt des leichten
  Zeichenpfads (siehe `_draw_navigate_items()`) - nach rund 8
  Wiederholungen einer gehaltenen Taste schaltete das Spiel dadurch bei
  praktisch jedem weiteren Schritt auf den vollen Aufbau um. Auf Seite 1
  bleibt die Sprungweite jetzt immer bei 1 - kein Zeilensprung mehr,
  und der leichte Zeichenpfad bleibt innerhalb der sichtbaren Zeilen
  durchgehend aktiv. Schnelleres Scrollen bleibt trotzdem möglich, da
  die Wiederhol-Taktrate selbst beim Halten weiterhin beschleunigt.
  Seite 0 (Kategorien-Hauptmenü) bleibt unverändert, dort wurde kein
  entsprechender Wunsch geäußert. Wichtig dazu ehrlich gesagt: sobald
  die Auswahl über das allererste sichtbare Bildschirm-Fenster hinaus
  weiterscrollt, verlangt schon das reine Verschieben des Listenfensters
  selbst (unabhängig von dieser Änderung) weiterhin den vollen Aufbau je
  Schritt - der leichte Pfad wurde bisher nur für Bewegungen INNERHALB
  des sichtbaren Fensters gebaut. Bei sehr langen Listen bleibt beim
  durchgehenden Scrollen dadurch weiterhin ein Rest-Ruckeln bestehen;
  das wäre ein separates, größeres Stück Arbeit (ein echter "Scroll"-
  Zeichenpfad).
- HDMI-Cover-Anzeige (art_hd) fiel bisher automatisch auf das SD-Cover
  zurück, sobald für ein Spiel keine passende HD-Datei existierte
  (Nutzer-Rückmeldung: "wäre es machbar, dass wenn es keine art_hd-
  Cover für den HDMI-Modus gibt, auch einfach keine angezeigt werden,
  anstatt die SD-Cover dort einzublenden? Das sieht blöd aus"). Ein auf
  HDMI-Auflösung stark hochskaliertes SD-Bild wirkt tatsächlich sichtbar
  matschig. Betroffen waren alle sechs Stellen im Code, die HD-Cover
  laden (Spieleliste, Attract-Modus, "Wonne oder Tonne", Trophäenraum,
  Jahresrückblick) - fehlt jetzt die HD-Datei, wird im HDMI-Modus
  konsequent kein Cover gezeigt (bzw. die an den meisten dieser Stellen
  bereits vorhandene "kein Artwork"-/Systembild-Platzhalteranzeige
  greift), statt des unscharfen SD-Rückfalls. Reines SD-Layout (CRT)
  bleibt komplett unverändert - dort gab es noch nie eine HD-Datei zu
  suchen.
- `Frontend_Install.sh`/`Frontend_Install_Remote.sh` gaben beim
  Ausführen einmalig die harmlose, aber verwirrende Meldung
  "shell-init: error retrieving current directory: getcwd: cannot
  access parent directories: No such file or directory" aus (per
  Screenshot von echter Hardware gemeldet - danach lief die Installation
  normal weiter). Ursache: das Skript löschte seinen eigenen, temporären
  Download-Ordner (`rm -rf "$TMP_DIR"`), während die Shell selbst noch
  genau dort stand (`cd "$TMP_DIR"` ganz am Anfang) - der direkt danach
  gestartete neue Bash-Prozess (Übergabe an `Frontend_Update.sh`) konnte
  sein Arbeitsverzeichnis dadurch nicht mehr ermitteln. Fix: vor dem
  Löschen zurück in ein garantiert weiterhin existierendes Verzeichnis
  wechseln.
- Scrollen im Kategorien-Hauptmenü konnte bei schnellem/gehaltenem
  Hoch/Runter gelegentlich ruckeln bzw. wie Zeilensprünge wirken
  (Nutzer-Rückmeldung: "im Hauptmenü wenn ich schnell scrolle macht
  das Zeilensprünge und lagt etwas"). Ursache: für die Kategorienliste
  (im Gegensatz zur Spieleliste) gab es bisher KEINEN günstigen
  Teil-Redraw-Pfad - jeder einzelne Navigationsschritt löste immer
  den kompletten Bildschirmaufbau aus (Löschen + alle sichtbaren
  Zeilen + Artbox + Statusleiste + volles Warten auf den
  Bildschirmaufbau), laut einer früheren Profiling-Runde 47-57ms auf
  HDMI - das kann sich bei gehaltener Taste mit der Eingabe-
  Wiederholrate überschneiden. Neuer, leichter Zeichenpfad
  (`_draw_navigate_cats()`, Pendant zur bereits bestehenden Lösung für
  die Spieleliste) aktualisiert bei einem einzelnen Schritt jetzt nur
  noch die betroffenen Zeilen plus die Artbox, statt der ganzen Seite.
  Zusätzlich respektiert auch der "Turbo-Sprung" bei länger gehaltener
  Taste (mehrere Zeilen auf einmal, dort bleibt der volle Aufbau
  nötig) jetzt den "Schnelles Scrollen"-Schalter beim Warten auf den
  Bildschirmaufbau, was bisher nur die Spieleliste tat. Gründlich
  gegen einen vollen Bildschirmaufbau pixel-für-pixel abgeglichen
  (CRT und HDMI, oben/mitte/unten in der Liste, mit und ohne
  System-Farbwechsel) - dabei zwei echte, kleine Bildfehler gefunden
  und behoben: der Leucht-Rand der neu markierten Zeile reichte ohne
  Korrektur minimal in die Zeile darunter hinein (bei einem
  vollständigen Neuaufbau fällt das nie auf, weil dort ohnehin jede
  Zeile neu gezeichnet wird), und die Randbereiche der Artbox nutzten
  beim Zurücksetzen eine einfarbige statt der bei aktiver
  Rand-Abdunkelung eigentlich leicht abgestuften Hintergrundfarbe.
- "Weiterspielen" und "Zuletzt gespielt" zeigten ein gerade gespieltes
  Spiel manchmal nicht an (Nutzer-Rückmeldung: "Tetris (NES RA) zB was
  ich vorhin kurz gespielt habe, zeigt er nicht"). Per Ferndiagnose
  (Nutzer hat `recently_played.json` und `frontend.log` per SSH
  ausgelesen und geteilt) zweifelsfrei geklärt: die AUFZEICHNUNG
  funktionierte die ganze Zeit korrekt - Tetris stand tatsächlich an
  erster Stelle in `recently_played.json`, und der Spielstart war auch
  im Log vermerkt. Der eigentliche Fehler lag in der ANZEIGE: die
  Menüliste (`self.cats`) wird aus Performance-Gründen NICHT bei jedem
  Spielstart komplett neu aufgebaut (das würde einen kompletten
  Scan/Cache-Check aller Spiele-Systeme anstoßen und nach jedem Spiel
  spürbar Ladezeit kosten), sondern nur beim Programmstart bzw. einem
  echten Rescan. Dadurch blieb der beim Verlassen des Spiels gezeigte
  Menüstand einfach der von VOR dem Spiel - bis zufällig irgendein
  anderer Vorgang (Rescan, Sprachwechsel, Musik-Umschalten) einen
  kompletten Neuaufbau auslöste. Neue, gezielte `_sync_recent_category()`
  aktualisiert jetzt nach JEDEM Spiel (egal ob normaler Kategorie-
  Start, Zufalls-Zock oder F11-Schnellstart - alle laufen durch
  dieselbe zentrale `run_core()`) ausschließlich "Weiterspielen" und
  "Zuletzt gespielt", ohne die teure komplette Neuscan-Logik
  anzustoßen - gleiches, bereits bewährtes Prinzip wie die bestehende
  `_sync_favorites_category()`. Mit einer eigenen Diagnose bestätigt
  (recently_played.json/frontend.log-Auszug des Nutzers als Testfall
  nachgestellt) sowie mit der vollständigen Regressionssuite
  (18/18 Kombinationen) geprüft.
- `Frontend_Install.sh` brach beim Ausführen mit `Permission denied`
  auf `/dev/null` und `syntax error near unexpected token 'done'` ab
  (Screenshot von echter Hardware). Ursache lag NICHT im Skript
  selbst, sondern in Windows-Git (MINGW64/Git Bash) - ohne eine feste
  Vorgabe im Repo entscheidet jeder Rechner per `core.autocrlf`
  eigenmächtig, ob Textdateien beim Auschecken CRLF- oder reine
  LF-Zeilenenden bekommen. Ein Shell-Skript mit CRLF-Zeilenenden ist
  auf MiSTers Linux/bash aber kaputt - ein zusätzliches CR-Byte am
  Zeilenende sprengt vor allem Zeilenfortsetzungen, genau das
  beobachtete Fehlerbild (mit einer eigenen CRLF-Simulation
  nachgestellt und bestätigt). Neue `.gitattributes`-Datei erzwingt
  jetzt für jeden, der das Repo auscheckt, reine LF-Zeilenenden bei
  `.sh`/`.py`/`.json`/`.md`/`.txt` - unabhängig von der eigenen
  Git-Konfiguration. Zusätzlich die neue WOT.art-Ausnahme (siehe
  vorheriger Eintrag) ohne Backslash-Zeilenfortsetzung umgeschrieben,
  damit sie auch ohne den `.gitattributes`-Fix robust bleibt.
- Das neue Zufalls-Zock-Bild (`sysart/WOT.art`) kam bei einer
  BESTEHENDEN Installation über Update UND Install NIE an, egal wie
  oft man es versuchte (Nutzer-Rückmeldung eines Freundes: "Nope noch
  da", nach mehrfachem Update UND Install-Lauf). Ursache gefunden:
  alle drei Install-Skripte (`Frontend_Install.sh`,
  `Frontend_Install_Remote.sh`, `Frontend_Install_Offline.sh`) kopieren
  `sysart/` bewusst mit "nicht überschreiben" - schützt eigene, per
  Hand ersetzte System-Logos vor einem Update. Existierte
  `sysart/WOT.art` aber schon (das alte Platzhalterbild lag dort schon
  lange), griff genau dieser Schutz und verhinderte JEDE Aktualisierung
  dauerhaft - unabhängig davon, wie oft die Skripte liefen. Jetzt gibt
  es eine kurze, bewusst gepflegte Ausnahmeliste (aktuell nur
  `WOT.art`), die trotzdem überschrieben wird; alle anderen
  sysart-Dateien (also echte Nutzer-Anpassungen) bleiben wie bisher
  geschützt. EHRLICH DOKUMENTIERTE EINSCHRÄNKUNG: wer `WOT.art`
  zwischenzeitlich selbst durch eigenes Artwork ersetzt hat, verliert
  das bei einem künftigen Update wieder - es gibt keinen zuverlässigen
  Weg, "noch der alte Standard" von "bewusst selbst ersetzt" zu
  unterscheiden, ohne dafür einen eigenen Fingerabdruck pro Datei zu
  speichern. Mit einer eigenen Simulation aller drei Install-Skript-
  Varianten geprüft (neues Bild kommt an, andere sysart-Dateien bleiben
  unangetastet).
- F12 (echtes MiSTer-OSD öffnen) sprang manchmal sofort wieder zurück
  ins Frontend, ohne dass der Nutzer irgendetwas gedrückt hatte
  (Nutzerfrage: "ist das normal?" - war es nicht). Ursache: `open_osd()`
  injiziert selbst ein F12-Tastenevent, damit MiSTer tatsächlich in
  sein eigenes OSD wechselt - das passiert auf derselben Geräte-
  verbindung, von der dieselbe Eingabe-Verwaltung direkt im Anschluss
  auch wieder liest. Das selbst erzeugte Event landete dadurch sofort
  wieder in der eigenen Lesewarteschlange, und weil F12 selbst bewusst
  auch als Rückkehr-Taste zählt (Sicherheitsnetz gegen dauerhaftes
  Hängenbleiben im OSD, siehe weiter oben), erfüllte es damit
  augenblicklich die eigene Abbruchbedingung. Jetzt wird die
  Eingabe-Warteschlange direkt nach dem Injizieren einmal geleert,
  bevor auf eine tatsächliche Rückkehr-Eingabe gewartet wird - eine
  echte, spätere Rückkehr-Taste bleibt davon unberührt. Mit einer
  gezielten Simulation der Selbst-Rückkopplung geprüft.
- Musik spielte nach dem Beenden über den eigenen Beenden-Dialog
  manchmal im Hintergrund weiter, hörbar auch noch zurück im MiSTer-
  OSD (Nutzer-Rückmeldung: "wenn ich das Frontend beende spielt die
  Musik weiter während ich im OSD bin"). Ursache: Lautstärke-,
  Quellen- oder Titelwechsel stoßen den eigentlichen mpg123-Neustart
  bewusst in einem Hintergrund-Thread an (damit ein hängender
  Netzwerk-Stream/eine langsame Soundeffekt-Neuerzeugung nicht die
  Eingabe blockiert) - wurde kurz vor dem Beenden noch etwas davon
  bedient, konnte dieser Thread NACH dem eigentlichen `shutdown()`
  noch einen frischen mpg123-Prozess starten, den zu dem Zeitpunkt
  niemand mehr kennt oder je wieder beendet. `shutdown()` markiert den
  Player jetzt zuerst als beendet; jeder Versuch, danach noch mpg123
  zu starten (egal aus welchem der genannten Hintergrund-Threads),
  wird an der einzigen tatsächlichen Startstelle abgefangen und läuft
  ins Leere. Mit einer gezielten Race-Simulation geprüft (Hintergrund-
  Thread trifft absichtlich unmittelbar nach `shutdown()` ein).
- Die Musik stotterte nach einem ganz normalen Neustart des Frontends
  (nicht nur nach einem Update) manchmal weiter wie "doppelt"
  (Nutzer-Rückmeldung) - der zuvor eingeführte Aufräum-Schritt für
  verwaiste mpg123-Prozesse (siehe unten) schickte bisher nur SIGTERM
  und kehrte sofort zurück, ohne abzuwarten, ob der Alt-Prozess das
  Signal überhaupt schon verarbeitet hatte - kurzes Überlappungs-
  fenster zwischen sterbendem Alt-Prozess und frisch gestartetem
  neuen. Wartet jetzt bis zu ~1s auf das tatsächliche Prozessende
  (erkennt dabei auch einen "Zombie"-Zwischenzustand korrekt als
  bereits beendet, statt unnötig die volle Wartezeit auszureizen) und
  erzwingt danach nötigenfalls SIGKILL. Mit zwei gezielten Tests
  geprüft (normaler Prozess und ein absichtlich SIGTERM-resistenter,
  um die SIGKILL-Eskalation selbst zu überprüfen).
- Nach einem Update blieb das Frontend ganz selten (Nutzer-
  Rückmeldung: "passiert nicht oft aber ab und zu") an der rohen
  Linux-Konsole/Login-Aufforderung hängen, statt zu starten - der
  Bildschirm zeigte nur noch "Welcome to MiSTer ... login:", nichts
  reagierte mehr. Ursache: `Frontend_Update.sh` (und `Frontend_Start.sh`)
  ersetzten die eigene Shell bisher bedingungslos per `exec` durch den
  neuen Python-Prozess - scheiterte der (z.B. durch eine seltene, kurze
  Race unmittelbar nach dem Beenden der alten Instanz, ähnliche
  Fehlerkategorie wie der bereits in `frontend_boot.sh` behobene "1 von
  10 startet nicht richtig"-Bug beim normalen Hochfahren, nur bisher
  ohne dessen Sicherheitsnetz), gab es danach überhaupt keinen Prozess
  mehr, der irgendetwas auf den Bildschirm hätte zeichnen können - und
  keinerlei sichtbaren Hinweis, dass etwas schiefgelaufen ist. Jetzt:
  kein `exec` mehr, echter überwachter Start mit automatischem
  Neuversuch, falls der Prozess sofort (innerhalb von 3 Sekunden)
  wieder beendet ist, und einer klar sichtbaren Fehlermeldung samt
  Log-Hinweis, falls selbst der zweite Versuch scheitert - statt einer
  stillen, leeren Konsole. Mit einer eigenen Simulation aller drei
  Fälle geprüft (Absturz-dann-Erfolg, Dauerabsturz, normaler Lauf ohne
  Neuversuch).
- Hilfe/Übersicht (System -> Info) auf den aktuellen Stand gebracht
  (Nutzer-Rückmeldung: "es fehlen einige Tasten") - erneut gegen die
  tatsächliche Tastenbelegung geprüft, ergänzt: "/"/F2 (Volltextsuche
  in der Spieleliste), Select allein am Pad (macht dasselbe wie
  Zurück/B) sowie F5 als Reset-Taste während ein Core läuft. Dabei
  aufgefallen und korrigiert: "Y: nächster Musiktitel" stand bisher
  unter "Während des Spielens", funktioniert technisch aber nur beim
  Bedienen des Menüs selbst (MiSTer sperrt die normale Tastenebene
  während ein Core läuft exklusiv) - jetzt unter "Überall" geführt,
  mit F5 als zweiter, gleichwertiger Taste dafür (im Menü - nicht zu
  verwechseln mit F5 als Reset-Taste während des Spielens, zwei
  unterschiedliche Kontexte, dieselbe physische Taste).
- Zufalls-Zock-Logo ausgetauscht (Nutzer-Vorlage) und dabei einen
  stillen, bestehenden Bug behoben: der Code suchte bereits nach
  `zufalls_zock.art`, die mitgelieferte Bilddatei hieß aber noch
  `wonne_oder_tonne.art` (Rest einer alten Umbenennung) - das eigene
  Logo wurde dadurch nie gefunden, angezeigt wurde unbemerkt nur der
  reine Text-Titel als Rückfall. Datei jetzt unter dem richtigen
  Namen, alte Datei entfernt.
- Update-Infobox (mittige Meldung "Update vX.Y!"/"Neu: ...") war im
  CRT-Modus teils riesig und zeigte scheinbar nichts an (Nutzer-
  Rückmeldung). Ursache: die Box wurde bisher ausschließlich aus der
  vollen Zeichenlänge des Textes berechnet, ganz ohne Rücksicht auf
  die verfügbare Bildschirmbreite. Beim kurzen Versions-Hinweis fällt
  das nicht auf, aber der "Neue Fixes"-Hinweis zeigt den frei
  formulierten `LATEST_BUILD.json`-Text - der kann ein ganzer, längerer
  Satz sein. Auf CRT (320px breit) sprengte das die Box um ein
  Vielfaches, die Box landete dadurch (rechnerisch stark negative
  Startposition) praktisch komplett außerhalb des sichtbaren Bereichs.
  Jetzt wie beim Beenden-Dialog wortweise umgebrochen und auf maximal
  3 Zeilen begrenzt - passt garantiert auf jede Auflösung.
- Nach einem Neustart des Frontends setzte die Musik gelegentlich
  aus/stotterte, "als würde da was doppelt laufen" (Nutzer-
  Rückmeldung) - und genau das war es auch: überlebte der `mpg123`-
  Kindprozess der VORHERIGEN Instanz einen nicht ganz sauberen
  Neustart (z.B. weil `/tmp` - und damit dessen PID - einen Soft-Reset
  überlebt, siehe der ähnliche Fall bei der Sperrdatei in
  `single_instance.py`), wusste die NEUE Instanz nichts davon und
  startete einfach ihren eigenen zweiten `mpg123` dazu - zwei
  Musikstreams gleichzeitig auf derselben Audioausgabe. Alle
  bisherigen mpg123-Überlagerungs-Fixes (Prozess-Sperre, Jingle-
  Zähler) deckten nur Fälle INNERHALB einer laufenden Instanz ab,
  nicht einen Rest aus einer vorherigen. Jetzt räumt `MusicPlayer` beim
  eigenen Start einmalig über `/proc` jeden noch laufenden `mpg123`-
  Prozess weg, bevor es selbst einen neuen startet (mpg123 wird auf
  dem MiSTer ausschließlich vom Frontend selbst genutzt, ein Abschuss
  kann also nichts Fremdes treffen).
- Boxart-Download (`mister_boxart.py`) überarbeitet (Nutzer-Vorlage:
  ein selbst geprüfter, vertrauenswürdiger Mirror mit bereits fertigen
  .art-Dateien - übernommen, aber bewusst nicht 1:1, drei Korrekturen
  gegenüber der Vorlage):
  - Der Mirror läuft jetzt als schneller Hauptweg (kein Dekodieren
    mehr auf dem MiSTer selbst nötig), mit automatischem Rückfall auf
    den bisherigen Weg (thumbnails.libretro.com, Fallback GitHub) für
    alles, was der Mirror gerade nicht liefert - kein Alles-oder-
    nichts, falls der Mirror mal nicht erreichbar ist.
  - Regions-Priorität bewusst NICHT auf die in der Vorlage verwendete
    alte Reihenfolge zurückgestellt, sondern bei der bereits vorher
    aus echter Nutzer-Rückmeldung korrigierten Reihenfolge (USA/World
    zuerst) belassen - sonst wäre der schon behobene Bug (Europa-Cover
    für USA-Sammlungen) wieder aufgetaucht.
  - Zusätzlich ein tatsächlicher, bisher unbemerkter Bug gefunden und
    behoben: Game-Gear-ROMs (`.gg`) wurden bei der Cover-Suche gegen
    die Master-System-Datenbank abgeglichen statt gegen die eigene
    Game-Gear-Datenbank - praktisch nie ein Treffer. ROMs und fertige
    .art-Dateien bleiben weiter zusammen im gemeinsamen "SMS"-Ordner
    (so wie das Frontend selbst danach sucht, siehe `fe/systems.py`),
    nur die Cover-QUELLE wird jetzt intern je nach Dateiendung
    getrennt nachgeschlagen.
  - Die zusätzlichen Systeme aus der Vorlage (u.a. Atari-Familie, C64,
    Amiga, ScummVM) wurden bewusst NICHT übernommen: das Frontend
    zeigt aktuell nur die 13 Systeme aus `GAME_SYSTEMS` als eigene
    Kategorie an, für alles Weitere gäbe es nirgends eine Anzeige für
    die geladenen Cover - wäre nur unnötig belegter SD-Kartenplatz.
- Geheime Codes/Erfolgs-Popups überlagerten sich hörbar mit sich selbst
  und mit der laufenden Musik ("Sound kommt, aber MP3/Radio pausiert
  nicht dabei, es kommt zur Überlagerung und fängt das Stottern an" -
  Nutzer-Rückmeldung). Zwei Ursachen, beide in `_play_ducked_sfx()`
  bzw. an dessen Aufrufstellen:
  - Bei einer Erst-Freischaltung (neuer Geheimcode/Erfolg) lief
    zusätzlich zum neuen, sauber gedämpften `_play_ducked_sfx(
    "achievement")` noch ein alter, direkter `play_sfx("achievement",
    ...)`-Aufruf mit - ein reines Überbleibsel aus der Zeit vor der
    Dämpfungs-Funktion, das denselben Ton kommentarlos ein zweites Mal
    (unabhängig von ihr) abspielte. Entfernt.
  - Löst ein Geheimcode ZWEI Töne kurz hintereinander aus (den
    allgemeinen Erfolgston direkt gefolgt vom eigenen Theme-/Raum-/
    Chiptune-Ton, z.B. bei einem neuen geheimen Theme), lief jeder
    Aufruf bisher in einem komplett eigenständigen Hintergrund-Thread -
    beide Töne konnten dadurch teilweise GLEICHZEITIG auf derselben
    Audioausgabe landen (das eigentliche Stottern), und der zuerst
    fertige Thread startete die Musik bereits wieder, während der
    zweite Ton noch lief. Jetzt über einen Zähler statt eines einzelnen
    Ein/Aus-Flags koordiniert: nur der erste einer solchen "Salve" hält
    die Musik an, nur der letzte startet sie wieder, und die
    eigentlichen Sound-Dateien spielen dabei garantiert sauber
    nacheinander statt sich zu überlagern.
- "Weiterspielen" und "Zuletzt gespielt" funktionierten nicht sauber
  (Nutzer-Rückmeldung, zwei Ursachen gefunden und behoben):
  - Die Liste war auf 15 Einträge gedeckelt - bei etwas aktiverer
    Nutzung fielen ältere Spiele dadurch schon nach relativ kurzer Zeit
    stillschweigend wieder heraus, ohne dass das irgendwo sichtbar
    gewesen wäre. Jetzt 100 Einträge.
  - Die Duplikat-Erkennung beim Einreihen verglich bisher NUR den
    Anzeigenamen: zwei gleichnamige Spiele auf UNTERSCHIEDLICHEN
    Systemen (z.B. "Sonic the Hedgehog" auf Mega Drive UND Master
    System) galten dadurch fälschlich als dasselbe Spiel - startete man
    das eine, verschwand der Eintrag des anderen ersatzlos aus der
    Liste. Jetzt zählt zusätzlich das jeweilige System mit; nur
    wirklich dasselbe Spiel auf demselben System wird noch nach oben
    verschoben statt doppelt zu erscheinen.
  - Zusätzlich (Nutzerwunsch: "richtig unterscheiden, welcher Core
    geladen war"): der Core-Auswahlbildschirm, der beim Start aus
    Weiterspielen/Zuletzt gespielt/Favoriten weiterhin für JEDES Spiel
    erneut erscheint (bewusst keine stille Automatik, siehe
    Kommentar in `draw_core_choice_screen()`), stand bisher unabhängig
    von der Spielhistorie immer auf "normaler Core" - wer aus
    Gewohnheit schnell bestätigte, landete dadurch leicht im falschen
    Core, ohne dass RA-Fortschritt erfasst wurde. Die Vorauswahl
    richtet sich jetzt danach, mit welchem Core genau dieses Spiel
    zuletzt tatsächlich gestartet wurde - Bestätigen übernimmt dann
    automatisch wieder den richtigen Core, eine bewusste Umentscheidung
    bleibt weiterhin jederzeit möglich.
- Nach "MiSTer-Menü öffnen" (F12) blieb man auf manchen Pad-Belegungen
  dauerhaft im echten MiSTer-OSD gefangen - selbst `start_frontend.sh`
  half dann nicht, sondern meldete nur "Frontend läuft bereits", weil
  der Prozess tatsächlich weiterlief, nur eben in genau dieser
  Warteschleife feststeckte (die bislang ausschließlich auf Taste F10
  oder Pad-Button X reagierte). Die Schleife akzeptiert jetzt zusätzlich
  drei weitere, unabhängige Wege zurück (ESC, der Standard-"Zurück"-
  Button sowie nochmaliges Drücken von MiSTer-Menü/F12 als Umschalter),
  und "Zurück ins Frontend" lässt sich über den Tastenbelegungs-
  Assistenten jetzt zusätzlich auch auf eine ganz eigene Taste legen.
- CIFS/NAS-eingehängte Spiele wurden nie gefunden, selbst wenn die
  Einhängung einwandfrei lief: `/media/fat/cifs` (der von MiSTer
  typischerweise genutzte Netzlaufwerk-Pfad) wurde beim Durchsuchen
  der Spiele-Ordner schlicht nie erreicht, weil die Suche "fat"
  komplett überspringt (die SD-Karte selbst ist ja schon separat
  abgedeckt) - `/media/fat/cifs` liegt aber eine Ebene *unterhalb*
  davon und wurde dadurch nie mit erfasst. Jetzt zusätzlich gezielt
  durchsucht (der Pfad selbst, ein `games`-Unterordner sowie alle
  direkten Unterordner einzelner Freigaben). Zusätzlich: die "beim
  Start auf Netzwerk/NAS warten"-Option muss nicht mehr von Hand
  gesetzt werden, sobald `user-startup.sh` bereits ein CIFS-Mount-
  Skript enthält (automatisch erkannt, per Menü weiterhin übersteuerbar)
  - und unabhängig von dieser Option prüft das Frontend während der
  ersten paar Minuten nach dem Start ohnehin periodisch im Hintergrund,
  ob inzwischen ein neues Netzlaufwerk aufgetaucht ist, und zieht die
  Spieleliste dann automatisch einmal nach, statt sich auf eine einzige
  starre Wartezeit beim Booten zu verlassen.
- Die Dateinamen unter `Scripts/` waren uneinheitlich gewachsen
  (`install.sh`, `install_frontend.sh`, `start_frontend.sh`,
  `stream_toggle.sh` usw.) und dadurch im MiSTer-OSD zwischen fremden
  Skripten kaum wiederzufinden. Vorher geprüft, ob MiSTers Scripts-Menü
  eigene Unterordner sauber darstellt (technisch ja, beliebig
  verschachtelbar) - dagegen entschieden, weil ein Unterordner im OSD
  einen zusätzlichen Klick kostet und die etablierte Community-Praxis
  (z.B. Update All, MiSTerMAME) stattdessen auf ein gemeinsames,
  sprechendes Präfix setzt. Alle 9 eigenen Skripte tragen jetzt
  einheitlich das Präfix `Frontend_` (`Frontend_Install.sh`,
  `Frontend_Install_Remote.sh`, `Frontend_Install_Offline.sh`,
  `Frontend_Uninstall.sh`, `Frontend_Start.sh`, `Frontend_Update.sh`,
  `Frontend_Stream_Toggle.sh`, `Frontend_Boxart_Download.sh`,
  `Frontend_Gameinfo_Download.sh`) und stehen im OSD dadurch alphabetisch
  zusammen; `Scripts/MiSTer_RA.sh` bleibt bewusst unangetastet, da es
  sich um ein fremdes Drittanbieter-Tool handelt. Migration läuft
  automatisch mit: ein bereits auf der SD-Karte liegendes altes
  `install_frontend.sh` funktioniert noch genau ein letztes Mal (der
  bisherige `update_frontend.sh`-Aufruf bleibt dafür unter seinem alten
  Namen als reine Weiterleitung erhalten), und `Frontend_Update.sh`
  räumt bei jedem folgenden Install/Update automatisch sämtliche 9 alten
  Dateinamen von selbst auf - kein manueller Eingriff nötig.
- Mehrere verbliebene ASCII-Umlaut-Ersatzschreibweisen in der
  Oberfläche korrigiert (u.a. Trophäenraum, Jahresrückblick).
- `Scripts/install.sh`, `Scripts/install_offline.sh` und
  `Scripts/uninstall.sh` liefen den Hauptdateien im Wurzelverzeichnis
  hinterher (u.a. fehlte der komplette `fe/`-Modulordner-Fix, der
  ursprünglich ein reales Installationsproblem gelöst hatte) - jetzt
  synchronisiert, plus eine neue GitHub Action, die bei jedem Push
  automatisch prüft, ob beide Seiten noch übereinstimmen.
- `FRONTEND_VERSION` war zweimal unabhängig als Zeichenkette
  hinterlegt (`frontend.py` und `fe/menu.py`) - dieselbe Drift-Gefahr
  wie bei den Scripts-Kopien. Jetzt eine einzige, kanonische Quelle.
- Englische README war bei "v3.2" stehengeblieben, während die
  deutsche schon bei v4.3 war - beide jetzt synchron.
- "Neue Version verfügbar"-Hinweis war nur ein kleines,
  2-Sekunden-Fußzeilen-Popup und wurde dadurch praktisch nie bemerkt -
  zeigt jetzt wie der "Neue Fixes"-Hinweis eine große Infobox. War im
  ersten Anlauf noch an denselben Leerlauf-Schwellenwert wie der
  Attract-Modus gekoppelt (Update-Check startete erst nach etlichen
  Sekunden Leerlauf) - startet jetzt sofort, sobald das Hauptmenü
  sichtbar ist, und bleibt 2-3 Sekunden stehen (statt der 5s des
  "Neue Fixes"-Hinweises).
- Nach Bestätigen oder Abbrechen der Volltextsuche (F2/"/") blieb der
  farbige Suchbalken oben im Bild als Leiche stehen, statt richtig zu
  verschwinden - der HDMI-Performance-Schnellpfad in
  `_draw_page_items_impl()` erkannte nicht, dass der Balken den Puffer
  außerhalb seiner eigenen Buchführung verändert hatte, und übersprang
  deshalb fälschlich den nötigen vollen Neuaufbau. Der Suchbalken
  zählt jetzt bei jedem eigenen Zeichnen `full_redraw_gen` mit hoch,
  wodurch der Schnellpfad direkt danach zuverlässig einmal den echten,
  sauberen Neuaufbau erzwingt.
- Geheimcode für den Entwicklerraum reagierte nicht auf deutschen
  Tastaturen: Das Frontend liest rohe Tastatur-Scancodes direkt aus
  `/dev/input`, ganz ohne Tastaturlayout-Umrechnung - die bedruckte
  Y-Taste löste dadurch "letter:Z" aus, nicht "letter:Y" ("Y" und "Z"
  sind die einzigen beiden Buchstaben, die zwischen QWERTY- und
  QWERTZ-Layout die Position tauschen). Da dieses Projekt durchgehend
  auf deutsche Nutzer ausgelegt ist, jetzt direkt an der Quelle
  behoben statt layoutneutral ausgewichen: `LETTER_KEYS` in
  `fe/input.py` ordnet Y/Z jetzt so zu, wie sie auf einer deutschen
  Tastatur tatsächlich beschriftet sind - betrifft nicht nur den
  Geheimcode, sondern auch den ganz normalen Buchstaben-Direktsprung
  (A-Z-Taste drücken, zum nächsten Eintrag mit diesem Buchstaben
  springen), der beim Buchstaben Y/Z bisher ebenso falsch sprang.
- Bonus-Geheimcode im Entwicklerraum ("Geheimnis im Geheimnis") ließ
  sich nicht eingeben - der Bildschirm zeichnete sich beim Betreten
  zunächst einmal und wartete auf eine erste, komplett verworfene
  Taste ("nur zum Bestätigen"), bevor die eigentliche Code-Erkennung
  überhaupt zu lauschen begann. Genau dieser erste Tastendruck war
  aber bereits das "E" des Codes - er verschwand spurlos, die
  Erkennung sah nur noch "G" als vermeintlich ersten Buchstaben und
  verließ den Raum sofort wieder. Der doppelte Zeichnen-und-Warten-
  Schritt entfällt jetzt komplett; der allererste Tastendruck nach dem
  Betreten zählt von Anfang an für den Bonus-Code.
- Entwicklerraum auf CRT (320×240) nicht mehr lesbar: längere Zeilen
  (Mitwirkende, Danksagung) liefen bisher ungewrappt durch und wurden
  am Bildschirmrand einfach abgeschnitten statt umgebrochen. Laufen
  jetzt wie die übrigen Info-Bildschirme durch echten Zeilenumbruch;
  die dadurch zusätzlich nötigen Zeilen bekommen ihren Platz über eine
  automatisch kompaktere Zeilenhöhe, die sich am tatsächlich
  benötigten Platz orientiert (auf HDMI mit reichlich Platz bleibt das
  Layout unverändert) - dadurch bleibt garantiert alles sichtbar,
  unabhängig von Sprache oder Textlänge.
- "Neue Fixes verfügbar"-Hinweis erschien trotz zahlreicher echter
  Änderungen nicht mehr: dieser Hinweis vergleicht bewusst NICHT die
  Versionsnummer (die bleibt laut Wunsch stabil bei v4.4), sondern eine
  eigene, separate Kennung in `frontend/LATEST_BUILD.json` auf GitHub -
  genau diese Kennung wurde beim letzten Fix-Batch nicht mit
  hochgezählt, das eigene Gerät hatte den (unveränderten) Stand
  dadurch schon als "gesehen" gespeichert. Kennung jetzt aktualisiert;
  wird ab sofort bei jedem nennenswerten Fix-Batch mit hochgezählt.
- Freigeschaltete geheime Themes erschienen im Menü System → Anzeige
  unter "Farbschema" nicht mit ihrem echten Namen, sondern entweder mit
  der alten "Dunkel (Standard)"-Beschriftung oder einem bloßen "?" -
  die Theme-Namenslisten in `fe/menu.py` waren beim Hinzufügen der 9
  neuen geheimen Themes nicht mit aktualisiert worden (dieses Modul
  führt bewusst eine eigene, unabhängige Kopie der Theme-Konstanten,
  um `frontend.py` nicht importieren zu müssen). Beide Listen sind
  jetzt synchron; alle 9 neuen Themes zeigen ihren echten Namen und
  lassen sich über "Farbschema wechseln" wie gewohnt anwählen, sobald
  sie einmal per Geheimcode freigeschaltet wurden.
- "RA-Erfolgsjäger" erschien auf der Hauptseite manchmal gar nicht und
  tauchte erst nach irgendeiner unabhängigen Aktion (z. B. eine
  Einstellung ändern) plötzlich doch auf: Der Hintergrund-Abruf der
  RetroAchievements-Fortschrittsdaten aktualisierte zwar den internen
  Datenspeicher, stieß aber nur unter einer sehr engen Bedingung
  ("Nutzer steht exakt auf der allerersten Kategorie, hat noch gar
  nichts angeklickt") einen Neuaufbau der Kategorienliste an - im
  Alltag praktisch nie erfüllt. Der Wiederholungsabruf bei
  fehlgeschlagenem erstem Versuch löste sogar überhaupt nie einen
  Neuaufbau aus. Jetzt setzt jeder erfolgreiche Datenabruf (egal ob
  beim ersten Versuch oder bei einem späteren Wiederholungsversuch)
  nur noch ein "schmutzig"-Merkmal; ein neuer, sicherer Mechanismus
  baut die Kategorienliste zuverlässig neu auf, sobald man als
  Nächstes auf der Kategorien-Übersicht steht - unabhängig davon, wo
  man sich in der Zwischenzeit im Menü bewegt hat, und ohne dabei die
  aktuell markierte Kategorie zu verlieren.
- "RA-Erfolgsjäger" zeigte in der Boxart-Spalte bisher nur den
  generischen "kein Artwork"-Platzhalter. Neues, eigens erstelltes
  Pokal-Motiv (mit einem kleinen Controller-Emblem, bewusst kein
  Nachbau des echten RetroAchievements-Markenlogos) unter
  `frontend/sysart/RA_HUNTER.art` ergänzt und `_category_art_key()` in
  `fe/art.py` um den passenden Schlüssel erweitert - die Kategorie
  bekommt jetzt wie "Favoriten"/"Sammlungen" ein eigenes Logo neben der
  Liste, sowohl auf CRT als auch auf HDMI.
- Installierte Fixes/Updates wirkten nach `Scripts/install_frontend.sh`
  scheinbar nicht, obwohl auf der SD-Karte längst alles aktuell war
  (genau daran zeigte sich der obige RA-Erfolgsjäger-Fix beim ersten
  Nutzertest): das Skript kopierte bisher nur die neuen Dateien, ohne
  den bereits laufenden Frontend-Prozess zu beenden - der hatte seinen
  alten Code aber schon im Speicher, liest ihn nie von selbst neu ein.
  Wurde `install_frontend` aus dem Frontend-Menü selbst heraus
  gestartet (System → Scripts), landete man über `back_to_frontend()`
  einfach wieder in genau dieser alten, unveränderten Instanz - ohne
  einen kompletten manuellen MiSTer-Neustart blieb jede frisch
  installierte Änderung bis zum nächsten Booten unsichtbar. Das Skript
  startet den Frontend-Prozess jetzt am Ende selbst automatisch neu
  (über das bereits vorhandene, dafür gebaute `update_frontend.sh`) -
  weder beim Erstinstall noch bei einem späteren erneuten Ausführen
  ist danach noch ein manueller Neustart nötig.
- Drei Geheimnisse blieben beim Freischalten komplett stumm: das
  goldene Geheim-Theme, der Entwicklerraum und der Bonus-Code im
  Entwicklerraum ("Geheimnis im Geheimnis") riefen bisher überhaupt
  keine Sound-Funktion auf, obwohl der generische Mechanismus dafür
  (`_play_ducked_sfx()` - Musik kurz pausieren, Sound abspielen, danach
  automatisch fortsetzen, falls sie an war) längst existierte und für
  die 9 Konsolen-Themes bereits genutzt wurde. Alle drei rufen diesen
  Mechanismus jetzt ebenfalls auf; der Bonus-Code bekam dabei zusätzlich
  einen eigenen Sound-Namen statt weiterhin den generischen
  "Erfolg freigeschaltet"-Ton mitzubenutzen.

**Neue Features:**
- Jedes Geheimnis und jedes der 9 geheimen Themes hat jetzt einen
  eigenen, echten Sound-Jingle statt eines synthetisch erzeugten
  Ersatztons: 14 MP3-Dateien liegen unter `frontend/sfx/` (nur
  Regenbogen-Cursor bleibt bewusst stumm, rein visueller Effekt).
  Wird ein Code eingegeben, pausiert eine eventuell laufende Musik kurz,
  der zugehörige Sound spielt ab, danach läuft die Musik automatisch
  weiter, falls sie an war (`_play_ducked_sfx()`, unverändert
  wiederverwendet). Fehlt eine MP3 auf einem Gerät (z. B. bei eigenen
  Anpassungen), springt weiterhin der bisherige synthetische Ersatzton
  ein statt komplett stumm zu bleiben. `Scripts/install.sh`,
  `Scripts/install_frontend.sh` und `Scripts/install_offline.sh` kopieren
  `frontend/sfx/` jetzt beim (Erst-)Install/Update automatisch mit
  (gleiches "nicht überschreiben"-Prinzip wie bei `sysart/`/
  `sfx_source/`, eigene Sound-Dateien mit demselben Namen bleiben
  erhalten).

**Dokumentation:**
- `docs/Dragend_Anleitung.pdf` aktualisiert: F2 als zweite Suche-Taste
  ergänzt, die Doppelbelegung von F5 (kurz im Menü = Musik, gehalten im
  Spiel = Reset) klargestellt, und die bisher komplett leere
  JOYPAD-Seite mit den tatsächlichen Pad-Belegungen gefüllt.
- "Geheimcodes - Hinweise" (öffentliches, spoilerarmes Hinweisblatt zu
  allen Geheimnissen) neu in zwei Dateien aufgeteilt: Der bisherige
  konkrete Google-Suchbegriff je Geheimnis ("Rechercheansatz") wurde aus
  dem Hauptdokument entfernt und steht jetzt nur noch separat im neuen,
  klar als Abkürzung gekennzeichneten Zusatzblatt "Geheimcodes -
  Recherche" - wer selbst recherchieren will, wird durch das
  Hauptdokument allein nicht mehr vorzeitig gespoilert.

## v4.3 — großes Sammel-Release (staging → main)

Alles, was sich seit v4.2 angesammelt hat, jetzt offiziell gebündelt.
Ausführlich als `v4.3-alpha1` getestet, bevor es hierher gemergt wurde.

**Neue Features:**
- Rainwave-Internetradio als zweite Musikquelle neben MP3
- Lautstärke-Regler für Musik und Menü-Sounds gemeinsam
- Ersteinrichtungs-Assistent (8 Schritte, automatisch beim ersten
  Start, jederzeit über System → Info erneut aufrufbar)
- SNES Tracker als optionale Kategorie (nur sichtbar, wenn der Core
  tatsächlich installiert ist) und SMW Hacks als eigene Kategorie
- GitHub-Update-Benachrichtigung, asynchroner RA-Fortschritts-Abruf
- Mehr versteckte Erfolge, Jubiläums-Hinweise, saisonale
  Dekorationen, weitere Ostereier
- "Wonne oder Tonne" (Dennsens Bewertungs-Format): zieht ein
  zufälliges, noch nicht bewertetes NES/SNES-Spiel, mit korrekter
  RetroAchievements-Core-Abfrage beim Start
- Echter, selbst gewählter Sound für Erfolge und Popup-Benachrichtigungen
- `FRONTEND_VERSION`-Konstante und `VERSION`-Datei als zusätzliche,
  verbindliche Versions-Quellen

**Bugfixes:**
- (Unl)/(Pirate)-getaggte ROMs wurden fälschlich als Junk gefiltert
- Veralteter Scan-Cache überlebte Änderungen an der Filterlogik
- Doppelter Radio-Stream durch eine Wettlaufsituation beim
  Lautstärke-Wechsel
- Kuratierte Liste erkannte Namenskonventions-Unterschiede nicht
  (Artikel-Stellung, "&" vs. "and")
- Uhrzeit blieb bei fehlgeschlagener Erst-Synchronisierung dauerhaft
  falsch, wenn kein RetroAchievements eingerichtet war
- Update- und Jubiläums-Hinweis wurden vom Attract-Modus lautlos
  verschluckt
- Scripts aus dem Frontend liefen ohne steuerndes Terminal (setsid +
  TIOCSCTTY), interaktive dialog-Scripts scheiterten dadurch
- Boxart-Download über beide Kerne parallelisiert (spürbar schneller)

## v4.2 — Bugfix: Uhrzeit blieb bei manchen Nutzern dauerhaft falsch
Der bisherige Neuversuch für eine beim Start fehlgeschlagene
Zeit-Synchronisierung lief nur über den RetroAchievements-Mechanismus
— Nutzer ohne eingerichtetes RA hatten dadurch überhaupt keine
Wiederholung. Schlug der allererste, im Hintergrund laufende Versuch
beim Programmstart fehl (z. B. weil das Netzwerk noch nicht bereit
war), blieb die Uhr für die ganze Sitzung falsch, egal welcher
Zeitzonen-Versatz eingestellt war. Neuer, von RA komplett
unabhängiger Wiederholungsmechanismus behebt das.

## v4.1 — Neues Feature: Lautstärke-Regler
Übernommen aus einem separat vorbereiteten, auf echter Hardware
getesteten Vorschlag von TheRealSutefan. Regler für Musik und
Menü-Sounds gemeinsam (0/20/40/60/80/100%), neuer Menüpunkt
"Lautstärke: X%" in "Anzeige & Sound". Musik läuft über mpg123 und
bekommt den eingebauten Lautstärke-Faktor (gilt für MP3 UND
Rainwave-Radio). Menü-Sounds sind selbst erzeugte WAVs ohne eigenen
Lautstärke-Schalter — die Lautstärke steckt dort in der Amplitude der
Datei selbst, die bei einer Änderung neu erzeugt wird. Läuft im
Hintergrund, damit das Menü dabei nicht einfriert.

## v4.0 — mehrere Änderungen aus einer weiteren Sammel-Rückmeldung
- F11 ("Zufallssprung") startet jetzt tatsächlich ein zufälliges
  Spiel über alle Systeme hinweg, statt nur die Auswahl zu bewegen —
  inklusive RA-Core-Abfrage, falls zutreffend.
- Core-Auswahl-Titel und die Kopfzeile in der Spieleliste schneiden
  auf CRT nicht mehr ab, sondern verkleinern sich bei Bedarf.
- Neue einstellbare Attract-Modus-Verzögerung (30s bis 15min statt
  fest auf 90 Sekunden).
- System-Menü umsortiert: Musik-Einträge jetzt unter "Anzeige &
  Sound", CRT-Testbild jetzt unter dem umbenannten "Optionen"-Ordner
  (vorher "Verhalten").
- Scripts aus dem Frontend liefen ohne Wechsel in MiSTers
  Konsolenmodus — behoben.

## v3.9 — mehrere Bugfixes aus einer Sammel-Rückmeldung
- Spiele außerhalb von `/media/fat/games` (Netzlaufwerke, USB-Nummern
  über 5) werden jetzt zusätzlich dynamisch erkannt statt nur der
  festen Liste usb0–5.
- ROM-Hacks (und ähnlich getaggte Randomizer-Ausgaben) werden nicht
  mehr als "Junk" ausgefiltert.
- Mehrere Regionsversionen desselben Spiels (PAL/NTSC/etc.) bleiben
  jetzt alle erhalten und wählbar, statt nur die "beste" Region zu
  behalten.
- F10 zum Verlassen eines Spiels funktioniert jetzt zuverlässig über
  denselben HID-Weg wie Esc (lief vorher über die während des
  Spielens gesperrte normale Ebene).
- Geklärt: F11 ("Zufallssprung") startet nichts von selbst, bewegt
  nur die Auswahl — kein Bug.
- Neue `boxart_download.sh` mit interaktiver Profilauswahl übernommen.

## v3.8 — Neues Feature: Rainwave-Internetradio
Zweite Musikquelle neben den lokalen MP3s, übernommen aus einem
separat vorbereiteten, auf echter MiSTer-Hardware getesteten
Vorschlag. Neues eigenständiges Modul `frontend/rainwave.py` (reines
stdlib) spielt einen von fünf Rainwave-Sendern (Game, OCReMix,
Covers, Chiptune, All) über mpg123 ab und holt den aktuellen Titel
anonym über die öffentliche Rainwave-Schnittstelle. Neuer Menüpunkt
"Musik-Quelle" schaltet durch: MP3 → Radio (alle 5 Sender) → zurück
zu MP3. Der Titel fließt automatisch ins bestehende Stream-Overlay.
Zusätzlich abgesichert: fehlt `rainwave.py` doch mal, bleibt die
normale MP3-Wiedergabe unverändert nutzbar statt abzustürzen.

## v3.7 — Diagnose-Version Teil 2, immer noch kein Fix
Der v3.6-Diagnoseansatz hatte selbst einen Fehler: das Log-Budget war
über alle drei Schnittstellen gemeinsam begrenzt. Eine "geschwätzige"
Schnittstelle (periodisches Status-Signal, sieht nicht nach echten
Tastendrücken aus) hat dadurch alle 30 Log-Zeilen belegt, bevor die
anderen beiden Schnittstellen überhaupt einmal zu Wort kamen. Fix:
eigenes Budget pro Schnittstelle - jede bekommt jetzt garantiert
eigene Log-Zeilen.

## v3.6 — Diagnose-Version, KEIN Fix
Esc-Ausstieg funktioniert bei Sutefan trotz v3.5 (Schnittstellen
werden nachweislich korrekt gefunden und überwacht) weiterhin nicht.
Vermutung: das Report-*Format* ist das Problem, nicht mehr die
Schnittstellen-Auswahl — manche NKRO-Tastaturen senden Tastendrücke
als Bitmaske statt als einfachen Byte-Wert. Bewusst kein weiterer
Rateversuch diesmal: stattdessen zeichnet diese Version die rohen
Bytes der ersten 30 tatsächlich empfangenen Reports auf, damit der
nächste Fix auf echten Daten aufbaut.

## v3.5 — Bugfix Runde 3: echte Ursache per Log-Datei gefunden
Nutzer schickte die tatsächliche Diagnose-Zeile: eine mechanische
Custom-Tastatur (KBDFans Tiger80) legt gleichzeitig drei HID-
Schnittstellen mit identischem Namen an. Die Erkennung wählte bisher
immer nur eine davon — aber die tatsächlichen Tastendrücke liefen
über eine andere. Fix: statt einer einzelnen Schnittstelle werden
jetzt alle Schnittstellen mit demselben Tastaturnamen gleichzeitig
überwacht — welche davon die Tasten sendet, muss nicht mehr erraten
werden.

## v3.4 — Bugfix Runde 2: Esc-Ausstieg funktionierte weiterhin nicht
Der v3.3-Fix reichte nicht — der dortige Rückfall (USB-Boot-Protokoll)
ist im Standard zwar definiert, aber optional. Viele Tastaturen (v.a.
kabellose über einen Funk-Dongle) implementieren das gar nicht. Neue
dritte Erkennungsstufe: der HID-Report-Deskriptor selbst, der für
jedes HID-Gerät verpflichtend ist. Zusätzlich protokolliert die
Erkennung jetzt jeden Schritt — bisher war sie komplett stumm, was
jede Ferndiagnose zum Raten gemacht hat.

## v3.3 — Bugfix: Esc-Ausstieg funktionierte bei manchen Nutzern gar nicht
Esc-Ausstieg aus dem Spiel lief bei einem Nutzer zuverlässig, bei
zwei anderen mit angeschlossener Tastatur überhaupt nicht. Ursache:
die Tastatur-Erkennung suchte nur nach dem Wort "keyboard" im
selbstgemeldeten Gerätenamen — funktioniert nur bei Herstellern, die
dieses Wort tatsächlich verwenden. Andere Tastaturen wurden dadurch
komplett übersehen, lautlos (kein Fehler im Log). Neue zweite
Erkennungsstufe: der USB-HID-Standard selbst definiert eine
herstellerunabhängige Kennung für Tastaturen (bInterfaceProtocol==1) —
darüber werden jetzt auch Tastaturen erkannt, die "keyboard" nicht im
Namen tragen.

## v3.2 — konsolidiert (Nutzerwunsch: nicht wieder so viele Versionen in kurzer Zeit)
Zwischen v3.0 und v3.5 waren in kurzer Zeit sechs Versionsnummern
entstanden — vor allem, weil ein kritischer Bug drei Anläufe brauchte,
bis die echte Ursache gefunden war. Alles Passierte bleibt inhaltlich
vollständig erhalten, hier als ein gebündelter Eintrag:

**Standard-Boot-Animation:** ein D-Pad-Symbol, das flackernd "zum
Leben erwacht", statt eines direkten Sprungs ins Menü, wenn keine
eigene Boot-Animation existiert.

**Drei Anläufe für einen kritischen Bugfix** (Bildschirm blieb nach
dem Update schwarz, nichts passierte mehr): Versuch 1 (vermutet)
umging einen möglichen VSync-Hänger in der neuen Boot-Animation —
reichte allein nicht. Versuch 2 (vermutet, dann per Test bewiesen)
behob eine Zeitüberschreitungs-Prüfung, die bei wiederholt
fehlschlagender Geräteabfrage übersprungen werden konnte. Versuch 3
(mit einer echten Log-Datei endlich bestätigt) behob die eigentliche
Ursache: ein Reihenfolge-Fehler beim Programmstart
(`AttributeError: '_ra_lookup'`), der nur Nutzer mit eingerichtetem
RetroAchievements traf.

**CRT-Textabschneide-/Scroll-Fixes über neun Info-Bildschirme**
(mehrere Runden Rückmeldungen, teils mit echten CRT-Fotos): neue
Zeilenumbruch-Funktion (an Wortgrenzen statt mitten im Wort mit "~"
abzuschneiden), Mitwirkende und Geheimnisse scrollbar gemacht,
Trophäenraum komplett umgebaut (Cover bleibt fest, Statistik +
Zusammenfassung scrollen gemeinsam — vorher lief der Text quer durchs
Boxart), Zeitanzeige bei Fortschrittswerten vereinheitlicht ("Stunden
dann Minuten"), Geheimcode-Popup zentriert statt links unten am Rand.
Geklärt: der geheime Sound existiert, war vermutlich nur unhörbar,
weil Soundeffekte unterdrückt werden, solange Musik läuft.

**RA-Erfolgs-Vitrine (F6) beschleunigt:** kurzlebiger Cache (15
Minuten) für wiederholtes Ansehen desselben, bereits gespielten
Spiels — der separate Hintergrund-Watcher für neu verdiente Erfolge
während des Spielens bleibt bewusst ungecacht.

## v5.2 (letzte Version vor der Neuordnung)
Neue Standard-Boot-Animation: ein D-Pad-Symbol, das flackernd "zum
Leben erwacht", statt eines direkten Sprungs ins Menü. Bisher
passierte ohne eigene, selbst erstellte Boot-Animation gar nichts
Sichtbares. Komplett aus den eigenen Zeichen-Mitteln gebaut (kein
Video/Bild-Codec), läuft nur, wenn keine eigene Animation vorhanden
ist - wer sich per `video_to_bootanim.py` was Eigenes erstellt hat,
bleibt davon unberührt.

## v5.1
Vermuteter Bugfix (keine Log-Datei verfügbar, per Analyse hergeleitet):
nach einem Soft-Reset kommt das Frontend manchmal nicht wieder, ohne
jede Fehlermeldung. Hypothese: überlebt `/tmp` einen Soft-Reset (kein
echter Kernel-Neustart), bleibt auch eine alte Sperrdatei bestehen -
zeigt sie zufällig auf eine PID, die inzwischen ein völlig anderer
Prozess ist, verweigerte das Frontend bisher fälschlich den Start.
Prüft jetzt zusätzlich, ob die PID tatsächlich zu unserem eigenen
frontend.py gehört. Auch ohne bestätigte Diagnose eine echte
Verbesserung der Robustheit.

## v5.0
Performance-Politur: ein einmaliger, bereits bewusst in Kauf
genommener Berechnungs-Ruck beim allerersten Bildschirmaufbau (die
Hintergrund-Vignette wird beim ersten Mal berechnet, danach gecacht)
traf bisher ausgerechnet den ersten echten Blick ins Menü. Jetzt wird
der Cache still während der Boot-Animation vorgewärmt, die bei jedem
Neustart ohnehin läuft - der erste sichtbare Menü-Aufbau ist dadurch
messbar spürbar schneller.

## v4.9
Brotkrumen-Kopfzeile schneidet nicht mehr mitten im Wort ab. Passt
der volle Pfad ("Kategorie / Unterordner") nicht auf den Bildschirm,
zeigt die Kopfzeile jetzt nur noch den aktuellen Ordnernamen statt
kryptisch abgehackt zu wirken.

## v4.8
Kleine Bedienbarkeits-Politur: "Sammlungen" und "RA-Erfolgsjäger"
zeigen jetzt die Gesamtanzahl direkt im Namen ("Sammlungen (5)"), wie
es die Unterordner schon lange tun. Kein blindes Reingehen mehr
nötig, nur um zu sehen, ob überhaupt was drin ist.

## v4.7
Neue Hilfe-Übersicht (System-Menü → Info → "Hilfe / Übersicht", erster
Eintrag) - eine zentrale Stelle, die alles zeigt, was das Frontend
kann: Navigation, Tasten in der Spieleliste (F6/F7/F8), besondere
Hauptmenü-Einträge, System-Menü-Überblick. Erwähnt nur, dass es
Geheimnisse gibt, nicht welche.

## v4.6
Spieltagebuch: Name und System/Dauer stehen jetzt auf zwei getrennten
Zeilen statt einer - auf CRT wurden lange Titel vorher oft
abgeschnitten. Der Name bekommt jetzt die volle Zeilenbreite für
sich.

## v4.5
Neues Spieltagebuch (System-Menü → Statistiken & Erfolge →
"Spieltagebuch") - kleine, rollierende Version der letzten 30 Tage,
räumt sich automatisch selbst auf. Zeigt "Heute"/"Gestern" und dann
das Datum, darunter jede einzelne Spielsitzung mit System und Dauer.
Die volle, dauerhafte Version mit Archivierung bleibt bewusst
zurückgestellt - erstmal schauen, wie die kleine Version ankommt.

## v4.4
Bugfix: in seltenen Fällen (ca. 1 von 10) startete das Frontend nicht
richtig, MiSTer blieb im eigenen OSD hängen. Ursache: der
Autostart-Wrapper wartete nur 60s auf MiSTers eigenen Boot-Abschluss
und startete danach so oder so weiter - auf Systemen mit knapp
längerer Boot-Zeit (langsamere SD-Karte, große Sammlung) konnte das
Frontend so starten, während MiSTer selbst noch nicht ganz bereit
war. Wartezeit auf 120s verdoppelt (verlangsamt niemanden, der schon
zuverlässig startete - die Schleife bricht immer sofort ab, sobald
MiSTer wirklich fertig ist) plus ein zusätzliches Sicherheitsnetz:
bis zu 5 Neuversuche beim Öffnen des Bildschirms, falls es doch noch
zu früh sein sollte.

## v4.3
Neue "Sammlungen"-Kategorie im Hauptmenü - zwei automatische, aus
vorhandenen Daten abgeleitete Gruppierungen: "Dieses Jahr entdeckt"
und "Kurzweilige Spiele" (kurze durchschnittliche Sitzungsdauer, min.
2 Starts nötig). Kein neues Tracking nötig, taucht nur auf, wenn
tatsächlich etwas reinpasst.

## v4.2
Neuer Jahresrückblick (System-Menü → Statistiken & Erfolge →
"Jahresrückblick") - baut auf der Jahres-Bündelung aus v4.1 auf.
Zeigt Spielzeit, meistgespieltes Spiel, Lieblingssystem, Anzahl
verschiedener Spiele/Systeme und wie viele Spiele du dieses Jahr zum
ersten Mal entdeckt hast - alles eingegrenzt auf das laufende
Kalenderjahr statt "seit Aufzeichnungsbeginn". Zeigt eine freundliche
Meldung, wenn für das Jahr noch nichts aufgezeichnet wurde.

## v4.1
Fundament für einen künftigen echten Jahresrückblick: Spielzeit wird
jetzt zusätzlich nach Kalenderjahr gebündelt (bisher nur kumulierte
Gesamtwerte, keine Zeitachse). Komplett eigenständig - ändert nichts
an der bestehenden Spielzeit-Aufzeichnung, kein Risiko für
Trophäenraum, Top-10-Listen oder eigene Erfolge. Noch keine sichtbare
neue Funktion, reine Datengrundlage für den nächsten Schritt.

## v4.0
Das System-Menü war über viele Versionen hinweg auf 23 flache
Einträge angewachsen - jetzt in 7 thematische Untergruppen aufgeteilt
(RetroAchievements, Statistiken & Erfolge, Anzeige & Sound, Verhalten,
Eingabe & Sprache, Info, Wartung). Nutzt dieselbe Ordner-Navigation
wie eigene ROM-Unterordner - fühlt sich vertraut an, deutlich
übersichtlicher als die lange Liste vorher.

## v3.9
Credits angepasst: Dfense als Mitwirkender ergänzt. Betrifft sowohl
den sichtbaren Credits-Bildschirm als auch den (geheimen)
Entwicklerraum.

## v3.8
Neuer Bildschirm "Mitwirkende" im System-Menü - Ersteller, wer
mitgeholfen hat, ein Dank an alle Spieler. Ganz normal sichtbar im
Menü, kein Geheimnis wie der Entwicklerraum.

## v3.7
Geheimcodes auf reine Tastatur-Eingabe umgestellt (nicht mehr per
Gamepad). Grund: Am Joypad gab es schlicht keine Taste mehr, die auf
jedem Pad-Typ (gerade SNES-Nachbauten ohne L2/R2) garantiert
wirkungslos ist. Neuer Hinweistext auf dem Geheimnisse-Bildschirm
macht das transparent.

## v3.6
Echter Designfehler behoben: Die Geheimcodes nutzten ursprünglich "ok"
und "back" für die Bestätigungs-Tasten - aber die lösen im Hauptmenü
immer eine echte Wirkung aus (Kategorie betreten bzw. Beenden-Dialog),
egal ob gerade ein Code eingegeben wird. Einer der Codes hätte dadurch
nie vollständig eingegeben werden können. Jetzt werden "favorite" und
"completed" verwendet - beide im Hauptmenü nachweislich wirkungslos,
lösen also nie eine ungewollte Navigation aus. Alle Codes
funktionieren jetzt tatsächlich vollständig, ohne die normale
Bedienung während der Eingabe zu stören.

## v3.5
Bugfix: die Geheimcode-Erkennung lief bisher auf jeder Seite, nicht
nur im Hauptmenü wie eigentlich vorgesehen. Einer der (kurzen) Codes
hätte dadurch theoretisch auch während ganz normaler Navigation in
einer Spieleliste ungewollt auslösen können. Jetzt nur noch im
Hauptmenü aktiv - beim Seitenwechsel wird eine begonnene Eingabe
sauber verworfen statt später überraschend fortgesetzt zu werden.

## v3.4
Max-Level-Boot-Effekt - eine kurze Einblendung beim Booten, sobald das
Frontend-Level das Maximum erreicht hat. Läuft komplett unabhängig von
der normalen Boot-Animation, kostet unter dem Maximum keine einzige
zusätzliche Millisekunde. Die komplett alternative Boot-Animation
bleibt vorerst zurückgestellt - deutlich aufwendiger (eigene
Gestaltung + eigene CRT/HDMI-Performance-Abstimmung).

## v3.3
"Easter Egg System" - Frontend-Level (aus vorhandenen Daten
abgeleitet) plus ein paar geheime Cheat-Codes mit echten Wirkungen,
jeder schaltet ein anderes Geheimnis frei. Codes lassen sich beliebig
oft eingeben, wie echte Cheat-Codes. Neue "Geheimnisse"-Übersicht im
System-Menü zeigt "???" bis gefunden, dann Name und Herkunft - ohne
die Codes selbst zu verraten.

## v3.2
Flackern beim Scrollen und dauerhafte Zeilen-Überlappung behoben -
übernommen aus einer sorgfältigen, eigenständigen Fehlerdiagnose über
mehrere Iterationen. Die eigentliche Ursache: die markierte Zeile hat
einen leuchtenden Rand, der absichtlich etwas über die eigene Zeile
hinausragt - wurde die Zeile darüber vor der Markierung gezeichnet,
blieb dieser "Bleed" dauerhaft sichtbar, weil ihn nichts danach
übermalt hat. Jetzt wird die markierte Zeile immer zuerst gezeichnet,
Nachbarn (und im Sonderfall die Kopfzeile) danach - dazu eine neue
VSync-Wartefunktion gegen Tearing und gebündeltes statt mehrfaches
Bildschirm-Update beim Navigieren.

## v3.1
Abschließende Fehlerprüfung vor dem Gesamtpaket - dabei einen echten,
kleinen Bug gefunden: der Trophäenraum zeigte bei fehlendem Cover den
internen Text "no_artwork" wörtlich an, statt "kein Artwork" - ein
falscher Übersetzungsschlüssel. Behoben, nutzt jetzt dieselbe, bereits
vorhandene Übersetzung wie an anderer Stelle im Frontend. Ansonsten:
Syntax, Regressionstest und ein automatisierter Abgleich aller Texte
liefen sauber durch.

## v3.0
Eigener PNG-Decoder von Grund auf gebaut (Chunk-Parsing, komplette
Zeilen-Entfilterung mit allen 5 PNG-Filtertypen, alle gängigen
Farbtypen) - gegen Pillow als Referenz-Bibliothek bei echten
PNG-Dateien byte-identisch geprüft. Damit zeigt die RA-Erfolgs-Vitrine
(F6) jetzt echte Icons direkt am MiSTer-Bildschirm, nicht nur im
Browser-Overlay. Icons werden vorab geladen, damit das Scrollen selbst
flüssig bleibt, und dauerhaft lokal zwischengespeichert.

## v2.9
RA-Erfolge zeigen sich jetzt in Echtzeit im Streamer-Overlay - eine
Einblendung oben rechts mit Icon, Titel, Beschreibung und Punkten,
sobald ein Erfolg während des Spielens freigeschaltet wird (nicht erst
nach Rückkehr ins Menü). Läuft nur, wenn das Overlay aktiv ist, mit
eigenem Admin-Schalter zum Ein-/Ausschalten. Icons werden von RA
einmalig geladen und dauerhaft zwischengespeichert.

## v2.8
F6 (RA-Erfolgs-Vitrine) zeigte ohne RetroAchievements-Einrichtung gar
keine Rückmeldung - wirkte wie eine tote Taste. Jetzt zwei klare,
unterschiedliche Meldungen: "RetroAchievements nicht eingerichtet",
wenn gar keine Konfigurationsdatei existiert, und "Keine
RetroAchievements-Daten für dieses Spiel", wenn RA zwar eingerichtet
ist, aber für das gerade angeschaute Spiel nichts gefunden wird.

## v2.7
Neue RA-Erfolgs-Vitrine (Taste F6 bei einem Spiel mit
RetroAchievements-Unterstützung) - zeigt die komplette Erfolgsliste
(Name, Beschreibung, Punkte, freigeschaltet/nicht) statt nur der Zahl
neben dem Cover. Bewusst als separate, eigenständige Funktion gebaut -
die bestehende RA-Anzeige (Cover-Fortschritt, Erfolgsjäger,
Trophäenraum) bleibt komplett unverändert. Vorerst als Text-Liste
(Icons brauchen einen eigenen PNG-Decoder, den es noch nicht gibt -
kommt evtl. später). Die dafür nötige RA-GameID wird jetzt aus der
bestehenden Abfrage mitgenommen, ohne dass sich an deren Verhalten
etwas ändert.

## v2.6
Die System-Jingles aus v2.5 wieder entfernt - haben nicht gefallen.
Komplett zurückgebaut, keine Reste. Das CRT-Testbild aus derselben
Version bleibt bestehen.

## v2.5
Zwei neue Features: Jeder System-Einstieg bekommt jetzt einen kurzen,
eigenen Klang (14 Systeme, eigene erfundene Töne, keine Nachbildung
echter Konsolensounds) - spielt nur im Menü, vor jedem möglichen
Spielstart, stört also kein Intro-Video. Und ein CRT-Testbild im
System-Menü ("CRT-Testbild") - Geometrie-Rahmen, Raster, Farbbalken,
Zentrierkreuz, wie das alte Servicemenü echter Röhren-Monitore.

## v2.4
Bugfix: das Erfolgs-Pop-up blieb aus, wenn ein Erfolg ausgerechnet
während der allerersten Spielsitzung neu erreicht wurde (z. B. drei
verschiedene Systeme gestartet) - der Erfolg zeigte sich zwar korrekt
in "Meine Erfolge", aber ohne Pop-up/Ton. Die Schutzlogik gegen eine
Pop-up-Flut bei längerer Spielhistorie initialisiert sich jetzt schon
beim Programmstart statt erst beim ersten tatsächlichen Ereignis -
dadurch werden ab sofort auch Erfolge aus der allerersten Sitzung
zuverlässig gemeldet.

## v2.3
Neue Kategorie "RA-Erfolgsjäger" (direkt vor "Scripts" im Hauptmenü) -
zeigt alle Spiele in deiner Sammlung, die RetroAchievements-Erfolge
haben, bei denen du aber noch nichts freigeschaltet hast. Gruppiert
nach System, pro System nach Anzahl verfügbarer Erfolge sortiert (die
größten Gelegenheiten zuerst). Funktioniert wie deine eigenen
ROM-Unterordner - reinklicken, System wählen, loslegen. Taucht nur
auf, wenn RetroAchievements eingerichtet ist und tatsächlich etwas
gefunden wird.

## v2.2
Neue Option für NAS-Nutzer: "Beim Start auf NAS/Netzwerk warten" im
System-Menü (Standard AUS). Liegen ROMs auf einem Netzlaufwerk, kann
der Scan beim Booten starten, bevor die Verbindung wirklich steht -
die dann leere/unvollständige Liste würde sogar dauerhaft gecacht
werden. Mit eingeschalteter Option wartet das Frontend erst auf
Netzwerk und einen stabilen Ordnerinhalt, bevor gescannt wird. Für
SD-Karte/USB (die meisten Fälle) bleibt der Start unverändert schnell
- die Option kostet nur etwas, wenn man sie aktiv einschaltet.

## v2.1
"Weiterspielen" jetzt abgestimmt auf TheRealSutefans neues
"ra_lastplayed.sh"-Skript (nutzt MiSTers eigene Recent-Dateien, erfasst
dadurch jeden Spielstart - nicht nur was über unser Frontend lief).
"Weiterspielen" bevorzugt jetzt diese genauere externe Liste, falls
ein solches Skript aktiv ist, sonst unverändert unsere eigene. Dabei
auch eine Namens-Falle behoben: externe Einträge haben ein
Core-Präfix ("RA SNES - Chrono Trigger"), unsere
Durchgespielt-Markierung aber nur den reinen Namen - ohne den Fix
hätte "Weiterspielen" längst durchgespielte Titel weiter vorgeschlagen.

## v2.0
Neuer Bildschirm "Trophäenraum" (System-Menü → "Mein Trophäenraum") -
ein persönlicher Profil-Screen statt trockener Zahlen: großes Cover
deines meistgespielten Spiels, dein Lieblingssystem (anhand der
gesamten Spielzeit dort, nicht nur des einzelnen Top-Spiels), Erfolgs-
Zähler und eine kurze Zusammenfassung. Baut komplett auf Daten auf,
die wir längst sammeln - keine neue Einrichtung nötig.

## v1.99
Neue Kategorie "Weiterspielen" ganz oben im Hauptmenü - schlägt gezielt
das Spiel vor, das du zuletzt gestartet, aber noch nicht als
durchgespielt markiert hast. Verschwindet von selbst, sobald nichts
mehr offen ist (oder wenn du noch nie etwas gespielt hast) - kein
leerer Eintrag für niemanden, der die Durchgespielt-Markierung nicht
nutzt.

## v1.98
Zwei Dinge: Der Start wartet nicht mehr auf die Zeitsynchronisierung -
die läuft jetzt komplett im Hintergrund weiter, das Menü erscheint
sofort (die Uhr stellt sich trotzdem zuverlässig, nur eben ohne dass
der Start darauf wartet). Und: der gemeldete Cursor-Sprung beim
Scrollen ist behoben - bei einem beschleunigten Turbo-Sprung (Taste
gehalten) hat der schnelle Zeichenpfad nicht alle dazwischenliegenden
Zeilen aufgefrischt, wodurch die Markierung sichtbar "sprang". Läuft
jetzt bei Turbo-Sprüngen korrekt über den vollständigen Aufbau.

## v1.97
Kurze Einblendung samt eigenem Erfolgston, wenn ein Erfolg (normaler
Meilenstein oder versteckter) neu erreicht wird - beim Zurückkehren
aus einem Spiel, beim Favorisieren oder beim Markieren als
durchgespielt. Wer schon länger spielt und beim Update bereits einige
Erfolge erreicht hat, bekommt beim allerersten Start keine Flut von
Pop-ups für längst Erreichtes - nur echt Neues löst eine Meldung aus.

## v1.96
Drittes Paket von TheRealSutefan übernommen: ein Marker-Mechanismus
für sein separates "Recently Played"-Skript (aktuell inaktiv, bis das
fertig ist), Boot-Diagnose-Logging für das Soft-Reboot-Rätsel, und ein
Timing-Fix beim Overlay. Dazu vier gemeldete Fehler behoben - der
wichtigste: aus der RA-Core-Auswahl kam man mit keiner Taste zurück
(ESC hat fälschlich "normaler Core" gewählt und ist trotzdem in die
Kategorie gewechselt, statt wirklich abzubrechen). Außerdem: beide
Top-10-Listen und der Erfolge-Bildschirm scrollen jetzt auf CRT, wenn
nicht alles auf den Bildschirm passt, und der Titel "TOP 10 -
MEISTGESTARTET" wird nicht mehr abgeschnitten.

## v1.95
Die Spielzeit-Meilensteine zeigten rohe Sekunden statt einer lesbaren
Zeit (z. B. "198/3600" statt "3min/1h") - behoben. Dazu fünf neue
versteckte Erfolge, die als "???" erscheinen, bis sie erreicht sind:
Nachteule (zwischen 0-5 Uhr gespielt), Marathon (eine Sitzung über 3
Stunden am Stück), Sammlerin (10 Favoriten gleichzeitig), Stammspieler
(ein Spiel 20+ mal gestartet), Legende (alle höchsten Meilensteine
gleichzeitig erreicht).

## v1.94 — RA-Fortschritt für weitere Systeme repariert
Nach dem letzten Fix (Game Boy/Saturn) fehlte RA-Fortschritt immer
noch bei NES, SNES und anderen Systemen. Grund: RetroAchievements nennt
manche Konsolen anders, als wir angenommen hatten - "SNES/Super
Famicom" statt nur "SNES", "Mega Drive" statt "Genesis Mega Drive".
Der Abgleich verlangte bisher eine exakte Übereinstimmung. Jetzt wird
geprüft, ob unsere Bezeichnung als zusammenhängende Wortfolge in RAs
tatsächlichem Namen vorkommt - wortgrenzen-bewusst, damit "NES" nicht
aus Versehen jedes SNES-Spiel mittrifft.

## v1.93 — optischer Feinschliff
Vier Verbesserungen fürs Auge, alle ohne laufende Zusatzkosten:
abgerundete Ecken bei der Auswahl-Markierung, der Boxart-Bereich sieht
jetzt wie eine Karte mit Schlagschatten aus, eine dezente
Randabdunkelung (Vignette) auf einfarbigen Hintergründen, und etwas
mehr Luft zwischen Kopfzeile/Liste sowie Liste/Boxart. Eine echte,
pixelgenaue Vignette hätte über eine Sekunde gekostet - stattdessen
eine deutlich günstigere, zeilenbasierte Variante (ca. 3-20ms, nur
einmalig pro Farbe). Laufende Navigation bleibt bei 3,4ms pro
Neuzeichnen, keine spürbare Verlangsamung.

## v1.92 — zwei Fixes
Die Uhrzeit zeigte nach der NTP-Synchronisierung 2 Stunden zu wenig
(deutsche Sommerzeit) - NTP liefert UTC, wir haben das aber als
Ortszeit übernommen, weil MiSTer selbst keine Zeitzone kennt. Neue,
manuell einstellbare Zeitzone im System-Menü (0,5h-Schritte). Zweitens:
RetroAchievements-Fortschritt fehlte bei Game Boy und Saturn komplett
- falscher bzw. fehlender Systemschlüssel in der internen Zuordnung,
jetzt korrigiert und gegen die echte Systemliste abgeglichen.

## mpg123-Diagnose verbessert
Alle drei Installationswege (online, offline, aus dem MiSTer-Menü)
sagen jetzt nicht mehr nur "mpg123 fehlt", sondern auch, dass es
eigentlich zur MiSTer-Firmware gehört (kein separates Paket) und dass
meist ein "Update All" im MiSTer-OSD hilft.

## v1.91
Zweiter Patch von TheRealSutefan übernommen - diesmal vor allem
Performance und Overlay. Größter Einzelposten: ein Text-Zeilen-Cache,
der ganze Beschriftungen als fertigen Streifen zwischenspeichert statt
sie bei jedem Zeichnen neu zusammenzusetzen (byte-identisch zur alten
Ausgabe geprüft). Dazu: Cover, die beim schnellen Scrollen noch nicht
bereitstehen, werden übersprungen statt zu ruckeln und kurz danach
nachgeladen; eine überflüssige Zeilen-Wiederherstellung nach vollem
Neuzeichnen entfällt; das Scannen der Eingabegeräte prüft erst günstig,
ob sich überhaupt was geändert hat. Admin-Oberfläche des Overlays:
Schalter waren nicht klickbar (falsches HTML-Element), jetzt behoben,
wirken außerdem sofort statt erst beim nächsten Zustandswechsel. Das
Overlay durchsucht jetzt auch HD-Cover, und ein bisher unbemerkter
Fehler ist behoben: Cover waren im Browser eigentlich komplett
durchsichtig (fehlender Alpha-Kanal in unseren eigenen Cover-Dateien).

## v1.90
Ein Nutzer hat unabhängig einen eigenen Patch gebaut und eingereicht -
sieben Verbesserungen daraus übernommen, jede einzeln geprüft und auf
den aktuellen Stand angepasst: Admin-Oberfläche des Overlays reagierte
nicht auf Checkboxen, Boot-Skript las die Core-Datei nicht robust
genug, Cover mit führender Nummer im Dateinamen (kuratierte Sets)
wurden nicht gefunden, Overlay blieb während des Spiels leer, Cover-
Caches etwas vergrößert, deutlichere Startmeldungen (vor allem beim
"läuft schon"-Fall), Offline-Installer findet sein Paket jetzt
zuverlässiger.

## v1.89
Zwei neue Sachen, die zusammengehören: ein "Durchgespielt"-Status pro
Spiel (F7, wie Favorisieren) und ein eigenes, komplett lokales
Achievement-System - unabhängig von RetroAchievements, nur auf
unseren eigenen Daten basierend (Spielzeit, Starts, verschiedene
Systeme ausprobiert, durchgespielte Spiele). 15 Meilensteine, neuer
Anzeige-Bildschirm "Meine Erfolge" im System-Menü.

## v1.88 — wichtiger Fix
Die RA-Core-Auswahl aus v1.86 hat immer den normalen Core gestartet,
egal was man ausgewählt hat. Fehlender Baustein: eine echte `.mgl`-
Datei von sage2050s Werkzeug enthält neben dem Core-Pfad noch ein
zweites Element (`<setname same_dir="1">RA_NAME</setname>`) - ohne
das behandelt MiSTer den RA-Core offenbar nicht als eigene Variante.
Jetzt anhand einer echten, vom Nutzer geschickten Datei korrekt
nachgebaut. Dabei auch Saturn als unterstütztes System ergänzt (war
fälschlich als nicht unterstützt eingestuft).

## v1.87 — wichtiger Fix
Die Spieleliste wurde bei jedem Start komplett neu gescannt statt aus
dem Cache geladen. Grund: MiSTer legt oft leere `/media/usb0`-
Platzhalterordner an, auch ganz ohne angeschlossenes Laufwerk - unsere
USB-Bereitschaftsprüfung hat einen durchgehend leeren Ordner nie als
"fertig" erkannt und dadurch nie gecacht. Erkennt jetzt auch eine
stabil-leere USB-Situation korrekt als unbedenklich.

## Installation vereinfacht
Neues Skript `Scripts/install_frontend.sh` - eine einzige Datei
einmalig per WinSCP kopieren, danach reicht im MiSTer-Menü selbst
"Scripts -> install frontend" antippen. Kein SSH/Terminal mehr nötig
für die Erstinstallation oder ein Update.

## v1.86
Beim Betreten eines Systems (z. B. SNES) jetzt wählbar, ob der normale
Core oder ein RetroAchievements-Core geladen wird - falls einer über
sage2050s "MiSTer_RetroAchievements"-Werkzeug installiert ist. Findet
sich für ein System kein passender RA-Core, taucht die Frage dort gar
nicht erst auf.

## v1.85 — wichtiger Fix
Auf MiSTern mit einem Sony/PlayStation-artigen Controller blieb der
Bildschirm dauerhaft im MiSTer-eigenen Menü hängen, auch bei
manuellem Neustart. Der Grund: unsere Injektion des F9-Tastendrucks
(schaltet MiSTer in den Konsolenmodus) hat versehentlich die
"Consumer Control"-Nebenschnittstelle des Controllers getroffen statt
der echten Tastatur - beide meldet der Kernel als "Tastatur", nur
eine davon ist es wirklich. Sucht jetzt zuerst gezielt nach "Keyboard"
im Gerätenamen, bevor es auf die alte, ungenauere Erkennung
zurückfällt.

## v1.84
Die Soundeffekte haben teilweise die Musik gestört und sich bei
schneller Navigation gestapelt - kam davon, dass `aplay` offenbar auf
dieselbe Soundkarte wartete wie `mpg123`. Jetzt zwei Bremsen: kein
neuer Ton, solange der vorherige noch läuft, und während die Musik
tatsächlich gerade spielt, wird gar nicht erst versucht.

## v1.83
OBS-Overlay aufgehübscht: Genre/Jahr, Spielzeit, RetroAchievements-
Fortschritt und ein kleiner Stern für Favoriten sind jetzt mit im
Bild, jedes einzeln über das Backend an-/abschaltbar.

## v1.82
RetroAchievements-Fortschritt im Info-Bereich ("RA: 20/50"). Wer's
nicht eingerichtet hat, merkt nichts davon - keine Verzögerung, keine
Anzeige. Einrichtung per SSH (Bildschirmtastatur gibt's bei uns
nicht), Abgleich über den Spieletitel. Bei Zweifel zeigt's lieber
nichts an als was Falsches.

## v1.81
Hab die letzten fünf Versionen nochmal durchgecheckt. `play_sfx()`
hat unnötig oft eine Datei geprüft, bevor überhaupt die Drossel
greift - gefixt. Der Verdacht, die neue Spielzeit-Anzeige würde die
Navigation ausbremsen, hat sich beim genaueren Hinsehen zum Glück
nicht bestätigt.

## v1.80
Zwei Top-10-Listen im System-Menü: meistgespielt und meistgestartet.

## v1.79
Automatischer Spielzeit-Tracker. Merkt sich pro Spiel, wie lang
tatsächlich gespielt wurde - Ladezeiten zählen nicht mit.

## v1.78
Kleine Soundeffekte beim Navigieren, selbst erzeugt (kein Download
nötig). Ein-/ausschaltbar im System-Menü.

## v1.77
MiSTer hat keine gepufferte Uhr, also holt sich das Frontend jetzt
selbst die Zeit per NTP. Dazu drei Farbschemata zur Auswahl (Dunkel,
Hell, Retro-Grün).

## v1.76
Notausstieg vereinfacht - nur noch Esc statt der Dreifachkombi. Der
Pad-Ausstieg über Start+Select bleibt vorerst Zukunftsmusik, mein
Controller gibt während des Spiels einfach nichts her.

## v1.75
Einen Weg gefunden, während eines laufenden Spiels trotzdem noch
Tastatureingaben mitzubekommen (MiSTer sperrt das eigentlich
komplett). Damit jetzt: Notausstieg per Tastenkombi, ohne erst
zurück ins Menü zu müssen.

## v1.74
Mein eigener Fix aus v1.73 war noch halb kaputt - "Zuletzt gespielt"
und "System" nutzen intern dieselbe Markierung, dadurch hat sich die
falsche Kategorie aktualisiert. Jetzt sauber über den Namen gelöst.

## v1.73
Attract-Modus ließ sich zwar umschalten, die Beschriftung hat's nur
nicht gezeigt. Und: "Zurück" aus einem Unterordner sprang immer ganz
nach oben statt zur vorherigen Stelle - beides behoben.

## v1.72
Manche Cover fehlten einfach, obwohl sie da waren. Lag daran, dass
ein einmal fehlgeschlagener Ladeversuch für immer gemerkt wurde, auch
wenn's nur eine gerade noch kopierte, unvollständige Datei war.

## v1.71
Ein einzelner Schritt hoch/runter beim Browsen zeichnet jetzt nur
noch, was sich wirklich ändert, statt die ganze Seite neu aufzubauen.
Gute 51% schneller pro Schritt.

## v1.70
Des Rätsels Lösung für den zu früh startenden Attract-Modus: MiSTer
hat keine Batterie-Uhr, die Zeit kann mitten in der Sitzung plötzlich
springen. Auf eine Uhr umgestellt, die das nicht tut.

## v1.69
Der bisher größte Performance-Fund: Cover-Verkleinerung hat pro
Pixel einzeln gearbeitet statt zeilenweise. Kostete fast 90ms bei
jeder Navigation zu einem neuen Spiel. Jetzt 69% schneller.

## v1.68
Laufschrift bei langen Titeln raste auf CRT viel zu schnell durchs
Bild - fehlende Zeitbremse, jetzt nachgerüstet.

## v1.67
Der Zeichen-Cache für Rechtecke wuchs unbegrenzt weiter. Jetzt mit
Obergrenze.

## v1.66
Attract-Modus wartet jetzt 90 statt 45 Sekunden, und die Abfrage, ob
er aktiv ist, wird zwischengespeichert statt bei jedem Tick neu von
der Platte gelesen.

## v1.65
Attract-Modus ist manchmal viel zu früh angesprungen (lief schon
während Boot/Scan mit). Und: der Turbo-Sprung beim Klicken hat
manchmal zwei Zeilen übersprungen statt einer.

## v1.64 — kritischer Bugfix
Frontend stürzte kurz nach dem Boot ab, sobald der erste Equalizer-
Tick fällig war. Ein Codeblock war beim letzten Umbau verrutscht.
Peinlich, aber schnell gefunden.

## v1.63
Auch die Songtitel-Laufschrift läuft jetzt über den leichten
Zeichenpfad statt eines vollen Aufbaus.

## v1.62
Der bislang größte Performance-Sprung: jeder Equalizer-/Puls-Tick hat
bisher den ganzen Bildschirm neu gezeichnet, obwohl sich nur eine
Zeile ändert. 90% weniger Zeit pro Tick - das war vermutlich die
Hauptursache für das gemeldete HDMI-Ruckeln.

## v1.61
Fortsetzung von v1.60 - das Einfrieren beim Konfigurieren von "OSD
öffnen" lag an F9, das MiSTer für sich selbst reserviert. Jetzt mit
Zeitlimit und F9-Sperre im Belegungs-Assistenten.

## v1.60
Der Belegungs-Assistent hat die Eingabe während der ganzen Dauer
gesperrt, wodurch MiSTers eigene Menütaste parallel reagieren konnte
- Bildschirm ist eingefroren. Grab bleibt jetzt durchgehend aktiv.

## v1.59
L1/L2/R1/R2 komplett belegbar, auch für Controller, die die
Schultertasten als Analogwert statt als Knopf senden.

## v1.58
Favoriten-Liste - F8 oder L2 markiert ein Spiel, eigene Kategorie,
kleiner Stern in der Übersicht.

## v1.57
Attract-Modus / Bildschirmschoner - nach 45 Sekunden Leerlauf zeigt
das Menü ein zufälliges Spiel großflächig, wechselt alle paar
Sekunden weiter.

## v1.56
Boxart-Downloader kann jetzt auch Arcade-Cover.

## v1.53–v1.55
Ein paar hartnäckige USB-Kaltstart-Bugs gefixt, Offline-Installer
dazu, Equalizer und Laufschrift auch auf HDMI nochmal schneller,
Uhrzeit + Netzwerksymbol im Hauptmenü.

## v1.48–v1.52
Eigene Unterordner werden jetzt 1:1 übernommen statt alles
plattzuklopfen. Boxart erscheint auch auf Ordner-Ebene. Ein paar
Startup-Bugs behoben.

## v1.39–v1.47
Viel Performance-Feinschliff auf CRT. Größter Fund: der Boxart-
Schatten hat allein 60% der Zeichenzeit gefressen - auf eine
vorgemischte Variante umgestellt, rund 4x schneller. Boot-Animation
und Boxart-Downloader ebenfalls deutlich flotter.

## v1.30–v1.38
"Zuletzt gespielt" als neue Kategorie, Now-Playing in die Fußzeile,
Boot-Animation erkennt automatisch CRT/HDMI, richtiger Installer.

## v1.29
Akzentfarben pro System, Glow-Effekt, pulsierende Markierung,
Equalizer-Animation bei laufender Musik.

## v1.19–v1.28
Grundgerüst für die Zweiseiten-Navigation, Hintergrundmusik,
Sprachumschaltung, eigene Tastenbelegung, Stream-Overlay,
automatische Bereinigung der Spieleliste.

## v1.1–v1.6
Die ersten lauffähigen Versionen - Boxart, CRT/HDMI-Umschaltung,
Buchstaben-Sprung in der Liste.

---

Ausführliche Anleitung und alle Funktionen im Detail: `README.md`.
Kurzer Überblick mit Screenshots: `VORSCHAU.md`.
