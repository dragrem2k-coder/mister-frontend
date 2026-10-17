#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Die Funktionsliste bleibt vollstaendig (Build 283).

NUTZERWUNSCH: "dann haette ich einmal gerne eine liste mit allen
funktionen und einstellmoeglichkeiten was das frontend alles kann!
wirklich alles! fehlerfrei!"

"Fehlerfrei" ist keine Eigenschaft, die man einmal herstellt. Eine
Liste, die am Tag ihrer Fertigstellung stimmt, ist drei Builds spaeter
falsch - und zwar lautlos, denn eine Dokumentation beschwert sich
nicht.

DESHALB STEHT SIE IN DER SUITE. Dieser Test laesst den Erzeuger laufen
und besteht nur, wenn dessen Gegenprobe in BEIDE Richtungen aufgeht:

  * jeder Eintrag, den fe.menu.system_items() liefert, steht in der
    Liste (sonst fehlt etwas),
  * jede Menuezeile der Liste kommt von dort (sonst steht etwas drin,
    das es nicht gibt - und das ist schlimmer als eine Luecke, weil
    man danach sucht).

Wer also einen Menuepunkt hinzufuegt und die Liste nicht neu erzeugt,
bekommt eine rote Suite und nicht eine stille Falschaussage.

Ausfuehren:
    python3 tools/test_funktionsliste.py
