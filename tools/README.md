# tools/

Entwickler-Werkzeuge, die NICHT auf den MiSTer deployt werden (analog zu
`PC-Tools/`, aber fuer reine Test-/Diagnose-Skripte statt Endnutzer-Tools).

Alle Skripte hier laufen auf jedem PC mit Python 3, OHNE echte
MiSTer-Hardware (kein `/dev/fb0`, keine echten Eingabegeraete noetig) und
ohne zusaetzliche Pakete. Sie finden `frontend/frontend.py` von selbst
(relativ zum `tools/`-Ordner); ein abweichender Pfad laesst sich ueber die
Umgebungsvariable `FRONTEND_PY` setzen:

```
FRONTEND_PY=/pfad/zu/frontend.py python3 tools/regression_test.py
```

Alles auf einmal (Reihenfolge wie beim Ausliefern eines neuen Builds):

```
python3 tools/regression_test.py \
  && python3 tools/test_input_repeat.py \
  && python3 tools/test_overlay_redraw.py \
  && python3 tools/test_fb_size.py \
  && python3 tools/test_virtualboy.py \
  && python3 tools/test_cover_scaling.py \
  && python3 tools/test_nas_cache.py \
  && python3 tools/test_crt_layout.py \
  && python3 tools/test_autostart.py \
  && python3 tools/test_rom_filter.py \
  && python3 tools/test_mister_ini.py \
  && python3 tools/test_cover_prewarm.py \
  && python3 tools/test_reset_sofort.py \
  && python3 tools/test_system_abdeckung.py \
  && python3 tools/test_boxart_streifen.py \
  && python3 tools/test_sysart_logos.py \
  && python3 tools/test_prewarm_abbruch.py \
  && python3 tools/test_prewarm_absturz.py \
  && python3 tools/test_script_eingaben.py \
  && python3 tools/test_thumb_verdraengung.py \
  && python3 tools/test_kastenstufen.py \
  && python3 tools/test_kein_systemhintergrund.py \
  && python3 tools/test_pad_bedienung.py \
  && python3 tools/test_ruhige_boxspalte.py \
  && python3 tools/test_vsync_und_wiederholrate.py \
  && python3 tools/test_hinweisbox_flackern.py \
  && python3 tools/test_ra_einstellungen.py \
  && python3 tools/test_cover_panel.py \
  && python3 tools/test_kategorie_abzeichen.py \
  && python3 tools/test_abzeichen_verteilung.py \
  && python3 tools/test_vorauslader_prozess.py \
  && python3 tools/test_zeilen_spuren.py \
  && python3 tools/test_vorladen_richtung.py \
  && python3 tools/test_kaltes_cover.py \
  && python3 tools/test_cover_index.py \
  && python3 tools/test_hauptseite_spuren.py \
  && python3 tools/test_kernel_wechsel.py \
  && python3 tools/test_bildrand.py \
  && python3 tools/test_suchtreffer.py \
  && python3 tools/test_bildlib.py \
  && python3 tools/test_namensabgleich.py \
  && python3 tools/test_verkleinern.py \
  && python3 tools/test_cover_original.py \
  && python3 tools/test_artpacks.py \
  && python3 tools/diag_lightpath.py
```

| Skript | Art | Prueft |
|---|---|---|
| `regression_test.py` | Test (Pass/Fail) | Zeichnet jede Kategorie in beiden Aufloesungen ohne Ausnahme |
| `test_input_repeat.py` | Test (Pass/Fail) | Tastenwiederholung: Anlaufsperre, Richtungswechsel, Geister-Wiederholung |
| `test_overlay_redraw.py` | Test (Pass/Fail) | Hinweisbox verschwindet bitgenau restlos |
| `test_fb_size.py` | Test (Pass/Fail) | Menuepunkt "Menue-Aufloesung": fb_size in der MiSTer.ini |
| `test_virtualboy.py` | Test (Pass/Fail) | Kategorie "Virtual Boy": Core-/ROM-Pruefung, Logo, Akzentfarbe |
| `test_cover_scaling.py` | Test (Pass/Fail) | Verkleinern der Boxart: Flaechenmittel statt Wegwerfen |
| `test_nas_cache.py` | Test (Pass/Fail) | NAS-Spiele werden nicht bei jedem Start neu eingelesen |
| `test_crt_layout.py` | Test (Pass/Fail) | Engeres Layout auf CRT, keine Reste beim Scrollen, HDMI/480p unveraendert |
| `test_autostart.py` | Test (Pass/Fail) | Autostart-Schalter: user-startup.sh sicher aendern |
| `test_rom_filter.py` | Test (Pass/Fail) | ROMs verschwinden nicht mehr stillschweigend aus der Liste |
| `test_mister_ini.py` | Test (Pass/Fail) | Keine Video-Reste in der MiSTer.ini - und kein Anfassen fremder Bloecke |
| `test_cover_prewarm.py` | Test (Pass/Fail) | Cover-Vorberechnung: gleiche Kastengroesse wie der Zeichenpfad, bitgleiche Miniaturen |
| `test_reset_sofort.py` | Test (Pass/Fail) | F5-Reset und F1-Ausstieg ohne Haltezeit; F10 und der F4-Schnellstart restlos entfernt |
| `test_system_abdeckung.py` | Test (Pass/Fail) | Eine Systemliste fuer alle Werkzeuge; Startparameter der bestehenden Systeme festgenagelt |
| `test_boxart_streifen.py` | Test (Pass/Fail) | Restore-Band knabbert die Boxart-Karte nicht an; Panel-Auslassen nur auf HDMI |
| `test_sysart_logos.py` | Test (Pass/Fail) | Kategorie-Logos: gueltiges ART1, Groesse, Kartenhintergrund, Dateiname = Systemschluessel |
| `test_prewarm_abbruch.py` | Test (Pass/Fail) | read_action(timeout=0) sieht wirklich nach; Fortschrittsbild wird auf CRT nicht abgeschnitten |
| `test_prewarm_absturz.py` | Test (Pass/Fail) | "Miniaturen vorbereiten" kann das Frontend nicht mehr mitreissen; keine doppelten Cover |
| `test_script_eingaben.py` | Test (Pass/Fail) | Abfragen in den Shell-Skripten funktionieren auch mit Wagenruecklauf in der Eingabe |
| `test_thumb_verdraengung.py` | Test (Pass/Fail) | Miniaturen-Cache: Uhrensprung nach dem Start, Schutz der Kategorie-Logos, Aufraeumen auf Vorrat, getrennte Ablagen fuer CRT/HDMI |
| `test_kastenstufen.py` | Test (Pass/Fail) | Boxart-Kasten hat nur drei Hoehen, und der Text passt in jedem Fall noch hinein |
| `test_kein_systemhintergrund.py` | Test (Pass/Fail) | System-Hintergrundbilder sind restlos raus: kein bg-Zugriff, kein zweiter Bildversuch ohne Cover, kein Menuepunkt |
| `test_pad_bedienung.py` | Test (Pass/Fail) | Select als Modifikator (Select+A/Select+X), Buchstabenwaehler, Hilfe gegen die echte Belegung |
| `test_ruhige_boxspalte.py` | Test (Pass/Fail) | Verzoegertes Cover zeigt keinen Platzhalter, Platzhalter ist ein Rahmen, keine Spalte bei reinen Ordnerlisten, Positionsgedaechtnis je Kategorie |
| `test_vsync_und_wiederholrate.py` | Test (Pass/Fail) | Vsync-Auslassen nur noch bei schmalen Baendern, Wiederholrate folgt der gemessenen Zeichendauer |
| `test_hinweisbox_flackern.py` | Test (Pass/Fail) | Hinweisbox: genau ein Flip pro Aufbau, und der kommt NACH der Box |
| `test_ra_einstellungen.py` | Test (Pass/Fail) | MiSTers RA-Datei: nur die gemeinte Zeile wird angefasst, Zugangsdaten und Kommentare bleiben |
| `test_cover_panel.py` | Test (Pass/Fail) | Verkuerzter Schlagschatten ergibt bitgenau dasselbe Bild und ist schneller |
| `test_kategorie_abzeichen.py` | Test (Pass/Fail) | Alle Kategorie-Abzeichen gleich gross, gleicher Hintergrund, gleiche Stelle auf dem Schirm |
| `test_abzeichen_verteilung.py` | Test (Pass/Fail) | Die echten Installer-Bloecke ersetzen die alten Logos wirklich - einmal, und danach nie wieder |
| `test_vorauslader_prozess.py` | Test (Pass/Fail) | Vorauslader als eigener Prozess: rechnet, schreibt in den richtigen Ordner, faellt sauber auf den Thread zurueck |
| `test_zeilen_spuren.py` | Test (Pass/Fail) | Gezieltes Freiraeumen ergibt bitgenau dasselbe Bild wie der volle Aufbau, auch nach 30 Schritten |
| `test_vorladen_richtung.py` | Test (Pass/Fail) | Vorauslader startet fast sofort statt nach einer Sekunde und zielt beim Richtungswechsel neu |
| `test_kaltes_cover.py` | Test (Pass/Fail) | Kaltes Cover geht an den Arbeitsprozess - mit Notbremse, ohne Quelldatei gar nicht, und nur aus dem Zeichenpfad |
| `test_cover_index.py` | Test (Pass/Fail) | Cover-Index ohne regulaeren Ausdruck - bewiesen gleichwertig ueber 65536 Zeichen - und der Start-Thread steckt zurueck |
| `test_hauptseite_spuren.py` | Test (Pass/Fail) | Hauptseite ohne Vollbild-Clear: bitgenau wie der volle Aufbau, auch nach 30 Schritten, bei kuerzerem Songtitel und wegfallendem Netzwerk |
| `test_kernel_wechsel.py` | Test (Pass/Fail) | Bildspeicher wird auf beiden MiSTer-Kerneln erkannt - sysfs zuerst, ioctl als Rueckfall |
| `test_bildrand.py` | Test (Pass/Fail) | Einstellbarer Bildrand: Vorgabe unveraendert, kaputte Datei faellt zurueck, und der Wert kommt wirklich im Layout an |
| `test_suchtreffer.py` | Test (Pass/Fail) | Positionsanzeige und Trefferwechsel: ASCII-Abkuerzung bewiesen gleichwertig, neuer Sprung trifft dasselbe wie der alte, leichter Pfad bitgleich |
| `test_artpacks.py` | Test (Pass/Fail) | Artwork aus Artpacks in allen ueblichen Ablageformen, Arcade beim Vorbereiten, Groesse des Bild-Zwischenspeichers |
| `test_cover_original.py` | Test (Pass/Fail) | Download legt PNG/JPG im Original ab und das Frontend findet sie; Tauschschalter laesst Enter in Ruhe; USB-Wartezeit |
| `test_verkleinern.py` | Test (Pass/Fail) | Der umgebaute Verkleinerer liefert bitgenau dasselbe Bild wie vorher, und ist im HDMI-Fall doppelt so schnell |
| `test_namensabgleich.py` | Test (Pass/Fail) | Cover trotz anderer ROM-Schreibweise (GoodTools gegen No-Intro), und das Nachzieh-Netz fuer spaet anlaufende Laufwerke |
| `test_bildlib.py` | Test (Pass/Fail) | libpng/TurboJPEG ueber ctypes: bitgleich zum Python-Dekoder, Rueckfall ohne Bibliothek, fremde docs-Quelle nur als Luecken-Fueller |
| `diag_kaltes_cover.py` | Diagnose (immer Rueckgabewert 0) | Woraus ein kaltes Cover besteht: lesen, dekodieren, verkleinern - laeuft auch auf dem MiSTer |
| `diag_vorauslader.py` | Diagnose (immer Rueckgabewert 0) | Was der Vorauslader dem Zeichnen wegnimmt - Thread gegen Prozess |
| `diag_zeilen_spuren.py` | Diagnose (immer Rueckgabewert 0) | Was das gezielte Freiraeumen bringt - ganze Spalte gegen Spuren |
| `diag_hintergrundlast.py` | Diagnose (immer Rueckgabewert 0) | Was pro Tastendruck wirklich passiert: Dateizugriffe, Log-Zeilen, doppelte Arbeit |
| `diag_lightpath.py` | Diagnose (immer Rueckgabewert 0) | Leichter Zeichenpfad gegen vollen Neuaufbau |
| `_harness.py` | Hilfsmodul | Framebuffer-Attrappe + kuenstliche Uhr fuer die Zeichen-Tests |

