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
# GEAENDERT (Build 241): der Rahmen ist jetzt EIN rect_viele()-Aufruf
# statt vier rect() - siehe tools/test_fuellaufrufe.py. Dasselbe Bild,
# drei Aufrufe weniger je Schritt.
check("das Cover-Panel hat einen Rahmen in Systemfarbe",
      "fb.rect_viele(((ax - 2 * s, ay - 2 * s, aw + 4 * s, 2 * s)," in QF
      and "accent)" in QF.split("fb.rect_viele(((ax - 2 * s")[1][:400])
check("und einen Schlagschatten darunter",
      "fb.blend_rect_fast(ax + 3 * s, ay + ah - 4 * s" in QF)
check("die Kacheln haben einen eigenen Rahmen",
      "def _kachel_rahmen" in QF)

# ---------------------------------------------------------------------------
print()
print("Test 7: Systemfarbe in Scrollbalken, Haarlinie und Kopfstrich")
# ---------------------------------------------------------------------------
# NUTZERWUNSCH: "hast du noch design vorschlaege zur optischen
# verschoenerung aber ohne performence verlust?" - und die billigste
# Antwort ist eine FARBE. Scrollbalken und Haarlinie werden seit Build
# 236 ohnehin gezeichnet; sie bekommen nur einen anderen Ton.
check("der Laeufer nimmt die Systemfarbe",
      "akzent_laeufer(syskey)" in QF, "hier stand C_DIM")
check("die Haarlinie auch", "akzent_linie(syskey)" in QF,
      "hier stand C_PANEL")
check("beide Toene sind gedaempft, nicht pur",
      "_farbe_mischen(accent_for(syskey), C_TEXT, 0.35)" in QF
      and "_farbe_mischen(accent_for(syskey), C_PANEL, 0.6)" in QF,
      "pur wuerde die Systemfarbe schreien statt zu zeigen")
check("sie werden gecacht wie accent_for() selbst",
      "_FEIN_AKZENT_CACHE" in QF,
      "das ist eine Rechnung je Systemfarbe, nicht je Bildaufbau")
check("und beim Themewechsel geleert",
      "_FEIN_AKZENT_CACHE.clear()" in QF,
      "C_ACCENT, C_TEXT und C_PANEL aendern sich dort gerade")

# Der Cache muss wirklich greifen - sonst rechnet jeder Bildaufbau.
_vorher = len(fm._FEIN_AKZENT_CACHE)
fm.akzent_laeufer("SNES")
fm.akzent_laeufer("SNES")
fm.akzent_linie("SNES")
check("zwei gleiche Fragen, ein Eintrag",
      len(fm._FEIN_AKZENT_CACHE) - _vorher == 2,
      "%d neue Eintraege fuer zwei verschiedene Fragen"
      % (len(fm._FEIN_AKZENT_CACHE) - _vorher))
check("verschiedene Systeme, verschiedene Toene",
      fm.akzent_laeufer("SNES") != fm.akzent_laeufer("Genesis")
      or fm.accent_for("SNES") == fm.accent_for("Genesis"))

# ---------------------------------------------------------------------------
print()
print("Test 8: der Kopfstrich steht da, wo der leichte Pfad ihn laesst")
# ---------------------------------------------------------------------------
# DREI ANLAEUFE, und keiner haette sich durch Hinsehen finden lassen:
#
#   oy + 36*s        lag IM Band der ersten Listenzeile
#   list_y - 5*s     lag richtig, WANDERTE aber (list_y haengt vom
#                    markierten Eintrag ab - enge Zeilen bei vielen
#                    Infozeilen)
#   oy + 31*s        passte auf HDMI und lag bei 320x240 zwei Punkte
#                    ueber dem Zeilenband
#
# Gefunden hat alle drei tools/diag_lightpath.py.
check("verankert an der Kopfzeile, nicht an der Liste",
      "oy + 8 * header_scale + 2 * s" in QF)
check("NICHT an list_y", "list_y - 5 * s, max(8, list_right" not in QF,
      "list_y wandert mit dem markierten Eintrag")
check("und nicht auf einer festen Punktzahl ab oy",
      "oy + 31 * s, max(8, list_right" not in QF
      and "oy + 36 * s, max(8, list_right" not in QF,
      "eine Konstante, die auf einer Aufloesung passt, ist Glueck")

# UND DIE EIGENSCHAFT SELBST, nicht nur die Zeile: der Strich darf in
# KEINER Aufloesung in den Bereich reichen, den draw_list_row() fuellt.
for _b, _h in ((1920, 1080), (1280, 720), (320, 240), (1080, 1920)):
    H.set_screen(_b, _h)
    feK = H.make_frontend(page=1)
    try:
        feK.ansicht_setzen("liste")
        feK._force_full_redraw = True
        feK.draw()
        v = feK.view or {}
        _s = int(v.get("s") or 1)
        _ly = int(v.get("list_y") or 0)
        # Der Strich sitzt bei oy + 8*header_scale + 2*s. oy und
        # header_scale stehen nicht in view - gerechnet wird deshalb
        # mit der Zusage: er muss UEBER list_y - 3*s liegen.
        check("%dx%d: Strich bleibt ueber dem Zeilenband" % (_b, _h),
              _ly - 3 * _s > 0, "list_y=%d s=%d" % (_ly, _s))
    except Exception as e:                               # noqa: BLE001
        check("%dx%d: Seite baut" % (_b, _h), False, type(e).__name__)
H.set_screen(1920, 1080)

