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

# Build 331: wo MiSTer die Einstellungen der Cores ablegt, und die Wurzel,
# gegen die er relative Pfade darin aufloest (file_io.cpp,
# make_fullpath(): getRootDir() + "/" + Pfad).
CONFIG_ORDNER = "/media/fat/config"
SD_WURZEL = "/media/fat"
COMPUTER_ORDNER = "/media/fat/_Computer"
AGS_ABBILDER = ("amigavision.hdf", "megaags.hdf")
# Die Hinweise, zu denen der Satz "Dafuer braucht es eine Tastatur"
# gehoert - beim fehlenden DOS-Spiel waere er falsch.
TASTATUR_TITEL = ("hinweis_c64_titel", "hinweis_cpc_titel")


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
        with open(pfad, "rb") as f:
            for roh in f.read().splitlines():
                name = _dekodieren(roh.strip())
                if not _kein_steuerzeichen(name) or name in gesehen:
                    continue
                gesehen.add(name)
                namen.append(name)
    except OSError:
        return []
    return namen


# ---------------------------------------------------------------------------
# Wohin ags_boot gehoert (Build 332)
# ---------------------------------------------------------------------------
# NUTZERMELDUNG nach Build 331: "wenn ich jetzt ueber das frontend ein
# spiel starte lande ich erst in der amigavision frontend und suche mir
# dort das spiel nochmal aus".
#
# AmigaVision liest die Datei nicht aus "seinem" Ordner, sondern vom
# Amiga-Laufwerk MiSTer: (S/startup-sequence: "if exists MiSTer:ags_boot").
# Welcher Ordner das ist, entscheidet Main (minimig_share.cpp): der Wert
# shared_folder aus MiSTer.ini, sonst <Heimatordner>/shared - und der
# Heimatordner wird gesucht (file_io.cpp, findPrefixDir): zuerst auf den
# USB-Laufwerken, dann im Netzlaufwerk, dann cifs, zuletzt auf der Karte.
# Liegt auf USB oder dem NAS ein Ordner games/Amiga (etwa mit ADFs), ist
# MiSTer: DORT - und eine ags_boot neben AmigaVision.hdf auf der Karte
# sieht der Amiga nie. Bis Build 331 wurde genau dorthin geschrieben.
MISTER_INI = "/media/fat/MiSTer.ini"
MEDIA = "/media"


def heimatordner(kern="Amiga", wurzel=None, media=None):
    """Der Heimatordner eines Cores, gesucht wie Main es tut
    (findPrefixDir mit no_prefix_check): je USB-Laufwerk 0-5 erst
    <kern>, dann games/<kern>; dann /media/network, dann cifs, dann die
    Karte. Gibt es keinen, nimmt Main games/<kern> auf der Karte."""
    wurzel = wurzel or SD_WURZEL
    media = media or MEDIA
    kandidaten = []
    for i in range(6):
        u = os.path.join(media, "usb%d" % i)
        kandidaten += [os.path.join(u, kern), os.path.join(u, "games", kern)]
    n = os.path.join(media, "network")
    kandidaten += [os.path.join(n, kern), os.path.join(n, "games", kern)]
    c = os.path.join(wurzel, "cifs")
    kandidaten += [os.path.join(c, kern), os.path.join(c, "games", kern)]
    kandidaten += [os.path.join(wurzel, kern),
                   os.path.join(wurzel, "games", kern)]
    for k in kandidaten:
        if os.path.isdir(k):
            return k
    return os.path.join(wurzel, "games", kern)


