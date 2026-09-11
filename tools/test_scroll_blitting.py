#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft das Scroll-Blitting (Build 96).

AUSLOESER (Nutzer): "Scroll-Blitting probieren wir mal aus, wenn es
nichts bringt schmeissen wir es wieder raus" - und ausdruecklich "mit
An- und Ausschalter unter System, Anzeige & Sound".

WORUM ES GEHT: sobald die Markierung den Listenrand erreicht hat, ist
JEDER weitere Schritt ein kompletter Seitenaufbau (auf HDMI gemessen
45-110 ms). Beim Dauerscrollen ist das praktisch immer. Blitting
verschiebt stattdessen den schon gezeichneten Listenblock um eine
Zeilenhoehe im Speicher und zeichnet nur die drei Zeilen neu, die sich
wirklich geaendert haben.

DIE ENTSCHEIDENDE FRAGE ist nicht "ist es schneller" (das misst
tools/bench_scrollblit.py), sondern "kommt dasselbe Bild heraus".
Ein verschobener Block, der auch nur um ein Pixel danebenliegt oder
einen Rest stehenlaesst, faellt beim Scrollen sofort auf. Test 1
vergleicht deshalb Bildpunkt fuer Bildpunkt gegen den vollen Aufbau.

Ausfuehren:
    python3 tools/test_scroll_blitting.py
