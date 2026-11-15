#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Das Overlay laedt nie selbst Metadaten und laesst Eingaben vor (Build 325).

DER ANLASS steht im Log vom 15.11., beim Betreten einer Kategorie:

    RUCKLER: 956 ms busy (stream=224 haus=3 zeichnen=53 rest=676 ...)

stream= ist die Zustandsmeldung fuers Web-Overlay. Sie fragte das erste
Spiel der neuen Liste nach Genre und Jahr - und der ERSTE get_meta()-
Aufruf fuer ein System laedt einmalig dessen Tabellen. 224 ms, in denen
die Hauptschleife keinen Druck gelesen hat.

GEPRUEFT WIRD:
  1. meta_bereit() sagt die Wahrheit ueber die Zwischenspeicher: vor dem
     Laden nein, nach metadaten_ganz_vorwaermen() ja, nach dem
     Verdraengen wieder nein. GEGENPROBE: das alte metadaten_vorwaermen()
     allein laedt die gamelist nicht - meta_bereit() bleibt nein.
  2. stream_state() ruft get_meta() bei kalten Metadaten NICHT auf und
     stoesst stattdessen den Hintergrund an. GEGENPROBE: bei warmen
     Metadaten stehen Genre und Jahr drin.
  3. Der Hintergrundfaden laedt wirklich, je System hoechstens einer.
  4. _publish_stream() meldet nichts, solange eine Eingabe ansteht, und
     holt es im Leerlauf von next_action() nach. Genre und Jahr, die
     spaeter kommen, werden nachgemeldet.

Ausfuehren:
    python3 tools/test_overlay_metadaten.py
