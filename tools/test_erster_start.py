#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Der erste Start auf einer frischen Karte und der Boxart-Download (Build 336).

NUTZER: "neue Mister ... SH Script geladen ... restart. Aber nix zu
sehen". Im Log: "davon _partition_core_cats() 106632 ms" - das erste
Einlesen des Arcade-Ordners, zwei Minuten lang ohne ein Bild.
Dazu: "das mit dennsen86 wo er die boxarts abfragt muss raus, und bevor
man boxarts nachlaedt sollte das frontend erst schauen ob schon jemand
ueber update_all sich die boxarts geladen hat".

GEPRUEFT WIRD:
  1. _ordner_eintraege(): sortiert, ohne Punkt-Dateien, erkennt Ordner,
     Links und kaputte Links; ein fehlender Ordner wirft OSError.
  2. Der Arcade-Baum: dasselbe Ergebnis wie der alte Weg (listdir +
     isdir je Eintrag), aber ohne einen einzigen isdir()/stat() je
     Eintrag; melden() bekommt den wachsenden Stand; ein Fehler in
     melden() bricht das Einlesen nicht ab; das Log nennt die Zahlen.
  3. Der Spiele-Baum: ebenfalls ohne isdir() je Eintrag.
  4. Die Anzeige: erst nach einer kleinen Weile, dann gedrosselt; zeigt
     Text und Zahlen; danach wird alles neu gezeichnet.
  5. Das Anklopfen (F9) waehrend des ersten Einlesens: nur beim Start,
     nur mit Mechanik, ein Fehler bricht nichts ab; die Uhr dafuer
     steht VOR dem Einlesen.
  6. Der Boxart-Download: keine Mirror-Quelle mehr; zaehlt die Cover
     von update_all und meldet sie vorher; ein solches Cover wird auch
     im Modus "neu" nicht geladen.

Ausfuehren:
    python3 tools/test_erster_start.py
