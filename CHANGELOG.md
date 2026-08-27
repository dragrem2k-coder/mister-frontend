# Changelog

Was sich am Frontend so getan hat. Für die ganz kleinteiligen Details
schau am besten in die Git-Historie oder in den Kopf von
`frontend/frontend.py`.

## v4.4 — Reset-Feature, HDMI-Performance-Runde, Stream-Menüpunkt

**Neue Features:**
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

**Bugfixes:**
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
