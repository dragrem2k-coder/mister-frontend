# Dragend — Manual (complete)

This is the full description of every feature. The short overview is
in the [README](../README_EN.md) at the top level.
Deutsch: [`HANDBUCH.md`](HANDBUCH.md).

**By Dragrem2K**, with contributions from **TheRealSuTefan**, **Dfense**
and **Dennsen**.

My self-built frontend for the MiSTer FPGA: a game browser with boxart
and game info, gamepad and keyboard control, background music,
switchable German/English, custom key mapping, CRT and HDMI support,
autostart - all in pure standard Python, without a single external
dependency required on the MiSTer itself.

**About the screenshots below:** rendered directly from the actual
program code, not a photo montage - boxart, game titles and play stats
are placeholders, the system logos are real. They are generated with
`tools/screenshots_bauen.py` so they cannot go stale again. A compact
overview is additionally available in `notizen/VORSCHAU.md`.

<p align="center">
  <img src="screenshots/preview_1_kategorien.png" width="420" alt="Category menu with clock and network icon">
  &nbsp;&nbsp;
  <img src="screenshots/preview_2_spieleliste.png" width="420" alt="Game list with boxart, accent color and glow effect">
</p>
<p align="center">
  <img src="screenshots/preview_3_ordner.png" width="420" alt="Folder navigation for multi-CD games">
</p>
<p align="center"><sub>Left: main menu with clock, network icon, accent color and pulsing highlight &nbsp;|&nbsp; Center: game list with boxart, glow effect and drop shadow &nbsp;|&nbsp; Right: folder navigation - boxart also appears at the folder level for multi-CD games</sub></p>

**Not just a game list** - the actual heart of the idea are screens like
these, which make your own collection feel personal instead of merely
searchable:

<p align="center">
  <img src="screenshots/preview_5_trophaeenraum.png" width="420" alt="Trophy Room - personal profile screen">
  &nbsp;&nbsp;
  <img src="screenshots/preview_6_jahresrueckblick.png" width="420" alt="Year in Review - stats for the current calendar year">
</p>
<p align="center"><sub>Left: Trophy Room - cover of your most-played game, favorite system, achievement counter &nbsp;|&nbsp; Right: Year in Review - limited to the current calendar year, not "since records began"</sub></p>

**Three views, everywhere** - both the game list *and* the main page can
be switched between list, grid and gallery (section 8r):

<p align="center">
  <img src="screenshots/preview_9_liste_raster.png" width="280" alt="Game list as a dense grid">
  &nbsp;
  <img src="screenshots/preview_10_liste_galerie.png" width="280" alt="Game list as a gallery with a large cover and a neighbour strip">
  &nbsp;
  <img src="screenshots/preview_8_hauptseite_galerie.png" width="280" alt="Main page as a gallery with category badges">
</p>
<p align="center"><sub>Left: grid - 21 games at a glance on HDMI &nbsp;|&nbsp; Center: gallery - large cover, data beside it, neighbours as a strip &nbsp;|&nbsp; Right: the same gallery on the main page, with the category badges</sub></p>

**And on a CRT?** That is the question a view lives or dies by, so here
are the same views at 320x240:

<p align="center">
  <img src="screenshots/preview_crt_1_liste.png" width="240" alt="CRT: list">
  &nbsp;
  <img src="screenshots/preview_crt_2_raster.png" width="240" alt="CRT: grid">
  &nbsp;
  <img src="screenshots/preview_crt_3_galerie.png" width="240" alt="CRT: gallery">
</p>
<p align="center"><sub>CRT 320x240, original size - list, grid, gallery</sub></p>

## Installing: one file, one click

You only need **a single file** on the MiSTer, not the whole package:

