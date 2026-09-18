# Dragend – Miniaturen am PC rechnen

Das Verkleinern der Cover ist auf dem MiSTer der mit Abstand teuerste
Posten: ein voller Durchlauf von *Miniaturen vorbereiten* dauert je nach
Sammlung Stunden. Derselbe Bestand ist auf einem PC in Minuten durch.

Dieses Werkzeug nimmt dem MiSTer genau diesen Teil ab.

## In drei Schritten

**1. Auf dem MiSTer:**
System → Verhalten → **„Miniaturen-Auftrag für PC schreiben"**

Das Frontend schreibt `/media/fat/frontend/miniatur_auftrag.json` und
meldet, wie viele Miniaturen darin stehen. Gerechnet wird dabei nichts.

**2. Am PC:**
`Dragend-Miniaturen.exe` starten (oder `starten.bat`), Name oder IP des
MiSTer eintragen, **Start**.

Vorgabe ist `MiSTer` / Benutzer `root` / Passwort `1234` — die
Standardwerte eines MiSTer. Wer sie geändert hat, trägt seine eigenen
ein. Das Passwort wird **nicht** gespeichert.

**3. Fertig.** Beim nächsten Frontend-Start liegen die Miniaturen da.

## Die EXE bauen

`bauen.bat` doppelklicken. Das Skript holt Python-Pakete und legt
`dist\Dragend-Miniaturen.exe` an — eine einzelne Datei, die danach ohne
Python auf jedem Windows-Rechner läuft.

Voraussetzung ist einmalig Python von <https://www.python.org/downloads/>,
beim Installieren **„Add python.exe to PATH"** ankreuzen.

Wer kein eigenständiges Programm braucht: `starten.bat` startet das
Skript direkt.

## Warum der Umweg über eine Auftragsdatei

Naheliegend wäre, das Programm einfach auf den Cover-Ordner der
SD-Karte loszulassen. Das geht schief, und zwar leise.

Der Schlüssel, unter dem eine Miniatur abgelegt wird, ist

```
sha1(Pfad | Kastenbreite | Kastenhöhe | Dateigröße | Änderungszeit | Verfahrensnummer)
```

Drei dieser sechs Bestandteile sind vom PC aus nicht zuverlässig zu
bekommen:

| Bestandteil | Das Problem |
|---|---|
| **Pfad** | Über eine Freigabe heißt er `E:\...`, auf dem MiSTer `/media/fat/...`. Umlaute können anders kodiert sein. |
| **Änderungszeit** | FAT32 kennt nur Zwei-Sekunden-Schritte, dazu kommen Zeitzonen-Versätze. Eine Sekunde daneben genügt. |
| **Kastengrößen** | Sie hängen am Layout (Liste/Raster/Galerie, CRT gegen HDMI, Bildrand, Kastenstufen) — eine nachgebaute Rechnung läuft irgendwann auseinander. |

Stimmt davon etwas nicht, legt der PC fleißig Miniaturen ab, die der
MiSTer nie findet — und man merkt es erst, wenn nach Stunden nichts
schneller geworden ist.

Deshalb kommen Schlüssel **und** Kastengrößen fertig aus dem Frontend,
aus genau dem Code, der sie im Betrieb benutzt. Dieses Programm trifft
keine einzige eigene Annahme darüber.

## Was hier bewusst anders ist als auf dem MiSTer

JPEG-Cover werden am PC in voller Auflösung dekodiert. Der MiSTer lässt
TurboJPEG verkleinert dekodieren (1/2, 1/4, 1/8), weil ihm sonst die
Rechenzeit davonläuft.

Die **Zielgröße** ist in beiden Fällen dieselbe — sie kommt aus
`zielmass()` und den echten Dateimaßen. Nur die Bildpunkte, über die
gemittelt wird, sind am PC die feineren. Das Ergebnis ist also nicht
schlechter, sondern minimal besser; es ist nur nicht bitgleich. Auf den
Cache-Schlüssel hat das keinen Einfluss.

Bei PNG-Covern — der Normalfall — ist das Ergebnis **bitgenau
identisch**. `tools/test_pc_kern.py` weist das über Zufallsbilder nach.

## Dateien

| Datei | Zweck |
|---|---|
| `dragend_miniaturen.py` | Das Programm: Oberfläche, SSH/SFTP, Arbeitsverteilung |
| `dragend_kern.py` | Der Rechenkern — Kopien der Skalierroutinen aus `fe/art.py` |
| `bauen.bat` | Baut die EXE |
| `starten.bat` | Startet das Skript direkt |

`dragend_kern.py` enthält **Kopien**. Kopien laufen auseinander, und
hier fiele es nicht auf. Deshalb vergleicht `tools/test_pc_kern.py` bei
jedem Testlauf Byte für Byte gegen das Original, und
`tools/test_pc_durchstich.py` schickt einen echten Auftrag durch die
ganze Kette bis zurück zu `thumb_cache_has()`.

## Kommandozeile

Für Skripte und den Linux-/Mac-Einsatz:

```
python3 dragend_miniaturen.py --cli --host 192.168.178.160 --passwort 1234
```

## Wenn etwas nicht klappt

**„Keine Auftragsdatei gefunden"** – Schritt 1 auf dem MiSTer fehlt.

**„Das Frontend benutzt Verfahren X, dieses Programm kennt Y"** – EXE und
Frontend stammen aus verschiedenen Builds. Das Werkzeug bricht bewusst
ab, statt unauffindbare Miniaturen anzulegen. Beide auf denselben Stand
bringen.

**Verbindung schlägt fehl** – Läuft der MiSTer? Antwortet er auf `ping`?
SSH ist auf dem MiSTer ab Werk an; wurde das Passwort geändert, muss das
neue eingetragen werden.
