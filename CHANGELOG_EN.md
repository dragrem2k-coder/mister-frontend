# Changelog

Kept short: one block per release, covering what you actually notice.

If you want the details — which measurement led where, which attempt
failed, what a test caught — they are in the
[full archive](docs/CHANGELOG_ARCHIV.md) (every build since v1.1, in
German).

Deutsch: [`CHANGELOG.md`](CHANGELOG.md)

---

## After v4.7 — not yet released

**MiSTer's own favourites, `update_all` from the menu, and an eye on
storage.**

- **MiSTer favourites**: whatever you marked as a favourite in the MiSTer
  OSD now sits **inside your favourites category** — one list, two sources.
  Yours first, MiSTer's after, duplicates only once. The entries behave like
  any other game: box art, description, play time, RetroAchievements, all of
  it works. Nothing is written into your own favourites file: remove a
  favourite in the MiSTer OSD and it is gone here too.
- **Run `update_all`**: a menu entry next to the core selection, with the
  last run in its label ("23 days ago"). It launches the existing script —
  nothing is reimplemented. There is deliberately *no* network check for
  "are updates available": that would mean rebuilding the MiSTer
  downloader's databases, a second source of truth for the most important
  files on the card.
- **Storage watch**: plug in a USB stick while the frontend runs and it
  says so. It does **not** rescan on its own — that takes minutes with
  30,000 games and stays your decision.

Two things I had to correct about my own claims while looking: the core
management from Build 174 is fully wired after all, and the **core browser
has existed all along** — System menu → *Cores*, where you pick the core
version per system with left/right, including a warning when the chosen
file was deleted by `update_all`. I checked both before building, which is
exactly why nothing here was built twice.

**Fast scrolling works again — and a number that was missing.**

- **Tile view**: "fast scrolling" had had no effect in the tile view since
  the large tiles arrived (v4.7). The cause was a single limit: a copy was
  allowed to skip the wait for the display refresh up to a quarter of the
  screen height — but a band of large tiles is a good third. The limit is
  now 40 %, measured across all eight resolutions; a full page redraw
  (84 %) still waits, because that is where the visible tear appears. With
  the switch off nothing changes: everything still waits, as before.
  The **gallery** copies the whole screen on every step and therefore still
  waits — that is its own piece of work, not a number.
- **Stutter line**: `flip=` was two things in one number, copying *and*
  waiting. It now says "davon vsync=" beside it. That mix-up sent me to the
  wrong place twice; from now on the line says which it was.
- **Bench**: new section H, the transfer matrix — what a copy into the
  framebuffer costs per size and per call, and what follows for merging
  adjacent bands. On a PC it says "not measurable" rather than inventing a
  number.

**Scrolling: a fifth of the bytes onto the screen.**

- **Rectangles instead of bands.** Until now every partial copy spanned the
  *full width*, even when only two tiles had changed — `flip_rows()` knows
  nothing about columns. Measured at 1080p per scroll step:

  | | before | now |
  |---|---|---|
  | Tile view left/right | 3.74 MB | **1.19 MB** |
  | Tile view up/down | 6.50 MB | **1.19 MB** |
  | Gallery | 7.91 MB (full screen!) | **3.71 MB** |

  The **gallery** had been copying the entire screen on every step since
  v4.2, even though it only redraws the cover, the text and two strip tiles.
  That is why "fast scrolling" never did anything there. It still waits for
  the display refresh — 3.71 MB is 47 % of the screen, and a tear across
  cover and text would be visible. The tile view, at 15 %, may skip it.
- The copying runs in C (the same function that has restored the background
  since v4.6); without `libdragend` a Python path writes bit-identical
  output. Should short rows turn out to cost more per byte on your card,
  `touch /media/fat/frontend/rechteck_flip_aus` is enough — no update. The
  number for that comes from the new **bench section I**.
  *Measured on the DE10-Nano: short rows cost only 1.2x as much in C, and a
  scroll step 3.46 instead of 18.55 ms — a factor of 5.4.*

**Clearing the background in C — the forgotten half of v4.6.**

- Before drawing, the background is restored row by row. For the box-art
  column that has run in C since v4.6; for **everything else** it still ran
  in Python — and that is exactly what happens on every scroll step: 815
  rows in the tile view, 1541 in the gallery. Both now go through the same
  C function. On the device a short row costs 2.6x as much in Python as in C
  (measured, bench section I), and clearing is close to a third of a step.
- **Bench section J** is new and says what a step *consists of*: restore,
  blit, flip and the remainder, per step, with call and row counts. Until
  now the bench only said what a step costs, not where the time goes.
- **Correction to section E**: it compared scroll blitting on the main page
  against the *full* page rebuild (83 ms). But scrolling runs the fast path,
  which stood in the same report at 60 ms. The saving was overstated by
  23 ms. E now measures the fast path itself.

**The gallery no longer waits for the display refresh.**

- The text column on the right was cleared over its **entire height** on
  every step — 1268x495 pixels, 2.39 of the 3.71 MB a step copies. That
  space was being made for the description, which while scrolling has
  deliberately not been drawn since v4.6. Now only the height that actually
  held text on the previous step is cleared: **1.74 instead of 3.71 MB**.
- A gallery step is therefore 22 % of the screen instead of 47 % — below the
  limit above which the display refresh is waited for. With "fast scrolling"
  on that saves another **12-16 ms per step** on the device. The limit itself
  is unchanged: a tear across cover and text would be visible, so the area
  was made smaller rather than the rule weaker.
- **Two bench defects fixed**, both in sections I wrote myself: section E
  died with an `IndexError` (it drew whichever page the previous section had
  left set) and its verdict was lost; section J measured the same thing three
  times on the game list because it did not select a category. And J now
  breaks the "rest" down: text, cards, description, housekeeping.

**The list view now copies only what changed, too.**

- A navigation step in the list changes two text rows on the left and the box
  art column on the right. Because a partial copy only knew about *rows*, it
  spanned everything in between — **86 % of the screen for two rows and one
  column** at 1080p. Both areas now go to the screen as rectangles:

  | | before | now |
  |---|---|---|
  | Game list, one step | 6.83 MB | **3.12 MB** |
  | Main page, one step | 5.89 MB | **1.30 MB** |

- The rectangles are only used when they cover **every row** of the previous
  strip; otherwise the old path stands. That check fired twice while building
  and each time prevented a leftover before it could appear.
- **Bench section J now measures the real step.** It used to call `draw()`,
  which for the list is the *full* rebuild — its light path is never called
  from there. The report therefore showed 132 ms for a step that does not
  exist in that form. Section B keeps its series (comparable since v4.2) and
  now says that it is the full rebuild.

**Filling areas in C — and a partial-update trap defused.**

- On the device "cards" was the largest named item of a scroll step:
  **47 ms** in the game list, 35 in the gallery, 28 on the main page — filled
  and rounded rectangles with shadows, all loops over screen rows. The large
  areas are now filled by `libdragend` (version 5).
- **Only from 256 rows up**, and that is measured: the jump into C costs
  something itself, and for small areas it costs more than the assignments it
  saves (700×900 gets 2x faster, 60×40 three times slower). The large cards
  are all above it, the many small frames below. New bench section I/3 shows
  both side by side.
- **An old `libdragend.so` no longer slows everything down.** Until now any
  version whose number did not match exactly was discarded — so updating only
  `frontend.py` meant *no* C at all, not even for scaling (a factor of 124 on
  the device). A range now applies: a version-4 library is still used fully,
  only the new function is missing.
- Way out, should it not pay off on your card:
  `touch /media/fat/frontend/flaechen_c_aus` — takes effect after a restart.
- **Bench corrections**: section J now bounces inside the visible window;
  otherwise half the steps ran as full rebuilds and the average was neither
  number. And section E finally compares like with like: the light path
  *without* the flip against blitting *without* the flip. Its "factor 2.9" in
  the last report came from counting a full-screen flip and the housekeeping
  on one side only.

**The frames — the item the area threshold missed.**

- A recording of *one* scroll step showed which areas still ran in Python
  after build 219, and they were almost all **frames**: the marker around a
  tile, the "no artwork" placeholder. Such a bar is 3 points wide and 771
  tall — a tiny area, and still 771 assignments. That is exactly what a
  threshold in *area* missed, just as the previous one in *rows* had missed
  wide flat areas.
