# Measurements

Taken with the built-in bench (`python3 frontend.py --bench`, see the
[README](../README_EN.md#measure-it-yourself---bench)).

Deutsch: [MESSUNG.md](MESSUNG.md)

## Device

| | |
|---|---|
| Hardware | DE10-Nano |
| System | Linux 5.15.1-MiSTer (armv7l), Python 3.9.6 |
| Display | 1920×1080 |
| C module | libdragend version 3 |
| Collection | 30,064 games in 22 categories |
| As of | build 179, 2026-09-21 |

## Image chain — comparable between devices

Computed on a **generated** 1200×1600 test image, independent of what
is on the card. Three runs:

| | Run 1 | Run 2 | Run 3 |
|---|---|---|---|
| Downscale to 578×770, area average (C) | 114.50 ms | 111.70 ms | 112.13 ms |
| Downscale to 578×770, nearest (C) | 26.65 ms | 26.13 ms | 26.21 ms |
| Downscale to 176×235, area average (C) | 45.98 ms | 44.28 ms | 44.56 ms |
| Downscale to 176×235, nearest (C) | 3.89 ms | 3.81 ms | 3.93 ms |
| **C versus Python** | **×121** | **×123** | **×124** |

The three runs agree within **2 %**.

578×770 is the cover column box at 1080p, 176×235 a grid tile.
"Nearest" is sharp downscaling for CRTs (*System → Display & Sound*) —
4.3 times cheaper than smooth averaging for the large box, 11 times for
the tile.

| Thumbnail cache (run 3) | |
|---|---|
| Pack and write a 578×770 thumbnail | 694 ms |
| Read and unpack a 578×770 thumbnail | 90 ms |
| Read and decode a 1200×1600 PNG | 259 ms |

## Startup

| | Run 1 | Run 2 | Run 3 |
|---|---|---|---|
| Startup until categories are ready | 3,411 ms | 3,525 ms | 3,482 ms |
| **per game** | **0.114 ms** | **0.117 ms** | **0.116 ms** |

Depends on the collection, hence also given per game.

## Scrolling

Run 3, measured in the Arcade category (1027 entries), per step,
**without** waiting for the display refresh:

| Game list | cover has to be computed | cover already in memory |
|---|---|---|
| List | 264 ms | 79 ms |
| Grid | 72 ms | 50 ms |
| Gallery | 183 ms | 104 ms |

| Main page | cold | warm |
|---|---|---|
| List | 50 ms | 32 ms |
| Grid | 44 ms | 42 ms |
| Gallery | 77 ms | 74 ms |

**When reading this:** "cover has to be computed" is the upper bound.
While scrolling for real, the frontend skips the cover column during
fast scrolling and computes only when you stop. After *Prepare
thumbnails*, everyday use lies between the two columns.

| Frame transfer | |
|---|---|
| Copy the whole frame (7.9 MB) | 12.6 ms |
| Waiting for the display refresh (60 Hz) | +13.0 ms |

## How these numbers came about

The first two runs mostly found faults **in the measuring tool** —
among other things, the bench initially measured whatever category it
happened to land in, once a category with a single entry, i.e. a still
image. The scrolling figures above therefore come from run 3 only. The
image chain was never affected, because it does not depend on the
collection — hence all three runs there.

Measurements from other devices, resolutions or collection sizes are
welcome: run `--bench` and send `/tmp/dragend_bench.txt`.
