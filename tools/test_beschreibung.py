#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft die Spielbeschreibungen aus der fremden Datenbank (Build 139).

Der Nutzer wollte in der Galerie rechts neben dem Cover mehr sehen -
urspruenglich ein Bildschirmfoto, "ohne dass irgendetwas vorbereitet
oder umgerechnet werden muss". Beim Durchsehen der Ordner unter
/media/fat/docs kam etwas Besseres heraus: neben gameinfo.tsv liegt
dort je Sprache eine synopsis_<xx>.tsv mit einer Beschreibung pro
Spiel. Gemessen an der SNES-Datei des Nutzers: 1785 von 1802
Schluesseln haben einen Text (99%), Einlesen 4 ms, 1,3 MB im Speicher.

Das Frontend fuehrt Deutsch und Englisch - nur diese beiden Dateien
werden gelesen (Nutzerentscheidung).

Geprueft wird:
  1. Finden - exakt und ueber den unscharfen Namensabgleich,
  2. Sprache - Deutsch bevorzugt, Englisch fuellt Luecken; eine
     englische Oberflaeche bekommt NIE deutschen Text,
  3. Schalter "fremde Quellen" gilt auch hier,
  4. waehrend des Scrollens wird die 1,3-MB-Datei NICHT eingelesen,
  5. der Speicher laeuft nicht voll (hoechstens zwei Systemdateien),
  6. die Galerie zeichnet den Text wirklich - und die Liste nicht
     (dort haengt die Cache-Schluesselgroesse der Miniaturen dran).

Ausfuehren:
    python3 tools/test_beschreibung.py
