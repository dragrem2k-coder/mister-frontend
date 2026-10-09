#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Der Anfangsbuchstabe beim Schnellscrollen ist raus (Build 250).

NUTZERWUNSCH, woertlich: "nimm bitte die Buchstaben in der listen
ansicht raus ich finde das bloed das die angezeigt werden wenn ich nach
unten mit gedrueckter taste mit angezeigt werden!"

WAS DAS WAR. Build 243, einer von vier "optischen Verschoenerungen" -
der grosse Anfangsbuchstabe im leeren Cover-Kasten, solange das Cover
beim Scrollen uebersprungen wird. Meine Begruendung damals: "bei 1041
Eintraegen in Arcade sagt er, wo man gerade ist". Sie war nicht falsch,
aber sie war MEINE: beim Scrollen steht der Titel ohnehin in der
markierten Zeile, und wer die Liste bedient, liest dort. Ein grosses
Zeichen, das bei jedem Schritt wechselt, ist dann Unruhe.

WARUM KEIN SCHALTER DARAUS WURDE. Ein abschaltbarer Buchstabe haette
drei Dinge behalten muessen, die alle Geld kosten, und zwar auch bei
jedem, der ihn ausgeschaltet laesst:

  * ein fb.text()-Aufruf je Scrollschritt auf dem kurzen Weg,
  * ein zusaetzliches Rechteck im Flip (Build 249 hat die Zelle gerade
    erst eintragen muessen, weil sie MITTEN in der ausgesparten
    Kastenflaeche liegt - fehlte sie, blieb der alte Buchstabe stehen),
  * einen Menuepunkt fuer etwas, das niemand sucht.

Entfernt ist billiger als abschaltbar. Diese Datei haelt beides fest:
dass er weg ist, und was das spart.

WAS GEPRUEFT WIRD

  1. Die drei Bausteine gibt es nicht mehr - und zwar wirklich nicht,
     nicht nur unbenutzt.
  2. Im ausgesparten Cover-Kasten wird nichts mehr beschrieben.
  3. Der Flip je Scrollschritt wird kleiner, GEZAEHLT in Bytes
     (Abschnitt E des Bench lehrt seit Build 242, dass eine Stoppuhr
     ihr Urteil unter Last wechselt - siehe auch Build 249 und
     tools/test_cover_panel.py).
  4. Der kurze Weg greift jetzt in JEDEM Schritt - vorher konnte ihn
     ein wechselnder Buchstabe nicht mehr verhindern (Build 247), aber
     er musste ihn nachzeichnen.
  5. Der Platzhalter "kein Artwork" kommt NICHT an die frei gewordene
     Stelle. Er waere eine Luege fuer einen Sekundenbruchteil, und
     genau die hat in Build 89 geblitzt - der Nutzer hat sie damals
     gemeldet ("ploppt immer erst 'kein Artwork' auf").
  6. Ein Eintrag OHNE Cover zeigt den Platzhalter weiterhin - der Fall
     darf nicht mit dem uebersprungenen Cover zusammenfallen.

Ausfuehren:
    python3 tools/test_keine_buchstaben.py
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H                                        # noqa: E402

import fe.bench as BENCH                                    # noqa: E402
import fe.art as ART                                        # noqa: E402

fm = H.fm
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_QF = io.open(os.path.join(_REPO, "frontend", "frontend.py"),
              encoding="utf-8").read()
fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


def _liste(fe, n=60):
    """Eine Listenansicht mit n Eintraegen, deren Anfangsbuchstaben
    WECHSELN.

    DAS IST DER PUNKT DIESER HILFSFUNKTION, und er stammt aus einem
    eigenen Fehler: der Pruefstand hiess bis Build 245 "Spiel 000" bis
    "Spiel 059", und dort war der Anfangsbuchstabe immer derselbe. Eine
    Messung, die am Buchstaben haengt, sah dort perfekt aus und war auf
    dem Geraet um den Faktor drei daneben. Hier heissen die Eintraege
    deshalb "Alpha 000", "Beta 001", "Gamma 002", ..."""
    _namen = ("Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta",
              "Eta", "Theta", "Iota", "Kappa", "Lambda", "My")
    bi, _bn, _nm = BENCH._groesste_kategorie(fe)
    fe.page = 1
    fe.cat_i = bi
    fe.nav_path = []
    _, node, _ = fe.cats[fe.cat_i]
    node["items"] = [("%s %03d" % (_namen[i % len(_namen)], i), "game",
                      ("/f/%d.sfc" % i, ".sfc", "SNES", None, None))
                     for i in range(n)]
    node.pop("_display_items_cache", None)
    fe.item_i = 0
    fe.scroll = 0
    fe.ansicht_setzen("liste")


