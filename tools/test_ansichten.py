#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft die drei Ansichten der Spieleliste (Build 122).

Nutzerwunsch nach den Kachel-Entwuerfen: "B und D und das alte als
Schalter einbauen", und zur Bedienung: "besser nur per Schalter unter
Anzeige und Sound".

WORAUF ES ANKOMMT - und das ist bei einer neuen Ansicht nicht das
Aussehen, sondern drei Dinge, die man nicht sieht:

  1. DIE KASTENGROESSE. Der Schluessel des Miniatur-Zwischenspeichers
     enthaelt sie (siehe _thumb_cache_key() in fe/art.py). Fragt der
     Zeichenpfad ein Cover in einer anderen Groesse an, als der
     Vorauslader vorberechnet hat, legt der Vorauslader fleissig
     Miniaturen an, die nie jemand findet - und es ruckelt, obwohl
     "Miniaturen vorbereiten" durchgelaufen ist. Genau das ist bei der
     Listenansicht schon einmal passiert (Build 73), deshalb wird es
     hier fuer BEIDE neuen Ansichten nachgeprueft.

  2. DER SCHNELLE PFAD IM RASTER. Bei einem Schritt innerhalb einer
     Rasterseite werden nur ZWEI Kacheln neu gezeichnet. Das Ergebnis
     muss bitgenau dasselbe sein wie ein kompletter Neuaufbau - sonst
     bleiben Reste stehen, so wie frueher bei der Liste.

  3. DIE LEICHTEN PFADE DER LISTE DUERFEN SICH RAUSHALTEN. Sie kennen
     nur Zeilen. Griffen sie im Raster, wuerden sie mitten ins Bild
     zeichnen.

Ausfuehren:
    python3 tools/test_ansichten.py
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)

import _harness as H                                    # noqa: E402

fm = H.fm
sys.path.insert(0, os.path.join(_REPO, "frontend"))
import fe.settings as S                                 # noqa: E402
import fe.input as I                                    # noqa: E402
import fe.menu as M                                     # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


def unterschiede(a, b):
    """Anzahl abweichender Bildpunkte zweier Puffer."""
    if len(a) != len(b):
        return -1
    n = 0
    for i in range(0, len(a), 4):
        if a[i:i + 4] != b[i:i + 4]:
            n += 1
    return n


print("Test 1: alle drei Ansichten zeichnen ueberhaupt")
for breite, hoehe, wie in ((1920, 1080, "HDMI"), (320, 240, "CRT")):
    H.set_screen(breite, hoehe)
    f = H.make_frontend(page=1)
    f.item_i = 9
    for ansicht in S.ANSICHTEN:
        f.ansicht_setzen(ansicht)
        try:
            f.draw()
            ok, fehler = True, ""
        except Exception as e:                           # noqa: BLE001
            ok, fehler = False, repr(e)
        check("%-4s %-8s zeichnet" % (wie, ansicht), ok, fehler)
        check("%-4s %-8s faerbt den Schirm" % (wie, ansicht),
              any(f.fb.buf[:4096]))

print()
print("Test 2: die Kastengroesse, die gezeichnet wird, ist die, die")
print("        der Vorauslader vorberechnet")
# DER Test dieses Builds. Aufgezeichnet wird, welche Groessen der
# Zeichenpfad tatsaechlich bei ART.get_scaled() anfragt; verglichen
# wird mit dem, was cover_pfad_und_kasten() dem Vorauslader nennt.
for breite, hoehe, wie in ((1920, 1080, "HDMI"), (320, 240, "CRT")):
    H.set_screen(breite, hoehe)
    f = H.make_frontend(page=1)
    f.item_i = 3
    for ansicht in ("raster", "galerie"):
        f.ansicht_setzen(ansicht)
        gefragt = []
        echt = fm.ART.get_scaled

        def merken(pfad, bw, bh, *a, **kw):
            gefragt.append((bw, bh))
            return echt(pfad, bw, bh, *a, **kw)

        fm.ART.get_scaled = merken
        try:
            f.draw()
        finally:
            fm.ART.get_scaled = echt
        geo = f._art_panel_geometrie(ansicht)
        items = f._display_items()
        _n, _r, syskey = f.cats[f.cat_i]
        auftrag = f.cover_pfad_und_kasten(items[f.item_i], syskey, geo)
        check("%-4s %-8s Vorauslader kennt eine Groesse" % (wie, ansicht),
              auftrag is not None, repr(geo))
        if auftrag and gefragt:
            # Im Raster sind alle Kacheln gleich gross, in der Galerie
            # gibt es zwei Groessen (grosses Cover + Leiste) - das
            # GROSSE ist das, auf das es ankommt, und es muss dabei
            # sein.
            check("%-4s %-8s und genau die wird gezeichnet"
                  % (wie, ansicht),
                  (auftrag[1], auftrag[2]) in gefragt,
                  "Vorauslader %r, gezeichnet %r"
                  % ((auftrag[1], auftrag[2]), sorted(set(gefragt))))

