# Installer & Doku bereinigt — Notiz für Dragrem

Basis: v1.88 (dein aktueller GitHub-Stand). `frontend.py` und die
Programmlogik sind **unangetastet** — nur Installer-Skripte und Doku.

## 1. WinSCP komplett raus (Konsistenz)

WinSCP war quer durchs Paket verstreut (README, ANLEITUNG, CHANGELOG,
alle Installer, update_frontend.sh, PC-Tools). Überall ersetzt durch den
Standard-MiSTer-Weg ohne Zusatzprogramm: **Netzwerkfreigabe** (im
Explorer/Finder `\\<MiSTer-IP>\` bzw. `smb://<MiSTer-IP>/`) **oder die
microSD-Karte direkt am PC**. Betroffen:

- README.md (Voraussetzungen, Option A/C/D, Art-Upload, Bootanim, die
  Kommandozeilen-Warnung verallgemeinert), ANLEITUNG_fuer_Dennsen.md,
  CHANGELOG.md, KORREKTUREN_fuer_Dragrem.md
- install.sh, install_offline.sh, Scripts/install_frontend.sh,
  Scripts/update_frontend.sh (Root- und Scripts/-Kopien synchron)
- PC-Tools/boxart_fetch.py, art_convert.py, video_to_bootanim.py

Einzige verbliebene Nennung ist bewusst: „…kein WinSCP" als Beruhigung
in der Anleitung.

## 2. install_offline.sh: Paket-Suche robust gemacht (echter Bugfix)

**Problem:** Die Kopie `Scripts/install_offline.sh` brach ab
(„frontend.py nicht gefunden"), weil sie ihre Quelldateien nur direkt
neben sich suchte (`$(dirname $0)/frontend/…`) — aus `Scripts/` heraus
gibt es dort kein `frontend/`.

**Fix:** Neue `_find_src()`-Logik sucht das Paket robust — neben dem
Skript, eine Ebene höher (Skript liegt im `Scripts/`-Unterordner) und an
üblichen Stellen auf der SD (`/media/fat/MiSTer_Frontend*` usw.). Ein
Ordner gilt nur dann als Paket, wenn er `frontend/frontend.py` **und**
`install_offline.sh` enthält (`_is_pkg`) — dadurch wird das bereits
**installierte** `/media/fat/frontend` nie fälschlich als Quelle genommen
(kein Selbst-Kopieren).

**Effekt:** `install_offline.sh` läuft jetzt zuverlässig aus dem
Paketordner, aus dessen `Scripts/` und als OSD-Kopie in
`/media/fat/Scripts/`. Damit ist auch ein **Offline-Installer aus dem
OSD** möglich (Paket kopieren + `install_offline.sh` in `Scripts/` legen,
im Menü antippen).

Getestet: alle drei Wege end-to-end (echter Durchlauf, korrekt
installiert), plus der Fehlerfall „kein Paket da" (sauberer Abbruch mit
klarer Meldung).

## 3. Anleitung vereinfacht

ANLEITUNG Abschnitt 3 (Offline) war noch der alte manuelle Weg (Ordner
von Hand anlegen, `frontend/` und `Scripts/` einzeln kopieren, Autostart
per echo). Jetzt: **kompletten Paketordner rüberkopieren →
`install_offline.sh`** (macht Ordner, Kopieren und Autostart selbst).

## Kleiner Hinweis / offene Entscheidung für dich

Die Installer liegen doppelt vor (Wurzel **und** `Scripts/`). Ich habe
beide synchron gehalten, aber zwei Kopien zu pflegen ist auf Dauer eine
Fehlerquelle. Überlegenswert: nur eine Quelle pflegen und die Scripts/-
Kopie beim Build/Release automatisch daraus erzeugen.
