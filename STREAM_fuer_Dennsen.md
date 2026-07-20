# Stream-Overlay einrichten — Anleitung

Das Overlay zeigt in deinem Stream live an, was du gerade im MiSTer-Frontend
auswählst: Cover, Titel, System und den laufenden Musiktitel. Du spielst und
navigierst wie gewohnt am CRT — der Stream bekommt die Menü-Ansicht als
sauberes Overlay obendrauf, unabhängig vom Bildausgang.

**Wichtig vorab:** Deine Zuschauer sehen das Overlay ganz normal im
Twitch-Bild. Sie verbinden sich **nicht** mit dem MiSTer — das macht nur OBS
bei dir lokal. Der MiSTer und dein Stream-PC müssen im **selben Netzwerk**
sein.

---

## Schritt 1 — Overlay einschalten

Führe das Script `stream_toggle.sh` aus. Zwei Wege:

- **Am MiSTer:** OSD öffnen → **Scripts** → `stream_toggle` starten. (Oder im
  Frontend selbst in der Kategorie **Scripts**.)
- **Per SSH:** `/media/fat/Scripts/stream_toggle.sh on`

Danach das **Frontend einmal neu starten** (ESC raus und neu starten, oder
MiSTer neu booten). Der Server läuft erst nach dem Neustart.

Kontrolle: In `/tmp/frontend.log` steht dann eine Zeile wie
`StreamServer laeuft auf http://0.0.0.0:8080/`.

## Schritt 2 — IP des MiSTers herausfinden

Die brauchst du für OBS. Am schnellsten im MiSTer-OSD unter den
Netzwerk-/System-Infos, oder per SSH mit `ip addr`. Es ist eine Adresse wie
`192.168.x.x`. Merke sie dir — im Folgenden `<MiSTer-IP>`.

## Schritt 3 — Kurz im Browser testen

Öffne am Stream-PC im Browser `http://<MiSTer-IP>:8080/`. Wenn du jetzt am
MiSTer im Frontend herumnavigierst, sollte sich die Karte im Browser
mitbewegen. Klappt das, ist alles bereit für OBS. (Das Backend zum Einstellen
liegt unter `http://<MiSTer-IP>:8080/admin`.)

## Schritt 4 — In OBS einbinden

1. In deiner Szene **Quelle hinzufügen → Browser**.
2. **URL:** `http://<MiSTer-IP>:8080/`
3. **Breite/Höhe:** deine Canvas-Größe, also z.B. `1920` × `1080`.
4. Rest der Einstellungen kannst du auf Standard lassen. Der Hintergrund des
   Overlays ist transparent — es liegt also sauber über deinem Spielbild.
5. Die Quelle in der Szene ganz nach oben ziehen (damit sie über dem
   Game-Capture liegt).

Tipp: Aktiviere bei der Browser-Quelle „Browser neu laden, wenn Szene aktiv
wird" — dann ist nach OBS-Neustart sofort alles frisch.

## Schritt 5 — Aussehen einstellen (Backend)

Öffne `http://<MiSTer-IP>:8080/admin`. Änderungen sind **sofort live**, auch
in OBS. Du hast:

- **Branding-Text** — z.B. „Dennsen86", erscheint klein über dem Titel.
- **Akzentfarbe / Hintergrundfarbe** — Farbgebung der Karte.
- **Hintergrund transparent** — an lassen für Overlay; aus, wenn du eine
  volle Karte willst.
- **Cover / System-Badge / Vorschau-Liste / Now-Playing** — einzeln an/aus,
  je nachdem wie viel du im Bild haben willst.
- **Ecke** — in welche Bildecke die Karte gehört.
- **Größe** — 50–150 %, je nach Auflösung/Geschmack.

Rechts siehst du eine Live-Vorschau. Die Einstellungen bleiben gespeichert.

## Schritt 6 — Szenen-Aufbau (Empfehlung für dich)

Dein Fall: du spielst am CRT, das Spielbild geht über HDMI-Capture in den
Stream, das Overlay liegt oben drauf.

- **Beim Spielen:** Game-Capture füllt das Bild, das Overlay bleibt als kleine
  Karte in der Ecke (zeigt Titel + Now-Playing). Willst du es beim Spielen
  ganz weg, blende die Browser-Quelle einfach aus.
- **Beim Aussuchen im Menü:** genau hier war der Stream früher „blank", weil
  das MiSTer-Menü nicht gleichzeitig auf CRT und HDMI kann. Jetzt zeigt das
  Overlay live deine Auswahl — du brauchst keine „Wähle nächstes Spiel"-
  Standbildszene mehr. Optional kannst du eine eigene „Menü"-Szene bauen
  (z.B. Overlay groß mittig statt klein in der Ecke).

## Schritt 7 — Wieder ausschalten

`stream_toggle.sh off` (gleicher Weg wie Schritt 1) und Frontend neu starten.

---

## Wenn etwas nicht geht

- **Overlay bleibt leer / zeigt nur „-":** Hast du das Frontend nach dem
  Einschalten neu gestartet? Prüfe die Log-Zeile aus Schritt 1. Ohne Neustart
  läuft der Server nicht.
- **Browser zeigt unter `:8080` nichts:** richtige IP? MiSTer und PC im
  selben Netz? Läuft das Frontend gerade (Server läuft nur, solange das
  Frontend läuft)?
- **Kein Cover zu sehen:** Cover gibt es nur für Spiele, für die schon eine
  Boxart heruntergeladen wurde. Cores, Scripts und die Recently-Played-
  Shortcuts haben nie eins — das ist normal.
- **Overlay hängt / aktualisiert nicht mehr:** Browser-Quelle in OBS einmal
  neu laden. Das Overlay verbindet sich sonst nach kurzer Zeit von selbst
  wieder.
- **Sicherheit:** Port 8080 **nicht** im Router nach außen freigeben — das
  ist nur fürs Heimnetz gedacht.
