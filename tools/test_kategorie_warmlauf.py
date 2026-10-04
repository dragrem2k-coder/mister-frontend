#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Der Warmlauf der Namensverzeichnisse (Build 239).

DER ANLASS ist eine Meldung vom Geraet, die fuenf Kategorien nannte und
keine sechste: "wenn ich in die kategorie weiterspielen gehe haengt er
am anfang ganz schoen bis das frontend wahrscheinlich die covers dort
geladen hat. RA-Erfolgsjaeger genauso. bei sammlung und 2026 entdeckt
sowie kurzweilige spiele genauso."

Alle fuenf sind GEMISCHTE Kategorien, und die Ursache steht in
tools/diag_kategorie_betreten.py: beide Namensverzeichnisse werden JE
SYSTEM gebaut, und bei einer gemischten Kategorie faellt das komplett in
den Moment, in dem die Seite zum ersten Mal gezeichnet wird. Gemessen
im Raster: ein System = 1 Verzeichnisdurchlauf, zwoelf Systeme = 10.

DIESER TEST HAELT VIER DINGE FEST, und jedes einzelne davon war beim
Bauen schon einmal falsch:

  1. Der Warmlauf wirkt. Nach genug Ruhemomenten kostet das Betreten
     KEINEN Verzeichnisdurchlauf mehr.
  2. Er nimmt EIN System je Ruhemoment. Nicht alle - ein Durchlauf
     haelt beim Zerlegen der Dateinamen die GIL, und genau daran ist
     Build 107 schon einmal haengengeblieben.
  3. Er fragt die VERZEICHNISSE, nicht einen eigenen Merker. Der erste
     Entwurf hatte so einen Merker, und er stand vor der Abfrage: wer
     "Zwischenspeicher leeren" benutzte, bekam nie wieder einen
     Warmlauf.
  4. Er laeuft nur im Stillstand - nicht waehrend der Bedienung.

Ausfuehren:
    python3 tools/test_kategorie_warmlauf.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H          # noqa: E402

import fe.art as ART          # noqa: E402

fails = []
QF = open(H.FRONTEND_PY, encoding="utf-8", errors="replace").read()

SYSTEME = ("SNES", "Genesis", "NES", "PSX", "Amiga", "GBA",
           "TurboGrafx16", "N64", "MegaCD", "C64", "Saturn", "SMS")


def check(name, ok, info=""):
    print(("  OK   " if ok else "  FEHL ") + name
          + (("  " + str(info)) if info else ""))
    if not ok:
        fails.append(name)


def _items(systeme, anzahl=60):
    aus = []
    for i in range(anzahl):
        sk = systeme[i % len(systeme)]
        aus.append(("Spiel %03d" % i, "game",
                    ("/f/%s/%d.rom" % (sk, i), ".rom", sk, None, None)))
    return aus


def _kalt():
    ART._art_index_cache.clear()
    ART._docs_index_cache.clear()
    ART._thumb_fehlt.clear()
    ART._quell_stat.clear()
    ART.quelldaten_vergessen()
    ART.negativ_vergessen()


def _setzen(fe, systeme):
    _, node, _ = fe.cats[0]
    node["folders"] = {}
    node["items"] = _items(systeme)
    node.pop("_display_items_cache", None)
    fe._warmlauf_fertig_fuer = None


# ---------------------------------------------------------------------------
print("Test 1: er findet die Systeme einer gemischten Kategorie")
# ---------------------------------------------------------------------------
H.set_screen(1920, 1080)
fe = H.make_frontend(page=1)
_kalt()
_setzen(fe, SYSTEME)
fe.page = 0
fe.cat_i = 0
offen = fe._warmlauf_systeme()
check("alle zwoelf Systeme stehen an", len(offen) == 12,
      "gefunden: %d - %s" % (len(offen), ", ".join(offen[:4]) + " ..."))
check("jedes nur einmal", len(set(offen)) == len(offen))

_kalt()
_setzen(fe, ("SNES",))
check("bei einer Systemkategorie genau eins",
      len(fe._warmlauf_systeme()) == 1,
      "das ist der Fall, der NIE gemeldet wurde")

# ---------------------------------------------------------------------------
print()
print("Test 2: EIN System je Ruhemoment, nicht alle")
# ---------------------------------------------------------------------------
_kalt()
_setzen(fe, SYSTEME)
fe.page = 0
fe.cat_i = 0
vorher = len(ART._docs_index_cache)
check("ein Tick arbeitet", fe._warmlauf_tick() is True)
check("und baut genau ein System",
      len(ART._docs_index_cache) - vorher == 1,
      "%d dazugekommen - mehr waere die GIL-Falle aus Build 107"
      % (len(ART._docs_index_cache) - vorher))

ticks = 1
while fe._warmlauf_tick():
    ticks += 1
    if ticks > 50:
        break
check("nach zwoelf Ticks ist Schluss", ticks == 12, "%d Ticks" % ticks)
check("alle zwoelf sind gebaut", len(ART._docs_index_cache) == 12,
      "%d" % len(ART._docs_index_cache))
check("danach steht nichts mehr an", fe._warmlauf_systeme() == [])

# ---------------------------------------------------------------------------
print()
print("Test 3: danach kostet das Betreten keinen Durchlauf mehr")
# ---------------------------------------------------------------------------


