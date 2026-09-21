# Messergebnisse

Gemessen mit dem eingebauten Bench (`python3 frontend.py --bench`, siehe
[README](../README.md#selbst-nachmessen---bench)).

English: [MEASUREMENTS.md](MEASUREMENTS.md)

## Gerät

| | |
|---|---|
| Hardware | DE10-Nano |
| System | Linux 5.15.1-MiSTer (armv7l), Python 3.9.6 |
| Anzeige | 1920×1080 |
| C-Modul | libdragend Version 3 |
| Bestand | 30 064 Spiele in 22 Kategorien |
| Stand | Build 179, 21.09.2026 |

## Bildkette — zwischen Geräten vergleichbar

Gerechnet an einem **erzeugten** Testbild von 1200×1600 Bildpunkten,
unabhängig davon, was auf der Karte liegt. Drei Läufe:

| | Lauf 1 | Lauf 2 | Lauf 3 |
|---|---|---|---|
| Verkleinern auf 578×770, Flächenmittel (C) | 114,50 ms | 111,70 ms | 112,13 ms |
| Verkleinern auf 578×770, Nearest (C) | 26,65 ms | 26,13 ms | 26,21 ms |
| Verkleinern auf 176×235, Flächenmittel (C) | 45,98 ms | 44,28 ms | 44,56 ms |
| Verkleinern auf 176×235, Nearest (C) | 3,89 ms | 3,81 ms | 3,93 ms |
| **C gegenüber Python** | **×121** | **×123** | **×124** |

Die drei Läufe liegen innerhalb von **2 %** beieinander.

578×770 ist der Kasten der Boxart-Spalte auf 1080p, 176×235 eine
Rasterkachel. „Nearest" ist das scharfe Verkleinern für Röhren
(*System → Anzeige & Sound*) — am großen Kasten 4,3-mal, an der Kachel
11-mal billiger als das weiche Mitteln.

| Miniatur-Cache (Lauf 3) | |
|---|---|
| Miniatur 578×770 packen und schreiben | 694 ms |
| Miniatur 578×770 lesen und entpacken | 90 ms |
| PNG 1200×1600 lesen und dekodieren | 259 ms |

## Start

| | Lauf 1 | Lauf 2 | Lauf 3 |
|---|---|---|---|
| Start bis Kategorien bereit | 3 411 ms | 3 525 ms | 3 482 ms |
| **je Spiel** | **0,114 ms** | **0,117 ms** | **0,116 ms** |

Hängt vom Bestand ab, deshalb auch je Spiel angegeben.

## Scrollen

Lauf 3, gemessen in der Kategorie Arcade (1027 Einträge), je Schritt,
**ohne** das Warten auf den Bildaufbau:

| Spieleliste | Cover muss erst gerechnet werden | Cover liegt im Speicher |
|---|---|---|
| Liste | 264 ms | 79 ms |
| Raster | 72 ms | 50 ms |
| Galerie | 183 ms | 104 ms |

| Hauptseite | kalt | warm |
|---|---|---|
| Liste | 50 ms | 32 ms |
| Raster | 44 ms | 42 ms |
| Galerie | 77 ms | 74 ms |

**Wichtig beim Lesen:** „Cover muss erst gerechnet werden" ist die
Obergrenze. Beim echten Scrollen lässt das Frontend die Boxart-Spalte
aus, solange schnell geblättert wird, und rechnet erst beim
Stehenbleiben. Nach *Miniaturen vorbereiten* liegt der Alltag zwischen
beiden Spalten.

| Bildtransport | |
|---|---|
| Ganzes Bild kopieren (7,9 MB) | 12,6 ms |
| Warten auf den Bildaufbau (60 Hz) | +13,0 ms |

## Wie die Zahlen entstanden sind

Die ersten beiden Läufe haben vor allem Fehler **im Messwerkzeug**
gefunden — unter anderem hat der Bench anfangs zufällig in einer
Kategorie mit einem einzigen Eintrag gemessen, also ein Standbild. Die
Scroll-Zahlen oben stammen deshalb nur aus Lauf 3. Die Bildkette war
davon nie betroffen, weil sie nicht vom Bestand abhängt — daher dort
alle drei Läufe.

Eigene Messungen auf anderen Geräten, Auflösungen oder Bestandsgrößen
sind willkommen: `--bench` laufen lassen und `/tmp/dragend_bench.txt`
schicken.
