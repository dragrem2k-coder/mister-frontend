#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cover, Bildschirmfoto, Titelbild - und R2 dazwischen (Build 294).

WORUM ES GEHT

NUTZERWUNSCH: "mister update_all stellt ja in denn settings unter
punkt 6 extra content, dann punkt 3. game artwork dbs dort die
jeweiligen boxarts, screenshots, title screens zur verfuegung ... hast
du eine gute idee zusaetzlich zu denn boxarts die wir eh schon
verwenden die anderen beiden noch mit ins frontend in denn ansichten
mit einzubinden?" - und zur Taste: "aktuell nutzen wir ja L2 und r2 um
spiele zu Favoriten hinzuzufuegen, koennten wir dann r2 nutzen um die
Bilder durchzuwechseln? Wenn sie vorhanden sind? Mit kleiner Info das
wenn sie vorhanden sind man sie mit r2 durchwechseln kann?"

DIE ORDNERNAMEN SIND GEMESSEN, NICHT GERATEN. Ich hatte nach der
libretro-Konvention "Named_Snaps"/"Named_Titles" vermutet und vor dem
Bauen um ein ls gebeten. Auf seinem Geraet steht:

    /media/fat/docs/SNES/    -> Artwork  Manuals  README.md
                                Screenshots  Titles
    /media/fat/docs/Genesis/ -> Artwork  Screenshots  Titles

Also "Screenshots" und "Titles". Dieser Test baut GENAU DIESE
Ordnerstruktur in einem Testverzeichnis nach - nicht die, die ich
vermutet hatte.

DREI DINGE, DIE HIER ABGESICHERT WERDEN, und jedes davon ist eine
Stelle, an der ich mich beim Bauen hätte vertun können (und an einer
habe ich es):

1. EIN BILDSCHIRMFOTO DARF NIE AN DER STELLE EINER VERPACKUNG LANDEN.
   Das steht seit Build 115 im Quelltext und ist der Grund, warum die
   Named_*-Ordner damals ausgeschlossen wurden. Je Bildart ein
   EIGENER Index - stuenden sie in einem, gewaenne der erste Fund, und
   welcher das ist, haengt an der Ordnerreihenfolge.
2. R2 WAR NUR EIN ZWILLING VON L2. Beide hiessen "favorite". R2
   freizugeben kostet nichts - aber BEIDE Zeilen muessen wandern, die
   fuer den Knopf (BTN_TR2) und die fuer den Analogtrigger (AXIS_R2),
   sonst verhaelt sich ein Xbox-Pad anders als ein Pro Controller.
3. IM ZEICHENWEG DARF KEIN VERZEICHNIS GELESEN WERDEN. Ein Durchlauf
   kostet auf dem Geraet rund 167 ms; zwei davon beim Betreten jedes
   Systems waeren der Fehler aus Build 107 an neuer Stelle.

Ausfuehren:
    python3 tools/test_bildarten.py
