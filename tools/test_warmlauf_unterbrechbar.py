#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Die Vorarbeit nach dem Start haelt fuer einen Tastendruck an (Build 321).

DER ANLASS, in seinen Worten: "wenn ich denn mister anmache und das
frontend startet hab ich das gefuehl als wenn die ersten 10 sekunden das
joypad manchmal wie eingefroren ist ! und eingaben uebersprungen oder
nicht wahrgenommen werden! danach wirds dann besser".

In den ersten Sekunden werden die Namensverzeichnisse der Cover gebaut -
im Leerlauf der Hauptschleife (index_warmlaufen) und in einem Faden
(_prewarm_art_dirs). Der Docstring von index_warmlaufen() nannte die
Grenze selbst: "ein BEGONNENER Tick laeuft durch" - drei Verzeichnisse
zu rund 167 ms. Eine Taste, die hineinfiel, wartete, und in dieser Zeit
las niemand das Pad.

GEPRUEFT WIRD:
  1. Ein Verzeichnis ruft alle INDEX_HAPPEN Namen zwischendurch(), und
     das Ergebnis ist dasselbe wie ohne.
  2. Wirft zwischendurch() IndexUnterbrochen, wird das halbe
     Verzeichnis NICHT gespeichert.
  3. index_warmlaufen() kehrt dann sofort zurueck, zaehlt nichts als
     gebaut und schreibt keine "gebaut"-Zeile; der naechste Ruhemoment
     baut es vollstaendig (mit Dauer im Log).
  4. Von der anderen Seite: die Hauptschleife reicht ihre
     Unterbrechung wirklich durch (_warmlauf_tick), und die bricht genau
     dann ab, wenn eine Eingabe ansteht - GEGENPROBE ohne Eingabe.
  5. Ein Verzeichnis, das der Zeichenweg SOFORT braucht, holt das Pad
     ab (INDEX_ABHOLER) - aber nur auf dem Hauptfaden.
  6. Jede Startmarke holt das Pad ab.
  7. Der Faden _prewarm_art_dirs haelt mittendrin an.
  8. Der Schreib-Arbeiter zaehlt eine Pause ab ihrem BEGINN, und die
     laufende Pause ist abfragbar (der Fehler im Bench L.4).
  9. Die Hauptschleife meldet EINGABE-STAU.

Ausfuehren:
    python3 tools/test_warmlauf_unterbrechbar.py
