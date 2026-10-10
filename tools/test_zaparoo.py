#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Zaparoo (NFC-Tags) anbinden (Build 251).

Zaparoo (vormals TapTo) ist ein eigenes Projekt: es liest am MiSTer
NFC-Tags und startet das Spiel, das darauf steht. Wir binden es an -
erkennen, starten, und den einen ZapScript-Befehl nennen, den man in
der Zaparoo-App auf einen Tag schreibt.

DIE WICHTIGSTE ZUSAGE DIESES TESTS IST EINE UNTERLASSUNG: in
/media/fat/zaparoo wird NICHTS geschrieben. Dort liegen Konfiguration
und Zuordnungen eines fremden Programms - dieselbe Haltung wie bei
/media/fat/docs (fremde Artwork-Datenbank) und MiSTers Favoritendatei.
Und das Protokoll von Zaparoo wird nicht ausgewertet, genau wie bei
update_all: ein Logleser haengt am Zeilenformat eines fremden
Programms.

WORAN ES SONST SCHEITERN KANN

  1. Ein Pfad ist falsch geraten. Deshalb stehen die Pfade im Test
     noch einmal ausgeschrieben - wer sie im Modul aendert, stolpert
     hier und muss nachsehen, ob die Quelle das wirklich sagt.
  2. Der alte Name TapTo wird vergessen. Wer von damals kommt, hat das
     Skript unter dem alten Namen.
  3. Eine fehlende Datei oder ein unlesbares Verzeichnis wirft.
  4. Der ZapScript-Befehl ist falsch - dann tippt man ihn ab und
     nichts passiert.
  5. Der Menuepunkt verschweigt den Stand, und man muss hineingehen,
     um zu sehen, ob der Dienst laeuft.

Ausfuehren:
    python3 tools/test_zaparoo.py
"""
import io
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H                                        # noqa: E402

import fe.zaparoo as ZAP                                    # noqa: E402
import fe.translations as TR                                # noqa: E402

fm = H.fm
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_QF = io.open(os.path.join(_REPO, "frontend", "frontend.py"),
              encoding="utf-8").read()
_ZQ = io.open(os.path.join(_REPO, "frontend", "fe", "zaparoo.py"),
              encoding="utf-8").read()
fails = []
_TMP = tempfile.mkdtemp(prefix="zaparoo_")


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


# ---------------------------------------------------------------------------
print("Test 1: die Pfade stimmen mit der Quelle ueberein")
# ---------------------------------------------------------------------------
# AUSGESCHRIEBEN, NICHT AUS DEM MODUL GELESEN. Ein Test, der die
# Konstante gegen sich selbst prueft, prueft nichts. Diese Werte
# stammen aus zaparoo.org/docs (Plattform MiSTer) - wer sie im Modul
# aendert, soll hier stolpern und noch einmal nachsehen.
for _soll, _ist, _was in (
        ("/media/fat/Scripts/zaparoo.sh", ZAP.SKRIPT_KANDIDATEN[0],
         "Skript"),
        ("/media/fat/Scripts/tapto.sh", ZAP.SKRIPT_KANDIDATEN[1],
         "Skript (alter Name)"),
        ("/media/fat/zaparoo", ZAP.DATEN, "Datenordner"),
        ("/media/fat/zaparoo/config.toml", ZAP.KONFIG, "Konfiguration"),
        ("/media/fat/zaparoo/mappings", ZAP.MAPPINGS, "Zuordnungen"),
        ("/media/fat/linux/user-startup.sh", ZAP.STARTUP, "Startdatei")):
    check("%-22s %s" % (_was, _soll), _ist == _soll, _ist)

# ---------------------------------------------------------------------------
print()
print("Test 2: es wird NICHTS in Zaparoos Ordner geschrieben")
# ---------------------------------------------------------------------------
# DIE WICHTIGSTE ZUSAGE, und sie ist eine Unterlassung - deshalb wird
# sie am Quelltext geprueft und nicht am Verhalten: ein Verhaltenstest
# koennte nur zeigen, dass dieser EINE Durchlauf nichts geschrieben hat.
# OHNE DEN MODUL-DOCSTRING, und das ist nicht Pedanterie: der erste
# Entwurf dieses Tests suchte "core.log" im Quelltext und wurde rot am
# eigenen Modulkopf, der erklaert, WARUM das Protokoll nicht gelesen
# wird. Derselbe Fehler wie in Build 250 bei test_core_neu.py - ein
# Test, der die Begruendung als Verstoss zaehlt, ist kein Test.
_code = _ZQ.split('"""', 2)[-1]
_code = "\n".join(z for z in _code.split("\n")
                  if not z.strip().startswith("#"))
