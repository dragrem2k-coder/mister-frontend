# Changelog

Kurz gehalten: je Version ein Block mit dem, was man merkt.

Wer die Details will — welche Messung wozu geführt hat, welcher Versuch
danebenging, was ein Test gefunden hat — findet sie im
[ausführlichen Archiv](docs/CHANGELOG_ARCHIV.md) (alle Builds seit v1.1).

English: [`CHANGELOG_EN.md`](CHANGELOG_EN.md)

---

## v4.5 — CD-Spiele in Ordnern, C-Modul, Werkzeug für den PC

**Kernel 6.18: der Start hält sich jetzt selbst fest.** Nach dem
MiSTer-Linux-Update kam die alte Meldung *„ich hänge im OSD und höre
die Musik vom Frontend"* zurück, dazu ein Login-Gruß, der nach 20–30
Sekunden Ruhe wieder auftauchte und bis zum nächsten Tastendruck
stehen blieb. Ursache ist dieselbe wie beim Beenden: **ein einzelnes
F9 sitzt auf diesem Kernel nicht mehr zuverlässig** — MiSTer richtet
den Bildspeicher mehrfach neu ein, und wer vorher klopft, klopft an
eine Tür, die es noch nicht gibt. Das Frontend schaltet deshalb **auf
Kernel 6 und neuer von selbst** die Konsolen-Mechanik ein: das F9 wird
wiederholt, eine Wache räumt fremde Ausgabe weg, die Bildschirmschonung
der Textkonsole bleibt aus. Auf 5.15.1 ändert sich nichts. Erzwingen
lässt sich beides mit `konsole_mechanik_an` bzw. `konsole_mechanik_aus`,
und welcher Weg genommen wurde, steht im Log.

**Das Zucken bei voller Auflösung ist mit demselben Kernel-Update
verschwunden.** Es lag nie am Frontend. Sechs Erklärungen waren vorher
durchgemessen und verworfen worden — Eingabe-Leck, übersprungenes
Vsync, Speicherdurchsatz, der Cover-Weg, ein zweiter Bildspeicher und
fremde Schreibzugriffe; die letzte Messung zeigte über 294 Sekunden,
dass sich in unserem Bildspeicher **kein einziges Byte** änderte,
während es sichtbar zuckte. Die dafür gebauten Messwerkzeuge bleiben
erhalten (`flip_haeppchen`, `flip_rueckleser`, `fb_wacht.py`), alle
standardmäßig aus.

**Die Suche nach dem Zucken: vier Erklärungen ausgeschlossen.** Bei
voller Auflösung blitzt achtmal je Minute MiSTers eigenes Menübild für
ein bis zwei Bilder durch, immer dicht an einem Scrollschritt, bei
halber Auflösung nie. Vier Vermutungen sind inzwischen **gemessen und
widerlegt**, jede davon wäre plausibel gewesen:

* *Unsere Eingaben erreichen MiSTer und wecken ihn.* Er wacht beim
  Scrollen nicht öfter auf als im Leerlauf.
* *Übersprungenes Vsync.* Vollbilder warten seit v2.2 ausnahmslos.
* *Der Speicherbus ist dicht, weil 7,9 MB am Stück geschrieben werden.*
  Mit dem Schalter `flip_haeppchen` (16 Stücke, 500 µs Pause) brauchte
  der Bildtransport 34 ms statt 12,6 — dreimal so entzerrt, und das
  Zucken blieb unverändert.
* *Es hängt an den Covern.* Es zuckt auch in Kategorien ohne ein
  einziges Cover.

Übrig bleiben zwei Möglichkeiten, die einander ausschließen: jemand
**schreibt** in den Bildspeicher hinein, oder die Anzeige-Ebene wird
**weggeschaltet**. Dafür gibt es zwei Werkzeuge, beide **standardmäßig
aus** und beide ohne jede Wirkung auf das Bild:

