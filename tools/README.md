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

## diag_lightpath.py

DIAGNOSE, kein Pass/Fail-Test. Prueft die zentrale Annahme hinter dem
schnellen Zeichenpfad: ein Einzelschritt bzw. ein Puls-Tick muss dasselbe
Bild hinterlassen wie ein VOLLER Neuaufbau desselben Zustands.

Aktueller Stand: **22 von 32 verglichenen Faellen weichen ab**. Diese
Abweichungen sind bekannt, auf echter Hardware bisher NICHT sichtbar und
noch nicht aufgeklaert. Als Pass/Fail-Test wuerde das Skript deshalb
dauerhaft rot stehen und den Regressionslauf entwerten - es liefert
stattdessen immer den Rueckgabewert 0 und dient als Messinstrument:

> Die Zahl der Abweichungen darf bei Aenderungen am Zeichenpfad nicht
> STEIGEN.

Vor und nach einer Aenderung ausfuehren und die Zeile
`Abweichungen : N` vergleichen.