print()
print("Test 3: der schnelle Pfad im Raster ist bitgenau der volle Aufbau")
for breite, hoehe, wie in ((1920, 1080, "HDMI"), (320, 240, "CRT")):
    H.set_screen(breite, hoehe)
    f = H.make_frontend(page=1)
    f.ansicht_setzen("raster")
    f.item_i = 0
    f.draw()
    # Ein paar Schritte INNERHALB der Rasterseite - jeder davon nimmt
    # den schnellen Weg.
    for schritt in (1, 1, 1, 1):
        f.item_i += schritt
        f.draw()
    schnell = bytes(f.fb.buf)
    # Derselbe Zustand, aber erzwungen voll aufgebaut.
    f._raster_fast_key = None
    f.fb.mark_full_redraw()
    f.draw()
    voll = bytes(f.fb.buf)
    n = unterschiede(schnell, voll)
    check("%-4s vier Schritte ueber den schnellen Weg" % wie, n == 0,
          "%d abweichende Bildpunkte" % n)

    # Und derselbe Vergleich RUECKWAERTS - dort wurde bei der Liste
    # frueher der Rest der alten Markierung stehen gelassen.
    for _ in range(3):
        f.item_i -= 1
        f.draw()
    schnell = bytes(f.fb.buf)
    f._raster_fast_key = None
    f.fb.mark_full_redraw()
    f.draw()
    n = unterschiede(schnell, bytes(f.fb.buf))
    check("%-4s und drei Schritte zurueck" % wie, n == 0,
          "%d abweichende Bildpunkte" % n)

print()
print("Test 4: die leichten Pfade der Liste halten sich raus")
H.set_screen(1920, 1080)
f = H.make_frontend(page=1)
f.ansicht_setzen("liste")
f.item_i = 3
f.draw()
# ansicht_setzen() setzt _force_full_redraw - das ist ein EINMALIGER
# Merker, den der naechste leichte Pfad aufbraucht (so war der Merker
# schon immer gedacht: "der naechste Teil-Redraw ist unsicher"). Genau
# dieser eine Aufruf lehnt also ab; erst der danach greift wieder. Das
# hier stehen zu lassen ist der Punkt: sonst prueft der Test unten nur
# noch, dass der leichte Pfad IMMER ablehnt, und waere wertlos.
f.item_i += 1
f._draw_navigate_items(3)
f.draw()
alt_i = f.item_i
f.item_i += 1
check("in der Liste greift der leichte Pfad",
      f._draw_navigate_items(alt_i) is True)
for ansicht in ("raster", "galerie"):
    f.ansicht_setzen(ansicht)
    f.item_i = 3
    f.draw()
    f.item_i = 4
    check("in %-8s lehnt er ab" % ansicht,
          f._draw_navigate_items(3) is False)
    check("und die Laufschrift auch", f.marquee_needed() is False)

print()
print("Test 5: ohne Cover-Spalte bleibt es bei der Liste")
H.set_screen(1920, 1080)
f = H.make_frontend(page=1)
f.ansicht_setzen("raster")
check("mit Spielen ist Raster erlaubt", f.aktuelle_ansicht() == "raster")
# Eine Ebene aus lauter Ordnern - dort gibt es keine Cover-Spalte
# (siehe hat_artspalte()), und ein Raster waere eine Flaeche voller
# Platzhalter.
_n, node, _s = f.cats[f.cat_i]
node["items"] = [("Unterordner/", "folder", "Unterordner")]
node.pop("_display_items_cache", None)
check("reine Ordnerauswahl faellt auf Liste zurueck",
      f.aktuelle_ansicht() == "liste")
check("und Umschalten macht dort gar nichts",
      f.ansicht_umschalten() is None)
f.page = 0
check("auf der Hauptseite ebenfalls Liste",
      f.aktuelle_ansicht() == "liste")

print()
print("Test 6: die Richtungstasten folgen der Anordnung (Build 127)")
# GEAENDERT (Build 127). Hier standen frueher drei Zeichenketten-
# Vergleiche auf den Quelltext. Die waren gruen, waehrend die Bedienung
# falsch war: die Galerie lag wie die Liste verdrahtet, obwohl ihre
# Nachbarn WAAGERECHT liegen. Der Nutzer: "ich druecke oben und unten,
# um nach rechts und links zu gehen, das ist mist".
#
# Ein Zeichenketten-Vergleich kann das nicht finden - er prueft, dass
# etwas dasteht, nicht was es bedeutet. Deshalb wird die echte
# Zuordnung jetzt AUSGEFUEHRT: _schritte() wird aus dem Quelltext
# herausgeloest und mit einer Attrappe aufgerufen.
import textwrap                                          # noqa: E402

quelle = open(os.path.join(_REPO, "frontend", "frontend.py"),
              encoding="utf-8", errors="replace").read()
_ab = quelle.index("def _schritte(")
_ab = quelle.rindex("\n", 0, _ab) + 1
_bis = quelle.index("hoch_runter, links_rechts = _schritte(", _ab)
_bis = quelle.rindex("\n", 0, _bis) + 1
_block = textwrap.dedent(quelle[_ab:_bis])
_ns = {}
exec("def _bauen(self, move_step, page_step):\n"                # noqa: S102
     + textwrap.indent(_block, "    ")
     + "    return _schritte\n", _ns)


