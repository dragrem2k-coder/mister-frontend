# Korrekturen — Übergabe für Dragrem

v1.37. Vier Punkte, nach Auswirkung sortiert.

## 1. kill fror den Bildschirm ein — `frontend/frontend.py`

`kill $PID` schickt SIGTERM. Python führt bei SIGTERM ohne eigenen
Handler **keinen** `finally`-Block aus. Genau in `finally` steckte aber
das gesamte Aufräumen: Bildschirm löschen, Eingaben freigeben, F12
zurück ins MiSTer-Menü. Jedes `kill` durch `update_frontend.sh` oder
`install.sh` ließ den Bildschirm deshalb im letzten Frontend-Zustand
stehen — exklusiv gegriffene Eingabe, kein Rücksprung ins Menü.

Fix: `signal.signal(signal.SIGTERM, _handle_sigterm)`, der Handler wirft
`SystemExit`. Bestehende `finally`-Blöcke laufen dadurch normal durch.
Geprüft mit echtem Prozess und echtem `kill`.

## 2. install.sh überschrieb eigene System-Logos — `install.sh`

Die sysart-Zeile kopierte mit `cp -rf` — bei jedem erneuten Lauf (z. B.
für ein Update) wurden **alle** Logos ersetzt, auch von Hand ausgetauschte
wie eure Game-Boy-Bilder. Fix: `cp -rn` (no-clobber). Nur fehlende
Dateien werden ergänzt, vorhandene — Standard oder eigene — bleiben
unangetastet. Geprüft: eigene `NES.art` blieb erhalten, eine neue
`SMS.art` kam trotzdem dazu.

## 3. Versionsangabe im Repository falsch — `frontend/frontend.py`

Kopfzeile stand auf v1.29, während README und alle Commit-Nachrichten
bereits v1.36 zeigten. Ursache: die Versionszeile wurde jeweils nur in
der separaten Build-Kopie hochgezählt, nie im Git-Repository selbst —
der eigentliche Code war überall aktuell, nur dieser eine String hinkte
hinterher. Jetzt korrigiert (v1.37) und die fehlenden Changelog-Einträge
v1.30–v1.36 im Dateikopf nachgetragen.

## 4. Fehlender Shebang — nicht reproduzierbar

Geprüft: alle `.sh`- und `.py`-Dateien haben eine korrekte erste Zeile
(`#!/bin/bash` bzw. `#!/usr/bin/env python3`), alle Shell-Skripte sind
im Git-Repository korrekt mit Ausführungsrecht (755) hinterlegt, keine
Windows-Zeilenenden (CRLF) gefunden. Falls das an einer konkreten Datei
auftrat, bitte den Dateinamen nennen — vermutlich ein Snapshot vor
einem der obigen Fixes.

---

**Beigelegt:** `install.sh` (Offline-Fallback bereits vorhanden über
die manuelle Anleitung in der README) und `stream_server.py` +
zugehörige Dateien (OBS-Overlay, unverändert, Technik-Details weiterhin
in `STREAM_fuer_Dragrem.md`).

**Geprüft und unauffällig:** 8-Kombinationen-Regressionstest nach allen
vier Fixes, SIGTERM-Handler-Registrierung direkt verifiziert, kompletter
Build synchron zwischen Git-Repository und ZIP.
