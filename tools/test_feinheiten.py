#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scrollbalken, Akzentbalken, Haarlinie (Build 236).

DIE BEDINGUNG DES NUTZERS war eindeutig: "alles aber nur wenn absolut
keine Performance Verluste merkbar sind". Dieser Test haelt deshalb
nicht fest, dass die drei Elemente huebsch aussehen - das kann er
nicht -, sondern die drei Eigenschaften, von denen abhaengt, ob die
Bedingung erfuellt BLEIBT:

  1. SCROLLBALKEN UND HAARLINIE HAENGEN AM FENSTER, nicht am Zeiger.
     Sie werden deshalb nur beim Seitenaufbau gezeichnet. Rutschten sie
     je in den leichten Pfad, kosteten sie bei JEDEM Scrollschritt -
     und genau das soll nicht passieren.
  2. SIE GIBT ES NUR IN DER LISTENANSICHT. Beim ersten Entwurf liefen
     sie auch in Raster und Galerie, wo es gar keine Liste gibt - der
     Messlauf zeigte dort prompt einen Unterschied, der nichts mit
     ihnen zu tun hatte.
  3. DER SCHALTER KOSTET NICHTS. Er steht als Modulvariable da und wird
     beim Umschalten gesetzt - eine Dateiabfrage je Zeile waere genau
     die Sorte stiller Kosten, gegen die Build 212 angetreten ist.

Gemessen wird in tools/diag_feinheiten.py, nicht hier: eine Messung
gehoert nicht in einen Test, der auf jedem Rechner gruen sein soll.

Ausfuehren:
    python3 tools/test_feinheiten.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H          # noqa: E402

import fe.settings as S       # noqa: E402

fm = H.fm
fails = []
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QF = open(H.FRONTEND_PY, encoding="utf-8", errors="replace").read()


def check(name, ok, info=""):
    print(("  OK   " if ok else "  FEHL ") + name
          + (("  " + str(info)) if info else ""))
    if not ok:
        fails.append(name)


# ---------------------------------------------------------------------------
print("Test 1: sie werden WIRKLICH gezeichnet")
# ---------------------------------------------------------------------------
H.set_screen(1920, 1080)
fe = H.make_frontend(page=1)
fb = fe.fb


def _bild(an):
    fm.FEIN = an
    fe._force_full_redraw = True
    fe.draw()
    return bytes(fb.buf)


alt = getattr(fm, "FEIN", True)
try:
    fe.ansicht_setzen("liste")
    ohne = _bild(False)
    mit = _bild(True)
    anders = sum(1 for a, b in zip(ohne, mit) if a != b)
    check("mit Feinheiten sieht die Liste anders aus", anders > 0,
          "%d Bytes" % anders)
    check("aber nicht das halbe Bild", anders < len(ohne) // 8,
          "%d von %d Bytes - es sind drei duenne Striche"
          % (anders, len(ohne)))

    # ---------------------------------------------------------------
    print()
    print("Test 2: NUR in der Listenansicht")
    # ---------------------------------------------------------------
    # Beim ersten Entwurf liefen Scrollbalken und Haarlinie auch in
    # Raster und Galerie - dort gibt es keine Liste, wohl aber die
    # Koordinaten dafuer. Der Messlauf zeigte prompt einen Unterschied,
    # der nichts mit ihnen zu tun hatte.
    for ansicht in ("raster", "galerie"):
        try:
            fe.ansicht_setzen(ansicht)
        except Exception:                                # noqa: BLE001
            continue
        a = _bild(False)
        b = _bild(True)
        # In Raster und Galerie gibt es keine Listenzeilen, also auch
        # keinen Akzentbalken - und Scrollbalken und Haarlinie sind
        # ausdruecklich auf "liste" beschraenkt.
        check("in der %s-Ansicht aendert sich nichts" % ansicht,
              a == b,
              "%d Bytes anders" % sum(1 for x, y in zip(a, b) if x != y))
    fe.ansicht_setzen("liste")
finally:
    fm.FEIN = alt

# ---------------------------------------------------------------------------
print()
print("Test 3: sie haengen am FENSTER, nicht am Zeiger")
# ---------------------------------------------------------------------------
# Das ist der ganze Grund, warum sie im Scrollschritt nichts kosten.
_leicht = QF.split("def _draw_navigate_items_impl")[1].split("\n    def ")[0]
check("der leichte Pfad zeichnet keinen Scrollbalken",
      "len(items) > self.items_visible" not in _leicht)