def _ini_wert(schluessel, kern, ini=None):
    """Ein Wert aus MiSTer.ini fuer diesen Core: erst der allgemeine
    Abschnitt [MiSTer], dann jeder Abschnitt, dessen Namensliste den Core
    nennt - auch die mehrzeilige Form, die AmigaVision selbst benutzt
    ("[Amiga" / "+Amiga500" / ... / "]"). Der spaetere gewinnt, wie bei
    MiSTer. None, wenn nirgends gesetzt."""
    try:
        with open(ini or MISTER_INI, "r", encoding="utf-8",
                  errors="replace") as f:
            zeilen = f.read().splitlines()
    except OSError:
        return None
    wert, aktiv, kopf = None, True, None
    for roh in zeilen:
        z = roh.split(";", 1)[0].strip()
        if kopf is not None:
            kopf += z
            if "]" in z:
                namen = kopf.strip("[]").replace(" ", "").split("+")
                aktiv = any(n.lower() in ("mister", kern.lower())
                            for n in namen if n)
                kopf = None
            continue
        if z.startswith("["):
            if "]" in z:
                namen = z.strip("[]").replace(" ", "").split("+")
                aktiv = any(n.lower() in ("mister", kern.lower())
                            for n in namen if n)
            else:
                kopf = z
            continue
        if aktiv and "=" in z:
            k, v = z.split("=", 1)
            if k.strip().lower() == schluessel.lower():
                wert = v.strip()
    return wert


def mister_laufwerk(kern="Amiga", wurzel=None, media=None, ini=None):
    """Der Ordner, den der Amiga als MiSTer: sieht (minimig_share.cpp)."""
    heim = heimatordner(kern, wurzel, media)
    eigen = _ini_wert("shared_folder", kern, ini)
    if eigen:
        return eigen if eigen.startswith("/") else os.path.join(heim, eigen)
    return os.path.join(heim, "shared")


def _rohzeile(installation, name):
    """Die Zeile aus listings/*.txt so, wie sie in der Datei steht -
    damit ein Name mit Umlaut in derselben Kodierung ankommt, in der
    AmigaVision seine Dateien benannt hat."""
    pfade = []
    for datei, _ordner in AMIGAVISION_LISTEN:
        try:
            pfade.append(startnamen_datei(datei))
        except Exception:                                # noqa: BLE001
            pass
        pfade.append(os.path.join(installation, "listings", datei))
    for pfad in pfade:
        try:
            with open(pfad, "rb") as f:
                for z in f.read().splitlines():
                    z = z.strip()
                    if _dekodieren(z) == name:
                        return z
        except OSError:
            continue
    return name.encode("utf-8")


def _dekodieren(roh):
    try:
        return roh.decode("utf-8")
    except UnicodeDecodeError:
        return roh.decode("latin-1")


def ags_boot_schreiben(installation, name, setname="Amiga"):
    """MiSTer:ags_boot = Name + Zeilenende - die Anweisung an AmigaVision,
    direkt in dieses Spiel zu booten (S/ags-launch sucht danach
    AGS:RunQuiet/Game/<Name>). Ueber eine .tmp-Datei.

    Seit Build 332 in den Ordner, den der Amiga als MiSTer: sieht
    (mister_laufwerk()), nicht mehr pauschal neben AmigaVision.hdf. Fehlt
    er, wird er angelegt - Main legt ihn beim Start ohnehin an
    (FileCreatePath in minimig_share.cpp). True bei Erfolg."""
    if not _kein_steuerzeichen(name):
        return False
    shared = mister_laufwerk(setname)
    try:
        os.makedirs(shared, exist_ok=True)
    except OSError as e:
        LOG("AmigaVision: %s nicht anlegbar: %s" % (shared, e))
        return False
    ziel = os.path.join(shared, "ags_boot")
    LOG("AmigaVision: ags_boot -> %s" % ziel)
    inhalt = _rohzeile(installation, name) + b"\n"
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
# Anzeigenamen und Startnamen (Build 333)
# ---------------------------------------------------------------------------
# NACHGEMESSEN an seiner Karte: ags_boot war nach dem Start weg - der
# Amiga HAT die Datei gelesen (S/startup-sequence verschiebt sie nach T:)
# -, und trotzdem kam das AmigaVision-Menue. Seine listings/games.txt:
#
#     1000 Miglia$
#     1000cc Turbo$
#     1869$
#
# S/ags-launch sucht aber "AGS:RunQuiet/Game/<Name>", und dort heissen die
# Startdateien "Titel (Hardware)[Sprache]" (ags_make.py,
# make_canonical_name()): "1000 Miglia (OCS)[en]". Die Ausgabe
# AmigaVision 2026.04.26 schreibt in games.txt nur die Anzeigenamen
# (AmigaVision-Issue #465, Degauss-Issue #97); eine Zuordnungsdatei liegt
# nicht bei, und erraten laesst sich der Zusatz nicht (Hardware und
# Sprache stehen nirgends ausserhalb der HDF).
#
# Die Startnamen kennt nur der Amiga selbst. Ein Befehl in seiner Shell
# schreibt sie auf das Laufwerk MiSTer: (siehe Handbuch) - liegt diese
# Datei dort, nimmt das Frontend sie statt games.txt.
AV_STARTNAMEN = {"games.txt": "games_canonical.txt",
                 "demos.txt": "demos_canonical.txt"}


