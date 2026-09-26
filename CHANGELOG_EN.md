# Changelog

Kept short: one block per release, covering what you actually notice.

If you want the details — which measurement led where, which attempt
failed, what a test caught — they are in the
[full archive](docs/CHANGELOG_ARCHIV.md) (every build since v1.1, in
German).

Deutsch: [`CHANGELOG.md`](CHANGELOG.md)

---

## After v4.6 — not yet released

**Opening a folder was 80 % cover loading — and the cause was an
assumption that was measured correctly and then quietly went stale.**

A stutter on opening was reported: 476 ms on average, 1769 ms at worst. A
profiling run on the device broke it down:

```
_draw_page_items_impl        241 ms
  draw_art_panel             197 ms
    get_scaled               136 ms
      _thumb_cache_get       132 ms
        3x read()             66 ms   ← reading from the card
        zlib.decompress       64 ms   ← unpacking
```

The whole opening was the cover. And the comment at exactly that spot
held the assumption that had covered this for years: reading a cache file
costs **5.9 ms**. That was correctly measured back then — at the box size
of the time. At 1080p it has become 132 ms, twenty-two times as much.
Nobody did anything wrong; the number outgrew its frame along with the
covers, and because it sat there as a comment, it kept reassuring.

Thumbnails are therefore now stored as **JPEG** instead of zlib-packed
raw pixels — the file gets three times smaller, and the unpacking is done
by libjpeg in C rather than zlib against half a megabyte.

Three things deliberately *not* done across the board, all three measured
on real material (320×420, the HDMI box size):

| Image | raw | zlib | JPEG 97 |
|---|---|---|---|
| real badge `3DO.art` | 525 KB | 111 KB / 2.06 ms | 38 KB / 1.3 ms |
| smooth painted cover | 525 KB | 42 KB / 1.03 ms | 12 KB / 1.0 ms |
| noise (boundary case) | 525 KB | 363 KB / 3.10 ms | 360 KB / 3.3 ms |

- **Small images stay lossless.** Below 64 KB packed there is nothing to
  gain.
- **And it has to pay off.** The last row is why: there JPEG saves 3 of
  363 KB and unpacks more slowly. Anything that does not save at least
  half stays lossless. Both sizes are on hand when writing, so the
  decision is free.
- **Quality 97, not 92.** Measured against our own badges, because they
  are the hardest thing going through JPEG here — large areas, hard
  edges, lettering. At 92 individual edge pixels land up to 31 of 255 off,
  a faint ring you *can* find. At 97 it is at most 12 and 0.37 on
  average — below anything a screen shows. Costs 14 KB per image and is
  worth it.

**Nothing has to be rebuilt.** Both formats live in the same file and the
header decides — just as it already does for the "original fits" marker.
Old files are still read, and any large enough one is rewritten as JPEG
*on the side*. Each entry pays the old cost exactly once; with 97,000
entries that is the difference between a migration run and none at all.

Also: the cache file is read in **one** `read()` instead of three — 66 ms
in the profile.

*What I had to correct in myself:* my first test image was a generated
pattern, i.e. high-frequency noise — the worst case for JPEG, and
something no cover on earth looks like. The test reported "factor 1.1",
which would have been the wrong conclusion from the wrong image. With
real material from the repo it is 111 → 38 KB. And my first estimate of
"132 → 30 ms" was too optimistic; realistically it is about half, not a
quarter.

**A symlink loop can no longer hang the library scan.** The prompt came
from Degauss, which had to fix the same thing in v0.9.0 — but on
checking, ours was in worse shape, and *that* is the finding. The top
level had long been protected; the recursive descent was not at all:
`os.path.isdir()` follows symlinks, so a single link pointing upwards
(`games/SNES/alles -> /media/fat/games`) made the scan circle until
Python gave up. With 97,000 entries that hits the worst possible moment —
rebuilding the library.

