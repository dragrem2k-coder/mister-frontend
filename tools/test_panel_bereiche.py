#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Das Panel meldet, was es angefasst hat (Build 249).

DER BEFUND aus dem Bench vom 09.10.: in der Listenansicht kopiert ein
Scrollschritt 3,21 MB auf den Schirm, und **2,69 MB davon sind die
Boxart-Spalte als EIN Rechteck** - 84 %. Eingetragen wurde sie, bevor
das Panel ueberhaupt gezeichnet war, denn vorher weiss niemand, was es
anfassen wird.

Seit Build 244 stimmt das nicht mehr: auf dem kurzen Weg wird die
Flaeche des Cover-Kastens AUSGESPART (697x729, rund 2,0 MB) - dort
steht schon das Richtige. Mitkopiert wurde sie trotzdem.

WORAN DIESE AENDERUNG SCHEITERN KANN, und genau das steht hier:

  1. Die gemeldeten Streifen decken NICHT alles ab, was gezeichnet
     wurde - dann bleibt auf dem Schirm ein Rest stehen, waehrend im
     Puffer das Richtige steht. Das ist die Sorte Fehler, die dieses
     Projekt fuenfmal gejagt hat (Build 80, 122, 125, 128, 237), und
     Build 244 hat sie sich mit 69 Bytes an einer Kartenecke
     eingefangen.
  2. Der ANFANGSBUCHSTABE wird vergessen. Er liegt mitten im
     ausgesparten Kasten und wird seit Build 247 mitgezeichnet - fehlt
     seine Zelle, bleibt der alte Buchstabe stehen.
  3. MIT Cover wird auch nur ein Teil gemeldet - dort kommt das Bild
     hinein, und das wechselt jeden Schritt.
  4. Die Meldung bleibt von einem Schritt im naechsten stehen und wird
     fuer einen anderen Fall benutzt.

Die Pixelgleichheit selbst pruefen tools/test_rechteck_flip.py (Puffer
gegen Schirm) und tools/diag_flip_deckung.py (ungedeckte Punkte). Diese
Datei prueft die MELDUNG.

Ausfuehren:
    python3 tools/test_panel_bereiche.py
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H                                        # noqa: E402

import fe.bench as BENCH                                    # noqa: E402
import fe.art as ART                                         # noqa: E402

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


def _liste(fe, n=60):
    bi, _bn, _nm = BENCH._groesste_kategorie(fe)
    fe.page = 1
    fe.cat_i = bi
    fe.nav_path = []
    _, node, _ = fe.cats[fe.cat_i]
    node["items"] = [("Spiel %03d" % i, "game",
                      ("/f/%d.sfc" % i, ".sfc", "SNES", None, None))
                     for i in range(n)]
    node.pop("_display_items_cache", None)
    fe.item_i = 0
    fe.scroll = 0
    fe.ansicht_setzen("liste")


def _cover_aus():
    echt = ART.ART.get_scaled

    def ersatz(quelle, breite, hoehe, **k):
        ART.ART._defer_count = getattr(ART.ART, "_defer_count", 0) + 1
        return None

    ART.ART.get_scaled = ersatz
    return lambda: setattr(ART.ART, "get_scaled", echt)


def _cover_an(breite=697, hoehe=729):
    echt = ART.ART.get_scaled
    pix = bytes(bytearray([40, 90, 160, 0])) * breite * hoehe

    def ersatz(quelle, b, h, **k):
        return (breite, hoehe, pix)

    ART.ART.get_scaled = ersatz
    return lambda: setattr(ART.ART, "get_scaled", echt)


def _geflippt(fe, schritte=6):
    """(MB je Schritt, Liste der Rechtecke des letzten Schritts)."""
    fb = fe.fb
    konto = {"bytes": 0, "letzte": []}
    echt_rect, echt_rows, echt_voll = (fb.flip_rechtecke, fb.flip_rows,
                                       fb.flip)

    def h_rect(rl, *a, **k):
        rl = [tuple(r) for r in rl]
        konto["bytes"] += sum(r[2] * r[3] * 4 for r in rl)
        konto["letzte"] = rl
        return echt_rect(rl, *a, **k)

    def h_rows(y, h, *a, **k):
        konto["bytes"] += int(h) * fb.stride
        return echt_rows(y, h, *a, **k)

    def h_voll(*a, **k):
        konto["bytes"] += len(fb.buf)
        return echt_voll(*a, **k)

    schritt = BENCH.schritt_funktion(fe, 1)
    schritt(0)
    spanne = BENCH.fenster_spanne(fe, 1)
    for i in range(6):
        schritt(i % spanne)
    fb.flip_rechtecke, fb.flip_rows, fb.flip = h_rect, h_rows, h_voll
    try:
        for i in range(schritte):
            schritt(i % spanne)
    finally:
        fb.flip_rechtecke, fb.flip_rows, fb.flip = (echt_rect, echt_rows,
                                                    echt_voll)
    return (konto["bytes"] / float(schritte) / 1048576.0, konto["letzte"])