class _Attrappe(object):
    _raster_spalten = 7
    _kat_raster_spalten = 5


MOVE, PAGE = 1, 9
_schritte = _ns["_bauen"](_Attrappe(), MOVE, PAGE)

check("Liste: hoch/runter ein Schritt, links/rechts eine Seite",
      _schritte("liste", "_raster_spalten") == (MOVE, PAGE),
      repr(_schritte("liste", "_raster_spalten")))
check("Raster: hoch/runter eine ganze REIHE, links/rechts ein Nachbar",
      _schritte("raster", "_raster_spalten") == (7, MOVE),
      repr(_schritte("raster", "_raster_spalten")))
check("Galerie: links/rechts ein Nachbar, hoch/runter eine Seite",
      _schritte("galerie", "_raster_spalten") == (PAGE, MOVE),
      repr(_schritte("galerie", "_raster_spalten")))
check("die Hauptseite rechnet mit IHRER Spaltenzahl",
      _schritte("raster", "_kat_raster_spalten") == (5, MOVE),
      repr(_schritte("raster", "_kat_raster_spalten")))
# Das eigentliche Versehen von Build 122, in einer Zeile festgehalten:
check("Galerie und Liste sind NICHT gleich verdrahtet",
      _schritte("galerie", "_raster_spalten")
      != _schritte("liste", "_raster_spalten"))
# Und das Gegenstueck: in der Galerie sind hoch/runter nicht tot.
check("in der Galerie blaettern hoch/runter die Leiste",
      _schritte("galerie", "_raster_spalten")[0] == PAGE)

check("beide Seiten fragen ihre eigene Ansicht ab",
      "self.aktuelle_ansicht() if self.page == 1" in quelle
      and "self.aktuelle_ansicht_haupt() if self.page == 0" in quelle)

H.set_screen(1920, 1080)
f = H.make_frontend(page=1)
f.ansicht_setzen("raster")
f.item_i = 0
f.draw()
check("und die Spaltenzahl steht nach dem Zeichnen fest",
      getattr(f, "_raster_spalten", 0) == f.RASTER_HDMI[0],
      str(getattr(f, "_raster_spalten", None)))
# Bis zum ersten Bild darf nichts fehlen - sonst waere der erste
# Tastendruck nach dem Start eine Ausnahme.
f2 = H.make_frontend(page=1)
check("und sie hat schon vor dem ersten Bild einen Wert",
      getattr(f2, "_raster_spalten", None) == 1
      and getattr(f2, "_kat_raster_spalten", None) == 1)

print()
print("Test 7: Schalter, Taste und Menuepunkt")
# GEAENDERT (Build 124): hier stand F9. Das war ein Fehler - F9 ist
# bei MiSTer fuer den Wechsel Konsole/Grafikmodus reserviert, wir
# spielen die Taste selbst ein (enter_console_mode()), und der
# Tastenbelegungs-Assistent lehnt sie ausdruecklich ab. Deshalb wird
# hier BEIDES geprueft: dass F10 die Ansicht schaltet UND dass F9
# wieder frei ist.
check("F10 ist belegt", I.KEYMAP.get(I.KEY_F10) == "ansicht",
      repr(I.KEYMAP.get(I.KEY_F10)))
check("und F9 bleibt MiSTer ueberlassen",
      I.KEYMAP.get(I.KEY_F9) is None, repr(I.KEYMAP.get(I.KEY_F9)))
check("Select+Y ebenfalls",
      I.SELECT_COMBOS.get("music_next") == "ansicht")
check("drei Ansichten", S.ANSICHTEN == ("liste", "raster", "galerie"))
check("unbekannter Dateiinhalt faellt auf Liste zurueck",
      S.ansicht_schreiben("unfug") == "liste")
# Der Menuepunkt muss die Ansicht auch WIRKLICH anbieten - sonst
# findet sie niemand, der keine F9-Taste kennt.
eintraege = M.build_system_menu_items(H.make_frontend(page=0)) \
    if hasattr(M, "build_system_menu_items") else None
check("Menuepunkt existiert im Quelltext",
      '"ansicht", None)' in open(
          os.path.join(_REPO, "frontend", "fe", "menu.py"),
          encoding="utf-8", errors="replace").read())
check("und wird im Frontend auch behandelt",
      'elif kind == "ansicht":' in quelle)
_ = eintraege

print()
print("Test 8: die Taste merkt sich die Ansicht je Kategorie, der")
print("        Menuepunkt setzt die Vorgabe")
H.set_screen(1920, 1080)
f = H.make_frontend(page=1)
S.ansicht_schreiben("liste")
f._ansicht_je_kat = {}
f.ansicht_setzen("raster")                  # wie die Taste
check("die Kategorie steht auf Raster", f.aktuelle_ansicht() == "raster")
check("die Vorgabe auf der Karte bleibt Liste",
      S.ansicht_lesen() == "liste")
f.ansicht_setzen("galerie", merken=True)    # wie der Menuepunkt
check("der Menuepunkt schreibt die Vorgabe",
      S.ansicht_lesen() == "galerie")
