#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft, dass die Bedienhilfe am unteren Bildrand auf CRT ueberhaupt
erscheint (Build 144).

Hintergrund: an ueber einem Dutzend Stellen stand woertlich dieselbe
Rechnung

    hint_w = len(hint) * 8 * sc
    fb.text((W - hint_w) // 2, H - oy - 8 * sc, hint, sc, C_DIM, C_BG)

Passt der Hinweis nicht in eine Zeile, wird (W - hint_w) // 2 negativ -
und fb.text() zeichnet bei negativem x GAR NICHTS. Auf 320x240 stehen
bei Skalierung 1 genau 37 Zeichen zur Verfuegung; elf der deutschen
Hinweistexte sind laenger. In all diesen Bildschirmen fehlte die
Bedienhilfe auf dem CRT vollstaendig - nicht abgeschnitten, sondern
ersatzlos. Auf HDMI ist genug Platz, deshalb ist es nie aufgefallen.

Geprueft wird:
  1. der Helfer selbst: kurzer Hinweis unveraendert, langer umgebrochen
  2. dass kein deutscher/englischer Hinweistext mehr verschwindet
  3. die konkreten Bildschirme (Zufalls-Zock, Assistent, Ja/Nein)
  4. dass auf 1920x1080 kein Pixel anders liegt als vorher

Ausfuehren:
    python3 tools/test_hinweiszeile.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H                                        # noqa: E402

fm = H.fm
fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


def _textzeilen(fb):
    """Bildzeilen, in denen Text steht. Der Hintergrund ist ein ganz
    flacher Verlauf (0x07..0x0a), Text ist um ein Vielfaches heller."""
    return [y for y in range(fb.height)
            if max(fb.mm[y * fb.stride:(y + 1) * fb.stride]) > 0x40]


KURZ = "OK: weiter"
LANG = ("Hoch/Runter: wählen   OK: bestätigen   ESC: Einrichtung abbrechen")

# ---------------------------------------------------------------------------
print("Test 1: der Helfer selbst")
# ---------------------------------------------------------------------------
H.set_screen(320, 240)
f = H.make_frontend(page=1)
fb = f.fb
oy = fb.height * fm.OVERSCAN_Y // 100

fb.clear(fm.C_BG)
f._hinweis_unten(KURZ)
fb.flip()
kurz_zeilen = _textzeilen(fb)
check("kurzer Hinweis wird gezeichnet", bool(kurz_zeilen))
check("kurzer Hinweis steht unten",
      bool(kurz_zeilen) and min(kurz_zeilen) > fb.height * 3 // 4,
      "oberste Zeile %d" % min(kurz_zeilen or [0]))
check("kurzer Hinweis bleibt einzeilig",
      len(kurz_zeilen) <= 8, "%d Bildzeilen" % len(kurz_zeilen))

fb.clear(fm.C_BG)
f._hinweis_unten(LANG)
fb.flip()
lang_zeilen = _textzeilen(fb)
check("langer Hinweis wird ueberhaupt gezeichnet", bool(lang_zeilen))
check("langer Hinweis braucht zwei Zeilen",
      len(lang_zeilen) > len(kurz_zeilen),
      "%d statt %d Bildzeilen" % (len(lang_zeilen), len(kurz_zeilen)))
check("langer Hinweis bleibt im Overscan-Rand",
      bool(lang_zeilen) and max(lang_zeilen) < fb.height - oy,
      "letzte Zeile %d, Grenze %d" % (max(lang_zeilen or [0]), fb.height - oy))
check("langer Hinweis faengt nicht am linken Rand vorbei an",
      bool(lang_zeilen))

# ---------------------------------------------------------------------------
print("Test 2: kein Hinweistext verschwindet mehr")
# ---------------------------------------------------------------------------
import fe.translations as tr                                # noqa: E402

fehlend = []
for key, werte in sorted(tr.TRANSLATIONS.items()):
    if not isinstance(werte, dict) or "hint" not in key:
        continue
    for sprache in ("de", "en"):
        text = werte.get(sprache)
        if not text or "%" in text:
            continue
        fb.clear(fm.C_BG)
        f._hinweis_unten(text)
        fb.flip()
        if not _textzeilen(fb):
            fehlend.append("%s/%s" % (key, sprache))
check("jeder Hinweistext erscheint auf 320x240", not fehlend,
      ", ".join(fehlend[:6]))

# ---------------------------------------------------------------------------
print("Test 3: die betroffenen Bildschirme")
# ---------------------------------------------------------------------------
# Ja/Nein-Abfrage: der Hinweis sitzt INNERHALB der Box, dort galt
# derselbe Rechenfehler gegen box_w statt gegen W.
f.confirm_choice = 0
fb.clear(fm.C_BG)
f.draw_confirm_dialog()
fb.flip()
zeilen = _textzeilen(fb)
check("Ja/Nein-Abfrage zeichnet etwas", bool(zeilen))
if zeilen:
    # Der Hinweis steht zwischen Text und Knoepfen; ohne ihn waeren es
    # deutlich weniger Textzeilen. Grobpruefung: die Box hat mehr als
    # nur Frage + Knoepfe.
    check("Ja/Nein-Abfrage hat mehr als Frage und Knoepfe",
          len(zeilen) >= 24, "%d Bildzeilen mit Text" % len(zeilen))

# Einrichtungs-Assistent (_wizard_info) - wizard_skip_hint, 45 Zeichen.
eingaben = ["ok"]
f.inp.read_action = lambda: eingaben.pop(0) if eingaben else "ok"
fb.clear(fm.C_BG)
f._wizard_info("TITEL", ["Eine kurze Zeile."], skippable=True)
zeilen = _textzeilen(fb)
check("Assistent-Infoschirm zeigt die Bedienhilfe",
      bool(zeilen) and max(zeilen) > fb.height * 3 // 4,
      "letzte Zeile %d" % max(zeilen or [0]))

# Auswahlschirm (_wizard_choice) - wizard_choice_hint, 65 Zeichen.
eingaben = ["ok"]
fb.clear(fm.C_BG)
f._wizard_choice("TITEL", ["Erstens", "Zweitens"])
zeilen = _textzeilen(fb)
check("Assistent-Auswahl zeigt die Bedienhilfe",
      bool(zeilen) and max(zeilen) > fb.height * 3 // 4,
      "letzte Zeile %d" % max(zeilen or [0]))


def _baender(zeilen):
    """Zusammenhaengende Textbaender aus einer Zeilenliste."""
    if not zeilen:
        return []
    baender = [[zeilen[0], zeilen[0]]]
    for y in zeilen[1:]:
        if y == baender[-1][1] + 1:
            baender[-1][1] = y
        else:
            baender.append([y, y])
    return baender


# Der eigentliche Stolperstein beim ersten Anlauf von Build 144: ein
# zweizeiliger Hinweis schob sich auf CRT ueber die unterste Option.
# Jetzt zieht _wizard_choice() seine Hoehe vorher ab.
eingaben = ["ok"]
fb.clear(fm.C_BG)
f._wizard_choice("ZUFALLS-ZOCK",
                 ["Liste zurücksetzen", "Zurück"],
                 hint_key="wot_hint",
                 lines=["Alle 1274 Spiele waren schon dran. "
                        "Die Liste merkt sich jeden Start."])
baender = _baender(_textzeilen(fb))
check("Auswahlschirm hat Titel, Text, Optionen und Hinweis getrennt",
      len(baender) >= 5, "%d Baender: %s" % (len(baender), baender))
if len(baender) >= 2:
    abstaende = [baender[i + 1][0] - baender[i][1]
                 for i in range(len(baender) - 1)]
    check("keine zwei Textbloecke kleben aneinander",
          all(a >= 2 for a in abstaende), str(abstaende))
    check("alles bleibt im Overscan-Rand",
          baender[-1][1] < fb.height - oy,
          "letzte Zeile %d, Grenze %d" % (baender[-1][1], fb.height - oy))

# ---------------------------------------------------------------------------
print("Test 4: auf 1920x1080 aendert sich nichts")
# ---------------------------------------------------------------------------
H.set_screen(1920, 1080)
f2 = H.make_frontend(page=1)
fb2 = f2.fb
s = max(1, fb2.height // 360)
sc = s - 1 if s > 1 else 1
oy2 = fb2.height * fm.OVERSCAN_Y // 100

# Referenz: die alte Rechnung von Hand.
fb2.clear(fm.C_BG)
breite = len(LANG) * 8 * sc
fb2.text((fb2.width - breite) // 2, fb2.height - oy2 - 8 * sc,
         LANG, sc, fm.C_DIM, fm.C_BG)
fb2.flip()
alt = bytes(fb2.mm)

fb2.clear(fm.C_BG)
f2._hinweis_unten(LANG)
fb2.flip()
neu = bytes(fb2.mm)

check("HDMI-Bild ist bitgenau wie vorher", alt == neu,
      "%d abweichende Bytes" % sum(1 for a, b in zip(alt, neu) if a != b))

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  - " + x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
