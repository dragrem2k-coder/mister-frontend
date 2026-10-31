#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Das Cover des Basis-Spiels erben (Build 298).

WORUM ES GEHT. Befund des Nutzers: "mir fehlen immer noch einige
boxarts zu vielen spielen, kann man da noch was aendern? ich meine
immer wenn ich durch scrolle das es genau an diesen ohne cover immer
etwas hakt."

Seine SMW-Hacks liegen laut der Einrichtungsanleitung unter
/media/fat/games/SNES/SMW_HACKS/ und bilden ein eigenes System. Die
fremde Datenbank kennt kein Cover fuer "Brutal Mario" - fuer JEDEN
dieser Hacks gibt es also einen Platzhalter und drei fehlschlagende
Dateizugriffe je Scrollschritt.

Ein System darf deshalb ein BASIS-SPIEL benennen (COVER_BASIS in
fe/art.py). Findet ein Eintrag auf keinem der vier echten Wege ein
Cover, bekommt er das des Basis-Spiels.

WAS DIESER TEST VOR ALLEM SICHERT, ist nicht die Funktion sondern die
REIHENFOLGE und die REICHWEITE:

  * ein eigenes Cover gewinnt immer - das Erben ist der LETZTE Weg,
  * ein System ohne Eintrag erbt NICHTS (keine Rateregel, siehe den
    Kommentarblock bei COVER_BASIS: ein falsches Bild an einem
    normalen Spiel waere schlimmer als ein Platzhalter),
  * das Basis-Spiel erbt nicht von sich selbst (sonst Endlosschleife),
  * der Schalter wirkt wirklich.

Ausfuehren:
    python3 tools/test_cover_basis.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H          # noqa: E402,F401  (setzt den Pfad)

import fe.art as A            # noqa: E402
from _quelle import koerper, nur_code   # noqa: E402

# DIE BEIDEN HELFER WOHNEN IN tools/_quelle.py, und das ist der
# eigentliche Ertrag dieser Runde: die erste Fassung hier war
# falsch (sie suchte das Schlusszeichen eines Docstrings am
# Zeilenanfang und gab deshalb leeren Code zurueck), und zwei
# aeltere Tests hatten einen anderen Fehler derselben Sorte.
# Fuenf nachgebaute Fassungen, drei davon kaputt - jetzt eine.

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ART_PY = os.path.join(_REPO, "frontend", "fe", "art.py")

fails = []


def check(name, ok, info=""):
    if ok:
        print("  OK   %s %s" % (name, info))
    else:
        print("  FEHL %s %s" % (name, info))
        fails.append(name)






_quelle = open(_ART_PY, encoding="utf-8", errors="replace").read()


def frisch():
    """Alle Zwischenspeicher leeren, die am Erben haengen."""
    A._art_index_cache.clear()
    A._basis_cover_cache.clear()
    A._docs_index_cache.clear()
    A._cover_basis_eigen = None
    A._basis_an = True                 # Schalter im Test immer AN
    A.quelldaten_vergessen()
    A._basis_an = True                 # quelldaten_vergessen() setzt zurueck


# ---------------------------------------------------------------------------
print("Test 1: ein Hack ohne eigenes Cover erbt das des Basis-Spiels")
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    frisch()
    sysdir = os.path.join(tmp, "SMW_HACKS")
    os.makedirs(sysdir)
    # Der Name der ECHTEN Datei traegt die Region - genau wie in der
    # Datenbank des Nutzers. Dass "Super Mario World" sie trotzdem
    # findet, ist vergleichsname() aus Build 117, und das gehoert mit
    # geprueft: ohne diesen Schritt waere die Tabelle unbrauchbar,
    # weil niemand die Regionsschreibweise der Karte kennt.
    basis = os.path.join(sysdir, "Super Mario World (USA).art")
    with open(basis, "wb") as f:
        f.write(b"z" * 16)

    hacks = ["Brutal Mario", "Kaizo Mario World", "Invictus"]
    pfade = [A._art_path_in(tmp, "SMW_HACKS", h) for h in hacks]
    check("jeder Hack bekommt einen Pfad", all(p for p in pfade))
    check("und zwar den des Basis-Spiels",
          all(p == basis for p in pfade),
          "%r" % (sorted(set(pfade)),))
    # DAS IST DER EIGENTLICHE GEWINN und keine Nebenbemerkung: der
    # Schluessel des Miniaturen-Zwischenspeichers ist der Pfad plus die
    # Kastengroesse (siehe _thumb_cache_key()). EIN Pfad heisst also
    # EINE gerechnete Miniatur fuer den ganzen Ordner - der Hack-Ordner
    # wird dadurch billiger als vorher, nicht teurer.
    check("alle Hacks teilen EINEN Pfad, also EINE Miniatur",
          len(set(pfade)) == 1,
          "%d verschiedene" % len(set(pfade)))

