# Changelog

Kurz gehalten: je Version ein Block mit dem, was man merkt.

Wer die Details will — welche Messung wozu geführt hat, welcher Versuch
danebenging, was ein Test gefunden hat — findet sie im
[ausführlichen Archiv](docs/CHANGELOG_ARCHIV.md) (alle Builds seit v1.1).

English: [`CHANGELOG_EN.md`](CHANGELOG_EN.md)

---

## Nach v4.7 — noch nicht veröffentlicht

**MiSTers eigene Favoriten, `update_all` aus dem Menü, und ein Blick auf
den Speicher.**

- **MiSTer-Favoriten**: was du im MiSTer-OSD als Favorit markiert hast,
  steht jetzt **mit in deiner Favoriten-Kategorie** — eine Liste, zwei
  Quellen. Deine eigenen zuerst, MiSTers dahinter, Doppelte nur einmal. Die
  Einträge verhalten sich wie jedes andere Spiel: Boxart, Beschreibung,
  Spielzeit, RetroAchievements, alles greift. In deine Favoritendatei wird
  dabei **nichts** geschrieben: entfernst du einen Favoriten im MiSTer-OSD,
  ist er auch hier weg.
- **`update_all` starten**: ein Menüpunkt neben der Core-Wahl, mit dem
  letzten Lauf in der Beschriftung („vor 23 Tagen"). Gestartet wird das
  vorhandene Skript — nachgebaut wird nichts. Eine Netzabfrage „gibt es
  Updates?" gibt es bewusst *nicht*: dafür müsste das Frontend die
  Datenbanken des MiSTer-Downloaders nachbauen, und das wäre eine zweite
  Quelle der Wahrheit für die wichtigsten Dateien auf der Karte.
- **Speicher-Wächter**: steckst du im Betrieb einen USB-Stick ein, sagt das
  Frontend Bescheid. Es liest **nicht** von selbst neu ein — das dauert bei
  30.000 Spielen Minuten und bleibt deine Entscheidung.

Zwei Dinge, die ich beim Hinsehen an mir selbst korrigieren musste: die
Core-Verwaltung aus Build 174 ist entgegen meiner ersten Behauptung
vollständig angeschlossen, und der **Core Browser existiert längst** —
Systemmenü → *Cores*, dort wählst du je System die Core-Fassung, mit
links/rechts, inklusive Warnung, wenn die gewählte Datei von `update_all`
gelöscht wurde. Beides habe ich vor dem Bauen geprüft, und genau deshalb
steht hier kein doppelt gebautes Feature.

**Schnelles Scrollen wirkt wieder — und eine Zahl, die vorher fehlte.**

- **Kachelansicht**: „Schnelles Scrollen" hatte seit den großen Kacheln
  (v4.7) im Raster keine Wirkung mehr. Grund war eine einzelne Grenze: bis
  zu einem Viertel der Bildhöhe durfte eine Kopie das Warten auf den
  Bildwechsel auslassen — ein Band mit den großen Kacheln ist aber ein
  gutes Drittel hoch. Die Grenze liegt jetzt bei 40 %, gemessen über alle
  acht Auflösungen; der volle Seitenaufbau (84 %) wartet weiterhin, dort
  entsteht der sichtbare Bildriss. Wer den Schalter aus hat, merkt nichts:
  ohne ihn wird nach wie vor überall gewartet.
  Die **Galerie** kopiert bei jedem Schritt das ganze Bild und wartet
  deshalb weiter — das ist eine eigene Baustelle, keine Zahl.
- **Ruckler-Zeile**: `flip=` war zweierlei in einer Zahl, Kopieren *und*
  Warten. Jetzt steht „davon vsync=" daneben. Das hat mich zweimal an die
  falsche Stelle geschickt; künftig steht es in der Zeile.
- **Bench**: neuer Abschnitt H, die Übertragungs-Matrix — was eine Kopie in
  den Bildspeicher je Größe und je Aufruf kostet, und was daraus für das
  Zusammenfassen benachbarter Bänder folgt. Auf einem PC sagt er
  ausdrücklich „nicht messbar", statt eine Zahl zu erfinden.

**Scrollen: ein Fünftel der Bytes auf den Schirm.**

- **Rechtecke statt Bänder.** Bisher ging jede Teilkopie über die *volle
  Breite*, auch wenn sich nur zwei Kacheln geändert hatten — `flip_rows()`
  kennt keine Spalten. Gemessen auf 1080p je Scrollschritt:

  | | vorher | jetzt |
  |---|---|---|
  | Kachelansicht links/rechts | 3,74 MB | **1,19 MB** |
  | Kachelansicht hoch/runter | 6,50 MB | **1,19 MB** |
  | Galerie | 7,91 MB (Vollbild!) | **3,71 MB** |

  Die **Galerie** kopierte seit v4.2 bei *jedem* Schritt den ganzen Schirm,
  obwohl sie längst nur Cover, Text und zwei Leistenkacheln neu zeichnet.
  Das ist der Grund, warum „schnelles Scrollen" dort nie etwas gebracht hat.
  Sie wartet auch jetzt noch auf den Bildwechsel — 3,71 MB sind 47 % des
  Bildes, und ein Riss quer durch Cover und Text wäre sichtbar. Die
  Kachelansicht darf mit 15 % auslassen.
- Gerechnet wird in C (dieselbe Funktion, die seit v4.6 den Hintergrund
  wiederherstellt); ohne `libdragend` läuft ein Python-Weg, der bitgenau
  dasselbe schreibt. Sollten kurze Zeilen auf deiner Karte je Byte zu teuer
  sein, genügt ein `touch /media/fat/frontend/rechteck_flip_aus` — kein
  Update. Die Zahl dazu liefert der neue **Bench-Abschnitt I**.
  *Nachgemessen auf dem DE10-Nano: kurze Zeilen kosten in C nur das
  1,2-fache, ein Scrollschritt 3,46 statt 18,55 ms — Faktor 5,4.*

**Freiräumen in C — die vergessene Hälfte von v4.6.**

- Vor jedem Zeichnen wird der Hintergrund freigeräumt, Zeile für Zeile. Für
  die Boxart-Spalte lief das seit v4.6 in C, für **alles andere** weiter in
  Python — und ausgerechnet das fällt bei jedem Scrollschritt an: 815
  Bildzeilen in der Kachelansicht, 1541 in der Galerie. Jetzt laufen beide
  über dieselbe C-Funktion. Auf dem Gerät kostet eine kurze Zeile in Python
  2,6-mal so viel wie in C (gemessen, Bench-Abschnitt I), und das
  Freiräumen ist knapp ein Drittel eines Schritts.
- **Bench-Abschnitt J** ist neu und sagt, woraus ein Schritt *besteht*:
  restore, blit, flip und Rest, je Schritt, mit Aufrufen und Zeilen. Bisher
  stand im Bench nur, was ein Schritt kostet — nicht, wohin die Zeit geht.
- **Korrektur an Abschnitt E**: er verglich das Scroll-Blitting im Hauptmenü
  gegen den *vollen* Seitenaufbau (83 ms). Beim Scrollen läuft aber der
  schnelle Pfad, und der stand im selben Bericht mit 60 ms. Die Ersparnis
  war um 23 ms zu groß angegeben. E misst den schnellen Pfad jetzt selbst.

**Die Galerie wartet nicht mehr auf den Bildwechsel.**

- Die Textspalte rechts wurde bei jedem Schritt auf ihrer **ganzen Höhe**
  freigeräumt — 1268×495 Punkte, also 2,39 der 3,71 MB eines Schritts. Platz
  gemacht wurde damit für die Beschreibung, die beim Scrollen seit v4.6
  absichtlich *gar nicht gezeichnet* wird. Jetzt wird nur so hoch geräumt,
  wie beim letzten Schritt wirklich Text stand: **1,74 statt 3,71 MB**.
- Damit liegt ein Galerieschritt bei 22 % des Bildes statt 47 % — unter der
  Grenze, ab der auf den Bildwechsel gewartet wird. Mit „schnelles Scrollen"
  an spart das auf dem Gerät weitere **12–16 ms je Schritt**. Die Grenze
  selbst ist unverändert: ein Riss quer durch Cover und Text wäre sichtbar,
  also wurde die Fläche kleiner gemacht und nicht die Regel weicher.
- **Zwei Defekte im Bench behoben**, beide in Abschnitten, die ich selbst
  gebaut habe: Abschnitt E starb mit `IndexError` (er zeichnete die Seite,
  die der vorige Abschnitt zufällig eingestellt hatte) und das Ergebnis war
  weg; Abschnitt J maß auf der Spieleliste dreimal dasselbe, weil er die
  Kategorie nicht wählte. Und J teilt den „Rest" jetzt auf: Text, Karten,
  Beschreibung, Hausarbeit.

**Auch die Listenansicht kopiert nur noch, was sich geändert hat.**

- Ein Navigationsschritt in der Liste ändert zwei Textzeilen links und die
  Boxart-Spalte rechts. Weil eine Teilkopie bisher nur *Zeilen* kannte,
  umfasste sie alles dazwischen — auf 1080p **86 % des Bildes für zwei
  Zeilen und eine Spalte**. Jetzt gehen beide Bereiche als Rechtecke auf den
  Schirm:

  | | vorher | jetzt |
  |---|---|---|
  | Spieleliste, ein Schritt | 6,83 MB | **3,12 MB** |
  | Hauptseite, ein Schritt | 5,89 MB | **1,30 MB** |

- Verwendet werden die Rechtecke nur, wenn sie **jede Zeile** des bisherigen
  Streifens abdecken — sonst bleibt es beim alten Weg. Diese Prüfung hat beim
  Bauen zweimal angeschlagen und jeweils einen stehengebliebenen Rest
  verhindert, bevor er entstehen konnte.
- **Abschnitt J des Benchs misst jetzt den echten Schritt.** Bisher rief er
  `draw()`, und das ist für die Liste der *volle* Neuaufbau — ihr leichter
  Pfad wird von dort nie gerufen. Im Bericht stand deshalb 132 ms für einen
  Schritt, den es so nicht gibt. Abschnitt B behält seine Zahlenreihe
  (vergleichbar seit v4.2) und sagt jetzt dazu, dass es der volle Aufbau ist.

**Flächen füllen in C — und eine Falle beim Teil-Update entschärft.**

- Auf dem Gerät war „karten" der größte benannte Posten eines Scrollschritts:
  **47 ms** in der Spieleliste, 35 in der Galerie, 28 auf der Hauptseite — das
  sind gefüllte und abgerundete Rechtecke samt Schatten, alles Schleifen über
  Bildzeilen. Die dicken Flächen füllt jetzt `libdragend` (Version 5).
- **Erst ab 256 Zeilen**, und das ist gemessen: der Sprung nach C kostet
  selbst etwas, und bei kleinen Flächen ist er teurer als die gesparten
  Zuweisungen (700×900 wird 2× schneller, 60×40 dagegen dreimal langsamer).
  Die großen Karten liegen alle darüber, die vielen kleinen Rahmen darunter.
  Der neue Bench-Abschnitt I/3 zeigt beides nebeneinander.
- **Eine alte `libdragend.so` bremst jetzt nicht mehr alles aus.** Bisher
  wurde jede Fassung verworfen, deren Nummer nicht genau passte — wer nur
  `frontend.py` aktualisierte, hatte damit *überhaupt kein* C mehr, auch nicht
  beim Verkleinern (Faktor 124 auf dem Gerät). Jetzt gilt eine Spanne: eine
  4er-Fassung wird weiter voll genutzt, nur die neue Funktion fehlt dann.
- Notausgang, falls es auf deiner Karte nicht lohnt:
  `touch /media/fat/frontend/flaechen_c_aus` — wirkt nach einem Neustart.
- **Bench-Korrekturen**: Abschnitt J pendelt jetzt im sichtbaren Fenster,
  sonst lief die Hälfte der Schritte als voller Aufbau und der Mittelwert war
  keine von beiden Zahlen. Und Abschnitt E vergleicht endlich Gleiches mit
  Gleichem: der leichte Pfad *ohne* Flip gegen das Blitten *ohne* Flip. Sein
  „Faktor 2,9" aus dem letzten Bericht war dadurch zustande gekommen, dass
  auf der einen Seite ein Vollbild-Flip und die Hausarbeit mitgezählt wurden.

**Die Rahmen — der Posten, den die Flächenschwelle übersehen hat.**

- Ein Mitschnitt *eines* Scrollschritts zeigte, welche Flächen nach Build 219
  noch in Python liefen, und es waren fast nur **Rahmen**: die Markierung um
  die Kachel, der Platzhalter „kein Artwork". Ein solcher Balken ist
  3 Punkte breit und 771 hoch — winzige Fläche, und trotzdem 771 Zuweisungen.
  Genau das hatte eine Schwelle in *Flächen* übersehen, so wie die vorige in
  *Zeilen* die breiten flachen Flächen übersehen hatte.
- Jetzt **zwei Schwellen mit ODER**: viele Zeilen lohnen, viel Fläche lohnt,
  wenig von beidem bleibt in Python. Und ein Rahmen geht als **ein** Aufruf
  weg statt als vier. Gemessen: 3×771 ist 14× schneller, ein Kachelrahmen
  14×, der Platzhalterrahmen 22×.
- Gezählt statt geschätzt — Python-Zeilen je Scrollschritt auf 1080p:

  | | vorher | jetzt |
  |---|---|---|
  | Spieleliste | 1557 | **9** |
  | Kachelansicht | 740 | **0** |
  | Galerie | 1415 | **9** |

  Auf dem Gerät kostet eine solche Zeile rund 0,009 ms; die Rechnung sagt
  also gut 13 ms je Schritt in der Liste und 12 in der Galerie. Was davon
  ankommt, sagt der Bench — nicht ich.
- **Die Eckenrundung besteht aus zwei Stufen, nicht aus zweihundert Zeilen.**
  Beim Nachmessen fiel auf, dass die Einzugstabelle einer Rundung nur zwei
  verschiedene Werte hat: die 192 Eckenzeilen der Boxart-Karte sind in
  Wahrheit vier Rechtecke. Senkrecht aneinandergrenzende Zeilen gleicher
  Breite werden jetzt zusammengefasst, bevor sie nach C gehen — das Aufbauen
  der Liste war danach teurer als das Zeichnen selbst.
- Ein leichter Scrollschritt auf dem Entwicklungsrechner: **Liste 1,4–1,9×,
  Galerie 1,2–1,5×** schneller; die Kachelansicht liegt hier im Rauschen,
  hat aber als einzige gar keine Python-Zeile mehr übrig.

**Die eigentliche Bremse: der Sprung nach C kostet auf dem Gerät eine
Millisekunde.**

- Aus deinem Bericht vom 29.09. lässt sich beides ausrechnen:

      C      = 1,00 ms + 0,0000057 × Punkte
      Python = 0,25 ms + Zeilen × (0,0080 + 0,000012 × Breite)

  Geprüft an allen sieben gemessenen Formen. Die erste Zahl ist die
  wichtige: **ein C-Aufruf kostet auf dem DE10-Nano rund eine
  Millisekunde**, auf dem Entwicklungsrechner 0,007. Ein Scrollschritt
  macht acht bis fünfzehn davon — das läuft auf, bevor irgendetwas
  gezeichnet ist.
- **Adressen und ctypes-Felder werden jetzt wiederverwendet.** Vor jedem
  Aufruf wurde die Speicheradresse neu ermittelt und die Rechteckliste neu
  in ein C-Feld geschrieben — obwohl es immer dieselben Puffer sind und
  beim Scrollen dieselben Rechtecke an derselben Stelle. Nachgezählt im
  echten Zeichenpfad: 8 (Liste), 11 (Raster), 15 (Galerie) Adressabfragen
  und 2–5 Felder je Schritt, **alle aus dem Zwischenspeicher, kein
  einziger Fehltreffer**.
- **Die Schwelle aus Build 220 war zu niedrig**, und dein Bericht hat es
  schwarz auf weiß gezeigt: `60x40 … 0,6x — genutzt: ja`. Eine Fläche, die
  durch die Schwelle kam und in C langsamer ist. Die Zahlen stammen jetzt
  vom Gerät (96 Zeilen bzw. 65536 Punkte statt 32/16384). Damit bleibt
  auch `853x21` in Python — das ist die **Zeilenmarkierung der Liste**,
  zweimal je Schritt, und sie hat in C je Aufruf rund 0,5 ms verloren.
- **Neu in Abschnitt J: `cover`.** Der REST liegt bei 38–79 ms je Schritt
  und ist überall der größte Posten. Gemessen wird jetzt die Coversuche
  samt Zugriffen auf die Karte (`os.stat`, `open`) — Abschnitt G hat
  vorher schon gezeigt, dass ein `os.stat` dort 0,20 ms kostet. Bleibt der
  REST danach groß, fehlt der nächste Posten, und dann ist *das* die
  Aufgabe.
- Auf dem Entwicklungsrechner ist von alldem nichts zu sehen (drei Läufe:
  −3 % bis +21 %, also Rauschen) — dort kostet der Sprung eben 0,007 ms.
  **Die Vorhersage steht im Build und ist prüfbar**: die Zeile `3x771` in
  Abschnitt I/3 ist fast reiner Grundaufwand und muss fallen, `60x40` muss
  „genutzt: nein" zeigen. Tut sie es nicht, war die Überlegung falsch.

**Und die Ecken sind jetzt wirklich rund.**

- Die Abbruchbedingung für die Eckenrundung war seit v1.x umgedreht: sie
  konnte nur „ganz eingerückt" oder „gar nicht" ergeben, nie etwas
  dazwischen. Die Karten hatten deshalb **rechteckig ausgeschnittene
  Ecken**. Aufgefallen ist es erst, als Build 220 die Eckenzeilen
  zusammenfasste — die Tabelle hatte nur zwei Stufen.
- **Es kostet nichts**: die Boxart-Karte braucht 0,304 statt 0,322 ms, weil
  die Eckenzeilen eines Viertelkreises im Mittel schmaler sind als die der
  Kerbe. Sie gehen weiterhin in einem einzigen C-Aufruf weg.

**Ein Spiel ohne Cover fragte bei jedem Scrollschritt erneut die Karte.**

- Der neue Posten aus Build 221 hat es gezeigt: in der Spieleliste
  **20 Zugriffe auf die SD-Karte je Schritt, 13,44 ms** — und daneben
  „cover 0,00". Die Zugriffe liefen also an der Messung vorbei, mitten
  durch den REST.
- Nachgestellt und gezählt: ein Eintrag **ohne** Cover kostete drei
  Zugriffe, und zwar bei jedem Schritt wieder — auch beim zehnten Mal auf
  denselben Eintrag. Gemerkt wurde bisher nur ein *Treffer*; ein **Nein**
  wurde nie gemerkt, und bei 30273 Spielen hat nicht jedes ein Cover.
  Dazu fragte eine zweite Stelle dieselbe Datei gleich noch einmal ab.
- Jetzt wird das Nein genauso gemerkt wie das Ja. Gezählt beim Hoch- und
  Runterscrollen: **2,00 → 0,00 Zugriffe je Schritt**; beim Vorwärtslaufen
  durch lauter neue Einträge 3 → 2 (der doppelte ist weg, der erste bleibt
  nötig).
- **Und das Nein bleibt nicht stehen.** Während du blätterst, rechnet der
  Arbeitsprozess Miniaturen auf die Karte — bliebe unser Nein darüber
  bestehen, tauchte das Cover nie auf. Sobald du die Taste loslässt, wird
  es weggeräumt und einmal richtig nachgesehen: einmal je Loslassen, nicht
  je Schritt. Wer während des Betriebs Artwork auf die Karte kopiert, sieht
  es damit nach dem Loslassen statt erst nach einem Neustart.
- **Abschnitt J nennt jetzt die Rufer**: unter der cover-Zeile stehen die
  drei häufigsten Aufrufer mit ihrer Zahl je Schritt. „Zwanzig Zugriffe"
  allein sagt nicht, welche.

**MiSTers eigene Schriften — als zweite Wahl.**

- Du wolltest eine andere Schrift, und dein eigener Einwand war der
  bessere Weg: **MiSTer bringt seine OSD-Schriften mit**, und was auf deiner
  Karte liegt, steht jetzt auch hier zur Wahl. Systemmenü → *Schrift*, direkt
  neben scharf/weich: die eigene (Vorgabe), **„wie im MiSTer-OSD"** (liest
  `font=` aus deiner MiSTer.ini) oder jede einzelne Datei aus
  `/media/fat/font`.
