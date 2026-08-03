# MiSTer Custom Frontend v3.2

**By Dragrem2K**, with contributions from **TheRealSuTefan**, **Dfense**
and **Dennsen**.

My self-built frontend for the MiSTer FPGA: a game browser with boxart
and game info, gamepad and keyboard control, background music,
switchable German/English, custom key mapping, CRT and HDMI support,
autostart - all in pure standard Python, without a single external
dependency required on the MiSTer itself.

**About the screenshots below:** rendered directly from the actual
program code, not a photo montage - boxart and music titles are
placeholders, the system logos on the left are real. A compact overview
is additionally available in `VORSCHAU.md`.

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
- **No system modification, reversible at any time** - this is a single
  Python script that runs on a completely unmodified MiSTer. No swapping
  of the kernel/Linux image, no additional hardware needed. Try it out
  without risk: one command uninstalls it cleanly (see `uninstall.sh`),
  and your MiSTer is exactly as it was before.
- **No external dependency** - pure Python from the standard library,
  runs without a single additional package.
- **CRT and HDMI treated equally** - both with specially tuned looks and
  speed, not just "HDMI with CRT compatibility as a side effect".
- **Small and comprehensible** - a single Python file for the actual
  frontend, no abstraction layers, easy to read for anyone who wants to
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
7. System background images (optional)
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
   - 8i. Playtime tracker
   - 8j. Top 10 lists
   - 8k. RetroAchievements progress
   - 8l. Choosing a standard or RA core
   - 8m. Completed status + your own achievements
   - 8n. Easter-egg system (secrets) + frontend levels
   - 8o. CRT test pattern
   - 8p. Contributors
9. Switching language
10. Custom key mapping
11. Boot animation (startup video)
12. Stream overlay for OBS (optional)
13. Troubleshooting
14. Known limitations

---

## 1. Package contents