The check is now against the **ancestors** of the current path, not
against "seen before". The difference matters: a global set would also
have skipped a folder that legitimately appears twice (two links to the
same collection), quietly swallowing games. Only what already occurred on
the way *here* is a loop. Plus a depth cap of 24 as a second belt, and
every skipped spot is logged once — a silently omitted folder is exactly
the kind of fault you notice only when games are missing.

And it costs almost nothing: `realpath()` is expensive but is only needed
for **symlinks**. An ordinary subfolder cannot form a loop; its real path
is the parent's plus the name — computable without a single system call.
In the test: twelve subfolders, exactly **one** `realpath()`, for the
starting folder. All verified against a real loop on disk, not a mock.

**And in the system menu it still appeared — because these are two
different faults.** Reported: scrolling down in System → Display & sound
still brought the login greeting. The difference is measured:

- **Takeover** — MiSTer re-initialises the framebuffer, *every* pixel
  changes. The picture guard finds that reliably with eight probes.
- **Text** — the login greeting is just a few rows of letters. In a test
  with 2669 pixels set across rows 8–48 the guard did **not** find it:
  the probes sit between the glyphs. More probes cannot cure that, it
  would stay luck.

For the text case the right remedy has existed for a long time — simply
rewrite the topmost rows regularly, without detecting anything. It only
sat in the idle branch of the main loop, and that branch is skipped as
soon as input is pending. Which is exactly why the greeting came through
while a key was **held** and never otherwise. It now also runs once per
action; the throttle lives in the method itself (four times a second,
0.8 ms), so calling it more often costs nothing.

*Its test* now computes the real block extent in the source instead of
"nearest preceding `if` plus indentation" — the old technique would have
falsely reported the new call as part of a long-finished branch. That
makes three times this one check had to be sharpened, every time for the
same reason: it estimated where it could have calculated.

**The login greeting while scrolling is a much older fault than it
looked — and the frontend now takes its picture back by itself.**

It was reported after the main menu got faster. I had three
explanations, all wrong; again a measurement decided it. The read-back
checker verifies after every frame that the framebuffer still holds what
we wrote:

```
RUECKLESER: nach 26.9 s steht in 15 von 15 Proben-Zeilen fremder
Inhalt (Zeilen 0,16,32,48,90,180,270,360) - 2 Treffer bei 109 Bildern
```

**Fifteen out of fifteen.** That is something entirely different from
the finding behind the previous repair (two rows at the top, constantly).
Nobody is writing text here — the *whole picture* is no longer ours:
rarely, about once every hundred frames, but completely. And for anyone
with `fb_terminal=1` the **Linux console is the layer underneath** —
which is why it is the login greeting that appears and not something
else.

> *Addendum, measured:* the cause given here at first was that MiSTer
> re-initialises the framebuffer during operation. **That was wrong.**
> The user's `dmesg` shows `MiSTer_fb` lines only at startup (12:47:54
> and 12:48:12), while the guard's repairs happened at 12:49:09, 12:50:39
> and 12:59:34 — not one re-initialisation among them. The real cause is
> in the `inittab`:
> `console::respawn:/sbin/agetty --nohostname -L tty1 linux`. The agetty
> on `tty1` had PID **2725** while the one on `console` had 1126 — so it
> had restarted, and a fresh agetty **clears the screen** and writes its
> greeting. Clearing the console produces no `dmesg` line, but it does
> explain why all fifteen probe rows were foreign. The guard is still
> right and still useful — it takes the picture back whoever removed it.
> Only the reasoning was guessed, and that belongs corrected rather than
> quietly replaced.

That also settles what speeding up the main menu really did: every
scroll step used to copy 804 of 1080 screen rows, so such an outage was
three quarters painted over within 80 ms and went unnoticed. Now it is
120 rows, and the rest stays while a key is held. **The fault is older**,
it was merely covered up by accident — at 85 ms per scroll step as the
involuntary price.