## regression_test.py

Standard-Regressionstest fuer `frontend/frontend.py`. Ersetzt nur die
hardwarenahen Teile der `Framebuffer`-Klasse durch eine Attrappe, geht aber
bewusst durch den ECHTEN `Frontend()`-Konstruktor (siehe Kommentar im
Skript, Grund: ein frueherer Reihenfolge-Fehler in `__init__()` blieb
monatelang unentdeckt, weil jeder damalige Test das betroffene Attribut von
Hand vorher gesetzt hatte).

Testet 2 Aufloesungen (CRT 320x240, HDMI 1920x1080) x jede tatsaechlich
vorhandene Kategorie (aus `fe.cats`, skaliert automatisch mit der echten
Spielebibliothek) x mehrere Navigationspositionen/Sonderzustaende
(Beenden-Dialog, Attract-Modus, RA-Core-Auswahlbildschirm inkl. Abbruch).

Prueft NUR, dass `draw()`/verwandte Zeichenfunktionen ohne Ausnahme
durchlaufen (Abdeckung von Strukturfehlern, Index-/Attributfehlern,
Konstruktor-Reihenfolge). Prueft NICHT das tatsaechliche visuelle Ergebnis,
Eingabeverarbeitung oder Core-Start - das bleibt ein Test auf echter
Hardware.

Erwartetes Ergebnis: `18/18 Kombinationen bestanden` (die Zahl waechst mit
der Anzahl vorhandener Kategorien).

## test_input_repeat.py

Prueft die Tastenwiederholung mit der ECHTEN `InputManager`-Logik - ohne
echte Eingabegeraete, indem nur die Zustandsuebergaenge
(`_hold`/`_release`/`_cancel_repeat`) durchgespielt werden.

Sichert zwei Nutzer-Rueckmeldungen ab, die je einen Bugfix ausgeloest haben:

* "wenn ich nach unten gedrueckt halte und dann wieder nach oben druecke
  bleibt der kurz haengen" - beim Richtungswechsel MITTEN im Scrollen lief
  die volle Anlaufsperre erneut an (jetzt: verkuerzte Anlaufzeit, erreichtes
  Tempo bleibt erhalten).
* "der Cursor bewegt sich nicht und dann kommt auf einmal die ploetzliche
  Bewegung" - nach 'Zurueck'/'OK' lief eine Geister-Wiederholung der vorher
  gehaltenen Richtungstaste weiter.

Zusaetzlich abgedeckt: Achswechsel (runter -> rechts) darf NICHT als
Richtungswechsel zaehlen, nach einer Scroll-Pause gilt wieder die volle
Anlaufsperre, und Seiten-Spruenge (links/rechts) haben eine eigene,
langsamere Untergrenze als Zeilen-Spruenge.

## test_overlay_redraw.py

Prueft, dass eine eingeblendete Hinweisbox RESTLOS verschwindet.

Hintergrund (Nutzer-Rueckmeldung): "wenn ich von HDMI auf CRT umschalte
kommt das Popup mit der Info 'CRT aktiv' - sobald ich dann den Cursor
bewege, verschwindet die Infobox nicht ganz". Ursache war der schnelle
Zeichenpfad: er baut den Hintergrund ausserhalb der Listenspalte nicht neu
auf und liess deshalb den ueberstehenden Teil der Box stehen.

Der Test vergleicht BITGENAU mit einer Referenzinstanz, die dieselbe
Position ohne jemals eingeblendete Box zeichnet - bleibt auch nur ein Pixel
uebrig, schlaegt er fehl. Beide Wege werden abgedeckt: Box per Tastendruck
weggeraeumt und Box per Zeitablauf ausgelaufen.

## test_fb_size.py