"""
import os
import shutil
import sys
import tempfile

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
sys.path.insert(0, _HIER)
sys.path.insert(0, os.path.join(_REPO, "frontend"))

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


import fe.art as A                                        # noqa: E402

FE_PY = os.path.join(_REPO, "frontend", "frontend.py")
INP_PY = os.path.join(_REPO, "frontend", "fe", "input.py")
fe_src = open(FE_PY, encoding="utf-8").read()
inp_src = open(INP_PY, encoding="utf-8").read()


def nur_code(quelle):
    """Dieselbe Datei ohne Kommentarzeilen.

    ZUM DRITTEN MAL IN DIESEM PROJEKT, und jedes Mal hat es mich eine
    rote Zeile gekostet: eine Pruefung, die nach einem Begriff sucht,
    findet ihn auch in der ERKLAERUNG daneben.

    - test_anleitung: ein Wort, das auch im Kommentar stand
    - test_startweg (Build 291): "time.sleep" im Kommentar der
      Konstanten unter der Funktion
    - hier (Build 294): ich habe im Kommentar aufgeschrieben, was
      VORHER dastand ('BTN_TR2: "favorite"') und was ein falscher
      Griff gewesen waere ("ART.docs_bildart") - und beides dann
      gefunden.

    Der Kommentar ist richtig und soll stehenbleiben; er erklaert
    genau das, was die Pruefung sichert. Also muss die Pruefung den
    Code lesen und nicht die Prosa darueber."""
    return "\n".join(z for z in quelle.split("\n")
                     if not z.lstrip().startswith("#"))


fe_code = nur_code(fe_src)
inp_code = nur_code(inp_src)

print(__doc__.strip().split("\n")[0])
print()

# ---------------------------------------------------------------- 1
print("Test 1: die Ordner, die wirklich auf dem Geraet stehen")

check("die drei Arten sind benannt",
      A.DOCS_BILDARTEN == ("boxart", "snap", "titel"),
      str(A.DOCS_BILDARTEN))
check("'Screenshots' steht in der Snap-Liste",
      "Screenshots" in A.DOCS_UNTERORDNER_JE_ART["snap"],
      str(A.DOCS_UNTERORDNER_JE_ART["snap"]))
check("'Titles' steht in der Titel-Liste",
      "Titles" in A.DOCS_UNTERORDNER_JE_ART["titel"],
      str(A.DOCS_UNTERORDNER_JE_ART["titel"]))
# Die libretro-Namen bleiben trotzdem drin - sie kosten einen
# fehlschlagenden Systemaufruf und helfen jedem, der seine Bilder
# aus jener Welt mitgebracht hat.
check("die libretro-Namen sind zusaetzlich dabei",
      "Named_Snaps" in A.DOCS_UNTERORDNER_JE_ART["snap"]
      and "Named_Titles" in A.DOCS_UNTERORDNER_JE_ART["titel"])
# KEINE KOPIE fuer boxart: zwei Listen, die dasselbe bedeuten, gehen
# irgendwann auseinander, und dann sucht der Zeichenweg woanders als
# der Vorauslader.
check("boxart benutzt DIESELBE Liste, nicht eine Kopie",
      A.DOCS_UNTERORDNER_JE_ART["boxart"] is A.DOCS_UNTERORDNER)

print()

# ---------------------------------------------------------------- 2
print("Test 2: gefunden wird in einer echten Ordnerstruktur")

tmp = tempfile.mkdtemp(prefix="dragend_bildarten_")
_echt_base = A.DOCS_BASE
try:
    # Genau die Struktur von oben. Genesis hat KEINE Manuals - und
    # genau diese Unregelmaessigkeit stand in seinem ls.
    for sysname, unter in (("SNES", ("Artwork", "Manuals",
                                     "Screenshots", "Titles")),
                           ("Genesis", ("Artwork", "Screenshots",
                                        "Titles"))):
        for u in unter:
            os.makedirs(os.path.join(tmp, sysname, u))
    def _legen(sysname, unter, name):
        p = os.path.join(tmp, sysname, unter, name)
        with open(p, "wb") as fh:
            fh.write(b"x")
        return p

    p_box = _legen("SNES", "Artwork", "Super Mario World (USA).png")
    p_snap = _legen("SNES", "Screenshots", "Super Mario World (USA).png")
    p_tit = _legen("SNES", "Titles", "Super Mario World (USA).png")
    _legen("SNES", "Artwork", "Nur Cover (USA).png")
    # Nur ein Bildschirmfoto, kein Cover - der Fall, den die fremde
    # Datenbank durchaus hat.
    _legen("Genesis", "Screenshots", "Nur Foto (USA).png")

    A.DOCS_BASE = tmp
    A._docs_ordner_cache = None
    A._docs_index_cache.clear()

    check("das Cover wird gefunden",
          A.docs_bildart("SNES", "Super Mario World (USA)",
                         "boxart") == p_box)
    check("das Bildschirmfoto auch",
          A.docs_bildart("SNES", "Super Mario World (USA)",
                         "snap") == p_snap)
    check("und das Titelbild",
          A.docs_bildart("SNES", "Super Mario World (USA)",
                         "titel") == p_tit)
    # DAS IST DIE WICHTIGSTE ZEILE DIESES TESTS: die Pfade muessen
    # VERSCHIEDEN sein. Waeren Cover und Foto in einem Index, kaeme
    # hier dreimal dasselbe - und damit ein Bildschirmfoto an der
    # Stelle einer Verpackung.
    check("und zwar drei VERSCHIEDENE Dateien",
          len({p_box, p_snap, p_tit}) == 3)
    check("docs_cover() liefert weiterhin das Cover",
          A.docs_cover("SNES", "Super Mario World (USA)") == p_box,
          "die bestehende Suche bleibt unberuehrt")

    check("alle drei Arten werden gemeldet",
          A.docs_bildarten("SNES", "Super Mario World (USA)")
          == ("boxart", "snap", "titel"))
    check("bei nur einem Cover nur eine",
          A.docs_bildarten("SNES", "Nur Cover (USA)") == ("boxart",))
    check("bei nur einem Foto nur das Foto",
          A.docs_bildarten("Genesis", "Nur Foto (USA)") == ("snap",))
    check("fuer ein unbekanntes Spiel gar nichts",
          A.docs_bildarten("SNES", "Gibt Es Nicht (USA)") == ())

    # Der unscharfe Vergleich muss auch fuer die neuen Arten gelten -
    # die Datenbank ist No-Intro benannt, die ROMs des Nutzers sind es
    # nicht zwangslaeufig (Build 117).
    _legen("SNES", "Screenshots", "Zelda (USA) (Rev 1).png")
    A._docs_index_cache.clear()
    check("der unscharfe Vergleich gilt auch fuer Fotos",
          A.docs_bildart("SNES", "Zelda (U) [!]", "snap") is not None,
          "sonst waere die halbe Datenbank unerreichbar")

    print()

    # ------------------------------------------------------------ 3
    print("Test 3: je Art ein eigener Schluessel im Zwischenspeicher")

    A._docs_index_cache.clear()
    A.docs_bildart("SNES", "Super Mario World (USA)", "boxart")
    check("boxart liegt unter dem nackten Systemschluessel",
          "SNES" in A._docs_index_cache,
          "sonst waeren alle bestehenden Eintraege und die Tests, "
          "die sie zaehlen, auf einen Schlag ungueltig")
    A.docs_bildart("SNES", "Super Mario World (USA)", "snap")
    check("snap unter einem eigenen Paar",
          ("SNES", "snap") in A._docs_index_cache)
    check("_docs_index_fertig() rechnet denselben Schluessel",
          A._docs_index_fertig("SNES", "boxart")
          and A._docs_index_fertig("SNES", "snap")
          and not A._docs_index_fertig("SNES", "titel"),
          "eine zweite Schluesselrechnung waere ein Warmlauf, "
          "der nie fertig wird")

    print()

    # ------------------------------------------------------------ 4
    print("Test 4: im Zeichenweg wird KEIN Verzeichnis gelesen")

    # nur_fertig=True muss "weiss ich noch nicht" sagen, solange ein
    # Index fehlt - und darf ihn NICHT bauen. Gemessen wird das, indem
    # os.listdir gezaehlt wird: eine Behauptung ueber Kosten, die man
    # zaehlen kann, ist besser als eine ueber Zeiten, die man misst.
    A._docs_index_cache.clear()
    gezaehlt = [0]
    _echt_listdir = A.os.listdir

    def _zaehl_listdir(p):
        gezaehlt[0] += 1
        return _echt_listdir(p)

    A.os.listdir = _zaehl_listdir
    try:
        offen = A.docs_bildarten("SNES", "Super Mario World (USA)",
                                 nur_fertig=True)
        check("ohne fertige Indizes kommt None, nicht ()", offen is None,
              "None heisst 'weiss ich noch nicht', () heisst "
              "'gibt es nicht' - das ist nicht dasselbe")
        check("und es wurde kein Verzeichnis gelesen", gezaehlt[0] == 0,
              "%d x os.listdir - auf dem Geraet rund 167 ms je Stueck"
              % gezaehlt[0])
        # Jetzt der Warmlauf, so wie ihn das Frontend im Ruhemoment
        # aufruft: EIN Stueck Arbeit je Aufruf.
        A.index_warmlaufen(["SNES"], hoechstens=1)
        nach_warm = gezaehlt[0]
        check("der Warmlauf liest die Verzeichnisse", nach_warm > 0,
              "%d x" % nach_warm)
        # GEAENDERT IN BUILD 295. Hier stand "und baut alle drei
        # Arten" nach EINEM Aufruf - und genau das war der Fehler, den
        # der Nutzer gemeldet hat ("klemmt oder lagt ein wenig"): drei
        # Verzeichnisdurchlaeufe in einem Durchgang sind auf dem Geraet
        # eine halbe Sekunde, und ein begonnener Durchgang laeuft
        # durch. Der erste baut jetzt nur das COVER, denn nur das haelt
        # den Zeichenweg auf.
        check("der erste Durchgang baut das Cover",
              A._docs_index_fertig("SNES", "boxart"))
        check("und NICHT gleich die Extras mit",
              not A._docs_index_fertig("SNES", "snap")
              and not A._docs_index_fertig("SNES", "titel"),
              "die haelt nur der Vermerk 'R2 1/3' auf, und der "
              "darf warten")
        # Die Extras kommen in eigenen Durchgaengen nach. Gezaehlt
        # wird, bis nichts mehr ansteht - eine feste Zahl waere bei
        # der naechsten Bildart wieder falsch.
        runden = 1
        while A.index_warmlaufen(["SNES"], hoechstens=1) > 0:
            runden += 1
            if runden > 20:
                break
        check("und die Extras in eigenen Durchgaengen danach",
              all(A._docs_index_fertig("SNES", a)
                  for a in A.DOCS_BILDARTEN),
              "%d Durchgaenge fuer ein System mit %d Bildarten"
              % (runden, len(A.DOCS_BILDARTEN)))
        gezaehlt[0] = 0
        fertig = A.docs_bildarten("SNES", "Super Mario World (USA)",
                                  nur_fertig=True)
        check("danach antwortet der Zeichenweg", fertig is not None
              and "snap" in fertig, str(fertig))
        check("und zwar wieder ohne Verzeichnis zu lesen",
              gezaehlt[0] == 0, "%d x" % gezaehlt[0])
    finally:
        A.os.listdir = _echt_listdir
finally:
    A.DOCS_BASE = _echt_base
    A._docs_ordner_cache = None
    A._docs_index_cache.clear()
    shutil.rmtree(tmp, ignore_errors=True)

print()

# ---------------------------------------------------------------- 5
print("Test 5: R2 ist die Bildart, L2 bleibt der Favorit")

check("L2 ist weiterhin der Favoritenschalter",
      'BTN_TL2: "favorite"' in inp_src
      and 'AXIS_L2: "favorite"' in inp_src)
check("F8 auf der Tastatur auch",
      'KEY_F8: "favorite"' in inp_src)
check("R2 als KNOPF liegt auf der Bildart",
      'BTN_TR2: "bildart"' in inp_src)
# DIE ZWEITE ZEILE IST DIE FALLE: AXIS_R2 ist R2 als Analogtrigger.
# Waere nur eine umgestellt, verhielte sich ein Xbox-artiges Pad
# anders als sein Pro Controller - ein Fehler, den niemand bei sich
# nachstellen kann, weil er am Pad haengt.
check("und R2 als ANALOGTRIGGER ebenfalls",
      'AXIS_R2: "bildart"' in inp_src,
      "sonst verhaelt sich ein Xbox-Pad anders als ein Pro Controller")
check("R2 ist nicht mehr der Zwilling von L2",
      'BTN_TR2: "favorite"' not in inp_code
      and 'AXIS_R2: "favorite"' not in inp_code,
      "im CODE, nicht im Kommentar - dort steht absichtlich, "
      "was vorher dastand")
# Select+L2/R2 oeffnet seit Build 142 den Filter, und diese Tabelle
# ist nach der GRUNDAKTION geschluesselt. Ohne eigenen Eintrag waere
# Select+R2 still aus dem Filter herausgefallen.
check("Select+L2 oeffnet weiter den Filter",
      '"favorite": "filter"' in inp_src)
check("und Select+R2 auch, unveraendert",
      '"bildart": "filter"' in inp_src,
      "ohne diesen Eintrag faellt Select+R2 still heraus")

print()

# ---------------------------------------------------------------- 6
print("Test 6: gehakt wird an der EINEN Stelle, die es schon gab")


def koerper(quelle, name, klasse=None):
    """Der Koerper genau einer Funktion, per ast. Siehe die lange
    Begruendung in tools/test_startweg.py - Zeichenfenster und
    Textsuche sind in diesem Projekt schon dreimal danebengegangen."""
    import ast
    baum = ast.parse(quelle)
    zeilen = quelle.split("\n")
    wurzel = baum
    if klasse is not None:
        for k in baum.body:
            if isinstance(k, ast.ClassDef) and k.name == klasse:
                wurzel = k
                break
        else:
            return ""
    for k in wurzel.body:
        if isinstance(k, ast.FunctionDef) and k.name == name:
            return "\n".join(z for z in zeilen[k.lineno - 1:k.end_lineno]
                             if not z.lstrip().startswith("#"))
    return ""


cq = koerper(fe_src, "cover_quelle", klasse="Frontend")
check("cover_quelle() ist gefunden", bool(cq))
check("die Bildart wird dort gefragt",
      "_bildart_je_spiel" in cq and "docs_bildart(" in cq)
# GANZ VORN, vor der HD/SD-Entscheidung: sonst gewinnt bei einem
# vorhandenen Cover immer das Cover.
check("und zwar VOR der HD/SD-Entscheidung",
      cq.find("_bildart_je_spiel") < cq.find("self.fb.height >= 720"))
# ART ist die ArtCache-INSTANZ, nicht das Modul (siehe
# "ART = ArtCache()" in fe/art.py). "ART.docs_bildart(...)" sieht
# richtig aus und waere auf dem Geraet ein AttributeError gewesen -
# genau dieser Griff ist mir beim Bauen zuerst passiert.
check("die Funktion kommt NICHT ueber ART",
      "ART.docs_bildart" not in fe_code,
      "ART ist die Cache-Instanz, nicht das Modul - im Kommentar "
      "steht der falsche Griff absichtlich")
check("sondern ist direkt importiert",
      "docs_bildart, docs_bildarten" in fe_src)

check("es gibt die Umschaltfunktion",
      "def bildart_weiter(" in fe_src)
check("und die Aktion hinter R2",
      'elif act == "bildart":' in fe_src)
weiter = koerper(fe_src, "bildart_weiter", klasse="Frontend")
check("gewechselt wird nur zwischen vorhandenen Arten",
      "docs_bildarten(" in weiter)
check("bei nur einer Art sagt das Frontend das",
      "bildart_nur_eine" in weiter,
      "eine Taste, die ohne Erklaerung nichts tut, ist ein "
      "Fehlerbericht in Wartestellung")
check("und der Text steht im Katalog, zweisprachig",
      '"bildart_nur_eine"' in open(
          os.path.join(_REPO, "frontend", "fe", "translations.py"),
          encoding="utf-8").read())
# Die Anzeige muss den Wechsel sehen, sonst bleibt das alte Bild bis
# zum naechsten Zeilenwechsel stehen.
check("die Anzeige wird fuer ungueltig erklaert",
      "_anzeige_geaendert()" in weiter)
# Nicht auf die Karte: eine umgeschaltete Bildart ist ein Hinsehen,
# keine Einstellung.
check("gespeichert wird nichts auf der Karte",
      "ansicht_schreiben" not in weiter
      and "open(" not in weiter,
      "eine Bildart ist ein Hinsehen, keine Einstellung")

print()

# ---------------------------------------------------------------- 7
print("Test 7: der Vermerk steht auf dem Cover, nicht in der Fusszeile")

panel = koerper(fe_src, "draw_art_panel", klasse="Frontend")
check("draw_art_panel() ist gefunden", bool(panel))
check("der Vermerk wird dort gezeichnet",
      "bildart_stand(" in panel and '"R2 %d/%d"' in panel)
# Die Tastenlegende steht ausdruecklich NUR auf der Hauptseite, weil
# die Fusszeile der Liste schon Laufschrift UND Meldungen traegt und
# die sich bereits einmal in die Quere gekommen sind (Build 257).
check("die Tastenlegende bleibt unberuehrt",
      "bildart" not in koerper(fe_src, "_tastenlegende",
                               klasse="Frontend"),
      "die Fusszeile der Liste traegt schon zwei Schreiber")
check("es gibt bildart_stand()", "def bildart_stand(" in fe_src)
stand = koerper(fe_src, "bildart_stand", klasse="Frontend")
check("und es fragt nur_fertig=True",
      "nur_fertig=True" in stand,
      "im Zeichenweg darf kein Verzeichnis gelesen werden")
check("bei einer einzigen Art kommt None",
      "len(arten) < 2" in stand and "return None" in stand,
      "ein Hinweis auf eine Taste, die nichts tut, ist schlimmer "
      "als kein Hinweis")

print()

# ---------------------------------------------------------------- 8
print("Test 8: der Warmlauf macht die Arbeit, nicht der Zeichenweg")

warm = koerper(open(os.path.join(_REPO, "frontend", "fe", "art.py"),
                    encoding="utf-8").read(), "index_warmlaufen")
check("index_warmlaufen() baut alle Arten",
      "for art in DOCS_BILDARTEN" in warm)
offen = koerper(open(os.path.join(_REPO, "frontend", "fe", "art.py"),
                     encoding="utf-8").read(), "index_warm_offen")
check("und ein System gilt erst fertig, wenn alle drei stehen",
      "_docs_index_fertig" in offen,
      "sonst haette der Warmlauf die beiden neuen nie angefasst")

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
