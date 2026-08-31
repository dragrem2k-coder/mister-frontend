#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft das engere Layout auf CRT (Nutzerwunsch: "haben wir irgendwie
ne Moeglichkeit, das Frontend im CRT-Modus huebscher aussehen zu
lassen?").

WAS DER MANGEL WAR
------------------
Mehrere Abstaende standen als FESTE Pixelzahl im Layout (Kopfblock 46,
Zeilenhoehe 15, Abstand zur Boxart-Karte 20, Kategorie-Zeilenhoehe 22).
Sie skalieren zwar ueber s = H//360 mit - aber s ist sowohl bei 240 als
auch bei 480 Zeilen gleich 1. Bei 240 Zeilen belegten diese Abstaende
also den doppelten ANTEIL des Bildes. Gemessen an echten, in beiden
Aufloesungen gerenderten Bildern:

                       CRT 320x240   HDMI 1920x1080
    Zeichen pro Zeile       17            35
    sichtbare Spiele        10            17
    Kategorien im Menue      7            12
    Kopfzeilenblock         24 %          18 %

WAS HIER GEPRUEFT WIRD
----------------------
"Sieht huebscher aus" kann kein Test pruefen. Geprueft wird deshalb das
objektiv Nachrechenbare - und vor allem die zwei Dinge, die beim Bauen
tatsaechlich schiefgegangen sind:

1. Der Gewinn ist da (mehr Zeilen, mehr Zeichen).
2. HDMI und 640x480 bleiben BIT-genau unveraendert - die Aenderung
   sollte ausschliesslich CRT betreffen.
3. Der Kopfbereich kollidiert nicht mit der ersten Zeile. Genau das ist
   beim Bauen ZWEIMAL passiert (Auswahlbalken lief in die Eintragszahl)
   und faellt in reinen Zahlen nicht auf - deshalb wird die Freiraum-
   Rechnung hier ausdruecklich mitgeprueft.

Ausfuehren:
    python3 tools/test_crt_layout.py
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import _harness as H                                 # noqa: E402

fm = H.fm
fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


def layouts(w, h):
    H.set_screen(w, h)
    f = H.make_frontend(page=0)
    f._layout_items_cache = {}
    return f, f.layout_cats(), f.layout_items(True), f.layout_items(False)


def kennzahlen(w, h):
    _f, Lc, Li, Lv = layouts(w, h)
    s = Li["s"]
    breite = Li["list_right"] - Li["list_x"]
    return {
        "s": s,
        "zeichen": breite // (8 * s),
        "zeilen": Li["visible"],
        "kategorien": Lc["visible"],
        "kopf_anteil": 100.0 * Li["list_y"] / h,
        "art_anteil": 100.0 * Lc["art_w"] / w,
        "voll_breite": Lv["list_right"] - Lv["list_x"],
        "L_items": Li,
        "L_cats": Lc,
    }


print("Test 1: auf CRT kommt tatsaechlich mehr aufs Bild")
crt = kennzahlen(320, 240)
# Die Zahlen VOR der Aenderung, gemessen am selben Weg: 17 Zeichen,
# 10 Zeilen, 7 Kategorien, Kopfblock 24 %. Bewusst als Untergrenze
# festgehalten, nicht als exakter Wert - eine spaetere weitere
# Verbesserung soll diesen Test nicht rot faerben.
check("mindestens 20 Zeichen pro Zeile (vorher 17)",
      crt["zeichen"] >= 20, "jetzt %d" % crt["zeichen"])
check("mindestens 13 Spiele gleichzeitig sichtbar (vorher 10)",
      crt["zeilen"] >= 13, "jetzt %d" % crt["zeilen"])
check("mindestens 9 Kategorien im Hauptmenue (vorher 7)",
      crt["kategorien"] >= 9, "jetzt %d" % crt["kategorien"])
check("Kopfblock hoechstens 21 % der Hoehe (vorher 24 %)",
      crt["kopf_anteil"] <= 21.0, "jetzt %.0f %%" % crt["kopf_anteil"])
