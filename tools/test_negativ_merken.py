#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Das gemerkte NEIN (Build 222) - und der Stillstand, der es vergisst.

WORUM ES GEHT. Abschnitt J des Benchs sagte im Bericht vom 29.09. fuer
die Spieleliste:

    cover 0.00   (davon Karte 13.44 in 20 Zugriffen)

Zwanzig Zugriffe auf die SD-Karte JE SCROLLSCHRITT, 13,44 ms, und der
Posten "cover" daneben mit 0,00 - die Zugriffe liefen also an der
Messung vorbei, mitten durch den REST. Nachgestellt auf dem
Entwicklungsrechner: ein Eintrag OHNE Cover kostete drei Zugriffe, und
zwar bei JEDEM Schritt aufs Neue, auch beim zehnten Mal auf denselben
Eintrag.

Der Grund war, dass nur ein TREFFER gemerkt wurde:

  * _quelldaten() legte (Groesse, Zeit) ab - bei OSError aber nichts,
    also fragte ein Spiel ohne Cover die Karte immer wieder.
  * _auslagern_versuchen() fragte mit einem eigenen os.path.isfile()
    NOCH EINMAL nach derselben Datei.
  * _thumb_cache_get() lief in ein open(), das jedes Mal mit
    FileNotFoundError endete.

DIE GEGENPROBE, die dieser Test mitfuehrt: das Nein darf nicht stehen
bleiben. Der Arbeitsprozess schreibt Miniaturen auf die Karte, waehrend
hier geblaettert wird - bliebe unser Nein ueber seine Datei bestehen,
taeuchte das Cover nie auf. negativ_vergessen() raeumt es deshalb beim
Stillstand weg, und zwar NUR das Nein: die Treffer bleiben stehen, sonst
waere der Zwischenspeicher aus Build 212 wieder umsonst.

Ausfuehren:
    python3 tools/test_negativ_merken.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H          # noqa: E402,F401  (setzt den Pfad)

import fe.art as A            # noqa: E402

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

fails = []


def check(name, ok, info=""):
    if ok:
        print("  OK   %s %s" % (name, info))
    else:
        print("  FEHL %s %s" % (name, info))
        fails.append(name)


# ---------------------------------------------------------------------------
print("Test 1: eine fehlende Quelldatei wird genau EINMAL erfragt")
# ---------------------------------------------------------------------------
_echt_stat = os.stat
zaehler = [0]


def _stat_haken(p, *a, **k):
    zaehler[0] += 1
    return _echt_stat(p, *a, **k)


with tempfile.TemporaryDirectory() as tmp:
    fehlt = os.path.join(tmp, "gibt_es_nicht.art")
    da = os.path.join(tmp, "gibt_es.art")
    with open(da, "wb") as f:
        f.write(b"x" * 16)

    A.quelldaten_vergessen()
    os.stat = _stat_haken
    try:
        zaehler[0] = 0
        for _ in range(5):
            check_wert = A._quelldaten(fehlt)
        check("fuenf Abfragen, ein Zugriff", zaehler[0] == 1,
              "%d Zugriffe" % zaehler[0])
        check("und die Antwort bleibt None", check_wert is None)

        zaehler[0] = 0
        for _ in range(5):
            wert = A._quelldaten(da)
        check("dasselbe fuer eine Datei, die es GIBT", zaehler[0] == 1,
              "%d Zugriffe" % zaehler[0])
        check("und die Antwort ist (Groesse, Zeit)",
              isinstance(wert, tuple) and wert[0] == 16, "%r" % (wert,))

        # ---------------------------------------------------------------
        print()
        print("Test 2: der Stillstand vergisst NUR das Nein")
        # ---------------------------------------------------------------
        A.negativ_vergessen()
        zaehler[0] = 0
        A._quelldaten(da)
        check("der Treffer steht noch", zaehler[0] == 0,
              "%d Zugriffe - sonst waere Build 212 umsonst" % zaehler[0])
        zaehler[0] = 0
        A._quelldaten(fehlt)
        check("das Nein ist weg und wird neu geprueft", zaehler[0] == 1,
              "%d Zugriffe" % zaehler[0])

        # ---------------------------------------------------------------
        print()
        print("Test 3: ein Cover, das WAEHRENDDESSEN entsteht")
        # ---------------------------------------------------------------
        # Genau der Fall, der den Nutzer stoeren wuerde: waehrend des
        # Blaetterns legt der Arbeitsprozess die Datei an. Solange
        # geblaettert wird, darf das alte Nein gelten (sonst waere die
        # Ersparnis weg); beim Loslassen muss es verschwinden.
        neu = os.path.join(tmp, "kommt_gleich.art")
        A._quelldaten(neu)                      # Nein merken
        with open(neu, "wb") as f:
            f.write(b"y" * 32)
        check("waehrend des Blaetterns gilt das gemerkte Nein",
              A._quelldaten(neu) is None,
              "sonst kostet jeder Schritt wieder einen Zugriff")
        A.negativ_vergessen()
        check("nach dem Loslassen ist die Datei da",
              A._quelldaten(neu) is not None,
              "sonst taucht ein nachgerechnetes Cover nie auf")
    finally:
        os.stat = _echt_stat
        A.quelldaten_vergessen()

