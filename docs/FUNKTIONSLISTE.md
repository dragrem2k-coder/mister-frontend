# Dragend - was das Frontend alles kann

Vollstaendige Liste aller Funktionen und Einstellungen.

**Diese Datei ist erzeugt, nicht geschrieben.** Das Systemmenue
unten kommt aus `fe.menu.system_items()` - also aus genau dem
Code, der die Eintraege im Betrieb baut. Tasten, Schalterdateien
und Aufruf-Optionen sind aus dem Quelltext gelesen. Zum Schluss
laeuft eine Gegenprobe in beide Richtungen: fehlt ein Eintrag
oder steht einer zuviel darin, wird die Datei nicht geschrieben.

Neu erzeugen: `python3 tools/liste_erzeugen.py`

---

## 1. Die drei Ansichten

Jede Liste kann in drei Ansichten angezeigt werden; umgeschaltet
wird mit **F10** oder ueber das Kontextmenue (*Ansicht
wechseln*).

| Ansicht | Was man sieht |
|---|---|
| **Liste** | eine Zeile je Eintrag, rechts die Boxart des markierten Spiels |
| **Raster** | Kacheln mit Cover, mehrere Spalten |
| **Galerie** | grosse Cover, eines im Mittelpunkt |

Dazu zwei Seiten: die **Hauptseite** mit den Kategorien und die
**Spieleliste** innerhalb einer Kategorie. Beide haben ihre
eigene Ansichts-Einstellung.

---

## 2. Das Systemmenue, Gruppe fuer Gruppe

Die Eintraege stehen in der Reihenfolge, in der sie im Menue
erscheinen. Texte mit `->` sagen, was ein Druck darauf tut;
Texte mit Zahlen oder Namen zeigen den aktuellen Stand und
schalten weiter.

### RetroAchievements (2 Eintraege)

- `RetroAchievements: nicht eingerichtet`
- `Popups & Anzeige: RA in MiSTer selbst nicht eingerichtet`

Ist RetroAchievements eingerichtet, stehen hier
zusaetzlich:

- `RetroAchievements: <Benutzername> (neu laden)`
- `RetroAchievements: AN -> ausschalten (Fortschritt/Abzeichen/Listen pausieren, RA-fähige Cores starten weiterhin normal)`
- `Popups & Anzeige (MiSTer-RA-Einstellungen)`

Und in **MiSTer selbst** (nicht im Frontend) muessen
Benutzername und Passwort in
`/media/fat/retroachievements.cfg` stehen - das
Frontend liest diese Datei, legt sie aber nie an und
aendert darin hoechstens die eine Zeile, um die es
gerade geht.

### Statistiken & Erfolge (6 Eintraege)

- `Top 10: meistgespielt`
- `Top 10: meistgestartet`
- `Meine Erfolge`
- `Mein Trophäenraum`
- `Jahresrückblick`
- `Spieltagebuch`

### Anzeige & Sound (33 Eintraege)

- `Menü-Video: HDMI -> auf CRT wechseln (Neustart)`
- `Farbschema: Dunkel (Standard) -> nächstes`
- `Aktuelle Farben als eigenes Schema speichern`
- `Eigenes Farbschema bearbeiten`
- `Navigations-Soundeffekte: AN -> ausschalten`
- `Boot-Logo: Dragend -> auf neutral wechseln`
- `Schnelles Scrollen: AUS -> einschalten (etwas Bildriss-Risiko gegen kürzere Scroll-Verzögerung)`
- `Cover beim Scrollen: AUS -> einschalten (Liste zeigt das Cover sofort, wie die Galerie)`
- `Cover verkleinern: weich (gemittelt) -> scharf (Pixel-Look, auf der Roehre oft besser)`
- `Schrift: eigene`
- `Feinheiten: AN -> ausschalten (Scrollbalken, Akzentbalken, Trennlinie)`
- `Hintergrundbild: keines gewaehlt`
- `Lochmaske: keine gewaehlt`
- `Ansicht Spieleliste: Liste -> weiter (F10, am Pad Select+Y, schaltet sofort um)`
- `Ansicht Hauptseite: Liste -> weiter (F10 auf der Hauptseite)`
- `Scrollgeschwindigkeit: 1x -> nächste`
- `Ordner: zuerst`
- `Favoriten zuerst: AUS`
- `Spielzahl am Ordner: AN`
- `Tastenlegende: AN`
- `Ausgeblendete Einträge (0) -> zeigen`
- `Rand seitlich: 7 % -> weiter (für Röhren, die links/rechts abschneiden)`
- `Rand oben/unten: 5 % -> weiter (für Röhren, die oben/unten abschneiden)`
- `Fremdes Artwork/Daten: AN -> ausschalten (füllt Lücken aus der MiSTer-docs-Datenbank, ersetzt nie eigenes)`
- `Menü-Auflösung: voll -> auf halb stellen (schnelleres HDMI, weicheres Bild, nach Neustart)`
- `Markierungs-Schimmer: AN -> ausschalten (feste statt animierte Hervorhebung)`
- `Equalizer-Balken: AN -> ausschalten (testen ob es beim HDMI-Scrollen hilft)`
- `Musik-Titel-Laufschrift: AN -> ausschalten (fest statt scrollend)`
- `Stream-Overlay: AUS -> einschalten (wirkt nach Neustart)`
- `Bildschirmspiegel: AUS -> einschalten (braucht Stream-Overlay, wirkt nach Neustart)`
- `Musik: an -> ausschalten`
- `Musik-Quelle: MP3`
- `Lautstärke: 100%`

