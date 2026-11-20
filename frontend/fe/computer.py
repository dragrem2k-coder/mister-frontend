#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Die Computer-Systeme mit Spielen (Build 330): Commodore 64, Amiga,
Amstrad CPC und DOS (ao486).

NUTZERWUNSCH: "Wie koennen wir die Computer cores, besonders Amiga, C64,
amstrad, ao486 mit spielen noch schoen mit einbinden?" - dazu, was er
benutzt: "c64 nutze ich die one load collection, amiga die amigavision
und ao486 die 0mhz-dos". Die Spiele liegen in /media/fat/games, auf USB
oder auf dem NAS (fe.paths.GAMES_BASES deckt alle drei ab).

WAS JEDES SYSTEM BRAUCHT - und woher die Zahlen kommen. Die Startwerte
(type/index der MGL) stehen in fe/systems.py und stammen aus dem
CONF_STR der Cores selbst (C64.sv, Amstrad.sv, ao486.sv bei MiSTer-devel)
und decken sich mit der Systemdatenbank von Zaparoo:

  C64      S0 = Laufwerk 8 (D64/G64/T64/D81), F1 = PRG/CRT/REU/TAP.
           "Reset & Run PRG" steht im Core standardmaessig auf Ja - eine
           PRG oder ein Modul (die OneLoad64-Sammlung besteht aus Modulen,
           .crt) laeuft also von selbst los. Eine .T64 wird zur PRG
           (siehe fe/gimmick.py); eine Diskette wird nur eingelegt.
  Amstrad  S0 = Laufwerk A (DSK), F4 = Kassette (CDT), F6 = Snapshot (SNA).
  ao486    S0 = Diskette A, S2 = Festplatte IDE 0-0 (VHD), S4 = CD.
           Nach dem Einhaengen ein Reset, sonst bootet nichts.
  Amiga    F0 = Diskettenlaufwerk df0 (ADF) im Minimig-Core.

DIE DREI SAMMLUNGEN:

  OneLoad64   Module (.crt) in games/C64 - werden ganz normal eingelesen.
  AmigaVision ein grosses Festplattenabbild (AmigaVision.hdf oder
              MegaAGS.hdf) in games/Amiga mit eigenem Startmenue. Die
              Spieleliste steht in games/Amiga/listings/games.txt (ein
              Name je Zeile). Damit AmigaVision direkt in EIN Spiel
              bootet, steht dessen Name in games/Amiga/shared/ags_boot -
              derselbe Weg, den Zaparoo geht (hookAmiga in zaparoo-core).
              Gestartet wird dann der Minimig-Core mit dem Setnamen
              "Amiga" - dessen Einstellungen hat AmigaVision eingerichtet.
  0MHz-DOS    je Spiel eine fertige MGL in /media/fat/_DOS Games/ und die
              Abbilder in games/AO486/media/<Spiel>/. Die MGL bringt alles
              mit (Festplatte, CD, Reset) - das Frontend startet sie
              unveraendert und listet die Abbilder, die schon zu einer MGL
              gehoeren, nicht ein zweites Mal.