check("Logo-Spalte hoechstens 30 % der Breite (vorher 34 %)",
      crt["art_anteil"] <= 30.0, "jetzt %.0f %%" % crt["art_anteil"])

print()
print("Test 2: nichts davon faellt auf grosse Schirme durch")
# Der eigentliche Sinn des Tests: die Aenderung soll AUSSCHLIESSLICH
# kleine Schirme betreffen. Diese Werte sind die vor der Aenderung
# gemessenen - jede Abweichung waere ein ungewollter Nebeneffekt.
ERWARTET = {
    (1920, 1080): {"s": 3, "zeichen": 35, "zeilen": 17, "kategorien": 12,
                   "rowh": 45, "list_y_off": 46, "art_w": 340},
    (640, 480):   {"s": 1, "zeichen": 35, "zeilen": 24, "kategorien": 16,
                   "rowh": 15, "list_y_off": 46, "art_w": 217},
}
for (w, h), soll in ERWARTET.items():
    ist = kennzahlen(w, h)
    Li, Lc = ist["L_items"], ist["L_cats"]
    check("%dx%d: %d Zeichen unveraendert" % (w, h, soll["zeichen"]),
          ist["zeichen"] == soll["zeichen"], "jetzt %d" % ist["zeichen"])
    check("%dx%d: %d Zeilen unveraendert" % (w, h, soll["zeilen"]),
          ist["zeilen"] == soll["zeilen"], "jetzt %d" % ist["zeilen"])
    check("%dx%d: %d Kategorien unveraendert" % (w, h, soll["kategorien"]),
          ist["kategorien"] == soll["kategorien"],
          "jetzt %d" % ist["kategorien"])
    check("%dx%d: Zeilenhoehe unveraendert" % (w, h),
          Li["rowh"] == soll["rowh"], "jetzt %d" % Li["rowh"])
    check("%dx%d: Kopfblock unveraendert" % (w, h),
          Li["list_y"] - Li["oy"] == soll["list_y_off"] * soll["s"],
          "jetzt %d" % (Li["list_y"] - Li["oy"]))
    check("%dx%d: Logo-Spalte unveraendert" % (w, h),
          Lc["art_w"] == soll["art_w"], "jetzt %d" % Lc["art_w"])

print()
print("Test 3: der Kopfbereich kollidiert nicht mit der ersten Zeile")
# BUGFIX-ABSICHERUNG: beim Bauen lief der Auswahlbalken zweimal in die
# Kopfzeile hinein, weil nur die Zeilenzahl nachgerechnet, aber nicht
# die Hoehe des Kopfes beruecksichtigt wurde. Beide Seiten werden hier
# nachgerechnet - die Zahlen stammen direkt aus dem Zeichencode:
#   Hauptmenue: "MiSTer" mit 3*s ab oy, Kategorienzahl 8*s hoch bei
#               oy+28*s; die Markierung beginnt 4*s OBERHALB von y0
#               (siehe _draw_cat_row()).
#   Spieleliste: Titel bis 2*s hoch ab oy, Eintragszahl 8*s hoch bei
#               oy+22*s; die Zeilen beginnen bei list_y.
for w, h in ((320, 240), (640, 480), (1920, 1080)):
    ist = kennzahlen(w, h)
    Li, Lc = ist["L_items"], ist["L_cats"]
    s = Li["s"]
    kopf_unterkante = Lc["oy"] + 28 * s + 8 * s
    balken_oberkante = Lc["y0"] - 4 * s
    check("%dx%d Hauptmenue: Balken beginnt unter der Kategorienzahl"
          % (w, h), balken_oberkante >= kopf_unterkante,
          "Balken %d, Text endet %d" % (balken_oberkante, kopf_unterkante))
    liste_kopf_unterkante = Li["oy"] + 22 * s + 8 * s
    check("%dx%d Spieleliste: erste Zeile beginnt unter der Eintragszahl"
          % (w, h), Li["list_y"] >= liste_kopf_unterkante,
          "Zeile %d, Text endet %d" % (Li["list_y"], liste_kopf_unterkante))

