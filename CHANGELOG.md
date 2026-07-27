# Changelog

Was sich am Frontend so getan hat. Für die ganz kleinteiligen Details
schau am besten in die Git-Historie oder in den Kopf von
`frontend/frontend.py`.

## v1.84
Die Soundeffekte haben teilweise die Musik gestört und sich bei
schneller Navigation gestapelt - kam davon, dass `aplay` offenbar auf
dieselbe Soundkarte wartete wie `mpg123`. Jetzt zwei Bremsen: kein
neuer Ton, solange der vorherige noch läuft, und während die Musik
tatsächlich gerade spielt, wird gar nicht erst versucht.

## v1.83
OBS-Overlay aufgehübscht: Genre/Jahr, Spielzeit, RetroAchievements-
Fortschritt und ein kleiner Stern für Favoriten sind jetzt mit im
Bild, jedes einzeln über das Backend an-/abschaltbar.

## v1.82
RetroAchievements-Fortschritt im Info-Bereich ("RA: 20/50"). Wer's
nicht eingerichtet hat, merkt nichts davon - keine Verzögerung, keine
Anzeige. Einrichtung per SSH (Bildschirmtastatur gibt's bei uns
nicht), Abgleich über den Spieletitel. Bei Zweifel zeigt's lieber
nichts an als was Falsches.

## v1.81
Hab die letzten fünf Versionen nochmal durchgecheckt. `play_sfx()`
hat unnötig oft eine Datei geprüft, bevor überhaupt die Drossel
greift - gefixt. Der Verdacht, die neue Spielzeit-Anzeige würde die
Navigation ausbremsen, hat sich beim genaueren Hinsehen zum Glück
nicht bestätigt.

## v1.80
Zwei Top-10-Listen im System-Menü: meistgespielt und meistgestartet.

## v1.79
Automatischer Spielzeit-Tracker. Merkt sich pro Spiel, wie lang
tatsächlich gespielt wurde - Ladezeiten zählen nicht mit.

## v1.78
Kleine Soundeffekte beim Navigieren, selbst erzeugt (kein Download
nötig). Ein-/ausschaltbar im System-Menü.

## v1.77
MiSTer hat keine gepufferte Uhr, also holt sich das Frontend jetzt
selbst die Zeit per NTP. Dazu drei Farbschemata zur Auswahl (Dunkel,
Hell, Retro-Grün).

## v1.76
Notausstieg vereinfacht - nur noch Esc statt der Dreifachkombi. Der
Pad-Ausstieg über Start+Select bleibt vorerst Zukunftsmusik, mein
Controller gibt während des Spiels einfach nichts her.

## v1.75
Einen Weg gefunden, während eines laufenden Spiels trotzdem noch
Tastatureingaben mitzubekommen (MiSTer sperrt das eigentlich
komplett). Damit jetzt: Notausstieg per Tastenkombi, ohne erst
zurück ins Menü zu müssen.

## v1.74
Mein eigener Fix aus v1.73 war noch halb kaputt - "Zuletzt gespielt"
und "System" nutzen intern dieselbe Markierung, dadurch hat sich die
falsche Kategorie aktualisiert. Jetzt sauber über den Namen gelöst.

## v1.73
Attract-Modus ließ sich zwar umschalten, die Beschriftung hat's nur
nicht gezeigt. Und: "Zurück" aus einem Unterordner sprang immer ganz
nach oben statt zur vorherigen Stelle - beides behoben.

## v1.72
Manche Cover fehlten einfach, obwohl sie da waren. Lag daran, dass
ein einmal fehlgeschlagener Ladeversuch für immer gemerkt wurde, auch
wenn's nur eine gerade noch kopierte, unvollständige Datei war.

## v1.71
Ein einzelner Schritt hoch/runter beim Browsen zeichnet jetzt nur
noch, was sich wirklich ändert, statt die ganze Seite neu aufzubauen.
Gute 51% schneller pro Schritt.

## v1.70
Des Rätsels Lösung für den zu früh startenden Attract-Modus: MiSTer
hat keine Batterie-Uhr, die Zeit kann mitten in der Sitzung plötzlich
springen. Auf eine Uhr umgestellt, die das nicht tut.

## v1.69
Der bisher größte Performance-Fund: Cover-Verkleinerung hat pro
Pixel einzeln gearbeitet statt zeilenweise. Kostete fast 90ms bei
jeder Navigation zu einem neuen Spiel. Jetzt 69% schneller.