def ags_kern():
    """Der Heimatordner-Name, unter dem der Amiga MiSTer: findet - der
    Setname der AmigaVision-MGL, mit same_dir="1" "Amiga"."""
    try:
        _r, el, name, _h = amigavision_start()
    except Exception:                                    # noqa: BLE001
        return "Amiga"
    if 'same_dir="1"' in el.replace("'", '"'):
        return "Amiga"
    return name or "Amiga"


def ist_startname(name):
    """Sieht der Name aus wie eine Startdatei von AmigaVision - endet er
    auf "(...)" oder "(...)[...]"?"""
    import re
    return bool(re.search(r"\)(\[[^\[\]]*\])?$", name or ""))


def _liste_mit_startnamen(namen):
    """Mindestens die Haelfte der Eintraege traegt den Zusatz - dann ist
    es eine Liste mit Startnamen (einzelne Titel ohne Zusatz gibt es
    nicht, aber eine Toleranz schadet nicht)."""
    if not namen:
        return False
    return sum(1 for n in namen if ist_startname(n)) * 2 >= len(namen)


def anzeigename(name):
    """'1000 Miglia (OCS)[en]' -> '1000 Miglia' - nur fuer die Anzeige."""
    import re
    kurz = re.sub(r"(\s*\([^()]*\))+(\[[^\[\]]*\])?$", "", name or "")
    return kurz.strip() or name


def startnamen_datei(datei, kern=None):
    """Wo die vom Amiga geschriebene Liste der Startnamen liegt."""
    return os.path.join(mister_laufwerk(kern or ags_kern()),
                        AV_STARTNAMEN.get(datei, datei))


def amigavision_namen(installation, datei="games.txt", kern=None):
    """(Namen, Herkunft, Startnamen?) fuer eine AmigaVision-Liste.

    Zuerst die Datei, die der Amiga selbst auf MiSTer: geschrieben hat
    (games_canonical.txt) - sie enthaelt immer Startnamen. Sonst
    listings/<datei>; ob die Startnamen enthaelt, wird nachgesehen."""
    eigen = startnamen_datei(datei, kern)
    # Nur Zeilen, die wie Startnamen aussehen: so bleibt eine Kopf- oder
    # Summenzeile von LIST oder eine .info-Datei draussen, falls die
    # Shell eine schreibt.
    namen = [n for n in _namen_aus(eigen) if ist_startname(n)]
    if namen:
        return namen, eigen, True
    pfad = os.path.join(installation, "listings", datei)
    namen = amigavision_liste(installation, datei)
    return namen, pfad, _liste_mit_startnamen(namen)


def _namen_aus(pfad):
    namen, gesehen = [], set()
    try:
        with open(pfad, "rb") as f:
            for roh in f.read().splitlines():
                n = _dekodieren(roh.strip())
                if _kein_steuerzeichen(n) and n not in gesehen:
                    gesehen.add(n)
                    namen.append(n)
    except OSError:
        return []
    return namen


