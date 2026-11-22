# -*- coding: utf-8 -*-
"""Die Weihnachts-Deko (Build 342).

NUTZERWUNSCH: "fallender Schnee, Automatik und Kleinigkeiten" - nach
zwei Runden Beispielbildern: "das ist gut bitte so machen, wer es nicht
will sollte es in system mit schalter an und ausschalten koennen".

WAS DAZUGEHOERT

  - fallender Schnee auf der Hauptseite und in den Listen, solange
    niemand eine Taste drueckt (siehe Schnee unten),
  - eine warmweisse Lichterkette oben ueber dem Titel,
  - eine Weihnachtsmuetze, die oben links am "M" von "MiSTer" haengt,
  - aus Zufalls-Zock wird Wichtel-Zock (UMLEITUNG in
    fe/translations.py),
  - von selbst vom 1. Dezember bis zum 6. Januar; unter System ->
    Anzeige & Sound "automatisch / immer an / aus"
    (load_weihnachten() in fe/settings.py).

DAS RECHNEN OHNE PILLOW UND OHNE PUNKT-FUER-PUNKT-SCHLEIFE

Muetze und Birnen haben weiche Kanten und einen Lichthof, muessen also
mit Deckkraft auf das Bild gelegt werden. Eine Python-Schleife ueber
jeden Bildpunkt kostete auf dem Geraet fuer die Muetze allein ein
Zehntel einer Sekunde. Deshalb geht es hier ueber grosse Ganzzahlen:

    Ergebnis = Summe ueber die 16 Deckkraftstufen q von
               (Untergrund * (15 - q) / 15)  nur an den Punkten der Stufe q
             + Bild * q / 15                 (fertig vorgerechnet)

"Untergrund * (15-q)/15" ist EIN bytes.translate() ueber den ganzen
Ausschnitt, "nur an den Punkten der Stufe q" EIN bitweises Und mit
einer vorbereiteten Maske, und weil jede Byte-Summe hoechstens 255
ergibt, kann die Addition nie in das Nachbarbyte ueberlaufen. Alles
davon laeuft in C. Sechzehn Stufen sind auf dem Schirm von echten 256
nicht zu unterscheiden.

DAS ZWEITE PROBLEM: DASSELBE ZWEIMAL MALEN

Der Titel wird beim schnellen Teil-Neuaufbau der Hauptseite jedes Mal
neu geschrieben - aber nur in seinen eigenen Zeichenzellen. Wer die
Muetze danach einfach noch einmal darueberlegt, legt sie an den Stellen
ausserhalb der Zellen ZWEIMAL uebereinander, und die weichen Raender
werden mit jedem Schritt dunkler. malen() merkt sich deshalb, was es
zuletzt geschrieben hat und worauf: jeder Bildpunkt, der seitdem
unveraendert ist, bekommt seinen alten Untergrund zurueck, jeder
veraenderte gilt als neuer Untergrund. Auch das sind ein paar Operationen
auf grossen Ganzzahlen, keine Schleife.
"""
import base64
import math
import os
import random
import time
import zlib

import fe.translations as TR
from fe.settings import load_weihnachten

# Fuer Tests und den Bench: None = nach Einstellung und Datum,
# True/False = erzwungen. Die Tests laufen nicht im Dezember anders als
# im November, und der Bench misst im Dezember dasselbe wie im Juni.
ERZWUNGEN = None


def im_zeitraum(lt=None):
    """1. Dezember bis einschliesslich 6. Januar (Heilige Drei Koenige)."""
    if lt is None:
        lt = time.localtime()
    return lt.tm_mon == 12 or (lt.tm_mon == 1 and lt.tm_mday <= 6)


