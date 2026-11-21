#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Umlaute in MiSTer.ini und retroachievements.cfg (Build 339).

NUTZER nach dem Update: "bleibt das frontend im welcome to mister
login: stehen". Sein Log:

    crt_menu_active()  return "[Menu]" in open(MISTER_INI).read()
    UnicodeDecodeError: 'utf-8' codec can't decode byte 0xe4

Ein "ae" in latin-1 (0xe4) in seiner MiSTer.ini. Kein OSError - also
fing es kein except, und das Frontend stuerzte beim Start ab.

GEPRUEFT WIRD:
  1. Alle Leser von MiSTer.ini ueberleben latin-1 UND UTF-8 und finden
     ihre ASCII-Eintraege ([Menu], fb_size).
  2. Die eine Schreibstelle ([Menu]-Block) gibt den Rest der Datei Byte
     fuer Byte zurueck, die Sicherung ist eine Byte-Kopie.
  3. retroachievements.cfg: ein Schalter schreibt nur seine Zeile - ein
     Passwort mit latin-1- oder UTF-8-Zeichen bleibt Byte fuer Byte.
  4. Die cifs-Erkennung in user-startup.sh ueberlebt latin-1.
  5. GEGENPROBE: so wie bis Build 338 gelesen, wirft die Datei wirklich.

Ausfuehren:
    python3 tools/test_umlaut_in_ini.py
"""
import os
import shutil
import sys
import tempfile

_HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_HIER), "frontend"))

import fe.settings as SE                                 # noqa: E402
import fe.ra_settings as RS                              # noqa: E402
import fe.scan as SC                                     # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


print(__doc__.strip().split("\n")[0])
print()
TMP = tempfile.mkdtemp(prefix="umlaut_")
_alt = (SE.MISTER_INI, RS.RA_SETTINGS_FILE, SC.USER_STARTUP_FILE)
try:
    LATIN = ("[MiSTer]\r\n; Einstellungen f\xe4r den Fernseher\n"
             "video_mode=8\nfb_size=2\n\n[Menu]\nvideo_mode=0\n").encode("latin-1")
    UTF8 = ("[MiSTer]\n; Einstellungen für den Fernseher – groß\n"
            "video_mode=8\nfb_size=1\n").encode("utf-8")
    # -----------------------------------------------------------------------
    print("Test 1: lesen")
    # -----------------------------------------------------------------------
    ini = os.path.join(TMP, "MiSTer.ini")
    SE.MISTER_INI = ini
    for name, inhalt in (("latin-1", LATIN), ("UTF-8", UTF8)):
        open(ini, "wb").write(inhalt)
        try:
            SE.crt_menu_active()
            SE.fb_size_value()
            SE.mister_ini_video_zustand()
            SE.crt_menu_block_is_ours()
            ok, fehler = True, None
        except Exception as e:                           # noqa: BLE001
            ok, fehler = False, e
        check("%s: crt_menu_active, fb_size_value, Block-Pruefung - kein "
              "Absturz" % name, ok and fehler is None, fehler)
    open(ini, "wb").write(LATIN)
    check("latin-1: [Menu] gefunden", SE.crt_menu_active() is True)
    check("latin-1: fb_size gelesen", SE.fb_size_value() == 2,
          SE.fb_size_value())
    try:
        open(ini, encoding="utf-8").read()
        check("GEGENPROBE: als UTF-8 gelesen wirft die Datei", False)
    except UnicodeDecodeError:
        check("GEGENPROBE: als UTF-8 gelesen wirft die Datei", True)

    # -----------------------------------------------------------------------
    print()
    print("Test 2: die eine Schreibstelle")
    # -----------------------------------------------------------------------
    for name, inhalt in (("latin-1", LATIN), ("UTF-8", UTF8)):
        open(ini, "wb").write(inhalt)
        for rest in (ini + ".dragend_backup",):
            if os.path.exists(rest):
                os.remove(rest)
        text = SE._mister_ini_lesen()
        neu = text + "\n; angehaengt\n"
        check("%s: geschrieben" % name, SE._mister_ini_schreiben(neu) is True)
        roh = open(ini, "rb").read()
        erwartet = inhalt.replace(b"\r\n", b"\n") + b"\n; angehaengt\n"
        check("%s: der Rest der Datei Byte fuer Byte erhalten" % name,
              roh == erwartet, roh[:80])
        check("%s: die Sicherung ist eine Byte-Kopie" % name,
              open(ini + ".dragend_backup", "rb").read() == inhalt)

    # -----------------------------------------------------------------------
    print()
    print("Test 3: retroachievements.cfg")
    # -----------------------------------------------------------------------
    cfg = os.path.join(TMP, "retroachievements.cfg")
    RS.RA_SETTINGS_FILE = cfg
    for name, pw in (("latin-1", "geheim\xe4\xdf".encode("latin-1")),
                     ("UTF-8", "geheimäß€".encode("utf-8"))):
        inhalt = (b"# Kommentar\nusername=spieler\npassword=" + pw
                  + b"\nshow_popups=1\nunbekannt=wert\n")
        open(cfg, "wb").write(inhalt)
        try:
            RS.roh_schreiben("show_popups", "0")
            fehler = None
        except Exception as e:                           # noqa: BLE001
            fehler = e
        roh = open(cfg, "rb").read()
        check("%s: Schalter geschrieben, kein Absturz" % name,
              fehler is None and b"show_popups=0" in roh, fehler)
        check("%s: Passwort Byte fuer Byte erhalten" % name,
              (b"password=" + pw + b"\n") in roh)
        check("%s: alles andere unveraendert" % name,
              roh == inhalt.replace(b"show_popups=1", b"show_popups=0"), roh)

    # -----------------------------------------------------------------------
    print()
    print("Test 4: user-startup.sh")
    # -----------------------------------------------------------------------
    us = os.path.join(TMP, "user-startup.sh")
    SC.USER_STARTUP_FILE = us
    open(us, "wb").write("# f\xe4r das NAS\nmount -t cifs //nas/x /media/fat/cifs\n"
                         .encode("latin-1"))
    try:
        r, fehler = SC._autostart_has_cifs_entry(), None
    except Exception as e:                               # noqa: BLE001
        r, fehler = None, e
    check("cifs in user-startup.sh trotz Umlaut erkannt, kein Absturz",
          fehler is None and r is True, (r, fehler))
finally:
    SE.MISTER_INI, RS.RA_SETTINGS_FILE, SC.USER_STARTUP_FILE = _alt
    shutil.rmtree(TMP, ignore_errors=True)

print()
if fails:
    print("ROT: %d Pruefung(en) fehlgeschlagen:" % len(fails))
    for f_ in fails:
        print("   - " + f_)
    sys.exit(1)
print("ALLES GRUEN")