- Now **two thresholds with OR**: many rows pay off, much area pays off, a
  little of both stays in Python. And a frame goes off as **one** call
  instead of four. Measured: 3×771 is 14× faster, a tile frame 14×, the
  placeholder frame 22×.
- Counted, not guessed — Python rows per scroll step at 1080p:

  | | before | now |
  |---|---|---|
  | Game list | 1557 | **9** |
  | Tile view | 740 | **0** |
  | Gallery | 1415 | **9** |

  On the device such a row costs about 0.009 ms, so the arithmetic says a
  good 13 ms per step in the list and 12 in the gallery. What actually
  arrives is for the bench to say, not me.
- **A rounded corner consists of two steps, not two hundred rows.** While
  measuring it turned out that the indent table of a rounding has only two
  distinct values: the 192 corner rows of the box-art card are really four
  rectangles. Vertically adjacent rows of equal width are now merged before
  they go into C — building that list had become more expensive than the
  drawing itself.
- One light scroll step on the development machine: **list 1.4–1.9×, gallery
  1.2–1.5×** faster; the tile view is within the noise here, but is the only
  one left with no Python row at all.

**The real brake: on the device, a jump into C costs a millisecond.**

- Both of these can be derived from the 29.09. report:

      C      = 1.00 ms + 0.0000057 × points
      Python = 0.25 ms + rows × (0.0080 + 0.000012 × width)

  Checked against all seven measured shapes. The first number is the
  important one: **one C call costs about a millisecond on the DE10-Nano**,
  and 0.007 on the development machine. A scroll step makes eight to
  fifteen of them — that adds up before anything is drawn.
- **Addresses and ctypes arrays are now reused.** Before every call the
  memory address was looked up again and the rectangle list written into a
  fresh C array — although it is always the same buffers, and while
  scrolling the same rectangles in the same places. Counted in the real
  draw path: 8 (list), 11 (tiles), 15 (gallery) address lookups and 2–5
  arrays per step, **all served from the cache, not a single miss**.
- **The threshold from build 220 was too low**, and the report showed it in
  black and white: `60x40 … 0.6x — used: yes`. An area that passed the
  threshold and is slower in C. The numbers now come from the device (96
  rows / 65536 points instead of 32/16384). That also keeps `853x21` in
  Python — the **row marker of the list**, twice per step, which was losing
  about 0.5 ms per call in C.
- **New in section J: `cover`.** REST sits at 38–79 ms per step and is the
  largest item everywhere. The cover lookup is now measured, including its
  accesses to the card (`os.stat`, `open`) — section G had already shown an
  `os.stat` costs 0.20 ms there. If REST stays large afterwards, the next
  item is still missing, and finding it is *the* job.
- None of this shows on the development machine (three runs: −3 % to
  +21 %, i.e. noise) — a jump costs 0.007 ms there. **The prediction is in
  the build and can be checked**: the `3x771` line in section I/3 is almost
  pure overhead and must drop, and `60x40` must now read "used: no". If it
  does not, the reasoning was wrong.

**And the corners are really round now.**

- The stop condition for the corner rounding had been inverted for a long
  time: it could only produce "fully indented" or "not at all", never
  anything in between. The cards therefore had **rectangular notches** cut
  out of their corners. It only surfaced when build 220 merged the corner
  rows — the table had just two steps.
- **It costs nothing**: the box-art card takes 0.304 instead of 0.322 ms,
  because the corner rows of a quarter circle are narrower on average than
  those of the notch. They still go off in a single C call.

**A game without cover art asked the card again on every scroll step.**

- The new item from build 221 showed it: in the game list, **20 accesses to
  the SD card per step, 13.44 ms** — right next to "cover 0.00". The
  accesses were slipping past the measurement, straight through REST.
- Reproduced and counted: an entry **without** cover art cost three
  accesses, and did so on every step again — even the tenth time on the
  same entry. Only a *hit* was ever remembered; a **no** never was, and
  with 30273 games not every one has cover art. On top of that, a second
  place asked about the very same file once more.
- Now the no is remembered just like the yes. Counted while scrolling up and
  down: **2.00 → 0.00 accesses per step**; walking forward through nothing
  but new entries, 3 → 2 (the duplicate is gone, the first one is still
  needed).
- **And the no does not stay.** While you scroll, the worker process is
  computing thumbnails onto the card — if our no about its file stayed, the
  cover would never appear. The moment you let go of the key it is dropped
  and one proper look is taken: once per release, not per step. Copy artwork
  onto the card while the frontend runs and you will see it after releasing
  the key instead of after a restart.
- **Section J now names the callers**: under the cover line it lists the
  three most frequent ones with their count per step. "Twenty accesses"
  alone does not say which.

**MiSTer's own fonts — as a second choice.**

- You wanted a different font, and your own objection was the better route:
  **MiSTer ships its OSD fonts**, and whatever sits on your card can now be
  picked here too. System menu → *Font*, right next to sharp/soft: Dragend's
  own (default), **"like the MiSTer OSD"** (reads `font=` from your
  MiSTer.ini), or any single file from `/media/fat/font`.
- **Not one font is shipped with this.** The font you linked is a
  digitisation of the German licence-plate typeface; the state never
  published a digital version, the files in circulation are re-creations
  with an unclear licence — and this package is public. So only what is
  already on *your* card is read. The same stance as with the foreign
  artwork database.
- The format fit without detours: a `.pf` is 768 bytes, 96 characters of 8
  bytes each starting at space — exactly our 8×8 table, only with the bit
  order reversed.
- **Your MiSTer.ini is only read**, never written. The test checks the file
  byte for byte afterwards.
- **Accented characters keep coming from Dragend's own font.** A `.pf` ends
  at "z"; if the rest came from there too, half the German titles would be
  question marks.
- Honestly: not every `.pf` is a text font. A few (tracker fonts, say) have
  symbols where the letters should be — you see it at once and move on.

**The update notice had been failing for nineteen builds.**

- Your log said `Build-Check fehlgeschlagen: Unterminated string` on every
  start, and your `update_check_state.json` listed **`2026-09-27-204`** as
  the last build you were told about. Together that was the diagnosis: the
  reply from GitHub was read with `read(2000)` — and the field holding the
  long build description has been several kilobytes since build 205. So
  2000 bytes were read **from the middle of a string**, and the result was
  no longer valid JSON.
- What made it nasty: the version check next to it kept working (the
  VERSION file is four bytes), and the log line looked like broken JSON
  rather than a limit set too low. The limit is now 256 kB, and on a read
  error the log names the length read **and** the limit.
- A test now checks the **actual file in the package** against the limit,
  with at least four times the headroom. That check was missing — it would
  have fired at build 205.

**And three repeat offenders in the draw path.**

- First, why they became visible at all: your device still had
  `/media/fat/frontend/profile` from an earlier debugging session, which
  runs a full cProfile around **every** page build. After deleting it the
  numbers halved: game list 97.7 → **47.2 ms** per step, main page gallery
  106.7 → **58.3**, main page list 68.3 → **28.9**. The bench now **warns in
  its header** when profiling is on, with the command to switch it off. A
  measuring instrument that hides its own state is a bad instrument.
- `_games_signature` was asking about the ROM folders **20.9 times per
  step**. It now throttles itself for eight seconds, regardless of whether
  the caller counts correctly.
- `eq_effect_enabled` read from the card once per step just to learn a
  setting nobody flips while scrolling. Now from the cache.
- The PERF log line wrote on **every** step, because a step sits above its
  20 ms threshold — and each line is a file access. It now appears at most
  once a second and says how many it swallowed.

**The main page gallery was the last blind spot.**

- It is the **only** view the rework in v4.7 never reached: every step
  pushed the **whole image** to the screen, 7.9 MB and 14.8 ms, while the
  game-list gallery next to it manages with 2.5 MB. The traces were being
  collected there all along — just never used. Now **3.92 instead of
  7.91 MB**.
- **And a tool that answers mechanically** the question I already got wrong
  once in v4.7: does the rectangle flip really cover everything that
  changed? It compares the *changed* pixels of a step against the *reported*
  rectangles; the difference is what stays on screen while the buffer looks
  correct. Back then that was 210,600 pixels, found by accident. Today: all
  six views, both resolutions, **zero uncovered pixels**.

**Cover art is now copied in C.**

- Covers and text strips needed a C function with **two** strides: a decoded
  cover sits tightly packed, the target has the screen's stride — the
  existing C copy only handles equal rasters. Both ran as a Python loop over
  the rows, and the report lists `blit` at 6–12 ms per step in **every**
  view.