* `flip_rueckleser` — das Frontend merkt sich beim Schreiben acht
  Zeilen und sieht beim nächsten Bild nach, ob sie noch dastehen.
  Abweichung heißt *geschrieben*; keine Abweichung bei sichtbarem
  Zucken heißt *weggeschaltet*. Alle 30 Sekunden schreibt er eine
  Bilanz ins Log, auch wenn nichts war — sonst ließe sich aus seinem
  Schweigen nicht ablesen, ob er nichts gefunden hat oder gar nicht
  lief, und ein Werkzeug, das nur bei Erfolg redet, kann eine
  Vermutung nur bestätigen und nie widerlegen.
* `fb_wacht.py` — dieselbe Frage ohne laufendes Frontend, mit einem
  Prüfmuster im Bildspeicher. Es rechnet nebenbei aus, ob dort Platz
  für eine zweite Bildseite ist; auf dem DE10-Nano ist er das nicht,
  womit auch ein Umschalten zwischen zwei Seiten ausscheidet.

Der Bildtransport in Häppchen bleibt als Schalter erhalten, damit sich
die Messung nachvollziehen lässt: 56 Kombinationen aus Größen und
Stückzahlen sind bitgleich zum bisherigen Weg.

**Cover im Raster kamen bei 1080p nicht nach.** Gefunden über ein Video
von SuTe: das Raster blieb fast leer, ein Cover erschien nur auf der
Kachel, auf der man stehen blieb, nach einem Seitenwechsel war wieder
alles leer, und in der Galerie fehlte oft das große Cover. Sein
`--bench` zeigte, dass sein Gerät nicht langsamer ist — die Bildkette
liegt auf 1–2 % bei den Werten eines zweiten Geräts. Es waren drei
Fehler im Ablauf: das Nachzeichnen im Leerlauf malte im Raster nur
zwei Kacheln, fertige Cover für die übrigen lagen auf der Karte und
wurden nie gezeigt; eine Taste brach die Aufträge an den
Arbeitsprozess ab, ließ aber deren Wartevermerke stehen, worauf die
Hauptschleife im Leerlauf endlos nachzeichnete; und die Notbremse hielt
den Arbeitsprozess nach zwei Sekunden für hängend, obwohl er 21
Kacheln abzuarbeiten hatte — dann rechnete der Zeichenweg selbst, und
100–500 ms je Kachel reagierte nichts. Bei halber Auflösung sind die
Cover so klein, dass keiner dieser Fehler zum Tragen kam.
*Nachtrag:* in einer früheren Fassung stand hier, das sei das Zucken
gewesen. Das war falsch — die drei Fehler sind echt und behoben, aber
das Zucken tritt auch in Kategorien ohne ein einziges Cover auf.

**Das Frontend vermisst sich selbst: `--bench`.** Jede Zahl in diesem
Projekt seit Build 73 war Handarbeit — Profilschalter setzen,
scrollen, `grep PERF`, abtippen. Das ergibt Zahlen für genau dieses
Gerät an genau diesem Tag; zwischen zwei Geräten ließ sich damit
nichts vergleichen. `python3 frontend.py --bench` fährt jetzt einen
festen Ablauf: Startdauer (auch **je Spiel**, damit 2 000 und 97 000
Spiele vergleichbar bleiben), voller Seitenaufbau und Zeit je
Scrollschritt in allen drei Ansichten auf beiden Seiten, der reine
Bildtransport, und die ganze Bildkette — Verkleinern in C gegen
Python, Miniatur packen, schreiben, lesen, PNG dekodieren. Der Kniff
steckt im Testbild: es wird **erzeugt** statt von der Karte gelesen,
und die Maße stehen fest — zwei Geräte messen damit wirklich
dasselbe. Was sich prinzipiell nicht vergleichen lässt, nämlich eine
echte Cover-Datei, steht in einem eigenen Abschnitt mit genau diesem
Hinweis daneben. Der Lauf **schreibt nichts auf die SD-Karte**; was
er zum Messen schreiben muss, landet in einem temporären Ordner, der
danach verschwindet. Bericht auf der Konsole und in
`/tmp/dragend_bench.txt`.

