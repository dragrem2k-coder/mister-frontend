#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft, dass die System-Hintergrundbilder wirklich raus sind
(Build 87).

AUSLOESER (Nutzerentscheidung): "grossen Systembildhintergrund komplett
rausnehmen, war eh bloede."

Das Feature hatte zwei Auftritte, und beide kosteten Leistung:

  1. BILDSCHIRMFUELLEND hinter der Spieleliste. Der Puffer musste bei
     jedem Kategoriewechsel neu zusammengesetzt werden - bei 1920x1080
     8,3 MB, zeilenweise in Python, hier gemessene 41-67 ms und auf der
     MiSTer-CPU entsprechend mehr. Dazu hielt BgCache bis zu vier
     solcher Vollbildpuffer, bei 1080p rund 33 MB.

  2. KLEIN in der Boxart-Spalte, als Ersatz fuer ein fehlendes Cover.
     Das war die teuerste Einzeloperation im ganzen Frontend
     (200-700+ ms je Skalierung) - und sie wurde von KEINEM Vorauslader
     erfasst: "Miniaturen vorbereiten" laeuft nur ueber Eintraege mit
     Cover-Pfad. Ordner haben praktisch nie ein eigenes Cover, also traf
     es jede Ordner-Ebene, und jedes Spiel ohne Artwork obendrein.

DIE ZUSAGEN, die hier geprueft werden:
  1. Kein Code-Pfad greift noch auf den bg-Ordner zu.
  2. Ein Eintrag ohne Cover zeichnet den schlichten Platzhalter - und
     zwar ohne einen einzigen Skalierungsaufruf.
  3. Der Hintergrund der Spieleliste ist die einfarbige Flaeche aus
     fb.clear(), nicht mehr eine Bildkopie.
  4. Der Menuepunkt "System-Hintergrundbilder" ist aus dem Systemmenue
     verschwunden.

Ausfuehren:
    python3 tools/test_kein_systemhintergrund.py
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import _harness as H                                  # noqa: E402

fm = H.fm
sys.path.insert(0, os.path.dirname(H.FRONTEND_PY))
import fe.art as A                                    # noqa: E402
import fe.menu as M                                   # noqa: E402
import fe.settings as S                               # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


print("Test 1: der bg-Ordner ist aus dem Code verschwunden")
# Nicht "steht nicht mehr im Menue", sondern: es gibt die Bausteine
# nicht mehr. Bliebe BgCache liegen, koennte ein spaeterer Umbau es
# versehentlich wieder anschalten.
for name in ("BG_BASE", "BgCache", "BG"):
    check("fe.art hat kein %s mehr" % name, not hasattr(A, name),
          "noch vorhanden: %r" % (getattr(A, name, None),))
for name in ("system_bg_enabled", "toggle_system_bg",
             "SYSTEM_BG_DISABLED_FLAG"):
    check("fe.settings hat kein %s mehr" % name, not hasattr(S, name))

quelle = open(H.FRONTEND_PY, encoding="utf-8").read()
# Nur echter Code zaehlt - die Kommentare erklaeren ja gerade, was
# entfernt wurde und warum.
code = "\n".join(z for z in quelle.splitlines()
                 if not z.lstrip().startswith("#"))
for muster in ("BG_BASE", "BG.get(", "_cur_bg", "system_bg_enabled"):
    check("frontend.py benutzt %s nirgends mehr" % muster,
          muster not in code)

