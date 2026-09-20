# Changelog

Kept short: one block per release, covering what you actually notice.

If you want the details — which measurement led where, which attempt
failed, what a test caught — they are in the
[full archive](docs/CHANGELOG_ARCHIV.md) (every build since v1.1, in
German).

Deutsch: [`CHANGELOG.md`](CHANGELOG.md)

---

## v4.5 — CD games in folders, a C module, a PC tool

**The frontend measures itself: `--bench`.** Every number in this
project since build 73 was hand work — set the profile switch,
scroll, `grep PERF`, type it up. That yields numbers for one device
on one day; nothing could be compared between two machines.
`python3 frontend.py --bench` now runs one fixed sequence: startup
time (also **per game**, so 2,000 and 97,000 games stay comparable),
full page build and time per scroll step across all three views on
both pages, the raw frame transfer, and the whole image chain —
downscaling in C versus Python, packing, writing and reading a
thumbnail, decoding a PNG. The trick is in the test image: it is
**generated** rather than read from the card, and the sizes are
fixed, so two devices really do measure the same thing. What cannot
be compared in principle — a real cover file — sits in its own
section with exactly that caveat next to it. The run **writes
nothing to the SD card**; what it has to write in order to measure
goes to a temporary folder that is removed afterwards. Report on the
console and in `/tmp/dragend_bench.txt`.

**The first bench run on real hardware convicted the bench itself
first.** Five faults, all in the measuring tool, none in the
frontend — the worst: the run **did write to the card**. Drawing
computes covers, and a computed cover gets written out as a
thumbnail, so the promise in the report was untrue. During a run the
thumbnail cache now points at a temporary folder — the promise holds
again, and every device really does start cold on the cold pass.
Also: writing a thumbnail was measured at compression level 6 while
the frontend has used level 1 since build 154 (1,176 ms was reported
for something that takes half as long); the cover search expected a
list where a folder tree stands, and so reported "no cover found" on
a card with 30,064 games; the test image took 25.5 seconds, two
thirds of the whole run, purely as preparation — now about one
second; and the per-step figure lumped drawing together with
computing covers. **Cold and warm are now reported separately**,
with the honest note that cold is the upper bound and not everyday
use: while scrolling for real, the frontend skips the cover column.

**Folders holding a single game are dissolved.** For PSX, Mega CD and
Saturn, each game usually sits in its own folder because one `.cue`
comes with several `.bin` files. That made the list nothing but folders
— and with no games in it, there was no cover art, no grid and no
gallery. Now the game itself appears in the list. Multi-disc games (two
`.cue` files in one folder) stay folders, because there you do have to
pick. Can be turned off under *System → Options*.

**A C module for the two most expensive image operations.** Scaling
cover art up and down now runs in `libdragend.so`. Measured on the
device: **102 to 143 times faster** (1888 → 18 ms). Covers no longer
trail behind while you scroll. If the library is missing, the frontend
computes in Python as before — it is an option, not a requirement.

**A Windows tool that prepares the thumbnails on your PC.** It connects
to the MiSTer over the network, renders the covers on every core your PC
has, and copies them back. Six hours on the MiSTer become minutes. Lives
in `pc_tools/`.

**Cold boot sometimes ended up in the OSD.** Two days of hunting and
four dead ends. The frontend had no way of knowing whether its own
picture was on screen at all — until it turned out that MiSTer's CPU
load says exactly that: 100 % in the OSD, 1.4 % at the console. After
that it was three lines of code.

**The login prompt stays away.** "Welcome to MiSTer / login:" could
appear at the top of the screen during normal use — while rescanning
the game list, and sometimes just sitting in the menu. The login
process on `tty1` writes into the same framebuffer as the frontend, and
until now that was only cleaned up during startup. On top of that, an
idle frontend usually transfers just a few rows at a time (marquee,
clock) — never the topmost ones, which is exactly where the prompt
sits. A watchdog now checks once a second and clears it within two.

**A race that made thumbnails disappear.** Cache cleanup deleted
leftover temporary files — including ones another thread was still
writing to. The freshly computed thumbnail was gone, "prepare
thumbnails" reported *done* anyway, and the cover still loaded in while
scrolling. A test had flagged this twice since build 119 and it could
never be reproduced; it only became visible once the C module made both
threads fast enough to reliably overtake each other.

**Quitting no longer returned to the OSD.** For two days, *Quit
frontend* left a black screen with a blinking cursor, followed by the
login greeting. Self-inflicted: while reworking the shutdown sequence
the F12 moved to the front, but clearing and releasing the framebuffer
stayed at the end — so we painted over MiSTer's freshly drawn OSD. The
screen now belongs to MiSTer from the F12 onwards, and a test pins the
order down.