**Der erste Bench-Lauf auf echter Hardware hat als Erstes den Bench
selbst überführt.** Fünf Fehler, alle im Messgerät, keiner im
Frontend — der schlimmste: der Lauf **schrieb doch auf die Karte**.
Zeichnen rechnet Cover, und ein gerechnetes Cover wird als Miniatur
weggeschrieben; die Zusage im Bericht stimmte also nicht. Der
Miniaturen-Cache zeigt während des Laufs jetzt in einen temporären
Ordner — damit gilt die Zusage wieder, und jedes Gerät fängt beim
kalten Durchgang wirklich kalt an. Dazu: das Packen einer Miniatur
war mit Stufe 6 gemessen, das Frontend packt seit Build 154 mit
Stufe 1 (gemeldet wurden 1 176 ms für etwas, das halb so lange
dauert); die Cover-Suche erwartete eine Liste, wo ein
Ordnerbaum steht, und meldete deshalb bei 30 064 Spielen „kein Cover
gefunden"; das Testbild brauchte 25,5 Sekunden, zwei Drittel der
ganzen Laufzeit, für reine Vorbereitung — jetzt rund eine Sekunde;
und der Schrittwert warf Zeichnen und Cover-Rechnen in eine Zahl.
**Kalt und warm stehen jetzt getrennt**, mit der ehrlichen Anmerkung
daneben, dass kalt die Obergrenze ist und nicht der Alltag: beim
echten Scrollen lässt das Frontend die Boxart-Spalte aus.

**Und der zweite Lauf fand den größten Fehler — am Bildschirm, nicht
in der Datei.** „Der Bench landet immer im Super Game Boy, dann
passiert nichts mehr, es werden keine Cover gescrollt." Genau so war
es: **welche Kategorie gemessen wird, war Zufall.** Der Zeiger blieb
stehen, wo die Schleife über die Hauptseite ihn liegen gelassen
hatte — im ersten Lauf PlayStation, im zweiten Super Game Boy mit
einem einzigen Eintrag. Dort bleibt die Auswahl auf demselben Spiel
stehen, das Bild ändert sich nie, und gemessen wird ein Standbild.
Damit erklären sich auch die drei Werte 52,98 / 52,97 / 52,99 aus
jenem Lauf: drei völlig verschiedene Zeichenwege, identisch auf die
Hundertstel, weil keiner etwas zu tun hatte. Jetzt wird die größte
Kategorie **bewusst** gewählt, ihr Name und ihre Eintragszahl stehen
im Bericht, und bei einer zu kurzen Liste warnt er. Dazu zwei
weitere Funde: in jedem Schrittwert steckte das **Vsync-Warten**
(50,0 ms sind bei 60 Hz exakt drei Bildperioden — gemessen wurde die
Bildwiederholrate), es fällt jetzt aus der Messung heraus und steht
einmal separat da; und die Cache-Umleitung wirkte nur im
Elternprozess, weil der Vorauslader seit Build 102 ein **eigener
Prozess** ist — er schrieb weiter auf die Karte, während der
Elternprozess im temporären Ordner nie etwas fand. Für die Messung
rechnet der Zeichenweg jetzt selbst.

**Ordner mit nur einem Spiel werden aufgelöst.** Bei PSX, Mega CD und
Saturn liegt meist jedes Spiel in einem eigenen Ordner, weil eine `.cue`
mehrere `.bin` mitbringt. Die Liste bestand dort deshalb nur aus
Ordnern — und damit gab es weder Cover noch Raster oder Galerie. Jetzt
steht das Spiel direkt in der Liste. Mehrteilige Spiele (zwei `.cue` im
selben Ordner) bleiben Ordner, dort muss man ja auswählen. Abschaltbar
unter *System → Optionen*.

**Ein C-Modul für die beiden teuersten Bildrechnungen.** Cover
verkleinern und vergrößern laufen jetzt in `libdragend.so`. Gemessen auf
dem Gerät: **102- bis 143-mal schneller** (1888 → 18 ms). Das Nachladen
beim Scrollen fällt damit praktisch weg. Fehlt die Bibliothek, rechnet
das Frontend wie bisher in Python weiter — sie ist eine Option, keine
Pflicht.

