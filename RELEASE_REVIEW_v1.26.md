# Release-Review v1.25 → v1.26

Ich habe den Komplettbuild vom 21.07. vor der Freigabe durchgeprüft: alle
Python-/Shell-Dateien kompiliert, die neuen v1.20–v1.25-Features gelesen, die
sysart-Dateien validiert und die kritische Logik empirisch getestet.

**Kurzfassung: Ein echter Blocker gefunden (Mehrteiler/Disc-Spiele
verschwinden), gefixt. Der Rest sieht gut aus.**

---

## 🔴 Blocker (gefixt in v1.26): Disc 2+ verschwand aus der Liste

**Was passiert ist:** Die Region-Dedupe aus v1.23 nutzt `_canonical_key()`,
und der strippt *alle* Klammer-Zusätze. Damit landen

```
Final Fantasy VII (USA) (Disc 1)  ->  key: "final fantasy vii"
Final Fantasy VII (USA) (Disc 2)  ->  key: "final fantasy vii"
Final Fantasy VII (USA) (Disc 3)  ->  key: "final fantasy vii"
```

alle auf **demselben** Schlüssel. Die Schleife behält pro Schlüssel nur einen
Eintrag → **Disc 2 und 3 fielen komplett aus der Liste** und waren im Frontend
nicht mehr startbar. Betrifft PSX, Saturn und MegaCD, also genau die Systeme
mit mehrteiligen Spielen.

Mein Testlauf mit 9 typischen ROM-Namen: alte Logik behielt **5** Einträge,
korrekt wären **8**. Drei Discs waren weg.

Dasselbe steckte in `mister_boxart.py`, `mister_gameinfo.py` und
`boxart_fetch.py` — dort mit der Folge, dass Disc 2+ auch kein Cover und
keine Metadaten bekommen hätte.

**Fix:** Neue Regex `_DISC` erkennt Datenträger-Marker
(`Disc|Disk|CD|Side|Part|Tape|Track` + Nummer/Buchstabe). Der bleibt Teil des
Dedupe-Schlüssels, alles andere wird weiter gestrippt. Ergebnis:

- `Spiel (USA) (Disc 1)` / `(Disc 2)` / `(Disc 3)` → **drei** Einträge ✔
- `Chrono Trigger (USA)` / `(Europe)` → weiterhin **ein** Eintrag ✔
- `Sonic CD (USA)` wird **nicht** als Disc-Marker missverstanden ✔

In allen vier Dateien identisch umgesetzt (im Downloader als Funktion
`dedupe_key()`), damit Frontend und Cover-Zuordnung konsistent bleiben.

Zusätzlich zeigt `display_name()` den Disc-Marker jetzt mit an — sonst
stünden in der Liste drei identische Zeilen „Final Fantasy VII".

*Kleine bekannte Restkante:* Hat jemand Disc 1 nur als Europe- und Disc 2/3
nur als USA-Fassung, mischt die Regions-Dedupe die Fassungen. Das ist der
Logik inhärent, sehr selten, und deutlich harmloser als der bisherige
Totalverlust. Wollte ich nicht ohne Not weiter verkomplizieren.

---

## 🟡 Politur (ebenfalls in v1.26): Overlay im Kategorien-Menü

`stream_state()` las immer `items[self.item_i]` — auch auf Seite 0. Dort
gehört `item_i` aber noch zur zuletzt geöffneten Kategorie. Im Stream stand
also ein veralteter Spieltitel, während Dennsen durch die Systeme blättert.

Jetzt seitenbewusst: Auf Seite 0 zeigt das Overlay die markierte **Kategorie**
(inkl. Vorschau-Liste der Systeme), kein Cover; auf Seite 1 wie gehabt das
Spiel. Titel wird ohne Klammer-Tags angezeigt, das Cover weiterhin über den
echten Dateinamen geladen (neues Feld `art_name` — deshalb ist auch
`stream_overlay.html` minimal angepasst).

---

## ✅ Was ich geprüft habe und in Ordnung ist

- **Alle Python-/Shell-Dateien** kompilieren bzw. sind syntaktisch sauber.
- **GBC-Split** sauber übernommen — Frontend, beide MiSTer-Downloader *und*
  `boxart_fetch.py` sind konsistent (`.gb` → GAMEBOY, `.gbc` → GBC).
- **Stream-Integration** vollständig und an allen 6 Stellen korrekt; dein
  `dirname`-Guard in `stream_server.py` ist eine gute Ergänzung.
- **22 sysart-Dateien** validiert: alle korrektes `ART1`-Format, Größe passt
  zum Header, und die Namen decken sich exakt mit den `GAME_SYSTEMS`-Keys —
  kein fehlendes und kein überflüssiges Logo.
- **JUNK_TAGS** auf Fehlalarme getestet: `Demolition Man`, `Test Drive`,
  `Program Director` werden korrekt **nicht** gefiltert (die Klammer im Tag
  schützt zuverlässig). Nur ein Hinweis, kein Fehler: `(Unl)` und `(Hack)`
  filtern auch Homebrew und ROM-Hacks weg — falls User danach fragen, ist das
  Absicht, nicht Bug.
- **`filter_curated()`**: Sicherheitsnetz funktioniert wie dokumentiert
  (System ganz ohne Metadaten wird nicht gefiltert), Kategorien ohne syskey
  bleiben unangetastet. Opt-in per Flag-Datei — gute Wahl.
- **Boot-Animation**: sauber abgesichert (fehlender Ordner, leerer Ordner,
  Marker schon gesetzt → still weiter ins Menü), fps aus `bootanim.json` wird
  auf 1–30 geklemmt.
- **v1.25 OSD-Musikpause**: korrekt, `pause_for_core()`/`resume_after_core()`
  symmetrisch um die Passthrough-Schleife.
- **`start_frontend.sh`**: guter Ersatz für das alte `frontend_toggle.sh` —
  respektiert die `disable`-Datei und erkennt verwaiste Lock-Dateien.

## 📄 Kleinigkeit an der Doku

`STREAM_fuer_Dennsen.md` (die Einrichtungs-Anleitung) fehlte im Paket, nur die
Technik-Doku war drin. Habe ich wieder beigelegt und den README-Verweis
entsprechend ergänzt.

---

## Freigabe-Empfehlung

Mit dem Disc-Fix: **freigeben**. Ohne den Fix würde ich es nicht rausgeben —
verschwundene Spiele sind für die Nutzer schwer zu diagnostizieren und
sähen nach Datenverlust aus.

Was ich mangels Hardware **nicht** testen konnte und ihr beim ersten Lauf
kurz gegenprüfen solltet: einmal in ein PSX-/MegaCD-Verzeichnis mit einem
mehrteiligen Spiel schauen, ob jetzt alle Discs in der Liste stehen (und ggf.
`mister_boxart.py`/`mister_gameinfo.py` einmal neu laufen lassen, damit Disc 2+
Cover und Infos bekommt). Ebenso der reale Betrieb von Boot-Animation und
Stream-Overlay auf dem Gerät.
