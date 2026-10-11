#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Die vier Kleinigkeiten an der Liste (Build 256).

Scrollgeschwindigkeit als Zahl, Ordner vor oder hinter den Spielen,
Favoriten zuerst, Spielzahl am Ordner - dazu das Ausblenden einzelner
Eintraege. Die Ideen stammen aus einem Blick auf Degauss, der Code
nicht (Degauss steht unter PolyForm Noncommercial, keine freie
Lizenz).

WORAN ES SCHEITERN KANN - und das sind die Punkte, an denen dieser
Test haengt:

  1. DER SCHNELLE WEG GEHT VERLOREN. _liste_anpassen() liegt im
     Zeichenweg. Wer nichts einstellt, muss die Liste unveraendert
     und OHNE Kopie zurueckbekommen - sonst kostet eine Einstellung,
     die niemand benutzt, bei jedem Bildaufbau eine neue Liste.
  2. DER MERKER MERKT ZU VIEL. Haengt er nicht an einem Zaehler, der
     sich bei jedem Favoriten- und Ausblend-Wechsel dreht, bleibt die
     Liste stehen, wie sie war - und zwar still.
  3. DIE ORDNERZAHL WIRD JE BILD GEZAEHLT. Ein Ordner mit 30.000
     Eintraegen bedeutet dann einen vollstaendigen Baumdurchlauf pro
     Zeile und Bild.
  4. DAS SCROLL-TEMPO WIRD SCHNELLER ALS DAS GERAET ZEICHNET. Genau
     daran ist Build 93 gescheitert: der Ueberschuss staut sich, die
     Liste laeuft nach dem Loslassen weiter. Der Faktor darf nach
     unten frei wirken, nach oben nur bis zur gemessenen Zeit.
  5. AUSBLENDEN LOESCHT ETWAS. Es darf ausschliesslich eine eigene
     Datei entstehen; auf der Karte wird nichts angefasst.

Ausfuehren:
    python3 tools/test_listen_kleinzeug.py
