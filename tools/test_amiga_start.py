#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Amiga startet mit den richtigen Einstellungen, 0MHz meldet fehlende Dateien (Build 331).

NUTZERMELDUNG nach Build 330: "amiga spiele starten nicht da lande ich
einfach bei der kickrom anzeige obwohl ich ein kickrom drauf habe" - und
"bei der 0mhz collection muss ich die spiele entpacken damit die
starten?". Dazu Geraetefotos und Abzeichen fuer die vier Computer.

GEPRUEFT WIRD (alles mit nachgebauten Dateien):
  1. Die Minimig-Einstellungsdatei wird gelesen wie MiSTer sie schreibt
     (Kennung, Kickstart, Festplatten); Unsinn ergibt None.
  2. Die Minimig-MGLs in _Computer: nur Minimig, nur ohne <file>, das
     Setname-Element woertlich.
  3. AmigaVision startet mit dem Setnamen der MGL, deren Einstellung
     AmigaVision.hdf einhaengt - nicht fest mit "Amiga".
  4. Eine ADF startet mit einer Einstellung, deren Kickstart da ist;
     eine eigene Minimig.cfg hat Vorrang; ohne alles wie bisher.
  5. write_mgl(): ein Fehler im Sonderfall wird protokolliert, und ein
     AmigaVision-Eintrag faellt NIE auf type="ags" zurueck.
  6. 0MHz: fehlende Abbilder werden erkannt (auch "ao486" klein), der
     Hinweis vor dem Start kommt, die Tastatur-Zeile nicht.
  7. Der Computer-Check zeigt Einstellungsdatei, Kickstart, Festplatte.
  8. Die Bilder: vier Abzeichen 320x420 und vier Fotos 420x320 auf
     C_PANEL.
  9. (Build 332) ags_boot landet im Laufwerk MiSTer: - gesucht wie Main
     (USB vor NAS vor Karte, shared_folder aus MiSTer.ini, same_dir) -,
     mit den Bytes der Liste; der Check meldet eine nicht eingetragene
     AmigaVision.hdf.
 10. (Build 333) Start- und Anzeigenamen - nur noch fuer alte Eintraege.
 11. (Build 334) "Amiga 500": beim Betreten AmigaVision oder ADF; ohne
     ADF gleich AmigaVision; ohne AmigaVision wie jedes System.

Ausfuehren:
    python3 tools/test_amiga_start.py
