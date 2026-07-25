# MiSTer Custom Frontend — Vorschau (Stand v1.56)

Ein selbstgebautes grafisches Frontend für den MiSTer FPGA, komplett in
purem Standard-Python — keine einzige externe Abhängigkeit auf dem
MiSTer selbst.

<p align="center">
  <img src="screenshots/preview_1_kategorien.png" width="420" alt="Kategorien-Menü">
  &nbsp;&nbsp;
  <img src="screenshots/preview_2_spieleliste.png" width="420" alt="Spieleliste mit Boxart">
</p>
<p align="center">
  <img src="screenshots/preview_3_ordner.png" width="420" alt="Ordner-Navigation bei Mehrfach-CD-Spielen">
  &nbsp;&nbsp;
  <img src="screenshots/preview_4_attract.png" width="420" alt="Attract-Modus / Bildschirmschoner">
</p>
<p align="center"><sub>Links: Ordner-Navigation — Boxart erscheint auch auf Ordner-Ebene bei Mehrfach-CD-Spielen &nbsp;|&nbsp;
Rechts: Attract-Modus — nach kurzer Untätigkeit zeigt das Menü von selbst eine Diashow der eigenen Sammlung</sub></p>

*Screenshots direkt aus dem echten Programmcode gerendert, keine
Fotomontage.*

---

## Was es kann

### Navigation & Darstellung
- Zwei Ebenen: Kategorien (Systeme, Arcade, Scripts, System) und
  Spieleliste, dazwischen beliebig tiefe **Ordner-Navigation** — deine
  eigene Ordnerstruktur (z. B. "1 US-A-E", Mehrfach-CD-Ordner) wird 1:1
  übernommen, statt alles in eine lange Liste zu quetschen
- Boxart erscheint automatisch auch auf Ordner-Ebene, wenn der Ordner
  einem katalogisierten Spiel entspricht (typisch bei PSX-Sammlungen
  mit einem Unterordner pro Spiel)
- "Zuletzt gespielt" — bis zu 15 zuletzt gestartete Spiele, systemübergreifend
- **Favoriten** — eigene, bewusst kuratierte Auswahl (F8/L2-Taste),
  unabhängig von "Zuletzt gespielt"
- **Attract-Modus**: nach kurzer Untätigkeit zeigt das Menü von selbst
  eine Diashow der eigenen Sammlung — großflächiges Cover, wechselt
  automatisch weiter, jede Taste beendet es sofort
- CRT (15 kHz) und HDMI werden automatisch erkannt, mit jeweils
  eigens abgestimmter Optik und Geschwindigkeit
- Akzentfarben pro System, pulsierende Auswahl-Markierung mit
  Glow-Effekt, animierter Equalizer bei laufender Musik
- Uhrzeit + Netzwerksymbol im Hauptmenü
- Sprache umschaltbar (Deutsch/Englisch)
- Eigene Tastenbelegung per Assistent (erkennt automatisch, welche
  Taste gedrückt wird)

### Boxart & Spielinfos
- Automatischer Download für alle unterstützten Konsolen **und
  Arcade** (über `libretro-thumbnails`), direkt auf dem MiSTer oder
  vom PC aus — mit parallelen Downloads für spürbar mehr Tempo
- Getrennte SD- und HD-Cover-Profile — automatische Auswahl je nach
  CRT/HDMI
- Automatische Bereinigung: Mehrfach-Regionen desselben Spiels werden
  zusammengefasst (beste Region gewinnt), rein japanische Titel lassen
  sich ausblenden, bekannte Beta/Proto/Hack-Dateien werden gefiltert
- Optionale "Nur katalogisierte Spiele"-Ansicht

### Musik & Stream
- Hintergrundmusik (MP3, zufällig gemischt), pausiert automatisch im
  MiSTer-Menü/OSD
- Boot-Animation (eigene Bildfolge), erkennt automatisch CRT/HDMI und
  zeigt die passende Version
- Stream-Overlay für OBS (Cover, Titel, Now-Playing im Browser),
  inklusive PC-Komfort-Werkzeug für die Einrichtung

### Installation & Pflege
- Ein-Kommando-Installation mit **oder** ohne Internetzugang, inklusive
  automatischer Sicherung der Vorversion bei jedem Update
- Persistenter Cache erkennt USB-Laufwerke zuverlässig, auch wenn sie
  nach einem Kaltstart erst verzögert oder unter wechselnder
  Nummerierung einhängen

---

## Warum ein eigenes Frontend?

MiSTer hat keine GPU — ein schwergewichtiges Menü kann die ARM-CPU
spürbar belasten. Genau da liegt der Schwerpunkt hier: der größte
Teil der Entwicklungszeit floss in gezielte Performance-Arbeit (u. a.
ein einzelner Effekt, der 60 % der Zeichenzeit auf HDMI kostete,
gefunden und auf einen Bruchteil reduziert), nicht in immer neue
Features. Keine externen Abhängigkeiten, beide Bildausgänge (CRT und
HDMI) gleichwertig unterstützt, eine einzelne, nachvollziehbare
Python-Datei. Ein Ein-Personen-Hobbyprojekt, kein Team-Produkt —
dafür sehr genau auf real genutzte Hardware abgestimmt.

---

*Für die komplette, ausführliche Dokumentation siehe `README.md`.*