The remedy exploits the fact that our buffer stays intact: nothing needs
redrawing, everything just needs copying once. After every partial flip,
eight pixels on screen are checked against **what was last written** —
not against the buffer, which legitimately runs ahead of the screen, and
that distinction is the entire reason there are no false alarms. If one
pixel does not match, someone else was at work, and the picture is
copied in full. Two of the eight sit in the topmost rows, where the
greeting appears.

Measured, the check costs **0.001 ms per frame** (0.8 %). The repair
itself only happens in the real case and is capped at five times per
second — if MiSTer wipes continuously, every partial flip would
otherwise become a full-screen copy and scrolling would end up slower
than before. How often it happens appears as `BILDWAECHTER:` in the log.

So the stopgap can go again:

```
rm /media/fat/frontend/artbox_aufschub_aus
```

The guard can be switched off with
`touch /media/fat/frontend/bildwaechter_aus`.

**The latency tally now names every action separately.** It used to be
one mean across everything:

```
LATENZ-BILANZ: 125 Schritte, Mittel 126 ms, schlechtester 205 ms (right)
```

That line answers no question. It mixes a 6 ms scroll step in the main
menu with a view switch that rebuilds a whole page — and so it could not
even show whether the change below it had taken effect at all. A second
line now comes with it:

```
LATENZ-JE-AKTION: ok/S1 1x Mittel 400 (max 400) | right/S1 4x Mittel 150
                  (max 150) | down/S0 21x Mittel 6 (max 6)
```

Per action **and page**, because the same key triggers entirely
different work in the main menu and in the game list. Sorted by the
mean, not by the outlier — what is wanted is whatever is constantly too
slow. The step count is included, because a mean over two steps is not a
statement.

That is the fourth measurement I had to sharpen today, and all four had
the same cause: they summarised what you need separately.

**Plus a single switch for the deferral below.** It was reported that
the login greeting flashes up again while scrolling with a key held.
Whether that is caused by the deferral could not be measured with
"covers immediately" — that switches two things at once. Hence:

```
touch /media/fat/frontend/artbox_aufschub_aus
```

That restores exactly the pre-change behaviour in the main menu, and
nothing else. Without the file the deferral stays on.

**The main menu now scrolls noticeably more smoothly — and the very
line that measured it buried a plan of mine.** The measuring tool from
v4.6 produced this eight times in a row in the main menu, with a
direction key held down:

```
RUCKLER: 85 ms busy (zeichnen=82 rest=3
         | davon bg=11 rows=4 art=17 flip=50)
```

`rest=3` means: nothing is being waited for, computed or managed — it
is being painted. That settled the planned decoupling of input and
drawing **before** it was built. It would have gained nothing here.

The breakdown shows that all three large items have *one* cause: the
logo column on the right. It is cleared (11 ms) and redrawn (17 ms) on
every single scroll step — and because the framebuffer can only be
copied in whole screen rows, the copied strip has to span everything
between the two changed text rows on the left and that column on the
right. 120 rows become 804, and that copy is too large to still fit
into one display change: it waits for the next one (50 ms). The two
rows that scrolling is actually about cost 4 ms.

So while a key is **held**, the logo now stays as it is and is brought
up to date as soon as the cursor comes to rest — exactly how the game
list has done it since build 96. The copied strip shrinks from 804 to
120 rows and drops below the threshold above which the display change
has to be waited for at all. A **single** key press is unaffected: the
logo appears immediately there, as before. Anyone who has "covers
immediately" switched on also keeps the old behaviour.

*What nearly went wrong:* the fast page build does not clear the logo
column — it may skip that, because all badges are exactly the same size
and the new one fully covers the old. Except for a category with **no**
badge: there a narrower placeholder appears instead of an image, and
the edge of the old card would have been left behind. Until now that
could not happen, because the clearing ran on every step. The test does
the arithmetic: 58,131 pixels would have been wrong.

---

## v4.6 — Kernel 6.18, and six explanations that a measurement outlived

