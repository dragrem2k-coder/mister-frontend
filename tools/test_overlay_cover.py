#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Das Overlay-Cover: JPEG, PNG und .art - und nur EINE Cover-Suche.

AUSLOESER (Nutzer-Rueckmeldung, Build 259 lieferte das Cover an der
Erfolgswand): "das cover wird nicht angezeigt! egal welche rom ich
starte". Das Raster war da, der Rahmen fuers Cover war da - und leer.

DREI FALSCHE FAEHRTEN, bevor es stimmte, und sie stehen hier, weil die
Reihenfolge lehrreich ist:

  1. "Vorgabe steht auf aus" - nein, der Rahmen war ja sichtbar, also
     griff die Klasse und der Schalter stand richtig.
  2. "OBS hat die alte Seite im Cache" - nein, aus demselben Grund.
  3. "Der Zustand hat kein syskey" (Favoriten/Zuletzt gespielt setzen
     es leer) - plausibel, und FALSCH: der Nutzer hat gegengeprueft und
     aus einer echten Systemkategorie gestartet. Auch kein Cover.

Das Bild hat es entschieden: ein LEERER, aber SICHTBARER Rahmen heisst,
dass kein 'src' gesetzt wurde - bei einem fehlgeschlagenen Abruf haette
onerror ihn ganz ausgeblendet. Und der Nutzer hatte die richtige
Vermutung: "oder liegt es daran, dass wir die Covers alle von .art weg
in c-modul als png und jpg geaendert haben?"

GENAU DARAN LAG ES, und der eigentliche Fehler ist aelter als Build 259:
stream_server.py hatte eine ZWEITE, nachgebaute Cover-Suche, die nur
".art" kannte. Das Frontend liest laengst auch JPEG und PNG (dazu die
gamelist.xml und die fremde Datenbank). Wer seine Cover umgestellt hat,
bekam "no art" - im grossen Cover genauso wie an der Wand. Build 259 hat
den Fehler nicht gemacht, nur sichtbar.

GEPRUEFT WIRD DESHALB AM ECHTEN SERVER, ueber echte HTTP-Abrufe: was
beim Browser ankommt, ist die Zusage - nicht, welche Funktion wen
aufruft.

Ausfuehren:
    python3 tools/test_overlay_cover.py