print()
print("Test 4: der Overscan-Rand bleibt unangetastet")
# Auf einem echten CRT wird der Bildrand abgeschnitten - genau dafuer
# gibt es OVERSCAN_X/Y. Beim Enger-Machen war die Versuchung gross,
# sich dort ein paar Pixel zu holen; das waere genau der falsche Ort.
for w, h in ((320, 240), (1920, 1080)):
    ist = kennzahlen(w, h)
    Li = ist["L_items"]
    s = Li["s"]
    check("%dx%d: Fusszeile haelt den vollen Sicherheitsrand ein"
          % (w, h), Li["footer_y"] == h - Li["oy"] - 13 * s,
          "footer_y %d" % Li["footer_y"])
    check("%dx%d: Fusszeilentext bleibt innerhalb des Rands" % (w, h),
          Li["footer_y"] + 8 * s <= h - Li["oy"] + 13 * s)
    check("%dx%d: linker Rand unveraendert bei %d %%"
          % (w, h, fm.OVERSCAN_X), Li["ox"] == w * fm.OVERSCAN_X // 100)

print()
print("Test 5: die Boxart-Spalte bleibt brauchbar breit")
# Der breitere Listenanteil auf CRT geht zu Lasten der Cover-Spalte.
# Das ist gewollt, darf aber nicht so weit gehen, dass das Cover
# unbrauchbar klein wird: die mitgelieferten CRT-Cover sind laut
# PC-Tools/art_convert.py (Profil "sd") bis zu 104 px breit.
for w, h in ((320, 240), (1920, 1080)):
    ist = kennzahlen(w, h)
    Li = ist["L_items"]
    s = Li["s"]
    luecke = (8 if h < fm.KOMPAKT_H else 20) * s
    art_x0 = Li["list_right"] + luecke
    art_w = (w - Li["ox"]) - art_x0
    nutzbar = art_w - 2 * (6 * s)          # pad in draw_art_panel()
    check("%dx%d: Cover-Spalte mindestens 90 px nutzbar" % (w, h),
          nutzbar >= 90, "jetzt %d px" % nutzbar)

print()
print("Test 6: ohne Boxart nutzt die Liste weiterhin die volle Breite")
for w, h in ((320, 240), (640, 480), (1920, 1080)):
    ist = kennzahlen(w, h)
    check("%dx%d: volle Breite = Bild minus beide Raender" % (w, h),
          ist["voll_breite"] == w - 2 * ist["L_items"]["ox"],
          "jetzt %d" % ist["voll_breite"])

print()
print("Test 7: nach dem Scrollen bleiben keine Reste stehen")
# BUGFIX-ABSICHERUNG (Nutzer-Rueckmeldung mit Foto vom CRT: "wenn ich
# jetzt durch die Menues scrolle oder in System-Ordner, zieht es
# Fehler").
#
# Die engere Zeilenhoehe hat eine STILLE KOPPLUNG aufgedeckt, die
# nirgends im Code stand: der Streifen, den draw_list_row() aufraeumt,
# beginnt bei y-3*s und ist rowh-2*s hoch, der Text ist aber 8*s hoch
# und beginnt bei y. Damit der Text vollstaendig im aufgeraeumten
# Bereich liegt, musste rowh >= 14*s-1 sein. Bei 15*s war das zufaellig
# erfuellt, bei 12 fehlte GENAU EIN Pixel - die unterste Zeile jedes
# Buchstabens blieb stehen. Bei der markierten Zeile ist der
# Zeichenhintergrund die Akzentfarbe, uebrig blieb also ein farbiger
# Strich.
#
# Zwei Ebenen werden geprueft: die Bedingung selbst (nachrechenbar,
# unabhaengig von Testdaten) und das tatsaechliche Bild nach echtem
# Scrollen.
for w, h in ((320, 240), (640, 480), (1920, 1080)):
    ist = kennzahlen(w, h)
    Li = ist["L_items"]
    s = Li["s"]
    band_h = max(Li["rowh"] - 2 * s, 11 * s)
    check("%dx%d: aufgeraeumter Streifen deckt den Text ab" % (w, h),
          band_h >= 3 * s + 8 * s,
          "Streifen %d, gebraucht %d" % (band_h, 3 * s + 8 * s))
    Lc = ist["L_cats"]
    cat_band = max(Lc["rowh"] - 4 * s, 12 * s)
    check("%dx%d: dasselbe im Hauptmenue" % (w, h),
          cat_band >= 4 * s + 8 * s,
          "Streifen %d, gebraucht %d" % (cat_band, 4 * s + 8 * s))


def reste_nach_scrollen(w, h, schritte=6):
    """Scrollt Schritt fuer Schritt ueber den schnellen Zeichenpfad und
    vergleicht das Ergebnis mit einem vollen Neuaufbau derselben
    Position. Liefert die Zahl abweichender Bildpunkte."""
    H.set_screen(w, h)
    fe = H.make_frontend(page=1)
    fe.item_i = 0
    fe.scroll = 0
    fe.draw_page_items(flip=False)
    for k in range(1, schritte + 1):
        fe.item_i = k
        fe._draw_navigate_items(k - 1)
    ist_buf = bytes(fe.fb.buf)

    H.set_screen(w, h)
    ref = H.make_frontend(page=1)
    ref.item_i = schritte
    ref.scroll = 0
    ref.draw_page_items(flip=False)
    soll_buf = bytes(ref.fb.buf)
    return sum(1 for i in range(0, len(ist_buf), 4)
               if ist_buf[i:i + 3] != soll_buf[i:i + 3])


# Zahlen zur Einordnung, gemessen an genau diesem Testaufbau:
#   vor dem Fix   CRT 2785 / HDMI 105717 abweichende Bildpunkte
#   nach dem Fix  CRT  107 / HDMI   2190
# Die verbliebenen liegen alle auf einer einzigen Bildzeile am unteren
# Rand der Boxart-Karte (bekannt, seit jeher vorhanden, auf echter
# Hardware nicht sichtbar). Die Grenzen sind bewusst knapp ueber den
# gemessenen Werten: jeder neue Rest faellt sofort auf.
for w, h, grenze in ((320, 240, 200), (1920, 1080, 3000)):
    n = reste_nach_scrollen(w, h)
    check("%dx%d: hoechstens %d abweichende Bildpunkte nach 6 Schritten"
          % (w, h, grenze), n <= grenze, "gemessen %d" % n)

print()
print("Test 8: was auf dem SCHIRM landet, stimmt - auch beim Hochscrollen")
# BUGFIX-ABSICHERUNG (Nutzer-Rueckmeldung: "beim Hochscrollen verursacht
# der immer noch Zeichenreste in den ROM-Ordnern sowie im
# System-Ordner").
#
# Test 7 verglich den ZEICHENPUFFER (fb.buf). Der war nach dem
# vorherigen Fix sauber - der Fehler blieb trotzdem sichtbar. Grund:
# der Fehler sass gar nicht im Puffer, sondern kam vom vollen
# Seitenaufbau, der auf CRT 4 Pixel WEIT IN DIE KOPFZEILE hineinraeumte
# (fester Rand von 10*s, der vom alten, hoeheren Kopfblock ausging) und
# die untere Haelfte der Eintragszahl wegradierte.
#
# Deshalb wird hier fb.mm verglichen - der Puffer, in den flip()/
# flip_rows() schreiben, also das, was der Nutzer TATSAECHLICH sieht.
# Und bewusst in beide Richtungen: hoch UND runter, jeweils innerhalb
# des Fensters und ueber den Rand hinaus (dort faellt der leichte Pfad
# selbst auf den vollen Aufbau zurueck - genau die Stelle, an der es
# gehakt hat).
def schirm_unterschiede(w, h, start, ziel):
    H.set_screen(w, h)
    fe = H.make_frontend(page=1)
    fe.item_i = start
    fe.scroll = 0
    fe.draw_page_items(flip=True)
    schritt = 1 if ziel > start else -1
    k = start
    while k != ziel:
        alt_i = k
        k += schritt
        fe.item_i = k
        if not fe._draw_navigate_items(alt_i):
            fe.draw_page_items(flip=True)   # wie im echten Ablauf
    ist = bytes(fe.fb.mm)

    H.set_screen(w, h)
    ref = H.make_frontend(page=1)
    ref.item_i = ziel
    ref.scroll = fe.scroll
    ref.draw_page_items(flip=True)
    soll = bytes(ref.fb.mm)
    return sum(1 for i in range(0, len(ist), 4) if ist[i:i + 3] != soll[i:i + 3])


for w, h in ((320, 240), (1920, 1080)):
    for name, a, b in (("runter", 0, 6), ("hoch", 6, 0),
                       ("runter ueber den Rand", 0, 18),
                       ("hoch ueber den Rand", 18, 2)):
        n = schirm_unterschiede(w, h, a, b)
        check("%dx%d %s: Schirmbild stimmt mit dem vollen Aufbau ueberein"
              % (w, h, name), n == 0, "%d abweichende Bildpunkte" % n)

print()
print("Test 9: dasselbe fuer Listen OHNE Boxart-Spalte (System-Menue)")
# BUGFIX-ABSICHERUNG (Nutzer-Rueckmeldung: "im System-Menue bleiben die
# Streifen stehen, im Ordner 'Anzeige & Sound' zum Beispiel").
#
# Genau dieser Fall war nach dem vorigen Anlauf noch kaputt und fiel
# durch alle bisherigen Tests: dort ist has_art False, die Liste nutzt
# die volle Breite, und es gibt kein Boxart-Panel, dessen eigener,
# grosszuegigerer Flip-Bereich den zu schmalen Zeilen-Flip zufaellig mit
# abgedeckt haette. Sichtbar blieb dadurch die unterste Bildzeile des
# Auswahlbalkens jeder verlassenen Zeile stehen - im Puffer war sie
# korrekt aufgeraeumt, sie wurde nur nie auf den Schirm kopiert.
OPTIONEN = ["Menuepunkt Nummer %d mit etwas laengerem Text" % i
            for i in range(14)]


def schirm_unterschiede_ohne_art(w, h, start, ziel):
    def baue(item_i, scroll=0):
        H.set_screen(w, h)
        f = H.make_frontend(page=1)
        node = f.cats[0][1]
        # kind "action" -> keine Boxart-Spalte
        node["items"] = [(t, "action", None) for t in OPTIONEN]
        node.pop("_display_items_cache", None)
        f.item_i = item_i
        f.scroll = scroll
        return f

    fe = baue(start)
    fe.draw_page_items(flip=True)
    schritt = 1 if ziel > start else -1
    k = start
    while k != ziel:
        alt_i = k
        k += schritt
        fe.item_i = k
        if not fe._draw_navigate_items(alt_i):
            fe.draw_page_items(flip=True)
    ist = bytes(fe.fb.mm)
    ref = baue(ziel, fe.scroll)
    ref.draw_page_items(flip=True)
    soll = bytes(ref.fb.mm)
    return sum(1 for i in range(0, len(ist), 4) if ist[i:i + 3] != soll[i:i + 3])


for w, h in ((320, 240), (1920, 1080)):
    for name, a, b in (("runter", 0, 8), ("hoch", 8, 0),
                       ("runter ueber den Rand", 0, 13),
                       ("hoch ueber den Rand", 13, 0)):
        n = schirm_unterschiede_ohne_art(w, h, a, b)
        check("%dx%d ohne Boxart, %s: Schirmbild stimmt" % (w, h, name),
              n == 0, "%d abweichende Bildpunkte" % n)

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for f in fails:
        print("   ", f)
    sys.exit(1)
print("Alle Tests bestanden.")