check("und raeumt die einzeln gemerkten Ausnahmen ab",
      f._ansicht_je_kat == {})
S.ansicht_schreiben("liste")

print()
print("Test 9: alle sichtbaren Kacheln landen beim Vorauslader,")
print("        nicht nur die letzte")
# BUGFIX (Build 123, Nutzer-Rueckmeldung: "wenn ich mit F9 zum Beispiel
# in Arcade die Ansicht wechsle, laden die Cover erst, wenn ich
# draufgehe").
#
# dringend() rief bis dahin uebergeben([auftrag]) - also "wirf alles
# weg, mach DAS hier". Fuer die Liste richtig, dort ist genau ein
# Cover zu sehen. Im Raster sind es 28, und jede Kachel warf die 27
# davor wieder weg. Uebrig blieb eine.
import fe.prewarm as P                                   # noqa: E402

pw = P.CoverPrewarmer()
pw._proc = object()          # Prozessbetrieb vortaeuschen, nichts starten
pw._thread = object()        # start() soll nichts tun
for i in range(5):
    pw.dringend("/tmp/cover_%d.png" % i, 100, 140)
check("fuenf dringende Auftraege stehen alle in der Liste",
      len(pw._auftraege) == 5, "%d" % len(pw._auftraege))
check("und in der Reihenfolge, in der gezeichnet wurde",
      pw._auftraege[0][0].endswith("cover_0.png")
      and pw._auftraege[-1][0].endswith("cover_4.png"))
pw.dringend("/tmp/cover_2.png", 100, 140)
check("derselbe Auftrag kommt nicht doppelt rein",
      len(pw._auftraege) == 5, "%d" % len(pw._auftraege))
pw.dringend("/tmp/cover_2.png", 200, 280)
check("eine andere Kastengroesse dagegen schon",
      len(pw._auftraege) == 6, "%d" % len(pw._auftraege))
# Die Vorratsliste ist Spekulation - sie darf und soll weichen, sobald
# etwas SICHTBARES ansteht.
pw.uebergeben([("/tmp/vorrat.png", 100, 140)])
check("uebergeben() setzt die Liste komplett neu",
      pw._auftraege == [("/tmp/vorrat.png", 100, 140)])
pw.dringend("/tmp/sichtbar.png", 100, 140)
check("der erste dringende Auftrag wirft den Vorrat weg",
      pw._auftraege == [("/tmp/sichtbar.png", 100, 140)],
      repr(pw._auftraege))
pw.abbrechen()
check("abbrechen() raeumt alles weg", pw._auftraege == [])
pw.uebergeben([("/tmp/v2.png", 100, 140)])
pw.dringend("/tmp/s2.png", 100, 140)
check("und danach faengt das Spiel sauber von vorne an",
      pw._auftraege == [("/tmp/s2.png", 100, 140)], repr(pw._auftraege))
quelle_pw = open(os.path.join(_REPO, "frontend", "fe", "prewarm.py"),
                 encoding="utf-8", errors="replace").read()
check("und dringend() uebergibt nicht mehr einzeln",
      "self.uebergeben([(pfad, bw, bh)])" not in quelle_pw)

print()
print("Test 10: dieselben drei Ansichten auf der HAUPTSEITE (Build 124)")
# Der Aufbau: eine realistische Kategorieliste mit echten
# Systemschluesseln (zu jedem gibt es eine Datei in frontend/sysart),
# damit die Bilder auch wirklich geladen werden koennen.
fm.SYSART_BASE = os.path.join(_REPO, "frontend", "sysart")
KAT = [("Favoriten", "FAVORITES"), ("Arcade", "ARCADE"), ("NES", "NES"),
       ("SNES", "SNES"), ("Game Boy", "GAMEBOY"), ("N64", "N64"),
       ("Mega Drive", "Genesis"), ("Neo Geo", "NEOGEO"),
       ("Atari 2600", "ATARI2600"), ("Computer", "COMPUTER"),
       ("System", "SYSTEM")]


def haupt(breite, hoehe):
    H.set_screen(breite, hoehe)
    f = H.make_frontend(page=0)
    # Der Vorauslader wuerde einen echten Arbeitsprozess starten und
    # einen Teil der Bilder auf "kommt gleich" setzen - dann waere der
    # Pixelvergleich unten von der Laune des Prozesses abhaengig.
    fm.ART.auslagern = None
    f.cats = [(n, {"folders": {}, "items": []}, k) for n, k in KAT]
    f.cat_i = 3
    return f


for breite, hoehe, wie in ((1920, 1080, "HDMI"), (320, 240, "CRT")):
    f = haupt(breite, hoehe)
    for ansicht in S.ANSICHTEN:
        f.ansicht_haupt_setzen(ansicht)
        try:
            f.draw()
            ok, fehler = True, ""
        except Exception as e:                           # noqa: BLE001
            ok, fehler = False, repr(e)
        check("%-4s Hauptseite %-8s zeichnet" % (wie, ansicht), ok, fehler)