## v1.68
Laufschrift bei langen Titeln raste auf CRT viel zu schnell durchs
Bild - fehlende Zeitbremse, jetzt nachgerüstet.

## v1.67
Der Zeichen-Cache für Rechtecke wuchs unbegrenzt weiter. Jetzt mit
Obergrenze.

## v1.66
Attract-Modus wartet jetzt 90 statt 45 Sekunden, und die Abfrage, ob
er aktiv ist, wird zwischengespeichert statt bei jedem Tick neu von
der Platte gelesen.

## v1.65
Attract-Modus ist manchmal viel zu früh angesprungen (lief schon
während Boot/Scan mit). Und: der Turbo-Sprung beim Klicken hat
manchmal zwei Zeilen übersprungen statt einer.

## v1.64 — kritischer Bugfix
Frontend stürzte kurz nach dem Boot ab, sobald der erste Equalizer-
Tick fällig war. Ein Codeblock war beim letzten Umbau verrutscht.
Peinlich, aber schnell gefunden.

## v1.63
Auch die Songtitel-Laufschrift läuft jetzt über den leichten
Zeichenpfad statt eines vollen Aufbaus.

## v1.62
Der bislang größte Performance-Sprung: jeder Equalizer-/Puls-Tick hat
bisher den ganzen Bildschirm neu gezeichnet, obwohl sich nur eine
Zeile ändert. 90% weniger Zeit pro Tick - das war vermutlich die
Hauptursache für das gemeldete HDMI-Ruckeln.

## v1.61
Fortsetzung von v1.60 - das Einfrieren beim Konfigurieren von "OSD
öffnen" lag an F9, das MiSTer für sich selbst reserviert. Jetzt mit
Zeitlimit und F9-Sperre im Belegungs-Assistenten.

## v1.60
Der Belegungs-Assistent hat die Eingabe während der ganzen Dauer
gesperrt, wodurch MiSTers eigene Menütaste parallel reagieren konnte
- Bildschirm ist eingefroren. Grab bleibt jetzt durchgehend aktiv.

## v1.59
L1/L2/R1/R2 komplett belegbar, auch für Controller, die die
Schultertasten als Analogwert statt als Knopf senden.

## v1.58
Favoriten-Liste - F8 oder L2 markiert ein Spiel, eigene Kategorie,
kleiner Stern in der Übersicht.

## v1.57
Attract-Modus / Bildschirmschoner - nach 45 Sekunden Leerlauf zeigt
das Menü ein zufälliges Spiel großflächig, wechselt alle paar
Sekunden weiter.

## v1.56
Boxart-Downloader kann jetzt auch Arcade-Cover.

## v1.53–v1.55
Ein paar hartnäckige USB-Kaltstart-Bugs gefixt, Offline-Installer
dazu, Equalizer und Laufschrift auch auf HDMI nochmal schneller,
Uhrzeit + Netzwerksymbol im Hauptmenü.

## v1.48–v1.52
Eigene Unterordner werden jetzt 1:1 übernommen statt alles
plattzuklopfen. Boxart erscheint auch auf Ordner-Ebene. Ein paar
Startup-Bugs behoben.

## v1.39–v1.47
Viel Performance-Feinschliff auf CRT. Größter Fund: der Boxart-
Schatten hat allein 60% der Zeichenzeit gefressen - auf eine
vorgemischte Variante umgestellt, rund 4x schneller. Boot-Animation
und Boxart-Downloader ebenfalls deutlich flotter.

## v1.30–v1.38
"Zuletzt gespielt" als neue Kategorie, Now-Playing in die Fußzeile,
Boot-Animation erkennt automatisch CRT/HDMI, richtiger Installer.

## v1.29
Akzentfarben pro System, Glow-Effekt, pulsierende Markierung,
Equalizer-Animation bei laufender Musik.

## v1.19–v1.28
Grundgerüst für die Zweiseiten-Navigation, Hintergrundmusik,
Sprachumschaltung, eigene Tastenbelegung, Stream-Overlay,
automatische Bereinigung der Spieleliste.

## v1.1–v1.6
Die ersten lauffähigen Versionen - Boxart, CRT/HDMI-Umschaltung,
Buchstaben-Sprung in der Liste.

---

Ausführliche Anleitung und alle Funktionen im Detail: `README.md`.
Kurzer Überblick mit Screenshots: `VORSCHAU.md`.
