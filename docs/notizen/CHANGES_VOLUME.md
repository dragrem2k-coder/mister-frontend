# Lautstärke-Regler – Änderungen (Vorschlag zum Übernehmen)

Ein Regler für **Musik UND Menü-Sounds** zusammen. Stufen 0/20/40/60/80/100 %.

## Warum zwei Mechanismen
- **Musik** läuft über `mpg123` → bekommt `-f <0..32768>` (Skalierungsfaktor).
- **Menü-Sounds** sind selbst erzeugte WAVs, abgespielt über `aplay` – und `aplay`
  hat **keinen** Lautstärke-Schalter. Daher steckt die Lautstärke in der
  **Amplitude** der WAV: sie werden bei Änderung mit `0.35 * VOL/100` neu erzeugt.

## Neu in `frontend.py` (alles additiv)
- Konstante `VOLUME_FILE` + globales `VOLUME` (0–100, persistent)
- `_load_volume()` / `_save_volume()` / `_mpg_scale()` / `_regenerate_sfx()`
- `_ensure_sfx_files()`: erzeugt die WAVs mit `volume=0.35 * VOLUME/100`
- mpg123-Aufrufe (MP3 **und** Radio) bekommen `-f _mpg_scale()`
- `MusicPlayer.cycle_volume()`: 0 → 20 → 40 → 60 → 80 → 100 → 0; speichert,
  erzeugt die Sounds neu und startet die Musik mit neuer Lautstärke neu
- Menüpunkt „Lautstärke: X%" + `run()`-Dispatch `elif kind == "volume"`
- Übersetzungsschlüssel `sys_volume`

## Auf Hardware prüfen
Dass `mpg123 -f` die Musik hörbar dämpft und die Menü-Sounds leiser werden.
(`-f` ist ein Standard-mpg123-Schalter, sollte vorhanden sein.)