def _cover_aus():
    """Das Cover wird waehrend des Scrollens UEBERSPRUNGEN - genau der
    Fall, in dem der Buchstabe erschien."""
    echt = ART.ART.get_scaled

    def ersatz(quelle, breite, hoehe, **k):
        ART.ART._defer_count = getattr(ART.ART, "_defer_count", 0) + 1
        return None

    ART.ART.get_scaled = ersatz
    return lambda: setattr(ART.ART, "get_scaled", echt)


def _schritte_messen(fe, schritte=6):
    """(MB je Schritt, Rechtecke des letzten Schritts, Zahl der
    Textaufrufe in der Boxart-Spalte)."""
    fb = fe.fb
    konto = {"bytes": 0, "letzte": [], "texte": 0}
    echt_rect, echt_rows, echt_voll = (fb.flip_rechtecke, fb.flip_rows,
                                       fb.flip)
    echt_text = fb.text
    _spalte_x = fb.width // 2

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

    def h_text(x, y, *a, **k):
        # GEZAEHLT WIRD NUR DER GROSSE EINZELBUCHSTABE, nicht jeder
        # Text in der Spalte. Darunter stehen Titel und Infozeilen, und
        # die sollen bleiben - der erste Entwurf dieses Tests zaehlte
        # sie mit und meldete zwoelf Aufrufe als Fehler.
        #
        # Der Buchstabe war unverwechselbar: EIN Zeichen in einer
        # Schriftgroesse von cover_h // 24, auf 1080p also rund 30,
        # waehrend der normale Text mit s = 3 gezeichnet wird.
        if (x > _spalte_x and len(a) >= 2 and isinstance(a[0], str)
                and len(a[0].strip()) == 1
                and isinstance(a[1], int) and a[1] >= 10):
            konto["texte"] += 1
        return echt_text(x, y, *a, **k)

    schritt = BENCH.schritt_funktion(fe, 1)
    schritt(0)
    spanne = BENCH.fenster_spanne(fe, 1)
    for i in range(6):
        schritt(i % spanne)
    fb.flip_rechtecke, fb.flip_rows, fb.flip = h_rect, h_rows, h_voll
    fb.text = h_text
    try:
        for i in range(schritte):
            schritt(i % spanne)
    finally:
        fb.flip_rechtecke, fb.flip_rows, fb.flip = (echt_rect, echt_rows,
                                                    echt_voll)
        fb.text = echt_text
    return (konto["bytes"] / float(schritte) / 1048576.0, konto["letzte"],
            konto["texte"])


# ---------------------------------------------------------------------------
print("Test 1: die drei Bausteine gibt es nicht mehr")
# ---------------------------------------------------------------------------
for _name, _was in (("_schnellmarke_zeichnen", "die Zeichenfunktion"),
                    ("schnellmarke_text", "die Zeichenwahl"),
                    ("SCHNELLMARKE_ANTEIL", "die Groessenvorgabe")):
    check("%s (%s) ist weg" % (_name, _was),
          ("def " + _name) not in _QF and (_name + " =") not in _QF)
# UND AUCH NICHT NUR UNBENUTZT: ein Aufruf ohne Definition waere ein
# NameError beim Scrollen - genau der Fehler, der in Build 248 bei
# scan_games() monatelang unentdeckt blieb.
check("und es ruft sie auch niemand mehr",
      "self._schnellmarke_zeichnen(" not in _QF
      and "self.schnellmarke_text(" not in _QF,
      "ein Aufruf ohne Definition waere ein NameError im Zeichenweg")
# Der Platzhalter dagegen MUSS bleiben.
check("_zeichne_kein_artwork() ist dagegen noch da",
      "def _zeichne_kein_artwork" in _QF,
      "er gilt fuer Eintraege, die WIRKLICH kein Cover haben")

# ---------------------------------------------------------------------------
print()
print("Test 2: beim uebersprungenen Cover wird in der Spalte nichts "
      "geschrieben")
# ---------------------------------------------------------------------------
H.set_screen(1920, 1080)
fe = H.make_frontend(page=1)
_liste(fe)
zurueck = _cover_aus()
try:
    mb, rechtecke, texte = _schritte_messen(fe)
finally:
    zurueck()

check("es wird ueberhaupt noch geflippt", mb > 0.1, "%.2f MB" % mb)
check("kein grosser Einzelbuchstabe mehr in der Spalte", texte == 0,
      "%d Aufrufe mit einem Zeichen in Schriftgroesse >= 10 - Titel "
      "und Infozeilen darunter werden nicht mitgezaehlt" % texte)
check("und kein quadratisches Rechteck mehr im Flip",
      not [r for r in rechtecke
           if r[2] > 60 and 0.7 < (float(r[2]) / max(1, r[3])) < 1.4],
      "die Zelle des Buchstaben war das einzige - die vier Streifen um "
      "den Kasten sind lang und schmal")

