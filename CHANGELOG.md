# Changelog

Alle nennenswerten Änderungen am MiSTer Custom Frontend. Kompakt
gehalten — für die volle technische Historie siehe die Git-Commits
bzw. den Kopfkommentar in `frontend/frontend.py`.

## v1.76 (2026-07-26)
- Notausstieg vereinfacht: reines Esc (statt Strg+Alt+Esc) auslösen —
  Haltezeit dafür bewusst auf 0,6s erhöht, damit ein normaler kurzer
  Esc-Druck in einem spiel-eigenen Pause-Menü nicht versehentlich
  auslöst. Pad-basierter Ausstieg (Start+Select) bleibt vorerst offen —
  beim getesteten 8BitDo-Controller kommt während des Spiels über
  keinen bekannten Kanal etwas durch.

## v1.75 (2026-07-26)
- NEUES FEATURE: Notausstieg per Strg+Alt+Esc während eines laufenden
  Spiels — über die rohe HID-Ebene (`/dev/hidrawX`), da die normale
  evdev-Ebene während eines Cores von MiSTer gesperrt wird (per gezielter
  Diagnose bestätigt: der bisherige F10-/Start+Select-Ausstieg konnte
  dadurch vermutlich nie tatsächlich auslösen). Tastatur wird dynamisch
  gefunden, Kombination muss 0,3s gehalten werden. Bestehender Pfad
  bleibt zusätzlich als Absicherung bestehen.

## v1.74 (2026-07-26)
- BUGFIX: der v1.73-Fix für den Attract-Modus-Schalter war selbst noch
  fehlerhaft — er suchte die "System"-Kategorie über "syskey ist None",
  aber "Zuletzt gespielt", "Favoriten" und "Scripts" nutzen das
  ebenfalls und stehen davor in der Liste. Dadurch wurde die falsche
  Kategorie aktualisiert, "System" blieb weiterhin eingefroren. Jetzt
  eindeutig über den Kategorienamen gefunden. Zusätzlich Protokollierung
  ergänzt für den Fall weiterer Probleme.

## v1.73 (2026-07-26)
- BUGFIX: Attract-Modus ließ sich im System-Menü scheinbar nicht
  umschalten — die angezeigte Beschriftung aktualisierte sich nie,
  obwohl die Einstellung selbst korrekt griff. Jetzt behoben.
- BUGFIX: "Zurück" aus einem Unterordner sprang immer auf Position 0
  der übergeordneten Ebene statt zur vorherigen Position zurück (z. B.
  bei einer alphabetischen PSX-Sammlung immer zu "A" statt "Q"). Jetzt
  wird die Position beim Betreten gemerkt und beim Zurückgehen
  wiederhergestellt — auch über mehrere Ebenen hinweg.
- Boxart-Problem (verpixeltes Cover beim Scrollen) weiterhin in
  Untersuchung.

## v1.72 (2026-07-26)
- BUGFIX: fehlendes Boxart bei manchen Titeln, erscheint aber später.
  ArtCache.get() cachte jeden fehlgeschlagenen Ladeversuch dauerhaft —
  auch bei einer beschädigten oder noch unvollständigen Cover-Datei
  (z. B. während eines laufenden Kopiervorgangs). Jetzt: nur "Datei
  existiert nicht" bleibt dauerhaft gecacht, ein Format-/Dekomprimierungs-
  fehler (möglicherweise vorübergehend) wird nicht gecacht — der nächste
  Zugriff versucht es einfach erneut. Zusätzlich zwei bisher nicht
  abgefangene Fehlerarten ergänzt, die sonst zum Absturz geführt hätten.

## v1.71 (2026-07-26)
- Leichter Zeichenpfad jetzt auch für echte Navigation (nicht nur
  Hintergrund-Ticks): ein einzelner hoch/runter-Schritt ohne Scrollen
  (der häufigste Fall beim Durchbrowsen) aktualisiert nur die
  betroffenen Zeilen + Boxart-Panel statt der kompletten Seite. Fällt
  bei Scrollen/Ordnerwechsel automatisch auf den vollen Aufbau zurück.
  51 % weniger Zeit pro Navigationsschritt (73ms → 36ms) bei einem
  realistischen HD-Cover. Pixelgenau gegen den vollen Aufbau geprüft
  (18 Sprungkombinationen, inkl. Favoriten-Markierung und
  Hintergrundbild) sowie über einen echten Durchlauf durch die
  Hauptschleife bestätigt.

## v1.70 (2026-07-26)
- WICHTIGER FUND: Ein Log-Ausschnitt zeigte Zeitstempel ab "00:00:11" —
  MiSTer hat offenbar keine batteriegepufferte Uhr, die per NTP
  nachträglich korrigiert wird, mitunter als plötzlicher Sprung um
  Stunden. Das ist höchstwahrscheinlich die eigentliche Ursache für den
  zu früh startenden Attract-Modus: der Leerlauf-Zähler nutzte die
  Systemuhr, ein Sprung sah sofort wie "90 Sekunden Leerlauf" aus.
  Fix: alle Zeitdauer-Messungen (42 Stellen) auf time.monotonic()
  umgestellt — eine Uhr, die nie springt. Echte Uhrzeit-Anzeige bleibt
  unverändert bei time.strftime().