1. Download
   [`Scripts/Frontend_Install.sh`](https://raw.githubusercontent.com/dragrem2k-coder/mister-frontend/main/Scripts/Frontend_Install.sh)
   (right-click → *Save as*).
2. Copy that file to `/media/fat/Scripts/` — via WinSCP, or just put
   the SD card into your PC.
3. On the MiSTer, in the OSD: run **Scripts → "Frontend Install"**
   once.

That's it. The script downloads everything else itself, sets up
autostart and launches the frontend at the end. No SSH, no terminal,
no unpacking.

The same script is also the **update path**: just run it again. Your
own boxart, music and settings stay untouched, only the program files
are replaced.

No internet on the MiSTer → [Option C](#option-c-without-internet-offline-from-the-package).
All the ways in detail are in [section 3](#3-installation-step-by-step).

## Why a custom frontend?

The MiSTer community keeps debating whether a graphical frontend even
makes sense - the concern is usually performance: MiSTer has no GPU, and
a heavyweight menu on the Linux side could put additional load on the
already-busy ARM CPU. A legitimate concern, and that's exactly where my
focus was while building: most of the time went not into new features
but into targeted performance work (among other things a boxart drop
shadow that alone ate up 60% of the drawing time on HDMI - found and
reduced to a fraction). The goal was for the menu to be imperceptible in
everyday use when you're not actively using it.

With **Zaparoo Frontend** there is now also an actively developed
community project with a similar goal for MiSTer (browse your library,
boxart, recently played, plus NFC tags) - anyone looking for a larger
solution maintained by multiple people, or who wants NFC cards to launch
games, should take a look. Likewise, **Taki Udon's Console Mode** is now
a very approachable solution that is fully controllable by gamepad
(paired with the SuperStation One, but works on any MiSTer).

What's different here:
- **No system modification, reversible at any time** - this is a
  Python program that runs on a completely unmodified MiSTer. No swapping
  of the kernel/Linux image, no additional hardware needed. Try it out
  without risk: one command uninstalls it cleanly (see `Scripts/Frontend_Uninstall.sh`),
  and your MiSTer is exactly as it was before.
- **No external dependency** - pure Python from the standard library,
  runs without a single additional package.
- **CRT and HDMI treated equally** - both with specially tuned looks and
  speed, not just "HDMI with CRT compatibility as a side effect".
- **Small and comprehensible** - `frontend/frontend.py` plus the
  `frontend/fe/` package of cleanly separated modules, no abstraction layers, easy to read for anyone who wants to
  tweak something themselves.
- **Your collection should feel alive, not just be quick to navigate** -
  Trophy Room, Year in Review, Game Diary, Collections and a small
  easter-egg system are not add-ons here, but the actual heart of the
  idea.

To be honest: this is a hobby project, not a team product. Fewer tested
setups than a large community project, but very precisely tuned to my
own, daily-used hardware - including a fairly detailed development
history to read up on (`CHANGELOG.md`).

## Table of contents

1. Package contents
2. Requirements
3. Installation step by step
4. Usage
5. Setting up background music
   - 5b. Internet radio (Rainwave)
6. Loading boxart and game info
   - 6b. Automatic list cleanup + curated list
7. System background images — removed in Build 87
   - 7b. System art box in the category menu
8. Setting up CRT screens (15 kHz)
   - 8b. Visual refinements
   - 8c. Recently played, loading progress
   - 8d. Attract mode / screensaver
   - 8e. Favorites
   - 8f. Clock synchronization
   - 8f-2. ROMs on a NAS/network drive
   - 8g. Themes/color schemes
   - 8h. Navigation sound effects
   - 8h-2. Random Pick: the draw with sound
   - 8h-3. Arranging the main page yourself
   - 8h-4. Remembered filters with a name of your own
   - 8h-5. Core updates: what's new
   - 8h-6. NFC tags via Zaparoo
   - 8h-7. Re-reading only what changed
   - 8h-8. Metadata from a `gamelist.xml`
   - 8b-2. Portrait mode (TATE)
   - 8g-2. Your own colour scheme: save and edit
   - 8v. MiSTer's own fonts
   - 8w. Shadow masks
   - 8x. Your own background images
   - 8y. MiSTer's own favourites
   - 8z. Cores: choosing a build and updating
   - 8q. Autostart on/off
   - 8i. Playtime tracker
   - 8j. Top 10 lists
   - 8k. RetroAchievements progress
   - 8l. Choosing a standard or RA core
   - 8m. Completed status + your own achievements
   - 8n. Easter-egg system (secrets) + frontend levels
   - 8o. CRT test pattern
   - 8p. Contributors
   - 8r. Views: list, grid, gallery
   - 8s. ROMs inside ZIP archives
   - 8t. Game descriptions
   - 8u. Covers while scrolling
9. Switching language
10. Custom key mapping
11. Boot animation (startup video)
12. Stream overlay for OBS (optional)
13. Troubleshooting
   - 13b. MiSTer Linux from 2026-09-07 (kernel 6.18)
14. Known limitations
15. Start options (`--show`, `--bench`, `--demo`, `--help`)
16. The system menu from A to Z — everything in one place

---

## 1. Package contents

| File                            | Destination on the MiSTer        | Purpose |
|----------------------------------|----------------------------------|-------|
| frontend/frontend.py            | /media/fat/frontend/             | The frontend itself (v4.8) |
| frontend/frontend_boot.sh       | /media/fat/frontend/             | Autostart wrapper (on every boot) |
| frontend/mister_boxart.py       | /media/fat/frontend/             | Boxart downloader (runs on the MiSTer) |
| frontend/mister_gameinfo.py     | /media/fat/frontend/             | Game-info downloader (runs on the MiSTer) |
| frontend/stream_server.py       | /media/fat/frontend/             | Web server for the stream overlay (optional) |
| frontend/stream_overlay.html    | /media/fat/frontend/             | OBS browser source (optional) |
| frontend/stream_admin.html      | /media/fat/frontend/             | Stream overlay configuration (optional) |
| Scripts/Frontend_Install_Remote.sh | /media/fat/Scripts/           | Installation with internet access (downloads from GitHub) |
| Scripts/Frontend_Install_Offline.sh | /media/fat/Scripts/          | Installation without internet access (from this package) |
| Scripts/Frontend_Uninstall.sh   | /media/fat/Scripts/              | Remove everything cleanly, optionally keep your own data |
| Scripts/Frontend_Install.sh     | /media/fat/Scripts/              | Install/update directly from the MiSTer menu (Option A) |
| Scripts/Frontend_Start.sh       | /media/fat/Scripts/              | Start the frontend manually from the MiSTer OSD |
| Scripts/Frontend_Update.sh      | /media/fat/Scripts/              | Restart cleanly after a file update (1 command instead of several) |
| Scripts/Frontend_Boxart_Download.sh | /media/fat/Scripts/          | Start the boxart download from the OSD/frontend |
| Scripts/Frontend_Gameinfo_Download.sh | /media/fat/Scripts/        | Start the game-info download from the OSD/frontend |
| Scripts/Frontend_Stream_Toggle.sh | /media/fat/Scripts/            | Toggle the stream overlay on/off (optional) |
| PC-Tools/art_convert.py         | stays on the PC (Python+Pillow)  | Images -> .art format, including background images |
| PC-Tools/boxart_fetch.py        | stays on the PC (optional)       | Alternative: download boxart on the PC instead of the MiSTer |
| PC-Tools/video_to_bootanim.py   | stays on the PC (Python+Pillow)  | Video/image sequence -> boot animation |
| PC-Tools/obs_setup.py           | stays on the PC (optional)       | Create a local OBS overlay file with a hard-coded MiSTer IP |
| PC-Tools/OBS_Setup_starten.bat  | stays on the PC (optional)       | Windows double-click launcher for obs_setup.py |
| music/                          | (for reference only, contents irrelevant) | Target folder for your own MP3s |

All scripts that show up in the MiSTer OSD (`Scripts/`) deliberately
share a `Frontend_` prefix, so they sort together in the OSD menu and are
recognisable at a glance (instead of disappearing among other people's
scripts under mixed names like `install_frontend.sh` or
`stream_toggle.sh`, as they did before). If you still have an older
version installed: the rename happens automatically with the next update,
no manual cleanup needed.

## 2. Requirements

- A MiSTer FPGA with current firmware (Python 3 is always already
  installed)
- Network access via SSH (`ssh root@<MiSTer-IP>`) and WinSCP (or another
  SFTP client) for copying the files
- For background music: `mpg123` must be present on the MiSTer. Check via
  SSH: `which mpg123` - if a path comes back (e.g. `/usr/bin/mpg123`),
  everything is fine. **If it's missing:** `mpg123` actually belongs to
  the MiSTer firmware itself, so it is not a separately installable
  package - a one-time "Update All" in the MiSTer OSD (bringing the whole
  firmware up to date) usually helps, then check again. If it still comes
  back empty: the frontend keeps running normally, just without music.
- For the PC tools (optional): Python 3 and `pip install Pillow`

## 3. Installation step by step

### Option A: One file, directly from the MiSTer menu (easiest)

No SSH/terminal needed - just copy a single, small file once via WinSCP:

1. Download
   [`Scripts/Frontend_Install.sh`](https://raw.githubusercontent.com/dragrem2k-coder/mister-frontend/main/Scripts/Frontend_Install.sh)
   (right-click -> Save as, or browser download).
2. Copy the file to `/media/fat/Scripts/` via WinSCP.
3. In the MiSTer OSD: tap **Scripts -> "Frontend Install"**.

The rest runs by itself - download, set up, autostart. At the end, press
a key briefly to get back to the menu. Then reboot once, done.

Can be run again at any time (e.g. for an update) - your own data (music,
boxart, settings) stays untouched, only the program files are replaced.
Requires internet access on the MiSTer (usually available automatically
on a home network).

### Option B: Via SSH, one command

If you already have an SSH session open anyway:
```bash
curl -Ls https://raw.githubusercontent.com/dragrem2k-coder/mister-frontend/main/Scripts/Frontend_Install_Remote.sh | bash
```
(If `curl` is missing, `wget -qO- ... | bash` also works - the script
tells you if both are missing.)

Does exactly the same thing as Option A, just via the terminal instead of
the MiSTer menu. Can likewise be run again at any time, your own data
stays untouched.

### Option C: Without internet (offline from the package)

If the MiSTer has no internet access, a specific version is desired, or
Option A/B fail due to outdated SSL certificates: copy the complete
package to the MiSTer via WinSCP, then via SSH or from the OSD under
Scripts:
```bash
cd /media/fat/MiSTer_Frontend   # folder you copied the package into
./Scripts/Frontend_Install_Offline.sh
```
Since Build 140 it no longer matters where you start the script from:
the package folder, its `Scripts/` subfolder directly, or a copy in
`/media/fat/Scripts/` for the OSD. Before that it only found its own
package when it sat one level higher (thanks to **SuTe** for the
report).
Asks interactively about autostart and stream overlay. Without prompts:
```bash
./Scripts/Frontend_Install_Offline.sh --yes                # autostart on, overlay off
./Scripts/Frontend_Install_Offline.sh --yes --stream        # additionally overlay on
./Scripts/Frontend_Install_Offline.sh --yes --no-autostart  # without autostart
```
Running it again is safe: your own boxart, metadata, music, self-replaced
system logos and settings stay untouched, and the previous program files
are automatically backed up beforehand (`frontend/backup_<date>/`).

### Option D: Manually via WinSCP

1. On the MiSTer, create via WinSCP: `/media/fat/frontend/`
2. Copy all files from the `frontend/` folder there.
3. Copy all files from the `Scripts/` folder to `/media/fat/Scripts/`.
4. Set up autostart once via SSH so the frontend appears automatically on
   every power-on:
   ```bash
   chmod +x /media/fat/frontend/frontend_boot.sh
   echo '/media/fat/frontend/frontend_boot.sh &' >> /media/fat/linux/user-startup.sh
   ```
5. Reboot the MiSTer once - the frontend should appear automatically.

### After installation (all three ways)

Manual start (e.g. for testing, without rebooting), via SSH:
```bash
python3 /media/fat/frontend/frontend.py
```

Or from the actual MiSTer OSD: main menu -> Scripts -> `Frontend_Start`
(MiSTer automatically lists every `.sh` script in `/media/fat/Scripts/`
in the OSD).

**Removing it again:** `./Scripts/Frontend_Uninstall.sh` (in the package folder)
reverts everything - autostart, Scripts, optionally the program files
themselves. Asks whether your own boxart/music/settings should be kept
(`./Scripts/Frontend_Uninstall.sh --yes` for "remove everything" without
prompts, `./Scripts/Frontend_Uninstall.sh --keep-data` for "remove only
program files" without prompts).

## 4. Usage

Two pages: page 1 (main menu) shows only the categories (Systems,
Arcade, Scripts, System) as a large list; Enter/A opens a category on
page 2, where the game list is on the left and, for game systems, a wide
boxart+info column is on the right.

**The "System" category is divided into 7 thematic groups**
(RetroAchievements, Statistics & Achievements, Display & Sound, Options,
Input & Language, Info, Maintenance) - just like with your own ROM
subfolders, click in once, then select the desired setting. All the
individual functions further down in this README ("System menu -> ...")
are therefore one click deeper than before, but otherwise unchanged.

**"Continue Playing" at the very top of the main menu** (if present):
specifically suggests the game you last started but haven't yet marked as
completed (F7, see section 8m). Disappears by itself once nothing is left
open.

**"Collections"** (if present): automatic, curated groupings from your
library - currently "Discovered this year" (games you started for the
first time in the current calendar year) and "Bite-sized games" (games
with a short average session length, at least 2 launches required).
Appears only if something actually fits.

**"Zufalls-Zock"** (Dennsen's rating format, in the main menu under
System or as its own menu item depending on configuration): pulls
three random, not-yet-rated games at once for you to choose from -
without repeats, until all of them have had a turn. Handy when "don't
know what to play" should become an actual decision, rather than just
suggesting a single random game (see F11 in the table below).

**Your own folder structure is adopted 1:1.** If you have organized your
ROMs in subfolders (e.g. "1 US-A-E", "2 Popular"), the frontend shows
these folders as their own clickable entries - nested arbitrarily deep,
exactly as stored on the media. Enter/A on a folder enters it, ESC/B goes
up one level (only at the very top does it return to the categories).
Folders always appear first in the list, then the games - both
alphabetically. Systems without subfolders still show the normal list
immediately.

**Clock + network icon at the bottom right of the main menu.** The clock
(HH:MM) is always there; the small bar icon next to it appears only when
a network is connected. Pure status indication ("network present"), not
actual signal strength. Rechecked every 5 seconds, without generating any
real network traffic.

| Input                            | Function |
|-------------------------------------|----------|
| Up/Down                            | Navigate one position (accelerates when held: 1->2->4->10) |
| Left/Right                         | Page through (grows when held: 1->2->3->5 screen pages) |
| Enter/A                            | Open category/folder or launch game/script |
| ESC/B                              | Back one folder/menu level; in the main menu: quit confirmation |
| A single letter (keyboard, A-Z)    | Jump directly to the next entry with that initial letter |
| F12 / Guide button                 | Open the actual MiSTer OSD (joystick mapping, ini settings) |
| X button (pad)                     | From the OSD back to the frontend |
| Y button (pad) / F5 or media "next track" key (keyboard) | Next song (manual music change) |
| F11                                 | Random game/category ("don't know what to play") |
| F8 / L2 or R2 button                | Toggle favorite (game entries only) |
| F7                                  | Toggle completed status (game entries only) |
| 3x Select in a row (pad)           | Quit confirmation (like ESC) |
| In a running game: **F1** on the keyboard | Straight back to the frontend, no hold time and no detour through the MiSTer OSD |
| In a running game: Esc on the keyboard, hold ~0.6 s | Same as F1, but with a hold time - needed because many games use Esc for their own pause menu |
| In a running game: **F5** on the keyboard | Reset the running core, no hold time (all cores, including RA - does NOT reload the core, RA progress is kept) |
| / or F2 (keyboard) | Start full-text search - matches anywhere in the name, not just the start (both keys trigger the exact same function) |
| In a running game: F12 -> "Exit to Menu Core" | Alternative via MiSTer's own menu |

**Returning from a running game:** As soon as a core is running, MiSTer
completely locks the normal keyboard/pad layer (verified: `cat
/dev/input/eventX` returns 0 bytes during a game, no matter what you
press) - Start+Select therefore never arrives during the game
itself; that is a platform limitation, not a frontend bug. But there is a
way around it: the *raw* HID layer of a connected keyboard remains
readable even during a running game. **F1 takes you straight back to
the frontend, immediately** - no hold time, because cores practically
never use that key. Esc does the same but needs to be held for about
0.6 s: many games use Esc for their own pause menu, so a short press
must not throw you out by accident. If that doesn't work for some reason (e.g.
no keyboard connected), the route via MiSTer's own menu remains: F12/menu
button on the pad opens MiSTer's on-screen menu over the running game,
choose "Exit to Menu Core" there - as soon as MiSTer really switches to
the menu, the frontend takes over again automatically.

## 5. Setting up background music

1. Copy your own MP3 files to `/media/fat/music/` (create the folder if
   needed).
2. Restart the frontend - playback starts automatically, randomly
   shuffled.
3. Control:
   - Y button on the pad, F5, or the "next track" media key on the
     keyboard (whichever's handy): next song
   - System -> "Music: On/Off": turn music completely on/off (state
     persists across restarts)
   - Music pauses automatically as soon as a game or script starts, and
     resumes automatically once you're back in the frontend
4. The currently playing track scrolls at the top next to the "MiSTer"
   logo (main menu) and below the game info in the boxart block (category
   view).

Without MP3s in the folder or without `mpg123`, the frontend simply stays
silent - no error message, it just keeps running without music.

## 5b. Internet radio (Rainwave)

Besides your own MP3s, an internet radio can play as background music:
**Rainwave** (rainwave.cc), a free station for video-game music - with
five channels (Game, OCReMix, Covers, Chiptune, All). It runs via the
same `mpg123` as MP3 playback, so it needs no additional software - just
an internet connection.

**Switching:** In the System menu under **Display & Sound -> "Music source"**.
The entry cycles in turn: MP3 (local files) -> Radio: Game -> OCReMix ->
Covers -> Chiptune -> All -> back to MP3. The chosen setting persists
across restarts.

The on/off switch ("Music: On/Off") is unaffected by this - it only
controls *whether* music plays; you choose the source separately.

**Now playing:** In radio mode, the scrolling text shows the station's
real currently-playing track (artist - title) instead of a filename -
the same display as for MP3s, at the top next to the "MiSTer" logo and in
the boxart block. Especially handy for streamers: the title also flows
into the OBS overlay automatically (section 12), without any extra setup.

Without an internet connection, or if the stream briefly drops, the
frontend automatically tries to reconnect. Rainwave is a free service -
we only listen in passively here (anonymously, no login needed).

## 6. Loading boxart and game info

Directly on the MiSTer, no PC needed (can also be started from the
Scripts category in the frontend itself):
```bash
python3 /media/fat/frontend/mister_boxart.py            # covers, CRT size
python3 /media/fat/frontend/mister_boxart.py hd          # additionally sharp covers for HDMI
python3 /media/fat/frontend/mister_gameinfo.py           # year/genre/player count
```

**Where the covers come from - four stages, first hit wins:**

1. **From the MiSTer itself.** If the cover is already in the artwork
   database under `/media/fat/docs` or in an artpack, there is nothing
   to download - the frontend shows it anyway.
2. **Ready-made PNG/JPG from a mirror.** Stored as-is: no decoding, no
   conversion.
3. **Pre-scaled `.art` from the same mirror.**
4. **thumbnails.libretro.com**, independent of the mirror, as the last
   safety net.

The file extension is determined from the **content**, not from the
name on the server - some servers report the wrong file type for
images. Anything that is not an image is not written but passed on to
the next stage.

**Foreign artwork and game data from the device** can be turned off
under *System -> Display & sound -> "Foreign artwork/data"*. The default
is **on**: the source only fills gaps and never replaces your own
artwork.

### Getting covers through Update All — possible, but not required

Many people already have the covers on their card without knowing it.
**Update All** (the well-known MiSTer maintenance script) can install
the *MiSTer Game Artwork Database*, which then lands under
`/media/fat/docs/<system>/Artwork/`. On the device of the user who
reported this, **21,198 covers** were sitting there unused.

The frontend has been reading that folder since Build 115. Nothing has
to be copied, renamed or converted: if the cover is there, it is shown
(stage 1 of the list above).

**This is an option, not a requirement.** If you don't use Update All,
simply download the covers as described above via *System →
Maintenance → "Download boxart"* — the result is the same. And if you
have both, there is no conflict: your own artwork always wins, the
database only fills gaps.

The same folders also provide **year, genre, developer and player
count** (`gameinfo.tsv`) and, since Build 139, the **game
descriptions** (see section 8t).

### "Prepare thumbnails" — what it does and when it is worth it

Found under *System → Maintenance → "Prepare thumbnails"*.

**The problem it solves.** Covers are stored at original size, often
900×1200 pixels. On screen they appear in three much smaller boxes —
on HDMI 733×909 for the list, 342×456 for the gallery and 176×235 for
the grid. So every cover has to be scaled into *each* of those boxes
the first time you look at it, and that takes one to two seconds on the
MiSTer. That single moment is the brief stutter you notice when
browsing a new collection for the first time.

**What the menu item does.** It computes those thumbnails in advance
and stores them in a cache on the SD card. From then on they are
instant — including after a reboot, because the cache survives power
off.

**What it costs.** Time, once, and space on the card. With a large
collection it runs for a while; you can stop it with a key press at any
time and continue later, and whatever was already computed is kept. CRT
and HDMI have separate caches — if you use both, run it once per mode.

**Do you have to?** No. Everything works without it; the frontend just
computes each thumbnail the moment you first look at that game. With a
small collection you will barely notice. With several thousand games
and a wish for smooth browsing, let it run once overnight.

The cache can be cleared under *System → Maintenance → "Clear
thumbnail cache"* — separately for CRT and HDMI.
**If you use both CRT and HDMI, run both lines** - without the `hd` run,
the frontend on HDMI simply upscales the small covers intended for the
tube (looks pixelated). With `hd`, both sizes exist side by side (`art/`
for CRT, `art_hd/` for HDMI), and the frontend automatically picks the
matching one - nothing has to be deleted/replaced.

**Also for Arcade** - runs along automatically, no separate option
needed. Finds all `_Arcade` folders, collects the MRA filenames (which
for MiSTer collections is usually already the game title) and loads
matching covers from `libretro-thumbnails/MAME`. Games without a database
match remain without a cover, as with the consoles, but end up in
`fehlend_ARCADE.txt`.

- Both scripts search your ROM folders (SD card and connected USB drives)
  and fetch matching data automatically from thumbnails.libretro.com or
  the libretro-database (each with a GitHub mirror as fallback)
- Runs with several parallel downloads instead of one after another -
  makes a noticeable difference with large collections
- Name matching: exact -> without region tags -> similarity search,
  preferred in this order: USA > World > Europe > Japan > Germany
- Can be aborted at any time with Ctrl+C, resumes exactly where it left
  off on the next start
- ROMs without a found cover end up in `fehlend_<System>.txt` in the
  respective `art` folder under `/media/fat/frontend/`

Alternative for the PC (`PC-Tools/boxart_fetch.py`, needs `pip install
Pillow`, also with parallel downloads): query the same source from your
computer and upload the finished `.art` files via WinSCP. Useful for your
own image sources (e.g. emumovies.com) - for that, `PC-Tools/art_convert.py`
converts any PNG/JPG into the `.art` format:
```
python art_convert.py --images "my_images/SNES" --roms "D:\roms\SNES" --out "art_out\SNES" --profile sd
```

## 6b. Automatic list cleanup + curated list

The game scan cleans up automatically, without touching your own folder
structure:
- Goes arbitrarily deep - your own sorting like "1 TOP 100/subfolder/
  game.chd" is found completely.
- Known boot/test files (`boot.rom`, `mister-boot.*` etc.) are hidden.
- Beta/proto/demo/hack/bad-dump tags are filtered out.
- Multiple regions of the same game ("Game (USA)", "Game (Europe)") are
  merged into one entry - best region wins (USA > World > Europe >
  Japan > Germany). With complete No-Intro sets this can noticeably reduce the
  list size.
- **Japan-only ROMs are hidden entirely** (not just merged, but filtered
  out in general) - detects "(Japan)"/"[Japan]" and "(J)". Multi-region
  tags like "(Japan, USA)" are kept, since that version also covers
  USA/Europe. Applies uniformly to the frontend scan AND all three
  boxart/info tools.

Additionally optional in the System menu: **"Curated list (DB-matched
only)"** shows only games with a match in the libretro database - like
the XML database per system used to be in Hyperspin. If a system has no
metadata loaded at all, it is NOT filtered (no risk of an empty list).
Takes effect immediately, without a restart.

## 7. System background images — removed in Build 87

Up to Build 86 a dimmed console photo could be placed in
`/media/fat/frontend/bg/` per system. It showed up in two places: full
screen behind the game list, and small in the box art column as a
stand-in when a game had no cover of its own.

**Both were removed in Build 87**, for measured performance reasons:

- The full-screen background had to be recomposed on every category
  change - 8.3 MB at 1920x1080, row by row in Python - and up to four of
  those full-screen buffers were kept in memory, about 33 MB at 1080p.
- The small stand-in in the box art column was the single most expensive
  operation in the whole frontend at 200-700 ms per scaling, and no
  prewarmer covered it. Anyone with many games without their own cover -
  and every folder counts as one - paid that repeatedly while browsing.

Missing cover art now shows the plain placeholder. The
`/media/fat/frontend/bg/` folder is no longer read and can be deleted;
the "System backgrounds" menu entry is gone accordingly.

## 7b. System art box in the category menu

In the main category menu (page 1), an art box appears to the right of
the list with the logo/cover of the currently highlighted system -
changes live as you page up/down through the categories.

**Already included in the build** (located in `frontend/sysart/`, no
longer needs to be created yourself): **all 48 systems** have a
real logo. Build 79 moved the logos that had been sitting in
`frontend/sysart/_weitere_systeme_noch_nicht_unterstuetzt/` into place
(Atari 5200/7800, Jaguar, ColecoVision, CD-i, Sega 32X, Super Game Boy,
TurboGrafx-CD), and Build 80 added 3DO, Atari 2600, Atari Lynx, Famicom
Disk System, Gamate, Intellivision, Neo Geo CD, Vectrex and WonderSwan.

The remaining 15 show the subtle placeholder; which ones they are and
what format new artwork needs is documented in
`docs/LOGOS_NACHLIEFERN.md` (German).

Create your own/additional images - since Build 80 there is a dedicated
tool for this (`art_convert.py` is for boxart and scales to the small
target boxes, which does not fit here):
```
python PC-Tools/sysart_convert.py console_logo.png frontend/sysart/SMS.art
```
Add `--fluten` if the logo sits on a solid black or white background,
and `--aufhellen` on top of that for black lettering (it would be
invisible on the dark card otherwise).
Copy the file to `/media/fat/frontend/sysart/<systemkey>.art` (e.g.
`sysart/SMS.art`, `sysart/NES.art`). Without a matching file, a subtle
placeholder appears instead of an error - so it can be filled in over
time.

## 8. Setting up CRT screens (15 kHz)

For the menu/frontend on a 15 kHz tube display, this block at the end of
`/media/fat/MiSTer.ini` does the job (it is managed automatically via
System -> "Menu video: HDMI -> switch to CRT" in the frontend, so it
normally does not have to be entered by hand):
```ini
[Menu]
vga_scaler=1
fb_terminal=1
video_mode=320,8,32,24,240,4,3,16,6048
```
The scaler can only do one mode at a time - the menu is therefore visible
either on the CRT or on HDMI (games themselves still run on both outputs
simultaneously, independent of the menu).

**Safety net against "no signal":** If you switch from HDMI to CRT via
System -> Display & sound while no CRT is actually connected, the
TV/monitor stays black after the automatic reboot - and since real CRT
detection isn't technically possible on the MiSTer, you'd be locked out
without physical access to the hardware. That's why the frontend shows a
clear notice with a countdown right after switching. If not a single
real input (key/pad) arrives within 20 seconds - e.g. because no CRT is
actually connected and the screen simply stays blank - the frontend
automatically switches back to HDMI and reboots on its own. A single
input within those 20 seconds permanently confirms CRT mode instead; the
notice disappears and nothing gets reset.

## 8c. Recently played, loading progress

Active automatically, no setup needed:
- **"Recently played"**: a new category at the very top of the main menu
  as soon as you've launched your first game - up to 100 entries, newest
  first. Appears only after the first game launch.
- **Loading progress**: shows a progress bar if the game list actually
  has to be re-read from disk. On a normal, fast cache hit, none of this
  appears.
- Before an actual scan, the frontend waits briefly (up to 4 seconds) in
  case USB drives are only just mounting after a cold start - prevents a
  scan started too early from mistakenly finding fewer games.

## 8b. Visual refinements

Active automatically, no setup needed:
- **Per-system accent color**: highlight, boxart frame and art-box frame
  take on a color matching the current system (NES red, Sega blue, SNES
  purple, etc.).
- **Pulsing highlight**: a subtle, deliberately slow brightening/dimming
  of the selection.
- **Glow effect** around the highlight, **drop shadow** under the boxart
  cover.
- **Equalizer bars** next to the now-playing display while music is
  playing (purely animated, not a real volume measurement).

If that's too busy for you: the pulsing highlight and the equalizer bars
can each be turned off individually via System -> Display & sound (handy
e.g. for testing whether that helps HDMI scrolling). The glow effect and
drop shadow stay code-only for now - let me know if you'd like a menu
switch for those too.

## 8d. Attract mode / screensaver

After 90 seconds without input (adjustable under *System -> Options
-> "Attract delay"*, from 30 seconds to 15 minutes), a random game automatically appears
full-screen with cover, title and system name - then changes every 6
seconds (avoiding repeats as long as more than one game is present). Any
key exits attract mode immediately and takes you back exactly to where
you were before - the key itself doesn't trigger anything additional.

Handy for demos/streams: if the menu runs in the background for a while,
it shows a kind of slideshow of your own collection by itself.

Can be turned on/off via the System menu (default: on). Only actual game
systems are affected (Recently played/Scripts/System are left out).

## 8e. Favorites

Your own, deliberately curated selection - independent of "Recently
played" (which fills up automatically; favorites only through you). F8
(keyboard) or **L2 or R2** (gamepad) toggles the favorite status of the
currently highlighted game - works only on actual game entries, not on
folders, scripts or cores. Favorited games show a small "*" before the
name.

L2/R2 work regardless of whether your pad sends them as a dedicated
button or as an analog trigger (common on many Xbox-style controllers) -
both are recognized. L1/R1 remain responsible for paging, but can be
remapped just like any other button via the assistant (section 10).

Appears as its own "Favorites" category directly after "Recently played"
and disappears again automatically once no favorites remain.

## 8f. Clock synchronization

MiSTer has no battery-backed real-time clock - the system clock starts
near zero on every reboot. The frontend therefore fetches the current
time itself via the internet (SNTP), right at the start - provided a
network is present. Without a network, nothing is attempted; with a
network but no answer from the time server, the attempt aborts by itself
after a short time.

**Time zone:** The time server always delivers UTC - since MiSTer has no
time-zone database of its own, the offset to your local time has to be
set manually once. In the System menu: "Time zone: UTC±X -> next" cycles
in 0.5-hour steps (e.g. UTC+2 for German summer time, UTC+1 for winter
time). After switching, the clock is re-synchronized immediately, no
restart needed (provided a network is present at that moment). Without a
setting: UTC.

## 8f-2. ROMs on a NAS/network drive

If your ROMs are on a network drive via CIFS/SMB or NFS instead of on an
SD card/USB, it can happen at boot that our scan starts before the
connection is really up - the then-empty or incomplete game list would
even be cached permanently.

For that there is the System-menu option **"Wait for NAS/network at
startup"** (default OFF). When enabled, the frontend first waits at
startup for a network connection and for the contents of the ROM folders
to stop changing before it scans. For SD card/USB (most users) just leave
the option off - there it would only cause unnecessary delay.

## 8g. Themes/color schemes

In the System menu: "Color scheme" cycles through three color schemes in
turn - Dark (default), Light and Retro Green. The per-system accent
colors are deliberately left unchanged; only background/text/panel
change.

## 8h. Navigation sound effects

In the System menu: "Navigation sound effects" turns short click tones on
or off when moving/confirming/going back (default: ON). The tones are
generated on the first start (no downloads needed) and run alongside the
background music.

## 8h-2. Random Pick: the draw with sound (Build 246)

*Random Pick — draw a game* can take its time instead of answering at
once. Under *Options*: **Draw suspense** — off, or 1 to 5 seconds.

While it draws, the titles run past like a wheel and a sound plays with
them; the covers of the candidates are shown. Any key cancels, and
cancelling **before** the draw has finished does not pick anything.

Set to *off*, nothing happens and no sound plays. If you hear nothing,
this probe says in plain words where the chain breaks (folder, file,
player, settings, sound card in use) and plays once at the end:

```
python3 /media/fat/frontend/sound_probe.py
```

---

## 8h-3. Arranging the main page yourself (Build 250)

System menu, under *Options*: **"Main page: sort and hide categories"**.

You get a list of all categories in their current order:

| Key | What it does |
|---|---|
| Up/Down | move the selection |
| Left/Right | **show or hide** a category |
| Enter | **pick up** an entry — Up/Down then moves it, Enter puts it down |
| Back / ESC | save and return |

The picked-up entry reads `= Name =` in its row, so you can watch it
travel. The number on the left says how far you have come without
counting.

**"System" is not in the list, and that is deliberate.** It always stays
visible and always last. Anyone who could hide it or move it up would
lose access to the settings — and deleting the file by hand needs SSH.
A hand-edited `/media/fat/frontend/hauptseite.json` cannot hide it
either.

**A newly added category stays visible.** Add a system or remember a
filter and it appears at the end (before "System"), ready to be moved —
it does not vanish just because the saved order does not know it yet.

Hidden is not deleted: the category stays in the editor's list, only in
grey, and one press of Left/Right brings it back.

---

## 8h-4. Remembered filters with a name of your own (Build 250)

Since Build 143 a filter condition can be remembered as a category of
its own — the name was built from the condition automatically ("SNES /
Platform / 1990-1994"). **That stays exactly as it was**, one keypress.

New is a second line below it: **"…or remember with your own name"**,
and for a category you already have, **"Rename this category"**. You get
the letter picker from the search — the same one that works on a CRT and
on HDMI. The automatic name is pre-filled, so renaming means correcting
rather than typing from scratch.

---

## 8h-5. Core updates: what's new (Build 250)

`update_all` can be started from the system menu (since Build 213).
Afterwards there used to be nothing to see — the script writes hundreds
of lines to the console, and if you were not watching you had no idea
whether anything had happened.

Now the frontend looks at which `.rbf` files are in `_Console`,
`_Computer`, `_Other`, `_Utility` and `_Arcade` **before** the run, and
again **afterwards**. The difference appears at once, in three groups:

- **New** — this core was not there before
- **Updated** — the core was there, with a different build
- **Gone** — `update_all` removed it

The third case is not theoretical: `update_all` clears old cores away,
and a core that disappeared is exactly what you want to know when a game
stops starting. If nothing changed, the frontend says that too. The
report stays reachable as **"Core updates: what's new (N)"**; if there is
no report, the entry does not appear at all.

**No log of `update_all` is parsed.** What is compared is the card with
itself — an observation of our own filesystem, which stays correct
whatever version of `update_all` you have and whatever it does
internally. A network query "are there updates?" is still deliberately
**absent**: that would mean rebuilding the MiSTer downloader's databases,
a second source of truth for the most important files on the card.

---

## 8h-6. NFC tags via Zaparoo (Build 251)

[Zaparoo](https://zaparoo.org) (formerly TapTo) is a **separate
project**, not part of Dragend: it reads NFC tags on the MiSTer and
starts whatever game is written on them. Put the card down, the game
runs.

The system menu entry under *Options* names the state — **not
installed**, **service not registered**, **not running** or **running** —
so you do not have to go in to find out whether it is ready.

Inside:

- **Enter launches the Zaparoo script.** On first start it registers
  itself as a service. It is launched the same way as `update_all` — no
  separate launch path is built.
- **Your recently played games** are listed, and for the selected one
  the frontend shows the single line you write onto a tag with the
  Zaparoo app:

  ```
  **launch:/media/fat/games/SNES/Super Mario World.sfc
  ```

  It is wrapped, not truncated — half a path would be worthless.

**Why "recently played" and not a game browser:** you make a tag for a
game you have just played. A second path through the whole game list
would be redundant, and an extra key in the list would be one more thing
to remember.

**Nothing is written into Zaparoo's own folder.** `/media/fat/zaparoo`
holds another program's configuration and mappings — the same stance as
with the foreign artwork database under `/media/fat/docs` and MiSTer's
favourites file: we read, we do not write. On top of that, Zaparoo has to
be restarted for a change to those files to take effect, so we could
write something that only applies later, and you would be left unsure
whether it arrived. Tags are written with the phone app; all that was
missing there was the one line, and now it is here.

If you still have the old **TapTo** installed, it is recognised too.

---

## 8h-7. Re-reading only what changed (Build 251)

Plug in a USB stick while the frontend runs and it tells you. That
message is **no longer fleeting**: an extra entry appears in the system
menu, right above *"Rescan game list"* —

> **Re-read only what changed (USB: +usb0)**

The difference is large. *"Rescan game list"* reads **all** systems from
the card; with 30,000 games that is minutes. The new entry compares each
system's signature and takes everything unchanged from the cache — for
one plugged-in stick, seconds.

Both ways stay: one fast, one thorough. If something looks wrong and you
are unsure, keep using the full rescan.

The message also says **what** appeared: USB, network drive, card, or
storage in general.

**On physical CDs/DVDs:** the MiSTer has no optical drives. A USB drive
with a CD in it appears like any other USB volume, and a game CD for PSX
or Mega CD is an image (`.cue`/`.chd`) on the card anyway. So there is
nothing of its own to detect — what there is, is an honest statement of
what was added.

---

## 8h-8. Metadata from a `gamelist.xml` (since Build 188)

Not new, but it was only ever in the changelog. If you curate your ROM
folders with **Skraper** or a similar tool, there is a `gamelist.xml` in
EmulationStation format sitting there — with year, genre, player count,
manufacturer, description and often the cover as well. If it is there,
it is read. No tool, no download, no setting.

**The order of precedence, and it is deliberate:**

1. your own data (`/media/fat/frontend/meta/<SYSTEM>.json`)
2. the `gamelist.xml`
3. the foreign database under `/media/fat/docs`

Filling happens **field by field**: a source only adds what the previous
one did not have, and never replaces. Same for covers — your own artwork
always comes first.

To switch it off: `touch /media/fat/frontend/gamelist_aus` — no update
needed.

---

## 8b-2. Portrait mode (TATE) — without a switch

Turn the screen (TATE, 90 degrees) and the **width** suddenly becomes the
tight side. The frontend notices this from the framebuffer's dimensions
and computes differently — there is no switch for it, because there is
no decision for you to make.

What changes:

- **Text width is measured against the width, not the height.** Without
  that rule only 23 characters per line would be left at 1080×1920 — a
  game title cut to a third. With it there are 38, and that is readable.
- **Grid tile size is computed, not hard-coded.** In portrait the tiles
  stand 1×2 instead of side by side.

Verified at 1080×1920, 720×1280, 480×640 and 240×320. That **landscape**
stays unchanged is not a claim: `regression_test.py` compares 18
combinations bit for bit, `diag_lightpath.py` another 34.

---

## 8g-2. Your own colour scheme: save and edit

Under *Display & Sound*, directly below the colour-scheme line, there are
two more entries:

| Entry | Action | What it does |
|---|---|---|
| Save current colours as your own scheme | `theme_eigen_speichern` | Takes the active scheme as a basis and makes one of your own from it |
| Edit your own colour scheme | `theme_eigen_bearbeiten` | Opens the editor |

In the editor you change the colours **while the frontend runs** and see
the effect immediately on a preview row — no editing files, no restart.
You can also choose whether the system colours are **blended towards the
accent** (a calmer overall picture) or whether every system keeps its own
colour. *Save and activate* stores it.

---

## 8v. MiSTer's own fonts

The frontend reads the `.pf` character sets from **`/media/fat/font`** —
the same ones MiSTer's OSD uses — and can draw in one of them.

- Entry *Font* (action `schrift`) under *Display & Sound*.
- Three choices: **own** (the frontend's built-in font), **like the
  MiSTer OSD** (whichever MiSTer is using) or a specific file.
- The picker shows a **sample line** (`0O 1lI 8B 5S Gg Qq 123 ABC abc`) —
  with pixel fonts those exact characters decide whether a font is usable.
- If the fonts sit in **subfolders**, you navigate into them; "all
  folders" shows them together.
- **Read, not modified.** Nothing is written into `/media/fat/font`; the
  choice is remembered in `/media/fat/frontend/schrift`.

---

## 8w. Shadow masks

MiSTer's own `.png` masks can be laid over the frontend's picture as a
grid — the same look the cores reproduce on a tube.

- Entry *Shadow mask* (action `masken`) under *Display & Sound*.
- Read from **`/media/fat/Shadow_Masks`**, plus the **MiSTer presets**
  from `/media/fat/Presets` as an entry of their own ("MiSTer presets
  (recommendations)") — exactly the selection MiSTer itself recommends.
- **Four modes**: `1x`, `1x rotated`, `2x`, `2x rotated`. Rotated is for
  masks meant for portrait use, `2x` for high resolutions.
- *Effect: ON/OFF* disables the chosen mask without losing the choice.
- **Read, not modified.** Nothing is written into `Shadow_Masks` or
  `Presets`, and `MiSTer.ini` is only **read** for this.

---

## 8x. Your own background images

Your own images behind the list — not to be confused with the system
backgrounds from section 7, which have been gone since Build 87.

- Put images into **`/media/fat/frontend/backgrounds`** (PNG or JPEG).
- Entry *Background image* (action `hintergrund`) under *Display &
  Sound*: pick one, cycle through all of them, or *off*.
- The image is **dimmed and cropped** so the text on top stays readable;
  with several present they are cycled.
- **It costs nothing while drawing.** The background lives in the shadow
  buffer and is not recomputed while scrolling — measured, not assumed.

---

## 8y. MiSTer's own favourites

Whatever you marked as a favourite in the **MiSTer OSD** sits inside your
favourites category: **one list, two sources.** Yours first, MiSTer's
after, duplicates only once.

The entries behave like any other game — box art, description, play
time, RetroAchievements, all of it works.

**Nothing is written into MiSTer's favourites file.** Remove a favourite
in the OSD and it is gone here too. Your own favourites (F8 / L2 / R2)
stay in the frontend's own file.

---

## 8z. Cores: choosing a build and updating

Two entries under *Options*:

| Entry | Action | What it does |
|---|---|---|
| Cores: choose the build per system | `cores` | If several builds of a core are on the card, you pick per system which one is launched — with left/right. "automatic" takes the newest. If the chosen file is missing because `update_all` cleared it away, the line says so and the choice falls back to automatic |
| Run update_all (cores and firmware) | `update_all` | Launches the **existing** script — nothing is reimplemented. The label names the last run ("23 days ago") so that "do I need this now?" can be answered without looking. If `update_all` is not installed, the line says that |

**A network query "are there core updates?" is deliberately absent.**
That would mean rebuilding the MiSTer downloader's databases, a second
source of truth for the most important files on the card.

What a run changed is then under *Core updates: what's new* — see
**section 8h-5**.

### The storage watch

Plug in a USB stick while the frontend runs, or add a network drive, and
the frontend says so and names the kind (USB / network drive / card).
**Nothing is re-read on its own** — with large collections that takes
minutes and stays your decision. Afterwards the entry *Re-read only what
changed* sits in the system menu until you use it; what it does exactly
is in **section 8h-7**.

---

## 8q. Autostart on/off

System menu, under *Options*: **Autostart: ON/OFF**. On means the
frontend starts together with the MiSTer; off means it does not, and you
start it from the OSD under *Scripts*.

The switch takes effect from the next reboot, and it writes to
`/media/fat/linux/user-startup.sh`. If that file is not writable, the
frontend says so and leaves autostart unchanged rather than claiming
success.

---

## 8i. Playtime tracker

Fully automatic, without setting anything up: the frontend remembers per
game how long it was actually played (loading times and a failed launch
don't count). Visible in the info area next to boxart/player count/year/
genre, e.g. "Played: 2h 15min". Stored in `playtime.json` in the
`frontend` folder.

## 8j. Top 10 lists

In the System menu: "Top 10: most played" and "Top 10: most launched"
show a full-screen overview of the 10 games with the longest total
playtime or the most launches. Purely informational - any key returns to
the menu.

## 8k. RetroAchievements progress

Shows in the info area how many achievements you've already earned in a
game ("RA: 20/50") - completely invisible while not set up, without any
delay at startup.

**Setup:** Create the file `/media/fat/frontend/retroachievements.cfg`
via SSH/text editor, two lines:
```
YourRAUsername
YourRAWebApiKey
```
You'll find the Web API key in your RA control panel under "Keys". Then
tap "RetroAchievements: YourName (reload)" in the System menu to trigger
the sync.

This only shows something if you've actually already earned achievements
in a game - either via a RA-capable MiSTer special version (odelot's
fork, to be installed separately), or because you've already played the
same game RA-tracked somewhere else. On a completely normal MiSTer
without the add-on version, it shows nothing for most games. The matching
runs via the game title (RA provides no file paths) - deliberately
cautious: if the name or system doesn't match unambiguously, it prefers
to show nothing rather than a possibly wrong match.

**RA achievement showcase (F6 key):** For a game with RA progress, F6
shows the complete achievement list - icon, name, description, points,
unlocked or not - instead of just the number next to the cover. Fetches
the data live on each call; icons are downloaded once and cached
permanently locally (a custom PNG decoder built directly into the
frontend). Completely standalone - if something doesn't fit here, the
normal progress display is unaffected.

## 8l. Choosing a standard or RA core

If you use **sage2050's "MiSTer_RetroAchievements" tool** (separate
`_RA_Cores` folder, where the RA core sits next to the normal core
instead of replacing it): when entering a system for which a RA-core
variant is found, the frontend briefly asks whether the normal or the RA
core should be loaded. Up/Down chooses, OK confirms, ESC cancels and you
stay on the system list (does NOT enter the category then). The choice
applies for the current session, until you enter the category again.

If no matching RA-core file is found for a system (or you don't have the
tool installed), the question doesn't even appear there - no interruption
for all other systems/users.

**Honestly:** I couldn't verify the exact file naming of this third-party
tool against a real installation - the frontend therefore tries several
plausible names per system. If the choice doesn't appear for a system
even though you have a RA core installed for it, let me know, and we'll
add the matching name variant.

**RA achievement hunter:** Its own category in the main menu (directly
before "Scripts") - shows all games in your collection that have RA
achievements but where you haven't unlocked anything yet. Sorted by
system like your own ROM subfolders, per system by the number of
available achievements (the biggest opportunities first). Appears only
when RetroAchievements is set up and something is actually found.

## 8m. Completed status + your own achievements

**Completed status:** F7 marks the current game as completed (press again
to turn it off again) - your own, combinable marker next to the favorite
star in the list ("V " or "* V " for both), additionally visible in the
info area.

**Your own, local achievements:** Completely independent of
RetroAchievements - based only on our own data (playtime, launches,
systems tried, completed games). In the System menu, "My achievements"
shows an overview of all 15 milestones (playtime, launch, explorer and
completed tiers), earned ones highlighted, open ones with a progress
figure. Runs completely automatically, no setup needed.

Plus **five hidden achievements** - appear as "???" until earned, after
which what they were about is revealed. No spoiler here, just try it out.

When an achievement is newly earned (whether a normal milestone or a
hidden one), there's a brief on-screen notification with its own
achievement sound - when returning from a game, when favoriting, or when
marking as completed.

**Trophy Room:** In the System menu, "My Trophy Room" - a personal
profile screen instead of dry numbers: a large cover of your most-played
game, your favorite system (based on the total playtime spent there, not
just the single top game), an achievement counter and a short summary.

**Year in Review:** In the System menu, "Year in Review" - like the
Trophy Room, but limited to the current calendar year instead of "since
records began": playtime this year, most-played game this year, favorite
system this year, and how many games you discovered for the first time
this year. Shows a friendly message if nothing has been recorded yet for
the current year.

**Game Diary:** In the System menu, "Game Diary" - a rolling log of the
last 30 days, "Today"/"Yesterday" and then the date, below it each
individual session with system and duration. Cleans itself up
automatically, so it never grows without bound. (Currently deliberately a
small version - a permanent variant with archiving is conceivable for
later.)

## 8n. Easter-egg system (secrets) + frontend levels

The frontend itself collects "experience" - derived from playtime,
launches and achievements, no additional setup needed. In the System menu
under "Secrets" you can see your progress: level 1 to 5; higher tiers are
reached via several paths (playtime OR launches OR hidden achievements -
no narrow forced path).

In addition there are a few **secret cheat codes** - deliberately
enterable **only via keyboard** (not via gamepad, see below for why),
entered in the **main menu** (not in a game list). Which codes exactly
they are and what they unlock is deliberately not revealed here - that's
for you to find out yourself. A code can be entered again any number of
times, just like a real cheat code - not just once.

**Why keyboard only, not gamepad:** In the main menu, "OK" and "Back" on
a gamepad always have a real effect (entering a category or the quit
dialog) - a code could therefore never be entered fully. Certain other
keys, by contrast, only trigger a harmless jump in the list, completely
safe in the middle of entering a code. Without a connected keyboard the
codes unfortunately remain out of reach - but the level system itself
needs no keyboard, that runs automatically.

The secrets overview shows "???" for what hasn't been found yet; after
discovery what it was about is revealed - no spoiler here, just try it
out.

## 8o. CRT test pattern

System menu -> "CRT test pattern" - a classic service-menu test pattern
like on real tube monitors: geometry frame at the edge of the picture, a
grid for checking linearity, a centering cross and color bars for color
calibration. Useful when setting up a 15 kHz CRT setup (see section 8).
Any key returns to the menu.

## 8p. Contributors

System menu -> "Contributors" - who built the frontend and who helped. A
small thank-you, not a secret like the developer room from section 8n.

## 8r. Views: list, grid, gallery

Both the game list **and** the main page come in three views:

| | shows | good when |
|---|---|---|
| **List** | a text list plus one large image beside it | you want to read long titles in full - and the only view that still shows something with no covers at all |
| **Grid** | images only, densely packed; the name of the selected entry is shown below | you want to see a lot at a glance. On HDMI that is 28 games, or **every** category without a single page turn |
| **Gallery** | one large image, data beside it, the neighbours as a strip below | you want detail without losing sight of what is next to it |

**There are two ways to switch, and they deliberately do different
things:**

- The **menu** under *System -> Display & sound* -> "Game list view" and
  "Main page view" sets the **default** - it applies everywhere and
  after the next start.
- **F10** (or **Select+Y** on the pad) switches **only what you are
  looking at** and saves nothing. In the game list it applies to the
  open category only, so you can browse in grid view and still keep the
  list for SNES.

**The direction keys follow the layout, not habit:**

| View | up / down | left / right |
|---|---|---|
| List | one entry | one page |
| Grid | a whole **row** | one neighbour |
| Gallery | one **page** | one neighbour |

In the gallery the neighbours sit side by side, so left/right is what
moves you one along. Up/down are not dead there: they page the
neighbour strip, which is exactly what left/right do in the list.

**A folder-only level always stays a list.** Folders practically never
have a cover of their own; a grid of nothing but placeholders would not
be a view, it would be a bug.

> **Tip:** After switching, run *System -> Options -> "Prepare
> thumbnails"* - each view needs the images in a different size. The
> menu item prepares all three views in one go, so you only need to run
> it once (but once per video mode: CRT and HDMI have their own sizes).
>
> **How long it takes, and what drives it.** Three box sizes are
> computed per cover, and the cost depends on the size of the *source
> file*, not of the tile. Rough figures on the MiSTer, using both
> cores: about half a second to a second per cover. With 5000 covers
> that is roughly an hour; with 30 000, correspondingly more. The run
> can be aborted with any key at any time and loses nothing - next time
> it carries on where it stopped.
>
> **Faster since Build 129:** TurboJPEG can decode a JPEG straight to a
> smaller size (1/2, 1/4, 1/8), libpng cannot. The same work from a JPEG
> therefore costs 416 ms instead of 689 ms for a 900x1200 cover. The
> downloader now writes a **JPEG working copy** next to every PNG it
> fetches; the original is left untouched. For covers already on the
> card there is `PC-Tools/arbeitskopien.py` - minutes on a PC, hours on
> the MiSTer. It costs about 0.2-0.4 MB per cover on top of the
> original; delete the `.jpg` files and the frontend goes back to the
> PNGs.
>
> **Card space:** budget about 0.3-0.8 MB per cover. If that gets too
> much, *System -> Maintenance -> "Clear cache"* removes all of it
> again; the only thing lost is computing time.

---

## 8s. ROMs inside ZIP archives

If your ROMs live inside ZIP archives, they are listed normally. An
archive is **a folder like any other** to the frontend: folders inside
the archive become folders, the games sit inside them and start as
usual.

**Nothing is ever extracted**, not even partially - only the table of
contents at the end of the file is read. This works because MiSTer
itself treats an archive in the launch path like a folder
(`path="some/other.zip/path/dummy.gg"` is written exactly like that in
the official MiSTer documentation).

Three deliberate decisions:

- A **broken or half-copied archive** does not break the scan - it is
  skipped silently, just like an unreadable file.
- An **archive without matching ROMs** does not show up at all. Many
  collections keep manuals next to the ROMs as an archive; an empty
  folder for those would only be in the way.
- **Romsets stay romsets.** Neo Geo only counts `.neo` as a ROM
  extension, arcade only `.mra` - the parts inside a romset archive
  match neither, so the archive stays exactly what it was.

---

## 8t. Game descriptions (since Build 139)

In the **gallery**, a short description of the game now sits to the
right of the cover — in German when the interface is set to German,
otherwise in English.

It comes from the same artwork database as the covers: next to
`gameinfo.tsv` there is a `synopsis_<xx>.tsv` per language. Only
**German and English** are read; if a German text is missing for a
game, the English one steps in. Measured against the SNES table:
**1,785 of 1,802** games have a description.

Nothing has to be prepared. It is text, not an image — no decoding, no
thumbnail, no cache. A system's table is read once the first time you
look at it and stays in memory afterwards.

Three deliberate decisions:

- **Gallery only.** The height of the list's boxart column determines
  the size of the pre-computed thumbnails — one extra line of text
  would invalidate the whole cache there.
- **One font step smaller.** Otherwise it would be two or three lines
  at 1080p, i.e. half a sentence. If the text still does not fit
  completely, it visibly ends with `~`.
- **Not read from the card while scrolling.** Same rule as for covers:
  the text appears once you stop.

It can be switched off with the same toggle as the foreign artwork:
*System → Display & sound → "Foreign artwork/data"*.

## 8u. Covers while scrolling (since Build 138)

*System → Display & sound → "Cover while scrolling"*, default **off**.

In list view the cover column is skipped while you scroll and only
drawn once you stop — that dates back to a time when a cover could cost
up to 1.2 seconds in the drawing path. The gallery does it more
finely: it always draws and only skips the single image that is not
ready yet.

Turned on, the list behaves like the gallery: a cover that is already
in memory appears immediately. The switch takes effect without a
restart — just flip it and scroll through a large list.

## 9. Switching language

System -> "Language: English -> switch to German" (or the other way
around to German) switches all visible texts in the frontend - headers/
footers, System menu, quit dialog, boxart info, now-playing. The chosen
state persists across restarts.

## 10. Custom key mapping

System -> "Configure buttons" starts an assistant: it asks in turn for
Up, Down, Left, Right, OK/Start, Back, Open MiSTer menu - just press the
desired button (keyboard or gamepad, any device). If your pad reports the
D-pad as an analog axis (most do), that is detected automatically and
skipped, since that direction then already works natively. ESC cancels at
any time without changing the existing mapping. System -> "Reset to
default buttons" resets everything to the factory setting.

## 11. Boot animation (startup video)

A small image sequence that is played once per MiSTer boot before the
normal menu appears - not a real video format (the MiSTer has no video
player), but a flip-book of individual images in the same `.art` format
as boxart and background images.

At startup, the frontend detects by itself whether CRT or HDMI menu mode
is currently active, and plays the matching animation - so you can store
different videos/images for the two modes.

1. On the PC (`pip install Pillow`, additionally ffmpeg in PATH for video
   sources), once per mode:
   ```
   # CRT variant:
   python video_to_bootanim.py --video intro.mp4 --out bootanim_crt ^
       --fps 10 --duration 3 --size 320x240

   # HDMI variant (can be a different video/section):
   python video_to_bootanim.py --video intro.mp4 --out bootanim_hdmi ^
       --fps 10 --duration 3 --size 960x540
   ```
   **For HDMI, better not use the full 1920x1080:** the frontend shows
   each image at its actually stored size (centered, with a border)
   instead of forcibly upscaling it to full screen - noticeably faster on
   the rather weak MiSTer processor. `960x540` instead of full
   `1920x1080` plays the animation about 7x more smoothly and still looks
   sharp on a 1080p TV. If a source is larger than the screen after all,
   it is scaled down automatically (but more slowly).
2. Copy the two folders via WinSCP to
   `/media/fat/frontend/bootanim_crt/` or
   `/media/fat/frontend/bootanim_hdmi/` (folder names exactly like this,
   with the underscore suffix).
3. Done - on the next boot, the animation matching the current mode
   appears automatically.

**Set up only one mode?** That works too - if the mode-specific folder is
missing, `bootanim/` (without a suffix, the old structure) is used
instead, if present.

Any key press during playback skips the rest immediately. If no matching
folder exists or it is empty, simply nothing happens.

**Deliberately keep it short:** Each image is decoded on the MiSTer in
pure Python - fast enough without issue for a few seconds of animation,
but not real video playback. Recommendation: 2-4 seconds, 8-12 frames per
second. Longer is possible, but then also lengthens the boot process.

## 12. Stream overlay for OBS (optional)

A web overlay shows in the stream in real time what is currently selected
in the frontend (cover, title, system, now-playing, genre/year, playtime,
RetroAchievements progress, favorite star) - independent of the MiSTer's
video output, so without the CRT/HDMI scaler limit from section 8. The
"menu view" for the stream does not come from the video output, but is
rendered directly in the browser and put on screen by OBS. Each
individual display can be turned on/off separately via the backend
interface.

**RA achievements in real time:** If a RetroAchievements achievement is
unlocked while playing, the overlay shows it directly - icon, title,
description, points, faded in after 7 seconds and gone again
automatically. No need to wait until returning to the menu. Its own
admin switch, if not desired.

**Reworked in Build 252**, so that it lands as a moment in the stream
and not just as a notice:

- **Several achievements in a row** no longer get lost. The second one
  used to overwrite the first; now they appear one after another, with a
  note of how many are still waiting ("+3 more").
- **The points count up**, from 0 to the value.
- The card **springs back as it enters**, the icon rotates in out of
  depth, and a sheen sweeps across it once.

Anyone with *"reduce motion"* set in their system automatically gets the
plain version from before — the overlay asks the setting.

**Its corner is yours (Build 255):** in the backend under *Popup:
corner*, directly below its switch. Default stays top right, so anyone
who never touches it notices nothing. Placed on the **left** it enters
from the left and carries the accent bar on its left edge. It has a
corner of its own, independent of the info card and of the achievement
wall; put it deliberately on top of the card and that is your call. One
exception: in the same corner as the **wall** it steps aside, because the
wall is tall and the popup in the middle of it would be unreadable.

**The achievement wall (Build 253):** a wall of *all* achievements of the
running game can be shown as well — the unlocked ones in colour, the rest
greyed out, with "74 / 98", the points and a progress bar above.

In the backend under *Achievement wall*: **off by default**, because it
takes up space. Plus a corner of its own (independent of the info card)
and the number of tiles per row, 4 to 24.

Unlock an achievement and **exactly that one tile flashes** and flips
from grey to colour. That is the point of it — otherwise the wall would
just be a table.

Two things worth knowing:

- **The very first time**, the frontend fetches the achievement icons
  from RetroAchievements in the background — for a game with 98
  achievements that takes about half a minute, and the wall fills up as
  it goes. After that the icons stay on the card and it is there at once.
- The wall only appears **while a game with RetroAchievements is
  running**. It disappears when you return to the menu.

**It is there right at game start (Build 254):** previously the wall did
not appear at all for a game where you had **no achievement yet** — and
then did on the next start. The reason: the RA game number came from the
list of games you had already interacted with, and a brand-new game is
not in it. The frontend now finds the number itself in the RA catalogue
of the system and remembers it permanently in
`/media/fat/frontend/ra_spielnummern.json`. The first time per system
that costs one catalogue fetch (a few seconds in the background); after
that the wall is there immediately — at 0 / 98, fully grey, and you
unlock it yourself.

**Visible rows, the rest scrolls (Build 254):** with 98 achievements and
12 tiles per row that is 9 rows — half the screen height on a 1080p
canvas. So next to the tiles-per-row there is a second slider,
**Visible rows**:

- at **0 (default)** the wall is shown in full, as before.
- at **2 to 20** only that window is visible and the wall **scrolls
  slowly from top to bottom** — pausing briefly at each end so you see
  the edges too, then back.
- Unlock an achievement while it scrolls and **the wall drives to that
  tile and holds there for three seconds**. Otherwise it might flash in
  a region outside the window — and then you would not see the flash,
  which is the whole point of the wall.

The setting **survives a change of game** (from Build 255). In Build 254
it was lost as soon as you switched games in the running frontend, and
the wall stood at full height again. It was always saved, it just was
not applied; if you ran into that, the new `stream_overlay.html` is
enough.

**The game title can be switched off (Build 254):** in the backend,
*Show game title*. Off means the whole title row disappears, star and
play time included — useful when the title is already elsewhere in the
stream or the game itself shows it. Cover, category and system are
unaffected and keep their own switches.

**Setup:**
1. Turn on - two equivalent ways:
   - **Directly in the frontend menu** (new, no SSH needed): System ->
     Display & Sound -> "Stream overlay: OFF -> turn on". Takes effect
     after a frontend restart, same as the SSH way (the web server is
     only set up at startup) - the menu label says so explicitly.
   - Via SSH:
     ```bash
     /media/fat/Scripts/Frontend_Stream_Toggle.sh on
     ```
   Both ways create the same enable file - without it the web server
   doesn't even start, so existing users notice nothing of it.
2. Restart the frontend (see section 13 for the clean restart procedure).
3. In OBS, add a **browser source** with the address
   `http://<MiSTer-IP>:8080/` (set width/height to your stream canvas,
   e.g. 1920x1080 - the rest stays transparent).

   **Convenience alternative:** `PC-Tools/obs_setup.py` (on Windows via
   double-click on `OBS_Setup_starten.bat`) asks for the MiSTer IP,
   checks the connection and creates a local overlay file with the
   address hard-coded - then in OBS simply select this file as a "Local
   file" instead of the URL. Handy if you want to customize the look with
   your own CSS. Completely optional, the normal URL works just as well.
4. Customize the appearance (position, colors, what is shown) at
   `http://<MiSTer-IP>:8080/admin` in the browser - takes effect
   immediately, without a restart.
5. Turn off again: either the same menu item (now "ON -> turn off") or
   `Frontend_Stream_Toggle.sh off` - then restart the frontend.

Runs entirely on standard Python (`http.server` + server-sent events), no
external packages, as its own background thread next to the normal
frontend loop - binds to port 8080 on the local network. Do **not**
forward it to the internet, there is no authentication. Technical
details: `notizen/STREAM_fuer_Dragrem.md`.

### 12.1 Screen mirror (optional, for CRT users)

Since CRT and HDMI can't run simultaneously in their respective native
resolution for technical reasons (a genuine hardware limitation of the
single scaler, not an oversight - see `notizen/STREAM_fuer_Dragrem.md` for
details), this feature additionally exposes the current frontend
screen as an image via the browser: `http://<MiSTer-IP>:8080/mirror`.
Handy if you run on CRT and still want to see (or show viewers) how
you're browsing the frontend.

**Important limitation:** this only mirrors the **frontend screen
itself** (categories, game list, cover selection) - **not** the
actual running game. As soon as a core starts, the mirror freezes on
the last frontend state until you're back in the menu - the actual
game video is generated directly by the FPGA core and never passes
through the frontend, so it's not accessible in software at all. For
the running game you'll still need a capture card on the HDMI output
(see 12.2 for automatic switching between the two).

For the same reason, this deliberately only works at CRT-sized
resolutions (up to 640px wide) - at HDMI resolution, encoding would
noticeably burden the already weak MiSTer CPU (measured: up to 830ms
per frame, 57% slowdown of a concurrently running thread), while
being unused there anyway since you already see the screen directly.

**Setup:** its own menu entry under System -> Display & Sound
("Screen mirror"), requires the stream overlay (12) as a prerequisite
- the menu label points this out. Add it in OBS as an additional
browser source with the address `http://<MiSTer-IP>:8080/mirror`,
same as the regular overlay.

### 12.2 Automatic OBS scene switching (optional)

For anyone with a capture card on the HDMI output: OBS can
automatically switch between two scenes - to the capture card scene
as soon as a game starts, and back to the frontend scene (e.g. with
the screen mirror from 12.1) as soon as you're back in the menu. The
frontend is the only thing that reliably knows exactly when that
happens.

**Prerequisites:**
- OBS' WebSocket server enabled (Tools -> WebSocket Server Settings) -
  port and password are also visible/configurable there.
- Two OBS scenes already created (names are up to you, e.g.
  "Frontend" and "Live Game").

**Setup:** at `http://<MiSTer-IP>:8080/admin` in the "Automatic scene
switching" section - copy the OBS machine's IP address, port and
password from OBS' WebSocket settings, enter both scene names exactly
as in OBS, turn on "Enabled". Takes effect immediately, no restart
needed.

Runs completely fault-tolerant: if OBS is unreachable, misconfigured,
or the feature is simply disabled, the scene-switch attempt is just
skipped - the actual game launch or return to the menu is never
affected or delayed by it.

## 13. Troubleshooting

- **The key-mapping assistant freezes while configuring "Open OSD" / the
  screen goes black with a login prompt**: F9 is reserved on MiSTer for
  switching between console and graphics mode - if your pad sends a real
  F9 (e.g. via a Home/Guide key), the kernel probably intercepts it
  before our process sees it. The assistant therefore has a time limit
  (20s, skips the query instead of waiting forever) and generally rejects
  a captured F9 as a mapping. If it still occurs: share
  `tail -60 /tmp/frontend.log` right afterwards.
  **For the same reason the frontend does not use F9 itself** - the view
  switch is on **F10** (section 8r).
- **After a file update** (new version installed): simply run
  `/media/fat/Scripts/Frontend_Update.sh` (via SSH or from the MiSTer OSD
  under Scripts) - it ends the old instance cleanly and restarts
  automatically.
- Frontend doesn't start / doesn't respond: check whether an instance is
  already running: `cat /tmp/frontend.lock`. End it with
  `kill $(cat /tmp/frontend.lock)`, then `rm -f /tmp/frontend.lock`. (On
  the MiSTer there is no `pkill`/`pgrep` - always use the
  `kill $(cat ...)` route.)
- Screen stays stuck in the MiSTer OSD at boot, but music is already
  playing: should be fixed (the screen switch used to happen after a
  possibly slow scan instead of before it). If it still occurs,
  `/tmp/frontend.log` helps with the search.
- Emergency stop for autostart problems: `touch /media/fat/frontend/disable`
  and restart (to reactivate: delete the file again).
- Diagnostics: `/tmp/frontend.log` logs devices, actions and errors
  (limits itself automatically to about ~512 KB so the mostly RAM-based
  `/tmp` storage doesn't fill up):
  ```bash
  tail -50 /tmp/frontend.log
  ```
- Never start long programs via the WinSCP command line (the console
  reports "no more data" after 15s and the cancel button kills the
  process) - always use a real SSH session (`ssh root@<MiSTer-IP>`).

## 13b. MiSTer Linux from 2026-09-07 (kernel 6.18)

The MiSTer Linux update of **7 September 2026** raises the kernel from
5.15.1 to 6.18.x and changed how the framebuffer is accessed. This is
not specific to this frontend: **Degauss**, the **Zaparoo Frontend** and
**Console Mode** all had to follow. Dragend runs on both kernels - there
is nothing to set. This section is here for the case where something
does go wrong.

The new kernel shows itself with this line in `dmesg`:

```
fb0: sys_fillrect: framebuffer is not in virtual address space.
```

**On exit: the first F12 does not arrive.** When leaving, the frontend
sends an F12 so MiSTer brings its OSD back. On 6.18 that first F12 does
not get through - without a countermeasure you are left with a black
screen and a blinking cursor, followed by the login greeting. The
frontend therefore checks **MiSTer's CPU load** to see whether the OSD
really is there, and retries up to three times:

```
Exit: injiziere F12 (1/3)
Exit: MiSTer bei   1% - das OSD ist NICHT gekommen, fasse nach
Exit: injiziere F12 (2/3)
Exit: MiSTer bei 100% - das OSD ist da
```

**The same on startup, with F9.** After booting, MiSTer sets up the
framebuffer **several times** (in one device's `dmesg` at seconds 3, 41,
48 and 51). Knocking once, early, means knocking at a door that does not
exist yet - the symptom was *"I am stuck in the OSD and can hear the
frontend's music"*. On **kernel 6 and newer** the frontend therefore
switches the console mechanics on automatically: the F9 is repeated, a
guard clears foreign output from the picture, and console blanking stays
off. On 5.15.1 **nothing changes**.

Both can be forced without waiting for a build:

```bash
touch /media/fat/frontend/konsole_mechanik_an     # always on
touch /media/fat/frontend/konsole_mechanik_aus    # always off
```

Which way was taken is in the log:

```bash
grep Konsole /tmp/frontend.log
# Konsole: Mechanik AN (Kernel 6.18.38-MiSTer)
```

**If the screen stays black anyway**, run the framebuffer probe - it
takes two minutes, changes nothing and says in plain words what the
cause is:

```bash
/media/fat/Scripts/Frontend_FB_Probe.sh
```

## 14. Known limitations

- ROM search goes arbitrarily deep, no level limit - but for speed
  reasons, the detection of whether a rescan is needed still only checks
  the topmost ROM folder level per system. So if you only change files
  deep in a subfolder, the frontend may not notice by itself - then run
  System -> "Rescan game list" manually once. Changes directly in the
  topmost system folder, by contrast, are always detected automatically.
- Arcade shows info from the MRA files; boxart also works (see section 6,
  mister_boxart.py loads it automatically).
- Menu visible on only one video output at a time (a technical limit of
  the MiSTer scaler, not a frontend restriction).
- Start+Select generally doesn't work during a running game -
  MiSTer claims the normal input layer exclusively as soon as a core runs
  (see section 4). The Esc route via the raw HID layer of the keyboard
  does work, however; a pad-based exit could not be reliably built in so
  far (on the tested controller it doesn't come through via any known
  channel during a game).
- The custom key mapping only captures discrete keys (keyboard keys and
  gamepad buttons); a D-pad that arrives as an analog axis already works
  natively and is skipped automatically by the assistant instead of being
  remapped.
- The three secret cheat codes (section 8n) deliberately only work with a
  connected keyboard, not via gamepad - in the main menu, "OK"/"Back" on
  a pad always have a real effect (entering a category or the quit
  dialog), so a code could never be entered fully.

---

## 15. Start options

The frontend is normally started without options (autostart, or
`Scripts -> Frontend`). For diagnosis and demonstration there are four:

| Option | What it does |
|---|---|
| `--show` | Says **what is installed, how it is configured and how fast it runs** — on screen and additionally as a file in `/tmp/dragend_show.txt`. The fastest way to report a state without hunting over SSH |
| `--bench` | A **fixed, repeatable measurement** across all drawing paths; report on screen and in `/tmp/dragend_bench.txt`. It deliberately touches **nothing** on the SD card |
| `--demo` | Three minutes of **guided tour**: views, filters, trophy room and the settings groups, played through by itself. Any key aborts |
| `--help` | This list. The check runs **before** everything else: a typo gets you three lines and nothing more — no half start, no lock left behind |

There is also a switch without an option: if the file
`/media/fat/frontend/profile` exists, the frontend writes `PERF` lines
into `/tmp/frontend.log`.

```bash
touch /media/fat/frontend/profile     # on
# ... use it normally, reproduce the problem ...
grep PERF /tmp/frontend.log           # look
rm /media/fat/frontend/profile        # off again
```

The switch lives in the short-lived cache: the very switch you use to
*measure* speed used to cost an SD-card access on every frame — even
when it was off.

---

## 16. The system menu from A to Z

Everything the frontend can do, in one place — in the order of the groups
as they appear in the menu. The *Action* column names the internal
identifier; it is useful when reporting something ("with `masken` it
does …") and it does not change with the language.

### RetroAchievements

| Entry | Action |
|---|---|
| RetroAchievements: configured as … (reload) / *not configured* | `ra_status`, `ra_setup` |
| RetroAchievements: ON/OFF | `ra_toggle` |
| Popups & display (MiSTer RA settings) | `ra_settings` |

The last line configures the popups **MiSTer itself** shows, so it hangs
on MiSTer's own file — not on our Web-API credentials. Anyone who has RA
set up in MiSTer but no key stored with us can still use it (and
conversely nobody ends up in a menu that cannot do anything).

### Statistics & achievements

| Entry | Action |
|---|---|
| Top 10: most played | `top10_time` |
| Top 10: most launched | `top10_launches` |
| My achievements | `milestones` |
| My trophy room | `trophy_room` |
| Year in review | `year_review` |
| Game diary | `diary` |

### Display & Sound

| Entry | Action |
|---|---|
| Menu video: CRT / HDMI (restart) | `crtmenu` |
| Colour scheme | `theme` |
| Save current colours as your own scheme | `theme_eigen_speichern` |
| Edit your own colour scheme | `theme_eigen_bearbeiten` |
| Navigation sound effects: ON/OFF | `sfx` |
| Boot logo: Dragend / neutral | `dragend_logo` |
| Fast scrolling: ON/OFF | `fast_scroll` |
| Covers while scrolling: ON/OFF | `cover_sofort` |
| Cover downscaling: sharp / smooth | `scharf_verkleinern` |
| Font | `schrift` |
| Fine details: ON/OFF (scrollbar, accent bars, divider) | `feinheiten` |
| Background image | `hintergrund` |
| Shadow mask | `masken` |
| Game list view | `ansicht` |
| Main page view | `ansicht_haupt` |
| Side / top-bottom margin | `overscan_x`, `overscan_y` |
| Foreign artwork/data: ON/OFF | `fremdquellen` |
| Menu resolution: full / half / quarter (HDMI only) | `fb_size` |
| Selection shimmer: ON/OFF | `pulse_effect` |
| Equalizer bars: ON/OFF | `eq_effect` |
| Music title marquee: ON/OFF | `track_marquee` |
| Stream overlay: ON/OFF (restart) | `stream_overlay` |
| Screen mirror: ON/OFF (restart) | `screen_mirror` |
| Music: on/off, source, volume | `music`, `music_source`, `volume` |

### Options

| Entry | Action |
|---|---|
| CRT test pattern | `crt_test` |
| Prepare thumbnails (once) | `thumb_prewarm` |
| Write a thumbnail job for the PC | `thumb_auftrag` |
| Curated list (database hits only): ON/OFF | `curated` |
| Hide beta/proto/demo and Japan-only: ON/OFF | `rom_filter` |
| Folders with a single game: as a game / as a folder | `einzelordner` |
| Main page: sort and hide categories | `hauptseite` |
| Zaparoo (NFC tags) | `zaparoo` |
| Core updates: what's new (N) — only when a report exists | `core_neu` |
| Cores: choose the build per system | `cores` |
| Run update_all (cores and firmware) | `update_all` |
| Re-read only what changed — only after a storage change | `nachscan` |
| Attract mode (screensaver): ON/OFF, delay | `attract`, `attract_delay` |
| Draw suspense (Random Pick with sound) | `ziehung_spannung` |
| Time zone | `timezone` |
| Wait for NAS/network at startup: ON/OFF | `network_wait` |
| Autostart: ON/OFF | `autostart` |

### Input & language

| Entry | Action |
|---|---|
| Language: German / English | `language` |
| Configure key mapping | `remap` |
| Reset to default mapping | `remap_reset` |
| Swap confirm/cancel: ON/OFF | `swap_ok_back` |

### Info

| Entry | Action |
|---|---|
| Help / overview | `help` |
| Run setup again | `setup_wizard` |
| Secrets | `secrets` |
| Contributors | `credits` |
| Check for updates: ON/OFF | `update_check` |

### Maintenance

| Entry | Action |
|---|---|
| Open the MiSTer OSD (settings/buttons) | `osd` |
| Rescan game list | `rescan` |
| Clear the thumbnail cache (CRT / HDMI) | `thumb_clear` |
| JPEG working copies: ON/OFF | `arbeitskopien` |
| Download box art (needs network) | `boxart_download` |
| Download game data (needs network) | `gameinfo_download` |
| Redraw the display | `redraw` |
| Reboot the MiSTer | `reboot` |
| Quit the frontend | `quit` |

Some entries appear **only under conditions**, and that is deliberate:
`fb_size` only on HDMI (in CRT mode the framebuffer is 320×240 anyway),
`core_neu` only when a report exists, `nachscan` only after a reported
storage change, and for Zaparoo the label names the state (not installed
/ service not registered / not running / running) instead of an entry
that leads nowhere.

---

## Technical summary

Python 3 (standard library only) draws directly into the framebuffer
`/dev/fb0` (mmap), reads input raw from `/dev/input/event*` (with an
exclusive grab and event injection for F9/F12), launches cores and games
via `/dev/MiSTer_cmd` or generated MGL files (parameters from the mrext
system database), and detects the return to the menu via `/tmp/CORENAME`.
Images are in a custom `.art` format (zlib-compressed BGRA raw pixels)
that can be blitted directly without an image library; for this, the
boxart downloader decodes PNGs with a custom decoder written in pure
Python. Background music runs via the external `mpg123` command-line
program in the background (subprocess), language switching via a central
translation dictionary, and custom key mapping via an editable
codes-to-actions mapping that is loaded at startup and merged with the
default mapping.

---

Created by **Dragrem2K**, with contributions from **TheRealSuTefan**,
**Dfense** and **Dennsen**. Licensed under the MIT license (see
`LICENSE`) - free to use, modify and redistribute. What has changed
between versions: see `CHANGELOG.md`.