check("und keine Haarlinie",
      "art_karte_x0(list_right, fb.height, s) - 4 * s" not in _leicht)
_voll = QF.split("def _draw_page_items_impl")[1].split("\n    def ")[0]
check("der Seitenaufbau zeichnet beide",
      "len(items) > self.items_visible" in _voll
      and "art_karte_x0(list_right, fb.height, s) - 4 * s" in _voll)
check("und beide nur in der Listenansicht",
      _voll.count('_ansicht == "liste"') >= 2,
      "sonst laufen sie in Raster und Galerie mit")

# Der Akzentbalken ist das EINZIGE Element im Scrollschritt - er sitzt
# in draw_list_row(), und die wird im leichten Pfad fuer zwei Zeilen
# gerufen.
_zeile = QF.split("def draw_list_row")[1].split("\n    def ")[0]
check("der Akzentbalken sitzt in der Zeile", "if FEIN and not sel:" in _zeile)
check("und NICHT auf der markierten Zeile",
      "not sel" in _zeile.split("if FEIN")[1][:40],
      "dort IST der Hintergrund schon die Systemfarbe - unsichtbar")

# ---------------------------------------------------------------------------
print()
print("Test 4: der Schalter kostet im Zeichenweg nichts")
# ---------------------------------------------------------------------------
check("er ist eine Modulvariable", "FEIN = True" in QF)
check("und wird beim Start einmal gelesen",
      "feinheiten_uebernehmen()" in QF)
check("beim Umschalten sofort nachgezogen",
      "toggle_feinheiten()" in QF and QF.count("feinheiten_uebernehmen()") >= 2,
      "sonst wirkte er erst nach einem Neustart")
check("im Zeichenweg wird KEINE Datei gefragt",
      "feinheiten_an()" not in _zeile and "feinheiten_an()" not in _voll,
      "eine Abfrage je Zeile waere genau die Sorte stiller Kosten")
check("es gibt genau EINEN Schalter fuer alle drei",
      hasattr(S, "toggle_feinheiten")
      and not hasattr(S, "toggle_scrollbalken"),
      "drei Schalter fuer eine Frage waeren zwei zuviel")

# ---------------------------------------------------------------------------
print()
print("Test 5: der Schalter schaltet wirklich")
# ---------------------------------------------------------------------------
import tempfile                                          # noqa: E402
with tempfile.TemporaryDirectory() as tmp:
    _altf = S.FEINHEITEN_AUS_FLAG
    try:
        S.FEINHEITEN_AUS_FLAG = os.path.join(tmp, "feinheiten_aus")
        S._vergessen()
        check("Vorgabe ist AN", S.feinheiten_an() is True)
        S.toggle_feinheiten()
        check("einmal umschalten -> AUS", S.feinheiten_an() is False)
        S.toggle_feinheiten()
        check("und wieder zurueck", S.feinheiten_an() is True)
    finally:
        S.FEINHEITEN_AUS_FLAG = _altf
        S._vergessen()

check("der Menueeintrag ist verdrahtet",
      '"feinheiten"' in open(os.path.join(_REPO, "frontend", "fe",
                                          "menu.py"),
                             encoding="utf-8").read())

# ---------------------------------------------------------------------------
print()
print("Test 6: Rahmen und Schatten am Cover gibt es laengst")
# ---------------------------------------------------------------------------
# Der vierte Wunsch war "Rahmen und Schatten am Cover". Den gibt es
# seit Build 98 (Panel) bzw. Build 124 (Kacheln) - ein zweiter Rahmen
# darueber waere kein Gewinn, sondern ein Doppelrahmen.
check("das Cover-Panel hat einen Rahmen in Systemfarbe",
      "fb.rect(ax - 2 * s, ay - 2 * s, aw + 4 * s, 2 * s, accent)" in QF)
check("und einen Schlagschatten darunter",
      "fb.blend_rect_fast(ax + 3 * s, ay + ah - 4 * s" in QF)
check("die Kacheln haben einen eigenen Rahmen",
      "def _kachel_rahmen" in QF)

print()
if fails:
    print("FEHLGESCHLAGEN (%d):" % len(fails))
    for f in fails:
        print("  - %s" % f)
    sys.exit(1)
print("Alles in Ordnung.")
