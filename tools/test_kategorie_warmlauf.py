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
def _systeme_im_cache():
    """Wie viele SYSTEME im Docs-Zwischenspeicher stehen - nicht wie
    viele Eintraege.

    GEAENDERT IN BUILD 294, und zwar am Messwert, nicht an der Zusage.
    Hier stand len(ART._docs_index_cache), und das war bis dahin
    dasselbe: ein Eintrag je System. Seit Build 294 hat jedes System
    DREI Indizes (Cover, Bildschirmfoto, Titelbild - siehe
    DOCS_BILDARTEN), der Schluessel ist fuer "boxart" der nackte
    syskey und sonst das Paar (syskey, art).

    Die Zusage dieses Tests ist unveraendert: HOECHSTENS EIN SYSTEM je
    Ruhemoment, sonst die GIL-Falle aus Build 107. Gezaehlt werden
    deshalb jetzt Systeme. Haette ich stattdessen die erwartete Zahl
    von 1 auf 3 hochgesetzt, waere der Test bei der naechsten Bildart
    wieder rot geworden - und zwar ohne dass sich an dem, was er
    sichern soll, etwas geaendert haette."""
    return len({k[0] if isinstance(k, tuple) else k
                for k in ART._docs_index_cache})


vorher = _systeme_im_cache()
check("ein Tick arbeitet", fe._warmlauf_tick() is True)
check("und baut genau ein System",
      _systeme_im_cache() - vorher == 1,
      "%d dazugekommen - mehr waere die GIL-Falle aus Build 107"
      % (_systeme_im_cache() - vorher))
# UMGESTELLT IN BUILD 295, und das ist der Kern dieses Builds.
#
# Hier stand nach Build 294:
#
#     check("und von diesem System alle drei Bildarten", ...)
#
# Das war die Zusage, die der Nutzer als Fehler gemeldet hat: "wenn
# ich das frontend starte reagiert fuer ein paar sekunden die joypad
# eingabe manchmal nicht oder klemmt oder lagt ein wenig".
#
# Build 294 baute alle drei Arten in EINEM Tick. Ein
# Verzeichnisdurchlauf kostet auf dem Geraet rund 167 ms - drei davon
# sind eine halbe Sekunde, in der eine Taste wartet, denn ein
# begonnener Tick laeuft durch. Schlimmer noch: der ZEICHENWEG
# blockiert nur auf dem COVER-Index; Foto und Titelbild braucht allein
# der Vermerk "R2 1/3", der ausdruecklich spaeter kommen darf. Das
# Cover des ZWEITEN Systems war damit erst nach dreimal so viel
# Vorarbeit da - ich hatte das Mittel gegen den Ruckler dreimal
# langsamer gemacht.
#
# JETZT: ein Tick baut die blockierende Gruppe EINES Systems (genau
# das, was vor Build 294 ein Tick war), die Extras kommen in eigenen
# Ticks danach.
check("und zwar dessen COVER-Index, denn nur der haelt das Zeichnen auf",
      ART._docs_index_fertig(SYSTEME[0], "boxart"))
check("die Extras kommen NICHT im selben Tick",
      not ART._docs_index_fertig(SYSTEME[0], "snap")
      and not ART._docs_index_fertig(SYSTEME[0], "titel"),
      "drei Durchlaeufe in einem Tick sind eine halbe Sekunde, "
      "in der eine Taste wartet")
# UND DIE REIHENFOLGE UEBER DIE SYSTEME: erst alle Cover, dann die
# Extras. Das ist die eigentliche Behebung - gepruefter Ablauf, nicht
# nur eine kleinere Portion.
for _ in range(len(SYSTEME) - 1):
    fe._warmlauf_tick()
check("nach einem Tick je System sind ALLE Cover da",
      all(ART._docs_index_fertig(s, "boxart") for s in SYSTEME),
      "genau so frueh wie vor Build 294")
check("und noch kein einziges Extra",
      not any(ART._docs_index_fertig(s, a)
              for s in SYSTEME for a in ("snap", "titel")),
      "der Vermerk darf warten, das Cover nicht")

# GEAENDERT IN BUILD 295 - am Messwert, nicht an der Zusage. Hier
# stand "nach zwoelf Ticks ist Schluss", also ein Tick je System.
# Seit Build 295 ist ein Tick ein STUECK ARBEIT: zwoelf Cover plus
# zwoelfmal zwei Extras, zusammen 36. Das ist der Preis dafuer, dass
# ein einzelner Tick wieder so billig ist wie vor Build 294 - und
# genau das war die Behebung.
#
# Gezaehlt wird deshalb von KALT, nicht ab hier: oben sind schon
# zwoelf Ticks gelaufen, und eine Zahl, die davon abhaengt, wie viele
# Pruefungen vorher stehen, ist beim naechsten Einschub falsch.
_kalt()
_setzen(fe, SYSTEME)
fe.page = 0
fe.cat_i = 0
ticks = 0
while fe._warmlauf_tick():
    ticks += 1
    if ticks > 100:
        break
erwartet = len(SYSTEME) * len(ART.DOCS_BILDARTEN)
check("er endet, und zwar nach genau so vielen Ticks wie Arbeit",
      ticks == erwartet,
      "%d Ticks, erwartet %d (%d Systeme x %d Bildarten)"
      % (ticks, erwartet, len(SYSTEME), len(ART.DOCS_BILDARTEN)))
check("alle zwoelf sind gebaut", _systeme_im_cache() == 12,
      "%d Systeme, %d Eintraege"
      % (_systeme_im_cache(), len(ART._docs_index_cache)))
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
    # Abgeleitet, nicht fest verdrahtet - siehe Test 4 (Build 295).
    for _ in range(len(SYSTEME) * len(ART.DOCS_BILDARTEN) + 5):
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
# ABGELEITET, NICHT FEST VERDRAHTET (Build 295). Hier stand
# range(30), was fuer zwoelf Systeme mit einer Bildart reichte. Mit
# drei Bildarten sind 36 Ticks noetig, und die Schleife war vorher
# fertig - die Pruefung darunter ging rot, obwohl am Warmlauf nichts
# falsch war. Eine Obergrenze, die sich aus der Arbeit ergibt, kann
# bei der naechsten Bildart nicht wieder danebenliegen.
for _ in range(len(SYSTEME) * len(ART.DOCS_BILDARTEN) + 5):
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
      "nav_active = self._nav_active()" in _stelle
      and "if not any_dialog and not nav_active:" in _stelle[-400:],
      "sonst arbeitete er mitten im Scrollen - seit Build 276 wird die "
      "Frage an EINER Stelle beantwortet, und eine gehaltene Taste "
      "zaehlt dort mit")
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
