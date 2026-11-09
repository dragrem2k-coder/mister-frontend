#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Die sechs Ansichten der Hauptseite (Build 314/315/316).

DIE GESCHICHTE IN DREI SAETZEN, weil sie erklaert, warum dieser Test
aussieht, wie er aussieht:

  * Build 314 hat Kachelwand, Dashboard und Karussell gebaut - aber
    als ZWEITEN Schalter ueber der vorhandenen Ansicht. Zwei Schalter,
    von denen einer den anderen stumm aussticht.
  * Prompt kamen zwei Meldungen: "beide ansichten ueberschneiden sich"
    und "bleibt aber in der listen ansicht, aber steuerung ist dann
    zum beispiel wie beim raster" - Bild von der einen Quelle,
    Navigation von der anderen.
  * Build 316 wirft den zweiten Schalter weg: die Hauptseite hat jetzt
    SECHS Ansichten an EINEM Schalter, und wer von 314/315 kommt,
    dessen Einstellung wird einmalig uebernommen.

WAS DIESER TEST SICHERT:
  1. sechs Ansichten, drei davon nur auf HDMI, Vorgabe "liste",
  2. es gibt KEINEN zweiten Schalter mehr - weder im Menue noch im
     Zweig,
  3. die HD-Regel steht an genau EINER Stelle, und auf der Roehre
     ueberspringt die Taste die drei HD-Ansichten (eine Taste, die
     dreimal nichts tut, haelt man fuer kaputt),
  4. die Geometrien liegen im Bild und ueberlappen sich nicht,
  5. alle sechs zeichnen auf allen Groessen, auch mit EINER Kategorie,
  6. der schnelle Pfad ist bitgenau wie ein voller Aufbau,
  7. ECHTE Tastenschritte, einmal rundherum - der Test, der den
     Ueberschneidungs-Fehler gefunden haette,
  8. ein Ansichtswechsel wirft ALLE sechs Zwischenspeicher weg,
  9. die Uebernahme aus Build 314/315 laeuft, laeuft nur EINMAL, und
     wird beim Start auch wirklich gerufen,
 10. der Fotosatz wird bevorzugt, mit Rueckfall auf das Abzeichen,
 11. die Fotodateien sind heil und einheitlich,
 12. kein zweiter Weg fuer etwas, das es schon gibt,
 13. und alle sechs Namen stehen woertlich in beiden Sprachen.

Ausfuehren:
    python3 tools/test_hauptseite_stil.py