### Optionen (16 Eintraege)

- `CRT-Testbild`
- `Miniaturen vorbereiten (einmalig, dauert einige Minuten)`
- `Miniaturen-Auftrag für PC schreiben`
- `Kuratierte Liste (nur DB-Treffer): AUS -> einschalten`
- `Beta/Proto/Demo und Nur-Japan ausblenden: AUS -> einschalten (aufgeräumtere Liste, dafür fehlen Dateien)`
- `Ordner mit nur einem Spiel: als Spiel anzeigen -> als Ordner belassen`
- `Hauptseite: Kategorien sortieren und ausblenden`
- `Zaparoo (NFC-Tags) ist nicht installiert`
- `Cores: Fassung je System waehlen`
- `update_all ist nicht installiert - beim MiSTer-Projekt holen und nach Scripts/ legen`
- `Attract-Modus (Bildschirmschoner): AN -> ausschalten`
- `Attract-Modus Verzögerung: 1.5min -> nächste`
- `Ziehung Spannung: 2.0s -> nächste`
- `Zeitzone: UTC -> nächste`
- `Beim Start auf NAS/Netzwerk warten: AUS -> einschalten (automatisch erkannt)`
- `Autostart: AUS -> einschalten (Frontend startet zusammen mit dem MiSTer)`

### Eingabe & Sprache (4 Eintraege)

- `Sprache: Deutsch -> auf Englisch wechseln`
- `Tastenbelegung anpassen`
- `Auf Standardbelegung zurücksetzen`
- `Bestätigen/Abbrechen vertauschen: AUS -> einschalten`

### Info (5 Eintraege)

- `Hilfe / Übersicht`
- `Einrichtung erneut starten`
- `Geheimnisse`
- `Mitwirkende`
- `Auf Updates prüfen: AN -> ausschalten`

### Wartung (11 Eintraege)

- `MiSTer-OSD öffnen (Settings/Buttons)`
- `ROM-Wächter: AN`
- `Mehrteilige Spiele bündeln: AN`
- `Spieleliste neu einlesen`
- `Miniaturen-Zwischenspeicher leeren (CRT / HDMI)`
- `JPEG-Arbeitskopien: AUS -> einschalten (legt beim Miniaturen-Vorbereiten je PNG-Cover eine .jpg daneben)`
- `Boxarts nachladen (braucht Netz, dauert etwas)`
- `Spieledaten nachladen (braucht Netz, dauert etwas)`
- `Anzeige neu aufbauen`
- `MiSTer neu starten`
- `Frontend beenden`

### Dazu drei Gruppen, die vom Geraet abhaengen

Sie stehen nicht oben, weil ihr Inhalt von der SD-Karte kommt
und nicht vom Frontend:

- **Cores** - alle gefundenen FPGA-Kerne, nach Art gruppiert
- **Standalone** - eigenstaendige Programme, nach ihren Ordnern
- **Scripts** - alles aus `/media/fat/Scripts`

---

## 3. Das Kontextmenue

Oeffnet sich mit **Y** (oder der Menue-Taste) auf einem Eintrag.
Was darin steht, haengt davon ab, worauf man steht - ein Spiel,
ein Ordner oder eine Kategorie.

- Anleitung anzeigen
- Favorit entfernen
- Als Favorit merken
- Nicht mehr durchgespielt
- Als durchgespielt merken
- Diesen Eintrag ausblenden
- Suchen
- Filter
- Zu Buchstabe springen
- Ansicht wechseln
- Zufälliges Spiel
- Zufälliger Favorit
- Diese Kategorie ausblenden

---

## 4. Die Tastenbelegung

Das ist die Belegung, wie sie im Quelltext steht. Jede davon
laesst sich im Menue unter *Eingabe & Sprache* -> 
*Tastenbelegung anpassen* aendern.