print()
print("Test 11: der schnelle Rasterpfad der Hauptseite ist bitgenau")
for breite, hoehe, wie in ((1920, 1080, "HDMI"), (320, 240, "CRT")):
    f = haupt(breite, hoehe)
    f.ansicht_haupt_setzen("raster")
    f.cat_i = 0
    f.draw()
    for _ in range(4):
        f.cat_i += 1
        f.draw()
    schnell = bytes(f.fb.buf)
    f._kat_raster_fast_key = None
    f.fb.mark_full_redraw()
    f.draw()
    n = unterschiede(schnell, bytes(f.fb.buf))
    check("%-4s vier Schritte ueber den schnellen Weg" % wie, n == 0,
          "%d abweichende Bildpunkte" % n)
    for _ in range(3):
        f.cat_i -= 1
        f.draw()
    schnell = bytes(f.fb.buf)
    f._kat_raster_fast_key = None
    f.fb.mark_full_redraw()
    f.draw()
    n = unterschiede(schnell, bytes(f.fb.buf))
    check("%-4s und drei Schritte zurueck" % wie, n == 0,
          "%d abweichende Bildpunkte" % n)

print()
print("Test 12: die Logo-Kastengroesse folgt der Ansicht")
# Dieselbe Falle wie bei den Spiel-Covern: der Schluessel des
# Zwischenspeichers enthaelt die Kastengroesse. Rechnet der
# Vorauslader mit der Liste, waehrend gezeichnet wird im Raster, legt
# er Logos an, die nie jemand abfragt.
f = haupt(1920, 1080)
kaesten = {}
for ansicht in S.ANSICHTEN:
    f.ansicht_haupt_setzen(ansicht)
    kaesten[ansicht] = f._kat_logo_kasten(ansicht)
    gefragt = []
    echt = fm.ART.get_scaled

    def merken(pfad, bw, bh, *a, **kw):
        gefragt.append((bw, bh))
        return echt(pfad, bw, bh, *a, **kw)

    fm.ART.get_scaled = merken
    try:
        f.draw()
    finally:
        fm.ART.get_scaled = echt
    check("%-8s zeichnet in genau dem Kasten, den der Vorauslader kennt"
          % ansicht, kaesten[ansicht] in gefragt,
          "Vorauslader %r, gezeichnet %r"
          % (kaesten[ansicht], sorted(set(gefragt))))
check("und die drei Kaesten sind wirklich verschieden",
      len(set(kaesten.values())) == 3, repr(kaesten))
# Die RUECKGABE von kategorie_logo_auftraege() enthaelt nur, was noch
# fehlt - nach den Zeichenversuchen oben liegt ein Teil schon auf der
# Karte. Geprueft wird deshalb, was die Funktion INSGESAMT anfasst:
# genau das ist die Liste, die sie vor der Verdraengung schuetzt.
angefasst = []
_echt_schuetzen = fm.thumb_cache_schuetzen
fm.thumb_cache_schuetzen = lambda liste: angefasst.extend(liste)
try:
    f.kategorie_logo_auftraege()
finally:
    fm.thumb_cache_schuetzen = _echt_schuetzen
check("kategorie_logo_auftraege() deckt alle drei Ansichten ab",
      len({(a[1], a[2]) for a in angefasst}) == 3,
      repr(sorted({(a[1], a[2]) for a in angefasst})))
check("und jede Kategorie kommt in jeder Groesse genau einmal vor",
      len(angefasst) == 3 * len(KAT), "%d von %d" % (len(angefasst),
                                                     3 * len(KAT)))

print()
print("Test 13: Bedienung und Tasten")
f = haupt(1920, 1080)
f.ansicht_haupt_setzen("raster")
f.draw()
check("die Spaltenzahl steht nach dem Zeichnen fest",
      getattr(f, "_kat_raster_spalten", 0) == f.RASTER_HDMI[0],
      str(getattr(f, "_kat_raster_spalten", None)))
check("der leichte Listenpfad haelt sich raus",
      f._draw_navigate_cats(0) is False)
check("und der Puls-Tick auch",
      f._draw_dynamic_cats(flip=False) == (None, None))
f.ansicht_haupt_setzen("liste")
f.draw()
f.cat_i = 1
f._draw_navigate_cats(0)          # verbraucht _force_full_redraw
f.draw()
f.cat_i = 2
check("in der Liste greift er weiterhin",
      f._draw_navigate_cats(1) is True)
check("F10 statt F9 (F9 gehoert MiSTer)",
      I.KEYMAP.get(I.KEY_F10) == "ansicht"
      and I.KEYMAP.get(I.KEY_F9) is None,
      "F9=%r F10=%r" % (I.KEYMAP.get(I.KEY_F9), I.KEYMAP.get(I.KEY_F10)))
check("eigene Einstellung fuer die Hauptseite",
      S.ANSICHT_HAUPT_FILE != S.ANSICHT_FILE)
quelle_menu = open(os.path.join(_REPO, "frontend", "fe", "menu.py"),
                   encoding="utf-8", errors="replace").read()