# ---------------------------------------------------------------------------
print()
print("Test 4: der Karten-Cache merkt sich fehlende Dateien ebenso")
# ---------------------------------------------------------------------------
_echt_open = A.open if hasattr(A, "open") else open
versuche = [0]


def _open_haken(p, *a, **k):
    versuche[0] += 1
    return _echt_open(p, *a, **k)


import builtins                                           # noqa: E402
builtins.open = _open_haken
try:
    A.quelldaten_vergessen()
    with tempfile.TemporaryDirectory() as tmp:
        ohne = os.path.join(tmp, "ohne_miniatur.png")
        versuche[0] = 0
        for _ in range(5):
            erg = A._thumb_cache_get(ohne, 100, 100)
        check("fuenf Abfragen, ein open()", versuche[0] == 1,
              "%d Versuche" % versuche[0])
        check("und es kommt nichts zurueck", erg is None)
        A.negativ_vergessen()
        versuche[0] = 0
        A._thumb_cache_get(ohne, 100, 100)
        check("nach dem Stillstand wird wieder nachgesehen",
              versuche[0] == 1, "%d Versuche" % versuche[0])
finally:
    builtins.open = _echt_open
    A.quelldaten_vergessen()

# ---------------------------------------------------------------------------
print()
print("Test 5: der Stillstand ist angeschlossen")
# ---------------------------------------------------------------------------
# Ein Zwischenspeicher, den niemand leert, ist ein Fehler mit Ansage -
# deshalb steht hier, dass die FLANKE gemeint ist (von "blaettert" nach
# "steht"), und nicht etwa jeder Durchlauf.
quelle = open(H.FRONTEND_PY, encoding="utf-8", errors="replace").read()
check("frontend.py ruft negativ_vergessen()",
      "negativ_vergessen()" in quelle)
_stelle = quelle[max(0, quelle.find("negativ_vergessen()") - 900):
                 quelle.find("negativ_vergessen()") + 40]
check("und zwar an der Flanke, nicht bei jedem Aufbau",
      "_vorher and not ART._defer_uncached" in _stelle,
      "sonst waere das Merken wirkungslos")
check("die Funktion wird auch importiert",
      "negativ_vergessen," in quelle or "negativ_vergessen " in quelle)

# ---------------------------------------------------------------------------
print()
print("Test 6: wer auf den Arbeitsprozess wartet, traut dem Nein nicht")
# ---------------------------------------------------------------------------
# DIESE BEIDEN HABEN BEIM BAUEN ANGESCHLAGEN, und zwar zu Recht:
# tools/test_kaltes_cover.py ("und der naechste Aufruf hat das Bild") und
# test_cover_prewarm.py. Der Arbeitsprozess schreibt die Datei in einem
# ANDEREN Prozess - unser Nein kann davon nichts wissen. Also gilt es
# nicht, solange wir auf genau dieses Cover warten, und es wird
# weggeworfen, sobald eine Lieferung ankommt.
quelle_art = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "..", "frontend", "fe", "art.py"),
                  encoding="utf-8", errors="replace").read()
check("_thumb_cache_get kennt den Schalter nein_gilt",
      "def _thumb_cache_get(path, w, h, nachziehen_erlaubt=False, "
      "nein_gilt=True)" in quelle_art)
check("und der Zeichenpfad schaltet ihn bei einem Wartefall ab",
      "box_key not in self._warte_start" in quelle_art,
      "sonst taucht ein nachgerechnetes Cover nie auf")
check("eine Lieferung wirft das gemerkte Nein weg",
      "_thumb_fehlt.clear()" in quelle_art.split("def warte_pruefen")[1]
      [:1400] if "def warte_pruefen" in quelle_art else False)
check("und eine selbst geschriebene Datei ebenso",
      quelle_art.count("_thumb_fehlt.discard(cpath)") >= 2,
      "beide Schreibwege: Miniatur und Marke")

# ---------------------------------------------------------------------------
print()
print("Test 7: die drei Dauerfrager aus dem Zeichenweg (Build 224)")
# ---------------------------------------------------------------------------
# ALLE DREI STANDEN IM BERICHT DES NUTZERS VOM 02.10., Abschnitt J, mit
# ihrer Zahl JE SCROLLSCHRITT - und keiner von ihnen hat dort etwas zu
# suchen.
import fe.scan as SC                                      # noqa: E402
import fe.settings as SE                                  # noqa: E402

check("ordner_sind_dazugekommen() sperrt sich selbst",
      hasattr(SC, "DAZU_SPERRE") and SC.DAZU_SPERRE >= 1.0,
      "%r s - 20,9 getmtime je Schritt standen im Bericht"
      % getattr(SC, "DAZU_SPERRE", None))
