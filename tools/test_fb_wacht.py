#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Die Wache am Bildspeicher (frontend/fb_wacht.py).

WORUM ES GEHT

Das Werkzeug soll eine einzige Frage beantworten: schreibt jemand in
unseren Bildspeicher hinein, oder wird die Anzeige-Ebene kurz
weggeschaltet? Es laeuft auf dem Geraet, nicht hier - geprueft wird
deshalb das, was sich ohne Bildspeicher pruefen laesst:

  - dass die Rohwerte des Treibers richtig ausgepackt werden
    (ein Versatz um vier Bytes im struct, und die Antwort ist Unsinn,
    sieht aber plausibel aus - die schlimmste Sorte Fehler),
  - dass die Rechnung 'wieviele Bildseiten passen hinein' stimmt,
  - dass das Muster wirklich an jeder Position eindeutig ist,
  - und dass die Wache sich weigert, solange das Frontend laeuft.

Der letzte Punkt ist kein Formalismus: schrieben beide gleichzeitig,
waere das Ergebnis Matsch, und zwar Matsch, der wie ein Befund
aussieht.

Ausfuehren:
    python3 tools/test_fb_wacht.py
"""
import importlib.util
import io
import os
import struct
import sys

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
_QUELLE = os.path.join(_REPO, "frontend", "fb_wacht.py")

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


spec = importlib.util.spec_from_file_location("fb_wacht", _QUELLE)
W = importlib.util.module_from_spec(spec)
spec.loader.exec_module(W)
W.sag = lambda *a, **k: None          # das Werkzeug redet sonst viel


# ---------------------------------------------------------------------------
print("Test 1: die Rohwerte des Treibers werden richtig ausgepackt")
# ---------------------------------------------------------------------------
def fb_var(xres, yres, xv, yv, xo, yo, bpp):
    roh = bytearray(160)
    struct.pack_into("<8I", roh, 0, xres, yres, xv, yv, xo, yo, bpp, 0)
    return roh


def fb_fix(kennung, smem_start, smem_len, zeile):
    roh = bytearray(160)
    roh[0:len(kennung)] = kennung
    struct.pack_into("<II", roh, 16, smem_start, smem_len)
    struct.pack_into("<I", roh, 44, zeile)
    return roh


class Treiber(object):
    """Ein /dev/fb0, das es nicht gibt - antwortet nur auf die beiden
    ioctls, um die es hier geht."""

    def __init__(self, var, fix):
        self.var, self.fix = var, fix
        self.abfragen = 0

    def ioctl(self, fd, anfrage, puffer, mutieren=False):
        if anfrage == W.FBIOGET_VSCREENINFO:
            self.abfragen += 1
            puffer[:len(self.var)] = self.var
        elif anfrage == W.FBIOGET_FSCREENINFO:
            puffer[:len(self.fix)] = self.fix
        else:
            raise OSError("unbekannter ioctl")
        return 0


t = Treiber(fb_var(1920, 1080, 1920, 1080, 0, 0, 32),
            fb_fix(b"MiSTer_fb", 0x3F000000, 1920 * 1080 * 4, 1920 * 4))
W.fcntl.ioctl = t.ioctl

v = W.vscreeninfo(0)
check("sichtbare Groesse", (v["xres"], v["yres"]) == (1920, 1080), v)
check("virtuelle Groesse",
      (v["xres_virtual"], v["yres_virtual"]) == (1920, 1080))
check("Versatz und Farbtiefe",
      (v["xoffset"], v["yoffset"], v["bpp"]) == (0, 0, 32))

f = W.fscreeninfo(0)
check("Name des Treibers", f["id"] == "MiSTer_fb", repr(f["id"]))
check("physische Adresse", f["smem_start"] == 0x3F000000,
      hex(f["smem_start"]))
check("gemeldete Groesse", f["smem_len"] == 1920 * 1080 * 4)
check("Zeilenlaenge an der 32-Bit-Stelle",
      f["line_length@44"] == 1920 * 4)
check("die gewaehlte Zeilenlaenge passt zur Breite",
      W.zeilenlaenge(v, f) == 1920 * 4, W.zeilenlaenge(v, f))

# Und der Fall, in dem die 32-Bit-Stelle Unsinn enthaelt: dann muss
# auf die Breite zurueckgefallen werden, nicht irgendein Wert genommen.
f2 = dict(f, **{"line_length@44": 3, "line_length@52": 0})
check("unbrauchbare Angaben -> Breite mal vier",
      W.zeilenlaenge(v, f2) == 1920 * 4, W.zeilenlaenge(v, f2))

# ---------------------------------------------------------------------------
print()
print("Test 2: passt mehr als eine Bildseite hinein?")
# ---------------------------------------------------------------------------
# Das ist die Frage, wegen der das Werkzeug ueberhaupt gebaut wurde.
def urteil(smem_len, yres_v=1080):
    ausgabe = []
    W.sag = lambda s="": ausgabe.append(s)
    tt = Treiber(fb_var(1920, 1080, 1920, yres_v, 0, 0, 32),
                 fb_fix(b"MiSTer_fb", 0x3F000000, smem_len, 1920 * 4))
    W.fcntl.ioctl = tt.ioctl
    W.abschnitt_nachsehen(0)
    W.sag = lambda *a, **k: None
    return "\n".join(ausgabe)


eine = 1920 * 1080 * 4
check("genau eine Seite -> 'nur eine Seite'",
      "nur eine Seite" in urteil(eine))
check("zwei Seiten -> als Treffer benannt",
      "MEHR ALS EINE SEITE" in urteil(2 * eine))
check("anderthalb Seiten -> weder noch, und gesagt wird es auch",
      "keine zweite ganze" in urteil(eine * 3 // 2))
check("yres_virtual groesser -> der Treiber raeumt es selbst ein",
      "raeumt also selbst ein" in urteil(2 * eine, yres_v=2160))
check("yres_virtual gleich -> 'kennt nur ein Bild'",
      "kennt nur ein Bild" in urteil(eine))
check("ohne gemeldete Groesse keine erfundene Aussage",
      "keine Aussage moeglich" in urteil(0))

# ---------------------------------------------------------------------------
print()
print("Test 3: das Muster ist an jeder Position eindeutig")
# ---------------------------------------------------------------------------
# Sonst koennte ein fremder Inhalt zufaellig durchgehen.
m = W.muster(100000)
check("richtige Laenge", len(m) == 100000)
check("bei jedem Aufruf dasselbe", m == W.muster(100000))
haeufigste = max(m.count(bytes([b])) for b in set(m))
check("kein Bytewert beherrscht das Muster",
      haeufigste < len(m) // 200, "haeufigster Wert %d mal" % haeufigste)
# Die eigentliche Probe: ein um EIN Byte verschobenes Muster darf
# nirgends laenger uebereinstimmen.
verschoben = W.muster(100000, versatz=1)
gleich = sum(1 for a, b in zip(m, verschoben) if a == b)
check("um ein Byte verschoben stimmt fast nichts ueberein",
      gleich < 100000 // 100, "%d von 100000" % gleich)

# ---------------------------------------------------------------------------
print()
print("Test 4: die Wache weigert sich, wenn das Frontend laeuft")
# ---------------------------------------------------------------------------
ausgabe = []
W.sag = lambda s="": ausgabe.append(s)
W.frontend_laeuft = lambda: True
eingeblendet = []


def _nicht_einblenden(*a):
    eingeblendet.append(a)
    raise AssertionError("es wurde trotzdem eingeblendet")


W.einblenden = _nicht_einblenden
ok = W.abschnitt_wache(0, v, f, 1920 * 4, eine, 5)
W.sag = lambda *a, **k: None
check("sie bricht ab", ok is False)
check("und sagt auch, warum",
      any("Frontend laeuft noch" in z for z in ausgabe))
check("ohne den Bildspeicher ueberhaupt einzublenden",
      not eingeblendet)

# ---------------------------------------------------------------------------
print()
print("Test 5: der Aufruf ist gutmuetig")
# ---------------------------------------------------------------------------
quelle = io.open(_QUELLE, encoding="utf-8").read()
check("ohne Argument wird NICHTS geschrieben",
      "dauer = 0" in quelle and "if dauer:" in quelle,
      "das blosse Nachsehen muss gefahrlos sein")
check("die Dauer ist nach oben begrenzt", "min(int(argumente[1]), 300)"
      in quelle)
check("am Ende wird das Bild geleert",
      quelle.count('mm[0:eine_seite] = b"\\x00" * eine_seite') == 1,
      "sonst bleibt das Pruefmuster stehen")
check("auf der Karte wird nichts angelegt",
      "/media/fat" not in quelle,
      "der Bericht gehoert nach /tmp")
check("der Bericht landet in /tmp", 'BERICHT = "/tmp/' in quelle)

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