check("und ein eigener Menuepunkt", '"ansicht_haupt", None' in quelle_menu)
# GEAENDERT (Build 127): hier stand 'kat_hoch_runter = max(' in quelle.
# Seit beide Seiten durch dieselbe Funktion gehen, gibt es diese Zeile
# nicht mehr - und die Bedeutung wird ohnehin in Test 6 ausgefuehrt
# statt nachgelesen. Uebrig bleibt, was hier wirklich hingehoert: dass
# die Hauptseite ihre EIGENE Spaltenzahl benutzt und nicht die der
# Spieleliste.
check("die Hauptseite hat eine eigene Spaltenzahl",
      "kat_hoch_runter, kat_links_rechts = _schritte(" in quelle
      and '"_kat_raster_spalten")' in quelle)

print()
print("Test 14: die Galerie braucht ZWEI Kastengroessen (Build 125)")
# BUGFIX-TEST. Der Nutzer hat eine Bildschirmaufnahme geschickt: in der
# Galerie waren die Kacheln der Nachbarleiste beim Scrollen schwarz,
# "trotz Miniaturen vorbereiten".
#
# Die Ursache: _art_panel_geometrie() liefert nur EINE Groesse. Die
# Galerie fragt aber zwei an - das grosse Cover und die Miniaturen der
# Leiste. Die Leiste stand damit in KEINER Vorbereitungsliste, in
# keinem Build.
H.set_screen(1920, 1080)
f = H.make_frontend(page=1)
fm.ART.auslagern = None
check("Liste braucht eine Groesse",
      len(f._ansicht_geometrien("liste", erzwingen=True)) == 1)
check("Raster braucht eine Groesse",
      len(f._ansicht_geometrien("raster", erzwingen=True)) == 1)
_gal = f._ansicht_geometrien("galerie", erzwingen=True)
check("Galerie braucht ZWEI", len(_gal) == 2, repr(_gal))

# Und beide muessen genau die sein, die der Zeichenpfad anfragt.
f.ansicht_setzen("galerie")
f.item_i = 3
gefragt = []
echt = fm.ART.get_scaled


def merken2(pfad, bw, bh, *a, **kw):
    gefragt.append((bw, bh))
    return echt(pfad, bw, bh, *a, **kw)


fm.ART.get_scaled = merken2
try:
    f.draw()
finally:
    fm.ART.get_scaled = echt
_vorbereitet = {(g[1], g[2]) for g in _gal}
check("und der Zeichenpfad fragt genau diese beiden an",
      _vorbereitet == set(gefragt),
      "vorbereitet %r, gezeichnet %r"
      % (sorted(_vorbereitet), sorted(set(gefragt))))

print()
print("Test 15: die Leiste blaettert, sie laeuft nicht mit")
for breite, hoehe, wie in ((1920, 1080, "HDMI"), (320, 240, "CRT")):
    H.set_screen(breite, hoehe)
    f = H.make_frontend(page=1)
    fm.ART.auslagern = None
    f.ansicht_setzen("galerie")
    f.item_i = 0
    f.draw()
    stand = [f.scroll]
    for i in range(1, 5):
        f.item_i = i
        f.draw()
        stand.append(f.scroll)
    check("%-4s die Leiste bleibt innerhalb einer Seite stehen" % wie,
          len(set(stand)) == 1, repr(stand))

print()
print("Test 16: die schnellen Pfade der Galerie sind bitgenau")
for breite, hoehe, wie in ((1920, 1080, "HDMI"), (320, 240, "CRT")):
    # ---- Spieleliste ----
    H.set_screen(breite, hoehe)
    f = H.make_frontend(page=1)
    fm.ART.auslagern = None
    f.ansicht_setzen("galerie")
    f.item_i = 0
    f.draw()
    for _ in range(4):
        f.item_i += 1
        f.draw()
    schnell = bytes(f.fb.buf)
    f._galerie_fast_key = None
    f.fb.mark_full_redraw()
    f.draw()
    n = unterschiede(schnell, bytes(f.fb.buf))
    check("%-4s Spieleliste, vier Schritte" % wie, n == 0,
          "%d abweichende Bildpunkte" % n)
    for _ in range(3):
        f.item_i -= 1
        f.draw()
    schnell = bytes(f.fb.buf)
    f._galerie_fast_key = None
    f.fb.mark_full_redraw()
    f.draw()
    n = unterschiede(schnell, bytes(f.fb.buf))
    check("%-4s Spieleliste, drei zurueck" % wie, n == 0,
          "%d abweichende Bildpunkte" % n)

    # ---- Hauptseite ----
    fm.SYSART_BASE = os.path.join(_REPO, "frontend", "sysart")
    f = haupt(breite, hoehe)
    f.ansicht_haupt_setzen("galerie")
    f.cat_i = 0
    f.draw()
    for _ in range(4):
        f.cat_i += 1
        f.draw()
    schnell = bytes(f.fb.buf)
    f._kat_galerie_fast_key = None
    f.fb.mark_full_redraw()
    f.draw()
    n = unterschiede(schnell, bytes(f.fb.buf))
    check("%-4s Hauptseite, vier Schritte" % wie, n == 0,
          "%d abweichende Bildpunkte" % n)