"""
import io
import os
import re
import shutil
import sys
import tempfile
import contextlib

_HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HIER)

import _harness as H                                     # noqa: E402

fm = H.fm
import fe.scan as SC                                     # noqa: E402
import fe.translations as TR                             # noqa: E402

fails = []


def check(label, cond, extra=""):
    print(("  OK   " if cond else "  FEHL ") + label
          + (("  " + str(extra)) if extra else ""))
    if not cond:
        fails.append(label)


def anlegen(pfad):
    os.makedirs(os.path.dirname(pfad), exist_ok=True)
    open(pfad, "wb").close()


def alter_arcade_baum(path):
    """Der Weg bis Build 335, nur als Vergleich."""
    node = {"folders": {}, "items": []}
    try:
        entries = sorted(os.listdir(path), key=str.lower)
    except OSError:
        return node
    files = []
    for entry in entries:
        if entry.startswith("."):
            continue
        full = os.path.join(path, entry)
        if os.path.isdir(full):
            sub = alter_arcade_baum(full)
            if sub["folders"] or sub["items"]:
                node["folders"][entry] = sub
        else:
            if os.path.splitext(entry)[1].lower() in (".mra", ".rbf", ".mgl"):
                files.append(full)
    for f in sorted(files, key=lambda p: os.path.basename(p).lower()):
        name = os.path.splitext(os.path.basename(f))[0]
        name = re.sub(r"_\d{8}[a-zA-Z]?$", "", name)
        node["items"].append((name, "core", f))
    return node


@contextlib.contextmanager
def gezaehlt(zaehler):
    """os.path.isdir und os.stat zaehlen."""
    _isdir, _stat = os.path.isdir, os.stat

    def isdir(p):
        zaehler.append(("isdir", p))
        return _isdir(p)

    def stat(p, *a, **k):
        zaehler.append(("stat", p))
        return _stat(p, *a, **k)
    os.path.isdir, os.stat = isdir, stat
    try:
        yield
    finally:
        os.path.isdir, os.stat = _isdir, _stat


print(__doc__.strip().split("\n")[0])
print()
TMP = tempfile.mkdtemp(prefix="erster_start_")
_lang = TR.CURRENT_LANG
_cache_alt = SC.ARCADE_TREE_CACHE
try:
    TR.CURRENT_LANG = "de"
    # -----------------------------------------------------------------------
    print("Test 1: _ordner_eintraege()")
    # -----------------------------------------------------------------------
    o = os.path.join(TMP, "eintraege")
    anlegen(os.path.join(o, "beta.mra"))
    anlegen(os.path.join(o, "Alpha.mra"))
    anlegen(os.path.join(o, ".versteckt"))
    anlegen(os.path.join(o, "Unter", "x.mra"))
    os.symlink(os.path.join(o, "Unter"), os.path.join(o, "Link"))
    os.symlink(os.path.join(o, "fehlt"), os.path.join(o, "kaputt"))
    e = SC._ordner_eintraege(o)
    check("sortiert ohne Gross/Klein, ohne Punkt-Dateien",
          [n for n, _d, _l in e] == ["Alpha.mra", "beta.mra", "kaputt",
                                     "Link", "Unter"], e)
    art = {n: (d, l) for n, d, l in e}
    check("Ordner erkannt", art["Unter"] == (True, False))
    check("Link auf Ordner: Ordner UND Link", art["Link"] == (True, True))
    check("kaputter Link: kein Ordner (wie os.path.isdir)",
          art["kaputt"] == (False, False))
    check("Datei: kein Ordner", art["Alpha.mra"] == (False, False))
    try:
        SC._ordner_eintraege(os.path.join(TMP, "gibtsnicht"))
        check("fehlender Ordner wirft OSError", False)
    except OSError:
        check("fehlender Ordner wirft OSError", True)

    # -----------------------------------------------------------------------
    print()
    print("Test 2: der Arcade-Baum")
    # -----------------------------------------------------------------------
    arc = os.path.join(TMP, "_Arcade")
    for i in range(120):
        anlegen(os.path.join(arc, "Spiel%03d.mra" % i))
    anlegen(os.path.join(arc, "cores", "Kern_20240101.rbf"))
    anlegen(os.path.join(arc, "_alternatives", "_Pac", "Pac (alt)_20231231b.mra"))
    anlegen(os.path.join(arc, "_Organized", "_1 A-E", "Asteroids.mra"))
    anlegen(os.path.join(arc, "_Organized", "_2 leer", "liesmich.txt"))
    anlegen(os.path.join(arc, ".versteckt", "x.mra"))
    anlegen(os.path.join(arc, "notiz.txt"))
    erwartet = alter_arcade_baum(arc)
    zaehler = []
    stand = []
    with gezaehlt(zaehler):
        neu = SC._arcade_folder_tree(arc, lambda d, o: stand.append((d, o)))
    check("dasselbe Ergebnis wie der alte Weg", neu == erwartet)
    check("leere Ordner fehlen weiterhin",
          "_2 leer" not in neu["folders"]["_Organized"]["folders"])
    check("KEIN isdir()/stat() je Eintrag (vorher 128 und mehr)",
          not zaehler, len(zaehler))
    check("melden(): je Ordner einmal, Stand waechst",
          len(stand) >= 5 and all(a <= b for a, b in zip(stand, stand[1:])),
          stand[-3:])
    check("melden(): am Ende alle Dateien und Ordner",
          stand[-1] == (123, 7), stand[-1])

    def kaputt(_d, _o):
        raise ValueError("Anzeige kaputt")
    meldungen = []
    _log = SC.LOG
    SC.LOG = lambda s: meldungen.append(s)
    try:
        neu2 = SC._arcade_folder_tree(arc, kaputt)
    finally:
        SC.LOG = _log
    check("ein Fehler in melden() bricht das Einlesen nicht ab",
          neu2 == erwartet)
    check("... und steht einmal im Log",
          len([m for m in meldungen if "Fortschrittsanzeige" in m]) == 1,
          len(meldungen))

    SC.ARCADE_TREE_CACHE = os.path.join(TMP, "arcade_tree_cache.pkl")
    meldungen = []
    SC.LOG = lambda s: meldungen.append(s)
    try:
        SC._arcade_tree_cached(arc, force=True)
        z1 = [m for m in meldungen if m.startswith("Arcade-Ordner eingelesen")]
        meldungen[:] = []
        aufrufe = []
        SC._arcade_tree_cached(arc, melden=lambda d, o: aufrufe.append(d))
        z2 = [m for m in meldungen if m.startswith("Arcade-Ordner eingelesen")]
    finally:
        SC.LOG = _log
    check("das Log nennt Dateien, Ordner und Dauer",
          len(z1) == 1 and "123 Dateien in 7 Ordnern" in z1[0], z1)
    check("passender Zwischenspeicher: kein Einlesen, keine Anzeige",
          not z2 and not aufrufe)

    # -----------------------------------------------------------------------
    print()
    print("Test 3: der Spiele-Baum")
    # -----------------------------------------------------------------------
    snes = os.path.join(TMP, "games", "SNES")
    for i in range(60):
        anlegen(os.path.join(snes, "Spiel %02d (USA).sfc" % i))
    anlegen(os.path.join(snes, "Hacks", "Hack (USA).sfc"))
    zaehler = []
    with gezaehlt(zaehler):
        node = SC._scan_folder_tree(snes, "SNES", "SNES",
                                    {".sfc": (1, "f", 1)})
    # "Hacks" mit genau einem Spiel wird durch dieses Spiel ersetzt
    # (Build 156, einzelordner_aufloesen) - also 61 Eintraege.
    namen = sorted(i[0] for i in node["items"])
    check("alle Spiele gefunden", len(namen) == 61
          and any("Hack" in n for n in namen), len(namen))
    check("KEIN isdir() je Eintrag",
          not [z for z in zaehler if z[0] == "isdir"],
          len([z for z in zaehler if z[0] == "isdir"]))

    # -----------------------------------------------------------------------
    print()
    print("Test 4: die Anzeige beim Einlesen")
    # -----------------------------------------------------------------------
    for (w, hh) in ((1920, 1080), (320, 240)):
        H.set_screen(w, hh)
        f = H.make_frontend(page=0)
        texte, bilder = [], []
        echt = f.fb.text
        f.fb.text = lambda x, y, txt, *a, **k: (texte.append(txt),
                                                echt(x, y, txt, *a, **k))
        f.fb.flip = lambda *a, **k: bilder.append(1)
        uhr = [100.0]
        _mono = fm.time.monotonic
        fm.time.monotonic = lambda: uhr[0]
        try:
            f._arcade_einlesen_seit = 100.0
            f._arcade_einlesen_zuletzt = 0.0
            f._arcade_einlesen_bilder = 0
            f._force_full_redraw = False
            f._draw_arcade_einlesen(10, 1)
            check("%dx%d: in den ersten 0,4 s nichts" % (w, hh), not bilder)
            uhr[0] = 100.5
            f._draw_arcade_einlesen(500, 12)
            check("%dx%d: danach ein Bild" % (w, hh), len(bilder) == 1)
            uhr[0] = 100.6
            f._draw_arcade_einlesen(600, 13)
            check("%dx%d: hoechstens alle 0,2 s" % (w, hh), len(bilder) == 1)
            uhr[0] = 100.75
            f._draw_arcade_einlesen(700, 14)
            check("%dx%d: und dann das naechste" % (w, hh), len(bilder) == 2)
        finally:
            fm.time.monotonic = _mono
        check("%dx%d: Text und Zahlen im Bild" % (w, hh),
              any("Arcade" in z for z in texte)
              and any("700" in z and "14" in z for z in texte), texte[-4:])
        check("%dx%d: danach wird alles neu gezeichnet" % (w, hh),
              f._force_full_redraw is True)
    check("Texte in beiden Sprachen",
          all(set(TR.TRANSLATIONS.get(k, {})) >= {"de", "en"}
              for k in ("arcade_einlesen", "arcade_einlesen_stand",
                        "arcade_einlesen_hinweis")))
    check("Stand-Text nimmt zwei Zahlen",
          fm.t("arcade_einlesen_stand", 3, 2) == "3 Dateien in 2 Ordnern")

    # -----------------------------------------------------------------------
    print()
    print("Test 5: F9 waehrend des ersten Einlesens")
    # -----------------------------------------------------------------------
    f = H.make_frontend(page=0)
    geklopft = []
    f._konsole_sichern = lambda *a: geklopft.append(1)
    _mech = type(f).konsole_mechanik
    try:
        type(f).konsole_mechanik = classmethod(lambda cls: True)
        f._im_start = False
        f._einlesen_lebenszeichen()
        check("GEGENPROBE: nach dem Start klopft niemand", not geklopft)
        f._im_start = True
        f._einlesen_lebenszeichen()
        check("beim Start mit Mechanik: _konsole_sichern()", geklopft == [1])
        type(f).konsole_mechanik = classmethod(lambda cls: False)
        f._einlesen_lebenszeichen()
        check("GEGENPROBE: ohne Mechanik nicht", geklopft == [1])
        type(f).konsole_mechanik = classmethod(lambda cls: True)

        def boom(*a):
            raise RuntimeError("kaputt")
        f._konsole_sichern = boom
        f._einlesen_lebenszeichen()
        check("ein Fehler beim Klopfen bricht nichts ab", True)
    finally:
        type(f).konsole_mechanik = _mech
        f._im_start = False

    q = open(H.FRONTEND_PY, encoding="utf-8").read()
    i_uhr = q.find("self._boot_time = time.monotonic()")
    i_bau = q.find("self._im_start = True")
    check("die F9-Uhr steht VOR dem ersten Einlesen",
          0 < i_uhr < i_bau, (i_uhr, i_bau))
    check("_im_start wird nach dem Einlesen sicher zurueckgesetzt",
          "finally:\n            self._im_start = False" in q)
    for name in ("_draw_scan_progress", "_draw_laufwerk_warten",
                 "_draw_arcade_einlesen"):
        k = q[q.find("def %s(" % name):]
        k = k[:k.find("\n    def ", 10)]
        check("%s klopft mit an" % name, "self._einlesen_lebenszeichen()" in k)
    k = q[q.find("def _partition_core_cats("):]
    k = k[:k.find("\n    def ", 10)]
    check("_partition_core_cats() reicht die Anzeige durch",
          "melden=self._draw_arcade_einlesen" in k)

    # -----------------------------------------------------------------------
    print()
    print("Test 6: der Boxart-Download")
    # -----------------------------------------------------------------------
    quelle = open(os.path.join(os.path.dirname(H.FRONTEND_PY),
                               "mister_boxart.py"), encoding="utf-8").read()
    code = "\n".join(z for z in quelle.split("\n")
                     if not z.lstrip().startswith("#"))
    check("kein dennsen86clips.de mehr im Code",
          "dennsen86clips" not in code.split('"""', 2)[-1])
    check("keine Mirror-Funktionen mehr",
          not any(n in quelle for n in ("def process_system_mirror",
                                        "def list_art", "def list_png",
                                        "HTTP_HOST =")))
    sys.path.insert(0, os.path.dirname(H.FRONTEND_PY))
    import mister_boxart as MB
    ua = os.path.join(TMP, "docs")
    for i in range(5):
        anlegen(os.path.join(ua, "SNES", "Artwork", "Spiel %d (USA).png" % i))
    anlegen(os.path.join(ua, "SNES", "Screenshots", "Spiel 0 (USA).png"))
    anlegen(os.path.join(ua, "Genesis", "Artwork", "Sonic.jpg"))
    anlegen(os.path.join(ua, "Genesis", "Artwork", "gameinfo.tsv"))
    anlegen(os.path.join(ua, "NES", "Manuals", "Mario.pdf"))
    check("update_all_artwork(): Cover gezaehlt, Bildschirmfotos nicht",
          MB.update_all_artwork((ua,)) == (2, 6),
          MB.update_all_artwork((ua,)))
    check("ohne Datenbank: (0, 0), kein Absturz",
          MB.update_all_artwork((os.path.join(TMP, "nix"),)) == (0, 0))
    puf = io.StringIO()
    with contextlib.redirect_stdout(puf):
        MB.update_all_melden((ua,))
    check("meldet vorher, was update_all schon hat",
          "Gefunden: 6 Cover in 2 Systemen" in puf.getvalue(), puf.getvalue())
    puf = io.StringIO()
    with contextlib.redirect_stdout(puf):
        MB.update_all_melden((os.path.join(TMP, "nix"),))
    check("ohne: nennt den Weg ueber update_all",
          "Game Artwork DBs" in puf.getvalue())

    # process_system(): update_all-Cover werden nie geladen, auch mit "neu"
    geladen = []
    _fb, _dc, _neu = MB.process_system_fallback, MB._docs_cover, MB.FORCE_NEU
    try:
        MB.process_system_fallback = (lambda sk, names, sn, out, box, g:
                                      geladen.extend(names) or [])
        MB._docs_cover = lambda sk, n: n.startswith("UA")
        art = os.path.join(TMP, "art")
        anlegen(os.path.join(art, "SNES", "Eigen.png"))
        roms = [("UA Spiel", ".sfc"), ("Eigen", ".sfc"), ("Fehlt", ".sfc")]
        for neu_modus, erwartet in ((False, ["Fehlt"]),
                                    (True, ["Eigen", "Fehlt"])):
            del geladen[:]
            MB.FORCE_NEU = neu_modus
            g = {"roms": 0, "neu": 0, "vorhanden": 0, "fehlend": 0,
                 "update_all": 0}
            with contextlib.redirect_stdout(io.StringIO()):
                MB.process_system("SNES", roms, {".sfc": "SNES"}, art, None,
                                  (1, 1), g)
            check("Modus %s: geladen nur %s" % ("neu" if neu_modus else
                                                 "normal", erwartet),
                  sorted(geladen) == erwartet, geladen)
            check("Modus %s: update_all-Cover gezaehlt"
                  % ("neu" if neu_modus else "normal"),
                  g["update_all"] == 1, g)
    finally:
        MB.process_system_fallback, MB._docs_cover, MB.FORCE_NEU = \
            _fb, _dc, _neu
finally:
    TR.CURRENT_LANG = _lang
    SC.ARCADE_TREE_CACHE = _cache_alt
    shutil.rmtree(TMP, ignore_errors=True)

print()
if fails:
    print("ROT: %d Pruefung(en) fehlgeschlagen:" % len(fails))
    for f_ in fails:
        print("   - " + f_)
    sys.exit(1)
print("ALLES GRUEN")
