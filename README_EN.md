# Dragend — MiSTer Custom Frontend v4.5

**By Dragrem2K**, with contributions from **TheRealSuTefan**, **Dfense**
and **Dennsen**.

🇩🇪 [Deutsch](README.md) · 📖 [Manual](docs/MANUAL_EN.md) ·
📄 [Manual as PDF](docs/Dragend_Manual_EN.pdf) ·
📝 [Changelog](CHANGELOG_EN.md)

A game browser for the MiSTer FPGA: cover art, game info, gamepad and
keyboard control, background music, CRT and HDMI treated as equals.
Plain standard Python — not a single extra dependency on the MiSTer.

<p align="center">
  <img src="screenshots/preview_1_kategorien.png" width="420" alt="Category menu">
  &nbsp;&nbsp;
  <img src="screenshots/preview_2_spieleliste.png" width="420" alt="Game list with cover art">
</p>
<p align="center">
  <img src="screenshots/preview_9_liste_raster.png" width="280" alt="Grid view">
  &nbsp;
  <img src="screenshots/preview_10_liste_galerie.png" width="280" alt="Gallery view">
  &nbsp;
  <img src="screenshots/preview_5_trophaeenraum.png" width="280" alt="Trophy room">
</p>
<p align="center"><sub>List, grid, gallery — and the trophy room. Every image rendered straight from the program code (<code>tools/screenshots_bauen.py</code>); cover art and save data are placeholders.</sub></p>

---

## Install: one file, one click

