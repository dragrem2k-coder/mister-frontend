#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""stream_state(): der Systemkey kommt vom EINTRAG, nicht von der
Kategorie (Build 261).

AUSLOESER (Nutzer-Rueckmeldung, direkt nach Build 260): "aus den
Kategorien geht es jetzt super, wenn ich die Spiele aber aus Zuletzt
gespielt, Weiterspielen, Zufalls-Zock, RA-Erfolgsjaeger, Sammlungen
starte, werden keine Covers mit angezeigt."

Diese Kategorien MISCHEN Systeme - ein Eintrag kann aus SNES kommen,
der naechste aus Mega Drive. Die Kategorie selbst hat deshalb keinen
Systemkey (syskey=None), und stream_state() hat genau diesen Key
weitergereicht. Im Overlay fehlte damit nicht nur das Cover
(/art braucht sys=), sondern auch Genre, Jahr und der RA-Fortschritt.

ZWEI BUILDS, ZWEI VERSCHIEDENE URSACHEN - und das ist der Grund, warum
dieser Test getrennt von test_overlay_cover.py steht:

  * Build 260: der Server fand die DATEI nicht (eigene Suche, nur
    ".art"). Das traf ALLE Kategorien.
  * Build 261: der Server bekommt gar nicht erst gesagt, in WELCHEM
    System er suchen soll. Das trifft nur die gemischten Kategorien.

Beim ersten Mal hatte ich auf diese zweite Ursache getippt, und der
Nutzer hat sie mit einer Gegenprobe widerlegt ("aus einer echten
Systemkategorie starten - auch kein Cover"). Die Vermutung war nicht
falsch, sie war nur VERDECKT: Build 260 musste erst weg, damit sie
ueberhaupt sichtbar werden konnte. Beide Tests bleiben deshalb stehen.

KEINE ZWEITE REGEL: benutzt wird _item_syskey() - dieselbe Funktion,
mit der auch der Zeichenweg das Cover eines gemischten Eintrags findet
(seit Build 122). Dieselbe Lehre wie in Build 260.

Ausfuehren:
    python3 tools/test_overlay_zustand.py
"""
import io
import os
import sys

_HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HIER)
import _harness as H                                    # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


def spiel(titel, syskey, endung=".sfc"):
    """Ein Eintrag, wie ihn der Scanner baut: der Systemkey steckt an
    Stelle 2 des arg-Tupels."""
    return (titel, "game", ("/games/%s/%s%s" % (syskey, titel, endung),
                            endung, syskey, None, None))


H.set_screen(1280, 720)
FE = H.make_frontend(page=1)

# ---------------------------------------------------------------------------
print("Test 1: eine normale Systemkategorie - unveraendert")
# ---------------------------------------------------------------------------
name, node, _ = FE.cats[0]
FE.cats[0] = (name, node, "SNES")
node["folders"] = {}
node["items"] = [spiel("Super Mario World (USA)", "SNES")]
node.pop("_display_items_cache", None)
FE.cat_i = 0
FE.item_i = 0
st = FE.stream_state()
check("der Systemkey steht drin", st["syskey"] == "SNES", str(st["syskey"]))
check("und der Dateiname fuers Cover",
      st["art_name"] == "Super Mario World (USA)", str(st["art_name"]))

# ---------------------------------------------------------------------------
print()
print("Test 2: eine GEMISCHTE Kategorie - der gemeldete Fall")
# ---------------------------------------------------------------------------
# So sieht "Zuletzt gespielt" aus: die Kategorie hat keinen Systemkey,
# die Eintraege tragen ihren eigenen.
gemischt = {"items": [spiel("Super Mario World (USA)", "SNES"),
                      spiel("Sonic (USA)", "MEGADRIVE", ".md"),
                      spiel("Sonic CD (USA)", "MEGACD", ".chd")],
            "folders": {}}
FE.cats[0] = ("Zuletzt gespielt", gemischt, None)
FE.cat_i = 0

for i, erwartet in enumerate(("SNES", "MEGADRIVE", "MEGACD")):
    FE.item_i = i
    st = FE.stream_state()
    check("Eintrag %d liefert %s" % (i + 1, erwartet),
          st["syskey"] == erwartet,
          "bekommen: %r - die Kategorie selbst hat KEINEN Key, "
          "deshalb kam hier bisher '' und das Overlay fragte "
          "/art ohne System" % st["syskey"])

FE.item_i = 1
st = FE.stream_state()
check("der Name fuers Cover stimmt weiterhin",
      st["art_name"] == "Sonic (USA)", str(st["art_name"]))
check("die Kategorie wird trotzdem als Name angezeigt",
      st["category"] == "Zuletzt gespielt", str(st["category"]))

# ---------------------------------------------------------------------------
print()
print("Test 3: nichts ausgewaehlt, und ein Ordner")
# ---------------------------------------------------------------------------
FE.item_i = 99                      # ausserhalb der Liste
st = FE.stream_state()
check("ohne Auswahl faellt es auf den Kategorie-Key zurueck",
      st["syskey"] == "", str(st["syskey"]))
check("und stuerzt nicht ab", st["total"] == 3)

gemischt["items"] = [("Ein Ordner", "folder", "/games/SNES/Ein Ordner")]
gemischt.pop("_display_items_cache", None)
FE.item_i = 0
st = FE.stream_state()
check("ein Ordner liefert ebenfalls keinen Key",
      st["syskey"] == "",
      "ein Ordner hat kein Cover - das Overlay fragt dann gar nicht "
      "erst an (Name endet auf '/')")

# ---------------------------------------------------------------------------
print()
print("Test 4: es ist dieselbe Funktion wie im Zeichenweg")
# ---------------------------------------------------------------------------
_q = io.open(H.FRONTEND_PY, encoding="utf-8").read()
_ss = _q.split("    def stream_state(self):")[1].split("\n    def ")[0]
check("stream_state() benutzt _item_syskey()",
      "self._item_syskey(" in _ss,
      "keine zweite Regel - dieselbe Lehre wie in Build 260")
check("und zwar fuer den veroeffentlichten Key",
      '"syskey": item_syskey' in _ss)
check("auch die Metadaten haengen daran",
      "get_meta(item_syskey" in _ss,
      "Genre und Jahr fehlten in gemischten Kategorien genauso")
check("und der RA-Fortschritt",
      "lookup_ra_progress(self._ra_lookup, sel, item_syskey)" in _ss)
check("der Kategorie-Key wird dafuer nirgends mehr benutzt",
      "get_meta(syskey," not in _ss and '"syskey": syskey' not in _ss,
      str([z.strip() for z in _ss.splitlines()
           if "syskey" in z and "item_syskey" not in z][:3]))

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