| Taste | Aktion | Was sie tut |
|---|---|---|
| `KEY_F10` | ansicht | Ansicht wechseln (Liste / Raster / Galerie) |
| `BTN_B` | back | zurueck |
| `KEY_F1` | back_fe | zum Frontend zurueck (waehrend ein Spiel laeuft) |
| `BTN_X` | back_fe | zum Frontend zurueck (waehrend ein Spiel laeuft) |
| `KEY_F7` | completed | als durchgespielt markieren |
| `KEY_DOWN` | down | eine Zeile nach unten |
| `BTN_DPAD_DOWN` | down | eine Zeile nach unten |
| `KEY_ESC` | exit | zurueck (Esc) |
| `KEY_F8` | favorite | als Favorit markieren |
| `BTN_TL2` | favorite | als Favorit markieren |
| `BTN_TR2` | favorite | als Favorit markieren |
| `AXIS_L2` | favorite | als Favorit markieren |
| `AXIS_R2` | favorite | als Favorit markieren |
| `KEY_TAB` | filter | Filter |
| `KEY_LEFT` | left | eine Seite zurueck (im Hauptmenue: Kategorie zurueck) |
| `BTN_TL` | left | eine Seite zurueck (im Hauptmenue: Kategorie zurueck) |
| `BTN_DPAD_LEFT` | left | eine Seite zurueck (im Hauptmenue: Kategorie zurueck) |
| `KEY_F4` | list_end | an das Ende der Liste |
| `KEY_F3` | list_start | an den Anfang der Liste |
| `BTN_Y` | music_next | naechster Titel |
| `KEY_F5` | music_next | naechster Titel |
| `KEY_NEXTSONG` | music_next | naechster Titel |
| `KEY_ENTER` | ok | oeffnen / starten / bestaetigen |
| `BTN_A` | ok | oeffnen / starten / bestaetigen |
| `BTN_START` | ok | oeffnen / starten / bestaetigen |
| `KEY_F12` | osd | MiSTers eigenes OSD oeffnen |
| `BTN_MODE` | osd | MiSTers eigenes OSD oeffnen |
| `KEY_F6` | ra_showcase | die Erfolge zum Spiel zeigen |
| `KEY_F11` | random | zufaelliges Spiel |
| `KEY_RIGHT` | right | eine Seite vor (im Hauptmenue: Kategorie vor) |
| `BTN_TR` | right | eine Seite vor (im Hauptmenue: Kategorie vor) |
| `BTN_DPAD_RIGHT` | right | eine Seite vor (im Hauptmenue: Kategorie vor) |
| `KEY_SLASH` | search | Suche |
| `KEY_F2` | search | Suche |
| `KEY_BACKSPACE` | search_backspace | in der Suche ein Zeichen zurueck |
| `BTN_SELECT` | select | Select (allein: zurueck; gehalten: Kombinationen) |
| `KEY_UP` | up | eine Zeile nach oben |
| `BTN_DPAD_UP` | up | eine Zeile nach oben |
| `A - Z, Leertaste` | letter:... | springt zum Buchstaben; in der Suche wird getippt (27 Tasten) |

### Select gehalten

| Kombination | Aktion |
|---|---|
| Select + back_fe | ra_showcase |
| Select + favorite | filter |
| Select + Links | list_start |
| Select + music_next | ansicht |
| Select + ok | search_pad |
| Select + Rechts | list_end |

---

## 5. Schalterdateien

Diese Schalter legt man von Hand an oder loescht sie wieder -
sie stehen in keinem Menue. Genau dafuer sind sie da: der Fall,
in dem man sie braucht, ist meist der, in dem man nicht ins
Menue kommt.

```
touch   /media/fat/frontend/<name>     # anlegen = einschalten
rm      /media/fat/frontend/<name>     # loeschen = ausschalten
```

- `anleitung_textmodus`
- `anleitung_tty1`
- `arbeitskopien_enabled`
- `artbox_aufschub_aus`
- `attract_disabled`
- `cover_sofort_enabled`
- `crt_menu_by_frontend`
- `crt_menu_pending_confirm`
- `curated_only`
- `dragend_logo_disabled`
- `einzelordner_aus`
- `eq_effect_disabled`
- `fast_scroll_enabled`
- `favoriten_zuerst`
- `feinheiten_aus`
- `flaechen_c_aus`
- `fremdquellen_aus`
- `hintergrund_aus`
- `konsole_mechanik_an`
- `konsole_mechanik_aus`
- `maske_aus`
- `multidisc_aus`
- `ordner_hinten`
- `ordner_zahlen_aus`
- `profile`
- `pulse_effect_disabled`
- `raster_klein`
- `rechteck_flip_aus`
- `rom_filter`
- `romwacht_aus`
- `screen_mirror_enabled`
- `setup_wizard_done`
- `stream_enabled`
- `tastenlegende_aus`
- `textkonsole_grafik_aus`
- `track_marquee_disabled`
- `verkleinern_scharf`

