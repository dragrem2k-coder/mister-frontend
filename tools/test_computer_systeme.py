#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Die Computer mit Spielen: C64, Amiga, Amstrad CPC, DOS (Build 330).

NUTZERWUNSCH: "Wie koennen wir die Computer cores, besonders Amiga, C64,
amstrad, ao486 mit spielen noch schoen mit einbinden?" - und: "c64 nutze
ich die one load collection, amiga die amigavision und ao486 die
0mhz-dos".

GEPRUEFT WIRD (alles mit nachgebauten Dateien in einem Temp-Ordner):
  1. Die Systemtabelle: vier neue Systeme mit den Startwerten aus dem
     CONF_STR der Cores; der Amstrad-PCW-Core zaehlt NICHT als CPC.
  2. Die Start-MGL: AmigaVision (ags_boot, Setname Amiga, keine Datei),
     T64 -> PRG ueber F1, ao486 mit Festplatte + CD-Abbild + Reset,
     Diskette + Reset; eine fertige MGL wird unveraendert gestartet;
     alles andere baut write_mgl() wie bisher.
  3. Der Baum: AmigaVision-Listen als Unterordner, 0MHz-MGLs oben, die
     Abbilder, die zu einer MGL gehoeren, nicht doppelt.
  4. Das Einlesen selbst (_scan_games_disk) nimmt das mit.
  5. Amstrad-Disketten: das Verzeichnis (normal und EXTENDED, Daten- und
     Systemformat) ergibt RUN"NAME.
  6. Der Hinweis vor dem Start: nur bei Disketten/Baendern, die nicht
     von selbst losgehen; OK startet, ESC nicht.
  7. Der Computer-Check unter Wartung.

Ausfuehren:
    python3 tools/test_computer_systeme.py