## v1.69 (2026-07-26)
- GROSSER Fund: die Cover-Verkleinerung (für HD-Cover, die größer als
  der verfügbare Platz sind — der Normalfall) machte pro Ziel-Pixel
  eine einzelne Zuweisung statt zeilenweise zu arbeiten. Kostete rund
  90ms **pro Navigation** zu einem neuen Spiel — eine andere, bisher
  unentdeckte Kategorie von Verzögerung als die bisherigen Tick-
  Optimierungen. Jetzt 69 % schneller (89,65ms → 27,81ms), pixelgenau
  identisch zum alten Ergebnis. Außerdem: Logging für den Attract-
  Modus-Start ergänzt, um die tatsächliche Leerlaufzeit zu sehen.

## v1.68 (2026-07-26)
- BUGFIX: Namens-Laufschrift bei langen Spieletiteln lief auf CRT viel
  zu schnell (bis zu 100 Zeichen/Sekunde statt beabsichtigter ~5,5).
  Ursache: keine eigene Zeitbremse — solange das Zeichnen teuer war
  (vor v1.62/63), bremste das automatisch aus; seit die Ticks viel
  billiger sind, lief die Schleife auf CRT nahe ihrem theoretischen
  Maximum. Jetzt mit derselben Zeitbremse wie Equalizer/Pulsieren.

## v1.67 (2026-07-26)
- Absicherung gegen unbegrenzt wachsenden Zeichen-Cache: die
  meistgenutzte Zeichenfunktion (rect()) cachte ohne Obergrenze nach
  Farbe+exakter Breite — bei leicht wechselnden Breiten über viele
  Navigationen sammelten sich nie wieder verwendete Einträge an.
  Jetzt mit Obergrenze (150 Einträge), eigener Cache getrennt von
  clear()s Hintergrundmustern. Ehrlicher Hinweis: ob das den
  gemeldeten Lag zusätzlich verbessert, war in der Sandbox nicht
  eindeutig messbar — die Absicherung selbst ist trotzdem sinnvoll.

## v1.66 (2026-07-26)
- Attract-Modus: Leerlauf-Schwelle von 45 auf 90 Sekunden erhöht
  (großzügigerer Puffer), zusätzlich attract_enabled() jetzt
  zwischengespeichert statt bei jedem Leerlauf-Durchlauf erneut die
  Datei zu prüfen.

## v1.65 (2026-07-25)
- Attract-Modus startete manchmal sehr schnell nach dem Neustart (der
  Leerlauf-Zähler lief schon während Scan/Boot-Animation mit) — jetzt
  erst danach zurückgesetzt.
- Cursor sprang gelegentlich zwei Zeilen statt einer beim Klicken durch
  das Menü — der Turbo-Sprung-Zähler unterschied nicht zwischen echtem
  Tastenhalten und mehreren schnellen Einzelklicks. Jetzt zeitbasiert
  abgesichert.

## v1.64 (2026-07-25) — KRITISCHER BUGFIX
- Frontend stürzte kurz nach dem Boot ab (Boot-Animation spielt,
  dann zurück ins MiSTer-OSD), sobald der erste Equalizer-/Laufschrift-
  Tick fällig wurde (praktisch bei jedem mit aktivierter Musik).
  Ursache: ein beim Einfügen einer v1.63-Funktion versehentlich
  verrutschter Codeblock. Behoben und mit einem echten Testlauf durch
  die Hauptschleife (nicht nur Pixel-Vergleiche) abgesichert.

## v1.63 (2026-07-25)
- Performance-Verbesserung fortgesetzt: auch die Songtitel-Laufschrift
  nutzt jetzt den leichten Zeichenpfad statt eines vollen Aufbaus
  (3,88ms → praktisch nicht mehr messbar), kombinierbar mit dem
  Equalizer-/Pulsier-Pfad aus v1.62.

## v1.62 (2026-07-25)
- GROSSE Performance-Verbesserung: jeder Equalizer-/Pulsier-Tick löste
  bisher einen kompletten Bildschirmaufbau aus, obwohl sich nur eine
  Zeile und ein paar Balken ändern. Neue leichte Zeichenpfade sparen
  90–92 % der Zeit pro Tick (gemessen: 5,15ms → 0,42ms auf HDMI) — die
  wahrscheinliche Hauptursache für das gemeldete HDMI-Lag-Gefühl.

## v1.61 (2026-07-25)
- BUGFIX (Fortsetzung von v1.60): der Grab-Fix hat das Einfrieren beim
  Konfigurieren von "OSD öffnen" nicht behoben. Neue Theorie: F9 ist
  bei MiSTer für den Konsolen-/Grafikmodus-Wechsel reserviert, vermutlich
  auf Kernel-Ebene — ein echtes F9 vom Pad käme nie bei unserem Prozess
  an. Zwei Absicherungen: Zeitlimit (20s) statt endlosem Warten, F9 wird
  nie als Belegung akzeptiert.

## v1.60 (2026-07-25)
- BUGFIX: Tastenbelegungs-Assistent löste den Eingabe-Grab für die
  gesamte Dauer, wodurch MiSTers eigene Menü-Taste beim Konfigurieren
  von "OSD öffnen" parallel reagieren konnte (Bildschirm fror ein /
  wurde schwarz mit Login-Prompt). Grab bleibt jetzt durchgehend
  gehalten — für das eigene Auslesen der Tasten nie nötig gewesen.

## v1.59 (2026-07-25)
- L1/L2/R1/R2 vollständig belegbar: viele Xbox-artige Controller
  senden L2/R2 als analogen Trigger statt als eigene Taste — das wurde
  bisher gar nicht erkannt. Jetzt per Schwellwert erfasst und wie eine
  normale Taste frei belegbar. L2 und R2 zeigen beide (digital und
  analog) standardmäßig auf "Favorit umschalten".

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