"""
import io
import os
import shutil
import socket
import struct
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zlib

_HIER = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HIER)
_FRONTEND_DIR = os.path.dirname(
    os.environ.get("FRONTEND_PY",
                   os.path.join(_REPO, "frontend", "frontend.py")))
sys.path.insert(0, _FRONTEND_DIR)

from stream_server import StreamServer                  # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + extra) if extra else ""))
    if not cond:
        fails.append(label)


def _freier_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


TMP = tempfile.mkdtemp(prefix="overlay_cover_")
ART = os.path.join(TMP, "art")
ART_HD = os.path.join(TMP, "art_hd")
os.makedirs(os.path.join(ART, "SNES"))
os.makedirs(os.path.join(ART_HD, "SNES"))


def schreiben(base, name, inhalt):
    pfad = os.path.join(base, "SNES", name)
    with open(pfad, "wb") as f:
        f.write(inhalt)
    return inhalt


def art1(w, h, farbe):
    """Eine echte .art-Datei (ART1, BGRA, zlib) wie unsere Werkzeuge sie
    schreiben."""
    pix = bytes(farbe) * (w * h)
    return b"ART1" + struct.pack("<HH", w, h) + zlib.compress(pix)


# Ein JPEG und ein PNG muessen hier nicht gueltig sein: der Server
# reicht sie unveraendert durch, er dekodiert sie nicht. Genau das ist
# die Zusage, und ein Bytevergleich prueft sie schaerfer als ein Bild.
JPG = schreiben(ART, "Spiel A.jpg", b"\xff\xd8\xff\xe0JPEG-Inhalt-A")
PNG = schreiben(ART, "Spiel B.png", b"\x89PNG\r\n\x1a\nInhalt-B")
ARTD = schreiben(ART, "Spiel C.art", art1(4, 3, b"\x10\x20\x30\x00"))
NUMM = schreiben(ART, "012 Spiel D.jpg", b"\xff\xd8\xff\xe0JPEG-Inhalt-D")
HD = schreiben(ART_HD, "Spiel E.jpg", b"\xff\xd8\xff\xe0JPEG-HD")
SD = schreiben(ART, "Spiel E.jpg", b"\xff\xd8\xff\xe0JPEG-SD")

PORT = _freier_port()
SRV = StreamServer(ART, port=PORT, host="127.0.0.1", art_hd=ART_HD,
                   config_path=os.path.join(TMP, "cfg.json"),
                   badge_cache_dir=os.path.join(TMP, "badges"))
SRV.start()
time.sleep(0.4)


def hole(name, sysk="SNES"):
    """(Status, Inhaltstyp, Bytes) - 404 kommt als (404, '', b'')."""
    url = ("http://127.0.0.1:%d/art?sys=%s&name=%s"
           % (PORT, urllib.parse.quote(sysk), urllib.parse.quote(name)))
    try:
        r = urllib.request.urlopen(url, timeout=5)
        return r.getcode(), r.headers.get("Content-Type", ""), r.read()
    except urllib.error.HTTPError as e:
        return e.code, "", e.read()


try:
    # -----------------------------------------------------------------
    print("Test 1: JPEG und PNG kommen an - UNVERAENDERT")
    # -----------------------------------------------------------------
    code, typ, roh = hole("Spiel A")
    check("ein JPEG-Cover wird ausgeliefert", code == 200, "Status %s" % code)
    check("als image/jpeg", typ == "image/jpeg", typ)
    check("Byte fuer Byte wie auf der Karte", roh == JPG,
          "der Browser kann JPEG selbst - umpacken waere Arbeit fuer "
          "nichts, und auf dem DE10-Nano spuerbare Arbeit")

    code, typ, roh = hole("Spiel B")
    check("ein PNG-Cover wird ausgeliefert", code == 200, "Status %s" % code)
    check("als image/png", typ == "image/png", typ)
    check("ebenfalls unveraendert", roh == PNG)

    # -----------------------------------------------------------------
    print()
    print("Test 2: unser eigenes .art wird weiterhin gewandelt")
    # -----------------------------------------------------------------
    code, typ, roh = hole("Spiel C")
    check("auch .art kommt an", code == 200, "Status %s" % code)
    check("und zwar als PNG", typ == "image/png", typ)
    check("es ist ein echtes PNG", roh[:8] == b"\x89PNG\r\n\x1a\n")
    check("also NICHT die Rohdatei", roh != ARTD,
          "ART1 kennt ausser uns niemand")

    # -----------------------------------------------------------------
    print()
    print("Test 3: der Fund - was die alte, eigene Suche NICHT konnte")
    # -----------------------------------------------------------------
    # Die alte Suche sammelte ausschliesslich Dateien auf ".art" ein.
    # Ein Cover aus einem nummerierten Satz als .jpg war damit doppelt
    # unsichtbar: falsche Endung UND der "NNN "-Vorsatz.
    code, typ, roh = hole("Spiel D")
    check("ein nummeriertes JPEG wird gefunden", code == 200,
          "Status %s - die fuehrende '012 ' muss ignoriert werden, "
          "und zwar auch bei einer fremden Endung" % code)
    check("und es ist das richtige", roh == NUMM)

    # -----------------------------------------------------------------
    print()
    print("Test 4: HD vor Standard, und was es nicht gibt")
    # -----------------------------------------------------------------
    code, typ, roh = hole("Spiel E")
    check("liegt es in beiden Ordnern, gewinnt HD", roh == HD,
          "im Browser ist Platz genug - dieselbe Rangfolge wie im "
          "Frontend ab 720 Bildzeilen")
    check("und es ist nicht das SD-Bild", roh != SD)

    code, typ, roh = hole("Gibt es nicht")
    check("ein fehlendes Cover bleibt 404", code == 404, "Status %s" % code)
    check("mit der bisherigen Begruendung", roh == b"no art", str(roh))
    check("ohne Systemkuerzel ebenfalls 404", hole("Spiel A", "")[0] == 404)

    # -----------------------------------------------------------------
    print()
    print("Test 5: es gibt nur EINE Cover-Suche")
    # -----------------------------------------------------------------
    # Das ist der eigentliche Punkt des Builds. Eine nachgebaute Suche
    # geht irgendwann immer auseinander - sie ist ja genau deshalb
    # auseinandergegangen.
    _q = io.open(os.path.join(_FRONTEND_DIR, "stream_server.py"),
                 encoding="utf-8").read()
    _fa = _q.split("def _find_art(")[1].split("\n    def ")[0]
    check("_find_art() fragt fe/art.py", "_cover_datei_holen()" in _fa)
    check("und zwar mit UNSEREN Ordnern", "self._art_bases" in _fa,
          "der Server bekommt sie als Parameter - sonst liefe jeder "
          "Test gegen /media/fat")
    check("der eigene .art-Weg ist nur noch Rueckfall",
          _fa.index("_cover_datei_holen()") < _fa.index('name + ".art"'),
          "er steht hinter der Abfrage, nicht davor")

    _ar = io.open(os.path.join(_FRONTEND_DIR, "fe", "art.py"),
                  encoding="utf-8").read()
    _cd = _ar.split("def cover_datei(")[1].split("\ndef ")[0]
    check("cover_datei() benutzt die vorhandene Rangfolge",
          "_art_path_in(" in _cd,
          "exakter Name, unscharfer Vergleich, gamelist, fremde "
          "Datenbank - alles schon da, nichts davon nachgebaut")
    check("und liefert nur, was es WIRKLICH gibt",
          "os.path.exists(" in _cd,
          "_art_path_in() gibt auch einen Pfad zurueck, der nicht "
          "existiert - das ist dort Absicht und hier ein Fehler")

    # Und die Zusage, die den Nutzerfall beschreibt, in einem Satz:
    SRV2 = None
    _neu = os.path.join(TMP, "nur_png")
    os.makedirs(os.path.join(_neu, "MEGACD"))
    with open(os.path.join(_neu, "MEGACD", "Sonic CD (USA).png"), "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\nSonic")
    _p2 = _freier_port()
    SRV2 = StreamServer(_neu, port=_p2, host="127.0.0.1",
                        config_path=os.path.join(TMP, "cfg2.json"),
                        badge_cache_dir=os.path.join(TMP, "badges2"))
    SRV2.start()
    time.sleep(0.4)
    try:
        r = urllib.request.urlopen(
            "http://127.0.0.1:%d/art?sys=MEGACD&name=%s"
            % (_p2, urllib.parse.quote("Sonic CD (USA)")), timeout=5)
        _code2, _roh2 = r.getcode(), r.read()
    except urllib.error.HTTPError as e:
        _code2, _roh2 = e.code, b""
    check("eine Sammlung GANZ OHNE .art liefert trotzdem Cover",
          _code2 == 200 and _roh2 == b"\x89PNG\r\n\x1a\nSonic",
          "genau der gemeldete Fall - vorher kam hier 'no art'")
finally:
    try:
        SRV.stop()
    except Exception:                                    # noqa: BLE001
        pass
    try:
        if SRV2:
            SRV2.stop()
    except Exception:                                    # noqa: BLE001
        pass
    shutil.rmtree(TMP, ignore_errors=True)

print()
if fails:
    print("FEHLGESCHLAGEN: %d" % len(fails))
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("Alle Pruefungen bestanden.")
