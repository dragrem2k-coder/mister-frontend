# Changelog

Was sich am Frontend so getan hat. Für die ganz kleinteiligen Details
schau am besten in die Git-Historie oder in
`docs/ENTWICKLUNGSHISTORIE.md` (stand früher als über 3300 Zeilen langer
Kommentarblock im Kopf von `frontend/frontend.py`).

## v4.4 — Reset-Feature, HDMI-Performance-Runde, Stream-Menüpunkt

**„Miniaturen vorbereiten": Abbruch hat nie funktioniert, Anzeige auf
CRT abgeschnitten** (Build 81 — Nutzer-Rückmeldung: „auf CRT steht da
nur *Miniaturen werden* und *jede Taste bricht ab - Gerechnetes bl*.
Außerdem kann ich durch Tastendruck nicht abbrechen, oder er reagiert
gar nicht"):

**1. Der Abbruch konnte gar nicht funktionieren.** Die Prüfung lief über
`read_action(timeout=0)`. Bei `timeout=0` ist die Deadline sofort
erreicht — und die Deadline-Prüfung stand ganz am Anfang der Schleife.
Die Funktion kehrte also zurück, **ohne `select()` überhaupt aufgerufen
zu haben**. Ein „Nachsehen ohne Warten" war in Wahrheit ein „gar nicht
nachsehen", und zwar lautlos, weil `None` auch der normale Rückgabewert
für „keine Taste" ist. Die Prüfung selbst muss bleiben (sie verhindert
eine Endlosschleife bei dauerhaft fehlschlagendem `select()`) — sie
wird jetzt nur für die erste Runde ausgesetzt, sodass es garantiert
genau einen echten, nicht blockierenden Blick gibt.

**2. Nichts passte auf den CRT-Schirm.** Nachgerechnet für 320x240: für
den Titel standen bei fester Schriftgröße 2 genau **18 Zeichen** zur
Verfügung, der Text hat 29. Für den Abbruch-Hinweis waren es **37
Zeichen** bei 51. `fb.text()` schneidet still ab — deshalb genau die
zitierten Bruchstücke. Beide Werkzeuge dagegen gibt es längst und werden
auf anderen Bildschirmen auch benutzt (`_fit_scale()` sucht die größte
noch passende Schriftgröße, `_wrap_text()` bricht an Wortgrenzen um) —
nur hier nicht. Der Balken sitzt jetzt außerdem unter dem Titel statt
auf einem festen Abstand, der von der großen Schrift ausging.

**3. Der Stand des Zwischenspeichers steht jetzt im Log.** Auf die Frage
„werden die Miniaturen gespeichert oder immer neu erstellt?" gab es
bisher keine direkte Antwort. Nach einem Durchlauf steht dort jetzt
`Zwischenspeicher 12345/20000 Dateien` — steht die Zahl an der
Obergrenze, verdrängt die Sammlung sich selbst, und **dann** wird
tatsächlich immer wieder neu gerechnet.