| File                            | Destination on the MiSTer        | Purpose |
|----------------------------------|----------------------------------|-------|
| frontend/frontend.py            | /media/fat/frontend/             | The frontend itself (v3.2) |
| frontend/frontend_boot.sh       | /media/fat/frontend/             | Autostart wrapper (on every boot) |
| frontend/mister_boxart.py       | /media/fat/frontend/             | Boxart downloader (runs on the MiSTer) |
| frontend/mister_gameinfo.py     | /media/fat/frontend/             | Game-info downloader (runs on the MiSTer) |
| frontend/stream_server.py       | /media/fat/frontend/             | Web server for the stream overlay (optional) |
| frontend/stream_overlay.html    | /media/fat/frontend/             | OBS browser source (optional) |
| frontend/stream_admin.html      | /media/fat/frontend/             | Stream overlay configuration (optional) |
| install.sh                      | stays in the package (installer) | Installation with internet access (downloads from GitHub) |
| install_offline.sh              | stays in the package (installer) | Installation without internet access (from this package) |
| uninstall.sh                     | stays in the package (uninstall) | Remove everything cleanly, optionally keep your own data |
| Scripts/install_frontend.sh     | /media/fat/Scripts/              | Install/update directly from the MiSTer menu (Option A) |
| Scripts/start_frontend.sh       | /media/fat/Scripts/              | Start the frontend manually from the MiSTer OSD |
| Scripts/update_frontend.sh      | /media/fat/Scripts/              | Restart cleanly after a file update (1 command instead of several) |
| Scripts/boxart_download.sh      | /media/fat/Scripts/              | Start the boxart download from the OSD/frontend |
| Scripts/gameinfo_download.sh    | /media/fat/Scripts/              | Start the game-info download from the OSD/frontend |
| Scripts/stream_toggle.sh        | /media/fat/Scripts/              | Toggle the stream overlay on/off (optional) |
| PC-Tools/art_convert.py         | stays on the PC (Python+Pillow)  | Images -> .art format, including background images |
| PC-Tools/boxart_fetch.py        | stays on the PC (optional)       | Alternative: download boxart on the PC instead of the MiSTer |
| PC-Tools/video_to_bootanim.py   | stays on the PC (Python+Pillow)  | Video/image sequence -> boot animation |
| PC-Tools/obs_setup.py           | stays on the PC (optional)       | Create a local OBS overlay file with a hard-coded MiSTer IP |
| PC-Tools/OBS_Setup_starten.bat  | stays on the PC (optional)       | Windows double-click launcher for obs_setup.py |
| music/                          | (for reference only, contents irrelevant) | Target folder for your own MP3s |

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
   [`Scripts/install_frontend.sh`](https://raw.githubusercontent.com/dragrem2k-coder/mister-frontend/main/Scripts/install_frontend.sh)
   (right-click -> Save as, or browser download).
2. Copy the file to `/media/fat/Scripts/` via WinSCP.
3. In the MiSTer OSD: tap **Scripts -> "install frontend"**.

The rest runs by itself - download, set up, autostart. At the end, press
a key briefly to get back to the menu. Then reboot once, done.

Can be run again at any time (e.g. for an update) - your own data (music,
boxart, settings) stays untouched, only the program files are replaced.
Requires internet access on the MiSTer (usually available automatically
on a home network).

### Option B: Via SSH, one command

If you already have an SSH session open anyway:
```bash
curl -Ls https://raw.githubusercontent.com/dragrem2k-coder/mister-frontend/main/install.sh | bash
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
./install_offline.sh
```
Asks interactively about autostart and stream overlay. Without prompts:
```bash
./install_offline.sh --yes                # autostart on, overlay off
./install_offline.sh --yes --stream        # additionally overlay on
./install_offline.sh --yes --no-autostart  # without autostart
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

Or from the actual MiSTer OSD: main menu -> Scripts -> `start_frontend`
(MiSTer automatically lists every `.sh` script in `/media/fat/Scripts/`
in the OSD).

**Removing it again:** `./uninstall.sh` (in the package folder) reverts
everything - autostart, Scripts, optionally the program files themselves.
Asks whether your own boxart/music/settings should be kept
(`./uninstall.sh --yes` for "remove everything" without prompts,
`./uninstall.sh --keep-data` for "remove only program files" without
prompts).

## 4. Usage

Two pages: page 1 (main menu) shows only the categories (Systems,
Arcade, Scripts, System) as a large list; Enter/A opens a category on
page 2, where the game list is on the left and, for game systems, a wide
boxart+info column is on the right.

**The "System" category is divided into 7 thematic groups**
(RetroAchievements, Statistics & Achievements, Display & Sound, Behavior,
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
| F10 / X button                     | From the OSD back to the frontend |
| Y key                              | Next song (manual music change) |
| F11                                 | Random game/category ("don't know what to play") |
| F8 / L2 or R2 button                | Toggle favorite (game entries only) |
| F7                                  | Toggle completed status (game entries only) |
| 3x Select in a row (pad)           | Quit confirmation (like ESC) |
| In a running game: Esc on the keyboard, hold ~0.6 s | Directly back to the frontend, without going through the MiSTer OSD |
| In a running game: F12 -> "Exit to Menu Core" | Alternative via MiSTer's own menu |

**Returning from a running game:** As soon as a core is running, MiSTer
completely locks the normal keyboard/pad layer (verified: `cat
/dev/input/eventX` returns 0 bytes during a game, no matter what you
press) - Start+Select or F10 therefore never arrive during the game
itself; that is a platform limitation, not a frontend bug. But there is a
way around it: the *raw* HID layer of a connected keyboard remains
readable even during a running game. Holding Esc a bit longer (the hold
time is deliberately chosen so that a normal short Esc press in a game's
own pause menu doesn't accidentally trigger the exit) therefore takes you
straight back to the frontend. If that doesn't work for some reason (e.g.
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
   - Y key: next song
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

**Switching:** In the System menu under **Behavior -> "Music source"**.
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
  preferred in this order: Germany > Europe > World > USA > Japan
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
  merged into one entry - best region wins (Germany > Europe > World >
  USA > Japan). With complete No-Intro sets this can noticeably reduce the
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

## 7. System background images (optional)

For a console photo as a dimmed background per system: a good source is
the public-domain photos by Evan Amos on Wikimedia Commons (search for
"Vanamo Online Game Museum").
```
python art_convert.py --bg --images nes.jpg --out NES_320x240.art --size 320x240 --darken 0.25
```
Copy to `/media/fat/frontend/bg/`. System keys: NES, SNES, Genesis, N64,
PSX, GAMEBOY, GBA, SMS, TGFX16, MegaCD, Saturn, NEOGEO, ARCADE.

## 7b. System art box in the category menu

In the main category menu (page 1), an art box appears to the right of
the list with the logo/cover of the currently highlighted system -
changes live as you page up/down through the categories.

**Already included in the build** (located in `frontend/sysart/`, no
longer needs to be created yourself): all 13 currently supported systems
(NES, SNES, Genesis, N64, PSX, GAMEBOY, GBC, GBA, SMS, TGFX16, MegaCD,
Saturn, NEOGEO) have a real logo stored. In the subfolder
`frontend/sysart/_weitere_systeme_noch_nicht_unterstuetzt/` there are also
finished logos for nine more systems (Atari 5200/7800/Jaguar,
ColecoVision, Philips CD-i, Pico-8, Sega 32X, Super Game Boy,
TurboGrafx-CD) - for the day they get added.

Create your own/additional images (the same converter as for boxart, no
background mode needed):
```
python art_convert.py --images console_logo.png --out SMS.art --profile hd
```
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

## 8c. Recently played, loading progress

Active automatically, no setup needed:
- **"Recently played"**: a new category at the very top of the main menu
  as soon as you've launched your first game - up to 15 entries, newest
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

If that's too busy for you: all four effects can be turned off
individually in the code - let me know if you'd rather have a menu switch
for it.

## 8d. Attract mode / screensaver

After 45 seconds without input, a random game automatically appears
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
description, points, faded in at the top right, gone again automatically
after 8 seconds. No need to wait until returning to the menu. Its own
admin switch, if not desired.

**Setup:**
1. Turn on via SSH:
   ```bash
   /media/fat/Scripts/stream_toggle.sh on
   ```
   (only creates an enable file - without it the web server doesn't even
   start, so existing users notice nothing of it)
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
5. Turn off again: `stream_toggle.sh off` + restart the frontend.

Runs entirely on standard Python (`http.server` + server-sent events), no
external packages, as its own background thread next to the normal
frontend loop - binds to port 8080 on the local network. Do **not**
forward it to the internet, there is no authentication. Detailed setup
step by step (also for non-techies): `ANLEITUNG_fuer_Dennsen.md`.
Technical details: `STREAM_fuer_Dragrem.md`.

## 13. Troubleshooting

- **The key-mapping assistant freezes while configuring "Open OSD" / the
  screen goes black with a login prompt**: F9 is reserved on MiSTer for
  switching between console and graphics mode - if your pad sends a real
  F9 (e.g. via a Home/Guide key), the kernel probably intercepts it
  before our process sees it. The assistant therefore has a time limit
  (20s, skips the query instead of waiting forever) and generally rejects
  a captured F9 as a mapping. If it still occurs: share
  `tail -60 /tmp/frontend.log` right afterwards.
- **After a file update** (new version installed): simply run
  `/media/fat/Scripts/update_frontend.sh` (via SSH or from the MiSTer OSD
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

## 14. Known limitations

- ROMs inside ZIP archives are currently not listed.
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
- Start+Select and F10 generally don't work during a running game -
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