**Ein Windows-Werkzeug, das die Miniaturen am PC vorbereitet.** Verbindet
sich über das Netzwerk mit dem MiSTer, rechnet die Cover auf allen Kernen
des PCs und legt sie zurück. Aus sechs Stunden auf dem MiSTer werden
Minuten. Liegt unter `pc_tools/`.

**Der Kaltstart landete manchmal im OSD.** Zwei Tage Fehlersuche mit vier
Sackgassen. Das Frontend hatte keine Möglichkeit zu erkennen, ob sein Bild
überhaupt sichtbar ist — bis sich zeigte, dass MiSTers CPU-Last genau das
verrät: 100 % im OSD, 1,4 % in der Konsole. Danach war es ein Dreizeiler.

**Der Login-Prompt bleibt weg.** „Welcome to MiSTer / login:" konnte
mitten im Betrieb oben im Bild auftauchen — beim Neueinlesen der
Spieleliste und manchmal einfach so im Menü. Der Login-Prozess auf
`tty1` schreibt in denselben Bildspeicher wie das Frontend; weggewischt
wurde das bisher nur im Startfenster. Dazu kommt, dass im Ruhezustand
meist nur einzelne Bildzeilen übertragen werden (Laufschrift, Uhr) —
die obersten fasst dabei niemand an, und genau dort steht der Prompt.
Jetzt sieht eine Wache jede Sekunde nach und räumt innerhalb von zwei
Sekunden auf.

**Ein Wettlauf, der Miniaturen verschwinden liess.** Das Aufräumen im
Zwischenspeicher hat liegengebliebene Zwischendateien gelöscht — auch
solche, in die gerade ein anderer Thread schrieb. Die frisch gerechnete
Miniatur war danach weg, „Miniaturen vorbereiten" meldete trotzdem
*fertig*, und das Cover lud beim Scrollen weiter nach. Ein Test hat das
seit Build 119 zweimal gemeldet und liess sich nie wiederholen;
sichtbar wurde es erst, als das C-Modul die beiden Fäden schnell genug
gemacht hat, dass sie sich zuverlässig überholen.

**Beenden führte nicht mehr ins OSD.** Zwei Tage lang blieb nach
*Frontend beenden* ein schwarzes Bild mit blinkendem Cursor stehen, kurz
darauf der Login-Gruß. Selbst verursacht: beim Umbau des Beenden-Ablaufs
wanderte das F12 nach vorn, das Leeren und Schließen des Bildspeichers
blieb aber hinten stehen — wir haben MiSTers gerade aufgebautes OSD
sofort wieder schwarz übermalt. Jetzt gehört der Bildschirm ab dem F12
MiSTer; ein Test hält die Reihenfolge fest.

**Cover scharf verkleinern — für die Röhre.** Bisher wurde immer
gemittelt: auf HDMI das bessere Bild, auf einer Röhre oft nicht, weil
Pixelkunst zu weichem Brei wird. *System → Anzeige & Sound* schaltet
jetzt auf Nearest-Neighbor um — in C gerechnet und dabei viermal
billiger als das Mitteln. Der Modus hängt im Schlüssel des
Miniaturen-Caches, sonst bliebe nach dem Umschalten die alte Miniatur
stehen; beide Fassungen liegen nebeneinander, zurückschalten geht
deshalb sofort.

**Core-Verwaltung.** Liegen von einem Core mehrere Fassungen auf der
Karte — beim NeXT-Core sind es schnell vier, mit sprechenden Namen wie
`scsi_dma_csr_fix` — lässt sich unter *System → Optionen → Cores*
wählen, welche ein System startet. Vorher schrieb das Frontend immer
den Namen ohne Datum, und MiSTer entschied allein. Eine gewählte
Fassung gilt nur, solange ihre Datei existiert: `update_all` löscht bei
jedem Lauf alte Cores, und ein Spiel, das sich danach still nicht mehr
starten lässt, wäre der schlechteste Tausch. Heruntergeladen wird hier
nichts — das bleibt `update_all`.