Prueft den Menuepunkt "Menue-Aufloesung" (Nutzerwunsch: "eventuell unter
System und dann unter Optionen dafuer einen Schalter einbauen, der beim
Neustart das an- und ausschaltet"). Der Punkt schaltet `fb_size` in der
MiSTer.ini durch (voll -> halb -> viertel).

Das ist der einzige Test hier, der eine Datei ausserhalb des Frontends
betrifft: die MiSTer.ini gehoert dem MiSTer, nicht uns, und ein Fehler
dort trifft das ganze Geraet. Entsprechend gruendlich wird geprueft, dass
ausser der einen Zeile NICHTS veraendert wird - insbesondere nicht der
`[Menu]`-Block, den der CRT-Schalter verwaltet. Gearbeitet wird immer auf
einer Kopie in einem temporaeren Ordner, nie auf einer echten MiSTer.ini.

Abgedeckt: Lesen/Schreiben/Durchschalten, wortgleiche Wiederherstellung
nach einem Rundlauf, mehrfach vorhandener Schluessel, Eintrag innerhalb
einer Sektion (darf nicht angefasst werden), ini ohne Sektionen,
unbekannter Wert, fehlende Datei, sowie die Menuezeile selbst
(sichtbar im HDMI-Modus, ausgeblendet im CRT-Modus) und die
Vollstaendigkeit der Uebersetzungen.

## test_virtualboy.py

Prueft die Kategorie "Virtual Boy" (Nutzerwunsch: "wenn der Core
verfuegbar ist und ROMs dazu vorhanden sind, wie die anderen Kategorien
auf der Hauptseite hinzufuegen").

Geprueft werden die drei Sichtbarkeits-Bedingungen (Core da + ROMs da ->
erscheint; Core weg -> erscheint nicht; ROM-Ordner leer -> erscheint
nicht), die Stammdaten (Ordner `games/VirtualBoy`, Endung `.vb`,
MGL-Parameter delay 1 / Typ f / Index 1), der Umgang mit dem
Datumsstempel im Core-Dateinamen (`VirtualBoy_20240115.rbf` - bei
mehreren Staenden muss der neueste gewinnen), Anzeigename und
Akzentfarbe sowie die mitgelieferte Logo-Datei `sysart/VIRTUALBOY.art`
(ART1-Kopf, Breite 900 wie die uebrigen Logos, Hintergrundfarbe
28,32,44, kein Rest des Karomusters aus der Bildvorlage).

Gearbeitet wird in einem temporaeren Ordner mit umgebogenen Pfaden, nie
auf echten Spieldaten.

## test_cover_scaling.py

Prueft das Verkleinern der Boxart (Nutzer-Rueckmeldung nach Einfuehrung
der "Menue-Aufloesung": "auf halb sehen die Boxarts pixelig aus").

Bisher wurden beim Verkleinern schlicht Bildzeilen und -spalten
weggeworfen (Nearest-Neighbor); jetzt wird ueber die zusammenfallenden
Bildpunkte gemittelt. "Sieht huebsch aus" kann kein Test pruefen -
geprueft wird deshalb das objektiv Nachrechenbare: unveraenderte
Zielgroesse, exakte Farbtreue bei einfarbigen Flaechen, Mittelung eines
1-Pixel-Streifenmusters (dort lieferte das alte Verfahren reines
Schwarz oder Weiss - genau der sichtbare Mangel), Monotonie eines
Verlaufs, Randfaelle bis hinunter zu 1x1, und dass sich der
Cache-Schluessel geaendert hat (sonst kaeme die Verbesserung bei bereits
zwischengespeicherten Covern nie an).

Gibt am Ende die gemessene Laufzeit aus - als Einordnung, nicht als
Bestehenskriterium.

## test_nas_cache.py

Prueft, dass Spiele auf einer Netzwerk-Freigabe NICHT bei jedem Start neu
eingelesen werden (Nutzer-Rueckmeldung ueber einen Bekannten).

Die Signatur, an der das Frontend "hat sich etwas geaendert?" erkennt,
kennzeichnet jeden Ablageort. Die Kennung lautete
`"usb:" if "/media/usb" in base else "fat:"` - ein NAS unter
`/media/fat/cifs/...` bekam damit dieselbe Kennung wie die SD-Karte.
Beim Kaltstart ist die Freigabe oft noch nicht eingehaengt, die frische
Signatur enthaelt die NAS-Ordner dann nicht, der gespeicherte Stand
schon - Unterschied, alles neu einlesen. Das Sicherheitsnetz
("Cache erwartet X, X fehlt -> warten") gab es nur fuer USB.

Geprueft wird das, was sich ohne echtes NAS objektiv nachstellen laesst:
eigene Kennung `nas:`, keine Kollision gleichnamiger Ordner auf Karte,
NAS und USB, Ortsunabhaengigkeit der Kennung (ein Umhaengen darf keinen
Neuscan ausloesen), das unveraenderte USB-Verhalten und die
Aufschluesselung nach System.

## test_crt_layout.py

Prueft das engere Layout auf CRT (Nutzerwunsch: "haben wir irgendwie
ne Moeglichkeit, das Frontend im CRT-Modus huebscher aussehen zu
lassen?").

Mehrere Abstaende standen als FESTE Pixelzahl im Layout (Kopfblock 46,
Zeilenhoehe 15, Abstand zur Boxart-Karte 20, Kategorie-Zeilenhoehe 22).
Sie skalieren zwar ueber `s = H//360` mit - aber `s` ist bei 240 und bei
480 Zeilen gleich 1, bei 240 Zeilen belegten sie also den doppelten
Bildanteil. Gemessen: 17 statt 35 Zeichen pro Zeile, 10 statt 17
sichtbare Spiele, 7 statt 12 Kategorien.

"Sieht huebscher aus" kann kein Test pruefen. Geprueft wird deshalb der
nachrechenbare Teil: dass der Gewinn da ist, dass HDMI und 640x480
BIT-genau unveraendert bleiben (der eigentliche Sinn des Tests), dass
der Overscan-Sicherheitsrand unangetastet ist, dass die Cover-Spalte
brauchbar breit bleibt - und dass der Kopfbereich nicht mit der ersten
Zeile kollidiert. Letzteres ist beim Bauen ZWEIMAL passiert (der
Auswahlbalken lief in die Eintragszahl) und faellt in reinen Zahlen
nicht auf, deshalb steht die Freiraum-Rechnung ausdruecklich im Test.

## test_autostart.py

Prueft den Autostart-Schalter (Nutzerfrage: "ist da jetzt quasi ein
Schalter unter System/Optionen drin, der den Autostart an- und
ausschaltbar macht?").

Das ist die heikelste Schreiboperation im ganzen Projekt: der Schalter
aendert `/media/fat/linux/user-startup.sh`, eine Datei, die dem MiSTer
gehoert. Ist ihr Inhalt kaputt, bootet das Geraet nicht mehr richtig -
und der Nutzer kaeme an kein Menue mehr, um es zurueckzunehmen.
Entsprechend liegt der Schwerpunkt auf den Faellen, in denen etwas
SCHIEFGEHT.

Abgedeckt: nur die eine Zeile faellt weg (fremde Eintraege UND der
Eintrag des F4-Waechters bleiben zeichengenau stehen, Reihenfolge
inklusive); ein auskommentierter Eintrag zaehlt nicht als "an";
mehrfaches Ein-/Ausschalten traegt nichts doppelt ein; die einmalige
Sicherheitskopie bewahrt den Originalzustand und wird spaeter NICHT
ueberschrieben; nach jeder Aenderung hat die Datei Shebang und
Ausfuehrungsrecht; eine Datei ohne Shebang bekommt einen; nicht sauber
kodierte Bytes ueberleben unveraendert. Und die drei Fehlerwege: nicht
beschreibbares Verzeichnis, scheiterndes `os.replace()` (kuenstlich
ausgeloest - der einzige Weg, der auch als root aussagekraeftig ist),
und eine durchgefallene Rueckleseprobe. In allen dreien muss die
Zieldatei zeichengenau unveraendert bleiben und darf keine halbe
Nebendatei liegen bleiben.

## test_rom_filter.py

Prueft, dass ROMs aus den Ordnern des Nutzers nicht mehr stillschweigend
verschwinden (Nutzer-Rueckmeldung: "Tetris (Japan) (En).gb wurde weder
mit kuratierter Liste noch ohne erkannt - erst als ich sie in Tetris.gb
umbenannt habe").

Zwei Ursachen, beide abgesichert. Erstens kannte der Nur-Japan-Filter
die Ausnahme "(Japan, USA)" (mehrere Regionen in EINER Klammer), aber
nicht "japanisches Release mit englischer Sprachfassung", wo die Sprache
in einer ZWEITEN Klammer steht - in No-Intro-Sets die uebliche
Schreibweise. Zweitens liefen beide Filter beim EINLESEN, immer, ohne
Schalter und ohne Hinweis, und damit VOR der kuratierten Liste; deren
Abschalten half deshalb nicht, die Datei war da schon verworfen.

Geprueft werden zehn uebliche Schreibweisen aus No-Intro/Redump, das
tatsaechliche Einlesen eines Ordners mit und ohne Filter (ohne Filter
muss JEDE Datei erscheinen, mit Filter muss der gemeldete Tetris-Titel
TROTZDEM sichtbar bleiben), dass der Schalter standardmaessig AUS ist,
und dass der Cache-Fingerabdruck den Schalterzustand kennt - sonst
wuerde ein Umschalten erst beim naechsten ohnehin faelligen Neuscan
sichtbar und der Menuepunkt wirkte kaputt.

## test_mister_ini.py

Prueft, dass das Frontend keine Video-Reste in der `MiSTer.ini`
hinterlaesst - und dass es dabei nichts anfasst, was ihm nicht gehoert
(Nutzer-Rueckmeldung nach einem wackelnden HDMI-Bild bei einem
Bekannten: "falls das die Ursache ist, sollten wir da Vorkehrungen
treffen, das heisst bei uninstall mit raus").

Das Frontend setzt selbst KEINEN Videomodus - es liest die Geometrie aus
`/sys/class/graphics/fb0/` und schreibt Pixel. Die einzigen beiden
Stellen, an denen es das Bild ueberhaupt beeinflussen kann, sind der
`[Menu]`-Block (CRT-Modus) und `fb_size` (Menue-Aufloesung).

Der wichtigste Block ist Test 3: ein `[Menu]`-Block kann auch vom Nutzer
selbst stammen (das ist eine ganz normale MiSTer-Funktion), und der darf
durch eine Deinstallation nicht verlorengehen. Entfernt wird nur, was
dem Frontend zuzurechnen ist - erkennbar an der Markierungsdatei ODER an
einem wortgleichen Blockinhalt (Rueckfall fuer Installationen aus der
Zeit vor der Markierung, Test 4). Eine einzige geaenderte Zeile genuegt,
damit der Block als fremd gilt (Test 4b).

Ausserdem: `fb_size` wird in BEIDE Umschaltrichtungen zurueckgesetzt
(Test 5/5b), das sichere Schreiben mit Sicherungskopie und Rueck-Lesen
(Test 6), ein absichtlich fehlgeschlagenes `os.replace` laesst die Datei
unveraendert (Test 6b), eine fehlende `MiSTer.ini` bricht nichts ab
(Test 7), die Log-Zeile beim Start nennt beide Einstellungen (Test 8),
und `frontend/mister_ini_cleanup.py` wird als eigener Prozess gegen eine
Wegwerf-`MiSTer.ini` wirklich ausgefuehrt (Test 9/9b) - einmal mit
eigenem, einmal mit fremdem Block.

## test_cover_prewarm.py

Prueft das Vorberechnen der Cover-Miniaturen (Build 73). Anlass waren
Messwerte vom Geraet des Nutzers: von 251 ms Seitenaufbau entfielen
225 ms auf EIN noch nicht vorberechnetes Cover, das Zeichnen selbst
kostete rund 20 ms.

**Test 1 ist der wichtigste dieser Datei.** Der Schluessel des
Festplatten-Caches enthaelt die KASTENGROESSE, in die das Cover
eingepasst wird - und die haengt am Text darunter, ist also pro Spiel
verschieden (im Log des Nutzers: 96x99, 96x111, 96x135 in derselben
Liste). Fragt der Vorauslader auch nur ein Pixel anders an als der
Zeichenpfad, legt er Miniaturen ab, die nie jemand findet - und es faellt
niemandem auf, weil nichts kaputtgeht, es bleibt nur langsam. Der Test
schneidet deshalb die vom ECHTEN Zeichenpfad angefragten Masse mit
(`ART.get_scaled` wird umgebogen) und vergleicht sie Eintrag fuer
Eintrag mit dem, was der Vorauslader vorhersagt - in beiden
Aufloesungen. Dazu die Gegenprobe, dass die Testtitel ueberhaupt
verschiedene Kastenhoehen erzeugen (auf CRT; auf HDMI deckelt die
85%-Regel alles auf dieselbe Hoehe).

Weiter: die vorberechnete Miniatur ist Byte fuer Byte identisch mit
einer frisch berechneten (Test 2, beide Richtungen - vergroessern und
verkleinern), Sonderfaelle wie fehlende/beschaedigte Dateien (2b), die
Vorberechnung fasst die Arbeitsspeicher-Caches von `ArtCache` NICHT an
(Test 3 - sie laeuft aus einem Hintergrund-Thread, und diese Caches
haben keine Sperre), der Thread arbeitet ab und laesst sich abbrechen
(4/4b), die Auftragsliste laesst schon Vorhandenes weg und schaut in
Scrollrichtung weiter voraus als zurueck (4c/4d), Menuepunkt und
Uebersetzungen (5).

## test_reset_sofort.py

Prueft die beiden Tasten, die waehrend eines laufenden Spiels SOFORT
ausloesen: F5 (Reset im Core) und F1 (zurueck ins Frontend). Ausserdem,
dass F10 und der F4-Schnellstart restlos entfernt sind.

Zum F5-Reset auf sofortigen Tastendruck (Nutzerwunsch:
"F5-Reset-Funktion haette ich gerne auf sofortigen Tastendruck, wenn das
geht"). Vorher lagen drei Verzoegerungen hintereinander: 0,6 s
Haltezeit, bis zu 0,2 s weil die Haltezeit erst am Anfang der naechsten
Schleifenrunde geprueft wurde (die vorher in `select(..., 0.2)` wartet),
und 0,2 s fuer das virtuelle Tastatur-Geraet, das bei JEDEM Reset neu
angelegt wurde. Uebrig bleibt die Tastendruckdauer von 0,1 s.

Der wichtigste Block ist Test 3: ohne Haltezeit darf blosses HALTEN
nicht zum Dauerfeuer werden - es braucht immer erst ein Loslassen. Dazu
geprueft: das Geraet wird nur einmal angelegt und danach
wiederverwendet, der zweite Aufruf wartet nachweislich nicht mehr auf
das Anlegen, Druck UND Loslassen aller drei Tasten werden gesendet
(bleibt eine haengen, kaeme kein weiterer Reset an), und nach einem
Schreibfehler wird das Geraet verworfen und beim naechsten Mal neu
angelegt - sonst waere ein einmal kaputtes Geraet ein Dauerproblem.

## test_system_abdeckung.py

Prueft, dass die Systemliste EINE Quelle hat - und dass beim Erweitern
kein bestehendes System stillschweigend andere Startparameter bekommt.

Ausloeser war die Nutzerfrage "muss ich das Boxart-Skript nochmal
starten, damit ich die fuer Virtual Boy bekomme?" Die Antwort war nein:
das System stand in KEINEM der drei Download-Werkzeuge. Die Liste gab es
viermal - einmal im Frontend, dreimal in den Werkzeugen, alle von Hand
gepflegt. **Das Tueckische ist der fehlende Fehler:** das Skript laeuft
durch, meldet Erfolg und laesst das fehlende System einfach aus.

Seit Build 79 ist `fe/systems.py` die einzige Quelle; die beiden
Werkzeuge auf dem MiSTer lesen direkt von dort, das PC-Werkzeug behaelt
eine erzeugte Kopie (es wird einzeln auf einen Windows-PC kopiert und
kann nichts importieren). Test 1 laedt alle drei und vergleicht ihre
Tabelle mit der Quelle.

**Test 3 ist der wichtigste:** er nagelt Startparameter und ROM-Ordner
der urspruenglichen 16 Systeme auf ihre bekannten Werte fest. Die Liste
wuchs in einem Zug von 16 auf 48 - ein dabei verrutschter Index heisst
"Core startet, ROM laedt nicht", und zwar ohne Fehlermeldung. Test 3b
macht dasselbe fuer die Datenbank-Zuordnung, besonders fuer den Sonder-
fall Game Gear (derselbe Core wie Master System, aber eine eigene
Cover-Datenbank).

Test 4c prueft, dass keine Kombination aus ROM-Ordner und Dateiendung
zweimal vergeben ist - sonst erschiene dieselbe Datei in zwei
Kategorien. Systeme ohne Datenbank stehen in einer Ausnahmeliste MIT
Begruendung (jeweils bei libretro nachgesehen, nicht vermutet).

## test_boxart_streifen.py

Der schnelle Seitenpfad stellt vor dem Neuzeichnen der Zeilen den
Hintergrund der Listenspalte wieder her - mit 10*s Rand nach jeder
Seite. Die Boxart-Karte beginnt aber nicht in festem Abstand: auf HDMI
42 Pixel rechts der Liste, auf CRT 2. Das Band wischte dort acht Pixel
weit in die Karte hinein; sichtbar wurde es erst, als Build 76 die Karte
waehrend des Scrollens nicht mehr jedes Mal darueber malte ("schwarzer
Block ueber Boxart und Gameinfo, beim Loslassen wieder weg").

Test 1 haelt die Voraussetzung fest (der Abstand ist NICHT konstant -
jede feste Pixelzahl an dieser Stelle erzeugt den Fehler erneut), Test 2
beweist auf Pixelebene, dass die Karte einen Scroll-Schritt mit
ausgelassenem Panel unveraendert uebersteht, Test 3 haelt fest, dass das
Auslassen selbst nur auf HDMI greift.

## test_sysart_logos.py

Prueft die Kategorie-Logos unter `frontend/sysart/`. Beide Fehler, die
hier moeglich sind, sind lautlos: ein Logo mit falschem Hintergrund
sieht nur aus wie ein heller Kasten auf der dunklen Karte, ein Logo mit
falsch geschriebenem Dateinamen wird schlicht nie geoeffnet. Zusaetzlich
wird die Groesse gedeckelt - das 3DO-Logo waere sonst bei 900 px Breite
1729 Zeilen hoch (6 MB), um am Ende 234 px breit dargestellt zu werden.

## test_prewarm_abbruch.py

Zwei Fehler an "Miniaturen vorbereiten", die als eine Meldung ankamen.

Der wichtigere Test ist Test 1: `read_action(timeout=0)` hat NIE etwas
gelesen. Bei timeout=0 ist die Deadline sofort erreicht, und die
Pruefung stand ganz am Anfang der Schleife - `select()` wurde also gar
nicht erst aufgerufen. Der Abbruch konnte damit nicht funktionieren, und
zwar lautlos, weil `None` auch der normale Rueckgabewert fuer "keine
Taste" ist. Der Test legt dafuer einen echten evdev-Datensatz in eine
Pipe und prueft, dass der Poll ihn findet UND trotzdem sofort
zurueckkehrt.

Test 3 rechnet nach, dass Titel und Abbruch-Hinweis in beiden Sprachen
und allen drei Aufloesungen in die verfuegbare Breite passen - auf
320x240 waren es vorher 18 bzw. 37 Zeichen Platz bei 29 bzw. 51 Zeichen
Text, und `fb.text()` schneidet still ab.

## test_prewarm_absturz.py

Der Nutzer meldete: "wenn er mit Miniaturen erstellen fertig ist,
springt das Frontend ins OSD". Es ist dort nicht gesprungen, sondern
ABGESTUERZT - der Aufraeum-Block in `run()` leert bei jedem Ende den
Bildschirm und injiziert F12, damit MiSTer sauber sein eigenes Menue
zeigt. Von aussen ist ein Absturz dadurch von einem gewollten Beenden
nicht zu unterscheiden.

Ursache, hier nachgestellt: ein Eintrag ohne Systemkey (Sonder-
kategorien wie System oder Zufalls-Zock haben bewusst `syskey=None`)
fuehrte zu `os.path.join(ART_BASE, None)` - ein **TypeError**, kein
OSError, also von keinem der bestehenden `except`-Zweige gefangen.

Test 3 schickt jede im Frontend vorkommende Eintragsform durch den
kompletten Durchlauf, Test 4 prueft das Sicherheitsnetz selbst (ein
absichtlich ausgeloester Fehler darf hoechstens den Vorgang kosten,
nie die Sitzung), Test 5 die Entdopplung.

## test_script_eingaben.py

`read -r` entfernt den Zeilenumbruch, aber KEIN Wagenruecklauf-Zeichen.
Je nach Startweg (MiSTer-OSD, serielle Konsole, SSH-Client) kommt eine
Eingabe als `"2\r"` an - und

    case "2\r" in 2|hd|HD) ... ;; *) ... ;; esac

trifft dann den `*`-Zweig. In `Frontend_Boxart_Download.sh` bedeutete
der "sd": die Profil-Auswahl war wirkungslos, und zwar lautlos.

Der Test nimmt die ECHTE Skriptdatei, ersetzt nur die letzte Zeile (die
python3 startet) und faehrt das Auswahlmenue mit beiden Eingabeformen.
Test 3 prueft zusaetzlich alle uebrigen Abfragen in `Scripts/`: jede
muss ihre Eingabe entweder saeubern oder ohnehin nur auf ein Praefix
vergleichen (`[nN]*`).

Warum das ueberhaupt ein automatischer Test sein muss: von Hand testet
man mit einer normalen Tastatur, und die liefert kein `\r`. Genau der
Fall, der beim Nutzer auftritt, ist der, den man beim Testen nie
erwischt.

## test_thumb_verdraengung.py

Der MiSTer hat keine gepufferte Uhr: nach dem Start steht sie auf 01:00,
ein paar Sekunden spaeter stellt NTP sie auf die echte Zeit. Die
Verdraengung im Miniaturen-Zwischenspeicher benutzte die Aenderungszeit
der Cache-Datei als "zuletzt benutzt"-Marke und setzte sie bei jedem
Treffer auf die AKTUELLE Systemzeit.

Damit lagen ausgerechnet die beim Start gelesenen Kategorie-Logos nach
dem Uhrensprung zwoelf Stunden in der Vergangenheit - sie waren
schlagartig die aeltesten Dateien im ganzen Zwischenspeicher und flogen
als Erste raus. **Sie wurden weggeworfen, WEIL sie gerade benutzt
wurden.** Im Log des Nutzers stehen die beiden Zeilen Sekunden
auseinander:

    01:00:16  THUMB_CACHE Treffer: 6.3ms (ATARI2600.art, 304x792)
    12:48:33  PERF cover: 1732 ms (ATARI2600.art)

Test 4 stellt genau diesen Sprung nach. Test 1/2 pruefen das Aufraeumen
auf Vorrat (frueher: EIN Eintrag je Schreibvorgang, jeder mit einem
getmtime je Datei - im Gegentest 50 Verzeichnisdurchgaenge bei 50
Schreibvorgaengen, jetzt 4), Test 3 den Schutz der Kategorie-Logos,
Test 6 das Aufraeumen liegengebliebener .tmp-Dateien.

## test_kastenstufen.py

Der Nutzer beschrieb es so: "wenn das Miniaturen vorbereiten
durchgelaufen ist und ich gehe in irgendein System und blaettere durch
die ROMs, kommt es mir so vor, als wuerde das Frontend immer noch
nachjustieren."

Die Ursache: die Hoehe des Boxart-Kastens haengt am TEXT darunter, und
der aendert sich im Betrieb. Startet man ein Spiel zum ersten Mal, kommt
"Gespielt: 12min" als neue Zeile dazu, der Kasten wird um eine
Zeilenhoehe kleiner, der Cache-Schluessel ein anderer - und die beim
Vorbereiten berechnete Miniatur ist wertlos. Dasselbe bei
"Durchgespielt" und bei jeder Aenderung des RA-Fortschritts.
Nachgerechnet gab es bis zu ZWOELF verschiedene Kastenhoehen.

Der Test faehrt den kompletten Kombinationsraum ab (4 Titellaengen x 5
Metadaten-Staende x Spielzeit x Durchgespielt x RA-Fortschritt = 160
Faelle je Aufloesung) und prueft zwei Zusagen:

1. **Hoechstens drei Kastenhoehen** je Aufloesung. Gemessen: CRT
   63/114/165, 480p 279/314/349, HDMI 513/642/771.
2. **Der Text passt IMMER noch vollstaendig** (`cover_h + text_h + 8*s
   <= art_h`). Das ist die wichtigere Zusage - eine Stufung, die Text
   abschneidet, waere schlimmer als das Problem, das sie loest.

Dazu die Gegenprobe, die den eigentlichen Zweck festnagelt: die
"Gespielt"-Zeile, die beim ersten Start eines Spiels dazukommt, darf die
Kastenhoehe NICHT mehr veraendern.

## test_kein_systemhintergrund.py

Build 87 hat die System-Hintergrundbilder komplett entfernt
(Nutzerentscheidung: "grossen Systembildhintergrund komplett
rausnehmen, war eh bloede"). Sie hatten zwei Auftritte, und beide
kosteten Leistung:

1. **Bildschirmfuellend hinter der Spieleliste.** Der Puffer musste bei
   jedem Kategoriewechsel neu zusammengesetzt werden - bei 1920x1080
   8,3 MB, zeilenweise in Python, hier gemessene 41-67 ms und auf der
   MiSTer-CPU entsprechend mehr. Dazu hielt BgCache bis zu VIER solcher
   Vollbildpuffer, bei 1080p rund 33 MB Arbeitsspeicher.
2. **Klein in der Boxart-Spalte**, als Ersatz fuer ein fehlendes Cover.
   Das war mit 200-700+ ms je Skalierung die teuerste Einzeloperation
   im ganzen Frontend - und sie wurde von KEINEM Vorauslader erfasst.

Ein Loeschen quer durch vier Dateien laesst leicht einen Rest stehen,
und ein Rest waere hier heimtueckisch: er kostet nichts, bis ihn ein
spaeterer Umbau versehentlich wieder anschaltet. Der Test prueft
deshalb nicht das Aussehen, sondern die Abwesenheit:

- `fe/art.py` hat kein `BG_BASE`, `BgCache`, `BG` mehr, `fe/settings.py`
  kein `system_bg_enabled`/`toggle_system_bg`/`SYSTEM_BG_DISABLED_FLAG`,
  und im CODE von `frontend.py` (Kommentare ausgenommen, die erklaeren
  ja gerade die Entfernung) taucht keines der Muster mehr auf.
- Ein Eintrag OHNE Cover loest genau EINEN Bildversuch aus - den fuers
  Cover selbst. Frueher kam ein zweiter fuer das Hintergrundbild.
- Zwei Kategorien mit verschiedenem Systemkey haben denselben
  Hintergrund, und der stammt bitgenau aus der `fb.clear()`-Vorlage
  (`fb._rowcache`).
- Im kompletten Systemmenue-Baum (44 Eintraege) gibt es keinen Eintrag
  der Art `system_bg` mehr.

## test_pad_bedienung.py

Build 88 hat drei Dinge zusammengefasst, die alle denselben Ursprung
haben: durchgezaehlt waren FUENF Funktionen ausschliesslich ueber die
Tastatur erreichbar - Volltextsuche, Buchstabensprung, Zufallsspiel,
Durchgespielt-Markierung und der RA-Schaukasten. Am Pad belegt waren nur
A, B, X, Y, Start, Select, L/R, L2/R2 und Mode.

Freie Pad-Tasten gibt es keine mehr, deshalb ist SELECT jetzt ein
Modifikator. Das ist heikler, als es klingt: Select ALLEIN muss weiter
wie Zurueck wirken, darf aber bei einer Kombination NICHT zusaetzlich
ein "zurueck" mitschicken - sonst landet man nach jeder Suche eine
Ebene hoeher. Geloest, indem "select" erst beim LOSLASSEN gemeldet wird
und nur dann, wenn zwischendurch keine Kombination ausgeloest hat.
Genau das prueft Test 1 und 2.

Test 3 nagelt fest, dass die Kombination an der ZIELAKTION der zweiten
Taste haengt und nicht an deren Tastencode - wer sich ueber
"Tastenbelegung anpassen" eine eigene Belegung eingerichtet hat, behaelt
die Kombination sonst nicht.

Test 4 deckt den Fall ab, der im Alltag am ehesten nervt: ein Funkpad
verliert die Verbindung, waehrend Select gehalten wird. Ohne das
Aufraeumen in rescan() waere Select fuer den Rest der Sitzung
"gehalten", und jedes A waere eine Suche.

Test 5/6 der Buchstabenwaehler: das Raster ist vollstaendig, die letzte
Zeile ist kuerzer als die anderen (36 Zeichen + 3 Sondertasten bei 7
Spalten), und keine Bewegung von keinem Feld aus darf ins Leere zeigen.
Test 6 zeichnet ihn in allen drei Aufloesungen - der Framebuffer der
Attrappe ist genau so gross wie der echte, ein Zeichnen ausserhalb
fliegt dort auf.

Test 8 prueft die Hilfe gegen die Wirklichkeit: jeder in section_keys
aufgefuehrte Eintrag muss in BEIDEN Sprachen existieren, F10 darf nicht
mehr als Ausstieg genannt werden (seit Build 77 ersatzlos entfallen),
F1 muss drinstehen, und die F5-Reset-Beschreibung darf keine Haltezeit
mehr nennen (RESET_HOLD ist seit Build 75 auf 0.0). Genau solche
stehengebliebenen Angaben waren der Anlass: "die Hilfe muss eh
ueberarbeitet werden, da stehen Sachen drin die sind nicht mehr
aktuell."

## test_ruhige_boxspalte.py

Vier Rueckmeldungen in einer Nachricht, alle zur Boxart-Spalte.

**Das Aufblitzen.** "Wenn ich durch die ROMs scrolle, etwas langsamer,
ploppt immer erst 'kein Artwork' auf und dann wird das Cover
nachgeladen." Ursache: `get_scaled()` liefert `None` fuer ZWEI voellig
verschiedene Faelle - "es gibt kein Cover" und "ich habe es waehrend des
Scrollens bewusst uebersprungen, es kommt in rund 150 ms"
(COVER_SETTLE, siehe `_defer_uncached` in `fe/art.py`). Der Zeichenpfad
konnte die beiden nicht unterscheiden und malte auch im zweiten Fall den
Platzhalter. Ein Zaehler (`ART._defer_count`) trennt sie jetzt: der
Aufrufer merkt sich den Stand davor und vergleicht.

Test 1 prueft beide Richtungen - wirklich kein Cover MUSS den
Platzhalter zeigen, nur verzoegert darf ihn NICHT zeigen. Test 2
sichert die Voraussetzung dafuer ab: der Zaehler muss an ALLEN drei
Defer-Stellen stehen. Ohne diese Pruefung wuerde Test 1 eine Zusage
pruefen, die er sich selbst nachgestellt hat.

**Der blaue Block.** Der Platzhalter war eine vollflaechig gefuellte
Flaeche in der Akzentfarbe, so gross wie das Cover geworden waere - auf
HDMI gut eine halbe Million Bildpunkte, bei jedem Eintrag ohne Cover neu
gefuellt. Jetzt ein duenner Rahmen. Test 3 zaehlt die gefaerbten
Bildpunkte im Kasten und vergleicht sie mit dem Umfang statt der
Flaeche: gemessen 8.772 statt 537.387 auf HDMI, also rund ein
Einundsechzigstel.

**Keine Spalte bei reinen Ordnerlisten.** Ordner haben praktisch nie ein
eigenes Cover; die Spalte zeigte dort fast immer nur den Platzhalter und
nahm der Liste dafuer knapp die Haelfte der Breite weg. Test 4 deckt die
Faelle ab, in denen die Spalte trotzdem bleiben MUSS - gemischte Ebenen
(Ordner und Spiele nebeneinander) und "Zuletzt gespielt" (syskey=None,
aber echte Spiele). Und er prueft, dass die Bedingung nur noch an EINER
Stelle steht: laufen die drei Aufrufer auseinander, berechnet der
Vorauslader Miniaturen unter einer Kastengroesse, die der Zeichenpfad
nie abfragt.

**Positionsgedaechtnis je Kategorie.** Fuer Unterordner gab es das
laengst (`_nav_position_stack`), eine Ebene hoeher nicht. Test 5 prueft
den Normalfall und die beiden Faelle, in denen ein gemerkter Index
schlimmer waere als keiner: eine kuerzer gewordene Liste und ein
Neu-Einlesen (nach dem sich auch die Kategorie-Nummerierung verschieben
kann).

## test_hinweisbox_flackern.py

Ein Flackern, das der Nutzer per Video gemeldet hat ("das kommt bei
einigen Einstellungen wenn man was veraendert"). Bild fuer Bild
ausgewertet (1920x1080, 60 Bilder/s): die Hinweisbox verschwand **6 mal
pro Sekunde fuer genau zwei Bilder** (33 ms).

Ursache: `draw()` brachte die Seite mit `flip=True` auf den Schirm und
zeichnete die Box ERST DANACH (mit eigenem `flip_rows()` nur ueber das
Box-Band). Zwischen beidem liegt das Rendern der Box - und genau so
lange zeigt der Bildschirm die fertige Seite ohne Box. Der 6-Hz-Takt kam
von der Laufschrift (0.18 s), die wegen `_overlay_active()` bewusst auf
den vollen `draw()` faellt.

Bemerkenswert: der Kommentar bei `any_dialog` in `draw()` beschrieb
diesen Fehler bereits woertlich ("sonst blitzt fuer einen Frame der
Hintergrund ohne Dialog auf") - er war nur fuer die beiden
Bestaetigungsdialoge behoben worden. Die Hinweisbox kam spaeter dazu und
wurde in der Aufzaehlung vergessen.

Geprueft wird deshalb nicht das Aussehen, sondern die **Reihenfolge der
Flips**: solange die Box aktiv ist, darf es pro Aufbau genau EINEN Flip
geben, und der muss NACH dem Zeichnen der Box kommen und ein Vollbild
sein. Test 5 sichert eine Feinheit ab, die beim Bauen auffiel:
`_overlay_active()` prueft die Uhr und darf deshalb pro Aufbau nur
EINMAL ausgewertet werden - liefe die Box genau zwischen zwei Aufrufen
ab, waere der Seiten-Flip unterdrueckt UND die Box nicht gezeichnet, das
Bild bliebe stehen.

## test_vsync_und_wiederholrate.py

Die beiden Latenz-Aenderungen aus Build 93. Beide gehen auf denselben
Satz zurueck: "Ich habe schnelles Scrollen eigentlich standardmaessig
an - und das fuehlt sich manchmal komisch an."

**Das Vsync-Auslassen war zu grob.** Es galt bis Build 92 pauschal fuer
JEDE Kopie, sobald der Schalter an war und gerade gescrollt wurde. Ein
Bildriss in einem zwei Zeilen hohen Streifen sieht niemand - derselbe
Riss quer durch ein 1080-Zeilen-Bild sieht jeder. Ab Build 93
entscheidet zusaetzlich die GROESSE des Bandes
(`VSYNC_SKIP_MAX_ANTEIL`, `Frontend._vsync_ueberspringen()`): bis 25 %
der Bildhoehe wird uebersprungen, darueber und bei jedem Vollbild wird
gewartet.

Test 3 ist der wichtigste: er prueft nicht die Schwelle an sich,
sondern dass die tatsaechlich GEMESSENEN Bandhoehen weit von ihr
entfernt liegen - leichter Pfad 11-13 % der Bildhoehe, voller Aufbau
81-84 %. Es gibt also keinen Grenzfall, der bei einer kleinen
Layout-Aenderung zufaellig auf die andere Seite kippt. Test 14 ist der
Regressionsschutz gegen ein versehentliches Zurueckrutschen auf den
alten, pauschalen Aufruf - und prueft zugleich, dass
`_scroll_skip_vsync()` NICHT verschwindet: es beantwortet weiterhin die
andere Frage ("wird gerade schnell gescrollt?") fuer die beiden
Entscheidungen, die gar nichts kopieren.

**Die Wiederholrate war geraten.** Feste 0.08 s bedeuten 12,5
angeforderte Schritte pro Sekunde - unabhaengig davon, ob ein Aufbau
3 ms kostet (CRT, leichter Pfad) oder 110 ms (HDMI, voller Aufbau mit
Cover). Beides ist falsch: im ersten Fall unnoetig traege, im zweiten
kommen mehr Schritte herein als gezeichnet werden koennen. Der
Ueberschuss verschwindet nicht, er staut sich - und der Stau ist genau
das, was man als Lag wahrnimmt. `zeichenzeit_melden()` bekommt die
tatsaechliche Dauer aus `run()` (dieselben Zeitstempel, die der
Ruckler-Detektor ohnehin nimmt - keine einzige zusaetzliche
Zeitabfrage), `_repeat_floor()` leitet den Boden daraus ab.

Test 9 sichert eine bewusste Asymmetrie ab: hoch/runter darf durch die
Messung schneller werden, links/rechts nicht. Bei einem Seitensprung
ist nicht die Rechenzeit die Grenze, sondern das Lesen - schnellere
Hardware aendert daran nichts. Die Tests 10 bis 12 decken ab, was
schiefgehen kann, wenn man eine Regelgroesse aus Messwerten ableitet:
Deckel nach oben, Verwerfen von Unsinn (Uhrensprung, ein
zwischendurch gestartetes Spiel), und Traegheit gegen einen einzelnen
Ausreisser.

## test_ra_einstellungen.py

Die RA-Einstellungen der MiSTer-Hauptanwendung, bedienbar aus unserem
System-Menue (Build 95).

**Was hier auf dem Spiel steht.** `/media/fat/retroachievements.cfg`
gehoert NICHT uns. Darin stehen die RA-Zugangsdaten des Nutzers
(Benutzername UND Passwort), moeglicherweise Kommentare, und in einer
kuenftigen MiSTer-Version Schluessel, die es heute noch nicht gibt. Ein
Fehler in `fe/ra_settings.py` kostet nicht ein falsches Pixel, sondern
im schlimmsten Fall den Zugang zu RetroAchievements. Deshalb prueft
Test 1 als erstes und wichtigstes, dass nach einer Aenderung **genau
eine Zeile weg und eine dazugekommen** ist - und zwar die gemeinte.

Die uebrigen Tests decken die Faelle ab, in denen ein naiver
INI-Editor still etwas kaputtmacht:

- **Test 2** - eine auskommentierte Zeile (`#multiline_desc=1`) darf
  nicht als gesetzter Wert gelten und nicht wiederbelebt werden.
- **Test 3** - ein NEUER globaler Wert muss VOR dem ersten
  `[Abschnitt]` landen. Am Dateiende angehaengt stuende er hinter
  `[Gameboy]` und waere damit plötzlich ein Gameboy-Wert.
- **Test 9** - Zuruecksetzen entfernt nur unsere drei Pro-Core-Werte
  und laesst fremde Schluessel im selben Abschnitt stehen.
- **Test 10** - fehlt die Datei, wird sie NICHT angelegt. Sie enthaelt
  Zugangsdaten; eine von uns erzeugte Datei ohne Benutzername waere
  fuer MiSTer wertlos.
- **Test 14** - der gefaehrlichste denkbare Fehler: es gibt ZWEI
  Dateien namens `retroachievements.cfg` (unsere unter
  `/media/fat/frontend/` mit Benutzername + Web-API-Schluessel, MiSTers
  unter `/media/fat/` mit Benutzername + Passwort). Geprueft wird, dass
  die Pfade verschieden sind und `ra_settings.py` nichts aus
  `retroachievements.py` importiert.

**Test 11** haelt eine Eigenart fest, die leicht zu uebersehen ist:
MiSTer legt seine Werte pro CORE ab, nicht pro System. Game Boy und
Game Boy Color benutzen denselben Core ("Gameboy"), SNES und SMW Hacks
ebenfalls ("SNES") - eine Aenderung gilt also zwangslaeufig fuer beide.
Der Bildschirm muss das auch dazusagen.

**Test 12** zeichnet den Bildschirm wirklich, in beiden Aufloesungen.
Zwei Layout-Fehler waren nur so zu finden und sind beide im gerenderten
PNG aufgefallen, nicht im Quelltext: auf CRT frass das lange deutsche
Label den WERT auf ("Bestenlisten-Aktualisierungen: ~" - ausgerechnet
die Information, um die es geht), und die Bedienzeile wurde mitten im
Wort abgeschnitten. Werte stehen jetzt rechtsbuendig und bekommen ihren
Platz zuerst; von der Bedienzeile gibt es drei Laengen.

## Scroll-Blitting (entfernt in Build 102)

Hier standen `test_scroll_blitting.py` und `bench_scrollblit.py`. Die
Idee aus Build 96: sobald die Markierung den Listenrand erreicht hat,
ist jeder weitere Schritt ein kompletter Seitenaufbau - statt ihn zu
bauen, den schon gezeichneten Block um eine Zeilenhoehe im Speicher
verschieben und nur die vier wirklich geaenderten Zeilen neu zeichnen.

**Der Test prüfte nicht die Geschwindigkeit, sondern das Bild**, und
genau das war seine Berechtigung: er hat zwei Fehler gefunden, die man
beim Lesen des Codes nicht sieht - eine falsche Aufrufreihenfolge
(`draw_art_panel()` reicht drei Bildzeilen in die Fusszeile hinein) und
die Zwischenraeume zwischen den Zeilen (`draw_list_row()` raeumt nur
39 von 45 Bildzeilen auf, im Rest stand nach dem Verschieben der
Nachbar).

**Der Benchmark hat den Pfad dann erledigt.** Nachgemessen in allen
drei Aufloesungen kostet das Verschieben mehr, als es spart:

| Aufloesung | voll | geblittet | Faktor |
|---|---|---|---|
| CRT 320x240 | 0.50 ms | 0.65 ms | 0.8x |
| 720p 1280x720 | 1.25 ms | 1.63 ms | 0.8x |
| HDMI 1920x1080 | 2.04 ms | 2.84 ms | 0.7x |

Beide Wege kopieren am Ende dieselbe Flaeche. Das Verschieben spart das
Setzen der Schrift, zahlt die Kopie aber ZUSAETZLICH zu den vier neu
gezeichneten Zeilen und den beiden wiederhergestellten Raendern. Damit
ist die Bedingung eingetreten, unter der der Pfad von Anfang an stand
("bestaetigt sich die Messung, gehoert der ganze Pfad geloescht") - er
ist mitsamt Schalter, Menuepunkt und flachem Vignetten-Band raus.

## test_cover_panel.py

Der Schlagschatten des Cover-Panels (Build 97). Die Messung aus
Build 96 hatte gezeigt, dass beim Scrollen auf HDMI nicht die
Listenzeilen die Zeit kosten, sondern das Cover-Panel - und dort war
der GROESSTE Einzelposten der Schatten.

Er wurde als vollstaendiger abgerundeter Kasten in Kartengroesse gemalt
und die Karte direkt danach darueber. Auf 1080p sind das 769x945 =
726.705 Bildpunkte, von denen **15.210 (2,1 %) jemals zu sehen sind**.
Gemessen 0,461 ms pro Panel-Aufbau, also 35 % des gesamten Panels, fuer
Bildpunkte, die im selben Atemzug wieder verschwinden.

**Die Anforderung ist hart: bitgenau dasselbe Bild.** Der Schatten ist
ein rein optisches Detail - waere er hinterher auch nur an einer Ecke
anders, waere das eine Verschlechterung fuer einen Gewinn, den niemand
sieht. Der Test rechnet deshalb nichts nach, sondern stellt den ALTEN
Weg gegen den NEUEN: derselbe Puffer, einmal volles Schattenrechteck
plus Karte, einmal verkuerzter Schatten plus Karte. Byte fuer Byte.

Zwei Fallen, beide vom Test gefunden:

1. **Der Bildrand.** `rect_rounded()` beschneidet Breite und Hoehe am
   Bildrand ZUERST und rundet danach - eine abgeschnittene Karte
   bekommt also eine ANDERE Rundung als eine freistehende. Die erste
   Fassung bildete das nicht nach und malte am Rand einen anders
   geformten Schatten.
2. **Zu clever ist langsam.** Die erste Fassung rechnete jede Bildzeile
   einzeln aus. Korrekt, aber gemessen VIERMAL LANGSAMER als das volle
   Rechteck, das sie ersetzen sollte - neunhundert Einzelzuweisungen
   schlagen jede eingesparte Flaeche. Jetzt geht der gerade Mittelteil
   in EINEM rect()-Aufruf weg, einzeln gerechnet wird nur an den Ecken.

Build 98 kam ein zweiter Schritt dazu: Karte und Schatten liegen in den
geraden Mittelzeilen direkt NEBENEINANDER und werden seitdem in EINER
Zuweisung geschrieben statt in zwei Zeilenschleifen ueber dieselben 900
Bildzeilen. Test 2b haelt auch das bitgenau fest - inklusive der Faelle,
in denen es NICHT zusammengefasst werden darf (Beschnitt am Bildrand,
Versatz groesser als der Radius).

Test 4 misst beide Schritte mit: eine Aenderung, die nur theoretisch
spart, hat hier nichts verloren. Abwechselnd im selben Lauf gemessen
ergab das auf HDMI 1,155 -> 0,844 ms (-27 %), auf CRT -3 %.

## test_bildrand.py

Der Bildrand (`OVERSCAN_X` / `OVERSCAN_Y`) stand bisher als feste Zahl
im Quelltext. Seit Build 113 laesst er sich im Menue einstellen -
uebernommen von Degauss, wo das ebenfalls moeglich ist. Auf HDMI
braucht das kaum jemand; auf einer Roehre schon, denn jede schneidet
anders ab.

Der Knackpunkt: die beiden Werte werden an SECHSUNDZWANZIG Stellen als
`W * OVERSCAN_X // 100` gelesen. Sie alle auf ein Objektfeld
umzustellen waeren sechsundzwanzig Gelegenheiten, ein Layout zu
verschieben. Stattdessen ueberschreibt `_overscan_anwenden()` die
Modul-Variablen - dieselbe Wirkung, ohne eine einzige dieser Zeilen
anzufassen.

Test 5 ist deshalb der eigentliche Test: er misst nicht die
Einstellung, sondern das Bild. Bei 2 % gegen 10 % muessen auf CRT UND
HDMI sowohl die Hauptseite (`layout_cats`) als auch die Spieleliste
(`layout_items`) einruecken, und zwar auf genau die eingestellten
Prozent und auf beiden Seiten.

Die uebrigen Pruefungen: ohne gespeicherten Wert gilt weiterhin 7/5
(wer nichts einstellt, bekommt exakt das Bild von vorher); eine von
Hand verstellte oder kaputte Datei faellt auf die Vorgabe zurueck statt
ein unbedienbares Menue zu erzeugen; das Weiterschalten laeuft durch
alle Stufen und dreht um; und der Layout-Zwischenspeicher wird beim
Umschalten geleert - ohne das bliebe die alte Aufteilung stehen und die
Einstellung waere sichtbar wirkungslos.

## test_suchtreffer.py

Deckt zwei Aenderungen aus Build 114 ab, die dieselbe Frage
beantworten - wo bin ich gerade?

**Die Positionsanzeige** ("142/3500" rechts in der Fusszeile). Getestet
wird nicht die Zeichenkette, sondern das Bild, auf CRT und HDMI. Zwei
Punkte, die man leicht uebersieht:

- Das Feld wird nach der GESAMTZAHL bemessen, nicht nach der gerade
  angezeigten Zahl. Sonst bliebe beim Wechsel von "1420/3500" auf
  "999/3500" die letzte Ziffer der laengeren Zahl stehen.
- Test 6 ist der eigentliche Test: die Zahl aendert sich bei genau dem
  Schritt, den der LEICHTE Zeichenpfad bedient. Stuende sie nur im
  vollen Aufbau, zeigte sie beim Durchblaettern dauerhaft etwas
  Veraltetes. Geprueft wird deshalb ueber fuenf Schritte hinweg
  bitgenau gegen den vollen Aufbau.

**Der Trefferwechsel** (hoch/runter blaettert durch die Suchtreffer,
der Balken zaehlt mit). Hier liegt das Risiko in der Leistung: die
Zaehlung muss die GANZE Liste normalisieren, statt beim ersten Treffer
aufzuhoeren. Ueber 12.605 Namen waren das 21,8 ms pro Tastendruck - auf
der MiSTer-CPU unbenutzbar. Die Abkuerzung fuer reines ASCII
(`unicodedata.normalize()` ist dort die Identitaet, uebrig bleibt
`.lower()`) bringt das auf 1,6 ms.

Test 1 weist die Gleichwertigkeit ueber alle 128 ASCII-Zeichen plus
3000 Zufallstexte mit Umlauten und CJK nach - dieselbe Beweisform wie
beim Cover-Index in Build 110, weil auch hier eine Abkuerzung eine
korrekte Funktion ersetzt. Test 2 vergleicht den neuen Sprung ueber
1000 Zufallsfaelle gegen die alte `jump_to_substring()`: die Suche
muss sich nach dem Umbau genauso verhalten wie vorher. Test 8 misst
nach, dass die Abkuerzung ueberhaupt etwas bringt - ohne diese Messung
waere Test 1 nur eine Gleichheitsaussage ueber zwei Funktionen, von
denen eine grundlos existiert.

## test_cover_original.py

Drei Aenderungen aus Build 119, die nur gemeinsam haben, dass sie aus
derselben Rueckmeldungsrunde stammen.

**Cover im Original ablegen.** Der Download wandelt nicht mehr in
`.art` um, sondern legt PNG/JPG unveraendert ab. Der Knackpunkt ist
nicht das Ablegen, sondern das WIEDERFINDEN: der Cover-Index kannte bis
dahin nur `.art` - ohne die Erweiterung laege die Datei auf der Karte
und wuerde nie gefunden. Geprueft wird deshalb beides, und dazu die
Reihenfolge (liegt beides, gewinnt `.art` - schon verkleinert, also
billiger), die Endung nach INHALT statt nach Servername, und dass ein
zweiter Durchlauf nichts doppelt laedt.

**Die Enter-Taste.** Der Schalter "Bestaetigen/Abbrechen vertauschen"
lief ueber die ganze Tastenbelegung. Auf der Tastatur ist Enter die
einzige Taste mit "ok" und es gibt dort gar keine mit "back" - nach dem
Umschalten hatte die Tastatur also ueberhaupt keine Bestaetigungstaste
mehr. Geprueft wird, dass Tastatur und Start unangetastet bleiben, A
und B dagegen wirklich tauschen, und dass zweimaliges Anwenden weiterhin
den Ausgangszustand herstellt - darauf baut das Umschalten im Menue.

**Die USB-Wartezeit.** Geprueft wird nicht nur die Zahl, sondern auch,
dass sie NUR in dem einen Fall greift, in dem der Cache USB-Ordner
erwartet und gerade keine da sind - der allgemeine Fall wartet
weiterhin kurz, sonst wuerde jeder Start ohne Not haengen.

## test_verkleinern.py

Nach Build 115 und 116 war das Verkleinern der ganze Rest: von einem
kalten Cover auf HDMI entfielen **97 von 101 ms** darauf. Gemessen
steckten 73 % davon in der inneren Summenschleife, 19 % in den
Divisionen.

Der Gewinn kommt aus einer einzigen Beobachtung. Bei einer
Verkleinerung schwaecher als 3:1 - und genau das ist der HDMI-Fall,
424x768 in einen 360x420-Kasten sind Faktor 1,8 - entsteht jede
Zielspalte aus hoechstens ZWEI Quellspalten. Ein `sum()` auf einem
Ausschnitt von zwei Werten kostet dann mehr als die zwei Werte selbst:
der Ausschnitt muss angelegt, der Aufruf gemacht werden.

| | vorher | nachher |
|---|---|---|
| HDMI, Faktor 1,8 | 98,8 ms | **45,4 ms** |
| genau halb | 21,2 ms | **10,0 ms** |
| CRT, Faktor 5 | 38,4 ms | 34,9 ms |

Der letzte Fall laeuft weiter ueber den allgemeinen Weg (drei
Quellspalten und mehr) und hat nur den Feinschliff bekommen:
Kanalebenen statt Ausschnitten mit Schrittweite 4, und die Zielzeile
per Ausschnitt-Zuweisung statt Bildpunkt fuer Bildpunkt.

**Was der Test beweisen muss, ist nicht das Tempo, sondern die
Gleichheit.** Eine Abweichung faellt nicht auf - sie sitzt einfach fuer
immer in den vorberechneten Miniaturen auf der Karte, gemischt mit den
alten. Der Test traegt deshalb eine wortgleiche Kopie der alten Fassung
und vergleicht ueber 120 Zufallsgroessen, dieselbe Beweisform wie beim
Cover-Index in Build 110. Test 3 zielt eigens auf den Sprung zwischen
schnellem und allgemeinem Weg - dort entscheidet sich, welcher genommen
wird, und genau an solchen Grenzen laufen zwei Fassungen auseinander.

## test_namensabgleich.py

Zwei Aenderungen aus Build 117, die aus DERSELBEN Ursache kamen: der
Nutzer hat eine andere USB-Festplatte angeschlossen.

**Der Namensabgleich.** Gemeldet als "bei N64 und Sega 32X werden mir
keine Boxarts mehr angezeigt" - das sah nach einem Fehler in einem der
letzten Builds aus, war aber keiner. Die ROMs auf der neuen Platte
tragen die alte GoodTools-Schreibweise, die heruntergeladenen Cover die
No-Intro-Schreibweise:

    007 - The World is Not Enough (U) [!]        (ROM)
    007 - The World Is Not Enough (USA).art      (Cover)

Zeichenweise passt davon nichts zusammen, nicht einmal "is" gegen "Is".
`vergleichsname()` wirft alles in Klammern weg und behaelt nur
Buchstaben und Ziffern in Grossschreibung - beide werden damit zu
`007THEWORLDISNOTENOUGH`.

Dasselbe gilt fuer die fremde Datenbank aus Build 115: sie ist
durchgehend No-Intro benannt. Ohne den Abgleich haette jemand 21.198
Cover auf der Karte, von denen keines gefunden wird.

Getestet wird an den ECHTEN Namenspaaren vom Geraet - und in die
Gegenrichtung: "Super Mario 64" darf nicht auf "Super Mario World"
treffen, "Mortal Kombat" nicht auf "Mortal Kombat II". Dazu, dass der
exakte Name immer gewinnt und dass bei mehreren gleichwertigen
Kandidaten stabil derselbe genommen wird (`os.listdir()` liefert keine
verlaessliche Reihenfolge).

**Das Nachzieh-Netz.** Gemeldet als "bei jedem Frontendstart wird
versucht, die Spieleliste neu aufzubauen, ich muss immer erst unter
Wartung von Hand neu einlesen" - die neue Platte laeuft langsamer an.
Dafuer gab es schon ein Sicherheitsnetz, es sah aber nur nach
NETZLAUFWERKEN, weil es fuer einen NAS-Nutzer gebaut wurde.

`ordner_sind_dazugekommen()` fragt jetzt allgemein, ob es Spieleordner
gibt, die es beim letzten Einlesen noch nicht gab. Geprueft wird
besonders, was NICHT ausloesen darf: ein geaenderter Zeitstempel (der
passiert im Alltag staendig und wuerde das Netz in einen Dauerscanner
verwandeln), ein weggefallener Ordner, und der allererste Start ohne
vorheriges Einlesen. Ausserdem, dass die Zwischenfrage den NAS-Merker
nicht ueberschreibt - er beschreibt das letzte echte Einlesen.

## test_bildlib.py

Deckt Build 115 ab: die Systembibliotheken `libpng16` und
`libturbojpeg`, die auf dem MiSTer liegen - nur eben weder als
Python-Modul noch als Kommandozeilenwerkzeug, weshalb mehrere Suchen
daran vorbeigingen. Ueber `ctypes` sind sie erreichbar.

Der Unterschied ist kein Feinschliff. Unser eigener PNG-Dekoder in
Python braucht fuer ein 400x560-Cover **210 ms**, libpng **2,6 ms** -
Faktor 80 hier, auf dem Geraet 200-500 ms gegen grob 30. Genau diese
Zahl ist der Grund fuer den Vorauslader im zweiten Prozess (Build
104), die Notbremse nach zwei Sekunden (Build 105) und das Auslagern
kalter Cover (Build 107).

Zwei Fragen muss der Test beantworten:

**Liefert die Bibliothek wirklich dasselbe Bild?** Ein Unterschied
faellt nicht auf, er zeigt nur irgendwann ein falsches Cover. Geprueft
wird deshalb bitgenau ueber RGB, RGBA, Graustufen und Palette - und in
die Gegenrichtung an einem echten Adam7-verschachtelten PNG, das
unserer gar nicht kann. Dieselbe Beweisform wie beim Cover-Index in
Build 110. Das verschachtelte Testbild steht als Konstante im Test,
weil Pillow keins schreiben kann und der Test nicht von einem
zufaellig installierten ImageMagick abhaengen soll.

**Kann die Aenderung etwas verschlechtern?** Test 3 schaltet die
Bibliothek kuenstlich ab und prueft, dass trotzdem dasselbe Bild
herauskommt - fehlt sie auf einem Geraet, uebernimmt der bisherige
Dekoder unveraendert.

Dazu die fremde Quelle unter `/media/fat/docs`: der Ordner wird sowohl
ueber den Systemschluessel als auch ueber die Core-Namen aus unserer
Systemliste gefunden (Mega Drive heisst dort `MegaDrive`), eigenes
Artwork behaelt immer Vorrang, eigene Spieledaten auch - die fremde
Tabelle fuellt nur Luecken und steuert das Feld bei, das unsere
libretro-Quelle nie hatte (den Entwickler). Kaputte Zeilen, leere
Felder und eine fehlende Datenbank duerfen nichts umwerfen.

Laeuft auch auf einem Rechner ohne diese Bibliotheken - die
betroffenen Pruefungen melden sich dann ausdruecklich als "nicht
pruefbar", statt stillschweigend zu bestehen.

**Test 12 und 13 kamen mit Build 116 dazu** und decken den Fehler ab,
der Build 115 fast wertlos gemacht haette: `prewarm_thumb()` kannte nur
das eigene `.art`-Format und gab bei einem JPG "fehler" zurueck. Die
21.198 neuen Cover wurden von "Miniaturen vorbereiten" also komplett
uebergangen - jedes einzelne musste der Zeichenpfad rechnen, wieder und
wieder. Test 12 prueft jetzt fuer PNG UND JPG, dass Vorbereitung und
Zeichenpfad **bitgenau dasselbe** Bild ergeben, in beiden
Kastengroessen. Dazu, dass `zielmass()` dieselben Masse liefert wie die
Rechnung vor Build 116 - sonst passten alte Miniaturen nicht mehr zu
neuen.

Test 13 prueft das verkleinerte Dekodieren: kleiner als die Datei, aber
nie unter die Zielgroesse; ohne Kastenangabe weiterhin volle Groesse;
und ein einmal klein gelesenes Bild darf einem groesseren Kasten nicht
untergeschoben werden.

## diag_kaltes_cover.py

DIAGNOSE, kein Pass/Fail-Test. **Laeuft auch auf dem MiSTer selbst** -
dort ist die Messung, auf die es ankommt.

Entstanden aus einer Vermutung, die sich als falsch herausstellte: nach
Build 115 lag nahe, die Schutzschwellen aus den Builds 105 und 107
seien jetzt zu vorsichtig, weil das Dekodieren um ein Vielfaches
schneller geworden ist. Die Messung zeigte etwas anderes - ein kaltes
Cover besteht aus zwei Teilen, und nur einer war schneller geworden:

| | vorher | nach Build 115 |
|---|---|---|
| dekodieren | 341,8 ms | 3,5 ms |
| auf Kastengroesse verkleinern | 97,7 ms | 97,7 ms |

Damit sind es **97 % der Wartezeit auf HDMI und 91 % auf CRT**, die auf
die Flaechenmittelung entfallen. Ein Lockern der Schwellen haette also
nicht das Warten beendet, sondern das Ruckeln zurueckgebracht.

Das Skript misst genau diese Aufteilung an ECHTEN Covern der jeweiligen
Karte (`art_hd`, `art`, `docs`) und geht dabei durch denselben Weg wie
der Zeichenpfad - einschliesslich des verkleinerten Dekodierens aus
Build 116. Auf einem Rechner ohne diese Ordner erzeugt es sich Cover in
typischer Groesse, damit die Aufteilung trotzdem sichtbar wird.

Die Faustregel steht am Ende der Ausgabe: **steht "verkleinern" ueber
der Haelfte, muss das Verkleinern billiger werden, nicht die Schwelle
groesser.**

## diag_lightpath.py

DIAGNOSE, kein Pass/Fail-Test. Prueft die zentrale Annahme hinter dem
schnellen Zeichenpfad: ein Einzelschritt bzw. ein Puls-Tick muss dasselbe
Bild hinterlassen wie ein VOLLER Neuaufbau desselben Zustands.

Aktueller Stand seit Build 114: **0 von 34 Faellen weichen ab.**

Das war jahrelang anders. Die Fallzahl allein taeuschte dabei: als der
Vignette-Fehler in `draw_list_row()` behoben wurde (siehe CHANGELOG,
Build 64), fiel sie nur von 24 auf 22 - im direkt nachgemessenen
Scroll-Versuch fielen die abweichenden BILDPUNKTE dagegen von 2.785 auf
107 (CRT) bzw. von 105.717 auf 2.190 (HDMI). Deshalb gibt das Skript
beide Zahlen aus.

Der REST (22 Faelle, rund 25.000 Bildpunkte) galt als „bekannt, auf
echter Hardware nicht sichtbar, nicht aufgeklaert" und lag laut
damaliger Notiz „fast alle auf einer einzigen Bildzeile am unteren Rand
der Boxart-Karte". Das war naeher dran, als es klang: der Schlagschatten
der Boxart-Karte reicht drei Bildzeilen weit in das Fussband hinein. Der
volle Aufbau raeumt das hinterher weg (`_fusszeile_zeichnen()` stellt
das ganze Band wieder her), der leichte Pfad fasste die Fusszeile gar
nicht an - dazu kam die stehengebliebene Laufschrift. Seit der leichte
Pfad die Fusszeile mitnimmt (Build 114, noetig fuer die
Positionsanzeige), sind beide Ursachen weg und der Vergleich ist
bitgenau.

**Damit ist das Skript zu einem echten Pass/Fail-Kandidaten geworden** -
bewusst noch nicht umgestellt: eine Null will erst ein paar Builds lang
halten, bevor man den Regressionslauf davon abhaengig macht. Es liefert
weiterhin immer den Rueckgabewert 0 und dient als Messinstrument:

> WEDER die Zahl der Faelle NOCH die Zahl abweichender Bildpunkte darf
> bei Aenderungen am Zeichenpfad steigen - die zweite ist dabei die
> aussagekraeftigere. Seit Build 114 heisst das: beide muessen 0
> bleiben.

Vor und nach einer Aenderung ausfuehren und BEIDE Zeilen
(`Abweichungen` und `Abweichende Punkte`) vergleichen.
