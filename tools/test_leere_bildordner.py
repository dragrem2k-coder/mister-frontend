#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bekannt leere Bildordner (Build 347).

ANLASS: Bench 26, Abschnitt P - Genesis 433,6 ms am Stueck, davon EIN
os.stat auf /media/usb0/games/MegaDrive/Artwork mit 402,3 ms. Den Ordner
gibt es nicht; um das zu wissen, liest die USB-Platte den ganzen
ROM-Ordner. Dasselbe bei MegaCD (230 ms, Bilder im ROM-Ordner selbst
gesucht, die dort nicht liegen).

GEPRUEFT WIRD:
  1. Beim ersten Bau werden fehlende und bilderlose Ordner gemerkt - mit
     dem richtigen Zeugen (Elternordner bzw. der Ordner selbst), in
     eine Datei, ueber .tmp geschrieben.
  2. Beim naechsten Start (neu geladen): KEIN Dateizugriff auf diese
     Ordner, beobachtet wird der Zeuge, der Nachpruef-Faden startet.
  3. Entsteht der Ordner (Zeuge aendert sich), wird wieder gefragt und
     das Bild gefunden.
  4. Windows/FAT (Zeuge aendert sich NICHT): der Nachpruef-Faden findet
     das Bild, artwork_geaendert() meldet es, danach ist es da.
  5. Nur "gibt es nicht" wird gemerkt, kein Lesefehler; nur unter
     LEER_NUR_UNTER; "Neu einlesen" vergisst alles; kaputte Datei.
  6. Einbau: der Rescan ruft die Funktion (nicht ueber ART), der Bench
     nennt die Zahlen, der Pruefstand lenkt die Datei um.

Ausfuehren:
    python3 tools/test_leere_bildordner.py