**Hochkant montierte Bildschirme (TATE), erster Schritt.** Das
Frontend stürzte dort nie ab — es war unbrauchbar, weil die
Vergrößerung des Layouts allein an der Höhe hing. Bei 1080×1920 blieben
dadurch **23 Zeichen je Zeile** übrig statt der 68, auf die alles
ausgelegt ist: jeder Spieltitel auf ein Drittel abgeschnitten. Quer
rechnet weiter die Höhe, hochkant jetzt die Breite — die knappe Seite.
Macht 38 statt 23 Zeichen.

**Hochkant, zweiter Schritt: die Aufteilung der Fläche.** Nach dem
ersten Schritt war das Frontend hochkant benutzbar, die Aufteilung
aber weiter für 16:9 gedacht. Nachgemessen bei 1080×1920: im
**Kachelraster** blieben **993 von 1497 Bildpunkten Höhe leer** — zwei
Drittel der Fläche, für die die Ansicht da ist —, und die Kachel war
mit 117×156 so groß wie quer auf 720p. In der **Galerie** hatte die
Datenspalte neben dem großen Cover **sieben Zeichen** statt 52, weil
das Cover aus der Höhe gerechnet wird und die hochkant riesig ist. Und
die **Boxart-Karte** auf der Liste war zu **68 %** leer (quer 11 %),
während die Liste daneben auf 20 Zeichen abschnitt. Jetzt rechnet das
Raster seine Aufteilung aus der Kachelgröße statt sie festzulegen
(4×5 statt 7×3, Kachel 213×285, Höhe voll genutzt), die Galerie setzt
die Daten hochkant **unter** das Cover — 38 Zeichen statt 7 —, und die
Listenspalte bekommt 62 statt 52 % der Breite: 24 Zeichen, und das
Cover ist damit anteilig so groß wie quer statt größer. Quer ändert
sich kein einziger Bildpunkt; die alten Meßwerte stehen als feste
Zahlen im Test.

**Ein Farbschema-Editor.** *System → Anzeige & Sound → Eigenes
Farbschema bearbeiten*: sechs Farben und der Monochrom-Schalter, am Pad
einstellbar, mit einer Vorschau darunter, die genau die Elemente zeigt,
in denen jede Farbe vorkommt. Hoch/Runter wählt die Zeile,
Links/Rechts ändert, Enter schaltet zwischen R, G und B, ESC geht ohne
Speichern zurück. Rundungen und Schriftgrößen bleiben bewusst außen
vor.

**Ein eigenes Farbschema.** *System → Anzeige & Sound → Aktuelle Farben
als eigenes Schema speichern* legt die gerade aktiven Farben in
`frontend/theme_eigen.json` ab und schaltet sofort darauf um. Danach
steht *Eigenes* in der normalen Durchschalt-Reihenfolge; die Datei kann
man von Hand feiner einstellen. Eine kaputte Datei heißt schlicht „kein
eigenes Schema" und hält den Start nie auf.

**Der Cover-Zwischenspeicher hatte keine Speichergrenze.** Er hielt
60 Bilder — eine *Stückzahl*. Seit v4.4 werden Cover im Original
geladen, und ein 1200×1600-Scan sind 7,7 MB: 60 davon wären 460 MB auf
einem Gerät mit rund 1 GB. Jetzt zusätzlich ein Budget von 48 MB,
gebaut wie die bewährte Verdrängung des skalierten Caches. Bei kleinen
Covern ändert sich nichts.

**Auf Kernel 6.18 kommt das erste F12 beim Beenden nicht an.** Das ist
der Kern der ganzen Sache, und er ist gemessen, nicht vermutet — auf
einem zweiten Gerät mit 6.18.38 steht im Log: *„MiSTer bei 1 % — das OSD
ist NICHT gekommen, fasse nach"*, und eine Sekunde später *„MiSTer bei
100 % — das OSD ist da"*. Das Frontend prüft deshalb nach dem F12 an
MiSTers CPU-Last, ob das OSD wirklich da ist, und fasst bis zu dreimal
nach. Auf dem alten Kernel kostet das nichts: dort meldet die erste
Messung sofort 100 %.