"""
import os
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import _harness as H                                  # noqa: E402

fm = H.fm
sys.path.insert(0, os.path.dirname(H.FRONTEND_PY))
import fe.settings as S                               # noqa: E402
import fe.framebuffer as FB                           # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


# Den Schalter auf eine Wegwerf-Datei umbiegen, damit der Test nichts
# unter /media/fat anfasst.
TMP = tempfile.mkdtemp(prefix="blit_")
S.SCROLL_BLIT_ENABLED_FLAG = os.path.join(TMP, "scroll_blit_enabled")


def blit_an(an):
    if an:
        open(S.SCROLL_BLIT_ENABLED_FLAG, "w").close()
    elif os.path.exists(S.SCROLL_BLIT_ENABLED_FLAG):
        os.remove(S.SCROLL_BLIT_ENABLED_FLAG)


def liste(w, h, anzahl=200):
    """Frontend mit einer Liste, die deutlich laenger ist als der
    sichtbare Ausschnitt - sonst wird nie gescrollt."""
    H.set_screen(w, h)
    f = H.make_frontend(page=1)
    node = f._current_node()
    node["items"] = [(H.TITLES[i % len(H.TITLES)] + " %d" % i, "game",
                      ("/f/%d.sfc" % i, ".sfc", "SNES", None, None))
                     for i in range(anzahl)]
    node.pop("_display_items_cache", None)
    f.item_i = 0
    f.scroll = 0
    return f


def bis_zum_rand(f):
    """Markierung an den unteren Listenrand fahren, ohne zu scrollen."""
    f.draw_page_items(flip=False)
    f.item_i = f.items_visible - 1
    f.draw_page_items(flip=False)


def unterschiede(a, b):
    return sum(1 for x, y in zip(a, b) if x != y)


AUFLOESUNGEN = ((320, 240, "CRT"), (1920, 1080, "HDMI"))


print("Test 1: geblittet sieht aus wie voll aufgebaut - Bildpunkt fuer "
      "Bildpunkt")
# Der Kern. Alles andere ist Nebensache, wenn das Bild nicht stimmt.
for w, h, name in AUFLOESUNGEN:
    for richtung, schritt in (("runter", +1), ("hoch", -1)):
        blit_an(True)
        f = liste(w, h)
        bis_zum_rand(f)
        if schritt < 0:
            # Erst ein Stueck hineinscrollen, damit es nach oben
            # ueberhaupt etwas zu scrollen gibt.
            for _ in range(5):
                f.item_i += 1
                f.scroll += 1
                f.draw_page_items(flip=False)
        alt_item, alt_scroll = f.item_i, f.scroll
        f.item_i += schritt
        f.scroll += schritt
        ok = f._scroll_blit_items(alt_item, alt_scroll)
        check("%s/%s: der Blit-Pfad wurde genommen" % (name, richtung), ok)
        geblittet = bytes(f.fb.buf)

        # Dasselbe Ziel auf dem vollen Weg.
        g = liste(w, h)
        g.item_i, g.scroll = f.item_i, f.scroll
        g.draw_page_items(flip=False)
        g.draw_page_items(flip=False)      # zweimal: erster Aufbau baut
                                            # den Hintergrund, zweiter
                                            # nimmt den schnellen Pfad -
                                            # derselbe Zustand wie beim
                                            # Blitten
        voll = bytes(g.fb.buf)
        d = unterschiede(geblittet, voll)
        check("%s/%s: bitgenau gleich" % (name, richtung), d == 0,
              "(%d abweichende Bytes)" % d)

print("Test 2: viele Schritte hintereinander driften nicht")
# Der eigentliche Grund fuer die flache Vignette: jeder Blit setzt auf
# dem Ergebnis des vorigen auf. Ein Fehler von einem Pixel pro Schritt
# waere nach dreissig Schritten ein sichtbarer Versatz.
for w, h, name in AUFLOESUNGEN:
    blit_an(True)
    f = liste(w, h)
    bis_zum_rand(f)
    geblittet_alle = True
    for _ in range(30):
        alt_item, alt_scroll = f.item_i, f.scroll
        f.item_i += 1
        f.scroll += 1
        if not f._scroll_blit_items(alt_item, alt_scroll):
            geblittet_alle = False
    check("%s: alle 30 Schritte wurden geblittet" % name, geblittet_alle)
    g = liste(w, h)
    g.item_i, g.scroll = f.item_i, f.scroll
    g.draw_page_items(flip=False)
    g.draw_page_items(flip=False)
    d = unterschiede(bytes(f.fb.buf), bytes(g.fb.buf))
    check("%s: nach 30 Schritten immer noch bitgenau" % name, d == 0,
          "(%d abweichende Bytes)" % d)

print("Test 3: ohne Schalter passiert gar nichts")
for w, h, name in AUFLOESUNGEN:
    blit_an(False)
    f = liste(w, h)
    bis_zum_rand(f)
    alt_item, alt_scroll = f.item_i, f.scroll
    f.item_i += 1
    f.scroll += 1
    check("%s: Blit-Pfad wird abgelehnt" % name,
          f._scroll_blit_items(alt_item, alt_scroll) is False)

print("Test 4: die Ablehnungsgruende greifen wirklich")
# Jeder Zweifelsfall MUSS auf den vollen Aufbau zurueckfallen - ein
# falsch stehengebliebener Bildteil waere schlimmer als ein paar
# Millisekunden mehr.
blit_an(True)
f = liste(1920, 1080)
bis_zum_rand(f)

alt_item, alt_scroll = f.item_i, f.scroll
f.item_i += 2
f.scroll += 2
check("zwei Zeilen auf einmal -> abgelehnt",
      f._scroll_blit_items(alt_item, alt_scroll) is False)
f.item_i, f.scroll = alt_item, alt_scroll

check("gar nicht gescrollt -> abgelehnt",
      f._scroll_blit_items(alt_item, alt_scroll) is False)

f.item_i += 1
f.scroll += 1
f._force_full_redraw = True
check("angeforderter Vollaufbau -> abgelehnt",
      f._scroll_blit_items(alt_item, alt_scroll) is False)
f._force_full_redraw = False
f.item_i, f.scroll = alt_item, alt_scroll

# Eine Hinweisbox liegt ueber der Seite - ein Teil-Redraw kann sie
# nicht korrekt herstellen (siehe _overlay_active()).
f.item_i += 1
f.scroll += 1
f._prominent_message = "Hinweis"
f._prominent_message_until = fm.time.monotonic() + 10
check("Hinweisbox aktiv -> abgelehnt",
      f._scroll_blit_items(alt_item, alt_scroll) is False)
f._prominent_message = None
f.item_i, f.scroll = alt_item, alt_scroll

# Jemand anders hat den Puffer komplett ueberschrieben (Hilfe, Dialog,
# Attract-Modus ...) - dann steht dort nicht mehr unsere Seite.
f.item_i += 1
f.scroll += 1
f.fb.mark_full_redraw()
check("fremder Vollaufbau dazwischen -> abgelehnt",
      f._scroll_blit_items(alt_item, alt_scroll) is False)

print("Test 5: die Vignette ist im Listenbereich flach - aber nur mit "
      "Schalter")
for w, h, name in AUFLOESUNGEN:
    blit_an(True)
    f = liste(w, h)
    f.draw_page_items(flip=False)
    band = FB.VIGNETTE_FLAT_BAND
    check("%s: ein Band ist gesetzt" % name, band is not None, "(%r)" % (band,))
    if band:
        L = f.layout_items(f.hat_artspalte(f.view["items"],
                                           f.view.get("syskey")))
        check("%s: das Band deckt den Listenbereich ab" % name,
              band[0] <= L["list_y"] and band[1] >= L["list_y"]
              + (L["visible"] - 1) * L["rowh"],
              "(Band %r, Liste ab %d)" % (band, L["list_y"]))
        # Alle Zeilen im Band muessen dieselbe Helligkeit haben.
        bg = f.fb._rowcache.get(f.fb.bg_key(fm.C_BG))
        check("%s: Hintergrundmuster liegt im Zwischenspeicher" % name,
              bg is not None)
        if bg:
            stride = f.fb.stride
            proben = set()
            for y in range(band[0] + 1, band[1] - 1,
                           max(1, (band[1] - band[0]) // 20)):
                proben.add(bytes(bg[y * stride:y * stride + 4]))
            check("%s: alle Zeilen im Band gleich hell" % name,
                  len(proben) == 1, "(%d verschiedene)" % len(proben))
            # Und ausserhalb muss es weiterhin einen Verlauf geben,
            # sonst haetten wir die Vignette versehentlich ganz
            # abgeschafft.
            aussen = set()
            for y in range(0, max(1, band[0]), max(1, band[0] // 8 or 1)):
                aussen.add(bytes(bg[y * stride:y * stride + 4]))
            check("%s: ausserhalb des Bandes bleibt der Verlauf" % name,
                  len(aussen) > 1, "(%d Stufen ueber dem Band)" % len(aussen))

    blit_an(False)
    g = liste(w, h)
    g.draw_page_items(flip=False)
    check("%s: ohne Schalter kein Band" % name,
          FB.VIGNETTE_FLAT_BAND is None,
          "(%r)" % (FB.VIGNETTE_FLAT_BAND,))

print("Test 6: der Hintergrund-Zwischenspeicher kennt das Band")
# Ohne das im Schluessel liefert der Zwischenspeicher nach dem
# Umschalten noch den alten Hintergrund, und der Wechsel waere erst
# nach einem Neustart sichtbar.
H.set_screen(1920, 1080)
f = H.make_frontend(page=1)
FB.VIGNETTE_FLAT_BAND = None
k1 = f.fb.bg_key(fm.C_BG)
FB.VIGNETTE_FLAT_BAND = (100, 900)
k2 = f.fb.bg_key(fm.C_BG)
check("verschiedene Baender -> verschiedene Schluessel", k1 != k2)
FB.VIGNETTE_FLAT_BAND = None

print("Test 7: der Schalter steht unter Anzeige & Sound")
import fe.menu as M                                    # noqa: E402
blit_an(False)
baum = M.system_items()


def alle_eintraege(node, pfad=""):
    for name, art, _x in node.get("items", []):
        yield pfad, name, art
    for label, unter in (node.get("folders") or {}).items():
        for e in alle_eintraege(unter, label):
            yield e


eintraege = list(alle_eintraege(baum))
treffer = [(p, n) for p, n, a in eintraege if a == "scroll_blit"]
check("es gibt genau einen Schalter", len(treffer) == 1,
      "(%r)" % (treffer,))
if treffer:
    gruppe = treffer[0][0]
    check("er steht in derselben Gruppe wie 'Schnelles Scrollen'",
          gruppe in [p for p, n, a in eintraege if a == "fast_scroll"],
          "(%r)" % gruppe)
check("die Beschriftung nennt den Preis (flache Randabdunkelung)",
      any("flach" in n.lower() or "flat" in n.lower()
          for p, n, a in eintraege if a == "scroll_blit"),
      "(%r)" % [n for p, n, a in eintraege if a == "scroll_blit"])

blit_an(True)
baum = M.system_items()
eintraege = list(alle_eintraege(baum))
check("eingeschaltet aendert sich die Beschriftung",
      any(" AN " in n or ": AN" in n or ": ON" in n
          for p, n, a in eintraege if a == "scroll_blit"),
      "(%r)" % [n for p, n, a in eintraege if a == "scroll_blit"])

blit_an(False)
FB.VIGNETTE_FLAT_BAND = None

print()
if fails:
    print("FEHLGESCHLAGEN (%d):" % len(fails))
    for f_ in fails:
        print("  -", f_)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