**Schwarzer Block über Boxart und Gameinfo beim Scrollen im CRT-Modus —
behoben** (Build 80 — Nutzer-Rückmeldung: „wenn ich jetzt nach unten
gedrückt halte und die ROMs durchsuche … wird ein Teil der Boxart und
der Gameinfo mit einem schwarzen Block nicht mehr sichtbar, sobald ich
loslasse sieht man wieder alles"):

**1. Die Ursache lag tiefer als der Build davor.** Der schnelle
Seitenpfad stellt vor dem Neuzeichnen der Zeilen den Hintergrund der
Listenspalte wieder her, mit 10·s Rand nach jeder Seite. Die Boxart-Karte
beginnt aber nicht in festem Abstand: auf HDMI erst 42 Pixel rechts der
Liste, auf CRT schon nach 2. Das Band wischte dort also **8 Pixel weit in
die Karte hinein** — schon immer, nur fiel es nie auf, weil die Karte
danach jedes Mal wieder darüber gemalt wurde. Seit Build 76 wird sie
während des Scrollens ausgelassen, seitdem blieb der Streifen stehen.
Der Rand endet jetzt an der Kartenkante.

**2. Fünf Stellen, eine Rechnung.** Die Position der Boxart-Spalte stand
wortgleich an vier Stellen im Code, der Innenrand der Karte an einer
fünften — genau deshalb konnte eine sechste Stelle mit einer festen
Pixelzahl darüber hinauswischen, ohne dass der Zusammenhang irgendwo
sichtbar war. Jetzt gibt es `art_spalte_x0()` und `art_karte_x0()`, und
`tools/test_boxart_streifen.py` prüft die Überlappung direkt.

**3. Das Auslassen der Boxart-Spalte gilt nur noch für HDMI.** Die
Messung, die Build 76 begründet hat (105 ms für die Spalte), stammt aus
dem HDMI-Modus mit 697x729-Covern. Auf CRT ist dasselbe Cover 96x99 —
die Ersparnis liegt bei wenigen Millisekunden, während jedes Auslassen
nach dem Loslassen einen kompletten Seitenaufbau nachzieht. Netto war
das dort ein Verlust; das CRT-Scrollen läuft wieder wie in Build 75.

**Neun weitere Kategorie-Logos** (Build 80, vom Nutzer geliefert): 3DO,
Atari 2600, Atari Lynx, Famicom Disk System, Gamate, Intellivision,
Neo Geo CD, Vectrex und WonderSwan. Damit haben 33 der 48 Systeme ein
Logo. Neu dazu: `PC-Tools/sysart_convert.py`, das Logos auf das richtige
Maß bringt und auf den Kartenhintergrund legt — inklusive der beiden
Fälle, die von Hand mühsam sind (eingemaltes Transparenz-Schachbrett,
schwarze Schrift, die auf der dunklen Karte unsichtbar wäre). Welche 15
noch fehlen und wie man sie umwandelt, steht in
`docs/LOGOS_NACHLIEFERN.md`.

**48 statt 16 Systeme — und die Systemliste gibt es nur noch einmal**
(Build 79 — Nutzerwunsch: „eigentlich sollten alle runtergeladen werden,
wenn die Cores und die passenden ROMs im Frontend mit verfügbar sind …
falls jemand mal auf die Idee kommt, dass er auf einmal Atari oder
Jaguar oder 3DO mit nutzen will. Quasi: falls vorhanden, dann auch mit
bereitstellen."):

**1. Die Ursache des Virtual-Boy-Fehlers ist beseitigt.** Die Systemliste
existierte **viermal**: im Frontend und in den drei Download-Werkzeugen,
alle von Hand gepflegt. Jetzt ist `fe/systems.py` die einzige Quelle —
sie enthält zusätzlich den Namen der libretro-Datenbank je System, und
die beiden Werkzeuge auf dem MiSTer lesen direkt von dort.
`PC-Tools/boxart_fetch.py` behält eine erzeugte Kopie, weil es einzeln
auf einen Windows-PC kopiert wird und nichts importieren kann; dass sie
nicht abdriftet, prüft der Test bei jedem Lauf.

**2. 30 weitere Konsolen dazu.** Alle übrigen Konsolen-Systeme der
MiSTer-Distribution: 3DO, Adventure Vision, Arcadia 2001, Astrocade,
Atari 2600/5200/7800/Lynx, Casio PV-1000, CD-i, Channel F,
ColecoVision, CreatiVision, Famicom Disk System, Game & Watch, Game
Gear, Gamate, Intellivision, Jaguar, Mega Duck, Neo Geo CD, Odyssey 2,
Pocket Challenge V2, Pokémon Mini, SG-1000, Sega 32X, Super Game Boy,
TurboGrafx-16 CD, VC 4000, Vectrex, WonderSwan (+ Color).

Jedes erscheint **nur, wenn Core und ROMs wirklich da sind** — der
Mechanismus dafür gab es schon, er wird jetzt nur breiter genutzt. Wer
die Cores nicht hat, merkt von der Liste nichts.

**Woher die Startparameter kommen, und warum ich ihnen traue:** alle aus
der mrext-Systemdatenbank, derselben Quelle wie unsere bisherigen. Zur
Kontrolle habe ich die dortigen Werte für die **bestehenden** Systeme
abgerufen und verglichen — NES `(2,f,1)`, SNES `(2,f,0)`, Mega Drive
`(1,f,1)`, PSX `(1,s,1)`, Master System `(1,f,1)`, Game Gear `(1,f,2)`,
TurboGrafx `(1,f,0)`, SuperGrafx `(1,f,1)`, MegaCD/Saturn `(1,s,0)`,
Neo Geo `(1,f,1)`: **alle stimmen exakt überein.** Die Quelle ist damit
an 13 Punkten belegt, nicht angenommen. Genauso die Datenbanknamen: jeder
einzelne wurde abgerufen, nicht geraten.

**Ehrlich dazu:** geraten ist nichts, *getestet* aber auch nichts — ich
habe keinen MiSTer. Ob ein Core wirklich startet und das ROM lädt, zeigt
erst der Einsatz. Sollte eines nicht laufen, steckt der Fehler mit hoher
Wahrscheinlichkeit in genau einer Zahl, und die steht im Code direkt
daneben.

**3. Acht Logos sind aufgetaucht.** Im Ordner
`sysart/_weitere_systeme_noch_nicht_unterstuetzt/` lagen längst fertige
Logos für Atari 5200/7800, Jaguar, ColecoVision, CD-i, Sega 32X, Super
Game Boy und TurboGrafx-CD — „für den Tag, an dem die mal ergänzt
werden". Der Tag ist heute; sie sind an ihren Platz gerückt. Damit haben
24 der 48 Systeme ein Logo. Welche noch fehlen und in welchem Format
Nachschub gehört, steht in `docs/LOGOS_NACHLIEFERN.md`. Eine eigene
Akzentfarbe hat jedes der 48 Systeme.

**Das Sicherheitsnetz:** `tools/test_system_abdeckung.py` nagelt
Startparameter, ROM-Ordner und Datenbank-Zuordnung der ursprünglichen 16
Systeme auf ihre bekannten Werte fest. Die Liste wuchs in einem Zug von
16 auf 48 — ein dabei verrutschter Index hieße „Core startet, ROM lädt
nicht", ohne Fehlermeldung. Zusätzlich geprüft: keine Kombination aus
ROM-Ordner und Dateiendung ist doppelt vergeben (sonst erschiene
dieselbe Datei in zwei Kategorien), und alle drei Werkzeuge liefern
dieselbe Tabelle.

Nachgemessen statt vermutet: die 34 zusätzlichen Core-Prüfungen beim
Start kosten zusammen rund 2 ms. Ein Zwischenspeicher dafür wäre Aufwand
ohne Gegenwert und ist bewusst nicht eingebaut.

**Zwei Dinge, die absichtlich so sind:** Game-Gear-Dateien im Ordner
`games/SMS` erscheinen weiterhin unter „Master System" (die Kategorie
liest `.gg` dort seit jeher mit) — die neue eigene Kategorie gilt für
den Ordner `games/GameGear`. Und der Zufalls-Zock zieht nach wie vor nur
aus den Standardsystemen, nicht aus den optionalen.


**Virtual Boy fehlte in allen drei Download-Werkzeugen** (Build 78 —
Nutzerfrage: „wir haben ja den Virtual Boy mit reingenommen, muss ich
das Script `Frontend_Boxart_Download.sh` nochmal starten, damit ich die
dafür bekomme?"):

Die ehrliche Antwort war **nein** — ein erneuter Lauf hätte nichts
gebracht, weil das System in keiner der Systemtabellen stand. Die
Kategorie kam mit einem früheren Build dazu; die drei Tabellen in
`frontend/mister_boxart.py`, `frontend/mister_gameinfo.py` und
`PC-Tools/boxart_fetch.py` wurden dabei übersehen.

**Das Tückische daran ist der fehlende Fehler.** Das Skript wäre brav
durchgelaufen, hätte die 13 ihm bekannten Systeme abgeklappert und
Erfolg gemeldet — Virtual Boy hätte es stillschweigend ausgelassen.
Sichtbar wäre nur gewesen, dass keine Cover kommen, und gesucht hätte
man den Fehler dann bei den ROM-Namen, beim Netzwerk oder bei den
Rechten.

Nachgetragen in allen drei Werkzeugen, mit **geprüften statt geratenen**
Namen: `thumbnails.libretro.com/Nintendo - Virtual Boy/Named_Boxarts/`
liefert echte Dateien, und `metadat/releaseyear/Nintendo - Virtual
Boy.dat` echte Einträge (beides abgerufen, nicht angenommen).

Neu dazu: `tools/test_system_abdeckung.py`. Er vergleicht die
Systemliste des Frontends mit allen drei Werkzeugen und prüft zusätzlich
ROM-Ordner, Dateiendungen und den Datenbanknamen — ein falscher Ordner
findet genauso lautlos nichts wie ein fehlender Eintrag. Systeme ohne
Datenbank (SMW-Hacks, ALTTP-Tracker) stehen in einer Ausnahmeliste mit
Begründung, und ein weiterer Test verhindert, dass diese Liste zur
Müllhalde wird.

**Für dich heißt das:** nach dem Aufspielen einmal
`Frontend_Boxart_Download.sh` laufen lassen (bereits vorhandene Cover
werden übersprungen, es lädt nur die fehlenden), und für Jahr/Genre/
Spielerzahl zusätzlich `Frontend_Gameinfo_Download.sh`.


**Tastenbelegung aufgeräumt: F1 raus aus dem Spiel, F4 und F10 weg**
(Build 77 — Nutzerwünsche: „Esc-Funktion hätte ich dann gerne auf F1,
und die soll so schnell auslösen wie die F5-Reset-Funktion", „F4 kann
raus komplett, auch der Schalter unter System, weil die Funktion ja
nicht geht", „F10 kann auch komplett raus, funktioniert genauso wenig"):

**1. F1 bringt dich sofort aus dem laufenden Spiel zurück ins
Frontend.** Kein Halten, ausgelöst in dem Moment, in dem die Taste
erkannt wird — genau wie der F5-Reset seit Build 75.

Esc bleibt daneben bestehen, mit seiner Haltezeit von 0,6 s. Das ist
Absicht und kein vergessener Rest: viele Spiele und Cores belegen Esc
selbst für ihr Pausemenü, ein kurzer Druck darf einen dort nicht
hinauswerfen. F1 belegt praktisch kein Core — deshalb ist sofortiges
Auslösen dort gefahrlos, bei Esc wäre es das nicht.

**2. F10 ist ersatzlos entfallen — und beim Ausbauen kam heraus, warum
es nie funktioniert hat.** Gleich zwei Gründe, jeder für sich schon
tödlich:

- Es wurde über die normale evdev-Ebene abgefragt. Genau die sperrt
  MiSTer exklusiv, sobald ein Core läuft — dieser Zweig konnte nie
  auslösen.
- Der HID-Weg, der später dazukam, prüfte auf `0x44`. Das ist im
  HID-Standard **F11**, nicht F10 (`0x43`). Erkannt wurde also all die
  Zeit F11; F10 selbst kam nie an.

Statt auf `0x43` zu korrigieren wurde die Prüfung ganz entfernt — sonst
würde ein F11-Druck im Spiel weiterhin unerwartet aussteigen.

**3. Der F4-Schnellstart ist komplett raus** — Menüschalter,
Übersetzungen, Selbstheilung und der Hintergrund-Wächter
(`frontend/f4_hotkey.py`), der bei jedem Boot die Eingabegeräte mitlas.

Wichtig für alle, die ihn installiert hatten: **die Installer und
`Frontend_Update.sh` räumen die Startzeile aus
`/media/fat/linux/user-startup.sh` und die Dateien jetzt aktiv weg.**
Ohne das bliebe dort eine Zeile stehen, die bei jedem Boot eine
gelöschte Datei starten will. Ein laufender Wächter wird dabei beendet.
Wer das Frontend ohne Autostart starten möchte, nimmt
OSD → Scripts → `Frontend_Start`; der Autostart-Schalter selbst bleibt
unverändert.

Anleitungen nachgezogen: `README.md`, `README_EN.md`,
`docs/anleitung_source.html` und die daraus erzeugte
`docs/Dragend_Anleitung.pdf`. Dazu neu: `docs/PDF_ERZEUGEN.md` — die PDF
muss mit Chromium erzeugt werden, nicht mit wkhtmltopdf; letzteres
ignoriert `@page { size: A4; margin: 0 }` und schrumpft den Inhalt
stillschweigend auf drei Viertel der Seite.

**Freie F-Tasten danach: F3.** Belegt sind F1 (Ausstieg), F2 (Suche),
F5 (Musik/Reset), F6 (RA-Schaufenster), F7 (durchgespielt), F8
(Favorit), F11 (Zufallsspiel), F12 (OSD); F9 gehört MiSTer selbst.

**Die Boxart-Spalte wird auch beim vollen Seitenaufbau ausgelassen**
(Build 76 — Messung im HDMI-Modus, Nutzerfrage: „es ist schon besser,
aber haben wir da noch Möglichkeiten das zu verbessern?"):

```
split: bgbild=0 bg=0 restore=22 rows=44(17) art=105 flip=21 ms
draw_page_items: 195 ms
```

Von rund 190 ms Seitenaufbau entfallen **über 100 ms allein auf die
Boxart-Spalte**. Im HDMI-Modus ist ein Cover 697×729 Bildpunkte, gut
2 MB, die gelesen, entpackt und in den Bildspeicher kopiert werden —
bei jedem einzelnen Scrollschritt.

Der leichte Zeichenpfad lässt die Spalte beim schnellen Scrollen längst
aus. Nur griff das ausgerechnet dann nicht, wenn es am meisten wehtut:
in einer langen Liste erreicht der Auswahlbalken nach wenigen Schritten
den unteren Rand, ab da muss die Liste bei **jedem** Schritt verschoben
werden, der leichte Pfad gibt auf — und der volle Neuaufbau zeichnete
die Spalte weiterhin jedes Mal. Genau der Fall, in dem man am längsten
scrollt.

Jetzt lässt auch der volle Aufbau sie aus, solange aktiv gescrollt wird.
Das zuletzt gezeichnete Cover bleibt so lange stehen und wird nach dem
Stillstand nachgeholt (`COVER_SETTLE`) — dasselbe Verhalten, das der
leichte Pfad schon immer hatte.

**Die eine Bedingung, die das sicher macht:** ausgelassen wird nur, wenn
der Hintergrund in diesem Durchgang *nicht* neu aufgebaut wurde (in der
Messung oben das `bg=0`). Dann steht das alte Cover noch im Puffer und
bleibt einfach stehen. Wurde der Hintergrund frisch gefüllt, würde ein
Auslassen ein leeres Feld hinterlassen — der Unterschied zwischen „altes
Cover steht noch" (harmlos, wird nachgeholt) und „da ist ein Loch"
(sieht kaputt aus). `tools/test_cover_prewarm.py` prüft beide Fälle und
vergleicht den Bildschirm nach dem Nachholen **bitgenau** mit einem, der
nie etwas ausgelassen hat: null abweichende Bildpunkte.

Wirksam nur bei eingeschaltetem „Schnelles Scrollen" (System → Anzeige)
— bewusst an denselben Schalter gehängt wie der leichte Pfad, damit ein
Schalter das gesamte Verhalten beim Scrollen bestimmt und nicht zwei
Regeln nebeneinander gelten.

**F5-Reset ohne Halten, und die Sonderkategorien nachgeprüft** (Build 75
— Nutzerwünsche: „F5-Reset-Funktion hätte ich gerne auf sofortigen
Tastendruck, wenn das geht" und „bitte auch die anderen bedenken wie die
Kategorie Zuletzt gespielt, Weiterspielen, SMW Hacks, SNES ALTTP
Tracker, Sammlungen, RA-Erfolgsjäger, Zufalls-Zock, System — nicht dass
da auch noch irgendwo was hängt"):

**1. F5 löst jetzt beim Drücken aus.** Es lagen drei Verzögerungen
hintereinander, und nur die erste war beabsichtigt:

- 0,6 s Haltezeit
- bis zu 0,2 s, weil die Haltezeit erst am *Anfang* der nächsten
  Schleifenrunde geprüft wurde — und die wartet vorher in
  `select(..., 0.2)`
- 0,2 s, weil das virtuelle Tastatur-Gerät bei **jedem** Reset neu
  angelegt wurde; der Kernel braucht diese Zeit, um es bekannt zu
  machen

Macht bis zu 1,0 s. Jetzt wird direkt an der Stelle ausgelöst, an der
die Taste erkannt wird, und das Gerät wird einmal angelegt und
wiederverwendet. Übrig bleibt die Tastendruckdauer von 0,1 s, die der
Empfänger braucht, um den Druck überhaupt zu sehen.

*Ehrlich benanntes Risiko:* ein versehentlicher F5-Antipper während des
Spielens ist jetzt sofort ein Reset, also im Zweifel ein verlorener
Spielstand — genau dafür war die Haltezeit da. Wer sie zurückhaben will,
setzt `RESET_HOLD` in `fe/input.py` wieder auf 0.6. Ein Dauerfeuer durch
bloßes Halten ist unabhängig davon ausgeschlossen: es braucht immer erst
ein Loslassen.

**2. Die Sonderkategorien sind nachweislich abgedeckt.** Sie sind der
gefährliche Fall, weil sie anders gebaut sind als ein normales System:
„Zuletzt gespielt", „Weiterspielen", „Favoriten", „Sammlungen" und
„RA-Erfolgsjäger" haben **keinen eigenen Systemkey** — sie mischen
Spiele aus mehreren Systemen, und der Systemkey steckt in jedem Eintrag
selbst. Würde der Vorauslader hier den Kategorie-Systemkey nehmen,
suchte er die Cover im falschen Ordner, und wieder fiele es nicht auf:
es bliebe nur langsam. `tools/test_cover_prewarm.py` baut diese
Kategorien jetzt so nach, wie `build_categories()` sie anlegt, und prüft
in beiden Auflösungen Eintrag für Eintrag, dass Vorhersage und
tatsächliche Anfrage übereinstimmen — inklusive der Logos
(`CONTINUE.art`, `RECENT.art`, `COLLECTIONS.art`, `RA_HUNTER.art`).

**Der 169-ms-Ausreißer bei einem reinen Cache-Treffer** (Build 74 —
Nutzer-Rückmeldung: „sind immer noch ein paar Ausreißer drin, zum
Beispiel CONTINUE.art, manche andere auf der Hauptseite habe ich das
Gefühl auch"):

Im Log stand etwas, das nicht sein durfte — ein **Treffer**, bei dem
also gar nichts gerechnet, sondern nur eine Datei gelesen wird:

```
THUMB_CACHE Treffer:   0.9 ms  (SNES.art, 77x156)
THUMB_CACHE Treffer:  15.5 ms  (Capcom vs. SNK Pro (USA).art, 96x163)
THUMB_CACHE Treffer: 169.0 ms  (Brave Prove (English v1.1b).art, 96x165)
```

Mein erster Verdacht war das Zeitstempel-Schreiben bei jedem Lesen
(`os.utime`, die LRU-Markierung). Eine Messung auf dem Gerät hat ihn
klar widerlegt und stattdessen den wahren Posten benannt:

```
Ordner durchzaehlen (7700 Dateien): 167 ms
lesen     Schnitt 11.2 ms, max 26 ms
entpacken Schnitt  1.3 ms, max  2 ms
utime     Schnitt  0.1 ms, max  0 ms
```

**1. Die Verdrängungs-Prüfung zählt nicht mehr bei jedem Schreiben.**
Sie begann mit genau jenem `os.listdir` über alle 7700 Dateien — 167 ms,
nach **jedem** geschriebenen Miniaturbild, im Hintergrund-Thread, der
sich dabei mit dem Zeichnen um dieselbe SD-Karte streitet. Die 167 ms
und der 169-ms-Treffer sind dieselbe Zahl. Jetzt wird die Anzahl einmal
ermittelt und danach mitgezählt; im Normalbetrieb findet gar kein
Verzeichniszugriff mehr statt. Alle 2000 Schreibvorgänge wird zur
Sicherheit nachgezählt, falls jemand von außen im Ordner aufräumt.

**2. Der Skalierungs-Cache begrenzt sich nach Speicher statt nach
Stückzahl.** Er hielt 20 Bilder — unabhängig davon, ob eine
CRT-Miniatur (rund 60 KB) oder ein HDMI-Cover (über 2 MB) darin lag. Auf
CRT passte damit nicht einmal eine Bildschirmseite plus Umfeld hinein:
beim Hoch- und Runterscrollen fiel ein Cover heraus, bevor man es
wiedersah, und wurde erneut von der Karte gelesen — die gemessenen
11 ms, jedes Mal. Jetzt gilt ein Budget von 24 MB, womit auf CRT
mehrere hundert Miniaturen im Speicher bleiben; auf HDMI bleibt es bei
einer Handvoll großer Bilder, aber nie bei weniger Plätzen als vorher.

**3. Die Kategorie-Logos der Hauptseite werden mit vorgewärmt.** Der
Vorauslader aus Build 73 kümmerte sich nur um die Spieleliste — dabei
sind ausgerechnet die Logos mit 900 px Breite die größten Bilder im
Frontend (`PERF cover: 722 ms (CONTINUE.art)`) und stehen auf der Seite,
die man beim Start als erstes sieht. Es sind nur rund zwanzig Stück, und
„Miniaturen vorbereiten" nimmt sie jetzt zuerst dran — wer den Durchlauf
nach einer Minute abbricht, hat wenigstens die erledigt.

**Cover-Miniaturen werden vorberechnet — das Stocken beim Ordnerwechsel**
(Build 73 — Nutzer-Rückmeldung: „wenn man in die Unterordner geht und
wieder zurück will, bleibt das Frontend echt mal hängen für 1–2
Sekunden … das nervt schon sehr"):

Diesem Fehler bin ich mit vier Vermutungen hinterhergelaufen, die alle
falsch waren — Dateisystem, Listensortierung, Netzwerk, und zuletzt
Bildschirm-Spiegel plus Stream-Overlay. Erst eine Messung auf dem Gerät
hat es beantwortet, und zwar unmissverständlich:

```
PERF split: bgbild=0 bg=0 restore=3 rows=5(13) art=225 flip=1 ms
PERF draw_page_items: 251 ms
```

Von 251 ms Seitenaufbau entfallen **225 ms auf ein einziges Cover**.
Hintergrund, Zeilen und Bildausgabe kosten zusammen rund 20 ms. Beim
zweiten Besuch kostet dasselbe Cover 1–6 ms — der Festplatten-Cache
arbeitet also einwandfrei, er ist beim ersten Durchgang durch eine Liste
nur eben noch leer. Das erlebte Hängen sind vier bis acht solcher Cover
hintereinander.

**Das korrigiert auch eine frühere Einschätzung von mir.** Auf die Frage
nach einem C-Modul für die Zeichen-Grundfunktionen hatte ich mit 47–55 %
Anteil gerechnet. Diese Messung sagt: die Zeichenroutinen sind mit 20 ms
längst nicht mehr der Engpass. Ein C-Modul hätte an der falschen Stelle
angesetzt.

**1. Vorausladen im Leerlauf.** Ein Hintergrund-Thread berechnet die
Cover der voraussichtlich als nächstes gebrauchten Einträge schon,
während jemand eine Seite ansieht (`frontend/fe/prewarm.py`). Zwei
Einschränkungen sind bewusst so entworfen und im Code benannt: auf der
schwachen CPU rechnet wegen Pythons GIL immer nur ein Thread, deshalb
lässt der Vorauslader bei **jeder** Eingabe sofort los — eine bereits
begonnene Miniatur läuft noch zu Ende, mehr nicht. Und er fasst die
Arbeitsspeicher-Caches von `ArtCache` mit keinem Byte an, sondern
schreibt ausschließlich Dateien; diese Caches haben keine Sperre, und
zwei Threads darin wären genau die Sorte Fehler, die sich nie
zuverlässig nachstellen lässt.

**2. Neuer Menüpunkt „Miniaturen vorbereiten"** (System → Verhalten).
Rechnet einmalig alle Cover durch. Danach ist auch das Springen in
Listen schnell, dauerhaft und über Neustarts hinweg. Ehrlich genannter
Preis, der auch im Menüpunkt selbst steht: grob 3–8 Minuten je 1000
Spiele, und CRT und HDMI brauchen getrennte Durchläufe. Läuft mit
Fortschrittsbalken und Restzeit-Schätzung, jede Taste bricht ab, und
Abbrechen verliert nichts.

**3. Die Kastengröße kommt jetzt aus einer einzigen Funktion**
(`cover_box_size()`). Das ist der unscheinbare, aber entscheidende
Punkt: Der Schlüssel des Festplatten-Caches enthält die Größe, in die
das Cover eingepasst wird — und die hängt am Text darunter, ist also pro
Spiel verschieden (im Log des Nutzers gut zu sehen: 96x99, 96x111,
96x135 in derselben Liste). Hätte der Vorauslader diese Rechnung
nachgebaut, wäre sie irgendwann abgewichen, und er hätte fleißig
Miniaturen abgelegt, die der Zeichenpfad nie findet — ohne dass
irgendetwas kaputtgeht, es bliebe nur langsam. `tools/test_cover_prewarm.py`
schneidet deshalb die vom **echten** Zeichenpfad angefragten Maße mit
und vergleicht sie Eintrag für Eintrag.

Ebenso herausgelöst: das Vergrößern (`_hochskalieren()`), damit
Vorberechnung und Anzeige bitgleiche Ergebnisse liefern — der
Modul-Kommentar in `fe/art.py` verlangt das ausdrücklich, und der Test
prüft es Byte für Byte in beiden Richtungen.

**Keine Video-Reste mehr in der `MiSTer.ini`** (Build 72 —
Nutzer-Rückmeldung nach einem wackelnden HDMI-Bild bei einem Bekannten:
„falls das die Ursache ist, sollten wir da Vorkehrungen treffen, das
heißt bei uninstall mit raus … nicht dass es noch mehrere betrifft"):

Vorweg, weil es für die Ursachensuche wichtig ist: **das Frontend setzt
selbst keinen Videomodus.** Es liest die Bildgeometrie aus
`/sys/class/graphics/fb0/` und schreibt Pixel — welches Signal am HDMI
anliegt, bestimmt weiterhin allein der MiSTer. Genau **zwei** Stellen in
der `MiSTer.ini` kann es überhaupt verändern: den `[Menu]`-Block
(CRT-Modus) und `fb_size` (Menü-Auflösung). Beide sind
Video-Einstellungen, die nach einer Deinstallation niemand mehr dem
Frontend zuordnen würde — und die Deinstallation fasste die `MiSTer.ini`
bisher überhaupt nicht an, obwohl sie eine rückstandsfreie Entfernung
versprach.

**1. Die Deinstallation räumt beides auf.** `Frontend_Uninstall.sh` ruft
vor dem Löschen der Programmdateien `mister_ini_cleanup.py` auf, das den
`[Menu]`-Block entfernt und `fb_size` auf den MiSTer-Standard
zurücksetzt. Es sagt in Klartext, was es getan hat.

**2. Ein selbst angelegter `[Menu]`-Block bleibt unangetastet.** `[Menu]`
ist eine ganz normale MiSTer-Funktion; wer dort eigene Werte stehen hat,
darf sie durch eine Deinstallation nicht verlieren. Entfernt wird nur,
was dem Frontend zuzurechnen ist — erkennbar an einer Markierungsdatei
(seit diesem Build beim Einschalten gesetzt) **oder** daran, dass der
Blockinhalt wortgleich dem ist, den der CRT-Schalter schreibt. Das
zweite Merkmal ist der Rückfall für alle, die den CRT-Modus mit einer
älteren Fassung eingeschaltet haben — also genau für die bestehenden
Installationen, um die es hier geht. Eine einzige geänderte Zeile
genügt, damit der Block als fremd gilt und stehen bleibt.

**3. Der Rückweg auf HDMI setzt `fb_size` mit zurück.** Bisher passierte
das nur in die andere Richtung. Ein im CRT-Modus vorgefundener Wert kann
gar keine bewusste Entscheidung sein — der Menüpunkt dafür ist dort
ausgeblendet. Ihn beim Rückweg stehen zu lassen hieße, jemanden mit
einem halb aufgelösten Bild sitzen zu lassen, ohne dass er weiß, woher
es kommt. Umgekehrt geht nichts verloren: eine bewusst auf HDMI
getroffene Wahl kann davon nicht betroffen sein. Das Zurücksetzen liegt
jetzt in `toggle_crt_menu()` selbst und greift damit auch auf dem
zweiten Weg — dem automatischen Rücksprung des CRT-Sicherheitsnetzes.

**4. Der Video-Zustand steht beim Start im Log.** Eine Zeile
(`MiSTer.ini beim Start: [Menu] … , fb_size=…`) sagt künftig sofort, ob
eine dieser beiden Einstellungen überhaupt gesetzt war — und ob der
Block vom Frontend stammt. Beim aktuellen Fehlerbild kostete genau diese
fehlende Auskunft zwei Rückfrage-Runden.

Alle Schreibzugriffe auf die `MiSTer.ini` laufen jetzt über denselben
abgesicherten Weg wie der Autostart-Eintrag: einmalige Sicherungskopie
(`MiSTer.ini.dragend_backup`), Temp-Datei im selben Verzeichnis,
Rück-Lesen zur Kontrolle, erst dann das atomare Umbenennen. Schlägt
irgendetwas davon fehl, bleibt die Datei unverändert. Abgesichert durch
`tools/test_mister_ini.py` (13 Blöcke, u. a. fremder Block, alte
Installation ohne Markierung, fehlgeschlagenes Schreiben, echter
Durchlauf des Aufräumskripts).

**Übersetzte japanische ROMs + CRT/HDMI raus aus dem Assistenten**
(Build 71 — Nutzer-Rückmeldungen: „Seiken Densetsu 3 (Japan) (German).sfc
und Magic Knight Rayearth (J) [T+Ger].sfc werden nicht erkannt, das sind
wieder so Sonderlocken" sowie „bei der Neuinstallation die Option
CRT/HDMI komplett rausnehmen — jeder, der einen MiSTer nutzt,
installiert das eh über HDMI"):

**1. Der Nur-Japan-Filter erkennt jetzt Übersetzungen und
ausgeschriebene Sprachnamen.** Build 69 hatte nur zweibuchstabige
Sprachcodes gelernt (`(En)`, `(En,Ja)`) — durch dieses Raster fielen die
beiden häufigsten anderen Schreibweisen:

- **Ausgeschriebene Sprachnamen:** `(German)`, `(English)`, `(Spanish)` …
- **Übersetzungs-Kennzeichen** der GoodTools-Konvention: `[T+Ger]`
  (neuere Übersetzung), `[T-Eng]` (ältere), oft mit Versions- und
  Gruppenzusatz wie `[T+Ger1.01_Team]`.

Beides bedeutet dasselbe: das Spiel ist nicht nur auf Japanisch nutzbar.
Bei Fan-Übersetzungen ist das sogar der häufigste Grund überhaupt, ein
japanisches ROM zu behalten — ausgerechnet die auszublenden ist das
Gegenteil des Gewollten. Ein Übersetzungs-Kennzeichen zählt jetzt
**immer** als Hinweis auf eine andere Sprache; eine Übersetzung ins
Japanische gibt es bei japanischen ROMs nicht. `(Japanese)`, `(Ja)`,
`(Rev A)` und `(v1.1)` bleiben korrekt ohne Wirkung.

Zur Einordnung: seit Build 69 ist der Filter **standardmäßig aus**, diese
Dateien erscheinen also ohnehin. Der Fix betrifft alle, die die
aufgeräumtere Liste eingeschaltet haben — dort dürfen übersetzte Titel
nicht verschwinden.

**2. Die CRT/HDMI-Frage ist aus dem Einrichtungsassistenten entfernt**
(Schritt 2 von vormals acht, jetzt sieben Schritte). Sachlich richtig —
installiert wird praktisch immer über HDMI — und es beseitigt eine echte
Falle: der Assistent läuft beim **allerersten** Start. Wer dort
versehentlich CRT wählt und keinen anschließt, sitzt vor einem schwarzen
Bild, ausgerechnet bevor er das Frontend überhaupt kennt. Das
Sicherheitsnetz (20 Sekunden ohne Eingabe → automatisch zurück auf HDMI)
fängt das zwar ab, aber gar nicht erst hineinlaufen zu können ist besser.

Die Umschaltung selbst bleibt vollständig erhalten — unter
System → Optionen → Anzeige & Sound, also bei jemandem, der das Frontend
bereits laufen sieht. Der Boxart-Download im Assistenten liest den
aktiven Modus jetzt aus der MiSTer.ini statt aus der entfallenen
Auswahl; das ist ohnehin die verlässlichere Quelle.


**F4: der Unterschied zwischen Vordergrund und Hintergrund**
(Build 70):

Befund aus der Ferndiagnose: im Diagnosemodus (`--debug`, im
Vordergrund) kam `Code 62` sauber an — beim Hintergrundprozess erschien
keine einzige Zeile im Log. Gleicher Code, gleiche Geräte, gleiche
Tastatur.

Der Unterschied war der Zustand des Frontends. Solange es läuft, greift
es die Eingabegeräte **exklusiv** ab (`EVIOCGRAB` in `fe/input.py`) —
ein anderer Leser bekommt in dieser Zeit nichts. Das ist richtig so und
soll auch so bleiben. Beim Diagnoselauf war das Frontend nachweislich
nicht aktiv (`Frontend laeuft gerade: nein`), beim Hintergrundtest
dagegen sehr wahrscheinlich schon.

Laut evdev-Verhalten bekommen bereits geöffnete Dateizeiger nach dem
Freigeben wieder Ereignisse. Nach dieser Fehlersuche verlasse ich mich
darauf nicht mehr: der Wächter merkt sich jetzt, ob das Frontend läuft,
und öffnet die Geräte **einmal frisch, sobald es sich beendet** — also
genau in dem Moment, in dem F4 überhaupt erst sinnvoll wird. Kostet
nichts (passiert höchstens beim Beenden des Frontends) und schließt
diese Unsicherheit vollständig aus.


**ROMs verschwanden stillschweigend aus der Liste — jetzt abschaltbar,
standardmäßig aus**
(Build 69 — Nutzer-Rückmeldung: „Die Datei heißt `Tetris (Japan) (En).gb`
— das ist die, die auch bei RetroAchievements genutzt werden soll. Diese
wurde weder mit kuratierter Liste noch ohne erkannt. Erst als ich den
Dateinamen auf `Tetris.gb` geändert habe.")

Zwei Ursachen, beide behoben.

**1. Der Nur-Japan-Filter war zu grob.** Er kannte bereits die Ausnahme
`(Japan, USA)` — mehrere Regionen in *einer* Klammer. Er kannte aber
nicht den in No-Intro-Sets sehr häufigen Fall: japanisches Release mit
englischer Sprachfassung, wobei die Sprache in einer **zweiten** Klammer
steht (`Tetris (Japan) (En)`, `Puyo Puyo (Japan) (En,Ja)`). Solche Titel
sind auf Englisch spielbar; sie auszublenden ist genau das, was der
Filter nicht tun soll. Erkannt wird jetzt die Sprachliste als eigene
Klammergruppe (`En` / `En,Fr` / `En,Ja,De`).

**2. Der eigentliche Fehler: die Filter waren unsichtbar.** `_is_junk()`
(beta/proto/demo/sample/`[b]`/program/test/kiosk) und `_is_japan_only()`
liefen beim **Einlesen**, immer, ohne Schalter, ohne Hinweis — und damit
**vor** der kuratierten Liste. Deshalb half deren Abschalten nicht: die
Datei war zu dem Zeitpunkt längst verworfen. Ein Nutzer sieht eine Datei
im Ordner, sieht sie im Frontend nicht, und nichts sagt ihm warum.

Beide Filter haben jetzt einen gemeinsamen Schalter unter
System → Optionen → **Verhalten**, und zwar **standardmäßig AUS**: ab
diesem Build erscheint jede ROM aus den Ordnern. Das ist eine bewusste
Verhaltensänderung für alle — „zeig mir, was in meinen Ordnern liegt"
ist die Erwartung, die niemanden überrascht. Wer die aufgeräumtere Liste
möchte, schaltet sie ein; auch dann bleibt `Tetris (Japan) (En)` dank
Fix 1 sichtbar.

Die Menüzeile nennt ausdrücklich, *was* ausgeblendet wird — „Filter
an/aus" allein sagt niemandem, welche Dateien dann fehlen, und genau
diese Unsichtbarkeit war das Problem.

**Die kuratierte Liste bleibt unverändert.** Sie war nicht die Ursache
und hat ihren eigenen Schalter; sie zu entfernen hätte den gemeldeten
Fehler nicht behoben.

Der Schalterzustand geht in den Cache-Fingerabdruck ein, und das
Umschalten stößt sofort einen Neuscan an — die Filter wirken beim
Einlesen, nicht beim Anzeigen. Ohne das änderte sich auf dem Bildschirm
nichts und der Menüpunkt wirkte kaputt.

Abgesichert durch `tools/test_rom_filter.py`.


**BUGFIX: ein zweiter Startversuch leerte die Sperrdatei des F4-Wächters**
(Build 68 — beim Nachgehen der Meldung „laeuft bereits - dieser Start
wird beendet" gefunden):

Die Sperrdatei wurde mit `"w"` geöffnet, und das **leert sie sofort** —
noch bevor überhaupt klar ist, ob die Sperre zu bekommen ist. Jeder
zweite Startversuch löschte damit die PID des tatsächlich laufenden
Wächters aus der Datei. Der lief zwar weiter (die Sperre hängt am
Dateizeiger, nicht am Inhalt), aber jede spätere Frage „läuft er, und
unter welcher PID?" bekam eine leere Datei zu sehen und antwortete
„nein" — also genau dann irreführend, wenn man sich darauf verlassen
wollte: im Selbsttest und bei der Deinstallation.

Jetzt wird ohne Leeren geöffnet, erst die Sperre geholt und
ausschließlich im Erfolgsfall geschrieben. Die Meldung nennt zusätzlich
die PID des Wächters, der die Sperre hält.


**F4 kommt an — und eine Messmöglichkeit fürs Stocken beim Zurückgehen**
(Build 67):

**F4 ist damit geklärt.** Der Selbsttest auf dem Gerät zeigt:
`Logitech Wireless Keyboard` und `MiSTer virtual input` melden beide
eine F4-Taste, und beim Drücken kommt `Taste gedrueckt: Code 62 <-- das
ist F4`, gefolgt von `>>> F4 erkannt. Menue aktiv: True, Frontend
laeuft: False`. Die Erkennung funktioniert also vollständig.

Was im Selbsttest noch fehlte, war die wichtigste Frage überhaupt:
**läuft der Wächter gerade als Hintergrunddienst?** Alles kann korrekt
eingerichtet sein und F4 trotzdem nichts tun, wenn ihn seit dem
Einschalten niemand gestartet hat — die Zeile in `user-startup.sh` wirkt
erst beim nächsten Boot. Der Selbsttest sagt das jetzt, samt der einen
Zeile zum Sofortstart. Außerdem steht jetzt ausdrücklich dabei, dass im
Diagnosemodus bewusst **nichts** gestartet wird (sonst läge das Frontend
sofort über der Ausgabe, die man gerade lesen will).

**Stocken beim schnellen Zurückgehen: erst messen, dann ändern.**
Nutzer-Rückmeldung: „wenn ich eine Kategorie auswähle, dort 2-3
Unterordner drin sind und ich dann schnell auf Zurück drücke, stockt es
etwas, bis ich wieder im Hauptmenü bin."

Nachgestellt in der Sandbox: derselbe Vorgang dauert dort **0,2 ms** —
das Stocken kommt also aus etwas, das nur auf der echten Hardware
auftritt (SD-Karten-Zugriff, echte Metadaten, echte RA-Daten). Nach
mehreren Fehlgriffen in dieser Runde wird deshalb bewusst nicht wieder
geraten.

Die ausführliche PERF-Messung gab es bisher nur über die
Umgebungsvariable `DRAGEND_PROFILE=1`. Das setzt voraus, das Frontend
von Hand mit gesetzter Variable zu starten — und genau dann läuft es
nicht mehr so, wie es normalerweise benutzt wird. Jetzt zusätzlich als
Schalterdatei, wie alle anderen Schalter auch:

```
touch /media/fat/frontend/profile      # einschalten
... normal benutzen, das Stocken nachstellen ...
grep PERF /tmp/frontend.log            # ansehen
rm /media/fat/frontend/profile         # wieder aus
```


**BUGFIX: die Streifen blieben im System-Menü stehen**
(Build 66 — Nutzer-Rückmeldung: „bei den ROMs verschwinden die Streifen,
sobald ich die Taste loslasse, im System-Menü bleiben sie stehen, im
Ordner Anzeige & Sound zum Beispiel"):

Diese Unterscheidung war der entscheidende Hinweis, und sie führte
direkt zur Ursache. Im System-Menü gibt es **keine Boxart-Spalte**
(`has_art` ist False). Dadurch fehlt auch deren großzügigerer
Flip-Bereich, der in der Spieleliste den eigentlichen Fehler zufällig
mit überdeckte.

Der Fehler: an zwei Stellen wurde der Bereich, der nach dem Zeichnen auf
den **Schirm kopiert** wird, weiterhin mit der alten Rechnung
`rowh - 2*s` bemessen, während gezeichnet längst mit `band_h`
(= `max(rowh-2*s, 11*s)`) wird. Der Puffer war also **korrekt** — die
unterste Bildzeile des Auswahlbalkens wurde nur nie auf den Schirm
übertragen. Genau deshalb war der Puffervergleich in Build 64 grün und
der Fehler trotzdem sichtbar.

In der Spieleliste flippt das Boxart-Panel einen breiten Streifen mit,
weshalb es dort nach dem Loslassen (voller Neuaufbau) wieder sauber
aussah — exakt das beobachtete Verhalten.

Mit aufgeräumt: dieselbe Rechnung stand auch noch an drei Stellen der
Kategorienseite. Alle nutzen jetzt denselben Ausdruck.

`tools/test_crt_layout.py` deckt jetzt zusätzlich Listen **ohne**
Boxart-Spalte ab — der Fall, der durch alle bisherigen Tests
durchgefallen ist. 16 Kombinationen (zwei Auflösungen × mit/ohne
Boxart × hoch/runter × innerhalb/über den Rand), alle mit 0
abweichenden Bildpunkten.

**Boxart-Zwischenspeicher: 4000 → 20000** (auf Nachfrage: „Platz genug
ist auf einer 128-GB-Karte sowieso"). Damit passt praktisch jede
realistische Sammlung vollständig hinein, in beiden Auflösungen — einmal
aufgewärmt, danach dauerhaft warm. Preis: im Extremfall (alles HDMI)
mehrere GB auf der Karte. Auf 128 GB unkritisch, auf einer 16-GB-Karte
nicht; wer knapp ist, setzt den Wert herunter oder löscht
`frontend/thumb_cache`.

**F4-Diagnose erweitert.** Der Selbsttest meldete zwar 6 lesbare
Eingabegeräte, aber nicht, *was* das für Geräte sind. Jetzt fragt er
Name und Tastenumfang direkt beim Kernel ab (dieselben ioctls wie
`evtest`) und sagt pro Gerät, ob es überhaupt eine F4-Taste kennt.
Meldet keines eine, sind es nur Gamepads — dann kann der Wächter
prinzipiell nicht funktionieren, und das ist eine Antwort statt einer
Vermutung. Wichtig dabei: eine Tastatur im SSH-Fenster zählt nicht, die
Tastendrücke gehen an den PC.


**BUGFIX: Zeichenreste beim Hochscrollen + Boxart-Zwischenspeicher zu klein**
(Build 65 — Nutzer-Rückmeldung: „beim Hochscrollen verursacht der immer
noch Zeichenreste in den ROM-Ordnern sowie im System-Ordner. Rendert der
die ganzen Boxarts jetzt immer neu?"):

**Warum Build 64 nicht gereicht hat.** Der Test dort verglich den
**Zeichenpuffer**. Der war sauber. Der Fehler saß aber nicht im Puffer,
sondern kam vom **vollen Seitenaufbau**: der räumt vor dem Zeichnen die
Listenspalte frei, mit einem festen Rand von `10*s` nach oben. Dieser
Rand stützte sich auf eine Annahme, die als Kommentar direkt daneben
stand — „der Abstand Kopfzeile→list_y beträgt 46*s minus Kopfzeilenhöhe
(~30*s) = ca. 16*s freier Zwischenraum". Mit dem engeren CRT-Kopfblock
(36*s) sind es nur noch 6*s. Der Rand griff also **4 Pixel weit in die
Kopfzeile** und radierte die untere Hälfte der Eintragszahl weg, direkt
nachdem sie gezeichnet worden war. Auf HDMI unauffällig (48*s
Zwischenraum), auf der Röhre sofort sichtbar — und weil der volle Aufbau
genau beim Scrollen über den Listenrand einspringt, trat es beim
Hochscrollen auf.

Das ist der **dritte Fall derselben Sorte** in diesem Build: eine feste
Pixelzahl, die stillschweigend vom alten Layout ausging. Der Rand wird
jetzt aus dem tatsächlich vorhandenen Zwischenraum abgeleitet statt
geraten. Mit gefixt: `_clear_row_glow_margin()` trug beide Fehler aus
Build 64 (zu schmaler Bereich, flache Füllung ohne Randabdunkelung)
noch in einer eigenen Kopie — nutzt jetzt dieselbe Funktion wie alle
anderen.

**Die Lehre für den Test.** `tools/test_crt_layout.py` vergleicht jetzt
`fb.mm` statt `fb.buf` — also das, was flip() tatsächlich auf den Schirm
bringt, nicht nur das, was gezeichnet wurde. Und in **beide** Richtungen,
innerhalb des Fensters und über den Listenrand hinaus (dort fällt der
leichte Pfad auf den vollen Aufbau zurück — genau die Stelle, an der es
gehakt hat). Ergebnis: 0 abweichende Bildpunkte in allen acht
Kombinationen. Der Puffervergleich allein hätte das nie gefunden.

**Boxart-Zwischenspeicher: 800 → 4000 Einträge.** Zur Frage „rendert der
die Boxarts jetzt immer neu?" — teilweise ja, und das war unvermeidbar:
die CRT-Cover-Spalte wurde von 101 auf 96 Pixel schmaler, und die
Zielgröße ist Teil des Cache-Schlüssels. Einmal komplett neu also.
**Dass es sich bei jedem Neustart wiederholt, ist aber eine echte
Grenze:** 800 Dateien sind für eine große Sammlung zu wenig. Jedes Cover
braucht einen eigenen Eintrag je Zielgröße (CRT und HDMI unterscheiden
sich, ebenso ändert sich die Cover-Höhe mit der Zahl der
Metadatenzeilen). Einmal quer durch zwei Systeme gescrollt, und die
Einträge des ersten sind schon wieder verdrängt.

Ehrlich benannter Preis: Platz auf der SD-Karte, je nach Mischung ein
paar hundert MB. Wer das nicht will, setzt den Wert herunter oder löscht
`frontend/thumb_cache` — es geht dabei nichts verloren außer Wartezeit.
Zusätzlich meldet die Verdrängung jetzt im Log, wie viele Einträge sie
entfernt hat: taucht das oft auf, ist die Grenze für diese Sammlung
immer noch zu klein. Vorher lief das völlig lautlos, weshalb sich die
Frage bis jetzt nur raten ließ.

**F4: Selbsttest statt weiterem Raten.** Nach zwei Fehlversuchen aus der
Ferne bekommt `f4_hotkey.py` einen Diagnosemodus:
`python3 /media/fat/frontend/f4_hotkey.py --debug` sagt in Klartext, was
auf dem Gerät wirklich vorliegt (Schalterdatei, Startscript,
Autostart-Zeile, Menüzustand, lesbare Eingabegeräte) und meldet danach
**jeden** Tastendruck mit seinem Code. Kommt beim Drücken von F4 keine
Zeile, erreicht die Taste den Wächter überhaupt nicht — dann liegt es
nicht an dieser Datei, und das ist eine Antwort statt einer Vermutung.


**BUGFIX: farbige Reste beim Scrollen auf dem CRT**
(Build 64 — Nutzer-Rückmeldung mit Foto: „habe mal den CRT-Modus
gestartet, und wenn ich jetzt durch die Menüs scrolle oder in
System-Ordner, zieht es Fehler — das ist erst nach unserem
CRT-Verschönern passiert, das war vorher nicht"):

Stimmt, und die Ursache saß genau dort. Nachgestellt hat sich das im
Testaufbau sofort — waagerechte farbige Streifen rechts neben den
Einträgen, exakt wie auf dem Foto.

**Ursache 1 — eine stille Kopplung, ein Pixel.** Der Streifen, den
`draw_list_row()` aufräumt, beginnt bei `y-3*s` und ist `rowh-2*s` hoch.
Der Text ist `8*s` hoch und beginnt bei `y`. Damit der Text vollständig
im aufgeräumten Bereich liegt, muss `rowh >= 14*s-1` gelten. Diese
Bedingung stand **nirgends** im Code. Bei den bisherigen Werten (15 bzw.
45) war sie zufällig erfüllt; mit der neuen CRT-Zeilenhöhe 12 fehlte
genau **ein** Pixel. Die unterste Zeile jedes Buchstabens wurde
gezeichnet, aber nie wieder aufgeräumt. Bei der markierten Zeile ist der
Zeichenhintergrund die Akzentfarbe — übrig blieb also ein farbiger
Strich. Und weil die markierte Zeile den vollen Namen zeigt
(Laufschrift), die unmarkierte aber den gekürzten, ragte der Strich
rechts über den Text hinaus. Genau das Bild auf dem Foto.

Behoben nicht durch eine größere Zeilenhöhe (das wäre nur das Symptom),
sondern indem der Aufräumbereich jetzt so bemessen wird, dass er den Text
**immer** abdeckt: `max(rowh - 2*s, 11*s)`. Für alle bisherigen
Auflösungen ändert sich dadurch nichts.

**Ursache 2 — dieselbe Beobachtung, zweiter Grund.** Beim Nachgehen fiel
ein zweiter, viel älterer Fehler auf: `draw_list_row()` füllte den
Zeilenhintergrund ohne Hintergrundbild schlicht per `fb.rect(..., C_BG)`
— eine **flache** Füllung. Der volle Neuaufbau nutzt dagegen
`fb.clear(C_BG)`, und das legt zusätzlich die dezente Randabdunkelung an
(`VIGNETTE_ENABLED`). Jede Zeile, über die der Cursor einmal gelaufen
war, bekam dadurch einen minimal helleren Hintergrund als eine nie
berührte — auf einer Röhre sichtbar als Streifen quer durch die Liste.
Exakt dieser Fehler war in `_restore_row_bg()` schon einmal gefunden und
behoben worden; diese zweite, ältere Kopie derselben Logik blieb dabei
stehen. Jetzt nutzen beide dieselbe Funktion.

**Messbar:** im nachgestellten Scroll-Versuch (6 Einzelschritte) fielen
die Abweichungen gegenüber einem vollen Neuaufbau von **2.785 auf 107**
Bildpunkte (CRT) und von **105.717 auf 2.190** (HDMI). Das ist zugleich
der größte Teil der lange bekannten Abweichungen im leichten
Zeichenpfad — die Fallzahl fiel dabei nur von 24 auf 22, weshalb
`diag_lightpath.py` jetzt zusätzlich die Zahl abweichender Bildpunkte
ausgibt: ohne die hätte diese Verbesserung wie ein Rundungsfehler
ausgesehen.

`tools/test_crt_layout.py` prüft jetzt beides — die Bedingung selbst
(nachrechenbar, ohne Testdaten) und das tatsächliche Bild nach echtem
Scrollen.


**BUGFIX: F4 wirkte nach einem Kaltstart nicht**
(Build 63 — Nutzer-Rückmeldung: „Autostart kann ich im Menü ausstellen,
aber die F4-Funktion, dass das Frontend dann startet, wenn ich den MiSTer
kalt starte und Autostart deaktiviert habe, das funktioniert nicht"):

Mein Entwurfsfehler. Der Schalter legt eine Schalterdatei an und startet
den Wächter sofort — beides funktionierte. Beim **Booten** muss den
Wächter aber jemand starten, und dafür gibt es genau einen Haken: eine
Zeile in `/media/fat/linux/user-startup.sh`. Die setzten bisher
**ausschließlich** die Installer bzw. `Frontend_Update.sh`.

Wer seine Dateien von Hand kopiert (oder aus anderem Grund keinen dieser
Wege gelaufen ist), hatte damit den Menüpunkt, den Wächter und die
Schalterdatei — aber keinen Starter. Der Schalter wirkte bis zum
nächsten Ausschalten und war nach einem Kaltstart still wirkungslos.
Schlimmer noch: der Menüpunkt meldete in **jedem** Fall Erfolg, die Zeile
sah aus wie jede andere eingeschaltete Option. Eine Funktion, deren
Funktionieren still an einem Schritt hängt, den der Nutzer weder sieht
noch prüfen kann.

Drei Änderungen:

1. **Der Schalter trägt die Startzeile jetzt selbst nach** — über
   denselben abgesicherten Schreibweg wie der Autostart-Schalter
   (Sicherheitskopie, Nebendatei, Rückleseprobe, atomares Ersetzen). Kein
   Installer mehr nötig.
2. **Selbstheilung beim Start:** ist der Schalter an und die Zeile fehlt,
   wird sie beim nächsten Start des Frontends einmal nachgetragen. Das
   repariert bestehende Installationen, ohne dass jemand etwas tun muss.
3. **Ehrliche Rückmeldung:** klappt das Nachtragen nicht, meldet der
   Menüpunkt das ausdrücklich statt Erfolg. Und solange die Zeile fehlt,
   trägt die Menüzeile selbst den Zusatz „(nicht nach einem Kaltstart!)".

Beim Ausschalten bleibt die Startzeile bewusst stehen: ohne
Schalterdatei ist sie wirkungslos, und jedes unnötige Schreiben in
`user-startup.sh` ist ein Risiko, das nichts einbringt.

Abgesichert durch drei neue Testblöcke in `tools/test_f4_hotkey.py`
(Kaltstart-Fall, Selbstheilung inkl. „schreibt nur einmal", und dass ein
auskommentierter Eintrag nicht als vorhanden zählt).


**Autostart im Menü an- und abschaltbar**
(Build 62 — Nutzerfrage: „ist da jetzt quasi ein Schalter unter
System/Optionen drin, der den Autostart an- und ausschaltbar macht, und
wenn er ausgeschaltet ist, muss man im OSD nur F4 drücken?"):

Ehrliche Antwort war: nur die Hälfte. Build 61 brachte den F4-Schalter,
einen Schalter für den Autostart selbst gab es im Menü **nie** — der
wurde einmalig beim Installieren eingerichtet und ließ sich danach nur
per SSH wieder loswerden.

Neuer Punkt unter System → Optionen → **Verhalten**, direkt über dem
F4-Schalter (die beiden gehören zusammen; wer den einen sucht, findet so
den anderen gleich mit). Ist der Autostart aus und F4 noch nicht
eingeschaltet, weist die Meldung ausdrücklich auf den Schalter darunter
hin.

**Warum nicht die vorhandene `disable`-Datei:** die prüfen auch
`Frontend_Start.sh` und der F4-Wächter. Damit wäre alles aus, auch der
manuelle Start und F4 — das genaue Gegenteil des Wunsches.

**Der Schalter entfernt die Zeile wirklich** (so gewünscht), statt sie
nur über eine Schalterdatei zu neutralisieren. Damit ist das die
heikelste Schreiboperation im Projekt: `/media/fat/linux/user-startup.sh`
gehört dem MiSTer, ein kaputter Inhalt legt den nächsten Boot lahm — und
zwar ohne dass man noch an ein Menü käme, um es zurückzunehmen. Vier
Sicherungen dagegen:

1. Vor der **ersten** Änderung eine Sicherheitskopie
   (`user-startup.sh.dragend_backup`), die später nie überschrieben wird
   und damit den Originalzustand bewahrt.
2. Geschrieben wird nie in die Zieldatei, sondern in eine Nebendatei im
   gleichen Verzeichnis.
3. Deren Inhalt wird **zurückgelesen und geprüft**, bevor sie an ihren
   Platz kommt (Shebang da, gewünschte Änderung tatsächlich drin). Fällt
   die Probe durch, wird sie verworfen.
4. Erst dann `os.replace()` — auf demselben Dateisystem atomar: entweder
   die alte oder die neue Fassung, nie eine halb geschriebene.

Alle anderen Zeilen bleiben zeichengenau erhalten — fremde Einträge, ein
NAS-Mount des Nutzers und der Eintrag des F4-Wächters (der enthält
`f4_hotkey.sh`, nicht `frontend_boot.sh`).

Abgesichert durch `tools/test_autostart.py`, mit Schwerpunkt auf den
Fehlerwegen: nicht beschreibbares Verzeichnis, künstlich scheiterndes
`os.replace()` (der einzige dieser Wege, der auch als root
aussagekräftig ist), durchgefallene Rückleseprobe. In allen dreien muss
die Zieldatei zeichengenau unverändert bleiben. Dazu: auskommentierter
Eintrag zählt nicht als „an", mehrfaches Umschalten trägt nichts doppelt
ein, nicht sauber kodierte Bytes in der Datei überleben unverändert.


**F4 startet das Frontend, CRT-Layout enger gefasst**
(Build 61 — Nutzerwünsche: „können wir das Script Frontend_Start.sh,
wenn einer kein Autostart eingerichtet hat, irgendwie auf F4 im OSD
einbinden?" und „haben wir irgendwie ne Möglichkeit, das Frontend im
CRT-Modus hübscher aussehen zu lassen?"):

**F4-Schnellstart (neu, standardmäßig aus).** Erst nachgesehen statt
geraten: MiSTers Menü-Code wertet F12, F1, F11, F10, F9, F7, ESC, BACK,
BACKSPACE und ENTER aus — **F4 kommt dort nicht vor**, die Taste ist
tatsächlich frei. Eine Möglichkeit, eine Taste per `MiSTer.ini` auf ein
Skript zu legen, gibt es dagegen nicht (die komplette Optionsliste
wurde danach durchsucht). Ohne Änderung an MiSTer selbst bleibt nur ein
eigener Wächter: `frontend/f4_hotkey.py`, gestartet über
`frontend/f4_hotkey.sh` aus `user-startup.sh`.

Bewusst zurückhaltend gebaut — was er *nicht* tut, ist hier der
wichtigere Teil:

- Kein `EVIOCGRAB`: er liest nur mit, MiSTers Menü bekommt jeden
  Tastendruck weiterhin unverändert.
- Reagiert nur, solange `/tmp/CORENAME` `MENU` meldet — mitten im Spiel
  passiert auf F4 nichts.
- Startet nichts, wenn `/tmp/frontend.lock` einen lebenden Prozess
  nennt.
- Standardmäßig aus. Der Eintrag in `user-startup.sh` wird zwar immer
  gesetzt (auch bei `--no-autostart`, denn genau diese Nutzer sind die
  Zielgruppe), ist ohne die Schalterdatei aber wirkungslos: der Wrapper
  beendet sich sofort wieder. Dadurch muss zum Ein-/Ausschalten **nie**
  an `user-startup.sh` gerührt werden — einer Datei, die dem MiSTer
  gehört und bei der ein Fehler den nächsten Boot lahmlegt.

Der Menüpunkt liegt unter System → Optionen → Verhalten und wirkt
sofort: beim Einschalten wird der Wächter mitgestartet, beim
Ausschalten beendet er sich innerhalb einer Sekunde selbst. Ehrliche
Grenze: nur Tastatur. Im MiSTer-Menü sind die Gamepad-Tasten bereits
vollständig von MiSTer belegt, eine freie gibt es dort nicht.

Abgesichert durch `tools/test_f4_hotkey.py` (u.a.: Tastencode gegen
`input-event-codes.h` des Systems geprüft; Loslassen und Halten lösen
nicht aus; `CORENAME` mit Nullbytes/CR/Leerzeichen wird korrekt
erkannt; verwaiste Sperrdatei; Installation/Update/Deinstallation
greifen ineinander).

**CRT-Layout.** Hier hatte ich zuerst eine falsche Diagnose gestellt
(„die Logos werden mittig beschnitten") — das betrifft die
Seiten-Hintergrundbilder aus `bg/`, nicht die Sysart-Logos, die sauber
eingepasst werden. Nach dem Nachrendern echter Bilder in beiden
Auflösungen zeigte sich der tatsächliche Mangel: mehrere Abstände
standen als **feste Pixelzahl** im Layout (Kopfblock 46, Zeilenhöhe 15,
Abstand zur Boxart-Karte 20, Kategorie-Zeilenhöhe 22). Sie skalieren
zwar über `s = H//360` mit — aber `s` ist bei 240 *und* bei 480 Zeilen
gleich 1, die Abstände belegten bei 240 Zeilen also den doppelten
Bildanteil.

| | CRT vorher | CRT jetzt | HDMI |
|---|---|---|---|
| Zeichen pro Zeile | 17 | **20** | 35 |
| Sichtbare Spiele | 10 | **13** | 17 |
| Kategorien im Hauptmenü | 7 | **9** | 12 |
| Anteil für den Kopfblock | 24 % | **20 %** | 18 % |
| Breite der Logo-Spalte | 34 % | **28 %** | 18 % |

Greift nur unterhalb von 400 Bildzeilen (`KOMPAKT_H`) — 640x480 zeigte
nachgemessen bereits 35 Zeichen und 24 Zeilen und braucht nichts.
HDMI und 480p bleiben unverändert, was `tools/test_crt_layout.py`
ausdrücklich mitprüft. Der Overscan-Sicherheitsrand bleibt ebenfalls
unangetastet: Platz am Bildrand zu holen wäre bei einer Röhre genau der
falsche Ort. Beim Bauen lief der Auswahlbalken zweimal in die
Kopfzeile — beide Male beim Nachrendern gesehen, nicht beim Rechnen;
die Freiraum-Rechnung ist deshalb jetzt Teil des Tests.

**Dokumentation.** `README_EN.md` führte durchweg noch die alten
Skriptnamen (`install.sh`, `install_offline.sh`,
`Scripts/install_frontend.sh`, `uninstall.sh`) und schickte Leser damit
zu Dateien, die es seit der Umbenennung nicht mehr gibt — komplett auf
die `Frontend_*.sh`-Namen umgestellt. In `README.md` waren außerdem
zwei Tabellenzeilen in einer Zeile zusammengelaufen.


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

**NAS-Nachtrag: das automatische Nachziehen lief bei jedem Start**
(Build 60 — Nutzer-Rückmeldung: "scannt nun ganz kurz … nope, scannt
schon wieder"):

Build 59 hat den ersten Teil behoben (die Signatur), aber nicht den
zweiten. „Ganz kurz" war schon der Hinweis: es wurde nur noch
*inkrementell* eingelesen, die Signatur passte also fast.

Der übersehene Teil sitzt in `_maybe_rescan_for_late_mount()` — dem
Sicherheitsnetz für Netzlaufwerke, die erst nach dem Start auftauchen.
Es prüfte:

```python
if not _has_network_mount():
    return
# -> gesehen! Spieleliste komplett neu aufbauen
```

`_has_network_mount()` sagt aber nur, **dass** eine Freigabe eingehängt
ist — nicht, ob sie **neu** ist. Bei jemandem, dessen NAS beim
Hochfahren ohnehin rechtzeitig da ist, war die Bedingung damit bei
**jedem** Start erfüllt: rund acht Sekunden nach dem Start lief ein
erzwungener kompletter Neuaufbau (`force_rescan=True`) — also genau das
Verhalten, das dieses Sicherheitsnetz eigentlich verhindern soll.

**Behoben:** das Frontend merkt sich jetzt beim Einlesen, ob dabei schon
Ordner von einer Freigabe dabei waren (`letzter_scan_hatte_nas()`). War
das der Fall, gibt es nichts nachzuziehen und das Sicherheitsnetz legt
sich sofort schlafen. Nur wenn die Freigabe beim Einlesen tatsächlich
gefehlt hat, wird später nachgezogen — so war es gemeint.

- **Neue Diagnose `SIG-DIFF`:** passt die Signatur nicht, schreibt das
  Frontend jetzt ins Log, WELCHE Einträge sich unterscheiden (nur im
  Cache / nur jetzt / andere Zeitmarke), dazu die aktuellen
  Netz-Einhängepunkte und Spiele-Wurzeln. Läuft ausschließlich im
  Fehlerfall — bei passendem Cache ist die Funktion längst zurück.
  Sollte es bei jemandem weiterhin scannen, steht die Ursache damit
  wörtlich im Log statt im Bereich der Vermutungen.

**Spiele auf einem NAS wurden bei JEDEM Start neu eingelesen**
(Build 59 — Nutzer-Rückmeldung über einen Bekannten: "seine Spiele liegen
auf einem NAS-Server, bei jedem Neustart werden die Spiele wieder neu
eingelesen, das ist Mist"):

Die Ursache ließ sich im Code festmachen. Die Signatur, an der das
Frontend erkennt "hat sich an der Sammlung etwas geändert?", kennzeichnet
jeden Ablageort mit einer kurzen Kennung. Die lautete:

```python
tag = "usb:" if "/media/usb" in base else "fat:"
```

Ein NAS hängt üblicherweise unter `/media/fat/cifs/...` — es bekam damit
**dieselbe Kennung wie die SD-Karte**. Das hatte zwei Folgen:

1. Beim Kaltstart ist die Freigabe oft noch nicht eingehängt. Die frisch
   gebildete Signatur enthält die NAS-Ordner dann nicht, der gespeicherte
   Stand (vom letzten Lauf **mit** NAS) schon → Unterschied → komplett neu
   einlesen. Für USB gibt es dafür längst ein Sicherheitsnetz ("Cache
   erwartet USB, USB fehlt → warten statt neu einlesen") — das prüfte aber
   ausschließlich auf `usb:` und sprang beim NAS mangels eigener Kennung
   **nie** an.
2. Ein Ordner `SNES` auf der Karte und einer auf dem NAS ergaben denselben
   Signatur-Schlüssel `fat:SNES`. Beim inkrementellen Vergleich waren sie
   nicht auseinanderzuhalten.

**Behoben:** Netzwerk-Freigaben bekommen eine eigene Kennung `nas:`
(ermittelt aus `/proc/mounts`, also unabhängig davon, wo die Freigabe
gerade eingehängt ist — ein Umhängen löst weiterhin keinen Neuscan aus).
Und das Sicherheitsnetz gilt jetzt auch für sie: erwartet der
gespeicherte Stand NAS-Ordner, sind aber gerade keine da, wird auf die
Einhängung gewartet (und danach noch auf einen stabilen Ordnerinhalt,
weil eine frisch eingehängte Freigabe kurz leer erscheinen kann) statt
die ganze Sammlung sinnlos neu einzulesen.

Das Warten läuft hier bewusst **unabhängig** von der Option "Beim Start
auf NAS/Netzwerk warten": es wird nur ausgelöst, wenn der gespeicherte
Stand selbst beweist, dass zuletzt von einer Freigabe gelesen wurde. Dann
ist Warten keine Vermutung mehr — dieselbe Überlegung wie beim
USB-Zweig, der ebenfalls ohne Option auskommt.

**Einmalig nach dem Update:** der gespeicherte Stand trägt noch die alten
`fat:`-Schlüssel, der erste Start liest deshalb noch einmal komplett ein.
Ab dem zweiten Start ist Ruhe.

Neuer Test `tools/test_nas_cache.py`.

**Die Cover werden schon beim ERZEUGEN grob verkleinert** (Build 58 —
Nutzer-Rückfrage: "kann das sein, dass du das bei den Boxarts bei den
Spielen/ROMs selbst vergessen hast?"):

**Ja, genau da.** Build 57 hat nur die Skalierung beim *Anzeigen*
verbessert. Die `.art`-Dateien der Spiele-Cover werden aber von
`frontend/mister_boxart.py` überhaupt erst erzeugt — und das Skript hat
dabei weiterhin Nearest-Neighbor verwendet, also Bildzeilen und -spalten
weggeworfen. Was dort verloren geht, kann später keine noch so gute
Anzeige-Skalierung zurückholen.

Dort wiegt der Mangel sogar schwerer als beim Anzeigen: die
heruntergeladenen Vorlagen sind mehrere hundert bis über tausend Pixel
breit, das Ziel misst 300×350 (hd) bzw. 104×168 (sd). Bei einer
Verkleinerung auf ein Drittel trägt jeder übernommene Bildpunkt die
Information von neun — acht davon fielen einfach weg.

Kurioserweise war das Gegenstück für den PC (`PC-Tools/art_convert.py`)
immer schon in Ordnung: es nutzt Pillow mit LANCZOS. Auf dem MiSTer
selbst ging das nicht, weil dort bewusst keine Bildbibliothek
vorausgesetzt wird — deshalb jetzt dieselbe Mittelung von Hand, ohne
zusätzliche Abhängigkeit.

- **Neuer Aufruf `mister_boxart.py hd neu`**: erzeugt auch bereits
  vorhandene Cover noch einmal. Ohne diesen Schalter würden genau die
  Cover, die man schon hat, für immer übersprungen — die Verbesserung
  käme also bei niemandem an, der seine Bilder bereits geladen hat.
  Abbrechen (Strg+C) und später fortsetzen geht wie gehabt.
- **Laufzeit, ehrlich gerechnet:** pro Cover 140 ms statt 13 ms (hd)
  bzw. 73 ms statt 2 ms (sd) auf einer schnellen Sandbox. Das klingt
  nach viel, fällt aber neben dem Herunterladen jedes einzelnen Bildes
  kaum ins Gewicht — bei 2000 ROMs sind das rund vier Minuten
  zusätzlich auf einen Lauf, der ohnehin deutlich länger dauert.
- Eine Vorlage, die bereits klein genug ist, wird jetzt gar nicht mehr
  angefasst (vorher lief sie unnötig durch die Skalierschleife).
- `tools/test_cover_scaling.py` deckt jetzt beide Stellen ab —
  Anzeigen UND Erzeugen.

**Boxart wird jetzt richtig verkleinert + zwei weitere Messblindflecke**
(Build 57):

- **Cover-Verkleinerung: Flächenmittel statt Wegwerfen**
  (Nutzer-Rückmeldung: "auf halb sehen jetzt die Boxarts pixelig aus …
  auf viertel läuft das Scrollen super, aber auch hier sehen die
  Boxarts verpixelt aus"). Ursache war eine Altlast im Skalierer: er
  hat beim Verkleinern schlicht **Bildzeilen und -spalten weggeworfen**
  (Nearest-Neighbor). Bei fotoartigen Bildern wie Boxart erzeugt das
  genau den ausgefransten Eindruck — feine Strukturen fallen je nach
  Rasterlage mal ganz weg, mal bleiben sie hart stehen. Jetzt wird über
  die zusammenfallenden Bildpunkte gemittelt.

  Warum das erst jetzt auffiel: die Cover-Fläche ist bei voller
  Auflösung **733×909** groß, ein übliches Cover passt hinein und wird
  gar nicht angefasst. Erst mit dem neuen Menüpunkt schrumpft sie auf
  **377×465** (halb) bzw. **179×223** (viertel) — und damit wurde zum
  ersten Mal überhaupt verkleinert.

  **Laufzeit, ehrlich benannt:** das Mitteln kostet rund das Zehnfache
  (gemessen 135 ms statt 11 ms für ein 600×800-Cover auf einer
  schnellen Sandbox, auf der MiSTer-CPU entsprechend mehr — grob ein
  bis zwei Sekunden). Das fällt **nur beim allerersten Betrachten** an:
  beim Scrollen wird ohnehin nicht skaliert, und das Ergebnis landet im
  Zwischenspeicher auf der SD-Karte. Der Hinweis darauf steht jetzt in
  der README, und das Frontend sagt es nach dem Umschalten selbst.

  Wichtig dabei: `THUMB_ALGO_VERSION` wurde hochgezählt, damit bereits
  gespeicherte Miniaturen aus dem alten Verfahren **nicht** weiter
  getroffen werden — sonst käme die Verbesserung ausgerechnet bei den
  Covern nicht an, die man am häufigsten anschaut. Alte Einträge
  veralten von selbst aus dem Cache heraus, es muss nichts von Hand
  gelöscht werden. Neuer Test `tools/test_cover_scaling.py`.

- **Hintergrundbild-Aufbau war nicht gemessen** (beim Nachgehen des
  Hakelns beim Zurückgehen gefunden). `BG.get()` setzt bei einem
  Cache-Fehltreffer den kompletten bildschirmfüllenden Hintergrund neu
  zusammen — bei 1920×1080 sind das 8,3 MB, zeilenweise in Python.
  Nachgemessen: **41–67 ms** auf dieser Sandbox, auf dem MiSTer
  entsprechend deutlich mehr. Das lag genau zwischen der "Hausarbeit"
  und dem `bg=`-Zeitnehmer und tauchte damit in **keiner** Messung auf.
  Jetzt eigener Posten `bgbild=` in `PERF split` und in der
  RUCKLER-Zeile.

- **Hintergrund-Zwischenspeicher von 2 auf 4 Plätze.** Mit nur zwei
  Plätzen genügte das Hin- und Herwechseln zwischen drei Systemen,
  damit jeder Wechsel wieder einen kompletten Neuaufbau auslöste — ein
  plausibler Teil des "hängt ab und zu kurz" beim Zurückgehen. Preis
  ehrlich benannt: jeder Platz kostet einen vollen Bildschirmpuffer,
  bei 1080p rund 8,3 MB, bei vier Plätzen also etwa 33 MB. Auf einem
  MiSTer mit ~1 GB RAM vertretbar; deshalb 4 und nicht 8. Mit
  kleinerer Menü-Auflösung sinkt der Bedarf entsprechend mit.

**Bugfix am Menü-Auflösung-Schalter + Ruckler-Suche** (Build 56):

- **BUGFIX (Nutzer-Rückmeldung: "ich merke da keinen Unterschied, egal
  was ich auswähle und dann Neustart mache"):** der Schalter hat
  tatsächlich nichts bewirkt — mein Fehler, und zwar ein grundsätzlicher.
  Ich hatte `fb_size` in einen vermeintlich "globalen Teil" der
  MiSTer.ini vor die erste `[Sektion]` geschrieben. **Diesen globalen
  Teil gibt es nicht.** Im ini-Parser des MiSTers (`cfg.cpp`,
  `ini_parse()`) startet die Variable `section` auf 0, und Zeilen werden
  nur ausgewertet, solange eine Sektion aktiv ist
  (`else if (section) ini_parse_var(line);`) — alles vor der ersten
  Sektionszeile wird **stillschweigend verworfen**. Die Einstellung kam
  also nie beim MiSTer an, und jede Stufe sah zwangsläufig gleich aus.
  Der Wert steht jetzt in der `[MiSTer]`-Sektion (die laut
  `ini_get_section()` immer greift, unabhängig vom geladenen Core); fehlt
  sie, wird sie angelegt. Der Test hat den Fehler nicht gefunden, weil er
  nur die *eigene* Lese-/Schreiblogik gegen sich selbst geprüft hat, nicht
  gegen das Format, das MiSTer tatsächlich liest — er prüft jetzt gezielt,
  dass ein Schlüssel vor der ersten Sektion NICHT zählt.

- **Ruckler-Detektor** (Nutzer-Rückmeldung: "wenn ich nach unten gedrückt
  halte, stockt es nach ein paar Sekunden einmal kurz — beim Hochhalten
  genauso, und im Hauptmenü auch"). So ein Stocken lässt sich durch
  Codelesen kaum finden, weil die Ursache gerade die Stelle ist, die
  *selten* etwas tut. Statt weiter zu raten misst die Hauptschleife jetzt
  ihre eigene Runde und schreibt eine Zeile ins Log, sobald eine davon
  spürbar lang war — mit Aufteilung, wohin die Zeit ging:

  ```
  RUCKLER: 340 ms busy (stream=2 haus=310 bg=1 restore=1 rows=18 art=6 flip=2 | vorige Aktion=down Seite=1)
  ```

  Neu ist dabei vor allem `haus=` — die sechs Aufgaben, die vor jedem
  Zeichnen laufen (Netzwerkstatus, Netzlaufwerk-Suche,
  RetroAchievements-Wiederholversuch, Uhrzeit-Abgleich …). Die tun fast
  immer nichts, prüfen aber jeweils eine eigene Uhr und schlagen dann
  alle paar Sekunden einmal richtig zu — genau das Muster aus der
  Beschreibung, und bisher in **keiner** Messung enthalten: die
  PERF-Zeile beginnt erst beim eigentlichen Zeichnen. Der Detektor ist
  bewusst immer aktiv (zwei Zeitabfragen pro Eingabe, geschrieben wird
  nur im Ausnahmefall) — ein extra einzuschaltender Schalter würde einen
  unregelmäßigen Ruckler typischerweise verpassen. Schwelle 80 ms:
  normale Bildaufbauten schlagen nie an, sichtbares Stocken sicher.

- **Zwei vorbeugende Maßnahmen** an den beiden Kandidaten, die zeitlich
  am besten passen: die Netzwerkstatus-Abfrage (alle 5 s, ein
  Systemaufruf mit bis zu 100 ms Zeitlimit) und die Netzlaufwerk-Suche
  (alle 8 s, ein Dateisystem-Zugriff) laufen nicht mehr mitten in einer
  gehaltenen Taste, sondern erst in der nächsten Atempause — dieselbe
  Zeitspanne, die auch Laufschrift und Puls beim Scrollen aussetzen
  lässt. Ein Netzwerk-Symbol darf beim Scrollen ein paar Sekunden alt
  sein. Sollte eine der beiden die Ursache sein, ist der Ruckler damit
  weg; falls nicht, benennt der Detektor beim nächsten Auftreten den
  wahren Verursacher.

**Neues System: Virtual Boy** (Build 55, Nutzerwunsch: "wenn der Core
verfügbar ist und ROMs dazu vorhanden sind, wie die anderen Kategorien
auf der Hauptseite hinzufügen"):

- Neue Kategorie **Virtual Boy** im Hauptmenü — als OPTIONALES System
  eingetragen, also nach demselben Muster wie der SNES-ALTTP-Tracker:
  sie erscheint nur, wenn **beides** stimmt, Core installiert UND ROMs
  im Ordner `games/VirtualBoy` vorhanden. Fehlt eines von beiden, taucht
  sie gar nicht erst auf — kein leerer oder ausgegrauter Platzhalter.
  Der Virtual-Boy-Core gehört nicht zur Standardausstattung eines
  MiSTers, er muss über den Downloader nachinstalliert werden.
- **Core-Erkennung mit Platzhalter.** Die bisherige Prüfung verglich
  einen festen Dateipfad — richtig für einen von Hand installierten
  Einzel-Core wie `SNES_Tracker.rbf`, aber falsch für offizielle Cores:
  die tragen den Build-Stempel im Namen (`VirtualBoy_20240115.rbf`) und
  heißen nach jedem Core-Update anders. Ein fester Pfad hätte genau
  einmal gepasst und die Kategorie beim nächsten Update stillschweigend
  verschwinden lassen. `core_check_path` darf jetzt ein Muster sein; bei
  mehreren vorhandenen Ständen gewinnt der neueste. Feste Pfade
  funktionieren unverändert weiter.
- **Systemlogo** `sysart/VIRTUALBOY.art` liegt bei (900 px breit wie die
  übrigen Logos). Die Bildvorlage hatte das Transparenz-Karomuster als
  echte Pixel eingebrannt (20×20-Raster in Weiß/Hellgrau, wie es beim
  Speichern einer Vorschau entsteht). Das Muster wurde rechnerisch
  wieder entfernt: das Raster ist exakt bekannt, dadurch ließen sich
  auch die halbtransparenten Kantenpixel korrekt zurückrechnen statt
  nur hart abzuschneiden. Die weiße Innenfläche des Nintendo-Logos
  wurde dabei bewusst erhalten — sie ist Teil des Logos und sieht dem
  Karomuster zum Verwechseln ähnlich.
- Eigene **Akzentfarbe** (235, 45, 45): das Gerät konnte nur Rot
  darstellen, das Logo ist rot, die Spiele sind rot. Kräftiger und
  weniger ins Rosa gehend als NES und Master System, damit die drei
  roten Systeme unterscheidbar bleiben.
- Die MGL-Parameter (`.vb`, delay 1, Typ `f`, Index 1) stammen aus
  derselben gepflegten Systemdatenbank wie die übrigen Systeme. Gegen
  die bekannten Werte der bereits laufenden Systeme abgeglichen: SNES,
  NES, Game Boy und Mega Drive stimmen dort exakt mit unseren seit
  Langem funktionierenden Werten überein, die Quelle ist für Virtual
  Boy also belastbar. Passt außerdem zur Core-Beschreibung selbst
  (`"FS1,VB ,Load ROM;"`).
- Neuer Test `tools/test_virtualboy.py` (26 Prüfungen): die drei
  Sichtbarkeits-Bedingungen, der Umgang mit dem Datumsstempel, sowie
  Logo-Datei, Anzeigename und Akzentfarbe.

**Einschränkung, ehrlich benannt:** der eigentliche Spielstart ließ sich
hier nicht prüfen — dafür braucht es den Core auf echter Hardware. Sollte
ein Spiel nicht starten und stattdessen das Core-Menü offen bleiben, ist
fast immer der MGL-Index schuld; das wäre eine Ein-Zeichen-Änderung in
`fe/systems.py`.

**HDMI-Performance, Runde 4** (Build 54 — auf die Frage "hast du noch
einen Ansatz, um den HDMI-Modus performancetechnisch flüssiger zu
kriegen?"):

Zuerst gemessen statt geraten. Ein Seitenaufbau auf 1920×1080 kostete
3,28 ms reine Zeichenzeit, aufgeteilt in: **Cover-Panel 67 %**,
**`_restore_row_bg()` 39 %**, Rest Listenzeilen/Text. Derselbe Aufbau
kostet auf CRT (320×240) nur 0,46 ms — also rund ein Sechstel. Der
Aufwand hängt fast vollständig an der Pixelzahl, und genau daran setzen
die beiden Änderungen an.

- **Zwei heiße Schleifen entschlackt** (bitgenau gleiches Bild, keine
  Verhaltensänderung):
  - `_restore_row_bg()` legte pro Bildzeile mit `cur_bg[off:end]` eine
    vollständige Zwischenkopie an (bei 700 Pixel Breite ~2,8 KB), die
    direkt danach kopiert und sofort weggeworfen wurde — nur, um eine
    Längenprüfung machen zu können. Mit `memoryview` entfällt diese
    Zwischenkopie ersatzlos; die Längenprüfung wird einmal vorab auf die
    Zeilenspanne angewandt statt pro Zeile. Gemessen **0,826 → 0,526 ms
    (−36 %)** für 700×880.
  - `rect()` schlug pro Bildzeile zweimal Attribute nach (`self.buf`,
    `self.stride`), rechnete den Offset neu aus und wertete — obwohl
    `scanlines` fast immer aus ist — jedes Mal eine Bedingung samt
    Modulo aus. Jetzt lokale Variablen, fortlaufend addierter Offset und
    eine eigene minimale Schleife für den häufigen Fall. Gemessen
    **0,427 → 0,382 ms (−11 %)** für 700×800.
  - Zusammen: **Seitenaufbau 3,28 → 2,87 ms (−12,5 %)**. Beide
    Umbauten wurden über 620 bzw. 800 zufällige Geometrien (inkl. aller
    Randfälle: Puffergrenzen, negative Positionen, zu kurzer
    Hintergrundpuffer, Scanlines) gegen die alte Fassung geprüft —
    **null abweichende Bytes**.

- **Neuer Menüpunkt "Menü-Auflösung"** (System → Optionen → Anzeige,
  Nutzerwunsch: "eventuell unter System und dann unter Optionen dafür
  einen Schalter einbauen, der beim Neustart das an- und ausschaltet").
  Schaltet `fb_size` in der MiSTer.ini durch: **voll → halb → viertel →
  voll**. MiSTer betreibt den Linux-Framebuffer dann kleiner und
  skaliert per Hardware wieder auf die Ausgabeauflösung hoch — bei
  halber Größe ist das **ein Viertel der Pixel**, und zwar bei allem:
  Hintergrund füllen, Zeilen zeichnen, Text setzen, Hintergrund
  wiederherstellen und die fertige Seite in den Framebuffer kopieren.
  Am Frontend selbst muss dafür nichts geändert werden, es liest die
  Geometrie beim Start aus `/sys/class/graphics/fb0` und skaliert sein
  Layout automatisch mit.

  Der Preis wird offen genannt: das Bild wird sichtbar weicher bzw.
  klotziger, weil die Hardware wieder hochrechnet. Deshalb Standard
  unverändert "voll" und ein Punkt zum Ausprobieren statt einer stillen
  Voreinstellung.

  Details der Umsetzung:
  - Die Änderung wirkt **erst nach einem Neustart** (die
    Framebuffer-Größe legt MiSTer beim Hochfahren fest). Anders als beim
    CRT-Umschalten wird deshalb NICHT sofort neu gestartet — beim
    Durchschalten von drei Stufen wäre ein erzwungener Neustart pro
    Tastendruck eine Zumutung. Stattdessen ein deutlicher Hinweis in der
    Zeile selbst UND als Meldung nach dem Umschalten.
  - `fb_size` wird als **globaler** Schlüssel geschrieben (vor der ersten
    `[Sektion]`), bewusst nicht in den `[Menu]`-Block: den legt der
    CRT-Schalter komplett an und entfernt ihn wieder, die Einstellung
    wäre sonst beim nächsten CRT-Umschalten stillschweigend weg.
  - Geschrieben wird **atomar** (Temp-Datei + `os.replace`), dieselbe
    Absicherung wie beim CRT-Schalter: ein Abbruch mitten im Schreiben
    darf die MiSTer.ini nicht zerstören.
  - Der Punkt erscheint **nur im HDMI-Modus**. Im CRT-Modus ist der
    Framebuffer ohnehin nur 320×240 — halbiert (160×120) wäre er
    unlesbar, und zu gewinnen gäbe es dort auch nichts. Schaltet man
    per CRT-Schalter in den CRT-Modus, wird eine gesetzte Verkleinerung
    automatisch zurückgenommen, da der Punkt dort nicht mehr sichtbar
    (und damit nicht mehr selbst korrigierbar) wäre.
  - Neuer Test `tools/test_fb_size.py` (26 Prüfungen): der einzige Test
    im Projekt, der eine Datei außerhalb des Frontends betrifft. Die
    MiSTer.ini gehört dem MiSTer, nicht uns — entsprechend gründlich
    wird geprüft, dass außer der einen Zeile nichts verändert wird und
    die Datei nach einem Rundlauf **wortgleich** wie vorher ist.

**Aufräumen und Testabdeckung** (Build 53, keine Verhaltensänderung im
Normalbetrieb — auf Nutzerfrage "kann ich irgendwo noch was optimieren
oder besser machen oder fixen?"):
- **Dateikopf ausgelagert:** der Modul-Kommentar am Anfang von
  `frontend/frontend.py` war auf 3.362 Zeilen bzw. rund 202.000 Zeichen
  angewachsen — 26 % der gesamten Datei, bevor die erste Codezeile kam.
  Python lädt so einen Kommentar bei jedem Start als Zeichenkette in
  den Speicher, gelesen hat ihn kein einziger Codepfad (geprüft:
  `__doc__` wird nirgends verwendet). Vor allem machte er die
  eigentliche Programmlogik in Editoren und bei der Suche schwer
  auffindbar. Der komplette Text steht jetzt wortgleich in
  `docs/ENTWICKLUNGSHISTORIE.md`; im Dateikopf bleiben Projektname,
  Steuerungsübersicht und Startbefehl (597 statt 202.204 Zeichen).
  Verifiziert: der Codeteil der Datei ist byte-identisch geblieben.
- **Toter Code entfernt:** `Framebuffer.glow_border_fast()` hatte seit
  dem Entfernen des Leuchtrands ("glow Effekt komplett raus") keinen
  einzigen Aufrufer mehr. Funktion entfernt, die vier Kommentar-
  Verweise darauf sinngemäß auf "früher" umgestellt, damit die
  Begründungen in den Kommentaren nachvollziehbar bleiben.
- **Messblindfleck geschlossen:** die Wiederherstellung des
  Listenspalten-Hintergrunds (`_restore_row_bg()`) lag genau ZWISCHEN
  den beiden Zeitnehmern der `PERF split`-Zeile — `bg=` endete davor,
  `rows=` begann danach — und tauchte deshalb in keiner Messung auf,
  obwohl sie nachgemessen rund 0,6 ms bzw. gut ein Fünftel eines
  Seitenaufbaus kostet. Bei der Fehlersuche fehlte damit ein spürbarer
  Posten in der Summe. Neuer eigener Zähler:
  `PERF split: bg=... restore=... rows=...(n) art=... flip=... ms`.
- **Drei Testskripte ins Projekt aufgenommen** (`tools/`): sie waren
  bisher nur temporär zur Absicherung einzelner Bugfixes entstanden und
  gingen danach verloren, obwohl sie genau die Stellen abdecken, an
  denen es schon zweimal Regressionen gab.
  - `test_input_repeat.py` — Tastenwiederholung mit der echten
    `InputManager`-Logik: Anlaufsperre, verkürzter Richtungswechsel
    mitten im Scrollen, Achswechsel, Geister-Wiederholung nach
    "Zurück"/"OK", eigene langsamere Untergrenze für Seiten-Sprünge.
  - `test_overlay_redraw.py` — die Hinweisbox ("CRT aktiv") muss
    bitgenau restlos verschwinden, über beide Wege (weggeklickt und
    per Zeitablauf), in beiden Auflösungen.
  - `diag_lightpath.py` — bewusst DIAGNOSE statt Pass/Fail-Test:
    vergleicht den leichten Zeichenpfad bitgenau mit einem vollen
    Neuaufbau. Aktuell weichen 22 von 32 Fällen ab; diese Abweichungen
    sind bekannt, auf echter Hardware bisher nicht sichtbar und noch
    nicht aufgeklärt. Als roter Test würde das Skript den
    Regressionslauf entwerten, als Messinstrument ist es nützlich: die
    Zahl darf bei Änderungen am Zeichenpfad nicht steigen.
  Alle Skripte finden `frontend.py` jetzt relativ zum `tools/`-Ordner
  (vorher fester Pfad aus einer Entwicklungsumgebung, überschreibbar
  per `FRONTEND_PY`) — das galt auch für den bestehenden
  `regression_test.py`. `tools/README.md` beschreibt alle vier Skripte
  samt Sammelaufruf.

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
- Cover-Vorladen blockiert nicht mehr direkt nach dem Zurückgehen
  (Nutzer-Rückmeldung: "ich bin in einen Games-Ordner gegangen, habe die
  Taste nach unten 5–8 Sekunden gedrückt gehalten, dann auf Zurück
  gedrückt — und da kam wieder dieser 1-Sekunden-Hänger"). Das war ein
  **anderer** Hänger als der zuvor behobene, mit eigener Ursache.

  Das Vorladen der Nachbar-Cover lief unmittelbar nach dem Nachzeichnen,
  also schon 150 ms nach dem letzten Tastendruck. Es ruft `ART.get()`
  auf — die **rohe** Dekodierung des Originalbildes (Datei lesen +
  zlib-Entpacken). Dabei hilft der Festplatten-Cache nicht: Der greift
  nur für bereits skalierte Bilder. Verschärfend kommt hinzu, dass die
  Zeitbremse `PREFETCH_BUDGET` am **Anfang** jeder Runde geprüft wird —
  die erste Dekodierung läuft also immer vollständig durch, egal wie
  lange sie dauert. Nach 5–8 Sekunden Scrollen sind reihenweise Nachbarn
  noch nicht dekodiert, und genau dann summiert sich das zur gemeldeten
  Sekunde.

  Vorladen ist aber reine Vorratshaltung für den Fall, dass jemand stehen
  bleibt und danach weiterblättert — es muss nicht 150 ms nach dem
  letzten Tastendruck passieren. Es hat jetzt eine eigene, deutlich
  längere Ruhe-Schwelle (`PREFETCH_SETTLE`, 1 s), getrennt vom
  Nachzeichnen (das weiterhin bei 150 ms bleibt). Wer nach dem
  Zurückgehen sofort weiternavigiert, zahlt dafür gar nichts mehr.
  Verifiziert mit fünf Tests (bei 0,3 s wird nachgezeichnet aber nicht
  vorgeladen; bei 1,5 s wird vorgeladen; pro Ruhephase nur einmal; ohne
  ausgelassene Cover gar kein Aufbau; jede Eingabe macht beide Schalter
  wieder scharf) plus Regressionssuite (18/18).
- Der Nachlade-Aufbau nach jedem Stillstand läuft nur noch, wenn wirklich
  etwas nachzuladen ist (Nutzer-Rückmeldung: "ab und zu hab ich immer
  noch kleine Hänger, wenn ich mehrmals schnell links/rechts drücke oder
  gedrückt halte und dann sofort auf Zurück"). Der COVER_SETTLE-Nachlader
  feuerte bisher nach **jedem** Stillstand — unabhängig davon, ob
  überhaupt ein Cover übersprungen worden war — und kostet dabei einen
  kompletten Seitenaufbau (auf echter Hardware 45–110 ms). Sobald der
  Festplatten-Cache warm ist, sind aber alle Cover sofort da; im
  Gerätelog steht durchgehend `THUMB_CACHE Treffer: 0,9–6,4 ms`. Es gab
  also nichts nachzuladen, und der Aufbau war reine Verschwendung — genau
  in dem Moment, in dem man nach schnellem Blättern die nächste Taste
  drückt.

  Jetzt wird vermerkt, ob tatsächlich etwas ausgelassen wurde: an den
  drei Auslass-Stellen in `fe/art.py` sowie beim bewusst übersprungenen
  Boxart-Panel während schnellen Scrollens. Nur dann läuft der Nachlader.
  Wichtig für den Normalfall: Ein Treffer im Festplatten-Cache kehrt
  **vor** der Auslass-Prüfung zurück, setzt den Vermerk also gar nicht —
  bei warmem Cache entfällt der Aufbau damit vollständig. Bleibt der
  Vermerk stehen, bleibt der Nachlader scharf und holt es beim nächsten
  Leerlauf-Tick nach.
- Absturz-Protokoll übersteht jetzt einen Neustart. `/tmp` wird beim
  Neustart des MiSTer geleert — dadurch ging ein bereits protokollierter
  Absturz-Traceback bei der Fehlersuche zweimal verloren, bevor er
  ausgewertet werden konnte. Der Traceback wird deshalb zusätzlich nach
  `/media/fat/frontend_crash.log` geschrieben (anhängend, mit
  Zeitstempel, damit auch mehrere Vorfälle erhalten bleiben). Außerdem
  ist die Bildschirmausgabe im Absturz-Handler jetzt abgesichert: Wurde
  das Frontend über ein Script gestartet, dessen Terminal inzwischen weg
  ist, scheitert schon ein einfaches `print()` mit "Broken pipe" — und
  würde als Folgefehler den echten Absturzgrund verdecken.
- Stream-Spiegel wird jetzt tatsächlich flüssiger — die Bremse saß im
  Browser (Nutzer-Rückmeldung nach dem Absenken des Server-Takts auf
  0,15 s: "hab jetzt keinen Unterschied gemerkt"). Genau deshalb nicht:
  Der Server kodierte zwar häufiger, das Overlay im Browser fragte aber
  weiterhin nur alle **250 ms** nach (`INTERVAL_MS` in
  `stream_mirror.html`). Damit blieb die sichtbare Bildrate bei 4/s
  hängen, egal was das Frontend tat. Der Abruf liegt jetzt bei 120 ms und
  damit bewusst etwas **schneller** als der Server kodiert (150 ms) — so
  wird jedes neue Bild ohne zusätzliche Wartezeit abgeholt, statt im
  ungünstigsten Fall fast einen ganzen Takt liegenzubleiben. Häufigeres
  Nachfragen kostet nichts: Das Bild ist wenige KB groß und wird
  serverseitig nur aus dem Speicher herausgereicht, ohne erneut zu
  kodieren.
- Update-Text im Dialog wird nicht mehr mitten im Satz abgeschnitten
  (Nutzer-Foto: der Hinweis brach bei "Ursache" ab). Ursache war kein
  Fehler im Code, sondern ein zu langer `summary`-Eintrag in
  `LATEST_BUILD.json`: Dieser Text wird dem Nutzer unverändert im
  Update-Dialog angezeigt, und dort passen nur rund **96 Zeichen auf CRT**
  bzw. 216 auf HDMI — die betreffende Zusammenfassung war rund 380
  Zeichen lang. Der `summary` ist eine kurze Nutzer-Meldung in einem
  Satz; die ausführliche Beschreibung gehört hierher in die CHANGELOG.md.
  Die Längengrenze ist jetzt direkt an der Stelle dokumentiert, an der
  die Zusammenfassung herkommt (`fe/update_check.py`), damit das nicht
  wieder passiert.
- Update-Hinweis erscheint jetzt auch nach einem MiSTer-Neustart
  (Nutzer-Rückmeldung: "wenn ich auf GitHub ein Update hochgeladen habe,
  wird es mir beim MiSTer-Neustart nicht angezeigt, auch ein zweiter
  Neustart zeigt nichts — dann habe ich das Frontend beendet und über OSD
  frontend_start ausgeführt, dann wurde mir angezeigt, dass ein Update
  verfügbar ist"). Es gab bisher **einen einzigen Abruf pro Sitzung**,
  gestartet sobald das Kategorien-Menü steht — also rund zwei Sekunden
  nach dem Start. Schlug der fehl, wurde er innerhalb der Sitzung nie
  wiederholt; beim zweiten Neustart passierte dasselbe.

  **Die Ursache war eine andere als zunächst vermutet.** Naheliegend war
  "beim Kaltstart ist das Netzwerk noch nicht bereit" — ein echtes
  Gerätelog zeigt aber etwas anderes, und zwar eindeutig:

  ```
  01:00:16  Rainwave: info-Abruf fehlgeschlagen: [SSL:
            CERTIFICATE_VERIFY_FAILED] certificate is not yet valid
  01:00:20  boot-watch +07s: ...
  12:02:03  boot-watch +12s: ...
  ```

  Das Netz war also da — die Verbindung kam bis zum TLS-Zertifikat. Aber
  die MiSTer-Uhr stand beim Start auf 01:00, und gegen eine derart
  falsche Uhr ist *jedes* Zertifikat "noch nicht gültig". Beide
  Update-Adressen laufen über HTTPS, der Abruf scheitert damit
  zwangsläufig. Die beiden boot-watch-Zeilen zeigen den Rest: zwischen 7
  und 12 Sekunden Laufzeit springt die Uhrzeit von 01:00 auf 12:02 — NTP
  stellt sie also erst rund zehn Sekunden **nach** dem Update-Check.

  Deshalb wird jetzt zuerst kurz auf eine gestellte Uhr gewartet
  (höchstens 30 s, im Hintergrund-Thread) und erst danach abgefragt.
  Zusätzlich wiederholt sich der Check bei ausbleibender Antwort nach 20,
  60 und 180 Sekunden — als Sicherheitsnetz für die Fälle, in denen
  wirklich kein Netz da ist. Ein Fehlschlag lässt sich dabei sauber von "es gibt
  nichts Neues" unterscheiden: `check_for_update()` liefert die entfernte
  Version auch dann zurück, wenn sie der lokalen entspricht, und nur bei
  einem echten Fehler `None`. Wiederholt wird also ausschließlich, wenn
  von **beiden** Abfragen nichts kam — bei vorhandenem Netz bleibt es
  exakt beim bisherigen einen Abruf. Verifiziert mit fünf Tests (Netz da
  → genau ein Versuch; Netz dauerhaft weg → vier Versuche ohne Absturz;
  Netz kommt beim dritten Versuch → danach Schluss; kompletter
  Hintergrund-Check läuft durch) plus Regressionssuite (18/18).
- Bildschirmspiegel fürs Streaming läuft etwas flüssiger: Mindestabstand
  zwischen zwei Schnappschüssen von 0,2 s auf 0,15 s gesenkt, also von 5
  auf rund 6,7 Bilder pro Sekunde. Bewusst dieser maßvolle Schritt und
  nicht 0,1 s — der Kodiervorgang selbst ist bei CRT-Auflösung mit ~3 ms
  bereits nahe am Optimum, die Bildrate kostet also unmittelbar CPU-Zeit
  in einem Hintergrund-Thread, der sich den Interpreter mit der
  Eingabe-Hauptschleife teilt. Sollte das Scrollen dadurch spürbar
  zurückfallen, ist `MIN_ENCODE_INTERVAL` die eine Zahl zum
  Zurückdrehen.
- Kein sekundenlanges Hängen mehr beim Ordnerwechsel
  (Nutzer-Rückmeldung: "wenn ich durch meine ROM-Listen scrolle und dann
  wieder auf Zurück drücke, bleibt der Cursor ab und zu mal für 1 Sekunde
  hängen — fühlt sich an, als wenn er nachladen müsste"). Genau das tat
  er auch. Es gibt einen Schutz, der noch nicht dekodierte Cover
  überspringt, solange navigiert wird (`ART._defer_uncached`) — gesetzt
  wurde er aber an **genau einer Stelle**: im Leerlauf-Zweig von
  `next_action()`. Beim Verarbeiten einer Navigations-Aktion wurde er
  nicht aktualisiert. Ein Ordnerwechsel zeichnet jedoch sofort
  (`_go_back_or_confirm_quit()` ruft direkt `draw()` auf) und benutzte
  dabei den veralteten Wert vom letzten Leerlauf-Tick.

  Wer vor dem Zurückdrücken kurz innehielt (länger als die 150 ms), bei
  dem stand der Schutz auf `False` — das Cover wurde dann **synchron im
  Zeichenpfad** von der Karte gelesen und entpackt. Für exakt diesen
  Vorgang ist im Code bereits eine echte Hardware-Messung dokumentiert:
  **1210 ms für ein einzelnes Cover**. Das erklärt auch das "ab und zu":
  Drückt man Zurück *mitten* im Scrollen, steht der veraltete Wert
  zufällig richtig und es passiert nichts.

  Behoben an der Wurzel: Der Wert wird jetzt dort gesetzt, wo er
  gebraucht wird — zu Beginn beider Seitenaufbauten (neue Hilfsfunktion
  `_sync_cover_defer()`) — und ist damit immer aktuell, egal über welchen
  Weg gezeichnet wurde. Damit das gefahrlos möglich ist, läuft der
  COVER_SETTLE-Nachlader jetzt **auch im Kategorien-Hauptmenü**: Bisher
  war er auf Seite 1 beschränkt, weshalb ein dort übersprungenes Bild nie
  nachgeladen worden wäre — genau der Grund, warum der Schutz früher
  nicht einfach überall gesetzt werden konnte.

  Verifiziert mit fünf gezielten Tests (Schutz aktiv während Navigation
  und aus im Stillstand, jeweils auf beiden Seiten; Nachlader nicht mehr
  seitenbeschränkt; und der konkrete Ablauf "aus dem Unterordner zurück"
  löst keinen synchronen Ladevorgang mehr aus) plus der vollständigen
  Regressionssuite (18/18).

  GEPRÜFT UND VERWORFEN bei derselben Untersuchung, damit es nicht
  erneut probiert wird: Der Bildschirmspiegel fürs Streaming kodiert
  RGBA, obwohl der Alphakanal fest auf 255 steht. Naheliegend wäre, auf
  PNG-Farbtyp 2 (RGB, 3 statt 4 Bytes) umzustellen — gemessen ist das
  aber **5× langsamer**, weil das Zusammenbauen der RGB-Zeilen eine
  Python-Schleife über die Pixel braucht, während der heutige Weg
  (`rgba[0::4], rgba[2::4] = ...`) komplett in C läuft. Die zlib-Ersparnis
  von 12% wird davon um ein Vielfaches aufgefressen. Auch ein niedrigerer
  Kompressionsgrad bringt nichts (Stufe 3 und 1 messen sich bei dieser
  Bildgröße nicht schneller als Stufe 6). Der Kodiervorgang bei
  CRT-Auflösung ist also bereits nahe am Optimum; die Bildrate von 5/s
  ist eine bewusste CPU-Grenze, kein Versäumnis.
- Die Hinweisbox ("CRT-Modus aktiv", Update-Hinweis) verschwindet jetzt
  vollständig (Nutzer-Rückmeldung: "wenn ich von HDMI auf CRT umschalte
  und der MiSTer im CRT-Modus neu startet, kommt die Info 'CRT aktiv' —
  sobald ich dann den Cursor bewege, verschwindet die Infobox nicht ganz
  und ist teilweise noch zu sehen"). Zwei Ursachen, die zusammenwirkten:
  1. Bei der ersten Eingabe wurde die Box zwar abgeschaltet
     (`_prominent_message = None`), aber **nichts zeichnete den
     Bildschirm daraufhin neu** — sie stand also weiter im Bildpuffer.
     Die unmittelbar folgende Navigation lief dann über den leichten
     Zeichenpfad, der nur einzelne Zeilenbänder auffrischt: Er nahm
     genau die Streifen weg, die er ohnehin anfasst, und ließ den Rest
     der Box stehen. Die Box liegt bei `oy + 55*s` über die volle
     Breite, auf Seite 1 also mitten über den ersten Listenzeilen — sie
     wurde dadurch stückweise angeknabbert statt entfernt. Dieselbe
     Fehlerklasse wie seinerzeit beim Beenden-Dialog, nur für die
     Hinweisbox. Der frühere Kommentar an `_draw_prominent_message()`,
     die Box werde "NICHT von den leichten Tick-Pfaden berührt", war
     schlicht falsch und ist entsprechend korrigiert.
  2. Selbst ein erzwungener voller `draw()` reichte **nicht** — das kam
     erst durch einen Pixelvergleich heraus. `draw_page_items()` nimmt
     beim Scrollen innerhalb derselben Liste seinen eigenen schnellen
     Pfad und baut den Hintergrund gar nicht neu auf, sondern stellt nur
     die Listenspalte wieder her. Alles, was die Box **außerhalb** dieser
     Spalte überdeckt hatte (Cover-Panel, Ränder), blieb deshalb stehen.

  Behoben über den dafür vorgesehenen Mechanismus: `_draw_prominent_
  message()` zählt jetzt `fb.full_redraw_gen` hoch — der Zähler bedeutet
  genau "irgendetwas anderes hat in den Puffer geschrieben" und entwertet
  den schnellen Hintergrund-Pfad. Das wirkt automatisch für **beide**
  Wege, auf denen die Box verschwindet (Zeitablauf und Abräumen bei der
  ersten Eingabe). Zusätzlich weigern sich die leichten Navigationspfade,
  solange eine Überlagerung sichtbar ist (neue Hilfsfunktion
  `_overlay_active()`), und die Animations-Ticks behandeln die Box jetzt
  wie einen Dialog — sie zeichnen dann voll und setzen die Box korrekt
  wieder obendrauf, statt sie anzuknabbern.

  Verifiziert mit einem gezielten Pixelvergleich auf beiden Auflösungen:
  Nach dem Verschwinden der Box ist der Bildpuffer **bitgenau identisch**
  mit einer Seite, die nie eine Box gesehen hat — geprüft für beide
  Verschwinde-Wege. Dazu die vollständige Regressionssuite (18/18).
- Seitensprung mit Links/Rechts läuft ruhig statt stockend
  (Nutzer-Rückmeldung: "wenn ich nach links oder rechts drücke um
  mehrere zu überspringen, fühlt sich das auch noch etwas stockend an im
  HDMI-Modus"). Anders als vermutet steckte hier **keine** weitere
  Anlaufsperre und keine Geister-Wiederholung — alle Rückgabepfade in
  `_translate()` wurden dafür systematisch durchgegangen, jeder setzt,
  beendet oder bricht eine Wiederholung korrekt ab. Die Ursache ist
  strukturell und ließ sich messen:

  | Aktion | Kosten | Text-Cache-Trefferquote |
  |---|---|---|
  | hoch/runter, ein Schritt (leichter Pfad) | 1,76 ms | ~86% |
  | **links/rechts, eine Seite** | **7,14 ms** | **19,5%** |

  Ein Seitensprung verschiebt die Auswahl um eine volle Bildschirmseite;
  danach zeigen *alle* sichtbaren Zeilen Titel, die noch nie gezeichnet
  wurden. Die Trefferquote bricht damit von ~86% auf ~20% ein, praktisch
  jede Zeile landet im teuren Neu-Render-Pfad, und einen leichten
  Zeichenpfad gibt es für Seitensprünge nicht (nur für Einzelschritte
  hoch/runter). Zusammen Faktor 4 gegenüber einem normalen Schritt —
  hochgerechnet auf die auf echter Hardware gemessenen 45–110 ms für
  einen vollen Aufbau also grob 110–260 ms pro Seitensprung. Angefordert
  wurden bei gehaltener Taste aber 12,5 pro Sekunde (Wiederhol-Boden
  0,08 s), liefern lassen sich real 4–9. Das Frontend hinkt dauerhaft
  hinterher, und weil die Dauer je nach Anteil neuer Titel schwankt,
  kommen die Bildaktualisierungen unregelmäßig an — genau das fühlt sich
  als Stocken an.

  Zwei Änderungen, beide nach demselben Grundsatz "nicht mehr anfordern
  als lieferbar ist":
  1. **Eigener Wiederhol-Boden für links/rechts** von 0,25 s statt der
     0,08 s von hoch/runter (`REPEAT_FLOOR_PAGE` in `fe/input.py`) — also
     4 statt 12,5 Seitenwechsel pro Sekunde. Ruhige, *gleichmäßige*
     Seitenwechsel statt unregelmäßig durchkommender, und man kann
     überhaupt noch lesen, wo man gelandet ist. Der erste Tastendruck
     reagiert unverändert sofort; betroffen ist ausschließlich die
     Wiederholrate bei gehaltener Taste. Hoch/runter bleibt exakt wie
     bisher bei 0,08 s.
  2. **Turbo-Wachstum auf Faktor 2 begrenzt** (vorher bis Faktor 5). Bei
     17 sichtbaren Zeilen sprang die Auswahl bisher auf bis zu 85
     Einträge pro Tastendruck — weder lesbar noch steuerbar, und jeder
     dieser Sprünge ein vollständiger Neuaufbau ohne einen einzigen
     nutzbaren Cache-Treffer. Zusammen mit dem langsameren Takt reicht
     Faktor 2 aus, um auch sehr lange Listen zügig zu durchqueren.

  Verifiziert mit einer eigenen Testreihe (hoch/runter behält seinen
  Takt; links/rechts erreicht den neuen Boden; erster Tastendruck
  unverändert; Richtungswechsel links↔rechts respektiert den Boden,
  hoch↔runter bleibt schnell) plus der vollständigen Regressionssuite
  (18/18) und den bestehenden Eingabe-Tests aus dem vorigen Build.
- Richtungswechsel beim Scrollen bleibt nicht mehr hängen
  (Nutzer-Rückmeldung: "wenn ich nach unten gedrückt halte und dann
  wieder nach oben drücke um zu scrollen, bleibt der kurz hängen, das
  fühlt sich klemmig an"). Ursache nachgerechnet statt vermutet:
  `_hold()` in `fe/input.py` setzt bei **jedem** frischen Tastendruck die
  volle Anlaufverzögerung von 400 ms und wirft die bereits erreichte
  Beschleunigung weg — und ein Richtungswechsel ist für die
  Eingabeschicht genau so ein frischer Tastendruck. Die Zeitleiste mit
  den echten Konstanten:

  | | Abstand zum nächsten Schritt |
  |---|---|
  | Dauerlauf vorher | 80 ms |
  | direkt nach dem Richtungswechsel | **400 ms** (Faktor 5) |
  | danach | 119 → 101 → 86 → 80 ms |

  Volle Geschwindigkeit war damit erst nach **0,79 s und 5 Schritten**
  wieder erreicht. Jetzt gilt: Lag die letzte *echte* Wiederholung
  derselben Achse weniger als 0,5 s zurück, startet der Richtungswechsel
  mit einer kurzen Pause von 140 ms und behält das bereits erreichte
  Tempo — volle Geschwindigkeit nach **0,14 s statt 0,79 s**. Die
  400-ms-Sperre hat ihren Sinn (ein einzelner, bewusster Tastendruck
  soll nicht ungewollt in eine Wiederholung laufen) und bleibt für genau
  diesen Fall vollständig erhalten: Sie greift unverändert, wenn vorher
  nicht gescrollt wurde, bei einem Achswechsel (runter → rechts) und
  nach jeder Scroll-Pause von mehr als einer halben Sekunde.
- Keine Geister-Wiederholung mehr nach "Zurück"/"OK"
  (Nutzer-Rückmeldung: "wenn ich in einem Ordner länger gescrollt habe
  und dann einen Ordner zurückgehe, bewegt sich der Cursor teilweise
  nicht und dann kommt auf einmal eine plötzliche Bewegung"). Beim
  Nachlesen gefunden: `_translate()` fasste `self.held` im Zweig für
  nicht wiederholbare Aktionen überhaupt nicht an — weder setzend noch
  löschend. Wer beim Drücken von "Zurück" die Richtungstaste noch
  gedrückt hielt, dessen Wiederholung lief im übergeordneten Ordner
  einfach weiter, ohne dass er etwas Neues gedrückt hat; der Cursor
  wanderte also von selbst weiter, bis der Loslass-Event eintraf. Eine
  nicht wiederholbare Aktion (Zurück, OK, Menü) beendet einen laufenden
  Scrollvorgang jetzt sofort.

  Beide Fixe mit einer eigenen Testreihe gegen die echte
  Wiederhol-Logik abgesichert (einzelner Tastendruck behält 400 ms;
  Richtungswechsel im Scrollen bekommt 140 ms und behält das Tempo;
  Achswechsel und Scroll-Pause lösen die Verkürzung korrekt NICHT aus;
  Abbruch nach "Zurück" setzt alles sauber zurück; `_release()`
  unverändert) plus der vollständigen Regressionssuite (18/18).

  AUSGESCHLOSSEN bei derselben Suche, damit es nicht erneut geprüft
  wird: `rescan()` läuft zwar in jeder Schleifenrunde, ist aber bereits
  auf einen einzigen `stat()`-Aufruf optimiert, solange sich
  `/dev/input` nicht ändert — kein Kostenfaktor. Und ein Rückstau
  aufgelaufener Tasten-Wiederholungen ist technisch ausgeschlossen: Die
  Auto-Wiederholung des Kernels (`value == 2`) wird bewusst ignoriert,
  und `self.held` verankert die nächste Fälligkeit immer an *jetzt*
  statt an der verpassten Deadline, kann also nicht nachfeuern.
- Animations-Ticks pausieren jetzt, solange aktiv navigiert wird. Bei
  der gezielten Suche nach weiteren ungeschützten Hintergrund-Redraws
  (dieselbe Fehlerklasse wie beim Beenden-Dialog) gefunden: Gegen einen
  offenen **Dialog** waren alle Zeichenpfade im Leerlauf-Zweig sauber
  abgesichert — gegen eine gerade laufende **Navigation** dagegen nicht.

  Das ist kein Randfall, sondern ein exakter Gleichstand zweier Werte:
  `next_action()` wartet auf HDMI 0,08 s auf eine Eingabe (das
  Puls-Intervall), und die Tastenwiederholung beschleunigt in
  `fe/input.py` über `iv = max(0.08, iv * 0.85)` auf einen Boden von —
  ebenfalls 0,08 s. Bei gehaltener Taste läuft der Timeout dadurch etwa
  jedes zweite Mal ab, der Leerlauf-Zweig feuert einen Puls-,
  Equalizer- oder Laufschrift-Tick, und der zeichnet die markierte Zeile
  samt eigenem `flip_rows()` neu — inklusive Vsync-Warten (auf echter
  Hardware 8–17 ms), direkt zwischen zwei Navigationsschritten, die
  genau dieselbe Zeile ohnehin gerade neu gezeichnet haben.

  Mit der echten Wiederhol-Logik aus `fe/input.py` nachgestellt (6 s
  gehaltene Taste, jeweils drei identische Läufe): **23 → 19
  Bildschirm-Updates bei gleicher Schrittzahl, also 17% weniger.**

  Sichtbar ändert sich nichts: `draw_list_row()` holt die aktuelle
  Schimmerfarbe bei jedem Zeichnen frisch über `_pulsed()`, die
  Animation läuft über die Navigationsschritte also ganz normal weiter.
  Die Ticks werden bewusst gar nicht erst aufgerufen, statt ihr Ergebnis
  zu verwerfen — so bleibt ihre interne Fälligkeitszeit stehen und die
  Animation setzt beim Loslassen ohne Verzögerung wieder ein. Verwendet
  wird dasselbe 150-ms-Fenster wie beim bereits vorhandenen
  `FAST_SCROLL_WINDOW`/`COVER_SETTLE`; bei normaler, langsamer
  Navigation (mehr als 150 ms zwischen zwei Schritten) greift der Schutz
  gar nicht erst. Verifiziert mit der vollständigen Regressionssuite
  (18/18) sowie dem Vergleich „leichter Zeichenpfad gegen vollen
  Neuaufbau" — keine neue Abweichung.

  ZWEI WEITERE ERGEBNISSE derselben Suche, beide ohne Codeänderung:
  - `_restore_row_bg()` (stellt beim schnellen Pfad die komplette
    Listenspalte wieder her) kostet **0,608 ms — 22% eines vollen
    Seitenaufbaus** und liegt dabei genau *zwischen* den Messpunkten
    `bg=` und `rows=` der `PERF split`-Zeile, taucht in den
    Hardware-Mitschnitten also überhaupt nicht auf. Geprüft, ob die
    Glow-Entfernung sie billiger macht: Der 10·s-Rand war tatsächlich
    Glow-Erbe, aber eine Kürzung auf die noch nötigen 4·s bringt nur
    3%. Die naheliegende Alternative (keine Spalten-Wiederherstellung,
    jede Zeile füllt ihren eigenen Hintergrund) misst zwar schneller
    (0,68 statt 0,93 ms), ist aber **nicht bildgleich** — sie füllt flach
    statt mit dem Vignette-Verlauf, also genau der Fehler, der bei
    `_restore_row_bg()` als „260.000 abweichende Pixel" dokumentiert
    ist. Ergebnis: teuer, aber notwendig; hier ist kein sicherer Gewinn
    zu holen.
  - Sobald der Cursor am unteren Rand steht und die Liste mitscrollt,
    gibt `_draw_navigate_items()` False zurück und **jeder** Schritt
    läuft über den vollen Seitenaufbau (im Test 43 von 59 Schritten).
    Das ist beim Durchblättern einer langen Liste der Normalfall und
    inhärent — ein Scroll um eine Zeile ändert den Text aller sichtbaren
    Zeilen, ein Teil-Redraw kann dort nichts einsparen.
- Glow-Effekt entfernt und die dadurch erzwungene Mehrarbeit beim
  Scrollen gleich mit (Nutzerwunsch: "glow Effekt komplett raus, 3
  Zeilen Sprung komplett beim Scrollen rausnehmen"). Die markierte Zeile
  hatte bisher zusätzlich zum farbigen Balken drei konzentrische
  Leucht-Ringe (`glow_border_fast()`, je vier `rect()`-Aufrufe — also 12
  zusätzliche Zeichenoperationen pro markierter Zeile, bei *jedem*
  Bildaufbau und *jedem* Puls-Tick). Der Balken selbst bleibt
  unverändert; nur das Leuchten drumherum ist weg.

  Der eigentliche Gewinn liegt aber in den Folgekosten: Weil der Glow
  bewusst über die eigene Zeile hinausragte, blutete er in die
  Nachbarzeilen — und musste dort wieder übermalt werden. Deshalb wurden
  bei jedem Navigationsschritt und jedem Puls-Tick **drei Zeilen**
  gezeichnet (die markierte plus beide Nachbarn) statt einer, dazu
  jeweils ein großzügig verbreiterter Randbereich freigeräumt und, wenn
  die Markierung ganz oben stand, zusätzlich die Kopfzeile neu gesetzt.
  All das war ausschließlich Reparaturarbeit am Glow. Ohne ihn bleibt
  jede Zeile in ihrem eigenen Bereich, und sämtliche dieser
  Zusatz-Durchgänge entfallen — an allen sechs betroffenen Stellen
  (`draw_page_items`, `_draw_navigate_items`, `_draw_dynamic_items`,
  `draw_page_cats`, `_draw_navigate_cats`, `_draw_dynamic_cats`).

  Zusätzlich fällt der Zeilensprung im Kategorien-Hauptmenü weg: Dort
  sprang die Auswahl bei gehaltener Taste noch um 2, dann 4, dann 10
  Zeilen. Das ist nicht nur optisch ein Sprung — ab einer Sprungweite
  über 1 greift der leichte Zeichenpfad nicht mehr, und jeder weitere
  Schritt löst wieder den vollen Seitenaufbau aus. Für die Spieleliste
  war das in einer früheren Runde bereits behoben, jetzt auch fürs
  Hauptmenü. Zügiges Durchlaufen bleibt über die beschleunigte
  Wiederhol-Taktrate erhalten, nur eben Zeile für Zeile.

  Gemessen (1920×1080, Median):

  | Zeichenpfad | vorher | nachher | |
  |---|---|---|---|
  | Spieleliste, voller Aufbau | 3,43 ms | 2,83 ms | −18% |
  | Spieleliste, ein Navigationsschritt | 2,48 ms | 1,84 ms | −26% |
  | Spieleliste, Puls-Tick | 0,296 ms | 0,068 ms | **−77%** |
  | Hauptmenü, voller Aufbau | 1,83 ms | 1,66 ms | −10% |
  | Hauptmenü, ein Navigationsschritt | 1,52 ms | 0,99 ms | **−35%** |
  | Hauptmenü, Puls-Tick | 0,318 ms | 0,045 ms | **−86%** |

  Die Puls-Ticks fallen dabei besonders ins Gewicht, weil sie dauerhaft
  laufen (bis zu ~12,5 pro Sekunde), auch wenn man einfach nur im Menü
  steht. Abgesichert über einen Vergleich, der genau das Risiko dieser
  Änderung prüft: Der leichte Zeichenpfad muss weiterhin bitgenau
  dasselbe Bild liefern wie ein vollständiger Neuaufbau — bliebe
  irgendwo ein Rest einer alten Markierung stehen, würde es auffallen.
  Über 32 Fälle (beide Auflösungen, Navigationsschritte und Puls-Ticks
  auf beiden Seiten) kam **keine einzige neue Abweichung** hinzu; zwei
  bereits vorher bestehende (Puls-Tick im Hauptmenü) sind durch die
  Änderung sogar verschwunden. Dazu die vollständige Regressionssuite
  (18/18).
  ANMERKUNG (unabhängig von dieser Änderung, für später notiert): Beim
  Aufbau dieses Vergleichs zeigte sich, dass der leichte Zeichenpfad der
  Spieleliste schon vorher nicht in allen Fällen bitgenau dem vollen
  Aufbau entsprach. Zwei dieser Abweichungen gehen auf die
  Rand-Abdunkelung zurück (die Zeilen werden im leichten Pfad einfarbig
  statt mit dem Verlauf gefüllt), die übrigen sind noch nicht
  eingegrenzt. Das ist ein bestehender Zustand, der durch diese Änderung
  weder besser noch schlechter wird.
- Textdarstellung deutlich entlastet — die Ursache der bisher
  unerklärten Fehltreffer im Text-Cache ist gefunden und behoben
  (Fortsetzung der HDMI-Performance-Runde, diesmal messend statt
  vermutend). Ausgangspunkt war die Frage, warum die im echten
  `DRAGEND_PROFILE`-Mitschnitt gemessene Trefferquote von 83–85%
  hartnäckig nicht besser wurde. Zwei Messungen haben das aufgeklärt:
  - Ein **Fehltreffer kostet das 45-fache eines Treffers** (0,45 ms
    gegen 0,010 ms bei einem 40-Zeichen-Titel). Die verbliebenen 15–17%
    Fehltreffer verursachen damit rund 90% der gesamten `text()`-Zeit —
    also genau die 34–74 ms, die im Profiling unter `draw_page_items()`
    auftauchten. Nicht die Trefferquote war das Problem, sondern der
    Preis pro Fehltreffer.
  - Die **Laufschrift der markierten Zeile war der Verursacher**: Sie
    rückt alle 0,18 s um ein Zeichen weiter und zeichnete dafür den
    Teilstring `full[off:off+maxc]` — für den Cache jedes Mal ein neuer
    Schlüssel, also ein garantierter Fehltreffer im Sekundentakt, und
    zwar dauerhaft, auch wenn man einfach nur stillsteht. Nachgestellt
    an einem typischen langen Titel ergab das 23 Fehltreffer und 23
    Cache-Einträge für einen einzigen Titel bei einer Trefferquote von
    86,1% — praktisch deckungsgleich mit den auf echter Hardware
    gemessenen 83–85%. Damit ist der Hauptteil der dortigen Fehltreffer
    erstmals reproduziert und erklärt.

  Zwei Änderungen, beide ohne jede sichtbare Auswirkung:
  1. Der Aufbau eines Textstreifens (`Framebuffer.text()`, der teure
     Fehltreffer-Pfad) läuft jetzt über 8 `join()`-Aufrufe statt über
     `len(s)·8·scale` einzelne Slice-Zuweisungen — bei einem
     40-Zeichen-Titel auf HDMI also 8 statt 960 Einzeloperationen, ohne
     die anschließende komplette Zweitkopie aller Zeilen. Zusätzlich
     teilen sich die `scale` identischen Wiederholungen einer
     Glyphenzeile dasselbe Objekt, statt kopiert zu werden. Gemessen:
     Listenzeile 0,382 → 0,116 ms (3,3×), Kopfzeile 0,243 → 0,049 ms
     (5,0×); Speicher pro Cache-Eintrag bei HDMI von 90 auf 30 KB.
  2. Neue Methode `Framebuffer.text_window()`: Da jedes Zeichen im
     fertigen Streifen eine feste Breite belegt, *ist* der
     Laufschrift-Ausschnitt schlicht ein Byte-Bereich des Streifens für
     den vollen Titel. Der wird jetzt einmal gerendert und danach nur
     noch ein Fenster daraus kopiert. Aus 23 teuren Neu-Renderings pro
     langem Titel werden 3 (eines je Schimmer-Stufe), die Trefferquote
     in diesem Szenario steigt von 86,1% auf 98,2%.

  Verifiziert mit 580 Byte-Vergleichen des Streifen-Aufbaus (kompletter
  ASCII- und Latin-1-Bereich, `?`-Rückfall außerhalb davon, Grenzfälle
  der Bereichsprüfung, alle Skalierungen, 300 Zufallstexte), 5836
  geprüften Laufschrift-Fällen inklusive Favoriten-/Durchgespielt-Präfix
  und Rückfallpfad für überlange Namen, einem Vorher/Nachher-Vergleich
  von 144 komplett gerenderten Bildschirmseiten (CRT und HDMI, inklusive
  eines vollen Schimmer-Zyklus und 104 Laufschrift-Positionen) sowie der
  vollständigen Regressionssuite (18/18) — überall null Abweichungen.
  EINSCHRÄNKUNG (ehrlichkeitshalber): Alle Zeitmessungen stammen aus der
  Entwicklungsumgebung, nicht vom MiSTer. Die Verhältnisse sollten sich
  übertragen (es geht um die Anzahl der Python-Operationen, nicht um
  Speicherbandbreite), die absolute Ersparnis auf echter Hardware kann
  aber abweichen. Was gesichert ist: das gezeichnete Bild ist bitgenau
  identisch, und es wird nichts zu einem anderen Zeitpunkt gezeichnet
  als bisher — die Änderung kann also nur schneller oder gleich schnell
  sein, aber nichts am Verhalten verändern.
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