"""
import errno
import json
import os
import shutil
import sys
import tempfile
import time

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
sys.path.insert(0, os.path.join(_REPO, "frontend"))
import fe.art as A                                       # noqa: E402
import fe.paths                                          # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


class Zaehler(object):
    """Zaehlt Dateizugriffe unterhalb eines Pfades."""

    def __init__(self, unter):
        self.unter = unter
        self.pfade = []

    def __enter__(self):
        self.echt = (os.stat, os.listdir, os.scandir)

        def _hulle(fn):
            def _f(p, *a, **k):
                if isinstance(p, str) and p.startswith(self.unter):
                    self.pfade.append(p)
                return fn(p, *a, **k)
            return _f
        os.stat, os.listdir, os.scandir = (_hulle(f) for f in self.echt)
        return self

    def __exit__(self, *a):
        os.stat, os.listdir, os.scandir = self.echt
        return False


tmp = tempfile.mkdtemp(prefix="leere_bildordner_")
_alt = (A.DOCS_BASE, A.FREMD_ZUSATZ_WURZELN, list(fe.paths.GAMES_BASES),
        A.LEER_NUR_UNTER, A.LEER_MERKER_FILE, A.LEER_NACHPRUEFEN_NACH)
try:
    docs = os.path.join(tmp, "docs")
    spiele = os.path.join(tmp, "games")
    basis = os.path.join(spiele, "SNES")
    os.makedirs(os.path.join(docs, "SNES", "Artwork"))
    os.makedirs(basis)
    open(os.path.join(docs, "SNES", "Artwork", "Aus docs (USA).jpg"),
         "wb").write(b"x")
    for i in range(30):
        open(os.path.join(basis, "Spiel %02d (USA).sfc" % i), "wb").close()
    A.DOCS_BASE = docs
    A.FREMD_ZUSATZ_WURZELN = ()
    fe.paths.GAMES_BASES = [spiele]
    A.LEER_NUR_UNTER = (tmp,)
    A.LEER_MERKER_FILE = os.path.join(tmp, "frontend", "art_leer.json")
    A.LEER_NACHPRUEFEN_NACH = 0.0
    A._leer[0] = None
    del A._leer_offen[:]
    A.docs_caches_leeren()

    # -----------------------------------------------------------------
    print("Test 1: erster Bau - merken mit dem richtigen Zeugen")
    # -----------------------------------------------------------------
    idx = A._docs_index("SNES")
    check("das vorhandene Cover wird gefunden",
          "Aus docs (USA)" in idx)
    merker = json.load(open(A.LEER_MERKER_FILE, encoding="utf-8"))
    fehlt = os.path.join(basis, "Artwork")
    check("fehlender Ordner gemerkt, Zeuge ist der Elternordner",
          merker.get(fehlt, [None])[0] == basis, merker.get(fehlt))
    check("bilderloser ROM-Ordner gemerkt, Zeuge ist er selbst",
          merker.get(basis, [None])[0] == basis, merker.get(basis))
    check("alle Unterordner ohne Bilder sind gemerkt",
          all(os.path.join(basis, u) in merker
              for u in A.DOCS_UNTERORDNER if u), len(merker))
    check("der Ordner MIT Bildern ist nicht gemerkt",
          os.path.join(docs, "SNES", "Artwork") not in merker)
    check("ueber .tmp geschrieben, nichts liegen geblieben",
          not os.path.exists(A.LEER_MERKER_FILE + ".tmp"))

    # -----------------------------------------------------------------
    print()
    print("Test 2: naechster Start - kein Zugriff auf die leeren Ordner")
    # -----------------------------------------------------------------
    A._leer[0] = None                     # neu laden wie nach dem Start
    A.docs_caches_leeren()
    A._index_ordner.clear()
    vorher = A.LEER_UEBERSPRUNGEN[0]
    gestartet = []
    _starten = A._leer_nachpruefen_starten
    A._leer_nachpruefen_starten = lambda: gestartet.append(1)
    with Zaehler(basis + os.sep) as z:
        idx = A._docs_index("SNES")
    A._leer_nachpruefen_starten = _starten
    check("kein einziger Zugriff unterhalb des ROM-Ordners", not z.pfade,
          z.pfade[:3])
    check("das Cover ist trotzdem da", "Aus docs (USA)" in idx)
    check("gezaehlt fuer den Bench (jeder gemerkte Ordner einmal)",
          A.LEER_UEBERSPRUNGEN[0] - vorher == len(A._leer_merker()),
          (A.LEER_UEBERSPRUNGEN[0] - vorher, len(A._leer_merker())))
    check("beobachtet wird der Zeuge", basis in A._index_ordner)
    check("der Nachpruef-Faden wird gestartet", gestartet == [1])

    # -----------------------------------------------------------------
    print()
    print("Test 3: der Ordner entsteht - es wird wieder gefragt")
    # -----------------------------------------------------------------
    # Ab hier ohne eigenen Nachpruef-Faden: Test 4 ruft ihn selbst auf,
    # ein zweiter, der nebenher liefe, waere ein Wettlauf im Test.
    A._leer_nachpruefen_starten = lambda: None
    time.sleep(0.02)
    os.makedirs(fehlt)
    open(os.path.join(fehlt, "Neu (USA).png"), "wb").write(b"x")
    st = os.stat(basis)
    os.utime(basis, (st.st_atime, st.st_mtime + 5))
    A.docs_caches_leeren()
    idx = A._docs_index("SNES")
    check("das neue Bild wird gefunden", "Neu (USA)" in idx)
    check("und der Ordner ist nicht mehr gemerkt",
          fehlt not in A._leer_merker())
    shutil.rmtree(fehlt)
    A.docs_caches_leeren()
    A._docs_index("SNES")

    # -----------------------------------------------------------------
    print()
    print("Test 4: Windows/FAT - der Zeuge bleibt gleich")
    # -----------------------------------------------------------------
    st = os.stat(basis)
    os.makedirs(fehlt)
    open(os.path.join(fehlt, "Vom PC (USA).png"), "wb").write(b"x")
    os.utime(basis, (st.st_atime, st.st_mtime))      # wie unter Windows
    A.docs_caches_leeren()
    del A._leer_offen[:]
    idx = A._docs_index("SNES")
    check("zunaechst uebersprungen (der Zeuge sagt nichts)",
          "Vom PC (USA)" not in idx)
    A._index_ordner.clear()
    check("vor dem Nachpruefen meldet niemand eine Aenderung",
          A.artwork_geaendert() is False)
    A._leer_nachpruefen(warten=0)
    check("der Faden findet das Bild und vergisst den Merker",
          fehlt not in A._leer_merker()
          and fehlt not in json.load(open(A.LEER_MERKER_FILE,
                                          encoding="utf-8")))
    check("artwork_geaendert() meldet es (einmal)",
          A.artwork_geaendert() is True and A.artwork_geaendert() is False)
    A.docs_caches_leeren()
    check("danach ist das Bild da",
          "Vom PC (USA)" in A._docs_index("SNES"))
    check("der Faden ist danach wieder frei", A._leer_faden[0] is None)
    A._leer_nachpruefen_starten = _starten
    # Der echte Faden: ein Ordner mit Bild auf der Liste - laeuft er,
    # meldet er ihn. (Ob er schon fertig ist, bevor man nachsieht, ist
    # Zufall; deshalb wird auf die Wirkung gewartet, nicht auf ihn.)
    with A._leer_sperre:
        A._leer_offen.append(fehlt)
    A._leer_widerlegt[0] = False
    A._leer_nachpruefen_starten()
    _ende = time.time() + 5.0
    while (A._leer_faden[0] is not None or not A._leer_widerlegt[0]) \
            and time.time() < _ende:
        time.sleep(0.01)
    check("der echte Faden laeuft durch, meldet und gibt sich frei",
          A._leer_widerlegt[0] is True and A._leer_faden[0] is None)
    A._leer_widerlegt[0] = False

    # -----------------------------------------------------------------
    print()
    print("Test 5: Grenzen")
    # -----------------------------------------------------------------
    leer = os.path.join(tmp, "nirgends")
    zeugen = {}
    anderswo = tempfile.mkdtemp(prefix="anderswo_")
    try:
        A._leer_vermerken(os.path.join(anderswo, "x"), anderswo, zeugen)
        check("ausserhalb von LEER_NUR_UNTER wird nichts gemerkt",
              os.path.join(anderswo, "x") not in A._leer_merker())
    finally:
        shutil.rmtree(anderswo, ignore_errors=True)
    _namen = A._ordner_namen

    def _eio(ordner, zw=None):
        if ordner.startswith(basis):
            raise OSError(errno.EIO, "Platte schlaeft")
        return _namen(ordner, zw)
    A.leere_bildordner_vergessen()
    A._ordner_namen = _eio
    A.docs_caches_leeren()
    A._docs_index("SNES")
    A._ordner_namen = _namen
    check("ein Lesefehler wird NICHT als 'gibt es nicht' gemerkt",
          not any(k.startswith(basis) for k in A._leer_merker()),
          sorted(A._leer_merker())[:2])
    A.docs_caches_leeren()
    A._docs_index("SNES")
    check("'Neu einlesen' vergisst alles",
          A._leer_merker() and (A.leere_bildordner_vergessen() or True)
          and A._leer_merker() == {}
          and json.load(open(A.LEER_MERKER_FILE, encoding="utf-8")) == {})
    with open(A.LEER_MERKER_FILE, "w") as f:
        f.write("{kaputt")
    A._leer[0] = None
    check("eine kaputte Merker-Datei heisst: nichts gemerkt",
          A._leer_merker() == {})
    check("ein Zeuge, den es nicht gibt, beglaubigt nichts",
          A._leer_bekannt(leer, {}) is False)

    # -----------------------------------------------------------------
    print()
    print("Test 6: Einbau")
    # -----------------------------------------------------------------
    fq = open(os.path.join(_REPO, "frontend", "frontend.py"),
              encoding="utf-8").read()
    zweig = fq.split('elif kind == "rescan":')[1][:900]
    check("'Neu einlesen' vergisst die Merker",
          "leere_bildordner_vergessen()" in zweig
          and "ART.leere_bildordner_vergessen" not in fq)
    check("und importiert die Funktion aus fe.art (ART ist die Instanz)",
          "    leere_bildordner_vergessen,\n" in fq.split(
              "from fe.art import (")[1].split("\n)\n")[0])
    bq = open(os.path.join(_REPO, "frontend", "fe", "bench.py"),
              encoding="utf-8").read()
    check("der Bench nennt die Zahlen",
          "LEER_UEBERSPRUNGEN" in bq and "BENCH_VERSION = 27" in bq)
    hq = open(os.path.join(_HIER, "_harness.py"), encoding="utf-8").read()
    check("der Pruefstand lenkt die Merker-Datei um",
          "LEER_MERKER_FILE" in hq)
    check("auf dem Geraet: nur unter /media/, Datei im Frontend-Ordner",
          _alt[3] == ("/media/",)
          and _alt[4] == "/media/fat/frontend/art_leer.json")
finally:
    (A.DOCS_BASE, A.FREMD_ZUSATZ_WURZELN, fe.paths.GAMES_BASES,
     A.LEER_NUR_UNTER, A.LEER_MERKER_FILE, A.LEER_NACHPRUEFEN_NACH) = (
        _alt[0], _alt[1], _alt[2], _alt[3], _alt[4], _alt[5])
    A._leer[0] = None
    A.docs_caches_leeren()
    shutil.rmtree(tmp, ignore_errors=True)

print()
if fails:
    print("ROT: %d Pruefung(en) fehlgeschlagen:" % len(fails))
    for f_ in fails:
        print("   - " + f_)
    sys.exit(1)
print("ALLES GRUEN")
