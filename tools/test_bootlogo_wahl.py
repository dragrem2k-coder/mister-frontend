#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Das Bootlogo zum Aussuchen: Dragend, Dennsen86, Cirdan, Zufall, neutral (Build 326).

NUTZERWUNSCH: "die beiden logos bitte als bootlogos zum aussuchen mit
einbinden" - Dennsen86 und Cirdan, neben dem Dragend-Logo.

GEPRUEFT WIRD:
  1. Die beiden neuen Dateien: gueltiges ART1, 640x640, ueber denselben
     Lader lesbar wie das Dragend-Logo - und die Farben stehen in der
     richtigen Reihenfolge (BGRA): das Gelb von Dennsen86 ist Gelb.
     GEGENPROBE: mit vertauschten Kanaelen waere es kein Gelb.
  2. Die Wahl: Vorgabe Dragend; der alte Schalter "neutral" aus der Zeit
     vor Build 326 gilt weiter; Durchschalten durch alle fuenf und
     wieder von vorn; beim Umschalten verschwindet der alte Schalter;
     Unsinn in der Datei faellt auf die Vorgabe zurueck.
  3. Welche Datei gezeigt wird: je Wahl die richtige, None fuer
     "neutral" und fuer ein fehlendes Logo; "zufall" waehlt nur unter
     den vorhandenen.
  4. Der Start zeigt die GEWAEHLTE Datei (am echten
     _draw_dragend_logo_boot()), ohne Angabe wie bisher das Dragend-Logo.
  5. Der Menuepunkt nennt das gewaehlte Logo.

Ausfuehren:
    python3 tools/test_bootlogo_wahl.py
