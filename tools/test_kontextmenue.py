#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Das Kontextmenue (Build 256).

X am Pad, F1 auf der Tastatur: eine Liste mit dem, was an dieser
Stelle gerade geht. Das Frontend kann all das laengst - nur verteilt
ueber F6, F7, F8, F10, F11, Tab und vier Select-Kombinationen. Wer ein
Pad in der Hand hat und keine Anleitung gelesen hat, findet davon fast
nichts.

WORAN ES SCHEITERN KANN, und darum haengt dieser Test an genau diesen
Punkten:

  1. EINE BESTEHENDE TASTE WIRD UMGEWIDMET. X ist "back_fe" - die
     Aktion, mit der man WAEHREND eines Cores ins Frontend
     zurueckkommt. Wer sie fuer das Menue umbenennt, nimmt dem Nutzer
     den Rueckweg aus dem Spiel. Deshalb bleibt die Aktion, was sie
     ist, und wird nur DORT behandelt, wo sie bisher ins Leere lief.
  2. F1 BRICHT DEN AUSSTIEG AUS DEM SPIEL. F1 steigt im Spiel sofort
     aus - aber ueber rohe HID-Auswertung, nicht ueber die KEYMAP.
     Wer das verwechselt, baut einen Fehler, den man erst im Spiel
     merkt.
  3. DAS MENUE MACHT DIE ARBEIT SELBST. Dann gaebe es zwei Wege zum
     selben Ziel (Favorit setzen, Ansicht wechseln, suchen), und
     einer davon wuerde eines Tages nicht mitgepflegt. Es liefert
     stattdessen den NAMEN einer vorhandenen Aktion zurueck.
  4. ES ZEIGT EINTRAEGE, DIE NICHT PASSEN. "Als Favorit merken" bei
     einem Ordner ist eine Enttaeuschung pro Zeile.
  5. AUSBLENDEN LEGT EINE ZWEITE WAHRHEIT AN. Fuer Kategorien gibt es
     seit Build 250 die Hauptseite - eine zweite Datei fuer dieselbe
     Frage laeuft frueher oder spaeter auseinander.

Ausfuehren:
    python3 tools/test_kontextmenue.py
