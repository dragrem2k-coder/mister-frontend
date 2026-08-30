#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft, dass Spiele auf einer Netzwerk-Freigabe NICHT bei jedem Start
neu eingelesen werden.

Hintergrund (Nutzer-Rueckmeldung ueber einen Bekannten): "seine Spiele
liegen auf einem NAS, er hat das Problem, dass bei jedem Neustart die
Spiele wieder neu eingelesen werden."

Die Ursache liess sich im Code festmachen. Die Signatur, an der das
Frontend erkennt "hat sich etwas geaendert?", kennzeichnet jeden
Ablageort mit einer kurzen Kennung. Die lautete:

    tag = "usb:" if "/media/usb" in base else "fat:"

Ein NAS haengt ueblicherweise unter /media/fat/cifs/... - es bekam damit
dieselbe Kennung wie die SD-Karte. Beim Kaltstart ist die Freigabe aber
oft noch nicht eingehaengt: die frische Signatur enthaelt die NAS-Ordner
dann nicht, der gespeicherte Stand (vom letzten Lauf MIT NAS) schon ->
Unterschied -> alles neu einlesen. Fuer USB gab es dagegen laengst ein
Sicherheitsnetz ("Cache erwartet USB, USB fehlt -> warten"), das beim
NAS mangels eigener Kennung nie ansprang.

Geprueft wird deshalb genau das, was sich ohne echtes NAS objektiv
nachstellen laesst: die Kennzeichnung der Ablageorte und die
Unterscheidbarkeit gleichnamiger Ordner.

Ausfuehren:
    python3 tools/test_nas_cache.py
