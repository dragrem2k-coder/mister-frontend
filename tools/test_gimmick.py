#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Das Gimmick unter System -> Wartung: Invade-a-Load auf dem C64-Core (Build 329).

NUTZERWUNSCH: "kann man dieses spiel im frontend starten? sollte als
gimmick unter system wartung sein".

GEPRUEFT WIRD (ohne das Spiel selbst - es wird nicht mitgeliefert, der
Test baut sich eine T64):
  1. T64 -> PRG: Ladeadresse + Inhalt des ersten Programms; die falsche
     Endadresse vieler T64 (0xC3C6) faellt auf das Dateiende zurueck;
     bei zwei Programmen das erste; Unsinn ergibt None.
  2. Finden: nur in den Suchordnern, Gross/Klein egal, die drei
     Schreibweisen, fremde Dateien nicht; der C64-Core mit und ohne
     Datum im Namen.
  3. Bereitstellen: eine PRG wird direkt genommen; aus einer T64 wird
     EINMAL in den eigenen Ordner geschrieben - nie neben die Quelle.
  4. Der Menuepunkt steht nur da, wenn Datei UND Core da sind.
  5. Der Start: MGL mit _Computer/C64, type "f", index 1 und dem Pfad
     der PRG; fehlt etwas, startet nichts und unten steht der Grund.

Ausfuehren:
    python3 tools/test_gimmick.py