# ---------------------------------------------------------------------------
print()
print("Test 2: ein eigenes Cover gewinnt - Erben ist der LETZTE Weg")
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    frisch()
    sysdir = os.path.join(tmp, "SMW_HACKS")
    os.makedirs(sysdir)
    basis = os.path.join(sysdir, "Super Mario World (USA).art")
    eigen = os.path.join(sysdir, "Brutal Mario.art")
    for p in (basis, eigen):
        with open(p, "wb") as f:
            f.write(b"z" * 16)
    check("wer ein eigenes Cover hat, behaelt es",
          A._art_path_in(tmp, "SMW_HACKS", "Brutal Mario") == eigen)
    check("und der Nachbar ohne eigenes erbt weiterhin",
          A._art_path_in(tmp, "SMW_HACKS", "Kaizo Mario World") == basis)

# ---------------------------------------------------------------------------
print()
print("Test 3: ein System ohne Eintrag erbt NICHTS")
# ---------------------------------------------------------------------------
# Das ist die Reichweite der Aenderung, und sie ist der Grund, warum
# keine Rateregel gebaut wurde. Ein normales SNES-Spiel ohne Cover darf
# auf keinen Fall das Bild eines anderen Spiels bekommen.
with tempfile.TemporaryDirectory() as tmp:
    frisch()
    sysdir = os.path.join(tmp, "SNES")
    os.makedirs(sysdir)
    with open(os.path.join(sysdir, "Super Mario World (USA).art"), "wb") as f:
        f.write(b"z" * 16)
    pfad = A._art_path_in(tmp, "SNES", "Irgendein Spiel ohne Cover")
    check("SNES erbt nicht",
          pfad.endswith("Irgendein Spiel ohne Cover.art"), pfad)
    check("der Rueckfallpfad existiert auch wirklich nicht",
          not os.path.exists(pfad),
          "sonst wuerde der Platzhalter nicht erscheinen")
    # UND DIE GEGENPROBE AUF DIE TABELLE SELBST: sie darf nur Systeme
    # enthalten, die wir auch ausliefern. Ein Eintrag fuer ein System,
    # das es nicht gibt, waere ein stiller Tippfehler - genau die Sorte
    # Fehler, die erst beim Nutzer auffaellt.
    from fe.systems import GAME_SYSTEMS, OPTIONAL_GAME_SYSTEMS
    bekannt = {e[1] for e in list(GAME_SYSTEMS) + list(OPTIONAL_GAME_SYSTEMS)}
    unbekannt = sorted(set(A.COVER_BASIS) - bekannt)
    check("jeder Eintrag in COVER_BASIS ist ein echtes System",
          not unbekannt, "unbekannt: %r" % (unbekannt,))
    check("und die Tabelle ist nicht leer",
          len(A.COVER_BASIS) >= 1, "%d Eintraege" % len(A.COVER_BASIS))

# ---------------------------------------------------------------------------
print()
print("Test 4: das Basis-Spiel erbt nicht von sich selbst")
# ---------------------------------------------------------------------------
# Ohne diese Bremse ruft die Suche nach dem Basis-Spiel die Suche nach
# dem Basis-Spiel, bis der Stapel voll ist. Geprueft wird deshalb
# ZWEIERLEI: dass die Abbruchbedingung im Code steht, UND dass ein
# Aufruf mit dem Namen des Basis-Spiels wirklich zurueckkommt.
with tempfile.TemporaryDirectory() as tmp:
    frisch()
    sysdir = os.path.join(tmp, "SMW_HACKS")
    os.makedirs(sysdir)
    for name in A.COVER_BASIS["SMW_HACKS"]:
        check("das Basis-Spiel selbst erbt nicht (%s)" % name,
              A._basis_cover(tmp, "SMW_HACKS", name) is None)
    # Und ohne vorhandenes Basis-Cover kommt gar nichts - kein Pfad auf
    # eine Datei, die es nicht gibt.
    check("ohne Basis-Cover wird nichts geerbt",
          A._basis_cover(tmp, "SMW_HACKS", "Brutal Mario") is None,
          "ein Pfad ins Leere waere schlimmer als kein Pfad")