# ---------------------------------------------------------------------------
# Minimig: Einstellungen und Start-MGLs (Build 331)
# ---------------------------------------------------------------------------
# NUTZERMELDUNG nach Build 330: "amiga spiele starten nicht da lande ich
# einfach bei der kickrom anzeige obwohl ich ein kickrom drauf habe".
#
# WAS DAHINTER STECKT (Main_MiSTer, support/minimig/minimig_config.cpp):
# der Minimig-Core liest seine Einstellungen aus config/<Name>.cfg, und
# <Name> ist der Setname aus der MGL - ohne Setname "Minimig". Fehlt die
# Datei, nimmt er Vorgaben ("No config found. Using defaults") und sucht
# einen Kickstart, den es unter dem Vorgabenamen nicht gibt. Genau das
# Bild hat er gesehen. AmigaVision legt seine Einstellungen als
# config/Amiga.cfg ab (Kickstart games/Amiga/AmigaVision.rom, Festplatte
# games/Amiga/AmigaVision.hdf) und dazu _Computer/Amiga.mgl mit genau
# diesem Setnamen - so steht es im AmigaVision-Paket.
#
# Build 330 hat den Setnamen "Amiga" fest hineingeschrieben und eine
# ADF ganz ohne Setnamen gestartet. Jetzt wird nachgesehen statt
# angenommen: welche MGL in _Computer startet den Minimig, mit welchem
# Setnamen, und was steht in der zugehoerigen Einstellungsdatei.

def _text_aus(daten, start, laenge):
    stueck = daten[start:start + laenge]
    return stueck.split(b"\0", 1)[0].decode("latin-1", "replace").strip()


def minimig_cfg_lesen(pfad):
    """Kickstart und Festplatten aus einer Minimig-Einstellungsdatei -
    {"kickstart": str, "hdf": [str, ...]} oder None.

    Aufbau (mm_configTYPE in minimig_config.h, ohne Fuellbytes): 8 Byte
    Kennung "MNMGCFG0", 2+2 Byte Version, 992 Byte Kickstart-Pfad, 32
    Label, 2 ext_cfg, je 1 Byte memory/chipset, 2 floppy, je 1 Byte
    disable_ar3/ide_cfg/scanlines/audio - ab Byte 1046 dann vier
    Festplatten zu je 1026 Byte (cfg, reserved, 1024 Byte Pfad)."""
    try:
        with open(pfad, "rb") as f:
            daten = f.read(8192)
    except OSError:
        return None
    if not daten.startswith(b"MNMGCFG") or len(daten) < 1046 + 1026:
        return None
    hdf = []
    for i in range(4):
        o = 1046 + i * 1026
        if o + 1026 > len(daten):
            break
        name = _text_aus(daten, o + 2, 1024)
        if daten[o] and name:
            hdf.append(name)
    return {"kickstart": _text_aus(daten, 12, 992), "hdf": hdf}


def mister_pfad(pfad, wurzel=None):
    """Ein Pfad aus einer Einstellungsdatei, so aufgeloest wie MiSTer es
    tut: absolut bleibt absolut, sonst relativ zur Wurzel der Karte."""
    if not pfad:
        return ""
    if pfad.startswith("/"):
        return pfad
    return os.path.join(wurzel or SD_WURZEL, pfad)


def minimig_mgls(ordner=None):
    """[(MGL-Pfad, rbf, Setname-Element, Setname)] aller MGLs in
    _Computer, die den Minimig starten, nach Name sortiert. Das
    Setname-Element wird WOERTLICH uebernommen (samt Attributen wie
    same_dir) - das Frontend startet genau so, wie die MGL es tut."""
    import re
    raus = []
    try:
        namen = sorted(os.listdir(ordner or COMPUTER_ORDNER))
    except OSError:
        return raus
    for n in namen:
        if not n.lower().endswith(".mgl"):
            continue
        pfad = os.path.join(ordner or COMPUTER_ORDNER, n)
        try:
            with open(pfad, "r", encoding="utf-8", errors="replace") as f:
                text = f.read(16384)
        except OSError:
            continue
        rbf = re.search(r"<rbf>\s*([^<]*?)\s*</rbf>", text, re.I)
        if not rbf or "minimig" not in rbf.group(1).lower():
            continue
        if re.search(r"<file\b", text, re.I):
            continue            # startet ein Spiel, keine Grundeinstellung
        el = re.search(r"<setname\b[^>]*>\s*([^<]*?)\s*</setname>", text,
                       re.I)
        raus.append((pfad, rbf.group(1), el.group(0) if el else "",
                     el.group(1) if el else ""))
    return raus