_q = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "..", "frontend", "fe", "scan.py"),
          encoding="utf-8", errors="replace").read()
check("und zwar unabhaengig vom Aufrufer",
      "if jetzt < _DAZU_BIS:" in _q,
      "die Drosselung in frontend.py allein hat nicht gereicht")

_s = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "..", "frontend", "fe", "settings.py"),
          encoding="utf-8", errors="replace").read()
check("eq_effect_enabled geht ueber den Zwischenspeicher",
      '_hole(("eq_effect"' in _s,
      "stand mit 1,0 Zugriffen je Schritt im Bericht")

_f = open(H.FRONTEND_PY, encoding="utf-8", errors="replace").read()
check("die PERF-Zeile ist gedrosselt",
      "_perf_log_naechste" in _f,
      "jede Logzeile ist ein open() auf die Karte")
check("und sagt, wie viele sie verschluckt hat",
      "weitere in der letzten Sekunde" in _f,
      "eine Zahl, die fehlt, ist schlimmer als eine, die sagt dass sie fehlt")

# ---------------------------------------------------------------------------
print()
print("Test 8: das Nein ueberlebt den Stillstand (Build 229)")
# ---------------------------------------------------------------------------
# BEFUND DES NUTZERS: "wenn ich durch eine grosse sammlung scrolle, die
# roms die keine boxarts haben ploppen immer etwas spaeter auf oder
# werden nachgerechnet."
#
# Das Nein wurde bei JEDEM Stillstand weggeworfen - also jedesmal, wenn
# man aufhoert zu scrollen, und damit genau in dem Moment, in dem man
# hinsieht. Fuer jeden Eintrag ohne Artwork wurden dann wieder drei
# Dateizugriffe faellig. Im Geraetebericht vom 03.10. stand dazu fuer die
# Galerie: "cover 1.91 (davon Karte 2.83 in 23 Zugriffen)".
#
# Geprueft wird die REGEL, nicht der Bildschirm: negativ_faellig()
# beantwortet das "ob", negativ_vergessen() raeumt. Zwei Fragen in einer
# Funktion waeren eine, die man irgendwann falsch beantwortet.
# Der Startwert liegt mit Absicht weit in der Vergangenheit: der ERSTE
# Stillstand nach dem Start muss nachsehen, sonst traegt das Frontend
# ein Nein mit sich herum, das es nie geprueft hat. (Weiter oben in
# diesem Test wurde schon geraeumt - also hier ausdruecklich auf den
# Startzustand zuruecksetzen, statt sich auf die Reihenfolge zu
# verlassen.)
A._NEGATIV_ZULETZT = -1e9
check("der allererste Blick ist faellig",
      A.negativ_faellig(0.0) is True,
      "beim Start darf nichts von gestern stehenbleiben")

A.negativ_vergessen(1000.0)
check("direkt danach nicht mehr",
      A.negativ_faellig(1000.0) is False)
check("auch nach einer Sekunde nicht",
      A.negativ_faellig(1001.0) is False,
      "genau das war der Fehler: jeder Stillstand raeumte auf")
check("kurz vor dem Takt noch nicht",
      A.negativ_faellig(1000.0 + A.NEGATIV_TAKT - 0.1) is False)
check("mit dem Takt wieder",
      A.negativ_faellig(1000.0 + A.NEGATIV_TAKT) is True,
      "wer Artwork auf die Karte kopiert, wartet hoechstens %g s"
      % A.NEGATIV_TAKT)

# UND ES MUSS WIRKLICH RAEUMEN, wenn es dran ist - sonst waere aus dem
# Fehler "zu oft" der Fehler "nie" geworden, und der ist schlimmer:
# ein Cover, das jemand nachtraeglich hinlegt, taeuchte nie auf.
A._thumb_fehlt.add("/irgendwo/fehlt.bin")
A.negativ_vergessen(2000.0)
check("und wenn es raeumt, raeumt es wirklich",
      "/irgendwo/fehlt.bin" not in A._thumb_fehlt)
check("der Takt faengt dabei neu an",
      A.negativ_faellig(2000.0) is False)

# Der Arbeitsprozess raeumt sein eigenes Nein unabhaengig davon weg -
# sonst haette die Drosselung ihn ausgebremst.
_a = open(os.path.join(_REPO, "frontend", "fe", "art.py"),
          encoding="utf-8").read()
check("der Warteblock raeumt weiterhin SOFORT",
      "_thumb_fehlt.clear()" in _a.split("DER ARBEITSPROZESS HAT GELIEFERT")
      [1][:600],
      "wer liefert, raeumt selbst auf - unabhaengig vom Takt")

_f2 = open(H.FRONTEND_PY, encoding="utf-8", errors="replace").read()
check("und der Stillstand fragt vorher nach",
      "and negativ_faellig():" in _f2,
      "nicht mehr an jeder Flanke")

print()
if fails:
    print("FEHLGESCHLAGEN (%d):" % len(fails))
    for f in fails:
        print("  - %s" % f)
    sys.exit(1)
print("Alles in Ordnung.")