"""
import os
import shutil
import struct
import sys
import tempfile
import time

_HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HIER)

import _harness as H                                     # noqa: E402

fm = H.fm
import fe.gimmick as G                                   # noqa: E402
import fe.menu as M                                      # noqa: E402
import fe.launch as L                                    # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


print(__doc__.strip().split("\n")[0])
print()


def t64(programme, falsches_ende=False):
    """Eine T64 bauen: programme = [(ladeadresse, bytes)]."""
    kopf = bytearray(b"C64 tape image file".ljust(32, b"\x00"))
    kopf += struct.pack("<HHH", 0x100, len(programme), len(programme))
    kopf += b"\x00\x00" + b"TESTBAND".ljust(24, b" ")
    eintraege = bytearray()
    daten = bytearray()
    versatz = 0x40 + 32 * len(programme)
    for start, inhalt in programme:
        ende = 0xC3C6 if falsches_ende else start + len(inhalt)
        eintraege += struct.pack("<BBHHHI", 1, 0x82, start, ende, 0,
                                 versatz + len(daten))
        eintraege += b"\x00" * 4 + b"PROGRAMM".ljust(16, b" ")
        daten += inhalt
    return bytes(kopf + eintraege + daten)


INHALT = bytes(range(256)) * 20 + b"ENDE"
INHALT2 = b"\x01\x02\x03" * 100

# ---------------------------------------------------------------------------
print("Test 1: T64 -> PRG")
# ---------------------------------------------------------------------------
prg = G.t64_erstes_programm(t64([(0x0801, INHALT)]))
check("Ladeadresse und Inhalt", prg == b"\x01\x08" + INHALT,
      len(prg or b""))
prg = G.t64_erstes_programm(t64([(0x0801, INHALT)], falsches_ende=True))
check("falsche Endadresse: bis zum Dateiende", prg == b"\x01\x08" + INHALT)
prg = G.t64_erstes_programm(t64([(0x0801, INHALT), (0xC000, INHALT2)]))
check("zwei Programme: das erste, nicht mehr", prg == b"\x01\x08" + INHALT)
prg = G.t64_erstes_programm(t64([(0x0801, INHALT), (0xC000, INHALT2)],
                                falsches_ende=True))
check("zwei Programme, falsche Endadresse: bis zum naechsten",
      prg == b"\x01\x08" + INHALT)
check("GEGENPROBE: keine T64 -> None",
      G.t64_erstes_programm(b"PK\x03\x04" + b"\x00" * 200) is None)
check("leer -> None", G.t64_erstes_programm(b"") is None)
check("zu kurz -> None", G.t64_erstes_programm(b"C64 tape") is None)

TMP = tempfile.mkdtemp(prefix="gimmick_")
try:
    # -----------------------------------------------------------------------
    print()
    print("Test 2: finden")
    # -----------------------------------------------------------------------
    a = os.path.join(TMP, "a")
    b = os.path.join(TMP, "b")
    kern = os.path.join(TMP, "_Computer")
    for o in (a, b, kern):
        os.makedirs(o)
    open(os.path.join(a, "Andere Spiel.t64"), "wb").close()
    check("nichts da: None", G.finden([a, b]) is None)
    pfad = os.path.join(b, "Invade-a-Load_USA.T64")
    with open(pfad, "wb") as f:
        f.write(t64([(0x0801, INHALT)]))
    check("Gross/Klein egal, im zweiten Ordner gefunden",
          G.finden([a, b]) == pfad, G.finden([a, b]))
    for name in ("invade_a_load.prg", "InvadeALoad.t64"):
        p = os.path.join(a, name)
        open(p, "wb").close()
        check("Schreibweise %s" % name, G.finden([a]) == p)
        os.remove(p)
    check("GEGENPROBE: falsche Endung nicht",
          not G._passt("Invade-a-Load.d64"))
    check("kein Core: nein", not G.c64_core_da(kern))
    open(os.path.join(kern, "C64_20260301.rbf"), "wb").close()
    check("C64_<Datum>.rbf: ja", G.c64_core_da(kern))
    os.remove(os.path.join(kern, "C64_20260301.rbf"))
    open(os.path.join(kern, "C64.rbf"), "wb").close()
    check("C64.rbf: ja", G.c64_core_da(kern))
    open(os.path.join(kern, "C64_falsch.txt"), "wb").close()
    os.remove(os.path.join(kern, "C64.rbf"))
    check("GEGENPROBE: etwas anderes mit C64 im Namen: nein",
          not G.c64_core_da(kern))

    # -----------------------------------------------------------------------
    print()
    print("Test 3: bereitstellen")
    # -----------------------------------------------------------------------
    eigen = os.path.join(TMP, "eigen")
    vorher_b = sorted(os.listdir(b))
    ziel = G.prg_bereitstellen(pfad, eigen)
    check("in den eigenen Ordner geschrieben",
          ziel == os.path.join(eigen, "Invade-a-Load_USA.prg"), ziel)
    check("mit dem ersten Programm",
          open(ziel, "rb").read() == b"\x01\x08" + INHALT)
    check("neben der Quelle hat sich nichts geaendert",
          sorted(os.listdir(b)) == vorher_b, os.listdir(b))
    check("keine .tmp liegen geblieben",
          not [n for n in os.listdir(eigen) if n.endswith(".tmp")])
    mtime = os.path.getmtime(ziel)
    time.sleep(0.05)
    check("zweiter Aufruf nimmt die vorhandene",
          G.prg_bereitstellen(pfad, eigen) == ziel
          and os.path.getmtime(ziel) == mtime)
    p = os.path.join(a, "Invade-a-Load.prg")
    open(p, "wb").close()
    check("eine PRG wird direkt genommen", G.prg_bereitstellen(p, eigen) == p)
    kaputt = os.path.join(a, "Invade-a-Load-kaputt.t64")
    with open(kaputt, "wb") as f:
        f.write(b"kein band")
    check("GEGENPROBE: unlesbare T64 -> None",
          G.prg_bereitstellen(kaputt, eigen) is None)

    # -----------------------------------------------------------------------
    print()
    print("Test 4: der Menuepunkt")
    # -----------------------------------------------------------------------
    def kinds():
        offen, raus = [M.system_items()], []
        while offen:
            k = offen.pop()
            raus.extend(e[1] for e in k.get("items", ()) if len(e) > 1)
            offen.extend(k.get("folders", {}).values())
        return raus
    _echt = G.verfuegbar
    try:
        G.verfuegbar = lambda: True
        check("da, wenn Datei und Core da sind", "invade_a_load" in kinds())
        G.verfuegbar = lambda: False
        check("GEGENPROBE: sonst nicht", "invade_a_load" not in kinds())
    finally:
        G.verfuegbar = _echt
    _f, _c = G.finden, G.c64_core_da
    try:
        G.finden = lambda ordner=None: pfad
        G.c64_core_da = lambda ordner=None: False
        check("verfuegbar() braucht den Core", G.verfuegbar() is False)
        G.c64_core_da = lambda ordner=None: True
        check("und die Datei", G.verfuegbar() is True)
        G.finden = lambda ordner=None: None
        check("GEGENPROBE: ohne Datei nein", G.verfuegbar() is False)
    finally:
        G.finden, G.c64_core_da = _f, _c

    # -----------------------------------------------------------------------
    print()
    print("Test 5: der Start")
    # -----------------------------------------------------------------------
    H.set_screen(1280, 720)
    f = H.make_frontend(page=0)
    gestartet = []
    meldungen = []
    f.run_core = lambda mgl, label=None, syskey=None, ra=False: \
        gestartet.append((mgl, label))
    _echt_draw = f.draw
    f.draw = lambda message=None, **k: meldungen.append(message)
    _alt = (G.finden, G.c64_core_da, G.GIMMICK_ORDNER, L.MGL_TMP)
    mgl_datei = os.path.join(TMP, "start.mgl")
    try:
        G.finden = lambda ordner=None: pfad
        G.c64_core_da = lambda ordner=None: True
        G.GIMMICK_ORDNER = eigen
        L.MGL_TMP = mgl_datei
        check("es startet", f._gimmick_starten() is True and len(gestartet)
              == 1, gestartet)
        xml = open(mgl_datei).read()
        check("auf dem C64-Core", "<rbf>_Computer/C64</rbf>" in xml, xml)
        check("als PRG ueber F1 (type f, index 1)",
              'type="f" index="1"' in xml, xml)
        check("mit der bereitgestellten PRG", ziel in xml, xml)
        del gestartet[:]
        G.c64_core_da = lambda ordner=None: False
        check("GEGENPROBE ohne Core: nichts gestartet, Grund unten",
              f._gimmick_starten() is False and not gestartet
              and meldungen[-1] == fm.t("gimmick_fehlt"), meldungen[-1:])
        G.c64_core_da = lambda ordner=None: True
        G.finden = lambda ordner=None: kaputt
        check("GEGENPROBE unlesbare Datei: nichts gestartet",
              f._gimmick_starten() is False and not gestartet
              and meldungen[-1] == fm.t("gimmick_kaputt"))
    finally:
        G.finden, G.c64_core_da, G.GIMMICK_ORDNER, L.MGL_TMP = _alt
        f.draw = _echt_draw
    q = open(H.FRONTEND_PY, encoding="utf-8").read()
    check("der Menuepunkt ist verdrahtet",
          'elif kind == "invade_a_load":' in q)
finally:
    shutil.rmtree(TMP, ignore_errors=True)

print()
if fails:
    print("ROT: %d Pruefung(en) fehlgeschlagen:" % len(fails))
    for f_ in fails:
        print("   - " + f_)
    sys.exit(1)
print("ALLES GRUEN")
