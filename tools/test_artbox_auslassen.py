#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Die Artbox der Hauptseite wartet, bis der Cursor steht (Build 196).

DIE MESSUNG, DIE DAZU GEFUEHRT HAT

Aus dem Log des Nutzers, achtmal hintereinander bei gehaltener
Richtungstaste im Kategorien-Hauptmenue:

    RUCKLER: 85 ms busy (stream=1 haus=0 zeichnen=82 rest=3
             | davon bg=11 restore=0 rows=4 art=17 flip=50
             | vorige Aktion=down Seite=0)

Erst diese Zeile hat die Frage entschieden, um die es vier Builds lang
ging: rest=3 heisst, es wird nicht gewartet und nicht verwaltet - es
wird gemalt. Die geplante Entkopplung von Eingabe und Zeichnen haette
hier nichts gebracht.

Und die Aufteilung zeigt, dass alle drei grossen Posten EINE Ursache
haben, die Artbox-Spalte rechts:

    bg=11    die Spalte wird freigeraeumt, in einer Python-Schleife
             ueber rund 900 Bildzeilen.
    art=17   das Abzeichen wird neu skaliert und gezeichnet.
    flip=50  und das ist der Preis dafuer: flip_rows() kennt nur
             Zeilen, keine Spalten. Der kopierte Streifen muss deshalb
             alles zwischen den zwei geaenderten Textzeilen (links) und
             der Spalte (rechts) einschliessen.

Die zwei Textzeilen, um die es beim Scrollen geht, kosten 4 ms.

WAS DIESER TEST ABSICHERT

  - dass ein EINZELNER Tastendruck nichts aufschiebt (sonst kaeme das
    Abzeichen auch dort erst 0,15 s spaeter),
  - dass die Entscheidung NICHT an fast_scroll_enabled() haengt - das
    ist eine Abwaegung ueber Bildrisse und hat hier nichts zu suchen,
  - dass der kopierte Streifen dadurch wirklich schrumpft, und zwar
    unter die Schwelle, ab der das Vsync-Warten entfallen darf,
  - dass nach dem Stillstand PIXELGENAU dasselbe Bild steht wie bei
    einem vollen Aufbau,
  - und das mit der Kategorie OHNE Abzeichen. Das ist der Fall, an dem
    es beim Bauen fast schiefgegangen ist: siehe Test 5.

Ausfuehren:
    python3 tools/test_artbox_auslassen.py