- **Mitgeliefert wird keine einzige.** Die verlinkte Schrift von der
  Download-Seite ist eine Digitalisierung der deutschen
  Kfz-Kennzeichenschrift; der Staat hat nie eine digitale Fassung
  veröffentlicht, die kursierenden Dateien sind Nachbauten mit unklarer
  Lizenz — und dieses Paket liegt öffentlich. Gelesen wird deshalb nur, was
  auf *deiner* Karte ohnehin liegt. Dieselbe Haltung wie bei der fremden
  Artwork-Datenbank.
- Das Format passte ohne Umweg: eine `.pf` ist 768 Byte, 96 Zeichen zu je
  8 Byte ab Leerzeichen — also genau unsere 8×8-Tabelle, nur mit
  umgekehrter Bitfolge.
- **Deine MiSTer.ini wird dabei nur gelesen**, nie geschrieben. Der Test
  prüft die Datei danach Byte für Byte.
- **Umlaute bleiben aus der eigenen Schrift.** Eine `.pf` endet beim „z";
  käme der Rest auch von dort, stünde „König der Löwen" voller Fragezeichen
  da.
- Ehrlich dazu: nicht jede `.pf` ist eine Textschrift. Ein paar (etwa aus
  Trackern) haben an den Buchstabenplätzen Symbole — das sieht man sofort
  und schaltet weiter.

**Die Update-Info kam seit neunzehn Builds nicht mehr an.**

- In deinem Log stand bei jedem Start `Build-Check fehlgeschlagen:
  Unterminated string`, und in deiner `update_check_state.json` stand als
  letzter gemeldeter Build **`2026-09-27-204`**. Beides zusammen war die
  Diagnose: die Antwort von GitHub wurde mit `read(2000)` gelesen — und das
  Feld mit der ausführlichen Build-Beschreibung ist seit Build 205 mehrere
  Kilobyte lang. Gelesen wurden also 2000 Byte **mitten aus einem Text**,
  und das Ergebnis war kein gültiges JSON mehr.
- Tückisch war, dass der Versions-Check daneben weiterlief (die
  VERSION-Datei ist vier Byte groß) und die Logzeile nach kaputtem JSON
  aussah statt nach einer zu kleinen Grenze. Die Grenze liegt jetzt bei
  256 kB, und bei einem Lesefehler nennt das Log die gelesene Länge **und**
  die Grenze.
- Ein Test prüft jetzt die **echte Datei im Paket** gegen die Grenze, mit
  mindestens dem Vierfachen Luft. Genau diese Prüfung hat gefehlt — sie
  wäre bei Build 205 angeschlagen.

**Und drei Dauerfrager aus dem Zeichenweg.**

- Zuerst der Grund, warum sie überhaupt sichtbar wurden: auf deinem Gerät
  lag noch die Datei `/media/fat/frontend/profile` aus einer früheren
  Fehlersuche. Damit lief um **jeden** Seitenaufbau ein vollständiges
  cProfile. Nach dem Löschen halbierten sich die Zahlen: Spieleliste 97,7 →
  **47,2 ms** je Schritt, Hauptseite-Galerie 106,7 → **58,3**, Hauptseite
  Liste 68,3 → **28,9**. Der Bench **warnt jetzt im Kopf**, wenn die
  Profilierung an ist — mit dem Befehl zum Abstellen daneben. Ein Messgerät,
  das seinen eigenen Zustand verschweigt, ist ein schlechtes Messgerät.
- `_games_signature` fragte mit **20,9 Zugriffen je Schritt** nach den
  ROM-Ordnern. Die Funktion sperrt sich jetzt selbst für acht Sekunden —
  unabhängig davon, ob der Aufrufer richtig zählt.
- `eq_effect_enabled` las einmal je Schritt von der Karte, nur um einen
  Schalter zu erfahren, den beim Blättern niemand umlegt. Jetzt aus dem
  Zwischenspeicher.
- Die PERF-Logzeile schrieb bei **jedem** Schritt ins Log, weil ein Schritt
  über ihrer 20-ms-Schwelle liegt — und jede Zeile ist ein Dateizugriff.
  Sie kommt jetzt höchstens einmal pro Sekunde und sagt dazu, wie viele sie
  verschluckt hat.

**Die Hauptseiten-Galerie war der letzte blinde Fleck.**

- Sie ist die **einzige** Ansicht, an der die Umbauten aus v4.7 nie
  vorbeigekommen sind: bei jedem Schritt ging das **ganze Bild** auf den
  Schirm, 7,9 MB und 14,8 ms, während die Spielelisten-Galerie daneben mit
  2,5 MB auskommt. Die Spuren wurden dort längst gesammelt — nur nie
  benutzt. Jetzt **3,92 statt 7,91 MB**.
- **Und ein Werkzeug, das die Frage mechanisch beantwortet**, an der ich in
  v4.7 schon einmal gescheitert bin: deckt der Rechteck-Flip wirklich alles
  ab, was sich geändert hat? Es vergleicht die *geänderten* Bildpunkte eines
  Schritts mit den *gemeldeten* Rechtecken; die Differenz sind Reste, die
  auf dem Schirm stehenbleiben, während der Puffer richtig aussieht. Damals
  waren das 210.600 Punkte, und gefunden wurden sie durch Zufall. Heute:
  alle sechs Ansichten, beide Auflösungen, **null ungedeckte Punkte**.

**Cover kopieren jetzt in C.**

- Für Cover und Textstreifen fehlte eine C-Funktion mit **zwei**
  Schrittweiten: ein dekodiertes Cover liegt dicht gepackt, das Ziel hat die
  Schrittweite des Bildschirms — die bisherige C-Kopie kann nur gleiche
  Raster. Beide liefen deshalb als Python-Schleife über die Bildzeilen, und
  im Bericht steht `blit` mit 6–12 ms je Schritt in **jeder** Ansicht.
- Gemessen am einzelnen Cover: Galerie 0,31 → **0,06 ms** (4,8×), Liste 0,64
  → **0,24 ms** (2,7×). Am Scrollschritt ist das hier nicht zu messen, und
  der Grund ist eindeutig: der Prüfstand hat gar keine Cover, `blit` läuft
  dort nie (nachgezählt: 0,0 Aufrufe je Schritt). Was ankommt, sagt dein
  Bench.
- Der Text folgt im nächsten Build — er braucht dieselbe Funktion, aber eine
  Umstellung am Textspeicher, und die will sorgfältig gemacht werden.

**Die Aussparung aus Build 234 hat nie gegriffen — drei Punkte zu hoch.**

- `karten` stand in deinem Bericht nach Build 234 unverändert bei 14,4 ms. Das
  war **kein Messfehler**: die Aussparung wurde verworfen, sobald sie auch nur
  einen Punkt über die geraden Mittelzeilen der Karte hinausragte — und genau
  das ist in der Listenansicht **immer** der Fall. Die Karte liegt bei y=36,
  das gerade Band beginnt bei y=57, die Oberkante des Covers bei **y=54**.
  Drei Punkte, und die ganze Ersparnis fiel weg.
- Jetzt wird **beschnitten statt abgewiesen**. Das ist genauso sicher: was
  übrigbleibt, ist eine *Teilmenge* dessen, was der Aufrufer als „wird gleich
  übermalt" zugesagt hat — weniger auszusparen ist immer erlaubt, mehr nie.
  Auf 1080p bleiben **76 % der Karte** ausgespart statt 0 %.
- Der Test prüft jetzt genau diese Zusage statt der alten Ablehnung: er malt
  **genau das Rechteck**, das er mitgegeben hat, und vergleicht Byte für Byte.

**Abschnitt J nennt die Boxart-Karte der Liste jetzt beim Namen.**

- Der Posten `cover` hatte nur den Weg von Raster und Galerie am Haken. In der
  Listenansicht kommt das Cover über `draw_art_panel()` — dessen Arbeit stand
  namenlos im `REST`. Dort steht `karten 14,4` und `REST 9,8 ms`, und genau
  dort habe ich drei Builds lang an der Stelle vorbeigemessen, die im Alltag
  ständig läuft.
- Neu: **`panel`**, mit dem *eigenen* Anteil (Karten, Kopien und Text darin
  haben ihre eigenen Posten und würden sonst doppelt zählen), und vom `REST`
  abgezogen. Bench-Nummer auf 6.

**Die Galerie räumte bei jedem Schritt eine ganze Textspalte frei — für
ein paar Zeilen Text.**

- Dein Bericht nennt `restore` in der Hauptseite/Galerie mit **12,99 ms** als
  größten Einzelposten überhaupt (5 Aufrufe, 1595 Zeilen). Ein neuer Messlauf
  (`tools/diag_restore_flip.py`) sagt, woher: **1259×507 Punkte, in jedem
  Schritt** — die komplette Textspalte neben dem Kategoriebild. Beschrieben
  sind davon ein Titel und ein paar Infozeilen.
- Freigeräumt wird jetzt genau das, was **zuletzt** dort stand, nicht die
  Spalte, in der es stehen könnte. Auf 1080p: **507 → 138 Zeilen**.
- **Und damit fällt auch der Flip**: die Spuren für den Bildspeicher entstehen
  aus dem Freiräumen, also wird weniger kopiert — **3,92 → 2,81 MB je
  Schritt** (−28 %). Der Bildspeicher ist laut Abschnitt H das Teuerste, was
  es hier gibt.
- **Die Deckungsprüfung hat mich dabei erwischt, und zwar zu Recht.** Ist die
  neue Beschriftung höher als die alte, lagen ihre unteren Zeilen außerhalb
  der freigeräumten Fläche — im Puffer richtig, auf dem Schirm nie:
  **5184 ungedeckte Punkte**. Der tatsächlich beschriebene Bereich wird jetzt
  von Hand als Spur eingetragen, wie es `draw_list_row()` auch tut. Danach:
  0 ungedeckte Punkte, Lightpath bitgenau, und ein Test wechselt eigens von
  einer langen auf eine kurze Beschriftung und vergleicht gegen den vollen
  Aufbau.

**Die vier Verschönerungen — drei neue, eine gab es längst.**

- **Scrollbalken rechts.** Bei 21.203 Einträgen in Arcade sagt er das, was
  sonst niemand sagt: wo du bist. Dünne Bahn, Läufer in Textfarbe.
- **Akzentbalken an den Zeilen.** Ein 3 Punkte breiter Streifen in der Farbe
  des Systems — an **jeder** Zeile, nicht nur an der markierten. Das ist
  nicht Geschmack: der Hintergrund der markierten Zeile *ist* bereits die
  Systemfarbe, ein Balken darauf wäre unsichtbar. An den übrigen Zeilen sagt
  er dir in gemischten Listen (Favoriten, Suche, Sammlungen) auf einen Blick,
  wozu ein Eintrag gehört.
- **Haarlinie zwischen Liste und Coverspalte.** Ein Punkt breit, gedämpfte
  Farbe — der Unterschied zwischen „zwei Spalten" und „ein Durcheinander".