"""
import os
import shutil
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)

import _harness as H                                    # noqa: E402

sys.path.insert(0, os.path.join(_REPO, "frontend"))
import fe.art as A                                      # noqa: E402
import fe.settings as S                                 # noqa: E402
import fe.translations as T                             # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


DE = ("Super Mario World fuehrt Mario und Luigi ins Dinosaurierland, wo sie "
      "gemeinsam mit Yoshi gegen Bowser und die Koopalinge antreten. Das "
      "Spiel bietet 96 Ausgaenge und zahlreiche Geheimwege.")
EN = ("Super Mario World takes Mario and Luigi to Dinosaur Land, where they "
      "team up with Yoshi against Bowser and the Koopalings.")
NUR_EN = "Only an English text exists for this one."

tmp = tempfile.mkdtemp(prefix="dragend_synopsis_")
_alt = (A.DOCS_BASE, A.FREMD_ZUSATZ_WURZELN, S.FREMDQUELLEN_AUS_FLAG,
        T.CURRENT_LANG)
try:
    docs = os.path.join(tmp, "docs")
    for sys_ in ("SNES", "NES"):
        os.makedirs(os.path.join(docs, sys_, "Artwork"))
    art = os.path.join(docs, "SNES", "Artwork")
    with open(os.path.join(art, "synopsis_de.tsv"), "w",
              encoding="utf-8") as fh:
        fh.write("#key\tsynopsis\n")
        fh.write("Super Mario World (USA)\t%s\n" % DE)
        fh.write("Nur Englisch (USA)\t\n")          # leere Zelle = Luecke
    with open(os.path.join(art, "synopsis_en.tsv"), "w",
              encoding="utf-8") as fh:
        fh.write("#key\tsynopsis\n")
        fh.write("Super Mario World (USA)\t%s\n" % EN)
        fh.write("Nur Englisch (USA)\t%s\n" % NUR_EN)
    # Eine Sprache, die wir bewusst NICHT lesen.
    with open(os.path.join(art, "synopsis_fr.tsv"), "w",
              encoding="utf-8") as fh:
        fh.write("#key\tsynopsis\n")
        fh.write("Super Mario World (USA)\tUn texte francais.\n")
    # Zweites System, damit die Verdraengung etwas zu verdraengen hat.
    with open(os.path.join(docs, "NES", "Artwork", "synopsis_de.tsv"), "w",
              encoding="utf-8") as fh:
        fh.write("#key\tsynopsis\n")
        fh.write("Super Mario Bros. (World)\tEin NES-Text.\n")

    A.DOCS_BASE = docs
    A.FREMD_ZUSATZ_WURZELN = ()
    S.FREMDQUELLEN_AUS_FLAG = os.path.join(tmp, "fremdquellen_aus")
    A.docs_caches_leeren()
    H._zwischenspeicher_leeren()
    A.ART._defer_uncached = False

    print("Test 1: finden")
    check("exakter Name",
          A.docs_synopsis("SNES", "Super Mario World (USA)", "de") == DE)
    check("anders benanntes ROM (unscharfer Abgleich)",
          A.docs_synopsis("SNES", "Super Mario World (E) [!]", "de") == DE,
          "GoodTools-Schreibweise")
    check("was es nicht gibt, gibt es nicht",
          A.docs_synopsis("SNES", "Gibt es gar nicht", "de") == "")
    check("ohne System oder Namen kein Absturz",
          A.docs_synopsis(None, "x", "de") == ""
          and A.docs_synopsis("SNES", "", "de") == "")

    print()
    print("Test 2: Sprache")
    check("Deutsch wird bevorzugt",
          A.docs_synopsis("SNES", "Super Mario World (USA)", "de") == DE)
    check("Englisch bleibt Englisch",
          A.docs_synopsis("SNES", "Super Mario World (USA)", "en") == EN)
    check("eine Luecke im Deutschen fuellt das Englische",
          A.docs_synopsis("SNES", "Nur Englisch (USA)", "de") == NUR_EN)
    # Der umgekehrte Weg waere ein deutscher Absatz in einer
    # englischen Oberflaeche - genau das soll nicht passieren.
    with open(os.path.join(art, "synopsis_de.tsv"), "a",
              encoding="utf-8") as fh:
        fh.write("Nur Deutsch (USA)\tEin deutscher Text.\n")
    A.docs_caches_leeren()
    check("aber Englisch faellt NIE auf Deutsch zurueck",
          A.docs_synopsis("SNES", "Nur Deutsch (USA)", "en") == "")
    # Das Frontend fragt nur "de" oder "en" - kaeme doch einmal etwas
    # anderes an, gilt Englisch, und die franzoesische Datei bleibt
    # ungelesen (sie steht nicht in DOCS_SPRACHEN).
    check("eine fremde Sprache landet bei Englisch",
          A.docs_synopsis("SNES", "Super Mario World (USA)", "fr") == EN)
    check("die franzoesische Datei wird nie eingelesen",
          not any(spr == "fr" for _sys, spr in A._docs_syn_cache))

    print()
    print("Test 3: der Schalter 'fremde Quellen' gilt auch hier")
    open(S.FREMDQUELLEN_AUS_FLAG, "w").close()
    H._zwischenspeicher_leeren()
    # fe/art.py merkt sich den Schalter einmal je Sitzung (_fremd_an) -
    # das Menue raeumt ihn beim Umschalten mit weg (siehe den
    # "fremdquellen"-Zweig in frontend.py), also hier genauso.
    A.docs_caches_leeren()
    check("aus heisst aus",
          A.docs_synopsis("SNES", "Super Mario World (USA)", "de") == "")
    os.remove(S.FREMDQUELLEN_AUS_FLAG)
    H._zwischenspeicher_leeren()
    A.docs_caches_leeren()
    check("und wieder an heisst wieder an",
          A.docs_synopsis("SNES", "Super Mario World (USA)", "de") == DE)

    print()
    print("Test 4: waehrend des Scrollens wird nicht von der Karte gelesen")
    A.docs_caches_leeren()
    A.ART._defer_uncached = True
    A.ART._deferred_something = False
    leer = A.docs_synopsis("SNES", "Super Mario World (USA)", "de")
    check("es kommt kein Text", leer == "")
    check("aber der Nachlader wird geweckt",
          A.ART._deferred_something is True)
    A.ART._defer_uncached = False
    check("im Stillstand ist er dann da",
          A.docs_synopsis("SNES", "Super Mario World (USA)", "de") == DE)

    print()
    print("Test 5: hoechstens zwei Systemdateien im Speicher")
    # Eine Datei ist 1,3 MB gross - wer durch zwanzig Systeme blaettert,
    # haette sonst 26 MB Text im Speicher, den niemand mehr anschaut.
    A.docs_caches_leeren()
    A.docs_synopsis("SNES", "Super Mario World (USA)", "de")   # de + nichts
    A.docs_synopsis("SNES", "Nur Deutsch (USA)", "en")         # + en
    A.docs_synopsis("NES", "Super Mario Bros. (World)", "de")  # + NES/de
    check("nicht mehr als %d Tabellen gehalten" % A.DOCS_SYNOPSIS_MAX,
          len(A._docs_syn_cache) <= A.DOCS_SYNOPSIS_MAX,
          "%d" % len(A._docs_syn_cache))
    check("und die zuletzt gebrauchte ist noch da",
          ("NES", "de") in A._docs_syn_cache)
    check("Buchfuehrung und Inhalt bleiben gleich lang",
          len(A._docs_syn_order) == len(A._docs_syn_cache),
          "%d / %d" % (len(A._docs_syn_order), len(A._docs_syn_cache)))

    print()
    print("Test 6: die Galerie zeichnet den Text, die Liste nicht")
    A.docs_caches_leeren()
    T.CURRENT_LANG = "de"
    H.set_screen(1920, 1080)
    f = H.make_frontend(page=1, titles=["Super Mario World (USA)",
                                        "Nur Deutsch (USA)",
                                        "Gibt es gar nicht"])
    A.ART._defer_uncached = False

    def _rechte_spalte(f):
        """Was rechts neben dem Cover steht, als Bytes."""
        fb = f.fb
        has_art = f.hat_artspalte(f._display_items(), f.cats[f.cat_i][2])
        L = f.layout_items(has_art)
        geo = f.galerie_geometrie(L)
        return bytes(fb.buf[geo["oben"] * fb.stride:
                            geo["leiste_y"] * fb.stride])

    f.ansicht_setzen("galerie")
    f.item_i = 2                      # Spiel OHNE Beschreibung
    f._force_full_redraw = True
    f.draw()
    ohne = _rechte_spalte(f)
    f.item_i = 0                      # Spiel MIT Beschreibung
    f._force_full_redraw = True
    f.draw()
    mit = _rechte_spalte(f)
    check("mit Beschreibung sieht die Spalte anders aus als ohne",
          mit != ohne)

    # Gegenprobe: ohne die Datenbank muss dasselbe Spiel genauso
    # aussehen wie eines ohne Text - sonst hat der Test oben nur den
    # unterschiedlichen Titel gesehen.
    _basis = A.DOCS_BASE
    A.DOCS_BASE = os.path.join(tmp, "gibtsnicht")
    A.docs_caches_leeren()
    f.item_i = 0
    f._force_full_redraw = True
    f.draw()
    ohne_db = _rechte_spalte(f)
    A.DOCS_BASE = _basis
    A.docs_caches_leeren()
    check("ohne Datenbank bleibt die Spalte wie frueher",
          ohne_db != mit)

    # Die Liste darf NICHT betroffen sein: die Hoehe ihrer Boxart-
    # Spalte geht ueber cover_box_size() in den Schluessel des
    # Miniatur-Caches ein. Beim Nutzer haengen daran 28.517 Miniaturen.
    f.ansicht_setzen("liste")
    f.item_i = 0
    kasten_mit = f.cover_box_size(500, 900, "SNES",
                                  f._display_items()[0], 3)
    A.DOCS_BASE = os.path.join(tmp, "gibtsnicht")
    A.docs_caches_leeren()
    kasten_ohne = f.cover_box_size(500, 900, "SNES",
                                   f._display_items()[0], 3)
    A.DOCS_BASE = _basis
    A.docs_caches_leeren()
    check("die Miniatur-Kastengroesse aendert sich NICHT",
          kasten_mit == kasten_ohne,
          "%r vs %r" % (kasten_mit, kasten_ohne))

    print()
    print("Test 7: ein gekappter Text ist als gekappt zu erkennen")
    # _wrap() haengt seine Tilde nur an, wenn die letzte ZEILE zu lang
    # war - bricht es wegen max_lines mittendrin ab, endet der Text
    # stillschweigend auf einem beliebigen Wort. Bei einer Datenzeile
    # egal, bei einem Absatz nicht: man haelt ihn fuer vollstaendig.
    roh = f._wrap(DE, 40, max_lines=3)
    check("_wrap() selbst markiert das nicht", not roh[-1].endswith("~"),
          roh[-1])
    # Der Zeichenweg tut es. Geprueft wird er ueber die Pixel: mit
    # wenig Platz muss die Spalte anders aussehen als mit viel.
    gezeichnet = []
    _echt_text = f.fb.text
    f.fb.text = lambda x, y, txt, sk, *a, **k: (
        gezeichnet.append(txt), _echt_text(x, y, txt, sk, *a, **k))[1]
    try:
        f._beschreibung_zeichnen(100, 100, 100 + 3 * 11 * 2, 40 * 8 * 2,
                                 ("Super Mario World (USA)", "game", None),
                                 "SNES", 3)
    finally:
        f.fb.text = _echt_text
    check("gezeichnet wurde ueberhaupt etwas", bool(gezeichnet),
          "%d Zeilen" % len(gezeichnet))
    check("und die letzte Zeile ist als gekappt markiert",
          bool(gezeichnet) and gezeichnet[-1].endswith("~"),
          gezeichnet[-1] if gezeichnet else "-")
    check("keine gezeichnete Zeile ist zu lang",
          all(len(z) <= 40 for z in gezeichnet),
          "max %d" % (max(len(z) for z in gezeichnet) if gezeichnet else 0))

finally:
    A.DOCS_BASE, A.FREMD_ZUSATZ_WURZELN = _alt[0], _alt[1]
    S.FREMDQUELLEN_AUS_FLAG = _alt[2]
    T.CURRENT_LANG = _alt[3]
    A.ART._defer_uncached = False
    A.docs_caches_leeren()
    H._zwischenspeicher_leeren()
    shutil.rmtree(tmp, ignore_errors=True)

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Tests bestanden.")