1. Download
   [`Frontend_Install.sh`](https://raw.githubusercontent.com/dragrem2k-coder/mister-frontend/main/Scripts/Frontend_Install.sh)
   (right-click → *Save link as*).
2. Copy it to `/media/fat/Scripts/` — over WinSCP, or with the SD card in
   your PC.
3. On the MiSTer: run **Scripts → "Frontend Install"**.

The script fetches everything else itself, sets up autostart and
launches the frontend when it is done. No SSH, no unpacking.

**Updating:** run the same script again. Your cover art, music and
settings are left untouched.

**Uninstalling:** `Frontend_Uninstall.sh` — your MiSTer is exactly as it
was. Nothing in the system is modified, no kernel, no image.

No internet on the MiSTer, or prefer SSH or a manual install? See
[Installation & Update (PDF, English)](docs/Installation_and_Update_EN.pdf).

---

## Features

### Your collection

| | |
|---|---|
| **Three views** | List, grid, gallery — for the game list *and* the main page, switchable per category (F10 / Select+Y) |
| **Cover art & game info** | Your own set under `art/`, plus the database under `/media/fat/docs` if you have it. A download script is included |
| **Game descriptions** | Shown next to the cover in gallery view |
| **Filters** | By genre, year, player count and developer (Tab / Select+L2+R2), remembered per category |
| **Search** | Type to narrow the list instantly |
| **Favourites & collections** | Your own lists across all systems |
| **Recently played** | Its own category, sorted by last launch |
| **ZIP archives** | ROMs inside archives are found and launched without ever extracting anything |
| **Single-game folders** | Dissolved automatically — matters for PSX, Mega CD and Saturn, where each game sits in its own folder |
| **ROMs on NAS/USB** | Network shares and USB numbers above 5 are discovered dynamically |

### Personal

| | |
|---|---|
| **Trophy room** | A profile screen: most-played game, favourite system, achievement count |
| **Year in review** | Statistics for the current calendar year |
| **Playtime tracker** | How long, how often, when last — per game and per system |
| **Top 10 lists** | By playtime, launch count, systems |
| **RetroAchievements** | Progress, achievement showcase (F6), popup when you earn one |
| **Completed & custom achievements** | Also for games RA does not support |
| **Easter eggs & frontend level** | Hidden achievements, anniversary notes, seasonal decorations |
| **Random pick / rate-it** | A random game you have not played, or not yet rated |

### Display & sound

| | |
|---|---|
| **CRT (15 kHz) and HDMI** | Each with its own look and layout, not one as a side effect of the other |
| **Themes** | Colour schemes, accent colour, adjustable screen margin |
| **Attract mode** | Screensaver showing cover art, delay from 30 s to 15 min |
| **Boot animation** | Your own video, or the built-in D-pad animation |
| **Music** | Your MP3s or Rainwave internet radio (five stations), one shared volume control |
| **Navigation sounds** | Generated tones, can be switched off |
| **CRT test pattern** | For setting geometry and sharpness |

### Technical & control

| | |
|---|---|
| **Language** | German / English, switchable at any time |
| **Custom key mapping** | Keyboard and gamepad freely assignable |
| **Autostart** | On/off from the menu |
| **Stream overlay for OBS** | Shows game, cover and music track in a browser source |
| **Prepare thumbnails** | Pre-compute covers once so nothing loads in later |
| **PC tool** | The same work on a Windows PC instead of the MiSTer — hours become minutes (`pc_tools/`) |
| **C module** | `libdragend.so` scales images about 100× faster. Optional; without it Python does the work |

All of it in detail: **[Manual](docs/MANUAL_EN.md)**.

---

## Controls, briefly

| Key | Pad | |
|---|---|---|
| Arrow keys | D-pad | Navigate |
| Enter | A / Start | Select, enter folder |
| Esc | B / Select | Back |
| F2 or `/` | Select + A | Search |
| Tab | Select + L2/R2 | Filter |
| F6 | Select + X | Achievement showcase |
| F7 / F8 | L2 / R2 | Mark completed / favourite |
| F10 | Select + Y | Switch view |
| F11 | — | Launch a random game |
| F12 | Guide / Mode | Open the MiSTer OSD |
| **F1** *(in a game)* | — | Back to the frontend. Esc does the same but must be held for ~0.6 s |

**F9 is deliberately left free.** MiSTer uses it itself to switch
between console and graphics mode — the frontend even injects it. The
key-mapping wizard rejects it for that reason.

The full mapping is in the
[manual PDF](docs/Dragend_Manual_EN.pdf).

---

## Requirements

- A MiSTer FPGA with a current Main and Linux image
- Free space on the SD card: around 20 MB for the frontend, plus your
  cover art
- Network for downloads and radio. Everything else works offline

Not needed: SSH, any extra package, any change to the system.

---

## Why another frontend?

The usual worry about a frontend on the MiSTer is performance — there is
no GPU, and the ARM CPU is busy already. That is exactly where the work
went: more of it into measuring and fixing than into features. You
should not feel the menu in day-to-day use.

There are alternatives, and they are good: **Zaparoo Frontend** (bigger,
maintained by several people, with NFC tags) and **Taki Udon's Console
Mode** (fully controller-driven, very approachable). What is different
here:

- **No system changes.** A Python program on an untouched MiSTer.
  Uninstalling leaves nothing behind.
- **No dependencies.** Standard library only.
- **CRT on equal footing with HDMI**, not as an afterthought.
- **The collection should feel alive**, not merely browsable — the
  trophy room, the year in review and the play diary are the point, not
  decoration.

To be straight about it: this is a hobby project, not a team product.
Fewer setups tested than a large community project would manage, but
tuned very closely to one machine that gets used every day.

---

## Where things live

| | |
|---|---|
| `frontend/` | The program. `frontend.py` plus the `fe/` package |
| `frontend/c/` | The optional C module and how to build it |
| `Scripts/` | Installer, uninstaller, cover art download |
| `pc_tools/` | The Windows thumbnail tool |
| `tools/` | Tests and diagnostics |
| `docs/` | Manual, PDFs, changelog archive |

---

## Help

If something does not work, troubleshooting is in the
[manual](docs/MANUAL_EN.md). The frontend logs to `/tmp/frontend.log` —
that file is the single most useful thing to attach to a report.

Licence: [MIT](LICENSE).