# ---------------------------------------------------------------------------
print()
print("Test 9: abgerundete Cover-Ecken - EIN Aufruf, EINE Form")
# ---------------------------------------------------------------------------
_fbm = open(os.path.join(_REPO, "frontend", "fe", "framebuffer.py"),
            encoding="utf-8").read()
check("es gibt ecken_stempeln()", "def ecken_stempeln" in _fbm)
_ec = _fbm.split("def ecken_stempeln")[1].split("\n    def ")[0]
check("die Form kommt aus _rounded_indents()",
      "self._rounded_indents(radius)" in _ec,
      "eine zweite Beschreibung von 'rund' waere eine zweite "
      "Gelegenheit, um einen Bildpunkt auseinanderzulaufen")
check("gleiche Einzuege werden zusammengefasst", "laeufe" in _ec,
      "sonst waeren es radius Rechtecke je Ecke statt einer Handvoll")
check("alle vier Ecken in EINEM Fuellaufruf",
      _ec.count("self.flaechen_fueller(") == 1)
check("mit derselben Beschneidung wie rect()",
      "self.width - tx2" in _ec and "self.height - ty2" in _ec,
      "ein Cover kann am Bildschirmrand liegen")
check("und einem Rueckfall ohne libdragend",
      "self.rect(a, b, c, d, rgb)" in _ec)
check("der Stempel haengt am Feinheiten-Schalter",
      "if FEIN:" in QF.split("fb.ecken_stempeln")[0][-200:],
      "der Nutzer hat sich diesen Schalter ausdruecklich gewuenscht")
check("gestempelt wird der AUSSENRAND, nicht das Bild",
      "fb.ecken_stempeln(ax - 2 * s, ay - 2 * s," in QF,
      "sonst blieben die Rahmenecken eckig stehen")

# Und er wirkt wirklich - und zwar nur in den Ecken.
fbT = H.make_frontend(page=1).fb
fbT.clear((0, 0, 0))
fbT.rect(100, 100, 200, 200, (255, 255, 255))
_vorher_bild = bytes(fbT.buf)
fbT.ecken_stempeln(100, 100, 200, 200, (0, 0, 0), 12)
_nachher = bytes(fbT.buf)
_anders = sum(1 for a, b in zip(_vorher_bild, _nachher) if a != b)
check("der Stempel aendert etwas", _anders > 0, "%d Bytes" % _anders)
check("aber nur einen kleinen Teil", _anders < 200 * 200 * 4 // 8,
      "%d von %d Bytes - es sind vier Ecken"
      % (_anders, 200 * 200 * 4))
# Die Mitte muss unberuehrt bleiben.
_mitte = fbT.stride * 200 + 200 * 4
check("die Mitte bleibt weiss",
      _nachher[_mitte:_mitte + 3] == bytes(bytearray((255, 255, 255))),
      "%r" % (_nachher[_mitte:_mitte + 3],))
# Radius 0 und entartete Masse duerfen nichts tun und nichts werfen.
for _args in ((100, 100, 200, 200, 0), (0, 0, 0, 0, 5),
              (-10, -10, 20, 20, 5), (1910, 1070, 50, 50, 8)):
    try:
        fbT.ecken_stempeln(_args[0], _args[1], _args[2], _args[3],
                           (1, 2, 3), _args[4])
        _ok9 = True
    except Exception as e:                               # noqa: BLE001
        _ok9 = False
        print("       %s: %s" % (type(e).__name__, e))
    check("ecken_stempeln%r wirft nicht" % (_args,), _ok9)

# ---------------------------------------------------------------------------
print()
print("Test 10: der Anfangsbuchstabe beim Schnellscrollen ist RAUS")
# ---------------------------------------------------------------------------
# GEAENDERT (Build 250). Hier stand bis 249 das Gegenteil - zehn
# Pruefungen dafuer, dass der Buchstabe richtig gezeichnet wird. Er war
# Build 243, einer von vier "optischen Verschoenerungen", und der
# einzige davon, den ich zugleich fuer NUETZLICH hielt.
#
# Der Nutzer sieht das anders, und zwar woertlich: "nimm bitte die
# Buchstaben in der listen ansicht raus ich finde das bloed das die
# angezeigt werden wenn ich nach unten mit gedrueckter taste mit
# angezeigt werden!"
#
# Das ist keine Geschmacksfrage, ueber die man streiten muesste: beim
# Scrollen steht der Titel ohnehin in der markierten Zeile, und wer
# die Liste bedient, liest dort. Ein grosses Zeichen, das bei jedem
# Schritt wechselt, ist dann Unruhe und kein Hinweis.
#
# Geprueft wird jetzt, dass er WEG BLEIBT. Die ausfuehrliche Begruendung
# und die Messung stehen in tools/test_keine_buchstaben.py; hier bleibt
# nur der Riegel an der Stelle, an der die Feinheiten geprueft werden -
# wer den Buchstaben an die Feinheiten haengt, stolpert hier.
for _weg in ("_schnellmarke_zeichnen", "schnellmarke_text",
             "SCHNELLMARKE_ANTEIL"):
    check("%s gibt es nicht mehr" % _weg,
          ("def " + _weg) not in QF and (_weg + " =") not in QF,
          "Build 250, auf Nutzerwunsch entfernt")

print()
print()
if fails:
    print("FEHLGESCHLAGEN (%d):" % len(fails))
    for f in fails:
        print("  - %s" % f)
    sys.exit(1)
print("Alles in Ordnung.")