_k = nur_code(koerper(_quelle, "_basis_cover"))
check("_basis_cover ruft _art_path_in mit erben=False",
      "erben=False" in _k,
      "sonst ruft die Suche sich selbst")
_ap = nur_code(koerper(_quelle, "_art_path_in"))
check("und _art_path_in kennt den Schalter",
      "erben=True" in _ap.splitlines()[0],
      _ap.splitlines()[0] if _ap else "(nicht gefunden)")

# ---------------------------------------------------------------------------
print()
print("Test 5: der Schalter wirkt")
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    frisch()
    sysdir = os.path.join(tmp, "SMW_HACKS")
    os.makedirs(sysdir)
    basis = os.path.join(sysdir, "Super Mario World (USA).art")
    with open(basis, "wb") as f:
        f.write(b"z" * 16)
    check("mit Schalter AN wird geerbt",
          A._art_path_in(tmp, "SMW_HACKS", "Brutal Mario") == basis)
    A._basis_an = False
    A._basis_cover_cache.clear()
    check("mit Schalter AUS nicht mehr",
          A._art_path_in(tmp, "SMW_HACKS", "Brutal Mario").endswith(
              "Brutal Mario.art"),
          "abschalten muss den Stand von Build 297 zurueckbringen")
    check("und die Kandidatenliste ist dann leer",
          A.cover_basis_namen("SMW_HACKS") == ())
    A._basis_an = True

# Der Menuepunkt und der Schalter muessen zusammengehoeren - ein
# Schalter ohne Menuepunkt ist unerreichbar, ein Menuepunkt ohne
# Handler tut nichts (das war Build 284).
import fe.settings as SE                                 # noqa: E402
check("fe/settings.py hat den Schalter",
      hasattr(SE, "toggle_cover_basis") and hasattr(SE, "cover_basis_an"))
_menu = open(os.path.join(_REPO, "frontend", "fe", "menu.py"),
             encoding="utf-8", errors="replace").read()
check("das Menue zeigt ihn", '"cover_basis"' in nur_code(_menu))
_fe = open(H.FRONTEND_PY, encoding="utf-8", errors="replace").read()
check("und frontend.py behandelt ihn",
      'kind == "cover_basis"' in nur_code(_fe),
      "sonst ein Menuepunkt, der nichts tut")
# Beim Umschalten MUESSEN die Zwischenspeicher fallen, sonst bleibt das
# alte Bild stehen und der Schalter sieht kaputt aus.
_zweig = nur_code(_fe).split('kind == "cover_basis"')[1][:900] \
    if 'kind == "cover_basis"' in nur_code(_fe) else ""
for noetig in ("toggle_cover_basis()", "docs_caches_leeren()",
               "quelldaten_vergessen()", "ART.cache.clear()"):
    check("der Zweig ruft %s" % noetig, noetig in _zweig)