**Das MiSTer-Linux-Update vom 07.09.2026 (Kernel 6.18) bricht
Frontends — auch dieses.** Der Rückbau auf Kernel 5.15.1 hat alle
gemeldeten Probleme sofort behoben, ohne eine Zeile am Frontend zu
ändern. Erkennbar an `fb0: sys_fillrect: framebuffer is not in virtual
address space` im `dmesg`. Degauss, das Zaparoo-Frontend und Console
Mode mussten dafür ebenfalls gepatcht werden. Dragend blendet den
Bildspeicher jetzt ersatzweise über `/dev/mem` ein, wenn `/dev/fb0` es
nicht mehr hergibt. Und `frontend/kernel_probe.py` misst auf einem
betroffenen Gerät in zwei Minuten, woran es liegt — genau damit wurde
die Sache oben aufgeklärt. Siehe den Abschnitt in der README.

**Beim Start ist die Mechanik aus Build 146–166 wieder abgeschaltet.**
Elf Builds hatten sich dort angesammelt; jede Änderung hatte einen
Grund, zusammen haben sie mehr gestört als geholfen. Standard ist
wieder: **ein** F9 beim Start, keine Dauerwache, kein Anfassen von
Cursor und Bildschirmschonung, Boot-Logo sofort. Nur der Ausstieg misst
nach — weil dort nachgewiesen ist, dass ein F12 nicht reicht.

**Gelöscht ist nichts.** Die Mechanik aus den Builds 146–166 kommt mit
einer Datei zurück: `touch /media/fat/frontend/konsole_mechanik_an`.
Ihre Gründe waren echt und gemessen — allen voran „bin im OSD und höre
die Musik vom Frontend". Kommt das wieder, ist die Antwort ein Befehl
statt ein Build.

**Alles, was auf die Textkonsole schreibt, läuft durch eine einzige
Stelle** (Cursor, Bildschirmschonung, die Wache gegen den Login-Prompt).
Vorher waren es sechs verstreute — dadurch ließ sich weder ansehen noch
abschalten, was dort passiert.

**Das Boot-Logo wartet, bis es jemand sehen kann.** Es wurde vollständig
gezeichnet — nur lag unser Bildspeicher zu dem Zeitpunkt noch gar nicht
auf dem Schirm. Jetzt startet es erst, wenn MiSTer nachweislich schläft.

**Der Start ist wieder schnell, auch mit gemerkten Filtern.** Ein
einziger gemerkter Filter kostete gemessene 2,2 Sekunden — nicht durch
das Filtern selbst (nachgemessen: 8 ms für 1800 Spiele), sondern durch
die Tabellen, die dabei zum ersten Mal von der Karte gelesen werden.
Das passiert jetzt im Hintergrund, während die Spieleliste eingelesen
wird.

**Und sonst:** Listenfilter nach Genre, Jahr, Spielerzahl und Entwickler
(Tab oder Select+L2/R2); Spielbeschreibungen in der Galerie; elf deutsche
Hinweiszeilen waren auf CRT unsichtbar; Miniaturen schreiben sich doppelt
so schnell; Scrollen fasst die SD-Karte nicht mehr bei jedem Schritt an.

## v4.4 — Ansichten, Boxart-Quellen, Geschwindigkeit

**Drei Ansichten, überall.** Spieleliste *und* Hauptseite lassen sich
zwischen Liste, Raster und Galerie umschalten — per Menü dauerhaft, per
F10 oder Select+Y nur für die offene Kategorie.

**ROMs in ZIP-Archiven** werden gefunden und gestartet, ohne dass je
etwas entpackt wird.

**Zweite Cover-Quelle:** liegt die Artwork-Datenbank unter
`/media/fat/docs`, wird sie mitbenutzt. Eigenes Artwork behält Vorrang.
Cover werden im Original geladen statt auf eine Kastengröße
zurechtgestutzt.

**Deutlich flüssiger.** Aus einem echten Profillauf auf dem Gerät kamen
vier Bremsen: die Spielbeschreibung kostete 159 von 259 ms je Aufbau, das
Raster kopierte bei jedem Schritt den ganzen Bildschirm, jeder
Scrollschritt las fünfmal von der SD-Karte, und das Verkleinern eines
Covers brauchte doppelt so lange wie nötig.

