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
  && python3 tools/test_f4_hotkey.py \
  && python3 tools/test_autostart.py \
  && python3 tools/test_rom_filter.py \
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
| `test_f4_hotkey.py` | Test (Pass/Fail) | F4-Schnellstart: Tastenerkennung, Sicherungen, Installation |
| `test_autostart.py` | Test (Pass/Fail) | Autostart-Schalter: user-startup.sh sicher aendern |
| `test_rom_filter.py` | Test (Pass/Fail) | ROMs verschwinden nicht mehr stillschweigend aus der Liste |
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

## test_f4_hotkey.py

Prueft den F4-Schnellstart (Nutzerwunsch: "koennen wir das Script
Frontend_Start.sh, wenn einer kein Autostart eingerichtet hat, irgendwie
auf F4 im OSD einbinden?").

Ein Hintergrundprozess, der beim Booten startet und Tastendruecke
mitliest, ist die heikelste Art von Zusatz in diesem Projekt: er laeuft,
wenn niemand hinsieht, und ein Fehler faellt erst auf, wenn das Geraet
sich seltsam verhaelt. Entsprechend wird nicht nur der Gutfall geprueft,
sondern vor allem, dass er in allen anderen Lagen NICHTS tut.

Die Tastenerkennung laeuft ueber eine Pipe als Ersatz-Eingabegeraet -
gefuettert mit exakt dem Byte-Format, das der Linux-Kernel auf
`/dev/input/event*` liefert. Abgedeckt: Tastencode gegen die
Systemkopfdatei `input-event-codes.h` geprueft, Loslassen und Halten
loesen NICHT aus, andere Tasten und andere Ereignistypen loesen NICHT
aus, ein abgeschnittenes Ereignis stuerzt nicht ab; `/tmp/CORENAME` mit
Nullbytes/CR/Leerzeichen wird korrekt als "Menue" erkannt (genau daran
ist frueher schon einmal etwas gescheitert); verwaiste und unlesbare
Sperrdateien; der Wrapper startet ohne Schalterdatei nichts und der
Not-Aus schlaegt den Schalter; und Installation, Update und
Deinstallation greifen ineinander (der Eintrag in `user-startup.sh`
wird nicht doppelt gesetzt und bei der Deinstallation wieder entfernt).

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

## diag_lightpath.py

DIAGNOSE, kein Pass/Fail-Test. Prueft die zentrale Annahme hinter dem
schnellen Zeichenpfad: ein Einzelschritt bzw. ein Puls-Tick muss dasselbe
Bild hinterlassen wie ein VOLLER Neuaufbau desselben Zustands.

Aktueller Stand: **22 von 34 verglichenen Faellen weichen ab**, zusammen
rund 28.000 Bildpunkte.

Die Fallzahl allein taeuscht: als der Vignette-Fehler in
`draw_list_row()` behoben wurde (siehe CHANGELOG, Build 64), fiel sie
nur von 24 auf 22 - im direkt nachgemessenen Scroll-Versuch fielen die
abweichenden BILDPUNKTE dagegen von 2.785 auf 107 (CRT) bzw. von 105.717
auf 2.190 (HDMI). Deshalb gibt das Skript beide Zahlen aus. Die
verbliebenen Abweichungen liegen fast alle auf einer einzigen Bildzeile
am unteren Rand der Boxart-Karte. Diese
Abweichungen sind bekannt, auf echter Hardware bisher NICHT sichtbar und
noch nicht aufgeklaert. Als Pass/Fail-Test wuerde das Skript deshalb
dauerhaft rot stehen und den Regressionslauf entwerten - es liefert
stattdessen immer den Rueckgabewert 0 und dient als Messinstrument:

> WEDER die Zahl der Faelle NOCH die Zahl abweichender Bildpunkte darf
> bei Aenderungen am Zeichenpfad steigen - die zweite ist dabei die
> aussagekraeftigere.

Vor und nach einer Aenderung ausfuehren und BEIDE Zeilen
(`Abweichungen` und `Abweichende Punkte`) vergleichen.