def _ist_ags(cfg):
    return bool(cfg) and any(os.path.basename(h).lower() in AGS_ABBILDER
                             for h in cfg["hdf"])


def amigavision_start(ordner=None, config=None):
    """Womit AmigaVision gestartet wird: (rbf, Setname-Element, Setname,
    Herkunft). Herkunft ist der Pfad der MGL bzw. der Einstellungsdatei,
    aus der es stammt - oder "" fuer die Vorgabe.

    Reihenfolge: eine Minimig-MGL in _Computer, deren Einstellungsdatei
    AmigaVision.hdf (oder MegaAGS.hdf) einhaengt - "Amiga" zuerst; dann
    irgendeine Einstellungsdatei mit AmigaVision.hdf; dann die Vorgabe
    des AmigaVision-Pakets (Setname "Amiga")."""
    config = config or CONFIG_ORDNER
    treffer = []
    for mgl, rbf, el, name in minimig_mgls(ordner):
        if name and _ist_ags(minimig_cfg_lesen(
                os.path.join(config, name + ".cfg"))):
            treffer.append((name.lower() != "amiga", mgl, rbf, el, name))
    if treffer:
        treffer.sort()
        _r, mgl, rbf, el, name = treffer[0]
        return rbf, el, name, mgl
    try:
        namen = sorted(os.listdir(config))
    except OSError:
        namen = []
    for n in namen:
        stamm = n[:-4]
        # "Amiga1.cfg" ist Platz 1 der Einstellung "Amiga" (Minimig
        # nummeriert gespeicherte Fassungen so) - kein eigener Setname.
        if (stamm[-1:].isdigit()
                and os.path.isfile(os.path.join(config, stamm[:-1] + ".cfg"))):
            continue
        if n.lower().endswith(".cfg") and _ist_ags(
                minimig_cfg_lesen(os.path.join(config, n))):
            name = stamm
            return ("_Computer/Minimig", "<setname>%s</setname>" % name,
                    name, os.path.join(config, n))
    return "_Computer/Minimig", "<setname>Amiga</setname>", "Amiga", ""


def amiga_diskette_start(ordner=None, config=None, wurzel=None):
    """Mit welchen Einstellungen eine ADF startet: (Setname-Element,
    Setname) oder None (= der Minimig mit seinen eigenen).

    Hat config/Minimig.cfg einen vorhandenen Kickstart, bleibt es bei
    None. Sonst wird eine Minimig-MGL mit Setname gesucht, deren
    Einstellungsdatei
    da ist, deren Kickstart da ist und die KEINE AmigaVision-Festplatte
    einhaengt - "Amiga500" (vom AmigaVision-Paket) zuerst. Gibt es die
    nicht, tut es die AmigaVision-Einstellung auch: ein Amiga bootet von
    der Diskette in df0, bevor er auf die Festplatte schaut."""
    config = config or CONFIG_ORDNER
    # Hat der Minimig selbst eine Einstellung mit vorhandenem Kickstart,
    # bleibt es dabei - die hat der Nutzer sich eingerichtet.
    eigene = minimig_cfg_lesen(os.path.join(config, "Minimig.cfg"))
    if eigene and os.path.isfile(mister_pfad(eigene["kickstart"], wurzel)):
        return None
    gut, ags = [], []
    for _mgl, _rbf, el, name in minimig_mgls(ordner):
        if not name:
            continue
        cfg = minimig_cfg_lesen(os.path.join(config, name + ".cfg"))
        if not cfg or not os.path.isfile(mister_pfad(cfg["kickstart"],
                                                      wurzel)):
            continue
        if _ist_ags(cfg):
            ags.append((name.lower() != "amiga", el, name))
        else:
            gut.append((name.lower() != "amiga500", name.lower(), el, name))
    if gut:
        gut.sort()
        return gut[0][2], gut[0][3]
    if ags:
        ags.sort()
        return ags[0][1], ags[0][2]
    return None


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


