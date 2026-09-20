#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Die einmaligen Metadaten-Ladekosten gehoeren nicht in den Startweg
(Build 165).

DER BEFUND, DER DAZU GEFUEHRT HAT

Ein EINZIGER gemerkter Filter kostete beim Start des Nutzers
gemessene 2218 ms - fast die Haelfte der ganzen Startzeit. Er hatte
recht mit "das ging schonmal schneller": langsamer wurde es nicht
durch einen Build, sondern in dem Moment, in dem er seinen ersten
Filter gespeichert hat.

Die Filterarbeit selbst ist es nicht. Nachgemessen mit 1800 Spielen:
get_meta() + FILTER.passt() zusammen 8 ms, auch im schlechtesten
Fall (kein Name trifft exakt, der Ausweich-Index muss gebaut werden).
Uebrig bleiben die drei einmaligen Ladevorgaenge, die der ERSTE
get_meta()-Aufruf fuer ein System ausloest:

    1. meta/<system>.json einlesen
    2. gameinfo.tsv der fremden Datenbank suchen und einlesen
    3. deren Ausweich-Index bauen

metadaten_vorwaermen() macht genau diese drei Schritte - damit sie in
einem Hintergrund-Thread passieren koennen, waehrend die Spieleliste
eingelesen wird, statt im Startweg.

WAS DIESER TEST PRUEFT

1. Vorwaermen laedt tatsaechlich alle drei Sachen (danach ist der
   erste get_meta()-Aufruf billig).
2. Es liefert drei getrennte Zeiten - eine Sammelzahl haette uns
   beim letzten Mal wieder nicht gesagt, welcher Schritt es war.
3. Es aendert nichts am ERGEBNIS: dieselben Metadaten wie ohne.
4. Ein fehlendes System, ein leerer Schluessel und eine kaputte
   Tabelle werfen nichts um - das laeuft in einem Thread, ein
   Fehler dort darf den Start nicht kosten.

Ausfuehren:
    python3 tools/test_vorwaermen.py
