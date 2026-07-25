# Changelog

Alle nennenswerten Änderungen am MiSTer Custom Frontend. Kompakt
gehalten — für die volle technische Historie siehe die Git-Commits
bzw. den Kopfkommentar in `frontend/frontend.py`.

## v1.58 (2026-07-25)
- Favoriten-Liste: F8/L2 markiert ein Spiel als Favorit (unabhängig
  von "Zuletzt gespielt"), eigene Kategorie, kleines "*" in der Liste.

## v1.57 (2026-07-25)
- Attract-Modus / Bildschirmschoner: nach 45 Sekunden ohne Eingabe
  zeigt das Menü automatisch ein zufälliges Spiel großflächig mit
  Cover, wechselt alle 6 Sekunden weiter. Jede Taste beendet es sofort.
  Über System-Menü an-/ausschaltbar (Standard: an).

## v1.56 (2026-07-25)
- Arcade-Boxart: `mister_boxart.py` lädt jetzt auch Cover für Arcade
  (über libretro-thumbnails/MAME), automatisch mit dabei, keine
  Extra-Option nötig.

## v1.53–v1.55
- Zwei echte USB-Kaltstart-Bugs behoben: instabile Cache-Signatur bei
  wechselndem USB-Mountpunkt, unnötiger Komplett-Neuscan trotz nur
  kurzer Verzögerung.
- SIGHUP-Absicherung (Schutz vor eingefrorenem Bildschirm bei
  SSH-Verbindungsabbruch während eines manuellen Tests).
- Offline-Installer (`install_offline.sh`) mit automatischer Sicherung
  der Vorversion, PC-Werkzeug für die OBS-Overlay-Einrichtung.
- Equalizer, pulsierende Markierung und Songtitel-Laufschrift auch auf
  HDMI spürbar schneller.
- Uhrzeit + Netzwerksymbol im Hauptmenü.

## v1.48–v1.52
- Ordnerstruktur-Navigation: eigene Unterordner werden beliebig tief
  1:1 übernommen, statt alles in eine flache Liste zu quetschen.
  Boxart erscheint automatisch auch auf Ordner-Ebene, wenn der Ordner
  selbst einem katalogisierten Spiel entspricht (z. B. Mehrfach-CD-
  Sammlungen).
- Frontend blieb nach einem Kaltstart manchmal im MiSTer-Menü hängen,
  während die Musik schon lief - behoben (Bildschirmwechsel läuft
  jetzt vor dem Scan, nicht danach).
- Erste USB-Absicherung gegen zu früh startende Scans.

## v1.39–v1.47
- Umfangreiche Performance-Arbeit: Equalizer, pulsierende Markierung
  und Laufschrift auf CRT deutlich flotter; ein echter Logikfehler
  behoben, der beide Effekte bremste, sobald die Laufschrift aktiv
  war.
- Größter HDMI-Fund: der Boxart-Schlagschatten kostete rund 60 % der
  gesamten Zeichenzeit - auf eine schnelle, vorgemischte Variante
  umgestellt (rund 4x schneller).
- Boot-Animation nutzt seither die native Bildgröße statt sie
  zwanghaft aufs Vollbild hochzuskalieren (rund 7x flüssiger auf
  HDMI).
- Boxart-Downloader läuft seither mit parallelen Downloads (rund 5x
  schneller).

## v1.30–v1.38
- Neue Kategorie "Zuletzt gespielt".
- Now-Playing-Anzeige in die Fußzeile verschoben.
- Rein japanische ROM-Titel werden ausgeblendet (Mehrfach-Region-Tags
  bleiben erhalten).
- Boot-Animation erkennt automatisch CRT/HDMI und zeigt die passende
  Version.
- Ein-Kommando-Installation (`install.sh`), inklusive Diagnose bei
  Download-Problemen.

## v1.29
- Akzentfarben pro System, Glow-Effekt und pulsierende Markierung,
  animierter Equalizer bei laufender Musik.

## v1.19–v1.28
- Grundlegende Zweiseiten-Navigation (Kategorien + Spieleliste),
  Hintergrundmusik, Sprachumschaltung Deutsch/Englisch, eigene
  Tastenbelegung, Turbo-Sprung beim Halten einer Richtungstaste.
- Stream-Overlay für OBS, System-Artbox im Kategorien-Menü,
  automatische Bereinigung der Spieleliste (Mehrfach-Regionen,
  bekannte Test-/Beta-Dateien).

## v1.1–v1.6
- Erste lauffähige Version: Boxart-Anzeige, CRT/HDMI-Umschaltung,
  Buchstaben-Sprung in der Liste.

---

Ausführliche Installationsanleitung, komplette Funktionsübersicht und
Fehlerbehebung: siehe `README.md`. Kompakte Feature-Übersicht mit
Screenshots: siehe `VORSCHAU.md`.
