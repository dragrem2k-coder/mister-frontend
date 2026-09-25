#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Die obersten Bildzeilen werden regelmaessig neu hingeschrieben.

DIE MESSUNG, DIE DAZU GEFUEHRT HAT (Build 190)

Der Nutzer meldete einen Login-Gruss, der beim Scrollen aufblitzt.
Drei Runden Verdacht gingen an die falsche Stelle - erst gegen Build
187, dann gegen unsere Konsolen-Mechanik. Sein Log entlastete beide:
genau EIN F9 zur Absicherung, nach vier Sekunden beendet, keine
einzige Fremdausgabe-Meldung der Dauerwache. Mit abgeschaltetem
Schalter kam der Prompt trotzdem.

Der Rueckleser hat es dann gesagt:

    RUECKLESER: nach 104.6 s steht in 2 von 7 Proben-Zeilen fremder
    Inhalt (Zeilen 0,32) - 10 Treffer bei 21 Bildern

Zehn Treffer bei einundzwanzig Bildern, und ausschliesslich in den
Zeilen 0 und 32. Die uebrigen fuenf Proben blieben sauber. Sichtbar
wurde das erst mit Build 189 - vorher lagen die Proben bei 0, 135,
270 ... und haetten den Bereich nie getroffen.

WAS DIESER TEST ABSICHERT

  - dass die Auffrischung UNABHAENGIG vom Mechanik-Schalter laeuft
    (die Ursache liegt nicht bei uns, also darf die Abhilfe nicht an
    unserem Schalter haengen),
  - dass sie den Bereich abdeckt, in dem die Treffer lagen,
  - dass sie gedrosselt ist und nicht bei jedem Schleifendurchlauf
    feuert,
  - dass sie das Vsync-Warten ueberspringt (schmales Band, Build 93),
  - und dass ein Fehler dabei den Betrieb nicht stoert.

Ausfuehren:
    python3 tools/test_kopfzeilen.py