print()
print("Test 17: die Karte ragt nicht mehr in die Leiste")
# Genau diesen Ueberstand hat der Pixelvergleich oben gefunden: das
# Polster um das grosse Cover plus sein Schlagschatten lagen 1*s IN der
# Nachbarleiste. Im vollen Aufbau unsichtbar (die Leiste wird danach
# gezeichnet), auf dem schnellen Pfad 2475 abweichende Bildpunkte.
for breite, hoehe, wie in ((1920, 1080, "HDMI"), (320, 240, "CRT")):
    H.set_screen(breite, hoehe)
    f = H.make_frontend(page=1)
    g = f.galerie_geometrie(f.layout_items(True))
    s_ = g["s"]
    karte_unten = g["oben"] + g["gross_h"] + fm.ART_CARD_PAD * s_ + 3 * s_
    check("%-4s Karte endet ueber der Leiste" % wie,
          karte_unten < g["leiste_y"],
          "Karte bis %d, Leiste ab %d" % (karte_unten, g["leiste_y"]))

print()
print("Test 18: der Nachlade-Thread (Build 125)")
import fe.nachladen as N                                 # noqa: E402

gelesen = []


def _lese_attrappe(pfad, bw, bh):
    gelesen.append((pfad, bw, bh))
    if "fehlt" in pfad:
        return None
    return (bw, bh, b"\x00" * (bw * bh * 4))


lader = N.MiniaturLader(_lese_attrappe)
lader.start()
lader.uebergeben([("/a.art", 4, 4), ("/fehlt.art", 4, 4), ("/b.art", 4, 4)])
import time as _t                                        # noqa: E402
_ende = _t.time() + 5.0
while _t.time() < _ende and len(gelesen) < 3:
    _t.sleep(0.02)
check("der Thread arbeitet die Liste ab", len(gelesen) == 3, repr(gelesen))
_t.sleep(0.1)
fertig = lader.abholen()
check("nur die vorhandenen kommen zurueck", len(fertig) == 2,
      repr([f_[0] for f_ in fertig]))
check("und die fehlende wird gezaehlt", lader.nicht_da == 1)
lader.uebergeben([("/c.art", 4, 4)])
lader.abbrechen()
check("abbrechen() raeumt die Liste weg", lader._auftraege == [])
lader.beenden()
check("beenden() legt den Thread still", lader._thread is None)

# Der Eingang in den RAM-Cache.
fm.ART.scaled = {}
fm.ART.scaled_order = []
fm.ART.scaled_bytes = 0
check("eine nachgeladene Miniatur landet im Cache",
      fm.ART.nachgeladen_eintragen("/a.art", 4, 4, (4, 4, b"\x00" * 64))
      is True)
check("und ein zweites Mal nicht noch einmal",
      fm.ART.nachgeladen_eintragen("/a.art", 4, 4, (4, 4, b"\x00" * 64))
      is False)
check("kaputte Eingabe wird abgewiesen",
      fm.ART.nachgeladen_eintragen("/x.art", 4, 4, None) is False)
check("was schon im RAM liegt, kommt nicht auf die Nachladeliste",
      fm.ART.nur_im_ram_fehlt("/a.art", 4, 4) is False)

quelle_pw = open(os.path.join(_REPO, "frontend", "fe", "prewarm.py"),
                 encoding="utf-8", errors="replace").read()
check("auftraege_bauen() kann die Gegenliste",
      "schon_da=False" in quelle_pw
      and "thumb_cache_has(pfad, bw, bh) != schon_da" in quelle_pw)
check("und das Frontend fuettert den Lader damit",
      "schon_da=True" in quelle and "self.lader.uebergeben(" in quelle)
check("jede Eingabe bricht ihn ab", "self.lader.abbrechen()" in quelle)
check("und der Spielstart raeumt ihn ab",
      quelle.count("self.lader.beenden()") >= 2)

print()
print("Test 19: die Kategorie-Abzeichen kommen VOR dem ersten Blick in")
print("         den Arbeitsspeicher (Build 127)")
# Nutzer mit Bildschirmaufnahme: "das passiert bei jedem Neustart vom
# MiSTer, das nervt, die Icons / Logos muessen schon da sein und nicht
# jedesmal neu aufploppen."
#
# Build 125 hatte den Nachlade-Thread gebaut, aber nur an die
# SPIELELISTE angeschlossen. Die Hauptseite hing weiter allein am
# Vorauslader - und der rechnet nur, was auf der Karte FEHLT. Nach
# einem Neustart liegt alles auf der Karte und nichts im Speicher:
# genau die Luecke, die man als Aufploppen sieht.
H.set_screen(1920, 1080)
f = H.make_frontend(page=0)

