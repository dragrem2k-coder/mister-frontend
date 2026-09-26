# Changelog

Kurz gehalten: je Version ein Block mit dem, was man merkt.

Wer die Details will — welche Messung wozu geführt hat, welcher Versuch
danebenging, was ein Test gefunden hat — findet sie im
[ausführlichen Archiv](docs/CHANGELOG_ARCHIV.md) (alle Builds seit v1.1).

English: [`CHANGELOG_EN.md`](CHANGELOG_EN.md)

---

## Nach v4.6 — noch nicht veröffentlicht

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