"""
import io
import os
import sys

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
sys.path.insert(0, _HIER)

import _harness as H                                     # noqa: E402

fm = H.fm
F = fm.Frontend
NOW = H.NOW

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


class FB(object):
    def __init__(self, hoehe=1080, kracht=False):
        self.height = hoehe
        self.aufrufe = []
        self.kracht = kracht

    def flip_rows(self, y, h, skip_vsync=False):
        if self.kracht:
            raise RuntimeError("Bildspeicher weg")
        self.aufrufe.append((y, h, skip_vsync))


class Lage(object):
    KOPFZEILEN = F.KOPFZEILEN
    KOPFZEILEN_TAKT = F.KOPFZEILEN_TAKT
    _kopfzeilen_auffrischen = F._kopfzeilen_auffrischen

    def __init__(self, **kw):
        self.fb = FB(**kw)


# ---------------------------------------------------------------------------
print("Test 1: sie deckt den gemessenen Bereich ab")
# ---------------------------------------------------------------------------
L = Lage()
L._kopfzeilen_auffrischen()
check("es wird geschrieben", len(L.fb.aufrufe) == 1, L.fb.aufrufe)
y, h, skip = L.fb.aufrufe[0]
check("ab Zeile 0", y == 0, y)
check("Zeile 32 liegt drin (dort waren die Treffer)", y <= 32 < y + h,
      "0 bis %d" % (y + h))
check("Zeile 47 auch (dort sass der Cursor)", y <= 47 < y + h)
check("aber es bleibt ein schmales Band", h <= 96,
      "%d Zeilen - mehr waere eine halbe Vollbildkopie" % h)
check("ohne Vsync-Warten", skip is True,
      "viermal je Sekunde 16 ms warten waere Stillstand")

# ---------------------------------------------------------------------------
print()
print("Test 2: gedrosselt, nicht bei jedem Durchlauf")
# ---------------------------------------------------------------------------
L = Lage()
for _ in range(200):
    L._kopfzeilen_auffrischen()
check("200 Durchlaeufe ohne Zeitfortschritt -> ein Schreibvorgang",
      len(L.fb.aufrufe) == 1, "%d" % len(L.fb.aufrufe))
NOW[0] += F.KOPFZEILEN_TAKT + 0.01
L._kopfzeilen_auffrischen()
check("nach dem Takt wieder einer", len(L.fb.aufrufe) == 2,
      "%d" % len(L.fb.aufrufe))
check("der Takt ist nicht zu langsam", F.KOPFZEILEN_TAKT <= 0.5,
      "%.2f s - laenger und man saehe den Prompt stehen"
      % F.KOPFZEILEN_TAKT)
check("und nicht zu schnell", F.KOPFZEILEN_TAKT >= 0.1,
      "%.2f s" % F.KOPFZEILEN_TAKT)

# ---------------------------------------------------------------------------
print()
print("Test 3: ein kleiner Schirm wird nicht ueberschrieben")
# ---------------------------------------------------------------------------
# Auf CRT ist der ganze Schirm 240 Zeilen hoch. Ein Band von 64 passt
# dort, aber die Grenze muss trotzdem stimmen - sonst schreibt jemand
# ueber das Bild hinaus.
L = Lage(hoehe=32)
L._kopfzeilen_auffrischen()
y, h, _ = L.fb.aufrufe[0]
check("nie ueber den unteren Rand hinaus", y + h <= 32, "%d" % (y + h))

# ---------------------------------------------------------------------------
print()
print("Test 4: ein Fehler stoert den Betrieb nicht")
# ---------------------------------------------------------------------------
L = Lage(kracht=True)
try:
    L._kopfzeilen_auffrischen()
    ok = True
except Exception as e:                                   # noqa: BLE001
    ok = False
    print("    ", type(e).__name__, e)
check("eine Ausnahme wird geschluckt", ok,
      "das Auffrischen ist Beiwerk, kein Grund zum Absturz")

# ---------------------------------------------------------------------------
print()
print("Test 5: UNABHAENGIG vom Mechanik-Schalter")
# ---------------------------------------------------------------------------
# Das ist der Kern. Die Ursache liegt nachweislich nicht bei uns - mit
# abgeschalteter Mechanik kam der Prompt genauso. Haengte die Abhilfe
# am selben Schalter, waere sie fuer genau den Fall nutzlos, der sie
# noetig gemacht hat.
quelle = io.open(os.path.join(_REPO, "frontend", "frontend.py"),
                 encoding="utf-8").read()
# Ueber die EINRUECKUNG geprueft, nicht ueber Textsuche: der Aufruf
# muss ein Geschwister des "if self.konsole_mechanik():" sein, kein
# Kind davon. Beim ersten Anlauf hat dieser Test danebengegriffen und
# einen Fehlalarm erzeugt - er suchte nach Zeichenketten statt nach
# der Struktur.
def _einzug(zeile):
    return len(zeile) - len(zeile.lstrip(" "))


_zeilen = quelle.splitlines()
_ruf_i = [i for i, z in enumerate(_zeilen)
          if z.strip() == "self._kopfzeilen_auffrischen()"]
check("der Aufruf steht genau einmal in der Hauptschleife",
      len(_ruf_i) == 1, "%d Fundstellen" % len(_ruf_i))
# Das NAECHSTGELEGENE if davor, nicht irgendeines: konsole_mechanik()
# wird an mehreren Stellen abgefragt, unter anderem in
# play_boot_animation() mit anderer Einrueckung. Beim zweiten Anlauf
# hat dieser Test genau daran danebengegriffen.
if _ruf_i:
    _i = _ruf_i[0]
    _vorher = [j for j in range(_i)
               if _zeilen[j].strip() == "if self.konsole_mechanik():"]
    _naechstes = _vorher[-1] if _vorher else None
    check("und NICHT im Mechanik-Zweig",
          _naechstes is None
          or _einzug(_zeilen[_i]) <= _einzug(_zeilen[_naechstes]),
          "Einzug %d gegen %d in Zeile %d"
          % (_einzug(_zeilen[_i]),
             _einzug(_zeilen[_naechstes]) if _naechstes else -1,
             (_naechstes or 0) + 1))
check("und die Begruendung steht dabei",
      "UNABHAENGIG VOM SCHALTER" in quelle)
check("die Messung, die dazu gefuehrt hat, ist festgehalten",
      "10 Treffer bei 21 Bildern" in quelle
      and "Zeilen 0,32" in quelle,
      "wer das in einem Jahr liest, soll den Beleg sehen")

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