- Measured on a single cover: gallery 0.31 → **0.06 ms** (4.8×), list 0.64 →
  **0.24 ms** (2.7×). It cannot be measured at step level here, and the
  reason is plain: the test rig has no cover art at all, so `blit` never
  runs there (counted: 0.0 calls per step). Your bench will tell.
- Text follows in the next build — it needs the same function but a change
  to the text cache, and that deserves care.

**The cut-out from build 234 never applied — three points too high.**

- `karten` stayed at 14.4 ms in your report after build 234, and that was no
  measurement error: the cut-out was rejected as soon as it stuck out of the
  card's straight middle rows by even one point — which in the list view is
  **always** the case (card at y=36, band from y=57, cover top at y=54).
- It is now **clipped instead of rejected**. Just as safe: what remains is a
  *subset* of what the caller promised would be painted over. On 1080p **76 %
  of the card** is skipped instead of 0 %.

**Section J now names the list view's boxart panel.**

- `cover` only hooked the grid/gallery path; in the list view the cover comes
  via `draw_art_panel()`, whose work sat nameless in `REST`. New post
  **`panel`** with its *own* share, subtracted from `REST`. Bench number 6.

**The gallery cleared a whole text column on every step — for a few lines of
text.**

- Your report lists `restore` on the main page/gallery at **12.99 ms**, the
  largest single item anywhere. A new measuring run says why: **1259×507
  points, every step** — the entire text column. On 1080p it is now
  **507 → 138 rows**.
- **The flip drops with it**, since the flip rectangles come from the
  clearing: **3.92 → 2.81 MB** per step (−28 %).
- **The coverage check caught me, rightly.** When the new caption is taller
  than the old one, its lower lines fell outside the cleared area — correct
  in the buffer, never on screen: **5184 uncovered points**. The region
  actually written is now recorded as a track by hand.

**The four visual touches — three new ones, one had been there all along.**

- **Scrollbar on the right**, **accent bars on the rows** (on every row, not
  just the selected one — the selected row's background already *is* the
  system colour), and a **hairline** between the list and the cover column.
- **Frame and shadow on the cover already exist** — since build 98 on the
  panel, since build 124 on the tiles. A second frame would just be a double
  frame; I pinned the existing one with a test instead.
- **Measured, as you asked** (`tools/diag_feinheiten.py`, each element on and
  off, interleaved, median run): **+0.04 to +0.06 ms** per scroll step in the
  list views, **nothing** in grid and gallery. Scrollbar and hairline hang on
  the *window*, not the cursor, so they are drawn only on a page build.
- **One switch for all three**: System menu → Display & Sound → Fine details.

**Your own background image — and it costs nothing while drawing.**

- System menu → Display & Sound → **Background image**. Its own page with
  folders, like masks and fonts. Put your `.png` or `.jpg` into
  **`/media/fat/frontend/backgrounds`**. It takes effect **as you move**, and
  left/right switches it on and off without losing your choice.
- **On the performance question: it costs nothing.** `fb.clear()` already
  copies a **full-screen template** — the "plain" background is not plain, it
  carries the vignette. What is in that template is irrelevant to the copy.
  Measured: **0.680 ms with a colour template, 0.667 ms with an image.** A
  test checks exactly this and goes red if it ever drifts.
- Cropped to **fill** (no bars), with a **darkening** in five steps — text on
  a photo is otherwise hard to read. That too is free: computed **once at
  load time**.
- **No image is shipped.**

**The list view with covers: three quarters of an area that was painted and
immediately painted over.**

- In your report `karten` is the largest item of a scroll step there, at
  **13.75 ms**, from only 5 calls. A new measuring run says why: **one card,
  769×945 points, in EVERY step** — with the cover landing right on top of it.
- The card now leaves that rectangle out, but only when the cover is already
  in memory, big enough, and going exactly there; otherwise it fills as
  before.
- **That the image stays identical is compared, not claimed**: 35 cases across
  five card sizes and seven cover aspect ratios, byte for byte. Here: 0.343 →
  **0.151 ms**.

**`--demo`: three minutes that show everything once.**

    python3 /media/fat/frontend/frontend.py --demo

- Nine stations: the main page in list, grid and gallery, then the biggest
  category in all three views — with covers — then the System menu, then a
  closing card. A short title card announces each station.
- **It runs the real frontend.** No separate drawing path: the same page
  builds, the same font, the same mask, your categories, your covers. Only
  the cursor moves, using the very step function the bench uses.
- **Any key aborts**, and afterwards everything is back where it was — page,
  category, entry, folder path, both views. Even when aborted mid-way.
- The length is **one number**: the stations share the total by weight.

**`--show`: the crash is gone, and it now also appears on the TV.**

- The crash: a category entry has **three** fields, I unpacked two. On the
  test bench the category list was **empty**, so the loop never ran and the
  test reported green. That was the real mistake — a test with an empty list
  does not test the loop.
- The report now also runs **on the TV**, page by page, in the current colour
  scheme. It advances on its own, any key skips ahead, back aborts.

**`--show`: the report, as opposed to the measuring instrument.**

- Five sections, built to be read out loud: your collection, what it can look
  like, what can be set (with the values in force right now), how fast it
  scrolls (ms per step and steps per second, per view), and where things live.
- **No hand-maintained feature list.** Such a list is quietly wrong after
  three builds. Everything comes from what the frontend already knows — the
  settings section is literally your System menu.
- **Measured with the same step function as the bench.** Two versions of the
  same scroll step would be two chances to drift apart. The report is also
  written to `/tmp/dragend_show.txt`.
- Also: `--help` no longer takes the single-instance lock.

**`--show` did not exist yet — now the frontend says so.**

- An unknown option used to be ignored silently and the frontend just
  started. It now reports the unknown option, prints the list of options it
  knows, and does **not** start. `--help` does the same without an error.

**Measured again: off the draw path was not enough — now it barely runs at all.**

- Your build-229 bench shows both sides. Good: REST in the gallery fell from
  **14.04 to 6.83 ms**. Bad: `cover 1.91 (davon Karte 19.68 in 22
  Zugriffen)`, against **2.83 ms** for the same accesses before — the work
  was not gone, it sat **next door** and competed for the same SD card.
- So: into the function instead of moving it again. The question is "has a
  folder **appeared**", and only the **names** are compared — yet it fetched
  a timestamp for every system folder under every base path. Around 630 file
  probes per pass, all thrown away.
- A new name can only appear if something changed at a **base path**. That is
  **13 probes instead of 630**, and the expensive pass only runs when
  something actually moved. Normally: not at all.

**Two stutters you reported — both found, both fixed.**

- Switching folders and categories could stall. Your report shows
  `20.9/Schritt _games_signature > getmtime`: roughly 630 file probes over 30
  steps, at 0.18 ms per warm `os.stat` — about **110 ms in a single step**.
  It is the ROM-folder fingerprint used to notice a late-mounted USB drive.
  It is postponed while a key is **held**, so it ran exactly when you stop
  scrolling or change category. It now runs **on its own thread**; the draw
  path gets the last known answer, at most eight seconds old.
- Entries without boxart appeared late or looked recomputed. The remembered
  "nothing there" from build 222 was thrown away at **every** standstill — so
  every time you stop, which is exactly when you look. It now lasts **up to
  30 seconds**. New artwork copied onto the card shows up within half a
  minute, and the worker still clears its own entry **immediately** when it
  finishes a thumbnail.

**The font gets the same page as the shadow mask — and the mask gets
MiSTer's four modes.**

- **Font**: System menu → *Font* now opens its own page with **folders**,
  just like the masks. At the top: the frontend's own font and "as in the
  OSD" (the one from your MiSTer.ini); below that the folder tree from
  `/media/fat/font`. The font switches **as you move** — title, list and a
  sample line (`0O 1lI 8B 5S …`) already appear in the font the bar is on.
  The old left/right cycling is gone.
- **The four mask modes**: `1x`, `2x`, `1x rotated`, `2x rotated` — the same
  four as in MiSTer's OSD. Its own line at the top of the mask page,
  left/right cycles, and the preview beside it shows the difference at once.
  At 1080p a 1× mask is so fine you can barely see it; **2× is usually what
  you want**. "Rotated" tips the pattern by 90°.
- **It costs nothing while drawing.** Both are transformations of the
  pattern table **at load time**, not per pixel. A 16×16 mask becomes 32×32
  at 2×; the C side takes up to 64×64.