# ---------------------------------------------------------------------------
print("Test 1: ohne Cover wird nur gemeldet, was auch beschrieben wurde")
# ---------------------------------------------------------------------------
H.set_screen(1920, 1080)
fe = H.make_frontend(page=1)
_liste(fe)
zurueck = _cover_aus()
try:
    mb_kurz, rechtecke = _geflippt(fe)
    bereiche = getattr(fe, "_panel_bereiche", None)
finally:
    zurueck()

check("es wird ueberhaupt geflippt", mb_kurz > 0.1, "%.2f MB" % mb_kurz)
check("und deutlich weniger als die ganze Spalte",
      mb_kurz < 2.6,
      "%.2f MB - vor Build 249 waren es 3,21 MB, davon 2,69 die Spalte"
      % mb_kurz)
check("die Spalte steht NICHT mehr als ein Stueck darin",
      not [r for r in rechtecke if r[2] > 700 and r[3] > 900],
      str([r for r in rechtecke if r[2] > 700 and r[3] > 900]))
check("stattdessen mehrere Streifen", len(rechtecke) >= 5,
      "%d Rechtecke" % len(rechtecke))
check("die Meldung wird nach dem Schritt wieder geleert",
      bereiche is None,
      "sonst wird sie im naechsten Schritt fuer einen anderen Fall "
      "benutzt")

# ---------------------------------------------------------------------------
print()
print("Test 2: der Anfangsbuchstabe ist mit dabei")
# ---------------------------------------------------------------------------
# Er liegt MITTEN im ausgesparten Kasten und wird seit Build 247
# mitgezeichnet. Fehlt seine Zelle, bleibt auf dem Schirm der alte
# Buchstabe stehen. Erkennbar an einem etwa quadratischen Rechteck in
# der Boxart-Spalte.
_quadrate = [r for r in rechtecke
             if r[2] > 60 and 0.7 < (float(r[2]) / max(1, r[3])) < 1.4]
check("ein etwa quadratisches Rechteck ist dabei (die Zelle)",
      bool(_quadrate), str(_quadrate[:3]))
check("und es liegt in der Boxart-Spalte, nicht in der Liste",
      bool(_quadrate) and all(r[0] > fe.fb.width // 2 for r in _quadrate),
      str([r[0] for r in _quadrate]))

# ---------------------------------------------------------------------------
print()
print("Test 3: MIT Cover bleibt es bei der ganzen Spalte")
# ---------------------------------------------------------------------------
fe2 = H.make_frontend(page=1)
_liste(fe2)
zurueck2 = _cover_an()
try:
    mb_cover, rechtecke2 = _geflippt(fe2)
finally:
    zurueck2()
_grosse = [r for r in rechtecke2 if r[2] > 700 and r[3] > 900]
check("die Spalte steht als ein Stueck darin", bool(_grosse),
      "dort kommt das Bild hinein, und das wechselt jeden Schritt")
check("und es wird mehr geflippt als ohne Cover", mb_cover > mb_kurz,
      "%.2f gegen %.2f MB" % (mb_cover, mb_kurz))

# ---------------------------------------------------------------------------
print()
print("Test 4: die Reihenfolge im Quelltext")
# ---------------------------------------------------------------------------
_q = io.open(os.path.join(_REPO, "frontend", "frontend.py"),
             encoding="utf-8").read()
_code = "\n".join(z for z in _q.split("\n")
                  if not z.strip().startswith("#"))
_block = _code.split("def _art_panel_aktualisieren")[1].split("\n    def ")[0]
_i_zeichnen = _block.find("self.draw_art_panel(")
_i_spur = _block.find("_sp.append(")
check("erst zeichnen, dann eintragen",
      0 < _i_zeichnen < _i_spur,
      "vorher weiss niemand, was das Panel anfassen wird - genau "
      "deshalb stand dort die ganze Spalte")
check("ohne Meldung bleibt es bei der ganzen Spalte",
      "art_x0 + art_w + _rand" in _block,
      "ein unbekannter Bereich muss immer der ganze sein")
check("die Meldung wird vor dem Zeichnen zurueckgesetzt",
      _block.find("self._panel_bereiche = None") < _i_zeichnen,
      "sonst gilt die des vorigen Schritts")
check("der Buchstabe meldet seine Zelle selbst",
      "_ber.append((bx, by, breite, hoehe))" in _code)

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