"""
import os
import shutil
import struct
import sys
import tempfile
import zlib

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
sys.path.insert(0, _HIER)

import _harness as H                                     # noqa: E402

fm = H.fm
import fe.settings as S                                  # noqa: E402
import fe.menu as M                                      # noqa: E402
import fe.art as A                                       # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


print(__doc__.strip().split("\n")[0])
print()

LOGO_DIR = os.path.join(_REPO, "frontend", "boot_logo")
DENNSEN = os.path.join(LOGO_DIR, "dennsen86_logo.art")
CIRDAN = os.path.join(LOGO_DIR, "cirdan_logo.art")
DRAGEND = os.path.join(LOGO_DIR, "dragend_logo.art")


def lesen(pfad):
    d = open(pfad, "rb").read()
    w, h = struct.unpack("<HH", d[4:8])
    return d[:4], w, h, zlib.decompress(d[8:])


def gelbanteil(roh, bgra=True):
    """Anteil der Bildpunkte, die kraeftig gelb sind (R und G hoch, B
    niedrig) - gelesen als BGRA, oder zur Gegenprobe als RGBA."""
    n = len(roh) // 4
    gelb = 0
    for i in range(0, len(roh), 4 * 7):           # jeder 7. Punkt reicht
        b, g, r = (roh[i], roh[i + 1], roh[i + 2]) if bgra else \
            (roh[i + 2], roh[i + 1], roh[i])
        if r > 180 and g > 180 and b < 90:
            gelb += 1
    return gelb / float(max(1, n // 7))


# ---------------------------------------------------------------------------
print("Test 1: die beiden neuen Dateien")
# ---------------------------------------------------------------------------
for name, pfad in (("Dennsen86", DENNSEN), ("Cirdan", CIRDAN)):
    check("%s liegt bei" % name, os.path.isfile(pfad))
    kopf, w, h, roh = lesen(pfad)
    check("%s: ART1, 640x640, vollstaendig" % name,
          kopf == b"ART1" and (w, h) == (640, 640)
          and len(roh) == w * h * 4, (kopf, w, h, len(roh)))
    check("%s: deckend (Alpha 255 wie beim Dragend-Logo)" % name,
          all(roh[i] == 255 for i in range(3, len(roh), 4 * 997)))
    art = A.ART.get(pfad)
    check("%s: ueber denselben Lader lesbar" % name,
          art is not None and art[0] == 640 and art[1] == 640)
_k, _w, _h, roh_d = lesen(DENNSEN)
anteil = gelbanteil(roh_d)
check("Dennsen86: das Gelb ist Gelb (BGRA)", anteil > 0.05,
      "%.1f %% gelb" % (anteil * 100))
check("GEGENPROBE: als RGBA gelesen waere es kein Gelb",
      gelbanteil(roh_d, bgra=False) < anteil / 5,
      "%.1f %%" % (gelbanteil(roh_d, bgra=False) * 100))
_k, _w, _h, roh_c = lesen(CIRDAN)
check("Cirdan: ueberwiegend dunkler Grund",
      sum(roh_c[i] + roh_c[i + 1] + roh_c[i + 2]
          for i in range(0, 4 * 640 * 20, 4)) / (640 * 20 * 3) < 60)

# ---------------------------------------------------------------------------
# Die Wahl, in eigenen Dateien
# ---------------------------------------------------------------------------
TMP = tempfile.mkdtemp(prefix="bootlogo_")
_alt = (S.BOOT_LOGO_WAHL_FILE, S.DRAGEND_LOGO_DISABLED_FLAG, S.BOOT_LOGOS)
S.BOOT_LOGO_WAHL_FILE = os.path.join(TMP, "boot_logo_wahl")
S.DRAGEND_LOGO_DISABLED_FLAG = os.path.join(TMP, "dragend_logo_disabled")
S.BOOT_LOGOS = (("dragend", DRAGEND, "Dragend"),
                ("dennsen86", DENNSEN, "Dennsen86"),
                ("cirdan", CIRDAN, "Cirdan"))
try:
    # -----------------------------------------------------------------------
    print()
    print("Test 2: die Wahl")
    # -----------------------------------------------------------------------
    check("Vorgabe: Dragend", S.boot_logo_wahl() == "dragend")
    open(S.DRAGEND_LOGO_DISABLED_FLAG, "w").close()
    check("der alte Schalter 'neutral' gilt weiter",
          S.boot_logo_wahl() == "neutral")
    check("und dann wird gar kein Logo gezeigt",
          S.dragend_logo_enabled() is False)
    gesehen = [S.boot_logo_weiter() for _ in range(5)]
    check("Durchschalten: alle fuenf und wieder von vorn",
          gesehen == ["dragend", "dennsen86", "cirdan", "zufall",
                      "neutral"], gesehen)
    check("beim Umschalten ist der alte Schalter verschwunden",
          not os.path.exists(S.DRAGEND_LOGO_DISABLED_FLAG))
    check("die Wahl steht in der Datei",
          open(S.BOOT_LOGO_WAHL_FILE).read().strip() == "neutral")
    check("der alte Name schaltet genauso weiter",
          S.toggle_dragend_logo() == "dragend")
    with open(S.BOOT_LOGO_WAHL_FILE, "w") as f:
        f.write("quatsch\n")
    check("Unsinn in der Datei: Vorgabe", S.boot_logo_wahl() == "dragend")

    # -----------------------------------------------------------------------
    print()
    print("Test 3: welche Datei gezeigt wird")
    # -----------------------------------------------------------------------
    check("Dragend", S.boot_logo_datei("dragend") == DRAGEND)
    check("Dennsen86", S.boot_logo_datei("dennsen86") == DENNSEN)
    check("Cirdan", S.boot_logo_datei("cirdan") == CIRDAN)
    check("neutral: keine", S.boot_logo_datei("neutral") is None)
    gezogen = []
    S.boot_logo_datei("zufall", zufall=lambda liste: gezogen.append(
        list(liste)) or liste[-1])
    check("Zufall waehlt unter allen drei",
          gezogen and sorted(gezogen[0]) == sorted([DRAGEND, DENNSEN, CIRDAN]))
    S.BOOT_LOGOS = (("dragend", DRAGEND, "Dragend"),
                    ("dennsen86", os.path.join(TMP, "fehlt.art"),
                     "Dennsen86"),
                    ("cirdan", CIRDAN, "Cirdan"))
    check("ein fehlendes Logo: keine Datei (dann das D-Pad-Symbol)",
          S.boot_logo_datei("dennsen86") is None)
    gezogen = []
    S.boot_logo_datei("zufall", zufall=lambda liste: gezogen.append(
        list(liste)) or liste[0])
    check("Zufall nimmt nur vorhandene",
          gezogen and sorted(gezogen[0]) == sorted([DRAGEND, CIRDAN]),
          gezogen)
    S.BOOT_LOGOS = (("dragend", DRAGEND, "Dragend"),
                    ("dennsen86", DENNSEN, "Dennsen86"),
                    ("cirdan", CIRDAN, "Cirdan"))

    # -----------------------------------------------------------------------
    print()
    print("Test 4: der Start zeigt die gewaehlte Datei")
    # -----------------------------------------------------------------------
    H.set_screen(1920, 1080)
    f = H.make_frontend(page=0)
    f.inp.read_action = lambda timeout=None: None
    f._auf_eigenes_bild_warten = lambda *a, **k: None
    geladen = []
    _echt_get = fm.ART.get

    def _get(pfad, *a, **k):
        geladen.append(pfad)
        return _echt_get(pfad, *a, **k)
    fm.ART.get = _get
    try:
        f._draw_dragend_logo_boot(CIRDAN)
        check("Cirdan geladen", geladen[:1] == [CIRDAN], geladen[:2])
        mitte = f.fb.width // 2, f.fb.height // 2
        check("und auf dem Bild steht etwas (nicht nur Schwarz)",
              any(f.fb.buf[((mitte[1] + dy) * f.fb.width + mitte[0]) * 4
                           + c] > 30
                  for dy in range(-60, 60, 5) for c in range(3)))
        del geladen[:]
        f._draw_dragend_logo_boot()
        check("GEGENPROBE ohne Angabe: wie bisher das Dragend-Logo",
              geladen[:1] == [fm.DRAGEND_LOGO_FILE], geladen[:1])
    finally:
        fm.ART.get = _echt_get
    q = open(H.FRONTEND_PY, encoding="utf-8").read()
    pb = H.nur_code(H.koerper(q, "play_boot_animation"))
    check("play_boot_animation() fragt boot_logo_datei()",
          "boot_logo_datei(" in pb and "_draw_dragend_logo_boot(_logo)" in pb)

    # -----------------------------------------------------------------------
    print()
    print("Test 5: der Menuepunkt nennt das gewaehlte Logo")
    # -----------------------------------------------------------------------
    def zeile():
        """Die Zeile mit kind "dragend_logo" im echten Menuebaum."""
        offen = [M.system_items()]
        while offen:
            knoten = offen.pop()
            for eintrag in knoten.get("items", ()):
                if len(eintrag) > 1 and eintrag[1] == "dragend_logo":
                    return eintrag[0]
            offen.extend(knoten.get("folders", {}).values())
        return None
    with open(S.BOOT_LOGO_WAHL_FILE, "w") as fh:
        fh.write("dennsen86\n")
    check("Dennsen86", "Dennsen86" in (zeile() or ""), zeile())
    with open(S.BOOT_LOGO_WAHL_FILE, "w") as fh:
        fh.write("cirdan\n")
    check("Cirdan", "Cirdan" in (zeile() or ""), zeile())
    with open(S.BOOT_LOGO_WAHL_FILE, "w") as fh:
        fh.write("zufall\n")
    check("Zufall", fm.t("sys_boot_logo_zufall") in (zeile() or ""),
          zeile())
finally:
    (S.BOOT_LOGO_WAHL_FILE, S.DRAGEND_LOGO_DISABLED_FLAG,
     S.BOOT_LOGOS) = _alt
    H._zwischenspeicher_leeren()
    shutil.rmtree(TMP, ignore_errors=True)

print()
if fails:
    print("ROT: %d Pruefung(en) fehlgeschlagen:" % len(fails))
    for f_ in fails:
        print("   - " + f_)
    sys.exit(1)
print("ALLES GRUEN")
