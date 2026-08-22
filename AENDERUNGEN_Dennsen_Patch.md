# Änderungen gegenüber Dragrems v1.90 (Dennsen-Patch)

Basis: Dragrems **v1.90** (inkl. dem detaillierten Start-Logging des
Testers) — darauf sitzen folgende Fixes. Dragrems Code/Logik ist sonst
unverändert.

## Overlay / Stream
- **Admin-Schalter reagieren wieder.** Die Schalter (Boxart, System,
  Liste, Now-Playing, Genre, Spielzeit, RA, Favorit) und das
  Ecke-Auswahlfeld ließen sich nicht umstellen — nur Größe/Farbe/Text.
  Ursache: es wurde nur auf das `input`-Ereignis gelauscht; Checkboxen
  und Auswahlfeld feuern aber `change`. Jetzt beides. (jsdom-getestet)
- **Overlay zeigt jetzt das laufende Spiel.** Beim Spielstart wird der
  Titel ans Overlay gepusht (vorher blieb es „leer", weil die
  Hauptschleife während des Spiels blockiert ist); bei Rückkehr springt
  es wieder auf den Menüstand.

## Cover
- **Tolerante Cover-Suche.** Cover aus kuratierten Sets mit führender
  Nummer (`007 Super Mario Kart (USA).art`) wurden nicht gefunden, weil
  das Spiel intern ohne Nummer heißt. Jetzt: erst exakter Name, sonst
  wird eine führende `NNN `-Nummer ignoriert. Wirkt in Frontend UND
  Overlay. (gegen echte Dateinamen getestet, inkl. Dubletten)

## Performance
- **Größere Cover-Caches** (dekodiert 40→90, skaliert 10→48). Nimmt den
  Ruckler beim Hin-und-Her-Scrollen, den die jetzt gefundenen Cover
  verursachten.

## Boot / Autostart
- **`frontend_boot.sh` robuster.** Der Wrapper wartet auf den Menü-Core
  (`/tmp/CORENAME` == "MENU"), schnitt aber — anders als das Frontend
  selbst — keine Leerzeichen/CR ab. Bei Firmware, die etwas anhängt,
  matchte "MENU" nie → 60 s Wartezeit. Jetzt wird genauso robust
  gelesen wie im Frontend.
  (Hinweis: Dragrems Team hatte diesen Wrapper noch nicht — liegt im
  Paket bei.)

## Installer & Doku
- **WinSCP überall entfernt**, ersetzt durch Netzwerkfreigabe/SD-Karte.
- **Offline-Installer robuster:** `install_offline.sh` findet sein Paket
  jetzt zuverlässig — aus dem Paketordner, dessen `Scripts/` oder als
  OSD-Kopie in `/media/fat/Scripts/` — und verwechselt das bereits
  installierte Frontend nicht mit der Quelle. Damit auch offline aus
  dem OSD installierbar.
- **Anleitung vereinfacht** (Paket kopieren → `install_offline.sh`).

## Noch offen
- **Soft-Reboot → OSD statt Frontend** (siehe separate Diagnose).
- **RA-Retry nach Zeitsync** (RetroAchievements bleibt leer, weil die
  Uhr beim Boot falsch ist und HTTPS scheitert) — auf Wunsch.
- **Asynchrones Cover-Laden** gegen den Erst-Decode-Ruckler — auf Wunsch.
