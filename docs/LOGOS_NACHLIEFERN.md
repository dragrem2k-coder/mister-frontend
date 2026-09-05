# Kategorie-Logos für die neuen Systeme

Mit Build 79 kennt das Frontend 48 Spielesysteme. Build 80 bringt neun
weitere Logos mit, damit sind es **33 von 48**. Die restlichen **15**
zeigen bis auf Weiteres den dezenten Platzhalter. Das ist kein Fehler
und stört nichts; die Kategorie funktioniert vollständig.

Acht Logos, die schon länger im Repo lagen
(`frontend/sysart/_weitere_systeme_noch_nicht_unterstuetzt/`), sind
bereits mit Build 79 an ihren Platz gerückt: Atari 5200/7800, Jaguar,
ColecoVision, CD-i, Sega 32X, Super Game Boy und TurboGrafx-CD.

## Mit Build 80 dazugekommen

3DO, Atari 2600, Atari Lynx, Famicom Disk System, Gamate,
Intellivision, Neo Geo CD, Vectrex, WonderSwan.

Sie liegen fest im Repo unter `frontend/sysart/` und kommen deshalb bei
jeder Installation und jedem Update automatisch mit — es muss nichts
von Hand kopiert werden.

## Format

| | |
|---|---|
| Breite | **900 Pixel** |
| Höhe | **höchstens 450 Pixel** — bei hochkantem Motiv entscheidet die Höhe, die Breite fällt dann kleiner aus (das 3DO-Logo ist so 234x450 statt 900x1729) |
| Hintergrund | **RGB 28, 32, 44** — dieselbe Farbe wie die Karte, sonst hebt sich das Logo als heller oder schwarzer Kasten ab |
| Rand | randlos auf das Motiv zugeschnitten |
| Format | `.art` (ART1) |

## Umwandeln

Dafür gibt es seit Build 80 ein eigenes Werkzeug —
`PC-Tools/art_convert.py` ist für **Boxart** da und skaliert auf die
kleinen Kästen, das passt hier nicht:

```bash
# Logo mit echter Transparenz - einfachster Fall:
python PC-Tools/sysart_convert.py logo.png frontend/sysart/SG1000.art

# Logo auf schwarzem oder weissem Grund:
python PC-Tools/sysart_convert.py logo.webp frontend/sysart/SG1000.art --fluten

# Schwarze Schrift auf hellem Grund (wäre auf der dunklen Karte unsichtbar):
python PC-Tools/sysart_convert.py logo.png frontend/sysart/SG1000.art \
    --fluten --aufhellen

# Vorlage, bei der das Transparenz-Schachbrett ins Bild gemalt ist:
python PC-Tools/sysart_convert.py logo.png frontend/sysart/SG1000.art --karo

# Zum Ansehen, bevor es ins Repo geht:
python PC-Tools/sysart_convert.py logo.png /tmp/probe.art --vorschau /tmp/probe.png
```

Die Optionen im Klartext:

| Option | Wofür |
|---|---|
| `--fluten` | entfernt einen einfarbigen Hintergrund vom Bildrand her. Konturen mitten im Logo bleiben stehen, weil die Flutfüllung dort nicht hinkommt. |
| `--karo` | entfernt helle, farblose Flächen im **ganzen** Bild — für Vorlagen, bei denen das graue Schachbrettmuster als echte Pixel drinsteht (Atari 2600 und Famicom Disk System lagen so vor). |
| `--aufhellen` | dreht schwarze Schrift in Weiß. Farbige Teile bleiben unangetastet, weil sie Sättigung haben. |
| `--toleranz` | Farbtoleranz der Flutfüllung, Standard 40. Bei JPEG-Vorlagen höher (60 hat beim Lynx-Logo gereicht). |

**Der Dateiname muss exakt der Systemschlüssel sein** — die Liste steht
unten. `python3 tools/test_sysart_logos.py` prüft danach Größe,
Hintergrundfarbe und ob der Name überhaupt zu einem System gehört.

## Was noch fehlt

| System | Dateiname |
|---|---|
| Adventure Vision | `ADVENTUREVISION.art` |
| Arcadia 2001 | `ARCADIA.art` |
| Astrocade | `ASTROCADE.art` |
| Casio PV-1000 | `CASIOPV1000.art` |
| Channel F | `CHANNELF.art` |
| CreatiVision | `CREATIVISION.art` |
| Game & Watch | `GAMENWATCH.art` |
| Game Gear | `GAMEGEAR.art` |
| Mega Duck | `MEGADUCK.art` |
| Odyssey 2 | `ODYSSEY2.art` |
| Pocket Challenge V2 | `POCKETCHALLENGEV2.art` |
| Pokemon Mini | `POKEMONMINI.art` |
| SG-1000 | `SG1000.art` |
| VC 4000 | `VC4000.art` |
| WonderSwan Color | `WONDERSWANCOLOR.art` |

Der Reihe nach ist völlig in Ordnung — jede Datei wirkt sofort, ohne
dass am Code etwas geändert werden muss. Eine Akzentfarbe hat jedes
dieser Systeme bereits (siehe `SYSTEM_ACCENT` in `frontend.py`); sie
umrahmt das Logo und färbt die Auswahl in der Liste.

## Kein eigenes Logo nötig

**SuperGrafx** braucht keins: `.sgx`-Dateien laufen auf dem
TurboGrafx16-Core und erscheinen deshalb in der Kategorie
**TurboGrafx16** (siehe `fe/systems.py`) — eine eigene Kategorie gibt es
dafür nicht.
