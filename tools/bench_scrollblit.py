#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Misst den Gewinn des Scroll-Blittings (Build 96).

DIAGNOSE, kein Pass/Fail-Test - deshalb immer Rueckgabewert 0.

Verglichen wird der ECHTE Weg mit dem ECHTEN Weg: einmal ein
Scrollschritt ueber den vollen Seitenaufbau (draw_page_items), einmal
derselbe Schritt ueber _scroll_blit_items(). Beide mit denselben
Zeichenroutinen und derselben Liste.

WICHTIG ZUR EINORDNUNG: die absoluten Zahlen gelten fuer den Rechner,
auf dem dieses Skript laeuft - auf der schwaecheren MiSTer-CPU sind
beide Werte um ein Vielfaches groesser. Aussagekraeftig ist deshalb das
VERHAELTNIS: beide Wege sind Python-Interpreter-gebunden (Slice-Kopien
und Schleifen, kein Fliesskomma, keine Bibliothek) und skalieren mit der
CPU-Geschwindigkeit aehnlich.

Die Messung hat beim Bauen von Build 96 eine falsche Erwartung
korrigiert: geschaetzt war, dass eine spaltenweise Kopie ueber rund 765
Bildzeilen TEURER ist als 17 Zeilen zwischengespeicherten Text neu zu
setzen. Sie ist es nicht - nicht annaehernd.

Ausfuehren:
    python3 tools/bench_scrollblit.py
"""
import os
import sys
import tempfile
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import _harness as H                                  # noqa: E402

fm = H.fm
sys.path.insert(0, os.path.dirname(H.FRONTEND_PY))
import fe.settings as S                               # noqa: E402
import fe.framebuffer as FB                           # noqa: E402

TMP = tempfile.mkdtemp(prefix="blitbench_")
S.SCROLL_BLIT_ENABLED_FLAG = os.path.join(TMP, "scroll_blit_enabled")
open(S.SCROLL_BLIT_ENABLED_FLAG, "w").close()


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
    f.item_i = f.items_visible - 1
    f.draw_page_items(flip=False)
    return f


def messen(f, wie, runden=40):
    """Einen Scrollschritt `runden` mal ausfuehren und die mittlere
    Dauer liefern. Vorher ein Warmlauf, damit der Text-Zwischenspeicher
    gefuellt ist - sonst misst man das Rendern der Schriftzeichen statt
    des Zeichenwegs."""
    def schritt():
        alt_i, alt_s = f.item_i, f.scroll
        f.item_i += 1
        f.scroll += 1
        if wie == "blit":
            if not f._scroll_blit_items(alt_i, alt_s):
                raise RuntimeError("Blit-Pfad unerwartet abgelehnt")
        else:
            f.draw_page_items(flip=False)

    for _ in range(10):
        schritt()
    t0 = time.perf_counter()
    for _ in range(runden):
        schritt()
    return (time.perf_counter() - t0) / runden * 1000.0


print("Scroll-Blitting gegen vollen Seitenaufbau")
print("(absolute Zahlen gelten fuer DIESEN Rechner - siehe Kopf)")
print()
print("%-6s %-11s %7s %10s %10s %8s"
      % ("Modus", "Aufloesung", "Zeilen", "voll", "blit", "Faktor"))
for w, h, name in ((320, 240, "CRT"), (1280, 720, "720p"),
                   (1920, 1080, "HDMI")):
    f = liste(w, h)
    L = f.layout_items(f.hat_artspalte(f.view["items"],
                                       f.view.get("syskey")))
    sichtbar = L["visible"]
    f2 = liste(w, h)
    t_voll = messen(f, "voll")
    t_blit = messen(f2, "blit")
    print("%-6s %-11s %7d %9.2f ms %9.2f ms %7.1fx"
          % (name, "%dx%d" % (w, h), sichtbar, t_voll, t_blit,
             (t_voll / t_blit) if t_blit else 0.0))

FB.VIGNETTE_FLAT_BAND = None
print()
print("Der Gewinn kommt daher, dass beim Blitten nur VIER Zeilen neu")
print("gezeichnet werden (beide Listenraender plus alte und neue")
print("Markierung) statt aller sichtbaren - der Rest wird als Block")
print("verschoben.")
sys.exit(0)