for _verboten, _was in (('open(', "oeffnen zum Schreiben"),
                        ("makedirs", "Ordner anlegen"),
                        ("os.replace", "Dateien ersetzen"),
                        ("os.remove", "loeschen"),
                        ("shutil", "kopieren/verschieben")):
    # open() gibt es einmal, und zwar lesend auf user-startup.sh.
    if _verboten == 'open(':
        _schreibend = ('"w"' in _code or "'w'" in _code
                       or '"a"' in _code or "'a'" in _code
                       or '"wb"' in _code or "'wb'" in _code)
        check("kein Schreibzugriff (%s)" % _was, not _schreibend,
              "in /media/fat/zaparoo liegt ein fremdes Programm")
        continue
    check("kein %s" % _was, _verboten not in _code)
check("das Protokoll von Zaparoo wird nicht gelesen",
      "core.log" not in _code,
      "dieselbe Absage wie bei update_all - ein Logleser haengt am "
      "Zeilenformat eines fremden Programms")
check("und die Begruendung steht im Modulkopf",
      "fremdes Verzeichnis" in _ZQ or "nicht unser Verzeichnis" in _ZQ)

# ---------------------------------------------------------------------------
print()
print("Test 3: erkennen - installiert, Dienst, laeuft")
# ---------------------------------------------------------------------------
_alt = (ZAP.SKRIPT_KANDIDATEN, ZAP.STARTUP, ZAP.MAPPINGS, ZAP.LAUFSPUR)
try:
    _skript = os.path.join(_TMP, "zaparoo.sh")
    _alt_skript = os.path.join(_TMP, "tapto.sh")
    ZAP.SKRIPT_KANDIDATEN = (_skript, _alt_skript)
    ZAP.STARTUP = os.path.join(_TMP, "user-startup.sh")
    ZAP.MAPPINGS = os.path.join(_TMP, "mappings")
    ZAP.LAUFSPUR = os.path.join(_TMP, "lauf")

    check("ohne Skript: nicht installiert", not ZAP.installiert())
    check("und skript_pfad() ist None", ZAP.skript_pfad() is None)
    io.open(_skript, "w").write("#!/bin/sh\n")
    check("mit Skript: installiert", ZAP.installiert())
    check("und der Pfad kommt zurueck", ZAP.skript_pfad() == _skript)

    # Der ALTE NAME muss gehen - wer von TapTo kommt, hat ihn noch.
    os.remove(_skript)
    io.open(_alt_skript, "w").write("#!/bin/sh\n")
    check("der alte Name TapTo zaehlt auch", ZAP.installiert(),
          "wer von damals kommt, hat das Skript so liegen")
    io.open(_skript, "w").write("#!/bin/sh\n")
    check("und bei beiden gewinnt der neue", ZAP.skript_pfad() == _skript)

    # Dienst
    check("ohne user-startup.sh: kein Dienst", not ZAP.dienst_eingetragen())
    io.open(ZAP.STARTUP, "w").write("#!/bin/sh\n# nichts\n")
    check("mit leerer Startdatei: kein Dienst",
          not ZAP.dienst_eingetragen())
    io.open(ZAP.STARTUP, "w").write("#!/bin/sh\n#mrext/zaparoo -service\n")
    check("eine AUSKOMMENTIERTE Zeile zaehlt nicht",
          not ZAP.dienst_eingetragen(),
          "sonst meldet das Frontend einen Dienst, den niemand startet")
    io.open(ZAP.STARTUP, "w").write("#!/bin/sh\n/media/fat/linux/mrext/zaparoo\n")
    check("eine echte Zeile zaehlt", ZAP.dienst_eingetragen())
    io.open(ZAP.STARTUP, "w").write("#!/bin/sh\nMRext/TapTo -service\n")
    check("auch der alte Name, Gross/Klein egal",
          ZAP.dienst_eingetragen())

    # Laeuft
    check("ohne Laufordner: laeuft nicht", not ZAP.laeuft())
    os.makedirs(ZAP.LAUFSPUR)
    check("mit Laufordner: laeuft", ZAP.laeuft())

    # Tags zaehlen, auch in Unterordnern
    check("ohne mappings-Ordner: 0", ZAP.tags_gezaehlt() == 0)
    os.makedirs(os.path.join(ZAP.MAPPINGS, "unten"))
    io.open(os.path.join(ZAP.MAPPINGS, "a.toml"), "w").write("x")
    io.open(os.path.join(ZAP.MAPPINGS, "unten", "b.TOML"), "w").write("x")
    io.open(os.path.join(ZAP.MAPPINGS, "nichts.txt"), "w").write("x")
    check("zwei .toml, auch im Unterordner, .txt nicht",
          ZAP.tags_gezaehlt() == 2, "%d" % ZAP.tags_gezaehlt())

    _st = ZAP.stand()
    check("stand() liefert alle Felder",
          set(_st) == {"pfad", "installiert", "dienst", "laeuft", "tags"},
          str(sorted(_st)))