for _ansicht in ("liste", "raster", "galerie"):
    f.ansicht_haupt_setzen(_ansicht)
    alle = f.kategorie_logo_alle()
    fehlt = f.kategorie_logo_auftraege()
    kasten = set((a[1], a[2]) for a in alle)
    check("%-8s liefert ueberhaupt Abzeichen" % _ansicht, len(alle) > 0,
          "%d" % len(alle))
    check("%-8s alle in EINER Kastengroesse" % _ansicht, len(kasten) == 1,
          repr(sorted(kasten)))
    # Der Kern: die Gegenliste ist eine OBERMENGE der Fehlliste. Waere
    # sie dieselbe, haette der Lader nach einem Neustart nichts zu tun.
    check("%-8s und enthaelt auch das, was schon auf der Karte liegt"
          % _ansicht, set(fehlt) <= set(alle),
          "%d fehlend, %d gesamt" % (len(fehlt), len(alle)))
    check("%-8s in der Kastengroesse, die auch gezeichnet wird"
          % _ansicht,
          kasten == set([f._kat_logo_kasten(_ansicht)]),
          "%r vs %r" % (sorted(kasten), f._kat_logo_kasten(_ansicht)))

# Und der Anschluss: Start UND Leerlauf muessen den Lader fuettern.
# Beim Start ist es wichtiger - dort laeuft die Startanimation, das ist
# die einzige Zeit, in der das Lesen von der Karte nichts kostet.
_kopf = quelle[:quelle.index("def kategorie_logo_alle")]
check("der Start merkt die Abzeichen beim Lader vor",
      "_logo_nachladen" in _kopf
      and "kategorie_logo_alle()" in _kopf)
check("und faengt dabei jeden Fehler ab - ein Abzeichen darf den "
      "Start nie verhindern",
      "except Exception:" in _kopf[_kopf.index("_logo_nachladen") - 400:
                                   _kopf.index("_logo_nachladen") + 400])
_leer = quelle[quelle.index("def _prewarm_anstossen"):]
_leer = _leer[:_leer.index("if self.page != 1:")]
check("und der Leerlauf der Hauptseite tut dasselbe",
      "kategorie_logo_alle()" in _leer
      and "self.lader.uebergeben(nachladen)" in _leer)
check("beide fragen vorher, was im Speicher wirklich fehlt",
      _kopf.count("nur_im_ram_fehlt") >= 1
      and "nur_im_ram_fehlt" in _leer)

print()
print("Test 20: die Wiederholrate folgt der Ansicht (Build 136)")
# Nutzer-Rueckmeldung: "das nach links und rechts scrollen kann trotzdem
# schneller passieren, wenn ich die Richtung gedrueckt halte."
#
# Es gibt zwei Boeden fuer die Wiederholrate bei gehaltener Taste: den
# normalen (0.08 s) und einen langsamen fuer Seitenspruenge (0.25 s,
# also vier je Sekunde). Der langsame ist richtig, wenn ein Druck eine
# ganze Seite weiterblaettert - mehr kann niemand lesen.
#
# Bis Build 135 galt er FEST fuer links/rechts. Seit Build 127 folgen
# die Richtungstasten aber der Anordnung (Test 6), und im Raster ist
# links/rechts die billigste Bewegung ueberhaupt: eine Kachel weiter,
# zwei neu gezeichnet. Die war damit auf vier Schritte je Sekunde
# gedeckelt.
#
# Die Zuordnung hier muss dieselbe sein wie bei _schritte() in Test 6 -
# es ist dieselbe Frage, einmal fuer die Schrittweite und einmal fuer
# das Tempo.
H.set_screen(1920, 1080)
f20 = H.make_frontend(page=1)
ERWARTET = {
    "liste":   (I.REPEAT_FLOOR_PAGE, I.REPEAT_FLOOR),
    "raster":  (I.REPEAT_FLOOR,      I.REPEAT_FLOOR),
    "galerie": (I.REPEAT_FLOOR,      I.REPEAT_FLOOR_PAGE),
}
for _a, (_lr, _hr) in ERWARTET.items():
    f20.ansicht_setzen(_a)
    f20.draw()
    ist_lr = f20.inp._repeat_floor("left")
    ist_hr = f20.inp._repeat_floor("up")
    check("%-8s links/rechts %.2f s" % (_a, _lr), ist_lr == _lr,
          "ist %.2f" % ist_lr)
    check("%-8s hoch/runter  %.2f s" % (_a, _hr), ist_hr == _hr,
          "ist %.2f" % ist_hr)

# Der Kern der Beschwerde als eigene Aussage.
f20.ansicht_setzen("raster")
f20.draw()
check("im Raster ist links/rechts nicht mehr gedeckelt",
      f20.inp._repeat_floor("left") < I.REPEAT_FLOOR_PAGE,
      "%.2f statt %.2f" % (f20.inp._repeat_floor("left"),
                           I.REPEAT_FLOOR_PAGE))

# Die Hauptseite hat ihre eigene Ansicht und darf nicht die der
# Spieleliste erben.
f21 = H.make_frontend(page=0)
f21.ansicht_haupt_setzen("raster")
f21.draw()
check("die Hauptseite richtet sich nach IHRER Ansicht",
      f21.inp._repeat_floor("left") == I.REPEAT_FLOOR,
      "%.2f" % f21.inp._repeat_floor("left"))

print()
if fails:
    print("FEHLGESCHLAGEN (%d):" % len(fails))
    for f_ in fails:
        print("  -", f_)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
