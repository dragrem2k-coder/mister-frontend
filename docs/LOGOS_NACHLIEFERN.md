# Kategorie-Logos für die neuen Systeme

Mit Build 79 kennt das Frontend 48 Spielesysteme. **24 haben ein Logo,
24 nicht** — die zeigen bis dahin den dezenten Platzhalter. Das ist kein
Fehler und stört nichts; die Kategorie funktioniert vollständig.

Acht Logos, die schon länger im Repo lagen
(`frontend/sysart/_weitere_systeme_noch_nicht_unterstuetzt/`), sind
dabei automatisch an ihren Platz gerückt: Atari 5200/7800, Jaguar,
ColecoVision, CD-i, Sega 32X, Super Game Boy und TurboGrafx-CD.

## Format

Genau wie die vorhandenen Logos:

| | |
|---|---|
| Breite | **900 Pixel** (Höhe frei — die vorhandenen liegen zwischen 128 und 403) |
| Hintergrund | **RGB 28, 32, 44** — dieselbe Farbe wie bei den bestehenden, sonst hebt sich das Logo als Kasten ab |
| Format | `.art` (ART1), erzeugt mit `PC-Tools/art_convert.py` |

## Umwandeln

```bash
python PC-Tools/art_convert.py --images mein_logo.png --out NEOGEOCD.art --profile hd
```

Die fertige Datei nach `frontend/sysart/` (im Repo) bzw.
`/media/fat/frontend/sysart/` (auf dem MiSTer) legen. **Der Dateiname
muss exakt der Systemschlüssel sein** — die Liste steht unten.

## Was noch fehlt

| System | Dateiname |
|---|---|
| 3DO | `3DO.art` |
| Adventure Vision | `ADVENTUREVISION.art` |
| Arcadia 2001 | `ARCADIA.art` |
| Astrocade | `ASTROCADE.art` |
| Atari 2600 | `ATARI2600.art` |
| Atari Lynx | `ATARILYNX.art` |
| Casio PV-1000 | `CASIOPV1000.art` |
| Channel F | `CHANNELF.art` |
| CreatiVision | `CREATIVISION.art` |
| Famicom Disk System | `FDS.art` |
| Gamate | `GAMATE.art` |
| Game & Watch | `GAMENWATCH.art` |
| Game Gear | `GAMEGEAR.art` |
| Intellivision | `INTELLIVISION.art` |
| Mega Duck | `MEGADUCK.art` |
| Neo Geo CD | `NEOGEOCD.art` |
| Odyssey 2 | `ODYSSEY2.art` |
| Pocket Challenge V2 | `POCKETCHALLENGEV2.art` |
| Pokemon Mini | `POKEMONMINI.art` |
| SG-1000 | `SG1000.art` |
| VC 4000 | `VC4000.art` |
| Vectrex | `VECTREX.art` |
| WonderSwan | `WONDERSWAN.art` |
| WonderSwan Color | `WONDERSWANCOLOR.art` |

Der Reihe nach ist völlig in Ordnung — jede Datei wirkt sofort, ohne
dass am Code etwas geändert werden muss. Eine Akzentfarbe hat jedes
dieser Systeme bereits (siehe `SYSTEM_ACCENT` in `frontend.py`); sie
umrahmt das Logo und färbt die Auswahl in der Liste.