# ---------------------------------------------------------------------------
print()
print("Test 6: die eigene Tabelle des Nutzers")
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    frisch()
    sysdir = os.path.join(tmp, "SNES")
    os.makedirs(sysdir)
    ziel = os.path.join(sysdir, "Super Mario Kart (USA).art")
    with open(ziel, "wb") as f:
        f.write(b"z" * 16)
    tabelle = os.path.join(tmp, "cover_basis.txt")
    with open(tabelle, "w", encoding="utf-8") as f:
        f.write("# eigene Zuordnung\n")
        f.write("SNES = Gibt es nicht | Super Mario Kart\n")
        f.write("kaputte Zeile ohne Gleichheitszeichen\n")
        f.write("\n")
    alt = A.COVER_BASIS_DATEI
    A.COVER_BASIS_DATEI = tabelle
    try:
        A._cover_basis_eigen = None
        A._basis_cover_cache.clear()
        A._art_index_cache.clear()
        check("die Datei wird gelesen",
              A.cover_basis_namen("SNES") ==
              ("Gibt es nicht", "Super Mario Kart"),
              "%r" % (A.cover_basis_namen("SNES"),))
        check("kaputte Zeilen werden uebersprungen",
              "kaputte Zeile ohne Gleichheitszeichen"
              not in A._cover_basis_eigene())
        check("der ZWEITE Kandidat greift, wenn der erste fehlt",
              A._art_path_in(tmp, "SNES", "Irgendein Hack") == ziel,
              "mehrere Kandidaten wegen 'Zelda, The' gegen 'The Zelda'")
        # Die eigene Tabelle gewinnt gegen die mitgelieferte.
        A._cover_basis_eigen = None
        with open(tabelle, "w", encoding="utf-8") as f:
            f.write("SMW_HACKS = Super Mario Kart\n")
        check("die eigene Tabelle gewinnt gegen die mitgelieferte",
              A.cover_basis_namen("SMW_HACKS") == ("Super Mario Kart",),
              "%r" % (A.cover_basis_namen("SMW_HACKS"),))
    finally:
        A.COVER_BASIS_DATEI = alt
        A._cover_basis_eigen = None

# EINE FEHLENDE DATEI IST DER NORMALFALL, nicht ein Fehler.
A.COVER_BASIS_DATEI = os.path.join(tempfile.gettempdir(),
                                   "gibt_es_ganz_sicher_nicht_298.txt")
A._cover_basis_eigen = None
check("ohne Datei bleibt die mitgelieferte Tabelle",
      A.cover_basis_namen("SMW_HACKS") == A.COVER_BASIS["SMW_HACKS"])
check("und die Datei wurde NICHT angelegt",
      not os.path.exists(A.COVER_BASIS_DATEI),
      "wir legen in diesem Projekt keine fremden Dateien an")
A.COVER_BASIS_DATEI = "/media/fat/frontend/cover_basis.txt"
A._cover_basis_eigen = None

# Und im Code darf es keinen Schreibweg auf diese Datei geben.
_fkt = nur_code(koerper(_quelle, "_cover_basis_eigene"))
check("gelesen wird nur",
      '"w"' not in _fkt and "'w'" not in _fkt and "makedirs" not in _fkt)

# ---------------------------------------------------------------------------
print()
print("Test 7: gesucht wird EINMAL je System, nicht je Eintrag")
# ---------------------------------------------------------------------------
# Ohne Zwischenspeicher endet die Suche in einem os.path.exists() JE
# EINTRAG und JE ZEICHNEN - dann waere aus einer Verbesserung ein
# Ruckler geworden, und zwar genau an den Eintraegen, um die es geht.
with tempfile.TemporaryDirectory() as tmp:
    frisch()
    sysdir = os.path.join(tmp, "SMW_HACKS")
    os.makedirs(sysdir)
    with open(os.path.join(sysdir, "Super Mario World (USA).art"), "wb") as f:
        f.write(b"z" * 16)

    echt = os.path.exists
    zaehler = [0]

    def haken(p):
        zaehler[0] += 1
        return echt(p)

    A.os.path.exists = haken
    try:
        # Erster Aufruf darf suchen, danach nicht mehr.
        A._art_path_in(tmp, "SMW_HACKS", "Hack 0")
        erste = zaehler[0]
        zaehler[0] = 0
        for i in range(1, 40):
            A._art_path_in(tmp, "SMW_HACKS", "Hack %d" % i)
        check("der erste Aufruf sieht nach", erste >= 1,
              "%d Zugriffe" % erste)
        check("die naechsten 39 nicht mehr", zaehler[0] == 0,
              "%d Zugriffe - einer je Eintrag waere der Ruckler"
              % zaehler[0])
    finally:
        A.os.path.exists = echt

print()
if fails:
    print("FEHLGESCHLAGEN (%d):" % len(fails))
    for f in fails:
        print("  - %s" % f)
    sys.exit(1)
print("Alles in Ordnung.")