"""
import io
import os
import sys

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
sys.path.insert(0, os.path.join(_REPO, "frontend"))

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


_FE = io.open(os.path.join(_REPO, "frontend", "frontend.py"),
              encoding="utf-8").read()
_IN = io.open(os.path.join(_REPO, "frontend", "fe", "input.py"),
              encoding="utf-8").read()

# ---------------------------------------------------------------------------
print("Test 1: die Taste - und was sie NICHT kaputtmacht")
# ---------------------------------------------------------------------------
import fe.input as INP                                     # noqa: E402

check("X bleibt 'back_fe'", INP.KEYMAP.get(INP.BTN_X) == "back_fe",
      "das ist der Rueckweg aus einem laufenden Core - wer ihn fuer "
      "das Menue umwidmet, nimmt ihn dem Nutzer weg")
check("F1 loest dieselbe Aktion aus",
      INP.KEYMAP.get(INP.KEY_F1) == "back_fe",
      "eine Regel fuer Pad und Tastatur: im Spiel zurueck ins "
      "Frontend, im Frontend das Menue")
check("und F1 hat den richtigen Code", INP.KEY_F1 == 59, str(INP.KEY_F1))

# DER AUSSTIEG AUS DEM SPIEL laeuft NICHT ueber die KEYMAP. Das ist
# der Grund, warum ein Eintrag dort gefahrlos ist - und genau das
# muss wahr bleiben.
_wge = _IN.split("def wait_game_exit")[1]
check("der Ausstieg per F1 im Spiel liest rohe HID-Berichte",
      "_hid_report_has_f1_key" in _wge,
      "nicht die KEYMAP - sonst haette der neue Eintrag ihn veraendert")
check("und fragt die KEYMAP dort nicht",
      "KEYMAP" not in _wge.split("_hid_report_has_f1_key")[0][-3000:],
      "sonst waere der Eintrag oben gefaehrlich")

# ---------------------------------------------------------------------------
print()
print("Test 2: die Hauptschleife behandelt die Aktion")
# ---------------------------------------------------------------------------
check("'back_fe' wird in der Hauptschleife behandelt",
      'elif act == "back_fe":' in _FE,
      "bisher kam die Aktion an und niemand tat etwas damit")
_zweig = _FE.split('elif act == "back_fe":')[1].split("elif act ==")[0]
check("und ruft das Kontextmenue", "self.kontextmenue()" in _zweig)
check("Abbruch zeichnet neu statt stehenzubleiben",
      "if gewaehlt is None:" in _zweig and "self.draw()" in _zweig)
check("eine Auswahl wird VORGEMERKT statt selbst ausgefuehrt",
      "_vorgemerkte_aktion" in _zweig,
      "sonst gaebe es zwei Wege zum selben Ziel")
check("next_action() bedient die Vormerkung vor der Tastatur",
      "_vorgemerkte_aktion"
      in _FE.split("def next_action(self):")[1].split("while True:")[0],
      "sonst kaeme sie nie an")

# ---------------------------------------------------------------------------
print()
print("Test 3: der Inhalt richtet sich nach dem, was markiert ist")
# ---------------------------------------------------------------------------
import fe.translations as TR                               # noqa: E402

_quelle = _FE[_FE.index("    def kontextmenue(self):"):]
_quelle = _quelle[:_quelle.index("\n    def ", 10)]
_quelle = "\n".join(z[4:] if z.startswith("    ") else z
                    for z in _quelle.split("\n"))
_um = {"t": TR.t}
exec(compile(_quelle, "<kontextmenue>", "exec"), _um)


class Attrappe(object):
    kontextmenue = _um["kontextmenue"]

    def __init__(self, page, items, fav=(), done=()):
        self.page = page
        self._items = list(items)
        self.item_i = 0
        self._favorites_set = set(fav)
        self._completed_set = set(done)
        self.gezeigt = None
        self._force_full_redraw = False

    def _display_items(self):
        return self._items

    def _wizard_choice(self, titel, optionen, **kw):
        self.gezeigt = list(optionen)
        return None          # Abbruch - uns interessiert nur die Liste


SPIEL = ("Super Mario World", "game", None)
ORDNER = ("Hacks/", "folder", "Hacks")

a = Attrappe(1, [SPIEL])
a.kontextmenue()
check("bei einem Spiel steht 'Als Favorit merken' drin",
      TR.t("ctx_fav_an") in a.gezeigt, str(a.gezeigt))
check("und 'Als durchgespielt merken'",
      TR.t("ctx_done_an") in a.gezeigt)

b = Attrappe(1, [SPIEL], fav={"Super Mario World"},
             done={"Super Mario World"})
b.kontextmenue()
check("ist es schon Favorit, steht dort 'entfernen'",
      TR.t("ctx_fav_aus") in b.gezeigt, str(b.gezeigt))
check("dasselbe bei durchgespielt",
      TR.t("ctx_done_aus") in b.gezeigt)

c = Attrappe(1, [ORDNER])
c.kontextmenue()
check("bei einem ORDNER steht kein Favoriten-Eintrag",
      TR.t("ctx_fav_an") not in c.gezeigt
      and TR.t("ctx_fav_aus") not in c.gezeigt,
      "ein Ordner kann kein Favorit sein - die Zeile waere eine "
      "Enttaeuschung")
check("und kein 'durchgespielt'",
      TR.t("ctx_done_an") not in c.gezeigt)
check("ausblenden geht trotzdem", TR.t("ctx_verstecken") in c.gezeigt)

d = Attrappe(0, [])
d.kontextmenue()
check("auf der Hauptseite steht 'Kategorie ausblenden'",
      TR.t("ctx_hauptseite") in d.gezeigt, str(d.gezeigt))
check("und dort KEIN Filter und keine Suche",
      TR.t("ctx_filter") not in d.gezeigt
      and TR.t("ctx_suche") not in d.gezeigt,
      "beides gibt es auf der Hauptseite nicht")

e = Attrappe(1, [SPIEL])
e.kontextmenue()
check("ohne Favoriten fehlt 'Zufaelliger Favorit'",
      TR.t("ctx_zufall_fav") not in e.gezeigt, str(e.gezeigt))
check("mit Favoriten ist er da", TR.t("ctx_zufall_fav") in b.gezeigt)

check("nach dem Menue wird ein voller Neuaufbau angefordert",
      a._force_full_redraw is True,
      "das Menue zeichnet sein eigenes Bild - ohne das bleiben Reste "
      "stehen")

# ---------------------------------------------------------------------------
print()
print("Test 4: die Auswahl sind NAMEN vorhandener Aktionen")
# ---------------------------------------------------------------------------
# Jeder zurueckgegebene Name muss entweder in der Hauptschleife
# behandelt werden oder einer der drei Sonderfaelle sein, die das
# Menue selbst erledigt.
import re                                                  # noqa: E402

namen = set(re.findall(r'"([a-z_]+)"\)\)\n', ""))   # Platzhalter
namen = set(re.findall(r'eintraege\.append\(\s*\([^,]+,\s*"([a-z_]+)"\)',
                       _quelle))
namen |= set(re.findall(r'"([a-z_]+)"\)\)', _quelle))
namen = {n for n in namen if not n.startswith("ctx_")}
EIGENE = {"verstecken", "buchstabe", "zufall_fav"}
# BEIDE FORMEN ZAEHLEN. Der erste Entwurf suchte nur nach
# 'act == "..."' und war bei "search" rot - das wird ueber
# 'act in ("search", "search_pad")' behandelt. Eine Pruefung, die an
# EINER Schreibweise haengt, prueft die Schreibweise und nicht die
# Zusage; derselbe Fehler wie schon dreimal in dieser Reihe.
behandelt = set(re.findall(r'act == "([a-z_]+)"', _FE))
behandelt |= set(re.findall(r'act in \(([^)]*)\)', _FE)
               and re.findall(r'"([a-z_]+)"',
                              " ".join(re.findall(r'act in \(([^)]*)\)',
                                                  _FE))) or [])
for n in sorted(namen - EIGENE):
    check("'%s' wird in der Hauptschleife behandelt" % n,
          n in behandelt, "sonst passiert beim Auswaehlen nichts")
for n in sorted(EIGENE):
    check("'%s' hat einen eigenen Zweig" % n,
          ('"%s"' % n) in _FE.split('elif act == "back_fe":')[1][:2000])

# ---------------------------------------------------------------------------
print()
print("Test 5: ausblenden legt KEINE zweite Wahrheit an")
# ---------------------------------------------------------------------------
_v = _FE[_FE.index("    def _kontext_verstecken(self):"):]
_v = _v[:_v.index("\n    def ", 10)]
check("auf der Hauptseite schreibt es in fe/hauptseite.py",
      "HS.speichern(" in _v and "HS.laden()" in _v,
      "dort gibt es die Sichtbarkeit seit Build 250 - eine zweite "
      "Datei fuer dieselbe Frage laeuft auseinander")
check("und benutzt deren Kuerzel statt eigener",
      "HS.schluessel(" in _v)
check("'System' bleibt auch hier",
      "HS.SYSTEM" in _v,
      "fe/hauptseite.py wirft es beim Speichern ohnehin heraus - eine "
      "Meldung ist ehrlicher als stilles Nichtstun")
check("in der Liste schreibt es in fe/versteckt.py",
      "VERSTECKT.umschalten(" in _v)
check("fuer Ordner zaehlt der Ordnername, nicht die Beschriftung",
      'arg if kind == "folder" else label' in _v,
      "sonst haette derselbe Ordner zwei Kennungen")
check("der Index wird hinterher begrenzt",
      "self.item_i = min(" in _v,
      "die Liste ist nach dem Ausblenden kuerzer - ohne das steht der "
      "Cursor hinter ihrem Ende")

# ---------------------------------------------------------------------------
print()
print("Test 6: der Zufallsfavorit benutzt denselben Startweg")
# ---------------------------------------------------------------------------
# GEPRUEFT WIRD DER ZWEIG, NICHT DIE GESAMTZAHL. Der erste
# Entwurf verlangte, dass write_mgl() genau einmal vorkommt - das
# ist falsch, es gibt den Zufallsstart UND den normalen Spielstart.
# Richtig ist: im Kontextmenue-Zweig selbst wird nichts gestartet.
_kz = _FE.split('elif act == "back_fe":')[1].split("elif act ==")[0]
# OHNE DIE KOMMENTARE. Im Zweig steht ein Kommentar, der erklaert,
# warum dort NICHT gestartet wird - und in dem kommt 'write_mgl()'
# vor. Der erste Entwurf stolperte genau darueber und meldete einen
# Fehler, der keiner war. Derselbe Fall wie in test_zaparoo.py, wo
# die Pruefung am eigenen Docstring haengenblieb: eine Pruefung muss
# am CODE haengen, nicht am Text daneben.
_kz = "\n".join(z for z in _kz.split("\n")
                if not z.strip().startswith("#"))
check("der Kontextmenue-Zweig startet selbst kein Spiel",
      "write_mgl(" not in _kz and "run_core(" not in _kz,
      "der Start haengt an der RA-Core-Frage, CORES.aufloesen(), "
      "record_recent() und write_mgl() - das ein zweites Mal "
      "hinzuschreiben hiesse, es ein zweites Mal pflegen zu muessen")
_rnd = _FE.split('elif act == "random":')[1][:3000]
check("die Auswahl wird gefiltert", "_favorites_set" in _rnd)
check("und eine leere Auswahl startet NICHTS",
      "ctx_zufall_fav_leer" in _rnd,
      "sonst startet 'zufaelliger Favorit' heimlich irgendein Spiel")
check("die Markierung wird gleich wieder zurueckgesetzt",
      "self._zufall_nur_favoriten = False" in _rnd,
      "sonst gilt sie auch beim naechsten F11")

# ---------------------------------------------------------------------------
print()
print("Test 7: der Buchstabensprung zeigt nur, was vorkommt")
# ---------------------------------------------------------------------------
_b = _FE[_FE.index("    def buchstaben_springen(self):"):]
_b = _b[:_b.index("\n    def ", 10)]
check("die Buchstaben kommen aus den echten Namen",
      "for n in namen:" in _b,
      "ein volles A-Z zwingt zum Vorbeifahren an leeren Zeilen")
check("alles Nicht-Buchstabe wird zu '#' zusammengefasst",
      '"#"' in _b and "isalpha()" in _b)
check("und '#' wird getrennt behandelt",
      'ziel == "#"' in _b,
      "jump_to_letter() kennt kein '#'")

# Alle neuen Texte gibt es in beiden Sprachen.
for sch in sorted(set(re.findall(r't\("(ctx_[a-z_]+)"', _FE))):
    eintrag = TR.TRANSLATIONS.get(sch)
    check("Text '%s' gibt es in beiden Sprachen" % sch,
          bool(eintrag and eintrag.get("de") and eintrag.get("en")),
          str(eintrag))

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