"""
import json
import os
import shutil
import sys
import tempfile
import threading
import time

_HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HIER)

import _harness as H                                     # noqa: E402

fm = H.fm
import fe.art as A                                       # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


print(__doc__.strip().split("\n")[0])
print()

TMP = tempfile.mkdtemp(prefix="overlay_meta_")
META = os.path.join(TMP, "meta")
os.makedirs(META)
SPIEL = "Super Mario World (USA)"
with open(os.path.join(META, "SNES.json"), "w") as fh:
    json.dump({SPIEL: {"genre": "Platform", "year": "1990"}}, fh)

_alt = (A.META_BASE, A._fremd_an, A.GAMELIST_AUS_FLAG, A._gamelist_dateien)


def caches_leeren():
    A._meta_cache.clear()
    A._gamelist_cache.clear()
    A._docs_info_cache.clear()
    A._docs_info_knapp.clear()


def spiel(titel):
    return (titel, "game", ("/games/SNES/%s.sfc" % titel, ".sfc", "SNES",
                            None, None))


class Strom(object):
    """Attrappe des Stream-Servers: merkt sich, was gemeldet wurde."""

    def __init__(self):
        self.gemeldet = []

    def publish(self, st):
        self.gemeldet.append(dict(st))


def warten_bis(bedingung, runden=200):
    """In echten Runden zu 0,02 s - die Uhr des Pruefstands steht."""
    for _ in range(runden):
        if bedingung():
            return True
        time.sleep(0.02)
    return bedingung()


try:
    A.META_BASE = META
    A._fremd_an = False                 # keine fremde Datenbank im Test
    A.GAMELIST_AUS_FLAG = os.path.join(TMP, "gamelist_aus")   # nicht da
    A._gamelist_dateien = lambda syskey: []                   # keine Liste

    # -----------------------------------------------------------------------
    print("Test 1: meta_bereit() sagt die Wahrheit")
    # -----------------------------------------------------------------------
    caches_leeren()
    check("vor dem Laden: nein", A.meta_bereit("SNES") is False)
    A.metadaten_vorwaermen("SNES")
    check("GEGENPROBE: das alte Vorwaermen allein laedt die gamelist "
          "nicht", A.meta_bereit("SNES") is False,
          "gamelist_meta() steigt bei leerem Namen aus")
    caches_leeren()
    zeiten = A.metadaten_ganz_vorwaermen("SNES")
    check("nach metadaten_ganz_vorwaermen(): ja",
          A.meta_bereit("SNES") is True)
    check("es liefert vier Zeiten", len(zeiten) == 4, zeiten)
    check("und get_meta() hat danach die Daten",
          A.get_meta("SNES", SPIEL).get("genre") == "Platform")
    A._meta_cache.pop("SNES")
    check("verdraengt: wieder nein", A.meta_bereit("SNES") is False,
          "ein eigener Merker haette das nicht mitbekommen")
    check("ohne Systemschluessel: nichts zu laden",
          A.meta_bereit("") is True)

    # -----------------------------------------------------------------------
    print()
    print("Test 2: stream_state() laedt nie selbst")
    # -----------------------------------------------------------------------
    caches_leeren()
    H.set_screen(1280, 720)
    f = H.make_frontend(page=1)
    name, node, _ = f.cats[0]
    f.cats[0] = (name, node, "SNES")
    node["folders"] = {}
    node["items"] = [spiel(SPIEL)]
    node.pop("_display_items_cache", None)
    f.cat_i = 0
    f.item_i = 0
    gerufen = []
    angestossen = []
    _echt_get_meta = fm.get_meta

    def _zaehlend(syskey, rom):
        gerufen.append(syskey)
        return _echt_get_meta(syskey, rom)
    fm.get_meta = _zaehlend
    _echt_hg = f._meta_im_hintergrund
    f._meta_im_hintergrund = lambda sk: angestossen.append(sk)
    try:
        st = f.stream_state()
        check("kalt: get_meta() nicht gerufen", not gerufen, gerufen)
        check("kalt: der Hintergrund angestossen",
              angestossen == ["SNES"], angestossen)
        check("Genre und Jahr fehlen vorerst",
              st["genre"] is None and st["year"] is None)
        check("der Rest ist vollstaendig",
              st["syskey"] == "SNES" and st["art_name"] == SPIEL)
        A.metadaten_ganz_vorwaermen("SNES")
        st = f.stream_state()
        check("GEGENPROBE warm: get_meta() gerufen", gerufen == ["SNES"],
              gerufen)
        check("warm: Genre und Jahr da",
              st["genre"] == "Platform" and st["year"] == "1990",
              (st["genre"], st["year"]))
        check("warm: nichts mehr angestossen", angestossen == ["SNES"],
              angestossen)
    finally:
        fm.get_meta = _echt_get_meta
        f._meta_im_hintergrund = _echt_hg

    # -----------------------------------------------------------------------
    print()
    print("Test 3: der Hintergrundfaden laedt - je System einer")
    # -----------------------------------------------------------------------
    caches_leeren()
    tor = threading.Event()
    _echt_inne = f._vorarbeit_innehalten
    f._vorarbeit_innehalten = lambda: tor.wait(5.0)
    try:
        check("der erste Anstoss startet einen Faden",
              f._meta_im_hintergrund("SNES") is True)
        check("ein zweiter, solange er laeuft, nicht",
              f._meta_im_hintergrund("SNES") is False)
        check("er wartet zuerst (hier: das Tor) und laedt noch nicht",
              A.meta_bereit("SNES") is False)
        tor.set()
        check("danach ist geladen",
              warten_bis(lambda: A.meta_bereit("SNES")))
        check("und der Faden ist abgemeldet",
              warten_bis(lambda: "SNES" not in f._meta_laeuft))
        check("ohne Systemschluessel startet nichts",
              f._meta_im_hintergrund("") is False)
    finally:
        f._vorarbeit_innehalten = _echt_inne

    # -----------------------------------------------------------------------
    print()
    print("Test 4: eine wartende Eingabe hat Vorrang vor dem Overlay")
    # -----------------------------------------------------------------------
    caches_leeren()
    f._meta_im_hintergrund = lambda sk: False     # bleibt kalt
    strom = f.stream = Strom()
    f._stream_sig = None
    f._stream_cheap_sig = None
    f.inp.eingabe_anstehend = lambda: True
    f._publish_stream()
    check("Eingabe steht an: nichts gemeldet", not strom.gemeldet)
    f.inp.eingabe_anstehend = lambda: False
    f._publish_stream()
    check("GEGENPROBE: ohne Eingabe gemeldet", len(strom.gemeldet) == 1,
          len(strom.gemeldet))
    check("vorerst ohne Genre", strom.gemeldet[-1]["genre"] is None)
    A.metadaten_ganz_vorwaermen("SNES")
    f._publish_stream()
    check("dieselbe Stelle gleich danach: nichts Neues (Vorpruefung)",
          len(strom.gemeldet) == 1, len(strom.gemeldet))
    H.NOW[0] += 2.1
    f._publish_stream()
    check("nach der Frist: Genre und Jahr nachgemeldet",
          len(strom.gemeldet) == 2
          and strom.gemeldet[-1]["genre"] == "Platform",
          [g.get("genre") for g in strom.gemeldet])

    # Der Leerlauf von next_action() holt nach, was zurueckstand.
    f.item_i = 0
    gemeldet_vorher = len(strom.gemeldet)
    f.cats[0][1]["items"] = [spiel(SPIEL), spiel("Zweites Spiel (USA)")]
    f.cats[0][1].pop("_display_items_cache", None)
    f.item_i = 1                        # neue Stelle, noch nicht gemeldet
    rest = [None, None, "down"]

    def _lesen(timeout=None):
        H.NOW[0] += max(timeout or 0.05, 0.05)
        return rest.pop(0) if rest else "down"
    f.inp.read_action = _lesen
    f.inp.flush = lambda: None
    act = f.next_action()
    check("next_action() liefert die Taste", act == "down", act)
    check("und hat im Leerlauf nachgemeldet",
          len(strom.gemeldet) > gemeldet_vorher
          and strom.gemeldet[-1]["index"] == 1,
          [g.get("index") for g in strom.gemeldet])
    f.stream = None
    rest[:] = [None, None, "down"]
    gemeldet_vorher = len(strom.gemeldet)
    f.item_i = 0
    f.next_action()
    check("GEGENPROBE: ohne Overlay meldet der Leerlauf nichts",
          len(strom.gemeldet) == gemeldet_vorher)
finally:
    (A.META_BASE, A._fremd_an, A.GAMELIST_AUS_FLAG,
     A._gamelist_dateien) = _alt
    caches_leeren()
    H._zwischenspeicher_leeren()
    shutil.rmtree(TMP, ignore_errors=True)

print()
if fails:
    print("ROT: %d Pruefung(en) fehlgeschlagen:" % len(fails))
    for f_ in fails:
        print("   - " + f_)
    sys.exit(1)
print("ALLES GRUEN")