A release in which almost nothing was guessed. The jump to kernel 6.18
brought three faults to light, a reported twitch used up six
explanations before the right one was left, and two of the faults found
had been sitting in our own source for months — they only became
visible once someone measured.


**The login greeting that flashed up while scrolling is gone — and
this time the cause is known.** Reported after the kernel update: after
50-60 seconds the login greeting flashes through, then irregularly
again and again. Three rounds of suspicion went to the wrong place. A
measurement settled it — on request the frontend checks after every
frame whether what it wrote is still in the framebuffer:

```
RUECKLESER: nach 104.6 s steht in 2 von 7 Proben-Zeilen fremder
Inhalt (Zeilen 0,32) - 10 Treffer bei 21 Bildern
```

Ten hits in twenty-one frames, **only in rows 0 and 32** — the other
five probes stayed clean. So something does write into it, but only at
the very top: the text console that MiSTer renders itself. Our own
console machinery is thereby cleared; the greeting appeared with it
switched off too.

The remedy is the simplest one available: the top 64 rows are simply
written again, four times a second. On 1080p that is 491 KB, about
0.8 ms — and it does **not** hang off the machinery switch, because
the cause is not ours.

**And then I stopped retrofitting path by path.** First the main page
was missing, then the grid and gallery views — each time the remainder
sat at the full duration, each time another path got instrumented. Yet
there is one place every drawing path goes through, and it was already
timing itself. The line now carries `zeichnen=` as a top-level item —
complete, whatever the view — with the individual items as its
breakdown. One line now answers the question that matters: is the time
in drawing at all, or outside it?

**And it found the next gap immediately — in the main menu.** With
the new remainder in place the log showed eleven identical lines,
`82 ms busy (bg=0 restore=0 rows=0 art=0 flip=0 rest=82)`: the entire
cost unaccounted for. The main page was the only one never measured at
all — neither its fast navigation path nor its full build. That is
what the remainder is for: it reports the gap itself instead of hiding
it behind plausible numbers. Both paths now report.

**The stutter breakdown was wrong — in exactly the path that runs
while scrolling.** The log showed fourteen identical-looking lines,
`202 ms busy (… bg=20 restore=6 rows=36 art=0 flip=22)`. Those items
add up to 85 ms; where the other 117 went was written nowhere. And
three of the numbers were letter-for-letter identical across all
fourteen while the measured time varied — they were only set on a full
page build and carried over as leftovers on the fast path. The line
looked plausible and led straight to the wrong place. Now every item is
zeroed before each action, the fast path reports its own, and the line
carries a **remainder**: if that is large, the tool says so itself.

**The frontend now measures what you actually feel.** There were two
numbers — how long a draw takes, and how long processing plus drawing
take together. Neither answers the question that matters: *key pressed
— when is the picture there?* That one is in the log now, with a tally
every 30 seconds even when nothing stood out. For a **held** key it
counts from when the repeat was due, not from the moment it fired: you
are not pressing again, you are holding — and what you feel is the gap
between steps. This is the groundwork for decoupling input from
drawing; the rework follows, aimed by these numbers rather than by a
hunch.

**The covers from `gamelist.xml` are used too.** It holds not only
year and genre but the image paths as well — and those point at files
Skraper has already downloaded **and matched by the ROM file's
checksum**. That is exactly what our fuzzy name matching has always
been working around; for a curated folder it disappears entirely. The
precedence stays: your own artwork wins, then the `gamelist.xml`, then
the foreign database. An entry pointing at nothing is skipped rather
than mistaken for a cover.

**`gamelist.xml` is now read.** Anyone who has curated their ROM
folder with Skraper, ScreenScraper or a similar tool has a
`gamelist.xml` in EmulationStation format sitting there — year, genre,
player count, publisher and a description. Exactly what the frontend
otherwise assembles from its own table and the foreign database. If
it's there it gets used; if it isn't, nothing changes. No tool, no
download, no preparation. The precedence is deliberate: your own data
beats the `gamelist.xml`, which beats the foreign database — and only
gaps are filled, nothing is ever replaced. The file is read in chunks;
a list with 10,000 entries is easily 20 MB, and that does not belong
in memory all at once on a 1 GB device. Turn it off with
`touch /media/fat/frontend/gamelist_aus`.