"""
import hashlib
import os
import re
import shutil
import struct
import sys
import tempfile
import traceback
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H          # noqa: E402

import fe.art as A            # noqa: E402
import fe.settings as S       # noqa: E402
import fe.translations as TR  # noqa: E402
from _quelle import koerper, nur_code                     # noqa: E402

fm = H.fm

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYSART = os.path.join(_REPO, "frontend", "sysart")
FOTOS = os.path.join(_REPO, "frontend", "sysart_foto")
A.SYSART_BASE = fm.SYSART_BASE = SYSART
A.SYSART_FOTO_BASE = fm.SYSART_FOTO_BASE = FOTOS

# DER BILDSPEICHER DARF HIER NICHTS VERDRAENGEN, sonst misst dieser
# Test sich selbst kaputt.
#
# ArtCache.LIMIT steht auf 60 Bildern. Dieser Test baut 28 Kategorien
# in sechs Ansichten, jede mit eigenen Kastengroessen - weit mehr als
# 60 Eintraege. Der Zwischenspeicher ist ein MODULWEITER, und beide
# Seiten des Bildvergleichs teilen ihn sich: die eine Seite hat ein
# Bild noch, die andere nicht mehr, und dann vergleicht man ein
# fertiges Bild mit einem Platzhalter und haelt den Unterschied fuer
# einen Zeichenfehler. Genau darauf bin ich beim ersten Anlauf
# hereingefallen (bis zu 500.000 "abweichende" Bildpunkte, alle
# unecht).
#
# Dass die Verdraengung funktioniert, prueft ein eigener Test - hier
# geht es um die Geometrie und das Freiraeumen, und dafuer muessen
# beide Seiten dieselben Bilder sehen.
#
# ES SIND VIER SCHRAUBEN UND NICHT EINE, und das habe ich erst beim
# zweiten Anlauf gemerkt: nur LIMIT hochzusetzen half nichts, weil
# seit Build 74 zusaetzlich ein SPEICHER-Budget verdraengt
# (ORIGINAL_BUDGET/SCALED_BUDGET). Welche Bilder dabei herausfliegen,
# haengt an der Reihenfolge - und genau das macht den Vergleich
# unzuverlaessig, bis alle vier offen sind.
A.ART.LIMIT = 100000
A.ART.ORIGINAL_MIN = 100000
A.ART.ORIGINAL_BUDGET = 8 * 1024 * 1024 * 1024
A.ART.SCALED_MIN = 100000
A.ART.SCALED_BUDGET = 8 * 1024 * 1024 * 1024

_QF = open(os.path.join(_REPO, "frontend", "frontend.py"),
           encoding="utf-8", errors="replace").read()
_ROH = nur_code(_QF)
_WAND = nur_code(koerper(_QF, "_draw_cats_kachelwand", "Frontend"))
_WKACHEL = nur_code(koerper(_QF, "_wand_kachel_zeichnen", "Frontend"))
_DASH = nur_code(koerper(_QF, "_draw_cats_dashboard", "Frontend"))
_TAFEL = nur_code(koerper(_QF, "_dash_tafel_zeichnen", "Frontend"))
_ZEILE = nur_code(koerper(_QF, "_dash_zeile_zeichnen", "Frontend"))
_KAR = nur_code(koerper(_QF, "_draw_cats_karussell", "Frontend"))
_IMPL = nur_code(koerper(_QF, "_draw_page_cats_impl", "Frontend"))
_HD = nur_code(koerper(_QF, "_ansicht_haupt_hd", "Frontend"))
_WEITER = nur_code(koerper(_QF, "_ansicht_haupt_weiter", "Frontend"))
_SETZEN = nur_code(koerper(_QF, "ansicht_haupt_setzen", "Frontend"))
_NAV = nur_code(koerper(_QF, "_draw_navigate_cats_impl", "Frontend"))
_LOGO = nur_code(koerper(_QF, "_kat_logo", "Frontend"))

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


def gleich(a, b):
    return (hashlib.sha256(bytes(a)).hexdigest()
            == hashlib.sha256(bytes(b)).hexdigest())


def abweichung(a, b):
    ab, bb = bytes(a), bytes(b)
    stellen = [i // 4 for i in range(0, len(ab), 4)
               if ab[i:i + 3] != bb[i:i + 3]]
    return (len(stellen), stellen[:3]) if stellen else (0, [])


print(__doc__.strip().split("\n")[0])
print()

TMP = tempfile.mkdtemp(prefix="hauptansicht_")
S.ANSICHT_HAUPT_FILE = os.path.join(TMP, "ansicht_haupt.txt")
S.HAUPT_STIL_FILE = os.path.join(TMP, "haupt_stil.txt")
# EIN EIGENER MINIATUR-ZWISCHENSPEICHER, und das ist kein Aufraeumen,
# sondern die dritte und letzte Ursache der "unechten Abweichungen":
# dieser Test lief ALLEIN gruen und im Pruefstand rot. Der Unterschied
# ist der Ordner auf der Platte, in den die Miniaturen geschrieben
# werden - er ist modulweit und bleibt zwischen zwei Tests stehen.
# Geschrieben wird ausserdem von einem HINTERGRUNDFADEN; was die eine
# Seite des Bildvergleichs dort schon findet und die andere noch
# nicht, entscheidet dann der Zufall. Mit einem eigenen, leeren Ordner
# je Lauf ist das ausgeschlossen.
# UMGEBOGEN WIRD DIE BASIS, NICHT DER ORDNER - und das ist der Haken,
# an dem der erste Versuch haengengeblieben ist: thumb_cache_modus()
# rechnet THUMB_CACHE_DIR bei jedem Aufloesungswechsel neu aus
# (THUMB_CACHE_BASE + "hd"/"sd"), und dieser Test wechselt die
# Aufloesung staendig. Eine Zuweisung an THUMB_CACHE_DIR allein ist
# nach dem naechsten set_screen() wieder weg.
# DEN SCHIMMER ABSCHALTEN - und DAS ist die Ursache, hinter der ich in
# Build 316 und 317 zweimal das falsche Symptom behandelt habe.
#
# _pulse_factor() rechnet "time.monotonic() - self._pulse_t0",
# sinusfoermig mit einer Sekunde Periode. Beide Seiten des Vergleichs
# bekommen denselben _pulse_t0 - aber nicht dieselbe Uhrzeit: die Uhr
# des Pruefstands wird im Lauf weitergestellt, und zwischen dem
# letzten Schritt der einen Seite und dem Aufbau der anderen liegt
# dann eine andere PHASE. Das Ergebnis ist ein Farbwert, der um
# genau eins danebenliegt (28,32,44 gegen 29,33,45) - und je laenger
# der Test schon laeuft, desto mehr Faelle trifft es. Genau deshalb
# lief er allein gruen und im Pruefstand rot.
#
# Dass der Schimmer selbst funktioniert, prueft tools/test_pulse.py.
S.PULSE_EFFECT_DISABLED_FLAG = os.path.join(TMP, "kein_puls")
open(S.PULSE_EFFECT_DISABLED_FLAG, "w").close()
H._zwischenspeicher_leeren()
A.THUMB_CACHE_BASE = os.path.join(TMP, "thumbs")
A.THUMB_CACHE_DIR = os.path.join(A.THUMB_CACHE_BASE, "hd")
os.makedirs(A.THUMB_CACHE_DIR, exist_ok=True)

NEU = ("kachelwand", "dashboard", "karussell")
ALLE = ("liste", "raster", "galerie") + NEU

# Eine Mischung aus Namen MIT Foto und Namen OHNE - genau der Fall, der
# auf seinem Geraet eintritt (20 Fotos, 60 Abzeichen). Ein Test nur mit
# Fotos haette den Rueckfall nie angefasst.
MIT_FOTO = ["NES", "SNES", "GAMEBOY", "GBC", "GBA", "N64", "Genesis",
            "SMS", "MegaCD", "PSX", "Saturn", "TGFX16", "NEOGEO",
            "ATARI2600", "ARCADE", "SUPERGAMEBOY", "PHYSICAL_DISC_CORES",
            "S32X", "VIRTUALBOY", "COMPUTER"]
OHNE_FOTO = ["FAVORITES", "CONTINUE", "RECENT", "COLLECTIONS",
             "GAMEGEAR", "ATARILYNX", "COLECOVISION", "SYSTEM"]
KEYS = OHNE_FOTO[:4] + MIT_FOTO + OHNE_FOTO[4:]


def seite(w, h, ansicht, anzahl=None):
    S.ansicht_haupt_schreiben(ansicht)
    H._zwischenspeicher_leeren()
    H.set_screen(w, h)
    f = H.make_frontend(page=0)
    f._ansicht_haupt = None
    # DEN COVER-SCHUTZ ABSCHALTEN, sonst misst dieser Test sich selbst
    # kaputt. _sync_cover_defer() setzt ART._defer_uncached auf
    # "time.monotonic() - _last_input_time < COVER_SETTLE"; im
    # Pruefstand steht die Uhr, also ist die Differenz 0 und der Schutz
    # IMMER an - dann zeigt jede Seite nur die Bilder, die zufaellig
    # schon im Speicher liegen. Beide Seiten des Vergleichs teilen sich
    # diesen Speicher, und schon vergleicht man ein fertiges Bild mit
    # einem Platzhalter. Mit _last_input_time = 0 ist die Differenz
    # riesig, der Schutz aus, und beide Seiten laden dasselbe.
    # Dass der Schutz selbst funktioniert, pruefen die Tests aus
    # Build 244/300.
    f._last_input_time = 0
    # DAS AUSLAGERN ABSCHALTEN - und das ist die FUENFTE und letzte
    # Ursache der "unechten Abweichungen", und die einzige, die nicht
    # an der Uhr haengt, sondern an einem FADEN.
    #
    # _kat_logo() fragt mit auslagern_ok=True. Hat der Bildspeicher das
    # Bild noch nicht in dieser Kastengroesse, gibt er es an den
    # Vorauslader ab, liefert None und der Zeichenweg malt den
    # Platzhalter - absichtlich so, denn auf dem Geraet kommt das Bild
    # eine Runde spaeter nach. Im Bildvergleich heisst das: die erste
    # Seite malt Platzhalter, bis der Faden fertig ist, die zweite
    # findet das Bild schon im Speicher und malt es. 44.192 Bildpunkte
    # Unterschied, Platzhalterfarbe gegen Foto - und kein einziger
    # davon ein Zeichenfehler. WER gewinnt, entscheidet allein, wie
    # schnell der Faden an diesem Tag war; genau deshalb war der Befund
    # von Lauf zu Lauf ein anderer.
    #
    # Mit auslagern = None rechnet get_scaled() selbst, sofort, und
    # beide Seiten sehen dasselbe. Gesetzt wird es in Frontend.__init__
    # (ART.auslagern = PREWARMER.dringend), also muss es NACH jedem
    # make_frontend() wieder heraus.
    # Dass das Auslagern selbst funktioniert, pruefen die Tests aus
    # Build 105.
    A.ART.auslagern = None
    namen = KEYS if anzahl is None else KEYS[:anzahl]
    # Der Systemkey MUSS gesetzt sein - sonst liefert
    # _category_art_key() None und geprueft wuerde der Platzhalter
    # statt der Karte mit dem Bild. Derselbe Stolperstein wie in
    # test_hauptseite_spuren.py.
    f.cats = [(k, {"items": [], "folders": {}}, k) for k in namen]
    f.cat_i = 0
    f.cat_scroll = 0
    return f


# ---------------------------------------------------------------------------
print("Test 1: sechs Ansichten an einem Schalter")
# ---------------------------------------------------------------------------
check("ANSICHTEN_HAUPT hat genau die sechs",
      S.ANSICHTEN_HAUPT == ALLE, "%r" % (S.ANSICHTEN_HAUPT,))
check("drei davon brauchen HDMI",
      S.ANSICHTEN_HAUPT_NUR_HD == NEU, "%r" % (S.ANSICHTEN_HAUPT_NUR_HD,))
check("und die drei neuen stehen HINTEN",
      S.ANSICHTEN_HAUPT[:3] == ("liste", "raster", "galerie"),
      "wer die Reihenfolge der alten drei aendert, aendert fuer jeden "
      "Bestandsnutzer, was die Taste tut")
os.remove(S.ANSICHT_HAUPT_FILE) if os.path.exists(S.ANSICHT_HAUPT_FILE) \
    else None
H._zwischenspeicher_leeren()
check("ohne Datei: liste", S.ansicht_haupt_lesen() == "liste",
      "%r" % (S.ansicht_haupt_lesen(),))
for wert in ALLE:
    S.ansicht_haupt_schreiben(wert)
    H._zwischenspeicher_leeren()
    check("geschrieben wird, was man setzt (%s)" % wert,
          S.ansicht_haupt_lesen() == wert)
with open(S.ANSICHT_HAUPT_FILE, "w") as fh:
    fh.write("\x00quatsch\n")
H._zwischenspeicher_leeren()
check("Muell in der Datei faellt auf liste zurueck",
      S.ansicht_haupt_lesen() == "liste",
      "eine von Hand verstellte Datei darf das Frontend nicht in einen "
      "Zustand bringen, aus dem man ohne Texteditor nicht herauskommt")

# ---------------------------------------------------------------------------
print()
print("Test 2: es gibt KEINEN zweiten Schalter mehr")
# ---------------------------------------------------------------------------
# DAS IST DIE EIGENTLICHE ZUSAGE VON BUILD 316. Bliebe der alte
# Schalter irgendwo stehen, waere der Fehler von Build 314 zurueck:
# zwei Quellen fuer dieselbe Frage, und eine sticht die andere stumm
# aus.
_qm = open(os.path.join(_REPO, "frontend", "fe", "menu.py"),
           encoding="utf-8").read()
check("kein Menuepunkt 'haupt_stil' mehr", '"haupt_stil"' not in _qm,
      "er steht jetzt in 'ansicht_haupt' mit drin")
check("und kein Zweig dafuer", 'kind == "haupt_stil"' not in _ROH)
check("frontend.py ruft haupt_stil_weiter() nicht mehr",
      "haupt_stil_weiter(" not in _ROH)
check("und kennt kein _haupt_stil() mehr",
      "_haupt_stil()" not in _ROH,
      "die Entscheidung faellt in aktuelle_ansicht_haupt()")
check("der Menuepunkt fuer die Hauptseite ist genau einer",
      _qm.count('"ansicht_haupt"') == 1)
# Die Schreibfunktionen aus Build 314 bleiben in fe/settings.py - die
# Uebernahme braucht sie. Was zaehlt, ist, dass sie NICHTS mehr
# steuern.
check("die alten Funktionen leben nur noch fuer die Uebernahme",
      hasattr(S, "haupt_stil_lesen") and hasattr(S, "haupt_stil_uebernehmen"))

# ---------------------------------------------------------------------------
print()
print("Test 3: die HD-Regel an genau einer Stelle")
# ---------------------------------------------------------------------------
check("es gibt genau ein _ansicht_haupt_hd()",
      len(re.findall(r"def _ansicht_haupt_hd", _ROH)) == 1)
check("die Schwelle ist dieselbe wie im Haus (720)", "720" in _HD,
      "eine zweite Zahl waere eine zweite Gelegenheit, "
      "auseinanderzulaufen")
check("aktuelle_ansicht_haupt() geht durch sie hindurch",
      "_ansicht_haupt_hd(" in nur_code(
          koerper(_QF, "aktuelle_ansicht_haupt", "Frontend")),
      "sonst holt der Zeichenweg seine Ansicht woanders her als die "
      "Navigation - genau der Fehler aus Build 314")
for b, h, ansicht, erwartet in (
        (1920, 1080, "kachelwand", "kachelwand"),
        (1920, 1080, "dashboard", "dashboard"),
        (1920, 1080, "karussell", "karussell"),
        (1280, 720, "kachelwand", "kachelwand"),
        (1080, 1920, "dashboard", "dashboard"),
        (320, 240, "kachelwand", "liste"),
        (640, 480, "dashboard", "liste"),
        (640, 480, "karussell", "liste"),
        (320, 240, "raster", "raster"),
        (1920, 1080, "liste", "liste")):
    f = seite(b, h, ansicht)
    ist = f.aktuelle_ansicht_haupt()
    check("%4dx%-4d  %-10s -> %s" % (b, h, ansicht, erwartet),
          ist == erwartet, "" if ist == erwartet else "%r" % ist)

f = seite(1920, 1080, "liste")
runde = []
_j = "liste"
for _ in range(7):
    _j = f._ansicht_haupt_weiter(_j)
    runde.append(_j)
check("auf HDMI laeuft die Taste durch alle sechs",
      runde == list(ALLE[1:]) + ["liste", "raster"], "%r" % (runde,))
f = seite(320, 240, "liste")
runde = []
_j = "liste"
for _ in range(4):
    _j = f._ansicht_haupt_weiter(_j)
    runde.append(_j)
check("auf der Roehre ueberspringt sie die drei HD-Ansichten",
      runde == ["raster", "galerie", "liste", "raster"], "%r" % (runde,))
check("eine Taste, die dreimal nichts tut, haelt man fuer kaputt",
      "ANSICHTEN_HAUPT_NUR_HD" in _WEITER)

# ---------------------------------------------------------------------------
print()
print("Test 4: ein Wechsel wirft ALLE Zwischenspeicher weg")
# ---------------------------------------------------------------------------
for schluessel in ("_pgc_fast_key", "_kat_raster_fast_key",
                   "_kat_galerie_fast_key", "_kat_wand_fast_key",
                   "_kat_dash_fast_key", "_kat_kar_fast_key"):
    check("ansicht_haupt_setzen() setzt %s zurueck" % schluessel,
          schluessel in _SETZEN,
          "bliebe auch nur einer stehen, zeichnete er beim naechsten "
          "Wechsel zurueck seinen schnellen Pfad in ein fremdes Bild")
check("und erzwingt einen vollen Aufbau",
      "_force_full_redraw = True" in _SETZEN
      and "mark_full_redraw()" in _SETZEN)

# ---------------------------------------------------------------------------
print()
print("Test 5: die Geometrien liegen im Bild")
# ---------------------------------------------------------------------------
for b, h in ((1920, 1080), (1280, 720), (1080, 1920), (1920, 1200),
             (2560, 1440)):
    f = seite(b, h, "kachelwand")
    g = f.kachelwand_geometrie(f.kat_layout())
    letzte = g["spalten"] * g["zeilen"] - 1
    fx, fy, fw, fh = f._kachel_feld(g, letzte)
    check("%4dx%-4d Kachelwand: letzte Kachel im Bild" % (b, h),
          fx >= 0 and fy >= 0 and fx + fw <= b and fy + fh <= h,
          "%r" % ((fx, fy, fw, fh),))
    check("%4dx%-4d Kachelwand: Bild und Text passen in die Kachel"
          % (b, h),
          g["bild_h"] + g["text_h"] + 2 * g["pad"] <= g["kachel_h"])
    check("%4dx%-4d Kachelwand: mindestens 2x1" % (b, h),
          g["spalten"] >= 2 and g["zeilen"] >= 1,
          "%dx%d" % (g["spalten"], g["zeilen"]))

    f = seite(b, h, "dashboard")
    g = f.dashboard_geometrie(f.kat_layout())
    check("%4dx%-4d Dashboard: Liste und Tafel ueberlappen nicht" % (b, h),
          g["ox"] + g["lw"] <= g["px"])
    check("%4dx%-4d Dashboard: Tafel im Bild" % (b, h),
          g["px"] + g["pw"] <= b and g["py"] + g["ph"] <= h)
    for fx, fy, fw, fh in g["felder"]:
        check("%4dx%-4d Dashboard: Feld liegt in der Tafel" % (b, h),
              fx >= g["px"] and fy >= g["py"]
              and fx + fw <= g["px"] + g["pw"]
              and fy + fh <= g["py"] + g["ph"])
    check("%4dx%-4d Dashboard: der Text steht unter dem Bild" % (b, h),
          g["text_y"] >= g["bild_y"] + g["bild_h"])

    f = seite(b, h, "karussell")
    g = f.karussell_geometrie(f.kat_layout())
    p = g["plaetze"]
    groessen = [e[3] for e in p]
    check("%4dx%-4d Karussell: fuenf Plaetze" % (b, h), len(p) == 5)
    check("%4dx%-4d Karussell: Mitte ist Platz 0 und am groessten"
          % (b, h), p[2][0] == 0 and groessen[2] == max(groessen))
    check("%4dx%-4d Karussell: symmetrisch" % (b, h),
          groessen[0] == groessen[4] and groessen[1] == groessen[3])
    check("%4dx%-4d Karussell: alles im Bild" % (b, h),
          all(e[1] >= 0 and e[1] + e[3] <= b
              and e[2] >= 0 and e[2] + e[4] <= h for e in p))
    check("%4dx%-4d Karussell: der Text beginnt unter der Reihe" % (b, h),
          g["text_y"] > p[2][2] + p[2][4])
    check("%4dx%-4d Karussell: die Karten liegen quer" % (b, h),
          g["mitte_b"] > g["mitte_h"],
          "ein Geraetefoto liegt quer, ein Spielcover steht hochkant")

# ---------------------------------------------------------------------------
print()
print("Test 6: alle sechs zeichnen")
# ---------------------------------------------------------------------------
for ansicht in ALLE:
    for b, h in ((1920, 1080), (1280, 720), (1080, 1920), (2560, 1440)):
        f = seite(b, h, ansicht)
        try:
            f.draw_page_cats(flip=False)
            f.cat_i = 1
            f.draw_page_cats(flip=False)       # ab hier der schnelle Weg
            f.cat_i = len(f.cats) - 1          # ans Ende
            f.draw_page_cats(flip=False)
            f.cat_i = 0                        # und zurueck an den Anfang
            f.draw_page_cats(flip=False)
            ok, fehler = True, ""
        except Exception as e:                           # noqa: BLE001
            ok, fehler = False, "%s: %s" % (type(e).__name__, e)
            traceback.print_exc(limit=4)
        check("%-10s %4dx%-4d vier Schritte, auch an beiden Raendern"
              % (ansicht, b, h), ok, fehler)
    # Und mit EINER einzigen Kategorie - im Karussell zeigen dann alle
    # fuenf Plaetze auf denselben Eintrag, im Raster wird die Seite
    # nicht voll.
    f = seite(1920, 1080, ansicht, anzahl=1)
    try:
        f.draw_page_cats(flip=False)
        f.draw_page_cats(flip=False)
        ok, fehler = True, ""
    except Exception as e:                               # noqa: BLE001
        ok, fehler = False, "%s: %s" % (type(e).__name__, e)
        traceback.print_exc(limit=4)
    check("%-10s eine einzige Kategorie" % ansicht, ok, fehler)

# ---------------------------------------------------------------------------
print()
print("Test 7: der schnelle Pfad ist bitgenau wie ein voller Aufbau")
# ---------------------------------------------------------------------------


def lauf(ansicht, w, h, schritte, richtung=1):
    f = seite(w, h, ansicht)
    f.draw_page_cats(flip=False)          # voller Aufbau
    f.draw_page_cats(flip=False)          # ab hier der schnelle Weg
    n = len(f.cats)
    for _ in range(schritte):
        f.cat_i = (f.cat_i + richtung) % n
        f.draw_page_cats(flip=False)
    schnell = bytes(f.fb.buf)

    g = seite(w, h, ansicht)
    g.cat_i = f.cat_i
    g.cat_scroll = f.cat_scroll
    # _pulse_t0 ist ein Wert JE INSTANZ - ohne diese Zeile vergleicht
    # man zwei Phasen desselben Schimmerns und haelt den
    # Farbunterschied fuer einen Zeichenfehler (siehe
    # test_hauptseite_spuren.py).
    g._pulse_t0 = f._pulse_t0
    g.fb.mark_full_redraw()
    g.draw_page_cats(flip=False)
    label = "%-10s %4dx%-4d %+d x%d" % (ansicht, w, h, richtung, schritte)
    if gleich(schnell, g.fb.buf):
        check(label + ": bitgenau", True)
    else:
        n_, wo = abweichung(schnell, g.fb.buf)
        check(label + ": bitgenau", False,
              "%d Bildpunkte, z.B. %s" % (n_, wo))


for _a in NEU:
    for _w, _h in ((1920, 1080), (1280, 720)):
        lauf(_a, _w, _h, 3, 1)
        lauf(_a, _w, _h, 7, 1)
        lauf(_a, _w, _h, 4, -1)

# ---------------------------------------------------------------------------
print()
print("Test 8: ECHTE Tastenschritte, einmal rundherum")
# ---------------------------------------------------------------------------
# DER TEST, DER DEN GEMELDETEN FEHLER GEFUNDEN HAETTE. Test 7 ruft
# draw_page_cats() direkt auf - die Taste geht aber zuerst durch
# _draw_navigate_cats(). Ein Test, der den Zeichenweg von unten
# anstoesst, prueft nie, ob ihn ueberhaupt jemand erreicht.


def rundherum(ansicht, w=1920, h=1080):
    f = seite(w, h, ansicht)
    f.draw_page_cats(flip=False)
    n = len(f.cats)
    schlecht = []
    for _ in range(n + 2):
        alt = f.cat_i
        f.cat_i = (f.cat_i + 1) % n       # genau das tut nav_anwenden()
        if not f._draw_navigate_cats(alt):
            f.draw_page_cats(flip=False)
        ist = bytes(f.fb.buf)
        g = seite(w, h, ansicht)
        g.cat_i = f.cat_i
        g.cat_scroll = f.cat_scroll
        g._pulse_t0 = f._pulse_t0
        g.fb.mark_full_redraw()
        g.draw_page_cats(flip=False)
        if not gleich(ist, g.fb.buf):
            schlecht.append((f.cat_i, abweichung(ist, g.fb.buf)[0]))
    check("%-10s %d Tastenschritte bitgenau" % (ansicht, n + 2),
          not schlecht,
          "" if not schlecht else "%d Schritte daneben, erster bei "
          "cat_i=%d mit %d Bildpunkten"
          % (len(schlecht), schlecht[0][0], schlecht[0][1]))


for _a in ALLE:
    rundherum(_a)

check("der leichte Pfad laesst nur die Liste durch",
      '!= "liste"' in _NAV,
      "bei jeder anderen Ansicht zeichnet ein eigener Weg - wer sich "
      "hier trotzdem fuer zustaendig haelt, malt Listenzeilen in ein "
      "fremdes Bild")

# ---------------------------------------------------------------------------
print()
print("Test 9: die Uebernahme aus Build 314/315")
# ---------------------------------------------------------------------------
S.ansicht_haupt_schreiben("liste")
with open(S.HAUPT_STIL_FILE, "w") as fh:
    fh.write("dashboard")
H._zwischenspeicher_leeren()
check("sie traegt den alten Wert in die Ansicht",
      S.haupt_stil_uebernehmen() == "dashboard")
check("und die Ansicht steht danach darauf",
      S.ansicht_haupt_lesen() == "dashboard",
      "%r" % (S.ansicht_haupt_lesen(),))
check("die alte Datei steht auf klassisch",
      open(S.HAUPT_STIL_FILE).read().strip() == "klassisch")
S.ansicht_haupt_schreiben("liste")
H._zwischenspeicher_leeren()
check("ein zweiter Lauf tut nichts mehr",
      S.haupt_stil_uebernehmen() is None
      and S.ansicht_haupt_lesen() == "liste",
      "sonst holte sie den Nutzer bei jedem Start zurueck, auch wenn "
      "er die Ansicht inzwischen bewusst umgestellt hat")
os.remove(S.HAUPT_STIL_FILE)
check("ohne alte Datei: nichts zu tun",
      S.haupt_stil_uebernehmen() is None)
with open(S.HAUPT_STIL_FILE, "w") as fh:
    fh.write("klassisch")
check("und 'klassisch' ist kein Grund, etwas zu aendern",
      S.haupt_stil_uebernehmen() is None)
check("sie wird beim Start WIRKLICH gerufen",
      "haupt_stil_uebernehmen()" in nur_code(
          koerper(_QF, "__init__", "Frontend")),
      "eine Uebernahme, die niemand ruft, ist eine Zeile Doku und "
      "sonst nichts")
check("und zwar abgesichert",
      "haupt_stil_uebernehmen" in _ROH and "except Exception" in nur_code(
          koerper(_QF, "__init__", "Frontend")),
      "eine Uebernahme, die schiefgeht, darf den Start nicht aufhalten")

# ---------------------------------------------------------------------------
print()
print("Test 10: der Fotosatz - Vorrang UND Rueckfall")
# ---------------------------------------------------------------------------
check("_kat_logo kennt den Fotosatz",
      "SYSART_FOTO_BASE" in _LOGO and "foto" in _LOGO)
check("gefragt wird ueber die gemerkte Liste, nicht ueber einen "
      "zweiten get_scaled-Versuch", "_sysart_foto_namen()" in _LOGO,
      "ein fehlendes Bild und ein uebersprungenes liefern beide None")

f = seite(1920, 1080, "kachelwand")
namen = f._sysart_foto_namen()
check("der Fotosatz wird gefunden", len(namen) >= 20,
      "%d Dateien" % len(namen))

_gefragt = []
_echt = A.ART.get_scaled


def _mitschreiben(pfad, *a, **k):
    _gefragt.append(pfad)
    return _echt(pfad, *a, **k)


A.ART.get_scaled = _mitschreiben
try:
    for idx, key in enumerate(KEYS):
        _gefragt[:] = []
        f._kat_logo(idx, 120, 90, foto=True)
        aus_foto = any(p.startswith(FOTOS) for p in _gefragt)
        soll = key in MIT_FOTO
        check("%-20s -> %s" % (key, "Foto" if soll else "Abzeichen"),
              aus_foto is soll, "%r" % (_gefragt,))
    _gefragt[:] = []
    f._kat_logo(KEYS.index("NES"), 120, 90)
    check("ohne foto=True bleibt es beim Abzeichen",
          _gefragt and all(p.startswith(SYSART)
                           and not p.startswith(FOTOS) for p in _gefragt),
          "%r" % (_gefragt,))
finally:
    A.ART.get_scaled = _echt

check("die drei klassischen Ansichten fragen NICHT nach Fotos",
      "foto=True" not in nur_code(
          koerper(_QF, "_kat_kachel_zeichnen", "Frontend")),
      "sein Wunsch war ausdruecklich 'fuer das neue'")

# ---------------------------------------------------------------------------
print()
print("Test 11: die Fotodateien sind heil und einheitlich")
# ---------------------------------------------------------------------------
PANEL = (28, 32, 44)
dateien = sorted(n for n in os.listdir(FOTOS) if n.endswith(".art"))
check("es liegen Dateien da", len(dateien) >= 20, "%d" % len(dateien))
masse = set()
for n in dateien:
    roh = open(os.path.join(FOTOS, n), "rb").read()
    if roh[:4] != b"ART1":
        check("%-24s ART1-Kopf" % n, False)
        continue
    b, h = struct.unpack("<HH", roh[4:8])
    masse.add((b, h))
    try:
        pix = zlib.decompress(roh[8:])
    except zlib.error as e:                              # noqa: BLE001
        check("%-24s entpackbar" % n, False, str(e))
        continue
    # Die Ecke MUSS C_PANEL sein (BGRA) - das Frontend blittet die
    # Datei undurchsichtig und sieht den Alphakanal gar nicht an. Eine
    # andere Eckfarbe waere auf der Karte ein sichtbarer Kasten.
    ecke = (pix[2], pix[1], pix[0])
    check("%-24s %dx%d, Ecke %r" % (n, b, h, ecke),
          len(pix) == b * h * 4 and ecke == PANEL)
check("alle Fotos haben dasselbe Mass", len(masse) == 1, "%r" % (masse,))
check("und zwar quer",
      bool(masse) and list(masse)[0][0] > list(masse)[0][1], "%r" % (masse,))
check("die Abzeichen sind unangetastet geblieben",
      struct.unpack("<HH", open(os.path.join(SYSART, "NES.art"),
                                "rb").read()[4:8]) == (320, 420),
      "sysart/ bleibt hochkant 320x420, der Fotosatz liegt daneben")
check("das Werkzeug zum Nachliefern liegt bei",
      os.path.exists(os.path.join(_REPO, "PC-Tools",
                                  "sysart_foto_convert.py")))

# ---------------------------------------------------------------------------
print()
print("Test 12: kein zweiter Weg fuer etwas, das es schon gibt")
# ---------------------------------------------------------------------------
for name, quelle in (("Kachelwand", _WAND + _WKACHEL),
                     ("Dashboard", _DASH + _TAFEL + _ZEILE),
                     ("Karussell", _KAR)):
    check("%s: Quelltext gefunden" % name, bool(quelle.strip()),
          "%d Zeichen" % len(quelle))
    for ruf, wofuer in (("self._kat_logo(", "das Kategoriebild"),
                        ("self._kachel_platzhalter(", "der leere Kasten"),
                        ("self._restore_row_bg(", "das Freiraeumen")):
        check("%-11s %-28s -> %s" % (name, ruf, wofuer), ruf in quelle)
    check("%s: die Zahlen kommen aus einem vorhandenen Helfer" % name,
          any(h in quelle for h in ("self._kat_eintraege(",
                                    "self._kat_favoriten(",
                                    "self._kat_infozeilen(")))
    check("%s: und zaehlt NICHT selbst" % name,
          'node.get("items"' not in quelle
          and '.get("items", ())' not in quelle,
          "ein Durchlauf ueber die Eintraege je Kachel und Schritt "
          "waere genau die Sorte Aufwand, die wir uns abgewoehnt haben")
for name, quelle in (("Kachelwand", _WAND), ("Dashboard", _DASH),
                     ("Karussell", _KAR)):
    for ruf in ("self._kat_kopf(", "self._kat_fusszeile(",
                "self._rechtecke_flippen(", "self._overlay_active()",
                "fb.full_redraw_gen"):
        check("%-11s %s" % (name, ruf), ruf in quelle)
check("die Kachelwand benutzt das Kachelfeld der Hauptseite",
      "self._kachel_feld(" in _WKACHEL)
check("das Karussell rechnet umlaufend", "% gesamt" in _KAR,
      "in einem Karussell gibt es kein 'da ist nichts mehr'")
check("die Aussparung wird an EINER Stelle gerechnet",
      len(re.findall(r"def _kat_bild_luecke", _ROH)) == 1
      and "_kat_bild_luecke(" in _WKACHEL
      and "_kat_bild_luecke(" in _TAFEL
      and "_kat_bild_luecke(" in _KAR)
for name, quelle in (("Kachelwand", _WKACHEL), ("Dashboard", _TAFEL),
                     ("Karussell", _KAR)):
    check("%s: das Bild wird VOR der Karte geholt" % name,
          quelle.index("self._kat_logo(")
          < quelle.index("karte_mit_schatten("),
          "wer noch nicht weiss, wo das Bild hinkommt, kann seine "
          "Flaeche nicht aussparen (Build 305)")
    check("%s: und die Karte bekommt die Aussparung" % name,
          "aussparen=" in quelle and "hintergrund_rgb=" in quelle)
check("der Verteiler steht an genau einer Stelle",
      len(re.findall(r"self\._draw_cats_stil\(", _ROH)) == 1
      and "_draw_cats_stil(" in _IMPL)
check("und fragt die HD-Liste, nicht einen zweiten Schalter",
      "ANSICHTEN_HAUPT_NUR_HD" in _IMPL)
_VERT = nur_code(koerper(_QF, "_draw_cats_stil", "Frontend"))
for ansicht in NEU:
    check("der Verteiler kennt %s" % ansicht,
          '"%s"' % ansicht in _VERT and "_draw_cats_%s(" % ansicht in _VERT)
check("und ein unbekannter Wert faellt durch", "return False" in _VERT)

# ---------------------------------------------------------------------------
print()
print("Test 13: die Namen stehen woertlich in beiden Sprachen")
# ---------------------------------------------------------------------------
# Der Menuepunkt setzt den Schluessel zusammen (t("ansicht_" + wert)),
# und zusammengesetzte Schluessel sieht die Vollstaendigkeitspruefung
# nicht - daran ist Build 309 schon einmal haengengeblieben. Diese
# Schleife ist der Ersatz: sie nennt jeden der sechs einzeln.
for wert in S.ANSICHTEN_HAUPT:
    k = "ansicht_" + wert
    e = TR.TRANSLATIONS.get(k)
    check("Text %-22s in beiden Sprachen" % k,
          bool(e) and bool(e.get("de")) and bool(e.get("en")),
          "" if e else "fehlt ganz")
for k in ("dash_eintraege", "dash_ordner", "dash_favoriten",
          "dash_anteil", "sys_ansicht_haupt"):
    e = TR.TRANSLATIONS.get(k)
    check("Text %-22s in beiden Sprachen" % k,
          bool(e) and bool(e.get("de")) and bool(e.get("en")),
          "" if e else "fehlt ganz")
check("sys_ansicht_haupt hat genau einen Platzhalter",
      all(len(re.findall(r"%[sd]", TR.TRANSLATIONS["sys_ansicht_haupt"][sp]))
          == 1 for sp in ("de", "en")))
for k in list(TR.TRANSLATIONS):
    if k.startswith("haupt_stil_") or k == "sys_haupt_stil":
        check("der alte Schluessel %s ist raus" % k, False,
              "er beschriebe einen Schalter, den es nicht mehr gibt")

# ---------------------------------------------------------------------------
print()
print("Test 14: die Steuerung folgt der Form, nicht der Gewohnheit")
# ---------------------------------------------------------------------------
# GEMELDET ZU BUILD 316: "liste mit hoch runter passt, raster galerie
# und karussell muss mit links rechts steuerbar sein, hier greift wohl
# noch die steuerung aus der listen ansicht".
#
# Die Zuordnung stand als Verschachtelung mitten in run() und war von
# keinem Test erreichbar - genau deshalb ist niemandem aufgefallen,
# dass die drei neuen Ansichten darin gar nicht vorkamen. Seit Build
# 317 ist es eine Methode, und hier wird sie gerufen.
f = seite(1920, 1080, "liste")
f._kat_raster_spalten = 6
MOVE, PAGE = 1, 9
erwartet = {
    "liste":      (MOVE, PAGE),   # senkrecht
    "dashboard":  (MOVE, PAGE),   # senkrecht
    "raster":     (6, MOVE),      # Flaeche: hoch/runter eine REIHE
    "kachelwand": (6, MOVE),      # Flaeche
    "galerie":    (PAGE, MOVE),   # waagerecht: links/rechts ein Nachbar
    "karussell":  (PAGE, MOVE),   # waagerecht
}
for ansicht in ALLE:
    ist = f.nav_schritte(ansicht, "_kat_raster_spalten", MOVE, PAGE)
    soll = erwartet[ansicht]
    check("%-11s hoch/runter=%s  links/rechts=%s"
          % (ansicht, soll[0], soll[1]), ist == soll, "%r" % (ist,))
check("keine der sechs faellt mehr stillschweigend in den Rueckfall",
      all(f.nav_schritte(a, "_kat_raster_spalten", MOVE, PAGE)
          != (MOVE, PAGE) for a in ("raster", "kachelwand", "galerie",
                                    "karussell")),
      "die Liste und das Dashboard SOLLEN dort landen, die vier "
      "anderen nicht")
check("run() benutzt dieselbe Methode und keine eigene Rechnung",
      len(re.findall(r"self\.nav_schritte\(", _ROH)) == 3
      and "def _schritte(" not in _ROH,
      # drei: zweimal in run() (Spieleliste und Hauptseite) und
      # einmal in _seiten_aktionen_melden() - genau der Punkt von
      # Build 318, siehe Test 17.
      "zwei Fassungen desselben Schritts sind zwei Gelegenheiten "
      "auseinanderzulaufen")

# ---------------------------------------------------------------------------
print()
print("Test 15: gezaehlt wird rekursiv - und einmal fuer alle")
# ---------------------------------------------------------------------------
# GEMELDET ZU BUILD 316, zwei Saetze, eine Ursache:
#   "warum werden mir bei snes und anderen kategorien 0 eintraege
#    angezeigt obwohl ordner und roms in den kategorien drin sind"
#   "und ab und zu ein paar haenger beim scrollen"
# Gezaehlt wurden nur die Eintraege DIREKT im Knoten (also 0, wenn die
# ROMs in Unterordnern liegen), und zwar je Kategorie beim ersten
# Sichtbarwerden - also mitten im Tastendruck.


def baum(name, direkt, unter, je):
    node = {"folders": {},
            "items": [(name + "_d%d" % i, "game", None)
                      for i in range(direkt)]}
    for u in range(unter):
        node["folders"]["U%d" % u] = {
            "folders": {},
            "items": [(name + "_u%d_%d" % (u, i), "game", None)
                      for i in range(je)]}
    return (name, node, name)


f = seite(1920, 1080, "kachelwand")
f.cats = [baum("SNES", 0, 3, 400),      # ALLES in Unterordnern
          baum("NES", 12, 2, 100),      # gemischt
          baum("GBA", 50, 0, 0),        # nur direkt
          baum("LEER", 0, 0, 0)]        # wirklich leer
f._favorites_set = {"SNES_u0_1", "SNES_u0_2", "NES_d3", "GBA_d7"}
f._kat_zahlen_cache = None
for i, (n, soll) in enumerate((("SNES", 1200), ("NES", 212),
                               ("GBA", 50), ("LEER", 0))):
    ist = f._kat_eintraege(i)
    check("%-5s zaehlt %d Eintraege" % (n, soll), ist == soll,
          "%r - Unterordner zaehlen mit" % (ist,))
check("die groesste ist die groesste", f._kat_groesste() == 1200,
      "%r" % (f._kat_groesste(),))
check("und eine leere Sammlung ergibt trotzdem keine Null als Teiler",
      f._kat_groesste() >= 1,
      "der Balken teilt dadurch - eine Null waere ein Absturz")

# ALLE auf einmal, nicht je Kategorie beim Sichtbarwerden: nach EINEM
# Aufruf muessen alle Zahlen dastehen. Das ist die Zusage gegen die
# Haenger.
f._kat_zahlen_cache = None
f._kat_eintraege(0)
check("ein Aufruf fuellt die Tabelle fuer ALLE Kategorien",
      len(f._kat_zahlen_cache["zahlen"]) == len(f.cats),
      "sonst kommt bei jeder neuen Kachelseite ein Durchlauf mitten "
      "im Tastendruck dazu")
check("die Favoriten stehen NICHT darin",
      f._kat_zahlen_cache["favoriten"] == {},
      "das ist der teure Teil - er wird nur fuer die markierte "
      "Kategorie des Dashboards gebraucht")
for i, soll in ((0, 2), (1, 1), (2, 1), (3, 0)):
    check("Favoriten in Kategorie %d: %d" % (i, soll),
          f._kat_favoriten(i) == soll, "%r" % (f._kat_favoriten(i),))
check("auch Favoriten werden rekursiv gezaehlt",
      f._kat_favoriten(0) == 2,
      "zwei der drei SNES-Favoriten liegen in einem Unterordner")
check("und einmal gezaehlt, bleiben sie gemerkt",
      0 in f._kat_zahlen_cache["favoriten"])
_alt = f._kat_zahlen_cache
f.cats = f.cats[:2]
f._kat_eintraege(0)
check("eine geaenderte Kategorienliste wirft die Tabelle weg",
      f._kat_zahlen_cache is not _alt
      and len(f._kat_zahlen_cache["zahlen"]) == 2)

check("die Kachelwand holt nur die Eintragszahl",
      "_kat_eintraege(" in _WKACHEL and "_kat_favoriten(" not in _WKACHEL,
      "haette sie die Favoriten mitgezaehlt, waere der Haenger "
      "geblieben - nur an einer anderen Stelle")
check("und das Dashboard holt die Favoriten nur fuer die markierte",
      "_kat_favoriten(" in _TAFEL and "_kat_favoriten(" not in _ZEILE)
check("gezaehlt wird mit dem Zaehler des Hauses",
      "_count_tree_items(" in nur_code(
          koerper(_QF, "_kat_zaehlwerk", "Frontend")),
      "dieselbe Zahl, die auch der Einrichtungsassistent nennt - "
      "zwei Zaehlweisen waeren zwei Wahrheiten")


# ---------------------------------------------------------------------------
print()
print("Test 16: der Coverflow ist eine Ansicht, kein zweiter Schalter")
# ---------------------------------------------------------------------------
# NUTZERWUNSCH ZU BUILD 317: "koennen wir zusaetzlich die alte galerie
# ansicht auch noch wieder dazuholen?" - beide gab es, nur hing der
# Coverflow an einem ZWEITEN Schalter ueber der Ansicht. Dieselbe
# Verdopplung wie auf der Hauptseite in Build 314, dieselbe Aufloesung
# wie in Build 316.
check("ANSICHTEN hat vier Werte",
      S.ANSICHTEN == ("liste", "raster", "galerie", "coverflow"),
      "%r" % (S.ANSICHTEN,))
check("und der Coverflow braucht HDMI",
      S.ANSICHTEN_NUR_HD == ("coverflow",), "%r" % (S.ANSICHTEN_NUR_HD,))
check("die alten drei stehen vorn",
      S.ANSICHTEN[:3] == ("liste", "raster", "galerie"),
      "wer die Reihenfolge aendert, aendert fuer jeden Bestandsnutzer, "
      "was die Taste tut")
check("kein Menuepunkt 'galerie_stil' mehr", '"galerie_stil"' not in _qm)
check("und kein Zweig dafuer", 'kind == "galerie_stil"' not in _ROH)
check("frontend.py kennt kein _galerie_flow() mehr",
      "def _galerie_flow" not in _ROH
      and "self._galerie_flow(" not in _ROH,
      "die Entscheidung faellt in aktuelle_ansicht()")
check("der Verteiler kennt den Coverflow",
      '"coverflow"' in nur_code(koerper(_QF, "_draw_items_kacheln",
                                        "Frontend")))
check("und _draw_items_galerie entscheidet nichts mehr",
      "_draw_items_galerie_flow(" not in nur_code(
          koerper(_QF, "_draw_items_galerie", "Frontend")),
      "eine zweite Entscheidungsebene unterhalb der Ansicht ist genau "
      "die Form, die auf der Hauptseite schiefgegangen ist")
for k in ("ansicht_liste", "ansicht_raster", "ansicht_galerie",
          "ansicht_coverflow"):
    e = TR.TRANSLATIONS.get(k)
    check("Text %-20s in beiden Sprachen" % k,
          bool(e) and bool(e.get("de")) and bool(e.get("en")),
          "" if e else "fehlt ganz")
for k in list(TR.TRANSLATIONS):
    if k.startswith("galerie_stil_") or k == "sys_galerie_stil":
        check("der alte Schluessel %s ist raus" % k, False)

# Die HD-Regel und die Taste
_tmp2 = tempfile.mkdtemp(prefix="ansicht_")
S.ANSICHT_FILE = os.path.join(_tmp2, "ansicht")
S.GALERIE_STIL_FILE = os.path.join(_tmp2, "galerie_stil.txt")


def liste(w, h, ansicht):
    S.ansicht_schreiben(ansicht)
    H._zwischenspeicher_leeren()
    H.set_screen(w, h)
    g = H.make_frontend(page=1)
    g._ansicht_je_kat = {}
    g._last_input_time = 0          # siehe seite(), gleicher Grund
    A.ART.auslagern = None          # siehe seite(), gleicher Grund
    return g


for b, h, ansicht, erwartet in ((1920, 1080, "coverflow", "coverflow"),
                                (1280, 720, "coverflow", "coverflow"),
                                (320, 240, "coverflow", "galerie"),
                                (640, 480, "coverflow", "galerie"),
                                (320, 240, "raster", "raster")):
    g = liste(b, h, ansicht)
    ist = g.aktuelle_ansicht()
    check("%4dx%-4d  %-10s -> %s" % (b, h, ansicht, erwartet),
          ist == erwartet, "" if ist == erwartet else "%r" % ist)
check("auf der Roehre faellt er auf die GALERIE zurueck, nicht auf die "
      "Liste", liste(320, 240, "coverflow").aktuelle_ansicht() == "galerie",
      "wer den Coverflow eingestellt hat, will eine Galerie sehen")
g = liste(1920, 1080, "liste")
check("auf HDMI laeuft die Taste durch alle vier",
      [g._ansicht_weiter(x) for x in S.ANSICHTEN]
      == ["raster", "galerie", "coverflow", "liste"],
      "%r" % ([g._ansicht_weiter(x) for x in S.ANSICHTEN],))
g = liste(320, 240, "liste")
check("auf der Roehre ueberspringt sie den Coverflow",
      [g._ansicht_weiter(x) for x in S.ANSICHTEN]
      == ["raster", "galerie", "liste", "liste"],
      "%r" % ([g._ansicht_weiter(x) for x in S.ANSICHTEN],))

# Die Uebernahme aus Build 313
S.ansicht_schreiben("liste")
with open(S.GALERIE_STIL_FILE, "w") as fh:
    fh.write("flow")
H._zwischenspeicher_leeren()
check("die Uebernahme traegt 'flow' in die Ansicht",
      S.galerie_stil_uebernehmen() == "coverflow")
check("und die Ansicht steht danach darauf",
      S.ansicht_lesen() == "coverflow", "%r" % (S.ansicht_lesen(),))
check("die alte Datei steht auf klassisch",
      open(S.GALERIE_STIL_FILE).read().strip() == "klassisch")
S.ansicht_schreiben("liste")
H._zwischenspeicher_leeren()
check("ein zweiter Lauf tut nichts mehr",
      S.galerie_stil_uebernehmen() is None
      and S.ansicht_lesen() == "liste")
check("sie wird beim Start WIRKLICH gerufen",
      "galerie_stil_uebernehmen()" in nur_code(
          koerper(_QF, "__init__", "Frontend")),
      "eine Uebernahme, die niemand ruft, ist eine Zeile Doku")

# ---------------------------------------------------------------------------
print()
print("Test 17: das Tempo kommt aus DERSELBEN Tabelle wie die Schrittweite")
# ---------------------------------------------------------------------------
# GEMELDET ZU BUILD 317: "in denn neuen ansichten koennte das scrollen
# nach links und rechts noch schneller gehen so wie in denn alten
# ansichten auch".
#
# Die Wiederholrate kennt einen langsamen Boden fuer Seitenspruenge
# (REPEAT_FLOOR_PAGE, vier Schritte je Sekunde). Welche Richtung eine
# Seite bewegt, stand in einer ZWEITEN Tabelle - mit dem Kommentar
# "die Zuordnung ist dieselbe wie bei _schritte()". War sie dann
# nicht: die drei neuen Ansichten fehlten dort und galten als
# Seitensprung, obwohl links/rechts bei ihnen die billigste Bewegung
# ueberhaupt ist.
_MELD = nur_code(koerper(_QF, "_seiten_aktionen_melden", "Frontend"))
check("die Meldung FRAGT nav_schritte(), statt nachzubauen",
      "self.nav_schritte(" in _MELD,
      "zwei Tabellen fuer dieselbe Frage sind zwei Gelegenheiten "
      "auseinanderzulaufen - und sie SIND auseinandergelaufen")
check("und baut keine eigene Liste mehr",
      '"raster"' not in _MELD and '"galerie"' not in _MELD)


class _Eingabe(object):
    def __init__(self):
        self.seiten = None

    def seiten_aktionen_setzen(self, aktionen):
        self.seiten = tuple(sorted(aktionen))


def seiten_fuer(ansicht, haupt):
    g = seite(1920, 1080, "liste") if haupt else liste(1920, 1080, "liste")
    g.inp = _Eingabe()
    g._kat_raster_spalten = 6
    g._raster_spalten = 7
    if haupt:
        g.page = 0
        g._ansicht_haupt = ansicht
    else:
        g.page = 1
        g._ansicht_je_kat = {g._ansicht_schluessel(): ansicht}
    g._seiten_aktionen_melden()
    return g.inp.seiten


ERWARTET_HAUPT = {
    "liste": ("left", "right"), "dashboard": ("left", "right"),
    "raster": (), "kachelwand": (),
    "galerie": ("down", "up"), "karussell": ("down", "up"),
}
for ansicht, soll in sorted(ERWARTET_HAUPT.items()):
    ist = seiten_fuer(ansicht, True)
    check("Hauptseite %-11s Seitenaktionen %r" % (ansicht, soll),
          ist == soll, "%r" % (ist,))
check("in Kachelwand und Karussell ist links/rechts NICHT gedeckelt",
      "left" not in (seiten_fuer("kachelwand", True) or ())
      and "left" not in (seiten_fuer("karussell", True) or ()),
      "genau das war der gemeldete Fehler")

shutil.rmtree(TMP, ignore_errors=True)

print()
if fails:
    print("ROT: %d Pruefung(en) fehlgeschlagen:" % len(fails))
    for f in fails:
        print("   - %s" % f)
    sys.exit(1)
print("ALLES GRUEN")