Namen auf `_aus` schalten etwas AB, wenn die Datei existiert.

### Und diese Dateien halten einen Wert oder Inhalt

Sie werden vom Menue geschrieben und stehen hier nur zur
Vollstaendigkeit. Von Hand anzulegen bringt nichts - eine leere
Datei ist ein Zustand, den das Menue nie herstellt. Loeschen
setzt die Einstellung dagegen gefahrlos auf die Vorgabe zurueck.

- `ansicht`
- `ansicht_haupt`
- `attract_delay`
- `bootanim`
- `flip_haeppchen`
- `flip_rueckleser`
- `hintergrund`
- `hintergrund_dim`
- `maske`
- `overscan`
- `schrift`
- `scroll_tempo`
- `theme`
- `ziehung_spannung`

---

## 6. Aufruf-Optionen

```
python3 /media/fat/frontend/frontend.py <option>
```

- `--bench`
- `--demo`
- `--help`
- `--show`

---

## 7. Die eingebaute Uebersicht

Das Frontend bringt seine eigene Hilfe mit, unter
*System -> Info -> Hilfe / Uebersicht*. Was dort steht:

- **/ oder F2 (Tastatur), Select+A (Pad)** - Spieleliste durchsuchen, springt zum ersten Treffer. Hoch/runter blättert durch die Treffer, der Balken zählt sie mit (3/17). Vom Pad aus erscheint ein Buchstabenraster auf dem Bildschirm (A wählt, B zurück, das Feld OK beendet)
- **Buchstabentaste (Tastatur)** - Springt zum nächsten Eintrag mit diesem Buchstaben
- **Esc (Tastatur, ca. 0,6s halten)** - Ebenfalls zurück ins Menü - Esc behält die Haltezeit, weil viele Spiele Esc selbst für ihr eigenes Pausenmenü benutzen
- **F1 (Tastatur)** - Sofort zurück ins Menü
- **F10 / Select+Y (Pad)** - Ansicht wechseln: Liste, Raster, Galerie (auch Hauptseite)
- **F11 (nur Tastatur)** - Zufälliges Spiel über alle Systeme starten
- **F12 / Mode-Taste (Pad)** - MiSTer-OSD öffnen (Joystick-Definition, Einstellungen)
- **F3 / F4 (Tastatur), Select+L / Select+R (Pad)** - An den Anfang / ans Ende der Liste springen
- **F5 (Tastatur)** - Laufenden Core zurücksetzen, ohne ihn neu zu laden (experimentell, RA-Fortschritt bleibt erhalten)
- **F6 (Tastatur), Select+X (Pad)** - RA-Erfolgs-Vitrine für das markierte Spiel
- **F7 (nur Tastatur)** - Durchgespielt-Status umschalten
- **F8 / L2 oder R2** - Favorit umschalten
- **Geheimnisse** - Verstecktes, das du selbst entdecken kannst
- **Mitwirkende** - Wer das gebaut hat
- **OK / A** - Auswählen, Kategorie/Ordner betreten
- **Pfeiltasten** - Bewegen
- **RA-Erfolgsjäger** - Offene Erfolge in deiner Bibliothek
- **Sammlungen** - Automatische Gruppierungen
- **Select (Pad)** - Zeigt die Kombinationen an; GEHALTEN ist Select der Umschalter für Select+A, Select+X und Select+L/R (zurück geht B)
- **Start + Select (Pad, ca. 0,8s halten)** - Funktioniert nur, wenn MiSTer den Controller nicht sperrt - bei den bisher getesteten Pads tut es das. Verlässlich ist der Ausstieg über die Tastatur.
- **Statistiken & Erfolge** - Top-10-Listen, Trophäenraum, Jahresrückblick, Spieltagebuch
- **Wartung** - Boxarts und Spieledaten nachträglich laden, Spieleliste neu einlesen, MiSTer-OSD öffnen
- **Weiterspielen** - Dein zuletzt offenes Spiel
- **Y (Pad) / F5 (Tastatur)** - Nächster Musiktitel (nur im Menü)
- **Zurück / B** - Eine Ebene zurück, ganz oben: Beenden-Dialog

---

## Was in dieser Liste NICHT steht

Damit auch das klar ist:

- **Was auf der Karte liegt** - Cores, Scripts, Standalone-
  Programme, Spiele, Cover. Das Frontend zeigt, was es findet.
- **Die Einstellungen von MiSTer selbst** (`MiSTer.ini`,
  Tastenbelegung der Kerne, Video). Das Frontend fasst dort
  genau eine Stelle an: den `[Menu]`-Block fuer den CRT-Modus,
  und das nur, wenn man es im Menue verlangt.
- **Was im Hintergrund laeuft** und keine Einstellung hat -
  Miniaturen, Vorauslader, der ROM-Waechter.