"""
import io
import os
import shutil
import sys
import tempfile

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
sys.path.insert(0, os.path.join(_REPO, "frontend"))

fails = []
_TMP = tempfile.mkdtemp(prefix="kleinzeug_")


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


# ---------------------------------------------------------------------------
print("Test 1: die Einstellungen selbst")
# ---------------------------------------------------------------------------
import fe.settings as S                                    # noqa: E402

# Die Dateien zeigen in den Spielbereich, nicht auf die echte Karte.
for name in ("SCROLL_TEMPO_FILE", "ORDNER_HINTEN_FLAG",
             "FAVORITEN_ZUERST_FLAG", "ORDNER_ZAHLEN_AUS_FLAG"):
    setattr(S, name, os.path.join(_TMP, name.lower()))

check("Vorgabe Scrolltempo ist 1.0", S.load_scroll_tempo() == 1.0,
      str(S.load_scroll_tempo()))
check("Vorgabe: Ordner zuerst", S.ordner_zuerst() is True)
check("Vorgabe: Favoriten zuerst AUS", S.favoriten_zuerst() is False,
      "wer seine Liste alphabetisch kennt, soll sie nicht umsortiert "
      "vorfinden")
check("Vorgabe: Ordnerzahlen AN", S.ordner_zahlen_an() is True)

_start = S.load_scroll_tempo()
stufen = [S.cycle_scroll_tempo() for _ in range(len(S.SCROLL_TEMPO_STUFEN))]
# EINMAL HERUM SIND GENAU SO VIELE SCHRITTE WIE STUFEN - danach muss
# wieder der Ausgangswert stehen. (Der erste Entwurf dieser Pruefung
# endete auf "or True" und war damit keine Pruefung, sondern eine
# Zeile, die immer gruen ist. Gefunden beim Durchlesen des eigenen
# Tests, nicht beim Ausfuehren - ein Test, der nicht scheitern kann,
# sagt nichts.)
check("einmal herum landet wieder am Anfang",
      stufen[-1] == _start, "%s -> %s" % (_start, stufen[-1]))
check("und unterwegs kommt jede Stufe genau einmal vor",
      sorted(stufen) == sorted(S.SCROLL_TEMPO_STUFEN), str(stufen))
# Eine von Hand verstellte Datei darf die Bedienung nicht kaputtmachen.
with io.open(S.SCROLL_TEMPO_FILE, "w", encoding="utf-8") as fh:
    fh.write("99")
from fe.zwischenspeicher import vergessen as _vergessen    # noqa: E402
_vergessen()
check("ein unsinniger Wert in der Datei faellt auf die Vorgabe zurueck",
      S.load_scroll_tempo() == S.SCROLL_TEMPO_STD,
      "sonst steht die Liste bei 99x still oder rast")

for an, aus, name in ((S.toggle_ordner_zuerst, S.ordner_zuerst, "Ordner"),
                      (S.toggle_favoriten_zuerst, S.favoriten_zuerst,
                       "Favoriten zuerst"),
                      (S.toggle_ordner_zahlen, S.ordner_zahlen_an,
                       "Ordnerzahlen")):
    vorher = aus()
    an()
    nachher = aus()
    an()
    check("%s laesst sich umschalten und zurueck" % name,
          nachher is not vorher and aus() is vorher)

# ---------------------------------------------------------------------------
print()
print("Test 2: das Scroll-Tempo wird nie schneller als das Geraet")
# ---------------------------------------------------------------------------
# DAS IST DIE WICHTIGSTE ZUSAGE DIESES BUILDS. Build 93 hat gezeigt,
# was passiert, wenn man mehr Wiederholungen anfordert, als das Bild
# hergibt: die Warteschlange laeuft nach dem Loslassen weiter.
import fe.input as INP                                     # noqa: E402

mgr = INP.InputManager.__new__(INP.InputManager)
mgr._zeichenzeit = {}
mgr.seiten_aktionen = INP.PAGE_ACTIONS

GEMESSEN = 0.10          # das Geraet braucht 100 ms je Bild
mgr._zeichenzeit = {INP.REPEAT_AXIS.get("down"): GEMESSEN}

S.cycle_scroll_tempo()   # irgendeine Stufe
for ziel in S.SCROLL_TEMPO_STUFEN:
    with io.open(S.SCROLL_TEMPO_FILE, "w", encoding="utf-8") as fh:
        fh.write("%g" % ziel)
    _vergessen()
    boden = mgr._repeat_floor("down")
    if ziel < 1.0:
        check("Stufe %gx ist langsamer als 1x" % ziel,
              boden > GEMESSEN * INP.REPEAT_MESS_RESERVE - 1e-9,
              "%.3f s" % boden)
    check("Stufe %gx bleibt bei >= der gemessenen Zeit" % ziel,
          boden >= GEMESSEN - 1e-9,
          "%.3f s gegen gemessene %.3f s - schneller anfordern, als "
          "gezeichnet wird, war genau der Fehler aus Build 93"
          % (boden, GEMESSEN))
    check("Stufe %gx bleibt unter der Notbremse" % ziel,
          boden <= INP.REPEAT_FLOOR_MAX + 1e-9, "%.3f s" % boden)

with io.open(S.SCROLL_TEMPO_FILE, "w", encoding="utf-8") as fh:
    fh.write("1")
_vergessen()
check("bei 1x kommt genau der alte Wert heraus",
      abs(mgr._repeat_floor("down")
          - min(INP.REPEAT_FLOOR_MAX,
                max(INP.REPEAT_FLOOR_MIN,
                    GEMESSEN * INP.REPEAT_MESS_RESERVE))) < 1e-9,
      "wer nichts einstellt, darf nichts merken")

# Ohne Messung (erster Tastendruck nach dem Start) muss es ebenfalls
# gehen - dort gibt es keine Untergrenze aus einer Messung.
mgr._zeichenzeit = {}
with io.open(S.SCROLL_TEMPO_FILE, "w", encoding="utf-8") as fh:
    fh.write("2")
_vergessen()
ohne = mgr._repeat_floor("down")
check("auch ohne Messung bleibt es in den Grenzen",
      INP.REPEAT_FLOOR_MIN - 1e-9 <= ohne <= INP.REPEAT_FLOOR_MAX + 1e-9,
      "%.3f s" % ohne)

# ---------------------------------------------------------------------------
print()
print("Test 3: ausgeblendete Eintraege")
# ---------------------------------------------------------------------------
import fe.versteckt as V                                   # noqa: E402

pfad = os.path.join(_TMP, "versteckt.json")
check("am Anfang ist nichts ausgeblendet", V.liste(pfad) == [])
V.umschalten("SNES", "Super Mario World", pfad)
V.umschalten("SNES", "Hacks", pfad)
V.umschalten("NES", "", pfad)
check("drei Eintraege gemerkt", V.anzahl(pfad) == 3, str(V.liste(pfad)))
daten = V.laden(pfad)
check("ein Spiel wird erkannt",
      V.ist_versteckt("SNES", "Super Mario World", daten))
check("ein anderes nicht", not V.ist_versteckt("SNES", "F-Zero", daten))
check("ein ganzes System wird erkannt", V.system_versteckt("NES", daten))
check("umschalten holt es zurueck",
      V.umschalten("SNES", "Hacks", pfad) is False
      and V.anzahl(pfad) == 2)
check("alles zeigen raeumt auf",
      V.alles_zeigen(pfad) == 2 and V.liste(pfad) == [])

# Geschrieben wird atomar - ein Stromausfall darf keine halbe Datei
# hinterlassen, und eine halbe Datei wuerde ALLE Ausblendungen kosten.
_q = io.open(os.path.join(_REPO, "frontend", "fe", "versteckt.py"),
             encoding="utf-8").read()
check("geschrieben wird per .tmp + os.replace()",
      '".tmp"' in _q and "os.replace(" in _q)
check("eine kaputte Datei kostet nicht alles, sondern liefert leer",
      V.laden(os.path.join(_REPO, "tools", "test_listen_kleinzeug.py")) == {},
      "diese Python-Datei ist garantiert kein gueltiges JSON")
check("die Zahl der Eintraege ist nach oben begrenzt",
      "MAX_EINTRAEGE" in _q and "MAX_EINTRAEGE" in _q.split("def umschalten")[1],
      "sonst durchsucht eine aufgeblaehte Datei jeden Listenaufbau")
check("es wird NICHTS geloescht",
      "os.remove" not in _q and "unlink" not in _q and "rmtree" not in _q,
      "Ausblenden ist eine Anzeigesache, kein Loeschen")

# ---------------------------------------------------------------------------
print()
print("Test 4: _liste_anpassen() - der schnelle Weg und die Reihenfolge")
# ---------------------------------------------------------------------------
# Die Methode wird aus dem Quelltext geschnitten und einzeln
# ausgefuehrt: das ganze Frontend zu importieren ist hier zu teuer und
# zu nebenwirkungsreich. Dasselbe Verfahren wie bei _ra_wand_daten()
# in test_erfolg_wand.py.
_FE = io.open(os.path.join(_REPO, "frontend", "frontend.py"),
              encoding="utf-8").read()


def _schneiden(name):
    i = _FE.index("    def %s(self" % name)
    j = _FE.index("\n    def ", i + 10)
    return "\n".join(z[4:] if z.startswith("    ") else z
                     for z in _FE[i:j].split("\n"))


_quelle = _schneiden("_liste_anpassen")
_umgebung = {"VERSTECKT": V, "ordner_zuerst": S.ordner_zuerst,
             "favoriten_zuerst": S.favoriten_zuerst}
exec(compile(_quelle, "<_liste_anpassen>", "exec"), _umgebung)


class Attrappe(object):
    def __init__(self):
        self.cats = [("SNES", {}, "SNES")]
        self.cat_i = 0
        self._favorites_set = set()
        self._anzeige_stand = 0
        self._anzeige_cache = None
    _liste_anpassen = _umgebung["_liste_anpassen"]


# Eine echte Datei fuer dieses Stueck - laden() ohne Pfad greift auf
# VERSTECKT_FILE zu.
V.VERSTECKT_FILE = pfad
_vergessen()

BASIS = [("Hacks/", "folder", "Hacks"),
         ("Tools/", "folder", "Tools"),
         ("Chrono Trigger", "game", object()),
         ("F-Zero", "game", object()),
         ("Super Mario World", "game", object())]

a = Attrappe()
check("ohne Einstellung kommt DASSELBE Listenobjekt zurueck",
      a._liste_anpassen(BASIS) is BASIS,
      "sonst kostet eine Einstellung, die niemand benutzt, bei jedem "
      "Bildaufbau eine neue Liste")

S.toggle_ordner_zuerst()          # Ordner nach hinten
raus = a._liste_anpassen(BASIS)
check("Ordner hinten: die Spiele stehen vorn",
      [x[1] for x in raus] == ["game", "game", "game", "folder", "folder"],
      str([x[0] for x in raus]))
check("und die Reihenfolge innerhalb der Gruppen bleibt",
      [x[0] for x in raus if x[1] == "game"]
      == ["Chrono Trigger", "F-Zero", "Super Mario World"])
S.toggle_ordner_zuerst()          # zurueck

a._favorites_set = {"F-Zero"}
S.toggle_favoriten_zuerst()
a._anzeige_geaendert = lambda: None
a._anzeige_cache = None
raus = a._liste_anpassen(BASIS)
check("Favoriten zuerst: der Favorit steht ganz oben",
      raus[0][0] == "F-Zero", str([x[0] for x in raus]))
check("die Ordner bleiben dabei beisammen",
      [x[0] for x in raus][1:3] == ["Hacks/", "Tools/"],
      str([x[0] for x in raus]))
S.toggle_favoriten_zuerst()
a._anzeige_cache = None

V.umschalten("SNES", "F-Zero", pfad)
V.umschalten("SNES", "Hacks", pfad)
_vergessen()
a._anzeige_cache = None
raus = a._liste_anpassen(BASIS)
check("ausgeblendet: das Spiel ist weg",
      "F-Zero" not in [x[0] for x in raus], str([x[0] for x in raus]))
check("ausgeblendet: der Ordner ist weg - erkannt am ORDNERNAMEN",
      "Hacks/" not in [x[0] for x in raus],
      "fuer Ordner zaehlt item[2] ('Hacks'), nicht die Beschriftung "
      "mit dem '/' - sonst haette derselbe Ordner zwei Kennungen")
check("der Rest steht unveraendert da",
      [x[0] for x in raus]
      == ["Tools/", "Chrono Trigger", "Super Mario World"])

# Der Merker muss sich bei einer Aenderung drehen.
vorher = a._liste_anpassen(BASIS)
check("zweimal gefragt, einmal gerechnet",
      a._liste_anpassen(BASIS) is vorher, "sonst ist der Merker wirkungslos")
V.umschalten("SNES", "F-Zero", pfad)      # wieder einblenden
_vergessen()
a._anzeige_stand += 1
check("nach einer Aenderung rechnet er neu",
      "F-Zero" in [x[0] for x in a._liste_anpassen(BASIS)],
      "ohne den Zaehler bliebe die Liste still stehen")

check("der Merker haengt am Zaehler",
      "_anzeige_stand" in _quelle,
      "ohne ihn kann eine Aenderung vergessen werden, und zwar still")
check("und er liegt NICHT am Knoten",
      "node[" not in _quelle and "_display_items_cache" not in _quelle,
      "der Knoten-Cache gehoert dem Baum und ueberlebt einen "
      "Kategoriewechsel - das hier ist Anzeigezustand")

# ---------------------------------------------------------------------------
print()
print("Test 5: die Ordnerzahl wird gemerkt, nicht gezaehlt")
# ---------------------------------------------------------------------------
_zahlen_quelle = _schneiden("_ordner_zahlen")
check("die Zahl liegt in einem Merker am Knoten",
      "_ordner_zahlen_cache" in _zahlen_quelle,
      "ohne ihn ist es ein Baumdurchlauf pro Zeile und Bild")
check("gezaehlt wird durch alle Unterordner",
      "for sub in n.get(\"folders\"" in _zahlen_quelle,
      "die Zahl an der obersten Ebene waere sonst nichtssagend")

_um = {}
exec(compile(_zahlen_quelle, "<_ordner_zahlen>", "exec"), _um)


class BaumAttrappe(object):
    _ordner_zahlen = _um["_ordner_zahlen"]


BAUM = {"items": [1, 2],
        "folders": {"A": {"items": [1, 2, 3],
                          "folders": {"A1": {"items": [1], "folders": {}}}},
                    "B": {"items": [], "folders": {}}}}
z = BaumAttrappe()._ordner_zahlen(BAUM)
check("A zaehlt seine Unterordner mit", z.get("A") == 4, str(z))
check("ein leerer Ordner zaehlt 0", z.get("B") == 0, str(z))
check("der Merker landet am Knoten", "_ordner_zahlen_cache" in BAUM)

# Zweiter Aufruf darf nicht noch einmal zaehlen: der Merker wird
# veraendert, und das muss sich zeigen.
BAUM["_ordner_zahlen_cache"] = {"A": 999}
check("beim zweiten Mal kommt der Merker",
      BaumAttrappe()._ordner_zahlen(BAUM).get("A") == 999)

check("gezeichnet wird die Zahl nur in der Listenansicht",
      '"%s [%d]"' in _FE and "ordner_zahlen_an()" in _FE
      and "_kachel_name_zeichnen" in _FE
      and "ordner_zahlen_an" not in _FE.split("def _kachel_name_zeichnen")[1][:1200],
      "im Raster steht nur EIN Name unter dem Bild - dort waere die "
      "Zahl keine Uebersicht")

shutil.rmtree(_TMP, ignore_errors=True)
print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