**Sharp cover downscaling — for CRTs.** Until now covers were always
averaged: the better picture on HDMI, often not on a CRT, where pixel
art turns to mush. *System → Display & Sound* now switches to
nearest-neighbour — computed in C and four times cheaper than
averaging. The mode is part of the thumbnail cache key, otherwise the
old thumbnail would simply stay; both variants live side by side, so
switching back is instant.

**Core management.** When several versions of a core sit on the card
— the NeXT core easily has four, with telling names like
`scsi_dma_csr_fix` — *System → Options → Cores* now lets you pick which
one a system launches. Previously the frontend always wrote the undated
name and MiSTer decided alone. A chosen version only applies while its
file exists: `update_all` deletes old cores on every run, and a game
that silently stops launching would be the worst trade. Nothing is
downloaded here — that stays with `update_all`.

**Portrait-mounted screens (TATE), first step.** The frontend never
crashed there — it was unusable, because the layout scale depended on
height alone. At 1080×1920 that left **23 characters per line** instead
of the 68 everything is designed around, cutting every game title to a
third. Landscape still uses the height; portrait now uses the width,
the scarce side. That makes 38 characters instead of 23.

**Portrait, second step: how the area is divided.** After the first
step the frontend was usable in portrait, but the layout was still
proportioned for 16:9. Measured at 1080×1920: in the **grid view**,
**993 of 1497 pixels of height stayed empty** — two thirds of the
area the view exists for — and the tile, at 117×156, was the size it
has in landscape on a 720p screen. In the **gallery**, the data
column next to the big cover had **seven characters** instead of 52,
because the cover is sized from the height and in portrait the height
is vast. And the **cover panel** on the list was **68 %** empty
(landscape 11 %) while the list beside it cut titles at 20
characters. The grid now derives its layout from the tile size
instead of fixing it (4×5 instead of 7×3, tile 213×285, height fully
used), the gallery puts the data **below** the cover in portrait — 38
characters instead of 7 — and the list column gets 62 % of the width
instead of 52 %: 24 characters, and the cover is now proportionally
the size it has in landscape rather than larger. Landscape does not
change by a single pixel; the old measurements are pinned as fixed
numbers in the test.

**A colour scheme editor.** *System → Display & Sound → Edit your own
colour scheme*: six colours and the monochrome switch, editable with
the pad, with a preview below showing exactly the elements each colour
appears in. Up/Down picks the row, Left/Right changes it, Enter cycles
R, G and B, ESC leaves without saving. Corner radii and font sizes are
deliberately left out.

**Your own colour scheme.** *System → Display & Sound → Save current
colours as your own scheme* writes the active colours to
`frontend/theme_eigen.json` and switches to them right away. *Custom*
then appears in the normal cycle; you can fine-tune the file by hand. A
broken file simply means "no custom scheme" and never holds up startup.

**The cover cache had no memory limit.** It held 60 images — a
*count*. Since v4.4 covers load at full resolution, and a 1200×1600
scan is 7.7 MB: 60 of those would be 460 MB on a device with about
1 GB. There is now a 48 MB budget as well, built like the proven
eviction of the scaled cache. With small covers nothing changes.

**On kernel 6.18 the first F12 on quit does not land.** That is the
heart of the matter, and it is measured rather than guessed — on a
second device running 6.18.38 the log reads *"MiSTer bei 1% - das OSD
ist NICHT gekommen, fasse nach"*, and one second later *"MiSTer bei
100% - das OSD ist da"*. The frontend therefore checks MiSTer's CPU
load after the F12 to see whether the OSD really appeared, and retries
up to three times. On the old kernel this costs nothing: there the
first measurement reports 100 % straight away.

**The MiSTer Linux update of 2026-09-07 (kernel 6.18) breaks
frontends — this one included.** Rolling back to kernel 5.15.1 fixed
every reported symptom without changing a single line of the frontend.
You can spot it by `fb0: sys_fillrect: framebuffer is not in virtual
address space` in `dmesg`. Degauss, the Zaparoo Frontend and Console
Mode all had to be patched for it too. Dragend now falls back to
mapping the framebuffer through `/dev/mem` when `/dev/fb0` no longer
allows it. And `frontend/kernel_probe.py` measures, on an affected
device and in two minutes, where the problem actually is — that is how
the item above was settled. See the section in the README.