- **Rahmen und Schatten am Cover gibt es längst** — seit Build 98 am Panel,
  seit Build 124 an den Kacheln. Ein zweiter Rahmen darüber wäre kein
  Gewinn, sondern ein Doppelrahmen. Ich habe es stattdessen mit einem Test
  festgehalten, damit es nicht still verschwindet.
- **Gemessen, wie du es verlangt hast** (`tools/diag_feinheiten.py`, jedes
  Element einzeln an und aus, abwechselnd gemessen und als mittlerer Lauf):
  Im Scrollschritt **+0,04 bis +0,06 ms** in den Listenansichten, in Raster
  und Galerie **nichts** (dort werden sie gar nicht gezeichnet). Der Grund:
  Scrollbalken und Haarlinie hängen am **Fenster**, nicht am Zeiger — beim
  leichten Scrollschritt ändert sich das Fenster per Definition nicht, sie
  werden also nur beim Seitenaufbau gezeichnet. Übrig bleibt der
  Akzentbalken mit zwei kleinen Rechtecken je Schritt.
- **Ein Schalter für alle drei**: Systemmenü → Anzeige & Sound →
  **Feinheiten**. Er wirkt sofort und kostet beim Zeichnen nichts — er steht
  als Modulvariable da, nicht als Dateiabfrage je Zeile. Wenn dein Bench
  einen echten Verlust zeigt, schalte ihn ab und sag Bescheid; dann fliegt
  der Akzentbalken wieder raus.

**Dein eigenes Hintergrundbild — und es kostet beim Zeichnen nichts.**

- Systemmenü → Anzeige & Sound → **Hintergrundbild**. Eigene Seite mit
  Ordnern, genau wie bei Maske und Schrift. Lege deine `.png` oder `.jpg` in
  **`/media/fat/frontend/backgrounds`** (Unterordner werden angezeigt). Das
  Bild wirkt **sofort beim Durchgehen** — die Seite, auf der du stehst, *ist*
  die Vorschau. Links/rechts schaltet an und aus, ohne die Auswahl zu
  verlieren.
- **Zur Performance-Frage, und die Antwort ist besser als gedacht: es kostet
  nichts.** `fb.clear()` kopiert schon heute einen **Vollbildpuffer** — die
  „einfarbige" Fläche ist nämlich gar nicht einfarbig, sie trägt die Vignette.
  Dasselbe gilt für die Teilwiederherstellung beim Scrollen. Was in dieser
  Vorlage steht, ist dem Kopieren egal. Nachgemessen: **0,680 ms mit
  Farbvorlage, 0,667 ms mit Bildvorlage.** Ein Test prüft genau das und wird
  rot, wenn es je auseinandergeht.
- Zugeschnitten wird **füllend** (keine Balken, Überstand fällt mittig weg),
  und es gibt eine **Abdunklung** in fünf Stufen — Text auf einem Foto ist
  sonst schwer zu lesen. Auch sie kostet nichts: sie wird **einmal beim
  Laden** ins Bild gerechnet, nicht bei jedem Bildaufbau.
- **Mitgeliefert wird kein Bild.** Dieselbe Haltung wie bei Masken und
  Schriften — und ein Test geht das ganze Paket durch und meldet jedes, das
  sich einschleicht.

**Die Listenansicht mit Covern: drei Viertel einer Fläche fielen weg, die
sofort wieder übermalt wurde.**

- Dein Wunsch war *„wenn noch was zu holen ist in der listenansicht das man
  mit eingeschalteten cover scrollen es noch schneller läuft"*. In deinem
  Bericht ist `karten` mit **13,75 ms** der größte Posten eines
  Scrollschritts dort — bei nur 5 Aufrufen. Ein neuer Messlauf
  (`tools/diag_kartenkosten.py`) sagt, woher: **eine einzige Karte, 769×945
  Punkte, in JEDEM Schritt.** Und direkt darauf landet das Cover.
- **Rund drei Viertel dieser Fläche wurden also gefüllt und sofort wieder
  übermalt.** Die Karte spart dieses Rechteck jetzt aus. Genau derselbe Fund
  wie damals in Build 97 beim Schatten — der alte Kommentar dort passt
  wieder: *„er war nur die falsche Frage"*.
- **Ausgespart wird nur, was sicher verdeckt wird.** Das Cover muss schon im
  Speicher liegen, groß genug sein und genau dorthin kommen; sonst wird voll
  gefüllt wie bisher. Ohne Cover ändert sich gar nichts.
- **Dass das Bild dasselbe bleibt, wird verglichen, nicht behauptet**:
  `tools/diag_karte_aussparen.py` zeichnet dieselbe Karte 35-mal mit und ohne
  Aussparung, über fünf Kartengrößen und sieben Cover-Seitenverhältnisse,
  und hält die Puffer Byte für Byte gegeneinander. Hier auf dem PC: 0,343 →
  **0,151 ms**. Was auf dem DE10-Nano ankommt, sagt dein Bench — dort kostet
  Füllen laut Abschnitt I rund 4,1 ms für 700×900.

**`--demo`: drei Minuten, die alles einmal zeigen.**

    python3 /media/fat/frontend/frontend.py --demo

- Neun Stationen: Hauptseite in **Liste, Raster und Galerie**, dann die
  größte Kategorie in allen drei Ansichten — mit Covern, so wie du scrollst
  —, dann das **Systemmenü**, und zum Schluss eine Abschlusskarte. Vor jeder
  Station eine kurze Titelkarte, die sagt, was gleich kommt.
- **Es läuft das echte Frontend.** Kein eigener Zeichenweg, keine
  nachgebauten Bildschirme: dieselben Seitenaufbauten, dieselbe Schrift,
  dieselbe Maske, deine Kategorien, deine Cover. Bewegt wird nur der Zeiger —
  mit genau der Schrittfunktion, die auch der Bench benutzt. Ein Demo-Modus,
  der sein eigenes Bild malt, zeigt am Ende etwas, das es gar nicht gibt.
- **Die Einblendung steht zwischen den Stationen, nicht darüber.** Eine
  dauerhafte Überlagerung müsste bei jedem Schritt neu gezeichnet werden und
  würde genau das verfälschen, was sie zeigen soll: die Geschwindigkeit.
- **Jede Taste bricht ab**, und danach steht alles wieder, wo es war —
  Seite, Kategorie, Eintrag, Ordnerpfad, beide Ansichten. Auch beim Abbruch
  mittendrin.
- Die Länge ist **eine Zahl**: die Stationen teilen sich die Gesamtzeit nach
  Gewicht.

**`--show`: der Absturz ist weg, und jetzt steht es auch auf dem Fernseher.**

- **Der Absturz.** `--show` ist bei dir in der zweiten Überschrift gestorben:
  `ValueError: too many values to unpack (expected 2)`. Ein Kategorieeintrag
  hat **drei** Felder (Name, Baum, Systemkey), ich habe zwei ausgepackt. Auf
  meinem Prüfstand war die Kategorieliste **leer** — die Schleife lief dort
  nie, und der Test meldete grün. Das war der eigentliche Fehler: ein Test
  mit einer leeren Liste prüft die Schleife nicht. Jetzt steht dort eine
  Kategorieliste, die der echten gleicht.
- **„ich dachte bei show sieht man was auf dem bildschirm" — stimmt.** Der
  Bericht läuft jetzt auch **auf dem Fernseher**, Seite für Seite, im
  eingestellten Farbschema. Es blättert von selbst weiter (eine Vorführung
  soll laufen), jede Taste geht sofort weiter, **Zurück bricht ab**. Auf der
  Konsole steht er weiterhin — zum Mitschicken taugt eine Textdatei besser
  als ein Foto vom Bildschirm.

**`--show`: der Bericht statt des Messgeräts.**

    python3 /media/fat/frontend/frontend.py --show

- Fünf Abschnitte, zum Vorlesen gebaut: **deine Sammlung** (Spiele,
  Kategorien, die zehn größten), **wie es aussehen kann** (Farbschemata,
  Ansichten, wie viele Lochmasken und Schriften auf deiner Karte liegen,
  die vier Maskenmodi), **was sich einstellen lässt** — und zwar mit den
  Werten, die gerade gelten —, **wie schnell es scrollt** (ms je Schritt
  und Schritte pro Sekunde, je Ansicht) und **wo was liegt**.
- **Keine von Hand gepflegte Funktionsliste.** So eine Liste ist nach drei
  Builds falsch, und zwar still. Alles kommt aus dem, was das Frontend
  ohnehin weiß: die Einstellungen sind **genau die Liste aus deinem
  Systemmenü**, die Masken und Schriften werden auf der Karte gezählt, der
  Bestand kommt aus dem laufenden Frontend.
- **Gemessen wird mit derselben Schrittfunktion wie im Bench.** Zwei
  Fassungen desselben Scrollschritts wären zwei Gelegenheiten
  auseinanderzulaufen — genau daran ist Abschnitt J in Build 218 schon
  einmal gescheitert (gemessen wurde der volle Neuaufbau statt des leichten
  Pfads). Der Bericht landet zusätzlich in `/tmp/dragend_show.txt`.
- Und: `--help` holt jetzt **nicht mehr die Einzelinstanz-Sperre**. In 230
  kam die Meldung erst hinter „Keine andere Instanz aktiv — starte
  Framebuffer/Eingaben …", für ein bloßes `--help` lief also der halbe
  Start. Jetzt steht die Prüfung vor allem anderen.

**`--show` gab es noch nicht — jetzt sagt das Frontend das auch.**

- Du hast `frontend.py --show` probiert und es startete einfach normal. Das
  lag an mir: die Option **gibt es noch nicht** (sie steht als Nächstes an),
  und alles außer `--bench` wurde bisher stillschweigend ignoriert. Jetzt
  meldet sich das Frontend bei einer unbekannten Option, zeigt die Liste
  dessen, was es kennt, und startet **nicht**. `--help` tut dasselbe ohne
  Fehler.

**Nachgemessen: nebenher war nicht genug — jetzt wird gar nicht mehr gesucht.**

- Dein Bench mit 229 zeigt beides. **Gut:** REST in der Galerie von
  **14,04 auf 6,83 ms** — der Zeichenweg wartet wirklich nicht mehr.
  **Schlecht:** `cover 1.91 (davon Karte 19.68 in 22 Zugriffen)`, vorher
  **2,83 ms** für dieselben Zugriffe. Die Arbeit war nicht weg, sie lag
  **nebenan** — und stritt sich mit dem Zeichenweg um dieselbe SD-Karte.
  `20.8/Schritt _games_signature > getmtime` stand unverändert da.
- Also in die Funktion geschaut statt noch einmal zu verlagern — und dort
  steht der eigentliche Fehler: die Frage lautet *„ist ein Ordner
  dazugekommen"*, verglichen werden nur die **Namen** — und trotzdem holte
  die Funktion für **jeden** Systemordner **jedes** Basispfads einen
  Zeitstempel. Rund 630 Dateiabfragen je Durchgang, deren Ergebnis danach
  weggeworfen wird.
- Ein neuer Name kann nur auftauchen, wenn sich an einem **Basispfad** etwas
  getan hat: entweder ist einer aufgetaucht (die spät angelaufene
  USB-Platte, um die es geht), oder in einem ist etwas angelegt worden — und
  das steht in seinem eigenen Zeitstempel. Das sind **13 Abfragen statt 630**,
  und nur wenn sich dort etwas gerührt hat, läuft überhaupt noch ein
  Durchgang. Im Normalfall: **gar keiner.**

**Zwei Hänger, die du gemeldet hast — beide gefunden und beide behoben.**

- *„ab und an wenn ich ordner und kategorien wechseln hab ich manchmal denn
  eindruck das es kleine hänger gibt"* — **den gab es wirklich.** In deinem
  Bericht steht `20.9/Schritt _games_signature > getmtime`. Über 30 Schritte
  sind das rund 630 Dateiabfragen, und bei 0,18 ms je warmem `os.stat`
  (Abschnitt G) sind das **rund 110 ms — in einem einzigen Schritt**. Es ist
  der Fingerabdruck der ROM-Ordner, mit dem das Frontend eine spät
  angelaufene USB-Platte erkennt. Er wird aufgeschoben, solange du eine Taste
  **hältst** — lief also genau dann, wenn du aufhörst zu scrollen oder die
  Kategorie wechselst. Jetzt läuft er **nebenher in einem eigenen Faden**;
  der Zeichenweg bekommt sofort die zuletzt bekannte Antwort. Die ist
  höchstens acht Sekunden alt, und das war schon immer in Ordnung — es geht
  um ein Laufwerk, das ohnehin erst irgendwann auftaucht.
- *„die roms die keine boxarts haben ploppen immer etwas später auf oder
  werden nachgerechnet"* — **auch das stimmte.** Das gemerkte „da ist nichts"
  aus Build 222 wurde bei **jedem** Stillstand weggeworfen, also jedesmal,
  wenn du aufhörst zu scrollen — und damit genau in dem Moment, in dem du
  hinsiehst. Für jeden Eintrag ohne Artwork wurden dann wieder drei
  Dateizugriffe fällig (im Bericht: `cover 1.91, davon Karte 2.83 in 23
  Zugriffen`). Jetzt hält das Nein **höchstens 30 Sekunden**, statt bei jedem
  Anhalten zu verfallen. Legst du neue Artwork auf die Karte, ist sie
  spätestens eine halbe Minute später da — und wenn der Arbeitsprozess eine
  Miniatur fertig rechnet, räumt er sein eigenes Nein weiterhin **sofort**
  weg, daran ändert sich nichts.

**Die Schrift bekommt dieselbe Seite wie die Lochmaske — und die Maske
die vier Modi vom MiSTer.**

- **Schrift**: Systemmenü → *Schrift* öffnet jetzt eine eigene Seite mit
  **Ordnern**, genau wie bei den Masken. Oben stehen die eigene Schrift des
  Frontends und „wie im OSD" (die aus deiner MiSTer.ini), darunter der
  Ordnerbaum aus `/media/fat/font`. Die Schrift wechselt **sofort beim
  Durchgehen** — Titel, Liste und eine Probezeile (`0O 1lI 8B 5S …`) stehen
  schon in der Schrift, auf der der Balken steht. Das Durchschalten mit
  links/rechts ist entfallen.
- **Die vier Maskenmodi**: `1x`, `2x`, `1x gedreht`, `2x gedreht` — dieselben
  vier wie im MiSTer-OSD. Eigene Zeile oben in der Maskenauswahl,
  links/rechts dreht sie durch, und die Vorschau daneben zeigt sofort den
  Unterschied. Auf 1080p ist eine 1×-Maske so fein, dass man sie kaum sieht;
  **2× ist meist das, was man will**. „Gedreht" kippt das Muster um 90° —
  aus senkrechten Streifen werden waagerechte.
- **Das kostet beim Zeichnen nichts.** Beides ist eine Umformung der
  Mustertabelle **beim Laden**, nicht je Bildpunkt. Danach rechnet C genau
  wie vorher. Eine 16×16-Maske wird in 2× zu 32×32; die C-Fassung nimmt bis
  64×64.
- Unter der Haube: das Blättern durch Ordner steht jetzt **einmal** da
  (`fe/dateibaum.py`) und wird von beiden benutzt. Zwei Stellen mit
  derselben Aufgabe laufen sonst auseinander.

**Der Textzeichner läuft jetzt in C.**

- Der letzte große Posten aus deinem Bericht vom 02.10.: `text` mit 15,57 ms
  je Scrollschritt in der Galerie, 31 % des ganzen Schritts. Mehrere Zeilen
  gehen jetzt als **ein Bund** nach C statt als acht einzelne
  Python-Schleifen — die Datenzeilen unter dem Cover und die Beschreibung
  sind die beiden Aufrufer.