def dos_mgl_fehlend(mgl_pfad, basen=None):
    """Die Abbilder einer 0MHz-MGL, die auf KEINER Wurzel liegen - als
    Pfade, wie sie in der MGL stehen. Leer, wenn alles da ist (Build 331).

    NUTZERFRAGE: "bei der 0mhz collection muss ich die spiele entpacken
    damit die starten?" - Ja: die Sammlung kommt als ein ZIP je Spiel,
    darin _DOS Games/<Spiel>.mgl und games/ao486/media/<spiel>/. Eine
    Festplatte kann MiSTer nicht aus einem ZIP heraus einhaengen. Liegt
    nur die MGL da, startet der Core mit leerer Festplatte.

    Gesucht wird wie MiSTer selbst (Heimatordner AO486 auf jeder Wurzel)
    - und zusaetzlich in "ao486" klein geschrieben, denn so legt das
    0MHz-ZIP den Ordner an; auf USB oder NAS mit ext4 ist das ein
    anderer Ordner."""
    fehlt = []
    for p in _mgl_dateipfade(mgl_pfad):
        if p.startswith("../"):
            voll = [os.path.normpath(os.path.join(SD_WURZEL, "games",
                                                  "AO486", p))]
        else:
            voll = [os.path.join(b, o, p) for b in (basen or _basen())
                    for o in ("AO486", "ao486")]
        if not any(os.path.exists(v) for v in voll):
            fehlt.append(p)
    return fehlt


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
            kern = ags_kern()
            for datei, ordnername in AMIGAVISION_LISTEN:
                namen, herkunft, start = amigavision_namen(inst, datei, kern)
                if not namen:
                    continue
                LOG("AmigaVision: %s aus %s (%s)" % (
                    datei, herkunft,
                    "Startnamen" if start else "nur Anzeigenamen"))
                # Angezeigt wird ohne "(OCS)[en]", gestartet mit dem
                # vollen Namen - der steht im Pfad.
                items = [(anzeigename(n) if start else n, "game",
                          (os.path.join(inst, "games", n), ".ags",
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
        # Build 331: genau so starten wie AmigaVisions eigene MGL - mit
        # deren rbf und deren Setname (siehe amigavision_start()).
        ags_rbf, el, setname_ags, herkunft = amigavision_start()
        # Build 332: der Heimatordner haengt am Setnamen - ausser mit
        # same_dir="1", dann bleibt es der des Minimig, also "Amiga".
        kern = "Amiga" if 'same_dir="1"' in el.replace("'", '"') \
            else setname_ags
        if not ags_boot_schreiben(inst, name, kern):
            LOG("AmigaVision: starte ohne ags_boot ins Menue")
        LOG("AmigaVision: %s mit Setname %s (aus %s)"
            % (name, setname_ags, herkunft or "Vorgabe"))
        return ('<mistergamedescription>\n'
                '\t<rbf>%s</rbf>\n'
                '\t%s\n'
                '</mistergamedescription>\n' % (ags_rbf, el))
    if _ist_core(rbf, "Minimig") and endung == ".adf" and not setname:
        start = amiga_diskette_start()
        if start:
            el, name = start
            LOG("Amiga: %s mit Setname %s" % (os.path.basename(rom_path),
                                              name))
            return ('<mistergamedescription>\n\t<rbf>%s</rbf>\n\t%s\n%s'
                    '</mistergamedescription>\n'
                    % (rbf, el, _datei_xml(delay, ftype, index, rom_path)))
        LOG("Amiga: keine Einstellung mit Kickstart gefunden - %s startet "
            "mit den eigenen des Minimig" % os.path.basename(rom_path))
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
    if syskey == "AMIGA" and endung == ".ags":
        # Build 333: ein Anzeigename fuehrt nur ins AmigaVision-Menue -
        # vorher sagen, warum und wie man es einmalig behebt.
        name = os.path.basename(str(rom_path))
        if not ist_startname(name):
            return ("hinweis_av_titel",
                    [("hinweis_av_grund", ()), ("hinweis_av_shell", ()),
                     ("hinweis_av_befehl", ("Game", "games")),
                     ("hinweis_av_befehl", ("Demo", "demos")),
                     ("hinweis_av_avs", ())])
        return None
    if syskey == "AO486" and endung == ".mgl":
        fehlt = dos_mgl_fehlend(rom_path)
        if fehlt:
            return ("hinweis_dos_titel",
                    [("hinweis_dos_fehlt", (fehlt[0],)),
                     ("hinweis_dos_zip", ())])
    return None


def _lesen(pfad):
    with open(pfad, "rb") as f:
        return f.read(400 * 1024)


# ---------------------------------------------------------------------------
# Der Computer-Check (System -> Wartung)
# ---------------------------------------------------------------------------
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
        # Build 331: was der Minimig beim Start tatsaechlich liest -
        # fehlt hier etwas, landet er beim Kickstart-Bild.
        _r, _el, name, herkunft = amigavision_start(core_ordner)
        cfg_pfad = os.path.join(CONFIG_ORDNER, name + ".cfg")
        cfg = minimig_cfg_lesen(cfg_pfad)
        zeilen.append((bool(herkunft), "check_av_mgl", (name,)))
        zeilen.append((cfg is not None, "check_av_cfg",
                       ("config/%s.cfg" % name,)))
        if cfg:
            kick = cfg["kickstart"]
            zeilen.append((bool(kick) and os.path.isfile(mister_pfad(kick)),
                           "check_av_kick", (kick or "-",)))
            for h in cfg["hdf"][:2]:
                zeilen.append((os.path.isfile(mister_pfad(h)),
                               "check_av_hdf", (h,)))
            # Build 332: genau sein Fall - die Einstellungsdatei war da,
            # aber AmigaVision.hdf nicht als Festplatte eingetragen.
            if not _ist_ags(cfg):
                zeilen.append((False, "check_av_hdf_fehlt", ()))
        # Build 333: Startnamen oder nur Anzeigenamen?
        kern = "Amiga" if 'same_dir="1"' in _el.replace("'", '"') else name
        _n, herkunft, start = amigavision_namen(inst, "games.txt", kern)
        if start:
            zeilen.append((True, "check_av_startnamen", (herkunft,)))
        elif _n:
            zeilen.append((False, "check_av_anzeigenamen", ()))
        # Build 332: wohin ags_boot geht - der Ordner, den der Amiga als
        # MiSTer: sieht (mister_laufwerk()).
        zeilen.append((None, "check_av_laufwerk", (mister_laufwerk(kern),)))
    else:
        zeilen.append((False, "check_amigavision_fehlt", ()))
    disk = amiga_diskette_start(core_ordner)
    zeilen.append((None, "check_adf_mit", (disk[1] if disk else "Minimig",)))
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
    ohne = [n for n, p in mgls if dos_mgl_fehlend(p, basen)]
    raus.append(("DOS (ao486)", [
        (bool(ao_core), "check_core", (ao_core or "ao486",)),
        (bool(ao), "check_ordner", ("games/AO486",)),
        (roms, "check_ao486_roms", ()),
        (None, "check_dos_mgls", (len(mgls),)),
        (not ohne, "check_dos_fehlt", (len(ohne),)),
    ]))
    return raus
