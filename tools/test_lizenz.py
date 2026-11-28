#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Die Lizenz (Build 351): GPL-3.0-or-later statt MIT.

GEPRUEFT WIRD:
  1. LICENSE ist der unveraenderte Text der GPL, Version 3.
  2. Der alte MIT-Text steht vollstaendig in LICENSE_MIT_bis_Build_350.txt,
     mit dem alten Copyright-Vermerk.
  3. README (de/en), VORSCHAU, Handbuch und Manual nennen die GPL und
     die alte Datei - und nirgends mehr MIT als Lizenz von Dragend.
  4. Das Skript von sage2050 behaelt seinen eigenen MIT-Vermerk.
  5. Der Kopf von frontend.py nennt die Lizenz.
  6. Der Zeitreise-Sound (Build 352) ist als Ausnahme vermerkt.

Ausfuehren:
    python3 tools/test_lizenz.py
"""
import hashlib
import os
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


def lies(name):
    with open(os.path.join(_REPO, name), encoding="utf-8") as f:
        return f.read()


lic = lies("LICENSE")
check("LICENSE: GPL Version 3",
      lic.startswith("                    GNU GENERAL PUBLIC LICENSE\n"
                     "                       Version 3, 29 June 2007")
      and "END OF TERMS AND CONDITIONS" in lic
      and "MIT License" not in lic)
check("LICENSE: der unveraenderte Text (674 Zeilen, Pruefsumme)",
      lic.count("\n") == 674
      and hashlib.md5(lic.encode("utf-8")).hexdigest()
      == "1ebbd3e34237af26da5dc08a4e440464",
      lic.count("\n"))
alt = lies("LICENSE_MIT_bis_Build_350.txt")
check("alte MIT-Lizenz vollstaendig aufbewahrt",
      "MIT License\n\nCopyright (c) 2026 Dragrem2K" in alt
      and "Permission is hereby granted, free of charge" in alt
      and alt.rstrip().endswith("SOFTWARE.")
      and "TheRealSuTefan" in alt and "Dfense" in alt
      and "Build 350" in alt and "GPL-3.0-or-later" in alt)
for name, muss in (("README.md", "Lizenz: [GPL-3.0-or-later](LICENSE)"),
                   ("README_EN.md", "Licence: [GPL-3.0-or-later](LICENSE)"),
                   ("VORSCHAU.md", "Lizenz: [GPL-3.0-or-later](LICENSE)"),
                   ("docs/HANDBUCH.md", "GPL-3.0-or-later, siehe `LICENSE`"),
                   ("docs/MANUAL_EN.md", "GPL-3.0-or-later, see `LICENSE`")):
    t = lies(name)
    check("%s nennt die GPL und die alte Datei" % name,
          muss in t and "LICENSE_MIT_bis_Build_350.txt" in t)
    check("%s nennt MIT nicht mehr als Lizenz von Dragend" % name,
          "[MIT](LICENSE)" not in t and "unter der MIT-Lizenz (siehe" not in t
          and "under the MIT license (see" not in t)
# Build 352: der Zeitreise-Sound steht unter der Pixabay-Lizenz.
for name in ("README.md", "README_EN.md", "docs/HANDBUCH.md",
             "docs/MANUAL_EN.md"):
    t = lies(name)
    check("%s nennt den Sound als Ausnahme von der GPL" % name,
          "zeitreise.mp3" in t and "Pixabay" in t
          and "QUELLEN.txt" in t)
q = lies("frontend/sfx/QUELLEN.txt")
check("frontend/sfx/QUELLEN.txt: Herkunft und Lizenz des Sounds",
      "AudioPapkin" in q and "Pixabay" in q and "NICHT unter der GPL" in q)
ra = lies("Scripts/MiSTer_RA.sh")
check("Scripts/MiSTer_RA.sh (sage2050) behaelt seinen MIT-Vermerk",
      "License: MIT" in ra)
kopf = lies("frontend/frontend.py")[:1500]
check("frontend.py: Lizenz im Kopf",
      "GNU General" in kopf and "Version 3" in kopf and "LICENSE" in kopf)

print()
if fails:
    print("ROT: %d Pruefung(en) fehlgeschlagen:" % len(fails))
    for f_ in fails:
        print("   - " + f_)
    sys.exit(1)
print("ALLES GRUEN")