finally:
    (ZAP.SKRIPT_KANDIDATEN, ZAP.STARTUP, ZAP.MAPPINGS,
     ZAP.LAUFSPUR) = _alt

# ---------------------------------------------------------------------------
print()
print("Test 4: der ZapScript-Befehl")
# ---------------------------------------------------------------------------
# "**launch:<Pfad>" ist der eine ZapScript-Befehl, der einen Dateipfad
# direkt nimmt (zaparoo.org/docs, Abschnitt Launch). Ist er falsch,
# tippt der Nutzer ihn ab und nichts passiert - deshalb steht er hier
# ausgeschrieben.
for _pfad, _erw in (
        ("/media/fat/games/SNES/Mario.sfc",
         "**launch:/media/fat/games/SNES/Mario.sfc"),
        ("/media/fat/games/Genesis/Sonic.md",
         "**launch:/media/fat/games/Genesis/Sonic.md"),
        ("  /media/fat/x.sfc  ", "**launch:/media/fat/x.sfc"),
        ("", ""),
        (None, "")):
    check("%-38r -> %r" % (_pfad, _erw),
          ZAP.zapscript_fuer(_pfad) == _erw,
          repr(ZAP.zapscript_fuer(_pfad)))
# Der Pfad darf NICHT umgeschrieben werden - bei einem ZIP-Archiv
# steht der Eintrag darin mit im Pfad, und MiSTer kommt damit zurecht.
_zip = "/media/fat/games/SNES/Sammlung.zip/Mario.sfc"
check("ein Pfad durch ein ZIP-Archiv bleibt ganz",
      ZAP.zapscript_fuer(_zip) == "**launch:" + _zip)

# spiel_pfad() holt den Pfad aus unserem Eintragsformat.
for _arg, _erw in ((("/f/x.sfc", ".sfc", "SNES", None, None), "/f/x.sfc"),
                   (["/f/y.md"], "/f/y.md"),
                   ((), ""), (None, ""), ("nurtext", "")):
    _ist = ZAP.spiel_pfad(_arg)
    check("spiel_pfad(%.30r) -> %r" % (_arg, _erw), _ist == _erw, repr(_ist))

# ---------------------------------------------------------------------------
print()
print("Test 5: angeschlossen")
# ---------------------------------------------------------------------------
H.set_screen(1920, 1080)
fe = H.make_frontend(page=0)
check("zaparoo_bildschirm() gibt es", hasattr(fe, "zaparoo_bildschirm"))
check("die Aktion wird behandelt", 'elif kind == "zaparoo":' in _QF)
check("mit Netz gegen einen Absturz darin",
      "zaparoo_bildschirm CRASH" in _QF)
_blk = "\n".join(z for z in _QF.split("\n")
                 if not z.strip().startswith("#"))
_scr = _blk.split("def zaparoo_bildschirm")[1].split("\n    def ")[0]
check("gestartet wird ueber run_script()", "self.run_script(" in _scr,
      "kein eigener Startweg - dasselbe wie bei update_all")