"""
import importlib.util
import io
import os
import sys

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


_spec = importlib.util.spec_from_file_location(
    "liste_erzeugen", os.path.join(_HIER, "liste_erzeugen.py"))
L = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(L)

print("Teil 1: die Gegenprobe des Erzeugers")
text, gruppen = L.bauen()
fehlen, ueberfluessig = L.gegenprobe(gruppen, text)
check("jeder Eintrag des echten Menue-Erzeugers steht in der Liste",
      not fehlen,
      "fehlt: " + ", ".join(fehlen[:5]) if fehlen else "")
check("und jede Menuezeile der Liste kommt von dort",
      not ueberfluessig,
      "zuviel: " + ", ".join(ueberfluessig[:5]) if ueberfluessig else "")

print()
print("Teil 2: die Liste hat Substanz")
# Untergrenzen, nicht exakte Zahlen: der Test soll merken, wenn ein
# ganzer Abschnitt wegbricht, und nicht bei jedem neuen Menuepunkt
# rot werden. Eine Pruefung, die bei jeder Aenderung angepasst werden
# muss, wird irgendwann angepasst, ohne hinzusehen.
anzahl = sum(len(e) for _g, e in gruppen)
check("das Systemmenue hat mindestens 60 Eintraege",
      anzahl >= 60, "%d" % anzahl)
check("in mindestens 6 Gruppen", len(gruppen) >= 6, "%d" % len(gruppen))
check("das Kontextmenue ist dabei",
      len(L.kontextmenue()) >= 10, "%d Punkte" % len(L.kontextmenue()))
check("die Tastenbelegung ist dabei",
      len(L.tasten()) >= 25, "%d Zeilen" % len(L.tasten()))
_sch, _wert = L.schalterdateien()
check("die Schalterdateien sind dabei",
      len(_sch) >= 20, "%d Schalter" % len(_sch))
check("und von den Wertdateien getrennt",
      len(_wert) >= 5 and not (set(_sch) & set(_wert)),
      "%d Wertdateien - bei einem Schalter zaehlt die Existenz, bei "
      "einem Wert der Inhalt" % len(_wert))
check("die Aufruf-Optionen sind dabei",
      len(L.optionen()) >= 3, "%s" % ", ".join(L.optionen()))
check("die eingebaute Uebersicht ist dabei",
      len(L.hilfe_themen()) >= 15,
      "%d Abschnitte" % len(L.hilfe_themen()))

print()
print("Teil 3: was die Liste ueber sich selbst sagt")
check("sie sagt, dass sie erzeugt ist",
      "erzeugt, nicht geschrieben" in text,
      "wer sie von Hand aendert, verliert die Aenderung beim naechsten "
      "Lauf - das muss drinstehen")
check("und wie man sie neu erzeugt",
      "tools/liste_erzeugen.py" in text)
check("sie nennt den zustandsabhaengigen Teil",
      "Ist RetroAchievements eingerichtet" in text,
      "der Erzeuger laeuft nicht auf dem MiSTer und sieht deshalb "
      "keine eingerichteten Achievements - das waere sonst genau an "
      "der Stelle falsch, an der die Liste vollstaendig sein soll")
check("und sie sagt, was NICHT darin steht",
      "NICHT steht" in text,
      "Cores, Scripts und Spiele kommen von der Karte; eine Liste, "
      "die das verschweigt, verspricht zu viel")

print()
print("Teil 4: die ausgelieferte Datei ist aktuell")
_ziel = os.path.join(_REPO, "docs", "FUNKTIONSLISTE.md")
if os.path.exists(_ziel):
    _da = io.open(_ziel, encoding="utf-8").read()
    check("docs/FUNKTIONSLISTE.md ist auf dem Stand des Erzeugers",
          _da == text,
          "sonst: python3 tools/liste_erzeugen.py")
else:
    check("docs/FUNKTIONSLISTE.md existiert", False,
          "python3 tools/liste_erzeugen.py")

print()
print("Teil 5: die grossen Funktionen (Build 284)")
# NACHFRAGE DES NUTZERS: "Hast du auch die Features bedacht, OBS etc,
# was es noch so alles kann?" - berechtigt. Die erste Fassung zaehlte
# das MENUE auf, und das OBS-Overlay steht dort als eine Zeile
# ("Stream-Overlay: an"), ohne dass irgendwo steht, was es ist.
#
# EIN MENUEPUNKT IST NICHT DASSELBE WIE EINE FUNKTION.
_funk, _innen = L.module_beschreibung()
check("die Funktionen sind einzeln benannt",
      len(_funk) >= 20, "%d" % len(_funk))
check("und das Innenleben getrennt davon",
      len(_innen) >= 20, "%d" % len(_innen))
check("kein Modul ohne Beschreibung",
      not [n for n, t in _funk + _innen if "ohne Beschreibung" in t],
      "ein unbenanntes Modul ist in einer Funktionsliste eine Luecke")

# DIE WICHTIGSTE PRUEFUNG DIESES TEILS: die Einteilung in Funktion und
# Innenleben steht als feste Liste im Erzeuger, weil man sie nicht aus
# dem Namen raten kann. Damit daraus keine Falle wird, muss JEDES Modul
# in genau einer Haelfte landen - ein neues Modul macht die Suite rot,
# bis jemand entscheidet, wohin es gehoert. Eine Liste, aus der neue
# Funktionen lautlos herausfallen, waere genau die, die nicht gewollt
# war.
import glob as _glob
import os as _os
_auf_platte = {_os.path.basename(p)[:-3]
               for p in _glob.glob(_os.path.join(_REPO, "frontend",
                                                 "fe", "*.py"))
               if not p.endswith("__init__.py")}
_auf_platte.add("stream_server")
_in_liste = set(L.alle_module())
check("jedes Modul kommt in der Liste vor",
      not (_auf_platte - _in_liste),
      "fehlt: " + ", ".join(sorted(_auf_platte - _in_liste)))
check("und keines doppelt oder erfunden",
      not (_in_liste - _auf_platte),
      "zuviel: " + ", ".join(sorted(_in_liste - _auf_platte)))

print()
print("Teil 6: das Overlay fuer OBS")
_port, _pfade = L.overlay_pfade()
check("der Port kommt aus dem Quelltext",
      _port == 8080, repr(_port) + " - eine Doku, die einen Port NENNT, "
      "muss ihn vom Code haben")
check("und die Pfade auch",
      "/overlay" in _pfade and "/admin" in _pfade
      and "/mirror" in _pfade,
      "%d Pfade: %s" % (len(_pfade), ", ".join(_pfade)))
check("jeder Pfad ist erklaert",
      all(("| `%s` |" % pf) in text for pf in _pfade),
      "ein Pfad ohne Erklaerung ist eine Zeile, die man nachschlagen "
      "muss")
check("und der OBS-Szenenwechsel ist genannt",
      "obs_websocket" in text and "Capture-Karten-Szene" in text)

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
