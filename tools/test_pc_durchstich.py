#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Der Durchstich: Auftrag schreiben -> am PC rechnen -> findet das
Frontend die Miniatur wieder? (Build 145)

Das ist die Frage, an der die ganze Sache haengt. Der Cache-Schluessel
enthaelt Pfad, Kastenmasse, Dateigroesse, Aenderungszeit und
Verfahrensnummer. Stimmt davon EINES nicht, legt der PC seine
Miniaturen unter einem Schluessel ab, unter dem nie jemand nachsieht -
und man merkt es erst, wenn nach Stunden nichts schneller geworden ist.

Hier laeuft die komplette Kette einmal durch, nur ohne Netz:

  1. Ein echtes PNG anlegen.
  2. Frontend._prewarm_auftrag_schreiben() die Auftragsdatei schreiben
     lassen - dieselbe Methode, die der Menuepunkt aufruft.
  3. Den Auftrag lesen und mit pc_tools/dragend_kern.py rechnen, genau
     wie das PC-Programm es taete.
  4. Die Ergebnisse dorthin legen, wohin der Auftrag zeigt.
  5. thumb_cache_has() fragen - und die Miniatur wieder auslesen.

Ausfuehren:
    python3 tools/test_pc_durchstich.py
"""
import os
import sys
import json
import shutil
import struct
import tempfile

_HIER = os.path.dirname(os.path.abspath(__file__))
_WURZEL = os.path.dirname(_HIER)
sys.path.insert(0, _HIER)
sys.path.insert(0, os.path.join(_WURZEL, "pc_tools"))

import _harness as H                                        # noqa: E402
import dragend_kern as KERN                                 # noqa: E402

fm = H.fm
ART = sys.modules["fe.art"]
fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


tmp = tempfile.mkdtemp(prefix="pc_durchstich_")
try:
    # ------------------------------------------------------------------
    print("Test 1: Auftrag schreiben")
    # ------------------------------------------------------------------
    from PIL import Image
    cover_pfad = os.path.join(tmp, "Super Grüße (Europe).png")
    # Bewusst mit Umlaut im Namen: genau daran koennte der Schluessel
    # zwischen zwei Systemen auseinanderlaufen.
    Image.new("RGBA", (600, 800), (180, 60, 40, 255)).save(cover_pfad)

    # Zwischenspeicher in den Testordner umbiegen.
    ART.THUMB_CACHE_BASE = os.path.join(tmp, "thumb_cache")
    ART.thumb_cache_modus_setzen(False)
    ART.thumb_cache_modus_setzen(True)

    f = H.make_frontend(page=1)
    f.AUFTRAG_DATEI = os.path.join(tmp, "miniatur_auftrag.json")
    fm.THUMB_CACHE_BASE = ART.THUMB_CACHE_BASE

    KAESTEN = [(360, 420), (137, 183), (900, 1200)]
    f._prewarm_auftrag_schreiben([(cover_pfad, KAESTEN)], [])

    check("Auftragsdatei liegt da", os.path.exists(f.AUFTRAG_DATEI))
    with open(f.AUFTRAG_DATEI, encoding="utf-8") as fh:
        auftrag = json.load(fh)
    check("Verfahrensnummer steht drin",
          auftrag.get("algo") == ART.THUMB_ALGO_VERSION,
          repr(auftrag.get("algo")))
    check("HDMI-Kennzeichen gesetzt", auftrag.get("hd") is True,
          repr(auftrag.get("hd")))
    check("ein Cover mit drei Kaesten",
          len(auftrag["cover"]) == 1
          and len(auftrag["cover"][0]["k"]) == 3,
          json.dumps(auftrag["cover"])[:120])
    check("Pfad mit Umlaut unveraendert uebernommen",
          auftrag["cover"][0]["p"] == cover_pfad)

    # ------------------------------------------------------------------
    print("Test 2: am 'PC' rechnen und ablegen")
    # ------------------------------------------------------------------
    with open(cover_pfad, "rb") as fh:
        rohdaten = fh.read()
    w, h, pix = KERN.bild_lesen(rohdaten)
    check("Bild in Originalgroesse gelesen", (w, h) == (600, 800),
          "%dx%d" % (w, h))

    geschrieben = 0
    for eintrag in auftrag["cover"]:
        for kasten in eintrag["k"]:
            inhalt = KERN.miniatur_bauen(w, h, pix, kasten["b"], kasten["h"])
            ziel = KERN.cache_pfad(auftrag["cache"], auftrag["hd"],
                                   kasten["k"])
            os.makedirs(os.path.dirname(ziel), exist_ok=True)
            with open(ziel, "wb") as fh:
                fh.write(inhalt)
            geschrieben += 1
    check("drei Dateien geschrieben", geschrieben == 3, str(geschrieben))

    # ------------------------------------------------------------------
    print("Test 3: findet das Frontend sie wieder?")
    # ------------------------------------------------------------------
    for (bw, bh) in KAESTEN:
        check("Treffer fuer %dx%d" % (bw, bh),
              ART.thumb_cache_has(cover_pfad, bw, bh))

    # Und laesst sie sich auch benutzen?
    erg = ART._thumb_cache_get(cover_pfad, 360, 420)
    check("360x420 laesst sich lesen", erg is not None)
    if erg and erg is not ART.ORIGINAL_PASST:
        tw, th, _pix = erg[0], erg[1], erg[2]
        soll = ART.zielmass(600, 800, 360, 420)
        check("Masse wie vom Frontend erwartet", (tw, th) == soll,
              "%dx%d gegen %s" % (tw, th, soll))

    # Der grosse Kasten (900x1200) ist groesser als das Cover -> Marke.
    erg = ART._thumb_cache_get(cover_pfad, 900, 1200)
    check("zu grosser Kasten ergibt die Marke",
          erg is ART.ORIGINAL_PASST, repr(erg)[:60])

    # ------------------------------------------------------------------
    print("Test 4: bereits vorhandene Miniaturen kommen nicht in den Auftrag")
    # ------------------------------------------------------------------
    f._prewarm_auftrag_schreiben([(cover_pfad, KAESTEN)], [])
    with open(f.AUFTRAG_DATEI, encoding="utf-8") as fh:
        zweiter = json.load(fh)
    check("zweiter Auftrag ist leer", not zweiter["cover"],
          json.dumps(zweiter["cover"])[:100])

    # ------------------------------------------------------------------
    print("Test 5: ein geaendertes Cover kommt wieder rein")
    # ------------------------------------------------------------------
    Image.new("RGBA", (600, 800), (20, 200, 90, 255)).save(cover_pfad)
    f._prewarm_auftrag_schreiben([(cover_pfad, KAESTEN)], [])
    with open(f.AUFTRAG_DATEI, encoding="utf-8") as fh:
        dritter = json.load(fh)
    check("geaendertes Cover steht wieder im Auftrag",
          len(dritter["cover"]) == 1
          and len(dritter["cover"][0]["k"]) == 3,
          json.dumps(dritter["cover"])[:120])
    alt = {k["k"] for k in auftrag["cover"][0]["k"]}
    neu = {k["k"] for k in dritter["cover"][0]["k"]}
    check("und zwar unter NEUEN Schluesseln", not (alt & neu),
          str(sorted(alt & neu)))
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  - " + x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