"""
import os
import shutil
import struct
import sys
import tempfile

_HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HIER)

import _harness as H                                     # noqa: E402

fm = H.fm
import fe.computer as C                                  # noqa: E402
import fe.launch as L                                    # noqa: E402
import fe.systems as SYS                                 # noqa: E402
import fe.menu as M                                      # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


def schreiben(pfad, inhalt=b""):
    os.makedirs(os.path.dirname(pfad), exist_ok=True)
    with open(pfad, "wb") as f:
        f.write(inhalt if isinstance(inhalt, bytes) else inhalt.encode())


print(__doc__.strip().split("\n")[0])
print()

TMP = tempfile.mkdtemp(prefix="computer_")
# Build 332: alles, was die Amiga-Wege auf der echten Karte suchen
# wuerden (Laufwerke, Einstellungen, MiSTer.ini), zeigt in den Temp-Ordner.
_ORTE = ("SD_WURZEL", "MEDIA", "MISTER_INI", "CONFIG_ORDNER",
         "COMPUTER_ORDNER")
_ORTE_ALT = {k: getattr(C, k) for k in _ORTE}
C.SD_WURZEL = TMP
C.MEDIA = os.path.join(TMP, "media")
C.MISTER_INI = os.path.join(TMP, "MiSTer.ini")
C.CONFIG_ORDNER = os.path.join(TMP, "config")
C.COMPUTER_ORDNER = os.path.join(TMP, "_Computer")
try:
    # -----------------------------------------------------------------------
    print("Test 1: die Systemtabelle")
    # -----------------------------------------------------------------------
    opt = {e[1]: e for e in SYS.OPTIONAL_GAME_SYSTEMS}
    for key in ("C64", "AMIGA", "AMSTRAD", "AO486"):
        check("%s ist ein optionales System" % key, key in opt)
    check("C64: Modul (OneLoad64) ueber F1",
          opt["C64"][4][".crt"] == (1, "f", 1))
    check("C64: PRG ueber F1", opt["C64"][4][".prg"] == (1, "f", 1))
    check("C64: Diskette in Laufwerk 8 (S0)",
          opt["C64"][4][".d64"] == (1, "s", 0))
    check("Amstrad: DSK an A: (S0), CDT F4, SNA F6",
          opt["AMSTRAD"][4] == {".dsk": (1, "s", 0), ".cdt": (1, "f", 4),
                                ".sna": (1, "f", 6)})
    check("ao486: VHD an IDE 0-0 (S2)", opt["AO486"][4][".vhd"] == (1, "s", 2))
    check("Amiga: ADF an df0 (F0)", opt["AMIGA"][4][".adf"] == (1, "f", 0))
    import fnmatch
    muster = os.path.basename(opt["AMSTRAD"][5])
    check("Amstrad_20260101.rbf zaehlt als CPC-Core",
          fnmatch.fnmatch("Amstrad_20260101.rbf", muster))
    check("GEGENPROBE: Amstrad-PCW_20260101.rbf nicht",
          not fnmatch.fnmatch("Amstrad-PCW_20260101.rbf", muster))
    for key, db in (("C64", "Commodore - 64"), ("AMIGA", "Commodore - Amiga"),
                    ("AMSTRAD", "Amstrad - CPC"), ("AO486", "DOS")):
        check("Cover-Datenbank %s = %s" % (key, db),
              SYS.LIBRETRO_DB.get(key) == db)

    # -----------------------------------------------------------------------
    print()
    print("Test 2: die Start-MGL")
    # -----------------------------------------------------------------------
    av = os.path.join(TMP, "games", "Amiga")
    schreiben(os.path.join(av, "AmigaVision.hdf"))
    os.makedirs(os.path.join(av, "shared"))
    rom = os.path.join(av, "games", "Turrican II")
    xml = C.mgl_inhalt("_Computer/Minimig", rom, 1, C.TYP_AGS, 0)
    boot = os.path.join(av, "shared", "ags_boot")
    check("AmigaVision: ags_boot = Name + Zeilenende",
          open(boot, "rb").read() == b"Turrican II\n")
    check("AmigaVision: Setname Amiga", "<setname>Amiga</setname>" in xml, xml)
    check("AmigaVision: Minimig-Core", "<rbf>_Computer/Minimig</rbf>" in xml)
    check("AmigaVision: KEINE Datei", "<file" not in xml)
    check("keine .tmp liegen geblieben",
          os.listdir(os.path.join(av, "shared")) == ["ags_boot"])
    av2 = os.path.join(TMP, "ohne_shared", "Amiga")
    schreiben(os.path.join(av2, "AmigaVision.hdf"))
    xml2 = C.mgl_inhalt("_Computer/Minimig",
                        os.path.join(av2, "games", "X"), 1, C.TYP_AGS, 0)
    check("eine zweite Installation: ags_boot trotzdem ins Laufwerk "
          "MiSTer: (Build 332), nicht daneben",
          not os.path.exists(os.path.join(av2, "shared"))
          and open(boot, "rb").read() == b"X\n"
          and "<setname>Amiga</setname>" in xml2)
    C.ags_boot_schreiben(av, "Turrican II")
    check("Steuerzeichen im Namen: kein ags_boot",
          C.ags_boot_schreiben(av, "a\nb") is False
          and open(boot, "rb").read() == b"Turrican II\n")

    # T64 -> PRG (Bauweise wie tools/test_gimmick.py)
    def t64(start, inhalt):
        kopf = bytearray(b"C64 tape image file".ljust(32, b"\x00"))
        kopf += struct.pack("<HHH", 0x100, 1, 1) + b"\x00\x00"
        kopf += b"BAND".ljust(24, b" ")
        e = struct.pack("<BBHHHI", 1, 0x82, start, start + len(inhalt), 0,
                        0x60) + b"\x00" * 4 + b"SPIEL".ljust(16, b" ")
        return bytes(kopf + e + inhalt)
    c64 = os.path.join(TMP, "games", "C64")
    t = os.path.join(c64, "Spiel.t64")
    schreiben(t, t64(0x0801, b"\xAA" * 300))
    prg_ordner = os.path.join(TMP, "c64_prg")
    vorher = sorted(os.listdir(c64))
    xml = C.mgl_inhalt("_Computer/C64", t, 1, "f", 1, prg_ordner=prg_ordner)
    prg = os.path.join(prg_ordner, "Spiel.prg")
    check("T64: PRG in den eigenen Ordner",
          open(prg, "rb").read() == b"\x01\x08" + b"\xAA" * 300)
    check("T64: ueber F1 (type f, index 1) mit der PRG",
          'type="f" index="1"' in xml and prg in xml, xml)
    check("neben der T64 hat sich nichts geaendert",
          sorted(os.listdir(c64)) == vorher)
    kaputt = os.path.join(c64, "Kaputt.t64")
    schreiben(kaputt, b"kein band")
    xml = C.mgl_inhalt("_Computer/C64", kaputt, 1, "f", 1,
                       prg_ordner=prg_ordner)
    check("GEGENPROBE unlesbare T64: ins Laufwerk 8 (s 0)",
          'type="s" index="0"' in xml and kaputt in xml, xml)

    # ao486
    ao = os.path.join(TMP, "games", "AO486", "media", "Spiel")
    vhd = os.path.join(ao, "spiel.vhd")
    schreiben(vhd)
    xml = C.mgl_inhalt("_Computer/ao486", vhd, 1, "s", 2)
    check("VHD allein: Festplatte an S2 und Reset",
          'type="s" index="2"' in xml and vhd in xml
          and '<reset delay="1"/>' in xml and xml.count("<file") == 1, xml)
    schreiben(os.path.join(ao, "spiel.chd"))
    xml = C.mgl_inhalt("_Computer/ao486", vhd, 1, "s", 2)
    check("VHD + CD-Abbild daneben: CD an S4",
          'type="s" index="4"' in xml and "spiel.chd" in xml
          and xml.count("<file") == 2, xml)
    disk = os.path.join(ao, "boot.img")
    schreiben(disk)
    xml = C.mgl_inhalt("_Computer/ao486", disk, 1, "s", 0)
    check("Diskette: S0 und Reset, keine CD dazu",
          'type="s" index="0"' in xml and '<reset delay="1"/>' in xml
          and xml.count("<file") == 1, xml)
    check("GEGENPROBE C64-Modul: gewoehnliche MGL (None)",
          C.mgl_inhalt("_Computer/C64", os.path.join(c64, "x.crt"), 1, "f",
                       1) is None)
    check("GEGENPROBE SNES: None",
          C.mgl_inhalt("_Console/SNES", "/x.sfc", 2, "f", 0) is None)

    alt = L.MGL_TMP
    L.MGL_TMP = os.path.join(TMP, "start.mgl")
    try:
        fertig = os.path.join(TMP, "_DOS Games", "Doom.mgl")
        schreiben(fertig, "<mistergamedescription/>")
        check("fertige 0MHz-MGL: unveraendert gestartet",
              L.write_mgl("_Computer/ao486", fertig, 0, C.TYP_MGL, 0)
              == fertig and not os.path.exists(L.MGL_TMP))
        p = L.write_mgl("_Computer/C64", os.path.join(c64, "x.crt"), 1, "f",
                        1)
        q = open(p).read()
        check("C64-Modul: die gewoehnliche MGL von write_mgl()",
              p == L.MGL_TMP and 'type="f" index="1"' in q
              and "x.crt" in q, q)
        p = L.write_mgl("_Computer/ao486", vhd, 1, "s", 2)
        check("ao486 ueber write_mgl(): mit Reset",
              '<reset delay="1"/>' in open(p).read())
    finally:
        L.MGL_TMP = alt

    # -----------------------------------------------------------------------
    print()
    print("Test 3: der Baum")
    # -----------------------------------------------------------------------
    basis = os.path.join(TMP, "games")
    schreiben(os.path.join(av, "listings", "games.txt"),
              "Turrican II\n\nLotus III\nTurrican II\n  \nSpeedball 2\n")
    schreiben(os.path.join(av, "listings", "demos.txt"), "State of the Art\n")
    # Build 334: keine AmigaVision-Liste mehr im Baum (Nutzerwunsch
    # "dann machen wir das anders") - die ADFs bleiben, wie sie sind.
    knoten = {"folders": {}, "items": [("Disk", "game", ("/d.adf", ".adf",
                                        "AMIGA", "r", (1, "f", 0)))]}
    C.knoten_ergaenzen("AMIGA", knoten, "_Computer/Minimig", basen=[basis])
    check("mit ADFs: der Baum bleibt unveraendert (keine AmigaVision-"
          "Ordner)", not knoten["folders"] and len(knoten["items"]) == 1
          and knoten["items"][0][0] == "Disk", knoten)
    nur_av = {"folders": {}, "items": []}
    C.knoten_ergaenzen("AMIGA", nur_av, "r", basen=[basis])
    check("ohne ADF, mit AmigaVision: ein Platzhalter haelt die Kategorie",
          nur_av["items"] == [("AmigaVision", C.TYP_AV_EINTRAG, av)],
          nur_av)
    leer = {"folders": {}, "items": []}
    C.knoten_ergaenzen("AMIGA", leer, "r", basen=[os.path.join(TMP, "x")])
    check("GEGENPROBE ohne AmigaVision: nichts dazu", leer == {
        "folders": {}, "items": []})

    dos = os.path.join(TMP, "_DOS Games")
    schreiben(os.path.join(dos, "Doom 2.mgl"),
              '<mistergamedescription><rbf>_computer/ao486</rbf>'
              '<file delay="0" type="s" index="2" '
              'path="media/Doom 2/DOOM 2.VHD"/><reset delay="1"/>'
              '</mistergamedescription>')
    ao_basis = os.path.join(basis, "AO486")
    doom = os.path.join(ao_basis, "media", "doom 2", "doom 2.vhd")
    schreiben(doom)
    anderes = os.path.join(ao_basis, "media", "Eigenes", "eigen.vhd")
    schreiben(anderes)
    def it(n, p):
        return (n, "game", (p, ".vhd", "AO486", "r", (1, "s", 2)))
    knoten = {"folders": {"media": {"folders": {
        "doom 2": {"folders": {}, "items": [it("doom 2", doom)]},
        "Eigenes": {"folders": {}, "items": [it("eigen", anderes)]}},
        "items": []}}, "items": []}
    C.knoten_ergaenzen("AO486", knoten, "_Computer/ao486", basen=[basis],
                       dos_muster=os.path.join(TMP, "_DOS*"))
    namen = [e[0] for e in knoten["items"]]
    check("0MHz-MGLs oben in der Liste (Doom 2, Doom)",
          namen == ["Doom", "Doom 2"], namen)
    check("als fertige MGL (Typ mgl)",
          knoten["items"][1][2][4] == (0, C.TYP_MGL, 0)
          and knoten["items"][1][2][0] == os.path.join(dos, "Doom 2.mgl"))
    check("das Abbild der MGL ist nicht doppelt da (Gross/Klein egal), "
          "der leere Ordner weg",
          "doom 2" not in knoten["folders"]["media"]["folders"])
    check("GEGENPROBE: ein eigenes Abbild ohne MGL bleibt",
          knoten["folders"]["media"]["folders"]["Eigenes"]["items"][0][0]
          == "eigen")
    k2 = {"folders": {}, "items": [it("x", "/x.vhd")]}
    C.knoten_ergaenzen("AO486", k2, "r", basen=[basis],
                       dos_muster=os.path.join(TMP, "nichts*"))
    check("GEGENPROBE ohne MGLs: unveraendert", [e[0] for e in k2["items"]]
          == ["x"])
    k3 = {"folders": {}, "items": [it("x", "/x.vhd")]}
    C.knoten_ergaenzen("SNES", k3, "r", basen=[basis])
    check("anderes System: unveraendert", len(k3["items"]) == 1
          and not k3["folders"])

    # -----------------------------------------------------------------------
    print()
    print("Test 4: das Einlesen nimmt es mit")
    # -----------------------------------------------------------------------
    import fe.scan as SC
    import fe.paths
    _alt = (fe.paths.GAMES_BASES, SC.optional_core_file, C.DOS_MGL_MUSTER)
    try:
        fe.paths.GAMES_BASES = [basis]
        SC.optional_core_file = lambda muster: "/da.rbf"
        C.DOS_MGL_MUSTER = os.path.join(TMP, "_DOS*")
        cats = SC._scan_games_disk(only_syskeys={"AMIGA", "AO486"})
        nach = {k: n for _d, n, k in cats}
        check("Amiga-Kategorie da (AmigaVision-Platzhalter, keine ADF)",
              [e[1] for e in nach.get("AMIGA", {}).get("items", [])]
              == [C.TYP_AV_EINTRAG],
              nach.get("AMIGA"))
        check("und sie heisst auf der Hauptseite \"Amiga 500\"",
              [d for d, _n, k in cats if k == "AMIGA"] == ["Amiga 500"])
        check("DOS-Kategorie mit den MGLs oben",
              [e[0] for e in nach.get("AO486", {}).get("items", [])][:2]
              == ["Doom", "Doom 2"])
        q = H.nur_code(H.koerper(open(SC.__file__, encoding="utf-8").read(),
                                 "_scan_games_disk"))
        check("der Aufruf steht im Einlesen",
              "_computer.knoten_ergaenzen(syskey, sys_node, rbf)" in q)
        sig = SC._games_signature()
        check("die Signatur kennt den MGL-Ordner und die AmigaVision-Liste",
              "dos:_DOS Games" in str(sig) and "ags:games.txt" in str(sig))
    finally:
        fe.paths.GAMES_BASES, SC.optional_core_file, C.DOS_MGL_MUSTER = _alt

    # -----------------------------------------------------------------------
    print()
    print("Test 5: Amstrad-Disketten")
    # -----------------------------------------------------------------------
    def eintrag(user, name, ext, extent=0, versteckt=False):
        n = name.ljust(8).encode()
        e = bytearray(ext.ljust(3).encode())
        if versteckt:
            e[1] |= 0x80
        return bytes([user]) + n + bytes(e) + bytes([extent]) + b"\x00" * 19

    VERZ = (eintrag(0, "DISC", "BAS") + eintrag(0, "GAME", "BIN")
            + eintrag(0, "GAME", "BIN", extent=1)
            + eintrag(0xE5, "GELOESCH", "BAS")
            + eintrag(1, "ANDERER", "BAS")
            + eintrag(0, "LOADER", "") + eintrag(0, "README", "TXT")
            + eintrag(0, "MENU", "BAS", versteckt=True))

    def dsk(erweitert=False, erste_id=0xC1, spuren=3, dir_spur=0):
        kopf = bytearray(256)
        kopf[:34] = (b"EXTENDED CPC DSK File\r\nDisk-Info\r\n" if erweitert
                     else b"MV - CPCEMU Disk-File\r\nDisk-Info\r\n")
        kopf[0x30] = spuren
        kopf[0x31] = 1
        groesse = 256 + 9 * 512
        if erweitert:
            for i in range(spuren):
                kopf[0x34 + i] = groesse // 256
        else:
            kopf[0x32:0x34] = struct.pack("<H", groesse)
        raus = bytes(kopf)
        for spur in range(spuren):
            ti = bytearray(256)
            ti[:12] = b"Track-Info\r\n"
            ti[0x10] = spur
            ti[0x14] = 2
            ti[0x15] = 9
            for s_ in range(9):
                info = bytes([spur, 0, erste_id + s_, 2, 0, 0]) + \
                    struct.pack("<H", 512)
                ti[0x18 + 8 * s_:0x20 + 8 * s_] = info
            daten = bytearray(b"\xE5" * (9 * 512))
            if spur == dir_spur:
                daten[:len(VERZ)] = VERZ
            raus += bytes(ti) + bytes(daten)
        return raus

    erwartet = ["DISC", "MENU", "GAME", "LOADER"]
    check("Standard-DSK, Datenformat: BAS zuerst, dann BIN/ohne Endung",
          C.cpc_dsk_programme(dsk()) == erwartet, C.cpc_dsk_programme(dsk()))
    check("EXTENDED-DSK", C.cpc_dsk_programme(dsk(True)) == erwartet,
          C.cpc_dsk_programme(dsk(True)))
    check("Systemformat (Spur 2, Sektor 41)",
          C.cpc_dsk_programme(dsk(erste_id=0x41, dir_spur=2)) == erwartet)
    check("GEGENPROBE: geloescht, Benutzer 1, TXT fehlen",
          not {"GELOESCH", "ANDERER", "README"}
          & set(C.cpc_dsk_programme(dsk())))
    check("ein Programm aus zwei Teilen steht einmal da",
          C.cpc_dsk_programme(dsk()).count("GAME") == 1)
    check("GEGENPROBE: keine DSK -> leer",
          C.cpc_dsk_programme(b"\x00" * 4096) == [])
    check("kaputt abgeschnitten -> kein Absturz",
          isinstance(C.cpc_dsk_programme(dsk()[:600]), list))

    # -----------------------------------------------------------------------
    print()
    print("Test 6: der Hinweis vor dem Start")
    # -----------------------------------------------------------------------
    h = C.starthinweis("C64", ".d64", "/x.d64")
    check("C64-Diskette: LOAD-Hinweis",
          h == ("hinweis_c64_titel", [("hinweis_c64_disk", ())]))
    check("GEGENPROBE C64-Modul und PRG: kein Hinweis",
          C.starthinweis("C64", ".crt", "/x") is None
          and C.starthinweis("C64", ".prg", "/x") is None)
    check("C64-Band: Hinweis",
          C.starthinweis("C64", ".TAP", "/x")[1][0][0] == "hinweis_c64_tap")
    h = C.starthinweis("AMSTRAD", ".dsk", "/x", lesen=lambda p: dsk())
    check("CPC-Diskette: RUN\"DISC zuerst",
          h[0] == "hinweis_cpc_titel"
          and h[1][0] == ("hinweis_cpc_run", ('RUN"DISC',))
          and len(h[1]) == 4, h)

    def _fehler(_p):
        raise OSError("weg")
    h = C.starthinweis("AMSTRAD", ".dsk", "/x", lesen=_fehler)
    check("unlesbare DSK: CAT-Hinweis", h[1] == [("hinweis_cpc_cat", ())])
    check("CPC-Band: |TAPE-Hinweis",
          C.starthinweis("AMSTRAD", ".cdt", "/x")[1][0][0]
          == "hinweis_cpc_tape")
    check("GEGENPROBE Snapshot, SNES, DOS: kein Hinweis",
          C.starthinweis("AMSTRAD", ".sna", "/x") is None
          and C.starthinweis("SNES", ".sfc", "/x") is None
          and C.starthinweis("AO486", ".mgl", "/x") is None)
    for k in ("hinweis_c64_titel", "hinweis_c64_disk", "hinweis_c64_tap",
              "hinweis_cpc_titel", "hinweis_cpc_run", "hinweis_cpc_cat",
              "hinweis_cpc_tape", "hinweis_tastatur", "hinweis_tasten"):
        check("Text %s uebersetzt" % k, fm.t(k) != k)

    for (w, hh) in ((1920, 1080), (320, 240)):
        H.set_screen(w, hh)
        f = H.make_frontend(page=0)
        bilder = []
        texte = []
        echt = f.fb.text
        f.fb.text = lambda x, y, txt, *a, **k: (texte.append(txt),
                                                echt(x, y, txt, *a, **k))
        f.fb.flip = lambda *a, **k: bilder.append(1)
        rest = ["down", "ok"]

        def _taste(timeout=None):
            # Keine Taste mehr uebrig: abbrechen statt ewig zu warten -
            # sonst haengt der Test, wenn der Bildschirm eine Taste
            # nicht annimmt, statt rot zu werden.
            if not rest:
                raise RuntimeError("Bildschirm wartet weiter")
            return rest.pop(0)
        f.inp.read_action = _taste
        check("%dx%d: OK startet" % (w, hh),
              f._computer_hinweis("C64", ".d64", "/x.d64") is True
              and len(bilder) == 1)
        check("%dx%d: der Befehl steht im Bild" % (w, hh),
              fm.t("hinweis_c64_disk") in texte, texte[:4])
        for taste in ("exit", "back"):
            rest = [taste]
            try:
                erg = f._computer_hinweis("AMSTRAD", ".cdt", "/x")
            except RuntimeError as e:
                erg = e
            check("%dx%d: %s startet nicht" % (w, hh, taste), erg is False,
                  erg)
        del bilder[:]
        check("%dx%d: GEGENPROBE ohne Hinweis: sofort, ohne Bild" % (w, hh),
              f._computer_hinweis("C64", ".crt", "/x") is True
              and not bilder)
    q = open(H.FRONTEND_PY, encoding="utf-8").read()
    for marke, was in (("record_recent(label, arg)", "Spielliste"),
                       ("record_recent(name, rand_arg)", "Zufallsstart")):
        i = q.find(marke)
        vor = q[max(0, i - 600):i]
        check("%s: Hinweis vor dem Start" % was,
              i > 0 and "self._computer_hinweis(syskey, ext, rom)" in vor)

    # -----------------------------------------------------------------------
    print()
    print("Test 7: der Computer-Check")
    # -----------------------------------------------------------------------
    kerne = os.path.join(TMP, "_Computer")
    schreiben(os.path.join(kerne, "C64_20260101.rbf"))
    schreiben(os.path.join(kerne, "Amstrad-PCW_20260101.rbf"))
    schreiben(os.path.join(kerne, "Minimig_20260101.rbf"))
    schreiben(os.path.join(ao_basis, "boot0.rom"))
    schreiben(os.path.join(c64, "Spiel.crt"))

    def ergebnis():
        return dict(C.computer_check([basis], kerne,
                                     os.path.join(TMP, "_DOS*")))
    e = ergebnis()
    check("C64: Core mit Namen gefunden",
          (True, "check_core", ("C64_20260101.rbf",)) in e["Commodore 64"])
    check("C64: 3 Spieldateien (crt und zwei t64)",
          (None, "check_spiele", (3,)) in e["Commodore 64"],
          e["Commodore 64"])
    check("GEGENPROBE Amstrad: der PCW-Core zaehlt nicht",
          e["Amstrad CPC"][0][0] is False)
    check("Amiga: AmigaVision gefunden",
          (True, "check_amigavision", (av,)) in e["Amiga"], e["Amiga"])
    check("GEGENPROBE ao486: nur boot0.rom -> fehlt, kein Core",
          (False, "check_ao486_roms", ()) in e["DOS (ao486)"]
          and e["DOS (ao486)"][0][0] is False)
    schreiben(os.path.join(ao_basis, "boot1.rom"))
    schreiben(os.path.join(kerne, "ao486_20260101.rbf"))
    e = ergebnis()
    check("ao486: beide ROMs und Core da, 2 MGLs",
          (True, "check_ao486_roms", ()) in e["DOS (ao486)"]
          and e["DOS (ao486)"][0][0] is True
          and (None, "check_dos_mgls", (2,)) in e["DOS (ao486)"])
    e2 = dict(C.computer_check([os.path.join(TMP, "leer")], kerne,
                               os.path.join(TMP, "nichts*")))
    check("GEGENPROBE ohne AmigaVision: als fehlend",
          (False, "check_amigavision_fehlt", ()) in e2["Amiga"])
    for name, zeilen in C.computer_check([basis], kerne):
        for _ok, k, a in zeilen:
            if fm.t(k, *a) == k:
                check("Text %s uebersetzt" % k, False)

    for (w, hh) in ((1920, 1080), (320, 240)):
        H.set_screen(w, hh)
        f = H.make_frontend(page=0)
        texte = []
        echt = f.fb.text
        f.fb.text = lambda x, y, txt, *a, **k: (texte.append((y, txt)),
                                                echt(x, y, txt, *a, **k))
        f.fb.flip = lambda *a, **k: None
        f.computer_check_bildschirm(C.computer_check([basis], kerne))
        s = fm._skala(f.fb.width, f.fb.height)
        maxc = (f.fb.width - 2 * (f.fb.width * fm.OVERSCAN_X // 100)) \
            // (8 * s)
        check("%dx%d: alle vier Computer im Bild" % (w, hh) if w > 320 else
              "%dx%d: mindestens die ersten beiden im Bild" % (w, hh),
              all(any(n == t_ for _y, t_ in texte) for n in
                  (("Commodore 64", "Amiga", "Amstrad CPC", "DOS (ao486)")
                   if w > 320 else ("Commodore 64", "Amiga"))))
        check("%dx%d: keine Zeile breiter als der Schirm" % (w, hh),
              all(len(t_) <= max(8, maxc) for _y, t_ in texte
                  if t_ != fm.t("ra_bilanz_hinweis")
                  and t_ != fm.t("computer_check_titel")),
              [t_ for _y, t_ in texte if len(t_) > maxc][:2])

    def kinds():
        offen, raus = [M.system_items()], []
        while offen:
            k = offen.pop()
            raus.extend(e[1] for e in k.get("items", ()) if len(e) > 1)
            offen.extend(k.get("folders", {}).values())
        return raus
    check("der Menuepunkt steht unter System", "computer_check" in kinds())
    check("und ist verdrahtet", 'elif kind == "computer_check":' in q)
finally:
    for _k, _v in _ORTE_ALT.items():
        setattr(C, _k, _v)
    shutil.rmtree(TMP, ignore_errors=True)

print()
if fails:
    print("ROT: %d Pruefung(en) fehlgeschlagen:" % len(fails))
    for f_ in fails:
        print("   - " + f_)
    sys.exit(1)
print("ALLES GRUEN")