- **Die Schwelle ist aus Gerätezahlen gerechnet**, nicht geraten: ein
  C-Aufruf kostet auf dem DE10-Nano rund 1 ms (Build 221), ein Streifen zu
  bauen rund 3 ms für 1248×16 Punkte. Umschlagpunkt bei ~5700 Punkten,
  gewählt 6000. Auf der Röhre bleibt damit fast alles in Python, und das ist
  richtig so — dort sind die Streifen klein.
- **Neu dabei: ein Text wird erst beim zweiten Auftritt gemerkt.** Beim
  Scrollen kommt jeder Titel genau einmal vor; Menüpunkte und Kopfzeilen
  kommen bei jedem Bild wieder. Vorher verdrängten die Einmaligen genau die,
  die getroffen worden wären.
- Was ankommt, sagt dein Bench — hier auf dem PC ist Text ohnehin billig.
  Bewiesen ist die Richtigkeit: derselbe Text, beide Wege, Byte für Byte
  verglichen über den ganzen ASCII- und Latin-1-Bereich, alle Schriftgrößen
  und die Ränder.

**Die Lochmasken stehen jetzt in Ordnern — und MiSTers Presets sind dabei.**

- Du hattest recht: eine Liste aus 1207 Zeilen ist keine Auswahl. Die Seite
  zeigt jetzt **die Ordnerstruktur, wie die Sammlung selbst sie anlegt** —
  hoch/runter wählt, **OK öffnet einen Ordner oder nimmt eine Maske**,
  Zurück geht **eine Ebene hoch** und erst an der Wurzel aus der Seite
  heraus. Hinter jedem Ordner steht, wie viele Masken darin liegen; wo du
  herkommst, steht unter dem Titel; und der Cursor landet beim Zurückgehen
  wieder auf dem Ordner, aus dem du kommst. Ordner ohne eine einzige Maske
  werden weggelassen.
- Öffnest du die Seite, startest du **dort, wo deine aktuelle Maske liegt** —
  nicht wieder ganz oben.
- **In `/media/fat/Presets` lag tatsächlich etwas für uns.** Ein Preset ist
  eine winzige INI mit einem ganzen Satz Videoeinstellungen, und eine ihrer
  Zeilen heißt `mask=` — die nennt genau eine Datei aus deinem
  `Shadow_Masks`. Ganz oben in der Liste steht deshalb jetzt
  **MiSTer-Presets (Empfehlungen)**: fertige, benannte Vorschläge von
  Leuten, die die Masken kennen. Presets ohne Maske und solche, deren Maske
  nicht auf der Karte liegt, fallen weg — ein Eintrag, der beim Drücken
  nichts tut, ist schlimmer als keiner.
- **`/media/fat/Filters` geht nicht**, und das ist keine Faulheit: das sind
  Koeffizienten für MiSTers **Scaler** (vier Abgriffe, sechzehn Phasen,
  −128…128). Sie bedeuten nur etwas, während ein Bild *skaliert* wird.
  Dragend malt direkt in der Auflösung des Bildschirms — es gibt bei uns
  keine Skalierstufe, in die man sie einhängen könnte. Scanlines in Dragend
  sind dagegen schlicht eine 1×2-Maske, und die hat die Sammlung bereits.

**MiSTers Lochmasken liegen jetzt auf Dragends Bild.**

- Systemmenü → **Lochmaske**. Eigene Seite, denn MiSTers Sammlung hat über
  tausend Masken — mit links/rechts durchzuschalten wäre keine Auswahl,
  sondern eine Strafe. Hoch/runter wählt, **links/rechts schaltet den Effekt
  an und aus, ohne die Auswahl zu verlieren**, OK übernimmt.
- Die Maske wirkt **sofort auf dieser Seite**, samt Graukeil und drei
  Farbbalken als Vorschau. Eine Maske nach Dateinamen auszuwählen und erst
  danach zu sehen, wäre Raten.
- **Mitgeliefert wird keine einzige.** Gelesen wird, was in
  `/media/fat/Shadow_Masks` liegt — MiSTers eigene Sammlung, auf deiner
  Karte. Ein Test geht das ganze Paket durch und meldet jede Maskendatei,
  die sich einschleicht.
- Beim Lesen gab es eine Überraschung: eine Datei kann **mehrere Muster** für
  verschiedene Bildhöhen enthalten. Der erste Entwurf kannte nur das erste
  und warf 106 von 1207 Dateien weg — ausgerechnet die aufwendigsten (Sony
  PVM, Commodore 1084). Jetzt werden **1207 von 1207** gelesen.
- **Was es kostet, steht hier und ist gemessen.** Der erste Entwurf
  multiplizierte je Bildpunkt — Faktor neun gegenüber einer bloßen Kopie.
  Mit einer Tabelle statt Multiplikation und einem eigenen Weg für
  gleichförmige Musterzeilen (bei Scanlines ist jede zweite Zeile neutral,
  also eine normale Kopie) kostet ein Scrollschritt hier **+0,7 bis +1,6 ms**
  mit einem feinen Muster und **+0,2 bis +0,4 ms** mit Scanlines. Auf dem
  DE10-Nano ist Rechnen je Bildpunkt teurer — dafür ist der Schalter da.

**Gemischte Kategorien hängen nicht mehr beim Betreten.**

- Die Meldung war ungewöhnlich präzise, weil sie fünf Kategorien nannte und
  keine sechste: Weiterspielen, RA-Erfolgsjäger, Sammlung, 2026 entdeckt,
  Kurzweilige Spiele. **Kein** Systemordner — obwohl die bei 30278 Spielen
  die größeren sind. Mehr Einträge konnten es also nicht sein.
- Was diese fünf unterscheidet, ist eine einzige Eigenschaft: ihre Einträge
  kommen aus **verschiedenen Systemen**. Und die beiden Namensverzeichnisse,
  über die ein Cover gefunden wird, werden **je System** gebaut — bei einer
  gemischten Kategorie also alle in dem einen Moment, in dem die Seite zum
  ersten Mal gezeichnet wird. Gezählt im Raster: ein System = **1**
  Verzeichnisdurchlauf, zwölf Systeme = **10**. Auf dem DE10-Nano kostet ein
  Durchlauf über einen Cover-Ordner rund 167 ms. Das war die Wartezeit, und
  sie steckte nicht im Zeichnen.
- Jetzt wird **im Ruhemoment vorgearbeitet**: während der Zeiger auf einer
  Kategorie steht, wird je Leerlauf-Tick **ein** System vorbereitet. Nach dem
  Ruhemoment kostet das Betreten **null** Durchläufe — in Raster und Galerie
  gemessen, in der Listenansicht gab es das Problem nie (dort hängt genau ein
  Cover am Panel, also genau ein System).
