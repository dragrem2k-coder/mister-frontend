# Vom leeren MiSTer zum Stream — Anleitung für Dennsen

**Wenn du nicht streamst: hör nach Teil 1 auf.** Das Frontend
funktioniert komplett eigenständig, alles ab Schritt 10 ist nur für
das OBS-Overlay im Stream.

---

## Teil 1 — Das Frontend auf dem MiSTer

### 1. Was du brauchst

- Deinen MiSTer im selben Netzwerk wie dein PC
- Ein SSH-Programm. Unter Windows 10/11 reicht die eingebaute
  PowerShell, sonst [PuTTY](https://www.putty.org/)
- Die IP-Adresse deines MiSTer — steht im MiSTer-Hauptmenü selbst
  unten, oder in der Übersicht deines Routers

Öffne PowerShell und verbinde dich:
```
ssh root@DEINE-MISTER-IP
```
Ersetze `DEINE-MISTER-IP` durch die echte Adresse, z. B.
`ssh root@192.168.1.50`.

**Erste Verbindung — zwei Rückfragen:**

- *"Are you sure you want to continue connecting (yes/no/[fingerprint])?"*
  → tippe **yes** und Enter
- *"root@...'s password:"* → dein MiSTer-Passwort. Falls du es nie
  geändert hast, probier einfach Enter (leeres Passwort) oder `1`

Bist du drin, siehst du eine Zeile wie `root@MiSTer:~#`.

### 2. Installation — mit Internetzugang (empfohlen)

Ein einziger Befehl lädt alles automatisch:
```
curl -Ls https://raw.githubusercontent.com/dragrem2k-coder/mister-frontend/main/Scripts/install.sh | bash
```

Das Skript läuft komplett automatisch durch, keine Rückfragen. Am Ende
steht:
```
=== Fertig! ===
```

**Falls stattdessen ein Fehler kommt:** Das Skript zeigt dir die
genaue Ursache und versucht selbst einen zweiten Anlauf (bei manchen
MiSTer-Installationen sind die Sicherheitszertifikate veraltet, das
wird automatisch umgangen). Klappt auch der zweite Versuch nicht,
zeigt es dir zwei Testbefehle zum Selbst-Prüfen — dann weiter mit
Schritt 3.

### 3. Installation — ohne Internetzugang

Falls dein MiSTer keinen Internetzugang hat:

1. Lade dir den kompletten Build als ZIP herunter (von GitHub oder von
   Dragrem direkt)
2. Öffne [WinSCP](https://winscp.net/), verbinde dich mit derselben
   Adresse/Passwort wie oben
   - **Erste Verbindung:** *"Continue connecting and add host key to
     cache?"* → **Ja**
3. Lege auf dem MiSTer den Ordner `/media/fat/frontend/` an
4. Kopiere den kompletten Inhalt von `frontend/` dort hinein
5. Kopiere den kompletten Inhalt von `Scripts/` nach
   `/media/fat/Scripts/`
6. Zurück in der SSH-Sitzung, Autostart einrichten:
   ```
   chmod +x /media/fat/frontend/frontend_boot.sh
   echo '/media/fat/frontend/frontend_boot.sh &' >> /media/fat/linux/user-startup.sh
   ```

### 4. Erster Start

Einmal komplett neu starten (Stromstecker oder Reset-Taste am MiSTer),
das Frontend erscheint automatisch.

Ohne Neustart testen, per SSH:
```
python3 /media/fat/frontend/frontend.py
```

### 5. Bedienung

| Taste | Wirkung |
|---|---|
| Hoch/Runter | Navigieren (hält man gedrückt, wird's schneller) |
| Links/Rechts | Seitenweise blättern |
| Enter / A | Kategorie öffnen bzw. Spiel starten |
| ESC / B | Zurück; im Hauptmenü: Beenden-Abfrage |
| Buchstabe (Tastatur) | Springt zum nächsten Eintrag mit diesem Anfangsbuchstaben |
| F12 / Guide-Taste | Echtes MiSTer-Menü öffnen |
| F10 / X-Taste | Aus dem MiSTer-Menü zurück ins Frontend |
| Y-Taste | Nächster Song |
| F11 | Zufälliges Spiel/Kategorie |

**Wichtig, falls eine Taste "nichts tut":** Nicht jede Tastatur/jeder
Empfänger sendet für F9–F12 denselben Code. Falls z. B. F11 bei dir
nichts auslöst, geh ins System-Menü auf **"Configure buttons"** und
leg die gewünschte Aktion neu auf eine Taste deiner Wahl.

**Während ein Spiel läuft:** Die Tastatur gehört dann exklusiv dem
Core, unser Frontend bekommt normalerweise nichts mehr mit. Ausnahme:
Esc auf der Tastatur etwas länger gedrückt halten (~0,6s) bringt dich
trotzdem direkt zurück ins Frontend — funktioniert über einen Umweg,
den wir extra dafür gebaut haben. Klappt das mal nicht, geht's immer
noch über die echte MiSTer-Menü-Taste (F12 bzw. deine Pad-Menü-Taste)
→ dort **"Exit to Menu Core"** wählen.

### 6. Boxart laden

Direkt auf dem MiSTer, kein PC nötig:
```
python3 /media/fat/frontend/mister_boxart.py
```
Für schärfere Cover zusätzlich (nur sinnvoll bei HDMI):
```
python3 /media/fat/frontend/mister_boxart.py hd
```
**HD-Cover-Profil:** Das `hd`-Profil lädt zusätzlich hochauflösende
Cover für HDMI-Betrieb (größere Dateien, deutlich schärfer auf einem
1080p-Bildschirm als auf einer Röhre nötig wäre). Läuft im Hintergrund
weiter, wo der Standardlauf aufgehört hat — kannst du jederzeit mit
Strg+C abbrechen und später fortsetzen.

### 7. Spielinfos laden

```
python3 /media/fat/frontend/mister_gameinfo.py
```
Lädt Jahr, Genre und Spieleranzahl für die Spiele, für die es einen
Datenbank-Treffer gibt.

### 8. Musik hinzufügen

MP3-Dateien einfach nach `/media/fat/music/` kopieren (per WinSCP),
Frontend neu starten — Wiedergabe beginnt automatisch, zufällig
gemischt.

### 9. Später aktualisieren

Neue Version einfach nochmal mit demselben Befehl aus Schritt 2
installieren — überschreibt nur die Programmdateien, deine Musik,
Boxart und Einstellungen bleiben unangetastet. Läuft das Frontend
gerade, wird es dabei automatisch sauber beendet und mit der neuen
Version neu gestartet.

---

## Teil 2 — Stream-Overlay für OBS

*Ab hier nur relevant, wenn du streamst.*

### 10. Warum es das überhaupt gibt

Der MiSTer kann sein Menü immer nur auf **einem** Videoausgang
gleichzeitig zeigen — entweder Röhre (CRT) oder HDMI, nie beide
zusammen (eine technische Grenze des MiSTer-Scalers, kein Fehler
unseres Frontends). Läuft dein Menü also auf CRT, sieht dein
HDMI-Capture für den Stream nichts davon. Das Overlay umgeht das:
Es läuft unabhängig als kleiner Webserver und zeigt Cover, Titel und
Now-Playing direkt im Browser — OBS zeigt einfach diesen Browser an,
egal was gerade auf dem eigentlichen Videoausgang läuft.

### 11. Einschalten

Per SSH:
```
/media/fat/Scripts/stream_toggle.sh on
```
Frontend einmal neu starten (Schritt 4 oder `update_frontend.sh`),
damit der Webserver tatsächlich hochfährt.

In OBS: **Quelle hinzufügen → Browser**, als URL:
```
http://DEINE-MISTER-IP:8080/
```
Breite/Höhe auf deine Stream-Leinwand setzen (z. B. 1920×1080) — der
Rest bleibt transparent, das Overlay legt sich automatisch über dein
Bild.

### 12. Aussehen anpassen

Im Browser auf deinem PC (nicht in OBS):
```
http://DEINE-MISTER-IP:8080/admin
```
Position, Farben, was angezeigt wird — alle Änderungen wirken sofort,
kein Neustart nötig.

Wieder ausschalten:
```
/media/fat/Scripts/stream_toggle.sh off
```
und Frontend neu starten.

---

## Troubleshooting — die häufigsten Stolpersteine

1. **Frontend reagiert nach einem Update nicht mehr richtig.**
   → `/media/fat/Scripts/update_frontend.sh` ausführen (per SSH oder
   aus dem MiSTer-OSD unter Scripts) — beendet die alte Instanz sauber
   und startet neu.

2. **Eine Taste (oft F9–F12) tut nichts.**
   → Nicht jede Tastatur sendet denselben Code. System-Menü →
   "Configure buttons" → gewünschte Aktion neu belegen.

3. **`install.sh` meldet einen Download-Fehler.**
   → Steht die genaue Ursache direkt im Skript-Output. Meist ein
   Zertifikatsproblem (wird automatisch ein zweites Mal ohne
   Zertifikatsprüfung versucht) oder fehlender Internetzugang — dann
   Weg über Teil 1, Schritt 3 (WinSCP) nutzen.

4. **Keine Boxart/Musik sichtbar.**
   → Boxart: Schritt 6 einmal laufen lassen. Musik: liegt was in
   `/media/fat/music/`? Kein `mpg123` auf dem MiSTer vorhanden → läuft
   das Frontend trotzdem stumm weiter, kein Fehler.

5. **Frontend hängt/reagiert während eines Spiels nicht auf eine
   Rückkehr-Taste.**
   → Esc auf der Tastatur probieren, etwas länger halten (~0,6s).
   Klappt das nicht, über die echte MiSTer-Menü-Taste (F12) →
   "Exit to Menu Core" zurückkehren — das funktioniert immer.

6. **Liste zeigt doppelte oder längst gelöschte Spiele.**
   → System-Menü → "Rescan game list" einmal manuell ausführen (bei
   Änderungen tief in Unterordnern wird das nicht automatisch
   erkannt, aus Tempogründen bewusst so).

7. **Stream-Overlay bleibt in OBS leer.**
   → Prüfen, ob `stream_toggle.sh on` VOR dem letzten Frontend-Neustart
   lief (der Webserver startet nur beim Hochfahren). Adresse in OBS
   exakt `http://DEINE-MISTER-IP:8080/` (mit Port, ohne `/admin`).

---

Bei allem, was hier nicht weiterhilft: Dragrem fragen, mit möglichst
genauer Fehlermeldung und was du zuletzt gemacht hast. Danke übrigens
an Sutefan, der beim Testen ordentlich mitgeholfen hat.