**At startup the machinery from builds 146–166 is switched off again.**
Eleven builds had piled up there; every change had a reason, but
together they got in the way more than they helped. The default is back
to: **one** F9 at startup, no watchdog, no touching the cursor or
screen blanking, boot logo straight away. Only the exit measures —
because there it is proven that one F12 is not enough.

**Nothing was deleted.** The machinery from builds 146–166 comes back
with one file: `touch /media/fat/frontend/konsole_mechanik_an`. Its
reasons were real and measured — above all "I'm in the OSD and I can
hear the frontend's music". If that returns, the answer is a command
rather than a build.

**Everything that writes to the text console goes through a single
place** (cursor, screen blanking, the watchdog against the login
prompt). It used to be six scattered ones, which made it impossible to
either inspect or switch off.

**The boot logo waits until someone can see it.** It was being drawn in
full — our framebuffer just wasn't on screen yet. It now starts once
MiSTer is demonstrably asleep.

**Startup is fast again, saved filters included.** A single saved
filter cost a measured 2.2 seconds — not the filtering itself (measured:
8 ms for 1800 games) but the tables read from the card for the first
time while doing it. That now happens in the background, while the game
list is being scanned.

**Also:** filter the list by genre, year, player count and developer
(Tab, or Select+L2/R2); game descriptions in the gallery view; eleven
German hint lines were invisible on CRT; thumbnails are written twice as
fast; scrolling no longer touches the SD card on every step.

## v4.4 — Views, artwork sources, speed

**Three views, everywhere.** Both the game list *and* the main page
switch between list, grid and gallery — permanently via the menu, or
just for the open category with F10 / Select+Y.

**ROMs inside ZIP archives** are found and launched without anything
ever being extracted.

**A second source for cover art:** if the artwork database sits under
`/media/fat/docs`, it gets used too. Your own artwork still wins. Covers
load at full resolution instead of being cut down to one box size.

**Noticeably smoother.** A real profiling run on the device turned up
four brakes: game descriptions cost 159 of 259 ms per page build, the
grid copied the whole screen on every step, each scroll step read from
the SD card five times, and downscaling a cover took twice as long as
it needed to.

**Fixes you can see:** red and blue were swapped in every thumbnail; at
half menu resolution all cover art disappeared; achievement popups were
invisible in grid and gallery; the offline installer could not find its
own package.

## v4.3 — large combined release

Rainwave internet radio as a second music source, a volume control, an
eight-step first-run wizard, SNES Tracker and SMW Hacks as their own
categories, update notifications via GitHub, the "Wonne oder Tonne"
rating format, more hidden achievements and seasonal decorations.

Plus a dozen fixes — among them: `(Unl)`/`(Pirate)` ROMs were wrongly
discarded, a stale scan cache survived changes to the filter logic, and
the clock stayed wrong for the whole session if the first sync failed
and RetroAchievements was not set up.

## v4.2 — clock stayed wrong for some users

The retry for a failed time sync only ran through the RetroAchievements
mechanism — anyone without RA got no second attempt at all. There is now
an independent path.

## v4.1 — volume control

For music and menu sounds together (0/20/40/60/80/100 %), new menu entry
under *Display & Sound*. Applies to MP3 and Rainwave radio alike.
Contributed by TheRealSutefan, tested on real hardware.

## v4.0 — batch of feedback

F11 now really launches a random game instead of just moving the
selection. Titles no longer get cut off on CRT; they shrink instead. The
attract mode delay is configurable (30 s to 15 min). System menu
reorganised.

## v3.9 — batch of feedback

Games outside `/media/fat/games` are discovered dynamically (network
shares, USB numbers above 5). ROM hacks and randomizers are no longer
treated as junk. All region variants of a game stay selectable. F10 to
leave a game works reliably.

## v3.8 — Rainwave internet radio

A second music source next to local MP3s, five stations, track titles
via the public API. Feeds the stream overlay too.

## v3.3 to v3.7 — the Esc exit, in four attempts

Leaving a game did not work at all on some keyboards. Three fixes missed
because they were built on guesses rather than data. The real cause
showed up only in a log file from the affected machine: a mechanical
keyboard registers three HID interfaces under the same name, and the
keystrokes went through one other than the monitored one. All of them
are watched now.

## v3.2 — consolidated

Default boot animation, text-truncation and scrolling fixes across nine
info screens (found with actual CRT photos), trophy room rebuilt, RA
achievement showcase sped up.

## v1.1 to v3.1

The build-up phase — from the first game browser through cover art,
music, gamepad control, RetroAchievements, the playtime tracker and the
trophy room to CRT support. Listed individually in the
[archive](docs/CHANGELOG_ARCHIV.md).