"""
import os
import shutil
import struct
import sys
import tempfile
import zlib

_HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HIER)

import _harness as H                                     # noqa: E402

fm = H.fm
import fe.computer as C                                  # noqa: E402
import fe.launch as L                                    # noqa: E402

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


def cfg(kick, hdf=(), kennung=b"MNMGCFG0"):
    """Eine Minimig-Einstellungsdatei, aufgebaut wie mm_configTYPE."""
    d = bytearray(5216)
    d[0:8] = kennung
    k = kick.encode()
    d[12:12 + len(k)] = k
    for i, h in enumerate(hdf):
        o = 1046 + i * 1026
        d[o] = 1
        hb = h.encode()
        d[o + 2:o + 2 + len(hb)] = hb
    return bytes(d)


def mgl(rbf, setname=None, datei=None):
    t = "<mistergamedescription>\n    <rbf>%s</rbf>\n" % rbf
    if setname:
        t += "    <setname>%s</setname>\n" % setname
    if datei:
        t += '    <file delay="1" type="f" index="0" path="%s"/>\n' % datei
    return t + "</mistergamedescription>\n"


print(__doc__.strip().split("\n")[0])
print()

TMP = tempfile.mkdtemp(prefix="amiga_")
_alt = (C.CONFIG_ORDNER, C.SD_WURZEL, C.COMPUTER_ORDNER, L.MGL_TMP,
        C.MEDIA, C.MISTER_INI)
try:
    WURZEL = os.path.join(TMP, "fat")
    KONF = os.path.join(WURZEL, "config")
    COMP = os.path.join(WURZEL, "_Computer")
    C.CONFIG_ORDNER, C.SD_WURZEL, C.COMPUTER_ORDNER = KONF, WURZEL, COMP
    MEDIA = os.path.join(TMP, "media")
    C.MEDIA, C.MISTER_INI = MEDIA, os.path.join(WURZEL, "MiSTer.ini")
    L.MGL_TMP = os.path.join(TMP, "start.mgl")

    # -----------------------------------------------------------------------
    print("Test 1: die Einstellungsdatei")
    # -----------------------------------------------------------------------
    p = os.path.join(TMP, "a.cfg")
    schreiben(p, cfg("games/Amiga/AmigaVision.rom",
                     ["games/Amiga/AmigaVision.hdf",
                      "games/Amiga/AmigaVision-Saves.hdf"]))
    e = C.minimig_cfg_lesen(p)
    check("Kickstart gelesen", e and e["kickstart"]
          == "games/Amiga/AmigaVision.rom", e)
    check("beide Festplatten gelesen", e and e["hdf"]
          == ["games/Amiga/AmigaVision.hdf",
              "games/Amiga/AmigaVision-Saves.hdf"])
    schreiben(p, cfg("x.rom", kennung=b"FALSCH00"))
    check("GEGENPROBE fremde Kennung -> None", C.minimig_cfg_lesen(p) is None)
    schreiben(p, b"MNMGCFG0" + b"\0" * 100)
    check("GEGENPROBE zu kurz -> None", C.minimig_cfg_lesen(p) is None)
    check("fehlt -> None", C.minimig_cfg_lesen(p + "x") is None)
    check("relativer Pfad gegen die Wurzel der Karte",
          C.mister_pfad("games/x.rom") == os.path.join(WURZEL, "games/x.rom"))
    check("absoluter bleibt", C.mister_pfad("/media/usb0/x") == "/media/usb0/x")

    # -----------------------------------------------------------------------
    print()
    print("Test 2: die Minimig-MGLs")
    # -----------------------------------------------------------------------
    schreiben(os.path.join(COMP, "Amiga.mgl"),
              mgl("_computer/minimig", "Amiga"))
    schreiben(os.path.join(COMP, "Amiga 500.mgl"),
              mgl("_computer/minimig", "Amiga500"))
    schreiben(os.path.join(COMP, "C64 Spiel.mgl"), mgl("_computer/c64", "X"))
    schreiben(os.path.join(COMP, "Mit Diskette.mgl"),
              mgl("_computer/minimig", "D", "x.adf"))
    m = C.minimig_mgls()
    check("zwei Minimig-MGLs, nach Name",
          [os.path.basename(x[0]) for x in m] == ["Amiga 500.mgl",
                                                  "Amiga.mgl"], m)
    check("Setname-Element woertlich",
          m and m[1][2] == "<setname>Amiga</setname>" and m[1][3] == "Amiga")
    check("GEGENPROBE: C64 und MGL mit <file> nicht dabei",
          not any("C64" in x[0] or "Diskette" in x[0] for x in m))

    # -----------------------------------------------------------------------
    print()
    print("Test 3: AmigaVision startet mit der richtigen Einstellung")
    # -----------------------------------------------------------------------
    r = C.amigavision_start()
    check("ohne Einstellungsdatei: Vorgabe Amiga, Herkunft leer",
          r[2] == "Amiga" and r[3] == "", r)
    schreiben(os.path.join(KONF, "Amiga.cfg"),
              cfg("games/Amiga/AmigaVision.rom",
                  ["games/Amiga/AmigaVision.hdf"]))
    r = C.amigavision_start()
    check("aus _Computer/Amiga.mgl", r[3] == os.path.join(COMP, "Amiga.mgl")
          and r[0] == "_computer/minimig", r)
    # Eine andere Installation: die AmigaVision-Einstellung heisst anders.
    os.remove(os.path.join(KONF, "Amiga.cfg"))
    schreiben(os.path.join(COMP, "AGS Neu.mgl"),
              mgl("_Computer/Minimig", "AGSNeu"))
    schreiben(os.path.join(KONF, "AGSNeu.cfg"),
              cfg("games/Amiga/k.rom", ["games/Amiga/MegaAGS.hdf"]))
    r = C.amigavision_start()
    check("anderer Setname wird gefunden (MegaAGS.hdf)", r[2] == "AGSNeu", r)
    schreiben(os.path.join(KONF, "Amiga.cfg"),
              cfg("games/Amiga/AmigaVision.rom",
                  ["games/Amiga/AmigaVision.hdf"]))
    check("zwei passende: Amiga zuerst", C.amigavision_start()[2] == "Amiga")
    os.remove(os.path.join(COMP, "AGS Neu.mgl"))
    os.remove(os.path.join(COMP, "Amiga.mgl"))
    os.remove(os.path.join(KONF, "Amiga.cfg"))
    schreiben(os.path.join(KONF, "AGSNeu1.cfg"),
              cfg("k.rom", ["games/Amiga/AmigaVision.hdf"]))
    r = C.amigavision_start()
    check("ohne MGL: aus den Einstellungsdateien, Platz 1 uebergangen",
          r[2] == "AGSNeu" and r[1] == "<setname>AGSNeu</setname>", r)
    os.remove(os.path.join(KONF, "AGSNeu1.cfg"))
    os.remove(os.path.join(KONF, "AGSNeu.cfg"))
    schreiben(os.path.join(COMP, "Amiga.mgl"),
              mgl("_computer/minimig", "Amiga"))
    schreiben(os.path.join(KONF, "Amiga.cfg"),
              cfg("games/Amiga/AmigaVision.rom",
                  ["games/Amiga/AmigaVision.hdf",
                   "games/Amiga/AmigaVision-Saves.hdf"]))

    av = os.path.join(WURZEL, "games", "Amiga")
    schreiben(os.path.join(av, "AmigaVision.hdf"))
    os.makedirs(os.path.join(av, "shared"))
    xml = C.mgl_inhalt("_Computer/Minimig",
                       os.path.join(av, "games", "Turrican"), 1, C.TYP_AGS, 0)
    check("Start-MGL: rbf und Setname aus AmigaVisions MGL",
          "<rbf>_computer/minimig</rbf>" in xml
          and "<setname>Amiga</setname>" in xml and "<file" not in xml, xml)
    check("ags_boot geschrieben",
          open(os.path.join(av, "shared", "ags_boot")).read() == "Turrican\n")

    # -----------------------------------------------------------------------
    print()
    print("Test 4: eine ADF")
    # -----------------------------------------------------------------------
    adf = os.path.join(av, "Spiel.adf")
    check("Kickstart von Amiga500 fehlt, AmigaVisions auch: Minimig wie "
          "bisher", C.amiga_diskette_start() is None)
    schreiben(os.path.join(WURZEL, "games/Amiga/AmigaVision.rom"))
    check("nur AmigaVisions Kickstart da: mit Einstellung Amiga",
          C.amiga_diskette_start() == ("<setname>Amiga</setname>", "Amiga"))
    schreiben(os.path.join(KONF, "Amiga500.cfg"), cfg("games/Amiga500/1.3.rom"))
    check("GEGENPROBE: Amiga500 ohne seinen Kickstart zaehlt nicht",
          C.amiga_diskette_start()[1] == "Amiga")
    schreiben(os.path.join(WURZEL, "games/Amiga500/1.3.rom"))
    check("Amiga500 mit Kickstart: zuerst",
          C.amiga_diskette_start() == ("<setname>Amiga500</setname>",
                                       "Amiga500"))
    xml = C.mgl_inhalt("_Computer/Minimig", adf, 1, "f", 0)
    check("Start-MGL der ADF: Setname + Diskette an df0",
          "<setname>Amiga500</setname>" in xml
          and 'type="f" index="0"' in xml and "Spiel.adf" in xml, xml)
    schreiben(os.path.join(KONF, "Minimig.cfg"), cfg("games/Amiga/KICK.ROM"))
    check("GEGENPROBE eigene Minimig.cfg ohne Kickstart: zaehlt nicht",
          C.amiga_diskette_start()[1] == "Amiga500")
    schreiben(os.path.join(WURZEL, "games/Amiga/KICK.ROM"))
    check("eigene Minimig.cfg mit Kickstart: hat Vorrang (None)",
          C.amiga_diskette_start() is None
          and C.mgl_inhalt("_Computer/Minimig", adf, 1, "f", 0) is None)
    os.remove(os.path.join(KONF, "Minimig.cfg"))
    check("GEGENPROBE andere Systeme unberuehrt",
          C.mgl_inhalt("_Console/SNES", "/x.sfc", 2, "f", 0) is None)

    # -----------------------------------------------------------------------
    print()
    print("Test 5: write_mgl() bei einem Fehler")
    # -----------------------------------------------------------------------
    import fe.log
    zeilen = []
    _echt_log, _echt_inhalt = fe.log.LOG, C.mgl_inhalt
    try:
        fe.log.LOG = lambda t: zeilen.append(t)

        def _kaputt(*a, **k):
            raise ValueError("absichtlich")
        C.mgl_inhalt = _kaputt
        p = L.write_mgl("_Computer/Minimig", "/x/games/Turrican", 1, "ags", 0)
        q = open(p).read()
        check("AmigaVision faellt nicht auf type=\"ags\" zurueck",
              'type="ags"' not in q and "<setname>Amiga</setname>" in q, q)
        check("der Fehler steht im Protokoll",
              any("absichtlich" in z for z in zeilen), zeilen)
        p = L.write_mgl("_Console/SNES", "/x.sfc", 2, "f", 0)
        check("andere Systeme: die gewoehnliche MGL",
              'type="f" index="0"' in open(p).read())
        C.mgl_inhalt = _echt_inhalt
        del zeilen[:]
        L.write_mgl("_Computer/Minimig", adf, 1, "f", 0)
        check("die gestartete Sonder-MGL steht im Protokoll",
              any(z.startswith("write_mgl: <mistergamedescription>")
                  for z in zeilen), zeilen)
    finally:
        fe.log.LOG, C.mgl_inhalt = _echt_log, _echt_inhalt

    # -----------------------------------------------------------------------
    print()
    print("Test 6: 0MHz ohne entpackte Dateien")
    # -----------------------------------------------------------------------
    basis = os.path.join(WURZEL, "games")
    dos = os.path.join(TMP, "_DOS Games")
    schreiben(os.path.join(dos, "Doom.mgl"),
              '<mistergamedescription><rbf>_computer/ao486</rbf>'
              '<file delay="0" type="s" index="2" path="media/doom/doom.vhd"/>'
              '</mistergamedescription>')
    fehl = C.dos_mgl_fehlend(os.path.join(dos, "Doom.mgl"), [basis])
    check("ohne Abbild: fehlt", fehl == ["media/doom/doom.vhd"], fehl)
    schreiben(os.path.join(basis, "ao486", "media", "doom", "doom.vhd"))
    check("in games/ao486 (klein, wie im ZIP): gefunden",
          C.dos_mgl_fehlend(os.path.join(dos, "Doom.mgl"), [basis]) == [])
    _b = C._basen
    try:
        C._basen = lambda: [os.path.join(TMP, "leer")]
        h = C.starthinweis("AO486", ".mgl", os.path.join(dos, "Doom.mgl"))
        check("Hinweis vor dem Start, wenn es fehlt",
              h and h[0] == "hinweis_dos_titel"
              and h[1][0] == ("hinweis_dos_fehlt", ("media/doom/doom.vhd",)),
              h)
        C._basen = lambda: [basis]
        check("GEGENPROBE alles da: kein Hinweis",
              C.starthinweis("AO486", ".mgl",
                             os.path.join(dos, "Doom.mgl")) is None)
        for k in ("hinweis_dos_titel", "hinweis_dos_fehlt", "hinweis_dos_zip",
                  "hinweis_tasten_trotzdem"):
            check("Text %s uebersetzt" % k, fm.t(k) != k)

        C._basen = lambda: [os.path.join(TMP, "leer")]
        H.set_screen(1280, 720)
        f = H.make_frontend(page=0)
        texte = []
        echt = f.fb.text
        f.fb.text = lambda x, y, txt, *a, **k: (texte.append(txt),
                                                echt(x, y, txt, *a, **k))
        f.fb.flip = lambda *a, **k: None
        rest = ["ok"]

        def _taste(timeout=None):
            if not rest:
                raise RuntimeError("Bildschirm wartet weiter")
            return rest.pop(0)
        f.inp.read_action = _taste
        check("OK startet trotzdem",
              f._computer_hinweis("AO486", ".mgl",
                                  os.path.join(dos, "Doom.mgl")) is True)
        check("die Tastatur-Zeile steht NICHT da",
              fm.t("hinweis_tastatur") not in texte)
        check("unten: trotzdem starten",
              any(fm.t("hinweis_tasten_trotzdem") in t_ for t_ in texte))
        del texte[:]
        rest = ["ok"]
        f._computer_hinweis("C64", ".d64", "/x.d64")
        check("GEGENPROBE C64-Diskette: Tastatur-Zeile steht da",
              fm.t("hinweis_tastatur") in texte)
    finally:
        C._basen = _b

    # -----------------------------------------------------------------------
    print()
    print("Test 7: der Computer-Check")
    # -----------------------------------------------------------------------
    os.remove(os.path.join(WURZEL, "games/Amiga/AmigaVision.rom"))
    erg = dict(C.computer_check([basis], COMP, os.path.join(TMP, "_DOS*")))
    am = erg["Amiga"]
    check("Einstellungsdatei da", (True, "check_av_cfg",
                                   ("config/Amiga.cfg",)) in am, am)
    check("GEGENPROBE: der Kickstart fehlt - genau das Kickstart-Bild",
          (False, "check_av_kick", ("games/Amiga/AmigaVision.rom",)) in am)
    check("Festplatte da, Speicherstand-Platte fehlt",
          (True, "check_av_hdf", ("games/Amiga/AmigaVision.hdf",)) in am
          and (False, "check_av_hdf",
               ("games/Amiga/AmigaVision-Saves.hdf",)) in am)
    check("ADF-Einstellung genannt",
          (None, "check_adf_mit", ("Amiga500",)) in am)
    schreiben(os.path.join(WURZEL, "games/Amiga/AmigaVision.rom"))
    am = dict(C.computer_check([basis], COMP))["Amiga"]
    check("Kickstart da -> gruen",
          (True, "check_av_kick", ("games/Amiga/AmigaVision.rom",)) in am)
    schreiben(os.path.join(dos, "Fehlt.mgl"),
              '<file type="s" index="2" path="media/weg/weg.vhd"/>')
    erg = dict(C.computer_check([basis], COMP, os.path.join(TMP, "_DOS*")))
    check("DOS: 1 von 2 ohne Spieldateien",
          (False, "check_dos_fehlt", (1,)) in erg["DOS (ao486)"],
          erg["DOS (ao486)"])
    for name, zl in erg.items():
        for _ok, k, a in zl:
            if fm.t(k, *a) == k:
                check("Text %s uebersetzt" % k, False)

    # -----------------------------------------------------------------------
    print()
    print("Test 9: ags_boot landet im Laufwerk MiSTer: (Build 332)")
    # -----------------------------------------------------------------------
    # NUTZERMELDUNG: "wenn ich jetzt ueber das frontend ein spiel starte
    # lande ich erst in der amigavision frontend und suche mir dort das
    # spiel nochmal aus" - ags_boot lag nicht dort, wo der Amiga sucht.
    check("ohne USB/NAS: Heimatordner games/Amiga auf der Karte",
          C.heimatordner("Amiga") == os.path.join(WURZEL, "games", "Amiga"))
    usb = os.path.join(MEDIA, "usb1", "games", "Amiga")
    os.makedirs(usb)
    check("ein USB-Laufwerk mit games/Amiga geht vor (wie in Main)",
          C.heimatordner("Amiga") == usb, C.heimatordner("Amiga"))
    os.makedirs(os.path.join(MEDIA, "usb0", "Amiga"))
    check("usb0 vor usb1, und dort <kern> vor games/<kern>",
          C.heimatordner("Amiga") == os.path.join(MEDIA, "usb0", "Amiga"))
    shutil.rmtree(os.path.join(MEDIA, "usb0"))
    cifs = os.path.join(WURZEL, "cifs", "games", "Amiga")
    os.makedirs(cifs)
    check("GEGENPROBE: USB geht auch vor dem NAS (cifs)",
          C.heimatordner("Amiga") == usb)
    shutil.rmtree(os.path.join(MEDIA, "usb1"))
    check("ohne USB: das NAS vor der Karte",
          C.heimatordner("Amiga") == cifs)

    # der Fall selbst: AmigaVision auf der Karte, games/Amiga auf dem NAS
    for f_ in os.listdir(os.path.join(av, "shared")):
        os.remove(os.path.join(av, "shared", f_))
    xml = C.mgl_inhalt("_Computer/Minimig",
                       os.path.join(av, "games", "Lotus"), 1, C.TYP_AGS, 0)
    check("ags_boot im MiSTer:-Laufwerk auf dem NAS",
          open(os.path.join(cifs, "shared", "ags_boot")).read() == "Lotus\n")
    check("GEGENPROBE: NICHT mehr neben AmigaVision.hdf (dort sieht der "
          "Amiga sie nie)",
          not os.path.exists(os.path.join(av, "shared", "ags_boot")))
    shutil.rmtree(os.path.join(WURZEL, "cifs"))

    # MiSTer.ini: shared_folder - auch im mehrzeiligen AmigaVision-Kopf
    schreiben(C.MISTER_INI, "[MiSTer]\nvideo_mode=8\n"
              "[SNES]\nshared_folder=/falsch\n"
              "[Amiga\n+Amiga500\n+AmigaCD32]\n"
              "shared_folder=/media/usb0/teilen ; Kommentar\n")
    check("shared_folder aus dem mehrzeiligen [Amiga+...]-Kopf",
          C.mister_laufwerk("Amiga") == "/media/usb0/teilen",
          C.mister_laufwerk("Amiga"))
    check("GEGENPROBE: der [SNES]-Abschnitt gilt nicht fuer Amiga",
          C._ini_wert("shared_folder", "Amiga500") == "/media/usb0/teilen"
          and C._ini_wert("shared_folder", "NES") is None)
    schreiben(C.MISTER_INI, "[MiSTer]\nshared_folder=geteilt\n")
    check("relativer Wert: unter dem Heimatordner",
          C.mister_laufwerk("Amiga")
          == os.path.join(WURZEL, "games", "Amiga", "geteilt"))
    os.remove(C.MISTER_INI)
    check("ohne Eintrag: <Heimatordner>/shared",
          C.mister_laufwerk("Amiga")
          == os.path.join(WURZEL, "games", "Amiga", "shared"))

    # same_dir="1": Heimatordner bleibt der des Minimig
    schreiben(os.path.join(COMP, "Amiga.mgl"),
              '<mistergamedescription><rbf>_computer/minimig</rbf>'
              '<setname same_dir="1">AGSX</setname>'
              '</mistergamedescription>')
    schreiben(os.path.join(KONF, "AGSX.cfg"),
              cfg("games/Amiga/AmigaVision.rom",
                  ["games/Amiga/AmigaVision.hdf"]))
    os.makedirs(os.path.join(WURZEL, "games", "AGSX"))
    C.mgl_inhalt("_Computer/Minimig", os.path.join(av, "games", "Elite"), 1,
                 C.TYP_AGS, 0)
    check("same_dir=\"1\": ags_boot in games/Amiga/shared",
          open(os.path.join(av, "shared", "ags_boot")).read() == "Elite\n")
    check("GEGENPROBE: nicht in games/AGSX",
          not os.path.exists(os.path.join(WURZEL, "games", "AGSX", "shared")))
    schreiben(os.path.join(COMP, "Amiga.mgl"),
              '<mistergamedescription><rbf>_computer/minimig</rbf>'
              '<setname>AGSX</setname></mistergamedescription>')
    C.mgl_inhalt("_Computer/Minimig", os.path.join(av, "games", "Elite"), 1,
                 C.TYP_AGS, 0)
    check("ohne same_dir: der Heimatordner heisst wie der Setname",
          open(os.path.join(WURZEL, "games", "AGSX", "shared",
                            "ags_boot")).read() == "Elite\n")
    schreiben(os.path.join(COMP, "Amiga.mgl"),
              mgl("_computer/minimig", "Amiga"))
    os.remove(os.path.join(KONF, "AGSX.cfg"))

    # ein Name mit Umlaut in Latin-1, wie Amiga-Dateinamen
    schreiben(os.path.join(av, "listings", "games.txt"),
              b"M\xfcllabfuhr\nLotus III\n")
    namen = C.amigavision_liste(av)
    check("Latin-1-Liste lesbar", namen == ["M\u00fcllabfuhr", "Lotus III"],
          namen)
    C.ags_boot_schreiben(av, "M\u00fcllabfuhr")
    check("ags_boot mit genau den Bytes der Liste",
          open(os.path.join(av, "shared", "ags_boot"), "rb").read()
          == b"M\xfcllabfuhr\n")

    # der Computer-Check: Festplatte nicht eingetragen
    gesichert = open(os.path.join(KONF, "Amiga.cfg"), "rb").read()
    schreiben(os.path.join(KONF, "Amiga.cfg"),
              cfg("games/Amiga/AmigaVision.rom"))
    am = dict(C.computer_check([basis], COMP))["Amiga"]
    check("Check: AmigaVision.hdf nicht eingetragen -> rot",
          (False, "check_av_hdf_fehlt", ()) in am, am)
    check("Build 334: die Zeile zum Laufwerk MiSTer: ist weg",
          not [z for z in am if z[1] == "check_av_laufwerk"])
    schreiben(os.path.join(KONF, "Amiga.cfg"), gesichert)
    am = dict(C.computer_check([basis], COMP))["Amiga"]
    check("GEGENPROBE: eingetragen -> keine Warnung",
          not [z for z in am if z[1] == "check_av_hdf_fehlt"])
    for k in ("check_av_hdf_fehlt", "check_av_laufwerk"):
        check("Text %s uebersetzt" % k, fm.t(k) != k)

    # -----------------------------------------------------------------------
    print()
    print("Test 10: Start- und Anzeigenamen (Build 333, fuer alte Eintraege)")
    # -----------------------------------------------------------------------
    # Seit Build 334 gibt es keine AmigaVision-Liste mehr im Frontend; die
    # Namenslogik bleibt fuer Eintraege, die noch in "Zuletzt gespielt"
    # oder den Favoriten stehen.
    check("Startname erkannt (Spiel)", C.ist_startname("1000 Miglia (OCS)[en]"))
    check("Startname erkannt (Demo)",
          C.ist_startname("State of the Art (Spaceballs)(OCS)"))
    check("GEGENPROBE: Anzeigename ist keiner",
          not C.ist_startname("1000 Miglia"))
    check("Anzeige ohne Zusatz",
          C.anzeigename("1000 Miglia (OCS)[en]") == "1000 Miglia")
    schreiben(os.path.join(av, "listings", "games.txt"),
              b"1000 Miglia\n1000cc Turbo\n1869\n")
    check("seine Liste: nur Anzeigenamen erkannt",
          C.amigavision_namen(av, "games.txt")[2] is False)
    shared = C.mister_laufwerk("Amiga")
    schreiben(os.path.join(shared, "games_canonical.txt"),
              b"1000 Miglia (OCS)[en]\nM\xfcllabfuhr (OCS)[de]\n"
              b"42 files - 812 blocks used\nReadme.info\n")
    namen, herkunft, start = C.amigavision_namen(av, "games.txt")
    check("die Amiga-Liste geht vor, nur Startnamen",
          start is True and namen == ["1000 Miglia (OCS)[en]",
                                      "M\u00fcllabfuhr (OCS)[de]"], namen)
    if os.path.exists(os.path.join(shared, "ags_boot")):
        os.remove(os.path.join(shared, "ags_boot"))
    C.mgl_inhalt("_Computer/Minimig",
                 os.path.join(av, "games", "M\u00fcllabfuhr (OCS)[de]"), 1,
                 C.TYP_AGS, 0)
    check("alter Eintrag: ags_boot in den Bytes der Amiga-Liste",
          open(os.path.join(shared, "ags_boot"), "rb").read()
          == b"M\xfcllabfuhr (OCS)[de]\n")
    os.remove(os.path.join(shared, "games_canonical.txt"))
    schreiben(os.path.join(av, "listings", "games.txt"),
              "Turrican\nLotus III\n")

    # -----------------------------------------------------------------------
    print()
    print("Test 11: \"Amiga 500\" - AmigaVision oder ADF (Build 334)")
    # -----------------------------------------------------------------------
    # NUTZERWUNSCH: "dann haette ich bitte nur auf der hauptseite denn
    # eintrag Amiga 500 und wenn man dort drauf klickt die auswahl
    # amigavision starten oder adf datein quasi roms starten wenn es mit
    # installiert ist".
    import fe.systems as SYS
    check("die Kategorie heisst \"Amiga 500\"",
          [e[0] for e in SYS.OPTIONAL_GAME_SYSTEMS if e[1] == "AMIGA"]
          == ["Amiga 500"])
    check("kein Shell-Hinweis mehr vor einem AmigaVision-Eintrag",
          C.starthinweis("AMIGA", ".ags",
                         os.path.join(av, "games", "1869")) is None)
    am = dict(C.computer_check([basis], COMP))["Amiga"]
    check("der Check spricht nicht mehr von Start-/Anzeigenamen",
          not [z for z in am if z[1] in ("check_av_anzeigenamen",
                                          "check_av_startnamen",
                                          "check_av_liste")])

    mgl_pfad, eigen = C.amigavision_mgl()
    check("AmigaVision startet mit AmigaVisions eigener MGL",
          mgl_pfad == os.path.join(COMP, "Amiga.mgl") and eigen is True,
          (mgl_pfad, eigen))
    os.rename(os.path.join(COMP, "Amiga.mgl"), os.path.join(TMP, "weg.mgl"))
    mgl_pfad, eigen = C.amigavision_mgl()
    q = open(mgl_pfad).read()
    check("ohne die MGL: selbst geschrieben, mit dem Setnamen der "
          "AmigaVision-Einstellung",
          eigen is False and mgl_pfad == L.MGL_TMP
          and "<setname>Amiga</setname>" in q and "<file" not in q, q)
    os.rename(os.path.join(TMP, "weg.mgl"), os.path.join(COMP, "Amiga.mgl"))

    import fe.paths
    _gb = fe.paths.GAMES_BASES
    try:
        fe.paths.GAMES_BASES = [basis]
        H.set_screen(1280, 720)
        f = H.make_frontend(page=0)
        gestartet, fragen = [], []
        f.run_core = lambda mgl, label=None, syskey=None, ra=False: \
            gestartet.append((mgl, label, syskey))
        f.draw = lambda *a, **k: None
        antwort = [None]

        def _frage(titel, optionen, **k):
            fragen.append((titel, list(optionen)))
            return antwort[0]
        f._wizard_choice = _frage
        adf = {"folders": {}, "items": [("Spiel", "game", (
            "/x/Spiel.adf", ".adf", "AMIGA", "_Computer/Minimig",
            (1, "f", 0)))]}
        antwort[0] = 1
        check("mit ADF und AmigaVision: Frage, \"ADF\" oeffnet die Liste",
              f._amiga_auswahl(adf) is True and not gestartet
              and fragen and fragen[-1][1] == [fm.t("amiga_av"),
                                               fm.t("amiga_adf")], fragen)
        antwort[0] = 0
        check("\"AmigaVision starten\" startet AmigaVisions MGL",
              f._amiga_auswahl(adf) is False
              and gestartet == [(os.path.join(COMP, "Amiga.mgl"),
                                 "AmigaVision", "AMIGA")], gestartet)
        del gestartet[:]
        antwort[0] = None
        check("GEGENPROBE ESC: nichts gestartet, Liste nicht geoeffnet",
              f._amiga_auswahl(adf) is False and not gestartet)
        del fragen[:]
        platzhalter = {"folders": {}, "items": [
            ("AmigaVision", C.TYP_AV_EINTRAG, av)]}
        check("nur AmigaVision, keine ADF: gleich starten, ohne Frage",
              f._amiga_auswahl(platzhalter) is False
              and len(gestartet) == 1 and not fragen)
        del gestartet[:]
        fe.paths.GAMES_BASES = [os.path.join(TMP, "leer")]
        check("GEGENPROBE ohne AmigaVision: wie jedes System, keine Frage",
              f._amiga_auswahl(adf) is True and not fragen
              and not gestartet)
        fe.paths.GAMES_BASES = [basis]

        # durch _enter_category() selbst
        f.cats = [("Amiga 500", adf, "AMIGA")]
        f.cat_i, f.page = 0, 0
        antwort[0] = 1
        f._enter_category()
        check("Hauptseite -> \"ADF\": die Liste ist offen", f.page == 1)
        f.page = 0
        antwort[0] = 0
        f._enter_category()
        check("Hauptseite -> \"AmigaVision\": Seite bleibt, Core startet",
              f.page == 0 and gestartet)
    finally:
        fe.paths.GAMES_BASES = _gb
    q = open(H.FRONTEND_PY, encoding="utf-8").read()
    check("der Platzhalter ist in der Hauptschleife verdrahtet",
          "elif kind == COMPUTER.TYP_AV_EINTRAG:" in q)
    for k in ("amiga_titel", "amiga_av", "amiga_adf", "amiga_av_fehlt"):
        check("Text %s uebersetzt" % k, fm.t(k) != k)

    # -----------------------------------------------------------------------
    print()
    print("Test 8: die Bilder")
    # -----------------------------------------------------------------------
    FE = os.path.dirname(H.FRONTEND_PY)

    def art(p):
        d = open(p, "rb").read()
        b, h = struct.unpack("<HH", d[4:8])
        roh = zlib.decompress(d[8:])
        return d[:4], b, h, roh

    for ordner, (b0, h0) in (("sysart", (320, 420)),
                             ("sysart_foto", (420, 320))):
        for k in ("C64", "AMIGA", "AMSTRAD", "AO486"):
            p = os.path.join(FE, ordner, k + ".art")
            if not os.path.isfile(p):
                check("%s/%s.art vorhanden" % (ordner, k), False)
                continue
            kenn, b, h, roh = art(p)
            ecke = tuple(roh[0:3])
            check("%s/%s.art: ART1, %dx%d, Ecke C_PANEL"
                  % (ordner, k, b0, h0),
                  kenn == b"ART1" and (b, h) == (b0, h0)
                  and len(roh) == b * h * 4 and ecke == (44, 32, 28),
                  (kenn, b, h, ecke))
            mitte = roh[(h // 2 * b + b // 2) * 4:(h // 2 * b + b // 2) * 4 + 3]
            check("GEGENPROBE %s/%s.art: in der Mitte steht etwas"
                  % (ordner, k), tuple(mitte) != (44, 32, 28))
finally:
    (C.CONFIG_ORDNER, C.SD_WURZEL, C.COMPUTER_ORDNER, L.MGL_TMP,
     C.MEDIA, C.MISTER_INI) = _alt
    shutil.rmtree(TMP, ignore_errors=True)

print()
if fails:
    print("ROT: %d Pruefung(en) fehlgeschlagen:" % len(fails))
    for f_ in fails:
        print("   - " + f_)
    sys.exit(1)
print("ALLES GRUEN")