check("der Befehl wird umgebrochen, nicht abgeschnitten",
      "self._wrap(_befehl" in _scr,
      "ein halber ROM-Pfad waere wertlos")
check("die Liste kommt aus 'Zuletzt gespielt'", "load_recent()" in _scr,
      "einen Tag legt man fuer ein Spiel an, das man gerade gespielt "
      "hat - die Liste gibt es schon")
check("ohne Pfad kein Eintrag", "if _p:" in _scr,
      "ohne Pfad kein Tag - dann lieber nicht anzeigen")

import fe.menu as MENU                                     # noqa: E402
_sys = MENU.system_items(False, "lokal", "")
_alle = []
_rest = [_sys]
while _rest:
    _n = _rest.pop()
    if not isinstance(_n, dict):
        continue
    _alle.extend(_n.get("items") or ())
    _rest.extend((_n.get("folders") or {}).values())
_treffer = [e for e in _alle if len(e) > 1 and e[1] == "zaparoo"]
check("der Menuepunkt steht im Systemmenue", len(_treffer) == 1,
      "%d von %d Eintraegen" % (len(_treffer), len(_alle)))
check("und seine Beschriftung sagt den Stand",
      _treffer and len(_treffer[0][0]) > 10, str(_treffer[:1]))

for _schl in ("sys_zaparoo", "sys_zaparoo_fehlt", "zaparoo_titel",
              "zaparoo_installiert", "zaparoo_dienst_an",
              "zaparoo_dienst_aus", "zaparoo_laeuft",
              "zaparoo_laeuft_nicht", "zaparoo_tags", "zaparoo_spiele",
              "zaparoo_befehl", "zaparoo_keine_spiele", "zaparoo_fehlt",
              "zaparoo_hinweis", "zaparoo_hinweis_fehlt"):
    _e = TR.TRANSLATIONS.get(_schl)
    check("%-24s zweisprachig" % _schl,
          bool(_e) and bool(_e.get("de")) and bool(_e.get("en")))

# ---------------------------------------------------------------------------
print()
print("Test 6: nichts wirft, auch wenn alles fehlt")
# ---------------------------------------------------------------------------
_alt = (ZAP.SKRIPT_KANDIDATEN, ZAP.STARTUP, ZAP.MAPPINGS, ZAP.LAUFSPUR)
try:
    _nix = os.path.join(_TMP, "gibtsnicht")
    ZAP.SKRIPT_KANDIDATEN = (os.path.join(_nix, "a.sh"),)
    ZAP.STARTUP = os.path.join(_nix, "b.sh")
    ZAP.MAPPINGS = os.path.join(_nix, "c")
    ZAP.LAUFSPUR = os.path.join(_nix, "d")
    for _fn, _name in ((ZAP.installiert, "installiert"),
                       (ZAP.dienst_eingetragen, "dienst_eingetragen"),
                       (ZAP.laeuft, "laeuft"),
                       (ZAP.tags_gezaehlt, "tags_gezaehlt"),
                       (ZAP.skript_pfad, "skript_pfad"),
                       (ZAP.stand, "stand")):
        try:
            _fn()
            _ok, _f = True, ""
        except Exception as e:                           # noqa: BLE001
            _ok, _f = False, "%s: %s" % (type(e).__name__, e)
        check("%s() wirft nicht" % _name, _ok, _f)
    # Und eine Startdatei, die ein Verzeichnis ist (der boeseste Fall).
    os.makedirs(os.path.join(_nix, "ordner"), exist_ok=True)
    ZAP.STARTUP = os.path.join(_nix, "ordner")
    try:
        ZAP.dienst_eingetragen()
        _ok, _f = True, ""
    except Exception as e:                               # noqa: BLE001
        _ok, _f = False, "%s: %s" % (type(e).__name__, e)
    check("auch wenn user-startup.sh ein Ordner ist", _ok, _f)
finally:
    (ZAP.SKRIPT_KANDIDATEN, ZAP.STARTUP, ZAP.MAPPINGS,
     ZAP.LAUFSPUR) = _alt

shutil.rmtree(_TMP, ignore_errors=True)
print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
