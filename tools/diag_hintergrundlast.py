#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Was passiert eigentlich pro Tastendruck? (Diagnose, kein Test)

NUTZERFRAGE: "HDMI-Modus laeuft auch, aber das Scrollen ist mir da zu
langsam, vor allem wenn Zeilen nach unten neu ins Bild kommen. Laufen da
noch irgendwelche Sachen im Hintergrund, die das verlangsamen?"

Die Frage ist mit blossem Codelesen nicht zu beantworten - der
Zeichenweg ist gross, und gerade die teuren Dinge stehen nicht dort, wo
man sie vermutet. Dieses Skript zaehlt deshalb mit, statt zu raten.

WAS GEZAEHLT WIRD und warum genau das:

  Dateizugriffe   Auf diesem Rechner sind sie fast umsonst. Auf dem
                  MiSTer liegen sie auf der SD-Karte und kosten ein
                  Vielfaches. Die ZAHL uebertraegt sich, die Zeit nicht -
                  deshalb ist die Zahl hier die aussagekraeftige Groesse.
  LOG-Zeilen      Jede oeffnet und schliesst die Datei einzeln.
  _display_items  Die sortierte Liste. Wird sie pro Schritt mehrfach
                  gebaut, ist das reine Doppelarbeit.
  layout_items    Dasselbe fuer die Seitenaufteilung.

Ausfuehren:
    python3 tools/diag_hintergrundlast.py
"""
import builtins
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import _harness as H                                   # noqa: E402

fm = H.fm
sys.path.insert(0, os.path.dirname(H.FRONTEND_PY))
import fe.log as LOGMOD                                # noqa: E402

ZAEHLER = {}


def _zaehle(name):
    ZAEHLER[name] = ZAEHLER.get(name, 0) + 1


def _huelle(modul, name, schluessel):
    echt = getattr(modul, name)

    def ersatz(*a, **kw):
        _zaehle(schluessel)
        return echt(*a, **kw)
    setattr(modul, name, ersatz)
    return echt


# --- Zaehler einhaengen -------------------------------------------------
_huelle(os.path, "exists", "datei: exists")
_huelle(os.path, "isfile", "datei: isfile")
_huelle(os.path, "isdir", "datei: isdir")
_huelle(os.path, "getsize", "datei: getsize")
_huelle(os.path, "getmtime", "datei: getmtime")
_huelle(os, "stat", "datei: stat")
_huelle(os, "listdir", "datei: listdir")
_huelle(builtins, "open", "datei: open")
_huelle(LOGMOD, "LOG", "LOG-Zeilen")
# frontend.py und die fe-Module haben LOG beim Import in ihren eigenen
# Namensraum geholt - die Huelle oben erreicht sie deshalb nicht mehr.
# Nachziehen, sonst zaehlt man nur die Haelfte.
for _m in list(sys.modules.values()):
    if getattr(_m, "__name__", "").startswith(("fe.", "frontend")) \
            and hasattr(_m, "LOG"):
        _m.LOG = LOGMOD.LOG

_echt_display = fm.Frontend._display_items


def _display_zaehlend(self, *a, **kw):
    _zaehle("_display_items")
    return _echt_display(self, *a, **kw)


fm.Frontend._display_items = _display_zaehlend

_echt_layout = fm.Frontend.layout_items


def _layout_zaehlend(self, *a, **kw):
    _zaehle("layout_items")
    return _echt_layout(self, *a, **kw)


fm.Frontend.layout_items = _layout_zaehlend


# --- Messen -------------------------------------------------------------
def liste(w, h, anzahl=400):
    H.set_screen(w, h)
    f = H.make_frontend(page=1)
    node = f._current_node()
    node["items"] = [(H.TITLES[i % len(H.TITLES)] + " %d" % i, "game",
                      ("/f/%d.sfc" % i, ".sfc", "SNES", None, None))
                     for i in range(anzahl)]
    node.pop("_display_items_cache", None)
    f.item_i = 0
    f.scroll = 0
    f.draw_page_items(flip=False)
    return f


def runde(f, schritt, runden=20):
    """Einen Schritt mehrfach ausfuehren, Zaehler und Zeit liefern."""
    for _ in range(5):                 # Warmlauf: Text-/Rechteckcache
        schritt(f)
    ZAEHLER.clear()
    t0 = time.perf_counter()
    for _ in range(runden):
        schritt(f)
    dauer = (time.perf_counter() - t0) / runden * 1000.0
    return dauer, {k: v / float(runden) for k, v in sorted(ZAEHLER.items())}


def schritt_in_fenster(f):
    """Markierung wandert, die Liste bleibt stehen - der leichte Weg."""
    L = f.layout_items(f.hat_artspalte(f.view["items"], f.view.get("syskey")))
    mitte = f.scroll + L["visible"] // 2
    f.item_i = mitte if f.item_i != mitte else mitte - 1
    f.draw_page_items(flip=False)


def schritt_mit_scroll(f):
    """Eine Zeile kommt unten neu ins Bild - der Fall aus der Frage."""
    f.item_i += 1
    f.scroll += 1
    if f.item_i > 380:
        f.item_i, f.scroll = 0, 0
    f.draw_page_items(flip=False)


def schritt_ordnerwechsel(f):
    """Hin und her zwischen zwei Kategorien - der zweite genannte Fall."""
    f.page = 0
    f.cat_i = (f.cat_i + 1) % len(f.cats)
    f.draw_page_cats(flip=False)


print("Was pro Tastendruck passiert")
print("(Zeiten gelten fuer DIESEN Rechner - auf dem MiSTer ein")
print(" Vielfaches. Uebertragbar sind die ZAHLEN, nicht die Zeiten.)")
print()

FAELLE = [
    ("Markierung wandert", schritt_in_fenster),
    ("Zeile kommt neu rein", schritt_mit_scroll),
    ("Kategoriewechsel", schritt_ordnerwechsel),
]

for w, h, name in ((320, 240, "CRT"), (1920, 1080, "HDMI")):
    print("=== %s %dx%d ===" % (name, w, h))
    for label, schritt in FAELLE:
        f = liste(w, h)
        if schritt is schritt_ordnerwechsel:
            f.page = 0
            f.draw_page_cats(flip=False)
        dauer, zaehler = runde(f, schritt)
        gesamt_datei = sum(v for k, v in zaehler.items()
                           if k.startswith("datei:"))
        print("  %-22s %7.2f ms   %5.1f Dateizugriffe   "
              "%3.1f LOG   %3.1f x _display_items   %3.1f x layout_items"
              % (label, dauer, gesamt_datei,
                 zaehler.get("LOG-Zeilen", 0.0),
                 zaehler.get("_display_items", 0.0),
                 zaehler.get("layout_items", 0.0)))
        einzeln = {k[7:]: v for k, v in zaehler.items()
                   if k.startswith("datei:") and v}
        if einzeln:
            print("       davon: " + ", ".join(
                "%s %.1f" % (k, v) for k, v in sorted(einzeln.items())))
    print()

sys.exit(0)