- Under the hood, folder browsing now lives in **one** place
  (`fe/dateibaum.py`) and is used by both.

**The text drawer now runs in C.**

- The last big item from the 02.10. report: `text` at 15.57 ms per scroll
  step in the gallery, 31 % of the whole step. Several lines now go to C as
  **one bundle** instead of eight separate Python loops — the data lines
  under the cover and the description are the two callers.
- **The threshold is computed from device numbers**, not guessed: a C call
  costs about 1 ms on the DE10-Nano (build 221), building a strip about 3 ms
  for 1248×16 points. Break-even at ~5700 points, chosen 6000. On a CRT
  almost everything stays in Python, and rightly so — the strips are small
  there.
- **New: a text is only remembered on its second appearance.** While
  scrolling, every title occurs exactly once; menu entries and headers come
  back with every frame. Before, the one-offs evicted exactly the entries
  that would have been hit.
- What arrives on the device is for your bench to say. What is proven is
  correctness: the same text drawn both ways and compared byte for byte
  across ASCII and Latin-1, every size, and the edges.

**The shadow masks are now browsed by folder — and MiSTer's presets are in there.**

- You were right: a list of 1207 lines is not a choice. The page now shows
  **the folder structure the collection itself uses** — up/down selects,
  **OK opens a folder or takes a mask**, back goes **one level up** and only
  leaves the page at the root. Each folder says how many masks are inside,
  the path is shown under the title, and going back puts the cursor on the
  folder you came from. Folders without a single mask are left out.
- Opening the page starts you **where your current mask lives**, not at the
  top again.
- **There really was something for us in `/media/fat/Presets`.** A preset is
  a tiny INI holding a whole set of video settings, and one of its lines is
  `mask=` — naming exactly one file from your `Shadow_Masks`. So the top of
  the list now offers **MiSTer presets (recommended)**: ready-made, named
  suggestions by people who know these masks. Presets without a mask, or
  whose mask is not on the card, are dropped.
- **`/media/fat/Filters` cannot be used**, and that is not laziness: those
  are coefficients for MiSTer's **scaler** (four taps, sixteen phases,
  −128…128). They only mean something while an image is being *scaled*.
  Dragend paints straight at the screen's own resolution — there is no
  scaling stage of ours to feed them into. Scanlines in Dragend are simply a
  1×2 mask, and the collection already has those.

**MiSTer's shadow masks now sit on Dragend's own picture.**

- System menu → **Shadow mask**. Its own page, because MiSTer's collection
  holds over a thousand of them — stepping through that with left/right
  would be a punishment, not a choice. Up/down selects, **left/right turns
  the effect on and off without losing your selection**, OK keeps it.
- The mask takes effect **immediately on that page**, with a grey ramp and
  three colour bars as a preview. Picking a mask by filename and only then
  seeing it would be guesswork.
- **Not one is shipped.** Only what sits in `/media/fat/Shadow_Masks` is
  read — MiSTer's own collection, on your card. A test walks the whole
  package and reports any mask file that sneaks in.
- Reading them held a surprise: one file can contain **several patterns** for
  different screen heights. The first attempt knew only the first one and
  discarded 106 of 1207 files — precisely the elaborate ones (Sony PVM,
  Commodore 1084). Now **1207 of 1207** are read.
- **What it costs is stated here and measured.** The first attempt multiplied
  per pixel — a factor of nine over a plain copy. With a lookup table instead
  of multiplication, and a separate path for uniform pattern rows (with
  scanlines every second row is neutral, i.e. an ordinary copy), a scroll
  step costs **+0.7 to +1.6 ms** here with a fine pattern and **+0.2 to
  +0.4 ms** with scanlines. On the DE10-Nano per-pixel work is dearer —
  that is what the switch is for.

**Mixed categories no longer stall when you enter them.**

- The report was unusually precise, because it named five categories and no
  sixth: Continue Playing, RA Achievement Hunter, Collection, Discovered in
  2026, Short Games. **No** system folder — even though with 30278 games
  those are the larger ones. So it could not be the number of entries.
- What sets those five apart is a single property: their entries come from
  **different systems**. And the two name indexes a cover is found through
  are built **per system** — for a mixed category that means all of them in
  the one moment the page is first drawn. Counted in the grid view: one
  system = **1** directory pass, twelve systems = **10**. On the DE10-Nano a
  pass over a cover folder costs roughly 167 ms. That was the wait, and it
  was not in the drawing.
- Now the work happens **while nothing is going on**: as long as the cursor
  rests on a category, **one** system is prepared per idle tick. After that
  pause, entering costs **zero** passes — measured in grid and gallery view;
  the list view never had the problem (there exactly one cover hangs on the
  panel, so exactly one system).