WAS DAS FRONTEND SCHREIBT: die Start-MGL (wie bei jedem Spiel), eine
PRG aus einer T64 in seinen eigenen Ordner, und bei AmigaVision die eine
Datei shared/ags_boot - mehr nicht. Weder Disketten noch Abbilder noch
die MGLs der Sammlungen werden angefasst.
"""
import glob
import os
import struct

from fe.log import LOG

# ---------------------------------------------------------------------------
# Wo gesucht wird
# ---------------------------------------------------------------------------
DOS_MGL_MUSTER = "/media/fat/_DOS*"
C64_PRG_ORDNER = "/media/fat/frontend/c64_prg"
AMIGAVISION_ABBILDER = ("AmigaVision.hdf", "MegaAGS.hdf")
AMIGAVISION_LISTEN = (("games.txt", "AmigaVision"),
                      ("demos.txt", "AmigaVision Demos"))
# Die pseudo-"Typen" in der Endungstabelle, an denen write_mgl() die
# Sonderfaelle erkennt (siehe mgl_inhalt()).
TYP_AGS = "ags"          # AmigaVision-Eintrag
TYP_MGL = "mgl"          # fertige MGL einer Sammlung (0MHz)


def _basen():
    try:
        import fe.paths
        return list(fe.paths.GAMES_BASES)
    except Exception:                                    # noqa: BLE001
        return ["/media/fat/games"]


def _kein_steuerzeichen(text):
    return text and not any(ord(c) < 32 for c in text)


# ---------------------------------------------------------------------------
# AmigaVision
# ---------------------------------------------------------------------------
def amigavision_installation(basen=None):
    """Der Ordner einer AmigaVision-Installation (mit AmigaVision.hdf
    oder MegaAGS.hdf) - der erste gefundene, oder None."""
    for base in (basen or _basen()):
        ordner = os.path.join(base, "Amiga")
        for abbild in AMIGAVISION_ABBILDER:
            if os.path.isfile(os.path.join(ordner, abbild)):
                return ordner
    return None


def amigavision_liste(installation, datei="games.txt"):
    """Die Namen aus listings/<datei> - in der Reihenfolge der Datei,
    ohne Leerzeilen und ohne Doppelte."""
    pfad = os.path.join(installation, "listings", datei)
    namen = []
    gesehen = set()
    try:
        with open(pfad, "r", encoding="utf-8", errors="replace") as f:
            for zeile in f:
                name = zeile.strip()
                if not _kein_steuerzeichen(name) or name in gesehen:
                    continue
                gesehen.add(name)
                namen.append(name)
    except OSError:
        return []
    return namen


def ags_boot_schreiben(installation, name):
    """games/Amiga/shared/ags_boot = Name + Zeilenende - die Anweisung an
    AmigaVision, direkt in dieses Spiel zu booten. Ueber eine .tmp-Datei;
    der Ordner shared muss da sein (er gehoert zu AmigaVision und wird
    nicht angelegt - fehlt er, stimmt mit der Installation etwas nicht).
    True bei Erfolg."""
    if not _kein_steuerzeichen(name):
        return False
    shared = os.path.join(installation, "shared")
    if not os.path.isdir(shared):
        LOG("AmigaVision: %s fehlt - kann nicht direkt starten" % shared)
        return False
    ziel = os.path.join(shared, "ags_boot")
    inhalt = (name + "\n").encode("utf-8")
    try:
        with open(ziel, "rb") as f:
            if f.read(len(inhalt) + 1) == inhalt:
                return True
    except OSError:
        pass
    try:
        tmp = ziel + ".tmp"
        with open(tmp, "wb") as f:
            f.write(inhalt)
        os.replace(tmp, ziel)
        return True
    except OSError as e:
        LOG("AmigaVision: ags_boot nicht geschrieben: %s" % e)
        return False


# ---------------------------------------------------------------------------
# 0MHz-DOS
# ---------------------------------------------------------------------------
def _mgl_dateipfade(mgl_pfad):
    """Die path-Angaben der <file>-Elemente einer MGL (roh)."""
    try:
        with open(mgl_pfad, "r", encoding="utf-8", errors="replace") as f:
            text = f.read(65536)
    except OSError:
        return []
    import re
    return re.findall(r'<file\b[^>]*\bpath\s*=\s*"([^"]*)"', text, re.I)


def dos_mgls(muster=None):
    """[(Name, MGL-Pfad)] aller MGLs in den MiSTer-Ordnern /media/fat/_DOS*
    (die 0MHz-Sammlung legt sie in "_DOS Games"), nach Name sortiert."""
    raus = []
    for ordner in sorted(glob.glob(muster or DOS_MGL_MUSTER)):
        if not os.path.isdir(ordner):
            continue
        try:
            namen = os.listdir(ordner)
        except OSError:
            continue
        for n in namen:
            if n.lower().endswith(".mgl") and not n.startswith("."):
                raus.append((os.path.splitext(n)[0], os.path.join(ordner, n)))
    raus.sort(key=lambda e: e[0].lower())
    return raus


def dos_mgl_abbilder(mgl_pfad, ao486_ordner):
    """Die Abbilder, die eine 0MHz-MGL einhaengt, als echte Pfade unter
    ao486_ordner (games/AO486 einer Wurzel) - normalisiert, damit der
    Vergleich mit den eingelesenen Dateien Gross/Klein nicht
    durcheinanderbringt."""
    raus = set()
    for p in _mgl_dateipfade(mgl_pfad):
        if p.startswith("../"):
            continue                       # absoluter Weg, kein Sammlungsteil
        raus.add(os.path.normcase(os.path.normpath(
            os.path.join(ao486_ordner, p))).lower())
    return raus


# ---------------------------------------------------------------------------
# Den Baum eines Systems ergaenzen (aus fe/scan.py aufgerufen)
# ---------------------------------------------------------------------------
def _alle_eintraege(knoten):
    for e in knoten.get("items", ()):
        yield knoten, e
    for unter in knoten.get("folders", {}).values():
        for paar in _alle_eintraege(unter):
            yield paar


def _leere_ordner_entfernen(knoten):
    for name in list(knoten.get("folders", {})):
        unter = knoten["folders"][name]
        _leere_ordner_entfernen(unter)
        if not unter.get("folders") and not unter.get("items"):
            del knoten["folders"][name]


def knoten_ergaenzen(syskey, knoten, rbf, basen=None, dos_muster=None):
    """Nach dem Einlesen der Ordner: die Sammlungen dazunehmen.

    AMIGA: je Liste von AmigaVision ein Unterordner ("AmigaVision",
           "AmigaVision Demos") mit einem Eintrag je Name.
    AO486: die 0MHz-MGLs als Eintraege oben in der Liste; die Abbilder,
           die schon zu einer MGL gehoeren, fliegen aus dem Baum (sonst
           stuende jedes Spiel zweimal da, einmal davon ohne CD).
    Andere Systeme: unveraendert. Gibt den Knoten zurueck."""
    if syskey == "AMIGA":
        inst = amigavision_installation(basen)
        if inst:
            for datei, ordnername in AMIGAVISION_LISTEN:
                namen = amigavision_liste(inst, datei)
                if not namen:
                    continue
                items = [(n, "game", (os.path.join(inst, "games", n), ".ags",
                                      syskey, rbf, (1, TYP_AGS, 0)))
                         for n in namen]
                knoten.setdefault("folders", {})[ordnername] = {
                    "folders": {}, "items": items}
            LOG("AmigaVision: %s" % inst)
    elif syskey == "AO486":
        mgls = dos_mgls(dos_muster)
        if mgls:
            belegt = set()
            for base in (basen or _basen()):
                ao = os.path.join(base, "AO486")
                if os.path.isdir(ao):
                    for _n, p in mgls:
                        belegt |= dos_mgl_abbilder(p, ao)
            for k, e in list(_alle_eintraege(knoten)):
                try:
                    pfad = e[2][0]
                except (TypeError, IndexError):
                    continue
                if os.path.normcase(os.path.normpath(pfad)).lower() in belegt:
                    k["items"].remove(e)
            _leere_ordner_entfernen(knoten)
            eigene = [(n, "game", (p, ".mgl", syskey, rbf, (0, TYP_MGL, 0)))
                      for n, p in mgls]
            knoten["items"] = eigene + list(knoten.get("items", []))
    return knoten


# ---------------------------------------------------------------------------
# Die Start-MGL (aus fe.launch.write_mgl() aufgerufen)
# ---------------------------------------------------------------------------
def _datei_xml(delay, typ, index, pfad):
    return ('\t<file delay="%d" type="%s" index="%d" '
            'path="../../../../..%s"/>\n' % (delay, typ, index, pfad))


def _ist_core(rbf, name):
    return os.path.basename(str(rbf or "")).lower().startswith(name.lower())


def mgl_inhalt(rbf, rom_path, delay, ftype, index, setname=None,
               prg_ordner=None):
    """Der Inhalt der Start-MGL fuer die Sonderfaelle der Computer -
    oder None, dann baut write_mgl() die gewoehnliche.

    Sonderfaelle:
      * AmigaVision-Eintrag (ftype "ags"): ags_boot schreiben, Minimig mit
        Setname "Amiga", KEINE Datei.
      * C64 mit .T64: das erste Programm als PRG, ueber F1 (laeuft los).
      * ao486 mit Festplatte (.vhd): Abbild an S2, liegt im selben Ordner
        ein CD-Abbild (.chd/.iso/.cue), dieses an S4; danach ein Reset.
      * ao486 mit Diskette: einhaengen und Reset.

    KEIN FEHLERWEG NACH AUSSEN: write_mgl() hat vier Aufrufer (Liste,
    Zufalls-Zock, Schnellstart, Weiterspielen), und keiner rechnet mit
    einem Fehler. Klappt ein Sonderfall nicht, gibt es den naechstbesten
    Start: AmigaVision ohne ags_boot bootet in sein eigenes Menue, eine
    T64, die sich nicht umwandeln laesst, wird als Band ins Laufwerk 8
    gelegt (der Core kann T64 dort einhaengen)."""
    endung = os.path.splitext(str(rom_path))[1].lower()
    if ftype == TYP_AGS:
        inst = os.path.dirname(os.path.dirname(rom_path))
        name = os.path.basename(rom_path)
        if not ags_boot_schreiben(inst, name):
            LOG("AmigaVision: starte ohne ags_boot ins Menue")
        return ('<mistergamedescription>\n'
                '\t<rbf>%s</rbf>\n'
                '\t<setname>Amiga</setname>\n'
                '</mistergamedescription>\n' % rbf)
    if _ist_core(rbf, "C64") and endung == ".t64":
        from fe.gimmick import prg_bereitstellen
        prg = prg_bereitstellen(rom_path, prg_ordner or C64_PRG_ORDNER)
        if not prg:
            LOG("C64: %s nicht umwandelbar - lege sie ins Laufwerk 8"
                % rom_path)
            return ('<mistergamedescription>\n\t<rbf>%s</rbf>\n%s'
                    '</mistergamedescription>\n'
                    % (rbf, _datei_xml(delay, "s", 0, rom_path)))
        return ('<mistergamedescription>\n\t<rbf>%s</rbf>\n%s'
                '</mistergamedescription>\n'
                % (rbf, _datei_xml(delay, "f", 1, prg)))
    if _ist_core(rbf, "ao486") and endung in (".vhd", ".img", ".ima",
                                               ".vfd"):
        dateien = _datei_xml(delay, ftype, index, rom_path)
        if endung == ".vhd":
            ordner = os.path.dirname(rom_path)
            try:
                nachbarn = sorted(os.listdir(ordner))
            except OSError:
                nachbarn = []
            for n in nachbarn:
                if os.path.splitext(n)[1].lower() in (".chd", ".iso",
                                                      ".cue"):
                    dateien += _datei_xml(delay, "s", 4,
                                          os.path.join(ordner, n))
                    break
        return ('<mistergamedescription>\n\t<rbf>%s</rbf>\n%s'
                '\t<reset delay="1"/>\n</mistergamedescription>\n'
                % (rbf, dateien))
    return None


# ---------------------------------------------------------------------------
# Hinweise vor dem Start
# ---------------------------------------------------------------------------
def cpc_dsk_programme(daten):
    """Die startbaren Programme einer Amstrad-Diskette (.DSK, normal oder
    "EXTENDED"), BAS zuerst - fuer den Hinweis RUN"NAME. Leere Liste,
    wenn sich nichts lesen laesst.

    Das Verzeichnis liegt auf Spur 0 in den Sektoren C1-C4 (Datenformat)
    oder auf Spur 2 in 41-44 (Systemformat); gelesen werden die Eintraege
    von Benutzer 0, erster Teil (Extent 0)."""
    if not daten or len(daten) < 0x200:
        return []
    erweitert = daten[:8] == b"EXTENDED"
    if not erweitert and daten[:8] != b"MV - CPC":
        return []
    spuren, seiten = daten[0x30], max(1, daten[0x31])
    if erweitert:
        groessen = [daten[0x34 + i] * 256 for i in range(spuren * seiten)]
    else:
        groesse = struct.unpack("<H", daten[0x32:0x34])[0]
        groessen = [groesse] * (spuren * seiten)
    versatz = 0x100
    sektoren = {}                          # (Spur, Sektornummer) -> Bytes
    for i, g in enumerate(groessen):
        if g == 0:
            continue
        spur = daten[versatz:versatz + g]
        if spur[:10] != b"Track-Info":
            break
        anzahl = spur[0x15]
        n_std = spur[0x14]
        pos = 0x100
        for s in range(min(anzahl, 29)):
            info = spur[0x18 + 8 * s:0x20 + 8 * s]
            if len(info) < 8:
                break
            sid, n = info[2], info[3]
            laenge = (struct.unpack("<H", info[6:8])[0] if erweitert
                      else 128 << min(n_std, 6))
            if laenge <= 0:
                laenge = 128 << min(n, 6)
            if i // seiten < 3:            # nur die ersten Spuren
                sektoren[(i // seiten, sid)] = spur[pos:pos + laenge]
            pos += laenge
        versatz += g
        if i // seiten >= 3:
            break
    verzeichnis = b""
    for spur, start in ((0, 0xC1), (2, 0x41), (1, 0x01)):
        if (spur, start) in sektoren:
            verzeichnis = b"".join(sektoren.get((spur, start + k), b"")
                                   for k in range(4))
            break
    bas, andere = [], []
    for k in range(0, len(verzeichnis) - 31, 32):
        e = verzeichnis[k:k + 32]
        if e[0] != 0 or e[12] != 0:
            continue
        name = bytes(b & 0x7F for b in e[1:9]).decode("ascii", "replace")
        ext = bytes(b & 0x7F for b in e[9:12]).decode("ascii", "replace")
        name, ext = name.strip(), ext.strip()
        if not name or not all(32 < ord(c) < 127 for c in name):
            continue
        if ext.upper() == "BAS":
            if name not in bas:
                bas.append(name)
        elif ext.upper() in ("BIN", "") and name not in andere:
            andere.append(name)
    return bas + [n for n in andere if n not in bas]


def starthinweis(syskey, endung, rom_path, lesen=None):
    """Was man nach dem Start tippen muss - als (Titelschluessel,
    [(Textschluessel, Argumente)]) - oder None, wenn das Spiel von selbst
    losgeht. Texte kommen ueber die Uebersetzungen (fe/translations.py)."""
    endung = (endung or "").lower()
    if syskey == "C64":
        if endung in (".d64", ".g64", ".d81"):
            return ("hinweis_c64_titel", [("hinweis_c64_disk", ())])
        if endung == ".tap":
            return ("hinweis_c64_titel", [("hinweis_c64_tap", ())])
        return None
    if syskey == "AMSTRAD":
        if endung == ".dsk":
            try:
                daten = (lesen or _lesen)(rom_path)
            except OSError:
                daten = b""
            programme = cpc_dsk_programme(daten)
            if programme:
                zeilen = [("hinweis_cpc_run", ('RUN"%s' % p,))
                          for p in programme[:4]]
                return ("hinweis_cpc_titel", zeilen)
            return ("hinweis_cpc_titel", [("hinweis_cpc_cat", ())])
        if endung == ".cdt":
            return ("hinweis_cpc_titel", [("hinweis_cpc_tape", ())])
    return None


def _lesen(pfad):
    with open(pfad, "rb") as f:
        return f.read(400 * 1024)


# ---------------------------------------------------------------------------
# Der Computer-Check (System -> Wartung)
# ---------------------------------------------------------------------------
COMPUTER_ORDNER = "/media/fat/_Computer"


def _core(muster, ordner=None):
    o = ordner or COMPUTER_ORDNER
    treffer = sorted(glob.glob(os.path.join(o, muster)))
    return os.path.basename(treffer[-1]) if treffer else None


def computer_check(basen=None, core_ordner=None, dos_muster=None):
    """Je System: (Name, [(ok, Textschluessel, Argumente)]). ok ist True,
    False oder None (nur zur Auskunft)."""
    basen = basen or _basen()

    def ordner(name):
        return [os.path.join(b, name) for b in basen
                if os.path.isdir(os.path.join(b, name))]

    def zaehlen(ordner_liste, endungen):
        n = 0
        for o in ordner_liste:
            for _w, _d, dateien in os.walk(o):
                n += sum(1 for d in dateien
                         if os.path.splitext(d)[1].lower() in endungen)
                if n > 99999:
                    return n
        return n

    raus = []
    # C64
    c64_core = _core("C64*.rbf", core_ordner)
    c64 = ordner("C64")
    raus.append(("Commodore 64", [
        (bool(c64_core), "check_core", (c64_core or "C64",)),
        (bool(c64), "check_ordner", ("games/C64",)),
        (None, "check_spiele", (zaehlen(c64, (".crt", ".prg", ".t64", ".d64",
                                             ".g64", ".d81", ".tap")),)),
    ]))
    # Amiga
    mm_core = _core("Minimig*.rbf", core_ordner)
    inst = amigavision_installation(basen)
    zeilen = [(bool(mm_core), "check_core", (mm_core or "Minimig",))]
    if inst:
        n = len(amigavision_liste(inst))
        zeilen.append((True, "check_amigavision", (inst,)))
        zeilen.append((n > 0, "check_av_liste", (n,)))
        zeilen.append((os.path.isdir(os.path.join(inst, "shared")),
                       "check_av_shared", ()))
    else:
        zeilen.append((False, "check_amigavision_fehlt", ()))
    raus.append(("Amiga", zeilen))
    # Amstrad
    cpc_core = _core("Amstrad[_.]*rbf", core_ordner)
    cpc = ordner("Amstrad")
    raus.append(("Amstrad CPC", [
        (bool(cpc_core), "check_core", (cpc_core or "Amstrad",)),
        (bool(cpc), "check_ordner", ("games/Amstrad",)),
        (None, "check_spiele", (zaehlen(cpc, (".dsk", ".cdt", ".sna")),)),
    ]))
    # ao486
    ao_core = _core("ao486*.rbf", core_ordner)
    ao = ordner("AO486")
    roms = any(os.path.isfile(os.path.join(o, "boot0.rom"))
               and os.path.isfile(os.path.join(o, "boot1.rom")) for o in ao)
    mgls = dos_mgls(dos_muster)
    raus.append(("DOS (ao486)", [
        (bool(ao_core), "check_core", (ao_core or "ao486",)),
        (bool(ao), "check_ordner", ("games/AO486",)),
        (roms, "check_ao486_roms", ()),
        (None, "check_dos_mgls", (len(mgls),)),
    ]))
    return raus