"""
import io
import json
import os
import shutil
import sys
import tempfile

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
sys.path.insert(0, os.path.join(_REPO, "frontend"))

import fe.art as art                                     # noqa: E402
import fe.filter as FILTER                               # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


N = 400
_tmp = tempfile.mkdtemp(prefix="test_vorwaermen_")
META = os.path.join(_tmp, "meta")
DOCS = os.path.join(_tmp, "docs")
os.makedirs(META)
os.makedirs(os.path.join(DOCS, "SNES"))

NAMEN = ["Spiel %03d (USA)" % i for i in range(N)]

art.META_BASE = META
art.DOCS_BASE = DOCS
art.FREMD_ZUSATZ_WURZELN = []

# Eigene Tabelle: nur die erste Haelfte.
io.open(os.path.join(META, "SNES.json"), "w", encoding="utf-8").write(
    json.dumps({n: {"year": "1992", "genre": "Platform", "players": "2"}
                for n in NAMEN[:N // 2]}))

# Fremde Tabelle: alle, mit Entwickler (den unsere Quelle nicht kennt).
with io.open(os.path.join(DOCS, "SNES", "gameinfo.tsv"), "w",
             encoding="utf-8") as fh:
    fh.write("#key\tname\tyear\tgenre\tdeveloper\tplayers\n")
    for n in NAMEN:
        fh.write("%s\t%s\t1993\tShooter\tNintendo\t1\n" % (n, n))


def frisch():
    """Alle Caches leeren - wie beim Programmstart."""
    art.docs_caches_leeren()
    art._meta_cache.clear()
    art._fremd_an = True


# ---------------------------------------------------------------------------
print("Test 1: nach dem Vorwaermen ist alles geladen")
# ---------------------------------------------------------------------------
frisch()
check("vorher ist die eigene Tabelle NICHT geladen",
      "SNES" not in art._meta_cache)
check("vorher ist die fremde Tabelle NICHT geladen",
      "SNES" not in art._docs_info_cache)

eigen, fremd, index = art.metadaten_vorwaermen("SNES")

check("danach ist die eigene Tabelle geladen", "SNES" in art._meta_cache)
check("danach ist die fremde Tabelle geladen",
      "SNES" in art._docs_info_cache)
check("danach steht auch der Ausweich-Index",
      "SNES" in art._docs_info_knapp)
check("der Index hat so viele Eintraege wie die Tabelle",
      len(art._docs_info_knapp.get("SNES", {})) == N,
      "%d von %d" % (len(art._docs_info_knapp.get("SNES", {})), N))

# ---------------------------------------------------------------------------
print()
print("Test 2: drei getrennte Zeiten, keine Sammelzahl")
# ---------------------------------------------------------------------------
check("drei Werte zurueck", isinstance((eigen, fremd, index), tuple)
      and len((eigen, fremd, index)) == 3)
check("alle drei sind Zahlen >= 0",
      all(isinstance(x, float) and x >= 0.0 for x in (eigen, fremd, index)),
      "%.2f / %.2f / %.2f ms" % (eigen, fremd, index))
# Wenn wirklich etwas geladen wurde, kann nicht alles exakt 0 sein.
check("mindestens einer der drei hat messbar gedauert",
      (eigen + fremd + index) > 0.0)

# ---------------------------------------------------------------------------
print()
print("Test 3: das Ergebnis bleibt dasselbe wie ohne Vorwaermen")
# ---------------------------------------------------------------------------
frisch()
ohne = [art.get_meta("SNES", n) for n in NAMEN]
frisch()
art.metadaten_vorwaermen("SNES")
mit = [art.get_meta("SNES", n) for n in NAMEN]
check("alle %d Eintraege identisch" % N, ohne == mit)
# Und der Inhalt stimmt auch inhaltlich: eigene Angabe gewinnt,
# der Entwickler kommt aus der fremden Tabelle dazu.
check("eigene Angabe gewinnt (year 1992, nicht 1993)",
      mit[0].get("year") == "1992", str(mit[0]))
check("fremdes Feld fuellt die Luecke (developer)",
      mit[0].get("developer") == "Nintendo", str(mit[0]))
check("ohne eigene Angabe gilt die fremde ganz",
      mit[-1].get("year") == "1993" and mit[-1].get("genre") == "Shooter",
      str(mit[-1]))

# ---------------------------------------------------------------------------
print()
print("Test 4: der zweite Zugriff ist billig - das ist der ganze Sinn")
# ---------------------------------------------------------------------------
import time                                              # noqa: E402
frisch()
t0 = time.perf_counter()
art.get_meta("SNES", NAMEN[0])
kalt = (time.perf_counter() - t0) * 1000.0
t0 = time.perf_counter()
art.get_meta("SNES", NAMEN[1])
warm = (time.perf_counter() - t0) * 1000.0
check("der erste Zugriff kostet deutlich mehr als der zweite",
      kalt > warm * 5, "kalt %.3f ms, warm %.3f ms" % (kalt, warm))

frisch()
art.metadaten_vorwaermen("SNES")
t0 = time.perf_counter()
art.get_meta("SNES", NAMEN[0])
nach_warm = (time.perf_counter() - t0) * 1000.0
check("nach dem Vorwaermen ist auch der ERSTE Zugriff billig",
      nach_warm < kalt / 2.0,
      "kalt %.3f ms, nach Vorwaermen %.3f ms" % (kalt, nach_warm))

# ---------------------------------------------------------------------------
print()
print("Test 5: nichts davon darf etwas umwerfen")
# ---------------------------------------------------------------------------
frisch()
check("leerer Schluessel", art.metadaten_vorwaermen("") == (0.0, 0.0, 0.0))
check("None als Schluessel", art.metadaten_vorwaermen(None) == (0.0, 0.0, 0.0))

frisch()
werte = art.metadaten_vorwaermen("GIBTESNICHT")
check("unbekanntes System liefert trotzdem drei Zahlen",
      len(werte) == 3 and all(isinstance(x, float) for x in werte))
check("unbekanntes System laedt nichts Fremdes",
      not art._docs_info_cache.get("GIBTESNICHT"))

# Kaputte Tabelle: kein Tab, halbe Zeilen, ungueltiges UTF-8.
os.makedirs(os.path.join(DOCS, "NES"))
with io.open(os.path.join(DOCS, "NES", "gameinfo.tsv"), "wb") as fh:
    fh.write(b"#key\tname\n\xff\xfe kaputt\nnur ein feld\n\n\t\t\t\n")
io.open(os.path.join(META, "NES.json"), "w", encoding="utf-8").write(
    "{das ist kein JSON")
frisch()
try:
    werte = art.metadaten_vorwaermen("NES")
    ok = len(werte) == 3
except Exception as e:                                   # noqa: BLE001
    ok = False
    print("    Ausnahme:", e)
check("kaputte Tabelle und kaputtes JSON werfen nichts", ok)
check("danach liefert get_meta() einfach nichts",
      art.get_meta("NES", "Irgendwas (USA)") == {})

# ---------------------------------------------------------------------------
print()
print("Test 6: der Aufrufer im Frontend waermt die richtigen Systeme vor")
# ---------------------------------------------------------------------------
# Kein Start des ganzen Frontends - geprueft wird die Zuordnung
# Kategoriename -> Systemschluessel, die _metadaten_vorwaermen_starten()
# benutzt. Sie muss sowohl den ANZEIGENAMEN ("Mega Drive") als auch den
# Schluessel selbst ("Genesis") treffen, weil in der gemerkten Datei der
# Anzeigename steht.
from fe.systems import GAME_SYSTEMS, OPTIONAL_GAME_SYSTEMS  # noqa: E402
namen = {}
for eintrag in list(GAME_SYSTEMS) + list(OPTIONAL_GAME_SYSTEMS):
    namen.setdefault(eintrag[0], eintrag[1])
    namen.setdefault(eintrag[1], eintrag[1])
check("'SNES' -> SNES", namen.get("SNES") == "SNES")
check("'Mega Drive' -> Genesis", namen.get("Mega Drive") == "Genesis")
check("'PlayStation' -> PSX", namen.get("PlayStation") == "PSX")
check("'Arcade' hat keinen Systemschluessel (wird uebersprungen)",
      namen.get("Arcade") is None)
check("'Favoriten' hat keinen (wird uebersprungen)",
      namen.get("Favoriten") is None)

quelltext = io.open(os.path.join(_REPO, "frontend", "frontend.py"),
                    encoding="utf-8").read()


def methode(name):
    """Den Rumpf EINER Methode herausschneiden - damit die Pruefungen
    unten sich auf die richtige Stelle beziehen und nicht auf
    irgendein gleichlautendes Stueck woanders in der Datei.

    (Build 164 hat genau daran eine rote Ampel bekommen: ein Test
    verglich mit einer woertlichen Quelltextzeile und ging bei einem
    reinen Umbau kaputt, obwohl das Verhalten stimmte.)"""
    anfang = quelltext.index("    def %s(self" % name)
    rest = quelltext[anfang + 10:]
    ende = rest.index("\n    def ")
    return rest[:ende]


rumpf = methode("_metadaten_vorwaermen_starten")
check("der Thread laeuft als daemon (darf das Beenden nie aufhalten)",
      "daemon=True" in rumpf)
check("er startet auch wirklich", ".start()" in rumpf)
check("ohne gemerkte Filter wird gar kein Thread gestartet",
      "if not gemerkte:" in rumpf and "return" in rumpf)
check("die Filterschleife wartet vorher auf den Thread",
      "_auf_vorwaermen_warten()" in methode("build_categories"))

# Reihenfolge im Start: erst den Thread anwerfen, dann die Marke,
# dann erst die Spieleliste - nur so hat er die Scan-Zeit fuer sich.
i_start = quelltext.index("self._metadaten_vorwaermen_starten()")
i_marke = quelltext.index('self._startmarke("Musik, RA-Abruf angestossen")')
i_bauen = quelltext.index("self.build_categories()\n        "
                          'self._startmarke("Spieleliste eingelesen")')
check("der Thread startet VOR dem Einlesen der Spieleliste",
      i_start < i_marke < i_bauen)

shutil.rmtree(_tmp, ignore_errors=True)

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
