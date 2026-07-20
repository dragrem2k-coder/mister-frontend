# Stream-Overlay — Technik-Übergabe für Dragrem

Kurzfassung: ein optionaler Web-Server im Frontend pusht die aktuelle Auswahl
per SSE an ein Browser-Overlay (OBS-Quelle) und ein Config-Backend. Reines
Standard-Python, keine neuen Abhängigkeiten, opt-in — bestehende Nutzer
merken davon nichts, solange die Freigabe-Datei fehlt.

## Neue/geänderte Dateien

| Datei | Was |
|-------|-----|
| `frontend/stream_server.py` | **neu** — HTTP-Server (`http.server`) + SSE, `.art`→PNG, Config-Persistenz |
| `frontend/stream_overlay.html` | **neu** — OBS-Overlay (SSE-Client) |
| `frontend/stream_admin.html` | **neu** — Config-Backend |
| `frontend/frontend.py` | **6 kleine Stellen** — siehe unten |
| `Scripts/stream_toggle.sh` | **neu** — Freigabe-Datei an/aus |

## Integration in frontend.py (genau diese Stellen)

1. **Konstanten** (nach `ART_HD`): `STREAM_ENABLED_FILE`,
   `STREAM_CONFIG_FILE`, `STREAM_PORT = 8080`, plus ein *guarded import*:
   ```python
   try:
       from stream_server import StreamServer
   except Exception:
       StreamServer = None
   ```
   → fehlt die Datei, läuft das Frontend normal weiter.

2. **`Frontend.__init__`** (nach `self.item_i = self.scroll = 0`): Server nur
   starten, wenn `StreamServer` da **und** `STREAM_ENABLED_FILE` existiert.
   Schlägt `start()` fehl (z.B. Port belegt), wird `self.stream = None` — kein
   harter Fehler.

3. **Zwei Methoden** (vor `def run`): `stream_state()` baut das State-Dict aus
   `self.cats[self.cat_i]` + `self.item_i` + `self.music`; `_publish_stream()`
   dedupliziert über eine Signatur und ruft `self.stream.publish()` nur bei
   echter Änderung.

4. **Hauptschleife**: eine Zeile `self._publish_stream()` direkt nach
   `act = self.next_action()`. Läuft also einmal pro Iteration, dedupliziert
   selbst — kein Peppering von publish-Aufrufen über den Code.

5. **Shutdown** (im `finally` von `run`): `if self.stream: self.stream.stop()`
   vor `self.music.shutdown()`.

Damit ist der Eingriff bewusst klein und an einer Stelle gebündelt. Wenn du in
deiner v1.19+-Basis mergest: die Anker (`self.item_i = self.scroll = 0`,
`act = self.next_action()`, `self.music.shutdown()`) sind eindeutig, das
sollte sauber übernehmbar sein.

## Datenvertrag (State-Dict)

```json
{
  "category": "Super Nintendo",   // Kategorie-Name (Badge)
  "system":   "Super Nintendo",   // = category (lesbarer Name fürs Badge)
  "syskey":   "SNES",             // Systemkey für die Cover-URL (/art)
  "name":     "Chrono Trigger",   // ausgewählter Eintrag (Titel)
  "index": 1, "total": 40,
  "nowplaying": "Corridors of Time" | null,
  "list": ["...","...","..."],    // kleines Fenster um die Auswahl
  "list_index": 1
}
```

Kategorien ohne `syskey` (Scripts, System, Core-Ordner) → Overlay blendet das
Cover aus, Badge zeigt den Kategorienamen. Passt automatisch.

## Server-Innenleben

- **SSE statt WebSocket**: einseitiger Push, nativ per `EventSource`, kein
  Handshake, kein Paket. Events `state` und `config`. `ThreadingHTTPServer`
  in einem Daemon-Thread; jede Verbindung (auch die lange SSE) hat ihren
  eigenen Thread. Pro Client eine `queue.Queue`; `publish()` legt die
  JSON-Nachricht in alle Queues, tote Clients fliegen raus. Heartbeat alle
  15 s als SSE-Kommentar.
- **Threading-Sicherheit**: der Server macht nur seltene Netzwerk-I/O in
  eigenen Threads; die Render-Schleife bleibt unberührt. Kein gemeinsamer
  Zustand außer `_state`/`_config`/`_clients`, alle unter einem Lock.
- **`.art`→PNG**: liest die vorhandene `ART1`/BGRA/zlib-Datei, swappt B/R,
  kodiert PNG (Color-Type 6, Filter 0) mit `zlib` — ~15 Zeilen, keine
  Bild-Lib. Overlay bekommt also exakt dasselbe Cover wie der CRT.
- **Config**: `/media/fat/frontend/stream_config.json`, atomar geschrieben
  (Temp + `os.replace`). `POST /config` merged nur bekannte Keys und pusht die
  neue Config live an alle Overlays.

Endpunkte: `/` (Overlay), `/admin`, `/events` (SSE), `/state`, `/config`
(GET/POST), `/art?sys=&name=`.

## Sicherheit / Betrieb

- Bindet auf `0.0.0.0:8080` (LAN). **Nicht** ins Internet forwarden — kein
  Auth in v1. Bei Bedarf Token-Parameter ergänzen.
- Zuschauer verbinden sich nie mit dem MiSTer; OBS komponiert lokal. Am Gerät
  hängen 1–2 Verbindungen (OBS + evtl. Backend-Tab). Last vernachlässigbar.
- Port fest in `STREAM_PORT`.

## Test-Status

Sandbox (grün): HTTP-Endpunkte, SSE-Push (state+config), `.art`→PNG inkl.
BGRA→RGBA (mit PIL gegengeprüft), Config-POST + atomare Persistenz,
`stream_state`/Dedupe-Logik; `frontend.py` und `stream_server.py`
kompilieren. Nicht testbar ohne Hardware: Server-Thread auf echtem ARM
(erwartet unkritisch) und das OBS-Zusammenspiel.

## Saubere nächste Schritte (bewusst offen gelassen)

- **System-Menü-Umschalter** analog zu „Music On/Off": Server im Betrieb
  starten/stoppen. `start()`/`stop()` sind dafür ausgelegt; es braucht nur
  einen Menüpunkt + Handler in der Schleife. Wollte ich ohne Hardware-Test
  nicht blind einbauen.
- **Metadaten im Overlay** (Jahr/Genre/Spieler): `stream_state()` um die
  `meta/*.json`-Felder erweitern, Overlay rendert sie unter dem Titel.
- **Mehrere Layouts/Themes** im Backend, falls gewünscht.
