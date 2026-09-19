# Rainwave-Internetradio – Änderungen (Vorschlag zum Übernehmen)

Zweite Musikquelle neben den lokalen MP3s. Auf echter MiSTer-Hardware getestet:
`mpg123` spielt `http://relay.rainwave.cc/game.mp3` direkt (mpg123 hat HTTP, aber
KEIN https – daher http), und `api4/info` liefert anonym den aktuellen Titel.
Der Now-Playing-Titel fließt automatisch ins OBS-Overlay (bestehender
`nowplaying`-Pfad, keine Overlay-Änderung nötig).

## Neu
- **`frontend/rainwave.py`** – eigenständiges stdlib-Modul: Stationstabelle
  (Game/OCReMix/Covers/Chiptune/All), `stream_url()`, `RainwaveRadio` mit
  `tick()` (pollt alle 15 s), `now_playing()`, `set_station()`. Enthält unten
  einen Direkt-Test (`python3 rainwave.py` / `... play <sid>`).

## Geändert in `frontend.py` (alles additiv, MP3-Pfad unverändert)
- `import rainwave`
- Konstante `MUSIC_SOURCE_FILE` (speichert Quelle + Stations-sid)
- `MusicPlayer`:
  - `__init__`: lädt Quelle/Station, legt `self.radio` an
  - `_load_source()` / `_save_source()`
  - `_start_current()`: bei Quelle „radio" → `mpg123 <stream-url>`
  - `tick()`: Radio-Zweig (pollt Now-Playing, verbindet nach Abriss neu, mit Backoff)
  - `current_track_name()`: Radio → Titel bzw. „Radio: <Station>"
  - `available()`: Radio verfügbar, wenn `mpg123` da ist
  - `cycle_source()`: MP3 → Radio(Game..All) → MP3; lässt An/Aus unberührt
- `system_items()`: neuer Eintrag „Musik-Quelle" + Label (Signatur um
  Quelle/Station erweitert; beide Aufrufer angepasst)
- `run()`-Dispatch: `elif kind == "music_source": self.music.cycle_source()`
- Übersetzungsschlüssel `sys_music_source`

## Guter-Gast-Hinweise (Rainwave)
Anonymes `api4/info` alle 15 s, eigener User-Agent, „via Rainwave"-Nennung
empfohlen. `RAINWAVE_STREAM_HOST` ggf. gegen die aktuelle Tune-in-Seite prüfen.