print()
print("Test 2: ohne Cover kommt der Platzhalter - ohne Skalierung")
# Der Kern der Sache. Frueher landete hier das grosse Systembild und
# damit ein get_scaled()-Aufruf ueber ein nahezu bildschirmfuellendes
# Bild.
for w, h, name in ((320, 240, "CRT"), (1920, 1080, "HDMI")):
    H.set_screen(w, h)
    f = H.make_frontend(page=1)
    L = f.layout_items(True)
    s = L["s"]
    art_x0 = fm.art_spalte_x0(L["list_right"], h, s)
    art_w = (w - L["ox"]) - art_x0
    art_h = L["footer_y"] - 8 * s - L["oy"]

    skaliert = []
    echt = A.ART.get_scaled

    def zaehlend(pfad, bw, bh, _e=echt, _l=skaliert):
        _l.append(pfad)
        return None                    # kein Bild vorhanden

    A.ART.get_scaled = zaehlend
    fm.ART.get_scaled = zaehlend
    fm.get_meta = lambda sk, n: {}
    fm.lookup_ra_progress = lambda *a, **k: None
    f._ra_lookup = None
    f._completed_set = set()
    f._playtime_cache = {}
    it = ("Spiel ohne Cover", "game",
          ("/f/x.sfc", ".sfc", "SNES", None, (1, "f", 0)))
    try:
        f.draw_art_panel(art_x0, art_w, L["oy"], art_h, "SNES", it, s)
    finally:
        A.ART.get_scaled = echt
        fm.ART.get_scaled = echt

    # Genau EIN Versuch: das Cover selbst. Kein zweiter fuer ein
    # Hintergrundbild.
    check("%s: nur ein Bildversuch (das Cover)" % name,
          len(skaliert) == 1, "%d Versuche: %s" % (len(skaliert), skaliert))
    check("%s: kein Versuch im bg-Ordner" % name,
          not [p for p in skaliert if p and "/bg/" in p],
          "%s" % [p for p in skaliert if p and "/bg/" in p])

print()
print("Test 3: der Listenhintergrund ist die einfarbige Flaeche")
# Zwei Kategorien mit unterschiedlichem Systemkey muessen denselben
# Hintergrund liefern - frueher haette jede ihr eigenes Bild bekommen.
H.set_screen(1920, 1080)
f = H.make_frontend(page=1)
f.draw_page_items(flip=False)
ecke_a = bytes(f.fb.buf[0:64])
f.cat_i = min(1, len(f.cats) - 1)
f.item_i = 0
f.scroll = 0
f.draw_page_items(flip=False)
ecke_b = bytes(f.fb.buf[0:64])
check("zwei Kategorien haben denselben Hintergrund",
      ecke_a == ecke_b)
# Und er stammt aus derselben Vorlage, die fb.clear() aufbaut.
vorlage = f.fb._rowcache.get(("bg", fm.C_BG, f.fb.width, f.fb.height))
check("die Vorlage aus fb.clear() ist vorhanden", vorlage is not None)
if vorlage is not None:
    check("die obere Bildzeile stammt genau aus dieser Vorlage",
          bytes(vorlage[0:64]) == ecke_a)

print()
print("Test 4: der Menuepunkt ist weg")
# system_items() liefert den Menuebaum: {"items": [...], "folders":
# {"Anzeige & Sound": {"items": [...]}, ...}}. Der Schalter sass in
# "Anzeige & Sound"; geprueft wird trotzdem der ganze Baum, damit er
# auch nicht anderswo wieder auftaucht.
def alle_eintraege(node):
    raus = list(node.get("items", []))
    for sub in node.get("folders", {}).values():
        raus.extend(alle_eintraege(sub))
    return raus


eintraege = alle_eintraege(M.system_items())
arten = [e[1] for e in eintraege
         if isinstance(e, (list, tuple)) and len(e) > 1]
check("das Systemmenue hat ueberhaupt Eintraege", len(arten) > 10,
      "%d Eintraege" % len(arten))
check("kein Menueeintrag der Art 'system_bg'", "system_bg" not in arten,
      "%d Eintraege geprueft" % len(arten))
menu_code = "\n".join(
    z for z in open(os.path.join(os.path.dirname(H.FRONTEND_PY),
                                 "fe", "menu.py"), encoding="utf-8")
    if not z.lstrip().startswith("#"))
check("fe/menu.py erwaehnt system_bg nicht mehr",
      "system_bg" not in menu_code)

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for f_ in fails:
        print("  -", f_)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
