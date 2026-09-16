# Changelog

Was sich am Frontend so getan hat. Für die ganz kleinteiligen Details
schau am besten in die Git-Historie oder in
`docs/ENTWICKLUNGSHISTORIE.md` (stand früher als über 3300 Zeilen langer
Kommentarblock im Kopf von `frontend/frontend.py`).

## v4.4 — Reset-Feature, HDMI-Performance-Runde, Stream-Menüpunkt

**Jeder Scrollschritt las fünfmal von der SD-Karte** (Build 135):

Auf die Frage, ob ein Rust-Rewrite das Scrollen schneller machen würde,
habe ich nachgemessen statt geantwortet. Ein einzelner Rasterschritt
fasste die Karte **fünfmal** an:

```
open    /media/fat/frontend/retroachievements.cfg
open    /media/fat/frontend/ansicht
exists  /media/fat/frontend/profile
exists  /media/fat/frontend/thumb_cache/hd
exists  /media/fat/frontend/fast_scroll_enabled
```

Bei jedem Tastendruck — für Werte, die sich nur ändern, wenn der Nutzer
im Menü etwas umstellt. In der Listenansicht kam noch
`pulse_effect_disabled` dazu.

**Warum das auf einer Entwicklungsmaschine unsichtbar ist:** dort liegen
die Dateien im Dateisystem-Cache, ein Zugriff kostet Mikrosekunden. Auf
dem MiSTer ist es exFAT auf einer SD-Karte — `open()` plus `read()`
kostet dort 1–5 ms und deutlich mehr, wenn die Karte gerade beschäftigt
ist. Vorauslader, Nachlader und Musik lesen von derselben Karte.

**Das ist die Erklärung für „meistens flüssig, manchmal ein Hänger":**
nicht der Durchschnitt, sondern der Ausreißer. Und ein Rust-Rewrite
hätte daran exakt nichts geändert — er hätte dieselben fünf Dateien
genauso oft geöffnet.

Neu ist `fe/zwischenspeicher.py`: ein kurzlebiger Speicher für genau
solche Schalter, eine halbe Sekunde gültig, mit ausdrücklichem
Verwerfen bei jeder Änderung. Gemessen: **von 50 Zugriffen auf zehn
Schritte auf null.**

**Zwei Fehler dabei, beide vom Test gefunden:**