- **One system per idle moment, not a background thread that walks them all.**
  Building an index is only partly waiting on the card; the rest is a loop
  over every file name, and that holds the GIL throughout. Build 107 already
  got caught by exactly that ("why is the main menu so sluggish after a
  restart?"). The warm-up stops the moment a key arrives.
- **Honestly:** enter a mixed category *immediately*, without resting on it,
  and you still wait — just no longer for every system. Pick it out, and you
  do not wait at all.

**Demo mode now actually shows something.**

- The report: "jiggles around in the first three rows in list view, the
  system menu and settings are not shown at all, then it just opens Random
  Play and stops there". Each point had its own cause, and two were the same
  mistake.
- **The jiggle in the first three rows**: how many rows fit the window is
  decided **while** drawing. The demo asked **before** anything had been
  drawn in the new view, and got the initial value 5 — a window of three
  rows. Now it draws first and asks after: 13 rows instead of 3.
- **The system menu**: the stop sat on the top level, which has little to
  show when there are few entries. It now descends into the fullest
  subfolder when that holds at least four entries.

**Background images appear immediately now.**

- Reported: "when I put several background images in the folder and click
  through them it always takes very long until one shows. **are they still
  being prepared? and every time anew?**" — both questions were the right
  ones to ask.
- The path was taken apart, and **a single item was 90 to 98 percent of it**:
  the dimming. Scaling 0–26 ms, cropping 2–5 ms, **dimming 214–233 ms**. And
  it was not the idea but the spelling — a **Python loop over every byte**,
  8.3 million of them at 1920×1080. The same work done in C: **14.6 times
  faster, bit-for-bit the same picture** (214 → 15 ms). On the MiSTer
  per-pixel work is dearer still; that is where the seconds were.
- **What was NOT shipped, although it was finished:** storing the prepared
  templates on the card — the suggestion in the report itself. It was built,
  with twelve passing tests. Then came the measurement: **the warm path cost
  more than the cold one** (decoding a 1080p JPEG takes 33.9 ms, re-reading
  the PNG 19.0 ms). So it came out again **before** it shipped. Instead the
  **per-part timings now go to the log**, one line per image change: after the
  change the largest item is decoding, and that depends on the format and the
  card — the number from the device decides whether anything else is needed.

**The demo is now about the settings.**

- Reported: "at the end I still see Random Play instead of a few settings
  being shown there under the category. I think that's bad!"
- **The cause was last build's heuristic.** The stop descended into the
  subfolder with the *most content*. On the test bench that is "Display &
  sound" with 27 entries — which is why the test passed. On a real card
  **Scripts and the standalone cores** count too, and 45 scripts beat 27
  settings. The demo was showing script names.
- **Five settings groups are now named explicitly** — Display & sound,
  Options, Statistics & achievements, Input & language, Maintenance — each
  with a title card saying what you can do there. If a group is missing on the
  device its stop is **skipped**; nothing is substituted. A demo that shows
  something other than what it announced is worse than one that leaves a stop
  out.
- **The time is redistributed**, exactly as asked: views from 7.8 down to
  **4.6**, settings from 1.4 up to **6.2**.
- **Every stop logs what it actually shows** (page, view, category, entry
  count, folder path). Twice in a row the demo showed something other than
  announced, and both times that was not determinable from outside — it
  depended on things that are only that way on the owner's device. One line
  per stop answers it in the next report.
- And a **correction to the last build**: "just opens Random Play" was
  attributed there to attract mode. That was wrong — `--demo` quits the
  frontend right after the demo, so the idle branch never runs again. That
  line stays as a tidy-up and is now labelled as one.

**Scrolling with covers: three fill calls fewer per step.**

- Asked: "when I go into the arcade folder with cover switching on and hold
  down to scroll, is there anything left to gain in display time or speed?"
- **The test bench was blind here.** It has no cover files — so `art` stays
  empty and the frame around the cover is never drawn. Four separate calls
  that happen on the MiSTer in *every* step appeared in no measurement. The
  diagnostic now **slips a cover in**, so the same path runs as on the device.
- The frame is now **one** call instead of four: in list view **8 → 5** fill
  calls per step. That this helps is in the owner's own bench, section I.3: a
  60×40 area costs 0.489 ms in C, a 697×3 one 0.318 ms — both *tiny* areas.
  That is not the area, that is the call. Three calls fewer are roughly
  **1.2 ms per step** on the device. What gets drawn is bit-for-bit identical,
  checked byte by byte across five geometries.
- It is exactly the move from Build 220 — which batched the tile frame and the
  *placeholder* frame. The frame around the *actual* cover was missed and has
  been running four-part ever since.

**The bench gains a section K — and loses two reporting bugs.**

- **What is not explained yet now says so.** By the cost model `karten` in
  list view should cost about 3 ms; the report says 13.81. Ten milliseconds
  with no name, every step — and not reproducible on the development machine,
  where the same step takes 1.4 ms instead of 39. So section K measures **on
  the device**, with a cover slipped in, reporting per view the number of calls
  and the **ms per call**.
- **`(davon Karte 3.35 in 0 Zugriffen)`** was not a contradiction in the
  frontend but `%d` applied to 0.7. It now prints a decimal.
- **`0.6/step _basen_merkmal > getmtime`** looked like an item. 0.6 accesses ×
  0.18 ms is **0.1 ms per step** — a single pass over the game roots spread
  across 30 steps, so Build 229's self-throttle does hold. **Nothing to fix
  here**, and without the time next to it that was not visible. Those lines
  now carry the time and are sorted by it.

**Three things the first report with section K said about the bench itself —
two of them my own mistakes.**

- **Section K ran into nothing, silently.** The report said "no image cache —
  skipped": the function that supplies the cover lives on the image cache
  itself, while the bench is deliberately handed the module. The whole section
  bailed out — with a line that reads like a device property rather than a
  programming error. Both cases are now handled.
- **The `karten` item got smaller because I looked away.** Build 241 merged
  four calls into one; `karten` fell from 13.81 to 13.02 ms — but the new call
  was in **no** counter. So part of the saving was not a saving but blindness.
  *An item that shrinks because you stop looking is worse than a large one.*
- **Section E reversed its verdict.** Two runs, same device, two days apart:
  once "marginally better (7.9 ms)", once "not worth it". Nothing had changed —
  both sides vary by about 15 percent and the threshold was sharp. Now the two
  sides are measured **alternately**, the median is taken across several
  rounds, and the **spread is printed**; if the difference is not larger than
  it, the section says "TOO CLOSE" instead of ruling. That is the honest
  answer and the more useful one: what lies in the noise, nobody notices while
  scrolling.

**And a real gap: what is the cold case made of?**

- `game list, list view, per step cold 296.82 ms` is the largest single value
  in the whole report, and what it consists of was written nowhere. Adding up
  two other sections got me to 180 ms — the remaining **116 were guesswork**.
  Whether the next piece of work belongs at the decoder or the scaler depends
  on it.
- Section B now **takes the cold pass apart itself**, on the device's real
  files at its real box sizes: decoding, scaling, remainder — each with its
  call count. The counters are released immediately afterwards; left in place,
  every following section would measure through them, and that would be a
  measurement error that looks like a finding.

**Four cosmetic additions — and what each costs is stated.**

All four sit behind the **fine-details switch** (System → Display & sound).

- **The system colour in the fine elements**: the scrollbar's runner and the
  hairline between list and cover column now take the system's tone, muted
  rather than pure. This **costs nothing** — it is a colour, and those
  elements are drawn anyway.
- **A thin accent rule under the header**, in the same colour: it tells you at
  a glance which system you are in. Costs **once per page build** and nothing
  per scroll step.
- **Rounded cover corners**: frame and cover get one shared rounding. Measured
  as **one** fill call with 16 rectangles, roughly **0.71 ms** on the MiSTer —
  and only when a cover is present; during fast scrolling the box art is
  skipped anyway. In all three views the difference is within the noise.
- **The initial letter while fast-scrolling**, large in the cover column. With
  1041 entries in Arcade it tells you where you are — and it sits exactly
  where the card is **already blank** while scrolling: no extra clearing, no
  extra flip. On release the real cover is drawn over it.

**Scrolling with covers: the card now spares the cover box.**

- Section K delivered what it was built for — the largest single item of a
  scroll step, with a name and a number: **the cover card, 8.295 ms**, out of
  a 39.42 ms step.
- **What was happening:** hold the key down with "covers immediately" on and
  the cover is skipped — yet the card was refilled completely **every step**,
  while the cover box looked exactly as it did the step before: same empty
  box, same initial letter. Only the **text** below changes.
- The card is now still drawn — corners, shadow, border, text area — but the
  **area of the cover box is spared**. The mechanism for that has existed
  since Build 234/238. Measured: filled bytes **2.71 → 0.66 MB**. By the
  bench's cost model that is **6.73 → 2.89 ms** per step on the MiSTer.
- It only applies **without** a cover: with one, the picture changes every
  step anyway, so there is nothing to save.

**And something that was finished and faster — and still is not shipped.**

- The first attempt dropped the card **entirely** and painted only the text
  block. It measured better: filled 2.71 → 0.44 MB, flipped 3.62 → **1.13
  MB**. It also required rebuilding the flip (separate bands instead of one
  span) and a report back from the panel. All of it was finished and passing.
- **Then a byte-exact test convicted it:** 69 bytes of difference between
  buffer and screen, at the card's bottom-right corner — a triangle of 17
  pixels. The surroundings of the corner rounding are *not* filled by the
  card; without the card call, whatever the previous step left stayed there.
  Exactly the kind of remnant this project has chased five times.
- Sparing the box is the smaller but **explicable** gain. The flip rebuild has
  been **removed again** — it was built for a design that no longer exists, and
  unused machinery in the flip path is precisely where you do not want it.
- **One bug caught before shipping:** the cover's identity was first keyed on
  a memory address. Python reuses the address of a collected object — two
  different covers of the same size would have shared an identity, and the
  previous game's cover would have stayed on screen. The path decides now.

**The report did not see the last build — and that was the finding.**

- After Build 244 another `--bench` ran on the device. `karte_mit_schatten`
  came in at **8.840 ms** — marginally *above* the 8.295 ms before it, even
  though the same step measures 2.71 → **0.66 MB** of filled bytes on the PC.
- **The cause is the test bench, not the build.** The section that counts fill
  calls slips a cover in on *every* call — and Build 244's spared area applies
  only when there is **none**. So the same path was measured twice, and the
  difference was noise. The same pattern as twice before: **the test bench is
  blind where it has no covers.**
- Each view now runs **twice**: once with a cover, once with the cover
  skipped — the way it behaves when scrolling fast. The check does not depend
  on any clock: if the sparing applies, the card counts about **174,000**
  filled points; if it does not, about **678,000**.

**Three numbers the report could not give before.**

- **The largest item now stands next to what its area explains.** For the
  cover card that is 2,587 rows and 0.70 MB — barely 3 ms by the device's cost
  model, 8.84 ms measured. **The gap is larger than everything Build 244 took
  out**, and it is written down before anyone optimises it away.
- **The row highlight** (`853x39`, 2.146 ms in *every* step) sits below both
  thresholds for moving a fill into C, so it stays in Python. That decision
  was never measured: 2,400 points (equally fast) and 16,384 (C clearly
  better, but for a different reason) were known. Nothing in between. The real
  callers' dimensions are measured now, and the threshold gets set **after**
  that.
- **The cold case** stood at 309 ms — 89 decoding, 47 scaling, and **173.6 ms
  "rest"**, more than the two named parts together. Thumbnails being packed
  and written in a thread *per cover* while drawing continues alongside
  explains exactly that kind of rest. Both are counted and reported
  separately now — the writing explicitly **not** subtracted, because it runs
  in parallel.

This build makes no draw path faster. It makes three places measurable where
guessing was the only option.

**The memory peak on rescan: 55 → 24 MB at 50,000 games.**

- This had been measured for a while and never acted on: at rest a game costs
  about **500 bytes** — 50,000 ROMs are 24 MB, nothing on a 1 GB device. On a
  **rescan** it was **1158 bytes per game**, because the old tree was still in
  memory while the new one was being built, with the pickle write buffer on
  top.
- **Two changes, both small:** the old tree is released *before* the new one
  is built (36 %), and the cache is written **per system** instead of in one
  piece (together **57 %**).

| 50,000 games | peak | per entry |
|---|---|---|
| before | 55.2 MB | 1158 B |
| release only | 35.6 MB | 746 B |
| **plus per-system writing** | **23.8 MB** | **498 B** |

- Extrapolated: at 250,000 games **124 instead of 290 MB**. That moves the
  ceiling for the largest conceivable collection, and it moves it where the
  ceiling actually was — not at rest, but at the peak.
- The cache file can now read **individual systems**. On an incremental rescan
  only the **unchanged** systems are read from the file; the changed ones have
  just been read from disk and need not be held twice.
- **Your existing cache file is still read.** Without that fallback everyone
  would get one full scan after the update — minutes at 30,000 games, for
  nothing. The first write converts it.

**And something uncomfortable that surfaced on the way.**

- The function that builds the **entire game list** was **half-converted and
  broken**: three cache helpers were called but never written. The first call
  would have raised a `NameError` — a frontend with no game list.
- It was never shipped (`fe/scan.py` has not been in a ZIP since Build 230),
  so neither your device nor your repo was ever affected. But **nobody caught
  it**, and that is the real finding: **not one test had ever called
  `scan_games()`.** The suite's 124 checks walked straight past the most
  central function in the program.
- So the first check in the new test file is the cheapest one: *does it run at
  all?* Then round-trip, partial reads, the old file format, five kinds of
  corrupted file, and an aborted write — which must leave neither a `.tmp`
  corpse nor half a cache file.

**The draw actually runs now — Build 246 was broken, by a single line.**

Reported: “I don't hear the sound in random pick" and “the titles don't spin
like a wheel either". **Both were the same bug.** The draw painted one frame
and then *stood still* until a button was pressed — at which point it ended
as “skipped", and the sound with it. Cause: `read_action()` is **blocking
without a timeout**; it waits for the next input, however long that takes. I
called it without one inside the wait loop.

- It now **waits and listens in one call** — `read_action` with the frame's
  remaining time as its timeout. The wheel spins, and a button still skips.
- Plus a **0.35 s button lockout** at the start: you reach this screen by
  pressing OK, and that same press is still there on the first look at the
  input queue. Without the lockout it ended the draw immediately.
- **The test bench could not see this**, because the test had replaced
  `read_action` with a non-blocking stand-in. That stand-in now raises when
  called without a timeout — the same bug cannot come back without turning a
  test red.
- **And a second, independent reason for silence:** I had also tied the draw
  sound to the “navigation sounds" switch. Anyone who turns the scroll clicks
  off — and many do — had a silent draw. That was my own addition and wrong:
  there is now **one** switch for the whole feature, the suspense duration.
- `_play_ducked_sfx` used to return **silently** when no sound file existed.
  Now it logs a line naming both paths it looked for. Plus a probe that walks
  the whole chain and plays once at the end:
  `python3 /media/fat/frontend/sound_probe.py`.

**Writing thumbnails was occupying both cores.**

- Section B of the bench says it in one line: **590 ms of packing and writing
  per scroll step**, with the step itself at 294 ms. Over 60 steps that is 35
  seconds of background work inside 18 seconds of measured time — on a device
  with **two** cores. That explains the unnamed “rest" of 156.9 ms: it is the
  CPU time the draw loop is missing.
- The cause was **one thread per cover**. The comment in the source argued it
  “only happens on a real cache miss, not on every scroll step" — the number
  refutes that: **44 writes in 60 steps.**
- There is now **one queue and one worker thread**. Writing occupies at most
  one core and leaves the other to drawing. The queue is bounded by **bytes**
  (24 MB), and on overflow the **oldest** entry is dropped — permissible,
  because the disk cache is pure optimisation: a dropped entry only means that
  cover is recomputed next time you scroll past it.
- “Prepare thumbnails" does **not** go through the queue; it still writes
  directly and synchronously. Nothing may be dropped there — that is the whole
  point of the run.

**The rounded corners were the unexplained rest.**

- Section K reported about **5 ms** per card call that the area does not
  explain — and **independently of the card size** (list 5.40 ms, gallery
  4.93 ms, at three times the area difference). A fixed price per call, then,
  not an area problem.
- The trail was in the same report: the same dimensions cost 2.036 ms as
  `rect_rounded` and only 0.860 as `rect` — **the rounding alone is 1.18 ms.**
  One card call collects about 21 narrow strips for the four corners, and all
  of them ran in Python: 33 rows, a few thousand points — below **both**
  thresholds for moving a fill into C.
- There is now a **third threshold: the number of rectangles.** Measured, not
  guessed — section I.3 has said since Build 220: “frame of 4 bars: Python
  6.441 ms, C 0.764 ms, 8.4x". Four strips, none of which reaches a threshold
  on its own, and C is eight times faster. From four rectangles a bundle goes
  to C. Measured on the test bench: **21 Python strips per card call → zero.**

**The short path only applied in one third of the steps.**

- The control number from Build 245 delivered on its first run: 531,383
  filled points, where 174,240 (applies) or 710,410 (does not) were the
  expected values. Computed over points **and** rows, independently the same:
  **33.4 % and 33.3 %.**
- The cause was the **initial letter**: it was part of the comparison, and in
  a real arcade list it changes often (“1942", “1943", “Aero Fighters",
  “Alien Syndrome"). On the test bench every entry was called “Spiel
  000…059" — always the same letter, which is why the measurement looked
  perfect. **The same blindness as before, one level up: the test data were
  too uniform.**
- The letter is no longer part of the comparison — it is **drawn along** on
  the short path. It may be, because text with a background colour paints its
  own cell, and that cell is the same for every letter. Cost: **one character**
  instead of the whole card.
- Measured in the hardest case (letter changes in *every* step): filled bytes
  **2.86 → 0.82 MB**, the same value as with an unchanging letter. The short
  path now applies in every step.

**Random pick: the draw now runs, with sound.**

- While drawing, the titles spin across the screen like a **wheel** — slowing
  down as they go — with a **draw sound** playing. Then the three games
  appear. Adjustable under *System → Behaviour & options → “Draw
  suspense”*: `off / 1.0s / 2.0s / 3.0s / 5.0s`, default 2 seconds.
- **Why that is a setting and not a fixed value:** the draw itself takes no
  time — taking three games out of a shuffled list is a list operation. Only
  the three covers cost anything, and with a warm cache they are there in
  milliseconds. A sound “until the games appear” would have been cut off in a
  blink. The suspense phase is therefore **deliberate waiting** — and `off`
  restores exactly the previous behaviour.
- The covers are loaded **during** the phase, not after it. So it only costs
  whatever exceeds the loading time.
- **Any button skips** the draw — and is consumed doing so, so a held OK
  button does not immediately launch a game.
- The sound comes from `sfx/zufall_ziehung.mp3` and can be replaced by your
  own MP3 under the same name. Without the file the frontend generates a
  substitute — the draw is never silent. With “navigation sounds” off it runs
  without sound.

**Two things that surfaced while building it.**

- **The sound would have played into the selection screen.** The MP3 is 7.9
  seconds long, the phase lasts one to five. The existing paths always play a
  sound **to the end** — there was no way to stop one at all. Now there is, and
  it has to handle being cancelled **before** the sound has even started: it
  runs in its own thread, and with warm covers the draw is regularly over
  before the player process is up. Without that, the sound starts exactly when
  it should stop.
- **A loop no button leads out of.** The draw runs until the clock runs out.
  If the clock stood still, it would run forever. The test bench found that,
  because there the clock **does** stand still — the test ran for ten minutes
  before it was killed. There is now an upper bound on the number of frames.

**There is no watermark — and the reason belongs here.**

The wish was the system logo subtly *behind the list*. That is where the
background lives, and the scroll path restores it from its row cache — so a
logo would have to be **inside** the full-screen template, one per category,
**8.3 MB each**. Build 235 removed exactly that cost. The system logo also
already exists where there is room for it: on the category page, next to the
list. The accent rule up top stands in its place.

**And a finding about my own tooling.**

The accent rule took **three attempts**, and each looked right on inspection:
once it sat inside the first list row's band (2617 differing pixels), once it
sat correctly but *moved*, because the list position depends on the selected
entry (2737), once it fit at 1080p and sat two pixels too low at 320×240
(160). All three were found by the same tool that compares every light draw
path against a full rebuild. **It also turned out that the scrollbar runner
has the same property** — with the old grey colour that never showed. It is
now checked at all four resolutions.
- **"then it just opens Random Play and stops there"** was not a fault of the
  demo but its **consequence** — the most surprising find of this build.
  Attract mode is called "Random Play — draw a game" in the menu and starts
  after 90 idle seconds by default. The demo runs for 180 seconds with a loop
  of its own: the input clock was three minutes stale afterwards, and the
  **first** idle tick after the demo met the condition at once. The clock is
  now refreshed at the end — in one place, which also runs when a key aborts
  the demo.

**And something uncomfortable about my own work.**

- The test suite had been running **without the C library** all along — on a
  path the MiSTer never takes. The shipped `libdragend.so` is the ARM build
  for the device and does not load on a PC at all. **Four tests** were
  failing because of it with nothing wrong in the frontend, and they even
  said so verbatim ("without it this test checks nothing") — nobody read the
  line as a finding. The harness now picks the build matching the
  architecture. **This changes nothing in the frontend** and is listed only
  because the previous build shipped with four failing tests.






---

## v4.7 — the login prompt, large tiles, and what measurements disproved

Eighteen builds since v4.6. What you notice, in four lines:

- The **login prompt** that kept appearing since kernel 6.18 is found and
  gone — the guard had been looking at eight single pixels instead of whole
  rows.
- The **grid view** now shows large box art: ten tiles of 270×361 instead
  of twenty-one of 176×235.
- **Quitting the frontend** no longer lands blindly on the console; it
  hands over through MiSTer's own command channel — and tells you what to
  do if even that fails.
- **Faster** in several places, every one of them measured on real
  hardware: partial frames by a factor of 3.3, JPEG thumbnails, two
  computations moved to C.

And one line of self-criticism, because it belongs here: several of these
builds fixed faults I had introduced myself, by measuring on the
development machine instead of on the MiSTer. The differences there are not
nuances — reading the MiSTer's framebuffer is roughly a hundred times more
expensive than ordinary RAM. The bench (`--bench`) now measures exactly
those places.

**Important after updating:** run "prepare thumbnails" once. The large grid
tiles have a new size, and without it the grid will load covers as you
first page through.


**MiSTer's command table solves two old riddles at once.**

It is in the program on the card, so what MiSTer accepts on its command
channel is finally established: `fb_cmd`, `video_mode`, `load_core`,
`screenshot`, `scaled`, `volume`, `mute`, `unmute`. **There is no `menu`
command** — the OSD cannot be opened this way at all, which explains why
the "open OSD" menu entry could never be reliable on this device. But
`load_core` exists, and with it the menu core can be loaded — *that* is
MiSTer's menu. It is how the frontend has long returned from a running
game; not a new mechanism, just the existing one in a second place.

**Quitting now tries that route.** The exit log showed three injected F12s
and MiSTer at 6–7 % each time — the injection does not arrive, while F12 on
the keyboard does open the menu. So after the three F12 attempts the menu
core is loaded and MiSTer's load is checked. If the menu arrives, done; if
not, the console hint from Build 210 remains.

Deliberately an *attempt*, not a solution announced: whether `load_core`
also fetches the menu when no game is running has not been measured yet — I
had already claimed it, relying on an answer that referred to something
else. It cannot be worse than before, and the log lines will say which case
it was.

**And "open OSD" can no longer freeze.** Reported: "the music stops and the
frontend picture stays put, no OSD appears, then I pressed every key one
after another and suddenly the OSD opens."

There was a `while True` with **no timeout at all**. If the injected F12
does not arrive there is no OSD — and the process waits forever for a
return key, with music paused and the picture frozen. The "suddenly" was
the first key that happens to count as a return. Now it checks *first*
whether the OSD arrived at all: if not, the frontend is back immediately and
says that F12 on the keyboard helps. And the wait loop itself has a
timeout, so nobody gets stuck even without a load signal.

**The large grid tiles are now the default** — adopted for good on request.
At 1080p that is 10 tiles of 270×361, 79 % of the gallery size. Back to the
old 7×3 grid with `touch /media/fat/frontend/raster_klein`. Run "prepare
thumbnails" once after switching.

---

**I measured on the wrong machine — corrected here, and the bench now
measures it on the device.**

Build 209 moved the picture guard from eight pixels to twenty whole rows. I
established the cost on the development machine: 0.013 ms for 150 kB. The
profile run on the real device then showed **2 milliseconds per look**,
twice per scroll step. The difference is not the CPU but *which memory*: on
the PC that is an array in ordinary RAM, on the device it is the
framebuffer — uncached, across the bus, and worse to read than to write.

The remedy, without giving up detection: only four of the twenty probes are
inspected per look, round-robin. Every probe comes up after five looks —
several times a second while scrolling, and the login greeting stays until
something wipes it. 150 kB per look becomes 30 kB.

So this cannot repeat, there is now **bench section F**: it reads the same
number of bytes once from RAM and once from the framebuffer, states the
factor between them, and then the cost of a real guard look. The number I
got wrong now comes from the device.

**The grid can show large tiles.** The request was "the box art size like
the large ones in the gallery, maybe eight on a screen". Worked out: the
grid area at 1080p is 1652×741 points, and only *one* row of 342×456 fits
in it. With two rows the tile becomes 270×361 — 79 % of the gallery size —
and ten of those fit:

```
small   7x3 = 21 tiles,  cover 176x235
large   5x2 = 10 tiles,  cover 270x361      (gallery: 342x456)
```

So ten rather than the hoped-for eight. It is computed the way portrait has
been since Build 176: the tile *size* is fixed, not the *count*. On 720p it
becomes 180×241, on a CRT 53×71, portrait 298×397.

The price, named honestly: 270×361 is a new box size, and the thumbnail
store keys on size. Run "prepare thumbnails" once after switching it on.
Off by default:

```
touch /media/fat/frontend/raster_gross     # on
rm    /media/fat/frontend/raster_gross     # off
```

**The gallery-from-grid-tile experiment is gone** — verdict at the TV:
"looks bad". Upscaler and all branches with it; a dead switch is worse than
none.

**For quitting, the cause is now established.** Three injected F12s, MiSTer
at 6–7 % load each time, "the OSD did NOT arrive" three times. So the
instrument from Build 166 works correctly — what fails is the *injection*,
while F12 on the keyboard does open the menu. The proper fix goes through
MiSTer's own command channel, whose formats are now known; which one
fetches the menu is not yet established, so it is not built. What this
build does: the dead end becomes an instruction. If the handover finally
fails, the console says to press F12.

---

**The picture guard never found the login prompt, because it was looking
at eight single pixels.**

That is the whole explanation for a nuisance that ran from Build 198 to
208. The guard has compared correctly since Build 198 — against what we
last wrote ourselves, which is why it has no false alarms. It just looked
at *eight pixels*. A picture switched away entirely it finds at once (15
of 15 probes were foreign on the user's device). But real text is made of
thin strokes, and the chance that one of eight points lands on one is
almost nil.

The probes are now **whole rows**: up to row 96 every eight rows — a
console text line is sixteen pixels tall and can no longer slip through —
and spread over the full height below that. Instead of 32 bytes it now
inspects 150 kB, 4800 times as much picture, and one look costs a measured
0.013 ms. The test makes the case with 200 prompts at random positions:

```
found out of 200 prompts:  row guard 200,  eight points 0
```

**One wrong turn is documented rather than hidden.** I first moved the
guard into C — 150 kB per look looks expensive. The measurement says
otherwise: 0.0158 ms in C against 0.0126 ms in Python. Python is even
marginally faster, because a slice comparison on a byte array *already is*
a `memcmp`; the Python overhead is per probe, not per byte. So the C part
came back out, bindings and fallback with it — the guard now has one
implementation that cannot drift. The numbers are in the source so nobody
"optimises" it again.

**What did belong in C** are the two places Python has to touch per
*pixel* and per *row*:

| | before | now | |
|---|---|---|---|
| Counting foreign output | 0.813 ms | 0.027 ms | 31× |
| Clearing an area (340×792) | 0.276 ms | 0.070 ms | 7× |

The counting has been running mid-scroll since Build 208 — 48 rows by 512
columns is 24576 comparisons. The clearing is the item that showed up in
the log as `bg=11` out of 85 ms per scroll step. Both keep their Python
version as a fallback and as a bit-exact reference in the test.

`libdragend` is therefore version 4. An old file reports 3, is rejected
with a log line, and the work is done in Python — so a half-applied update
breaks nothing, it only gets slower.

---

**The login prompt while holding a key: the watch was never running at
exactly that moment.**

Reported: "the login prompt pops up again when I scroll down in the list
view with the key held."

The cause has been half-written in our own comment since Build 199: the
main loop's idle branch is skipped while input is pending. So while a key
is *held*, everything built against the prompt was absent. Build 199 moved
only **one** remedy onto the per-action path — rewriting the topmost rows.
And that is not enough: the login process's greeting is taller than those
rows. The watch that detects the prompt *anywhere* on screen stayed in the
idle branch. It now runs once per action too, with its own throttle —
measured as one check per twenty key steps in a second.

The delicate part is the *order*, and the source says why: the watch
compares screen against drawn picture, and while scrolling those two
diverge outside the copied band. Checked earlier, it would have read our
own not-yet-copied rows as foreign text — the Build 151 flicker, back
again. So it checks *after* the header rows are refreshed, since those
have just re-copied exactly the area it looks at.

**And the F9 finding is unambiguous: it is not our picture.** Five times
"0 pixels, threshold 120". Our picture stands untouched in our own
framebuffer; MiSTer is simply showing a different display layer. Neither
the watch nor the picture guard can ever repair that — both only know our
own memory. The switch has to go through MiSTer itself. Which way that is
will not be guessed; measurements on the device are on their way.

---

**F9 on the keyboard is now noticed — and attract mode stops building
thumbnails of its own.**

Reported: "F12 gets me to the OSD, that still works; then I press F9 and
the frontend should come back, but I'm stuck at the login prompt" — plus
the decisive addition: "if I press F12 again at the login prompt, I'm back
in the frontend."

Our own source has said since Build 150 what triggers that prompt: *any*
F9 wakes the login process on tty1, and it writes its "Welcome to MiSTer …
login:" into the very framebuffer the frontend draws into. For its **own**
F9 at startup the frontend therefore cleans up afterwards. For the
**user's** F9 that never happened, for a simple reason: F9 is deliberately
mapped to *nothing*, because MiSTer needs the key for switching the
display — so the keypress never reached the frontend at all. It is now
recorded (and still does nothing), and the same cleanup that has worked
since Build 150 is armed.

Whether that is enough is not claimed here. His log contains **not a
single line** during the whole F12/F9 sequence — neither from the standing
watch nor from the picture guard. That leaves two possibilities: the
prompt is in our framebuffer and the watch counts too few pixels, or it is
*not* there at all and MiSTer is simply showing a different display layer
with our picture intact underneath. That F12 returns to the frontend
rather than opening the OSD fits the second. On exactly this hunt I took a
wrong turn four times in Builds 146–149, because an observation became a
cause — so nothing is guessed here: the build writes the pixel count to
the log. The next log line decides.

**Attract mode takes the game list's cover box.** It used to have its own
— 50 % of the width, 72 % of the height, so 960×777 at 1080p. The
thumbnail cache carries the box size in its key, which means the screen
saver computed and wrote a private, otherwise unused thumbnail for *every*
game it showed. The cover column yields 697×771 — nearly the same height,
and height is the limit for portrait covers anyway. Visually almost
nothing changes; it now reads the file the game list already has. The
badges on the main page are unchanged.

**New, to try out: the gallery from the grid tile.** Gallery-large
(342×456) and grid tile (176×235) sit close together, a factor of 1.94. If
the gallery takes that same tile and merely shows it bigger, a second file
per game disappears and switching between the two views is warm
immediately. The price is nearest-neighbour upscaling, so a visibly
coarser picture — only your eye at the TV can decide that. Hence a switch,
**off** by default:

```
touch /media/fat/frontend/galerie_kachelquelle     # on
rm    /media/fat/frontend/galerie_kachelquelle     # off
```

Without the file everything is line for line the state of Build 206.

---

**A half-applied update no longer leaves the frontend dead with a
traceback — and the fault was in how I ship it.**

At a friend of the user's, nothing started at all after an update:

```
Traceback (most recent call last):
  File "/media/fat/frontend/frontend.py", line 218, in <module>
    from fe.settings import (
ImportError: cannot import name 'artbox_aufschub_aus' from 'fe.settings'
```

His `frontend.py` knew the name, his `fe/settings.py` did not. The name
arrived in **both** files in the same build — and my build packages only
ever contain the *changed* files. A package carrying `frontend.py` but not
the matching `fe/settings.py` is therefore only safe if every earlier
package is already installed. Skip one and you get exactly this crash.
That is not a user error, it is a packaging error of mine.

Two things against it:

**The crash is now an instruction.** A safeguard already existed — the
frontend has long compared by name whether the parts match and printed
what to do instead of crashing. It simply never got its turn: a missing
name in an import dies *before* a single line of our own code runs. A
hook at the very top of the file — ahead of the first import — now closes
that gap for all thirty-odd imports at once.

Importantly, **everything else is passed through untouched.** A genuine
programming error still looks like one — a hook that catches too much
turns every future fault into a misleading update instruction. That is
verified against a real, reconstructed mixed state on disk, not just
against the function.

**And there is a complete package again.** For anyone who did not follow
every intermediate step, a full package is the safe route; incremental
ones are for those who were there without gaps.

**The switch to JPEG made scrolling slower first — that is fixed, and the
mistake was mine.**

After the switch the measured figures were worse than before:

```
before   down/S1  69x mean  72 ms (max  192)
after    down/S1   7x mean 492 ms (max  750)
         right/S1 59x mean 265 ms (max 1831)
```

Reading was not the problem; the rewriting was. Old thumbnails are
rewritten to JPEG when read, and that goes through a helper which starts
**its own thread per call**. Its own description states expressly that
this is only acceptable because it happens "only when writing away a
freshly computed thumbnail (not on every scroll step)". That is exactly
the assumption I had broken: while scrolling, every step started a thread
that packed, JPEG-encoded and dragged a directory scan along with it. On
two weak cores that competes directly with the drawing — and for the same
SD card.

I had read that description while building and still walked into it.

Two brakes now:

- **Only at rest.** Nothing is rewritten while you are navigating. The
  move happens when there is slack anyway.
- **At most one rewrite every two seconds.** Not even at idle should this
  become a storm.

With 97,000 entries the migration thus becomes a matter of normal use over
weeks — and is meant to be unnoticeable. Reading itself is as fast as
before; only the rewriting is throttled.

**The bench now answers a question that was already answered wrongly once
— on the development machine.**

When the list rolls on while scrolling the main menu, there is no light
drawing path: a full rebuild runs, `rows=77` in the user's log. The
obvious remedy would be to shift the already drawn block up by one row in
memory and only set the newly exposed row.

That existed (build 96) and was removed again (build 102), with
measurements — and with a comment that sits there expressly "so that
nobody (myself included) builds the same idea a second time in six
months". I had just proposed it for the second time; the comment worked.

One number in it is suspicious though: **2.04 ms for a full page build**.
On the user's device the same build costs 77 ms. Those are
development-machine figures, and there the ratio between setting text and
moving memory is the other way round — text is cheap, the copy expensive.
On a weak ARM CPU it is reversed. Recomputed with the device's numbers:
**8.5 ms copy + 13 ms for two rows against 77 ms** for the full rebuild.

So what was built is *not* the feature but the measurement: a new bench
section measures the three **ingredients** separately — full rebuild,
shifting the block, one category row — and writes the arithmetic out in
the open. Each individual measurement is simple enough that its
correctness is not in question, and the decision follows from the
arithmetic instead of from a hunch. It draws into the buffer only, never
to the screen.

Locally it reproduces build 102 cleanly: the shift alone costs 0.855 ms
and is therefore **more expensive than the entire full rebuild**
(0.479 ms). Whether that also holds on the device is what the bench will
say there.

*Two mistakes of my own along the way, both caught by tests:* with a
stopped clock — the test harness freezes it — the section turned three
zeros into "it does NOT pay off", i.e. a verdict from missing data. And
with an unreadable category tree it *aborted* instead of reporting
"skipped" and leaving the rest of the report standing. Both fixed, both
now covered.

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
