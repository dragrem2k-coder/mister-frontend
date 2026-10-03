#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft den unscharfen Namensabgleich und das Nachzieh-Netz fuer
spaet anlaufende Laufwerke (Build 117).

BEIDES KAM AUS DERSELBEN URSACHE. Der Nutzer hat eine andere
USB-Festplatte angeschlossen, und daraufhin fiel zweierlei auf:

  1. "bei jedem Frontendstart wird versucht, die Spieleliste neu
     aufzubauen, ich muss immer erst unter Wartung von Hand neu
     einlesen" - die Platte laeuft langsamer an als die alte.
  2. "bei N64 und Sega 32X werden mir keine Boxarts mehr angezeigt".

Der zweite Punkt sah nach einem Fehler in einem der letzten Builds
aus, war aber keiner. Die ROMs auf der neuen Platte tragen die alte
GoodTools-Schreibweise:

    007 - The World is Not Enough (U) [!]

die heruntergeladenen Cover die No-Intro-Schreibweise:

    007 - The World Is Not Enough (USA).art

Zeichenweise passt davon nichts zusammen - nicht einmal das "is"
gegen "Is". Genau dafuer gibt es jetzt vergleichsname().

WORAUF ES BEI DEM ABGLEICH ANKOMMT: er darf nur einspringen, wenn der
exakte Name nichts gefunden hat, und er darf keine VERSCHIEDENEN
Spiele zusammenwerfen. Beides wird hier geprueft.

Ausfuehren:
    python3 tools/test_namensabgleich.py
