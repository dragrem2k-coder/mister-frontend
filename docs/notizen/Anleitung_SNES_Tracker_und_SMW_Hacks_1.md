# Einrichtung: SNES ALTTP Tracker & SMW Hacks

Kurzanleitung für Dennsen86 – zwei neue Menüpunkte im MiSTer Custom Frontend (ab Version v4.2 mit den aktuellen Updates).

**Wichtig vorweg:** Beide Menüpunkte erscheinen nur, wenn die passenden Dateien wirklich an der richtigen Stelle liegen. Fehlt etwas, taucht der Menüpunkt einfach gar nicht erst auf – das ist normal und kein Fehler.

---

## 1. SNES ALTTP Tracker

Für automatisches Item-Tracking bei ALTTP-Randomizer-Seeds.

### Was angelegt werden muss

| # | Was | Wo genau |
|---|---|---|
| 1 | Core-Datei | `SNES_Tracker.rbf` nach `/media/fat/_Console/` kopieren |
| 2 | ROM-Ordner | `/media/fat/games/SNES/ZELDA_MSU/` anlegen (falls noch nicht vorhanden) |
| 3 | Seeds | Die ALTTPR-Seed-Dateien (`.sfc` / `.smc`) in genau diesen Ordner legen |

### Danach

- Frontend einmal neu starten (bzw. falls es schon läuft: kurz beenden und neu starten).
- Beim ersten Start nach dem Update kann ein einmaliger, kurzer Neuscan der Spieleliste passieren – normal, nur beim ersten Mal.
- Im Hauptmenü erscheint ein neuer Punkt **"SNES ALTTP Tracker"**. Dort stehen alle Dateien aus `ZELDA_MSU` zur Auswahl.
- Läuft `SNES_Tracker.rbf` **nicht** auf der SD-Karte, bleibt dieser Menüpunkt unsichtbar – dann bitte Schritt 1 prüfen.

### Hinweis

Dieses System hat **keine** RetroAchievements-Variante zur Auswahl – es startet immer direkt mit dem Tracker-Core.

---

## 2. SMW Hacks

Für Super-Mario-World-Hacks/Kaizo-Sammlungen – läuft mit dem ganz normalen SNES-Core (kein separater Core nötig).

### Was angelegt werden muss

| # | Was | Wo genau |
|---|---|---|
| 1 | ROM-Ordner | `/media/fat/games/SNES/SMW_HACKS/` anlegen (falls noch nicht vorhanden) |
| 2 | Hack-ROMs | Die SMW-Hack-Dateien (`.sfc` / `.smc`) in genau diesen Ordner legen |

Ein eigener Core ist **nicht** nötig – der normale SNES-Core (den du sowieso schon hast) reicht.

### Danach

- Frontend neu starten (einmaliger kurzer Neuscan wie oben).
- Im Hauptmenü erscheint ein neuer Punkt **"SMW Hacks"** mit eigener Farbgebung.
- Beim Öffnen erscheint – genau wie beim normalen SNES-Menüpunkt – die Auswahl **Standard-Core oder RetroAchievements-Core**, falls du den RA-SNES-Core installiert hast. Ohne RA-Core startet es einfach direkt mit dem Standard-Core.

---

## Kurz zusammengefasst

```
/media/fat/_Console/SNES_Tracker.rbf              <- Core für ALTTP Tracker
/media/fat/games/SNES/ZELDA_MSU/                  <- ALTTPR-Seeds hier rein
/media/fat/games/SNES/SMW_HACKS/                  <- SMW-Hacks hier rein (kein eigener Core nötig)
```

Beide ROM-Ordner liegen **unterhalb** des normalen SNES-Ordners, tauchen aber **nicht** zusätzlich in der normalen SNES-Liste auf – jedes System hat seine eigene, klar getrennte Übersicht.

Bei Fragen oder falls ein Menüpunkt nicht erscheinen will: kurz Bescheid geben, dann schauen wir uns das gemeinsam an.