# ---------------------------------------------------------------------------
print()
print("Test 3: und es spart gezaehlte Bytes je Scrollschritt")
# ---------------------------------------------------------------------------
# GEZAEHLT, NICHT GESTOPPT. Build 249 hat in tools/test_cover_panel.py
# genau deshalb eine Stoppuhr ausgebaut: sie wurde unter paralleler
# Last rot, ohne dass sich am Code etwas geaendert hatte. Bytes sind
# ganze Zahlen und auf jedem Geraet dieselben; was sie kosten, hat das
# Geraet gemessen (MS_JE_MB = 2,1 in fe/bench.py, Abschnitt I.1).
check("unter dem Stand von Build 249", mb < 1.91,
      "%.2f MB je Schritt - Build 249: 1,91, vor Build 249: 3,21"
      % mb)
_gespart = (1.91 - mb)
check("die Ersparnis ist die Zelle des Buchstaben plus ihr Rand",
      0.01 < _gespart < 0.40,
      "%.3f MB je Schritt, nach dem Kostenmodell rund %.2f ms"
      % (_gespart, _gespart * BENCH.MS_JE_MB))

# ---------------------------------------------------------------------------
print()
print("Test 4: der kurze Weg greift in jedem Schritt")
# ---------------------------------------------------------------------------
# Bis Build 246 stand der Buchstabe im Vergleich _stand, und ein
# wechselnder Buchstabe hat den kurzen Weg verhindert - gemessen griff
# er in genau einem Drittel der Schritte. Build 247 nahm ihn heraus und
# zeichnete ihn mit; Build 250 nimmt ihn ganz weg.
_code = "\n".join(z for z in _QF.split("\n")
                  if not z.strip().startswith("#"))
_blk = _code.split("def draw_art_panel")[1].split("\n    def ")[0]
check("der Kasten ohne Cover hat keinen Inhalt mehr",
      '_kasten = ("marke",)' in _blk,
      "ein leerer Kasten sieht fuer jeden Eintrag gleich aus")
check("und der kurze Weg zeichnet dort nichts nach",
      "_schnellmarke" not in _blk,
      "vorher stand hier ein fb.text() je Schritt")

# ---------------------------------------------------------------------------
print()
print("Test 5: der Platzhalter kommt NICHT an die frei gewordene Stelle")
# ---------------------------------------------------------------------------
# Das ist die naheliegende, falsche Reparatur. Build 89 hat sie schon
# einmal zurueckgenommen, auf Meldung des Nutzers: "wenn ich durch die
# ROMs scrolle, ploppt immer erst 'kein Artwork' auf und dann wird das
# Cover nachgeladen". Bei uebersprungenem Cover kommt das echte Bild in
# rund 150 ms von selbst (COVER_SETTLE) - der Platzhalter waere eine
# Luege fuer einen Sekundenbruchteil.
# DIE ZWEITE STELLE, nicht die erste: "if _kurz:" steht in
# draw_art_panel() zweimal - erst fuer die Kastenluecke, dann fuer den
# Zeichenzweig. Der erste Entwurf nahm die erste und pruefte damit den
# falschen Block.
_zweig = _blk.split("if _kurz:")[2].split("art_bottom = cy + cover_h")[0]
check("er haengt weiter an 'not nur_verzoegert'",
      "elif not nur_verzoegert:" in _zweig
      and "self._zeichne_kein_artwork(" in _zweig)
check("und im uebersprungenen Fall wird gar nichts gezeichnet",
      _zweig.count("self._zeichne_kein_artwork(") == 1,
      "genau ein Aufruf, und der gilt dem Eintrag OHNE Cover")

# ---------------------------------------------------------------------------
print()
print("Test 6: ein Eintrag ohne Cover zeigt den Platzhalter weiterhin")
# ---------------------------------------------------------------------------
# Die beiden Faelle duerfen nicht zusammenfallen: "noch nicht geladen"
# bleibt leer, "gibt es nicht" bekommt den Rahmen.
fe2 = H.make_frontend(page=1)
_liste(fe2, n=8)
_gerufen = {"n": 0}
_echt_platz = type(fe2)._zeichne_kein_artwork


def _zaehl(selbst, *a, **k):
    _gerufen["n"] += 1
    return _echt_platz(selbst, *a, **k)


type(fe2)._zeichne_kein_artwork = _zaehl
_alt_defer = getattr(ART.ART, "_defer_uncached", False)
try:
    # KEIN uebersprungenes Cover - die Datei gibt es einfach nicht.
    ART.ART._defer_uncached = False
    fe2._force_full_redraw = True
    fe2.draw()
finally:
    type(fe2)._zeichne_kein_artwork = _echt_platz
    ART.ART._defer_uncached = _alt_defer
check("der Platzhalter wird gezeichnet", _gerufen["n"] > 0,
      "%d Aufrufe" % _gerufen["n"])

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