"""
import io
import os
import sys

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
sys.path.insert(0, _HIER)

import _harness as H                                     # noqa: E402

fm = H.fm
F = fm.Frontend
NOW = H.NOW

# NEU (Build 218): diese Datei prueft den BANDWEG - sie liest die Hoehe
# des Streifens, den flip_rows() bekommt, und daran haengt ihre ganze
# Aussage ("der Streifen schrumpft, wenn die Artbox aufgeschoben wird").
# Seit Build 218 nehmen die leichten Pfade der Liste Rechtecke statt
# eines Bandes, und dann gibt es keine Bandhoehe mehr zu lesen.
#
# BEWUSST SO und nicht umgeschrieben: der Bandweg ist der Rueckfall
# (Geraet ohne libdragend, Schalter aus, unvollstaendige Deckung) und
# muss weiter funktionieren - bliebe er ungetestet, waere er genau die
# Sorte Pfad, die drei Builds spaeter still kaputt ist. Dass das
# Aufschieben auch auf dem RECHTECK-Weg wirkt, prueft
# tools/test_rechteck_flip.py (Block 13/14).
import os as _os218                                      # noqa: E402
import tempfile as _tf218                                # noqa: E402

import fe.settings as _S218                              # noqa: E402

_AUS218 = _os218.path.join(_tf218.mkdtemp(prefix="artbox_"),
                           "rechteck_flip_aus")
open(_AUS218, "w").close()
_S218.RECHTECK_FLIP_AUS_FLAG = _AUS218
H._zwischenspeicher_leeren()

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


# Der Schalter "Cover sofort" hebt das Aufschieben auf (siehe Test 3).
# Fuer die uebrigen Tests bleibt er aus.
fm.cover_sofort_enabled = lambda: False


class Inp(object):
    def __init__(self, letzte=0.0):
        self._last_repeat_time = letzte


class Lage(object):
    _scroll_serie_aktiv = F._scroll_serie_aktiv
    _artbox_auslassen = F._artbox_auslassen

    def __init__(self, letzte=0.0):
        self.inp = Inp(letzte)


# ---------------------------------------------------------------------------
print("Test 1: nur ein LAUFENDES Scrollen schiebt auf")
# ---------------------------------------------------------------------------
# _last_repeat_time wird in fe/input.py ausschliesslich bei einer echten
# Tastenwiederholung gesetzt, nicht bei jedem Druck ("nur ein
# nachweislich laufender Scrollvorgang", steht dort). Genau darum ist es
# der richtige Messpunkt: _last_input_time waere bei JEDEM Tastendruck
# frisch, und dann kaeme das Abzeichen auch beim einzelnen, bedachten
# Druck 0,15 s zu spaet.
check("ein einzelner Tastendruck schiebt NICHTS auf",
      Lage(letzte=0.0)._scroll_serie_aktiv() is False,
      "dort muss das Abzeichen sofort stehen")
check("eine laufende Wiederholung schon",
      Lage(letzte=NOW[0])._scroll_serie_aktiv() is True)
check("nach dem Loslassen wieder nicht",
      Lage(letzte=NOW[0] - fm.FAST_SCROLL_WINDOW - 0.01)
      ._scroll_serie_aktiv() is False)
check("und ohne Eingabegeraet auch nicht",
      Lage.__new__(Lage)._scroll_serie_aktiv() is False,
      "getattr-Kette, damit kein Testaufbau daran haengenbleibt")

# ---------------------------------------------------------------------------
print()
print("Test 2: die Entscheidung haengt NICHT am Bildriss-Schalter")
# ---------------------------------------------------------------------------
# Das ist der Kern der Bauentscheidung. _scroll_skip_vsync() und
# _vsync_ueberspringen() fragen beide fast_scroll_enabled() - eine
# Abwaegung darueber, ob ein sichtbarer Riss im Bild hingenommen wird.
# Beim Aufschieben kann nichts reissen; es kommt nur ein Bild einen
# Augenblick spaeter. Haengte beides am selben Schalter, bekaeme wer
# Risse scheut auch die Ersparnis nicht - und der Schalter ist eine
# Flaggdatei, steht also bei den meisten gar nicht.
_vorher = fm.fast_scroll_enabled
try:
    fm.fast_scroll_enabled = lambda: False
    check("mit ABGESCHALTETEM 'Schnelles Scrollen' wird trotzdem "
          "aufgeschoben",
          Lage(letzte=NOW[0])._artbox_auslassen() is True,
          "sonst waere der Gewinn an eine Bildriss-Einstellung gekoppelt")
finally:
    fm.fast_scroll_enabled = _vorher

quelle = io.open(os.path.join(_REPO, "frontend", "frontend.py"),
                 encoding="utf-8").read()
_blk = quelle[quelle.index("def _scroll_serie_aktiv("):]
_blk = _blk[:_blk.index("\n    def ", 10)]
# NUR der ausfuehrbare Teil, ohne den Docstring. Beim ersten Anlauf
# meldete dieser Test einen Fehler, den es nicht gab: der Docstring
# ERKLAERT, warum fast_scroll_enabled() hier nichts zu suchen hat, und
# die Textsuche fand diese Erklaerung. Das ist mir beim Bauen der
# letzten vier Builds nun zum vierten Mal passiert, immer gleich - nach
# dem Wort gesucht statt nach der Struktur. Deshalb hier ausdruecklich
# erst schneiden, dann pruefen.
_code = _blk.split('"""')[2] if _blk.count('"""') >= 2 else _blk
check("sie liest _last_repeat_time", "_last_repeat_time" in _code)
check("und NICHT _last_input_time", "_last_input_time" not in _code,
      "das waere bei jedem einzelnen Tastendruck frisch")
check("und ruft den Bildriss-Schalter nicht auf",
      "fast_scroll_enabled" not in _code,
      "im Docstring darf er vorkommen - dort steht, warum nicht")

# ---------------------------------------------------------------------------
print()
print("Test 3: 'Cover sofort' hebt es auf")
# ---------------------------------------------------------------------------
# Gleiche Begruendung wie auf Seite 1 (defer_panel in
# _art_panel_aktualisieren()): wer den Schalter setzt, will die Bilder
# sofort sehen und nimmt den Preis in Kauf.
fm.cover_sofort_enabled = lambda: True
check("mit 'Cover sofort' wird nichts aufgeschoben",
      Lage(letzte=NOW[0])._artbox_auslassen() is False)
fm.cover_sofort_enabled = lambda: False
check("ohne den Schalter schon",
      Lage(letzte=NOW[0])._artbox_auslassen() is True)

# ---------------------------------------------------------------------------
print()
print("Test 3b: der EINZELNE Schalter (Build 197)")
# ---------------------------------------------------------------------------
# Warum ein eigener, wenn "Cover sofort" den Aufschub schon aufhebt: der
# schaltet ZWEI Dinge gleichzeitig um (auf Seite 1 auch das
# Cover-Panel). Wer nachmessen will, ob eine Beobachtung an Build 196
# haengt, braucht einen Schalter, der nur das eine anfasst - sonst ist
# die Messung wertlos. Anlass war die Rueckmeldung "ab und zu ploppte
# jetzt wieder der Login-Prompt auf wenn ich gedrueckt halte und
# scrolle": ohne sauberen Schalter waere nicht entscheidbar, ob das an
# diesem Aufschub liegt.
_ab_vorher = fm.artbox_aufschub_aus
try:
    fm.artbox_aufschub_aus = lambda: True
    check("mit dem Schalter wird nichts aufgeschoben",
          Lage(letzte=NOW[0])._artbox_auslassen() is False,
          "damit steht wieder das Verhalten vor Build 196")
    fm.artbox_aufschub_aus = lambda: False
    check("ohne ihn wieder schon",
          Lage(letzte=NOW[0])._artbox_auslassen() is True)
finally:
    fm.artbox_aufschub_aus = _ab_vorher
check("er faesst das Cover-Panel der Spieleliste NICHT an",
      "artbox_aufschub_aus" not in quelle[quelle.index(
          "def _art_panel_aktualisieren("):][:3000],
      "sonst waere er kein einzelner Schalter mehr")


# ---------------------------------------------------------------------------
print()
print("Test 4: der kopierte Streifen schrumpft unter die Vsync-Schwelle")
# ---------------------------------------------------------------------------
def schritt(fe, serie):
    """Einen Navigationsschritt gehen und den geflippten Streifen
    zurueckgeben."""
    fe.inp._last_repeat_time = NOW[0] if serie else 0.0
    bands = []
    echt = fe.fb.flip_rows

    def fang(y, h, skip_vsync=False):
        bands.append((y, h))
        echt(y, h, skip_vsync=skip_vsync)

    fe.fb.flip_rows = fang
    fe._perf_bg = fe._perf_art = 0
    alt = fe.cat_i
    fe.cat_i = (fe.cat_i + 1) % len(fe.cats)
    try:
        ok = fe._draw_navigate_cats_impl(alt)
    finally:
        fe.fb.flip_rows = echt
    return ok, bands


fe = H.make_frontend(page=0)
fe.draw_page_cats()
_ok, _ohne = schritt(fe, serie=False)
check("der leichte Pfad greift", _ok is True)
_ok, _mit = schritt(fe, serie=True)

_h_ohne = _ohne[0][1] if _ohne else 0
_h_mit = _mit[0][1] if _mit else 0
_schwelle = fe.fb.height * fm.VSYNC_SKIP_MAX_ANTEIL
check("ohne Aufschub reicht der Streifen bis zur Artbox-Spalte",
      _h_ohne > _schwelle, "%d Zeilen, Schwelle %d" % (_h_ohne, _schwelle))
check("mit Aufschub bleibt er bei den zwei Textzeilen",
      0 < _h_mit <= _schwelle,
      "%d statt %d Zeilen" % (_h_mit, _h_ohne))
check("und das ist der eigentliche Gewinn: er darf jetzt ohne "
      "Vsync-Warten kopiert werden",
      _h_mit <= _schwelle < _h_ohne,
      "%d -> %d Zeilen bei Schwelle %d" % (_h_ohne, _h_mit, _schwelle))
check("die teure Arbeit entfaellt dabei ganz",
      fe._perf_bg == 0 and fe._perf_art == 0,
      "bg=%.1f ms art=%.1f ms" % (fe._perf_bg * 1000, fe._perf_art * 1000))
check("der Nachlader wird vorgemerkt",
      getattr(fm.ART, "_deferred_something", False) is True,
      "ohne diesen Vermerk zeichnet er seit Build 104 nicht mehr nach")
check("und zwar mit vollem Aufbau", fe._pgc_fast_key is None,
      "warum, sagt Test 5")

# ---------------------------------------------------------------------------
print()
print("Test 4b: dasselbe auf CRT")
# ---------------------------------------------------------------------------
# 320x240 ist ein anderes Bild, nicht nur ein kleineres: unter KOMPAKT_H
# (400) gibt es den schnellen Seitenaufbau gar nicht, der volle Aufbau
# raeumt also immer alles frei. Der Aufschub muss auch dort greifen und
# darf nichts stehenlassen - der Nutzer spielt auf beidem.
H.set_screen(320, 240)
try:
    fk = H.make_frontend(page=0)
    fk.draw_page_cats()
    _ok, _k_ohne = schritt(fk, serie=False)
    _ok, _k_mit = schritt(fk, serie=True)
    _hk_ohne = _k_ohne[0][1] if _k_ohne else 0
    _hk_mit = _k_mit[0][1] if _k_mit else 0
    check("CRT: der Streifen schrumpft auch dort",
          0 < _hk_mit < _hk_ohne,
          "%d statt %d Zeilen von %d" % (_hk_mit, _hk_ohne, fk.fb.height))

    ka = H.make_frontend(page=0)
    ka.draw_page_cats()
    ka.inp._last_repeat_time = NOW[0]
    ka.cat_i = 1
    ka._draw_navigate_cats_impl(0)
    ka.inp._last_repeat_time = 0.0
    ka.draw_page_cats()
    kb = H.make_frontend(page=0)
    kb.cat_i = 1
    kb.fb.full_redraw_gen += 1
    kb.draw_page_cats()
    _dk = sum(1 for x, y in zip(bytes(ka.fb.buf), bytes(kb.fb.buf)) if x != y)
    check("CRT: nach dem Stillstand pixelgleich zum vollen Aufbau",
          _dk == 0, "%d abweichende Bytes" % _dk)
finally:
    H.set_screen(1920, 1080)

# ---------------------------------------------------------------------------
print()
print("Test 5: DER FALL, AN DEM ES FAST SCHIEFGEGANGEN IST")
# ---------------------------------------------------------------------------
# Der schnelle Weg von draw_page_cats() raeumt die Artbox-Spalte NICHT
# frei. Er darf das, weil seit Build 99 alle Abzeichen exakt 320x420
# gross sind und das neue das alte deshalb vollstaendig abdeckt. Genau
# dann nicht, wenn die naechste Kategorie GAR KEIN Abzeichen hat: dann
# kommt der Platzhalter, der schmaler ist als die Karte darunter, und
# der linke Rand der alten Karte samt Schatten bliebe stehen.
#
# Bisher konnte das nicht passieren, weil das _bg_fill() im leichten
# Pfad die Spalte bei JEDEM Schritt freigeraeumt hat. Wer es aufschiebt,
# muss also auch dafuer sorgen, dass danach voll aufgebaut wird - sonst
# ist der Preis fuer 63 gesparte Millisekunden ein Kartenrand, der
# stehenbleibt.
#
# Gemessen ohne den Vermerk: 58131 abweichende Bytes, also rund 14500
# Bildpunkte alter Karte und alten Schattens. Dieser Test laesst den
# Vermerk absichtlich weg und verlangt, dass es dann WEH TUT - ein Test,
# der auch ohne die Reparatur gruen waere, sichert nichts ab.
ABZ = (304, 399, bytes(bytearray([90, 40, 20, 255]) * (304 * 399)))
_get_scaled = fm.ART.get_scaled
fm.ART.get_scaled = lambda pfad, w, h: (ABZ if "WOT" in pfad else None)
try:
    def nach_stillstand(vermerk_behalten):
        f = H.make_frontend(page=0)
        f.cat_i = 0
        f.draw_page_cats()                      # Kategorie 0: mit Abzeichen
        if f._artbox_karte is None:
            return None                         # Aufbau hat keine Karte gelegt
        f.inp._last_repeat_time = NOW[0]        # Taste wird gehalten
        merk = f._pgc_fast_key
        f.cat_i = 1                             # Kategorie 1: OHNE Abzeichen
        f._draw_navigate_cats_impl(0)
        if not vermerk_behalten:
            f._pgc_fast_key = merk              # Build 196 aushebeln
        f.inp._last_repeat_time = 0.0           # losgelassen
        f.draw_page_cats()                      # das macht der Nachlader
        return bytes(f.fb.buf)

    _sauber = H.make_frontend(page=0)
    _sauber.cat_i = 1
    _sauber.fb.full_redraw_gen += 1             # erzwingt vollen Aufbau
    _sauber.draw_page_cats()
    _soll = bytes(_sauber.fb.buf)

    _mit_v = nach_stillstand(True)
    _ohne_v = nach_stillstand(False)
    check("der Aufbau legt ueberhaupt eine Karte", _mit_v is not None,
          "sonst prueft dieser Test nichts")
    if _mit_v is not None:
        _d_mit = sum(1 for a, b in zip(_mit_v, _soll) if a != b)
        _d_ohne = sum(1 for a, b in zip(_ohne_v, _soll) if a != b)
        check("nach dem Stillstand steht PIXELGENAU das Bild eines "
              "vollen Aufbaus", _d_mit == 0,
              "%d abweichende Bytes" % _d_mit)
        check("und ohne den Vermerk waere ein Kartenrand stehengeblieben",
              _d_ohne > 1000,
              "%d abweichende Bytes - waere das hier klein, wuerde "
              "dieser Test nichts absichern" % _d_ohne)
finally:
    fm.ART.get_scaled = _get_scaled

# ---------------------------------------------------------------------------
print()
print("Test 6: auch ohne Abzeichen-Datei stimmt das Bild")
# ---------------------------------------------------------------------------
# Derselbe Vergleich im Normalfall dieses Pruefstands: hier liegen gar
# keine .art-Dateien, es laeuft also durchgehend der Platzhalter-Zweig.
a = H.make_frontend(page=0)
a.draw_page_cats()
a.inp._last_repeat_time = NOW[0]
a.cat_i = 1
a._draw_navigate_cats_impl(0)
a.inp._last_repeat_time = 0.0
a.draw_page_cats()

b = H.make_frontend(page=0)
b.cat_i = 1
b.fb.full_redraw_gen += 1
b.draw_page_cats()
_d = sum(1 for x, y in zip(bytes(a.fb.buf), bytes(b.fb.buf)) if x != y)
check("pixelgleich zum vollen Aufbau", _d == 0, "%d abweichende Bytes" % _d)

# ---------------------------------------------------------------------------
print()
print("Test 7: die Messung steht im Quelltext")
# ---------------------------------------------------------------------------
check("die Log-Zeile ist festgehalten",
      "zeichnen=82" in quelle and "flip=50" in quelle)
check("und die Einsicht, die sie gebracht hat",
      "kosten 4 ms" in quelle,
      "die zwei Textzeilen gegen die 78 ms fuer das Bild daneben")
check("Seite 1 wird als Vorbild genannt",
      "_art_panel_aktualisieren" in quelle)

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