"""
import os
import shutil
import sys
import tempfile
import threading
import time

_ECHTE_UHR = time.monotonic

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
sys.path.insert(0, _HIER)

import _harness as H                                     # noqa: E402

fm = H.fm
import fe.art as A                                       # noqa: E402
from _quelle import koerper, nur_code                    # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


print(__doc__.strip().split("\n")[0])
print()

TMP = tempfile.mkdtemp(prefix="warmlauf_unterbrechbar_")
HD, BASE = os.path.join(TMP, "hd"), os.path.join(TMP, "base")
N_DATEIEN = 700
SYSTEME = ("SNES", "GENESIS")
for wurzel in (HD, BASE):
    for sk in SYSTEME:
        os.makedirs(os.path.join(wurzel, sk))
        for i in range(N_DATEIEN):
            open(os.path.join(wurzel, sk, "%03d Spiel %d (USA) [!].art"
                              % (i % 40, i)), "w").close()
_ALT_WURZELN = A.INDEX_WARM_WURZELN
A.INDEX_WARM_WURZELN = (HD, BASE)
_ALT_ABHOLER = A.INDEX_ABHOLER[0]
A.INDEX_ABHOLER[0] = None


def kalt(*systeme):
    for sk in systeme or SYSTEME:
        for w in (HD, BASE):
            A._art_index_cache.pop((w, sk), None)
        A._docs_index_cache.pop(sk, None)


def cover_fertig(sk):
    """Die blockierende Gruppe eines Systems (beide Cover-Ordner und das
    Cover der fremden Datenbank) - genau das, was EIN Warmlauf-Tick baut.
    index_warm_offen() taugt dafuer nicht: es nennt ein System offen,
    bis auch Bildschirmfoto und Titelbild stehen."""
    return (all((w, sk) in A._art_index_cache for w in (HD, BASE))
            and A._docs_index_fertig(sk, "boxart"))


class Abbruch(object):
    """zwischendurch(), das beim n-ten Aufruf abbricht."""

    def __init__(self, beim=None):
        self.n = 0
        self.beim = beim

    def __call__(self):
        self.n += 1
        if self.beim is not None and self.n >= self.beim:
            raise A.IndexUnterbrochen()


try:
    # -----------------------------------------------------------------------
    print("Test 1: alle INDEX_HAPPEN Namen innehalten, gleiches Ergebnis")
    # -----------------------------------------------------------------------
    kalt()
    ohne = dict(A._art_index(HD, "SNES"))
    kalt()
    z = Abbruch()
    mit = dict(A._art_index(HD, "SNES", z))
    # Einmal nach dem Lesen des Ordners, dann in drei Durchgaengen ueber
    # die Namen (exakt, ohne Nummer, Vergleichsname) je einmal alle
    # INDEX_HAPPEN Namen - beim ersten Namen eines Durchgangs nicht.
    erwartet_min = 1 + 3 * ((N_DATEIEN - 1) // A.INDEX_HAPPEN)
    check("zwischendurch wird oft genug gerufen", z.n >= erwartet_min,
          "%d mal bei %d Dateien (Happen %d)"
          % (z.n, N_DATEIEN, A.INDEX_HAPPEN))
    check("das Verzeichnis ist dasselbe wie ohne", mit == ohne,
          "%d Eintraege" % len(mit))
    check("und es ist gespeichert", (HD, "SNES") in A._art_index_cache)

    # -----------------------------------------------------------------------
    print()
    print("Test 2: abgebrochen wird nichts gespeichert")
    # -----------------------------------------------------------------------
    kalt()
    try:
        A._art_index(HD, "SNES", Abbruch(beim=3))
        geworfen = False
    except A.IndexUnterbrochen:
        geworfen = True
    check("IndexUnterbrochen kommt beim Aufrufer an", geworfen)
    check("kein halbes Verzeichnis im Zwischenspeicher",
          (HD, "SNES") not in A._art_index_cache)

    # -----------------------------------------------------------------------
    print()
    print("Test 3: index_warmlaufen() bricht ab und baut danach vollstaendig")
    # -----------------------------------------------------------------------
    kalt()
    zeilen = []
    _echt_log = A.LOG
    A.LOG = lambda m: zeilen.append(m)
    try:
        r1 = A.index_warmlaufen(list(SYSTEME), hoechstens=1,
                                zwischendurch=Abbruch(beim=2))
        z1 = list(zeilen)
        offen1 = [sk for sk in SYSTEME if not cover_fertig(sk)]
        r2 = A.index_warmlaufen(list(SYSTEME), hoechstens=1,
                                zwischendurch=Abbruch())
        z2 = zeilen[len(z1):]
    finally:
        A.LOG = _echt_log
    check("abgebrochen: 0 gebaut", r1 == 0, r1)
    check("und keine 'gebaut'-Zeile", not any("gebaut" in m for m in z1),
          z1)
    check("beide Systeme stehen weiter aus", offen1 == list(SYSTEME),
          offen1)
    check("im naechsten Ruhemoment: eins gebaut", r2 == 1, r2)
    check("mit Dauer im Log", any("Cover-Index gebaut (" in m
                                  and "ms)" in m for m in z2), z2)

    # -----------------------------------------------------------------------
    print()
    print("Test 4: die Hauptschleife reicht ihre Unterbrechung durch")
    # -----------------------------------------------------------------------
    H.set_screen(1280, 720)
    f = H.make_frontend(page=0)
    gesehen = {}
    _echt_iw = fm.index_warmlaufen

    def _fang(systeme, hoechstens=1, zwischendurch=None):
        gesehen["zw"] = zwischendurch
        return 0

    fm.index_warmlaufen = _fang
    try:
        f._warmlauf_fertig_fuer = None
        f._warmlauf_systeme = lambda: ["SNES"]
        f._warmlauf_tick()
    finally:
        fm.index_warmlaufen = _echt_iw
    zw = gesehen.get("zw")
    check("_warmlauf_tick uebergibt eine Unterbrechung",
          zw is not None and getattr(zw, "__name__", "")
          == "_leerlauf_zwischendurch", zw)

    class InpAttrappe(object):
        def __init__(self, ja):
            self.ja = ja
            self.gefragt = 0

        def eingabe_anstehend(self):
            self.gefragt += 1
            return self.ja

    f.inp = InpAttrappe(False)
    try:
        f._leerlauf_zwischendurch()
        ohne_abbruch = True
    except A.IndexUnterbrochen:
        ohne_abbruch = False
    check("GEGENPROBE: ohne Eingabe kein Abbruch",
          ohne_abbruch and f.inp.gefragt == 1)
    f.inp = InpAttrappe(True)
    try:
        f._leerlauf_zwischendurch()
        abgebrochen = False
    except A.IndexUnterbrochen:
        abgebrochen = True
    check("mit Eingabe: Abbruch", abgebrochen)
    check("und gezaehlt", getattr(f, "_warmlauf_unterbrochen", 0) >= 1)
    # Und durch den ganzen Weg: echter Tick, echte Verzeichnisse.
    kalt()
    f.inp = InpAttrappe(True)
    f._warmlauf_fertig_fuer = None
    f._warmlauf_systeme = lambda: list(SYSTEME)
    gebaut = f._warmlauf_tick()
    check("durch den ganzen Weg: Taste steht an -> nichts gebaut",
          gebaut is False and not any(cover_fertig(sk) for sk in SYSTEME),
          gebaut)
    f.inp = InpAttrappe(False)
    gebaut = f._warmlauf_tick()
    check("keine Taste -> ein System gebaut",
          gebaut is True
          and [cover_fertig(sk) for sk in SYSTEME] == [True, False],
          "%r, %r" % (gebaut, [cover_fertig(sk) for sk in SYSTEME]))

    # -----------------------------------------------------------------------
    print()
    print("Test 5: der Zeichenweg holt das Pad ab - nur auf dem Hauptfaden")
    # -----------------------------------------------------------------------
    abgeholt = {"n": 0, "faeden": set()}

    def _abholer():
        abgeholt["n"] += 1
        abgeholt["faeden"].add(threading.current_thread().name)

    A.INDEX_ABHOLER[0] = _abholer
    try:
        kalt("GENESIS")
        A._art_index(HD, "GENESIS")
        n_haupt = abgeholt["n"]
        kalt("GENESIS")
        abgeholt["n"] = 0
        t = threading.Thread(target=A._art_index, args=(HD, "GENESIS"),
                             name="nebenfaden")
        t.start()
        t.join()
        n_neben = abgeholt["n"]
    finally:
        A.INDEX_ABHOLER[0] = None
    check("auf dem Hauptfaden wird abgeholt", n_haupt >= erwartet_min // 2,
          n_haupt)
    check("in einem anderen Faden NICHT (der Puffer gehoert "
          "read_action)", n_neben == 0, n_neben)
    check("das Frontend setzt den Abholer auf InputManager.abholen",
          "INDEX_ABHOLER[0] = self.inp.abholen"
          in nur_code(koerper(open(H.FRONTEND_PY, encoding="utf-8")
                              .read(), "__init__", "Frontend")))

    # -----------------------------------------------------------------------
    print()
    print("Test 6: jede Startmarke holt das Pad ab")
    # -----------------------------------------------------------------------
    class Zaehler(object):
        n = 0

        def abholen(self):
            Zaehler.n += 1
            return 0

    f.inp = Zaehler()
    f._startmarke("Test")
    f._startmarke("Test 2")
    check("zweimal gerufen", Zaehler.n == 2, Zaehler.n)

    # -----------------------------------------------------------------------
    print()
    print("Test 7: der Faden _prewarm_art_dirs haelt mittendrin an")
    # -----------------------------------------------------------------------
    _init = nur_code(koerper(open(H.FRONTEND_PY, encoding="utf-8").read(),
                             "__init__", "Frontend"))
    check("er uebergibt sein Innehalten an _art_index",
          "_art_index(ART_BASE, _syskey, _faden_innehalten)" in _init
          and "_art_index(ART_HD, _syskey, _faden_innehalten)" in _init)
    _inne = _init.split("def _faden_innehalten")[1].split("threading.")[0]
    check("und fasst dabei die Eingabe nicht an (nur held lesen)",
          "abholen" not in _inne and "read_action" not in _inne
          and "eingabe_anstehend" not in _inne)
    check("mit Obergrenze, damit es vorangeht",
          "PREWARM_MAX_WARTEN" in _inne)

    # -----------------------------------------------------------------------
    print()
    print("Test 8: der Schreib-Arbeiter zaehlt die Pause ab ihrem Beginn")
    # -----------------------------------------------------------------------
    _echt_marke = A._thumb_cache_put_marke
    geschrieben = []
    A._thumb_cache_put_marke = lambda *a: geschrieben.append(a)
    _alt_defer = A.ART._defer_uncached
    try:
        A.ART._defer_uncached = True
        vor = A.schreib_pausen_stand()[0]
        A._schreib_einstellen(("marke", "/x/test.png", 10, 10))
        laeuft = None
        ende = _ECHTE_UHR() + 2.0
        while _ECHTE_UHR() < ende:
            laeuft = A.schreib_pause_laeuft()
            if laeuft is not None:
                break
            time.sleep(0.02)
        mitten = A.schreib_pausen_stand()[0]
        check("die laufende Pause ist abfragbar", laeuft is not None,
              laeuft)
        check("und schon MITTEN in der Pause gezaehlt", mitten == vor + 1,
              "%d -> %d" % (vor, mitten))
        check("geschrieben wird waehrenddessen nichts", not geschrieben)
        A.ART._defer_uncached = False
        ende = _ECHTE_UHR() + 3.0
        while _ECHTE_UHR() < ende and not geschrieben:
            time.sleep(0.02)
        check("losgelassen: der Auftrag wird erledigt", len(geschrieben) == 1)
        check("und die Pause laeuft nicht mehr",
              A.schreib_pause_laeuft() is None)
    finally:
        A.ART._defer_uncached = _alt_defer
        A._thumb_cache_put_marke = _echt_marke

    # -----------------------------------------------------------------------
    print()
    print("Test 9: die Hauptschleife meldet EINGABE-STAU")
    # -----------------------------------------------------------------------
    _run = nur_code(koerper(open(H.FRONTEND_PY, encoding="utf-8").read(),
                            "run", "Frontend"))
    check("run() liest eingabe_wartezeit",
          "eingabe_wartezeit" in _run and "EINGABE_STAU_SCHWELLE" in _run)
    _na = nur_code(koerper(open(H.FRONTEND_PY, encoding="utf-8").read(),
                           "next_action", "Frontend"))
    check("der Leerlauf bucht Warmlauf und Nachzeichnen",
          '_leerlauf_buchen("Warmlauf"' in _na
          and '_leerlauf_buchen("Nachzeichnen"' in _na)
    f._leerlauf_max = None
    f._leerlauf_buchen("A", H.fm.time.monotonic() - 0.0)
    check("_leerlauf_buchen merkt sich etwas", f._leerlauf_max is not None
          and f._leerlauf_max[0] == "A")
finally:
    A.INDEX_WARM_WURZELN = _ALT_WURZELN
    A.INDEX_ABHOLER[0] = _ALT_ABHOLER
    shutil.rmtree(TMP, ignore_errors=True)

print()
if fails:
    print("ROT: %d Pruefung(en) fehlgeschlagen:" % len(fails))
    for f_ in fails:
        print("   - " + f_)
    sys.exit(1)
print("ALLES GRUEN")
