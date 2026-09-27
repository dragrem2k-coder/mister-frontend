#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Der Bildwaechter holt das Bild zurueck, wenn MiSTer es wischt.

DER FUND, DER DAZU GEFUEHRT HAT (Build 198)

Der Nutzer meldete nach Build 196, dass beim gehaltenen Scrollen wieder
der Login-Gruss aufblitzt. Der Rueckleser hat gesagt, was los ist:

    RUECKLESER: nach 26.9 s steht in 15 von 15 Proben-Zeilen fremder
    Inhalt (Zeilen 0,16,32,48,90,180,270,360) - 2 Treffer bei 109
    Bildern

FUENFZEHN VON FUENFZEHN - und das ist etwas voellig anderes als der
Befund aus Build 190 (damals "2 von 7 Proben-Zeilen (Zeilen 0,32) - 10
Treffer bei 21 Bildern", also Text oben, dauernd). Hier ist nicht Text
hineingeschrieben, hier ist das ganze Bild nicht mehr unseres: selten,
rund einmal je hundert Bilder, aber vollstaendig. Dazu passt das dmesg
des Nutzers - MiSTer richtet den Bildspeicher im Betrieb mehrfach neu
ein - und weil bei ihm fb_terminal=1 steht, ist die Linux-Konsole die
Ebene darunter. Deshalb ausgerechnet der Login-Gruss.

WARUM ES ERST MIT BUILD 196 AUFFIEL: vorher kopierte jeder
Scrollschritt 804 von 1080 Bildzeilen, ein Wischen war binnen 80 ms zu
drei Vierteln uebermalt. Seit 196 sind es 120 Zeilen. Der Fehler ist
also AELTER als 196 - der hat nur aufgehoert, ihn zufaellig zu
verdecken.

WAS DIESER TEST ABSICHERT

  - dass ein gewischter Schirm erkannt und VOLLSTAENDIG zurueckgeholt
    wird,
  - dass dabei nichts neu gezeichnet werden muss (der Puffer ist
    unversehrt),
  - und das Wichtigste: dass unser EIGENES Zeichnen keinen Fehlalarm
    ausloest. Der Puffer laeuft dem Schirm voellig legitim voraus;
    verglichen wird deshalb gegen das ZULETZT GESCHRIEBENE. Ein Test,
    der nur den Erfolgsfall prueft, haette diesen Unterschied nicht
    bemerkt.
  - dass Dauerfeuer gedrosselt wird - sonst waere jeder Teil-Flip eine
    Vollbildkopie und das Scrollen langsamer als vor Build 196.

Ausfuehren:
    python3 tools/test_bildwaechter.py
"""
import io
import os
import sys

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
sys.path.insert(0, _HIER)

import _harness as H                                     # noqa: E402

fm = H.fm
NOW = H.NOW

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


def neu(hoehe=1080, breite=1920):
    """Ein Framebuffer wie im Pruefstand, mit eingerichtetem Waechter."""
    H.set_screen(breite, hoehe)
    fb = fm.Framebuffer()
    fb._waechter_einrichten()
    return fb


# ---------------------------------------------------------------------------
print("Test 1: der Waechter ist von sich aus an")
# ---------------------------------------------------------------------------
fb = neu()
check("eingeschaltet, ohne dass jemand etwas setzen muss", fb._waechter_an,
      "das ist der Sinn der Sache - er soll bei allen laufen")
check("er hat Proben", len(fb._waechter_offsets) >= 2,
      len(fb._waechter_offsets))
check("zwei davon liegen in den obersten Zeilen (dort steht der Prompt)",
      sum(1 for o in fb._waechter_offsets if o < 64 * fb.stride) >= 2,
      [o // fb.stride for o in fb._waechter_offsets])
check("und sie stehen in verschiedenen Bildspalten",
      len(set(o % fb.stride for o in fb._waechter_offsets))
      == len(fb._waechter_offsets),
      "sonst koennte eine einfarbige Spalte alle gleichzeitig taeuschen")
check("noch kein Sollwert, es wurde ja nichts geschrieben",
      all(s is None for s in fb._waechter_soll))

# ---------------------------------------------------------------------------
print()
print("Test 2: ein gewischter Schirm wird ganz zurueckgeholt")
# ---------------------------------------------------------------------------
fb = neu()
fb.buf[:] = b"\x20\x40\x60\xff" * (fb.size // 4)      # unser Bild
fb.flip()
check("nach dem Vollbild stimmen Schirm und Puffer",
      bytes(fb.mm[:]) == bytes(fb.buf), "Ausgangslage")
check("und der Waechter hat Sollwerte",
      all(s is not None for s in fb._waechter_soll))

# MiSTer richtet den Bildspeicher neu ein: alles weg.
fb.mm[:] = b"\x00" * fb.size
check("der Waechter erkennt es", fb._waechter_pruefen() is True)

NOW[0] += 1.0
fb.flip_rows(162, 120)            # ein gewoehnlicher Scroll-Teilflip
check("und der naechste Teil-Flip holt das GANZE Bild zurueck",
      bytes(fb.mm[:]) == bytes(fb.buf),
      "%d abweichende Bytes"
      % sum(1 for a, b in zip(bytes(fb.mm[:]), bytes(fb.buf)) if a != b))
check("er zaehlt die Reparatur", fb._waechter_repariert == 1,
      fb._waechter_repariert)
check("danach ist wieder Ruhe", fb._waechter_pruefen() is False)

# ---------------------------------------------------------------------------
print()
print("Test 3: KEIN FEHLALARM durch unser eigenes Zeichnen")
# ---------------------------------------------------------------------------
# Das ist der Kern. Mehrere Zeichenpfade malen erst alles in den Puffer
# und flippen dann Band fuer Band - der Puffer laeuft dem Schirm also
# voellig legitim voraus. Wer gegen den PUFFER vergleicht, meldet genau
# das als Fremdschreiben und wuerde bei jedem Seitenaufbau eine
# Vollbildkopie anwerfen. Verglichen wird deshalb gegen das ZULETZT
# GESCHRIEBENE.
fb = neu()
fb.buf[:] = b"\x20\x40\x60\xff" * (fb.size // 4)
fb.flip()
vorher = fb._waechter_repariert

# Der Puffer aendert sich komplett - geflippt wird aber nur ein Band.
fb.buf[:] = b"\x11\x22\x33\xff" * (fb.size // 4)
NOW[0] += 1.0
fb.flip_rows(300, 60)
check("der Waechter schlaegt NICHT an, obwohl Puffer und Schirm weit "
      "auseinanderliegen",
      fb._waechter_repariert == vorher,
      "%d Reparaturen - er vergleicht gegen den Puffer statt gegen das "
      "Geschriebene" % (fb._waechter_repariert - vorher))
check("und der Teil-Flip hat nur sein Band geschrieben",
      bytes(fb.mm[300 * fb.stride:360 * fb.stride])
      == bytes(fb.buf[300 * fb.stride:360 * fb.stride])
      and bytes(fb.mm[:fb.stride]) != bytes(fb.buf[:fb.stride]),
      "sonst waere die Ersparnis von Build 196 dahin")

# Und ueber viele Teil-Flips hinweg ebenfalls nicht.
for i in range(20):
    NOW[0] += 1.0
    fb.buf[:] = bytes([i % 256, 0x22, 0x33, 0xff]) * (fb.size // 4)
    fb.flip_rows(100 + i, 40)
check("auch nach zwanzig Teil-Flips keine einzige Reparatur",
      fb._waechter_repariert == vorher,
      "%d" % (fb._waechter_repariert - vorher))

# ---------------------------------------------------------------------------
print()
print("Test 4: Dauerfeuer wird gedrosselt")
# ---------------------------------------------------------------------------
# Wischt MiSTer dauerhaft, wuerde jeder Teil-Flip zu einer
# Vollbildkopie - aus 1 ms wuerden 13, und das Scrollen waere langsamer
# als vor Build 196. Dann lieber das Band schreiben und die naechste
# Gelegenheit abwarten.
fb = neu()
fb.buf[:] = b"\x20\x40\x60\xff" * (fb.size // 4)
fb.flip()
n = 0
for _ in range(10):
    fb.mm[:] = b"\x00" * fb.size          # jedes Mal neu gewischt
    NOW[0] += 0.01                        # 10 ms - schneller als der Takt
    fb.flip_rows(162, 120)
    n += 1
check("zehn Wischer in 100 ms ergeben nicht zehn Vollbildkopien",
      fb._waechter_repariert <= 2, "%d Reparaturen" % fb._waechter_repariert)
NOW[0] += fb.WAECHTER_TAKT + 0.01
fb.mm[:] = b"\x00" * fb.size
fb.flip_rows(162, 120)
check("nach dem Takt wird wieder repariert", fb._waechter_repariert >= 2,
      fb._waechter_repariert)

# ---------------------------------------------------------------------------
print()
print("Test 5: abschaltbar, und ohne ihn bleibt alles wie vorher")
# ---------------------------------------------------------------------------
os.environ["DRAGEND_BILDWAECHTER"] = "0"
try:
    fb = neu()
    check("mit DRAGEND_BILDWAECHTER=0 ist er aus", not fb._waechter_an)
    fb.buf[:] = b"\x20\x40\x60\xff" * (fb.size // 4)
    fb.flip()
    fb.mm[:] = b"\x00" * fb.size
    NOW[0] += 1.0
    fb.flip_rows(162, 120)
    geschrieben = bytes(fb.mm[162 * fb.stride:282 * fb.stride])
    check("dann wird nur das Band geschrieben, wie vor Build 198",
          geschrieben == bytes(fb.buf[162 * fb.stride:282 * fb.stride])
          and bytes(fb.mm[:fb.stride]) == b"\x00" * fb.stride)
finally:
    del os.environ["DRAGEND_BILDWAECHTER"]

# ---------------------------------------------------------------------------
print()
print("Test 6: auf CRT genauso")
# ---------------------------------------------------------------------------
# 320x240: die beiden oberen Proben liegen bei Zeile 16 und 40, das
# passt dort noch - aber die Grenzen muessen stimmen, sonst zeigt eine
# Probe hinter das Bildende.
fb = neu(hoehe=240, breite=320)
check("alle Proben liegen im Bild",
      all(0 <= o <= fb.size - 4 for o in fb._waechter_offsets),
      [o // fb.stride for o in fb._waechter_offsets])
fb.buf[:] = b"\x20\x40\x60\xff" * (fb.size // 4)
fb.flip()
fb.mm[:] = b"\x00" * fb.size
NOW[0] += 1.0
fb.flip_rows(100, 30)
check("und ein Wischen wird auch dort zurueckgeholt",
      bytes(fb.mm[:]) == bytes(fb.buf))
H.set_screen(1920, 1080)

# ---------------------------------------------------------------------------
print()
print("Test 7: ein sehr kleines Bild bringt ihn nicht aus dem Tritt")
# ---------------------------------------------------------------------------
# Die Grenze ist "<= size - 4", nicht "< size - 4": ein Bildpunkt ist
# vier Byte lang, der letzte beginnt also genau bei size - 4. Beim
# ersten Anlauf stand hier "<" und der Test meldete einen Fehler, den
# es nicht gab - bei 16x8 liegt die letzte Probe exakt dort.
fb = neu(hoehe=8, breite=16)
check("Proben bleiben im Bild",
      all(0 <= o <= fb.size - 4 for o in fb._waechter_offsets),
      [(o // fb.stride, (o % fb.stride) // 4)
       for o in fb._waechter_offsets])
fb.buf[:] = b"\x20\x40\x60\xff" * (fb.size // 4)
fb.flip()
fb.mm[:] = b"\x00" * fb.size
NOW[0] += 1.0
fb.flip_rows(2, 2)
check("und das Bild kommt zurueck", bytes(fb.mm[:]) == bytes(fb.buf))
H.set_screen(1920, 1080)

# ---------------------------------------------------------------------------
print()
print("Test 8: der Fund steht im Quelltext")
# ---------------------------------------------------------------------------
quelle = io.open(os.path.join(_REPO, "frontend", "fe", "framebuffer.py"),
                 encoding="utf-8").read()
check("die Messung ist festgehalten", "15 von 15" in quelle)
check("und dass der Fehler AELTER ist als Build 196",
      "AELTER als Build 196" in quelle,
      "wer das in einem Jahr liest, soll nicht 196 verdaechtigen")
check("und warum gegen das Geschriebene verglichen wird, nicht gegen "
      "den Puffer",
      "ZULETZT GESCHRIEBENE" in quelle)

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