"""
import os
import sys
import shutil
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_FRONTEND_DIR = os.path.dirname(
    os.environ.get("FRONTEND_PY",
                   os.path.join(os.path.dirname(_HERE), "frontend",
                                "frontend.py")))
sys.path.insert(0, _FRONTEND_DIR)

import fe.paths                                   # noqa: E402
import fe.scan as S                               # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


TMP = tempfile.mkdtemp(prefix="nas_test_")
# Die Ordnernamen bilden die echten MiSTer-Pfade nach: die
# USB-Erkennung im Code prueft woertlich auf "/media/usb", der Test
# muss also unter einem entsprechend benannten Pfad arbeiten.
SD = os.path.join(TMP, "media", "fat", "games")
NAS = os.path.join(TMP, "media", "fat", "cifs", "meinserver", "games")
USB = os.path.join(TMP, "media", "usb0", "games")
for d in (SD, NAS, USB):
    os.makedirs(os.path.join(d, "SNES"))
    open(os.path.join(d, "SNES", "spiel.sfc"), "w").close()

# /proc/mounts nachbilden: der NAS-Pfad ist eine CIFS-Freigabe
_echte_mounts = S._netz_mountpunkte
S._netz_mountpunkte = lambda: [os.path.join(TMP, "media", "fat", "cifs", "meinserver")]


def signatur(basen):
    alt = fe.paths.GAMES_BASES
    try:
        fe.paths.GAMES_BASES = basen
        sig, per = S._games_signature()
        return sig, per
    finally:
        fe.paths.GAMES_BASES = alt


print("Test 1: jeder Ablageort bekommt eine EIGENE Kennung")
sig, _ = signatur([SD, NAS, USB])
kennungen = {e[0].split(":")[0] for e in sig}
check("SD-Karte, NAS und USB sind unterscheidbar",
      {"fat", "nas", "usb"} <= kennungen, str(sorted(kennungen)))
check("die Freigabe ist als 'nas:' gekennzeichnet",
      any(e[0] == "nas:SNES" for e in sig),
      str(sorted(e[0] for e in sig)))
ordner = sorted(e[0] for e in sig if e[0].endswith("SNES"))
check("ein gleichnamiger Ordner auf Karte, NAS und USB kollidiert nicht",
      ordner == ["fat:SNES", "nas:SNES", "usb:SNES"], str(ordner))

print()
print("Test 2: ohne eingehaengte Freigabe faellt der NAS-Teil weg")
S._netz_mountpunkte = lambda: []
sig_ohne, _ = signatur([SD, USB])
check("Signatur ohne NAS enthaelt keinen 'nas:'-Eintrag",
      not S._sig_expects(sig_ohne, "nas:"))
check("_sig_expects erkennt den Unterschied",
      S._sig_expects(sig, "nas:") and not S._sig_expects(sig_ohne, "nas:"))
S._netz_mountpunkte = lambda: [os.path.join(TMP, "media", "fat", "cifs", "meinserver")]

print()
print("Test 3: genau die Lage, die den Fehler ausgeloest hat")
# Gespeicherter Stand: MIT NAS.  Kaltstart: NAS noch nicht da.
check("gespeicherter Stand erwartet eine Freigabe",
      S._sig_expects(sig, "nas:"))
check("frische Signatur beim Kaltstart hat keine",
      not S._sig_expects(sig_ohne, "nas:"))
check("daraus folgt: es MUSS gewartet statt neu eingelesen werden",
      S._sig_expects(sig, "nas:") and not S._sig_expects(sig_ohne, "nas:"))
check("das Sicherheitsnetz dafuer existiert jetzt",
      hasattr(S, "_wait_for_nas_mount"))

print()
print("Test 4: die Kennung ist ortsunabhaengig")
# Dieselbe Freigabe an einem ANDEREN Einhaengepunkt muss dieselbe
# Signatur ergeben - sonst wuerde ein Umhaengen wieder alles neu einlesen.
NAS2 = os.path.join(TMP, "media", "anderswo", "games")
os.makedirs(os.path.join(NAS2, "SNES"))
open(os.path.join(NAS2, "SNES", "spiel.sfc"), "w").close()
S._netz_mountpunkte = lambda: [os.path.join(TMP, "media", "anderswo")]
sig2, _ = signatur([NAS2])
S._netz_mountpunkte = lambda: [os.path.join(TMP, "media", "fat", "cifs", "meinserver")]
sig1, _ = signatur([NAS])
check("gleicher Ordnername -> gleicher Signatur-Schluessel",
      [e[0] for e in sig1] == [e[0] for e in sig2],
      "%s vs %s" % ([e[0] for e in sig1], [e[0] for e in sig2]))

print()
print("Test 5: das USB-Sicherheitsnetz funktioniert unveraendert weiter")
S._netz_mountpunkte = lambda: []
sig_usb, _ = signatur([SD, USB])
sig_nur_sd, _ = signatur([SD])
check("mit USB wird USB erwartet", S._sig_expects_usb(sig_usb))
check("ohne USB nicht", not S._sig_expects_usb(sig_nur_sd))

print()
print("Test 6: die Aufschluesselung nach System bleibt heil")
S._netz_mountpunkte = lambda: [os.path.join(TMP, "media", "fat", "cifs", "meinserver")]
sig3, per = signatur([SD, NAS, USB])
check("SNES ist in der Aufschluesselung enthalten", "SNES" in per)
check("und enthaelt alle drei Ablageorte",
      len(per.get("SNES", [])) == 3, str(per.get("SNES")))

print()
print("Test 7: das automatische Nachziehen darf nicht bei JEDEM Start laufen")
# BUGFIX-ABSICHERUNG (Nutzer-Rueckmeldung: "scannt schon wieder", auch
# nachdem die Signatur-Kennung stimmte): das Sicherheitsnetz fuer spaet
# auftauchende Netzlaufwerke fragte nur, OB eine Freigabe eingehaengt
# ist - nicht, ob sie beim Einlesen der Spiele gefehlt hatte. Bei einem
# NAS, das rechtzeitig da ist, erzwang es dadurch bei jedem Start einen
# kompletten Neuaufbau, wenige Sekunden nach dem Hochfahren.
S._netz_mountpunkte = lambda: [os.path.join(TMP, "media", "fat", "cifs", "meinserver")]
signatur([SD, NAS, USB])
check("nach einem Einlesen MIT Freigabe: nichts nachzuholen",
      S.letzter_scan_hatte_nas())
S._netz_mountpunkte = lambda: []
signatur([SD, USB])
check("nach einem Einlesen OHNE Freigabe: Nachziehen bleibt sinnvoll",
      not S.letzter_scan_hatte_nas())

S._netz_mountpunkte = _echte_mounts
shutil.rmtree(TMP, ignore_errors=True)

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for f in fails:
        print("   ", f)
    sys.exit(1)
print("Alle Tests bestanden.")