*Das Verwerfen stand am Anfang der Schreibfunktionen* — und war damit
wirkungslos. Die Umschalter lesen erst den alten Zustand („wenn an, dann
ausschalten"), und genau dieses Lesen füllt den Speicher wieder, bevor
die neue Datei geschrieben ist. Der Schalter im Menü tat dadurch eine
halbe Sekunde lang scheinbar nichts. Jetzt erledigt das ein Dekorator
`@_nach_aenderung` mit `finally` — also auch dann, wenn das Schreiben
fehlschlägt.

*Der Schlüssel hing nur am Namen, nicht am Pfad.* Tests biegen solche
Konstanten auf Testpfade um; ein unter dem alten Pfad gemerkter Wert ist
danach schlicht falsch. `tools/test_cover_prewarm.py` ist genau darüber
gestolpert.

Dazu eine Falle für künftige Tests, die jetzt dokumentiert ist: der
Prüfstand friert `time.monotonic()` ein, die Gültigkeitsdauer läuft dort
also **nie** ab. `tools/_harness.py` räumt deshalb bei jedem
`make_frontend()` auf.


**Die neuen Bänder warteten trotzdem auf den Bildwechsel** (Build 134):

Rückmeldung: *„wenn ich schnell hintereinander nach links oder rechts
drücke, geht es ja auch schneller."* Das ist genau die Beschreibung
einer Kopie, die auf den Bildwechsel wartet — und es war ein Fehler von
mir, einen Build alt.

Build 133 bringt auf dem schnellen Pfad nur noch die geänderten Bänder
auf den Schirm. Die Aufrufer berechneten das Vsync-Verhalten dabei aber
mit `_vsync_ueberspringen(None)` — und `None` heißt dort ausdrücklich
**„Vollbild"**, wofür seit Build 93 *immer* gewartet wird. Die neuen,
kleinen Bänder haben dadurch jedes Mal die vollen 8–17 ms abgewartet,
also genau das, was die Regel sparen soll.

Die Entscheidung fällt jetzt **je Band, nach dessen Höhe** — so wie es
die Liste seit Build 93 macht. Bei schnellem Scrollen entfällt das
Warten für die 253- und 132-Zeilen-Bänder; bei einem einzelnen
Tastendruck wird weiterhin gewartet, und ein Band über einem Viertel der
Bildhöhe überspringt nie (`VSYNC_SKIP_MAX_ANTEIL`).

Dass ein einzelner Druck spürbar anders ist als eine schnelle Folge,
bleibt also — das ist Absicht. Ein einzelner Schritt ist kein Scrollen,
und ein Bildriss wäre dort ohne Not sichtbar. Wem das egal ist, schaltet
*System → Anzeige & Sound → „Schnelles Scrollen"*.


**Das Raster kopierte bei jedem Schritt den ganzen Bildschirm** (Build 133):

Wunsch: *„ich hätte gerne, dass das hin und her scrollen im neuen Raster
schneller läuft."* Beim Nachmessen kam etwas heraus, das ich seit Build
122 übersehen hatte.

Der schnelle Pfad zeichnet nur **zwei** Kacheln neu — die alte und die
neue Markierung. Danach lief aber trotzdem ein volles `fb.flip()`, also
eine Kopie des **kompletten** Bildspeichers: 8,3 MB auf 1080p, auf deinem
Gerät rund 13 ms. Zwei Kacheln sparen und dann den ganzen Schirm
kopieren — das Sparen davor war damit zur Hälfte umsonst.

Die Liste macht es seit Build 96 richtig (`flip_rows()` in
`_draw_navigate_items_impl()`). Den Kachelansichten hat es schlicht
gefehlt.

Jetzt gehen nur noch die geänderten Bänder auf den Schirm — die
angefassten Kacheln und der untere Streifen mit Spielname, Fußzeile und
Position:

| | kopierte Bildzeilen |
|---|---|
| links/rechts | 253 + 132 = **385 von 1080** |
| hoch/runter | 506 + 132 = **638 von 1080** |

Beim **Seitenwechsel** bleibt es beim vollen Bild — dort ändert sich
alles, ein Band wäre dort ein Fehler und kein Gewinn. Dasselbe bei
aktivem Suchbalken, der liegt oben außerhalb der Bänder.

Gilt für das Raster der Spieleliste **und** der Hauptseite. Die Galerie
bleibt bewusst beim vollen Bild: dort ändern sich mit einem Schritt das
große Cover, der Infotext und die Leiste, also ohnehin fast der ganze
Schirm.

**Warum der Test `fb.mm` vergleicht und nicht `fb.buf`.** Ein Vergleich
des Zeichenpuffers würde hier nichts beweisen — der ist in beiden Fällen
gleich, egal wie viel davon anschließend auf den Schirm wandert.
`tools/test_baender_flip.py` prüft deshalb, was wirklich angezeigt wird.
Genau dort würde ein zu knapp bemessenes Band als stehengebliebener Rest
auftauchen — die Sorte Fehler, die es hier schon viermal gab.


**Größere Kacheln, und zwei weitere Kopierstellen entschärft** (Build 132):

**Die Kacheln.** Rückmeldung mit Bildentwurf: *„hier hätte ich gerne
größere Bilder, von der Anzahl passt es aber."* Das Raster rechnete auf
HDMI mit **7×4 = 28** Kacheln und kam damit auf 124×166 — klein genug,
dass ein Cover nur noch ein Farbfleck war. Jetzt **7×3 = 21** und
**176×235**: knapp die anderthalbfache Kantenlänge, mehr als die
doppelte Fläche.

Die Nachbarleiste der Galerie wächst mit (22 % → 34 % der Höhe). Das ist
keine Kosmetik, sondern der Kern der Sache: beide Kachelansichten teilen
sich seit Build 128 **einen** Coverkasten, und `kachel_cover_kasten()`
nimmt den *kleineren* von beiden. Wäre die Leiste stehen geblieben,
hätte sie das Raster wieder heruntergezogen — die größeren Kacheln wären
nie angekommen, und es gäbe dauerhaft vier statt drei Kastengrößen.

> **Einmalig nötig:** *System → Optionen → „Miniaturen vorbereiten"*.
> Die Kachelgröße **ist** der Schlüssel des Zwischenspeichers — eine
> andere Größe heißt zwingend ein Durchlauf. Was vermieden wurde, ist
> der *dauerhafte* Aufpreis: es bleibt bei drei Kastengrößen. Der Preis
> auf der anderen Seite: das große Cover der Galerie schrumpft von 548
> auf 456 Bildpunkte Höhe. CRT bleibt unverändert bei 5×3.

**Und zwei weitere Kopierstellen.** Nach `blit()` in Build 131 zeigte
dasselbe Protokoll noch zwei Posten mit demselben Muster:

| | vorher | jetzt |
|---|---|---|
| `_restore_row_bg`, Listenspalte 700×880 | 0,441 ms | **0,308 ms** |
| `_restore_row_bg`, volle Breite 1920×880 | 0,535 ms | **0,286 ms** |
| `text()`, warmer Streifen-Cache | 0,008 ms | **0,005 ms** |

Zweimal derselbe Griff: `memoryview` auch auf das **Ziel**. Eine
Ausschnitt-Zuweisung auf ein `bytearray` muss den allgemeinen Fall
abdecken, in dem sich die Länge ändert und der Puffer wachsen oder
schrumpfen könnte; auf einem `memoryview` ist die Größe fest und es
bleibt reines Kopieren. Dazu in `_restore_row_bg` eine Abkürzung: deckt
der Bereich die volle Breite ab, ist er ein zusammenhängender Block und
braucht überhaupt keine Schleife.

`text()` stand im Protokoll mit 13 ms **eigener** Zeit bei 21 Aufrufen —
bei Schriftgröße 3 sind das rund 500 Zeilenzuweisungen je Seitenaufbau.

**Was der neue Test dabei gefunden hat, war der Test selbst.** Zwei
Fälle schlugen fehl; beide Male lag es nicht am Code. `_restore_row_bg`
lässt die unterste Zeile eines Bereichs aus, der über den rechten Rand
hinausragt — sie würde hinter dem Pufferende landen. Das war schon immer
so und ist richtig. Der zweite Fehlschlag war nur der liegengebliebene
Rest des ersten, weil der Test zwischen den Fällen nicht aufräumte.
Beides steht jetzt als eigene, ehrliche Aussage in
`tools/test_kopierpfade.py`.


**Der größte Einzelposten im Profiling war eine Zeile** (Build 131):

Aus einem `DRAGEND_PROFILE`-Protokoll vom Gerät:

```
0.144 s  _draw_cats_galerie
  0.075 s  blit          ← 12 Aufrufe
  0.021 s  clear
  0.016 s  flip
```

75 ms in zwölf `blit()`-Aufrufen — mehr als alles andere in diesem
Aufbau. Und anders als ein kalter Miniatur-Cache fällt das bei **jedem**
Seitenaufbau an, auch wenn „Miniaturen vorbereiten" längst durchlief.

Die Ursache stand in einer Zeile:

```python
chunk = pix[src_off:src_off + need]
```

Ein Ausschnitt auf `bytes`/`bytearray` legt eine **Kopie** an. Bei einem
411×548-Cover sind das 548 Zwischenobjekte pro Bild — Speicher
anfordern, kopieren, wegwerfen, 548 Mal. Mit `memoryview` ist derselbe
Ausschnitt ein Verweis, und die Zuweisung kopiert direkt von der Quelle
ins Ziel.

| Cover | vorher | jetzt |
|---|---|---|
| 411×548 (Galerie) | 0,45 ms | **0,25 ms** |
| 733×909 (Liste) | 0,93 ms | **0,54 ms** |

Rund die Hälfte, und das Ergebnis ist Byte für Byte dasselbe — es ist
dieselbe Kopie, nur ohne den Umweg. `diag_lightpath.py` bestätigt das
über alle 34 Fälle.

Die beiden Längenprüfungen von früher sind nicht verschwunden, sie
stehen jetzt **einmal vor** der Schleife statt in jedem Durchlauf. Ihr
Zweck bleibt wichtig: eine Zuweisung mit der falschen Byte-Anzahl
verkürzt ein `bytearray` und verschiebt alles dahinter — auf dem Schirm
sieht das aus, als wäre das halbe Bild diagonal verrutscht.
`tools/test_blit.py` spielt genau diese Randfälle durch.

**Nebenbei überprüft, was nicht das Problem war.** Die schnellen Pfade
der Kachelansichten greifen wie vorgesehen: bei zehn Schritten durch die
Hauptseite gab es einen einzigen vollen Neuaufbau in der Galerie und
keinen im Raster. Der Vollaufbau im Protokoll war also ein echter
Seitenwechsel, kein Fehler. Der Equalizer taucht im ganzen Protokoll
nicht auf.


**Bei halbierter Menü-Auflösung verschwanden alle Boxarts** (Build 130):

Gemeldet: wer die Menü-Auflösung halbiert (etwa gegen Flackern bei
1080p) und **nur** `art_hd/` pflegt, sieht plötzlich gar keine Cover
mehr — obwohl die Bilder da sind und die Miniaturen erzeugt wurden.

Die Schwelle stand an **acht** Stellen als `if H >= 720`. Bei halber
Auflösung ist `H` rund 540, also darunter — das Frontend suchte nur
noch in `art/`. Wer dort nichts liegen hat, bekam nichts. Der alte
„matschig hochskaliert"-Grund für die Schwelle greift hier auch nicht:
HD-Bilder würden ja **herunter**skaliert, und das ist scharf.

**Der naheliegende Fix wäre falsch gewesen.** „Immer zuerst `art_hd/`"
behebt den gemeldeten Fall und macht einen neuen: die Regel trifft auch
die *echte* Röhre mit H=240. Wer dort sein `art/` gepflegt hat — kleine,
fertig verkleinerte Bilder — bekäme ab sofort jedes Cover aus der großen
HD-Datei, also eine 900×1200-Flächenmittelung statt eines fertigen
300×350-Bildes. Auf der schwächsten Hardware der teuerste Weg, und
genau der, gegen den Build 128/129 angearbeitet haben.

Die Regel ist deshalb **absichtlich nicht symmetrisch**:

| Auflösung | Quelle |
|---|---|
| ab 720 Zeilen | nur `art_hd/`, **kein** Rückfall (Build 89: ein hochskaliertes SD-Bild „sieht blöd aus", dann lieber keins) |
| darunter | erst `art/`, und nur wenn dort nichts liegt, `art_hd/` |

Damit behält die Röhre mit gepflegtem `art/` ihren billigen Weg, die
halbe Auflösung sieht ihre HD-Cover, und eine Röhre *ohne* `art/` sieht
künftig auch etwas statt nichts.

Entschieden wird über die **Dateiexistenz**, nicht über das Ergebnis des
Zeichenversuchs — das liefert auch dann nichts, wenn beim Scrollen
bewusst übersprungen wurde. Ein Rückfall an dieser Stelle wäre genau der
Ruckler, den das Überspringen verhindern soll.

Die acht Fundstellen gehen jetzt alle durch `cover_quelle()`; zwei davon
(Trophäenraum und Jahresrückblick) standen in der Meldung noch gar
nicht. Der Test prüft mit, dass niemand sonst mehr `art_hd/` direkt
anfasst — sonst läuft in einem halben Jahr wieder eine Kopie davon
auseinander.


**JPEG-Arbeitskopien, ein Fehler aus Build 128, und die ganze
Dokumentation auf Stand** (Build 129):

**Der Fehler zuerst, weil er meiner war.** Build 128 hat in
`prewarm_thumb_mehrfach()` einmal auf das größte Ziel dekodiert und
alle Kästen daraus gerechnet. Bei PNG ist das richtig und schneller.
Bei JPEG war es beides nicht:

Der **Zeichenpfad** fragt sein Bild je Kasten an und bekommt für eine
kleine Kachel ein 1/8 dekodiertes Bild. Die Vorbereitung rechnete
dieselbe Kachel aus dem großen — andere Bildpunkte. Die gespeicherte
Miniatur war damit **nicht mehr bit-identisch** zu einer frisch
berechneten, und genau das verlangt der Modulkommentar in `fe/art.py`.
Aufgefallen ist es nicht, weil mein Test in Build 128 nur PNG-Quellen
benutzt hat: die Bitgleichheit war geprüft, aber nur für das Format,
bei dem sie ohnehin galt.

Jetzt entscheidet das Format: kann die Bibliothek für dieses Bild
verkleinert dekodieren, wird je Kasten einzeln gerechnet — derselbe
Weg, den der Zeichenpfad geht. Nebenbei ist das auch schneller: 438
statt 520 ms bei einem 900×1200-JPEG.

**Und daraus folgt die Arbeitskopie.** TurboJPEG kann verkleinert
dekodieren (1/2, 1/4, 1/8 direkt aus dem Dekoder), libpng kann das
nicht. Dieselbe Arbeit kostet deshalb:

| Quelle | „Miniaturen vorbereiten", drei HDMI-Kästen |
|---|---|
| PNG | 689 ms |
| JPEG | **416 ms** |

Der Download legt seit Build 129 neben jedes heruntergeladene PNG eine
**JPEG-Arbeitskopie**. Das Original bleibt unangetastet — Build 119 hat
ausdrücklich zugesagt, dass Cover im Original liegen bleiben, und dabei
bleibt es. Liegen beide nebeneinander, nimmt das Frontend die `.jpg`;
wer das nicht will, löscht sie und bekommt wieder das PNG.

Für die Cover, die schon auf der Karte liegen, gibt es
`PC-Tools/arbeitskopien.py` — auf einem PC Minuten, auf dem MiSTer
Stunden. Kategorie-Abzeichen bleiben außen vor: JPEG kennt keine
Transparenz.

**Eine Größenbremse habe ich zweimal falsch eingebaut**, bevor die
Messung es geklärt hat: erst „nur schreiben, wenn das JPEG kleiner ist",
dann „höchstens doppelt so groß". Beide gehen davon aus, die
Arbeitskopie solle Platz sparen. Tut sie nicht — sie spart Rechenzeit,
und die hängt an der **Bildpunktzahl**, nicht an der Dateigröße. Ein
PNG, das sich gut komprimieren lässt, ist klein auf der Karte und beim
Verkleinern trotzdem genauso teuer. Die Bremse hätte die Arbeitskopie
ausgerechnet dort verhindert, wo sie am meisten bringt. Sie ist raus;
der Platzbedarf (0,2–0,4 MB je Cover) steht stattdessen in der README.

**Noch ein stiller Fund:** die Reihenfolge unter den Cover-Formaten war
die von `os.listdir()`, also dem Zufall überlassen. Liegen `.jpg` und
`.png` zu einem Spiel, entschied das Dateisystem — zwei Karten mit
demselben Inhalt konnten unterschiedlich schnell sein, ohne dass
irgendetwas darauf hingedeutet hätte. Jetzt fest: `.art` → `.jpg` → `.png`.

**Dokumentation und Screenshots.** Rückmeldung: *„aktualisiere auch mal
die ganzen Dateien für mein GitHub-Rep, da ist vieles veraltet, auch
die Screenshots sind veraltet."* Beides stimmte. Die Bilder zeigten die
Spieleliste von Build 100; die drei Ansichten aus Build 122/124 kamen
darauf überhaupt nicht vor.

Neu ist `tools/screenshots_bauen.py`: es rendert alle README-Bilder aus
dem **echten Zeichenpfad**, inklusive der drei Ansichten und der
CRT-Fassungen. Ein Bild, das einmal von Hand entsteht, veraltet
zwangsläufig — dieses lässt sich nach jedem Build in einer Minute neu
erzeugen.

Im README waren zwölf Aussagen sachlich falsch, darunter: die
Regions-Reihenfolge stand verkehrt herum (tatsächlich USA > World >
Europe > Japan > Germany), die Menügruppe heißt „Optionen" und nicht
„Verhalten", „Zuletzt gespielt" führt 100 statt 15 Einträge, der
Attract-Modus startet nach 90 statt 45 Sekunden, und es haben längst
alle 48 Systeme ein Logo statt 33. Dazu fehlten F3/F4, F6 und F10 in
der Tastentabelle sowie das halbe Systemmenü.



**„Miniaturen vorbereiten" lief sechs Stunden — und konnte gar nicht
fertig werden** (Build 128):

Rückmeldung: *„Miniaturen vorbereiten läuft im HDMI-Modus jetzt schon 6
Stunden, das ist viel zu lange. Das geht garnicht und schreckt ab."*

Die Zahlen vom Gerät machten daraus etwas anderes als ein
Geschwindigkeitsproblem:

```
28517 Cover  ×  4 Kastengrößen  =  114 068 Cache-Dateien
                  Obergrenze:          40 000
```

Ab 40 000 Dateien verdrängt der Zwischenspeicher das Älteste — also
genau das, was derselbe Durchlauf zwei Stunden vorher gerechnet hat.
**Der Lauf hat sich im Kreis gedreht.** Sichtbar gewesen wäre das an der
Zeile `THUMB_CACHE Verdraengung` im Log; die steht in `/tmp` und ist
nach einem Neustart weg.

**Der Denkfehler dahinter, und er war meiner.** In Build 123 stand als
Begründung, alle drei Ansichten vorzubereiten sei fast gratis: *„die
Rasterkacheln sind klein, das Verkleinern kostet dort einen
Bruchteil."* Nachgemessen an einem 900×1200-Cover:

| Kasten | | Zeit |
|---|---|---|
| 733×909 | Liste | 162 ms |
| 411×548 | Galerie | 183 ms |
| 128×171 | Raster | 68 ms |
| 124×166 | Galerie-Leiste | 68 ms |

Die winzige Kachel kostet **40 % der großen, nicht 3 %**. Die
Flächenmittelung liest jeden Quellpunkt, egal wie klein das Ziel ist —
ich hatte nach der Zielgröße geurteilt, und die ist hier fast egal.

**Vier Änderungen, zusammen gemessen 40 % weniger Zeit und 44 % weniger
Platz auf der Karte** (600×800-Cover), dazu der zweite Kern:

1. **Drei Kastengrößen statt vier.** Raster und Galerie-Leiste
   unterschieden sich um vier Bildpunkte (128×171 gegen 124×166) — und
   ergaben dadurch zwei komplett getrennte Miniaturen je Cover, weil die
   Kastengröße im Cache-Schlüssel steht. Beide benutzen jetzt denselben
   Kasten, und zwar den kleineren der beiden.
2. **Einmal lesen, einmal dekodieren.** Statt dreimal dieselbe Datei von
   der SD-Karte zu holen und dreimal dasselbe PNG zu dekodieren. Die
   Ergebnisse sind bitgenau dieselben — jeder Kasten wird weiterhin aus
   dem Original gerechnet, nie aus einer fertigen Miniatur.
3. **Der zweite CPU-Kern rechnet mit.** Der Menüpunkt hatte den
   Vorauslader-Prozess abgeschaltet (richtig) und danach alles selbst
   gerechnet, einkernig (falsch). Der DE10-Nano hat zwei Kerne.
4. **Acht Byte statt einer halben Megabyte.** Passt ein Cover ohne
   Skalierung in den Kasten, wurde bisher eine vollständige Kopie
   abgelegt. Gemessen: die Kopie war 548 KB groß und mit 5,9 ms
   **langsamer** zu lesen, als das Original neu zu dekodieren (4,8 ms).
   Dort steht jetzt eine Marke.

Die Obergrenze steigt von 40 000 auf 150 000 Dateien — mit drei Kästen
braucht die Sammlung 85 551, und es bleibt Luft.

> **Einmalig nötig:** vor dem nächsten Durchlauf *System → Wartung →
> „Zwischenspeicher leeren"*. Die alten Einträge sind nicht falsch, nur
> größer als nötig — ohne Leeren bleiben sie liegen und der Platzgewinn
> verpufft.

**Und was der Test nicht konnte.** `tools/test_prewarm_absturz.py` hat
beim Umbau gemeldet, die Hälfte der Cover werde nicht mehr vorbereitet.
Das stimmte nicht — sie liefen über den zweiten Kern, und der hat einen
eigenen Adressraum, in dem die Testattrappe nicht gilt. Festgehalten,
weil es für jeden künftigen Test an dieser Stelle gilt.



**Die Richtungstasten folgen jetzt der Anordnung, und die
Kategorie-Logos sind beim Start schon da** (Build 127):

Zwei Rückmeldungen zu den neuen Ansichten, beide berechtigt.

*„ich drücke oben und unten, um nach rechts und links zu gehen, das ist
mist"* — in der **Galerie** lagen die Tasten wie in der Liste
verdrahtet, obwohl dort die Nachbarn **waagerecht** nebeneinander
stehen. Wer ein Cover weiter will, drückte nach oben. Ab sofort
entscheidet die Anordnung, nicht die Gewohnheit:

| Ansicht | hoch / runter | links / rechts |
|---|---|---|
| Liste | ein Eintrag | eine Seite |
| Raster | eine ganze **Reihe** | ein Nachbar |
| Galerie | eine **Seite** | ein Nachbar |

In der Galerie sind hoch/runter damit nicht tot — sie blättern die
Nachbarleiste weiter, also genau das, was in der Liste links/rechts
tun. Spieleliste und Hauptseite rechnen dabei jede mit ihrer eigenen
Spaltenzahl. Der Test dazu führt die Zuordnung jetzt wirklich **aus**,
statt im Quelltext nachzulesen: die alte Prüfung war grün, während die
Bedienung falsch war.

*„das passiert bei jedem Neustart vom MiSTer, das nervt — die Icons /
Logos müssen schon da sein und nicht jedes Mal neu aufploppen"* — der
Nachlade-Thread aus Build 125 hing nur an der **Spieleliste**. Die
Hauptseite hatte weiterhin allein den Vorauslader, und der rechnet nur,
was auf der Karte **fehlt**. Nach einem Neustart liegt aber alles auf
der Karte und nichts im Arbeitsspeicher — genau diese Lücke sah man als
Aufploppen. Jetzt werden die rund zwei Dutzend Abzeichen schon
**während der Startanimation** von der Karte in den Speicher geholt,
und im Leerlauf der Hauptseite noch einmal nachgezogen, falls die
Ansicht gewechselt wurde.

**Rot und Blau waren vertauscht** (Build 126):

Rückmeldung mit Bildschirmfoto: *„die Farben von den Boxarts passen
nicht, was ist da denn passiert?"* — das goldene Nintendo-Siegel war
blau, der Himmel kippte ins Kalte.

Der Bildspeicher des MiSTer ist **BGRA**: `fb.rect((255,0,0))` legt
`(0,0,255)` ab. Der `.art`-Dekoder liefert BGRA, der Downloader erzeugt
BGRA. Die drei Dekoder für PNG und JPEG lieferten aber **RGBA**:

| Stelle | stand dort | richtig |
|---|---|---|
| `fe/bildlib.py` | `TJPF_RGBX` | `TJPF_BGRX` |
| `fe/bildlib.py` | `PNG_FORMAT_RGBA` (0x03) | `PNG_FORMAT_BGRA` (0x13) |
| `fe/art.py` | `_decode_png_python` baute RGBA | baut BGRA |

**Warum es so lange keiner gesehen hat:** bis Build 119 wurde *jedes*
heruntergeladene Cover in `.art` umgewandelt, und der Weg war immer
richtig. Die Anzeige lief also nie durch diese Dekoder. Seit Build 119
bleiben PNG/JPG im Original liegen, seit Build 123 kommen sie sogar
bevorzugt so vom Spiegel. Aus einem schlafenden Fehler wurde ein
sichtbarer — und zwar genau in dem Moment, in dem das Frontend besser
werden sollte.

**Warum kein Test angeschlagen hat, und was sich daran ändert.**
`tools/test_bildlib.py` prüft seit Build 115, dass libpng *bitgleich*
zum Python-Dekoder ist. Beide waren gleich falsch — eine
Gleichheitsaussage über zwei Funktionen sagt nichts darüber, ob beide
richtig liegen. Der neue `tools/test_farbkanaele.py` misst deshalb
gegen einen Maßstab aus einer anderen Familie: `fb.rect()`, also das,
was tatsächlich auf dem Schirm landet. Geprüft werden alle Wege —
libpng, der Python-Dekoder mit jedem PNG-Farbtyp (inklusive Palette und
Graustufen), TurboJPEG, und `.art` als Vergleich.

**Nebenwirkung: die Miniaturen auf der Karte tragen den Fehler.** Am
Schlüssel ist nicht zu erkennen, aus welchem Quellformat eine Miniatur
gerechnet wurde, also müssen alle einmal neu — `THUMB_ALGO_VERSION`
steht jetzt auf „3". Einmal **„Miniaturen vorbereiten"** laufen lassen,
je Bildmodus einmal.

**Und die RetroAchievements-Abzeichen sind gleich mit repariert** — die
liefen schon immer über denselben PNG-Dekoder.

**Warum die Cover trotz „Miniaturen vorbereiten" nachgeladen haben**
(Build 125):

Rückmeldung mit Bildschirmaufnahme: *„die Boxarts sind trotz Miniaturen
vorbereiten nicht sofort sichtbar, das stört"* — in der Galerie waren
die Kacheln der Nachbarleiste beim Scrollen schwarz. Drei Ursachen, alle
meine:

### 1. Die Nachbarleiste stand in keiner Vorbereitungsliste

Die Galerie fragt **zwei** Bildgrößen an, das große Cover und die
Miniaturen der Leiste. Vorbereitet wurde nur die erste:

| | Größe | vorbereitet |
|---|---|---|
| großes Cover | 426 × 569 | ja |
| Leisten-Miniatur | 124 × 166 | **nie, in keinem Build** |

Elf Bilder pro Bildaufbau, alle kalt, alle beim Scrollen übersprungen.
„Miniaturen vorbereiten" konnte laufen, so oft es wollte.

### 2. Die Leiste lief bei jedem Schritt mit

Sie stand mittig um den Cursor — was heißt, dass sie sich bei **jedem**
Schritt um eine Kachel verschiebt und alle elf neu gezeichnet werden
müssen, dazu das große Cover. Jetzt **blättert** sie seitenweise, wie
das Raster seit Build 122. Damit steht sie die meiste Zeit still, und
sie ist nebenbei ruhiger anzusehen.

Erst dadurch wurde ein **schneller Pfad für die Galerie** möglich, den
es vorher aus gutem Grund nicht gab: solange die Leiste steht, ändern
sich pro Schritt nur das große Cover, der Text daneben und welche
Kachel den Rahmen trägt. Gespart werden der Vollbild-`clear()` (auf
1080p 8,3 MB) und elf Kachel-Kopien (rund 0,9 MB) — **pro Tastendruck**.

Der Pixelvergleich dieses neuen Pfads hat gleich noch etwas gefunden:
die Karte um das große Cover ragte 1 Punkt **in die Leiste hinein**
(Polster plus Schlagschatten waren im Abstand nicht eingerechnet). Im
vollen Aufbau unsichtbar, weil die Leiste danach gezeichnet wird — auf
dem schnellen Pfad 2475 abweichende Bildpunkte. Vierter Fall derselben
Sorte im Projekt.

### 3. „Miniaturen vorbereiten" füllt die Karte, nicht den Arbeitsspeicher

Das ist der Grund für das *„bei jedem Neustart"*. Nutzerfrage dazu:
*„kann man nicht was anlegen, JSON oder txt, dass der RAM schnell
gefüllt wird?"*

Eine Datei mit Pfaden hilft nicht — teuer ist nicht das **Finden** einer
Miniatur, sondern das **Auspacken**. Die Richtung stimmt aber, sie muss
nur auf die richtige Stelle zielen: **ein Nachlade-Thread** holt fertige
Miniaturen von der Karte in den Arbeitsspeicher, vorwärts vom Cursor,
nur im Leerlauf, abgebrochen bei jeder Eingabe.

Warum das der vorhandene Vorauslader nicht kann: der ist seit Build 102
ein **eigener Prozess** — und ein eigener Prozess hat einen eigenen
Adressraum, er *kann* unseren RAM gar nicht füllen. Er meldet eine
vorhandene Miniatur als „Treffer" und geht weiter.

Und warum hier ein Thread darf, wo das Verkleinern einen Prozess
brauchte: das Verkleinern ist reines Python und hält die GIL die ganze
Zeit. Das Auspacken ist zlib, ein C-Modul, und **gibt die GIL frei** —
ein Nachlade-Thread nimmt dem Zeichnen also fast nichts weg. Eingetragen
wird die fertige Miniatur trotzdem im Hauptthread; der Cache räumt beim
Eintragen auch auf, und zwei Threads, die dieselbe Liste kürzen, sind
eine Fehlerquelle, die man sich für eine reine Beschleunigung nicht
einhandelt.

Geprüft in `tools/test_ansichten.py`, jetzt 18 Prüfblöcke — darunter der
bitgenaue Vergleich beider Galerie-Schnellpfade (Spieleliste und
Hauptseite, beide Auflösungen, vorwärts und rückwärts) und der Nachweis,
dass die Karte nicht mehr in die Leiste ragt.

**Die Hauptseite bekommt dieselben drei Ansichten, F9 zieht um, und
die README ist wieder auf Stand** (Build 124):

### Raster und Galerie jetzt auch für die Kategorien

Nach der Spieleliste in Build 122 gibt es Liste, **Raster** und
**Galerie** jetzt auch auf der Hauptseite. Der Gewinn ist hier sogar
größer als bei den Spielen: auf HDMI passen **alle** Kategorien einer
typisch bestückten Karte auf ein einziges Bild — 24 Abzeichen, kein
Blättern. Die Liste zeigt dort je nach Auflösung 9 bis 16.

Ein Glücksfall hat das billig gemacht: alle Sysart-Abzeichen sind
320×420, also genau das hochkante 3:4, mit dem auch die Spiel-Cover
arbeiten. Die Kachelrechnung aus Build 122 passt damit **unverändert** —
es brauchte nur einen zweiten Aufrufer, kein zweites Layout. Zwei
Layouts wären zwei Gelegenheiten gewesen, auseinanderzulaufen.

**Eigene Einstellung, eigener Menüpunkt.** Unter *Anzeige & Sound*
stehen jetzt zwei Zeilen: „Ansicht Spieleliste" und „Ansicht
Hauptseite". Die beiden Seiten zeigen Verschiedenes, und es gibt keinen
Grund anzunehmen, dass wer das eine als Raster will, auch das andere so
will. **F10** schaltet weiterhin live um — auf der Seite, auf der man
gerade steht.

Die Galerie zeigt neben dem großen Abzeichen etwas, das heute nirgends
auf der Hauptseite steht: **wie viele Spiele in einer Kategorie
stecken**, wie viele davon Favoriten sind, und wie viele Unterordner es
gibt.

### F9 zieht auf F10 um

In Build 122 lag die Ansichts-Umschaltung auf F9, weil das die letzte
freie Funktionstaste war. Das war ein Fehler — und er stand seit jeher
in unserer **eigenen README**: F9 ist bei MiSTer für den Wechsel
zwischen Konsole und Grafikmodus reserviert. Wir spielen die Taste
sogar selbst ein, wenn wir in den Konsolenmodus wollen, und der
Tastenbelegungs-Assistent lehnt ein erfasstes F9 ausdrücklich ab.

In der Praxis wäre es gutgegangen: solange das Frontend läuft, greift
es die Tastatur exklusiv und MiSTer sieht die Taste gar nicht. Aber
zwei Bedeutungen für dieselbe Taste, von denen eine in der eigenen
Dokumentation als Problemfall steht, ist eine zu viel. **F10** ist frei
und hat bei MiSTer keine Bedeutung.

### Ein Farbklotz, der nie hätte da sein dürfen

Beim Nachrendern der Hauptseite aufgefallen und gleich für beide Seiten
behoben: die Markierung um eine Kachel war eine **gefüllte** Fläche in
Systemfarbe, über die anschließend das Bild gelegt wurde — sichtbar
blieb nur der Rand. Solange ein Bild kommt, sieht das gleich aus. Kommt
keines, weil der Bild-Cache es während des Scrollens überspringt, stand
dort ein vollflächiger Farbklotz, bis das Bild nachkam. Jetzt ist die
Markierung ein **Rahmen**: das kann nicht mehr passieren, und sie malt
nebenbei nur einen Bruchteil der Punkte.

### README

Die README hatte einiges verpasst. Nachgetragen bzw. richtiggestellt:

- **„ROMs in ZIP-Archiven werden aktuell nicht gelistet"** stand noch
  unter „Bekannte Grenzen" — seit Build 121 falsch. Raus, und ein
  eigener Abschnitt dafür.
- **Neuer Abschnitt zu den drei Ansichten** — welche was zeigt, die
  zwei Umschaltwege und warum sie nicht dasselbe tun, und der Hinweis,
  dass „Miniaturen vorbereiten" alle drei mitrechnet.
- **Woher die Cover kommen** — die vier Stufen (Gerät, PNG-Spiegel,
  art-Spiegel, libretro), die Erkennung nach Dateiinhalt statt
  Servername, und der Schalter für fremdes Artwork.
- **Der F9-Abschnitt** bei der Fehlerbehebung sagt jetzt auch, dass das
  Frontend die Taste deshalb selbst nicht belegt.

Beides, Deutsch und Englisch.

Geprüft: `tools/test_ansichten.py` wuchs von 8 auf 13 Prüfblöcke —
darunter der bitgenaue Vergleich des schnellen Rasterpfads der
Hauptseite in beiden Auflösungen und der Nachweis, dass die
Logo-Kastengröße der Ansicht folgt (dieselbe Falle wie bei den Covern).
`tools/test_cover_prewarm.py` Test 8 angepasst: „alle Logos haben
dieselbe Kastengröße" heißt jetzt „eine je Ansicht" — die Aussage
dahinter (unter Logos steht kein Text, der die Höhe verschiebt) ist
unverändert.

**Zweite Cover-Quelle, und zwei Fehler aus Build 122** (Build 123):

### Die zweite Quelle ist da

Der Download geht jetzt **vier Stufen** durch und hört beim ersten
Treffer auf:

0. **Auf dem MiSTer selbst** — liegt das Cover schon in der
   Artwork-Datenbank unter `/media/fat/docs` oder in einem Artpack,
   gibt es nichts zu laden. Kostet null Bandbreite und null Platz.
1. **Spiegel, `png/`-Baum** *(neu)* — fertige PNG/JPG, die genau so
   abgelegt werden, wie sie kommen. Kein Dekodieren, kein Verkleinern,
   kein Umwandeln — seit Build 119 die Form, in der wir Cover haben
   wollen.
2. **Spiegel, `art/`-Baum** — dieselbe Quelle, aber bereits fertig
   verkleinert. Im „art"-Modus die erste Wahl, sonst das Netz darunter.
3. **libretro** — unabhängig vom Spiegel, als letztes Netz.

Drei Eigenheiten der neuen Stufe, alle vom Betreiber so dokumentiert
und alle einzeln geprüft:

- **Klartext-HTTP, kein SSL.** Der Host hat bewusst kein Zertifikat.
  Ein versehentliches `https` wäre kein Schönheitsfehler, sondern der
  Totalausfall der Stufe.
- **Zwei Ablageorte.** Meist `<System>/Named_Boxarts/`, bei Amiga und
  Amstrad direkt `<System>/`. Beide werden gelistet; kommt ein Name in
  beiden vor, gewinnt die direkte. Der Named_Boxarts-Zweig bleibt
  drin — er kostet ein Verzeichnis-Listing pro System und macht die
  Migration schmerzfrei.
- **Der Server meldet falsche Content-Types.** Die Endung kommt aus den
  ersten Bytes. Was kein Bild ist — eine HTML-Fehlerseite etwa —, wird
  **nicht** geschrieben, sondern an die nächste Stufe weitergereicht.
  Lieber eine Stufe später ein Cover als eine kaputte Datei auf der
  Karte.

Dateinamen folgen der No-Intro-Konvention, also derselbe unscharfe
Abgleich wie überall (Build 117).

### Der Beenden-Dialog blieb stehen

Rückmeldung: *„wenn ich das Frontend beenden will und dann Nein
anklicke, bleibt die Infobox stehen — aber nur im HDMI-Modus."*

Der Dialog schreibt mitten in den Bildspeicher, ohne dass die Seite
davon erfährt. Beim nächsten Aufbau sah der schnelle Zeichenpfad seinen
eigenen Schlüssel unverändert, hielt den Hintergrund für gültig und
frischte nur die Zeilen auf — der Dialog blieb zwischen ihnen liegen.
Dass es **nur** auf HDMI auffiel, hat einen Grund: den schnellen Pfad
auf der Hauptseite gibt es nur dort (auf der Röhre ist ein voller
Neuaufbau billiger, dort verschwand der Dialog von selbst).

Die Hinweisbox und der Suchbalken melden so etwas längst an. Beim
Bestätigungsdialog war es schlicht vergessen. Der Pixelvergleich zeigte
nebenbei, dass es **auch auf der Röhre** etwas hinterließ — nur in der
Spieleliste statt auf der Hauptseite, und dort so klein, dass es nie
gemeldet wurde.

### Im Raster luden die Cover einzeln nach

Rückmeldung: *„hab die Miniaturen durchlaufen lassen, und wenn ich dann
mit F9 zum Beispiel in Arcade die Ansicht wechsle, laden die erst, wenn
ich draufgehe."*

Zwei Ursachen, beide echte Fehler aus Build 122:

**Der Vorauslader nahm nur einen Auftrag an.** Die Funktion für „das
brauche ich JETZT" warf bisher die ganze Liste weg und setzte den einen
neuen Auftrag hinein. Für die Liste völlig richtig — dort ist pro Bild
genau ein Cover zu sehen. Im Raster sind es 28, und **jede Kachel warf
die 27 davor wieder weg.** Übrig blieb eine. Genau das sieht man als
„sie laden erst, wenn ich draufgehe": es wurde tatsächlich immer nur
ein einziges Cover pro Bild gerechnet. Jetzt wird gesammelt; verworfen
wird nur die spekulative Vorratsliste, und das einmal.

**„Miniaturen vorbereiten" ließ zwei Ansichten aus.** Der Schlüssel des
Zwischenspeichers enthält die Kastengröße, und Raster und Galerie
rechnen mit anderen Kästen als die Liste. Build 122 bereitete nur die
Liste und die als **Vorgabe eingestellte** Ansicht vor, mit der
Begründung, alle drei zu rechnen sei dreifache Laufzeit für etwas, das
vielleicht nie jemand aufruft. Die Begründung hat die Taste übersehen:
**F9 schaltet ausdrücklich um, ohne etwas zu speichern** — wer sie
benutzt, landet damit immer in der einen Ansicht, für die nichts
vorbereitet wurde. Ein Menüpunkt, der „vorbereiten" heißt und dann doch
nachlädt, ist schlimmer als gar keiner. Jetzt werden alle drei
vorbereitet; die Rasterkacheln sind klein, dreifache Laufzeit wird es
dadurch nicht.

Geprüft in `tools/test_quelle_png.py` (6 Prüfblöcke) sowie in
`tools/test_overlay_redraw.py` und `tools/test_ansichten.py`, die je
einen Block dazubekommen haben.

**Drei Ansichten für die Spieleliste** (Build 122):

Aus den Kachel-Entwürfen ausgewählt: *„B und D und das alte als
Schalter einbauen"*, und zur Bedienung *„besser nur per Schalter unter
Anzeige und Sound"*. Genau so ist es geworden.

- **Liste** — was wir bisher hatten, und weiter die Vorgabe. Sie ist
  die einzige Ansicht, die auch ganz ohne Cover noch etwas anzeigt, und
  die einzige, in der ein langer Titel vollständig lesbar ist.
- **Raster** — 28 Cover auf einen Blick (HDMI 7×4, Röhre 5×3), an der
  einzelnen Kachel steht nichts, der Name des markierten Spiels steht
  darunter. Gescrollt wird **seitenweise**: ein Raster, das bei jedem
  Schritt um eine Reihe wandert, lässt das Auge den gerade
  angeschauten Titel verlieren.
- **Galerie** — ein großes Cover links, die Spieldaten rechts, die
  Nachbarn als Leiste darunter.

**Umgeschaltet wird auf zwei Wegen, und die tun absichtlich nicht
dasselbe.** Der Menüpunkt unter *Anzeige & Sound* setzt die **Vorgabe** —
sie gilt überall und beim nächsten Start. **F9** (am Pad **Select+Y**)
schaltet **nur die gerade offene Kategorie** um und speichert nichts.
Wer im Raster stöbern und bei SNES trotzdem die Liste haben will, kann
das; wer sich festlegt, tut es im Menü.

**Im Raster bedeuten die Richtungstasten etwas anderes**: hoch/runter
wechselt die **Reihe**, links/rechts den **Nachbarn**. Eine Seite
weiterzuspringen, wenn man nach rechts drückt, wäre vor einem Raster
schlicht falsch — das Auge folgt der Reihe, nicht der Seite. In Liste
und Galerie bleibt alles wie bisher.

**Eine reine Ordnerauswahl bleibt immer Liste.** Ordner haben praktisch
nie ein eigenes Cover; ein Raster aus lauter Platzhaltern wäre keine
Ansicht, sondern ein Fehler.

Unter der Haube waren zwei Dinge wichtiger als das Aussehen:

**Die Kastengröße.** Der Schlüssel des Miniatur-Zwischenspeichers
enthält sie. Rechnet der Zeichenpfad mit einer anderen Größe als der
Vorauslader, legt der Vorauslader fleißig Miniaturen an, die nie jemand
findet — es ruckelt, obwohl „Miniaturen vorbereiten" durchgelaufen ist.
Genau das ist schon einmal passiert (Build 73). Deshalb hat jede
Ansicht **eine** Geometriefunktion, die beide Seiten benutzen, und ein
Test, der genau das nachweist. **„Miniaturen vorbereiten" rechnet
außerdem für die eingestellte Ansicht gleich mit** — sonst wäre der
Durchlauf nach einem Wechsel wertlos gewesen.

**Der schnelle Pfad im Raster.** Innerhalb einer Rasterseite werden nur
**zwei** Kacheln neu gezeichnet, die alte und die neue Markierung; alles
andere steht schon richtig im Speicher. Ohne das müsste jeder
Tastendruck 28 Cover neu in den Bildspeicher kopieren. Der
Pixelvergleich gegen den vollen Neuaufbau hat dabei sofort etwas
gefunden: auf der Röhre lag der Rahmen der Markierung drei Punkte tief
**in der Eintragszahl** der Kopfzeile — beim vollen Aufbau blieb sie
darunter stehen, beim schnellen Pfad wurde sie weggewischt. Zwei
verschiedene Bilder für denselben Zustand, und beide falsch. Der
Startpunkt des Rasters wird jetzt abgeleitet statt geraten.

Und: während schnellen Scrollens erscheint **kein** Platzhalter, wenn
ein Cover nur übersprungen wurde. In einer einzelnen Box war das schon
störend (Build 89); in einem Raster aus 28 Kacheln wäre es ein Flimmern
über den halben Bildschirm.

Geprüft in `tools/test_ansichten.py` (8 Prüfblöcke, u. a. der bitgenaue
Vergleich in beiden Auflösungen); anschauen lässt es sich mit
`tools/diag_ansichten.py`.

**ROMs in ZIP-Archiven** (Build 121):

Aus dem Vergleich mit Degauss war das der einzige Punkt, bei dem uns
wirklich etwas fehlte: liegen die ROMs in Archiven, zeigte das Frontend
schlicht nichts an. Der Ordner sah leer aus.

Ab jetzt ist ein Archiv für uns **ein Ordner wie jeder andere**.
Unterordner im Archiv werden zu Unterordnern, die Spiele stehen darin,
und man startet sie ganz normal.

Der Grund, warum das so unaufwendig geht, steht in der offiziellen
MiSTer-Dokumentation: im MGL-Pfad darf ein Archiv wie ein Ordner stehen
(`path="some/other.zip/path/dummy.gg"`). Am **Startweg ändert sich
deshalb keine einzige Zeile** — wir setzen den Pfad einfach durch das
Archiv hindurch zusammen. Geändert hat sich nur das Einlesen.

**Entpackt wird dabei nie etwas**, auch nicht teilweise. Gelesen wird
nur das Inhaltsverzeichnis am Ende der Datei — das sind ein paar
Bytes, kein Auspacken von hunderten Megabyte. Sonst wäre ein Scan über
eine größere Sammlung nicht mehr auszuhalten.

Drei Dinge bewusst so und nicht anders:

- **Ein kaputtes oder halb kopiertes Archiv wirft den Scan nicht um.**
  Es fällt still weg, so wie eine unlesbare Datei auch.
- **Ein Archiv ohne passende ROMs taucht gar nicht erst auf.** Viele
  Sammlungen legen Handbücher oder Textdateien als Archiv daneben; ein
  leerer Ordner dafür wäre nur im Weg. Dasselbe gilt für leere
  Unterordner im Archiv.
- **Romsets bleiben Romsets.** Bei Neo Geo zählt nur `.neo` als
  ROM-Endung; die Teile in einem Romset-Archiv passen auf keine davon,
  und das Archiv bleibt damit genau das, was es vorher war.

Geprüft in `tools/test_zip.py` (6 Prüfblöcke) — darunter ausdrücklich,
dass nach einem Scan im ROM-Ordner keine einzige Datei dazugekommen
ist.

**Arcade, Artpacks, und ein Zwischenspeicher, der zu klein war**
(Build 120):

**Arcade wurde beim Vorbereiten übergangen.** Rückmeldung: *„habe eine
neue SD-Karte verbaut, noch keine ROMs drauf, aber Arcade über Update
All bekommen — wenn ich jetzt Miniaturen dafür vorbereiten will, sagt
das Frontend ‚keine Spiele gefunden'."*

Es hatte recht: die Arbeitsliste war leer. In der Funktion, die
Vorauslader und „Miniaturen vorbereiten" den Cover-Pfad liefert, stand
eine Ausnahme für Arcade mit der Begründung, Arcade-Cover hingen an der
MRA-Datei und es gebe keinen einfachen Dateipfad. Der erste Teil
stimmt — die **Metadaten** kommen von dort —, der Schluss war falsch:
das **Cover** liegt wie bei jedem anderen System unter
`<art>/ARCADE/<Name>`, und der Zeichenpfad sucht es auch genau dort.
Nur das Vorbereiten machte einen Bogen darum. Wer ausschließlich
Arcade hat, stand damit ganz ohne.

**Artwork aus Artpacks.** Seit Build 115 lesen wir die Datenbank unter
`/media/fat/docs`. Artpacks landen aber je nach Paket woanders. Gesucht
wird jetzt in mehreren Wurzeln — `docs`, ein eigener `Artwork`- oder
`Boxart`-Ordner, und die Spiele-Ordner selbst — und dort jeweils in den
üblichen Unterordnern (`Artwork`, `Named_Boxarts`, `Covers`) oder gleich
im Systemordner. Kommt ein Spiel in zwei Paketen vor, gewinnt immer
dasselbe, nicht mal so und mal so.

Bewusst **nur Boxarts**: `Named_Snaps` und `Named_Titles` sind
Bildschirmfotos, und ein Bildschirmfoto an der Stelle einer Verpackung
wäre eine unangenehme Überraschung.

**Der Bild-Zwischenspeicher war zu klein.** Auf die Frage, ob der
zweite Durchlauf durch eine Liste deshalb schneller ist, weil der erste
noch rechnet: *„ja, das stört mich sehr."*

Er tut es, und der Grund war eine Zahl. Ein HDMI-Cover belegt rund
380 KB — in 24 MB passten etwa **sechzig** Stück. Bei einer Liste mit
tausenden Einträgen fällt ein Cover damit längst wieder heraus, bevor
man es wiedersieht, und muss beim nächsten Vorbeikommen erneut von der
Karte gelesen und entpackt werden. Jetzt sind es 96 MB, also rund
**250 Cover** — genug für die ganze Umgebung, in der man sich beim
Blättern bewegt. Auf CRT belegt ein Cover rund 50 KB, dort sind es
entsprechend Tausende.

**Der Download sieht zuerst auf dem Gerät selbst nach.** Liegt das
Cover bereits in einer der Artwork-Quellen, kommt es gar nicht erst in
die Warteschlange — bei einer vollständig installierten Datenbank sind
das zehntausende Einträge, die nicht geladen werden müssen.


**Cover im Original, Enter bleibt Enter, und Geduld mit der USB-Platte**
(Build 119):

**Der Cover-Download wandelt nicht mehr um.** Nutzerwunsch: *„ich würde
ganz gerne JPG und PNG beim Cover-Download bevorzugen, anstatt auf .art
umzuwandeln — denke mal das ist der bessere und schnellere Weg, wenn
einer alles auf einmal runterladen möchte."* Stimmt in beiden Punkten,
und seit Build 115 spricht nichts mehr dagegen — das Frontend liest PNG
und JPG selbst.

Der Rückfall-Weg (libretro-Thumbnails, für alles, was der Mirror nicht
hat) legt das geladene Bild jetzt **unverändert** ab. Das Dekodieren
und Verkleinern in reinem Python auf der MiSTer-CPU fällt weg — genau
der Teil, dessentwegen dort nur zwei gleichzeitige Umwandlungen
erlaubt waren und es früher Abstürze durch Spitzenspeicher gab. Ein
Download ist jetzt nur noch ein Download.

Dazu ein Vorteil, der vorher gar nicht möglich war: die Datei behält
**volle Auflösung**. Bisher wurde auf die Kastengröße *eines* Profils
verkleinert — wer zwischen CRT und HDMI wechselt, brauchte deshalb zwei
Durchläufe. Jetzt bedient dieselbe Datei beide.

Der Preis, ehrlich genannt: **Platz auf der Karte**. Ein volles
libretro-Cover ist ein Vielfaches einer fertig verkleinerten
`.art`-Datei. Wer knapp ist, hängt das Wort `art` an den Aufruf und
bekommt das alte Verhalten. Der Mirror-Weg liefert unverändert fertige
`.art`-Dateien — dort gibt es nichts umzuwandeln.

Damit das überhaupt etwas nützt, kennt der Cover-Index jetzt auch
`.png` und `.jpg`. Liegt zu einem Spiel beides, gewinnt `.art`: schon
verkleinert, also billiger zu zeichnen.

**Die Enter-Taste.** Rückmeldung: *„wenn ich unter Eingabe und Sprache
Bestätigen/Abbrechen vertauschen aktiviere, ändert auf einmal die
Enter-Taste auf der Tastatur ihre Funktion und hat statt Eingabe die
Zurück-Funktion — das ist Mist."*

Er hat recht, und es war schlimmer als beschrieben. Der Umschalter lief
über die **ganze** Tastenbelegung. Auf der Tastatur ist Enter die
einzige Taste mit „Bestätigen", und eine mit „Zurück" gibt es dort gar
nicht (zurück liegt auf Esc, und das ist eine eigene Aktion) — nach dem
Umschalten hatte die Tastatur also **überhaupt keine
Bestätigungstaste** mehr. Der Schalter ist ausdrücklich für das Pad
gedacht (Nintendo- gegen Xbox-Anordnung) und fasst jetzt nur noch das
an.

Dabei ist derselbe Fehler eine Etage tiefer gleich mit aufgefallen:
**Start** wurde ebenfalls zu „Zurück". Es gibt kein Controller-Layout,
auf dem Start abbricht — nach dem Umschalten hatte man zwei
Abbrechen-Tasten und eine zum Bestätigen. Start bleibt jetzt, was es
ist.

**Die USB-Platte, zweiter Anlauf.** Rückmeldung nach Build 117: *„das
findet das Frontend jetzt zwar, aber er liest sie beim Start quasi
nochmal ein, das macht er bei jedem kalten Neustart."*

Build 117 hat das Symptom behoben, nicht die Ursache. Beim Kaltstart
war die Platte nach den vorgesehenen **zehn Sekunden** immer noch nicht
da — also lief ein kompletter Scan ohne sie, und kurz darauf der
automatische zweite mit ihr. Zwei Scans statt keinem.

Jetzt wird bis zu **45 Sekunden** gewartet — aber nur in dem einen
Fall, in dem der Cache weiß, dass dort Spiele liegen, und gerade keine
zu sehen sind. Ist die Platte rechtzeitig oben (der Regelfall), kommt
das Frontend an dieser Stelle gar nicht vorbei und wartet keine
Sekunde. Damit dabei niemand den Stecker zieht, steht auf dem Schirm,
worauf gewartet wird und warum.


**Der letzte große Posten: das Verkleinern** (Build 118):

Nach Build 115 und 116 war klar, woran es noch hängt. Von einem kalten
Cover auf HDMI entfielen **97 von 101 ms** aufs Verkleinern — auf jedes
Cover, in jedem Format, seit es das Frontend gibt.

Der Gewinn kam am Ende aus einer einzigen Beobachtung. Bei einer
Verkleinerung schwächer als 3:1 — und genau das ist der HDMI-Fall,
424×768 in einen 360×420-Kasten sind Faktor 1,8 — entsteht **jede
Zielspalte aus höchstens zwei Quellspalten**. Ein `sum()` über einen
Ausschnitt von zwei Werten kostet dann mehr als die zwei Werte selbst:
der Ausschnitt muss angelegt, der Aufruf gemacht werden. Jetzt werden
die beiden Quellwerte direkt adressiert.

| | vorher | nachher |
|---|---|---|
| HDMI, Faktor 1,8 | 98,8 ms | **45,4 ms** |
| genau halb | 21,2 ms | **10,0 ms** |
| CRT, Faktor 5 | 38,4 ms | 34,9 ms |

Der letzte Fall läuft weiter über den allgemeinen Weg und hat nur
Feinschliff bekommen (Kanalebenen statt Ausschnitten mit Schrittweite
4, Zielzeile per Ausschnitt-Zuweisung statt Bildpunkt für Bildpunkt) —
gut 10 %, quer über alle Faktoren.

**Das Ergebnis ist bitgenau dasselbe wie vorher.** Das ist hier keine
Formsache: eine Abweichung würde nicht auffallen, sie säße einfach für
immer in den vorberechneten Miniaturen auf der Karte, gemischt mit den
alten. Nachgewiesen über 120 Zufallsgrößen und eigens an der Grenze,
an der der schnelle Weg an den allgemeinen abgibt.

**Zusammengerechnet über die vier Builds** kostet ein kaltes JPG-Cover
auf HDMI jetzt rund **43 ms statt 445** — und auf CRT 28 statt 385.


**Eine andere USB-Platte — und zwei Probleme, die daraus folgten**
(Build 117):

Zwei Rückmeldungen, die zunächst nichts miteinander zu tun zu haben
schienen. Sie haben dieselbe Ursache: eine ausgetauschte Festplatte.

**„Bei N64 und Sega 32X werden keine Boxarts mehr angezeigt."** Das sah
nach einem Fehler aus den letzten Builds aus, war aber keiner. Die ROMs
auf der neuen Platte tragen die alte GoodTools-Schreibweise, die
heruntergeladenen Cover die No-Intro-Schreibweise:

```
007 - The World is Not Enough (U) [!]        das ROM
007 - The World Is Not Enough (USA).art      das Cover
```

Zeichenweise passt davon nichts zusammen — nicht einmal „is" gegen
„Is". Neu ist deshalb ein **Ausweich-Vergleich**: alles in Klammern
fällt weg, übrig bleiben Buchstaben und Ziffern in Großschreibung.
Beide werden damit zu `007THEWORLDISNOTENOUGH`.

Er greift **nur, wenn der exakte Name nichts gefunden hat** — dein
eigenes Artwork behält also immer Vorrang. Der Preis: die
Regionskennung fällt weg, die US- und die japanische Fassung desselben
Spiels können auf denselben Namen fallen. Das ist bewusst bezahlt; ein
Cover der falschen Region ist besser als gar keins. Verschiedene Spiele
treffen sich dabei nicht, das ist geprüft: „Super Mario 64" bleibt von
„Super Mario World" getrennt, „Mortal Kombat" von „Mortal Kombat II".

**Nebenbei repariert das etwas Größeres:** die docs-Datenbank aus Build
115 ist durchgehend No-Intro benannt. Wer seine ROMs anders benannt
hat, hätte dort 21.198 Cover liegen gehabt, von denen keines gefunden
wird.

**„Bei jedem Frontendstart wird die Spieleliste neu aufgebaut."** Die
neue Platte läuft langsamer an als die alte: beim Einlesen ist sie noch
nicht da. Für genau dieses Problem gab es schon ein Sicherheitsnetz —
es hat aber **nur nach Netzlaufwerken gesehen**, weil es für einen
NAS-Nutzer gebaut wurde. Eine spät anlaufende USB-Platte fiel durchs
Raster.

Jetzt fragt es allgemein: gibt es jetzt Spieleordner, die es beim
letzten Einlesen noch nicht gab? Wenn ja, wird **einmal** automatisch
nachgezogen, genau wie bisher beim NAS. Der Gang ins Wartungsmenü
entfällt.

Bewusst nur „dazugekommen", nicht „verändert": ein geänderter
Zeitstempel passiert im Alltag ständig — ein gestartetes Spiel reicht —
und würde das Netz in einen Dauerscanner verwandeln.


**Ein Fehler in Build 115 — und die Messung, die eine Vermutung
widerlegt hat** (Build 116):

Rückmeldung nach Build 115: Cover bleiben beim Scrollen häufiger weg
als nötig. Meine Vermutung war, die Schutzschwellen aus den Builds 105
und 107 seien jetzt zu vorsichtig — schließlich ist das Dekodieren
achtzigmal schneller geworden. **Die Messung hat das widerlegt.**

Ein kaltes Cover besteht aus zwei Teilen, und Build 115 hat nur einen
davon angefasst:

| | vorher | nach Build 115 |
|---|---|---|
| dekodieren | 341,8 ms | 3,5 ms |
| auf Kastengröße verkleinern | 97,7 ms | 97,7 ms |

Das Verkleinern ist Flächenmittelung in reinem Python und war früher
der kleinere Posten. Jetzt sind es **97 % der Wartezeit auf HDMI und
91 % auf CRT**. Die Schwellen zu lockern hätte also nicht das Warten
beendet, sondern das Ruckeln zurückgebracht.

**Der eigentliche Grund war ein Fehler.** `prewarm_thumb()` — die
Funktion hinter „Miniaturen vorbereiten" und dem
Hintergrund-Vorauslader — kannte nur unser eigenes `.art`-Format und
gab bei einem JPG schlicht „fehler" zurück. Die 21.198 neuen Cover aus
Build 115 wurden von der Vorbereitung damit **komplett übergangen**.
Jedes einzelne musste der Zeichenpfad berechnen, immer wieder, jedes
Mal wenn man daran vorbeikam. Genau das war zu sehen.

Behoben, indem das Einlesen des Originals jetzt an **einer** Stelle
steht (`original_lesen()`), die sich Zeichenpfad, Vorbereitung und
Arbeitsprozess teilen. Der Modulkommentar verlangt seit jeher, dass
eine gespeicherte Miniatur bitgenau einer frisch berechneten
entspricht; mit drei Fassungen desselben Ablaufs war das eine Frage der
Zeit.

**Dazu der Hebel, den die Messung sichtbar gemacht hat.** TurboJPEG
kann beim Dekodieren gleich verkleinern. Ein 424×768-Cover, das in
einen 360×420-Kasten soll, wird am Ende 231×420 — es reicht also, es
auf 265×480 zu dekodieren statt auf volle Größe. Der Python-Verkleinerer
hat dann 2,6-mal weniger Bildpunkte vor sich:

| JPG-Cover, kalt | vorher | jetzt |
|---|---|---|
| CRT | 43,2 ms | **10,0 ms** |
| HDMI | 104,9 ms | **63,5 ms** |

Eine Stelle war dabei nicht offensichtlich, und die erste Fassung ist
hineingelaufen: als Dekodierziel darf **nicht der Kasten** genommen
werden, sondern die tatsächliche Zielgröße. Mit dem Kasten (360×420)
kommt 371×672 heraus statt 265×480 — der halbe Gewinn verschenkt, und
die Messung hat es sofort gezeigt (89 statt 63 ms). Die Rechnung steht
deshalb jetzt als `zielmass()` an genau einer Stelle, benutzt von allen
dreien.

Neu dabei: `tools/diag_kaltes_cover.py` zeigt diese Aufteilung — und
läuft auch auf dem MiSTer selbst, damit die nächste Entscheidung nicht
wieder auf einer Hochrechnung steht.


**Der MiSTer kann Bilder dekodieren — wir haben es nur nie gefragt**
(Build 115):

Der Anlass war die Suche nach fremden Artwork-Quellen. Gefunden wurde
etwas anderes, und zwar etwas, das das ganze Frontend betrifft.

**Auf dem MiSTer liegen `libpng16` und `libturbojpeg`.** Nicht als
Python-Modul, nicht als Kommandozeilenwerkzeug — deshalb sind mehrere
Suchen daran vorbeigelaufen, meine eingeschlossen. Über `ctypes` sind
sie trotzdem erreichbar: kein Compiler, keine Installation, keine neue
Abhängigkeit.

Der Unterschied ist kein Feinschliff. Unser eigener PNG-Dekoder in
Python braucht für ein 400×560-Cover **210 ms**, libpng **2,6 ms** —
hier gemessen, Faktor 80. Auf dem Gerät bedeutet das: **ein kaltes
Cover fällt von 200–500 ms auf grob 30 ms.**

Genau diese Zahl ist der Grund für den Vorauslader im zweiten Prozess
(Build 104), die Notbremse nach zwei Sekunden (Build 105) und das
Auslagern kalter Cover an den Arbeitsprozess (Build 107). Nichts davon
wird entfernt — es wird nur vom Notbehelf zur Vorsichtsmaßnahme.

**Verschlechtern kann das nichts.** Unser Python-Dekoder bleibt
vollständig erhalten und übernimmt, wenn die Bibliothek fehlt. Dass
beide dasselbe Bild liefern, ist bitgenau nachgewiesen — RGB, RGBA,
Graustufen, Palette. In der Gegenrichtung kann libpng ein
verschachteltes PNG, an dem unserer scheitert; es ist also eine echte
Obermenge.

**JPG wird damit zur vollwertigen Bildquelle.** Gemessen auf dem Gerät
des Nutzers: 18,4 ms für ein 424×768-Cover, verkleinert 9,8 ms.
TurboJPEG kann beim Dekodieren gleich auf 1/2 oder 1/4 heruntergehen,
das nehmen wir mit. Eingehängt ist es an einer einzigen Stelle — dort,
wo bisher nur unser `.art`-Format gelesen wurde. Dadurch können
**alle** acht Cover-Aufrufstellen fremdes Artwork anzeigen, ohne dass
eine davon angefasst werden musste.

**Und die fremde Datenbank, um die es ursprünglich ging.** Viele
MiSTer-Nutzer haben über den Downloader eine Handbuch- und
Artwork-Sammlung installiert, ohne es zu merken. Auf der Karte des
Nutzers lagen dort **21.198 Cover und eine vollständige
Spieledaten-Tabelle**, ungenutzt:

```
/media/fat/docs/<Core>/Artwork/<ROM-Name>.jpg
/media/fat/docs/<Core>/Artwork/gameinfo.tsv
```

Beides wird jetzt gelesen — **rein als Rückfall**. Eigenes Artwork hat
immer Vorrang, eigene Spieledaten auch; die fremde Tabelle füllt nur
Lücken und steuert ein Feld bei, das unsere libretro-Quelle nie hatte:
den **Entwickler**. Für jeden, dessen MiSTer nicht am Netz hängt, ist
das der Unterschied zwischen „keine Infos" und „alle Infos". Ein
Schalter unter **Anzeige & Sound** schaltet das Ganze ab; Vorgabe ist
an, weil es nur dort etwas zeigen kann, wo vorher „kein Artwork"
stand.

Die Zuordnung kostet fast nichts, weil unsere Systemliste die
MiSTer-Core-Namen ohnehin schon führt — die Ordner dort heißen genau
so. Verglichen wird auf Buchstaben und Ziffern eingedampft, wie bei den
Kategorie-Abzeichen in Build 112, damit „MegaDrive", „Mega Drive" und
„mega-drive" alle treffen.

**Zwei Dinge, die beim Bauen wichtig waren.** Erstens: benutzt wird
ausdrücklich TurboJPEG und nicht die klassische libjpeg-Schnittstelle.
Die verlangt, eine große C-Struktur bitgenau nachzubauen, und beendet
bei einem kaputten Bild den ganzen Prozess über `exit()` — aus Python
heraus nicht abzufangen. TurboJPEG meldet Fehler als Rückgabewert.
Dasselbe bei libpng: dort ist es die „vereinfachte" Schnittstelle von
libpng 1.6, die ohne `setjmp` auskommt.

Zweitens ein Fehler, den mir der eigene Test sofort nachgewiesen hat:
TurboJPEG kennt auch Vergrößerungsstufen bis 2/1, und meine erste
Fassung machte aus einem 600×800-Bild bei großem Zielmaß brav
1050×1400 — mehr Arbeit als das Original, ohne ein einziges
zusätzliches Bilddetail.


**Wo bin ich in der Liste? Drei Antworten** (Build 114):

**1. Die Fußzeile zeigt jetzt „142/3500".** Bisher nannte die Kopfzeile
nur die Gesamtzahl — bei 3500 Einträgen sagte nichts, ob man bei 5 %
oder 80 % steht. Die Zahl steht rechts, der Musiktitel rückt
entsprechend früher zu Ende. Passt die ganze Liste ohnehin auf den
Schirm, bleibt die Anzeige weg; sie wäre dann nur Beiwerk und nähme auf
der Röhre dem Titel den Platz.

**2. Die Suche kann endlich einen zweiten Treffer.** Bisher beendete im
Suchmodus jede Taste außer Buchstaben die Suche stillschweigend — auch
hoch und runter. Traf „mario" das falsche Mario, kam man nur weiter,
indem man mehr tippte. Jetzt blättern hoch und runter durch die
Treffer, die Suche bleibt dabei offen, und der Suchbalken zählt mit:
„3/17". Man sieht also auch, ob sich Weitersuchen überhaupt lohnt.

**3. F3 und F4 springen an den Anfang bzw. ans Ende der Liste**, am Pad
Select+L und Select+R. Das waren die letzten im Frontend völlig
unbelegten Funktionstasten, und L/R springen ohnehin schon seitenweise
— mit Select dazu eben ganz an den Rand. Die Hilfeseite führt beides
auf.

**Was dabei nebenbei herauskam — der Zeichenpfad ist zum ersten Mal
bitgenau.** `diag_lightpath.py` vergleicht seit Build 64, ob ein
Einzelschritt dasselbe Bild hinterlässt wie ein vollständiger
Neuaufbau. Seither standen dort **22 von 34 Fällen und rund 25.000
abweichende Bildpunkte** als „bekannt, auf echter Hardware nicht
sichtbar, nicht aufgeklärt". Die Notiz von damals war näher dran, als
sie klang: die Abweichungen lägen „fast alle auf einer einzigen
Bildzeile am unteren Rand der Boxart-Karte".

Es war der **Schlagschatten der Boxart-Karte**, der drei Bildzeilen weit
in das Fußband hineinragt. Der volle Aufbau räumt ihn weg, weil er die
Fußzeile ohnehin wiederherstellt; der leichte Pfad fasste die Fußzeile
nie an. Dazu kam die stehengebliebene Laufschrift. Weil die
Positionsanzeige den leichten Pfad zwingt, die Fußzeile mitzunehmen,
sind beide Ursachen weg: **0 von 34 Fällen, 0 abweichende Bildpunkte.**

Die Sorge um die Kosten war unbegründet und ist nachgemessen: das ganze
Fußband wiederherzustellen kostet 0,013 ms gegen 0,008 ms für nur das
Zahlenfeld — `_restore_row_bg()` arbeitet aus einer fertigen
Hintergrundzeile, die Breite fällt kaum ins Gewicht. Die erste Fassung
hatte trotzdem nur das schmale Feld aufgefrischt, aus Rücksicht auf die
Builds 102–110; der Pixelvergleich hat das widerlegt.

**Die Stelle, an der es hätte klemmen können**, ist nicht die Anzeige,
sondern der Trefferzähler: um „3/17" zu schreiben, muss die *ganze*
Liste durchsucht werden, statt beim ersten Treffer aufzuhören. Über
12.605 Namen sind das 21,8 ms — pro Tastendruck, auf der MiSTer-CPU
entsprechend mehr. Deshalb nimmt die Namensnormalisierung für reines
ASCII eine Abkürzung (`unicodedata.normalize()` ist dort die Identität,
übrig bleibt `.lower()`): 1,6 ms statt 21,8. Dass das wirklich dasselbe
Ergebnis liefert, ist über alle 128 ASCII-Zeichen plus 3000
Zufallstexte mit Umlauten und CJK nachgewiesen, und der neue Sprung ist
über 1000 Zufallsfälle gegen die alte Funktion gestellt — dieselbe
Beweisform wie beim Cover-Index in Build 110.

Am Rande: `test_cover_panel.py` maß seine Geschwindigkeitszusage als
Mittelwert und wurde dadurch rot, wenn die ganze Suite unter Last lief
(Faktor 1,3 statt 1,8, ohne Codeänderung). Jetzt das Minimum aus
mehreren Durchgängen — bei Mikromessungen ohnehin die ehrlichere Zahl,
denn Störungen von außen können nur bremsen.


**Der Bildrand lässt sich jetzt im Menü einstellen** (Build 113):

Abgeschaut bei Degauss, wo Randbreite und Bildlage einstellbar sind.
Bei uns standen die beiden Werte als feste Zahlen im Quelltext:
`OVERSCAN_X = 7`, `OVERSCAN_Y = 5`. Auf HDMI ist das unkritisch; auf
einer Röhre nicht — jede sitzt anders, manche schneiden rechts mehr ab
als links, und wer das korrigieren wollte, musste bisher Python
editieren.

Unter **Anzeige & Sound** stehen dafür zwei neue Punkte: *Rand seitlich*
und *Rand oben/unten*, jeweils in Prozent, jeweils mit Enter eine Stufe
weiter (0–10 in Einerschritten, dann 12 und 15, danach wieder von
vorn). Gespeichert wird in `/media/fat/frontend/overscan`.

**Wer nichts einstellt, bekommt exakt das Bild von vorher** — ohne
Datei gelten weiterhin 7 und 5. Eine kaputte oder von Hand verstellte
Datei (Buchstaben, negative Zahlen, über 20 %) fällt ebenfalls auf
diese Vorgabe zurück, statt ein Menü zu erzeugen, das man nicht mehr
bedienen kann, um den Fehler zurückzunehmen.

**Wie es umgesetzt ist, und warum so:** die beiden Werte werden an
sechsundzwanzig Stellen als `W * OVERSCAN_X // 100` gelesen. Sie alle
auf ein Objektfeld umzustellen wären sechsundzwanzig Gelegenheiten, ein
Layout zu verschieben. Stattdessen überschreibt `_overscan_anwenden()`
die Modul-Variablen — dieselbe Wirkung, ohne eine einzige dieser Zeilen
anzufassen. `tools/test_bildrand.py` weist nach, dass der Wert
tatsächlich überall ankommt: geprüft wird nicht die Einstellung,
sondern das Bild, auf CRT und HDMI, für Hauptseite und Spieleliste.

Eine Stelle war dabei nicht offensichtlich: der Layout-Zwischenspeicher
hat den Schlüssel `(Breite, Höhe, Boxart ja/nein)` — der Rand kommt
darin nicht vor. Ohne Leeren bliebe nach dem Umschalten die alte
Aufteilung stehen und die Einstellung wäre sichtbar wirkungslos.


**Zwei weitere Kategorie-Abzeichen** (Build 112):

`CUSTOM_CORES` und `PHYSICAL_DISC_CORES`, im selben Stil und derselben
Größe wie die anderen 57 — durch denselben Umwandler gelaufen
(`PC-Tools/sysart_abzeichen.py`, viertes Blatt), also 320×420 mit
C_PANEL als Hintergrund. Damit landen sie automatisch im selben
Rechteck wie alle anderen; der Test weist das nach.

**Die beiden hängen nicht an einem Systemkey, sondern am Ordnernamen**
auf der SD-Karte — derselbe Fall wie „Computer". Bei „Computer" steht
im Code ein wörtlicher Vergleich, samt der ehrlichen Einschränkung *„bei
anderen Nutzern mit anders benanntem Ordner greift dieser Sonderfall
nicht"*. Für diese beiden ist es nachsichtiger gelöst: verglichen wird
der auf Buchstaben und Ziffern eingedampfte Name. „Custom Cores",
„custom cores", „CustomCores" und „_Custom Cores" treffen damit alle
dasselbe Abzeichen, ebenso „Physical Disc Cores" und die Kurzform „Disc
Cores". Ein Systemkey behält weiterhin Vorrang.

Am Umwandler eine Kleinigkeit, die das Nachtragen erst praktikabel
macht: `--nur N` verarbeitet ein einzelnes Blatt. Vorher mussten alle
Blätter gleichzeitig vorliegen — für zwei Nachzügler hätte man die
älteren Vorlagen wieder heraussuchen müssen, die gar nicht im Repo
liegen.

Beim Verteilen ist nichts zu beachten: es sind **neue** Dateinamen, die
kopieren die Installer ohnehin. Die einmalige Komplett-Ersetzung aus
Build 101 (`.abzeichen_v1`) bleibt unberührt.


**Das Frontend startet auch auf dem neuen MiSTer-Kernel** (Build 111):

Rückmeldung: „Einige Nutzer haben auf den neuen Kernel gewechselt, und
da lief unser Frontend nicht mehr — deswegen habe ich Update All nicht
gestartet."

Das MiSTer-Update vom **07.09.2026** hat den Linux-Kernel gewechselt und
dabei den Zugriff auf den Bildspeicher verändert. Mehrere Frontends
(Zaparoo, Degauss) starteten danach nicht mehr — sie beendeten sich,
*bevor* überhaupt etwas auf dem Schirm stand. **Kernelseitig ist nichts
zurückgenommen worden**, jedes Programm hat sich selbst gepatcht. Wir
also auch.

**Bei uns hing es an einer einzigen Funktion.** `_read_geometry()` las
drei Dateien unter `/sys/class/graphics/fb0/`. Fehlt oder ändert sich
eine davon, fliegt nach fünf Versuchen eine Ausnahme — und das Frontend
endet still. Wort für Wort das gemeldete Verhalten.

**Der Umbau in drei Punkten:**

1. **sysfs bleibt der erste Versuch.** Auf dem alten Kernel ändert sich
   buchstäblich nichts — gleicher Code, gleiche Werte. Erst wenn er
   ausfällt *oder unplausible Werte liefert*, übernimmt der Rückfall.
2. **Der Rückfall fragt den Treiber direkt** (`FBIOGET_VSCREENINFO` /
   `FBIOGET_FSCREENINFO`). Diese ioctls sind stabile Kernel-ABI und seit
   Jahrzehnten unverändert; die sysfs-Attribute sind es nicht. Dieselben
   Aufrufe benutzt `tools/fb_probe.py` schon länger, dort auf echter
   Hardware erprobt. Beantwortet ein Treiber nur den ersten, wird die
   Zeilenlänge aus der Breite abgeleitet.
3. **Scheitert doch alles, steht danach im Log, WAS der Kernel
   anbietet** — alle `/dev/fb*`, alle Knoten unter
   `/sys/class/graphics/`, und je Knoten die Dateien samt Inhalt. Genau
   diese Zeilen fehlen den anderen Frontends, die „einfach nicht mehr
   starten".

Dazu Kleinigkeiten am Rand: `/dev/fb0` ist nicht mehr fest verdrahtet
(erster Kandidat bleibt es, `DRAGEND_FBDEV` übersteuert für die
Fehlersuche), das Gerät wird jetzt *vor* der Geometrie geöffnet (der
ioctl-Weg braucht einen offenen Deskriptor), und ein unerwarteter
Farbtiefenwert landet im Log statt nur auf einer Konsole, die in dem
Moment niemand sieht.

**Geprüft wird gegen einen nachgebauten sysfs-Ordner und einen
nachgebildeten Treiber** (`tools/test_kernel_wechsel.py`) — auf dem
Entwicklungsrechner gibt es keinen MiSTer-Bildspeicher, und die Zusage
„läuft auf beiden Kerneln" ließe sich sonst überhaupt nicht prüfen.
Test 1 rechnet dabei mit genau den Werten, die auf dem Gerät des
Nutzers abgelesen wurden (5.15.1-MiSTer, CRT: `320,240` / `1280` / `32`)
— damit der alte Kernel nicht kaputtgeht, während der neue gerettet
wird.

*Ehrlich zur Grenze dieser Änderung:* was der neue Kernel wirklich
anbietet, weiß ich nicht — niemand hat bisher berichtet, welche Dateien
dort noch da sind. Der Rückfall deckt den wahrscheinlichsten Fall ab
(sysfs weg oder unvollständig). Startet es danach immer noch nicht,
liefert die neue Diagnose im Log beim ersten Versuch die Antwort, statt
dass wir raten.


**Die Karte unter dem Abzeichen wird nicht mehr bei jedem Schritt neu
gemalt** (Build 110):

Sie ist bei jeder Kategorie **exakt dieselbe** — gleiche Stelle, gleiche
Größe, gleiche Farben, seit alle Abzeichen 320×420 groß sind. Beim
Kategoriewechsel ändert sich an ihr kein einziger Bildpunkt. Gemessen
kostete sie trotzdem 0,283 ms und damit **22 %** eines
Kategorieschritts auf HDMI.

Auf dem schnellen Weg entfällt sie jetzt; das Abzeichen deckt sie
ohnehin vollständig ab. Nach einem vollen Aufbau (dort hat `fb.clear()`
sie weggewischt) und auf dem leichten Navigationspfad (der räumt die
ganze Artbox-Fläche frei) wird sie weiterhin gezeichnet — beides prüft
der Test namentlich nach.

| Auflösung | voller Aufbau | schnell | |
|---|---|---|---|
| CRT 320×240 | 0,250 ms | 0,249 ms | bewusst aus |
| 1280×720 | 1,139 ms | 0,736 ms | **+35 %** |
| HDMI 1920×1080 | 1,786 ms | 0,943 ms | **+47 %** |

**Ein Messfehler von mir, der beinahe durchgegangen wäre:** die
Kategorien im Test und im Benchmark hatten keinen Systemkey — und ohne
den liefert `_category_art_key()` None, es gibt gar kein Abzeichen, und
der Zeichenweg landet im „kein Artwork"-Platzhalter. Gemessen und
geprüft wurde also der Platzhalter, nicht die Karte. Aufgefallen ist es
nur, weil in einer Messung plötzlich weder `karte_mit_schatten()` noch
das Blitten des Abzeichens auftauchte. Mit richtigem Systemkey liegt der
Schritt 0,3 ms höher als vorher gedacht — die Zahlen oben sind die
korrigierten. Der Test prüft jetzt als **erstes**, dass überhaupt ein
Abzeichen gezeichnet wird.


**Zwei Markierungsbalken gleichzeitig — Fehler aus Build 108 behoben**
(Build 109):

Nutzer-Screenshot: im Hauptmenü leuchten zwei Zeilen rot, „seit dem
letzten Update, wenn ich scrolle und das Bild verlasse nach oben oder
unten". Der Fehler ist meiner, eingebaut mit Build 108.

**Die Ursache:** `_draw_dynamic_cats()` malt den Markierungsbalken
**selbst** (`fb.rect`), statt über `_draw_cat_row()` zu gehen — und trug
sich deshalb nicht in die Spurbuchhaltung ein, die Build 108 eingeführt
hat.

Der Ablauf, der den Rest erzeugt:

1. Ein leichter Navigationsschritt lässt `_draw_cat_row()` die **alte**
   Zeile zeichnen. Die trägt sich brav ein — als schmales Textfeld,
   360 Punkte breit.
2. Danach malt `_draw_dynamic_cats()` die **neue** Zeile mit einem
   1300 Punkte breiten Balken. **Ohne Eintrag.** Die Spur dieser Zeile
   stand weiterhin auf „360 Punkte Text".
3. Wandert die Auswahl beim nächsten Schritt weiter, räumt der schnelle
   Weg nur diese 360 Punkte frei. Die restlichen **940 bleiben als roter
   Balken stehen** — nachgemessen 61560 Bildpunkte.

Bis Build 107 fiel das nicht auf, weil jeder Seitenaufbau ohnehin mit
`fb.clear()` begann und alles miterledigte. Der schnelle Weg hat den
Fehler nicht verursacht, er hat ihn **sichtbar gemacht**.

**Warum der Test ihn nicht gefunden hat, und was jetzt anders ist.**
`tools/test_hauptseite_spuren.py` rief bisher immer nur
`draw_page_cats()`. Im echten Ablauf wechseln sich aber **drei** Wege ab
— leichter Navigationsschritt, Puls-Takt, voller Aufbau —, und der
Fehler entstand genau an der Naht. Der Test fährt jetzt diese Mischung
und vergleicht nach **jedem einzelnen** Schritt (der Rest ist erst nach
dem übernächsten zu sehen).

**Und ein Eigentor beim Absichern, für die Nachwelt:** dieser neue Test
meldete zunächst 2022 abweichende Bildpunkte auf CRT — an einer Stelle,
die mit dem Freiräumen nichts zu tun hatte. Ursache war der Test:
`_pulse_factor()` rechnet gegen `self._pulse_t0`, einen Wert **je
Instanz**. Die Vergleichsseite hatte damit eine andere Schimmer-Phase.
Auf HDMI fiel es nicht auf, weil die Schimmerfarbe dort auf gröbere
Stufen gerundet wird.

**Stand nach der Korrektur** (HDMI, Kategorieschritt): 1,90 ms vor Build
108, jetzt **0,89–0,98 ms**. Was übrig bleibt, verteilt sich auf fünf
`rect()`-Aufrufe (Markierungsbalken und die Karte unter dem Abzeichen),
das Freiräumen der Spuren und siebzehn Textzeilen. Die Karte unter dem
Abzeichen ist dabei bei jedem Schritt identisch — der nächste Kandidat,
falls es noch nicht reicht.

**Das Hauptmenü — diesmal an der richtigen Stelle gesucht** (Build 108):

Build 107 hat den Start entlastet, aber die Rückmeldung blieb: „scrollt
noch etwas langsam, wirkt etwas träge". Zu Recht — ich hatte die
Hintergrundarbeit untersucht und den **Zeichenweg der Hauptseite selbst**
nie gemessen. Das nachgeholt, und es lagen dort zwei Posten, die Seite 1
längst hinter sich hat:

| | |
|---|---|
| `fb.clear()` bei **jedem** Kategorieschritt | 0,64 ms — eine Kopie von 8,3 MB |
| ein `fb.rect()` je sichtbarer Zeile, direkt nach diesem clear | 0,94 ms für 16 Aufrufe |

Zusammen 83 % von 1,90 ms — für Arbeit, die zweimal dasselbe tat.

**Erstens: `bg_fresh` für die Kategoriezeilen.** Nach einem frischen
`fb.clear()` steht der Hintergrund bereits; eine unmarkierte Zeile hat
dann gar nichts mehr zu füllen. Seite 1 hat genau das seit Langem
(gefunden damals mit „37 rect()-Aufrufe pro Bildaufbau bei 17-18
sichtbaren Zeilen"), Seite 0 nicht. Nebenbei eine Korrektur: die Füllung
war `fb.rect(..., C_BG)` — flach, ohne die Randabdunkelung, die
`fb.clear()` anlegt. Die Zeilenbänder der Hauptseite waren dadurch
minimal heller als der Rest. Derselbe Fehler war auf Seite 1 schon
einmal per Pixelvergleich gefunden worden; jetzt sehen beide Seiten
gleich aus.

**Zweitens: der schnelle Weg ohne Vollbild-Clear.** Ändert sich an der
Form der Seite nichts, bleibt der Hintergrund stehen und es wird nur
freigeräumt, was im vorigen Bild wirklich bemalt war — **6 % des Bildes
statt 100 %**. Abgesichert über `fb.full_redraw_gen` wie auf Seite 1:
lief zwischendurch irgendeine andere Bildschirmseite, wird wieder voll
aufgebaut.

Zwei Bereiche brauchten dabei eigenes Freiräumen, weil sie sich
unabhängig von der Kategorie ändern: die Kopfzeile mit
Songtitel-Laufschrift und Equalizer (wird der Titel kürzer, bliebe der
Schwanz stehen) und das Netzwerksymbol unten rechts (es wird *nur*
gezeichnet, wenn eine Verbindung besteht — fällt sie weg, entfernt es
sonst niemand). Beide prüft `tools/test_hauptseite_spuren.py`
ausdrücklich, denn die Bildvergleiche laufen mit eingefrorener Uhr und
ohne Musik und hätten genau diese zwei Fälle nicht gesehen.

**Und eine Schwelle, weil die erste Fassung CRT langsamer machte:**

| Auflösung | bis 107 | ab 108 | |
|---|---|---|---|
| CRT 320×240 | 0,155 ms | 0,155 ms | schneller Weg bewusst **aus** |
| 640×480 | 0,348 ms | 0,336 ms | +3 % |
| 1280×720 | 0,741 ms | 0,573 ms | +23 % |
| HDMI 1920×1080 | 1,389 ms | 0,889 ms | **+36 %** |

Auf CRT ist `fb.clear()` eine einzige Kopie von 307 KB — billiger als
ein Dutzend einzeln freigeräumter Rechtecke mit ihrem jeweiligen
Vorlauf; gemessen **−23 %**. Erst wenn der Bildspeicher groß wird, dreht
sich das Verhältnis. Der schnelle Weg gilt deshalb ab `KOMPAKT_H`,
derselben Schwelle, die das Layout ohnehin schon zwischen „enges Bild"
und „großes Bild" zieht.

Mit beiden Änderungen kostet ein Kategorieschritt auf HDMI **0,89 statt
1,90 ms — 53 % weniger**.

**Neu im `docs`-Ordner:** `Geheimcodes_Hinweise.pdf` (2 Seiten).

**Das träge Hauptmenü direkt nach dem Start** (Build 107):

Rückmeldung: „Warum ist nach einem Neustart das Hauptmenü so träge? Das
Scrollen ist total langsam, wird erst nach ein paar Sekunden besser."

**Gefunden — und es war ein einziger regulärer Ausdruck.** Beim Start
baut `_art_index()` für jedes System ein Verzeichnis „Spielname →
Coverdatei" auf, in `art/` **und** `art_hd/`. Je Datei lief dabei ein
`re.sub(r"^\d+\s+", …)`, um eine führende Sortiernummer zu entfernen.
Bei einer großen Sammlung sind das sechsstellig viele Aufrufe — reines
Python, also **GIL-haltend**, genau in den Sekunden, in denen jemand
das frisch gestartete Menü bedient.

Nachgemessen an 48 Systemen zu je 1500 Covern:

| | |
|---|---|
| Index-Aufbau gesamt | 0,129 s |
| davon nur `re.sub` | 0,090 s (**69 %**) |
| Ersatz ohne regulären Ausdruck | 0,026 s (**4× schneller**) |

Auf der deutlich langsameren MiSTer-CPU sind aus diesen 0,129 s
mehrere Sekunden — das sind die „paar Sekunden" aus der Meldung.

Der Trick ist unspektakulär: die allermeisten Cover-Namen fangen gar
nicht mit einer Ziffer an, und für die ist nach **einer** Prüfung
Schluss. **Gleichwertigkeit ist hier aber nicht verhandelbar** — eine
Abweichung stürzt nicht ab und malt nichts falsch, sie zeigt irgendwann
bei irgendeinem Spiel das falsche Cover, und niemand bringt das je mit
dieser Funktion in Verbindung. `tools/test_cover_index.py` prüft
deshalb nicht ein paar Beispiele, sondern **alle 65536 Zeichen der
Basic Multilingual Plane in vier Stellungen**: null Abweichungen. Dabei
fiel auch auf, warum es `isdecimal()` sein muss und nicht das
naheliegendere `isdigit()` — `\d` trifft genau die Dezimalziffern,
`isdigit()` zusätzlich Dinge wie die hochgestellte Zwei.

**Zweite Hälfte: der Start-Thread steckt jetzt zurück.** Auch viermal
schneller ist auf der schwachen CPU noch spürbar, wenn es am Stück
durchläuft. Solange bedient wird, tut der Thread nichts — Vorwärmen ist
reine Vorratshaltung, und ein Cover-Ordner wird erst gebraucht, wenn
jemand in das System hineingeht.

**Die erste Fassung davon war falsch, und das Nachmessen hat es
gefangen:** sie wartete nur auf eine Ruhephase und blieb prompt bei
**null** eingelesenen Systemen stehen. Bei gehaltener Taste wiederholt
die Eingabe alle 0,08 s, die Ruhe-Schwelle liegt bei 0,10 s — es kommt
schlicht nie eine Ruhephase zustande. Wer nach dem Start zehn Sekunden
durchscrollt, hätte danach jeden Ordner immer noch kalt gehabt. Jetzt
mit Obergrenze (`PREWARM_MAX_WARTEN`): nach zwei Sekunden wird ein
System eingelesen, auch wenn gerade bedient wird. Fortschritt ist damit
garantiert, die Last bleibt ein Happen alle zwei Sekunden statt
sekundenlang am Stück.

*Ehrlich zur Messung:* der Effekt aufs Zeichnen ließ sich auf dem
Entwicklungsrechner **nicht** nachweisen — dort dauert der ganze
Index-Aufbau 0,129 s, verteilt über Sekunden ist das unsichtbar.
Belegt sind die Bausteine (69 % Anteil, Faktor 4, garantierter
Fortschritt), nicht das Endergebnis auf deiner Hardware.

*Und noch ein Eigentor beim Messen, für die Nachwelt:* die erste
Messreihe meldete hartnäckig „null Systeme", obwohl die Obergrenze
schon drin war. Ursache war nicht der Code, sondern die Test-Attrappe —
sie friert `time.monotonic()` **prozessweit** ein, und das Messskript
hatte damit gerechnet. Mit `time.perf_counter()` gemessen greift die
Obergrenze wie vorgesehen.

**Die Kategorie-Abzeichen werden beim Start auf dem zweiten Kern
gerechnet** (Build 106):

Auf die Frage „bringt uns der zweite Kern beim Startvorgang noch etwas
oder im Hauptmenü?" — für **einen** der beiden Teile ja, und die
Trennlinie ist der eigentlich interessante Punkt.

Der Hintergrund-Thread beim Start machte zwei ganz verschiedene Dinge:

| | | |
|---|---|---|
| **(a)** | 57 Abzeichen dekodieren und skalieren | reines Python, **GIL-gebunden** — nimmt dem Zeichnen Rechenzeit weg |
| **(b)** | `os.listdir()` über jeden Cover-Ordner | **I/O** — Python gibt die GIL beim Warten frei |

Nur (a) gehört auf den zweiten Kern. Gemessen, Hauptseite zeichnen
während alle 57 Abzeichen vorgerechnet werden:

| | |
|---|---|
| Leerlauf, nichts nebenher | 1,939 ms |
| mit Thread (bis Build 105) | 2,117 ms (**+9 %**) |
| mit Arbeitsprozess (ab 106) | 1,910 ms (**−2 %**, im Rauschen) |

Kleiner als beim Cover-Vorauslader — und das war zu erwarten: seit
Build 99/100 sind die Abzeichen einheitlich 320×420 statt bis zu 900 px
breit, also längst nicht mehr die teuersten Bilder im Frontend.

**Die Aufträge dafür gab es schon.** `kategorie_logo_auftraege()` wurde
beim Start bereits gerufen — nur wegen `thumb_cache_schuetzen()`, der
Rückgabewert wanderte in den Papierkorb. Genau diese Liste ist das, was
der Arbeitsprozess braucht: Pfad und Kastengröße je Abzeichen, dieselbe
Rechnung wie im Zeichenpfad. Übergeben wird sie jetzt **sofort**, nicht
erst im ersten Ruhemoment: der Arbeiter soll schon während der
Boot-Animation rechnen.

**(b) bleibt ausdrücklich ein Thread.** Ein eigener Prozess brächte dort
nichts — was dabei warm wird, ist der Verzeichnis-Cache des
Betriebssystems, und den teilen sich alle Prozesse ohnehin. Und das
Warten auf die SD-Karte blockiert die GIL gar nicht erst.

**Zwei Dinge ändern sich bewusst nicht:** Die erste sichtbare Kategorie
wird weiterhin **synchron** vor dem ersten Bildaufbau gewärmt — im Code
ist dokumentiert, dass ein Hintergrund-Arbeiter dieses Rennen
nachweislich verliert. Und der zweite große Startposten, das Einlesen
kalter Cover-Ordner (gemessen 1077 ms kalt gegen ~20 ms warm), ist
SD-Karte und nicht CPU. Zwei Kerne machen keine Karte schneller.

Beim Prüfen sah es kurz so aus, als blieben verwaiste Arbeitsprozesse
zurück. Das waren die eigenen Suchbefehle, die sich selbst gefunden
haben — echte Arbeitsprozesse nach einem vollen Testlauf: **null**. Sie
beenden sich korrekt, sobald ihre Leitung schließt.

**Ein kaltes Cover wird nicht mehr im Zeichen-Thread gerechnet**
(Build 105):

Bis hierher galt: während des Scrollens werden noch nicht berechnete
Cover übersprungen, **im Stillstand** werden sie gerechnet. Der
Stillstand ist aber genau der Moment, in dem jemand hinschaut — und eine
Erstberechnung kostet auf HDMI 200–500 ms, in denen die Bedienung steht.
Das war der Rest, der nach Build 104 noch hakte.

Jetzt geht diese Rechnung an den Arbeitsprozess auf dem zweiten Kern.
Der Cover-Platz bleibt eine Runde leer, der `COVER_SETTLE`-Nachlader
holt das Bild, sobald die Miniatur da ist. Kein „kein Artwork"-Aufblitzen
— das unterscheidet der Zeichenpfad seit Build 89 über `_defer_count`,
und dieselbe Unterscheidung greift hier.

**Drei Sicherungen, und die sind das Eigentliche an dieser Änderung:**

1. **Ohne Quelldatei wird nicht ausgelagert.** Ein Spiel ohne Cover — in
   einer frischen Sammlung der Normalfall — würde sonst zwei Sekunden
   auf einen Arbeiter warten, der nichts finden kann, statt sofort den
   Platzhalter zu zeigen. Ein `os.path.isfile()` ist hier kostenlos: wir
   sind bereits im Zweig, der sonst das ganze Bild dekodieren würde.
2. **Notbremse nach zwei Sekunden.** Antwortet niemand — hängender oder
   abgestürzter Arbeitsprozess —, rechnet der Zeichen-Thread doch
   selbst. Lieber ein einmaliger Ruckler als ein Cover, das gar nicht
   mehr auftaucht, und zwar lautlos.
3. **Im Thread-Betrieb wird gar nicht erst ausgelagert.** `dringend()`
   lehnt ab, wenn kein Arbeitsprozess läuft: ohne zweiten Kern nimmt das
   Rechnen dem Zeichnen dieselbe Zeit weg — nur eben später und mit
   einem leeren Cover-Platz dazwischen. Schlechter als vorher wird es
   dadurch nirgends.

**Beim ersten Anlauf lief das Auslagern für *jeden* Aufrufer von
`get_scaled()` — und `tools/test_cover_prewarm.py` hat das sofort
gefangen.** Es hätte das synchrone Vorwärmen beim Start stillschweigend
wirkungslos gemacht: die Funktion, die die Sysart-Datei der ersten
Kategorie *vor* dem ersten Bildaufbau in den Speicher holt, hätte nur
noch einen Auftrag abgegeben und nichts gewärmt. Deshalb ist das
Auslagern jetzt ausdrücklich pro Aufrufer freigegeben (`auslagern_ok`)
und steht an genau zwei Stellen — beiden im Cover-Zeichenpfad.

Dazu ein kosmetischer Fund: der Arbeitsprozess schrieb eine
`BrokenPipeError`-Rückverfolgung auf die Konsole, wenn das Frontend
beendet wurde, während er noch an einer Miniatur saß. Das ist der
Normalfall beim Herunterfahren, sah aber aus wie ein echtes Problem.

**Der Vorauslader wartet nicht mehr, und er zielt beim Umdrehen neu**
(Build 104):

Rückmeldung: „Wenn ich beim Scrollen schnell die Richtung wechsle, hängt
es kurz, und wenn ich Ordner hin und her wechsle auch." Beides zeigte auf
dieselbe Stelle — und alle drei Ursachen waren **Überbleibsel aus der
Zeit, als das Vorrechnen noch im Hauptprozess lief**.

**1. Eine volle Sekunde Wartezeit.** `PREFETCH_SETTLE = 1.0` — und die
Begründung dafür war völlig richtig, solange das Vorrechnen dem Zeichnen
Rechenzeit wegnahm. Sie stand wörtlich im Code, samt Fehlerbericht dazu:
„5–8 Sekunden nach unten gehalten, dann Zurück — und da kam wieder dieser
1-Sekunden-Hänger." Jede Sekunde Wartezeit war damals ein Schutz.

Seit Build 102 rechnet der Vorauslader in einem eigenen Prozess auf dem
zweiten Kern. Der Schutz wurde damit zum Nachteil: wer schnell scrollt
und umdreht, kommt nie eine Sekunde zur Ruhe — es wurde also **gar
nichts** vorgerechnet, während der zweite Kern danebenstand. Jetzt
`PREWARM_SETTLE = 0.10`, also knapp **unter** `COVER_SETTLE`: der
Arbeitsprozess hat seine Aufträge schon, wenn der Hauptthread gleich
darauf das Cover-Panel zeichnet, und rechnet die Nachbarn nebenher. Bei
gehaltener Taste (Wiederholung alle 0,08 s) löst das bewusst nicht aus —
dort wird das Panel ohnehin ausgelassen.

**2. Vorausgeschaut wurde nur in eine Richtung.** 20 Einträge voraus, 6
zurück — und neu gezielt erst nach der nächsten vollständigen Ruhephase.
Wer umdreht, hat 20 vorgerechnete Cover **hinter** sich und kaltes Land
vor sich. Ein Richtungswechsel löst das Neuzielen jetzt selbst aus, auch
wenn für diese Ruhephase schon einmal vorgemerkt wurde.

**3. `_prefetch_neighbor_covers()` ist ersatzlos raus.** Sie dekodierte
Cover im **Hauptthread** — auf HDMI der teure Teil, 200–500 ms je Bild —
und das ausgerechnet in der Ruhephase, in der als nächstes ein
Tastendruck kommt. Ihr Zeitbudget half nur begrenzt: geprüft wurde es am
*Anfang* jeder Runde, die erste Dekodierung lief also immer vollständig
durch.

Sie entstand, bevor es den Vorauslader gab, und konnte nur **roh**
dekodieren: die Zielgröße der Miniatur hängt vom Titeltext ab (längere
Titel → weniger Platz fürs Cover), und die ließ sich dort nicht
vorhersagen. Der Vorauslader **kann** das (`cover_pfad_und_kasten()`,
dieselbe Rechnung wie der Zeichenpfad), liefert deshalb die *fertige*
Miniatur statt des rohen Bildes — und rechnet dabei auf dem zweiten Kern.
Sie war damit die schwächere Kopie am schlechteren Ort.

`tools/test_vorladen_richtung.py` (neu) prüft nicht nur den Quelltext,
sondern fährt den echten Leerlauf-Zweig von `next_action()`: vorgemerkt
wird in der Ruhe, **nicht** ein zweites Mal ohne Grund, aber sehr wohl
nach einem Richtungswechsel — und danach wieder Ruhe statt Dauerfeuer.

**Beim Scrollen wird nur noch freigeräumt, wo wirklich etwas stand**
(Build 103):

Der gemessen größte Einzelposten eines Scrollschritts war nicht das
Zeichnen der Zeilen, sondern das **Freiräumen davor**. Der schnelle Pfad
stellte die komplette Listenspalte wieder her — auf HDMI 859 × 765
Bildpunkte, jede Bildzeile einzeln kopiert, **0,68 von 1,14 ms**. Mehr
als alle siebzehn Zeilen zusammen.

Gebraucht wird der Hintergrund aber nur dort, wo im vorigen Bild etwas
stand, und das ist in **beiden** Richtungen weniger:

| | |
|---|---|
| Breite | Eine unmarkierte Zeile besteht nur aus ihrem Text. Der Zeichensatz hat feste Breite, die Ausdehnung steht also fest. Der mittlere Titel belegt 45 % der Spaltenbreite. |
| Höhe | Der Text ist 8·s hoch — auf HDMI 24 statt 45 Bildpunkte Zeilenhöhe. |

Jede Zeile merkt sich jetzt, wie weit sie gemalt hat. Freigeräumt wird
nur noch das: **185 335 statt 758 175 Bildpunkte auf HDMI — ein
Viertel.** Auf CRT 39 %.

Dazu kamen die Ränder weg. Der alte Aufruf legte rundum 10·s Rand dazu —
ein Überbleibsel des Leucht-Rands, der absichtlich über seine Zeile
hinausragte. Den gibt es seit „Glow-Effekt komplett raus" nicht mehr;
der Rand räumte also Fläche frei, auf der ohnehin nichts stand.

**Im selben Aufwasch eine Doppelarbeit gefunden:**
`_clear_row_glow_margin()` räumte einen Zeilenbereich frei, den
`draw_list_row()` unmittelbar danach **noch einmal** freiräumte —
Bildzeile für Bildzeile dasselbe Rechteck. Auch das ein Rest des
entfernten Glows: ohne ihn schrumpfte der Überstand auf null, und übrig
blieb exakt der Bereich, den die Zeile ohnehin selbst aufräumt. Die
Funktion heißt jetzt `_zeilen_platz()` und rechnet nur noch.

Gemessen (`tools/diag_zeilen_spuren.py`, vier Durchläufe):

| | bis 102 | ab 103 | Gewinn |
|---|---|---|---|
| HDMI, Zeile kommt neu rein | 1,02 ms | 0,65 ms | **rund ein Drittel** (28–41 %) |
| HDMI, Markierung wandert | 0,34 ms | 0,29 ms | ~15 % |
| CRT, Markierung wandert | 0,08 ms | 0,064 ms | ~15–25 % |
| CRT, Zeile kommt neu rein | 0,29 ms | 0,29 ms | im Rauschen |

Dass CRT beim Scrollen nichts gewinnt, ist kein Fehler, sondern die
Rechnung von oben: dort belegt ein Titel 80 % der Spaltenbreite, und die
Zeilen sind ohnehin flach — es gibt schlicht wenig zu sparen. Der
Engpass lag auf HDMI, und dort greift es.

**Geprüft wird das nicht per Augenschein.** Ist die gemerkte Ausdehnung
auch nur einen Bildpunkt zu klein, bleibt bei jedem Schritt ein Rest
stehen, und weil jeder Schritt auf dem vorigen aufsetzt, verschmiert die
Liste. Genau diese Sorte Fehler hat beim Scroll-Blitting zweimal
zugeschlagen. `tools/test_zeilen_spuren.py` vergleicht deshalb Bildpunkt
für Bildpunkt gegen den vollen Neuaufbau — einzeln und nach dreißig
Schritten, hoch wie runter, mit langen und kurzen Titeln gemischt, mit
Ordnern dazwischen und mit einer Liste, die kürzer ist als das Fenster.

**Zwei Sicherungen für den zweiten CPU-Kern** (Build 103):

Auf die Frage „wenn wir zwei Kerne haben, sollten wir die auch nutzen —
aber nicht, dass dann irgendwelche Cores nicht mehr richtig laufen":

1. **Der Arbeitsprozess stellt sich freiwillig zurück** (`os.nice(10)`).
   Im Menü ist der zweite Kern frei, das kostet dort nichts. Es geht um
   den Fall, dass doch einmal beide gebraucht werden: das
   MiSTer-Programm liest bei CD-Cores, Diskettenabbildern und
   MSU-1-Musik während des Spielens fortlaufend von der Karte nach —
   bekäme es seine Rechenzeit nicht rechtzeitig, hört man das als
   Tonaussetzer. Zurückgestellt bekommt es die CPU immer zuerst.
2. **Vor dem Core-Start wird der Vorauslader ganz abgeräumt** und beim
   Rücksprung ins Menü von selbst wieder hochgefahren. Die Auftragsliste
   war ohnehin leer, aber der Prozess belegte gut 18 MB, und eine
   begonnene Miniatur wäre noch bis zu eine halbe Sekunde weitergelaufen
   — genau während der Core lädt.

Der heikle Teil daran war nicht das Beenden, sondern das
**Wiederanlaufen**: ein alter Arbeiter-Thread darf danach nicht als
zweiter neben dem neuen weiterlaufen. Zwei Schreiber auf derselben
Leitung zum Arbeitsprozess, und keine Antwort gehörte mehr eindeutig zu
einer Frage. Jeder Thread prüft deshalb bei jedem Durchgang, ob er noch
der aktuelle Arbeiter ist. `tools/test_vorauslader_prozess.py` zählt
nach.

**Der Cover-Vorauslader rechnet jetzt auf dem zweiten CPU-Kern**
(Build 102):

Ausgelöst durch die Frage: „HDMI-Modus läuft auch, aber das Scrollen ist
mir da zu langsam, vor allem wenn Zeilen nach unten neu ins Bild kommen,
auch wenn ich zwischen den Ordnern hin und her wechsle. Laufen da noch
irgendwelche Sachen im Hintergrund, die das verlangsamen?"

Ja — und die Antwort stand seit Build 73 als offene Einschränkung im
Kopf von `fe/prewarm.py`: der Vorauslader rechnete in einem
Hintergrund-**Thread**, und Pythons GIL lässt immer nur einen Thread
rechnen. Eine begonnene Miniatur ließ sich nicht mittendrin abbrechen.
Auf dem Gerät kostet so eine Erstberechnung 200–500 ms, bei einem
Kategorie-Logo 722 ms. Wer genau dann eine Taste drückte, wartete. Und
das trifft fast nur HDMI: ein Cover für 1080p hat rund **neunmal** so
viele Bildpunkte wie eines für 240p. Die beiden genannten Situationen —
neue Zeilen von unten, Ordnerwechsel — sind genau die, in denen
reihenweise noch nicht berechnete Cover anstehen.

**Der DE10-Nano hat zwei Kerne, und Pythons GIL gilt nur innerhalb
eines Prozesses.** Der Vorauslader ist jetzt ein eigener Prozess
(`fe/prewarm_worker.py`) und rechnet auf dem Kern, der bisher brachlag.
Nachgemessen mit `tools/diag_vorauslader.py` (Rechner mit ebenfalls zwei
Kernen; Dauer eines Scrollschritts, während der Vorauslader arbeitet,
und wie viele Miniaturen er in denselben drei Sekunden schafft):

| | Leerlauf | Thread (bis 101) | Prozess (ab 102) |
|---|---|---|---|
| CRT 320x240 | 0,252 ms | 0,448 ms (+78 %), 32 fertig | 0,294 ms (+17 %), **57 fertig** |
| HDMI 1920x1080 | 1,001 ms | 1,075 ms (+7 %), 3 fertig | 1,060 ms (+6 %), **25 fertig** |

Zwei Dinge stehen da, und das zweite ist für die Beschwerde das
wichtigere: der Thread bremst nicht nur stärker, er **kommt selbst kaum
voran** — auf HDMI 3 fertige Miniaturen gegen 25, also achtmal so weit.
Je mehr Cover vorgerechnet sind, desto seltener muss der Zeichenpfad
beim Scrollen selbst rechnen.

Ehrlich dazu: null Aufschlag ist es auch als Prozess nicht, Speicherbus
und SD-Karte teilen sich beide weiterhin. Null war nie zu erwarten.

**Rückfall eingebaut:** lässt sich der Prozess nicht starten (kein
passendes python3, Speicher knapp, Rechte) oder bricht er im Betrieb
weg, rechnet wieder der Thread — genau wie vorher. Schlechter als vorher
kann es dadurch nicht werden. Der Cache-Ordner steht in **jedem**
Auftrag mit drin, statt einmal ausgehandelt zu werden: das Frontend
schaltet zwischen HD- und SD-Zwischenspeicher um, und ein Prozess mit
eigener Vorstellung davon hätte stillschweigend in den falschen Ordner
geschrieben — die Miniaturen wären berechnet und der Zeichenpfad fände
sie trotzdem nie.

**Scroll-Blitting ist wieder raus** (Build 102):

Es stand unter dem Vorbehalt, unter dem es gebaut wurde („wenn es nichts
bringt, schmeißen wir es wieder raus"). Nachgemessen kostet das
Verschieben in **jeder** Auflösung mehr, als es spart:

| Auflösung | voll | geblittet | Faktor |
|---|---|---|---|
| CRT 320x240 | 0,50 ms | 0,65 ms | 0,8x |
| 720p 1280x720 | 1,25 ms | 1,63 ms | 0,8x |
| HDMI 1920x1080 | 2,04 ms | 2,84 ms | 0,7x |

Der Grund: beide Wege kopieren am Ende dieselbe Fläche. Das Verschieben
spart das Setzen der Schrift, zahlt die Kopie aber **zusätzlich** zu den
vier neu gezeichneten Zeilen und den beiden wiederhergestellten Rändern.
Raus sind der Zeichenpfad, der Schalter, der Menüpunkt unter Anzeige &
Sound, beide Beschriftungen und das flache Vignetten-Band, das nur
seinetwegen existierte — die Randabdunkelung verläuft wieder über das
ganze Bild. Die Schalter-Datei auf der Karte räumt
`Frontend_Update.sh` weg. Begründung und Messwerte bleiben als
Kommentar an der Stelle stehen, an der der Pfad aufgerufen wurde, damit
niemand dieselbe Idee in einem halben Jahr ein zweites Mal baut.

**Nebenbei aufgefallen** (noch nicht behoben, festgehalten in
`tools/diag_hintergrundlast.py`): pro Tastendruck werden vier
Schalter-Dateien von der SD-Karte abgefragt (`profiling_an`,
`pulse_effect_enabled`, `fast_scroll_enabled` und bis eben
`scroll_blit_enabled`), im Leerlauf zwei weitere 12,5-mal pro Sekunde.
Das sind Einstellungen, die sich nur ändern, wenn jemand sie im Menü
umlegt.

**Die neuen Abzeichen kommen auf der Karte auch wirklich an**
(Build 101):

Ausgelöst durch eine Nutzerfrage: „Muss ich die alten händisch löschen
auf GitHub? Oder werden die alten überschrieben?" Auf GitHub: ja. Auf
der **SD-Karte: nein** — und genau das war ein Fehler.

Alle drei Installer kopieren `sysart` bewusst ohne Überschreiben, damit
selbst gemaltes Artwork bei einem erneuten Lauf nicht verlorengeht.
Richtig gedacht für einzelne Bilder — aber mit Build 99/100 wurden
*alle* 57 Kategorie-Logos umgestellt. 42 davon tragen denselben
Dateinamen wie ein altes Logo und wären nie auf der Karte angekommen.
Dieselbe Falle wie damals bei `WOT.art` („immer noch das alte
Zufalls-Zock-Bild, auch nach Update UND Install"), nur 42-fach.

| | |
|---|---|
| neue Abzeichen, die angekommen wären | 15 |
| Abzeichen, die hängengeblieben wären | 42 |
| tote Vollbild-Dateien, die niemand entfernt hätte | 4 (1,7 MB) |

**Die Lösung ist eine einmalige, per Marke gesteuerte Ersetzung.** Fehlt
`sysart/.abzeichen_v1`, wird der komplette Satz genau einmal
überschrieben, die vier toten Dateien werden gelöscht und die Marke
gesetzt. Ab dann gilt wieder „vorhandene behalten" — wer sich danach ein
eigenes Abzeichen malt, behält es bei jedem weiteren Lauf.

**Dazu kam ein Henne-Ei-Problem**, das die Reparatur beim ersten Mal
wirkungslos gemacht hätte: Bei einem Update läuft zuerst noch der
**alte** Installer von der Karte. Der lädt zwar das neue Repo und legt
den neuen Installer ab — sein eigener `sysart`-Schritt ist in genau
diesem Lauf aber noch der alte. Der Nutzer säh eine halb umgestellte
Hauptseite und hätte keinen Grund, das Update ein zweites Mal zu
starten.

Gelöst an der einen Stelle, an der bereits neuer Code läuft, obwohl der
Installer noch der alte war: `Frontend_Install.sh` übergibt am Ende per
`exec` an `Frontend_Update.sh` — und die wurde wenige Zeilen vorher
frisch mitinstalliert. Fehlt dort die Marke, wird die Installation genau
einmal nachgestartet. Drei Bremsen verhindern eine Endlosschleife: ein
Stempel unter `/tmp` (höchstens ein Nachlauf pro Systemstart), eine
Prüfung, ob der Installer auf der Karte die Ersetzung überhaupt kennt,
und die Bedingung, dass `sysart` existiert.

`tools/test_abzeichen_verteilung.py` (neu) schneidet die **echten**
Shell-Blöcke aus allen drei Installern heraus und lässt sie gegen eine
künstliche SD-Karte laufen — kein Nachbau, sondern der Code, der später
auf dem MiSTer läuft. Fiele einer der Blöcke wieder auf „nur ergänzen"
zurück, schlägt der Test fehl.

**Alle 57 Kategorien tragen jetzt ein Abzeichen** (Build 100):

Mit dem dritten Vorlagenblatt (32 weitere Abzeichen) ist der Satz
vollständig. Ein Abzeichen deckt drei Kategorien ab — das Atari-Motiv
trägt „2600/5200/7800" und gilt für alle drei.

| | |
|---|---|
| gebraucht | 57 |
| vorhanden | 57 |
| fehlt | nichts |

**Das dritte Blatt brauchte drei neue Kunstgriffe**, weil es anders
gebaut ist als die ersten beiden:

1. **Grundfarbe statt Schwarz.** Blatt 1 und 2 liegen auf Schwarz,
   Blatt 3 auf Beige. Das Freistellen darf also nicht „alles Dunkle"
   entfernen — es flutet jetzt vom Bildrand her, unabhängig davon,
   welche Farbe der Grund hat.
2. **Farbverlauf im Hintergrund.** Blatt 3 ist nicht gleichmäßig getönt:
   Ecke (102,94,68), Mitte (160,143,106) — 58 Stufen Unterschied. Gegen
   die Eckfarbe verglichen bliebe entweder die halbe Bildmitte als
   „Motiv" stehen oder die Abzeichen würden mitgefressen. Verglichen
   wird deshalb mit dem *Nachbarpunkt*: ein Verlauf ändert sich langsam,
   die Umrandung eines Abzeichens ist ein harter Sprung.
3. **Helligkeitsgrenze.** Der lokale Vergleich allein reichte nicht —
   die weiche Kante ließ das Fluten Punkt für Punkt ins Abzeichen
   hineinkriechen, und bei den meisten war der beige Kreis weggefressen.
   Der Kreis ist aber immer deutlich heller (209) als die hellste
   Hintergrundstelle (143); diese Grenze kann kein Verlauf überschreiten.

Außerdem erkennt der Konverter die Zellgrenzen jetzt an den *echten*
Lücken im Bild statt gleichmäßig zu teilen — mit relativer Schwelle,
denn auf Blatt 3 berühren sich die Abzeichen fast und es gibt keine
komplett leeren Bildzeilen.

**Vier tote Dateien entfernt:** `SMW_HACKS_1920x1080.art`,
`SNES_ALTTP_TRACKER_1920x1080.art` und die beiden 320×240-Varianten
(zusammen 1,7 MB). Sie wurden von keiner Codestelle geladen —
Überbleibsel der Vollbild-Hintergründe, die in Build 87 entfallen sind.

`tools/test_kategorie_abzeichen.py` prüft jetzt alle 57 namentlich: ein
neu dazukommendes System ohne Abzeichen fällt damit sofort auf.

**Neue Kategorie-Abzeichen im Hauptmenü** (Build 99 — „Ich hätte gerne
auf der Hauptseite die alten Sysarts durch diese hier ersetzt, damit es
einheitlich aussieht. Alle bitte auf eine Höhe setzen, mittig rechts
neben den Kategorien … soll alles die gleiche Größe haben, ohne dass ein
Rahmen neu gezeichnet werden muss"):

24 gelieferte Pixel-Abzeichen ersetzen die alten Logos. Sie liegen
jetzt als **einheitliche Kacheln von 320×420** vor — jede Kategorie
landet dadurch im exakt selben Rechteck auf dem Schirm, unabhängig
davon, wie lang ihr Name ist.

**Die Feinheit beim Zuschneiden:** normiert wird auf den *Kreis*, nicht
auf das ganze Bild. Die Vorlagen sind 239 bis 295 Punkte breit — aber
nicht, weil die Kreise unterschiedlich groß wären, sondern weil der Text
darunter verschieden lang ist („N64" gegen „SEGA MASTER SYSTEM"). Wer
auf die Gesamtbreite normiert, macht ausgerechnet die Kreise mit kurzem
Namen zu groß.

Drei Anläufe hat es gebraucht, und alle drei Fehler waren nur im
gerenderten Bild zu sehen:

1. **Schwarzer Kasten.** Der Blattgrund blieb stehen — jedes Abzeichen
   saß in einem schwarzen Rechteck auf der Karte. Jetzt wird der Grund
   vom Rand her geflutet; „alles Dunkle ersetzen" wäre falsch gewesen,
   weil Mega Drive, N64 und Neo-Geo selbst überwiegend schwarz sind.
2. **Abgeschnittene Beschriftungen.** Ein fester Zelleneinzug gegen das
   Übersprechen der Nachbarn schnitt bei „WEITER-SPIELEN" die zweite
   Zeile ab. Jetzt werden die echten Zellgrenzen aus den Lücken im Bild
   bestimmt statt gleichmäßig geteilt.
3. **Rechteck statt Abzeichen.** Ohne Rahmen stand der eingebackene
   Kartenhintergrund sichtbar auf der Seite. Das Abzeichen liegt jetzt
   auf derselben Karte wie das Cover auf der Spieleseite — gezeichnet
   mit dem zusammengefassten Aufruf aus Build 98.

Rahmen in Systemfarbe und Schattenstreifen sind entfallen: die Abzeichen
sind fertige runde Marken mit eigener Umrandung, ein Bilderrahmen
drumherum sah aus wie ein Rahmen um einen Aufkleber. Und er war der
einzige Grund, warum sich beim Kategoriewechsel überhaupt etwas
*außerhalb* des Bildes ändern konnte.

Nebenbei sind die Dateien deutlich kleiner geworden: die alten Logos
lagen bei 900 Punkten Breite (SYSTEM.art war 379 KB, um am Ende 300
Punkte breit gezeigt zu werden), die neuen Kacheln im Schnitt bei
108 KB.

Neu: `PC-Tools/sysart_abzeichen.py` (erzeugt die Kacheln aus den
Vorlagenblättern, für weitere Blätter wiederverwendbar) und
`tools/test_kategorie_abzeichen.py` (32 Prüfungen, darunter: alle
Abzeichen landen wirklich im selben Rechteck).

**Noch offen:** 33 der 57 Kategorien haben noch kein Abzeichen in
diesem Stil — 18 tragen weiter ihr altes Logo, 15 haben gar keins.


**Cover-Panel auf HDMI 27 % schneller** (Build 97 + 98) — zwei Schritte,
beide mit bitgenau unverändertem Bild:

| | alt | neu | |
|---|---|---|---|
| Cover-Panel HDMI | 1,155 ms | 0,844 ms | **−27 %** |
| Cover-Panel CRT | 0,159 ms | 0,154 ms | −3 % |

(abwechselnd im selben Lauf gemessen, Median aus neun Durchgängen — bei
getrennten Läufen schwankten die Zahlen stärker als der Effekt.)

**Schritt 2 (Build 98): Karte und Schatten in einer Zeilenschleife.**
Beim Messen des ersten Schritts fiel auf, dass der sichtbare
Schattenstreifen direkt *neben* der Karte liegt — die Karte endet bei
x+w, der Streifen geht von x+w bis x+w+Versatz. Zwei getrennte Aufrufe
bedeuteten dort zwei Zeilenschleifen über dieselben rund 900 Bildzeilen.

Und die Zeilenschleife ist der teure Teil, nicht die kopierten Bytes:
eine Zeile mit 36 Byte kostet 0,25 µs, eine mit 3076 Byte 0,40 µs — der
Grundaufwand überwiegt deutlich. Jetzt wird in den geraden Mittelzeilen
*eine* vorgefertigte Zeile aus Kartenfarbe und Schattenfarbe
geschrieben. An den Eckenrundungen bleibt alles beim bewährten Weg;
das sind nur wenige Dutzend Zeilen.

**Schritt 1 (Build 97): der Schlagschatten war zu 98 % unsichtbar.**

Die Messung aus Build 96 hatte gezeigt, wo die Zeit beim Scrollen auf
HDMI wirklich hingeht — nicht in die Listenzeilen, sondern ins
Cover-Panel. Und dort war der größte Einzelposten der Schatten.

Er wurde als **vollständiger** abgerundeter Kasten in Kartengröße
gemalt — und die Karte direkt danach darüber. Auf 1080p sind das
769×945 = 726.705 Bildpunkte, von denen **15.210 (2,1 %) jemals zu
sehen sind**. Der Rest wird im selben Atemzug übermalt. Gemessen
0,461 ms pro Panel-Aufbau, also 35 % des gesamten Panels, für nichts.

Der alte Kommentar an dieser Stelle stimmte sogar — „kostet genauso
wenig wie ein normaler `rect()`-Aufruf". Er war nur die falsche Frage:
ein `rect()` dieser Größe ist nicht billig, sondern der zweitteuerste
Posten im Panel.

| | vorher | nachher |
|---|---|---|
| Schatten | 0,461 ms | 0,227 ms |
| Cover-Panel gesamt (HDMI) | 1,125 ms | 0,969 ms |

**Das Bild ist bitgenau unverändert.** Der Schatten ist ein rein
optisches Detail — wäre er hinterher an einer Ecke anders, wäre das
eine Verschlechterung für einen Gewinn, den niemand sieht. Statt die
sichtbare Form als zwei Streifen nachzubauen (naheliegend, aber an den
gerundeten Ecken nicht exakt: auch die Karte hat Eckkerben, durch die
der Schatten stellenweise durchscheint), wird Bildzeile für Bildzeile
gerechnet — Schattenspanne minus Kartenspanne.

**Zwei Fallen, beide vom Test gefunden:**

1. **Der Bildrand.** `rect_rounded()` beschneidet Breite und Höhe am
   Bildrand *zuerst* und rundet danach — eine abgeschnittene Karte
   bekommt also eine andere Rundung als eine freistehende. Die erste
   Fassung bildete das nicht nach.
2. **Zu clever ist langsam.** Die erste Fassung rechnete jede Bildzeile
   einzeln aus. Korrekt — aber gemessen **viermal langsamer** als das
   volle Rechteck, das sie ersetzen sollte. Neunhundert
   Einzelzuweisungen schlagen jede eingesparte Fläche. Jetzt geht der
   gerade Mittelteil in *einem* `rect()`-Aufruf weg, einzeln gerechnet
   wird nur an den Ecken.

Neuer Test: `tools/test_cover_panel.py` (44 Prüfungen), inklusive zweier
Messungen — eine Änderung, die nur theoretisch spart, hat hier nichts
verloren. Geprüft wird jeweils gegen den *alten* Zeichenweg, Byte für
Byte, in neun Größen- und Randkombinationen.

CRT ist von alledem kaum betroffen: das Panel kostet dort 0,165 ms
gegen 1,125 ms auf HDMI, Faktor 6,8. Das deckt sich mit der
Beobachtung, dass sich im CRT-Modus längst nichts mehr träge anfühlt.


**Scroll-Blitting — gebaut, gemessen, und es bringt nichts** (Build 96 —
„Scroll-Blitting probieren wir mal aus, wenn es nichts bringt schmeißen
wir es wieder raus", mit An- und Ausschalter unter *System → Anzeige &
Sound*):

Die Idee: sobald die Markierung den Listenrand erreicht hat, ist **jeder**
weitere Schritt ein kompletter Seitenaufbau. Statt ihn zu bauen, wird der
schon gezeichnete Listenblock um eine Zeilenhöhe im Speicher verschoben
und nur noch vier Zeilen neu gezeichnet.

**Das Ergebnis:**

| Auflösung | voll | geblittet | Faktor |
|---|---|---|---|
| CRT 320×240 | 0,48 ms | 0,48 ms | 1,0× |
| 720p | 1,92 ms | 1,76 ms | 1,1× |
| HDMI 1920×1080 | 2,49 ms | 3,11 ms | **0,8×** |

Der Grund steht in derselben Messung, nach Posten aufgeteilt (HDMI):

| Posten | Zeit |
|---|---|
| **Cover-Panel** | **1,195 ms — 61 %** |
| alle 17 Zeilen zeichnen | 0,734 ms |
| Block verschieben | 0,372 ms |
| nur 4 Zeilen zeichnen | 0,241 ms |
| zwei Randstreifen | 0,040 ms |
| Fußzeile | 0,015 ms |

Blitting greift die 0,734 ms an und ersetzt sie durch 0,653 ms — spart
also rund 0,08 ms von knapp 2 ms. **Der eigentliche Brocken ist das
Cover-Panel, und das zeichnen beide Wege gleichermaßen.**

Ich habe bei diesem Build **zweimal danebengelegen**, beide Male von der
Messung korrigiert. Erst erwartete ich, Blitting werde zu teuer — eine
spaltenweise Kopie über 774 Zeilen gegen 17 Zeilen zwischengespeicherten
Text. Ein erster Prototyp war dann 5× schneller, was die Erwartung
widerlegte. Der Prototyp ließ aber Cover-Panel und Fußzeile weg.
Vollständig gebaut und ehrlich gemessen bleibt nichts übrig.

**Trotzdem ausgeliefert, Standard AUS.** Die Entwicklungsumgebung ist
nicht das Gerät: dort hat das Cover echte Bilddaten und die CPU ist eine
andere. Der Schalter kostet nichts, solange er aus ist, und beantwortet
die Frage auf dem MiSTer mit einem Tastendruck. Bestätigt sich die
Messung dort, gehört der ganze Pfad gelöscht.

**Der Preis, wenn man ihn einschaltet:** die Randabdunkelung wird hinter
der Liste flach. Sie hängt von der Bildzeile ab — verschiebt man den
Block, wandert sie mit, und weil jeder Schritt auf dem vorigen aufsetzt,
summiert sich der Fehler. Oben und unten am Bildrand bleibt sie
unverändert. Die Menüzeile nennt diesen Preis mit.

**Zwei Fehler, die nur der bitgenaue Vergleich gefunden hat.** Der Test
vergleicht den geblitteten Bildschirm Punkt für Punkt mit dem voll
aufgebauten — einzeln und nach 30 Schritten:

1. **Reihenfolge.** `draw_art_panel()` reicht mit seiner untersten Kante
   drei Bildzeilen in die Fußzeile hinein; die Fußzeile räumt das beim
   Wiederherstellen auf. Der Blit-Pfad rief beides umgekehrt auf — der
   Überstand blieb stehen.
2. **Zwischenräume.** Eine Listenzeile räumt nur ihren Textbereich auf
   (39 von 45 Bildzeilen). Die restlichen sechs sind normalerweise
   ohnehin Hintergrund — nach einer Verschiebung steht dort aber Rest
   der Nachbarzeile. Beim Herunterscrollen fällt der aus dem Bild, beim
   Hochscrollen landet er mitten drin.

Neu: `tools/test_scroll_blitting.py` (36 Prüfungen) und
`tools/bench_scrollblit.py`. Nebenbei wurden drei Stellen
zusammengeführt, die denselben Code hatten: das Cover-Panel, die
Fußzeile und der Schlüssel des Hintergrund-Zwischenspeichers.


**MiSTers RA-Einstellungen jetzt im Frontend** (Build 95 — „Sute hat eine
neue Main MiSTer gebaut, die hat nun RA Settings, können wir das
irgendwie mit ins Frontend einbauen?" und später: „Das hätte ich auch
gerne bei uns im Frontend, und zwar dann einstellbar unter System und
dann RetroAchievements"):

Neu unter **System & Wartung → RetroAchievements → Popups & Anzeige**.
Alle zwölf Werte auf einem Bildschirm, auf Deutsch ausgeschrieben statt
als englische Kürzel, und vom Sofa aus bedienbar. Das OSD kann dasselbe
— aber nur auf Englisch, nur mit Kürzeln („Multiline Description") und
nur über drei Menüebenen.

| | |
|---|---|
| Neun Schalter | Popups bei Herausforderungs-Start/-Ende, Fortschritt, Name im Fortschritts-Popup, Bestenlisten-Aktualisierung/-Eintrag, Beschreibung mehrzeilig, Laufschrift in der Erfolgsliste, Erfolgsliste mit Menü+Y |
| Popup-Position | links / mittig / rechts |
| Feinjustierung | Waagerecht −80…+80, Senkrecht −10…+10 |

**Global oder pro Core.** Die Position und die beiden Offsets lassen
sich getrennt für jeden Core einstellen — genau die drei Werte, die
MiSTer laut seinem eigenen Log pro Core ausliest. Ein Umschalter oben
wechselt den Geltungsbereich, und hinter jedem Wert steht, ob er *eigen*
oder vom globalen *geerbt* ist. Ohne diesen Zusatz sehen „0, weil global
0" und „0, weil hier ausdrücklich gesetzt" gleich aus, verhalten sich
aber verschieden, sobald man den globalen Wert ändert.

**Ehrlich bei den Core-Namen:** MiSTer legt pro *Core* ab, nicht pro
System. Game Boy und Game Boy Color teilen sich den Core „Gameboy", SNES
und SMW Hacks den Core „SNES" — eine Änderung gilt also zwangsläufig für
beide. Das steht auch so auf dem Bildschirm, statt es zu verstecken.

**Keine Vorschau des Popups**, obwohl die Versuchung groß war. MiSTer
zeichnet das Popup über den *laufenden Core*, in dessen Auflösung (oft
256×224), nicht in unserer. Eine Vorschau hätte weder die richtige Größe
noch die richtigen Proportionen und würde beim Feinjustieren aktiv in die
Irre führen. Stattdessen der ehrliche Hinweis, dass die Änderung beim
nächsten Core-Start greift.

**Vorsicht beim Schreiben.** Die Datei `/media/fat/retroachievements.cfg`
gehört nicht uns — darin stehen RA-Benutzername *und Passwort*. Das neue
Modul ändert deshalb immer nur genau die eine gemeinte Zeile und lässt
alles andere Byte für Byte stehen: Kommentare, Reihenfolge, Schreibweise,
auch Schlüssel, die wir gar nicht kennen. Geschrieben wird wie bei
MiSTer selbst über eine temporäre Datei mit anschließendem Umbenennen.
Fehlt die Datei, legen wir sie **nicht** an.

Nicht verwechseln: das ist eine **andere** Datei als unsere eigene
`/media/fat/frontend/retroachievements.cfg` (Benutzername +
Web-API-Schlüssel für die Fortschrittsanzeige). Gleicher Name, anderer
Ordner, anderes Format, andere Zugangsdaten — ein eigener Test wacht
darüber, dass die beiden nie zusammenlaufen.

Neuer Test: `tools/test_ra_einstellungen.py` (56 Prüfungen). Zwei
Layout-Fehler wurden nur im gerenderten Bild sichtbar: auf CRT fraß das
lange deutsche Label den *Wert* auf, und die Bedienzeile brach mitten im
Wort ab. Werte stehen jetzt rechtsbündig und bekommen ihren Platz
zuerst.


**Das Flackern der Hinweisbox behoben** (Build 94 — gemeldet per Video:
„das Flackern müssen wir auch beheben, das kommt bei einigen Einstellungen
wenn man was verändert"):

Das Video ließ sich Bild für Bild auswerten (1920×1080, 60 Bilder/s). Die
Hinweisbox verschwand dabei **6 mal pro Sekunde für genau zwei Bilder**
(33 ms) — kein Zufall, sondern ein exakter Takt.

Der Ablauf war:

1. `draw_page_items(flip=True)` → die fertige Seite **ohne** Box geht auf
   den Schirm
2. `_draw_prominent_message()` → die Box wird gezeichnet und mit einem
   eigenen, kleinen Flip nachgereicht

Zwischen 1 und 2 liegt das Rendern der Box (Rahmen, bis zu drei
Textzeilen) — und genau so lange zeigt der Bildschirm die Seite ohne sie.
Der 6-Hz-Takt kam von der Laufschrift (0,18 s): solange die Box sichtbar
ist, fällt sie bewusst auf den vollen Seitenaufbau zurück, und **jeder
dieser Takte erzeugte ein Aufblitzen**.

Das Unangenehme daran: der Kommentar an der betreffenden Stelle
beschreibt diesen Fehler bereits wörtlich — *„sonst blitzt für einen
Frame der Hintergrund ohne Dialog auf, genau das war das Flackern beim
Wechseln zwischen den Optionen"*. Er wurde damals nur für die beiden
Bestätigungsdialoge behoben. Die Hinweisbox kam später dazu und fehlte in
der Aufzählung. Jetzt steht sie drin, und die Box schließt mit einem
vollen Flip ab statt mit einem Streifen.

Unter dem Strich wird dabei sogar ein Vollbild-Flip pro Aufbau
eingespart, weil der vorgezogene Seiten-Flip komplett entfällt.

Neuer Test: `tools/test_hinweisbox_flackern.py` (24 Prüfungen). Er prüft
nicht das Aussehen, sondern die Reihenfolge der Flips — gegen den alten
Stand gehalten schlägt er zuverlässig an.

**Nebenbei: eine Fehlerquelle in der Testumgebung beseitigt.** Die
künstliche Uhr im Testgerüst ersetzte nur `monotonic()`, nicht
`strftime()` — die Uhrzeit in der Statuszeile kam also weiter von der
echten Uhr. Fiel ein Minutenwechsel zwischen Referenz- und
Vergleichsaufbau, meldete `diag_lightpath.py` eine Abweichung, die es
nicht gab (22 Fälle im einen Lauf, 23 im nächsten). Genau das ist beim
Prüfen dieses Builds passiert und hat Fehlersuche an der falschen Stelle
gekostet. Die Uhr steht in Vergleichen jetzt fest.


**Zwei Latenz-Änderungen, beide aus einem einzigen Satz entstanden**
(Build 93 — „Ich habe schnelles Scrollen eigentlich standardmäßig an,
und das fühlt sich manchmal komisch an, bitte berücksichtigen"):

Dieser Satz hat die geplante Richtung umgeworfen. Alles, was als
Beschleunigung vorgeschlagen war, lief bei ihm längst — der Schalter war
die ganze Zeit an. Was er spürte, war die **Kehrseite** davon.

**1. Das Vsync-Auslassen war zu grob.** Es galt pauschal für *jede*
Kopie, sobald der Schalter an war und gerade gescrollt wurde. Ein
Bildriss in einem zwei Zeilen hohen Streifen sieht niemand — derselbe
Riss quer durch ein 1080-Zeilen-Bild sieht jeder. Ab jetzt entscheidet
zusätzlich, **wie viel Bild** die Kopie anfasst:

| Was wird kopiert | Anteil der Bildhöhe | Vsync |
|---|---|---|
| Navigations-Tick, Laufschrift | 11–13 % | wird übersprungen |
| voller Seitenaufbau | 81–84 % | wird gewartet |

Die Schwelle liegt bei 25 %, also weit von beiden gemessenen Werten
entfernt — kein Grenzfall, der bei einer Layout-Änderung zufällig kippt.
Die 11,1 ms Vollbild-Kopie (auf dem Gerät gemessen) passen in den
16,7 ms langen Bildwechsel, das Warten ist also bezahlbar. Der Schalter
bleibt Voraussetzung: wer ihn aus hat, bekommt weiterhin überall Vsync.

**2. Die Wiederholrate der gehaltenen Richtungstaste war geraten.** Feste
0,08 s heißen 12,5 angeforderte Schritte pro Sekunde — unabhängig davon,
ob ein Aufbau 3 ms kostet (CRT, leichter Pfad) oder 110 ms (HDMI, voller
Aufbau mit Cover). Beides ist falsch:

- **zu langsam**, wo mehr ginge (CRT könnte 25/s);
- **zu schnell**, wo es nicht reicht — es kommen mehr Schritte herein,
  als gezeichnet werden können. Der Überschuss verschwindet nicht, er
  **staut sich**: die Liste läuft nach dem Loslassen noch weiter. Genau
  das nimmt man als Lag wahr.

Das Frontend misst jetzt, wie lange Verarbeitung und Neuzeichnen
tatsächlich gedauert haben, und leitet die Wiederholrate daraus ab —
mit denselben Zeitstempeln, die der Ruckler-Detektor ohnehin nimmt, also
ohne eine einzige zusätzliche Zeitabfrage. Bewusst asymmetrisch:
hoch/runter darf dadurch **schneller** werden, links/rechts nicht. Bei
einem Seitensprung ist nicht die Rechenzeit die Grenze, sondern das
Lesen — schnellere Hardware ändert daran nichts.

Abgesichert nach oben (Deckel bei 0,5 s, damit eine langsame Phase die
Bedienung nicht festnagelt), nach unten (nie schneller als 25 Schritte/s),
gegen Unsinn (Uhrensprung, ein zwischendurch gestartetes Spiel) und gegen
einzelne Ausreißer (gleitendes Mittel über acht Aufbauten).

Neuer Test: `tools/test_vsync_und_wiederholrate.py` (14 Prüfungen).
Nebenbei ein Fehlalarm im Skript-Test korrigiert — `read -r -n 1`
(beliebige Taste abwarten, ohne Variable) wurde als ungeprüfte Eingabe
gemeldet, weil die Suche die Ziffer `1` für einen Variablennamen hielt.


**Der eigentliche Fehler: Cover, die genau in den Kasten passen, landeten
nie im Zwischenspeicher** (Build 92 — gefunden durch die
Nutzer-Beobachtung: „Das passiert bei NES, Master System, Atari 2600,
Atari 5200, Jaguar, Sega 32X, Arcade … was mir aufgefallen ist, dass die
Boxarts in diesen Kategorien andere **Größen** haben im Gegensatz zu den
anderen — kann es daran liegen?"):

**Ja, genau daran.** Beim Einpassen eines Covers gibt es drei Fälle, und
einer davon fiel durchs Raster:

| Cover | Was passiert | Kam in den Cache? |
|---|---|---|
| größer als der Kasten | verkleinern | ja |
| viel kleiner (ganzzahlig ≥ 2×) | hochskalieren | ja |
| kleiner, aber Faktor 1 | bleibt unverändert | **nein** |

Der dritte Fall war sogar ausdrücklich so gebaut, mit der Begründung „das
Bild passt genau, ein Eintrag wäre byte-identisch zum Original". Der
erste Halbsatz stimmt — der Schluss war falsch, wegen zweier Folgen:

1. `thumb_cache_has()` meldet für dieses Cover **für immer** „nicht da".
   „Miniaturen vorbereiten" rechnete es bei **jedem** Durchlauf neu und
   hakte es nie ab. Diese Systeme konnten durch das Vorbereiten
   überhaupt nicht schneller werden — egal wie oft man es laufen ließ.
2. Der Treffer auf der Karte wird **vor** der Überspring-Prüfung
   abgefragt. Ohne Eintrag lief jeder Aufruf in diese Prüfung, und sobald
   der Rohbild-Cache (60 Einträge) das Cover verdrängt hatte, wurde beim
   Scrollen wieder übersprungen — das gemeldete Aufblitzen und
   Nachladen. In einer Liste mit 269 Einträgen passiert das ständig.

Betroffen war damit genau ein schmales Größenband, und deshalb traf es
nur die Systeme, deren Scans zufällig darin liegen. Beide Stellen
(Zeichenpfad und Vorbereitung) legen den Eintrag jetzt an.

**Ein bestehender Test hielt den Fehler fest, statt ihn zu finden:**
`test_cover_prewarm.py` prüfte wörtlich „passt das Bild exakt, wird
nichts abgelegt". Die Zusage ist umgedreht und mit der Begründung
versehen, warum der Eintrag gebraucht wird, obwohl er byte-identisch
ist. Dazu neu `test_thumb_verdraengung.py` Test 13, der alle drei
Größenfälle durchspielt und prüft, dass keiner davon beim Scrollen mehr
übersprungen wird.

**Praktische Folge:** nach dem Umstieg einmal „Miniaturen vorbereiten"
laufen lassen. Für die betroffenen Systeme entstehen dabei erstmals
Einträge — der Zwischenspeicher wächst also etwas, dafür sind diese
Kategorien danach genauso schnell wie alle anderen.

**Zwischenspeicher von Hand leeren, und eine Bilanz statt eines Gefühls**
(Build 91 — Nutzerwunsch: „Vielleicht sollten wir noch einbauen, dass
man per Hand den Cache für SD sowie HD unter System/Wartung einmal
leeren kann. Irgendwie hab ich das Gefühl, dass der letzte Build nicht
greift, was das Scrollen angeht."):

**1. Neuer Menüpunkt unter Wartung: „Miniaturen-Zwischenspeicher leeren
(CRT / HDMI)".** Getrennt nach Modus — wer nur HDMI fährt, wird die
CRT-Hälfte los, ohne die andere anzufassen. Die Auswahl nennt gleich die
Zahlen mit („CRT (SD): 12.482 Dateien, 1,8 GB"), und die sind der
eigentliche Wert dieses Bildschirms: wer wissen will, ob der
Zwischenspeicher überhaupt gefüllt ist, sieht es hier, ohne die
SD-Karte an den Rechner zu stecken. Gelöscht werden ausschließlich
`.art`- und liegengebliebene `.art.tmp`-Dateien; alles andere bleibt
unangetastet.

**2. Eine Trefferbilanz im Log.** Die Frage „greift der Cache?" war
bisher nur über Umwege zu beantworten. Jetzt schreibt das Frontend alle
50 Vorgänge eine Zeile:

    THUMB_CACHE Bilanz: 312 Treffer, 47 Fehltreffer (86% Treffer)

Steht dort eine hohe Trefferquote, ist der Zwischenspeicher warm und ein
Ruckeln hat eine andere Ursache. Steht dort eine hohe Fehltrefferquote,
wird tatsächlich neu gerechnet — und dann lohnt die Suche nach dem
Warum. Im Gegenzug ist die alte Einzelzeile je gezeichnetem Cover
standardmäßig **aus**: die lief bei jedem einzelnen Cover und hat in
einer langen Sitzung tausende Zeilen erzeugt, die das Interessante
zugedeckt haben.

**3. Die Kategorie-Logos werden gemessen.** Zum gemeldeten Hänger beim
Zurückgehen ins Hauptmenü: die Logos sind mit 900 Bildpunkten Breite die
größten Bilder im ganzen Frontend. Liegen sie im Zwischenspeicher,
kosten sie nichts — liegen sie nicht drin, sind es Hunderte
Millisekunden. Das stand in **keiner** Messung. Jetzt schreibt es sich
selbst ins Log, sobald es auffällig wird:

    PERF katlogo: 412 ms (PlayStation)

**4. Nebenbei korrigiert:** die Hinweiszeile der Ein-aus-N-Auswahl stand
fest auf „ESC: Einrichtung abbrechen" — außerhalb des
Einrichtungs-Assistenten schlicht falsch, und beim Leeren des
Zwischenspeichers klang es, als würde man die Einrichtung wegwerfen.

Nachgemessen wurde vorher: ein Durchlauf von „Miniaturen vorbereiten"
gefolgt von Blättern, Zurückgehen auf die Ordner-Ebene, Zurückgehen ins
Hauptmenü und erneutem Betreten der Kategorie ergibt in der Messumgebung
**null** Neuberechnungen. Der Mechanismus selbst ist also in Ordnung —
was auf dem Gerät passiert, muss die Bilanz zeigen.

**Select geht nicht mehr zurück** (Build 90 — Nutzervorschlag: „Das mit
Select funktioniert, aber dadurch dass Select noch die
Rückwärts-Funktion hat, ist es etwas blöde. Mein Vorschlag: die
Zurück-Funktion von Select runternehmen, da wir diese ja eh auf dem
Joypad mit B schon haben."):

Er hat recht, und der Grund fiel erst beim Benutzen auf: seit Build 88
ist Select ein Modifikator. Wer ihn hält und sich dann anders
entscheidet, löste beim Loslassen ein „eine Ebene zurück" aus, das er
nie wollte. Zwei Bedeutungen auf einer Taste, von denen eine ohnehin
doppelt vorhanden ist (B), sind eine zu viel.

Statt einer toten Taste zeigt Select allein jetzt kurz die Kombinationen
an: „Select halten + A = Suche, + X = RA-Schaukasten". Das ist genau die
Entdeckbarkeit, um die es bei dem ganzen Umbau ging — bisher musste man
in die Hilfe schauen, um überhaupt zu wissen, dass es die Kombinationen
gibt.

**Die Boxart-Spalte wird ruhiger** (Build 89 — vier Rückmeldungen in
einer Nachricht):

**1. Kein Aufblitzen von „kein Artwork" mehr.** („Wenn ich durch die
ROMs scrolle, etwas langsamer, ploppt immer erst ‚kein Artwork' auf und
dann wird das Cover nachgeladen.") `get_scaled()` lieferte `None` für
zwei völlig verschiedene Fälle: „es gibt kein Cover" und „ich habe es
während des Scrollens bewusst übersprungen, es kommt in rund 150 ms"
(COVER_SETTLE). Der Zeichenpfad konnte die beiden nicht unterscheiden
und malte auch im zweiten Fall den Platzhalter — der Sekundenbruchteile
später vom Cover ersetzt wurde. Ein Zähler trennt die Fälle jetzt; beim
Überspringen bleibt die Karte einfach leer, bis das Cover da ist.

**Wichtig dazu:** dass das überhaupt so oft passiert, heißt, dass der
Miniaturen-Zwischenspeicher für diese Cover leer ist — bei einem Treffer
gibt es gar keine Verzögerung. **Build 86 hat die Kastenhöhen geändert,
damit sind alle vorher erzeugten Einträge ungültig.** Nach dem Umstieg
auf 86 oder neuer muss „Miniaturen vorbereiten" einmal neu laufen.

**2. Der Platzhalter ist kein blauer Block mehr.** („Wenn ein ROM
wirklich kein Artwork hat, die Box bitte so anpassen, dass das nicht
immer auf die große blaue umspringt — das ist optisch nicht schön und
könnte auch Performance-Einbußen bedeuten.") Er war eine vollflächig
gefüllte Fläche in der Akzentfarbe, so groß wie das Cover geworden wäre.
Jetzt ein dünner Rahmen mit dem Hinweis mittig darin. Nachgemessen:
**8.772 statt 537.387 gefärbte Bildpunkte** auf HDMI, also rund ein
Einundsechzigstel — der Verdacht mit der Performance war berechtigt.

**3. Reine Ordnerlisten bekommen keine Boxart-Spalte mehr.** („Wenn ich
in eine Kategorie reingehe und nur die Ordnerauswahl dort sehe, braucht
daneben keine Artwork-Box stehen.") Ordner haben praktisch nie ein
eigenes Cover; die Spalte zeigte dort fast immer nur den Platzhalter und
nahm der Liste dafür knapp die Hälfte der Breite weg. Gemischte Ebenen
(Ordner und Spiele nebeneinander) behalten sie, ebenso „Zuletzt
gespielt". Die Bedingung stand vorher an vier Stellen im Code
handgeschrieben und steht jetzt in einer Funktion — laufen die
auseinander, berechnet der Vorauslader Miniaturen unter einer
Kastengröße, die der Zeichenpfad nie abfragt.

**4. Die Kategorie merkt sich, wo man war.** Für Unterordner gab es das
längst (`_nav_position_stack`), eine Ebene höher nicht: wer SNES bis
„Super Mario World" durchblättert, zurück zu den Kategorien geht und
wieder in SNES hinein, stand wieder bei „1942". Gemerkt wird nur die
Position auf der obersten Ebene, nicht der zuletzt geöffnete Unterordner
— sonst käme man ohne Herausklicken nicht mehr an die oberste Ebene.
Nach einem Neu-Einlesen werden die gemerkten Positionen verworfen, weil
sich dann auch die Kategorie-Nummerierung verschieben kann.

Neu: `tools/test_ruhige_boxspalte.py`. Gesamtstand: 24 Testskripte, alle
grün.

**Suche und Schaukasten jetzt auch mit dem Pad, Hilfe überarbeitet,
Nachladen ohne Umweg** (Build 88 — Nutzerwunsch: „Suche per Pad, mit der
Tastenkombi Select gedrückt halten und A drücken wäre super. Schaukasten
dann Select und X. Die Hilfe muss eh überarbeitet werden, da stehen
Sachen drin die sind nicht mehr aktuell. Boxarts nachladen sowie
Spieledaten nachladen ebenso machen"):

**1. Fünf Funktionen waren nur mit Tastatur erreichbar.** Durchgezählt:
Volltextsuche (`/`/F2), Buchstabensprung (alle Buchstabentasten),
Zufallsspiel (F11), Durchgespielt-Markierung (F7) und der RA-Schaukasten
(F6). Am Pad belegt waren nur A, B, X, Y, Start, Select, L/R, L2/R2 und
Mode — wer mit dem Controller auf dem Sofa sitzt, konnte in einer Liste
mit tausenden Einträgen also ausschließlich seitenweise blättern.

Freie Pad-Tasten gibt es keine mehr, deshalb ist **Select jetzt ein
Modifikator**: gehalten und mit A kombiniert öffnet es die Suche, mit X
den RA-Schaukasten. Select allein wirkt unverändert wie Zurück — nur
wird es jetzt erst beim **Loslassen** gemeldet und nur dann, wenn
zwischendurch keine Kombination ausgelöst hat. Ohne diesen Kniff käme
nach jeder Suche zusätzlich ein „eine Ebene zurück" hinterher. Die
Zuordnung hängt an der Zielaktion der zweiten Taste, nicht an ihrem
Tastencode: wer sich über „Tastenbelegung anpassen" eine eigene Belegung
eingerichtet hat, behält die Kombination.

**2. Ein Buchstabenraster für die Suche per Pad.** Mit dem D-Pad
bedienbar, A wählt, B geht zurück, das Feld OK beendet. Es schreibt in
dieselbe Anfrage und ruft dieselbe Sprungrechnung auf wie die Tastatur —
neue Suchlogik gibt es keine. Die Feldgröße wird aus dem verfügbaren
Platz gerechnet statt fest gesetzt: auf CRT stehen abzüglich Overscan
rund 278 Bildpunkte zur Verfügung, auf HDMI knapp 1700. Wer eine
Tastatur hat, tippt weiter einfach los und bekommt das Raster gar nicht
zu sehen.

**3. Die Hilfe stimmte an mehreren Stellen nicht mehr.** Gegen die
tatsächliche KEYMAP geprüft und korrigiert:

- „Esc oder F10 (ca. 0,6s halten)" als Ausstieg — **F10 ist seit Build
  77 ersatzlos entfallen** (es lief über die evdev-Ebene, die MiSTer
  während eines Cores sperrt, und die HID-Prüfung dafür verglich
  versehentlich F11). F1 hat die Aufgabe übernommen und stand bisher gar
  nicht in der Hilfe. Jetzt: F1 sofort, Esc mit Haltezeit daneben — mit
  der Begründung, warum ausgerechnet Esc eine Haltezeit behält (viele
  Spiele benutzen Esc selbst für ihr Pausenmenü).
- „F5 (Tastatur, ca. 0,6s halten)" für den Reset — seit Build 75 ist
  `RESET_HOLD = 0.0`, der Reset löst beim ersten erkannten Tastendruck
  aus.
- „Start + Select (Pad, ca. 0,8s halten) — Sofort zurück ins Menü" stand
  da, als wäre es ein gleichwertiger Weg. Ist es nicht: MiSTer sperrt
  während eines laufenden Cores die evdev-Ebene exklusiv, und bei den
  bisher getesteten Controller-Empfängern kam auch über den
  hidraw-Kanal nichts an. Der Code-Zweig bleibt als Absicherung
  bestehen, die Hilfe verkauft ihn aber nicht mehr als sichere Zusage.
- „Y / F5" für den nächsten Musiktitel — Y ist die **Pad**-Taste; die
  Tastatur-Y-Bindung wurde schon immer von der Buchstabensprung-Schleife
  überschrieben. Steht jetzt so da.
- F7 und F11 sind als „nur Tastatur" gekennzeichnet, statt so zu tun,
  als gäbe es sie überall.

**4. Boxarts und Spieledaten nachladen — ohne Umweg.** Beide Skripte
liefen bisher **nur** im Ersteinrichtungs-Assistenten (Schritt 4 und 5).
Wer später nachladen wollte, musste entweder den ganzen Assistenten
erneut durchlaufen oder das Frontend verlassen und das Skript im OSD
starten. Jetzt stehen sie als eigene Punkte unter Wartung; das Profil
(sd/hd) bestimmt `crt_menu_active()`, seit Build 83 verlässlich, es wird
also nichts mehr gefragt. Nach dem Nachladen wird die Spieleliste neu
eingelesen — sonst zeigt sie weiter die alten Daten.

Neu: `tools/test_pad_bedienung.py` mit neun Prüfgruppen (Modifikator,
beide Kombinationen, Umbelegbarkeit, abgezogenes Pad, Raster,
Zeichnen in allen Auflösungen, Suchsprung, Hilfe gegen die Wirklichkeit,
Menüpunkte). Gesamtstand: 23 Testskripte, alle grün.

**System-Hintergrundbilder komplett entfernt** (Build 87 —
Nutzerentscheidung: „großen Systembildhintergrund komplett rausnehmen,
war eh blöde"):

Die Bilder aus `/media/fat/frontend/bg/` hatten zwei Auftritte, und
beide kosteten Leistung:

**1. Bildschirmfüllend hinter der Spieleliste.** Der Puffer wurde bei
jedem Kategoriewechsel neu zusammengesetzt — bei 1920×1080 sind das
8,3 MB, zeilenweise in Python, in der Sandbox gemessene 41–67 ms und auf
der MiSTer-CPU entsprechend mehr. Das war auch der Grund für das kurze
Hängen beim Zurückgehen aus einem ROM-Ordner. Dazu hielt `BgCache` bis
zu vier solcher Vollbildpuffer im Speicher, bei 1080p rund 33 MB.

**2. Klein in der Boxart-Spalte**, als Ersatz für ein fehlendes Cover.
Das war mit 200–700+ ms je Skalierung die teuerste Einzeloperation im
ganzen Frontend — und sie wurde von **keinem** Vorauslader erfasst:
„Miniaturen vorbereiten" läuft nur über Einträge mit Cover-Pfad, und
geschützt vor der Verdrängung war das Ergebnis auch nicht. Man konnte
den Durchlauf komplett abwarten und trotzdem bei jedem Spiel ohne
eigenes Cover — und bei jedem Ordner, denn Ordner haben praktisch nie
eins — in dieselbe halbe Sekunde Wartezeit laufen.

Fehlt ein Cover, erscheint jetzt der schlichte Platzhalter. Weg sind
damit: `BgCache` und `BG_BASE` in `fe/art.py`, das `_cur_bg`-Kopieren im
Zeichenpfad, der Menüpunkt „System-Hintergrundbilder", die
Einstellungsdatei `system_bg_disabled` und der `bgbild=`-Posten aus den
PERF- und RUCKLER-Zeilen im Log. Der Ordner
`/media/fat/frontend/bg/` wird nicht mehr gelesen und kann gelöscht
werden.

**Ordnerzeilen kommen jetzt in die Miniaturen-Vorbereitung** (Build 87,
derselbe Zusammenhang): `_alle_spiel_eintraege()` stieg zwar in jeden
Unterordner ab, nahm aber nur dessen **Inhalt** mit — der Eintrag, der
den Ordner in der Liste darstellt, kam nie vor. Ein Ordner mit eigenem
Artwork wurde deshalb nie vorberechnet, egal wie oft man den Durchlauf
startete. Jetzt ist er dabei, mit exakt demselben Eintrag, den auch die
Anzeige benutzt.

Neu: `tools/test_kein_systemhintergrund.py` prüft die Abwesenheit statt
des Aussehens — kein `BG_BASE`/`BgCache`/`_cur_bg` mehr im Code, genau
ein Bildversuch bei einem Eintrag ohne Cover, gleicher Hintergrund für
verschiedene Systeme, kein `system_bg` im Menübaum. Gesamtstand: 22
Testskripte, alle grün.

**Der Boxart-Kasten hat nur noch drei Höhen** (Build 86 — Nutzerwunsch:
„ich möchte bitte die drei Stufen einbauen … zudem habe ich den
Eindruck, dass das mit dem Miniaturen vorbereiten nicht richtig klappt —
wenn das durchgelaufen ist und ich gehe in irgendein System und blättere
durch die ROMs, kommt es mir so vor, als würde das Frontend immer noch
nachjustieren"):

Der Eindruck stimmte, und er hatte eine handfeste Ursache. Die Höhe des
Boxart-Kastens richtete sich nach dem **Text darunter** — je mehr Zeilen
Spieler/Jahr/Genre/Hersteller, desto flacher der Kasten. Dieser Text
ändert sich aber im Betrieb: startet man ein Spiel zum ersten Mal, kommt
„Gespielt: 12 min" als zusätzliche Zeile dazu, später „Durchgespielt",
und der RA-Fortschritt wandert. Jede dieser Zeilen machte den Kasten um
eine Zeilenhöhe kleiner — und weil die Kastenhöhe im Cache-Schlüssel
steckt, war die beim „Miniaturen vorbereiten" berechnete Miniatur damit
wertlos und musste neu skaliert werden. Genau das fühlt sich beim
Blättern an wie Nachjustieren.

Nachgerechnet gab es bis zu **zwölf** verschiedene Kastenhöhen (CRT
68–165, HDMI 513–772). Jetzt sind es **drei feste Stufen** (CRT
63/114/165, HDMI 513/642/771): eine Textzeile mehr oder weniger bleibt
fast immer in derselben Stufe, die vorbereitete Miniatur passt weiter.
Nebenbei sieht die Liste ruhiger aus, weil die Karte beim Durchblättern
nicht mehr bei jedem Spiel eine andere Höhe hat.

Die unterste Stufe ist bewusst so gewählt, dass auch der **längste
mögliche** Text noch vollständig hineinpasst (3 Titelzeilen + 7
Infozeilen). `tools/test_kastenstufen.py` prüft beide Zusagen über den
kompletten Kombinationsraum aus Titellänge, Metadaten, Spielzeit,
Durchgespielt und RA-Fortschritt: höchstens drei Höhen, und der Text
passt in jedem einzelnen Fall.

**Getrennte Zwischenspeicher für CRT und HDMI, Obergrenze auf 40.000**
(Build 85 — Nutzerwunsch: „Obergrenze auf 40000 erhöhen und bitte für
jeden Modus, also CRT und HDMI, einen eigenen Cache anlegen — quasi
einmal SD-Variante für CRT-Modus und einmal HD-Variante für
HDMI-Modus"):

**1. Zwei getrennte Ablagen.** Statt eines gemeinsamen Ordners jetzt
`thumb_cache/hd/` und `thumb_cache/sd/`, gewählt beim Start nach
derselben Bedingung wie die Cover-Quelle (ab 720 Bildzeilen HD). Wer nur
einen Modus benutzt, kann den anderen in einem Rutsch löschen, und eine
lange HDMI-Sitzung verdrängt die CRT-Einträge nicht mehr nach und nach.

**2. Obergrenze 20.000 → 40.000, und zwar je Modus.** Beim Nutzer
klebten 20.008 Dateien exakt an der alten Grenze — 10.000 Spiele mit
Cover in zwei Modi sind eben 20.000 Einträge. Im Extremfall können jetzt
80.000 Dateien zusammenkommen: bei grob 150 KB je HDMI- und 15 KB je
CRT-Miniatur rund 6,6 GB. Auf einer 128-GB-Karte unkritisch, auf einer
kleinen nicht — der Wert steht als eine Konstante in `fe/art.py`, und
die tatsächliche Belegung steht nach jedem Durchlauf im Log.

**3. 256 Unterordner statt einer flachen Ablage.** Das ist der Haken an
der größeren Obergrenze: `/media/fat` ist üblicherweise exFAT, und dort
ist das Nachschlagen in einem Verzeichnis **linear** — jedes Öffnen
läuft die Einträge durch. 40.000 Dateien in einem Ordner wären doppelt
so teuer wie die bisherigen 20.000 gewesen. Die Dateien liegen jetzt
nach den ersten zwei Zeichen ihres Schlüssels verteilt
(`hd/a7/a7f3….art`), das sind rund 156 Einträge je Ordner statt 40.000.
Gemessen im Test: 2000 Schlüssel verteilen sich auf alle 256 Ordner.

**4. Die alte, flache Ablage wird aufgeräumt.** Die Dateien der
Vorgängerfassung liegen am falschen Ort und werden nie wieder gefunden;
sie werden beim ersten Start nach dem Update im Hintergrund entfernt,
statt für immer Platz zu belegen.

**Die Kategorie-Logos wurden weggeworfen, WEIL sie gerade benutzt
wurden** (Build 84 — Nutzer-Rückmeldung: „bei Virtual Boy, SNES-Tracker
etc. so viel ms, warum? Dachte das ist alles im Cache und dann solche
Ausreißer?"):

Im Log standen diese zwei Zeilen:

```
01:00:16  THUMB_CACHE Treffer: 6.3ms (ATARI2600.art, 304x792)
12:48:33  PERF cover: 1732 ms (ATARI2600.art)
```

**Der entscheidende Hinweis kam vom Nutzer selbst:** „wenn das an der Uhr
liegt, die aktualisiert sich ja immer erst nach ein paar Sekunden. Ich
starte das Frontend, dann steht da 1.00, dann nach ein paar Sekunden
springt sie auf die tatsächliche Uhrzeit." Die beiden Zeilen liegen also
nicht zwölf Stunden auseinander, sondern **Sekunden**.

**1. Die Ursache.** Der MiSTer hat keine batteriegepufferte Uhr. Die
Verdrängung im Miniaturen-Zwischenspeicher benutzt die Änderungszeit der
Cache-Datei als „zuletzt benutzt"-Marke und setzte sie bei jedem Treffer
per `os.utime` auf die **aktuelle** Systemzeit. Beim Start ist das 01:00.
Springt die Uhr danach auf 12:48, liegen ausgerechnet die eben gelesenen
Dateien zwölf Stunden in der Vergangenheit — sie sind schlagartig die
ältesten im ganzen Zwischenspeicher und fliegen als Erste raus. Die
Umkehrung dessen, was eine Verdrängung tun soll. Jetzt wird vor dem
Stellen der Uhr keine Marke gesetzt; die in dieser Zeit berührten
Einträge werden nachgeholt, sobald NTP fertig ist.

**2. Die Kategorie-Logos sind jetzt geschützt.** Rund vier Dutzend
Dateien, aber die teuersten Neuberechnungen im ganzen Frontend (auf dem
Gerät 1,4–3,7 Sekunden je Logo, weil sie mit 900 px die größten Bilder
sind) — und sie stehen auf genau der Seite, die man beim Start sieht.
Sie werden nie mehr verdrängt.

**3. Die Verdrängung räumt auf Vorrat.** Vorher wurde exakt auf die
Obergrenze heruntergeräumt: bei vollem Cache genau **ein** Eintrag je
Schreibvorgang, und dafür jedes Mal ein `listdir` plus ein `getmtime`
**je Datei** — bei 20.000 Dateien also 20.000 Systemaufrufe. Aus den
Messungen des Nutzers ließ sich das herausrechnen:

```
Zeit eines Fehltreffers = 1030 ms + 7,4 µs je Quellpixel
```

Die 1030 ms sind bildgrößen-**unabhängig**; das war genau dieser
Durchgang. Jetzt wird auf 90 % Zielfüllung geräumt, der teure Durchgang
läuft dadurch nur noch etwa alle 2000 Schreibvorgänge. Im Gegentest: 50
Verzeichnisdurchgänge bei 50 Schreibvorgängen vorher, 4 danach.

**4. Liegengebliebene Zwischendateien werden aufgeräumt.** Beim Nutzer
standen 20008 Dateien im Ordner bei einer Obergrenze von 20000 — die
überzähligen sind abgebrochene Schreibvorgänge (`.art.tmpPID_TID`), die
bisher niemand entfernt hat, weil die Verdrängung nur auf `.art` sah.

**Boxart-Download lud immer SD herunter, egal was man wählte**
(Build 83 — Nutzer-Rückmeldung: „egal ob ich Option 1 oder 2 auswähle,
der lädt immer nur Profil sd runter"):

**1. Die Ursache.** `read -r` entfernt den Zeilenumbruch, aber **kein
Wagenrücklauf-Zeichen**. Je nach Startweg (MiSTer-OSD, serielle Konsole,
SSH-Client) kommt die Eingabe als `"2\r"` an — und

```sh
case "2\r" in 2|hd|HD) PROFIL="hd" ;; *) PROFIL="sd" ;; esac
```

trifft den `*`-Zweig. Der bedeutete „sd". Nachgestellt: `"2"` → hd,
`"2 "` → hd (Leerzeichen stehen in `IFS`, die entfernt `read` selbst),
`"2\r"` → **sd**. Die Auswahl war also wirkungslos, und zwar lautlos.

**2. Nicht mehr stillschweigend durchfallen.** Eine nicht erkannte
Eingabe wird jetzt als solche gemeldet, statt kommentarlos SD zu
bedeuten. Genau dieses stille Durchfallen hat den Fehler unsichtbar
gemacht.

**3. Der Standard richtet sich nach der Wirklichkeit.** Er stand fest
auf SD. Jetzt kommt er aus dem tatsächlich eingestellten Menü-Modus (dem
`[Menu]`-Block der MiSTer.ini, dieselbe Quelle wie `crt_menu_active()`
im Frontend) — wer auf HDMI unterwegs ist, bekommt mit Enter auch HD.
Und die Startzeile nennt jetzt den Zielordner, sodass eine falsche Wahl
sofort auffällt.

**4. Dieselbe Falle an drei weiteren Stellen entschärft.**
`Frontend_Uninstall.sh` („auch eigene Daten löschen?") und zweimal
`MiSTer_RA.sh` verglichen ebenfalls exakt. Am unangenehmsten dort: ein
Wagenrücklauf wäre mit in `retroachievements.cfg` geschrieben worden und
**jeder Login hätte ohne sichtbaren Grund fehlgeschlagen**.

**Das Frontend ist nach „Miniaturen vorbereiten" nicht ins OSD
gesprungen — es ist abgestürzt** (Build 82 — Nutzer-Rückmeldung: „wenn
er mit Miniaturen erstellen fertig ist, springt das Frontend ins OSD.
Wenn ich dann das Frontend_Start.sh Script starte, geht er wieder ins
Frontend rein"):

**1. Der Absturz, und warum er wie eine Funktion aussah.** Der
Aufräum-Block in `run()` leert bei *jedem* Ende den Bildschirm und
injiziert F12, damit MiSTer sauber sein eigenes Menü zeigt. Ein Absturz
ist von außen dadurch nicht von einem gewollten Beenden zu
unterscheiden — deshalb hat das monatelang nach Bedienung ausgesehen
statt nach einem Fehler. Die Ursache ist nachgestellt und behoben: ein
Eintrag ohne Systemkey (Sonderkategorien wie *System* oder
*Zufalls-Zock* haben bewusst `syskey=None`) führte zu
`os.path.join(ART_BASE, None)` — ein **TypeError**, kein OSError, also
von keinem der bestehenden `except`-Zweige gefangen.

**2. Sicherheitsnetz.** „Miniaturen vorbereiten" ist eine reine
Bequemlichkeitsfunktion. Was darin schiefgeht, darf jetzt höchstens
diesen einen Vorgang kosten, niemals die laufende Sitzung — mit
vollständigem Fehlerbericht im Log, damit ein solcher Fall beim nächsten
Mal nachweisbar ist statt nur spürbar.

**3. Aus 52.000 werden die Cover, die es wirklich gibt**
(Nutzer-Rückmeldung: „wenn ich Miniaturen starte, steht da dann 178 von
52000, wobei die meisten ROMs kein Artwork besitzen"). 52.000 war die
Zahl *aller* Einträge *aller* Kategorien — dasselbe Spiel zählte dort
unter Favoriten, Zuletzt gespielt, Weiterspielen und in jeder Sammlung
erneut mit, dazu alle Menüpunkte, Scripts und Cores und alle Spiele ohne
Cover. Der Balken zeigte eine Arbeitsmenge, die es nie gab. Jetzt wird
zuerst die Liste der tatsächlich zu berechnenden Ziele aufgebaut;
Doppelte fallen dabei von selbst weg, weil zwei Einträge desselben
Spiels denselben Cache-Schlüssel ergeben.

**4. Aufgelaufene Tastendrücke werden verworfen.** Nach einem Vorgang,
der Minuten dauert, wurde alles, was in der Zwischenzeit gedrückt wurde,
beim Zurückkehren am Stück abgespielt.

**5. Das Log überlebt jetzt ein Update.** Es liegt unter `/tmp` (also im
RAM) und wurde von `Frontend_Update.sh` zusätzlich gelöscht — ausgerechnet
im einzigen Ablauf, der mit einem Neustart endet, war die Spur damit
garantiert vernichtet. Es wird jetzt vorher nach
`/media/fat/frontend/last_update.log` gerettet.

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