**Reparaturen, die man sieht:** Rot und Blau waren in allen Miniaturen
vertauscht; bei halbierter Menü-Auflösung verschwanden alle Boxarts;
Erfolgs-Popups waren in Raster und Galerie unsichtbar; der Offline-
Installer fand sein eigenes Paket nicht.

## v4.3 — großes Sammel-Release

Rainwave-Internetradio als zweite Musikquelle, Lautstärke-Regler,
Ersteinrichtungs-Assistent in acht Schritten, SNES Tracker und SMW Hacks
als eigene Kategorien, Update-Benachrichtigung über GitHub, „Wonne oder
Tonne" als Bewertungs-Format, mehr versteckte Erfolge und saisonale
Dekorationen.

Dazu ein Dutzend Reparaturen — darunter: `(Unl)`/`(Pirate)`-ROMs wurden
fälschlich aussortiert, ein veralteter Scan-Cache überlebte Änderungen
an der Filterlogik, und die Uhrzeit blieb dauerhaft falsch, wenn die
erste Synchronisierung fehlschlug und kein RetroAchievements
eingerichtet war.

## v4.2 — Uhrzeit blieb bei manchen dauerhaft falsch

Der Neuversuch für eine fehlgeschlagene Zeit-Synchronisierung lief nur
über den RetroAchievements-Mechanismus — wer RA nicht eingerichtet
hatte, bekam überhaupt keinen zweiten Versuch. Jetzt gibt es einen
davon unabhängigen Weg.

## v4.1 — Lautstärke-Regler

Für Musik und Menü-Sounds gemeinsam (0/20/40/60/80/100 %), neuer
Menüpunkt unter *Anzeige & Sound*. Gilt für MP3 und Rainwave-Radio.
Beitrag von TheRealSutefan, auf echter Hardware getestet.

## v4.0 — Sammel-Rückmeldung

F11 startet jetzt wirklich ein zufälliges Spiel statt nur die Auswahl zu
bewegen. Titel schneiden auf CRT nicht mehr ab, sondern verkleinern
sich. Die Attract-Modus-Verzögerung ist einstellbar (30 s bis 15 min).
System-Menü umsortiert.

## v3.9 — Sammel-Rückmeldung

Spiele außerhalb von `/media/fat/games` werden dynamisch gefunden
(Netzlaufwerke, USB-Nummern über 5). ROM-Hacks und Randomizer gelten
nicht mehr als Müll. Mehrere Regionsversionen desselben Spiels bleiben
alle wählbar. F10 zum Verlassen eines Spiels funktioniert zuverlässig.

## v3.8 — Rainwave-Internetradio

Zweite Musikquelle neben den lokalen MP3s, fünf Sender, Titelanzeige
über die öffentliche Schnittstelle. Läuft auch im Stream-Overlay mit.

## v3.3 bis v3.7 — der Esc-Ausstieg, in vier Anläufen

Der Ausstieg aus einem Spiel funktionierte bei manchen Tastaturen gar
nicht. Drei Reparaturversuche gingen daneben, weil sie auf Vermutungen
statt auf Daten beruhten. Die echte Ursache fand erst eine Log-Datei
vom betroffenen Gerät: eine mechanische Tastatur legt drei
HID-Schnittstellen mit identischem Namen an, und die Tasten liefen über
eine andere als die überwachte. Jetzt werden alle gleichzeitig
überwacht.

## v3.2 — konsolidiert

Standard-Boot-Animation, Textabschneide- und Scroll-Reparaturen über
neun Info-Bildschirme (mit echten CRT-Fotos gefunden), Trophäenraum
umgebaut, RA-Erfolgs-Vitrine beschleunigt.

## v1.1 bis v3.1

Die Aufbauphase — vom ersten Spielebrowser über Boxart, Musik,
Joypad-Bedienung, RetroAchievements, Spielzeit-Tracker und
Trophäenraum bis zum CRT-Modus. Im
[Archiv](docs/CHANGELOG_ARCHIV.md) einzeln aufgeführt.