def _betreten_zaehlen(ansicht):
    """Eine Kategorie betreten und die Verzeichnisdurchlaeufe zaehlen."""
    konto = [0]
    echt = os.listdir

    def _ld(p, *a, **k):
        konto[0] += 1
        return echt(p, *a, **k)

    fe.page = 1
    fe.cat_i = 0
    fe.nav_path = []
    fe.item_i = 0
    fe.scroll = 0
    fe.ansicht_setzen(ansicht)
    os.listdir = _ld
    try:
        fe._force_full_redraw = True
        fe.draw()
    finally:
        os.listdir = echt
    return konto[0]


for ansicht in ("raster", "galerie"):
    _kalt()
    _setzen(fe, SYSTEME)
    kalt = _betreten_zaehlen(ansicht)

    _kalt()
    _setzen(fe, SYSTEME)
    fe.page = 0
    fe.cat_i = 0
    for _ in range(30):
        if not fe._warmlauf_tick():
            break
    warm = _betreten_zaehlen(ansicht)

    check("%s: kalt kostet Durchlaeufe" % ansicht, kalt > 1,
          "%d - auf dem Geraet rund %.1f s" % (kalt, kalt * 0.167))
    check("%s: nach dem Ruhemoment keinen" % ansicht, warm == 0,
          "%d statt %d" % (warm, kalt))

# ---------------------------------------------------------------------------
print()
print("Test 4: gefragt werden die Verzeichnisse, nicht ein Merker")
# ---------------------------------------------------------------------------
# DAS WAR DER FEHLER DES ERSTEN ENTWURFS. Er hatte ein
# _index_warm_fertig-Set, und die Abfrage stand VOR der Abfrage der
# Verzeichnisse. Wird zwischendurch geleert ("Zwischenspeicher leeren"
# im Menue tut genau das), behauptete der Merker weiter, alles sei warm.
_kalt()
_setzen(fe, SYSTEME)
fe.page = 0
fe.cat_i = 0
for _ in range(30):
    if not fe._warmlauf_tick():
        break
check("erst ist alles warm", fe._warmlauf_systeme() == [])
# Jetzt leeren, wie es das Menue tut:
ART._art_index_cache.clear()
ART._docs_index_cache.clear()
fe._warmlauf_fertig_fuer = None
check("nach dem Leeren steht wieder alles an",
      len(fe._warmlauf_systeme()) == 12,
      "sonst liefe der Warmlauf nie wieder - genau der Fehler von vorhin")
check("es gibt keinen eigenen Merker mehr",
      not hasattr(ART, "_index_warm_fertig"),
      "ein zweiter Ort fuer dieselbe Wahrheit war einer zuviel")

# ---------------------------------------------------------------------------
print()
print("Test 5: er laeuft nur im Stillstand")
# ---------------------------------------------------------------------------
_stelle = QF.split("self._warmlauf_tick()")[0]
check("der Aufruf haengt hinter nav_active",
      "nav_active = (time.monotonic() - self._last_input_time" in _stelle
      and "if not any_dialog and not nav_active:" in _stelle[-400:],
      "sonst arbeitete er mitten im Scrollen")
check("und nicht im Zeichenweg",
      "_warmlauf_tick" not in QF.split("def draw_list_row")[1]
      .split("\n    def ")[0])
check("der Merker verhindert das Abtasten im Dauerlauf",
      "_warmlauf_fertig_fuer" in QF,
      "der Tick kommt alle 0.08 s - 60 Eintraege abtasten fuer nichts")

# ---------------------------------------------------------------------------
print()
print("Test 6: er bricht nichts, wenn es nichts zu tun gibt")
# ---------------------------------------------------------------------------
_, node, _ = fe.cats[0]
for was, bauen in (
        ("eine leere Kategorie", lambda: node.update(items=[], folders={})),
        ("kaputte Eintraege", lambda: node.update(
            items=[("x", "game", None), ("y", "game", ()), ("z", "game", 7)],
            folders={})),
        ("Eintraege ohne System", lambda: node.update(
            items=[("x", "game", ("/f/x.rom", ".rom", None, None, None))],
            folders={}))):
    bauen()
    node.pop("_display_items_cache", None)
    fe._warmlauf_fertig_fuer = None
    try:
        fe._warmlauf_systeme()
        fe._warmlauf_tick()
        ok = True
    except Exception as e:                               # noqa: BLE001
        ok = False
        print("       %s: %s" % (type(e).__name__, e))
    check("%s wirft nicht" % was, ok)

# Auch ohne Kategorien ueberhaupt:
_cats = fe.cats
try:
    fe.cats = []
    fe._warmlauf_fertig_fuer = None
    fe._warmlauf_systeme()
    fe._warmlauf_tick()
    check("ohne Kategorien wirft es nicht", True)
except Exception as e:                                   # noqa: BLE001
    check("ohne Kategorien wirft es nicht", False, type(e).__name__)
finally:
    fe.cats = _cats

print()
if fails:
    print("FEHLGESCHLAGEN (%d):" % len(fails))
    for f in fails:
        print("  - %s" % f)
    sys.exit(1)
print("Alles in Ordnung.")