- **Ein System je Ruhemoment, kein Hintergrund-Thread, der alles durchläuft.**
  Der Aufbau ist nur zum Teil Warten auf die Karte; der andere Teil ist eine
  Schleife über jeden Dateinamen, und die hält durchgehend die GIL. Genau
  daran ist Build 107 schon einmal hängengeblieben („warum ist nach einem
  Neustart das Hauptmenü so träge?"). Der Warmlauf bricht sofort ab, sobald
  wieder eine Taste kommt.
- **Ehrlich dazu:** wer eine gemischte Kategorie *sofort* betritt, ohne einen
  Moment auf ihr zu stehen, wartet weiter — nur eben nicht mehr für alle
  Systeme. Wer sie aussucht, wartet gar nicht mehr.

**Der Demo-Modus zeigt jetzt wirklich etwas.**

- Gemeldet wurde: „zuckt in der Listenansicht nur in den ersten drei Zeilen
  rum, System-Menü und Einstellungen werden gar nicht gezeigt, dann öffnet er
  nur Zufalls-Zock und bleibt dort stehen". Alle drei Punkte hatten je eine
  eigene Ursache, und zwei davon waren derselbe Denkfehler.
- **Das Zucken in den ersten drei Zeilen**: wie viele Zeilen ins Fenster
  passen, wird **während** des Zeichnens festgelegt. Die Demo hat danach
  gefragt, **bevor** in der neuen Ansicht einmal gezeichnet wurde — und bekam
  den Startwert 5, also ein Fenster von drei Zeilen. Jetzt wird erst
  gezeichnet, dann gefragt: 13 Zeilen statt 3.
- **Das System-Menü**: die Station stand auf der obersten Ebene, und die hat
  bei wenigen Einträgen nichts zu zeigen. Jetzt steigt sie in den
  vollsten Unterordner ab, wenn dort mindestens vier Einträge liegen.

**Hintergrundbilder erscheinen jetzt sofort.**

- Gemeldet: „wenn ich mehrere background bilder in denn ordner packe und
  diese dann durchklicke dauert das immer sehr lang bis es angezeigt wird.
  **werden diese noch vorbereitet? und jedesmal neu?**" — beide Fragen waren
  richtig gestellt.
- Der Weg wurde zerlegt, und **ein einziger Posten war 90 bis 98 Prozent**:
  das Abdunkeln. Skalieren 0–26 ms, Zuschneiden 2–5 ms, **Abdunkeln
  214–233 ms**. Und es war nicht die Idee, sondern die Schreibweise — dort
  stand eine **Python-Schleife über jedes Byte**, bei 1920×1080 also über 8,3
  Millionen. Dieselbe Arbeit in C erledigt: **14,6-mal schneller, bitgenau
  dasselbe Bild** (214 → 15 ms). Auf dem MiSTer ist Rechnen je Bildpunkt ein
  Vielfaches teurer; dort waren das die Sekunden.
- **Was NICHT eingebaut wurde, obwohl es fertig war:** die fertigen Vorlagen
  auf der Karte ablegen — der eigene Vorschlag aus der Meldung. Das war
  gebaut, mit zwölf grünen Tests. Dann kam die Messung: **der warme Weg war
  teurer als der kalte** (ein 1080p-JPEG zu dekodieren kostet 33,9 ms, das PNG
  neu zu lesen 19,0 ms). Also ist es wieder herausgeflogen, **bevor** es
  ausgeliefert wurde. Statt dessen stehen jetzt die **Teilzeiten im Log**, eine
  Zeile je Bildwechsel: nach der Änderung ist der größte Posten das
  Dekodieren, und das hängt am Format und an der Karte — die Zahl vom Gerät
  entscheidet, ob noch etwas zu tun ist.

**Die Vorführung dreht sich jetzt um die Einstellungen.**

- Gemeldet: „ich sehe am ende immer noch zufalls zock anstatt dass dort unter
  der kategorie ein paar einstellungs sachen gezeigt werden. finde ich blöd!"
- **Die Ursache war die Heuristik aus dem letzten Build.** Die Station stieg
  in den Unterordner mit dem *meisten Inhalt* ab. Auf dem Prüfstand ist das
  „Anzeige & Sound" mit 27 Einträgen — deshalb war der Test grün. Auf einer
  echten Karte zählen aber **Scripts und die Standalone-Cores** mit, und
  45 Skripte schlagen 27 Einstellungen. Die Vorführung zeigte Skriptnamen.
- **Jetzt stehen fünf Einstellungsgruppen namentlich da** — Anzeige & Sound,
  Optionen, Statistiken & Erfolge, Eingabe & Sprache, Wartung — jede mit einer
  Titelkarte, die sagt, was man dort machen kann. Fehlt eine Gruppe auf dem
  Gerät, wird ihre Station **übersprungen**; ersetzt wird nichts. Eine
  Vorführung, die etwas anderes zeigt als angekündigt, ist schlimmer als eine,
  die eine Station weglässt.
- **Die Zeit ist umverteilt**, genau wie gewünscht: Ansichten von 7,8 auf
  **4,6**, Einstellungen von 1,4 auf **6,2**.
- **Jede Station schreibt ins Log, was sie wirklich zeigt** (Seite, Ansicht,
  Kategorie, Zahl der Einträge, Ordnerpfad). Zweimal hintereinander hat die
  Vorführung etwas anderes gezeigt als angekündigt, und beide Male war das von
  außen nicht feststellbar — es hing an Dingen, die nur auf dem eigenen Gerät
  so sind. Eine Zeile je Station beantwortet das beim nächsten Bericht.
- Und eine **Korrektur zum letzten Build**: „öffnet nur Zufalls-Zock" wurde
  dort dem Attract-Modus zugeschrieben. Das war falsch — `--demo` beendet das
  Frontend direkt nach der Vorführung, der Leerlauf kommt nie mehr dran. Die
  Zeile von damals bleibt als Aufräumzeile stehen und ist jetzt auch so
  benannt.

**Scrollen mit Cover: drei Füllaufrufe weniger je Schritt.**

- Gefragt: „wenn ich in arcade ordner gehe mit cover wechsel anzeigen und nach
  unten gedrückt scrolle, kann man da noch was an anzeigezeit bzw
  geschwindigkeit rausholen?"
- **Der Prüfstand war an dieser Stelle blind.** Er hat keine Cover-Dateien —
  damit bleibt `art` leer, und der Rahmen um das Cover wird gar nicht
  gezeichnet. Vier Einzelaufrufe, die es auf dem MiSTer in *jedem* Schritt
  gibt, tauchten in keiner Messung auf. Die Diagnose **schiebt jetzt ein
  Cover unter**, und damit läuft derselbe Weg wie auf dem Gerät.
- Der Rahmen ist jetzt **ein** Aufruf statt vier: in der Listenansicht
  **8 → 5** Füllaufrufe je Schritt. Dass das etwas bringt, steht im eigenen
  Bench, Abschnitt I.3: eine 60×40-Fläche kostet in C 0,489 ms, eine 697×3
  0,318 ms — beides *winzige* Flächen. Das ist nicht die Fläche, das ist der
  Aufruf. Drei Aufrufe weniger sind auf dem Gerät rund **1,2 ms je Schritt**.
  Gezeichnet wird bitgenau dasselbe, über fünf Geometrien Byte für Byte
  geprüft.
- Es ist genau der Griff aus Build 220 — dort wurden der Kachelrahmen und der
  *Platzhalter*-Rahmen zusammengefasst. Der Rahmen um das *tatsächliche* Cover
  war dabei übersehen worden und ist seit zwanzig Builds mitgelaufen.

**Der Bench bekommt einen Abschnitt K — und zwei Berichtsfehler weniger.**

- **Was noch nicht erklärt ist, steht jetzt auch so da.** Nach dem
  Kostenmodell müsste `karten` in der Listenansicht rund 3 ms kosten; im
  Bericht stehen 13,81. Zehn Millisekunden ohne Namen, in jedem Schritt — und
  auf dem Entwicklungsrechner nicht nachstellbar, weil derselbe Schritt hier
  1,4 statt 39 ms braucht. Abschnitt K misst deshalb **auf dem Gerät**, mit
  untergeschobenem Cover, je Ansicht die Zahl der Aufrufe und die **ms je
  Aufruf**.
- **`(davon Karte 3.35 in 0 Zugriffen)`** war kein Widerspruch im Frontend,
  sondern `%d` auf 0,7. Steht jetzt mit Dezimalstelle da.
- **`0.6/Schritt _basen_merkmal > getmtime`** sah nach einem Posten aus. 0,6
  Zugriffe × 0,18 ms sind **0,1 ms je Schritt** — ein einziger Durchlauf über
  die Spielewurzeln, über 30 Schritte verteilt; die Selbstsperre von Build 229
  greift also. **Hier war nichts zu beheben**, und ohne die Zeit daneben war
  das nicht zu sehen. Die Zeilen nennen jetzt die Zeit und sind nach Zeit
  sortiert.

**Drei Dinge, die der erste Bericht mit Abschnitt K über den Bench selbst
gesagt hat — zwei davon eigene Fehler.**

- **Abschnitt K lief lautlos ins Leere.** Im Bericht stand „kein
  Bild-Zwischenspeicher — übersprungen": die Funktion, die das Cover liefert,
  sitzt auf dem Bild-Zwischenspeicher selbst, das Bench bekommt aber
  absichtlich das Modul übergeben. Der ganze Abschnitt sprang ab — mit einer
  Zeile, die wie eine Geräte-Eigenschaft klingt statt wie ein
  Programmierfehler. Jetzt werden beide Fälle bedient.
- **Der Posten `karten` wurde kleiner, weil ich weggesehen habe.** Build 241
  hat vier Aufrufe zu einem zusammengefasst; `karten` fiel von 13,81 auf
  13,02 ms — aber der neue Aufruf stand in **keinem** Zähler. Ein Teil der
  Ersparnis war also keine, sondern Blindheit. *Ein Posten, der kleiner wird,
  weil man wegsieht, ist schlimmer als ein großer.*
- **Abschnitt E hat sein Urteil umgedreht.** Zwei Läufe, dasselbe Gerät, zwei
  Tage auseinander: einmal „knapp besser (7,9 ms)", einmal „es lohnt NICHT".
  Nichts hatte sich geändert — beide Seiten streuen um rund 15 Prozent, und
  die Schwelle war scharf. Jetzt wird **abwechselnd** gemessen, der Median
  über mehrere Runden genommen und die **Streuung mit ausgegeben**; liegt der
  Unterschied nicht über ihr, sagt der Abschnitt „ZU KNAPP" statt zu urteilen.
  Das ist die ehrliche Antwort und zugleich die nützlichere: was im Rauschen
  liegt, merkt beim Scrollen niemand.

**Und eine echte Lücke: woraus besteht der kalte Fall?**

- `Spieleliste liste je Schritt kalt 296,82 ms` ist der größte Einzelwert des
  ganzen Berichts, und was darin steckt, stand nirgends. Aus zwei anderen
  Abschnitten zusammengerechnet kam ich auf 180 ms — die restlichen **116
  waren geraten**. Davon hängt ab, ob die nächste Arbeit am Dekodierer oder am
  Verkleinerer ansetzt.
- Abschnitt B **zerlegt den kalten Durchlauf jetzt selbst**, an den echten
  Dateien des Geräts in den echten Kastengrößen: dekodieren, verkleinern,
  Rest — jeweils mit der Zahl der Aufrufe. Die Zähler werden direkt danach
  wieder gelöst; blieben sie stehen, würden alle folgenden Abschnitte durch
  sie hindurch messen, und das wäre ein Messfehler, der nach einem Befund
  aussieht.

**Vier Verschönerungen — und was sie kosten, steht dabei.**

Alle vier hängen am **Feinheiten-Schalter** (System → Anzeige & Sound), den
du dir ausdrücklich gewünscht hast.

- **Die Systemfarbe in den feinen Elementen**: der Läufer des Scrollbalkens
  und die Haarlinie zwischen Liste und Coverspalte nehmen jetzt den Ton des
  Systems an, gedämpft statt pur. Das **kostet nichts** — es ist eine Farbe,
  und die Elemente werden ohnehin gezeichnet.
- **Ein dünner Akzentstrich unter der Kopfzeile**, in derselben Farbe: er
  sagt auf einen Blick, in welchem System du bist. Kostet **einmal je
  Seitenaufbau** und je Scrollschritt nichts.
- **Abgerundete Cover-Ecken**: Rahmen und Cover bekommen eine gemeinsame
  Rundung. Gemessen **ein** Füllaufruf mit 16 Rechtecken, auf dem MiSTer rund
  **0,71 ms** — und nur dann, wenn ein Cover da ist; beim schnellen Scrollen
  wird die Boxart ohnehin ausgelassen. In allen drei Ansichten liegt der
  Unterschied im Rauschen.
- **Der Anfangsbuchstabe beim Schnellscrollen**, groß in der Coverspalte. Bei
  1041 Einträgen in Arcade sagt er, wo du gerade bist — und er steht genau an
  der Stelle, an der die Karte beim Scrollen **ohnehin leer** ist: kein
  zusätzliches Freiräumen, kein zusätzlicher Flip. Beim Loslassen zeichnet
  das echte Cover darüber.

**Scrollen mit Cover: die Karte spart den Cover-Kasten aus.**

- Abschnitt K hat geliefert, wofür er gebaut wurde — den größten Einzelposten
  eines Scrollschritts, mit Namen und Zahl: **die Cover-Karte, 8,295 ms**, bei
  einem Schritt von 39,42 ms.
- **Was dabei passierte:** hältst du die Taste gedrückt und ist „Cover sofort"
  an, wird das Cover übersprungen — die Karte aber **jeden Schritt** komplett
  neu gefüllt. Dabei sieht der Cover-Kasten genauso aus wie im Schritt davor:
  derselbe leere Kasten, derselbe Anfangsbuchstabe. Nur der **Text** darunter
  wechselt.
- Jetzt wird die Karte weiter gezeichnet — Ecken, Schatten, Rand, Textbereich
  —, aber die **Fläche des Cover-Kastens ausgespart**. Den Mechanismus dafür
  gibt es seit Build 234/238. Gemessen: gefüllte Bytes **2,71 → 0,66 MB**.
  Nach dem Kostenmodell aus dem Bench sind das auf dem MiSTer **6,73 → 2,89
  ms** je Schritt.
- Es greift nur **ohne** Cover: mit Cover wechselt das Bild ohnehin jeden
  Schritt, da gibt es nichts zu sparen.

**Und etwas, das fertig und schneller war — und trotzdem nicht ausgeliefert
wird.**

- Der erste Entwurf ließ die Karte **ganz** weg und malte nur den Textblock.
  Gemessen war er besser: gefüllt 2,71 → 0,44 MB, geflippt 3,62 → **1,13 MB**.
  Dafür waren zusätzlich der Flip umgebaut (getrennte Bänder statt einer
  Spanne) und eine Rückmeldung aus dem Panel eingebaut. Beides war fertig und
  grün.
- **Dann hat ein byte-genauer Test es überführt:** 69 Bytes Unterschied
  zwischen Puffer und Bildschirm, an der unteren rechten Kartenecke — ein
  Dreieck von 17 Bildpunkten. Die Umgebung der Eckenrundung wird nämlich
  *nicht* von der Karte gefüllt; ohne den Kartenaufruf blieb dort, was der
  vorige Schritt hinterlassen hatte. Genau die Sorte Rest, die dieses Projekt
  fünfmal gejagt hat.
- Die Aussparung ist der kleinere, aber **erklärbare** Gewinn. Der Flip-Umbau
  ist wieder **ausgebaut** — er war für einen Entwurf gebaut, den es nicht
  mehr gibt, und unbenutzte Maschinerie im Flip-Pfad ist genau dort, wo man
  sie nicht haben will.
- **Ein Fehler, vor dem Ausliefern gefunden:** die Kennung des Covers stand
  erst als Speicheradresse da. Python gibt die Adresse eines aufgeräumten
  Objekts wieder aus — zwei verschiedene Cover gleicher Größe hätten dieselbe
  Kennung bekommen, und dann wäre das Cover des vorigen Spiels stehen
  geblieben. Jetzt entscheidet der Pfad.

**Das Wasserzeichen gibt es nicht — und der Grund gehört dazu.**

Gewünscht war das System-Logo dezent *hinter der Liste*. Dort liegt der
Hintergrund, und den holt der Scrollweg aus seinem Zeilenspeicher zurück —
ein Logo müsste also **in** der Vollbildvorlage stehen, eine je Kategorie,
**8,3 MB das Stück**. Genau diesen Posten hat Build 235 herausgenommen. Das
Systemlogo gibt es außerdem schon dort, wo Platz dafür ist: auf der
Kategorienseite, neben der Liste. Statt dessen der Akzentstrich oben.

**Und ein Fund über das eigene Werkzeug.**

Der Akzentstrich hat **drei Anläufe** gebraucht, und jeder sah beim Hinsehen
richtig aus: einmal lag er im Band der ersten Listenzeile (2617 abweichende
Bildpunkte), einmal richtig — aber er *wanderte*, weil die Listenposition vom
markierten Eintrag abhängt (2737), einmal passte er auf 1080p und lag bei
320×240 zwei Punkte zu tief (160). Gefunden hat alle drei dasselbe Werkzeug,
das jeden leichten Zeichenweg gegen einen vollen Neuaufbau vergleicht.
**Dabei kam heraus, dass der Scrollbalken-Läufer dieselbe Eigenschaft hat** —
mit der alten grauen Farbe fiel das nie auf. Jetzt wird es für alle vier
Auflösungen geprüft.
- **„öffnet nur Zufalls-Zock und bleibt dort stehen"** war kein Fehler der
  Vorführung, sondern ihre **Folge** — und der überraschendste Befund des
  Builds. Der Attract-Modus heißt im Menü „Zufalls-Zock — Spiel ziehen" und
  startet nach voreingestellt 90 Sekunden ohne Eingabe. Die Vorführung läuft
  180 Sekunden und hat ihre eigene Schleife: die Eingabe-Uhr stand danach
  drei Minuten in der Vergangenheit, und der **erste** Leerlauf-Tick nach der
  Vorführung erfüllte die Bedingung sofort. Jetzt wird die Uhr am Ende
  nachgestellt — an einer Stelle, die auch beim Abbruch durch eine Taste
  läuft.

**Und etwas Unangenehmes über die eigene Arbeit.**

- Die Testsuite lief die ganze Zeit **ohne die C-Bibliothek** — also auf
  einem Weg, den der MiSTer nie geht. Die mitgelieferte `libdragend.so` ist
  die ARM-Fassung für das Gerät und lädt auf einem PC gar nicht. **Vier
  Tests** sind daran gescheitert, ohne dass am Frontend etwas falsch war, und
  sie haben es sogar wörtlich gesagt („ohne sie prüft dieser Test nichts") —
  nur hat niemand die Zeile als Befund gelesen. Der Prüfstand nimmt jetzt die
  zur Architektur passende Fassung. **Das ändert am Frontend nichts** und
  gehört hier nur deshalb hin, weil der vorige Build mit vier roten Tests
  ausgeliefert wurde.






---

## v4.7 — der Login-Prompt, große Kacheln, und was Messungen widerlegt haben

Achtzehn Builds seit v4.6. Was man davon merkt, in vier Zeilen:

- Der **Login-Prompt**, der seit Kernel 6.18 immer wieder ins Bild platzte,
  ist gefunden und weg — der Wächter hatte acht einzelne Bildpunkte
  angesehen statt ganzer Zeilen.
- Die **Rasteransicht** zeigt jetzt große Boxart: zehn Kacheln à 270×361
  statt einundzwanzig à 176×235.
- **Frontend beenden** landet nicht mehr blind auf der Konsole, sondern
  übergibt über MiSTers eigenen Befehlskanal — und sagt dir, was zu tun
  ist, falls auch das nicht greift.
- **Schneller** an mehreren Stellen, jede einzelne auf echter Hardware
  nachgemessen: Teilbilder um Faktor 3,3, Miniaturen als JPEG, zwei
  Rechenwege nach C.

Und eine Zeile Selbstkritik, weil sie dazugehört: mehrere dieser Builds
haben Fehler behoben, die ich zuvor selbst eingebaut hatte, weil ich auf
dem Entwicklungsrechner gemessen habe statt auf dem MiSTer. Die
Unterschiede sind dort keine Nuancen — der Bildspeicher des MiSTer ist
beim Lesen etwa hundertmal teurer als normaler Arbeitsspeicher. Der Bench
(`--bench`) misst deshalb inzwischen auch genau diese Stellen.

**Wichtig nach dem Update:** einmal „Miniaturen vorbereiten" laufen
lassen. Die großen Rasterkacheln haben eine neue Größe, und ohne
Vorbereitung lädt das Raster beim ersten Durchblättern nach.


**MiSTers Befehlstabelle löst zwei alte Rätsel auf einmal.**

Sie steht im Programm auf der Karte, und damit ist endlich belegt, was
MiSTer über seinen Befehlskanal annimmt: `fb_cmd`, `video_mode`,
`load_core`, `screenshot`, `scaled`, `volume`, `mute`, `unmute`. **Einen
`menu`-Befehl gibt es nicht** — das OSD lässt sich über diesen Weg also
gar nicht aufklappen. Damit ist geklärt, warum der Menüpunkt „OSD öffnen"
auf diesem Gerät nie zuverlässig sein konnte. `load_core` gibt es aber,
und damit lässt sich das Menü-Core laden — *das* ist MiSTers Menü. Genau so
kommt das Frontend seit langem aus einem laufenden Spiel zurück; es ist
kein neuer Mechanismus, sondern der vorhandene an einer zweiten Stelle.

**Beenden versucht jetzt diesen Weg.** Das Exit-Log zeigte dreimal
eingespeistes F12 und dreimal MiSTers Last bei 6–7 % — die
Tastatur-Einspeisung kommt nicht an, während F12 auf der Tastatur das Menü
sehr wohl öffnet. Nach den drei F12-Versuchen wird deshalb das Menü-Core
geladen und nachgesehen, ob MiSTers Last hochgeht. Kommt das Menü, ist
Schluss; kommt es nicht, bleibt der Hinweis auf der Konsole.

Ausdrücklich ein *Versuch*, keine Lösung mit Ansage: dass `load_core` auch
dann das Menü holt, wenn gar kein Spiel läuft, ist noch nicht gemessen — ich
hatte es schon behauptet und mich dabei auf eine Antwort gestützt, die sich
auf etwas anderes bezog. Schlechter als vorher kann es nicht werden, und
die Log-Zeilen sagen beim nächsten Mal, welcher Fall es war.

**Und „OSD öffnen" kann nicht mehr einfrieren.** Gemeldet: „hört die Musik
auf und das Frontend-Bild bleibt stehen, kein OSD kommt, dann hab ich auf
alle Tasten nacheinander gedrückt und plötzlich öffnet sich das OSD."

Dort stand ein `while True` **ohne jedes Zeitlimit**. Kommt das
eingespeiste F12 nicht an, gibt es kein OSD — und der Prozess wartet für
immer auf eine Rückkehrtaste, mit pausierter Musik und stehendem Bild. Das
„plötzlich" war die erste Taste, die zufällig als Rückkehr zählt. Jetzt
wird *vorher* gemessen, ob das OSD überhaupt kam: kam es nicht, ist das
Frontend sofort zurück und sagt, dass F12 auf der Tastatur hilft. Und die
Warteschleife selbst hat ein Zeitlimit, damit auch ohne Messsignal niemand
mehr festsitzt.

**Die großen Rasterkacheln sind jetzt der Standard** — auf Wunsch fest
übernommen. Bei 1080p sind das 10 Kacheln à 270×361, also 79 % der
Galerie-Größe. Zurück zum alten 7×3-Raster geht es mit
`touch /media/fat/frontend/raster_klein`. Nach dem Umstieg einmal
„Miniaturen vorbereiten" laufen lassen.

---

**Ich habe auf dem falschen Rechner gemessen — das wird hier korrigiert,
und der Bench misst es künftig auf dem Gerät.**

Build 209 hat den Bildwächter von acht Bildpunkten auf zwanzig ganze
Zeilen umgestellt. Die Kosten habe ich auf dem Entwicklungsrechner
ermittelt: 0,013 ms für 150 kB. Im Profillauf auf dem echten Gerät stand
dann **2 Millisekunden je Blick**, zweimal je Scrollschritt. Der
Unterschied ist nicht die CPU, sondern *welcher Speicher*: auf dem PC ist
das ein Feld im normalen Arbeitsspeicher, auf dem Gerät der Bildspeicher —
ungecacht, über den Bus, beim Lesen noch unangenehmer als beim Schreiben.

Abhilfe, ohne an der Erkennung zu sparen: je Blick werden nur vier der
zwanzig Proben angesehen, im Ringverfahren. Jede Probe ist nach fünf
Blicken dran — beim Scrollen also mehrmals pro Sekunde, und der Login-Gruß
steht ja, bis ihn jemand wegwischt. Aus 150 kB je Blick werden 30 kB.

Damit sich das nicht wiederholt, gibt es **Bench-Abschnitt F**: er liest
dieselbe Byte-Menge einmal aus dem Arbeitsspeicher und einmal aus dem
Bildspeicher, nennt den Faktor dazwischen und dann die Kosten eines echten
Wächter-Blicks. Die Zahl, an der ich mich verschätzt habe, kommt ab jetzt
vom Gerät.

**Das Raster kann große Kacheln zeigen.** Gewünscht war „die Boxart-Größe
wie die großen in der Galerie, vielleicht acht auf einen Schirm".
Nachgerechnet: die Rasterfläche ist bei 1080p 1652×741 Punkte, und von
342×456 passt darin nur *eine* Reihe. Bei zwei Reihen wird die Kachel
270×361 — 79 % der Galerie-Größe — und davon passen zehn hinein:

```
klein   7x3 = 21 Kacheln,  Cover 176x235
groß    5x2 = 10 Kacheln,  Cover 270x361      (Galerie: 342x456)
```

Also zehn statt der erhofften acht. Gerechnet wird wie hochkant seit Build
176: nicht die *Zahl* der Kacheln steht fest, sondern ihre *Größe*. Auf
720p werden es 180×241, auf der Röhre 53×71, hochkant 298×397.

Der Preis, ehrlich benannt: 270×361 ist eine neue Kastengröße, und der
Miniaturen-Speicher merkt sich die Größe. Beim ersten Einschalten einmal
„Miniaturen vorbereiten" laufen lassen. Standard aus:

```
touch /media/fat/frontend/raster_gross     # an
rm    /media/fat/frontend/raster_gross     # aus
```

**Die Galerie aus der Rasterkachel ist wieder weg** — Urteil am Fernseher:
„sieht blöd aus". Samt Hochskalierer und allen Verzweigungen; ein toter
Schalter ist schlimmer als keiner.

**Beim Beenden ist jetzt belegt, woran es liegt.** Dreimal eingespeistes
F12, dreimal MiSTer bei 6–7 % Last, dreimal „das OSD ist NICHT gekommen".
Das Messinstrument aus Build 166 arbeitet also korrekt — was nicht
funktioniert, ist die *Einspeisung*, während F12 auf der Tastatur das Menü
sehr wohl öffnet. Die richtige Abhilfe läuft über MiSTers eigenen
Befehlskanal, dessen Formate jetzt bekannt sind; welcher davon das Menü
holt, ist noch nicht belegt und wird deshalb nicht gebaut. Was dieser
Build tut: aus der Sackgasse wird eine Anleitung. Schlägt die Übergabe
endgültig fehl, steht auf der Konsole, dass F12 zu drücken ist.

---

**Der Bildwächter hat den Login-Prompt nie gefunden, weil er acht
einzelne Bildpunkte angesehen hat.**

Das ist die ganze Erklärung für ein Ärgernis, das sich über Builds 198
bis 208 gezogen hat. Der Wächter vergleicht seit Build 198 richtig — gegen
das, was wir zuletzt selbst geschrieben haben, weshalb er keine
Fehlalarme kennt. Er sah dabei nur *acht Bildpunkte* an. Ein ganz
weggeschaltetes Bild findet er damit sofort (beim Nutzer waren 15 von 15
Proben fremd). Echter Text besteht aber aus dünnen Strichen, und dass
einer von acht Punkten genau auf einem liegt, ist fast ausgeschlossen.

Jetzt sind die Proben **ganze Zeilen**: bis Bildzeile 96 alle acht Zeilen
— eine Konsolen-Textzeile ist sechzehn Bildpunkte hoch und kann also
nicht mehr hindurchpassen — und darunter gestreut über die ganze Höhe.
Statt 32 Byte werden 150 kB angesehen, 4800-mal so viel Bild, und ein
Blick kostet gemessen 0,013 ms. Der Test macht die Probe mit 200 Prompts
an zufälliger Stelle:

```
von 200 Prompts gefunden:  Zeilen-Wächter 200,  acht Punkte 0
```

**Ein Irrweg steht dokumentiert statt versteckt.** Ich hatte den Wächter
zuerst nach C geholt — 150 kB je Blick sehen teuer aus. Die Messung sagt
das Gegenteil: 0,0158 ms in C gegen 0,0126 ms in Python. Python ist sogar
minimal schneller, weil ein Schnittvergleich auf einem Bytefeld *bereits*
ein `memcmp` ist; der Python-Aufwand fällt je Probe an, nicht je Byte. Der
C-Teil ist deshalb wieder rausgeflogen, samt Bindungen und Rückfall — der
Wächter hat jetzt eine Fassung, die nicht auseinanderlaufen kann. Die
Zahlen stehen im Quelltext, damit das niemand erneut „optimiert".

**Was wirklich nach C gehörte,** sind die zwei Stellen, die Python je
*Bildpunkt* beziehungsweise je *Bildzeile* anfassen muss:

| | vorher | jetzt | |
|---|---|---|---|
| Fremdausgabe zählen | 0,813 ms | 0,027 ms | 31× |
| Bereich freiräumen (340×792) | 0,276 ms | 0,070 ms | 7× |

Das Zählen lief seit Build 208 auch mitten im Scrollen — 48 Zeilen mal 512
Spalten sind 24576 Vergleiche. Das Freiräumen ist der Posten, der im Log
als `bg=11` von 85 ms je Scrollschritt sichtbar war. Beide behalten ihre
Python-Fassung als Rückfall und als bitgenaues Vergleichsmaß im Test.

`libdragend` ist damit Fassung 4. Eine alte Datei meldet 3, wird mit einer
Log-Zeile verworfen, und es wird in Python gerechnet — ein halbes Update
macht also nichts kaputt, nur langsamer.

---

**Der Login-Prompt beim gehaltenen Scrollen: die Wache war an genau dieser
Stelle nie aktiv.**

Gemeldet: „ploppt das Login-Prompt wieder auf, wenn ich zum Beispiel in der
Listenansicht nach unten scrolle bei gedrückter Taste."

Die Ursache stand seit Build 199 halb in unserem eigenen Kommentar: der
Leerlaufzweig der Hauptschleife wird übersprungen, solange eine Eingabe
anliegt. Beim *Halten* einer Taste war deshalb alles abwesend, was gegen
den Prompt gebaut wurde. Build 199 hat daraus nur **eine** Abhilfe
mitgenommen — das regelmäßige Neuschreiben der obersten Zeilen. Und genau
das reicht nicht: der Gruß des Login-Prozesses ist höher als diese Zeilen.
Die Wache, die den Prompt *überall* im Bild erkennt, blieb im
Leerlaufzweig stehen. Sie läuft jetzt auch einmal je Aktion, mit ihrer
eigenen Drosselung — gemessen eine Prüfung bei zwanzig Tastenschritten in
einer Sekunde.

Der empfindliche Punkt dabei ist die *Reihenfolge*, und die ist im
Quelltext begründet: die Wache vergleicht Schirm und gezeichnetes Bild,
und beim Scrollen laufen die beiden außerhalb des kopierten Streifens
auseinander. Vorher geprüft, hätte sie eigene, noch nicht kopierte Zeilen
für fremden Text gehalten — das wäre das Flackern aus Build 151 zurück.
Sie prüft deshalb *nach* dem Auffrischen der Kopfzeilen, die genau den
Bereich frisch kopiert haben, den sie ansieht.

**Und der F9-Befund ist eindeutig: es ist nicht unser Bild.** Fünfmal
„0 Bildpunkte, Schwelle 120". Unser Bild steht unversehrt in unserem
Bildspeicher; MiSTer zeigt schlicht eine andere Anzeige-Ebene. Damit ist
klar, dass weder die Wache noch der Bildwächter das je reparieren können —
beide kennen nur unseren eigenen Speicher. Das Umschalten muss über MiSTer
selbst laufen. Welcher Weg das ist, wird nicht geraten; dafür sind
Messungen auf dem Gerät unterwegs.

---

**Das F9 auf der Tastatur wird jetzt bemerkt — und der Attract-Modus hört
auf, sich eigene Miniaturen zu bauen.**

Gemeldet: „mit F12 komme ich ins OSD, das klappt noch, drücke ich dann F9,
sollte das Frontend ja wieder kommen, ich bleibe dann aber im Login-Prompt
hängen" — und dazu der entscheidende Nachtrag: „drücke ich im Login-Prompt
nochmal F12, bin ich wieder im Frontend."

Der eigene Quelltext sagt zu diesem Prompt seit Build 150, was ihn
auslöst: *jedes* F9 weckt den Login-Prozess auf tty1, und der schreibt
sein „Welcome to MiSTer … login:" in denselben Bildspeicher, in den das
Frontend zeichnet. Für sein **eigenes** F9 beim Start räumt das Frontend
darum hinterher auf. Beim F9 **des Nutzers** ist das nie passiert, und
zwar aus einem einfachen Grund: F9 ist in der Tastenbelegung absichtlich
auf *nichts* gelegt, weil MiSTer die Taste für den Anzeigewechsel braucht
— der Tastendruck erreichte das Frontend also überhaupt nicht. Jetzt wird
er vermerkt (wirkungslos bleibt er weiterhin) und dasselbe, seit Build 150
bewährte Aufräumen angesetzt.

Ob das reicht, ist damit noch nicht behauptet. In seinem Log steht während
der ganzen F12/F9-Folge **keine einzige** Zeile — weder von der
Dauerwache noch vom Bildwächter. Das lässt zwei Möglichkeiten offen: der
Prompt steht in unserem Bildspeicher und die Wache zählt zu wenige
Bildpunkte, oder er steht dort *gar nicht* und MiSTer zeigt schlicht eine
andere Anzeige-Ebene, unser Bild unversehrt darunter. Dass F12 zurück ins
Frontend führt statt ins OSD, passt zur zweiten. Bei genau dieser
Fehlersuche bin ich in den Builds 146–149 viermal falsch abgebogen, weil
aus einer Beobachtung eine Ursache wurde — deshalb wird hier nicht
geraten: der Build schreibt die Zahl der gefundenen Bildpunkte ins Log.
Die nächste Log-Zeile entscheidet.

**Der Attract-Modus nimmt den Cover-Kasten der Spieleliste.** Bisher hatte
er einen eigenen — 50 % der Breite, 72 % der Höhe, bei 1080p also
960×777. Der Miniaturen-Cache trägt die Kastengröße im Schlüssel, und
deshalb hat der Bildschirmschoner für *jedes* gezeigte Spiel eine eigene,
sonst von niemandem gebrauchte Miniatur gerechnet und auf die Karte
geschrieben. Die Cover-Spalte liefert 697×771 — fast dieselbe Höhe, und
die begrenzt bei hochkantigen Covern ohnehin. Sichtbar ändert sich also
kaum etwas, nur greift er ab jetzt auf die Datei, die die Spieleliste
längst hat. Die Abzeichen der Hauptseite bleiben unverändert.

**Neu zum Ausprobieren: die Galerie aus der Raster-Kachel.** Galerie-groß
(342×456) und Raster-Kachel (176×235) liegen nah beieinander, Faktor 1,94.
Nimmt die Galerie dieselbe Kachel und zeigt sie nur größer, fällt je Spiel
eine zweite Datei weg und der Wechsel zwischen beiden Ansichten ist sofort
warm. Der Preis ist Nearest-Neighbor-Vergrößerung, also ein sichtbar
gröberes Bild — das kann nur das Auge am Fernseher entscheiden. Deshalb
ein Schalter, standardmäßig **aus**:

```
touch /media/fat/frontend/galerie_kachelquelle     # an
rm    /media/fat/frontend/galerie_kachelquelle     # aus
```

Ohne die Datei ist alles Zeile für Zeile der Stand von Build 206.

---

**Ein halb eingespieltes Update lässt das Frontend nicht mehr mit einem
Traceback stehen — und der Fehler lag an meiner Auslieferung.**

Bei einem Freund des Nutzers startete nach einem Update gar nichts mehr:

```
Traceback (most recent call last):
  File "/media/fat/frontend/frontend.py", line 218, in <module>
    from fe.settings import (
ImportError: cannot import name 'artbox_aufschub_aus' from 'fe.settings'
FEHLER: Frontend startet auch im zweiten Versuch sofort wieder ab.
```

Seine `frontend.py` kannte den Namen, seine `fe/settings.py` nicht. Der
Name kam in einem Build in **beide** Dateien gleichzeitig — und meine
Build-Pakete enthalten immer nur die *geänderten* Dateien. Ein Paket, das
`frontend.py` mitbringt, aber die passende `fe/settings.py` nicht, ist
deshalb nur dann sicher, wenn alle vorherigen Pakete schon drauf sind.
Wer eines überspringt, bekommt genau diesen Absturz. Das ist kein
Bedienfehler, das ist ein Verpackungsfehler von mir.

Zwei Dinge dagegen:

**Der Absturz ist jetzt eine Anleitung.** Es gab bereits eine Vorsorge —
das Frontend vergleicht seit längerem namentlich, ob die Teile
zusammenpassen, und druckt statt eines Absturzes, was zu tun ist. Sie kam
nur nie zum Zug: ein fehlender Name in einem Import stirbt, *bevor* eine
einzige Zeile eigener Code läuft. Ein Haken ganz oben in der Datei — vor
dem ersten Import — schließt die Lücke jetzt für alle über dreißig
Importe auf einmal:

```
ACHTUNG: frontend.py und das fe/-Paket passen nicht zusammen.
  cannot import name 'artbox_aufschub_aus' from 'fe.settings'
Behoben mit einer VOLLSTÄNDIGEN Installation:
  /media/fat/Scripts/Frontend_Update.sh
```

Wichtig dabei: **alles andere wird unverändert durchgereicht.** Ein
echter Programmfehler sieht weiterhin aus wie einer — ein Haken, der zu
viel abfängt, macht aus jedem künftigen Fehler eine irreführende
Update-Anleitung, und dann sucht man tagelang an der falschen Stelle.
Geprüft wird das an einem echten, nachgebauten Mischstand auf der Platte,
nicht nur an der Funktion.

**Und es gibt wieder ein vollständiges Paket.** Für alle, die nicht jeden
Zwischenstand mitgemacht haben, ist ein Komplettpaket der sichere Weg —
inkrementelle Pakete sind etwas für den, der lückenlos dabei war.

**Die Umstellung auf JPEG hat das Scrollen erst langsamer gemacht — das
ist behoben, und der Fehler war meiner.**

Nach der Umstellung waren die gemessenen Zahlen schlechter als davor:

```
vorher   down/S1  69x Mittel  72 ms (max  192)
danach   down/S1   7x Mittel 492 ms (max  750)
         right/S1 59x Mittel 265 ms (max 1831)
```

Das Lesen war nicht das Problem, das Nachziehen war es. Alte Miniaturen
werden beim Lesen auf JPEG umgeschrieben, und das geht über eine
Hilfsfunktion, die dafür **einen eigenen Thread pro Aufruf** startet.
In deren Beschreibung steht ausdrücklich, dass das nur deshalb in Ordnung
ist, weil es „nur beim Wegschreiben einer frisch berechneten Miniatur
passiert (nicht bei jedem Scrollschritt)". Genau diese Annahme hatte ich
gebrochen: beim Scrollen wurde je Schritt ein Thread gestartet, der
packte, JPEG kodierte und dabei auch noch einen Verzeichnisdurchlauf
mitzog. Auf zwei schwachen Kernen konkurriert das direkt mit dem
Zeichnen — und um dieselbe SD-Karte.

Ich hatte diese Beschreibung beim Bauen gelesen und bin trotzdem
hineingelaufen.

Jetzt zwei Bremsen:

- **Nur im Stillstand.** Während geblättert wird, wird nichts
  umgeschrieben. Umgezogen wird, wenn ohnehin Luft ist.
- **Höchstens eine Umstellung alle zwei Sekunden.** Auch im Leerlauf soll
  daraus kein Sturm werden.

Bei 97.000 Einträgen wird die Umstellung damit eine Sache der normalen
Nutzung über Wochen — und soll sich gar nicht anfühlen. Das Lesen selbst
ist unverändert schnell; gedrosselt ist nur das Umschreiben.

**Der Bench beantwortet jetzt eine Frage, die auf dem Entwicklungsrechner
schon einmal falsch beantwortet wurde.**

Rollt beim Scrollen im Hauptmenü die Liste weiter, gibt es keinen
leichten Zeichenweg — es läuft ein voller Aufbau, im Log des Nutzers
`rows=77`. Die naheliegende Abhilfe wäre, den gezeichneten Block im
Speicher um eine Zeile zu verschieben und nur die neue Zeile zu setzen.

Genau das gab es schon (Build 96) und wurde wieder entfernt (Build 102),
mit Messwerten — und mit einem Kommentar, der ausdrücklich dasteht,
„damit niemand (ich eingeschlossen) dieselbe Idee in einem halben Jahr
ein zweites Mal baut". Ich hatte sie gerade zum zweiten Mal
vorgeschlagen; der Kommentar hat funktioniert.

Eine Zahl darin ist aber verdächtig: **2,04 ms für einen vollen
Seitenaufbau**. Auf dem Gerät des Nutzers kostet derselbe Aufbau 77 ms.
Das sind Werte vom Entwicklungsrechner, und dort ist das Verhältnis
zwischen Schrift setzen und Speicher schieben umgekehrt — Text ist
billig, die Kopie teuer. Auf einer schwachen ARM-CPU ist es andersherum.
Nachgerechnet mit den Gerätezahlen: **8,5 ms Kopie + 13 ms für zwei
Zeilen gegen 77 ms** voller Aufbau.

Gebaut wurde deshalb *nicht* das Feature, sondern die Messung: ein neuer
Bench-Abschnitt misst die drei **Zutaten** einzeln — voller Aufbau,
Verschieben des Blocks, eine Kategoriezeile — und schreibt die Rechnung
offen hin. Jede Einzelmessung ist so simpel, dass an ihrer Richtigkeit
nichts zu deuten ist, und die Entscheidung folgt aus der Rechnung statt
aus einer Vermutung. Gezeichnet wird nur in den Puffer, nie auf den
Schirm.

Lokal reproduziert er Build 102 sauber: das Verschieben allein kostet
0,855 ms und ist damit **teurer als der ganze volle Aufbau** (0,479 ms).
Ob das auf dem Gerät auch gilt, sagt der Bench dort.

*Zwei Fehler, die mir dabei selbst unterlaufen sind, beide von Tests
gefangen:* der Abschnitt hat bei stehender Uhr — der Prüfstand friert sie
ein — aus drei Nullen ein „es lohnt NICHT" gemacht, also ein Urteil aus
fehlenden Daten. Und er hat bei einem unlesbaren Kategoriebaum
*abgebrochen*, statt „übersprungen" zu melden und den Rest des Berichts
stehen zu lassen. Beides ist behoben und beides jetzt geprüft.

**Ordner öffnen war zu 80 % das Cover — und die Ursache war eine
Annahme, die richtig gemessen und dann still falsch geworden ist.**

Gemeldet wurde ein Hänger beim Öffnen: im Mittel 476 ms, im Spitzenfall
1769 ms. Ein Profillauf auf dem Gerät hat es aufgeschlüsselt:

```
_draw_page_items_impl        241 ms
  draw_art_panel             197 ms
    get_scaled               136 ms
      _thumb_cache_get       132 ms
        3x read()             66 ms   ← von der Karte lesen
        zlib.decompress       64 ms   ← auspacken
```

Das ganze Öffnen war das Cover. Und im Kommentar an genau dieser Stelle
stand die Annahme, die das jahrelang gedeckt hat: eine Cache-Datei zu
lesen kostet **5,9 ms**. Das war damals korrekt gemessen — bei der
damaligen Kastengröße. Auf 1080p sind daraus 132 ms geworden,
zweiundzwanzigmal so viel. Niemand hat etwas falsch gemacht; die Zahl
ist mit den größeren Covern aus dem Rahmen gewachsen, und weil sie als
Kommentar dastand, hat sie weiter beruhigt.

Miniaturen werden deshalb jetzt als **JPEG** abgelegt statt als
zlib-gepackte Rohpixel — die Datei wird dreimal kleiner, und das
Auspacken macht libjpeg in C statt zlib gegen einen halben Megabyte.

Drei Dinge, die dabei absichtlich *nicht* pauschal gemacht werden, alle
drei an echtem Material nachgemessen (320×420, HDMI-Kastengröße):

| Bild | roh | zlib | JPEG 97 |
|---|---|---|---|
| echtes Abzeichen `3DO.art` | 525 KB | 111 KB / 2,06 ms | 38 KB / 1,3 ms |
| glattes, gemaltes Cover | 525 KB | 42 KB / 1,03 ms | 12 KB / 1,0 ms |
| Rauschen (Grenzfall) | 525 KB | 363 KB / 3,10 ms | 360 KB / 3,3 ms |

- **Kleine Bilder bleiben verlustfrei.** Unter 64 KB gepackt gibt es
  nichts zu holen.
- **Und es muss sich lohnen.** Die letzte Zeile ist der Grund: dort
  spart JPEG 3 von 363 KB und packt langsamer aus. Wer nicht mindestens
  die Hälfte spart, bleibt bei der verlustfreien Fassung. Beide Größen
  liegen beim Schreiben ohnehin vor, die Entscheidung ist gratis.
- **Güte 97, nicht 92.** Gemessen an den eigenen Abzeichen, weil die das
  Schwerste sind, was hier durch JPEG geht — große Flächen, harte Kanten,
  Schrift. Bei 92 stehen einzelne Randpunkte um bis zu 31 von 255
  daneben, ein schwacher Ring, den man finden *kann*. Bei 97 sind es
  höchstens 12 und im Mittel 0,37 — unterhalb von allem, was ein
  Bildschirm zeigt. Kostet 14 KB je Bild und ist es wert.

**Nichts muss neu aufgebaut werden.** Beide Formate stehen in derselben
Datei, der Kopf entscheidet — wie schon bei der Marke „Original passt".
Alte Dateien werden weiter gelesen, und wer groß genug ist, wird
*nebenher* als JPEG nachgezogen. Jeder Eintrag zahlt die alten Kosten
genau einmal; bei 97.000 Einträgen ist das der Unterschied zwischen
einem Umstellungslauf und gar keinem.

Dazu: die Cache-Datei wird in **einem** `read()` gelesen statt in drei —
im Profil standen dafür 66 ms.

*Was ich mir dabei selbst korrigieren musste:* mein erstes Testbild war
ein erzeugtes Muster, also hochfrequentes Rauschen — der schlechteste
Fall für JPEG, und etwas, das kein Cover der Welt so aussieht. Der Test
meldete „Faktor 1,1", und das wäre die falsche Schlussfolgerung aus
einem falschen Bild gewesen. Mit echtem Material aus dem Repo sind es
111 → 38 KB. Und meine erste Schätzung „132 → 30 ms" war zu optimistisch;
realistisch ist etwa die Hälfte, nicht ein Viertel.

**Eine Symlink-Schleife kann das Einlesen nicht mehr aufhängen.** Der
Anstoß kam von Degauss, das in v0.9.0 dasselbe reparieren musste — beim
Nachsehen stand es bei uns aber schlechter, und *das* ist der Fund. Die
obere Ebene war seit langem abgesichert, der rekursive Abstieg gar
nicht: `os.path.isdir()` folgt Symlinks, also genügte ein Link, der nach
oben zeigt (`games/SNES/alles -> /media/fat/games`), und das Einlesen
kreiste, bis Python abbricht. Bei 97.000 Einträgen trifft das den
unangenehmsten Moment überhaupt — den Neuaufbau der Bibliothek.

Geprüft wird jetzt gegen die **Vorfahren** des aktuellen Weges, nicht
gegen „schon mal gesehen". Der Unterschied ist wichtig: eine globale
Merkliste hätte auch einen Ordner übersprungen, der völlig legitim ein
zweites Mal auftaucht (zwei Links auf dieselbe Sammlung), und damit
still Spiele verschluckt. Nur was auf dem Weg *hierher* schon vorkam,
ist eine Schleife. Dazu ein Tiefendeckel von 24 als zweiter Gürtel, und
jede übersprungene Stelle steht einmal im Log — ein stillschweigend
weggelassener Ordner ist genau die Sorte Fehler, die man erst bemerkt,
wenn Spiele fehlen.

Und es kostet praktisch nichts: `realpath()` ist teuer, wird aber nur
für **Symlinks** gebraucht. Ein gewöhnlicher Unterordner kann keine
Schleife bauen, sein echter Pfad ist der des Vaters plus Name — das
rechnet man ohne einen einzigen Systemaufruf aus. Im Test: bei zwölf
Unterordnern genau **ein** `realpath()`, für den Startordner. Geprüft
wird das an einer echten Schleife auf der Platte, nicht an einer
Attrappe.

**Und im Systemmenü kam er trotzdem noch — weil es zwei verschiedene
Fehlerbilder sind.** Gemeldet: „in System und dann in Anzeigen/Sounds
wenn ich dort runterscrolle kommt der login prompt noch". Der Unterschied
ist nachgemessen:

- **Übernahme** — MiSTer richtet den Bildspeicher neu ein, *jeder*
  Bildpunkt ändert sich. Das findet der Bildwächter mit acht Proben
  sicher.
- **Text** — der Login-Gruß sind nur ein paar Zeilen Buchstaben. Im
  Versuch mit 2669 gesetzten Bildpunkten in den Zeilen 8–48 hat der
  Wächter ihn **nicht** gefunden: die Proben liegen zwischen den
  Glyphen. Mit mehr Proben ist das nicht zu heilen, es bliebe Glück.

Für den Textfall gibt es die richtige Abhilfe schon lange — die obersten
Zeilen einfach regelmäßig neu hinschreiben, ohne irgendetwas zu erkennen.
Sie stand nur im Leerlaufzweig der Hauptschleife, und der wird
übersprungen, sobald eine Eingabe anliegt. Genau deshalb kam der Gruß
beim **gehaltenen** Scrollen durch und sonst nie. Jetzt läuft sie
zusätzlich einmal je Aktion; gedrosselt wird in der Methode selbst
(viermal je Sekunde, 0,8 ms), häufigeres Rufen kostet also nichts.

*Der Test dazu* prüft jetzt die echte Blockausdehnung im Quelltext statt
„nächstes `if` davor plus Einrückung" — die alte Technik hätte den neuen
Aufruf fälschlich als Teil eines längst beendeten Zweigs gemeldet. Damit
hat diese eine Prüfung dreimal nachgeschärft werden müssen, jedes Mal aus
demselben Grund: sie hat geschätzt, wo sie rechnen konnte.

**Der Login-Gruß beim Scrollen ist ein viel älterer Fehler, als er
aussah — und jetzt holt sich das Frontend sein Bild selbst zurück.**

Gemeldet wurde er, nachdem das Hauptmenü schneller geworden war. Ich
hatte drei Erklärungen, alle falsch; entschieden hat es wieder eine
Messung. Der Rückleser prüft nach jedem Bild, ob im Bildspeicher noch
steht, was wir hingeschrieben haben:

```
RUECKLESER: nach 26.9 s steht in 15 von 15 Proben-Zeilen fremder
Inhalt (Zeilen 0,16,32,48,90,180,270,360) - 2 Treffer bei 109 Bildern
```

**Fünfzehn von fünfzehn.** Das ist etwas völlig anderes als der Befund,
der zur letzten Reparatur geführt hat (damals zwei Zeilen oben,
dauernd). Hier schreibt niemand Text hinein — hier ist das *ganze Bild*
nicht mehr unseres: selten, rund einmal je hundert Bilder, aber
vollständig. Und wer `fb_terminal=1` gesetzt hat, bei dem ist die
**Linux-Konsole die Ebene darunter** — deshalb erscheint ausgerechnet
der Login-Gruß und nicht irgendetwas anderes.

> *Nachtrag, nachgemessen:* als Ursache stand hier zuerst, MiSTer richte
> den Bildspeicher im Betrieb mehrfach neu ein. **Das war falsch.** Das
> `dmesg` des Nutzers zeigt `MiSTer_fb`-Zeilen nur beim Start (12:47:54
> und 12:48:12), die Reparaturen des Wächters lagen aber bei 12:49:09,
> 12:50:39 und 12:59:34 — keine einzige Neueinrichtung dazu. Die
> wirkliche Ursache steht in der `inittab`:
> `console::respawn:/sbin/agetty --nohostname -L tty1 linux`. Der agetty
> auf `tty1` hatte im Log PID **2725**, der auf `console` 1126 — er war
> also neu gestartet, und ein frischer agetty **löscht den Schirm** und
> schreibt seinen Gruß hin. Ein Konsolen-Löschen erzeugt keine
> `dmesg`-Zeile, erklärt aber genau, warum alle fünfzehn Proben-Zeilen
> fremd waren. Der Wächter ist trotzdem richtig und nützlich — er holt
> das Bild zurück, egal wer es weggenommen hat. Nur die Begründung war
> geraten, und das gehört korrigiert und nicht stillschweigend ersetzt.

Damit ist auch klar, was die Beschleunigung des Hauptmenüs wirklich
getan hat: vorher kopierte jeder Scrollschritt 804 von 1080 Bildzeilen,
ein solcher Ausfall war binnen 80 ms zu drei Vierteln übermalt und fiel
nicht auf. Jetzt sind es 120 Zeilen, und der Rest bleibt stehen, solange
die Taste gehalten wird. **Der Fehler ist älter**, er war nur zufällig
verdeckt — mit 85 ms pro Scrollschritt als unfreiwilligem Preis dafür.

Die Abhilfe nutzt aus, dass unser Puffer dabei unversehrt bleibt: es ist
nichts neu zu zeichnen, es muss nur einmal alles kopiert werden. Nach
jedem Teil-Flip werden acht Bildpunkte auf dem Schirm gegen **das
zuletzt Geschriebene** geprüft — nicht gegen den Puffer, denn der läuft
dem Schirm völlig legitim voraus, und dieser Unterschied ist der ganze
Grund, warum es keine Fehlalarme gibt. Stimmt ein Punkt nicht, war ein
Fremder am Werk, und das Bild wird komplett neu kopiert. Zwei der acht
Punkte liegen in den obersten Zeilen, wo der Gruß steht.

Gemessen kostet die Prüfung **0,001 ms pro Bild** (0,8 %). Die Reparatur
selbst fällt nur im Ernstfall an und ist auf fünfmal je Sekunde
begrenzt — wischt MiSTer dauerhaft, wäre sonst jeder Teil-Flip eine
Vollbildkopie und das Scrollen langsamer als vorher. Wie oft es
passiert, steht als `BILDWAECHTER:` im Log.

Damit kann die Notbremse wieder weg:

```
rm /media/fat/frontend/artbox_aufschub_aus
```

Abschalten lässt sich der Wächter mit
`touch /media/fat/frontend/bildwaechter_aus`.

**Die Latenz-Bilanz nennt jetzt jede Aktion einzeln.** Vorher stand dort
ein Mittel über alles:

```
LATENZ-BILANZ: 125 Schritte, Mittel 126 ms, schlechtester 205 ms (right)
```

Diese Zeile beantwortet keine Frage. Sie mischt einen 6-ms-Scrollschritt
im Hauptmenü mit einem Ansichtswechsel, der eine ganze Seite neu baut —
und deshalb ließ sich an ihr nicht einmal ablesen, ob die Änderung
darunter überhaupt gegriffen hat. Jetzt kommt eine zweite Zeile dazu:

```
LATENZ-JE-AKTION: ok/S1 1x Mittel 400 (max 400) | right/S1 4x Mittel 150
                  (max 150) | down/S0 21x Mittel 6 (max 6)
```

Je Aktion **und Seite**, weil dieselbe Taste auf der Hauptseite und in
der Spieleliste völlig verschiedene Arbeit auslöst. Sortiert nach dem
Mittel, nicht nach dem Ausreißer — gesucht ist, was ständig zu lange
braucht. Die Schrittzahl steht dabei, denn ein Mittel über zwei Schritte
ist keine Aussage.

Das ist heute die vierte Messung, die ich nachschärfen musste, und alle
vier hatten dieselbe Ursache: sie fassten zusammen, was man einzeln
braucht.

**Dazu ein einzelner Schalter für den Aufschub darunter.** Gemeldet
wurde, dass beim gehaltenen Scrollen wieder der Login-Gruß aufblitzt.
Ob das am Aufschub hängt, ließe sich mit „Cover sofort" nicht messen —
der schaltet zwei Dinge gleichzeitig um. Deshalb:

```
touch /media/fat/frontend/artbox_aufschub_aus
```

Damit steht im Hauptmenü wieder genau das Verhalten vor der Änderung,
und nichts sonst. Ohne die Datei bleibt es beim Aufschub.

**Das Hauptmenü scrollt jetzt deutlich flüssiger — und dieselbe Zeile,
die das gemessen hat, hat einen Plan von mir beerdigt.** Das
Messwerkzeug aus v4.6 hat im Hauptmenü achtmal hintereinander bei
gehaltener Richtungstaste das hier geliefert:

```
RUCKLER: 85 ms busy (zeichnen=82 rest=3
         | davon bg=11 rows=4 art=17 flip=50)
```

`rest=3` heißt: es wird nicht gewartet, nicht gerechnet und nicht
verwaltet — es wird gemalt. Damit war die geplante Entkopplung von
Eingabe und Zeichnen erledigt, **bevor** sie gebaut wurde. Sie hätte
hier nichts gebracht.

Die Aufteilung zeigt, dass alle drei großen Posten *eine* Ursache
haben: die Logo-Spalte rechts. Sie wird bei jedem einzelnen
Scrollschritt freigeräumt (11 ms) und neu gezeichnet (17 ms) — und weil
der Bildspeicher nur in ganzen Bildzeilen kopiert werden kann, muss der
kopierte Streifen alles zwischen den zwei geänderten Textzeilen links
und der Spalte rechts umfassen. Aus 120 Bildzeilen werden so 804, und
diese Kopie ist zu groß, um noch in einen Bildwechsel zu passen: sie
wartet auf den nächsten (50 ms). Die zwei Zeilen, um die es beim
Scrollen überhaupt geht, kosten 4 ms.

Bei **gehaltener** Taste bleibt das Logo deshalb jetzt stehen und wird
nachgezogen, sobald der Cursor stehenbleibt — genau so macht es die
Spieleliste seit Build 96. Der kopierte Streifen schrumpft damit von
804 auf 120 Bildzeilen und fällt unter die Grenze, ab der auf den
Bildwechsel gar nicht mehr gewartet werden muss. Ein **einzelner**
Tastendruck ist nicht betroffen: dort steht das Logo sofort da, wie
bisher. Wer „Cover sofort" eingeschaltet hat, behält ebenfalls das alte
Verhalten.

*Was dabei fast schiefging:* der schnelle Seitenaufbau räumt die
Logo-Spalte nicht frei — er darf das, weil alle Abzeichen exakt gleich
groß sind und das neue das alte vollständig abdeckt. Nur gilt das nicht
für eine Kategorie **ohne** Abzeichen: dort steht statt eines Bildes
ein schmalerer Platzhalter, und der Rand der alten Karte wäre
stehengeblieben. Bisher konnte das nicht passieren, weil das
Freiräumen bei jedem Schritt lief. Der Test rechnet nach: 58 131
Bildpunkte hätten falsch gestanden.

---

## v4.6 — Kernel 6.18, und sechs Erklärungen, die eine Messung überlebt haben

Ein Release, in dem fast nichts geraten wurde. Der Kernel-Sprung auf
6.18 hat drei Fehler ans Licht geholt, ein gemeldetes Zucken hat sechs
Erklärungen verbraucht, bis die richtige übrig blieb, und zwei der
gefundenen Fehler standen seit Monaten im eigenen Quelltext — sichtbar
geworden sind sie erst, als jemand nachgemessen hat.


**Der Login-Gruß, der beim Scrollen aufblitzt, ist weg — und diesmal
weiß ich auch, warum.** Gemeldet nach dem Kernel-Update: nach 50–60
Sekunden blitzt kurz der Login-Gruß durch, danach unregelmäßig immer
wieder. Drei Verdachtsrunden gingen an die falsche Stelle. Entschieden
hat es eine Messung — das Frontend prüft auf Wunsch nach jedem Bild,
ob im Bildspeicher noch steht, was es hingeschrieben hat:

```
RUECKLESER: nach 104.6 s steht in 2 von 7 Proben-Zeilen fremder
Inhalt (Zeilen 0,32) - 10 Treffer bei 21 Bildern
```

Zehn Treffer bei einundzwanzig Bildern, **ausschließlich in den
Zeilen 0 und 32** — die übrigen fünf Proben blieben sauber. Es
schreibt also jemand hinein, aber nur ganz oben: die Textkonsole, die
MiSTer selbst darstellt. Unsere eigene Konsolen-Mechanik ist damit
entlastet, sie kam auch abgeschaltet.

Die Abhilfe ist die einfachste denkbare: die obersten 64 Bildzeilen
werden viermal je Sekunde einfach wieder hingeschrieben. Das sind auf
1080p 491 KB, rund 0,8 ms — und es hängt **nicht** am Mechanik-
Schalter, denn die Ursache liegt nicht bei uns.

**Und dann habe ich aufgehört, Pfad für Pfad nachzurüsten.** Erst
fehlte die Hauptseite, dann Raster und Galerie — jedes Mal stand der
Rest auf der vollen Zeit, jedes Mal kam ein weiterer vermessener Pfad
dazu. Dabei gibt es eine Stelle, durch die **alle** Zeichenwege laufen,
und dort wurde ohnehin schon gemessen. Die Zeile hat jetzt
`zeichnen=` als Oberposten — vollständig, egal welche Ansicht — und
die Einzelposten sind dessen Aufteilung. Damit beantwortet eine
einzige Zeile die Frage, um die es geht: steckt die Zeit überhaupt im
Zeichnen, oder außerhalb?

**Und sie hat sofort die nächste Lücke gefunden — im Hauptmenü.** Mit
dem neuen Rest-Posten stand im Log elfmal hintereinander
`82 ms busy (bg=0 restore=0 rows=0 art=0 flip=0 rest=82)`: der
gesamte Aufwand unbekannt. Die Hauptseite war als einzige überhaupt
nicht vermessen — weder ihr schneller Navigationspfad noch ihr voller
Aufbau. Genau dafür ist der Rest da: er meldet die Lücke selbst, statt
sie hinter plausiblen Zahlen zu verstecken. Beide Pfade zählen jetzt
mit.

**Die Aufschlüsselung der Ruckler stimmte nicht — ausgerechnet dort,
wo gescrollt wird.** Im Log stand vierzehnmal hintereinander
`202 ms busy (… bg=20 restore=6 rows=36 art=0 flip=22)`. Die genannten
Posten ergeben zusammen 85 ms; wo die übrigen 117 waren, stand
nirgends. Und drei der Zahlen waren in allen vierzehn Zeilen
buchstabengleich, während die gemessene Zeit schwankte — sie wurden nur
beim vollen Seitenaufbau gesetzt und auf dem schnellen Pfad als Altlast
weitergeschrieben. Die Zeile sah plausibel aus und hat prompt an die
falsche Stelle geführt. Jetzt gehen alle Posten vor jeder Aktion auf
null, der schnelle Pfad trägt seine eigenen ein, und die Zeile weist
einen **Rest** aus: ist der groß, sagt das Werkzeug es selbst.

**Das Frontend misst jetzt, was man tatsächlich spürt.** Es gab zwei
Zahlen — wie lange ein Zeichenvorgang dauert und wie lange
Verarbeitung plus Zeichnen zusammen brauchen. Keine davon beantwortet
die Frage, um die es geht: *Taste gedrückt — wann steht das Bild?* Die
steht jetzt im Log, samt einer Bilanz alle 30 Sekunden, auch wenn
nichts auffällig war. Bei einer **gehaltenen** Taste zählt dabei der
Fälligkeitstermin der Wiederholung, nicht der Augenblick: man drückt
dort nicht neu, man hält — und was man spürt, ist der Abstand zwischen
zwei Schritten. Das ist die Vorarbeit für das Entkoppeln von Eingabe
und Zeichnen; der Umbau folgt, gezielt nach diesen Zahlen statt nach
einer Vermutung.

**Auch die Cover aus der `gamelist.xml` werden benutzt.** Dort stehen
nicht nur Jahr und Genre, sondern auch die Bildpfade — und die zeigen
auf Dateien, die Skraper bereits heruntergeladen **und über die
Prüfsumme der ROM-Datei zugeordnet** hat. Genau daran arbeitet unser
unscharfer Namensvergleich seit jeher; für ein gepflegtes Verzeichnis
entfällt er damit komplett. Die Rangfolge bleibt: eigenes Artwork
gewinnt, dann die `gamelist.xml`, dann die fremde Datenbank. Zeigt ein
Eintrag ins Leere, wird er übergangen statt für ein Cover gehalten.

**`gamelist.xml` wird mitgelesen.** Wer sein ROM-Verzeichnis mit
Skraper, ScreenScraper oder einem ähnlichen Werkzeug gepflegt hat, hat
dort eine `gamelist.xml` im EmulationStation-Format liegen — mit Jahr,
Genre, Spielerzahl, Hersteller und einer Beschreibung. Genau das, was
das Frontend sonst über die eigene Tabelle und die fremde Datenbank
zusammensucht. Liegt sie da, wird sie benutzt; liegt sie nicht da,
ändert sich nichts. Kein Werkzeug, kein Download, kein Vorbereiten.
Die Rangfolge ist mit Absicht so: eigene Daten schlagen die
`gamelist.xml`, die schlägt die fremde Datenbank — und gefüllt werden
nur Lücken, ersetzt wird nie. Gelesen wird die Datei häppchenweise;
eine Liste mit 10.000 Einträgen ist schnell 20 MB groß, und die gehört
auf einem Gerät mit 1 GB RAM nicht am Stück in den Speicher.
Abschalten geht mit `touch /media/fat/frontend/gamelist_aus`.

**Der Bench kennt jetzt drei Zustände statt zwei.** Zwischen „kalt"
(die Miniatur muss erst gerechnet werden) und „warm" (sie liegt im
RAM) fehlte ausgerechnet der Fall, der beim Scrollen durch eine große
Sammlung der häufigste ist: **die Miniatur liegt auf der Karte, aber
nicht mehr im Speicher** — verdrängt, oder das Frontend wurde neu
gestartet. Lesen, Entpacken, Eintragen. Diese Zahl stand bisher
nirgends, dabei entscheidet gerade sie, wie sich das Gerät im Alltag
anfühlt.

**Der Installer hat sich selbst überschrieben.** Gemeldet von einem
Nutzer beim Installieren: `syntax error near unexpected token 'fi'`,
mitten im Lauf. Die Datei war in Ordnung — der Fehler entstand erst
beim Ausführen. In `/media/fat/Scripts` liegt das Skript, das gerade
läuft; Bash liest es häppchenweise und merkt sich seine Position darin.
Ein `cp` schreibt in *dieselbe* Datei, und damit steht unter der
gemerkten Stelle plötzlich anderer Inhalt. Dass es nur manchmal
auftrat, passt dazu: es hing daran, ob sich die Datei an genau dieser
Stelle unterschied. Alle drei Installer schreiben jetzt daneben und
benennen um — ein Umbenennen tauscht nur den Verzeichniseintrag, das
laufende Skript bleibt unberührt.

**Der RetroAchievements-Abruf lief beim Start zweimal.** Im Quelltext
steht seit Längerem ein ausführlicher Kommentar, warum dieser Abruf in
einen Hintergrund-Thread verlegt wurde: er hielt den Start um bis zu
3,5 Sekunden an, und der Bildschirm blieb dunkel. Nur stand die alte,
blockierende Fassung vierzig Zeilen darüber weiterhin da. Beide liefen.
Die Verbesserung, die der Kommentar beschreibt, hat nie stattgefunden.
Aufgefallen ist es beim Vermessen, nicht beim Lesen. Jetzt ist es
wirklich so, wie es dort steht.

**Das Frontend merkt jetzt selbst, wenn seine Teile nicht
zusammenpassen.** Auf einem Gerät lag `frontend.py` aus Build 184 neben
einem `fe/art.py`, das älter war als Build 180 — von Hand eingespielt,
nur die eine Datei. Der Absturz kam nicht beim Start, sondern beim
ersten Druck auf eine Pfeiltaste, und sah auf dem Bildschirm aus wie
*„das Frontend beendet sich und ich lande im OSD"*, also wie ein
Kernel- oder Anzeigeproblem. Das hat eine Stunde Fehlersuche an der
völlig falschen Stelle gekostet. Beim Start wird jetzt einmal
nachgesehen, ob `frontend.py` und das `fe/`-Paket zueinander passen;
fehlt etwas, steht im Klartext da, **was** fehlt, **seit wann** es
dazugehört und **wie** man es behebt. Abgebrochen wird nicht — ein
Frontend, das wegen dieser Prüfung gar nicht mehr startet, wäre
schlimmer als das Problem.

**Das Bootlogo ist auf Kernel 6.18 wieder da.** Gemeldet als *„ich
sehe etwas länger das OSD, dann kurz den Login-Prompt, dann das
Frontend — das Bootlogo kommt gar nicht mehr"*. Der Fehler war nicht
das Logo, sondern die Reihenfolge: das Frontend wartet vor der
Boot-Animation darauf, dass MiSTer den Bildschirm übergibt — ein Logo
in einen Bildspeicher zu malen, den niemand sieht, ist verlorene Zeit.
Ausgelöst wird diese Übergabe aber von den F9-Nachfassern, und die
laufen aus der Hauptschleife, die erst *nach* der Boot-Animation
beginnt. Wir haben also darauf gewartet, dass jemand klopft, und dabei
selbst die Hand stillgehalten. Auf 5.15 fiel das nie auf, weil dort
schon das erste F9 saß. Die Warteschleife fasst jetzt selbst nach, und
ihre Obergrenze steigt von 6 auf 12 Sekunden. Wer eine Taste drückt,
wartet gar nicht; wer die Übergabe sofort bekommt, merkt nichts.

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

---

## v4.5 — CD-Spiele in Ordnern, C-Modul, Werkzeug für den PC

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