"""
import os
import shutil
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)

import _harness as H                                    # noqa: E402,F401

sys.path.insert(0, os.path.join(_REPO, "frontend"))
import fe.art as A                                      # noqa: E402
import fe.paths as FP
import fe.scan as S                                     # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


print("Test 1: die echten Namenspaare vom Geraet finden zusammen")
paare = [
    ("007 - The World is Not Enough (U) [!]",
     "007 - The World Is Not Enough (USA)"),
    ("AeroFighters Assault (U) [!]", "AeroFighters Assault (USA)"),
    ("1080 Snowboarding (JU) (M2) [!]", "1080 Snowboarding (USA)"),
    ("Mortal Kombat II 32X (JUE) (Dec 1994) [!]",
     "Mortal Kombat II 32X (JUE)"),
    ("Knuckles Chaotix 32X (5) [!]", "Knuckles Chaotix 32X (USA)"),
]
for rom, cover in paare:
    check("%-40s = %s" % (rom[:40], cover[:34]),
          A.vergleichsname(rom) == A.vergleichsname(cover),
          "%r vs %r" % (A.vergleichsname(rom), A.vergleichsname(cover)))

print()
print("Test 2: verschiedene Spiele bleiben verschieden")
# Der eigentliche Preis des unscharfen Vergleichs waere, wenn er zu
# viel zusammenwirft. Diese Paare MUESSEN auseinanderbleiben.
getrennt = [
    ("Super Mario 64 (U) [!]", "Super Mario World (USA)"),
    ("Mortal Kombat (USA)", "Mortal Kombat II (USA)"),
    ("Zelda - Ocarina of Time (USA)", "Zelda - Majora's Mask (USA)"),
    ("F-Zero X (USA)", "F-Zero (USA)"),
]
for a, b in getrennt:
    check("%-32s != %s" % (a[:32], b[:30]),
          A.vergleichsname(a) != A.vergleichsname(b),
          A.vergleichsname(a))

print()
print("Test 3: Sonderfaelle des Vergleichsnamens")
check("Klammern verschwinden mitsamt Inhalt",
      A.vergleichsname("Spiel (USA) (Rev A) [!]") == "SPIEL",
      A.vergleichsname("Spiel (USA) (Rev A) [!]"))
check("Satzzeichen verschwinden",
      A.vergleichsname("Knuckles' Chaotix - 32X!") == "KNUCKLESCHAOTIX32X",
      A.vergleichsname("Knuckles' Chaotix - 32X!"))
check("verschachtelte Klammern",
      A.vergleichsname("Spiel (USA (Rev)) Extra") == "SPIELEXTRA",
      A.vergleichsname("Spiel (USA (Rev)) Extra"))
check("eine Klammer ohne Ende frisst nicht den Rest",
      A.vergleichsname("Spiel )USA( Extra") == "SPIELUSA",
      A.vergleichsname("Spiel )USA( Extra"))
check("ein Name, der nur aus Klammern besteht, ergibt nichts",
      A.vergleichsname("(USA)") == "", A.vergleichsname("(USA)"))
check("Umlaute bleiben erhalten",
      A.vergleichsname("Grün (D)") == "GRÜN", A.vergleichsname("Grün (D)"))

print()
print("Test 4: der exakte Name gewinnt IMMER")
tmp = tempfile.mkdtemp(prefix="namen_")
_alt_docs = A.DOCS_BASE
try:
    A.DOCS_BASE = os.path.join(tmp, "keine_docs")
    eigen = os.path.join(tmp, "art_hd")
    os.makedirs(os.path.join(eigen, "N64"))
    # Zwei Dateien, die denselben Vergleichsnamen ergeben, und eine
    # davon heisst exakt wie das ROM.
    for f in ("Spiel (U) [!].art", "Spiel (USA).art",
              "007 - The World Is Not Enough (USA).art"):
        open(os.path.join(eigen, "N64", f), "wb").write(b"ART1")
    A.docs_caches_leeren()
    A._art_index_cache.clear()
    p = A._art_path_in(eigen, "N64", "Spiel (U) [!]")
    check("exakter Treffer wird genommen",
          os.path.basename(p) == "Spiel (U) [!].art", p)
    p = A._art_path_in(eigen, "N64", "007 - The World is Not Enough (U) [!]")
    check("sonst der unscharfe Treffer",
          os.path.basename(p) == "007 - The World Is Not Enough (USA).art", p)
    p = A._art_path_in(eigen, "N64", "Voellig Anderes Spiel (U)")
    check("und ohne jeden Treffer der bisherige Rueckfall",
          p.endswith("Voellig Anderes Spiel (U).art"), p)
    # Bei zwei gleichwertigen Kandidaten muss die Wahl STABIL sein -
    # os.listdir() liefert keine verlaessliche Reihenfolge.
    erste = A._art_path_in(eigen, "N64", "Spiel [!]")
    for _ in range(5):
        A._art_index_cache.clear()
        check2 = A._art_path_in(eigen, "N64", "Spiel [!]")
        if check2 != erste:
            erste = None
            break
    check("bei mehreren Kandidaten immer derselbe", erste is not None,
          "%s" % (os.path.basename(erste) if erste else "wechselt!"))

    print()
    print("Test 5: auch die fremde Datenbank findet anders benannte ROMs")
    docs = os.path.join(tmp, "docs")
    os.makedirs(os.path.join(docs, "N64", "Artwork"))
    open(os.path.join(docs, "N64", "Artwork",
                      "Blast Corps (USA).jpg"), "wb").write(b"x")
    with open(os.path.join(docs, "N64", "Artwork", "gameinfo.tsv"),
              "w", encoding="utf-8") as fh:
        fh.write("#key\tname\tyear\tgenre\tdeveloper\tplayers\n")
        fh.write("Blast Corps (USA)\tBlast Corps\t1997\tAction\tRare\t1\n")
    A.DOCS_BASE = docs
    A.docs_caches_leeren()
    check("Cover trotz GoodTools-Namen gefunden",
          A.docs_cover("N64", "Blast Corps (U) [!]") is not None)
    check("und die Spieledaten ebenso",
          A.docs_meta("N64", "Blast Corps (U) [!]").get("year") == "1997",
          "%r" % (A.docs_meta("N64", "Blast Corps (U) [!]"),))
    check("was es nicht gibt, gibt es weiterhin nicht",
          A.docs_cover("N64", "Gibt Es Nicht (U)") is None)
finally:
    A.DOCS_BASE = _alt_docs
    A.docs_caches_leeren()
    A._art_index_cache.clear()
    shutil.rmtree(tmp, ignore_errors=True)

print()
print("Test 6: spaet angelaufenes Laufwerk wird bemerkt")
# Ohne vorheriges Einlesen darf NICHTS ausgeloest werden - sonst
# zoege das Frontend beim allerersten Start sofort nach.
S._LETZTE_ORDNER = set()
check("ohne vorheriges Einlesen passiert nichts",
      S.ordner_sind_dazugekommen() is False)

S.ordner_merken([("usb:SNES", 111), ("fat:NES", 222),
                 ("__scan_logic_version__", 3)])
check("die Sondereintraege stehen nicht im Merker",
      all(":" in k for k in S._LETZTE_ORDNER), "%r" % (S._LETZTE_ORDNER,))
check("aber die echten Ordner schon",
      S._LETZTE_ORDNER == {"usb:SNES", "fat:NES"}, "%r" % (S._LETZTE_ORDNER,))

echt = S._games_signature
# GEAENDERT (Build 224): vor jeder Frage die Selbstsperre loesen.
# ordner_sind_dazugekommen() merkt sich seine Antwort acht Sekunden lang
# (siehe dort - im Bericht des Nutzers stand sie mit 20,9 Zugriffen JE
# SCROLLSCHRITT). Dieser Test prueft die ERKENNUNG, nicht die Sperre;
# dass es sie gibt, prueft tools/test_negativ_merken.py.
# GEAENDERT (Build 229): der Fingerabdruck laeuft jetzt NEBENHER.
# ordner_sind_dazugekommen() stoesst nur noch an und liefert sofort die
# zuletzt bekannte Antwort - genau deswegen haengt das Umschalten der
# Kategorie nicht mehr. Ein Test, der die ERKENNUNG prueft, braucht
# aber ein Ergebnis: also anstossen, abwarten, dann fragen.
def _frisch():
    S.dazu_fertig_abwarten()            # einen alten Faden auslaufen lassen
    S.dazu_sperre_loesen()
    # Build 230: die billige Vorfrage ueberspringen. Sie prueft, ob sich
    # an den Basispfaden etwas geruehrt hat; hier wird die ERKENNUNG
    # geprueft, und die Vorfrage hat ihren eigenen Abschnitt weiter
    # unten. None ist nie gleich einem Tupel - also laeuft der Durchgang.
    S._LETZTE_BASEN = None
    S.ordner_sind_dazugekommen()        # stoesst den neuen an
    assert S.dazu_fertig_abwarten(), "Hintergrundfaden haengt"
    return S._DAZU_WERT


try:
    S._games_signature = lambda: ([("usb:SNES", 999), ("fat:NES", 222)], {})
    check("ein NEUER Zeitstempel allein loest nichts aus",
          _frisch() is False)
    S._games_signature = lambda: ([("usb:SNES", 111)], {})
    check("ein WEGGEFALLENER Ordner loest auch nichts aus",
          _frisch() is False)
    S._games_signature = lambda: ([("usb:SNES", 111), ("fat:NES", 222),
                                   ("usb:N64", 333)], {})
    check("ein DAZUGEKOMMENER Ordner loest aus",
          _frisch() is True)
    # Die Abfrage darf den NAS-Merker nicht ueberschreiben - er
    # beschreibt das letzte echte Einlesen, nicht diese Zwischenfrage.
    S._LETZTE_SIGNATUR_MIT_NAS = True
    S._games_signature = lambda: ([("usb:SNES", 111)], {})
    _frisch()
    check("der NAS-Merker bleibt unangetastet",
          S.letzter_scan_hatte_nas() is True)
    S._LETZTE_SIGNATUR_MIT_NAS = False
    # Und ein Fehler beim Nachsehen darf nichts umwerfen.
    def _kaputt():
        raise OSError("Laufwerk weg")
    S._games_signature = _kaputt
    check("ein Fehler beim Nachsehen wirft nichts um",
          _frisch() is False)
finally:
    S._games_signature = echt
    S._LETZTE_ORDNER = set()

print()
print("Test 7: das Sicherheitsnetz benutzt es auch")
quelle = open(os.path.join(_REPO, "frontend", "frontend.py"),
              encoding="utf-8", errors="replace").read()
check("die Abfrage ist verdrahtet",
      "elif ordner_sind_dazugekommen():" in quelle)
# NEU (Build 229): und sie RECHNET im Zeichenweg nichts mehr. Der
# Fingerabdruck laeuft in einem eigenen Faden; der Aufrufer bekommt die
# zuletzt bekannte Antwort. Das ist der Unterschied zwischen "selten
# teuer" (Build 224) und "nie teuer" - und nur Letzteres loest den
# Haenger beim Kategoriewechsel, den der Nutzer gemeldet hat.
_qs = open(os.path.join(_REPO, "frontend", "fe", "scan.py"),
           encoding="utf-8").read()
_rumpf = _qs.split("def ordner_sind_dazugekommen")[1].split("\ndef ")[0]
# ---------------------------------------------------------------------------
# DIE BILLIGE VORFRAGE (Build 230)
# ---------------------------------------------------------------------------
# Build 229 hat den Fingerabdruck in einen eigenen Faden gelegt. Der
# Bericht vom 03.10., 10:43, zeigte, dass das nicht reichte: REST fiel
# von 14,04 auf 6,83 ms, aber "cover 1.91 (davon Karte 19.68 in 22
# Zugriffen)" - vorher 2,83 ms fuer dieselben Zugriffe. Die Arbeit lag
# nur nebenan und stritt sich mit dem Zeichenweg um die Karte.
#
# Jetzt wird vorher gefragt, ob sich an den Basispfaden ueberhaupt etwas
# geruehrt hat - eine Handvoll stat-Aufrufe statt rund sechshundert.
_zaehler = {"n": 0}
_echt_sig = S._games_signature


def _gezaehlt():
    _zaehler["n"] += 1
    return ([("usb:SNES", 1)], {})


try:
    S._games_signature = _gezaehlt
    # Nicht leer: ohne ein vorheriges Einlesen steigt
    # ordner_sind_dazugekommen() gleich zu Beginn aus - es gaebe nichts
    # zu vergleichen.
    S._LETZTE_ORDNER = {"fat:NES"}
    S.dazu_fertig_abwarten()
    # Gleiches Merkmal -> gar kein Durchgang.
    S._LETZTE_BASEN = S._basen_merkmal()
    S.dazu_sperre_loesen()
    S.ordner_sind_dazugekommen()
    S.dazu_fertig_abwarten()
    check("ruehrt sich an den Basispfaden nichts, wird NICHT gesucht",
          _zaehler["n"] == 0,
          "%d Durchgaenge - genau das waren die 630 stat-Aufrufe"
          % _zaehler["n"])
    # Anderes Merkmal -> jetzt lohnt der teure Blick.
    S._LETZTE_BASEN = (("/gibt/es/nicht", 1),)
    S.dazu_sperre_loesen()
    S.ordner_sind_dazugekommen()
    S.dazu_fertig_abwarten()
    check("hat sich etwas geruehrt, wird gesucht",
          _zaehler["n"] == 1, "%d Durchgaenge" % _zaehler["n"])
finally:
    S._games_signature = _echt_sig
    S._LETZTE_BASEN = ()
    S.dazu_sperre_loesen()

check("das Merkmal sind nur die Basispfade",
      len(S._basen_merkmal()) <= len(FP.GAMES_BASES),
      "%d Pfade - nicht jeder Systemordner darunter"
      % len(FP.GAMES_BASES))
check("und es wird beim Einlesen mitgemerkt",
      "_LETZTE_BASEN = _basen_merkmal()" in _qs,
      "sonst vergleicht die eine Haelfte mit einem Stand, den die "
      "andere nie gesehen hat")

check("der Fingerabdruck laeuft NEBENHER",
      "_threading.Thread(target=_dazu_nachsehen" in _rumpf,
      "sonst haengt der Zeichenweg an os.stat je Systemordner")
check("und wird im Zeichenweg nicht mehr gerechnet",
      "_games_signature()" not in _rumpf,
      "genau diese Zeile stand im Bericht mit 20,9 Zugriffen je Schritt")
check("der Faden ist ein Daemon",
      "daemon=True" in _rumpf,
      "er darf das Beenden des Frontends nicht aufhalten")
check("und ein fehlgeschlagener Start haelt nichts auf",
      "except RuntimeError:" in _rumpf)
check("der Netzlaufwerk-Weg bleibt bestehen",
      "if _has_network_mount():" in quelle
      and "letzter_scan_hatte_nas():" in quelle)
check("und beide muenden in denselben einmaligen Nachzug",
      quelle.count("self._late_mount_rescan_pending = True") >= 2
      and "self._late_mount_rescan_done = True\n        self."
          "_rebuild_categories_preserving_selection(force_rescan=True)"
          in quelle)
skript = open(os.path.join(_REPO, "frontend", "fe", "scan.py"),
              encoding="utf-8", errors="replace").read()
check("und der Merker wird beim Einlesen gesetzt",
      skript.count("ordner_merken(sig)") >= 3,
      "%d Stellen" % skript.count("ordner_merken(sig)"))

print()
if fails:
    print("FEHLGESCHLAGEN (%d):" % len(fails))
    for f_ in fails:
        print("  -", f_)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