**The bench now knows three states instead of two.** Between "cold"
(the thumbnail has to be computed) and "warm" (it's in RAM) the one
case that matters most while scrolling a large collection was missing:
**the thumbnail is on the card but no longer in memory** — evicted, or
the frontend was restarted. Read, decompress, insert. That number was
nowhere, and it is precisely the one that decides how the device feels
day to day.

**The installer was overwriting itself.** Reported by a user during
installation: `syntax error near unexpected token 'fi'`, mid-run. The
file was fine — the fault appeared only while running. The script being
executed lives in `/media/fat/Scripts`; bash reads it in chunks and
remembers its position in the file. A `cp` writes into *that same*
file, so different content suddenly sits under the remembered position.
That it only happened sometimes fits: it depended on whether the file
differed at exactly that spot. All three installers now write alongside
and rename — a rename only swaps the directory entry, leaving the
running script untouched.

**The RetroAchievements fetch ran twice at startup.** A long comment in
the source explains why that fetch was moved to a background thread: it
held the start up by as much as 3.5 seconds with the screen dark. But
the old, blocking version was still sitting forty lines above it. Both
ran. The improvement the comment describes never actually happened. It
surfaced through measurement, not through reading. Now it is what the
comment says it is.

**The frontend now notices when its own parts don't match.** On one
device `frontend.py` from build 184 sat next to an `fe/art.py` older
than build 180 — copied in by hand, that one file only. The crash came
not at startup but on the first press of an arrow key, and on screen it
looked like *"the frontend quits and I end up in the OSD"*, i.e. like a
kernel or display problem. It cost an hour of searching in entirely the
wrong place. At startup the frontend now checks once whether
`frontend.py` and the `fe/` package fit together; if something is
missing it says plainly **what** is missing, **since when** it belongs
there and **how** to fix it. It does not abort — a frontend that
refuses to start because of this check would be worse than the problem.

**The boot logo is back on kernel 6.18.** Reported as *"I see the OSD
a bit longer, then briefly the login prompt, then the frontend — the
boot logo doesn't show any more"*. The fault was not the logo but the
order: before the boot animation the frontend waits for MiSTer to hand
over the screen — painting a logo into a framebuffer nobody is looking
at is wasted time. But that handover is triggered by the F9 retries,
and those run from the main loop, which only starts *after* the boot
animation. So we waited for someone to knock while keeping our own
hand still. On 5.15 it never showed, because there the first F9
landed. The wait loop now retries by itself, and its ceiling goes from
6 to 12 seconds. Press a key and you wait not at all; get the handover
straight away and you notice nothing.

**Kernel 6.18: startup now holds on by itself.** After the MiSTer
Linux update the old report came back — *"I'm stuck in the OSD and
hear the frontend's music"* — plus a login greeting that reappeared
after 20-30 seconds of idling and stayed until the next key press. The
cause is the same as on quit: **a single F9 no longer lands reliably
on this kernel.** MiSTer re-initialises the framebuffer several times,
and knocking before that is knocking at a door that does not exist
yet. So on **kernel 6 and newer the frontend switches the console
machinery on by itself**: the F9 is repeated, a watch wipes foreign
output away, console blanking stays off. On 5.15.1 nothing changes.
Either side can be forced with `konsole_mechanik_an` or
`konsole_mechanik_aus`, and the log says which way it went.

**The twitch at full resolution disappeared with that same kernel
update.** It was never the frontend. Six explanations had been
measured and discarded before that — input leak, skipped vsync, memory
bandwidth, the cover path, a second framebuffer page and foreign
writes; the final measurement showed that over 294 seconds **not a
single byte** changed in our framebuffer while it visibly twitched.
The instruments built for it stay in place (`flip_haeppchen`,
`flip_rueckleser`, `fb_wacht.py`), all off by default.

**Hunting the twitch: four explanations ruled out.** At full
resolution MiSTer's own menu picture flashes through eight times a
minute for one or two frames, always close to a scroll step, never at
half resolution. Four theories have now been **measured and
disproved**, each of them plausible:

* *Our input reaches MiSTer and wakes it.* It wakes no more often
  while scrolling than when idle.
* *Skipped vsync.* Full frames have waited without exception since
  v2.2.
* *The memory bus is saturated by writing 7.9 MB in one go.* With the
  `flip_haeppchen` switch (16 chunks, 500 µs pause) the transfer took
  34 ms instead of 12.6 — three times as spread out, and the twitch
  was unchanged.
* *It is the covers.* It twitches in categories without a single
  cover too.

Two possibilities remain, and they exclude each other: someone
**writes** into the framebuffer, or the display layer is **switched
away**. Two tools answer that, both **off by default** and both
without any effect on the picture:

* `flip_rueckleser` — on every write the frontend remembers eight
  rows and checks on the next frame whether they are still there. A
  difference means *written*; no difference while it visibly twitches
  means *switched away*. Every 30 seconds it writes a tally to the
  log even when nothing happened — otherwise its silence would not
  say whether it found nothing or never ran, and a tool that only
  speaks on success can confirm a theory but never disprove one.
* `fb_wacht.py` — the same question without a running frontend, using
  a test pattern in the framebuffer. It also works out whether there
  is room for a second page there; on the DE10-Nano there is not,
  which rules out page flipping as well.

The chunked transfer stays as a switch so the measurement can be
reproduced: 56 combinations of sizes and chunk counts are bit-identical
to the previous path.

---

## v4.5 — CD games in folders, a C module, a PC tool

**Grid covers did not load in at 1080p.** Found through a video from
SuTe: the grid stayed nearly empty, a cover appeared only on the tile
you stopped on, a page turn emptied everything again, and the gallery
often lacked its big cover. His `--bench` showed his device is not
slower — the image chain is within 1–2 % of a second device. There
were three faults in the flow: the idle redraw painted only two tiles
in the grid, so finished covers for the others sat on the card and
never showed; a key press cancelled the jobs sent to the worker
process but left their wait markers behind, after which the main loop
redrew endlessly while idle; and the emergency brake took the worker
for hung after two seconds although it had 21 tiles to work through —
then the drawing path computed them itself, and for 100–500 ms per
tile nothing responded. At half resolution the covers are small enough
that none of these faults came into play. *Correction:* an earlier
version said here that this was the twitching. That was wrong — the
three faults are real and fixed, but the twitch also occurs in
categories without a single cover.

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

**And the second run found the biggest fault — on the screen, not in
the file.** "The bench always ends up in Super Game Boy, then
nothing happens, no covers scroll." Exactly so: **which category got
measured was an accident.** The cursor stayed wherever the loop over
the main page had left it — PlayStation on the first run, Super Game
Boy with a single entry on the second. There the selection never
moves, the picture never changes, and what gets measured is a still
image. That also explains the three figures 52.98 / 52.97 / 52.99
from that run: three completely different drawing paths, identical
to the hundredth, because none of them had anything to do. The
largest category is now chosen **deliberately**, its name and entry
count appear in the report, and a too-short list gets a warning. Two
further findings: every per-step figure contained the **vsync wait**
(50.0 ms is exactly three frame periods at 60 Hz — what was measured
was the refresh rate), it is now outside the measurement and
reported once on its own; and the cache redirect only applied to the
parent process, because the prewarmer has been a **separate
process** since build 102 — it kept writing to the card while the
parent never found anything in the temporary folder. For the
measurement the drawing path now computes covers itself.

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