def aktiv(lt=None):
    if ERZWUNGEN is not None:
        return bool(ERZWUNGEN)
    # Fuer Testlaeufe von aussen (die Suite, ein Pruefstand):
    # DRAGEND_WEIHNACHTEN=aus/an geht vor Datei und Datum.
    umgebung = os.environ.get("DRAGEND_WEIHNACHTEN", "").strip().lower()
    if umgebung in ("an", "aus"):
        return umgebung == "an"
    stufe = load_weihnachten()
    if stufe == "an":
        return True
    if stufe == "aus":
        return False
    return im_zeitraum(lt)


def umleitung_setzen(an):
    """Wichtel-Zock an oder aus. Aendert das Woerterbuch an Ort und
    Stelle - t() haelt eine Referenz darauf."""
    TR.UMLEITUNG.clear()
    if an:
        TR.UMLEITUNG.update(TR.SAISON_FASSUNGEN)


# ======================================================================
# Bilder mit Deckkraft
# ======================================================================
STUFEN = 15
_INV = [bytes((v * (STUFEN - q)) // STUFEN for v in range(256))
        for q in range(STUFEN + 1)]
_MAL = [bytes((v * q) // STUFEN for v in range(256))
        for q in range(STUFEN + 1)]
_GLEICH = [bytes(255 if v == q else 0 for v in range(256))
           for q in range(STUFEN + 1)]
_STUFE = bytes((a * STUFEN + 127) // 255 for a in range(256))
_NICHT_NULL = bytes([0] + [1] * 255)


def _int(b):
    return int.from_bytes(b, "little")


class Bild(object):
    """Ein Bild mit Deckkraft, vorbereitet fuer _mischen()."""

    def __init__(self, w, h, ax, ay, bgra):
        self.w, self.h, self.ax, self.ay = w, h, ax, ay
        self.roh = bytes(bgra)                 # gerade Deckkraft
        n = w * h
        stufe = self.roh[3::4].translate(_STUFE)
        ebene = bytearray(4 * n)               # Stufe je Farbbyte,
        ebene[0::4] = stufe                    # 0 im vierten Byte
        ebene[1::4] = stufe
        ebene[2::4] = stufe
        ebene = bytes(ebene)
        self.m0 = _int(ebene.translate(_GLEICH[0]))
        self.stufen = []
        farbe = 0
        for q in range(1, STUFEN + 1):
            if q not in stufe:
                continue
            m = _int(ebene.translate(_GLEICH[q]))
            farbe += _int(self.roh.translate(_MAL[q])) & m
            if q < STUFEN:
                self.stufen.append((q, m))
        self.farbe = farbe
        self.laenge = 4 * n
        self.alle = (1 << (8 * self.laenge)) - 1
        self.tief = _int(b"\x01\x00\x00\x00" * n)
        self._ausschnitte = {}

    def mischen(self, unter):
        """Das Bild ueber den Untergrund `unter` (bytes, Zeilen
        aneinander) legen - siehe Modulkommentar."""
        acc = _int(unter) & self.m0
        for q, m in self.stufen:
            acc += _int(unter.translate(_INV[q])) & m
        acc += self.farbe
        return acc.to_bytes(self.laenge, "little")

    def basis(self, jetzt, out_alt, basis_alt):
        """Der Untergrund, auf den gemalt werden muss: unveraenderte
        Bildpunkte bekommen den alten zurueck, veraenderte gelten als
        neu (siehe Modulkommentar, "dasselbe zweimal malen")."""
        n = self.laenge
        diff = (_int(jetzt) ^ _int(out_alt)).to_bytes(n, "little")
        f = _int(diff.translate(_NICHT_NULL))
        f = (f | (f >> 8) | (f >> 16) | (f >> 24)) & self.tief
        pm = f * 0xFFFFFFFF
        neu = (_int(jetzt) & pm) | (_int(basis_alt) & (self.alle ^ pm))
        return neu.to_bytes(n, "little")

    def ausschnitt(self, x0, y0, x1, y1):
        """Ein Teil des Bildes - fuer den Rand des Schirms."""
        k = (x0, y0, x1, y1)
        b = self._ausschnitte.get(k)
        if b is None:
            zeile = self.w * 4
            teile = [self.roh[y * zeile + x0 * 4:y * zeile + x1 * 4]
                     for y in range(y0, y1)]
            b = Bild(x1 - x0, y1 - y0, self.ax - x0, self.ay - y0,
                     b"".join(teile))
            self._ausschnitte[k] = b
        return b


_BILDER = {}


def bild(name):
    """Ein Bild aus fe/weihnacht_bilder.py, beim ersten Gebrauch geladen
    und vorbereitet. None, wenn es das Bild nicht gibt."""
    b = _BILDER.get(name)
    if b is None and name not in _BILDER:
        try:
            from fe.weihnacht_bilder import BILDER
            w, h, ax, ay, daten = BILDER[name]
            b = Bild(w, h, ax, ay, zlib.decompress(base64.b64decode(daten)))
        except Exception:                                # noqa: BLE001
            b = None
        _BILDER[name] = b
    return b


# Je Stelle auf dem Schirm: was zuletzt dort geschrieben wurde, worauf,
# und ein kleiner Zwischenspeicher "Untergrund -> Ergebnis".
_STAND = {}
_STAND_MAX_CACHE = 6


def malen(fb, b, x, y):
    """Bild `b` mit seiner linken oberen Ecke an (x, y) ins Puffer-Bild
    legen; am Schirmrand abgeschnitten. Kein Flip - das macht der
    Zeichenpfad, der es aufruft. Liefert das gezeichnete Rechteck oder
    None."""
    if b is None:
        return None
    W, H = fb.width, fb.height
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(W, x + b.w), min(H, y + b.h)
    if x1 <= x0 or y1 <= y0:
        return None
    if (x0, y0, x1, y1) != (x, y, x + b.w, y + b.h):
        b = b.ausschnitt(x0 - x, y0 - y, x1 - x, y1 - y)
    buf, zl = fb.buf, fb.stride
    n = b.w * 4
    off = y0 * zl + x0 * 4
    ende = off + b.h * zl
    jetzt = b"".join([buf[o:o + n] for o in range(off, ende, zl)])
    schl = (id(b), x0, y0, W, H)
    st = _STAND.get(schl)
    if st is not None and jetzt == st[0]:
        return (x0, y0, b.w, b.h)          # liegt schon genau so da
    cache = st[2] if st is not None else {}
    treffer = cache.get(jetzt)
    if treffer is None:
        basis = b.basis(jetzt, st[0], st[1]) if st is not None else jetzt
        treffer = cache.get(basis)
        if treffer is None:
            treffer = (b.mischen(basis), basis)
            cache[basis] = treffer
        cache[jetzt] = treffer
        while len(cache) > _STAND_MAX_CACHE:
            cache.pop(next(iter(cache)))
    out, basis = treffer
    mv = memoryview(out)
    i = 0
    for o in range(off, ende, zl):
        buf[o:o + n] = mv[i:i + n]
        i += n
    _STAND[schl] = (out, basis, cache)
    return (x0, y0, b.w, b.h)


# ======================================================================
# Muetze und Lichterkette
# ======================================================================
def titel_hoehe(s):
    """Hoehe der hellen Schrift von "MiSTer" in Groesse 3*s -
    nachgemessen: 20 Punkte bei s=1, 41 bei s=2, 62 bei s=3."""
    return (62 * s + 1) // 3


def muetze_lage(ox, oy, s):
    """(Bild, x, y) der Muetze - wie im freigegebenen Beispiel: der
    Pelzrand sitzt auf der Oberkante des M, ein gutes Stueck nach links
    ueberstehend, die Spitze kippt nach rechts. Auf der Roehre (s=1)
    etwas tiefer und kleiner, sonst rutscht sie aus dem Bild."""
    b = bild("muetze_%d" % max(1, min(4, s)))
    if b is None:
        return None
    hoch = titel_hoehe(s)
    tief = 0.22 if s <= 1 else 0.30
    x = ox + int(hoch * 1.05 * 0.55 - b.w * 0.5)
    y = oy + int(hoch * tief - b.h * 0.9)
    return b, x, y


def kette_plan(W, band, s):
    """Die Lichterkette im Streifen ueber dem Titel (Hoehe `band`, das
    ist der obere Bildrand oy).

    Liefert (Drahtstuecke, Birnen) oder None, wenn der Streifen zu
    schmal ist - wer den Bildrand oben auf 0 gestellt hat, bekommt die
    Muetze, aber keine Kette, die in den Titel haengt.

    Drahtstuecke: (x, y, breite, dicke) - waagerechte Stuecke gleicher
    Hoehe, zusammengefasst, damit es ein paar hundert Schreibvorgaenge
    werden und nicht einer je Bildspalte.
    Birnen: (Bildname, Ankerpunkt x, Ankerpunkt y)."""
    if band < 8 or W < 64:
        return None
    r = max(1, min(8, int(round(band * 0.115))))
    oben = max(1, int(round(band * 0.15)))
    dicke = max(1, int(round(r / 2.0)))
    # Die Birne samt Lichthof (4 r unter dem Aufhaengepunkt, der selbst
    # in der Mitte des Drahts sitzt) muss ueber dem Titel enden - siehe
    # birne_masse() in PC-Tools/weihnacht_bilder.py. 0,924 ist der
    # Sinus an der tiefsten Birne (3/8 des Bogens).
    durchhang = (band - oben - 4 * r - 1 - dicke // 2) / 0.924
    if durchhang < 2:
        return None
    boegen = max(2, int(round(W / (6.0 * band))))
    bogen = W / float(boegen)
    stuecke = []
    start, alt = 0, None
    for x in range(W + 1):
        if x < W:
            t = (x % bogen) / bogen
            y = oben + int(durchhang * math.sin(math.pi * t))
        else:
            y = None
        if y != alt:
            if alt is not None:
                stuecke.append((start, alt, x - start, dicke))
            start, alt = x, y
    birnen = []
    for k in range(boegen):
        for i, t in enumerate((0.125, 0.375, 0.625, 0.875)):
            bx = int(k * bogen + t * bogen)
            by = oben + int(durchhang * math.sin(math.pi * t)) + dicke // 2
            # leichtes Funkeln: zwei Helligkeiten, fest verteilt
            name = "birne_%d%s" % (r, "a" if (k * 4 + i) % 3 else "b")
            birnen.append((name, bx, by))
    return stuecke, birnen


DRAHT = (40, 37, 30)
_PLAENE = {}


def kopf_deko(fb, ox, oy, s, kette=True):
    """Lichterkette (nur mit kette=True) und Muetze an den Titel der
    Hauptseite. Gerufen direkt nach fb.text(..., "MiSTer", ...). Kein
    Flip. Tut nichts, wenn die Deko nicht an ist."""
    if not aktiv():
        return
    W = fb.width
    if kette:
        k = (W, oy, s)
        plan = _PLAENE.get(k)
        if plan is None and k not in _PLAENE:
            plan = _PLAENE[k] = kette_plan(W, oy, s)
        if plan is not None:
            stuecke, birnen = plan
            buf, zl = fb.buf, fb.stride
            farbe = fb.px(DRAHT)
            for (x, y, w, d) in stuecke:
                bytes_ = farbe * w
                off = y * zl + x * 4
                for _ in range(d):
                    buf[off:off + 4 * w] = bytes_
                    off += zl
            for name, bx, by in birnen:
                b = bild(name)
                if b is not None:
                    malen(fb, b, bx - b.ax, by - b.ay)
    lage = muetze_lage(ox, oy, s)
    if lage is not None:
        malen(fb, lage[0], lage[1], lage[2])


# ======================================================================
# Schnee
# ======================================================================
# Drei Tiefen: weit (klein, dunkel, langsam), mittel, nah (gross, hell,
# schnell). Die Farben sind bewusst "krumm" - wischen() erkennt eine
# Flocke daran, dass der Bildpunkt noch genau ihre Farbe hat, und eine
# ungerade Farbe kommt in einem Cover kaum zufaellig an derselben
# Stelle vor.
SCHNEE_FARBEN = ((147, 155, 177), (205, 213, 231), (237, 243, 253))
SCHNEE_TEMPO = (30.0, 55.0, 85.0)          # Punkte je Sekunde bei s=3
SCHNEE_ANTEILE = (0.45, 0.35, 0.20)
SCHNEE_ZAHL_HD = 55
SCHNEE_ZAHL_ROEHRE = 28
SCHNEE_TAKT = 0.05                          # hoechstens 20 Bilder/s
SCHNEE_RUHE = 0.6                           # so lange nach einer Taste

_RUND4 = (".##.", "####", "####", ".##.")
_RUND6 = ("..##..", ".####.", "######", "######", ".####.", "..##..")
_STERN = ("#.#.#", ".###.", "#####", ".###.", "#.#.#")
STERN_ANTEIL = 0.25                         # so viele der nahen Flocken


def _form(muster, zelle):
    """Muster aus Zellen -> Liste je Bildzeile von (dx, laenge)."""
    zeilen = []
    for reihe in muster:
        stuecke = []
        x = 0
        while x < len(reihe):
            if reihe[x] == "#":
                a = x
                while x < len(reihe) and reihe[x] == "#":
                    x += 1
                stuecke.append((a * zelle, (x - a) * zelle))
            else:
                x += 1
        for _ in range(zelle):
            zeilen.append(stuecke)
    return zeilen


def flocken_formen(s):
    """Die Formen der Flocken als Bildzeilen, in der Reihenfolge
    weit, mittel, nah, nah-als-Stern. Auf HDMI runde Flocken wie im
    freigegebenen Beispiel (bei 1080p 2, 8 und 12 Punkte gross, dazu ab
    und zu ein Kristall); auf der Roehre (s=1) bewusst Pixel-Schnee:
    ein Punkt, ein heller Punkt, ein Zweierquadrat."""
    if s <= 1:
        punkt = _form(("#",), 1)
        zwei = _form(("#",), 2)
        return (punkt, punkt, zwei, zwei)
    zelle = max(1, (s + 1) // 2)
    return (_form(("#",), max(1, s - 1)), _form(_RUND4, zelle),
            _form(_RUND6, zelle), _form(_STERN, zelle))


class Schnee(object):
    """Fallender Schnee, der sich selbst wieder wegraeumt.

    WIE: jede Flocke merkt sich beim Zeichnen die Bildpunkte darunter
    und beim naechsten Schritt werden sie zurueckgeschrieben, bevor die
    Flocke an ihrer neuen Stelle erscheint. Geflippt werden genau diese
    kleinen Rechtecke - der Rest des Bildes bleibt unberuehrt, damit
    bleibt auch die Bedingung fuer flip_rechtecke() erfuellt
    (ausserhalb der Rechtecke stimmen Puffer und Schirm ueberein).

    UND WENN DAZWISCHEN JEMAND ANDERES GEZEICHNET HAT - die Laufschrift,
    die Uhr, ein nachgeladenes Cover? Dann liegt unter der Flocke etwas
    Neues, und der gemerkte Untergrund ist veraltet. wischen() schreibt
    deshalb nur dort zurueck, wo noch GENAU die Flocke steht; ein
    uebermalter Bildpunkt gehoert dem, der ihn uebermalt hat. Groessere
    Zeichenvorgaenge (draw(), das Nachzeichnen) raeumen den Schnee
    vorher ganz weg - siehe _schnee_weg() in frontend.py."""

    def __init__(self, W, H, s, seed=None):
        self.W, self.H, self.s = W, H, s
        self.formen = flocken_formen(s)
        rnd = random.Random(seed)
        self._rnd = rnd
        zahl = SCHNEE_ZAHL_ROEHRE if s <= 1 else SCHNEE_ZAHL_HD
        self.flocken = []
        for i in range(zahl):
            z = rnd.random()
            tiefe = 0 if z < SCHNEE_ANTEILE[0] else (
                1 if z < SCHNEE_ANTEILE[0] + SCHNEE_ANTEILE[1] else 2)
            form = tiefe
            if tiefe == 2 and rnd.random() < STERN_ANTEIL:
                form = 3
            self.flocken.append([rnd.uniform(0, W), rnd.uniform(0, H),
                                 tiefe, rnd.uniform(0, 2 * math.pi),
                                 rnd.uniform(0.6, 1.4), form])
        self.gezeichnet = []      # (x, y, w, h, unter, drauf) je Flocke
        self.zeit = 0.0

    def schritt(self, dt):
        """Alle Flocken um dt Sekunden weiter."""
        dt = max(0.0, min(dt, 0.2))     # nach einer Pause nicht springen
        self.zeit += dt
        f = self.s / 3.0
        for fl in self.flocken:
            x, y, tiefe, phase, eigen, form = fl
            y += SCHNEE_TEMPO[tiefe] * eigen * f * dt
            x += math.sin(phase + self.zeit * (0.8 + 0.3 * tiefe)) \
                * 12.0 * f * (tiefe + 1) * dt
            hoch = len(self.formen[form])
            if y > self.H:
                y = -hoch - self._rnd.uniform(0, 20 * f)
                x = self._rnd.uniform(0, self.W)
            if x < -hoch:
                x += self.W + hoch
            elif x > self.W:
                x -= self.W + hoch
            fl[0], fl[1] = x, y

    def wischen(self, fb):
        """Alle gezeichneten Flocken wieder weg. Liefert die Rechtecke,
        die geflippt werden muessen."""
        if not self.gezeichnet:
            return []
        buf, zl = fb.buf, fb.stride
        rechtecke = []
        for (x, y, w, h, unter, drauf) in reversed(self.gezeichnet):
            n = w * 4
            off = y * zl + x * 4
            for i in range(h):
                jetzt = buf[off:off + n]
                d = drauf[i]
                if jetzt == d:
                    buf[off:off + n] = unter[i]
                else:
                    u = unter[i]
                    for p in range(0, n, 4):
                        dp = d[p:p + 4]
                        if jetzt[p:p + 4] == dp and dp != u[p:p + 4]:
                            buf[off + p:off + p + 4] = u[p:p + 4]
                off += zl
            rechtecke.append((x, y, w, h))
        self.gezeichnet = []
        return rechtecke

    def zeichnen(self, fb):
        """Alle Flocken an ihrer jetzigen Stelle zeichnen. Liefert die
        Rechtecke. Nur Flocken, die ganz im Bild liegen - am Rand
        tauchen sie einen Schritt spaeter auf, das sieht man nicht."""
        buf, zl = fb.buf, fb.stride
        W, H = fb.width, fb.height
        rechtecke = []
        for (x, y, tiefe, _p, _e, f) in self.flocken:
            form = self.formen[f]
            h = len(form)
            w = h
            xi, yi = int(x), int(y)
            if xi < 0 or yi < 0 or xi + w > W or yi + h > H:
                continue
            farbe = fb.px(SCHNEE_FARBEN[tiefe])
            n = w * 4
            off = yi * zl + xi * 4
            unter, drauf = [], []
            o = off
            for stuecke in form:
                unter.append(bytes(buf[o:o + n]))
                for dx, laenge in stuecke:
                    a = o + dx * 4
                    buf[a:a + laenge * 4] = farbe * laenge
                drauf.append(bytes(buf[o:o + n]))
                o += zl
            self.gezeichnet.append((xi, yi, w, h, unter, drauf))
            rechtecke.append((xi, yi, w, h))
        return rechtecke
